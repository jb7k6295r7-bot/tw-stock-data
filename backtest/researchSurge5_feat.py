# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq5 特徵層（第二批）：每個特徵分位 × 250 格 × 三段的 ① 提升倍數（月分群 CI）＋ ② 涵蓋率、③ 可交易曲線（5～250 日）、
挑選（探索）→ 確認（Bonferroni）→ 早年；妖股特徵（P 後回落 30／50／70%）；結束特徵（P−k 對漲勢中段）；買不買得到版（挑中者）。
由 researchSurge5 --stage feat 呼叫；讀法見 researchSurge5 開頭 S1～S17。"""
from __future__ import annotations

import html
import json
import os
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

from backtest import researchSurge5 as S5
from backtest import avgdown as AV

Z95 = 1.959963984540054
HALF = S5.NC // 2                          # 125（裁定 seq278 §2：「至少一半格」照比例套用）
NH = len(S5.HS)
HI_OF_CELL = np.array([c // len(S5.GS) for c in range(S5.NC)])


def levels():
    """(欄索引, 欄, 級距碼, 級距名, 名稱, 類別, 型態, 早年可用, 進挑選)"""
    out = []
    for f in S5.SPECS:
        col, name, cat, kind, L, early = f
        fi = S5.FIX[col]
        if kind in ("q", "qts") or (kind == "x" and col != "d_X1"):
            for q in range(1, 6):
                out.append((fi, col, q, f"Q{q}", name, cat, kind, early, True))
        elif kind == "bin":
            out.append((fi, col, 2, "是", name, cat, kind, early, True))
        elif kind in ("dbin",) or col == "d_X1":
            out.append((fi, col, 2, "是", name, cat, "dbin", early, False))
        elif kind == "dlvl":
            for v, nm in S5.LVLN[col].items():
                out.append((fi, col, v + 1, nm, name, cat, kind, early, False))
    return out


def ratio_stats(e, nn, eall, nall, cov_num, cov_den, z):
    """e, nn：(NC, NM) 有特徵者事件、定義域列；eall, nall：(NC, NM) 特徵有值全體 ⇒ lift, lo, hi, cov（NC）。"""
    N = nn.sum(1); Nall = nall.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = e.sum(1) / N
        se = np.sqrt(((e - p[:, None] * nn) ** 2).sum(1)) / N
        base = eall.sum(1) / Nall
        lift = p / base; lo = (p - z * se) / base; hi = (p + z * se) / base
        cov = cov_num / cov_den
    lift[~(base > 0)] = np.nan; lo[~(base > 0)] = np.nan
    return lift, lo, hi, cov


def run(log):
    T0 = time.time()
    os.makedirs(S5.OUT, exist_ok=True)
    uni, cal, mon, segd, E = S5.load_all()
    n = len(cal); S = len(uni)
    mi = (mon - mon.min()).astype(np.int64); NM = int(mi.max()) + 1
    segm = {sg: np.zeros(NM, bool) for sg in S5.SEG}
    for sg, dm in segd.items():
        segm[sg][np.unique(mi[dm])] = True
    bar = np.load(os.path.join(S5.WORK, "bar.npy")); hdef = np.load(os.path.join(S5.WORK, "hdef.npy"))
    locked = np.load(os.path.join(S5.WORK, "locked.npy")); disp = np.load(os.path.join(S5.WORK, "disp.npy"))
    nxt_bar = np.zeros_like(bar); nxt_bar[:, :-1] = bar[:, 1:]
    excl = ~nxt_bar; excl[:, :-1] |= locked[:, 1:] | disp[:, 1:]
    log("[特徵] 載入五等分表（全部進記憶體）"); Q = np.load(os.path.join(S5.WORK, "Q.npy"))
    LV = levels()
    log(f"[特徵] 級距 {len(LV)}（進挑選 {sum(1 for x in LV if x[8])}）")
    bidx = np.flatnonzero(bar.ravel()); b_day = bidx % n; b_mi = mi[b_day]; b_h = np.minimum(hdef.ravel()[bidx].astype(np.int64), 250)
    b_ex = excl.ravel()[bidx]
    ec, es, ed = E["cell"].astype(np.int64), E["s"].astype(np.int64), E["d"].astype(np.int64)
    e_mi = mi[ed]; e_ex = excl[es, ed]
    CODES = 7

    def base_counts(qf, rowmask=None):
        keep = qf > 0
        if rowmask is not None:
            keep &= rowmask
        key = (qf[keep].astype(np.int64) * NM + b_mi[keep]) * 251 + b_h[keep]
        c = np.bincount(key, minlength=CODES * NM * 251).reshape(CODES, NM, 251)
        ge = np.cumsum(c[:, :, ::-1], axis=2)[:, :, ::-1]
        return ge[:, :, list(S5.HS)]                                                   # (CODES, NM, 25)

    def ev_counts(code_e, w=None, evmask=None):
        keep = code_e > 0
        if evmask is not None:
            keep &= evmask
        key = (code_e[keep].astype(np.int64) * S5.NC + ec[keep]) * NM + e_mi[keep]
        return np.bincount(key, weights=None if w is None else w[keep], minlength=CODES * S5.NC * NM).reshape(CODES, S5.NC, NM)

    # ═══ A. ①② 全部級距 × 250 格 × 三段 ═══
    rows = []
    cellsA = {}
    for fi_ in sorted({x[0] for x in LV}):
        q = Q[fi_]; qf = q.ravel()[bidx]
        NC_ = base_counts(qf)                                                           # (CODES, NM, 25)
        code_e = q[es, ed]
        EC_ = ev_counts(code_e)                                                         # (CODES, NC, NM)
        nrow = NC_[:, :, HI_OF_CELL].transpose(0, 2, 1)                                  # (CODES, NC, NM)
        eall = EC_[1:].sum(0); nall = nrow[1:].sum(0)
        for lv in [x for x in LV if x[0] == fi_]:
            code = lv[2]
            for sg in S5.SEG:
                sm = segm[sg]
                if sg == "早年" and not lv[7]:
                    continue
                e = EC_[code][:, sm].astype(float); nn = nrow[code][:, sm].astype(float)
                if nn.sum() == 0:
                    continue
                lift, lo, hi, cov = ratio_stats(e, nn, eall[:, sm].astype(float), nall[:, sm].astype(float), e.sum(1), eall[:, sm].sum(1).astype(float), Z95)
                cellsA[(lv[1], code, sg)] = (lift, lo, hi, cov, e.sum(1), nn.sum(1))
    log(f"[①②] 完成 {time.time() - T0:.0f}s")

    def lvname(lv):
        return f"{lv[4]}｜{lv[3]}"
    # 挑選（探索）
    PK = []
    for lv in LV:
        r = cellsA.get((lv[1], lv[2], "探索"))
        if r is None or not lv[8]:
            continue
        lift, lo, hi, cov, ev, nn = r
        npass = int(np.sum((lo > 1) & (cov >= 0.05)))
        if npass >= HALF:
            PK.append(lv)
    k = len(PK); zB = NormalDist().inv_cdf(1 - 0.025 / max(k, 1))
    log(f"[挑選] 探索段進確認段 {k} 個級距｜Bonferroni z＝{zB:.3f}")
    # 確認段以 Bonferroni 重算 lo
    for lv in PK:
        fi_ = lv[0]; q = Q[fi_]; qf = q.ravel()[bidx]
        NC_ = base_counts(qf); code_e = q[es, ed]; EC_ = ev_counts(code_e)
        nrow = NC_[:, :, HI_OF_CELL].transpose(0, 2, 1); eall = EC_[1:].sum(0); nall = nrow[1:].sum(0)
        sm = segm["確認"]; code = lv[2]
        e = EC_[code][:, sm].astype(float); nn = nrow[code][:, sm].astype(float)
        cellsA[(lv[1], code, "確認B")] = ratio_stats(e, nn, eall[:, sm].astype(float), nall[:, sm].astype(float), e.sum(1), eall[:, sm].sum(1).astype(float), zB) + (e.sum(1), nn.sum(1))
        # 買不買得到版（剔除 t＋1 無成交／鎖死／處置中）
        NCx = base_counts(qf, ~b_ex); ECx = ev_counts(code_e, evmask=~e_ex)
        nrx = NCx[:, :, HI_OF_CELL].transpose(0, 2, 1); eax = ECx[1:].sum(0); nax = nrx[1:].sum(0)
        for sg in ("探索", "確認"):
            sm = segm[sg]; e = ECx[code][:, sm].astype(float); nn = nrx[code][:, sm].astype(float)
            cellsA[(lv[1], code, sg + "_可買")] = ratio_stats(e, nn, eax[:, sm].astype(float), nax[:, sm].astype(float), e.sum(1), eax[:, sm].sum(1).astype(float), zB if sg == "確認" else Z95) + (e.sum(1), nn.sum(1))
    # 輸出 ①② 全表
    recs = []
    for (col, code, sg), (lift, lo, hi, cov, ev, nn) in cellsA.items():
        for c in range(S5.NC):
            recs.append((col, code, sg, S5.cell_name(c), float(lift[c]), float(lo[c]), float(hi[c]), float(cov[c]), int(ev[c]), int(nn[c])))
    A = pd.DataFrame(recs, columns=["欄", "碼", "段", "格", "提升", "下緣", "上緣", "涵蓋率", "事件", "定義域列"])
    A.to_csv(os.path.join(S5.OUT, "feat_cells.csv.gz"), index=False, float_format="%.5g")
    del A, recs
    SUMR = []
    for lv in LV:
        r = {"欄": lv[1], "碼": lv[2], "特徵": lvname(lv), "類別": lv[5], "型態": lv[6], "進挑選": lv[8], "進確認段": lv in PK}
        for sg in ("探索", "確認", "早年", "確認B", "探索_可買", "確認_可買"):
            x = cellsA.get((lv[1], lv[2], sg))
            if x is None:
                r[f"{sg}_無資料"] = True if sg == "早年" and not lv[7] else None
                continue
            lift, lo, hi, cov, ev, nn = x
            r[f"{sg}_提升中位"] = float(np.nanmedian(lift)); r[f"{sg}_涵蓋率中位"] = float(np.nanmedian(cov))
            r[f"{sg}_下緣>1格數"] = int(np.sum(lo > 1)); r[f"{sg}_提升>1格數"] = int(np.sum(lift > 1))
            r[f"{sg}_下緣>1且涵蓋≥5%格數"] = int(np.sum((lo > 1) & (cov >= 0.05)))
            r[f"{sg}_H60g100_提升"] = float(lift[S5.cell_of(5, 1)]); r[f"{sg}_H60g100_下緣"] = float(lo[S5.cell_of(5, 1)]); r[f"{sg}_H60g100_涵蓋率"] = float(cov[S5.cell_of(5, 1)])
        if lv in PK:
            r["站得住（確認，Bonferroni）"] = bool(r.get("確認B_下緣>1格數", 0) >= HALF)
            if not r.get("早年_無資料"):
                r["早年方向"] = "同向" if r.get("早年_提升>1格數", 0) >= HALF else "相反或不一致"
        SUMR.append(r)
    SUMR = pd.DataFrame(SUMR)
    log(f"[確認] 站得住 {int(SUMR.get('站得住（確認，Bonferroni）', pd.Series(dtype=bool)).fillna(False).sum())} 個")
    # ═══ C. ③ 可交易曲線 ═══
    Rm = np.load(os.path.join(S5.WORK, "R.npy"), mmap_mode="r")
    r20 = np.load(os.path.join(S5.WORK, "r20c.npy"))
    R5 = np.asarray(Rm[0]).ravel()[bidx]; r20f = r20.ravel()[bidx]
    ok10 = np.isfinite(R5) & np.isfinite(r20f)
    dec = np.full(len(bidx), -1, np.int64)
    order = np.argsort(b_day, kind="stable")
    bd_sorted = b_day[order]; starts = np.searchsorted(bd_sorted, np.arange(n)); ends = np.searchsorted(bd_sorted, np.arange(n), side="right")
    for t in range(n):
        ix = order[starts[t]:ends[t]]
        if len(ix) == 0:
            continue
        v = np.where(ok10[ix], r20f[ix], np.nan)
        dec[ix] = AV.deciles(v)
    log(f"[③] 基準② 十分位完成 {time.time() - T0:.0f}s")
    fis = sorted({x[0] for x in LV})
    ACC = {k_: np.zeros((len(fis), len(S5.HOLD), CODES, NM)) for k_ in ("n1", "s1", "n2", "s2", "nr", "sr")}
    ALL = {k_: np.zeros((len(S5.HOLD), NM)) for k_ in ("nr", "sr", "n2", "s2")}
    Qf = {fi_: Q[fi_].ravel()[bidx] for fi_ in fis}
    for j, hh in enumerate(S5.HOLD):
        r = np.asarray(Rm[j]).ravel()[bidx].astype(np.float64); fin = np.isfinite(r)
        sd = np.bincount(b_day[fin], r[fin], minlength=n); cd = np.bincount(b_day[fin], minlength=n)
        x1 = np.full(len(r), np.nan); m1 = fin & (cd[b_day] > 1)
        x1[m1] = r[m1] - (sd[b_day[m1]] - r[m1]) / (cd[b_day[m1]] - 1)
        k2 = b_day * 10 + dec; m2 = fin & (dec >= 0)
        s2 = np.bincount(k2[m2], r[m2], minlength=n * 10); c2 = np.bincount(k2[m2], minlength=n * 10)
        x2 = np.full(len(r), np.nan); m2 &= c2[np.where(dec >= 0, k2, 0)] > 1
        x2[m2] = r[m2] - (s2[k2[m2]] - r[m2]) / (c2[k2[m2]] - 1)
        rn = r - S5.COST
        ALL["nr"][j] = np.bincount(b_mi[fin], minlength=NM); ALL["sr"][j] = np.bincount(b_mi[fin], rn[fin], minlength=NM)
        ALL["n2"][j] = np.bincount(b_mi[m2], minlength=NM); ALL["s2"][j] = np.bincount(b_mi[m2], x2[m2], minlength=NM)
        for a, fi_ in enumerate(fis):
            qf = Qf[fi_]
            for nk, sk, mk_, val in (("n1", "s1", m1, x1), ("n2", "s2", m2, x2), ("nr", "sr", fin, rn)):
                kk = mk_ & (qf > 0)
                key = qf[kk].astype(np.int64) * NM + b_mi[kk]
                ACC[nk][a, j] = np.bincount(key, minlength=CODES * NM).reshape(CODES, NM)
                ACC[sk][a, j] = np.bincount(key, val[kk], minlength=CODES * NM).reshape(CODES, NM)
        if j % 10 == 0:
            log(f"[③] h＝{hh} {time.time() - T0:.0f}s")
    fpos = {fi_: a for a, fi_ in enumerate(fis)}
    CUR = []

    def cstat(nm_, sm_, z):
        nn = nm_[0][..., sm_]; ss = nm_[1][..., sm_]
        N = nn.sum(-1)
        with np.errstate(invalid="ignore", divide="ignore"):
            mu = ss.sum(-1) / N
            se = np.sqrt(((ss - mu[..., None] * nn) ** 2).sum(-1)) / N
        return mu, mu - z * se, mu + z * se, N
    for sg in S5.SEG:
        sm = segm[sg]
        mu, lo, hi, N = cstat((ALL["nr"], ALL["sr"]), sm, Z95)
        mu2, lo2, hi2, N2 = cstat((ALL["n2"], ALL["s2"]), sm, Z95)
        for j, hh in enumerate(S5.HOLD):
            CUR.append({"欄": "全體", "碼": 0, "特徵": "全體", "段": sg, "h": hh, "淨報酬": mu[j], "淨報酬_下": lo[j], "淨報酬_上": hi[j], "n": int(N[j]), "對基準②": mu2[j]})
    for lv in LV:
        a = fpos[lv[0]]; code = lv[2]
        for sg in S5.SEG:
            if sg == "早年" and not lv[7]:
                continue
            z = (NormalDist().inv_cdf(1 - 0.025 / max(k, 1)) if (sg == "確認" and lv in PK) else Z95)
            sm = segm[sg]
            o1 = cstat((ACC["n1"][a, :, code], ACC["s1"][a, :, code]), sm, z)
            o2 = cstat((ACC["n2"][a, :, code], ACC["s2"][a, :, code]), sm, z)
            orr = cstat((ACC["nr"][a, :, code], ACC["sr"][a, :, code]), sm, z)
            for j, hh in enumerate(S5.HOLD):
                CUR.append({"欄": lv[1], "碼": code, "特徵": lvname(lv), "段": sg, "h": hh, "對全體": o1[0][j], "對全體_下": o1[1][j], "對全體_上": o1[2][j],
                            "對基準②": o2[0][j], "對基準②_下": o2[1][j], "對基準②_上": o2[2][j], "淨報酬": orr[0][j], "淨報酬_下": orr[1][j], "淨報酬_上": orr[2][j], "n": int(o2[3][j])})
    CUR = pd.DataFrame(CUR); CUR.to_csv(os.path.join(S5.OUT, "curves.csv.gz"), index=False, float_format="%.5g")

    def ranges(g):
        """對基準② 下緣 − 成本 ＞ 0 的持有天數，連續 ≥ 3 格才標。"""
        ok = (g["對基準②_下"].to_numpy() - S5.COST > 0); hs = g["h"].to_numpy(); out = []; i = 0
        while i < len(ok):
            if ok[i]:
                j = i
                while j + 1 < len(ok) and ok[j + 1]:
                    j += 1
                if j - i + 1 >= 3:
                    out.append(f"{hs[i]}～{hs[j]} 日")
                i = j + 1
            else:
                i += 1
        neg = (g["對基準②_上"].to_numpy() + S5.COST < 0)
        return "、".join(out) if out else "沒有", int(neg.sum())
    cg = CUR[CUR["欄"] != "全體"].groupby(["欄", "碼", "段"])
    RG = {kk: ranges(g.sort_values("h")) for kk, g in cg}
    for sg in S5.SEG:
        SUMR[f"{sg}_③買了賺的持有區間"] = [RG.get((c_, q_, sg), ("—", 0))[0] for c_, q_ in zip(SUMR["欄"], SUMR["碼"])]
        SUMR[f"{sg}_③顯著輸的格數"] = [RG.get((c_, q_, sg), ("—", 0))[1] for c_, q_ in zip(SUMR["欄"], SUMR["碼"])]
        for hh in (20, 60, 120, 250):
            g = CUR[(CUR["段"] == sg) & (CUR["h"] == hh)].set_index(["欄", "碼"])
            SUMR[f"{sg}_③對基準②_{hh}日"] = [g["對基準②"].get((c_, q_), np.nan) for c_, q_ in zip(SUMR["欄"], SUMR["碼"])]
    log(f"[③] 完成 {time.time() - T0:.0f}s")
    # ═══ D. 妖股特徵（S15）＋ E. 結束特徵（S16）：共用「挑→驗」═══
    def family(get_counts, tag):
        """get_counts(fi_) ⇒ (e_all_codes (CODES,NC,NM) 陽性, n_all_codes (CODES,NC,NM) 樣本)；回 (列表, 進確認段)。"""
        ST_ = {}; CF = {}
        for fi_ in fis:
            ea_, na_ = get_counts(fi_)
            eA = ea_[1:].sum(0); nA = na_[1:].sum(0)
            for lv in [v for v in LV if v[0] == fi_]:
                code = lv[2]
                for sg in S5.SEG:
                    if sg == "早年" and not lv[7]:
                        continue
                    sm = segm[sg]
                    e = ea_[code][:, sm].astype(float); nn = na_[code][:, sm].astype(float)
                    if nn.sum() == 0:
                        continue
                    ea = eA[:, sm].astype(float); na = nA[:, sm].astype(float)
                    st = ratio_stats(e, nn, ea, na, e.sum(1), ea.sum(1), Z95)
                    ST_[(lv, sg)] = (st[0], st[1], st[3], e.sum(1))
                    if sg == "確認":
                        CF[lv] = (e.astype(np.float32), nn.astype(np.float32), ea.astype(np.float32), na.astype(np.float32))
        pk = [lv for lv in LV if lv[8] and (lv, "探索") in ST_ and int(np.sum((ST_[(lv, "探索")][1] > 1) & (ST_[(lv, "探索")][2] >= 0.05))) >= HALF]
        zb = NormalDist().inv_cdf(1 - 0.025 / max(len(pk), 1))
        out = []
        for lv in LV:
            r = {**tag, "欄": lv[1], "碼": lv[2], "特徵": lvname(lv), "進確認段": lv in pk}
            for sg in S5.SEG:
                v = ST_.get((lv, sg))
                if v is None:
                    continue
                lift, lo, cov, es_ = v
                r[f"{sg}_提升中位"] = float(np.nanmedian(lift)); r[f"{sg}_涵蓋率中位"] = float(np.nanmedian(cov))
                r[f"{sg}_下緣>1且涵蓋≥5%格數"] = int(np.sum((lo > 1) & (cov >= 0.05))); r[f"{sg}_提升>1格數"] = int(np.sum(lift > 1))
                r[f"{sg}_陽性數"] = int(es_.sum())
            if lv in pk and lv in CF:
                e, nn, ea, na = (x.astype(float) for x in CF[lv])
                lift, lo, hi, cov = ratio_stats(e, nn, ea, na, e.sum(1), ea.sum(1), zb)
                r["確認_Bonferroni下緣>1格數"] = int(np.sum(lo > 1)); r["站得住（確認）"] = bool(r["確認_Bonferroni下緣>1格數"] >= HALF)
            out.append(r)
        return out, pk
    YR = []; YPK = {}
    for x in (30, 50, 70):
        hit = (E[f"dd{x}"] > 0).astype(float)

        def gc(fi_, hit=hit):
            code_e = Q[fi_][es, ed]
            return ev_counts(code_e, w=hit), ev_counts(code_e)
        rr, pk = family(gc, {"回落": f"{x}%"}); YR += rr; YPK[x] = pk
        log(f"[妖股] 回落 {x}%：進確認段 {len(pk)}（{time.time() - T0:.0f}s）")
    YR = pd.DataFrame(YR); YR.to_csv(os.path.join(S5.OUT, "yao_summary.csv"), index=False, float_format="%.5g")
    ER = []; EPK = {}
    Pv = E["P"].astype(np.int64)
    for x in (10, 20, 30):
        ended = E[f"dd{x}"] > 0
        for kk in S5.KEND:
            pos = Pv - kk; mid = ed + (Pv - ed) // 2
            ii = np.flatnonzero(ended & (pos > ed) & (Pv - mid > 20) & (mid > ed))
            cc = ec[ii]; mm_ = e_mi[ii]; ss = es[ii]; pp_ = pos[ii]; md_ = mid[ii]

            def gc(fi_, cc=cc, mm_=mm_, ss=ss, pp_=pp_, md_=md_):
                q = Q[fi_]; cp = q[ss, pp_].astype(np.int64); cq = q[ss, md_].astype(np.int64)
                kp = cp > 0; kq = cq > 0
                npos = np.bincount((cp[kp] * S5.NC + cc[kp]) * NM + mm_[kp], minlength=CODES * S5.NC * NM).reshape(CODES, S5.NC, NM)
                nctl = np.bincount((cq[kq] * S5.NC + cc[kq]) * NM + mm_[kq], minlength=CODES * S5.NC * NM).reshape(CODES, S5.NC, NM)
                return npos, npos + nctl
            rr, pk = family(gc, {"結束套": f"回落{x}%", "k": kk}); ER += rr; EPK[(x, kk)] = pk
            log(f"[結束] 回落 {x}% k＝{kk}：事件 {len(ii)}｜進確認段 {len(pk)}（{time.time() - T0:.0f}s）")
    ER = pd.DataFrame(ER); ER.to_csv(os.path.join(S5.OUT, "end_summary.csv"), index=False, float_format="%.5g")
    # ═══ N ═══
    nY = {x: len(v) for x, v in YPK.items()}; nE = {f"{x}_{kk}": len(v) for (x, kk), v in EPK.items()}
    NS = k + sum(nY.values()) + sum(nE.values())
    SUMR.to_csv(os.path.join(S5.OUT, "feat_summary.csv"), index=False, float_format="%.5g")
    SUM = {"分析開始": S5.START, "所用登錄": S5.SEQ, "g 網格": "照裁定 seq277", "執行者": "未看過 seq4 結果",
           "級距數": len(LV), "進挑選級距": sum(1 for x in LV if x[8]), "挑選門檻": f"探索段 250 格中 ≥ {HALF} 格「① 95% 下緣 ＞ 1 且 ② ≥ 5%」",
           "飆股特徵 進確認段": [f"{lvname(lv)}" for lv in PK], "Bonferroni k（飆股）": k,
           "站得住（飆股，確認）": SUMR.loc[SUMR.get("站得住（確認，Bonferroni）", pd.Series(False, index=SUMR.index)).fillna(False).astype(bool), "特徵"].tolist(),
           "妖股 進確認段": {f"{x}%": [lvname(lv) for lv in v] for x, v in YPK.items()},
           "妖股 站得住": {f"{x}%": YR[(YR["回落"] == f"{x}%") & YR.get("站得住（確認）", pd.Series(False, index=YR.index)).fillna(False).astype(bool)]["特徵"].tolist() for x in (30, 50, 70)},
           "結束 進確認段": {kk_: [lvname(lv) for lv in v] for kk_, v in {f"回落{x}%_k{kk}": v for (x, kk), v in EPK.items()}.items()},
           "結束 站得住": ER[ER.get("站得住（確認）", pd.Series(False, index=ER.index)).fillna(False).astype(bool)][["結束套", "k", "特徵"]].to_dict("records"),
           "N_單筆": NS, "N 組成": {"飆股": k, "妖股": nY, "結束": nE}, "耗時秒": round(time.time() - T0)}
    json.dump(SUM, open(os.path.join(S5.OUT, "summary_feat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] N_單筆 {NS}｜{json.dumps(SUM['N 組成'], ensure_ascii=False)}")
    report_feat(SUM, SUMR, YR, ER)
    page_feat(SUM, SUMR, YR, ER)
    log("[特徵] 報告、網頁完成")


R_ = lambda x: "—" if x is None or not isinstance(x, (int, float, np.floating)) or not np.isfinite(x) else f"{x:.2f}"
C_ = lambda x: "—" if x is None or not isinstance(x, (int, float, np.floating)) or not np.isfinite(x) else f"{x * 100:.1f}%"
I_ = lambda x: "—" if x is None or not isinstance(x, (int, float, np.integer, np.floating)) or not np.isfinite(x) else f"{int(x)}"


def _flag(df, col):
    return df[col].fillna(False).astype(bool) if col in df.columns else pd.Series(False, index=df.index)


def report_feat(SUM, SUMR, YR, ER):
    NL = "\n"
    L = ["# PREREG飆股回推 seq5 第二批：特徵（起漲前長什麼樣、買了賺不賺、妖股、結束）", "",
         f"> 分析開始 {SUM['分析開始']}｜所用登錄 {SUM['所用登錄']}｜g 網格照裁定 seq277｜執行者未看過 seq4 結果｜資料 main {S5.MAIN_SHA[:10]}＋早年 {S5.EARLY_SHA[:10]}（接合）｜讀法 S1～S17 見 researchSurge5.py 開頭", "",
         f"- 級距 {SUM['級距數']}（進挑選 {SUM['進挑選級距']}；使用者原門檻版本只描述）｜挑選門檻：{SUM['挑選門檻']}",
         f"- **N_單筆 ＝ {SUM['N_單筆']}**（組成 {json.dumps(SUM['N 組成'], ensure_ascii=False)}）；Bonferroni 各族用自己的 k", ""]
    P = SUMR[SUMR["進確認段"] == True].copy()
    P["_c"] = P["確認B_下緣>1格數"].fillna(0) if "確認B_下緣>1格數" in P.columns else 0
    P = P.sort_values(["_c", "探索_下緣>1且涵蓋≥5%格數"], ascending=False)
    L.append(f"## 一、飆股特徵：探索段進確認段 {len(P)} 個 ⇒ 確認段站得住 {len(SUM['站得住（飆股，確認）'])} 個"); L.append("")
    L.append("| 特徵 | 探索 過門檻格 | 探索 提升中位 | 探索 涵蓋中位 | 確認 Bonf 下緣>1 格 | 確認 提升中位 | 站得住 | 早年 提升>1 格 | 早年方向 | 確認 ③ 買了賺的持有區間 | 確認 ③ 對基準② 20／60／120／250 日 | 可買版 確認 Bonf 下緣>1 格 |")
    L.append("|---" * 12 + "|")
    for r in P.to_dict("records"):
        L.append(f"| {r['特徵']} | {I_(r.get('探索_下緣>1且涵蓋≥5%格數'))} | {R_(r.get('探索_提升中位'))} | {C_(r.get('探索_涵蓋率中位'))} | {I_(r.get('確認B_下緣>1格數'))} | {R_(r.get('確認_提升中位'))} | "
                 f"{'✅' if r.get('站得住（確認，Bonferroni）') is True else '✘'} | {'無資料' if r.get('早年_無資料') is True else I_(r.get('早年_提升>1格數'))} | {r.get('早年方向') if isinstance(r.get('早年方向'), str) else '—'} | "
                 f"{r.get('確認_③買了賺的持有區間', '—')} | {'／'.join(C_(r.get(f'確認_③對基準②_{h}日')) for h in (20, 60, 120, 250))} | {I_(r.get('確認_可買_下緣>1格數'))} |")
    L.append(""); L.append("## 二、使用者原門檻版本（只描述，⛔ 不進挑選）"); L.append("")
    L.append("| 特徵 | 探索 提升中位 | 探索 涵蓋中位 | 探索 下緣>1且涵蓋≥5% 格 | 確認 提升中位 | 確認 下緣>1 格 | 早年 提升中位 | 確認 ③ 對基準② 60 日 | 確認 ③ 買了賺區間 |"); L.append("|---" * 9 + "|")
    for r in SUMR[SUMR["進挑選"] == False].to_dict("records"):
        L.append(f"| {r['特徵']} | {R_(r.get('探索_提升中位'))} | {C_(r.get('探索_涵蓋率中位'))} | {I_(r.get('探索_下緣>1且涵蓋≥5%格數'))} | {R_(r.get('確認_提升中位'))} | {I_(r.get('確認_下緣>1格數'))} | "
                 f"{'無資料' if r.get('早年_無資料') is True else R_(r.get('早年_提升中位'))} | {C_(r.get('確認_③對基準②_60日'))} | {r.get('確認_③買了賺的持有區間', '—')} |")
    L.append(""); L.append("## 三、妖股特徵（飆股事件內，對「高點後回落 x%」）"); L.append("")
    for x in (30, 50, 70):
        g = YR[(YR["回落"] == f"{x}%") & (YR["進確認段"] == True)]
        okk = g[_flag(g, "站得住（確認）")]
        L.append(f"- 回落 {x}%：進確認段 {len(g)} 個；站得住 {len(okk)} 個" + (f"：{'、'.join(okk['特徵'])}" if len(okk) else ""))
        for r in g.to_dict("records"):
            L.append(f"  - {r['特徵']}：探索 過門檻 {I_(r.get('探索_下緣>1且涵蓋≥5%格數'))} 格、提升中位 {R_(r.get('探索_提升中位'))}｜確認 Bonf 下緣>1 {I_(r.get('確認_Bonferroni下緣>1格數'))} 格、提升中位 {R_(r.get('確認_提升中位'))}")
    L.append(""); L.append("## 四、結束特徵（高點前 k 日 對 同一段漲勢中段）"); L.append("")
    for (x, kk), g in ER.groupby(["結束套", "k"]):
        g2 = g[g["進確認段"] == True]; okk = g2[_flag(g2, "站得住（確認）")]
        L.append(f"- {x}、k＝{kk}：進確認段 {len(g2)} 個；站得住 {len(okk)} 個" + (f"：{'、'.join(okk['特徵'])}" if len(okk) else ""))
    L.append(""); L.append("檔案：feat_summary.csv（每個級距一列）｜feat_cells.csv.gz（級距 × 250 格 × 段 的 ①②）｜curves.csv.gz（③ 5～250 日曲線）｜yao_summary.csv｜end_summary.csv｜summary_feat.json")
    open(os.path.join(S5.OUT, "REPORT_feat.md"), "w", encoding="utf-8").write(NL.join(L) + NL)


def page_feat(SUM, SUMR, YR, ER):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.ok{background:#e8f5e9}td.l,th.l{text-align:left}small{color:#666}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>飆股回推 第二批</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股回推（seq5）第二批：起漲前長什麼樣、買了賺不賺</h1>",
         f"<p class='lead'>分析開始 {SUM['分析開始']}，照登錄 {SUM['所用登錄']}；漲幅網格照裁定 seq277；執行者沒看過上一版結果。</p>",
         "<p class='note'>每個特徵分五組（或是／否），在 250 種飆股定義（10～250 天內漲 50%～10 倍）各算一次：<b>提升倍數</b>＝有這特徵的股票變飆股的機率是一般的幾倍；"
         "<b>涵蓋率</b>＝飆股裡事先有這特徵的佔幾成。2017–21 至少一半定義裡「提升倍數確定 ＞ 1、涵蓋率 ≥ 5%」才挑出來，2022–26 再驗（一起比的校正版）。"
         "<b>買了賺不賺</b>＝隔天開盤買、抱 5～250 天，比前 20 天漲跌差不多的股票多賺，而且多出來的要大於來回成本 0.585%。</p>",
         f"<p class='note'>檢定數 N＝{SUM['N_單筆']}。</p>"]
    P = SUMR[SUMR["進確認段"] == True].copy()
    okf = _flag(P, "站得住（確認，Bonferroni）")
    H.append(f"<h2>一、2017–21 挑出 {len(P)} 個，2022–26 站得住 {int(okf.sum())} 個</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>提升倍數（中位）<br>17–21／22–26</th><th>涵蓋率</th><th>站得住</th><th>買了賺（22–26）</th><th>2005–14</th></tr>")
    P["_c"] = P["確認B_下緣>1格數"].fillna(0) if "確認B_下緣>1格數" in P.columns else 0
    for r in P.sort_values("_c", ascending=False).to_dict("records"):
        st = r.get("站得住（確認，Bonferroni）") is True
        H.append(f"<tr class='{'ok' if st else ''}'><td class='l'>{html.escape(r['特徵'])}</td><td>{R_(r.get('探索_提升中位'))}／{R_(r.get('確認_提升中位'))}</td><td>{C_(r.get('確認_涵蓋率中位'))}</td>"
                 f"<td>{'✅' if st else '✘'}<br><small>{I_(r.get('確認B_下緣>1格數'))}/250</small></td><td>{html.escape(str(r.get('確認_③買了賺的持有區間', '—')))}</td>"
                 f"<td>{'無資料' if r.get('早年_無資料') is True else html.escape(str(r.get('早年方向', '—')))}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>二、你給的原門檻（只描述）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>提升倍數 17–21／22–26</th><th>涵蓋率</th><th>買了賺（22–26）</th></tr>")
    for r in SUMR[SUMR["進挑選"] == False].to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{R_(r.get('探索_提升中位'))}／{R_(r.get('確認_提升中位'))}</td><td>{C_(r.get('確認_涵蓋率中位'))}</td><td>{html.escape(str(r.get('確認_③買了賺的持有區間', '—')))}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>三、妖股與結束</h2><div class='wrap'><table><tr><th class='l'>族</th><th>挑出</th><th>站得住</th></tr>")
    for x in (30, 50, 70):
        g = YR[(YR["回落"] == f"{x}%") & (YR["進確認段"] == True)]; okk = g[_flag(g, "站得住（確認）")]
        H.append(f"<tr><td class='l'>高點後跌 {x}%</td><td>{len(g)}</td><td>{html.escape('、'.join(okk['特徵'])) or '沒有'}</td></tr>")
    for (x, kk), g in ER.groupby(["結束套", "k"]):
        g2 = g[g["進確認段"] == True]; okk = g2[_flag(g2, "站得住（確認）")]
        H.append(f"<tr><td class='l'>結束（{x}）高點前 {kk} 天</td><td>{len(g2)}</td><td>{html.escape('、'.join(okk['特徵'])) or '沒有'}</td></tr>")
    H.append("</table></div></main></body></html>")
    open(os.path.join(S5.OUT, "飆股回推seq5_第二批_20260929.html"), "w", encoding="utf-8").write("\n".join(H))

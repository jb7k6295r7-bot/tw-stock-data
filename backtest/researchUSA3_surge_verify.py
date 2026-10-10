# -*- coding: utf-8 -*-
"""USREG-A3-17 驗證段（裁定 seq321 §二 Q1）：只驗探索段挑出的【結束族 9 個】級距，驗證段 2024-01-02～2026-09-30；N 9。
飆股族、妖股族探索段挑出 0 個 ⇒ 依裁定結案、本檔不做。⛔ 不改 researchUSA3_surge.py 與 resultsUSA34/A3/ 既有檔；結果只寫 A3-17_verify.json（新檔）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_surge_verify --run [--procs 3]
    ...                                                                                                  --check

判準：台股 PREREG飆股回推 seq7（sha 15a22c6b6c2c36d0）§十之五「驗（確認段）：同一條件（至少一半格子 ① CI 下緣 ＞ 1，Bonferroni ＝ 進確認段的特徵數）
      ⇒ 站得住」、§十之六 結束特徵「挑與驗同十之五」、§十一 近年版（找 2021～2023、驗 2024～）；
      台股執行讀法 researchSurge6 U6（Bonferroni 各族用自己的 k）＋ researchSurge5 S12（確認段 ≥125 格「① Bonferroni 下緣 ＞ 1」⇒ 站得住，② 照報）、S19（結束可交易）；
      美股探索段讀法 researchUSA3_surge.py G1～G10（台北 2026-10-07 11:55 寫死）一律沿用。

═══ 驗證段補讀法（V 標；⭐ 寫死於 2026-10-10 23:17（台北），寫死前 ⛔ 沒看任何驗證段（2024 起）起漲日、提升倍數或報酬）═══
 V1 段：驗證段起漲日 t ∈ [2024-01-02, 2026-09-30]；資料尾 ＝ 2026-09-30（G3 同；hdef ＝ min(250, 資料尾−t, 下一個壞根−1−t)）。
    事件鏈自 2021-01-04 起算、跨探索／驗證交界不重起（台股 seq6 U4「交界不重起」）⇒ 用 researchUSA3_surge.build_events 一次建到 2026-09-30，再取 t ≥ 2024-01-02 的事件。
 V2 特徵、五等分、母體、壞根、P、回落、結束族陽性（P−k）與對照（漲勢中段）一律照 G1～G6 原式（直接 import researchUSA3_surge.stock／qtie／ratio_stats）；
    只算 9 個級距用到的 4 個欄（rsi14、kdrun、dhi_60、dhi_120；都是同日橫斷面五等分，單欄算與全欄算相同）。
 V3 判定（S12＋U6）：各族（回落 x%｜P−k 日）用自己的 Bonferroni k ＝ 該族探索段挑出數（回落30%｜P−1 ＝ 3，其餘各 1）、z ＝ Φ⁻¹(1 − 0.025／k)；
    驗證段 250 格中 ≥ 125 格「① Bonferroni 下緣 ＞ 1」⇒「站得住」，否則「沒站住」；② 涵蓋率照報、⛔ 不進判定（S12 原式）。
    月分群依 t 的曆月（驗證段 33 個月）。另報「總 N＝9 的 Bonferroni」與「95% 且 ② ≥ 5%（探索段挑選式）」兩種格數（描述，⛔ 不改判定）。
 V4 三欄：合併 ＝ 判定；只 S&P 400、只 S&P 500 ＝ 事件 t 當天歸屬（G1、C3）同式只報格數（描述）。
 V5 重現閘：同一次建出的特徵與事件，用探索段（t ≤ 2023-12-29、95%、② ≥ 5%）重算這 9 個級距的「過門檻格數」必須逐一等於 A3-17.json 的值；不等 ⇒ 不出判定。
 V6 結束可交易（S19，描述＋驗證段標區間）：只對「站得住」的級距做；對象 ＝ 驗證段所有格事件的 (股, t) 聯集；t＋1 開盤買；
    規則 A ＝ 持有中該級距第一次出現於 d（t ＜ d ≤ t＋h−1）⇒ d 之後第一個有效開盤賣；規則 B ＝ 抱到 t＋h 收盤；h ＝ 5～250（每 5）；
    B 需 t＋h ≤ 2026-09-30、(t, t＋h] 無壞根、t＋1 有效開盤；A−B 月分群 CI（Bonferroni k ＝ 站得住的不同級距數），連續 ≥ 3 格下緣 ＞ 0 ⇒「一出現就賣較好」、上緣 ＜ 0 ⇒「續抱較好」。
    沒有級距站得住 ⇒ 不算（照實寫）。
 V7 |ret|＞50%：資料庫已逐筆確認（假的已在 ret_blank.csv 留空）⇒ 不再做 G9 敏感度；另計驗證段事件是否碰到 ret_blank.csv 列（只計數）。
 V8 先驗：台股先驗 ①～④ 針對確認段（台股 seq5／seq6 確認段結束特徵：一出現就賣全輸續抱）⇒ 本件照報對錯（「結束特徵站得住」先驗方向＝台股站得住的級距數），只描述。
 V9 輸出只有彙總（級距 × 格數、網格中位、涵蓋率、站得住與否）；逐筆事件、Q 只在 ~/us_work/c/a317/（repo 外，列 sha）。
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_surge as S      # noqa: E402
C = S.C
U = S.U

READ_TS = "2026-10-10 23:17（台北）"
VAL0 = pd.Timestamp("2024-01-02")
WORKV = os.path.expanduser("~/us_work/c/a317")
OUTF = os.path.join(C.OUT, "A3-17_verify.json")
HOLD = tuple(range(5, 251, 5))
_FI: list = []


def picks():
    """A3-17.json 探索段挑出（合併）⇒ [(族名, x, k, 欄, 碼, 探索過門檻格數, 探索網格中位提升, 探索涵蓋率中位)]。"""
    d = json.load(open(os.path.join(C.OUT, "A3-17.json"), encoding="utf-8"))
    out = []
    for fam, lst in d["挑出（合併）"].items():
        if not lst:
            continue
        assert fam.startswith("結束"), fam
        x = int(fam.split("回落")[1].split("%")[0]); k = int(fam.split("P−")[1].split("日")[0])
        for p in lst:
            out.append((fam, x, k, p["欄"], int(p["碼"]), int(p["過門檻格數"]), float(p["網格中位提升"]), float(p["涵蓋率中位"])))
    assert len(out) == 9 and d["N_待裁定"] == 9, len(out)
    return out


def vstock(t):
    r = S.stock(t)
    if r is None:
        return None
    r["F"] = r["F"][_FI].copy()
    r.pop("E50", None); r.pop("hdef50", None)
    return r


def _init2(G, fi):
    S._init(G)
    _FI[:] = fi


def build(procs):
    meta, ST = C.load_cache()
    cal, w1 = meta["cal"], meta["w1"]; n = len(cal)
    p0 = int(cal.searchsorted(S.SURGE0)); pX = w1; pE = w1
    assert cal[p0] == S.SURGE0
    PK = picks()
    cols = sorted({p[3] for p in PK})
    fi = [S.FIX[c] for c in cols]
    SH, SPL = S.load_shares()
    MK, M200, TR = S.market(cal)
    G = {"cal": cal, "cald": cal.values.astype("datetime64[D]").astype(np.int64), "n": n, "p0": p0, "pX": pX, "pE": pE, "w1": w1,
         "ST": ST, "SH": SH, "SPL": SPL, "MKTQ": MK, "MKT200": M200, "TR": TR, "SEC": S.load_sectors()}
    _init2(G, fi)
    t0 = time.time(); res = []
    with Pool(procs, initializer=_init2, initargs=(G, fi)) as pool:
        for k, r in enumerate(pool.imap(vstock, sorted(ST), chunksize=4)):
            if r is not None:
                res.append(r)
            if (k + 1) % 200 == 0:
                print("[verify] %d／%d %.0fs" % (k + 1, len(ST), time.time() - t0), flush=True)
    return meta, ST, cal, p0, pX, pE, res, cols, PK


def qcols(F, bar):
    nc, S_, nd = F.shape
    Q = np.zeros((nc, S_, nd), np.int8)
    for c in range(nc):
        X = F[c]
        for t in range(nd):
            b_ = bar[:, t]
            if b_.any():
                Q[c, b_, t] = S.qtie(X[b_, t])
    return Q


def fam_counts(Q, ci, E, x, kk, evmask, emon, NM):
    """結束族（G6 原式）：陽性 P−k、對照漲勢中段；→ (ea_, na_) 形狀 (7, NC, NM)。"""
    ec, es, ed, EP = E["cell"], E["s"], E["d"], E["P"]
    ended = E[f"dd{x}"] > 0
    pos = EP - kk; mid = ed + (EP - ed) // 2
    ii = np.flatnonzero(ended & (pos > ed) & (EP - mid > 20) & (mid > ed) & evmask)
    cc = ec[ii]; mm_ = emon[ii]; ss = es[ii]; pp_ = pos[ii]; md_ = mid[ii]
    q = Q[ci]; cp = q[ss, pp_].astype(np.int64); cq = q[ss, md_].astype(np.int64)
    cel = np.r_[cc, cc]; mon = np.r_[mm_, mm_]; code = np.r_[cp, cq]; y = np.r_[np.ones(len(cp)), np.zeros(len(cq))]
    keep = code > 0
    key = (code[keep] * S.NC + cel[keep]) * NM + mon[keep]
    ea_ = np.bincount(key, weights=y[keep], minlength=7 * S.NC * NM).reshape(7, S.NC, NM)
    na_ = np.bincount(key, minlength=7 * S.NC * NM).reshape(7, S.NC, NM)
    return ea_, na_, len(ii)


def stats(ea_, na_, code, z):
    e = ea_[code].astype(float); nn = na_[code].astype(float)
    eA = ea_[1:].sum(0).astype(float); nA = na_[1:].sum(0).astype(float)
    lift, lo, hi, cov = S.ratio_stats(e, nn, eA, nA, e.sum(1), eA.sum(1), z)
    ok = np.isfinite(lift)
    return {"lift": lift, "lo": lo, "cov": cov,
            "提升中位": float(np.nanmedian(lift)) if ok.any() else None, "提升p10": float(np.nanpercentile(lift, 10)) if ok.any() else None,
            "提升p90": float(np.nanpercentile(lift, 90)) if ok.any() else None,
            "涵蓋率中位": float(np.nanmedian(cov)) if np.isfinite(cov).any() else None,
            "下緣>1格數": int(np.sum(lo > 1)), "下緣>1且涵蓋≥5%格數": int(np.sum((lo > 1) & (cov >= 0.05))),
            "陽性列數": int(e.sum()), "有特徵列數": int(nn.sum())}


def endtrade(Q, ci, code, ST, sids, cal, p0, v0, w1, res_ev, mi_v, NM, z):
    """V6（S19）：驗證段事件 (股, t) 聯集；A−B 逐 h。"""
    key = np.unique(res_ev["s"] * 100000 + res_ev["d"])
    SS, TT = key // 100000, key % 100000
    NH = len(HOLD)
    acc_n = np.zeros((NH, NM)); acc_s = np.zeros((NH, NM)); acc_hit = np.zeros((NH, NM))
    for s in np.unique(SS):
        d = ST[sids[int(s)]]
        o = d["opens"]; cf = d["closes"]; pb = d["pb"]; n = len(o)
        okop = np.isfinite(o) & (o > 0)
        nxo = np.full(n + 2, n + 10, np.int64)
        for p in range(n - 1, -1, -1):
            nxo[p] = p if okop[p] else nxo[p + 1]
        cpb = np.r_[0, np.cumsum(pb)]
        qrow = np.zeros(n, np.int8); qrow[p0:p0 + Q.shape[2]] = Q[ci, int(s)]
        sig = np.flatnonzero(qrow == code)
        for tt in TT[SS == s]:
            t = int(tt) + p0
            if not (t + 1 < n and okop[t + 1]):
                continue
            ob = o[t + 1]
            j = np.searchsorted(sig, t + 1)
            dsig = int(sig[j]) if j < len(sig) else n + 10
            ex = int(nxo[min(dsig + 1, n + 1)]) if dsig < n else n + 10
            m_ = mi_v[int(tt)]
            for hj, hh in enumerate(HOLD):
                if t + hh > w1 or cpb[t + hh + 1] - cpb[t + 1] > 0:
                    continue
                B = cf[t + hh] / ob - 1
                early = (dsig <= t + hh - 1) and (ex <= t + hh)
                A = (o[ex] / ob - 1) if early else B
                acc_n[hj, m_] += 1; acc_s[hj, m_] += A - B; acc_hit[hj, m_] += float(early)
    rows = []
    for hj, hh in enumerate(HOLD):
        nn = acc_n[hj]; ss = acc_s[hj]; N = nn.sum()
        if N == 0:
            rows.append({"h": hh, "n": 0}); continue
        mu = ss.sum() / N; se = np.sqrt(((ss - mu * nn) ** 2).sum()) / N
        rows.append({"h": hh, "n": int(N), "A−B": mu, "下": mu - z * se, "上": mu + z * se, "訊號已出現比例": acc_hit[hj].sum() / N})
    return rows


def _rng(ok, hs):
    out = []; i = 0
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
    return "、".join(out) if out else "沒有"


def run(procs=3):
    T0 = time.time()
    meta, ST, cal, p0, pX, pE, res, cols, PK = build(procs)
    sids = [r["t"] for r in res]; Sn = len(sids); nd = pE - p0 + 1
    F = np.empty((len(cols), Sn, nd), np.float32)
    for si, r in enumerate(res):
        F[:, si, :] = r["F"]; r["F"] = None
    bar = np.stack([r["bar"] for r in res]); m4 = np.stack([r["m4"] for r in res])
    Q = qcols(F, bar); del F
    print("[verify] 特徵＋五等分 %.0fs" % (time.time() - T0), flush=True)
    rows = []
    for si, r in enumerate(res):
        for e in r["E"]:
            rows.append((e[0], si, e[1] - p0, e[2] - p0, *e[3:]))
    a = np.array(rows, np.int64)
    E = {"cell": a[:, 0], "s": a[:, 1], "d": a[:, 2], "P": a[:, 3], **{f"dd{x}": a[:, 4 + i] for i, x in enumerate((10, 20, 30, 50, 70))}}
    days = cal[p0:pE + 1]
    v0 = int(cal.searchsorted(VAL0)) - p0
    xend = int(cal.searchsorted(S.EXP_LAST, side="right")) - 1 - p0
    assert days[v0] == VAL0
    # ── V5 重現閘：探索段事件 ＝ events_explore.npz；9 級距過門檻格數 ＝ A3-17.json ──
    z0 = np.load(os.path.join(S.WORKS, "events_explore.npz"))
    exm = E["d"] <= xend
    old = set(zip([str(x) for x in z0["sids"][z0["s"]]], z0["cell"].tolist(), z0["d"].tolist(), z0["P"].tolist()))
    new = set(zip([sids[i] for i in E["s"][exm]], E["cell"][exm].tolist(), E["d"][exm].tolist(), E["P"][exm].tolist()))
    gate_ev = {"探索段事件數（本次）": int(exm.sum()), "探索段事件數（events_explore.npz）": int(len(z0["cell"])), "集合相同": old == new}
    mon_all = np.array([d.year * 12 + d.month for d in days])
    mi_x = (mon_all - mon_all.min()).astype(np.int64); NMx = int(mi_x[:xend + 1].max()) + 1
    emon_x = np.minimum(mi_x[E["d"]], NMx - 1)
    gate = []
    for fam, x, kk, col, code, ncell, lift0, cov0 in PK:
        ci = cols.index(col)
        ea_, na_, _ = fam_counts(Q, ci, E, x, kk, exm, emon_x, NMx)
        st = stats(ea_, na_, code, S.Z95)
        gate.append({"族": fam, "級距": f"{col}｜Q{code}", "探索過門檻格數（本次）": st["下緣>1且涵蓋≥5%格數"], "A3-17.json": ncell,
                     "相同": st["下緣>1且涵蓋≥5%格數"] == ncell})
    gate_ok = gate_ev["集合相同"] and all(g["相同"] for g in gate)
    print("[verify] 重現閘 %s %s" % (gate_ok, json.dumps(gate_ev, ensure_ascii=False)), flush=True)
    if not gate_ok:
        C.jdump({"⛔": "重現閘不過，不出判定", "事件": gate_ev, "級距": gate}, os.path.join(WORKV, "gate_fail.json"))
        raise SystemExit("重現閘不過")
    # ── 驗證段 ──
    vm = E["d"] >= v0
    mi_v = np.maximum(mon_all - (VAL0.year * 12 + VAL0.month), 0).astype(np.int64); NMv = int(mi_v.max()) + 1
    emon_v = mi_v[E["d"]]
    m4ev = m4[E["s"], E["d"]]
    famk = {}
    for p in PK:
        famk[p[0]] = famk.get(p[0], 0) + 1
    zN = NormalDist().inv_cdf(1 - 0.025 / 9)
    OUTR = []; stood = []
    for fam, x, kk, col, code, ncell, lift0, cov0 in PK:
        ci = cols.index(col); kf = famk[fam]; zb = NormalDist().inv_cdf(1 - 0.025 / kf)
        rr = {"族": fam, "級距": f"{dict((c[0], c[1]) for c in S.SPECS)[col]}｜Q{code}", "欄": col, "碼": code, "Bonferroni k（族）": kf, "z": zb,
              "探索": {"過門檻格數": ncell, "網格中位提升": lift0, "涵蓋率中位": cov0}}
        for g, msk in (("合併", vm), ("只400", vm & m4ev), ("只500", vm & ~m4ev)):
            ea_, na_, nev = fam_counts(Q, ci, E, x, kk, msk, emon_v, NMv)
            sB = stats(ea_, na_, code, zb); sN = stats(ea_, na_, code, zN); s95 = stats(ea_, na_, code, S.Z95)
            rr[g] = {"結束事件數（陽性＝對照）": int(nev), "Bonf下緣>1格數": sB["下緣>1格數"], "總N9_Bonf下緣>1格數": sN["下緣>1格數"],
                     "95%且涵蓋≥5%格數": s95["下緣>1且涵蓋≥5%格數"], "網格中位提升": sB["提升中位"], "提升p10": sB["提升p10"], "提升p90": sB["提升p90"],
                     "涵蓋率中位": sB["涵蓋率中位"], "陽性列數": sB["陽性列數"]}
        rr["標籤"] = "站得住" if rr["合併"]["Bonf下緣>1格數"] >= S.HALF else "沒站住"
        rr["只400描述"] = "≥125 格" if rr["只400"]["Bonf下緣>1格數"] >= S.HALF else "＜125 格"
        rr["只500描述"] = "≥125 格" if rr["只500"]["Bonf下緣>1格數"] >= S.HALF else "＜125 格"
        rr["總N9版"] = "站得住" if rr["合併"]["總N9_Bonf下緣>1格數"] >= S.HALF else "沒站住"
        OUTR.append(rr)
        if rr["標籤"] == "站得住":
            stood.append((col, code))
    print("[verify] 驗證段：" + "；".join(f"{r['族']} {r['級距']} {r['合併']['Bonf下緣>1格數']} 格 ⇒ {r['標籤']}" for r in OUTR), flush=True)
    # 驗證段網格描述
    cntv = np.bincount(E["cell"][vm], minlength=S.NC)
    GD = {"驗證段事件總數（格加總）": int(cntv.sum()), "有事件格數": int((cntv > 0).sum()), "≥30 件格數": int((cntv >= 30).sum()),
          "H60g100格事件數": int(cntv[S.cell_of(5, 1)]), "H250g50格事件數": int(cntv[S.cell_of(24, 0)]),
          "實際最晚起漲日": str(days[int(E["d"][vm].max())].date()) if vm.any() else None}
    # ret_blank 計數（V7）
    rb = []
    for f in ("membership", "membership_sp400"):
        p = os.path.join(os.path.expanduser("~/usdata/b33bde6/data"), f, "ret_blank.csv")
        if os.path.exists(p):
            rb += [(r.file_ticker, pd.Timestamp(r.date)) for r in pd.read_csv(p).itertuples()]
    touch = 0
    for tk, dt in rb:
        if tk in sids and dt in days:
            si = sids.index(tk); di = days.get_loc(dt)
            touch += int(np.sum(vm & (E["s"] == si) & (E["d"] < di) & (E["d"] + 250 >= di)))
    # 結束可交易（V6）
    ET = {}
    if stood:
        kB = len(set(stood)); zB = NormalDist().inv_cdf(1 - 0.025 / kB)
        evv = {"s": E["s"][vm], "d": E["d"][vm]}
        for col, code in sorted(set(stood)):
            rows_ = endtrade(Q, cols.index(col), code, ST, sids, cal, p0, v0, meta["w1"], evv, mi_v, NMv, zB)
            ok = [r for r in rows_ if r.get("n", 0) > 0]
            hs = [r["h"] for r in ok]
            ET[f"{col}｜Q{code}"] = {"Bonferroni k": kB, "z": zB, "一出現就賣較好": _rng([r["下"] > 0 for r in ok], hs), "續抱較好": _rng([r["上"] < 0 for r in ok], hs),
                                    **{f"A−B_{h}日": next((r["A−B"] for r in ok if r["h"] == h), None) for h in (20, 60, 120, 250)},
                                    "訊號在250日內出現比例": next((r["訊號已出現比例"] for r in ok if r["h"] == 250), None), "n_250日": next((r["n"] for r in ok if r["h"] == 250), None)}
    # 工作檔（repo 外）
    os.makedirs(WORKV, exist_ok=True)
    pe_ = os.path.join(WORKV, "events_all.npz"); np.savez(pe_, **E, sids=np.array(sids))
    pq_ = os.path.join(WORKV, "Q4.npz"); np.savez_compressed(pq_, Q=Q, bar=bar, cols=np.array(cols))
    shas = {"events_all.npz": {"rows": int(len(E["cell"])), "sha256": C.sha256f(pe_)}, "Q4.npz": {"sha256": C.sha256f(pq_)}}
    nstand = sum(1 for r in OUTR if r["標籤"] == "站得住")
    lines = "；".join(f"{r['族']} {r['級距']}：驗證段 {r['合併']['Bonf下緣>1格數']}／250 格 ⇒ {r['標籤']}" for r in OUTR)
    sent = (f"美股 S&P 500＋400 飆股回推（A3-17）探索段 2021～2023 挑出的 9 個「結束」特徵，在驗證段 2024-01～2026-09 站得住 {nstand} 個（N 9；各族 Bonferroni）。"
            f"{lines}。⭐ 這只是「漲到頂前長什麼樣」的描述性比對，不是買賣規則；"
            + ("站得住者的「一出現就賣 vs 續抱」見結束可交易。" if stood else "沒有站得住者 ⇒ 結束可交易不算。")
            + f"{C.IDEA}；{C.SURV}。")
    card = {"件": "A3-17", "名稱": "飆股回推比對 價量特徵部分——驗證段（只結束族 9 個）", "N": 9, "裁定": "seq321 §二 Q1（准開驗證段、只驗結束族 9 個、N 9；飆股族、妖股族 0 個 ⇒ 結案）",
            "標籤": f"站得住 {nstand}／9", "判定": "各族 Bonferroni（k＝該族挑出數）下緣 ＞ 1 的格數 ≥ 125／250 ⇒ 站得住（台股 seq7 §十之五、researchSurge5 S12、researchSurge6 U6）",
            "三欄": {"合併": f"站得住 {nstand}／9（判定）", "只400": "；".join(f"{r['級距']}（{r['族'][3:-1]}）{r['只400']['Bonf下緣>1格數']} 格" for r in OUTR),
                     "只500": "；".join(f"{r['級距']}（{r['族'][3:-1]}）{r['只500']['Bonf下緣>1格數']} 格" for r in OUTR)},
            "條件出場必報": "不適用（描述性特徵比對，非組合層）", "結果句": sent,
            "偏離": ["驗證段資料尾 2026-09-30（台股 seq7 寫 2026-08；美股照 G3 窗尾）",
                     "|ret|＞50%% 敏感度（G9）不再做：資料庫已逐筆確認、假的兩筆已在 ret_blank.csv 留空（另計驗證段事件碰到 ret_blank 列 %d 筆）" % touch,
                     "S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 偏向存活股（沿用探索段 C9）"],
            "補讀法": ["V1～V9（researchUSA3_surge_verify.py docstring，%s 寫死）" % READ_TS],
            "先驗紀錄": "台股 seq5／seq6 確認段結束特徵站得住者「一出現就賣」全輸續抱；美股驗證段站得住 %d 個（描述，不記對錯）" % nstand}
    out = {"卡片": card, "讀法寫死": READ_TS, "資料commit": meta["data_commit"], "驗證段": [str(VAL0.date()), str(cal[meta["w1"]].date())],
           "檔數": Sn, "重現閘": {"事件": gate_ev, "級距": gate, "通過": gate_ok}, "驗證段網格描述": GD, "逐級距": OUTR,
           "結束可交易（V6）": ET if stood else "沒有站得住的級距 ⇒ 不算", "ret_blank 碰觸事件數": touch,
           "逐筆檔sha（repo外）": shas, "耗時秒": round(time.time() - T0, 1)}
    C.jdump(out, OUTF)
    print("[verify] 完成 站得住 %d／9 ｜%.0fs" % (nstand, time.time() - T0), flush=True)
    return out


def check(nrep=3, seed=20261010):
    """獨立查核（⭐ 不呼叫 fam_counts／stats／ratio_stats）：抽 nrep 個級距 × 2 格，從 events_all.npz＋Q4.npz 用逐列 Python 迴圈重算驗證段 ①（月分群、Bonferroni）下緣，
    對 A3-17_verify.json 的「該格下緣 ＞ 1」是否一致；再用格數彙總對 JSON（同一格集合的計數）。"""
    z = np.load(os.path.join(WORKV, "events_all.npz")); qz = np.load(os.path.join(WORKV, "Q4.npz"))
    Q = qz["Q"]; cols = list(qz["cols"])
    J = json.load(open(OUTF, encoding="utf-8"))
    meta, _ = C.load_cache(); cal = meta["cal"]
    p0 = int(cal.searchsorted(S.SURGE0)); days = cal[p0:p0 + Q.shape[2]]
    v0 = int(np.searchsorted(days, VAL0))
    rng = np.random.default_rng(seed)
    PK = picks(); diff = 0; tot = 0; det = []
    famk = {}
    for p in PK:
        famk[p[0]] = famk.get(p[0], 0) + 1
    for i in rng.choice(len(PK), size=min(nrep, len(PK)), replace=False):
        fam, x, kk, col, code = PK[int(i)][:5]
        zb = NormalDist().inv_cdf(1 - 0.025 / famk[fam]); ci = cols.index(col)
        rr = next(r for r in J["逐級距"] if r["族"] == fam and r["欄"] == col)
        cnt_lo = 0
        bycell = {}
        cl_, d_, P_, s_, h_ = (z["cell"].tolist(), z["d"].tolist(), z["P"].tolist(), z["s"].tolist(), z[f"dd{x}"].tolist())
        for j in range(len(cl_)):                       # 逐事件迴圈（一次走完、依格分桶）
            if d_[j] < v0 or h_[j] <= 0:
                continue
            t, P = d_[j], P_[j]; pos = P - kk; mid = t + (P - t) // 2
            if not (pos > t and P - mid > 20 and mid > t):
                continue
            d0 = days[t]; mkey = d0.year * 12 + d0.month
            per_m = bycell.setdefault(cl_[j], {})
            for loc, y in ((pos, 1), (mid, 0)):
                qv = int(Q[ci, s_[j], loc])
                if qv == 0:
                    continue
                a_ = per_m.setdefault(mkey, [0, 0, 0, 0])      # 有特徵陽性、有特徵列、全陽性、全列
                a_[3] += 1; a_[2] += y
                if qv == code:
                    a_[1] += 1; a_[0] += y
        for cell in range(S.NC):
            per_m = bycell.get(cell)
            if not per_m:
                continue
            e = np.array([v[0] for v in per_m.values()], float); nn = np.array([v[1] for v in per_m.values()], float)
            ea = sum(v[2] for v in per_m.values()); na = sum(v[3] for v in per_m.values())
            if nn.sum() == 0 or na == 0 or ea == 0:
                continue
            p = e.sum() / nn.sum(); se = np.sqrt(((e - p * nn) ** 2).sum()) / nn.sum(); base = ea / na
            if (p - zb * se) / base > 1:
                cnt_lo += 1
        tot += 1; same = cnt_lo == rr["合併"]["Bonf下緣>1格數"]; diff += int(not same)
        det.append({"族": fam, "級距": col, "獨立重算格數": cnt_lo, "JSON": rr["合併"]["Bonf下緣>1格數"], "相同": same})
    return {"件": "A3-17 驗證段", "抽樣": tot, "不同": diff, "明細": det,
            "說明": "抽級距：250 格逐事件 Python 迴圈重算驗證段 Bonferroni 下緣 ＞ 1 的格數（不呼叫 ratio_stats）對 JSON"}


if __name__ == "__main__":
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 3
    if "--run" in sys.argv:
        run(procs)
    if "--check" in sys.argv:
        r = check()
        print(json.dumps(r, ensure_ascii=False))
        C.jdump(r, os.path.join(WORKV, "check.json"))

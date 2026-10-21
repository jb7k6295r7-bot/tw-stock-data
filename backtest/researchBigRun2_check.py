# -*- coding: utf-8 -*-
"""researchBigRun2 對帳（第一階段：甲補充版、族群分群）——回測線計算子代理。⛔ 不算任何之後報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun2_check [--dir backtest/resultsBigRun2]
輸出 <dir>/check.json、check.log

 K1 與第一件同式：甲補充_窗 的 R_vw、R_ew、R0050、原版達標 與 resultsBigRun/甲_窗.csv.gz 逐列比（乾跑只比交集列、只當邏輯檢查）。
 K2 全市場等權指數：抽 8 個 3 年窗，由面板價格逐月、逐檔走有效 K 棒（另寫：每檔月內累乘「有效 K 棒收盤比，壞根那根略過」）重算等權報酬，與 R全市場等權 比；
    全部窗重判 補充達標（R ≥ 1 ∧ R ≥ 2 × R全市場等權）。
 K3 併段：由 甲補充_窗 的補充達標旗標自己併段（j2 − 36 ≤ j1），與 甲補充_段 起點、最後達標窗終點、達標窗數逐段比；另抽 3 段 load_bars 重讀、逐日持有市值迴圈驗 高點、漲幅。
 K4 族群：① 抽 300 對段，從面板價格另算週收盤比（週末日最後一根有效 K 棒，週內有壞根 ⇒ 該週缺）減全市場等權週報酬，pandas 直接算重疊週相關，
    與主程式相關矩陣比；② 依「距離 ≤ 0.8 的邊」切成連通塊（平均連結不可能跨塊合併），≤ 150 段的塊用逐步重算平均距離的天真平均連結重分，
    三個切點的分群與 族群_段 比（同一群／不同群的關係一致）。
 K5 彙總：freq_甲補充 段數、族群_群 段數與家數 由明細重算；策略鎖 --check；git status。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import research11 as R                        # noqa: E402
import backtest.data as D                                   # noqa: E402

SHA = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
DATA = os.path.expanduser(f"~/bgrwork/main_{SHA[:12]}/data")
SRC1 = "backtest/resultsBigRun"
LOG = []
RES = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def close(a, b, tol=1e-6):
    fa = a is not None and np.isfinite(a); fb = b is not None and np.isfinite(b)
    if not fa and not fb:
        return True
    return fa and fb and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="backtest/resultsBigRun2"); a = ap.parse_args()
    OD = a.dir
    rng = np.random.default_rng(20261022)
    J = json.load(open(os.path.join(OD, "bigrun2.json"), encoding="utf-8"))
    dry = bool(J.get("乾跑limit"))
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL)
    pos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    USE = sorted(J["乾跑代號"]) if dry else sorted(set(ie) | set(im))
    W2 = pd.read_csv(os.path.join(OD, "甲補充_窗.csv.gz")); SEG = pd.read_csv(os.path.join(OD, "甲補充_段.csv"))
    # ── K1
    W1 = pd.read_csv(os.path.join(SRC1, "甲_窗.csv.gz"))
    m = W2.merge(W1, on=["產業", "窗起", "窗終"], how="inner", suffixes=("", "_1"))
    ok1 = [close(r["R_vw"], r["R_vw_1"], 1e-9) and close(r["R_ew"], r["R_ew_1"], 1e-9) and close(r["R0050"], r["R0050_1"], 1e-12)
           and (pd.isna(r["達標_vw"]) or bool(r["原版達標_vw"]) == bool(r["達標_vw"])) for _, r in m.iterrows()]
    RES["K1"] = {"補充窗列": len(W2), "第一件窗列": len(W1), "交集": len(m), "相符": int(sum(ok1)), "乾跑": dry}
    log(f"K1 與第一件同式：交集 {len(m)} 列、相符 {sum(ok1)}（補充 {len(W2)}、第一件 {len(W1)}）")

    # 面板價格（合併、接縫）——另寫一份
    def merged(s):
        parts = []
        for Z, off, ix in ((Ze, 0, ie), (Zm, NE, im)):
            if s in ix:
                c = Z["C"][ix[s]]; v = np.flatnonzero(np.isfinite(c))
                parts.append((v + off, c[v].astype(float), np.asarray(Z["BAD"][ix[s]][v], bool), Z["data"], Z["cal"]))
        if not parts:
            return None
        if len(parts) == 2:
            (pe, ce, be, de, cale), (pm, cm, bm, dm, calm) = parts
            if len(pe) and len(pm):
                def raw(data, cal, p, off):
                    x = pd.read_csv(os.path.join(data, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "close"])
                    v = pd.to_numeric(x.loc[x["date"] == str(cal[p - off].date()), "close"], errors="coerce")
                    return float(v.iloc[-1]) if len(v) else np.nan
                re_ = raw(de, cale, pe[-1], 0); rm_ = raw(dm, calm, pm[0], NE)
                Mf = ce[-1] * rm_ / (re_ * cm[0]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0) else np.nan
                bm = bm.copy()
                if np.isfinite(Mf) and Mf > 0:
                    cm = cm * Mf; bm[0] = (pm[0] - pe[-1] - 1) >= 5
                else:
                    bm[0] = True
            return np.r_[pe, pm], np.r_[ce, cm], np.r_[be, bm]
        return parts[0][0], parts[0][1], parts[0][2]
    MS = {}

    def ms(s):
        if s not in MS:
            MS[s] = merged(s)
        return MS[s]
    ym = CAL.year * 12 + CAL.month
    mstart = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); mend = np.r_[mstart[1:] - 1, NC - 1]
    MON = [(int(mstart[k] - 1), int(mend[k])) for k in range(1, len(mstart))]
    VALID = {}
    for s in USE:
        r = ms(s)
        VALID[s] = r[0] if r is not None else np.array([], np.int64)

    # ── K2 全市場等權
    def mkt_ret(pa, pt):
        I = 1.0
        for (b, e) in MON:
            if e <= pa or b >= pt:
                continue
            g = []
            for s in USE:
                vp = VALID[s]
                k = int(np.searchsorted(vp, b, "right")) - 1
                if k < 0 or b - vp[k] > 20:
                    continue
                pos, c, bad = ms(s)
                x = 1.0
                for kk in range(k + 1, len(pos)):
                    if pos[kk] > min(e, pt):
                        break
                    if not bad[kk]:
                        x *= c[kk] / c[kk - 1]
                g.append(x)
            I *= float(np.mean(g))
        return I - 1.0
    k2 = []
    pick = W2.drop_duplicates(["窗起", "窗終"]).sample(min(8, W2[["窗起", "窗終"]].drop_duplicates().shape[0]), random_state=5)
    for _, w in pick.iterrows():
        rm = mkt_ret(pos_le(w["窗起"]), pos_le(w["窗終"]))
        k2.append(close(rm, w["R全市場等權"], 1e-6))
        log(f"  K2 {w['窗起']}→{w['窗終']}：手算 {rm:+.6f} 檔 {w['R全市場等權']:+.6f} {'✔' if k2[-1] else '✖'}")
    flag_ok = 0
    for kd in ("vw", "ew"):
        x = W2[W2[f"R_{kd}"].notna()]
        hit = (x[f"R_{kd}"] >= 1.0) & (x[f"R_{kd}"] >= 2 * x["R全市場等權"])
        flag_ok += int((hit == x[f"補充達標_{kd}"].astype(bool)).sum())
    RES["K2"] = {"抽窗": len(k2), "相符": int(sum(k2)), "達標旗標重判相符": flag_ok, "達標旗標列": int(W2["R_vw"].notna().sum() + W2["R_ew"].notna().sum())}
    log(f"K2 全市場等權 {sum(k2)}/{len(k2)}；達標旗標重判 {flag_ok}/{RES['K2']['達標旗標列']}")

    # ── K3 併段＋抽段
    k3 = []
    for kd, lab in (("vw", "市值"), ("ew", "等權")):
        X = W2[W2[f"補充達標_{kd}"].fillna(False).astype(bool)].copy()
        X["s"] = pd.to_datetime(X["窗起"]); X["t"] = pd.to_datetime(X["窗終"])
        for ind, g in X.groupby("產業"):
            grp = []
            for _, w in g.sort_values("t").iterrows():
                if grp and w["s"] <= grp[-1][-1]["t"]:
                    grp[-1].append(w)
                else:
                    grp.append([w])
            for gg in grp:
                mm = SEG[(SEG["加權"] == lab) & (SEG["產業"] == ind) & (SEG["起點"] == str(gg[0]["s"].date()))]
                k3.append(len(mm) == 1 and mm.iloc[0]["最後達標窗終點"] == str(gg[-1]["t"].date()) and int(mm.iloc[0]["達標窗數"]) == len(gg))
    rev, rev_ly, cat, _, _, _ = PRE.load_rev(DATA)
    PIT = PRE.PIT(DATA, cat)
    CACHE = {}

    def lb(s):
        if s in CACHE:
            return CACHE[s]
        parts = []
        for Z, off, ix in ((Ze, 0, ie), (Zm, NE, im)):
            if s not in ix:
                continue
            D.DATA = Z["data"]; B = R.load_bars(s, Z["mk"].get(s, "twse"), Z["cal"])
            if B is None:
                continue
            idx = B["idx"].astype(np.int64); nb = len(idx)
            bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool) | np.asarray(Z["BAD"][ix[s]][idx], bool)
            parts.append((idx + off, np.asarray(B["c"], float), np.asarray(B["rc"], float), bad))
        if len(parts) == 2:
            (pe, ce, re_, be), (pm, cm, rm_, bm) = parts
            Mf = ce[-1] * rm_[0] / (re_[-1] * cm[0]) if (np.isfinite(rm_[0]) and np.isfinite(re_[-1]) and re_[-1] > 0) else np.nan
            bm = bm.copy()
            if np.isfinite(Mf) and Mf > 0:
                cm = cm * Mf; bm[0] = (pm[0] - pe[-1] - 1) >= 5
            else:
                bm[0] = True
            out = (np.r_[pe, pm], np.r_[ce, cm], np.r_[be, bm])
        elif parts:
            out = (parts[0][0], parts[0][1], parts[0][3])
        else:
            out = None
        x = np.ones(NC)
        if out is not None:
            for k in range(1, len(out[0])):
                if not out[2][k]:
                    x[out[0][k]] = out[1][k] / out[1][k - 1]
        CACHE[s] = x
        return x
    MCm = {}
    for s in USE:
        x = np.full(NC, np.nan)
        if s in ie:
            x[:NE] = Ze["MC"][ie[s]]
        if s in im:
            x[NE:] = Zm["MC"][im[s]]
        MCm[s] = x
    segk = []
    if len(SEG):
        S2 = SEG.assign(_l=pd.to_datetime(SEG["最後達標窗終點"]) - pd.to_datetime(SEG["起點"])).sort_values("_l")
        for _, r in S2.head(3).iterrows():
            kd = "vw" if r["加權"] == "市值" else "ew"
            pa, pt = pos_le(r["起點"]), pos_le(r["最後達標窗終點"])
            vals = [1.0]; poss = [pa]; I = 1.0; okm = True
            for (b, e) in MON:
                if e <= pa or b >= pt:
                    continue
                mem = []
                for s in USE:
                    vp = VALID[s]; k = int(np.searchsorted(vp, b, "right")) - 1
                    if k < 0 or b - vp[k] > 20 or not (np.isfinite(MCm[s][b]) and MCm[s][b] > 0):
                        continue
                    if PIT.at(s, CAL[b])[0] == r["產業"]:
                        mem.append(s)
                if len(mem) < 5:
                    okm = False; break
                W = np.array([MCm[s][b] if kd == "vw" else 1.0 for s in mem])
                end = min(e, pt)
                G = np.cumprod(np.stack([lb(s)[b + 1:end + 1] for s in mem]), axis=1)
                v = I * (W @ G) / W.sum(); vals += list(v); poss += list(range(b + 1, end + 1)); I = float(v[-1])
            if not okm:
                segk.append(False); continue
            H = poss[int(np.argmax(vals))]
            ok = str(CAL[H].date()) == r["高點"] and close(max(vals) - 1, r["漲幅"], 1e-6)
            segk.append(ok)
            log(f"  K3 段 {r['段號']}：高點 {CAL[H].date()}/{r['高點']} 漲幅 {max(vals) - 1:+.6f}/{r['漲幅']:+.6f} {'✔' if ok else '✖'}")
    RES["K3"] = {"自己併段": len(k3), "檔內段": len(SEG), "相符": int(sum(k3)), "抽段重算": len(segk), "抽段相符": int(sum(segk))}
    log(f"K3 併段 {sum(k3)}/{len(k3)}（檔 {len(SEG)}）；抽段 {sum(segk)}/{len(segk)}")

    # ── K4 族群
    GS = pd.read_csv(os.path.join(OD, "族群_段.csv"), dtype={"代號": str})
    CR = np.load(os.path.expanduser(f"~/bgrwork/bgr2_corr_{'dry' if dry else 'full'}.npy"))
    if len(CR) != len(GS):
        raise SystemExit("⛔ 相關矩陣與族群_段列數不同")
    MK = pd.read_csv(os.path.join(OD, "mkt_ew_index.csv.gz"))["全市場等權"].to_numpy(float)
    iso = CAL.isocalendar(); wid = (iso.year * 100 + iso.week).to_numpy()
    WE = np.flatnonzero(np.r_[wid[1:] != wid[:-1], True])
    WS = {}

    def wser(s):
        """週末日序列：(週序 → 週對數報酬)，週內有壞根 ⇒ 缺；另算法：週末日最後一根有效 K 棒收盤比。"""
        if s in WS:
            return WS[s]
        pos, c, bad = ms(s)
        lastk = np.searchsorted(pos, WE, "right") - 1
        out = np.full(len(WE), np.nan)
        cb = np.r_[0, np.cumsum(bad)]
        for w in range(1, len(WE)):
            k1, k0 = lastk[w], lastk[w - 1]
            if k1 < 0 or k0 < 0:
                continue
            if cb[k1 + 1] - cb[k0 + 1] > 0:
                continue
            out[w] = np.log(c[k1] / c[k0]) if k1 > k0 else 0.0
        WS[s] = out
        return out
    mlr = np.r_[np.nan, np.log(MK[WE[1:]] / MK[WE[:-1]])]
    pairs = []
    n = len(GS)
    while len(pairs) < 300:
        i, j = rng.integers(0, n, 2)
        if i == j:
            continue
        si, ei = pos_le(GS.at[i, "起點"]), pos_le(GS.at[i, "高點"]); sj, ej = pos_le(GS.at[j, "起點"]), pos_le(GS.at[j, "高點"])
        if min(ei, ej) - max(si, sj) < 300 and len(pairs) < 200:
            continue
        pairs.append((int(i), int(j)))
    okc = 0; bads = []
    for i, j in pairs:
        ser = []
        for k in (i, j):
            s = GS.at[k, "代號"]; ps, ph = pos_le(GS.at[k, "起點"]), pos_le(GS.at[k, "高點"])
            x = wser(s) - mlr
            sel = (WE > ps) & (WE <= ph)
            # 起點所在週不算（主程式從起點後第一個完整週起）
            wk0 = int(np.searchsorted(WE, ps, "left"))
            sel[:wk0 + 1] = False
            ser.append(pd.Series(np.where(sel, x, np.nan)))
        df = pd.concat(ser, axis=1).dropna()
        mine = df[0].corr(df[1]) if len(df) >= 52 else np.nan
        fil = CR[i, j]
        if close(mine, fil, 1e-5):
            okc += 1
        else:
            bads.append((i, j, len(df), mine, float(fil)))
    # ② 天真平均連結
    DM = np.where(np.isfinite(CR), 1.0 - CR, 1.0).astype(float); np.fill_diagonal(DM, 0.0)
    adj = DM <= 0.8; np.fill_diagonal(adj, False)
    comp = -np.ones(n, int); cid = 0
    for st in range(n):
        if comp[st] >= 0:
            continue
        stack = [st]; comp[st] = cid
        while stack:
            u = stack.pop()
            for v in np.flatnonzero(adj[u] & (comp < 0)):
                comp[v] = cid; stack.append(v)
        cid += 1
    sizes = Counter(comp)
    k4b = {c: [0, 0] for c in (0.6, 0.7, 0.8)}
    checked = 0
    for c_id, sz in sizes.items():
        if sz < 2 or sz > 150:
            continue
        mem = np.flatnonzero(comp == c_id); sub = DM[np.ix_(mem, mem)]
        cl = [[k] for k in range(len(mem))]
        hist = []
        while len(cl) > 1:
            best = (np.inf, None, None)
            for x in range(len(cl)):
                for y in range(x + 1, len(cl)):
                    d = sub[np.ix_(cl[x], cl[y])].mean()
                    if d < best[0] - 1e-12:
                        best = (d, x, y)
            if best[0] > 0.8:
                break
            d, x, y = best
            hist.append((d, list(cl[x]), list(cl[y])))
            cl[x] = cl[x] + cl[y]; del cl[y]
        for cut in (0.6, 0.7, 0.8):
            lab = list(range(len(mem)))
            for d, A, B in hist:
                if d <= cut:
                    ra = lab[A[0]]
                    for b in A + B:
                        pass
                    tgt = {lab[q] for q in A + B}
                    lab = [ra if l in tgt else l for l in lab]
            fil = GS[f"群_切{cut}"].to_numpy()[mem]
            # 檔內只標 ≥3 段群（其餘 0）；比較：同一群關係在 ≥3 段群上一致
            mine_g = Counter(lab)
            for p in range(len(mem)):
                for q in range(p + 1, len(mem)):
                    same_mine = lab[p] == lab[q] and mine_g[lab[p]] >= 3
                    same_fil = fil[p] == fil[q] and fil[p] > 0
                    k4b[cut][0] += 1; k4b[cut][1] += int(same_mine == same_fil)
        checked += sz
    # ③ 全部段：最近鄰鏈（nearest-neighbor chain）平均連結——與主程式「每步全矩陣找最小」不同演算法，平均連結可約 ⇒ 樹相同
    Dn = DM.copy(); np.fill_diagonal(Dn, np.inf); act = np.ones(n, bool); sz = np.ones(n); chain = []; mg = []; left = n
    while left > 1:
        if not chain:
            chain = [int(np.flatnonzero(act)[0])]
        a_ = chain[-1]
        row = np.where(act, Dn[a_], np.inf); row[a_] = np.inf
        b_ = int(np.argmin(row))
        if len(chain) > 1 and row[chain[-2]] <= row[b_]:
            b_ = chain[-2]
        if len(chain) > 1 and b_ == chain[-2]:
            chain.pop(); chain.pop()
            h = float(Dn[a_, b_])
            new = (sz[a_] * Dn[a_] + sz[b_] * Dn[b_]) / (sz[a_] + sz[b_])
            Dn[a_, :] = new; Dn[:, a_] = new; Dn[a_, a_] = np.inf
            act[b_] = False; sz[a_] += sz[b_]; mg.append((a_, b_, h)); left -= 1
        else:
            chain.append(b_)

    def canon(lab, small_zero):
        lab = np.asarray(lab); out = np.arange(len(lab))
        if small_zero:
            for g in set(lab[lab > 0]):
                ix = np.flatnonzero(lab == g); out[ix] = ix.min()
        else:
            cnt = Counter(lab)
            for g, c_ in cnt.items():
                if c_ >= 3:
                    ix = np.flatnonzero(lab == g); out[ix] = ix.min()
        return out
    k4c = {}
    for cut in (0.6, 0.7, 0.8):
        par = list(range(n))

        def fnd(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        for a_, b_, h in mg:
            if h <= cut:
                par[fnd(b_)] = fnd(a_)
        mine = canon([fnd(x) for x in range(n)], False); fil = canon(GS[f"群_切{cut}"].to_numpy(), True)
        k4c[str(cut)] = {"段數": n, "分群相同的段": int((mine == fil).sum())}
    log("  K4 最近鄰鏈全部段：" + "、".join(f"切{c} {v['分群相同的段']}/{v['段數']}" for c, v in k4c.items()))
    RES["K4"] = {"最近鄰鏈全部段": k4c, "相關抽對": len(pairs), "相關相符": okc, "不符例": bads[:5], "連通塊數": len(sizes), "≤150段塊內段數(已驗)": checked,
                 "最大塊段數": max(sizes.values()), "天真平均連結_成對關係": {str(c): {"對數": v[0], "相符": v[1]} for c, v in k4b.items()}}
    log(f"K4 族群：相關 {okc}/{len(pairs)}；連通塊 {len(sizes)}、最大 {max(sizes.values())}、≤150 塊已驗 {checked} 段；成對關係 " +
        "、".join(f"切{c} {v[1]}/{v[0]}" for c, v in k4b.items()))
    # ── K5
    ok5 = []
    FR = pd.read_csv(os.path.join(OD, "freq_甲補充.csv"))
    for lab in ("市值", "等權"):
        ok5.append(int(FR[f"補充段數_{lab}"].sum()) == int((SEG["加權"] == lab).sum()) if len(SEG) else True)
    GR = pd.read_csv(os.path.join(OD, "族群_群.csv"))
    for _, r in GR.iterrows():
        sub = GS[GS[f"群_切0.7"] == r["群號"]]
        ok5.append(len(sub) == r["段數"] and sub["代號"].nunique() == r["家數"])
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    RES["K5"] = {"彙總項": len(ok5), "相符": int(sum(ok5)), "策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:],
                 "已追蹤檔改動": [x for x in st if not x.startswith("??")], "本件新增": [x for x in st if "BigRun2" in x]}
    log(f"K5 彙總 {sum(ok5)}/{len(ok5)}；策略鎖 {RES['K5']['策略鎖']}；已追蹤檔改動 {len(RES['K5']['已追蹤檔改動'])}")
    json.dump(RES, open(os.path.join(OD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OD, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

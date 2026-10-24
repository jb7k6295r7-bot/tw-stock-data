# -*- coding: utf-8 -*-
"""researchPickDistUS_freq 獨立對帳（⛔ 不 import researchPickDistUS_freq 的任何函式；只讀它的輸出檔＋同一份 A4 世界與季營收資料）。
 K1 由 events_*.csv.gz 自己重數各臂各段：事件、可進場、750 走得完、主格、n_eff、S&P 500／400、斷點、下市 ⇒ 與 freq.csv 逐格相同。
 K2 重複窗：甲乙丙同檔相鄰事件 ≥ 36 個月；丁每檔每判斷日至多一列。
 K3 斷點自己重建（pb ∪ 連續 ≥5 交易日無 K 棒後第一根）；A（近 750，逐對掃描）、B 暴力重算：每臂抽 150 件 ＋ 丁隨機 400 筆。
 K4 「第一次」：抽到的甲乙丙事件，從上一件＋36 個月（或 2018-12）到本件之前的判斷日，該臂條件都不成立。
 K5 季營收轉強另寫：可用日 ≤ d 的季報、最新期末距 d ≤ 200 日；連續季 ＝ 相鄰期末 60～120 日；年增 ＝ 期末早 350～380 日那一季；
    甲 ＝ 年增 − 近 4 季和年增 ≥ 0.05；乙 ＝ hi8 ∧ ¬hi8(上一季) ⇒ 與事件檔「季甲」「季乙」「轉強」一致。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDistUS_freq_check
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K        # noqa: E402  資料：A4 世界
from backtest import researchUSA4 as A4      # noqa: E402  資料：load_fund、key_at（讀檔，不是被查的邏輯）

D = "backtest/resultsPickDistUS/freq"
ARMS = ["甲", "乙", "丙", "丁"]
LAB = {"甲": "甲 A＋B", "乙": "乙 A＋B＋轉強", "丙": "對照一 B 且非 A", "丁": "對照二 全母體"}
RES = []


def ok(name, cond, info=""):
    RES.append((name, bool(cond), info)); print(("✔" if cond else "✘"), name, info, flush=True)


def rev_mine(F, key, d, edays):
    if key is None or key not in F["revenue"]:
        return None
    pe, v, av, fy = F["revenue"][key]
    m = np.flatnonzero(av <= d)
    if not len(m):
        return (False, False, False)
    j = m[-1]
    fresh = edays - pe[j] <= 200

    def consec(k, end):
        if end - k + 1 < 0:
            return None
        sel = m[end - k + 1:end + 1] if end - k + 1 >= 0 else None
        if sel is None or len(sel) < k:
            return None
        dd = np.diff(pe[sel])
        if not ((dd >= 60) & (dd <= 120)).all() or not np.isfinite(v[sel]).all():
            return None
        return v[sel]
    yo = np.nan
    if fresh:
        pk = m[(pe[m] >= pe[j] - 380) & (pe[m] <= pe[j] - 350)]
        if len(pk) and v[pk[-1]] > 0 and np.isfinite(v[j]):
            yo = v[j] / v[pk[-1]] - 1
    L = len(m) - 1
    v8 = consec(8, L) if fresh else None
    v9 = consec(9, L) if fresh else None
    ttm = (v8[4:].sum() / v8[:4].sum() - 1) if (v8 is not None and v8[:4].sum() > 0) else np.nan
    hi8 = (v8[-1] > v8[:-1].max()) if v8 is not None else None
    hp = (v9[7] > v9[:7].max()) if v9 is not None else None
    jia = bool(np.isfinite(yo) and np.isfinite(ttm) and yo - ttm >= 0.05)
    yi = bool(hi8 is True or hi8 == True) and not bool(hp is True or hp == True)  # noqa: E712
    return (jia, yi, jia or yi)


def main():
    FR = pd.read_csv(os.path.join(D, "freq.csv"))
    E = {a: pd.read_csv(os.path.join(D, f"events_{a}.csv.gz")) for a in ARMS}
    for a in ARMS:
        for nm in ("判斷窗", "段外"):
            d = E[a][E[a]["段"] == nm]; m = d[d["主格"]]
            r = FR[(FR["臂"] == LAB[a]) & (FR["段"] == nm)].iloc[0]
            mine = {"事件(重複窗後)": len(d), "可進場": int((d["進場"] == "保留").sum()), "750走得完": int(d["H750走得完"].sum()), "主格事件": len(m),
                    "n_eff": int(m["月"].nunique()), "S&P500": int((d["指數"] == "S&P500").sum()), "S&P400": int((d["指數"] == "S&P400").sum()),
                    "主格斷點截斷": int((m["H750窗內遇斷點"] == True).sum()), "主格下市": int((m["H750窗內遇下市"] == True).sum())}  # noqa: E712
            diff = {k: (v, r.get(k, np.nan)) for k, v in mine.items()
                    if (pd.isna(r.get(k, np.nan)) and v != 0) or (not pd.isna(r.get(k, np.nan)) and int(r[k]) != v)}
            ok(f"K1 {a}{nm} 重數", not diff, str(diff) if diff else f"事件 {len(d)} 主格 {len(m)} n_eff {mine['n_eff']}")
    for a in ("甲", "乙", "丙"):
        d = E[a].copy(); dt = pd.to_datetime(d["判斷日"]); d["mk"] = dt.dt.year * 12 + dt.dt.month - 1
        g = d.sort_values(["ticker", "mk"]).groupby("ticker")["mk"].diff().dropna()
        ok(f"K2 {a} 同檔相鄰事件 ≥36 月", (g >= 36).all(), f"最小 {g.min() if len(g) else '—'}")
    ok("K2 丁 每檔每判斷日至多一列", not E["丁"].duplicated(["ticker", "判斷日"]).any())
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]
    C = W["C"]; V = W["valid"]; ix = W["ix"]; m5 = W["m5"]; m4 = W["m4"]
    BAD = np.asarray(W["pb"], bool).copy()
    for j in range(V.shape[1]):
        vp = np.flatnonzero(V[:, j])
        for k in range(1, len(vp)):
            if vp[k] - vp[k - 1] - 1 >= 5:
                BAD[vp[k], j] = True
    F = A4.load_fund(cal)
    s = pd.Series(np.arange(len(cal)), index=cal)
    tail = int(np.flatnonzero(V.sum(axis=1) > 0)[-1])
    MEs = [int(p) for p in s.groupby([s.index.year, s.index.month]).last() if p <= tail and str(cal[p].date()) >= "2018-12-01"]

    def bA(j, d):
        vp = np.flatnonzero(V[:d + 1, j]); vp = vp[vp >= d - 750]
        bads = np.flatnonzero(BAD[:d + 1, j])
        for k1 in range(1, len(vp)):
            t1 = int(vp[k1]); lb = bads[bads <= t1]; lb = int(lb[-1]) if len(lb) else -1
            cand = vp[(vp >= max(lb, d - 750)) & (vp < t1)]
            if len(cand) and C[t1, j] >= 3 * C[cand, j].min():
                return True
        return False

    def bB(j, d):
        vp = np.flatnonzero(V[:, j]); a = d - 499
        if not len(vp) or vp[0] > a or BAD[a + 1:d + 1, j].any():
            return False
        w = C[a:d + 1, j]; w = w[np.isfinite(w)]
        return bool(C[d, j] < 2 * w.min() and C[d, j] <= 0.85 * w.max())

    def up(t, d):
        r = rev_mine(F, A4.key_at(F["SEG"], t, cal[d]), d, int(cal[d].value // 86400_000_000_000))
        return (False, False, False) if r is None else r
    cond = {"甲": lambda A, B, U: A and B, "乙": lambda A, B, U: A and B and U, "丙": lambda A, B, U: B and not A}
    rng = np.random.default_rng(7)
    for a in ARMS:
        d = E[a]; smp = d.iloc[rng.choice(len(d), min(150, len(d)), replace=False)]
        mis = []; umis = []; fb = []
        for r in smp.itertuples(index=False):
            j = ix[r.ticker]; dd = int(cal.searchsorted(pd.Timestamp(r.判斷日)))
            A_, B_ = bA(j, dd), bB(j, dd); u = up(r.ticker, dd)
            if A_ != r.A成立 or B_ != r.B:
                mis.append((r.ticker, r.判斷日, A_, r.A成立, B_, r.B))
            if (u[0], u[1], u[2]) != (r.季甲, r.季乙, r.轉強):
                umis.append((r.ticker, r.判斷日, u, (r.季甲, r.季乙, r.轉強)))
            if a in cond:
                if not cond[a](A_, B_, u[2]):
                    mis.append((r.ticker, r.判斷日, "條件不成立"))
                mk = cal[dd].year * 12 + cal[dd].month - 1
                prev = d[(d["ticker"] == r.ticker) & (pd.to_datetime(d["判斷日"]) < cal[dd])]
                lo = (max(pd.Timestamp(x).year * 12 + pd.Timestamp(x).month - 1 for x in prev["判斷日"]) + 36) if len(prev) else 0
                for q in MEs:
                    mq = cal[q].year * 12 + cal[q].month - 1
                    if lo <= mq < mk and (m5[q, j] or m4[q, j]) and V[q, j] and cond[a](bA(j, q), bB(j, q), up(r.ticker, q)[2]):
                        fb.append((r.ticker, r.判斷日, str(cal[q].date()))); break
        ok(f"K3 {a} 抽 {len(smp)} 件 A／B 暴力重算", not mis, str(mis[:5]))
        ok(f"K5 {a} 季營收轉強另寫一致", not umis, str(umis[:5]))
        if a in cond:
            ok(f"K4 {a} 「第一次」", not fb, str(fb[:5]))
    d4 = E["丁"].set_index(["ticker", "判斷日"]); n = mis = 0
    for _ in range(400):
        q = MEs[rng.integers(len(MEs))]
        cs = np.flatnonzero((m5[q] | m4[q]) & V[q]); j = int(cs[rng.integers(len(cs))]); t = W["tick"][j]
        key = (t, str(cal[q].date()))
        if key not in d4.index:
            continue
        r = d4.loc[key]; n += 1
        fv = int(np.flatnonzero(V[:, j])[0])
        if bA(j, q) != r["A成立"] or bB(j, q) != r["B"] or (fv <= q - 750) != r["A可判"]:
            mis += 1
    ok(f"K3 丁 隨機 {n} 筆 A／B／A可判", mis == 0, f"不一致 {mis}")
    nf = sum(1 for _, c, _ in RES if not c)
    print(f"[對帳] {len(RES)} 項，不過 {nf}")
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()

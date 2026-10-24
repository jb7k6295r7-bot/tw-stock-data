# -*- coding: utf-8 -*-
"""researchPickDist_freq 獨立對帳（⛔ 不 import researchPickDist_freq 的任何函式；只讀它的輸出檔）。
 K1 由 events_*.csv.gz 自己重數各臂各段：事件、e 可進場、750 走得完、主格、n_eff、上市／上櫃、壞根、下市 ⇒ 與 freq_段.csv 逐格相同。
 K2 重複窗：每臂每檔相鄰事件期別相差 ≥ 36 個月；丁每檔每期至多一列。
 K3 A、B 暴力重算（另寫：逐對 t0＜t1 掃描，非 rolling）：每臂抽 150 件事件 ＋ 過閘股月隨機 400 筆，A、B、A近750、A可判 與事件檔／重算一致。
 K4 「第一次」：抽到的甲乙丙事件，從上一件事件＋36 個月（或 2008-01 起）到本件之前的每個判日，暴力判該臂條件 ∧ 過閘 都不成立。
 K5 轉強：抽到事件的轉強 ＝ rev_table 該期（accel ≥ 0.05）∨（hi24 ∧ ¬hi24_prev），與 up 欄一致。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDist_freq_check
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  只為讀同一份價格面板與月營收（資料，不是被查的邏輯）

D = "backtest/resultsPickDist/freq"
SHA = "9b0e9882572c438ec25771031658ddc701ca6171"
ARMS = ["甲", "乙", "丙", "丁"]
RES = []


def ok(name, cond, info=""):
    RES.append((name, bool(cond), info)); print(("✔" if cond else "✘"), name, info, flush=True)


def mnum(p):
    return int(p[:4]) * 12 + int(p[5:7]) - 1


_HC = {}


def brute_hits(C, BAD, i):
    """逐根 t1 掃描（非 rolling）：同段、t1−750 ≤ t0 ＜ t1 的最低收盤 × 3 ≤ c(t1) ⇒ 命中；回命中位置陣列（快取）。"""
    if i in _HC:
        return _HC[i]
    vp = np.flatnonzero(np.isfinite(C[i])); bads = np.flatnonzero(BAD[i]); out = []
    for k1 in range(1, len(vp)):
        t1 = int(vp[k1])
        lb = bads[bads <= t1]; lb = int(lb[-1]) if len(lb) else -1
        lo = max(t1 - 750, lb, int(vp[0]))
        k0 = int(np.searchsorted(vp, lo, "left"))
        if k0 < k1 and C[i, t1] >= 3.0 * C[i, vp[k0:k1]].min():
            out.append(t1)
    _HC[i] = np.array(out, dtype=np.int64)
    return _HC[i]


def brute_A(C, BAD, i, p1, recent=False):
    if not recent:
        h = brute_hits(C, BAD, i)
        return bool(len(h) and h[0] <= p1)
    vp = np.flatnonzero(np.isfinite(C[i, :p1 + 1])); vp = vp[vp >= p1 - 750]
    bads = np.flatnonzero(BAD[i, :p1 + 1])
    for k1 in range(1, len(vp)):
        t1 = int(vp[k1])
        lb = bads[bads <= t1]; lb = int(lb[-1]) if len(lb) else -1
        lo = max(t1 - 750, lb, int(vp[0]))
        cand = vp[(vp >= lo) & (vp < t1)]
        if len(cand) and C[i, t1] >= 3.0 * C[i, cand].min():
            return True
    return False


def brute_B(C, BAD, i, p1):
    vp = np.flatnonzero(np.isfinite(C[i]))
    a = p1 - 499
    if not len(vp) or vp[0] > a or a < 0:
        return False
    if BAD[i, a + 1:p1 + 1].any():
        return False
    w = C[i, a:p1 + 1]; w = w[np.isfinite(w)]; c = C[i, p1]
    return bool(c < 2 * w.min() and c <= 0.85 * w.max())


def main():
    FR = pd.read_csv(os.path.join(D, "freq_段.csv"))
    E = {a: pd.read_csv(os.path.join(D, f"events_{a}.csv.gz"), dtype={"sid": str, "期別": str}, low_memory=False) for a in ARMS}
    # K1
    for a in ARMS:
        for nm in ("早段", "後段", "段外"):
            d = E[a][E[a]["段"] == nm]; m = d[d["主格"]]
            r = FR[(FR["臂"] == a) & (FR["段"] == nm)].iloc[0]
            mine = {"事件(重複窗後)": len(d), "e可進場": int((d["進場"] == "保留").sum()), "750走得完": int(d["H750走得完"].sum()),
                    "主格事件": len(m), "n_eff": int(m["月"].nunique()), "上市": int((d["市場"] == "twse").sum()), "上櫃": int((d["市場"] == "tpex").sum()),
                    "主格壞根截斷": int((m["H750窗內遇壞根"] == True).sum()), "主格下市": int((m["H750窗內遇下市"] == True).sum())}  # noqa: E712
            diff = {k: (v, r.get(k, np.nan)) for k, v in mine.items()
                    if (pd.isna(r.get(k, np.nan)) and v != 0) or (not pd.isna(r.get(k, np.nan)) and int(r[k]) != v)}
            ok(f"K1 {a}{nm} 重數", not diff, str(diff) if diff else f"事件 {len(d)} 主格 {len(m)} n_eff {mine['n_eff']}")
    # K2
    for a in ("甲", "乙", "丙"):
        d = E[a].copy(); d["mk"] = d["期別"].map(mnum); d = d.sort_values(["sid", "mk"])
        g = d.groupby("sid")["mk"].diff().dropna()
        ok(f"K2 {a} 同檔相鄰事件 ≥36 月", (g >= 36).all(), f"最小 {g.min() if len(g) else '—'}")
    ok("K2 丁 每檔每期至多一列", not E["丁"].duplicated(["sid", "期別"]).any())
    # 資料
    sha, DN, MD = RT.ensure_data(SHA)
    PX = RT.prices(sha, DN, 3)
    C, BAD, G, CAL, ix = PX["C"], PX["BAD"], PX["G"], PX["CAL"], PX["ix"]
    RV, _ = RT.rev_table(MD, PX["SIDS"], 3, tag="trp")
    RVi = RV.set_index(["sid", "period"])
    periods = sorted(RV["period"].unique())
    APOS = {P: int(CAL.searchsorted(pd.Timestamp(RT.BM.rev_avail(P)), side="right")) for P in periods}
    rng = np.random.default_rng(7)
    cond = {"甲": lambda A, B, U: A and B, "乙": lambda A, B, U: A and B and U, "丙": lambda A, B, U: B and not A}

    def up_of(s, P):
        if (s, P) not in RVi.index:
            return False
        r = RVi.loc[(s, P)]
        ac = r["accel"]; h = r["hi24"]; hp = r["hi24_prev"]
        return bool((np.isfinite(ac) and ac >= 0.05) or (h == 1.0 and not hp == 1.0))
    # K3、K4、K5
    for a in ARMS:
        d = E[a]
        smp = d.iloc[rng.choice(len(d), min(150, len(d)), replace=False)] if len(d) else d
        mis = []; first_bad = []; upmis = 0
        for r in smp.itertuples(index=False):
            i = ix[r.sid]; A_ = APOS[r.期別]; p1 = A_ - 1
            if str(CAL[A_].date()) != r.A:
                mis.append((r.sid, r.期別, "A日期")); continue
            ba = brute_A(C, BAD, i, p1); bb = brute_B(C, BAD, i, p1); br = brute_A(C, BAD, i, p1, recent=True)
            if ba != r.A成立 or bb != r.B or br != r.A近750:
                mis.append((r.sid, r.期別, ba, r.A成立, bb, r.B, br, r.A近750))
            u = up_of(r.sid, r.期別)
            if u != r.轉強:
                upmis += 1
            if a in cond and not cond[a](ba, bb, u):
                mis.append((r.sid, r.期別, "條件不成立"))
            if a in cond:
                prev = d[(d["sid"] == r.sid) & (d["期別"].map(mnum) < mnum(r.期別))]
                lo = (prev["期別"].map(mnum).max() + 36) if len(prev) else mnum("2007-12")
                for P in periods:
                    if lo <= mnum(P) < mnum(r.期別) and str(CAL[min(APOS[P], len(CAL) - 1)].date()) >= "2008-01-01" and APOS[P] < len(CAL):
                        q1 = APOS[P] - 1
                        if np.isfinite(C[i, q1]) and G[i, q1] and cond[a](brute_A(C, BAD, i, q1), brute_B(C, BAD, i, q1), up_of(r.sid, P)):
                            first_bad.append((r.sid, r.期別, P)); break
        ok(f"K3 {a} 抽 {len(smp)} 件 A／B／A近750 暴力重算一致", not mis, str(mis[:5]))
        ok(f"K5 {a} 轉強一致", upmis == 0, f"不一致 {upmis}")
        if a in cond:
            ok(f"K4 {a} 「第一次」暴力檢查", not first_bad, str(first_bad[:5]))
    # K3 隨機過閘股月
    ms = [(P, APOS[P]) for P in periods if APOS[P] < len(CAL) and str(CAL[APOS[P]].date()) >= "2008-01-01"]
    d4 = E["丁"].set_index(["sid", "期別"])
    mis = 0; n = 0
    for _ in range(400):
        P, A_ = ms[rng.integers(len(ms))]
        cs = np.flatnonzero(G[:, A_ - 1])
        if not len(cs):
            continue
        i = int(cs[rng.integers(len(cs))]); s = PX["SIDS"][i]
        if (s, P) not in d4.index:
            continue
        r = d4.loc[(s, P)]; n += 1
        if brute_A(C, BAD, i, A_ - 1) != r["A成立"] or brute_B(C, BAD, i, A_ - 1) != r["B"]:
            mis += 1
        fv = np.flatnonzero(np.isfinite(C[i]))[0]
        if bool(fv <= A_ - 1 - 750) != r["A可判"]:
            mis += 1
    ok(f"K3 丁 隨機過閘股月 {n} 筆 A／B／A可判 暴力重算", mis == 0, f"不一致 {mis}")
    nf = sum(1 for _, c, _ in RES if not c)
    print(f"[對帳] {len(RES)} 項，不過 {nf}")
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()

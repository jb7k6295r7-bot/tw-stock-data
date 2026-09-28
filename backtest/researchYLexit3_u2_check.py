# -*- coding: utf-8 -*-
"""營量出場 使用者版 v2：簡短查核（⛔ 不 import researchYLexit3_u2、researchYLexit3_u、researchYLexit3、researchYLexit、researchYLexit3_b）。
警訊、低價沿用 seq3 獨立查核（researchYLexit3_check.load）；甲 v1 ＋ 乙兩日確認出場自寫 ⇒ 主世界 k55_c10_C120（看警訊）、k60_c10_C250（不看警訊）
種子 0 eq_sha ＝ user_v2/seeds.csv；擋下（持有中／最後出場）次數 ＝ cells.csv。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLexit3_u2_check.py
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R
from backtest import researchYLexit3_check as C3

OUT = "backtest/resultsYLexit3/user_v2"
COST = R.COST


def path(b, lo, ma, cl, op, s, k, e, K, cs, C, NP, n0, nk, warn):
    idx = b["idx"]; Wn = b["W"]; n = len(idx); nbk = b["nb"][max(0, k - 20)]
    ke = k + 1; kk = ke + K - 1; kc = ke + C - 1; last = min(kc, n - 1, nbk - 1)
    P0 = float(op[s][e]); inm = True; ve = 1.0; pe = P0; vf = 0.0; todo = None; val = {}; cand = None; sb = None; lim = 15; rel = None
    act = None; Bv = None; bc = None; nout_ = 0; nin = 0; cnt = {"擋持": 0, "擋出": 0}; lastj = None
    for j in range(ke, last + 1):
        t = int(idx[j]); ot = float(op[s][t]); ct = float(cl[s][t])
        if todo == "s" and inm and np.isfinite(ot) and ot > 0:
            vf = ve * ot / pe; inm = False; sb = j; lim = 15; nout_ += 1
        elif todo == "b" and not inm and np.isfinite(ot) and ot > 0:
            ve = vf * (1 - COST); pe = ot; inm = True; cand = None; nin += 1
        elif todo == "a":
            if inm and np.isfinite(ot) and ot > 0:
                vf = ve * ot / pe; inm = False; nout_ += 1
            val[t] = vf; rel = t; break
        elif todo == "f" and np.isfinite(ot) and ot > 0:
            val[t] = ve * ot / pe; rel = t; break
        todo = None
        val[t] = ve * ct / pe if inm else vf
        if act is None and inm and j >= kk:
            act = j; Bv = ct
        if j >= last:
            lastj = j; break
        if inm and act is not None:
            ok = bc is not None and ct < lo[bc]
            if bc is not None and not ok:
                cnt["擋出"] += 1
            if ok:
                todo = "f"; bc = None; continue
            if (j - act) % cs == 0 and ct >= Bv:
                Bv = ct
            bc = j if ct < Bv else None
        elif inm:
            ok = cand is not None and ct < lo[cand]
            if cand is not None and not ok:
                cnt["擋持"] += 1
            if ok:
                cand = None
                if nin >= 1:
                    todo = "a"; continue
                todo = "s"
                if warn and any(Wn[w][j] for w in ("W1", "W2", "W3", "W4")):
                    todo = "a"
            else:
                cand = j if ct < P0 * 0.9 else None
        else:
            m_ = j - sb + 1
            if warn and any(Wn[w][j] for w in ("W1", "W2", "W3", "W4")):
                todo = "a"
            elif ct >= P0 or j in nk:
                todo = "b"
            elif m_ == 15 and lim == 15:
                seg = lo[sb:j + 1]; mm = sb + max(i for i, v in enumerate(seg) if v == seg.min()); ca = False
                if j - mm >= 6:
                    mins = [lo[mm + 1 + 3 * q: mm + 4 + 3 * q].min() for q in range((j - mm) // 3)]
                    ca = all(v > lo[mm] for v in mins) and all(mins[q] < mins[q + 1] for q in range(len(mins) - 1))
                v5, v10, v20, v60 = (ma[w][j] for w in (5, 10, 20, 60))
                cb = j >= 5 and np.all(np.isfinite([v5, v10, v20, v60, ma[20][j - 5]])) and v5 > v10 > v20 and v20 > ma[20][j - 5] and v20 >= v60 * 0.98
                if ca or cb:
                    lim = 25
                else:
                    todo = "a"
            elif lim == 25 and m_ >= 25:
                todo = "a"
    if rel is None:
        t = int(idx[lastj])
        if not inm:
            rel = t + 1 if t + 1 < NP else NP - 1; val[rel] = vf
        elif lastj == kc or (lastj == nbk - 1 and nbk <= min(kc, n - 1)):
            rel = t
        else:
            rel = n0 if t == n0 - 1 else t
    if nout_ == 0:
        return None, rel, (val[rel] - 1.0 if rel in val and todo == "f" else float(cl[s][min(rel, NP - 1)]) / P0 - 1.0), cnt
    arr = np.array(cl[s], dtype=float, copy=True); cur = None
    for t in range(e, NP):
        cur = val.get(t, cur)
        if cur is not None:
            arr[t] = P0 * cur
    return arr, rel, arr[min(rel, NP - 1)] / P0 - 1.0, cnt


def main():
    RES = {}
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv"), dtype={"eq_sha": str}); TB = pd.read_csv(os.path.join(OUT, "cells.csv"))
    RR.use_snapshot()
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True); cal = ctx["cal"]; cl, op, NP = ctx["closes"], ctx["opens"], ctx["ncal"]; mk = ctx["mk"]; w0, w1 = ctx["w0"], ctx["w1"]
    base = ctx["sig13"]; ALL = RR._G["AND"]
    rvd = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "yoy"])
    rev = {s: list(zip(g["signal_pos"].astype(int), g["yoy"].astype(float))) for s, g in rvd.groupby("stock_id")}
    B = {s: C3.load(s, mk, cal, rev) for s in sorted(set(base["sid"]))}
    LM = {}
    for s in B:
        bb = R.load_bars(s, mk.get(s, "twse"), cal); c = bb["c"]
        LM[s] = (bb["l"], {n: np.array([c[i - n + 1:i + 1].mean() if i >= n - 1 else np.nan for i in range(len(c))]) for n in (5, 10, 20, 60)})
    newk = {s: set(g["k"].astype(int)) for s, g in ALL.groupby("sid")}
    SF = {}
    for s in sorted(cl):
        st_ = D.load_stock(s, mk.get(s, "twse"), cal)
        if st_ is None:
            continue
        v_ = np.flatnonzero(np.isfinite(st_.df["close"].to_numpy(float)))
        if len(v_) and v_[-1] < w1:
            SF[s] = int(v_[-1])
    bad = []; badc = []
    for K, cs, C, warn in ((55, 10, 120, True), (60, 10, 250, False)):
        rows = []; ac = {}; ao = {}; hm = {}; tot = {"擋持": 0, "擋出": 0}
        for s, k, e, x0, rv in zip(base["sid"], base["k"].astype(int), base["entry_pos"].astype(int), base["xpos_H60"].astype(int), base["relvol"]):
            if x0 < 0 or B.get(s) is None:
                rows.append((s, s, e, x0, np.nan, rv)); continue
            arr, xp, g, cnt = path(B[s], LM[s][0], LM[s][1], cl, op, s, k, e, K, cs, C, NP, len(cal), newk.get(s, set()), warn)
            if w0 <= e <= w1:
                tot["擋持"] += cnt["擋持"]; tot["擋出"] += cnt["擋出"]
            if arr is None:
                rows.append((s, s, e, xp, g, rv))
            else:
                key = f"{s}#{e}"; ac[key] = arr; ao[key] = op[s]; hm[key] = s; rows.append((key, s, e, xp, g, rv))
        T = pd.DataFrame(rows, columns=["sid", "u", "entry_pos", "xpos_HX", "g_HX", "relvol"])
        for u in set(T["u"]):
            hm.setdefault(u, u)
        SFJ = {**SF, **{k_: SF[u] for k_, u in hm.items() if u in SF and k_ != u}}
        eq = C3.run(T, "HX", {**cl, **ac}, {**op, **ao}, NP, SFJ, hm)
        nm = f"使用者v2_k{K}_c{cs}_C{C}" + ("" if warn else "_不看警訊")
        if C3.h16(eq) != SD[(SD["世界"] == "主") & (SD["格"] == nm)]["eq_sha"].iloc[0]:
            bad.append(nm)
        r = TB[TB["格"] == nm].iloc[0]
        if [tot["擋持"], tot["擋出"]] != [int(r["主_擋下_持有中"]), int(r["主_擋下_最後出場"])]:
            badc.append((nm, tot, [int(r["主_擋下_持有中"]), int(r["主_擋下_最後出場"])]))
        print(nm, "done", bad, badc, flush=True)
    RES["① 自寫 v2 兩格 ⇒ eq_sha ＝ seeds.csv"] = {"不符": bad, "過": not bad}
    RES["② 擋下（持有中／最後出場）＝ cells.csv"] = {"不符": badc, "過": not badc}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES["③ 閘（主程式）"] = {**S["閘"], "過": all(S["閘"].values())}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

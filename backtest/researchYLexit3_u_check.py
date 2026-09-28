# -*- coding: utf-8 -*-
"""營量出場 甲件 使用者版 v1：簡短查核（⛔ 不 import researchYLexit3_u、researchYLexit3、researchYLexit、researchYLexit3_b）。
警訊沿用 seq3 獨立查核（researchYLexit3_check.load，自寫）；兩天確認、15／25 天、(a)(b) 延長自寫 ⇒ 主世界 H40（看／不看警訊）種子 0 eq_sha ＝ user_v1/seeds.csv；
另核 cells.csv 的擋下、確認賣出、延長次數。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLexit3_u_check.py
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

OUT = "backtest/resultsYLexit3/user_v1"
COST = R.COST


def path(b, lo, ma, cl, op, s, k, e, x, NP, n0, nk, warn):
    idx = b["idx"]; W = b["W"]
    ke = k + 1; last = int(np.searchsorted(idx, (NP - 2) if x >= n0 else x, side="right") - 1)
    P0 = float(op[s][e]); inm = True; ve = 1.0; pe = P0; vf = 0.0; todo = None; val = {}; cand = None; sb = None; lim = 15; rel = None
    cnt = {"擋": 0, "確認賣": 0, "延長": None, "出": 0, "進": 0}
    for j in range(ke, last + 1):
        t = int(idx[j]); ot = float(op[s][t]); ct = float(cl[s][t])
        if todo == "s" and inm and np.isfinite(ot) and ot > 0:
            vf = ve * ot / pe; inm = False; sb = j; lim = 15; cnt["出"] += 1
        elif todo == "b" and not inm and np.isfinite(ot) and ot > 0:
            ve = vf * (1 - COST); pe = ot; inm = True; cand = None; cnt["進"] += 1
        elif todo == "a":
            if inm and np.isfinite(ot) and ot > 0:
                vf = ve * ot / pe; inm = False; cnt["出"] += 1
            val[t] = vf; rel = t; break
        todo = None
        val[t] = ve * ct / pe if inm else vf
        if j >= last:
            break
        if inm:
            ok = cand is not None and ct < lo[cand]
            if cand is not None and not ok:
                cnt["擋"] += 1
            if ok:
                cand = None; cnt["確認賣"] += 1
                if cnt["進"] >= 1:
                    todo = "a"; continue
                todo = "s"
                if warn and any(W[w][j] for w in ("W1", "W2", "W3", "W4")):
                    todo = "a"
            else:
                cand = j if ct < P0 * 0.9 else None
        else:
            n = j - sb + 1
            if warn and any(W[w][j] for w in ("W1", "W2", "W3", "W4")):
                todo = "a"
            elif ct >= P0 or j in nk:
                todo = "b"
            elif n == 15 and lim == 15:
                seg = lo[sb:j + 1]; m = sb + max(i for i, v in enumerate(seg) if v == seg.min())
                ca = False
                if j - m >= 6:
                    mins = [lo[m + 1 + 3 * q: m + 4 + 3 * q].min() for q in range((j - m) // 3)]
                    ca = all(v > lo[m] for v in mins) and all(mins[q] < mins[q + 1] for q in range(len(mins) - 1))
                m5, m10, m20, m60 = (ma[w][j] for w in (5, 10, 20, 60))
                cb = j >= 5 and np.all(np.isfinite([m5, m10, m20, m60, ma[20][j - 5]])) and m5 > m10 > m20 and m20 > ma[20][j - 5] and m20 >= m60 * 0.98
                if ca or cb:
                    lim = 25; cnt["延長"] = ("a" if ca else "") + ("b" if cb else "")
                else:
                    todo = "a"
            elif lim == 25 and n >= 25:
                todo = "a"
    if cnt["出"] == 0:
        return None, x, None, cnt
    arr = np.array(cl[s], dtype=float, copy=True); cur = None
    for t in range(e, NP):
        cur = val.get(t, cur)
        if cur is not None:
            arr[t] = P0 * cur
    xp = rel if rel is not None else x
    return arr, xp, arr[min(xp, NP - 1)] / P0 - 1, cnt


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
    sj = C3.exit_h(base, 40, B, len(cal), {})
    bad = []; badc = []
    for warn in (True, False):
        rows = []; ac = {}; ao = {}; hm = {}; tot = {"擋": 0, "確認賣": 0, "a": 0, "b": 0, "ab": 0}
        for s, k, e, x, g0, rv in zip(sj["sid"], sj["k"].astype(int), sj["entry_pos"].astype(int), sj["xpos_H40"].astype(int), sj["g_H40"].astype(float), sj["relvol"]):
            if B.get(s) is None:
                rows.append((s, s, e, x, g0, rv)); continue
            arr, xp, g, cnt = path(B[s], LM[s][0], LM[s][1], cl, op, s, k, e, x, NP, len(cal), newk.get(s, set()), warn)
            if w0 <= e <= w1:
                tot["擋"] += cnt["擋"]; tot["確認賣"] += cnt["確認賣"]
                if cnt["延長"]:
                    tot[cnt["延長"]] += 1
            if arr is None:
                rows.append((s, s, e, x, g0, rv)); continue
            key = f"{s}#{e}"; ac[key] = arr; ao[key] = op[s]; hm[key] = s; rows.append((key, s, e, xp, g, rv))
        T = pd.DataFrame(rows, columns=["sid", "u", "entry_pos", "xpos_H40", "g_H40", "relvol"])
        for u in set(T["u"]):
            hm.setdefault(u, u)
        SFJ = {**SF, **{k_: SF[u] for k_, u in hm.items() if u in SF and k_ != u}}
        eq = C3.run(T, "H40", {**cl, **ac}, {**op, **ao}, NP, SFJ, hm)
        nm = "使用者v1_H40" + ("" if warn else "_不看警訊")
        if C3.h16(eq) != SD[(SD["世界"] == "主") & (SD["格"] == nm)]["eq_sha"].iloc[0]:
            bad.append(nm)
        r = TB[TB["格"] == nm].iloc[0]
        mine = [tot["擋"], tot["確認賣"], tot["a"], tot["b"], tot["ab"]]; ref = [r["主_擋下次數"], r["主_確認賣出次數"], r["主_延長_a"], r["主_延長_b"], r["主_延長_ab"]]
        if [int(v) for v in mine] != [int(v) for v in ref]:
            badc.append((nm, mine, ref))
        print(nm, "done", bad, badc, flush=True)
    RES["① 自寫使用者版 H40（看／不看警訊）⇒ eq_sha ＝ seeds.csv"] = {"不符": bad, "過": not bad}
    RES["② 擋下、確認賣出、延長 a／b／ab 次數 ＝ cells.csv"] = {"不符": badc, "過": not badc}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    RES["③ 閘（主程式）"] = {**S["閘"], "過": all(S["閘"].values())}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG季節性 seq1 獨立查核（⛔ 不 import researchSeason）。
世界資料照本體來源取（researchT1fix.build_ctx(True)、researchV.body_setup("main")），季節性邏輯、bench 序列、統計全部自寫；引擎 research11.simulate_mtm。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSeason_check.py

 ① 挑中格（兩個世界）種子 0、1：自寫停買／切倉／0050 序列 ⇒ 引擎權益 sha ＝ seeds.csv
 ② 自 seeds.csv 重算：各格中位、同顆配對差中位、K7 進場數、挑格
 ③ 年為單位差：自算逐年差 ＝ cells.csv；自寫 bootstrap（另一個種子）CI 與判定一致（容差 0.01）
 ④ 假訊號 p ＝ summary
 ⑤ 0050 各段 ＝ summary
"""
from __future__ import annotations
import hashlib, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR
from backtest import research13 as R13

OUT = "backtest/resultsSeason"
MON = {"1月": (1,), "1～2月": (1, 2), "1～3月": (1, 2, 3)}
SP = {"營飆": ("H120", 10, 1000), "營量": ("H60", 20, 7000)}
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "早年": ("2012-06-04", "2014-12-31")}


def wm(eq, first, end, a, b):
    lo = min(first, a)
    return R13.window_stats(eq, lo, max(end, b + 1), a, b + 1)


def main():
    RES = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    DF = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip", low_memory=False)
    T = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    picks = {s: v["格"] for s, v in S["挑格"].items() if "不可判定" not in v["格"]}
    # ①
    bad1 = []; n1 = 0; Z5 = {}
    for wk in ("main", "early"):
        RR.use_snapshot()
        if wk == "main":
            from backtest import researchT1fix as T1
            ctx = T1.build_ctx(True); cal = ctx["cal"]; NP = ctx["ncal"]; w1 = ctx["w1"]; cl, op = ctx["closes"], ctx["opens"]
            sigs = {"營飆": ctx["sig"], "營量": ctx["sig13"]}; mk = ctx["mk"]
        else:
            from backtest import researchV as V
            from backtest import researchYear1M as Y
            V.body_setup("main", lambda x: None)
            cal = V._B["cal"]; w0, w1 = V._B["w0"], V._B["w1"]; NP = Y._G["NP"]; cl, op = Y._G["closes"], Y._G["opens"]; mk = Y._G["uni"]
            sigs = {"營飆": Y.sig_of(1, "mtm", w0, w1), "營量": Y.sig_of(13, "mtm", w0, w1)}
        pool = sorted(cl) if wk == "main" else sorted(set(sigs["營飆"]["sid"]) | set(sigs["營量"]["sid"]))
        SF = {}
        for s in pool:
            st = D.load_stock(s, mk.get(s, "twse"), cal)
            if st is None:
                continue
            v = np.flatnonzero(np.isfinite(st.df["close"].to_numpy(float)))
            if len(v) and v[-1] < w1:
                SF[s] = int(v[-1])
        bc = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(); bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float)
        for sg in (("探索", "確認") if wk == "main" else ("早年",)):
            a_ = int(cal.searchsorted(pd.Timestamp(SEG[sg][0]))); b_ = int(cal.searchsorted(pd.Timestamp(SEG[sg][1]), side="right") - 1)
            c5, m5 = wm(bc, 0, len(cal), a_, b_)
            Z5[sg] = (abs(c5 - S["0050"][sg]["年化"]), abs(m5 - S["0050"][sg]["回落"]))
        for strat, pk in picks.items():
            m, mo = pk.split("_"); rule, N, s0 = SP[strat]
            inm = np.zeros(NP, bool); inm[:len(cal)] = np.isin(cal.month, MON[mo])
            sig = sigs[strat]; sig = sig[~inm[sig["entry_pos"].to_numpy(int)]].copy()
            if m == "丙":
                first = [t for t in range(1, NP) if inm[t] and not inm[t - 1]]
                xs, gs = f"xpos_{rule}", f"g_{rule}"
                for i in range(len(sig)):
                    e = int(sig.iat[i, sig.columns.get_loc("entry_pos")]); x = int(sig.iat[i, sig.columns.get_loc(xs)]); sid = sig.iat[i, sig.columns.get_loc("sid")]
                    f = next((t for t in first if t > e), None)
                    if f is not None and f <= x:
                        px = op[sid][f] if (np.isfinite(op[sid][f]) and op[sid][f] > 0) else cl[sid][f - 1]
                        sig.iat[i, sig.columns.get_loc(xs)] = f; sig.iat[i, sig.columns.get_loc(gs)] = px / op[sid][e] - 1.0
            kw = {}
            if m in ("乙", "丙"):
                c = np.r_[bc, bc[-1]]; o = np.r_[bo, np.nan]
                B = [1.0]
                for t in range(1, NP):
                    ot = o[t] if (np.isfinite(o[t]) and o[t] > 0) else c[t - 1]
                    if inm[t] and not inm[t - 1]:
                        B.append(B[-1] * (c[t] / ot))
                    elif inm[t] and inm[t - 1]:
                        B.append(B[-1] * (c[t] / c[t - 1]))
                    elif inm[t - 1]:
                        B.append(B[-1] * (ot / c[t - 1] * (1 - 0.00385)))
                    else:
                        B.append(B[-1])
                kw = dict(cash_mode="bench", bench=np.array(B), bench_cost=0.0)
            if strat == "營量":
                kw.update(log=[], d_max=None, pick="relvol", queue_days=0)
            for r in (0, 1):
                o_ = R.simulate_mtm(sig, rule, N, np.random.default_rng(s0 + r), cl, op, NP, return_equity=True, stop_force=SF, **kw)
                h = hashlib.sha256(np.asarray(o_["equity"], float).tobytes()).hexdigest()[:16]
                ref = DF[(DF["world"] == wk) & (DF["kind"] == "cell") & (DF["strat"] == strat) & (DF["cell"] == pk) & (DF["r"] == r)]["eq_sha"].iloc[0]
                n1 += 1
                if h != ref:
                    bad1.append((wk, strat, pk, r))
        print(wk, "done", bad1, flush=True)
    RES["① 挑中格自寫變體 ⇒ 權益 sha（兩世界 × 種子 0、1）"] = {"比對": n1, "不符": bad1, "過": not bad1}
    # ②⑤
    Z = S["0050"]; bad2 = []
    for (wk, s), base in DF[DF["kind"] == "base"].groupby(["world", "strat"]):
        base = base.set_index("r")
        for sg in (("探索", "確認") if wk == "main" else ("早年",)):
            rb = T[(T["世界"] == wk) & (T["策略"] == s) & (T["格"] == "原策略") & (T["段"] == sg)].iloc[0]
            if abs(base[f"{sg}_年化"].median() - rb["年化中位"]) > 1e-15:
                bad2.append((wk, s, "原", sg))
            for cellname, c in DF[(DF["world"] == wk) & (DF["kind"] == "cell") & (DF["strat"] == s)].groupby("cell"):
                c = c.set_index("r")
                rc = T[(T["世界"] == wk) & (T["策略"] == s) & (T["格"] == cellname) & (T["段"] == sg)].iloc[0]
                d = (c[f"{sg}_年化"] - base[f"{sg}_年化"]).median()
                if abs(d - rc["年化差中位"]) > 1e-15 or abs(c[f"{sg}_年化"].median() - rc["年化中位"]) > 1e-15:
                    bad2.append((wk, s, cellname, sg))
    # 挑格（自算 K7）
    selfpick = {}
    for s in ("營飆", "營量"):
        base = DF[(DF["world"] == "main") & (DF["kind"] == "base") & (DF["strat"] == s)].set_index("r")
        cand = []
        for cellname in sorted(DF[(DF["world"] == "main") & (DF["kind"] == "cell") & (DF["strat"] == s)]["cell"].unique()):
            m, mo = cellname.split("_")
            cols = [k for k in base.columns if k.startswith("b20") and int(k[6:8]) in MON[mo] and "2017-03" <= k[1:] <= "2021-12"]
            nb = float(base[cols].fillna(0).sum(axis=1).median()) if cols else 0.0
            c = DF[(DF["world"] == "main") & (DF["kind"] == "cell") & (DF["strat"] == s) & (DF["cell"] == cellname)].set_index("r")
            cand.append((cellname, float((c["探索_年化"] - base["探索_年化"]).median()), float(c["探索_年化"].median() / abs(c["探索_回落"].median())), nb))
        ok = [x for x in cand if x[3] >= 20]
        selfpick[s] = sorted(ok, key=lambda x: (-x[1], -x[2]))[0][0] if ok else None
    RES["② 中位、配對差、K7、挑格"] = {"不符": bad2, "自挑": selfpick, "過": not bad2 and all(selfpick[s] == picks.get(s) for s in selfpick)}
    # 0050
    RES["⑤ 0050 各段（自算 window_stats）"] = {"差": Z5, "過": all(max(v) < 1e-15 for v in Z5.values())}
    # ③
    rng = np.random.default_rng(777); bad3 = []
    for r_ in T[T["格"] != "原策略"].itertuples():
        yd = json.loads(r_.逐年差)
        base = DF[(DF["world"] == r_.世界) & (DF["kind"] == "base") & (DF["strat"] == r_.策略)].set_index("r")
        c = DF[(DF["world"] == r_.世界) & (DF["kind"] == "cell") & (DF["strat"] == r_.策略) & (DF["cell"] == r_.格)].set_index("r")
        mine = {y: float((c[f"y{y}"] - base[f"y{y}"]).mean()) for y in yd}
        if any(abs(mine[y] - yd[y]) > 1e-6 for y in yd):
            bad3.append((r_.世界, r_.策略, r_.格, r_.段, "逐年差")); continue
        v = np.array(list(mine.values()))
        if len(v) < 3:
            ok = r_.年判定.startswith("依構造")
        else:
            bm = v[rng.integers(0, len(v), size=(20000, len(v)))].mean(1); lo, hi = np.percentile(bm, [2.5, 97.5])
            vv = "多賺" if lo > 0 else ("少賺" if hi < 0 else "測不出")
            ok = (vv == r_.年判定) or (min(abs(lo), abs(hi)) < 0.01)
            ok = ok and abs(lo - r_.年CI下) < 0.01 and abs(hi - r_.年CI上) < 0.01
        if not ok:
            bad3.append((r_.世界, r_.策略, r_.格, r_.段))
    RES["③ 年為單位差與 bootstrap 判定"] = {"不符": bad3, "過": not bad3}
    # ④
    bad4 = []
    for s, pk in picks.items():
        for wk, sg in (("main", "確認"), ("early", "早年"), ("main", "探索")):
            base = DF[(DF["world"] == wk) & (DF["kind"] == "base") & (DF["strat"] == s)].set_index("r")
            fk = DF[(DF["world"] == wk) & (DF["kind"] == "fake") & (DF["strat"] == s)]
            fd = fk[f"{sg}_年化"].to_numpy() - base.loc[fk["r"].to_numpy(), f"{sg}_年化"].to_numpy()
            real = T[(T["世界"] == wk) & (T["策略"] == s) & (T["格"] == pk) & (T["段"] == sg)].iloc[0]["年化差中位"]
            p = float(np.mean(fd >= real))
            if abs(p - S["判定"][s][sg]["假訊號 p（隨機 ≥ 配對差中位）"]) > 1e-12:
                bad4.append((s, sg))
    RES["④ 假訊號 p"] = {"不符": bad4, "過": not bad4}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

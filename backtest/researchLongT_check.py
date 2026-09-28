# -*- coding: utf-8 -*-
"""researchLongT 獨立查核（另一套寫法）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchLongT_check.py

① 樣板：主窗 2 個換股日（探索、確認各一）＋ 早年 1 個，全橫斷面自己重算八條（逐檔讀 load_stock、有效 K 棒用切片算 MA／高低／r_n，不用 rolling）、
   RS 名次自己排、eligible 自己讀面板＋gate3（innov_ky 開）；比對主程式 researchLongT.tables 的 樣板集合、RS、挑中格名單（前 N）
   （營收旗標共用 p4_features.rev_hi24_flags，寫明）
② 溫斯坦：主窗抽 3 筆訊號，週 K 用 pandas W-SUN 期間分組、條件自己算，比對進出場日與 g
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchLongT as RL
from backtest import researchMomX as MX
from backtest import universe_gate as UG
D, H2 = MX.D, MX.H2
OUT = "backtest/resultsLongT"


def indep_template(cfg, cal, e, flag):
    D.DATA = cfg["data"]
    pan = pd.read_csv(cfg["panel"], dtype={"stock_id": str}, parse_dates=["measure_date"])
    g = pan[pan["measure_date"] == cal[e - 1]]
    tf = lambda s: s.astype(str).isin(["True", "1"])
    el = (tf(g["liq_ok"]) & tf(g["bars_ok"])) if cfg["elig"] == "eligible_v" else tf(g["eligible"])
    stocks = pd.read_csv(os.path.join(cfg["data"], "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    mk = dict(zip(G["stock_id"], G["market"]))
    ok = sorted(set(g.loc[el.to_numpy(), "stock_id"]) & set(mk))
    RS = {}; C7 = set(); REV = set()
    fcol = {s: j for j, s in enumerate(flag.columns)}; fl = flag.to_numpy(float)
    for s in ok:
        st = D.load_stock(s, mk[s], cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float); v = np.flatnonzero(np.isfinite(c)); v = v[v <= e - 1]
        if len(v) < 253:
            continue
        cb = c[v]; i = len(cb) - 1; C = cb[i]
        ma = lambda n_, j=i: math.fsum(cb[j - n_ + 1:j + 1]) / n_          # fsum：正確捨入（平盤股 C ＝ MA 的相等要判得出來）
        r = lambda n_: cb[i] / cb[i - n_] - 1
        RS[s] = 2 * r(63) + r(126) + r(189) + r(252)
        if (C > ma(150) and C > ma(200) and ma(150) > ma(200) and ma(200) > ma(200, i - 21) and ma(50) > ma(150) and ma(50) > ma(200) and C > ma(50)
                and C >= cb[i - 249:i + 1].min() * 1.3 and C >= cb[i - 249:i + 1].max() * 0.75):
            C7.add(s)
        j = fcol.get(s)
        if j is not None and fl[e - 1, j] == 100:
            REV.add(s)
    order = sorted(RS, key=lambda s: (-RS[s], s)); top = set(order[:int(math.ceil(0.3 * len(order)))])
    return RS, C7 & top, REV


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    pick = S["挑中"]["格"]; fam, fq, N = pick.split("_"); N = int(N[1:])
    rep = {"挑中格": pick, "樣板": [], "溫斯坦": []}; bad = 0
    for tag, cfg in (("主", RL.MAIN), ("早年", RL.EARLY)):
        Wd = MX.load_world(cfg, 2, print)
        D.DATA = cfg["data"]
        flag, _ = RL.rev_flags(Wd["cal"], tag == "主")
        TT, RSB = RL.tables(Wd, flag)
        cal = Wd["cal"]
        es = [e for e in Wd["rebs"] if (fq == "月" or cal[e].month in (1, 4, 7, 10))]
        dates = ([es[len(es) // 4], es[3 * len(es) // 4]] if tag == "主" else [es[len(es) // 2]])
        sel = RL.select(Wd, TT, fam, fq, N)
        for e in dates:
            RS, TM, REV = indep_template(cfg, cal, e, flag)
            mine_sel = sorted((TM if fam == "甲" else TM & REV), key=lambda s: (-RS[s], s))[:N]
            d = {"世界": tag, "換股日": str(cal[e].date()), "RS 可算檔數 本支／主程式": [len(RS), len(TT[e]["RS"])],
                 "RS 最大差": float(max([abs(RS[s] - TT[e]["RS"][s]) for s in set(RS) & set(TT[e]["RS"])] + [0.0])),
                 "RS 集合差": len(set(RS) ^ set(TT[e]["RS"])), "樣板集合差": len(TM ^ TT[e]["tmpl"]), "樣板檔數": len(TM),
                 "名單相同": mine_sel == sel[e], "名單": mine_sel}
            b = d["RS 集合差"] + d["樣板集合差"] + int(d["RS 最大差"] > 1e-9) + int(not d["名單相同"])
            d["不符"] = b; bad += b; rep["樣板"].append(d); print("[樣板]", json.dumps(d, ensure_ascii=False), flush=True)
        if tag == "主":
            # 溫斯坦：抽 3 筆
            D.DATA = cfg["data"]
            stocks = pd.read_csv(os.path.join(cfg["data"], "meta", "stocks.csv"), dtype=str); mkd = dict(zip(stocks["stock_id"], stocks["market"]))
            VOL = {}
            import random
            sids = sorted(Wd["sids"]); rng = random.Random(20260928); cand = rng.sample(sids, 60)
            for s in cand:
                st = D.load_stock(s, mkd.get(s, "twse"), cal)
                VOL[s] = None if st is None else pd.to_numeric(st.df["volume"], errors="coerce").to_numpy(np.float64)
            Wsub = dict(Wd); Wsub["sids"] = cand
            main_sig = weinstein_rows(Wsub, VOL, RSB)
            per = cal.to_period("W-SUN"); TP = list(pd.unique(per)); ti = {q: i for i, q in enumerate(TP)}
            bench = Wd["bench"]; bw = pd.Series(bench, index=cal).groupby(per).last()
            n_ok = 0
            for r in main_sig.head(200).itertuples():
                if n_ok >= 3:
                    break
                s = r.sid; P = Wd["P"][s]; v = P["valid"]
                df = pd.DataFrame({"o": P["o"], "c": P["c"], "v": VOL[s]}, index=cal)[v]
                W = df.groupby(df.index.to_period("W-SUN")).agg(O=("o", "first"), C=("c", "last"), V=("v", "sum"))
                q = cal[r.pos].to_period("W-SUN"); t = list(W.index).index(q)
                C = W["C"].to_numpy(); V = W["V"].to_numpy()
                ma30 = lambda j: C[j - 29:j + 1].mean()
                rsl = C / bw.reindex(W.index).to_numpy()
                cond = (t >= 51 and ma30(t) > ma30(t - 4) and C[t] > C[t - 26:t].max() and V[t] >= 2 * V[t - 10:t].mean() and rsl[t] > rsl[t - 51:t + 1].mean())
                ent_q = TP[ti[q] + 1]; days = np.flatnonzero((per == ent_q) & v); ent = int(days[0])
                xs = None
                for t2 in range(t + 1, len(W)):
                    if ti[W.index[t2]] < ti[ent_q]:
                        continue
                    if C[t2] < ma30(t2):
                        xs = W.index[t2]; break
                if xs is not None and ti[xs] + 1 < len(TP):
                    nxt = np.flatnonzero(v & (np.arange(len(cal)) >= np.flatnonzero(per == TP[ti[xs] + 1])[0]))
                    xp = int(nxt[0]) if len(nxt) else len(cal) - 1
                    g = P["o"][xp] / P["o"][ent] - 1 if len(nxt) else P["c"][-1] / P["o"][ent] - 1
                else:
                    xp = len(cal) - 1; g = P["c"][-1] / P["o"][ent] - 1
                d = {"sid": s, "訊號週": str(q), "本支條件成立": bool(cond), "進場 本支／主程式": [ent, int(r.entry_pos)], "出場 本支／主程式": [xp, int(r.xpos_W)],
                     "g 差": float(abs(g - r.g_W))}
                b = int(not cond) + int(ent != r.entry_pos) + int(xp != r.xpos_W) + int(d["g 差"] > 1e-9)
                d["不符"] = b; bad += b; rep["溫斯坦"].append(d); n_ok += 1; print("[溫斯坦]", json.dumps(d, ensure_ascii=False), flush=True)
    rep["合計不符"] = bad
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不符", bad)


def weinstein_rows(Wd, VOL, RSB):
    """主程式的訊號列（只取訊號表、不跑引擎）：重用 researchLongT.weinstein 的前半段。"""
    import types
    src = RL.weinstein
    rows = []
    # 直接呼叫主程式函式，攔下引擎：用一個 0 檔的 stop_force 跑一次也可，但這裡只要 sig ⇒ 暫換 simulate_mtm
    orig = RL.R11.simulate_mtm
    RL.R11.simulate_mtm = lambda sig, *a_, **k_: (rows.append(sig), {"equity": np.ones(1)})[1]
    try:
        src(Wd, VOL, RSB, "查核", lambda m: None)
    finally:
        RL.R11.simulate_mtm = orig
    return rows[0]


if __name__ == "__main__":
    main()

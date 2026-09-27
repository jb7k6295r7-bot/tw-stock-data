# -*- coding: utf-8 -*-
"""researchYLretest 第一批的獨立查核（⛔ 不 import researchYLretest）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLretest_check.py [--n 3]

① 從 b1_seeds.csv 自己算各格中位、比值、標籤（0050 同窗自己算）、④ 配對差 CI ⇒ 對 summary.json
② 停止交易股：自己用 D.load_stock 找「最後有效收盤 ＜ 主窗尾、之後沒有成交」⇒ 檔數對 summary
③ 假訊號：照檔頭寫的抽樣規格自己重建第 0～n−1 次的假訊號列（relvol、H60 出場用自己寫的迴圈），自己呼叫引擎 ⇒ 年化／回落 對 b1_fake.csv；
   並驗每筆假訊號與對應真訊號同月、當天有 K 棒
④ 219 取最好估計：從 b1_fake.csv 自己算 F(1.124)、K＝219／17 的百分位
"""
from __future__ import annotations
import argparse, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import research11 as R
from backtest import universe_gate as UG
OUT = os.path.expanduser("~/tw-p17/backtest/resultsYLretest")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=3); a = ap.parse_args()
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    Sd = pd.read_csv(os.path.join(OUT, "b1_seeds.csv"), float_precision="round_trip"); FK = pd.read_csv(os.path.join(OUT, "b1_fake.csv"), float_precision="round_trip")
    cal = D.load_calendar(); w0, w1 = RR.win_bounds(cal); bench = RR.load_bench(cal)
    for k, g in Sd.groupby("key"):
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        ws = w0 + int(k.split("+")[1]) if "起點+" in k else w0
        b = RR.bench_row(cal, bench, ws, w1 + 1); r50 = b["cagr"] / abs(b["mdd"])
        lab = "合格" if (c > b["cagr"] and c / abs(m) >= r50) else ("另列" if c > b["cagr"] else "不合格")
        x = S["格"][k]
        if abs(x["年化中位"] - c) > 1e-15 or abs(x["回落中位"] - m) > 1e-15 or x["標籤"] != lab:
            errs.append(f"格 {k}")
    on = Sd[Sd["key"] == "#13_開"].set_index("r"); s14 = Sd[Sd["key"] == "#14_開"].set_index("r")
    d = (on["cagr"] - s14["cagr"]).to_numpy(); ci = [d.mean() - 1.96 * d.std(ddof=1) / math.sqrt(len(d)), d.mean() + 1.96 * d.std(ddof=1) / math.sqrt(len(d))]
    if max(abs(ci[0] - S["④relvol減隨機"]["cagr"]["CI"][0]), abs(ci[1] - S["④relvol減隨機"]["cagr"]["CI"][1])) > 1e-12:
        errs.append("④ CI")
    # ② 停止交易股
    U = D.load_universe(); U = U[U["stock_id"].isin(set(UG.gate3(pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str))["stock_id"]))]
    mk = U.set_index("stock_id")["market"]; n_stop = 0; last = {}
    for s in sorted(U["stock_id"]):
        st = D.load_stock(s, mk[s], cal)
        if st is None:
            continue
        v = np.flatnonzero(np.isfinite(st.df["close"].to_numpy(float)))
        if len(v):
            last[s] = int(v[-1])
            n_stop += int(v[-1] < w1)
    if n_stop != S["停止交易股（母體、主窗內）"]:
        errs.append(f"② 停止交易股 {n_stop} vs {S['停止交易股（母體、主窗內）']}")
    info["停止交易股"] = n_stop
    # ③ 假訊號重建
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", lambda x: None)
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    real = AND[(e >= w0) & (e <= w1)]; real = real[real["xpos_H60"] >= 0]
    mon = np.array([str(x)[:7] for x in cal])
    closes, opens = RR.load_prices(sorted(set(U["stock_id"])), cal, mk, "branch")
    for s_ in G["closes"]:
        closes[s_] = G["closes"][s_]; opens[s_] = G["opens"][s_]
    bars = {}; alive = {}
    for s_ in sorted(closes):
        B = R.load_bars(s_, mk.get(s_, "twse"), cal)
        if B is None:
            continue
        bars[s_] = B
        for dd in B["idx"]:
            alive.setdefault(int(dd), []).append(s_)
    SF = {s_: L for s_, L in last.items() if L < w1 and s_ in closes}
    for i in range(a.n):
        rng = np.random.default_rng([20260927, i]); rows = []
        for m_ in mon[real["pos"].to_numpy(int)]:
            ds = [d_ for d_ in range(len(cal)) if mon[d_] == m_]
            for _ in range(50):
                d_ = ds[int(rng.integers(len(ds)))]
                pool = alive.get(d_)
                if not pool:
                    continue
                sid = pool[int(rng.integers(len(pool)))]
                B = bars[sid]; idx = B["idx"]
                k = int(np.searchsorted(idx, d_))
                if k + 1 >= len(idx):
                    continue
                if int(idx[k]) != d_ or mon[d_] != m_:
                    errs.append(f"③ 第 {i} 次 {sid} 日期不對")
                amt = B["amt"]
                if k >= 60:
                    w = [x for x in amt[k - 60:k] if math.isfinite(x)]
                    med = float(np.median(w)) if w else float("nan")
                    rel = float(amt[k]) / med if med > 0 and math.isfinite(amt[k]) else float("nan")
                else:
                    rel = float("nan")
                nb = B["next_bad"][max(0, k - 20)]; ex = k + 60 - 1 + 1       # 進場 k＋1、持有 60 根 ⇒ 出場根 k＋60
                if nb > k and ex < len(B["c"]) and ex < nb:
                    xp, g = int(idx[ex]), float(B["c"][ex] / B["o"][k + 1] - 1)
                else:
                    xp, g = -1, float("nan")
                rows.append((sid, k, d_, int(idx[k + 1]), xp, g, rel))
                break
        F = pd.DataFrame(rows, columns=["sid", "k", "pos", "entry_pos", "xpos_H60", "g_H60", "relvol"]).drop_duplicates(["sid", "entry_pos"])
        F = F[(F["entry_pos"] >= w0) & (F["entry_pos"] <= w1)].reset_index(drop=True)
        s = R.simulate_mtm(F, "H60", 20, np.random.default_rng(7000 + i), closes, opens, len(cal), return_equity=True, log=[], d_max=None,
                           pick="relvol", queue_days=0, stop_force=SF)
        c, m, _ = RR.win_metrics(s["equity"], s["first"], s["end"], w0, w1)
        ref = FK[FK["i"] == i].iloc[0]
        if repr(float(c)) != repr(float(ref["cagr"])) or repr(float(m)) != repr(float(ref["mdd"])):
            errs.append(f"③ 第 {i} 次：自己 {c}／{m} vs 檔 {ref['cagr']}／{ref['mdd']}")
    info["假訊號重建次數"] = a.n
    # ④ 百分位
    Fc = float((FK["ratio"] <= 1.124).mean()); E_ = S["②假訊號"]["219取最好_估計"]
    if abs(Fc - E_["F(1.124)"]) > 1e-15 or abs(Fc ** 219 - E_["K=219 百分位"]) > 1e-12 or abs(Fc ** 17 - E_["K=17 百分位"]) > 1e-12:
        errs.append("④ 百分位")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:20]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()

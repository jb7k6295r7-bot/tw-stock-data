# -*- coding: utf-8 -*-
"""PREREGV 早年段本體的獨立查核（⛔ 不 import researchV／early_data／任何策略程式；只讀它們寫出的檔與原始資料）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchV_check.py

查核項（每項印 ✅／⛔，全部寫進 resultsV/body_check.json）：
  ① 0050 同窗（判定窗、描述段）：從版面的 stocks/0050.csv＋adj/0050.csv 自己還原（F(d)＝事件日 > d 的 8 位因子連乘；主程式用 8 位 cum_factor ⇒ 容差 1e−7）、自己算年化與回落，對 body_summary.json
  ② 0050 的 adj 因子：逐筆對原始 early/exright 的 (前收 − 權值+息值) ÷ 前收（含 2011-10-26）
  ③ 每個版本 × 格：從 body_seeds 自己取中位、比值、Q／R／F，對 body_cells.csv
  ④ Bonferroni 下界：從 body_meanret 自己寫月分群 bootstrap（另一個種子、另一種抽法），對 body_cells 的下界（同號、差 ＜ 1.5 點）
  ⑤ #25 對 #1 同種子 皆正／皆負；#26 的百分位（中位秩）
  ⑥ 假訊號臂 x（逐條重算）
  ⑦ 版面：R2 收進來的代號數、官方減資事件數（原始 early/reduce 去重）
  ⑧ 結果句必附三件
"""
import glob
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsV")
SNAP = os.path.expanduser("~/earlydata/3edc0e2206")
LAY = os.path.join(SNAP, "main", "data")
RAW = os.path.join(SNAP, "raw", "data")
ANN = 245
RES = {}


def ok(name, cond, detail=""):
    RES[name] = {"過": bool(cond), "detail": detail}
    print(("✅" if cond else "⛔"), name, detail, flush=True)


def cal_():
    return pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(LAY, "meta", "calendar_twse.csv"))["date"]))


def bench_close(cal):
    px = pd.read_csv(os.path.join(LAY, "stocks", "0050.csv"), dtype={"date": str})
    px["date"] = pd.to_datetime(px["date"]); px = px.drop_duplicates("date").set_index("date")["close"].astype(float)
    adj = pd.read_csv(os.path.join(LAY, "adj", "0050.csv"), dtype={"date": str})
    ev = [(pd.Timestamp(d), float(f)) for d, f in zip(adj["date"], adj["factor"])]
    F = np.array([np.prod([f for d, f in ev if d > t]) for t in px.index])
    return (px * F).reindex(cal).ffill().to_numpy()


def stats(seg):
    n = len(seg)
    cagr = (seg[-1] / seg[0]) ** (1 / (n / ANN)) - 1
    pk = np.maximum.accumulate(seg)
    return cagr, float(((seg - pk) / pk).min())


def win(cal, v):
    if v == "desc":
        per = cal.strftime("%Y-%m")
        return int(np.flatnonzero(per == "2008-01")[0]) + 1, int(np.flatnonzero(per == "2012-05")[-1])
    return int(cal.searchsorted(pd.Timestamp("2012-06-04"))), len(cal) - 1


def label(c, m, bc, bm):
    r, br = c / abs(m), bc / abs(bm)
    return ("Q" if (c > bc and r >= br) else ("R" if c > bc else "F")), r


def main():
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "body_cells.csv"))
    SD = pd.read_csv(os.path.join(OUT, "body_seeds.csv.gz"), float_precision="round_trip")
    PL = pd.read_csv(os.path.join(OUT, "body_placebo.csv.gz"), float_precision="round_trip")
    cal = cal_(); b = bench_close(cal)
    # ①
    B = {}
    for v in ("main", "desc"):
        if v not in S["0050"]:
            continue
        w0, w1 = win(cal, v)
        c, m = stats(b[w0:w1 + 1] / b[w0])
        B[v] = (c, m)
        ok(f"① 0050 {v} 窗 年化／回落", abs(c - S["0050"][v]["cagr"]) < 1e-7 and abs(m - S["0050"][v]["mdd"]) < 1e-7,
           f"本檔 {c:.10f}／{m:.10f}｜body {S['0050'][v]['cagr']:.10f}／{S['0050'][v]['mdd']:.10f}")
    # ②
    ex = pd.concat([pd.read_csv(f, dtype=str) for f in glob.glob(os.path.join(RAW, "early", "exright", "*.csv")) if not os.path.basename(f).startswith("_")])
    ex = ex[ex["stock_id"] == "0050"].sort_values("date")
    adj = pd.read_csv(os.path.join(LAY, "adj", "0050.csv"), dtype={"date": str})
    mine = [(d, (float(p) - float(v)) / float(p)) for d, p, v in zip(ex["date"], ex["pre_close"], ex["value"])]
    same = len(mine) == len(adj) and all(d == a and abs(f - float(g)) < 5e-9 for (d, f), a, g in zip(mine, adj["date"], adj["factor"]))
    ok("② 0050 adj 因子 ＝ (前收−息值)/前收（原始 TWT49U）", same, f"{len(mine)} 筆；含 2011-10-26：{'2011-10-26' in set(adj['date'])}")
    # ③
    bad = 0; n = 0
    for (v, cid), g in SD.groupby(["variant", "cell"]):
        if cid in (0,):
            continue
        q = C[(C["variant"] == v) & (C["編號"] == cid)]
        if not len(q):
            continue
        bc, bm = S["0050"][v]["cagr"], S["0050"][v]["mdd"]
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, r = label(c, m, bc, bm)
        n += 1
        bad += int(not (abs(c - q["年化"].iloc[0]) < 1e-13 and abs(m - q["回落"].iloc[0]) < 1e-13 and lab == q["標籤"].iloc[0] and len(g) == 200))
    ok("③ 各版本×格 中位／標籤／200 顆", bad == 0, f"{n} 格，不符 {bad}")
    # ④
    mr = pd.read_csv(os.path.join(OUT, "body_meanret_main.csv.gz"), index_col=0, parse_dates=True, float_precision="round_trip")
    mon = mr.index.to_period("M"); ms = sorted(set(mon)); K = len(ms)
    g = np.random.default_rng(7)
    bad = 0; det = {}
    for cid in range(1, 27):
        col = f"c{cid}"
        if col not in mr:
            continue
        d = (mr[col] - mr["0050"]).groupby(mon)
        sums = d.sum().to_numpy(); cnts = d.count().to_numpy().astype(float)
        st = np.empty(20000)
        for i in range(20000):
            ix = g.integers(0, K, K)
            st[i] = sums[ix].sum() / cnts[ix].sum() * ANN
        lb = float(np.quantile(st, 0.05 / 26))
        q = C[(C["variant"] == "main") & (C["編號"] == cid)]["Bonferroni下界"].iloc[0]
        det[cid] = [round(lb, 4), round(float(q), 4)]
        bad += int(not (np.sign(lb) == np.sign(q) and abs(lb - q) < 0.015))
    ok("④ Bonferroni 下界（獨立 bootstrap，同號且差 < 1.5 點）", bad == 0, f"不符 {bad}；{det}")
    # ⑤
    m1 = SD[(SD["variant"] == "main") & (SD["cell"] == 1)].set_index("r").sort_index()
    for cid in (25, 26):
        gg = SD[(SD["variant"] == "main") & (SD["cell"] == cid)].set_index("r").sort_index()
        dc = gg["cagr"] - m1["cagr"]; dm = gg["mdd"] - m1["mdd"]
        pos, neg = int(((dc > 0) & (dm > 0)).sum()), int(((dc < 0) & (dm < 0)).sum())
        v2 = S["v2"][str(cid)]
        ok(f"⑤ #{cid} 對 #1 同種子 皆正／皆負", pos == v2["皆正"] and neg == v2["皆負"], f"{pos}／{neg}")
    g26 = SD[(SD["variant"] == "main") & (SD["cell"] == 26)]
    x = float(g26["cagr"].median()); dist = m1["cagr"].to_numpy()
    p = float(((dist < x).sum() + 0.5 * (dist == x).sum()) / len(dist) * 100)
    ok("⑤ #26 年化百分位", abs(p - S["v2"]["26"]["年化百分位"]) < 1e-9, f"{p:.3f}")
    # ⑥
    P = pd.read_csv(os.path.join(OUT, "body_placebo.csv"))
    bc, bm = S["0050"]["main"]["cagr"], S["0050"]["main"]["mdd"]
    bad = 0
    for _, r in P.iterrows():
        cid = int(r["編號"])
        if r["次數"] == 0:
            continue
        if cid in (1, 4, 7, 12, 15, 16, 17, 3, 6, 9, 11, 13, 14):
            gg = PL[(PL["kind"].isin(["P10", "P1"])) & (PL["cell"] == cid)]
            x = sum(label(c, m, bc, bm)[0] == "Q" for c, m in zip(gg["cagr"], gg["mdd"]))
        else:
            kind = {2: "P3shift", 10: "P3shift", 5: "W_shuf", 22: "P9", 23: "P9"}[cid]
            gg = PL[(PL["kind"] == kind) & (PL["cell"] == cid)].groupby("j")[["cagr", "mdd"]].median()
            x = sum(label(c, m, bc, bm)[0] == "Q" for c, m in zip(gg["cagr"], gg["mdd"]))
        bad += int(x != r["x_Q"])
    ok("⑥ 假訊號臂 x_Q 逐條重算", bad == 0, f"不符 {bad}")
    # ⑦
    daily = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "market"]) for f in glob.glob(os.path.join(RAW, "early", "daily", "*.csv"))])
    tw = set(daily.loc[daily["market"] == "twse", "stock_id"])
    today = set(pd.read_csv(os.path.join(RAW, "meta", "stocks.csv"), dtype=str)["stock_id"])
    r2 = sorted(s for s in tw - today if len(s) == 4 and s[0] in "123456789" and not s.startswith("91"))
    st = json.load(open(os.path.join(SNAP, "main", "STATUS.json"), encoding="utf-8"))
    ok("⑦ R2 收進來的代號數", len(r2) == st["roster"]["R2 收為 stock"], f"{len(r2)}")
    rd = pd.concat([pd.read_csv(f, dtype=str) for f in glob.glob(os.path.join(RAW, "early", "reduce", "*.csv")) if not os.path.basename(f).startswith("_")])
    ev = rd.drop_duplicates(["stock_id", "date"])
    ok("⑦ 官方減資（上市，去重後）", len(ev) == len(pd.read_csv(os.path.join(SNAP, "reduce_events.csv"))), f"原始 {len(rd)} 列 ⇒ {len(ev)} 事件")
    # ⑧
    SE = pd.read_csv(os.path.join(OUT, "body_sentences.csv"))
    need = ("早年只驗上市股", "樣本只有約 3 年", "本段樣本只夠分 Q／R／F，『可以說找到』依構造不可得")
    ok("⑧ 結果句必附三件", all(all(k in s for k in need) for s in SE["結果句"]), f"{len(SE)} 句")
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "body_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("== researchV_check：", "全部過" if RES["全部過"] else "⛔ 有不過", flush=True)


if __name__ == "__main__":
    main()

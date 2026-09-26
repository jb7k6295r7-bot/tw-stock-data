# -*- coding: utf-8 -*-
"""researchYfMix13 的獨立查核（⛔ 不 import backtest.researchYfMix13／researchYear1M）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfMix13_check

  Q1 閘：seeds_main.csv 逐種子對 regime_t1/seeds.csv（t1 #1）、rerun17_seeds.csv（main #13）；中位對 cells.csv／rerun17.csv；
     0050 從 eq_main.npz 自己算年化、回落對錨（逐位元）
  Q2 主窗混合：從 eq_main.npz 用本檔自己寫的再平衡（每年第一個交易日、換手＝Σ|目標−現值|÷2、×0.585%）重算每顆每組的年化、回落、期末
     ⇒ 對 mix_seeds.csv.gz；再重算中位、比值、標籤（自寫判準：年化 ＞ 錨、比值 ≥ 錨比值）⇒ 對 mix.csv
  Q3 逐年：mix.csv 各窗期末中位 ＝ mix_seeds 重算；純營飆／純 #13 的逐種子期末 ＝ resultsYear1M/seeds.csv.gz（格 1／13）；純 0050 ＝ bench_windows.csv
  Q4 持股重疊：從 positions.csv.gz 自己重建逐日持股（買進日 ≤ t ＜ 賣出日）⇒ 對 overlap_seeds.csv 與 overlap.csv
  Q5 相關：從 eq_main.npz 重算逐顆相關（全期、逐年）⇒ 對 corr_seeds.csv 與 corr.csv
  Q6 回落起訖：從 eq_main.npz 重算每顆高點日、谷底日 ⇒ 對 dd_seeds.csv 與 facts.json
輸出 resultsYfMix13/check.json
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYfMix13")
N17 = os.path.join(HERE, "resultsN17")
Y1 = os.path.join(HERE, "resultsYear1M")
RTP = dict(float_precision="round_trip")
ANC = (0.24020209886370614, -0.3395700527611012)
W = {"A": (1, 0, 0), "B": (0, 1, 0), "Z": (0, 0, 1), "AB75": (.75, .25, 0), "AB50": (.5, .5, 0), "AB25": (.25, .75, 0),
     "T33": (1 / 3, 1 / 3, 1 / 3), "T442": (.4, .4, .2), "T255": (.25, .25, .5)}


def close(a, b, tol=1e-9):
    a, b = float(a), float(b)
    if np.isnan(a) and np.isnan(b):
        return True
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def ann_mdd(v):
    v = np.asarray(v, float); n = len(v)
    c = (v[-1] / v[0]) ** (1 / (n / 245)) - 1
    pk = np.maximum.accumulate(v)
    return c, float(((v - pk) / pk).min())


def my_mix(legs, w, dates):
    """自寫：各腿各自複利；每年第一個交易日（第 0 天除外）先扣成本 ＝ Σ|w·V − 腿|÷2 × 0.585%，再按 w 重配。"""
    legs = [np.asarray(x, float) for x in legs]; w = np.asarray(w, float)
    hold = w.copy(); out = [1.0]
    yr = pd.DatetimeIndex(dates).year
    for t in range(1, len(legs[0])):
        hold = hold * np.array([x[t] / x[t - 1] for x in legs])
        tot = hold.sum()
        if yr[t] != yr[t - 1]:
            tot -= np.abs(w * tot - hold).sum() / 2 * 0.00585
            hold = w * tot
        out.append(tot)
    return np.array(out)


def main():
    res = {}
    Z = np.load(os.path.join(OUT, "eq_main.npz"))
    YF, B13, EZ = Z["yf"], Z["b13"], Z["z"]; dates = pd.to_datetime(Z["dates"])
    n = len(EZ)
    # Q1
    S = pd.read_csv(os.path.join(OUT, "seeds_main.csv"), dtype={"eq_sha": str}, **RTP)
    t1 = pd.read_csv(os.path.join(N17, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, **RTP)
    t1 = t1[(t1["stage"] == "t1") & (t1["cell"] == 1)].set_index("r").sort_index()
    m13 = pd.read_csv(os.path.join(N17, "rerun17_seeds.csv"), dtype={"eq_sha": str}, **RTP)
    m13 = m13[(m13["stage"] == "main") & (m13["cell"] == 13)].set_index("r").sort_index()
    q1 = {}
    for cid, ref in ((1, t1), (13, m13)):
        g = S[S["cell"] == cid].set_index("r").sort_index()
        q1[f"格{cid}_逐種子不同"] = int(sum(repr(float(a)) != repr(float(b)) for k in ("cagr", "mdd", "vol") for a, b in zip(g[k], ref[k]))
                                   + (g["eq_sha"] != ref["eq_sha"]).sum() + (g["trades"] != ref["trades"]).sum())
    cells = pd.read_csv(os.path.join(N17, "regime_t1", "cells.csv"), **RTP); r17 = pd.read_csv(os.path.join(N17, "rerun17.csv"), **RTP)
    q1["營飆中位逐位元"] = repr(float(S[S["cell"] == 1]["cagr"].median())) == repr(float(cells.loc[cells["編號"] == 1, "t1_年化"].iloc[0]))
    q1["#13中位逐位元"] = repr(float(S[S["cell"] == 13]["cagr"].median())) == repr(float(r17.loc[r17["編號"] == 13, "主窗_年化"].iloc[0]))
    cz, mz = ann_mdd(EZ)
    q1["0050錨逐位元"] = repr(float(cz)) == repr(ANC[0]) and repr(float(mz)) == repr(ANC[1])
    # 純營飆：從 npz 自算年化 ⇒ 對 seeds_main（逐位元）
    q1["npz營飆年化對seeds逐位元"] = all(repr(float(ann_mdd(YF[r])[0])) == repr(float(v)) for r, v in zip(range(200), S[S["cell"] == 1].sort_values("r")["cagr"]))
    q1["過"] = q1["格1_逐種子不同"] == 0 and q1["格13_逐種子不同"] == 0 and q1["營飆中位逐位元"] and q1["#13中位逐位元"] and q1["0050錨逐位元"] and q1["npz營飆年化對seeds逐位元"]
    res["Q1_閘"] = q1
    # Q2
    MS = pd.read_csv(os.path.join(OUT, "mix_seeds.csv.gz"), **RTP); MX = pd.read_csv(os.path.join(OUT, "mix.csv"), **RTP)
    mm = MS[MS["scope"] == "主窗"].set_index(["mix", "r"])
    maxd = 0.0; bad2 = []
    for k, w in W.items():
        for r in range(200):
            V = my_mix([YF[r], B13, EZ], w, dates)
            c, m = ann_mdd(V); ev = 1e6 * V[-1] / V[0]
            q = mm.loc[(k, r)]
            d = max(abs(c - q["cagr"]), abs(m - q["mdd"]), abs(ev / q["end_value"] - 1))
            maxd = max(maxd, d)
            if d > 1e-10:
                bad2.append((k, r, d))
    lab_bad = []
    for q in MX.itertuples():
        g = MS[(MS["scope"] == "主窗") & (MS["mix"] == q.鍵)]
        c, m = g["cagr"].quantile(.5), g["mdd"].quantile(.5)
        ratio = c / abs(m); lab = ("合格" if ratio >= ANC[0] / abs(ANC[1]) else "另列") if c > ANC[0] else "不合格"
        if not (close(c, q.主窗年化_中位) and close(m, q.主窗回落_中位) and close(ratio, q.比值) and lab == q.對0050標籤
                and close(g["end_value"].quantile(.5), q.主窗100萬期末_中位)):
            lab_bad.append(q.鍵)
    res["Q2_主窗混合"] = {"自算對逐種子最大差": maxd, "超過1e-10": bad2[:10], "中位標籤不符": lab_bad, "過": not bad2 and not lab_bad}
    # Q3
    scopes = [s for s in dict.fromkeys(MS["scope"]) if s != "主窗"]
    bad3 = []
    for q in MX.itertuples():
        for s in scopes:
            if not close(MS[(MS["scope"] == s) & (MS["mix"] == q.鍵)]["end_value"].quantile(.5), MX.loc[q.Index, f"{s}_期末中位"]):
                bad3.append((q.鍵, s))
    Y = pd.read_csv(os.path.join(Y1, "seeds.csv.gz"), **RTP); Y = Y[Y["kind"] == "fixed"]
    Bw = pd.read_csv(os.path.join(Y1, "bench_windows.csv"), **RTP).query("kind == 'fixed'").set_index("win")
    d3 = 0.0
    for s in scopes:
        win, var = (s.replace("_引擎原樣", ""), "eng") if s.endswith("_引擎原樣") else (s, "mtm")
        for k, cid in (("A", 1), ("B", 13)):
            a = MS[(MS["scope"] == s) & (MS["mix"] == k)].sort_values("r")["end_value"].to_numpy()
            b = Y[(Y["win"] == win) & (Y["cell"] == cid) & (Y["variant"] == var)].sort_values("r")["end_value"].to_numpy()
            d3 = max(d3, float(np.abs(a / b - 1).max()) if len(a) == len(b) == 200 else np.inf)
        z = MS[(MS["scope"] == s) & (MS["mix"] == "Z")]["end_value"].to_numpy()
        d3 = max(d3, float(np.abs(z / Bw.loc[win, "end_value"] - 1).max()))
    res["Q3_逐年"] = {"中位不符": bad3, "純臂對Year1M與0050最大相對差": d3, "過": not bad3 and d3 < 1e-12}
    # Q4
    P = pd.read_csv(os.path.join(OUT, "positions.csv.gz"), dtype={"sid": str}, **RTP)
    OV = pd.read_csv(os.path.join(OUT, "overlap_seeds.csv"), **RTP).set_index("r")
    w0 = int(Z["w0"]); w1 = int(Z["w1"])

    def held(df):
        H = [set() for _ in range(n)]
        for sid, tb, ts in zip(df["sid"], df["t_buy"], df["t_sell"]):
            ts = 10 ** 9 if ts < 0 else ts
            for t in range(max(tb, w0), min(ts, w1 + 1)):
                H[t - w0].add(sid)
        return H
    H13 = held(P[P["cell"] == 13])
    e13 = set(zip(P.loc[(P["cell"] == 13) & P["t_buy"].between(w0, w1), "sid"], P.loc[(P["cell"] == 13) & P["t_buy"].between(w0, w1), "week"]))
    bad4 = 0
    for r, g in P[P["cell"] == 1].groupby("r"):
        H = held(g)
        fr = [len(a & b) / len(a) for a, b in zip(H, H13) if a]
        g2 = g[g["t_buy"].between(w0, w1)]
        e1 = list(zip(g2["sid"], g2["week"]))
        mine = {"重疊÷營飆_逐日均值": np.mean(fr), "重疊÷營飆_逐日中位": np.median(fr),
                "營飆進場_同檔同週也在#13進場": np.mean([x in e13 for x in e1])}
        bad4 += int(not all(close(v, OV.loc[r, k]) for k, v in mine.items()))
    OS = pd.read_csv(os.path.join(OUT, "overlap.csv"), **RTP).set_index("量")
    bad4b = [c for c in OS.index if not (close(OV[c].quantile(.5), OS.loc[c, "中位"]) and close(OV[c].quantile(.1), OS.loc[c, "p10"])
                                         and close(OV[c].quantile(.9), OS.loc[c, "p90"]))]
    res["Q4_重疊"] = {"逐種子不符": bad4, "彙總不符": bad4b, "過": bad4 == 0 and not bad4b}
    # Q5
    CR = pd.read_csv(os.path.join(OUT, "corr_seeds.csv"), **RTP).set_index("r")
    rb = B13[1:] / B13[:-1] - 1; yrs = dates[1:].year
    bad5 = 0
    for r in range(200):
        ra = YF[r][1:] / YF[r][:-1] - 1
        mine = {"全期_營飆×#13": pd.Series(ra).corr(pd.Series(rb))}
        for y in sorted(set(yrs)):
            m_ = np.asarray(yrs == y)
            mine[f"{y}_營飆×#13"] = pd.Series(ra[m_]).corr(pd.Series(rb[m_]))
        bad5 += int(not all(close(v, CR.loc[r, k], 1e-9) for k, v in mine.items()))
    CS = pd.read_csv(os.path.join(OUT, "corr.csv"), **RTP).set_index("量")
    bad5b = [c for c in CS.index if not close(CR[c].quantile(.5), CS.loc[c, "中位"])]
    res["Q5_相關"] = {"逐種子不符": bad5, "彙總不符": bad5b, "過": bad5 == 0 and not bad5b}
    # Q6
    DD = pd.read_csv(os.path.join(OUT, "dd_seeds.csv"), **RTP).set_index("r")
    F = json.load(open(os.path.join(OUT, "facts.json"), encoding="utf-8"))["回落起訖"]

    def pt(v):
        dd = v / np.maximum.accumulate(v) - 1; t = int(np.argmin(dd)); return int(np.argmax(v[:t + 1])), t
    bad6 = 0
    for r in range(200):
        p, t = pt(YF[r])
        bad6 += int(str(dates[p].date()) != DD.loc[r, "高點"] or str(dates[t].date()) != DD.loc[r, "谷底"])
    p, t = pt(B13); ok13 = (str(dates[p].date()), str(dates[t].date())) == (F["#13"]["高點"], F["#13"]["谷底"])
    p, t = pt(EZ); okz = (str(dates[p].date()), str(dates[t].date())) == (F["0050"]["高點"], F["0050"]["谷底"])
    res["Q6_回落起訖"] = {"營飆逐種子不符": bad6, "#13": ok13, "0050": okz, "過": bad6 == 0 and ok13 and okz}
    res["全部過"] = all(v["過"] for v in res.values() if isinstance(v, dict))
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREGU 查核：從逐筆檔（resultsU/events_body_*.csv、fake_arm_*.csv）用【另一套寫法】重算，與 summary.json 比。
⛔ 不 import researchU／researchU_core／research11（不共用主程式的 dstat／cl_stats）。
   D 與其分群 SE：逐筆影響函數 ψ_i ＝ w_x (y_i − b_x)／n_x，SE ＝ √Σ_g(Σ_{i∈g} ψ_i)²（CR0；與主程式的矩陣三明治在代數上相等、寫法不同）
   平均與月分群 CI：SE ＝ √Σ_g(Σ_{i∈g}(x_i − x̄))²／n
"""
import os, json
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest/resultsU"))
S = json.load(open("summary.json", encoding="utf-8"))
WD = {"38.2": 0.5, "61.8": 0.5, "30": -0.25, "45": -0.25, "55": -0.25, "70": -0.25}
W50 = {"50": 1.0, "45": -0.5, "55": -0.5}; W38 = {"38.2": 1.0, "30": -0.5, "45": -0.5}; W62 = {"61.8": 1.0, "55": -0.5, "70": -0.5}
cal = pd.read_csv(os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data/meta/calendar_twse.csv"))["date"].tolist()
w0 = cal.index("2017-03-02")
worst = {}


def lin(E, col, wts, cl, filt=True):
    d = E[E["pos"].isin(list(wts))]
    if filt:
        d = d[d[col] >= 0]
    b = d.groupby("pos")[col].mean(); n = d.groupby("pos")[col].size()
    psi = d.apply(lambda r: wts[r["pos"]] * (r[col] - b[r["pos"]]) / n[r["pos"]], axis=1)
    se = float(np.sqrt((psi.groupby(d[cl]).sum() ** 2).sum()))
    D = float(sum(w * b[p] for p, w in wts.items()))
    return D, D - 1.96 * se, D + 1.96 * se, b


def mci(x, g):
    x = np.asarray(x, float); ok = np.isfinite(x); x = x[ok]; g = np.asarray(g)[ok]
    m = x.mean(); se = np.sqrt((pd.Series(x - m).groupby(g).sum() ** 2).sum()) / len(x)
    return m, m - 1.96 * se, m + 1.96 * se


def cmp(name, mine, ref):
    d = max(abs(a - b) for a, b in zip(mine, ref))
    worst[name] = d
    print("{:<34} 重算 {}  主程式 {}  最大差 {:.1e}".format(name, " ".join("{:+.6f}".format(v) for v in mine), " ".join("{:+.6f}".format(v) for v in ref), d))


E = pd.read_csv("events_body_k5_H20.csv", dtype={"sid": str, "pos": str, "market": str})
J = S["判定格"]
D, lo, hi, b = lin(E, "y", WD, "mon"); cmp("判定格 D（月）", (D, lo, hi), (J["D"], J["lo_月"], J["hi_月"]))
D, lo, hi, _ = lin(E, "y", WD, "wave_id"); cmp("判定格 D（波段）", (D, lo, hi), (J["D"], J["lo_波段"], J["hi_波段"]))
cmp("七位置 b(x)", [E[(E.pos == p) & (E.y >= 0)]["y"].mean() for p in ["30", "38.2", "45", "50", "55", "61.8", "70"]],
    [J["各位置"][p]["b"] for p in ["30", "38.2", "45", "50", "55", "61.8", "70"]])
# n_eff
ne = min(min(int(((E.pos == p) & (E.y >= 0)).sum()), int(np.minimum((E[(E.pos == p) & (E.y >= 0)]["T"] - w0) // 20, 114).nunique())) for p in WD)
print("n_eff 重算 {}／主程式 {}".format(ne, J["n_eff"])); worst["n_eff"] = abs(ne - J["n_eff"])
F = S["§五必報"]
for nm, W_, key in (("38.2 − 鄰位", W38, "38.2"), ("61.8 − 鄰位", W62, "61.8")):
    D, lo, hi, _ = lin(E, "y", W_, "mon"); r = F["費氏位各自_b(F)−鄰位平均（只報）"][key]; cmp(nm, (D, lo, hi), (r["D"], r["lo"], r["hi"]))
D, lo, hi, _ = lin(E, "y", W50, "mon"); r = S["§六描述臂"]["a_50%"]; cmp("描述臂 a 50%", (D, lo, hi), (r["D50"], r["lo"], r["hi"]))
for p in ["30", "38.2", "45", "50", "55", "61.8", "70"]:
    e = E[E.pos == p]; r = F["七位置"][p]["X20對EWc"]; cmp("§五 X20 平均 " + p, mci(e["X"], e["mon"]), (r["平均"], r["lo"], r["hi"]))
for col, nm in (("y_b3", "±3%帶"), ("y_b8", "±8%帶")):
    D, lo, hi, _ = lin(E.assign(y=E[col]), "y", WD, "mon"); r = S["§六描述臂"]["b_判定帶與窗"][nm]; cmp("描述臂 b " + nm, (D, lo, hi), (r["D"], r["lo"], r["hi"]))
for cfg, nm, grp in (("k5_H10", "10日窗", "b_判定帶與窗"), ("k5_H40", "40日窗", "b_判定帶與窗"), ("k3_H20", "k3", "c_k"), ("k10_H20", "k10", "c_k")):
    e = pd.read_csv("events_body_{}.csv".format(cfg), dtype={"sid": str, "pos": str})
    D, lo, hi, _ = lin(e, "y", WD, "mon"); r = S["§六描述臂"][grp][nm]; cmp("描述臂 " + nm, (D, lo, hi), (r["D"], r["lo"], r["hi"]))
dd = E[E["d_ok"]]
D, lo, hi, _ = lin(dd, "Xd", WD, "mon", filt=False); r = S["§六描述臂"]["d_交易版"]["D_d（X_d 的同形線性組合）"]; cmp("描述臂 d D_d", (D, lo, hi), (r["D"], r["lo"], r["hi"]))
for mk, nm in (("twse", "上市"), ("tpex", "上櫃")):
    D, lo, hi, _ = lin(E[E.market == mk], "y", WD, "mon"); r = F["上市上櫃"][nm]; cmp("§五 " + nm + " D", (D, lo, hi), (r["D"], r["lo"], r["hi"]))
FK = pd.read_csv("fake_arm_registered.csv")
fD = FK["D"].to_numpy(); q = J["假訊號臂_登錄"]
cmp("假訊號臂 百分位／x／p95", ((fD < J["D"]).mean() * 100, (fD >= J["D"]).sum(), np.percentile(fD, 95)), (q["真D百分位"], q["D_fake≥真D的次數x"], q["D_fake的95百分位"]))
print("最大差（全部）{:.1e} ⇒ {}".format(max(worst.values()), "✅ 相符" if max(worst.values()) < 1e-10 else "⛔ 不符"))
json.dump({k: float(v) for k, v in worst.items()}, open("verify.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# -*- coding: utf-8 -*-
"""F9 對帳檢查（researchMktDrop_f9 的獨立重算；只讀檔、不改任何結果）

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_f9_check

 C1 F9 挑檔獨立重算：只讀 quality/features.csv（F6、F7、Q、淨報酬、買得到），純 Python 排序（F9 降冪 ⇒ F7 降冪 ⇒ 代號），18 事件 × N=1/2/3 對 f9/event_picks.csv
 C2 單一事件明細：2025-03-31（F9 N=1 最大貢獻事件）N=3 逐檔名次與報酬
 C3 f9/summary.csv 的對照列（0050、正2、C+全買、隨機、F6、F7、F8、Q）逐格對 quality/summary.csv；F8 兩段對 f8/summary.csv；F6／F7 兩段對 fund/summary.csv
 C4 f9 借用的 quality.quintiles 路徑：用原 Q 重跑必須重現 quality/quintile.csv、quintile_mono.csv
 C5 F9 N=3（18 事件）隨機百分位獨立重算（同種子）
 C6 10/15 F9 前 3 由三個來源檔獨立重算
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from backtest import researchMktDrop_fund as FU
from backtest import researchMktDrop_quality as QL

REPO = os.path.expanduser("~/tw-p17")
R = os.path.join(REPO, "backtest/resultsMktDrop")
OK = []


def chk(name, cond, info=""):
    OK.append(bool(cond)); print(f"[{'通過' if cond else '❌失敗'}] {name} {info}", flush=True)


def pct_rank(v):
    return pd.Series(v).rank(pct=True, method="average").to_numpy() * 100


def main():
    QF = pd.read_csv(os.path.join(R, "quality/features.csv"), dtype={"sid": str})
    QF["買得到"] = QF["買得到"].astype(str).str.lower().eq("true")
    EP = pd.read_csv(os.path.join(R, "f9/event_picks.csv"), dtype={"選中": str})
    E9 = EP[EP["分數"] == "F9"].set_index(["事件日", "N"])
    # C1
    bad = 0; mx = 0.0; detail = None
    for ev, g in QF.groupby("事件日"):
        g = g.reset_index(drop=True)
        f9 = np.round(pct_rank(g["F6"]) + pct_rank(g["F7"]) + pct_rank(g["Q"]), 6)
        idx = sorted(range(len(g)), key=lambda i: (-f9[i], -g["F7"][i], g["sid"][i]))
        for N in (1, 2, 3):
            sel = idx[:N]; ids = [g["sid"][i] for i in sel]
            b = [g["淨報酬"][i] for i in sel if g["買得到"][i]]
            ret = float(np.mean(b)) if b else 0.0
            e = E9.loc[(ev, N)]
            bad += int(str(e["選中"]).split() != ids); mx = max(mx, abs(ret - float(e["報酬"])))
            if ev == "2025-03-31" and N == 3:
                detail = [(g["sid"][i], round(f9[i], 2), round(pct_rank(g["F6"])[i], 1), round(pct_rank(g["F7"])[i], 1), round(pct_rank(g["Q"])[i], 1),
                           g["淨報酬"][i] if g["買得到"][i] else "買不到") for i in sel] + [("等權", round(ret, 6))]
    chk("C1 F9 挑檔獨立重算 vs f9/event_picks（54 格）", bad == 0 and mx < 1e-5, f"選中不同 {bad}、報酬最大差 {mx:.1e}")
    # C2
    print(f"[C2] 2025-03-31 F9 N=3（代號, F9, F6名次, F7名次, Q名次, 淨報酬）: {detail}")
    chk("C2 2025-03-31 N=3 與 event_picks 一致", abs(detail[-1][1] - float(E9.loc[("2025-03-31", 3)]["報酬"])) < 1e-5)
    # C3
    S9 = pd.read_csv(os.path.join(R, "f9/summary.csv")); QS = pd.read_csv(os.path.join(R, "quality/summary.csv"))
    for X in (S9, QS):
        X["N_"] = pd.to_numeric(X["N"], errors="coerce").fillna(0).astype(int)
    num = ["事件數", "平均", "中位", "勝率", "最差", "最好", "虧＞10%次數", "隨機段平均P10", "隨機段平均P50", "隨機段平均P90", "空手事件數",
           "隨機中位置（百分位）", "勝過C+全買事件數", "勝過A事件數"]
    a = S9[S9["方法"] != "F9"].merge(QS, on=["段", "方法", "N_"], suffixes=("", "_q"))
    n_exp = int((S9["方法"] != "F9").sum())
    d = max(float(np.nanmax(np.abs(a[c].astype(float) - a[c + "_q"].astype(float)) / np.maximum(1, np.abs(a[c + "_q"].astype(float))))) for c in num)
    chk("C3a 對照列 vs quality/summary.csv", len(a) == n_exp == 54, f"列 {len(a)}/{n_exp}、最大相對差 {d:.1e}")
    chk("C3a' 差 ＜ 1e-5", d < 1e-5)
    F8S = pd.read_csv(os.path.join(R, "f8/summary.csv")); FS = pd.read_csv(os.path.join(R, "fund/summary.csv"))
    m = 0.0
    for _, r in S9[S9["方法"].isin(["F6", "F7", "F8"]) & S9["段"].isin(["2015～2021", "2022～"])].iterrows():
        src = F8S if r["方法"] == "F8" else FS
        f = src[(src["段"] == r["段"]) & (src["方法"] == r["方法"]) & (pd.to_numeric(src["N"], errors="coerce") == r["N_"])].iloc[0]
        for c in ("平均", "中位", "勝率", "最差", "隨機中位置（百分位）"):
            m = max(m, abs(float(f[c]) - float(r[c])))
    chk("C3b F8 vs f8/summary、F6／F7 vs fund/summary（兩段 × 3N）", m < 1e-5, f"最大差 {m:.1e}")
    # C4
    segev = {"2015～2021": sorted(QF[QF["段"] == "2015～2021"]["事件日"].unique()), "2022～": sorted(QF[QF["段"] == "2022～"]["事件日"].unique())}
    segev["2015～（18事件）"] = segev["2015～2021"] + segev["2022～"]
    QT, QX = QL.quintiles(QF.copy(), segev)
    oT = pd.read_csv(os.path.join(R, "quality/quintile.csv")); oX = pd.read_csv(os.path.join(R, "quality/quintile_mono.csv"))
    dT = float(np.nanmax(np.abs(QT.select_dtypes("number").to_numpy(float) - oT.select_dtypes("number").to_numpy(float))))
    cx = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q5−Q1", "Q5−Q1 CI95低", "Q5−Q1 CI95高", "Q5＞Q1 事件比例"]
    dX = float(np.nanmax(np.abs(QX[cx].to_numpy(float) - oX[cx].to_numpy(float))))
    dS = float(np.nanmax(np.abs(QX["Spearman 事件平均"].to_numpy(float) - oX["Spearman 事件平均"].to_numpy(float))))
    chk("C4 quality.quintiles 用原 Q 重現 quality 五分位（組平均、CI、Q5−Q1）", dT < 1e-5 and dX < 1e-5, f"quintile 最大差 {dT:.1e}、mono {dX:.1e}")
    chk("C4' Spearman 事件平均（features 存 ％.6g，原程式浮點雜訊打破的同分在存檔後恢復同分 ⇒ 容差 1e-4）", dS < 1e-4, f"最大差 {dS:.1e}")
    # C4b F9 五分位單一事件獨立重算（Q5 組）
    F9F = pd.read_csv(os.path.join(R, "f9/features.csv"), dtype={"sid": str}); F9F["買得到"] = F9F["買得到"].astype(str).str.lower().eq("true")
    q5 = []
    for ev, g in F9F.groupby("事件日"):
        g = g.sort_values("sid", kind="mergesort").sort_values(["F9", "F7"], ascending=[False, False], kind="mergesort").reset_index(drop=True)
        n = len(g); grp = 5 - (np.arange(n) * 5 // n); b = g[(grp == 5) & g["買得到"].to_numpy()]
        q5.append(b["淨報酬"].mean())
    oq = pd.read_csv(os.path.join(R, "f9/quintile_mono.csv")).set_index("段")
    chk("C4b F9 Q5（18 事件等權）獨立重算", abs(np.nanmean(q5) - oq.loc["2015～（18事件）", "Q5"]) < 1e-5, f"{np.nanmean(q5):.6f} vs {oq.loc['2015～（18事件）', 'Q5']:.6f}")
    # C5
    ALL = pd.read_csv(os.path.join(R, "fund/features.csv"), dtype={"sid": str}); ALL["買得到"] = ALL["買得到"].astype(str).str.lower().eq("true")
    evs_all = sorted(ALL["事件日"].unique()); evs = segev["2015～（18事件）"]
    rs = []
    for i, ev in enumerate(evs_all):
        if ev not in evs:
            continue
        dd = ALL[ALL["事件日"] == ev]; net = np.where(dd["買得到"].to_numpy(), dd["淨報酬"].to_numpy(float), np.nan)
        rng = np.random.default_rng([FU.SEED, i, 3]); ix = np.argsort(rng.random((FU.NR, len(net))), axis=1)[:, :3]
        v = net[ix]; fin = np.isfinite(v); c = fin.sum(axis=1)
        rs.append(np.where(c > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(c, 1), 0.0))
    sa = np.stack(rs).mean(axis=0)
    f9m = float(E9.reset_index().query("N == 3")["報酬"].mean())
    row = S9[(S9["段"] == "2015～（18事件）") & (S9["方法"] == "F9") & (S9["N_"] == 3)].iloc[0]
    chk("C5 F9 N=3 18 事件平均與隨機百分位重算", abs(f9m - row["平均"]) < 1e-5 and abs((sa < f9m).mean() - row["隨機中位置（百分位）"]) < 1e-9,
        f"平均 {f9m:.6f}、百分位 {(sa < f9m).mean():.4f}")
    # C6
    W = pd.read_csv(os.path.join(R, "fund/forward_20261015_features.csv"), dtype={"sid": str})
    QW = pd.read_csv(os.path.join(R, "quality/forward_20261015.csv"), dtype={"代號": str}).set_index("代號")
    W["Q"] = [QW.loc[s, "Q"] for s in W["sid"]]
    W["F9"] = pct_rank(W["F6"]) + pct_rank(W["F7"]) + pct_rank(W["Q"])
    top = W.sort_values("sid").sort_values(["F9", "F7"], ascending=[False, False], kind="mergesort")["sid"].head(3).tolist()
    FW = pd.read_csv(os.path.join(R, "f9/forward_20261015.csv"), dtype={"代號": str})
    chk("C6 10/15 F9 前 3 獨立重算", top == FW["代號"].head(3).tolist(), f"{top}")
    print(f"\n共 {len(OK)} 項，通過 {sum(OK)}、失敗 {len(OK) - sum(OK)}")
    assert all(OK)


if __name__ == "__main__":
    main()

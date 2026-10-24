# -*- coding: utf-8 -*-
"""researchTurnover 獨立查核——回測線計算子代理，2026-10-24。⛔ 不 import researchTurnover；盡量讀【另一份】逐筆檔重算。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurnover_check

 C1 營量 規則版 ＝ resultsYLallin/trades.csv.gz、daily.csv.gz 帳 YL（YLallin 自己重跑的那一份，主表讀 resultsYFallin）
 C2 營飆 全買版 ＝ resultsYLallin 帳 YFW1（YLallin 重算的營飆 W1，主表讀 resultsYFallin W1）
 C3 營量 全買版 ＝ resultsYLallin 帳 V1（同檔；持有改用 FIFO 逐代號配對、窗用日期字串比較，與主表 searchsorted／位置窗不同路）
 C4 高10 規則版 ＝ resultsPTHn/trades_<世界>_N10.csv.gz ＋ eq_<世界>.npz N10_eq（主表讀 resultsPTH10tie 原）；成本另用 N10_pend 驗 0050 買回腿
 C5 大跌 4 檔 ＝ event_rows 逐事件手數（事件日字串在窗內）
 比：每年買進筆、每年賣出筆、持有天數平均／中位、年換手率、每年成本（0.585 版）＝ table.csv（相對差 < 1e−9；筆數完全相同）
"""
from __future__ import annotations

import json
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17"))
B = "backtest"
OUT = f"{B}/resultsTurnover"
WIN = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "早年": ("2005-02-01", "2014-12-31")}
TAB = pd.read_csv(f"{OUT}/table.csv")
RES = {}


def trow(name, seg):
    q = TAB[(TAB["策略"] == name) & (TAB["段"] == seg)]
    assert len(q) == 1, (name, seg)
    return q.iloc[0]


def cmp(tag, mine, ref, exact=False):
    d = abs(mine - ref) / max(abs(ref), 1e-300)
    ok = (mine == ref) if exact else d < 1e-9
    RES[tag] = {"重算": mine, "表": float(ref), "相對差": d, "過": bool(ok)}


def yl_check(name, acct, segs=("探索", "確認", "早年")):
    T = pd.read_csv(f"{B}/resultsYLallin/trades.csv.gz"); Dd = pd.read_csv(f"{B}/resultsYLallin/daily.csv.gz")
    for sg in segs:
        wn = "早年" if sg == "早年" else "主"
        a, b = WIN[sg]
        D = Dd[(Dd["世界"] == wn) & (Dd["帳"] == acct)]
        dmap = dict(zip(D["t"], D["日期"].fillna("").astype(str)))
        inw = D[(D["日期"].fillna("") >= a) & (D["日期"].fillna("") <= b)]
        yrs = len(inw) / 245.0
        X = T[(T["世界"] == wn) & (T["帳"] == acct)].copy()
        X["d"] = X["t"].map(dmap).fillna("")
        X = X.sort_values(["t", "side"], kind="stable")
        bw = X[(X["side"] == "buy") & (X["d"] >= a) & (X["d"] <= b)]
        sw = X[(X["side"] == "sell") & (X["d"] >= a) & (X["d"] <= b)]
        # FIFO 逐代號配對
        q = defaultdict(deque); hold = {}
        for i, r in X.iterrows():
            if r["side"] == "buy":
                q[r["sid"]].append(i)
            else:
                j = q[r["sid"]].popleft(); hold[j] = int(r["t"]) - int(X.loc[j, "t"])
        hd = np.array([hold[i] for i in bw.index if i in hold], float)
        r = trow(name, sg)
        cmp(f"{name}|{sg}|買進筆每年", len(bw) / yrs, r["買進筆每年"])
        cmp(f"{name}|{sg}|賣出筆每年", len(sw) / yrs, r["賣出筆每年"])
        cmp(f"{name}|{sg}|持有天數平均", hd.mean(), r["持有天數平均"])
        cmp(f"{name}|{sg}|持有天數中位", float(np.median(hd)), r["持有天數中位"])
        cmp(f"{name}|{sg}|年換手率", sw["amt_out"].sum() / inw["持股市值"].mean() / yrs, r["年換手率"])
        if acct != "YFW1" or True:
            cmp(f"{name}|{sg}|成本每年0585", (sw["amt"] * 0.00585).sum() / inw["權益"].mean() / yrs, r["成本每年_0585"])


def p10_check(name="高10 規則版（抽籤）"):
    for sg, wn, (a, b) in (("探索", "主", WIN["探索"]), ("確認", "主", WIN["確認"]), ("早年", "早年", ("2005-01-03", "2014-12-31"))):
        dates = np.load(f"{B}/resultsPTH10tie/main/raw_{wn}.npz")["dates"].astype(str)      # 只取日曆
        Z = np.load(f"{B}/resultsPTHn/eq_{wn}.npz"); eq = Z["N10_eq"]; pend = Z["N10_pend"]
        T = pd.read_csv(f"{B}/resultsPTHn/trades_{wn}_N10.csv.gz", dtype={"sid": str})
        m = (dates >= a) & (dates <= b); yrs = m.sum() / 245.0; meq = eq[m].mean()
        idx = pd.Series(np.arange(len(dates)), index=dates)
        bw = T[(T["買進日"] >= a) & (T["買進日"] <= b)]
        sw = T[T["賣出日"].notna() & (T["賣出日"] >= a) & (T["賣出日"] <= b)]
        hd = (idx[bw.loc[bw["賣出日"].notna(), "賣出日"]].to_numpy() - idx[bw.loc[bw["賣出日"].notna(), "買進日"]].to_numpy()).astype(float)
        # 0050 買回腿：引擎 pend（賣出當天入帳、隔天買回）⇒ 用 pend 序列（另一路）算買回金額
        nxt = np.r_[0.0, pend[:-1]]                                     # 第 t 天開盤買回 ＝ 前一天收盤 pend
        etf_buy = (nxt[m] * 0.001425).sum()
        etf_sell = (bw["金額"] / (1 - 0.002425) * 0.002425).sum()
        stk = (sw["金額"] * 0.00585).sum()
        r = trow(name, sg)
        cmp(f"{name}|{sg}|買進筆每年", len(bw) / yrs, r["買進筆每年"])
        cmp(f"{name}|{sg}|賣出筆每年", len(sw) / yrs, r["賣出筆每年"])
        cmp(f"{name}|{sg}|持有天數平均", hd.mean(), r["持有天數平均"])
        cmp(f"{name}|{sg}|持有天數中位", float(np.median(hd)), r["持有天數中位"])
        cmp(f"{name}|{sg}|年換手率", (sw["入帳"] + sw["金額"] * 0.00585).sum() / meq / yrs, r["年換手率"])
        cmp(f"{name}|{sg}|成本每年0585（個股＋0050 由 pend 序列）", (stk + etf_sell + etf_buy) / meq / yrs, r["成本每年_0585"])


def md_check():
    d = pd.read_csv(f"{B}/resultsMktDrop/addon2/event_rows.csv")
    f = d[(d["世界"] == "主") & (d["候選"] == "F9") & (d["觸發"] == "T2") & (d["方式"] == "乙") & (d["出場"] == "主")]
    cal = np.load(f"{B}/resultsBenchRejudge/mktdrop_curves.npz")["dates"].astype(str)
    for sg in ("探索", "確認"):
        a, b = WIN[sg]; yrs = ((cal >= a) & (cal <= b)).sum() / 245.0
        e = f[(f["事件日"] >= a) & (f["事件日"] < b)]
        ad = e[e["有觸發"] & e["加碼進場"]]
        for name, extra in (("大跌 4 檔（甲：撥 20%、不加碼）", 0), ("大跌 4 檔（甲：撥 20%、−5% 加碼同一批）", 1)):
            n = e["首次檔數"].sum() + (ad["加碼檔數"].sum() if extra else 0)
            sl = len(e) + (len(ad) if extra else 0)
            hd = list(e["不加碼_持有天數"]) + (list(ad["加碼份_持有天數"]) if extra else [])
            r = trow(name, sg)
            cmp(f"{name}|{sg}|買進筆每年", n / yrs, r["買進筆每年"])
            cmp(f"{name}|{sg}|持有天數中位", float(np.median(hd)), r["持有天數中位"])
            cmp(f"{name}|{sg}|成本每年0585", sl * 0.2 * (1 - (1 - 0.00585) * (1 - 0.00385)) / yrs, r["成本每年_0585"])


def main():
    yl_check("營量 規則版（v1 relvol）", "YL")
    yl_check("營飆 全買版（W1）", "YFW1")
    yl_check("營量 全買版（V1）", "V1")
    p10_check()
    md_check()
    bad = [k for k, v in RES.items() if not v["過"]]
    json.dump({"項數": len(RES), "不過": bad, "明細": RES}, open(f"{OUT}/check.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    for k, v in RES.items():
        print(("✓ " if v["過"] else "✗ ") + f"{k}：重算 {v['重算']:.10g}｜表 {v['表']:.10g}")
    print(f"查核 {len(RES)} 項｜不過 {len(bad)}")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

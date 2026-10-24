# -*- coding: utf-8 -*-
"""各策略實際換手與摩擦成本描述表（裁定 seq459 §九.1；使用者問「持股 40 檔摩擦成本重不重」）——回測線計算子代理，2026-10-24。
⭐ 描述、⛔ 不計 N、⛔ 不判定、⛔ 不調任何策略參數；⛔ 不改既有檔（策略鎖 25 支、各結果夾只讀），⛔ 不重跑任何回測：全部讀既有逐筆／逐日輸出。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurnover
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurnover_check

═══ 出處（每個策略的正式回測輸出；數字只放一處，本表只引用並註出處）═══
 營飆 規則版（v1，抽籤 200 顆）  backtest/resultsYFallin/trades_W.csv.gz、daily_W.csv.gz 帳 v1（＝ r0 那一顆；E1 閘 eq_sha ＝ resultsYF_N）
                                  ＋ seeds.csv.gz（200 顆逐顆 換手每年／成本每年）；年化 ＝ cells.csv「營飆 v1（抽籤）」200 顆中位（＝ resultsBenchRejudge/rank.csv）
 營飆 全買版（W1）               同上 帳 W1；年化 ＝ resultsYFallin/cells.csv W1（＝ rank.csv「營飆（使用者全買版）」）
 營量 規則版（v1，relvol）        同上 帳 YL；年化 ＝ resultsYFallin/cells.csv「營量 v1」（＝ rank.csv）
 營量 全買版（V1）               backtest/resultsYLallin/trades.csv.gz、daily.csv.gz 帳 V1；年化 ＝ resultsYLallin/cells.csv V1
 高10 規則版（抽籤）             backtest/resultsPTH10tie/main/trades_<世界>_原.csv.gz（原種子；＝ resultsPTHn trades_<世界>_N10 逐字）＋ raw_<世界>.npz 原_eq
                                  年化 ＝ 200 組中位（rank.csv；早年 resultsPTH10seed/summary.csv）並列原種子（resultsPTH10tie/main/table.csv 原）
 高10 F9 版                      同上 trades_<世界>_T1.csv.gz ＋ raw T1_eq；年化 ＝ table.csv T1
 大跌 4 檔（甲：撥 20%）          backtest/resultsMktDrop/addon2/event_rows.csv（F9、主世界）；不加碼 ＝ 各事件首次部位；−5% 加碼 ＝ 觸發 T2·方式乙·主出場那幾列
                                  日曆 ＝ resultsBenchRejudge/mktdrop_curves.npz dates；年化 ＝ rank.csv
 六四 v1（0050 60%＋00685L 40%）  backtest/results64retest/summary.json「每年動手」「成本／年（占市值）」（researchMix70.sim 的 acts、crel）；年化 ＝ 同檔窗 A、rank.csv 確認

═══ 讀法（寫死於算任何本件數字之前，2026-10-24 台北）═══
 T1 窗：營量／營飆、高10、大跌 ＝ 原報告段 探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（＝ 2022 起主排名窗）；
    早年（參考）營量／營飆 2005-02-01～2014-12-31、高10 2005-01-03～2014-12-31（各原件窗）；六四 ＝ 窗 A 2018-01-15～2026-08-24、確認 2022-01-03～2026-08-24。
    窗位置 x ＝ 第一個 日期 ≥ 窗首、y ＝ 最後一個 日期 ≤ 窗尾（各件自己的世界日曆）；年數 ＝ (y − x ＋ 1) ÷ 245（repo 慣例）。
 T2 筆數：買進筆 ＝ 買進日在窗內的筆數 ÷ 年數；賣出筆 ＝ 賣出日在窗內 ÷ 年數（個股；ETF 腿另列）。
 T3 持有天數（交易日）＝ 賣出日位置 − 買進日位置（世界日曆）；取買進日在窗內且已賣出的筆；平均、中位。
    大跌 ＝ 事件層「首次買進到最後一份賣完」（event_rows 不加碼_持有天數；加碼份 ＝ 加碼份_持有天數）；六四 ＝ 不適用（一直持有、每年 1 月調回）。
 T4 年換手率 ＝ 窗內賣出金額（毛，＝ 買進金額 ×（1＋毛報酬））÷ 窗內平均持倉市值 ÷ 年數。
    營量／營飆 持倉市值 ＝ daily「持股市值」；高10 ＝ 權益（0050 補位算持倉、待買回現金近 0）；
    大跌 ＝ 買進側 Σ撥出比例 ÷ 年數（event_rows 無賣出金額，以事件當時淨值為分母）；六四 ＝ 成本／年 ÷ 0.385%（＝ Σ單邊成交額 ÷ 當時市值 ÷ 年數）。
 T5 成本（每年，占資金）：
    個股 ＝ 每筆 買進金額 × 來回費率，記在賣出日（＝ 回測內扣法 research11.COST；researchYFallin.seg_metrics／researchPTHpf.pf_stats 同式），
           ÷ 窗內平均權益 ÷ 年數。來回費率 0.585%（買 0.1425%＋賣 0.1425%＋稅 0.3%）；3 折版 0.3855%（0.1425%×0.3×2＋0.3%）。
    ETF 腿（稅 0.1%）：高10 每筆個股買進同日賣 0050（金額 ÷ (1−0.2425%)，扣 0.2425%）、每筆個股賣出隔一交易日買回 0050（入帳金額，扣 0.1425%）
           ＝ researchTurtleS2PF.simulate main 模式逐行；3 折 ⇒ 賣 0.04275%＋0.1%、買 0.04275%。
    大跌 ＝ 每事件 撥出比例 w × [1 −（1−個股來回）（1−ETF 來回）]（＝ researchMktDrop_v1.curve2 扣法；ETF 來回 0.385%，3 折 0.1855%），Σ ÷ 年數（以事件當時淨值為分母）。
    六四 ＝ 年調回 成本／年（檔值，ETF 0.385%）＋ 窗首建倉一次 0.385% ÷ 年數（researchMix70.sim 建倉 tr＝1、照扣）；3 折 ＝ 同成交額 × 0.1855%。
    營飆 規則版 0.585 版 ＝ 200 顆「成本每年」中位（seeds.csv.gz）；成本 ＝ 金額 × 費率 ⇒ 3 折版 ＝ × 0.3855 ÷ 0.585（逐位元成比例）。筆數、持有、換手率 ＝ r0。
 T6 年化 ＝ 照原回測口徑（已扣 0.585%／ETF 0.385%）引用出處檔；成本占報酬 ＝ 每年成本 ÷ 年化（年化 ≤ 0 寫「—」）。
 T7 錨點（不過即停）：本檔由逐筆重算的「換手每年（買進金額 ÷ 平均權益）」「成本每年」「買進筆每年」＝ 原件 cells.csv／seeds.csv.gz／table.csv 檔值（相對差 < 1e−9）；
    高10 個股＋ETF 成本合計 ＝ table.csv「成本合計每年(實付)」、平均持有天數、買進筆 ＝ table.csv；大跌 事件數 ＝ addon2/portfolio.csv 之略過 0 與 mktdrop_curves.json 事件數。
輸出 backtest/resultsTurnover/：table.csv、summary.md、run.log
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
os.chdir(REPO)
B = "backtest"
OUT = os.path.join(B, "resultsTurnover")
TIME = "2026-10-24（台北）"

R_STK, R_STK3 = 0.00585, 0.001425 * 0.3 * 2 + 0.003           # 0.585% ／ 0.3855%
FEE, FEE3, TAX_ETF = 0.001425, 0.001425 * 0.3, 0.001
R_ETF, R_ETF3 = FEE * 2 + TAX_ETF, FEE3 * 2 + TAX_ETF           # 0.385% ／ 0.1855%
BC_BUY, BC_SELL = FEE, FEE + TAX_ETF                            # researchTurtleS2PF 同值
W_SLEEVE = 0.20
WIN = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "早年": ("2005-02-01", "2014-12-31")}
WIN_P10_EARLY = ("2005-01-03", "2014-12-31")
WIN_64 = {"窗A": ("2018-01-15", "2026-08-24"), "確認": ("2022-01-03", "2026-08-24")}
WLABEL = {"探索": "主窗①探索 2017-03-02～2021-12-30", "確認": "2022 起（確認）2022-01-03～2026-08-24", "早年": "早年（參考）",
          "窗A": "主窗 窗A 2018-01-15～2026-08-24"}


def xy(dates, a, b):
    d = np.asarray(dates).astype(str)
    ok = np.flatnonzero((d >= a) & (d <= b) & (d != "") & (d != "nan"))
    return int(ok[0]), int(ok[-1])


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


LOG = []


def log(s):
    LOG.append(s); print(s, flush=True)


# ═════════════ 營量／營飆（researchYFallin／researchYLallin 逐筆）═════════════
def yl_book(trades, daily, wn, acct, win):
    D = daily[(daily["世界"] == wn) & (daily["帳"] == acct)].sort_values("t")
    T = trades[(trades["世界"] == wn) & (trades["帳"] == acct)]
    dates = D["日期"].fillna("").astype(str).to_numpy()
    eq = D["權益"].to_numpy(float); hv = D["持股市值"].to_numpy(float); npos = D["持股"].to_numpy(float)
    assert np.array_equal(D["t"].to_numpy(), np.arange(len(D)))
    x, y = xy(dates, *win); yrs = (y - x + 1) / 245.0
    bu = T[T["side"] == "buy"].copy(); se = T[T["side"] == "sell"].copy()
    bw = bu[(bu["t"] >= x) & (bu["t"] <= y)]; sw = se[(se["t"] >= x) & (se["t"] <= y)]
    meq, mhv = float(eq[x:y + 1].mean()), float(hv[x:y + 1].mean())
    # 持有：買進配對下一筆同代號賣出（t_sell ＞ t_buy；引擎同日先賣後買 ⇒ 同日那筆賣出屬於舊部位；買進當天不會出場）
    sells = {}
    for sid, g in se.groupby("sid"):
        sells[sid] = np.sort(g["t"].to_numpy(int))
    hd = []
    for sid, t in zip(bw["sid"], bw["t"].astype(int)):
        s = sells.get(sid)
        if s is None:
            continue
        k = np.searchsorted(s, t, side="right")
        if k < len(s):
            hd.append(int(s[k]) - t)
    r = {"x": x, "y": y, "年數": yrs, "買進筆每年": len(bw) / yrs, "賣出筆每年": len(sw) / yrs,
         "持有天數平均": float(np.mean(hd)), "持有天數中位": float(np.median(hd)), "持有筆": len(hd),
         "年換手率": float(sw["amt_out"].sum() / mhv / yrs),
         "換手每年(買進÷平均權益)": float(bw["amt"].sum() / meq / yrs),
         "成本每年_0585": float(sw["cost"].sum() / meq / yrs),
         "成本每年_3折": float((sw["amt"] * R_STK3).sum() / meq / yrs),
         "平均持股": float(npos[x:y + 1].mean()), "最多持股": int(npos[x:y + 1].max())}
    assert np.allclose(sw["cost"].to_numpy(float), sw["amt"].to_numpy(float) * R_STK, rtol=1e-12)
    return r


# ═════════════ 高10（researchPTH10tie 逐筆）═════════════
def p10_book(wn, arm, win):
    Z = np.load(f"{B}/resultsPTH10tie/main/raw_{wn}.npz")
    dates = Z["dates"].astype(str); eq = Z[f"{arm}_eq"]; nh = Z[f"{arm}_nh"]
    pos = {d: i for i, d in enumerate(dates)}
    T = pd.read_csv(f"{B}/resultsPTH10tie/main/trades_{wn}_{arm}.csv.gz", dtype={"sid": str})
    tb = T["買進日"].map(pos).to_numpy(); ts = T["賣出日"].map(pos)
    x, y = xy(dates, *win); yrs = (y - x + 1) / 245.0; meq = float(eq[x:y + 1].mean())
    amt = T["金額"].to_numpy(float); proc = T["入帳"].to_numpy(float)
    sold = ts.notna().to_numpy(); ts = ts.fillna(-1).astype(int).to_numpy()
    ib = (tb >= x) & (tb <= y); is_ = sold & (ts >= x) & (ts <= y)
    gross = proc + amt * R_STK                                       # 入帳 ＝ 金額×(1＋R−COST)
    stk = float((amt[is_] * R_STK).sum()); stk3 = float((amt[is_] * R_STK3).sum())
    # ETF 腿：個股買進同日賣 0050；個股賣出隔一交易日買回
    gro = amt / (1 - BC_SELL)
    e_sell = float((gro[ib] * BC_SELL).sum()); e_sell3 = float((gro[ib] * (FEE3 + TAX_ETF)).sum())
    tbb = ts + 1; ibb = sold & (tbb >= x) & (tbb <= y)
    e_buy = float((proc[ibb] * BC_BUY).sum()); e_buy3 = float((proc[ibb] * FEE3).sum())
    hd = (ts - tb)[ib & sold]
    return {"x": x, "y": y, "年數": yrs, "買進筆每年": int(ib.sum()) / yrs, "賣出筆每年": int(is_.sum()) / yrs, "買進筆": int(ib.sum()),
            "持有天數平均": float(hd.mean()), "持有天數中位": float(np.median(hd)), "持有筆": int(len(hd)),
            "年換手率": float(gross[is_].sum() / meq / yrs),
            "換手每年(買進÷平均權益)": float(amt[ib].sum() / meq / yrs),
            "個股成本每年": stk / meq / yrs, "ETF成本每年": (e_sell + e_buy) / meq / yrs,
            "成本每年_0585": (stk + e_sell + e_buy) / meq / yrs, "成本每年_3折": (stk3 + e_sell3 + e_buy3) / meq / yrs,
            "ETF腿每年": (int(ib.sum()) + int(ibb.sum())) / yrs,
            "平均持股": float(nh[x:y + 1].mean()), "最多持股": int(nh[x:y + 1].max())}


# ═════════════ 大跌 4 檔（addon2 事件層）═════════════
def md_events():
    d = pd.read_csv(f"{B}/resultsMktDrop/addon2/event_rows.csv")
    f = d[(d["世界"] == "主") & (d["候選"] == "F9") & (d["觸發"] == "T2") & (d["方式"] == "乙") & (d["出場"] == "主")].copy()
    cal = np.load(f"{B}/resultsBenchRejudge/mktdrop_curves.npz")["dates"].astype(str)
    pos = {c: i for i, c in enumerate(cal)}
    f["e0"] = f["事件日"].map(pos) + 1                                # t 收盤決定、t＋1 開盤買
    f["end"] = f["e0"] + f["不加碼_持有天數"].astype(int)
    f["ea"] = f["觸發日"].map(pos) + 1
    # curve2 略過規則：前一部位未賣完（j ≤ end）時新事件略過
    keep, last = [], -1
    for e0, end in zip(f["e0"], f["end"]):
        keep.append(e0 > last)
        if e0 > last:
            last = end
    f["略過"] = ~np.array(keep)
    return f, cal


def md_book(f, cal, win, addon):
    x, y = xy(cal, *win); yrs = (y - x + 1) / 245.0
    ev = f[(~f["略過"]) & (f["e0"] >= x) & (f["e0"] <= y)]
    rate = 1 - (1 - R_STK) * (1 - R_ETF); rate3 = 1 - (1 - R_STK3) * (1 - R_ETF3)
    n_ev = len(ev); nb = float(ev["首次檔數"].sum()); hd = list(ev["不加碼_持有天數"].astype(float))
    sleeves = n_ev
    nadd, nab = 0, 0.0
    if addon:
        ad = f[(~f["略過"]) & f["有觸發"].astype(bool) & f["加碼進場"].astype(bool) & (f["ea"] >= x) & (f["ea"] <= y)]
        nadd = len(ad); nab = float(ad["加碼檔數"].sum()); hd += list(ad["加碼份_持有天數"].astype(float))
        sleeves += nadd
    return {"x": x, "y": y, "年數": yrs, "事件數": n_ev, "加碼次數": nadd, "事件每年": n_ev / yrs,
            "買進筆每年": (nb + nab) / yrs, "賣出筆每年": (nb + nab) / yrs,
            "持有天數平均": float(np.mean(hd)), "持有天數中位": float(np.median(hd)), "持有筆": len(hd),
            "年換手率": sleeves * W_SLEEVE / yrs, "成本每年_0585": sleeves * W_SLEEVE * rate / yrs, "成本每年_3折": sleeves * W_SLEEVE * rate3 / yrs,
            "ETF腿每年": 2 * sleeves / yrs}


# ═════════════ 六四（results64retest summary.json）═════════════
def six4_book(cal, key, win):
    S = json.load(open(f"{B}/results64retest/summary.json", encoding="utf-8"))["① 同窗判定＋⑤ 並列"][key]["六四 v1（真 00685L）"]
    x, y = xy(cal, *win); yrs = (y - x + 1) / 245.0
    acts = S["每年動手"]; crel = S["成本／年（占市值）"]
    to = crel / R_ETF
    return {"x": x, "y": y, "年數": yrs, "買進筆每年": acts, "賣出筆每年": acts, "年換手率": to,
            "成本每年_0585": crel + R_ETF / yrs, "成本每年_3折": to * R_ETF3 + R_ETF3 / yrs,
            "調回成本每年": crel, "建倉攤提每年": R_ETF / yrs, "年化_檔": S["年化"]}


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    log(f"researchTurnover 開跑｜讀法寫死 {TIME}")
    rank = pd.read_csv(f"{B}/resultsBenchRejudge/rank.csv")
    rk = {(r["段"], r["策略"]): float(r["年化"]) for _, r in rank.iterrows()}
    cyf = pd.read_csv(f"{B}/resultsYFallin/cells.csv"); cyl = pd.read_csv(f"{B}/resultsYLallin/cells.csv")
    seeds = pd.read_csv(f"{B}/resultsYFallin/seeds.csv.gz")
    tyf = pd.read_csv(f"{B}/resultsYFallin/trades_W.csv.gz"); dyf = pd.read_csv(f"{B}/resultsYFallin/daily_W.csv.gz")
    tyl = pd.read_csv(f"{B}/resultsYLallin/trades.csv.gz"); dyl = pd.read_csv(f"{B}/resultsYLallin/daily.csv.gz")
    ptab = pd.read_csv(f"{B}/resultsPTH10tie/main/table.csv")
    psum = pd.read_csv(f"{B}/resultsPTH10seed/summary.csv")
    rows, gate = [], {}

    def cell(df, wn, sg, acct, col):
        q = df[(df["世界"] == wn) & (df["段"] == sg) & (df["帳"] == acct)]
        assert len(q) == 1, (wn, sg, acct)
        return float(q.iloc[0][col])

    YL = [("營飆 規則版（v1 抽籤）", tyf, dyf, "v1", cyf, "營飆 v1（抽籤）", "resultsYFallin/trades_W.csv.gz 帳 v1（r0）＋seeds.csv.gz 200 顆；年化 cells.csv 200 顆中位"),
          ("營飆 全買版（W1）", tyf, dyf, "W1", cyf, "W1 同日全買·可超過10檔", "resultsYFallin/trades_W.csv.gz、daily_W.csv.gz 帳 W1；年化 cells.csv"),
          ("營量 規則版（v1 relvol）", tyf, dyf, "YL", cyf, "營量 v1", "resultsYFallin/trades_W.csv.gz、daily_W.csv.gz 帳 YL；年化 cells.csv"),
          ("營量 全買版（V1）", tyl, dyl, "V1", cyl, "V1 營量同日全買·可超過20檔", "resultsYLallin/trades.csv.gz、daily.csv.gz 帳 V1；年化 resultsYLallin/cells.csv")]
    for name, tr, dl, acct, cdf, cname, src in YL:
        for sg in ("探索", "確認", "早年"):
            wn = "早年" if sg == "早年" else "主"
            r = yl_book(tr, dl, wn, acct, WIN[sg])
            # 錨點
            if acct == "v1":
                s0 = seeds[(seeds["世界"] == wn) & (seeds["帳"] == "v1") & (seeds["r"] == 0)].iloc[0]
                for k, col in (("換手每年(買進÷平均權益)", "換手每年"), ("成本每年_0585", "成本每年"), ("買進筆每年", "買進筆每年")):
                    gate[f"{name}|{sg}|{k} vs seeds r0"] = rel(r[k], float(s0[f"{sg}_{col}"]))
                sv = seeds[(seeds["世界"] == wn) & (seeds["帳"] == "v1")]
                c200 = sv[f"{sg}_成本每年"].astype(float)
                gate[f"{name}|{sg}|200 顆成本中位 vs cells"] = rel(float(c200.median()), cell(cdf, wn, sg, cname, "成本每年"))
                r["r0_成本每年_0585"] = r["成本每年_0585"]
                r["成本每年_0585"] = float(c200.median()); r["成本每年_3折"] = float(c200.median()) * R_STK3 / R_STK
                r["200顆成本p10"], r["200顆成本p90"] = float(c200.quantile(.1)), float(c200.quantile(.9))
                r["註"] = (f"成本 ＝ 200 顆中位（p10 {c200.quantile(.1):.3%}～p90 {c200.quantile(.9):.3%}）；筆數、持有、換手率 ＝ r0；"
                          f"200 顆買進筆每年 {sv[f'{sg}_買進筆每年'].astype(float).min():.2f}～{sv[f'{sg}_買進筆每年'].astype(float).max():.2f}")
            else:
                for k, col in (("換手每年(買進÷平均權益)", "換手每年"), ("成本每年_0585", "成本每年")):
                    gate[f"{name}|{sg}|{k} vs cells"] = rel(r[k], cell(cdf, wn, sg, cname, col))
                if "買進筆每年" in cdf.columns:
                    gate[f"{name}|{sg}|買進筆每年 vs cells"] = rel(r["買進筆每年"], cell(cdf, wn, sg, cname, "買進筆每年"))
                elif "交易筆數" in cdf.columns:
                    pass
                r["註"] = ""
            gate[f"{name}|{sg}|平均持股 vs cells"] = rel(r["平均持股"], cell(cdf, wn, sg, cname, "持股")) if acct != "v1" else 0.0
            ann = cell(cdf, wn, sg, cname, "年化")
            asrc = ("resultsYLallin" if cdf is cyl else "resultsYFallin") + f"/cells.csv「{cname}」{sg}"
            rows.append({"策略": name, "窗": WLABEL[sg] if sg != "早年" else "早年（參考）2005-02-01～2014-12-31", "段": sg, **r, "年化": ann,
                         "年化出處": asrc, "出處": src.split("；年化")[0]})

    # 高10
    for name, arm in (("高10 規則版（抽籤）", "原"), ("高10 F9 版", "T1")):
        for sg in ("探索", "確認", "早年"):
            wn = "早年" if sg == "早年" else "主"
            win = WIN_P10_EARLY if sg == "早年" else WIN[sg]
            r = p10_book(wn, arm, win)
            q = ptab[(ptab["世界"] == wn) & (ptab["排序"] == arm) & (ptab["滑價"] == False) & (ptab["段"] == sg)].iloc[0]  # noqa: E712
            gate[f"{name}|{sg}|成本合計 vs table"] = rel(r["成本每年_0585"], float(q["成本合計每年(實付)"]))
            gate[f"{name}|{sg}|換手每年 vs table"] = rel(r["換手每年(買進÷平均權益)"], float(q["換手每年"]))
            gate[f"{name}|{sg}|平均持有天數 vs table"] = rel(r["持有天數平均"], float(q["平均持有天數"]))
            gate[f"{name}|{sg}|買進筆 vs table"] = float(r["買進筆"] != int(q["買進筆"]))
            gate[f"{name}|{sg}|平均持股 vs table"] = rel(r["平均持股"], float(q["平均持股"]))
            a_seed = float(q["年化"])
            if arm == "原":
                if sg == "早年":
                    a200 = float(psum[(psum["世界"] == "早年") & (psum["來源"] == "同分換種子")].iloc[0]["年化_中位"])
                    src_a = "resultsPTH10seed/summary.csv 早年 200 組中位"
                else:
                    a200 = rk[(sg, "高10")]; src_a = "resultsBenchRejudge/rank.csv 高10（200 組中位）"
                ann = a200; note = f"年化 ＝ 200 組中位；原種子（本表筆數與成本所用那一組）年化 {a_seed:+.2%}（table.csv 原）"
            else:
                ann = a_seed; src_a = "resultsPTH10tie/main/table.csv T1"; note = ""
            note += ("；" if note else "") + f"成本含 0050 補位腿（個股 {r['個股成本每年']:.3%}＋0050 {r['ETF成本每年']:.3%}／年）；換手率分母 ＝ 權益（0050 補位算持倉）"
            rows.append({"策略": name, "窗": (WLABEL[sg] if sg != "早年" else "早年（參考）2005-01-03～2014-12-31"), "段": sg, **r, "年化": ann,
                         "年化出處": src_a, "出處": f"resultsPTH10tie/main/trades_{wn}_{arm}.csv.gz＋raw_{wn}.npz {arm}_eq", "註": note})

    # 大跌
    f, cal = md_events()
    P = pd.read_csv(f"{B}/resultsMktDrop/addon2/portfolio.csv")
    pf = P[(P["世界"] == "主") & (P["候選"] == "F9") & (P["觸發"] == "不加碼")]
    gate["大跌|略過事件數 vs portfolio.csv"] = float(int(f["略過"].sum()) != int(pf["略過"].sum()))
    MJ = json.load(open(f"{B}/resultsBenchRejudge/mktdrop_curves.json", encoding="utf-8"))["主世界 F9 事件數（依原段）"]
    gate["大跌|主世界事件數 vs mktdrop_curves.json"] = float(len(f) != sum(MJ.values()))
    pT2 = P[(P["世界"] == "主") & (P["候選"] == "F9") & (P["觸發"] == "T2") & (P["方式"] == "乙") & (P["出場"] == "主")]
    gate["大跌|加碼次數 vs portfolio.csv"] = float(int((f["有觸發"].astype(bool) & f["加碼進場"].astype(bool)).sum()) != int(pT2["加碼次數（段內）"].sum()))
    for name, addon, rname in (("大跌 4 檔（甲：撥 20%、不加碼）", False, "大跌 4 檔（甲：撥 20%、不加碼）"),
                               ("大跌 4 檔（甲：撥 20%、−5% 加碼同一批）", True, "大跌 4 檔（甲：撥 20%、−5% 加碼同一批）")):
        for sg in ("探索", "確認"):
            r = md_book(f, cal, WIN[sg], addon)
            note = (f"窗內 {r['事件數']} 個事件" + (f"、加碼 {r['加碼次數']} 次" if addon else "") +
                    "；平時抱 0050 不動；每事件撥 20% 買 F9 前 4（1 事件只買到 3 檔）、收復隔天賣回 0050；持有天數為事件層（首次買進到最後一份賣完）；"
                    "成本與換手率以事件當時淨值為分母；年換手率為買進側")
            rows.append({"策略": name, "窗": WLABEL[sg], "段": sg, **r, "年化": rk[(sg, rname)], "年化出處": f"resultsBenchRejudge/rank.csv「{rname}」",
                         "出處": "resultsMktDrop/addon2/event_rows.csv（F9、主、T2·乙·主列）＋resultsBenchRejudge/mktdrop_curves.npz 日曆", "註": note})

    # 六四
    for sg, key in (("窗A", "A 2018-01-15～2026-08-24"), ("確認", "B 確認段 2022-01-03～2026-08-24")):
        r = six4_book(cal, key, WIN_64[sg])
        ann = r["年化_檔"] if sg == "窗A" else rk[("確認", "六四 v1")]
        if sg == "確認":
            gate["六四|確認年化 summary.json vs rank.csv"] = rel(r["年化_檔"], rk[("確認", "六四 v1")])
        note = (f"一直持有兩檔 ETF，每年 1 月第一個交易日調回（每次 1 賣 1 買）；ETF 費率 0.385%（3 折 0.1855%）；"
                f"成本 ＝ 調回 {r['調回成本每年']:.4%}／年 ＋ 窗首建倉一次攤提 {r['建倉攤提每年']:.4%}／年；持有天數不適用")
        rows.append({"策略": "六四 v1（0050 60%＋00685L 40%）", "窗": WLABEL[sg], "段": sg, **r, "持有天數平均": np.nan, "持有天數中位": np.nan,
                     "年化": ann, "年化出處": "results64retest/summary.json 窗A" if sg == "窗A" else "resultsBenchRejudge/rank.csv 六四 v1",
                     "出處": "results64retest/summary.json「每年動手」「成本／年（占市值）」", "註": note})

    bad = {k: v for k, v in gate.items() if v > 1e-9}
    log(f"[錨點] {len(gate)} 項｜不過 {len(bad)}")
    for k, v in gate.items():
        log(f"  {'✗' if v > 1e-9 else '✓'} {k}：{v:.3g}")
    if bad:
        json.dump(gate, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        raise SystemExit(f"⛔ 錨點不過 {list(bad)}")

    df = pd.DataFrame(rows)
    df["成本占年化_0585"] = np.where(df["年化"] > 0, df["成本每年_0585"] / df["年化"], np.nan)
    df["成本占年化_3折"] = np.where(df["年化"] > 0, df["成本每年_3折"] / df["年化"], np.nan)
    cols = ["策略", "窗", "段", "年數", "平均持股", "最多持股", "買進筆每年", "賣出筆每年", "ETF腿每年", "持有天數平均", "持有天數中位", "持有筆",
            "年換手率", "換手每年(買進÷平均權益)", "成本每年_0585", "成本每年_3折", "年化", "成本占年化_0585", "成本占年化_3折",
            "事件數", "加碼次數", "個股成本每年", "ETF成本每年", "調回成本每年", "建倉攤提每年", "200顆成本p10", "200顆成本p90", "r0_成本每年_0585",
            "出處", "年化出處", "註"]
    df = df.reindex(columns=cols)
    df.to_csv(os.path.join(OUT, "table.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    json.dump(gate, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(df)
    log(f"完成｜{len(df)} 列｜{time.time() - T0:.1f} 秒")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def f_(v, fmt):
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else format(v, fmt)


def write_md(df):
    L = ["## 各策略實際換手與摩擦成本（描述、不計 N、不判定；裁定 seq459 §九.1）", "",
         f"產出 {TIME}｜回測線 researchTurnover｜全部讀既有回測逐筆／逐日輸出，⛔ 沒有重跑、沒有調參數。", "",
         "- 成本口徑：個股來回 0.585%（買 0.1425%＋賣 0.1425%＋稅 0.3%）；3 折版 0.3855%（手續費×0.3）。ETF（0050、00685L）來回 0.385%（稅 0.1%），3 折版 0.1855%。",
         "- 每年成本 ＝ 窗內實付手續費＋稅 ÷ 窗內平均淨值 ÷ 年數（大跌、六四以交易當時淨值為分母）。年化照原回測口徑，已扣 0.585%／0.385%。",
         "- 2022 起 ＝ 使用者主排名窗（2022-01-03～2026-08-24）。持有天數 ＝ 交易日。", "",
         "| 策略 | 窗 | 平均持股 | 每年買／賣筆 | 持有天數 平均／中位 | 年換手率 | 每年成本 0.585 版 | 3 折版 | 年化 | 成本占年化（0.585／3 折） |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        L.append(f"| {r['策略']} | {r['窗']} | {f_(r['平均持股'], '.1f')} | {r['買進筆每年']:.1f}／{r['賣出筆每年']:.1f} | "
                 f"{f_(r['持有天數平均'], '.0f')}／{f_(r['持有天數中位'], '.0f')} | {r['年換手率']:.2f} 倍 | {r['成本每年_0585']:.2%} | {r['成本每年_3折']:.2%} | "
                 f"{r['年化']:+.2%} | {f_(r['成本占年化_0585'] * 10, '.2f')} 成／{f_(r['成本占年化_3折'] * 10, '.2f')} 成 |")
    L += ["", "### 白話（每策略一句，2022 起窗）", ""]
    for _, r in df[df["段"] == "確認"].iterrows():
        L.append(f"- **{r['策略']}**：每年成本約佔資金 {r['成本每年_0585']:.2%}（3 折 {r['成本每年_3折']:.2%}），約佔年化報酬 {r['成本占年化_0585'] * 10:.1f} 成（3 折 {r['成本占年化_3折'] * 10:.1f} 成）；"
                 f"每年約買 {r['買進筆每年']:.0f} 筆、賣 {r['賣出筆每年']:.0f} 筆" + (f"，中位抱 {r['持有天數中位']:.0f} 個交易日。" if np.isfinite(r['持有天數中位']) else "。"))
    L += ["", "### 出處與註", ""]
    for nm, g in df.groupby("策略", sort=False):
        L.append(f"- **{nm}**：逐筆 `backtest/{g.iloc[0]['出處']}`；年化 " + "、".join(f"`{a}`" for a in dict.fromkeys(g["年化出處"])) + "。")
        for _, r in g.iterrows():
            if isinstance(r["註"], str) and r["註"]:
                L.append(f"  - {r['窗']}：{r['註']}")
    L += ["", "- 年換手率 ＝ 年賣出金額 ÷ 平均持倉市值（營量／營飆用持股市值；高10 用淨值、0050 補位算持倉；大跌為買進側撥出比例；六四 ＝ Σ單邊成交額 ÷ 當時市值）。",
          "- 營飆規則版、高10 規則版是抽籤：筆數、持有天數用單一一組（營飆 r0、高10 原種子），各組筆數幾乎相同；營飆成本取 200 顆中位，高10 年化取 200 組中位（原種子另註）。",
          "- 3 折版只把手續費打 3 折、稅不變；回測原本只扣 0.585%／0.385%，3 折版是「若手續費 3 折，每年可少付多少」的描述，⛔ 年化沒有改算。",
          "- 未含滑價（另見 researchSlip／各件滑價臂）。描述、不計 N、不判定。"]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

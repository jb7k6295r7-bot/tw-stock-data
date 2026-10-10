# -*- coding: utf-8 -*-
"""USREG-C6（← 草稿 B6，sha 1fb69a5dbca84de7）現金獲利能力：近四季營業現金流 ÷ 總資產（CBOP 代理）最高的公司比較會漲？
裁定 seq321 §三：N（美股帳）2（事件層、組合層）；判定 ＝ 合併母體（⛔ 不套 seq316）；只 S&P 500、只 S&P 400 照報；與 A4-1（品質因子）分開計 N、結果句並引。

═══ C6 補讀法（C6- 標；⭐ 寫死於 2026-10-10 23:41（台北），寫死前 ⛔ 沒看任何 C6 數字）═══
 C6-1 季財報 ＝ us-stock-data b33bde6 的 quarterly_cfo.csv、quarterly_assets.csv、quarterly_operating_income.csv（第一次公布值 value；
      可用日 ＝ first_filed 的次一交易日；Q4 ＝ 全年 − 前三季，資料庫已推算、derived 標記）；讀法與代號重用分段 ＝ researchUSA4.load_fund／key_at／q_last 原式
      （近四季 ＝ 可用日 ≤ e 的最後 4 季、相鄰季期末差 60～120 天、最新一季期末距 e ≤ 200 天、值都要有限）。
 C6-2 CBOP ＝ 近四季營業現金流合計 ÷ 最近一季期末總資產（＞ 0）；換股日 e ＝ 每月第一個交易日、排名在 e−1 收盤後（K3；「月底排名、次一交易日開盤」）。
      會計版（描述）＝ 近四季營業利益 ÷ 同一總資產；應計版（描述）＝ (近四季營業現金流 − 近四季營業利益) ÷ 總資產（高 ＝ 應計少）。
 C6-3 排除（登錄：銀行、保險 SIC 6020～6199、63xx；REIT 6798）：資料庫沒有 SIC ⇒ 用 GICS 近似（B3 sector_pit，e−1 當天）：
      industry group ∈ {Banks, Insurance}、sub-industry ∈ {Consumer Finance, Thrifts & Mortgage Finance, Commercial & Residential Mortgage Finance}、
      或 sub-industry 名稱含 REIT（含 Mortgage REITs）；sector 缺 ⇒ 不排除（計數）。researchUSA4_gics.ig_of 對照。
 C6-4 組合層（判定）：e−1 在合併母體、未排除、CBOP 可算者排名；前 10% ＝ 進場名單（依 CBOP 遞減補，⭐ 不抽籤）、前 20% ＝ 續抱（掉出 ⇒ e 開盤賣；seq308）；
      8 槽等權換股簿（K3）；成本 0.05%（敏感度 0.02、0.10%）；固定換股對照（描述）：每季、每半年、每 240 日全換成當時前 8 名（C3-4 同式）；固定 {20,60,120,240} 日（K4）。
      判定窗 ＝ [第一個換股日前一日收盤, 2026-09-30]。
 C6-5 事件層（判定）：每個換股日，同一母體（e−1 在指數、未排除、有次月報酬）CBOP 最高十分位等權次月報酬 − 母體等權次月報酬；
      平均 ＞ 0 且 95% CI（逐月 sd÷√月數）不含 0 ⇒ 測得出（＋）。描述：會計版、應計版、只 S&P 500、只 S&P 400、最低十分位。
 C6-6 描述：品質＋動能交集（CBOP 前 10% ∩ C3 MOM 前 30%，同規則：續抱 ＝ CBOP 前 20% ∩ MOM 前 30%）；產業集中度；可算覆蓋率（在指數、未排除股-月中 CBOP 可算比例）。
 C6-7 假訊號（⛔ 不判）：每個換股日把 CBOP 在可排名股票間隨機打亂 200 次（rng ＝ default_rng([20261010, 6, 1, r])），同規則 ⇒ p ＝ 隨機年化 ＞ ^SP500TR 的比例；p ≥ 5% ⇒ 警語。
 C6-8 相鄰件並引：A4-1（resultsUSA34/A4/summary.json：甲族、乙族標籤）。
 C6-9 先驗對錯（登錄 §七）：事件層最高十分位贏母體（平均 ＞ 0，約五成五）；測得出（約三成）；組合層合格或另列（約三成）；
      現金版優於會計版（約五成五；事件層平均較高）。
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC as K

READ_TS = "2026-10-10 23:41（台北）"
EX_SUB = {"consumer finance", "thrifts & mortgage finance", "commercial & residential mortgage finance"}


def load_F():
    from backtest import us_data as U
    R = K.rworld(); A4 = R["A4"]
    old = U.ROOT
    try:
        U.ROOT = K.NEWROOT
        F = A4.load_fund(R["cal"])
    finally:
        U.ROOT = old
    return F


def scores(F):
    R = K.rworld(); A4 = R["A4"]; W = R["Wd"]; cal = R["cal"]
    from backtest import researchUSA4_gics as GI
    SEG = F["SEG"]; tick = [str(t) for t in W["tick"]]; Sn = len(tick)
    CB, OI, AC, EXC = {}, {}, {}, {}
    cnt = {"排除股月": 0, "sector缺股月": 0, "在指數股月": 0, "可算股月": 0}
    M_ = R["memb"]["合併"]
    for e in R["ms"]:
        ed = int(np.datetime64(cal[e], "D").astype(np.int64)); edm = int(np.datetime64(cal[e - 1], "D").astype(np.int64))
        cb = np.full(Sn, np.nan); oi = np.full(Sn, np.nan); ac = np.full(Sn, np.nan); ex = np.zeros(Sn, bool)
        for j in np.flatnonzero(M_[e - 1]):
            t = tick[j]
            gs, gsub = A4.sector_at(R["sec"], t, edm)
            cnt["在指數股月"] += 1
            if gs is None:
                cnt["sector缺股月"] += 1
            else:
                ig = GI.ig_of(gs, gsub); sb = (gsub or "").lower()
                if ig in ("Banks", "Insurance") or sb in EX_SUB or "reit" in sb:
                    ex[j] = True; cnt["排除股月"] += 1; continue
            k = A4.key_at(SEG, t, cal[e])
            if k is None:
                continue
            q4 = A4.q_last(F, "cfo", k, e, 4, edays=ed); qa = A4.q_last(F, "assets", k, e, 1, edays=ed)
            if qa is None or not (qa[1][0] > 0):
                continue
            if q4 is not None:
                cb[j] = q4[1].sum() / qa[1][0]; cnt["可算股月"] += 1
            qo = A4.q_last(F, "operating_income", k, e, 4, edays=ed)
            if qo is not None:
                oi[j] = qo[1].sum() / qa[1][0]
                if q4 is not None:
                    ac[j] = (q4[1].sum() - qo[1].sum()) / qa[1][0]
        if np.isfinite(cb).any():
            CB[int(e)] = cb
        OI[int(e)] = oi; AC[int(e)] = ac; EXC[int(e)] = ex
    return CB, OI, AC, EXC, cnt


def run(a):
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    T0 = time.time()
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; A4 = R["A4"]
    F = load_F()
    K.log("[C6] 財報 %.0fs" % (time.time() - T0), "c6.log")
    CB, OI, AC, EXC, cnt = scores(F)
    K.log("[C6] 分數 %.0fs %s" % (time.time() - T0, cnt), "c6.log")
    t0 = min(CB); a0 = t0 - 1
    M_ = R["memb"]["合併"]
    cols = {}
    for g in ("合併", "只500", "只400"):
        BUY, KEEP, ORD = K.rank_tables(CB, R["memb"][g], 0.10, 0.20, excl=EXC)
        res, tr, s, bm = K.rank_main(KEEP, BUY, t0, w1, a0, w1)
        s["等效獨立檔數"] = K.n_eff(W, res["holds"]); s["產業集中度"] = K.sector_conc(res["holds"])
        s["2022 年 100 萬"] = K.year_window(res["eq"], cal, int(cal.searchsorted(pd.Timestamp("2022-01-03"))), int(cal.searchsorted(pd.Timestamp("2022-12-30"))))
        evs, _ = K.event_layer(CB, R["memb"][g], sorted(CB), excl=EXC)
        cols[g] = {"res": res, "tr": tr, "s": s, "ev": evs, "tab": (BUY, KEEP, ORD)}
    bm = K.metrics(R["B"], a0, w1)
    BUY, KEEP, ORD = cols["合併"]["tab"]
    sb = A4.sim_book(ORD, W, K.N_SLOTS, t0, w1)
    gate = float(np.max(np.abs(sb["eq"] - cols["合併"]["res"]["eq"])))
    K.log("[C6] 閘 %.3g" % gate, "c6.log")
    if gate > 1e-12:
        K.jdump({"⛔": "閘不過", "最大差": gate}, "C6_gate_fail.json"); raise SystemExit("C6 閘不過")
    D = {}
    for c_ in K.COST_SENS:
        _, _, s, _ = K.rank_main(KEEP, BUY, t0, w1, a0, w1, cost=c_, trades=False)
        D[f"成本{c_:.2%}"] = {k: s[k] for k in ("年化", "回落", "比值", "標籤")}
    FH = {}
    for H in K.FIXH:
        r_ = A4.sim_book(BUY, W, K.N_SLOTS, t0, w1, fixed_h=H)
        m = K.metrics(r_["eq"], a0, w1); m["標籤"] = K.label(m["年化"], m["回落"], bm["年化"], bm["回落"]); FH[f"{H}日"] = m
    D["固定天數（描述）"] = FH
    from backtest import researchUSC_c3 as C3
    CBx = {e: np.where(EXC[e], np.nan, v) for e, v in CB.items()}
    FX = {}
    for nm, mo, ev_ in (("每季", (1, 4, 7, 10), False), ("每半年", (1, 7), False), ("每240日", None, True)):
        K2, B2 = C3.fixed_tables(CBx, M_, mo, t0, ev_)
        _, _, s, _ = K.rank_main(K2, B2, t0, w1, a0, w1)
        FX[nm] = {k: s.get(k) for k in ("年化", "回落", "比值", "標籤", "每年換手")}
    D["固定換股對照"] = FX
    # 會計版、應計版
    for nm, SS in (("會計版（營業利益÷資產）", OI), ("應計版（(CFO−OI)÷資產）", AC)):
        SSx = {e: v for e, v in SS.items() if np.isfinite(v).any()}
        B2, K2, _ = K.rank_tables(SSx, M_, 0.10, 0.20, excl=EXC)
        tt = min(e for e in SSx if B2.get(e))
        _, _, s, _ = K.rank_main(K2, B2, max(tt, t0), w1, a0, w1)
        ev2, _ = K.event_layer(SSx, M_, sorted(SSx), excl=EXC)
        D[nm] = {"組合": {k: s.get(k) for k in ("年化", "回落", "比值", "標籤", "每年換手")}, "事件層": {k: ev2.get(k) for k in ("月數", "平均", "lo", "hi", "判語")}}
    # 品質＋動能交集
    S12 = C3.mom_scores()
    _, _, O30 = K.rank_tables(S12, M_, 0.30, 0.30)
    BQ, KQ = {}, {}
    for e in BUY:
        m30 = set(O30.get(e, []))
        BQ[e] = [j for j in BUY[e] if j in m30]; KQ[e] = set(j for j in KEEP[e] if j in m30)
    _, _, sq, _ = K.rank_main(KQ, BQ, t0, w1, a0, w1)
    D["品質＋動能交集（描述）"] = {k: sq.get(k) for k in ("年化", "回落", "比值", "標籤", "平均持股", "每年換手")}
    K.log("[C6] 描述 %.0fs" % (time.time() - T0), "c6.log")

    def gen(r):
        rng = np.random.default_rng([20261010, 6, 1, r]); S2 = {}
        for e, v in CB.items():
            ok = np.flatnonzero(np.isfinite(v) & M_[e - 1] & ~EXC[e]); w = np.full(len(v), np.nan)
            w[ok] = v[rng.permutation(ok)]; S2[e] = w
        B2, K2, _ = K.rank_tables(S2, M_, 0.10, 0.20, excl=EXC)
        return K2, B2
    c, m, tv = K.run_random(gen, t0, w1, a0, w1, a.seeds, a.procs)
    FK = K.rand_summary(c, m, tv, bm, cols["合併"]["s"]["年化"])
    K.log("[C6] 假訊號 %.0fs" % (time.time() - T0), "c6.log")
    lab = {g: cols[g]["s"]["標籤"] for g in cols}
    ev = cols["合併"]["ev"]; labE = ev["判語"]; Sx = cols["合併"]["s"]
    a4 = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A4/summary.json"), encoding="utf-8"))
    a41 = [x for x in a4["件"] if x["件"] == "A4-1"]
    adj = "相鄰件 A4-1（品質因子，會計盈餘版，另計 N）：" + "；".join(f"{x['名稱']} {x['標籤']}" for x in a41)
    pre = f"隨機挑也有 {FK['p（隨機年化 ＞ ^SP500TR）']:.1%}；" if FK["p（隨機年化 ＞ ^SP500TR）"] >= 0.05 else ""
    if lab["合併"] == "合格":
        body = f"買營業現金流相對資產最高的 8 檔：年化 {Sx['年化']:+.1%}（^SP500TR {bm['年化']:+.1%}）；⚠ Chen & Welch 2026 說這類效果修正後很小、需前瞻再驗"
    elif lab["合併"] == "另列":
        body = f"買營業現金流相對資產最高的 8 檔：報酬贏大盤但回落更深（年化 {Sx['年化']:+.1%}、回落 {Sx['回落']:.1%}；^SP500TR {bm['年化']:+.1%}、{bm['回落']:.1%}）"
    else:
        body = (f"2016～2026 美股現金獲利能力選股沒有贏大盤（年化 {Sx['年化']:+.1%}，^SP500TR {bm['年化']:+.1%}），"
                "與 Chen & Welch 2026「2005 年後大中型股效果近 0」一致")
    body += f"；事件層 {labE}（最高十分位每月 {ev['平均']:+.2%}，CI {ev['lo']:+.2%}～{ev['hi']:+.2%}）"
    opp = K.opposite(lab["只500"], lab["只400"])
    sent = (pre + body + f"。只 S&P 500 {lab['只500']}（{cols['只500']['s']['年化']:+.1%}）、只 S&P 400 {lab['只400']}（{cols['只400']['s']['年化']:+.1%}）"
            + ("⚠ 兩欄方向相反" if opp else "") + f"。{adj}。CBOP 是最簡代理（CFO÷資產），非 Ball 等精確版。{K.SURV}。")
    evOI = D["會計版（營業利益÷資產）"]["事件層"]
    pri = [{"先驗": "事件層最高十分位贏母體（約五成五）", "結果": f"{ev['平均']:+.3%}", "對": bool(ev["平均"] > 0)},
           {"先驗": "事件層測得出（約三成）", "結果": labE, "對": labE == "測得出（＋）"},
           {"先驗": "組合層合格或另列（約三成）", "結果": lab["合併"], "對": lab["合併"] in ("合格", "另列")},
           {"先驗": "現金版優於會計版（約五成五；事件層平均較高）", "結果": f"{ev['平均']:+.3%} vs {evOI['平均']:+.3%}", "對": bool(ev["平均"] > evOI["平均"])}]
    keep_keys = ("年化", "回落", "比值", "標籤", "平均持股", "現金比例", "每年換手", "成本／年", "出場筆數", "窗尾仍持有（檔）", "持有天數_平均", "持有天數_中位",
                 "持有天數_p10", "持有天數_p90", "持有天數_最長", "離頂多近_中位", "出場勝率", "出場原因", "計數", "等效獨立檔數", "產業集中度", "2022 年 100 萬")
    card = {"件": "C6", "名稱": "現金獲利能力（近四季營業現金流÷總資產，8 檔）", "登錄": f"USREG-B6 seq1 sha {K.REG['C6'][1]}（→ C6）", "裁定": K.RULING, "N": 2,
            "標籤": {"事件層": labE, "組合層": lab["合併"]}, "判定欄": "合併（美股原生新題，⛔ 不套 seq316）",
            "三欄": {g: f"組合 {cols[g]['s']['年化']:+.2%}／{cols[g]['s']['回落']:.2%}／{cols[g]['s']['比值']:.2f}／{lab[g]}｜事件 {cols[g]['ev']['平均']:+.3%}（{cols[g]['ev']['判語']}）" for g in cols},
            "兩欄方向相反": opp, "基準": bm,
            "條件出場必報": {k: Sx.get(k) for k in ("持有天數_平均", "持有天數_中位", "持有天數_p10", "持有天數_p90", "持有天數_最長", "窗尾仍持有（檔）", "離頂多近_中位")},
            "相鄰件": adj, "結果句": sent,
            "偏離": ["銀行、保險、REIT 排除用 GICS 近似（資料庫無 SIC）", "CBOP 用最簡代理 CFO÷資產（登錄已標「代理」）",
                     f"第一個換股日 {cal[t0].date()}（需近四季現金流可用）"],
            "補讀法": [f"C6-1～C6-9（researchUSC_c6.py docstring，{READ_TS} 寫死）", f"K1～K11（researchUSC.py，{K.READ_TS}）"],
            "相對門檻（seq321 §五）": "進出門檻是排名（前 10%／20%）⇒ 已是相對"}
    cov = {**cnt, "可算比例（在指數未排除股月）": cnt["可算股月"] / max(1, cnt["在指數股月"] - cnt["排除股月"])}
    out = {"卡片": card, "三欄": {g: {"組合": {k: cols[g]["s"].get(k) for k in keep_keys}, "事件層": cols[g]["ev"]} for g in cols}, "描述": D, "假訊號": FK,
           "先驗": pri, "覆蓋": cov, "閘": {"sim_book 最大差": gate}, "第一個換股日": str(cal[t0].date()),
           "資料": {"財報": K.NEW_COMMIT, "價格": "~/us_work/a4/world.npz（881c86a）"}, "算於": K.now_tpe(), "秒": round(time.time() - T0)}
    pd.to_pickle({"tr": {g: cols[g]["tr"] for g in cols}, "eq": {g: cols[g]["res"]["eq"] for g in cols}}, os.path.join(K.WORK, "c6_trades_eq.pkl"))
    K.jdump(out, "C6.json")
    K.log("[C6] %s" % card["三欄"], "c6.log")
    return out

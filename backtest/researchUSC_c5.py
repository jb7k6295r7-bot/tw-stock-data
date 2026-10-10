# -*- coding: utf-8 -*-
"""USREG-C5（← 草稿 B5，sha a23a0b616ed17a57）個股同月份季節性：過去幾年同一個曆月表現最好的股票，這個月會不會又最好？
裁定 seq321 §三：N（美股帳）2（事件層、組合層）；判定 ＝ 合併母體（⛔ 不套 seq316）；只 S&P 500、只 S&P 400 照報。

═══ C5 補讀法（C5- 標；⭐ 寫死於 2026-10-10 23:39（台北），寫死前 ⛔ 沒看任何 C5 數字）═══
 C5-1 月報酬 r(i, m) ＝ m 月最後一個交易日收盤 ÷ m−1 月最後一個交易日收盤 − 1（K 共用 period_ret：起點錨前 5 根內要有有效 K 棒、⛔ 不跨斷點、終點用 ffill 收盤）。
      面板 2015-12 起 ⇒ 第一個月報酬 2016-01。
 C5-2 SEAS（要買 X 月，於 X 月第一個交易日 e 開盤）＝ 過去 y ＝ 1～10 年的 r(i, X−12y) 中可得者的平均（主，至少 1 年）；描述 k＝1（只 y＝1）、k＝5（y＝1～5 全要有）。
      ⇒ 主格與 k＝1 第一個換股日 2017-01-03、k＝5 第一個 2021-01-04（照實報）。判定窗 ＝ [主格第一個換股日前一日收盤, 2026-09-30]。
 C5-3 組合層（判定）：e−1 在合併母體且 SEAS 可算者排名；前 10%（無條件進位）＝ 進場名單（依 SEAS 遞減補、⭐ 不抽籤）；續抱 ＝ 仍在前 10%（登錄「下個月不在前 10% ⇒ 賣」）。
      8 槽等權、換股簿（K3）；成本 0.05%（敏感度 0.02、0.10%）；固定 {20,60,120,240} 日只描述（K4）。
 C5-4 事件層（判定）：每個換股日 e，合併母體（e−1 在指數、有次月報酬）中 SEAS 最高十分位等權次月報酬 − 母體等權次月報酬（次月 ＝ e−1 收盤 → e 所在月最後一日收盤）；
      平均 ＞ 0 且 95% CI（逐月 sd÷√月數）不含 0 ⇒「同月強勢有延續」。描述：最低十分位、k＝1、k＝5、只 S&P 500、只 S&P 400、
      扣掉一般動能（e 當月 C3 MOM 前 10% 的股票排除後重算）。
 C5-5 假訊號（⛔ 不判）：每個換股日把 SEAS 在可排名股票間隨機打亂（200 次；rng ＝ default_rng([20261010, 5, 1, r])），規則同主臂 ⇒ p ＝ 隨機年化 ＞ ^SP500TR 的比例；
      p ≥ 5% ⇒ 結果句前加「隨機挑也有 x%」。錯開一個月（拿 X−1 曆月的過去同月報酬去選 X 月）：事件層與組合層各算一次（安慰劑）。
 C5-6 必報：年化、回落、比值、每年換手、成本／年、持有天數分佈、窗尾仍持有、離頂多近、產業集中度（K3：平均產業數、最大產業占比）、2022 那一年 100 萬、等效獨立檔數。
 C5-7 先驗對錯（登錄 §八）：事件層測得出為正（約四成五）；組合層合格或另列（約二成五）；錯開一個月表現差於主訊號（約六成：組合層年化較低）；
      持股明顯集中在少數產業（約七成：最大產業占比平均 ≥ 0.375，即平均至少 3／8 檔同產業）。
"""
from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC as K

READ_TS = "2026-10-10 23:39（台北）"


def monthly_returns():
    R = K.rworld(); last = R["last"]
    MR = {}
    for k in sorted(last):
        if (k - 1) in last and last[k] <= R["w1"]:
            MR[k] = K.period_ret(last[k - 1], last[k])
    return MR


def seas(MR, shift=0, kmode="all"):
    R = K.rworld(); ym = R["ym"]; S = {}
    for e in R["ms"]:
        X = int(ym[e]) - shift
        ys = range(1, 11) if kmode == "all" else (range(1, 2) if kmode == "k1" else range(1, 6))
        arr = [MR.get(X - 12 * y) for y in ys]
        if kmode == "k5" and any(a is None for a in arr):
            continue
        arr = [a for a in arr if a is not None]
        if not arr:
            continue
        A = np.vstack(arr)
        with np.errstate(invalid="ignore"):
            cnt = np.isfinite(A).sum(0); m = np.nanmean(np.where(np.isfinite(A), A, np.nan), axis=0) if True else None
        if kmode == "k5":
            m = np.where(cnt == len(arr), m, np.nan)
        else:
            m = np.where(cnt >= 1, m, np.nan)
        if np.isfinite(m).any():
            S[int(e)] = m
    return S


def run(a):
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    T0 = time.time()
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; A4 = R["A4"]
    MR = monthly_returns()
    S = seas(MR)
    t0 = min(S); a0 = t0 - 1
    M_ = R["memb"]["合併"]
    cols = {}
    for g in ("合併", "只500", "只400"):
        BUY, KEEP, ORD = K.rank_tables(S, R["memb"][g], 0.10, 0.10)
        res, tr, s, bm = K.rank_main(KEEP, BUY, t0, w1, a0, w1)
        s["等效獨立檔數"] = K.n_eff(W, res["holds"]); s["產業集中度"] = K.sector_conc(res["holds"])
        s["2022 年 100 萬"] = K.year_window(res["eq"], cal, int(cal.searchsorted(pd.Timestamp("2022-01-03"))), int(cal.searchsorted(pd.Timestamp("2022-12-30"))))
        evs, _ = K.event_layer(S, R["memb"][g], sorted(S))
        cols[g] = {"res": res, "tr": tr, "s": s, "ev": evs, "tab": (BUY, KEEP, ORD)}
    bm = K.metrics(R["B"], a0, w1)
    BUY, KEEP, ORD = cols["合併"]["tab"]
    sb = A4.sim_book(ORD, W, K.N_SLOTS, t0, w1)
    gate = float(np.max(np.abs(sb["eq"] - cols["合併"]["res"]["eq"])))
    K.log("[C5] 閘 %.3g" % gate, "c5.log")
    if gate > 1e-12:
        K.jdump({"⛔": "閘不過", "最大差": gate}, "C5_gate_fail.json"); raise SystemExit("C5 閘不過")
    D = {}
    for c_ in K.COST_SENS:
        _, _, s, _ = K.rank_main(KEEP, BUY, t0, w1, a0, w1, cost=c_, trades=False)
        D[f"成本{c_:.2%}"] = {k: s[k] for k in ("年化", "回落", "比值", "標籤")}
    FH = {}
    for H in K.FIXH:
        r_ = A4.sim_book(BUY, W, K.N_SLOTS, t0, w1, fixed_h=H)
        m = K.metrics(r_["eq"], a0, w1); m["標籤"] = K.label(m["年化"], m["回落"], bm["年化"], bm["回落"]); FH[f"{H}日"] = m
    D["固定天數（描述）"] = FH
    for km in ("k1", "k5"):
        Sk = seas(MR, 0, km)
        Bk, Kk, _ = K.rank_tables(Sk, M_, 0.10, 0.10)
        tk = min(Sk)
        _, _, s, bmk = K.rank_main(Kk, Bk, tk, w1, tk - 1, w1)
        ev, _ = K.event_layer(Sk, M_, sorted(Sk))
        D[f"{km}"] = {"第一個換股日": str(cal[tk].date()), "組合": {k: s[k] for k in ("年化", "回落", "比值", "標籤", "每年換手")}, "基準": bmk,
                      "事件層": {k: ev.get(k) for k in ("月數", "平均", "lo", "hi", "判語")}}
    # 扣掉一般動能
    from backtest import researchUSC_c3 as C3
    S12 = C3.mom_scores()
    B12, _, _ = K.rank_tables(S12, M_, 0.10, 0.10)
    excl = {}
    for e in S:
        x = np.zeros(W["C"].shape[1], bool)
        if e in B12:
            x[B12[e]] = True
        excl[e] = x
    ev_x, _ = K.event_layer(S, M_, sorted(S), excl=excl)
    D["事件層_扣一般動能前10%"] = {k: ev_x.get(k) for k in ("月數", "平均", "lo", "hi", "判語")}
    # 安慰劑：錯開一個月
    Sp = seas(MR, 1)
    Bp, Kp, _ = K.rank_tables(Sp, M_, 0.10, 0.10)
    _, _, sp, _ = K.rank_main(Kp, Bp, t0, w1, a0, w1)
    evp, _ = K.event_layer(Sp, M_, sorted(Sp))
    D["安慰劑_錯開一個月"] = {"組合": {k: sp[k] for k in ("年化", "回落", "比值", "標籤", "每年換手")}, "事件層": {k: evp.get(k) for k in ("月數", "平均", "lo", "hi", "判語")}}
    K.log("[C5] 描述 %.0fs" % (time.time() - T0), "c5.log")

    def gen(r):
        rng = np.random.default_rng([20261010, 5, 1, r]); S2 = {}
        for e, v in S.items():
            ok = np.flatnonzero(np.isfinite(v) & M_[e - 1]); w = np.full(len(v), np.nan)
            w[ok] = v[rng.permutation(ok)]; S2[e] = w
        B2, K2, _ = K.rank_tables(S2, M_, 0.10, 0.10)
        return K2, B2
    c, m, tv = K.run_random(gen, t0, w1, a0, w1, a.seeds, a.procs)
    FK = K.rand_summary(c, m, tv, bm, cols["合併"]["s"]["年化"])
    K.log("[C5] 假訊號 %.0fs" % (time.time() - T0), "c5.log")
    lab = {g: cols[g]["s"]["標籤"] for g in cols}
    ev = cols["合併"]["ev"]; labE = ev["判語"]
    Sx = cols["合併"]["s"]
    pre = f"隨機挑也有 {FK['p（隨機年化 ＞ ^SP500TR）']:.1%}；" if FK["p（隨機年化 ＞ ^SP500TR）"] >= 0.05 else ""
    if lab["合併"] == "合格":
        body = f"每月買過去同月最強的 8 檔：年化 {Sx['年化']:+.1%}（^SP500TR {bm['年化']:+.1%}）；⚠ 每月幾乎全換、只有約 10 年資料、需前瞻再驗"
    elif labE == "測得出（＋）":
        body = f"同月強勢在美股仍看得到（最高十分位每月多 {ev['平均']:+.2%}），但只做多 8 檔贏不了大盤（年化 {Sx['年化']:+.1%}，^SP500TR {bm['年化']:+.1%}，{lab['合併']}）"
    else:
        body = (f"2016 年後美股同月份季節性看不到（事件層 {labE}：最高十分位每月 {ev['平均']:+.2%}，CI {ev['lo']:+.2%}～{ev['hi']:+.2%}）；"
                f"組合層年化 {Sx['年化']:+.1%}（^SP500TR {bm['年化']:+.1%}）⇒ {lab['合併']}")
    opp = K.opposite(lab["只500"], lab["只400"])
    sent = (pre + body + f"。只 S&P 500 {lab['只500']}（{cols['只500']['s']['年化']:+.1%}；事件層 {cols['只500']['ev']['判語']}）、只 S&P 400 {lab['只400']}"
            f"（{cols['只400']['s']['年化']:+.1%}；事件層 {cols['只400']['ev']['判語']}）" + ("⚠ 兩欄方向相反" if opp else "") + f"。{K.CW}。{K.SURV}。")
    conc = Sx["產業集中度"]["最大產業占比平均"]
    pri = [{"先驗": "事件層測得出為正（約四成五）", "結果": labE, "對": labE == "測得出（＋）"},
           {"先驗": "組合層合格或另列（約二成五）", "結果": lab["合併"], "對": lab["合併"] in ("合格", "另列")},
           {"先驗": "錯開一個月差於主訊號（約六成；組合年化較低）", "結果": f"{D['安慰劑_錯開一個月']['組合']['年化']:+.1%} vs {Sx['年化']:+.1%}",
            "對": bool(D["安慰劑_錯開一個月"]["組合"]["年化"] < Sx["年化"])},
           {"先驗": "持股明顯集中在少數產業（約七成；最大產業占比平均 ≥ 0.375）", "結果": f"{conc:.2f}", "對": bool(conc >= 0.375)}]
    keep_keys = ("年化", "回落", "比值", "標籤", "平均持股", "現金比例", "每年換手", "成本／年", "出場筆數", "窗尾仍持有（檔）", "持有天數_平均", "持有天數_中位",
                 "持有天數_p10", "持有天數_p90", "持有天數_最長", "離頂多近_中位", "出場勝率", "出場原因", "計數", "等效獨立檔數", "產業集中度", "2022 年 100 萬")
    card = {"件": "C5", "名稱": "同月份季節性（買過去同月最強的 8 檔）", "登錄": f"USREG-B5 seq1 sha {K.REG['C5'][1]}（→ C5）", "裁定": K.RULING, "N": 2,
            "標籤": {"事件層": labE, "組合層": lab["合併"]}, "判定欄": "合併（美股原生新題，⛔ 不套 seq316）",
            "三欄": {g: f"組合 {cols[g]['s']['年化']:+.2%}／{cols[g]['s']['回落']:.2%}／{cols[g]['s']['比值']:.2f}／{lab[g]}｜事件 {cols[g]['ev']['平均']:+.3%}（{cols[g]['ev']['判語']}）" for g in cols},
            "兩欄方向相反": opp, "基準": bm,
            "條件出場必報": {k: Sx.get(k) for k in ("持有天數_平均", "持有天數_中位", "持有天數_p10", "持有天數_p90", "持有天數_最長", "窗尾仍持有（檔）", "離頂多近_中位")},
            "結果句": sent, "偏離": ["第一個換股日 2017-01-03（需至少 1 年同月報酬；面板 2015-12 起）；判定窗 2016-12-30～2026-09-30"],
            "補讀法": [f"C5-1～C5-7（researchUSC_c5.py docstring，{READ_TS} 寫死）", f"K1～K11（researchUSC.py，{K.READ_TS}）"],
            "相對門檻（seq321 §五）": "進出門檻是排名（前 10%）⇒ 已是相對"}
    out = {"卡片": card, "三欄": {g: {"組合": {k: cols[g]["s"].get(k) for k in keep_keys}, "事件層": cols[g]["ev"]} for g in cols}, "描述": D, "假訊號": FK,
           "先驗": pri, "閘": {"sim_book 最大差": gate}, "第一個換股日": str(cal[t0].date()), "算於": K.now_tpe(), "秒": round(time.time() - T0)}
    pd.to_pickle({"tr": {g: cols[g]["tr"] for g in cols}, "eq": {g: cols[g]["res"]["eq"] for g in cols}}, os.path.join(K.WORK, "c5_trades_eq.pkl"))
    K.jdump(out, "C5.json")
    K.log("[C5] %s" % card["三欄"], "c5.log")
    return out

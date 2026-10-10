# -*- coding: utf-8 -*-
"""USREG-C3（← 草稿 B3，sha a98a1275a19c69f7）美股經典動能（過去 12 個月扣最近 1 個月）。
裁定 seq321 §三：N（美股帳）1；判定 ＝ 合併母體（⛔ 不套 seq316）；只 S&P 500、只 S&P 400 照報；與 A3-12（動能改良版）分開計 N、結果句並引。

═══ C3 補讀法（C3- 標；⭐ 寫死於 2026-10-10 23:30（台北），寫死前 ⛔ 沒看任何 C3 數字）═══
 C3-1 換股日 e ＝ 每月第一個交易日（K3）；量測月底 ＝ e−1（上個月最後一個交易日）。MOM ＝ 收盤(e 往前第 2 個月底) ÷ 收盤(e 往前第 13 個月底) − 1
      （＝ 量測月底往前第 12 個月底到第 1 個月底，扣最近 1 個月）；兩個錨點各自前 5 根內要有有效 K 棒、錨點 12 到 e−1 之間 ⛔ 不跨斷點，否則不排。
      面板 2015-12 起 ⇒ 第一個量測月底 2016-12-30、第一個換股日 2017-01-03；判定窗 ＝ [2016-12-30 收盤, 2026-09-30]（K2）。
 C3-2 排名母體 ＝ e−1 當天在該欄指數（合併 ＝ S&P 500∪400）且 MOM 可算者；同分依代號序。前 10%（無條件進位）＝ 進場名單（依 MOM 遞減補空槽，⭐ 不抽籤）；
      前 20% ＝ 續抱名單；持股掉出前 20%（含不在母體）⇒ e 開盤賣（seq308「不再符合才換」、⛔ 無最長天數）。8 槽等權（K3）。
 C3-3 鄰格（描述）：進 5%／出 20%、進 10%／出 30%、進 10%／出 10%。成本敏感度 0.02%、0.10%（描述）。
 C3-4 固定換股對照（描述）：每月、每季（1、4、7、10 月）、每半年（1、7 月）、每 240 日（自第一個換股日起第一個 ≥ 240k 交易日的換股日）——
      換股日全部換成當時 MOM 前 8 名（仍在前 8 名者續抱、不重買）。固定 {20,60,120,240} 日（seq308，K4）：researchUSA4.sim_book fixed_h，名單 ＝ 前 10%。
 C3-5 描述臂：a 大盤濾網 ＝ SPY 還原收盤（USREG-A1 資料）在 e−1 低於其 200 日線 ⇒ e 不新買（續抱規則不變）；b 6−1（e 往前第 2 個月底 ÷ 第 7 個月底 − 1）；
      c 動能崩跌段單獨報：2020-03-02～2020-06-30、2022-01-03～2022-12-30、2025-01-02～2025-06-30、2025-07-01～2025-12-31（主臂與 ^SP500TR 同段報酬）；
      d 產業集中度（K3 持股、GICS sector B3：平均產業數、最大產業占比）；e 只 S&P 500、只 S&P 400（K5）。
      抽籤臂（描述）：進場名單內抽籤（種子 102000＋r、200 顆）。
 C3-6 假訊號臂 f：每個換股日從合併母體隨機挑股補空槽，每筆抱的換股期數從主臂已出場交易的「持有換股期數」分佈抽（同換手頻率）；200 次；
      rng ＝ default_rng([20261010, 3, 6, r])；p ＝ 隨機年化 ＞ ^SP500TR 的比例；p ≥ 5% ⇒ 結果句前加「隨機挑也有 x%」。
 C3-7 必報：年化、回落、比值、每年換手、持有天數分佈、窗尾仍持有、離頂多近、與四種固定換股的差、2022 那一年 100 萬剩多少（2021-12-31 收盤起）、等效獨立檔數（K6）。
 C3-8 閘：主臂（合併）權益 ＝ researchUSA4.sim_book（sel ＝ 前 20% 依序）逐日相同（≤1e−12；K3）。
 C3-9 相鄰件並引：A3-12（resultsUSA34/A3/A3-12.json；seq321：M2～M4 事後擴母體 ⇒ 只描述，M1 不合格）。
 C3-10 先驗對錯（登錄 §七）：主臂另列或合格（約五成五）；a 回落較淺（約七成）、年化較低（約六成）；只 S&P 400 年化高於只 S&P 500（約五成）；假訊號 p ≥ 5%（約四成）。
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC as K

READ_TS = "2026-10-10 23:30（台北）"
CRASH = {"2020-03～06": ("2020-03-02", "2020-06-30"), "2022 全年": ("2022-01-03", "2022-12-30"),
         "2025 上半": ("2025-01-02", "2025-06-30"), "2025 下半": ("2025-07-01", "2025-12-31")}


def mom_scores(back_far=13, back_near=2):
    R = K.rworld(); ym = R["ym"]; last = R["last"]; W = R["Wd"]; cpb = R["cpb"]
    S = {}
    for e in R["ms"]:
        k = int(ym[e])
        if (k - back_far) not in last:
            continue
        a12 = last[k - back_far]; a1 = last[k - back_near]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = W["CF"][a1] / W["CF"][a12] - 1
        ok = K.anchor_ok(a12) & K.anchor_ok(a1) & ((cpb[e - 1] - cpb[a12]) == 0) & np.isfinite(r)
        S[int(e)] = np.where(ok, r, np.nan)
    return S


def spy_filter():
    """SPY（USREG-A1 資料）e−1 收盤 ＜ 200 日線 ⇒ True（不新買）。"""
    from backtest import researchUSA1_data as A
    R = K.rworld(); cal = R["cal"]
    y = A.yahoo("SPY"); c = (y["adjclose"]).astype(float)
    c.index = pd.to_datetime(c.index); c = c.dropna()
    ma = c.rolling(200, min_periods=200).mean()
    below = (c < ma).reindex(cal).ffill().fillna(False).to_numpy(bool)
    return {int(e): bool(below[e - 1]) for e in R["ms"]}


def fixed_tables(scores, M_, months, t0, every240=False):
    R = K.rworld(); ym = R["ym"]; KEEP, BUY = {}, {}
    es = [e for e in sorted(scores) if e >= t0]
    if every240:
        sel = []; nxt = t0
        for e in es:
            if e >= nxt:
                sel.append(e); nxt = e + 240
    else:
        sel = [e for e in es if (int(ym[e]) % 12 + 1) in months]
    for e in sel:
        sc = scores[e]; el = np.flatnonzero(np.isfinite(sc) & M_[e - 1])
        order = el[np.lexsort((el, -sc[el]))][:K.N_SLOTS]
        BUY[e] = [int(x) for x in order]; KEEP[e] = set(BUY[e])
    return KEEP, BUY


def run(a):
    T0 = time.time()
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; A4 = R["A4"]
    S12 = mom_scores()
    t0 = min(e for e, v in S12.items() if np.isfinite(v).any()); a0 = t0 - 1
    cols = {}
    TAB = {}
    for g in ("合併", "只500", "只400"):
        BUY, KEEP, ORD = K.rank_tables(S12, R["memb"][g])
        TAB[g] = (BUY, KEEP, ORD)
        res, tr, s, bm = K.rank_main(KEEP, BUY, t0, w1, a0, w1)
        s["等效獨立檔數"] = K.n_eff(W, res["holds"]); s["產業集中度"] = K.sector_conc(res["holds"])
        s["2022 年 100 萬"] = K.year_window(res["eq"], cal, int(cal.searchsorted(pd.Timestamp("2022-01-03"))), int(cal.searchsorted(pd.Timestamp("2022-12-30"))))
        s["崩跌段"] = {k: {"主臂": K.win_ret(res["eq"], cal, *v), "^SP500TR": K.win_ret(R["B"], cal, *v)} for k, v in CRASH.items()}
        cols[g] = {"res": res, "tr": tr, "s": s}
    bm = K.metrics(R["B"], a0, w1)
    # 閘（C3-8）
    BUY, KEEP, ORD = TAB["合併"]
    sb = A4.sim_book(ORD, W, K.N_SLOTS, t0, w1)
    gate = float(np.max(np.abs(sb["eq"] - cols["合併"]["res"]["eq"])))
    K.log("[C3] 閘 sim_book 最大差 %.3g" % gate, "c3.log")
    if gate > 1e-12:
        K.jdump({"⛔": "閘不過", "最大差": gate}, "C3_gate_fail.json"); raise SystemExit("C3 閘不過")
    M_ = R["memb"]["合併"]
    D = {}
    # 成本
    for c_ in K.COST_SENS:
        _, _, s, _ = K.rank_main(KEEP, BUY, t0, w1, a0, w1, cost=c_, trades=False)
        D[f"成本{c_:.2%}"] = {k: s[k] for k in ("年化", "回落", "比值", "標籤")}
    # 鄰格
    for en, ex in ((0.05, 0.20), (0.10, 0.30), (0.10, 0.10)):
        B2, K2, _ = K.rank_tables(S12, M_, en, ex)
        _, tr2, s, _ = K.rank_main(K2, B2, t0, w1, a0, w1)
        D[f"鄰格 進{en:.0%}出{ex:.0%}"] = {k: s.get(k) for k in ("年化", "回落", "比值", "標籤", "每年換手", "持有天數_中位", "窗尾仍持有（檔）")}
    # 固定換股
    FX = {}
    for nm, mo, ev in (("每月", tuple(range(1, 13)), False), ("每季", (1, 4, 7, 10), False), ("每半年", (1, 7), False), ("每240日", None, True)):
        K2, B2 = fixed_tables(S12, M_, mo, t0, ev)
        _, _, s, _ = K.rank_main(K2, B2, t0, w1, a0, w1)
        FX[nm] = {k: s.get(k) for k in ("年化", "回落", "比值", "標籤", "每年換手")}
        FX[nm]["主臂−本臂（年化點）"] = (cols["合併"]["s"]["年化"] - s["年化"]) * 100
    D["固定換股對照"] = FX
    # 固定天數（seq308 描述）
    FH = {}
    for H in K.FIXH:
        r_ = A4.sim_book(BUY, W, K.N_SLOTS, t0, w1, fixed_h=H)
        m = K.metrics(r_["eq"], a0, w1); m["標籤"] = K.label(m["年化"], m["回落"], bm["年化"], bm["回落"]); FH[f"{H}日"] = m
    D["固定天數（描述）"] = FH
    # a 大盤濾網
    flt = spy_filter()
    Ba = {e: ([] if flt.get(e) else v) for e, v in BUY.items()}
    _, tra, sa, _ = K.rank_main(KEEP, Ba, t0, w1, a0, w1)
    D["a 大盤濾網"] = {**{k: sa.get(k) for k in ("年化", "回落", "比值", "標籤", "每年換手", "持有天數_中位")}, "不新買的換股日比例": float(np.mean([flt[e] for e in BUY]))}
    # b 6−1
    S6 = mom_scores(7, 2)
    B6, K6, _ = K.rank_tables(S6, M_)
    _, _, s6, _ = K.rank_main(K6, B6, t0, w1, a0, w1)
    D["b 6−1"] = {k: s6.get(k) for k in ("年化", "回落", "比值", "標籤", "每年換手")}
    K.log("[C3] 描述臂 %.0fs" % (time.time() - T0), "c3.log")
    # 抽籤臂
    def gen_lot(r):
        rng = np.random.default_rng(K.SEED0 + r)
        return KEEP, {e: [v[i] for i in rng.permutation(len(v))] for e, v in BUY.items()}
    c, m, tv = K.run_random(gen_lot, t0, w1, a0, w1, a.seeds, a.procs)
    D["抽籤臂"] = K.rand_summary(c, m, tv, bm, cols["合併"]["s"]["年化"])
    # 假訊號 f（C3-6）
    ms = np.array(sorted(BUY)); trm = cols["合併"]["tr"]
    hl = np.array([max(1, int(np.searchsorted(ms, x[2], side="right") - 1 - np.searchsorted(ms, x[1], side="left")))
                   for x in trm if x[5] == "換股"], int)
    memb = M_

    def gen_fake(r):
        rng = np.random.default_rng([20261010, 3, 6, r]); rem = {}

        def kf(t, held):
            keep = set()
            for j in held:
                rem[j] = rem.get(j, 1) - 1
                if rem[j] > 0:
                    keep.add(j)
            return keep

        def bf(t, held):
            el = np.flatnonzero(memb[t - 1] & W["valid"][t])
            return [int(x) for x in rng.permutation(el)[:40]]

        def ob(j, t):
            rem[j] = int(rng.choice(hl))
        return kf, bf, ob
    K._JOB["rebs"] = ms
    c, m, tv = K.run_random(gen_fake, t0, w1, a0, w1, a.seeds, a.procs)
    FK = K.rand_summary(c, m, tv, bm, cols["合併"]["s"]["年化"]); FK["主臂持有換股期數中位"] = float(np.median(hl))
    K.log("[C3] 隨機臂 %.0fs" % (time.time() - T0), "c3.log")
    # 標籤與結果句
    lab = {g: cols[g]["s"]["標籤"] for g in cols}
    S = cols["合併"]["s"]
    a312 = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A3/A3-12.json"), encoding="utf-8"))["卡片"]
    adj = f"相鄰件 A3-12（動能改良版，另計 N）：{a312['標籤']}；seq321：M2～M4 事後擴母體 ⇒ 只描述、M1 不合格"
    pre = f"隨機挑也有 {FK['p（隨機年化 ＞ ^SP500TR）']:.1%}；" if FK["p（隨機年化 ＞ ^SP500TR）"] >= 0.05 else ""
    if lab["合併"] == "合格":
        body = (f"美股 S&P 500＋400 買過去一年最強的 8 檔、掉出前 20% 才換：年化 {S['年化']:+.1%}（^SP500TR {bm['年化']:+.1%}），回落 {S['回落']:.1%}；"
                "⚠ 只有約 10 年資料、需前瞻再驗；動能崩跌時（例 2009 型）可能一個月跌兩三成")
    elif lab["合併"] == "另列":
        body = f"報酬贏大盤但回落更深：年化 {S['年化']:+.1%}（^SP500TR {bm['年化']:+.1%}），回落 {S['回落']:.1%}（^SP500TR {bm['回落']:.1%}）"
    else:
        body = f"2016～2026 美股原始動能沒有贏 ^SP500TR：年化 {S['年化']:+.1%}（^SP500TR {bm['年化']:+.1%}），回落 {S['回落']:.1%}"
    opp = K.opposite(lab["只500"], lab["只400"])
    sent = (pre + body + f"。只 S&P 500 {lab['只500']}（{cols['只500']['s']['年化']:+.1%}）、只 S&P 400 {lab['只400']}（{cols['只400']['s']['年化']:+.1%}）"
            + ("⚠ 兩欄方向相反" if opp else "") + f"。{adj}。{K.CW}。{K.SURV}。")
    pri = [{"先驗": "主臂另列或合格（約五成五）", "結果": lab["合併"], "對": lab["合併"] in ("合格", "另列")},
           {"先驗": "a 大盤濾網版回落較淺（約七成）", "結果": f"{D['a 大盤濾網']['回落']:.1%} vs {S['回落']:.1%}", "對": bool(D["a 大盤濾網"]["回落"] > S["回落"])},
           {"先驗": "a 大盤濾網版年化較低（約六成）", "結果": f"{D['a 大盤濾網']['年化']:+.1%} vs {S['年化']:+.1%}", "對": bool(D["a 大盤濾網"]["年化"] < S["年化"])},
           {"先驗": "只 S&P 400 年化高於只 S&P 500（約五成）", "結果": f"{cols['只400']['s']['年化']:+.1%} vs {cols['只500']['s']['年化']:+.1%}",
            "對": bool(cols["只400"]["s"]["年化"] > cols["只500"]["s"]["年化"])},
           {"先驗": "假訊號 p ≥ 5%（約四成）", "結果": f"{FK['p（隨機年化 ＞ ^SP500TR）']:.1%}", "對": bool(FK["p（隨機年化 ＞ ^SP500TR）"] >= 0.05)}]
    keep_keys = ("年化", "回落", "比值", "標籤", "平均持股", "現金比例", "每年換手", "成本／年", "出場筆數", "窗尾仍持有（檔）", "持有天數_平均", "持有天數_中位",
                 "持有天數_p10", "持有天數_p90", "持有天數_最長", "離頂多近_中位", "出場勝率", "出場原因", "計數", "等效獨立檔數", "產業集中度", "2022 年 100 萬", "崩跌段")
    card = {"件": "C3", "名稱": "經典動能（12−1 個月、8 檔、進前 10% 出前 20%）", "登錄": f"USREG-B3 seq1 sha {K.REG['C3'][1]}（→ C3）", "裁定": K.RULING,
            "N": 1, "標籤": lab["合併"], "判定欄": "合併（美股原生新題，⛔ 不套 seq316）",
            "三欄": {g: f"{cols[g]['s']['年化']:+.2%}／{cols[g]['s']['回落']:.2%}／{cols[g]['s']['比值']:.2f}／{lab[g]}" for g in cols},
            "兩欄方向相反": opp, "基準": bm,
            "條件出場必報": {k: S.get(k) for k in ("持有天數_平均", "持有天數_中位", "持有天數_p10", "持有天數_p90", "持有天數_最長", "窗尾仍持有（檔）", "離頂多近_中位")},
            "相鄰件": adj, "結果句": sent,
            "偏離": ["第一個換股日 2017-01-03（面板 2015-12 起 ⇒ 12 個月回看要到 2016-12 底）；判定窗 2016-12-30～2026-09-30，⛔ 不是登錄字面的 2016-01-04 起",
                     "持股掉出指數 ⇒ 不在排名 ⇒ 落選賣出（A4 G3 換股簿型）"],
            "補讀法": [f"C3-1～C3-10（researchUSC_c3.py docstring，{READ_TS} 寫死）", f"K1～K11（researchUSC.py，{K.READ_TS}）"],
            "相對門檻（seq321 §五）": "進出門檻是排名（前 10%／20%）⇒ 已是相對"}
    out = {"卡片": card, "三欄": {g: {k: cols[g]["s"].get(k) for k in keep_keys} for g in cols}, "描述": D, "假訊號": FK, "先驗": pri,
           "閘": {"sim_book 最大差": gate}, "第一個換股日": str(cal[t0].date()), "資料": {"world": "~/us_work/a4/world.npz（881c86a）"},
           "算於": K.now_tpe(), "秒": round(time.time() - T0)}
    pd.to_pickle({"tr": {g: cols[g]["tr"] for g in cols}, "eq": {g: cols[g]["res"]["eq"] for g in cols}}, os.path.join(K.WORK, "c3_trades_eq.pkl"))
    K.jdump(out, "C3.json")
    K.log("[C3] %s｜%s" % (card["標籤"], card["三欄"]), "c3.log")
    return out

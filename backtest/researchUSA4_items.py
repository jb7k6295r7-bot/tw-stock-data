# -*- coding: utf-8 -*-
"""USREG-A4 各件（A4-1～7、A4-9、A4-12、A4-13；A4-10 見 researchUSA4_surge、A4-11 見 researchUSA4_ml）。共同讀法 G1～G16 見 researchUSA4.py。

═══ 逐件執行者補讀法（寫死於 2026-10-07 11:54（台北）；寫死前 ⛔ 沒看任何 A4 報酬）═══
A4-1 品質因子（台股 seq1 24e7fb594193b9c0 §二～§四）
  I1 換股日 ＝ G8 月初 e；頻率 月／季／半年；N 10／20；甲 ＝ 該欄母體 ∩ 非 GICS Financials（B3 sector 缺 ⇒ 不排除、計數）∩ Qk 可算，Qk 由高到低前 N（同值依代號）；
     乙 ＝ 再 ∩ 季營收創 8 季新高（P6）；Q1 ROE（TTM 淨利 ÷ 兩期權益平均）Q2 營業利益÷期末資產 Q3 ROA Q4 研發強度（P7；研發缺 ⇒ 不排名）。
  I2 退化（K7）：探索段平均持股 ＜ N÷2 或現金 ＞ 30% ⇒ 不進挑選；兩族各挑 1、各自標籤（N 2）。
  I3 描述：乙族同池「量放大」挑（e−1 那根 收盤×量 ÷ 前 60 根中位，營量 v1 挑法）同格並列；同池隨機 reps 次 ⇒ p；Q1～Q4 兩兩 Spearman（每個 e 橫斷面平均）。
A4-2 大師三套（台股 seq4 48365ba96fb2b1a9 §一～§四；seq2 主臂改條件；seq319 Q10）
  I4 條件 ＝ prep 同式（M1～M4、X2、PE15、O1、O3；資料缺 ⇒ 不符）；量測日 ＝ G8 月初 e，起點 2018-03-01（三套同起點），探索 2018-03～2021-12、確認 2022-01～2026-09。
  I5 主臂「不再符合才換」：e 當天 4 條全成立 ⇒ e 開盤進（10 槽、抽籤）；之後每個月初 e′ 檢查（e′ 該檔不在面板＝資料缺 ⇒ 不符）⇒ 不再全成立 ⇒ e′ 開盤賣；
     ⛔ 無最長天數；窗尾仍持有 ⇒ 2026-09-30 收盤結算。描述：固定 20／60／120／240 日（原文 H{20,60,120}）。
A4-3 外部研究三件（台股 seq1 d412ffe18178b3be §二～§四；台股回測 researchExtX1 K2～K8、researchExt A1～A6、B1～B5 同式移植）
  I6 X1：月底資料 ⇒ 次一交易日（月初 e）開盤整批調回目標權重（原文「營收延後 14 天」是為月營收公布；季財報改 first_filed 可用日 ⇒ 不再延後，prep 已定）；
     池 ＝ 季營收年增 10%～150%（「連 3 個月年增 ＞ 0」⇒ 連 1 季，被包含）；四因子池內百分位（average）相加：季年增、60 日報酬、單季 ROE（單季淨利 ÷ 兩期權益平均）、
     60 日波動（低者高）；不在池或缺 ⇒ 0；分數 rank ≤ 40 入選、權重 ∝ 分數²。60 日報酬與波動用【還原】收盤（⚠ 原文用未還原；美股未還原價有拆股跳動 ⇒ 改還原，逐字標）。
  I7 X2：換股月 ＝ 2005-01 起每 5 個月（月份序 ≡ 0 mod 5）之月初 e；因子用 e−1；TV100 ＝ [e−100, e−1] 日報酬標準差（≥ 75 個）；
     CGO 的 P ＝（高＋低＋收）÷3（還原；美股無成交金額）、V ＝ 量 ÷ 今日基準股數（e 的 shares_today；100 日內視為不變，⚠ 逐字標）、V＞1 截 1；
     母體 ＝ 該欄母體 ∩ 有效 K 棒 ≥ 100；TV100 升冪取前 ⌈10%⌉ ⇒ CGO 降冪取 50；主臂「不再符合才換」＝ 換股簿 N 50 續抱仍入選。
  I8 X1、X2 判定 ＝ 全窗 2016-01-04～2026-09-30（P12）；確認段並報（描述）。
  I9 X3：事件 ＝ 季營收 ＞ 之前所有季（之前 ≥ 8 季有值；prep 同式）；T ＝ 可用日 av（first_filed 次一交易日，prep），進場 T＋1 開盤；
     R_H ＝ PX(T＋1＋H) ÷ O(T＋1) − 1（PX ＝ 有效開盤、否則最後收盤；USM B2）；X ＝ R − EW_H(T＋1)（合併母體等權，同日同 H、(T＋1, T＋1＋H] 無斷點者；成本相消）；
     同檔 20 日內只取第一筆；[T, T＋1＋H] 斷點或 T＋1 無 K 棒 ⇒ 剔除；判定 H20、全窗（P12）、researchM.summ／verdict；60 日描述；
     描述格：公告前 20 日漲 ≥ 10%（法人淨賣超拿掉）。「與營飆 v1 重疊」美股無營飆 v1 ⇒ 不做（照實寫）。
A4-4 低週轉（台股 seq1 47ac98f3c6b5fb02）
  I10 TO(L) ＝ prep to20／to60／to120（L 日均量 ÷ 今日基準股數）；缺 ⇒ 不進候選；甲 ＝ 該欄母體 TO 最低 N；乙 ＝ 創 8 季新高池內 TO 最低 N；
     L 3 × 頻率 3 × N 2 ＝ 18 格／族；兩族各挑 1、各自標籤；N 計 1（prep 清單）。描述：反向臂（TO 最高）、乙同池量放大挑、同池隨機。
A4-5 強勢類股（台股 seq1 bb1c8b224f5bb587）
  I11 換股日 ＝ 每月 10 日之後（日 ＞ 10）第一個交易日 t（照用）；類股 ＝ G15 industry group（t−1 當天 B3）；成分 ＝ t 當天在該欄母體且 t−1 有收盤者；成分 ＜ 5 不排名；
     強度 ＝ 成分 ffill 收盤 CF[t−1]÷CF[t−1−L] − 1 的等權平均（L ∈ {20,60,120}）；前 k 強（k ∈ {1,3,5}）；
     (a) 前 k 類股內個股同 L 報酬前 10；(b) 其中季營收創 8 季新高（可用日 ≤ t）者依 L 報酬取前 10、不足留現金；月換、續抱仍入選；18 格挑 1。
     描述：隨機 k 類股（同挑法）reps 次 ⇒ p；(c) 類股內隨機 200 次。
A4-6 產業營收加速季版（台股 seq3 42339de513c98702；台股回測 researchIndRev_prereg P2～P8 同式移植）
  I12 換股月 1／4／7／10（季）、1／7（半年）、1（年）的月初 e；資料季 Q* ＝ 期末日 ≤ e − 90 天的最近曆季（P10）；公司季營收依期末日對到最近曆季末（±45 天）；
     只用可用日 ≤ e 的值；產業 ＝ G15 industry group（e 當天 B3，panel 同式）；排除 Banks、Financial Services、Insurance（台股「金融保險」）；
     同公司基準：num(q) ＝ Σ 當季營收、den(q) ＝ Σ 去年同季營收（兩季都有值的公司）；A1 ＝ num(Q*)÷den(Q*) − 1；
     A2 ＝ A1 −（Σ_{Q*−3..Q*} num ÷ Σ den − 1）；A3 ＝ A1 − A1(Q*−1)；公司數 ＜ 5 不排名；成員 ＝ e 當天在該欄母體者。
  I13 挑股：S1 市值前 20、S2 前 3、S3 創 8 季新高者依市值前 10；目標金額 ＝ 前一日權益 ÷（K × n_i）（S3 ÷（K×10））；續抱仍入選。
     出場 E0 定期｜E1 每個季換股月月初（含非換股的季月）持有產業 A2(Q*) ＜ 0 且前一季 A2 ＞ 0 ⇒ 當日開盤賣｜E2／E3 產業持股等權指數從本次持有期間最高回落 ≥ 20／30% ⇒ 次日開盤賣；
     賣出後現金到下一換股日；出場條件仍成立的產業跳過、由下一名遞補（台股 P4、P7）。216 格；退化 ＝ 探索段平均持股 ＜ 3 或現金 ＞ 30%。
     描述：隨機挑產業 reps 次 ⇒ p；反向臂；挑中格同 A×K×S×R 下 E0～E3 對照。
A4-7 事件型兩件（台股 seq2 8eae2968c12438fc；台股回測 researchEvt E1～E10 同式移植）
  I14 庫藏股代理（P11、Q6）：每筆季買回（buyback 欄）可用日 av ⇒ T ＝ av、進場 T＋1 開盤（prep「公告日 → first_filed 次一交易日」）；
     比值 ＝ 季買回 ÷ 市值（G10，T 的前一日原始收盤 × T 可用股數）；「每季前 10%」⇒ 期末日所在曆季為一組，門檻 ＝【前一曆季那一組】比值的第 90 百分位
     （同季的組要等全部公司申報完才知道 ⇒ 用前一季的組定門檻、⛔ 不前視；執行者補）；比值 ≥ 門檻且 ＞ 0 ⇒ 事件；5%、20% 只描述（⛔ 不計 N、不改挑）。
  I15 成分剔除（P11）：membership／membership_sp400 changes 的 removed_ticker（含升級到 S&P 500 的 S&P 400 剔除，照 P11 字面；另報排除同日升級的描述版）；
     T ＝ 生效日當天或之前最後一個交易日、進場 T＋1 開盤；欄 ＝ 被剔除的指數（只400／只500）；公告日臂拿掉。
  I16 單筆層（描述）：同檔 20 日內只取第一筆；R_H ＝ CF[min(T＋H, 窗尾)] ÷ O[T＋1] − 1，H ∈ {5,20,60,120}；基準② ＝ 同一個 T、同 H，
     該欄母體中 T＋1 可買、無斷點、前 20 日報酬可算者依前 20 日報酬分十分位，同十分位其他股平均；判定量 ＝ X − 0.05%；曆月群集 CI。
  I17 組合層（判定）：10 槽、抽籤、xpos ＝ T＋H 收盤（台股 E10），H ∈ {20, 60, 120} 探索挑 1、確認判；探索段年均事件 ＜ 10 ⇒ 依構造不可判定。
A4-9 年線戰法基本面季版（台股外部作者批 seq1 62e4026f16879fed §二 W2、§三）
  I18 技術面候選 ＝ prep W2c（s 站上日、j 拉回日）；基本面在 s 判：最新季營收年增 ＞ 0 或 最新季淨利由負轉正（Q7 兩條「或」都留；G9 分段鍵）；
     訊號 j ⇒ j＋1 開盤進；出場 ＝ 持有中收盤由上往下穿越 MA10／20／60（相鄰有效 K 棒；t−1 收 ≥ MA、t 收 ＜ MA，t ≥ j＋1）⇒ t＋1 開盤賣；⛔ 無最長天數；
     10 槽、抽籤、可再進；3 格探索挑 1；退化 ＝ 主窗事件 ＜ 200 或年均 ＜ 10、或探索段段尾未出場 ＞ 50%。
A4-12 十一票（台股 seq1 dbc1881f24a76661）
  I19 票 ＝ prep MONTH 列：① 創 8 季新高 ② 季年增 ≥ 15% ③ hi250_L ④ stack（MA5＞10＞20＞60）⑤ strong（4 取 3）⑥ td9_L ⑦ rsi_L ⑧ s06_L
     ⑨ vr20_250 在當月該欄母體前 20% ⑩ utb_L（−1）⑪ vsc_L（−1）；缺 ⇒ 0 票；分數同分抽籤（default_rng([20261007, 12, e])）；L 3 × 月／季 × N 2 ＝ 12 格。
     描述：甲 ①～⑤、乙 ⑥～⑪、丙 隨機 reps 次 ⇒ p。
A4-13 探索批（台股 seq4 d41c9151eca3fd53）
  I20 條件 ＝ F01 季年增、F03 季增率、F04 距 8 季最高、F05 −近 1 月報酬、F06 近 3 月、F07 近 6 月、F08 12−1、F09 收盤 ÷ 250 日最高、F10 收盤 ÷ MA60 − 1、
     F11 −60 日波動、F12 20 日均量 ÷ 其前 60 日均量、F16 盈餘殖利率（淨利 ≤ 0 ⇒ 缺）、F17 近 365 日配息 ÷ 收盤、F18 淨值 ÷ 市值；F02 ≡ F01（退化）、F13～F15 拿掉。
     單一 14 ＋ 兩兩 91 ＝ 105 格；候選 ＝ 該欄母體內百分位（兩兩 ＝ 兩百分位平均、兩者都要有值）前 10%（⌊0.1 n⌋ 檔，同分依代號）；
     8 槽、抽籤、e 開盤進、第 120 根收盤出（xpos ＝ e＋119）；探索段只讀 2021-12-31 以前價格（段尾收盤結算），確認段 2022-01-03 重新起跑。
  I21 線索 ＝ 探索段年化 ＞ ^SP500TR 同段者依比值排、每個條件最多 2 條、取 5；運氣基準（丙）＝ 假條件（每月隨機 10%）× 105 個、每個 50 顆種子中位（⚠ 台股 200 顆，
     本件為省時改 50，逐字標）⇒ 線索比值在「105 次取最好」分佈的分位（F^105）；確認段 S0（同欄母體每月隨機 10%）200 顆 ⇒ 合格比例 p。
"""
from __future__ import annotations

import json
import math
import os
import pickle
import time
from collections import Counter, defaultdict
from itertools import combinations
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backtest import researchUSA4 as C

FREQ = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7), "年": (1,)}
_X: dict = {}


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


# ═════════════ 共用上下文 ═════════════
def context(lim=False):
    if "ctx" in _X:
        return _X["ctx"]
    cal, w0, w1, sp, c0 = C.setup_cal()
    Wd = C.load_world(lim)
    M, FD = C.load_panel(lim)
    M = M[M["t"].isin(set(Wd["tick"]))].copy()
    M["j"] = M["t"].map(Wd["ix"]).astype(int)
    M["mon"] = cal[M["e"].to_numpy()].month
    segs = {"探索": (w0, sp), "確認": (c0, w1), "全窗": (w0, w1)}
    BM = C.bench_metrics(cal, segs)
    MS = C.month_starts(cal, w0, w1)
    X = {"cal": cal, "w0": w0, "w1": w1, "sp": sp, "c0": c0, "Wd": Wd, "M": M, "F": FD["F"], "W2c": FD["W2c"], "sec": FD["sec"],
         "segs": segs, "BM": BM, "MS": MS, "lim": lim}
    X["ME"] = {e: g for e, g in M.groupby("e")}
    _X["ctx"] = X
    return X


def popmask(g, pop):
    if pop == "合併":
        return np.ones(len(g), bool)
    return g["m4"].to_numpy(bool) if pop == "只400" else g["m5"].to_numpy(bool)


def rebs_of(X, fq, start=None):
    mons = FREQ[fq]
    out = [e for e in X["MS"] if (mons is None or X["cal"][e].month in mons)]
    if start is not None:
        out = [e for e in out if e >= start]
    return out


def topn_sel(g, col, N, asc=False):
    d = g[np.isfinite(g[col].to_numpy(float))]
    d = d.sort_values([col, "t"], ascending=[asc, True])
    return d["j"].tolist()[:N]


def pick_cell(rows, N_of=None):
    """rows：[(cell, 探索 stats dict, 標籤)]；台股慣例：去退化 ⇒ 過判準者取比值最高；都沒過取比值最高；平手年化高、再原序。"""
    ok = [r for r in rows if not r[1].get("退化")]
    if not ok:
        return None
    q = [r for r in ok if r[2] == "合格"]
    pool = q if q else ok
    best = sorted(enumerate(pool), key=lambda t: (-(t[1][1]["比值"] if np.isfinite(t[1][1]["比值"]) else -9), -t[1][1]["年化"], t[0]))[0][1]
    return best[0]


def degenerate(st, N):
    return bool(st["平均持股"] < N / 2 or st["現金比例"] > 0.30)


def book_judge(X, sel_fn, N, t0, cfg_name, reps_fn=None, reps=0, fixed=True, extra=None, weights_fn=None, full_rebal=False):
    """挑中格：三欄主臂＋判定；固定天數描述；成本敏感度；|ret|＞50% 敏感度；持有分佈。sel_fn(pop) ⇒ sel 或 (sel, weights)。"""
    Wd, segs, BM, w1 = X["Wd"], X["segs"], X["BM"], X["w1"]
    out = {"格": cfg_name, "欄": {}}
    brk50 = Wd["pb"] | Wd["f50"]
    for pop in C.COLS:
        s = sel_fn(pop)
        wts = None
        if isinstance(s, tuple):
            s, wts = s
        tr = []
        res = C.sim_book(s, Wd, N, t0, w1, weights=wts, full_rebal=full_rebal, trades_out=tr)
        R = {nm: C.book_stats(res, a, b, trades=tr, Wd=Wd) for nm, (a, b) in segs.items() if b >= t0}
        for nm in R:
            R[nm]["標籤"] = C.lab(R[nm]["年化"], R[nm]["回落"], BM[nm]["年化"], BM[nm]["回落"])
        R["窗尾仍持有（檔）"] = len(res["open"]); R["計數"] = res["cnt"]
        if pop != "只500":
            for cs in C.COST_SENS:
                r2 = C.sim_book(s, Wd, N, t0, w1, cost=cs, weights=wts, full_rebal=full_rebal)
                R["成本%.2f%%" % (cs * 100)] = {nm: C.seg_metrics(r2["eq"], a, b) for nm, (a, b) in segs.items() if b >= t0}
            r3 = C.sim_book(s, Wd, N, t0, w1, brk=brk50, weights=wts, full_rebal=full_rebal)
            R["ret50剔除"] = {nm: dict(C.seg_metrics(r3["eq"], a, b), 標籤=C.lab(*[C.seg_metrics(r3["eq"], a, b)[k] for k in ("年化", "回落")],
                                                                          BM[nm]["年化"], BM[nm]["回落"])) for nm, (a, b) in segs.items() if b >= t0}
            if fixed and wts is None:
                R["固定天數（描述）"] = {}
                for H in C.FIXH:
                    trh = []
                    r4 = C.sim_book(s, Wd, N, t0, w1, fixed_h=H, trades_out=trh)
                    R["固定天數（描述）"]["H%d" % H] = {nm: C.book_stats(r4, a, b) for nm, (a, b) in segs.items() if b >= t0}
        out["欄"][pop] = R
        if pop == "合併":
            out["_eq"] = res["eq"]
    return out


def final_from(out, seg="確認"):
    lc = out["欄"]["合併"][seg]["標籤"]; l4 = out["欄"]["只400"][seg]["標籤"]
    return C.final_label(lc, l4), lc, l4


# ═════════════ 假訊號（換股簿同池隨機）═════════════
def _rand_book(args):
    k, r = args
    s = _X["rand"][k]
    rng = np.random.default_rng([20261007, s["item"], s["arm"], r])
    sel = {}
    for e, pool in s["pools"].items():
        pool = sorted(pool)
        sel[e] = list(rng.choice(pool, size=min(s["N"], len(pool)), replace=False)) if len(pool) else []
    res = C.sim_book(sel, _X["ctx"]["Wd"], s["N"], s["t0"], _X["ctx"]["w1"])
    return k, r, {nm: C.seg_metrics(res["eq"], a, b) for nm, (a, b) in _X["ctx"]["segs"].items() if b >= s["t0"]}


def rand_books(specs, reps, procs):
    """specs：{k: {"pools": {e: [j]}, "N":, "t0":, "item": int, "arm": int}} ⇒ {k: DataFrame}。"""
    _X["rand"] = specs
    jobs = [(k, r) for k in specs for r in range(reps)]
    with Pool(procs) as pool:
        res = pool.map(_rand_book, jobs, chunksize=max(1, len(jobs) // (procs * 10)))
    D = defaultdict(list)
    for k, r, m in res:
        row = {"r": r}
        for nm, v in m.items():
            row[nm + "_年化"] = v["年化"]; row[nm + "_回落"] = v["回落"]
        D[k].append(row)
    return {k: pd.DataFrame(v) for k, v in D.items()}


def p_of(df, seg, c):
    x = df[seg + "_年化"].to_numpy(float)
    return float(np.mean(x >= c)) if len(x) else np.nan


# ═════════════ A4-1 品質因子 ═════════════
QK = {"Q1": "roe", "Q2": "oia", "Q3": "roa", "Q4": "rnd_int"}


def a41(X, a):
    M = X["ME"]; Wd = X["Wd"]; w0, sp = X["w0"], X["sp"]
    log("A4-1 品質因子")
    relv = relvol_map(X)

    def sel_of(fam, k, fq, N, pop, by=None):
        sel = {}; short = 0; nreb = 0; psz = []
        for e in rebs_of(X, fq):
            g = M.get(e)
            if g is None:
                continue
            g = g[popmask(g, pop)]
            g = g[g["sector"].fillna("") != "Financials"]
            if fam == "乙":
                g = g[g["rev_hi8"].astype(float).fillna(0) > 0]
                psz.append(len(g))
            nreb += 1
            if by == "量":
                g = g.assign(rv=[relv.get((e, j), np.nan) for j in g["j"]])
                sel[e] = topn_sel(g, "rv", N)
            elif by == "rand":
                sel[e] = g[np.isfinite(g[QK[k]].to_numpy(float))]["j"].tolist() if fam == "甲" else g["j"].tolist()
            else:
                sel[e] = topn_sel(g, QK[k], N)
            short += int(len(sel[e]) < N) if by != "rand" else 0
        return sel, (short / nreb if nreb else np.nan), (float(np.mean(psz)) if psz else np.nan)
    R = {"件": "A4-1", "名稱": "品質因子選股（ROE、營業利益÷資產、ROA、研發強度）", "族": {}}
    for fam in ("甲", "乙"):
        rows = []; grid = []
        for k in QK:
            for fq in ("月", "季", "半年"):
                for N in (10, 20):
                    s, shortf, psz = sel_of(fam, k, fq, N, "合併")
                    res = C.sim_book(s, Wd, N, w0, X["w1"])
                    st = C.book_stats(res, w0, sp); st["退化"] = degenerate(st, N)
                    l_ = C.lab(st["年化"], st["回落"], X["BM"]["探索"]["年化"], X["BM"]["探索"]["回落"])
                    cf = C.book_stats(res, X["c0"], X["w1"])
                    rows.append(((k, fq, N), st, l_))
                    grid.append({"Qk": k, "頻率": fq, "N": N, "探索": st, "探索標籤": l_, "確認（描述）": cf, "湊不滿N的換股比例": shortf, "池平均檔數": psz})
        ch = pick_cell(rows)
        k, fq, N = ch
        J = book_judge(X, lambda pop: sel_of(fam, k, fq, N, pop)[0], N, w0, "%s族 %s %s N%d" % (fam, k, fq, N))
        fl, lc, l4 = final_from(J)
        J.pop("_eq", None)
        D = {"挑中格": {"Qk": k, "量測": QK[k], "頻率": fq, "N": N}, "判定": J, "標籤": fl, "合併確認": lc, "只400確認": l4, "全表": grid}
        # 同池隨機
        pools = {e: v for e, v in sel_of(fam, k, fq, N, "合併", by="rand")[0].items()}
        rb = rand_books({"r": {"pools": pools, "N": N, "t0": w0, "item": 1, "arm": 1 if fam == "甲" else 2}}, a.reps, a.procs)["r"]
        D["同池隨機"] = {"次數": a.reps, "p_確認": p_of(rb, "確認", J["欄"]["合併"]["確認"]["年化"]),
                       "隨機年化中位_確認": float(rb["確認_年化"].median()), "隨機合格比例_確認": float(np.mean([C.lab(c, m, X["BM"]["確認"]["年化"], X["BM"]["確認"]["回落"]) == "合格" for c, m in zip(rb["確認_年化"], rb["確認_回落"])]))}
        if fam == "乙":
            s, _, _ = sel_of(fam, k, fq, N, "合併", by="量")
            res = C.sim_book(s, Wd, N, w0, X["w1"])
            D["同池量放大挑（描述）"] = {nm: C.book_stats(res, a_, b_) for nm, (a_, b_) in X["segs"].items()}
        R["族"][fam] = D
    # Q1～Q4 兩兩 Spearman
    cors = defaultdict(list)
    for e in X["MS"]:
        g = M.get(e)
        if g is None:
            continue
        g = g[g["sector"].fillna("") != "Financials"]
        for x_, y_ in combinations(QK, 2):
            d = g[[QK[x_], QK[y_]]].astype(float).dropna()
            if len(d) >= 30:
                cors[x_ + "×" + y_].append(d.rank().corr().iloc[0, 1])
    R["Q兩兩Spearman（逐月平均）"] = {k: float(np.mean(v)) for k, v in cors.items()}
    R["N"] = 2
    R["附註"] = [C.IDEA, C.NO_EARLY, "乙族池用季營收創 8 季新高：" + C.Q14, "研發強度覆蓋 S&P 500 27.6%／S&P 400 22.7%（prep §三）", C.SURV]
    return R


def relvol_map(X):
    """e ⇒ e−1 那根（收盤×量）÷ 前 60 根有效 K 棒中位（營量 v1 挑法；描述臂）。"""
    if "relv" in _X:
        return _X["relv"]
    Wd = X["Wd"]; out = {}
    amt = Wd["CF"] * np.nan_to_num(Wd["V"].astype(float))
    for j in range(amt.shape[1]):
        vb = np.flatnonzero(Wd["valid"][:, j])
        if len(vb) < 61:
            continue
        a = amt[vb, j]
        med = pd.Series(a).shift(1).rolling(60, min_periods=60).median().to_numpy()
        for e in X["MS"]:
            k = int(np.searchsorted(vb, e)) - 1
            if k >= 60 and np.isfinite(med[k]) and med[k] > 0:
                out[(e, j)] = a[k] / med[k]
    _X["relv"] = out
    return out


# ═════════════ A4-2 大師三套 ═════════════
SETS = {"墨菲": ("M1", "M2", "M3", "M4"), "喜偉": ("M2", "X2", "PE15", "M3"), "歐沙那希": ("O1", "M2", "O3", "PE15")}


def a42(X, a):
    log("A4-2 大師三套")
    cal, Wd, w1 = X["cal"], X["Wd"], X["w1"]
    start = int(cal.searchsorted(pd.Timestamp("2018-03-01")))
    segs = {"探索": (start, X["sp"]), "確認": (X["c0"], w1), "全窗": (start, w1)}
    BM = C.bench_metrics(cal, segs)
    M = X["M"]
    MSs = [e for e in X["MS"] if e >= start]
    R = {"件": "A4-2", "名稱": "大師三套（仿 App 墨菲／喜偉／歐沙那希條件）", "起點": str(cal[start].date()), "套": {}}
    arms = {}; info = {}
    for nm, cs in SETS.items():
        ok = np.ones(len(M), bool)
        for c_ in cs:
            ok &= (M[c_].astype(float).fillna(0).to_numpy() > 0)
        S = M.assign(ok=ok)[["j", "e", "ok", "m4", "m5"]]
        okset = set(zip(S.loc[S["ok"], "j"], S.loc[S["ok"], "e"]))
        cand = S[S["ok"] & (S["e"] >= start)]
        cnt = cand.groupby("e").size().reindex(MSs).fillna(0)
        info[nm] = {"每月候選中位": float(cnt.median()), "p10": float(cnt.quantile(0.1)), "p90": float(cnt.quantile(0.9)),
                    "＜10檔月比例": float((cnt < 10).mean()), "常常湊不滿10檔": bool((cnt < 10).mean() > 0.30)}
        for pop in C.COLS:
            cp = cand if pop == "合併" else cand[cand["m4"] if pop == "只400" else cand["m5"]]
            rows = {"main": [], **{"fix%d" % H: [] for H in C.FIXH}}
            for j, e in zip(cp["j"], cp["e"]):
                o = Wd["O"][e, j]
                if not (np.isfinite(o) and o > 0):
                    continue
                x = None
                for e2 in MSs:
                    if e2 <= e:
                        continue
                    if (j, e2) not in okset:
                        x = e2; break
                if x is None or x > w1:
                    x = w1; g = Wd["CF"][w1, j] / o - 1
                else:
                    ox = Wd["O"][x, j]; g = (ox if np.isfinite(ox) and ox > 0 else Wd["CF"][x, j]) / o - 1
                mo = str(cal[e])[:7]
                if not C.crosses(Wd["pb"], j, e, x):
                    rows["main"].append((j, e, x, g, mo))
                for H in C.FIXH:
                    xh = min(e + H - 1, w1)
                    if not C.crosses(Wd["pb"], j, e, xh):
                        rows["fix%d" % H].append((j, e, xh, Wd["CF"][xh, j] / o - 1, mo))
            for arm, rr in rows.items():
                if arm != "main" and pop == "只500":
                    continue
                arms[(nm, pop, arm)] = {"sig": C.mk_sig(rr), "N": 10, "segs": segs, "cost": C.COST, "audit": arm == "main" and pop == "合併"}
            if pop != "只500":
                for cs_ in C.COST_SENS:
                    arms[(nm, pop, "cost%g" % cs_)] = {"sig": C.mk_sig(rows["main"]), "N": 10, "segs": segs, "cost": cs_}
                # |ret|>50%
                f50 = Wd["pb"] | Wd["f50"]
                arms[(nm, pop, "ret50")] = {"sig": C.mk_sig([r_ for r_ in rows["main"] if not C.crosses(f50, r_[0], r_[1], r_[2])]), "N": 10, "segs": segs, "cost": C.COST}
    D = C.run_slots(arms, Wd, a.procs, a.seeds)
    for nm in SETS:
        T = {"候選": info[nm], "欄": {}}
        for pop in C.COLS:
            T["欄"][pop] = {arm: C.slot_summary(D[(nm, pop, arm)], segs, BM) for (n_, p_, arm) in arms if n_ == nm and p_ == pop}
            T["欄"][pop]["訊號筆數"] = int(len(arms[(nm, pop, "main")]["sig"]))
        sig = arms[(nm, "合併", "main")]["sig"]
        T["持有分佈（合併主臂、種子102000實際成交）"] = holds_from(D[(nm, "合併", "main")], sig, Wd, dict(X, segs=segs))
        lc = T["欄"]["合併"]["main"]["確認"]["標籤"]; l4 = T["欄"]["只400"]["main"]["確認"]["標籤"]
        T["標籤"] = C.final_label(lc, l4); T["合併確認"] = lc; T["只400確認"] = l4
        T["前綴"] = "常常湊不滿 10 檔" if info[nm]["常常湊不滿10檔"] else ""
        R["套"][nm] = T
    R["基準"] = BM
    R["N"] = 3
    R["附註"] = [C.IDEA, "起點 2018-03（墨菲候選首次 ≥10 檔；seq319 Q10）、資料缺 ⇒ 不符", "喜偉、歐沙那希照原文、⛔ 不放寬",
               "名稱一律「仿 App〔大師〕條件」，算法照本線定義、不保證與 App 相同", "負債 ＝ 資產 − 權益、EPS ＝ 年淨利 ÷ 封面股數（代理）", C.SURV]
    return R


# ═════════════ A4-3 外部研究三件 ═════════════
def x2_months(X):
    out = []
    for e in X["MS"]:
        d = X["cal"][e]
        if ((d.year * 12 + d.month) - (2005 * 12 + 1)) % 5 == 0:
            out.append(e)
    return out


def a43(X, a):
    log("A4-3 外部研究三件")
    Wd, cal, w0, w1, M = X["Wd"], X["cal"], X["w0"], X["w1"], X["ME"]
    R = {"件": "A4-3", "名稱": "外部研究三件（X1 多因子、X2 CGO＋低波動、X3 季營收創紀錄）", "N": 3}
    CF = Wd["CF"]
    # ── X1
    def x1_sel(pop, fq="月"):
        sel = {}; wts = {}
        for e in rebs_of(X, fq):
            g = M.get(e)
            if g is None:
                continue
            g = g[popmask(g, pop)].copy()
            y = g["rev_yoy"].astype(float)
            pool = (y > 0.10) & (y < 1.50)
            g = g[pool.to_numpy()]
            if not len(g):
                sel[e] = []; wts[e] = {}; continue
            j = g["j"].to_numpy()
            mom = CF[e - 1, j] / CF[e - 61, j] - 1 if e - 61 >= 0 else np.full(len(j), np.nan)
            sc = np.zeros(len(g))
            for v, asc in ((g["rev_yoy"].astype(float).to_numpy(), True), (mom, True), (g["roe_q"].astype(float).to_numpy(), True),
                           (g["vol60"].astype(float).to_numpy(), False)):
                r = pd.Series(v).rank(pct=True, ascending=asc).fillna(0).to_numpy()
                sc += r
            rk = pd.Series(sc).rank(ascending=False).to_numpy()
            m = rk <= 40
            jj = j[m]; ss = sc[m] ** 2
            tw = {int(x): float(s / ss.sum()) for x, s in zip(jj, ss)} if ss.sum() > 0 else {}
            sel[e] = [int(x) for x in jj]; wts[e] = tw
        return sel, wts
    J1 = book_judge(X, lambda pop: x1_sel(pop), 40, w0, "X1 月換 40 檔 分數平方加權", fixed=False, full_rebal=True)
    eq1 = J1.pop("_eq", None)
    fl, lc, l4 = final_from(J1, "全窗")
    X1 = {"判定": J1, "標籤（全窗，P12）": fl, "合併全窗": lc, "只400全窗": l4,
          "確認段標籤（描述）": final_from(J1, "確認")[0]}
    for fq in ("季", "半年"):
        s, w = x1_sel("合併", fq)
        res = C.sim_book(s, Wd, 40, w0, w1, weights=w, full_rebal=True)
        X1["頻率%s（描述）" % fq] = {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}
    pools = {}
    for e in rebs_of(X, "月"):
        g = M.get(e)
        if g is None:
            continue
        y = g["rev_yoy"].astype(float)
        pools[e] = g[((y > 0.10) & (y < 1.50)).to_numpy()]["j"].tolist()
    rb = rand_books({"x1": {"pools": pools, "N": 40, "t0": w0, "item": 3, "arm": 1}}, a.reps, a.procs)["x1"]
    X1["同池隨機（等權 min(40, 池)）"] = {"次數": a.reps, "p_全窗": p_of(rb, "全窗", J1["欄"]["合併"]["全窗"]["年化"]),
                                    "隨機年化中位_全窗": float(rb["全窗_年化"].median())}
    X1["讀法差異"] = "60 日報酬、波動用還原價（原文未還原；美股未還原價有拆股跳動）"
    R["X1"] = X1
    # ── X2
    def x2_sel(pop, months=None):
        sel = {}
        ems = x2_months(X) if months is None else months
        for e in ems:
            g = M.get(e)
            if g is None:
                continue
            g = g[popmask(g, pop)]
            rows = []
            for j, sh, tk in zip(g["j"], g["shares_today"].astype(float), g["t"]):
                ck = (int(j), e)
                if ck not in _X["x2cache"]:
                    _X["x2cache"][ck] = cgo_tv(Wd, int(j), e, sh)
                v = _X["x2cache"][ck]
                if v is not None:
                    rows.append((int(j), v[0], v[1], tk))
            if not rows:
                sel[e] = []; continue
            d = pd.DataFrame(rows, columns=["j", "tv", "cgo", "t"])
            k = int(math.ceil(0.10 * len(d)))
            low = d.sort_values(["tv", "t"]).head(k)
            sel[e] = low.sort_values(["cgo", "t"], ascending=[False, True])["j"].tolist()[:50]
        return sel
    _X["x2cache"] = {}
    J2 = book_judge(X, lambda pop: x2_sel(pop), 50, w0, "X2 每 5 個月 50 檔等權（不再符合才換）")
    J2.pop("_eq", None)
    fl, lc, l4 = final_from(J2, "全窗")
    R["X2"] = {"判定": J2, "標籤（全窗，P12）": fl, "合併全窗": lc, "只400全窗": l4, "確認段標籤（描述）": final_from(J2, "確認")[0],
               "換股月": [str(cal[e].date()) for e in x2_months(X)]}
    for nm_, ms_ in (("月換", list(X["MS"])), ("季換", [e for e in X["MS"] if ((cal[e].year * 12 + cal[e].month) - (2005 * 12 + 1)) % 3 == 0])):
        s = x2_sel("合併", ms_)
        res = C.sim_book(s, Wd, 50, w0, w1)
        R["X2"]["頻率%s（描述）" % nm_] = {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}
    # ── X3
    R["X3"] = x3_events(X)
    lc = R["X3"]["H20"]["合併"]["判語"]; l4 = R["X3"]["H20"]["只400"]["判語"]
    pos = lambda s: "測得出（＋）" in s
    R["X3"]["標籤"] = "測得出（＋）" if (pos(lc) and pos(l4)) else ("事後擴母體" if pos(lc) else ("測得出（−）" if "（−）" in lc else "測不出"))
    R["附註"] = [C.IDEA, "出處為公開研究、原文數字未必可重現", "X1、X2、X3 依 P12 全窗判（原文期間是台股期間）", C.SURV]
    return R


def cgo_tv(Wd, j, e, sh):
    """X2 因子（t ＝ e−1）：(TV100, CGO) 或 None。"""
    k = ("cgo", j, e)
    t = e - 1
    v = Wd["valid"][:, j]
    if t < 100 or not v[t] or v[:t + 1].sum() < 100 or not (np.isfinite(sh) and sh > 0):
        return None
    C_ = Wd["CF"][t - 100:t + 1, j]
    vv = v[t - 100:t + 1]
    r = C_[1:] / C_[:-1] - 1
    okr = vv[1:] & vv[:-1] & np.isfinite(r)
    if okr.sum() < 75:
        return None
    tv = float(np.std(r[okr], ddof=1))
    H = Wd["H"][t - 99:t + 1, j].astype(float); L = Wd["L"][t - 99:t + 1, j].astype(float); Cc = Wd["C"][t - 99:t + 1, j]
    P = (H + L + Cc) / 3
    V = np.nan_to_num(Wd["V"][t - 99:t + 1, j].astype(float)) / sh
    V = np.where(vv[1:], np.clip(V, 0, 1), 0.0)
    P = np.where(vv[1:], P, 0.0)
    # w_n ＝ V_{t−n}·Π_{s=1..n}(1 − V_{t−n+s})；陣列由舊到新 ⇒ 反轉
    Vr = V[::-1]; Pr = P[::-1]
    surv = np.r_[1.0, np.cumprod(1 - Vr[:-1])]
    w = Vr * surv
    if w.sum() <= 0:
        return None
    rp = float((Pr * w).sum() / w.sum())
    c = Wd["C"][t, j]
    return tv, (c - rp) / c


def x3_events(X):
    F = X["F"]; Wd = X["Wd"]; cal = X["cal"]; w0, w1 = X["w0"], X["w1"]
    CF, O, valid, pb = Wd["CF"], Wd["O"], Wd["valid"], Wd["pb"]
    ix = Wd["ix"]; SEG = F["SEG"]
    ev = []
    for k, (pe, v, av, fy) in F["revenue"].items():
        t = k.split("#")[0]
        if t not in ix:
            continue
        o = np.argsort(pe); pe2, v2, av2 = pe[o], v[o], av[o]
        for i in range(8, len(v2)):
            if np.isfinite(v2[i]) and v2[i] > np.nanmax(v2[:i]) and av2[i] < len(cal):
                T = int(av2[i])
                if C.key_at(SEG, t, cal[T]) != k:          # 代號重用：只收該段
                    continue
                ev.append((ix[t], T))
    PX = lambda j, i: O[i, j] if (valid[i, j] and np.isfinite(O[i, j]) and O[i, j] > 0) else CF[i, j]
    out = {}
    mem = Wd["mem"]
    for H in (20, 60):
        EW = {}
        rows = {c: [] for c in C.COLS}
        last = {}
        for j, T in sorted(ev, key=lambda x: (x[0], x[1])):
            if not (w0 <= T <= w1 - (H + 1)):
                continue
            if not (mem[T, j] and valid[T, j]):
                continue
            if j in last and T <= last[j] + 20:
                continue
            last[j] = T
            if not valid[T + 1, j] or not (np.isfinite(O[T + 1, j]) and O[T + 1, j] > 0) or pb[T + 1:T + 2 + H, j].any():
                continue
            if T not in EW:
                ok = mem[T + 1] & valid[T + 1] & np.isfinite(O[T + 1]) & (np.nan_to_num(O[T + 1]) > 0) & ~pb[T + 2:T + 2 + H].any(axis=0)
                jj = np.flatnonzero(ok)
                px = np.where(valid[T + 1 + H, jj] & (np.nan_to_num(O[T + 1 + H, jj]) > 0), O[T + 1 + H, jj], CF[T + 1 + H, jj])
                EW[T] = float(np.nanmean(px / O[T + 1, jj] - 1))
            r = PX(j, T + 1 + H) / O[T + 1, j] - 1
            x = r - EW[T]
            pre = CF[T, j] / CF[T - 20, j] - 1 if T >= 20 else np.nan
            for col in C.COLS:
                if col == "只400" and not Wd["m4"][T, j]:
                    continue
                if col == "只500" and not Wd["m5"][T, j]:
                    continue
                rows[col].append((x, T, pre))
        out["H%d" % H] = {}
        for col, rr in rows.items():
            if not rr:
                out["H%d" % H][col] = {"n": 0, "判語": "—"}; continue
            x = np.array([r[0] for r in rr]); T = np.array([r[1] for r in rr]); pre = np.array([r[2] for r in rr])
            s = C.ev_summ(x, T, cal, w0)
            s["判語"] = s.get("判語", "—")
            m = np.isfinite(pre) & (pre >= 0.10)
            s["描述_公告前20日漲≥10%"] = C.ev_summ(x[m], T[m], cal, w0) if m.sum() else {"n": 0}
            out["H%d" % H][col] = s
    out["原始事件數"] = len(ev)
    out["判定"] = "H20 全窗（P12）；H60 描述"
    return out


# ═════════════ A4-4 低週轉 ═════════════
def a44(X, a):
    log("A4-4 低週轉")
    M, Wd, w0, sp = X["ME"], X["Wd"], X["w0"], X["sp"]
    relv = relvol_map(X)

    def sel_of(fam, L, fq, N, pop, mode="low"):
        sel = {}
        for e in rebs_of(X, fq):
            g = M.get(e)
            if g is None:
                continue
            g = g[popmask(g, pop)]
            if fam == "乙":
                g = g[g["rev_hi8"].astype(float).fillna(0) > 0]
            g = g[np.isfinite(g["to%d" % L].astype(float).to_numpy())]
            if mode == "low":
                sel[e] = topn_sel(g, "to%d" % L, N, asc=True)
            elif mode == "high":
                sel[e] = topn_sel(g, "to%d" % L, N, asc=False)
            elif mode == "量":
                g = g.assign(rv=[relv.get((e, j), np.nan) for j in g["j"]])
                sel[e] = topn_sel(g, "rv", N)
            else:
                sel[e] = g["j"].tolist()
        return sel
    R = {"件": "A4-4", "名稱": "低週轉選股", "族": {}}
    for fam in ("甲", "乙"):
        rows = []; grid = []
        for L in (20, 60, 120):
            for fq in ("月", "季", "半年"):
                for N in (10, 20):
                    s = sel_of(fam, L, fq, N, "合併")
                    res = C.sim_book(s, Wd, N, w0, X["w1"])
                    st = C.book_stats(res, w0, sp); st["退化"] = degenerate(st, N)
                    l_ = C.lab(st["年化"], st["回落"], X["BM"]["探索"]["年化"], X["BM"]["探索"]["回落"])
                    rows.append(((L, fq, N), st, l_))
                    grid.append({"L": L, "頻率": fq, "N": N, "探索": st, "探索標籤": l_, "確認（描述）": C.book_stats(res, X["c0"], X["w1"])})
        L, fq, N = pick_cell(rows)
        J = book_judge(X, lambda pop: sel_of(fam, L, fq, N, pop), N, w0, "%s族 TO(%d) %s N%d" % (fam, L, fq, N))
        J.pop("_eq", None)
        fl, lc, l4 = final_from(J)
        D = {"挑中格": {"L": L, "頻率": fq, "N": N}, "判定": J, "標籤": fl, "合併確認": lc, "只400確認": l4, "全表": grid}
        res = C.sim_book(sel_of(fam, L, fq, N, "合併", "high"), Wd, N, w0, X["w1"])
        D["反向臂（周轉最高，描述）"] = {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}
        if fam == "乙":
            res = C.sim_book(sel_of(fam, L, fq, N, "合併", "量"), Wd, N, w0, X["w1"])
            D["同池量放大挑（描述）"] = {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}
        rb = rand_books({"r": {"pools": sel_of(fam, L, fq, N, "合併", "pool"), "N": N, "t0": w0, "item": 4, "arm": 1 if fam == "甲" else 2}},
                        a.reps, a.procs)["r"]
        D["同池隨機"] = {"次數": a.reps, "p_確認": p_of(rb, "確認", J["欄"]["合併"]["確認"]["年化"]), "隨機年化中位_確認": float(rb["確認_年化"].median())}
        # 持股周轉與波動分位
        s = sel_of(fam, L, fq, N, "合併")
        tp = []; vp = []
        for e, js in s.items():
            g = M.get(e)
            if g is None or not js:
                continue
            rto = g["to%d" % L].astype(float).rank(pct=True); rv = g["vol60"].astype(float).rank(pct=True)
            m = g["j"].isin(js).to_numpy()
            tp += list(rto[m].dropna()); vp += list(rv[m].dropna())
        D["持股周轉率分位平均"] = float(np.mean(tp)) if tp else np.nan; D["持股60日波動分位平均"] = float(np.mean(vp)) if vp else np.nan
        R["族"][fam] = D
    R["N"] = 1
    R["附註"] = [C.IDEA, C.NO_EARLY, "乙族池用季營收創 8 季新高：" + C.Q14, "股數 ＝ B2 封面股數＋Yahoo 拆股（P8）", C.SURV]
    return R


# ═════════════ A4-5 強勢類股 ═════════════
def a45_days(X):
    cal = X["cal"]; out = []
    seen = set()
    for i in range(X["w0"], X["w1"] + 1):
        d = cal[i]
        if d.day > 10 and (d.year, d.month) not in seen:
            seen.add((d.year, d.month)); out.append(i)
    return out


def a45(X, a):
    log("A4-5 強勢類股")
    Wd, cal, w0, w1, sp, F = X["Wd"], X["cal"], X["w0"], X["w1"], X["sp"], X["F"]
    CF, valid = Wd["CF"], Wd["valid"]
    cd = cal.values.astype("datetime64[D]").astype(np.int64)
    days = a45_days(X)
    tick = Wd["tick"]
    hi8c = {}
    # 每個換股日：成分、類股、L 報酬、創 8 季新高
    INF = {}
    for t in days:
        ed = int(cd[t - 1])
        for pop in C.COLS:
            m = Wd["m4"][t] if pop == "只400" else (Wd["m5"][t] if pop == "只500" else Wd["mem"][t])
            js = np.flatnonzero(m & valid[t - 1])
            rows = []
            for j in js:
                tk = tick[j]
                gs, gsub = C.sector_at(X["sec"], tk, ed)
                ig = C.GICS.ig_of(gs, gsub)
                if ig is None:
                    continue
                key = (j, t)
                if key not in hi8c:
                    k = C.key_at(F["SEG"], tk, cal[t])
                    q8 = C.q_last(F, "revenue", k, t, 8, edays=int(cd[t])) if k is not None else None
                    hi8c[key] = bool(q8[1][-1] > q8[1][:-1].max()) if q8 is not None else False
                rows.append((j, ig, hi8c[key], tk))
            INF[(t, pop)] = rows

    def build(L, k, how, pop, rng=None):
        sel = {}
        for t in days:
            rows = INF[(t, pop)]
            if t - 1 - L < 0:
                sel[t] = []; continue
            r = {j: CF[t - 1, j] / CF[t - 1 - L, j] - 1 for j, *_ in rows}
            grp = defaultdict(list)
            for j, ig, h, tk in rows:
                if np.isfinite(r[j]):
                    grp[ig].append((j, h, tk))
            st = {ig: np.mean([r[j] for j, _, _ in v]) for ig, v in grp.items() if len(v) >= 5}
            if rng is None:
                top = [ig for ig, _ in sorted(st.items(), key=lambda x: (-x[1], x[0]))[:k]]
            else:
                nm = sorted(st); top = [nm[i] for i in rng.permutation(len(nm))[:k]] if nm else []
            mem = [(j, h, tk) for ig in top for (j, h, tk) in grp[ig]]
            if how == "b":
                mem = [x for x in mem if x[1]]
            if how == "c":
                pool = sorted(j for j, _, _ in mem)
                sel[t] = list(rng.choice(pool, size=min(10, len(pool)), replace=False)) if pool else []
            else:
                sel[t] = [j for j, _, tk in sorted(mem, key=lambda x: (-r[x[0]], x[2]))[:10]]
        return sel
    rows = []; grid = []
    for L in (20, 60, 120):
        for k in (1, 3, 5):
            for how in ("a", "b"):
                s = build(L, k, how, "合併")
                res = C.sim_book(s, Wd, 10, days[0], w1)
                st = C.book_stats(res, days[0], sp); st["退化"] = degenerate(st, 10)
                l_ = C.lab(st["年化"], st["回落"], X["BM"]["探索"]["年化"], X["BM"]["探索"]["回落"])
                rows.append(((L, k, how), st, l_))
                grid.append({"L": L, "k": k, "挑法": how, "探索": st, "探索標籤": l_, "確認（描述）": C.book_stats(res, X["c0"], w1)})
    L, k, how = pick_cell(rows)
    J = book_judge(X, lambda pop: build(L, k, how, pop), 10, days[0], "L%d k%d (%s)" % (L, k, how))
    J.pop("_eq", None)
    fl, lc, l4 = final_from(J)
    R = {"件": "A4-5", "名稱": "強勢類股選股（熱力圖邏輯）", "類股層級": "GICS industry group", "挑中格": {"L": L, "k": k, "挑法": how},
         "判定": J, "標籤": fl, "合併確認": lc, "只400確認": l4, "全表": grid, "N": 1}
    # 假訊號：隨機 k 類股
    _X["a45"] = (build, L, k, how, days)
    D = []
    reps = a.reps
    with Pool(a.procs) as pool:
        D = pool.map(_a45_rand, [(r, "k") for r in range(reps)], chunksize=max(1, reps // (a.procs * 10)))
    cr = np.array([d["確認"]["年化"] for d in D])
    R["隨機挑類股"] = {"次數": reps, "p_確認": float(np.mean(cr >= J["欄"]["合併"]["確認"]["年化"])), "隨機年化中位_確認": float(np.median(cr))}
    with Pool(a.procs) as pool:
        D2 = pool.map(_a45_rand, [(r, "c") for r in range(200)], chunksize=10)
    R["類股內隨機（描述）"] = {"次數": 200, "年化中位_確認": float(np.median([d["確認"]["年化"] for d in D2]))}
    # 集中度
    s = build(L, k, how, "合併")
    conc = []
    igof = {}
    for t, js in s.items():
        if not js:
            continue
        ed = int(cd[t - 1])
        c = Counter(C.GICS.ig_of(*C.sector_at(X["sec"], tick[j], ed)) for j in js)
        conc.append(max(c.values()) / len(js))
        for ig_ in c:
            igof[ig_] = igof.get(ig_, 0) + 1
    R["同類股占比最大值_平均"] = float(np.mean(conc)) if conc else np.nan
    R["最常入選類股前5"] = sorted(igof.items(), key=lambda x: -x[1])[:5]
    R["附註"] = [C.IDEA, C.NO_EARLY, "(b) 用季營收創 8 季新高：" + C.Q14, "類股 ＝ GICS industry group（seq319 Q8；對照率見 GICS 對照）", C.SURV]
    return R


def _a45_rand(args):
    r, kind = args
    build, L, k, how, days = _X["a45"]
    X = _X["ctx"]
    rng = np.random.default_rng([20261007, 5, 1 if kind == "k" else 2, r])
    s = build(L, k, how if kind == "k" else "c", "合併", rng=rng)
    res = C.sim_book(s, X["Wd"], 10, days[0], X["w1"])
    return {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}


# ═════════════ A4-6 產業營收加速（季版）═════════════
FIN_IG = ("Banks", "Financial Services", "Insurance")
RMON = {"季": (1, 4, 7, 10), "半年": (1, 7), "年": (1,)}
EXX = {"E2": 0.20, "E3": 0.30}


def cq_index(dday):
    """日（int days）⇒ 曆季序號（最近的曆季末，±45 天）。"""
    d = pd.Timestamp(np.datetime64(int(dday), "D"))
    qe = [pd.Timestamp(d.year - 1, 12, 31), pd.Timestamp(d.year, 3, 31), pd.Timestamp(d.year, 6, 30), pd.Timestamp(d.year, 9, 30), pd.Timestamp(d.year, 12, 31)]
    best = min(qe, key=lambda x: abs((x - d).days))
    if abs((best - d).days) > 45:
        return None
    return best.year * 4 + (best.month - 1) // 3


def a46_tables(X):
    """每個季月初 e、每欄：產業 A1／A2／A3、公司數；產業成員（市值、創 8 季新高）。"""
    F, Wd, cal = X["F"], X["Wd"], X["cal"]
    cd = cal.values.astype("datetime64[D]").astype(np.int64)
    QE = [e for e in X["MS"] if cal[e].month in (1, 4, 7, 10)]
    tick = Wd["tick"]
    # 公司 × 曆季 ⇒ (值, 可用日)
    CQ = {}
    for k, (pe, v, av, fy) in F["revenue"].items():
        d = {}
        for p_, v_, a_ in zip(pe, v, av):
            q = cq_index(p_)
            if q is None or not np.isfinite(v_) or v_ <= 0:
                continue
            if q not in d:
                d[q] = (v_, a_)
        CQ[k] = d
    T = {}
    for e in QE:
        d = cal[e]
        target = d - pd.Timedelta(days=90)
        qs = target.year * 4 + (target.month - 1) // 3
        # 期末日 ≤ e − 90 的最近曆季：qs 這一季的季末若 > target ⇒ 往前一季
        qend = pd.Timestamp(qs // 4, (qs % 4) * 3 + 3, 1) + pd.offsets.MonthEnd(0)
        Qs = qs if qend <= target else qs - 1
        ed1 = int(cd[e])
        for pop in C.COLS:
            m = Wd["m4"][e] if pop == "只400" else (Wd["m5"][e] if pop == "只500" else Wd["mem"][e])
            js = np.flatnonzero(m)
            byig = defaultdict(list)
            for j in js:
                tk = tick[j]
                ig = C.GICS.ig_of(*C.sector_at(X["sec"], tk, ed1))
                if ig is None or ig in FIN_IG:
                    continue
                k = C.key_at(F["SEG"], tk, cal[e])
                byig[ig].append((j, k))
            A = {}
            for ig, mem in byig.items():
                def numden(q):
                    n_ = d_ = 0.0; c_ = 0
                    for j, k in mem:
                        x = CQ.get(k, {})
                        a1 = x.get(q); b1 = x.get(q - 4)
                        if a1 and b1 and a1[1] <= e and b1[1] <= e:
                            n_ += a1[0]; d_ += b1[0]; c_ += 1
                    return n_, d_, c_
                nd = {q: numden(q) for q in range(Qs - 4, Qs + 1)}
                n0, d0, c0 = nd[Qs]
                if c0 < 5 or d0 <= 0:
                    continue
                A1 = n0 / d0 - 1
                s4n = sum(nd[q][0] for q in range(Qs - 3, Qs + 1)); s4d = sum(nd[q][1] for q in range(Qs - 3, Qs + 1))
                A2 = A1 - (s4n / s4d - 1) if s4d > 0 else np.nan
                n1, d1, _ = nd[Qs - 1]
                A3 = A1 - (n1 / d1 - 1) if d1 > 0 else np.nan
                # 前一季的 A2（E1 用）
                p4n = sum(nd[q][0] for q in range(Qs - 4, Qs)); p4d = sum(nd[q][1] for q in range(Qs - 4, Qs))
                A1p = n1 / d1 - 1 if d1 > 0 else np.nan
                A2p = A1p - (p4n / p4d - 1) if p4d > 0 and np.isfinite(A1p) else np.nan
                A[ig] = {"A1": A1, "A2": A2, "A3": A3, "A2prev": A2p, "公司數": c0}
            T[(e, pop)] = {"A": A, "Q": Qs}
    return T, QE


def a46_members(X, e, pop):
    """產業成員（e 當天在該欄母體、市值有限 ＞ 0）依市值排序；創 8 季新高旗標。"""
    key = ("a46m", e, pop)
    if key in _X:
        return _X[key]
    M = X["ME"].get(e)
    out = defaultdict(list)
    if M is not None:
        g = M[popmask(M, pop)]
        g = g[np.isfinite(g["mcap"].astype(float).to_numpy()) & (g["mcap"].astype(float).to_numpy() > 0)]
        for j, ig, mc, h, tk in zip(g["j"], g["ig"], g["mcap"].astype(float), g["rev_hi8"].astype(float).fillna(0), g["t"]):
            if ig is None or ig in FIN_IG:
                continue
            out[ig].append((-mc, tk, int(j), h > 0))
    res = {}
    for ig, v in out.items():
        v.sort()
        o = [j for _, _, j, _ in v]; h = [j for _, _, j, hh in v if hh]
        res[ig] = {"S1": o[:20], "S2": o[:3], "S3": h[:10]}
    _X[key] = res
    return res


def sim_ind(X, cfg, pop, rng=None, order="top", trades_out=None):
    """台股 researchIndRev_prereg.sim_ind 同式（美股：無漲跌停、斷點／下市 G11／G12）。"""
    Wd, cal, w1 = X["Wd"], X["cal"], X["w1"]
    T, QE = X["a46T"]
    O, CF, valid, last, brk = Wd["O"], Wd["CF"], Wd["valid"], Wd["last"], Wd["pb"]
    A, K, S, R_, E = cfg
    t0 = QE[0]
    reb = [e for e in QE if cal[e].month in RMON[R_]]
    rebset = set(reb); qset = set(QE)
    n = len(cal)
    eq = np.ones(n); cash = 1.0; pos = {}; pend = set(); pind = {}; pbuy = {}
    npos = np.zeros(n, np.int16); cashf = np.zeros(n); costd = np.zeros(n); buyd = np.zeros(n)
    held = {}; ban = {}; exit_next = set(); episodes = []; cnt = Counter(); picks = {}
    X_ = EXX.get(E)
    for t in range(t0, w1 + 1):
        for j in list(pos):
            u, amt, b, hi = pos[j]
            if (t > b and brk[t, j]) or t > last[j]:
                px = CF[t - 1, j] if t <= last[j] else CF[last[j], j]
                pos.pop(j); pend.discard(j); pind.pop(j, None); pbuy.pop(j, None)
                cash += u * px - amt * C.COST; costd[t] += amt * C.COST; cnt["斷點或下市結清"] += 1
                if trades_out is not None:
                    trades_out.append((j, b, t - 1, px / (amt / u) - 1, px / hi - 1 if hi > 0 else np.nan, "斷點"))
        ex = []
        if E in EXX:
            ex = sorted(i for i in exit_next if i in held)
        elif E == "E1" and t in qset:
            Ai = T[(t, pop)]["A"]
            for i in sorted(held):
                v = Ai.get(i)
                if v is not None and np.isfinite(v["A2"]) and np.isfinite(v["A2prev"]) and v["A2"] < 0 and v["A2prev"] > 0:
                    ex.append(i)
        exit_next = set()
        for i in ex:
            h = held.pop(i)
            basket = sorted(j for j in pos if pind.get(j) == i)
            pend |= set(basket)
            episodes.append({"ind": i, "start": h["start"], "end": t, "why": E})
            ban[i] = {"E": E, "I": h["I"], "peak": h["peak"], "basket": basket}
            cnt["E出場"] += 1
        sel = None
        if t in rebset:
            Ai = T[(t, pop)]["A"]
            nm = sorted(i for i, v in Ai.items() if np.isfinite(v[A]))
            if order == "random":
                rk = [nm[k] for k in rng.permutation(len(nm))]
            else:
                rk = sorted(nm, key=lambda i: ((-Ai[i][A]) if order == "top" else Ai[i][A], i))
            if not rk:
                cnt["無可排名"] += 1
            else:
                chosen = []
                for i in rk:
                    if i in ban:
                        b = ban[i]
                        hold_ = (np.isfinite(Ai[i]["A2"]) and Ai[i]["A2"] < 0) if b["E"] == "E1" else (b["I"] <= (1 - EXX[b["E"]]) * b["peak"])
                        if hold_:
                            cnt["ban_skip"] += 1; continue
                        del ban[i]
                    chosen.append(i)
                    if len(chosen) == K:
                        break
                PK = a46_members(X, t, pop)
                sel = []; div = {}; sind = {}
                for i in chosen:
                    lst = PK.get(i, {}).get(S, [])
                    if not lst:
                        cnt["產業0檔"] += 1
                    n_i = 10 if S == "S3" else len(lst)
                    for j in lst:
                        sel.append(j); div[j] = K * n_i; sind[j] = i
                pend = (pend | (set(pos) - set(sel))) - set(sel)
                for i in list(held):
                    if i not in chosen:
                        h = held.pop(i); episodes.append({"ind": i, "start": h["start"], "end": t, "why": "換股"})
                for i in chosen:
                    if i not in held:
                        held[i] = {"start": t, "I": 1.0, "peak": -np.inf}
                for j in sel:
                    if j in pos:
                        pind[j] = sind[j]
                picks[t] = list(chosen)
        for j in sorted(pend):
            if j not in pos:
                pend.discard(j); continue
            o_t = O[t, j]
            if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                cnt["sell_delayed"] += 1; continue
            u, amt, b, hi = pos.pop(j)
            cash += u * o_t - amt * C.COST; costd[t] += amt * C.COST; pend.discard(j); pind.pop(j, None); pbuy.pop(j, None)
            if trades_out is not None:
                trades_out.append((j, b, t, o_t / (amt / u) - 1, o_t / max(hi, o_t) - 1, "賣"))
        if sel is not None:
            for j in [j for j in sel if j not in pos]:
                o_t = O[t, j]
                if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                    cnt["buy_halt"] += 1; continue
                amt = min(eq[t - 1] / div[j], cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[j] = [amt / o_t, amt, t, o_t]; pind[j] = sind[j]; pbuy[j] = (t, o_t); buyd[t] += amt
        hv = 0.0
        for j, p in pos.items():
            c = CF[t, j]; hv += p[0] * c
            if c > p[3]:
                p[3] = c
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
        if X_ is not None:
            grp = defaultdict(list)
            for j in pos:
                if j in pind:
                    grp[pind[j]].append(j)
            for i, h in held.items():
                rs = []
                for j in grp.get(i, []):
                    bt, bp = pbuy[j]; ref = bp if bt == t else CF[t - 1, j]; ct = CF[t, j]
                    if np.isfinite(ct) and np.isfinite(ref) and ref > 0:
                        rs.append(ct / ref - 1)
                if rs:
                    h["I"] *= 1 + float(np.mean(rs)); h["peak"] = max(h["peak"], h["I"])
                    if h["I"] <= (1 - X_) * h["peak"]:
                        exit_next.add(i)
            for i, b in ban.items():
                rs = [CF[t, j] / CF[t - 1, j] - 1 for j in b["basket"] if np.isfinite(CF[t, j]) and np.isfinite(CF[t - 1, j]) and CF[t - 1, j] > 0]
                if rs:
                    b["I"] *= 1 + float(np.mean(rs))
    eq[w1 + 1:] = eq[w1]
    for i, h in held.items():
        episodes.append({"ind": i, "start": h["start"], "end": None, "why": "窗尾"})
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": dict(cnt), "episodes": episodes, "picks": picks, "t0": t0,
            "open": list(pos)}


def ind_stats(res, a, b, w1, trades=None):
    st = C.book_stats(res, a, b)
    ep = [e for e in res["episodes"] if a <= e["start"] <= b]
    hd = [((e["end"] if e["end"] is not None else w1 + 1) - e["start"]) for e in ep]
    st.update({"產業持有段數": len(ep), "產業平均持有天數": float(np.mean(hd)) if hd else np.nan,
               "E出場次數": sum(1 for e in ep if e["why"] in ("E1", "E2", "E3"))})
    if trades is not None:
        st.update(C.hold_stats([x for x in trades if a <= x[1] <= b], b))
    return st


def _a46_cell(cfg):
    X = _X["ctx"]
    res = sim_ind(X, cfg, "合併")
    st = ind_stats(res, res["t0"], X["sp"], X["w1"])
    cf = ind_stats(res, X["c0"], X["w1"], X["w1"])
    return cfg, st, cf


def _a46_rand(args):
    r, cfg = args
    X = _X["ctx"]
    rng = np.random.default_rng([20261007, 6, r])
    res = sim_ind(X, cfg, "合併", rng=rng, order="random")
    return {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}


def a46(X, a):
    log("A4-6 產業營收加速（季版）")
    X["a46T"] = a46_tables(X)
    T, QE = X["a46T"]
    cells = [(A_, K, S, R_, E) for A_ in ("A1", "A2", "A3") for K in (1, 3) for S in ("S1", "S2", "S3") for R_ in ("季", "半年", "年") for E in ("E0", "E1", "E2", "E3")]
    with Pool(a.procs) as pool:
        out = pool.map(_a46_cell, cells, chunksize=4)
    rows = []; grid = []
    for cfg, st, cf in out:
        st["退化"] = bool(st["平均持股"] < 3 or st["現金比例"] > 0.30)
        l_ = C.lab(st["年化"], st["回落"], X["BM"]["探索"]["年化"], X["BM"]["探索"]["回落"])
        rows.append((cfg, st, l_))
        grid.append({"A": cfg[0], "K": cfg[1], "S": cfg[2], "R": cfg[3], "E": cfg[4], "探索": st, "探索標籤": l_, "確認（描述）": cf})
    ch = pick_cell(rows)
    J = {"格": "%s K%d %s %s %s" % ch, "欄": {}}
    for pop in C.COLS:
        tr = []
        res = sim_ind(X, ch, pop, trades_out=tr)
        Rr = {nm: ind_stats(res, a_, b_, X["w1"], trades=tr) for nm, (a_, b_) in X["segs"].items()}
        for nm in Rr:
            Rr[nm]["標籤"] = C.lab(Rr[nm]["年化"], Rr[nm]["回落"], X["BM"][nm]["年化"], X["BM"][nm]["回落"])
        Rr["窗尾仍持有（檔）"] = len(res["open"]); Rr["計數"] = res["cnt"]
        if pop == "合併":
            Rr["挑中產業次數"] = Counter(i for v in res["picks"].values() for i in v).most_common(10)
        J["欄"][pop] = Rr
    fl, lc, l4 = final_from(J)
    R = {"件": "A4-6", "名稱": "產業營收加速（季版）", "類股層級": "GICS industry group（排除 Banks、Financial Services、Insurance）",
         "挑中格": dict(zip(("A", "K", "S", "R", "E"), ch)), "判定": J, "標籤": fl, "合併確認": lc, "只400確認": l4, "N": 1}
    R["全表"] = grid
    # 同 A×K×S×R 下 E 對照
    R["E對照（同A×K×S×R，合併）"] = {g["E"]: {"探索": g["探索"], "確認": g["確認（描述）"]} for g in grid
                                 if (g["A"], g["K"], g["S"], g["R"]) == ch[:4]}
    # 反向臂、隨機產業
    res = sim_ind(X, ch, "合併", order="bottom")
    R["反向臂（描述）"] = {nm: C.seg_metrics(res["eq"], a_, b_) for nm, (a_, b_) in X["segs"].items()}
    with Pool(a.procs) as pool:
        D = pool.map(_a46_rand, [(r, ch) for r in range(a.reps)], chunksize=max(1, a.reps // (a.procs * 10)))
    cr = np.array([d["確認"]["年化"] for d in D])
    R["隨機挑產業"] = {"次數": a.reps, "p_確認": float(np.mean(cr >= J["欄"]["合併"]["確認"]["年化"])), "隨機年化中位_確認": float(np.median(cr))}
    # 可排名產業數
    R["可排名產業數（合併，每季中位）"] = float(np.median([len(T[(e, "合併")]["A"]) for e in QE]))
    R["附註"] = [C.IDEA, C.NO_EARLY, "台股兩件後續已不合格結案：產業營收落後 seq2、產業落後買賣點 seq2（裁定 seq315、317）",
               "S3 用季營收創 8 季新高：" + C.Q14, "類股 ＝ GICS industry group（seq319 Q8）", C.SURV]
    return R


# ═════════════ A4-7 事件型兩件 ═════════════
def a47_buyback(X, x_pct=0.10):
    F, Wd, cal, w0, w1 = X["F"], X["Wd"], X["cal"], X["w0"], X["w1"]
    cd = cal.values.astype("datetime64[D]").astype(np.int64)
    ix = Wd["ix"]; SEG = F["SEG"]
    rows = []
    for k, (pe, v, av, fy) in F["buyback"].items():
        t = k.split("#")[0]
        if t not in ix:
            continue
        j = ix[t]
        for p_, v_, a_ in zip(pe, v, av):
            if a_ >= len(cal) or a_ < 1 or not np.isfinite(v_):
                continue
            if C.key_at(SEG, t, cal[a_]) != k:
                continue
            q = cq_index(p_)
            if q is None:
                continue
            ed = int(cd[a_])
            sh = C.shares_at(F, k, a_, ed)
            rc = Wd["RCu"][:a_, j]
            vv = np.flatnonzero(np.isfinite(rc))
            if not len(vv) or not np.isfinite(sh):
                continue
            mc = sh * rc[vv[-1]]
            if not mc > 0:
                continue
            rows.append((j, int(a_), q, v_ / mc))
    D = pd.DataFrame(rows, columns=["j", "T", "q", "r"])
    thr = D.groupby("q")["r"].quantile(1 - x_pct)
    D["thr"] = D["q"].map(lambda q: thr.get(q - 1, np.nan))
    E = D[(D["r"] > 0) & np.isfinite(D["thr"]) & (D["r"] >= D["thr"])]
    return [(int(j), int(T)) for j, T in zip(E["j"], E["T"])], {"申報筆數": len(D), "事件（門檻後）": len(E)}


def a47_removals(X, excl_promo=False):
    Wd, cal = X["Wd"], X["cal"]; ix = Wd["ix"]
    out = []
    ch5 = pd.read_csv(C.U._p("membership", "changes.csv"), dtype=str, keep_default_na=False)
    ch4 = pd.read_csv(C.U._p("membership_sp400", "changes.csv"), dtype=str, keep_default_na=False)
    add5 = set(zip(ch5["date"], ch5["added_ticker"]))
    for idx, ch in (("sp500", ch5), ("sp400", ch4)):
        for d, t in zip(ch["date"], ch["removed_ticker"]):
            if not t or t not in ix:
                continue
            dt = pd.Timestamp(d)
            if not (cal[0] <= dt <= cal[-1]):
                continue
            if excl_promo and idx == "sp400" and (d, t) in add5:
                continue
            T = int(cal.searchsorted(dt, side="right")) - 1
            out.append((ix[t], T, idx))
    return out


def ev_layer(X, events, col_of, Hs=(5, 20, 60, 120)):
    """單筆層（I16）：同檔 20 日只取第一筆；R_H、基準②（同 T、同 H、同十分位）。col_of(j, T, tag) ⇒ 欄集合。"""
    Wd, cal, w0, w1, sp = X["Wd"], X["cal"], X["w0"], X["w1"], X["sp"]
    CF, O, valid, pb, mem = Wd["CF"], Wd["O"], Wd["valid"], Wd["pb"], Wd["mem"]
    last = {}; keep = []
    for ev in sorted(events, key=lambda x: (x[0], x[1])):
        j, T = ev[0], ev[1]
        if not (w0 <= T <= w1 - 1):
            continue
        if j in last and T <= last[j] + 20:
            continue
        last[j] = T
        if not valid[T + 1, j] or not (np.isfinite(O[T + 1, j]) and O[T + 1, j] > 0):
            continue
        keep.append(ev)
    out = {}
    bcache = {}
    for H in Hs:
        res = defaultdict(list)
        for ev in keep:
            j, T = ev[0], ev[1]
            x = min(T + H, w1)
            if pb[T + 1:x + 1, j].any() or T < 20:
                continue
            r = CF[x, j] / O[T + 1, j] - 1
            key = (T, H)
            if key not in bcache:
                ok = mem[T] & valid[T + 1] & (np.nan_to_num(O[T + 1]) > 0) & ~pb[T + 1:x + 1].any(axis=0)
                jj = np.flatnonzero(ok)
                p20 = CF[T, jj] / CF[T - 20, jj] - 1
                rr = CF[x, jj] / O[T + 1, jj] - 1
                m = np.isfinite(p20) & np.isfinite(rr)
                jj, p20, rr = jj[m], p20[m], rr[m]
                dec = np.minimum((pd.Series(p20).rank(method="first").to_numpy() - 1) * 10 // max(len(jj), 1), 9).astype(int) if len(jj) else np.zeros(0, int)
                bcache[key] = ({int(x): (i, int(d)) for i, (x, d) in enumerate(zip(jj, dec))}, dec, rr)
            dmap, dec, rr = bcache[key]
            if j not in dmap:
                continue
            ij, dj = dmap[j]
            sel = (dec == dj)
            cntd = int(sel.sum()) - 1
            if cntd <= 0:
                continue
            ybar = (float(rr[sel].sum()) - float(rr[ij])) / cntd
            xx = r - ybar - C.COST
            seg = "探索" if T <= sp else "確認"
            for col in col_of(*ev):
                res[(col, seg)].append((xx, T))
                res[(col, "全窗")].append((xx, T))
        out["H%d" % H] = {"%s|%s" % k: C.ev_summ([v[0] for v in vv], [v[1] for v in vv], cal, w0) for k, vv in res.items()}
    return out, keep


def a47_portfolio(X, keep, col_of, a, tag):
    Wd, cal, w0, w1, sp, c0 = X["Wd"], X["cal"], X["w0"], X["w1"], X["sp"], X["c0"]
    arms = {}
    for H in (20, 60, 120):
        for pop in C.COLS:
            rr = []
            for ev in keep:
                j, T = ev[0], ev[1]
                if pop not in col_of(*ev):
                    continue
                x = min(T + H, w1)
                if C.crosses(Wd["pb"], j, T + 1, x):
                    continue
                rr.append((j, T + 1, x, Wd["CF"][x, j] / Wd["O"][T + 1, j] - 1, str(cal[T])[:7]))
            arms[(tag, H, pop)] = {"sig": C.mk_sig(rr), "N": 10, "segs": X["segs"], "cost": C.COST, "audit": False}
    D = C.run_slots(arms, Wd, a.procs, a.seeds)
    S = {k: C.slot_summary(D[k], X["segs"], X["BM"]) for k in arms}
    yrs_exp = (sp - w0 + 1) / 252
    rows = []
    for H in (20, 60, 120):
        sig = arms[(tag, H, "合併")]["sig"]
        ne = int(((sig["entry_pos"] >= w0) & (sig["entry_pos"] <= sp)).sum())
        st = {"比值": S[(tag, H, "合併")]["探索"]["比值"], "年化": S[(tag, H, "合併")]["探索"]["年化中位"], "退化": ne / yrs_exp < 10}
        rows.append((H, st, S[(tag, H, "合併")]["探索"]["標籤"]))
    ch = pick_cell(rows)
    ny = {}
    for H in (20, 60, 120):
        sg = arms[(tag, H, "合併")]["sig"]
        ny[H] = int(((sg["entry_pos"] >= w0) & (sg["entry_pos"] <= sp)).sum()) / yrs_exp
    out = {"全表": {"H%d|%s" % (H, pop): S[(tag, H, pop)] for (_, H, pop) in arms}, "探索年均事件（合併）": ny}
    if ch is None:
        out["標籤"] = "不可判定（探索段年均事件 ＜ 10）"
        return out, None
    lc = S[(tag, ch, "合併")]["確認"]["標籤"]; l4 = S[(tag, ch, "只400")]["確認"]["標籤"]
    # 只400 事件太少 ⇒ 依構造不可判定（K7）
    sig4 = arms[(tag, ch, "只400")]["sig"]
    ne4 = int(((sig4["entry_pos"] >= w0) & (sig4["entry_pos"] <= sp)).sum()) / yrs_exp
    out.update({"挑中H": ch, "合併確認": lc, "只400確認": l4, "只400探索年均事件": ne4,
                "標籤": C.final_label(lc, l4) if ne4 >= 10 else ("事後擴母體" if lc == "合格" else C.final_label(lc, "—")) + "（只 S&P 400 年均事件 ＜ 10）"})
    return out, ch


def a47(X, a):
    log("A4-7 事件型兩件")
    Wd = X["Wd"]
    R = {"件": "A4-7", "名稱": "事件型兩件（庫藏股代理、指數成分剔除）", "N": 2}
    colf = lambda j, T: [c for c in C.COLS if c == "合併" or (c == "只400" and Wd["m4"][T, j]) or (c == "只500" and Wd["m5"][T, j])]
    ev, info = a47_buyback(X, 0.10)
    single, keep = ev_layer(X, ev, colf)
    port, ch = a47_portfolio(X, keep, colf, a, "BB")
    R["庫藏股代理（每季前10%）"] = {"事件": info, "保留": len(keep), "單筆層（描述）": single, "組合層": port}
    # 敏感度 5%、20%（描述、只跑挑中 H）
    sens = {}
    for xp in (0.05, 0.20):
        ev2, info2 = a47_buyback(X, xp)
        _, keep2 = ev_layer(X, ev2, colf, Hs=(20,))
        if ch is not None:
            p2, _ = a47_portfolio(X, keep2, colf, a, "BB%.2f" % xp)
            sens["前%d%%" % int(xp * 100)] = {"事件": info2, "挑中H%d" % ch: {k: v for k, v in p2["全表"].items() if k.startswith("H%d|" % ch)}}
    R["庫藏股代理"] = {"敏感度（描述、⛔ 不計 N、不改挑）": sens}
    rm = a47_removals(X)
    colr = lambda j, T, idx: ["合併", "只400" if idx == "sp400" else "只500"]
    single, keep = ev_layer(X, rm, colr)
    yrs = (X["w1"] - X["w0"] + 1) / 252
    port, _ = a47_portfolio(X, keep, colr, a, "RM")
    R["成分剔除"] = {"剔除事件（窗內、有價）": len(keep), "年均（合併）": len(keep) / yrs, "單筆層（描述）": single, "組合層": port}
    rm2 = a47_removals(X, excl_promo=True)
    s2, k2 = ev_layer(X, rm2, colr, Hs=(20, 60))
    R["成分剔除"]["排除同日升級 S&P 500 的版本（描述）"] = {"事件": len(k2), "單筆層": s2}
    R["附註"] = [C.IDEA, C.NO_EARLY, "庫藏股 ＝ 季買回 ÷ 市值（代理，現金流量表、無逐筆事件；目的 1／3 分類做不到 ⇒ 退化）", "成分剔除公告日臂拿掉（資料沒有公告日）", C.SURV]
    return R


# ═════════════ A4-9 年線戰法基本面季版 ═════════════
def a49(X, a):
    log("A4-9 年線戰法基本面季版")
    Wd, cal, w0, w1, sp, F = X["Wd"], X["cal"], X["w0"], X["w1"], X["sp"], X["F"]
    cd = cal.values.astype("datetime64[D]").astype(np.int64)
    ix = Wd["ix"]; CF, O, valid = Wd["CF"], Wd["O"], Wd["valid"]
    sigs = []; acc = Counter()
    for t, lst in X["W2c"].items():
        if t not in ix:
            continue
        j = ix[t]
        for s, r in lst:
            acc["候選"] += 1
            k = C.key_at(F["SEG"], t, cal[s])
            if k is None:
                continue
            y = C.yoy_at(F, "revenue", k, s, int(cd[s]))
            qn = C.q_last(F, "net_income", k, s, 2, edays=int(cd[s]))
            turn = bool(qn[1][1] > 0 and qn[1][0] <= 0) if qn is not None else False
            if (np.isfinite(y) and y > 0) or turn:
                acc["成立"] += 1; sigs.append((j, r))
    madn = {}
    for jj in set(j for j, _ in sigs):
        vb = np.flatnonzero(valid[:, jj]); cb = Wd["C"][vb, jj]
        madn[jj] = {}
        for L in (10, 20, 60):
            m = pd.Series(cb).rolling(L, min_periods=L).mean().to_numpy()
            x = np.zeros(len(vb), bool)
            with np.errstate(invalid="ignore"):
                x[1:] = (cb[:-1] >= m[:-1]) & (cb[1:] < m[1:])
            madn[jj][L] = vb[x]
    arms = {}; tails = {}
    for L in (10, 20, 60):
        for pop in C.COLS:
            rows = {"main": [], **{"fix%d" % H: [] for H in C.FIXH}}
            for j, r in sigs:
                if pop == "只400" and not Wd["m4"][r, j]:
                    continue
                if pop == "只500" and not Wd["m5"][r, j]:
                    continue
                e = r + 1
                if e > w1 or not (valid[e, j] and np.isfinite(O[e, j]) and O[e, j] > 0):
                    continue
                xs = madn[j][L]; xs = xs[xs >= e]
                if len(xs) and xs[0] + 1 <= w1:
                    x = int(xs[0]) + 1; ox = O[x, j]; g = (ox if np.isfinite(ox) and ox > 0 else CF[x, j]) / O[e, j] - 1
                else:
                    x = w1; g = CF[w1, j] / O[e, j] - 1
                mo = str(cal[r])[:7]
                if not C.crosses(Wd["pb"], j, e, x):
                    rows["main"].append((j, e, x, g, mo))
                for H in C.FIXH:
                    xh = min(e + H - 1, w1)
                    if not C.crosses(Wd["pb"], j, e, xh):
                        rows["fix%d" % H].append((j, e, xh, CF[xh, j] / O[e, j] - 1, mo))
            for arm, rr in rows.items():
                if arm != "main" and (pop == "只500" or L != 0):
                    pass
                arms[(L, pop, arm)] = {"sig": C.mk_sig(rr), "N": 10, "segs": X["segs"], "cost": C.COST, "audit": arm == "main"}
            # 段尾未出場（探索段，事件為單位）
            ent = [(j, r + 1) for j, r in sigs if w0 <= r + 1 <= sp]
            if pop == "合併":
                tl = 0
                for j, e in ent:
                    xs = madn[j][L]; xs = xs[xs >= e]
                    tl += int(not (len(xs) and xs[0] + 1 <= sp))
                tails[L] = tl / max(len(ent), 1)
    # 只保留需要的臂（固定天數只在挑中格後跑 ⇒ 先跑主臂）
    main_arms = {k: v for k, v in arms.items() if k[2] == "main"}
    D = C.run_slots(main_arms, Wd, a.procs, a.seeds)
    S = {k: C.slot_summary(D[k], X["segs"], X["BM"]) for k in main_arms}
    yrs = (w1 - w0 + 1) / 252
    rows = []
    for L in (10, 20, 60):
        n_ = len(main_arms[(L, "合併", "main")]["sig"])
        st = {"比值": S[(L, "合併", "main")]["探索"]["比值"], "年化": S[(L, "合併", "main")]["探索"]["年化中位"],
              "退化": bool(n_ < 200 or n_ / yrs < 10 or tails[L] > 0.5)}
        rows.append((L, st, S[(L, "合併", "main")]["探索"]["標籤"]))
    ch = pick_cell(rows)
    R = {"件": "A4-9", "名稱": "年線戰法基本面季版", "訊號": dict(acc), "N": 1, "探索段段尾未出場比例": tails,
         "全表": {"MA%d|%s" % (L, p): S[(L, p, "main")] for (L, p, _) in main_arms}}
    if ch is None:
        R["標籤"] = "不可判定"; return R
    extra = {}
    for pop in C.COLS:
        for H in C.FIXH:
            extra[(ch, pop, "fix%d" % H)] = arms[(ch, pop, "fix%d" % H)]
        if pop != "只500":
            for cs_ in C.COST_SENS:
                extra[(ch, pop, "cost%g" % cs_)] = dict(arms[(ch, pop, "main")], cost=cs_, audit=False)
            f50 = Wd["pb"] | Wd["f50"]
            sg = arms[(ch, pop, "main")]["sig"]
            keepm = [not C.crosses(f50, int(s_), int(e_), int(x_)) for s_, e_, x_ in zip(sg["sid"], sg["entry_pos"], sg["xpos_" + C.RULE])]
            extra[(ch, pop, "ret50")] = dict(arms[(ch, pop, "main")], sig=sg[keepm].reset_index(drop=True), audit=False)
    D2 = C.run_slots(extra, Wd, a.procs, a.seeds)
    S2 = {k: C.slot_summary(D2[k], X["segs"], X["BM"]) for k in extra}
    lc = S[(ch, "合併", "main")]["確認"]["標籤"]; l4 = S[(ch, "只400", "main")]["確認"]["標籤"]
    R.update({"挑中格": "跌破 MA%d" % ch, "合併確認": lc, "只400確認": l4, "標籤": C.final_label(lc, l4),
              "挑中格描述臂": {"%s|%s" % (k[1], k[2]): v for k, v in S2.items()},
              "持有分佈（合併、種子102000）": holds_from(D[(ch, "合併", "main")], main_arms[(ch, "合併", "main")]["sig"], Wd, X)})
    R["附註"] = [C.IDEA, C.NO_EARLY, "兩條「或」都留（季營收年增 ＞ 0 或季淨利由負轉正；seq319 Q7）", C.SURV]
    return R


def holds_from(df, sig, Wd, X):
    """種子 102000：持有天數分佈、離頂多近、段尾仍持有（G7）。holds ＝ (sid, 買日, 賣日)。"""
    r0 = df[df["seed"] == C.SEED0]
    if not len(r0) or "holds" not in r0.columns:
        return {}
    plan = {(int(s), int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_" + C.RULE])}
    CF, O = Wd["CF"], Wd["O"]
    out = {}
    for nm, (a_, b_) in X["segs"].items():
        tr = []
        for sid, bt, st in r0["holds"].iloc[0]:
            if not (a_ <= bt <= b_):
                continue
            x = st
            px = O[x, sid] if (x == plan.get((sid, bt)) and x < b_ and np.isfinite(O[x, sid]) and O[x, sid] > 0) else CF[x, sid]
            hi = np.nanmax(CF[bt:x + 1, sid])
            tr.append((sid, bt, x, px / O[bt, sid] - 1, px / hi - 1 if hi > 0 else np.nan, ""))
        h = C.hold_stats(tr, b_)
        h["段尾仍持有（筆，計畫出場在段後）"] = int(sum(1 for (sid, bt, st) in r0["holds"].iloc[0] if a_ <= bt <= b_ and plan.get((sid, bt), 0) > b_))
        h["窗尾仍持有（筆，2026-09-30 收盤結算）"] = int(sum(1 for (sid, bt, st) in r0["holds"].iloc[0]
                                                   if a_ <= bt <= b_ and st == X["w1"] and plan.get((sid, bt)) == X["w1"]))
        out[nm] = h
    return out


# ═════════════ A4-12 十一票 ═════════════
def a412(X, a):
    log("A4-12 十一票")
    M, Wd, w0, sp = X["ME"], X["Wd"], X["w0"], X["sp"]

    def score_df(g, L, which="all"):
        b = lambda c: g[c].astype(float).fillna(0).to_numpy() > 0
        vr = g["vr20_250"].astype(float)
        v9 = (vr.rank(pct=True, ascending=False) <= 0.20).to_numpy() & np.isfinite(vr.to_numpy())
        votes = {"①": b("rev_hi8"), "②": g["rev_yoy"].astype(float).fillna(-9).to_numpy() >= 0.15, "③": b("hi250_L%d" % L), "④": b("stack"),
                 "⑤": b("strong"), "⑥": b("td9_L%d" % L), "⑦": b("rsi_L%d" % L), "⑧": b("s06_L%d" % L), "⑨": v9,
                 "⑩": -1 * b("utb_L%d" % L), "⑪": -1 * b("vsc_L%d" % L)}
        keys = {"all": list(votes), "強": ["①", "②", "③", "④", "⑤"], "弱": ["⑥", "⑦", "⑧", "⑨", "⑩", "⑪"]}[which]
        sc = sum(votes[k].astype(int) for k in keys)
        return sc, votes

    def sel_of(L, fq, N, pop, which="all", rand=False):
        sel = {}
        for e in rebs_of(X, fq):
            g = M.get(e)
            if g is None:
                continue
            g = g[popmask(g, pop)]
            if rand:
                sel[e] = g["j"].tolist(); continue
            sc, _ = score_df(g, L, which)
            rng = np.random.default_rng([20261007, 12, int(e)])
            tie = rng.permutation(len(g))
            o = np.lexsort((tie, -sc))
            sel[e] = g["j"].to_numpy()[o][:N].tolist()
        return sel
    rows = []; grid = []
    for L in (5, 20, 60):
        for fq in ("月", "季"):
            for N in (10, 20):
                res = C.sim_book(sel_of(L, fq, N, "合併"), Wd, N, w0, X["w1"])
                st = C.book_stats(res, w0, sp); st["退化"] = degenerate(st, N)
                l_ = C.lab(st["年化"], st["回落"], X["BM"]["探索"]["年化"], X["BM"]["探索"]["回落"])
                rows.append(((L, fq, N), st, l_))
                grid.append({"L": L, "換股": fq, "N": N, "探索": st, "探索標籤": l_, "確認（描述）": C.book_stats(res, X["c0"], X["w1"])})
    L, fq, N = pick_cell(rows)
    J = book_judge(X, lambda pop: sel_of(L, fq, N, pop), N, w0, "L%d %s N%d" % (L, fq, N))
    J.pop("_eq", None)
    fl, lc, l4 = final_from(J)
    R = {"件": "A4-12", "名稱": "多個弱訊號十一票（等權投票）", "挑中格": {"L": L, "換股": fq, "N": N}, "判定": J, "標籤": fl,
         "合併確認": lc, "只400確認": l4, "全表": grid, "N": 1}
    for nm, wh in (("甲 強的5票（描述）", "強"), ("乙 弱的6票（描述）", "弱")):
        res = C.sim_book(sel_of(L, fq, N, "合併", wh), Wd, N, w0, X["w1"])
        R[nm] = {k: C.seg_metrics(res["eq"], a_, b_) for k, (a_, b_) in X["segs"].items()}
    rb = rand_books({"r": {"pools": sel_of(L, fq, N, "合併", rand=True), "N": N, "t0": w0, "item": 12, "arm": 1}}, a.reps, a.procs)["r"]
    R["丙 隨機挑同檔數"] = {"次數": a.reps, "p_確認": p_of(rb, "確認", J["欄"]["合併"]["確認"]["年化"]), "隨機年化中位_確認": float(rb["確認_年化"].median()),
                       "乙對隨機_p_確認": p_of(rb, "確認", R["乙 弱的6票（描述）"]["確認"]["年化"])}
    # 每票命中率、兩兩相關
    s = sel_of(L, fq, N, "合併")
    hit = defaultdict(list); V = defaultdict(list)
    for e, js in s.items():
        g = M.get(e)
        if g is None:
            continue
        _, votes = score_df(g, L)
        m = g["j"].isin(js).to_numpy()
        for k, v in votes.items():
            hit[k].append(float(np.mean(v[m] != 0)) if m.any() else np.nan); V[k].append(v != 0)
    R["每票命中率"] = {k: float(np.nanmean(v)) for k, v in hit.items()}
    VV = pd.DataFrame({k: np.concatenate(v) for k, v in V.items()}).astype(float)
    cm = VV.corr()
    R["票兩兩相關_最大"] = sorted([((a_, b_), float(cm.loc[a_, b_])) for a_, b_ in combinations(cm.columns, 2) if np.isfinite(cm.loc[a_, b_])], key=lambda x: -x[1])[:5]
    R["附註"] = [C.IDEA, C.NO_EARLY, "① 用季營收創 8 季新高：" + C.Q14, "⑤ 強勢股拿掉「20 日漲停 ≥3 次」⇒ 4 條中 ≥3（票數仍 11）", C.SURV]
    return R


# ═════════════ A4-13 探索批 ═════════════
F13 = {"F01": ("rev_yoy", 1), "F03": ("rev_qoq", 1), "F04": ("rev_dist8", 1), "F05": ("r21", -1), "F06": ("r63", 1), "F07": ("r126", 1),
       "F08": ("r12_1", 1), "F09": ("d250hi", 1), "F10": ("c_ma60", 1), "F11": ("vol60", -1), "F12": ("f12", 1), "F16": ("ep", 1),
       "F17": ("divy", 1), "F18": ("bp", 1)}


def a413_pct(X):
    """每個 e、每欄：各條件母體內百分位（DataFrame：j、各 F）。"""
    if "a413p" in _X:
        return _X["a413p"]
    Wd = X["Wd"]; V = np.nan_to_num(Wd["V"].astype(float)); valid = Wd["valid"]
    out = {}
    for e in X["MS"]:
        g = X["ME"].get(e)
        if g is None:
            continue
        g = g.copy()
        f12 = []
        for j in g["j"]:
            vb = np.flatnonzero(valid[:e, j])
            if len(vb) < 80:
                f12.append(np.nan); continue
            a20 = V[vb[-20:], j].mean(); a60 = V[vb[-80:-20], j].mean()
            f12.append(a20 / a60 if a60 > 0 else np.nan)
        g["f12"] = f12
        for pop in C.COLS:
            h = g[popmask(g, pop)]
            P = {"j": h["j"].to_numpy(), "t": h["t"].to_numpy()}
            for F, (col, sgn) in F13.items():
                v = h[col].astype(float).to_numpy() * sgn
                P[F] = pd.Series(v).rank(pct=True, method="average").to_numpy()
            out[(e, pop)] = pd.DataFrame(P)
    _X["a413p"] = out
    return out


def a413_cands(X, cell, pop, t_lo, t_hi):
    P = a413_pct(X)
    out = {}
    for e in X["MS"]:
        if not (t_lo <= e <= t_hi):
            continue
        d = P.get((e, pop))
        if d is None:
            continue
        sc = d[cell[0]].to_numpy() if len(cell) == 1 else (d[cell[0]].to_numpy() + d[cell[1]].to_numpy()) / 2
        ok = np.isfinite(sc)
        n = int(math.floor(0.10 * ok.sum()))
        dd = pd.DataFrame({"j": d["j"].to_numpy()[ok], "t": d["t"].to_numpy()[ok], "s": sc[ok]}).sort_values(["s", "t"], ascending=[False, True])
        out[e] = dd["j"].tolist()[:n]
    return out


def a413_sig(X, cands, end, H=120):
    Wd, cal = X["Wd"], X["cal"]
    O, CF = Wd["O"], Wd["CF"]
    rows = []
    for e, js in cands.items():
        for j in js:
            o = O[e, j]
            if not (np.isfinite(o) and o > 0):
                continue
            x = min(e + H - 1, end)
            if C.crosses(Wd["pb"], j, e, x):
                continue
            rows.append((j, e, x, CF[x, j] / o - 1, str(cal[e])[:7]))
    return C.mk_sig(rows)


def a413(X, a):
    log("A4-13 探索批")
    Wd, w0, w1, sp, c0, cal = X["Wd"], X["w0"], X["w1"], X["sp"], X["c0"], X["cal"]
    conds = list(F13)
    cells = [(f,) for f in conds] + list(combinations(conds, 2))
    segE = {"探索": (w0, sp)}; segC = {"確認": (c0, w1)}
    BM = X["BM"]
    arms = {}
    for cell in cells:
        arms[cell] = {"sig": a413_sig(X, a413_cands(X, cell, "合併", w0, sp), sp), "N": 8, "segs": segE, "cost": C.COST}
    D = C.run_slots(arms, Wd, a.procs, a.seeds)
    S = {k: C.slot_summary(D[k], segE, BM) for k in arms}
    # 線索
    cand = sorted([k for k in cells if S[k]["探索"]["年化中位"] > BM["探索"]["年化"]], key=lambda k: (-S[k]["探索"]["比值"], -S[k]["探索"]["年化中位"]))
    used = Counter(); clues = []
    for k in cand:
        if all(used[f] < 2 for f in k):
            clues.append(k); used.update(k)
        if len(clues) == 5:
            break
    log("A4-13 線索 %s" % clues)
    # 運氣基準（丙）：假條件 105 個 × 50 顆
    fk = {}
    for i in range(len(cells)):
        rng = np.random.default_rng([20261007, 13, i])
        cc = {}
        for e in X["MS"]:
            if w0 <= e <= sp:
                d = a413_pct(X).get((e, "合併"))
                if d is None:
                    continue
                n = int(math.floor(0.10 * len(d)))
                cc[e] = list(rng.choice(d["j"].to_numpy(), size=n, replace=False))
        fk[("fake", i)] = {"sig": a413_sig(X, cc, sp), "N": 8, "segs": segE, "cost": C.COST}
    DF = C.run_slots(fk, Wd, a.procs, min(50, a.seeds))
    fr = np.array([float(DF[k]["探索_年化"].median()) / abs(float(DF[k]["探索_回落"].median())) for k in fk])
    luck = {}
    for k in clues:
        x = S[k]["探索"]["比值"]
        Fx = float(np.mean(fr <= x))
        luck["＋".join(k)] = {"比值": x, "在105次取最好分佈的分位": Fx ** len(cells), "與運氣分不開": bool(Fx ** len(cells) < 0.95)}
    # 確認段
    carms = {}
    for k in clues:
        for pop in C.COLS:
            carms[(k, pop)] = {"sig": a413_sig(X, a413_cands(X, k, pop, c0, w1), w1), "N": 8, "segs": segC, "cost": C.COST}
            if pop != "只500":
                f50 = Wd["pb"] | Wd["f50"]
                sg = carms[(k, pop)]["sig"]
                keepm = [not C.crosses(f50, int(s_), int(e_), int(x_)) for s_, e_, x_ in zip(sg["sid"], sg["entry_pos"], sg["xpos_" + C.RULE])]
                carms[(k, pop, "ret50")] = {"sig": sg[keepm].reset_index(drop=True), "N": 8, "segs": segC, "cost": C.COST}
                for cs_ in C.COST_SENS:
                    carms[(k, pop, "cost%g" % cs_)] = {"sig": sg, "N": 8, "segs": segC, "cost": cs_}
    for pop in ("合併", "只400"):
        cc = {}
        rng = np.random.default_rng([20261007, 13, 999, 0 if pop == "合併" else 1])
        for e in X["MS"]:
            if c0 <= e <= w1:
                d = a413_pct(X).get((e, pop))
                if d is None:
                    continue
                n = int(math.floor(0.10 * len(d)))
                cc[e] = list(rng.choice(d["j"].to_numpy(), size=n, replace=False))
        carms[("S0", pop)] = {"sig": a413_sig(X, cc, w1), "N": 8, "segs": segC, "cost": C.COST}
    DC = C.run_slots(carms, Wd, a.procs, a.seeds)
    SC = {k: C.slot_summary(DC[k], segC, BM) for k in carms}
    R = {"件": "A4-13", "名稱": "探索批（季財報版；14 條件、105 格）", "N": 5, "探索全表": {"＋".join(k): S[k]["探索"] for k in cells},
         "線索": ["＋".join(k) for k in clues], "運氣基準（丙）": luck, "確認": {}}
    labs = []
    for k in clues:
        lc = SC[(k, "合併")]["確認"]["標籤"]; l4 = SC[(k, "只400")]["確認"]["標籤"]
        R["確認"]["＋".join(k)] = {"合併": SC[(k, "合併")]["確認"], "只400": SC[(k, "只400")]["確認"], "只500（描述）": SC[(k, "只500")]["確認"],
                                  "ret50（合併）": SC[(k, "合併", "ret50")]["確認"], "ret50（只400）": SC[(k, "只400", "ret50")]["確認"],
                                  "標籤": C.final_label(lc, l4)}
        labs.append(C.final_label(lc, l4))
    for cs_ in C.COST_SENS:
        for k in clues:
            R["確認"]["＋".join(k)]["成本%.2f%%（合併）" % (cs_ * 100)] = SC[(k, "合併", "cost%g" % cs_)]["確認"]
    R["確認S0"] = {pop: {"合格比例p": SC[("S0", pop)]["確認"]["逐種子合格比例"], "年化中位": SC[("S0", pop)]["確認"]["年化中位"]} for pop in ("合併", "只400")}
    R["純運氣預期合格條數"] = 5 * R["確認S0"]["合併"]["合格比例p"]
    R["標籤彙總"] = Counter(labs)
    R["附註"] = [C.IDEA, C.NO_EARLY, "F13～F15 籌碼拿掉、F02 ≡ F01 退化", "主臂照原文：8 槽、第 120 根收盤出（原文寫死天數，登錄 §〇）", C.SURV]
    return R


# ═════════════ 入口 ═════════════
ITEMS = {"A4-1": a41, "A4-2": a42, "A4-3": a43, "A4-4": a44, "A4-5": a45, "A4-6": a46, "A4-7": a47, "A4-9": a49, "A4-12": a412, "A4-13": a413}


def run_items(a):
    X = context(bool(a.lim))
    only = [x for x in a.only.split(",") if x] or list(ITEMS)
    for it in only:
        t0 = time.time()
        R = ITEMS[it](X, a)
        R["耗時秒"] = round(time.time() - t0, 1); R["算於"] = C.now_tpe(); R["讀法寫死"] = C.READ_TS
        R["台股原登錄"] = C.TW_REG.get(it)
        C.jdump(R, os.path.join(C.OUT, "%s.json" % it))
        log("%s 完成 %.0fs ⇒ %s" % (it, time.time() - t0, R.get("標籤", R.get("標籤彙總", ""))))


def report(a):
    from backtest import researchUSA4_page as RP
    RP.main(a)


# ═════════════ 跟進（seq242 ②：合格／另列者固定跟進出場敏感度；描述、⛔ 不判、不計 N）═════════════
def a42_rows(X, conds, pop, start):
    """A4-2 主臂訊號列（a42 同式）。"""
    Wd, cal, w1, M = X["Wd"], X["cal"], X["w1"], X["M"]
    MSs = [e for e in X["MS"] if e >= start]
    ok = np.ones(len(M), bool)
    for c_ in conds:
        ok &= (M[c_].astype(float).fillna(0).to_numpy() > 0)
    S = M.assign(ok=ok)[["j", "e", "ok", "m4", "m5"]]
    okset = set(zip(S.loc[S["ok"], "j"], S.loc[S["ok"], "e"]))
    cand = S[S["ok"] & (S["e"] >= start)]
    cp = cand if pop == "合併" else cand[cand["m4"] if pop == "只400" else cand["m5"]]
    rows = []
    for j, e in zip(cp["j"], cp["e"]):
        o = Wd["O"][e, j]
        if not (np.isfinite(o) and o > 0):
            continue
        x = None
        for e2 in MSs:
            if e2 > e and (j, e2) not in okset:
                x = e2; break
        if x is None or x > w1:
            x = w1; g = Wd["CF"][w1, j] / o - 1
        else:
            ox = Wd["O"][x, j]; g = (ox if np.isfinite(ox) and ox > 0 else Wd["CF"][x, j]) / o - 1
        if not C.crosses(Wd["pb"], j, e, x):
            rows.append((int(j), int(e), int(x), float(g), str(cal[e])[:7]))
    return rows


def stop_rows(Wd, rows, s, w1):
    out = []
    for j, e, x, g, mo in rows:
        o = Wd["O"][e, j]; cf = Wd["CF"][e:x, j]
        hit = np.flatnonzero(cf <= o * (1 - s))
        if len(hit) and e + hit[0] + 1 < x:
            d = e + hit[0] + 1; od = Wd["O"][d, j]
            out.append((j, e, d, (od if np.isfinite(od) and od > 0 else Wd["CF"][d, j]) / o - 1, mo))
        else:
            out.append((j, e, x, g, mo))
    return out


def _fake42(args):
    r = args
    s = _X["f42"]; Wd = _X["ctx"]["Wd"]; w1 = _X["ctx"]["w1"]
    rng = np.random.default_rng([20261007, 2, s["arm"], r])
    rows = []
    for j, e, x, g, mo in s["rows"]:
        pool = s["pool"][e]
        if not len(pool):
            continue
        for _ in range(10):
            jj = int(pool[rng.integers(len(pool))])
            if not C.crosses(Wd["pb"], jj, e, x):
                break
        o = Wd["O"][e, jj]
        if x == w1:
            gg = Wd["CF"][w1, jj] / o - 1
        else:
            ox = Wd["O"][x, jj]; gg = (ox if np.isfinite(ox) and ox > 0 else Wd["CF"][x, jj]) / o - 1
        rows.append((jj, e, x, gg, mo))
    sig = C.mk_sig(rows)
    C.R11.COST = C.COST
    ctx = C.slot_ctx(Wd)
    out = C.R11.simulate_mtm(sig, C.RULE, 10, np.random.default_rng(C.SEED0 + r), ctx["closes"], ctx["opens"], ctx["n"], return_equity=True,
                             pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=ctx["trad"], delist=ctx["dl"])
    eq = out["equity"]
    return {nm: C.seg_metrics(eq, a_, b_) for nm, (a_, b_) in s["segs"].items()}


def followup(a):
    X = context(bool(a.lim))
    Wd, cal, w1 = X["Wd"], X["cal"], X["w1"]
    R = {"性質": "seq242 ②：合格／另列者固定跟進出場敏感度（描述、⛔ 不判、不計 N）", "算於": C.now_tpe()}
    # ── A4-2
    d42 = json.load(open(os.path.join(C.OUT, "A4-2.json"), encoding="utf-8"))
    start = int(cal.searchsorted(pd.Timestamp("2018-03-01")))
    segs = {"探索": (start, X["sp"]), "確認": (X["c0"], w1), "全窗": (start, w1)}
    BM = C.bench_metrics(cal, segs)
    C.slot_ctx(Wd)
    for nm, cs in SETS.items():
        T = d42["套"][nm]
        if not (T["合併確認"] in ("合格", "另列")):
            continue
        out = {}
        for pop in ("合併", "只400"):
            rows = a42_rows(X, cs, pop, start)
            arms = {("N5",): {"sig": C.mk_sig(rows), "N": 5, "segs": segs, "cost": C.COST},
                    ("N20",): {"sig": C.mk_sig(rows), "N": 20, "segs": segs, "cost": C.COST},
                    ("停損10%",): {"sig": C.mk_sig(stop_rows(Wd, rows, 0.10, w1)), "N": 10, "segs": segs, "cost": C.COST},
                    ("停損20%",): {"sig": C.mk_sig(stop_rows(Wd, rows, 0.20, w1)), "N": 10, "segs": segs, "cost": C.COST}}
            if pop == "合併":
                for k in range(4):
                    arms[("拿掉" + cs[k],)] = {"sig": C.mk_sig(a42_rows(X, tuple(c for i, c in enumerate(cs) if i != k), pop, start)), "N": 10, "segs": segs, "cost": C.COST}
            D = C.run_slots(arms, Wd, a.procs, a.seeds)
            out[pop] = {k[0]: C.slot_summary(D[k], segs, BM)["確認"] for k in arms}
            # 假訊號：每筆換成同一進場日、同欄母體隨機一檔（持有區間不變）
            pool = {}
            for e in sorted(set(r[1] for r in rows)):
                g = X["ME"].get(e)
                g = g[popmask(g, pop)] if g is not None else None
                js = g["j"].to_numpy() if g is not None else np.zeros(0, int)
                js = js[np.isfinite(Wd["O"][e, js]) & (np.nan_to_num(Wd["O"][e, js]) > 0)] if len(js) else js
                pool[e] = js
            _X["f42"] = {"rows": rows, "pool": pool, "segs": segs, "arm": 1 if pop == "合併" else 2}
            with Pool(a.procs) as pp:
                F = pp.map(_fake42, range(a.reps), chunksize=max(1, a.reps // (a.procs * 10)))
            lab_ = [C.lab(f["確認"]["年化"], f["確認"]["回落"], BM["確認"]["年化"], BM["確認"]["回落"]) for f in F]
            real = T["欄"][pop]["main"]["確認"]["年化中位"]
            out[pop]["假訊號（同日同池隨機一檔、持有區間不變）"] = {"次數": a.reps, "合格比例": float(np.mean([l_ == "合格" for l_ in lab_])),
                                                     "年化中位": float(np.median([f["確認"]["年化"] for f in F])),
                                                     "p（假 ≥ 真年化中位）": float(np.mean([f["確認"]["年化"] >= real for f in F]))}
        R["A4-2 " + nm] = out
        log("跟進 A4-2 %s 完成" % nm)
    # ── A4-1（換股簿）
    d41 = json.load(open(os.path.join(C.OUT, "A4-1.json"), encoding="utf-8"))
    ma60 = pd.DataFrame(Wd["CF"]).rolling(60, min_periods=60).mean().to_numpy()
    for fam in ("甲", "乙"):
        D = d41["族"][fam]
        if D["合併確認"] not in ("合格", "另列"):
            continue
        ch = D["挑中格"]; out = {}
        for pop in ("合併", "只400"):
            def sel_for(N):
                sel = {}
                for e in rebs_of(X, ch["頻率"]):
                    g = X["ME"].get(e)
                    if g is None:
                        continue
                    g = g[popmask(g, pop)]
                    g = g[g["sector"].fillna("") != "Financials"]
                    if fam == "乙":
                        g = g[g["rev_hi8"].astype(float).fillna(0) > 0]
                    sel[e] = topn_sel(g, ch["量測"], N)
                return sel
            o = {}
            for N in (5, 20):
                res = C.sim_book(sel_for(N), Wd, N, X["w0"], w1)
                m = C.seg_metrics(res["eq"], X["c0"], w1); m["標籤"] = C.lab(m["年化"], m["回落"], X["BM"]["確認"]["年化"], X["BM"]["確認"]["回落"]); o["N%d" % N] = m
            res = C.sim_book(sel_for(ch["N"]), Wd, ch["N"], X["w0"], w1, ma_stop=ma60)
            m = C.seg_metrics(res["eq"], X["c0"], w1); m["標籤"] = C.lab(m["年化"], m["回落"], X["BM"]["確認"]["年化"], X["BM"]["確認"]["回落"]); o["跌破MA60次日賣"] = m
            out[pop] = o
        R["A4-1 %s族" % fam] = out
        log("跟進 A4-1 %s 完成" % fam)
    C.jdump(R, os.path.join(C.OUT, "followup.json"))

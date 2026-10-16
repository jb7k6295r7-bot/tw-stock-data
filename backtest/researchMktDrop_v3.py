# -*- coding: utf-8 -*-
"""PREREG大盤大跌後買什麼 seq3（登錄 sha deb289c23b6020bd；裁定 seq358 核；取代 seq2；C＋ 新格 seq353 已 N_組合 ＋1；買法四臂只描述、⛔ 不計 N；判語不動）
——回測線計算子代理，2026-10-17。
⚠ 已看過初測與 seq1 結果 ⇒ 事後重切、最多暫定；判語只到方向（一致／不一致）；合格只看前瞻（事件累計 ≥ 10 次判一次）。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（researchMktDrop_v1／初測／researchExit5 只 import 重用；v1 逐股快取只讀）；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_v3 [--procs 2]
    獨立重算： ... -m backtest.researchMktDrop_v3_check [--procs 2]

═══ 讀法（執行者補的都在這裡；寫死於第一次跑之前，2026-10-17 台北）═══
 R0 事件、母體、候選 A～F、出場（主＋副1＋副2）、成本、配對 0050、①②組合層、隨機日 200 次、段、等效獨立事件數：⭐ 全部照 seq1 v1（researchMktDrop_v1）——
    v1.index_events／day_stats／bpath／curve1／curve2／wstats／eff_n 只 import 呼叫；v1.run 是單一函式、會寫 v1 目錄 ⇒ 本檔照抄其迴圈（邏輯不改）、輸出改到 v3 目錄；
    逐股快取讀 ~/mktdropwork/v1/packs_*.pkl（只讀）；執行期把 v1 模組的 CANDS／basket 換成本件清單（記憶體內、⛔ 不改 v1 檔）
    隨機日種子 ＝ v1 同式 default_rng([v1.RSEED, 段號, 候選號, i])；候選號 A～F ＝ 0～5（同 v1）、C＋ ＝ 9（同 researchMktDrop_yl，⇒ C＋ 主出場數字可與 yl 對帳）
 R1 C＋（登錄 §二、§八）＝ C 那一成（事件日 R1 母體報酬最低 ceil(10%) 檔，v1 穩定排序）中「事件日可得的最近一期月營收年增 ＞ 0」的股票等權；
    營收 ＝ researchExit5.load_revenue（早年＋主世界 revenue_hist、主世界優先，同 deep／yl）；可得日 ＝ researchExit5.avail_pos
    （≤2025-12 期 次月 10 日之後第一個交易日、≥2026-01 期 次月 15 日之後第一個交易日）；取可得日 ≤ t 的最後一期；年增 ＝ 當月營收 ÷ 去年當月營收 − 1（去年 ≤0 或缺 ⇒ 缺 ⇒ 不入選）；
    ⛔ 不設資料過舊上限（同 deep／yl）；候選檔數 ＝ 過濾後、買不到之前；買不到剔除（同 v1）；C＋ 也做 q1／f2／f3 與副1／副2 描述（同 v1 格式）
    判語口徑同 v1（seq1 §四）：兩主段 事件層配對差平均 ＞ 0 ∧ ② 年化 ≥ 一直抱 0050 ∧ ② 比值 ≥ 一直抱 0050 ⇒「方向一致（暫定）」，否則「方向不一致」
 R2 買法四臂（登錄 §九；⛔ 不判、不計 N；適用 A、B、C、C＋、E；q2 接受事件；出場一律主出場 ＝ v1 快取 SP／SX／SK 同一筆）：
    P主 ＝ t＋1 開盤（＝ v1 主規則；程式內對帳 ＝ v1 day_stats 淨報酬，差 ＞ 1e−12 ⇒ 停）
    P0 ＝ 事件日 t 收盤價買：該股 t 有 K 棒（母體成員本來就有）∧ t 收盤非漲停（load_bars up）∧ 之後還有 K 棒 ∧ 下一根不是壞根（同 v1「隔天是壞根 ⇒ 買不到」）
    P1 ＝ t＋2 開盤、P2 ＝ t＋3 開盤（日曆位置）：該日有 K 棒 ∧ 有成交 ∧ 開盤有效 ∧ 非開盤漲停鎖死 ∧ 從 t 的下一根到買進根之間（含）沒有壞根
         ⇒ 買不到剔除（比例照報）；籃子 ＝ 同一份 t 收盤決定的名單（買不到之前），各臂各自剔除
    買前已出場：主出場賣出時點（開盤賣 ＝ 2×位置、收盤賣 ＝ 2×位置＋1）不晚於買進時點（開盤 2×位置、收盤 2×位置＋1）⇒ 該檔該臂不進場；
         整籃都不進場 ⇒ 該事件該臂記「未進場（買前已收復）」：平均另報「只算有進場的」與「未進場記 0」兩種
    P3 ＝ 一半資金 P主、一半資金 P1：淨報酬 ＝ 0.5 × P主 籃子淨報酬 ＋ 0.5 × P1 籃子淨報酬（P1 未進場 ⇒ 該半留現金 0、無成本）
    每臂淨報酬 ＝ 等權籃子 (1 ＋ 平均毛報酬) × (1 − 成本) − 1（成本同 v1：個股 0.585%、ETF 0.385%）
    報：每格每買法 事件層平均、中位、勝率、對 P主 的差（同事件兩臂都有進場者：平均、中位）、未進場事件數；跳空 ＝ P主 可買檔 (t＋1 開盤 ÷ t 收盤 − 1) 籃內平均 ⇒ 段內事件中位
    段 ＝ 2006～2014、2015～2021、2022～ ＋「全部」；B 早年 ⛔ 不算（同 v1）
 R3 最壞情況（登錄 §五 seq3；q2 主出場；A～F、C＋）：等待交易日 ＝ 賣完日曆位置 − 買進日曆位置（籃子最後一檔賣出；壞根／下市先賣的不延長）；
    最深帳面跌幅 ＝ 持有中籃子毛值（相對買價、日收盤、已賣的檔固定在賣價）最低點 − 1（未扣成本；不低於買價 ⇒ 0）＝ v1「持有中最低相對買價」；
    每格每段報最長等待、最深跌幅；最慘 3 事件 ＝ 三段合併依最深帳面跌幅由深到淺（同值依日期）；另附指數本身的收復等待（v1 events）
 R4 對帳：A～F 的 cells／portfolio／event_rows／main_table／events／random 以同格式輸出後與 v1 目錄逐字比對（不同 ⇒ 改數值比、報最大差）；C＋ q2 主出場 vs yl main_table
── 事後註（照實記）──
 ① 02:05 第一次全跑：A～F 五檔逐字相同；events.csv 因指數資料比 v1 新（origin/main 已到 2026-10-16）多 3 列（q2／f2／f3 的 2026-10-15，世界尾後、不算）
    ⇒ 對帳改成以 v1 的（定義, 日期）對齊、另列多出的列後重跑；⛔ 事件、候選、出場、判語、買法定義都沒改
輸出 backtest/resultsMktDrop/v3/：MktDrop_v3.json、main_table.csv、cells.csv、event_rows.csv、portfolio.csv、events.csv、random.csv.gz、
      buyarms.csv、buyarm_rows.csv、worst.csv、worst_top3.csv、recon_v1.csv、run.log
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest/resultsMktDrop/v3")
V1OUT = os.path.join(REPO, "backtest/resultsMktDrop/v1")
YLMAIN = os.path.join(REPO, "backtest/resultsMktDrop/yl/main_table.csv")
V1WORK = os.path.expanduser("~/mktdropwork/v1")
REG = {"件": "PREREG大盤大跌後買什麼 seq3", "sha": "deb289c23b6020bd", "裁定": "seq358 核（取代 seq2；C＋ 新格 seq353 已 N_組合 ＋1；買法四臂只描述、不計 N；判語不動）",
       "前版": {"seq2": "4511f202c434bc62", "seq1": "94852550bcc7e70a"}}
TIME = "2026-10-17 02:00（台北；讀法寫死、第一次跑之前）"
CANDS3 = ["A", "B", "C", "D", "E", "F", "C+"]
RIDX = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "C+": 9}
ARM_CANDS = ["A", "B", "C", "C+", "E"]
ARMS = ["P主", "P0", "P1", "P2", "P3"]
AN = {"P主": "t＋1 開盤買（主規則）", "P0": "事件日 t 收盤價買", "P1": "t＋2 開盤買（隔 1 天）", "P2": "t＋3 開盤買（隔 2 天）", "P3": "一半 t＋1 開盤、一半 t＋2 開盤"}
SEG_ORDER = {"2006～2014": 0, "2015～2021": 1, "2022～": 2, "全部": 3}
NOTES_V3 = ["看過初測才登錄，最多暫定",
            "事件約每年 1 次，樣本很少",
            "收復才賣的勝率有一部分來自規則本身（等多久都等）",
            "C＋：從約 10 個描述變體中挑出（逆勢漲三種、逐筆拆解、加碼營量營飆持股三種、營收條件兩種）；看過後才挑，最多暫定",
            "正2 的結果含槓桿本身的效果",
            "早年（2006～2014）含減資假飆股約 0.3%（剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；2005-01～2007-06 只有上市",
            "判語只到方向（一致／不一致）；⛔ 不給合格；合格只看前瞻（事件累計 ≥ 10 次判一次）",
            "買法四臂（§九）只描述、⛔ 不判、⛔ 不據此改主判、⛔ 不挑最好的買法；P0 事件判定用 t 收盤，實務上要在 13:25 前以盤中價近似判斷",
            "最深帳面跌幅未扣成本；等待交易日 ＝ 買進到籃子賣完",
            "成本：個股 0.585% 來回、ETF 0.385%；未含滑價；⛔ 不是買賣建議"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 逐股 K 棒（買法臂用；只讀資料層）═════════════
def bars_job(a):
    wn, sid = a
    from backtest import data as D
    from backtest import research11 as R
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = np.asarray(B["idx"], np.int64); nb = len(idx)
    next_bad = np.asarray(B["next_bad"])
    bad = np.asarray(next_bad[:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    return sid, {"idx": idx, "o": np.asarray(B["o"], float), "c": np.asarray(B["c"], float), "up": np.asarray(B["up"], bool), "bad": bad}


def sel_pre(M, t, cd):
    """t 收盤決定的名單（買不到之前）；照抄 v1.basket 的選股（不含 BUY 過濾）。"""
    if cd in ("A", "B"):
        return np.array([M["S"] + (0 if cd == "A" else 1)])
    if cd == "F":
        return np.flatnonzero(M["ACH"][:, t])
    m = M["MEM"][:, t] & np.isfinite(M["RET"][:, t])
    rows = np.flatnonzero(m)
    if len(rows) < 20:
        return np.array([], int)
    v = M["RET"][rows, t]
    if cd in ("C", "D", "C+"):
        ns = int(np.ceil(0.10 * len(rows)))
        o = np.argsort(v, kind="stable")
        sel = rows[o[:ns]] if cd in ("C", "C+") else rows[o[::-1][:ns]]
        if cd == "C+":
            with np.errstate(invalid="ignore"):
                sel = sel[M["YOY"][sel, t] > 0]
        return sel
    ic = M["IND"][rows, t]; ok = ic >= 0
    if not ok.any():
        return np.array([], int)
    df = pd.DataFrame({"i": ic[ok], "v": v[ok], "r": rows[ok]})
    g = df.groupby("i")["v"].agg(["mean", "count"]); g = g[g["count"] >= 5]
    if len(g) < 2:
        return np.array([], int)
    g = g.reset_index().sort_values(["mean", "i"], kind="stable")
    worst = [int(x) for x in g["i"].iloc[:2]]
    return df.loc[df["i"].isin(worst), "r"].to_numpy()


def arm_legs(W, M, BARS, r, p):
    """⇒ {臂: (買進時點, 買價) 或 None}、主出場 (賣出時點, 賣價)、跳空（P主 可買時）。"""
    n0 = W["n0"]; S = M["S"]
    spos = int(M["SP"]["主"][r, p]); sx = float(M["SX"]["主"][r, p]); kd = int(M["SK"]["主"][r, p])
    if spos < 0:
        return None, None, np.nan
    ts = 2 * spos + (0 if kd == 0 else 1)
    legs = {}
    legs["P主"] = (2 * (p + 1), float(M["BP"][r, p])) if M["BUY"][r, p] else None
    if r >= S:                                              # ETF
        df = W["etf_0050" if r == S else "etf_00631L"]
        tr = df["traded"].to_numpy(bool); o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
        legs["P0"] = (2 * p + 1, float(c[p])) if (tr[p] and np.isfinite(c[p]) and c[p] > 0) else None
        for a_, j in (("P1", 2), ("P2", 3)):
            q = p + j
            legs[a_] = (2 * q, float(o[q])) if (q < n0 and tr[q] and np.isfinite(o[q]) and o[q] > 0) else None
        gap = float(o[p + 1] / c[p] - 1.0) if legs["P主"] is not None else np.nan
    else:
        sid = M["sids"][r]; B = BARS[sid]; i = W["ix"][sid]
        idx, o, c, up, bad = B["idx"], B["o"], B["c"], B["up"], B["bad"]; nb = len(idx)
        k = int(np.searchsorted(idx, p))
        if not (k < nb and idx[k] == p):
            raise SystemExit(f"⛔ {sid} 事件日 {p} 沒有 K 棒")
        if legs["P主"] is not None and abs(o[k + 1] / legs["P主"][1] - 1.0) > 1e-12:
            raise SystemExit(f"⛔ {sid} t＋1 開盤 ≠ v1 BP")
        legs["P0"] = (2 * p + 1, float(c[k])) if (k + 1 < nb and not bad[k + 1] and not up[k] and np.isfinite(c[k]) and c[k] > 0) else None
        TRD, O, UPL = W["TRD"][i], W["O"][i], W["UPL"][i]
        for a_, j in (("P1", 2), ("P2", 3)):
            q = p + j
            b = int(np.searchsorted(idx, q))
            ok = (q < n0 and b < nb and idx[b] == q and not bad[k + 1:b + 1].any() and TRD[q] and np.isfinite(O[q]) and O[q] > 0 and not UPL[q])
            legs[a_] = (2 * q, float(o[b])) if ok else None
        gap = float(o[k + 1] / c[k] - 1.0) if legs["P主"] is not None else np.nan
    return legs, (ts, sx), gap


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    from multiprocessing import Pool
    from backtest import researchMktDrop as MD
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchExit5 as EX5
    MD.SEGS = V1.SEGS_V1
    orig_basket = V1.basket

    def basket3(M, t, cd):
        if cd != "C+":
            return orig_basket(M, t, cd)
        sel = sel_pre(M, t, "C+")
        return sel[M["BUY"][sel, t]], len(sel), None
    V1.basket = basket3; V1.CANDS = CANDS3                 # 只在記憶體內換（⛔ 不改 v1 檔）
    CN3 = {**V1.CN, "C+": "C 中最近一期月營收年增 ＞ 0"}
    S = {"件": REG, "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭 R0～R4", "必附": NOTES_V3, "候選": CN3, "出場": V1.EN, "事件定義": V1.DN,
         "買法": AN, "閘": {}}
    IXmd = MD.load_index(log)
    sha = IXmd["sha"]; df = IXmd["df"]
    EV = V1.index_events(df)
    fr = np.flatnonzero(np.isfinite(EV["q2"]))[0]
    for k in V1.DEFS:
        ft = np.flatnonzero(EV["FIRST"][k])
        if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
            raise SystemExit(f"⛔ {k} 收復列與初測 rec 不同")
    S["指數"] = {"origin/main sha": sha, "期間": f"{df['date'].iloc[0].date()}～{df['date'].iloc[-1].date()}",
                 "門檻起算": "2005-01-03", "第一個可判日": str(df["date"].iloc[fr].date())}
    v1j = json.load(open(os.path.join(V1OUT, "MktDrop_v1.json"), encoding="utf-8"))
    S["指數"]["v1 用的 sha"] = v1j["指數"]["origin/main sha"]
    S["指數"]["與 v1 同 sha"] = bool(sha == v1j["指數"]["origin/main sha"])
    # 事件清單（同 v1）
    rows = []
    for k in V1.DEFS:
        for i in np.flatnonzero(EV["FIRST"][k]):
            rc = int(EV["rec"][i]); b = int(EV["BLK"][k][i])
            nblk = int(((EV["BLK"][k] == i)).sum()) if EV["ACC"][k][i] else None
            rows.append({"定義": k, "日期": str(df["date"].iloc[i].date()), "指數報酬": float(EV["r"][i]), "門檻": V1.thr_of(EV, k, i),
                         "判定": "接受" if EV["ACC"][k][i] else "持有中又遇事件（不加碼）", "被誰擋": (str(df["date"].iloc[b].date()) if b >= 0 else None),
                         "收復日": (str(df["date"].iloc[rc].date()) if rc >= 0 else None),
                         "收復等待（指數交易日）": (rc - i if rc >= 0 else None), "未收復（到指數尾）": rc < 0,
                         "持有中又遇事件次數": nblk, "原始日數（波段內 20 日）": int(EV["RAW"][k][i:i + V1.DEDUP + 1].sum())})
    EVT = pd.DataFrame(rows)
    S["事件數"] = {k: {"原始": int(EV["RAW"][k].sum()), "去重（波段第一天）": int(EV["FIRST"][k].sum()), "接受": int(EV["ACC"][k].sum()),
                     "持有中又遇事件": int((EV["BLK"][k] >= 0).sum())} for k in V1.DEFS}
    log(f"[事件] {S['事件數']}")
    S["前瞻 10/15 判定"] = V1.judge_date(V1.FWD0_DATE, df=df, sha=sha)
    # 營收（同 yl）
    rev_e, rly_e, info_e = EX5.load_revenue(MD.DB.WORLDS["早年"]["data"])
    rev_m, rly_m, info_m = EX5.load_revenue(MD.DB.WORLDS["主"]["data"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    S["營收"] = {"早年": info_e, "主": info_m}
    PRE_rev = MD.PRE.load_rev(MD.IND_DATA)
    MD._G["PIT"] = MD.PRE.PIT(MD.IND_DATA, PRE_rev[2])
    ROWS = []; CELLS = []; PORT = []; RND = []; AROWS = []
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W; _G[wn] = W
        S["閘"][wn] = {"世界": W["gate"], "壞根": W["bad_info"], "段": {sg: f"{W['cal'][x].date()}～{W['cal'][y].date()}" for sg, (x, y) in W["segp"].items()}}
        PK = pickle.load(open(os.path.join(V1WORK, f"packs_{wn}.pkl"), "rb")); log(f"[逐股 {wn}] 讀 v1 快取（只讀）")
        gc = max(v["gate_c"] for v in PK.values())
        S["閘"][wn]["快取收盤 vs load_bars 最大相對差"] = gc
        if gc > 1e-9:
            raise SystemExit(f"⛔ {wn} 價格閘不過 {gc}")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        S["閘"][wn]["ETF 有資料"] = {s: (None if EP[s] is None else f"{W['cal'][EP[s]['idx'][0]].date()}～{W['cal'][EP[s]['idx'][-1]].date()}") for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        S["閘"][wn]["營量"] = MD.f_flags(W, PK, M, log)
        cal = W["cal"]; n0 = W["n0"]; BO, BC = W["BO"], W["BC"]
        # 營收年增矩陣（同 yl）
        AV = EX5.avail_pos(list(rev.index), cal)
        YOY = np.full((M["S"], n0), np.nan); ar = np.arange(n0)
        for r, s in enumerate(M["sids"]):
            ev = EX5.rev_events(s, rev, rly, AV, n0)
            if not ev:
                continue
            rA = np.array([e[0] for e in ev], np.int64)
            j = np.searchsorted(rA, ar, "right") - 1; ok = j >= 0; jj = np.maximum(j, 0)
            yv = np.array([e[1] for e in ev], float)
            YOY[r, ok] = yv[jj[ok]]
        M["YOY"] = YOY
        DAY, MEMB = V1.day_stats(W, M, log)
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        holdc = {"0050": BC / BC[0]}
        if EP.get("00631L") is not None:
            cf = EP["00631L"]["cff"]; f0 = np.flatnonzero(np.isfinite(cf))[0]; hc = np.full(n0, np.nan); hc[f0:] = cf[f0:] / cf[f0]
            holdc["00631L"] = hc
        for sg, (x0, y0) in W["segp"].items():
            b = MD.RR.bench_row(cal, W["bench"], x0, y0 + 1)
            S.setdefault("一直抱", {})[sg] = {"0050": V1.wstats(holdc["0050"], x0, y0), "0050（rerun17.bench_row 對照）": {"年化": b["cagr"], "最大回落": b["mdd"]},
                                             "00631L（正2 一直抱，描述）": (V1.wstats(holdc["00631L"], x0, y0) if "00631L" in holdc and np.isfinite(holdc["00631L"][x0]) else None)}
        EVS = {}
        for k in V1.DEFS:
            rawpos = {datepos[d] for d in df["date"][EV["RAW"][k]] if d in datepos}
            evs = []
            for i in np.flatnonzero(EV["ACC"][k]):
                p = datepos.get(df["date"].iloc[i])
                if p is not None and p + 1 < n0 and segof(p) is not None:
                    evs.append((p, i))
            EVS[k] = evs
            for cd in CANDS3:
                if cd == "B" and wn == "早年":
                    continue
                cost = V1.COST_ETF if cd in ("A", "B") else V1.COST_STK
                for x in V1.EXITS:
                    paths = {}
                    for p, i in evs:
                        Dx = DAY[cd]; Dd = Dx[x]
                        base = {"世界": wn, "段": segof(p), "定義": k, "候選": cd, "出場": x, "日期": str(cal[p].date()), "指數報酬": float(EV["r"][i]),
                                "選出檔數": int(Dx["nsel"][p]), "買到檔數": int(Dx["n"][p]), "產業": Dx["ind"][p],
                                "候選不足（F ＜5）": bool(cd == "F" and Dx["nsel"][p] < 5)}
                        if Dx["n"][p] == 0:
                            ROWS.append({**base, "進場": False}); continue
                        e_, end_, V, ro = V1.bpath(W, M, MEMB[(cd, p)], p, x)
                        paths[p] = (e_, end_, V, ro)
                        Vpk = np.maximum.accumulate(np.r_[1.0, V])
                        ROWS.append({**base, "進場": True, "報酬": float(Dd["net"][p]), "毛報酬": float(Dd["gross"][p]), "配對0050": float(Dd["b50"][p]),
                                     "配對差": float(Dd["net"][p] - Dd["b50"][p]), "平均持有天數": float(Dd["hold"][p]), "最長持有天數": float(Dd["maxhold"][p]),
                                     "持有中最大回落": float(np.min(np.r_[1.0, V] / Vpk - 1)), "持有中最低相對買價": float(min(0.0, np.min(V) - 1)),
                                     "窗尾未出場比例": float(Dd["unex"][p]), "賣完日": str(cal[end_].date()),
                                     "等待交易日（買進到賣完）": int(end_ - e_), "最深帳面跌幅日": str(cal[e_ + int(np.argmin(V))].date())})
                    for sg, (x0, y0) in W["segp"].items():
                        es = [(p, i) for p, i in evs if x0 <= p <= y0]
                        ec = [p for p, _ in es if DAY[cd]["n"][p] > 0]
                        Dd = DAY[cd][x]
                        row = {"世界": wn, "段": sg, "定義": k, "候選": cd, "出場": x, "指數事件數（接受、段內）": len(es), "進場事件數": len(ec)}
                        if cd == "F":
                            row["候選不足事件數（＜5，含 0）"] = int(sum(DAY["F"]["nsel"][p] < 5 for p, _ in es)); row["0 檔事件數"] = int(sum(DAY["F"]["n"][p] == 0 for p, _ in es))
                        if ec:
                            vals = np.array([Dd["net"][p] for p in ec]); b50 = np.array([Dd["b50"][p] for p in ec]); dif = vals - b50
                            ne, rho, prs = V1.eff_n(vals, [(paths[p][0], paths[p][1]) for p in ec])
                            nb_ = np.array([DAY[cd]["n"][p] for p in ec]); ns_ = np.array([DAY[cd]["nsel"][p] for p in ec])
                            row.update({"等效獨立事件數": ne, "ρ": rho, "重疊對數": prs, "平均報酬": float(vals.mean()), "中位報酬": float(np.median(vals)),
                                        "勝率": float(np.mean(vals > 0)), "同期0050平均（配對、含成本）": float(b50.mean()),
                                        "配對差平均": float(dif.mean()), "配對差中位": float(np.median(dif)), "X較好比例": float(np.mean(dif > 0)),
                                        "平均持有天數": float(np.mean([Dd["hold"][p] for p in ec])), "最長持有天數": float(np.max([Dd["maxhold"][p] for p in ec])),
                                        "有窗尾未出場的事件數": int(sum(Dd["unex"][p] > 0 for p in ec)), "平均籃子檔數": float(nb_.mean()),
                                        "買不到比例": float(1 - nb_.sum() / ns_.sum()) if ns_.sum() else np.nan})
                            if k == "q2" and x == "主":
                                yrs = pd.Series([cal[p].year for p in ec]).value_counts().to_dict()
                                pool = {y_: np.array([t for t in range(x0, min(y0, n0 - 2) + 1) if cal[t].year == y_ and t not in rawpos and DAY[cd]["n"][t] > 0], int) for y_ in yrs}
                                rm = []
                                for rep in range(V1.NRAND):
                                    rng = np.random.default_rng([V1.RSEED, list(V1.SEGS_V1[wn]).index(sg) + (0 if wn == "早年" else 1), RIDX[cd], rep])
                                    dl = [rng.choice(pool[y_], size=min(c_, len(pool[y_])), replace=False) for y_, c_ in sorted(yrs.items()) if len(pool[y_])]
                                    dr = np.concatenate(dl) if dl else np.array([], int)
                                    rm.append(float(np.mean(Dd["net"][dr])) if len(dr) else np.nan)
                                    RND.append({"段": sg, "候選": cd, "i": rep, "隨機平均": rm[-1]})
                                rm = np.array(rm)
                                row.update({"隨機平均": float(np.nanmean(rm)), "實際減隨機": float(vals.mean() - np.nanmean(rm)), "p（隨機 ≥ 實際）": float(np.nanmean(rm >= vals.mean()))})
                        CELLS.append(row)
                    if k == "q2" and x == "主":
                        pl = [paths[p] for p in sorted(paths)]
                        eq1, inm = V1.curve1(n0, pl, cost)
                        if cd == "A":
                            eq2, skp = holdc["0050"].copy(), 0
                        else:
                            eq2, skp = V1.curve2(n0, pl, BO, BC, cost)
                        for sg, (x0, y0) in W["segp"].items():
                            h = V1.wstats(holdc["0050"], x0, y0); s1 = V1.wstats(eq1, x0, y0); s2 = V1.wstats(eq2, x0, y0)
                            PORT.append({"世界": wn, "段": sg, "候選": cd, "①只在事件進場_年化": s1["年化"], "①最大回落": s1["最大回落"], "①比值": s1["比值"],
                                         "①在場日比例": float(inm[x0:y0 + 1].mean()),
                                         "②平時0050換20%_年化": s2["年化"], "②最大回落": s2["最大回落"], "②比值": s2["比值"], "②略過重疊事件": skp,
                                         "一直抱0050_年化": h["年化"], "一直抱0050_最大回落": h["最大回落"], "一直抱0050_比值": h["比值"],
                                         "①比值減0050": s1["比值"] - h["比值"], "②年化減0050": s2["年化"] - h["年化"], "②比值減0050": s2["比值"] - h["比值"]})
            log(f"[{wn}] {k} 完｜{time.time() - T0:.0f}s")
        # ═══ 買法四臂（q2 接受事件）═══
        evs = EVS["q2"]
        need = set()
        for p, _ in evs:
            for cd in ("C", "E"):
                need |= {M["sids"][r] for r in sel_pre(M, p, cd) if r < M["S"]}
        t1 = time.time()
        with Pool(a.procs) as pool:
            BARS = dict(pool.imap_unordered(bars_job, [(wn, s) for s in sorted(need)], chunksize=8))
        log(f"[買法 {wn}] 讀 K 棒 {len(BARS)} 檔｜{time.time() - t1:.0f}s")
        mism = 0
        for p, i in evs:
            sg = segof(p)
            for cd in ARM_CANDS:
                if cd == "B" and wn == "早年":
                    continue
                sel = sel_pre(M, p, cd)
                if cd not in ("A", "B"):
                    Iv1 = MEMB.get((cd, p), np.array([], int))
                    if not np.array_equal(np.sort(sel[M["BUY"][sel, p]]), np.sort(Iv1)) or len(sel) != DAY[cd]["nsel"][p]:
                        raise SystemExit(f"⛔ {wn} {cal[p].date()} {cd} 名單 ≠ v1 籃子")
                cost = V1.COST_ETF if cd in ("A", "B") else V1.COST_STK
                acc = {a_: {"g": [], "feas": 0, "pre": 0} for a_ in ARMS if a_ != "P3"}
                gaps = []
                for r in sel:
                    legs, sale, gap = arm_legs(W, M, BARS, int(r), p)
                    if legs is None:
                        continue
                    if np.isfinite(gap):
                        gaps.append(gap)
                    ts, sx = sale
                    for a_, lg in legs.items():
                        if lg is None:
                            continue
                        acc[a_]["feas"] += 1
                        tb, px = lg
                        if ts <= tb:
                            acc[a_]["pre"] += 1; continue
                        acc[a_]["g"].append(sx / px - 1.0)
                res = {}
                for a_, v in acc.items():
                    ent = len(v["g"]) > 0
                    g = float(np.mean(v["g"])) if ent else np.nan
                    res[a_] = {"選出檔數": len(sel), "可買檔數": v["feas"], "買前已出場檔數": v["pre"], "進場檔數": len(v["g"]), "進場": ent,
                               "毛報酬": g, "報酬": ((1 + g) * (1 - cost) - 1) if ent else np.nan}
                # 對帳 P主 ＝ v1
                v1n = DAY[cd]["主"]["net"][p] if DAY[cd]["n"][p] > 0 else np.nan
                if res["P主"]["進場檔數"] != DAY[cd]["n"][p] or (np.isfinite(v1n) != np.isfinite(res["P主"]["報酬"])) or (np.isfinite(v1n) and abs(v1n - res["P主"]["報酬"]) > 1e-12):
                    mism += 1
                hm = res["P主"]["報酬"] if res["P主"]["進場"] else 0.0
                h1 = res["P1"]["報酬"] if res["P1"]["進場"] else 0.0
                ent3 = res["P主"]["進場"] or res["P1"]["進場"]
                res["P3"] = {"選出檔數": len(sel), "可買檔數": np.nan, "買前已出場檔數": np.nan, "進場檔數": res["P主"]["進場檔數"] + res["P1"]["進場檔數"],
                             "進場": ent3, "毛報酬": np.nan, "報酬": (0.5 * hm + 0.5 * h1) if ent3 else np.nan, "P3 後半留現金": not res["P1"]["進場"]}
                for a_ in ARMS:
                    AROWS.append({"世界": wn, "段": sg, "候選": cd, "日期": str(cal[p].date()), "指數報酬": float(EV["r"][i]), "買法": a_,
                                  "跳空（t＋1開÷t收−1，P主可買檔平均）": (float(np.mean(gaps)) if gaps else np.nan), **res[a_]})
        S["閘"][wn]["買法 P主 ≠ v1 主出場（事件×格）"] = mism
        log(f"[買法 {wn}] P主 對帳 v1 不符 {mism}｜{time.time() - T0:.0f}s")
        if mism:
            raise SystemExit(f"⛔ {wn} 買法 P主 與 v1 不符 {mism}")
        if wn == "主":
            S["世界尾後的接受事件（只列、不算）"] = {k: [str(df['date'].iloc[i].date()) for i in np.flatnonzero(EV["ACC"][k]) if df["date"].iloc[i] > cal[-1]] for k in V1.DEFS}
            S["個股快照尾"] = str(cal[-1].date())
        del M, DAY, MEMB, PK, BARS
    ER = pd.DataFrame(ROWS); CE = pd.DataFrame(CELLS); PO = pd.DataFrame(PORT); AR = pd.DataFrame(AROWS)
    # ═══ 主表＋判語（同 v1 口徑；C＋ 新格）═══
    m = CE[(CE["定義"] == "q2") & (CE["出場"] == "主")].merge(PO, on=["世界", "段", "候選"], how="left")
    verdict = {}
    for cd in CANDS3:
        if cd == "A":
            verdict[cd] = "基準（不判）"; continue
        conds = []
        for sg in V1.MAIN_SEGS:
            r_ = m[(m["候選"] == cd) & (m["段"] == sg)]
            if (not len(r_)) or ("配對差平均" not in r_.columns) or (not np.isfinite(r_["配對差平均"].iloc[0])) or (not np.isfinite(r_["②年化減0050"].iloc[0])):
                conds.append((sg, False, "無進場事件")); continue
            r_ = r_.iloc[0]
            c1 = r_["配對差平均"] > 0; c2 = r_["②年化減0050"] >= 0; c3 = r_["②比值減0050"] >= 0
            conds.append((sg, bool(c1 and c2 and c3), f"配對差 {r_['配對差平均']:+.4f}{'✔' if c1 else '✘'}｜②年化差 {r_['②年化減0050']:+.4f}{'✔' if c2 else '✘'}｜②比值差 {r_['②比值減0050']:+.3f}{'✔' if c3 else '✘'}"))
        verdict[cd] = {"判語": "方向一致（暫定）" if all(c[1] for c in conds) else "方向不一致", "逐段": {c[0]: c[2] for c in conds}}
        if cd == "F":
            fr_ = ER[(ER["定義"] == "q2") & (ER["出場"] == "主") & (ER["候選"] == "F") & ER["段"].isin(V1.MAIN_SEGS)]
            nfull = int((fr_["選出檔數"] >= 5).sum())
            verdict[cd]["足額事件（≥5 檔）"] = nfull
            verdict[cd]["候選不足事件"] = int(fr_["候選不足（F ＜5）"].sum())
            if nfull == 0:
                verdict[cd]["判語"] += "——⚠ 退化：兩主段每個事件都候選不足（0～4 檔），實質是 1～4 檔個股、照實報"
    verdict["C+"]["必附"] = "從約 10 個描述變體中挑出（逆勢漲三種、逐筆拆解、加碼營量營飆持股三種、營收條件兩種）；看過後才挑，最多暫定"
    m["方向判語（兩主段）"] = m["候選"].map(lambda c: verdict[c] if isinstance(verdict[c], str) else verdict[c]["判語"])
    m["_s"] = m["段"].map({"2006～2014": 0, "2015～2021": 1, "2022～": 2}); m["_c"] = m["候選"].map(CANDS3.index)
    m = m.sort_values(["_c", "_s"]).drop(columns=["_s", "_c"])
    keep = ["段", "候選", "指數事件數（接受、段內）", "進場事件數", "等效獨立事件數", "平均報酬", "中位報酬", "勝率", "同期0050平均（配對、含成本）",
            "配對差平均", "配對差中位", "X較好比例", "平均持有天數", "最長持有天數", "有窗尾未出場的事件數", "平均籃子檔數",
            "隨機平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落", "①比值", "②平時0050換20%_年化", "②最大回落", "②比值",
            "一直抱0050_年化", "一直抱0050_最大回落", "一直抱0050_比值", "②年化減0050", "②比值減0050", "方向判語（兩主段）", "候選不足事件數（＜5，含 0）", "0 檔事件數"]
    MT = m[[c for c in keep if c in m.columns]]
    # ═══ 買法彙總 ═══
    AS = []
    for cd in ARM_CANDS:
        for sg in ["2006～2014", "2015～2021", "2022～", "全部"]:
            sub = AR[(AR["候選"] == cd) & ((AR["段"] == sg) if sg != "全部" else True)]
            if not len(sub):
                continue
            mn = sub[sub["買法"] == "P主"].set_index("日期")
            gp = mn["跳空（t＋1開÷t收−1，P主可買檔平均）"].astype(float)
            for a_ in ARMS:
                q = sub[sub["買法"] == a_].set_index("日期")
                ev_n = len(q); ent = q[q["進場"].astype(bool)]
                v = ent["報酬"].astype(float).to_numpy()
                both = ent.index.intersection(mn[mn["進場"].astype(bool)].index)
                dif = (q.loc[both, "報酬"].astype(float) - mn.loc[both, "報酬"].astype(float)).to_numpy()
                v0 = np.where(q["進場"].astype(bool), q["報酬"].astype(float).fillna(0.0), 0.0)
                pre_ev = int(((~q["進場"].astype(bool)) & (q["可買檔數"].fillna(0) > 0)).sum()) if a_ != "P3" else int((~q["進場"].astype(bool)).sum())
                AS.append({"候選": cd, "名稱": CN3[cd], "段": sg, "買法": a_, "買法說明": AN[a_], "事件數": ev_n, "進場事件數": len(ent),
                           "未進場事件數（買前已收復）": pre_ev, "未進場事件數（全部原因）": int(ev_n - len(ent)),
                           "平均報酬": float(v.mean()) if len(v) else np.nan, "中位報酬": float(np.median(v)) if len(v) else np.nan,
                           "勝率": float(np.mean(v > 0)) if len(v) else np.nan, "最差": float(v.min()) if len(v) else np.nan,
                           "平均報酬（未進場記0）": float(v0.mean()) if ev_n else np.nan,
                           "對P主差_平均（兩臂都進場）": float(dif.mean()) if len(dif) else np.nan, "對P主差_中位": float(np.median(dif)) if len(dif) else np.nan,
                           "對P主差_較好比例": float(np.mean(dif > 0)) if len(dif) else np.nan, "比較事件數": len(dif),
                           "可買比例（檔）": (float(q["可買檔數"].sum() / q["選出檔數"].sum()) if (a_ != "P3" and q["選出檔數"].sum()) else np.nan),
                           "跳空中位（t＋1開÷t收−1）": float(np.nanmedian(gp)) if np.isfinite(gp).any() else np.nan,
                           "跳空平均": float(np.nanmean(gp)) if np.isfinite(gp).any() else np.nan})
    AS = pd.DataFrame(AS)
    AS["_c"] = AS["候選"].map(ARM_CANDS.index); AS["_s"] = AS["段"].map(SEG_ORDER); AS["_a"] = AS["買法"].map(ARMS.index)
    AS = AS.sort_values(["_c", "_s", "_a"]).drop(columns=["_c", "_s", "_a"])
    # ═══ 最壞情況（q2 主出場）═══
    q2m = ER[(ER["定義"] == "q2") & (ER["出場"] == "主") & (ER["進場"] == True)].copy()   # noqa: E712
    evq = EVT[(EVT["定義"] == "q2")].set_index("日期")
    q2m["指數收復等待（指數交易日）"] = q2m["日期"].map(evq["收復等待（指數交易日）"])
    WS = []; TOP = []
    for cd in CANDS3:
        for sg in ["2006～2014", "2015～2021", "2022～", "全部"]:
            sub = q2m[(q2m["候選"] == cd) & ((q2m["段"] == sg) if sg != "全部" else True)]
            if not len(sub):
                continue
            iw = sub["等待交易日（買進到賣完）"].astype(int).idxmax(); idp = sub["持有中最低相對買價"].astype(float).idxmin()
            WS.append({"候選": cd, "名稱": CN3[cd], "段": sg, "進場事件數": len(sub),
                       "最長等待交易日": int(sub.loc[iw, "等待交易日（買進到賣完）"]), "最長等待事件": sub.loc[iw, "日期"],
                       "等待交易日中位": float(sub["等待交易日（買進到賣完）"].median()),
                       "最深帳面跌幅": float(sub.loc[idp, "持有中最低相對買價"]), "最深跌幅事件": sub.loc[idp, "日期"],
                       "帳面跌幅中位": float(sub["持有中最低相對買價"].median()), "帳面曾跌超過10%事件數": int((sub["持有中最低相對買價"] < -0.10).sum()),
                       "有窗尾未出場事件數": int((sub["窗尾未出場比例"].fillna(0) > 0).sum())})
        sub = q2m[q2m["候選"] == cd].sort_values(["持有中最低相對買價", "日期"])
        for rk, (_, r_) in enumerate(sub.head(3).iterrows(), 1):
            TOP.append({"候選": cd, "名稱": CN3[cd], "名次": rk, "日期": r_["日期"], "段": r_["段"], "指數當日跌幅": r_["指數報酬"],
                        "等待交易日（買進到賣完）": int(r_["等待交易日（買進到賣完）"]), "指數收復等待（指數交易日）": r_["指數收復等待（指數交易日）"],
                        "最深帳面跌幅": float(r_["持有中最低相對買價"]), "最深日": r_["最深帳面跌幅日"], "最後報酬（淨）": float(r_["報酬"]),
                        "持有中最大回落（高點起）": float(r_["持有中最大回落"]), "窗尾未出場比例": float(r_["窗尾未出場比例"]), "賣完日": r_["賣完日"]})
    WS = pd.DataFrame(WS); TOP = pd.DataFrame(TOP)
    # ═══ 存檔 ═══
    MT.to_csv(os.path.join(OUT, "main_table.csv"), index=False, float_format="%.6g", encoding="utf-8")
    CE.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.6g", encoding="utf-8")
    ER.to_csv(os.path.join(OUT, "event_rows.csv"), index=False, float_format="%.10g", encoding="utf-8")
    PO.to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EVT.to_csv(os.path.join(OUT, "events.csv"), index=False, float_format="%.10g", encoding="utf-8")
    pd.DataFrame(RND).to_csv(os.path.join(OUT, "random.csv.gz"), index=False, float_format="%.6g")
    AR.to_csv(os.path.join(OUT, "buyarm_rows.csv"), index=False, float_format="%.12g", encoding="utf-8")
    AS.to_csv(os.path.join(OUT, "buyarms.csv"), index=False, float_format="%.6g", encoding="utf-8")
    WS.to_csv(os.path.join(OUT, "worst.csv"), index=False, float_format="%.6g", encoding="utf-8")
    TOP.to_csv(os.path.join(OUT, "worst_top3.csv"), index=False, float_format="%.6g", encoding="utf-8")
    # ═══ 對帳 v1（A～F）═══
    REC = []
    for fn, cmpz in (("cells.csv", None), ("portfolio.csv", None), ("event_rows.csv", None), ("main_table.csv", None), ("events.csv", None), ("random.csv.gz", "gzip")):
        a_ = pd.read_csv(os.path.join(V1OUT, fn), dtype=str, keep_default_na=False)
        b_ = pd.read_csv(os.path.join(OUT, fn), dtype=str, keep_default_na=False)
        if "候選" in b_.columns:
            b_ = b_[b_["候選"] != "C+"].reset_index(drop=True)
        extra = ""
        if fn == "events.csv":                    # 指數資料比 v1 新（多出世界尾後的事件列）⇒ 以 v1 的（定義, 日期）對齊
            kb = set(zip(a_["定義"], a_["日期"]))
            ex_ = b_[[(d, t) not in kb for d, t in zip(b_["定義"], b_["日期"])]]
            extra = "；".join(f"{d} {t} {j}" for d, t, j in zip(ex_["定義"], ex_["日期"], ex_["判定"]))
            b_ = a_[["定義", "日期"]].merge(b_, on=["定義", "日期"], how="left").fillna("")
        miss_cols = [c for c in a_.columns if c not in b_.columns]
        b_ = b_[[c for c in a_.columns if c in b_.columns]]
        same_shape = a_.shape == b_.shape and not miss_cols
        neq = int((a_.values != b_.values).sum()) if same_shape else -1
        mx = 0.0
        if same_shape and neq:
            for c in a_.columns:
                x = pd.to_numeric(a_[c], errors="coerce"); y = pd.to_numeric(b_[c], errors="coerce")
                d = (x - y).abs() / np.maximum(1.0, y.abs())
                if d.notna().any():
                    mx = max(mx, float(d.max()))
        REC.append({"檔": fn, "v1 列": len(a_), "v3（去 C＋）列": len(b_), "欄位缺": " ".join(miss_cols), "同形狀": same_shape, "逐字不同格數": neq, "數值最大相對差": mx,
                    "v3 多出的列（v1 沒有）": extra})
    REC = pd.DataFrame(REC)
    REC.to_csv(os.path.join(OUT, "recon_v1.csv"), index=False, encoding="utf-8")
    vj = v1j["方向判語"]
    S["對帳 v1"] = {"檔": REC.to_dict("records"), "判語 A～F 與 v1 相同": all(json.dumps(verdict[c], ensure_ascii=False, sort_keys=True) == json.dumps(vj[c], ensure_ascii=False, sort_keys=True) for c in V1.CANDS_ORIG)}
    log("[對帳 v1]\n" + REC.to_string(index=False) + f"\n判語相同 {S['對帳 v1']['判語 A～F 與 v1 相同']}")
    # 對帳 yl C＋
    try:
        Y = pd.read_csv(YLMAIN); Y = Y[Y["候選"] == "C+"]
        cols = ["平均報酬", "中位報酬", "勝率", "配對差平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落"]
        mx = 0.0
        for sg in ("2006～2014", "2015～2021", "2022～"):
            a1 = MT[(MT["候選"] == "C+") & (MT["段"] == sg)].iloc[0]; b1 = Y[Y["段"] == sg].iloc[0]
            mx = max(mx, max(abs(float(a1[c]) - float(b1[c])) / max(1.0, abs(float(b1[c]))) for c in cols))
        S["對帳 yl C＋（q2 主出場，6 位有效）"] = {"欄": cols, "最大相對差": mx}
        log(f"[對帳 yl C＋] 最大相對差 {mx:.2e}")
    except Exception as ex:                                          # noqa: BLE001
        S["對帳 yl C＋（q2 主出場，6 位有效）"] = f"讀不到：{ex}"
    S["方向判語"] = verdict
    S["主表"] = MT.to_dict("records")
    S["買法四臂"] = AS.to_dict("records")
    S["最壞情況"] = WS.to_dict("records"); S["最慘3事件"] = TOP.to_dict("records")
    S["窗尾未出場（主出場）"] = ER[(ER["出場"] == "主") & (ER["窗尾未出場比例"].fillna(0) > 0)][["世界", "定義", "候選", "日期", "窗尾未出場比例", "報酬"]].to_dict("records")
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_v3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 300)
    log("[主表 q2 主出場]\n" + MT[["段", "候選", "進場事件數", "平均報酬", "中位報酬", "勝率", "同期0050平均（配對、含成本）", "配對差平均", "X較好比例", "實際減隨機", "p（隨機 ≥ 實際）",
                                "①只在事件進場_年化", "①最大回落", "②平時0050換20%_年化", "②最大回落", "②年化減0050", "②比值減0050", "方向判語（兩主段）"]].to_string())
    log(f"[判語] {json.dumps(verdict, ensure_ascii=False)}")
    log("[買法]\n" + AS[["候選", "段", "買法", "事件數", "進場事件數", "未進場事件數（買前已收復）", "平均報酬", "中位報酬", "勝率", "平均報酬（未進場記0）",
                       "對P主差_平均（兩臂都進場）", "對P主差_中位", "可買比例（檔）", "跳空中位（t＋1開÷t收−1）"]].to_string(index=False))
    log("[最壞]\n" + WS.to_string(index=False))
    log("[最慘3]\n" + TOP.to_string(index=False))
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    sys.path.insert(0, REPO)
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchMktDrop_v1 as V1
    V1.CANDS_ORIG = list(V1.CANDS)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

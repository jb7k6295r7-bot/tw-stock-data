# -*- coding: utf-8 -*-
"""PREREG大盤大跌後買什麼 seq1（裁定 seq352 發號、N_組合 ＋1；登錄 sha 94852550bcc7e70a）——回測線計算子代理，2026-10-15。
⚠ 已看過初測（researchMktDrop.py／resultsMktDrop/）⇒ 事後重切、最多暫定；判語只到方向（一致／不一致）；合格只看前瞻（事件累計 ≥ 10 次判一次）。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（初測程式只 import 重用）；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_v1 [--procs 4]
    前瞻判定（輕量、只讀指數）： ... -m backtest.researchMktDrop_v1 --judge 2026-10-16 [--write]

═══ 照登錄（逐條）＋執行者補的讀法（第一次跑之前寫死，2026-10-15 22:55 台北）═══
 一、事件：r(t) ＝ 公開庫 data/history/market_index.csv（git show origin/main，sha 記在 json）收盤 ÷ 前一列收盤 − 1
    q(t) ＝ 2005-01-03～t−1 所有交易日 r 的第 2 百分位（擴張視窗、線性內插＝numpy 預設）；視窗 ＜ 250 筆不判
    事件 ＝ r(t) ≤ q(t) ∧ 前 20 個指數交易日（列）內沒有別的 r ≤ q 的日子（執行者讀法：「別的事件日」＝原始 r ≤ q 日，與初測同）
    ⭐ 同時只處理一個事件：已接受事件 t0 的部位持有到「指數收復日 D（收盤 ≥ t0−1 收盤）的隔天開盤」；新事件 t ≤ D ⇒ 不加碼、記「持有中又遇事件」
       （執行者讀法：鎖以指數主出場為準、六格共用、跨早年／主世界連續；D 不存在＝一直持有）
    描述（⛔ 不判）：固定 r ≤ −2%、≤ −3%（同起算期：q(t) 可算的日子起）；門檻改最低 1%；同去重、同鎖
 二、候選（t 收盤決定、t＋1 開盤買、等權）：A 0050；B 00631L（早年段 ⛔ 不算）；
    C／D ＝ 事件日 R1 母體報酬最低／最高 ceil(10%) 檔（R1 ＝ 營量營飆同閘 patterns.Frame.gate ∧ pit_valid ∧ 四碼普通股 ∧ 含已下市 ∧ 前 20 根無壞根；
          母體 ＜ 20 檔不排——與初測同，執行者補）
    E ＝ 事件日母體成員 ≥ 5 檔的產業（industry_pit pit 版＋營收彙總表後備；排「其他」「存託憑證」「ETF」與無產業——執行者補、與初測同）中
          等權報酬最差的 2 個，兩產業的 R1 股合併等權（執行者讀法）
    F ＝ 事件日營量 v1 正式訊號（research11 主格 5 取 3 ∧ 去重 20 根 ∧ research13.and_flags 營收 24 月新高；⭐ 只「已達成」，⛔ 不含初測加的「即將達成」）等權；
          候選 ＜ 5 檔 ⇒ 記「候選不足」、照實報（1～4 檔仍照買照算；0 檔 ⇒ 該事件 F 不進場）
    買不到（隔天沒成交、開盤漲停鎖死、隔天是壞根）⇒ 剔除、比例照報
 三、出場：主 ＝ 加權收盤 ≥ 事件日前一日收盤的第一天 D ⇒ D 之後第一根可賣開盤全賣（鎖跌停順延）；⛔ 不設天數；未觸發 ⇒ 窗尾收盤計值、列「窗尾仍持有」
    描述出場（⛔ 不判）：副1 收盤跌破自身 MA20（執行者讀法＝自進場根起先收盤 ≥ MA20、之後第一根收盤 ＜ MA20，同初測）；副2 自買進後最高收盤回落 3×ATR20
    個股持有中遇壞根（缺口 ≥ 5 日，seq335）⇒ 壞根前一根收盤強制賣；下市 ⇒ 最後交易日收盤賣
 四、比較：事件層 ＝ 每事件 X 淨報酬 − 配對 0050（籃內每檔換成 0050、同一天開盤買、同一時點賣，⭐ 扣 ETF 成本 0.385%）；平均、中位、X 較好比例
    組合層 ① 只在事件進場、其餘現金（連續資金曲線，在場日 ＝ 當天在場各筆日報酬等權平均）
           ② 平時抱 0050；事件 t＋1 開盤把淨值 20% 換成 X（扣 X 來回成本＋0050 來回 0.385%），全籃賣完那一刻換回 0050（開盤賣 ⇒ 開盤換回；收盤賣 ⇒ 收盤換回）；
             A 的 ② ≡ 一直抱 0050（換自己＝不動）
           曲線各世界連續（早年世界 2004-02～2014-12、主世界 2015-01～2026-09-24），按段切；年化／最大回落 ＝ research13.window_stats（同 0050 一直抱口徑）；
           比值 ＝ 年化 ÷ |最大回落|（rerun17 口徑）
    段：早年 2006～2014｜2015～2021｜2022～資料尾（個股快照 2026-09-24）
    方向一致 ＝ 兩個主段都：事件層平均配對差 ＞ 0 ∧ ② 年化 ≥ 一直抱 0050 ∧ ② 比值 ≥ 一直抱 0050；否則不一致（A 是基準、不判）
 五、必報：事件清單（日、跌幅、門檻、收復等待、持有中又遇事件數）；等效獨立事件數（n²÷(n＋2Pρ)，同初測）；每格每事件報酬、持有天數、持有中最大跌幅；
    窗尾未出場清單；隨機日 200 次（同年、非原始事件日、同主出場、同候選；統計＝每筆平均淨報酬；p ＝ 隨機 ≥ 實際的比例）
    成本 個股 0.585%、ETF 0.385%（0.1425%×2＋0.1%）；未含滑價
 裁定 seq352 加：描述對照「正2 一直抱同窗」（⛔ 不改判語）；結果句加「正2 的結果含槓桿本身的效果」
 前瞻：backtest/forward/mktdrop/（events.csv、positions.csv；只追加）；2026-10-15 若符合 ⇒ 第 0 筆（描述、不入判）；10/16 起入判
── 事後註（照實記）──
 ① 22:55 第一次全跑：配對 0050 在 0050 停牌日（2025-06 分割）開盤是 NaN ⇒ 描述出場 2022～ 幾格配對差 NaN；改成停牌日用前一日收盤（與 ② 曲線同口徑）重跑；
    另外 F 判語加「足額事件數」與退化標記、主表排序——⛔ 事件、候選、出場、判語規則都沒改
輸出 backtest/resultsMktDrop/v1/：MktDrop_v1.json、main_table.csv、cells.csv、events.csv、event_rows.csv、portfolio.csv、random.csv.gz、run.log；大檔 ~/mktdropwork/v1/
"""
from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import math
import os
import pickle
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/v1")
WORK = os.path.expanduser("~/mktdropwork/v1")
FWD = os.path.join(REPO, "backtest/forward/mktdrop")
INIT_EVENTS = os.path.join(REPO, "backtest/resultsMktDrop/events.csv")
REG = {"件": "PREREG大盤大跌後買什麼 seq1", "sha": "94852550bcc7e70a", "裁定": "seq352（N_組合 ＋1）"}
TIME = "2026-10-15 22:55（台北；讀法寫死、第一次跑之前）"
WIN0 = pd.Timestamp("2005-01-03")
MINWIN = 250
DEDUP = 20
ANN = 245
NRAND = 200
RSEED = 2026101501
W_SLEEVE = 0.20
COST_STK, COST_ETF = 0.00585, 0.00385
CANDS = ["A", "B", "C", "D", "E", "F"]
CN = {"A": "0050", "B": "00631L 正2", "C": "當天跌最多一成", "D": "當天最抗跌一成", "E": "跌最多兩個產業", "F": "營量v1 正式訊號（已達成）"}
EXITS = ["主", "副1", "副2"]
EN = {"主": "加權收復大跌前一日收盤 ⇒ 隔天開盤賣（不設天數）", "副1": "跌破自身 MA20（描述）", "副2": "買進後最高收盤回落 3×ATR20（描述）"}
DEFS = ["q2", "q1", "f2", "f3"]
DN = {"q2": "擴張視窗最低 2%（主）", "q1": "最低 1%（描述）", "f2": "固定 ≤ −2%（描述）", "f3": "固定 ≤ −3%（描述）"}
SEGS_V1 = {"早年": {"2006～2014": ("2006-01-01", "2014-12-31")},
           "主": {"2015～2021": ("2015-01-01", "2021-12-31"), "2022～": ("2022-01-01", None)}}
MAIN_SEGS = ["2015～2021", "2022～"]
FWD_START = "2026-10-16"          # 裁定 seq352（10/15 22:43）後第一個交易日
FWD0_DATE = "2026-10-15"          # 第 0 筆（描述、不入判）
NOTES = ["看過初測才登錄，最多暫定",
         "事件約每年 1 次，樣本很少",
         "收復才賣的勝率有一部分來自規則本身（等多久都等）",
         "正2 的結果含槓桿本身的效果",
         "早年（2006～2014）含減資假飆股約 0.3%（剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；2005-01～2007-06 只有上市",
         "判語只到方向（一致／不一致）；⛔ 不給合格；合格只看前瞻（事件累計 ≥ 10 次判一次）",
         "⚠ 個股急跌錯殺五刀已封存（seq340）；本件以大盤事件日為準，不是重切同一批",
         "成本：個股 0.585% 來回、ETF 0.385%；未含滑價；⛔ 不是買賣建議"]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def qtl(srt, p):
    m = len(srt); x = p * (m - 1); lo = int(math.floor(x)); hi = min(lo + 1, m - 1)
    return srt[lo] + (x - lo) * (srt[hi] - srt[lo])


# ═════════════ 指數（輕量；前瞻判定也用這段）═════════════
def read_index(sha=None):
    if sha is None:
        sha = subprocess.run(["git", "-C", REPO, "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    raw = subprocess.run(["git", "-C", REPO, "show", f"{sha}:data/history/market_index.csv"], capture_output=True, check=True).stdout
    df = pd.read_csv(io.BytesIO(raw), dtype={"date": str})
    df["date"] = pd.to_datetime(df["date"]); df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    return sha, df


def index_events(df):
    """⇒ dict：r、q2、q1、RAW、FIRST、rec（收復列；−1 ＝ 未收復）、ACC（接受）、BLK（持有中又遇事件 ⇒ 被哪個接受事件擋）。"""
    d = df["date"].to_numpy(); cl = df["close"].to_numpy(float); n = len(cl)
    r = np.r_[np.nan, cl[1:] / cl[:-1] - 1.0]
    inwin = (df["date"] >= WIN0).to_numpy() & np.isfinite(r)
    q2 = np.full(n, np.nan); q1 = np.full(n, np.nan); srt = []
    for i in range(n):
        if inwin[i] and len(srt) >= MINWIN:
            q2[i] = qtl(srt, 0.02); q1[i] = qtl(srt, 0.01)
        if inwin[i]:
            bisect.insort(srt, r[i])
    ok = np.isfinite(q2)
    with np.errstate(invalid="ignore"):
        RAW = {"q2": ok & (r <= q2), "q1": ok & (r <= q1), "f2": ok & (r <= -0.02), "f3": ok & (r <= -0.03)}
    FIRST = {}
    for k, m in RAW.items():
        cs = np.r_[0, np.cumsum(m)]
        lo = np.maximum(np.arange(n) - DEDUP, 0)
        FIRST[k] = m & ((cs[np.arange(n)] - cs[lo]) == 0)
    rec = np.full(n, -1, np.int64)
    for k in FIRST:
        for t in np.flatnonzero(FIRST[k]):
            if rec[t] != -1 or t == 0:
                continue
            hit = np.flatnonzero(cl[t + 1:] >= cl[t - 1])
            rec[t] = t + 1 + int(hit[0]) if len(hit) else -2
    rec[rec == -2] = -1
    ACC = {}; BLK = {}
    for k in FIRST:
        acc = np.zeros(n, bool); blk = np.full(n, -1, np.int64); hold_until = -1; cur = -1
        for t in np.flatnonzero(FIRST[k]):
            if t <= hold_until:
                blk[t] = cur
                continue
            acc[t] = True; cur = t
            hold_until = int(rec[t]) if rec[t] >= 0 else 10 ** 9
        ACC[k] = acc; BLK[k] = blk
    return {"df": df, "cl": cl, "r": r, "q2": q2, "q1": q1, "RAW": RAW, "FIRST": FIRST, "rec": rec, "ACC": ACC, "BLK": BLK, "n": n}


def thr_of(EV, k, i):
    return float(EV[k][i]) if k in ("q2", "q1") else (-0.02 if k == "f2" else -0.03)


def judge_date(date, df=None, sha=None, k="q2"):
    """前瞻每日判定（只讀指數）：date 是否為事件日。⇒ dict（狀態：資料未到／事件／非事件／持有中又遇事件）。"""
    if df is None:
        sha, df = read_index(sha)
    dt = pd.Timestamp(date)
    EV = index_events(df)
    dd = df["date"]; cl = EV["cl"]; r = EV["r"]
    out = {"日期": str(dt.date()), "指數 sha": sha, "指數資料尾": str(dd.iloc[-1].date())}
    # 持有中：最後一個接受事件（截至 date 之前）
    prev = np.flatnonzero(EV["ACC"][k] & (dd < dt).to_numpy())
    holding = None
    if len(prev):
        t0 = int(prev[-1]); rc = int(EV["rec"][t0])
        rec_before = rc >= 0 and dd.iloc[rc] < dt
        holding = {"上一個接受事件": str(dd.iloc[t0].date()), "收復目標（事件前一日收盤）": float(cl[t0 - 1]),
                   "收復日": (str(dd.iloc[rc].date()) if rc >= 0 else None), "date 當天仍持有": bool(not rec_before)}
    out["持有狀態"] = holding
    if (dd == dt).any():
        i = int(np.flatnonzero((dd == dt).to_numpy())[0])
        q = thr_of(EV, k, i)
        raw = bool(EV["RAW"][k][i]); first = bool(EV["FIRST"][k][i])
        st = "非事件" if not raw else ("同波段（前 20 日內已有）" if not first else ("持有中又遇事件" if EV["BLK"][k][i] >= 0 else "事件"))
        out.update({"狀態": st, "收盤": float(cl[i]), "前一日收盤": float(cl[i - 1]), "指數報酬": float(r[i]), "門檻": q})
        return out
    # 資料未到：以資料尾為「前一交易日」算 date 適用門檻（假設 date 是資料尾的下一個交易日）
    wr = r[(dd >= WIN0).to_numpy() & np.isfinite(r)]
    srt = sorted(wr.tolist())
    q = qtl(srt, 0.02 if k == "q2" else 0.01) if k in ("q2", "q1") else (-0.02 if k == "f2" else -0.03)
    last20 = bool(EV["RAW"][k][-DEDUP:].any())
    out.update({"狀態": "資料未到", "前一日收盤（資料尾）": float(cl[-1]), "適用門檻（假設 date＝資料尾下一交易日）": float(q),
                "觸發點位（收盤 ≤）": float(cl[-1] * (1 + q)), "前 20 日內已有原始事件": last20})
    return out


# ═════════════ 前瞻紀錄格式（只追加）═════════════
FWD_EV_COLS = ["序號", "事件日", "入判", "指數收盤", "前一日收盤（收復目標）", "指數報酬", "門檻q", "判定", "買進日", "收復日", "賣出日", "狀態", "指數sha", "寫入時間"]
FWD_POS_COLS = ["序號", "事件日", "候選", "代號", "名稱", "買進日", "買進價", "出場條件", "出場日", "出場價", "出場種類", "報酬", "狀態", "備註", "寫入時間"]
FWD_EXIT = "加權收盤 ≥ 事件前一日收盤 ⇒ 隔天開盤全賣；⛔ 不設天數；個股遇壞根前一根收盤強制賣、下市最後收盤"


def fwd_init():
    os.makedirs(FWD, exist_ok=True)
    for fn, cols in (("events.csv", FWD_EV_COLS), ("positions.csv", FWD_POS_COLS)):
        p = os.path.join(FWD, fn)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerow(cols)


def _append(fn, cols, rows):
    fwd_init()
    p = os.path.join(FWD, fn)
    with open(p, encoding="utf-8-sig") as f:
        head = next(csv.reader(f))
    if head != cols:
        raise SystemExit(f"⛔ {p} 表頭不同：{head}")
    with open(p, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        for r_ in rows:
            bad = set(r_) - set(cols)
            if bad:
                raise SystemExit(f"⛔ 多出欄位 {bad}")
            w.writerow({c: r_.get(c, "") for c in cols})


def fwd_append_event(row):
    """一列事件（狀態：待買／持有中／已出場；入判：否＝第 0 筆描述，是＝10/16 起）。⛔ 已寫入的列不改。"""
    _append("events.csv", FWD_EV_COLS, [row])


def fwd_append_positions(rows):
    """事件 × 候選 × 代號（ETF 一列；C～F 每檔一列；F 候選 ＜ 5 備註「候選不足」）。⛔ 已寫入的列不改。"""
    _append("positions.csv", FWD_POS_COLS, rows)


def fwd_next_seq():
    p = os.path.join(FWD, "events.csv")
    if not os.path.exists(p):
        return None
    ev = pd.read_csv(p, encoding="utf-8-sig", dtype=str)
    return 0 if not len(ev) else int(pd.to_numeric(ev["序號"]).max()) + 1


def fwd_judge_and_record(date, write=False):
    """每日呼叫：判定 date；是事件且 write ⇒ 追加 events.csv 一列（候選清單另由 fwd_append_positions 在 t＋1 開盤後填）。"""
    J = judge_date(date)
    if write and J["狀態"] in ("事件", "持有中又遇事件"):
        p = os.path.join(FWD, "events.csv")
        ev = pd.read_csv(p, encoding="utf-8-sig", dtype=str) if os.path.exists(p) else pd.DataFrame(columns=FWD_EV_COLS)
        if (ev["事件日"] == J["日期"]).any():
            J["寫入"] = "已有、不重寫"; return J
        seq = 0 if J["日期"] == FWD0_DATE else max(1, (fwd_next_seq() or 1))
        fwd_append_event({"序號": seq, "事件日": J["日期"], "入判": ("否（第 0 筆描述）" if seq == 0 else ("是" if J["狀態"] == "事件" else "否（持有中又遇事件）")),
                          "指數收盤": J["收盤"], "前一日收盤（收復目標）": J["前一日收盤"], "指數報酬": J["指數報酬"], "門檻q": J["門檻"], "判定": J["狀態"],
                          "狀態": ("待買" if J["狀態"] == "事件" else "不加碼"), "指數sha": J["指數 sha"], "寫入時間": now_tpe()})
        J["寫入"] = f"events.csv 序號 {seq}"
    return J


# ═════════════ 籃子與逐日統計 ═════════════
def basket(M, t, cd):
    """⇒ (買得到的列, 選出檔數, 產業標籤)。"""
    S = M["S"]
    if cd in ("A", "B"):
        r = S + (0 if cd == "A" else 1)
        return (np.array([r]) if M["BUY"][r, t] else np.array([], int)), (1 if M["BUY"][r, t] else 0), None
    if cd == "F":
        sel = np.flatnonzero(M["ACH"][:, t])
        return sel[M["BUY"][sel, t]], len(sel), None
    m = M["MEM"][:, t] & np.isfinite(M["RET"][:, t])
    rows = np.flatnonzero(m)
    if len(rows) < 20:
        return np.array([], int), 0, None
    v = M["RET"][rows, t]
    if cd in ("C", "D"):
        ns = int(np.ceil(0.10 * len(rows)))
        o = np.argsort(v, kind="stable")
        sel = rows[o[:ns]] if cd == "C" else rows[o[::-1][:ns]]
        return sel[M["BUY"][sel, t]], len(sel), None
    ic = M["IND"][rows, t]; ok = ic >= 0
    if not ok.any():
        return np.array([], int), 0, None
    df = pd.DataFrame({"i": ic[ok], "v": v[ok], "r": rows[ok]})
    g = df.groupby("i")["v"].agg(["mean", "count"]); g = g[g["count"] >= 5]
    if len(g) < 2:
        return np.array([], int), 0, None
    g = g.reset_index().sort_values(["mean", "i"], kind="stable")
    worst = [int(x) for x in g["i"].iloc[:2]]
    sel = df.loc[df["i"].isin(worst), "r"].to_numpy()
    return sel[M["BUY"][sel, t]], len(sel), "／".join(M["inds"][w] for w in worst)


def day_stats(W, M, log):
    n0 = W["n0"]; BC = W["BC"]
    BO = np.where(np.isfinite(W["BO"]) & (W["BO"] > 0), W["BO"], np.r_[np.nan, BC[:-1]])   # 0050 停牌日（2025-06 分割）開盤 ⇒ 前一日收盤
    out = {cd: {"n": np.zeros(n0, int), "nsel": np.zeros(n0, int), "ind": np.full(n0, None, object),
                **{x: {k: np.full(n0, np.nan) for k in ("net", "gross", "hold", "unex", "b50", "maxhold")} for x in EXITS}} for cd in CANDS}
    MEMB = {}
    for t in range(n0 - 1):
        e = t + 1
        for cd in CANDS:
            I, nsel, ind = basket(M, t, cd)
            o = out[cd]; o["n"][t] = len(I); o["nsel"][t] = nsel; o["ind"][t] = ind
            if not len(I):
                continue
            MEMB[(cd, t)] = I
            cost = COST_ETF if cd in ("A", "B") else COST_STK
            bp = M["BP"][I, t]
            for x in EXITS:
                sp = M["SP"][x][I, t].astype(np.int64); sx = M["SX"][x][I, t]; kd = M["SK"][x][I, t]
                gm = float(np.mean(sx / bp - 1.0))
                o[x]["gross"][t] = gm; o[x]["net"][t] = (1 + gm) * (1 - cost) - 1
                o[x]["hold"][t] = float(np.mean(sp - e)); o[x]["maxhold"][t] = float(np.max(sp - e)); o[x]["unex"][t] = float(np.mean(kd == 3))
                spc = np.minimum(sp, n0 - 1)
                bb = np.where(kd == 0, BO[spc], BC[spc])
                b0 = BO[e]
                o[x]["b50"][t] = (1 + float(np.mean(bb / b0 - 1.0))) * (1 - COST_ETF) - 1 if np.isfinite(b0) else np.nan
    log(f"[每日籃子 {W['name']}] " + "｜".join(f"{cd} 有籃日 {int((out[cd]['n'] > 0).sum())}" for cd in CANDS))
    return out, MEMB


def bpath(W, M, I, t, x):
    """⇒ (e, end, V 毛值路徑（相對買價、日收盤；已賣的檔固定在賣價）, 最後一批是否開盤賣)。"""
    n0 = W["n0"]; e = t + 1
    sp = M["SP"][x][I, t].astype(np.int64); sx = M["SX"][x][I, t]; bp = M["BP"][I, t]; kd = M["SK"][x][I, t]
    end = int(min(max(sp.max(), e), n0 - 1))
    P_ = M["C"][I, e:end + 1] / bp[:, None]
    tt = np.arange(e, end + 1)[None, :]
    P_ = np.where(tt >= sp[:, None], (sx / bp)[:, None], P_)
    V = np.nanmean(P_, axis=0)
    last = sp == sp.max()
    reopen = bool(np.all(kd[last] == 0))
    return e, end, V, reopen


def curve1(n0, paths, cost):
    sm = np.zeros(n0); ct = np.zeros(n0)
    for e, end, V, _ in paths:
        Vn = V * (1 - cost); r = Vn / np.r_[1.0, Vn[:-1]] - 1.0
        sm[e:end + 1] += np.nan_to_num(r); ct[e:end + 1] += 1
    R_ = np.where(ct > 0, sm / np.maximum(ct, 1), 0.0)
    return np.cumprod(1 + R_), ct > 0


def curve2(n0, paths, BO, BC, cost):
    """平時抱 0050；事件 t＋1 開盤換 20% 到 X；全籃賣完換回。⇒ (淨值曲線, 略過的重疊事件數)。"""
    by_e = {p[0]: p for p in paths}
    eq = np.ones(n0); core = 1.0; act = None; skipped = 0
    for j in range(1, n0):
        o_ = BO[j] if np.isfinite(BO[j]) and BO[j] > 0 else BC[j - 1]
        core *= o_ / BC[j - 1]
        if j in by_e:
            if act is None:
                e0, end, V, reopen = by_e[j]
                tot = core; core = tot * (1 - W_SLEEVE)
                act = (e0, end, V, reopen, tot * W_SLEEVE * (1 - cost) * (1 - COST_ETF))
            else:
                skipped += 1
        sl = 0.0
        if act is not None:
            e0, end, V, reopen, S0 = act
            if j == end and reopen:
                core += S0 * V[j - e0]
        core *= BC[j] / o_
        if act is not None:
            e0, end, V, reopen, S0 = act
            if j == end:
                if not reopen:
                    core += S0 * V[j - e0]
                act = None
            else:
                sl = S0 * V[j - e0]
        eq[j] = core + sl
    return eq, skipped


def wstats(eq, x0, y0):
    from backtest import research13 as R13
    c, m = R13.window_stats(np.asarray(eq, float), 0, len(eq), x0, y0 + 1)
    return {"年化": float(c), "最大回落": float(m), "比值": float(c / abs(m)) if m < 0 else np.nan}


def eff_n(vals, iv):
    n = len(vals)
    if n < 2:
        return float(n), np.nan, 0
    v = np.asarray(vals, float); d = v - v.mean(); var = float(np.mean(d ** 2))
    pairs = 0; acc = 0.0
    for a in range(n):
        for b in range(a + 1, n):
            if iv[a][0] <= iv[b][1] and iv[b][0] <= iv[a][1]:
                pairs += 1; acc += d[a] * d[b]
    if pairs == 0 or var == 0:
        return float(n), (np.nan if pairs == 0 else 0.0), pairs
    rho = float(np.clip(acc / (pairs * var), 0.0, 1.0))
    return float(n * n / (n + 2 * pairs * rho)), rho, pairs


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    from multiprocessing import Pool
    from backtest import researchMktDrop as MD      # 初測：只 import 重用（世界、逐股出場、矩陣、營量旗標）
    MD.SEGS = SEGS_V1
    S = {"件": REG, "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭（一～五）", "必附": NOTES, "候選": CN, "出場": EN, "事件定義": DN, "閘": {}}
    IXmd = MD.load_index(log)                    # 只用 rec（收復）建世界的 Darr；門檻用本件 index_events
    sha = IXmd["sha"]; df = IXmd["df"]
    EV = index_events(df)
    fr = np.flatnonzero(np.isfinite(EV["q2"]))[0]
    for k in DEFS:
        ft = np.flatnonzero(EV["FIRST"][k])
        if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
            raise SystemExit(f"⛔ {k} 收復列與初測 rec 不同")
    S["指數"] = {"origin/main sha": sha, "期間": f"{df['date'].iloc[0].date()}～{df['date'].iloc[-1].date()}",
                 "門檻起算": "2005-01-03", "第一個可判日": str(df["date"].iloc[fr].date())}
    # 事件清單
    rows = []
    for k in DEFS:
        for i in np.flatnonzero(EV["FIRST"][k]):
            rc = int(EV["rec"][i]); b = int(EV["BLK"][k][i])
            nblk = int(((EV["BLK"][k] == i)).sum()) if EV["ACC"][k][i] else None
            rows.append({"定義": k, "日期": str(df["date"].iloc[i].date()), "指數報酬": float(EV["r"][i]), "門檻": thr_of(EV, k, i),
                         "判定": "接受" if EV["ACC"][k][i] else "持有中又遇事件（不加碼）", "被誰擋": (str(df["date"].iloc[b].date()) if b >= 0 else None),
                         "收復日": (str(df["date"].iloc[rc].date()) if rc >= 0 else None),
                         "收復等待（指數交易日）": (rc - i if rc >= 0 else None), "未收復（到指數尾）": rc < 0,
                         "持有中又遇事件次數": nblk, "原始日數（波段內 20 日）": int(EV["RAW"][k][i:i + DEDUP + 1].sum())})
    EVT = pd.DataFrame(rows)
    S["事件數"] = {k: {"原始": int(EV["RAW"][k].sum()), "去重（波段第一天）": int(EV["FIRST"][k].sum()), "接受": int(EV["ACC"][k].sum()),
                     "持有中又遇事件": int((EV["BLK"][k] >= 0).sum())} for k in DEFS}
    log(f"[事件] {S['事件數']}")
    # 與初測事件清單比較
    try:
        E0 = pd.read_csv(INIT_EVENTS)
        o_ = set(E0[(E0["定義"] == "q2") & E0["波段第一天"]]["日期"])
        n_ = set(EVT[(EVT["定義"] == "q2")]["日期"]); n_acc = set(EVT[(EVT["定義"] == "q2") & (EVT["判定"] == "接受")]["日期"])
        S["與初測事件差（q2）"] = {"初測去重": len(o_), "本件去重": len(n_), "本件接受": len(n_acc),
                              "只在初測（門檻起算不同）": sorted(o_ - n_), "只在本件": sorted(n_ - o_), "本件去重但被鎖擋": sorted(n_ - n_acc)}
    except Exception as ex:                       # noqa: BLE001
        S["與初測事件差（q2）"] = f"讀不到初測 events.csv：{ex}"
    # 前瞻 10/15
    S["前瞻 10/15 判定"] = judge_date(FWD0_DATE, df=df, sha=sha)
    fwd_init()
    PRE_rev = MD.PRE.load_rev(MD.IND_DATA)
    MD._G["PIT"] = MD.PRE.PIT(MD.IND_DATA, PRE_rev[2])
    ROWS = []; CELLS = []; PORT = []; RND = []
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W
        S["閘"][wn] = {"世界": W["gate"], "壞根": W["bad_info"], "段": {sg: f"{W['cal'][x].date()}～{W['cal'][y].date()}" for sg, (x, y) in W["segp"].items()}}
        cp = os.path.join(WORK, f"packs_{wn}.pkl")
        if os.path.exists(cp):
            PK = pickle.load(open(cp, "rb")); log(f"[逐股 {wn}] 讀快取 {cp}")
        else:
            t0 = time.time(); PK = {}
            with Pool(a.procs) as pool:
                for j, (s, pk) in enumerate(pool.imap_unordered(MD.stock_job, [(wn, s) for s in W["run_sids"]], chunksize=8)):
                    if pk is not None:
                        PK[s] = pk
                    if j % 500 == 0:
                        log(f"[逐股 {wn}] {j}/{len(W['run_sids'])}｜{time.time() - t0:.0f}s")
            pickle.dump(PK, open(cp, "wb"), protocol=5)
        gc = max(v["gate_c"] for v in PK.values())
        S["閘"][wn]["快取收盤 vs load_bars 最大相對差"] = gc
        if gc > 1e-9:
            raise SystemExit(f"⛔ {wn} 價格閘不過 {gc}")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        S["閘"][wn]["ETF 有資料"] = {s: (None if EP[s] is None else f"{W['cal'][EP[s]['idx'][0]].date()}～{W['cal'][EP[s]['idx'][-1]].date()}") for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        S["閘"][wn]["營量"] = MD.f_flags(W, PK, M, log)
        DAY, MEMB = day_stats(W, M, log)
        cal = W["cal"]; n0 = W["n0"]; BO, BC = W["BO"], W["BC"]
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        # 一直抱
        holdc = {"0050": BC / BC[0]}
        if EP.get("00631L") is not None:
            cf = EP["00631L"]["cff"]; f0 = np.flatnonzero(np.isfinite(cf))[0]; hc = np.full(n0, np.nan); hc[f0:] = cf[f0:] / cf[f0]
            holdc["00631L"] = hc
        for sg, (x0, y0) in W["segp"].items():
            b = MD.RR.bench_row(cal, W["bench"], x0, y0 + 1)
            S.setdefault("一直抱", {})[sg] = {"0050": wstats(holdc["0050"], x0, y0), "0050（rerun17.bench_row 對照）": {"年化": b["cagr"], "最大回落": b["mdd"]},
                                             "00631L（正2 一直抱，描述）": (wstats(holdc["00631L"], x0, y0) if "00631L" in holdc and np.isfinite(holdc["00631L"][x0]) else None)}
        for k in DEFS:
            rawpos = {datepos[d] for d in df["date"][EV["RAW"][k]] if d in datepos}
            evs = []
            for i in np.flatnonzero(EV["ACC"][k]):
                p = datepos.get(df["date"].iloc[i])
                if p is not None and p + 1 < n0 and segof(p) is not None:
                    evs.append((p, i))
            for cd in CANDS:
                if cd == "B" and wn == "早年":
                    continue
                cost = COST_ETF if cd in ("A", "B") else COST_STK
                for x in EXITS:
                    paths = {}
                    for p, i in evs:
                        Dx = DAY[cd]; Dd = Dx[x]
                        base = {"世界": wn, "段": segof(p), "定義": k, "候選": cd, "出場": x, "日期": str(cal[p].date()), "指數報酬": float(EV["r"][i]),
                                "選出檔數": int(Dx["nsel"][p]), "買到檔數": int(Dx["n"][p]), "產業": Dx["ind"][p],
                                "候選不足（F ＜5）": bool(cd == "F" and Dx["nsel"][p] < 5)}
                        if Dx["n"][p] == 0:
                            ROWS.append({**base, "進場": False}); continue
                        e_, end_, V, ro = bpath(W, M, MEMB[(cd, p)], p, x)
                        paths[p] = (e_, end_, V, ro)
                        Vpk = np.maximum.accumulate(np.r_[1.0, V])
                        ROWS.append({**base, "進場": True, "報酬": float(Dd["net"][p]), "毛報酬": float(Dd["gross"][p]), "配對0050": float(Dd["b50"][p]),
                                     "配對差": float(Dd["net"][p] - Dd["b50"][p]), "平均持有天數": float(Dd["hold"][p]), "最長持有天數": float(Dd["maxhold"][p]),
                                     "持有中最大回落": float(np.min(np.r_[1.0, V] / Vpk - 1)), "持有中最低相對買價": float(min(0.0, np.min(V) - 1)),
                                     "窗尾未出場比例": float(Dd["unex"][p]), "賣完日": str(cal[end_].date())})
                    # 段彙總
                    for sg, (x0, y0) in W["segp"].items():
                        es = [(p, i) for p, i in evs if x0 <= p <= y0]
                        ec = [p for p, _ in es if DAY[cd]["n"][p] > 0]
                        Dd = DAY[cd][x]
                        row = {"世界": wn, "段": sg, "定義": k, "候選": cd, "出場": x, "指數事件數（接受、段內）": len(es), "進場事件數": len(ec)}
                        if cd == "F":
                            row["候選不足事件數（＜5，含 0）"] = int(sum(DAY["F"]["nsel"][p] < 5 for p, _ in es)); row["0 檔事件數"] = int(sum(DAY["F"]["n"][p] == 0 for p, _ in es))
                        if ec:
                            vals = np.array([Dd["net"][p] for p in ec]); b50 = np.array([Dd["b50"][p] for p in ec]); dif = vals - b50
                            ne, rho, prs = eff_n(vals, [(paths[p][0], paths[p][1]) for p in ec])
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
                                for rep in range(NRAND):
                                    rng = np.random.default_rng([RSEED, list(SEGS_V1[wn]).index(sg) + (0 if wn == "早年" else 1), CANDS.index(cd), rep])
                                    dl = [rng.choice(pool[y_], size=min(c_, len(pool[y_])), replace=False) for y_, c_ in sorted(yrs.items()) if len(pool[y_])]
                                    dr = np.concatenate(dl) if dl else np.array([], int)
                                    rm.append(float(np.mean(Dd["net"][dr])) if len(dr) else np.nan)
                                    RND.append({"段": sg, "候選": cd, "i": rep, "隨機平均": rm[-1]})
                                rm = np.array(rm)
                                row.update({"隨機平均": float(np.nanmean(rm)), "實際減隨機": float(vals.mean() - np.nanmean(rm)), "p（隨機 ≥ 實際）": float(np.nanmean(rm >= vals.mean()))})
                        CELLS.append(row)
                    # 組合層（只 q2 主出場）
                    if k == "q2" and x == "主":
                        pl = [paths[p] for p in sorted(paths)]
                        eq1, inm = curve1(n0, pl, cost)
                        if cd == "A":
                            eq2, skp = holdc["0050"].copy(), 0
                        else:
                            eq2, skp = curve2(n0, pl, BO, BC, cost)
                        for sg, (x0, y0) in W["segp"].items():
                            h = wstats(holdc["0050"], x0, y0); s1 = wstats(eq1, x0, y0); s2 = wstats(eq2, x0, y0)
                            PORT.append({"世界": wn, "段": sg, "候選": cd, "①只在事件進場_年化": s1["年化"], "①最大回落": s1["最大回落"], "①比值": s1["比值"],
                                         "①在場日比例": float(inm[x0:y0 + 1].mean()),
                                         "②平時0050換20%_年化": s2["年化"], "②最大回落": s2["最大回落"], "②比值": s2["比值"], "②略過重疊事件": skp,
                                         "一直抱0050_年化": h["年化"], "一直抱0050_最大回落": h["最大回落"], "一直抱0050_比值": h["比值"],
                                         "①比值減0050": s1["比值"] - h["比值"], "②年化減0050": s2["年化"] - h["年化"], "②比值減0050": s2["比值"] - h["比值"]})
            log(f"[{wn}] {k} 完｜{time.time() - T0:.0f}s")
        # 世界尾後的接受事件（只列）
        if wn == "主":
            S["世界尾後的接受事件（只列、不算）"] = {k: [str(df['date'].iloc[i].date()) for i in np.flatnonzero(EV["ACC"][k]) if df["date"].iloc[i] > cal[-1]] for k in DEFS}
            S["個股快照尾"] = str(cal[-1].date())
        del M, DAY, MEMB, PK
    ER = pd.DataFrame(ROWS); CE = pd.DataFrame(CELLS); PO = pd.DataFrame(PORT)
    # 主表：q2 × 主出場 × 六候選 × 三段 ＋ 判語
    m = CE[(CE["定義"] == "q2") & (CE["出場"] == "主")].merge(PO, on=["世界", "段", "候選"], how="left")
    verdict = {}
    for cd in CANDS:
        if cd == "A":
            verdict[cd] = "基準（不判）"; continue
        conds = []
        for sg in MAIN_SEGS:
            r_ = m[(m["候選"] == cd) & (m["段"] == sg)]
            if (not len(r_)) or ("配對差平均" not in r_.columns) or (not np.isfinite(r_["配對差平均"].iloc[0])) or (not np.isfinite(r_["②年化減0050"].iloc[0])):
                conds.append((sg, False, "無進場事件")); continue
            r_ = r_.iloc[0]
            c1 = r_["配對差平均"] > 0; c2 = r_["②年化減0050"] >= 0; c3 = r_["②比值減0050"] >= 0
            conds.append((sg, bool(c1 and c2 and c3), f"配對差 {r_['配對差平均']:+.4f}{'✔' if c1 else '✘'}｜②年化差 {r_['②年化減0050']:+.4f}{'✔' if c2 else '✘'}｜②比值差 {r_['②比值減0050']:+.3f}{'✔' if c3 else '✘'}"))
        verdict[cd] = {"判語": "方向一致（暫定）" if all(c[1] for c in conds) else "方向不一致", "逐段": {c[0]: c[2] for c in conds}}
        if cd == "F":
            fr_ = ER[(ER["定義"] == "q2") & (ER["出場"] == "主") & (ER["候選"] == "F") & ER["段"].isin(MAIN_SEGS)]
            nfull = int((fr_["選出檔數"] >= 5).sum())
            verdict[cd]["足額事件（≥5 檔）"] = nfull
            verdict[cd]["候選不足事件"] = int(fr_["候選不足（F ＜5）"].sum())
            if nfull == 0:
                verdict[cd]["判語"] += "——⚠ 退化：兩主段每個事件都候選不足（0～4 檔），實質是 1～4 檔個股、照實報"
    m["方向判語（兩主段）"] = m["候選"].map(lambda c: verdict[c] if isinstance(verdict[c], str) else verdict[c]["判語"])
    m["_s"] = m["段"].map({"2006～2014": 0, "2015～2021": 1, "2022～": 2}); m["_c"] = m["候選"].map(CANDS.index)
    m = m.sort_values(["_c", "_s"]).drop(columns=["_s", "_c"])
    keep = ["段", "候選", "指數事件數（接受、段內）", "進場事件數", "等效獨立事件數", "平均報酬", "中位報酬", "勝率", "同期0050平均（配對、含成本）",
            "配對差平均", "配對差中位", "X較好比例", "平均持有天數", "最長持有天數", "有窗尾未出場的事件數", "平均籃子檔數",
            "隨機平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落", "①比值", "②平時0050換20%_年化", "②最大回落", "②比值",
            "一直抱0050_年化", "一直抱0050_最大回落", "一直抱0050_比值", "②年化減0050", "②比值減0050", "方向判語（兩主段）", "候選不足事件數（＜5，含 0）", "0 檔事件數"]
    MT = m[[c for c in keep if c in m.columns]]
    MT.to_csv(os.path.join(OUT, "main_table.csv"), index=False, float_format="%.6g", encoding="utf-8")
    CE.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.6g", encoding="utf-8")
    ER.to_csv(os.path.join(OUT, "event_rows.csv"), index=False, float_format="%.10g", encoding="utf-8")
    PO.to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EVT.to_csv(os.path.join(OUT, "events.csv"), index=False, float_format="%.10g", encoding="utf-8")
    pd.DataFrame(RND).to_csv(os.path.join(OUT, "random.csv.gz"), index=False, float_format="%.6g")
    S["方向判語"] = verdict
    # 窗尾未出場
    S["窗尾未出場（主出場）"] = ER[(ER["出場"] == "主") & (ER["窗尾未出場比例"].fillna(0) > 0)][["世界", "定義", "候選", "日期", "窗尾未出場比例", "報酬"]].to_dict("records")
    # 先驗（樣本內描述，⛔ 不改）
    q2c = CE[CE["定義"] == "q2"]
    S["先驗對照（樣本內，描述）"] = {
        "② C、E 主出場平均持有（交易日）": {f"{r_['候選']} {r_['段']}": r_.get("平均持有天數") for _, r_ in q2c[(q2c["出場"] == "主") & q2c["候選"].isin(["C", "E"])].iterrows()},
        "③ 描述出場配對差平均": {f"{r_['候選']} {r_['出場']} {r_['段']}": r_.get("配對差平均") for _, r_ in q2c[q2c["出場"].isin(["副1", "副2"])].iterrows()}}
    S["差異（照登錄 vs 初測）"] = [
        "門檻起算：初測 1990 起全部日報酬 ⇒ 本件 2005-01-03 起（登錄 §一）；第一個可判日見「指數」",
        "同時只處理一個事件：初測沒有 ⇒ 本件持有中（到收復隔天開盤）又遇事件不加碼、只記（登錄 §一）",
        "早年段：初測 2005～2014 ⇒ 本件 2006～2014（登錄 §四）；一直抱 0050 也改這個窗",
        "E：初測最差 1 個產業 ⇒ 本件最差 2 個產業合併等權（登錄 §二）",
        "F：初測「已達成 ∪ 即將達成」⇒ 本件只「已達成」（照正式選股條件）；候選 ＜ 5 記候選不足（登錄 §二）",
        "事件層比較：初測同期 0050 不扣成本 ⇒ 本件配對 0050 扣 ETF 0.385%（登錄 §四「對 A」，A 本身含成本）；報平均、中位、X 較好比例",
        "組合層：初測只有「只在事件進場」且按段各自起算 ⇒ 本件 ① 連續曲線按段切、新增 ②（平時 0050、事件換 20%），年化回落用 window_stats 同口徑、加比值",
        "隨機日：初測三種出場都做 ⇒ 本件只做主出場（登錄 §五「同主出場規則」）",
        "B 早年：初測列 0 筆 ⇒ 本件早年段 B 不算（登錄 §二）",
        "描述門檻（f2、f3、q1）：同去重、同鎖；起算期同 q2 可判日（初測 2005 起、無鎖）",
        "出場、母體 R1、C／D 一成、成本、壞根、世界資料：與初測相同（只 import 重用）"]
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_v1.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[主表 q2 主出場]\n" + MT[["段", "候選", "進場事件數", "平均報酬", "勝率", "同期0050平均（配對、含成本）", "配對差平均", "實際減隨機", "p（隨機 ≥ 實際）",
                                "②年化減0050", "②比值減0050", "方向判語（兩主段）"]].to_string())
    log(f"[判語] {json.dumps(verdict, ensure_ascii=False)}")
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--judge", default=None, help="只做前瞻判定（YYYY-MM-DD）")
    ap.add_argument("--write", action="store_true", help="--judge 是事件時追加 forward/mktdrop/events.csv")
    a = ap.parse_args()
    sys.path.insert(0, REPO)
    if a.judge:
        print(json.dumps(fwd_judge_and_record(a.judge, a.write), ensure_ascii=False, indent=1, default=str)); return
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

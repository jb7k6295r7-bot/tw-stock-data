# -*- coding: utf-8 -*-
"""PREREG營飆停損（台股策略線登錄 seq1 sha bbd598d26c8f31d8；裁定線 seq200 發號）的停損線建構器 ＋ ⓓ 補股池放寬的逐日池建構器。
回測線，2026-09-26。⛔ 只建線與池，⛔ 不跑任何判定格；⛔ 不改 listexit_lines.py／research11.py（只 import）。

停損線格式 ＝ research11.simulate_mtm 的 stop_line：dict[(sid, entry_pos)] → (start, levels)，levels[i] ＝ 日曆位置 start＋i
收盤時生效的停損價（NaN ＝ 這一天沒有停損）；引擎在 t 開盤讀 closes[t−1] 與 levels[t−1−start] 比（stop_line_le=False ⇒「＜」、
True ⇒「≤」），觸發 ⇒ t 開盤整檔出。⭐ 所以 levels 在日曆位置 d 的值只准用到 d（含）以前的收盤 ⇒ 決策日 t 只看 t−1 以前。

六族（登錄 §二 字面；比較方向 ＝ 登錄字面，給 simulate_mtm 的 stop_line_le 見 FAMILIES）：
  P15  p15_lines：線 ＝ ep × 0.85 常數（ep ＝ 引擎進場價：開盤，開盤無效改收盤）；登錄「收盤 ≤ 進場價 × 0.85」⇒ le=True
       ＝ listexit_lines.s1_lines(x=0.15) 的同一條線，只把 (1−0.15)×ep 寫成 ep×85／100（pct_of；真值可表示時兩式證明相同，見 selftest）
  T20  t20_lines：線 ＝ 0.80 × 進場以來最高收盤（進場日收盤起算；只數有效 K 棒；只升不降）；登錄「收盤 ≤ …× 0.80」⇒ le=True
       ⚠ 起點是【進場日收盤】（登錄字面），⛔ 不是 ep（引擎 P7 的 stop=("trail",X) 是 peak_close.get(sid, ep) 起算、另一條路徑）
  A3   a3_lines：＝ listexit_lines.s2_lines(mult=3.0, high_start="entry_close") 原樣（登錄「同 S2，只把 2 倍改 3 倍」）
       S2 是「收盤 ＜ 停損價」⇒ le=False；起始 ep − 3×ATR(訊號日 k)；收盤創新高（嚴格 ＞）才上調 max(舊線, 收盤 − 3×ATR(當日))
  M20  ma_lines(n=20)：線 ＝ 有效 K 棒上的 20 根還原收盤簡單平均，【含該根自己的收盤】（研究十一 M5 同寫法：c[j] ＜ ma5[j]）；
  M50  ma_lines(n=50)：同上 50 根；登錄「收盤 ＜ 均線」⇒ le=False
       停牌日（非有效 K 棒）線沿用前一根的均線值（引擎 closes 在停牌日也是 ffill 前一根 ⇒ 比較結果與前一根相同）
       收盤取引擎的 closes（float32 → float64；與引擎比較的是同一個數）；均線 NaN（根數不足）⇒ 那天沒停損
       ⚠ arm（登錄沒寫、⛔ 本支不選、呼叫端必填）：進場日收盤已在均線下怎麼辦
          "state"       字面「收盤 ＜ 均線」是狀態 ⇒ 進場日收盤 ＜ MA(e) ⇒ e 的次一根開盤就出
          "cross_sig"   讀成「跌破」且把訊號日 k 當前一根：c[k] ≥ MA(k) ⇒ 從進場日起同 state；c[k] ＜ MA(k) ⇒ 等到進場後第一根
                        收盤 ≥ 均線那一根（含）才開始有線（之前 NaN）
          "cross_entry" 讀成「跌破」且只看進場後：等到進場後（含進場日）第一根收盤 ≥ 均線才開始有線
  F    f_lines：前低棘輪 ＝ PREREGD5 §一 原樣 ⇒ 直接呼叫 stop_fractal.stop_line（a68eb28840），對應日曆位置的寫法照
       researchD5.build_lines（有效 K 棒 ＝ load_stock df 收盤有限的那些根；進場日非 K 棒 ⇒ 無線；非 K 棒日沿用前一根）；
       PREREGD5「還原收盤 < 停損」⇒ le=False；找不到前低 ⇒ 進場開盤（還原、該根 o[e]）− 3×ATR(e−1)

PREREG營飆時停（台股策略線登錄 seq1 sha 118f59657e8e0dde；裁定 seq201 發號）：time_lines(kind, d)，kind ∈ R0／R10／NH、d ∈ 20／40／60
  第 1 根 ＝ 進場日（有效 K 棒）；只在第 d 根那一天的日曆位置放線（其餘 NaN ＝ 無停損）⇒ 引擎 t−1 ＝ 第 d 根 ⇒ 第 d 根次一日開盤全賣
  R0  線 ＝ ep、le=True（「收盤 ≤ 進場價」）｜R10 線 ＝ ep×110／100、le=False（「收盤 ＜ 進場價 × 1.10」；⚠ ep×1.10 在某些整數價會高一個 ulp
      ⇒「剛好漲 10%」被誤判成沒反應，selftest H3 有例）
  NH  第 d−19..d 根內沒有「收盤嚴格大於第 1 根以來所有收盤」的事件（第 1 根是起點、不算事件；裁定 seq201 ②）⇒ 線 ＝ BIG（必觸發）、
      否則 NaN；le=False。⚠ 登錄寫 +∞，但引擎只比 np.isfinite(線) 的線 ⇒ +∞ 永遠不觸發 ⇒ 用 float64 最大有限值
  補進來的部位同樣在它自己的第 d 根檢查（裁定 seq201 ①）⇒ 線以 (sid, entry_pos) 建、全部 sig 列都要建

ⓓ 補股池放寬（裁定 seq200 附則 ⓓ，描述臂）：pool_build() ＝ 研究十一 stock_features 主格（30|3）【去掉 20 根去重】
  （把 GRID_* 暫時換成單一格 30|3|0 呼叫原函式，⛔ 不改 research11.py）⇒ research13.and_flags（營收 24 月新高，STALE_MAX 45）
  ⇒ t−1 大盤閘（reg[entry_pos − 1]）⇒ 主窗；每一列 ＝「t−1 收盤三條件都成立、t＝entry_pos 可進」的一個候選。
  「未持有」由引擎在模擬當下排除（⛔ 建構器不知道持股）。去重版必須逐列重建出 setup_t1 的 1,688 列（pool_check 驗）。
"""
from __future__ import annotations

import bisect
import hashlib
import os

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import research11 as R
from . import stop_fractal as SF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYfStop")
RULE = "H120"
ARMS = ("state", "cross_sig", "cross_entry")

# ⭐ 給 simulate_mtm 的參數：stop_line＝該族的線、stop_line_le＝下表、stop_proceeds="next"（登錄 §三 ＝ 名單出場 S1、S2 同一套）
FAMILIES = {
    "P15": {"le": True,  "rule": "收盤 ≤ 進場價 × 0.85"},
    "T20": {"le": True,  "rule": "收盤 ≤ 進場以來最高收盤 × 0.80（進場日收盤起算）"},
    "A3":  {"le": False, "rule": "3×ATR 追蹤（同 S2：收盤 ＜ 停損價）"},
    "M20": {"le": False, "rule": "收盤 ＜ 20 日均線"},
    "M50": {"le": False, "rule": "收盤 ＜ 50 日均線"},
    "F":   {"le": False, "rule": "前低棘輪（PREREGD5：還原收盤 < 停損）"},
}


def sim_kw(fam, lines):
    """後續判定格給 listexit_lines.sim(ctx, kw, r) 的 kw（⛔ 本支不呼叫）。"""
    return {"stop_line": lines, "stop_line_le": FAMILIES[fam]["le"], "stop_proceeds": "next"}


def _rows(sig, rule=RULE):
    for sid, k, e, xp in zip(sig["sid"], sig["k"], sig["entry_pos"], sig[f"xpos_{rule}"]):
        yield sid, int(k), int(e), int(xp)


# ─────────────────────────── 比例線的浮點寫法
def pct_of(x, pct):
    """x × pct／100（pct 整數）⇒ 真值可表示時【恰好】等於它（x 是 float32 值 ⇒ x×pct 在 float64 內無捨入，再 ÷100 正確捨入一次）。
    ⚠ (1−0.15)×x 與 x×85/100：0.85 的捨入誤差 < 結果半個 ulp ⇒ 真值可表示時兩式相同（等價）；但 x×1.10 不行（1.10 捨入偏大，
      例 50×1.10 ＝ 55.00000000000001）⇒ R10「收盤恰好漲 10%」會被誤判 ⇒ 一律用本式。"""
    return x * pct / 100.0


# ─────────────────────────── P15
def p15_lines(sig, opens, closes, rule=RULE, pct=85):
    """線 ＝ ep × 0.85（pct_of 寫法）；ep ＝ listexit_lines.engine_ep。＝ s1_lines(x=0.15) 除浮點寫法外同一條（selftest 報兩式判法不同的列數）。"""
    out = {}
    for sid, k, e, xp in _rows(sig, rule):
        if xp < 0:
            continue
        ep = L.engine_ep(opens, closes, sid, e)
        out[(sid, e)] = (e, np.full(xp - e + 1, pct_of(ep, pct)))
    return out


# ─────────────────────────── T20
def t20_levels(c_cal, valid, e, xp, pct=80):
    """c_cal：引擎收盤（日曆長）；valid：有效 K 棒布林（日曆長）；e 必須是有效 K 棒。
    回 levels[e..xp]：0.80 × 進場以來（含進場日收盤）有效 K 棒的最高收盤；非有效 K 棒日沿用；只升不降。"""
    if not valid[e]:
        raise ValueError(f"進場日 {e} 不是有效 K 棒")
    seg_v = valid[e:xp + 1]; seg_c = np.asarray(c_cal[e:xp + 1], float)
    run = np.where(seg_v, seg_c, -np.inf)
    hi = np.maximum.accumulate(run)
    return pct_of(hi, pct)


def t20_lines(sig, closes, valid_of, rule=RULE, pct=80):
    out = {}
    for sid, k, e, xp in _rows(sig, rule):
        if xp < 0:
            continue
        out[(sid, e)] = (e, t20_levels(closes[sid], valid_of(sid), e, xp, pct))
    return out


# ─────────────────────────── A3
def a3_lines(sig, opens, closes, bars_of, rule=RULE):
    return L.s2_lines(sig, rule, opens, closes, bars_of, mult=3.0, high_start="entry_close")


# ─────────────────────────── M20／M50
def ma_valid(c_cal, idx, n):
    """有效 K 棒上的 n 根簡單平均（含該根自己）；回與 idx 同長，前 n−1 根 NaN。"""
    cv = np.asarray(c_cal, float)[idx]
    cs = np.concatenate(([0.0], np.cumsum(cv)))
    ma = np.full(len(cv), np.nan)
    if len(cv) >= n:
        ma[n - 1:] = (cs[n:] - cs[:-n]) / n
    return ma


def ma_levels(c_cal, idx, ma, k, e, xp, arm):
    """idx：有效 K 棒日曆位置；ma：ma_valid 的結果；k：訊號根（idx 索引，idx[k+1] ＝ e）。回 levels[e..xp]。"""
    if arm not in ARMS:
        raise ValueError(f"arm 必須明給（登錄沒寫、待裁定）：{ARMS}，收到 {arm!r}")
    if int(idx[k + 1]) != e:
        raise ValueError(f"訊號根 k＝{k} 的下一根不是 entry_pos {e}")
    c = np.asarray(c_cal, float)
    lv = np.empty(xp - e + 1)
    armed = arm == "state" or (arm == "cross_sig" and np.isfinite(ma[k]) and c[idx[k]] >= ma[k])
    j = k + 1; cur = np.nan
    for d in range(e, xp + 1):
        if j < len(idx) and int(idx[j]) == d:
            cur = ma[j]
            if not armed and np.isfinite(cur) and c[d] >= cur:
                armed = True
            j += 1
        lv[d - e] = cur if armed else np.nan
    return lv


def ma_lines(sig, closes, bars_of, n, arm, rule=RULE):
    out = {}; cache = {}
    for sid, k, e, xp in _rows(sig, rule):
        if xp < 0:
            continue
        if sid not in cache:
            idx = bars_of(sid)["idx"]
            cache[sid] = (idx, ma_valid(closes[sid], idx, n))
        idx, ma = cache[sid]
        out[(sid, e)] = (e, ma_levels(closes[sid], idx, ma, k, e, xp, arm))
    return out


# ─────────────────────────── F（PREREGD5 原樣）
def f_ohlc(B):
    """researchD5 同一條：有效 K 棒 ＝ load_stock df 收盤有限；o/h/l/c 取 df（還原、float64）。"""
    df = B["df"]
    c = df["close"].to_numpy(float)
    v = np.flatnonzero(np.isfinite(c))
    return v.tolist(), tuple(df[kk].to_numpy(float)[v] for kk in ("open", "high", "low", "close"))


def f_one(bars, ohlc, e_pos, x_pos, k=SF.K_SIDE, stop_fn=None):
    """researchD5.build_lines 的單列版（逐字同一段）。回 (levels 或 None, kind, 初始停損)。"""
    stop_fn = stop_fn or SF.stop_line
    o, h, l, c = ohlc
    j = bisect.bisect_left(bars, e_pos)
    if j >= len(bars) or bars[j] != e_pos:
        return None, "進場日非 K 棒", np.nan
    jx = bisect.bisect_right(bars, x_pos) - 1
    lv, kind = stop_fn(o, h, l, c, j, jx, k=k)
    arr = np.full(x_pos - e_pos + 1, np.nan)
    for b, v in zip(range(j, jx + 1), lv):
        arr[bars[b] - e_pos] = v
    arr = pd.Series(arr).ffill().to_numpy()
    return arr, kind, float(lv[0]) if len(lv) else np.nan


def f_lines(sig, bars_of, rule=RULE):
    out = {}; kinds = {}; cache = {}
    for sid, k, e, xp in _rows(sig, rule):
        if xp < 0:
            continue
        if sid not in cache:
            cache[sid] = f_ohlc(bars_of(sid))
        bars, ohlc = cache[sid]
        arr, kind, _ = f_one(bars, ohlc, e, xp)
        kinds[(sid, e)] = kind
        if arr is not None:
            out[(sid, e)] = (e, arr)
    return out, kinds


# ─────────────────────────── 全部六族（＋ M 的三種 arm）
def build_all(sig, opens, closes, bars_of, arms=ARMS, rule=RULE):
    """回 {名: (lines, skipped, extra)}；M20／M50 每個 arm 各一份（名 ＝ "M20:state" 等）。"""
    res = {}
    res["P15"] = (p15_lines(sig, opens, closes, rule), 0, {})
    valid_cache = {}

    def valid_of(sid):
        if sid not in valid_cache:
            v = np.zeros(len(closes[sid]), bool); v[bars_of(sid)["idx"]] = True; valid_cache[sid] = v
        return valid_cache[sid]
    res["T20"] = (t20_lines(sig, closes, valid_of, rule), 0, {})
    a3, sk = a3_lines(sig, opens, closes, bars_of, rule)
    res["A3"] = (a3, sk, {})
    for n in (20, 50):
        for arm in arms:
            res[f"M{n}:{arm}"] = (ma_lines(sig, closes, bars_of, n, arm, rule), 0, {})
    fl, kinds = f_lines(sig, bars_of, rule)
    res["F"] = (fl, sum(1 for v in kinds.values() if v == "進場日非 K 棒"), {"kinds": kinds})
    return res


def fam_of(name):
    return name.split(":")[0]


def lines_sha(lines):
    h = hashlib.sha256()
    for key in sorted(lines):
        st, lv = lines[key]
        h.update(f"{key[0]}|{key[1]}|{st}|".encode()); h.update(np.asarray(lv, float).tobytes())
    return h.hexdigest()[:16]


def first_trigger(lv, start, c_cal, xp, le):
    """只看價格與線（⛔ 不跑引擎）：引擎同一式——t 從 start＋1 到 xp−1（t ＝ xp 是排程出場日、不搶），
    c ＝ c_cal[t−1]、線 ＝ lv[t−1−start]，有限且（le ⇒ ≤／否則 ＜）⇒ 回觸發的 t−1（收盤跌破那一天的日曆位置），無 ⇒ −1。"""
    c = np.asarray(c_cal[start:xp], float)          # t−1 ＝ start … xp−1
    v = np.asarray(lv[:xp - start], float)
    ok = np.isfinite(v) & np.isfinite(c) & ((c <= v) if le else (c < v))
    w = np.flatnonzero(ok)
    return start + int(w[0]) if len(w) else -1


# ─────────────────────────── PREREG營飆時停（台股策略線登錄 seq1 sha 118f59657e8e0dde；裁定 seq201）
TIME_DEFS = ("R0", "R10", "NH")
TIME_DS = (20, 40, 60)
TIME_LE = {"R0": True, "R10": False, "NH": False}        # R0「收盤 ≤ 進場價」；R10「收盤 ＜ 進場價 × 1.10」；NH 線＝「必觸發」
TIME_WIN = 20                                            # NH「第 d 根往回 20 根（d−19～d）」
BIG = float(np.finfo(np.float64).max)                   # ⚠ 引擎要求 np.isfinite(線) 才比 ⇒ 登錄的「+∞」用最大有限值表達（任何有限收盤都 ＜ 它）


def time_level(cb, ep, kind, d, win=TIME_WIN):
    """cb：進場日起的有效 K 棒收盤（cb[0] ＝ 第 1 根 ＝ 進場日），長度 ≥ d。回第 d 根收盤時的線值（NaN ＝ 不觸發／沒有線）。
    NH：第 m 根（m ≥ 2）收盤【嚴格】大於第 1..m−1 根所有收盤 ⇒ 事件（第 1 根是起點、⛔ 不算事件；裁定 seq201 ②）；
        第 max(2, d−19)..d 根內沒有事件 ⇒ BIG（必觸發），否則 NaN。"""
    if kind == "R0":
        return float(ep)
    if kind == "R10":
        return pct_of(ep, 110)
    if kind != "NH":
        raise ValueError(kind)
    ev = np.zeros(d, bool); hi = float(cb[0])
    for m in range(1, d):
        if float(cb[m]) > hi:
            ev[m] = True; hi = float(cb[m])
    lo = max(0, d - win)
    return np.nan if ev[lo:d].any() else BIG


def time_levels(c_cal, idx, k, e, xp, ep, kind, d, win=TIME_WIN):
    """一筆部位的時停線：只有第 d 根有效 K 棒（第 1 根 ＝ 進場日 ＝ idx[k+1]）那一天的日曆位置有值，其餘 NaN。
    引擎在 t 開盤讀 levels[t−1−start] ⇒ t−1 ＝ 第 d 根 ⇒ t ＝ 第 d 根的次一個日曆日開盤賣；那天停牌（開盤無效）⇒ 引擎記 sl_pending、
    延到下一個有效開盤（⭐ 之後的日子線是 NaN 也照樣賣：pending 不再看線）。回 (levels, 狀態)。"""
    if int(idx[k + 1]) != e:
        raise ValueError(f"訊號根 k＝{k} 的下一根不是 entry_pos {e}")
    lv = np.full(xp - e + 1, np.nan)
    jd = k + 1 + d - 1
    if jd >= len(idx):
        return lv, "無第 d 根"
    D = int(idx[jd])
    if D + 1 > xp - 1:                                   # 引擎在 t ≥ 排程出場日不搶；t ＝ D＋1 必須 ＜ xp
        return lv, "第 d 根太晚"
    cb = np.asarray(c_cal, float)[idx[k + 1:jd + 1]]
    lv[D - e] = time_level(cb, ep, kind, d, win)
    return lv, "ok"


def time_lines(sig, opens, closes, bars_of, kind, d, rule=RULE):
    out = {}; st = {}
    for sid, k, e, xp in _rows(sig, rule):
        if xp < 0:
            continue
        idx = bars_of(sid)["idx"]
        lv, s = time_levels(closes[sid], idx, k, e, xp, L.engine_ep(opens, closes, sid, e), kind, d)
        st[s] = st.get(s, 0) + 1
        out[(sid, e)] = (e, lv)
    return out, st


def time_kw(kind, lines):
    """後續判定格給 listexit_lines.sim 的 kw（⛔ 本支不呼叫）。"""
    return {"stop_line": lines, "stop_line_le": TIME_LE[kind], "stop_proceeds": "next"}


# ─────────────────────────── ⓓ 補股池放寬（逐日池）
POOL_S = "pool_S_nodedup.csv.gz"
POOL_AND = "pool_and_nodedup.csv.gz"
S_COLS = ["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]


def pool_build(log=print, limit=None):
    """① stock_features 主格去掉去重（GRID 暫換 30|3|0；⛔ 不改 research11.py）⇒ pool_S_nodedup.csv.gz
    ② 照 rerun17_build ③ 同一條讀法（讀回 csv）⇒ and_flags ⇒ pool_and_nodedup.csv.gz（⛔ 還沒套大盤閘與窗；pool_rows 套）。"""
    import time
    from . import data as D
    from . import rerun17 as RR
    from . import research13 as R13
    from . import universe_gate as UG
    RR.use_snapshot()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    tasks = [(r.stock_id, r.market, r.first_seen) for r in uni.itertuples()]
    if limit:
        tasks = tasks[:limit]
    saved = (R.GRID_C1, R.GRID_C3, R.GRID_DEDUP, R.MAIN_CELL)
    c1, c3, _ = R.MAIN_CELL
    rows = []
    try:
        R.GRID_C1, R.GRID_C3, R.GRID_DEDUP, R.MAIN_CELL = [c1], [c3], [0], (c1, c3, 0)
        R._init(cal)
        for i, t in enumerate(tasks):
            r = R.stock_features(t)
            if r is not None:
                rows.extend(r["main"])
            if (i + 1) % 250 == 0:
                log(f"  ① {i + 1}/{len(tasks)} {time.time() - t0:.0f}s")
    finally:
        R.GRID_C1, R.GRID_C3, R.GRID_DEDUP, R.MAIN_CELL = saved
    S_full = pd.DataFrame(rows)
    S_full.to_csv(os.path.join(OUT, POOL_S), index=False)
    log(f"[①S 不去重] {len(S_full):,} 列／{S_full['sid'].nunique():,} 檔｜{time.time() - t0:.0f}s")
    pnl = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str})
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    S = pd.read_csv(os.path.join(OUT, POOL_S), dtype={"sid": str})
    S = S[S_COLS].copy()
    flags, _ = R13.and_flags(S, pnl)
    AND = S[flags].copy()
    AND.to_csv(os.path.join(OUT, POOL_AND), index=False)
    log(f"[②AND 不去重] {len(AND):,} 列／{AND['sid'].nunique():,} 檔｜{time.time() - t0:.0f}s")


def dedup20(S, dd=None):
    """研究十一的去重（同檔上一個被選的訊號之後 > dd 根有效 K 棒）套回不去重的列 ⇒ 應重建 signals_S。"""
    dd = R.MAIN_CELL[2] if dd is None else dd
    keep = np.zeros(len(S), bool)
    ks = S["k"].to_numpy(); sids = S["sid"].to_numpy()
    order = np.lexsort((ks, sids))
    last_sid, last = None, -10 ** 9
    for i in order:
        if sids[i] != last_sid:
            last_sid, last = sids[i], -10 ** 9
        if ks[i] - last > dd:
            keep[i] = True; last = ks[i]
    return keep


def pool_rows(ctx):
    """讀 pool_and_nodedup.csv.gz ⇒ 套 setup_t1 同一條大盤閘（reg[entry_pos − 1]）與主窗 ⇒ 逐日池的列（⛔ 未排除持股）。"""
    G = ctx["RR"]._G
    reg = G["regime"]
    A = pd.read_csv(os.path.join(OUT, POOL_AND), dtype={"sid": str})
    e = A["entry_pos"].to_numpy()
    if e.min() < 1:
        raise SystemExit("⛔ entry_pos 有 0")
    inwin = (e >= G["w0"]) & (e <= G["w1"])
    return A[reg[e - 1] & inwin].copy()

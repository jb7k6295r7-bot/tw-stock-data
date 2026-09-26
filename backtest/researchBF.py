# -*- coding: utf-8 -*-
"""PREREG突破過濾【直接買 vs 加一道過濾】單筆層——回測線落地。【本支目前只有 pre 段：開跑前檢查，⛔ 不讀任何報酬】
判準＝台股策略線 登錄 seq2（sha 245c89b4d6d49657，7503B，2026-09-26 00:57）；編號＝裁定線 seq186 §五
（N_前段 最多 ＋14；① 退化檢查：每格報「買到的比例」「與 A 同日買進的比例」，≥ 95% 與 A 同日 ⇒ 依構造退化、不計 N；
 ② 「加過濾比較好」須 Bonferroni（0.05／可判定格數，雙尾）下界 ＞ 0）。

用法（repo 根；PYTHONPATH=~/tw-p17；Python ＝ ~/tw-p16/.venv/bin/python）：
    python backtest/researchBF.py pre [--procs 2] [--limit N]     # ⛔ 不算任何報酬；--limit 只給除錯
    （body 段：⛔ 尚未寫——等讀法 Q1～Q14 裁定後才加）
輸出：backtest/resultsBF/（pre_cells.csv、pre_ledger.csv、pre_sensitivity.csv、pre_events.csv.gz、pre_check.json、PRE_REPORT.md）

資料／母體／事件：import researchX（⇒ researchH2：main edc6f8002f 快照、gate3、還原 OHLC、tradability 原始價漲跌停）；
delist on（登錄 §一；同 PREREG型態全量 Q5／researchM_freq._g5(upto)：delisted_official／delisted_gap 的股票，最後成交之後的無成交日 ⛔ 不算連續缺日）；
偵測器 patterns_x.py（commit 84d1c88737，⛔ 只 import、不改）：W 底、頭肩底 ＝ PX.detect_turn（有效 K 棒序列）；
箱型 ＝ PX.box_events（研究二 box_breakout 原樣，T ＝ 站穩確認日＝訊號日＋2）。頸線 N ＝ 偵測器的 level
（W 底 close[A]、頭肩底 (A1＋A2)／2、箱型 箱頂 box_top[訊號日]）＝ 登錄 §一 逐字。
fixture：selftest()（本支買法規則 F1～F11；每條都是「該成立／該不成立」成對 ⇒ 分得出來、不假紅）
      ＋ selftest_patterns_x.run_all()（T1：W、頭肩底、箱型必須過）
      ＋ 事件層對帳（照 researchX Y1～Y5 的設定重做 ⇒ 與已交件 resultsX/freq.json 甲_w／甲_hs／甲_box 的保留數與剔除帳逐項相同）
      ＋ 0050 主窗錨逐位元（rerun17.bench_row；本體「A 本身 vs 0050 同段」要用）。

登錄已寫死（照寫、⛔ 不動）：五種買法的數字（1.03、5 日、3 天、1.5 倍、5 日均量、20 日、1.02、0.97）、錘子形／多頭吞噬形狀、
  箱型不做 C、終點 ＝ A 的 H60 收盤（T＋1＋59 ＝ T＋60，交易日曆）、同檔同型 20 個交易日只取第一筆（researchX Y2 的走法）、
  60 日區段、＜ 30 段 ⇒ 依構造不可判定、≥ 95% 與 A 同日 ⇒ 依構造退化。

⚠ 登錄沒寫清楚、要裁的地方（◇ ＝ pre 暫用來算計數的那一個；⛔ 不是選定——等裁定；每處另一讀法的計數在 pre_sensitivity.csv）：
  見下方 READINGS（可算的 Q1～Q10）與 READINGS_TEXT（只列、不影響判退化或影響極小的 Q11～Q14）。
"""
from __future__ import annotations
import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchX as RX                                   # noqa: E402  ⇒ researchH2（D.DATA ＝ main edc6f8002f 快照）
import researchM_freq as MF                              # noqa: E402  _g5（delist on）
H2, D, TR, UG, PX = RX.H2, RX.D, RX.TR, RX.UG, RX.PX
sys.path.insert(0, os.path.expanduser("~/tw-p17"))

OUT = "backtest/resultsBF"
REG = "PREREG突破過濾 登錄 seq2（sha 245c89b4d6d49657）；裁定 seq186 §五"
W0, W1, SHA = H2.W0, H2.W1, H2.SHA
H = 60                     # 終點 ＝ T＋60（A 進場日 T＋1 起第 60 根收盤）
MERGE = 20
BLK = 60                   # 主 CI 分群區段（登錄 §三）
MIN_BLK = 30               # ＜ 30 段 ⇒ 依構造不可判定
DEGEN = 0.95               # ≥ 95% 與 A 同日 ⇒ 依構造退化
# 登錄 §二 設計參數（⛔ 不掃）
B_PCT, B_DAYS = 1.03, 5
C_DAYS = 3
D_X, VM_N = 1.5, 5
E_DAYS, E_NEAR, E_BREAK = 20, 1.02, 0.97
HAM_SH, HAM_UP, DOJI = 2.0, 0.10, 0.10
TYPES = ("w", "hs", "box")
NAME = {"w": "W 底", "hs": "頭肩底", "box": "箱型"}
ARMS = {"w": "BCDEF", "hs": "BCDEF", "box": "BDEF"}          # 箱型不做 C（登錄 §二 C）⇒ 14 格
ARM_NAME = {"A": "A 直接買", "B": "B 幅度 3%", "C": "C 站穩 3 天", "D": "D 放量 1.5 倍", "E": "E 等回測＋量縮＋止跌 K", "F": "F 三道全加"}

READINGS = [
    ("win", "Q1 事件窗（T 的範圍）", [
        ("60", "T ∈ [窗起點, 窗尾−60]：終點 T＋60 在窗內（H60 是判定；H20／H120 只描述，H120 另取子集）"),
        ("120", "T ≤ 窗尾−120：H60 判定與 H120 描述用同一批事件（researchX Y1 的寫法）")]),
    ("brk", "Q2 硬斷點「[型態第一個轉折, 終點] 內」的內容", [
        ("甲", "[第一轉折, T] 用 researchX Y3（價格斷點、連續 ≥5 日無 K 棒、處置期間、注意股公告日）＋ (T, T＋60] 用 H2.brk（價格、停牌；researchX Y4）"),
        ("乙", "整段 [第一轉折, T＋60] 只用 H2.brk（價格斷點＋連續 ≥5 日無 K 棒；⛔ 不含處置／注意）")]),
    ("a_untrd", "Q3 A 的 T＋1 停牌或開盤漲停", [
        ("excl", "事件剔除並計數（researchX Y5）⇒ A 每筆都買得到"),
        ("zero", "事件保留、A 記「沒買到」＝0（PREREG限價 M0 的寫法）；A 的進場規則同 Q4")]),
    ("untrd", "Q4 過濾臂的進場日（條件成立日的次日開盤）停牌或開盤漲停", [
        ("zero", "沒買到（算 0；PREREG限價 M0）"),
        ("next", "順延到下一個可成交日開盤（不超過終點）"),
        ("limitbuy", "開盤漲停照買（PREREG限價 M0′）；停牌仍沒買到")]),
    ("days", "Q5 B 的「5 個交易日」、C 的「連續 3 天」、E／F 的「20 個交易日」怎麼數", [
        ("cal", "交易日曆：停牌日也佔一天、當天條件不成立（C 遇停牌即不成立）（researchX Y1、researchLimit L3）"),
        ("bar", "該股有效 K 棒（停牌日不算；PREREGX X1 幾何的數法）")]),
    ("vm", "Q6「前 5 日均量」（D、E②）", [
        ("bar", "前 5 根有效 K 棒的成交量平均（H2 R1 技術指標慣例）"),
        ("cal", "日曆前 5 日；其中任一日無成交 ⇒ 不可算 ⇒ 條件不成立（研究二 Frame.vol_ma20 的寫法）")]),
    ("boxT", "Q7 箱型 B、D 的「T」", [
        ("T", "字面：T ＝ 研究二站穩確認日（登錄 §一）⇒ B 看確認日起 5 日收盤、D 看確認日當天的量"),
        ("sig", "研究二訊號日（突破當天）⇒ B 在訊號日就成立（研究二已要求收盤 ＞ 箱頂×1.03）、D 看突破當天的量；進場一律不早於 T＋1")]),
    ("F", "Q8 F「B 與 D 都成立之後，再照 E 等回測」的等待窗", [
        ("甲", "B 成立日 b 之後重新數 20 日：R ∈ [b＋1, b＋20]；跌破 0.97N 只看 (b, R]"),
        ("乙", "沿用 E 的窗：R ∈ [max(T＋1, b＋1), T＋20]；跌破 0.97N 從 T＋1 看起")]),
    ("eng", "Q9 多頭吞噬（止跌 K）的「前一根」", [
        ("bar", "前一根有效 K 棒（PREREG型態全量 A1）"),
        ("cal", "日曆前一日；前一日停牌 ⇒ 不成立")]),
    ("merge", "Q10「同檔同型 20 個交易日只取第一筆」遇到被剔除的事件", [
        ("X", "被剔除（斷點／T＋1 不可成交）的事件 ⛔ 不開合併窗：窗從「上一個被保留事件」算（researchX Y2、H2 R5）"),
        ("P", "先合併、再剔除：窗從「上一個沒被合併的事件」算，被剔除的也開窗（PREREG型態全量 Q2）")]),
]
BASE = {k: opts[0][0] for k, _, opts in READINGS}

READINGS_TEXT = [
    ("Q11「與 A 同日買進的比例」的分母",
     "◇ 全部事件（＝ 過濾臂與 A 逐筆相同的比例；退化的意思是 Δ 依構造 ≈ 0）／另一讀法：只算買到的事件。"
     "兩個分母 pre_cells.csv 都列（同日比例_全部、同日比例_買到中）；判退化用前者。⚠ 用後者時 D 放量在 W 底、頭肩底必然 100%（D 買到就是 T＋1）⇒ 依定義退化。"),
    ("Q12 錘子形「非十字」",
     "◇ 全長 R ＞ 0 且實體 B ＞ 0.1R（＝ PREREG型態全量「十字 ＝ R＞0 且 B≤0.1R」的否定，並排除一字線 R＝0：R＝0 時「下影 ≥ 2 倍實體」"
     "「上影 ≤ 10% 全長」兩條都是 0≥0 會成立）／另一讀法：研究二 P4 的 B ≥ 0.1R（只差等號）。錘子不分紅黑（登錄沒寫顏色）。"),
    ("Q13 60 日區段歸屬",
     "◇ (T − 窗起點)//60（researchX judge 的寫法）／另一讀法：以 A 進場日 T＋1 歸段。pre_cells.csv 兩個都列（區段數、區段數_T+1）。"),
    ("Q14 價格與量的尺度",
     "◇ 頸線 N、收盤、最低一律還原價（登錄 §一「還原 OHLC」；N 本身也是還原價）；量 ＝ data.load_stock 的原始成交股數（未還原）"
     "⇒ 前 5 日窗內若有面額變更，量比會失真（不另處理，本體另報件數）。"),
]


# ═════════════ 每檔前處理（fixture 與正式共用同一支） ═════════════
def prep(o, h, l, c, v):
    """回：valid、bars、vm5_bar、vm5_cal、ham、eng_bar、eng_cal（全部日曆對齊）。"""
    o, h, l, c, v = (np.asarray(x, float) for x in (o, h, l, c, v))
    n = len(c)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    vb = pd.Series(v[bars]).rolling(VM_N, min_periods=VM_N).mean().shift(1).to_numpy(float)
    vm5_bar = np.full(n, np.nan); vm5_bar[bars] = vb
    vm5_cal = pd.Series(v).rolling(VM_N, min_periods=VM_N).mean().shift(1).to_numpy(float)
    ok = np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & valid
    with np.errstate(invalid="ignore"):
        R = h - l; B = np.abs(c - o); top = np.fmax(o, c); bot = np.fmin(o, c)
        lower = bot - l; upper = h - top
        ham = ok & (R > 0) & (B > DOJI * R) & (lower >= HAM_SH * B) & (upper <= HAM_UP * R)
        wh = ok & (c > o); bk = ok & (c < o)
    # 多頭吞噬（PREREG型態全量 #56 形狀；不要求事前趨勢）：前一根黑、這一根白、實體頂 ≥、實體底 ≤、實體 ＞
    with np.errstate(invalid="ignore"):
        def eng_pair(t, p):
            return wh[t] & bk[p] & ok[p] & (top[t] >= top[p]) & (bot[t] <= bot[p]) & (B[t] > B[p])
        eng_bar = np.zeros(n, bool)
        if len(bars) > 1:
            eng_bar[bars[1:]] = eng_pair(bars[1:], bars[:-1])
        eng_cal = np.zeros(n, bool)
        if n > 1:
            t = np.arange(1, n); eng_cal[1:] = eng_pair(t, t - 1) & valid[t - 1]
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "valid": valid, "bars": bars,
            "vm5_bar": vm5_bar, "vm5_cal": vm5_cal, "ham": ham, "eng_bar": eng_bar, "eng_cal": eng_cal}


# ═════════════ 買法規則（登錄 §二） ═════════════
def seq_days(S, s, k, mode):
    n = len(S["c"])
    if mode == "cal":
        return list(range(max(s, 0), min(s + k, n)))
    b = S["bars"]; i = int(np.searchsorted(b, s))
    return [int(x) for x in b[i:i + k]]


def entry_at(S, x, end, mode):
    """「次日開盤買」：x ＝ 條件成立日＋1。回 (進場日 或 None, 沒買到的原因)。"""
    n = len(S["c"])

    def ok(d):
        return d < n and bool(S["trd"][d]) and np.isfinite(S["o"][d])
    if x > end:
        return None, "超過終點"
    if mode == "next":
        d = x
        while d <= end:
            if ok(d) and not S["up_o"][d]:
                return d, None
            d += 1
        return None, "順延到終點仍不可成交"
    if not ok(x):
        return None, "進場日停牌"
    if S["up_o"][x] and mode != "limitbuy":
        return None, "進場日開盤漲停"
    return x, None


def wait_retest(S, N, ds, vm, eng, after=None):
    """E：ds 內第一個同時符合 ①②③ 的日子 R；在那之前任一天收盤 ＜ 0.97N ⇒ 沒買。after：F 要求 R ＞ after。"""
    c, l, v = S["c"], S["l"], S["v"]
    for d in ds:
        if not S["valid"][d]:
            continue
        if c[d] < E_BREAK * N:
            return None, "跌破頸線"
        if after is not None and d <= after:
            continue
        if l[d] <= E_NEAR * N and c[d] >= N and np.isfinite(vm[d]) and v[d] < vm[d] and (S["ham"][d] or eng[d]):
            return d, None
    return None, "窗內沒出現"


def arms(S, e, typ, o):
    """回 {臂: (進場日或 None, 原因, 條件成立日)}。⛔ 不讀任何報酬。"""
    T, N = e["T"], e["N"]; end = T + H
    c, v = S["c"], S["v"]
    vm = S["vm5_bar"] if o["vm"] == "bar" else S["vm5_cal"]
    eng = S["eng_bar"] if o["eng"] == "bar" else S["eng_cal"]
    out = {}
    if o["a_untrd"] == "excl":
        out["A"] = (T + 1, None, T)
    else:
        x, why = entry_at(S, T + 1, end, o["untrd"]); out["A"] = (x, why, T)
    T0 = e["sig"] if (typ == "box" and o["boxT"] == "sig") else T
    # B
    b = None
    for d in seq_days(S, T0, B_DAYS, o["days"]):
        if S["valid"][d] and c[d] >= B_PCT * N:
            b = d; break
    if b is not None:
        b = max(b, T)                                        # 進場一律不早於 T＋1（只影響 Q7 乙）
        x, why = entry_at(S, b + 1, end, o["untrd"]); out["B"] = (x, why, b)
    else:
        out["B"] = (None, "5 日內沒有收盤 ≥ 1.03N", None)
    # C
    if "C" in ARMS[typ]:
        ds = seq_days(S, T, C_DAYS, o["days"])
        if len(ds) == C_DAYS and all(S["valid"][d] and c[d] > N for d in ds):
            x, why = entry_at(S, ds[-1] + 1, end, o["untrd"]); out["C"] = (x, why, ds[-1])
        else:
            out["C"] = (None, "3 天沒有全部收盤 ＞ N", None)
    # D
    Dok = bool(S["valid"][T0] and np.isfinite(vm[T0]) and v[T0] >= D_X * vm[T0])
    if Dok:
        x, why = entry_at(S, T + 1, end, o["untrd"]); out["D"] = (x, why, T0)
    else:
        out["D"] = (None, "量不到 1.5 倍（或均量不可算）", None)
    # E
    R, why = wait_retest(S, N, seq_days(S, T + 1, E_DAYS, o["days"]), vm, eng)
    if R is not None:
        x, why = entry_at(S, R + 1, end, o["untrd"]); out["E"] = (x, why, R)
    else:
        out["E"] = (None, why, None)
    # F
    if b is None or not Dok:
        out["F"] = (None, "B 或 D 不成立", None)
    else:
        if o["F"] == "甲":
            R, why = wait_retest(S, N, seq_days(S, b + 1, E_DAYS, o["days"]), vm, eng)
        else:
            R, why = wait_retest(S, N, seq_days(S, T + 1, E_DAYS, o["days"]), vm, eng, after=b)
        if R is not None:
            x, why = entry_at(S, R + 1, end, o["untrd"]); out["F"] = (x, why, R)
        else:
            out["F"] = (None, why, None)
    return out


# ═════════════ 事件層（researchX Y2 的走法；Q1～Q3） ═════════════
def keep(S, typ, w0, wE, n, o):
    acc = {"原始_窗內": 0, "合併掉": 0, "剔除_型態視窗_價格或停牌": 0, "剔除_型態視窗_處置": 0, "剔除_型態視窗_注意": 0,
           "剔除_未來窗斷點": 0, "剔除_硬斷點(乙)": 0, "剔除_T+1停牌": 0, "剔除_T+1開盤漲停": 0}
    out = []; t_keep = -10 ** 9
    for e in sorted(S["A"][typ], key=lambda x: x["T"]):
        T = e["T"]
        if not (w0 <= T <= wE):
            continue
        acc["原始_窗內"] += 1
        if t_keep < T <= t_keep + MERGE:
            acc["合併掉"] += 1; continue
        if o.get("merge", "X") == "P":
            t_keep = T                                       # Q10 另一讀法：被剔除的也開合併窗（PREREG型態全量 Q2）
        if T + H >= n:
            acc["剔除_未來窗斷點"] += 1; continue
        if o["brk"] == "甲":
            why = RX.brk_pat(S, e["first"], T)
            if why:
                acc["剔除_型態視窗_" + why] += 1; continue
            if RX.brk_fwd(S, T + 1, T + H):
                acc["剔除_未來窗斷點"] += 1; continue
        else:
            if H2.brk(S, e["first"], T + H):
                acc["剔除_硬斷點(乙)"] += 1; continue
        if o["a_untrd"] == "excl":
            tn = RX.tradable_next(S, T)
            if tn:
                acc["剔除_T+1停牌" if tn == "halt" else "剔除_T+1開盤漲停"] += 1; continue
        out.append(e); t_keep = T
    return out, acc


# ═════════════ 讀檔 ═════════════
_OFF = {}


def _init(cal, disp, attn, off):
    RX._init(cal, disp, attn); _OFF["off"] = off


def load_one(args):
    sid, market = args
    cal = RX._G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float); v = df["volume"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:                                        # 同 researchX.load_one
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    g5x = RX._g5(valid)                                      # researchX 原樣（只給對帳）
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_OFF["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = MF._g5(valid, upto=ds["last"]) if delisted else MF._g5(valid)   # delist on
    dm = D.disposal_mask(sid, cal, RX._G["disp"], after_days=0)
    am = np.zeros(n, bool)
    ad = RX._G["attn"].get(sid)
    if ad:
        am = np.isin(cal.values, np.array(sorted(ad), dtype="datetime64[ns]"))
    ret = np.full(n, np.nan); ret[1:] = c[1:] / c[:-1] - 1.0
    vol20 = pd.Series(ret).rolling(20, min_periods=20).std(ddof=1).to_numpy()   # 只給對帳（researchX Y2 最後一條）
    cb = c[bars]
    A = {}
    for kind in ("w", "hs"):
        r = PX.detect_turn(kind, cb)
        A[kind] = [{"T": int(bars[e["T"]]), "first": int(bars[e["first"]]), "N": float(e["level"]), "target": float(e["target"]),
                    "sig": int(bars[e["T"]])} for e in r["events"]]
    f = PX.frame_open(df, st.event_dates)
    A["box"] = [{"T": int(e["T"]), "first": int(e["first"]), "N": float(e["level"]), "target": float(e["target"]), "sig": int(e["sig"])}
                for e in PX.box_events(f)]
    S = prep(o, h, l, c, v)
    S.update({"sid": sid, "market": market, "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32), "cs_g5_x": np.cumsum(g5x).astype(np.int32),
              "status": ds["status"] if ds else None, "last": ds["last"] if ds else None,
              "cs_d": np.cumsum(dm).astype(np.int32), "cs_a": np.cumsum(am).astype(np.int32),
              "trd": tb["trd"], "up_o": tb["up_o"], "vol": vol20, "A": A})
    return S


def load_all(procs, lim=None):
    t0 = time.time()
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    disp = D.load_disposal_intervals(); attn = D.load_attention_dates()
    off = TR.load_official()
    with Pool(procs, initializer=_init, initargs=(cal, disp, attn, off)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    print("[資料] 快照 {}｜gate3 {:,} 檔、可用 {:,}｜判定窗 [{}, {}]｜{:.0f}s".format(SHA[:10], len(U), len(ST), W0, W1, time.time() - t0), flush=True)
    return cal, n, w0, w1, U, ST


# ═════════════ pre：每格計數（⛔ 不讀報酬） ═════════════
def run_cells(ST, cal, w0, w1, n, o, keep_events=False):
    wE = w1 - (H if o["win"] == "60" else 120)
    rows, ledger, evrows = [], [], []
    for typ in TYPES:
        acc_t, recs = {}, []
        for sid in sorted(ST):
            S = ST[sid]
            k, acc = keep(S, typ, w0, wE, n, o)
            for a_, v_ in acc.items():
                acc_t[a_] = acc_t.get(a_, 0) + v_
            for e in k:
                recs.append((sid, e, arms(S, e, typ, o)))
        ne = len(recs)
        dl = sum(1 for s_, e, _ in recs if (ST[s_].get("status") or "").startswith("delisted") and ST[s_]["last"] < e["T"] + H)
        ledger.append(dict(型態=NAME[typ], 保留=ne, **acc_t, 保留中_終點前下市=dl))
        blk = len({(e["T"] - w0) // BLK for _, e, _ in recs})
        blk1 = len({(e["T"] + 1 - w0) // BLK for _, e, _ in recs})
        blk_max = (wE - w0) // BLK + 1
        for arm in "A" + ARMS[typ]:
            ent = [r[arm][0] for _, _, r in recs]
            aent = [r["A"][0] for _, _, r in recs]
            bought = [x is not None for x in ent]
            same = [x is not None and x == a for x, a in zip(ent, aent)]
            nb = int(sum(bought)); ns = int(sum(same))
            wait = [x - e["T"] for (x, (_, e, _)) in zip(ent, recs) if x is not None]
            why = {}
            for _, _, r in recs:
                if r[arm][0] is None:
                    why[r[arm][1]] = why.get(r[arm][1], 0) + 1
            rows.append({"型態": NAME[typ], "typ": typ, "買法": arm, "買法名": ARM_NAME[arm], "事件數": ne,
                         "相異檔數": len({s for s, _, _ in recs}), "買到數": nb, "買到比例": nb / ne if ne else np.nan,
                         "與A同日數": ns, "同日比例_全部": ns / ne if ne else np.nan, "同日比例_買到中": ns / nb if nb else np.nan,
                         "平均等待天數(進場日−T)": float(np.mean(wait)) if wait else np.nan,
                         "沒買到原因": json.dumps(why, ensure_ascii=False, sort_keys=True),
                         "區段數": blk, "區段數_T+1": blk1, "區段上限": blk_max, "n_eff": min(ne, blk)})
        if keep_events:
            for sid, e, r in recs:
                row = {"sid": sid, "market": ST[sid]["market"], "type": typ, "T": str(cal[e["T"]].date()),
                       "first": str(cal[max(e["first"], 0)].date()), "sig": str(cal[e["sig"]].date()), "N": e["N"]}
                for arm in "A" + ARMS[typ]:
                    x, why, cd = r[arm]
                    row[f"entry_{arm}"] = str(cal[x].date()) if x is not None else ""
                    row[f"cond_{arm}"] = str(cal[cd].date()) if cd is not None else ""
                    row[f"why_{arm}"] = why or ""
                evrows.append(row)
    C = pd.DataFrame(rows)
    judge = C["買法"] != "A"
    C["退化"] = judge & (C["同日比例_全部"] >= DEGEN)
    C["區段不足"] = judge & (C["區段數"] < MIN_BLK)
    C["狀態"] = np.where(~judge, "基準（不判）", np.where(C["退化"], "依構造退化（≥95% 與 A 同日）⇒ 不計 N",
                       np.where(C["區段不足"], "依構造不可判定（＜30 段）⇒ 不計 N", "可判定")))
    return C, pd.DataFrame(ledger), pd.DataFrame(evrows)


def bonf(k):
    if k <= 0:
        return None, None
    a = 0.05 / k
    return a, NormalDist().inv_cdf(1 - a / 2)


# ═════════════ fixture（F1～F11） ═════════════
FX = []


def _chk(name, cond, detail=""):
    FX.append({"名": name, "過": bool(cond), "細": detail})
    print(("✅ " if cond else "❌ ") + name + ("｜" + detail if detail else ""), flush=True)
    return cond


def _mk(n=90):
    o = np.full(n, 106.0); h = np.full(n, 107.0); l = np.full(n, 105.5); c = np.full(n, 106.5); v = np.full(n, 1000.0)
    return o, h, l, c, v


def _S(o, h, l, c, v, trd=None, up_o=None):
    S = prep(o, h, l, c, v); n = len(c)
    S["trd"] = np.isfinite(np.asarray(c, float)) if trd is None else trd
    S["up_o"] = np.zeros(n, bool) if up_o is None else up_o
    z = np.zeros(n, np.int32)
    S.update(cs_pb=z.copy(), cs_g5=z.copy(), cs_d=z.copy(), cs_a=z.copy())
    return S


def _halt(arrs, d):
    for a in arrs:
        a[d] = np.nan


def selftest():
    FX.clear()
    T, N = 10, 100.0
    ev = {"T": T, "N": N, "first": 0, "sig": T}
    o0 = dict(BASE)

    def run(S, typ="w", e=ev, **kw):
        return arms(S, e, typ, dict(o0, **kw))

    # F1 B：幅度 3%、5 日窗、當天就成立
    o, h, l, c, v = _mk(); c[T] = 101; c[T + 1] = 101; c[T + 2] = 103.5
    _chk("F1a B：T＋2 收盤 103.5 ≥ 103 ⇒ T＋3 買", run(_S(o, h, l, c, v))["B"][0] == T + 3)
    o, h, l, c, v = _mk(); c[T:T + 5] = [101, 101.5, 102, 102.5, 102.9]
    _chk("F1b B：T～T＋4 全 ＜ 103、T＋5 才 106.5 ⇒ 沒買（5 日窗有作用）", run(_S(o, h, l, c, v))["B"][0] is None)
    o, h, l, c, v = _mk(); c[T] = 104
    _chk("F1c B：T 當天 104 ⇒ T＋1 買（與 A 同日）", run(_S(o, h, l, c, v))["B"][0] == T + 1)
    # F2 C：連 3 天收盤 ＞ N；停牌在日曆／K 棒兩種數法
    o, h, l, c, v = _mk(); c[T:T + 3] = [101, 100.5, 100.2]
    _chk("F2a C：T、T＋1、T＋2 都 ＞ 100 ⇒ T＋3 買", run(_S(o, h, l, c, v))["C"][0] == T + 3)
    o, h, l, c, v = _mk(); c[T:T + 3] = [101, 100.0, 100.2]
    _chk("F2b C：T＋1 收盤 ＝ N（不是 ＞）⇒ 沒買", run(_S(o, h, l, c, v))["C"][0] is None)
    o, h, l, c, v = _mk(); c[T] = 101; _halt((o, h, l, c, v), T + 1)
    S = _S(o, h, l, c, v)
    _chk("F2c C：T＋1 停牌 ⇒ 日曆數法沒買、K 棒數法 T、T＋2、T＋3 ⇒ T＋4 買",
         run(S, days="cal")["C"][0] is None and run(S, days="bar")["C"][0] == T + 4)
    # F3 D：≥ 1.5 倍；均量兩種算法
    o, h, l, c, v = _mk(); c[T] = 101; v[T] = 1500
    _chk("F3a D：量 1500 ＝ 1.5 × 1000 ⇒ T＋1 買", run(_S(o, h, l, c, v))["D"][0] == T + 1)
    v[T] = 1499
    _chk("F3b D：量 1499 ⇒ 沒買", run(_S(o, h, l, c, v))["D"][0] is None)
    o, h, l, c, v = _mk(); c[T] = 101; v[T] = 1500; _halt((o, h, l, c, v), T - 3)
    S = _S(o, h, l, c, v)
    _chk("F3c D：T−3 停牌 ⇒ 日曆均量不可算（沒買）、K 棒均量可算（T＋1 買）",
         run(S, vm="cal")["D"][0] is None and run(S, vm="bar")["D"][0] == T + 1)

    # F4 E：錘子、量縮、回到頸線、跌破、20 日窗
    def e_case(R=T + 5, lowR=100.5, hR=102.05, vR=900.0, brk_day=None):
        o, h, l, c, v = _mk(); c[T] = 101
        o[R], c[R], h[R], l[R], v[R] = 101.5, 102.0, hR, lowR, vR
        if brk_day is not None:
            c[brk_day] = 96.9
        return _S(o, h, l, c, v)
    _chk("F4a E：T＋5 錘子（下影 1.0 ＝ 2×實體、上影 0.05）、最低 100.5、收 102、量 900 ＜ 1000 ⇒ T＋6 買", run(e_case())["E"][0] == T + 6)
    _chk("F4b E：同上但量 1000（不是 ＜）⇒ 沒買", run(e_case(vR=1000.0))["E"][0] is None)
    _chk("F4c E：同上但上影 0.3 ＞ 10% 全長 ⇒ 不是錘子 ⇒ 沒買", run(e_case(hR=102.3))["E"][0] is None)
    _chk("F4d E：T＋3 收盤 96.9 ＜ 97 ⇒ 跌破 ⇒ 沒買（即使 T＋5 有錘子）", run(e_case(brk_day=T + 3))["E"][:2] == (None, "跌破頸線"))
    _chk("F4e E：錘子在 T＋20 ⇒ T＋21 買；在 T＋21 ⇒ 沒買（20 日窗）",
         run(e_case(R=T + 20))["E"][0] == T + 21 and run(e_case(R=T + 21))["E"][0] is None)
    o, h, l, c, v = _mk(); c[T] = 101
    o[T + 5], h[T + 5], l[T + 5], c[T + 5] = 103.5, 104.05, 102.5, 104.0; v[T + 5] = 900
    S = _S(o, h, l, c, v)
    _chk("F4f E：錘子形成立但最低 102.5 ＞ 102 ⇒ 沒回到頸線 ⇒ 沒買", bool(S["ham"][T + 5]) and run(S)["E"][0] is None)
    o, h, l, c, v = _mk(); c[T] = 101
    o[T + 4], h[T + 4], l[T + 4], c[T + 4] = 103.0, 103.2, 101.8, 102.0
    o[T + 5], h[T + 5], l[T + 5], c[T + 5] = 101.9, 103.3, 101.0, 103.2; v[T + 5] = 900
    S = _S(o, h, l, c, v)
    _chk("F4g E：T＋4 黑、T＋5 白吞噬（非錘子）⇒ T＋6 買", (not S["ham"][T + 5]) and bool(S["eng_bar"][T + 5]) and run(S)["E"][0] == T + 6)
    c[T + 5] = 102.9; S = _S(o, h, l, c, v)
    _chk("F4h E：白 K 收 102.9 ＜ 前黑 K 實體頂 103 ⇒ 不吞噬 ⇒ 沒買", run(S)["E"][0] is None)
    # F5 F：B、D 成立之後的等回測
    o, h, l, c, v = _mk(); c[T] = 101; v[T] = 2000
    o[T + 1], h[T + 1], l[T + 1], c[T + 1] = 103.0, 103.55, 101.9, 103.5; v[T + 1] = 900     # b＝T＋1 本身也是回測錘子
    S = _S(o, h, l, c, v)
    r = run(S)
    _chk("F5a F：b＝T＋1 當天就是回測錘子 ⇒ E 在 T＋2 買、F 要 R ＞ b ⇒ 沒買", r["E"][0] == T + 2 and r["F"][0] is None, str((r["E"], r["F"])))
    o, h, l, c, v = _mk(); c[T] = 101; v[T] = 2000; c[T + 1] = 103.5
    o[T + 3], c[T + 3], h[T + 3], l[T + 3], v[T + 3] = 101.5, 102.0, 102.05, 100.5, 900
    r = run(_S(o, h, l, c, v))
    _chk("F5b F：b＝T＋1、D 成立、T＋3 錘子 ⇒ F 在 T＋4 買", r["F"][0] == T + 4 and r["B"][0] == T + 2)
    v[T] = 1000; r = run(_S(o, h, l, c, v))
    _chk("F5c F：D 不成立 ⇒ F 沒買（E 照買）", r["F"][0] is None and r["E"][0] == T + 4)
    o, h, l, c, v = _mk(); c[T] = 101; v[T] = 2000; c[T + 1] = 103.5
    o[T + 21], c[T + 21], h[T + 21], l[T + 21], v[T + 21] = 101.5, 102.0, 102.05, 100.5, 900
    S = _S(o, h, l, c, v)
    _chk("F5d F：錘子在 T＋21 ＝ b＋20 ⇒ 讀法甲 T＋22 買、讀法乙 沒買（窗到 T＋20）",
         run(S, F="甲")["F"][0] == T + 22 and run(S, F="乙")["F"][0] is None)
    # F6 進場日不可成交
    o, h, l, c, v = _mk(); c[T] = 101; c[T + 1] = 101; c[T + 2] = 103.5
    up = np.zeros(len(c), bool); up[T + 3] = True
    S = _S(o, h, l, c, v, up_o=up)
    _chk("F6a 進場日 T＋3 開盤漲停 ⇒ zero 沒買／next T＋4／limitbuy T＋3",
         run(S, untrd="zero")["B"][0] is None and run(S, untrd="next")["B"][0] == T + 4 and run(S, untrd="limitbuy")["B"][0] == T + 3)
    o, h, l, c, v = _mk(); c[T] = 101; c[T + 1] = 101; c[T + 2] = 103.5; _halt((o, h, l, c, v), T + 3)
    S = _S(o, h, l, c, v)
    _chk("F6b 進場日 T＋3 停牌 ⇒ limitbuy 仍沒買／next T＋4", run(S, untrd="limitbuy")["B"][0] is None and run(S, untrd="next")["B"][0] == T + 4)
    up = np.zeros(90, bool); up[T + 1] = True
    o, h, l, c, v = _mk(); c[T] = 101
    S = _S(o, h, l, c, v, up_o=up)
    _chk("F6c A：T＋1 開盤漲停、Q3 zero ⇒ A 沒買；excl ⇒ A＝T＋1（剔除在 keep 做）",
         run(S, a_untrd="zero")["A"][0] is None and run(S, a_untrd="excl")["A"][0] == T + 1)
    # F7 形狀
    o, h, l, c, v = _mk(); o[5] = h[5] = l[5] = c[5] = 100.0
    o[6], h[6], l[6], c[6] = 100.0, 100.05, 98.0, 100.05   # 十字：B 0.05 ≤ 0.1×2.05
    o[7], h[7], l[7], c[7] = 100.0, 100.35, 98.0, 100.3    # B 0.3、R 2.35、下影 2.0、上影 0.05 ⇒ 錘子
    S = _S(o, h, l, c, v)
    _chk("F7 錘子：一字線不是、十字不是、B 0.3／下影 2.0／上影 0.05 是", (not S["ham"][5]) and (not S["ham"][6]) and bool(S["ham"][7]))
    o, h, l, c, v = _mk()
    o[20], h[20], l[20], c[20] = 103.0, 103.2, 101.8, 102.0; _halt((o, h, l, c, v), 21)
    o[22], h[22], l[22], c[22] = 101.9, 103.3, 101.0, 103.2
    S = _S(o, h, l, c, v)
    _chk("F8 吞噬：中間停一天 ⇒ K 棒前一根成立、日曆前一日不成立", bool(S["eng_bar"][22]) and not S["eng_cal"][22])
    # F9 箱型 Q7
    o, h, l, c, v = _mk(); c[T - 2] = 104; c[T:T + 5] = 101
    eb = {"T": T, "N": N, "first": 0, "sig": T - 2}
    S = _S(o, h, l, c, v)
    _chk("F9 箱型 B：T 讀法（確認日起 5 日都 101）沒買；sig 讀法（訊號日 104）⇒ T＋1 買",
         run(S, "box", eb, boxT="T")["B"][0] is None and run(S, "box", eb, boxT="sig")["B"][0] == T + 1)
    # F10 事件層：合併 20 日、硬斷點
    o, h, l, c, v = _mk(200); S = _S(o, h, l, c, v)
    S["A"] = {"w": [{"T": 20, "first": 5, "N": 1.0, "sig": 20}, {"T": 40, "first": 25, "N": 1.0, "sig": 40},
                    {"T": 41, "first": 26, "N": 1.0, "sig": 41}]}
    k, acc = keep(S, "w", 0, 139, 200, dict(o0))
    ok1 = [e["T"] for e in k] == [20, 41] and acc["合併掉"] == 1
    pb = np.zeros(200, bool); pb[95] = True; S["cs_pb"] = np.cumsum(pb).astype(np.int32)
    k, acc = keep(S, "w", 0, 139, 200, dict(o0))
    k2, acc2 = keep(S, "w", 0, 139, 200, dict(o0, brk="乙"))
    ok2 = [e["T"] for e in k] == [20] and acc["剔除_未來窗斷點"] == 1 and [e["T"] for e in k2] == [20] and acc2["剔除_硬斷點(乙)"] == 1
    _chk("F10 keep：T＝40 落在 (20, 40] 被合併、41 保留；(41, 101] 內第 95 根價格斷點 ⇒ 41 被剔除（甲 未來窗／乙 硬斷點）", ok1 and ok2,
         f"{[e['T'] for e in k]} {acc}")
    o, h, l, c, v = _mk(200); S = _S(o, h, l, c, v)
    S["A"] = {"w": [{"T": 20, "first": 5, "N": 1.0, "sig": 20}, {"T": 30, "first": 25, "N": 1.0, "sig": 30}]}
    pb = np.zeros(200, bool); pb[15] = True; S["cs_pb"] = np.cumsum(pb).astype(np.int32)
    kx, _ = keep(S, "w", 0, 139, 200, dict(o0, merge="X"))
    kp, ap = keep(S, "w", 0, 139, 200, dict(o0, merge="P"))
    _chk("F11 Q10：T＝20 型態視窗有斷點被剔除 ⇒ X 讀法 T＝30 保留、P 讀法 T＝30 被合併",
         [e["T"] for e in kx] == [30] and kp == [] and ap["合併掉"] == 1)
    return all(x["過"] for x in FX)


# ═════════════ 主程式 ═════════════
def md_table(df):
    cols = list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        L.append("| " + " | ".join("{:,}".format(r[c]) if isinstance(r[c], (int, np.integer)) else str(r[c]) for c in cols) + " |")
    return "\n".join(L)


def fmt_cells(C):
    L = ["| 型態 | 買法 | 事件數 | 區段數 | 買到比例 | 同日比例（全部） | 同日比例（買到中） | 平均等待（進場日−T） | 狀態 |",
         "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in C.iterrows():
        L.append("| {} | {} | {:,} | {} | {:.1%} | {:.1%} | {} | {} | {} |".format(
            r["型態"], r["買法名"], r["事件數"], r["區段數"], r["買到比例"], r["同日比例_全部"],
            "—" if pd.isna(r["同日比例_買到中"]) else "{:.1%}".format(r["同日比例_買到中"]),
            "—" if pd.isna(r["平均等待天數(進場日−T)"]) else "{:.2f}".format(r["平均等待天數(進場日−T)"]), r["狀態"]))
    return "\n".join(L)


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "pre":
        raise SystemExit("用法：researchBF.py pre [--procs 2] [--limit N]（body 段尚未寫：等讀法裁定）")
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    tag = "_limit" if lim else ""
    os.makedirs(OUT, exist_ok=True)
    chk = {"登錄": REG, "快照": SHA, "D.DATA": D.DATA}
    assert os.path.realpath(D.DATA) == os.path.realpath(H2.H2D) and SHA.startswith("edc6f8002f"), "⛔ 快照不對"
    # ① 本支 fixture
    ok_fx = selftest()
    chk["fixture"] = {"全過": ok_fx, "條": FX}
    assert ok_fx, "⛔ fixture 不過 ⇒ 不算"
    # ② T1
    from backtest import selftest_patterns_x as STX
    t1, _ = STX.run_all()
    chk["T1"] = t1
    assert all(t1[k] for k in TYPES), "⛔ T1 不過：{}".format(t1)
    cal, n, w0, w1, U, ST = load_all(procs, lim)
    chk.update({"gate3母體": len(U), "可用檔數": len(ST), "判定窗": [W0, W1], "w0": w0, "w1": w1, "窗日數": w1 - w0 + 1})
    # ③ 0050 錨
    from backtest import rerun17 as R17
    R17.use_snapshot()
    bw = R17.bench_row(cal, R17.load_bench(cal), w0, w1 + 1)
    same = repr(bw["cagr"]) == repr(R17.ANCHOR[0]) and repr(bw["mdd"]) == repr(R17.ANCHOR[1])
    chk["0050錨"] = {"年化": bw["cagr"], "回落": bw["mdd"], "釘死值": list(R17.ANCHOR), "逐位元": same}
    print("[0050 錨] {!r}／{!r}｜逐位元 {}".format(bw["cagr"], bw["mdd"], same), flush=True)
    # ④ 事件層對帳（researchX Y1～Y5 的設定 ⇒ resultsX/freq.json）
    if not lim:
        fr = json.load(open("backtest/resultsX/freq.json", encoding="utf-8"))
        rec = {}
        for typ in TYPES:
            tot, kept = {}, 0
            for s in sorted(ST):
                k, a = RX.keep_A(dict(ST[s], cs_g5=ST[s]["cs_g5_x"]), typ, w0, w1 - RX.HMAX, n)   # researchX 沒有 delist on
                kept += len(k)
                for k_, v_ in a.items():
                    tot[k_] = tot.get(k_, 0) + v_
            ref = fr[f"甲_{typ}"]
            rec[typ] = {"本支保留": kept, "freq保留": ref["保留"], "帳相同": tot == ref["帳"], "保留相同": kept == ref["保留"]}
            print("[對帳] {} 保留 {} vs {}｜帳相同 {}".format(NAME[typ], kept, ref["保留"], tot == ref["帳"]), flush=True)
        chk["對帳_researchX"] = rec
        assert all(v["帳相同"] and v["保留相同"] for v in rec.values()), "⛔ 事件層與 researchX 對不上 ⇒ 不算"
    # ⑤ 主表（◇ 暫行讀法）
    C, LG, EV = run_cells(ST, cal, w0, w1, n, BASE, keep_events=True)
    k_judge = int((C["狀態"] == "可判定").sum())
    a_b, z_b = bonf(k_judge)
    C.to_csv(os.path.join(OUT, f"pre_cells{tag}.csv"), index=False)
    LG.to_csv(os.path.join(OUT, f"pre_ledger{tag}.csv"), index=False)
    EV.to_csv(os.path.join(OUT, f"pre_events{tag}.csv.gz"), index=False)
    print(C[["型態", "買法", "事件數", "區段數", "買到比例", "同日比例_全部", "狀態"]].to_string(), flush=True)
    # ⑥ 敏感度：每處讀法單獨換一個
    SR = []
    for key, q, opts in READINGS:
        for val, _ in opts:
            o = dict(BASE, **{key: val})
            Ck = C if val == BASE[key] else run_cells(ST, cal, w0, w1, n, o)[0]
            kj = int((Ck["狀態"] == "可判定").sum())
            for _, r in Ck.iterrows():
                SR.append({"讀法": q, "鍵": key, "選項": val, "是否◇": val == BASE[key], "型態": r["型態"], "買法": r["買法"],
                           "事件數": r["事件數"], "區段數": r["區段數"], "買到比例": r["買到比例"], "同日比例_全部": r["同日比例_全部"],
                           "同日比例_買到中": r["同日比例_買到中"], "狀態": r["狀態"], "該讀法下可判定格數": kj})
            print("[敏感度] {} = {}｜可判定 {} 格".format(key, val, kj), flush=True)
    SRd = pd.DataFrame(SR)
    SRd.to_csv(os.path.join(OUT, f"pre_sensitivity{tag}.csv"), index=False)
    chk["主表"] = {"可判定格數": k_judge, "Bonferroni_alpha": a_b, "Bonferroni_z": z_b,
                 "退化格": C.loc[C["退化"], ["型態", "買法"]].values.tolist(), "區段不足格": C.loc[C["區段不足"], ["型態", "買法"]].values.tolist()}
    json.dump(chk, open(os.path.join(OUT, f"pre_check{tag}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    write_report(C, LG, SRd, chk, k_judge, a_b, z_b, tag)
    print("[pre] 完成｜可判定 {} 格｜Bonferroni α {}".format(k_judge, a_b), flush=True)


def write_report(C, LG, SRd, chk, k, a_b, z_b, tag):
    L = []
    A = L.append
    A("# PREREG突破過濾｜開跑前檢查（pre 段）\n")
    A(f"> 判準：{REG}。⛔ 本段沒有讀、也沒有算任何報酬；表中數字全部引自 `pre_cells{tag}.csv`／`pre_ledger{tag}.csv`／`pre_sensitivity{tag}.csv`／`pre_check{tag}.json`。")
    A("> ⚠ 這份表是用【◇ 暫行讀法】算的計數，⛔ 不是讀法已選定；Q1～Q14 要裁定後才跑本體。\n")
    A("## 一、查核\n")
    fx = chk["fixture"]
    A("- 本支 fixture（researchBF.selftest，F1～F11，每條成對）：{}／{} 過".format(sum(x["過"] for x in fx["條"]), len(fx["條"])))
    A("- T1（selftest_patterns_x.run_all）：{}".format(chk["T1"]))
    if "對帳_researchX" in chk:
        A("- 事件層對帳（照 researchX Y1～Y5 設定重做 ⇒ resultsX/freq.json 甲）：" + "；".join(
            "{} 保留 {} ＝ {}、剔除帳{}".format(NAME[t], v["本支保留"], v["freq保留"], "逐項相同" if v["帳相同"] else "⛔ 不同")
            for t, v in chk["對帳_researchX"].items()))
    b = chk["0050錨"]
    A("- 0050 主窗錨：年化 {!r}、回落 {!r} ⇒ 與釘死值逐位元{}".format(b["年化"], b["回落"], "相同" if b["逐位元"] else "⛔ 不同"))
    A("- 快照 {}；gate3 {:,} 檔、可用 {:,} 檔；判定窗 {}～{}（{} 日）\n".format(chk["快照"][:10], chk["gate3母體"], chk["可用檔數"], *chk["判定窗"], chk["窗日數"]))
    A("## 二、事件帳（◇ 暫行讀法）\n")
    A(md_table(LG))
    A("\n## 三、14 格退化表（◇ 暫行讀法；A 是基準、不判）\n")
    A(fmt_cells(C))
    A("\n- 可判定格數 ＝ **{}**；Bonferroni 雙尾 α ＝ 0.05／{} ＝ {}；z ＝ {}".format(
        k, k, "—" if a_b is None else "{:.6f}".format(a_b), "—" if z_b is None else "{:.4f}".format(z_b)))
    A("- 沒買到的原因逐格在 pre_cells.csv「沒買到原因」欄。\n")
    A("## 四、登錄沒寫清楚的地方（⛔ 未選；◇ 只是 pre 暫用）\n")
    for key, q, opts in READINGS:
        A(f"**{q}**（鍵 `{key}`）")
        for val, txt in opts:
            sub = SRd[(SRd["鍵"] == key) & (SRd["選項"] == val)]
            kj = int(sub["該讀法下可判定格數"].iloc[0]) if len(sub) else -1
            A("- {}`{}`：{}　⇒ 可判定 {} 格".format("◇ " if val == BASE[key] else "", val, txt, kj))
        A("")
    for q, txt in READINGS_TEXT:
        A(f"**{q}**：{txt}\n")
    A("## 五、敏感度：每處換成另一讀法時，會變的格\n")
    base = SRd[SRd["是否◇"]].drop_duplicates(["型態", "買法"]).set_index(["型態", "買法"])
    for key, q, opts in READINGS:
        for val, _ in opts[1:]:
            sub = SRd[(SRd["鍵"] == key) & (SRd["選項"] == val)].set_index(["型態", "買法"])
            ch = []
            for ix, r in sub.iterrows():
                b0 = base.loc[ix]
                if (r["狀態"] != b0["狀態"] or abs(r["買到比例"] - b0["買到比例"]) >= 0.005
                        or abs(r["同日比例_全部"] - b0["同日比例_全部"]) >= 0.005 or r["事件數"] != b0["事件數"]):
                    ch.append("{}×{}：事件 {:,}→{:,}、買到 {:.1%}→{:.1%}、同日 {:.1%}→{:.1%}{}".format(
                        ix[0], ix[1], b0["事件數"], r["事件數"], b0["買到比例"], r["買到比例"], b0["同日比例_全部"], r["同日比例_全部"],
                        "、狀態 {}→{}".format(b0["狀態"], r["狀態"]) if r["狀態"] != b0["狀態"] else ""))
            A(f"**{q} ⇒ `{val}`**：" + ("變動 ≥ 0.5 個百分點、事件數或狀態改變的格：" if ch else "沒有一格的買到比例／同日比例變動 ≥ 0.5 個百分點、狀態也不變"))
            for x in ch:
                A(f"- {x}")
            A("")
    open(os.path.join(OUT, f"PRE_REPORT{tag}.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

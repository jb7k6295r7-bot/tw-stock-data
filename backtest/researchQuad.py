# -*- coding: utf-8 -*-
"""PREREG四類單獨（台股策略線登錄 seq2 sha 85d8b357fa51e67d；裁定線 seq216 發號、N_前段 ＋4；附則：探索段 26 種全部照報、同分取觸發比例較低者）。
停損、停利、減碼、加碼四類，不綁任何選股策略：全市場任意進場、單筆層配對差為主判；探索段挑、確認段驗；組合層只描述。回測線，2026-09-27。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchQuad.py pre|explore|confirm|port|all [--procs 2] [--limit N]

═══ 底（登錄 §一；裁定回覆 (a)(甲)）═══
  資料 edc6f8002f 快照（researchH2 把 D.DATA 指過去）；還原價；gate3；成本 0.585%（每一塊買進的錢賣出時付一次）
  母體 ＝ W1 eligible（resultsp4/panel.csv.gz 的 eligible ＝ liq_ok ∧ bars_ok ∧ inst_ok）∩ gate3
  ⭐ (a) 量測日 ＝ 每月第一個交易日（面板 measure_date），【收盤】判 eligible ⇒ 次一交易日（第二個交易日）開盤進場 e
     ⇒ 比登錄字面「第一個交易日開盤」晚一天，為了不前視（eligible 用到量測日當天收盤）；同 W1、探索批
  進場 e 開盤漲停或停牌（或開盤無效）⇒ 該檔該月不建；P0 ＝ 還原 open(e)；出場 x ＝ e＋119（交易日曆；抱 120 根）；
     x 日沒成交 ⇒ x 以前最後一根有效收盤（delist on）；硬斷點 [e, x] ⇒ 剔除（researchH2 R3，計數）
  ⭐ (甲) 兩段只收整筆落在段內的持有：探索段 e ≥ 2017-03-02 且 x ≤ 2021-12-30；確認段 e ≥ 2022-01-03 且 x ≤ 2026-08-24
  基準 ＝ 買了抱 120 根；描述另報抱 60 根（x60 ＝ e＋59）的基準報酬
═══ 規則（登錄 §二，26 種；觸發一律 t−1 收盤條件成立 ⇒ t 開盤成交；⛔ 之後不再加）═══
  條件只在有效 K 棒（收盤有限）上判；判定日 d ∈ [e, x−1]；成交日 s ＝ d 之後第一個可成交開盤（賣：有成交、開盤非跌停；買：有成交、開盤非漲停；
  開盤有效）；s ≥ x ⇒ 不做（遞延撞到出場日）；比例線一律 P×pct/100（yfstop_lines.pct_of 同式）
  停損（全賣）：SL5／10／15／20 收盤 ≤ P0×(100−k)/100｜TR10／20 收盤 ≤ 進場以來（含進場日收盤）有效 K 棒最高收盤×(100−k)/100
               （＝ yfstop_lines.t20_levels）｜AT2／AT3 ATR 追蹤（＝ listexit_lines.trail_levels，Wilder 14、起點甲、嚴格新高才上調、收盤 ＜ 線）
               ｜MA20／MA50 收盤 ＜ 均線（有效 K 棒、含當根；均線 ＝ fsum÷n；arm＝state，＝ yfstop_lines.ma_levels）
  停利（全賣）：TP20／30／50／100 收盤 ≥ P0×(100＋k)/100
  減碼（賣一半、每筆一次）：RU15／30／50 收盤 ≥ P0×(100＋k)/100｜RD10／20 收盤 ≤ P0×(100−k)/100
     RG60／RG200：0050（還原收盤 ffill）收盤 ＜ MA_n（research11.regime_below）⇒ 次日開盤賣一半；站回 ⇒ 次日開盤用賣得的錢全部補回；
       同一筆可來回多次；進場時（e−1 收盤）已在線下 ⇒ 只買半份、另半份現金等站回（P9 2-C ⓕⓖⓗ 同一套）；做不成就隔天再試（到 x 前）
  加碼（加半份 ＝ 0.5 單位資金、每筆一次）：AU10／20 收盤 ≥ P0×(100＋k)/100｜AD10／20 收盤 ≤ P0×(100−k)/100
     ｜AH40 進場後第 40 根有效 K 棒（進場日 ＝ 第 1 根；登錄「滿 40 根」）收盤 ＞ P0 ⇒ 次一個可買開盤加（只判這一次）
  報酬（每筆以進場資金 1 為單位的損益）：賣掉的部分從賣出到出場記 0；加碼那半份從加碼日起算；成本 ＝ 0.585% ×（買進金額合計）
  配對差 diff ＝ 加規則的報酬 − 買了就抱的報酬（同一筆）；「觸發」＝ 該筆真的成交了至少一次該規則的動作
═══ 判定（登錄 §三）═══
  探索段：每類挑 diff 平均最高的一種（同分 ⇒ 觸發比例較低者；再同 ⇒ 規則序）；平均 ≤ 0 ⇒「探索段就沒有比抱著好 ⇒ 不做」（⛔ 不進確認、不計 N）
  確認段（⛔ 探索段挑完才算）：挑出的那一種；CI ＝ 以進場月分群的 CR0；出口 ＝ PREREGH1 §五（avgdown.exit_result；n_eff ＝ min(n, 月數)）
     結果② ＝ 好、結果③ ＝ 差、結果① 或 出口① ＝ 分不出
  假訊號臂：登錄未列 ⇒ ⛔ 不跑
  組合層描述（⛔ 不判）：確認段、進確認的規則；引擎 simulate_mtm：訊號 ＝ 確認段每月全部持有、N＝60、d_max＝10、pick＝None（每月隨機 10 檔）、
     H120、200 顆（種子 r）、無 tradable；全賣類用事先算好的必觸發線（BIG）、減碼 trim_rule／regime_trim、加碼 add_rule（引擎寫法，⚠ 與單筆層在門檻
     剛好相等時可能差一筆、加碼金額是 0.5 slot）⇒ 年化、回落、對 0050（同窗）
輸出 backtest/resultsQuad/：pre.json、explore_diffs.csv.gz、explore_cells.csv、confirm_diffs.csv.gz、confirm_cells.csv、port_seeds.csv、port_cells.csv、
     summary.json、run.log、REPORT.md
"""
from __future__ import annotations

import argparse
import math
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchAvg as RA                                  # ⭐ prep（還原價、tradability、斷點、delist）；import 時 researchH2 把 D.DATA 指到快照
from backtest import avgdown as AV
from backtest import listexit_lines as L
from backtest import research11 as R11
from backtest import yfstop_lines as Y

D, H2 = RA.D, RA.H2
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsQuad")
COST = 0.00585
E0, C1, C2, W1 = "2017-03-02", "2021-12-30", "2022-01-03", "2026-08-24"
H = 120
RULES = [("停損", "SL5"), ("停損", "SL10"), ("停損", "SL15"), ("停損", "SL20"), ("停損", "TR10"), ("停損", "TR20"), ("停損", "AT2"), ("停損", "AT3"),
         ("停損", "MA20"), ("停損", "MA50"), ("停利", "TP20"), ("停利", "TP30"), ("停利", "TP50"), ("停利", "TP100"),
         ("減碼", "RU15"), ("減碼", "RU30"), ("減碼", "RU50"), ("減碼", "RD10"), ("減碼", "RD20"), ("減碼", "RG60"), ("減碼", "RG200"),
         ("加碼", "AU10"), ("加碼", "AU20"), ("加碼", "AD10"), ("加碼", "AD20"), ("加碼", "AH40")]
CODES = [c for _, c in RULES]
CLASS = dict((c, k) for k, c in RULES)
NAME = {"SL5": "固定 −5%", "SL10": "固定 −10%", "SL15": "固定 −15%", "SL20": "固定 −20%", "TR10": "追蹤 −10%", "TR20": "追蹤 −20%",
        "AT2": "2×ATR 追蹤", "AT3": "3×ATR 追蹤", "MA20": "跌破 20 日線", "MA50": "跌破 50 日線", "TP20": "漲 +20% 全賣", "TP30": "漲 +30% 全賣",
        "TP50": "漲 +50% 全賣", "TP100": "漲 +100% 全賣", "RU15": "漲 +15% 賣半", "RU30": "漲 +30% 賣半", "RU50": "漲 +50% 賣半",
        "RD10": "跌 −10% 賣半", "RD20": "跌 −20% 賣半", "RG60": "0050 跌破 60 日線賣半（站回補回）", "RG200": "0050 跌破 200 日線賣半（站回補回）",
        "AU10": "漲 +10% 加半份", "AU20": "漲 +20% 加半份", "AD10": "跌 −10% 加半份（攤平）", "AD20": "跌 −20% 加半份（攤平）", "AH40": "滿 40 根仍為正 加半份"}
MUST = "這是全市場的平均，不是對某一檔的預測"
_G: dict = {}


# ═════════════════════════════ 規則的線與觸發（單筆、向量化；fixture 對 yfstop_lines／listexit_lines 逐位元驗）
def ma_exact(c_cal, idx, n):
    """有效 K 棒上的 n 根簡單平均（含該根自己）＝ math.fsum(窗)／n（和先正確捨入一次）。
    ⚠ ⛔ 不用 yfstop_lines.ma_valid 的 cumsum 相減式：累加誤差約 1e−13 ⇒ 收盤【恰好等於】均線時（還原價在跳動單位格上常見）
      會被判成「收盤 ＜ 均線」（fixture 實例：1102 2019 年、1301）。長度、NaN 位置與 ma_valid 相同。"""
    cv = np.asarray(c_cal, float)[idx]
    ma = np.full(len(cv), np.nan)
    if len(cv) >= n:
        w = np.lib.stride_tricks.sliding_window_view(cv, n)
        ma[n - 1:] = np.fromiter((math.fsum(r) for r in w), float, count=len(w)) / n
    return ma


def pct_of(x, p):
    return x * p / 100.0


def levels(code, S, e, x, P0):
    """回 (lv 陣列（日曆 e..x−1）, le)。lv 對應判定日 d 的線；NaN ＝ 不判。"""
    c, v = S["c"], S["valid"]
    seg_c = c[e:x]; seg_v = v[e:x]; n = x - e
    if code.startswith("SL"):
        return np.full(n, pct_of(P0, 100 - int(code[2:]))), True
    if code.startswith("TR"):
        run = np.where(seg_v, seg_c, -np.inf)
        return pct_of(np.maximum.accumulate(run), 100 - int(code[2:])), True
    if code.startswith("AT"):
        A = S["atr_cal"]; k_ = S["prevbar"][e]
        if k_ < 0 or not np.isfinite(S["atr_cal"][k_]):
            return np.full(n, np.nan), False
        mult = float(code[2:])
        cur0 = P0 - mult * float(A[k_])
        prev_hi = np.maximum.accumulate(np.r_[-np.inf, np.where(seg_v, seg_c, -np.inf)[:-1]])
        newhi = seg_v & (seg_c > prev_hi)
        a_ = A[e:x]
        cand = np.where(newhi & np.isfinite(a_), seg_c - mult * a_, -np.inf)
        return np.maximum.accumulate(np.maximum(cur0, cand)), False
    if code.startswith("MA"):
        m = S["ma20"] if code == "MA20" else S["ma50"]
        return m[S["lv"][e:x]], False
    if code.startswith("TP") or code.startswith("RU") or code.startswith("AU"):
        return np.full(n, pct_of(P0, 100 + int(code[2:]))), None          # None ＝ ≥
    if code.startswith("RD") or code.startswith("AD"):
        return np.full(n, pct_of(P0, 100 - int(code[2:]))), True
    raise ValueError(code)


def first_trig(code, S, e, x, P0):
    """第一個判定日 d（日曆位置；沒有 ⇒ −1）。"""
    c = S["c"][e:x]; v = S["valid"][e:x]
    if code == "AH40":
        b = S["bars"]; i0 = int(np.searchsorted(b, e))
        if i0 + 39 >= len(b):
            return -1
        d = int(b[i0 + 39])
        return d if (d < x and S["valid"][d] and S["c"][d] > P0) else -1
    lv, le = levels(code, S, e, x, P0)
    with np.errstate(invalid="ignore"):
        hit = v & np.isfinite(lv) & ((c >= lv) if le is None else ((c <= lv) if le else (c < lv)))
    i = int(np.argmax(hit)) if hit.any() else -1
    return e + i if i >= 0 else -1


def exec_day(S, d, side, x):
    """d 之後第一個可成交開盤 s（s < x；否則 −1）。"""
    nxt = S["nxt_sell"] if side == "sell" else S["nxt_buy"]
    if d + 1 >= len(nxt):
        return -1
    s = int(nxt[d + 1])
    return s if 0 <= s < x else -1


def rule_pnl(code, S, e, x, j, P0, base):
    """回 (diff, 觸發, 動作次數)。base ＝ c[j]/P0 − 1 − COST。"""
    o, c = S["o"], S["c"]
    cj = float(c[j])
    if code.startswith("RG"):
        bl = S["below60"] if code == "RG60" else S["below200"]
        shares = 1.0 / P0; cash = 0.0; bought = 1.0; half = False; acts = 0
        if bl[e - 1]:                                    # 進場時已在線下 ⇒ 只買半份
            shares = 0.5 / P0; cash = 0.5; bought = 0.5; half = True
        pend = None
        for t in range(e + 1, x):
            want = "sell" if (bl[t - 1] and not half) else ("buy" if (not bl[t - 1] and half) else None)
            if want is None:
                continue
            ok = S["ok_sell"][t] if want == "sell" else S["ok_buy"][t]
            if not ok:
                continue
            if want == "sell":
                sh = shares / 2.0; cash += sh * o[t]; shares -= sh; half = True
            else:
                shares += cash / o[t]; bought += cash; cash = 0.0; half = False
            acts += 1
        val = shares * cj + cash - bought * COST
        return float(val - 1.0 - base), acts > 0 or bool(bl[e - 1]), acts
    d = first_trig(code, S, e, x, P0)
    if d < 0:
        return 0.0, False, 0
    cls = CLASS[code]
    s = exec_day(S, d, "buy" if cls == "加碼" else "sell", x)
    if s < 0:
        return 0.0, False, 0
    if cls in ("停損", "停利"):
        return float((o[s] / P0 - 1.0 - COST) - base), True, 1
    if cls == "減碼":
        return float(0.5 * (o[s] - cj) / P0), True, 1
    return float(0.5 * (cj / o[s] - 1.0 - COST)), True, 1          # 加碼


# ═════════════════════════════ 每檔
def stock_data(sid, market):
    cal = _G["cal"]
    S = RA.prep(sid, market, cal, _G["off"])
    if S is None:
        return None
    n = len(cal)
    S["ok_sell"] = AV.trade_ok(S["trd"], S["dn_o"], S["o"]); S["ok_buy"] = AV.trade_ok(S["trd"], S["up_o"], S["o"])
    S["nxt_sell"] = AV.next_true(S["ok_sell"]); S["nxt_buy"] = AV.next_true(S["ok_buy"])
    S["lv"] = np.asarray(S["lv"], int)
    b = S["bars"]
    prevbar = np.full(n, -1, int)
    for i in range(1, len(b)):
        prevbar[b[i]] = b[i - 1]
    S["prevbar"] = prevbar
    atr_cal = np.full(n, np.nan); ma20 = np.full(n, np.nan); ma50 = np.full(n, np.nan)
    df = D.load_stock(sid, market, cal).df                      # ATR（Wilder 14）與均線都在【有效 K 棒】上算（同 valid ＝ 收盤有限）
    h = df["high"].to_numpy(float)[b]; l_ = df["low"].to_numpy(float)[b]; cb = S["c"][b]
    S["atr_bars"] = R11.wilder_atr(h, l_, cb)
    atr_cal[b] = S["atr_bars"]
    S["ma20_bars"] = ma_exact(S["c"], b, 20); S["ma50_bars"] = ma_exact(S["c"], b, 50)
    ma20[b] = S["ma20_bars"]; ma50[b] = S["ma50_bars"]
    S["atr_cal"] = atr_cal; S["ma20"] = ma20; S["ma50"] = ma50
    S["below60"] = _G["below60"]; S["below200"] = _G["below200"]
    return S


def work(args):
    sid, market, rows, mode, codes = args          # rows：[(e, seg)]
    S = stock_data(sid, market)
    out = []
    if S is None:
        return [{"sid": sid, "market": market, "e": e, "seg": seg, "status": "無資料"} for e, seg in rows]
    ncal = len(_G["cal"])
    for e, seg in rows:
        x = e + H - 1
        r = {"sid": sid, "market": market, "e": e, "seg": seg}
        if x >= ncal:
            r["status"] = "超出日曆"; out.append(r); continue
        if not S["ok_buy"][e]:
            r["status"] = "進場日漲停或停牌"; out.append(r); continue
        if bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], e, x)[0]):
            r["status"] = "硬斷點"; out.append(r); continue
        P0 = float(S["o"][e]); j = int(S["lv"][x]); j60 = int(S["lv"][e + 59])
        r["status"] = "保留"
        for code in codes:
            if code.startswith("AT") and not np.isfinite(S["atr_cal"][max(S["prevbar"][e], 0)]):
                r[f"na_{code}"] = 1
        if mode == "pre":                               # ⛔ 不算報酬：只看觸發
            for code in codes:
                if code.startswith("RG"):
                    _, tr, n_ = rule_pnl(code, S, e, x, j, P0, 0.0)
                else:
                    d = first_trig(code, S, e, x, P0)
                    tr = d >= 0 and exec_day(S, d, "buy" if CLASS[code] == "加碼" else "sell", x) >= 0
                r[f"t_{code}"] = int(bool(tr))
        else:
            base = float(S["c"][j] / P0 - 1.0 - COST)
            r["base"] = base; r["base60"] = float(S["c"][j60] / P0 - 1.0 - COST)
            for code in codes:
                dff, tr, n_ = rule_pnl(code, S, e, x, j, P0, base)
                r[f"d_{code}"] = dff; r[f"t_{code}"] = int(bool(tr))
        out.append(r)
    return out


def _init(cal, off, below60, below200):
    _G.update(cal=cal, off=off, below60=below60, below200=below200)



# ═════════════════════════════ 閘門：向量化的線 ＝ 既有 builder（逐位元）
def gate_levels(cal, p, mk, c50ff, nsample, log, seed=20260927):
    off = RA.TR.load_official()
    _init(cal, off, R11.regime_below(c50ff, 60), R11.regime_below(c50ff, 200))
    rng = np.random.default_rng(seed)
    q = p.iloc[rng.choice(len(p), size=min(nsample, len(p)), replace=False)]
    cnt = {"持有": 0, "TR": 0, "AT": 0, "AT無法起算": 0, "MA": 0, "不一致": 0}
    bad = []
    for sid, g in q.groupby("stock_id"):
        S = stock_data(sid, mk.get(sid, "twse"))
        if S is None:
            continue
        b = S["bars"]
        for e in g["e"].astype(int):
            x = e + H - 1
            if x >= len(cal) or not S["ok_buy"][e] or not S["valid"][e]:
                continue
            P0 = float(S["o"][e]); cnt["持有"] += 1
            for pc in (10, 20):
                mine, _ = levels(f"TR{pc}", S, e, x, P0)
                ref = Y.t20_levels(S["c"], S["valid"], e, x - 1, pct=100 - pc)
                cnt["TR"] += 1
                if not np.array_equal(mine, ref):
                    bad.append((sid, e, f"TR{pc}"))
            k = int(np.searchsorted(b, e)) - 1
            for m in (2, 3):
                mine, _ = levels(f"AT{m}", S, e, x, P0)
                ref = L.trail_levels(b, S["atr_bars"], S["c"], k, P0, x - 1, mult=float(m), high_start="entry_close") if k >= 0 else None
                if ref is None:
                    cnt["AT無法起算"] += 1
                    if not np.all(np.isnan(mine)):
                        bad.append((sid, e, f"AT{m}-na"))
                    continue
                cnt["AT"] += 1
                if ref[0] != e or not np.array_equal(mine, ref[1]):
                    bad.append((sid, e, f"AT{m}"))
            if k >= 0:
                for n_, key in ((20, "ma20_bars"), (50, "ma50_bars")):
                    mine, _ = levels(f"MA{n_}", S, e, x, P0)
                    ref = Y.ma_levels(S["c"], b, S[key], k, e, x - 1, "state")
                    cnt["MA"] += 1
                    if not np.array_equal(mine, ref, equal_nan=True):
                        bad.append((sid, e, f"MA{n_}"))
    cnt["不一致"] = len(bad)
    log(f"[閘門 線＝builder] {cnt}｜前幾筆不一致 {bad[:5]}")
    return cnt, bad

# ═════════════════════════════ 母體
def setup(log):
    cal = D.load_calendar(); ncal = len(cal)
    pos = {d: i for i, d in enumerate(cal)}
    e0, c1, c2, w1 = (int(cal.searchsorted(pd.Timestamp(s))) for s in (E0, C1, C2, W1))
    assert [str(cal[i].date()) for i in (e0, c1, c2, w1)] == [E0, C1, C2, W1]
    U = RA.load_universe(None)
    from backtest import p4_features as P4F
    pnl_path = os.path.join(HERE, "resultsp4", "panel.csv.gz")
    p = P4F.read_panel(pnl_path)
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))].copy()
    p["T"] = p["measure_date"].map(pos)
    if p["T"].isna().any():
        raise SystemExit("⛔ 量測日不在日曆上")
    p["e"] = p["T"].astype(int) + 1; p["x"] = p["e"] + H - 1
    p["seg"] = np.where((p["e"] >= e0) & (p["x"] <= c1), "explore", np.where((p["e"] >= c2) & (p["x"] <= w1), "confirm", ""))
    p = p[p["seg"] != ""]
    mk = U.set_index("stock_id")["market"]
    s50 = D.load_stock("0050", "twse", cal).df
    c50ff = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
    info = {"面板": pnl_path, "面板 sha256": hashlib.sha256(open(pnl_path, "rb").read()).hexdigest()[:16], "gate3 檔數": int(len(U)),
            "候選持有（eligible∩gate3、段內）": {s: int((p["seg"] == s).sum()) for s in ("explore", "confirm")},
            "月數": {s: int(p.loc[p["seg"] == s, "measure_date"].nunique()) for s in ("explore", "confirm")},
            "位置": {"e0": e0, "c1": c1, "c2": c2, "w1": w1}}
    log(f"[母體] {info}")
    return cal, U, p, mk, c50ff, info, (e0, c1, c2, w1)


def run_pool(cal, p, mk, c50ff, procs, mode, codes, segs, limit=None):
    off = RA.TR.load_official()
    below60 = R11.regime_below(c50ff, 60); below200 = R11.regime_below(c50ff, 200)
    q = p[p["seg"].isin(segs)]
    if limit:
        q = q[q["stock_id"].isin(sorted(p["stock_id"].unique())[:limit])]
    tasks = [(sid, mk.get(sid, "twse"), list(zip(g["e"].astype(int), g["seg"])), mode, codes) for sid, g in q.groupby("stock_id")]
    if limit:
        pass
    rows = []
    with Pool(procs, initializer=_init, initargs=(cal, off, below60, below200)) as pool:
        for r in pool.imap_unordered(work, tasks, chunksize=8):
            rows += r
    return pd.DataFrame(rows).sort_values(["sid", "e"]).reset_index(drop=True)


# ═════════════════════════════ 統計
def ci_stats(d, months):
    d = np.asarray(d, float); n = len(d)
    m, se, ng = AV.cr0(d, months)
    lo, hi = m - 1.96 * se, m + 1.96 * se
    n_eff = int(min(n, ng))
    ex, rs = AV.exit_result(m, lo, hi, n, n_eff)
    return {"mean": m, "se": se, "lo": lo, "hi": hi, "n": n, "月數": int(ng), "n_eff": n_eff, "出口": ex, "結果": rs}


def verdict(rs):
    return {"結果②": "好", "結果③": "差"}.get(rs, "分不出")


def cell_rows(K, codes, cal, seg):
    rows = []
    mon = K["e"].map(lambda t: str(cal[t])[:7]).to_numpy()
    yr = K["e"].map(lambda t: cal[t].year).to_numpy()
    for code in codes:
        d = K[f"d_{code}"].to_numpy(float); t = K[f"t_{code}"].to_numpy(bool)
        c = ci_stats(d, mon)
        row = {"seg": seg, "類": CLASS[code], "code": code, "名": NAME[code], **c, "median": float(np.median(d)),
               "trig_frac": float(t.mean()), "n_trig": int(t.sum()), "diff_pos_frac": float((d > 0).mean()),
               "diff_trig_mean": float(d[t].mean()) if t.any() else np.nan, "diff_trig_median": float(np.median(d[t])) if t.any() else np.nan,
               "base_trig_mean": float(K["base"].to_numpy()[t].mean()) if t.any() else np.nan,
               "base_trig_median": float(np.median(K["base"].to_numpy()[t])) if t.any() else np.nan,
               "hold_better_frac_trig": float((d[t] < 0).mean()) if t.any() else np.nan,
               "p10": float(np.percentile(d, 10)), "p90": float(np.percentile(d, 90))}
        for m_ in ("twse", "tpex"):
            sel = K["market"].to_numpy() == m_
            row[f"mean_{m_}"] = float(d[sel].mean()) if sel.any() else np.nan; row[f"n_{m_}"] = int(sel.sum())
        for y in sorted(set(yr)):
            row[f"y{y}"] = float(d[yr == y].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def pick_best(E):
    out = {}
    for cls in ("停損", "停利", "減碼", "加碼"):
        g = E[E["類"] == cls].copy()
        g["_ord"] = [CODES.index(c) for c in g["code"]]
        g = g.sort_values(["mean", "trig_frac", "_ord"], ascending=[False, True, True])
        b = g.iloc[0]
        tie = int((g["mean"] == b["mean"]).sum())
        out[cls] = {"code": b["code"], "名": b["名"], "探索段平均": float(b["mean"]), "觸發比例": float(b["trig_frac"]), "同分數": tie,
                    "進確認": bool(b["mean"] > 0)}
    return out


# ═════════════════════════════ 組合層描述（⛔ 不判）
def port(cal, p, mk, c50ff, sel_codes, reps, procs, log, lims, limit=None):
    from backtest import rerun17 as RR
    e0, c1, c2, w1 = lims
    q = p[p["seg"] == "confirm"]
    if limit:
        q = q[q["stock_id"].isin(sorted(q["stock_id"].unique())[:limit])]
    cz, oz = {}, {}
    trig = {}
    off = RA.TR.load_official()
    _init(cal, off, R11.regime_below(c50ff, 60), R11.regime_below(c50ff, 200))
    rows = []
    for sid, g in q.groupby("stock_id"):
        S = stock_data(sid, mk.get(sid, "twse"))
        if S is None:
            continue
        cz[sid] = pd.Series(S["c"]).ffill().to_numpy(float); oz[sid] = np.asarray(S["o"], float)
        for e in g["e"].astype(int):
            x = e + H - 1
            if x >= len(cal) or not S["ok_buy"][e] or bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], e, x)[0]):
                continue
            j = int(S["lv"][x]); P0 = float(S["o"][e])
            rows.append({"sid": sid, "entry_pos": e, "xpos_H120": x, "g_H120": float(S["c"][j] / P0 - 1.0)})
            for code in sel_codes:
                if CLASS[code] in ("停損", "停利"):
                    d = first_trig(code, S, e, x, P0)
                    if d >= 0 and exec_day(S, d, "sell", x) >= 0:
                        trig[(code, sid, e)] = d
    sig = pd.DataFrame(rows)
    ncal = len(cal)
    BIG = float(np.finfo(np.float64).max)

    def kw_of(code):
        k = int(code[2:]) if code[2:].isdigit() else None
        if CLASS[code] in ("停損", "停利"):
            sl = {}
            for r in sig.itertuples():
                lv = np.full(r.xpos_H120 - r.entry_pos + 1, np.nan)
                d = trig.get((code, r.sid, r.entry_pos))
                if d is not None:
                    lv[d - r.entry_pos] = BIG
                sl[(r.sid, r.entry_pos)] = (r.entry_pos, lv)
            return {"stop_line": sl}
        if code.startswith("RG"):
            return {"regime_trim": {"hold": 0.5, "ma": int(code[2:]), "bench": c50ff}}
        if code.startswith("RU"):
            return {"trim_rule": {"kind": "gain", "x": k / 100, "frac": 0.5}}
        if code.startswith("RD"):
            return {"trim_rule": {"kind": "loss", "x": k / 100, "frac": 0.5}}
        if code.startswith("AU"):
            return {"add_rule": {"kind": "gain", "x": k / 100}}
        if code.startswith("AD"):
            return {"add_rule": {"kind": "loss", "x": k / 100}}
        return {"add_rule": {"kind": "hold", "days": 40}}
    arms = {"base": {}}
    for code in sel_codes:
        arms[code] = kw_of(code)
    out = []
    for key, kw in arms.items():
        t0 = time.time()
        for r in range(reps):
            o = R11.simulate_mtm(sig, "H120", 60, np.random.default_rng(r), cz, oz, ncal, return_equity=True, d_max=10, **kw)
            c_, m_, v_ = RR.win_metrics(o["equity"], o["first"], o["end"], c2, w1)
            out.append({"arm": key, "r": r, "cagr": float(c_), "mdd": float(m_), "vol": float(v_), "trades": int(o["trades"])})
        log(f"  [組合層 {key}] {time.time() - t0:.0f}s")
    Pd = pd.DataFrame(out)
    bw = RR.bench_row(cal, pd.Series(c50ff).to_numpy(), c2, w1 + 1)
    return Pd, bw, len(sig)


# ═════════════════════════════ 主程式
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["gate", "pre", "explore", "confirm", "port", "all", "report"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    if a.mode == "report":                           # 只重寫 REPORT.md（讀既有 csv／json，⛔ 不重算）
        report(json.load(open(os.path.join(a.out, "summary.json"), encoding="utf-8")), a.out)
        return
    t00 = time.time()
    log(f"===== researchQuad {a.mode} procs={a.procs} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchQuad.py", "research11.py", "avgdown.py", "researchAvg.py", "yfstop_lines.py", "listexit_lines.py")}
    log(f"[程式 sha256] {src}")
    cal, U, p, mk, c50ff, info, lims = setup(log)
    S = json.load(open(os.path.join(a.out, "summary.json"), encoding="utf-8")) if os.path.exists(os.path.join(a.out, "summary.json")) else {}
    S.update({"登錄": "PREREG四類單獨 seq2 sha 85d8b357fa51e67d；裁定 seq216", "母體": info, "程式": src,
              "讀法": {"(a)": "進場比字面晚一天（第一個交易日收盤判 eligible、第二個交易日開盤進場），為了不前視",
                     "(甲)": "兩段只收整筆落在段內的持有", "假訊號臂": "登錄未列、不跑"}})
    if a.mode in ("gate", "pre", "all"):
        cnt, bad = gate_levels(cal, p, mk, c50ff, 3000 if not a.limit else 200, log)
        S["閘門_線"] = cnt
        if bad:
            json.dump(S, open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
            raise SystemExit("⛔ 閘門不過：向量化的線 ≠ builder")
    if a.mode in ("pre", "all"):
        t0 = time.time()
        K = run_pool(cal, p, mk, c50ff, a.procs, "pre", CODES, ["explore", "confirm"], a.limit)
        st = K.groupby(["seg", "status"]).size().unstack(fill_value=0)
        keep = K[K["status"] == "保留"]
        pre = {"狀態": {s: {k: int(v) for k, v in st.loc[s].items()} for s in st.index},
               "保留": {s: int((keep["seg"] == s).sum()) for s in ("explore", "confirm")},
               "月數": {s: int(keep.loc[keep["seg"] == s, "e"].map(lambda t: str(cal[t])[:7]).nunique()) for s in ("explore", "confirm")},
               "觸發比例（探索段；⛔ 不含報酬）": {c: float(keep.loc[keep["seg"] == "explore", f"t_{c}"].mean()) for c in CODES},
               "觸發比例（確認段；⛔ 不含報酬）": {c: float(keep.loc[keep["seg"] == "confirm", f"t_{c}"].mean()) for c in CODES},
               "ATR 無法起算的持有": {c: int(keep[f"na_{c}"].fillna(0).sum()) if f"na_{c}" in keep else 0 for c in ("AT2", "AT3")},
               "可判定性": {s: ("出口②（30～99 月）" if 30 <= int(keep.loc[keep["seg"] == s, "e"].map(lambda t: str(cal[t])[:7]).nunique()) < 100 else "看月數")
                         for s in ("explore", "confirm")}}
        json.dump(pre, open(os.path.join(a.out, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        S["pre"] = pre
        log(f"[pre] {json.dumps({k: pre[k] for k in ('狀態', '保留', '月數', '可判定性')}, ensure_ascii=False)}｜{time.time() - t0:.0f}s")
    if a.mode in ("explore", "all"):
        t0 = time.time()
        log(f"[探索段 開始] {time.strftime('%F %T')}（⛔ 確認段此時不算）")
        K = run_pool(cal, p, mk, c50ff, a.procs, "body", CODES, ["explore"], a.limit)
        K = K[K["status"] == "保留"].reset_index(drop=True)
        cols = ["sid", "market", "e", "base", "base60"] + [f"d_{c}" for c in CODES] + [f"t_{c}" for c in CODES]
        K[cols].to_csv(os.path.join(a.out, "explore_diffs.csv.gz"), index=False, float_format="%.17g")
        E = cell_rows(K, CODES, cal, "explore")
        E.to_csv(os.path.join(a.out, "explore_cells.csv"), index=False)
        best = pick_best(E)
        S["探索段挑選"] = best; S["探索段基準"] = {"base120_mean": float(K["base"].mean()), "base60_mean": float(K["base60"].mean()), "n": int(len(K))}
        S["探索段完成"] = time.strftime("%F %T")
        log(f"[探索段 完成] {time.time() - t0:.0f}s｜挑選 {json.dumps(best, ensure_ascii=False)}")
    if a.mode in ("confirm", "all"):
        best = S["探索段挑選"]
        sel = [v["code"] for v in best.values() if v["進確認"]]
        log(f"[確認段 開始] {time.strftime('%F %T')}｜只算挑出且探索段平均 ＞ 0 的：{sel}")
        if sel:
            K = run_pool(cal, p, mk, c50ff, a.procs, "body", sel, ["confirm"], a.limit)
            K = K[K["status"] == "保留"].reset_index(drop=True)
            cols = ["sid", "market", "e", "base", "base60"] + [f"d_{c}" for c in sel] + [f"t_{c}" for c in sel]
            K[cols].to_csv(os.path.join(a.out, "confirm_diffs.csv.gz"), index=False, float_format="%.17g")
            Cc = cell_rows(K, sel, cal, "confirm")
            Cc["verdict"] = [verdict(r) if ex != "出口①" else "分不出" for r, ex in zip(Cc["結果"], Cc["出口"])]
            Cc.to_csv(os.path.join(a.out, "confirm_cells.csv"), index=False)
            S["確認段"] = Cc[["類", "code", "mean", "lo", "hi", "n", "月數", "出口", "結果", "verdict", "trig_frac"]].to_dict("records")
            S["確認段基準"] = {"base120_mean": float(K["base"].mean()), "base60_mean": float(K["base60"].mean()), "n": int(len(K))}
        else:
            S["確認段"] = []
        S["確認段完成"] = time.strftime("%F %T")
    if a.mode in ("port", "all"):
        sel = [v["code"] for v in S["探索段挑選"].values() if v["進確認"]]
        if sel:
            Pd, bw, nsig = port(cal, p, mk, c50ff, sel, a.reps, a.procs, log, lims, a.limit)
            Pd.to_csv(os.path.join(a.out, "port_seeds.csv"), index=False)
            b = Pd[Pd["arm"] == "base"].set_index("r").sort_index()
            rows = []
            for k, g in Pd.groupby("arm", sort=False):
                g = g.set_index("r").sort_index()
                c_, m_ = float(g["cagr"].median()), float(g["mdd"].median()); ratio = c_ / abs(m_)
                c50, m50 = bw["cagr"], bw["mdd"]
                lab = "合格" if (c_ > c50 and ratio >= c50 / abs(m50)) else ("另列" if c_ > c50 else "不合格")
                dc = g["cagr"] - b["cagr"]; dm = g["mdd"] - b["mdd"]
                rows.append({"arm": k, "cagr_med": c_, "mdd_med": m_, "ratio": ratio, "label_desc": lab, "both_better": int(((dc > 0) & (dm > 0)).sum()),
                             "both_worse": int(((dc < 0) & (dm < 0)).sum()), "d_cagr_med": float(dc.median()), "d_mdd_med": float(dm.median()),
                             "c50": c50, "m50": m50})
            pd.DataFrame(rows).to_csv(os.path.join(a.out, "port_cells.csv"), index=False)
            S["組合層"] = {"訊號列": nsig, "0050 同窗": {"cagr": bw["cagr"], "mdd": bw["mdd"]}, "格": rows}
        else:
            S["組合層"] = "沒有規則進確認段 ⇒ 不跑"
    S["秒_本次"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if a.mode in ("confirm", "port", "all") and "探索段挑選" in S:
        report(S, a.out)
    log(f"[完成] {time.time() - t00:.0f}s")


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def report(S, OUT_):
    E = pd.read_csv(os.path.join(OUT_, "explore_cells.csv"))
    Cc = pd.read_csv(os.path.join(OUT_, "confirm_cells.csv")) if os.path.exists(os.path.join(OUT_, "confirm_cells.csv")) else pd.DataFrame()
    best = S["探索段挑選"]
    Ls = ["# PREREG四類單獨：停損、停利、減碼、加碼（不綁任何選股策略；全市場任意進場、單筆層）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq2（sha 85d8b357fa51e67d）；裁定 seq216。回測線。", "",
          "- (a) 進場比字面晚一天，為了不前視（第一個交易日收盤判 eligible、第二個交易日開盤進場；同 W1、探索批）",
          "- (甲) 兩段只收整筆落在段內的持有（探索段 e ≥ 2017-03-02 且出場 ≤ 2021-12-30；確認段 e ≥ 2022-01-03 且出場 ≤ 2026-08-24）",
          "- 假訊號臂：登錄未列、不跑", "", "## 事件帳（pre；⛔ 不含報酬）", "",
          "| 段 | 候選（eligible∩gate3、整筆在段內） | 進場日漲停／停牌不建 | 硬斷點剔除 | 保留 | 進場月數 | 可判定性 |", "|---|---|---|---|---|---|---|"]
    pre = S.get("pre", {})
    for sg, nm in (("explore", "探索 2017-03～2021-12"), ("confirm", "確認 2022-01～2026-08")):
        st = pre.get("狀態", {}).get(sg, {})
        Ls.append(f"| {nm} | {S['母體']['候選持有（eligible∩gate3、段內）'][sg]:,} | {st.get('進場日漲停或停牌', 0)} | {st.get('硬斷點', 0)} | "
                  f"{pre.get('保留', {}).get(sg, 0):,} | {pre.get('月數', {}).get(sg)} | {pre.get('可判定性', {}).get(sg)} |")
    Ls += ["", f"閘門：向量化的線 ＝ 既有 builder（yfstop_lines.t20_levels／listexit_lines.trail_levels／yfstop_lines.ma_levels）逐位元：{S.get('閘門_線')}", "",
           "⚠ 均線 ＝ math.fsum(窗)÷n。⛔ 沒用 yfstop_lines.ma_valid 的 cumsum 相減式：它累加誤差約 1e−13，收盤【恰好等於】均線時會被判成「跌破」"
           "（查核抓到的實例：1102、1301；還原價在跳動格上，恰好相等並不罕見）。", "",
           "## 結果句（⛔ 只照登錄 §四查表）", ""]
    for cls in ("停損", "停利", "減碼", "加碼"):
        b = best[cls]
        if not b["進確認"]:
            Ls.append(f"- **{cls}**：探索段最好的〔{b['名']}〕平均 {_p(b['探索段平均'], 3)} ≤ 0 ⇒ 探索段就沒有比抱著好 ⇒ 不做。"
                      f"一般買股票不必{cls}：沒有比買了就抱好。探索段試了 {int((E['類'] == cls).sum())} 種。（{MUST}）")
            continue
        q = Cc[Cc["code"] == b["code"]].iloc[0]
        if q["verdict"] == "好":
            Ls.append(f"- **{cls}**：一般買股票加〔{b['名']}〕，在沒看過的 2022～2026 也比買了就抱好，平均多 {_p(q['mean'], 3)}；⚠ 從 {int((E['類'] == cls).sum())} 種裡挑出來的。"
                      f"探索段試了 {int((E['類'] == cls).sum())} 種。（{MUST}）")
        else:
            Ls.append(f"- **{cls}**：一般買股票不必{cls}：沒有比買了就抱好（確認段〔{b['名']}〕平均 {_p(q['mean'], 3)}、CI [{_p(q['lo'], 3)}, {_p(q['hi'], 3)}]、"
                      f"{q['出口']}／{q['結果']} ⇒ {q['verdict']}）。探索段試了 {int((E['類'] == cls).sum())} 種。（{MUST}）")
    Ls += ["", "## 探索段 26 種（全部照報，描述；每筆配對差 ＝ 加規則 − 買了就抱；CI 以進場月分群）", "",
           "| 類 | 規則 | 配對差平均 | CI | 中位 | 觸發比例 | 被觸發那些筆：配對差平均／抱著較好的占比 | 上市／上櫃 平均 |", "|---|---|---|---|---|---|---|---|"]
    for r in E.itertuples():
        mark = "⭐ " if best[r.類]["code"] == r.code else ""
        Ls.append(f"| {r.類} | {mark}{r.名} | {_p(r.mean, 3)} | [{_p(r.lo, 3)}, {_p(r.hi, 3)}] | {_p(r.median, 3)} | {r.trig_frac:.3f} | "
                  f"{_p(r.diff_trig_mean, 3)}／{r.hold_better_frac_trig:.3f} | {_p(r.mean_twse, 3)}／{_p(r.mean_tpex, 3)} |")
    Ls += ["", f"探索段基準（買了就抱）：抱 120 根平均 {_p(S['探索段基準']['base120_mean'])}、抱 60 根平均 {_p(S['探索段基準']['base60_mean'])}（描述）、n＝{S['探索段基準']['n']}", "",
           "⭐ 挑選規則（裁定附則）：每類取平均最高；同分取觸發比例較低者（事前定）。本次同分數：" + "、".join(f"{k} {v['同分數']}" for k, v in best.items()) + "（1 ＝ 沒有同分）。", ""]
    if len(Cc):
        Ls += ["## 確認段（挑出的規則）", "", "| 類 | 規則 | 配對差平均 | CI | 出口／結果 | 判定 | 觸發比例 | 放棄組：被觸發那些筆抱到 120 根平均／中位、抱著較好 | 上市／上櫃 |",
               "|---|---|---|---|---|---|---|---|---|"]
        for r in Cc.itertuples():
            Ls.append(f"| {r.類} | {r.名} | {_p(r.mean, 3)} | [{_p(r.lo, 3)}, {_p(r.hi, 3)}] | {r.出口}／{r.結果} | {r.verdict} | {r.trig_frac:.3f} | "
                      f"{_p(r.base_trig_mean)}／{_p(r.base_trig_median)}、{r.hold_better_frac_trig:.3f} | {_p(r.mean_twse, 3)}／{_p(r.mean_tpex, 3)} |")
        Ls += ["", f"確認段基準（買了就抱）：抱 120 根平均 {_p(S['確認段基準']['base120_mean'])}、抱 60 根平均 {_p(S['確認段基準']['base60_mean'])}（描述）、n＝{S['確認段基準']['n']}", ""]
        Ls += ["### 分年（依進場年；配對差平均）", ""]
        yc = [c for c in Cc.columns if c.startswith("y")]
        Ls += ["| 段 | 規則 | " + " | ".join(c[1:] for c in yc) + " |", "|---|---|" + "---|" * len(yc)]
        for r in Cc.itertuples():
            Ls.append(f"| 確認 | {r.名} | " + " | ".join(_p(getattr(r, c), 2) for c in yc) + " |")
        ye = [c for c in E.columns if c.startswith("y")]
        Ls += ["", "| 段 | 規則（每類探索段最好的那種） | " + " | ".join(c[1:] for c in ye) + " |", "|---|---|" + "---|" * len(ye)]
        for cls in ("停損", "停利", "減碼", "加碼"):
            r = E[E["code"] == best[cls]["code"]].iloc[0]
            Ls.append(f"| 探索 | {r['名']} | " + " | ".join(_p(r[c], 2) for c in ye) + " |")
        Ls += ["", "（26 種的逐年值都在 explore_cells.csv 的 yYYYY 欄）", ""]
    if isinstance(S.get("組合層"), dict):
        Ls += ["## 組合層描述（⛔ 不判；確認段、每月隨機 10 檔、抱 120 天、200 顆）", "", "| 臂 | 年化中位 | 回落中位 | 比值 | 對 0050（描述） | 對不加 兩項皆好／皆差 |", "|---|---|---|---|---|---|"]
        for r in S["組合層"]["格"]:
            Ls.append(f"| {NAME.get(r['arm'], '不加規則')} | {_p(r['cagr_med'])} | {_p(r['mdd_med'])} | {r['ratio']:.4f} | {r['label_desc']} | {r['both_better']}／{r['both_worse']} |")
        Ls += ["", f"0050 同窗（2022-01-03～2026-08-24）：年化 {_p(S['組合層']['0050 同窗']['cagr'])}、回落 {_p(S['組合層']['0050 同窗']['mdd'])}。"
               f"訊號 ＝ 確認段全部持有 {S['組合層']['訊號列']:,} 列；N＝60、每日最多新進 10 檔（隨機）、抱 120 天、種子 0～199；「對 0050」欄只是描述（⛔ 不判）。", "",
               "⚠ 組合層的加碼用引擎 add_rule：加 0.5 ×【加碼當天的 slot】、現金不足就不加（記次數、不重試）、門檻寫法 c ≤ 0.90 × 進場價（引擎進場價）"
               "⇒ 與單筆層的「0.5 單位、一定加得到」不同，只作描述。", ""]
    else:
        Ls += ["## 組合層描述", "", f"{S.get('組合層')}", ""]
    open(os.path.join(OUT_, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Ls) + "\n")


if __name__ == "__main__":
    main()

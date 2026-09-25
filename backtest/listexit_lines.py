# -*- coding: utf-8 -*-
"""PREREG名單出場 乙（台股策略線登錄 seq1 sha db11230f58632a0d；裁定線 seq189）的停損線建構器與 #1 t−1 包裝。回測線，2026-09-26。

停損線的格式 ＝ research11.simulate_mtm 的 stop_line：dict[(sid, entry_pos)] → (start, levels)，levels[i] ＝ 日曆位置 start＋i
收盤時生效的停損價；引擎在 t 開盤讀 closes[t−1] 與 levels[t−1−start] 比，觸發 ⇒ t 開盤整檔出。

  S1  s1_lines(sig, rule, opens, closes, x=0.10)：線 ＝ (1 − x) × ep 常數；配 simulate_mtm(stop_line_le=True) ⇒「收盤 ≤ 進場價 × 0.90」
      ep 照引擎規則：進場日開盤（有限且 ＞ 0），否則當日收盤
  S2  s2_lines(sig, rule, opens, closes, bars_of, mult=2.0, high_start=…)：2×ATR 追蹤；配 stop_line_le=False（「收盤 ＜ 停損價」）
      起始 ＝ ep − mult × ATR(訊號日 k)；之後在【有效 K 棒】上，收盤創新高（嚴格 ＞）才上調到 max(舊線, 收盤 − mult × ATR(當日))，只升不降
      high_start（登錄沒寫死 ⇒ 裁定線 seq192 ① 定案（甲）＝ "entry_close"；（乙）不跑、參數留著）：
        "entry_close"（預設、定案）：高點從 −∞ 起算 ⇒ 進場日收盤就是第一個高點（同 research11 A2 的寫法）
        "above_ep"（不跑）：高點從 ep 起算 ⇒ 收盤要先超過進場價才算新高
      非有效 K 棒的日子（停牌）線不動（沿用前一根）；收盤取引擎的 closes（ffill 過的那一份），ATR 取 load_bars 的有效 K 棒
      ⭐ 同一天「先判觸發再上調」與「先上調再判」等價：新線 ＝ max(舊線, c − 2ATR) 而 c ＞ c − 2ATR ⇒ c ＜ 新線 ⇔ c ＜ 舊線
  ATR ＝ research11.wilder_atr（Wilder 遞迴 n＝14、真實高低價、TR 用前一根有效收盤、第 14 根 ＝ 前 14 個 TR 平均、前 113 根 NaN）
      ⭐ 裁定線 seq192 ②：tw-ta-exit-position 原文（TR ＝ max(今高−今低, |今高−昨收|, |今低−昨收|)；ATR_t ＝ (ATR_{t−1}×13＋TR_t)÷14、
        種子 ＝ 前 14 根 TR 簡單平均；只吃有效 K 棒；序列 ≥ 114 根）與本函式一致 ⇒ 照用；訊號日有效 K 棒 ＜ 114 根的部位照算、另報筆數
        （#1 的訊號要求 k ≥ 249 ⇒ 依構造 0 筆；ATR(訊號日) 無效的列不建線、計入 skipped）

#1 t−1 包裝：setup_t1() ＝ rerun17 同 builder、同快照、同 AND 訊號、t−1 大盤閘（reg[entry_pos − 1]）、主窗；
  sim(ctx, kw, r) ＝ simulate_mtm(sig, "H120", 10, default_rng(1000＋r), closes, opens, ncal, return_equity=True, **kw)
  ⇒ kw 全空時與 resultsN17/regime_t1/seeds.csv 的 t1 #1 逐位元相同（selftest_listexit.py t1gate 驗）
"""
from __future__ import annotations

import os

import numpy as np

from . import research11 as R

ATR_NOTE = "ATR ＝ research11.wilder_atr（Wilder n＝14、有效 K 棒、首值＝前 14 個 TR 平均、前 113 根 NaN）；裁定 seq192 ②：與 tw-ta-exit-position 原文一致"
HIGH_STARTS = ("entry_close", "above_ep")


def engine_ep(opens, closes, sid, t):
    """引擎的進場價規則：t 開盤有限且 ＞ 0 ⇒ 開盤，否則 t 收盤（research11.simulate_mtm 同一式）。"""
    ep = float(opens[sid][t])
    if not np.isfinite(ep) or ep <= 0:
        ep = float(closes[sid][t])
    return ep


def s1_lines(sig, rule, opens, closes, x=0.10):
    out = {}
    for sid, e, xp in zip(sig["sid"], sig["entry_pos"], sig[f"xpos_{rule}"]):
        e = int(e); xp = int(xp)
        if xp < 0:
            continue
        ep = engine_ep(opens, closes, sid, e)
        out[(sid, e)] = (e, np.full(xp - e + 1, (1.0 - x) * ep))
    return out


def trail_levels(idx, atr, c_cal, k, ep, last_pos, mult=2.0, high_start="entry_close"):
    """一筆持有的 2×ATR 追蹤線。idx：有效 K 棒的日曆位置（遞增）；atr：與 idx 同長；c_cal：引擎收盤（日曆長）；
    k：訊號根（idx 的索引）；ep：進場價；last_pos：最後需要的日曆位置（含）。回 (start, levels) 或 None（ATR(訊號日) 無效）。"""
    if high_start not in HIGH_STARTS:
        raise ValueError(f"high_start 只能是 {HIGH_STARTS}，收到 {high_start!r}")
    start = int(idx[k + 1])
    a0 = float(atr[k])
    if not np.isfinite(a0):
        return None
    cur = ep - mult * a0
    hi = -np.inf if high_start == "entry_close" else ep
    lv = np.empty(last_pos - start + 1)
    j = k + 1
    for d in range(start, last_pos + 1):
        if j < len(idx) and int(idx[j]) == d:          # 有效 K 棒
            cj = float(c_cal[d])
            if cj > hi:                                  # 收盤創新高（嚴格）
                hi = cj
                if np.isfinite(atr[j]):
                    cur = max(cur, cj - mult * float(atr[j]))   # 只升不降
            j += 1
        lv[d - start] = cur
    return start, lv


def s2_lines(sig, rule, opens, closes, bars_of, mult=2.0, high_start="entry_close"):
    """bars_of(sid) ⇒ research11.load_bars 的 dict（idx、h、l、c）；訊號根 k ＝ sig 的 k 欄（idx[k＋1] 必須 ＝ entry_pos）。"""
    out = {}; skipped = 0; cache = {}
    for sid, k, e, xp in zip(sig["sid"], sig["k"], sig["entry_pos"], sig[f"xpos_{rule}"]):
        k = int(k); e = int(e); xp = int(xp)
        if xp < 0:
            continue
        if sid not in cache:
            B = bars_of(sid)
            cache[sid] = None if B is None else (B["idx"], R.wilder_atr(B["h"], B["l"], B["c"]))
        if cache[sid] is None:
            skipped += 1; continue
        idx, atr = cache[sid]
        if k + 1 >= len(idx) or int(idx[k + 1]) != e:
            raise ValueError(f"{sid}：訊號根 k＝{k} 的下一根不是 entry_pos {e}")
        r = trail_levels(idx, atr, closes[sid], k, engine_ep(opens, closes, sid, e), xp, mult, high_start)
        if r is None:
            skipped += 1; continue
        out[(sid, e)] = r
    return out, skipped


# ─────────────────────────── #1 t−1 包裝（rerun17 同一套）
def setup_t1(log=print):
    from . import data as D
    from . import rerun17 as RR
    RR.use_snapshot()
    cal = D.load_calendar()
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log)
    G = RR._G
    reg = G["regime"]; AND = G["AND"]
    e = AND["entry_pos"].to_numpy()
    if e.min() < 1:
        raise SystemExit("⛔ entry_pos 有 0")
    inwin = (e >= G["w0"]) & (e <= G["w1"])
    sig = AND[reg[e - 1] & inwin]
    mk = D.load_universe().set_index("stock_id")["market"]
    return {"cal": cal, "sig": sig, "closes": G["closes"], "opens": G["opens"], "ncal": G["ncal"], "w0": G["w0"], "w1": G["w1"],
            "mk": mk, "RR": RR, "D": D}


def sim(ctx, kw, r, eng=None, audit=None):
    E = eng if eng is not None else R
    return E.simulate_mtm(ctx["sig"], "H120", 10, np.random.default_rng(1000 + r), ctx["closes"], ctx["opens"], ctx["ncal"],
                          return_equity=True, audit=audit, **kw)

# -*- coding: utf-8 -*-
"""PREREG限價（台股策略線 seq3，sha fddc47686e5339f9；裁定線 seq165、166）——限價成交判定與出場的【核心函式】（純函式、無 I/O）。

⭐ 本檔只放規則本身，讓 selftest_limit_entry.py 能用合成資料逐條驗；讀資料、彙總在 researchLimit.py。

規則（登錄 §二 逐字落地）：
  限價 P ＝ 訊號日 m 的【未還原】收盤 ×（1 − k%），照當時 tick 往下取整（tick 級距 ＝ research11._tick，與漲跌停價同一套）
  有效期 ＝ m+1 起 5 個交易日（交易日曆上的 e … e+4；e ＝ entry_pos ＝ m+1）
  成交   ＝ 第一個「當日【未還原】最低 ≤ P」的交易日；成交價 ＝ min（當日未還原開盤, P）
  該日停牌（trd＝False）或最低非有限 ⇒ 該日不可能成交，但仍佔 5 日中的一天（交易日曆上數）
  開盤＝漲停且最低 ＞ P ⇒ 自然不成交（⛔ 不另判）；開盤＝漲停但最低 ≤ P ⇒ 照規則以 P 成交（自然成立）
  5 日都沒碰到 ⇒ 放棄（報酬 0）
  M0：e 開盤市價；e 停牌／開盤非有限／開盤＝漲停（up_o）⇒ 放棄（報酬 0）
  M0'：同 M0，但開盤＝漲停也以開盤價買到（停牌、開盤非有限仍買不到）
出場（各臂共用 M0 的那一天）：x ＝ D.exit_pos(e, H) ＝ e＋H−1 的【還原收盤】，引擎規則（ref_interval_close.measure_close 逐字）：
  ① x 有成交且收盤≠跌停價 ⇒ 收盤出（ok）
  ② 否則 ⇒ 之後第一個「有成交且開盤≠跌停價」日的開盤出（exit_delayed）
  ③ 之後再也沒成交：下市 ⇒ 最後成交收盤了結（delist_settled）；ambig ⇒ 量不到（delist_ambig）；日曆尾仍賣不掉 ⇒ unresolved
報酬（成交的筆）＝ 出場還原價 ÷（成交未還原價 × F(成交日)）− 1 − 0.585%；放棄的筆 ＝ 0
"""
from __future__ import annotations
import numpy as np

COST_RT = 0.00585
VALID_DAYS = 5
KS = (1, 2, 3)
EPS = 1e-9


def tick(p: float) -> float:
    """台股升降單位（與 research11._tick 同一張表；⛔ 不 import 是為了讓 selftest 可獨立比對，兩者相等由 selftest 斷言）。"""
    return 0.01 if p < 10 else 0.05 if p < 50 else 0.1 if p < 100 else 0.5 if p < 500 else 1.0 if p < 1000 else 5.0


def limit_px(close_m_raw: float, k: int) -> float:
    """P ＝ close_m ×（1 − k%）照 tick 往下取整。tick 以【取整前】的價位決定（同 research11.limit_price 的寫法）。"""
    # ⭐ 整數運算（單位 0.0001 元）避免 99.0/0.1 ＝ 989.999… 被 floor 成 989 這種浮點誤差
    c_cent = int(round(close_m_raw * 100))                  # 台股價格最小 0.01
    raw_u = c_cent * (100 - k)                              # 單位 0.0001 元，精確
    t_u = int(round(tick(raw_u / 10000.0) * 10000))
    return (raw_u // t_u) * t_u / 10000.0


def fill_limit(e: int, P: float, ro, rl, trd, days: int = VALID_DAYS):
    """回 (t_fill, fill_raw)；沒成交回 (None, None)。ro／rl：未還原開盤／最低（日曆長度）；trd：當日有成交。
    ⭐ 只讀 e … e+days−1 這幾天的 ro／rl／trd ⇒ 成交日之後的價格不影響結果（selftest F7 突變驗）。"""
    n = len(rl)
    for t in range(e, min(e + days, n)):
        if not trd[t]:
            continue
        lo = rl[t]
        if not (np.isfinite(lo) and lo > 0):
            continue
        if lo <= P + EPS:
            op = ro[t]
            px = min(op, P) if (np.isfinite(op) and op > 0) else P
            return t, float(px)
    return None, None


def fill_m0(e: int, ro, trd, up_o, allow_limit_up: bool = False):
    """M0／M0'：回 (status, fill_raw)。status ∈ ok／halt_in／no_open／limit_up。"""
    if e >= len(ro) or not trd[e]:
        return "halt_in", None
    if not (np.isfinite(ro[e]) and ro[e] > 0):
        return "no_open", None
    if up_o[e] and not allow_limit_up:
        return "limit_up", None
    return "ok", float(ro[e])


def exit_engine(e: int, H: int, c_adj, o_adj, trd, dn_c, dn_o, last: int, dstatus: str):
    """回 (status, t_exit, px_adj)。c_adj ＝ 還原收盤（ffill 過，同 RI.load_all 的 closes）；o_adj ＝ 還原開盤。
    ⭐ 與 ref_interval_close.measure_close 的出場段逐字同（researchLimit 另有逐筆比對）。"""
    ncal = len(c_adj)
    x = e + H - 1                                  # ＝ D.exit_pos(e, H)（研究檔呼叫 D.exit_pos，這裡只給 selftest 用同式）
    if x >= ncal:
        return "beyond_cal", None, None
    if trd[x] and not dn_c[x] and np.isfinite(c_adj[x]) and c_adj[x] > 0:
        return "ok", x, float(c_adj[x])
    t = x + 1
    while t < ncal:
        if trd[t] and not dn_o[t] and np.isfinite(o_adj[t]) and o_adj[t] > 0:
            return "exit_delayed", t, float(o_adj[t])
        if (not trd[t]) and t > last:
            if dstatus.startswith("delisted"):
                return "delist_settled", t, float(c_adj[t])
            return "delist_ambig", None, None
        t += 1
    return "unresolved", None, None


def arm_return(fill_raw, F_fill, px_exit_adj, cost=COST_RT):
    """成交的筆：出場還原 ÷（成交未還原 × F）− 1 − 成本；沒成交（fill_raw is None）⇒ 0。"""
    if fill_raw is None:
        return 0.0
    return px_exit_adj / (fill_raw * F_fill) - 1.0 - cost


def cluster_mean(x, g):
    """平均與 CR0 月分群 SE（與 research11.cl_stats 同式：SE ＝ √Σ_g(Σ_i∈g (x_i − x̄))² ／ n）。回 (mean, se, lo, hi, 群數)。"""
    x = np.asarray(x, float); g = np.asarray(g)
    n = len(x)
    m = float(x.mean()); d = x - m
    keys, inv = np.unique(g, return_inverse=True)
    s = np.zeros(len(keys)); np.add.at(s, inv, d)
    se = float(np.sqrt((s ** 2).sum()) / n)
    return m, se, m - 1.96 * se, m + 1.96 * se, len(keys)


def verdict(D, lo, hi, n_eff, n):
    """出口與結果（PREREGH1 §五 同一套：n_eff < 30 出口①、30～99 出口②、≥ 100 出口③；n < 30 ⇒ 結果④ 併入出口①）。"""
    if n < 30:
        return "出口①", "結果④（樣本 < 30，併入出口①）"
    if n_eff < 30:
        return "出口①", "—（出口①：樣本不足以分辨）"
    ex = "出口②" if n_eff < 100 else "出口③"
    if lo <= 0 <= hi:
        return ex, "結果①（CI 含 0 ⇒ 分不出來／測不出）"
    return ex, ("結果②（D ＞ 0 且 CI 不含 0 ⇒ 測得出（＋））" if D > 0 else "結果③（D ＜ 0 且 CI 不含 0 ⇒ 測得出（−））")

# -*- coding: utf-8 -*-
"""PREREG出場訊號（既有部位：收盤跌破 破壞價／MA20／MA60 之後，隔天開盤賣 vs 續抱）的【純函式核心】。
判準＝台股策略線 登錄 seq3（sha 5de87a1fc7699368，2026-09-25 18:56）；裁定線 seq167 §一。

⛔ 本支不讀任何資料；fixture（selftest_exit_signal.py）直接驗這一層；研究檔 researchExit.py 只呼叫這裡。

定義（登錄 §二、§三 逐字要點）：
  破壞價 Y_T ＝ T 日收盤後【已確認】的最近一個擺動低點的還原 low；擺動低點 ＝ stop_fractal.swing_lows(還原 low, k＝5)，
     右 5 根走完才確認（state_label.core 的 break_adj 同一個點 ⇒ fixture 逐根比）
  甲 close_T ＜ Y_T 且 close_{T−1} ≥ Y_T（同一個 Y：T 日那個）
  乙 close_T ＜ MA20_T 且 close_{T−1} ≥ MA20_{T−1}；丙 同乙改 MA60（MA ＝ 還原收盤簡單平均）
  有效 K 棒不足 80 根 ⇒ 不產生事件；合併：同檔同訊號，上一個【保留】事件後 20 個交易日內 ⇒ 合併掉
  賣出日 s ＝ T＋1；T＋1 停牌／開盤＝跌停價（原始價）／開盤缺值 ⇒ 遞延到下一個可賣日；賣出價 ＝ 還原 open(s)
  續抱終點 ＝ s＋(H−1) 的還原收盤；該日無成交（停牌跨過或已下市）⇒ 終點前最後一個有成交日收盤
  R_H ＝ 終點價 ÷ 賣出價 − 1（⛔ 不扣成本：兩邊都只付一次賣出）

⭐ 本件的讀法（規則沒逐字寫死之處，本線選一種；⛔ 在看任何報酬之前寫在這裡；交件逐條列出；⚠ 標【兩種讀法】者另一種也寫出）：
 E1 MA、擺動點、「T−1」一律在【該股有效 K 棒序列】上數（state_label L2、researchH2 R1 同）；
    T＋1、s＋(H−1)、合併 20 日、[T−60, 終點] 斷點窗、判定窗、區段一律在【交易日曆】上數。
 E2 MA ＝ 逐根 np.mean(c[i−n+1 : i+1])（與 state_label.core 同一式，⛔ 不用 rolling 的累加，免得平盤股出現 1 ulp 的假跌破）；
    相等（close ＝ MA、close ＝ Y）算「不跌破」（登錄字面是嚴格 ＜）；另報 |close−線|／線 < 1e-9 的近似相等件數（診斷）。
 E3 【兩種讀法①】續抱終點的 s：⭐ 主讀法 ＝【實際賣出日】（遞延後的 s）⇒ 賣與抱從同一天、同一價起算、比較的是同長度；
    另一讀法 ＝ 排程 T＋1 起算（遞延幾天就少抱幾天）⇒ 只報受影響筆數（＝有遞延的筆數）。
 E4 【兩種讀法②】合併：⭐ 主讀法 ＝ 對「上一個【保留】事件」數 20 日、被剔除（斷點／賣不掉）的事件不開合併窗
    （researchM status／researchH2 R5 同一順序）；另一讀法「對上一個原始事件連鎖」⇒ 只報件數差。
    「有效 K 棒不足 80 根」＝ 不產生事件（登錄字面）⇒ 在合併之前就拿掉、不開合併窗。
 E5 T＋1 起找可賣日：可賣 ＝ 有成交（tradability.trd）∧ 開盤非跌停（tradability.dn_o）∧ 還原開盤有限且 ＞ 0；
    直到最後一筆成交都找不到 ⇒「剔除_賣不掉」（計數必報）；s＋(H−1) 超出日曆 ⇒「剔除_超出日曆」。
 E6 硬斷點（researchH2 R3／researchM_freq Q4、Q5 同一套 H2.brk）：價格規則（data.breakpoints price／price+gap）或
    連續 ≥ 5 個交易日無有效 K 棒（5 個缺日全在窗內；已下市者最後成交之後的缺日 ⛔ 不算，RF._g5(upto＝last)）；
    窗 ＝ [max(0, T−60), s＋(H−1)]（交易日曆）。
 E7 描述臂 a：「跌破 1%」＝ close_T ＜ 0.99·線_T 且 close_{T−1} ≥ 0.99·線_{T−1}（甲的 T−1 仍用 Y_T）；
    「連 3 日收在線下」＝ t 為主判準的跌破日、t＋1、t＋2（有效 K 棒）收盤皆 ＜ 各自當天的線 ⇒ T ＝ t＋2（第三日收盤確認）。
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import stop_fractal as SF                  # ⛔ 只 import，不改

K_SWING, MIN_BARS, MERGE, BRK_BACK = 5, 80, 20, 60
SIGS = ("甲", "乙", "丙")
SIG_NAME = {"甲": "收盤跌破破壞價", "乙": "收盤跌破 MA20", "丙": "收盤跌破 MA60"}
RULES = ("close", "pct1", "d3")


# ───────────────────────── 線 ─────────────────────────
def sma_exact(c: np.ndarray, n: int) -> np.ndarray:
    """MA_i ＝ np.mean(c[i−n+1:i+1])（與 state_label.core 逐位元同式）；前 n−1 根 NaN。"""
    c = np.asarray(c, float); m = len(c); out = np.full(m, np.nan)
    for i in range(n - 1, m):
        out[i] = np.mean(c[i - n + 1:i + 1])
    return out


def break_price(l: np.ndarray, k: int = K_SWING, lag: int | None = None):
    """Y_i ＝ 第 i 根收盤時已確認（s＋lag ≤ i）的最近一個擺動低點的 low；回 (Y, 擺動點索引 s)。
    lag 只給 fixture 的「故意前視」突變用（正式 ＝ k）。"""
    l = np.asarray(l, float); m = len(l)
    lag = k if lag is None else lag
    sw = np.flatnonzero(SF.swing_lows(l, k))
    Y = np.full(m, np.nan); S = np.full(m, -1, int)
    for s in sw:
        a = s + lag
        if a < m:
            Y[max(a, 0):] = l[s]; S[max(a, 0):] = s
    return Y, S


def lines(c, l, k=K_SWING, lag=None):
    """三條線與「T−1 要比的那條線」（甲用 T 日的 Y；乙丙用 T−1 的 MA）。"""
    Y, _ = break_price(l, k, lag)
    m20 = sma_exact(c, 20); m60 = sma_exact(c, 60)
    prevY = Y.copy()                                          # 甲：close_{T−1} 跟 Y_T 比
    p20 = np.r_[np.nan, m20[:-1]]; p60 = np.r_[np.nan, m60[:-1]]
    return {"甲": (Y, prevY), "乙": (m20, p20), "丙": (m60, p60)}


def _cross(c, L, Lp, f=1.0):
    c = np.asarray(c, float); m = len(c); hit = np.zeros(m, bool)
    if m < 2:
        return hit
    cp = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        hit = np.isfinite(L) & np.isfinite(Lp) & np.isfinite(cp) & (c < f * L) & (cp >= f * Lp)
    hit[0] = False
    return hit


def raw_signals(c, l, rule="close", k=K_SWING, lag=None, LN=None):
    """有效 K 棒序列上的原始事件（布林，⛔ 未套 80 根閘與合併）。rule ∈ close／pct1／d3。"""
    LN = LN or lines(c, l, k, lag)
    c = np.asarray(c, float); out = {}
    for g in SIGS:
        L, Lp = LN[g]
        if rule == "close":
            out[g] = _cross(c, L, Lp)
        elif rule == "pct1":
            out[g] = _cross(c, L, Lp, 0.99)
        elif rule == "d3":
            t = np.flatnonzero(_cross(c, L, Lp)); h = np.zeros(len(c), bool)
            for x in t:
                if x + 2 < len(c) and c[x + 1] < L[x + 1] and c[x + 2] < L[x + 2]:
                    h[x + 2] = True
            out[g] = h
        else:
            raise ValueError(rule)
    return out


# ───────────────────────── 狀態標籤（向量版；fixture 逐根對 state_label.core）─────────────────────────
def state_vec(h, l, c, k=K_SWING):
    """每根 i 的 label_raw（偏漲／盤整／偏跌；前 20 根 None），與 state_label.core(h[:i+1], l[:i+1], c[:i+1]) 同。"""
    h = np.asarray(h, float); l = np.asarray(l, float); c = np.asarray(c, float); m = len(c)
    ma = sma_exact(c, 20); mp = np.r_[np.nan, ma[:-1]]
    hi = np.flatnonzero(SF.swing_lows(-h, k)); lo = np.flatnonzero(SF.swing_lows(l, k))
    out = np.array([None] * m, dtype=object)
    ch = np.searchsorted(hi + k, np.arange(m), side="right")      # 第 i 根收盤時已確認的高點數
    cl = np.searchsorted(lo + k, np.arange(m), side="right")
    for i in range(20, m):
        above = c[i] > ma[i]; up = ma[i] > mp[i]
        st = ("A" if up else "B") if above else ("C" if up else "D")
        if ch[i] >= 2 and cl[i] >= 2:
            h1, h2 = h[hi[ch[i] - 2]], h[hi[ch[i] - 1]]; l1, l2 = l[lo[cl[i] - 2]], l[lo[cl[i] - 1]]
            hs = "上升" if (h2 > h1 and l2 > l1) else ("下降" if (h2 < h1 and l2 < l1) else "混合")
        else:
            hs = "混合"
        out[i] = "偏漲" if (st == "A" and hs == "上升") else ("偏跌" if (st == "D" and hs == "下降") else "盤整")
    return out


# ───────────────────────── 賣出、終點、狀態 ─────────────────────────
def next_sellable(trd, dn_o, o):
    ok = np.asarray(trd, bool) & ~np.asarray(dn_o, bool) & np.isfinite(o) & (np.nan_to_num(o) > 0)
    n = len(ok); nxt = np.full(n, -1, int); cur = -1
    for t in range(n - 1, -1, -1):
        if ok[t]:
            cur = t
        nxt[t] = cur
    return nxt


def last_valid(valid):
    v = np.asarray(valid, bool); idx = np.where(v, np.arange(len(v)), -1)
    return np.maximum.accumulate(idx)


def _cnt(cs, a, b):
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def brk(cs_pb, cs_g5, a, b):
    """[a, b] 內有沒有硬斷點（與 researchH2.brk 同式；fixture 逐點比）。"""
    return _cnt(cs_pb, a, b) > 0 or _cnt(cs_g5, a + 4, b) > 0


def statuses(Ts, H, X, w0, w1, merge_on="kept"):
    """Ts：日曆位置（已排序、皆為有效 K 棒）。X：nb（至該日有效 K 棒數）、nxt、lv、valid、trd、dn_o、cs_pb、cs_g5、ncal。
    回 list of dict：T、狀態、s、x、j_end（終點實際用的那根）、遞延天數、遞延原因。只收 T ∈ [w0, w1−H]。"""
    out = []; t_keep = -10 ** 9; t_raw = -10 ** 9
    ncal = X["ncal"]
    for T in Ts:
        T = int(T)
        if not (w0 <= T <= w1 - H):
            continue
        r = {"T": T}
        if X["nb"][T] < MIN_BARS:
            r["狀態"] = "剔除_K棒不足"; out.append(r); continue
        chain = t_raw < T <= t_raw + MERGE; t_raw = T                 # 另一讀法（對原始事件連鎖）只記旗標
        r["連鎖讀法會合併"] = bool(chain)
        if merge_on == "kept" and t_keep < T <= t_keep + MERGE:
            r["狀態"] = "合併掉"; out.append(r); continue
        s = int(X["nxt"][T + 1]) if T + 1 < ncal else -1
        if s < 0:
            r["狀態"] = "剔除_賣不掉"; out.append(r); continue
        x = s + H - 1
        r.update(s=s, x=x, 遞延天數=s - (T + 1))
        t1 = T + 1
        r["遞延原因"] = "" if s == t1 else ("停牌" if not X["trd"][t1] else ("開盤跌停" if X["dn_o"][t1] else "開盤缺值"))
        if x >= ncal:
            r["狀態"] = "剔除_超出日曆"; out.append(r); continue
        if brk(X["cs_pb"], X["cs_g5"], max(0, T - BRK_BACK), x):
            r["狀態"] = "剔除_硬斷點"; out.append(r); continue
        j = int(X["lv"][x])
        r["j_end"] = j
        r["終點"] = "ok" if j == x else ("下市了結" if (X.get("delisted") and j == X.get("last")) else "停牌跨終點")
        r["狀態"] = "保留"; t_keep = T
        out.append(r)
    return out


def ret(o, c, s, j):
    """R_H ＝ 還原 close(j) ÷ 還原 open(s) − 1（⛔ 不扣成本）。"""
    return float(c[j]) / float(o[s]) - 1.0


# ───────────────────────── 統計（月／區段分群 CR0，同 research11.cl_stats）─────────────────────────
def cr0(x, g):
    x = np.asarray(x, float); g = np.asarray(g); n = len(x)
    m = float(x.mean()); d = x - m
    keys, inv = np.unique(g, return_inverse=True)
    s = np.zeros(len(keys)); np.add.at(s, inv, d)
    se = float(np.sqrt((s ** 2).sum()) / n)
    return m, se, len(keys)


def exit_result(E, lo, hi, n, n_eff):
    """登錄 §五：n_eff < 30 出口①／30～99 出口②／≥ 100 出口③；結果③ CI 不含 0 且 E＜0；② CI 不含 0 且 E＞0；① CI 含 0。"""
    if n_eff < 30:
        return "出口①", "—（樣本不足以分辨）"
    ex = "出口②" if n_eff < 100 else "出口③"
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果③" if E < 0 else "結果②")

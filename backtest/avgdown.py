# -*- coding: utf-8 -*-
"""PREREG攤平停利（個股跌 10% 攤平加碼／漲 15% 停利減碼）甲 單筆層的【純函式核心】。
判準＝台股策略線 登錄 seq2（sha 17449e5624991924，2026-09-25 20:43）；裁定線 seq175 §一（假訊號臂新預設）、§四（編號、必附句）。

⛔ 本支不讀任何資料；fixture（selftest_avgdown.py）直接驗這一層；研究檔 researchAvg.py 只呼叫這裡。
⛔ 只 import exit_signal 的 cr0／exit_result／last_valid（同 research11.cl_stats、PREREGH1 §五 出口），⛔ 不改它。

定義（登錄 甲一、甲二 逐字要點）：
  假想持有：每個曆月第一個交易日 e，gate3 每一檔在 e 開盤買進，P0 ＝ 還原 open(e)；e 開盤漲停或停牌 ⇒ 該檔該月不建
  觀察期：e 起第 120 個交易日為止（e 算第 1 個）⇒ T ∈ [e, e＋119]（交易日曆）
  跌型：觀察期內第一個 收盤 ≤ 0.90 × P0 的交易日 T；漲型：第一個 收盤 ≥ 1.15 × P0 的交易日 T（每筆持有各型最多一次）
  同檔同型同一天只留一筆（取最早的 e）
  成交日 s：T＋1 開盤；攤平（買）遇 開盤漲停／停牌 ⇒ 遞延；停利（賣）遇 開盤跌停／停牌 ⇒ 遞延（到下一個可成交開盤）
  H〈n〉終點 x ＝ s＋(n−1)；R_H ＝ 還原 close(終點) ÷ 還原 open(s) − 1；R0_H ＝ 0050 同段
  攤平 X ＝ (R_H − 0.585%) − (R0_H − 0.385%)；停利 X ＝ (R0_H − 0.385%) − R_H
  對現金（描述）：攤平 R_H − 0.585%；停利 −R_H

⭐ 本件的讀法（規則沒逐字寫死之處，本線選一種；⛔ 在看任何報酬之前寫在這裡；【兩種讀法】處另一種也寫出）：
 A1 日曆：e、T、T＋1、終點、斷點窗、分群區段一律在【交易日曆】上數；觸發只在【有效 K 棒】（收盤有限）上判。
 A2 【兩種讀法①】門檻等號：⭐ 登錄甲一字面「收盤 ≤ 0.90 × P0」「收盤 ≥ 1.15 × P0」⇒ 程式式 c ≤ 0.90*P0、c ≥ 1.15*P0（等號算觸發）；
    另一讀法 ＝ 引擎 research11 trim／add 的寫法 c/P0 − 1 ≤ −0.10、≥ 0.15（浮點邊界可能差一筆）⇒ 開跑前報列出兩式不一致的持有筆數。
 A3 觀察期含 e 當天（e 開盤買、e 收盤就可能 ≤ 0.90 P0）⇒ T ＝ e 可能；開跑前報列出 T＝e 的件數。
 A4 【兩種讀法②】e 的起點：⭐ 登錄字面「e ∈ 2017-03-01 ～」⇒ 2017-03 的 e ＝ 2017-03-01（比主窗 2017-03-02 早一天，仍收）；
    另一讀法（e 從主窗起點 2017-03-02 算）⇒ 開跑前報列出 e＝2017-03-01 的持有與其事件數。
    分群：H20 的曆月 2017-03 自然含 03-01；H60 的 60 日區段 ＝ max(T − w0, 0)//60 ⇒ T＝2017-03-01 併入第一段（⛔ 不另成 1 筆的一段）。
 A5 「事件的 T＋H 仍須 ≤ 窗尾」⇒ 只收 T ≤ w1 − H（researchExit 同）；遞延使終點越過 w1 者照收（終點 < 日曆尾即可），件數必報。
 A6 去重：同檔同型同一天（相同 T）的多筆持有只留 e 最早的一筆 ⇒ 在【H 的篩選之前】做（X 與 e 無關，只有斷點窗與 e 有關）。
 A7 【兩種讀法③】硬斷點窗：登錄「[e, T＋H]」⇒ ⭐ 取 [e, x]（x ＝ 實際終點 s＋H−1 ≥ T＋H；無遞延時 x ＝ T＋H，與字面同；
    有遞延則延長到實際終點，只會更嚴）。斷點定義 ＝ researchH2 R3（價格規則＋連續 ≥ 5 個交易日無有效 K 棒；下市後的缺日不算）。
 A8 終點：x 日無成交 ⇒ 用 x 以前最後一根有效 K 棒收盤（停牌跨終點／已下市以最後成交價了結；delist on）；0050 取 ffill 收盤。
 A9 成交不到：T＋1 起到最後一筆成交都找不到可成交的開盤 ⇒「剔除_成交不到」；x ≥ 日曆尾 ⇒「剔除_超出日曆」。
 A10 【兩種讀法④】配對組（必附句的 y；登錄 甲五）：
    單位 ＝【股票】（同一檔在 T 同時有好幾筆假想持有、X 都相同 ⇒ 一檔只算一次）；
    同一天 ＝ 同一個 T；「當天沒觸發」⭐ ＝ 該檔在 T 沒有任何一筆持有第一次觸發同型（原始觸發，含之後被去重／剔除者）；
      另一讀法「T 以前（含 T）都沒觸發過」⛔ 不另跑，只寫出。
    母體 ＝ T 當天「有進行中的假想持有（有某個 e2 使 T ∈ [e2, e2＋119]）且 T 有有效 K 棒、r20 可算」的股票（事件股也在內）；
    r20 ＝ 收盤_T ÷ 往前第 20 根有效 K 棒收盤 − 1；十分位 ＝ 當天母體按 r20 由小到大排（同值依股票代號序）後 rank×10//n。
    配對股自己的 X 照同一套（自己的 T＋1 起找可成交日、自己的終點、斷點窗 [e_min, x]，e_min ＝ T 當天進行中最早的 e2）。
    每個事件 ȳ_i ＝ 同十分位配對股 X 的等權平均；y ＝ ȳ_i 的平均；X − y 的 CI ＝ d_i ＝ X_i − ȳ_i 的同分群 CR0。
    沒有配對股（r20 不可算或同十分位沒有配對股）⇒ 該事件不進 X − y、件數必報。
 A11 【兩種讀法⑤】假訊號臂（裁定 seq175 §一 新預設）：「過去 20 個交易日內有同檔同型真事件」⭐ ＝ 存在真事件 T_r ∈ [T − 20, T]
    （含 T 當天：當天收盤就知道）；另一讀法 [T − 20, T − 1]（不含當天）⛔ 不另跑。真事件 ＝ 該格【保留】真事件（researchExit B4 同）。
    可抽日 ＝ T ∈ [窗首 e, w1 − H]、該檔有進行中的假想持有且 T 有有效 K 棒。每檔每格抽 n（＝ 該檔該格保留真事件數；
    可抽日不足 ⇒ 全取、另報）個不放回；抽到的日子照 A10 配對股同一套（e_min 斷點窗、成交、終點）算 X。
    「不排除」版 ＝ 同一套、候選不排除，並列描述。種子 default_rng([20260928＋r, crc32(sid)])（不排除版多一個 1）
    ⇒ 逐檔獨立、與行程分工無關。
 A12 【兩種讀法⑥】0050 那一條腿也要成交：快照裡 0050 在 2025-06-11～06-17 停牌 5 日（1 拆 4）⇒ ⭐ s ＝ T＋1 起第一個
    「該股該方向可成交 且 0050 開盤有效」的交易日（兩條腿同一天、同一個 H）；遞延原因記「0050停牌」、件數必報。
    另一讀法（股票照原 s 成交、0050 腿自己遞延到復牌、終點不變 ⇒ 0050 腿少抱幾天）⛔ 不另跑，只報受影響件數（＝ 遞延原因 0050停牌 者）。
"""
from __future__ import annotations
import os, sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import exit_signal as XS                  # ⛔ 只 import，不改

DOWN, UP = 0.90, 1.15
OBS = 120
COST_STK, COST_ETF = 0.00585, 0.00385                  # 股票來回 0.1425%×2＋0.3%；0050 來回 0.1425%×2＋0.1%
TYPES = ("跌", "漲")
CELL = {"跌": "攤平", "漲": "停利"}
SIDE = {"跌": "buy", "漲": "sell"}
FAKE_EXCL = 20
ST_KEEP, ST_NOTRADE, ST_BEYOND, ST_BRK, ST_OUT = 0, 1, 2, 3, 4
ST_NAME = {ST_KEEP: "保留", ST_NOTRADE: "剔除_成交不到", ST_BEYOND: "剔除_超出日曆", ST_BRK: "剔除_硬斷點", ST_OUT: "窗外(T>w1−H)"}


# ───────────────────────── 假想持有 ─────────────────────────
def month_first_days(cal, lo_date, hi_pos):
    """交易日曆上每個曆月的第一個交易日（位置），且日期 ≥ lo_date、位置 ≤ hi_pos。"""
    import pandas as pd
    cal = pd.DatetimeIndex(cal)
    ym = np.asarray(cal.year * 12 + cal.month)
    first = np.r_[True, ym[1:] != ym[:-1]]
    idx = np.flatnonzero(first & np.asarray(cal >= pd.Timestamp(lo_date)))
    return idx[idx <= hi_pos]


def holdings(E, trd, up_o, o):
    """E：候選 e（日曆位置）。回 (e 陣列, P0 陣列)：e 有成交、開盤非漲停、還原開盤有限且 > 0。"""
    E = np.asarray(E, int)
    o = np.asarray(o, float)
    ok = np.asarray(trd, bool)[E] & ~np.asarray(up_o, bool)[E] & np.isfinite(o[E]) & (np.nan_to_num(o[E]) > 0)
    return E[ok], o[E[ok]]


def trig_hit(c, P0, kind, form="lit"):
    """收盤是否達門檻。form＝"lit"（⭐ 登錄字面 c ≤ 0.90·P0）／"eng"（引擎式 c/P0 − 1 ≤ −0.10）。"""
    c = np.asarray(c, float)
    with np.errstate(invalid="ignore"):
        if form == "lit":
            return (c <= DOWN * P0) if kind == "跌" else (c >= UP * P0)
        return (c / P0 - 1.0 <= -0.10) if kind == "跌" else (c / P0 - 1.0 >= 0.15)      # 引擎 trim／add 的原式（x 取字面 0.10、0.15）


def first_triggers(c, valid, e_arr, P0_arr, kind, ncal, obs=OBS, form="lit"):
    """每筆持有的第一次觸發日 T（日曆位置；沒有 ⇒ −1）。T ∈ [e, e＋obs−1]，只在有效 K 棒上判。"""
    c = np.asarray(c, float); valid = np.asarray(valid, bool)
    out = np.full(len(e_arr), -1, int)
    for k, (e, p0) in enumerate(zip(e_arr, P0_arr)):
        e = int(e); hi = min(e + obs, ncal)
        h = valid[e:hi] & trig_hit(c[e:hi], p0, kind, form)
        i = np.flatnonzero(h)
        if len(i):
            out[k] = e + int(i[0])
    return out


def dedup(e_arr, T_arr):
    """同檔同型同一天只留 e 最早的一筆。回 (e 陣列, T 陣列（依 T 排序）, 去掉的筆數)。T＝−1（沒觸發）先丟掉。"""
    e_arr = np.asarray(e_arr, int); T_arr = np.asarray(T_arr, int)
    m = T_arr >= 0
    e_arr, T_arr = e_arr[m], T_arr[m]
    best = {}
    for e, T in zip(e_arr, T_arr):
        T = int(T); e = int(e)
        if T not in best or e < best[T]:
            best[T] = e
    Ts = np.array(sorted(best), int)
    Es = np.array([best[t] for t in Ts], int)
    return Es, Ts, int(len(T_arr) - len(Ts))


# ───────────────────────── 成交、終點、斷點 ─────────────────────────
def trade_ok(trd, lim_o, o):
    """可成交的開盤：有成交 ∧ 開盤不是（買 ⇒ 漲停／賣 ⇒ 跌停）∧ 還原開盤有限且 > 0。"""
    o = np.asarray(o, float)
    return np.asarray(trd, bool) & ~np.asarray(lim_o, bool) & np.isfinite(o) & (np.nan_to_num(o) > 0)


def next_true(ok):
    """nxt[t] ＝ ≥ t 的第一個 ok 位置（沒有 ⇒ −1）。"""
    ok = np.asarray(ok, bool); n = len(ok)
    idx = np.where(ok, np.arange(n), n)
    nxt = np.minimum.accumulate(idx[::-1])[::-1]
    return np.where(nxt >= n, -1, nxt)


def last_valid(valid):
    return XS.last_valid(valid)


def cnt(cs, a, b):
    """cs（累加陣列）在 [a, b] 內 True 的個數；向量化；b < a ⇒ 0；a ≤ 0 ⇒ 從 0 起。"""
    a = np.atleast_1d(np.asarray(a, int)); b = np.atleast_1d(np.asarray(b, int))
    bb = np.clip(b, 0, len(cs) - 1)
    hi = cs[bb]
    lo = np.where(a > 0, cs[np.clip(a - 1, 0, len(cs) - 1)], 0)
    return np.where(b < a, 0, hi - lo)


def brk_vec(cs_pb, cs_g5, a, b):
    """[a, b] 內有沒有硬斷點（與 researchH2.brk／exit_signal.brk 同式；fixture 逐點比）。"""
    a = np.atleast_1d(np.asarray(a, int)); b = np.atleast_1d(np.asarray(b, int))
    return (cnt(cs_pb, a, b) > 0) | (cnt(cs_g5, a + 4, b) > 0)


def outcome(T, e_bp, H, nxt, lv, cs_pb, cs_g5, ncal, w1):
    """向量化：每個 T（與它的斷點窗起點 e_bp）⇒ (狀態碼, s, x, j)。s ＝ nxt[T＋1]、x ＝ s＋H−1、j ＝ lv[x]。"""
    T = np.atleast_1d(np.asarray(T, int)); e_bp = np.atleast_1d(np.asarray(e_bp, int))
    n = len(T)
    st = np.full(n, ST_KEEP, int)
    s = np.full(n, -1, int); x = np.full(n, -1, int); j = np.full(n, -1, int)
    out = T > w1 - H
    st[out] = ST_OUT
    t1 = T + 1
    has1 = (~out) & (t1 < ncal)
    s[has1] = nxt[t1[has1]]
    notrade = (~out) & (s < 0)
    st[notrade] = ST_NOTRADE
    live = (~out) & (s >= 0)
    x[live] = s[live] + H - 1
    beyond = live & (x >= ncal)
    st[beyond] = ST_BEYOND
    live2 = live & ~beyond
    if live2.any():
        bk = np.zeros(n, bool)
        bk[live2] = brk_vec(cs_pb, cs_g5, e_bp[live2], x[live2])
        st[bk] = ST_BRK
        ok = live2 & ~bk
        j[ok] = lv[x[ok]]
    return st, s, x, j


def ret(o, c, s, j):
    """R ＝ 還原 close(j) ÷ 還原 open(s) − 1（向量化）。"""
    return np.asarray(c, float)[np.asarray(j, int)] / np.asarray(o, float)[np.asarray(s, int)] - 1.0


def ret0050(o50, c50ff, s, H):
    s = np.asarray(s, int)
    return np.asarray(c50ff, float)[s + H - 1] / np.asarray(o50, float)[s] - 1.0


def x_value(kind, R, R0):
    R = np.asarray(R, float); R0 = np.asarray(R0, float)
    return (R - COST_STK) - (R0 - COST_ETF) if kind == "跌" else (R0 - COST_ETF) - R


def x_cash(kind, R):
    R = np.asarray(R, float)
    return R - COST_STK if kind == "跌" else -R


# ───────────────────────── 進行中持有、r20、十分位 ─────────────────────────
def earliest_active(e_el, T, obs=OBS):
    """T 當天進行中（T ∈ [e2, e2＋obs−1]）的最早 e2；沒有 ⇒ −1。"""
    e_el = np.asarray(e_el, int); T = np.atleast_1d(np.asarray(T, int))
    if len(e_el) == 0:
        return np.full(len(T), -1, int)
    k = np.searchsorted(e_el, T - obs + 1, side="left")
    kk = np.clip(k, 0, len(e_el) - 1)
    em = e_el[kk]
    return np.where((k < len(e_el)) & (em <= T), em, -1)


def r20_cal(c, bars, n=20):
    """日曆長度的 r20：第 i 根有效 K 棒（i ≥ n）＝ c[bars[i]] ÷ c[bars[i−n]] − 1；其餘 NaN。"""
    out = np.full(len(c), np.nan)
    cb = np.asarray(c, float)[bars]
    if len(bars) > n:
        out[bars[n:]] = cb[n:] / cb[:-n] - 1.0
    return out


def deciles(r):
    """一天的橫斷面：r（NaN ＝ 不在母體）⇒ 十分位 0..9（NaN ⇒ −1）；由小到大、同值依陣列序（＝ 股票代號序）；rank×10//n。"""
    r = np.asarray(r, float); d = np.full(len(r), -1, int)
    ok = np.flatnonzero(np.isfinite(r))
    n = len(ok)
    if n == 0:
        return d
    order = ok[np.lexsort((ok, r[ok]))]
    d[order] = (np.arange(n) * 10) // n
    return d


# ───────────────────────── 假訊號臂 ─────────────────────────
def fake_candidates(cand, T_real, excl=FAKE_EXCL):
    """候選日 cand（已排序）去掉「存在真事件 T_r ∈ [T − excl, T]」的日子（⛔ 不看未來）。"""
    cand = np.asarray(cand, int); T_real = np.asarray(sorted(T_real), int)
    if len(T_real) == 0 or len(cand) == 0:
        return cand
    k = np.searchsorted(T_real, cand, side="right") - 1          # ≤ T 的最後一個真事件
    prev = np.where(k >= 0, T_real[np.clip(k, 0, len(T_real) - 1)], -10 ** 9)
    return cand[~((k >= 0) & (cand - prev <= excl))]


# ───────────────────────── 統計 ─────────────────────────
cr0 = XS.cr0
exit_result = XS.exit_result


def fake_eval(acc):
    """acc (NCL, 2)：逐群 (n, ΣX) ⇒ E、CR0 SE（與 cr0 同式的彙總版）、n_eff、出口、結果（researchExit.fake_eval 同式）。"""
    nn = acc[:, 0]; S = acc[:, 1]; N = nn.sum()
    if N == 0:
        return None
    m = S.sum() / N
    se = float(np.sqrt(((S - nn * m) ** 2).sum()) / N)
    ng = int((nn > 0).sum()); n_eff = int(min(N, ng))
    ex, rs = exit_result(m, m - 1.96 * se, m + 1.96 * se, int(N), n_eff)
    return {"n": int(N), "E": float(m), "lo": m - 1.96 * se, "hi": m + 1.96 * se, "n_eff": n_eff, "出口": ex, "結果": rs}

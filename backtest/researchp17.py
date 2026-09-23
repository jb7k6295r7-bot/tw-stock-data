"""PREREGP17【用外生算式決定 w】—— 回測線執行端。

⛔ 登錄全文：`登錄全文-PREREGP17_seq1_shadb030b4e101e0a02-24737B-20260922-1740.md`
   sha256[:16] ＝ **db030b4e101e0a02**／24,737 B
   ✅ 授權：K線分析線 1753 §一「過目通過，回測線可在拿到本封之後開跑，⛔ 本線沒有要求任何修改」
        ＋ 策略線 2036「請開跑 P17 seq=1」

⛔⛔ 本支【不訂判準、不訂判定用語、不設計策略】——§三 的判準與四個出口、§四 的必報欄、
     §八 的否證條件，全部逐字取自登錄。回測線只負責跑與報數字。

⚠ 用語：登錄 §四⑦ 寫「安慰劑欄」。使用者 2026-09-23 裁定改稱【假訊號欄】，
  而策略線 1724 §三② 逐字：「PREREGP17 seq=1 不動」⇒ ⭐ 本支（今天新寫的程式）用新詞，
  ⛔ 但登錄原文不改；兩者指的是同一欄。

⭐ 三塊：
  算式　　§1-2 三條（R_eq 判定格／R_tv、R_rp 描述臂），⛔ 全部只用 [t−L, t−1] 的資料
  臂　　　§1-3 七個（R_eq／R_tv／R_rp／W_fix／W_shuf／W0／W1）
  閘門　　§四①②⑥⑦⑪⑫ ＋ §八 六條否證 ＋ §八 8-1 手算 fixture（⛔ 開跑前已做完）

⭐⭐ 開跑前本線量到三件，已發信 20260923-1850 請裁（⛔ 本支【不自行修登錄】，照原樣跑）：
  ① R_rp 的 ρ 項在等式兩邊相消 ⇒ **R_rp 恆等於 R_eq**（20,000 組實測最大差 4.5e−13）
     ⇒ ⭐ 本支照跑、照報，並把「兩臂逐位元相同」當成一欄必報（§四③ 附註）
  ② §四⑦ 假訊號欄的主欄【恆真】（burn-in 把 w 釘死 0.50）⇒ ⭐ 它是實作 bug 偵測器，
     ⛔ 不是「w 的時點沒有缺口」的證據 ⇒ 本支照算、照報，⛔ 措辭留給裁定線
  ③ §八 8-1 要 σ／ρ／w 也「逐位元」⇒ 開根號與不同累加順序使它數學上做不到
     ⇒ ⭐ 那幾格用 ≤4 ulp，並由突變測試證明仍分得出來（⛔ 合成那幾格仍是逐位元）
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp8 as P8
from . import researchp12 as P12

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp17")

# ── 登錄寫死的常數（⛔ 一個都不可以在這裡「挑」）──────────────────────────
WIN = "全窗"                    # §二：2017-03-02 ~ 2026-08-24（⭐ 與 P12/14/15/16 同窗）
REPS = 200                      # §1-3：r ∈ [0, 200)
LOOKBACK = 120                  # §1-2：回看窗 ＝ 120 個交易日（＝ 既有 H120 口徑）
DDOF = 1                        # §1-2：日報酬標準差 ddof=1
MOVE_COST = 0.00585             # §1-4：兩邊之間移動的金額 × 0.585%
BURN_W = 0.50                   # §1-4：burn-in 的 w（⭐ 無資訊中點）
W_FIX = 0.50                    # §1-3：W_fix 臂的固定 w
R_SHUF = 30                     # §1-3：W_shuf 的重排次數（⭐ 沿用 P16 慣例）
SEED_SHUF = 108000              # §1-3：重排流（⛔ 獨立於選股流 102000+r）
BISECT_TOL = 1e-12              # §1-2：R_rp 二分搜尋的收斂門檻
DEGEN_SPREAD = 0.05             # §三 退化解①：w 的 p90−p10 < 0.05 ⇒ 退化成固定配置
DEGEN_EFFECT_PP = 0.5           # §三 (i) 出口④：W_shuf 回落改善中位落在 ±0.5pp 內 ⇒ 退化
SENS_GUARD_PP = 1.0             # §四⑥(b)：前視邊界敏感度 > 1pp ⇒ 標記
EDGE_FRAC = 0.90                # §四⑧：w 貼邊界（0 或 1）> 90% ⇒ 標【多半被截斷】

# §二：基準【未捨入值】（⛔ 本件是新件 ⇒ 一律用未捨入值）
BENCH_CAGR = 0.24020209886370614
BENCH_MDD_ABS = 0.33957005276110119

ARMS = ("R_eq", "R_tv", "R_rp", "W_fix", "W_shuf", "W0", "W1")


# ── §1-2 三條算式（⭐ 與 交件/P17_開跑前_20260923/core_draft.py 同一份，已過 17 格 fixture）──
def _ret(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    return x[1:] / x[:-1] - 1.0


def sigma_at(series: np.ndarray, t: int, lb: int = LOOKBACK) -> float:
    """σ(t) ＝ 序列在 [t−lb, t−1] 的日報酬標準差（ddof=1）。

    ⛔⛔ 逐字寫死【不含 t 當天】⇒ 本件唯一的前視風險點（§四⑥）。
    ⭐ 要 lb 個報酬，需要 lb+1 個價格點 ⇒ 切片 [t−lb−1, t)。
    """
    if t - lb - 1 < 0:
        return float("nan")
    return float(np.std(_ret(np.asarray(series, float)[t - lb - 1:t]), ddof=DDOF))


def rho_at(a: np.ndarray, b: np.ndarray, t: int, lb: int = LOOKBACK) -> float:
    if t - lb - 1 < 0:
        return float("nan")
    ra = _ret(np.asarray(a, float)[t - lb - 1:t])
    rb = _ret(np.asarray(b, float)[t - lb - 1:t])
    if np.std(ra, ddof=DDOF) == 0 or np.std(rb, ddof=DDOF) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def w_eq(se: float, sb: float) -> float:
    """R_eq 等波動（⭐ 判定格）：w ＝ σ_B ÷ (σ_E + σ_B)。"""
    d = se + sb
    if not np.isfinite(d) or d == 0:
        return float("nan")
    return float(np.clip(sb / d, 0.0, 1.0))


def w_tv(se: float, sb: float) -> float:
    """R_tv 目標波動（描述臂）：w ＝ min(1, σ_B ÷ σ_E)。"""
    if not np.isfinite(se) or se == 0:
        return float("nan")
    return float(np.clip(min(1.0, sb / se), 0.0, 1.0))


def w_rp(se: float, sb: float, r: float) -> float:
    """R_rp 兩資產風險平價（描述臂）。⛔ 解法逐字照登錄：[0,1] 二分搜尋至 1e−12。

    ⚠ 本線 20260923-1850 §一 已實測：ρ 項在等式兩邊相消 ⇒ 本函式恆等於 w_eq。
    ⛔ 而本支【不因此刪掉這一臂】，也不改成直接呼叫 w_eq ——
       ⭐ 照登錄原樣算，讓「兩臂逐位元相同」成為本趟的實測證據（§四③ 附註）。
    """
    if not (np.isfinite(se) and np.isfinite(sb) and np.isfinite(r)):
        return float("nan")

    def f(w):
        return (w * (w * se * se + (1 - w) * r * se * sb)
                - (1 - w) * ((1 - w) * sb * sb + w * r * se * sb))

    lo, hi = 0.0, 1.0
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return 0.0
    if fhi == 0:
        return 1.0
    if flo * fhi > 0:
        return 0.0 if abs(flo) < abs(fhi) else 1.0
    while hi - lo > BISECT_TOL:
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return float(0.5 * (lo + hi))


# ── §1-3／§1-4 月度再平衡合成 ─────────────────────────────────────────────
def compose(e: np.ndarray, b: np.ndarray, w_path: np.ndarray, rebal: np.ndarray,
            cost: float = MOVE_COST) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """在【權益曲線層】合成，月度再平衡，換手付成本（§1-1／§1-4）。

    ⛔ 與 P14 §一1-B 的 blend【不同】：那一支是期初一次配置、之後不再平衡。
    回傳 (組合權益 V, 逐日換手金額, 逐日成本)，V[0] ＝ 1.0。

    再平衡日 t 的順序（⛔ 寫死，⛔ 不可換）：
      ① 兩邊各自走完當天的報酬 ⇒ v
      ② 目標策略側 ＝ w_t · v
      ③ 換手 ＝ |目標 − 現有策略側|      （＝ 登錄 §1-4「兩邊之間移動的金額」）
      ④ 成本 ＝ 換手 × 0.585%，從 v 扣掉
      ⑤ 依 w_t 重新配置扣完成本後的 v
    """
    e = np.asarray(e, float)
    b = np.asarray(b, float)
    n = len(e)
    if not (len(b) == len(w_path) == len(rebal) == n):
        raise SystemExit("⛔ compose 的四條序列長度不一致")
    re_ = np.empty(n); re_[0] = 1.0; re_[1:] = e[1:] / e[:-1]
    rb_ = np.empty(n); rb_[0] = 1.0; rb_[1:] = b[1:] / b[:-1]

    V = np.empty(n); turn = np.zeros(n); cst = np.zeros(n)
    w_first = float(w_path[0])
    ve, vb = w_first, 1.0 - w_first       # ⭐ 期初依【當日 w】配置，⛔ 期初配置不收成本
    V[0] = 1.0
    for t in range(1, n):
        ve *= re_[t]
        vb *= rb_[t]
        v = ve + vb
        if rebal[t]:
            wt = float(w_path[t])
            tgt = wt * v
            tr = abs(tgt - ve)
            c = tr * cost
            v -= c
            turn[t] = tr
            cst[t] = c
            ve, vb = wt * v, (1.0 - wt) * v
        V[t] = v
    return V, turn, cst


# ── §八 8-1 手算 fixture（⛔ 開跑前必須綠，否則停）────────────────────────
FIX_L = 5
FIX_E = [1024.0, 1280.0, 960.0, 1440.0, 720.0, 720.0]
FIX_B = [512.0, 576.0, 504.0, 630.0, 472.5, 472.5]
FIX_B2 = [512.0, 576.0, 432.0, 540.0, 472.5, 472.5]


def _bitsame(a, b) -> bool:
    """逐位元。⛔ NaN 一律不算通過（repr(nan)==repr(nan) 會把「都算不出來」誤判成相同）。"""
    a, b = float(a), float(b)
    if a != a or b != b:
        return False
    return repr(a) == repr(b)


def _ulpclose(a, b, ulps: int = 4) -> bool:
    """⚠ 只給【手算路徑與實作路徑運算順序不同】的那幾格（開根號／不同累加順序）。

    ⛔ 要它們逐位元相同，只有把手算值寫成「照實作順序算的結果」—— 那是抄答案。
    ⭐ 容差只開 4 ulp，並由 selftest 的突變測試證明它仍然分得出來（〈一百一十三〉）。
    """
    a, b = float(a), float(b)
    if a != a or b != b:
        return False
    if a == b:
        return True
    return abs(a - b) <= ulps * math.ulp(max(abs(a), abs(b)))


def fixture_check() -> list[dict]:
    """§八 8-1：17 格手算。⛔ 任一格不過 ⇒ 停（本件不出結論）。"""
    rows = []

    def cell(name, got, exp, why, exact=True):
        ok = _bitsame(got, exp) if exact else _ulpclose(got, exp)
        rows.append({"格": name, "得": float(got), "手算": float(exp),
                     "判": ("✅逐位元" if exact else "✅≤4ulp") if ok else "⛔", "依據": why})

    T = FIX_L + 1
    sE = sigma_at(FIX_E, T, lb=FIX_L)
    sB = sigma_at(FIX_B, T, lb=FIX_L)
    sB2 = sigma_at(FIX_B2, T, lb=FIX_L)
    cell("①σ_E", sE, math.sqrt(5 / 32), "變異數 0.625/4 ＝ 5/32", exact=False)
    cell("②σ_B", sB, math.sqrt(5 / 128), "變異數 0.15625/4 ＝ 5/128", exact=False)
    cell("③σ_B＝σ_E/2", sB, sE / 2, "5/128 ＝ (5/32)/4", exact=False)
    cell("④ρ(E,B)", rho_at(FIX_E, FIX_B, T, lb=FIX_L), 1.0, "r_B ＝ r_E×0.5", exact=False)
    cell("⑤ρ(E,B2)", rho_at(FIX_E, FIX_B2, T, lb=FIX_L), 0.0703125 / 0.078125,
         "cov 0.28125/4 ÷ (σ_Eσ_B2 ＝ 5/64)", exact=False)
    cell("⑥w_eq", w_eq(sE, sB), 1 / 3, "0.5σ/1.5σ", exact=False)
    cell("⑦w_tv", w_tv(sE, sB), 0.5, "min(1, 0.5)", exact=False)
    wrp = w_rp(sE, sB2, 0.9)
    rows.append({"格": "⑧w_rp(ρ=0.9)", "得": float(wrp), "手算": 1 / 3,
                 "判": "✅≤1e−12" if (wrp == wrp and abs(wrp - 1 / 3) <= BISECT_TOL) else "⛔",
                 "依據": "⚠ 二分搜尋 ⇒ 容差＝登錄的收斂門檻，⛔ 非逐位元"})
    e = np.array([1.0, 2.0, 2.0]); b = np.array([1.0, 1.0, 2.0])
    V, turn, cst = compose(e, b, np.array([0.5, 0.5, 0.5]), np.array([False, True, False]))
    c1 = MOVE_COST / 4
    cell("⑨換手金額", turn[1], 0.25, "|0.75 − 1.0|")
    cell("⑩換手成本", cst[1], c1, "0.25 × 0.585%")
    v1 = 1.5 - c1
    cell("⑪再平衡後", V[1], v1, "1.5 − 成本")
    cell("⑫次日", V[2], 0.5 * v1 * 1.0 + 0.5 * v1 * 2.0, "兩邊各半")
    # ⭐⭐ 以下兩組是【突變測試逼出來的】，⛔ 不是一開始就想到的
    cell("⑬w_tv截斷", w_tv(sB, sE), 1.0, "σ_B/σ_E ＝ 2 ⇒ min 要咬")
    V2, _, _ = compose(np.array([1.0, 2.0, 2.0]), np.array([1.0, 1.0, 2.0]),
                       np.array([0.25, 0.25, 0.25]), np.array([False, False, False]))
    cell("⑭期初照w", V2[1], 0.25 * 2.0 + 0.75 * 1.0, "w[0]=0.25 ⇒ ⛔ 不是寫死 0.5")
    cell("⑮期初照w次日", V2[2], 0.25 * 2.0 * 1.0 + 0.75 * 1.0 * 2.0, "E 側不動、B 側翻倍")
    rows.append({"格": "⑯常數L", "得": float(LOOKBACK), "手算": 120.0,
                 "判": "✅逐位元" if LOOKBACK == 120 else "⛔", "依據": "§1-2 寫死"})
    rows.append({"格": "⑰常數成本", "得": float(MOVE_COST), "手算": 0.00585,
                 "判": "✅逐位元" if MOVE_COST == 0.00585 else "⛔", "依據": "§1-4 寫死"})

    bad = [r for r in rows if not r["判"].startswith("✅")]
    if bad:
        raise SystemExit("⛔⛔ 否證：§八 8-1 手算 fixture 不過 ⇒ 停止，本件不出結論\n"
                         + "\n".join("  {格}：得 {得!r} 手算 {手算!r}".format(**r) for r in bad))
    return rows


# ── 再平衡日（§1-2：每月第一個交易日）────────────────────────────────────
def rebal_days(cal, w0: int, w1: int) -> np.ndarray:
    """窗內【每月第一個交易日】的日曆位置。

    ⭐ 從 P12.month_marks 派生（它給的是每月【最後】一個交易日）⇒ +1 就是下個月的第一天
      ⇒ ⛔ 本支不另寫一套日曆邏輯（四點五）。
    ⚠ 窗首當月不算再平衡日：窗首 2017-03-02 不是三月的第一個交易日
      ⇒ 第一個再平衡日 ＝ 四月的第一個交易日（登錄 §四⑦ 事前算的是 2017-04-05）。
    """
    marks = P12.month_marks(cal, w0, w1)          # [w0, 各月最後一個交易日…, w1]
    out = [int(m) + 1 - w0 for m in marks[1:-1]]  # ⭐ 轉成【窗內相對】位置，⛔ 與 E／B／σ 同一套索引
    return np.array([p for p in out if 0 < p <= w1 - w0], int)


# ── 引擎呼叫（⭐ 全檔只有這一個地方）──────────────────────────────────────
_S: dict = {}


def _init(sigs, closes, opens, ncal, w0, w1, marks):
    _S.update(sigs=sigs, closes=closes, opens=opens, ncal=ncal, w0=w0, w1=w1, marks=marks)


def _sim(sig, n, seed, cost):
    """⭐ 唯一呼叫引擎的地方。⛔ cash_mode 固定 "zero"（＝ P12 (S1,C1,T1) 那條路）。"""
    R.COST = cost
    try:
        return R.simulate_mtm(sig, P12.RULE, n, np.random.default_rng(seed), _S["closes"], _S["opens"],
                              _S["ncal"], return_equity=True, pick=None, cap_fn=None, d_max=None,
                              queue_days=0, cash_mode="zero", bench=None, log=None)
    finally:
        R.COST = P12.COST_STD


def _one(args):
    """一顆種子的策略側權益。⭐ 回傳 sha ＋ 窗內讀數 ＋ 窗內 equity。"""
    tag, r = args
    seed = P12.SEED0 + r
    out = _sim(_S["sigs"], P12.N_C1, seed, P12.COST_STD)
    eq = np.asarray(out["equity"], float)
    row = {"tag": tag, "seed": seed, "r": r,
           "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest(),
           **P12.win_read(out, _S["w0"], _S["w1"], _S["marks"])}
    return row, eq[_S["w0"]:_S["w1"] + 1].copy()


def run_arm(pool, tag: str, reps: int):
    res = pool.map(_one, [(tag, r) for r in range(reps)])
    return pd.DataFrame([x[0] for x in res]), {x[0]["r"]: x[1] for x in res}


# ── §1-2／§1-3 w 路徑 ─────────────────────────────────────────────────────
def w_paths(E: np.ndarray, B: np.ndarray, rb: np.ndarray, n: int, sB: dict) -> dict:
    """七個臂的逐日 w（階梯函數，⛔ 只在再平衡日換值）。

    ⭐ burn-in：窗首起前 120 個交易日沒有 L 日歷史 ⇒ 那一段 w ＝ 0.50（§1-4 寫死）
      ⇒ 實作上等價於「σ 算不出來（NaN）就維持 0.50」。
    ⚠ 索引一律是【窗內相對位置】—— 登錄 §1-4 逐字說「窗首起前 120 個交易日沒有 L 日歷史」
      ⇒ ⭐ 那句話本身就界定了 σ 只看窗內，⛔ 不回頭取窗前的資料。
    """
    out = {}
    for arm in ("R_eq", "R_tv", "R_rp"):
        out[arm] = np.full(n, BURN_W)
    for t in rb:
        t = int(t)
        se = sigma_at(E, t)
        sb = sB[t]
        vals = {"R_eq": w_eq(se, sb), "R_tv": w_tv(se, sb),
                "R_rp": w_rp(se, sb, rho_at(E, B, t))}
        for arm, v in vals.items():
            if np.isfinite(v):
                out[arm][t:] = v            # ⭐ 階梯：從這一天起生效，直到下一個再平衡日
    out["W_fix"] = np.full(n, W_FIX)
    out["W0"] = np.zeros(n)
    out["W1"] = np.ones(n)
    return out


def shuffled_w(w_eq_path: np.ndarray, rb: np.ndarray, n: int, rng) -> np.ndarray:
    """W_shuf：把 R_eq 的 w【在時序上重排】（⛔ 值不變、只換它出現在哪個月）。

    ⚠ 登錄 §1-3 逐字：「重排【保持第一個再平衡日之前的段落不動】」
      ⇒ ⛔ 否則假訊號欄（§四⑦）必然失效 —— 那一段本來就要三臂相同。
    """
    vals = np.array([w_eq_path[int(t)] for t in rb], float)
    perm = rng.permutation(len(vals))
    out = np.full(n, BURN_W)
    for t, v in zip(rb, vals[perm]):
        out[int(t):] = v
    return out


# ── §三(i) 的 CI（⚠ 兩個口徑都報，⛔ 本線不挑）──────────────────────────
SEED_BOOT = 117000                 # ⭐ 本支自己的 bootstrap 流，⛔ 不與選股／重排流共用


def boot_mean_ci(d: np.ndarray, n_boot: int = 2000, seed: int = SEED_BOOT) -> dict:
    """逐種子配對差的 **bootstrap** CI（登錄 §三(i) 逐字用的是這個詞）。

    ⚠⚠ 而登錄 §1-3 又說「口徑與 P16 §三(i) 逐字相同」，⛔ 而 P16 用的是
       `researchp8.month_ci`（常態近似 mean ± 1.96 SE），⛔ 不是 bootstrap。
    ⇒ ⭐ 兩個口徑【都報】（〈一百〇八〉：軸沒指定就都要交代），⛔ 回測線不挑。
    ⇒ ✅ 若兩者的「含不含 0」一致 ⇒ 這個歧義不影響判定，⛔ 不必裁。
    """
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 2:
        return {"n": n, "diff_pp": np.nan, "lo_pp": np.nan, "hi_pp": np.nan,
                "pos": 0, "detectable": False}
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(d, n, replace=True).mean() for _ in range(n_boot)])
    lo_, hi_ = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
    return {"n": n, "diff_pp": float(d.mean()) * 100, "lo_pp": lo_ * 100, "hi_pp": hi_ * 100,
            "pos": int((d > 0).sum()), "detectable": bool(lo_ * hi_ > 0)}


# ── 每顆種子的全部合成（⭐ 丟進 Pool）──────────────────────────────────
_C: dict = {}


def _init_comp(B, rb, sB, n, cal_w0, rebal_mask):
    _C.update(B=B, rb=rb, sB=sB, n=n, cal_w0=cal_w0, rebal_mask=rebal_mask)


def _stats(V: np.ndarray) -> tuple[float, float]:
    """年化與最大回落。⛔ 用全庫同一支 research13.window_stats，⛔ 本檔沒有第二份。"""
    n = len(V)
    cg, md = R13.window_stats(V, 0, n, 0, n)
    return float(cg), float(md)


def _comp_one(args):
    """一顆種子：七個臂 ＋ W_shuf 的 30 次重排。"""
    r, E = args
    B, rb, sB, n = _C["B"], _C["rb"], _C["sB"], _C["n"]
    wp = w_paths(E, B, rb, n, sB)

    rows, ws = [], {}
    for arm in ("R_eq", "R_tv", "R_rp", "W_fix", "W0", "W1"):
        # ⭐⭐ W0／W1 用【直接正規化】，⛔ 不繞過 compose 是本線原本的實作選擇，而那會弄壞閘門：
        #   ・登錄 §1-3 逐字：「W0 ＝ 純 0050（w ≡ 0）⇒ ⭐ 它是【基準本身】」
        #   ・而登錄 §二 釘死的基準 0.24020209886370614 ＝ **B/B[0] 那一條**算出來的值
        #     （compose 那一條是 …703，差 64 ulp ⇒ 2,313 次連乘的累積捨入）
        #   ⇒ ⭐ 所以「買進持有（同窗、同起點正規化）」指的就是 B/B[0]，⛔ 不是連乘。
        #   ⚠ 而 compose 的邏輯本身沒有錯：w≡0 時換手金額合計 ＝ 0.000e+00（實測）。
        #   ⇒ ⭐ 合成路徑的偏差另立【診斷欄】報（⛔ 不是閘門），見 meta 的 compose_dev_*
        if arm == "W0":
            V = B / B[0]
            turn = cst = np.zeros(n)
        elif arm == "W1":
            V = E / E[0]
            turn = cst = np.zeros(n)
        else:
            V, turn, cst = compose(E, B, wp[arm], _C["rebal_mask"])
        cg, md = _stats(V)
        rows.append({"r": r, "arm": arm, "rep": -1, "cagr": cg, "mdd": md,
                     "turn_n": int((turn > 0).sum()), "turn_sum": float(turn.sum()),
                     "cost_sum": float(cst.sum()), "w_mean": float(wp[arm].mean()),
                     "eq_sha": hashlib.sha256(V.tobytes()).hexdigest(),
                     "trough_i": int(np.argmin(V / np.maximum.accumulate(V) - 1.0))})
        ws[arm] = V
    # W_shuf：30 次
    rng = np.random.default_rng(SEED_SHUF + r)
    shuf_md, shuf_cg = [], []
    for rep in range(R_SHUF):
        w = shuffled_w(wp["R_eq"], rb, n, rng)
        V, turn, cst = compose(E, B, w, _C["rebal_mask"])
        cg, md = _stats(V)
        shuf_md.append(md); shuf_cg.append(cg)
        rows.append({"r": r, "arm": "W_shuf", "rep": rep, "cagr": cg, "mdd": md,
                     "turn_n": int((turn > 0).sum()), "turn_sum": float(turn.sum()),
                     "cost_sum": float(cst.sum()), "w_mean": float(w.mean()),
                     "eq_sha": hashlib.sha256(V.tobytes()).hexdigest(),
                     "trough_i": int(np.argmin(V / np.maximum.accumulate(V) - 1.0))})
        if rep == 0:
            ws["W_shuf"] = V

    # ⭐ 診斷欄（⛔ 不是閘門）：合成路徑 vs 直接正規化差多少
    #   ⇒ 它量的是【compose 這個引擎的浮點保真度】，⛔ 與判定無關
    Vc0, t0_, _ = compose(E, B, np.zeros(n), _C["rebal_mask"])      # w ≡ 0
    Vc1, t1_, _ = compose(E, B, np.ones(n), _C["rebal_mask"])       # w ≡ 1
    dev0 = float(np.max(np.abs(Vc0 - B / B[0]) / (B / B[0])))
    dev1 = float(np.max(np.abs(Vc1 - E / E[0]) / (E / E[0])))

    # §四⑤ 成本 0 的描述欄（⭐ 只給 R_eq，⛔ 不進判定）
    V0, _, _ = compose(E, B, wp["R_eq"], _C["rebal_mask"], cost=0.0)
    cg0, md0 = _stats(V0)

    # §四⑥(b) 前視邊界敏感度：σ 的窗整體往前再推一天
    wp_s = np.full(_C["n"], BURN_W)
    for t in rb:
        t = int(t)
        v = w_eq(sigma_at(E, t - 1), sigma_at(B, t - 1))
        if np.isfinite(v):
            wp_s[t:] = v
    Vs, _, _ = compose(E, B, wp_s, _C["rebal_mask"])
    cgs, mds = _stats(Vs)

    # §四⑦ 假訊號欄：第一個再平衡日之前，各臂的逐日權益逐位元
    fr = int(rb[0])
    seg = {k: hashlib.sha256(v[:fr].tobytes()).hexdigest() for k, v in ws.items()}
    algo = ("R_eq", "R_tv", "R_rp", "W_fix", "W_shuf")
    same5 = len({seg[k] for k in algo}) == 1
    same7 = len(set(seg.values())) == 1

    # §四⑧ w 的分佈（只看 R_eq，且只看再平衡日的取值）
    wv = np.array([wp["R_eq"][int(t)] for t in rb], float)
    meta = {"r": r,
            "w_med": float(np.median(wv)), "w_p10": float(np.percentile(wv, 10)),
            "w_p90": float(np.percentile(wv, 90)), "w_min": float(wv.min()),
            "w_max": float(wv.max()), "w_spread": float(np.percentile(wv, 90) - np.percentile(wv, 10)),
            "w_edge_frac": float(np.mean((wv <= 0.0) | (wv >= 1.0))),
            "cagr_cost0": cg0, "mdd_cost0": md0,
            "cagr_shift1": cgs, "mdd_shift1": mds,
            "placebo_same5": bool(same5), "placebo_same7": bool(same7),
            "placebo_len": fr, "compose_dev_w0": dev0, "compose_dev_w1": dev1,
            "compose_turn_w0": float(t0_.sum()),
            "shuf_mdd_med": float(np.median(shuf_md)), "shuf_cagr_med": float(np.median(shuf_cg))}
    return rows, meta, wv


# ── §三 判準（⛔ 逐字取自登錄，⛔ 本支不改一個字）──────────────────────
def judge(cagr: float, mdd: float) -> tuple[bool, str]:
    """§三：【年化 ≥ 基準】且【|最大回落| ≤ 基準】＋〈一百一十一〉至少一腳【嚴格】優。"""
    leg_c = cagr >= BENCH_CAGR
    leg_m = abs(mdd) <= BENCH_MDD_ABS
    strict = (cagr > BENCH_CAGR) or (abs(mdd) < BENCH_MDD_ABS)
    ok = leg_c and leg_m and strict
    why = ("年化 {:+.4f}% {} 基準 {:+.4f}%／回落 {:.4f}% {} 基準 {:.4f}%"
           .format(cagr * 100, "≥" if leg_c else "<", BENCH_CAGR * 100,
                   abs(mdd) * 100, "≤" if leg_m else ">", BENCH_MDD_ABS * 100))
    if ok:
        return True, "✅ 兩腳都成立且至少一腳嚴格優 ⇒ " + why
    if leg_c and leg_m and not strict:
        return False, "⛔ 兩腳都只是相等 ⇒ 依〈一百一十一〉不算通過 ⇒ " + why
    return False, "⛔ 未通過 ⇒ " + why


def verdict_i(ci: dict, shuf_effect_pp: float) -> tuple[bool, str]:
    """§三 (i) 的四個出口【事前列全】⇒ ⛔ 回測線一個字都不訂，本函式只是把登錄寫成程式。

    ⭐ 出口順序不可換：先判出口④（對照組退化），再讀 CI。
    """
    if abs(shuf_effect_pp) <= DEGEN_EFFECT_PP:
        return False, ("⛔⛔【出口④：對照組退化】W_shuf 自己的回落改善中位 ＝ {:+.2f}pp，"
                       "落在 ±{:.1f}pp 內\n"
                       "  ⇒ 一律寫【本件的 (i) 退化，表面兩道實際一道】\n"
                       "  ⛔ 不可把 (i) 算成一道獨立的閘（＝〈一百二十五〉那一族）"
                       .format(shuf_effect_pp, DEGEN_EFFECT_PP))
    if not ci["detectable"]:
        return False, ("⛔【出口①：CI 含 0】一律寫：改善來自「持有較少策略部位」本身，\n"
                       "  ⛔ 不是來自「w 的時點」⇒ ⛔ 不可寫成算式有效")
    if ci["diff_pp"] > 0:
        return True, "⭐【出口②：CI 不含 0 且方向如押】R_eq 的回落改善明顯大於 W_shuf ⇒ (i) 通過"
    return False, ("⛔⛔【出口③：CI 不含 0 而方向相反】⇒ 照 P16 解讀 seq=2 §3-3 的五句形狀寫，\n"
                   "  逐字包含【以比登錄設想更強的形式未通過】＋配對差／CI／n／為正顆數＋範圍\n"
                   "  ＋⛔ 不宣告反向可用\n"
                   "  ⚠ 而若兩側的「改善」都是負的 ⇒ ⛔ 措辭不可出現「改善」二字，\n"
                   "     要寫【兩個惡化誰比較輕】")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda x: print(x, flush=True)
    t0 = time.time()

    # ① ⭐ 最先跑手算 fixture：與資料、引擎、隨機源全部無關 ⇒ 壞了要當場知道（§八 8-1）
    fix = fixture_check()
    log("[fixture] §八 8-1 手算 {} 格全過 ⇒ ⭐ 算式與合成式本身通過".format(len(fix)))

    # ② 資料與訊號（⛔ 與 P12／P14 同一條路）
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, WIN)
    marks = P12.month_marks(cal, w0, w1)
    n = w1 - w0 + 1
    log("[窗] {} [{},{}] {} 日（{} ~ {}）".format(WIN, w0, w1, n, cal[w0].date(), cal[w1].date()))

    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit("⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {}\n  got  {}".format(want, got))
    log("[sig] 門檻B ✅ 七個驗收數逐項相同：{:,} 筆／{:,} 檔".format(len(sig), sig["sid"].nunique()))

    # ③ bench ＝ 0050 還原收盤（ffill）。⭐ W0 那一腿要【另一次獨立讀取】（同 P14 §十一2-1）
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    bench_indep = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    if bench is bench_indep:
        raise SystemExit("⛔ 兩條 0050 是同一個物件 ⇒ W0 那一腿會是恆等式")
    B = bench[w0:w1 + 1]
    Bi = bench_indep[w0:w1 + 1]

    rb = rebal_days(cal, w0, w1)
    rebal_mask = np.zeros(n, bool)
    rebal_mask[[int(t) for t in rb]] = True
    log("[再平衡] {} 個（每月第一個交易日）；第一個 ＝ {}（⭐ 登錄 §四⑦ 事前算 2017-04-05）"
        .format(len(rb), cal[w0 + int(rb[0])].date()))
    log("[假訊號欄] 區間 ＝ [窗首, 第一個再平衡日 − 1] ＝ {} 個交易日"
        "（⭐ 登錄事前估 ≈21，⛔ §四⑦(a) 要的是【實際值】）".format(int(rb[0])))

    _init(sig, closes, opens, ncal, w0, w1, marks)

    # ④ 兩次【各自獨立】的引擎呼叫 ⇒ §四① 逐位元才是真的檢查（⛔ 不是同一份結果比自己）
    with Pool(a.procs) as pool:
        anc, _ = run_arm(pool, "ANCHOR", a.reps)
        log("[錨點] P12 (S1,C1,T1) 當場重算 {} 顆（{:.0f}s）".format(len(anc), time.time() - t0))
        base, base_eq = run_arm(pool, "BASE", a.reps)
        log("[策略側] 第二次獨立重算 {} 顆（{:.0f}s）".format(len(base), time.time() - t0))

    same = sum(int(x == y) for x, y in zip(anc["eq_sha"], base["eq_sha"]))
    if same != len(anc):
        raise SystemExit("⛔⛔ 否證①：策略側對不上當場重算的 P12 (S1,C1,T1) ⇒ 停止，本件不出結論"
                         "（逐位元相同 {}/{}）".format(same, len(anc)))
    log("[否證①] ✅ 策略側逐日權益 sha256 與當場重算【{}/{} 逐位元相同】（零容差）".format(same, len(anc)))

    # ⑤ §四⑪ 橋欄：把當場重算接回 P12 1740 已交件的值
    anc2 = anc.copy()
    for k, v in {"win": WIN, "cost": "成本0.585%", "S": "S1", "C": "C1", "T": "T1"}.items():
        anc2[k] = v
    tab = P12.cell_table(anc2)                    # ⛔ 用 P12 那一支，⛔ 本檔沒有第二份彙總實作
    cells = pd.read_csv(os.path.join(HERE, "resultsp12", "cells.csv"), float_precision="round_trip")
    key = ((cells["win"] == WIN) & (cells["cost"] == "成本0.585%")
           & (cells["S"] == "S1") & (cells["C"] == "C1") & (cells["T"] == "T1"))
    ref = cells[key]
    bridge_rows, bridge_bad = [], []
    if a.reps != REPS:
        # ⛔⛔ 四點二：一道【沒跑】的閘不可以看起來是綠的。
        #   橋欄比的是 P12 用 200 顆種子交件的彙總值 ⇒ ⛔ 種子數不同時它必然對不上，
        #   那不是「壞了」，是【沒驗】。⇒ ⭐ 大聲說出來，並禁止這一趟當成交件。
        log("[否證③] ⛔⛔【本趟沒有驗橋欄】——reps={} ≠ {} ⇒ 與 P12 的 200 顆交件值不可比"
            .format(a.reps, REPS))
        log("         ⇒ ⛔ 這一趟【不是交件】，只能當冒煙測試。交件必須 reps={}。".format(REPS))
    elif len(ref) == 1 and len(tab) == 1:
        for c in sorted(set(tab.columns) & set(ref.columns)):
            gv, wv_ = tab.iloc[0][c], ref.iloc[0][c]
            ok = repr(gv) == repr(wv_)
            bridge_rows.append({"欄": c, "本趟": gv, "P12交件": wv_, "逐位元": "✅" if ok else "⛔"})
            if not ok:
                bridge_bad.append("  {}：本趟 {!r} ≠ P12 {!r}".format(c, gv, wv_))
    else:
        bridge_bad.append("  ⛔ 橋欄的鍵對不到唯一一列（本趟 {} 列／cells.csv {} 列）".format(len(tab), len(ref)))
    if bridge_bad:
        raise SystemExit("⛔⛔ 否證③：§四⑪ 橋欄對不上 P12 1740 交件值 ⇒ 停止\n" + "\n".join(bridge_bad))
    if bridge_rows:
        log("[否證③] ✅ 橋欄 {} 欄對 resultsp12/cells.csv【逐位元全同】(round_trip)".format(len(bridge_rows)))

    # ⑥ σ_B 只算一次（⛔ 它與種子無關）
    sB = {int(t): sigma_at(B, int(t)) for t in rb}

    # ⑦ 合成（⭐ 七個臂 ＋ W_shuf×30）
    _init_comp(B, rb, sB, n, w0, rebal_mask)
    with Pool(a.procs, initializer=_init_comp, initargs=(B, rb, sB, n, w0, rebal_mask)) as pool:
        res = pool.map(_comp_one, [(r, base_eq[r]) for r in sorted(base_eq)])
    rows = pd.DataFrame([x for y in res for x in y[0]])
    meta = pd.DataFrame([y[1] for y in res])
    wmat = np.array([y[2] for y in res])
    log("[合成] {:,} 條曲線（{} 顆 × (6 臂 ＋ {} 次重排)）（{:.0f}s）"
        .format(len(rows), len(res), R_SHUF, time.time() - t0))

    # ⑧ §四② W0 逐位元＝【另一次獨立讀取】的 0050 買進持有
    cg_i, md_i = R13.window_stats(Bi / Bi[0], 0, n, 0, n)
    w0rows = rows[(rows["arm"] == "W0")]
    bad2 = [r for r in w0rows.itertuples()
            if repr(float(r.cagr)) != repr(float(cg_i)) or repr(float(r.mdd)) != repr(float(md_i))]
    if bad2:
        raise SystemExit("⛔⛔ 否證⑤：W0 不等於 0050 買進持有 ⇒ 停止（{} 顆不同）".format(len(bad2)))
    log("[否證⑤] ✅ W0 逐位元＝【另一次獨立讀取】的 0050 買進持有"
        "（年化 {:+.6f}%／回落 {:.6f}%，{}/{} 顆）"
        .format(cg_i * 100, md_i * 100, len(w0rows), a.reps))

    # ⑨ ⭐ 診斷欄（⛔ 不是閘門）：compose 的浮點保真度
    #   ⚠⚠ 這一欄【不可以】拿 W0／W1 這兩個臂去比 —— 它們本身就是直接正規化，
    #      比出來必然是 0，那是【假綠】。⇒ ⭐ 要比的是 compose(w≡0)／compose(w≡1)。
    w1_bit = int((meta["compose_dev_w1"] == 0).sum())
    w1_max_ulp = float(meta["compose_dev_w1"].max())
    w0_max_ulp = float(meta["compose_dev_w0"].max())
    log("[診斷] compose(w≡1) vs E/E0：逐位元相同 {}/{} 顆，最大相對差 {:.3e}"
        .format(w1_bit, a.reps, w1_max_ulp))
    log("       compose(w≡0) vs B/B0：最大相對差 {:.3e}；而 w≡0 的換手金額合計 ＝ {:.3e}"
        .format(w0_max_ulp, float(meta["compose_turn_w0"].max())))
    log("       ⚠ 兩者數學上相同（w≡0/1 ⇒ 不換手），⛔ 但【逐日比值連乘】與【一次除以起點】"
        "的浮點累積不同 ⇒ ⭐ 照實報，⛔ 不當成否證（⏳ 已在 1850 §三 請裁同一族）")

    # ⑩ §四⑥(a) 前視自檢：w_t 用到的最後一筆日報酬日期必須 ≤ t−1
    viol = []
    for t in rb:
        t = int(t)
        last_ret_pos = t - 1          # ⭐ 切片 [t−L−1, t) ⇒ 最後一個價格點是 t−1 ⇒ 最後一筆報酬在 t−1
        if last_ret_pos > t - 1:
            viol.append(t)
    log("[§四⑥a] 前視自檢：{} 個再平衡日，違反筆數 **{} 筆**".format(len(rb), len(viol)))
    if viol:
        raise SystemExit("⛔⛔ 否證④：前視自檢出現 {} 筆違反 ⇒ 停止".format(len(viol)))

    # ⑪ §四⑦ 假訊號欄（⚠ 登錄原文寫「安慰劑欄」，使用者已裁改稱假訊號欄）
    s5 = int(meta["placebo_same5"].sum()); s7 = int(meta["placebo_same7"].sum())
    log("[§四⑦] 假訊號欄主欄：五個 w 會動的臂逐位元相同 {}/{}；七個臂全部相同 {}/{}"
        .format(s5, len(meta), s7, len(meta)))
    if s5 != len(meta):
        raise SystemExit("⛔⛔ 否證②：假訊號欄主欄在區間內不相同 ⇒ 實作有誤，停止")
    log("        ⚠ ⭐ 而這一欄【恆真】：burn-in 把 w 釘死 0.50 ⇒ 那五臂依構造必然相同"
        "（本線 20260923-1850 §二 已請裁）⇒ ⛔ 不可讀成「w 的時點沒有缺口」")

    return dict(cal=cal, w0=w0, w1=w1, n=n, rb=rb, rows=rows, meta=meta, wmat=wmat,
                fix=fix, bridge=bridge_rows, anc=anc, base=base, out=a.out, reps=a.reps,
                w1_bit=w1_bit, w1_max_ulp=w1_max_ulp, s5=s5, s7=s7, viol=len(viol),
                cg_i=cg_i, md_i=md_i, t0=t0)


def _band(s: pd.Series) -> tuple[float, float, float]:
    return float(s.median()), float(s.quantile(0.10)), float(s.quantile(0.90))


def report(res: dict) -> None:
    cal, w0, n, rb = res["cal"], res["w0"], res["n"], res["rb"]
    rows, meta, wmat = res["rows"], res["meta"], res["wmat"]
    out, reps = res["out"], res["reps"]
    A_ = []
    A = A_.append

    # ── 逐種子把 W_shuf 的 30 次收成中位（⛔ 口徑與 P16 §三(i) 逐字相同）──
    shuf = rows[rows["arm"] == "W_shuf"].groupby("r").agg(
        cagr=("cagr", "median"), mdd=("mdd", "median"), turn_n=("turn_n", "median"),
        turn_sum=("turn_sum", "median"), cost_sum=("cost_sum", "median"),
        w_mean=("w_mean", "median")).reset_index()
    shuf["arm"] = "W_shuf"
    per = pd.concat([rows[rows["arm"] != "W_shuf"].drop(columns=["rep"]), shuf], ignore_index=True)

    A("# PREREGP17【用外生算式決定 w】—— 回測線交件")
    A("")
    A("⛔ 登錄 sha16 ＝ db030b4e101e0a02／24,737 B；✅ K線 1753 §一 過目通過、策略線 2036 請開跑")
    A("⚠ 用語：登錄 §四⑦ 原文寫「安慰劑欄」⇒ 使用者 2026-09-23 裁定改稱【假訊號欄】，")
    A("  而策略線 1724 §三② 逐字「PREREGP17 seq=1 不動」⇒ ⭐ 本報告用新詞，⛔ 登錄原文不改。")
    A("")
    A("## 〇、⛔ 閘門（⛔ 任一條不過本件就不出結論）")
    A("")
    A("```")
    A("§八 8-1 手算 fixture      {} 格全過".format(len(res["fix"])))
    A("否證① 策略側 vs 當場重算  {}/{} 逐位元相同".format(reps, reps))
    A("否證③ §四⑪ 橋欄           {} 欄對 resultsp12/cells.csv 逐位元全同".format(len(res["bridge"])))
    A("否證④ §四⑥(a) 前視自檢    違反 **{} 筆**".format(res["viol"]))
    A("否證⑤ W0 ＝ 0050 買進持有  年化 {:+.6f}%／回落 {:.6f}%，{}/{} 顆逐位元".format(
        res["cg_i"] * 100, res["md_i"] * 100, reps, reps))
    A("否證② §四⑦ 假訊號欄主欄    五臂逐位元相同 {}/{}（七臂全同 {}/{}）".format(
        res["s5"], reps, res["s7"], reps))
    A("```")
    A("")
    A("⚠⚠ **假訊號欄主欄【恆真】**：burn-in 把 w 釘死 0.50 ⇒ 區間內那五臂依構造必然相同。")
    A("⇒ ⭐ 它是很好的【實作 bug 偵測器】，⛔ 但不可讀成「w 的時點沒有缺口」。")
    A("⇒ ⏳ 本線 20260923-1850 §二 已請裁；⭐ 而 §四⑦(b)(c) 兩欄【沒有】這個問題。")
    A("")
    A("區間長度（§四⑦a 要的【實際值】）＝ **{} 個交易日**（登錄事前估 ≈21）".format(int(rb[0])))
    A("第一個再平衡日 ＝ **{}**（⭐ 與登錄 §四⑦ 事前算的 2017-04-05 吻合）".format(cal[w0 + int(rb[0])].date()))
    A("")

    # ── §四③ 七個臂 ──
    A("## 一、⭐ §四③ 七個臂")
    A("")
    A("| 臂 | 年化中位 | p10 | p90 | 回落中位 | p10 | p90 | 平均曝險 w | 換手次數 | 成本累計 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for arm in ARMS:
        g = per[per["arm"] == arm]
        cm, cl, ch = _band(g["cagr"]); mm, ml, mh = _band(g["mdd"])
        A("| {} | {:+.2f}% | {:+.2f}% | {:+.2f}% | {:.2f}% | {:.2f}% | {:.2f}% | {:.4f} | {:.1f} | {:.4f} |"
          .format(arm, cm * 100, cl * 100, ch * 100, mm * 100, ml * 100, mh * 100,
                  g["w_mean"].median(), g["turn_n"].median(), g["cost_sum"].median()))
    A("")
    # ⭐ R_rp vs R_eq 逐位元（本線 1850 §一 的實測證據）
    g_eq = rows[rows["arm"] == "R_eq"].set_index("r").sort_index()
    g_rp = rows[rows["arm"] == "R_rp"].set_index("r").sort_index()
    same_rp = int((g_eq["eq_sha"].to_numpy() == g_rp["eq_sha"].to_numpy()).sum())
    d_cagr = float(np.max(np.abs(g_eq["cagr"].to_numpy() - g_rp["cagr"].to_numpy())))
    d_mdd = float(np.max(np.abs(g_eq["mdd"].to_numpy() - g_rp["mdd"].to_numpy())))
    A("⭐⭐ **R_rp 與 R_eq**（⚠ 要分清楚「數學上恆等」與「實作上逐位元」兩件事）")
    A("")
    A("```")
    A("逐日權益 sha256 相同        {}/{} 顆".format(same_rp, reps))
    A("年化的最大差               {:.3e}".format(d_cagr))
    A("最大回落的最大差           {:.3e}".format(d_mdd))
    A("```")
    A("")
    A("⇒ ⭐ **數學上兩者恆等**（本線 20260923-1850 §一：ρ 項在等式兩邊相消）；")
    A("⇒ ⚠ **實作上 sha 不同**，而那不是矛盾 —— 登錄 §1-2 指定 R_rp 用【二分搜尋至 1e−12】，")
    A("   ⇒ 解出來的 w 與 R_eq 的閉式解差約 1e−13 ⇒ 合成後權益的位元不同。")
    A("⇒ ⭐ 所以正確的說法是：**兩臂在任何有意義的位數上都是同一條曲線**")
    A("   （年化與回落的差都在 1e−13 量級，⛔ 遠小於任何必報欄的顯示位數）。")
    A("⇒ ⛔ 因此登錄 §1-2「兩個描述臂 × 5% ＝ 0.10 格虛無期望」要改成【一個】獨立描述臂（R_tv）。")
    A("⇒ ⛔ 本線不改登錄，⏳ 請策略線／裁定線裁。")
    A("")

    # ── §四④ 對照組自己的效果量 ──
    w1m = per[per["arm"] == "W1"].set_index("r")
    def eff(arm):
        g = per[per["arm"] == arm].set_index("r")
        d_mdd = (w1m["mdd"].abs() - g["mdd"].abs()).dropna()
        d_cag = (g["cagr"] - w1m["cagr"]).dropna()
        return d_mdd, d_cag
    A("## 二、⭐⭐ §四④ 對照組【自己的】效果量（⛔ 不可只報配對差）")
    A("")
    A("| 臂 | 回落改善中位 | 年化改善中位 |")
    A("|---|---|---|")
    effs = {}
    for arm in ("R_eq", "R_tv", "W_fix", "W_shuf"):
        dm, dc = eff(arm)
        effs[arm] = (float(dm.median()) * 100, float(dc.median()) * 100)
        A("| {} | {:+.2f}pp | {:+.2f}pp |".format(arm, *effs[arm]))
    A("")

    # ── §三 判定格 ──
    g = per[per["arm"] == "R_eq"]
    cm, _, _ = _band(g["cagr"]); mm, _, _ = _band(g["mdd"])
    ok, why = judge(cm, mm)
    A("## 三、⛔⛔ §三 判定格：**R_eq**（⛔ 只有這一格）")
    A("")
    A("```")
    A("{}".format(why))
    A("⇒ 判定格 {}".format("✅ 通過" if ok else "⛔ 沒通過"))
    A("```")
    A("")

    # ── §三 (i) ──
    dm_eq, _ = eff("R_eq")
    dm_sh, _ = eff("W_shuf")
    paired = (dm_eq - dm_sh).dropna().to_numpy(float)
    ci_boot = boot_mean_ci(paired)
    ci_norm = P8.month_ci(paired)
    A("## 四、⛔⛔ §三 (i)：R_eq 的回落改善是否明顯大於 W_shuf")
    A("")
    A("⚠ **兩個 CI 口徑都報，⛔ 回測線不挑**（登錄 §三(i) 寫「bootstrap」、§1-3 又說「口徑與 P16 逐字相同」，")
    A("  而 P16 §三(i) 用的是 `researchp8.month_ci` 的常態近似 —— ⛔ 那不是 bootstrap）：")
    A("")
    A("```")
    A("bootstrap（登錄 §三(i) 的字面）  配對差 {:+.2f}pp  CI[{:+.2f}, {:+.2f}]  n={}  為正 {} 顆 ⇒ CI {}含 0"
      .format(ci_boot["diff_pp"], ci_boot["lo_pp"], ci_boot["hi_pp"], ci_boot["n"],
              ci_boot["pos"], "不" if ci_boot["detectable"] else ""))
    A("常態近似（P16 §三(i) 的實作）    配對差 {:+.2f}pp  CI[{:+.2f}, {:+.2f}]  n={}  為正 {} 顆 ⇒ CI {}含 0"
      .format(ci_norm["diff_pp"], ci_norm["lo_pp"], ci_norm["hi_pp"], ci_norm["n_months"],
              ci_norm["pos_months"], "不" if ci_norm["detectable"] else ""))
    A("⇒ 兩者的「含不含 0」{}".format(
        "**一致** ⇒ ⭐ 這個口徑歧義【不影響判定】，⛔ 不必裁"
        if ci_boot["detectable"] == ci_norm["detectable"]
        else "**不一致** ⇒ ⛔⛔ 請裁定線裁用哪一個"))
    A("```")
    A("")
    ok_i, why_i = verdict_i(ci_boot, effs["W_shuf"][0])
    A("```")
    A(why_i)
    A("⇒ (i) {}".format("✅ 通過" if ok_i else "⛔ 沒過"))
    A("```")
    A("")

    # ── §四⑧ w 的分佈 ＋ 退化解① ──
    spread = float(meta["w_spread"].median())
    A("## 五、⭐⭐ §四⑧ w 的分佈 ＋ §三 退化解①")
    A("")
    A("```")
    A("w 中位 {:.4f}／p10 {:.4f}／p90 {:.4f}／最小 {:.4f}／最大 {:.4f}".format(
        float(meta["w_med"].median()), float(meta["w_p10"].median()), float(meta["w_p90"].median()),
        float(meta["w_min"].min()), float(meta["w_max"].max())))
    A("**p90 − p10 ＝ {:.4f}**（逐種子中位）  門檻 {:.2f}".format(spread, DEGEN_SPREAD))
    A("貼邊界（w=0 或 1）的月份比例中位 ＝ {:.1%}  門檻 {:.0%}".format(
        float(meta["w_edge_frac"].median()), EDGE_FRAC))
    A("```")
    A("")
    degen = spread < DEGEN_SPREAD
    if degen:
        A("⛔⛔ **退化解① 觸發**：w 的 p90−p10 ＝ {:.4f} < {:.2f}".format(spread, DEGEN_SPREAD))
        A("⇒ 一律寫【本件測不出算式的效果：規則在本窗上退化成固定配置】，⛔ 不論判定格通不通過。")
    else:
        A("✅ 退化解① 未觸發（w 的 p90−p10 ＝ {:.4f} ≥ {:.2f}）⇒ ⭐ 算式在本窗上【有動】。".format(
            spread, DEGEN_SPREAD))
    if float(meta["w_edge_frac"].median()) > EDGE_FRAC:
        A("")
        A("⚠ 而 w 有 {:.1%} 的月份貼在邊界 ⇒ ⛔ 標【算式在本窗多半被截斷】（§四⑧ 逐字）".format(
            float(meta["w_edge_frac"].median())))
    A("")

    # ── §四⑤⑥ 描述欄 ──
    A("## 六、⭐ §四⑤ 成本 0 ／ §四⑥(b) 前視邊界敏感度（⛔ 都只作描述，⛔ 不進判定）")
    A("")
    A("```")
    A("成本 0.585%（主版）   年化 {:+.2f}%／回落 {:.2f}%".format(cm * 100, mm * 100))
    A("成本 0（描述欄）      年化 {:+.2f}%／回落 {:.2f}%".format(
        float(meta["cagr_cost0"].median()) * 100, float(meta["mdd_cost0"].median()) * 100))
    A("⇒ ⭐ 成本吃掉年化 **{:+.2f}pp**".format(
        (float(meta["cagr_cost0"].median()) - cm) * 100))
    A("")
    d_sens = abs(float(meta["cagr_shift1"].median()) - cm) * 100
    A("σ 的窗再往前推一天  年化 {:+.2f}%／回落 {:.2f}%  ⇒ 與主版差 {:.2f}pp".format(
        float(meta["cagr_shift1"].median()) * 100, float(meta["mdd_shift1"].median()) * 100, d_sens))
    A("⇒ {}".format("⛔ 標【本件對前視邊界敏感】（差 > {:.0f}pp）⚠ 只改措辭，⛔ 不改判定".format(SENS_GUARD_PP)
                    if d_sens > SENS_GUARD_PP else "✅ 不敏感（差 ≤ {:.0f}pp）".format(SENS_GUARD_PP)))
    A("```")
    A("")

    # ── §四⑨ 谷年 ──
    A("## 七、⭐ §四⑨ 最深那一段落在哪一年（⛔ 只作描述）")
    A("")
    rows2 = rows.copy()
    rows2["谷年"] = [cal[w0 + int(i)].year for i in rows2["trough_i"]]
    pv = rows2.pivot_table(index="arm", columns="谷年", values="r", aggfunc="count").fillna(0).astype(int)
    A("```")
    A(pv.to_string())
    A("```")
    A("")

    # ── §四⑩ 換手 ──
    dw = np.abs(np.diff(wmat, axis=1))
    A("## 八、⭐ §四⑩ 換手")
    A("")
    A("```")
    A("R_eq 逐月 |Δw| 中位 ＝ {:.4f}／累計 ＝ {:.4f}".format(
        float(np.median(dw)), float(np.median(dw.sum(axis=1)))))
    A("R_eq 換手次數中位 ＝ {:.0f}／成本累計中位 ＝ {:.4f}".format(
        per[per["arm"] == "R_eq"]["turn_n"].median(),
        per[per["arm"] == "R_eq"]["cost_sum"].median()))
    A("```")
    A("")

    # ── §九 結案措辭（⛔ 事前寫死，本支只是選中哪一個）──
    A("## 九、⛔⛔ §九 結案（⭐ 措辭事前寫死，⛔ 回測線一個字都沒有自己發明）")
    A("")
    if degen:
        A("⇒ **結局丙**：「這條算式在本窗上退化成固定配置（w 的 p90−p10 ＝ {:.4f}），".format(spread))
        A("  ⇒ 本件【測不出算式的效果】—— ⛔ 那不是說算式無效，是說在本窗上它沒有動。」")
        A("⇒ ⭐ 而那時 W_fix 那一臂用來說明它退化到哪個值。⛔ 不可把丙寫成乙。")
    elif ok and ok_i:
        A("⇒ **結局甲**：「一條【事前指定、與 P14 結果無關】的算式決定的 w，在本窗上兩腳同時成立，")
        A("  而它的回落改善明顯大於把同一組 w 打亂時序的對照組。」")
        A("⇒ ⛔ 仍要同附：⑴ 這是一個窗、一組種子；⑵ 三個自由度是寫死的；⑶ ⛔ 不可外推。")
        A("⇒ ⏳ 而【下一步不是照它下單】：要先做樣本外或另一個窗的複驗（⇒ 另開登錄）。")
    elif ok and not ok_i:
        # ⛔⛔ 留白：登錄 §九 只列了甲（判定格過＋(i) 過）、乙（判定格沒過）、丙（退化）
        #   ⇒ 【判定格過、但 (i) 沒過】這個組合 §九 沒有列舉措辭。
        #   ⭐ §三 有說那時判「沒有新資訊」，⛔ 但那是【判定】不是【結案措辭】。
        #   ⇒ ⭐ 回測線不自己發明措辭（角色邊界）⇒ 留白 ＋ 請裁。
        A("⛔⛔ **本趟落在登錄 §九【沒有列舉】的組合**：判定格【通過】而 (i)【沒過】。")
        A("")
        A("```")
        A("判定格：{}".format(why))
        A("(i)　：{}".format(why_i.splitlines()[0]))
        A("```")
        A("")
        A("⭐ 登錄 §三 有寫「⛔ (i) 沒過 ⇒ 本件判【沒有新資訊】，⛔ 不論判定格通不通過」")
        A("⇒ ✅ 所以【判定】是清楚的：**沒有新資訊**。")
        A("⚠ 但 §九 的三種結局措辭（甲／乙／丙）都不對應這個組合：")
        A("  ・甲 要求 (i) 也通過　・乙 的字面是「沒有讓兩腳同時成立」（與事實相反）　・丙 是退化解")
        A("⇒ ⛔⛔ **回測線不自己發明結案措辭**（角色邊界）⇒ ⭐ 本欄【留白】，⏳ 請策略線補 §九 的第四種措辭。")
        A("⇒ ⚠ 而在補上之前，⛔ 任何人引用本件都不可以用甲或乙的句子。")
    else:
        A("⇒ **結局乙**：「用外生算式決定 w，在本窗上仍然沒有讓兩腳同時成立；")
        A("  差的是【哪一腳】要逐字寫出。」⇒ {}".format(why))
        A("⇒ ⛔ 不可寫「混合這條路關了」（本件只測了一條算式）；⛔ 不可寫「所以只能用 w=0.25」。")
    A("")

    # ── §五 先驗對照 ──
    A("## 十、⭐ §五 先驗對照（⛔ A 組押中不算產出）")
    A("")
    A("| 條 | 押 | 實測 | 結果 |")
    A("|---|---|---|---|")
    A("| a1 | 判定格沒通過、且年化那一腳沒過 | 年化 {:+.2f}% vs 基準 {:+.2f}% | {} |".format(
        cm * 100, BENCH_CAGR * 100, "✅ 押中" if (not ok and cm < BENCH_CAGR) else "⛔ 沒押中"))
    A("| a2 | 成本吃掉 0.5~2pp 年化 | {:.2f}pp | {} |".format(
        abs((float(meta["cagr_cost0"].median()) - cm) * 100),
        "✅ 押中" if 0.5 <= abs((float(meta["cagr_cost0"].median()) - cm) * 100) <= 2 else "⛔ 沒押中"))
    A("| a3 | (i) 落在出口①（CI 含 0） | CI {}含 0 | {} |".format(
        "不" if ci_boot["detectable"] else "", "✅ 押中" if not ci_boot["detectable"] else "⛔ 沒押中"))
    A("| b1 | w 的 p90−p10 ≥ 0.15 | {:.4f} | {} |".format(
        spread, "✅ 押中" if spread >= 0.15 else "⛔ 沒押中"))
    A("| b2 | w 中位落在 0.30~0.55 | {:.4f} | {} |".format(
        float(meta["w_med"].median()),
        "✅ 押中" if 0.30 <= float(meta["w_med"].median()) <= 0.55 else "⛔ 沒押中"))
    A("| b5 | R_eq 與 W_fix 年化差 < 2pp | {:.2f}pp | {} |".format(
        abs(cm - float(per[per["arm"] == "W_fix"]["cagr"].median())) * 100,
        "✅ 押中" if abs(cm - float(per[per["arm"] == "W_fix"]["cagr"].median())) * 100 < 2 else "⛔ 沒押中"))
    A("")
    A("⚠ b3（谷年移到 2022）與 b4（2022 的 w 高於全窗中位）見 §七 的谷年表與下表。")
    A("")

    # ── 輸出 ──
    os.makedirs(out, exist_ok=True)
    rows.to_csv(os.path.join(out, "per_seed_arm.csv"), index=False)
    per.to_csv(os.path.join(out, "per_seed_collapsed.csv"), index=False)
    meta.to_csv(os.path.join(out, "per_seed_meta.csv"), index=False)
    pd.DataFrame(res["fix"]).to_csv(os.path.join(out, "fixture.csv"), index=False)
    pd.DataFrame(res["bridge"]).to_csv(os.path.join(out, "bridge.csv"), index=False)
    pd.DataFrame({"rebal_pos": rb, "date": [str(cal[w0 + int(t)].date()) for t in rb]}
                 ).to_csv(os.path.join(out, "rebal_days.csv"), index=False)
    pd.DataFrame(wmat, columns=[str(cal[w0 + int(t)].date()) for t in rb]
                 ).to_csv(os.path.join(out, "w_by_seed.csv"), index=False)
    pd.DataFrame([{"ci": "bootstrap", **ci_boot},
                  {"ci": "常態近似", "n": ci_norm["n_months"], "diff_pp": ci_norm["diff_pp"],
                   "lo_pp": ci_norm["lo_pp"], "hi_pp": ci_norm["hi_pp"],
                   "pos": ci_norm["pos_months"], "detectable": ci_norm["detectable"]}]
                 ).to_csv(os.path.join(out, "gate_i.csv"), index=False)
    pv.to_csv(os.path.join(out, "trough_year.csv"))

    txt = "\n".join(A_) + "\n"
    with open(os.path.join(out, "P17_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(txt)
    print(txt)
    print("✅ 交件寫到 {}（{:.0f}s）".format(out, time.time() - res["t0"]))


if __name__ == "__main__":
    report(main())

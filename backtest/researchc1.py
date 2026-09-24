"""PREREGC1：SMA 趨勢濾網（多頭持有 vs 現金）—— 六幣 —— 回測線執行端。

⛔ 登錄全文：`登錄全文-PREREGC1_SMA趨勢濾網_加密策略線_v6_sha3a9109fcc10a8f16-20260923-2349.md`
   sha256[:16] ＝ **3a9109fcc10a8f16**（⭐ 整檔含 pw1 行；本線已自己重算相符）／18,297 B
⛔ 口徑：`登錄全文-口徑定版草稿五格_加密策略線_v3_sha284c106a7c7ddf67-20260923-2220.md`
   sha256[:16] ＝ **284c106a7c7ddf67**（整檔）／7,584 B ⇒ ✅ 已通過
✅ 授權：裁定線 20260923-2354「PREREGC1 v6 過目通過，准開跑」
✅ 四個實作問題：裁定線 20260924-0038 逐件答（答案都已寫在 v6 正文裡）

⛔⛔ 本支【不訂判準、不訂措辭、不寫解讀】——§2-D 的判準、§四 的四個出口、
     §五 的強制揭露，全部逐字取自登錄。回測線只負責跑與報數字。

⭐ 裁定線 20260924-0038 定下來的四件（⛔ 本支照字面，不自己挑）：
  ① 窗【不對齊】：各幣從自己 SMA_N 有值那天起算（v6 §2-A，使用者裁定）
  ② 暖身期【剔除】：窗首 ＝ 第 N 根；買進持有對照組從同一天起算
  ③ 判定格 ＝ 每幣一格：N=200 規則 vs 該幣自己的買進持有
     （N=50／BTC 描述欄／假訊號組 全部只作描述或只決定措辭）
  ④ 出口② 的分母 ＝ 6（一幣一次；兩腳都嚴格優仍算一次）
  ⑤ 判定以 |回落| 深度比為準（本專案一貫讀法，見 P15 §9-3）

⚠⚠ 本支對 v6 §八 的一個回報（⛔ 不是不照做，是它不適用）：
  §八 要回測線「開跑前把四處外部化：成本常數／漲跌停取整／市場碼／bench 序列」。
  ⇒ ⭐ 那四處全部屬於 `research11.simulate_mtm`（N 個等權槽的個股組合引擎）。
  ⇒ ⛔⛔ 而本件是【單資產、二元持有/空手】的擇時規則，⛔ 不呼叫那支引擎
    （同 P17 的 compose：兩資產權益層合成也沒有呼叫它）。
  ⇒ ⇒ 所以本支【沒有東西可以外部化】，⛔ 也不該為了「照做」去硬接那支引擎
    —— 硬接會把漲跌停、張數取整、槽位這些幣市不存在的東西帶進來。
  ⇒ ⏳ 已回報加密策略線與裁定線；若裁定要本支改走引擎，本線照改。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data", "crypto")
OUT = os.path.join(HERE, "resultsc1")

# ── 登錄寫死的常數（⛔ 一個都不可以在這裡「挑」）──────────────────────────
COINS = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE")   # §2-A
N_MAIN = 200                                          # §2-A 主格
N_ROBUST = 50                                         # §2-A 穩健性（⛔ 只決定措辭）
COST_RT = 0.002                                       # §2-B 來回 0.2%（taker×2）
DAYS_YEAR = 365.25                                    # 口徑 v3 §① 幣市用日曆日
N_BOOT = 2000                                         # §七
N_PLACEBO = 1000                                      # §2-C③
SEED = 20260923                                       # §七／§2-C③ 種子寫死
ASOF = "2026-09-20"                                   # §2-A 快照
LAST_FULL = "2026-09-19"                              # §2-A 最新完整日（UTC）
EXPO_DEGEN = 0.90                                     # §四④ 曝險 ≥90% ⇒ 假訊號閘退化
MIN_TRADES = 5                                        # §五② 進出場次數 <5 ⇒ 結構上不可得
PCTL_TAIL = 90.0                                      # §2-D 必12／§五 假訊號上尾門檻


# ── 規則與績效 ─────────────────────────────────────────────────────────────
def sma(c: np.ndarray, n: int) -> np.ndarray:
    """簡單移動平均，前 n−1 根為 NaN（⭐ 只用到 t 為止的收盤，⛔ 沒有前視）。"""
    out = np.full(len(c), np.nan)
    if len(c) >= n:
        cs = np.cumsum(np.insert(c, 0, 0.0))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def rule_series(c: np.ndarray, n: int):
    """§2-A：訊號(t)＝close(t)>SMA_N(t)；部位從 close(t) 持有到 close(t+1)。

    ⭐⭐ 回傳的 r_rule[i] 對應【窗內第 i 個報酬期間】，逐字照登錄：
        r_rule[i] ＝ sig[i] × r[i+1]，⛔ 不是 sig[i] × r[i]
    ⇒ 成本：部位在 i 與 i−1 之間改變 ⇒ 扣單邊 COST_RT/2。
    """
    m = sma(c, n)
    ok = np.flatnonzero(~np.isnan(m))
    if len(ok) == 0:
        return None
    w0 = int(ok[0])                       # ⭐ 窗首 ＝ SMA_N 第一個有值的那一天（②暖身剔除）
    cw, mw = c[w0:], m[w0:]
    sig = (cw > mw).astype(float)         # 訊號(t)
    r = np.empty(len(cw)); r[0] = 0.0
    r[1:] = cw[1:] / cw[:-1] - 1.0        # r(t) ＝ close(t)/close(t-1) − 1
    # ⭐ 訊號(t) 吃 r(t+1) ⇒ 對齊成「第 i 期報酬 ＝ sig[i] × r[i+1]」
    held = sig[:-1]                       # 第 i 期持有旗標（i ＝ 0..n-2）
    rets = r[1:]                          # 第 i 期報酬
    gross = held * rets
    # 成本：持有旗標從上一期到這一期改變 ⇒ 一次單邊成本
    prev = np.insert(held[:-1], 0, 0.0)   # ⭐ 期初從空手開始 ⇒ 第一次進場要收成本
    cost = np.abs(held - prev) * (COST_RT / 2.0)
    net = gross - cost
    bh = rets.copy()                      # ②逐幣買進持有（同窗同幣，⛔ 不扣成本：它不換手）
    return {"w0": w0, "held": held, "r_rule": net, "r_bh": bh,
            "gross": gross, "cost": cost}


def equity(r: np.ndarray) -> np.ndarray:
    return np.cumprod(1.0 + r)


def cagr(r: np.ndarray) -> float:
    """CAGR，⭐ 幣市用日曆日 365.25（口徑 v3 §①）。"""
    v = equity(r)
    if v[-1] <= 0:
        return -1.0
    return float(v[-1] ** (DAYS_YEAR / len(r)) - 1.0)


def mdd(r: np.ndarray) -> float:
    """最大回落（⭐ 回傳【負數】；深度比用絕對值，見下方 judge）。"""
    v = equity(r)
    return float(np.min(v / np.maximum.accumulate(v) - 1.0))


# ── §七 Politis–White (2004) 自動區塊長（⭐ 外生演算法，⛔ 不看回測結果）──────
def politis_white_block(x: np.ndarray) -> int:
    """stationary bootstrap 的自動區塊長。

    ⭐ 逐字照 Politis–White (2004) 的 flat-top lag-window 做法：
      ① K_N ＝ max(5, sqrt(log10(n)))；門檻 c ＝ 2 sqrt(log10(n)/n)
      ② m̂ ＝ 最小的 k，使 |ρ(k+j)| < c 對 j=1..K_N 全部成立
      ③ M ＝ 2 m̂（上限 n/2）；Ĝ、D̂ 依原文（stationary 版 D̂ ＝ 2 ĝ(0)²）
      ④ b ＝ (2 Ĝ² / D̂)^(1/3) n^(1/3)，夾在 [1, min(3 sqrt(n), n/3)]
    ⛔ 本函式只看 x 的自相關結構，⛔ 不看任何判定結果。
    """
    x = np.asarray(x, float)
    n = len(x)
    xm = x - x.mean()
    denom = float(np.dot(xm, xm))
    if denom <= 0:
        return 1
    maxlag = max(1, min(n - 1, int(np.ceil(10 * np.log10(n)))))
    rho = np.array([float(np.dot(xm[:n - k], xm[k:]) / denom) for k in range(maxlag + 1)])
    KN = int(max(5, np.sqrt(np.log10(n))))
    c = 2.0 * np.sqrt(np.log10(n) / n)
    mhat = 0
    for k in range(1, maxlag + 1):
        hi = min(maxlag, k + KN)
        if hi > k and np.all(np.abs(rho[k + 1:hi + 1]) < c):
            mhat = k - 1
            break
    else:
        mhat = maxlag
    M = min(int(2 * max(mhat, 1)), n // 2)
    lam = lambda t: 1.0 if abs(t) <= 0.5 else (2.0 * (1.0 - abs(t)) if abs(t) <= 1 else 0.0)
    g = np.array([float(np.dot(xm[:n - k], xm[k:]) / n) for k in range(M + 1)])
    Ghat = 0.0
    for k in range(1, M + 1):
        Ghat += 2.0 * lam(k / M) * k * g[k]
    ghat0 = g[0] + 2.0 * sum(lam(k / M) * g[k] for k in range(1, M + 1))
    Dhat = 2.0 * ghat0 ** 2
    if Dhat <= 0 or not np.isfinite(Ghat):
        return 1
    b = (2.0 * Ghat ** 2 / Dhat) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    return int(np.clip(round(b), 1, max(1, min(3 * np.sqrt(n), n / 3))))


def stationary_idx(n: int, L: float, rng) -> np.ndarray:
    """stationary block bootstrap 的索引（⭐ 幾何長度、環繞）。"""
    p = 1.0 / max(L, 1.0)
    idx = np.empty(n, int)
    i = 0
    while i < n:
        start = rng.integers(0, n)
        ln = min(rng.geometric(p), n - i)
        idx[i:i + ln] = (start + np.arange(ln)) % n
        i += ln
    return idx


def paired_ci(r_rule: np.ndarray, r_bh: np.ndarray, L: int, rng):
    """§七：配對的 stationary block bootstrap ⇒ 兩臂用【同一組】區塊。"""
    d_cagr, d_mdd = [], []
    for _ in range(N_BOOT):
        i = stationary_idx(len(r_rule), L, rng)
        a, b = r_rule[i], r_bh[i]
        d_cagr.append(cagr(a) - cagr(b))
        d_mdd.append(abs(mdd(a)) - abs(mdd(b)))     # ⭐ 深度比（裁定線 0038 §二）
    q = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
    return {"cagr": q(d_cagr), "mdd": q(d_mdd)}


# ── §2-C③ 假訊號組：整段打亂重排（⛔ 保留段數、各段長度、曝險）────────────
def segments(held: np.ndarray):
    """把 0/1 持有序列切成 (值, 長度) 的段。"""
    out, cur, ln = [], held[0], 1
    for v in held[1:]:
        if v == cur:
            ln += 1
        else:
            out.append((cur, ln)); cur, ln = v, 1
    out.append((cur, ln))
    return out


def placebo_dist(held: np.ndarray, rets: np.ndarray, rng):
    """§2-C③：只打亂【段落出現的順序】，1,000 組，每組同樣扣 0.2% 來回。"""
    segs = segments(held)
    cg, md = [], []
    for _ in range(N_PLACEBO):
        order = rng.permutation(len(segs))
        h = np.concatenate([np.full(segs[k][1], segs[k][0]) for k in order])
        prev = np.insert(h[:-1], 0, 0.0)
        net = h * rets - np.abs(h - prev) * (COST_RT / 2.0)
        cg.append(cagr(net)); md.append(abs(mdd(net)))
    return np.array(cg), np.array(md)


# ── §2-D 判準（⛔ 逐字取自登錄，⛔ 本支不改一個字）────────────────────────
def judge(cg_r, md_r, cg_b, md_b):
    """主判準：年化 ≥ 買進持有 且 |最大回落| ≤ 買進持有，且至少一腳嚴格優。"""
    leg_c = cg_r >= cg_b
    leg_m = abs(md_r) <= abs(md_b)
    strict_c = cg_r > cg_b
    strict_m = abs(md_r) < abs(md_b)
    ok = leg_c and leg_m and (strict_c or strict_m)
    return ok, strict_c, strict_m


def exit_of(ok, strict_c, strict_m, ci, ci2_mdd):
    """§四 出口①~③（⛔ 綁【判定格嚴格優那一腳的方向】，⛔ 不綁先驗）。"""
    if not ok:
        return "判定格未過", "⛔ 判定格沒過 ⇒ 不進出口判斷"
    legs = []
    if strict_c:
        legs.append(("CAGR", ci["cagr"]))
    if strict_m:
        legs.append(("MDD", ci["mdd"]))
    # ⚠ 回落腳：L 與 2L 兩條方向不一致 ⇒ 標【CI 不穩】一律走出口①（§七）
    if strict_m:
        lo1, hi1 = ci["mdd"]; lo2, hi2 = ci2_mdd
        s1 = 0 if lo1 <= 0 <= hi1 else (1 if lo1 > 0 else -1)
        s2 = 0 if lo2 <= 0 <= hi2 else (1 if lo2 > 0 else -1)
        if s1 != s2:
            return "出口①", "⚠ 回落腳 CI 不穩（L 與 2L 方向不一致）⇒ 一律走出口①"
    outs = []
    for name, (lo, hi) in legs:
        if lo <= 0 <= hi:
            outs.append((name, "出口①", "CI 含 0 ⇒ 測不出"))
        elif hi < 0:
            # ⭐ 配對差為負 ＝ 規則的值比買進持有小
            #   CAGR 腳：嚴格優是「規則 > 基準」⇒ 差應為正 ⇒ 負 ＝ 反向
            #   MDD 腳：嚴格優是「|規則| < |基準|」⇒ 差應為負 ⇒ 負 ＝ 同向
            outs.append((name, "出口②" if name == "MDD" else "出口③",
                         "CI 不含 0，配對差為負"))
        else:
            outs.append((name, "出口③" if name == "MDD" else "出口②",
                         "CI 不含 0，配對差為正"))
    # 兩腳都嚴格優 ⇒ 兩條都要出口② 才算；任一含 0 ⇒ 降級到該條的出口
    names = [o[1] for o in outs]
    if all(x == "出口②" for x in names):
        return "出口②", "；".join("{} {}".format(a, c) for a, b, c in outs)
    if "出口③" in names:
        return "出口③", "；".join("{} {}".format(a, c) for a, b, c in outs)
    return "出口①", "；".join("{} {}".format(a, c) for a, b, c in outs)


def breakeven_cost(c: np.ndarray, n: int, leg: str, cg_b, md_b) -> float:
    """§五之二：來回成本調到多高時，該腳「嚴格優」消失。"""
    lo, hi = COST_RT, 0.50
    base = rule_series(c, n)
    if base is None:
        return float("nan")

    def strict_at(rt):
        held, rets = base["held"], base["r_bh"]
        prev = np.insert(held[:-1], 0, 0.0)
        net = held * rets - np.abs(held - prev) * (rt / 2.0)
        return (cagr(net) > cg_b) if leg == "CAGR" else (abs(mdd(net)) < abs(md_b))

    if not strict_at(lo):
        return float("nan")
    if strict_at(hi):
        return float("inf")
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if strict_at(mid):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0

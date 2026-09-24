"""PREREGC3：六幣組合層（依 C1 訊號、membership 觸發、現金限制下的漂移權重）—— 回測線執行端。

⛔ 登錄全文：`登錄全文-PREREGC3_六幣組合層動態等權_加密策略線_v4_shaf4021ef34db9e27d-20260924-1811.md`
   sha256[:16] ＝ **f4021ef34db9e27d**（⭐ 整檔含 pw1 行；本線已自己重算相符）／17,190 B
✅ 過目：裁定線 20260924-1814「C3 v4 過目通過 … fixture 過了才開跑」

⛔⛔ 本支【不訂判準、不訂措辭、不寫解讀】。本檔目前只有三件（開跑前置，裁定線 1814 §三）：
  ① 窗首精確日（§九②）　② 同步率描述（§九①，⛔ 純描述、⛔ 不設門檻）　③ 引擎 ＋ fixture（§八）

⭐ 引擎逐字照 v4 §2-A之二（本線的讀法寫在 simulate() 的 docstring；⛔ 有讀法差異處另列「實作選擇」）
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C1   # noqa: E402  ⭐ 訊號逐字沿用 C1 v6（登錄 §一）

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsc3")

COINS = C1.COINS            # §2-A 分母＝6
N_SIG = C1.N_MAIN           # 沿用 C1：SMA200
COST_RT = C1.COST_RT        # §2-B 來回 0.2%（taker×2）⇒ 單邊 0.1%
LAST_FULL = C1.LAST_FULL


# ── 資料與訊號（⭐ 餵引擎的那一層也走一次：〈一百一十三〉09-24 附則）─────────
def load_panel(data_dir: str = C1.DATA, coins=COINS, n: int = N_SIG):
    """回傳 (dates, close[T×K], sig[T×K], w0_by_coin)，窗 ＝ 六幣同時有 SMA200 的第一天起。

    ⭐ 訊號在【各幣自己的全歷史】上算（SMA 只用到 t 為止 ⇒ 沒有前視），再切到共同窗。
    """
    frames, w0s = {}, {}
    for s in coins:
        d = pd.read_csv(os.path.join(data_dir, "{}.csv".format(s)), dtype={"date": str})
        d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
        c = d["close"].to_numpy(float)
        m = C1.sma(c, n)
        ok = np.flatnonzero(~np.isnan(m))
        w0s[s] = d["date"].iloc[int(ok[0])]
        frames[s] = pd.DataFrame({"date": d["date"], "close": c,
                                  "sig": np.where(np.isnan(m), np.nan, (c > m).astype(float))})
    start = max(w0s.values())                      # ⭐ §2-A 窗首 ＝ 最晚起算那一幣
    idx = None
    for s in coins:
        f = frames[s][frames[s]["date"] >= start].set_index("date")
        idx = f.index if idx is None else idx.intersection(f.index)
    dates = np.array(sorted(idx))
    close = np.column_stack([frames[s].set_index("date").loc[dates, "close"].to_numpy(float) for s in coins])
    sig = np.column_stack([frames[s].set_index("date").loc[dates, "sig"].to_numpy(float) for s in coins])
    assert not np.isnan(sig).any(), "窗內仍有 SMA200 未定義的幣"
    return dates, close, sig, w0s


# ── 引擎 ─────────────────────────────────────────────────────────────────────
def simulate(close: np.ndarray, sig: np.ndarray, cost_rt: float = COST_RT,
             variant: str = "v4", trace: bool = False, stats: bool = False):
    """v4 §2-A之二 的逐日引擎。回傳 nav_pre（長 T）；nav_pre[0]＝1。

    ⭐ 時點（沿用 C1）：訊號(t) 在收盤 t 知道 ⇒ 交易在收盤 t 成交 ⇒ 吃 t→t+1 的報酬。
       第 i 期報酬 ＝ nav_pre[i+1]／nav_pre[i] − 1（收盤 i 的成本算在第 i 期，同 C1）。
    ⭐ 收盤 t 的處理順序（本線讀法）：
       ① 離開 S_t 的幣：全數賣出 ⇒ 收入（扣單邊成本）轉現金；目標與成本基礎歸零
       ② 進入 S_t 的幣：進場日目標金額 ＝ 【①之後】的淨值 ／ |S_t| ⇒ ⛔ 之後不重算（凍結）
       ③ 等待中 ＝ S_t 內「成本基礎 ＜ 進場日目標金額」的幣（含 0 與部分買入；v4 洞①）
       ④ 當日可用現金按等待幣數【平分】；每幣實際買 ＝ min(平分額, 缺口)（v4 洞②）
          ⇒ 多的留現金，⛔ 當天不轉給其他等待中的幣；次一交易日重跑一次同樣流程
       ⑤ 同一交易日只做一次分配結算
    ⭐ 實作選擇（⛔ 登錄沒逐字寫到、本線先照這樣寫死，已在交件信列出請確認）：
       (i)  買入花費 X 現金 ⇒ 得到 X×(1−單邊成本) 的部位；成本基礎記 X（＝現金支出）
       (ii) 賣出部位 V ⇒ 得到 V×(1−單邊成本) 現金
       (iii) 部位以【顆數】記帳（顆數 × 收盤價 ＝ 市值）
    stats：True ⇒ 另回記帳（買額、賣額、成本、買賣次數、逐日收盤後現金比例）；⛔ 不改任何數值路徑
    variant：只給 selftest 的鑑別力格用（⛔ 正式跑一律 "v4"）
       "nocap"     ⇒ 拿掉洞② 的缺口上限
       "v3wait"    ⇒ 等待中只算「成本基礎 ＝ 0」（v3 的斷崖版）
       "retarget"  ⇒ 目標金額每天用當日淨值／|S_t| 重算（偷偷再平衡）
       "sameday"   ⇒ 封頂後的餘額當天轉給其他等待中的幣
       "lookahead" ⇒ 訊號(t) 吃 r(t)（時點錯）
    """
    T, K = close.shape
    f = cost_rt / 2.0
    if variant == "lookahead":
        sig = np.vstack([sig[1:], sig[-1:]])
    units = np.zeros(K)
    basis = np.zeros(K)
    target = np.zeros(K)
    member = np.zeros(K, bool)
    cash = 1.0
    nav_pre = np.empty(T)
    rows = []
    st = {"buy": 0.0, "sell": 0.0, "fee": 0.0, "n_buy": 0, "n_sell": 0, "cash_frac": np.zeros(T)}
    for t in range(T):
        p = close[t]
        nav_pre[t] = cash + float(np.dot(units, p))
        s_now = sig[t] > 0.5
        # ① 離場
        for k in np.flatnonzero(member & ~s_now):
            v = units[k] * p[k]
            st["sell"] += v; st["fee"] += v * f; st["n_sell"] += int(units[k] > 0.0)   # ⭐ 沒買到就離場的不算一次賣出
            cash += units[k] * p[k] * (1.0 - f)
            units[k] = 0.0; basis[k] = 0.0; target[k] = 0.0
        nav_after_exit = cash + float(np.dot(units, p))
        n_s = int(s_now.sum())
        # ② 進場：凍結目標金額
        for k in np.flatnonzero(s_now & ~member):
            target[k] = nav_after_exit / n_s
            basis[k] = 0.0
        if variant == "retarget" and n_s > 0:
            target[s_now] = nav_after_exit / n_s
        member = s_now.copy()
        # ③ 等待中
        if variant == "v3wait":
            # v3：只有「進場當天」或「成本基礎 0」才算等待；部分買入者永遠不補
            waiting = [k for k in np.flatnonzero(member) if basis[k] == 0.0 and target[k] > 0.0]
        else:
            waiting = [k for k in np.flatnonzero(member) if basis[k] < target[k]]
        # ④ 平分、封頂
        if waiting and cash > 0.0:
            share = cash / len(waiting)
            spent = {}
            for k in waiting:
                gap = target[k] - basis[k]
                x = share if variant == "nocap" else min(share, gap)
                spent[k] = x
            if variant == "sameday":
                left = cash - sum(spent.values())
                for k in waiting:
                    more = min(left, target[k] - basis[k] - spent[k])
                    if more > 0:
                        spent[k] += more; left -= more
            for k, x in spent.items():
                if x <= 0.0:
                    continue
                st["buy"] += x; st["fee"] += x * f; st["n_buy"] += 1
                units[k] += x * (1.0 - f) / p[k]
                basis[k] = target[k] if x == target[k] - basis[k] else basis[k] + x
                cash -= x
        nav_post = cash + float(np.dot(units, p))
        st["cash_frac"][t] = cash / nav_post if nav_post > 0 else 1.0
        if trace:
            rows.append({"t": t, "nav_pre": nav_pre[t], "cash": cash,
                         "units": units.copy(), "basis": basis.copy(), "target": target.copy(),
                         "nav_post": cash + float(np.dot(units, p))})
    if stats:
        return nav_pre, st
    return (nav_pre, rows) if trace else nav_pre


def rets_from_nav(nav_pre: np.ndarray) -> np.ndarray:
    return nav_pre[1:] / nav_pre[:-1] - 1.0


# ── §九① 同步率（⛔ 純描述、⛔ 不設門檻、⛔ 不進判準）────────────────────────
def sync_describe(sig: np.ndarray):
    """用【訊號(t)】（＝收盤 t 決定、t+1 生效的在場集合）逐日描述。"""
    T, K = sig.shape
    n_in = sig.sum(axis=1).astype(int)
    dist = {k: int((n_in == k).sum()) for k in range(K + 1)}
    pair_same = np.zeros((K, K))
    phi = np.full((K, K), np.nan)
    for i in range(K):
        for j in range(K):
            pair_same[i, j] = float((sig[:, i] == sig[:, j]).mean())
            a, b = sig[:, i], sig[:, j]
            if a.std() > 0 and b.std() > 0:
                phi[i, j] = float(np.corrcoef(a, b)[0, 1])
    iu = np.triu_indices(K, 1)
    return {"T": T, "dist": dist,
            "all_in": dist[K] / T, "all_out": dist[0] / T,
            "unanimous": (dist[K] + dist[0]) / T,
            "mean_n_in": float(n_in.mean()),
            "pair_same": pair_same, "phi": phi,
            "pair_same_mean": float(pair_same[iu].mean()),
            "phi_mean": float(np.nanmean(phi[iu])),
            "phi_min": float(np.nanmin(phi[iu])), "phi_max": float(np.nanmax(phi[iu]))}

# -*- coding: utf-8 -*-
"""H2（144／200MA 雙翻揚）**純計數**：事件數、合併後事件數、相異檔數、獨立區段數。

⛔⛔ 本支【不算任何報酬】、⛔ 不跑策略、⛔ 不開登錄、⛔ 不動任何判定。
   ⇒ ⭐ 依台股策略線 1105 §三／裁定線 1130 §三：純描述、與報酬無關 ⇒ ⛔ 不算偷看。
   ⇒ ⛔⛔ 而它【不可以】用來決定要不要測 —— 只決定【出口怎麼寫】與【先驗怎麼押】。

口徑出處（⭐ 逐條指名，⛔ 本線一個字都沒自訂）：
  訊號　　H2 seq=5 §一：MA144(t)>MA144(t−k) ∧ MA200(t)>MA200(t−k)
          ∧ close(t) ≥ max(MA144(t),MA200(t)) ∧ close(t−1) < max(MA144(t−1),MA200(t−1))
  k　　　 H2 seq=5 §五①：**判定格固定 k=5**，⛔ 不掃；k=1／10 各一格【只作描述】
  母體　　H2 seq=5 §六：需 ≥200 根日 K ⇒ 必報母體檔數、被排除的檔數
  判定窗　裁定線 1047 §一 (甲) 釘死窗 [523, 2835] ＝ 2017-03-02 ~ 2026-08-24（W=2,313）
  合併　　H2 seq=5 §六之二②：同一檔在前一事件的持有窗（H 天）結束前再觸發 ⇒ 併入前一個
          §六之二⑦：持有窗從【被保留的那一個事件】的 t₀ 起算，⛔ 不隨併入的事件往後延
  區段　　§六之二⑤⑥：從判定窗起點 **523** 切、長度 H 的不重疊區段
          出口分流取 **min(同檔非重疊 n, 有 ≥1 事件的獨立區段數)** 對照 30／100
          出口③ ⇔ H ≤ ⌊W／100⌋　出口② ⇔ H ≤ ⌊W／30⌋（⛔ 是窗長的函數，⛔ 不是常數）
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

W0, W1 = 523, 2835                  # ⭐ 釘死窗（含兩端）
W = W1 - W0 + 1                     # ＝ 2,313 交易日
HS = (20, 60, 120)
KS = (5, 1, 10)                     # ⭐ 5 ＝ 判定格（§五①）；1／10 只作描述
MIN_BARS = 200                      # §六：需 ≥200 根日 K
LONG, SHORT = 200, 144

cal = D.load_calendar()
uni = D.load_universe()
print("日曆 {} 日｜釘死窗 [{},{}] {} ~ {}（W={:,}）".format(
    len(cal), W0, W1, cal[W0].date(), cal[W1].date(), W))
print("universe {:,} 檔".format(len(uni)))


def ma(x: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(x)
    return s.rolling(n, min_periods=n).mean().to_numpy()


events = {k: [] for k in KS}        # k -> list[(sid, pos)]
n_pool = 0
n_drop_bars = 0
n_missing = 0

for sid, mkt in zip(uni["stock_id"].astype(str), uni["market"].astype(str)):
    st = D.load_stock(sid, mkt, cal)
    if st is None:
        n_missing += 1
        continue
    c = st.df["close"].to_numpy(float)
    if np.isfinite(c).sum() < MIN_BARS:
        n_drop_bars += 1
        continue
    n_pool += 1
    m144, m200 = ma(c, SHORT), ma(c, LONG)
    mx = np.fmax(m144, m200)
    for k in KS:
        up = np.zeros(len(c), bool)
        up[k:] = (m144[k:] > m144[:-k]) & (m200[k:] > m200[:-k])
        first = np.zeros(len(c), bool)
        first[1:] = (c[1:] >= mx[1:]) & (c[:-1] < mx[:-1])
        sig = up & first & np.isfinite(c) & np.isfinite(mx)
        idx = np.flatnonzero(sig)
        idx = idx[(idx >= W0) & (idx <= W1)]
        for p in idx:
            events[k].append((sid, int(p)))

print("⭐ 母體 {:,} 檔（≥{} 根日 K）｜⛔ 因 K 棒不足排除 {:,} 檔｜⛔ 讀不到 {:,} 檔"
      .format(n_pool, MIN_BARS, n_drop_bars, n_missing))
print()


def merge_same_sid(ev: list[tuple[str, int]], H: int) -> list[tuple[str, int]]:
    """§六之二②⑦：同檔在【被保留事件】的 t₀ + H 之前再觸發 ⇒ 併入，⛔ 起點不往後延。"""
    out = []
    by = {}
    for sid, p in sorted(ev, key=lambda t: (t[0], t[1])):
        keep = by.get(sid)
        if keep is None or p >= keep + H:
            out.append((sid, p))
            by[sid] = p
    return out


def seg_hits(ev: list[tuple[str, int]], H: int) -> int:
    """從 523 起切、長度 H 的不重疊區段中，有 ≥1 個事件的段數。"""
    return len({(p - W0) // H for _, p in ev if (p - W0) // H < W // H})


rows = []
for k in KS:
    ev = events[k]
    raw_n = len(ev)
    raw_sid = len({s for s, _ in ev})
    tag = "⭐ 判定格" if k == 5 else "（描述）"
    print("=== k={} {} ｜原始觸發 {:,} 筆／相異 {:,} 檔 ===".format(k, tag, raw_n, raw_sid))
    for H in HS:
        mg = merge_same_sid(ev, H)
        n, nsid = len(mg), len({s for s, _ in mg})
        cut = raw_n - n
        cap = W // H
        hits = seg_hits(mg, H)
        conservative = min(n, hits)
        exit_no = "③" if conservative >= 100 else ("②" if conservative >= 30 else "①")
        rows.append(dict(k=k, H=H, raw=raw_n, merged=n, cut=cut,
                         cut_pct=cut / raw_n * 100 if raw_n else np.nan,
                         sid_raw=raw_sid, sid_merged=nsid,
                         seg_cap=cap, seg_hit=hits, conservative=conservative, exit=exit_no))
        print("  H={:>3}｜合併後 **{:>5,}** 筆（被併掉 {:>5,}＝{:>5.1f}%）｜相異檔 {:,}→{:,}"
              .format(H, n, cut, cut / raw_n * 100 if raw_n else float("nan"), raw_sid, nsid))
        print("        ④ 不重疊 {:>3} 日區段：上限 ⌊{:,}/{}⌋ = **{:>3}** ｜有 ≥1 事件 **{:>3}** 段"
              .format(H, W, H, cap, hits))
        print("        ⇒ min(同檔非重疊 n={:,}，獨立區段 {}) = **{}** ⇒ 出口 **{}**"
              .format(n, hits, conservative, exit_no))
    print()

df = pd.DataFrame(rows)
out = "backtest/resultsh2_counts.csv"
df.to_csv(out, index=False, encoding="utf-8")
print("⇒ 落檔 {}（{} 列）".format(out, len(df)))
print()
print("=== ⭐⭐ 判定格（k=5）三個 H 的結論，對照裁定線 1235 §二 的門檻函數 ===")
print("   W={:,} ⇒ 出口③ ⇔ H ≤ ⌊W/100⌋ = {}；出口② ⇔ H ≤ ⌊W/30⌋ = {}".format(
    W, W // 100, W // 30))
for r in df[df.k == 5].itertuples():
    print("   H={:>3} ⇒ 區段上限 {:>3}｜實際 {:>3} 段｜合併後 {:>5,} 筆 ⇒ min={:>4} ⇒ **出口 {}**"
          .format(r.H, r.seg_cap, r.seg_hit, r.merged, r.conservative, r._12 if hasattr(r, "_12") else r.exit))

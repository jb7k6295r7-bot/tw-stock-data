"""研究二十：RS 五候選排序相關性前測 ＋ ZVR 分佈。判準 backtest/PREREG20.md。

    python3 -m backtest.research20 [--procs 4] [--limit N]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research15 as R15

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results20")
R11DIR = os.path.join(HERE, "results11")
LIQ = 5e7
BANDS = [(-np.inf, 60), (60, 80), (80, 100), (100, 200), (200, np.inf)]
_G: dict = {}


def _init(cal):
    _G["cal"] = cal


def _spearman(x, y):
    rx = pd.Series(x).rank().to_numpy(); ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def load_one(args):
    sid, market = args
    st = D.load_stock(sid, market, _G["cal"])
    if st is None:
        return None
    df = st.df
    return sid, df["close"].to_numpy(float), df["volume"].to_numpy(float), df["amount"].to_numpy(float), df["traded"].to_numpy(bool)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); ap.add_argument("--limit", type=int)
    a = ap.parse_args(); os.makedirs(RESULTS, exist_ok=True); t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"]
    uni = uni[~uni["stock_id"].map(ind).isin(R15.EXCL_IND)]
    if a.limit:
        uni = uni.head(a.limit)
    sids, C, V, AMT, T = [], [], [], [], []
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        for r in pool.imap_unordered(load_one, list(zip(uni["stock_id"], uni["market"])), chunksize=16):
            if r is None:
                continue
            sids.append(r[0]); C.append(r[1]); V.append(r[2]); AMT.append(r[3]); T.append(r[4])
    C = np.array(C).T; V = np.array(V).T; AMT = np.array(AMT).T; T = np.array(T).T      # (days, stocks)
    n_days, n_stk = C.shape
    print(f"載入 {n_stk} 檔 {time.time() - t0:.0f}s", file=sys.stderr)
    bench = D.load_benchmark(cal)["close"].to_numpy(float)
    # 沿用前值的收盤（非交易日）；洞 ≥ 5 日標記
    Cf = pd.DataFrame(C).ffill().to_numpy()
    gap = pd.DataFrame(~T).rolling(5, min_periods=5).sum().to_numpy()      # 最近 5 日無成交天數
    cum_traded = np.cumsum(T, axis=0)
    amt20 = pd.DataFrame(np.where(T, AMT, np.nan)).rolling(20, min_periods=20).mean().to_numpy()   # 有成交日的均額（近似）
    r = Cf / bench[:, None]
    L = ["# 研究二十：RS 前測 ＋ ZVR——細表", "", f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG20.md`。", ""]
    # 月底快照
    months = pd.Series(cal).dt.to_period("M")
    snaps = [int(i) for i in pd.Series(range(n_days)).groupby(months.to_numpy()).max().to_numpy() if cal[int(i)] >= pd.Timestamp("2016-01-01") and cal[int(i)] <= pd.Timestamp("2026-08-31")]
    names = ["L0_20", "L0_60", "L1", "L2a", "L2b", "L3", "L4_15", "L4_10"]
    corr = {}; overlap = {}; jacc = {}; nstk = []
    up = np.vstack([np.zeros((1, n_stk), bool), Cf[1:] > Cf[:-1]])
    rp = r * 100; sma200 = pd.DataFrame(rp).rolling(200, min_periods=200).mean().to_numpy()
    for t in snaps:
        if t < 260:
            continue
        ok = (cum_traded[t] >= 260) & (gap[t] < 5) & (amt20[t] >= LIQ) & T[t]
        if ok.sum() < 50:
            continue
        idx = np.flatnonzero(ok); nstk.append(len(idx))
        def ret(n):
            return Cf[t, idx] / Cf[t - n, idx] - 1
        S = {"L0_20": r[t, idx] / r[t - 20, idx] - 1, "L0_60": r[t, idx] / r[t - 60, idx] - 1,
             "L1": rp[t, idx] / sma200[t, idx] - 1,
             "L2a": 0.4 * ret(63) + 0.2 * ret(126) + 0.2 * ret(189) + 0.2 * ret(252),
             "L2b": 0.4 * (Cf[t, idx] / Cf[t - 63, idx] - 1) + 0.2 * (Cf[t - 63, idx] / Cf[t - 126, idx] - 1) + 0.2 * (Cf[t - 126, idx] / Cf[t - 189, idx] - 1) + 0.2 * (Cf[t - 189, idx] / Cf[t - 252, idx] - 1),
             "L3": Cf[t - 21, idx] / Cf[t - 252, idx] - 1,
             "L4_15": up[t - 14:t + 1, idx].mean(0), "L4_10": up[t - 9:t + 1, idx].mean(0)}
        for i, x in enumerate(names):
            for y in names[i + 1:]:
                m = np.isfinite(S[x]) & np.isfinite(S[y])
                if m.sum() < 30:
                    continue
                corr.setdefault((x, y), []).append(_spearman(S[x][m], S[y][m]))
        base = S["L0_20"]; q = np.nanpercentile(base, 90); top0 = set(np.flatnonzero(base >= q))
        for x in names[1:]:
            qx = np.nanpercentile(S[x], 90); topx = set(np.flatnonzero(S[x] >= qx))
            if topx:
                overlap.setdefault(x, []).append(len(topx & top0) / len(topx)); jacc.setdefault(x, []).append(len(topx & top0) / len(topx | top0))
    L.append(f"## 一、快照 {len(nstk)} 個月底、每日母體中位 {np.median(nstk):.0f} 檔（p10 {np.percentile(nstk, 10):.0f}、p90 {np.percentile(nstk, 90):.0f}）"); L.append("")
    L.append("### Spearman 排序相關（128 日的中位；括號 p10 ~ p90）"); L.append("")
    L.append("| | " + " | ".join(names[1:]) + " |"); L.append("|---|" + "---|" * (len(names) - 1))
    for i, x in enumerate(names[:-1]):
        cells = []
        for y in names[1:]:
            v = corr.get((x, y)) or corr.get((y, x))
            cells.append(f"**{np.median(v):.2f}**（{np.percentile(v, 10):.2f} ~ {np.percentile(v, 90):.2f}）" if v else "—")
        L.append(f"| {x} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("### 前 10% 重疊率（候選前 10% 之中也在 L0_20 前 10% 的比例；Jaccard）"); L.append("")
    L.append("| 候選 | 重疊率 中位 | p10 ~ p90 | Jaccard 中位 |"); L.append("|---|---:|---|---:|")
    for x in names[1:]:
        v = overlap.get(x, []); j = jacc.get(x, [])
        L.append(f"| {x} | {np.median(v) * 100:.0f}% | {np.percentile(v, 10) * 100:.0f} ~ {np.percentile(v, 90) * 100:.0f}% | {np.median(j):.2f} |")
    L.append("")
    # 決策規則
    L.append("### 決策（PREREG20 二節 3）"); L.append("")
    for x in names[1:]:
        v = corr.get(("L0_20", x)); ov = overlap.get(x, [])
        same = bool(v and np.median(v) >= 0.8 and np.median(ov) >= 0.6)
        L.append(f"- {x} vs L0_20：Spearman 中位 {np.median(v):.2f}、前 10% 重疊 {np.median(ov) * 100:.0f}% ⇒ {'同一件事，併入 L0' if same else '不同'}")
    v = corr.get(("L2a", "L2b")); L.append(f"- L2a vs L2b：{np.median(v):.2f} ⇒ {'歧義不重要' if np.median(v) >= 0.9 else '歧義重要'}")
    for x in ("L4_15", "L4_10"):
        mx = max(np.median(corr.get((a_, x)) or corr.get((x, a_))) for a_ in names if a_ != x and a_ not in ("L4_15", "L4_10"))
        L.append(f"- {x} 與其餘（不含另一個 L4）的最大 Spearman 中位 {mx:.2f} ⇒ {'有獨立資訊' if mx < 0.5 else '沒有'}")
    L.append("")
    # MVP 通過率（最後 24 個快照）
    L.append("### MVP 通過率（原版 12/15、量 +20%、價 +20%；台股版 7/10、量 +20%、價 +10%）"); L.append("")
    Vf = pd.DataFrame(np.where(T, V, np.nan)).ffill().to_numpy()
    pr = []
    for t in snaps[-36:]:
        ok = (cum_traded[t] >= 260) & (gap[t] < 5) & (amt20[t] >= LIQ) & T[t]; idx = np.flatnonzero(ok)
        v15 = Vf[t - 14:t + 1, idx].mean(0); v15p = Vf[t - 29:t - 14, idx].mean(0); p15 = Cf[t, idx] / Cf[t - 15, idx] - 1
        v10 = Vf[t - 9:t + 1, idx].mean(0); v10p = Vf[t - 19:t - 9, idx].mean(0); p10 = Cf[t, idx] / Cf[t - 10, idx] - 1
        pr.append(((up[t - 14:t + 1, idx].mean(0) >= 12 / 15) & (v15 >= 1.2 * v15p) & (p15 >= 0.2)).mean())
        pr.append(((up[t - 9:t + 1, idx].mean(0) >= 0.7) & (v10 >= 1.2 * v10p) & (p10 >= 0.1)).mean())
    pr = np.array(pr).reshape(-1, 2)
    L.append(f"- 最近 36 個月底：原版通過率中位 {np.median(pr[:, 0]) * 100:.2f}%、台股版 {np.median(pr[:, 1]) * 100:.2f}%（母體每日約 {np.median(nstk):.0f} 檔）"); L.append("")
    # ZVR
    L.append("## 二、ZVR ＝ volume ÷ SMA30（含當日）× 100"); L.append("")
    sma30 = pd.DataFrame(np.where(T, V, np.nan)).rolling(30, min_periods=30).mean().to_numpy()
    zvr = np.where(T & (sma30 > 0), V / sma30 * 100, np.nan)
    okm = (cum_traded >= 260) & (amt20 >= LIQ) & T & (cal.to_numpy()[:, None] >= np.datetime64("2016-01-01"))
    z = zvr[okm]; z = z[np.isfinite(z)]
    def bands(x):
        return "、".join(f"{'<60' if lo == -np.inf else ('≥200' if hi == np.inf else f'{lo}–{hi}')} {((x >= lo) & (x < hi)).mean() * 100:.1f}%" for lo, hi in BANDS)
    L.append(f"- 全母體有效 K 棒 {len(z):,} 根：{bands(z)}；ZVR ≥ 150（詩魂攻擊量 1.5 倍）{(z >= 150).mean() * 100:.1f}%；中位 {np.median(z):.0f}")
    S11 = pd.read_csv(os.path.join(R11DIR, "signals.csv.gz"), dtype={"sid": str}, low_memory=False)
    S11 = S11[(S11["cell"] == "30|3|20") & (S11["liq"] >= LIQ)]
    col = {s: i for i, s in enumerate(sids)}
    zs = np.array([zvr[int(p), col[s]] for s, p in zip(S11["sid"], S11["pos"]) if s in col]); zs = zs[np.isfinite(zs)]
    L.append(f"- 研究十一 3/5 訊號根 {len(zs):,} 根（⚠ C3 條件本來就要求量 ×3 ⇒ 分佈偏高是機械的）：{bands(zs)}；≥ 150 {(zs >= 150).mean() * 100:.1f}%；中位 {np.median(zs):.0f}")
    L.append("")
    open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L))
    print(f"完成 {time.time() - t0:.0f}s → {RESULTS}/summary.md", file=sys.stderr)


if __name__ == "__main__":
    main()

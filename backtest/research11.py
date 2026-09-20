"""研究十一長版（妖股／飆股相似度計分，K線分析 2026-09-11 交辦七項）＋ 研究十二 創新高拆解 ＋ 第七項。判準 backtest/PREREG9.md。

    python3 -m backtest.research11 [--procs 4] [--stocks 2330 ...] [--reps 200] [--out DIR]

訊號在「有效 K 棒」序列上算（近 N 根 ＝ 近 N 個有成交日）。漲跌停用價格自算（PREREG9 一節），不用資料庫 `limit` 欄。
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import evaluate as E

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results11")
COST = E.COST
SPLIT = "2021-01-01"
HOLDS = [5, 10, 20, 60, 120]
CAP = 120
ATR_MIN_BARS = 114
GRID_C1 = [0.20, 0.30, 0.40]
GRID_C3 = [2.0, 3.0, 5.0]
GRID_DEDUP = [10, 20, 40]
MAIN_CELL = (0.30, 3.0, 20)
SLIPS = [0.0, 0.003, 0.005, 0.010]
_G: dict = {}


# ── 漲跌停價（未還原價） ──
def _tick(p: float) -> float:
    return 0.01 if p < 10 else 0.05 if p < 50 else 0.1 if p < 100 else 0.5 if p < 500 else 1.0 if p < 1000 else 5.0


def limit_price(ref: float, up: bool, lim: float) -> float:
    raw = ref * (1 + lim) if up else ref * (1 - lim)
    t = _tick(raw)
    return math.floor(raw / t + 1e-9) * t if up else math.ceil(raw / t - 1e-9) * t


def limit_flags(rc: np.ndarray, dates: pd.DatetimeIndex, skip: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """rc：未還原收盤（有效 K 棒序列）。skip：該根不判（還原事件日、上市前 5 根）。"""
    n = len(rc); up = np.zeros(n, bool); dn = np.zeros(n, bool)
    cut = pd.Timestamp("2015-06-01")
    for k in range(1, n):
        if skip[k] or np.isnan(rc[k]) or np.isnan(rc[k - 1]) or rc[k - 1] <= 0:
            continue
        lim = 0.07 if dates[k] < cut else 0.10
        up[k] = abs(rc[k] - limit_price(rc[k - 1], True, lim)) < 1e-6
        dn[k] = abs(rc[k] - limit_price(rc[k - 1], False, lim)) < 1e-6
    return up, dn


def wilder_atr(h, l, c, n=14):
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    atr = np.full(len(c), np.nan)
    if len(c) < n:
        return atr
    atr[n - 1] = tr[:n].mean()
    for i in range(n, len(c)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    atr[:ATR_MIN_BARS - 1] = np.nan   # 種子殘餘 < 0.1% 之後才可引用
    return atr


def _roll_max(x, w):
    return pd.Series(x).rolling(w, min_periods=w).max().to_numpy(float)


def _roll_mean(x, w):
    return pd.Series(x).rolling(w, min_periods=w).mean().to_numpy(float)


def _init(cal):
    _G["cal"] = cal


# ── 出場 ──
def fixed_exit(o, c, k, H, nb):
    """訊號根 k，進場 k+1 開盤，**持有 H 根**（進場那根算第 1 根）收盤出。回傳 (exit_bar, gross) 或 None。nb ＝ k−20 之後第一個壞根。

    ⭐ 出場根一律走 `data.exit_pos`（唯一實作，P4_v3 追加二十一）：exit_pos(k+1, H) ＝ k+H ⇒ 與舊寫法逐位元相同。"""
    e = D.exit_pos(k + 1, H)
    if e >= len(c) or e >= nb:
        return None
    return e, c[e] / o[k + 1] - 1


def cond_exit(o, c, k, nb, cond):
    """條件出場：從 k+1 起逐根看 cond(j)；成立 → j+1 開盤出（無則 j 收盤）；上限 k+CAP 收盤。"""
    n = len(c); last = min(n - 1, k + CAP)
    if last >= nb:
        return None
    ep = o[k + 1]
    for j in range(k + 1, last + 1):
        if cond(j):
            if j + 1 <= n - 1 and j + 1 < nb:
                return j + 1, o[j + 1] / ep - 1, True
            return j, c[j] / ep - 1, True
    return last, c[last] / ep - 1, False


def load_bars(sid, market, cal):
    """有效 K 棒序列與壞根視窗（研究十一／十三共用）。回傳 dict 或 None（< 260 根）。
    鍵：idx（日曆位置）、dates、o/c/h/l/amt（還原價）、rc（未還原收盤）、up/dn（漲跌停）、ev_bar、skip、next_bad、df。"""
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    traded = df["traded"].to_numpy()
    idx = np.flatnonzero(traded)
    if len(idx) < 260:
        return None
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")["close"]
    rc_full = pd.to_numeric(raw.reindex(cal), errors="coerce").to_numpy(float)
    c = df["close"].to_numpy()[idx]; o = df["open"].to_numpy()[idx]; h = df["high"].to_numpy()[idx]; l = df["low"].to_numpy()[idx]
    amt = df["amount"].to_numpy()[idx]; rc = rc_full[idx]
    dates = cal[idx]; n = len(idx)
    # 還原事件、幽靈事件、斷點、洞
    adj = D.load_adj(sid)
    ev_bar = np.zeros(n, bool); phantom = np.zeros(n, bool)
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= n:
                continue
            ev_bar[k] = True
            if k > 0 and not np.isnan(rc[k]) and not np.isnan(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    phantom[k] = True
    bad = phantom.copy()
    gap = np.diff(idx) - 1
    bad[1:] |= gap >= 5
    for b in D.breakpoints(df, st.event_dates):
        if D.applies(b):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < n:
                bad[k] = True
    # next_bad[k]：第一個 ≥ k 的壞根索引（無則 n+10）
    next_bad = np.full(n + 1, n + 10, int)
    for k in range(n - 1, -1, -1):
        next_bad[k] = k if bad[k] else next_bad[k + 1]
    skip = ev_bar.copy()
    if dates[0] > pd.Timestamp("2015-01-12"):
        skip[:5] = True
    up, dn = limit_flags(rc, dates, skip)
    return {"idx": idx, "dates": dates, "o": o, "c": c, "h": h, "l": l, "amt": amt, "rc": rc, "up": up, "dn": dn,
            "ev_bar": ev_bar, "skip": skip, "next_bad": next_bad, "df": df}


def stock_features(args):
    sid, market, first_seen = args
    B = load_bars(sid, market, _G["cal"])
    if B is None:
        return None
    idx, dates, o, c, h, l, amt, up, dn, skip, next_bad, df = (B[k] for k in ("idx", "dates", "o", "c", "h", "l", "amt", "up", "dn", "skip", "next_bad", "df"))
    n = len(idx)
    # 特徵
    ret20 =np.array(c / np.roll(c, 20) - 1, dtype=float); ret20[:20] = np.nan
    nup20 = pd.Series(up.astype(int)).rolling(20, min_periods=20).sum().to_numpy(float)
    amt_prev20 = np.array(_roll_mean(np.roll(amt, 1), 20), dtype=float); amt_prev20[:21] = np.nan
    amt_ratio = amt / amt_prev20
    ma5 = _roll_mean(c, 5); ma20 = _roll_mean(c, 20); ma60 = _roll_mean(c, 60); ma100 = _roll_mean(c, 100)
    hi = {w: _roll_max(c, w) for w in (60, 120, 250, 500)}
    pct = np.array(c / np.roll(c, 1) - 1, dtype=float); pct[0] = np.nan
    atr = wilder_atr(h, l, c)
    liq = amt_prev20
    amt_med60 = pd.Series(amt).shift(1).rolling(60, min_periods=60).median().to_numpy(float)
    amt_ratio60 = amt / amt_med60   # K線分析 09-09 裁定的挑選規則：訊號日成交金額 ÷ 前 60 根中位數（只記錄，不用來選）
    nb_sig = np.array([next_bad[max(0, k - 20)] for k in range(n)])
    eligible = (np.arange(n) >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(amt_ratio)
    eligible &= nb_sig > np.arange(n)   # 訊號根本身與前 20 根無壞根
    month = dates.strftime("%Y-%m")
    out = {"sid": sid, "main": [], "grid": [], "base": {}, "b12": [], "close": None}
    # 母體基準：所有合格根，各持有期
    for H in HOLDS:
        e = np.arange(n) + H
        ok = eligible & (e < n) & (np.arange(n) + 1 < n)
        ok[ok] &= e[ok] < nb_sig[ok]
        ks = np.flatnonzero(ok)
        if len(ks) == 0:
            continue
        g = c[ks + H] / o[ks + 1] - 1
        s = pd.DataFrame({"m": month[ks], "g": g}).groupby("m")["g"].agg(["sum", "count"])
        out["base"][H] = s
    # 27 格
    for c1 in GRID_C1:
        for c3 in GRID_C3:
            score = ((ret20 >= c1).astype(int) + (nup20 >= 3).astype(int) + (amt_ratio >= c3).astype(int)
                     + (c > ma100).astype(int) + (c >= hi[250]).astype(int))
            cand = np.flatnonzero(eligible & (score >= 3))
            for dd in GRID_DEDUP:
                last = -10 ** 9; picked = []
                for k in cand:
                    if k - last > dd:
                        picked.append(k); last = k
                is_main = (c1, c3, dd) == MAIN_CELL
                for k in picked:
                    if k + 1 >= n:
                        continue
                    row = {"cell": f"{int(c1 * 100)}|{int(c3)}|{dd}", "sid": sid, "k": int(k), "pos": int(idx[k]), "entry_pos": int(idx[k + 1]),
                           "month": month[k], "score": int(score[k]), "c1": bool(ret20[k] >= c1), "c2": bool(nup20[k] >= 3),
                           "c3": bool(amt_ratio[k] >= c3), "c4": bool(c[k] > ma100[k]), "c5": bool(c[k] >= hi[250][k]), "liq": float(liq[k]), "amt_ratio60": float(amt_ratio60[k])}
                    for H in (20, 60, 120):
                        r = fixed_exit(o, c, k, H, nb_sig[k]); row[f"g_H{H}"] = r[1] if r else np.nan
                    if not is_main:
                        out["grid"].append(row); continue
                    for H in (5, 10):
                        r = fixed_exit(o, c, k, H, nb_sig[k]); row[f"g_H{H}"] = r[1] if r else np.nan
                    for H in HOLDS:
                        r = fixed_exit(o, c, k, H, nb_sig[k]); row[f"x_H{H}"] = r[0] if r else -1
                    for name, kx in (("A2", 2.0), ("A3", 3.0)):
                        st_ = {"hi": -np.inf, "stop": -np.inf}
                        def cond(j, st_=st_, kx=kx):
                            if c[j] > st_["hi"]:
                                st_["hi"] = c[j]
                                if not np.isnan(atr[j]):
                                    st_["stop"] = max(st_["stop"], st_["hi"] - kx * atr[j])
                            return c[j] < st_["stop"]
                        r = cond_exit(o, c, k, nb_sig[k], cond) if not np.isnan(atr[k]) else None
                        row[f"g_{name}"], row[f"x_{name}"], row[f"t_{name}"] = (r[1], r[0], r[2]) if r else (np.nan, -1, False)
                    r = cond_exit(o, c, k, nb_sig[k], lambda j: (not np.isnan(ma5[j])) and c[j] < ma5[j])
                    row["g_M5"], row["x_M5"], row["t_M5"] = (r[1], r[0], r[2]) if r else (np.nan, -1, False)
                    r = cond_exit(o, c, k, nb_sig[k], lambda j: bool(dn[j]))
                    row["g_LD"], row["x_LD"], row["t_LD"] = (r[1], r[0], r[2]) if r else (np.nan, -1, False)
                    for nm in ["H5", "H10", "H20", "H60", "H120", "A2", "A3", "M5", "LD"]:
                        xb = row[f"x_{nm}"]; row[f"xpos_{nm}"] = int(idx[xb]) if xb >= 0 else -1; row[f"bars_{nm}"] = (xb - k) if xb >= 0 else np.nan
                    out["main"].append(row)
    # 研究十二 基準組 B
    B = eligible & (pct >= 0.07) & (c > ma60) & ~np.isnan(ma60) & ~np.isnan(ma20) & ~np.isnan(ma5)
    for k in np.flatnonzero(B):
        if k + 1 >= n:
            continue
        row = {"sid": sid, "k": int(k), "pos": int(idx[k]), "month": month[k], "liq": float(liq[k]),
               "bull": bool(c[k] > ma5[k] > ma20[k] > ma60[k]), "q": bool(amt_ratio[k] >= 2.0), "nq": bool(amt_ratio[k] < 1.0),
               "e": bool(ret20[k] < 0.15), "l": bool(ret20[k] >= 0.30)}
        for w in (60, 120, 250, 500):
            row[f"hi{w}"] = bool(c[k] >= hi[w][k]) if not np.isnan(hi[w][k]) else None
            row[f"dist{w}"] = float(c[k] / hi[w][k] - 1) if not np.isnan(hi[w][k]) else np.nan
        for H in (20, 60, 120):
            r = fixed_exit(o, c, k, H, nb_sig[k]); row[f"g_H{H}"] = r[1] if r else np.nan
        out["b12"].append(row)
    if out["main"]:
        out["close"] = pd.Series(df["close"].to_numpy()).ffill().to_numpy(np.float32)
        out["open"] = df["open"].to_numpy(np.float32)
    return out


# ── 統計 ──
def cl_stats(x: np.ndarray, m: np.ndarray, base: float = 0.0) -> dict:
    ok = ~np.isnan(x); x = x[ok]; m = m[ok]
    n = len(x)
    if n == 0:
        return {"n": 0}
    mean = float(x.mean()); d = x - mean
    s = pd.Series(d).groupby(m).sum().to_numpy()
    se = float(np.sqrt((s ** 2).sum()) / n)
    return {"n": n, "mean": mean, "median": float(np.median(x)), "win": float((x > 0).mean()), "worst": float(x.min()),
            "p10": float(np.percentile(x, 10)), "se": se, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se, "excess": mean - base,
            "months": int(len(s))}


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def main():
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--stocks", nargs="*"); ap.add_argument("--limit", type=int)
    ap.add_argument("--reps", type=int, default=200); ap.add_argument("--out", default=None)
    ap.add_argument("--report-only", action="store_true", help="只用既有 signals/grid/base12/baseline_months 重做報表（含組合層）")
    a = ap.parse_args()
    if a.out:
        RESULTS = a.out
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    if a.report_only:
        main_df = pd.read_csv(os.path.join(RESULTS, "signals.csv.gz"), dtype={"sid": str})
        grid_df = pd.read_csv(os.path.join(RESULTS, "grid.csv.gz"), dtype={"sid": str})
        b12 = pd.read_csv(os.path.join(RESULTS, "base12.csv.gz"), dtype={"sid": str})
        bm = pd.read_csv(os.path.join(RESULTS, "baseline_months.csv"), dtype={"month": str}).set_index(["hold", "month"])
        base = {H: bm.loc[H] for H in HOLDS}
        closes, opens = {}, {}
        mk = uni.set_index("stock_id")["market"]
        for sid in main_df["sid"].unique():
            st = D.load_stock(sid, mk.get(sid, "twse"), cal)
            closes[sid] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32); opens[sid] = st.df["open"].to_numpy(np.float32)
        report(main_df, grid_df, b12, base, closes, opens, cal, a.reps)
        print(f"報表完成 {time.time() - t0:.0f}s", file=sys.stderr); return
    if a.stocks:
        uni = uni[uni["stock_id"].isin(a.stocks)]
    if a.limit:
        uni = uni.head(a.limit)
    tasks = [(r.stock_id, r.market, r.first_seen) for r in uni.itertuples()]
    outs = []
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        for i, r in enumerate(pool.imap_unordered(stock_features, tasks, chunksize=8)):
            if r is not None:
                outs.append(r)
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{len(tasks)}  {time.time() - t0:.0f}s", file=sys.stderr)
    os.makedirs(RESULTS, exist_ok=True)
    main_df = pd.DataFrame([r for o in outs for r in o["main"]])
    grid_df = pd.DataFrame([r for o in outs for r in o["grid"]])
    b12 = pd.DataFrame([r for o in outs for r in o["b12"]])
    base = {}
    for H in HOLDS:
        parts = [o["base"][H] for o in outs if H in o["base"]]
        s = pd.concat(parts).groupby(level=0).sum()
        base[H] = s
    closes = {o["sid"]: o["close"] for o in outs if o["close"] is not None}
    opens = {o["sid"]: o["open"] for o in outs if o["close"] is not None}
    main_df.to_csv(os.path.join(RESULTS, "signals.csv.gz"), index=False)
    grid_df.to_csv(os.path.join(RESULTS, "grid.csv.gz"), index=False)
    b12.to_csv(os.path.join(RESULTS, "base12.csv.gz"), index=False)
    pd.concat({H: s for H, s in base.items()}, names=["hold", "month"]).to_csv(os.path.join(RESULTS, "baseline_months.csv"))
    np.savez_compressed(os.path.join(RESULTS, "closes.npz"), **{k: v for k, v in closes.items()})
    np.savez_compressed(os.path.join(RESULTS, "opens.npz"), **{k: v for k, v in opens.items()})
    print(f"訊號 {len(main_df):,}（主格）、格點列 {len(grid_df):,}、B 組 {len(b12):,}，{time.time() - t0:.0f}s", file=sys.stderr)
    report(main_df, grid_df, b12, base, closes, opens, cal, a.reps)
    print(f"完成 {time.time() - t0:.0f}s", file=sys.stderr)


def base_mean(base, H, months=None):
    s = base[H]
    if months is not None:
        s = s[s.index.isin(months)]
    return float(s["sum"].sum() / s["count"].sum()) - COST if s["count"].sum() else np.nan


def period_mask(month: pd.Series, per: str):
    return (month < "2021-01") if per == "A" else (month >= "2021-01") if per == "B" else pd.Series(True, index=month.index)


def rule_table(df, base, per, slip, L, title):
    m = period_mask(df["month"], per); d = df[m]
    months = set(d["month"])
    L.append(f"#### {title}（n＝{len(d):,}，滑價 {slip * 100:.1f}%）"); L.append("")
    L.append("| 規則 | n | 平均 | 中位 | 勝率 | 最壞單筆 | p10 | 持有根 | 月分群 95% CI | 基準 | 超額 | 超額 月配對 95% CI | 統計層 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|")
    for nm in ["H5", "H10", "H20", "H60", "H120", "A2", "A3", "M5", "LD"]:
        x = d[f"g_{nm}"].to_numpy(float) - COST - slip
        H = int(nm[1:]) if nm[0] == "H" else None
        b = base_mean(base, H, months) - slip if H else np.nan
        s = cl_stats(x, d["month"].to_numpy(), b if H else 0.0)
        if s["n"] == 0:
            L.append(f"| {nm} | 0 | | | | | | | | | | | |"); continue
        bars = d[f"bars_{nm}"].mean()
        exc = f"**{s['excess'] * 100:+.2f} pp**" if H else "—"
        if H:
            # 超額的月配對版：每筆減去「同月、同持有期」的母體基準（毛），再做月分群 CI（滑價兩邊同扣、抵銷）
            bm = (base[H]["sum"] / base[H]["count"])
            ex_i = d[f"g_{nm}"].to_numpy(float) - d["month"].map(bm).to_numpy(float)
            se_ = cl_stats(ex_i, d["month"].to_numpy())
            exci = f"{se_['lo'] * 100:+.2f} ~ {se_['hi'] * 100:+.2f} pp"
            verdict = "測不出" if se_["lo"] <= 0 <= se_["hi"] else ("測得出（＋）" if se_["mean"] > 0 else "測得出（−）")
        else:
            exci = "—"; verdict = "—（見配對表）"
        L.append(f"| {nm} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['worst'])} | {_p(s['p10'])} | {bars:.1f} | "
                 f"{_p(s['lo'])} ~ {_p(s['hi'])} | {_p(b) if H else '—'} | {exc} | {exci} | {verdict} |")
    L.append("")


def paired_table(df, per, L):
    m = period_mask(df["month"], per); d = df[m]
    L.append(f"#### 配對停損（{per}，同一筆訊號兩種出場）"); L.append("")
    L.append("| 配對 | n | 配對差 平均 | 月分群 95% CI | 判定 |"); L.append("|---|---:|---:|---|---|")
    for a_, b_ in (("A2", "H10"), ("A3", "H20"), ("M5", "H5"), ("LD", "H120")):
        x = (d[f"g_{a_}"] - d[f"g_{b_}"]).to_numpy(float)
        s = cl_stats(x, d["month"].to_numpy())
        if s["n"] == 0:
            continue
        v = "測不出" if s["lo"] <= 0 <= s["hi"] else ("測得出（停損較差）" if s["mean"] < 0 else "測得出（停損較好）")
        L.append(f"| {a_} − {b_} | {s['n']:,} | {s['mean'] * 100:+.2f} pp | {s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f} | {v} |")
    # LD 拆
    t = d["t_LD"].fillna(False).astype(bool); ok = d["g_LD"].notna() & d["g_H120"].notna()
    for lab, mm in (("真的跌停出場", t & ok), ("抱到 120 根上限", ~t & ok)):
        dd = d[mm]
        if len(dd) == 0:
            continue
        L.append(f"- LD {lab}：{len(dd):,} 筆（{len(dd) / max(1, ok.sum()) * 100:.1f}%），LD 平均 {_p(dd['g_LD'].mean() - COST)}、中位 {_p(dd['g_LD'].median() - COST)}；同一批 H120 {_p(dd['g_H120'].mean() - COST)}")
    L.append("")


_LOG_COLS = ("g_H20", "g_H60", "g_H120", "relvol", "month")


def simulate_mtm(sig: pd.DataFrame, rule: str, n_slots: int, rng, closes: dict, opens: dict, ncal: int, return_equity: bool = False,
                 d_max: int | None = None, pick: str | None = None, log: list | None = None, queue_days: int = 0,
                 cash_mode: str = "zero", bench=None, bench_cost: float = COST / 2, cap_fn=None, stop=None,
                 weak=None, weak_size: float = 0.5, report_maxw: bool = False):
    """N 個等權槽、逐日收盤市值權益（研究十一／十三／十五／P1 共用）。

    PREREGP1（2026-09-14）加的四個參數**預設值下行為與原版逐位元相同**（resultsp1/regress 逐種子驗）：
      d_max       同一天最多新增幾個部位（None ＝ 不限，原版）
      pick        候選多於可進場數時怎麼挑：None ＝ rng.permutation（原版）；欄名（例 "relvol"）＝ 依該欄遞減、NaN 排最後
      log         list ⇒ 逐筆記錄每個候選訊號的去向：in（進場，delay＝推遲天數）／a 槽滿／b 當日新增達 d／c 該 sid 已持有／b_expired
      queue_days  被 b 擋掉的訊號最多再等 Q 個交易日（每天重試；進場價＝實際進場日開盤、出場日不變、gross 重算）；0 ＝ 不排隊
    擋掉原因：候選數 > min(槽餘, d 餘) 時，多出來的標 a（槽餘 ≤ d 餘）或 b（否則）；cash 用盡視同 a。⚠ a 不排隊（原版：當天沒進就丟）。
    PREREGP3（2026-09-14）再加：
      cash_mode   "zero"（原版：閒置資金報酬 0）／"bench"（閒置資金持有 bench，進出 bench 各付一次 bench_cost 的單邊成本）
      bench       cash_mode="bench" 時必填：與 closes 同長度的還原收盤序列（ffill 過、全正）
      bench_cost  單邊成本（預設 COST/2＝來回成本的一半，⚠ 回測線定的：台股買 0.1425%、賣 0.4425% 不對稱，這裡取平均）
    bench 記帳：閒置資金以 bench 單位數持有，equity ＝ 單位數 × bench[t] ＋ 持股市值；進場要提 amt 現金 ⇒ 賣 amt/(1−c) 的 bench；
    出場拿回 P ⇒ 買 P×(1−c) 的 bench。cash_mode="zero" 時程式路徑與原版相同（回歸 R1 逐位元驗）。
    PREREGP2（2026-09-15）再加：
      cap_fn      None（原版路徑，逐位元相同）／callable(sid, t, holding_sids) → bool：類股集中度上限。候選依 order 逐一問，
                  不合格者標 log 原因 "cap"（⛔ 不排隊、不占 avail，名額讓給下一個候選）；holding_sids ＝ 當下持有 ＋ 今天已進的。
    PREREGP7（2026-09-20，策略線 0945）再加：
      stop        None（原版路徑，⛔ 逐位元相同）／("fix", X)／("trail", X)，X ＝ 正的小數（0.15 ＝ 15%）
                  ("fix",  X) 收盤 ≤ **進場價** × (1−X) ⇒ 當日收盤出場
                  ("trail",X) 收盤 ≤ **進場後最高收盤** × (1−X) ⇒ 當日收盤出場（最高收盤含進場日）
      ⭐ 時序（⛔ 沒有前視）：停損只看**已經收盤**的日子。第 t 天開盤前檢查到第 t−1 天收盤破線
        ⇒ 該部位在第 t 天被結清、槽位在第 t 天釋出（⭐ 與排程出場 exit_pos ≤ t 走**同一條路**），
        而**記帳用的是觸發日（t−1）的收盤**——⛔ 不是第 t 天的價。
      ⚠ 所以「出場後當天釋放槽位」在本引擎的意思是：觸發日收盤出場、**次一個交易日**那個槽位可以再進場
        （⛔ 本引擎的進場價是當日開盤，收盤之後不可能再用同一天的開盤進場）。
      ⇒ 多回報五個量（⛔ 給 PREREGP7 的必報用）：stop_exits／stop_rate／stop_days（觸發日的日曆位置 list）／
        stop_max_same_day（單日觸發家數最大值）／stop_cut_right_tail（被砍掉、原本排程出場會賺 > 50% 的筆數）。
    PREREGP9 2-C ⓑ（2026-09-20，策略線 seq=5 §2-C ＋ 回測線追加一）再加：
      weak        None（原版路徑，⛔ 逐位元相同）／長度 ncal 的布林序列：weak[t] ＝ 第 t 天是「弱勢」
                  ⇒ **當天進場的新部位**只買 weak_size 個 slot（登錄逐字：新部位只買 0.5 slot）
      weak_size   0 < x ≤ 1，預設 0.5
      report_maxw False（⛔ 回傳鍵與原版相同）／True ⇒ 多回 max_pos_frac＝逐日「單一部位市值 ÷ equity」的最大值
      ⭐ 省下的那半個 slot **留在現金**（⛔ 不讓給下一個候選、⛔ 不放大別的部位）⇒ 它的報酬照 cash_mode 走。
      ⛔ 只作用在【新部位】：已持有的部位不減、不賣、不調整（登錄 §2-C ⓑ 逐字）。
      ⚠ weak[t] 的**時序**由呼叫端負責（PREREGP9 用 t−1 的收盤與 MA60[t−1]）——⛔ 本引擎不自己算弱勢。
    PREREGP11（2026-09-20，策略線 seq=4 §八 ＋ 回測線追加一）：
      n_slots  除了純量，也可以是**長度 ncal 的整數序列**＝【逐日的槽位容量】（⭐ 逐月 N_t 用這個）
               ⇒ 第 t 天的容量 ＝ n_slots[t]；進場金額 slot ＝ equity[t−1] / n_slots[t]
               ⛔ 容量變小時【不強制出場】（只是不再進新的）⇒ len(open_pos) > 容量會出現
               ⛔ slot_use 的分母改成 Σ 容量（⛔ 不是 (end−first) × 某一個 N）
      ⛔ 傳純量時走的是原來那條路，逐位元相同。
    """
    caps = None                       # PREREGP11：逐日容量。⛔ None ＝ 純量 n_slots ⇒ 原版路徑逐位元相同
    if not isinstance(n_slots, (int, np.integer)):
        caps = np.asarray(n_slots, int)
        if caps.shape != (ncal,):
            raise ValueError(f"逐日容量要是長度 {ncal} 的整數序列，收到 {caps.shape}")
        if (caps < 1).any():
            raise ValueError("逐日容量每一天都要 ≥ 1（登錄 §八：N_t 下限 1 檔）")
    use_bench = cash_mode == "bench"
    if use_bench:
        if bench is None:
            raise ValueError("cash_mode='bench' 需要 bench 序列")
        bench = np.asarray(bench, float)
        if not np.all(np.isfinite(bench)) or not np.all(bench > 0):
            raise ValueError("bench 序列要 ffill 過且全正")
    cols = ["sid", "entry_pos", f"xpos_{rule}", f"g_{rule}"]
    extra = [c for c in _LOG_COLS if c in sig.columns and c not in cols]
    d = sig[cols + extra].dropna(subset=cols)
    d = d[d[f"xpos_{rule}"] >= 0].rename(columns={f"xpos_{rule}": "exit_pos", f"g_{rule}": "gross"})
    by_entry = {k: g for k, g in d.groupby("entry_pos")}
    first, last = int(d["entry_pos"].min()), int(d["exit_pos"].max())
    equity = np.ones(ncal); cash = 1.0; open_pos = []; held = set(); trades = 0; used = 0
    hold_val = np.zeros(ncal) if return_equity else None
    units = (1.0 / bench[max(first - 1, 0)]) if use_bench else 0.0      # bench 模式：閒置資金以 bench 單位數持有
    wins = 0; pending = []; n_deferred = 0; delays = []; n_expired = 0
    inf = float("inf")
    # PREREGP7：停損。⛔ stop is None 時下面每一段都跳過 ⇒ 原版路徑逐位元相同。
    stop_kind, stop_x = (stop if stop is not None else (None, None))
    if stop is not None and (stop_kind not in ("fix", "trail") or not (0 < stop_x < 1)):
        raise ValueError(f"stop 只能是 ('fix'|'trail', 0<X<1)，收到 {stop!r}")
    # PREREGP9 2-C ⓑ：弱勢日的新部位只買 weak_size 個 slot。⛔ weak is None 時下面每一段都跳過 ⇒ 原版路徑逐位元相同。
    if weak is not None:
        weak = np.asarray(weak, bool)
        if weak.shape != (ncal,):
            raise ValueError(f"weak 要是長度 {ncal} 的布林序列，收到 {weak.shape}")
        if not (0 < weak_size <= 1):
            raise ValueError(f"weak_size 要在 (0, 1]，收到 {weak_size!r}")
    max_pos_frac = 0.0
    peak_close = {}                 # sid → 進場後最高收盤（trail 用）
    stop_exits = 0; stop_days = []; stop_cut_right_tail = 0; hold_days = []; entry_day = {}

    def _rec(row, reason, t, delay=0, gross=np.nan):
        if log is not None:
            rec = {"t": t, "sid": row["sid"], "entry_pos": int(row["entry_pos"]), "exit_pos": int(row["exit_pos"]), "reason": reason, "delay": delay, "gross": gross,
                   **{c: row[c] for c in extra}}
            if f"g_{rule}" not in rec:
                rec[f"g_{rule}"] = float(row["gross"])      # 主格出場的原始逐筆報酬（rule 那一欄被改名成 gross，這裡補回原名）
            log.append(rec)

    for t in range(first, min(ncal, last + 2)):
        if stop is not None and open_pos and t > first:
            # ⭐ 只看 t−1（已經收盤的那一天）⇒ ⛔ 沒有前視；破線的部位改成「今天結清、記 t−1 的收盤」
            hit = []
            for k, (ex, sid, amt, gross, ep) in enumerate(open_pos):
                if ex <= t:
                    continue                                  # 排程出場本來就在今天結清，⛔ 不搶它
                c = float(closes[sid][t - 1])
                if not np.isfinite(c):
                    continue
                level = ep * (1 - stop_x) if stop_kind == "fix" else peak_close.get(sid, ep) * (1 - stop_x)
                if c <= level:
                    if gross > 0.50:
                        stop_cut_right_tail += 1              # 原本排程出場會賺 > 50%，被停損砍掉
                    open_pos[k] = (t, sid, amt, c / ep - 1.0, ep)
                    hit.append(sid)
            if hit:
                stop_exits += len(hit); stop_days.append((t - 1, len(hit)))
        still = []
        for ex, sid, amt, gross, ep in open_pos:
            if ex <= t:
                if use_bench:
                    units += amt * (1 + gross - COST) * (1 - bench_cost) / bench[t]   # 拿回的錢買 bench，付單邊成本
                else:
                    cash += amt * (1 + gross - COST)
                held.discard(sid)
                if stop is not None:
                    peak_close.pop(sid, None)
                    e0 = entry_day.pop(sid, None)
                    if e0 is not None:
                        hold_days.append(t - e0)           # 實際持有天數（⛔ 停損出場的會短於排程的 H）
            else:
                still.append((ex, sid, amt, gross, ep))
        open_pos = still
        g = by_entry.get(t)
        if queue_days and pending:                       # 隊列裡的訊號今天再試一次；過期或出場日已到 ⇒ b_expired
            keep = []; q_rows = []
            for row, t0 in pending:
                if t - t0 > queue_days or int(row["exit_pos"]) <= t:
                    n_expired += 1; _rec(row, "b_expired", t, t - t0); continue
                keep.append((row, t0)); q_rows.append({**row, "_t0": t0})
            pending = keep
            if q_rows:
                q = pd.DataFrame(q_rows)
                g = q if g is None else pd.concat([g.assign(_t0=t), q], ignore_index=True)
        elif log is not None and g is not None:
            g = g.assign(_t0=t)
        ns_t = n_slots if caps is None else int(caps[t])
        if g is not None and len(open_pos) < ns_t:
            if log is not None and held:
                for _, row in g[g["sid"].isin(held)].iterrows():
                    if "_t0" not in row or int(row["_t0"]) == t:      # 隊列裡的等待中不記；新訊號撞持倉才記 c
                        _rec(row, "c", t)
            cand = g[~g["sid"].isin(held)]
            if len(cand):
                slots_free = ns_t - len(open_pos)
                d_free = inf if d_max is None else d_max
                avail = int(min(slots_free, d_free))
                if pick is None:
                    order = rng.permutation(len(cand))
                else:
                    key = cand[pick].to_numpy(float); key = np.where(np.isnan(key), -inf, key)
                    order = np.argsort(-key, kind="stable")
                if cap_fn is None:
                    take = order[:avail]; rest = list(order[avail:])
                else:                                            # PREREGP2：逐一問 cap_fn，不合格者記 "cap"、名額往後讓
                    take = []; rest = []; hold_now = set(held)
                    for i in order:
                        if len(take) >= avail:
                            rest.append(i); continue
                        sid_i = cand.iloc[i]["sid"]
                        if cap_fn(sid_i, t, hold_now):
                            take.append(i); hold_now.add(sid_i)
                        else:
                            _rec(cand.iloc[i], "cap", t)
                    take = np.asarray(take, dtype=int)
                slot = equity[t - 1] / ns_t
                if weak is not None and weak[t]:
                    slot = slot * weak_size          # ⭐ 只縮**今天要進的新部位**；省下的留在現金
                entered_q = set()
                for j, i in enumerate(take):
                    if use_bench:
                        cash = units * bench[t] * (1 - bench_cost)                   # 賣 bench 能提出的現金（扣單邊成本）
                    row = cand.iloc[i]; amt = min(slot, cash)
                    if amt <= 1e-9:
                        rest = list(take[j:]) + rest; break
                    if use_bench:
                        units -= amt / ((1 - bench_cost) * bench[t])
                    else:
                        cash -= amt
                    ep = float(opens[row["sid"]][t])   # 進場價 ＝ 進場日開盤（還原價）；市值 ＝ 收盤 ÷ 進場開盤
                    if not np.isfinite(ep) or ep <= 0:
                        ep = float(closes[row["sid"]][t])
                    t0 = int(row["_t0"]) if "_t0" in row else t
                    gross = float(row["gross"]) if t0 == t else float(closes[row["sid"]][int(row["exit_pos"])]) / ep - 1.0   # 推遲進場 ⇒ 重算
                    open_pos.append((int(row["exit_pos"]), row["sid"], amt, gross, ep)); held.add(row["sid"]); trades += 1
                    if stop is not None:
                        entry_day[row["sid"]] = t
                    wins += int(gross - COST > 0)
                    if t0 != t:
                        n_deferred += 1; delays.append(t - t0); entered_q.add((row["sid"], int(row["entry_pos"])))
                    _rec(row, "in", t, t - t0, gross)
                if entered_q:
                    pending = [(r, t0) for r, t0 in pending if (r["sid"], int(r["entry_pos"])) not in entered_q]
                if rest and (log is not None or queue_days):
                    reason = "a" if slots_free <= d_free else "b"
                    for i in rest:
                        row = cand.iloc[i]
                        if "_t0" in row and int(row["_t0"]) != t:
                            continue                                    # 已在隊列裡，繼續等
                        if reason == "b" and queue_days:
                            pending.append((row, t))                    # 等下一天；結果到時再記
                        else:
                            _rec(row, reason, t)
        used += len(open_pos)
        if use_bench:
            cash = units * bench[t]
        if stop is not None:
            for _, sid, _, _, ep in open_pos:                 # 收盤後更新最高收盤（trail 的參考點，含進場日）
                c = float(closes[sid][t])
                if np.isfinite(c):
                    peak_close[sid] = max(peak_close.get(sid, ep), c)
        hv = sum(amt * float(closes[sid][t]) / ep for _, sid, amt, _, ep in open_pos)
        equity[t] = cash + hv
        if report_maxw and open_pos and equity[t] > 0:   # ⭐ 必報③：單一部位最大佔比（⛔ 唯讀，不動數值路徑）
            max_pos_frac = max(max_pos_frac, max(amt * float(closes[sid][t]) / ep for _, sid, amt, _, ep in open_pos) / equity[t])
        if return_equity:
            hold_val[t] = hv          # PREREGP3 丙（時點隨機對照）要的逐日持股市值；⛔ 只在 return_equity 時記，數值路徑不變
    equity[:first] = 1.0; end = min(ncal, last + 2); equity[end:] = equity[end - 1]
    years = (end - first) / 245; final = equity[end - 1]
    peak = np.maximum.accumulate(equity); mdd = float(((equity - peak) / peak).min())
    cap_sum = (end - first) * n_slots if caps is None else int(caps[first:end].sum())
    out = {"cagr": final ** (1 / years) - 1, "mdd": mdd, "trades": trades, "slot_use": used / cap_sum, "first": first, "end": end,
           "m": trades, "pos_frac": wins / trades if trades else np.nan, "deferred": n_deferred, "delay_med": float(np.median(delays)) if delays else np.nan, "expired": n_expired}
    if stop is not None:            # PREREGP7 必報（⛔ stop is None 時這幾個鍵不存在 ⇒ 原版回傳逐位元相同）
        out["stop_exits"] = stop_exits
        out["stop_rate"] = stop_exits / trades if trades else np.nan
        out["stop_days"] = stop_days
        out["stop_max_same_day"] = max((n for _, n in stop_days), default=0)
        out["stop_cut_right_tail"] = stop_cut_right_tail
        out["hold_days_mean"] = float(np.mean(hold_days)) if hold_days else np.nan
    if report_maxw:                 # PREREGP9 §2-E③（⛔ report_maxw=False 時這個鍵不存在 ⇒ 原版回傳逐位元相同）
        out["max_pos_frac"] = max_pos_frac
    if return_equity:
        out["equity"] = equity; out["hold_val"] = hold_val
    return out


def report(main_df, grid_df, b12, base, closes, opens, cal, reps):
    L = ["# 研究十一長版 ＋ 研究十二 創新高拆解 ＋ 第七項——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG9.md`。主格 (C1 30%, C3 ×3, 去重 20)。", ""]
    md = main_df
    L.append(f"母體：{md['sid'].nunique():,} 檔有訊號；主格 score ≥ 3 訊號 **{len(md):,}** 筆（4/5 {int((md['score'] >= 4).sum()):,}、5/5 {int((md['score'] >= 5).sum()):,}，都是 ≥3 去重後的子集）。基準（無閘門、所有合格股票日）：" +
             "、".join(f"H{H} {_p(base_mean(base, H))}" for H in HOLDS)); L.append("")
    n_noc2 = int(((md["score"] - md["c2"].astype(int)) >= 3).sum())
    L.append(f"⚠ 與 K線分析短版（3/5 ＝ 9,066 筆）的對帳：短版的 C2 用資料庫 `limit` 欄（對真漲停召回約 10%），等於 C2 幾乎不給分；本版 C2 用價格自算。本版訊號裡「不靠 C2 也 ≥ 3 分」的有 **{n_noc2:,}** 筆，C2 成立的 {int(md['c2'].sum()):,} 筆（{md['c2'].mean() * 100:.0f}%）。差距的其餘來源：母體（2,130 vs 1,886 檔）、公司行動排除法（本版：斷點＋洞＋幽靈事件；短版：四條件代理）。")
    L.append("")
    L.append("## 一、主表：3/5 層 × 八條出場（全期、A 段 2015–2020、B 段 2021–2026）"); L.append("")
    for per, lab in (("ALL", "全期"), ("A", "A 段 2015–2020"), ("B", "B 段 2021–2026")):
        rule_table(md, base, per, 0.0, L, lab)
    L.append("### 4/5 層（子集）"); L.append("")
    rule_table(md[md["score"] >= 4], base, "ALL", 0.0, L, "4/5 全期")
    L.append("### 5/5 層（子集；⛔ 樣本不足，只報不下結論）"); L.append("")
    rule_table(md[md["score"] >= 5], base, "ALL", 0.0, L, "5/5 全期")
    L.append("### ⭐ 量當變數：C3 成立 vs 不成立（3/5 層）"); L.append("")
    L.append("| 組 | n | H20 平均／中位 | H60 平均／中位 | H120 平均／中位 | H120 破產率（≤ −50%） |"); L.append("|---|---:|---|---|---|---:|")
    for lab, mm in (("C3 成立（額 ≥ 3×）", md["c3"]), ("C3 不成立", ~md["c3"])):
        d = md[mm]
        L.append(f"| {lab} | {len(d):,} | " + " | ".join(f"{_p(d[f'g_H{H}'].mean() - COST)}／{_p(d[f'g_H{H}'].median() - COST)}" for H in (20, 60, 120)) +
                 f" | {((d['g_H120'] - COST) <= -0.5).mean() * 100:.1f}% |")
    x = (md.loc[md["c3"], "g_H120"].mean() - md.loc[~md["c3"], "g_H120"].mean())
    L.append(f"- C3 成立 − 不成立（H120）：{x * 100:+.2f} pp"); L.append("")
    L.append("### 流動性當變數（3/5 層，近 20 根成交金額均值）"); L.append("")
    L.append("| 門檻 | n | H20 | H60 | H120 | H120 中位 |"); L.append("|---|---:|---:|---:|---:|---:|")
    for lab, th in (("不設", 0), ("≥ 1,000 萬", 1e7), ("≥ 2,000 萬", 2e7), ("≥ 5,000 萬", 5e7)):
        d = md[md["liq"] >= th]
        L.append(f"| {lab} | {len(d):,} | " + " | ".join(_p(d[f'g_H{H}'].mean() - COST) for H in (20, 60, 120)) + f" | {_p(d['g_H120'].median() - COST)} |")
    L.append("")
    # ② 滑價
    L.append("## 二、滑價敏感度（3/5 層，全期；超額對同滑價的基準）"); L.append("")
    L.append("| 滑價 | H20 超額 | H60 超額 | H120 超額 | LD 平均 |"); L.append("|---|---:|---:|---:|---:|")
    ex120 = {}
    for sl in SLIPS:
        row = []
        for H in (20, 60, 120):
            e = (md[f"g_H{H}"].mean() - COST - sl) - (base_mean(base, H, set(md["month"])) - sl); row.append(e)
            if H == 120: ex120[sl] = e
        L.append(f"| {sl * 100:.1f}% | " + " | ".join(f"{e * 100:+.2f} pp" for e in row) + f" | {_p(md['g_LD'].mean() - COST - sl)} |")
    L.append("- ⚠ 滑價對超額的影響：同一筆滑價基準也扣，所以固定持有的超額**不隨滑價變**（兩邊同時扣）；會變的是**絕對報酬**與「扣完剩多少」。H120 平均扣完：" +
             "、".join(f"{sl * 100:.1f}% → {_p(md['g_H120'].mean() - COST - sl)}" for sl in SLIPS))
    for H in (20, 60, 120):
        e0 = md[f"g_H{H}"].mean() - COST - base_mean(base, H, set(md["month"]))
        L.append(f"- 若基準視為「不交易的替代」（基準不扣滑價）：H{H} 超額 {e0 * 100:+.2f} pp，**來回滑價達 {e0 * 100:.2f}% 時歸零**；0.3／0.5／1.0% 時剩 " + "、".join(f"{(e0 - sl) * 100:+.2f} pp" for sl in SLIPS[1:]))
    L.append("- 換手快的規則吃滑價多：H5 平均 " + "、".join(f"{sl * 100:.1f}% → {_p(md['g_H5'].mean() - COST - sl)}" for sl in SLIPS)); L.append("")
    # ③ 配對
    L.append("## 三、配對停損（同一筆訊號、兩種出場）"); L.append("")
    for per in ("ALL", "A", "B"):
        paired_table(md, per, L)
    # ⑤ 27 格
    L.append("## 四、27 格子門檻掃描（score ≥ 3；全報不挑）"); L.append("")
    allg = pd.concat([grid_df, md[grid_df.columns.intersection(md.columns)]], ignore_index=True)
    L.append("| C1 | C3 | 去重 | n | H20 超額 | H60 超額 | H120 超額 | H120 中位 | A 段 H120 超額 | B 段 H120 超額 |"); L.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    cellA = {}
    for cell, d in allg.groupby("cell"):
        c1, c3, dd = cell.split("|")
        row = [c1 + "%", "×" + c3, dd, f"{len(d):,}"]
        for H in (20, 60, 120):
            row.append(f"{(d[f'g_H{H}'].mean() - COST - base_mean(base, H, set(d['month']))) * 100:+.2f} pp")
        row.append(_p(d["g_H120"].median() - COST))
        for per in ("A", "B"):
            dd_ = d[period_mask(d["month"], per)]
            e = (dd_["g_H120"].mean() - COST - base_mean(base, 120, set(dd_["month"]))) if len(dd_) else np.nan
            row.append(f"{e * 100:+.2f} pp" if not np.isnan(e) else "—")
            if per == "A": cellA[cell] = e
        L.append("| " + " | ".join(row) + " |")
    best = max(cellA, key=lambda k: cellA[k] if not np.isnan(cellA[k]) else -9)
    dB = allg[(allg["cell"] == best) & period_mask(allg["month"], "B")]
    eB = dB["g_H120"].mean() - COST - base_mean(base, 120, set(dB["month"]))
    L.append(f"\n- **樣本外驗證（事前寫死的選法）**：A 段 H120 超額最高的一格是 ({best})，A 段 {cellA[best] * 100:+.2f} pp → B 段 **{eB * 100:+.2f} pp**（n {len(dB):,}）。主格 (30|3|20) 的 A／B 見上表。"); L.append("")
    # ⑥ 創新高
    L.append("## 五、研究十二 創新高拆解（基準組 B ＝ 當日漲幅 ≥ 7% 且收盤 > MA60，量不當前提）"); L.append("")
    L.append(f"B 組 {len(b12):,} 筆（不去重）。"); L.append("")
    b = b12
    L.append("### (c) 重疊率"); L.append("")
    both = (b["hi120"] == True) & (b["hi250"] == True)
    L.append(f"- B 內 P120（創 120 根新高）{int((b['hi120'] == True).sum()):,} 筆、P250 {int((b['hi250'] == True).sum()):,} 筆；同時 {int(both.sum()):,} 筆 ⇒ **|P120∧P250| ÷ |P120| = {both.sum() / max(1, (b['hi120'] == True).sum()) * 100:.1f}%、÷ |P250| = {both.sum() / max(1, (b['hi250'] == True).sum()) * 100:.1f}%**。")
    key12 = set(zip(b.loc[b["hi120"] == True, "sid"], b.loc[b["hi120"] == True, "pos"]))
    c5 = md[md["c5"]]
    ov = sum((s, p) in key12 for s, p in zip(c5["sid"], c5["pos"]))
    L.append(f"- 研究十一 3/5 訊號中 C5 成立 {len(c5):,} 筆，其中同一天也是 B 組 P120 的 {ov:,} 筆（{ov / max(1, len(c5)) * 100:.1f}%）；反向：B 組 P120 {len(key12):,} 筆裡是研究十一 3/5 訊號日的 {sum((s, p) in set(zip(md['sid'], md['pos'])) for s, p in key12):,} 筆。"); L.append("")
    L.append("### (a) 回看窗：創 N 根新高 vs 未創（B 內）"); L.append("")
    L.append("| N | 期間 | 創新高 n | 未創 n | H20 差 | H60 差 | H120 差 | H120 月分群 CI |"); L.append("|---:|---|---:|---:|---:|---:|---:|---|")
    for w in (60, 120, 250, 500):
        for per in ("ALL", "A", "B"):
            d = b[period_mask(b["month"], per) & b[f"hi{w}"].notna()]
            y, nn = d[d[f"hi{w}"] == True], d[d[f"hi{w}"] == False]
            if len(y) == 0 or len(nn) == 0:
                continue
            diffs = []
            for H in (20, 60, 120):
                diffs.append(y[f"g_H{H}"].mean() - nn[f"g_H{H}"].mean())
            # CI：兩組均值差的月分群 SE（各自算後合併）
            s1 = cl_stats(y["g_H120"].to_numpy(float), y["month"].to_numpy()); s2 = cl_stats(nn["g_H120"].to_numpy(float), nn["month"].to_numpy())
            se = math.sqrt(s1.get("se", 0) ** 2 + s2.get("se", 0) ** 2); dfd = diffs[2]
            L.append(f"| {w} | {per} | {len(y):,} | {len(nn):,} | " + " | ".join(f"{x * 100:+.2f} pp" for x in diffs) + f" | {(dfd - 1.96 * se) * 100:+.2f} ~ {(dfd + 1.96 * se) * 100:+.2f} |")
    L.append("")
    L.append("### (b) 連續版：收盤 ÷ 近 N 根最高收盤 − 1 的十等分（B 內，全期；D10 ＝ 最接近新高）"); L.append("")
    for w in (120, 250):
        d = b[b[f"dist{w}"].notna()].copy()
        d["dec"] = pd.qcut(d[f"dist{w}"].rank(method="first"), 10, labels=False) + 1
        L.append(f"N＝{w}：")
        L.append("| 十等分 | n | 距離中位 | H20 平均 | H60 平均 | H120 平均 | H120 中位 |"); L.append("|---:|---:|---:|---:|---:|---:|---:|")
        for dec, g in d.groupby("dec"):
            L.append(f"| D{dec} | {len(g):,} | {g[f'dist{w}'].median() * 100:+.1f}% | " + " | ".join(_p(g[f"g_H{H}"].mean() - COST) for H in (20, 60, 120)) + f" | {_p(g['g_H120'].median() - COST)} |")
        L.append("")
    # ⑦
    L.append("## 六、第七項：多頭排列（收盤 > MA5 > MA20 > MA60）持有期相依（B 內）"); L.append("")
    L.append("| 期間 | 有 n | 無 n | H20 差 | CI | H60 差 | CI | H120 差 | CI |"); L.append("|---|---:|---:|---:|---|---:|---|---:|---|")
    for per in ("ALL", "A", "B"):
        d = b[period_mask(b["month"], per)]; y, nn = d[d["bull"]], d[~d["bull"]]
        row = [per, f"{len(y):,}", f"{len(nn):,}"]
        for H in (20, 60, 120):
            s1 = cl_stats(y[f"g_H{H}"].to_numpy(float), y["month"].to_numpy()); s2 = cl_stats(nn[f"g_H{H}"].to_numpy(float), nn["month"].to_numpy())
            dd_ = s1["mean"] - s2["mean"]; se = math.sqrt(s1["se"] ** 2 + s2["se"] ** 2)
            row += [f"{dd_ * 100:+.2f} pp", f"{(dd_ - 1.96 * se) * 100:+.2f}~{(dd_ + 1.96 * se) * 100:+.2f}"]
        L.append("| " + " | ".join(row) + " |")
    L.append("- 量當變數（B 內、H120）：價量齊揚 Q（額 ≥ 2×）vs 量縮 N（額 < 1×）：" +
             f"Q n {int(b['q'].sum()):,} 平均 {_p(b.loc[b['q'], 'g_H120'].mean() - COST)} 中位 {_p(b.loc[b['q'], 'g_H120'].median() - COST)}；N n {int(b['nq'].sum()):,} 平均 {_p(b.loc[b['nq'], 'g_H120'].mean() - COST)} 中位 {_p(b.loc[b['nq'], 'g_H120'].median() - COST)}")
    L.append("- 早鳥 E（近 20 根 < 15%）vs 追高 L（≥ 30%）（B 內、H20／H60／H120 平均）：" +
             "；".join(f"H{H} E {_p(b.loc[b['e'], f'g_H{H}'].mean() - COST)} / L {_p(b.loc[b['l'], f'g_H{H}'].mean() - COST)}" for H in (20, 60, 120)) +
             f"（E n {int(b['e'].sum()):,}、L n {int(b['l'].sum()):,}）"); L.append("")
    # ④ 組合層
    L.append(f"## 七、組合層（3/5 層；N 個等權槽、隨機補位、{reps} 種子；逐日收盤市值權益）"); L.append("")
    L.append("| N | 規則 | 年化 中位 | 年化 p10～p90 | 最大回落 中位 | 最大回落 p10～p90 | 槽位使用率 | 交易筆數 |"); L.append("|---:|---|---:|---|---:|---|---:|---:|")
    ncal = len(cal)
    for n_slots in (5, 10, 20):
        for rule in ("H20", "H60", "H120", "LD"):
            st = pd.DataFrame([simulate_mtm(md, rule, n_slots, np.random.default_rng(3000 + r), closes, opens, ncal) for r in range(reps)])
            L.append(f"| {n_slots} | {rule} | **{st['cagr'].median() * 100:+.1f}%** | {np.percentile(st['cagr'], 10) * 100:+.1f}% ~ {np.percentile(st['cagr'], 90) * 100:+.1f}% | "
                     f"{st['mdd'].median() * 100:.1f}% | {np.percentile(st['mdd'], 10) * 100:.1f}% ~ {np.percentile(st['mdd'], 90) * 100:.1f}% | {st['slot_use'].median() * 100:.0f}% | {st['trades'].median():.0f} |")
    L.append("")
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

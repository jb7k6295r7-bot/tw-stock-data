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

TRANCHE_GAP = 20                    # PREREGP9 seq8 §二 2-A：第 2..k 份「之後每 20 個交易日各買一份」（⛔ 登錄寫死，⛔ 不掃）


def regime_below(bench_close, n: int) -> np.ndarray:
    """PREREGP9 seq8 §一「大盤狀態」：below[i] ＝ 0050 還原收盤[i] < MA_n[i]（MA 含第 i 天，共 n 根）。

    ⭐ 這是【第 i 天收盤之後】才知道的狀態 ⇒ simulate_mtm 在第 t 天開盤只讀 below[t−1]（引擎自己平移，⛔ 呼叫端不要先平移）。
    暖身不足（前 n−1 天）或收盤非有限 ⇒ False。與 researchp9.weak_flags 同一個算式：weak_flags(b)[t] ＝ regime_below(b, 60)[t−1]。
    """
    b = np.asarray(bench_close, float)
    if int(n) != n or n < 1:
        raise ValueError(f"MA 天數要是正整數，收到 {n!r}")
    ma = pd.Series(b).rolling(int(n)).mean().to_numpy()
    return np.isfinite(ma) & (b < ma)


def simulate_mtm(sig: pd.DataFrame, rule: str, n_slots: int, rng, closes: dict, opens: dict, ncal: int, return_equity: bool = False,
                 d_max: int | None = None, pick: str | None = None, log: list | None = None, queue_days: int = 0,
                 cash_mode: str = "zero", bench=None, bench_cost: float = COST / 2, cap_fn=None, stop=None,
                 weak=None, weak_size: float = 0.5, report_maxw: bool = False, maxw_detail: bool = False,
                 weight_fn=None, tradable=None, audit=None, delist=None, stop_line=None,
                 entry_tranches=None, add_rule=None, trim_rule=None, size_mult_by_regime=None, regime_trim=None,
                 trim_proceeds=None, nx_cap=None, stop_line_le=False, stop_proceeds=None, stop_block=None,
                 nx_order="before"):
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
      maxw_detail 需要 report_maxw；True ⇒ 再多回 maxw_daily（逐日那個最大值的序列）與 maxw_sid（每天是哪一檔）
                  ⇒ ⭐ 給【分佈】用（〈九十二〉：一個百分比要連同它的分佈一起報），⛔ 只有最大值看不出常態
      ⭐ 省下的那半個 slot **留在現金**（⛔ 不讓給下一個候選、⛔ 不放大別的部位）⇒ 它的報酬照 cash_mode 走。
      ⛔ 只作用在【新部位】：已持有的部位不減、不賣、不調整（登錄 §2-C ⓑ 逐字）。
      ⚠ weak[t] 的**時序**由呼叫端負責（PREREGP9 用 t−1 的收盤與 MA60[t−1]）——⛔ 本引擎不自己算弱勢。
    PREREGP13（2026-09-20，策略線 seq=3 §二 逐字規格）再加：
      weight_fn   None（原版路徑，⛔ 逐位元相同）／callable(batch, t, equity, cash) → list[目標金額]
                  batch ＝ 當天【通過 order、通過 cap_fn、尚未持有、要一起進場】的候選列（⭐ 保序）
                  回傳 ＝ 與 batch 等長的【目標金額】（⛔ 不是權重比例；單位與 equity 相同）
      ⭐ 逐檔金額改由呼叫端決定 ⇒ 這是引擎第一次有「同一天每檔金額可以不同」這個概念。
      ⛔ 現金不足怎麼辦【由 weight_fn 自己決定】（它收得到 cash）⇒ 引擎只做最後一道保險 min(target, cash)。
      ⚠ target ≤ 1e-9 ⇒ 該檔【不進場】並記 log 原因 "nocap"，⭐ 然後**繼續**問下一檔
        （⛔ 與原版路徑的 `break` 不同：原版的 amt ≤ 1e-9 只可能是現金用盡 ⇒ 後面都不必問了；
          而 weight_fn 那條路的 0 可能是「這一檔沒有市值資料」⇒ ⛔ 不可以連累後面的候選）
      ⛔⛔ 護欄（策略線 seq=3 §五 逐字，⭐ 與能力同一份落地）：
        「往後任何使用 weight_fn 的登錄，都要在跑之前寫死權重函數的逐字定義。
          ⛔ 不可以掃一組權重、⛔ 不可以事後在幾個權重函數之間挑。」
    PREREGP11（2026-09-20，策略線 seq=4 §八 ＋ 回測線追加一）：
      n_slots  除了純量，也可以是**長度 ncal 的整數序列**＝【逐日的槽位容量】（⭐ 逐月 N_t 用這個）
               ⇒ 第 t 天的容量 ＝ n_slots[t]；進場金額 slot ＝ equity[t−1] / n_slots[t]
               ⛔ 容量變小時【不強制出場】（只是不再進新的）⇒ len(open_pos) > 容量會出現
               ⛔ slot_use 的分母改成 Σ 容量（⛔ 不是 (end−first) × 某一個 N）
      ⛔ 傳純量時走的是原來那條路，逐位元相同。

    PREREGP9 seq8 §六（2026-09-25，台股策略線登錄 sha 373e1906b9dd52ed；回測線落地）再加五個參數，⛔ 全部預設關閉：
      ⭐ 全部是 None（entry_tranches 另外 1 也算關閉）⇒ 下面每一段都跳過 ⇒ 原路徑逐位元相同
        （回歸閘 1：regress_tradability 18 組、regress_delist 6 組、改前／改後 A/B；回歸閘 2：researchp9 base 臂；
          見 backtest/selftest_p9engine.py、backtest/resultsp9_engine/ENGINE_REPORT.md）
      entry_tranches  2-A 分批進場：整數 k ≥ 2。slot 拆 k 等份：進場日買 1 份（slot÷k），之後在進場日 +20、+40…個
                      交易日（日曆位置）各買 1 份（每份 ＝【進場日那個 slot】÷k，⛔ 不是當天的 slot）；
                      期間已出場（或當天就是排程出場日）⇒ 剩下的不買（計入 x_tr_unbought）
      add_rule        2-B 加碼：dict，每部位【只加一次】、加 size（預設 0.5）×【加碼當天的 slot】（equity[t−1]÷N）
                        {"kind": "gain", "x": 0.15}  ⓐ 收盤[t−1] ÷ 進場價 − 1 ≥ x ⇒ t 開盤加
                        {"kind": "flag", "flags": {sid: 長度 ncal 的布林序列}}
                                                     ⓑ flags[sid][t−1] 為真 ⇒ t 開盤加（「貼近 120 日高點三分位」由呼叫端
                                                        照 PREREGP8 算好傳進來；⛔ 引擎不認識三分位）；進場日以前的旗標讀不到
                        {"kind": "hold", "days": 40} ⓒ 持有滿 days 根（進場那根算第 1 根，同 H120 口徑）那天的收盤
                                                        ＞ 進場價 ⇒ 次一交易日開盤加；⭐ 只在那一天判一次（當天不為正 ⇒ 不加）
                        {"kind": "loss", "x": 0.10}  ⓓ（PREREG攤平停利 乙一，見下段）收盤[t−1] ≤ (1 − x) × 進場價 ⇒ t 開盤加（攤平）
                      "short": "skip"（預設，登錄 §二 2-B 逐字「現金不足不加並記次數」）／"partial"（有多少買多少、記次數）
                      ⭐ 現金不足時該部位的加碼機會就用掉了（⛔ 不每天重試）⇒ 計入 x_add_short
      trim_rule       2-C ⓐ 個股減半：dict {"x": 0.10, "frac": 0.5}：收盤[t−1] ÷ 進場價 − 1 ≤ −x ⇒ t 開盤賣 frac（以股數計）；
                      只一次；⛔ 不是停損出場，剩下的照原排程出場
                      {"kind": "gain", "x": 0.15, "frac": 0.5} ⓘ（PREREG攤平停利 乙二，見下段）收盤[t−1] ≥ (1 + x) × 進場價
                        ⇒ t 開盤賣 frac；"kind" 省略或 "loss" ＝ 上面的 2-C ⓐ（⛔ 原式一字不改）
      size_mult_by_regime  2-C ⓑⓒⓓⓔ 新部位倍數：dict {"mult": m, "below": 布林序列} 或 {"mult": m, "ma": n, "bench": 0050 還原收盤}
                      below[t−1]（見 regime_below）為真 ⇒ 第 t 天進場的新部位買 m × slot
                        m ≤ 1：與 weak／weak_size 同一條算式（slot×m 再 min(slot, 現金)）⇒ ⓑⓓⓔ 用 m＝0.5
                        m ＞ 1（ⓒ 1.5）：「上限、現金不足照 2-B 規則」⇒ "short": "skip"（預設）現金 ＜ m×slot ⇒ 只買 1 個 slot
                                         （仍照 min(slot, 現金)）並計入 x_mult_short；"partial" ⇒ min(m×slot, 現金)
                      ⭐ 已持有的部位不動（同 ⓑ）
      regime_trim     2-C ⓕⓖⓗ 跌破賣半：dict {"hold": 0.5, "below": 布林序列} 或 {"hold": 0.5, "ma": n, "bench": 0050 還原收盤}
                      below[t−1] 為真 ⇒ t 開盤把每一個「整份」部位賣到剩 hold（以股數計），並標為「半份」；
                        線下期間進場的新部位只買 hold × slot，也標「半份」；已是半份的不再賣
                      below[t−1] 為假 ⇒ t 開盤把每一個「半份」部位加買到 1÷hold 倍股數（＝賣出前的股數／整份）
                        現金 ＜ 總需求 ⇒ 每一檔按【同一比例】少補（比例＝現金÷總需求），記 x_rt_refill_short（天數）
                      賣出所得留現金（cash_mode="zero" ⇒ 報酬 0）；出場照原排程、⛔ 不因賣半而改；已出場的不補
    PREREG攤平停利 乙（2026-09-25，台股策略線登錄 seq2 sha 17449e5624991924；裁定線 seq177 §一① 准 (a)；回測線落地）
    在既有兩個參數上各加一種 kind，⛔ 沒有新增參數名；⭐ 不傳該 kind ⇒ 走的仍是原本那幾行（回歸閘見
    backtest/selftest_avgengine.py、backtest/resultsAvg/ENGINE_B_REPORT.md）：
      add_rule  {"kind": "loss", "x": 0.10[, "size": 0.5][, "short": "skip"]}   乙一 2-B ⓓ 個股攤平
                  部位收盤[t−1] ≤ (1 − x) × 進場價 ⇒ t 開盤加 size ×【加碼當天的 slot】（equity[t−1]÷N）；每部位只一次；
                  現金不足、漲停／停牌遞延、計數鍵（x_add_trig／x_add_n／x_add_short／x_add_blocked_days）、audit kind "add"
                  ⇒ 全部與 gain／flag／hold 同一段程式（⭐ 只多一個觸發分支）
      trim_rule {"kind": "gain", "x": 0.15[, "frac": 0.5]}                     乙二 2-C ⓘ 個股停利
                  部位收盤[t−1] ≥ (1 + x) × 進場價 ⇒ t 開盤賣 frac（以股數計）；只一次；賣得的現金照 2-C ⓐ 原樣留現金；
                  跌停／停牌遞延、計數鍵（x_trim_n／x_trim_blocked_days）、audit kind "trim" ⇒ 與 2-C ⓐ 同一段程式
      ⭐ 等號與寫法照登錄字面「收盤 ≤ 0.90 × 進場價」「收盤 ≥ 1.15 × 進場價」（裁定 seq177 §一① 收下回測 2122 §四①）：
        程式式是 c ≤ (1 − x)·ep、c ≥ (1 + x)·ep（等號算觸發；1 − 0.10 ＝＝ 0.90、1 + 0.15 ＝＝ 1.15 在浮點上逐位元成立）
        ⚠ 與既有 gain／2-C ⓐ 的比值式 c/ep − 1 ≥ x、≤ −x【不同】：價格恰好落在門檻上時比值式可能差一個 ulp 而不觸發
          （例 ep＝10、c＝9.0：字面式觸發、比值式 9.0/10 − 1 ＝ −0.09999999999999998 不觸發）⇒ 既有兩型 ⛔ 沒改（會破壞 P9 的逐位元重現）
      x 必須明給（⛔ 不給預設值，避免 −10%／＋15% 靠預設值帶進來）；loss 的 x ∈ (0, 1)、gain 的 x ＞ 0
    PREREG攤平停利 seq3 乙二（2026-09-25，台股策略線登錄 seq3 sha 31cc3c4e5d565dda 乙二 ①～④；裁定線 seq180 §二①、seq181 核准；
    回測線落地）再加【第三個開關】（新參數名，⛔ 預設關閉；回歸閘見 backtest/selftest_avgengine2.py、resultsAvg/ENGINE_B2_REPORT.md）：
      trim_proceeds  None（預設 ⇒ 下面每一段都跳過、原路徑逐位元相同 ＝ 登錄乙三「賣得現金閒置」描述版：賣得現金併入一般現金、報酬 0）
                     "next" ⇒ 賣半拿回的現金流向下一檔候選；⛔ 只能與 trim_rule kind="gain" 同開（其他組合 ⇒ ValueError）
        每一次賣半拿回的【淨】現金（成交金額 − 該筆 f×B×COST ＝ 實際入帳的錢）記成一筆「待買」，排進先進先出佇列：
        ① 名額：待買買進的是一個新部位、佔 1 個槽位；總部位數仍 ≤ 當天容量（n_slots／caps[t]）
           ⇒ 槽滿的量測日不買、等（計入 x_nx_full_days）；⛔ 不超過容量
        ② 買哪一檔：「量測日」＝ 訊號表 sig 有 entry_pos＝t 的交易日（⛔ 沒有訊號列的日子引擎看不到 ⇒ 與候選池空同義）；
           候選池 ＝ 當天訊號去掉已持有的（含被賣半、仍持有的那一檔）⇒ ⛔ 不重複買；挑法 ＝ 引擎原本那一次 rng.permutation
           （或 pick 排序）⇒ ⛔ 不另外抽、同顆種子的 rng 接著抽；待買【先】配給挑中的前幾檔（先賣的先買），剩下的名額才照原規則
           進一般新部位
        ③ 金額：該筆待買的全額（⛔ 不是 slot、⛔ 不取 min(slot, ·)、⛔ 不併筆：一筆待買 ＝ 一檔）
        ④ 當天有訊號但全是已持有的（計入 x_nx_empty_days）或槽滿 ⇒ 留到下一個有候選且有空槽的量測日；期間是現金、報酬 0
        ⭐ 讀法（登錄沒寫，本件選的；交件報告列出）：
          ・「下一個量測日」＝ 賣出日（含）以後第一個量測日：賣半在 t 開盤、新部位也在 t 開盤（同日順序 排程出場 → 賣 → 新部位）
            ⇒ 賣出日本身是量測日 ⇒ 當天就買（⛔ 沒有前視：賣半的觸發只讀 t−1 收盤，挑股只用當天的訊號池）
          ・待買與一般新部位同一天搶名額 ⇒ 待買先配（它先到；避免因名額被一般新部位拿走而一直閒置）；待買動用的只有它自己那筆錢，
            而輪到一般新部位時佇列已清空 ⇒ 一般新部位照舊 min(slot, 現金)，⛔ 不會動到還在等的待買
          ・tradable 開啟時挑中的那檔開盤漲停／停牌 ⇒ 照原規則該名額今天持現金、⛔ 不遞補；待買不消耗，配給挑中名單裡下一檔可買的，
            或繼續等（當時有待買 ⇒ 計入 x_nx_blocked）
          ・待買買進的部位是一般部位：出場照該訊號列的排程；它自己漲 15% 也會賣半（每部位一次），拿回的錢再成一筆待買
          ・x_new_n／x_mbar_* 只數一般新部位（⛔ 不含待買買進的）；trades／m 兩者都數；audit 的這種買進多記 kind＝"nx"
          ・模擬結束還沒買出去的待買 ⇒ 留現金（x_nx_pending_end 筆、x_nx_pending_amt_end 元）
        多回傳（只在 "next" 時出現）：x_nx_n（待買買進筆數）、x_nx_amt（金額合計）、x_nx_waits（每筆 賣出日 → 買進日 的交易日數）、
          x_nx_full_days、x_nx_empty_days、x_nx_blocked、x_nx_pending_end、x_nx_pending_amt_end
    裁定線 seq186 §三 選（乙）（2026-09-26；回測線落地）再加 nx_cap（⛔ 預設 None ⇒ 與 12c39cb810 逐位元相同）：
      nx_cap  None（預設）⇒ 待買的容量 ＝ 當天容量（n_slots／caps[t]）⇒ 上面 ①「⛔ 不超過容量」原樣
                ⭐ 裁定 seq188 的 #1（N＝10）停損／停利賣出後買下一檔、同在 10 槽上限內 ＝ 就是這條 None 路徑
              整數 K ⇒ 待買買進可以用到【總部位數】≤ K_t ＝ max(K, 當天容量)（caps 開啟時取 max(K, caps[t])）；
                一般新部位仍只在【總部位數】＜ 當天容量時才買（⭐ 讀法，裁定線給的：看總數、⛔ 不是看一般部位數）
                ⇒ 例 n_slots＝8、nx_cap＝10：一般新部位滿 8 就停；待買可以開到第 9、10 檔；滿 10 待買才等（x_nx_full_days）；
                  目前 9 檔（其中 1 檔是待買買進的）⇒ 一般新部位不買，要等總數 ＜ 8
                同一天：挑中名單的長度 ＝ max(min(待買筆數, K_t − 總數), 當天容量 − 總數)，待買先配（同 seq3）、剩下的才是一般新部位
                ⇒ 一般新部位買完時總數 ≤ 當天容量；待買買完時總數 ≤ K_t
              ⛔ 只能與 trim_proceeds="next" 同開；純量 n_slots 時 K 必須 ≥ n_slots；K 要是整數（bool ⇒ ValueError）
              多回傳（只在 K 給了時出現）：x_nx_over（總數已 ≥ 當天容量時由待買買進的筆數 ＝ 第 9、10 檔那種）
    PREREG名單出場 乙（2026-09-26，台股策略線登錄 seq1 sha db11230f58632a0d；裁定線 seq189 發號；回測線落地）再加三個參數，
    ⛔ 全部預設關閉 ⇒ 與 b1717d5c19 逐位元相同（回歸閘見 backtest/selftest_listexit.py、resultsListExit/ENGINE_REPORT.md）：
      stop_line_le  False（預設：stop_line 照原樣「收盤 ＜ 線」才觸發）／True ⇒「收盤 ≤ 線」（S1「收盤 ≤ 進場價 × 0.90」用；線 ＝ ep × 0.90，
                    ep 照引擎規則 ＝ 進場日開盤、開盤無效改用當日收盤）；⛔ 只能與 stop_line 同開
      stop_proceeds None（預設）／"next" ⇒ stop_line 停損全出拿回的【淨】現金（沒動過的部位 amt×(1＋gross−COST)；被賣半過的
                    amt×(1＋gross) − B×COST，＝ 當天實際入帳的錢）記成一筆待買，進 trim_proceeds 同一個先進先出佇列，規則照 seq3 ①～④
                    （待買先配、全額、一筆一檔、不重複買、同顆 rng 接著抽、槽滿等、期間報酬 0；容量照 nx_cap，None ＝ 當天容量）
                    ⛔ 只能與 stop_line 同開；可單獨開（S1、S2）或與 trim_proceeds 同開（S1＋T1、S2＋T1）
                    ⭐ 讀法：登錄「次一交易日的訊號池」＝ 從觸發日（t−1 收盤）算的次一交易日 t ＝ 停損賣出那天；停損在 t 開盤賣、
                      新部位也在 t 開盤買、同日順序 停損 → 排程出場 → 賣半 → 新部位 ⇒ 與 seq3 讀法 b「含賣出當天」一致（⛔ 沒有前視）
      stop_block    None（預設）／dict sid → {"trd", "dn_o"}（backtest/tradability.build 的同名欄）⇒ 描述版「開盤跌停或停牌賣不掉」：
                    【只】擋 stop_line 的停損賣出（開盤跌停 dn_o 或停牌 trd＝False ⇒ 延到下一個可成交開盤、每天計入 sl_delayed_days，
                    另回 sl_block_days）；進場、排程出場、賣半一律照原樣（⛔ 不等於開 tradable）；⛔ 只能與 stop_line 同開
      stop_line 與 trim_rule kind="gain" 可以同開（⛔ 其他 P9 參數仍與 stop_line 互斥）：
        同一天先處理停損（整檔出）、再處理賣半 ⇒ 已停損的部位不再賣半；停損已觸發但還在等可賣開盤的部位 ⇒ 也不賣半
      ⚠ 停損後同檔再買：⛔ 引擎沒有冷卻（裁定：照登錄括號「＝ 引擎原 20 根去重」，那是訊號建構器 research11.stock_features 的
        「同檔上一個訊號之後 > 20 根有效 K 棒」，⛔ 不是從停損日算）；預留設計 stop_cooldown（未實作，等裁定）
      多回傳：stop_block 給了 ⇒ sl_block_days；stop_proceeds 給了 ⇒ x_nx_stop_lots（停損產生的待買筆數）
    裁定線 seq192（2026-09-26）描述臂 D1「一般新部位優先」（⛔ 不判定）：
      nx_order  "before"（預設 ＝ seq3 起的現行：待買先配給挑中的前幾檔）／"after" ⇒ 同一天挑中的名單【先】照一般規則進一般新部位，
                一般新部位只用【一般現金】＝ 現金 − 佇列裡所有待買（⛔ 不動待買的錢）；一般現金買不起（min(slot, 一般現金) ≤ 1e−9）
                或總數已 ≥ 當天容量 ⇒ 名單剩下的檔才給待買（仍一筆一檔、全額、先進先出）
                nx_cap 開啟時名單長度 ＝ min(K_t − 總數, max(當天容量 − 總數, 0) ＋ 待買筆數)（一般到當天容量、待買到 K_t）
                ⛔ 只能與 trim_proceeds／stop_proceeds＝"next" 同開
      ⚠ 描述臂 D2「待買併入 slot／併池」⛔ 不需要新參數：就是 trim_proceeds=None（賣得現金併入一般現金，有空槽時一般新部位照
        min(equity/N, 現金) 買）；⚠ 登錄描述臂 ⓐ 的字面「賣得現金閒置到那檔出場」與引擎 None 路徑不同——引擎沒有「綁到那檔出場」
        的閒置，None 路徑那筆錢在【任何】槽空出來時就可以被一般新部位用到（上限 equity/N）
    ⭐ 共同規則（五個參數都一樣）：
      ・時序：所有判定只讀 t−1 以前（0050 狀態 below[t−1]、個股收盤[t−1]），成交在 t 開盤（還原開盤價）
      ・同一天的順序：排程出場 → 賣（減半／賣半）→ 買（補回／分批／加碼）→ 新部位進場
        ⭐ 既有部位的加減碼先於新部位（⚠ 讀法：登錄沒寫同日先後，選「先照顧已持有的」並寫在這裡）
      ・可交易性：買 ＝ 開盤有限且 > 0，tradable 開啟時另要有成交且開盤不是漲停；賣 ＝ 同上但開盤不是跌停
        ⇒ 做不成的那一筆留著，下一個交易日開盤再試（每天計入 x_*_blocked_days），直到排程出場日為止
      ・成本（引擎慣例：每一塊【買進的錢】在賣出時付一次來回 COST）：部位另記成本基礎 B（買進金額合計）
          賣 f（以股數計）⇒ 拿回 f × 市值 − f × B × COST，B ← (1−f)B；加買 a 元 ⇒ B ← B + a
          排程出場 ⇒ amt×(1+gross) − B×COST；⭐ 沒被動過的部位仍走原式 amt×(1+gross−COST)（⛔ 逐位元相同）
        部位的 amt 在擴充路徑上的意思是「以進場價 ep 計的名目」：市值 ＝ amt × 收盤 ÷ ep（⛔ 與原版同一個式子）
        ⇒ 在價格 p 加買 a 元 ⇒ amt ← amt + a × ep ÷ p；賣 f ⇒ amt ← (1−f) amt
      ・引擎沒有整張／零股的概念（金額連續）⇒ 登錄「股數取整張以下照引擎零股規則」＝ 不取整
      ・一個部位不論分幾批、加幾次，都只佔 1 個槽位（len(open_pos) 口徑不變）
      ・⛔ 五個參數互斥（也不與 weak 同開；登錄 §二「各自獨立、不互相疊加」；2-D 組合要另寫規則）；
        ⛔ 不與 stop／stop_line／weight_fn／cash_mode="bench" 同開（沒有 fixture 覆蓋 ⇒ 直接報錯）
      ・多回傳（只在開啟時出現，⛔ 關閉時回傳鍵與原版相同）：x_new_n、x_mbar_nominal、x_mbar_actual，以及各自的
        x_tr_*／x_add_*／x_trim_*／x_mult_*／x_rt_* 計數與成本（見程式尾）；audit 開啟時逐筆多記 kind 欄
    """
    # 裁定線 20260924-1714 §三⑥（2026-09-24）再加：
    #   audit      None（原版路徑，⛔ 逐位元相同）／list ⇒ 逐次換手的稽核紀錄，每筆一個 dict：
    #              t／date_pos／sid／side（"buy"/"sell"）／amt（成交金額）／px（成交價）
    #              ／target_w（目標權重＝amt÷前一日 equity）／equity_prev／cost（該筆成本）
    #              ⭐ 它與既有的 `log` 不同：log 記【訊號的去向】（含沒成交的），
    #                audit 記【真的成交的每一筆】的金額、權重與成本 ⇒ 兩者不重複
    #              ⛔ 成本口徑：進場不扣（COST 在出場一次扣完，見下面 cash += amt*(1+gross-COST)）
    #                ⇒ 所以 buy 的 cost 記 0.0、sell 的 cost 記 amt*COST ⇒ ⭐ 與引擎的記帳一致
    # 裁定線 20260924-1714 §一（2026-09-24）再加：
    #   tradable   None（原版路徑，⛔ 逐位元相同，回歸閘門 backtest/regress_tradability.py）／
    #              dict sid → {"trd","up_o","dn_o"}（backtest/tradability.build）：
    #              ① 買：進場日開盤＝漲停價 或 停牌 ⇒ 不成交，該名額今天持現金（⛔ 不遞補下一名）
    #              ② 賣：出場日停牌 ⇒ 延到第一個可交易日【開盤】出；那天開盤＝跌停價 ⇒ 再等下一天
    #                 延後期間照市價（ffill 收盤）計值
    #              ③ 開啟時 613–615 那個「open 非有限 ⇒ 用 ffill 收盤成交」的退路不會被走到（進場前已擋）
    #              ⚠ 排程出場日【有成交】時照原版用當日收盤出（1714 §一② 的「開盤＝跌停」是針對開盤成交）
    #              ④（裁定線 20260924-1744 裁 (乙)）排程出場日【收盤＝跌停價】（dn_c）⇒ 視為賣不掉，
    #                 隔日起照 ② 在第一個可交易日【開盤】出（開盤又跌停 ⇒ 再等）；計入 tr_close_locked
    #                 ⛔ 只管排程出場；停損出場（stop）當天記的是 t−1 收盤，⛔ 不受當天 dn_c 影響
    #   delist     None（⛔ 原路徑逐位元相同，回歸閘門 backtest/regress_delist.py）／
    #              dict sid → {"last","status"}（backtest/tradability.delist_status）；⛔ 只在 tradable 開啟時有意義
    #              ⑤（裁定線 20260924-2319 seq98 §二）出場日沒成交、而且【之後再也沒有成交】（t > last）⇒ 先分類：
    #                 status delisted_official／delisted_gap ⇒ 下市 ⇒ 以最後成交價了結（用原本的 gross，
    #                   ＝ tradable 關閉時的行為）；計入 tr_delist_settled
    #                 status ambig（最後成交離全域日曆尾 < 60 日、又沒有官方下市日）⇒ 照停牌處理（延後／掛到模擬尾），
    #                   逐筆計入 tr_delist_ambig（⛔ 不猜）
    #              ⚠ 以最後成交價了結對下市股偏樂觀 ⇒ 用到這條的結論仍附倖存者有界論證
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
    tr_stats = {"limit_up": 0, "halt_in": 0, "exit_delayed": 0, "close_locked": 0} if tradable is not None else None
    if delist is not None:
        if tradable is None:
            raise ValueError("delist 只在 tradable 開啟時有意義（seq98 §二）")
        tr_stats.update({"delist_settled": 0, "delist_ambig": 0})
    _dl_ambig = set()
    # 裁定線 20260925-0407 seq119 §四（採回測 0400）：stop_line ＝ 每個部位一條【事先算好】的停損線
    #   dict[(sid, entry_pos)] → (start, levels)：levels[i] ＝ 日曆位置 start+i 收盤時生效的停損價（NaN ＝ 無停損）
    #   行為：t−1 收盤 < 該部位 t−1 的停損價 ⇒ 第 t 根【開盤】出場；開盤跌停／停牌／開盤無效 ⇒ 留著，第一個可賣的開盤出
    #   ⛔ 排程出場當天不搶（同 stop）；⛔ 與 stop 同時給 ⇒ 報錯；None ⇒ 本段全部跳過（原路徑逐位元相同）
    #   ⭐ 引擎不認識「碎形」：停損線怎麼算在研究腳本（backtest/stop_fractal.py），前視由那邊的 fixture ①⑤ 把關
    if stop_line is not None and stop is not None:
        raise ValueError("stop_line 與 stop 不可同時給（裁定線 seq119 §四 條件一）")
    sl_key = {}; sl_pending = set(); sl_stats = {"sl_exits": 0, "sl_delayed_days": 0, "sl_skip_sched": 0}; sl_days = []
    _eq_prev = 1.0                  # ⭐ audit 用：前一日 equity（算目標權重的分母）
    maxw_daily = np.zeros(ncal) if (report_maxw and maxw_detail) else None
    maxw_sid = [""] * ncal if (report_maxw and maxw_detail) else None
    peak_close = {}                 # sid → 進場後最高收盤（trail 用）
    stop_exits = 0; stop_days = []; stop_cut_right_tail = 0; hold_days = []; entry_day = {}
    # ── PREREGP9 seq8 §六 引擎擴充（規格見 docstring 末段）。⛔ 五個參數全 None ⇒ _ext False ⇒ 下面的狀態全是 None、每一段都跳過
    _xk = None if (entry_tranches is None or entry_tranches == 1) else entry_tranches
    _ext = any(p is not None for p in (_xk, add_rule, trim_rule, size_mult_by_regime, regime_trim))
    _xs = _xb = _xc = _xbelow = _xm = _xm_short = _add_kind = _rt_hold = None
    _trim_kind = None               # PREREG攤平停利 乙二：trim_rule 的 kind（None ＝ trim_rule 關）
    if _ext:
        n_on = sum(p is not None for p in (_xk, add_rule, trim_rule, size_mult_by_regime, regime_trim, weak))
        if n_on != 1:
            raise ValueError("PREREGP9 seq8 的五個參數（與 weak）一次只能開一個（登錄 §二：各自獨立、不互相疊加）")
        _sl_trim = stop_line is not None and trim_rule is not None and trim_rule.get("kind", "loss") == "gain"   # 名單出場 乙：S＋T 組合格
        if stop is not None or (stop_line is not None and not _sl_trim) or weight_fn is not None or use_bench:
            raise ValueError("PREREGP9 seq8 的參數不與 stop／stop_line／weight_fn／cash_mode='bench' 同開（沒有 fixture 覆蓋）")

        def _below_of(spec, name):
            if "below" in spec:
                bl_ = np.asarray(spec["below"], bool)
            else:
                bl_ = regime_below(spec["bench"], spec["ma"])
            if bl_.shape != (ncal,):
                raise ValueError(f"{name} 的狀態序列要是長度 {ncal}，收到 {bl_.shape}")
            return bl_
        if _xk is not None:
            if int(_xk) != _xk or _xk < 2:
                raise ValueError(f"entry_tranches 要是 ≥ 1 的整數（1 ＝ 關閉），收到 {entry_tranches!r}")
            _xk = int(_xk)
        if add_rule is not None:
            _add_kind = add_rule.get("kind")
            if _add_kind not in ("gain", "flag", "hold", "loss"):
                raise ValueError(f"add_rule['kind'] 只能是 gain／flag／hold／loss，收到 {_add_kind!r}")
            if _add_kind == "loss" and not ("x" in add_rule and 0 < add_rule["x"] < 1):
                raise ValueError(f"add_rule kind='loss' 要明給 x ∈ (0, 1)（跌 x 加碼），收到 {add_rule!r}")
            if add_rule.get("short", "skip") not in ("skip", "partial"):
                raise ValueError("add_rule['short'] 只能是 'skip'（登錄逐字）或 'partial'")
            if _add_kind == "hold" and int(add_rule.get("days", 40)) < 1:
                raise ValueError("add_rule['days'] 要 ≥ 1")
        if trim_rule is not None:
            _trim_kind = trim_rule.get("kind", "loss")
            if _trim_kind not in ("loss", "gain"):
                raise ValueError(f"trim_rule['kind'] 只能是 loss（2-C ⓐ，預設）／gain（2-C ⓘ），收到 {_trim_kind!r}")
            if _trim_kind == "gain":
                if not ("x" in trim_rule and trim_rule["x"] > 0 and 0 < trim_rule.get("frac", 0.5) < 1):
                    raise ValueError(f"trim_rule kind='gain' 要明給 x ＞ 0、frac ∈ (0, 1)，收到 {trim_rule!r}")
            elif not (0 < trim_rule.get("x", 0.10) < 1 and 0 < trim_rule.get("frac", 0.5) < 1):
                raise ValueError(f"trim_rule 的 x、frac 都要在 (0, 1)，收到 {trim_rule!r}")
        if size_mult_by_regime is not None:
            _xm = float(size_mult_by_regime["mult"])
            _xm_short = size_mult_by_regime.get("short", "skip")
            if not (_xm > 0) or _xm_short not in ("skip", "partial"):
                raise ValueError(f"size_mult_by_regime：mult 要 > 0、short 只能是 skip／partial，收到 {size_mult_by_regime!r}")
            _xbelow = _below_of(size_mult_by_regime, "size_mult_by_regime")
        if regime_trim is not None:
            _rt_hold = float(regime_trim.get("hold", 0.5))
            if not (0 < _rt_hold < 1):
                raise ValueError(f"regime_trim['hold'] 要在 (0, 1)，收到 {_rt_hold!r}")
            _xbelow = _below_of(regime_trim, "regime_trim")
        _xs = {}                        # sid → 部位狀態：t0、slot0、tr（已處理份數）、add／trim（0 未觸發、1 待成交、2 完成）、rt（full／half）
        _xb = {}                        # sid → 成本基礎 B（⭐ 只有被加減碼動過的部位才有；沒動過 ⇒ 出場走原式）
        _xc = {"new_n": 0, "mult_nom": 0.0, "mult_act": 0.0,
               "tr_buys": 0, "tr_short": 0, "tr_blocked_days": 0, "tr_unbought": 0,
               "add_n": 0, "add_short": 0, "add_trig": 0, "add_blocked_days": 0,
               "trim_n": 0, "trim_blocked_days": 0,
               "mult_n": 0, "mult_short": 0,
               "rt_sell_events": 0, "rt_sell_n": 0, "rt_refill_events": 0, "rt_refill_n": 0, "rt_refill_short": 0,
               "rt_refill_fill_min": 1.0, "rt_blocked_days": 0,
               "cost_sell": 0.0, "buy_amt": 0.0}
        _xyear_cost = {}                # 日曆位置 t → 當天加減碼賣出付的成本（給 §四⑦「每年因賣半與補回多付的成本」）

    _nx = None                      # PREREG攤平停利 seq3 乙二：賣得現金流向下一檔（None ＝ 關 ⇒ 下面每一段都跳過）
    if trim_proceeds is not None:
        if trim_proceeds != "next":
            raise ValueError(f"trim_proceeds 只能是 None（關）或 'next'，收到 {trim_proceeds!r}")
        if trim_rule is None or _trim_kind != "gain":
            raise ValueError("trim_proceeds='next' 只能與 trim_rule kind='gain' 同開（PREREG攤平停利 seq3 乙二）")
        _nx = {"lots": [], "n": 0, "amt": 0.0, "waits": [], "full_days": 0, "empty_days": 0, "blocked": 0}
    _nx_trim = _nx is not None      # 賣半的淨現金進待買（trim_proceeds="next"）
    _nx_stop = False                # PREREG名單出場 乙：停損全出的淨現金進待買（stop_proceeds="next"）
    if not isinstance(stop_line_le, (bool, np.bool_)):
        raise ValueError(f"stop_line_le 只能是 True／False，收到 {stop_line_le!r}")
    if stop_line_le and stop_line is None:
        raise ValueError("stop_line_le 只能與 stop_line 同開")
    if stop_block is not None and stop_line is None:
        raise ValueError("stop_block 只能與 stop_line 同開（只擋停損賣出）")
    if stop_proceeds is not None:
        if stop_proceeds != "next":
            raise ValueError(f"stop_proceeds 只能是 None（關）或 'next'，收到 {stop_proceeds!r}")
        if stop_line is None:
            raise ValueError("stop_proceeds='next' 只能與 stop_line 同開")
        _nx_stop = True
        if _nx is None:
            _nx = {"lots": [], "n": 0, "amt": 0.0, "waits": [], "full_days": 0, "empty_days": 0, "blocked": 0}
        _nx["stop_lots"] = 0
    if nx_order not in ("before", "after"):
        raise ValueError(f"nx_order 只能是 'before'（預設）或 'after'，收到 {nx_order!r}")
    if nx_order == "after" and _nx is None:
        raise ValueError("nx_order='after' 只能與 trim_proceeds／stop_proceeds='next' 同開（裁定 seq192 D1）")
    _nx_after = nx_order == "after"
    _sl_blk = 0                     # stop_block 擋掉的停損賣出（天次）
    _nxk = None                     # 裁定 seq186 §三（乙）：待買的總檔數上限（None ⇒ ＝ 當天容量、12c39cb810 路徑）
    if nx_cap is not None:
        if _nx is None:
            raise ValueError("nx_cap 只能與 trim_proceeds='next'／stop_proceeds='next' 同開（裁定 seq186 §三）")
        if isinstance(nx_cap, (bool, np.bool_)) or not isinstance(nx_cap, (int, np.integer)):
            raise ValueError(f"nx_cap 要是整數，收到 {nx_cap!r}")
        _nxk = int(nx_cap)
        if _nxk < 1 or (caps is None and _nxk < n_slots):
            raise ValueError(f"nx_cap 必須 ≥ n_slots（{n_slots}），收到 {nx_cap!r}")
        _nx["over"] = 0

    def _x_px(sid, t, side):
        """t 開盤能不能成交：能 ⇒ 回開盤價；不能 ⇒ None（見 docstring「可交易性」）。"""
        o = float(opens[sid][t])
        if not (np.isfinite(o) and o > 0):
            return None
        if tradable is not None:
            tb = tradable[sid]
            if not tb["trd"][t] or (tb["up_o"][t] if side == "buy" else tb["dn_o"][t]):
                return None
        return o

    def _x_sell(k, t, frac, o, kind):
        """賣掉 open_pos[k] 的 frac（以股數計）於開盤價 o；成本 ＝ frac × B × COST。"""
        nonlocal cash
        ex, sid, amt, gross, ep = open_pos[k]
        b0 = _xb.get(sid, amt)
        proceeds = amt * frac * o / ep
        c_ = b0 * frac * COST
        cash += proceeds - c_
        open_pos[k] = (ex, sid, amt * (1.0 - frac), gross, ep)
        _xb[sid] = b0 * (1.0 - frac)
        _xc["cost_sell"] += c_; _xyear_cost[t] = _xyear_cost.get(t, 0.0) + c_
        if audit is not None:
            audit.append({"t": t, "sid": sid, "side": "sell", "kind": kind, "amt": float(proceeds), "px": o,
                          "target_w": (float(proceeds) / _eq_prev) if _eq_prev > 0 else float("nan"),
                          "equity_prev": _eq_prev, "cost": float(c_)})
        return proceeds - c_

    def _x_buy(k, t, a, o, kind):
        """用 a 元現金在開盤價 o 加買 open_pos[k]：amt ← amt + a×ep÷o、B ← B + a（成本等賣出時再付）。"""
        nonlocal cash
        ex, sid, amt, gross, ep = open_pos[k]
        b0 = _xb.get(sid, amt)
        cash -= a
        open_pos[k] = (ex, sid, amt + a * ep / o, gross, ep)
        _xb[sid] = b0 + a
        _xc["buy_amt"] += a
        if audit is not None:
            audit.append({"t": t, "sid": sid, "side": "buy", "kind": kind, "amt": float(a), "px": o,
                          "target_w": (float(a) / _eq_prev) if _eq_prev > 0 else float("nan"),
                          "equity_prev": _eq_prev, "cost": 0.0})

    def _x_day(t):
        """每天開盤、排程出場之後、新部位進場之前：既有部位的加減碼（先賣後買）。"""
        nonlocal cash
        ns_ = n_slots if caps is None else int(caps[t])
        # ① 個股減半（2-C ⓐ）
        if trim_rule is not None:
            tx = trim_rule.get("x", 0.10); tf = trim_rule.get("frac", 0.5)
            for k in range(len(open_pos)):
                ex, sid, amt, gross, ep = open_pos[k]
                s = _xs.get(sid)
                if ex <= t or s is None or s["trim"] == 2:
                    continue
                if stop_line is not None and sid in sl_pending:
                    continue                        # 名單出場 乙：停損已觸發、在等可賣的開盤 ⇒ 整檔要出、⛔ 不賣半  # _SLPEND
                if s["trim"] == 0:
                    c1 = float(closes[sid][t - 1])  # _XLAG
                    if _trim_kind == "gain":        # 乙二 2-C ⓘ：登錄字面「收盤 ≥ 1.15 × 進場價」
                        if np.isfinite(c1) and c1 >= (1.0 + tx) * ep:
                            s["trim"] = 1
                    elif np.isfinite(c1) and c1 / ep - 1.0 <= -tx:
                        s["trim"] = 1
                if s["trim"] == 1:
                    o = _x_px(sid, t, "sell")
                    if o is None:
                        _xc["trim_blocked_days"] += 1; continue
                    net_ = _x_sell(k, t, tf, o, "trim"); s["trim"] = 2; _xc["trim_n"] += 1
                    if _nx_trim:
                        _nx["lots"].append((net_, t))       # seq3 乙二：實際入帳的淨現金 ⇒ 一筆待買（先進先出）
        # ② 跌破賣半／站回補回（2-C ⓕⓖⓗ）
        if regime_trim is not None:
            bl = bool(_xbelow[t - 1])  # _XLAG
            if bl:
                n_ = 0
                for k in range(len(open_pos)):
                    ex, sid, amt, gross, ep = open_pos[k]
                    s = _xs.get(sid)
                    if ex <= t or s is None or s["rt"] != "full":
                        continue
                    o = _x_px(sid, t, "sell")
                    if o is None:
                        _xc["rt_blocked_days"] += 1; continue
                    _x_sell(k, t, 1.0 - _rt_hold, o, "rt_sell"); s["rt"] = "half"; n_ += 1
                if n_:
                    _xc["rt_sell_events"] += 1; _xc["rt_sell_n"] += n_
            else:
                need = []
                for k in range(len(open_pos)):
                    ex, sid, amt, gross, ep = open_pos[k]
                    s = _xs.get(sid)
                    if ex <= t or s is None or s["rt"] != "half":
                        continue
                    o = _x_px(sid, t, "buy")
                    if o is None:
                        _xc["rt_blocked_days"] += 1; continue
                    need.append((k, s, o, amt * o / ep * (1.0 / _rt_hold - 1.0)))   # 補到 1÷hold 倍股數所需的金額
                if need:
                    tot = sum(n_ for _, _, _, n_ in need)
                    scale = 1.0 if cash >= tot else max(cash, 0.0) / tot
                    if scale < 1.0:
                        _xc["rt_refill_short"] += 1; _xc["rt_refill_fill_min"] = min(_xc["rt_refill_fill_min"], scale)
                    for k, s, o, n_ in need:
                        a = n_ * scale
                        if a > 1e-12:
                            _x_buy(k, t, a, o, "rt_refill")
                        s["rt"] = "full"
                    _xc["rt_refill_events"] += 1; _xc["rt_refill_n"] += len(need)
        # ③ 分批進場的第 2..k 份（2-A）
        if _xk is not None:
            for k in range(len(open_pos)):
                ex, sid, amt, gross, ep = open_pos[k]
                s = _xs.get(sid)
                if ex <= t or s is None:
                    continue
                due = min(_xk - 1, (t - s["t0"]) // TRANCHE_GAP) - s["tr"]
                if due <= 0:
                    continue
                o = _x_px(sid, t, "buy")
                if o is None:
                    _xc["tr_blocked_days"] += 1; continue
                want = s["slot0"] / _xk * due
                a = min(want, cash)
                if a < want:
                    _xc["tr_short"] += 1
                if a > 1e-9:
                    _x_buy(k, t, a, o, "tranche")
                s["tr"] += due; _xc["tr_buys"] += due
        # ④ 加碼（2-B ⓐⓑⓒ）
        if add_rule is not None:
            size = add_rule.get("size", 0.5)
            for k in range(len(open_pos)):
                ex, sid, amt, gross, ep = open_pos[k]
                s = _xs.get(sid)
                if ex <= t or s is None or s["add"] == 2:
                    continue
                if s["add"] == 0:
                    if _add_kind == "gain":
                        c1 = float(closes[sid][t - 1])  # _XLAG
                        trig = bool(np.isfinite(c1) and c1 / ep - 1.0 >= add_rule.get("x", 0.15))
                    elif _add_kind == "loss":        # 乙一 2-B ⓓ：登錄字面「收盤 ≤ 0.90 × 進場價」
                        c1 = float(closes[sid][t - 1])  # _XLAG
                        trig = bool(np.isfinite(c1) and c1 <= (1.0 - add_rule["x"]) * ep)
                    elif _add_kind == "flag":
                        fl = add_rule["flags"].get(sid)
                        trig = bool(fl is not None and fl[t - 1])  # _XLAG
                    else:
                        tj = s["t0"] + int(add_rule.get("days", 40)) - 1     # 持有滿 days 根的那一天（進場那根算第 1 根）
                        if t - 1 < tj:
                            continue                                     # 還沒滿 days 根
                        c1 = float(closes[sid][t - 1])  # _XLAG
                        trig = bool(t - 1 == tj and np.isfinite(c1) and c1 > ep)
                        if not trig:
                            s["add"] = 2; continue                       # ⭐ 只在滿 days 根那一天判一次
                    if not trig:
                        continue
                    s["add"] = 1; _xc["add_trig"] += 1
                o = _x_px(sid, t, "buy")
                if o is None:
                    _xc["add_blocked_days"] += 1; continue
                want = size * equity[t - 1] / ns_
                if cash < want:
                    _xc["add_short"] += 1
                    a = min(want, cash) if add_rule.get("short", "skip") == "partial" else 0.0
                else:
                    a = want
                if a > 1e-9:
                    _x_buy(k, t, a, o, "add"); _xc["add_n"] += 1
                s["add"] = 2

    def _rec(row, reason, t, delay=0, gross=np.nan):
        if log is not None:
            rec = {"t": t, "sid": row["sid"], "entry_pos": int(row["entry_pos"]), "exit_pos": int(row["exit_pos"]), "reason": reason, "delay": delay, "gross": gross,
                   **{c: row[c] for c in extra}}
            if f"g_{rule}" not in rec:
                rec[f"g_{rule}"] = float(row["gross"])      # 主格出場的原始逐筆報酬（rule 那一欄被改名成 gross，這裡補回原名）
            log.append(rec)

    t_end = min(ncal, last + 2); t_done = t_end - 1
    for t in range(first, ncal if tradable is not None else t_end):
        if tradable is not None and t >= t_end and not open_pos:
            break                                         # ⭐ 延後出場全部了結才停
        hit_now = ()                                      # 今天被停損改成出場的 sid（⛔ 只給 tradable 的 dn_c 排除用）
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
            hit_now = set(hit)
        if stop_line is not None and open_pos and t > first:
            hit = []
            for k, (ex, sid, amt, gross, ep) in enumerate(open_pos):
                if ex <= t:
                    if sid in sl_pending:
                        sl_pending.discard(sid)
                    continue                                  # 排程出場本來就在今天結清，⛔ 不搶它
                trig = sid in sl_pending
                if not trig:
                    key = sl_key.get(sid)
                    rec_ = stop_line.get(key) if key is not None else None
                    if rec_ is not None:
                        st0, lv = rec_; i = t - 1 - st0
                        c = float(closes[sid][t - 1])  # _SLLAG
                        if 0 <= i < len(lv) and np.isfinite(lv[i]) and np.isfinite(c) and (c <= lv[i] if stop_line_le else c < lv[i]):  # _SLCMP
                            trig = True
                if not trig:
                    continue
                o_t = float(opens[sid][t])
                can = np.isfinite(o_t) and o_t > 0
                if tradable is not None:
                    can = can and bool(tradable[sid]["trd"][t]) and not bool(tradable[sid]["dn_o"][t])
                if stop_block is not None and can:  # 名單出場 乙 描述版：只擋停損賣出
                    can = bool(stop_block[sid]["trd"][t]) and not bool(stop_block[sid]["dn_o"][t])  # _SLBLOCK
                    _sl_blk += not can
                if can:
                    open_pos[k] = (t, sid, amt, o_t / ep - 1.0, ep)
                    hit.append(sid); sl_pending.discard(sid)
                else:
                    sl_pending.add(sid); sl_stats["sl_delayed_days"] += 1
            if hit:
                sl_stats["sl_exits"] += len(hit); sl_days.append((t, len(hit)))
            hit_now = set(hit_now) | set(hit)
        still = []
        for ex, sid, amt, gross, ep in open_pos:
            if ex <= t and tradable is not None and (t > ex or not tradable[sid]["trd"][t]
                                                     or (sid not in hit_now and tradable[sid]["dn_c"][t])):
                tb = tradable[sid]; o_t = float(opens[sid][t])
                _dl = None
                if delist is not None and (not tb["trd"][t]) and sid in delist and t > delist[sid]["last"]:
                    _dl = delist[sid]["status"]                             # ⑤ 之後再也沒有成交
                if _dl is not None and _dl.startswith("delisted"):
                    tr_stats["delist_settled"] += 1                        # ⑤ 下市 ⇒ 以最後成交價了結（原 gross）
                else:
                    if _dl is not None and (sid, ex) not in _dl_ambig:
                        _dl_ambig.add((sid, ex)); tr_stats["delist_ambig"] += 1   # ⑤ 分不出 ⇒ 照停牌、逐筆報數
                    if t == ex and tb["trd"][t]:
                        tr_stats["close_locked"] += 1                      # ④ 排程出場日收盤鎖跌停
                    if t == ex or not tb["trd"][t] or tb["dn_o"][t] or not np.isfinite(o_t) or o_t <= 0:
                        still.append((ex, sid, amt, gross, ep)); continue  # 還賣不掉：照 ffill 收盤計值
                    gross = o_t / ep - 1.0                                 # ⭐ 第一個可成交日【開盤】出
                    tr_stats["exit_delayed"] += 1
            if ex <= t:
                _xb_ = _xb.pop(sid, None) if _xb is not None else None      # PREREGP9 seq8：被加減碼動過 ⇒ 成本基礎另記
                if audit is not None:
                    audit.append({"t": t, "sid": sid, "side": "sell", "amt": float(amt * (1 + gross)),
                                  "px": float(ep * (1 + gross)),
                                  "target_w": (float(amt * (1 + gross)) / _eq_prev) if _eq_prev > 0 else float("nan"),
                                  "equity_prev": _eq_prev, "cost": float(amt * COST) if _xb_ is None else float(_xb_ * COST)})
                if _xb_ is not None:
                    cash += amt * (1 + gross) - _xb_ * COST                    # ⛔ 只有動過的部位走這條；沒動過的仍走下面原式
                elif use_bench:
                    units += amt * (1 + gross - COST) * (1 - bench_cost) / bench[t]   # 拿回的錢買 bench，付單邊成本
                else:
                    cash += amt * (1 + gross - COST)
                if _nx_stop and sid in hit_now:    # 名單出場 乙：停損全出的淨入帳（與上面入帳同一式）⇒ 一筆待買  # _NXSTOP
                    _nx["lots"].append((amt * (1 + gross - COST) if _xb_ is None else amt * (1 + gross) - _xb_ * COST, t))
                    _nx["stop_lots"] += 1
                if _xs is not None:
                    s_ = _xs.pop(sid, None)
                    if s_ is not None and _xk is not None:
                        _xc["tr_unbought"] += _xk - 1 - s_["tr"]              # 2-A：出場時還沒買的份數
                held.discard(sid)
                if stop_line is not None:
                    sl_key.pop(sid, None); sl_pending.discard(sid)
                if stop is not None:
                    peak_close.pop(sid, None)
                    e0 = entry_day.pop(sid, None)
                    if e0 is not None:
                        hold_days.append(t - e0)           # 實際持有天數（⛔ 停損出場的會短於排程的 H）
            else:
                still.append((ex, sid, amt, gross, ep))
        open_pos = still
        if _ext and open_pos:
            _x_day(t)                                     # PREREGP9 seq8：既有部位的加減碼（⛔ _ext False 時不進來）
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
        _nx_kt = ns_t if _nxk is None else max(_nxk, ns_t)   # seq186：待買的容量（None ⇒ ＝ 當天容量）
        if _nx is not None and _nx["lots"] and g is not None and len(open_pos) >= _nx_kt:
            _nx["full_days"] += 1                        # seq3 乙二 ①：槽滿 ⇒ 待買等
        if g is not None and (len(open_pos) < ns_t or (_nxk is not None and _nx["lots"] and len(open_pos) < _nx_kt)):  # _NXK_ENTER
            if log is not None and held:
                for _, row in g[g["sid"].isin(held)].iterrows():
                    if "_t0" not in row or int(row["_t0"]) == t:      # 隊列裡的等待中不記；新訊號撞持倉才記 c
                        _rec(row, "c", t)
            cand = g[~g["sid"].isin(held)]
            if _nx is not None and _nx["lots"] and not len(cand):
                _nx["empty_days"] += 1                   # seq3 乙二 ④：有訊號但全是已持有的 ⇒ 待買等  # _NX_EMPTY
            if len(cand):
                slots_free = ns_t - len(open_pos)
                if _nxk is not None:                     # seq186：待買可用到 K_t；一般新部位仍只到 ns_t（待買先配 ⇒ 名單長度見 docstring）
                    slots_free = max(min(len(_nx["lots"]), _nx_kt - len(open_pos)), slots_free)   # _NXK_FREE
                    if _nx_after:                        # seq192 D1：一般到當天容量、待買到 K_t
                        slots_free = min(_nx_kt - len(open_pos), max(ns_t - len(open_pos), 0) + len(_nx["lots"]))   # _NXAFTER_FREE
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
                _x_big = None
                if _ext:                             # PREREGP9 seq8：新部位的大小（⛔ _ext False 時不進來）
                    _x_full = slot; _x_nom = 1.0
                    _x_bl = bool(_xbelow[t - 1]) if (_xbelow is not None and t >= 1) else False  # _XLAG
                    if _xk is not None:
                        slot = slot / _xk            # 2-A：第 1 份
                    elif _xm is not None and _x_bl:
                        _x_nom = _xm
                        if _xm <= 1:
                            slot = slot * _xm        # ⓑⓓⓔ：與 weak 同一條算式
                        else:
                            _x_big = slot * _xm      # ⓒ：上限 m×slot，現金不足照 2-B（見迴圈內）
                    elif regime_trim is not None and _x_bl:
                        _x_nom = _rt_hold; slot = slot * _rt_hold   # ⓕⓖⓗ：線下新部位只買 hold 份
                entered_q = set()
                targets = None
                if weight_fn is not None and len(take):          # PREREGP13：逐檔目標金額由呼叫端算（⛔ 現金不足的處置也在它那裡）
                    batch = [cand.iloc[i] for i in take]
                    targets = list(weight_fn(batch, t, equity[t - 1], cash))
                    if len(targets) != len(take):
                        raise ValueError(f"weight_fn 要回與 batch 等長的金額，batch {len(take)}／回 {len(targets)}")
                for j, i in enumerate(take):
                    if use_bench:
                        cash = units * bench[t] * (1 - bench_cost)                   # 賣 bench 能提出的現金（扣單邊成本）
                    row = cand.iloc[i]
                    if tradable is not None:
                        tb = tradable[row["sid"]]; o_t = float(opens[row["sid"]][t])
                        if (not tb["trd"][t]) or tb["up_o"][t] or not np.isfinite(o_t) or o_t <= 0:
                            k_ = "halt_in" if not tb["trd"][t] else "limit_up"
                            tr_stats[k_] += 1; _rec(row, k_, t)
                            if _nx is not None and _nx["lots"]:
                                _nx["blocked"] += 1                   # seq3 乙二：待買不消耗，配給下一檔可買的或繼續等
                            continue                                      # ⭐ 不遞補：名額今天持現金
                    _nx_buy = _nx is not None and bool(_nx["lots"])      # seq3 乙二 ②：待買先配給挑中的前幾檔  # _NX_WHO
                    _nx_gen = None
                    if _nx_buy and _nx_after:            # seq192 D1：一般新部位優先，只用一般現金（現金 − 待買）
                        _nx_gen = cash - sum(a_ for a_, _ in _nx["lots"])
                        _nx_buy = not (len(open_pos) < ns_t and min(slot, _nx_gen) > 1e-9)   # _NXAFTER_WHO
                    if _nx_buy:
                        amt, _nx_t = _nx["lots"].pop(0)                  # seq3 乙二 ③：全額  # _NX_AMT
                        if _nxk is not None and len(open_pos) >= ns_t:
                            _nx["over"] += 1                             # seq186：超過一般容量的那幾檔（第 9、10 檔）
                        _nx["n"] += 1; _nx["amt"] += amt; _nx["waits"].append(t - _nx_t)
                    elif targets is None:
                        amt = min(slot, cash if _nx_gen is None else _nx_gen)   # _NXAFTER_GEN
                        if amt <= 1e-9:
                            rest = list(take[j:]) + rest; break
                        if _x_big is not None:       # ⓒ 1.5 slot
                            if cash >= _x_big:
                                amt = _x_big
                            else:
                                _xc["mult_short"] += 1
                                if _xm_short == "partial":
                                    amt = min(_x_big, cash)
                    else:
                        amt = min(float(targets[j]), cash)
                        if not np.isfinite(amt) or amt <= 1e-9:
                            _rec(row, "nocap", t); continue      # ⭐ 這一檔沒得買（沒市值／沒現金）⇒ ⛔ 不連累後面的候選
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
                    if audit is not None:
                        audit.append({"t": t, "sid": row["sid"], "side": "buy", "amt": float(amt), "px": ep,
                                      "target_w": (float(amt) / _eq_prev) if _eq_prev > 0 else float("nan"),
                                      "equity_prev": _eq_prev, "cost": 0.0})
                        if _nx_buy:
                            audit[-1]["kind"] = "nx"             # seq3 乙二：待買買進的（一般新部位沒有 kind，照舊）
                    if _xs is not None:              # PREREGP9 seq8：登記部位狀態
                        _xs[row["sid"]] = {"t0": t, "slot0": _x_full, "tr": 0, "add": 0, "trim": 0,
                                           "rt": "half" if (regime_trim is not None and _x_bl) else "full"}
                        if not _nx_buy:              # seq3 乙二：x_new_n／m̄ 只數一般新部位
                            _xc["new_n"] += 1; _xc["mult_nom"] += _x_nom; _xc["mult_act"] += amt / _x_full
                            if _x_nom != 1.0:
                                _xc["mult_n"] += 1
                    if stop is not None:
                        entry_day[row["sid"]] = t
                    if stop_line is not None:
                        sl_key[row["sid"]] = (row["sid"], int(row["entry_pos"]))
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
            w_t, sid_t = max(((amt * float(closes[sid][t]) / ep) / equity[t], sid) for _, sid, amt, _, ep in open_pos)
            max_pos_frac = max(max_pos_frac, w_t)
            if maxw_daily is not None:
                maxw_daily[t] = w_t; maxw_sid[t] = sid_t
        _eq_prev = equity[t]
        t_done = t
        if return_equity:
            hold_val[t] = hv          # PREREGP3 丙（時點隨機對照）要的逐日持股市值；⛔ 只在 return_equity 時記，數值路徑不變
    end = min(ncal, last + 2)
    if tradable is not None:
        end = max(end, t_done + 1)          # 延後出場把模擬尾巴往後拉
    equity[:first] = 1.0; equity[end:] = equity[end - 1]
    years = (end - first) / 245; final = equity[end - 1]
    peak = np.maximum.accumulate(equity); mdd = float(((equity - peak) / peak).min())
    cap_sum = (end - first) * n_slots if caps is None else int(caps[first:end].sum())
    out = {"cagr": final ** (1 / years) - 1, "mdd": mdd, "trades": trades, "slot_use": used / cap_sum, "first": first, "end": end,
           "m": trades, "pos_frac": wins / trades if trades else np.nan, "deferred": n_deferred, "delay_med": float(np.median(delays)) if delays else np.nan, "expired": n_expired}
    if stop_line is not None:       # 裁定線 seq119 §四（⛔ stop_line is None 時這幾個鍵不存在 ⇒ 原版回傳逐位元相同）
        out.update({"sl_exits": sl_stats["sl_exits"], "sl_delayed_days": sl_stats["sl_delayed_days"], "sl_days": sl_days,
                    "sl_rate": sl_stats["sl_exits"] / trades if trades else np.nan})
        if stop_block is not None:  # 名單出場 乙（⛔ stop_block=None 時這個鍵不存在）
            out["sl_block_days"] = _sl_blk
    if stop is not None:            # PREREGP7 必報（⛔ stop is None 時這幾個鍵不存在 ⇒ 原版回傳逐位元相同）
        out["stop_exits"] = stop_exits
        out["stop_rate"] = stop_exits / trades if trades else np.nan
        out["stop_days"] = stop_days
        out["stop_max_same_day"] = max((n for _, n in stop_days), default=0)
        out["stop_cut_right_tail"] = stop_cut_right_tail
        out["hold_days_mean"] = float(np.mean(hold_days)) if hold_days else np.nan
    if report_maxw:                 # PREREGP9 §2-E③（⛔ report_maxw=False 時這個鍵不存在 ⇒ 原版回傳逐位元相同）
        out["max_pos_frac"] = max_pos_frac
        if maxw_detail:
            out["maxw_daily"] = maxw_daily; out["maxw_sid"] = maxw_sid
    if tradable is not None:        # ⛔ tradable=None 時這幾個鍵不存在 ⇒ 原版回傳逐位元相同
        out["tr_limit_up"] = tr_stats["limit_up"]; out["tr_halt_in"] = tr_stats["halt_in"]
        out["tr_exit_delayed"] = tr_stats["exit_delayed"]; out["tr_open_at_end"] = len(open_pos)
        out["tr_close_locked"] = tr_stats["close_locked"]
        if delist is not None:      # ⛔ delist=None 時這兩個鍵不存在 ⇒ 既有回傳逐位元相同
            out["tr_delist_settled"] = tr_stats["delist_settled"]; out["tr_delist_ambig"] = tr_stats["delist_ambig"]
    if _ext:                        # PREREGP9 seq8 必報（⛔ 五個參數全關時這些鍵不存在 ⇒ 原版回傳逐位元相同）
        for k_, v_ in _xc.items():
            if k_ not in ("mult_nom", "mult_act"):
                out[f"x_{k_}"] = v_
        out["x_mbar_nominal"] = _xc["mult_nom"] / _xc["new_n"] if _xc["new_n"] else np.nan   # §四① m̄（名目倍數）
        out["x_mbar_actual"] = _xc["mult_act"] / _xc["new_n"] if _xc["new_n"] else np.nan    # 實買金額 ÷ 當天 slot
        out["x_open_at_end"] = len(_xs)
        out["x_cost_days"] = sorted(_xyear_cost.items())      # (日曆位置, 當天加減碼賣出付的成本) ⇒ 呼叫端按年彙總（§四⑦）
    if _nx is not None:             # seq3 乙二（⛔ trim_proceeds=None 時這些鍵不存在 ⇒ 既有回傳逐位元相同）
        out["x_nx_n"] = _nx["n"]; out["x_nx_amt"] = _nx["amt"]; out["x_nx_waits"] = list(_nx["waits"])
        out["x_nx_full_days"] = _nx["full_days"]; out["x_nx_empty_days"] = _nx["empty_days"]; out["x_nx_blocked"] = _nx["blocked"]
        out["x_nx_pending_end"] = len(_nx["lots"]); out["x_nx_pending_amt_end"] = float(sum(a_ for a_, _ in _nx["lots"]))
        if _nxk is not None:        # seq186（⛔ nx_cap=None 時這個鍵不存在 ⇒ 與 12c39cb810 逐位元相同）
            out["x_nx_over"] = _nx["over"]
        if _nx_stop:                # 名單出場 乙（⛔ stop_proceeds=None 時這個鍵不存在）
            out["x_nx_stop_lots"] = _nx["stop_lots"]
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

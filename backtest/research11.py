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
    """訊號根 k，進場 k+1 開盤，k+H 收盤出。回傳 (exit_bar, gross) 或 None。nb ＝ k−20 之後第一個壞根。"""
    e = k + H
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


def simulate_mtm(sig: pd.DataFrame, rule: str, n_slots: int, rng, closes: dict, opens: dict, ncal: int, return_equity: bool = False):
    d = sig[["sid", "entry_pos", f"xpos_{rule}", f"g_{rule}"]].dropna()
    d = d[d[f"xpos_{rule}"] >= 0].rename(columns={f"xpos_{rule}": "exit_pos", f"g_{rule}": "gross"})
    by_entry = {k: g for k, g in d.groupby("entry_pos")}
    first, last = int(d["entry_pos"].min()), int(d["exit_pos"].max())
    equity = np.ones(ncal); cash = 1.0; open_pos = []; held = set(); trades = 0; used = 0
    for t in range(first, min(ncal, last + 2)):
        still = []
        for ex, sid, amt, gross, ep in open_pos:
            if ex <= t:
                cash += amt * (1 + gross - COST); held.discard(sid)
            else:
                still.append((ex, sid, amt, gross, ep))
        open_pos = still
        g = by_entry.get(t)
        if g is not None and len(open_pos) < n_slots:
            cand = g[~g["sid"].isin(held)]
            if len(cand):
                take = rng.permutation(len(cand))[: n_slots - len(open_pos)]
                slot = equity[t - 1] / n_slots
                for i in take:
                    row = cand.iloc[i]; amt = min(slot, cash)
                    if amt <= 1e-9:
                        break
                    cash -= amt; ep = float(opens[row["sid"]][t])   # 進場價 ＝ 進場日開盤（還原價）；市值 ＝ 收盤 ÷ 進場開盤
                    if not np.isfinite(ep) or ep <= 0:
                        ep = float(closes[row["sid"]][t])
                    open_pos.append((int(row["exit_pos"]), row["sid"], amt, float(row["gross"]), ep)); held.add(row["sid"]); trades += 1
        used += len(open_pos)
        equity[t] = cash + sum(amt * float(closes[sid][t]) / ep for _, sid, amt, _, ep in open_pos)
    equity[:first] = 1.0; end = min(ncal, last + 2); equity[end:] = equity[end - 1]
    years = (end - first) / 245; final = equity[end - 1]
    peak = np.maximum.accumulate(equity); mdd = float(((equity - peak) / peak).min())
    out = {"cagr": final ** (1 / years) - 1, "mdd": mdd, "trades": trades, "slot_use": used / ((end - first) * n_slots), "first": first, "end": end}
    if return_equity:
        out["equity"] = equity
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

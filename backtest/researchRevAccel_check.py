# -*- coding: utf-8 -*-
"""PREREG高成長加速 —— 抽樣獨立查核（回測線計算子代理）。
⭐ 獨立寫法：⛔ 不 import researchRevAccel／researchRevLimitUp／data.load_stock／research34；直接讀 csv 自己算還原價、年增、加速、可用日、母體、出場。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevAccel_check [--n 120] [--neg 80]

查：① 抽 n 筆主窗訊號：加速旗標（年增 ≥ 30、上月 ≥ 30、差 ≥ 20、營收 ＞ 0）、t0、d ＝ t0−1 有 K 棒 ∧ amt20 ≥ 5,000 萬 ∧ 非金融生技、
       E1／E2 出場位置與 0.585% 版毛報酬
    ② 抽 neg 個「加速、主窗內、但沒有訊號」的股-期：d 確實不在母體（pit_valid 不查：板期、興櫃列極少，有差照列）
輸出 backtest/resultsRevAccel/check.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsRevAccel")


def tw_dir():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    d = os.path.expanduser(f"~/rluwork/tw_{S['meta']['tw-stock-data'][:12]}/data")
    assert os.path.isdir(d), d
    return d


def calendar():
    return pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(H2D, "meta", "calendar_twse.csv"))["date"]))


def prices(sid, cal):
    raw = pd.read_csv(os.path.join(H2D, "stocks", f"{sid}.csv"), dtype=str).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"])
    raw = raw.reindex(cal)
    num = lambda k: np.array(pd.to_numeric(raw[k], errors="coerce"), dtype=float)
    o, c, amt = num("open"), num("close"), num("amount")
    o[~(o > 0)] = np.nan; c[~(c > 0)] = np.nan
    F = np.ones(len(cal))
    ap = os.path.join(H2D, "adj", f"{sid}.csv")
    if os.path.exists(ap):
        a = pd.read_csv(ap, dtype={"date": str}).sort_values("date")
        ad = pd.to_datetime(a["date"]).to_numpy(); cf = a["cum_factor"].astype(float).to_numpy()
        for k, d in enumerate(cal.to_numpy()):
            j = np.searchsorted(ad, d, side="right")
            if j < len(ad):
                F[k] = cf[j]
    return o * F, c * F, amt


def revenue(DATA):
    fs = sorted(glob.glob(os.path.join(DATA, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]) for f in fs], ignore_index=True)
    df["v"] = pd.to_numeric(df["當月營收"], errors="coerce"); df["ly"] = pd.to_numeric(df["去年當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    return {(s, p): (v, l) for s, p, v, l in zip(df["stock_id"], df["period"], df["v"], df["ly"])}, sorted(df["period"].unique())


def mplus(p, k):
    y, m = int(p[:4]), int(p[5:]); t = y * 12 + m - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def yoy(REV, sid, p):
    v, l = REV.get((sid, p), (np.nan, np.nan))
    if not (np.isfinite(v) and np.isfinite(l) and v > 0 and l > 0):
        return np.nan
    return (v / l - 1) * 100


def accel(REV, sid, p):
    v = REV.get((sid, p), (np.nan, np.nan))[0]
    y0, y1 = yoy(REV, sid, p), yoy(REV, sid, mplus(p, -1))
    return bool(np.isfinite(v) and v > 0 and np.isfinite(y0) and np.isfinite(y1) and y0 >= 30 - 1e-9 and y1 >= 30 - 1e-9 and y0 - y1 >= 20 - 1e-9)


def t0_of(p, cal):
    y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    cut = pd.Timestamp(y2, m2, 10 if p <= "2025-12" else 15)
    w = np.flatnonzero(cal > cut)
    return int(w[0]) if len(w) else None


def industry_fn(DATA):
    p = pd.read_csv(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), dtype=str)
    seg = {}
    for s, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
        seg.setdefault(s, []).append((pd.Timestamp(a) if isinstance(a, str) and a else pd.Timestamp.min, pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp.max, ind))

    def f(s, d):
        d = pd.Timestamp(d.year, d.month, 1)                     # 月初判、月內沿用（本件 A3）
        sg = sorted(seg.get(s, []), key=lambda z: z[0])
        for a, b, ind in sg:
            if a <= d <= b:
                return ind
        if sg and d > sg[-1][1]:
            return sg[-1][2]
        return None
    return f


def amt20(k, c, amt):
    b = np.flatnonzero(np.isfinite(c[:k + 1]))
    if len(b) < 20:
        return np.nan
    return float(np.nanmean(amt[b[-20:]]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=120); ap.add_argument("--neg", type=int, default=80)
    a = ap.parse_args()
    DATA = tw_dir(); cal = calendar(); n = len(cal)
    REV, P0 = revenue(DATA); IND = industry_fn(DATA)
    S = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str, "M": str})
    rng = np.random.default_rng(20261013)
    cache = {}

    def px(s):
        if s not in cache:
            cache[s] = prices(s, cal)
        return cache[s]
    diffs = []; checked = 0
    for i in sorted(rng.choice(len(S), min(a.n, len(S)), replace=False).tolist()):
        r = S.iloc[i]; sid = r["sid"]; M = r["M"]
        o, c, amt = px(sid)
        bad = []
        if not accel(REV, sid, M):
            bad.append("加速旗標")
        t0 = t0_of(M, cal)
        if t0 != int(r["t0"]) or t0 != int(r["e"]) or t0 - 1 != int(r["d"]):
            bad.append(f"t0 {t0}≠{r['t0']}")
        d = t0 - 1
        if not (np.isfinite(c[d]) and amt20(d, c, amt) >= 5e7 and IND(sid, cal[d]) not in ("金融保險", "生技醫療業")):
            bad.append("母體")
        if abs(yoy(REV, sid, M) - float(r["Y"])) > 1e-8 * max(1.0, abs(float(r["Y"]))):        # signals.csv 存 10 位有效數字 ⇒ 相對容差
            bad.append("年增值")
        e = t0
        okb = np.flatnonzero(np.isfinite(c) & np.isfinite(o))
        nxt = lambda x: int(okb[np.searchsorted(okb, x)]) if np.searchsorted(okb, x) < len(okb) else None
        cf = pd.Series(c).ffill().to_numpy()
        rm = np.maximum.accumulate(cf[e:]); w = np.flatnonzero(cf[e:] <= rm * 0.8 + 1e-12)
        x2 = nxt(e + int(w[0]) + 1) if len(w) and e + int(w[0]) + 1 < n else None
        x1 = None
        for k in range(1, 400):
            M2 = mplus(M, k)
            if M2 > P0[-1]:
                break
            t = t0_of(M2, cal)
            if t is None:
                break
            if t <= e:
                continue
            y0, y1 = yoy(REV, sid, M2), yoy(REV, sid, mplus(M2, -1))
            if (not np.isfinite(y0)) or y0 < 30 - 1e-9 or (np.isfinite(y1) and y0 - y1 <= -20 + 1e-9):
                x1 = nxt(t); break
        for nm, x in (("E1", x1), ("E2", x2)):
            want = r[f"{nm}_xpos"]
            if x is None:
                if int(want) != n:
                    bad.append(f"{nm} 未完≠{want}")
            else:
                g = o[x] / o[e] - 1
                if int(want) != x or abs(g - float(r[f"{nm}_g"])) > 1e-6:
                    bad.append(f"{nm} x {x}≠{want} g {g:.6f}≠{float(r[f'{nm}_g']):.6f}")
        checked += 1
        if bad:
            diffs.append({"sid": sid, "M": M, "不同": bad})
    # ② 反例
    have = set(zip(S["sid"], S["M"]))
    sids = sorted({p[0] for p in REV}); sids = [s for s in sids if len(s) == 4 and s.isdigit() and s[0] != "0" and not s.startswith("91")]
    pers = [p for p in P0 if "2017-02" <= p <= "2026-07"]
    negd = []; negc = 0; tries = 0
    while negc < a.neg and tries < 200000:
        tries += 1
        sid = sids[int(rng.integers(len(sids)))]; M = pers[int(rng.integers(len(pers)))]
        if (sid, M) in have or not accel(REV, sid, M):
            continue
        t0 = t0_of(M, cal)
        if t0 is None or not (pd.Timestamp("2017-03-02") <= cal[t0] <= pd.Timestamp("2026-08-24")):
            continue
        if not os.path.exists(os.path.join(H2D, "stocks", f"{sid}.csv")):
            negc += 1; continue
        o, c, amt = px(sid); d = t0 - 1
        negc += 1
        if np.isfinite(c[d]) and amt20(d, c, amt) >= 5e7 and IND(sid, cal[d]) not in ("金融保險", "生技醫療業") and np.isfinite(o[t0]):
            negd.append({"sid": sid, "M": M, "d": str(cal[d].date()), "amt20": amt20(d, c, amt)})
    res = {"抽樣訊號": checked, "不同": len(diffs), "明細": diffs[:30], "反例（加速無訊號）抽": negc, "反例不同": len(negd), "反例明細": negd[:30]}
    res["結論"] = f"抽 {checked} 筆訊號、{negc} 個加速無訊號股-期，獨立重算 {len(diffs) + len(negd)} 筆不同"
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()

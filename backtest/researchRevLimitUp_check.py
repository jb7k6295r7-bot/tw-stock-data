# -*- coding: utf-8 -*-
"""PREREG好營收再加漲停 seq2 —— 抽樣獨立查核（回測線計算子代理）。
⭐ 獨立寫法：⛔ 不 import researchRevLimitUp、data.load_stock、research34、p4_features；直接讀 csv 自己算還原價、可用日、24 月新高、漲停、出場。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevLimitUp_check [--n 80] [--neg 60]

查：① 抽 n 筆訊號：好營收旗標、t0、d 是窗內第一個「有 K 棒 ∧ amt20 ≥ 5,000 萬 ∧ 漲停 ∧ 非金融生技」的日子、漲停判定（官方／備援）、E1／E2 出場位置與 0.585% 版毛報酬
    ② 抽 neg 個「好營收、窗內沒有訊號」的股-期：窗內確實沒有符合的日子（pit_valid 不查：板期、興櫃列極少，有差照列）
輸出 backtest/resultsRevLimitUp/check.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd

H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsRevLimitUp")


def tw_dir():
    ds = sorted(glob.glob(os.path.expanduser("~/rluwork/tw_*/data")))
    assert len(ds) >= 1
    return ds[-1]


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
    return o * F, c * F, c, amt


def revenue(DATA):
    fs = sorted(glob.glob(os.path.join(DATA, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs], ignore_index=True)
    df["v"] = pd.to_numeric(df["當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    return {(s, p): v for s, p, v in zip(df["stock_id"], df["period"], df["v"])}, sorted(df["period"].unique())


def mplus(p, k):
    y, m = int(p[:4]), int(p[5:]); t = y * 12 + m - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def good(REV, P0, sid, p):
    v = REV.get((sid, p), np.nan)
    if not np.isfinite(v):
        return np.nan
    hist = [REV.get((sid, mplus(p, -k)), np.nan) for k in range(1, 24)]
    own = [q for q in P0 if np.isfinite(REV.get((sid, q), np.nan))]
    first = own[0] if own else None
    if first is not None and first != P0[0] and first > mplus(p, -23):
        return 0.0
    h = [x for x in hist if np.isfinite(x)]
    if mplus(p, -23) < P0[0] or len(h) < 18:
        return np.nan
    return 1.0 if v > max(h) else 0.0


def t0_of(p, cal):
    y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    day = 10 if p <= "2025-12" else 15
    cut = pd.Timestamp(y2, m2, day)
    k = int(np.flatnonzero(cal > cut)[0]) if (cal > cut).any() else None
    return k


def industry_fn(DATA):
    p = pd.read_csv(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), dtype=str)
    seg = {}
    for s, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
        seg.setdefault(s, []).append((pd.Timestamp(a) if isinstance(a, str) and a else pd.Timestamp.min, pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp.max, ind))

    def f(s, d):
        for a, b, ind in seg.get(s, []):
            if a <= d <= b:
                return ind
        return None
    return f


def exright(DATA):
    out = {}
    for f in sorted(glob.glob(os.path.join(DATA, "universe", "exright", "*.csv"))):
        x = pd.read_csv(f, dtype=str)
        for s, d, lu in zip(x["stock_id"], x["date"], x["limit_up"]):
            try:
                out[(s.strip(), d.strip())] = float(lu)
            except (TypeError, ValueError):
                pass
    return out


def is_lu(sid, k, cal, c_adj, c_raw, EXR):
    if not np.isfinite(c_adj[k]):
        return False, None
    lu = EXR.get((sid, str(cal[k].date())))
    if lu is not None and lu < 9999:
        return bool(c_raw[k] >= lu - 1e-6), "官方"
    prev = np.flatnonzero(np.isfinite(c_adj[:k]))
    if not len(prev):
        return False, "備援"
    thr = 0.065 if cal[k] < pd.Timestamp("2015-06-01") else 0.095
    return bool(c_adj[k] / c_adj[prev[-1]] - 1 >= thr - 1e-12), "備援"


def amt20(k, c_adj, amt):
    b = np.flatnonzero(np.isfinite(c_adj[:k + 1]))
    if len(b) < 20:
        return np.nan
    return float(np.nanmean(amt[b[-20:]]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=80); ap.add_argument("--neg", type=int, default=60)
    a = ap.parse_args()
    DATA = tw_dir(); cal = calendar(); n = len(cal)
    REV, P0 = revenue(DATA); IND = industry_fn(DATA); EXR = exright(DATA)
    S = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str, "M": str})
    rng = np.random.default_rng(20261012)
    diffs = []; checked = 0; nof = 0
    cache = {}

    def px(s):
        if s not in cache:
            cache[s] = prices(s, cal)
        return cache[s]
    pick = sorted(set(rng.choice(len(S), min(a.n, len(S)), replace=False).tolist()) | set(np.flatnonzero(S["官方可判"].to_numpy(bool)).tolist()))   # 官方判定的訊號全查
    for i in pick:
        r = S.iloc[i]; sid = r["sid"]; M = r["M"]
        o, c, cr, amt = px(sid)
        bad = []
        if good(REV, P0, sid, M) != 1.0:
            bad.append("好營收")
        t0 = t0_of(M, cal)
        if t0 != int(r["t0"]):
            bad.append(f"t0 {t0}≠{r['t0']}")
        first = None
        for k in range(t0, min(t0 + 20, n - 1)):
            lu, how = is_lu(sid, k, cal, c, cr, EXR)
            ind = IND(sid, cal[k])
            if lu and np.isfinite(c[k]) and amt20(k, c, amt) >= 5e7 and ind not in ("金融保險", "生技醫療業"):
                first = (k, how); break
        if first is None or first[0] != int(r["d"]):
            bad.append(f"d {first}≠{r['d']}")
        else:
            nof += first[1] == "官方"
            if (first[1] == "官方") != bool(r["官方可判"]):
                bad.append("官方可判")
        e = int(r["d"]) + 1
        if e != int(r["e"]):
            bad.append("e")
        okb = np.flatnonzero(np.isfinite(c) & np.isfinite(o))
        nxt = lambda x: int(okb[np.searchsorted(okb, x)]) if np.searchsorted(okb, x) < len(okb) else None
        # E2
        cf = pd.Series(c).ffill().to_numpy()
        rm = np.maximum.accumulate(cf[e:]); w = np.flatnonzero(cf[e:] <= rm * 0.8 + 1e-12)
        x2 = nxt(e + int(w[0]) + 1) if len(w) and e + int(w[0]) + 1 < n else None
        # E1
        x1 = None
        for k in range(1, 400):
            M2 = mplus(M, k)
            t = t0_of(M2, cal) if M2 <= P0[-1] or True else None
            if t is None:
                break
            if t <= e:
                continue
            if good(REV, P0, sid, M2) != 1.0:
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
            diffs.append({"sid": sid, "M": M, "d": str(cal[int(r['d'])].date()), "不同": bad})
    # ② 反例：好營收但沒訊號
    have = set(zip(S["sid"], S["M"]))
    sids = sorted({s for s in S["sid"]})
    negd = []; negc = 0; tries = 0
    pers = [p for p in P0 if "2017-02" <= p <= "2026-06"]
    while negc < a.neg and tries < 5000:
        tries += 1
        sid = sids[int(rng.integers(len(sids)))]; M = pers[int(rng.integers(len(pers)))]
        if (sid, M) in have or good(REV, P0, sid, M) != 1.0:
            continue
        t0 = t0_of(M, cal)
        if t0 is None or t0 + 1 >= n:
            continue
        e_lo = t0 + 1
        if not (pd.Timestamp("2017-03-02") <= cal[e_lo] and cal[min(t0 + 20, n - 1)] <= pd.Timestamp("2026-08-24")):
            continue
        o, c, cr, amt = px(sid)
        hit = None
        for k in range(t0, min(t0 + 20, n - 1)):
            lu, how = is_lu(sid, k, cal, c, cr, EXR)
            if lu and np.isfinite(c[k]) and amt20(k, c, amt) >= 5e7 and IND(sid, cal[k]) not in ("金融保險", "生技醫療業"):
                hit = k; break
        negc += 1
        if hit is not None:
            negd.append({"sid": sid, "M": M, "應有訊號日": str(cal[hit].date())})
    res = {"抽樣訊號": checked, "其中官方判定": int(nof), "不同": len(diffs), "明細": diffs[:30], "反例（好營收無訊號）抽": negc, "反例不同": len(negd), "反例明細": negd[:30]}
    res["結論"] = f"抽 {checked} 筆訊號、{negc} 個無訊號股-期，獨立重算 {len(diffs) + len(negd)} 筆不同"
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()

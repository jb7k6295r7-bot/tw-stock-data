# -*- coding: utf-8 -*-
"""USREG-U 本體的【獨立路】查核。⛔ 不 import researchUSU／researchUSM*／us_data／fib_u／stop_fractal／researchU*／research11。
直接讀 ~/usdata/0043f97/data 的原始 CSV，自己還原、自己判有效 K 棒、母體、斷點：
 ① 抽 20 筆保留事件（k5_H20）：自己驗 H0 是嚴格擺動高點（左右各 5 根有效 K 棒）、L0 是 [tH−120, tH) 內 conf 時已確認的最低嚴格擺動低點（同值取晚）、
    漲幅 ≥ 20%、跨度 ≥ 10、H0 是 [tL, tH] 的頂、conf ＝ tH＋5 根；p(x)；[tH, conf] 內沒有 low ≤ p；T ＝ conf 之後第一根 low ≤ p；T 當天在母體；
    [T, T+20] 無缺日、無斷點；y（±5% 帶、閉區間、依序第一個出帶收盤）；g20 ＝ close(≤T+20)／close(T) − 1 ⇒ 與本體比
 ② 取 5 個 T：逐檔重算 EWc_20(T)（close 版、in_index、斷點排除）
 ③ 從逐筆檔重算 D（七位置 b 的線性組合）與月分群 CR0 SE（影響函數寫法）、n_eff ⇒ 與 body_summary.json 比
輸出：resultsUSU/body_check.json（只有最大差與計數）；明細 ~/us_work/usu/check_detail.csv。
"""
import os, sys, json, math
import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/0043f97/data")
WORK = os.path.expanduser("~/us_work/usu")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSU")
W0 = "2016-01-04"
FR = {"30": 0.30, "38.2": 0.382, "45": 0.45, "50": 0.50, "55": 0.55, "61.8": 0.618, "70": 0.70}
WD = {"38.2": 0.5, "61.8": 0.5, "30": -0.25, "45": -0.25, "55": -0.25, "70": -0.25}
_cache = {}
CAL = sorted(pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"].tolist())
POS = {d: i for i, d in enumerate(CAL)}


def src_px(src):
    if src in _cache:
        return _cache[src]
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(os.path.join(ROOT, "prices_yahoo", f + ".csv"), dtype={"date": str}); k = d["adjclose"] / d["close"]
        cols = (d["open"] * k, d["high"] * k, d["low"] * k, d["close"] * k)
    else:
        d = pd.read_csv(os.path.join(ROOT, "prices", f + ".csv"), dtype={"date": str})
        cols = (d["adjOpen"], d["adjHigh"], d["adjLow"], d["adjClose"])
    m = {dt: tuple(float(x) for x in v) for dt, *v in zip(d["date"], *cols)}
    _cache[src] = m
    return m


def tk(t):
    key = "T:" + t
    if key in _cache:
        return _cache[key]
    pn = pd.read_csv(os.path.join(ROOT, "panel", t + ".csv"), dtype=str, keep_default_na=False)
    bars, mem, brk = {}, set(), set(); prev = None
    for dt, ii, s in zip(pn["date"], pn["in_index"], pn["src"]):
        star = s.endswith("*"); s0 = s.rstrip("*")
        if dt not in POS:
            continue
        i = POS[dt]
        if ii == "1":
            mem.add(i)
        if star or (prev is not None and s0 != prev):
            brk.add(i)
        prev = s0
        v = src_px(s0).get(dt)
        if v is not None and all(math.isfinite(x) and x > 0 for x in v) and v[2] <= min(v[0], v[3]) and max(v[0], v[3]) <= v[1]:
            bars[i] = v
    r = {"bars": bars, "mem": mem, "brk": brk, "seq": sorted(bars)}
    _cache[key] = r
    return r


def close_le(E, j):
    while j >= 0 and j not in E["bars"]:
        j -= 1
    return E["bars"][j][3]


def strict_ext(x, i, k, hi):
    if i - k < 0 or i + k >= len(x):
        return False
    return all((x[i] > x[j]) if hi else (x[i] < x[j]) for j in range(i - k, i + k + 1) if j != i)


def check_event(E, r):
    seq = E["seq"]; ix = {p: q for q, p in enumerate(seq)}
    H = [E["bars"][p][1] for p in seq]; L = [E["bars"][p][2] for p in seq]; C = [E["bars"][p][3] for p in seq]
    tH, tL, conf, T = ix[POS[r["tH_date"]]], ix[POS[r["tL_date"]]], ix[POS[r["conf_date"]]], POS[r["T_date"]]
    ok = strict_ext(H, tH, 5, True) and conf == tH + 5
    lows = [s for s in range(max(0, tH - 120), tH) if strict_ext(L, s, 5, False) and s + 5 <= conf]
    mn = min(L[s] for s in lows); tl2 = max(s for s in lows if L[s] == mn)
    ok &= tl2 == tL and (H[tH] - L[tL]) / L[tL] >= 0.2 - 1e-12 and tH - tL >= 10 and all(H[q] <= H[tH] for q in range(tL, tH + 1))
    p = H[tH] - FR[r["pos"]] * (H[tH] - L[tL])
    ok &= abs(p - float(r["p"])) < 1e-9 * p
    ok &= all(L[q] > p for q in range(tH, conf + 1))
    bT = ix[T]; ok &= L[bT] <= p and all(L[q] > p for q in range(conf + 1, bT))
    ok &= T in E["mem"]
    lo_, hi_ = T, min(T + 20, E["seq"][-1])
    ok &= all(j in E["bars"] for j in range(lo_, hi_ + 1)) and not any(j in E["brk"] for j in range(T, T + 21))
    y = -1
    for j in range(T, T + 21):
        if j in E["bars"]:
            v = E["bars"][j][3]
            if v > p * 1.05:
                y = 1; break
            if v < p * 0.95:
                y = 0; break
    g = close_le(E, T + 20) / E["bars"][T][3] - 1
    return ok, y, g


def main():
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    rng = np.random.default_rng(20260927)
    Ev = pd.read_csv(os.path.join(WORK, "events_body_k5_H20.csv"), dtype={"sid": str, "pos": str})
    det = []; res = {}
    bad = 0; ydiff = 0; gd = 0.0
    days = set()
    for i in rng.choice(len(Ev), 20, replace=False):
        r = Ev.iloc[int(i)]
        ok, y, g = check_event(tk(r["sid"]), r)
        bad += int(not ok); ydiff += int(y != int(r["y"])); gd = max(gd, abs(g - float(r["g20"])))
        days.add((POS[r["T_date"]], float(r["EWc"])))
        det.append({"查核": "①", "sid": r["sid"], "pos": r["pos"], "T": r["T_date"], "幾何母體斷點": ok, "y同": y == int(r["y"]), "g差": abs(g - float(r["g20"]))})
    res["①事件"] = {"筆數": 20, "幾何／母體／斷點不符": bad, "y不同": ydiff, "g20最大差": gd}
    print("① 20 筆：幾何／母體／斷點不符 {}｜y 不同 {}｜g20 最大差 {:.1e}".format(bad, ydiff, gd), flush=True)
    tickers = sorted(f[:-4] for f in os.listdir(os.path.join(ROOT, "panel")) if f.endswith(".csv") and not f.startswith("_"))
    me = 0.0; ne = 0
    for d, v in sorted(days)[:5]:
        tot = k = 0
        for t in tickers:
            E = tk(t)
            if d not in E["mem"] or d not in E["bars"] or any(x in E["brk"] for x in range(d + 1, d + 21)):
                continue
            tot += close_le(E, d + 20) / E["bars"][d][3] - 1; k += 1
        me = max(me, abs(tot / k - v)); ne += 1
        det.append({"查核": "②", "T": CAL[d], "差": abs(tot / k - v), "成分數": k})
    res["②EWc"] = {"天數": ne, "最大差": me}
    print("② EWc {} 天最大差 {:.1e}".format(ne, me), flush=True)
    d = Ev[Ev["y"] >= 0]
    b = {p: d.loc[d["pos"] == p, "y"].mean() for p in WD}; nx = {p: int((d["pos"] == p).sum()) for p in WD}
    D = sum(WD[p] * b[p] for p in WD)
    infl = np.zeros(len(d))
    for q, (p, y) in enumerate(zip(d["pos"], d["y"])):
        if p in WD:
            infl[q] = WD[p] * (y - b[p]) / nx[p]
    se = math.sqrt(float((pd.Series(infl).groupby(d["mon"].to_numpy()).sum() ** 2).sum()))
    J = S["判定格"]
    w0 = POS[W0]; cap = S["區段上限"]
    neff = min(min(nx[p], len(set(np.minimum((np.array([POS[x] for x in d.loc[d["pos"] == p, "T_date"]]) - w0) // 20, cap - 1)))) for p in WD)
    dd = max(abs(D - J["D"]), abs(se - J["se_月"]), abs(D - 1.96 * se - J["lo_月"]), abs(D + 1.96 * se - J["hi_月"]))
    res["③判定格重算"] = {"D": D, "se": se, "與本體最大差": dd, "n_eff": neff, "n_eff相同": bool(neff == J["n_eff"])}
    print("③ D {:+.5f} se {:.5f}｜與本體最大差 {:.1e}｜n_eff {}（本體 {}）".format(D, se, dd, neff, J["n_eff"]), flush=True)
    pd.DataFrame(det).to_csv(os.path.join(WORK, "check_detail.csv"), index=False)
    allok = bad == 0 and ydiff == 0 and gd < 1e-12 and me < 1e-12 and dd < 1e-12 and neff == J["n_eff"]
    res["全部通過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "body_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if allok else "⛔ 有不符", flush=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()

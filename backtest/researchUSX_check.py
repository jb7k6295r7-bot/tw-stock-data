# -*- coding: utf-8 -*-
"""USREG-X 本體的【獨立路】查核。⛔ 不 import researchUSX／researchUSM*／us_data／patterns_x／patterns／trendline_m／research11。
直接讀 ~/usdata/0043f97/data 的原始 CSV（還原、有效 K 棒、母體、斷點的判法同 researchUSM_check.py，但本檔自己寫一份）：
 ① 甲 每型抽 ≤ 4 筆（共 ≤ 20）：自己算 c[T]、目標距離、事件 H60 達成（(T, T+60] 還原 high 最大 ≥ 目標）、對照股 c[T] 與 H60 達成、d_60；
    另驗 事件與對照 T 當天都在母體、對照 ≠ 事件股
 ② 乙 抽 20 筆：R ＝ close(≤ S+20 最後一根)／open(S+1) − 1；另取 5 個 S+1 日逐檔重算 EW20（close 出場版）
 ③ 11 格重算：甲 H60 的 d_60 平均、月分群 CR0 SE、95% CI、60 日區段數；乙 X 的同一組（20 日區段）⇒ 與 body_summary.json 比
 ④ 幾何：W 底、頭肩底各抽 6 筆，從自己的有效 K 棒序列驗 取點是 k＝3 局部低點、門檻、A／頸線、突破根是第一個收盤越過、60 根視窗、目標算式；
    旗形 抽 6 筆驗旗桿 ≥ 30%（20 根內）、旗面 5～25 根、回檔 5～20%、斜率 ≤ 0、收斂、突破、目標。
輸出：resultsUSX/body_check.json（只有最大差與計數）；明細 ~/us_work/usx/check_detail.csv（repo 外）。
"""
import os, sys, json, math
import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/0043f97/data")
WORK = os.path.expanduser("~/us_work/usx")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSX")
COST = 0.0005
W0 = "2016-01-04"
_cache = {}
CAL = sorted(pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"].tolist())
POS = {d: i for i, d in enumerate(CAL)}


def src_px(src):
    if src in _cache:
        return _cache[src]
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(os.path.join(ROOT, "prices_yahoo", f + ".csv"), dtype={"date": str})
        k = d["adjclose"] / d["close"]
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
        if v is None:
            continue
        o, h, l, c = v
        if all(math.isfinite(x) and x > 0 for x in v) and l <= min(o, c) and max(o, c) <= h:
            bars[i] = v
    r = {"bars": bars, "mem": mem, "brk": brk, "seq": sorted(bars)}
    _cache[key] = r
    return r


def close_le(T, j):
    b = T["bars"]
    while j >= 0 and j not in b:
        j -= 1
    return b[j][3]


def hit(T, a, H, tgt):
    hs = [T["bars"][j][1] for j in range(a + 1, a + H + 1) if j in T["bars"]]
    return int(bool(hs) and max(hs) >= tgt)


def cl(x, months):
    x = np.asarray(x, float); n = len(x); m = x.mean(); d = x - m
    s = pd.Series(d).groupby(np.asarray(months)).sum().to_numpy()
    se = math.sqrt(float((s ** 2).sum())) / n
    return m, se, m - 1.96 * se, m + 1.96 * se


def locext(c, i, k=3, kind="L"):
    if i - k < 0 or i + k >= len(c):
        return False
    w = c[i - k:i + k + 1]
    return c[i] <= min(w) if kind == "L" else c[i] >= max(w)


def geo_w(T, r):
    seq = T["seq"]; ix = {p: q for q, p in enumerate(seq)}; c = [T["bars"][p][3] for p in seq]
    p = json.loads(r["pts"]); L1, L2, A = ix[POS[p["L1"]]], ix[POS[p["L2"]]], ix[POS[p["A"]]]; b = ix[POS[r["date"]]]
    ok = locext(c, L1) and locext(c, L2) and L2 - L1 >= 5
    ok &= abs(c[L1] - c[L2]) / c[L1] <= 0.05
    m = min(c[L1], c[L2]); ok &= A == L1 + int(np.argmax(c[L1:L2 + 1])) and (c[A] - m) / m >= 0.10
    ok &= b >= L2 + 3 and c[b] > c[A] and all(c[q] <= c[A] for q in range(L2 + 3, b)) and b - L1 + 1 <= 60
    ok &= abs(float(r["target"]) - (c[A] + (c[A] - m))) < 1e-9 * c[A]
    return ok


def geo_hs(T, r):
    seq = T["seq"]; ix = {p: q for q, p in enumerate(seq)}; c = [T["bars"][p][3] for p in seq]
    p = json.loads(r["pts"]); L, H, R = ix[POS[p["L"]]], ix[POS[p["H"]]], ix[POS[p["R"]]]; b = ix[POS[r["date"]]]
    ok = all(locext(c, q) for q in (L, H, R)) and H - L >= 5 and R - H >= 5
    ok &= c[H] < c[L] and c[H] < c[R] and abs(c[L] - c[R]) / c[H] <= 0.05
    neck = (max(c[L:H + 1]) + max(c[H:R + 1])) / 2.0
    ok &= (neck - c[H]) / neck >= 0.10
    ok &= b >= R + 3 and c[b] > neck and all(c[q] <= neck for q in range(R + 3, b)) and b - L + 1 <= 60
    ok &= abs(float(r["target"]) - (neck + (neck - c[H]))) < 1e-9 * neck
    return ok


def geo_flag(T, r):
    seq = T["seq"]; ix = {p: q for q, p in enumerate(seq)}; c = np.array([T["bars"][p][3] for p in seq])
    p = json.loads(r["pts"]); E, S0 = ix[POS[p["E"]]], ix[POS[p["S0"]]]; b = ix[POS[r["date"]]]
    ok = locext(list(c), E, kind="H") and S0 == E - 20 + int(np.argmin(c[E - 20:E])) and c[E] / c[S0] - 1 >= 0.30
    F = c[E + 1:b]; mlen = len(F)
    ok &= 5 <= mlen <= 25 and 0.05 <= (c[E] - F.min()) / c[E] <= 0.20
    x = np.arange(mlen) - (mlen - 1) / 2.0
    ok &= float((x * (F - F.mean())).sum()) <= 0
    h1 = int(math.ceil(mlen / 2.0)); ok &= (F[h1:].max() - F[h1:].min()) <= (F[:h1].max() - F[:h1].min())
    ok &= c[b] > F.max() and all(c[q] <= c[E] for q in range(E + 1, b))
    ok &= abs(float(r["target"]) - (F.max() + (c[E] - c[S0]))) < 1e-9 * c[E]
    return ok


def main():
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    rng = np.random.default_rng(20260927)
    tickers = sorted(f[:-4] for f in os.listdir(os.path.join(ROOT, "panel")) if f.endswith(".csv") and not f.startswith("_"))
    det = []; res = {}
    TA = ("box", "cup", "w", "hs", "flag"); TB = ("box", "cup", "w", "hs", "flag", "trend")
    A = {t: pd.read_csv(os.path.join(WORK, f"A_{t}.csv.gz"), dtype={"sid": str, "ctl": str}) for t in TA}
    B = {t: pd.read_csv(os.path.join(WORK, f"B_{t}.csv.gz"), dtype={"sid": str}) for t in TB}
    w0 = POS[W0]
    # ①
    md = 0.0; bad = 0; n1 = 0
    for typ in TA:
        X = A[typ]
        if len(X) == 0:
            continue
        for i in rng.choice(len(X), min(4, len(X)), replace=False):
            r = X.iloc[int(i)]; T = POS[r["date"]]; E = tk(r["sid"]); C_ = tk(r["ctl"])
            cT = E["bars"][T][3]; dist = float(r["target"]) / cT - 1
            s60 = hit(E, T, 60, float(r["target"])); ctgt = C_["bars"][T][3] * (1 + dist); c60 = hit(C_, T, 60, ctgt)
            d = abs(cT - float(r["c_T"])) / cT + abs(dist - float(r["dist"])) + abs(s60 - int(r["sig_60"])) + abs(c60 - int(r["ctl_60"]))
            pop = T in E["mem"] and T in C_["mem"] and r["sid"] != r["ctl"] and (T + 1) in E["bars"] and (T + 1) in C_["bars"]
            md = max(md, d); bad += int(not pop); n1 += 1
            det.append({"查核": "①", "型": typ, "sid": r["sid"], "T": r["date"], "差": d, "母體": pop})
    res["①甲"] = {"筆數": n1, "最大差（c_T 相對差＋距離差＋兩個達成旗標差）": md, "母體不符": bad}
    print("① 甲 {} 筆 最大差 {:.2e}；母體不符 {}".format(n1, md, bad), flush=True)
    # ②
    mr = 0.0; n2 = 0; days = set(); allB = pd.concat([B[t].assign(型=t) for t in TB], ignore_index=True)
    for i in rng.choice(len(allB), 20, replace=False):
        r = allB.iloc[int(i)]; s = POS[r["date"]]; E = tk(r["sid"])
        R = close_le(E, s + 20) / E["bars"][s + 1][0] - 1
        mr = max(mr, abs(R - float(r["R"]))); n2 += 1; days.add((s + 1, float(r["EW"])))
        det.append({"查核": "②", "型": r["型"], "sid": r["sid"], "T": r["date"], "差": abs(R - float(r["R"]))})
    me = 0.0; ne = 0
    for d, ewv in sorted(days)[:5]:
        tot = k = 0
        for t in tickers:
            E = tk(t)
            if d not in E["mem"] or d not in E["bars"] or any(x in E["brk"] for x in range(d + 1, d + 20)):
                continue
            tot += close_le(E, d + 19) / E["bars"][d][0] - 1; k += 1
        me = max(me, abs(tot / k - ewv)); ne += 1
        det.append({"查核": "②EW", "T": CAL[d], "差": abs(tot / k - ewv), "成分數": k})
    res["②乙"] = {"R筆數": n2, "R最大差": mr, "EW天數": ne, "EW最大差": me}
    print("② 乙 R {} 筆最大差 {:.2e}｜EW {} 天最大差 {:.2e}".format(n2, mr, ne, me), flush=True)
    # ③
    mc = 0.0; same = True; rec = {}
    for typ in TA:
        X = A[typ]; J = S["甲"][typ]["H60（判定）"]
        if len(X) == 0:
            continue
        m, se, lo, hi = cl(X["d_60"].to_numpy(float), X["month"].to_numpy())
        blk = len(set((np.array([POS[d] for d in X["date"]]) - w0) // 60))
        dd = max(abs(m - J["D"]), abs(se - J["se_月"]), abs(lo - J["lo"]), abs(hi - J["hi"])); mc = max(mc, dd)
        same &= (len(X) == J["n"] and blk == J["區段數"]); rec["甲_" + typ] = {"差": dd, "n": len(X), "區段": blk}
    for typ in TB:
        X = B[typ]; J = S["乙"][typ]["判定"]
        m, se, lo, hi = cl(X["X"].to_numpy(float), X["month"].to_numpy())
        blk = len(set((np.array([POS[d] for d in X["date"]]) - w0) // 20))
        dd = max(abs(m - J["D"]), abs(se - J["se_月"]), abs(lo - J["lo"]), abs(hi - J["hi"])); mc = max(mc, dd)
        same &= (len(X) == J["n"] and blk == J["區段數"]); rec["乙_" + typ] = {"差": dd, "n": len(X), "區段": blk}
    res["③11格重算"] = {"最大差": mc, "筆數區段相同": bool(same), "逐格": rec}
    print("③ 11 格重算最大差 {:.2e}；筆數區段相同 {}".format(mc, same), flush=True)
    # ④
    g = {}
    for typ, fn in (("w", geo_w), ("hs", geo_hs), ("flag", geo_flag)):
        X = A[typ]; ok = 0; k = min(6, len(X))
        for i in rng.choice(len(X), k, replace=False):
            r = X.iloc[int(i)]
            try:
                v = bool(fn(tk(r["sid"]), r))
            except Exception as ex:
                v = False; print("  ④ 例外", typ, repr(ex))
            ok += int(v); det.append({"查核": "④", "型": typ, "sid": r["sid"], "T": r["date"], "通過": v})
        g[typ] = {"抽": k, "通過": ok}
    res["④幾何"] = g
    print("④ 幾何 {}".format(g), flush=True)
    pd.DataFrame(det).to_csv(os.path.join(WORK, "check_detail.csv"), index=False)
    allok = (md < 1e-12 and bad == 0 and mr < 1e-12 and me < 1e-12 and mc < 1e-12 and same and all(v["通過"] == v["抽"] for v in g.values()))
    res["全部通過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "body_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if allok else "⛔ 有不符", flush=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()

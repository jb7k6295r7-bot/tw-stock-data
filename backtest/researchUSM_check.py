# -*- coding: utf-8 -*-
"""USREG-M 本體的【獨立路】查核。⛔ 不 import researchUSM／researchUSM_body／us_data／trendline_m／researchM／stop_fractal／research11。
直接讀釘住的快照 ~/usdata/0043f97/data 的原始 CSV，自己做還原、自己判有效 K 棒、自己判母體：
   還原：yahoo ⇒ X × adjclose ÷ close；tiingo ⇒ adjOpen／adjHigh／adjLow／adjClose；取面板每一列 src（去掉 *）那個檔的同日列
   有效 K 棒：四價有限、> 0、low ≤ min(開,收)、max(開,收) ≤ high；日曆 ＝ macro/yahoo_GSPC.csv 的日期
   斷點：面板 src 帶 *（同日拆股＋配息）、或相鄰兩列 src 不同（來源接縫）
   母體：面板該日 in_index＝1
① 抽 21 筆保留事件（甲乙丙各 7）：R_e ＝ px(T+21)／open(T+1) − 1 − 0.05%（px：有效且開盤 > 0 ⇒ 開盤；否則往回最後一根有效收盤），與主程式比；
   另驗 T 當天在母體、[最早取點, T+21] 內每個交易日（首末 K 棒之間）都有有效 K 棒且無斷點、T+1 有 K 棒
② 取 5 個不同的 T+1：逐檔迴圈（全部有面板的檔）算 EW20，與主程式 ew20.csv 比；
③ 從事件檔用自己的算式重算三格：平均、月分群 CR0 SE 與 95% CI、20 日區段數、n_eff，與 body_summary.json 比；
④ 幾何：甲 12、乙 6 筆保留事件，從自己的有效 K 棒序列驗兩（三）個取點是【嚴格】樞紐（左右各 5 根）、遞降、確認根＝最後取點＋5、
   跨度 ≤ 120、有效期 ≤ 60、實體不穿、確認後到 T−1 沒有新樞紐確認、收盤突破；乙 第三點 ≤ 2%；丙 6 筆以 polyfit 驗斜率、R²、突破。
輸出：resultsUSM/body_check.json（只有最大差與計數）；逐筆明細 ~/us_work/usm/body/check_detail.csv（repo 外）。
"""
import os, sys, json, math
import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/0043f97/data")
WORK = os.path.expanduser("~/us_work/usm/body")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSM")
COST = 0.0005
W0, W1 = "2016-01-04", "2026-08-31"
_cache = {}


def calendar():
    d = pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"]
    return sorted(d.tolist())


CAL = calendar()
POS = {d: i for i, d in enumerate(CAL)}


def src_px(src):
    if src in _cache:
        return _cache[src]
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(os.path.join(ROOT, "prices_yahoo", f + ".csv"), dtype={"date": str})
        k = d["adjclose"] / d["close"]
        o, h, l, c = d["open"] * k, d["high"] * k, d["low"] * k, d["close"] * k
    else:
        d = pd.read_csv(os.path.join(ROOT, "prices", f + ".csv"), dtype={"date": str})
        o, h, l, c = d["adjOpen"], d["adjHigh"], d["adjLow"], d["adjClose"]
    m = {}
    for dt, a, b, cc, e in zip(d["date"], o, h, l, c):
        m[dt] = (float(a), float(b), float(cc), float(e))
    _cache[src] = m
    return m


def ticker(t):
    """→ dict：bars（日曆位置 → (o,h,l,c)）、mem（日曆位置集合）、brk（日曆位置集合：該根與前一根不可相連）。"""
    key = "T:" + t
    if key in _cache:
        return _cache[key]
    p = os.path.join(ROOT, "panel", t + ".csv")
    pn = pd.read_csv(p, dtype=str, keep_default_na=False)
    bars, mem, brk = {}, set(), set()
    prev_src = None
    for dt, ii, s in zip(pn["date"], pn["in_index"], pn["src"]):
        star = s.endswith("*"); s0 = s.rstrip("*")
        if dt not in POS:
            continue
        i = POS[dt]
        if ii == "1":
            mem.add(i)
        if star or (prev_src is not None and s0 != prev_src):
            brk.add(i)
        prev_src = s0
        v = src_px(s0).get(dt)
        if v is None:
            continue
        o, h, l, c = v
        if all(math.isfinite(x) and x > 0 for x in v) and l <= min(o, c) and max(o, c) <= h:
            bars[i] = v
    r = {"bars": bars, "mem": mem, "brk": brk, "first": min(bars) if bars else None, "last": max(bars) if bars else None}
    _cache[key] = r
    return r


def px(tk, j):
    b = tk["bars"]
    if j in b and b[j][0] > 0:
        return b[j][0], False
    jj = j
    while jj >= 0 and jj not in b:
        jj -= 1
    return b[jj][3], True


def ew20(d, tickers):
    tot = k = 0
    for t in tickers:
        tk = ticker(t)
        if d not in tk["mem"] or d not in tk["bars"]:
            continue
        if any(x in tk["brk"] for x in range(d + 1, d + 21)):
            continue
        e, _ = px(tk, d + 20)
        tot += e / tk["bars"][d][0] - 1.0; k += 1
    return tot / k, k


def cl(x, months):
    x = np.asarray(x, float); n = len(x); m = x.mean(); d = x - m
    s = pd.Series(d).groupby(np.asarray(months)).sum().to_numpy()
    se = math.sqrt(float((s ** 2).sum())) / n
    return m, se, m - 1.96 * se, m + 1.96 * se


def pivots(H, R=5):
    n = len(H); out = []
    for s in range(R, n - R):
        if all(H[s] > H[s - k] for k in range(1, R + 1)) and all(H[s] > H[s + k] for k in range(1, R + 1)):
            out.append(s)
    return out


def geo_check(tk, row, meth):
    """row：events_X 列（T、first、anchors、conf、T_bar 等）。回 (ok, 理由)。"""
    seq = sorted(tk["bars"]); ix = {p: k for k, p in enumerate(seq)}
    O = [tk["bars"][p][0] for p in seq]; H = [tk["bars"][p][1] for p in seq]; C = [tk["bars"][p][3] for p in seq]
    T = POS[row["T_date"]]; b = ix[T]
    if meth == "丙":
        N = 60; y = np.array(C[b - N:b]); x = np.arange(N, dtype=float)
        sl, ic = np.polyfit(x, y, 1)
        r2 = 1 - ((y - (sl * x + ic)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        ok = sl < 0 and r2 >= 0.5 and C[b] > sl * N + ic and C[b - 1] <= sl * (N - 1) + ic and seq[b - N] == POS[row["first_date"]]
        return ok, "slope={:.3g} r2={:.3f}".format(sl, r2)
    anc = [ix[POS[a]] for a in row["anchors_dates"]]
    piv = pivots(H)
    ps = set(piv)
    if not all(a in ps for a in anc):
        return False, "取點不是嚴格樞紐"
    if not all(H[anc[k]] > H[anc[k + 1]] for k in range(len(anc) - 1)):
        return False, "非遞降"
    conf = anc[-1] + 5
    if seq[conf] != POS[row["conf_date"]]:
        return False, "確認根不符"
    before = [p for p in piv if p + 5 <= conf]
    if before[-len(anc):] != anc:
        return False, "取點不是確認時最近的樞紐"
    if any(conf < p + 5 <= b - 1 for p in piv):
        return False, "確認後到 T−1 有新樞紐確認（線應被換掉）"
    p1, p2 = anc[0], anc[1]; slope = (H[p2] - H[p1]) / (p2 - p1)
    line = lambda j: H[p1] + slope * (j - p1)
    if conf - p1 > 120 or b - conf > 60 or b - conf < 1:
        return False, "期限"
    for j in range(p1, anc[-1] + 1):
        if j in (p1, p2):
            continue
        if max(O[j], C[j]) > line(j):
            return False, "實體穿線"
    if meth == "乙":
        l3 = line(anc[2])
        if not (l3 > 0 and abs(H[anc[2]] - l3) / l3 <= 0.02):
            return False, "第三點"
    if not (C[b] > line(b) and C[b - 1] <= line(b - 1)):
        return False, "未收盤突破"
    return True, "ok"


def main():
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    rng = np.random.default_rng(20260927)
    tickers = sorted(f[:-4] for f in os.listdir(os.path.join(ROOT, "panel")) if f.endswith(".csv") and not f.startswith("_"))
    det = []; res = {"①R_e": {}, "②EW20": {}, "③三格重算": {}, "④幾何": {}}
    w0 = POS[W0]
    ev = {m: pd.read_csv(os.path.join(WORK, "events_X_{}.csv".format(m)), dtype={"sid": str}) for m in ("甲", "乙", "丙")}
    # ①
    maxd = 0.0; bad_pop = 0; n1 = 0; days = set()
    for m in ("甲", "乙", "丙"):
        E = ev[m]
        for i in rng.choice(len(E), 7, replace=False):
            r = E.iloc[int(i)]; tk = ticker(r["sid"]); T = POS[r["T_date"]]; first = POS[r["T_date"]] - (int(r["T"]) - int(r["first"]))
            P0 = tk["bars"][T + 1][0]; ex, fb = px(tk, T + 21)
            R = ex / P0 - 1 - COST
            ok_pop = T in tk["mem"] and T in tk["bars"] and (T + 1) in tk["bars"]
            lo, hi = max(first, tk["first"]), min(T + 21, tk["last"])
            ok_brk = all((j in tk["bars"]) for j in range(lo, hi + 1)) and not any(j in tk["brk"] for j in range(first, T + 22))
            bad_pop += int(not (ok_pop and ok_brk)); n1 += 1
            d_ = abs(R - float(r["R"])); maxd = max(maxd, d_); days.add(T + 1)
            det.append({"查核": "①", "畫法": m, "sid": r["sid"], "T": r["T_date"], "R_本體": float(r["R"]), "R_獨立": R, "差": d_,
                        "母體與斷點": bool(ok_pop and ok_brk), "EW_本體": float(r["EW"])})
    res["①R_e"] = {"筆數": n1, "R_e最大差": maxd, "母體／斷點／T+1 不符筆數": bad_pop}
    print("① R_e {} 筆最大差 {:.2e}；母體／斷點不符 {}".format(n1, maxd, bad_pop), flush=True)
    # ②
    ew = pd.read_csv(os.path.join(WORK, "ew20.csv"), dtype={"date": str}).set_index("date")
    maxe = 0.0; ne = 0
    for d in sorted(days)[:5]:
        v, k = ew20(d, tickers)
        b = float(ew.loc[CAL[d], "EW20"]); maxe = max(maxe, abs(v - b)); ne += 1
        det.append({"查核": "②", "T": CAL[d], "EW_本體": b, "EW_獨立": v, "差": abs(v - b), "成分數_獨立": k, "成分數_本體": int(ew.loc[CAL[d], "n_members"])})
    res["②EW20"] = {"天數": ne, "最大差": maxe}
    print("② EW20 {} 天最大差 {:.2e}".format(ne, maxe), flush=True)
    # ③
    md = 0.0
    for m in ("甲", "乙", "丙"):
        E = ev[m]; Tp = [POS[d] for d in E["T_date"]]
        mo = [d[:7] for d in E["T_date"]]
        mean, se, lo, hi = cl(E["X"].to_numpy(), mo)
        blk = len(set(min((t - w0) // 20, S["區段上限"] - 1) for t in Tp))
        J = S["判定三格"][m]
        dd = max(abs(mean - J["平均"]), abs(se - J["se_月"]), abs(lo - J["lo"]), abs(hi - J["hi"]))
        same_n = (len(E) == J["n"]) and (blk == J["區段數"]) and (min(len(E), blk) == J["n_eff"])
        md = max(md, dd)
        res["③三格重算"][m] = {"n": len(E), "區段": blk, "n_eff": min(len(E), blk), "與本體最大差": dd, "筆數區段相同": bool(same_n)}
    res["③三格重算"]["最大差"] = md
    print("③ 三格重算最大差 {:.2e}；{}".format(md, {m: res["③三格重算"][m]["筆數區段相同"] for m in ("甲", "乙", "丙")}), flush=True)
    # ④
    for m, k in (("甲", 12), ("乙", 6), ("丙", 6)):
        E = ev[m]; ok = 0; why = {}
        for i in rng.choice(len(E), k, replace=False):
            r = E.iloc[int(i)].to_dict()
            if m != "丙":
                r["anchors_dates"] = str(r["anchors_dates"]).split("|")
            g, w = geo_check(ticker(r["sid"]), r, m)
            ok += int(g); why[w] = why.get(w, 0) + 1 if not g else why.get(w, 0)
            det.append({"查核": "④", "畫法": m, "sid": r["sid"], "T": r["T_date"], "通過": g, "說明": w})
        res["④幾何"][m] = {"抽": k, "通過": ok}
    print("④ 幾何 {}".format(res["④幾何"]), flush=True)
    pd.DataFrame(det).to_csv(os.path.join(WORK, "check_detail.csv"), index=False)
    allok = (res["①R_e"]["R_e最大差"] < 1e-12 and res["①R_e"]["母體／斷點／T+1 不符筆數"] == 0 and res["②EW20"]["最大差"] < 1e-12
             and md < 1e-12 and all(res["③三格重算"][m]["筆數區段相同"] for m in ("甲", "乙", "丙"))
             and all(v["通過"] == v["抽"] for v in res["④幾何"].values()))
    res["全部通過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "body_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if allok else "⛔ 有不符", flush=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()

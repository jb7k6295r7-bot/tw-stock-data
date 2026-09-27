# -*- coding: utf-8 -*-
"""researchRev 的獨立查核（⛔ 不 import researchRev；指標與訊號用逐根迴圈另寫）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchRev_check.py [--n 80]

① 大盤：自己接 0050（主快照＋早年 data/early 釘 3edc0e2206），逐根迴圈重寫 TD9／KD 背離／MACD 背離／RSI／爆量長影／60 日線／上升線跌破
   ⇒ 主窗、合併 20、T＋1 開盤有效 ⇒ 原版基準日清單 對 events_market.csv（逐筆）；R20／R60 逐筆重算
② 大盤格：從自己重算的報酬重算 基準、X、CI（20 日區段 CR0、Bonferroni z）、出口、判定、成功率 ⇒ 對 cells.csv
③ 個股基準：從 stock_days.csv.gz 自己排十分位（每天橫斷面、同值依代號序）⇒ 對 dec 欄；(月, 分位) 平均 ⇒ 對 stock_base2.csv
④ 個股格：從 stock_rows.csv.gz ＋自己的基準重算 X、CI（月 CR0、Bonferroni）、判定 ⇒ 對 cells.csv
⑤ 個股逐檔：抽 n 檔，逐根迴圈重偵測 TD9／RSI／60 日線／爆量長影／上升線跌破，套窗、母體月、合併 20、剔除
   ⇒ 對 stock_rows.csv.gz 的同檔同訊號（狀態與 R20 逐筆）
"""
from __future__ import annotations
import argparse, io, json, math, os, subprocess, sys
from statistics import NormalDist
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                      # 只用資料讀取（快照）、brk
import researchM_freq as MF                  # 只用 _g5
D, TR = H2.D, H2.TR
OUT = os.path.expanduser("~/tw-p17/backtest/resultsRev")
DB = os.path.expanduser("~/tw-stock-data")
W0, W1, E0, E1 = "2017-03-02", "2026-08-24", "2004-02-11", "2016-12-30"
SIMPLE = ["H_TD", "L_TD", "H_KD", "L_KD", "H_MACD", "L_MACD", "H_RSI", "L_RSI", "H_VS", "L_VS", "H_MA", "L_MA", "H_TL"]
STOCK_SIMPLE = ["H_TD", "L_TD", "H_RSI", "L_RSI", "H_MA", "L_MA", "H_VS", "L_VS", "H_TL"]
HIGH = {"H_M", "H_TD", "H_KD", "H_MACD", "H_RSI", "H_VS", "H_EVE", "H_ENG", "H_TL", "H_MA"}


# ───────── 逐根迴圈指標
def loop_kd(h, l, c):
    n = len(c); K = [math.nan] * n; k = 50.0; d = 50.0
    for t in range(8, n):
        hh = max(h[t - 8:t + 1]); ll = min(l[t - 8:t + 1])
        rsv = 50.0 if hh == ll else (c[t] - ll) / (hh - ll) * 100.0
        k = k * 2.0 / 3.0 + rsv / 3.0; d = d * 2.0 / 3.0 + k / 3.0; K[t] = k
    return K


def loop_ema(c, span):
    a = 2.0 / (span + 1); e = c[0]; out = [e]
    for x in c[1:]:
        e = (1 - a) * e + a * x; out.append(e)
    return out


def loop_dif(c):
    e12, e26 = loop_ema(c, 12), loop_ema(c, 26)
    return [math.nan if t < 25 else e12[t] - e26[t] for t in range(len(c))]


def loop_rsi(c, n=14):
    m = len(c); out = [math.nan] * m
    if m <= n:
        return out
    g = [max(c[i] - c[i - 1], 0.0) for i in range(1, m)]; lo = [max(c[i - 1] - c[i], 0.0) for i in range(1, m)]
    ag = sum(g[:n]) / n; al = sum(lo[:n]) / n
    for t in range(n, m):
        if t > n:
            ag = (ag * (n - 1) + g[t - 1]) / n; al = (al * (n - 1) + lo[t - 1]) / n
        out[t] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def fractal(x, k, low):
    n = len(x); out = []
    for s in range(k, n - k):
        nb = list(x[s - k:s]) + list(x[s + 1:s + k + 1])
        if (low and all(x[s] < y for y in nb)) or ((not low) and all(x[s] > y for y in nb)):
            out.append(s)
    return out


def loop_div(h, l, ind, top):
    piv = fractal(h, 2, False) if top else fractal(l, 2, True)
    ev = []
    for a, b in zip(piv[:-1], piv[1:]):
        if b + 2 >= len(h) or not (math.isfinite(ind[a]) and math.isfinite(ind[b])):
            continue
        if (top and h[b] > h[a] and ind[b] < ind[a]) or ((not top) and l[b] < l[a] and ind[b] > ind[a]):
            ev.append(b + 2)
    return ev


def loop_signals(o, h, l, c, v, codes):
    n = len(c); ev = {k: [] for k in codes}
    run_u = run_d = 0
    K = loop_kd(h, l, c) if {"H_KD", "L_KD"} & set(codes) else None
    DIF = loop_dif(list(c)) if {"H_MACD", "L_MACD"} & set(codes) else None
    R = loop_rsi(list(c))
    MA = [math.nan] * n
    for t in range(59, n):
        MA[t] = math.fsum(c[t - 59:t + 1]) / 60
    for t in range(n):
        up = t >= 4 and c[t] > c[t - 4]; dn = t >= 4 and c[t] < c[t - 4]
        run_u = run_u + 1 if up else 0; run_d = run_d + 1 if dn else 0
        if run_u == 9 and "H_TD" in ev: ev["H_TD"].append(t)
        if run_d == 9 and "L_TD" in ev: ev["L_TD"].append(t)
        if t >= 1 and math.isfinite(R[t - 1]) and math.isfinite(R[t]):
            if R[t - 1] > 70 and R[t] < 70 and "H_RSI" in ev: ev["H_RSI"].append(t)
            if R[t - 1] < 30 and R[t] > 30 and "L_RSI" in ev: ev["L_RSI"].append(t)
        if t >= 1 and math.isfinite(MA[t - 1]):
            if c[t] < MA[t] and c[t - 1] >= MA[t - 1] and "H_MA" in ev: ev["H_MA"].append(t)
            if c[t] > MA[t] and c[t - 1] <= MA[t - 1] and "L_MA" in ev: ev["L_MA"].append(t)
        if t >= 20:
            vm = sum(v[t - 20:t]) / 20
            body = abs(c[t] - o[t])
            if vm > 0 and v[t] > 2 * vm:
                U = h[t] - max(o[t], c[t]); Dn = min(o[t], c[t]) - l[t]
                if U > 0 and U >= 2 * body and h[t] >= max(h[t - 19:t + 1]) and "H_VS" in ev: ev["H_VS"].append(t)
                if Dn > 0 and Dn >= 2 * body and l[t] <= min(l[t - 19:t + 1]) and "L_VS" in ev: ev["L_VS"].append(t)
    if K is not None:
        ev["H_KD"] = loop_div(h, l, K, True); ev["L_KD"] = loop_div(h, l, K, False)
    if DIF is not None:
        ev["H_MACD"] = loop_div(h, l, DIF, True); ev["L_MACD"] = loop_div(h, l, DIF, False)
    if "H_TL" in ev:
        tl = loop_upline(o, l, c)
        ev["H_TL"] = [t for t, _ in tl]; ev["_TLF"] = {t: f for t, f in tl}
    return ev


def loop_upline(o, l, c, R=5):
    """上升線跌破：最近兩個已確認樞紐低點（左右各 5 根嚴格）、遞升、跨度 ≤ 120、中間實體底不低於線；線自確認日起 ≤ 60 根；
    收盤 ＜ 線 × 99/100 且前一根 ≥ 線(前一根) × 99/100。"""
    n = len(c); piv = fractal(l, R, True); conf = {s + R: s for s in piv}
    got = []; line = None; hist = []
    for b in range(n):
        if line is not None:
            p1, l1, sl, cf = line
            if b - cf > 60:
                line = None
            else:
                lvb = l1 + sl * (b - p1); lvp = l1 + sl * (b - 1 - p1)
                if b >= 1 and c[b] < lvb * 99 / 100.0 and c[b - 1] >= lvp * 99 / 100.0:
                    got.append((b, p1)); line = None
        if b in conf:
            hist.append(conf[b]); line = None
            if len(hist) >= 2:
                p1, p2 = hist[-2], hist[-1]
                if l[p2] > l[p1]:
                    sl = (l[p2] - l[p1]) / (p2 - p1)
                    if sl > 0 and b - p1 <= 120:
                        ok = all(not (min(o[j], c[j]) < l[p1] + sl * (j - p1)) for j in range(p1 + 1, p2))
                        if ok:
                            line = (p1, l[p1], sl, b)
    return got


def merge(Ts):
    out = []; t0 = -10 ** 9
    for t in Ts:
        if not (t0 < t <= t0 + 20):
            out.append(t); t0 = t
    return out


# ───────── 0050
def git(*a):
    return subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True, check=True).stdout


def m0050():
    cal = D.load_calendar()
    df = D.load_stock("0050", "twse", cal).df
    main = {k: df[kk].to_numpy(float) for k, kk in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"), ("v", "volume"))}
    main["dates"] = [str(x.date()) for x in cal]
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", "0050.csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")
    fb = int(np.flatnonzero(np.isfinite(main["c"]))[0])
    s = main["c"][fb] / float(raw.loc[main["dates"][fb], "close"])
    rows = git("grep", "-h", "_0050,", "3edc0e2206", "--", "data/early/daily/")
    E = pd.read_csv(io.StringIO(rows), header=None, dtype=str).iloc[:, [1, 2, 5, 6, 7, 8, 9]]
    E.columns = ["date", "sid", "o", "h", "l", "c", "v"]
    E = E[(E["sid"] == "0050") & (E["date"] < main["dates"][fb])].copy()
    for k in "ohlcv":
        E[k] = pd.to_numeric(E[k], errors="coerce")
    E = E[E["c"].notna() & (E["c"] > 0)].sort_values("date").drop_duplicates("date")
    ex = git("grep", "-h", ",0050,", "3edc0e2206", "--", "data/early/exright/")
    X = pd.read_csv(io.StringIO(ex), header=None, dtype=str)
    X = X[X[1] == "0050"]
    fac = [(r[0], float(r[3]) / float(r[2])) for r in X.itertuples(index=False)]
    F = np.array([np.prod([f for dd, f in fac if dd > d]) for d in E["date"]])
    spl = {"dates": list(E["date"]) + main["dates"]}
    for k in "ohlc":
        spl[k] = np.concatenate([E[k].to_numpy(float) * F * s, main[k]])
    spl["v"] = np.concatenate([E["v"].to_numpy(float), main["v"]])
    return main, spl


def series_events(X, codes):
    b = np.flatnonzero(np.isfinite(X["c"]))
    arr = {k: [float(x) for x in np.asarray(X[k])[b]] for k in "ohlcv"}
    ev = loop_signals(arr["o"], arr["h"], arr["l"], arr["c"], arr["v"], codes)
    return {k: [int(b[t]) for t in v] for k, v in ev.items() if not k.startswith("_")}, b


def lastvalid(c, i):
    while not np.isfinite(c[i]):
        i -= 1
    return i


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    tot = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, math.sqrt(float((tot ** 2).sum())) / n, len(tot)


def judge(x, g, z, high):
    m, se, ng = cr0(x, g); ne = min(len(x), ng)
    if ne < 10:
        return {"n_eff": ne, "判定": "不可判定", "mean": m}
    lo, hi = m - z * se, m + z * se
    if ne < 30:
        ex, rs = "出口①", "—（樣本不足以分辨）"
    else:
        ex = "出口②" if ne < 100 else "出口③"
        rs = "結果①" if lo <= 0 <= hi else ("結果③" if m < 0 else "結果②")
    ok = rs == ("結果③" if high else "結果②")
    return {"n_eff": ne, "mean": m, "lo": lo, "hi": hi, "出口": ex, "結果": rs, "判定": "通過" if ok else "不通過"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=80); ap.add_argument("--out", default=OUT); a = ap.parse_args()
    OUT_ = a.out
    errs = []; info = {}
    C = pd.read_csv(os.path.join(OUT_, "cells.csv")); S = json.load(open(os.path.join(OUT_, "summary.json"), encoding="utf-8"))
    EM = pd.read_csv(os.path.join(OUT_, "events_market.csv"))
    # ① 大盤事件與報酬
    main_, spl = m0050()
    cm = {}
    for seg, X, a0, a1 in (("主窗", main_, W0, W1), ("早年", spl, E0, E1)):
        lo = X["dates"].index(a0); hi = X["dates"].index(a1)
        ev, b = series_events(X, SIMPLE)
        valid = np.isfinite(X["c"])
        Rs = {}
        for code in SIMPLE:
            T = merge([t for t in ev[code] if lo <= t <= hi - 20])
            T = [t for t in T if np.isfinite(X["o"][t + 1])]
            mine = [X["dates"][t] for t in T]
            got = EM[(EM["段"] == seg) & (EM["code"] == code) & (EM["版"] == "原版")]["基準日"].tolist()
            if mine != got:
                errs.append(f"大盤 {seg} {code} 事件不一致：自己 {len(mine)} 筆、檔 {len(got)} 筆；前幾個差 {sorted(set(mine) ^ set(got))[:4]}")
            r = [X["c"][lastvalid(X["c"], t + 20)] / X["o"][t + 1] - 1 for t in T]
            fr = EM[(EM["段"] == seg) & (EM["code"] == code) & (EM["版"] == "原版")]["R20"].to_numpy(float)
            if len(r) == len(fr) and len(r) and np.max(np.abs(np.array(r) - fr)) > 1e-12:
                errs.append(f"大盤 {seg} {code} R20 不一致")
            Rs[code] = (np.array(r), np.array(T))
        bd = [d for d in range(lo, hi - 19) if valid[d] and np.isfinite(X["o"][d + 1])]
        base = np.array([X["c"][lastvalid(X["c"], d + 20)] / X["o"][d + 1] - 1 for d in bd])
        bk = S[f"大盤基準_{seg}"]
        if abs(bk["R20平均"] - base.mean()) > 1e-12 or bk["日數"] != len(base):
            errs.append(f"大盤 {seg} 基準不一致")
        cm[seg] = (Rs, base, lo)
        info[f"大盤_{seg}_比對訊號"] = len(SIMPLE)
    # ② 大盤格（全部訊號，用 events_market 的報酬；簡單訊號的報酬已在 ① 對過）
    zM = NormalDist().inv_cdf(1 - (0.05 / S["Bonferroni_大盤"]["k"]) / 2)
    for seg in ("主窗",):
        Rs, base, lo = cm[seg]
        dates = main_["dates"]
        for r in C[(C["層"] == "大盤") & (C["段"] == seg)].itertuples():
            e = EM[(EM["段"] == seg) & (EM["code"] == r.code) & (EM["版"] == r.版)]
            x = e["R20"].to_numpy(float) - base.mean()
            g = [(dates.index(d) - lo) // 20 for d in e["基準日"]]
            if not len(x):
                continue
            j = judge(x, g, zM, r.code in HIGH)
            if j["判定"] != r.判定 or abs(j["mean"] - r.mean) > 1e-12:
                errs.append(f"大盤格 {r.code} {r.版}：判定 {j['判定']} vs 檔 {r.判定}")
            sr = float((e["R20"] < 0).mean()) if r.code in HIGH else float((e["R20"] > 0).mean())
            if abs(sr - r.成功率) > 1e-12:
                errs.append(f"大盤格 {r.code} {r.版} 成功率")
    # ③ 個股基準
    DD = pd.read_csv(os.path.join(OUT_, "stock_days.csv.gz"), dtype={"sid": str})
    dec = np.full(len(DD), -1, int)
    for d, g in DD.groupby("d"):
        ok = g[np.isfinite(g["r20p"])].sort_values(["r20p", "sid"], kind="mergesort")
        n = len(ok)
        dec[ok.index.to_numpy()] = (np.arange(n) * 10) // n
    bad = int((dec != DD["dec"].to_numpy()).sum())
    if bad:
        errs.append(f"十分位不一致 {bad} 列")
    cal = D.load_calendar(); mon = np.array([str(x)[:7] for x in cal])
    DD["m"] = mon[DD["d"].to_numpy()]
    fin = DD[np.isfinite(DD["R20"]) & (DD["dec"] >= 0)]
    B2 = fin.groupby(["m", "dec"])["R20"].mean()
    B2f = pd.read_csv(os.path.join(OUT_, "stock_base2.csv"), dtype={"m": str}).set_index(["m", "dec"])["mean"]
    dmax = float(np.nanmax(np.abs(B2.reindex(B2f.index).to_numpy() - B2f.to_numpy())))
    if dmax > 1e-12:
        errs.append(f"基準② 不一致 {dmax}")
    info["基準②格數"] = int(len(B2)); info["十分位列數"] = int(len(DD))
    # ④ 個股格
    R = pd.read_csv(os.path.join(OUT_, "stock_rows.csv.gz"), dtype={"sid": str})
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], dec)}
    zS = NormalDist().inv_cdf(1 - (0.05 / S["Bonferroni_個股"]["k"]) / 2)
    for r in C[(C["層"] == "個股")].itertuples():
        e = R[R["code"] == r.code]
        if r.版 == "原版":
            k = e[e["st"] == "保留"]; bd = k["T"].to_numpy(int); rr = k["R20"].to_numpy(float)
        else:
            k = e[e["st_c"] == "保留"]; bd = k["C"].to_numpy(int); rr = k["R20c"].to_numpy(float)
        mm = mon[bd]
        b2 = np.array([B2.get((m_, key.get((s, int(d)), -1)), np.nan) for s, d, m_ in zip(k["sid"], bd, mm)])
        ok = np.isfinite(b2)
        x = rr[ok] - b2[ok]
        if int(ok.sum()) != r.事件:
            errs.append(f"個股格 {r.code} {r.版} 事件數 {int(ok.sum())} vs {r.事件}"); continue
        j = judge(x, mm[ok], zS, r.code in HIGH)
        if j["判定"] != r.判定 or abs(j["mean"] - r.mean) > 1e-12:
            errs.append(f"個股格 {r.code} {r.版}：判定 {j['判定']} vs 檔 {r.判定}；平均 {j['mean']} vs {r.mean}")
    # ⑤ 個股逐檔
    rng = np.random.default_rng(11)
    sids = sorted(R["sid"].unique())
    pick = [sids[i] for i in rng.choice(len(sids), size=min(a.n, len(sids)), replace=False)]
    from backtest import p4_features as P4F
    p = P4F.read_panel(os.path.expanduser("~/tw-p17/backtest/resultsp4/panel.csv.gz"))
    p = p[p["eligible"].astype(bool)]
    elig = p.groupby("stock_id")["measure_date"].apply(lambda s: set(str(x)[:7] for x in s)).to_dict()
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    off = TR.load_official(); nchk = 0
    mkt = R.drop_duplicates("sid").set_index("sid")["market"]
    for sid in pick:
        st = D.load_stock(sid, mkt[sid], cal); df = st.df
        o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
        valid = np.isfinite(c); b = np.flatnonzero(valid)
        ev = loop_signals(*[[float(x) for x in arr[b]] for arr in (o, h, l, c, v)], STOCK_SIMPLE)
        tb = TR.one(sid, cal); ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
        dl = ds is not None and ds["status"].startswith("delisted")
        pb = np.zeros(len(cal), bool)
        for b_ in D.breakpoints(df, st.event_dates):
            if b_["rule"] in ("price", "price+gap"):
                pb[b_["pos"]] = True
        g5 = MF._g5(valid, upto=ds["last"]) if dl else MF._g5(valid)
        SS = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
        em = elig.get(sid, set())
        tlf = {int(b[t]): int(b[f]) for t, f in ev["_TLF"].items()}
        for code in STOCK_SIMPLE:
            T = [int(b[t]) for t in ev[code]]
            T = [t for t in T if w0 <= t <= w1 - 20 and mon[t] in em]
            T = merge(T)
            mine = []
            for t in T:
                f0 = tlf[t] if code == "H_TL" else t
                bad_ = H2.brk(SS, f0, t + 20) or (not tb["trd"][t + 1]) or (not np.isfinite(o[t + 1])) or tb["up_o"][t + 1] or tb["dn_o"][t + 1]
                if not bad_:
                    mine.append((t, c[lastvalid(c, t + 20)] / o[t + 1] - 1))
            got = R[(R["sid"] == sid) & (R["code"] == code) & (R["st"] == "保留")][["T", "R20"]]
            gl = [(int(t), float(r_)) for t, r_ in zip(got["T"], got["R20"])]
            if [t for t, _ in mine] != [t for t, _ in gl]:
                errs.append(f"個股 {sid} {code} 事件不一致：自己 {len(mine)}、檔 {len(gl)}；差 {sorted(set(t for t, _ in mine) ^ set(t for t, _ in gl))[:3]}")
            elif any(abs(x - y) > 1e-12 for (_, x), (_, y) in zip(mine, gl)):
                errs.append(f"個股 {sid} {code} R20 不一致")
            nchk += len(mine)
    info.update(個股逐檔檔數=len(pick), 個股逐檔事件=nchk, 錯誤數=len(errs))
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:25]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs[:300]}, open(os.path.join(OUT_, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()

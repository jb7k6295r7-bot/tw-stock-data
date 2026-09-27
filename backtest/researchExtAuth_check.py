# -*- coding: utf-8 -*-
"""PREREG外部作者 獨立查核（⛔ 不 import researchExtAuth；只讀它的輸出檔對數）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtAuth_check.py [--procs 2]

另走一條路重算：
 ① 偵測：七顆＋均線跌破，用另寫的程式（W1 反向回看、均線自寫 fsum、20 日均量自寫、百分位自寫）對全母體重算
    ⇒ 每格（進場 15 格 × 探索／確認／主窗）的列數、段尾未出場列、出場觸發列 ＝ pre.json 逐格相同
 ② 基本面：月營收（自讀 revenue_hist）、季財報（自讀 fin_hist、filing_dates）自寫可用日 ⇒ W2 候選數與過基本面數 ＝ pre.json
 ③ 出場三顆的有效觸發列（Y2 出、Y4 兩臂、Y5 × H × 段）＝ pre.json
 ④ 判定格的確認段列（進場日、觸發日）＝ confirm_rows_*.csv.gz 逐列相同；引擎用 confirm_rows 重建 ⇒ r＝0～2 的年化／回落 ＝ confirm_audit3.csv
 ⑤ 挑格與判定：由 cells.csv 自己套登錄挑法與判準 ⇒ ＝ summary.json；0050 主窗 ＝ P17 錨
 ⑥ 單筆層：由 se_events.csv.gz ＋ win_stock_days.csv.gz 自己算基準② 差的平均 ⇒ ＝ se_cells.csv
共用（⛔ 沒有另寫）：data.load_stock（還原價）、research11.simulate_mtm（引擎）、rerun17.load_prices／load_bench、avgdown.cr0（群聚 SE）。
"""
from __future__ import annotations
import argparse, glob, json, math, os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import p4_features as P4F
from backtest import avgdown as AV
D = H2.D
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsExtAuth")
FD = os.path.expanduser("~/msdata/b6cce05ba3b0fe4809d0c5e5c84abab8a1630f21/data")
PANEL = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "主窗": ("2017-03-02", "2026-08-24")}
_G = {}


def fma(x, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = math.fsum(x[i - n + 1:i + 1]) / n
    return out


def vm20(v):
    out = np.full(len(v), np.nan)
    for i in range(20, len(v)):
        w = v[i - 20:i]
        if np.isfinite(w).all():
            out[i] = w.sum() / 20
    return out


def detect2(o, h, l, c, v):
    nb = len(c)
    bd = np.where(o != 0, (c - o) / o, np.nan)
    LR = bd >= 0.04; LB = bd <= -0.04; SM = np.abs(bd) < 0.02
    vm = vm20(v); m5, m10, m20, m60, m250 = (fma(c, k) for k in (5, 10, 20, 60, 250))
    R = {}
    # W1：反向回看
    w1 = []
    for j in np.flatnonzero(LR):
        for k in (1, 2, 3):
            d0 = j - k - 1
            if d0 < 0:
                break
            mid = range(d0 + 1, j)
            if LR[d0] and all(SM[x] and c[x] >= l[d0] for x in mid) and c[j] > h[d0]:
                w1.append(j); break
            if not all(SM[x] for x in mid):
                break
    R["W1"] = sorted(set(w1))
    # W2 候選
    w2 = []
    bel = [bool(np.isfinite(m250[i]) and c[i] < m250[i]) for i in range(nb)]
    for s in range(61, nb):
        if not (np.isfinite(m250[s - 1]) and np.isfinite(m250[s])):
            continue
        if not (c[s - 1] <= m250[s - 1] and c[s] > m250[s]):
            continue
        if sum(bel[s - 60:s]) < 40:
            continue
        for j in range(s + 1, min(s + 10, nb - 1) + 1):
            if c[j] < m250[j]:
                break
            if c[j] < c[j - 1] and v[j] < vm[j] * 0.5:
                w2.append((s, j)); break
    R["W2c"] = w2
    # Y1
    pct = np.full(nb, np.nan)
    for p in range(250, nb):
        w = vm[p - 250:p]
        if np.isfinite(w).all():
            pct[p] = np.percentile(w, 20)
    prep = np.zeros(nb, bool)
    for p in range(29, nb):
        if np.isfinite(vm[p]) and np.isfinite(pct[p]) and vm[p] <= pct[p] and l[p - 9:p + 1].min() >= l[p - 29:p - 9].min():
            prep[p] = True
    y1 = set(); y1b = []
    for b in range(20, nb):
        if not prep[max(b - 10, 0):b].any():
            continue
        N = h[b - 20:b].max()
        if not (np.isfinite(vm[b]) and v[b] >= 2 * vm[b] and LR[b] and c[b] > N):
            continue
        rr = -1
        for r in (b + 1, b + 2):
            if r < nb and (l[r] <= max(N * 1.01, m5[r]) if np.isfinite(m5[r]) else l[r] <= N * 1.01) and c[r] >= N:
                rr = r; break
        y1b.append((b, rr))
        if rr >= 0:
            y1.add(rr)
    R["Y1"] = sorted(y1); R["Y1b"] = y1b
    # Y2
    y2i, y2o = set(), set()
    for d in range(60, nb):
        if not (c[d] >= h[d - 60:d].max() * 0.95 and np.isfinite(vm[d]) and v[d] >= 2 * vm[d] and LB[d]):
            continue
        brk = [j for j in range(d + 1, min(d + 3, nb - 1) + 1) if c[j] < l[d]]
        if brk:
            y2o.add(brk[0]); continue
        e = d + 4
        if e < nb and v[e] <= 0.5 * v[d] and c[e] > o[e] and c[e] >= (o[d] + c[d]) / 2:
            y2i.add(e)
    R["Y2in"] = sorted(y2i); R["Y2out"] = sorted(y2o)
    # Y3
    y3 = set()
    for d in range(20, nb):
        if not (np.isfinite(vm[d]) and v[d] >= 3 * vm[d] and LB[d]):
            continue
        run = 0; k = d + 1
        while k < nb and run < 3 and v[k] < v[k - 1] and l[k] >= l[d]:
            run += 1
            if run >= 2:
                e = k + 1
                if (e < nb and np.isfinite(vm[e]) and v[e] >= vm[e] and np.isfinite(m5[e - 1]) and np.isfinite(m5[e])
                        and c[e - 1] <= m5[e - 1] and c[e] > m5[e]):
                    y3.add(e); break
            k += 1
    R["Y3"] = sorted(y3)
    # Y5、跌破
    R["Y5"] = [t for t in range(5, nb) if c[t] < m20[t] and v[t] < v[t - 1] < v[t - 2] < v[t - 3] < v[t - 4] and m20[t] < m20[t - 5]]
    for k, m in ((5, m5), (10, m10), (20, m20), (60, m60)):
        R[f"MA{k}"] = [t for t in range(1, nb) if c[t - 1] >= m[t - 1] and c[t] < m[t]]
    return R


def one(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None
    df = st.df
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    b = np.flatnonzero(np.isfinite(c))
    if len(b) < 30:
        return None
    R = detect2(o[b], h[b], l[b], c[b], v[b])
    out = {}
    for k, x in R.items():
        if k == "W2c":
            out[k] = [(int(b[s]), int(b[r])) for s, r in x]
        elif k == "Y1b":
            out[k] = [(int(b[s]), int(b[r]) if r >= 0 else -1) for s, r in x]
        else:
            out[k] = np.array([int(b[t]) for t in x], int)
    return sid, out, c, b


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    t00 = time.time()
    RES = {}
    pre = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    cal = D.load_calendar(); n = len(cal); mon = np.array([str(x)[:7] for x in cal])
    P = {k: (int(np.flatnonzero(cal == pd.Timestamp(v[0]))[0]), int(np.flatnonzero(cal == pd.Timestamp(v[1]))[0])) for k, v in SEG.items()}
    U = H2.UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    p = P4F.read_panel(PANEL)
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {s: set(str(x)[:7] for x in g["measure_date"]) for s, g in p.groupby("stock_id")}
    mk = U.set_index("stock_id")["market"]
    sids = sorted(elig)
    with Pool(a.procs, initializer=lambda c_: _G.update(cal=c_), initargs=(cal,)) as pool:
        X = {r[0]: r for r in pool.imap_unordered(one, [(s, mk.get(s, "twse")) for s in sids], chunksize=4) if r is not None}
    print(f"[偵測] {len(X)} 檔｜{time.time() - t00:.0f}s", flush=True)
    # ② 基本面（自讀）
    fs = sorted(glob.glob(os.path.join(H2.H2D, "mops", "revenue_hist", "*.csv")))
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
    rv["r"] = pd.to_numeric(rv["當月營收"], errors="coerce"); rv["ly"] = pd.to_numeric(rv["去年當月營收"], errors="coerce")
    rv = rv[np.isfinite(rv["r"])]

    def avail_rev(per):
        y, m = int(per[:4]), int(per[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        return int(cal.searchsorted(pd.Timestamp(y2, m2, 10), side="right"))
    rv["av"] = rv["period"].map(avail_rev)
    rv = rv[rv["av"] < n]
    REV = {s: g.sort_values("period") for s, g in rv.groupby("stock_id")}
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "ni_q", "ni_ytd"])
                   for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv")))]).drop_duplicates(["stock_id", "period"], keep="last")
    F = F.set_index(["stock_id", "period"])
    fdt = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fdt["d"] = pd.to_datetime(fdt["uploaded_at"].str[:10], errors="coerce")
    fdt = fdt.dropna(subset=["d"]).groupby(["stock_id", "year", "season"])["d"].min().to_dict()

    def ni1(s, y, q):
        key = (s, f"{y}Q{q}")
        if key not in F.index:
            return np.nan
        a_, b_ = F.at[key, "ni_q"], F.at[key, "ni_ytd"]
        if np.isfinite(a_):
            return a_
        if q == 1:
            return b_
        k2 = (s, f"{y}Q{q - 1}")
        return b_ - F.at[k2, "ni_ytd"] if k2 in F.index else np.nan

    def avail_fin(s, y, q):
        d = fdt.get((s, y, q))
        if d is not None:
            return int(cal.searchsorted(d, side="right"))
        dl = pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, {1: 5, 2: 8, 3: 11}[q], {1: 15, 2: 14, 3: 14}[q])
        return int(cal.searchsorted(dl, side="right")) + 5
    FQ = {}
    for (s, per) in F.index:
        FQ.setdefault(s, []).append((int(per[:4]), int(per[-1])))

    def fund(s, t):
        g = REV.get(s)
        if g is not None:
            gg = g[g["av"] <= t]
            if len(gg):
                last = gg.iloc[-1]
                if np.isfinite(last["ly"]) and last["ly"] > 0 and last["r"] > last["ly"]:
                    return True
        qs = [(y, q) for y, q in FQ.get(s, []) if avail_fin(s, y, q) <= t]
        if qs:
            y, q = max(qs)
            py, pq = (y - 1, 4) if q == 1 else (y, q - 1)
            a_, b_ = ni1(s, y, q), ni1(s, py, pq)
            if (py, pq) in FQ.get(s, []) and np.isfinite(a_) and np.isfinite(b_) and a_ > 0 and b_ < 0:
                return True
        return False
    cand = 0; passed = 0
    for sid, (s_, R, c, b) in X.items():
        keep = sorted({r for s, r in R["W2c"] if fund(sid, s)})
        cand += len(R["W2c"]); passed += sum(1 for s, r in R["W2c"] if fund(sid, s))
        R["W2"] = np.array(keep, int)
    RES["② W2 基本面"] = {"候選": cand, "過基本面": passed, "pre": [pre["W2"]["候選 (s, r)"], pre["W2"]["過基本面"]],
                        "過": [cand, passed] == [pre["W2"]["候選 (s, r)"], pre["W2"]["過基本面"]]}
    print(RES["② W2 基本面"], flush=True)
    # ① 進場格列數
    bad = []
    for r in pre["進場格"]:
        code, xo = r["格"].split("|")
        for seg in ("探索", "確認", "主窗"):
            s0, s1 = P[seg]; nrow = 0; nopen = 0; ntrig = 0
            for sid, (_, R, c, b) in X.items():
                em = elig.get(sid, set())
                ent = [t for t in R[code] if s0 <= t + 1 <= s1 and mon[t] in em]
                Xd = R[xo]
                for t in ent:
                    nrow += 1
                    later = Xd[(Xd >= t + 1) & (Xd <= s1)]
                    if len(later):
                        ntrig += 1
                    else:
                        nopen += 1
            got = (nrow, nopen, ntrig); ref = (r[f"{seg}_列"], r[f"{seg}_段尾未出場列"], r[f"{seg}_出場觸發列"])
            if got != ref:
                bad.append((r["格"], seg, got, ref))
    RES["① 進場格列數"] = {"比對": len(pre["進場格"]) * 3, "不同": len(bad), "例": bad[:5], "過": not bad}
    print(RES["① 進場格列數"], flush=True)
    # ③ 出場格有效觸發（需要引擎進場價 ⇒ rerun17.load_prices）
    RR.use_snapshot()
    cz, oz = RR.load_prices(sorted(X), cal, mk, "branch")
    bad = []
    for seg in ("探索", "確認", "主窗"):
        s0, s1 = P[seg]
        base = []
        for sid, (_, R, c, b) in X.items():
            em = elig.get(sid, set())
            ts = sorted(set().union(*[set(int(t) for t in R[k]) for k in ("W1", "W2", "Y1", "Y2in", "Y3")]))
            base += [(sid, t) for t in ts if s0 <= t + 1 <= s1 and mon[t] in em]
        for H in (20, 60, 120):
            cnt = {k: 0 for k in ("Y2out", "Y4_MA5", "Y4_MA10", "Y5")}
            for sid, t in base:
                _, R, c, b = X[sid]; e = t + 1
                x = min(e + H - 1, s1 + 1); lim = min(s1, x - 2)
                if lim < e:
                    continue
                ep = float(oz[sid][e]) if (np.isfinite(oz[sid][e]) and oz[sid][e] > 0) else float(cz[sid][e])
                for k in ("Y2out", "Y5"):
                    cnt[k] += int(((R[k] >= e) & (R[k] <= lim)).any())
                bb = b[(b >= e) & (b <= lim)]
                for arm in ("MA5", "MA10"):
                    xs = set(R[arm].tolist()); hi = -np.inf; hit = False
                    for d in bb:
                        if hi >= ep * 125 / 100:
                            if d in xs:
                                hit = True; break
                        elif hi >= ep * 110 / 100 and c[d] < ep:
                            hit = True; break
                        hi = max(hi, c[d])
                    cnt[f"Y4_{arm}"] += int(hit)
            for k, v in cnt.items():
                ref = [o_ for o_ in pre["出場格"] if o_["段"] == seg and o_["格"] == f"{k}|H{H}"][0]
                if (v, len(base)) != (ref["有效觸發列"], ref["基準列"]):
                    bad.append((seg, k, H, v, ref["有效觸發列"], len(base), ref["基準列"]))
    RES["③ 出場格觸發"] = {"比對": 36, "不同": len(bad), "例": bad[:5], "過": not bad}
    print(RES["③ 出場格觸發"], flush=True)
    # ④ 判定格：確認段列與引擎
    bad = []; bad2 = []
    AU = pd.read_csv(os.path.join(OUT, "confirm_audit3.csv"))
    ncal = n
    for g, cellname in S["探索段挑格"].items():
        if "|" not in cellname:
            continue
        code, xo = cellname.split("|")
        f = os.path.join(OUT, f"confirm_rows_{g}.csv.gz")
        CR = pd.read_csv(f, dtype={"sid": str})
        s0, s1 = P["確認"]
        mine = []
        if code in ("W1", "W2", "Y1", "Y2in", "Y3"):
            for sid, (_, R, c, b) in X.items():
                em = elig.get(sid, set())
                for t in R[code]:
                    if s0 <= t + 1 <= s1 and mon[t] in em:
                        later = R[xo][(R[xo] >= t + 1) & (R[xo] <= s1)]
                        mine.append((sid, int(t) + 1, int(later[0]) if len(later) else -1))
            theirs = list(zip(CR["sid"], CR["entry_pos"].astype(int), CR["trig"].astype(int)))
            if sorted(mine) != sorted(theirs):
                bad.append((g, len(mine), len(theirs)))
        # 引擎重建
        sig = pd.DataFrame({"sid": CR["sid"], "entry_pos": CR["entry_pos"].astype(int), "xpos_X": CR["xpos"].astype(int)})
        sig["g_X"] = [float(cz[s][x]) / e_ - 1.0 for s, x, e_ in zip(sig["sid"], sig["xpos_X"], CR["ep"])]
        sl = {(s, int(e)): (int(d), np.array([np.finfo(np.float64).max])) for s, e, d in zip(CR["sid"], CR["entry_pos"], CR["trig"]) if d >= 0}
        for r in range(3):
            o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, **({"stop_line": sl} if sl else {}))
            c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
            ref = AU[(AU["cell"] == f"確認|{code}|{xo}") & (AU["r"] == r)].iloc[0]
            if abs(c_ - ref["cagr"]) > 1e-12 or abs(m_ - ref["mdd"]) > 1e-12:
                bad2.append((g, r, c_, ref["cagr"]))
    RES["④ 判定格列與引擎"] = {"列不同": bad, "引擎不同": bad2[:5], "過": not bad and not bad2}
    print(RES["④ 判定格列與引擎"], flush=True)
    # ⑤ 挑格與判定
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    bench = RR.load_bench(cal)
    Z = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    groups = {"W1": [("W1", x) for x in ("MA10", "MA20", "MA60")], "W2": [("W2", x) for x in ("MA10", "MA20", "MA60")],
              "Y1": [("Y1", x) for x in ("MA10", "MA20", "MA60")], "Y2": [("Y2in", x) for x in ("MA10", "MA20", "MA60")] + [("Y2out", f"H{H}") for H in (20, 60, 120)],
              "Y3": [("Y3", x) for x in ("MA10", "MA20", "MA60")], "Y4": [(c_, f"H{H}") for c_ in ("Y4_MA5", "Y4_MA10") for H in (20, 60, 120)],
              "Y5": [("Y5", f"H{H}") for H in (20, 60, 120)]}
    mism = []
    for g, lst in groups.items():
        ex = C[C["段"] == "探索"]
        rows = [ex[(ex["顆"] == c_) & (ex["出場／H"] == x_)].iloc[0] for c_, x_ in lst]
        rows = [r for r in rows if not (isinstance(r["剔除"], str) and r["剔除"])]
        if not rows:
            mine = "依構造不可判定（全部格被剔除）"
        else:
            z = Z["探索"]; r0 = z["cagr"] / abs(z["mdd"])
            ok = [r for r in rows if r["cagr_med"] > z["cagr"] and r["cagr_med"] / abs(r["mdd_med"]) >= r0]
            pool = ok or rows
            best = sorted(pool, key=lambda r: (-(r["cagr_med"] / abs(r["mdd_med"])), -r["cagr_med"]))[0]
            mine = f"{best['顆']}|{best['出場／H']}"
        if mine != S["探索段挑格"][g]:
            mism.append((g, mine, S["探索段挑格"][g]))
        if "|" in mine:
            c_, x_ = mine.split("|"); lab = {}
            for seg in ("確認", "主窗"):
                r = C[(C["段"] == seg) & (C["顆"] == c_) & (C["出場／H"] == x_)].iloc[0]
                z = Z[seg]
                lab[seg] = ("合格" if (r["cagr_med"] > z["cagr"] and r["cagr_med"] / abs(r["mdd_med"]) >= z["cagr"] / abs(z["mdd"]))
                            else ("另列" if r["cagr_med"] > z["cagr"] else "不合格"))
            fin = ("合格" if lab["確認"] == "合格" and lab["主窗"] == "合格" else "確認段合格、全段未過" if lab["確認"] == "合格"
                   else "另列" if lab["確認"] == "另列" and lab["主窗"] in ("合格", "另列") else "確認段另列、全段未過" if lab["確認"] == "另列" else "不合格")
            if fin != S["判定"][g]["判定"]:
                mism.append((g, fin, S["判定"][g]["判定"]))
    anchor = abs(Z["主窗"]["cagr"] - 0.24020209886370614) < 1e-12 and abs(Z["主窗"]["mdd"] + 0.3395700527611012) < 1e-12
    RES["⑤ 挑格與判定"] = {"不同": mism, "0050 主窗對錨": anchor, "過": not mism and anchor}
    print(RES["⑤ 挑格與判定"], flush=True)
    # ⑥ 單筆層
    EV = pd.read_csv(os.path.join(OUT, "se_events.csv.gz"), dtype={"sid": str})
    DD = pd.read_csv(os.path.join(HERE, "resultsRev", "win_stock_days.csv.gz"), dtype={"sid": str})
    DD["m"] = mon[DD["d"].to_numpy()]
    SEC = pd.read_csv(os.path.join(OUT, "se_cells.csv"))
    worst = 0.0
    for H in (5, 10, 20, 60):
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec"] >= 0)]
        B2 = f.groupby(["m", "dec"])[f"R{H}"].mean().rename("b2").reset_index()
        e = EV[(EV["H"] == H) & (EV["st"] == "保留")].copy()
        e["m"] = mon[e["T"].to_numpy(int)]
        e = e.merge(DD[["sid", "d", "dec"]].rename(columns={"d": "T"}), on=["sid", "T"], how="left")
        e = e.merge(B2, on=["m", "dec"], how="left")
        for code, g in e.groupby("code"):
            g = g[np.isfinite(g["b2"])]
            x = (g["R"] - g["b2"]).mean() if len(g) else np.nan
            ref = SEC[(SEC["code"] == code) & (SEC["H"] == H)]["mean"].iloc[0]
            if np.isfinite(x) or np.isfinite(ref):
                worst = max(worst, abs(x - ref) if (np.isfinite(x) and np.isfinite(ref)) else np.inf)
    RES["⑥ 單筆層差平均"] = {"最大差": float(worst), "過": bool(worst < 1e-12)}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))
    print(f"查核完成 {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()

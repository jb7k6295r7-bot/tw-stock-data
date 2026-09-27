# -*- coding: utf-8 -*-
"""PREREG外部作者追加 獨立查核（⛔ 不 import researchExtAuth2；只讀它的輸出檔對數）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtAuth2_check.py [--procs 2]

 ① 三顆偵測另寫（迴圈、自寫均線 fsum、自寫 20 日均量）⇒ F1／F1c／O1 各格三段列數與段尾未出場列、S1 六種基準出場的有效觸發 ＝ pre.json
    （S1 的基準 ＝ seq1 五顆進場任一：沿用 seq1 已獨立查核過的 researchExtAuth.detect ／ fund_ok；⛔ 本件沒有另寫）
 ② 停止交易日另寫（最後一根有效收盤 ＜ 段尾）＝ research11.stop_force_days
 ③ 判定格確認段列（進場日、觸發日）＝ confirm_rows_*.csv.gz；引擎（帶 stop_force）重建 r＝0～2 ＝ confirm_audit3.csv
 ④ 挑格（剔除後、過判準者取比值最高、都沒過取比值最高）與判定（確認段＋主窗）＝ summary.json；0050 主窗錨
 ⑤ 單筆層差平均：se_events.csv.gz ＋ win_stock_days.csv.gz 自算基準② ＝ se_cells.csv
"""
from __future__ import annotations
import argparse, json, math, os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExtAuth as EA                               # 只為 seq1 基準（已查核）
D, RR, R11 = EA.D, EA.RR, EA.R11
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsExtAuth2")
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


def det(o, h, l, c, v):
    nb = len(c); vm = vm20(v); m5, m10, m20, m60 = (fma(c, k) for k in (5, 10, 20, 60))
    R = {"F1": [], "F1c": [], "O1": [], "O1low": [], "S1": []}
    for r in range(15, nb):
        bs = (r - 3, r - 2, r - 1)
        if all(c[b] < o[b] and abs((c[b] - o[b]) / o[b]) < 0.02 for b in bs) and c[r - 4] / c[r - 14] - 1 <= -0.05 \
                and (c[r] - o[r]) / o[r] >= 0.03 and o[r] <= c[r - 1] and c[r] >= o[r - 3] and np.isfinite(vm[r]) and v[r] >= 1.5 * vm[r]:
            R["F1"].append(r)
            top = max(h[b] for b in bs)
            cf = [d for d in range(r + 1, min(r + 5, nb - 1) + 1) if c[d] > top]
            if cf and cf[0] not in R["F1c"]:
                R["F1c"].append(cf[0])
    R["F1c"] = sorted(R["F1c"])
    seen = set()
    for k in range(6, nb):
        a = k - 1
        if np.isfinite(m60[a]) and m5[a] > m10[a] > m20[a] > m60[a] and m20[a] > m20[k - 6] and c[a] >= m20[a] and c[k] < m20[k]:
            js = [j for j in range(k + 1, min(k + 3, nb - 1) + 1) if c[j] >= m20[j]]
            if js and js[0] not in seen:
                seen.add(js[0]); R["O1"].append(js[0]); R["O1low"].append(l[k])
    # S1
    both = []
    for t in range(nb):
        ok = t >= 59 and c[t] >= max(h[t - 59:t + 1]) * 0.90 and t >= 4 and np.isfinite(vm[t]) and np.mean(v[t - 4:t + 1]) < 0.7 * vm[t]
        both.append(bool(ok))
    runs = []                       # (起, 迄) 長度 ≥ 10
    t = 0
    while t < nb:
        if both[t]:
            s = t
            while t < nb and both[t]:
                t += 1
            if t - s >= 10:
                runs.append((s, t - 1))
        else:
            t += 1
    for t in range(1, nb):
        el = any((s + 9 <= t <= e) or (e + 1 <= t <= e + 5) for s, e in runs)
        if el and np.isfinite(vm[t]) and v[t] >= 1.5 * vm[t] and c[t] < c[t - 1]:
            R["S1"].append(t)
    for n_, m in ((10, m10), (20, m20), (60, m60)):
        R[f"MA{n_}"] = [t for t in range(1, nb) if c[t - 1] >= m[t - 1] and c[t] < m[t]]
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
    R = det(o[b], h[b], l[b], c[b], v[b])
    out = {k: np.array([int(b[t]) for t in x], int) for k, x in R.items() if k != "O1low"}
    out["O1low"] = np.array(R["O1low"], float)
    base = EA.stock_work((sid, mk))
    ent = np.unique(np.concatenate([np.asarray(base["S"][k], int) for k in EA.ENTRIES])) if base else np.zeros(0, int)
    return sid, out, c, b, ent


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    t00 = time.time(); RES = {}
    pre = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    cal = D.load_calendar(); n = len(cal); mon = np.array([str(x)[:7] for x in cal])
    P = {k: (int(np.flatnonzero(cal == pd.Timestamp(v[0]))[0]), int(np.flatnonzero(cal == pd.Timestamp(v[1]))[0])) for k, v in SEG.items()}
    sids, elig, mk = EA.SG.stock_universe(cal, EA.PANEL, os.path.join(EA.H2.H2D, "meta", "stocks.csv"))
    FUND, _ = EA.load_fund(cal, print)

    def init(c_, f_):
        _G.update(cal=c_); EA._init({"cal": c_, "mode": "pre", "FUND": f_})
    with Pool(a.procs, initializer=init, initargs=(cal, FUND)) as pool:
        X = {r[0]: r for r in pool.imap_unordered(one, [(s, mk.get(s, "twse")) for s in sids], chunksize=4) if r is not None}
    print(f"[偵測] {len(X)} 檔｜{time.time() - t00:.0f}s", flush=True)
    # ① 進場格
    bad = []
    for rec in pre["進場格"]:
        code, xo = rec["格"].split("|")
        for seg in ("探索", "確認", "主窗"):
            s0, s1 = P[seg]; nrow = 0; nopen = 0
            for sid, (_, R, c, b, _) in X.items():
                em = elig.get(sid, set())
                sigs = R[code]
                lows = R["O1low"] if code == "O1" else None
                for i, t in enumerate(sigs):
                    if not (s0 <= t + 1 <= s1 and mon[t] in em):
                        continue
                    nrow += 1; e = t + 1
                    if xo == "OWN":
                        bb = b[(b >= e) & (b <= s1)]
                        hit = bool(np.any(c[bb] < lows[i]))
                    else:
                        Xd = R[xo]; hit = bool(np.any((Xd >= e) & (Xd <= s1)))
                    nopen += int(not hit)
            got, ref = (nrow, nopen), (rec[f"{seg}_列"], rec[f"{seg}_段尾未出場列"])
            if got != ref:
                bad.append((rec["格"], seg, got, ref))
    RES["① 進場格列數"] = {"比對": len(pre["進場格"]) * 3, "不同": bad[:5], "過": not bad}
    print(RES["① 進場格列數"], flush=True)
    # ① S1 出場格
    RR.use_snapshot(); cz, oz = RR.load_prices(sorted(X), cal, mk, "branch")
    bad = []
    for seg in ("探索", "確認", "主窗"):
        s0, s1 = P[seg]
        base = [(sid, int(t)) for sid, (_, R, c, b, ent) in X.items() for t in ent if s0 <= t + 1 <= s1 and mon[t] in elig.get(sid, set())]
        for ex in ("H20", "H60", "H120", "MA10", "MA20", "MA60"):
            cnt = 0
            for sid, t in base:
                R = X[sid][1]; e = t + 1; s1s = R["S1"]
                if ex.startswith("H"):
                    x = min(e + int(ex[1:]) - 1, s1 + 1); lim = min(s1, x - 2)
                    cnt += int(np.any((s1s >= e) & (s1s <= lim)))
                else:
                    Xd = R[ex]; dm = Xd[(Xd >= e) & (Xd <= s1)]; ds = s1s[(s1s >= e) & (s1s <= s1)]
                    if len(ds) and (not len(dm) or ds[0] < dm[0]):
                        cnt += 1
            ref = [r for r in pre["出場格"] if r["段"] == seg and r["格"] == f"S1|{ex}"][0]
            if (cnt, len(base)) != (ref["有效觸發列"], ref["基準列"]):
                bad.append((seg, ex, cnt, ref["有效觸發列"], len(base), ref["基準列"]))
    RES["① S1 出場格觸發"] = {"比對": 18, "不同": bad[:5], "過": not bad}
    print(RES["① S1 出場格觸發"], flush=True)
    # ② 停止交易日
    valid = {sid: np.isfinite(X[sid][2]) for sid in X}
    mism = 0
    for s0, s1 in P.values():
        mine = {sid: int(np.flatnonzero(v)[-1]) for sid, v in valid.items() if np.flatnonzero(v)[-1] < s1}
        mism += int(mine != R11.stop_force_days(valid, s1))
    RES["② 停止交易日"] = {"不同段數": mism, "過": mism == 0}
    # ③ 判定格
    AU = pd.read_csv(os.path.join(OUT, "confirm_audit3.csv"))
    s0, s1 = P["確認"]; SF = R11.stop_force_days(valid, s1)
    b2 = []; b3 = []
    for g, cn in S["探索段挑格"].items():
        if "|" not in cn:
            continue
        code, xo = cn.split("|")
        CR = pd.read_csv(os.path.join(OUT, f"confirm_rows_{g}.csv.gz"), dtype={"sid": str})
        if code in ("F1", "F1c", "O1"):
            mine = []
            for sid, (_, R, c, b, _) in X.items():
                em = elig.get(sid, set())
                for i, t in enumerate(R[code]):
                    if not (s0 <= t + 1 <= s1 and mon[t] in em):
                        continue
                    e = t + 1
                    if xo == "OWN":
                        bb = b[(b >= e) & (b <= s1)]; w = bb[c[bb] < R["O1low"][i]]; d = int(w[0]) if len(w) else -1
                    else:
                        Xd = R[xo]; w = Xd[(Xd >= e) & (Xd <= s1)]; d = int(w[0]) if len(w) else -1
                    mine.append((sid, e, d))
            if sorted(mine) != sorted(zip(CR["sid"], CR["entry_pos"].astype(int), CR["trig"].astype(int))):
                b2.append((g, len(mine), len(CR)))
        sig = pd.DataFrame({"sid": CR["sid"], "entry_pos": CR["entry_pos"].astype(int), "xpos_X": CR["xpos"].astype(int)})
        sig["g_X"] = [float(cz[s][x]) / e_ - 1.0 for s, x, e_ in zip(sig["sid"], sig["xpos_X"], CR["ep"])]
        sl = {(s, int(e)): (int(d), np.array([np.finfo(np.float64).max])) for s, e, d in zip(CR["sid"], CR["entry_pos"], CR["trig"]) if d >= 0}
        for r in range(3):
            o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, n, return_equity=True, stop_force=SF, **({"stop_line": sl} if sl else {}))
            c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
            ref = AU[(AU["cell"] == f"確認|{code}|{xo}") & (AU["r"] == r)].iloc[0]
            if abs(c_ - ref["cagr"]) > 1e-12 or abs(m_ - ref["mdd"]) > 1e-12:
                b3.append((g, r, c_, ref["cagr"]))
    RES["③ 判定格列與引擎"] = {"列不同": b2, "引擎不同": b3[:5], "過": not b2 and not b3}
    print(RES["③ 判定格列與引擎"], flush=True)
    # ④ 挑格與判定
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    bench = RR.load_bench(cal); Z = {seg: RR.bench_row(cal, bench, a_, b_ + 1) for seg, (a_, b_) in P.items()}
    groups = {"F1": [(c_, x_) for c_ in ("F1", "F1c") for x_ in ("MA10", "MA20", "MA60")], "O1": [("O1", x_) for x_ in ("OWN", "MA10", "MA20", "MA60")],
              "S1": [("S1", f"H{H}") for H in (20, 60, 120)] + [("S1", x_) for x_ in ("MA10", "MA20", "MA60")]}
    mism = []
    for g, lst in groups.items():
        ex = C[C["段"] == "探索"]
        rows = [ex[(ex["顆"] == c_) & (ex["出場／H"] == x_)].iloc[0] for c_, x_ in lst]
        rows = [r for r in rows if not (isinstance(r["剔除"], str) and r["剔除"])]
        if not rows:
            mine = "依構造不可判定（全部格被剔除）"
        else:
            z = Z["探索"]; r0 = z["cagr"] / abs(z["mdd"])
            okr = [r for r in rows if r["cagr_med"] > z["cagr"] and r["cagr_med"] / abs(r["mdd_med"]) >= r0]
            best = sorted(okr or rows, key=lambda r: (-(r["cagr_med"] / abs(r["mdd_med"])), -r["cagr_med"]))[0]
            mine = f"{best['顆']}|{best['出場／H']}"
        if mine != S["探索段挑格"][g]:
            mism.append((g, mine, S["探索段挑格"][g]))
        if "|" in mine:
            c_, x_ = mine.split("|"); lab = {}
            for seg in ("確認", "主窗"):
                r = C[(C["段"] == seg) & (C["顆"] == c_) & (C["出場／H"] == x_)].iloc[0]; z = Z[seg]
                lab[seg] = "合格" if (r["cagr_med"] > z["cagr"] and r["cagr_med"] / abs(r["mdd_med"]) >= z["cagr"] / abs(z["mdd"])) else ("另列" if r["cagr_med"] > z["cagr"] else "不合格")
            fin = ("合格" if lab["確認"] == "合格" and lab["主窗"] == "合格" else "確認段合格、全段未過" if lab["確認"] == "合格"
                   else "另列" if lab["確認"] == "另列" and lab["主窗"] in ("合格", "另列") else "確認段另列、全段未過" if lab["確認"] == "另列" else "不合格")
            if fin != S["判定"][g]["判定"]:
                mism.append((g, fin, S["判定"][g]["判定"]))
    anchor = abs(Z["主窗"]["cagr"] - 0.24020209886370614) < 1e-12 and abs(Z["主窗"]["mdd"] + 0.3395700527611012) < 1e-12
    RES["④ 挑格與判定"] = {"不同": mism, "0050 主窗對錨": anchor, "過": not mism and anchor}
    # ⑤ 單筆層
    EV = pd.read_csv(os.path.join(OUT, "se_events.csv.gz"), dtype={"sid": str})
    DD = pd.read_csv(EA.WIN_DAYS_FILE, dtype={"sid": str}); DD["m"] = mon[DD["d"].to_numpy()]
    SEC = pd.read_csv(os.path.join(OUT, "se_cells.csv"))
    worst = 0.0
    for H in (5, 10, 20, 60):
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec"] >= 0)]
        B2 = f.groupby(["m", "dec"])[f"R{H}"].mean().rename("b2").reset_index()
        e = EV[(EV["H"] == H) & (EV["st"] == "保留")].copy(); e["m"] = mon[e["T"].to_numpy(int)]
        e = e.merge(DD[["sid", "d", "dec"]].rename(columns={"d": "T"}), on=["sid", "T"], how="left").merge(B2, on=["m", "dec"], how="left")
        for code, g in e.groupby("code"):
            g = g[np.isfinite(g["b2"])]
            x = (g["R"] - g["b2"]).mean() if len(g) else np.nan
            ref = SEC[(SEC["code"] == code) & (SEC["H"] == H)]["mean"].iloc[0]
            if np.isfinite(x) or np.isfinite(ref):
                worst = max(worst, abs(x - ref) if (np.isfinite(x) and np.isfinite(ref)) else np.inf)
    RES["⑤ 單筆層差平均"] = {"最大差": float(worst), "過": bool(worst < 1e-12)}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))
    print(f"查核完成 {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()

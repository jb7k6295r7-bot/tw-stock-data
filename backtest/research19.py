"""研究十九：停損位置——結構低點（A）vs 結構低點 − k×ATR（B_k）vs 固定比例安慰劑（C_k，校準同鬆緊）。判準 backtest/PREREG19.md。

    python3 -m backtest.research19 [--procs 4] [--limit N]

訊號集 ＝ results15/signals.csv.gz 主格 B3（不重新偵測訊號，只重跑 chan.detect 取回抽低點 stop 並逐筆對上 k）。
K 棒／ATR／CI：research11；閘門：research15 的旗標已在 signals 裡。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import chan as C
from . import data as D
from . import research11 as R
from . import research15 as R15

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results19")
R15DIR = os.path.join(HERE, "results15")
COST = R.COST
HOLDS = (20, 60, 120)
KS = (0.5, 1.0, 1.5, 2.0, 2.5)
_G: dict = {}


def _init(cal):
    R._init(cal); _G["cal"] = cal


def exit_with_stop(o, c, l, k, H, stop, next_bad, intraday=False):
    """進 open[k+1]；t ∈ [k+1, k+H]：收盤跌破（close < stop）⇒ open[t+1] 出（t＝k+H 或超序列 ⇒ close[t]）；
    盤中觸價版：low ≤ stop ⇒ min(open[t], stop) 當根成交。沒觸發 ⇒ close[k+H]。窗 [k+1, 出場根] 不可有壞根。回傳 (gross, stopped, exit_bar)。"""
    n = len(c); e = k + H
    if e >= n or e >= next_bad[k + 1] or not (o[k + 1] > 0):
        return np.nan, None, -1
    ep = o[k + 1]
    for t in range(k + 1, e + 1):
        if intraday:
            if l[t] <= stop:
                px = min(o[t], stop)
                return px / ep - 1, True, t
        elif c[t] < stop:
            if t + 1 <= e and t + 1 < n:
                return o[t + 1] / ep - 1, True, t + 1
            return c[t] / ep - 1, True, t
    return c[e] / ep - 1, False, e


def worker(args):
    sid, market, ks = args                      # ks: [(k, rid)]
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return [{"rid": rid, "err": "no_bars"} for _, rid in ks]
    o, c, h, l, next_bad = (B[x] for x in ("o", "c", "h", "l", "next_bad"))
    vp = R15.VARIANTS["main"]
    _, sigs = C.detect(h, l, c, pen_mode=vp["pen_mode"], zg_mode=vp["zg_mode"], n_pens=vp["n_pens"], start=0)
    stop_at = {int(s["signal_raw"]): float(s["stop"]) for s in sigs if s["kind"] == "B3"}
    atr = R.wilder_atr(h, l, c)
    out = []
    for k, rid in ks:
        if k not in stop_at or not np.isfinite(atr[k]) or k + 1 >= len(c):
            out.append({"rid": rid, "err": "no_stop" if k not in stop_at else "no_atr"}); continue
        lo = stop_at[k]; ep = o[k + 1]
        row = {"rid": rid, "lo": lo, "atr": float(atr[k]), "entry": float(ep), "distA": (ep - lo) / ep, "atr_pct": float(atr[k] / c[k])}
        for H in HOLDS:
            for mode, tag in ((False, ""), (True, "i")):
                g, st, xb = exit_with_stop(o, c, l, k, H, lo, next_bad, mode)
                row[f"A{tag}_H{H}"] = g; row[f"A{tag}_s_H{H}"] = st
                for kk in KS:
                    g, st, xb = exit_with_stop(o, c, l, k, H, lo - kk * atr[k], next_bad, mode)
                    row[f"B{kk}{tag}_H{H}"] = g; row[f"B{kk}{tag}_s_H{H}"] = st
        out.append(row)
    return out


def _p(x, d=2):
    return R._p(x, d)


def _ci(s):
    return f"{s['mean'] * 100:+.2f} pp（{s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {'測不出' if s['lo'] <= 0 <= s['hi'] else '測得出'}"


def cell(name, x, m, base_m):
    x = np.asarray(x, float); m = np.asarray(m); ok = ~np.isnan(x); x, m = x[ok], m[ok]
    if len(x) == 0:
        return f"| {name} | 0 | | | | | | | |", None
    s = R.cl_stats(x - COST, m)
    ex = x - pd.Series(m).map(base_m).to_numpy(float); se = R.cl_stats(ex, m)
    v = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
    return (f"| {name} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['p10'])} | "
            f"{se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {v} |"), se


HDR = ["| 格 | n | 平均 | 中位 | 勝率 | p10 | 超額 | 超額 月配對 CI | 統計層 |", "|---|---:|---:|---:|---:|---:|---:|---|---|"]


def calibrate_m(distA, lo, ep, target):
    """二分法求 m：median(distA + m·lo/ep) == target。"""
    a, b = 0.0, 1.0
    for _ in range(60):
        mid = (a + b) / 2
        if np.nanmedian(distA + mid * lo / ep) < target:
            a = mid
        else:
            b = mid
    return (a + b) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--limit", type=int)
    ap.add_argument("--calib-window", choices=["full", "A"], default="full", help="安慰劑 C 的 m(k) 校準母體：full＝全樣本（原版，方法論第五十二條命中）；A＝只用 A 窗 2016–2020 校準再套全部（追加）")
    ap.add_argument("--out", default=None, help="輸出目錄（追加重跑時另開，⛔ 不覆蓋 results19）")
    a = ap.parse_args()
    global RESULTS
    if a.out:
        RESULTS = a.out
    os.makedirs(RESULTS, exist_ok=True); t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe().set_index("stock_id")["market"]
    S = pd.read_csv(os.path.join(R15DIR, "signals.csv.gz"), dtype={"sid": str}, low_memory=False)
    S = S[(S["kind"] == "B3") & (S["variant"] == "main")].copy(); S["gate_all"] = S["gate_ok"] & S["liq_ok"]
    S = R15.dedup(S); S = S[S["gate_all"]].copy(); S["rid"] = np.arange(len(S))
    E = pd.read_csv(os.path.join(R15DIR, "eligible.csv.gz"), dtype={"sid": str})
    base_m = {H: E[E["liq"]].groupby("month")[f"g{H}"].mean() for H in HOLDS}
    if a.limit:
        S = S[S["sid"].isin(S["sid"].unique()[:a.limit])]
    jobs = [(sid, uni.get(sid), [(int(k), int(rid)) for k, rid in zip(g["k"], g["rid"])]) for sid, g in S.groupby("sid")]
    rows = []
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, jobs, chunksize=8)):
            rows.extend(r)
            if (i + 1) % 300 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", file=sys.stderr)
    P = pd.DataFrame(rows)
    err = P[P.get("err").notna()] if "err" in P else P.iloc[0:0]
    P = P[P.get("err").isna()] if "err" in P else P
    M = S.merge(P, on="rid", how="inner")
    L = ["# 研究十九：停損位置——細表", "", f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG19.md`（K線分析 0236 合併版）。訊號集 ＝ 研究十五主格 B3。", ""]
    L.append(f"## 〇、對帳：研究十五 B3 {len(S):,} 筆；重跑 chan.detect 對上 stop {len(P):,} 筆；對不上／無 ATR {len(err):,} 筆（{err['err'].value_counts().to_dict() if len(err) else ''}）")
    if len(P) < 0.98 * len(S):
        L.append("⛔ 對帳不過（< 98%），停。"); open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L)); print("\n".join(L)); sys.exit(1)
    # P1 對帳：無停損版 ＝ close[k+H]/open[k+1] 應等於 signals 的 g_H
    L.append("")
    # C 校準
    L.append("## 一、停損距離 %（entry − stop）÷ entry 與 C 的校準"); L.append("")
    L.append("| 組 | 距離中位 | p10 | p90 |"); L.append("|---|---:|---:|---:|")
    dA = M["distA"].to_numpy(float); lo = M["lo"].to_numpy(float); ep = M["entry"].to_numpy(float); atrv = M["atr"].to_numpy(float)
    cw = (M["month"] < "2021-01").to_numpy() if a.calib_window == "A" else np.ones(len(M), bool)   # 校準母體（A 窗 or 全樣本）
    L.append(f"校準母體：{a.calib_window}（{int(cw.sum()):,}／{len(M):,} 筆）"); L.append("")
    L.append(f"| A | {np.nanmedian(dA) * 100:.2f}% | {np.nanpercentile(dA, 10) * 100:.2f}% | {np.nanpercentile(dA, 90) * 100:.2f}% |")
    mk = {}
    for kk in KS:
        dB = dA + kk * atrv / ep
        m = calibrate_m(dA[cw], lo[cw], ep[cw], float(np.nanmedian(dB[cw]))); mk[kk] = m
        dC = dA + m * lo / ep
        L.append(f"| B_{kk} | {np.nanmedian(dB) * 100:.2f}% | {np.nanpercentile(dB, 10) * 100:.2f}% | {np.nanpercentile(dB, 90) * 100:.2f}% |")
        L.append(f"| C_{kk}（m＝{m * 100:.2f}%） | {np.nanmedian(dC) * 100:.2f}% | {np.nanpercentile(dC, 10) * 100:.2f}% | {np.nanpercentile(dC, 90) * 100:.2f}% |")
    L.append(""); L.append(f"- ATR14／價格 中位 {np.nanmedian(M['atr_pct']) * 100:.2f}%，p10 {np.nanpercentile(M['atr_pct'], 10) * 100:.2f}%、p90 {np.nanpercentile(M['atr_pct'], 90) * 100:.2f}%"); L.append("")
    # C 的出場要重算：需要每筆 stop = lo(1−m) ⇒ 再跑一次 worker？改成主程序用已存的 K 棒不可行 ⇒ 用第二輪 pool
    C_jobs = [(sid, uni.get(sid), [(int(k), int(rid)) for k, rid in zip(g["k"], g["rid"])], mk) for sid, g in S.groupby("sid")]
    rowsC = []
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        for r in pool.imap_unordered(worker_c, C_jobs, chunksize=8):
            rowsC.extend(r)
    PC = pd.DataFrame(rowsC); M = M.merge(PC, on="rid", how="left")
    M.to_csv(os.path.join(RESULTS, "rows.csv.gz"), index=False)
    ksig = {"": 0, "i": 0}
    for tag, lab in (("", "主格：收盤跌破"), ("i", "敏感度：盤中觸價")):
        L.append(f"## 二{'' if tag == '' else '′'}、{lab}"); L.append("")
        for H in HOLDS:
            L.append(f"#### H{H}"); L.append(""); L += HDR
            L.append(cell("無停損（＝研究十五 P1）", M[f"g_H{H}"], M["month"], base_m[H])[0])
            L.append(cell(f"A 結構低點（停損率 {M[f'A{tag}_s_H{H}'].mean() * 100:.0f}%）", M[f"A{tag}_H{H}"], M["month"], base_m[H])[0])
            for kk in KS:
                L.append(cell(f"B_{kk}（停損率 {M[f'B{kk}{tag}_s_H{H}'].mean() * 100:.0f}%）", M[f"B{kk}{tag}_H{H}"], M["month"], base_m[H])[0])
                L.append(cell(f"C_{kk}（停損率 {M[f'C{kk}{tag}_s_H{H}'].mean() * 100:.0f}%）", M[f"C{kk}{tag}_H{H}"], M["month"], base_m[H])[0])
            L.append(""); L.append("比較（同筆配對、月分群 CI）：")
            for kk in KS:
                d1 = R.cl_stats((M[f"B{kk}{tag}_H{H}"] - M[f"A{tag}_H{H}"]).to_numpy(float), M["month"].to_numpy())
                d2 = R.cl_stats((M[f"B{kk}{tag}_H{H}"] - M[f"C{kk}{tag}_H{H}"]).to_numpy(float), M["month"].to_numpy())
                ksig[tag] += int(not (d1["lo"] <= 0 <= d1["hi"])) + int(not (d2["lo"] <= 0 <= d2["hi"]))
                sav = M[(M[f"A{tag}_s_H{H}"] == True) & (M[f"B{kk}{tag}_s_H{H}"] == False)]
                sv = cell("", sav[f"B{kk}{tag}_H{H}"], sav["month"], base_m[H])[1] if len(sav) else None
                savC = M[(M[f"A{tag}_s_H{H}"] == True) & (M[f"C{kk}{tag}_s_H{H}"] == False)]
                svC = cell("", savC[f"C{kk}{tag}_H{H}"], savC["month"], base_m[H])[1] if len(savC) else None
                L.append(f"- k＝{kk}：B − A {_ci(d1)}；**B − C {_ci(d2)}**；⭐ A 被停損、B 沒被停損 n {len(sav):,}：B 報酬 {_p(np.nanmean(sav[f'B{kk}{tag}_H{H}']) - COST) if len(sav) else '—'}、對基準 {(_ci(sv) if sv else '—')}；A 停損 C 沒停損 n {len(savC):,}：對基準 {(_ci(svC) if svC else '—')}")
            # 放棄組：被 A 停損那批若不停損的報酬（＝ g_H）
            stA = M[M[f"A{tag}_s_H{H}"] == True]
            L.append(f"- 放棄組：A 被停損那批 n {len(stA):,}，若不停損（研究十五 P1）的報酬 {_p(np.nanmean(stA[f'g_H{H}']) - COST)}，實際停損出場 {_p(np.nanmean(stA[f'A{tag}_H{H}']) - COST)}")
            L.append("")
    # 探索性：按 ATR/價格 高低兩群 B − C（H20、k=1.0）
    L.append("## 三、探索性（事後分析，⛔ 不進 30 格）：按進場時 ATR／價格 分高低兩群，B_1.0 − C_1.0（H20）"); L.append("")
    med = np.nanmedian(M["atr_pct"])
    for lab, mm in (("低波動", M["atr_pct"] <= med), ("高波動", M["atr_pct"] > med)):
        d = M[mm]; s = R.cl_stats((d["B1.0_H20"] - d["C1.0_H20"]).to_numpy(float), d["month"].to_numpy())
        L.append(f"- {lab}（n {len(d):,}）：{_ci(s)}")
    L.append("")
    L.append(f"## 四、格數：主格 30 格、測得出 {ksig['']} 格、雜訊期望 1.5；盤中觸價 30 格、測得出 {ksig['i']} 格、雜訊期望 1.5")
    open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L))
    print(f"完成 {time.time() - t0:.0f}s → {RESULTS}/summary.md；主格測得出 {ksig['']}/30、盤中 {ksig['i']}/30", file=sys.stderr)


def worker_c(args):
    """C_k：stop = lo × (1 − m(k))。"""
    sid, market, ks, mk = args
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return []
    o, c, h, l, next_bad = (B[x] for x in ("o", "c", "h", "l", "next_bad"))
    vp = R15.VARIANTS["main"]
    _, sigs = C.detect(h, l, c, pen_mode=vp["pen_mode"], zg_mode=vp["zg_mode"], n_pens=vp["n_pens"], start=0)
    stop_at = {int(s["signal_raw"]): float(s["stop"]) for s in sigs if s["kind"] == "B3"}
    out = []
    for k, rid in ks:
        if k not in stop_at:
            continue
        lo = stop_at[k]; row = {"rid": rid}
        for H in HOLDS:
            for mode, tag in ((False, ""), (True, "i")):
                for kk, m in mk.items():
                    g, st, _ = exit_with_stop(o, c, l, k, H, lo * (1 - m), next_bad, mode)
                    row[f"C{kk}{tag}_H{H}"] = g; row[f"C{kk}{tag}_s_H{H}"] = st
        out.append(row)
    return out


if __name__ == "__main__":
    main()

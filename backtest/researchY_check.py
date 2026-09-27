# -*- coding: utf-8 -*-
"""PREREGY 本體的獨立查核（回測線，2026-09-27）。⛔ 不 import researchY；資料從原檔重讀、事件與統計用另一套寫法重算。

  K1 0050 還原開盤：直接讀 edc6f 快照 stocks/0050.csv＋adj/0050.csv（cum_factor 取「事件日 > d」第一列）⇒ 對 body 逐事件 R20（差 ≤ 1e-12）
  K2 事件：pandas rolling(756).quantile（線性）＋ 迴圈去重（隔 ≥ 20）＋ 起算日 ＝ 下一個台北交易日；#3 用 csv 模組自讀 instamt
      ⇒ 12 格連續量「窗內事件數」對 body_cells；#2、#3 起算日逐筆對 body 逐事件檔
  K3 #5：自讀 us-stock-data 2119dc10 兩檔 ⇒ 4 格窗內事件數
  K4 判得動的格：對照、D、CR0 月分群 SE（逐群迴圈）、Bonferroni（0.05／16）CI、出口、結果、候選、假訊號臂百分位（同種子、同抽法）
  K5 出口①的格：n、n_eff 與出口；且 body_cells 沒有任何報酬欄有值（照 PREREGH1 §五只報筆數）
  K6 洩漏：repo 內 body_* 沒有 #2／#5 逐事件列、沒有 2017-03-02 以前的報酬、早年檔只有事件日

    python -m backtest.researchY_check
"""
from __future__ import annotations

import csv
import glob
import io
import json
import os
import subprocess
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsY")
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
YD = os.path.expanduser("~/ydata/3edc0e2206/data")
PRIV = os.path.expanduser("~/us_work/prey")
US = os.path.expanduser("~/us-stock-data")
US_A, US_B = "591624c722486fd533359beac3a1583016d88756", "2119dc10718d0fc6c7d4b1df6e041713760d46b1"
W0, W1, E0, E1 = "2017-03-02", "2026-08-24", "2008-01-01", "2014-12-31"
L, H, GAP = 756, 20, 20
Z = NormalDist().inv_cdf(1 - 0.05 / 16 / 2)
RES: dict = {}


def ok(name, cond, info=""):
    RES[name] = {"過": bool(cond), "說明": info}
    print(f"[{'✅' if cond else '⛔'}] {name}｜{info}", flush=True)


def git_csv(sha, path):
    raw = subprocess.run(["git", "-C", US, "show", f"{sha}:{path}"], capture_output=True, check=True).stdout
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def calendar():
    early = []
    with open(os.path.join(YD, "early/_structure.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["market"] == "twse" and int(r["rows"]) > 0:
                early.append(r["date"])
    with open(os.path.join(YD, "meta/calendar_twse.csv"), encoding="utf-8") as fh:
        main = [r["date"] for r in csv.DictReader(fh)]
    return sorted(set(early)) + [d for d in main if d > max(early)]


def adj_open(sid, cal):
    px = {}
    with open(os.path.join(SNAP, "stocks", f"{sid}.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                v = float(r["open"])
            except ValueError:
                continue
            if v > 0:
                px[r["date"]] = v
    ev = []
    p = os.path.join(SNAP, "adj", f"{sid}.csv")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            ev = sorted((r["date"], float(r["cum_factor"])) for r in csv.DictReader(fh))
    out = np.full(len(cal), np.nan)
    for i, d in enumerate(cal):
        if d in px:
            f = next((c for (e, c) in ev if e > d), 1.0)
            out[i] = px[d] * f
    return out


def tails(dates, v, cal):
    """回傳 {端: [起算位置…]}（去重後；台北日曆位置）。dates 為原生觀測日。"""
    s = pd.Series(v).reset_index(drop=True)
    q5 = s.rolling(L).quantile(0.05, interpolation="linear"); q95 = s.rolling(L).quantile(0.95, interpolation="linear")
    out = {}
    calA = np.asarray(cal)
    for end, m in (("低端", (s <= q5) & q5.notna()), ("高端", (s >= q95) & q95.notna())):
        idx = np.flatnonzero(m.to_numpy())
        kept, last = [], None
        for i in idx:
            if last is None or i - last >= GAP:
                kept.append(i); last = i
        out[end] = [(str(dates[i]), int(np.searchsorted(calA, dates[i], side="right"))) for i in kept]
    return out


def main():
    cal = calendar(); calA = np.asarray(cal); pos = {d: i for i, d in enumerate(cal)}
    w0, w1 = pos[W0], pos[W1]
    cells = pd.read_csv(os.path.join(OUT, "body_cells.csv"))
    cell = {(r["因素"], r["端"]): r for _, r in cells.iterrows()}
    ok("K0 日曆", w1 - w0 + 1 == 2313, f"主窗 {w1 - w0 + 1} 日")

    # ── K1 0050 ──
    o = adj_open("0050", cal)
    R20 = np.full(len(cal), np.nan); R20[:-H] = o[H:] / o[:-H] - 1
    pub = pd.read_csv(os.path.join(OUT, "body_events.csv"), dtype={"起算日": str})
    priv = pd.read_csv(os.path.join(PRIV, "body_events_priv.csv"), dtype={"起算日": str})
    allev = pd.concat([pub, priv], ignore_index=True)
    diff = max(abs(R20[pos[d]] - r) for d, r in zip(allev["起算日"], allev["R20"]))
    ok("K1 0050 還原開盤 R20 逐事件", diff <= 1e-12, f"{len(allev)} 筆，最大差 {diff:.2e}")

    # ── K2 連續量事件 ──
    ev = {}
    g = git_csv(US_A, "data/macro/yahoo_GSPC.csv")
    gd = [r["date"] for r in g if r["close"] not in ("", "null")]; gc = np.array([float(r["close"]) for r in g if r["close"] not in ("", "null")])
    t2 = tails(gd[1:], gc[1:] / gc[:-1] - 1, cal)
    ev["#2"] = {e: [(calA[s] if s < len(cal) else "", s) for (_, s) in lst] for e, lst in t2.items()}   # #2 事件日＝起算日（台北 T）
    for key, name, kind in (("#7", "fred_DGS10.csv", "diff"), ("#8", "fred_VIXCLS.csv", "level"), ("#6", "cbc_BP01D01_NTD.csv", "pct")):
        rows = git_csv(US_A, f"data/macro/{name}")
        col = "ntd_per_usd" if key == "#6" else "value"
        dd, vv = [], []
        for r in rows:
            try:
                vv.append(float(r[col])); dd.append(r["date"])
            except ValueError:
                pass
        vv = np.array(vv)
        if kind == "diff":
            x = np.r_[np.full(20, np.nan), (vv[20:] - vv[:-20]) * 100]
        elif kind == "pct":
            x = np.r_[np.full(20, np.nan), vv[20:] / vv[:-20] - 1]
        else:
            x = vv
        m = ~np.isnan(x)
        ev[key] = tails(np.asarray(dd)[m], x[m], cal)
    # #3
    net = {}
    for tree in ("early", "universe"):
        for f in sorted(glob.glob(os.path.join(YD, tree, "instamt", "*.csv"))):
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if r["investor"] in ("外資", "外資及陸資", "外資及陸資(不含外資自營商)", "外資自營商"):
                        net[r["date"]] = net.get(r["date"], 0.0) + float(r["net"])
    d3 = sorted(net)
    ev["#3"] = tails(np.asarray(d3), np.array([net[d] for d in d3]), cal)
    # #9
    pv = {}
    for tree in ("early", "universe"):
        for f in sorted(glob.glob(os.path.join(YD, tree, "marginmkt", "*.csv"))):
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if r["item"] == "融資金額(仟元)":
                        pv[r["date"]] = float(r["prev"])
    d9 = sorted(pv); p9 = np.array([pv[d] for d in d9])
    x9 = p9[20:] / p9[:-20] - 1
    ev["#9"] = tails(np.asarray(d9[20:]), x9, cal)
    mism = []
    for key in ("#2", "#3", "#6", "#7", "#8", "#9"):
        for end in ("低端", "高端"):
            n_in = sum(1 for (d, s) in ev[key][end] if W0 <= d <= W1)
            nb = int(cell[(key, end)]["窗內事件（事件日在窗內）"])
            if n_in != nb:
                mism.append((key, end, n_in, nb))
    ok("K2 12 格窗內事件數", not mism, f"不符 {mism}")
    for key, src in (("#2", priv), ("#3", pub)):
        for end in ("低端", "高端"):
            mine = sorted(calA[s] for (d, s) in ev[key][end] if W0 <= d <= W1 and s + H <= w1 and np.isfinite(R20[s]))
            theirs = sorted(src[(src["因素"] == key) & (src["端"] == end)]["起算日"])
            ok(f"K2 {key} {end} 起算日逐筆", mine == theirs, f"{len(mine)} 筆")

    # ── K3 #5 ──
    fr = git_csv(US_B, "data/macro/fomc_rate_changes.csv")
    cb = git_csv(US_B, "data/macro/cbc_rediscount.csv")

    def ded(ss):
        k, last = [], None
        for s in sorted(ss):
            if last is None or s - last >= GAP:
                k.append(s); last = s
        return k
    c5 = {}
    for end, col in (("調升", "increase_bp"), ("調降", "decrease_bp")):
        ss = [int(np.searchsorted(calA, r["statement_date"], side="right")) for r in fr if r[col].strip() not in ("", "...", "0")]
        c5[("#5 聯準會", end)] = sum(1 for s in ded(ss) if W0 <= calA[s] <= W1)
    for end, dv in (("調升", "升"), ("調降", "降")):
        rr = [r["decision_release_date"] for r in cb if r["direction"] == dv and r["decision_release_date"]]
        ss = {int(np.searchsorted(calA, d, side="right")): d for d in rr}
        c5[("#5 台灣", end)] = sum(1 for s in ded(ss) if W0 <= ss[s] <= W1)
    bad5 = [(k, v, int(cell[k]["窗內事件（事件日在窗內）"])) for k, v in c5.items() if v != int(cell[k]["窗內事件（事件日在窗內）"])]
    ok("K3 #5 四格窗內事件數", not bad5, f"{ {f'{a} {b}': v for (a, b), v in c5.items()} }｜不符 {bad5}")

    # ── K4 判得動的格 ──
    elig = [s for s in range(w0, w1 - H + 1) if np.isfinite(R20[s])]
    base = float(np.mean(R20[elig]))
    judged = cells[cells["出口"] != "出口①"]
    for _, r in judged.iterrows():
        src = priv if r["因素"] in ("#2", "#5 聯準會", "#5 台灣") else pub
        sd = src[(src["因素"] == r["因素"]) & (src["端"] == r["端"])]["起算日"].tolist()
        s = np.array([pos[d] for d in sd]); x = R20[s]
        D_ = x.mean() - base
        grp = {}
        for si, xi in zip(s, x):
            grp.setdefault(calA[si][:7], []).append(xi - x.mean())
        se = np.sqrt(sum(sum(v) ** 2 for v in grp.values())) / len(x)
        lo, hi = D_ - Z * se, D_ + Z * se
        neff = min(len(s), len({(si - w0) // H for si in s}))
        ex = "出口①" if neff < 30 else ("出口②" if neff < 100 else "出口③")
        res = "結果①" if lo <= 0 <= hi else ("結果②" if D_ > 0 else "結果③")
        cand = {"結果①": "都不是", "結果②": "加碼候選", "結果③": "減碼候選"}[res]
        fk = [R20[np.random.default_rng(20260925 + k).choice(np.array(elig), len(s), replace=False)].mean() for k in range(1000)]
        pct = float(np.mean(np.array(fk) <= x.mean()) * 100)
        good = (abs(base - r["對照（母體基準）"]) < 1e-12 and abs(D_ - r["D"]) < 1e-12 and abs(se - r["月分群 SE"]) < 1e-12
                and abs(lo - r["Bonferroni CI 下"]) < 1e-12 and abs(hi - r["Bonferroni CI 上"]) < 1e-12 and ex == r["出口"] and res == r["結果"]
                and cand == r["候選"] and int(neff) == int(r["n_eff"]) and abs(pct - r["假訊號臂百分位（真平均在 1,000 個假平均的位置）"]) < 1e-9)
        ok(f"K4 {r['因素']} {r['端']}", good, f"n {len(s)}｜n_eff {neff}｜{ex}｜{res}｜{cand}｜假訊號百分位 {pct:.1f}")

    # ── K5 出口①的格 ──
    ret_cols = [c for c in cells.columns if c in ("事件平均 R20", "D", "月分群 SE") or c.startswith("描述")]
    e1 = cells[cells["出口"] == "出口①"]
    bad = [f"{a} {b}" for a, b, n in zip(e1["因素"], e1["端"], e1["n_eff"]) if n >= 30]
    leak = int(e1[ret_cols].notna().sum().sum())
    ok("K5 出口①的格 n_eff < 30 且無任何報酬欄", not bad and leak == 0, f"{len(e1)} 格；n_eff ≥ 30 的 {bad}；報酬欄非空 {leak}")

    # ── K6 洩漏 ──
    fl = pd.read_csv(os.path.join(OUT, "body_early_flags.csv"))
    c6 = {"repo 逐事件檔沒有 #2／#5": not pub["因素"].isin(["#2", "#5 聯準會", "#5 台灣"]).any(),
          "repo 逐事件檔起算日全 ≥ 主窗首日": bool((pub["起算日"] >= W0).all()),
          "早年旗標檔只有 因素／端／早年事件日 三欄": list(fl.columns) == ["因素", "端", "早年事件日"],
          "早年旗標檔沒有 #2／#5": not fl["因素"].isin(["#2", "#5 聯準會", "#5 台灣"]).any(),
          "早年旗標全在 2008-01～2014-12": bool(((fl["早年事件日"] >= E0) & (fl["早年事件日"] <= E1)).all())}
    ok("K6 洩漏", all(c6.values()), json.dumps(c6, ensure_ascii=False))
    allok = all(v["過"] for v in RES.values())
    json.dump({"全部過": allok, "項": RES}, open(os.path.join(OUT, "body_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[查核] 全部過 {allok}（{sum(v['過'] for v in RES.values())}／{len(RES)}）")


if __name__ == "__main__":
    main()

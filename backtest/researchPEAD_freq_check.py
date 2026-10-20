# -*- coding: utf-8 -*-
"""researchPEAD_freq 對帳（財報公告後漂移 PEAD seq1 頻率表乾跑，登錄 sha af545cdcfa5bf94f）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有期結果。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEAD_freq_check
輸出 backtest/resultsPEAD/freq/check.json、check.log

（全部用 csv 模組／自寫迴圈重讀原始檔，⛔ 不呼叫 researchPEAD_freq 的函式）
C1 抽 40 筆（上季切點保留 16、同季切點保留 8、閘外 8、最低十分位 8；default_rng(20261020)）：自讀 fin_hist 算單季 EPS（Q1＝累計、其餘＝累計相減、
   不可算改 eps_q）、d、前 8 季樣本標準差、SUE ⇒ 與事件檔相同（差 ＜ 1e−9）。
C2 同 40 筆：自讀 filing_dates，AI1 最早、否則 AI2 最早 ⇒ ＝ 事件檔上傳時戳；e ＝ 日曆第一個日期 ＞ 上傳日 ⇒ ＝ 事件檔 e。
C3 不前視（全事件檔）：e ＞ 上傳日（每筆）；上傳日 ＞ 該季季底（每筆）；SUE 只用 q−12～q 的 EPS（構造；C1 已逐筆重算）。
C4 切點：自算主世界全部股票（rluwork sids ∩ D.load_stock 有成交日 ≥ 260）每季 SUE ⇒ 抽 8 季：SUE可算家數、同季 90 百分位、上一季 90 百分位 ＝ quarterly.csv。
C5 閘：C1 樣本自算 e−20～e−1 日均量 ≥ 500,000 股 ∧ 含 e 的 20 日都有成交 ∧ pit_valid[e] ⇒ 保留者為真、閘外者為假。
C6 營收分組：C1 樣本自讀 revenue_hist，三個月年增、可得日（次月 10 日；2026-01 期起 15 日之後第一個交易日）≤ e ⇒ ＝ 事件檔營收分組。
C7 策略鎖：python3 -m backtest.strategy_lock --check 必須相符。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import pickle
import statistics
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  只用 WORLDS 路徑
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsPEAD/freq"
WD = os.path.expanduser("~/peadwork/006adbd009/data")
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return float("nan")


def read_fin():
    out = {}
    for f in sorted(glob.glob(os.path.join(WD, "mops", "fin_hist", "*.csv"))):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                y, q = int(r["period"][:4]), int(r["period"][-1])
                out[(r["stock_id"], y * 4 + q - 1)] = (num(r["eps_ytd"]) if r["eps_ytd"] else float("nan"),
                                                       num(r["eps_q"]) if r["eps_q"] else float("nan"))
    return out


def single(fin, s, qi):
    if (s, qi) not in fin:
        return float("nan")
    ytd, eq = fin[(s, qi)]
    if qi % 4 == 0:
        e = ytd
    else:
        p = fin.get((s, qi - 1), (float("nan"), float("nan")))[0]
        e = ytd - p
    if e != e and eq == eq:
        e = eq
    return e


def sue(fin, s, qi):
    E = {k: single(fin, s, k) for k in range(qi - 12, qi + 1)}
    d = lambda k: E[k] - E[k - 4]
    if (s, qi) not in fin:
        return float("nan"), "無列"
    if d(qi) != d(qi):
        return float("nan"), "EPS缺"
    h = [d(k) for k in range(qi - 8, qi)]
    if any(x != x for x in h):
        return float("nan"), "前8季不足"
    sd = statistics.stdev(h)
    if not sd > 0:
        return float("nan"), "標準差0"
    return d(qi) / sd, "ok"


def main():
    J = {}; bad = 0
    rng = np.random.default_rng(20261020)
    ev = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str})
    qt = pd.read_csv(os.path.join(OUT, "quarterly.csv"))
    data = AT.WORLDS["主"]["data"]; D.DATA = data
    cal = D.load_calendar()
    stx = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str); mk = dict(zip(stx["stock_id"], stx["market"]))
    fin = read_fin()
    # filing_dates
    up = {}
    with open(os.path.join(WD, "meta", "filing_dates.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["doc_code"] in ("AI1", "AI2") and r["uploaded_at"]:
                k = (r["stock_id"], int(r["year"]) * 4 + int(r["season"]) - 1)
                up.setdefault(k, {}).setdefault(r["doc_code"], []).append(r["uploaded_at"])
    # 樣本
    ev0 = ev; ev = ev[ev["e"].notna() & (ev["e"].astype(str) != "")]
    grp = [("上季保留", ev[ev["上季切點_入選"] & (ev["st"] == "保留")], 16), ("同季保留", ev[ev["同季切點_入選"] & (ev["st"] == "保留")], 8),
           ("閘外", ev[ev["st"] == "閘外(500張/pit)"], 8), ("最低十分位", ev[ev["最低十分位"]], 8)]
    pick = pd.concat([g.sample(n, random_state=int(rng.integers(1e9))).assign(組=nm) for nm, g, n in grp])
    # 營收
    revf = {}
    for f in sorted(glob.glob(os.path.join(WD, "mops", "revenue_hist", "*.csv"))):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                revf[(r["stock_id"], r["period"])] = (num(r["當月營收"]), num(r["去年當月營收"]))
    rows = []
    for _, r in pick.iterrows():
        s, qi = r["sid"], int(r["qi"])
        v, why = sue(fin, s, qi)
        ok1 = why == "ok" and abs(v - r["SUE"]) < 1e-9 and abs(single(fin, s, qi) - r["EPS"]) < 1e-9
        u = up.get((s, qi), {}); ts = min(u["AI1"]) if "AI1" in u else (min(u["AI2"]) if "AI2" in u else None)
        ud = pd.Timestamp(ts[:10]) if ts else None
        e = cal[cal > ud][0] if ud is not None else None
        ok2 = ts is not None and pd.Timestamp(ts) == pd.Timestamp(r["上傳時戳"]) and str(e.date()) == r["e"]
        # 閘
        st = D.load_stock(s, mk.get(s, "twse"), cal); df = st.df
        p = int(cal.searchsorted(e)); vol = df["volume"].to_numpy(float); trd = df["traded"].to_numpy(bool)
        g = bool(p >= 20 and trd[p - 19:p + 1].all() and np.nanmean(vol[p - 20:p]) >= 500_000 and bool(np.asarray(UG.pit_valid(s, cal, data))[p]))
        ok5 = (g if r["st"] in ("保留", "e開盤鎖漲停", "e無成交") else (not g)) if r["st"] != "" else True
        # 營收
        y, q = qi // 4, qi % 4 + 1
        gr = "營收已先好"; yo = []
        for m in (3 * q - 2, 3 * q - 1, 3 * q):
            per = f"{y}-{m:02d}"
            y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            av = cal[cal > pd.Timestamp(y2, m2, 10 if per <= "2025-12" else 15)][0]
            rv, rl = revf.get((s, per), (float("nan"), float("nan")))
            if not (rv == rv and rl == rl and rl > 0) or av > e:
                gr = "沒先好_資料不全"; break
            yo.append(rv / rl - 1)
        if gr == "營收已先好" and not all(x > 0 for x in yo):
            gr = "沒先好_有月≤0"
        ok6 = gr == r["營收分組"]
        okall = ok1 and ok2 and ok5 and ok6
        bad += 0 if okall else 1
        rows.append({"組": r["組"], "sid": s, "季": r["季"], "SUE檔": r["SUE"], "SUE手算": v, "上傳檔": r["上傳時戳"], "上傳手算": ts, "e檔": r["e"],
                     "e手算": str(e.date()) if e is not None else None, "st": r["st"], "閘手算": g, "營收檔": r["營收分組"], "營收手算": gr,
                     "C1": ok1, "C2": ok2, "C5": ok5, "C6": ok6})
    J["C1C2C5C6"] = rows
    log(f"[C1/C2/C5/C6] {sum(x['C1'] and x['C2'] and x['C5'] and x['C6'] for x in rows)}／{len(rows)} 相符｜"
        f"C1 {sum(x['C1'] for x in rows)} C2 {sum(x['C2'] for x in rows)} C5 {sum(x['C5'] for x in rows)} C6 {sum(x['C6'] for x in rows)}")
    # C3
    evv = ev
    ed = pd.to_datetime(evv["e"]); ud = pd.to_datetime(evv["上傳時戳"].str[:10])
    qend = pd.PeriodIndex(evv["季"].str.replace("Q", "-Q"), freq="Q").end_time.normalize()
    n_bad_e = int((ed <= ud).sum()); n_bad_q = int((ud.values <= qend.values).sum())
    J["C3"] = {"事件列": int(len(evv)), "e≤上傳日": n_bad_e, "上傳日≤季底": n_bad_q, "e−上傳日 最小天數": int((ed - ud).dt.days.min())}
    bad += (n_bad_e > 0) + (n_bad_q > 0)
    log(f"[C3] {J['C3']}")
    # C4
    Z = pickle.load(open(os.path.expanduser("~/rluwork/world_main.pkl"), "rb"))
    uni = []
    for s in Z["sids"]:
        st = D.load_stock(s, mk.get(s, "twse"), cal)
        if st is not None and int(st.df["traded"].sum()) >= 260:
            uni.append(s)
    log(f"[C4] 自算母體 {len(uni)} 檔")
    qsel = sorted(rng.choice(qt.loc[qt["上季切點"].notna(), "季"].to_numpy(), 8, replace=False))
    c4 = []
    for qn in qsel:
        y, q = int(qn[:4]), int(qn[-1]); qi = y * 4 + q - 1
        v = [x for x in (sue(fin, s, qi)[0] for s in uni) if x == x]
        v1 = [x for x in (sue(fin, s, qi - 1)[0] for s in uni) if x == x]
        r = qt[qt["季"] == qn].iloc[0]
        ok = len(v) == r["SUE可算"] and abs(np.quantile(v, 0.9) - r["同季切點"]) < 1e-9 and abs(np.quantile(v1, 0.9) - r["上季切點"]) < 1e-9
        c4.append({"季": qn, "可算手算": len(v), "可算檔": int(r["SUE可算"]), "同季切點手算": float(np.quantile(v, 0.9)), "同季切點檔": r["同季切點"],
                   "上季切點手算": float(np.quantile(v1, 0.9)), "上季切點檔": r["上季切點"], "OK": bool(ok)})
        bad += 0 if ok else 1
    J["C4"] = c4
    log(f"[C4] {sum(x['OK'] for x in c4)}／{len(c4)} 季切點與家數相符")
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    J["C7_策略鎖"] = {"rc": p.returncode, "out": (p.stdout + p.stderr)[-800:]}
    log(f"[C7] strategy_lock --check rc={p.returncode}｜{(p.stdout + p.stderr).strip()[-300:]}")
    bad += 0 if p.returncode == 0 else 1
    J["不符項數"] = int(bad)
    log(f"[總] 不符 {bad} 項")
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

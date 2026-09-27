# -*- coding: utf-8 -*-
"""researchLev2_desc 的簡單獨立查核（⛔ 不 import backtest 任何模組）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchLev2_desc_check.py

D1 純抱：自讀快照 CSV、自己還原；純抱路徑 ＝ (1 − 0.385%) × 收盤_t ÷ 開盤_窗首（封閉式，不跑引擎）
D2 事後改挑法：用 idxmax 在 body_q1／body_q2 重挑（不同寫法）
D3 壓力：早年 0050 用 csv 模組逐列讀（git grep 另一個樣式）、除息檔逐檔 git show、逐日迴圈合成
"""
import csv
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsLev2")
DB = os.path.expanduser("~/tw-stock-data")
TOL = 1e-10
bad = []


def chk(n, ok, det=""):
    print(("✅" if ok else "⛔"), n, det, flush=True)
    if not ok:
        bad.append(n)


cal = list(pd.read_csv(os.path.join(SNAP, "meta", "calendar_twse.csv"))["date"])


def series(sid):
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str).set_index("date")
    a = pd.read_csv(os.path.join(SNAP, "adj", f"{sid}.csv"), dtype=str)
    out = {}
    for d in cal:
        if d not in r.index:
            out[d] = (np.nan, np.nan); continue
        f = 1.0
        for ed, cf in zip(a["date"], a["cum_factor"]):
            if ed > d:
                f = float(cf); break
        o, c = float(r.at[d, "open"] or "nan"), float(r.at[d, "close"] or "nan")
        out[d] = (o * f if o > 0 else np.nan, c * f if c > 0 else np.nan)
    o = np.array([out[d][0] for d in cal]); c = pd.Series([out[d][1] for d in cal]).ffill().to_numpy()
    return o, c


# D1
bh = pd.read_csv(os.path.join(OUT, "desc_buyhold.csv"), dtype={"檔": str})
mx = 0.0
for sid in ("00631L", "00685L", "0050", "0052"):
    o, c = series(sid)
    for r in bh[bh["檔"] == sid].itertuples():
        a, b = r.窗.split("～"); i0, i1 = cal.index(a), cal.index(b)
        v = (1 - 0.00385) * c[i0:i1 + 1] / o[i0]
        n = len(v); cg = v[-1] ** (245 / n) - 1
        p = np.concatenate([[1.0], v]); dd = ((p - np.maximum.accumulate(p)) / np.maximum.accumulate(p)).min()
        mx = max(mx, abs(cg - r.年化), abs(dd - r.回落), abs(v[-1] * 1e6 - r._7) / 1e6, abs(min(1.0, v.min()) * 1e6 - r.最慘時剩) / 1e6)
chk("D1 純抱 12 列（年化／回落／期末／最慘）", mx < TOL, f"最大差 {mx:.1e}")

# D2
q1 = pd.read_csv(os.path.join(OUT, "body_q1.csv"), dtype={"ETF": str, "正2": str}); q2 = pd.read_csv(os.path.join(OUT, "body_q2.csv"), dtype={"ETF": str, "正2": str})
mc = pd.read_csv(os.path.join(OUT, "desc_maxcagr.csv"))
got = []
for grp in ("挑選池", "00685L描述"):
    ex = q1[(q1["段"] == "探索") & (q1["組"] == grp)]
    top = ex[ex["年化"] == ex["年化"].max()].sort_values("正2%").iloc[0]
    cf = q1[(q1["段"] == "確認") & (q1["組"] == grp) & (q1["ETF"] == top["ETF"]) & (q1["ETF%"] == top["ETF%"]) & (q1["正2%"] == top["正2%"])]["年化"].iloc[0]
    got.append(cf)
ex = q2[(q2["段"] == "探索") & (q2["組"] == "挑選池")]; top = ex.loc[ex["年化"].idxmax()]
got.append(q2[(q2["段"] == "確認") & (q2["條件"] == top["條件"]) & (q2["換法"] == top["換法"]) & (q2["ETF"] == top["ETF"]) & (q2["正2"] == top["正2"])]["年化"].iloc[0])
chk("D2 事後改挑法 3 列（確認年化）", np.allclose(got, mc["確認年化"].to_numpy(), rtol=0, atol=1e-15), f"{[round(x, 6) for x in got]}")

# D3
S = json.load(open(os.path.join(OUT, "desc_summary.json"), encoding="utf-8"))
sha = S["早年資料"]["sha"]
txt = subprocess.run(["git", "-C", DB, "grep", "-h", ",0050,元大台灣50,twse,", sha, "--", "data/early/daily/"], capture_output=True, text=True).stdout
px = {}
for row in csv.reader(io.StringIO(txt)):
    px[row[1]] = float(row[8])
days = sorted(px)
exf = subprocess.run(["git", "-C", DB, "grep", "-l", ",0050,", sha, "--", "data/early/exright/"], capture_output=True, text=True).stdout.split()
evs = []
for f in exf:
    body = subprocess.run(["git", "-C", DB, "show", f.replace(f"{sha}:", f"{sha}:", 1)], capture_output=True, text=True).stdout
    for row in csv.DictReader(io.StringIO(body)):
        if row["stock_id"] == "0050":
            evs.append((row["date"], float(row["ref_price"]) / float(row["pre_close"])))
adj = {}
for d in days:
    f = 1.0
    for ed, fac in evs:
        if ed > d:
            f *= fac
    adj[d] = px[d] * f
st = pd.read_csv(os.path.join(OUT, "desc_stress.csv"))
mx = 0.0
for per, (a, b) in {"2008": ("2008-01-01", "2009-03-31"), "2011": ("2011-01-01", "2011-12-31")}.items():
    ds = [d for d in days if a <= d <= b]; prev = days[days.index(ds[0]) - 1]
    L = 1.0; pk = 1.0; mdd = 0.0; low = 1.0
    for i, d in enumerate(ds):
        r = adj[d] / adj[prev if i == 0 else ds[i - 1]] - 1
        L *= 1 + 2 * r - 0.01 / 245
        pk = max(pk, L); mdd = min(mdd, L / pk - 1); low = min(low, L)
    row = st[st["期間"].str.startswith(per) & st["對象"].str.startswith("合成正2")].iloc[0]
    mx = max(mx, abs(mdd - row["最大跌幅"]), abs(low * 1e6 - row["100萬谷底剩"]) / 1e6, abs(L * 1e6 - row["100萬期末"]) / 1e6)
chk("D3 壓力合成（2008、2011：最大跌幅／谷底／期末）", mx < 1e-9 and len(evs) == S["錨"]["除息事件"], f"最大差 {mx:.1e}、除息 {len(evs)} 筆")
print("⛔ 不過：" + "、".join(bad) if bad else "✅ 全過")
sys.exit(1 if bad else 0)

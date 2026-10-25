# -*- coding: utf-8 -*-
"""researchV41EV 獨立重算（不 import researchV41EV；自寫取日、結算、統計）——回測線計算子代理。
台股 4 段＋美股 4 段逐格重算 R、超額（60、72 月），另以 table.csv 重算兩平 p*、n、μ、s 與 stats.csv 比對。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchV41EV_check
"""
import io
import json
import math
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  只取面板
from backtest import researchShortageExit as SE             # noqa: E402

OUT = "backtest/resultsV41EV"
TOL = 1e-9
TW_PICK = {"K31": "6488", "K52": "2049", "K13": "2408", "K45": "1909", "K46": "2498"}   # 4 段以上、含早年與順延案
US_PICK = {"K27": "MU", "K05": "ALB", "K09": "ANET", "K54": "ENPH"}
TB = pd.read_csv(os.path.join(OUT, "table.csv"), dtype={"代號": str})
CS = pd.read_csv(os.path.join(OUT, "cases_input.csv"), dtype=str)
res = []; bad = 0


def cmp(tag, a, b):
    global bad
    ok = (np.isnan(a) and np.isnan(b)) or abs(a - b) < TOL
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}: 重算 {a:.10f} ／ 主程式 {b:.10f}")


# ── 台股：自己找進場（日曆上 ≥ 次月 1 日、第一個 TRD 且 O、C 有值）、自己找判決位置（日期 ≤ 目標的最後一根有效收盤）
sha, DN, MD = RT.ensure_data("9b0e9882572c")
PX = RT.prices(sha, DN, 3); O, _ = SE.seam_open(PX)
CAL = pd.DatetimeIndex(PX["CAL"]); C = PX["C"]; BAD = PX["BAD"]; TRD = PX["TRD"]
tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
tri["date"] = pd.to_datetime(tri["date"]); tri = tri.dropna().drop_duplicates("date").set_index("date")["close"].sort_index()
for cid, sid in TW_PICK.items():
    i = PX["ix"][sid]; ym = CS.set_index("id").loc[cid, "燈亮月"]
    y, m = map(int, ym.split("-")); m += 1
    if m == 13:
        y, m = y + 1, 1
    first = pd.Timestamp(y, m, 1)
    cand = [p for p in range(len(CAL)) if CAL[p] >= first and TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p])]
    e = cand[0]; P0 = O[i, e]
    for H in (60, 72):
        tgt = CAL[e] + pd.DateOffset(months=H)
        valid = [p for p in range(e, len(CAL)) if CAL[p] <= tgt and np.isfinite(C[i, p])]
        if any(BAD[i, e + 1:valid[-1] + 1]):
            res.append(f"--  {cid} {sid} {H}月 有壞根，check 不重算（主程式另標）"); continue
        x = valid[-1]
        R = C[i, x] / P0 - 1 - 0.00585
        Mk = tri[tri.index <= CAL[x]].iloc[-1] / tri[tri.index <= CAL[e - 1]].iloc[-1] - 1
        r = TB[(TB["id"] == cid) & (TB["代號"] == sid) & (TB["H月"] == H)].iloc[0]
        cmp(f"{cid} {sid} {H}月 R（進 {CAL[e].date()} 結 {CAL[x].date()}）", R, r["R"]); cmp(f"{cid} {sid} {H}月 超額", R - Mk, r["超額"])

# ── 美股：直接讀 prices_yahoo 原始 csv
REPO = os.path.expanduser("~/us-stock-data")


def g(path):
    return subprocess.run(["git", "-C", REPO, "show", f"origin/main:{path}"], capture_output=True, check=True).stdout


SP = pd.read_csv(io.BytesIO(g("data/macro/yahoo_SP500TR.csv"))); SP["date"] = pd.to_datetime(SP["date"]); SP = SP[SP["adjclose"] > 0].set_index("date")["adjclose"].sort_index()
GS = pd.to_datetime(pd.read_csv(io.BytesIO(g("data/macro/yahoo_GSPC.csv")))["date"]).sort_values().reset_index(drop=True)
for cid, tk in US_PICK.items():
    P = pd.read_csv(io.BytesIO(g(f"data/prices_yahoo/{tk}.csv"))); P["date"] = pd.to_datetime(P["date"])
    P = P[(P["open"] > 0) & (P["close"] > 0) & (P["adjclose"] > 0)].sort_values("date").reset_index(drop=True)
    ym = CS.set_index("id").loc[cid, "燈亮月"]; first = (pd.Period(ym, "M") + 1).start_time
    er = P[P["date"] >= first].iloc[0]; P0 = er["open"] / er["close"] * er["adjclose"]
    prevd = GS[GS < er["date"]].iloc[-1]
    for H in (60, 72):
        tgt = er["date"] + pd.DateOffset(months=H)
        xr = P[P["date"] <= tgt].iloc[-1]
        R = xr["adjclose"] / P0 - 1 - 0.001
        Mk = SP[SP.index <= xr["date"]].iloc[-1] / SP[SP.index <= prevd].iloc[-1] - 1
        r = TB[(TB["id"] == cid) & (TB["H月"] == H)].iloc[0]
        cmp(f"{cid} {tk} {H}月 R（進 {er['date'].date()} 結 {xr['date'].date()}）", R, r["R"]); cmp(f"{cid} {tk} {H}月 超額", R - Mk, r["超額"])

# ── 統計重算（以 table.csv 每檔值；本版每主題 1 檔 ⇒ 主題值＝該檔）
ST = pd.read_csv(os.path.join(OUT, "stats.csv"))
for mk in ("TW", "US"):
    for H in (24, 36, 60, 72):
        d = TB[(TB["市場"] == mk) & (TB["H月"] == H) & TB["R"].notna()]
        th = d.groupby("id").agg(結果=("結果", "first"), v=("超額", "mean"))
        w = th[th["結果"] == "大漲"]["v"].to_numpy(); l = th[th["結果"] == "失敗"]["v"].to_numpy()
        s = ST[(ST["市場"] == mk) & (ST["H月"] == H) & (ST["樣本單位"] == "主題") & (ST["量"] == "超額")].iloc[0]
        mu = l.mean(); sd = np.sqrt(((l - mu) ** 2).sum() / (len(l) - 1))
        cmp(f"{mk} {H}月 贏家平均", w.mean(), s["贏家平均"]); cmp(f"{mk} {H}月 反例中位", float(np.median(l)), s["反例中位"])
        cmp(f"{mk} {H}月 反例 s", sd, s["反例s"]); cmp(f"{mk} {H}月 門檻", mu - 1.28 * sd / math.sqrt(8), s["門檻μ−1.28s/√8"])
        for k, W, L in (("平均", w.mean(), mu), ("中位", np.median(w), np.median(l))):
            if L < 0:
                p = -L / (W - L); n = math.ceil(math.log(0.1) / math.log(1 - p))
                cmp(f"{mk} {H}月 p*_{k}", p, s[f"p*_{k}"]); cmp(f"{mk} {H}月 n_{k}", float(n), float(s[f"n_{k}"]))
            else:
                res.append(f"{'OK ' if not np.isfinite(s[f'p*_{k}']) else 'BAD'} {mk} {H}月 p*_{k}：反例 ≥0 ⇒ 不適用")
log = "\n".join(res) + f"\n\n不符 {bad} 格／共 {sum(1 for x in res if x[:3] in ('OK ', 'BAD'))} 格\n"
open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write(log)
json.dump({"不符": bad, "格數": len(res)}, open(os.path.join(OUT, "check.json"), "w"))
print(log)

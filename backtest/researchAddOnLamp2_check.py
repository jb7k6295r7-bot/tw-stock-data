# -*- coding: utf-8 -*-
"""researchAddOnLamp2 獨立重算（⛔ 不 import researchAddOnLamp2／researchLampCensus／researchV41EV）——回測線計算子代理。
① 自讀兩份燈 2 附件自定加碼月；自建成員（代表股＝案例表公司欄末 4 碼；同業＝peers_input_TW 名次前 3）→ 對 rows.csv 的成員集合；
② 每檔 燈1／加碼(b)／加碼(a) 的 R、超額自算 → 對 rows.csv（窗內有壞根或下市者 check 不重算、沿用主程式值並照列）；
③ 自建每案值 → 加碼 2 份、甲、乙、乙÷份數 的平均與中位（主表剔 K35、含 K35；兩版；大漲／失敗／全部）→ 對 stats.csv。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnLamp2_check
"""
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  只取面板
from backtest import researchShortageExit as SE             # noqa: E402

OUT = "backtest/resultsAddOnLamp2"
V41 = "backtest/resultsV41EV"
SHA = "9b0e9882572c"
TOL = 1e-9
res = []; bad = 0


def cmp(tag, a, b, tol=TOL):
    global bad
    a = float(a); b = float(b)
    ok = (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) < tol)
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}: 重算 {a:.10f} ／ 主程式 {b:.10f}")


def tsh(path):
    return subprocess.run(["git", "show", f"{SHA}:{path}"], capture_output=True, check=True).stdout


CS = pd.read_csv(os.path.join(V41, "cases_input.csv"), dtype=str, keep_default_na=False)
CS = CS[CS["市場"] == "TW"].set_index("id")
W = pd.read_csv(os.path.join(OUT, "win16_lamp2_input.csv"), dtype=str, keep_default_na=False)
L = pd.read_csv(os.path.join(OUT, "lose15_lamp2_input.csv"), dtype=str, keep_default_na=False)
addm = {}   # id -> 加碼進場所在月（取該月第一個交易日）
for _, r in W.iterrows():
    l2 = r["燈2月_出場表"]
    addm[r["id"]] = None if (l2 == "無" or l2 <= r["燈1月_案例表"]) else str(pd.Period(l2, "M") + 1)
for _, r in L.iterrows():
    addm[r["id"]] = None if r["加碼月"] == "不加碼" else r["加碼月"]
n_win = sum(1 for _, r in W.iterrows() if addm[r["id"]]); n_lose = sum(1 for _, r in L.iterrows() if addm[r["id"]])
res.append(f"--  加碼案數：大漲 {n_win}／{len(W)}、失敗 {n_lose}／{len(L)}（含 K35）")
okk = (n_win, n_lose) == (14, 8); bad += (not okk); res.append(f"{'OK ' if okk else 'BAD'} 加碼案數＝大漲 14、失敗 7＋K35")
PT = pd.read_csv(os.path.join(V41, "peers_input_TW.csv"), dtype=str, keep_default_na=False)
PT["n"] = pd.to_numeric(PT["名次"], errors="coerce"); PT = PT.sort_values(["id", "n"])
mem = {"代表股版": {}, "同業等權版": {}}
for cid, r in CS.iterrows():
    mem["代表股版"][cid] = [r["公司"].split()[-1]]
    mem["同業等權版"][cid] = [c.strip() for c in PT[PT["id"] == cid]["代號"] if c.strip()][:3]
RW = pd.read_csv(os.path.join(OUT, "rows.csv"), dtype={"代號": str})
allme = sorted({(k, c) for v in mem for k, cs in mem[v].items() for c in cs})
allmain = sorted({(r.id, r.代號) for r in RW.itertuples()})
okk = allme == allmain; bad += (not okk); res.append(f"{'OK ' if okk else 'BAD'} 成員集合 {len(allme)} 對（主程式 {len(allmain)}）")

sha, DN, MD = RT.ensure_data(SHA)
PX = RT.prices(sha, DN, 3); O, _ = SE.seam_open(PX)
CAL = pd.DatetimeIndex(PX["CAL"]); C = PX["C"]; BAD = PX["BAD"]; TRD = PX["TRD"]; IX = PX["ix"]
tri = pd.read_csv(io.BytesIO(tsh("data/history/market_tri.csv"))); tri["date"] = pd.to_datetime(tri["date"])
tri = tri.dropna().drop_duplicates("date").set_index("date")["close"].sort_index()


def trv(d):
    return float(tri[tri.index <= d].iloc[-1])


def ent(i, first):
    return [p for p in range(len(CAL)) if CAL[p] >= first and TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p])][0]


def settle(i, e, tgt):
    valid = [p for p in range(e, len(CAL)) if CAL[p] <= tgt and np.isfinite(C[i, p])]
    x = valid[-1]
    fin = np.flatnonzero(np.isfinite(C[i])); lastv = int(fin[-1])
    xcal = int(np.searchsorted(CAL, tgt, "right")) - 1
    if BAD[i, e + 1:x + 1].any() or (len(CAL) - 1 - lastv >= 5 and lastv < xcal):
        return None
    R = C[i, x] / O[i, e] - 1 - 0.00585
    return R - (trv(CAL[x]) / trv(CAL[e - 1]) - 1), R


val = {}
for cid, sid in allme:
    i = IX[sid]
    e = ent(i, (pd.Period(CS.loc[cid, "燈亮月"], "M") + 1).start_time)
    t = CAL[e] + pd.DateOffset(months=60)
    jobs = [("燈1", e, t)]
    if addm[cid]:
        e2 = ent(i, pd.Period(addm[cid], "M").start_time)
        if e2 > e:
            jobs += [("加碼(b)", e2, t), ("加碼(a)", e2, CAL[e2] + pd.DateOffset(months=60))]
    for seg, ee, tg in jobs:
        rr = RW[(RW["id"] == cid) & (RW["代號"] == sid) & (RW["段"] == seg)]
        if len(rr) != 1:
            bad += 1; res.append(f"BAD {cid} {sid} {seg} 主程式無此格"); continue
        out = settle(i, ee, tg)
        if out is None:
            res.append(f"--  {cid} {sid} {seg} 窗內壞根／下市，check 不重算（沿用主程式 {float(rr['超額'].iloc[0]):+.4f}）")
            val[(cid, sid, seg)] = float(rr["超額"].iloc[0]); continue
        X, R = out
        cmp(f"{cid} {sid} {seg} R（進 {CAL[ee].date()}）", R, rr["R"].iloc[0]); cmp(f"{cid} {sid} {seg} 超額", X, rr["超額"].iloc[0])
        val[(cid, sid, seg)] = X
extra = [f"{r.id} {r.代號} {r.段}" for r in RW[RW["R"].notna()].itertuples() if (r.id, r.代號, r.段) not in val]
okk = not extra; bad += (not okk); res.append(f"{'OK ' if okk else 'BAD'} 主程式格都在 check 內（多出 {extra}）")

ST = pd.read_csv(os.path.join(OUT, "stats.csv"))


def stg(**kw):
    d = ST
    for a, b in kw.items():
        d = d[d[a] == b]
    return d.iloc[0]


for incl in ("主表(剔K35)", "含K35"):
    for v in mem:
        rows = []
        for cid in CS.index:
            if incl == "主表(剔K35)" and cid == "K35":
                continue
            cs = mem[v][cid]
            x1 = np.mean([val[(cid, c, "燈1")] for c in cs])
            has = all((cid, c, "加碼(b)") in val for c in cs)
            ab = np.mean([val[(cid, c, "加碼(b)")] for c in cs]) if has else np.nan
            aa = np.mean([val[(cid, c, "加碼(a)")] for c in cs]) if has else np.nan
            rows.append((CS.loc[cid, "結果"], x1, ab, aa, has))
        for grp in ("全部", "大漲", "失敗"):
            q = [r for r in rows if grp == "全部" or r[0] == grp]
            j = [r[1] for r in q]; y = [r[1] + 2 * r[2] if r[4] else r[1] for r in q]; yr = [(r[1] + 2 * r[2]) / 3 if r[4] else r[1] for r in q]
            b2 = [2 * r[2] for r in q if r[4]]; a2 = [2 * r[3] for r in q if r[4]]
            for lab, vv in (("甲只買1份", j), ("乙有加碼(總損益)", y), ("乙有加碼(÷投入份數)", yr), ("加碼2份(b)同結算日", b2), ("加碼2份(a)自己60月", a2)):
                s = stg(樣本=incl, 版=v, 組=grp, 量=lab)
                cmp(f"{incl} {v} {grp} {lab} n", len(vv), s["n"]); cmp(f"{incl} {v} {grp} {lab} 平均", np.mean(vv), s["平均"])
                cmp(f"{incl} {v} {grp} {lab} 中位", np.median(vv), s["中位"])
nn = sum(1 for x in res if x[:3] in ("OK ", "BAD"))
log = "\n".join(res) + f"\n\n不符 {bad} 格／共 {nn} 格\n"
open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write(log)
json.dump({"不符": bad, "格數": nn}, open(os.path.join(OUT, "check.json"), "w"))
print("\n".join(x for x in res if not x.startswith("OK")) + f"\n不符 {bad} 格／共 {nn} 格")

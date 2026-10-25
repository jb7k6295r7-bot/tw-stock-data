# -*- coding: utf-8 -*-
"""researchLampCensus 獨立重算（⛔ 不 import researchLampCensus／researchV41EV；自讀清單、自算市值、自取進場與結算日、自算統計）——回測線計算子代理。
① 每檔市值（自讀 data/stocks 原檔）與下限判定 → 對 caps.csv；
② 每檔×每段（燈1 12／24／末、加碼(a) 12／24／末、加碼(b) 12／24）R、大盤、超額 → 對 rows.csv（窗內有壞根或下市者 check 不重算、照列）；
③ 自建訊號值 → 命中率（＞0、≥+1、≥+2、平均、中位）、加碼 2 份、甲乙兩版 → 對 stats.csv。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus_check
"""
import io
import json
import os
import re
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  只取面板
from backtest import researchShortageExit as SE             # noqa: E402  只取接縫開盤

OUT = "backtest/resultsLampCensus"
SHA = "9b0e9882572c"
TOL = 1e-9
res = []; bad = 0


def cmp(tag, a, b, tol=TOL):
    global bad
    a = float(a) if a is not None else np.nan; b = float(b) if b is not None else np.nan
    ok = (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) < tol)
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}: 重算 {a:.10f} ／ 主程式 {b:.10f}")


def tsh(path):
    return subprocess.run(["git", "show", f"{SHA}:{path}"], capture_output=True, check=True).stdout


S = pd.read_csv(os.path.join(OUT, "signals_input.csv"), dtype=str, keep_default_na=False)
S.columns = ["id", "ver"] + list(S.columns[2:])
sig = {}
for _, r in S.iterrows():
    cs = [x.split()[0] for x in (r["公司1"], r["公司2"], r["公司3"]) if x.strip() and x.strip() != "無點名"]
    y, q = r["燈1季"].split("Q"); m1 = f"{y}-{int(q) * 3:02d}"
    m2 = None
    if r["燈2季"].strip():
        y2, q2 = r["燈2季"].split("Q"); m2 = f"{y2}-{int(q2) * 3:02d}"
    sig[r["id"]] = {"甲": r["ver"] in ("甲", "兩版"), "乙": r["ver"] in ("乙", "兩版"), "型": r["型"], "codes": cs, "m1": m1, "m2": m2}

# ① 市值
CP = pd.read_csv(os.path.join(OUT, "caps.csv"), dtype={"代號": str})
keep = {}
for k, s in sig.items():
    kk = []
    for c in s["codes"]:
        D = pd.read_csv(io.BytesIO(tsh(f"data/stocks/{c}.csv")), dtype={"date": str})
        D = D[D["date"].str.startswith(s["m1"]) & (pd.to_numeric(D["close"], errors="coerce") > 0)]
        last = D.iloc[-1]
        sh = pd.to_numeric(D["shares"], errors="coerce"); sh = sh[sh > 0]
        v = float(last["close"]) * float(sh.iloc[-1])
        mine = CP[(CP["訊號"] == k) & (CP["代號"] == c)]["市值(億)"].iloc[0] * 1e8
        cmp(f"市值 {k} {c}（{s['m1']} 末 {last['date']}）", v, mine, tol=1e-3)
        if v >= 1e10:
            kk.append(c)
    keep[k] = kk

# ② 逐格
sha, DN, MD = RT.ensure_data(SHA)
PX = RT.prices(sha, DN, 3); O, _ = SE.seam_open(PX)
CAL = pd.DatetimeIndex(PX["CAL"]); C = PX["C"]; BAD = PX["BAD"]; TRD = PX["TRD"]; IX = PX["ix"]
tri = pd.read_csv(io.BytesIO(tsh("data/history/market_tri.csv"))); tri["date"] = pd.to_datetime(tri["date"])
tri = tri.dropna().drop_duplicates("date").set_index("date")["close"].sort_index()


def trv(d):
    return float(tri[tri.index <= d].iloc[-1])


def ent(i, ym):
    first = (pd.Period(ym, "M") + 1).start_time
    return [p for p in range(len(CAL)) if CAL[p] >= first and TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p])][0]


def settle(i, e, tgt):
    """tgt None ⇒ 資料尾。回 (R, M, X, 未到, skip)。"""
    if tgt is not None and tgt > CAL[-1]:
        return None, None, None, True, False
    lim = CAL[-1] if tgt is None else tgt
    valid = [p for p in range(e, len(CAL)) if CAL[p] <= lim and np.isfinite(C[i, p])]
    x = valid[-1]
    if BAD[i, e + 1:x + 1].any() or (len(CAL) - 1 - x >= 5 and tgt is None):
        return None, None, None, False, True
    R = C[i, x] / O[i, e] - 1 - 0.00585; M = trv(CAL[x]) / trv(CAL[e - 1]) - 1
    return R, M, R - M, False, False


RW = pd.read_csv(os.path.join(OUT, "rows.csv"), dtype={"代號": str, "H": str})
val = {}       # (k, c, seg, H) -> 超額 或 "未到"
for k, s in sig.items():
    for c in keep[k]:
        i = IX[c]; e = ent(i, s["m1"])
        e2 = ent(i, s["m2"]) if s["m2"] else None
        if e2 is not None and e2 <= e:
            e2 = None
        jobs = [("燈1", H, e, None if H == "末" else CAL[e] + pd.DateOffset(months=H)) for H in (12, 24, "末")]
        if e2 is not None:
            jobs += [("加碼(a)", H, e2, None if H == "末" else CAL[e2] + pd.DateOffset(months=H)) for H in (12, 24, "末")]
            for H in (12, 24):
                t = CAL[e] + pd.DateOffset(months=H)
                if CAL[e2] < t:
                    jobs.append(("加碼(b)", H, e2, t))
        for seg, H, ee, t in jobs:
            R, M, X, ny, skip = settle(i, ee, t)
            rr = RW[(RW["訊號"] == k) & (RW["代號"] == c) & (RW["段"] == seg) & (RW["H"] == str(H))]
            if skip:
                res.append(f"--  {k} {c} {seg} {H} 窗內壞根／下市，check 不重算"); val[(k, c, seg, str(H))] = float(rr["超額"].iloc[0]); continue
            if ny:
                okk = len(rr) == 1 and str(rr["未到"].iloc[0]) == "True"; bad += (not okk)
                res.append(f"{'OK ' if okk else 'BAD'} {k} {c} {seg} {H} 未到"); val[(k, c, seg, str(H))] = "未到"; continue
            cmp(f"{k} {c} {seg} {H} R（進 {CAL[ee].date()}）", R, rr["R"].iloc[0]); cmp(f"{k} {c} {seg} {H} 超額", X, rr["超額"].iloc[0])
            val[(k, c, seg, str(H))] = X
# 主程式多出的格？
extra = RW[RW["R"].notna() & RW["入選"].astype(str).eq("True")]
miss = [f"{r.訊號} {r.代號} {r.段} {r.H}" for r in extra.itertuples() if (r.訊號, r.代號, r.段, r.H) not in val]
okk = not miss; bad += (not okk); res.append(f"{'OK ' if okk else 'BAD'} 主程式入選格都在 check 內（多出：{miss[:10]}）")


# ③ 統計
def sv(k, seg, H):
    cs = keep[k]
    if not cs:
        return np.nan, False
    xs = [val.get((k, c, seg, H)) for c in cs]
    if any(x == "未到" for x in xs):
        return np.nan, True
    xs = [x for x in xs if x is not None]
    return (float(np.mean(xs)) if len(xs) == len(cs) else np.nan), False


def hs(v):
    v = np.array([x for x in v if np.isfinite(x)])
    return {"n": len(v), ">0": (v > 0).mean() if len(v) else np.nan, "≥+1": (v >= 1).mean() if len(v) else np.nan,
            "≥+2": (v >= 2).mean() if len(v) else np.nan, "平均": v.mean() if len(v) else np.nan, "中位": np.median(v) if len(v) else np.nan}


ST = pd.read_csv(os.path.join(OUT, "stats.csv"), dtype={"H": str})


def stget(**kw):
    d = ST
    for a, b in kw.items():
        d = d[d[a] == b]
    return d.iloc[0]


for ver in ("甲", "乙"):
    for ty in ("全部", "缺貨", "新需求", "政策"):
        ks = [k for k, s in sig.items() if s[ver] and s["codes"] and keep[k] and (ty == "全部" or s["型"] == ty)]
        for H in ("12", "24", "末"):
            x1 = {k: sv(k, "燈1", H)[0] for k in ks}
            h = hs(list(x1.values())); s = stget(表="命中率", 版=ver, 型=ty, H=H, 單位="訊號", 量="超額")
            cmp(f"{ver} {ty} {H} 命中 n", h["n"], s["n"])
            for f in (">0", "≥+1", "≥+2", "平均", "中位"):
                cmp(f"{ver} {ty} {H} 命中 {f}", h[f], s[f])
            # 加碼
            for seg in (("加碼(a)", "加碼(b)") if H != "末" else ("加碼(a)",)):
                av = [2 * sv(k, seg, H)[0] for k in ks if sig[k]["m2"]]
                if not av:
                    continue
                h2 = hs(av); s2 = stget(表="加碼2份", 版=ver, 型=ty, H=H, 單位="訊號", 量=seg)
                cmp(f"{ver} {ty} {H} {seg} 2份 n", h2["n"], s2["n"]); cmp(f"{ver} {ty} {H} {seg} 2份 平均", h2["平均"], s2["平均"])
                cmp(f"{ver} {ty} {H} {seg} 2份 中位", h2["中位"], s2["中位"])
            # 甲乙
            A = {k: sv(k, "加碼(a)" if H == "末" else "加碼(b)", H)[0] for k in ks}
            yi = [x1[k] + 2 * A[k] if np.isfinite(A[k]) else x1[k] for k in ks]
            yr = [(x1[k] + 2 * A[k]) / 3 if np.isfinite(A[k]) else x1[k] for k in ks]
            for lab, v in (("乙有加碼(總損益)", yi), ("乙有加碼(÷投入份數)", yr)):
                h3 = hs(v); s3 = stget(表="甲乙", 版=ver, 型=ty, H=H, 量=lab)
                cmp(f"{ver} {ty} {H} {lab} 平均", h3["平均"], s3["平均"]); cmp(f"{ver} {ty} {H} {lab} 中位", h3["中位"], s3["中位"])
log = "\n".join(res) + f"\n\n不符 {bad} 格／共 {sum(1 for x in res if x[:3] in ('OK ', 'BAD'))} 格\n"
open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write(log)
json.dump({"不符": bad, "格數": sum(1 for x in res if x[:3] in ('OK ', 'BAD'))}, open(os.path.join(OUT, "check.json"), "w"))
print("\n".join(x for x in res if not x.startswith("OK")) + f"\n不符 {bad} 格／共 {sum(1 for x in res if x[:3] in ('OK ', 'BAD'))} 格")

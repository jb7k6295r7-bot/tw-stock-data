# -*- coding: utf-8 -*-
"""researchLampCensus 獨立重算（⛔ 不 import researchLampCensus／researchV41EV；自讀清單、自算市值、自取進場與結算日、自算統計）——回測線計算子代理。
① 每檔市值（自讀 data/stocks 原檔）與下限判定 → 對 caps.csv；
② 每檔×每段（燈1 12／24／末、加碼(a) 12／24／末、加碼(b) 12／24）R、超額 → 對 rows.csv（窗內有壞根或下市者 check 不重算、照列）；
③ 自建訊號值、自判情境（照實／寬鬆／嚴格，看「判定把握」欄）與類別（傳產／電子／合計）→
   中位、最好、最壞、P25、P75、平均、命中率（燈 1 那 1 份、加碼 2 份 (a)(b)、甲乙兩版）→ 對 stats.csv；欄缺時確認只出照實。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus_check [--out 目錄]
"""
import argparse
import glob
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

ap = argparse.ArgumentParser(); ap.add_argument("--out", default="backtest/resultsLampCensus"); OUT = ap.parse_args().out
SHA = "9b0e9882572c"
TOL = 1e-9
res = []; bad = 0


def cmp(tag, a, b, tol=TOL):
    global bad
    a = float(a) if a is not None else np.nan; b = float(b) if b is not None else np.nan
    ok = (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) < tol)
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}: 重算 {a:.10f} ／ 主程式 {b:.10f}")


def flag(tag, ok):
    global bad
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}")


def tsh(path):
    return subprocess.run(["git", "show", f"{SHA}:{path}"], capture_output=True, check=True).stdout


files = sorted(glob.glob(os.path.join(OUT, "signals_input*.csv")), key=lambda f: (f != os.path.join(OUT, "signals_input.csv"), f))
EL = ("半導體", "電腦", "光電", "通信網路", "電子零組件"); TR = {"水泥", "食品", "塑膠", "紡織", "電機機械", "電器電纜"}
sig = {}; seen = set(); has_sure = False; has_sure2 = False; has_self = False
for k, f in enumerate(files, 1):
    D = pd.read_csv(f, dtype=str, keep_default_na=False)
    vc = [c for c in D.columns if c.startswith("版本")][0]
    sc = [c for c in D.columns if "把握" in c and "燈2" not in c]; sc2 = [c for c in D.columns if "把握" in c and "燈2" in c]
    cc = [c for c in D.columns if "代碼" in c]
    sf = [c for c in D.columns if "判燈者自評" in c]
    has_sure |= bool(sc); has_sure2 |= bool(sc2); has_self |= bool(sf)
    for _, r in D.iterrows():
        key = r["訊號編號"] if (k == 1 or r["訊號編號"] not in seen) else f"F{k}:{r['訊號編號']}"
        cl = None
        if cc and re.match(r"^\s*\d", r[cc[0]]):
            n = int(re.match(r"^\s*(\d+)", r[cc[0]]).group(1)); cl = "電子" if 24 <= n <= 28 else ("傳產" if 1 <= n <= 6 else None)
        if cl is None:
            cl = "電子" if any(r["產業"].strip().startswith(x) for x in EL) else ("傳產" if r["產業"].strip() in TR else "其他")
        cs = [x.split()[0] for x in (r["公司1"], r["公司2"], r["公司3"]) if x.strip() and x.strip() != "無點名"]
        y, q = r["燈1季"].split("Q"); m1 = f"{y}-{int(q) * 3:02d}"
        m2 = None
        if r["燈2季"].strip():
            y2, q2 = r["燈2季"].split("Q"); m2 = f"{y2}-{int(q2) * 3:02d}"
        sig[key] = {"甲": r[vc] in ("甲", "兩版"), "乙": r[vc] in ("乙", "兩版"), "型": r["型"], "codes": cs, "m1": m1, "m2": m2, "類": cl,
                    "兩可": bool(sc) and r[sc[0]].strip() == "兩可", "燈2兩可": bool(sc2) and r[sc2[0]].strip() == "兩可",
                    "知道": bool(sf) and r[sf[0]].strip() == "知道"}
    seen |= {kk for kk in sig}
res.append(f"--  清單 {len(files)} 份、訊號 {len(sig)}；判定把握欄 {'有' if has_sure else '缺'}；燈2把握欄 {'有' if has_sure2 else '缺'}；自評欄 {'有' if has_self else '缺'}")

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
    if tgt is not None and tgt > CAL[-1]:
        return None, True, False
    lim = CAL[-1] if tgt is None else tgt
    valid = [p for p in range(e, len(CAL)) if CAL[p] <= lim and np.isfinite(C[i, p])]
    x = valid[-1]
    fin = np.flatnonzero(np.isfinite(C[i])); lastv = int(fin[-1]); xcal = int(np.searchsorted(CAL, lim, "right")) - 1
    if BAD[i, e + 1:x + 1].any() or (len(CAL) - 1 - lastv >= 5 and lastv < xcal):
        return None, False, True
    R = C[i, x] / O[i, e] - 1 - 0.00585
    return (R, R - (trv(CAL[x]) / trv(CAL[e - 1]) - 1)), False, False


RW = pd.read_csv(os.path.join(OUT, "rows.csv"), dtype={"代號": str, "H": str})
val = {}
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
            out, ny, skip = settle(i, ee, t)
            rr = RW[(RW["訊號"] == k) & (RW["代號"] == c) & (RW["段"] == seg) & (RW["H"] == str(H))]
            if skip:
                res.append(f"--  {k} {c} {seg} {H} 窗內壞根／下市，check 不重算"); val[(k, c, seg, str(H))] = float(rr["超額"].iloc[0]); continue
            if ny:
                flag(f"{k} {c} {seg} {H} 未到", len(rr) == 1 and str(rr["未到"].iloc[0]) == "True"); val[(k, c, seg, str(H))] = "未到"; continue
            cmp(f"{k} {c} {seg} {H} R（進 {CAL[ee].date()}）", out[0], rr["R"].iloc[0]); cmp(f"{k} {c} {seg} {H} 超額", out[1], rr["超額"].iloc[0])
            val[(k, c, seg, str(H))] = out[1]
extra = RW[RW["R"].notna() & RW["入選"].astype(str).eq("True")]
miss = [f"{r.訊號} {r.代號} {r.段} {r.H}" for r in extra.itertuples() if (r.訊號, r.代號, r.段, r.H) not in val]
flag(f"主程式入選格都在 check 內（多出：{miss[:10]}）", not miss)


# ③ 統計
def sv(k, seg, H):
    cs = keep[k]
    if not cs:
        return np.nan
    xs = [val.get((k, c, seg, H)) for c in cs]
    if any(x == "未到" for x in xs) or any(x is None for x in xs):
        return np.nan
    return float(np.mean(xs))


def st(v):
    v = np.array([x for x in v if np.isfinite(x)])
    if not len(v):
        return {"n": 0}
    return {"n": len(v), "中位": np.median(v), "最好": v.max(), "最壞": v.min(), "P25": np.percentile(v, 25), "P75": np.percentile(v, 75), "平均": v.mean(),
            ">0": (v > 0).mean(), "≥+1": (v >= 1).mean(), "≥+2": (v >= 2).mean()}


ST = pd.read_csv(os.path.join(OUT, "stats.csv"), dtype={"H": str})
scen_main = sorted(ST["情境"].unique())
want = {"照實"} | ({"寬鬆", "嚴格"} if has_sure else set()) | ({"剔自評知道"} if has_self else set())
flag(f"情境＝{scen_main}（應為 {sorted(want)}）", set(scen_main) == want)
cls = [c for c in ("傳產", "電子", "其他") if any(s["類"] == c for s in sig.values())]
groups = cls + (["合計"] if len(cls) > 1 else [])
flag(f"類別＝{sorted(ST['類'].unique())}（應為 {groups}）", set(ST["類"].unique()) == set(groups))


def stget(**kw):
    d = ST
    for a, b in kw.items():
        d = d[d[a] == b]
    return d.iloc[0] if len(d) else None


FIELDS = ("n", "中位", "最好", "最壞", "P25", "P75", "平均", ">0", "≥+1", "≥+2")
for sc in scen_main:
    for gp in groups:
        for ver in ("甲", "乙"):
            for ty in ("全部", "缺貨", "新需求", "政策"):
                ks = [k for k, s in sig.items() if s[ver] and s["codes"] and keep[k] and (ty == "全部" or s["型"] == ty) and (gp == "合計" or s["類"] == gp)
                      and not (sc == "嚴格" and s["兩可"]) and not (sc == "剔自評知道" and s["知道"])]
                if not ks:
                    continue
                dropa = {k: (sc == "嚴格" and sig[k]["燈2兩可"]) for k in ks}
                for H in ("12", "24", "末"):
                    x1 = {k: sv(k, "燈1", H) for k in ks}
                    h = st(list(x1.values())); s = stget(情境=sc, 類=gp, 表="燈1", 版=ver, 型=ty, H=H, 單位="訊號", 量="超額")
                    for f in FIELDS:
                        if h["n"] or f == "n":
                            cmp(f"{sc} {gp} {ver} {ty} {H} 燈1 {f}", h.get(f, np.nan), s[f])
                    for seg in (("加碼(a)", "加碼(b)") if H != "末" else ("加碼(a)",)):
                        av = [2 * sv(k, seg, H) for k in ks if sig[k]["m2"] and not dropa[k]]
                        if not av:
                            continue
                        h2 = st(av); s2 = stget(情境=sc, 類=gp, 表="加碼2份", 版=ver, 型=ty, H=H, 單位="訊號", 量=seg)
                        for f in ("n", "中位", "最好", "最壞", "P25", "P75", "平均"):
                            if h2["n"] or f == "n":
                                cmp(f"{sc} {gp} {ver} {ty} {H} {seg} 2份 {f}", h2.get(f, np.nan), s2[f])
                    A = {k: (np.nan if dropa[k] else sv(k, "加碼(a)" if H == "末" else "加碼(b)", H)) for k in ks}
                    yi = [x1[k] + 2 * A[k] if np.isfinite(A[k]) else x1[k] for k in ks]
                    yr = [(x1[k] + 2 * A[k]) / 3 if np.isfinite(A[k]) else x1[k] for k in ks]
                    for lab, v in (("乙有加碼(總損益)", yi), ("乙有加碼(÷投入份數)", yr)):
                        h3 = st(v); s3 = stget(情境=sc, 類=gp, 表="甲乙", 版=ver, 型=ty, H=H, 量=lab)
                        for f in ("中位", "最好", "最壞", "P25", "P75", "平均"):
                            if h3["n"]:
                                cmp(f"{sc} {gp} {ver} {ty} {H} {lab} {f}", h3[f], s3[f])
nn = sum(1 for x in res if x[:3] in ("OK ", "BAD"))
log = "\n".join(res) + f"\n\n不符 {bad} 格／共 {nn} 格\n"
open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write(log)
json.dump({"不符": bad, "格數": nn}, open(os.path.join(OUT, "check.json"), "w"))
print("\n".join(x for x in res if not x.startswith("OK")) + f"\n不符 {bad} 格／共 {nn} 格")

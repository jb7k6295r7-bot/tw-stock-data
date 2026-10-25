# -*- coding: utf-8 -*-
"""researchLampCensus_extra 獨立重算（⛔ 不 import researchLampCensus／_extra／researchV41EV；自讀面板、大盤、industry_pit、data/stocks）——回測線計算子代理。
① 對照 (a)：每檔 15 個季末進場的 12／24／末 超額平均 → 訊號值，對 extra_control.csv「對照a_*」（窗內有壞根或下市的格沿用主程式 rows 值不重算，照列）；
② 對照 (b)：抽 6 組（產業別、季）自算成員（industry_pit 當日段＋市值 ≥100 億）→ 對 extra_universe.csv 成員與 12／24／末 平均；
③ 訊號 − 對照的中位與勝過比例（照實、各類、甲乙、12／24／末）、年份中位、右尾（平均、去 1、去 3、中位）→ 對 extra_stats.csv；⛔ 自助法區間不重算（隨機）；
④ 每檔 24 月 絕對／相對 2 倍 → 對 extra_hit2.csv；⑤ 出處日次一交易日進場 每檔 12／24／末 超額 → 對 extra_alt_entry.csv。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus_extra_check [--out 目錄]
"""
import argparse
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

ap = argparse.ArgumentParser(); ap.add_argument("--out", default="backtest/resultsLampCensus"); OUT = ap.parse_args().out
SHA = "9b0e9882572c"; TOL = 1e-9
res = []; bad = 0


def cmp(tag, a, b, tol=TOL):
    global bad
    a = float(a); b = float(b)
    ok = (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) < tol)
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}: 重算 {a:.10f} ／ 主程式 {b:.10f}")


def flag(tag, ok):
    global bad
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}")


def tsh(path):
    return subprocess.run(["git", "show", f"{SHA}:{path}"], capture_output=True, check=True).stdout


sha, DN, MD = RT.ensure_data(SHA)
PX = RT.prices(sha, DN, 3); O, _ = SE.seam_open(PX)
CAL = pd.DatetimeIndex(PX["CAL"]); C = PX["C"]; BAD = PX["BAD"]; TRD = PX["TRD"]; IX = PX["ix"]; N = len(CAL)
tri = pd.read_csv(io.BytesIO(tsh("data/history/market_tri.csv"))); tri["date"] = pd.to_datetime(tri["date"])
tri = tri.dropna().drop_duplicates("date").set_index("date")["close"].sort_index()
tv = tri.values; ti = tri.index


def trv(d):
    return float(tv[ti.searchsorted(d, "right") - 1])


def ent_after(i, first, strict=False):
    p = int(CAL.searchsorted(first, "right" if strict else "left"))
    while p < N and not (TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p])):
        p += 1
    return p if p < N else None


FIN = {}


def lastv(i):
    if i not in FIN:
        FIN[i] = int(np.flatnonzero(np.isfinite(C[i]))[-1])
    return FIN[i]


def settle(i, e, H):
    """回 超額 或 'NY'（未到）或 'SKIP'（窗內壞根／下市）。"""
    tgt = None if H == "末" else CAL[e] + pd.DateOffset(months=int(H))
    if tgt is not None and tgt > CAL[-1]:
        return "NY"
    xcal = N - 1 if tgt is None else int(CAL.searchsorted(tgt, "right")) - 1
    lv = lastv(i)
    if BAD[i, e + 1:xcal + 1].any() or (N - 1 - lv >= 5 and lv < xcal):
        return "SKIP"
    x = xcal
    while not np.isfinite(C[i, x]):
        x -= 1
    return C[i, x] / O[i, e] - 1 - 0.00585 - (trv(CAL[x]) / trv(CAL[e - 1]) - 1)


RW = pd.read_csv(os.path.join(OUT, "rows.csv"), dtype={"代號": str, "H": str})
XC = pd.read_csv(os.path.join(OUT, "extra_control.csv"), dtype={"訊號": str})
ST = pd.read_csv(os.path.join(OUT, "extra_stats.csv"), dtype={"H": str, "年": str})
QE = [f"{y}-{m:02d}" for y in (2021, 2022, 2023, 2024) for m in (3, 6, 9, 12)][:15]
HS = ("12", "24", "末")

# ① 對照 (a)
skipped = 0
stockA = {}
for sid in sorted({c for s in XC["各檔"] for c in s.split("／")}):
    i = IX[sid]; acc = {H: [] for H in HS}; sk = {H: False for H in HS}
    for ym in QE:
        e = ent_after(i, (pd.Period(ym, "M") + 1).start_time)
        if e is None:
            continue
        for H in HS:
            v = settle(i, e, H)
            if v == "SKIP":
                sk[H] = True
            elif v != "NY":
                acc[H].append(v)
    stockA[sid] = {H: (np.nan if sk[H] else (np.mean(acc[H]) if acc[H] else np.nan)) for H in HS}
    skipped += sum(sk.values())
for _, r in XC.iterrows():
    cs = r["各檔"].split("／")
    for H in HS:
        v = [stockA[c][H] for c in cs]
        if any(np.isnan(x) for x in v):
            res.append(f"--  對照a {r['訊號']} {H}：有檔窗內壞根／下市或無值，check 不重算"); continue
        cmp(f"對照a {r['訊號']} {H}", np.mean(v), r[f"對照a_{H}"])
res.append(f"--  對照a 有壞根／下市不重算的 檔×段 {skipped}")

# ② 對照 (b) 抽 6 組
PT = pd.read_csv(io.BytesIO(tsh("data/meta/industry_hist/industry_pit.csv")), dtype=str, keep_default_na=False)
PT["s"] = pd.to_datetime(PT["start"].replace("", "1900-01-01")); PT["e"] = pd.to_datetime(PT["end"].replace("", "2262-01-01"))
UN = pd.read_csv(os.path.join(OUT, "extra_universe.csv"), dtype=str, keep_default_na=False)
pick = UN.sample(n=min(6, len(UN)), random_state=7)
CAPC = {}


def cap(sid, ym):
    if sid not in CAPC:
        t = subprocess.run(["git", "show", f"{SHA}:data/stocks/{sid}.csv"], capture_output=True)
        CAPC[sid] = pd.read_csv(io.BytesIO(t.stdout), dtype={"date": str}) if t.returncode == 0 else None
    D = CAPC[sid]
    if D is None:
        return np.nan
    m = D[D["date"].str.startswith(ym)]
    c = pd.to_numeric(m["close"], errors="coerce"); s = pd.to_numeric(m["shares"], errors="coerce")
    m = m[c > 0]
    if not len(m):
        return np.nan
    sh = s[(s > 0) & (c > 0)]
    return float(pd.to_numeric(m["close"]).iloc[-1]) * float(sh.iloc[-1]) if len(sh) else np.nan


for _, u in pick.iterrows():
    d = pd.Period(u["季末月"], "M").end_time.normalize()
    cand = sorted(set(PT[(PT["industry"] == u["產業別"]) & (PT["s"] <= d) & (PT["e"] >= d)]["stock_id"]) & set(IX))
    memb = [s for s in cand if np.isfinite(cap(s, u["季末月"])) and cap(s, u["季末月"]) >= 1e10]
    flag(f"對照b 成員 {u['產業別']} {u['季末月']}：重算 {len(memb)} 檔／主程式 {u['成員']}", "／".join(memb) == u["成員代號"])
    for H in HS:
        vals = []; sk = False
        for s in memb:
            e = ent_after(IX[s], (pd.Period(u["季末月"], "M") + 1).start_time)
            if e is None:
                continue
            v = settle(IX[s], e, H)
            if v == "SKIP":
                sk = True; break
            if v != "NY":
                vals.append(v)
        if sk:
            res.append(f"--  對照b {u['產業別']} {u['季末月']} {H} 有成員窗內壞根／下市，check 不重算"); continue
        cmp(f"對照b {u['產業別']} {u['季末月']} {H} 平均", np.mean(vals) if vals else np.nan, float(u[H]) if u[H] != "" else np.nan)


# ③ 統計
def sub(gp, ver):
    d = XC if gp == "合計" else XC[XC["類"] == gp]
    return d[d[ver].astype(bool)]


groups = sorted(set(ST["類"]))
for gp in groups:
    for ver in ("甲", "乙"):
        d = sub(gp, ver)
        for H in HS:
            for kind, lab in (("a", "同股任意季"), ("b", "同產業隨機")):
                df = (d[f"訊號_{H}"] - d[f"對照{kind}_{H}"]).dropna()
                s = ST[(ST["表"] == "對照") & (ST["情境"] == "照實") & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H) & (ST["對照"] == lab)].iloc[0]
                cmp(f"差中位 {gp} {ver} {H} {lab}", df.median(), s["差中位"]); cmp(f"勝過比例 {gp} {ver} {H} {lab}", (df > 0).mean(), s["勝過比例"])
                cmp(f"n {gp} {ver} {H} {lab}", len(df), s["n"])
            x = np.sort(d[f"訊號_{H}"].dropna().to_numpy())[::-1]
            s = ST[(ST["表"] == "右尾") & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H)].iloc[0]
            for lab, v in (("平均", x.mean()), ("去最大1平均", x[1:].mean()), ("去最大3平均", x[3:].mean()), ("中位", np.median(x))):
                cmp(f"右尾 {gp} {ver} {H} {lab}", v, s[lab])
            for y in ("2021", "2022", "2023", "2024"):
                q = d[(d["燈1季"].str[:4] == y) & d[f"訊號_{H}"].notna()]
                s = ST[(ST["表"] == "年份") & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H) & (ST["年"] == y)].iloc[0]
                if len(q):
                    cmp(f"年份 {gp} {ver} {H} {y} 超額中位", q[f"訊號_{H}"].median(), s["超額中位"]); cmp(f"年份 {gp} {ver} {H} {y} 大盤中位", q[f"大盤_{H}"].median(), s["大盤中位"])

# ④ 2 倍
HT = pd.read_csv(os.path.join(OUT, "extra_hit2.csv"), dtype={"代號": str})
for _, h in HT.iterrows():
    i = IX[h["代號"]]; e = int(CAL.searchsorted(pd.Timestamp(h["進場日"])))
    tgt = CAL[e] + pd.DateOffset(months=24); xcal = (N - 1) if tgt > CAL[-1] else int(CAL.searchsorted(tgt, "right")) - 1
    bb = np.flatnonzero(BAD[i, e + 1:xcal + 1]); xe = e + int(bb[0]) if len(bb) else xcal; xe = min(xe, lastv(i))
    ab = False; rel = False; m0 = trv(CAL[e - 1])
    for p in range(e, xe + 1):
        if np.isfinite(C[i, p]):
            g = C[i, p] / O[i, e]
            ab |= g >= 2; rel |= g / (trv(CAL[p]) / m0) >= 2
    flag(f"2倍 {h['訊號']} {h['代號']}：絕對 {ab}／相對 {rel}", (ab == bool(h["絕對2倍"])) and (rel == bool(h["相對2倍"])))

# ⑤ 出處日進場
AL = pd.read_csv(os.path.join(OUT, "extra_alt_entry.csv"), dtype={"代號": str, "H": str})
for _, a in AL.iterrows():
    i = IX[a["代號"]]; e = ent_after(i, pd.Timestamp(a["出處日期"]), strict=True)
    okd = str(CAL[e].date()) == a["進場日"]
    if not okd:
        flag(f"出處日進場日 {a['訊號']} {a['代號']}", False); continue
    v = settle(i, e, a["H"])
    if v in ("SKIP",):
        res.append(f"--  出處日 {a['訊號']} {a['代號']} {a['H']} 窗內壞根／下市，check 不重算"); continue
    if v == "NY":
        flag(f"出處日 {a['訊號']} {a['代號']} {a['H']} 未到", np.isnan(a["超額"])); continue
    cmp(f"出處日 {a['訊號']} {a['代號']} {a['H']}（進 {a['進場日']}）", v, a["超額"])

nn = sum(1 for x in res if x[:3] in ("OK ", "BAD"))
log = "\n".join(res) + f"\n\n不符 {bad} 格／共 {nn} 格（自助法區間不重算）\n"
open(os.path.join(OUT, "extra_check.log"), "w", encoding="utf-8").write(log)
json.dump({"不符": bad, "格數": nn}, open(os.path.join(OUT, "extra_check.json"), "w"))
print("\n".join(x for x in res if x.startswith("BAD"))[:3000] + f"\n不符 {bad} 格／共 {nn} 格；不重算 {sum(1 for x in res if x.startswith('--'))} 列")

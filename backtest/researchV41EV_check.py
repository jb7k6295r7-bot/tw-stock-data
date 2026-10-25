# -*- coding: utf-8 -*-
"""researchV41EV 獨立重算（不 import researchV41EV；自寫取日、結算、市值、成員、統計）——回測線計算子代理。
① 台股 9 檔、美股 8 檔（含同業與下市股）逐格重算 R、超額（60、72 月）；
② 台股 6 檔燈亮月月底市值（自讀 data/stocks、data/early/daily）；設下限剔除名單自判；
③ 三版 × 台美 × 4 個判決月的主題統計（平均、中位、s、門檻、p*、n）自 table.csv＋自建成員重算，對 stats.csv。
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
SHA = "9b0e9882572c"
TW_PICK = [("K31", "6488"), ("K52", "2049"), ("K13", "2408"), ("K45", "1909"), ("K46", "2498"),
           ("K22", "2303"), ("K45", "1907"), ("K53", "2542"), ("K12", "3481")]
US_PICK = [("K27", "MU"), ("K05", "ALB"), ("K09", "ANET"), ("K54", "ENPH"), ("K14", "AMD"), ("K09", "JNPR"), ("K25", "HPE"), ("K05", "FMC")]
CAP_PICK = [("K28", "2731"), ("K41", "2014"), ("K44", "3081"), ("K01", "3576"), ("K06", "8078"), ("K21", "8358")]
TB = pd.read_csv(os.path.join(OUT, "table.csv"), dtype={"代號": str})
CS = pd.read_csv(os.path.join(OUT, "cases_input.csv"), dtype=str).set_index("id")
res = []; bad = 0


def cmp(tag, a, b, tol=TOL):
    global bad
    ok = (np.isnan(a) and np.isnan(b)) or abs(a - b) < tol
    bad += (not ok); res.append(f"{'OK ' if ok else 'BAD'} {tag}: 重算 {a:.10f} ／ 主程式 {b:.10f}")


def tsh(path):
    return subprocess.run(["git", "show", f"{SHA}:{path}"], capture_output=True, check=True).stdout


# ── 0050 報酬（獨立公式）：raw1/raw0 ÷ Π_{d0<事件≤d1}(ref/pre)；事件用 git grep 掃 early/exright＋data/adj/0050.csv
_g = subprocess.run(["git", "grep", "-h", ",0050,", SHA, "--", "data/early/exright/"], capture_output=True, text=True).stdout.split("\n")
EV50 = []
for ln in _g:
    p = ln.split(",")
    if len(p) > 4 and p[1] == "0050":
        EV50.append((pd.Timestamp(p[0]), float(p[3]) / float(p[2])))
_A = pd.read_csv(io.BytesIO(tsh("data/adj/0050.csv")))
EV50 += [(pd.Timestamp(d), float(r) / float(q)) for d, q, r in zip(_A["date"], _A["pre_close"], _A["ref_price"])]
_S50 = pd.read_csv(io.BytesIO(tsh("data/stocks/0050.csv"))); _S50["date"] = pd.to_datetime(_S50["date"])
_S50 = _S50[_S50["close"] > 0].set_index("date")["close"]


def raw50(d):
    d = pd.Timestamp(d)
    if d >= pd.Timestamp("2015-01-01"):
        return float(_S50[_S50.index <= d].iloc[-1])
    for k in range(10):
        dd = d - pd.Timedelta(days=k)
        t = subprocess.run(["git", "show", f"{SHA}:data/early/daily/{dd.date()}.csv"], capture_output=True)
        if t.returncode == 0:
            E = pd.read_csv(io.BytesIO(t.stdout), dtype={"stock_id": str})
            q = E[(E["stock_id"] == "0050") & (E["close"] > 0)]
            if len(q):
                return float(q["close"].iloc[0])
    raise SystemExit(f"0050 {d} 查無")


def r50(d0, d1):
    f = np.prod([x for d, x in EV50 if pd.Timestamp(d0) < d <= pd.Timestamp(d1)]) if EV50 else 1.0
    return raw50(d1) / raw50(d0) / f - 1


res.append(f"--  0050 事件（check 自掃）{len(EV50)} 筆")
# ── ① 台股
sha, DN, MD = RT.ensure_data(SHA)
PX = RT.prices(sha, DN, 3); O, _ = SE.seam_open(PX)
CAL = pd.DatetimeIndex(PX["CAL"]); C = PX["C"]; BAD = PX["BAD"]; TRD = PX["TRD"]
tri = pd.read_csv(io.BytesIO(tsh("data/history/market_tri.csv")))
tri["date"] = pd.to_datetime(tri["date"]); tri = tri.dropna().drop_duplicates("date").set_index("date")["close"].sort_index()
for cid, sid in TW_PICK:
    i = PX["ix"][sid]; ym = CS.loc[cid, "燈亮月"]
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
        if len(CAL) - 1 - valid[-1] >= 5 and CAL[valid[-1]] < tgt:
            res.append(f"--  {cid} {sid} {H}月 下市，check 不重算"); continue
        x = valid[-1]
        R = C[i, x] / P0 - 1 - 0.00585
        Mk = tri[tri.index <= CAL[x]].iloc[-1] / tri[tri.index <= CAL[e - 1]].iloc[-1] - 1
        r = TB[(TB["id"] == cid) & (TB["代號"] == sid) & (TB["H月"] == H)].iloc[0]
        cmp(f"{cid} {sid} {H}月 R（進 {CAL[e].date()} 結 {CAL[x].date()}）", R, r["R"]); cmp(f"{cid} {sid} {H}月 超額（大盤）", R - Mk, r["超額"])
        cmp(f"{cid} {sid} {H}月 大盤報酬", Mk, r["大盤"])
        z = r50(CAL[e - 1], CAL[x]); cmp(f"{cid} {sid} {H}月 超額（0050，{CAL[e - 1].date()}→{CAL[x].date()}；容差 1e-6：因子欄 8 位小數 vs ref/pre 現算）", R - z, r["超額0050"], tol=1e-6)

# ── ① 美股：直接讀原始 csv（prices_yahoo 或 prices）
REPO = os.path.expanduser("~/us-stock-data")


def g(path):
    t = subprocess.run(["git", "-C", REPO, "show", f"origin/main:{path}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


SP = pd.read_csv(io.BytesIO(g("data/macro/yahoo_SP500TR.csv"))); SP["date"] = pd.to_datetime(SP["date"]); SP = SP[SP["adjclose"] > 0].set_index("date")["adjclose"].sort_index()
GS = pd.to_datetime(pd.read_csv(io.BytesIO(g("data/macro/yahoo_GSPC.csv")))["date"]).sort_values().reset_index(drop=True)
US_PICK += [("K02", "U"), ("K07", "ZIM"), ("K33", "CCJ"), ("K10", "DDD"), ("K40", "LCID"), ("K51", "PLUG"), ("K39", "DNNGY"), ("K16", "FSLR"), ("K50", "CGC")]


def yload(raw):
    P = pd.read_csv(io.BytesIO(raw)); P["date"] = pd.to_datetime(P["date"])
    P = P[(P["open"] > 0) & (P["close"] > 0) & (P["adjclose"] > 0)].sort_values("date").reset_index(drop=True)
    P["ao"] = P["open"] / P["close"] * P["adjclose"]; P["ac"] = P["adjclose"]
    return P


for cid, tk in US_PICK:
    first = (pd.Period(CS.loc[cid, "燈亮月"], "M") + 1).start_time
    P = None
    raw = g(f"data/prices_yahoo/{tk}.csv")
    if raw is not None:
        P = yload(raw)
        if P["date"].iloc[0] > first:
            P = None
    if P is None and g(f"data/prices/{tk}.csv") is not None:
        P = pd.read_csv(io.BytesIO(g(f"data/prices/{tk}.csv"))); P["date"] = pd.to_datetime(P["date"])
        P = P[(P["adjOpen"] > 0) & (P["adjClose"] > 0) & (P["close"] > 0)].sort_values("date").reset_index(drop=True)
        P["ao"] = P["adjOpen"]; P["ac"] = P["adjClose"]
    if P is None:
        P = yload(g(f"data/extra_yahoo/yahoo_{tk}.csv"))
    er = P[P["date"] >= first].iloc[0]; P0 = er["ao"]
    prevd = GS[GS < er["date"]].iloc[-1]
    for H in (60, 72):
        tgt = er["date"] + pd.DateOffset(months=H)
        if tk == "DNNGY":
            tgt = min(tgt, pd.Timestamp("2025-09-05"))     # Ørsted 配權未還原 ⇒ 截
        xr = P[P["date"] <= tgt].iloc[-1]
        R = xr["ac"] / P0 - 1 - 0.001
        Mk = SP[SP.index <= xr["date"]].iloc[-1] / SP[SP.index <= prevd].iloc[-1] - 1
        r = TB[(TB["id"] == cid) & (TB["代號"] == tk) & (TB["H月"] == H)].iloc[0]
        cmp(f"{cid} {tk} {H}月 R（進 {er['date'].date()} 結 {xr['date'].date()}）", R, r["R"]); cmp(f"{cid} {tk} {H}月 超額", R - Mk, r["超額"])

# ── ② 台股市值
CP = pd.read_csv(os.path.join(OUT, "caps.csv"), dtype={"代號": str})
for cid, sid in CAP_PICK:
    ym = CS.loc[cid, "燈亮月"]
    if ym < "2015-01":
        days = sorted(x.rsplit("/", 1)[1][:-4] for x in subprocess.run(["git", "ls-tree", "--name-only", SHA, "data/early/daily/"], capture_output=True, text=True).stdout.split() if x.rsplit("/", 1)[1].startswith(ym))
        v = np.nan
        for d in days[::-1]:
            E = pd.read_csv(io.BytesIO(tsh(f"data/early/daily/{d}.csv")), dtype={"stock_id": str})
            q = E[(E["stock_id"] == sid) & (E["close"] > 0)]
            if len(q):
                v = float(q["close"].iloc[0] * q["shares"].iloc[0]); break
    else:
        S = pd.read_csv(io.BytesIO(tsh(f"data/stocks/{sid}.csv")), dtype={"stock_id": str})
        q = S[S["date"].str.startswith(ym) & (S["close"] > 0)].iloc[-1]
        v = float(q["close"] * q["shares"])
    mine = CP[(CP["id"] == cid) & (CP["代號"] == sid)]["市值(億)"].iloc[0] * 1e8
    cmp(f"市值 {cid} {sid}（{ym} 月底）", v, mine, tol=1e-3)

# ── 自建成員（三版），自判下限
PT = pd.read_csv(os.path.join(OUT, "peers_input_TW.csv"), dtype=str, keep_default_na=False)
PU = pd.read_csv(os.path.join(OUT, "peers_input_US.csv"), dtype=str, keep_default_na=False)
PP = pd.concat([PT.assign(市場="TW"), PU.assign(市場="US")])
PP["n"] = pd.to_numeric(PP["名次"], errors="coerce"); PP = PP.sort_values(["id", "n"])
capv = {(r.id, str(r.代號)): r for r in CP.itertuples()}
mem = {"代表股版": {}, "同業等權版": {}, "設下限版": {}}
for cid, r in CS.iterrows():
    s = r["公司"]
    rep = s.split()[-1] if r["市場"] == "TW" else ("DNNGY" if s.startswith("Ørsted") else s.split("（")[0])   # K39 用美元 ADR（照主程式 ★）
    mem["代表股版"][cid] = [rep]
    lst = [c.strip() for c in PP[PP["id"] == cid]["代號"] if c.strip()]
    mem["同業等權版"][cid] = lst[:3]
    keep = []
    for c in lst:
        cr = capv.get((cid, c))
        if r["市場"] == "TW":
            small = cr is not None and np.isfinite(cr._10) and cr._10 * 1e8 < 1e10
        else:
            small = cr is not None and cr.判定 == "＜20億美元"
        if not small:
            keep.append(c)
    mem["設下限版"][cid] = keep[:3]
cutme = sorted(f"{cid} {c}" for cid in CS.index for c in mem["同業等權版"][cid] if c not in mem["設下限版"][cid])
MBf = pd.read_csv(os.path.join(OUT, "members.csv"), dtype={"代號": str})
cutmain = sorted(f"{r.id} {r.代號}" for r in MBf[(MBf["版"] == "設下限版") & (MBf["註"] == "市值不足、剔除")].itertuples())
ok = cutme == cutmain; bad += (not ok)
res.append(f"{'OK ' if ok else 'BAD'} 設下限剔除名單：重算 {cutme} ／ 主程式 {cutmain}")

# ── ③ 統計
ST = pd.read_csv(os.path.join(OUT, "stats.csv"))
for v in mem:
    for mk in ("TW", "US"):
        for H in (24, 36, 60, 72):
            d = TB[(TB["市場"] == mk) & (TB["H月"] == H) & TB["R"].notna()]
            vals = {}
            for cid in d["id"].unique():
                q = d[(d["id"] == cid) & d["代號"].isin(mem[v][cid])]
                if len(q):
                    vals[cid] = (q["結果"].iloc[0], q["超額"].mean())
            w = np.array([x for k_, (rs, x) in vals.items() if rs == "大漲"]); l = np.array([x for k_, (rs, x) in vals.items() if rs == "失敗"])
            if mk == "TW":
                v5 = {}
                for cid in d["id"].unique():
                    q = d[(d["id"] == cid) & d["代號"].isin(mem[v][cid])]
                    if len(q):
                        v5[cid] = (q["結果"].iloc[0], q["超額0050"].mean())
                w5 = np.array([x for _, (rs, x) in v5.items() if rs == "大漲"]); l5 = np.array([x for _, (rs, x) in v5.items() if rs == "失敗"])
                s5 = ST[(ST["版"] == v) & (ST["市場"] == mk) & (ST["H月"] == H) & (ST["樣本單位"] == "主題") & (ST["量"] == "超額0050")].iloc[0]
                cmp(f"{v} TW {H}月 0050版 贏家平均", w5.mean(), s5["贏家平均"]); cmp(f"{v} TW {H}月 0050版 反例中位", float(np.median(l5)), s5["反例中位"])
                if l5.mean() < 0:
                    cmp(f"{v} TW {H}月 0050版 p*_平均", -l5.mean() / (w5.mean() - l5.mean()), s5["p*_平均"])
            s = ST[(ST["版"] == v) & (ST["市場"] == mk) & (ST["H月"] == H) & (ST["樣本單位"] == "主題") & (ST["量"] == "超額")].iloc[0]
            mu = l.mean(); sd = np.sqrt(((l - mu) ** 2).sum() / (len(l) - 1))
            tag = f"{v} {mk} {H}月"
            cmp(f"{tag} 贏家平均", w.mean(), s["贏家平均"]); cmp(f"{tag} 贏家中位", float(np.median(w)), s["贏家中位"])
            cmp(f"{tag} 反例平均", mu, s["反例平均"]); cmp(f"{tag} 反例中位", float(np.median(l)), s["反例中位"])
            cmp(f"{tag} 反例 s", sd, s["反例s"]); cmp(f"{tag} 門檻", mu - 1.28 * sd / math.sqrt(8), s["門檻μ−1.28s/√8"])
            for k, W, L in (("平均", w.mean(), mu), ("中位", np.median(w), np.median(l))):
                if L < 0 and W > 0:
                    p = -L / (W - L); n = math.ceil(math.log(0.1) / math.log(1 - p))
                    cmp(f"{tag} p*_{k}", p, s[f"p*_{k}"]); cmp(f"{tag} n_{k}", float(n), float(s[f"n_{k}"]))
                else:
                    okk = not np.isfinite(s[f"p*_{k}"]); bad += (not okk)
                    res.append(f"{'OK ' if okk else 'BAD'} {tag} p*_{k}：反例 ≥0 ⇒ 不適用")
log = "\n".join(res) + f"\n\n不符 {bad} 格／共 {sum(1 for x in res if x[:3] in ('OK ', 'BAD'))} 格\n"
open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write(log)
json.dump({"不符": bad, "格數": len(res)}, open(os.path.join(OUT, "check.json"), "w"))
print(log)

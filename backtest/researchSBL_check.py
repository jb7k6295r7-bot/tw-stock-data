# -*- coding: utf-8 -*-
"""researchSBL 的獨立查核（⛔ 不 import researchSBL）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSBL_check.py

① 量測值：抽 40 個股-月（panel_month），自己讀原始檔（借券日檔、stocks 成交量與股數、stocks_inst）重算 S／I／F（L 5／20／60）與 B ⇒ 相對差 ≤ 1e−9
② 報酬與基準②：抽 1 個確認段的月，自己讀該月分組池全部股票（D.load_stock 接合版面）算 R_20 與前 20 日報酬、自己分十分位 ⇒ X_20 對 panel_month（差 ≤ 1e−12）
③ 單筆層格：從 panel_month 自己分十分位（同值依代號序）、自己做兩組差與月分群 CR0、n_eff、出口、Bonferroni k、成本帶 ±0.585%、判定、「穩」⇒ 對 cells_single.csv
④ 組合層：從 and_filter.csv.gz 自己組 12 格的保留列 ⇒ 對 summary 保留筆數；自己套 K7、挑格、0050 同段標籤、件標籤；
   挑中格與原版各重跑種子 0（自己呼叫 research11.simulate_mtm、自己組訊號）⇒ 探索／確認年化對 seeds_main.csv.gz
⑤ 甲的「最高十分位」旗標：抽 3 筆 AND 列，自己讀當月 panel_ext eligible 全部股票、自己算 S ⇒ 旗標相同
⚠ 範圍：①② 是抽查；早年組合層只核保留筆數與標籤，⛔ 沒有重跑早年引擎
⇒ backtest/resultsSBL/check.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from statistics import NormalDist

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

OUT = "backtest/resultsSBL"
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_edc6f8002f/data")
EINST = os.path.expanduser("~/earlydata/950ad26e12/main/data/stocks_inst")
MAIN = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
UD = os.path.expanduser("~/h2data/univ_aa964804e7/data/universe")
COST = 0.00585
HS = (5, 20, 60, 120)
RP = dict(float_precision="round_trip")
errs = []; info = {}
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
PM = pd.read_csv(os.path.join(OUT, "panel_month.csv.gz"), dtype={"sid": str}, **RP)
D.DATA = ST
cal = D.load_calendar(); dstr = [str(d.date()) for d in cal]
rng = np.random.default_rng(20260928)


# ① 量測值
def nz(v):
    v = pd.to_numeric(v, errors="coerce")
    return float(v) if pd.notna(v) else 0.0


def raw_stock(sid):
    x = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")
    return x


def sbl_day(d):
    out = {}
    for sub in ("sbl", "otcsbl"):
        p = os.path.join(UD, sub, d + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"stock_id": str})
            for s, a, b in zip(x["stock_id"], x["sbl_sell"], x["sbl_balance"]):
                out[s] = (float(a) if pd.notna(a) else 0.0, float(b) if pd.notna(b) else 0.0)
    return out


SBLC = {}


def sbl_get(d):
    if d not in SBLC:
        SBLC[d] = sbl_day(d)
    return SBLC[d]


def inst_rows(sid):
    parts = []
    for p, lo, hi in ((os.path.join(EINST, sid + ".csv"), None, "2014-12-31"), (os.path.join(MAIN, "stocks_inst", sid + ".csv"), "2015-01-05", None)):
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str}).drop_duplicates("date")
            x = x[(x["date"] >= (lo or "0")) & (x["date"] <= (hi or "9"))]
            parts.append(x)
    return pd.concat(parts).set_index("date") if parts else None, [os.path.exists(os.path.join(EINST, sid + ".csv")), os.path.exists(os.path.join(MAIN, "stocks_inst", sid + ".csv"))]


cand = PM[np.isfinite(PM["I20"]) | np.isfinite(PM["S20"])]
smp = cand.iloc[rng.choice(len(cand), size=40, replace=False)]
nbad = 0; ncmp = 0
for _, r in smp.iterrows():
    sid, T = r["sid"], int(r["T"])
    rs = raw_stock(sid)
    sh = pd.to_numeric(rs["shares"], errors="coerce"); sh = sh.where(sh > 0).reindex(dstr[:T + 1]).ffill()
    shT = float(sh.iloc[-1]) if len(sh) else np.nan
    ins, has = inst_rows(sid)
    for L in (5, 20, 60):
        days = dstr[T - L + 1:T + 1]
        # S
        if days[0] >= "2015-01-05":
            vol = sum(nz(rs["volume"].get(d, 0)) for d in days)
            sb = sum(sbl_get(d).get(sid, (0.0, 0.0))[0] for d in days)
            mine = sb / vol if vol > 0 else np.nan
        else:
            mine = np.nan
        for k, v in ((f"S{L}", mine),):
            ncmp += 1
            a_, b_ = v, r[k]
            if not ((np.isnan(a_) and np.isnan(b_)) or (np.isfinite(a_) and np.isfinite(b_) and abs(a_ - b_) <= 1e-9 * max(1e-12, abs(b_)) + 1e-15)):
                nbad += 1; errs.append(f"① {sid} T{dstr[T]} {k} 自算 {a_} 檔 {b_}")
        # I、F
        ok = days[0] >= "2012-05-02" and np.isfinite(shT) and (days[0] >= "2015-01-05" or has[0]) and (days[-1] < "2015-01-05" or has[1])
        for k, col in ((f"I{L}", "trust"), (f"F{L}", "foreign")):
            if ok and ins is not None:
                v = sum(float(ins[col].get(d, 0) if pd.notna(ins[col].get(d, 0)) else 0) for d in days) / shT
            else:
                v = np.nan
            ncmp += 1
            b_ = r[k]
            if not ((np.isnan(v) and np.isnan(b_)) or (np.isfinite(v) and np.isfinite(b_) and abs(v - b_) <= 1e-9 * max(1e-12, abs(b_)) + 1e-15)):
                nbad += 1; errs.append(f"① {sid} T{dstr[T]} {k} 自算 {v} 檔 {b_}")
    vb = sbl_get(dstr[T]).get(sid, (0.0, 0.0))[1] / shT if (dstr[T] >= "2015-01-05" and np.isfinite(shT)) else np.nan
    ncmp += 1
    if not ((np.isnan(vb) and np.isnan(r["B"])) or abs(vb - r["B"]) <= 1e-9 * max(1e-12, abs(r["B"])) + 1e-15):
        nbad += 1; errs.append(f"① {sid} B")
info["① 抽查股-月／比對值／不同"] = [len(smp), ncmp, nbad]

# ② 一個確認段的月 X_20
m0 = sorted(PM.loc[PM["月"] >= "2022-01", "月"].unique())[int(rng.integers(0, 50))]
g = PM[PM["月"] == m0]
T = int(g["T"].iloc[0]); H = 20
mkd = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"].to_dict()
Rm, r20m = {}, {}
for sid in g["sid"]:
    st = D.load_stock(sid, mkd[sid], cal); c = st.df["close"].to_numpy(float); o = st.df["open"].to_numpy(float)
    cf = pd.Series(c).ffill().to_numpy(); v = np.flatnonzero(np.isfinite(c))
    Rm[sid] = cf[min(T + H, len(cal) - 1)] / o[T + 1] - 1.0
    k = np.searchsorted(v, T)
    r20m[sid] = c[v[k]] / c[v[k - 20]] - 1.0 if (k < len(v) and v[k] == T and k >= 20) else np.nan
pool = g[np.isfinite(g["R20"])]
sids = list(pool["sid"]); rr = np.array([Rm[s] for s in sids]); q = np.array([r20m[s] for s in sids])
okq = np.isfinite(q)
order = np.flatnonzero(okq)[np.lexsort((np.array(sids)[okq], q[okq]))]
dec = np.full(len(sids), -1); dec[order] = (np.arange(len(order)) * 10) // len(order)
xm = np.full(len(sids), np.nan)
for d_ in range(10):
    m = dec == d_
    if m.sum() >= 2:
        xm[m] = rr[m] - (rr[m].sum() - rr[m]) / (m.sum() - 1)
xd = pool["X20"].to_numpy(float)
dm = np.nanmax(np.abs(xm - xd)) if np.isfinite(xm).any() else np.nan
rdm = float(np.nanmax(np.abs(rr - pool["R20"].to_numpy(float))))
info["② 月／池／R 最大差／X 最大差／X 有無不一致"] = [m0, len(sids), rdm, float(dm), int((np.isfinite(xm) != np.isfinite(xd)).sum())]
if not (rdm <= 1e-12 and dm <= 1e-12 and (np.isfinite(xm) == np.isfinite(xd)).all()):
    errs.append("② X_20")

# ③ 單筆層格
C = pd.read_csv(os.path.join(OUT, "cells_single.csv"), **RP)
SEGM = {"早年": ("2012-08", "2016-12"), "探索": ("2017-03", "2021-12"), "確認": ("2022-01", "2026-08")}
FAV = {"S": 0, "B": 0, "I": 9, "F": 9}


def dec_of(v, sid):
    d = np.full(len(v), -1); ok = np.flatnonzero(np.isfinite(v))
    if len(ok):
        o_ = ok[np.lexsort((sid[ok], v[ok]))]; d[o_] = (np.arange(len(ok)) * 10) // len(ok)
    return d


mine = []
for vn in [f"{v}{L}" for v in "SIF" for L in (5, 20, 60)] + ["B"]:
    var = vn[0]; L = int(vn[1:]) if vn != "B" else None
    for sg, (x0, x1) in SEGM.items():
        lo_ = "2015-05" if (var in "SB" and sg == "早年") else x0; hi_ = "2016-12" if (var in "SB" and sg == "早年") else x1
        g = PM[(PM["月"] >= lo_) & (PM["月"] <= hi_)]
        if not len(g):
            continue
        dec = np.full(len(g), -1)
        for m_, idx in g.groupby("月").indices.items():
            dec[idx] = dec_of(g[vn].to_numpy(float)[idx], g["sid"].to_numpy()[idx])
        s0 = int(g["T"].min())
        for H in HS:
            x = g[f"X{H}"].to_numpy(float); ok = np.isfinite(x) & (dec >= 0); top = ok & (dec == 9); bot = ok & (dec == 0)
            if top.sum() < 2 or bot.sum() < 2:
                continue
            mt, mb = x[top].mean(), x[bot].mean(); Dv = mt - mb
            # CR0：兩組迴歸 β 的分群 SE ＝ 各組殘差按月加總
            mon = g["月"].to_numpy()
            ut = x[top] - mt; ub = x[bot] - mb
            st_ = pd.Series(ut).groupby(mon[top]).sum(); sb_ = pd.Series(ub).groupby(mon[bot]).sum()
            allm = sorted(set(st_.index) | set(sb_.index))
            # β 的影響函數：top 的每筆 u/nt、bot 的每筆 −u/nb
            ssum = np.array([st_.get(m, 0.0) / top.sum() - sb_.get(m, 0.0) / bot.sum() for m in allm])
            se = float(np.sqrt((ssum ** 2).sum()))
            Tt = g["T"].to_numpy()
            blk = lambda msk: len(set(((Tt[msk] - s0) // H).tolist()))
            ne = min(min(int(top.sum()), blk(top)), min(int(bot.sum()), blk(bot)))
            mine.append({"變數": var, "L": L, "H": H, "段": sg, "D": Dv, "SE": se, "n_eff": ne})
M = pd.DataFrame(mine)
M["描述"] = (M["變數"] == "B") | ((M["變數"] == "S") & (M["段"] == "早年"))
M["出口"] = np.where(M["n_eff"] < 30, "出口①", np.where(M["n_eff"] < 100, "出口②", "出口③"))
M["可判定"] = (~M["描述"]) & (M["n_eff"] >= 30)
k = M[M["可判定"]].groupby("段").size().to_dict()
info["③ k（自算／檔）"] = [k, S["單筆層 Bonferroni k"]]
if {s: int(k.get(s, 0)) for s in SEGM} != S["單筆層 Bonferroni k"]:
    errs.append("③ k")
res = []
for _, r in M.iterrows():
    z = NormalDist().inv_cdf(1 - 0.025 / max(k.get(r["段"], 1), 1))
    lo, hi = r["D"] - z * r["SE"], r["D"] + z * r["SE"]
    v = "測得出（＋）" if lo > COST else ("測得出（−）" if hi < -COST else "測不出")
    res.append(("描述：" if r["描述"] else "") + (v if (r["可判定"] or r["描述"]) else "出口①（不可判定）"))
M["結果"] = res
cc = C[np.isfinite(C["D"])].copy()
cc["L"] = cc["L"].astype("float"); M["L"] = M["L"].astype("float")
J = cc.merge(M, on=["變數", "L", "H", "段"], how="outer", suffixes=("", "_m"), indicator=True)
nb3 = int((J["_merge"] != "both").sum())
both = J[J["_merge"] == "both"]
nb3 += int((np.abs(both["D"] - both["D_m"]) > 1e-12).sum()) + int((np.abs(both["SE"] - both["SE_m"]) > 1e-10 * np.maximum(1, np.abs(both["SE"]))).sum())
nb3 += int((both["n_eff"] != both["n_eff_m"]).sum()) + int((both["結果"] != both["結果_m"]).sum())
info["③ 格數／不同"] = [int(len(both)), nb3]
if nb3:
    errs.append("③ 單筆層格")
# 穩
HS_ = list(HS); nst = 0
for (var, L, sg), g in M[M["可判定"]].groupby(["變數", "L", "段"]):
    g = g.set_index("H")
    for H in g.index:
        rv = g.loc[H, "結果"]
        if not rv.startswith("測得出"):
            continue
        i_ = HS_.index(H); nbh = [HS_[i_ + d] for d in (-1, 1) if 0 <= i_ + d < 4 and HS_[i_ + d] in g.index]
        mine_st = nbh and all(g.loc[h, "結果"] == rv for h in nbh)
        f = C[(C["變數"] == var) & (C["L"] == L) & (C["段"] == sg) & (C["H"] == H)]["穩不穩"].iloc[0]
        if bool(mine_st) != (f == "穩"):
            nst += 1; errs.append(f"③ 穩 {var}{L} {sg} H{H}")
info["③ 穩 不同"] = nst

# ④ 組合層
F = pd.read_csv(os.path.join(OUT, "and_filter.csv.gz"), dtype={"sid": str}, **RP)
Fm = F[F["世界"] == "主"]
nb4 = 0
for L in (5, 20, 60):
    top = Fm[f"S{L}_最高十分位"].astype(str).isin(["True", "1", "1.0"]).to_numpy()
    iv = Fm[f"I{L}"].to_numpy(float); fv = Fm[f"F{L}"].to_numpy(float)
    mA = ~top; mB = np.nan_to_num(iv, nan=-1) > 0; mC = np.nan_to_num(iv + fv, nan=-1) > 0
    for vn, mm in (("甲", mA), ("乙", mB), ("丙", mC), ("丁", mA & mB)):
        if int(mm.sum()) != S["過濾計數（主）"][f"{vn}_L{L}"]["保留"]:
            nb4 += 1; errs.append(f"④ 主 {vn}_L{L} 保留")
Fe = F[F["世界"] == "早年"]
for L in (5, 20, 60):
    iv = Fe[f"I{L}"].to_numpy(float); fv = Fe[f"F{L}"].to_numpy(float)
    for vn, mm in (("乙", np.nan_to_num(iv, nan=-1) > 0), ("丙", np.nan_to_num(iv + fv, nan=-1) > 0)):
        if int(mm.sum()) != S["過濾計數（早年）"][f"{vn}_L{L}"]["保留"]:
            nb4 += 1; errs.append(f"④ 早年 {vn}_L{L} 保留")
PT = pd.read_csv(os.path.join(OUT, "cells_combo.csv"), **RP)
B50 = S["0050 同段"]
lab = lambda c, m, b: "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")
for _, r in PT.iterrows():
    for sg in ("探索", "確認"):
        if lab(r[f"{sg}_年化"], r[f"{sg}_回落"], B50[sg]) != r[f"{sg}_標籤"]:
            nb4 += 1; errs.append(f"④ {r['格']} {sg} 標籤")
deg = PT[(PT["格"] != "原版") & ((PT["探索_持股"] < 10) | (PT["探索_現金"] > 0.30))]["格"].tolist()
cand = PT[(PT["格"] != "原版") & ~PT["格"].isin(deg)].copy()
cand["r_"] = cand["探索_年化"] / cand["探索_回落"].abs()
pk = cand.sort_values(["r_", "探索_年化"], ascending=[False, False]).iloc[0]["格"] if len(cand) else None
info["④ 退化／挑中（自算）"] = [deg, pk]
if deg != S["退化（挑前排除）"] or pk != S["挑中格"]:
    nb4 += 1; errs.append("④ 挑格")
EPT = pd.read_csv(os.path.join(OUT, "cells_combo_early.csv"), **RP)
eb = S["0050 早年"]["2012-08-01～2014-12-31"]
for _, r in EPT.iterrows():
    if lab(r["早年_年化"], r["早年_回落"], eb) != r["早年_標籤"]:
        nb4 += 1; errs.append(f"④ 早年 {r['格']} 標籤")
# 種子 0 重跑
from backtest import rerun17 as RR
from backtest import listexit_lines as LL
from backtest import research11 as R11
ctx = LL.setup_t1(lambda x: None, t1=True)
G = RR._G; A = G["AND"]; e = A["entry_pos"].to_numpy(); sig = A[(e >= G["w0"]) & (e <= G["w1"])]
assert list(sig["sid"]) == list(Fm["sid"]) and list(sig["entry_pos"]) == list(Fm["entry_pos"])
SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), G["w1"])
SEED = pd.read_csv(os.path.join(OUT, "seeds_main.csv.gz"), **RP)
segp = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
for key in ["原版"] + ([pk] if pk else []):
    if key == "原版":
        s2 = sig
    else:
        vn, L = key.split("_L"); L = int(L)
        top = Fm[f"S{L}_最高十分位"].astype(str).isin(["True", "1", "1.0"]).to_numpy()
        iv = Fm[f"I{L}"].to_numpy(float); fv = Fm[f"F{L}"].to_numpy(float)
        mm = {"甲": ~top, "乙": np.nan_to_num(iv, nan=-1) > 0, "丙": np.nan_to_num(iv + fv, nan=-1) > 0,
              "丁": (~top) & (np.nan_to_num(iv, nan=-1) > 0)}[vn]
        s2 = sig[mm]
    o = R11.simulate_mtm(s2, "H60", 20, np.random.default_rng(7000), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True,
                         log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
    eq = np.asarray(o["equity"], float)
    for sg, (x, y) in segp.items():
        a_, b_ = int(ctx["cal"].searchsorted(pd.Timestamp(x))), int(ctx["cal"].searchsorted(pd.Timestamp(y)))
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], a_, b_)
        ref = SEED[(SEED["格"] == key) & (SEED["r"] == 0)].iloc[0]
        info[f"④ 種子0 {key} {sg}（自跑／檔）"] = [float(c_), float(ref[f"{sg}_年化"])]
        if repr(float(c_)) != repr(float(ref[f"{sg}_年化"])):
            nb4 += 1; errs.append(f"④ 種子0 {key} {sg}")
info["④ 不同"] = nb4

# ⑤ 甲 旗標
D.DATA = ST
mp = pd.read_csv("backtest/resultsp9_engine/panel_ext.csv.gz", dtype={"stock_id": str}, parse_dates=["measure_date"])
mds = sorted(mp["measure_date"].unique())
nb5 = 0
pick_rows = rng.choice(len(Fm), size=3, replace=False)
for j in pick_rows:
    r = Fm.iloc[j]; L = 20
    d = r["資料日"]; T = dstr.index(d); ee = pd.Timestamp(dstr[T + 1])
    md = max(m for m in mds if m <= ee)
    uni = mp[(mp["measure_date"] == md) & mp["eligible"].astype(str).isin(["True", "1", "1.0"])]["stock_id"].tolist()
    days = dstr[T - L + 1:T + 1]
    SB = {dd: sbl_get(dd) for dd in days}
    vals = {}
    for s in sorted(set(uni) | {r["sid"]}):
        p = os.path.join(ST, "stocks", s + ".csv")
        if not os.path.exists(p):
            continue
        x = pd.read_csv(p, dtype={"date": str}, usecols=["date", "volume"]).drop_duplicates("date").set_index("date")["volume"]
        vol = sum(float(x.get(dd, 0) if pd.notna(x.get(dd, 0)) else 0) for dd in days)
        sb = sum(SB[dd].get(s, (0.0, 0.0))[0] for dd in days)
        vals[s] = sb / vol if vol > 0 else np.nan
    us = [s for s in sorted(uni) if s in vals and np.isfinite(vals[s])]
    v = np.array([vals[s] for s in us]); o_ = np.lexsort((np.array(us), v)); dq = np.empty(len(us), int); dq[o_] = (np.arange(len(us)) * 10) // len(us)
    if r["sid"] in us:
        mine_top = dq[us.index(r["sid"])] == 9
    else:
        mine_top = bool(np.isfinite(vals.get(r["sid"], np.nan)) and vals[r["sid"]] >= v[dq == 9].min())
    ftop = str(r["S20_最高十分位"]) in ("True", "1", "1.0")
    if mine_top != ftop:
        nb5 += 1; errs.append(f"⑤ {r['sid']} {d}")
info["⑤ 抽 AND 列／不同"] = [3, nb5]
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:40]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:15]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))

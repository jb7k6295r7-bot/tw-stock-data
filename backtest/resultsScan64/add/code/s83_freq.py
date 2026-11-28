# -*- coding: utf-8 -*-
"""scanadd：S83 漲停次數（官方漲跌停價）頻率表＋等價／退化檢查。⛔ 不碰任何報酬。
先跑 s83_limit.py（產 ~/scanadd/factors/S83.parquet、~/scanadd/s83/upoff.npz）。
頻率表：逐月函式 monthly() 直接執行 add/code/freq_add.py 的原始碼（唯一實作；freq_add.py 在 module 層會跑全部，不 import）。
相近價量因子：直接呼叫 code/factors.py 的 price_factors()（唯一實作），只把 save／save_events 換成存到記憶體、不寫檔；
  取 S83alt（research11 規則推算漲停價的 20 日漲停次數，64 格只當備註、沒跑）、S11 一價到底次數、S10 樂透型（20 日最大單日漲幅）、
  S02 短期反轉（21 日報酬）、S06 量能放大。
輸出 ~/scanadd/s83/：s83_freq.csv、freqmonthly_S83.csv、s83_degen.csv（逐月）、s83_degen_summary.csv。"""
import os, ast
import numpy as np, pandas as pd
import snap
import factors as F
D = snap.fix(); snap.check()

BASE = snap.BASE; FAC = os.path.join(BASE, "factors"); OUT = os.path.join(BASE, "s83")
U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
U = U_df.to_numpy(bool); sids = list(U_df.columns); me = pd.DatetimeIndex(pd.to_datetime(U_df.index))
assert sids == F.sids and list(me) == list(F.me_dates)
hold = np.array([str(d.to_period("M") + 1) for d in me])
seg = np.where((hold >= "2017-03") & (hold <= "2021-12"), "探索", np.where((hold >= "2022-01") & (hold <= "2026-08"), "確認", ""))
MIN_VAL = 50

FA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "freq_add.py")
_src = open(FA, encoding="utf-8").read()
_fn = [n for n in ast.parse(_src).body if isinstance(n, ast.FunctionDef) and n.name == "monthly"]
assert len(_fn) == 1
exec(compile(ast.get_source_segment(_src, _fn[0]), FA + "[monthly]", "exec"), globals())


def rd(code):
    return pd.read_parquet(os.path.join(FAC, f"{code}.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)


S83 = rd("S83")
d = monthly(S83); d.to_csv(os.path.join(OUT, "freqmonthly_S83.csv"), index=False)
LIMSHA = open(os.path.expanduser("~/s83_limits_data/SHA.txt")).read().split()[0]
r = dict(S號="S83", 因子="漲停次數（官方漲跌停價）",
         定義="形成月最後交易日往回 20 根內「收盤（未還原）≥ 當日官方漲停價」天數（有值根 ≥15）；取高；上市 pricelimit/<d>.limit_up、上櫃 otcpricelimit/<d 前一交易日>.next_limit_up；9999.95／0.01 排除、查不到不判")
for sg in ("探索", "確認"):
    x = d[d.seg == sg]
    r[f"可用月{sg}"] = int(x.usable.sum()); r[f"形成月數{sg}"] = len(x)
    r[f"母體中位{sg}"] = float(x.nuni.median()); r[f"有值中位{sg}"] = float(x.nval.median())
    r[f"可算比例中位{sg}"] = round(float((x.nval / x.nuni).median()), 4)
    r[f"前五分之一平均檔數{sg}"] = round(float(x.loc[x.usable, "ntop"].mean()), 1) if x.usable.any() else np.nan
    r[f"前組檔數中位{sg}"] = float(x.loc[x.usable, "ntop"].median()) if x.usable.any() else np.nan
    r[f"前組檔數最小{sg}"] = int(x.loc[x.usable, "ntop"].min()) if x.usable.any() else np.nan
    r[f"前組檔數最大{sg}"] = int(x.loc[x.usable, "ntop"].max()) if x.usable.any() else np.nan
    r[f"月換手中位{sg}"] = round(float(x.turnover.median()), 3) if x.turnover.notna().any() else np.nan
    r[f"值＝0比例中位{sg}"] = round(float(x.zero.median()), 4); r[f"值>0比例中位{sg}"] = round(float(x.pos.median()), 4)
r["標籤"] = "可跑（待裁定）"
r["可用日規則"] = "形成月最後交易日收盤後可得（官方漲停價、日線收盤皆當日公布）"
r["資料"] = f"官方漲跌停價 tw-stock-data {LIMSHA}；價量母體 {snap.SHA}"
fq = pd.DataFrame([r]); fq.to_csv(os.path.join(OUT, "s83_freq.csv"), index=False, encoding="utf-8-sig")
print(fq.T.to_string())

# 前組實際是「有漲停者」嗎：逐月前組＝值>0 的月數
pos_eq = []
for i in range(len(me)):
    if not seg[i]:
        continue
    ok = U[i] & np.isfinite(S83[i]); v = S83[i]
    pct = pd.Series(np.where(ok, v, np.nan)).rank(pct=True, method="average").to_numpy()
    top = ok & (pct > 0.8)
    pos_eq.append(dict(seg=seg[i], top=int(top.sum()), pos=int((ok & (v > 0)).sum()), val=int(ok.sum()), eq=bool((top == (ok & (v > 0))).all())))
pe = pd.DataFrame(pos_eq)

# ───── 相近價量因子：factors.price_factors() 原式，存記憶體 ─────
CAP = {}
F.save = lambda code, arr, binary=False: CAP.__setitem__(code, np.asarray(arr, float))
F.save_events = lambda code, ev: None
F.price_factors()
snap.check()
NEAR = ["S83alt", "S11", "S10", "S02", "S06"]


def sp(a, b, m):
    return pd.Series(a[m]).rank().corr(pd.Series(b[m]).rank()) if m.sum() > 10 else np.nan


def topset(v, u):
    ok = u & np.isfinite(v)
    pct = pd.Series(np.where(ok, v, np.nan)).rank(pct=True, method="average").to_numpy()
    return ok & (pct > 0.8), ok


rows = []
for i in range(len(me)):
    if not seg[i]:
        continue
    u = U[i]; t83, o83 = topset(S83[i], u)
    row = dict(form=str(me[i].date()), seg=seg[i], S83_top=int(t83.sum()))
    for c in NEAR:
        v = CAP[c][i]; tc, oc = topset(v, u)          # 前組一律取高（S02 取高＝近 21 日漲最多，與漲停次數同側）
        row[f"rho_{c}"] = sp(S83[i], v, o83 & oc)
        row[f"S83前組在{c}前組比例"] = (t83 & tc).sum() / max(t83.sum(), 1)
        row[f"{c}前組在S83前組比例"] = (t83 & tc).sum() / max(tc.sum(), 1)
        if c == "S83alt":
            row["值完全相同比例"] = float((S83[i][o83 & oc] == v[o83 & oc]).mean()) if (o83 & oc).any() else np.nan
    rows.append(row)
dg = pd.DataFrame(rows); dg.to_csv(os.path.join(OUT, "s83_degen.csv"), index=False)

# 逐日：官方漲停 vs research11 推算漲停（母體內有效根）
Z = np.load(os.path.join(OUT, "upoff.npz"))
UPo = Z["UP"].astype(float); UPr = np.where(F.VALID, F.M["UP"], np.nan)
kpos = me.searchsorted(F.cal, side="left") - 1
inU = np.zeros(UPo.shape, bool)
for t in range(len(F.cal)):
    if kpos[t] >= 0:
        inU[t] = U[kpos[t]]
both = inU & np.isfinite(UPo) & np.isfinite(UPr)
a = UPo[both] == 1; b = UPr[both] == 1
daily = dict(母體內兩者皆可判根=int(both.sum()), 官方漲停根=int(a.sum()), 推算漲停根=int(b.sum()), 兩者皆漲停=int((a & b).sum()),
             只有官方=int((a & ~b).sum()), 只有推算=int((~a & b).sum()), 官方可判但推算缺=int((inU & np.isfinite(UPo) & ~np.isfinite(UPr)).sum()))

summ = []
for sg in ("探索", "確認"):
    x = dg[dg.seg == sg]; p = pe[pe.seg == sg]
    for c in NEAR:
        summ.append(dict(段=sg, 相近因子=c, 月Spearman中位=round(x[f"rho_{c}"].median(), 3), 月Spearman最小=round(x[f"rho_{c}"].min(), 3),
                         月Spearman最大=round(x[f"rho_{c}"].max(), 3), S83前組落在其前組比例中位=round(x[f"S83前組在{c}前組比例"].median(), 3),
                         其前組落在S83前組比例中位=round(x[f"{c}前組在S83前組比例"].median(), 3),
                         值完全相同比例中位=round(x["值完全相同比例"].median(), 4) if c == "S83alt" else np.nan))
    summ.append(dict(段=sg, 相近因子="（前組＝值>0者 的月數）", 月Spearman中位=f"{int(p['eq'].sum())}／{len(p)}"))
sm = pd.DataFrame(summ); sm.to_csv(os.path.join(OUT, "s83_degen_summary.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame([daily]).to_csv(os.path.join(OUT, "s83_daily_official_vs_r11.csv"), index=False, encoding="utf-8-sig")
print(sm.to_string()); print(daily)
snap.check()

# -*- coding: utf-8 -*-
"""seq521 對帳：抽 10 檔，從原始 CSV 用另一條路手算，對 pool169_20261020.csv。
⛔ 不 import researchLongPool／research34／data（獨立路徑）；還原因子用 adj 的 factor 欄自己連乘（不用 cum_factor）。
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/resultsLongPool/_check.py
"""
import glob
import os
import re

import numpy as np
import pandas as pd

SHA = "5cb00a60c1fcdc6f2a388a9fbcb50a8812e32584"
H = os.path.expanduser(f"~/h2data/{SHA}/data")
FD = os.path.expanduser(f"~/longpoolwork/{SHA[:10]}/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsLongPool")
PICK = ["2330", "8299", "3661", "4971", "3718", "4573", "1623", "3289", "2464", "6669"]
SPL = {"3718": "5371"}
ASOF = pd.Timestamp("2026-10-20")

pool = pd.read_csv(os.path.join(OUT, "pool169_20261020.csv"), dtype={"stock_id": str}).set_index("stock_id")
cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(H, "meta", "calendar_twse.csv"))["date"]))
assert cal[-1] == ASOF


def rev_series(sid):
    L = []
    for f in glob.glob(os.path.join(H, "mops", "revenue_hist", "*.csv")):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
        x = x[x["stock_id"] == sid]
        if len(x):
            L.append(x)
    if not L:
        return None
    x = pd.concat(L).drop_duplicates("period", keep="last").set_index("period").sort_index()
    return x.astype(float)


def fs_ytd(sid, per, col):
    fs = glob.glob(os.path.join(FD, "mops", "fs_hist", f"{per}_ci_*.csv"))
    for f in fs:
        x = pd.read_csv(f, dtype={"stock_id": str})
        x = x[x["stock_id"] == sid]
        if len(x):
            return float(pd.to_numeric(x[col].iloc[0], errors="coerce")) * 1000
    return np.nan


def fin_ytd(sid, per, col):
    x = pd.read_csv(os.path.join(FD, "mops", "fin_hist", f"{per}.csv"), dtype={"stock_id": str})
    x = x[x["stock_id"] == sid]
    return float(x[col].iloc[0]) if len(x) else np.nan


def inv(sid, per):
    x = pd.read_csv(os.path.join(FD, "meta", "fs_xbrl", f"fs_xbrl_{per[:4]}.csv"), dtype={"stock_id": str})
    x = x[(x["stock_id"] == sid) & (x["period"] == per)]
    if not len(x):
        return np.nan
    x = x.sort_values("report")                 # cr < ir
    return float(x["inventories"].iloc[0])


def adj_close(sid):
    x = pd.read_csv(os.path.join(H, "stocks", f"{sid}.csv"), usecols=["date", "close", "volume"])
    x["date"] = pd.to_datetime(x["date"]); x = x.drop_duplicates("date").set_index("date").sort_index()
    x = x[x["close"] > 0]
    p = os.path.join(H, "adj", f"{sid}.csv")
    F = np.ones(len(x))
    if os.path.exists(p):
        a = pd.read_csv(p); a["date"] = pd.to_datetime(a["date"])
        for d, f in zip(a["date"], a["factor"].astype(float)):
            F[x.index < d] *= f
    x["ac"] = x["close"] * F
    return x


def px(sid):
    x = adj_close(sid)
    if sid in SPL:
        o = adj_close(SPL[sid]); x = pd.concat([o[o.index < x.index.min()], x])
    return x


rows = []
def cmp(sid, k, mine, col):
    v = pool.at[sid, col] if col in pool.columns else np.nan
    if isinstance(mine, (bool, np.bool_)) or isinstance(v, (bool, np.bool_)) or (isinstance(v, str) and v in ("True", "False")):
        ok = str(bool(mine)) == str(v) if not (isinstance(mine, float) and np.isnan(mine)) else pd.isna(v)
    else:
        a = float(mine) if mine is not None else np.nan; b = float(v) if not pd.isna(v) else np.nan
        ok = (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) <= 1e-4 * max(1, abs(b)))
    rows.append({"stock_id": sid, "項目": k, "手算": mine, "pool": v, "相符": bool(ok)})


md = open(os.path.expanduser(f"~/tw-p17/backtest/resultsDaily/daily_{ASOF.date()}.md"), encoding="utf-8").read()
sec = {k: re.search(rf"## {k}、.*?(?=\n## )", md, re.S).group(0) for k in ("一", "二", "三")}

for sid in PICK:
    # 月營收
    R = rev_series(sid)
    if R is not None and "2026-09" in R.index:
        r0, ly = R.at["2026-09", "當月營收"], R.at["2026-09", "去年當月營收"]
        cmp(sid, "營收 2026-09", r0, "rev_2026-09")
        cmp(sid, "年增 2026-09", r0 / ly - 1 if ly > 0 else np.nan, "yoy_2026-09")
        prev = pd.period_range("2024-09", "2026-08", freq="M").astype(str)
        h = R["當月營收"].reindex(prev)
        cmp(sid, "創24月高 2026-09", bool(r0 >= h.max()) if h.notna().all() else np.nan, "hi24_2026-09")
        ms = pd.period_range("2025-10", "2026-09", freq="M").astype(str)
        yy = (R["當月營收"] / R["去年當月營收"].where(R["去年當月營收"] > 0) - 1).reindex(ms)
        cmp(sid, "加速", yy.iloc[-3:].mean() - yy.mean() if yy.notna().all() else np.nan, "rev_accel")
    # 季報（3718 用 5371）
    s = SPL.get(sid, sid)
    for per, prv in (("2026Q2", "2026Q1"), ("2025Q4", "2025Q3")):
        c = fs_ytd(s, per, "營業成本") - fs_ytd(s, prv, "營業成本")
        rv = fs_ytd(s, per, "營業收入") - fs_ytd(s, prv, "營業收入")
        gp = fs_ytd(s, per, "營業毛利（毛損）淨額") - fs_ytd(s, prv, "營業毛利（毛損）淨額")
        if not np.isfinite(c):                                       # fs_hist 沒有 ⇒ fin_hist（另一來源）
            rv = fin_ytd(s, per, "rev_ytd") - fin_ytd(s, prv, "rev_ytd"); gp = fin_ytd(s, per, "gp_ytd") - fin_ytd(s, prv, "gp_ytd"); c = rv - gp
        iv = inv(s, per)
        fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype=str)
        fd = fd[(fd["stock_id"] == s) & (fd["year"] == per[:4]) & (fd["season"] == per[-1])]
        has_ts = len(fd) > 0
        cmp(sid, f"存貨天數 {per}", iv / c * 91.25 if (has_ts and np.isfinite(iv) and c > 0) else np.nan, f"inv_days_{per}")
        cmp(sid, f"毛利率 {per}", gp / rv if (has_ts and rv > 0) else np.nan, f"gm_{per}")
        # 交叉：fs_hist 營業成本 vs fin_hist（營收−毛利）
        if np.isfinite(c):
            c2 = (fin_ytd(s, per, "rev_ytd") - fin_ytd(s, prv, "rev_ytd")) - (fin_ytd(s, per, "gp_ytd") - fin_ytd(s, prv, "gp_ytd"))
            rows.append({"stock_id": sid, "項目": f"〔交叉〕{per} 營業成本 fs_hist vs fin_hist(營收−毛利)", "手算": c, "pool": c2,
                         "相符": bool(np.isfinite(c2) and abs(c - c2) <= 0.005 * abs(c2))})
    # 價格
    if pool.at[sid, "market"] != "emerging":
        x = px(sid); c = x["ac"]; last = c.iloc[-1]
        w = c[c.index > ASOF - pd.Timedelta(days=364)]
        cmp(sid, "離52週高", last / w.max() - 1, "pct_from_52w_high")
        b = c[c.index <= ASOF - pd.Timedelta(days=365)]
        cmp(sid, "近一年報酬", last / b.iloc[-1] - 1 if len(b) else np.nan, "ret_1y")
        me = pd.Timestamp("2026-09-30"); s0 = pd.Timestamp("2025-09-30")
        ww = c[(c.index > s0) & (c.index <= me)]
        if sid not in SPL and pool.at[sid, "pth_status"] == "排序母體":
            cmp(sid, "PTH 2026-09", ww.iloc[-1] / ww.max(), "pth_2026-09")
        ps = pd.read_csv(os.path.join(H, "stocks_per", f"{sid}.csv")) if os.path.exists(os.path.join(H, "stocks_per", f"{sid}.csv")) else None
        if ps is not None:
            ps["date"] = pd.to_datetime(ps["date"]); ps = ps.drop_duplicates("date").set_index("date")["per"]
            t = ps.get(ASOF, np.nan)
            h5 = ps[(ps.index > ASOF - pd.DateOffset(years=5)) & (ps > 0)].dropna()
            cmp(sid, "本益比", t if t > 0 else np.nan, "per")
            cmp(sid, "本益比5年百分位", (h5 <= t).mean() if t > 0 else np.nan, "per_pct5y")
    v = pd.read_csv(os.path.join(H, "stocks", f"{sid}.csv"), usecols=["date", "volume"]); v["date"] = pd.to_datetime(v["date"])
    v = v.drop_duplicates("date").set_index("date")["volume"]
    if sid in SPL:
        o = pd.read_csv(os.path.join(H, "stocks", f"{SPL[sid]}.csv"), usecols=["date", "volume"]); o["date"] = pd.to_datetime(o["date"])
        v = pd.concat([o.set_index("date")["volume"], v])
    cmp(sid, "20日均量(張)", v.reindex(cal[-20:]).fillna(0).mean() / 1000, "vol20_lots")
    cmp(sid, "營飆已達成", f"- {sid} " in sec["一"], "營飆v1已達成")
    cmp(sid, "營量已達成", f"- {sid} " in sec["二"], "營量v1已達成")
    cmp(sid, "營量即將達成", f"| {sid} " in sec["三"], "營量v1即將達成")

df = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print(df.to_string())
print(f"\n對帳 {len(df)} 項（含交叉 {df['項目'].str.startswith('〔交叉〕').sum()} 項）；相符 {int(df['相符'].sum())}；不符 {int((~df['相符']).sum())}")
print(df[~df["相符"]].to_string() if (~df["相符"]).any() else "全部相符")

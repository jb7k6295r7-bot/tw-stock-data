# -*- coding: utf-8 -*-
"""長線大漲段 第二階段補：毛利、營業利益相關欄改用 fs_xbrl 新三欄重產（資料庫 C 交件；描述、不判、不計 N）——回測線計算子代理。
⛔ 不 commit、不改既有檔（researchBigRun3、resultsBigRun3 只讀；新檔只在 resultsBigRun3/xbrl/）；私有資料 ⛔ 不讀；不做任何檢定。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun3b [--dry]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun3b_check [--dry]
輸出 backtest/resultsBigRun3/xbrl/：新舊對照_乙.csv、新舊對照_甲.csv、覆蓋率_年.csv、並排_乙_xbrl.csv、並排_甲_xbrl.csv、
     乙_xbrl欄.csv.gz、對照B_乙_xbrl欄.csv、甲_xbrl欄.csv、對照B_甲_xbrl欄.csv、對照C_xbrl欄.csv、bigrun3b.json、run.log

═══ 讀法（E 標；★＝執行者定；其餘 ＝ researchBigRun3 D1～D9 原樣）═══
 E1 受影響欄（7 欄）：毛利率、毛利率年變化、毛利率由降轉升、營業利益率、營業利益率年變化、營業利益率由降轉升、存貨天數（分母營業成本也換成新欄）。
    其餘欄（含合約負債÷單季營收、市值營收比等）不動，沿用 resultsBigRun3。
 E2 新來源 ＝ tw-stock-data origin/main（SHA 常數）meta/fs_xbrl：gross_profit_ytd（營業毛利（毛損）淨額）、operating_income_ytd、cost_of_sales_ytd、revenue_ytd、
    inventories；年初累計 ⇒ 單季（本季 − 前季，Q1 不減；前季缺 ⇒ 缺）；同 (代號, 期別) cr 合併優先（researchBigRun3 同）；2013Q1 起，2013 以前照實「無」。
    毛利率 ＝ 單季毛利 ÷ 單季營收（＞ 0）；營業利益率 ＝ 單季營業利益 ÷ 單季營收；存貨天數 ＝ 期末存貨 ÷ 單季營業成本（＞ 0）× 91.25；
    年變化 ＝ 本季 − 去年同季（百分點）；由降轉升 ＝ 本季年變化 ＞ 0 且前一季年變化 ≤ 0（D3 同式）。
 E3 ★ 時點用哪一季：沿用原面板（researchBigRun3）每格的「已上傳最新季」（filing_dates 上傳日 ＜ 月底，快照 dbfb96cb81a7）⇒ 新舊兩版只差資料來源，可逐格比；
    （新快照的 filing_dates 若選到不同季，對帳 K2 照報筆數，⛔ 不改。）
 E4 單位、時點、對照 A～D、併段、族群 ＝ resultsBigRun3 原樣（逐列讀 _i、_ind、_k 欄；⛔ 不重選段、不重選對照）；產業層 ＝ 當月成員中位數（旗標取比例）。
 E5 新舊對照：每欄 × 時點報 兩版各自有值數、兩版都有值數、中位、兩版差的中位與 |差| 中位、|差| ≤ 0.5 百分點（存貨天數 ≤ 1 天）比例；
    覆蓋率_年 ＝ 個股月底面板中「20 日內有成交」格的兩版有值率，逐年。
 E6 必附：沿用 researchBigRun3 D9；另加「資料庫 C 版毛利、營業利益 2013 起（含下市；金融業空白屬正常）」。外資持股 2024-08 後待資料庫，本件不動。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import pickle
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLongPool as LP                 # noqa: E402  qkey、qlabel

SHA = "bc6cfec3813cb276517d74d6910f78a66b4fee99"
WORK = os.path.expanduser("~/bgrwork")
SRC = "backtest/resultsBigRun3"
OUT = "backtest/resultsBigRun3/xbrl"
DAYS_Q = 91.25
QK0 = LP.qkey(2012, 1)
FEATS = ["毛利率", "毛利率年變化", "毛利率由降轉升", "營業利益率", "營業利益率年變化", "營業利益率由降轉升", "存貨天數"]
FLAGS = {"毛利率由降轉升", "營業利益率由降轉升"}
PTS = ("前12月", "起點", "高點前6月", "高點", "高點後6月")
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def ensure_arch():
    root = os.path.join(WORK, f"mainC_{SHA[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        subprocess.run(["git", "cat-file", "-e", SHA], check=True)
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", SHA, "data/meta/fs_xbrl", "data/meta/filing_dates.csv"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(SHA)
    return os.path.join(root, "data")


def single(a, j):
    """年初累計陣列 a（索引 j ↔ qk ＝ QK0 ＋ j）⇒ 單季。"""
    if j < 0 or not np.isfinite(a[j]):
        return np.nan
    if (QK0 + j) % 4 == 0:
        return a[j]
    return a[j] - a[j - 1] if j >= 1 and np.isfinite(a[j - 1]) else np.nan


def qstat(f, v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0, "中位": np.nan, "p25": np.nan, "p75": np.nan}
    if f in FLAGS:
        return {"n": int(len(v)), "中位": float(v.mean()), "p25": np.nan, "p75": np.nan}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p25": float(np.percentile(v, 25)), "p75": float(np.percentile(v, 75))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    src = os.path.join(WORK, "dry3") if a.dry else SRC
    out = os.path.join(WORK, "dry3b") if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    DATA = ensure_arch()
    log(f"[資料] fs_xbrl ＝ origin/main {SHA[:12]}｜面板 bgr3_panel_{'dry' if a.dry else 'full'}.pkl｜段與對照 ＝ {src}")
    PN = pickle.load(open(os.path.join(WORK, f"bgr3_panel_{'dry' if a.dry else 'full'}.pkl"), "rb"))
    SIDS = PN["SIDS"]; MEp = PN["MEp"]; K = len(MEp); N = len(SIDS); P = PN["P"]; META = PN["META"]; INDM = PN["INDM"]
    ids = set(SIDS)
    L = []
    for f in sorted(glob.glob(os.path.join(DATA, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "inventories", "revenue_ytd", "cost_of_sales_ytd",
                                                             "gross_profit_ytd", "operating_income_ytd"])
        x = x[x["stock_id"].isin(ids)].copy()
        x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        x["qk"] = [LP.qkey(p[:4], p[-1]) for p in x["period"]]
        L.append(x)
    X = pd.concat(L)
    cols = ["inventories", "revenue_ytd", "cost_of_sales_ytd", "gross_profit_ytd", "operating_income_ytd"]
    for c in cols:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    nQ = int(META["fs_qk"].max()) - QK0 + 6
    ARR = {}
    for s, g in X.groupby("stock_id"):
        d = {c: np.full(nQ, np.nan) for c in cols}
        jj = g["qk"].to_numpy(int) - QK0; ok = (jj >= 0) & (jj < nQ)
        for c in cols:
            d[c][jj[ok]] = g[c].to_numpy(float)[ok]
        rq = np.array([single(d["revenue_ytd"], j) for j in range(nQ)]); gq = np.array([single(d["gross_profit_ytd"], j) for j in range(nQ)])
        oq = np.array([single(d["operating_income_ytd"], j) for j in range(nQ)]); cq = np.array([single(d["cost_of_sales_ytd"], j) for j in range(nQ)])
        with np.errstate(invalid="ignore", divide="ignore"):
            gm = np.where(rq > 0, gq / rq, np.nan); om = np.where(rq > 0, oq / rq, np.nan)
            ivd = np.where(cq > 0, d["inventories"] / cq * DAYS_Q, np.nan)
        ARR[s] = {"gm": gm, "om": om, "ivd": ivd}
    log(f"[fs_xbrl] {len(X)} 列、{len(ARR)} 檔｜期別 {X['period'].min()}～{X['period'].max()}｜{time.time() - t0:.0f}s")

    def at(arr, j):
        return arr[j] if 0 <= j < len(arr) else np.nan
    NP = {f: np.full((N, K), np.nan, np.float32) for f in FEATS}
    for i, s in enumerate(SIDS):
        A = ARR.get(s)
        if A is None:
            continue
        for k in np.flatnonzero(META["fs_qk"][i] >= 0):
            j = int(META["fs_qk"][i, k]) - QK0
            for base, nm in (("gm", "毛利率"), ("om", "營業利益率")):
                v0, v4, v1, v5 = at(A[base], j), at(A[base], j - 4), at(A[base], j - 1), at(A[base], j - 5)
                NP[nm][i, k] = v0; NP[f"{nm}年變化"][i, k] = v0 - v4
                if np.isfinite(v0 - v4) and np.isfinite(v1 - v5):
                    NP[f"{nm}由降轉升"][i, k] = float(v0 - v4 > 0 and v1 - v5 <= 0)
            NP["存貨天數"][i, k] = at(A["ivd"], j)
    log(f"[面板] 新 7 欄完成｜{time.time() - t0:.0f}s")
    # 覆蓋率（逐年）
    alive = np.isfinite(P["市值(億)"])
    COV = []
    from backtest import researchIndMom_freq as IMF          # 只為重建合併日曆（月底年份）
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"])
    MEy = np.array([CAL[int(p)].year for p in MEp])
    for y in sorted(set(MEy)):
        ks = np.flatnonzero(MEy == y); al = alive[:, ks]
        r = {"年": int(y), "有成交格": int(al.sum())}
        for f in FEATS:
            r[f"{f}_舊有值率"] = float(np.isfinite(P[f][:, ks])[al].mean()) if al.any() else np.nan
            r[f"{f}_新有值率"] = float(np.isfinite(NP[f][:, ks])[al].mean()) if al.any() else np.nan
        COV.append(r)
    COV = pd.DataFrame(COV)
    # 單位
    YI = pd.read_csv(os.path.join(src, "乙_全表.csv.gz"), dtype={"代號": str})
    BI = pd.read_csv(os.path.join(src, "對照B_乙.csv"), dtype={"代號": str})
    JA = pd.read_csv(os.path.join(src, "甲_全表.csv")); JB = pd.read_csv(os.path.join(src, "對照B_甲.csv")); JC = pd.read_csv(os.path.join(src, "對照C.csv"))

    def stock_cols(df):
        o = {}
        for f in FEATS:
            for pt in PTS:
                ks = df[f"_k{pt}"].to_numpy(int); ii = df["_i"].to_numpy(int); ok = (ks >= 0) & (ks < K)
                v = np.full(len(df), np.nan); v[ok] = NP[f][ii[ok], ks[ok]]
                o[f"{f}@{pt}(xbrl)"] = v
        return pd.DataFrame(o, index=df.index)
    INDS = sorted({x for x in np.unique(INDM) if x})
    IPn = {f: {ind: np.full(K, np.nan) for ind in INDS} for f in FEATS}
    for k in range(K):
        byind = defaultdict(list)
        for i in np.flatnonzero(INDM[:, k] != ""):
            byind[INDM[i, k]].append(i)
        for ind, mem in byind.items():
            for f in FEATS:
                v = NP[f][mem, k]; v = v[np.isfinite(v)]
                if len(v):
                    IPn[f][ind][k] = float(v.mean()) if f in FLAGS else float(np.median(v))

    def ind_cols(df):
        o = {}
        for f in FEATS:
            for pt in PTS:
                o[f"{f}@{pt}(xbrl)"] = [IPn[f][ind][int(k)] if (ind in IPn[f] and 0 <= int(k) < K) else np.nan for ind, k in zip(df["_ind"], df[f"_k{pt}"])]
        return pd.DataFrame(o, index=df.index)
    keep_y = ["代號", "名稱", "起點", "高點", "倍數", "產業(起點PIT)", "族群(切0.7)", "對照D", "_i"] + [f"_k{p}" for p in PTS]
    YN = pd.concat([YI[keep_y], YI[[f"{f}@{p}" for f in FEATS for p in PTS]].add_suffix("(舊)"), stock_cols(YI)], axis=1)
    keep_b = ["代號", "名稱", "起點", "高點(窗內最高)", "3年報酬", "0050同窗", "_i"] + [f"_k{p}" for p in PTS]
    BN = pd.concat([BI[keep_b], BI[[f"{f}@{p}" for f in FEATS for p in PTS]].add_suffix("(舊)"), stock_cols(BI)], axis=1)
    keep_j = ["版", "產業", "起點", "_ind"] + [f"_k{p}" for p in PTS]
    JAN = pd.concat([JA[keep_j + ["段號", "高點", "漲幅"]], JA[[f"{f}@{p}" for f in FEATS for p in PTS]].add_suffix("(舊)"), ind_cols(JA)], axis=1)
    JBN = pd.concat([JB[keep_j + ["高點(窗內最高)"]], JB[[f"{f}@{p}" for f in FEATS for p in PTS]].add_suffix("(舊)"), ind_cols(JB)], axis=1)
    JCN = pd.concat([JC[keep_j + ["高點"]], JC[[f"{f}@{p}" for f in FEATS for p in PTS]].add_suffix("(舊)"), ind_cols(JC)], axis=1)
    log(f"[單位] 乙 {len(YN)}、B乙 {len(BN)}、甲 {len(JAN)}、B甲 {len(JBN)}、C {len(JCN)}｜{time.time() - t0:.0f}s")

    # 並排（只受影響欄）
    XC = {}

    def cross(f, k):
        if (f, k) not in XC:
            v = NP[f][:, k].astype(float); XC[(f, k)] = np.sort(v[np.isfinite(v)])
        return XC[(f, k)]

    def prc(x, arr):
        if not np.isfinite(x) or not len(arr):
            return np.nan
        lo = np.searchsorted(arr, x, "left"); hi = np.searchsorted(arr, x, "right")
        return float((lo + 0.5 * (hi - lo)) / len(arr))
    yr = lambda df: pd.to_datetime(df["起點"]).dt.year
    SIDE = []
    for er, (y0, y1) in {"全期": (2004, 2100), "2005～2014": (2004, 2014), "2015～": (2015, 2100)}.items():
        g1 = YN[(yr(YN) >= y0) & (yr(YN) <= y1)]; gb = BN[(yr(BN) >= y0) & (yr(BN) <= y1)]
        groups = {"乙": g1, "B": gb, "D崩": g1[g1["對照D"] == "崩"], "乙非D": g1[g1["對照D"] == "未崩"]}
        for f in FEATS:
            for pt in PTS:
                col = f"{f}@{pt}(xbrl)"; row = {"起點期": er, "欄": f, "時點": pt}
                for gn, df in groups.items():
                    st = qstat(f, df[col]); row.update({f"{gn}_n": st["n"], f"{gn}_中位": st["中位"], f"{gn}_p25": st["p25"], f"{gn}_p75": st["p75"]})
                med = []; pr = []
                for k, x in zip(g1[f"_k{pt}"].to_numpy(int), g1[col].to_numpy(float)):
                    if 0 <= k < K:
                        arr = cross(f, int(k))
                        if len(arr):
                            med.append(float(arr.mean()) if f in FLAGS else float(np.median(arr)))
                            if f not in FLAGS:
                                pr.append(prc(x, arr))
                row["A_同月他股中位"] = float(np.median(med)) if med else np.nan
                row["乙在同月百分位中位"] = float(np.nanmedian(pr)) if pr and np.isfinite(pr).any() else np.nan
                SIDE.append(row)
    SIDE = pd.DataFrame(SIDE)
    SIDEJ = []
    for vn in ("原版市值", "原版等權", "補充市值", "補充等權"):
        GA, GB, GC = JAN[JAN["版"] == vn], JBN[JBN["版"] == vn], JCN[JCN["版"] == vn]
        for f in FEATS:
            for pt in PTS:
                col = f"{f}@{pt}(xbrl)"; row = {"版": vn, "欄": f, "時點": pt}
                for gn, df in (("甲", GA), ("B", GB), ("C", GC)):
                    st = qstat(f, df[col]); row.update({f"{gn}_n": st["n"], f"{gn}_中位": st["中位"], f"{gn}_p25": st["p25"], f"{gn}_p75": st["p75"]})
                med = []; pr = []
                for ind, k, x in zip(GA["_ind"], GA[f"_k{pt}"].to_numpy(int), GA[col].to_numpy(float)):
                    if 0 <= k < K:
                        arr = np.sort(np.array([IPn[f][o][k] for o in INDS if o != ind], float)); arr = arr[np.isfinite(arr)]
                        if len(arr):
                            med.append(float(arr.mean()) if f in FLAGS else float(np.median(arr)))
                            if f not in FLAGS:
                                pr.append(prc(x, arr))
                row["A_同月他產業中位"] = float(np.median(med)) if med else np.nan
                row["甲在同月百分位中位"] = float(np.nanmedian(pr)) if pr and np.isfinite(pr).any() else np.nan
                SIDEJ.append(row)
    SIDEJ = pd.DataFrame(SIDEJ)

    # 新舊對照
    def comp(df, label, by=None):
        rows = []
        parts = [("全部", df)] if by is None else [(v, df[df[by] == v]) for v in df[by].unique()]
        for pn, d in parts:
            for f in FEATS:
                tol = 1.0 if f == "存貨天數" else 0.005
                for pt in PTS:
                    o = d[f"{f}@{pt}(舊)"].to_numpy(float); n = d[f"{f}@{pt}(xbrl)"].to_numpy(float)
                    both = np.isfinite(o) & np.isfinite(n); dif = n[both] - o[both]
                    r = {"單位": label, "分組": pn, "欄": f, "時點": pt, "列數": len(d), "舊有值": int(np.isfinite(o).sum()), "新有值": int(np.isfinite(n).sum()),
                         "兩版都有": int(both.sum()), "只舊有": int((np.isfinite(o) & ~np.isfinite(n)).sum()), "只新有": int((~np.isfinite(o) & np.isfinite(n)).sum()),
                         "舊中位(全部有值)": qstat(f, o)["中位"], "新中位(全部有值)": qstat(f, n)["中位"]}
                    if f in FLAGS:
                        r["兩版都有_旗標一致比例"] = float((o[both] == n[both]).mean()) if both.any() else np.nan
                    else:
                        r["差(新−舊)中位"] = float(np.median(dif)) if len(dif) else np.nan
                        r["|差|中位"] = float(np.median(np.abs(dif))) if len(dif) else np.nan
                        r[f"|差|≤{'1天' if f == '存貨天數' else '0.5百分點'}比例"] = float((np.abs(dif) <= tol).mean()) if len(dif) else np.nan
                    rows.append(r)
        return rows
    CY = pd.DataFrame(comp(YN, "乙") + comp(BN, "對照B乙"))
    CJ = pd.DataFrame(comp(JAN, "甲", "版") + comp(JBN, "對照B甲", "版") + comp(JCN, "對照C", "版"))
    # 存檔
    def w(df, name):
        df.to_csv(os.path.join(out, name), index=False, encoding="utf-8-sig")
    w(CY, "新舊對照_乙.csv"); w(CJ, "新舊對照_甲.csv"); w(COV, "覆蓋率_年.csv"); w(SIDE, "並排_乙_xbrl.csv"); w(SIDEJ, "並排_甲_xbrl.csv")
    with gzip.open(os.path.join(out, "乙_xbrl欄.csv.gz"), "wt", encoding="utf-8") as fh:
        YN.to_csv(fh, index=False)
    w(BN, "對照B_乙_xbrl欄.csv"); w(JAN, "甲_xbrl欄.csv"); w(JBN, "對照B_甲_xbrl欄.csv"); w(JCN, "對照C_xbrl欄.csv")
    pickle.dump({"NP": NP}, open(os.path.join(WORK, f"bgr3b_np_{'dry' if a.dry else 'full'}.pkl"), "wb"), protocol=5)
    J = {"性質": "描述（⛔ 不判、不計 N、不檢定）；毛利、營業利益相關 7 欄改用 fs_xbrl 新三欄重產，舊版並列", "fs_xbrl快照": SHA,
         "時點選季": "沿用 researchBigRun3 面板（filing_dates 快照 dbfb96cb81a7）", "乾跑": a.dry, "欄": FEATS,
         "必附": ["描述，不是選股規則", "族群是事後分群，只當描述，⛔ 不當回測母體", "2015～2020 下市公司月營收約 80 家補不回", "上櫃 2007-07 前無價",
                "月營收為最新版、更正期間有輕微前視（快照 dbfb96cb81a7）", "景氣燈號為修正後資料、非當時公布值",
                "資料庫 C 版毛利、營業利益 2013 起（含下市；金融業空白屬正常）；2013 以前照實無", "外資持股 2024-08 後待資料庫（本件不動）"],
         "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "bigrun3b.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

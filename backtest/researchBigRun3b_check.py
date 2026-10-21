# -*- coding: utf-8 -*-
"""researchBigRun3b 對帳（fs_xbrl 新三欄重產的 7 欄）——回測線計算子代理。⛔ 不檢定。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun3b_check [--dry]
輸出 <xbrl 夾>/check.json、check.log

 K1 抽 200 個（股, 月底）格：直接讀新快照 fs_xbrl 原檔（另寫解析：cr 優先、年初累計差分）重算 7 欄，與新面板比。
 K2 不前視：新值所在格的財報上傳日（原面板 META）＜ 月底日；另抽 3,000 格用新快照 filing_dates 重找「已上傳最新季」，報與原面板選季不同的格數（只報、不改）。
 K3 「(舊)」欄與 resultsBigRun3 原表逐格相同；乙、B乙、甲、B甲、C 的新欄由面板與 INDM 另算（個股直接查格、產業另算成員中位）抽 300 格比。
 K4 並排表與新舊對照表由明細重算（n、中位、兩版都有、只舊有、只新有）。
 K5 策略鎖 --check；git status。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
SHA = "bc6cfec3813cb276517d74d6910f78a66b4fee99"
WORK = os.path.expanduser("~/bgrwork")
DC = os.path.join(WORK, f"mainC_{SHA[:12]}", "data")
FEATS = ["毛利率", "毛利率年變化", "毛利率由降轉升", "營業利益率", "營業利益率年變化", "營業利益率由降轉升", "存貨天數"]
FLAGS = {"毛利率由降轉升", "營業利益率由降轉升"}
PTS = ("前12月", "起點", "高點前6月", "高點", "高點後6月")
LOG = []; RES = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def close(a, b, tol=1e-6):
    fa = a is not None and np.isfinite(a); fb = b is not None and np.isfinite(b)
    if not fa and not fb:
        return True
    return fa and fb and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    tag = "dry" if a.dry else "full"
    SRC = os.path.join(WORK, "dry3") if a.dry else "backtest/resultsBigRun3"
    OD = os.path.join(WORK, "dry3b") if a.dry else "backtest/resultsBigRun3/xbrl"
    rng = np.random.default_rng(20261024)
    PN = pickle.load(open(os.path.join(WORK, f"bgr3_panel_{tag}.pkl"), "rb")); NP = pickle.load(open(os.path.join(WORK, f"bgr3b_np_{tag}.pkl"), "rb"))["NP"]
    SIDS = PN["SIDS"]; MEp = PN["MEp"]; META = PN["META"]; INDM = PN["INDM"]; K = len(MEp)
    from backtest import researchIndMom_freq as IMF
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log); CAL = Ze["cal"].append(Zm["cal"])
    # ── K1 原檔重算
    raw = {}
    for f in sorted(glob.glob(os.path.join(DC, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype=str)
        for r in x.itertuples(index=False):
            key = (r.stock_id, r.period)
            if key in raw and raw[key]["report"] == "cr":
                continue
            if key in raw and r.report != "cr":
                continue
            raw[key] = {"report": r.report, **{c: pd.to_numeric(getattr(r, c), errors="coerce") for c in
                                                ("revenue_ytd", "gross_profit_ytd", "operating_income_ytd", "cost_of_sales_ytd", "inventories")}}

    def per(qk):
        return f"{qk // 4}Q{qk % 4 + 1}"

    def sq(s, qk, c):
        v = raw.get((s, per(qk)), {}).get(c, np.nan)
        if qk % 4 == 0 or not np.isfinite(v):
            return v
        pv = raw.get((s, per(qk - 1)), {}).get(c, np.nan)
        return v - pv if np.isfinite(pv) else np.nan

    def ratio(s, qk, c):
        r_ = sq(s, qk, "revenue_ytd"); g = sq(s, qk, c)
        return g / r_ if np.isfinite(r_) and r_ > 0 and np.isfinite(g) else np.nan
    cells = np.argwhere(META["fs_qk"] >= 0)
    pick = cells[rng.choice(len(cells), min(200, len(cells)), replace=False)]
    k1 = {f: [0, 0] for f in FEATS}; bad = []
    for i, k in pick:
        s = SIDS[i]; qk = int(META["fs_qk"][i, k]); mine = {}
        for c, nm in (("gross_profit_ytd", "毛利率"), ("operating_income_ytd", "營業利益率")):
            v0, v4, v1, v5 = ratio(s, qk, c), ratio(s, qk - 4, c), ratio(s, qk - 1, c), ratio(s, qk - 5, c)
            mine[nm] = v0; mine[f"{nm}年變化"] = v0 - v4
            mine[f"{nm}由降轉升"] = float(v0 - v4 > 0 and v1 - v5 <= 0) if np.isfinite(v0 - v4) and np.isfinite(v1 - v5) else np.nan
        cs = sq(s, qk, "cost_of_sales_ytd"); inv = raw.get((s, per(qk)), {}).get("inventories", np.nan)
        mine["存貨天數"] = inv / cs * 91.25 if np.isfinite(cs) and cs > 0 and np.isfinite(inv) else np.nan
        for f in FEATS:
            ok = close(mine[f], float(NP[f][i, k]), 1e-5)
            k1[f][0] += 1; k1[f][1] += int(ok)
            if not ok and len(bad) < 8:
                bad.append((s, per(qk), f, mine[f], float(NP[f][i, k])))
    RES["K1"] = {f: {"抽": v[0], "相符": v[1]} for f, v in k1.items()}; RES["K1_不符例"] = bad
    log("K1 原檔重算：" + "、".join(f"{f} {v[1]}/{v[0]}" for f, v in k1.items()))
    # ── K2
    med = np.array([np.datetime64(CAL[int(p)], "D").astype(np.int64) for p in MEp])
    hasv = np.zeros_like(META["fs_av"], bool)
    for f in FEATS:
        hasv |= np.isfinite(NP[f])
    ii, kk = np.nonzero(hasv)
    nbad = int((META["fs_av"][ii, kk] >= med[kk]).sum()) + int((META["fs_av"][ii, kk] < 0).sum())
    fd = pd.read_csv(os.path.join(DC, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce").dt.normalize(); fd = fd.dropna(subset=["d"])
    up = fd.groupby(["stock_id", "year", "season"])["d"].min()
    ai1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "year", "season"])["d"].min(); up.loc[ai1.index] = ai1
    UPS = {}
    for (s, y, q), d in up.items():
        UPS.setdefault(s, []).append((d, int(y) * 4 + int(q) - 1))
    smp = cells[rng.choice(len(cells), min(3000, len(cells)), replace=False)]; diff = 0
    for i, k in smp:
        d = CAL[int(MEp[k])]; c = [qk for dd, qk in UPS.get(SIDS[i], []) if dd < d]
        diff += int((max(c) if c else -1) != META["fs_qk"][i, k])
    RES["K2"] = {"新值格": int(len(ii)), "上傳日≥月底或缺": nbad, "新快照選季不同(抽3000)": diff}
    log(f"K2 不前視：新值 {len(ii)} 格中上傳日 ≥ 月底或缺 {nbad}；新快照 filing_dates 選季不同 {diff}/{len(smp)}（只報）")
    # ── K3
    YI0 = pd.read_csv(os.path.join(SRC, "乙_全表.csv.gz"), dtype={"代號": str}); YN = pd.read_csv(os.path.join(OD, "乙_xbrl欄.csv.gz"), dtype={"代號": str})
    BI0 = pd.read_csv(os.path.join(SRC, "對照B_乙.csv"), dtype={"代號": str}); BN = pd.read_csv(os.path.join(OD, "對照B_乙_xbrl欄.csv"), dtype={"代號": str})
    JA0 = pd.read_csv(os.path.join(SRC, "甲_全表.csv")); JAN = pd.read_csv(os.path.join(OD, "甲_xbrl欄.csv"))
    JB0 = pd.read_csv(os.path.join(SRC, "對照B_甲.csv")); JBN = pd.read_csv(os.path.join(OD, "對照B_甲_xbrl欄.csv"))
    JC0 = pd.read_csv(os.path.join(SRC, "對照C.csv")); JCN = pd.read_csv(os.path.join(OD, "對照C_xbrl欄.csv"))
    same_old = 0; n_old = 0
    for d0, dn in ((YI0, YN), (BI0, BN), (JA0, JAN), (JB0, JBN), (JC0, JCN)):
        for f in FEATS:
            for p in PTS:
                a_ = d0[f"{f}@{p}"].to_numpy(float); b_ = dn[f"{f}@{p}(舊)"].to_numpy(float)
                n_old += 1; same_old += int(len(a_) == len(b_) and np.array_equal(np.isnan(a_), np.isnan(b_)) and np.allclose(a_[~np.isnan(a_)], b_[~np.isnan(b_)]))
    ok3 = 0; n3 = 0
    for df in (YN, BN):
        for _ in range(100):
            r = df.iloc[int(rng.integers(len(df)))]; f = FEATS[int(rng.integers(7))]; p = PTS[int(rng.integers(5))]; k = int(r[f"_k{p}"])
            mine = float(NP[f][int(r["_i"]), k]) if 0 <= k < K else np.nan
            n3 += 1; ok3 += int(close(mine, r[f"{f}@{p}(xbrl)"], 1e-6))
    for df in (JAN, JBN, JCN):
        for _ in range(35):
            r = df.iloc[int(rng.integers(len(df)))]; f = FEATS[int(rng.integers(7))]; p = PTS[int(rng.integers(5))]; k = int(r[f"_k{p}"])
            if 0 <= k < K:
                mem = [i for i in range(len(SIDS)) if INDM[i, k] == r["_ind"]]
                v = np.array([NP[f][i, k] for i in mem], float); v = v[np.isfinite(v)]
                mine = (v.mean() if f in FLAGS else np.median(v)) if len(v) else np.nan
            else:
                mine = np.nan
            n3 += 1; ok3 += int(close(mine, r[f"{f}@{p}(xbrl)"], 1e-6))
    RES["K3"] = {"舊欄與原表相同(欄×時點×檔)": f"{same_old}/{n_old}", "新欄抽格": n3, "相符": ok3}
    log(f"K3 舊欄與原表相同 {same_old}/{n_old}；新欄抽格重算 {ok3}/{n3}")
    # ── K4
    SI = pd.read_csv(os.path.join(OD, "並排_乙_xbrl.csv")); SJ = pd.read_csv(os.path.join(OD, "並排_甲_xbrl.csv"))
    ok4 = 0; n4 = 0
    yr = lambda df: pd.to_datetime(df["起點"]).dt.year
    for _, r in SI.iterrows():
        y0, y1 = {"全期": (2004, 2100), "2005～2014": (2004, 2014), "2015～": (2015, 2100)}[r["起點期"]]
        g1 = YN[(yr(YN) >= y0) & (yr(YN) <= y1)]; gb = BN[(yr(BN) >= y0) & (yr(BN) <= y1)]
        for gn, df in (("乙", g1), ("B", gb), ("D崩", g1[g1["對照D"] == "崩"]), ("乙非D", g1[g1["對照D"] == "未崩"])):
            v = df[f"{r['欄']}@{r['時點']}(xbrl)"].to_numpy(float); v = v[np.isfinite(v)]
            m = (v.mean() if r["欄"] in FLAGS else np.median(v)) if len(v) else np.nan
            n4 += 1; ok4 += int(len(v) == r[f"{gn}_n"] and close(m, r[f"{gn}_中位"], 1e-9))
    for _, r in SJ.iterrows():
        for gn, df in (("甲", JAN), ("B", JBN), ("C", JCN)):
            v = df[df["版"] == r["版"]][f"{r['欄']}@{r['時點']}(xbrl)"].to_numpy(float); v = v[np.isfinite(v)]
            m = (v.mean() if r["欄"] in FLAGS else np.median(v)) if len(v) else np.nan
            n4 += 1; ok4 += int(len(v) == r[f"{gn}_n"] and close(m, r[f"{gn}_中位"], 1e-9))
    CY = pd.read_csv(os.path.join(OD, "新舊對照_乙.csv"))
    for _, r in CY.iterrows():
        df = YN if r["單位"] == "乙" else BN
        o = df[f"{r['欄']}@{r['時點']}(舊)"].to_numpy(float); n = df[f"{r['欄']}@{r['時點']}(xbrl)"].to_numpy(float)
        n4 += 1; ok4 += int(np.isfinite(o).sum() == r["舊有值"] and np.isfinite(n).sum() == r["新有值"] and (np.isfinite(o) & np.isfinite(n)).sum() == r["兩版都有"])
    RES["K4"] = {"格": n4, "相符": ok4}
    log(f"K4 並排與新舊對照重算 {ok4}/{n4}")
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    RES["K5"] = {"策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:], "已追蹤檔改動": [x for x in st if not x.startswith("??")],
                 "本件新增": [x for x in st if "BigRun3b" in x or "xbrl" in x]}
    log(f"K5 策略鎖 {RES['K5']['策略鎖']}；已追蹤檔改動 {len(RES['K5']['已追蹤檔改動'])}；新增 {RES['K5']['本件新增']}")
    json.dump(RES, open(os.path.join(OD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OD, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

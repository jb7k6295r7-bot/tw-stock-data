# -*- coding: utf-8 -*-
"""對照 D（漲了又崩）拆產業、拆族群、產業相對版、虧損比例（台股 seq541，使用者追問；描述、不判、不計 N）——回測線計算子代理。
⛔ 描述，不是出場規則；不檢定、不給門檻；不 commit、不改既有檔；私有資料 ⛔ 不讀。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun5 [--dry]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun5_check [--dry]
輸出 backtest/resultsBigRun5/：產業.csv、族群.csv、產業相對.csv、虧損.csv、本益比有值率.csv、逐段.csv.gz、bigrun5.json、run.log

═══ 讀法（G 標；★＝執行者定；其餘 ＝ researchBigRun3 D1～D9、researchBigRun4 F1）═══
 G1 單位 ＝ resultsBigRun3/乙_全表 的乙 ×3；兩組 ＝「D崩」（高點後 12 個月內最低收盤 ≤ 高點 × 0.5）與「乙非D」（＝ 對照 D 標「未崩」者；未定、下市、遇壞根截 不進兩組，段數照報）。
    時點 ＝ 高點前6月、高點（D2：月底面板；高點 ＝ 高點當天或之前最後月底）。
 G2 欄：本益比（官方 per，虧損 ⇒ 空白）、本益比 5 年位置、ROE（近 4 季淨利 ÷ 權益）、營業利益率（fs_xbrl 新版，researchBigRun4 A）、合約負債年增（2018 起）、
    千張大戶比 12 月變化（集保 2017 起，百分點）——都是 researchBigRun3／4 月底面板原值。
 G3 ① 依起點產業（industry_pit，乙表「產業(起點PIT)」）：★ 該產業乙 ×3 全部段數 ＜ 20 ⇒ 併「其他(段數<20併)」；報 段數、崩、未崩、未定等、崩比例（＝ 崩 ÷（崩＋未崩））、
      各欄兩組中位與有值數。另報 全部、2005～2014 起點、2015 起起點 三列。
    ④ 依族群（resultsBigRun2 族群 切 0.7）段數前 15 大（群號 1～15，群號依段數排）同 ①。
 G4 ② 產業相對版 ★：基準 ＝ 同一月底、同一 PIT 產業（月底面板 INDM，該月在市、市值 ＞ 0、排除類別）全部個股的中位（含該股自己）；
      本益比 ÷ 產業中位（兩者皆有值且中位 ＞ 0）、ROE − 產業中位、營業利益率 − 產業中位；報兩組 n、中位、四分位（全部與兩個起點期）。
 G5 ③ 虧損 ＝ 近 4 季 EPS 合計 ＜ 0（fin_hist eps_ytd 差分成單季；★ 選季沿用月底面板「已上傳最新季」；fin_hist 取最新 origin/main（SHA 常數））；
      報兩組 有值數、虧損比例；另報 本益比有值率（＝ 本益比有值段 ÷ 該組段數）與「本益比空白者中虧損的比例」。
 G6 必附：描述，不是出場規則｜事後圈的段｜虧損股本益比空白｜任何門檻要用另起草登錄（seq421）｜族群是事後分群只當描述｜2015～2020 下市月營收約 80 家補不回。
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

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLongPool as LP                 # noqa: E402  qkey、single

SHA = "eeb5af5f8feca83d0702fa0423a0c58cdb77900d"
WORK = os.path.expanduser("~/bgrwork")
OUT = "backtest/resultsBigRun5"
PTS = ("高點前6月", "高點")
FE = ["本益比", "本益比5年位置", "ROE", "營業利益率", "合約負債年增", "集保千張大戶比12月變化"]
MINSEG = 20
NOTES = ["描述，不是出場規則", "事後圈的段", "虧損股本益比空白", "任何門檻要用另起草登錄（seq421）", "族群是事後分群，只當描述、⛔ 不當母體",
         "2015～2020 下市月營收約 80 家補不回"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def ensure_arch():
    root = os.path.join(WORK, f"mainE_{SHA[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        subprocess.run(["git", "cat-file", "-e", SHA], check=True)
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", SHA, "data/mops/fin_hist"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(SHA)
    return os.path.join(root, "data")


def st(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0, "中位": np.nan, "p25": np.nan, "p75": np.nan}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p25": float(np.percentile(v, 25)), "p75": float(np.percentile(v, 75))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    t0 = time.time(); tag = "dry" if a.dry else "full"
    src3 = os.path.join(WORK, "dry3") if a.dry else "backtest/resultsBigRun3"
    out = os.path.join(WORK, "dry5") if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    DN = ensure_arch()
    PN = pickle.load(open(os.path.join(WORK, f"bgr3_panel_{tag}.pkl"), "rb")); B4 = pickle.load(open(os.path.join(WORK, f"bgr4_{tag}.pkl"), "rb"))
    SIDS = PN["SIDS"]; P = PN["P"]; META = PN["META"]; INDM = PN["INDM"]; K = len(PN["MEp"]); N = len(SIDS)
    log(f"[資料] 月底面板 bgr3_panel_{tag}、營業利益率 bgr4_{tag}（fs_xbrl c1db66ce9730）、fin_hist origin/main {SHA[:12]}")
    ARR = {f: (B4["OPM"]["營業利益率"] if f == "營業利益率" else P[f]).astype(float) for f in FE}
    # 近 4 季 EPS
    L = []
    for f in sorted(glob.glob(os.path.join(DN, "mops", "fin_hist", "*.csv"))):
        per = os.path.basename(f)[:6]; qk = LP.qkey(per[:4], per[5])
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd"]); x["qk"] = qk; L.append(x)
    FN = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last"); FN["eps_ytd"] = pd.to_numeric(FN["eps_ytd"], errors="coerce")
    EPSY = {s: g.set_index("qk")["eps_ytd"] for s, g in FN.groupby("stock_id")}

    def eps4(i, k):
        if not (0 <= k < K):
            return np.nan
        qk = int(META["fs_qk"][i, k]); y = EPSY.get(SIDS[i])
        if qk < 0 or y is None:
            return np.nan
        q = [LP.single(y, j) for j in range(qk - 3, qk + 1)]
        return float(sum(q)) if np.isfinite(q).all() else np.nan
    # 產業中位（同月同產業）
    MED = {f: {} for f in ("本益比", "ROE", "營業利益率")}

    def imed(f, ind, k):
        key = (ind, k)
        if key not in MED[f]:
            mem = np.flatnonzero(INDM[:, k] == ind)
            v = ARR[f][mem, k]; v = v[np.isfinite(v)]
            MED[f][key] = float(np.median(v)) if len(v) else np.nan
        return MED[f][key]
    Y = pd.read_csv(os.path.join(src3, "乙_全表.csv.gz"), dtype={"代號": str})
    rows = []
    for _, r in Y.iterrows():
        i = int(r["_i"]); rec = {"代號": r["代號"], "名稱": r["名稱"], "起點": r["起點"], "高點": r["高點"], "產業(起點PIT)": r["產業(起點PIT)"],
                               "族群(切0.7)": int(r["族群(切0.7)"]), "對照D": r["對照D"], "組": {"崩": "D崩", "未崩": "乙非D"}.get(r["對照D"], "不進兩組")}
        for pt in PTS:
            k = int(r[f"_k{pt}"]); ok = 0 <= k < K
            for f in FE:
                rec[f"{f}@{pt}"] = ARR[f][i, k] if ok else np.nan
            ind_k = INDM[i, k] if ok else ""
            rec[f"月底產業@{pt}"] = ind_k
            for f in ("本益比", "ROE", "營業利益率"):
                m = imed(f, ind_k, k) if (ok and ind_k) else np.nan
                v = rec[f"{f}@{pt}"]
                rec[f"{f}產業中位@{pt}"] = m
                if f == "本益比":
                    rec[f"本益比÷產業中位@{pt}"] = v / m if (np.isfinite(v) and np.isfinite(m) and m > 0) else np.nan
                else:
                    rec[f"{f}−產業中位@{pt}"] = v - m if (np.isfinite(v) and np.isfinite(m)) else np.nan
            e = eps4(i, k); rec[f"近4季EPS@{pt}"] = e; rec[f"虧損@{pt}"] = float(e < 0) if np.isfinite(e) else np.nan
        rows.append(rec)
    S = pd.DataFrame(rows)
    yr = pd.to_datetime(S["起點"]).dt.year
    S["起點期"] = np.where(yr <= 2014, "2005～2014", "2015～")
    cnt_ind = S["產業(起點PIT)"].value_counts()
    S["產業(併)"] = [x if cnt_ind[x] >= MINSEG else f"其他(段數<{MINSEG}併)" for x in S["產業(起點PIT)"]]
    log(f"[逐段] {len(S)}｜D崩 {(S['組'] == 'D崩').sum()}、乙非D {(S['組'] == '乙非D').sum()}｜{time.time() - t0:.0f}s")

    def block(df, label):
        r = {"分組": label, "段數": len(df), "崩": int((df["組"] == "D崩").sum()), "未崩": int((df["組"] == "乙非D").sum()),
             "不進兩組(未定／下市／遇壞根截)": int((df["組"] == "不進兩組").sum())}
        r["崩比例(崩÷(崩+未崩))"] = r["崩"] / (r["崩"] + r["未崩"]) if (r["崩"] + r["未崩"]) else np.nan
        for pt in PTS:
            for f in FE:
                for g in ("D崩", "乙非D"):
                    s_ = st(df.loc[df["組"] == g, f"{f}@{pt}"])
                    r[f"{f}@{pt}_{g}_中位"] = s_["中位"]; r[f"{f}@{pt}_{g}_n"] = s_["n"]
        return r
    IND = [block(S, "全部"), block(S[S["起點期"] == "2005～2014"], "全部(2005～2014起點)"), block(S[S["起點期"] == "2015～"], "全部(2015起起點)")]
    for ind, g in sorted(S.groupby("產業(併)"), key=lambda z: -len(z[1])):
        IND.append(block(g, ind))
    IND = pd.DataFrame(IND)
    GR = pd.read_csv("backtest/resultsBigRun2/族群_群.csv")
    GRP = []
    for gno in range(1, 16):
        g = S[S["族群(切0.7)"] == gno]
        if not len(g):
            continue
        gi = GR[GR["群號"] == gno].iloc[0]
        r = block(g, f"群{gno}"); r.update({"代表股": gi["代表股"], "期間": gi["期間"], "官方產業分布": gi["官方產業分布"]})
        GRP.append(r)
    GRP = pd.DataFrame(GRP)
    REL = []
    for per_, d in (("全期", S), ("2005～2014", S[S["起點期"] == "2005～2014"]), ("2015～", S[S["起點期"] == "2015～"])):
        for pt in PTS:
            for col in (f"本益比÷產業中位@{pt}", f"ROE−產業中位@{pt}", f"營業利益率−產業中位@{pt}"):
                r = {"起點期": per_, "時點": pt, "欄": col.split("@")[0]}
                for g in ("D崩", "乙非D"):
                    s_ = st(d.loc[d["組"] == g, col]); r.update({f"{g}_{k}": v for k, v in s_.items()})
                REL.append(r)
    REL = pd.DataFrame(REL)
    LOSS = []; PEV = []
    for per_, d in (("全期", S), ("2005～2014", S[S["起點期"] == "2005～2014"]), ("2015～", S[S["起點期"] == "2015～"])):
        for pt in PTS:
            for g in ("D崩", "乙非D"):
                dd = d[d["組"] == g]; lv = dd[f"虧損@{pt}"].to_numpy(float); pe = dd[f"本益比@{pt}"].to_numpy(float)
                blank = ~np.isfinite(pe); lb = lv[blank]
                LOSS.append({"起點期": per_, "時點": pt, "組": g, "段數": len(dd), "近4季EPS有值": int(np.isfinite(lv).sum()),
                             "虧損比例(EPS<0÷EPS有值)": float(np.nanmean(lv)) if np.isfinite(lv).any() else np.nan})
                PEV.append({"起點期": per_, "時點": pt, "組": g, "段數": len(dd), "本益比有值": int(np.isfinite(pe).sum()),
                            "本益比有值率": float(np.isfinite(pe).mean()) if len(dd) else np.nan,
                            "本益比空白且EPS有值": int(np.isfinite(lb).sum()), "本益比空白者中虧損比例": float(np.nanmean(lb)) if np.isfinite(lb).any() else np.nan})
    LOSS = pd.DataFrame(LOSS); PEV = pd.DataFrame(PEV)
    w = lambda df, nm: df.to_csv(os.path.join(out, nm), index=False, encoding="utf-8-sig")
    w(IND, "產業.csv"); w(GRP, "族群.csv"); w(REL, "產業相對.csv"); w(LOSS, "虧損.csv"); w(PEV, "本益比有值率.csv")
    with gzip.open(os.path.join(out, "逐段.csv.gz"), "wt", encoding="utf-8") as fh:
        S.to_csv(fh, index=False)
    J = {"性質": "描述（⛔ 不是出場規則、不判、不計 N）", "依據": "台股 seq541（使用者追問）", "fin_hist快照": SHA, "營業利益率": "researchBigRun4 A（fs_xbrl c1db66ce9730）",
         "併其他門檻": f"產業乙段數 < {MINSEG}", "乾跑": a.dry, "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "bigrun5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""高10 同分改排序 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 resultsPTH10tie/freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10tie_freq_check [--procs 4]

K1 不前視（members_<世界>.csv.gz 全列）：月營收可得日 ≤ 排序日；財報季（F6 fin_q、Q q_finq、F7 f7_fin_q）可用日（filing_dates 原檔另算：AI1 優先最早；
   無時戳 ⇒ 法定期限）＜ 排序日；集保資料日的下一個週一 ≤ 排序日；60／20 日有效報酬數 ≤ 60／20。
K2 另一條路重算：月營收年增（revenue_hist 原檔、可得日自算）抽 400 列；60 日波動、MAX（快取收盤自寫向量式）抽 400 列 ⇒ 與 members 檔（%.10g 存檔）相對差 ≤ 1e−9。
K3 同分群：由事件檔 trades_<世界>_跳月 自算每進場日 候選數、PTH＝1 檔數、同分組數(≥2)、同分群成員 ⇒ 與 resultsPTH10seed/ties_<世界>.csv、monthly_<世界>.csv、
   members 檔相同；monthly「原|買進格數／原|需抽」＝ ties 檔；freq.csv 原路徑欄由 ties 檔自算相同。
K4 分數 glue 對 mktdrop_cands：主 2 個、早年 1 個排序日的最大同分群，以【未覆寫 AI1】的財報跑本件 date_scores ⇒ F6、F7 與 mktdrop_cands.f8_rank、
   Q 與 mktdrop_cands.q_scores 逐檔相差 ≤ 1e−12；再以覆寫版重算 ⇒ 與 members 檔 F6、F7、Q 相同。
K5 輸出無報酬欄（欄名不含 年化／回落／淨值／比值／入帳，且無 R、px 欄）；策略鎖 25 支相符；git 工作樹：只新增 researchPTH10tie_freq*.py 與 resultsPTH10tie/。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTH10tie_freq as TF            # noqa: E402
from backtest import researchMktDrop_fund as FU             # noqa: E402
from backtest import researchMktDrop_quality as QL          # noqa: E402
from backtest import researchExit5 as EX5                   # noqa: E402
from backtest import mktdrop_cands as MC                    # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = TF.OUT
SEEDDIR = TF.SEEDDIR
SP = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/f4c14e25-a422-4a37-ab64-e11f2ead97b5/scratchpad"
FIX = {"主": ("2019-06-28", "2024-05-31"), "早年": ("2013-06-28",)}


def filing_avail():
    fd = pd.read_csv(os.path.join(FU.XD, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["key"] = fd["stock_id"] + "|" + fd["year"].astype(str) + "Q" + fd["season"].astype(str)
    a1 = fd[fd["doc_code"] == "AI1"].groupby("key")["d"].min(); al = fd.groupby("key")["d"].min()
    out = al.to_dict(); out.update(a1.to_dict())
    return out


def deadline(qs):
    y, q = int(qs[:4]), int(qs[-1])
    return pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, {1: 5, 2: 8, 3: 11}[q], {1: 15, 2: 14, 3: 14}[q])


def rev_raw(data):
    fs = sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
    df["r"] = pd.to_numeric(df["當月營收"], errors="coerce"); df["l"] = pd.to_numeric(df["去年當月營收"], errors="coerce")
    df = df[np.isfinite(df["r"])].reset_index(drop=True)
    y = df["period"].str[:4].astype(int); m = df["period"].str[5:].astype(int)
    y2 = np.where(m == 12, y + 1, y); m2 = np.where(m == 12, 1, m + 1)
    day = np.where(df["period"] <= "2025-12", 10, 15)
    df["avd"] = pd.to_datetime(pd.DataFrame({"year": y2, "month": m2, "day": day})).to_numpy()
    return df


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); a = ap.parse_args()
    log = RA.log_to(os.path.join(OUT, "check.log"))
    J = {"K1": {}, "K2": {}, "K3": {}, "K4": {}, "K5": {}}
    FA = filing_avail()
    for wn in ("主", "早年"):
        MB = pd.read_csv(os.path.join(OUT, f"members_{wn}.csv.gz"), dtype={"sid": str, "形成月底": str, "進場日": str, "rev_avail_date": str, "tdcc_date": str})
        t = pd.to_datetime(MB["形成月底"])
        # ── K1
        ra = pd.to_datetime(MB["rev_avail_date"].replace("", np.nan), errors="coerce")
        bad = {"月營收可得日>排序日": int((ra > t).sum())}
        for qc, sc in (("fin_q", "fin_src"), ("q_finq", "q_finsrc")):
            n = 0; nn = 0
            for s, q, src, tt in zip(MB["sid"], MB[qc], MB[sc], t):
                if not isinstance(q, str):
                    continue
                nn += 1
                av = FA.get(f"{s}|{q}") if src == "t57sb01" else deadline(q)
                if av is None or not (av < tt):
                    n += 1
            bad[f"{qc} 可用日≥排序日（{nn} 列有季）"] = n
        n = 0; nn = 0
        for s, q, tt in zip(MB["sid"], MB["f7_fin_q"], t):
            if isinstance(q, str) and q[:4].isdigit():
                nn += 1; av = FA.get(f"{s}|{q}")
                if av is None or not (av < tt):
                    n += 1
        bad[f"f7_fin_q 可用日≥排序日（{nn} 列有時戳季）"] = n
        td = pd.to_datetime(MB["tdcc_date"].replace("", np.nan), errors="coerce")
        tav = td + pd.to_timedelta(7 - td.dt.weekday, unit="D")
        bad["集保可用日>排序日"] = int((tav > t).sum())
        bad["vol60_n>60 或 max20_n>20"] = int(((MB["vol60_n"] > 60) | (MB["max20_n"] > 20)).sum())
        J["K1"][wn] = bad
        log(f"[K1 {wn}] {bad}")
        if any(bad.values()):
            raise SystemExit(f"⛔ K1 {wn} 前視 {bad}")
        # ── K2 營收
        W = M.build_world(wn, log)
        RV = rev_raw(W["data"])
        rs = MB.sample(min(400, len(MB)), random_state=1)
        dif = 0.0; nfin = 0
        for s, tt, v in zip(rs["sid"], pd.to_datetime(rs["形成月底"]), rs["rv_yoy"]):
            g = RV[(RV["stock_id"] == s) & (RV["avd"] < tt)]
            if len(g) == 0:
                w = np.nan
            else:
                g = g.sort_values("avd"); r = g.iloc[-1]
                w = r["r"] / r["l"] - 1 if (np.isfinite(r["l"]) and r["l"] > 0) else np.nan
            if np.isfinite(w) != np.isfinite(v):
                raise SystemExit(f"⛔ K2 營收 {s} {tt.date()} 可算性不同 {w} {v}")
            if np.isfinite(w):
                dif = max(dif, abs(w - v) / max(1.0, abs(w))); nfin += 1
        J["K2"][f"{wn}|營收年增 抽 {len(rs)} 列"] = f"可算 {nfin}、最大相對差（members 檔 %.10g 存檔） {dif:.2e}"
        if dif > 1e-9:
            raise SystemExit("⛔ K2 營收差")
        # ── K2 波動（向量式）
        C = W["C"]; TR = W["TRD"]
        d60 = 0.0; dmx = 0.0
        for s, f_, v6, vm in zip(rs["sid"], rs["形成月底"], rs["vol60"], rs["max20"]):
            i = W["ix"][s]; p = int(W["cal"].searchsorted(pd.Timestamp(f_)))
            bp = np.zeros(W["n0"], bool); bp[list(W["BADPOS"].get(s, set()))] = True
            dd = np.arange(p - 59, p + 1); dd = dd[dd >= 1]
            ok = TR[i, dd] & TR[i, dd - 1] & ~bp[dd] & ~bp[dd - 1] & np.isfinite(C[i, dd]) & np.isfinite(C[i, dd - 1]) & (C[i, dd - 1] > 0)
            r = C[i, dd[ok]] / C[i, dd[ok] - 1] - 1
            w6 = r.std(ddof=1) if len(r) >= 40 else np.nan
            ok2 = ok[-20:]; r2 = C[i, dd[-20:][ok2]] / C[i, dd[-20:][ok2] - 1] - 1
            wm = r2.max() if len(r2) >= 15 else np.nan
            for w, v, nm in ((w6, v6, "vol60"), (wm, vm, "max20")):
                if np.isfinite(w) != np.isfinite(v):
                    raise SystemExit(f"⛔ K2 {nm} {s} {f_} 可算性不同")
            if np.isfinite(w6):
                d60 = max(d60, abs(w6 - v6) / max(1.0, abs(w6)))
            if np.isfinite(wm):
                dmx = max(dmx, abs(wm - vm) / max(1.0, abs(wm)))
        J["K2"][f"{wn}|60日波動／MAX 抽 {len(rs)} 列"] = f"最大相對差（%.10g 存檔） {d60:.2e}／{dmx:.2e}"
        if max(d60, dmx) > 1e-9:
            raise SystemExit("⛔ K2 波動差")
        # ── K3
        fr = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_跳月.csv.gz"), dtype=str, keep_default_na=False)
        fr["p"] = fr["PTH"].astype(float)
        TI = pd.read_csv(os.path.join(SEEDDIR, f"ties_{wn}.csv"), encoding="utf-8-sig")
        MO = pd.read_csv(os.path.join(OUT, f"monthly_{wn}.csv"), encoding="utf-8-sig")
        nb = 0
        for e, g in fr.groupby("進場日"):
            vc = g["p"].value_counts()
            ti = TI[TI["進場日"] == e].iloc[0]; mo = MO[MO["進場日"] == e].iloc[0]
            mem = int(vc[vc >= 2].sum())
            ok = (len(g) == ti["候選"] == mo["候選"] and int((g["p"] == 1.0).sum()) == ti["PTH=1組"] == mo["PTH=1組"]
                  and int((vc >= 2).sum()) == ti["同分組數(≥2)"] == mo["同分組數(≥2)"] and mem == mo["同分群成員"] == int((MB["進場日"] == e).sum())
                  and int(mo["原|買進格數"]) == int(ti["買進格數"]) and bool(mo["原|需抽"]) == bool(ti["需抽"]))
            if not ok:
                raise SystemExit(f"⛔ K3 {wn} {e} 不符")
            nb += 1
        J["K3"][f"{wn}|事件檔自算 vs ties／monthly／members（候選、PTH=1、同分組數、成員、原路徑買進格數、需抽）"] = f"{nb}/{len(TI)} 批相同"
        FQ = pd.read_csv(os.path.join(OUT, "freq.csv"), encoding="utf-8-sig")
        for sg in TF.SEGS[wn]:
            if sg == "主全窗":
                T = TI[TI["候選"] > 0]
            else:
                x, y = W["segp"][sg]; lo, hi = W["dates"][x], W["dates"][y]
                T = TI[(TI["進場日"] >= lo) & (TI["進場日"] <= hi) & (TI["候選"] > 0)]
            Tb = T[T["買進格數"] > 0]
            f = FQ[(FQ["世界"] == wn) & (FQ["段"] == sg)].iloc[0]
            mine = [len(T), float(T["PTH=1組"].mean()), float(Tb["需抽"].mean()), float(T["買進格數"].mean())]
            theirs = [f["批次(月)"], f["PTH=1組大小平均"], f["需抽月比例(有買進月)"], f["每月補格數平均(全部月)"]]
            if any(abs(float("%.6g" % u) - float(v)) > 1e-12 for u, v in zip(mine, theirs)):
                raise SystemExit(f"⛔ K3 freq {wn}/{sg} {mine} {theirs}")
        J["K3"][f"{wn}|freq.csv 原路徑欄（批次、PTH=1 平均、需抽比例、補格平均）由 ties 自算"] = "相同（%.6g）"
        # ── K4
        FINp, _ = FU.load_fin(); QFINp, _ = QL.load_fin()
        FIN0, _ = FU.load_fin(); QFIN0, _ = QL.load_fin()
        am, _ = TF.ai1_table(FU.XD); TF.ai1_patch(FINp, am); TF.ai1_patch(QFINp, am)
        TD, _ = FU.load_tdcc(); DV, mkd, smk = QL.load_div()
        rev, rly, _ = EX5.load_revenue(W["data"]); AV = EX5.avail_pos(list(rev.index), W["cal"]); AVA = np.array([AV[p] for p in rev.index], np.int64)
        for want in FIX[wn]:
            fs = sorted(MB["形成月底"].unique()); f_ = min(fs, key=lambda z: abs(pd.Timestamp(z) - pd.Timestamp(want)))
            g = MB[MB["形成月底"] == f_]; gid = g["grp"].value_counts().idxmax(); g = g[g["grp"] == gid]
            sids = g["sid"].tolist(); t_ = pd.Timestamp(f_); ds = str(t_.date())
            FU._G["cal"] = {W["data"]: W["cal"]}
            us = FU.universe_sids(W["data"], ds, ds)
            sa = sorted(set(us) | set(sids))
            BR = FU.run_jobs([(W["data"], s, W["mk"].get(s, us.get(s, "twse")), [ds]) for s in sa], a.procs, f"check {wn} {ds}")
            X = {"W": W, "BR": BR, "rev": rev, "rly": rly, "AV": AV, "AVA": AVA, "TD": TD, "DV": DV, "mkd": mkd, "smk": smk}
            d0 = TF.date_scores(X, t_, sids, {s: 0 for s in sids}, FIN0, QFIN0).set_index("sid")
            cp = [(s, "", -float(d0.loc[s, "tc_drop"]), float(d0.loc[s, "rv_yoy"])) for s in sids]
            o8, info, dref = MC.f8_rank(t_, W["data"], FU.XD, W["cal"], cp, procs=a.procs, log=log)
            dref = dref.set_index("sid")
            QW, _ = MC.q_scores(t_, FU.FDATA, FU.XD, sids, log)
            QW = QW.set_index("sid")
            e6 = float(np.nanmax(np.abs(d0.loc[sids, "F6"].to_numpy(float) - dref.loc[sids, "F6"].to_numpy(float))))
            e7 = float(np.nanmax(np.abs(d0.loc[sids, "F7"].to_numpy(float) - dref.loc[sids, "F7"].to_numpy(float))))
            eq = float(np.nanmax(np.abs(d0.loc[sids, "Q"].to_numpy(float) - QW.loc[sids, "Q"].to_numpy(float))))
            dp = TF.date_scores(X, t_, sids, {s: int(gid) for s in sids}, FINp, QFINp).set_index("sid")
            gg = g.set_index("sid")
            m6 = float(np.nanmax(np.abs(dp.loc[sids, "F6"].to_numpy(float) - gg.loc[sids, "F6"].to_numpy(float))))
            m7 = float(np.nanmax(np.abs(dp.loc[sids, "F7"].to_numpy(float) - gg.loc[sids, "F7"].to_numpy(float))))
            mq = float(np.nanmax(np.abs(dp.loc[sids, "Q"].to_numpy(float) - gg.loc[sids, "Q"].to_numpy(float))))
            J["K4"][f"{wn}|{ds} 同分群 {len(sids)} 檔"] = {"未覆寫 vs f8_rank F6／F7 最大差": [e6, e7], "未覆寫 vs q_scores Q 最大差": eq,
                                                       "覆寫版重算 vs members F6／F7／Q（%.10g 存檔）": [m6, m7, mq], "f8_rank info": info}
            log(f"[K4 {wn} {ds}] {J['K4'][f'{wn}|{ds} 同分群 {len(sids)} 檔']}")
            if max(e6, e7, eq) > 1e-12 or max(m6, m7, mq) > 1e-8:
                raise SystemExit("⛔ K4 不符")
        del W
    # ── K5
    badc = []
    for f in glob.glob(os.path.join(OUT, "*.csv")) + glob.glob(os.path.join(OUT, "*.csv.gz")):
        cols = pd.read_csv(f, nrows=0).columns
        for c in cols:
            if any(k in c for k in ("年化", "回落", "淨值", "比值", "入帳")) or c in ("R", "px", "R淨", "eq"):
                badc.append((os.path.basename(f), c))
    J["K5"]["輸出含報酬欄"] = badc
    if badc:
        raise SystemExit(f"⛔ K5 報酬欄 {badc}")
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    J["K5"]["strategy_lock"] = (p.stdout.strip().splitlines() or [p.stderr.strip()[-200:]])[-1]; J["K5"]["rc"] = p.returncode
    now = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    base = open(os.path.join(SP, "p10t_git_before.txt"), encoding="utf-8").read().splitlines()
    J["K5"]["git 新增"] = sorted(set(now) - set(base)); J["K5"]["git 消失"] = sorted(set(base) - set(now))
    dm = subprocess.run("git diff | md5sum", shell=True, capture_output=True, text=True).stdout.strip()
    J["K5"]["git diff md5 與開工前相同"] = dm == open(os.path.join(SP, "p10t_gitdiff_before.txt")).read().splitlines()[-1].strip()
    log(f"[K5] {J['K5']}")
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[完] check 全過")


if __name__ == "__main__":
    main()

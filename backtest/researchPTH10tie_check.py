# -*- coding: utf-8 -*-
"""高10 同分三排序 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀、只寫 resultsPTH10tie/main/check.json、check.log；⛔ 不改任何既有檔。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10tie_check

K0 登錄 sha 另一條路（researchIndMom_freq_check.reg_ok：信箱根目錄＋_封存-* 全部同 sha 檔逐一重算）；策略鎖 25 支相符。
K1 另一條路重算統計：raw_<世界>.npz 權益 ⇒ benchmark_rejudge.estat（rerun17.win_metrics、end＝len）＋ 日期字串自切窗 ⇒ cells 年化／回落 相對差 ≤ 1e−9；
   百分位（≤、＜）自算 ＝ cells；判定（四個 ≥ 0.97）自算 ＝ result.json。
K2 200 組分布對排名表：排名窗（2022-01-03～2026-08-24）與探索段 200 組中位 ＝ resultsBenchRejudge/rank.csv「高10」列（%.10g）；
   大盤報酬指數、0050 同窗 ＝ rank.csv「大盤（報酬指數）」「0050」列。
K3 排序真的照鍵走（動態路徑）：各排序交易檔每個買進日 ⇒ 該批事件（keys 檔）扣「同代號持有中（買進 ＜ e ≤ 賣出）」後，
   依 lexsort(rk原, −鍵, 算不出, −PTH) 取前 k（k ＝ 當天實買數）＝ 實買集合；逐批全過。原排序交易檔 ＝ resultsPTHn trades_<世界>_N10 全文。
K4 排序鍵 ＝ 頻率表 members 檔（keys 檔各排序鍵 ＝ members 對應欄同號，算不出 ⇔ NaN）；不前視：月營收可得日 ≤ 形成月底、60／20 日有效數 ≤ 60／20、
   進場日 ＞ 形成月底（跳月）。
K5 git 工作樹：本件只新增 researchPTH10tie*.py 與 resultsPTH10tie/main/。
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTH10tie as T                  # noqa: E402
from backtest import researchIndMom_freq_check as IC        # noqa: E402
from backtest import benchmark_rejudge as BR_               # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402

OUT = T.OUT
LOG = []


def log(m):
    print(m, flush=True); LOG.append(str(m))


def rel(a, b):
    a, b = float(a), float(b)
    if np.isnan(a) and np.isnan(b):
        return 0.0
    return abs(a - b) / max(1.0, abs(b))


def win_xy(dates, a, b):
    d = pd.DatetimeIndex(pd.to_datetime(dates))
    return int(d.searchsorted(pd.Timestamp(a))), int(d.searchsorted(pd.Timestamp(b), side="right")) - 1


def main():
    CK = {"K0_登錄sha": IC.reg_ok(T.REG_SHA), "K0_策略鎖": IC.lock_ok()}
    R = json.load(open(os.path.join(OUT, "result.json"), encoding="utf-8"))
    rank = pd.read_csv("backtest/resultsBenchRejudge/rank.csv", encoding="utf-8-sig", dtype=str)
    K1bad = K2bad = 0; K1n = 0; K3 = {}; K4 = {}
    for wn in ("主", "早年"):
        Z = np.load(os.path.join(OUT, f"raw_{wn}.npz"))
        dates = Z["dates"]
        C = pd.read_csv(os.path.join(OUT, f"cells_{wn}.csv"), encoding="utf-8-sig", float_precision="round_trip")
        Wj = json.load(open(os.path.join(OUT, f"world_{wn}.json"), encoding="utf-8"))
        WIN = {sg: win_xy(dates, *w.split("～")) for sg, w in Wj["窗"].items()}
        SE = Z["seeds_eq"]
        dist = {sg: np.array([BR_.estat(e, x, y) for e in SE]) for sg, (x, y) in WIN.items()}
        for _, r in C.iterrows():
            x, y = WIN[r["段"]]
            c, m = BR_.estat(Z[f"{r['排序']}{'s' if r['滑價'] else ''}_eq"], x, y)
            K1n += 1
            if rel(c, r["年化"]) > 1e-9 or rel(m, r["回落"]) > 1e-9:
                K1bad += 1; log(f"K1 不符 {wn} {r['排序']} {r['段']} {c} {r['年化']} {m} {r['回落']}")
            if not r["滑價"]:
                dv = dist[r["段"]]; rt = dv[:, 0] / np.abs(dv[:, 1])
                for col, v, dd in (("年化", c, dv[:, 0]), ("比值", AS.ratio(c, m), rt)):
                    if abs((dd <= v).mean() - r[f"{col}_百分位(≤)"]) > 1e-12 or abs((dd < v).mean() - r[f"{col}_百分位(<)"]) > 1e-12:
                        K1bad += 1; log(f"K1 百分位不符 {wn} {r['排序']} {r['段']} {col}")
        # K2
        sgmap = {"主": {"確認": "確認", "探索": "探索"}, "早年": {}}[wn]
        for sg, rsg in sgmap.items():
            dv = dist[sg]
            rr = rank[(rank["段"] == rsg) & (rank["策略"] == "高10")].iloc[0]
            if Wj["窗"][sg] != rr["窗"]:
                K2bad += 1; log(f"K2 窗不同 {sg}")
            for v, col in ((np.median(dv[:, 0]), "年化"), (np.median(dv[:, 1]), "回落")):
                if "%.10g" % v != rr[col]:
                    K2bad += 1; log(f"K2 高10 200 組中位 {sg} {col} {v} ≠ {rr[col]}")
            c0 = C[(C["排序"] == "原") & (~C["滑價"]) & (C["段"] == sg)].iloc[0]
            for nm, cc, mc in (("大盤（報酬指數）", "大盤年化", "大盤回落"), ("0050", "0050年化", "0050回落")):
                rb = rank[(rank["段"] == rsg) & (rank["策略"] == nm)].iloc[0]
                for col, v in (("年化", c0[cc]), ("回落", c0[mc])):
                    if rel(v, float(rb[col])) > 1e-9:
                        K2bad += 1; log(f"K2 {nm} {sg} {col} {v} ≠ {rb[col]}")
        # K3
        KD = pd.read_csv(os.path.join(OUT, f"keys_{wn}.csv.gz"), dtype={"sid": str, "形成月底": str, "進場日": str}, float_precision="round_trip")
        res = {}
        for nm in T.ORDS:
            tf = pd.read_csv(os.path.join(OUT, f"trades_{wn}_{nm}.csv.gz"), dtype=str, keep_default_na=False)
            if nm == "原":
                with gzip.open(os.path.join(OUT, f"trades_{wn}_原.csv.gz"), "rt", encoding="utf-8") as a_, \
                        gzip.open(f"backtest/resultsPTHn/trades_{wn}_N10.csv.gz", "rt", encoding="utf-8") as b_:
                    res["原交易檔 ＝ resultsPTHn N10 全文"] = a_.read() == b_.read()
            fl = np.zeros(len(KD), bool) if nm == "原" else KD[f"{nm}_算不出"].to_numpy(bool)
            sc = np.zeros(len(KD)) if nm == "原" else KD[f"{nm}_鍵"].to_numpy(float)
            iv = list(zip(tf["sid"], tf["買進日"], [x if x else "9999-12-31" for x in tf["賣出日"]]))
            nb = 0; bad = 0
            for e, g in tf.groupby("買進日"):
                cand = KD[KD["進場日"] == e]
                held = {s for s, b, x in iv if b < e <= x}
                cand = cand[~cand["sid"].isin(held)]
                ii = cand.index.to_numpy()
                o = np.lexsort((KD["rk原"].to_numpy()[ii], -sc[ii], fl[ii].astype(np.int8), -KD["PTH"].to_numpy()[ii]))
                top = set(cand["sid"].to_numpy()[o][:len(g)])
                nb += 1
                if top != set(g["sid"]):
                    bad += 1
            res[nm] = f"{nb} 批、不符 {bad}"
        K3[wn] = res
        # K4
        MB = pd.read_csv(os.path.join("backtest/resultsPTH10tie/freq", f"members_{wn}.csv.gz"), dtype={"sid": str, "形成月底": str, "進場日": str, "rev_avail_date": str},
                         float_precision="round_trip")
        kd = KD.set_index("q")
        mis = 0
        for nm, (col, neg) in T.KEYCOL.items():
            v = MB[col].to_numpy(float) * (-1 if neg else 1)
            kk = kd.loc[MB["q"].to_numpy()]
            fl_ = kk[f"{nm}_算不出"].to_numpy(bool)
            mis += int((fl_ != ~np.isfinite(v)).sum()) + int((np.abs(kk[f"{nm}_鍵"].to_numpy(float)[~fl_] - v[~fl_]) > 0).sum())
        ra = MB["rev_avail_date"].fillna("")
        K4[wn] = {"排序鍵 ≠ members（列）": mis,
                  "月營收可得日 ＞ 形成月底（列）": int(((ra != "") & (ra > MB["形成月底"])).sum()),
                  "vol60_n ＞ 60 或 max20_n ＞ 20": int(((MB["vol60_n"] > 60) | (MB["max20_n"] > 20)).sum()),
                  "進場日 ≤ 形成月底（事件）": int((KD["進場日"] <= KD["形成月底"]).sum()),
                  "非同分群事件鍵非 0／旗標": int(sum(((KD["grp"] < 0) & (KD[f"{nm}_算不出"].astype(bool) | (KD[f"{nm}_鍵"] != 0))).sum() for nm in T.KEYCOL))}
    # K1 判定
    C = pd.read_csv(os.path.join(OUT, "cells_主.csv"), encoding="utf-8-sig", float_precision="round_trip")
    vd = {nm: T.verdict_of(C, nm)[0] for nm in T.JUDGED}
    vbad = sum(vd[nm] != R["判定"][nm]["成立"] for nm in T.JUDGED)
    CK["K1_統計重算"] = f"{K1n} 格、不符 {K1bad}"; CK["K1_判定重算"] = f"{vd}｜與 result.json 不符 {vbad}"
    CK["K2_對排名表"] = f"不符 {K2bad}"; CK["K3_動態路徑照鍵"] = K3; CK["K4_鍵與不前視"] = K4
    st = subprocess.run(["git", "-c", "core.quotepath=off", "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout.splitlines()
    mine = [l for l in st if "researchPTH10tie" in l or "resultsPTH10tie/" in l]
    CK["K5_本件git"] = {"本件相關": len(mine), "非新增": [l for l in mine if not l.startswith("??")],
                       "範圍外": [l for l in mine if not (l[3:].startswith("backtest/researchPTH10tie.py") or l[3:].startswith("backtest/researchPTH10tie_check.py")
                                                      or l[3:].startswith("backtest/resultsPTH10tie/main/"))]}
    ok3 = all((v is True) or (isinstance(v, str) and v.endswith("不符 0")) for w in K3.values() for v in w.values())
    ok4 = all(v == 0 for w in K4.values() for v in w.values())
    CK["全過"] = bool(CK["K0_登錄sha"][0] and CK["K0_策略鎖"][0] and K1bad == 0 and vbad == 0 and K2bad == 0 and ok3 and ok4
                    and not CK["K5_本件git"]["非新增"] and not CK["K5_本件git"]["範圍外"])
    log(json.dumps(CK, ensure_ascii=False, indent=1, default=str))
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

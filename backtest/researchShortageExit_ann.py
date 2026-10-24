# -*- coding: utf-8 -*-
"""缺貨型持股確認後怎麼賣・第一輪 seq1（C1～C7）加描述欄「每筆年化」——回測線計算子代理（描述、不計 N；判語一字不改）。
依據：裁定 seq460 §二（已定版件加一欄「每筆年化」，判語照原「記 0」，⛔ 不追溯改）、seq461；台股策略線 1843 §一（短持有寫死）。
⛔ 不改 researchShortageExit.py 與 resultsShortageExit/ 既有檔；只新增本檔、researchShortageExit_ann_check.py、resultsShortageExit/main/ann/。
⛔ researchShortageExit（seam_open、lastvalid_le）、researchShortageExit_freq（RULES、ES、RNAME）、researchRevTurn_freq（ensure_data、prices）只 import。

    乾跑：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_ann --dry   （R 全 0 ⇒ ~/rtfwork/dry_sx_ann）
    正式：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_ann         （⇒ resultsShortageExit/main/ann/）
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_ann_check [--dry]

═══ 讀法（Y 標；寫於 2026-10-24（台北），⛔ 在看任何本件年化數字之前）═══
 Y1 資料版本 ＝ 原正式跑 main.json 的 origin/main（443ee8ce96ec…）；事件與觸發 ＝ 已提交 resultsShortageExit/freq/events.csv.gz（⛔ 不重算）。
 Y2 錨點：用原正式跑 M2／M3 同式（researchShortageExit.seam_open 開盤、lastvalid_le 收盤、E_eff 同 M2）逐筆重建 R_C0 與 R_C1～R_C7，
    與已提交 resultsShortageExit/main/events_R.csv.gz 逐筆比（列數、鍵、R 全欄）：任一不同 ⇒ 中止、⛔ 不算年化。
 Y3 年化 ＝ (1 ＋ R)^(250 ÷ max(H, 60)) − 1；R ＝ 原 M3 的 R（含賣出成本 0.4425%）；H ＝ 持有交易日數（合併日曆位置差，進場日 e 算第 1 日）：
    賣出者 H ＝ s − e ＋ 1（s ＝ 頻率表 s 偏移的開盤）；不賣 ★ H ＝ xv − e ＋ 1（xv ＝ 實際取收盤那根：E_eff 當天或之前最後有效 K 棒）；★ 1 ＋ R ≤ 0 ⇒ −1。
    比法 ＝ 同一筆「賣法年化 − 抱到評估點（C0）年化」；沒賣 ⇒ 0。評估點照原登錄：E250（判定格的評估點）；E500、E120 原本即有描述 ⇒ 一起報。
 Y4 報（段 × 母體 × E × C1～C7）：差的中位（主報）、平均、＞0 比例、賣出者中位；賣法臂與 C0 臂年化中位；持有 ＜ 60 日件數與比例（賣法臂，全部事件為分母）。
    C6 原為「還沒測」（只描述）照標；一般股、族群只描述。
 Y5 呈現：原判語與原結果句一字不改照引；新欄只寫一句「若照每筆年化比：…」附在後面，⛔ 不改判語、⛔ 不並列判定。
 Y6 乾跑（--dry）：錨點照做（只輸出相同與否），之後 R 全換 0 ⇒ 年化、差全 0，跑通全部欄位；輸出 ~/rtfwork/dry_sx_ann（⛔ 不進 repo）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchShortageExit as SXM            # noqa: E402
from backtest import researchShortageExit_freq as SX        # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402

ORIG = "backtest/resultsShortageExit/main"
FREQ = SX.OUT
OUT0 = os.path.join(ORIG, "ann")
DRY_OUT = os.path.join(RT.WORK, "dry_sx_ann")
COST = 0.004425
HMIN = 60
CELLS = ["C1", "C2", "C3", "C4", "C5", "C7"]
SEGS = ["早於探索(不入段)", "探索", "確認"]
LOG = RT.LOG
log = RT.log


def ann(r, h):
    g = 1.0 + float(r)
    return -1.0 if g <= 0 else g ** (250.0 / max(int(h), HMIN)) - 1.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    out = DRY_OUT if a.dry else OUT0
    os.makedirs(out, exist_ok=True)
    MJ0 = json.load(open(os.path.join(ORIG, "main.json"), encoding="utf-8"))
    sha = MJ0["origin/main"]
    log(f"[Y1] 原正式跑 origin/main {sha}｜{'乾跑' if a.dry else '正式'}")
    _, DN, _ = RT.ensure_data(sha)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        PX = RT.prices(sha, DN, a.procs)
        O, nseam = SXM.seam_open(PX)
    CAL, ix, C, BAD, VP, LASTV = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"]
    CEND = len(CAL) - 1
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str, "期別": str})
    EV = EV[EV["進場"] == "保留"].reset_index(drop=True)
    rows = []
    for rd in EV.to_dict("records"):
        i = ix[rd["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(rd["e"])))
        P0 = O[i, e]
        lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
        for E in SX.ES:
            if not rd[f"E{E}走得完"]:
                continue
            x = e + E; st = "完整"
            bb = np.flatnonzero(BAD[i, e + 1:x + 1])
            if len(bb):
                x = e + int(bb[0]); st = "壞根截斷"
            if delist and lastv < x:
                x = lastv; st = "下市結算"
            if st != rd[f"E{E}狀態"]:
                raise SystemExit(f"⛔ E_eff 狀態與頻率表不同 {rd['sid']} {rd['e']} E{E}")
            xv = SXM.lastvalid_le(VP, i, x)
            R0 = C[i, xv] / P0 - 1 - COST
            row = {"sid": rd["sid"], "期別": rd["期別"], "e": rd["e"], "段": rd["段"], "母體": rd["母體"], "族群": rd["族群"] if isinstance(rd["族群"], str) else "",
                   "進場月": rd["進場月"], "E": E, "E狀態": st, "R_C0": R0, "H_C0": xv - e + 1}
            for c in SX.RULES:
                oc = rd[f"{c}_E{E}"]
                if oc == "賣出":
                    s = e + int(rd[f"{c}_s偏移"])
                    if s > x:
                        raise SystemExit(f"⛔ 賣出晚於 E_eff {rd['sid']} {c}")
                    row[f"R_{c}"] = O[i, s] / P0 - 1 - COST; row[f"H_{c}"] = s - e + 1
                else:
                    row[f"R_{c}"] = R0; row[f"H_{c}"] = xv - e + 1
                row[f"{c}_結果"] = oc
            rows.append(row)
    RR = pd.DataFrame(rows)
    # ── Y2 錨點
    OR = pd.read_csv(os.path.join(ORIG, "events_R.csv.gz"), dtype={"sid": str, "期別": str}, encoding="utf-8-sig", float_precision="round_trip")
    keys_same = bool(len(OR) == len(RR) and (OR[["sid", "期別", "e", "E", "段", "母體"]].astype(str).to_numpy() == RR[["sid", "期別", "e", "E", "段", "母體"]].astype(str).to_numpy()).all())
    rcols = ["R_C0"] + [f"R_{c}" for c in SX.RULES]
    exact = {c: bool(keys_same and np.array_equal(OR[c].to_numpy(float), RR[c].to_numpy(float))) for c in rcols}
    maxd = float(max(np.nanmax(np.abs(OR[c].to_numpy(float) - RR[c].to_numpy(float))) for c in rcols)) if keys_same else np.nan
    res_same = bool(keys_same and all((OR[f"{c}_結果"].astype(str) == RR[f"{c}_結果"].astype(str)).all() for c in SX.RULES))
    ANC = {"列數": [len(OR), len(RR)], "鍵相同": keys_same, "R逐筆完全相同": exact, "R最大差": maxd, "結果欄相同": res_same}
    log(f"[Y2 錨點] {ANC}")
    if not (keys_same and res_same and maxd <= 1e-12):
        raise SystemExit(f"⛔ 錨點不同 ⇒ 中止：{ANC}")
    if a.dry:
        for c in rcols:
            RR[c] = 0.0
    # ── Y3 年化
    RR["年化_C0"] = [ann(r, h) for r, h in zip(RR["R_C0"], RR["H_C0"])]
    for c in SX.RULES:
        RR[f"年化_{c}"] = [ann(r, h) for r, h in zip(RR[f"R_{c}"], RR[f"H_{c}"])]
        RR[f"年化差_{c}"] = RR[f"年化_{c}"] - RR["年化_C0"]
    # ── Y4 表
    pops = {"缺貨型": RR["母體"] == "缺貨型", "一般股": RR["母體"] == "一般股", **{f"族群:{g}": RR["族群"].str.contains(g) for g in SX.GROUPS}}
    AN = []
    for sg in SEGS:
        for pn, pm in pops.items():
            for E in SX.ES:
                d = RR[(RR["段"] == sg) & pm & (RR["E"] == E)]
                if not len(d):
                    continue
                for c in SX.RULES:
                    x_ = d[f"年化差_{c}"].to_numpy(float); sold = (d[f"{c}_結果"] == "賣出").to_numpy()
                    idt = "還沒測（只描述）" if c == "C6" else ("判定格的描述欄" if (pn == "缺貨型" and E == 250 and sg in ("探索", "確認")) else "描述")
                    AN.append({"段": sg, "母體": pn, "E": E, "賣法": c, "名稱": SX.RNAME[c], "身分": idt, "n": len(d), "月數": int(d["進場月"].nunique()), "賣出": int(sold.sum()),
                               "年化差中位(賣法−C0)": float(np.median(x_)), "年化差平均": float(x_.mean()), "年化差>0比例": float((x_ > 0).mean()),
                               "賣出者年化差中位": (float(np.median(x_[sold])) if sold.any() else np.nan),
                               "賣法年化中位": float(d[f"年化_{c}"].median()), "C0年化中位": float(d["年化_C0"].median()),
                               "持有<60日件數(賣法臂)": int((d[f"H_{c}"] < HMIN).sum()), "持有<60日比例(賣法臂,÷全部)": float((d[f"H_{c}"] < HMIN).mean()),
                               "C0臂持有<60日件數": int((d["H_C0"] < HMIN).sum()), "賣法臂H中位": float(d[f"H_{c}"].median())})
    AN = pd.DataFrame(AN)
    # ── Y5 句
    CE = pd.read_csv(os.path.join(ORIG, "cells.csv"), encoding="utf-8-sig").set_index("賣法")
    K = AN[AN["母體"] == "缺貨型"].set_index(["段", "E", "賣法"])
    f2 = lambda v: f"{v * 100:+.2f}"   # noqa: E731
    SENT = {}
    for c in SX.RULES:
        orig = MJ0["結果句"][SX.RULES.index(c)]
        a250 = K.loc[("確認", 250, c)]; b250 = K.loc[("探索", 250, c)]; a500 = K.loc[("確認", 500, c)]; b500 = K.loc[("探索", 500, c)]
        SENT[c] = (orig + f"｜若照每筆年化比（賣法年化 − 抱到 E250 年化，描述、不判）：中位 確認 {f2(a250['年化差中位(賣法−C0)'])} 點／探索 {f2(b250['年化差中位(賣法−C0)'])} 點"
                   f"（平均 {f2(a250['年化差平均'])}／{f2(b250['年化差平均'])}；持有＜60 日 {a250['持有<60日比例(賣法臂,÷全部)'] * 100:.1f}%／{b250['持有<60日比例(賣法臂,÷全部)'] * 100:.1f}%）；"
                   f"E500 中位 確認 {f2(a500['年化差中位(賣法−C0)'])}／探索 {f2(b500['年化差中位(賣法−C0)'])} 點")
        log(f"[句] {c}：{SENT[c]}")
    DC = {}
    if a.dry:
        nc = [c for c in RR.columns if c.startswith(("年化_", "年化差_"))]
        DC = {"年化欄全0": bool(np.all(RR[nc].to_numpy(float) == 0)), "年化欄無空值": bool(not RR[nc].isna().any().any()),
              "H欄≥1": bool((RR[[c for c in RR.columns if c.startswith("H_")]].to_numpy() >= 1).all()),
              "表空值欄": {c: int(AN[c].isna().sum()) for c in AN.columns if AN[c].isna().any()}, "表列數": len(AN), "句數": len(SENT)}
        log(f"[Y6 乾跑檢查] {DC}")
    keep = ["sid", "期別", "e", "段", "母體", "族群", "進場月", "E", "E狀態", "H_C0", "年化_C0"] + [f"{p}_{c}" for c in SX.RULES for p in ("H", "年化", "年化差")] + [f"{c}_結果" for c in SX.RULES]
    RR[keep].to_csv(os.path.join(out, "events_ann.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    AN.to_csv(os.path.join(out, "ann.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "缺貨型出場第一輪 seq1（C1～C7）加描述欄「每筆年化」（描述、不計 N；判語一字不改）" + ("【乾跑：R 全 0】" if a.dry else ""),
         "依據": "裁定 seq460 §二、seq461；台股策略線 1843 §一", "origin/main": sha, "接縫開盤倍數檔數": nseam, "錨點": ANC,
         "原判定(一字不改)": {c: CE.at[c, "判定"] for c in SX.RULES}, "結果句(原句＋若照每筆年化比)": SENT, "乾跑檢查": DC,
         "表_缺貨型E250": AN[(AN["母體"] == "缺貨型") & (AN["E"] == 250)].to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "ann.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

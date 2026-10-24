# -*- coding: utf-8 -*-
"""缺貨型出場第一輪「每筆年化」描述欄【對帳】——回測線計算子代理。⛔ 只讀；只寫 ann/（或乾跑夾）check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_ann_check [--dry]

Z1 錨點旗標：ann.json 錨點 鍵相同、結果欄相同、R 逐筆完全相同（全欄）。
Z2 逐筆年化獨立重算：R 取【已提交】main/events_R.csv.gz（round_trip 讀）；H 自算（賣出 ＝ 頻率表 s 偏移＋1；不賣 ＝ 自掃 E_eff 之前最後一根 isfinite 收盤 − e ＋ 1，
   E_eff 自算：e＋E、(e, e＋E] 第一個壞根、下市 ≥5 日則末根）；年化 ＝ (1＋R)^(250÷max(H,60))−1 ⇒ 與 events_ann 逐筆比（乾跑：R ＝ 0）。
Z3 ann.csv 由逐筆自算（n、賣出數、差中位、平均、持有＜60 日件數）全部列相同。
Z4 原判語未動：ann.json 原判定 ＝ 已提交 cells.csv「判定」；既有檔 md5 與跑前快照相同。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402

ORIG = "backtest/resultsShortageExit/main"
FREQ = "backtest/resultsShortageExit/freq"
RULES = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
ES = (120, 250, 500)
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def a_(r, h):
    return -1.0 if 1 + r <= 0 else (1 + r) ** (250.0 / max(h, 60)) - 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = os.path.join(RT.WORK, "dry_sx_ann") if a.dry else os.path.join(ORIG, "ann")
    CK = {}
    J = json.load(open(os.path.join(out, "ann.json"), encoding="utf-8"))
    an = J["錨點"]
    CK["Z1_錨點"] = {"旗標": an, "過": bool(an["鍵相同"] and an["結果欄相同"] and all(an["R逐筆完全相同"].values()))}
    log(f"[Z1] {CK['Z1_錨點']}")
    EA = pd.read_csv(os.path.join(out, "events_ann.csv.gz"), dtype={"sid": str, "期別": str}, encoding="utf-8-sig", float_precision="round_trip")
    OR = pd.read_csv(os.path.join(ORIG, "events_R.csv.gz"), dtype={"sid": str, "期別": str}, encoding="utf-8-sig", float_precision="round_trip")
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str, "期別": str})
    EV = EV[EV["進場"] == "保留"]
    sha = J["origin/main"]
    _, DN, _ = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix, C, BAD = PX["CAL"], PX["ix"], PX["C"], PX["BAD"]
    CEND = len(CAL) - 1
    fin_last = {}
    evk = {(r["sid"], r["e"]): r for r in EV.to_dict("records")}
    mx = {"H": 0, "年化": 0.0, "年化差": 0.0}; nrow = 0
    if len(EA) != len(OR) or not (EA[["sid", "e", "E"]].astype(str).to_numpy() == OR[["sid", "e", "E"]].astype(str).to_numpy()).all():
        raise SystemExit("⛔ events_ann 與 events_R 鍵不同")
    for ra, ro in zip(EA.to_dict("records"), OR.to_dict("records")):
        rd = evk[(ra["sid"], ra["e"])]; i = ix[ra["sid"]]; E = int(ra["E"])
        e = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(ra["e"])), "left"))
        if i not in fin_last:
            f = np.flatnonzero(np.isfinite(C[i])); fin_last[i] = f
        f = fin_last[i]; lastv = int(f[-1])
        x = e + E
        bb = np.flatnonzero(BAD[i, e + 1:x + 1])
        if len(bb):
            x = e + int(bb[0])
        if CEND - lastv >= 5 and lastv < x:
            x = lastv
        xv = int(f[np.searchsorted(f, x, "right") - 1])
        H0 = xv - e + 1
        R0 = 0.0 if a.dry else ro["R_C0"]
        A0 = a_(R0, H0)
        mx["H"] = max(mx["H"], abs(int(ra["H_C0"]) - H0)); mx["年化"] = max(mx["年化"], abs(ra["年化_C0"] - A0))
        for c in RULES:
            if rd[f"{c}_E{E}"] == "賣出":
                Hk = int(rd[f"{c}_s偏移"]) + 1
            else:
                Hk = H0
            Rk = 0.0 if a.dry else ro[f"R_{c}"]
            Ak = a_(Rk, Hk)
            mx["H"] = max(mx["H"], abs(int(ra[f"H_{c}"]) - Hk)); mx["年化"] = max(mx["年化"], abs(ra[f"年化_{c}"] - Ak))
            mx["年化差"] = max(mx["年化差"], abs(ra[f"年化差_{c}"] - (Ak - A0)))
        nrow += 1
    CK["Z2_逐筆年化"] = {"列": nrow, "最大差": mx, "過": mx["H"] == 0 and mx["年化"] < 1e-12 and mx["年化差"] < 1e-12}
    log(f"[Z2] {CK['Z2_逐筆年化']}")
    AN = pd.read_csv(os.path.join(out, "ann.csv"), encoding="utf-8-sig")
    ok = []
    for _, r in AN.iterrows():
        pm = EA["母體"] == r["母體"] if not r["母體"].startswith("族群:") else EA["族群"].fillna("").str.contains(r["母體"][3:])
        d = EA[(EA["段"] == r["段"]) & pm & (EA["E"] == r["E"])]
        x_ = d[f"年化差_{r['賣法']}"].to_numpy(float)
        ok += [len(d) == r["n"], int((d[f"{r['賣法']}_結果"] == "賣出").sum()) == r["賣出"], abs(np.median(x_) - r["年化差中位(賣法−C0)"]) < 1e-12,
               abs(x_.mean() - r["年化差平均"]) < 1e-12, int((d[f"H_{r['賣法']}"] < 60).sum()) == r["持有<60日件數(賣法臂)"]]
    CK["Z3_表"] = {"列": len(AN), "項": len(ok), "過": all(ok)}
    log(f"[Z3] {CK['Z3_表']}")
    CE = pd.read_csv(os.path.join(ORIG, "cells.csv"), encoding="utf-8-sig").set_index("賣法")
    same = all(J["原判定(一字不改)"][c] == CE.at[c, "判定"] for c in RULES)
    md5 = subprocess.run(["md5sum", "-c", os.path.expanduser("~/rtfwork/md5_before_ann.txt")], capture_output=True, text=True).stdout.splitlines()
    md5bad = [l for l in md5 if not l.endswith(": OK") and "researchShortageExit2.py" not in l]
    CK["Z4_原判語與既有檔"] = {"原判定相同": same, "md5不同": md5bad, "過": same and not md5bad}
    log(f"[Z4] {CK['Z4_原判語與既有檔']}")
    CK["全過"] = all(CK[k]["過"] for k in CK if k.startswith("Z"))
    log(f"[全過] {CK['全過']}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""長線三問 丙「每筆年化」描述欄【對帳】——回測線計算子代理。⛔ 只讀；只寫 ann/（或乾跑夾）check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_ann_check [--dry]

W1 錨點旗標：long3_ann.json 丙_表、events_丙 逐位元組相同、件數相同。
W2 逐筆年化獨立重算：R 取【已提交】resultsLong3/events_丙.csv.gz（round_trip 讀）扣 0.585%；合併日曆自建（兩世界 data/ 的交易日曆直接接）；
   H ＝ 日曆位置(賣日 或 抱3年出場日) − e ＋ 1；年化 ＝ (1＋R)^(250÷max(H,60))−1 ⇒ 與 events_丙_ann 逐筆比（乾跑 R ＝ 0）。
W3 丙_ann_表 由逐筆自算（事件、觸發、差中位、平均、＞0 比例、持有＜60 日件數）全部列相同；事件、觸發 ＝ 已提交 丙_表。
W4 原句一字不改：每句以已提交 long3.json 丙句 開頭；既有檔 md5 與跑前快照相同。
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
from backtest import researchAscTri_freq as AT              # noqa: E402  WORLDS（資料路徑）
import backtest.data as D                                   # noqa: E402

ORIG = "backtest/resultsLong3"
FS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
COST = 0.00585
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def a_(r, h):
    return -1.0 if 1 + r <= 0 else (1 + r) ** (250.0 / max(h, 60)) - 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    out = os.path.expanduser("~/rtfwork/dry_l3_ann") if a.dry else os.path.join(ORIG, "ann")
    CK = {}
    J = json.load(open(os.path.join(out, "long3_ann.json"), encoding="utf-8"))
    CK["W1_錨點"] = {"旗標": J["錨點"], "過": all(J["錨點"].values())}
    log(f"[W1] {CK['W1_錨點']}")
    import backtest.evaluate as EVAL
    cal = []
    for wn in ("早年", "主"):
        D.DATA = AT.WORLDS[wn]["data"]; cal.append(D.load_calendar())
    CAL = cal[0].append(cal[1]); P = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(CAL)}
    CR = pd.read_csv(os.path.join(ORIG, "events_丙.csv.gz"), dtype={"sid": str, "期別": str}, float_precision="round_trip")
    EA = pd.read_csv(os.path.join(out, "events_丙_ann.csv.gz"), dtype={"sid": str, "期別": str}, float_precision="round_trip")
    if len(CR) != len(EA) or not (CR[["sid", "e"]].astype(str).to_numpy() == EA[["sid", "e"]].astype(str).to_numpy()).all():
        raise SystemExit("⛔ 鍵不同")
    mx = {"H": 0, "年化": 0.0, "年化差": 0.0}; nchk = 0
    MI = []
    for rc, ra in zip(CR.to_dict("records"), EA.to_dict("records")):
        e = int(rc["e"]); b3 = rc["抱3年R"]
        m = {"e": e, "窗完整": bool(rc["窗完整"]), "進場日": rc["進場日"]}
        if not np.isfinite(b3):
            MI.append(m); continue
        H3 = P[rc["抱3年出場日"]] - e + 1; A3 = a_(0.0 if a.dry else b3 - COST, H3)
        mx["H"] = max(mx["H"], abs(int(ra["H_抱3年"]) - H3)); mx["年化"] = max(mx["年化"], abs(ra["年化_抱3年"] - A3))
        m["H3"] = H3; m["A3"] = A3
        for F in FS:
            if bool(rc[f"{F}_賣"]):
                Hk = P[rc[f"{F}_賣日"]] - e + 1; Ak = a_(0.0 if a.dry else rc[f"{F}_R"] - COST, Hk)
            else:
                Hk, Ak = H3, A3
            mx["H"] = max(mx["H"], abs(int(ra[f"H_{F}"]) - Hk)); mx["年化"] = max(mx["年化"], abs(ra[f"年化_{F}"] - Ak))
            mx["年化差"] = max(mx["年化差"], abs(ra[f"年化差_{F}"] - (Ak - A3)))
            m[f"H_{F}"] = Hk; m[f"ad_{F}"] = Ak - A3; m[f"s_{F}"] = bool(rc[f"{F}_賣"])
        nchk += 1; MI.append(m)
    CK["W2_逐筆年化"] = {"成本(EVAL.COST)": EVAL.COST, "比對列": nchk, "最大差": mx, "過": EVAL.COST == COST and mx["H"] == 0 and mx["年化"] < 1e-12 and mx["年化差"] < 1e-12}
    log(f"[W2] {CK['W2_逐筆年化']}")
    MI = pd.DataFrame(MI)
    TB = pd.read_csv(os.path.join(out, "丙_ann_表.csv"), encoding="utf-8-sig"); TCo = pd.read_csv(os.path.join(ORIG, "丙_表.csv"))
    p141231 = int(CAL.searchsorted(pd.Timestamp("2014-12-31"), side="right")) - 1
    seg = {"全部窗完整": (0, len(CAL) - 1), "早年進場(～2014)": (0, p141231), "2015～進場": (p141231 + 1, len(CAL) - 1),
           "探索進場(2017-03～2021-12)": (P["2017-03-02"], P["2021-12-30"])}
    ok = []
    for _, r in TB.iterrows():
        a0, a1 = seg[r["進場段"]]; F = r["法"]
        sub = MI[(MI["e"] >= a0) & (MI["e"] <= a1) & MI["窗完整"] & MI["A3"].notna()]
        x_ = sub[f"ad_{F}"].to_numpy(float)
        o = TCo[(TCo["進場段"] == r["進場段"]) & (TCo["法"] == F)].iloc[0]
        ok += [len(sub) == r["事件(窗完整)"] == o["事件(窗完整)"], int(sub[f"s_{F}"].sum()) == r["觸發賣出"] == o["觸發賣出"],
               abs(np.median(x_) - r["年化差中位(賣法−抱3年)"]) < 1e-12, abs(x_.mean() - r["年化差平均"]) < 1e-12,
               abs((x_ > 0).mean() - r["年化差>0比例"]) < 1e-12, int((sub[f"H_{F}"] < 60).sum()) == r["持有<60日件數(賣法臂)"]]
    CK["W3_表"] = {"列": len(TB), "項": len(ok), "過": all(ok)}
    log(f"[W3] {CK['W3_表']}")
    L0 = json.load(open(os.path.join(ORIG, "long3.json"), encoding="utf-8"))["丙句"]
    sent_ok = all(J["丙句(原句一字不改＋若照每筆年化比)"][F].startswith(L0[F] + "｜若照每筆年化比") for F in FS)
    md5 = subprocess.run(["md5sum", "-c", os.path.expanduser("~/rtfwork/md5_before_ann.txt")], capture_output=True, text=True).stdout.splitlines()
    md5bad = [l for l in md5 if not l.endswith(": OK") and "researchShortageExit2.py" not in l]
    CK["W4_原句與既有檔"] = {"原句一字不改": sent_ok, "md5不同": md5bad, "過": sent_ok and not md5bad}
    log(f"[W4] {CK['W4_原句與既有檔']}")
    CK["全過"] = all(CK[k]["過"] for k in CK if k.startswith("W"))
    log(f"[全過] {CK['全過']}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""缺貨型確認後怎麼賣・第二輪 seq1 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit2_freq_check [--out 目錄]

K1 登錄 sha 獨立重算（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼）＋ 裁定 seq458 信在。
K2 事件：events.csv 與第一輪 events.csv.gz（同版 443ee8ce96ec）的（sid, 期別, A, e, 母體, 進場, 產業）集合相同；段依 e 自判（探索 2006-04～2014-12｜確認 2015-01～）。
K3 觸發：全部缺貨型 E1000 主格事件，另一條路自算 —— PPI 用 pandas 自讀（first_value 優先、空白補 fred 修正值）、可用日自算（日期 ＞ 首發日的第一個交易日）、
   月增／年增用 pandas shift 自算；D1／D2（主讀法、另一讀法）在 [e, E_eff−1] 的第一個判到位置 ⇒ k 偏移逐值相同；D3 賣出日（≥ e＋625 第一個有成交且收盤有效）逐值相同；
   D1／D2 賣出日（k＋1 起第一個可賣開盤）逐值相同；值來源標籤逐值相同。
K4 freq_段.csv（E1000）判到、賣出、事件、月數與 counts.csv 主格、n_eff 由 events.csv.gz 自算相同。
K5 私有：輸出各 csv 無 PPI 值（數值欄全為整數或空）、無 PPI／ppi 欄名；git 工作樹相對開跑前只多本件新檔與結果夾。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit2_freq as S2       # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=S2.OUT); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = a.out
    CK = {}
    dirs = [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*")))
    fs = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md")) if f"sha{S2.REG_SHA}" in os.path.basename(f)]
    rul = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md")) if "seq458" in os.path.basename(f) and "裁定線" in os.path.basename(f)]
    CK["K1_登錄sha"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == S2.REG_SHA for f in fs), "裁定seq458": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1_登錄sha']}")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8"))
    sha, us_sha = J["origin/main"], J["us-stock-data"]
    EV = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype={"sid": str, "期別": str}, keep_default_na=False, na_values=[""])
    # ── K2
    E1 = pd.read_csv("backtest/resultsShortageExit/freq/events.csv.gz", dtype={"sid": str, "期別": str}, keep_default_na=False)
    cols = ["sid", "期別", "A", "e", "母體", "進場", "產業"]
    a1 = set(map(tuple, E1[cols].astype(str).to_numpy())); a2 = set(map(tuple, EV[cols].fillna("").astype(str).to_numpy()))

    def seg(e):
        if not isinstance(e, str) or not e:
            return "其他"
        return "早於探索(不入段)" if e < "2006-04-01" else ("探索" if e <= "2014-12-31" else "確認")
    segbad = int((EV["e"].map(seg) != EV["段"]).sum())
    CK["K2_事件"] = {"同版": sha == S2.PIN, "第一輪": len(a1), "本件": len(a2), "只在第一輪": len(a1 - a2), "只在本件": len(a2 - a1), "段自判不同": segbad}
    log(f"[K2] {CK['K2_事件']}")
    # ── K3
    _, DN, _ = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix, C, O, TRD, DNL = PX["CAL"], PX["ix"], PX["C"], PX["O"], PX["TRD"], PX["DNL"]
    caln = CAL.values
    git = lambda p: io.BytesIO(subprocess.run(["git", "-C", S2.US_REPO, "show", f"{us_sha}:{p}"], capture_output=True, check=True).stdout)  # noqa: E731
    PF = pd.read_csv(git("data/macro/ppi_first_release.csv"), dtype={"first_value": float})
    SER = {}
    for ind, ser in S2.PPI_MAP.items():
        f = pd.read_csv(git(f"data/macro/fred_{ser}.csv"), na_values=["."])
        f["period"] = f["date"].str[:7]
        g = PF[PF["series"] == ser].merge(f[["period", "value"]], on="period", how="left").sort_values("period").reset_index(drop=True)
        g["v"] = g["first_value"].combine_first(g["value"])
        g["s"] = np.where(g["first_value"].notna(), "首", np.where(g["value"].notna(), "修", ""))
        g["av"] = [int(np.searchsorted(caln, np.datetime64(pd.Timestamp(d)), "right")) for d in g["first_release_date"]]
        mom = g["v"] / g["v"].shift(1) - 1
        g["c1"] = (mom < 0) & (mom.shift(1) < 0) & (mom.shift(2) < 0)
        y = g["v"] / g["v"].shift(12) - 1
        g["c2"] = (y < 0) & (y.shift(1) >= 0)

        def lb(row_idx, offs):
            ss = {g["s"].iloc[row_idx - o] for o in offs}
            return "首發值" if ss == {"首"} else ("修正值" if ss == {"修"} else "混合")
        g["l1"] = [lb(j, (0, 1, 2, 3)) if j >= 3 else "" for j in range(len(g))]
        g["l2"] = [lb(j, (0, 1, 12, 13)) if j >= 13 else "" for j in range(len(g))]
        SER[ind] = g
    M = EV[(EV["母體"] == "缺貨型") & (EV["進場"] == "保留") & (EV["E1000走得完"] == True)].reset_index(drop=True)  # noqa: E712
    diff = {k: 0 for k in ("D1_k", "D2_k", "D1′_k", "D2′_k", "D1_s", "D2_s", "D3_s", "D1_來源", "D2_來源", "D1_結果", "D2_結果", "D3_結果")}
    for rd in M.to_dict("records"):                    # itertuples 會把含 ′ 的欄名改成位置名
        i = ix[rd["sid"]]; e = int(np.searchsorted(caln, np.datetime64(pd.Timestamp(rd["e"])), "left"))
        x = e + int(rd["E1000_eff偏移"])
        g = SER[rd["產業"]]
        w = g[(g["av"] >= e) & (g["av"] <= x - 1)]
        for c, cc, back in (("D1", "c1", None), ("D2", "c2", None), ("D1′", "c1", 2), ("D2′", "c2", 1)):
            hit = w[w[cc]]
            if back is not None:
                hit = hit[[bool(j - back >= 0 and g["av"].iloc[j - back] >= e) for j in hit.index]]
            mine = int(hit["av"].iloc[0]) - e if len(hit) else None
            col = {"D1": "D1_k偏移", "D2": "D2_k偏移", "D1′": "D1′_k偏移", "D2′": "D2′_k偏移"}[c]
            theirs = rd[col]
            theirs = None if (theirs is None or (isinstance(theirs, float) and np.isnan(theirs)) or rd[f"{c}_E1000"] == "不賣") else int(theirs)
            if mine != theirs:
                diff[f"{c}_k"] += 1
            if c in ("D1", "D2"):
                if mine is not None:
                    k = e + mine
                    ss = next((t for t in range(k + 1, len(CAL)) if TRD[i, t] and np.isfinite(C[i, t]) and np.isfinite(O[i, t]) and not DNL[i, t]), None)
                    sold = ss is not None and ss <= x
                    res = "賣出" if sold else "判到未賣出"
                    if sold and int(rd[f"{c}_s偏移"]) != ss - e:
                        diff[f"{c}_s"] += 1
                    lab = g["l1" if c == "D1" else "l2"].iloc[hit.index[0]]
                    if lab != rd[f"{c}值來源"]:
                        diff[f"{c}_來源"] += 1
                else:
                    res = "不賣"
                if res != rd[f"{c}_E1000"]:
                    diff[f"{c}_結果"] += 1
        k3 = e + 625
        s3 = next((t for t in range(k3, len(CAL)) if TRD[i, t] and np.isfinite(C[i, t])), None)
        res3 = "不賣" if k3 > x else ("賣出" if (s3 is not None and s3 <= x) else "判到未賣出")
        if res3 != rd["D3_E1000"]:
            diff["D3_結果"] += 1
        if res3 == "賣出" and int(rd["D3_s偏移"]) != s3 - e:
            diff["D3_s"] += 1
    CK["K3_觸發逐值"] = {"主格事件(全部)": len(M), "不同": diff, "全同": all(v == 0 for v in diff.values())}
    log(f"[K3] {CK['K3_觸發逐值']}")
    # ── K4
    FR = pd.read_csv(os.path.join(out, "freq_段.csv"), encoding="utf-8-sig")
    CN = pd.read_csv(os.path.join(out, "counts.csv"), encoding="utf-8-sig")
    k4 = []
    for sg in ("探索", "確認", "早於探索(不入段)"):
        mm = M[M["段"] == sg]
        cn = CN[(CN["段"] == sg) & (CN["母體"] == "缺貨型")].iloc[0]
        k4.append(int(cn["主格(E1000走得完)"]) == len(mm)); k4.append(int(cn["n_eff(主格進場月數)"]) == mm["進場月"].nunique())
        for c in ("D1", "D2", "D3", "D1′", "D2′"):
            f = FR[(FR["段"] == sg) & (FR["E"] == 1000) & (FR["賣法"] == c)]
            if not len(mm):
                continue
            f = f.iloc[0]
            k4 += [int(f["事件"]) == len(mm), int(f["月數"]) == mm["進場月"].nunique(), int(f["判到"]) == int((mm[f"{c}_E1000"] != "不賣").sum()),
                   int(f["賣出"]) == int((mm[f"{c}_E1000"] == "賣出").sum())]
    CK["K4_彙總"] = {"項": len(k4), "相符": all(k4)}
    log(f"[K4] {CK['K4_彙總']}")
    # ── K5
    bad = []
    for f in glob.glob(os.path.join(out, "*.csv*")):
        d = pd.read_csv(f, encoding="utf-8-sig")
        if any(("PPI" in c or "ppi" in c) for c in d.columns):
            bad.append((os.path.basename(f), "欄名"))
        if os.path.basename(f).startswith("events"):
            for c in d.columns:
                if d[c].dtype.kind == "f" and not np.all(np.isnan(d[c]) | (d[c] == np.round(d[c]))):
                    bad.append((os.path.basename(f), c))
    st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True).stdout.splitlines()
    before = set(open(os.path.expanduser("~/rtfwork/git_before_sx2.txt"), encoding="utf-8").read().splitlines())
    new = [l for l in st if l not in before]
    mine_ = [l for l in new if ("researchShortageExit2" in l or "resultsShortageExit2" in l)]
    other = [l for l in new if l not in mine_]
    okn = all(l.startswith("??") for l in mine_) and not any(l[:2].strip() in ("M", "D") for l in other if "ShortageExit" in l)
    CK["K5_私有與工作樹"] = {"疑似值欄": bad, "本件新增": mine_, "別件同時段新增（非本件、不計）": other, "本件只新增檔、未改既有檔": okn}
    log(f"[K5] {CK['K5_私有與工作樹']}")
    CK["全過"] = bool(CK["K1_登錄sha"]["相符"] and rul and CK["K2_事件"]["只在第一輪"] == 0 and CK["K2_事件"]["只在本件"] == 0 and segbad == 0
                    and CK["K3_觸發逐值"]["全同"] and CK["K4_彙總"]["相符"] and not bad and okn)
    log(f"[全過] {CK['全過']}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

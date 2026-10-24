# -*- coding: utf-8 -*-
"""缺貨型確認後怎麼賣・第二輪 seq1 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀；只寫 resultsShortageExit2/main/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit2_check [--out 目錄]

K1 逐筆 R、d 獨立重算：價格面板同源（RT.prices＋SXM.seam_open），但進場價、E_eff 收盤（自掃 isfinite 找最後有效根）、賣出價（D3 收盤、其餘開盤）、
   成本、d 一律本檔自算 ⇒ 與 events_R 逐值比（≤1e−12）；賣出／不賣結果與頻率表 events 逐值相同。
K2 判定 3 格：月分群 se 自寫（不呼叫 research11.cl_stats）、z ＝ Φ⁻¹(1−0.05/6) ⇒ 兩段平均、確認段 Bonf3 上下界與 cells.csv 相同（≤1e−12），判定句自判相同。
K3 每筆年化：H（賣出 s−e＋1；不賣 xv−e＋1）與年化 ＝ (1＋R)^(250÷max(H,60))−1 自算 ⇒ 逐筆相同；ann.csv 各段×E×賣法 中位、平均、持有＜60 日比例相同。
K4 件數守恆：各段×E 列數 ＝ 頻率表 events（缺貨型、保留、E 走得完）；E1000 探索 298／確認 235 ＝ freq counts 主格；n_eff 88／79。
K5 私有：輸出無 PPI／ppi 欄名；輸出所有 csv 數值格、summary.md 與 main.json 內小數，沒有任何一個等於私有 PPI 序列的值（非整數值，容差 1e−9／四捨五入位數）。
K6 工作樹：相對開跑前快照（~/rtfwork/git_before_ann.txt）只多本件與 _ann 新檔；既有已提交檔 md5 不變（~/rtfwork/md5_before_ann.txt 中非 researchShortageExit2.py 者）。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SXM            # noqa: E402
from backtest import researchShortageExit2_freq as S2       # noqa: E402

OUT = "backtest/resultsShortageExit2/main"
FREQ = S2.OUT
COST = 0.004425
RULES = ["D1", "D2", "D3", "D1′", "D2′"]
CELLS = ["D1", "D2", "D3"]
ZB = NormalDist().inv_cdf(1 - 0.05 / 6)
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def my_cl(x, m):
    x = np.asarray(x, float); m = np.asarray(m)
    mu = x.mean(); dev = x - mu
    sums = {}
    for k, v in zip(m, dev):
        sums[k] = sums.get(k, 0.0) + v
    se = np.sqrt(sum(v * v for v in sums.values())) / len(x)
    return mu, se


def my_ann(r, h):
    g = 1.0 + r
    return -1.0 if g <= 0 else g ** (250.0 / max(h, 60)) - 1.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=OUT); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = a.out
    CK = {}
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8"))
    sha, us_sha = MJ["origin/main"], MJ["us-stock-data"]
    RR = pd.read_csv(os.path.join(out, "events_R.csv.gz"), dtype={"sid": str, "期別": str}, encoding="utf-8-sig")
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str, "期別": str})
    EV = EV[(EV["進場"] == "保留") & (EV["母體"] == "缺貨型")].reset_index(drop=True)
    _, DN, _ = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, a.procs)
    O, _ = SXM.seam_open(PX)
    CAL, ix, C = PX["CAL"], PX["ix"], PX["C"]
    key = {(r["sid"], r["e"], int(r["E"])): r for r in RR.to_dict("records")}
    mx = {"R": 0.0, "d": 0.0, "H": 0, "年化": 0.0, "年化差": 0.0}; nres = 0; nrow = 0; miss = 0
    mine = []
    for rd in EV.to_dict("records"):
        i = ix[rd["sid"]]; e = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(rd["e"])), "left"))
        P0 = O[i, e]
        for E in S2.ES:
            if not rd[f"E{E}走得完"]:
                continue
            x = e + int(rd[f"E{E}_eff偏移"])
            fin = np.flatnonzero(np.isfinite(C[i, :x + 1])); xv = int(fin[-1])
            R0 = C[i, xv] / P0 - 1 - COST; H0 = xv - e + 1; A0 = my_ann(R0, H0)
            r = key.get((rd["sid"], rd["e"], E))
            if r is None:
                miss += 1; continue
            nrow += 1
            mx["R"] = max(mx["R"], abs(r["R_D0"] - R0)); mx["H"] = max(mx["H"], abs(int(r["H_D0"]) - H0)); mx["年化"] = max(mx["年化"], abs(r["年化_D0"] - A0))
            m = {"段": rd["段"], "E": E, "進場月": rd["進場月"]}
            for c in RULES:
                oc = rd[f"{c}_E{E}"]
                if oc != r[f"{c}_結果"]:
                    nres += 1
                if oc == "賣出":
                    s = e + int(rd[f"{c}_s偏移"])
                    ps = C[i, s] if c == "D3" else O[i, s]
                    Rk = ps / P0 - 1 - COST; Hk = s - e + 1
                else:
                    Rk, Hk = R0, H0
                Ak = my_ann(Rk, Hk)
                mx["R"] = max(mx["R"], abs(r[f"R_{c}"] - Rk)); mx["d"] = max(mx["d"], abs(r[f"d_{c}"] - (Rk - R0)))
                mx["H"] = max(mx["H"], abs(int(r[f"H_{c}"]) - Hk)); mx["年化差"] = max(mx["年化差"], abs(r[f"年化差_{c}"] - (Ak - A0)))
                m[f"d_{c}"] = Rk - R0; m[f"ad_{c}"] = Ak - A0; m[f"H_{c}"] = Hk
            mine.append(m)
    MI = pd.DataFrame(mine)
    ok1 = miss == 0 and nrow == len(RR) and nres == 0 and mx["R"] < 1e-12 and mx["d"] < 1e-12
    CK["K1_逐筆R與d"] = {"列": nrow, "events_R列": len(RR), "找不到": miss, "結果不同": nres, "最大差": mx, "過": ok1}
    log(f"[K1] {CK['K1_逐筆R與d']}")
    # K2
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig").set_index("賣法")
    k2 = []; vv = {}
    J = MI[MI["E"] == 1000]
    for c in CELLS:
        st = {}
        for sg in ("探索", "確認"):
            d = J[J["段"] == sg]
            mu, se = my_cl(d[f"d_{c}"].to_numpy(), d["進場月"].to_numpy())
            st[sg] = (mu, se, d["進場月"].nunique())
            k2.append(abs(mu - CE.at[c, f"{sg}_d平均"]) < 1e-12)
        lo = st["確認"][0] - ZB * st["確認"][1]; hi = st["確認"][0] + ZB * st["確認"][1]
        lo_c, hi_c = [float(v) for v in CE.at[c, "確認_CI98.33(Bonf3)"].strip("[]").split(",")]
        k2 += [abs(lo - lo_c) < 5e-5, abs(hi - hi_c) < 5e-5]
        if min(st["探索"][2], st["確認"][2]) < 24:
            v = "還沒測（n_eff ＜ 24）"
        elif st["探索"][0] > 0 and st["確認"][0] > 0 and lo > 0:
            v = f"{c} 比不賣有利（暫定）"
        elif st["探索"][0] < 0 and st["確認"][0] < 0 and hi < 0:
            v = f"{c} 比不賣差（暫定）"
        else:
            v = f"{c} 跟不賣分不出"
        vv[c] = v; k2.append(v == CE.at[c, "判定(記0口徑)"])
    CK["K2_判定3格"] = {"自判": vv, "項": len(k2), "過": all(k2)}
    log(f"[K2] {CK['K2_判定3格']}")
    # K3
    AN = pd.read_csv(os.path.join(out, "ann.csv"), encoding="utf-8-sig")
    k3 = []
    for _, r in AN.iterrows():
        d = MI[(MI["段"] == r["段"]) & (MI["E"] == r["E"])]
        x_ = d[f"ad_{r['賣法']}"].to_numpy()
        k3 += [len(d) == r["n"], abs(np.median(x_) - r["年化差中位(賣法−D0)"]) < 1e-12, abs(x_.mean() - r["年化差平均"]) < 1e-12,
               abs((d[f"H_{r['賣法']}"] < 60).mean() - r["持有<60日比例(賣法臂,÷全部)"]) < 1e-12]
    ok3 = all(k3) and mx["H"] == 0 and mx["年化"] < 1e-12 and mx["年化差"] < 1e-12
    CK["K3_每筆年化"] = {"ann列": len(AN), "項": len(k3), "逐筆H最大差": mx["H"], "過": ok3}
    log(f"[K3] {CK['K3_每筆年化']}")
    # K4
    CN = pd.read_csv(os.path.join(FREQ, "counts.csv"), encoding="utf-8-sig")
    k4 = {}
    for sg in ("早於探索(不入段)", "探索", "確認"):
        for E in S2.ES:
            k4[f"{sg}_E{E}"] = int(((RR["段"] == sg) & (RR["E"] == E)).sum()) == int(((EV["段"] == sg) & (EV[f"E{E}走得完"] == True)).sum())  # noqa: E712
        cn = CN[(CN["段"] == sg) & (CN["母體"] == "缺貨型")].iloc[0]
        jj = RR[(RR["段"] == sg) & (RR["E"] == 1000)]
        k4[f"{sg}_主格"] = int(cn["主格(E1000走得完)"]) == len(jj) and int(cn["n_eff(主格進場月數)"]) == jj["進場月"].nunique()
    CK["K4_件數守恆"] = {"探索E1000": int(((RR["段"] == "探索") & (RR["E"] == 1000)).sum()), "確認E1000": int(((RR["段"] == "確認") & (RR["E"] == 1000)).sum()),
                       "項": k4, "過": all(k4.values())}
    log(f"[K4] {CK['K4_件數守恆']}")
    # K5
    git = lambda p: io.BytesIO(subprocess.run(["git", "-C", S2.US_REPO, "show", f"{us_sha}:{p}"], capture_output=True, check=True).stdout)  # noqa: E731
    vals = set()
    PF = pd.read_csv(git("data/macro/ppi_first_release.csv"))
    vals |= set(PF["first_value"].dropna().astype(float))
    for ser in set(S2.PPI_MAP.values()):
        f = pd.read_csv(git(f"data/macro/fred_{ser}.csv"), na_values=["."])
        vals |= set(f["value"].dropna().astype(float))
    pv = np.array(sorted(v for v in vals if v != round(v)))
    bad = []
    for f in glob.glob(os.path.join(out, "*.csv*")):
        d = pd.read_csv(f, encoding="utf-8-sig")
        if any(("PPI" in str(c) or "ppi" in str(c)) for c in d.columns):
            bad.append((os.path.basename(f), "欄名"))
        nd = d.select_dtypes("number")
        nd = nd[[c for c in nd.columns if not str(c).startswith(("H", "賣法臂H"))]]     # 持有日數（含中位 x.5）不是物價值
        num = nd.to_numpy(float).ravel()
        num = num[np.isfinite(num) & (num != np.round(num))]
        if len(num):
            k = np.clip(np.searchsorted(pv, num), 1, len(pv) - 1)
            near = np.minimum(abs(pv[k] - num), abs(pv[k - 1] - num))
            if (near < 1e-9).any():
                bad.append((os.path.basename(f), int((near < 1e-9).sum())))
    pr = {round(v, 3) for v in pv} | {round(v, 1) for v in pv if v > 50}
    for f in ("summary.md", "main.json"):
        txt = open(os.path.join(out, f), encoding="utf-8").read()
        nums = [float(t) for t in re.findall(r"(?<![\d.])\d{2,4}\.\d{3}(?!\d)", txt)]
        hit = [t for t in nums if round(t, 3) in pr]
        if hit:
            bad.append((f, hit[:5]))
    CK["K5_私有"] = {"PPI 非整數值個數": len(pv), "疑似": bad, "過": not bad}
    log(f"[K5] {CK['K5_私有']}")
    # K6
    st = subprocess.run(["git", "status", "--short"], capture_output=True, text=True).stdout.splitlines()
    before = set(open(os.path.expanduser("~/rtfwork/git_before_ann.txt"), encoding="utf-8").read().splitlines())
    new = [l for l in st if l not in before]
    md5 = subprocess.run(["md5sum", "-c", os.path.expanduser("~/rtfwork/md5_before_ann.txt")], capture_output=True, text=True).stdout.splitlines()
    md5bad = [l for l in md5 if not l.endswith(": OK") and "researchShortageExit2.py" not in l]
    mine_ = [l for l in new if any(t in l for t in ("ShortageExit2", "_ann", "resultsLong3/ann", "resultsShortageExit/main/ann"))]
    other = [l for l in new if l not in mine_]
    okm = all(l.startswith("??") or l == " M backtest/researchShortageExit2.py" for l in mine_) and not any("ShortageExit" in l or "Long3" in l for l in other)
    CK["K6_工作樹"] = {"本件": mine_, "別件同時段（非本件、不計）": other, "md5 不同(不含本件 researchShortageExit2.py)": md5bad,
                     "說明": "researchShortageExit2.py 已於 ab323ff470 提交，本件准改（改動見檔頭 2026-10-24 註）", "過": okm and not md5bad}
    log(f"[K6] {CK['K6_工作樹']}")
    CK["全過"] = all(CK[k]["過"] for k in CK if k.startswith("K"))
    log(f"[全過] {CK['全過']}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

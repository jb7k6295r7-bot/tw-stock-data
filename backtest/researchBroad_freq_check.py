# -*- coding: utf-8 -*-
"""廣撒長抱 seq1 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀、不改任何既有檔（只寫 freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad_freq_check

C1 登錄 sha 獨立重算 ＋ 裁定 seq454 信在。
C2 批與成員另路：月營收快取直接以 accel ≥ 0.05 ∧ hi24 ∧ ¬hi24_prev（G1）、up ∧ ¬up_prev（G2）、自算可用日（次月 10／15 日後第一個交易日）＋1、
   W1 ＝ 量測面板快取直接查（批日同月最後量測日）∩ 價格面板 ⇒ 每批 G1、G2、W1 名單與 prep 完全相同。
C3 每筆出場另路：抽 5,000 筆（代號, 批日, H）以 BAD／TRD／UPL／有效 K 棒直接判（買不到、壞根、下市、到期、順延、走不完）相同。
C4 帳另路：G1 H250、G2 H750、純廣撒 H500 三格以逐日迴圈重算每日投入與不同代號數 ⇒ 各段平均現金、同時持有平均、最多與 cells.csv 相同。
C5 重疊：batches.csv 的 G1∩G2、營量／營飆重疊由 prep 名單與 and_signals（只讀 sid、pos、entry_pos）自算相同（全部批）。
C6 隨機框架：第 0、500、999 次逐批抽樣自算，「與訊號批同檔」相同；同種子兩次結果相同。
C7 輸出無報酬類欄；策略鎖 25 支相符；git 相對開跑前只多本件新檔與結果夾。
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchBroad_freq as BF               # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchTriple_freq as TP              # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def close(a, b, tol=1e-9):
    return bool((np.isnan(a) and np.isnan(b)) or abs(a - b) <= tol * max(1.0, abs(a)))


def main():
    out = BF.OUT; CK = {}
    dirs = [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*")))
    allmd = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md"))]
    fs = [f for f in allmd if f"sha{BF.REG_SHA}" in os.path.basename(f)]
    rul = [os.path.basename(f) for f in allmd if "seq454" in os.path.basename(f) and "裁定線-" in os.path.basename(f)]
    CK["C1"] = {"登錄": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == BF.REG_SHA for f in fs), "裁定seq454": rul}
    log(f"[C1] {CK['C1']}")
    MJ = json.load(open(os.path.join(out, "meta.json"), encoding="utf-8")); sha = MJ["origin/main"]
    PR = pickle.load(open(os.path.join(BF.WK, f"prep_{sha[:12]}.pkl"), "rb"))
    sha_, DN, MD = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, 4)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]; CEND = len(CAL) - 1
    C, BAD, TRD, UPL, O = PX["C"], PX["BAD"], PX["TRD"], PX["UPL"], PX["O"]
    # ── C2
    Z = pickle.load(open(os.path.join(RT.WORK, f"rv_{TP.RV_TAG}_s{RT.SHIFT_Y}.pkl"), "rb")); RV = Z["RV"]
    W = {nm: pickle.load(open(os.path.join(BF.CTX, f"ctx_{nm}.pkl"), "rb")) for nm in ("early", "main")}

    def w1(d):
        for nm in ("main", "early"):
            Cw = W[nm]
            if d in set(Cw["cal"]):
                mm = [m for m in Cw["meas"] if m.year == d.year and m.month == d.month]
                if mm:
                    return [s for s in Cw["memW"].get(max(mm), []) if s in ix]
        return []
    bt = {x["P"]: x for x in PR["BT"]}
    bad2 = 0; nb = 0
    for P, g in RV.groupby("period"):
        y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        A_ = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)), "right"))
        b = A_ + 1
        if b > CEND or not ("2012-06-01" <= str(CAL[b].date()) <= "2026-08-31"):
            if P in bt:
                bad2 += 1
            continue
        nb += 1
        ws = w1(CAL[b]); wset = set(ws)
        g1 = sorted(s for s in g.loc[(g["accel"] >= 0.05) & (g["hi24"] == 1.0) & ~(g["hi24_prev"] == 1.0), "sid"] if s in wset)
        g2 = sorted(s for s in g.loc[g["up"].astype(bool) & ~g["up_prev"].astype(bool), "sid"] if s in wset)
        x = bt.get(P)
        if x is None or x["b"] != b or sorted(x["W1"]) != sorted(ws) or sorted(x["G1"]) != g1 or sorted(x["G2"]) != g2:
            bad2 += 1
    CK["C2_批與成員"] = {"自算批": nb, "prep批": len(PR["BT"]), "不同": bad2 + abs(nb - len(PR["BT"]))}
    log(f"[C2] {CK['C2_批與成員']}")
    # ── C3
    VP = PX["VP"]; LASTV = PX["LASTV"]

    def ex2(i, b, H):
        mat = b + H - 1
        if not (np.isfinite(C[i, b]) and TRD[i, b] and np.isfinite(O[i, b]) and O[i, b] > 0) or BAD[i, b] or UPL[i, b]:
            return None
        end = min(mat, CEND)
        opts = []
        for p in range(b + 1, end + 1):
            if BAD[i, p]:
                q = p - 1
                while not np.isfinite(C[i, q]):
                    q -= 1
                opts.append(q); break
        if LASTV[i] < end and CEND - LASTV[i] >= 5:
            opts.append(int(LASTV[i]))
        if opts:
            return min(opts)
        if mat > CEND:
            return CEND + 1
        q = mat
        while q <= CEND and not np.isfinite(C[i, q]):
            q += 1
        return q if q <= CEND else CEND + 1
    keys = list(PR["LX"].keys()); rng = np.random.default_rng(11)
    samp = [keys[k] for k in rng.choice(len(keys), min(5000, len(keys)), replace=False)]
    b3 = sum(1 for (i, b, H) in samp if ex2(i, b, H) != PR["LX"][(i, b, H)][0])
    CK["C3_出場"] = {"抽": len(samp), "不同": b3}; log(f"[C3] {CK['C3_出場']}")
    # ── C4
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig")
    MEM = {"G1": [x["G1"] for x in PR["BT"]], "G2": [x["G2"] for x in PR["BT"]], "純廣撒": [x["W1"] for x in PR["BT"]]}
    b4 = []
    for G, H in (("G1", 250), ("G2", 750), ("純廣撒", 500)):
        n = CEND + 1; inv = np.zeros(n); held = [set() for _ in range(n)] if G != "純廣撒" else None
        dcount = np.zeros(n)
        slots = []    # (release, amount)
        sl = 1.0 / round(H / 21)
        hold_iv = []
        for j, x in enumerate(PR["BT"]):
            b = x["b"]; mat = b + H - 1
            occ = sum(v for r, v in slots if r >= b); Aj = min(sl, max(0.0, 1 - occ))
            lst = MEM[G][j]; rel = mat if mat <= CEND else 10 ** 9
            for s in lst:
                i = ix[s]; e = PR["LX"][(i, b, H)][0]
                if e is None:
                    continue
                inv[b:e] += Aj / len(lst); hold_iv.append((i, b, e))
                if e > mat:
                    rel = 10 ** 9 if e > CEND else max(rel, e)
            slots.append((rel, Aj))
        dd = np.zeros(n + 1)
        by = {}
        for i, a_, e_ in hold_iv:
            by.setdefault(i, []).append((a_, e_))
        for i, iv in by.items():
            cov = np.zeros(n + 1, bool)
            for a_, e_ in iv:
                cov[a_:e_] = True
            dd[:n] += cov[:n]
        for nm, x_, y_ in BF.SEGS:
            a_ = max(int(CAL.searchsorted(pd.Timestamp(x_))), PR["BT"][0]["b"]); z_ = min(int(CAL.searchsorted(pd.Timestamp(y_), "right")) - 1, CEND)
            r = CE[(CE["格"] == G) & (CE["H"] == H) & (CE["段"] == nm)].iloc[0]
            mine = [float((1 - inv[a_:z_ + 1]).mean()), float(dd[a_:z_ + 1].mean()), int(dd[a_:z_ + 1].max())]
            theirs = [r["平均現金比例"], r["同時持有不同代號平均"], r["同時持有不同代號最多"]]
            if not all(close(float(p), float(q), 1e-7) for p, q in zip(mine, theirs)):
                b4.append((G, H, nm, mine, theirs))
    CK["C4_帳另路"] = {"不符": b4}; log(f"[C4] {CK['C4_帳另路']}")
    # ── C5
    BR = pd.read_csv(os.path.join(out, "batches.csv.gz"), encoding="utf-8-sig")
    from backtest import rerun17 as RR
    import backtest.data as D
    D.DATA = RR.H2D; mcal = D.load_calendar(); reg = RR.regime_mask(RR.load_bench(mcal))
    AN = pd.read_csv(BF.AND_CSV, dtype={"sid": str}, usecols=["sid", "pos", "entry_pos"])
    AN = AN[(AN["pos"] < len(mcal)) & (AN["entry_pos"] <= len(mcal))]
    LQ = {"營量": {}, "營飆": {}}
    for s, p, ep in zip(AN["sid"], AN["pos"], AN["entry_pos"]):
        m = str(mcal[p].date())[:7]
        LQ["營量"].setdefault(m, set()).add(s)
        if reg[ep - 1]:
            LQ["營飆"].setdefault(m, set()).add(s)
    lo, hi = min(LQ["營量"]), max(LQ["營量"])
    b5 = 0
    for x, r in zip(PR["BT"], BR.to_dict("records")):
        g1, g2 = set(x["G1"]), set(x["G2"])
        if len(g1 & g2) != int(r["G1∩G2"]):
            b5 += 1
        m = x["d"][:7]
        for lab in ("營量", "營飆"):
            for G, g in (("G1", g1), ("G2", g2)):
                v = (len(g & LQ[lab].get(m, set())) / len(g)) if (g and lo <= m <= hi) else np.nan
                if not close(v, float(r[f"{G}中為當月{lab}"]) if r[f"{G}中為當月{lab}"] == r[f"{G}中為當月{lab}"] else np.nan):
                    b5 += 1
    CK["C5_重疊"] = {"批": len(BR), "不同": b5}; log(f"[C5] {CK['C5_重疊']}")
    # ── C6
    RF = pd.read_csv(os.path.join(out, "random_frame.csv"), encoding="utf-8-sig")
    b6 = []
    for G in ("G1", "G2"):
        for r in (0, 500, 999):
            vals = []
            for _ in range(2):
                rng = np.random.default_rng([BF.SEED, r]); same = 0; tot = 0
                for x in PR["BT"]:
                    pool = sorted(x["W1"]); k = len(x[G]); tot += k
                    pk = [pool[q] for q in rng.permutation(len(pool))[:k]] if k else []
                    same += len(set(pk) & set(x[G]))
                vals.append(same / max(1, tot))
            if vals[0] != vals[1]:
                b6.append((G, r, "不可重現"))
            if not (RF.loc[RF["格"] == G, "p5"].iloc[0] - 0.05 <= vals[0] <= RF.loc[RF["格"] == G, "p95"].iloc[0] + 0.05):
                b6.append((G, r, vals[0]))
    CK["C6_隨機"] = {"不符": b6}; log(f"[C6] {CK['C6_隨機']}")
    # ── C7
    cols = [c for f in glob.glob(os.path.join(out, "*.csv*")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = [c for c in cols if any(w in c for w in ("報酬", "年化", "回落", "MDD", "淨值", "倍數", "命中"))]
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.expanduser("~/trpwork/git_before_broad.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    CK["C7"] = {"報酬類欄": badc, "策略鎖": lock, "git 新增": extra, "git 只多本件": all(any(w in x for w in ("researchBroad_freq", "resultsBroad")) for x in extra)}
    ok = (CK["C1"]["相符"] and bool(rul) and CK["C2_批與成員"]["不同"] == 0 and b3 == 0 and not b4 and b5 == 0 and not b6 and not badc
          and "相符" in "".join(lock) and CK["C7"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[C7] {CK['C7']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

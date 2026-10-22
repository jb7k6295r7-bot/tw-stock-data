# -*- coding: utf-8 -*-
"""researchIndRevHold（產業營收加速改長抱 seq2 正式跑）對帳——回測線計算子代理，2026-10-23。獨立寫法，0 不同才算過。
 C1 登錄 sha（seq2 800ad3a4bcacd7da）去 pw1 行 sha256 前 16 碼相符
 C2 乾跑（價格全 1、成本 0）＝ 頻率表：dry.json 三個版本（主 H2D、早年 eotc、早年 reduce_v2）持股數 0 不同、現金差 ≤ 1e−6（頻率表存 float32）、權益恆 1
 C3 大盤報酬指數：自己 git show market_tri.csv、自己 ffill 到日曆、自己寫 CAGR／MDD（245 日／年）⇒ 各段與 meta 基準相對差 ≤ 1e−12；
    0050 主段探索／確認 ＝ 前件 resultsIndRev/prereg/meta.json 的 0050（逐位元）
 C4 逐日迴圈重算（價格版；獨立寫法：自由現金＋各批帳戶、開盤買、收盤賣、批全部賣完才回收）：挑中格（主、早年）＋ 另抽 2 格（default_rng(20261023)）
    ⇒ 與 RH.sim_book 權益相對差 ≤ 1e−9；挑中格另對 eq.npz
 C5 挑格重現：自己由 cells.csv 依登錄規則（退化、合格優先、比值、平手順）重挑 ⇒ 與 meta 相同；標籤自己重算 ⇒ 0 不同
 C6 隨機重現：r ＝ 0、1、500 重跑（RH._rand_job）⇒ 與 random.csv.gz 逐欄相同
 C7 策略鎖相符（25 支）
輸出 backtest/resultsIndRevHold/main/check.json
"""
from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import subprocess
import sys
from argparse import Namespace

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndRevHold as RH               # noqa: E402
from backtest import researchIndRevHold_freq as FQ          # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchIndRevLag_prereg as LAGP       # noqa: E402

OUT = RH.OUT


def my_sha(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def my_stats(x, a, z):
    seg = np.asarray(x[a:z + 1], float); yrs = (z + 1 - a) / 245
    c = (seg[-1] / seg[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(seg); m = float(((seg - pk) / pk).min())
    return c, m


def loop_book(Wd, BL, picks, K, S, H):
    """C4：逐日、獨立。"""
    cal = Wd["cal"]; T = Wd["T"]; n = len(cal); FL = Wd["FL"]; SFd = Wd["SF"]; PX = Wd["PX"]
    nsl = int(round(H / 21)); bd = {b: j for j, (b, _) in enumerate(BL)}
    F = 1.0; eq = np.ones(n); bts = []
    isbad = {}; nxt = {}

    def prep(s):
        if s not in isbad:
            f = FL[s]; ib = np.zeros(n + 1, bool); ib[f["bad"]] = True; isbad[s] = ib
            tr = np.flatnonzero(f["trd"]); k = np.searchsorted(tr, np.arange(n), "right")
            nxt[s] = np.where(k < len(tr), tr[np.minimum(k, len(tr) - 1)], n)
    for t in range(BL[0][0], T + 1):
        if t in bd:
            j = bd[t]; b = t
            A = min(eq[b - 1] / nsl, max(F, 0.0)); F -= A
            bt = {"mat": b + H - 1, "cash": A, "lots": [], "rel": False}
            mem = Wd["MEM"][b][0]
            for i in picks[j]:
                lst = mem.get(i, []); lst = lst[:20] if S == "S1" else lst
                if not lst:
                    continue
                per = A / K / len(lst)
                for s in lst:
                    f = FL.get(s)
                    if f is None:
                        continue
                    prep(s)
                    if not f["trd"][b] or not Wd["okopen"][s][b] or f["up"][b] or isbad[s][b]:
                        continue
                    bt["lots"].append({"s": s, "u": per / PX[s]["o"][b], "amt": per, "on": True})
                    bt["cash"] -= per
            bts.append(bt)
        for bt in bts:
            if bt["rel"]:
                continue
            end = min(bt["mat"], T)
            for L in bt["lots"]:
                if not L["on"]:
                    continue
                s = L["s"]; f = FL[s]; sold = False
                if t <= end:
                    Lst = SFd.get(s)
                    if Lst is not None and t == Lst + 1:
                        sold = True
                    elif f["trd"][t]:
                        q = int(nxt[s][t])
                        if q <= end and isbad[s][q]:
                            sold = True
                if not sold and t >= bt["mat"] and f["trd"][t] and not f["dc"][t]:
                    sold = True
                if sold:
                    L["on"] = False; bt["cash"] += L["u"] * PX[s]["c"][t] - L["amt"] * RH.COST
            if t >= bt["mat"] and not any(L["on"] for L in bt["lots"]):
                bt["rel"] = True; F += bt["cash"]
        eq[t] = F + sum(bt["cash"] + sum(L["u"] * PX[L["s"]]["c"][t] for L in bt["lots"] if L["on"]) for bt in bts if not bt["rel"])
    return eq


def lock_ok():
    p = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    out = (p.stdout + p.stderr).strip().splitlines()
    return ("相符" in "".join(out[-3:])) and p.returncode == 0, out[-3:]


def main():
    CK = {}
    fs = []
    for d in ["/mnt/c/SynologyDrive/跨線信箱"] + sorted(glob.glob("/mnt/c/SynologyDrive/跨線信箱/_封存-*")):
        fs += [f for f in glob.glob(os.path.join(d, "*.md")) if "sha800ad3a4bcacd7da" in os.path.basename(f)]
    CK["C1_登錄sha"] = {"檔數": len(fs), "相符": bool(fs) and all(my_sha(f) == "800ad3a4bcacd7da" for f in fs)}
    dj = json.load(open(os.path.join(OUT, "dry.json"), encoding="utf-8"))
    CK["C2_乾跑＝頻率表"] = {k: v for k, v in dj.items() if k != "判讀"}
    c2 = all(v["持股數不同日數（合計）"] == 0 and v["現金最大差"] <= 1e-6 and v["權益偏離1最大"] == 0 for k, v in dj.items() if k != "判讀")
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    sha = META["main"]
    a = Namespace(procs=4, sha=sha, reps=0)
    RH.G["sha"] = sha
    LAGP.setup(a, sha); FQ.install_A(sha)
    raw = subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout
    tri = pd.read_csv(io.BytesIO(raw)); tri["date"] = pd.to_datetime(tri["date"])
    C3 = []; C4 = []
    TM = pd.read_csv(os.path.join(OUT, "cells.csv"))
    ch = META["挑格"]["挑中參數"]
    eqz = np.load(os.path.join(OUT, "eq.npz"))
    rng = np.random.default_rng(20261023)
    cells = [(A, K, S, H) for A in RH.AS for K in RH.KS for S in RH.SS for H in RH.HS]
    extra = [cells[int(k)] for k in rng.choice(len(cells), 2, replace=False)]
    for world in ("main", "early"):
        Wd = RH.prep(world, a)
        cal = Wd["cal"]
        s = tri.drop_duplicates("date").set_index("date")["close"]
        mine = []
        for d in cal:
            v = s[s.index <= d]
            mine.append(float(v.iloc[-1]))
        mine = np.array(mine)
        for sg, (x0, x1) in FQ.SEGS[world].items():
            a_ = int(cal.searchsorted(pd.Timestamp(x0))); z_ = min(int(cal.searchsorted(pd.Timestamp(x1), "right") - 1), Wd["T"])
            c, m = my_stats(mine, a_, z_)
            ref = META["基準"][world][sg]["大盤"]
            C3.append({"段": sg, "年化(自算/主)": [c, ref[0]], "回落(自算/主)": [m, ref[1]], "過": abs(c - ref[0]) <= 1e-12 * max(1, abs(ref[0])) and abs(m - ref[1]) <= 1e-12})
        BL = Wd["BL"]["主讀法"]
        for (A, K, S, H) in [(ch["A"], ch["K"], ch["S"], ch["H"])] + extra:
            e1 = loop_book(Wd, BL, Wd["PK"]["主讀法"][(A, K)], K, S, H)
            e2 = RH.sim_book(Wd, BL, Wd["PK"]["主讀法"][(A, K)], K, S, H)["eq"]
            t0 = BL[0][0]; T = Wd["T"]
            d = float(np.max(np.abs(e1[t0:T + 1] / e2[t0:T + 1] - 1)))
            r = {"世界": world, "格": f"{A}|K{K}|{S}|H{H}", "權益最大相對差": d, "過": d <= 1e-9}
            if (A, K, S, H) == (ch["A"], ch["K"], ch["S"], ch["H"]):
                r["對eq.npz"] = bool(np.array_equal(e2, eqz[world]))
                r["過"] = r["過"] and r["對eq.npz"]
            C4.append(r); print(r, flush=True)
        RH.W.pop(world, None)
    pm = json.load(open(os.path.join(PRE.OUT, "meta.json"), encoding="utf-8"))["0050"]
    b0 = META["基準"]["main"]
    c3b = all(repr(float(b0[sg]["0050"][k])) == repr(float(pm[sg][nm])) for sg in ("探索", "確認") for k, nm in ((0, "年化"), (1, "回落")))
    CK["C3_大盤報酬指數"] = C3; CK["C3_0050對前件逐位元"] = c3b
    CK["C4_逐日重算"] = C4
    # C5
    ex = TM[TM["段"] == "探索"].copy()
    ex["deg"] = (ex["平均持股"] < 5) | (ex["平均現金"] > 0.30)
    cand = ex[~ex["deg"]]
    lab = lambda c, m, c0, m0: ("合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格"))
    relab = [lab(c, m, c0, m0) for c, m, c0, m0 in zip(TM["年化"], TM["回落"], TM["大盤年化"], TM["大盤回落"])]
    nlab = int(sum(1 for x, y in zip(relab, TM["標籤"]) if x != y))
    pool_ = cand[cand["標籤"] == "合格"] if (cand["標籤"] == "合格").any() else cand
    order = {**{v: i for i, v in enumerate(RH.AS)}}
    best = sorted(pool_.itertuples(), key=lambda r: (-r.比值, -r.年化, RH.AS.index(r.A), RH.KS.index(r.K), RH.HS.index(r.H), RH.SS.index(r.S)))[0]
    mych = {"A": best.A, "K": int(best.K), "S": best.S, "H": int(best.H)}
    CK["C5_挑格重現"] = {"自挑": mych, "主": ch, "標籤不同": nlab, "過": mych == ch and nlab == 0}
    # C6
    RD = pd.read_csv(os.path.join(OUT, "random.csv.gz"))
    RH.G["ch"] = ch
    c6 = []
    for world in ("main", "early"):
        Wd = RH.prep(world, a)
        Wd["NAMES"] = [PRE.ranked("pit", ch["A"], M, "names") for b, M in Wd["BL"]["主讀法"]]
        for r in (0, 1, 500):
            row = RH._rand_job((world, r, r + 1))[0]
            ref = RD[(RD["世界"] == world) & (RD["r"] == r)].iloc[0]
            diff = max(abs(float(row[k]) - float(ref[k])) / max(abs(float(ref[k])), 1e-12) for k in row if k not in ("世界", "r") and np.isfinite(float(ref[k])))
            c6.append({"世界": world, "r": r, "最大相對差": diff, "過": diff <= 1e-6})
        RH.W.pop(world, None)
    CK["C6_隨機重現"] = c6
    CK["C6_註"] = "random.csv.gz 以 %.8g 存 ⇒ 門檻 1e−6"
    CK["C7_策略鎖"] = lock_ok()
    CK["全過"] = bool(CK["C1_登錄sha"]["相符"] and c2 and all(x["過"] for x in C3) and c3b and all(x["過"] for x in C4) and CK["C5_挑格重現"]["過"]
                    and all(x["過"] for x in c6) and CK["C7_策略鎖"][0])
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("全過" if CK["全過"] else "⛔ 有不符", json.dumps({k: v for k, v in CK.items() if k in ("C1_登錄sha", "C3_0050對前件逐位元", "C5_挑格重現", "C6_隨機重現", "C7_策略鎖")},
                                                    ensure_ascii=False, default=str))
    print(json.dumps(C3, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

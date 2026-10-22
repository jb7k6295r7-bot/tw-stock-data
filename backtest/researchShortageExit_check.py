# -*- coding: utf-8 -*-
"""缺貨型持股確認後怎麼賣 seq1 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾（只寫 main/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_check

K1 登錄 sha 獨立重算 ＋ 裁定 seq448 信在。
K2 頻率表重建逐字相同（main.json）；events_R（事件, E）集合 ＝ freq/events 中 e 可進場 ∧ E 走得完。
K3 抽 500 列（E 不限）另一條路重算：接縫倍數改以「出場那天」的合併收盤 ÷ 主世界面板收盤取（不同日取、應相同）、E_eff 以 pandas 自找、
   賣出價直接取 freq 的 s 偏移 ⇒ R_C0、各賣法 R、d 逐值相同（相對 1e−9）。
K4 判定 6 格：自寫月分群 se（不呼叫 research11）、z ＝ Φ⁻¹(1 − 0.05/12) ⇒ 平均、CI、判定字串逐格相同；desc.csv E250 缺貨型／一般股 平均自算相同。
K5 輸出：策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔與 main 結果夾。
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pickle
import subprocess
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchShortageExit as SM             # noqa: E402
from backtest import researchShortageExit_freq as SX        # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def mail(pat):
    return [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if pat in os.path.basename(f)]


def clse(x, m):
    x = np.asarray(x, float); mu = x.mean()
    g = pd.Series(x - mu).groupby(np.asarray(m)).sum().to_numpy()
    return mu, float(np.sqrt((g ** 2).sum()) / len(x))


def main():
    out = SM.OUT; CK = {}
    fs = mail(f"sha{SX.REG_SHA}"); rul = mail("seq448")
    CK["K1"] = {"登錄": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == SX.REG_SHA for f in fs), "裁定seq448": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1']}")
    if not (CK["K1"]["相符"] and rul):
        raise SystemExit("⛔ K1")
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8")); sha = MJ["origin/main"]
    RR = pd.read_csv(os.path.join(out, "events_R.csv.gz"), dtype={"sid": str, "期別": str})
    EV = pd.read_csv(os.path.join(SX.OUT, "events.csv.gz"), dtype={"sid": str, "期別": str})
    EV = EV[EV["進場"] == "保留"]
    want = {(s, e, E) for E in SX.ES for s, e, w in zip(EV["sid"], EV["e"], EV[f"E{E}走得完"]) if w == True}  # noqa: E712
    have = set(zip(RR["sid"], RR["e"], RR["E"]))
    CK["K2"] = {"重建": MJ["頻率表重建"], "events_R": len(have), "應有": len(want), "差": len(want ^ have)}
    log(f"[K2] {CK['K2']}")
    # ── K3
    _, DN, _ = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, 3)
    from backtest import researchIndMom_freq as IMF
    Zm = IMF.build_panel("主", 2, print)
    CAL, ix, C, BAD, O, NE = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["O"], PX["NE"]
    CEND = len(CAL) - 1
    EVi = EV.set_index(["sid", "e"])
    S = RR.sample(500, random_state=13)
    bad = 0; mx = 0.0
    for _, r in S.iterrows():
        i = ix[r["sid"]]; e = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["e"])))); E = int(r["E"])
        f = 1.0
        if r["sid"] in PX["im"]:
            j = PX["im"][r["sid"]]
            v = np.flatnonzero(np.isfinite(Zm["C"][j]))
            if len(v):
                f = PX["C"][i, NE + v[-1]] / Zm["C"][j, v[-1]]
        def op(p):
            return O[i, p] * (f if p >= NE else 1.0)
        x = e + E
        cs = pd.Series(BAD[i, e + 1:x + 1])
        if cs.any():
            x = e + int(cs.idxmax())
        lv = int(np.flatnonzero(np.isfinite(C[i]))[-1])
        if CEND - lv >= 5 and lv < x:
            x = lv
        seg = pd.Series(C[i, :x + 1]).dropna()
        px = seg.iloc[-1]
        R0 = px / op(e) - 1 - SM.COST
        ev = EVi.loc[(r["sid"], r["e"])]
        mine = {"R_C0": R0}
        for c in SX.RULES:
            if ev[f"{c}_E{E}"] == "賣出":
                mine[f"R_{c}"] = op(e + int(ev[f"{c}_s偏移"])) / op(e) - 1 - SM.COST
            else:
                mine[f"R_{c}"] = R0
            mine[f"d_{c}"] = mine[f"R_{c}"] - R0
        for k, v in mine.items():
            dv = abs(v - r[k]) / max(1.0, abs(v)); mx = max(mx, dv)
            if dv > 1e-9:
                bad += 1
    CK["K3"] = {"抽列": len(S), "不同": bad, "最大相對差": mx}
    log(f"[K3] {CK['K3']}")
    # ── K4
    zb = NormalDist().inv_cdf(1 - 0.05 / 12)
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig")
    J = RR[(RR["母體"] == "缺貨型") & (RR["E"] == 250)]
    k4 = []
    for _, r in CE.iterrows():
        c = r["賣法"]; st = {}
        for sg in ("探索", "確認"):
            d = J[J["段"] == sg]
            mu, se = clse(d[f"d_{c}"], d["進場月"])
            st[sg] = (mu, mu - zb * se, mu + zb * se, d["進場月"].nunique(), d[d["C7可判"]]["進場月"].nunique())
            if abs(mu - r[f"{sg}_d平均"]) > 1e-12 or r[f"{sg}_CI99.17(Bonf6)"] != f"[{mu - zb * se:+.4f}, {mu + zb * se:+.4f}]":
                k4.append((c, sg))
        ex, cf = st["探索"], st["確認"]
        if c == "C6":
            v = "還沒測"
        elif min(ex[3], cf[3]) < 24 or (c == "C7" and min(ex[4], cf[4]) < 24):
            v = "還沒測"
        elif ex[0] > 0 and cf[0] > 0 and cf[1] > 0:
            v = "有利"
        elif ex[0] < 0 and cf[0] < 0 and cf[2] < 0:
            v = "差"
        else:
            v = "分不出"
        if v not in r["判定"]:
            k4.append((c, "判定", v, r["判定"]))
    DS = pd.read_csv(os.path.join(out, "desc.csv"), encoding="utf-8-sig")
    for _, r in DS[(DS["E"] == 250) & DS["母體"].isin(["缺貨型", "一般股"])].iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["母體"] == r["母體"]) & (RR["E"] == 250)]
        col = "R_C0" if r["賣法"].startswith("C0") else "d_" + r["賣法"].split()[0]
        if abs(d[col].mean() - r["平均"]) > 1e-12 or len(d) != r["n"]:
            k4.append(("desc", r["段"], r["母體"], r["賣法"]))
    CK["K4"] = {"不符": k4, "z": zb}
    log(f"[K4] {CK['K4']}")
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(RT.WORK, "git_before_main.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("researchShortageExit.py", "researchShortageExit_check.py", "researchRevTurn.py", "researchRevTurn_check.py", "resultsShortageExit/main", "resultsRevTurn/main")
    others = [x for x in extra if not any(w in x for w in allowed)]
    CK["K5"] = {"策略鎖": lock, "git 新增": extra, "本件以外（他處同時新增，本件程式不寫）": others,
                "只多本件或他處新檔": all(x.startswith("?? ") for x in others)}
    ok = CK["K1"]["相符"] and all(MJ["頻率表重建"].values()) and CK["K2"]["差"] == 0 and bad == 0 and not k4 and "相符" in "".join(lock) and CK["K5"]["只多本件或他處新檔"]
    CK["全過"] = bool(ok)
    log(f"[K5] {CK['K5']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

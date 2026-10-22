# -*- coding: utf-8 -*-
"""營收轉強驗證 seq2 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾（只寫 main/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevTurn_check

K1 登錄 sha 獨立重算 ＋ 裁定 seq448 信在。
K2 頻率表重建逐字相同（main.json）；events_R（事件, H）集合 ＝ freq/events 中 配到 ∧ H 走得完。
K3 抽 400 列另一條路重算：接縫倍數以出場日取、出場以 pandas 自找、對照逐檔自算 ⇒ R事件、R對照平均、X、大盤報酬指數 R 逐值相同。
K4 判定：自寫月分群 se ⇒ 各段×H 的 X 平均、CI95、判定字串；split.csv、group12.csv 自算相同。
K5 策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔與 main 結果夾。
"""
from __future__ import annotations

import glob
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn as RM                  # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit_check as SC       # noqa: E402  sha_of、mail、clse

LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def main():
    out = RM.OUT; CK = {}
    fs = SC.mail(f"sha{RT.REG_SHA}"); rul = SC.mail("seq448")
    CK["K1"] = {"登錄": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(SC.sha_of(f) == RT.REG_SHA for f in fs), "裁定seq448": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1']}")
    if not (CK["K1"]["相符"] and rul):
        raise SystemExit("⛔ K1")
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8")); sha = MJ["origin/main"]
    RR = pd.read_csv(os.path.join(out, "events_R.csv.gz"), dtype={"sid": str, "期別": str})
    EV = pd.read_csv(os.path.join(RT.OUT, "events.csv.gz"), dtype=str, keep_default_na=False)
    EV = EV[EV["配到"] == "True"]
    want = {(s, e, H) for H in RT.HS for s, e, w in zip(EV["sid"], EV["e"], EV[f"H{H}走得完"]) if w == "True"}
    have = set(zip(RR["sid"], RR["e"], RR["H"]))
    CK["K2"] = {"重建": MJ["頻率表重建"], "events_R": len(have), "應有": len(want), "差": len(want ^ have)}
    log(f"[K2] {CK['K2']}")
    # ── K3
    _, DN, _ = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, 3)
    from backtest import researchIndMom_freq as IMF
    Zm = IMF.build_panel("主", 2, print)
    CAL, ix, C, BAD, O, NE = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["O"], PX["NE"]
    CEND = len(CAL) - 1
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri = pd.Series(tri["close"].astype(float).to_numpy(), index=pd.to_datetime(tri["date"])).groupby(level=0).first()

    def tri_at(d):
        return float(tri[tri.index <= d].iloc[-1])

    def R_of(sid, e, H):
        i = ix[sid]; f = 1.0
        if sid in PX["im"]:
            j = PX["im"][sid]; v = np.flatnonzero(np.isfinite(Zm["C"][j]))
            if len(v):
                f = PX["C"][i, NE + v[-1]] / Zm["C"][j, v[-1]]
        p0 = O[i, e] * (f if e >= NE else 1.0)
        x = e + H
        cs = pd.Series(BAD[i, e + 1:x + 1])
        if cs.any():
            x = e + int(cs.idxmax())
        lv = int(np.flatnonzero(np.isfinite(C[i]))[-1])
        if CEND - lv >= 5 and lv < x:
            x = lv
        return pd.Series(C[i, e:x + 1]).dropna().iloc[-1] / p0 - 1
    EVi = EV.set_index(["sid", "e"])
    S = RR.sample(400, random_state=17)
    bad = 0; mx = 0.0
    for _, r in S.iterrows():
        e = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["e"])))); H = int(r["H"])
        Re = R_of(r["sid"], e, H)
        rc = np.nanmean([R_of(s, e, H) for s in EVi.loc[(r["sid"], r["e"]), "對照"].split()])
        Ri = tri_at(CAL[e + H]) / tri_at(CAL[e - 1]) - 1
        for a_, b_ in ((Re, r["R事件"]), (rc, r["R對照平均"]), (Re - rc, r["X"]), (Ri, r["R大盤報酬指數"])):
            dv = abs(a_ - b_) / max(1.0, abs(a_)); mx = max(mx, dv)
            bad += int(dv > 1e-9)
    CK["K3"] = {"抽列": len(S), "不同": bad, "最大相對差": mx}
    log(f"[K3] {CK['K3']}")
    # ── K4
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig")
    k4 = []; st = {}
    for _, r in CE.iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["H"] == r["H"])].dropna(subset=["X"])
        mu, se = SC.clse(d["X"], d["月"])
        st[(r["H"], r["段"])] = (mu, mu - 1.96 * se, mu + 1.96 * se, d["月"].nunique())
        if abs(mu - r["X平均"]) > 1e-12 or abs(mu - 1.96 * se - r["CI95下"]) > 1e-12 or len(d) != r["n"]:
            k4.append((r["H"], r["段"]))
    ex, cf = st[(250, "探索")], st[(250, "確認")]
    v = "還沒測" if min(ex[3], cf[3]) < 24 else ("合格" if (ex[0] > 0 and cf[0] > 0 and cf[1] > 0) else ("不合格" if cf[0] <= 0 else "測不出"))
    if not MJ["判定"].startswith(v):
        k4.append(("判定", v, MJ["判定"]))
    SP = pd.read_csv(os.path.join(out, "split.csv"), encoding="utf-8-sig")
    for _, r in SP.iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["H"] == 250)].dropna(subset=["X"])
        m = {"原物料型八業": d["原物料型"] == True, "其他產業": d["原物料型"] == False, "毛利率年增>0": d["毛利率年增>0"] == True,  # noqa: E712
             "毛利率年增≤0（≈轉嫁型）": d["毛利率年增>0"] == False, "毛利率不可算": d["毛利率年增>0"].isna(), "甲單獨": d["甲"] & ~d["乙"],  # noqa: E712
             "乙單獨": ~d["甲"] & d["乙"], "甲且乙": d["甲"] & d["乙"], "前30%": d["市值前30%"] == True, "後70%": d["市值前30%"] == False,  # noqa: E712
             "≥當日中位": d["前60日≥中位"] == True, "＜當日中位": d["前60日≥中位"] == False}[r["組"]]  # noqa: E712
        dd = d[m]
        if len(dd) != r["n"] or (len(dd) and abs(dd["X"].mean() - r["X平均"]) > 1e-12):
            k4.append(("split", r["段"], r["組"]))
    G12 = pd.read_csv(os.path.join(out, "group12.csv"), encoding="utf-8-sig")
    for _, r in G12.iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["H"] == 250)].dropna(subset=["X"])
        m0 = 2017 * 12 if r["段"] == "探索" else 2022 * 12
        g = d.groupby(d["月"].map(lambda s: (int(s[:4]) * 12 + int(s[5:7]) - 1 - m0) % 12))["X"].mean()
        if int((g > 0).sum()) != int(r["＞0組數"]) or abs(g.median() - r["組X中位"]) > 1e-12:
            k4.append(("group12", r["段"]))
    CK["K4"] = {"不符": k4}
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

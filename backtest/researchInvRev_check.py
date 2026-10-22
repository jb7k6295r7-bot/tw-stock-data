# -*- coding: utf-8 -*-
"""存貨天數下降＋營收轉強 seq1 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾（只寫 main/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev_check

K1 登錄 sha 獨立重算 ＋ 裁定 seq456 信在。
K2 頻率表重建逐字相同（main.json）；events_R（事件, H）集合 ＝ freq/events 中 e 可進場 ∧ H 走得完。
K3 抽 400 列另一條路重算：接縫倍數以主世界最後一根取、出場 pandas 自找、主對照與描述對照逐檔自算 ⇒ R事件、R主對照平均、R描述對照平均、X、指數 R 逐值相同。
   （不要求存貨版主對照只描述，對照名單不存檔 ⇒ 只核件數與 X 欄＝R事件−該欄對照平均的恆等式）
K4 判定：自寫月分群 se ⇒ H×段 X_主 平均、CI95、判定字串；split 原物料／其他、group12 自算相同。
K5 敏感度：sens.csv 事件數 ＝ ~/rtfwork/ivr_sens_* 頻率表事件數；X 平均由各該 events 另一條路重算相同。
K6 策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔與 main 結果夾（他處新檔另列）。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchInvRev as IM                   # noqa: E402
from backtest import researchInvRev_freq as IV              # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit_check as SC       # noqa: E402  sha_of、mail、clse

LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def main():
    out = IM.OUT; CK = {}
    fs = SC.mail(f"sha{IV.REG_SHA}"); rul = SC.mail("seq456")
    CK["K1"] = {"登錄": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(SC.sha_of(f) == IV.REG_SHA for f in fs), "裁定seq456": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1']}")
    if not (CK["K1"]["相符"] and rul):
        raise SystemExit("⛔ K1")
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8"))
    RR = pd.read_csv(os.path.join(out, "events_R.csv.gz"), dtype={"sid": str, "期別": str})
    EV = pd.read_csv(os.path.join(IV.OUT, "events.csv.gz"), dtype=str, keep_default_na=False)
    EV = EV[EV["進場"] == "保留"]
    want = {(s, e, H) for H in IV.HS for s, e, w in zip(EV["sid"], EV["e"], EV[f"H{H}走得完"]) if w == "True"}
    have = set(zip(RR["sid"], RR["e"], RR["H"]))
    CK["K2"] = {"重建": MJ["頻率表重建"], "events_R": len(have), "應有": len(want), "差": len(want ^ have)}
    log(f"[K2] {CK['K2']}")
    _, DN, _ = RT.ensure_data(IV.BASE_SHA)
    PX = RT.prices(IV.BASE_SHA, DN, 3)
    from backtest import researchIndMom_freq as IMF
    Zm = IMF.build_panel("主", 2, print)
    CAL, ix, C, BAD, O, NE = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["O"], PX["NE"]
    CEND = len(CAL) - 1
    latest = MJ["資料"]["最新 main"]
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{latest}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
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
    S = RR.sample(400, random_state=21)
    bad = 0; mx = 0.0; idb = 0
    for _, r in S.iterrows():
        e = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["e"])))); H = int(r["H"])
        ev = EVi.loc[(r["sid"], r["e"])]
        Re = R_of(r["sid"], e, H)
        pairs = [(Re, r["R事件"]), (tri_at(CAL[e + H]) / tri_at(CAL[e - 1]) - 1, r["R指數"])]
        for col, lab in (("主對照", "主"), ("描述對照", "描述")):
            ss = ev[col].split()
            if ss:
                m = float(np.nanmean([R_of(s, e, H) for s in ss]))
                pairs += [(m, r[f"R{lab}對照平均"]), (Re - m, r[f"X_{lab}"])]
            elif np.isfinite(r[f"X_{lab}"]):
                bad += 1
        for a_, b_ in pairs:
            dv = abs(a_ - b_) / max(1.0, abs(a_)); mx = max(mx, dv); bad += int(dv > 1e-9)
        if np.isfinite(r["X_無存貨要求"]) and abs(r["R事件"] - r["R無存貨要求對照平均"] - r["X_無存貨要求"]) > 1e-12:
            idb += 1
    CK["K3"] = {"抽列": len(S), "不同": bad, "最大相對差": mx, "無存貨要求版恆等式不符": idb,
                "無存貨要求版配到": MJ["不要求存貨版主對照配到"]}
    log(f"[K3] {CK['K3']}")
    # ── K4
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig")
    k4 = []; st = {}
    for _, r in CE.iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["H"] == r["H"])].dropna(subset=["X_主"])
        mu, se = SC.clse(d["X_主"], d["月"])
        st[(r["H"], r["段"])] = (mu, mu - 1.96 * se, mu + 1.96 * se, d["月"].nunique())
        if abs(mu - r["X_主_平均"]) > 1e-12 or abs(mu - 1.96 * se - r["X_主_CI95下"]) > 1e-12 or len(d) != r["X_主_n"]:
            k4.append((r["H"], r["段"]))
    ex, cf = st[(250, "探索")], st[(250, "確認")]
    v = "還沒測" if min(ex[3], cf[3]) < 24 else ("合格" if (ex[0] > 0 and cf[0] > 0 and cf[1] > 0) else ("不合格" if cf[0] <= 0 else "測不出"))
    if not MJ["判定"].startswith(v):
        k4.append(("判定", v, MJ["判定"]))
    SP = pd.read_csv(os.path.join(out, "split.csv"), encoding="utf-8-sig")
    for _, r in SP[SP["組"].isin(["原物料八業", "其他產業"])].iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["H"] == 250)].dropna(subset=["X_主"])
        dd = d[d["原物料型"] == (r["組"] == "原物料八業")]
        if len(dd) != r["n"] or abs(dd["X_主"].mean() - r["X平均"]) > 1e-12:
            k4.append(("split", r["段"], r["組"]))
    G12 = pd.read_csv(os.path.join(out, "group12.csv"), encoding="utf-8-sig")
    for _, r in G12.iterrows():
        d = RR[(RR["段"] == r["段"]) & (RR["H"] == 250)].dropna(subset=["X_主"])
        m0 = 2015 * 12 + 3 if r["段"] == "探索" else 2020 * 12
        g = d.groupby(d["月"].map(lambda s: (int(s[:4]) * 12 + int(s[5:7]) - 1 - m0) % 12))["X_主"].mean()
        if int((g > 0).sum()) != int(r["＞0組數"]) or abs(g.median() - r["組X中位"]) > 1e-12:
            k4.append(("group12", r["段"]))
    CK["K4"] = {"不符": k4}
    log(f"[K4] {CK['K4']}")
    # ── K5 敏感度
    SE = pd.read_csv(os.path.join(out, "sens.csv"), encoding="utf-8-sig")
    k5 = []
    for thr in IV.SENS:
        E2 = pd.read_csv(os.path.join(RT.WORK, f"ivr_sens_{int(-thr * 100)}", "events.csv.gz"), dtype=str, keep_default_na=False)
        for sg in ("探索", "確認"):
            r = SE[(SE["門檻"].round(4) == round(thr, 4)) & (SE["段"] == sg)].iloc[0]
            d = E2[(E2["段"] == sg) & (E2["進場"] == "保留") & (E2["主對照"] != "") & (E2["H250走得完"] == "True")]
            xs = []
            for s, e_, ctl in zip(d["sid"], d["e"], d["主對照"]):
                e = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(e_))))
                xs.append(R_of(s, e, 250) - np.nanmean([R_of(c, e, 250) for c in ctl.split()]))
            if int((E2["段"] == sg).sum()) != int(r["事件"]) or len(xs) != int(r["主格n"]) or abs(np.mean(xs) - r["X平均"]) > 1e-9:
                k5.append((thr, sg, len(xs), float(np.mean(xs)) if xs else None, r["X平均"]))
    CK["K5"] = {"不符": k5}
    log(f"[K5] {CK['K5']}")
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(RT.WORK, "git_before_ivrm.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("researchInvRev.py", "researchInvRev_check.py", "resultsInvRev/main")
    others = [x for x in extra if not any(w in x for w in allowed)]
    CK["K6"] = {"策略鎖": lock, "git 新增": extra, "本件以外（他處同時新增）": others, "只多本件或他處新檔": all(x.startswith("?? ") for x in others)}
    ok = (CK["K1"]["相符"] and all(MJ["頻率表重建"].values()) and CK["K2"]["差"] == 0 and bad == 0 and idb == 0 and not k4 and not k5
          and "相符" in "".join(lock) and CK["K6"]["只多本件或他處新檔"])
    CK["全過"] = bool(ok)
    log(f"[K6] {CK['K6']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()

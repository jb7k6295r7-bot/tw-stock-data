# -*- coding: utf-8 -*-
"""PREREG財報公告後漂移PEAD組合層 seq1【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPEADpf/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEADpf_check

C1 日曆時間組合逐日重建（M、Mslip、SAMEQ、H20、H120，全部日子）：只用 events_<臂>.csv.gz（入組合、進場日、賣出日、買價、賣價）＋ 快取開收盤、有無成交
   ＋ 0050 開收盤，另寫一支（陣列記持股數、成本以【二分法】解「成本 ＝ 依（淨值 − 成本）算出的目標所需成本」，主檔用定點疊代）⇒ 對 eq npz 逐日；
   抽樣 6 個調整日印明細：n、w、可交易各檔調整後權重 ＝ w ×（淨值 − 成本）÷ 淨值、0050 權重、凍結檔數。
C2 事件：入組合事件 買價 ＝ 快取還原開盤、賣價 ＝ 買價×(1＋R)、R ＝ resultsPEAD 事件層同 (代號, 季) 的 R；同檔持有期不重疊（入組合者）；
   不入者皆為「e ≤ 同檔前一筆賣出日」。
C3 10 檔版（S10）：researchPTHpf_check.rebuild_slot（自寫 10 槽迴圈）⇒ 對 eq；每個買進日 買到的 SUE ≥ 同日沒買到且未持有的候選；有空槽、0050 未用盡卻有未買候選的日子 ＝ 0。
C4 0050 價：npz 的 Bc／Bo ＝ data.load_stock("0050") 還原收盤（ffill）／開盤（缺 ⇒ 前一日收盤）。
C5 段指標：自寫年化與最大回落、0050 同窗 ⇒ 對主表（JSON 全精度）；標籤重算。
C6 等效獨立檔數：主判每段抽 2 個進場日，researchDumb.eff_n（原函式）⇒ 對矩陣化值。
C7 策略鎖：python -m backtest.strategy_lock --check ＝ 相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPEADpf as M                    # noqa: E402  常數、ARMS
from backtest import researchPTHpf as PP                    # noqa: E402  finish_world、effn_vec（C6 對照）
from backtest import researchPTHpf_check as PC              # noqa: E402  rebuild_slot、seg_metrics、lab
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import researchDumb as RD                     # noqa: E402
from backtest import data as D                              # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = M.OUT
B_, S_ = 0.001425, 0.004425
EB, ES = 0.001425, 0.002425
SL = 0.005


def cost_of(T, cur, T50, cur50, cb, cs):
    d = T - cur; d50 = T50 - cur50
    return float(np.sum(np.where(d > 0, d * cb, -d * cs))) + (d50 * EB if d50 > 0 else -d50 * ES)


def targets(E, c, ntr, F, w):
    En = E - c
    T = np.full(ntr, w * En); T50 = En - T.sum() - F
    if T50 < 0:
        if T.sum() > 0:
            T = T * max(En - F, 0.0) / T.sum()
        T50 = En - T.sum() - F
    return T, T50


def bisect_cost(E, cur, F, w, cur50, cb, cs):
    lo, hi = 0.0, 0.05 * E
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        T, T50 = targets(E, mid, len(cur), F, w)
        if cost_of(T, cur, T50, cur50, cb, cs) > mid:
            lo = mid
        else:
            hi = mid
    c = 0.5 * (lo + hi)
    T, T50 = targets(E, c, len(cur), F, w)
    return c, T, T50


def rebuild_cal(W, ek, slip, sample, log, tag):
    n0 = W["n0"]; CM = W["CM"]; O = np.asarray(W["O"], float)[:, :n0]; TRD = W["TRD"]; Bc = W["Bc"]; Bo = W["Bo"]
    cb = B_ + (SL if slip else 0.0); cs = S_ + (SL if slip else 0.0)
    dpos = {d: i for i, d in enumerate(W["dates"])}
    k = ek[ek["入組合"]].reset_index(drop=True)
    j = k["sid"].map(W["ix"]).to_numpy(); e = k["進場日"].map(dpos).to_numpy(); s = np.array([dpos[x] if x else -1 for x in k["賣出日"]])
    P = k["買價P"].to_numpy(float); px = k["賣價"].to_numpy(float)
    m = len(k); sh = np.zeros(m); act = np.zeros(m, bool)
    u = 1.0 / Bc[0]; cash = 0.0; eq = np.zeros(n0); det = {}
    ent = {}; ex = {}
    for q in range(m):
        ent.setdefault(int(e[q]), []).append(q)
        if s[q] >= 0:
            ex.setdefault(int(s[q]), []).append(q)
    for t in range(n0):
        if t in ent:
            hq = np.flatnonzero(act)
            okp = TRD[j[hq], t] & np.isfinite(O[j[hq], t]) & (np.nan_to_num(O[j[hq], t]) > 0)
            tq = hq[okp]; fq = hq[~okp]
            F = float(np.sum(sh[fq] * CM[j[fq], t - 1])) if len(fq) else 0.0
            nq = np.array(ent[t]); cur = np.r_[sh[tq] * O[j[tq], t], np.zeros(len(nq))]
            E = u * Bo[t] + cash + float(cur.sum()) + F
            w = 1.0 / max(len(hq) + len(nq), 10)
            c, T, T50 = bisect_cost(E, cur, F, w, u * Bo[t], cb, cs)
            sh[tq] = T[:len(tq)] / O[j[tq], t]; sh[nq] = T[len(tq):] / P[nq]; act[nq] = True
            u = T50 / Bo[t]; cash = E - c - T.sum() - F - T50
            if t in sample:
                det[f"{W['dates'][t]} 開盤"] = {"n": int(len(hq) + len(nq)), "w": w, "淨值": E, "成本": c, "凍結檔數": int(len(fq)),
                                               "可交易權重(調整後)最小／最大": [float(T.min() / E), float(T.max() / E)] if len(T) else None,
                                               "應為 w×(淨值−成本)÷淨值": w * (E - c) / E, "0050權重": T50 / E}
        if t in ex:
            xq = np.array([q for q in ex[t] if act[q]])
            proc = 0.0
            if len(xq):
                V = sh[xq] * px[xq]; proc = float(np.sum(V * (1 - cs))); sh[xq] = 0.0; act[xq] = False
                hq = np.flatnonzero(act)
                okc = TRD[j[hq], t]
                tq = hq[okc]; fq = hq[~okc]
                F = float(np.sum(sh[fq] * CM[j[fq], t])) if len(fq) else 0.0
                cur = sh[tq] * CM[j[tq], t]
                E = u * Bc[t] + cash + proc + float(cur.sum()) + F
                w = 1.0 / max(len(hq), 10)
                c, T, T50 = bisect_cost(E, cur, F, w, u * Bc[t], cb, cs)
                sh[tq] = T / CM[j[tq], t]
                u = T50 / Bc[t]; cash = E - c - T.sum() - F - T50
                if t in sample:
                    det[f"{W['dates'][t]} 收盤"] = {"n": int(len(hq)), "w": w, "淨值": E, "成本": c, "凍結檔數": int(len(fq)),
                                                   "可交易權重(調整後)最小／最大": [float(T.min() / E), float(T.max() / E)] if len(T) else None,
                                                   "應為 w×(淨值−成本)÷淨值": w * (E - c) / E, "0050權重": T50 / E}
        hq = np.flatnonzero(act)
        eq[t] = u * Bc[t] + cash + float(np.sum(sh[hq] * CM[j[hq], t]))
    return eq, det


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    T0 = time.time(); J = {"時間": M.now_tpe()}; ok = True
    PJ = json.load(open(os.path.join(OUT, "PEADpf.json"), encoding="utf-8"))
    W = AS.load_world("主", log); PP.finish_world(W)
    Z = np.load(os.path.join(OUT, "eq.npz"))
    # C4
    D.DATA = W["data"]; st = D.load_stock("0050", "twse", W["cal"]).df
    bc = pd.Series(st["close"].to_numpy(float)).ffill().to_numpy(); bo = st["open"].to_numpy(float).copy()
    for t in range(len(bo)):
        if not (np.isfinite(bo[t]) and bo[t] > 0):
            bo[t] = bc[t - 1] if t > 0 else bc[0]
    c4 = {"Bc 最大差": float(np.max(np.abs(Z["Bc"] - bc))), "Bo 最大差": float(np.max(np.abs(Z["Bo"] - bo)))}
    J["C4"] = c4; log(f"[C4] {c4}"); ok &= c4["Bc 最大差"] == 0 and c4["Bo 最大差"] == 0
    dpos = {d: i for i, d in enumerate(W["dates"])}
    # C1、C2
    ref = pd.read_csv("backtest/resultsPEAD/events/trades_上季切點.csv.gz", dtype={"sid": str}, keep_default_na=False, float_precision="round_trip")
    refR = {(s, q): r for s, q, r in zip(ref["sid"], ref["季"], ref["R"])}
    rng = np.random.default_rng(20261021)
    for arm, cfg in M.ARMS.items():
        if cfg["kind"] != "cal":
            continue
        ek = PC.rd(os.path.join(OUT, f"events_{arm}.csv.gz"))
        ek["入組合"] = ek["入組合"].astype(str) == "True"
        rd = sorted(set(ek.loc[ek["入組合"], "進場日"].map(dpos)) | set(ek.loc[ek["入組合"] & (ek["賣出日"] != ""), "賣出日"].map(dpos)))
        sample = set(int(x) for x in rng.choice(rd, 6, replace=False)) if arm == "M" else set()
        eq, det = rebuild_cal(W, ek, cfg["slip"], sample, log, arm)
        d = float(np.max(np.abs(eq / Z[f"{arm}_eq"] - 1)))
        c1 = {"逐日淨值最大相對差": d}
        if det:
            c1["抽樣調整日"] = det
            for k_, v_ in det.items():
                log(f"  [C1 抽樣 {arm} {k_}] {json.dumps(v_, ensure_ascii=False, default=float)}")
            dv = [abs(z - v_["應為 w×(淨值−成本)÷淨值"]) for v_ in det.values() if v_["可交易權重(調整後)最小／最大"]
                  for z in v_["可交易權重(調整後)最小／最大"]]
            c1["抽樣日可交易權重偏離最大"] = float(max(dv)) if dv else 0.0
        J[f"C1_{arm}"] = c1; log(f"[C1 {arm}] 逐日淨值最大相對差 {d:.2e}"); ok &= d <= 1e-9
        # C2
        k = ek[ek["入組合"]]
        O = np.asarray(W["O"], float)
        nb = {"買價≠快取開盤": 0, "賣價式": 0, "R≠事件層": 0, "同檔重疊": 0, "不入但未重疊": 0}
        for sid, e_, P, px, R, q in zip(k["sid"], k["進場日"], k["買價P"], k["賣價"], k["R"], k["季"]):
            if O[W["ix"][sid], dpos[e_]] != P:
                nb["買價≠快取開盤"] += 1
            if not ((np.isnan(px) and np.isnan(R)) or abs(px - P * (1 + R)) <= 1e-12 * P):
                nb["賣價式"] += 1
            if arm in ("M", "Mslip"):
                rr = refR[(sid, q)]; rr = float(rr) if rr != "" else np.nan
                if not ((np.isnan(rr) and np.isnan(R)) or rr == R):
                    nb["R≠事件層"] += 1
        iv = {}
        for sid, e_, s_ in zip(k["sid"], k["進場日"].map(dpos), [dpos[x] if x else 10 ** 9 for x in k["賣出日"]]):
            iv.setdefault(sid, []).append((e_, s_))
        for sid, L in iv.items():
            L.sort()
            nb["同檔重疊"] += sum(1 for a_, b_ in zip(L[:-1], L[1:]) if b_[0] <= a_[1])
        for sid, e_ in zip(ek.loc[~ek["入組合"], "sid"], ek.loc[~ek["入組合"], "進場日"].map(dpos)):
            if not any(a_ <= e_ <= b_ for a_, b_ in iv.get(sid, [])):
                nb["不入但未重疊"] += 1
        nb["入組合"] = int(len(k)); nb["不入"] = int((~ek["入組合"]).sum())
        J[f"C2_{arm}"] = nb; log(f"[C2 {arm}] {nb}"); ok &= not any(v for kk, v in nb.items() if kk not in ("入組合", "不入"))
    # C3
    df = PC.rd(os.path.join(OUT, "trades_S10.csv.gz"))
    eq, bad = PC.rebuild_slot(W, df, Z["Bc"], Z["Bo"])
    d = float(np.max(np.abs(eq / Z["S10_eq"] - 1)))
    tb = df["買進日"].map(dpos).to_numpy(); ts = np.array([dpos[x] if x else W["n0"] + 1 for x in df["賣出日"]])
    evd = ref.assign(t=ref["進場日"].map(dpos))
    viol = 0; nday = 0
    for t, g in df.groupby(tb):
        nday += 1
        held = set(df["sid"][(tb < t) & (ts >= t)])               # 當天賣出者當天不再買（block_same）
        cand = evd[(evd["t"] == t) & ~evd["sid"].isin(held) & ~evd["sid"].isin(set(g["sid"]))]
        nheld = int(((tb < t) & (ts > t)).sum()) + len(g)
        if len(cand) and g["SUE"].min() < cand["SUE"].max() - 1e-15:
            viol += 1
        if len(cand) and nheld < 10 and Z["S10_u"][t] > 1e-9:
            viol += 1
    c3 = {"逐日淨值最大相對差": d, "買進日": nday, "SUE由高往下違反日": viol, **bad}
    J["C3"] = c3; log(f"[C3] {c3}"); ok &= d <= 1e-9 and viol == 0 and not any(bad.values())
    # C5
    bad5 = []
    for r in PJ["主表"]:
        x = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[0]))); y = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[1])))
        cg, md = PC.seg_metrics(Z[f"{r['臂']}_eq"], x, y); bcg, bmd = PC.seg_metrics(Z["Bc"], x, y)
        if abs(cg - r["年化"]) > 1e-9 or abs(md - r["回落"]) > 1e-9 or abs(bcg - r["0050年化"]) > 1e-9 or PC.lab(cg, md, bcg, bmd) != r["標籤"]:
            bad5.append((r["臂"], r["段"]))
    J["C5"] = {"列": len(PJ["主表"]), "不同": len(bad5), "例": [str(b) for b in bad5[:3]]}; log(f"[C5] {J['C5']}"); ok &= not bad5
    # C6
    ek = PC.rd(os.path.join(OUT, "events_M.csv.gz"))
    ek = ek[ek["入組合"].astype(str) == "True"]
    iv = np.stack([ek["sid"].map(W["ix"]).to_numpy(), ek["進場日"].map(dpos).to_numpy(),
                   np.array([dpos[x] if x else W["n0"] + 1 for x in ek["賣出日"]])], 1).astype(np.int64)
    Wd = {"C": W["C"], "ix": W["ix"], "NP": W["n0"] + 1}
    c6 = []
    for sg, (x, y) in W["segp"].items():
        days = sorted({int(t) for t in iv[:, 1] if x <= t <= y})
        for t in [days[len(days) // 3], days[2 * len(days) // 3]]:
            m = (iv[:, 1] <= t) & (t < iv[:, 2])
            TRx = [{"r": {"sid": W["sids"][j]}, "tb": int(a_), "ts": int(b_) if b_ <= W["n0"] else None} for j, a_, b_ in iv[m]]
            r0 = RD.eff_n(Wd, TRx, [t])[0]; mine = PP.effn_vec(W["C"], iv[m, 0], t)
            c6.append({"段": sg, "日": W["dates"][t], "N": r0[1], "eff_n(原)": r0[3], "矩陣化": mine[3], "相對差": abs(mine[3] / r0[3] - 1)})
            log(f"  [C6] {c6[-1]}")
    J["C6"] = c6; ok &= all(z["相對差"] < 1e-9 for z in c6)
    # C7
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    c7 = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
          "既有追蹤檔有改動(工作樹)": [l for l in gs if not l.startswith("??")], "本件新增": [l for l in gs if l.startswith("??") and ("PTHpf" in l or "PEADpf" in l)]}
    J["C7"] = c7; log(f"[C7] {c7}"); ok &= p.returncode == 0
    J["全部通過"] = bool(ok); J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{J['耗時秒']}s")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchYLskip 的獨立查核（營量版 seq378 同法）——回測線計算子代理。⛔ 不改任何既有檔、⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLskip_check

 Q1 主 r＝0、早年 r＝0（另各加 r＝137 驗不抽籤）：直接呼叫 research11.simulate_mtm（⛔ 不經 researchYLskip.engine、⛔ 不傳 log），
    只用 audit 逐日重建「開盤前持有」（同日先賣後買），自行分類 A 買到／D 已持有／C 槽滿（持有 ≥ 20）／B 其餘 ⇒ 與 classes.npz 逐筆比；eq_sha 對 seed_check
 Q1b B 確實是「relvol 排名在後」：每個有 B 的日子，B 的 relvol 最大值 ≤ 同日 A 的 relvol 最小值（NaN 視為 −∞）；且同日 A 筆數 ＝ 空槽數（現金用盡日除外，另計）
 Q2 A 類每筆淨報酬 ＝ audit 賣出金額 ÷ 買進金額 − 1 − COST（與主檔用的價格比值是不同欄）⇒ 對 signals.csv 淨
 Q3 抽樣訊號（每世界 6 筆）手算：D.load_stock 有成交列的還原收盤、純迴圈算前 20／60 日漲幅、距 52 週高；波位置逐日往回走、同週用 isocalendar；0050 超額重算
    （＝ researchYFskip_check.hand 的邏輯複製；⛔ 不 import 該檔，因為它 import 時會開 resultsYFskip/run_check.log）
 Q4 cells.csv 占比、筆數 ＝ classes.npz 重數；Q5 cells.csv 淨_平均／淨_中位／超額_平均 ＝ signals.csv 依類直接 mean／median（p ∈ {0,1}）
 Q6 seed_check 各段 B／C 筆數 ＝ Q1 自行分類的筆數
 容差：signals.csv 以 %.12g 存 ⇒ 1e−9
輸出 backtest/resultsYLskip/check.json、run_check.log
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

OUT = os.environ.get("YLS_OUT", "backtest/resultsYLskip")
SEEDS = (0, 137)
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
CLS = ("A", "B", "C", "D")
N = 20
COST = R.COST
TOL = 1e-9
_T0 = time.time()
_f = open(os.path.join(OUT, "run_check.log"), "a", encoding="utf-8")


def log(m):
    m = f"[{time.time() - _T0:6.0f}s] {m}"; print(m, flush=True); _f.write(m + "\n"); _f.flush()


def hand(W, wn, SIGT, res):
    cal = W["cal"]
    T = SIGT[SIGT["世界"] == wn].reset_index(drop=True)
    rng = np.random.default_rng(7)
    pick = rng.choice(np.flatnonzero((T["價格狀態"] == "ok").to_numpy()), 6, replace=False)
    days = sorted(set(T["訊號日"]))
    bo = D.load_stock("0050", "twse", cal).df
    b_open = bo["open"].to_numpy(float); b_close = pd.Series(bo["close"].to_numpy(float)).ffill().to_numpy(float)
    out = []
    for i in pick:
        r = T.iloc[i]; sid = r["sid"]; e = int(r["entry_pos"]); d = int(r["訊號日"])
        df = D.load_stock(sid, W["uni"].get(sid, "twse"), cal).df
        tr = np.flatnonzero(df["traded"].to_numpy()); c = df["close"].to_numpy(float)[tr]
        j = int(np.flatnonzero(tr == e)[0]) - 1
        r20 = c[j] / c[j - 20] - 1 if j >= 20 else np.nan
        r60 = c[j] / c[j - 60] - 1 if j >= 60 else np.nan
        mx = max(c[max(j - 244, 0):j + 1]); d52 = c[j] / mx - 1
        k = days.index(d); s = k
        while s > 0 and days[s] - days[s - 1] <= 5:
            s -= 1
        wave_start = days[s]
        prior = int(((T["訊號日"] >= wave_start) & (T["訊號日"] < d)).sum())
        iso = cal[d].isocalendar()[:2]
        wk = int(sum(1 for dd in T["訊號日"] if cal[dd].isocalendar()[:2] == iso))
        xp = int(r["xpos"]); pdx = min(xp, len(cal) - 1)
        if int(r["強制出場"]):
            pdx = int(W["SF"][sid])
        b_in = b_open[e] if np.isfinite(b_open[e]) and b_open[e] > 0 else b_close[e]
        exc = r["淨"] - (b_close[pdx] / b_in - 1 - 0.00385)
        rec = {"sid": sid, "entry_pos": e, "日期": str(cal[d].date()), "類": r["類"],
               "前20 主檔／手算": (r["前20日漲幅"], r20), "前60 主檔／手算": (r["前60日漲幅"], r60),
               "距52週高 主檔／手算（窗長）": (r["距52週高"], d52, int(r["52週窗長"])),
               "距本波首訊號 主檔／手算": (int(r["距本波首訊號"]), d - wave_start), "本波此前 主檔／手算": (int(r["本波此前訊號數"]), prior),
               "同週 主檔／手算": (int(r["同週訊號數"]), wk), "超額 主檔／手算": (r["超額"], exc)}
        ok = (abs(r20 - r["前20日漲幅"]) < TOL and (np.isnan(r["前60日漲幅"]) or abs(r60 - r["前60日漲幅"]) < TOL)
              and (int(r["52週窗長"]) < 245 or abs(d52 - r["距52週高"]) < TOL) and d - wave_start == int(r["距本波首訊號"])
              and prior == int(r["本波此前訊號數"]) and wk == int(r["同週訊號數"]) and abs(exc - r["超額"]) < TOL)
        rec["一致"] = bool(ok); out.append(rec)
    res[f"Q3 {wn} 手算"] = out
    res[f"Q3 {wn} 不一致筆"] = int(sum(not z["一致"] for z in out))
    log(f"[Q3 {wn}] 不一致 {res[f'Q3 {wn} 不一致筆']}／{len(out)}")


def engine_check(W, wn, SIGT, CMw, SC, res):
    T = SIGT[SIGT["世界"] == wn].reset_index(drop=True)
    E = T["entry_pos"].to_numpy(int); SID = T["sid"].to_numpy(); NET = T["淨"].to_numpy(float)
    RV = np.where(np.isnan(T["relvol"].to_numpy(float)), -np.inf, T["relvol"].to_numpy(float))
    for r in SEEDS:
        au = []
        o = R.simulate_mtm(W["SIG"][False], "H60", N, np.random.default_rng(RR.P1_SEED0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                           d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
        sh = hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()[:16]
        sc = SC[(SC["世界"] == wn) & (SC["r"] == r)].iloc[0]
        ev = {}
        for a in au:
            ev.setdefault(a["t"], []).append(a)
        held = {}; mine = np.full(len(T), -1); maxd = 0.0; nA = 0
        byday = {}
        for i in np.argsort(E, kind="stable"):
            byday.setdefault(int(E[i]), []).append(i)
        rank_bad = 0; slot_bad = 0; cash_days = 0; bdays = 0
        for t in sorted(set(ev) | set(E)):
            for a in ev.get(t, []):
                if a["side"] == "sell":
                    sb = held.pop(a["sid"])
                    net_a = a["amt"] / sb[1] - 1.0 - COST
                    i = int(np.flatnonzero((SID == a["sid"]) & (E == sb[0]))[0])
                    maxd = max(maxd, abs(net_a - NET[i])); nA += 1
            before = dict(held)
            bought = {a["sid"] for a in ev.get(t, []) if a["side"] == "buy"}
            ii = byday.get(t, [])
            for i in ii:
                s = SID[i]
                mine[i] = 0 if s in bought else (3 if s in before else (2 if len(before) >= N else 1))
            ia = [i for i in ii if mine[i] == 0]; ib = [i for i in ii if mine[i] == 1]
            if ib:
                bdays += 1
                if ia and RV[ib].max() > RV[ia].min():
                    rank_bad += 1
                if len(ia) != N - len(before):
                    cash_days += 1
                    if len(ia) > N - len(before):
                        slot_bad += 1
            for a in ev.get(t, []):
                if a["side"] == "buy":
                    held[a["sid"]] = (t, a["amt"])
        diff = int((mine != CMw).sum())
        res[f"Q1 {wn} r{r} 分類不同筆"] = diff
        res[f"Q1 {wn} r{r} eq_sha ≠ seed_check"] = int(sh != sc["eq_sha"])
        res[f"Q1b {wn} r{r} 有B日／B relvol 高於同日 A 的日數／A ≠ 空槽日（現金用盡）／A 超過空槽日"] = (bdays, rank_bad, cash_days, slot_bad)
        res[f"Q2 {wn} r{r} A 淨報酬（金額式）最大差／已出場筆"] = (maxd, nA)
        q6 = 0
        for sg in SEGS[wn]:
            m = (T["段"] == sg).to_numpy()
            for j, c in enumerate(CLS):
                q6 += int(int(((mine == j) & m).sum()) != int(sc[f"{sg}_{c}"]))
        res[f"Q6 {wn} r{r} 段×類筆數 ≠ seed_check"] = q6
        log(f"[Q1 {wn} r{r}] 分類不同 {diff}｜A {int((mine == 0).sum())} B {int((mine == 1).sum())} C {int((mine == 2).sum())} D {int((mine == 3).sum())}｜"
            f"sha {sh}｜Q1b {res[f'Q1b {wn} r{r} 有B日／B relvol 高於同日 A 的日數／A ≠ 空槽日（現金用盡）／A 超過空槽日']}｜Q2 {maxd:.2e}/{nA}｜Q6 {q6}")


def main():
    log("[查核開始]")
    SIGT = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str})
    CM = np.load(os.path.join(OUT, "classes.npz"))
    SC = pd.read_csv(os.path.join(OUT, "seed_check.csv.gz"), dtype={"eq_sha": str})
    cells = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8-sig")
    res = {}
    Wm, _ = IG.main_world(log)
    hand(Wm, "主", SIGT, res)
    engine_check(Wm, "主", SIGT, CM["主"], SC, res)
    We, _ = IG.early_world(log, 3)
    hand(We, "早年", SIGT, res)
    engine_check(We, "早年", SIGT, CM["早年"], SC, res)
    bad4 = bad5 = 0
    for wn in ("主", "早年"):
        T = SIGT[SIGT["世界"] == wn].reset_index(drop=True)
        segl = [(sg, (T["段"] == sg).to_numpy()) for sg in SEGS[wn]]
        if wn == "主":
            segl.append(("確認·滿60", ((T["段"] == "確認") & (T["未滿60"] == 0)).to_numpy()))
        for sg, m in segl:
            for j, c in enumerate(CLS):
                sel = m & (CM[wn] == j)
                cr = cells[(cells["世界"] == wn) & (cells["段"] == sg) & (cells["類"].str.startswith(c))].iloc[0]
                bad4 += int(abs(sel.sum() / m.sum() - cr["占比"]) > 1e-9) + int(int(sel.sum()) != int(cr["筆數"]))
                if sel.any():
                    v = T.loc[sel, "淨"]; x = T.loc[sel, "超額"]
                    # 加權中位（累積權重首次 ≥ 一半）＝ 排序後第 ceil(n/2) 個 ⇒ 用 lower median 對
                    lo_med = float(np.sort(v.to_numpy())[(len(v) - 1) // 2])
                    bad5 += int(abs(v.mean() - cr["淨_平均"]) > TOL) + int(abs(lo_med - cr["淨_中位"]) > TOL) + int(abs(x.mean() - cr["超額_平均"]) > TOL)
    res["Q4 占比／筆數不符格數"] = bad4
    res["Q5 淨平均／淨中位／超額平均不符格數"] = bad5
    log(f"[查核] {json.dumps({k: v for k, v in res.items() if not k.startswith('Q3') or '不一致' in k}, ensure_ascii=False, default=str)}")
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[查核完]")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchYFskip 的獨立查核（裁定 seq378）——回測線計算子代理。⛔ 不改任何既有檔、⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYFskip_check

 Q1 抽樣種子（主 r＝0、97、199；早年 r＝0、123、199）：直接呼叫 research11.simulate_mtm（⛔ 不經 researchYF_N.engine、⛔ 不傳 log），
    只用 audit 逐日重建「開盤前持有」（同日先賣後買），自行分類 A 買到／D 已持有／C 槽滿／B 其餘 ⇒ 與 classes.npz 該顆逐筆比；eq_sha 對 seed_counts
 Q2 抽樣種子 A 類每筆淨報酬 ＝ audit 賣出金額 ÷ 買進金額 − 1 − COST（與主檔用的價格比值是不同欄）⇒ 對 signals.csv 淨
 Q3 抽樣訊號（每世界 6 筆）手算：D.load_stock 有成交列的還原收盤、純迴圈算前 20／60 日漲幅、距 52 週高（52週窗長＝245 的才比）；
    波位置用逐日往回走（間隔 ≤5 同波）、同週用 isocalendar；0050 超額用 D.load_stock("0050") 重算
 Q4 cells.csv 占比 ＝ classes.npz 重數
 容差：signals.csv 以 %.12g 存 ⇒ 與 signals.csv 比的數值容差 1e−9（主檔內部 K5 用全精度、1e−12）
輸出 backtest/resultsYFskip/check.json、run_check.log
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

OUT = "backtest/resultsYFskip"
SEEDS = {"主": (0, 97, 199), "早年": (0, 123, 199)}
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
CLS = ("A", "B", "C", "D")
COST = R.COST
TOL = 1e-9                                                   # signals.csv 以 %.12g 存（12 位有效數字）⇒ 比對容差 1e−9
_T0 = time.time()
_f = open(os.path.join(OUT, "run_check.log"), "a", encoding="utf-8")


def log(m):
    m = f"[{time.time() - _T0:6.0f}s] {m}"; print(m, flush=True); _f.write(m + "\n"); _f.flush()


def hand(W, wn, SIGT, res):
    """Q3：抽樣訊號手算（在該世界的 D.DATA 下）。"""
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
        j = int(np.flatnonzero(tr == e)[0]) - 1                  # 進場根前一根 ＝ 訊號根
        r20 = c[j] / c[j - 20] - 1 if j >= 20 else np.nan
        r60 = c[j] / c[j - 60] - 1 if j >= 60 else np.nan
        mx = max(c[max(j - 244, 0):j + 1]); d52 = c[j] / mx - 1
        # 波：往回走
        k = days.index(d); s = k
        while s > 0 and days[s] - days[s - 1] <= 5:
            s -= 1
        wave_start = days[s]
        prior = int(((T["訊號日"] >= wave_start) & (T["訊號日"] < d)).sum())
        iso = cal[d].isocalendar()[:2]
        wk = int(sum(1 for dd in T["訊號日"] if cal[dd].isocalendar()[:2] == iso))
        # 0050
        xp = int(r["xpos"]); pdx = min(xp, len(cal) - 1)
        if int(r["強制出場"]):
            pdx = int(W["SF"][sid])
        b_in = b_open[e] if np.isfinite(b_open[e]) and b_open[e] > 0 else b_close[e]
        exc = r["淨"] - (b_close[pdx] / b_in - 1 - 0.00385)
        rec = {"sid": sid, "entry_pos": e, "日期": str(cal[d].date()),
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
    bad_cls = 0; bad_sha = 0; maxd = 0.0; nA = 0
    for r in SEEDS[wn]:
        au = []
        o = R.simulate_mtm(W["SIG"][True], "H120", 10, np.random.default_rng(RR.P10_SEED0 + r), W["closes"], W["opens"], W["NP"],
                           return_equity=True, stop_force=W["SF"], audit=au)
        sh = hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()[:16]
        bad_sha += int(sh != SC[(SC["世界"] == wn) & (SC["r"] == r)]["eq_sha"].iloc[0])
        ev = {}
        for a in au:
            ev.setdefault(a["t"], []).append(a)
        held = {}; mine = np.full(len(T), -1); buy_amt = {}
        order = np.argsort(E, kind="stable"); tdays = sorted(set(ev) | set(E))
        byday = {}
        for i in order:
            byday.setdefault(int(E[i]), []).append(i)
        for t in tdays:
            for a in ev.get(t, []):
                if a["side"] == "sell":
                    sb = held.pop(a["sid"])
                    net_a = a["amt"] / sb[1] - 1.0 - COST
                    i = int(np.flatnonzero((SID == a["sid"]) & (E == sb[0]))[0])
                    maxd = max(maxd, abs(net_a - NET[i])); nA += 1
            before = dict(held)
            bought = {a["sid"] for a in ev.get(t, []) if a["side"] == "buy"}
            for i in byday.get(t, []):
                s = SID[i]
                mine[i] = 0 if s in bought else (3 if s in before else (2 if len(before) >= 10 else 1))
            for a in ev.get(t, []):
                if a["side"] == "buy":
                    held[a["sid"]] = (t, a["amt"])
        col = CMw[:, r]
        bad_cls += int((mine != col).sum())
        log(f"[Q1 {wn} r{r}] 分類不同 {int((mine != col).sum())}｜A {int((mine == 0).sum())} B {int((mine == 1).sum())} C {int((mine == 2).sum())} D {int((mine == 3).sum())}｜sha {sh}")
    res[f"Q1 {wn} 分類不同筆（抽樣 {len(SEEDS[wn])} 顆）"] = bad_cls
    res[f"Q1 {wn} eq_sha 不同顆"] = bad_sha
    res[f"Q2 {wn} A 淨報酬（金額式）最大差"] = maxd
    res[f"Q2 {wn} 已出場 A 筆數"] = nA


def main():
    log("[查核開始]")
    SIGT = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str})
    CM = np.load(os.path.join(OUT, "classes.npz"))
    SC = pd.read_csv(os.path.join(OUT, "seed_counts.csv.gz"), dtype={"eq_sha": str})
    cells = pd.read_csv(os.path.join(OUT, "cells.csv"))
    res = {}
    Wm, _ = IG.main_world(log)
    hand(Wm, "主", SIGT, res)
    engine_check(Wm, "主", SIGT, CM["主"], SC, res)
    We, _ = IG.early_world(log, 3)
    hand(We, "早年", SIGT, res)
    engine_check(We, "早年", SIGT, CM["早年"], SC, res)
    # Q4
    bad = 0
    for wn in ("主", "早年"):
        T = SIGT[SIGT["世界"] == wn].reset_index(drop=True)
        for sg in SEGS[wn]:
            m = (T["段"] == sg).to_numpy()
            for j, c in enumerate(CLS):
                share = float(np.mean([(CM[wn][m, s] == j).mean() for s in range(CM[wn].shape[1])]))
                v = cells[(cells["世界"] == wn) & (cells["段"] == sg) & (cells["類"].str.startswith(c))]["占比"].iloc[0]
                bad += int(abs(share - v) > 1e-9)
    res["Q4 占比不符格數"] = bad
    log(f"[查核] {json.dumps(res, ensure_ascii=False, default=str)[:3000]}")
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[查核完]")


if __name__ == "__main__":
    main()

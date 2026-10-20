# -*- coding: utf-8 -*-
"""researchExit3_freq 對帳（抽樣手算、不前視、策略鎖）——回測線計算子代理。⛔ 不算任何出場法報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit3_freq_check
輸出 backtest/resultsExit3/freq/check.json、check.log

 E1 交易清單：trades_r0 每筆 (sid, 進場位置) 都在該策略訊號表；出清日 ＝ 訊號表 xpos（或停止交易 L＋1、資料尾未賣）；同一帳戶同日持股數 ≤ 槽數。
 E2 事件：每個世界×策略抽 30 筆交易，逐日迴圈（買價 ＝ 世界還原開盤，無效 ⇒ 收盤）重找 S+／S−／S0_30/40/60 的 T，與 events_r0 逐筆比（含「沒有」）。
 E3 不前視：全部事件 e ≤ T ＜ x；S0_N 的 T ＝ e＋N−1；候選表的 entry_pos ＝ T＋1（＝ 訊號日 T 收盤已知）。
 E4 候選數：抽 60 個事件逐筆迴圈重算（訊號表 entry_pos ＝ T＋1 的代號 − 自己 − 當天仍持有）。
 E5 S0 箱：抽 40 個 S0 事件逐日迴圈重判 先突破／先跌破／都沒有。
 E6 策略鎖 --check；git 已追蹤檔沒有被本件改動。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchExit3_freq as X3               # noqa: E402  只用常數 STR、OUT、RA 路徑（計算一律本檔迴圈重寫）

OUT = X3.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def main():
    res = {}
    WS = {}
    WS["主"], _ = IG.main_world(log)
    WS["早年"], _ = IG.early_world(log, 2)
    import pickle
    from backtest import researchAddOn as RA
    BAD = {}
    for wn, part in (("主", "main"), ("早年", "early")):
        B = pickle.load(open(os.path.join(RA.CRASH_WORK, f"bad_{part}.pkl"), "rb"))
        BAD[wn] = {s: set(int(x) for x in a_) | set(int(x) for x in b_) for s, (a_, b_) in B.items()}
    Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
    EX, _ = RA.early_extra_bad(Wa, lambda *x: None)
    for s, ks in EX.items():
        BAD["早年"].setdefault(s, set()).update(int(k) for k in ks)
    TR = pd.read_csv(os.path.join(OUT, "trades_r0.csv.gz"), dtype={"sid": str})
    EV = pd.read_csv(os.path.join(OUT, "events_r0.csv.gz"), dtype={"sid": str})
    # ── E1
    e1 = []
    for (wn, sn), T in TR.groupby(["世界", "策略"]):
        W = WS[wn]; S = X3.STR[sn]; SIG = W["SIG"][S["G"]]
        xp = {(s, int(e)): int(x) for s, e, x in zip(SIG["sid"], SIG["entry_pos"], SIG[f"xpos_H{S['H']}"])}
        ncal = len(W["cal"])
        for s, e, x in zip(T["sid"], T["e"], T["x"]):
            if (s, int(e)) not in xp:
                e1.append((wn, sn, s, e, "不在訊號表")); continue
            L = W["SF"].get(s)
            ok = (x == xp[(s, e)]) or (x >= ncal and xp[(s, e)] >= ncal - 1) or (L is not None and x == L + 1) or (x >= ncal)
            if not ok:
                e1.append((wn, sn, s, e, x, xp[(s, e)]))
        mx = 0
        for t in np.unique(T["e"]):
            mx = max(mx, int(((T["e"] <= t) & (T["x"] > t)).sum()))
        res[f"E1 {wn}·{sn} 同日最多持股"] = [mx, S.get("N", 20 if sn == "營量" else 10)]
        if mx > (20 if sn == "營量" else 10):
            e1.append((wn, sn, "持股超過槽數", mx))
    res["E1 交易不符"] = len(e1); res["E1 明細"] = e1[:10]
    log(f"[E1] {len(e1)}")
    # ── E2
    rng = np.random.default_rng(20261020)
    e2 = []
    for (wn, sn), T in TR.groupby(["世界", "策略"]):
        W = WS[wn]; last = len(W["cal"]) - 1
        smp = T.sample(min(30, len(T)), random_state=7)
        for s, e, x in zip(smp["sid"], smp["e"], smp["x"]):
            c = W["closes"][s]; bp = float(W["opens"][s][e])
            if not np.isfinite(bp) or bp <= 0:
                bp = float(c[e])
            hi = min(int(x) - 1, last)
            for b in sorted(BAD[wn].get(s, ())):
                if e < b <= min(int(x), last):
                    hi = min(hi, b - 1); break
            got = {}
            t = e; maxr = -9; minr = 9
            while t <= hi:
                r = c[t] / bp - 1
                if "S+" not in got and r >= 0.15:
                    got["S+"] = t
                if "S−" not in got and r <= -0.15:
                    got["S−"] = t
                maxr = max(maxr, r); minr = min(minr, r)
                for N in (30, 40, 60):
                    if t == e + N - 1 and maxr < 0.15 and minr > -0.15:
                        got[f"S0_{N}"] = t
                t += 1
            ev = EV[(EV["世界"] == wn) & (EV["策略"] == sn) & (EV["sid"] == s) & (EV["e"] == e)]
            have = dict(zip(ev["狀態"], ev["T"]))
            if have != got:
                e2.append((wn, sn, s, int(e), have, got))
    res["E2 事件不同（120 筆交易）"] = len(e2); res["E2 明細"] = [str(x) for x in e2[:5]]
    log(f"[E2] {len(e2)}")
    # ── E3
    bad3 = int(((EV["T"] < EV["e"]) | (EV["T"] >= EV["x"])).sum())
    s0 = EV[EV["狀態"].str.startswith("S0")]
    bad3 += int((s0["T"] != s0["e"] + s0["狀態"].str[3:].astype(int) - 1).sum())
    res["E3 不前視違反"] = bad3
    log(f"[E3] {bad3}")
    # ── E4
    e4 = []
    smp = EV.sample(60, random_state=8)
    for r in smp.itertuples(index=False):
        W = WS[r.世界]; S = X3.STR[r.策略]; SIG = W["SIG"][S["G"]]
        X = int(r.T) + 1
        if X > len(W["cal"]) - 1:
            want = -1
        else:
            T = TR[(TR["世界"] == r.世界) & (TR["策略"] == r.策略)]
            held = set()
            for s, e, x in zip(T["sid"], T["e"], T["x"]):
                if e <= X < x:
                    held.add(s)
            cand = [s for s, ep in zip(SIG["sid"], SIG["entry_pos"]) if int(ep) == X]
            want = 0 if not cand else sum(1 for s in cand if s != r.sid and s not in held)
        if want != r.候選數:
            e4.append((r.世界, r.策略, r.sid, r.T, want, r.候選數))
    res["E4 候選數不同（60 筆）"] = len(e4); res["E4 明細"] = e4[:5]
    log(f"[E4] {len(e4)}")
    # ── E5
    e5 = []
    smp = EV[EV["狀態"].str.startswith("S0")].sample(40, random_state=9)
    for r in smp.itertuples(index=False):
        W = WS[r.世界]; c = W["closes"][r.sid]; last = len(W["cal"]) - 1
        e, t = int(r.e), int(r.T)
        up = max(c[e:t + 1]); lo = min(c[e:t + 1])
        end = min(t + 120, last)
        for b in sorted(BAD[r.世界].get(r.sid, ())):
            if b > t:
                end = min(end, b - 1); break
        lab = "都沒有"
        for j in range(t + 1, end + 1):
            if c[j] > up:
                lab = "先突破"; break
            if c[j] < lo:
                lab = "先跌破"; break
        if lab != r.S0箱:
            e5.append((r.世界, r.策略, r.sid, t, lab, r.S0箱))
    res["E5 S0 箱不同（40 筆）"] = len(e5); res["E5 明細"] = e5[:5]
    log(f"[E5] {len(e5)}")
    # ── E6
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--short"], capture_output=True, text=True).stdout.splitlines()
    res["E6 策略鎖"] = (lk.stdout.strip() + lk.stderr.strip())[:200]; res["E6 策略鎖 exit"] = lk.returncode
    res["E6 git 已追蹤檔被改（M）"] = [l for l in gs if l.startswith(" M") or l.startswith("M ")]
    ok = res["E1 交易不符"] == 0 and len(e2) == 0 and bad3 == 0 and len(e4) == 0 and len(e5) == 0 and lk.returncode == 0
    res["全部通過"] = bool(ok)
    log(f"[結論] 全部通過 {ok}｜{res['E6 策略鎖']}")
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

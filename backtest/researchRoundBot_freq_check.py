# -*- coding: utf-8 -*-
"""researchRoundBot_freq 對帳（PREREG圓弧底 seq1 頻率表乾跑，登錄 sha f2488c52d9e96535）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRoundBot_freq_check
輸出 backtest/resultsRoundBot/freq/check.json、check.log

C0 策略鎖（同三重底件）。
C1 S22 與型態全量逐筆：主世界 M 格全部偵測 (sid, T, first＝a) 與已提交 resultsPatAll/events_S22_圓形底.csv.gz（同窗、兩邊都有的股票）逐筆比。
C2 抽樣手算（主、早年各：J 保留 ≤5、M 保留但非 J ≤4；default_rng(20261021)）——⛔ 不呼叫本件條件函式：
   a ＝ [T−250, T−60] 最高收盤（最早）、c[T] ＞ c[a] 且 c[a+1..T−1] ≤ c[a]、np.polyfit 二次 γ＞0、R² ≥ 0.6、頂點在中間三分之一、
   b ＝ c[a..T−1] 最低、b−a ≥ 20、T−b ≥ 20、r60[a] ＜ 0；MA5／MA20 逐根迴圈重算金叉日（b＋1..T）、走平 ±2%、T 前 10 根；
   放量、收紅（原始 csv）、母體、T＋1、還原因子（同三重底件 hand_common）；dd250、120 日線下、量縮（中心 20 根）；格成員 ＝ 條件重算。
C3 不前視：截在 k 重跑 PA.detect_round ⇒ (k, a) 仍在；截在 k−1 ⇒ 沒有 k；隨機 3 截點 S22 逐筆相同。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRoundBot_freq as RB            # noqa: E402
from backtest import researchTripleBot_freq_check as TBC    # noqa: E402  lock_check、patall_compare、hand_common、dd_hand、below_hand
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402
from backtest import patterns_all as PA                     # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = RB.OUT
PATALL_EV = "backtest/resultsPatAll/events_S22_圓形底.csv.gz"
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def ma_loop(c, bad, t, n):
    if t - n + 1 < 0 or any(bad[q] for q in range(t - n + 2, t + 1)):
        return None
    return sum(c[t - n + 1:t + 1]) / n


def main():
    rng = np.random.default_rng(20261021)
    res = {"C0": TBC.lock_check(), "C1": None, "C2": [], "C3": []}; fails = []
    log(f"[C0 策略鎖] {res['C0']}")
    if not res["C0"]["ok"]:
        fails.append({"C0": res["C0"]})
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str}, low_memory=False)
        if wn == "主":
            res["C1"] = TBC.patall_compare(ev, cal, set(W["sids"]), path=PATALL_EV)
            sb = TBC.short_bars(W, {x[0] for x in res["C1"]["只在PatAll例"]}) if res["C1"]["只在PatAll"] <= 10 else set()
            res["C1"]["只在PatAll且本件load_bars不足260根"] = sorted(sb)
            res["C1"]["ok"] = res["C1"]["只在本件"] == 0 and res["C1"]["只在PatAll"] <= 10 and all(x[0] in sb for x in res["C1"]["只在PatAll例"])
            log(f"[C1 S22 與型態全量] {res['C1']}")
            if not res["C1"]["ok"]:
                fails.append({"C1": "S22 與 PatAll 不一致"})
        Mk = ev[(ev["格"] == "M") & (ev["st"] == "保留")]
        Jk = ev[(ev["格"] == "J") & (ev["st"] == "保留")]
        jset = set(zip(Jk["sid"], Jk["T"]))
        nonJ = Mk[[(s, t) not in jset for s, t in zip(Mk["sid"], Mk["T"])]]
        picks = [("J", Jk.iloc[np.sort(rng.choice(len(Jk), min(5, len(Jk)), replace=False))]),
                 ("M非J", nonJ.iloc[np.sort(rng.choice(len(nonJ), min(4, len(nonJ)), replace=False))])]
        for lab, P in picks:
            for _, e in P.iterrows():
                sid = e["sid"]; B, idx, bad = RTC.bars_of(W, sid); df = B["df"]
                c = np.asarray(B["c"], float); o = np.asarray(B["o"], float)
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T))
                a = k - 250 + int(np.argmax(c[k - 250:k - 60 + 1]))
                L = k - 1 - a
                x = np.arange(a, k, dtype=float); y = c[a:k]
                g2, g1, g0 = np.polyfit(x - x.mean(), y, 2)
                yh = np.polyval([g2, g1, g0], x - x.mean()); r2 = 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()
                xv = -g1 / (2 * g2) + x.mean()
                b = a + int(np.argmin(c[a:k]))
                chk = {"a相符": str(cal[idx[a]].date()) == e["a"] == e["first"], "c[T]>c[a]且之前未站上": bool(c[k] > c[a] and (c[a + 1:k] <= c[a]).all()),
                       "γ>0": bool(g2 > 0), "R²≥0.6": bool(r2 >= 0.6), "頂點中間三分之一": bool(a + L / 3 <= xv <= a + 2 * L / 3),
                       "b相符": str(cal[idx[b]].date()) == e["b"], "b−a≥20、T−b≥20": bool(b - a >= 20 and k - b >= 20),
                       "r60[a]<0": bool(c[a - 1] / c[a - 61] - 1 < 0)}
                gx = []
                for t in range(b + 1, k + 1):
                    m5p, m20p, m5, m20 = ma_loop(c, bad, t - 1, 5), ma_loop(c, bad, t - 1, 20), ma_loop(c, bad, t, 5), ma_loop(c, bad, t, 20)
                    if None not in (m5p, m20p, m5, m20) and m5p <= m20p + 1e-9 * abs(m20p) and m5 > m20 + 1e-9 * abs(m20):
                        gx.append(t)
                flat = any((lambda p, q: p is not None and q is not None and abs(p / q - 1) <= 0.02)(ma_loop(c, bad, t - 1, 20), ma_loop(c, bad, t - 21, 20)) for t in gx)
                chk["金叉日數相符"] = len(gx) == int(e["金叉日數"])
                chk["走平後金叉相符"] = flat == bool(e["gx_flat"]); chk["T前10根金叉相符"] = any(t >= k - 9 for t in gx) == bool(e["gx_10"])
                chk.update(TBC.hand_common(W, sid, e, df, idx, bad, T, k))
                dd = TBC.dd_hand(c, bad, b)
                chk["dd250相符"] = (dd is None and pd.isna(e["dd250"])) or (dd is not None and abs(dd - float(e["dd250"])) < 1e-3)
                chk["120線下根數相符"] = TBC.below_hand(c, bad, b) == int(e["線下根數"])
                V = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
                def cm(lo, hi):
                    if lo < 0 or hi >= len(V) or any(bad[q] for q in range(lo + 1, hi + 1)) or not np.isfinite(V[lo:hi + 1]).all():
                        return None
                    return V[lo:hi + 1].mean()
                vb, va = cm(b - 10, b + 9), cm(a - 10, a + 9)
                chk["量縮相符"] = bool((vb is not None and va is not None and vb < va) == bool(e["shrink"]))
                chk["型態期間無壞根"] = not any(bad[q] for q in range(a + 1, k + 1))
                vr = V[k] / V[k - 20:k].mean(); red = c[k] > o[k]
                isJ = bool(len(gx) > 0 and vr >= 1.5 and red and dd is not None and dd <= -0.20)
                chk["格成員＝條件重算"] = isJ == (lab == "J")
                full = PA.detect_round(c, PA._rN(c, 60))["S22"]
                tk = PA.detect_round(c[:k + 1], PA._rN(c[:k + 1], 60))["S22"]
                tk1 = PA.detect_round(c[:k], PA._rN(c[:k], 60))["S22"]
                c3 = {"截在T仍偵測到(T,a)": (k, a) in tk, "截在T−1無此T": all(x_[0] != k for x_ in tk1)}
                okc = True
                for ct in sorted(rng.choice(np.arange(300, len(c)), 3, replace=False).tolist()):
                    tr_ = PA.detect_round(c[:ct + 1], PA._rN(c[:ct + 1], 60))["S22"]
                    okc &= sorted(x_ for x_ in full if x_[0] <= ct) == sorted(tr_)
                c3["隨機截點S22逐筆相同"] = bool(okc)
                b1 = [z for z, v in chk.items() if not v]; b3 = [z for z, v in c3.items() if not v]
                res["C2"].append({"世界": wn, "類": lab, "sid": sid, "T": e["T"], **chk}); res["C3"].append({"世界": wn, "sid": sid, "T": e["T"], **c3})
                if b1 or b3:
                    fails.append({"世界": wn, "類": lab, "sid": sid, "T": e["T"], "C2不符": b1, "C3不符": b3})
                log(f"{wn} {lab} {sid} T={e['T']}｜C2 {'✔' if not b1 else b1}｜C3 {'✔' if not b3 else b3}")
    res["不符"] = fails
    res["結論"] = f"C0 策略鎖、C1 S22 逐筆、C2 {len(res['C2'])} 筆手算、C3 不前視 全部相符" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchKDJ3_freq 對帳（PREREG KDJ三週期共振 seq1 頻率表乾跑，登錄 sha 94378c24e2a8af54）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKDJ3_freq_check
輸出 backtest/resultsKDJ3/freq/check.json、check.log

C0 策略鎖（同三重底件）。
C1 抽樣手算（主、早年各：J 保留 5、D 保留但非 J 5；default_rng(20261022)）——⛔ 不呼叫本件模組、researchWeekly.kd、weekly_bars：
   日線 KD 用 researchWR_freq_check.kd_loop（逐根迴圈、壞根重起）比對 K／D[T−1]、K／D[T]、金叉、K[T−1] ＜ 20、段內位置 ≥ 20；
   週／月 K：pandas 依週一／日曆月把 ≤ T 的有成交列分組（只取在交易日曆上「最後一個交易日 ≤ T」的已收完週／月），
   依壞 K 棒自行分段（壞 K 棒是該週／月第一根 ⇒ 該週／月起新段；否則下一週／月起），逐根迴圈 KD（起始 50），比對值、段內位置 ≥ 20、
   同段（所用週／月的第一根之後到 T 無壞 K 棒）；格成員 ＝ 條件重算；母體、T＋1 可買。
C2 不前視：同上各筆，日曆陣列截在 T（有效 K 棒截在 k）重跑 WR.kd_daily、RW.weekly_bars＋period_kd ⇒ 日、週、月 K 與事件檔相同。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchKDJ3_freq as KJ                # noqa: E402
from backtest import researchTripleBot_freq_check as TBC    # noqa: E402  lock_check
from backtest import researchWR_freq_check as WRC           # noqa: E402  kd_loop、gate_chk、next_open_chk
from backtest import researchWR_freq as WR                  # noqa: E402
from backtest import researchWeekly as RW                   # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = KJ.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def period_hand(cal, df, idx, bad, T, k, kind):
    """回 (K, D, 段內位置, 同段, 該週月第一根日期)；無可用週月 ⇒ None。"""
    key_cal = ((cal - pd.to_timedelta(cal.weekday, unit="D")).normalize() if kind == "w" else cal.to_period("M").to_timestamp())
    key_cal = pd.Series(key_cal, index=range(len(cal)))
    end_of = key_cal.groupby(key_cal).apply(lambda s: s.index.max())          # 交易日曆上每週／月最後一日位置
    rows = [j for j in idx if j <= T]
    kq = {j: q for q, j in enumerate(idx)}
    grp = {}
    for j in rows:
        grp.setdefault(key_cal[j], []).append(j)
    keys = [g for g in sorted(grp) if end_of[g] <= T]
    if not keys:
        return None
    # 分段
    seg_start = 0; inval = set()
    for i_, g in enumerate(keys):
        qs = [kq[j] for j in grp[g]]
        bq = [q for q in qs if bad[q] and q > 0]
        if not bq:
            continue
        if bq[0] == qs[0] and len(bq) == 1:
            seg_start = i_
        else:
            inval.add(i_); seg_start = i_ + 1
    last = len(keys) - 1
    if last in inval or seg_start > last:
        return {"K": None, "D": None, "pos": -1, "same": False, "first": str(cal[grp[keys[last]][0]].date())}
    H = [max(df["high"].iloc[j] for j in grp[g]) for g in keys]; L = [min(df["low"].iloc[j] for j in grp[g]) for g in keys]
    C = [df["close"].iloc[grp[g][-1]] for g in keys]
    k0 = d0 = 50.0; Kv = Dv = None
    for t in range(seg_start, last + 1):
        p = t - seg_start
        if p < 8:
            continue
        lo = min(L[t - 8:t + 1]); hi = max(H[t - 8:t + 1])
        rsv = 50.0 if hi - lo <= 0 else (C[t] - lo) / (hi - lo) * 100.0
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3
    Kv, Dv = (k0, d0) if last - seg_start >= 8 else (None, None)
    fq = kq[grp[keys[last]][0]]
    same = not any(bad[q] for q in range(fq + 1, k + 1))
    return {"K": Kv, "D": Dv, "pos": last - seg_start, "same": same, "first": str(cal[grp[keys[last]][0]].date())}


def main():
    rng = np.random.default_rng(20261022)
    res = {"C0": TBC.lock_check(), "C1": [], "C2": []}; fails = []
    log(f"[C0 策略鎖] {res['C0']}")
    if not res["C0"]["ok"]:
        fails.append({"C0": res["C0"]})
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        wk, wf, wl = RW.weeks_of(cal); mo, mf, ml = KJ.months_of(cal)
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str}, low_memory=False)
        Jk = ev[(ev["格"] == "J") & (ev["st"] == "保留")]
        Dk = ev[(ev["格"] == "D") & (ev["st"] == "保留")]
        jset = set(zip(Jk["sid"], Jk["T"]))
        nonJ = Dk[[(s, t) not in jset for s, t in zip(Dk["sid"], Dk["T"])]]
        picks = [("J", Jk.iloc[np.sort(rng.choice(len(Jk), min(5, len(Jk)), replace=False))]),
                 ("D非J", nonJ.iloc[np.sort(rng.choice(len(nonJ), min(5, len(nonJ)), replace=False))])]
        for lab, P in picks:
            for _, e in P.iterrows():
                sid = e["sid"]; B, idx, bad = RTC.bars_of(W, sid); df = B["df"]; i = W["ix"][sid]
                h, l, c = (np.asarray(B[z], float) for z in ("h", "l", "c"))
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T))
                K, Dd, ps = WRC.kd_loop(h, l, c, bad)
                chk = {"K[T-1]相符": abs(K[k - 1] - e["K[T-1]"]) < 1e-3, "D[T-1]相符": abs(Dd[k - 1] - e["D[T-1]"]) < 1e-3,
                       "K[T]相符": abs(K[k] - e["K[T]"]) < 1e-3, "D[T]相符": abs(Dd[k] - e["D[T]"]) < 1e-3,
                       "日線金叉且K[T−1]<20": bool(K[k - 1] <= Dd[k - 1] and K[k] > Dd[k] and K[k - 1] < 20),
                       "段內位置≥20且T−1同段": bool(ps[k] >= 20 and ps[k - 1] == ps[k] - 1)}
                flags = {}
                for nm in ("w", "m"):
                    r = period_hand(cal, df, idx, bad, T, k, nm)
                    ok20 = r is not None and r["same"] and r["pos"] >= 20 and r["K"] is not None
                    flags[nm] = bool(ok20 and r["K"] < 20)
                    chk[f"{nm}條件相符"] = flags[nm] == bool(e[nm])
                    if ok20:
                        chk[f"{nm}K值相符"] = abs(r["K"] - float(e[nm + "K"])) < 1e-3
                        chk[f"{nm}週月第一根相符"] = r["first"] == e[nm + "日"]
                chk["格成員＝條件重算"] = (flags["w"] and flags["m"]) == (lab == "J")
                chk.update(WRC.gate_chk(W, df, T, i))
                chk["T+1 可買"] = WRC.next_open_chk(W, i, idx, bad, k, T)
                # C2 不前視：截在 T
                Kt, Dt, pt = WR.kd_daily(h[:k + 1], l[:k + 1], c[:k + 1], bad[:k + 1])
                c2 = {"日K截斷相同": abs(Kt[k] - e["K[T]"]) < 1e-3 and abs(Kt[k - 1] - e["K[T-1]"]) < 1e-3}
                o_, h_, l_, c_ = (df[z].to_numpy(float)[:T + 1] for z in ("open", "high", "low", "close"))
                vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[:T + 1]
                valid = np.asarray(df["traded"].to_numpy(), bool)[:T + 1]
                for nm, gid, gl in (("w", wk, wl), ("m", mo, ml)):
                    ids, _, PH, PL, PC, _ = RW.weekly_bars(valid, o_, h_, l_, c_, vol, gid[:T + 1])
                    jq = np.searchsorted(ids, gid[idx[:k + 1]])
                    Kp, Dp, pp, fq = KJ.period_kd(jq, PH, PL, PC, bad[:k + 1])
                    g = int(gid[T]); gmax = g if T == int(gl[g]) else g - 1
                    j = int(np.searchsorted(ids, gmax, "right")) - 1
                    ev_K = e[nm + "K"]
                    kk = Kp[j] if j >= 0 else np.nan
                    c2[f"{nm}K截斷相同"] = bool((pd.isna(ev_K) and not np.isfinite(kk)) or (np.isfinite(kk) and not pd.isna(ev_K) and abs(kk - float(ev_K)) < 1e-3))
                b1 = [z for z, v in chk.items() if not v]; b2 = [z for z, v in c2.items() if not v]
                res["C1"].append({"世界": wn, "類": lab, "sid": sid, "T": e["T"], **chk}); res["C2"].append({"世界": wn, "sid": sid, "T": e["T"], **c2})
                if b1 or b2:
                    fails.append({"世界": wn, "類": lab, "sid": sid, "T": e["T"], "C1不符": b1, "C2不符": b2})
                log(f"{wn} {lab} {sid} T={e['T']}｜C1 {'✔' if not b1 else b1}｜C2 {'✔' if not b2 else b2}")
    res["不符"] = fails
    res["結論"] = f"C0 策略鎖、C1 {len(res['C1'])} 筆手算、C2 不前視 全部相符" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

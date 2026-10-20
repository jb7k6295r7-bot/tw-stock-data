# -*- coding: utf-8 -*-
"""researchTripleBot_freq 對帳（PREREG三重底 seq1 頻率表乾跑，登錄 sha 806f2cd9554b213d）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTripleBot_freq_check
輸出 backtest/resultsTripleBot/freq/check.json、check.log

C0 策略鎖：strategy_lock.check() 無差異（營量／營飆鎖內各支一字未動）；本件新檔不在鎖定閉包內。
C1 S2 與型態全量逐筆：主世界 M 格全部偵測 (sid, T, first)（任何狀態）在窗 [2017-03-02, 2026-08-24 往前 20 個交易日] 內，
   與已提交 resultsPatAll/events_S02_三重底.csv.gz 兩邊都有的股票逐筆比（PatAll 母體 gate3 v1、無 260 根門檻 ⇒ 名單差另報、不算差異）。
C2 抽樣手算（主、早年各：J 保留 5、M 保留但非 J 4；default_rng(20261020)）——⛔ 不呼叫本件模組的條件函式，用日曆 df 逐列與原始 csv 重算：
   三底等低 ≤ 5%、反彈高點 ≥ 10%、三底是 k＝3 局部低點、T 為第三底確認（L3＋3）後第一個收盤 ＞ C_A、T − L1 ＋ 1 ≤ 60、r60[L1] ＜ 0；
   vr20／vr5（日曆 df 有成交列）、收紅（原始 csv 收 ＞ 開）、dd250（壞根後截短）、120 日線下根數、量縮；格成員 ＝ 條件重算；
   母體（自算 500 張、pit）、型態期間無壞根、T＋1 可買、高低收同一還原因子。
C3 不前視：同上各筆，有效 K 棒截在 k 重跑 PA.detect_turns ⇒ (k, first) 仍在；截在 k−1 ⇒ 沒有 k；條件函式（vol_ratio、longdown、below_run）
   以截斷陣列重算 ＝ 事件檔值；另每檔 3 個隨機截點：全序列 S2 中 ≤ 截點者 ＝ 截斷序列 S2（逐筆）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTripleBot_freq as TB           # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of
from backtest import researchWR_freq_check as WRC           # noqa: E402  gate_chk、next_open_chk、adj_chk
from backtest import patterns_all as PA                     # noqa: E402
from backtest import strategy_lock as SL                    # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = TB.OUT
PATALL_EV = "backtest/resultsPatAll/events_S02_三重底.csv.gz"
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def lock_check():
    d = SL.check(); clo = SL.closure()
    mine = ("researchTripleBot_freq", "researchRoundBot_freq", "researchKDJ3_freq")
    return {"差異": d, "鎖定支數": len(clo), "本件新檔在閉包內": [m for m in mine if m in clo], "ok": (not d) and not any(m in clo for m in mine)}


def patall_compare(ev, cal, wn_ok, vid_cell="M", path=PATALL_EV):
    pe = pd.read_csv(path, dtype={"sid": str})
    w0 = int(cal.searchsorted(pd.Timestamp("2017-03-02"))); w1 = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    lo, hi = str(cal[w0].date()), str(cal[w1 - 20].date())
    A = ev[ev["格"] == vid_cell]
    mine = {(s, t, f) for s, t, f in zip(A["sid"], A["T"], A["first"]) if lo <= t <= hi}
    common = set(pe["sid"]) & wn_ok
    theirs = {(s, t, f) for s, t, f in zip(pe["sid"], pe["T"], pe["first"]) if s in common}
    mine_c = {x for x in mine if x[0] in common}
    return {"PatAll事件數": int(len(pe)), "兩邊都有的股票": len(common), "PatAll（共同股）": len(theirs), "本件（共同股、同窗）": len(mine_c),
            "只在PatAll": len(theirs - mine_c), "只在本件": len(mine_c - theirs), "只在PatAll例": sorted(theirs - mine_c)[:10],
            "只在本件例": sorted(mine_c - theirs)[:10], "本件有、PatAll母體沒有的股票事件數": len([x for x in mine if x[0] not in set(pe["sid"])]),
            "PatAll有、本件母體沒有的股票事件數": int(sum(1 for s in pe["sid"] if s not in wn_ok)), "ok": theirs == mine_c}


def same_nan(a, b):
    return bool((np.isnan(a) and np.isnan(b)) or a == b)


def short_bars(W, sids):
    """名單差：load_bars ＜ 260 根（本件母體不進）的股票。"""
    from backtest import research11 as R
    from backtest import data as D
    D.DATA = W["data"]
    return {s for s in sids if R.load_bars(s, W["mk"].get(s, "twse"), W["cal"]) is None}


def raw_oc(W, sid, T):
    raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
    raw["date"] = pd.to_datetime(raw["date"]); rr = raw.set_index("date").loc[W["cal"][T]]
    return float(rr["open"]), float(rr["close"])


def hand_common(W, sid, e, df, idx, bad, T, k):
    """放量、收紅、母體、T＋1（兩件共用）。"""
    trd = df["traded"].to_numpy(bool); V = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    rows = [j for j in range(T + 1) if trd[j]]
    chk = {}
    for n, key in ((20, "vr20"), (5, "vr5")):
        win = rows[-(n + 1):-1]
        kk = [int(np.searchsorted(idx, j)) for j in rows[-(n + 1):]]
        okc = len(win) == n and not any(bad[q] for q in kk[1:]) and np.isfinite(V[win]).all() and np.mean(V[win]) > 0
        vr = V[T] / np.mean(V[win]) if okc else None
        chk[f"{key}相符"] = (vr is None and pd.isna(e[key])) or (vr is not None and abs(vr - float(e[key])) < 1e-3)
    ro, rc = raw_oc(W, sid, T)
    chk["收紅相符(原始csv)"] = bool((rc > ro) == bool(e["收紅"]))
    i = W["ix"][sid]
    chk.update(WRC.gate_chk(W, df, T, i))
    chk["T+1 可買"] = WRC.next_open_chk(W, i, idx, bad, k, T)
    chk["高低收同一還原因子"] = WRC.adj_chk(W, sid, df, T)
    return chk


def dd_hand(c, bad, kb):
    s0 = max([j for j in range(kb + 1) if bad[j]] + [0])         # kb 所在無壞根段的第一根
    lo = max(kb - 249, s0)
    if kb - lo + 1 < 60:
        return None
    return c[kb] / max(c[lo:kb + 1]) - 1.0


def below_hand(c, bad, kb):
    r = 0; j = kb
    while j >= 119:
        if any(bad[q] for q in range(j - 118, j + 1)):
            break
        if not c[j] < sum(c[j - 119:j + 1]) / 120.0:
            break
        r += 1; j -= 1
    return r


def main():
    rng = np.random.default_rng(20261020)
    res = {"C0": lock_check(), "C1": None, "C2": [], "C3": []}; fails = []
    log(f"[C0 策略鎖] {res['C0']}")
    if not res["C0"]["ok"]:
        fails.append({"C0": res["C0"]})
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str}, low_memory=False)
        if wn == "主":
            fq = json.load(open(os.path.join(OUT, "freq.json"), encoding="utf-8"))
            ok_sids = set(W["sids"])
            res["C1"] = patall_compare(ev, cal, ok_sids)
            sb = short_bars(W, {x[0] for x in res["C1"]["只在PatAll例"]}) if res["C1"]["只在PatAll"] <= 10 else set()
            res["C1"]["只在PatAll且本件load_bars不足260根"] = sorted(sb)
            res["C1"]["ok"] = res["C1"]["只在本件"] == 0 and res["C1"]["只在PatAll"] <= 10 and all(x[0] in sb for x in res["C1"]["只在PatAll例"])
            log(f"[C1 S2 與型態全量] {res['C1']}")
            if not res["C1"]["ok"]:
                fails.append({"C1": "S2 與 PatAll 不一致"})
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
                kq = lambda d: int(np.searchsorted(idx, pos[d]))
                L1, L2, L3, kf = kq(e["L1"]), kq(e["L2"]), kq(e["L3"]), kq(e["first"])
                v3 = c[[L1, L2, L3]]; mn = v3.min()
                cA = max(c[L1:L3 + 1].max(), 0)
                chk = {"first＝L1": kf == L1, "三底等低≤5%": bool((v3.max() - mn) / mn <= 0.05),
                       "反彈≥10%": bool((max(c[L1:L2 + 1].max(), c[L2:L3 + 1].max()) - mn) / mn >= 0.10),
                       "三底是k=3局部低點": all(c[L] <= c[max(0, L - 3):L + 4].min() for L in (L1, L2, L3)),
                       "同類間隔≥5": bool(L2 - L1 >= 5 and L3 - L2 >= 5),
                       "T是確認後第一個收盤>C_A": bool(c[k] > cA and k >= L3 + 3 and all(c[t] <= cA for t in range(L3 + 3, k))),
                       "T−L1+1≤60": bool(k - L1 + 1 <= 60), "r60[L1]<0": bool(c[L1 - 1] / c[L1 - 61] - 1 < 0)}
                chk.update(hand_common(W, sid, e, df, idx, bad, T, k))
                dd = dd_hand(c, bad, L1)
                chk["dd250相符"] = (dd is None and pd.isna(e["dd250"])) or (dd is not None and abs(dd - float(e["dd250"])) < 1e-3)
                chk["120線下根數相符"] = below_hand(c, bad, L1) == int(e["線下根數"])
                V = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
                chk["量縮相符"] = bool((np.isfinite(V[L3]) and np.isfinite(V[L1]) and V[L3] < V[L1]) == bool(e["shrink"]))
                chk["型態期間無壞根"] = not any(bad[q] for q in range(kf + 1, k + 1))
                vr = V[k] / V[k - 20:k].mean(); red = c[k] > o[k]
                isJ = bool(vr >= 1.5 and red and dd is not None and dd <= -0.20)
                chk["格成員＝條件重算"] = isJ == (lab == "J")
                # C3 不前視
                cd = c
                full = PA.detect_turns(cd, PA._rN(cd, 60))["S02"]
                tk = PA.detect_turns(cd[:k + 1], PA._rN(cd[:k + 1], 60))["S02"]
                tk1 = PA.detect_turns(cd[:k], PA._rN(cd[:k], 60))["S02"]
                c3 = {"截在T仍偵測到(T,first)": (k, kf) in tk, "截在T−1無此T": all(x[0] != k for x in tk1),
                      "vol_ratio截斷相同": TB.vol_ratio(V[:k + 1], bad[:k + 1], k, 20) == TB.vol_ratio(V, bad, k, 20) or
                      (np.isnan(TB.vol_ratio(V[:k + 1], bad[:k + 1], k, 20)) and np.isnan(TB.vol_ratio(V, bad, k, 20))),
                      "longdown截斷相同": same_nan(TB.longdown(c[:L1 + 1], TB.seg_start(bad[:L1 + 1]), L1)[0], TB.longdown(c, TB.seg_start(bad), L1)[0]),
                      "below_run截斷相同": TB.below_run(c[:L1 + 1], bad[:L1 + 1], L1) == TB.below_run(c, bad, L1)}
                okc = True
                for ct in sorted(rng.choice(np.arange(100, len(cd)), 3, replace=False).tolist()):
                    tr_ = PA.detect_turns(cd[:ct + 1], PA._rN(cd[:ct + 1], 60))["S02"]
                    okc &= sorted(x for x in full if x[0] <= ct) == sorted(tr_)
                c3["隨機截點S2逐筆相同"] = bool(okc)
                b1 = [z for z, v in chk.items() if not v]; b3 = [z for z, v in c3.items() if not v]
                res["C2"].append({"世界": wn, "類": lab, "sid": sid, "T": e["T"], **chk}); res["C3"].append({"世界": wn, "sid": sid, "T": e["T"], **c3})
                if b1 or b3:
                    fails.append({"世界": wn, "類": lab, "sid": sid, "T": e["T"], "C2不符": b1, "C3不符": b3})
                log(f"{wn} {lab} {sid} T={e['T']}｜C2 {'✔' if not b1 else b1}｜C3 {'✔' if not b3 else b3}")
    res["不符"] = fails
    res["結論"] = f"C0 策略鎖、C1 S2 逐筆、C2 {len(res['C2'])} 筆手算、C3 不前視 全部相符" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

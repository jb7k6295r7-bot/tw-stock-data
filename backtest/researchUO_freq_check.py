# -*- coding: utf-8 -*-
"""researchUO_freq 對帳（UO 底背離 seq1 頻率表，登錄 sha 5982a1082147efef）——回測線計算子代理。⛔ 不讀、不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUO_freq_check
輸出 backtest/resultsUO/freq/check.json、check.log

C1 抽 20 筆 A 格保留事件（主 12、早年 8；default_rng(20261017)）逐筆用【自寫逐根迴圈】重算（⛔ 不呼叫 researchUO_freq 的 uo／pivots／detect）：
   UO（BP、TR、A7／A14／A28、4/2/1；[k−27, k] 有壞 K 棒 ⇒ 無值）、收盤轉折低點（左右各 5 根嚴格較高、[s−4, s＋5] 無壞 K 棒）、
   P1 為 P2 前最近的有效轉折、①（P2−P1 ≤ 60、c[P2] ＜ c[P1]、UO(P2) ＞ UO(P1)）、②（min UO[P1..P2] ＜ 30）、
   ③（T ∈ [conf＋1, conf＋20]、UO[T] ＞ max、窗內 T 之前都 ≤ max）、事件檔 UO 值相符（|差| ＜ 1e−8）、
   母體（自算 T−20～T−1 日均量 ≥ 500,000 股 ∧ 含 T 的 20 日都有成交 ∧ pit_valid）、T＋1 有成交且非開盤鎖漲停、
   還原口徑（原始 csv：T 當天 還原收盤／原始收盤 ＝ 還原高／原始高 ＝ 還原低／原始低）。
C2 不前視：同 20 檔，把有效 K 棒截在 T（只留 ≤ T）重跑 researchUO_freq 的偵測 ⇒ 該事件仍在、P1／P2 相同；截在 T−1 ⇒ 該 T 不在。
   另每檔取 3 個隨機截點 cut：全序列偵測中 T ≤ cut 的事件 ＝ 截斷序列偵測的全部事件（逐筆相同）。
C3 同 20 檔全序列：模組 uo() 與自寫迴圈 UO 逐根最大差；模組 D2 事件 ＝ 自寫穿越事件。
"""
from __future__ import annotations

import gzip
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchUO_freq as RU                  # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = RU.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def uo_loop(h, l, c, bad):
    n = len(c); U = np.full(n, np.nan)
    for k in range(28, n):
        if any(bad[j] for j in range(k - 27, k + 1)):
            continue
        A = {}
        okk = True
        for w in (7, 14, 28):
            sb = 0.0; st = 0.0
            for j in range(k - w + 1, k + 1):
                pc = c[j - 1]
                lo = l[j] if l[j] < pc else pc
                hi = h[j] if h[j] > pc else pc
                sb += c[j] - lo; st += hi - lo
            if not st > 0:
                okk = False; break
            A[w] = sb / st
        if okk:
            U[k] = 100.0 * (4 * A[7] + 2 * A[14] + A[28]) / 7.0
    return U


def piv_loop(c, bad):
    n = len(c); out = []
    for s in range(5, n - 5):
        if all(c[j] > c[s] for j in range(s - 5, s)) and all(c[j] > c[s] for j in range(s + 1, s + 6)):
            if not any(bad[j] for j in range(s - 4, s + 6)):
                out.append(s)
    return out


def bars_of(W, sid):
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"])
    idx = B["idx"].astype(np.int64); nb = len(idx)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    return B, idx, bad


def main():
    rng = np.random.default_rng(20261017)
    res = {"C1": [], "C2": [], "C3": []}; fails = []
    for wn, m in (("主", 12), ("早年", 8)):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        A = ev[(ev["格"] == "A") & (ev["st"] == "保留")].reset_index(drop=True)
        pick = A.iloc[np.sort(rng.choice(len(A), m, replace=False))]
        for _, e in pick.iterrows():
            sid = e["sid"]; B, idx, bad = bars_of(W, sid)
            h, l, c = (np.asarray(B[k], float) for k in ("h", "l", "c")); df = B["df"]
            T = pos[e["T"]]; P1 = pos[e["P1"]]; P2 = pos[e["P2"]]
            k = int(np.searchsorted(idx, T)); k1 = int(np.searchsorted(idx, P1)); k2 = int(np.searchsorted(idx, P2))
            U = uo_loop(h, l, c, bad); pv = piv_loop(c, bad)
            chk = {}
            chk["P1、P2 是轉折"] = (k1 in pv) and (k2 in pv)
            chk["P1 緊鄰 P2"] = bool(k1 in pv and k2 in pv and pv.index(k2) == pv.index(k1) + 1)
            chk["P2−P1≤60"] = k2 - k1 <= 60
            chk["c[P2]<c[P1]"] = bool(c[k2] < c[k1])
            seg = U[k1:k2 + 1]
            chk["UO[P1..P2] 有值"] = bool(np.isfinite(seg).all())
            chk["UO(P2)>UO(P1)"] = bool(U[k2] > U[k1])
            chk["min UO<30"] = bool(np.nanmin(seg) < 30)
            M = np.nanmax(seg); conf = k2 + 5
            chk["T∈[conf+1,conf+20]"] = conf + 1 <= k <= conf + 20
            chk["UO[T]>max"] = bool(U[k] > M)
            chk["T 是窗內第一個"] = bool(all(np.isfinite(U[t]) and U[t] <= M for t in range(conf + 1, k)))
            chk["UO 值相符"] = bool(abs(U[k1] - e["uoP1"]) < 1e-8 and abs(U[k2] - e["uoP2"]) < 1e-8 and abs(U[k] - e["uoT"]) < 1e-8
                                and abs(np.nanmin(seg) - e["uoMin"]) < 1e-8 and abs(M - e["uoMax"]) < 1e-8)
            vol = df["volume"].to_numpy(float); trd = df["traded"].to_numpy(bool)
            chk["母體 500 張"] = bool(trd[T - 19:T + 1].all() and np.nanmean(vol[T - 20:T]) >= 500_000 and np.isfinite(vol[T - 20:T]).all())
            chk["pit_valid"] = bool(W["PV"][W["ix"][sid]][T])
            chk["T+1 可買"] = bool(k + 1 < len(idx) and idx[k + 1] == T + 1 and W["TRD"][W["ix"][sid]][T + 1]
                                 and not W["UPL"][W["ix"][sid]][T + 1] and not bad[k + 1])
            raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
            raw["date"] = pd.to_datetime(raw["date"]); rr = raw.set_index("date").loc[cal[T]]
            fc, fh, fl = df["close"].iloc[T] / float(rr["close"]), df["high"].iloc[T] / float(rr["high"]), df["low"].iloc[T] / float(rr["low"])
            chk["高低收同一還原因子"] = bool(abs(fc - fh) < 1e-9 * max(1, fc) and abs(fc - fl) < 1e-9 * max(1, fc))
            # C2 不前視
            def run(kk):
                hh, ll, cc, bb = h[:kk + 1], l[:kk + 1], c[:kk + 1], bad[:kk + 1]
                Uu = RU.uo(hh, ll, cc, bb); pp = RU.pivots(cc, bb)
                return RU.detect(cc, Uu, pp)
            e_full = RU.detect(c, RU.uo(h, l, c, bad), RU.pivots(c, bad))
            tr_at = run(k); tr_bef = run(k - 1)
            c2 = {"截在T仍偵測到且P1P2同": any(t == k and p1 == k1 and p2 == k2 for t, p1, p2, _ in tr_at),
                  "截在T−1無此T": not any(t == k for t, *_ in tr_bef)}
            cuts = sorted(rng.choice(np.arange(60, len(c)), 3, replace=False).tolist())
            c2["隨機截點逐筆相同"] = all(sorted(x for x in e_full if x[0] <= ct) == sorted(run(ct)) for ct in cuts)
            # C3
            Um = RU.uo(h, l, c, bad)
            both = np.isfinite(Um) & np.isfinite(U)
            c3 = {"uo有值位置相同": bool((np.isfinite(Um) == np.isfinite(U)).all()), "uo最大差": float(np.max(np.abs(Um[both] - U[both]))) if both.any() else 0.0,
                  "轉折相同": RU.pivots(c, bad) == pv,
                  "D2相同": RU.detect_d2(Um) == [kk for kk in range(1, len(U)) if np.isfinite(U[kk - 1]) and np.isfinite(U[kk]) and U[kk - 1] < 30 <= U[kk]]}
            c3["ok"] = c3["uo有值位置相同"] and c3["uo最大差"] < 1e-8 and c3["轉折相同"] and c3["D2相同"]
            r1 = {"世界": wn, "sid": sid, "T": e["T"], "P1": e["P1"], "P2": e["P2"], "UO(P1)": round(U[k1], 3), "UO(P2)": round(U[k2], 3),
                  "minUO": round(float(np.nanmin(seg)), 3), "maxUO": round(float(M), 3), "UO(T)": round(U[k], 3), "T−conf(根)": k - conf, **chk}
            res["C1"].append(r1); res["C2"].append({"世界": wn, "sid": sid, "T": e["T"], "截點": cuts, **c2}); res["C3"].append({"世界": wn, "sid": sid, **c3})
            bad1 = [x for x, v in chk.items() if not v]; bad2 = [x for x, v in c2.items() if not v]
            if bad1 or bad2 or not c3["ok"]:
                fails.append({"sid": sid, "T": e["T"], "C1不符": bad1, "C2不符": bad2, "C3": c3})
            log(f"{wn} {sid} T={e['T']} P1={e['P1']} P2={e['P2']} UO {U[k1]:.2f}→{U[k2]:.2f} min {np.nanmin(seg):.2f} max {M:.2f} T:{U[k]:.2f} "
                f"T−conf={k - conf}｜C1 {'✔' if not bad1 else bad1}｜C2 {'✔' if not bad2 else bad2}｜C3 {'✔' if c3['ok'] else c3}")
    res["不符"] = fails
    res["結論"] = "20 筆全部相符" if not fails else f"{len(fails)} 筆不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

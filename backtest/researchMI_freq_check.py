# -*- coding: utf-8 -*-
"""researchMI_freq 對帳（Mass Index 反轉凸起 seq1 頻率表乾跑，登錄 sha 356f3ccfda10a90f）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMI_freq_check
輸出 backtest/resultsMI/freq/check.json、check.log

C1 抽 20 筆保留事件（主：A 6、D1_26 2、D2_無方向 2；早年同；default_rng(20261018)），逐筆用【日曆 df 逐列】取有成交日的還原高低收、
   本檔獨立逐根迴圈（⛔ 不呼叫 researchMI_freq 的 indicators／bulges／ema_sma_seed）重算 E1、E2、MI、EMA9(收盤)：
   事件檔 MI[T−1]、MI[T]、EMA9c[T−1]、EMA9c[T]、凸起開始日、MI峰值 相符；MI[開始−1] ≤ 27 ＜ MI[開始]；開始＋1 … T−1 的 MI 都有效且 ≥ 門檻；
   MI[T] ＜ 門檻（A／D2 26.5、D1 26.0）；開始之前最近一次「≤27→＞27」之後已有完成或缺值（＝ 本檔獨立狀態機含此 (開始, T)）；
   A／D1：EMA9c[T] ＜ EMA9c[T−1]；段內位置 ≥ 60（[T−60, T] 無壞 K 棒）；母體（自算 500 張 ∧ 20 日有成交 ∧ pit_valid）；T＋1 可買；高低收同一還原因子。
C2 不前視：同 20 檔，截在 k ⇒ k 仍在；截在 k−1 ⇒ 沒有 k；另每檔 3 個隨機截點：全序列 A、D1、D2 偵測中 ≤ cut 者 ＝ 截斷序列偵測（逐筆相同）。
C3 指標逐根：同 20 檔全序列，模組 MI、EMA9c 與本檔逐根迴圈版比對（有值位置相同、最大差 ＜ 1e−9）。
   ⚠ venv 無第三方 Mass Index 套件 ⇒ 只能自寫兩份互對，未與第三方實作對帳。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchMI_freq as MF                  # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of（⛔ 只 import）
from backtest import researchWR_freq_check as WC            # noqa: E402  gate_chk／adj_chk／next_open_chk（⛔ 只 import）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = MF.OUT
LOG = []
THR = {"A": 26.5, "D1_26": 26.0, "D2_無方向": 26.5}


def log(s):
    print(s, flush=True); LOG.append(str(s))


# ═════════════ 獨立逐根版 ═════════════
def loop_ind(h, l, c, bad, n=9, w=25, warm=60):
    N = len(c); MI = np.full(N, np.nan); EC = np.full(N, np.nan); POS = np.zeros(N, np.int64)
    a = 2.0 / (n + 1)
    s = 0; buf1 = []; buf2 = []; bufc = []; e1 = e2 = ec = None; rat = []
    for t in range(N):
        if t == 0 or bad[t]:
            s = t; buf1 = []; buf2 = []; bufc = []; e1 = e2 = ec = None; rat = []
        POS[t] = t - s
        x = h[t] - l[t]
        if e1 is None:
            buf1.append(x)
            if len(buf1) == n:
                e1 = sum(buf1) / n
        else:
            e1 = e1 + a * (x - e1)
        if e1 is not None:
            if e2 is None:
                buf2.append(e1)
                if len(buf2) == n:
                    e2 = sum(buf2) / n
            else:
                e2 = e2 + a * (e1 - e2)
        if ec is None:
            bufc.append(c[t])
            if len(bufc) == n:
                ec = sum(bufc) / n
        else:
            ec = ec + a * (c[t] - ec)
        if ec is not None:
            EC[t] = ec
        if e2 is not None and e2 > 0:
            rat.append(e1 / e2)
            if len(rat) >= w and t - s >= warm:
                MI[t] = sum(rat[-w:])
        elif e2 is not None:
            rat.append(np.nan)
    return MI, EC, POS


def loop_bulge(MI, dn, up=27.0):
    out = []; armed = False; k0 = -1
    for k in range(1, len(MI)):
        if not np.isfinite(MI[k]):
            armed = False; continue
        if armed:
            if MI[k] < dn:
                out.append((k0, k)); armed = False
            continue
        if np.isfinite(MI[k - 1]) and MI[k - 1] <= up < MI[k]:
            armed = True; k0 = k
    return out


def mod_det(cell, h, l, c, bad):
    MI, EC, *_ = MF.indicators(h, l, c, bad)
    done, _, _ = MF.bulges(MI, THR[cell])
    return [t for (t, k0, pk) in done if cell == "D2_無方向" or MF.down(EC, t)]


def main():
    rng = np.random.default_rng(20261018)
    res = {"C1": [], "C2": [], "C3": []}; fails = []
    for wn, plan in (("主", (("A", 6), ("D1_26", 2), ("D2_無方向", 2))), ("早年", (("A", 6), ("D1_26", 2), ("D2_無方向", 2)))):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        for cell, m in plan:
            A = ev[(ev["格"] == cell) & (ev["st"] == "保留")].reset_index(drop=True)
            pick = A.iloc[np.sort(rng.choice(len(A), m, replace=False))]
            thr = THR[cell]
            for _, e in pick.iterrows():
                sid = e["sid"]; B, idx, bad = RTC.bars_of(W, sid); df = B["df"]; i = W["ix"][sid]
                h, l, c = (np.asarray(B[z], float) for z in ("h", "l", "c"))
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T))
                # 日曆 df 逐列：有成交日 ⇒ 有效 K 棒
                trd = df["traded"].to_numpy(bool)
                bars = np.flatnonzero(trd)
                Hc, Lc, Cc = (df[z].to_numpy(float)[bars] for z in ("high", "low", "close"))
                chk = {"有效K棒＝df有成交列": bool(len(bars) == len(idx) and (bars == idx).all())}
                MI, EC, POS = loop_ind(Hc, Lc, Cc, bad)
                k0 = int(np.searchsorted(idx, pos[e["凸起開始日"]]))
                eq = lambda a_, b_: bool(abs(a_ - b_) < 1e-9)
                chk["MI[T-1]相符"] = eq(MI[k - 1], e["MI[T-1]"]); chk["MI[T]相符"] = eq(MI[k], e["MI[T]"])
                chk["EMA9c[T-1]相符"] = eq(EC[k - 1], e["EMA9c[T-1]"]); chk["EMA9c[T]相符"] = eq(EC[k], e["EMA9c[T]"])
                chk["MI峰值相符"] = eq(float(np.max(MI[k0:k + 1])), e["MI峰值"])
                chk["開始：MI[開始−1]≤27＜MI[開始]"] = bool(MI[k0 - 1] <= 27.0 < MI[k0])
                mid = MI[k0 + 1:k]
                chk["開始+1…T−1 有效且≥門檻"] = bool(np.isfinite(mid).all() and (mid >= thr).all())
                chk["MI[T]＜門檻"] = bool(MI[k] < thr)
                chk["獨立狀態機含(開始,T)"] = (k0, k) in loop_bulge(MI, thr)
                if cell != "D2_無方向":
                    chk["EMA9c下彎"] = bool(EC[k] < EC[k - 1])
                chk["段內位置≥60"] = bool(POS[k] >= 60 and not bad[k - 60 + 1:k + 1].any() if k >= 60 else False)
                chk.update(WC.gate_chk(W, df, T, i))
                chk["T+1 可買"] = WC.next_open_chk(W, i, idx, bad, k, T)
                chk["高低收同一還原因子"] = WC.adj_chk(W, sid, df, T)
                # C2
                c2 = {"截在T仍偵測到": k in mod_det(cell, h[:k + 1], l[:k + 1], c[:k + 1], bad[:k + 1]),
                      "截在T−1無此T": k not in mod_det(cell, h[:k], l[:k], c[:k], bad[:k])}
                cuts = sorted(rng.choice(np.arange(80, len(c)), 3, replace=False).tolist())
                okc = True
                for ct in cuts:
                    for cc in THR:
                        okc &= [z for z in mod_det(cc, h, l, c, bad) if z <= ct] == mod_det(cc, h[:ct + 1], l[:ct + 1], c[:ct + 1], bad[:ct + 1])
                c2["隨機截點偵測逐筆相同"] = bool(okc)
                # C3
                Mm, Em, *_ = MF.indicators(h, l, c, bad)
                c3 = {}
                for nm, a_, b_ in (("MI", Mm, MI), ("EMA9c", Em, EC)):
                    same = bool((np.isfinite(a_) == np.isfinite(b_)).all()); both = np.isfinite(a_) & np.isfinite(b_)
                    c3[nm + "有值位置同"] = same; c3[nm + "最大差"] = float(np.max(np.abs(a_[both] - b_[both]))) if both.any() else 0.0
                c3["MI範圍"] = [round(float(np.nanmin(Mm)), 3), round(float(np.nanmax(Mm)), 3)]
                c3["ok"] = c3["MI有值位置同"] and c3["EMA9c有值位置同"] and max(c3["MI最大差"], c3["EMA9c最大差"]) < 1e-9
                res["C1"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "凸起開始日": e["凸起開始日"], **chk})
                res["C2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "截點": cuts, **c2})
                res["C3"].append({"世界": wn, "sid": sid, **c3})
                b1 = [z for z, v_ in chk.items() if not v_]; b2 = [z for z, v_ in c2.items() if not v_]
                if b1 or b2 or not c3["ok"]:
                    fails.append({"格": cell, "sid": sid, "T": e["T"], "C1不符": b1, "C2不符": b2, "C3": c3})
                log(f"{wn} {cell} {sid} 開始={e['凸起開始日']} T={e['T']} MI[T]={e['MI[T]']:.3f}｜C1 {'✔' if not b1 else b1}｜C2 {'✔' if not b2 else b2}"
                    f"｜C3 {'✔' if c3['ok'] else c3}（MI 差 {c3['MI最大差']:.1e}、EMA 差 {c3['EMA9c最大差']:.1e}）")
    res["不符"] = fails
    res["結論"] = f"{len(res['C1'])} 筆全部相符" if not fails else f"{len(fails)} 筆不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

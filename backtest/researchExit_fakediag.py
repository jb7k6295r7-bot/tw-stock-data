# -*- coding: utf-8 -*-
"""PREREG出場訊號 假訊號臂的診斷（⛔ 描述、⛔ 不進判定、⛔ 不改登錄的假訊號臂）。

緣由：本體假訊號臂（seq159 預設：同檔、全窗、排除真事件前後各 20 日）的假 E 遠高於真 E。
   ⇒ 疑「排除真事件【之後】20 日」等於用了未來資訊挑日子：未來 20 日內沒有跌破（保留事件）的日子，本來就是之後走勢好的日子。
診斷：同一檔、同一格 (訊號, H)、同一套可落日（有效 K 棒、至該日 ≥ 80 根、T ∈ [窗起點, 窗尾−H]），【每一天】都當訊號日
   （⛔ 不抽樣、⛔ 不合併；賣出遞延、終點、[T−60, 終點] 斷點與本體同一套 exit_signal 陣列），算 R_H 的等權平均，四種排除：
   A 不排除｜B 排除前後各 20 日（＝ 登錄的假訊號臂母體）｜C 只排除「之前 20 日內有真事件」（真事件 ∈ [T−20, T)，不用未來）
   D 只排除「之後 20 日內有真事件」（真事件 ∈ (T, T＋20]，用了未來）
   真事件 ＝ 該格保留事件（與本體 B4 同）；B、C、D 皆另排除 T 本身是真事件的日子。
"""
from __future__ import annotations
import os, sys, json, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExit as RX
from backtest import exit_signal as XS

_G = {}


def _init(cal, w0, w1, off):
    _G.update(cal=cal, w0=w0, w1=w1, off=off)


def work(args):
    sid, market = args
    cal, w0, w1, off = _G["cal"], _G["w0"], _G["w1"], _G["off"]
    P = RX.prep(sid, market, cal, off)
    if P is None:
        return None
    X = P["X"]; bars = P["bars"]; n = len(cal)
    ev, _ = RX.events_of(P)
    out = np.zeros((3, 2, 4, 2))
    base = bars[X["nb"][bars] >= XS.MIN_BARS]
    for gi, g in enumerate(XS.SIGS):
        for hi, H in enumerate(RX.H_JUDGE):
            st = XS.statuses(ev[("close", g)], H, X, w0, w1)
            Tk = np.array(sorted(r["T"] for r in st if r["狀態"] == "保留"), int)
            T = base[(base >= w0) & (base <= w1 - H)]
            if len(T) == 0:
                continue
            s = X["nxt"][np.minimum(T + 1, n - 1)]
            ok = s >= 0
            x = np.where(ok, s + H - 1, 0); ok &= x < n
            a = np.maximum(0, T - XS.BRK_BACK)
            cpb, cg5 = X["cs_pb"], X["cs_g5"]
            def cnt(cs, lo, hi_):
                v = cs[np.clip(hi_, 0, n - 1)] - np.where(lo > 0, cs[np.clip(lo - 1, 0, n - 1)], 0)
                return np.where(hi_ >= lo, v, 0)
            br = (cnt(cpb, a, x) > 0) | (cnt(cg5, a + 4, x) > 0)
            ok &= ~br
            j = X["lv"][np.clip(x, 0, n - 1)]
            R = np.where(ok, P["c"][j] / P["o"][np.clip(s, 0, n - 1)] - 1.0, np.nan)
            if len(Tk):
                k = np.searchsorted(Tk, T, side="left")
                # 之前 20 日內（含 T）有真事件：最大的 Tk ≤ T 滿足 T − Tk ≤ 20
                kr = np.searchsorted(Tk, T, side="right") - 1
                before = (kr >= 0) & (T - Tk[np.clip(kr, 0, len(Tk) - 1)] <= 20)
                # 之後 20 日內（含 T）有真事件：最小的 Tk ≥ T 滿足 Tk − T ≤ 20
                after = (k < len(Tk)) & (Tk[np.clip(k, 0, len(Tk) - 1)] - T <= 20)
                isT = np.isin(T, Tk)
            else:
                before = after = isT = np.zeros(len(T), bool)
            masks = [np.ones(len(T), bool), ~before & ~after, ~before & ~isT, ~after & ~isT]
            for vi, m in enumerate(masks):
                r = R[m & np.isfinite(R)]
                out[gi, hi, vi, 0] += len(r); out[gi, hi, vi, 1] += r.sum()
    return out


def main():
    t0 = time.time()
    procs, lim, cal, w0, w1, U, off = RX.setup(sys.argv)
    acc = np.zeros((3, 2, 4, 2))
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, off)) as pool:
        for r in pool.imap_unordered(work, list(zip(U["stock_id"], U["market"])), chunksize=8):
            if r is not None:
                acc += r
    S = json.load(open(os.path.join(RX.OUT, "summary.json"), encoding="utf-8"))
    names = ["A 不排除", "B 排除前後各20日（登錄假訊號臂母體）", "C 只排除之前20日（不用未來）", "D 只排除之後20日（用了未來）"]
    res = {"說明": __doc__.strip().splitlines()[0], "格": {}}
    for gi, g in enumerate(XS.SIGS):
        for hi, H in enumerate(RX.H_JUDGE):
            k = "{}_H{}".format(g, H)
            d = {nm: {"日數": int(acc[gi, hi, vi, 0]), "平均R": float(acc[gi, hi, vi, 1] / acc[gi, hi, vi, 0])} for vi, nm in enumerate(names)}
            d["真E"] = S["判定6格"][k]["E"]; d["假訊號臂平均E（本體）"] = S["判定6格"][k]["假訊號"]["假訊號日平均E"]
            res["格"][k] = d
            print(k, "｜".join("{} {:+.3f}%（{:,} 日）".format(nm[:1], v["平均R"] * 100, v["日數"]) for nm, v in d.items() if isinstance(v, dict)),
                  "｜真 E {:+.3f}%｜本體假 E {:+.3f}%".format(d["真E"] * 100, d["假訊號臂平均E（本體）"] * 100), flush=True)
    json.dump(res, open(os.path.join(RX.OUT, "fake_diag.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchUSTopPrev 獨立查核（⛔ 不呼叫 researchUSTopPrev 的任何函式，也不呼叫 K.period_ret／K.metrics／K.anchor_ok）。
只用同一份世界陣列（K.rworld 讀檔）＋ ^SP500TR ＋ DTB3，另寫：
  X1 選股：逐年以 pandas 另算「Y−1 年最後交易日在 S&P 500、Y−2 年最後交易日前 5 根內有有效 K 棒、期間無斷點」的全年報酬，排序（報酬遞減、代號序）
     ⇒ 前 3 名代號與報酬 對 topprev.json 逐年表。
  X2 年報酬：封閉式 Σ w·(賣出開盤 ÷ 買進開盤) − 0.05%（末年 ＝ 資料尾收盤、不扣賣出成本）；停損臂逐日掃收盤 ≤ 0.65 × 買價（若觸發則次一有效開盤賣、
     現金按 DTB3 逐日計）；期間斷點／下市另算。對 json 三組逐年報酬。
  X3 權益：逐年連乘 ⇒ 逐日路徑（年內 ＝ 年初資金 × Σ w·收盤/買價）對 ~/us_work/topprev/equity_daily.csv 每一天；年化、回落、比值、
     2026 貢獻占比、拿掉最好一年（年報酬改 0 連乘）年化 對 json。
  差 ≤ 1e−9 才算過；不同數合計要 0。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSTopPrev_check
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K          # noqa: E402  （只用 rworld 讀世界）

TOL = 1e-9
J = json.load(open(os.path.join(K.OUT, "topprev", "topprev.json"), encoding="utf-8"))


def main():
    R = K.rworld(); W = R["Wd"]; cal = pd.DatetimeIndex(R["cal"])
    tk = np.asarray(W["tick"]); C = W["C"]; O = W["O"]; V = W["valid"]; pb = W["pb"]
    CFx = pd.DataFrame(C).ffill().to_numpy()
    nv = V.sum(axis=1); tail = int(np.where(nv > 0)[0].max())
    firstday = pd.Series(np.arange(len(cal)), index=cal).groupby(cal.year).min().to_dict()
    years = [y for y in range(2017, 2100) if y in firstday and firstday[y] <= tail]
    bad = 0; notes = []

    def cmp(name, x, y):
        nonlocal bad
        if isinstance(x, str) or isinstance(y, str):
            ok = x == y
        else:
            ok = abs(float(x) - float(y)) <= TOL * max(1.0, abs(float(y)))
        if not ok:
            bad += 1; notes.append("%s：查核 %s ≠ 主程式 %s" % (name, x, y))

    rows = {r["持有年"]: r for r in J["逐年"]}
    picks = {}
    # X1
    for y in years:
        s = firstday[y] - 1; b0 = firstday[y - 1] - 1
        mem = W["m5"][s]
        df = pd.DataFrame({"t": tk, "mem": mem, "anc": V[b0 - 4:b0 + 1].any(axis=0),
                           "brk": pb[b0 + 1:s + 1].any(axis=0), "r": CFx[s] / CFx[b0] - 1})
        df = df[df["mem"] & df["anc"] & ~df["brk"] & np.isfinite(df["r"])]
        df = df.sort_values(["r", "t"], ascending=[False, True])
        top = df.head(3)
        picks[y] = [int(np.where(tk == t)[0][0]) for t in top["t"]]
        for k, (t, r) in enumerate(zip(top["t"], top["r"]), 1):
            cmp("%d 第%d名代號" % (y, k), t, rows[y]["第%d名" % k])
            cmp("%d 第%d名前一年漲幅" % (y, k), r, rows[y]["第%d名前一年漲幅" % k])
        cmp("%d 可排檔數" % y, len(df), rows[y]["可排檔數"])

    # DTB3（現金；只在停損或結清後用到）
    from backtest import researchUSA1_data as A1
    d = A1.fred("DTB3"); d.index = pd.to_datetime(d.index)
    dd = d.ffill().reindex(cal.union(d.index)).ffill().reindex(cal).to_numpy(float)

    # X2
    def year_ret(y, js, ws, stop):
        t0 = firstday[y]; endreb = (y + 1) in firstday and firstday[y + 1] <= tail
        t1 = firstday[y + 1] if endreb else tail
        tot = 0.0; ev = []
        for j, w in zip(js, ws):
            bp = O[t0, j]
            # 斷點／下市 ⇒ 結清（持有期 (t0, t1]）
            hit = None
            for t in range(t0 + 1, t1 + 1):
                if pb[t, j]:
                    hit = (t, CFx[t - 1, j], "斷點"); break
                if t > W["last"][j]:
                    hit = (t, CFx[W["last"][j], j], "下市"); break
            sl = None
            if stop:
                for t in range(t0, t1):
                    if V[t, j] and C[t, j] <= bp * (1 - stop):
                        nx = [u for u in range(t + 1, t1) if V[u, j] and np.isfinite(O[u, j]) and O[u, j] > 0]
                        if nx:
                            sl = (nx[0], O[nx[0], j])
                        break
            if hit is not None and (sl is None or hit[0] <= sl[0]):
                tsell, px, why = hit; ev.append(why)
            elif sl is not None:
                tsell, px = sl; ev.append("停損")
            else:
                tsell = None
            if tsell is None:
                if endreb:
                    v = w * O[t1, j] / bp - w * 0.0005
                else:
                    v = w * CFx[tail, j] / bp
            else:
                v = w * px / bp - w * 0.0005
                last_cash_day = (t1 - 1) if endreb else tail
                for t in range(tsell + 1, last_cash_day + 1):
                    v *= 1 + dd[t - 1] / 100 / 252
            tot += v
        return tot - 1, ev

    arms = {"第1名": ([1.0], 1, None), "前3名等權": ([1 / 3] * 3, 3, None), "第1名＋35%停損": ([1.0], 1, 0.35)}
    yrs = {}
    for k, (ws, n, stop) in arms.items():
        yrs[k] = {}
        for y in years:
            r, ev = year_ret(y, picks[y][:n], ws, stop)
            yrs[k][y] = r
            if ev:
                notes.append("%s %d 事件 %s" % (k, y, ev))
            cmp("%s %d 年報酬" % (k, y), r, J["全窗"][k]["逐年報酬"][str(y)])

    # X3
    a = firstday[years[0]] - 1
    eqd = pd.read_csv(os.path.join(os.path.expanduser("~/us_work/topprev"), "equity_daily.csv"), index_col=0, parse_dates=True)
    for k, (ws, n, stop) in arms.items():
        path = np.full(tail - a + 1, np.nan); path[0] = 1.0
        cap = 1.0
        for y in years:
            t0 = firstday[y]; t1 = (firstday[y + 1] - 1) if (y + 1) in firstday and firstday[y + 1] <= tail else tail
            if stop is None or not any("停損" in x for x in notes if x.startswith("%s %d" % (k, y))):
                for t in range(t0, t1 + 1):
                    path[t - a] = cap * sum(w * CFx[t, j] / O[t0, j] for j, w in zip(picks[y][:n], ws))
            cap *= 1 + yrs[k][y]
        cmp("%s 期末倍數" % k, path[-1], J["全窗"][k]["期末倍數"])
        cmp("%s 期末＝逐年連乘" % k, cap, path[-1])
        dif = np.nanmax(np.abs(path - eqd[k].to_numpy()))
        cmp("%s 逐日權益最大差" % k, dif, 0.0)
        yrsN = (tail - a) / 252
        ann = path[-1] ** (1 / yrsN) - 1
        mdd = 0.0; pk = -np.inf
        for v in path:
            pk = max(pk, v); mdd = min(mdd, v / pk - 1)
        cmp("%s 年化" % k, ann, J["全窗"][k]["年化"]); cmp("%s 回落" % k, mdd, J["全窗"][k]["回落"])
        cmp("%s 比值" % k, ann / abs(mdd), J["全窗"][k]["比值"])
        start26 = np.prod([1 + yrs[k][y] for y in years if y < 2026])
        cmp("%s 2026貢獻占比" % k, (cap - start26) / (cap - 1), J["全窗"][k]["2026貢獻占比（占全窗總獲利）"])
        yb = max(yrs[k], key=lambda y: yrs[k][y])
        capx = np.prod([1 + yrs[k][y] for y in years if y != yb])
        cmp("%s 拿掉最好一年(%d) 年化" % (k, yb), capx ** (1 / yrsN) - 1, J["全窗"][k]["拿掉最好一年"]["年化"])
        cmp("%s 拿掉最好一年 年" % k, yb, J["全窗"][k]["拿掉最好一年"]["拿掉的年"])
    # 基準
    B = R["B"]
    bann = (B[tail] / B[a]) ** (252 / (tail - a)) - 1
    cmp("^SP500TR 年化", bann, J["全窗"]["^SP500TR"]["年化"])
    bp_ = B[a:tail + 1]; bmdd = float(np.min(bp_ / np.maximum.accumulate(bp_) - 1))
    cmp("^SP500TR 回落", bmdd, J["全窗"]["^SP500TR"]["回落"])
    for y in years:
        t1 = (firstday[y + 1] - 1) if (y + 1) in firstday and firstday[y + 1] <= tail else tail
        cmp("^SP500TR %d" % y, B[t1] / B[firstday[y] - 1] - 1, rows[y]["當年_^SP500TR"])

    out = {"不同數": bad, "備註": notes, "資料尾": str(cal[tail].date()), "比對項": "X1 選股前3＋可排檔數、X2 三組逐年報酬、X3 逐日權益／年化／回落／比值／2026占比／拿掉最好一年、基準",
           "時間": K.now_tpe()}
    K.jdump(out, os.path.join(K.OUT, "topprev", "check.json"))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

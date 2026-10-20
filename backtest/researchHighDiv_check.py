# -*- coding: utf-8 -*-
"""researchHighDiv 獨立查核（回測線，2026-10-20）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchHighDiv_check.py

 A 獨立重寫的逐年模擬（不 import researchHighDiv.sim；以 pandas 逐事件、年為單位）對 grid.csv／yearly.csv 三格
 B 抽樣年手算：全期 50萬 領現 合併 3.5% 50／50 的 2009、2024 年（調回、單位、配息、稅、健保）
 C 再平衡：每次調回後權重 ＝ 目標、成本 ＝ 0.385% × 調動
 D 0050 一致性：除息事件 → 還原因子鏈 對 data.load_stock 的還原收盤（tw-p17 快照）逐日比值；
   100% 0050、不扣稅健保、再投入、成本 0 在 rerun17 主窗 2017-03-02～2026-08-24 的年化 對 ANCHOR（0050 含息還原）
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchHighDiv as HD   # noqa: E402  只借資料讀取與常數；模擬獨立重寫
from backtest import data as D               # noqa: E402
from backtest import rerun17 as RR           # noqa: E402

OUT = HD.OUT
G = pd.read_csv(os.path.join(OUT, "grid.csv"))
Y = pd.read_csv(os.path.join(OUT, "yearly.csv"), dtype={"年": str})
msha = HD.git("rev-parse", HD.MAIN_REF).strip()
cal, pos, X = HD.load(msha)
ok_all = []


def chk(name, cond, info=""):
    ok_all.append(bool(cond)); print(f"[{'OK' if cond else 'NG'}] {name} {info}")


def indep(a0, hd, d0, d1, V0, tspec, mode, cost=HD.COST, buy=HD.BUYCOST):
    """獨立版：日迴圈但寫法不同（字典持股、年度抵減另記），回 (年化, 年表)。"""
    i0, i1 = pos[d0], pos[d1]
    W = {"0050": a0, hd: 1 - a0}
    held = {k: 0.0 for k in W}; used = {}; NAV = 1.0; prevV = V0; navs = []; yr = {}
    first = True
    for t in range(i0, i1 + 1):
        day = cal[t]; y = day[:4]; out = 0.0
        for k in W:
            if held[k] > 0:
                held[k] *= X[k]["split"][t]
                d = X[k]["div"][t]
                if d > 0:
                    g = held[k] * d
                    if tspec is None:
                        tx = nh = 0.0
                    else:
                        if tspec[0] == "sep":
                            tx = 0.28 * g
                        else:
                            room = 80000.0 - used.get(y, 0.0); cr = min(0.085 * g, max(room, 0.0)); used[y] = used.get(y, 0.0) + cr
                            tx = tspec[1] * g - cr
                        nh = 0.0211 * g if g >= 20000 else 0.0
                    net = g - tx - nh
                    e = yr.setdefault(y, [0.0, 0.0])
                    e[0] += g; e[1] += net
                    if mode == "領現":
                        out += net
                    else:
                        held[k] += net * (1 - buy) / X[k]["C"][t]
        newyear = (t > i0) and cal[t - 1][5:7] == "12" and day[5:7] == "01"
        if first or newyear:
            if first:
                Vt = V0; tr = V0
            else:
                Vt = sum(held[k] * X[k]["O"][t] for k in W)
                tr = 0.5 * sum(abs(W[k] * Vt - held[k] * X[k]["O"][t]) for k in W)
            V2 = Vt - tr * cost
            held = {k: (W[k] * V2 / X[k]["O"][t] if W[k] > 0 else 0.0) for k in W}
            first = False
        V = sum(held[k] * X[k]["C"][t] for k in W)
        NAV = (V + out) / V0 if t == i0 else NAV * (V + out) / prevV
        prevV = V; navs.append(NAV)
        yr.setdefault(y, [0.0, 0.0])
        yr[y].append(V)                            # 年末市值以最後一筆為準
    navs = np.array(navs); n = len(navs)
    cagr = navs[-1] ** (245 / n) - 1
    return cagr, navs, yr


# ── A ──
CASES = [(0.5, "0056", "全期", "50萬", "領現", "合併 淨3.5%（12%級）"), (0.0, "0056", "全期", "250萬", "再投入", "分開 28%"),
         (1.0, "0056", "2017～今", "50萬", "領現", "不扣稅健保"), (0.7, "00878", "00878 短窗 2020～今", "250萬", "領現", "合併 淨11.5%（20%級）"),
         (0.3 + 0.2, "0056", "2007～2016", "250萬", "領現", "合併 淨11.5%（20%級）")]
WIN = {"全期": ("2007-12-26", cal[-1]), "2007～2016": ("2007-12-26", "2016-12-30"), "2017～今": ("2017-01-03", cal[-1]),
       "00878 短窗 2020～今": ("2020-07-20", cal[-1])}
for a0, hd, wn, pn, mode, tn in CASES:
    c, navs, yr = indep(a0, hd, *WIN[wn], HD.PRINCIPALS[pn], HD.TAXES[tn], mode)
    row = G[(G["窗"] == wn) & (G["本金"] == pn) & (G["配息"] == mode) & (G["稅版"] == tn) & (G["0050%"] == int(round(a0 * 100)))].iloc[0]
    chk(f"A 年化 {wn}/{pn}/{mode}/{tn}/0050 {int(a0*100)}%", abs(c - row["稅後年化"]) < 1e-10, f"獨立 {c:.6%} vs 主 {row['稅後年化']:.6%}")
    # 年表：稅後現金 ÷ 年初市值
    ys = sorted(yr); vals = []
    for k, y in enumerate(ys[1:], 1):
        prev = yr[ys[k - 1]][-1]; vals.append((y, yr[y][1] / prev * 1e6))
    yy = Y[(Y["窗"] == wn) & (Y["本金"] == pn) & (Y["配息"] == mode) & (Y["稅版"] == tn) & (Y["0050%"] == int(round(a0 * 100)))]
    mm = dict(zip(yy["年"], yy["稅後現金每100萬"]))
    diffs = [abs(v - mm[y]) for y, v in vals if y in mm]
    chk(f"A 年表 {wn}/{pn}/{mode}/{tn}", len(diffs) >= len(mm) - 1 and max(diffs) < 1e-6, f"比對 {len(diffs)} 年、最大差 {max(diffs):.2e}")

# ── B 抽樣年手算 ──
EV = pd.read_csv(os.path.join(OUT, "sample_events_full_50w_cash_3.5_5050.csv"), dtype={"etf": str})
TR = pd.read_csv(os.path.join(OUT, "sample_trades_full_50w_cash_3.5_5050.csv"))
for y in ("2009", "2024"):
    t0 = TR[TR["date"].str[:4] == y].iloc[0]; tt = pos[t0["date"]]
    o50, o56 = X["0050"]["O"][tt], X["0056"]["O"][tt]
    V2 = t0["前市值"] - t0["成本"]; u50 = 0.5 * V2 / o50; u56 = 0.5 * V2 / o56
    print(f"[B {y}] 調回日 {t0['date']} 前市值 {t0['前市值']:,.0f} 元、調動 {t0['調動']:,.0f}、成本 {t0['成本']:,.1f}（＝0.385%×調動 {abs(t0['成本']-0.00385*t0['調動'])<1e-6}）"
          f"；開盤 0050 {o50} 0056 {o56} ⇒ 單位 {u50:,.2f}／{u56:,.2f}")
    used = 0.0
    for _, e in EV[EV["date"].str[:4] == y].iterrows():
        u = u50 if e["etf"] == "0050" else u56
        if e["etf"] == "0050" and e["date"] >= "2025-06-18":
            u *= 4
        g = u * e["每單位配息"]; cr = min(0.085 * g, 80000 - used); used += cr; tx = 0.12 * g - cr; nh = 0.0211 * g if g >= 20000 else 0.0
        okb = abs(g - e["給付"]) < 1e-6 and abs(tx - e["稅"]) < 1e-6 and abs(nh - e["健保"]) < 1e-6
        chk(f"B {e['date']} {e['etf']}", okb, f"單位 {u:,.2f} × {e['每單位配息']} ＝ 給付 {g:,.0f}；稅 12%−8.5% ＝ {tx:,.0f}；健保 {'2.11%＝'+format(nh,',.0f') if nh else '未達 2 萬不扣'}；淨 {g-tx-nh:,.0f}")

# ── C 再平衡 ──
r = HD.sim(("0050", "0056"), (0.5, 0.5), pos["2007-12-26"], len(cal) - 1, X, cal, 500000.0, HD.TAXES["合併 淨3.5%（12%級）"], "領現")
bad = 0
for tr_ in r["trades"][1:]:
    t = pos[tr_["date"]]
    if not (cal[t - 1][:4] != cal[t][:4] and cal[t][5:7] == "01"):
        bad += 1
chk("C 調回都在每年 1 月第一個交易日", bad == 0 and len(r["trades"]) - 1 == len({c[:4] for c in cal}) - 1, f"調回 {len(r['trades'])-1} 次")
chk("C 成本 ＝ 0.385% × 調動", all(abs(t_["成本"] - 0.00385 * t_["調動"]) < 1e-6 for t_ in r["trades"]))

# ── D 0050 一致性 ──
calm = D.load_calendar()
st = D.load_stock("0050", "twse", calm).df["close"].to_numpy(float)   # tw-p17 快照、還原
mstr = [str(x.date()) for x in calm]
# 用參考價口徑（ref/pre）建還原鏈，與 data.cum_factor_series 同式
tr_ref = np.ones(len(cal))
for t in range(1, len(cal)):
    c_prev = X["0050"]["C"][t - 1]; d = X["0050"]["div"][t]; s = X["0050"]["split"][t]
    f = ((c_prev - d) / c_prev) if d > 0 else 1.0
    f = f / s if s != 1 else f
    tr_ref[t] = tr_ref[t - 1] * (X["0050"]["C"][t] / c_prev) / f
common = [d for d in mstr if d in pos and d >= "2015-01-05"]
a = np.array([tr_ref[pos[d]] for d in common]); b = np.array([st[mstr.index(d)] for d in common])
okm = np.isfinite(a) & np.isfinite(b)
rel = (a[okm] / a[okm][0]) / (b[okm] / b[okm][0]) - 1
chk("D 除息事件還原鏈 ＝ data.load_stock 還原收盤（2015 起逐日）", np.nanmax(np.abs(rel)) < 2e-3, f"最大相對差 {np.nanmax(np.abs(rel)):.2e}（{len(common)} 日；分割日四捨五入差）")
w0, w1 = RR.win_bounds(calm)
HD_COST, HD_BUY = HD.COST, HD.BUYCOST
HD.COST = 0.0; HD.BUYCOST = 0.0
r = HD.sim(("0050", "0056"), (1.0, 0.0), pos[RR.W0], pos[RR.W1], X, cal, 500000.0, None, "再投入")
HD.COST, HD.BUYCOST = HD_COST, HD_BUY
nav = r["nav"]; seg = nav / nav[0]; c_my = seg[-1] ** (245 / len(seg)) - 1
pk = np.maximum.accumulate(seg); m_my = float(((seg - pk) / pk).min())
chk("D 100% 0050 再投入、無稅無成本 對 ANCHOR（含息還原）年化", abs(c_my - RR.ANCHOR[0]) < 5e-4,
    f"本檔 {c_my:.4%}／{m_my:.2%} vs ANCHOR {RR.ANCHOR[0]:.4%}／{RR.ANCHOR[1]:.2%}（差 {c_my-RR.ANCHOR[0]:+.4%}；本檔在除息日收盤再投入、還原鏈用參考價）")
row = G[(G["窗"] == "2017～今") & (G["本金"] == "50萬") & (G["配息"] == "再投入") & (G["稅版"] == "不扣稅健保") & (G["0050%"] == 100)].iloc[0]
print(f"[D 參考] 2017～今 100% 0050 再投入、不扣稅健保、含成本 年化 {row['稅後年化']:.4%}")
print(f"\n查核結果：{sum(ok_all)}／{len(ok_all)} 通過")

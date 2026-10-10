# -*- coding: utf-8 -*-
"""C17 BTC 幣本位重報 --check（讀法 B9）：獨立寫法重算，逐位比；另 fixture＋反例。"""
from __future__ import annotations
import os, sys, json, datetime as dt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import researchC17 as R
import researchC17_btccm as B


def ref_funding(dates):
    raw = pd.read_csv(os.path.join(R.ROOT, "data", "meta", "crypto_cm_funding_rest", "BTCUSD_PERP.csv"))
    acc = {}
    for ms, r in zip(raw["funding_time"].astype("int64"), raw["funding_rate"].astype(float)):
        ts = (dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(ms // 1000))).replace(minute=0, second=0)
        day = (ts - dt.timedelta(seconds=1)).strftime("%Y-%m-%d")
        acc.setdefault(day, {}).setdefault(ts, r)
    allts = sorted(t for d in acc.values() for t in d)
    first, last = allts[0], allts[-1]
    out = []
    for d in dates:
        D = dt.datetime.strptime(d, "%Y-%m-%d")
        if first <= D + dt.timedelta(hours=8) and D + dt.timedelta(days=1) <= last:
            out.append(sum(acc.get(d, {}).values()))
        else:
            out.append(0.10 / 365.25)
    return out


def ref_trades(s, i0, i1):
    o, h, lo, c, qv = s["open"], s["high"], s["low"], s["close"], s["qv"]
    trades = []
    t = i0
    while t <= i1:
        ok = False
        if t >= 20:
            avg = sum(qv[t - 20:t]) / 20.0
            ok = qv[t] > 2.0 * avg and c[t] / c[t - 1] - 1 > 0.05
        if ok and t + 1 <= i1:
            e = t + 1; k = e; x = None
            while k <= i1:
                lv = lo[t]
                m10 = min(lo[k - 10:k])
                if m10 > lv:
                    lv = m10
                if c[k] < lv:
                    x = k + 1 if k + 1 <= i1 else None
                    break
                k += 1
            trades.append((t, e, min(k, i1), x))
            if x is None:
                break
            t = x
        else:
            t += 1
    return trades


def ref_path(s, i0, i1, trades, n, fund, low, ratio=None):
    N = n * 100.0
    o, c, dates = s["open"], s["close"], s["dates"]
    W = B.W0; liq = None; touched = 0
    eq = {}
    for (t, e, last, x) in trades:
        # 進場前的空手日：權益＝W
        Pe = o[e]; N = n * 100.0 if ratio is None else ratio * B.W0 * Pe
        W -= 0.001 * N / Pe
        hit = False
        for d in range(e, last + 1):
            pref = Pe if d == e else c[d - 1]
            W -= fund[d] * N / pref
            # 不等式：最低點權益 ≤ 維持保證金
            if W + N * (1 / Pe - 1 / low[d]) <= 0.004 * N / low[d]:
                hit = True; liq = dates[d]; touched += 1; W = 0.0
                eq[d] = 0.0
                break
            eq[d] = W + N * (1 / Pe - 1 / c[d])
        if hit:
            break
        if x is not None:
            W += N * (1 / Pe - 1 / o[x]) - 0.001 * N / o[x]
    # 逐年：用年末那天的權益（持有中＝含未實現；空手＝W 的當時值）——以逐日重建
    full = []
    Wt = B.W0; dead = False
    tr_iter = {e: (t, e, last, x) for (t, e, last, x) in trades}
    cur = None; realized = B.W0
    # 用 eq（持有日）與交易邊界重建每日權益
    W_run = B.W0; Pe = None
    for d in range(i0, i1 + 1):
        if dead:
            full.append(0.0); continue
        if cur is not None and cur[3] == d:
            W_run += N * (1 / Pe - 1 / o[d]) - 0.001 * N / o[d]; cur = None
        if d in tr_iter:
            cur = tr_iter[d]; Pe = o[d]; N = n * 100.0 if ratio is None else ratio * B.W0 * Pe; W_run -= 0.001 * N / Pe
        if cur is not None and cur[1] <= d <= cur[2]:
            pref = Pe if d == cur[1] else c[d - 1]
            W_run -= fund[d] * N / pref
            if liq == dates[d]:
                dead = True; full.append(0.0); continue
            full.append(W_run + N * (1 / Pe - 1 / c[d]))
        else:
            full.append(W_run)
    yrs = {}
    for d, v in zip(dates[i0:i1 + 1], full):
        yrs[d[:4]] = v
    ys = []; prev = B.W0
    for y in sorted(yrs):
        ys.append(yrs[y] - prev); prev = yrs[y]
    return {"W_end": full[-1], "liq": liq, "touched": touched, "years": ys}


def fx_liq(mut=None):
    """fixture：Pe＝100,000、3 張（N＝300）、W＝0.0715 ⇒ Lp＝301.2/(0.0715+0.003)＝4,043.0；日低 4,000 要觸及、4,100 不觸及。
    反例 mut＝usd_formula：誤用 U 本位公式 Pe×(1−W×Pe/N)… 這裡用「不含 N/Pe 項」Lp＝N(1+m)/W 反例。"""
    N, W, Pe = 300.0, 0.0715, 100000.0
    Lp = N * 1.004 / (W + N / Pe) if mut is None else N * 1.004 / W
    return (4000 <= Lp) and not (4100 <= Lp)


def main():
    s = B.load()
    J, _ = B.run()
    fund = ref_funding(list(s["dates"]))
    out = {"比對": [], "fixture": {"正確通過": bool(fx_liq()), "反例被抓到": not fx_liq("drop_NPe")}}
    nd = 0; ncmp = 0; maxd = 0.0
    fdiff = float(np.max(np.abs(np.array(fund) - s["fund"])))
    out["資金費逐日最大差"] = fdiff; nd += int(fdiff > 1e-15); ncmp += 1
    for lab, (a, b) in B.WINS:
        i0, i1 = R.window_idx(s, a, b)
        rt = ref_trades(s, i0, i1)
        et = [(t["t"], t["e"], t["last"], t["x"]) for t in R.unit_run(s, i0, i1, 2.0, 0.05, B.RULE, "open")["trades"]]
        same = rt == et; nd += int(not same); ncmp += 1
        for n in B.SIZES:
            k = n * 100.0 / (B.W0 * float(s["close"][-1]))
            rpk = ref_path(s, i0, i1, rt, n, fund, s["low"], ratio=k)
            epk = B.path(s, i0, i1, [{"t": t, "e": e, "last": l, "x": x} for (t, e, l, x) in et], n, "spot", ratio=k)
            dk = abs(rpk["W_end"] - epk["W_end"]); maxd = max(maxd, dk)
            badk = dk > 1e-12 or rpk["liq"] != epk["liq_day"]
            nd += int(badk); ncmp += 1
            out["比對"].append({"窗": lab, "張": f"{n}_按今日比例", "窗末錢包差": dk, "強平日相同": rpk["liq"] == epk["liq_day"]})
            for lk in ("spot", "mark"):
                low = s["low"] if lk == "spot" else np.where(np.isnan(s["mlow"]), s["low"], s["mlow"])
                rp = ref_path(s, i0, i1, rt, n, fund, low)
                ep = B.path(s, i0, i1, [{"t": t, "e": e, "last": l, "x": x} for (t, e, l, x) in et], n, lk)
                em = B.measure(s, i0, i1, ep)
                d1 = abs(rp["W_end"] - ep["W_end"]); maxd = max(maxd, d1)
                same_liq = rp["liq"] == ep["liq_day"]
                same_t = rp["touched"] == int(sum(r["touched"] for r in ep["rows"]))
                ey = [y["增減BTC"] for y in em["逐年"]]
                dy = max(abs(x - y) for x, y in zip(rp["years"], ey)) if len(ey) == len(rp["years"]) else 1.0
                maxd = max(maxd, dy)
                bad = d1 > 1e-12 or dy > 1e-12 or not same_liq or not same_t
                nd += int(bad); ncmp += 1
                out["比對"].append({"窗": lab, "張": n, "日低": lk, "交易清單相同": same, "窗末錢包差": d1, "強平日相同": same_liq,
                                  "觸及筆數相同": same_t, "逐年最大差": dy})
    out["比對次數"] = ncmp; out["不同數"] = nd; out["最大差"] = maxd
    with open(os.path.join(R.OUT, "check_btccm.json"), "w", encoding="utf-8") as f:
        json.dump(R.to_jsonable(out), f, ensure_ascii=False, indent=1)
    print("check_btccm: 比對", ncmp, "不同", nd, "最大差", maxd, "fixture", out["fixture"])

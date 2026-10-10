# -*- coding: utf-8 -*-
"""PREREGC17 --check（讀法 K14）：fixture＋會變紅的反例，以及另一支純迴圈參考實作逐位比。"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import researchC17 as R


# ───────────── 純迴圈參考實作（不共用引擎任何函式） ─────────────
def ref_sig(s, vm, up):
    qv, c = s["qv"], s["close"]
    out = []
    for t in range(len(c)):
        if t < 20:
            out.append(False); continue
        avg = 0.0
        for j in range(t - 20, t):
            avg += qv[j]
        avg /= 20.0
        out.append(bool(qv[t] > vm * avg and (c[t] / c[t - 1] - 1.0) > up))
    return out


def ref_exit(s, k, t, e, rule):
    kind, p = rule
    c, lo = s["close"], s["low"]
    if kind == "low":
        m = lo[t]
        for j in range(max(k - p, 0), k):
            if lo[j] < m:
                m = lo[j]
        return c[k] < m
    if kind == "ma":
        tot = 0.0
        for j in range(k - p + 1, k + 1):
            tot += c[j]
        return c[k] < tot / p
    if kind == "trail":
        mx = c[e]
        for j in range(e, k + 1):
            mx = max(mx, c[j])
        return c[k] < mx * (1 - p)
    if kind == "fixed":
        return k - e + 1 >= p


def ref_run(s, i0, i1, vm, up, rule):
    sig = ref_sig(s, vm, up)
    o, c, f = s["open"], s["close"], s["fund"]
    trades = []
    pos = None   # (t, e)
    day_net = {}
    t = i0
    d = i0
    flat_from = i0
    # 逐日走：空手時看訊號；持有時看出場
    while d <= i1:
        if pos is None:
            if d >= flat_from and sig[d] and d + 1 <= i1:
                pos = (d, d + 1)
            d += 1
            continue
        ts, e = pos
        k = d
        if k < e:
            d += 1; continue
        hit = ref_exit(s, k, ts, e, rule)
        g = (c[k] / o[k]) if k == e else (c[k] / c[k - 1])
        cost = R.COST if k == e else 0.0
        if hit and k + 1 <= i1:
            g = g * (o[k + 1] / c[k]); cost += R.COST
            day_net[k] = g - 1.0 - f[k] - cost
            trades.append((ts, e, k, k + 1)); pos = None; flat_from = k + 1
            d = k + 1
            continue
        day_net[k] = g - 1.0 - f[k] - cost
        if hit or k == i1:
            trades.append((ts, e, min(k, i1), None)); pos = None
            break
        d += 1
    wm = 0.0
    for j in range(i0, i1 + 1):
        wm += c[j] / c[j - 1] - 1.0
    wm /= (i1 - i0 + 1)
    hs = 0.0
    for v in day_net.values():
        hs += v
    ex = hs / len(day_net) - wm if day_net else float("nan")
    return trades, ex, day_net


def ref_shift(s, i0, i1, held_w, k, wm):
    T = len(held_w)
    h = [held_w[(j - k) % T] for j in range(T)]
    o, c, f = s["open"], s["close"], s["fund"]
    tot, nd = 0.0, 0
    for j in range(T):
        if not h[j]:
            continue
        d = i0 + j
        ent = (j == 0) or not h[j - 1]
        lst = (j < T - 1) and not h[j + 1]
        g = (c[d] / o[d]) if ent else (c[d] / c[d - 1])
        if lst:
            g *= o[d + 1] / c[d]
        tot += g - 1.0 - f[d] - R.COST * ent - R.COST * lst - wm
        nd += 1
    return tot / nd


# ───────────── fixtures ─────────────
def mk(close, low=None, qv=None, opn=None):
    n = len(close)
    close = np.asarray(close, float)
    s = {"name": "fx", "dates": np.array(pd.date_range("2020-01-01", periods=n).strftime("%Y-%m-%d"))}
    s["close"] = close
    s["open"] = np.asarray(opn, float) if opn is not None else np.r_[close[0], close[:-1]]
    s["low"] = np.asarray(low, float) if low is not None else np.minimum(s["open"], close) * 0.99
    s["high"] = np.maximum(s["open"], close) * 1.01
    s["qv"] = np.asarray(qv, float) if qv is not None else np.full(n, 100.0)
    s["rcc"] = np.r_[np.nan, close[1:] / close[:-1] - 1.0]
    s["fund"] = np.zeros(n); s["fend"] = np.zeros(n); s["fmiss"] = np.zeros(n, bool); s["fcnt"] = np.zeros(n)
    return s


def fx_a(mut):
    """a. 均量不含 t：qv_t＝210、前 20 日 100 ⇒ 210 ＞ 200 是訊號；含 t 的均量 105.5 ⇒ 211 ＞ 210 不是訊號。"""
    c = [100.0] * 20 + [106.0, 107.0]
    q = [100.0] * 20 + [210.0, 100.0]
    s = mk(c, qv=q)
    return bool(R.signals(s, 2.0, 0.05, mut)[20])


def fx_b(mut):
    """b. 次日開盤平倉：訊號日 20，進場 21 開 106；22 收 90（破訊號日低）⇒ 23 開盤 80 平。
    每筆報酬＝(c21/o21)(c22/c21)(o23/c22) − 1 − 0.2% ＝ 80/106 − 1 − 0.002（無資金費）。"""
    c = [100.0] * 20 + [106.0, 107.0, 90.0, 85.0, 85.0]
    o = [100.0] * 20 + [100.0, 106.0, 107.0, 80.0, 85.0]
    lo = [99.0] * 20 + [100.0, 105.0, 89.0, 79.0, 84.0]
    q = [100.0] * 20 + [300.0, 100.0, 100.0, 100.0, 100.0]
    s = mk(c, low=lo, qv=q, opn=o)
    sig = R.signals(s, 2.0, 0.05)
    tr = R.simulate(s, 20, len(c) - 1, sig, ("low", 10))
    h, en, lx = R.flags_from_trades(len(c), tr)
    net = R.net_series(s, h, en, lx, "open", mut)
    r = float(np.prod(1 + net[h]) - 1)
    exp_net = (107 / 106 - 0.001) * (90 / 107 * 80 / 90 - 0.001) - 1   # 逐日 g−1−成本 再複利
    return abs(r - exp_net) < 1e-12 and tr[0]["x"] == 23


def fx_c(mut):
    """c. 資金費毫秒尾數：2020-01-02 00:00:00.002 那筆（0.01）屬於持有日 2020-01-01；2020-01-01 08:00 那筆 0.001 也屬 01-01。"""
    ev = pd.DataFrame({"calc_time": [1577836800000, 1577836800000 + 8 * 3600000, 1577836800000 + 16 * 3600000, 1577923200002, 1577923200000 + 8 * 3600000,
                                     1577923200000 + 16 * 3600000, 1578009600000, 1578009600000 + 8 * 3600000],
                       "r": [0.0, 0.001, 0.002, 0.01, 0.0, 0.0, 0.0, 0.0]})
    p = os.path.join(R.OUT, "_fx_c.csv")
    ev.rename(columns={"r": "last_funding_rate"}).to_csv(p, index=False)
    e = R._funding_events(p, "calc_time", "last_funding_rate", mut)
    os.remove(p)
    fund, fend, miss, cnt = R.funding_arrays(np.array(["2020-01-01", "2020-01-02"]), e, mut)
    return abs(fund[0] - 0.013) < 1e-15 and abs(fend[0] - 0.01) < 1e-15


def fx_d(mut):
    """d. 持倉中再出訊號不重設：第 2 個訊號（日 41，低 127）後日 42 收 110：照規則門檻＝訊號日 20 的低 100.5 ⇒ 不出場；重設的反例門檻 117 ⇒ 出場。"""
    c = [100.0] * 20 + [106.0] + [107.0 + i for i in range(20)] + [126.0 * 1.06, 110.0, 111.0]
    lo = [99.0] * 20 + [100.5] + [106.0 + i for i in range(20)] + [127.0, 109.0, 110.0]
    q = [100.0] * 20 + [300.0] + [100.0] * 20 + [300.0, 100.0, 100.0]
    s = mk(c, low=lo, qv=q)
    sig = R.signals(s, 2.0, 0.05)
    assert sig[20] and sig[41]
    tr = R.simulate(s, 20, len(c) - 1, sig, ("low", 10), "open", mut)
    return tr[0]["x"] is None


FIX = [("a", fx_a, "avg_incl_t", "均量含 t 當天"), ("b", fx_b, "exit_close", "觸發日收盤就平（不是次日開盤）"),
       ("c", fx_c, "ms_date", "資金費用時戳當天日期歸日（00:00 那筆歸到次日）"), ("d", fx_d, "reset", "持倉中再出訊號就重設訊號日低")]


def main():
    out = {"fixtures": [], "抽樣比對": [], "平移比對": []}
    ok_all = True
    for name, f, mut, desc in FIX:
        good = bool(f(None)); bad = bool(f(mut))
        out["fixtures"].append({"fixture": name, "正確引擎通過": good, "反例": desc, "反例被抓到(變紅)": not bad})
        ok_all &= good and not bad
    btc, early, coins = R.build_units("BTCUSDT")
    units = {"BTC_W1": (btc, *R.window_idx(btc, *R.W1)), "BTC_W2": (btc, *R.window_idx(btc, *R.W2)),
             "BTC_early_bitstamp": (early, *R.window_idx(early, "2013-01-01", R.EARLY_END))}
    for c, s in coins.items():
        units[c] = (s, *R.window_idx(s, s["dates"][0], R.END))
    rng = np.random.default_rng(R.SEED)
    cells = [(R.MAIN_SIG, R.MAIN_EXIT)]
    allc = [(sg, ex) for sg in R.SIGS for ex in R.EXITS if (sg == R.MAIN_SIG or ex == R.MAIN_EXIT) and not (sg == R.MAIN_SIG and ex == R.MAIN_EXIT)]
    for i in rng.choice(len(allc), 6, replace=False):
        cells.append(allc[int(i)])
    ndiff = 0; maxd = 0.0; ncmp = 0
    for (vm, up), rule in cells:
        for k, (s, i0, i1) in units.items():
            eng = R.unit_run(s, i0, i1, vm, up, rule)
            trs, ex, dn = ref_run(s, i0, i1, vm, up, rule)
            et = [(x["t"], x["e"], x["last"], x["x"]) for x in eng["trades"]]
            same_tr = et == trs
            d = abs(eng["excess"] - ex) if not (np.isnan(eng["excess"]) and np.isnan(ex)) else 0.0
            sig_e = R.signals(s, vm, up); sig_r = ref_sig(s, vm, up)
            nsig = int(sum(bool(a) != b for a, b in zip(sig_e, sig_r)))
            bad = (not same_tr) or d > 1e-12 or nsig > 0
            ndiff += int(bad); maxd = max(maxd, d); ncmp += 1
            out["抽樣比對"].append({"格": f"{vm}x{up}_{rule[0]}{rule[1]}", "單位": k, "筆數": len(trs), "交易清單相同": same_tr,
                                 "訊號不同天數": nsig, "每天多賺差": d})
    # 平移
    for k in ("BTC_W1", "BTC_W2", "SOL"):
        s, i0, i1 = units[k]
        eng = R.unit_run(s, i0, i1, *R.MAIN_SIG, R.MAIN_EXIT)
        w = R.sub(s, i0, i1); hw = eng["held"][i0:i1 + 1].copy()
        for _ in range(7):
            kk = int(rng.integers(1, len(hw)))
            a = R.shift_stat([(w, hw, eng["wmean"])], [kk])
            b = ref_shift(s, i0, i1, list(hw), kk, eng["wmean"])
            dd = abs(a - b); maxd = max(maxd, dd); ncmp += 1
            ndiff += int(dd > 1e-12)
            out["平移比對"].append({"單位": k, "k": kk, "差": dd})
    # 資金費歸日：另用 datetime 逐筆歸日，抽 300 個覆蓋日比
    import datetime as dt
    raw = pd.read_csv(os.path.join(R.ROOT, "data", "crypto_funding", "BTCUSDT.csv"))
    if R.FUND2019:
        raw = pd.concat([pd.read_csv(R.F2019), raw])
    acc = {}
    for ms, r in zip(raw["calc_time"].astype("int64"), raw["last_funding_rate"].astype(float)):
        ts = dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(ms // 1000))
        ts = ts.replace(minute=0, second=0)
        day = (ts - dt.timedelta(seconds=1)).strftime("%Y-%m-%d")
        acc.setdefault(day, {})
        acc[day].setdefault(ts, r)
    cov = np.where(~btc["fmiss"])[0]
    nf = 0
    for i in rng.choice(cov, 300, replace=False):
        v = sum(acc.get(btc["dates"][i], {}).values())
        dd = abs(v - btc["fund"][i]); maxd = max(maxd, dd); ncmp += 1
        nf += int(dd > 1e-15)
    ndiff += nf
    out["資金費歸日抽樣300不同"] = nf
    out["比對次數"] = ncmp; out["不同數"] = ndiff; out["最大差"] = maxd; out["fixture全過"] = bool(ok_all)
    with open(os.path.join(R.OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(R.to_jsonable(out), f, ensure_ascii=False, indent=1)
    print("check: 比對", ncmp, "不同", ndiff, "最大差", maxd, "fixture全過", ok_all)

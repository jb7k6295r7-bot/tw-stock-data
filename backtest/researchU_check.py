# -*- coding: utf-8 -*-
"""PREREGU 本體的【獨立路】查核：⛔ 不 import data.py／tradability／fib_u／researchU*／researchM*／numpy／pandas。
直接用 csv 模組讀釘住快照的原始日線（data/stocks）與還原事件表（data/adj），自己算還原價：
   還原價(d) ＝ 原始價(d) × cum_factor（adj 表中第一個【事件日 > d】那一列；沒有 ⇒ 1）
   一列四價任一 ≤ 0 ⇒ 該列四價皆視為缺；空白 ⇒ 缺；同日重複列取第一列
① 抽 20 筆保留事件，逐筆手算：
   p ＝ 還原 high(t_H) − x·(還原 high(t_H) − 還原 low(t_L))；並驗「第一次觸及」：[t_H, conf] 內還原 low 全 > p、(conf, T) 內還原 low 全 > p、還原 low(T) ≤ p
   y ＝ [T, T+20] 有收盤的日子依序第一個落在閉區間 [0.95p, 1.05p] 之外者（> ⇒ 1、< ⇒ 0；都在帶內 ⇒ −1）
   g20 ＝ close(≤T+20 最後一個有收盤日)／close(T) − 1
   交易版 gd ＝ 出場價(T+21)／還原開盤(T+1) − 1（出場價：有收盤且開盤 > 0 ⇒ 還原開盤；否則往回找最後一個有收盤日的還原收盤）
② 取其中 n_days 個不同的 T：逐檔迴圈（全部可用 gate3）算 close(≤d+20 最後有收盤)／close(d) − 1 的等權平均（d 日有收盤者），與主程式的 EWc_20(d) 比
"""
import csv, os, math

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
SNAP = os.path.expanduser("~/h2data/{}/data".format(SHA))
FR = {"30": 0.30, "38.2": 0.382, "45": 0.45, "50": 0.50, "55": 0.55, "61.8": 0.618, "70": 0.70}
_cache = {}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def calendar():
    with open(os.path.join(SNAP, "meta", "calendar_twse.csv"), newline="", encoding="utf-8") as f:
        return sorted(r["date"] for r in csv.DictReader(f))


def stock(sid):
    if sid in _cache:
        return _cache[sid]
    p = os.path.join(SNAP, "stocks", sid + ".csv")
    px = {}
    if os.path.exists(p):
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = r["date"]
                if d in px:
                    continue
                v = [_num(r[k]) for k in ("open", "high", "low", "close")]
                if any((not math.isnan(x)) and x <= 0 for x in v):
                    v = [math.nan] * 4
                px[d] = v
    adj = []
    pa = os.path.join(SNAP, "adj", sid + ".csv")
    if os.path.exists(pa):
        with open(pa, newline="", encoding="utf-8") as f:
            adj = sorted((r["date"], float(r["cum_factor"])) for r in csv.DictReader(f))
    _cache[sid] = (px, adj)
    return _cache[sid]


def factor(adj, d):
    for ed, cf in adj:
        if ed > d:
            return cf
    return 1.0


def val(sid, d, k):
    """還原價；k：0 開、1 高、2 低、3 收。無該日或缺 ⇒ nan。"""
    px, adj = stock(sid)
    if d not in px or math.isnan(px[d][k]):
        return math.nan
    return px[d][k] * factor(adj, d)


def has_close(sid, d):
    return not math.isnan(val(sid, d, 3))


def close_ff(sid, cal, j):
    k = j
    while k >= 0 and not has_close(sid, cal[k]):
        k -= 1
    return val(sid, cal[k], 3) if k >= 0 else math.nan


def exit_px(sid, cal, j):
    o = val(sid, cal[j], 0)
    if has_close(sid, cal[j]) and not math.isnan(o) and o > 0:
        return o
    return close_ff(sid, cal, j)


def run(pick, universe, n_days=5):
    cal = calendar(); pos = {d: i for i, d in enumerate(cal)}
    det = []; wp = wg = wd = 0.0; ybad = 0; touch_bad = 0
    for q in pick:
        s = q["sid"]; iT = pos[q["T"]]; iH = pos[q["tH"]]; iC = pos[q["conf"]]
        H0 = val(s, q["tH"], 1); L0 = val(s, q["tL"], 2)
        p = H0 - FR[q["pos"]] * (H0 - L0)
        lows_pre = [val(s, cal[j], 2) for j in range(iH, iC + 1)]
        lows_mid = [val(s, cal[j], 2) for j in range(iC + 1, iT)]
        ok_touch = all(math.isnan(x) or x > p for x in lows_pre + lows_mid) and val(s, q["T"], 2) <= p
        touch_bad += int(not ok_touch)
        y = -1
        for j in range(iT, iT + 21):
            v = val(s, cal[j], 3)
            if math.isnan(v):
                continue
            if v > p * 1.05:
                y = 1; break
            if v < p * 0.95:
                y = 0; break
        g20 = close_ff(s, cal, iT + 20) / val(s, q["T"], 3) - 1.0
        gd = None
        if q["gd"] is not None:
            gd = exit_px(s, cal, iT + 21) / val(s, cal[iT + 1], 0) - 1.0
            wd = max(wd, abs(gd - q["gd"]))
        rp = abs(p - q["p"]) / q["p"]; wp = max(wp, rp); wg = max(wg, abs(g20 - q["g20"])); ybad += int(y != q["y"])
        det.append({"sid": s, "pos": q["pos"], "T": q["T"], "p_獨立": p, "p_主程式": q["p"], "第一次觸及成立": ok_touch,
                    "y_獨立": y, "y_主程式": q["y"], "g20_獨立": g20, "g20_主程式": q["g20"], "gd_獨立": gd, "gd_主程式": q["gd"]})
    days = []
    for q in pick:
        if q["T"] not in [d for d, _ in days]:
            days.append((q["T"], q["EWc"]))
        if len(days) >= n_days:
            break
    ew_det = []; ew_worst = 0.0
    for d, ew_main in days:
        i = pos[d]; tot = 0.0; k = 0
        for sid in universe:
            c0 = val(sid, d, 3)
            if math.isnan(c0):
                continue
            tot += close_ff(sid, cal, i + 20) / c0 - 1.0; k += 1
        ew = tot / k
        ew_worst = max(ew_worst, abs(ew - ew_main))
        ew_det.append({"d": d, "檔數": k, "EWc_獨立": ew, "EWc_主程式": ew_main, "差": abs(ew - ew_main)})
    return {"筆數": len(det), "p最大相對差": wp, "第一次觸及不成立": touch_bad, "y不同": ybad, "g20最大差": wg, "gd最大差": wd,
            "明細": det, "基準天數": len(ew_det), "基準最大差": ew_worst, "基準明細": ew_det,
            "判": bool(wp < 1e-12 and touch_bad == 0 and ybad == 0 and wg < 1e-9 and wd < 1e-9 and ew_worst < 1e-9)}

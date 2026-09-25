# -*- coding: utf-8 -*-
"""PREREGM 本體的【獨立路】查核：⛔ 不 import data.py／tradability／trendline_m／researchM／numpy／pandas。
直接用 csv 模組讀釘住快照的原始日線（data/stocks）與還原事件表（data/adj），自己算還原價：
   還原價(d) ＝ 原始價(d) × cum_factor（adj 表中第一個【事件日 > d】那一列；沒有 ⇒ 1）
   一列四價任一 ≤ 0 ⇒ 該列四價皆視為缺；空白 ⇒ 缺；同日重複列取第一列
   出場價 px(j)：j 有收盤且開盤 > 0 ⇒ 還原開盤；否則往回找最後一個有收盤的交易日 ⇒ 該日還原收盤
① 抽 20 筆保留事件：R_e ＝ px(T+21)／還原開盤(T+1) − 1 − 0.585%，與主程式比
② 取其中 n_days 個不同的進場日 d：逐檔迴圈（全部 gate3）算 px(d+20)／還原開盤(d) − 1 的等權平均，與主程式的 EW_20(d) 比
"""
import csv, os, math

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
SNAP = os.path.expanduser("~/h2data/{}/data".format(SHA))
COST = 0.00585
_cache = {}


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return math.nan
    return v


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
                px[d] = (v[0], v[3])
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


def has_close(px, d):
    return d in px and not math.isnan(px[d][1])


def open_adj(sid, d):
    px, adj = stock(sid)
    if not has_close(px, d):
        return math.nan
    o = px[d][0]
    return o * factor(adj, d) if (not math.isnan(o) and o > 0) else math.nan


def exit_px(sid, cal, j):
    px, adj = stock(sid)
    d = cal[j]
    if has_close(px, d) and not math.isnan(px[d][0]) and px[d][0] > 0:
        return px[d][0] * factor(adj, d)
    k = j
    while k >= 0 and not has_close(px, cal[k]):
        k -= 1
    if k < 0:
        return math.nan
    return px[cal[k]][1] * factor(adj, cal[k])


def run(pick, universe, n_days=5):
    cal = calendar(); pos = {d: i for i, d in enumerate(cal)}
    det = []; worst = 0.0
    for p in pick:
        i1 = pos[p["T1"]]; i21 = pos[p["T21"]]
        assert i21 - pos[p["T"]] == 21 and i1 - pos[p["T"]] == 1
        P0 = open_adj(p["sid"], p["T1"]); ex = exit_px(p["sid"], cal, i21)
        R = ex / P0 - 1.0 - COST
        dd = abs(R - p["R"]); worst = max(worst, dd)
        det.append({"畫法": p["畫法"], "sid": p["sid"], "T": p["T"], "P0_獨立": P0, "出場_獨立": ex, "R_獨立": R, "R_主程式": p["R"], "差": dd})
    days = []
    for p in pick:
        if p["T1"] not in [d for d, _ in days]:
            days.append((p["T1"], p["EW20"]))
        if len(days) >= n_days:
            break
    ew_det = []; ew_worst = 0.0
    for d, ew_main in days:
        i = pos[d]; tot = 0.0; k = 0
        for sid in universe:
            o = open_adj(sid, d)
            if math.isnan(o):
                continue
            ex = exit_px(sid, cal, i + 20)
            tot += ex / o - 1.0; k += 1
        ew = tot / k
        ew_worst = max(ew_worst, abs(ew - ew_main))
        ew_det.append({"d": d, "檔數": k, "EW_獨立": ew, "EW_主程式": ew_main, "差": abs(ew - ew_main)})
    return {"R_e筆數": len(det), "R_e最大差": worst, "R_e明細": det, "基準天數": len(ew_det), "基準最大差": ew_worst, "基準明細": ew_det,
            "判": bool(worst < 1e-9 and ew_worst < 1e-9)}

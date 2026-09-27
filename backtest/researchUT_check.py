# -*- coding: utf-8 -*-
"""PREREG上升趨勢線 本體的【獨立路】查核。⛔ 不 import researchUT／trendline_ut／trendline_m／stop_fractal／research11／data。
 ① R_e 與基準：researchM_check（PREREGM 的獨立路：csv 模組讀快照原始日線＋還原事件表、自己還原）抽主格 20 筆 R_e、5 天 EW_20
 ② 幾何：主格（甲 R5 1% 穿越）抽 15 筆，從自己讀的還原 OHLC（有效 K 棒序列）驗：兩個取點是【嚴格】樞紐低點（左右各 5 根）、遞升、
    確認根 ＝ 最後取點＋5、取點是確認時最近的兩個樞紐、確認後到 T−1 沒有新樞紐確認、跨度 ≤ 120、有效 ≤ 60、實體底不低於線、
    T 是確認後【第一個】1% 穿越（c ＜ 0.99ℓ ∧ 前一根 ≥ 0.99ℓ）
 ③ 18 格重算：從 events_X.csv.gz 自己算平均、月分群 CR0 SE、95% CI、20 日區段、n_eff ⇒ 與 summary.json 比
輸出 backtest/resultsUT/check.json、check_detail.csv。"""
import os, sys, csv, json, math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchM_check as MC                       # PREREGM 的獨立路（⛔ 不經 data.py）

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUT")
SNAP = MC.SNAP
W0 = "2017-03-02"
_c = {}


def ohlc(sid):
    """快照原始日線 × 還原因子（MC.factor 同式）⇒ {date: (o, h, l, c)}；任一 ≤ 0 ⇒ 四價皆缺。"""
    if sid in _c:
        return _c[sid]
    px = {}
    with open(os.path.join(SNAP, "stocks", sid + ".csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["date"]
            if d in px:
                continue
            v = [MC._num(r[k]) for k in ("open", "high", "low", "close")]
            if any((not math.isnan(x)) and x <= 0 for x in v):
                v = [math.nan] * 4
            px[d] = v
    _, adj = MC.stock(sid)
    out = {d: tuple(x * MC.factor(adj, d) for x in v) for d, v in px.items()}
    _c[sid] = out
    return out


def piv_low(L, s, k=5):
    if s - k < 0 or s + k >= len(L):
        return False
    return all(L[s] < L[j] for j in range(s - k, s + k + 1) if j != s)


def geo(sid, row, cal):
    P = ohlc(sid)
    seq = [d for d in cal if d in P and not math.isnan(P[d][3])]
    ix = {d: i for i, d in enumerate(seq)}
    O = [P[d][0] for d in seq]; L = [P[d][2] for d in seq]; C = [P[d][3] for d in seq]
    a1, a2 = row["anchors"].split("|")
    p1, p2, cf, b = ix[a1], ix[a2], ix[row["conf"]], ix[row["T_date"]]
    if not (piv_low(L, p1) and piv_low(L, p2) and L[p2] > L[p1] and cf == p2 + 5):
        return False, "取點／確認"
    piv = [s for s in range(len(L)) if piv_low(L, s)]
    before = [s for s in piv if s + 5 <= cf]
    if before[-2:] != [p1, p2]:
        return False, "不是最近兩個樞紐"
    if any(cf < s + 5 <= b - 1 for s in piv):
        return False, "中途換線"
    sl = (L[p2] - L[p1]) / (p2 - p1); lv = lambda j: L[p1] + sl * (j - p1)
    if cf - p1 > 120 or b - cf > 60 or b - cf < 1:
        return False, "期限"
    for j in range(p1 + 1, p2):
        bot = min(O[j] if not math.isnan(O[j]) else C[j], C[j])
        if bot < lv(j):
            return False, "實體穿線"
    hit = lambda j: C[j] < 0.99 * lv(j) and C[j - 1] >= 0.99 * lv(j - 1)
    if not hit(b):
        return False, "T 不是 1% 穿越"
    if any(hit(j) for j in range(cf + 1, b)):
        return False, "之前已穿越"
    return True, "ok"


def cl(x, mon):
    x = np.asarray(x, float); n = len(x); m = x.mean(); d = x - m
    s = pd.Series(d).groupby(np.asarray(mon)).sum().to_numpy()
    se = math.sqrt(float((s ** 2).sum())) / n
    return m, se, m - 1.96 * se, m + 1.96 * se


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    E = pd.read_csv(os.path.join(OUT, "events_X.csv.gz"), dtype={"sid": str})
    cal = MC.calendar(); pos = {d: i for i, d in enumerate(cal)}
    pre = pd.read_csv(os.path.join(OUT, "pre_events.csv.gz"), dtype={"sid": str})
    res = {}; det = []
    rng = np.random.default_rng(20260927)
    main = E[E["格"] == "甲_R5_1%穿越"].reset_index(drop=True)
    # ① R_e／EW
    pick = []
    for i in rng.choice(len(main), 20, replace=False):
        r = main.iloc[int(i)]; T = pos[r["T_date"]]
        pick.append({"畫法": "甲", "sid": r["sid"], "T": r["T_date"], "T1": cal[T + 1], "T21": cal[T + 21], "R": float(r["R"]), "EW20": float(r["EW"])})
    stocks = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str)
    from backtest import universe_gate as UG                      # 母體名單（共用閘門，⛔ 不是主程式）
    U = UG.gate3(stocks)
    ck = MC.run(pick, list(U["stock_id"]), n_days=5)
    res["①R_e與基準"] = {"R_e筆數": ck["R_e筆數"], "R_e最大差": ck["R_e最大差"], "基準天數": ck["基準天數"], "基準最大差": ck["基準最大差"]}
    print("① R_e {} 筆最大差 {:.1e}｜基準 {} 天最大差 {:.1e}".format(ck["R_e筆數"], ck["R_e最大差"], ck["基準天數"], ck["基準最大差"]), flush=True)
    # ② 幾何
    pk = pre[(pre["格"] == "甲_R5_1%穿越") & (pre["狀態"] == "保留")].reset_index(drop=True)
    ok = 0; why = {}
    for i in rng.choice(len(pk), 15, replace=False):
        r = pk.iloc[int(i)].to_dict(); r["T_date"] = r["T"]
        g, w = geo(r["sid"], r, cal)
        ok += int(g); why[w] = why.get(w, 0) + 1
        det.append({"查核": "②", "sid": r["sid"], "T": r["T"], "通過": g, "說明": w})
    res["②幾何"] = {"抽": 15, "通過": ok, "理由": why}
    print("② 幾何 {}／15 {}".format(ok, why), flush=True)
    # ③ 18 格
    md = 0.0; same = True
    for cell, g in E.groupby("格"):
        mon = [d[:7] for d in g["T_date"]]
        m, se, lo, hi = cl(g["X"], mon)
        blk = len({min((pos[d] - pos[W0]) // 20, 114) for d in g["T_date"]})
        J = S["格"][cell]
        dd = max(abs(m - J["平均"]), abs(se - J["se_月"]), abs(lo - J["lo"]), abs(hi - J["hi"])); md = max(md, dd)
        same &= (len(g) == J["n"] and blk == J["區段數"] and min(len(g), blk) == J["n_eff"])
    res["③格重算"] = {"格數": int(E["格"].nunique()), "最大差": md, "筆數區段n_eff相同": bool(same)}
    print("③ {} 格重算最大差 {:.1e}｜筆數區段 n_eff 相同 {}".format(E["格"].nunique(), md, same), flush=True)
    pd.DataFrame(det + [dict(x, 查核="①") for x in ck["R_e明細"]]).to_csv(os.path.join(OUT, "check_detail.csv"), index=False)
    allok = ck["判"] and ok == 15 and md < 1e-12 and same
    res["全部通過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if allok else "⛔ 有不符", flush=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()

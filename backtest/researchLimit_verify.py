# -*- coding: utf-8 -*-
"""PREREG限價 獨立查核（⛔ 不 import researchLimit／limit_entry／backtest 任何模組；只用 csv、decimal、numpy、pandas）。

① 從逐筆檔 resultsLimit/trades.csv.gz 重算三格 D ＝ mean(r20_Lk − r20_M0) 與月分群 CR0 CI，對 summary.json。
② 抽 20 筆（種子 20260925）用【原始價 CSV ＋ data/adj 逐事件連乘還原因子】手算：限價 P（Decimal 取整）、
   5 日內成交判定、成交價、H20 收盤出場報酬；日曆自己用 calendar_twse.csv 的字串數。
   20 筆 ＝ 14 筆有成交（L1／L2／L3 輪流）＋ 6 筆沒成交；只抽 x20_status＝ok（出場在排程日收盤）者。
"""
import os, csv, json
from decimal import Decimal, ROUND_FLOOR
import numpy as np, pandas as pd

ROOT = os.path.expanduser("~/tw-p17")
DATA = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.join(ROOT, "backtest", "resultsLimit")
COST = 0.00585

T = pd.read_csv(os.path.join(OUT, "trades.csv.gz"), dtype={"sid": str})
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
res = {}

# ── ① 三格 D 與月分群 CI
for k in (1, 2, 3):
    d = (T[f"r20_L{k}"] - T["r20_M0"]).dropna()
    mon = T.loc[d.index, "month"].to_numpy()
    x = d.to_numpy(float); n = len(x); m = x.mean()
    sums = {}
    for g, v in zip(mon, x - m):
        sums[g] = sums.get(g, 0.0) + v
    se = np.sqrt(sum(v * v for v in sums.values())) / n
    lo, hi = m - 1.96 * se, m + 1.96 * se
    J = S["判定_H20"][f"L{k}"]
    diff = max(abs(m - J["D"]), abs(lo - J["lo"]), abs(hi - J["hi"]))
    res[f"L{k}"] = {"D": m, "lo": lo, "hi": hi, "月數": len(sums), "n": n, "與 summary 最大差": diff}
    assert diff < 1e-12 and len(sums) == J["月數"] and n == J["n"], (k, diff)
    print("① L{}：D {:+.4f}%  CI [{:+.4f}%, {:+.4f}%]  月 {}  n {:,}｜與主程式最大差 {:.1e}".format(k, m * 100, lo * 100, hi * 100, len(sums), n, diff))

# ── ② 20 筆手算
cal = [r["date"] for r in csv.DictReader(open(os.path.join(DATA, "meta", "calendar_twse.csv"), encoding="utf-8"))]
cal = sorted(cal)


def tick(p):
    p = Decimal(p)
    return Decimal("0.01") if p < 10 else Decimal("0.05") if p < 50 else Decimal("0.1") if p < 100 else \
        Decimal("0.5") if p < 500 else Decimal("1") if p < 1000 else Decimal("5")


def P_of(close_s, k):
    raw = Decimal(close_s) * (Decimal(100 - k) / Decimal(100))
    t = tick(raw)
    return float((raw / t).to_integral_value(rounding=ROUND_FLOOR) * t)


def F_of(ev, ds):
    f = 1.0
    for dd, fac in ev:
        if dd > ds:
            f *= fac
    return f


ok = T[T["x20_status"] == "ok"]
rng = np.random.default_rng(20260925)
picks = []
for j in range(14):
    k = j % 3 + 1
    pool = ok[ok[f"L{k}_fill_raw"].notna()]
    picks.append((int(pool.index[rng.integers(len(pool))]), k))
for j in range(6):
    k = j % 3 + 1
    pool = ok[ok[f"L{k}_fill_raw"].isna()]
    picks.append((int(pool.index[rng.integers(len(pool))]), k))
mx = 0.0; n_ok = 0
for idx, k in picks:
    r = T.loc[idx]; sid = r["sid"]
    rows = {x["date"]: x for x in csv.DictReader(open(os.path.join(DATA, "stocks", sid + ".csv"), encoding="utf-8"))}
    ev = []
    pa = os.path.join(DATA, "adj", sid + ".csv")
    if os.path.exists(pa):
        ev = [(x["date"], float(x["factor"])) for x in csv.DictReader(open(pa, encoding="utf-8"))]
    md = str(r["m_date"]); ed = str(r["e_date"])
    im = cal.index(md); ie = cal.index(ed)
    assert ie == im + 1, "⛔ e 不是 m 的下一個交易日"
    P = P_of(rows[md]["close"], k)
    assert abs(P - r[f"L{k}_P"]) < 1e-9, (sid, P, r[f"L{k}_P"])
    fill_d, fill_px = None, None
    for j in range(5):
        ds = cal[ie + j]
        if ds not in rows:
            continue
        lo_s, op_s, cl_s = rows[ds]["low"], rows[ds]["open"], rows[ds]["close"]
        if not cl_s or float(cl_s) <= 0 or not lo_s or float(lo_s) <= 0:
            continue
        if float(lo_s) <= P + 1e-9:
            fill_d = ds; fill_px = min(float(op_s), P) if op_s and float(op_s) > 0 else P
            break
    xd = cal[ie + 19]                                     # H20：進場日算第 1 天 ⇒ 第 20 個交易日
    x_adj = float(rows[xd]["close"]) * F_of(ev, xd)
    m0_adj = float(rows[ed]["open"]) * F_of(ev, ed)
    hand_m0 = x_adj / m0_adj - 1 - COST if r["M0_status"] == "ok" else 0.0
    if fill_d is None:
        hand = 0.0
        assert pd.isna(r[f"L{k}_fill_raw"]), (sid, "手算沒成交、程式有成交")
    else:
        hand = x_adj / (fill_px * F_of(ev, fill_d)) - 1 - COST
        assert cal.index(fill_d) == int(r[f"L{k}_t"]) - int(r["e"]) + ie, (sid, "成交日不同")
        assert abs(fill_px - r[f"L{k}_fill_raw"]) < 1e-9, (sid, "成交價不同")
    d1 = abs(hand - r[f"r20_L{k}"]); d2 = abs(hand_m0 - r["r20_M0"])
    mx = max(mx, d1, d2); n_ok += 1
    print("② {} L{} m {} P {:.2f}｜成交 {} @ {}｜出 {}｜L 程式 {:+.6f} 手算 {:+.6f}｜M0 程式 {:+.6f} 手算 {:+.6f}｜差 {:.1e}".format(
        sid, k, md, P, fill_d or "—", "{:.2f}".format(fill_px) if fill_px else "—", xd, r[f"r20_L{k}"], hand, r["r20_M0"], hand_m0, max(d1, d2)))
assert mx < 1e-10, mx
res["手算20筆"] = {"筆數": n_ok, "最大差": mx}
print("② 手算 {} 筆：成交判定、成交價、成交日全同；報酬最大差 {:.1e}".format(n_ok, mx))
json.dump(res, open(os.path.join(OUT, "verify.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print("== 獨立查核過 ==")

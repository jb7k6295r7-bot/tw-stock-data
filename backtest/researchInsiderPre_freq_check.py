# -*- coding: utf-8 -*-
"""researchInsiderPre_freq 對帳（獨立寫法；⛔ 不讀、不算任何進場後報酬）——回測線計算子代理，2026-10-21。
 C1 登錄 sha 獨立重算
 C2 分組、市場、合併：csv 模組讀事件表原檔、純 Python（bisect）重做 ⇒ 每個事件（組、代號、首筆日、列數）與 events.csv.gz 全同
 C3 不前視／時點：全部有 T、e 的列：T ≤ 申報日 ＜ e，(申報日, e) 之間沒有其他交易日；T、e 都在該世界日曆
 C4 股數占比抽樣（default_rng(20261021) 抽保留事件 6 筆，早年、主各 3）：自讀原檔加總預定股數（去完全重複列）、自讀 stocks／eotc 已發行股數 ⇒ 占比相同
 C5 配對抽樣（主世界 3 筆、早年 1 筆）：自寫有效 K 棒迴圈算前 12 個月報酬、自排五分位、自讀原檔判 ±60 交易日 ⇒ 主池候選數、配對代號相同
 C6 輸出欄沒有任何報酬／持有期結果欄
 C7 策略鎖相符
輸出 backtest/resultsInsiderPre/freq/check.json
"""
from __future__ import annotations

import bisect
import csv
import glob
import gzip
import json
import math
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom_freq_check as IC        # noqa: E402
from backtest import researchInsiderPre_freq as Q           # noqa: E402

OUT = Q.OUT
TRADE = ("一般交易", "盤後定價", "鉅額", "拍賣")


def grp(m, tt, to):
    s = set()
    for t in m.split("|"):
        s.add("一般交易" if any(k in t for k in TRADE) else "贈與" if "贈與" in t else "信託" if "信託" in t else "其他")
    if len(s) > 1:
        return "混合"
    g = next(iter(s))
    return "其他" if (g == "信託" and (tt == "employee_trust" or "限制員工" in to)) else g


def fnum(x):
    try:
        return float(x)
    except ValueError:
        return None


def main():
    CK = {"C1_登錄sha": IC.reg_ok(Q.REG_SHA)}
    sha, DATA = Q.ensure_data()
    raw = []
    for f in sorted(glob.glob(os.path.join(DATA, "meta", "insider_predeclare", "insider_predeclare_*.csv"))):
        raw += list(csv.DictReader(open(f, encoding="utf-8")))
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "rt", encoding="utf-8") as fh:
        E = pd.read_csv(fh, dtype={"sid": str, "配對代號": str})
    Ze = IM.build_panel("早年", 2); Zm = IM.build_panel("主", 2)
    days = sorted(set(pd.bdate_range("2003-05-01", Ze["cal"][0] - pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
                  | set(Ze["cal"].strftime("%Y-%m-%d")) | set(Zm["cal"].strftime("%Y-%m-%d")))
    pos = lambda ds: bisect.bisect_right(days, ds) - 1
    # C2
    rows = [r for r in raw if r["market"] in ("sii", "otc")]
    for r in rows:
        r["g"] = grp(r["method_raw"], r["transferee_type"], r["transferee_org"]); r["p"] = pos(r["declare_date"])
    by = defaultdict(list)
    for r in rows:
        by[(r["g"], r["stock_id"])].append(r)
    mine = []
    for (g, s), rr in by.items():
        rr.sort(key=lambda r: r["declare_date"])
        a = None; n = 0; d0 = None
        for r in rr:
            if a is not None and r["p"] - a <= 30:
                n += 1; continue
            if a is not None:
                mine.append((g, s, d0, n))
            a = r["p"]; d0 = r["declare_date"]; n = 1
        mine.append((g, s, d0, n))
    theirs = list(zip(E["組"], E["sid"], E["date"], E["列數"].astype(int)))
    CK["C2_分組合併"] = {"事件數(手/主)": [len(mine), len(theirs)], "逐筆相同": sorted(mine) == sorted(theirs),
                      "各組(手)": dict(Counter(m[0] for m in mine)), "上市櫃列數(手)": len(rows)}
    # C3
    cals = {"早年": set(Ze["cal"].strftime("%Y-%m-%d")), "主": set(Zm["cal"].strftime("%Y-%m-%d"))}
    sc = {"早年": sorted(cals["早年"]), "主": sorted(cals["主"])}
    bad = n = 0
    for d, T, e, wn in zip(E["date"], E["T"], E["e"], E["世界"]):
        if not isinstance(T, str) or not T:
            continue
        n += 1
        c = sc[wn]
        between = bisect.bisect_left(c, e) - bisect.bisect_right(c, d)
        if not (T <= d < e) or between != 0 or T not in cals[wn] or e not in cals[wn]:
            bad += 1
    CK["C3_時點"] = {"檢查": n, "違反": bad}
    # C4 占比
    K = E[E["st"] == "保留"].reset_index(drop=True)
    rng = np.random.default_rng(20261021)
    rawby = defaultdict(list)
    for r in rows:
        rawby[(r["g"], r["stock_id"])].append(r)
    da = None
    C4 = []
    picks = list(rng.choice(np.flatnonzero(K["世界"] == "早年"), 3, replace=False)) + list(rng.choice(np.flatnonzero(K["世界"] == "主"), 3, replace=False))
    for k in picks:
        r = K.iloc[int(k)]
        d0, d1 = r["date"], r["末筆"]
        seen = set(); tot = 0.0
        for x in rawby[(r["組"], r["sid"])]:
            if not (d0 <= x["declare_date"] <= d1) or x["p"] - pos(d0) > 30:
                continue
            key = tuple(x[c] for c in raw[0].keys())
            if key in seen:
                continue
            seen.add(key)
            if r["組"] == "一般交易" and (x["shares_split"] or x["shares"]):
                v = sum(fnum(y) for y in x["shares_split"].split("|")) if x["shares_split"] else fnum(x["shares"])
            else:
                v = (fnum(x["plan_own"]) or 0) + (fnum(x["plan_trust"]) or 0)
            tot += v
        if r["世界"] == "主":
            st = list(csv.DictReader(open(os.path.join(Zm["data"], "stocks", f"{r['sid']}.csv"), encoding="utf-8")))
            so = [float(x["shares"]) for x in st if x["date"] <= r["T"] and fnum(x["shares"]) and float(x["shares"]) > 0]
        else:
            if da is None:
                da = pd.read_pickle(Q.EOTC_DAILY)
            x = da[(da["stock_id"] == r["sid"]) & (da["date"].astype(str) <= r["T"])].sort_values("date")
            so = [float(v) for v in pd.to_numeric(x["shares"], errors="coerce") if v and v > 0]
        so = so[-1] if so else float("nan")
        mine_r = tot / so
        C4.append({"sid": r["sid"], "date": d0, "組": r["組"], "世界": r["世界"], "占比(手/主)": [round(mine_r, 8), round(float(r["占比"]), 8)],
                   "相同": bool(abs(mine_r - float(r["占比"])) < 1e-9)})
        print(C4[-1], flush=True)
    CK["C4_占比抽樣"] = C4
    # C5 配對
    decl = defaultdict(list)
    for r in raw:
        decl[r["stock_id"]].append(pos(r["declare_date"]))
    C5 = []
    KM = K[K["配對"].isin(["主配對", "配對失敗"])]
    picks = list(rng.choice(np.flatnonzero(KM["世界"] == "主"), 3, replace=False)) + list(rng.choice(np.flatnonzero(KM["世界"] == "早年"), 1, replace=False))
    for k in picks:
        r = KM.iloc[int(k)]; Z = Zm if r["世界"] == "主" else Ze; cal = Z["cal"]
        T = int(cal.searchsorted(pd.Timestamp(r["T"]))); a_day = cal[T] - pd.DateOffset(months=12)
        xs = {}
        for i, s in enumerate(Z["sids"]):
            if not (Z["G"][i, T] and np.isfinite(Z["C"][i, T])):
                continue
            mc = Z["MC"][i, T]
            if not (np.isfinite(mc) and mc > 0):
                continue
            vp = [p for p in np.flatnonzero(np.isfinite(Z["C"][i, :T + 1])) if cal[p] <= a_day]
            if not vp:
                continue
            pa = vp[-1]
            if Z["BAD"][i, pa + 1:T + 1].any():
                continue
            xs[s] = (mc, Z["C"][i, T] / Z["C"][i, pa] - 1)
        rs = np.array([v[1] for v in xs.values()]); qr = np.quantile(rs, np.linspace(0.2, 0.8, 4))
        qui = lambda x: int((qr <= x).sum())
        s0 = r["sid"]; m0, r0 = xs[s0]; pT = pos(r["T"])
        non = [s for s in xs if s != s0 and not any(pT - 60 <= p <= pT + 60 for p in decl.get(s, []))]
        prim = [s for s in non if qui(xs[s][1]) == qui(r0)]
        best = min(prim, key=lambda s: abs(math.log(xs[s][0] / m0))) if prim else None
        theirs_c = int(r["主池候選數"]); theirs_b = r["配對代號"] if isinstance(r.get("配對代號"), str) else None
        C5.append({"sid": s0, "date": r["date"], "組": r["組"], "世界": r["世界"], "主池(手/主)": [len(prim), theirs_c], "配對(手/主)": [best, theirs_b],
                   "相同": len(prim) == theirs_c and best == theirs_b})
        print(C5[-1], flush=True)
    CK["C5_配對抽樣"] = C5
    badcols = [c for c in E.columns if any(w in str(c) for w in ("報酬", "ret", "CAR", "超額", "持有報"))]
    CK["C6_無報酬欄"] = {"可疑欄": badcols, "欄": list(E.columns)}
    CK["C7_策略鎖"] = IC.lock_ok()
    CK["全過"] = bool(CK["C1_登錄sha"][0] and CK["C2_分組合併"]["逐筆相同"] and bad == 0 and all(x["相同"] for x in C4)
                    and all(x["相同"] for x in C5) and not badcols and CK["C7_策略鎖"][0])
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("全過" if CK["全過"] else "⛔ 有不符", CK["C2_分組合併"]["事件數(手/主)"], CK["C2_分組合併"]["逐筆相同"], CK["C3_時點"], CK["C7_策略鎖"])


if __name__ == "__main__":
    main()

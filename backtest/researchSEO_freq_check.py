# -*- coding: utf-8 -*-
"""researchSEO_freq 對帳（獨立寫法；⛔ 不讀、不算任何進場後報酬）——回測線計算子代理，2026-10-21。
 C1 登錄 sha 獨立重算
 C2 分組、ipo 排除、12 個月去重：csv 模組讀事件表原檔、純 Python 重做 ⇒ 每列組別、是否略過與 events.csv.gz 全同；各組筆數相同
 C3 不前視／時點：全部有 T、e 的列：T ≤ 公告日 ＜ e，且 (公告日, e) 之間沒有其他交易日（e ＝ 下一交易日）
 C4 抽樣手算（default_rng(20261021) 抽主世界保留事件 4 筆）：自寫有效 K 棒迴圈算前 12 個月報酬、自排十分位／五分位、自讀事件表原檔判前後 3 年
    ⇒ 主池、放寬池候選數相同；發行公司 load_bars＋Frame.gate[T] 重讀為真
 C5 策略鎖相符
輸出 backtest/resultsSEO/freq/check.json
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom_freq_check as IC        # noqa: E402
from backtest import researchSEO_freq as SQ                 # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import patterns as P                          # noqa: E402

OUT = SQ.OUT


def add12(d):
    y, m, dd = d.year + 1, d.month, d.day
    if m == 2 and dd == 29:
        dd = 28
    return pd.Timestamp(y, m, dd)


def main():
    CK = {"C1_登錄sha": IC.reg_ok(SQ.REG_SHA)}
    sha, DATA = IM.ensure_main()
    raw = list(csv.DictReader(open(os.path.join(DATA, "meta", "seo_cb_events", "seo_cb_events.csv"), encoding="utf-8")))
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "rt", encoding="utf-8") as fh:
        E = pd.read_csv(fh, dtype={"sid": str, "time": str})
    # C2
    rows = [r for r in raw if r["ipo"] != "1"]
    for r in rows:
        r["g"] = ("S私" if r["private"] == "1" else "S") if r["class"] == "seo" else ("C私" if r["private"] == "1" else "C")
    rows.sort(key=lambda r: (r["date"], r["time"], r["stock_id"]))
    last = {}; mine = []
    for r in rows:
        d = pd.Timestamp(r["date"]); k = (r["g"], r["stock_id"])
        skip = k in last and d < add12(last[k])
        if not skip:
            last[k] = d
        mine.append((r["stock_id"], r["date"], r["g"], skip))
    theirs = list(zip(E["sid"], E["date"], E["組"], E["st"] == "12個月內重複略過"))
    CK["C2_去重分組"] = {"列數(手/主)": [len(mine), len(theirs)], "逐列相同": sorted(mine) == sorted(theirs),
                      "各組(手)": dict(Counter(g for _, _, g, s in mine if not s)), "ipo(手)": sum(r["ipo"] == "1" for r in raw)}
    # C3
    W = {wn: AT.load_world(wn) for wn in ("早年", "主")}
    bad = 0; n = 0
    for d, T, e, wn in zip(E["date"], E["T"], E["e"], E["世界"]):
        if not isinstance(T, str) or not T:
            continue
        n += 1
        cal = W[wn]["cal"]
        between = ((cal > pd.Timestamp(d)) & (cal < pd.Timestamp(e))).sum()
        if not (T <= d < e) or between != 0 or pd.Timestamp(T) not in cal or pd.Timestamp(e) not in cal:
            bad += 1
    CK["C3_時點"] = {"檢查": n, "違反": bad}
    # C4
    Z = IM.panel_aux(IM.build_panel("主", 2)); cal = Z["cal"]
    iss = {}
    for r in raw:
        iss.setdefault(r["stock_id"], []).append(pd.Timestamp(r["date"]))
    K = E[(E["st"] == "保留") & (E["世界"] == "主") & E["主池候選數"].notna()]
    rng = np.random.default_rng(20261021)
    C4 = []
    import backtest.data as D
    D.DATA = W["主"]["data"]
    for k in rng.choice(len(K), 4, replace=False):
        r = K.iloc[int(k)]; d = pd.Timestamp(r["date"]); T = int(cal.searchsorted(pd.Timestamp(r["T"])))
        a_day = cal[T] - pd.DateOffset(months=12)
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
        mcs = np.array([v[0] for v in xs.values()]); rs = np.array([v[1] for v in xs.values()])
        qm = np.quantile(mcs, np.linspace(0.1, 0.9, 9)); qr = np.quantile(rs, np.linspace(0.2, 0.8, 4))
        dec = lambda x: int((qm <= x).sum()); qui = lambda x: int((qr <= x).sum())
        s0 = r["sid"]; m0, r0 = xs[s0]
        lo, hi = d - pd.DateOffset(years=3), d + pd.DateOffset(years=3)
        non = [s for s in xs if s != s0 and not any(lo <= x <= hi for x in iss.get(s, []))]
        same_d = [s for s in non if dec(xs[s][0]) == dec(m0)]
        prim = [s for s in same_d if qui(xs[s][1]) == qui(r0)]
        B = R.load_bars(s0, W["主"]["mk"].get(s0, "twse"), cal)
        g = bool(np.asarray(P.Frame(B["df"], set()).gate, bool)[T]) and bool(W["主"]["PV"][W["主"]["ix"][s0]][T])
        C4.append({"sid": s0, "date": r["date"], "組": r["組"], "主池(手/主)": [len(prim), int(r["主池候選數"])],
                   "放寬池(手/主)": [len(same_d), int(r["放寬池候選數"])], "閘內": g,
                   "相同": len(prim) == int(r["主池候選數"]) and len(same_d) == int(r["放寬池候選數"]) and g})
        print(C4[-1], flush=True)
    CK["C4_抽樣手算"] = C4
    CK["C5_策略鎖"] = IC.lock_ok()
    CK["全過"] = bool(CK["C1_登錄sha"][0] and CK["C2_去重分組"]["逐列相同"] and bad == 0 and all(x["相同"] for x in C4) and CK["C5_策略鎖"][0])
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("全過" if CK["全過"] else "⛔ 有不符", CK["C2_去重分組"]["逐列相同"], CK["C3_時點"], CK["C5_策略鎖"])


if __name__ == "__main__":
    main()

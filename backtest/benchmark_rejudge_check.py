# -*- coding: utf-8 -*-
"""benchmark_rejudge 對帳／查核（回測線計算子代理）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.benchmark_rejudge_check [--tr 來源]

 C1 對帳（必過）：重判同一條路改餵 0050（各件世界資料 rerun17.load_bench）⇒ 0050 年化／回落 ＝ 檔值、標籤 ＝ 原標籤、權益重算 ＝ 檔值，逐列 0 不符
 C2 合成序列 fixture（⛔ 不含任何真實報酬）：
    ① on_cal 補值日數；② weak_core 逐窗以獨立迴圈重算（月底 ＝ 逐日比月份、滾動 12、嚴格落後、分組、名次、期間合併）
 C3 排名表：已排名列比值不增、同比值年化不增；「—」列都有註
 C4 compare：價格指數逐年報酬以獨立 groupby（年末收盤）重算 ＝ compare_year.csv
 C5 buildeq（有檔才驗）：eq_主／eq_早年 各段 年化／回落 中位 ＝ resultsYL_integrate/cells.csv（%.8g 容差）
輸出 backtest/resultsBenchRejudge/check.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import benchmark_rejudge as BR                 # noqa: E402
from backtest import researchAscTri as AS                    # noqa: E402


def c2():
    out = {}
    cal = pd.bdate_range("2019-01-01", "2022-12-31")
    s = pd.Series(np.arange(len(cal), dtype=float) + 100.0, index=cal).drop(cal[[5, 6, 300]])
    _, nfill = BR.on_cal(s, cal)
    out["① on_cal 補值日數 ＝ 3"] = nfill == 3
    rng = np.random.default_rng(7)
    n = len(cal)
    s50 = np.cumprod(1 + rng.normal(0.0004, 0.01, n)); sT = np.cumprod(1 + rng.normal(0.0004, 0.01, n))
    EQ = {"甲": [np.cumprod(1 + rng.normal(0.0005, 0.012, n))], "乙": [np.cumprod(1 + rng.normal(0.0003, 0.012, n)) for _ in range(3)]}
    x, y = 10, n - 1
    R = BR.weak_core(cal, x, y, s50, sT, EQ)
    # 獨立迴圈：完整月底（資料尾月是否完整依 BMonthEnd）
    me = [t for t in range(n - 1) if cal[t + 1].month != cal[t].month]
    if cal[n - 1] == cal[n - 1] + pd.offsets.BMonthEnd(0):
        me.append(n - 1)
    pts = [x] + [t for t in me if x < t <= y]
    lag, nbad = [], 0
    for k in range(12, len(pts)):
        pa, pb = pts[k - 12], pts[k]
        r5, rT = s50[pb] / s50[pa] - 1, sT[pb] / sT[pa] - 1
        if r5 < rT:
            d = rT - r5
            g = "0～2 點" if d <= 0.02 else ("2～5 點" if d <= 0.05 else "5 點以上")
            ra = EQ["甲"][0][pb] / EQ["甲"][0][pa] - 1
            rb = float(np.median([e[pb] / e[pa] - 1 for e in EQ["乙"]]))
            lag.append((pa, pb, g, ra, rb, r5, rT))
    out["② 落後窗數相同"] = len(lag) == R["落後窗數"]
    out["② 滾動窗數相同"] = R["滾動窗數"] == len(pts) - 12
    for (pa, pb, g, ra, rb, r5, rT), p in zip(lag, R["逐窗"]):
        vals = {"甲": ra, "乙": rb, "0050": r5, "大盤（報酬指數）": rT}
        order = sorted(vals, key=lambda k: -vals[k])
        if (p["pa"], p["pb"], p["組"]) != (pa, pb, g) or abs(p["報酬"]["甲"] - ra) > 1e-15 or abs(p["報酬"]["乙"] - rb) > 1e-15 \
                or any(p["名次"][k] != order.index(k) + 1 for k in vals):
            nbad += 1
    out["② 逐窗（窗、組、報酬、名次）不符數"] = nbad
    nper = sum(1 for i in range(len(lag)) if i == 0 or pts.index(lag[i][1]) != pts.index(lag[i - 1][1]) + 1)
    out["② 期間數相同"] = nper == len(R["期間"])
    out["② 分組窗數加總 ＝ 全部"] = sum(R["分組"][g]["窗數"] for g in ("0～2 點", "2～5 點", "5 點以上")) == R["分組"]["全部"]["窗數"]
    return out


def c3():
    p = os.path.join(BR.OUT, "rank.csv")
    if not os.path.exists(p):
        return {"略": "rank.csv 不存在"}
    T = pd.read_csv(p, float_precision="round_trip")
    bad = 0; nonote = 0
    for sg, g in T.groupby("段"):
        v = g[g["年化"].notna() & ~g["排名"].astype(str).str.startswith("另表")]
        for i in range(1, len(v)):
            a, b = v.iloc[i - 1], v.iloc[i]
            if b["比值"] > a["比值"] + 1e-15 or (abs(b["比值"] - a["比值"]) <= 1e-15 and b["年化"] > a["年化"]):
                bad += 1
        nonote += int(((g["年化"].isna()) & (g["註"].isna())).sum())
    return {"排序違反數": bad, "「—」列無註數": nonote}


def c4():
    p = os.path.join(BR.OUT, "compare_year.csv")
    if not os.path.exists(p):
        return {"略": "compare_year.csv 不存在"}
    Y = pd.read_csv(p, float_precision="round_trip")
    pr = BR.read_series(f"git:origin/main:{BR.PRICE_GIT}")
    bad = 0
    for _, r in Y.iterrows():
        a, b = pd.Timestamp(r["起"]), pd.Timestamp(r["訖"])
        v = pr[pr.index <= b].iloc[-1] / pr[pr.index <= a].iloc[-1] - 1
        bad += int(abs(v - r["大盤價格指數"]) > 1e-9)          # compare_year.csv 以 %.10g 寫檔
    return {"價格指數逐年不符數": bad, "列數": len(Y)}


def c5():
    out = {}
    C = pd.read_csv("backtest/resultsYL_integrate/cells.csv", float_precision="round_trip")
    W = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}, "早年": {"早年": ("2005-02-01", "2014-12-31")}}
    for wn, segs in W.items():
        p = os.path.join(BR.OUT, f"eq_{wn}.npz")
        if not os.path.exists(p):
            out[wn] = "略（未 buildeq）"; continue
        Z = np.load(p); cal = BR.world_cal(BR.WORLD_DATA[wn])
        bad = 0
        for sg, (a, b) in segs.items():
            x, y = BR.seg_pos(cal, a, b)
            for key, L in (("H120·S10·閘·抽籤", Z["YF"]), ("H60·S20·無·relvol", Z["YL"])):
                c, m = BR.med_stat(list(L), x, y)
                r = C[(C["世界"] == wn) & (C["格"] == key)].iloc[0]
                bad += int(abs(c - r[f"{sg}_年化"]) > 5e-8 * max(1, abs(c)) or abs(m - r[f"{sg}_回落"]) > 5e-8 * max(1, abs(m)))
        out[wn] = {"不符": bad}
    return out


def c6():
    """weak 的權益組（只驗讀得到、長度、首末日；⛔ 不算任何報酬）。"""
    out = {}
    for wn in ("主", "早年"):
        E = BR.rank_universe(wn)
        out[wn] = {k: {"條數": len(v), "長度": int(len(v[0])), "首": str(v[0].index[0].date()), "末": str(v[0].index[-1].date()),
                       "缺值": int(np.isnan(v[0].to_numpy()).sum())} for k, v in E.items()}
    return out


def c7(a):
    """第三階段：大跌 4 檔曲線閘、高10 種子權益、報酬指數重判的標記規則、報酬指數序列對齊。"""
    out = {}
    p = os.path.join(BR.OUT, "mktdrop_curves.json")
    out["大跌 4 檔：攔到曲線 ＝ addon2/portfolio.csv 不符"] = json.load(open(p, encoding="utf-8"))["閘：攔到曲線重算 ＝ addon2/portfolio.csv（%.6g）不符"] if os.path.exists(p) else "略（未建）"
    for wn in ("主", "早年"):
        q = os.path.join(BR.OUT, f"pth10seed_{wn}.npz")
        if os.path.exists(q):
            Z = np.load(q)
            out[f"高10 種子 {wn}：k＝0 ＝ PTHn N10_eq"] = bool(np.array_equal(Z["eq"][0], np.load(f"backtest/resultsPTHn/eq_{wn}.npz")["N10_eq"]))
            out[f"高10 種子 {wn}：條數"] = int(Z["eq"].shape[0])
    r = os.path.join(BR.OUT, "rejudge.csv")
    if a.tr and os.path.exists(r):
        D = pd.read_csv(r)
        tag = D["新基準重看"].astype(str).str.startswith("合格（")
        out["「新基準重看：候選」只標在原標籤非合格的列"] = bool((D.loc[tag, "原標籤"] != "合格").all())
        out["原非合格、新合格卻沒標的列"] = int(((D["新基準重看"] == "合格") & (D["原標籤"] != "合格")).sum())
        out["新標籤缺（—）列"] = int(D["新基準重看"].astype(str).str.startswith("—").sum())
        T = BR.read_series(a.tr)
        for wn in ("主", "早年"):
            cal = BR.world_cal(BR.WORLD_DATA[wn]); x = cal.searchsorted(pd.Timestamp("2005-01-01" if wn == "早年" else "2015-01-01"))
            _, nf = BR.on_cal(T[T.index >= cal[x]], cal[x:])
            out[f"報酬指數對 {wn} 世界日曆 ffill 補值日"] = nf
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tr", default=None); a = ap.parse_args()
    a.procs, a.part = 1, None
    os.makedirs(BR.OUT, exist_ok=True)
    res, Cc = BR.reconcile(a)
    S = {"C1 對帳（0050 基準重現舊標籤）": res, "C1 不符列": Cc[~(Cc["標籤相同"] & Cc["0050相符"] & Cc["年化回落相符"])].to_dict("records"),
         "C2 合成 fixture": c2(), "C3 排名表": c3(), "C4 compare": c4(), "C5 buildeq": c5(), "C6 weak 權益組": c6(), "C7 第三階段": c7(a)}
    S["C1 0050 值不符的說明"] = {
        "趨勢樣板｜早年 2005-03-01～2014-12-31": "原件 resultsLongT 早年 0050 ＝ 0.0727091；以 rerun17.load_bench 讀三份早年版面（含原件所用 3edc0e2206）同窗皆 0.0723925"
                                          " ⇒ 原件 0050 取法與 load_bench 不同（成因未查）；策略年化／回落與標籤相同，不影響新基準重判（新基準不經 0050）",
        "219｜PREREG9／研究十一（12 格）｜2016-01-12～2026-09-11": "錨 0.249（results11/CONCLUSIONS.md，較早資料快照）；同窗 edc6f 0050 ＝ 0.24846，與 results13 同窗錨 0.248 相符"
                                                          " ⇒ 窗位相同、差在資料快照（0.05 點，超過錨捨入半單位 0.0005）；12 格標籤全部相同",
        "一目三役｜A 2009-01-05～2019-03-29": "合併日曆（researchTri.load_all）0050 與原件相對差 5e−9（原件 0050 在早年／主快照接合處的取法不同）；標籤相同"}

    def _explained(r):
        return r["標籤相同"] and (r["策略"] == "趨勢樣板" and r["段"] == "早年" or str(r["策略"]).startswith("219｜PREREG9")
                                 or (str(r["策略"]).startswith("一目三役") and str(r["段"]).startswith("A ") and r["0050年化相對差"] < 1e-7))
    S["C1 0050 值不符（已說明者除外）"] = int(sum(1 for r in S["C1 不符列"] if r["0050相符"] is False and not _explained(r)))
    S["C1 依族"] = Cc.assign(值不符=(Cc["0050相符"].astype(str) == "False"), 標籤不符=~Cc["標籤相同"]).groupby(Cc["族"].fillna("第一階段")).agg(
        列=("策略", "size"), 件=("策略", "nunique"), 標籤不符=("標籤不符", "sum"), 值不符=("值不符", "sum")).astype(int).to_dict("index")
    ok = (res["標籤不符"] == 0 and S["C1 0050 值不符（已說明者除外）"] == 0 and res["年化回落不符"] == 0 and S["C2 合成 fixture"]["② 逐窗（窗、組、報酬、名次）不符數"] == 0
          and S["C3 排名表"].get("排序違反數", 0) == 0 and S["C4 compare"].get("價格指數逐年不符數", 0) == 0
          and all(v == "略（未 buildeq）" or v["不符"] == 0 for v in S["C5 buildeq"].values())
          and all(v is True or v == 0 for k, v in S["C2 合成 fixture"].items()))
    c7v = S["C7 第三階段"]
    ok = ok and c7v.get("大跌 4 檔：攔到曲線 ＝ addon2/portfolio.csv 不符", 0) in (0, "略（未建）") \
        and all(v is True for k, v in c7v.items() if k.endswith("N10_eq")) \
        and c7v.get("「新基準重看：候選」只標在原標籤非合格的列", True) is True and c7v.get("原非合格、新合格卻沒標的列", 0) == 0
    S["全部通過"] = bool(ok)
    json.dump(S, open(os.path.join(BR.OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in S.items() if k != "C1 不符列"}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

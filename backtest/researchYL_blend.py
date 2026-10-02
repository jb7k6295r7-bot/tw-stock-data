# -*- coding: utf-8 -*-
"""營量 v1 ＋ 營飆 v1 資金比例合併（使用者問：「營量、營飆兩個融合呢？如果差不多的話！」；只描述，⛔ 不計 N、⛔ 不調任何策略參數）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_blend [--check]

═══ 讀法（寫死於 2026-10-02 10:34（台北），在算任何數字之前）═══
 B1 本體與閘（同 researchYL_flowexit F1，A ＝ 正式 T1、停止交易強制出場開）：ctx ＝ researchT1fix.build_ctx(True)；
    營量 v1 ＝ FE.run_engine(ctx, "營量 v1", sig13, "H60", 20, r＝0, SF)（relvol 挑選、不抽籤 ⇒ 1 條）
    營飆 v1 ＝ FE.run_engine(ctx, "營飆 v1", sig, "H120", 10, r, SF)，r ＝ 0～199
    閘：每條權益曲線的 eq_sha、first、end、trades 與主窗年化／回落 repr ＝ resultsT1fix/seeds.csv.gz（c13｜t1｜r0；c1｜t1｜r0～199）
 B2 資金比例（營飆：營量）＝ 100:0、67:33（使用者現在用的 2:1，w ＝ 2/3）、50:50、33:67（w ＝ 1/3）、0:100，全部照報，⛔ 不挑最佳
    營飆每顆種子各自配同一條營量（營量只有一條）⇒ 每個比例 200 條合併曲線 ⇒ 報中位、p10～p90
 B3 兩種合併法（權益曲線起點皆 1；first ＝ 兩者較早、end ＝ 兩者較晚以前的共同段 min(end)）：
    ① 每日再平衡：r_t ＝ w r營飆_t ＋ (1−w) r營量_t，eq ＝ ∏(1＋r)（⚠ 近似：不計再平衡成本與零股，兩邊各自照自己的槽位跑）
    ② 不再平衡：eq ＝ w eq營飆 ＋ (1−w) eq營量（一開始分好、各自滾）；end 之後兩條都持平（引擎本來就 equity[end:] ＝ equity[end−1]）
    端點閘：② 的 100:0、0:100 ＝ 單一策略逐位元；① 的端點年化／回落與單一策略差 ≤ 1e−12（累乘的浮點順序不同，⛔ 不要求逐位元）
 B4 指標（同一條權益曲線切窗，RR.win_metrics）：年化、最大回落、年化 ÷ |回落|；期間 ＝ 全部（主窗 2017-03-02～2026-08-24）、2021-01～2023-12、2024-01～2026-08-24
    各年報酬：主窗內每個日曆年，年末（或窗尾）÷ 前一年末（2017 用窗首）− 1
    對 0050（使用者判準，同 researchYLexit.label）：年化 ＞ 0050 同段 且 年化÷|回落| ≥ 0050 同段 ⇒ 合格；只有年化 ＞ ⇒ 另列；否則不合格
      0050 ＝ RR.bench_row（同段還原收盤）；報「各顆標籤的比例」與「中位數字對 0050 的標籤」
 B5 相似度（主窗；營飆每顆各算，報中位、p10～p90）：
    ⓐ 同日入選：候選層 ＝ (代號, 進場位置) 在兩邊候選表的交集 ÷ 各自筆數；實買層 ＝ 兩邊實際買進 (日, 代號) 交集 ÷ 各自買進筆數
    ⓑ 持股重疊（按金額）：每日 Σ_檔 min(營量該檔市值 ÷ 營量權益, 營飆該檔市值 ÷ 營飆權益)，主窗逐日平均；
       市值由 audit 重建：買進列 amt、px ⇒ 持有 [買進日, 賣出日) 每日市值 ＝ amt × 收盤 ÷ px（同引擎 hv 式）
    ⓒ 日報酬相關係數（主窗 t ＝ w0＋1～w1）
    ⓓ 各自虧最大的 3 個月（主窗月報酬；營飆取 200 顆月報酬中位），另一個策略當月報酬（營飆報中位、p10～p90、虧錢顆數比例）
 B6 單一融合策略（例：抱 90 天、15 檔）＝ 新參數組 ⇒ 必須走登錄，⛔ 本件不實作，網頁只寫一段說明
 B7 查核（--check，種子 0～1）：① 合併兩法逐日迴圈重算 vs 向量化；② 端點閘；③ 持股市值重建：非交易日隱含現金（權益 − Σ市值）不變（≤ 1e−9）、
    Σ權重 ≤ 1；④ 持股重疊逐日字典重算（每 7 天抽一天）；⑤ 各年報酬與 0050 標籤逐筆重算；⑥ 實買重疊用集合迴圈重算 ⇒ 全部 0 不同才算過
輸出 backtest/resultsYL_blend/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R
from backtest import rerun17 as RR
from backtest import researchYL_flowexit as FE

TIME = "2026-10-02 10:34（台北）"
OUT = "backtest/resultsYL_blend"
WTS = [(1.0, "100:0"), (2 / 3, "67:33"), (0.5, "50:50"), (1 / 3, "33:67"), (0.0, "0:100")]
METH = {"①": "每日再平衡", "②": "不再平衡"}
SEGS = FE.SEGS
NYF = 200


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def label(c, m, b):
    if not (np.isfinite(c) and np.isfinite(m)) or m == 0:
        return "—"
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def blend(eF, oF, eY, oY, w, how):
    first = min(oF["first"], oY["first"]); end = min(oF["end"], oY["end"])
    if how == "②":
        return w * eF + (1 - w) * eY, first, end
    n = len(eF); rF = np.zeros(n); rY = np.zeros(n)
    rF[1:end] = eF[1:end] / eF[:end - 1] - 1; rY[1:end] = eY[1:end] / eY[:end - 1] - 1
    return np.cumprod(1 + w * rF + (1 - w) * rY), first, end


def seg_metrics(eq, first, end, SEGP):
    out = {}
    for sg, (x, y) in SEGP.items():
        c_, m_, _ = RR.win_metrics(eq, first, end, x, y)
        out[sg] = (float(c_), float(m_))
    return out


def year_ends(cal, w0, w1):
    yrs = sorted(set(cal[w0:w1 + 1].year))
    ends = [int(np.flatnonzero((cal.year == y) & (np.arange(len(cal)) <= w1))[-1]) for y in yrs]
    return yrs, ends


def year_rets(eq, w0, ends):
    prev = w0; out = []
    for b in ends:
        out.append(float(eq[b] / eq[prev] - 1)); prev = b
    return out


def month_ends(cal, w0, w1):
    p = cal[w0:w1 + 1].to_period("M")
    keys = sorted(set(p))
    ends = [w0 + int(np.flatnonzero(p == k)[-1]) for k in keys]
    return [str(k) for k in keys], ends


def holdings_w(au, eq, closes, n, sid_index):
    """audit ⇒ 每日權重矩陣 W[檔, 日] ＝ 市值 ÷ 權益（持有 [買進日, 賣出日)）。"""
    W = np.zeros((len(sid_index), n))
    opn = {}
    for a in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
        if a["side"] == "buy":
            opn.setdefault(a["sid"], []).append((a["t"], a["amt"], a["px"]))
        else:
            t0, amt, px = opn[a["sid"]].pop(0)
            i = sid_index[a["sid"]]
            W[i, t0:a["t"]] += amt * np.asarray(closes[a["sid"]][t0:a["t"]], float) / px
    for sid, lst in opn.items():                         # 期末未賣
        for t0, amt, px in lst:
            i = sid_index[sid]
            W[i, t0:n] += amt * np.asarray(closes[sid][t0:n], float) / px
    V = W.copy()
    W /= np.asarray(eq, float)[None, :n]
    return W, V


def buys_set(au, w0, w1):
    return {(a["t"], a["sid"]) for a in au if a["side"] == "buy" and w0 <= a["t"] <= w1}


def qs(x):
    x = np.asarray(x, float)
    return {"中位": float(np.median(x)), "p10": float(np.quantile(x, .1)), "p90": float(np.quantile(x, .9))}


def setup(log):
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); w0, w1 = ctx["w0"], ctx["w1"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    SEGP = FE.seg_pos(cal, w0, w1)
    bench = RR._G["bench"]
    B50 = {sg: RR.bench_row(cal, bench, x, y + 1) for sg, (x, y) in SEGP.items()}
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    return ctx, cal, n0, w0, w1, SF, SEGP, bench, B50, ref


def gate(o, eq, rr, w0, w1):
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    return (sha(eq) == str(rr["eq_sha"]) and int(o["first"]) == int(rr["first"]) and int(o["end"]) == int(rr["end"])
            and int(o["trades"]) == int(rr["trades"]) and repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"])))


def run(log, seeds=None):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    ctx, cal, n0, w0, w1, SF, SEGP, bench, B50, ref = setup(log)
    seeds = list(range(NYF)) if seeds is None else seeds
    log(f"[ctx] {time.time() - T0:.0f}s｜主窗 {cal[w0].date()}～{cal[w1].date()}")
    gates = {}
    oY, auY = FE.run_engine(ctx, "營量 v1", ctx["sig13"], "H60", 20, 0, SF)
    eY = np.asarray(oY["equity"], float)
    gates["營量 r0 ＝ resultsT1fix（eq_sha／first／end／trades／年化回落 repr）"] = bool(gate(oY, eY, ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)].iloc[0], w0, w1))
    sids = sorted(set(ctx["sig13"]["sid"]) | set(ctx["sig"]["sid"]))
    SI = {s: i for i, s in enumerate(sids)}
    n = len(eY)
    WY, _ = holdings_w(auY, eY, ctx["closes"], n, SI)
    BY = buys_set(auY, w0, w1)
    yrs, yends = year_ends(cal, w0, w1)
    mks, mends = month_ends(cal, w0, w1)
    candY = set(zip(ctx["sig13"]["sid"], ctx["sig13"]["entry_pos"].astype(int)))
    candF = set(zip(ctx["sig"]["sid"], ctx["sig"]["entry_pos"].astype(int)))
    rY = eY[w0 + 1:w1 + 1] / eY[w0:w1] - 1
    mY = np.array([eY[b] / eY[a] - 1 for a, b in zip([w0] + mends[:-1], mends)])
    rows, yrows, sim, mF_all = [], [], [], []
    bad = 0
    for r in seeds:
        oF, auF = FE.run_engine(ctx, "營飆 v1", ctx["sig"], "H120", 10, r, SF)
        eF = np.asarray(oF["equity"], float)
        bad += int(not gate(oF, eF, ref[(ref["key"] == "c1") & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0], w0, w1))
        for w, wn in WTS:
            for how in METH:
                eq, f_, e_ = blend(eF, oF, eY, oY, w, how)
                sm = seg_metrics(eq, f_, e_, SEGP)
                row = {"r": r, "比例": wn, "合併": how}
                for sg, (c_, m_) in sm.items():
                    row[f"{sg}_年化"] = c_; row[f"{sg}_回落"] = m_
                    row[f"{sg}_比值"] = c_ / abs(m_) if m_ else np.nan
                    row[f"{sg}_0050"] = label(c_, m_, B50[sg])
                rows.append(row)
                yrows.append({"r": r, "比例": wn, "合併": how, **dict(zip([str(y) for y in yrs], year_rets(eq, w0, yends)))})
                if how == "②" and w in (1.0, 0.0):
                    gates.setdefault("② 端點 ＝ 單一策略逐位元（不同顆數）", 0)
                    gates["② 端點 ＝ 單一策略逐位元（不同顆數）"] += int(not np.array_equal(eq, eF if w == 1.0 else eY))
                if how == "①" and w in (1.0, 0.0):
                    o_, e_s = (oF, eF) if w == 1.0 else (oY, eY)
                    ref_m = seg_metrics(e_s, o_["first"], o_["end"], SEGP)
                    d = max(abs(sm[k][j] - ref_m[k][j]) for k in sm for j in (0, 1) if np.isfinite(sm[k][j]))
                    gates.setdefault("① 端點年化回落最大差", 0.0)
                    gates["① 端點年化回落最大差"] = max(gates["① 端點年化回落最大差"], float(d))
        # 相似度
        WF, _ = holdings_w(auF, eF, ctx["closes"], n, SI)
        ov = np.minimum(WY[:, w0:w1 + 1], WF[:, w0:w1 + 1]).sum(0)
        BF = buys_set(auF, w0, w1)
        rF = eF[w0 + 1:w1 + 1] / eF[w0:w1] - 1
        mF = np.array([eF[b] / eF[a] - 1 for a, b in zip([w0] + mends[:-1], mends)])
        mF_all.append(mF)
        sim.append({"r": r, "持股重疊（按金額，日均）": float(ov.mean()), "營量持股比例（日均）": float(WY[:, w0:w1 + 1].sum(0).mean()),
                    "營飆持股比例（日均）": float(WF[:, w0:w1 + 1].sum(0).mean()),
                    "重疊 ÷ 兩者較小持股": float(ov.mean() / min(WY[:, w0:w1 + 1].sum(0).mean(), WF[:, w0:w1 + 1].sum(0).mean())),
                    "實買：營飆的買進也被營量同日買": len(BF & BY) / len(BF), "實買：營量的買進也被營飆同日買": len(BF & BY) / len(BY),
                    "日報酬相關": float(np.corrcoef(rF, rY)[0, 1]), "月報酬相關": float(np.corrcoef(mF, mY)[0, 1])})
        if r % 50 == 0:
            log(f"[營飆] r{r}｜{time.time() - T0:.0f}s")
    gates["營飆 ＝ resultsT1fix（不同顆數）"] = bad
    gates["① 端點差 ≤ 1e−12"] = bool(gates["① 端點年化回落最大差"] <= 1e-12)
    S = pd.DataFrame(rows); Y = pd.DataFrame(yrows); SM = pd.DataFrame(sim)
    S.to_csv(os.path.join(OUT, "blend_seeds.csv.gz"), index=False, float_format="%.10g")
    Y.to_csv(os.path.join(OUT, "years_seeds.csv.gz"), index=False, float_format="%.10g")
    SM.to_csv(os.path.join(OUT, "similarity_seeds.csv"), index=False, float_format="%.10g")
    # 彙總
    summ = []
    for how in METH:
        for w, wn in WTS:
            g = S[(S["比例"] == wn) & (S["合併"] == how)]
            for sg in SEGS:
                c = qs(g[f"{sg}_年化"]); m = qs(g[f"{sg}_回落"]); rt = qs(g[f"{sg}_比值"])
                lab = g[f"{sg}_0050"].value_counts(normalize=True)
                summ.append({"合併": how, "比例": wn, "段": sg, "年化中位": c["中位"], "年化p10": c["p10"], "年化p90": c["p90"],
                             "回落中位": m["中位"], "回落p10": m["p10"], "回落p90": m["p90"], "比值中位": rt["中位"], "比值p10": rt["p10"], "比值p90": rt["p90"],
                             "合格比例": float(lab.get("合格", 0)), "另列比例": float(lab.get("另列", 0)), "不合格比例": float(lab.get("不合格", 0)),
                             "中位對0050": label(c["中位"], m["中位"], B50[sg]), "0050年化": B50[sg]["cagr"], "0050回落": B50[sg]["mdd"]})
    SU = pd.DataFrame(summ); SU.to_csv(os.path.join(OUT, "summary_blend.csv"), index=False, float_format="%.6g")
    ysum = []
    for how in METH:
        for w, wn in WTS:
            g = Y[(Y["比例"] == wn) & (Y["合併"] == how)]
            for y in yrs:
                q = qs(g[str(y)]); ysum.append({"合併": how, "比例": wn, "年": y, **q})
    YS = pd.DataFrame(ysum)
    b_y = year_rets(np.asarray(bench, float), w0, yends)
    YS.to_csv(os.path.join(OUT, "summary_years.csv"), index=False, float_format="%.6g")
    # 最差月份
    MF = np.vstack(mF_all); mFm = np.median(MF, 0)
    worst = {"營量最差 3 個月": [], "營飆最差 3 個月（200 顆月報酬中位）": []}
    for i in np.argsort(mY)[:3]:
        worst["營量最差 3 個月"].append({"月": mks[i], "營量": float(mY[i]), "營飆中位": float(mFm[i]), "營飆p10": float(np.quantile(MF[:, i], .1)),
                                    "營飆p90": float(np.quantile(MF[:, i], .9)), "營飆虧錢顆數比例": float((MF[:, i] < 0).mean())})
    for i in np.argsort(mFm)[:3]:
        worst["營飆最差 3 個月（200 顆月報酬中位）"].append({"月": mks[i], "營飆中位": float(mFm[i]), "營飆p10": float(np.quantile(MF[:, i], .1)),
                                                     "營飆p90": float(np.quantile(MF[:, i], .9)), "營量": float(mY[i])})
    simq = {k: qs(SM[k]) for k in SM.columns if k != "r"}
    cand = {"候選：營飆候選也是營量候選": len(candF & candY) / len(candF), "候選：營量候選也是營飆候選": len(candF & candY) / len(candY),
            "營量候選筆": len(candY), "營飆候選筆": len(candF)}
    META = {"讀法寫死": TIME, "閘": gates, "主窗": [str(cal[w0].date()), str(cal[w1].date())], "SEGP": {k: [str(cal[a].date()), str(cal[b].date())] for k, (a, b) in SEGP.items()},
            "0050": B50, "0050各年": dict(zip([str(y) for y in yrs], b_y)), "相似度": simq, "候選重疊": cand, "最差月份": worst,
            "營飆顆數": len(seeds), "耗時秒": round(time.time() - T0)}
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(META, f, ensure_ascii=False, indent=1, default=float)
    log(f"[完] 閘 {json.dumps(gates, ensure_ascii=False)}｜{time.time() - T0:.0f}s")
    return META


# ═════════════ 查核 ═════════════
def check(log):
    T0 = time.time()
    ctx, cal, n0, w0, w1, SF, SEGP, bench, B50, ref = setup(log)
    out = {"讀法寫死": TIME}
    oY, auY = FE.run_engine(ctx, "營量 v1", ctx["sig13"], "H60", 20, 0, SF); eY = np.asarray(oY["equity"], float)
    sids = sorted(set(ctx["sig13"]["sid"]) | set(ctx["sig"]["sid"])); SI = {s: i for i, s in enumerate(sids)}
    n = len(eY); yrs, yends = year_ends(cal, w0, w1)
    nd = {}
    for r in (0, 1):
        oF, auF = FE.run_engine(ctx, "營飆 v1", ctx["sig"], "H120", 10, r, SF); eF = np.asarray(oF["equity"], float)
        # ① 合併迴圈
        for w, wn in WTS:
            end = min(oF["end"], oY["end"])
            e1 = [1.0]; e2 = []
            for t in range(1, n):
                if t < end:
                    e1.append(e1[-1] * (1 + w * (eF[t] / eF[t - 1] - 1) + (1 - w) * (eY[t] / eY[t - 1] - 1)))
                else:
                    e1.append(e1[-1])
            for t in range(n):
                e2.append(w * eF[t] + (1 - w) * eY[t])
            v1, _, _ = blend(eF, oF, eY, oY, w, "①"); v2, _, _ = blend(eF, oF, eY, oY, w, "②")
            nd.setdefault("① 合併迴圈 vs 向量（相對差 > 1e−12 的日數）", 0)
            nd["① 合併迴圈 vs 向量（相對差 > 1e−12 的日數）"] += int((np.abs(np.array(e1) / v1 - 1) > 1e-12).sum())
            nd.setdefault("① 不再平衡迴圈 vs 向量（不同日數）", 0)
            nd["① 不再平衡迴圈 vs 向量（不同日數）"] += int((np.array(e2) != v2).sum())
            # ⑤ 各年與 0050 標籤
            yr = year_rets(v2, w0, yends); prev = w0
            for k, b in enumerate(yends):
                nd.setdefault("⑤ 各年報酬（不同）", 0)
                nd["⑤ 各年報酬（不同）"] += int(abs(yr[k] - (v2[b] / v2[prev] - 1)) > 1e-15); prev = b
            sm = seg_metrics(v2, min(oF["first"], oY["first"]), end, SEGP)
            for sg, (c_, m_) in sm.items():
                b = B50[sg]; lab = "—"
                if np.isfinite(c_):
                    lab = "不合格"
                    if c_ > b["cagr"]:
                        lab = "另列"
                        if c_ / -m_ >= b["cagr"] / -b["mdd"]:
                            lab = "合格"
                nd.setdefault("⑤ 0050 標籤（不同）", 0); nd["⑤ 0050 標籤（不同）"] += int(lab != label(c_, m_, B50[sg]))
        # ② 端點
        nd.setdefault("② 不再平衡端點 ≠ 單一策略", 0)
        nd["② 不再平衡端點 ≠ 單一策略"] += int(not np.array_equal(blend(eF, oF, eY, oY, 1.0, "②")[0], eF)) + int(not np.array_equal(blend(eF, oF, eY, oY, 0.0, "②")[0], eY))
        # ③ 持股重建
        for nm, au, eq, oo in (("營量", auY, eY, oY), ("營飆", auF, eF, oF)):
            W, V = holdings_w(au, eq, ctx["closes"], n, SI)
            E = int(oo["end"])                                   # end 之後引擎把權益攤平，不再逐日計值 ⇒ 只驗 [0, end)
            cash = (eq - V.sum(0))[:E]
            ev = np.zeros(n, bool)
            for a in au:
                ev[a["t"]] = True
            moved = np.abs(np.diff(cash)) > 1e-9
            nd.setdefault("③ 非交易日隱含現金變動（日數）", 0)
            nd["③ 非交易日隱含現金變動（日數）"] += int((moved & ~ev[1:E]).sum())
            nd.setdefault("③ Σ權重 ＞ 1（日數）", 0)
            nd["③ Σ權重 ＞ 1（日數）"] += int((W[:, :E].sum(0) > 1 + 1e-9).sum())
            nd.setdefault("③ 隱含現金 < −1e−9（日數）", 0)
            nd["③ 隱含現金 < −1e−9（日數）"] += int((cash < -1e-9).sum())
        # ④ 持股重疊逐日字典
        WY, _ = holdings_w(auY, eY, ctx["closes"], n, SI); WF, _ = holdings_w(auF, eF, ctx["closes"], n, SI)
        vec = np.minimum(WY, WF).sum(0)

        def hold_on(au, t):
            h = {}
            buys = {}
            for a in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
                if a["t"] > t:
                    break
                if a["side"] == "buy":
                    buys.setdefault(a["sid"], []).append(a)
                else:
                    buys[a["sid"]].pop(0)
            for s, lst in buys.items():
                for a in lst:
                    h[s] = h.get(s, 0.0) + a["amt"] * float(ctx["closes"][s][t]) / a["px"]
            return h
        cnt = 0
        for t in range(w0, w1 + 1, 7):
            hy = hold_on(auY, t); hf = hold_on(auF, t)
            v = sum(min(hy.get(s, 0) / eY[t], hf.get(s, 0) / eF[t]) for s in set(hy) | set(hf))
            cnt += int(abs(v - vec[t]) > 1e-12)
        nd.setdefault("④ 持股重疊逐日重算（不同日數）", 0); nd["④ 持股重疊逐日重算（不同日數）"] += cnt
        # ⑥ 實買重疊
        by = [(a["t"], a["sid"]) for a in auY if a["side"] == "buy" and w0 <= a["t"] <= w1]
        bf = [(a["t"], a["sid"]) for a in auF if a["side"] == "buy" and w0 <= a["t"] <= w1]
        k = sum(1 for x in bf if x in by)
        nd.setdefault("⑥ 實買重疊（不同）", 0); nd["⑥ 實買重疊（不同）"] += int(k != len(buys_set(auF, w0, w1) & buys_set(auY, w0, w1)))
    out["不同"] = nd
    out["全過"] = all(v == 0 for v in nd.values())
    out["耗時秒"] = round(time.time() - T0)
    with open(os.path.join(OUT, "check.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"[check] {json.dumps(out, ensure_ascii=False)}")
    return out


# ═════════════ 網頁 ═════════════
def page(META, chk):
    from backtest import tradecheck as TC
    SU = pd.read_csv(os.path.join(OUT, "summary_blend.csv")); YS = pd.read_csv(os.path.join(OUT, "summary_years.csv"))
    e = html.escape
    P = lambda x: "—" if not np.isfinite(x) else f"{x:+.1%}"
    F = lambda x: "—" if not np.isfinite(x) else f"{x:.2f}"
    g = lambda how, wn, sg: SU[(SU["合併"] == how) & (SU["比例"] == wn) & (SU["段"] == sg)].iloc[0]
    sm = META["相似度"]; cd = META["候選重疊"]
    a, b, c = g("①", "100:0", "全部"), g("①", "0:100", "全部"), g("①", "67:33", "全部")
    c2 = g("②", "67:33", "全部")
    rat = {sg: [g("①", wn, sg)["比值中位"] for _, wn in WTS] for sg in SEGS}
    labs = {sg: sorted(set(g(h, wn, sg)["中位對0050"] for h in METH for _, wn in WTS)) for sg in SEGS}
    wm = META["最差月份"]["營量最差 3 個月"][0]
    concl = [
        f"<li><b>全部期間</b>（營飆取 200 顆中位）：營飆單獨 年化 {P(a['年化中位'])}、回落 {P(a['回落中位'])}；營量單獨 {P(b['年化中位'])}、{P(b['回落中位'])}；"
        f"你現在的 2:1 每日再平衡 {P(c['年化中位'])}、{P(c['回落中位'])}，不再平衡 {P(c2['年化中位'])}、{P(c2['回落中位'])}。"
        "⇒ 確實差不多：合併後的年化、回落大致落在兩者之間，沒有明顯「合起來比兩個都好」"
        f"（只有 2021～2023 的回落，合併後 {P(g('①', '33:67', '2021-2023')['回落中位'])}～{P(g('①', '67:33', '2021-2023')['回落中位'])} 比兩個單獨都淺一點）。</li>",
        f"<li><b>沒有哪個比例各段都最好</b>：年化÷|回落|（營飆→營量 由 100:0 到 0:100）全部期間 {' → '.join(F(x) for x in rat['全部'])}，"
        f"2021～2023 {' → '.join(F(x) for x in rat['2021-2023'])}，2024～2026.08 {' → '.join(F(x) for x in rat['2024-2026.08'])}。⛔ 只描述，不據此挑比例。</li>",
        f"<li><b>對 0050</b>：全部期間、2021～2023 每個比例都{'／'.join(labs['全部'])}；2024～2026.08 每個比例都{'／'.join(labs['2024-2026.08'])}"
        f"（0050 同段年化 {P(META['0050']['2024-2026.08']['cagr'])}）。</li>",
        f"<li><b>兩個有多像</b>：營飆的候選 {cd['候選：營飆候選也是營量候選']:.0%} 也是營量候選，營飆實際買的約 {sm['實買：營飆的買進也被營量同日買']['中位']:.0%} 營量同一天也買；"
        f"但抱的天數不同，按金額算每天持股只重疊 {sm['持股重疊（按金額，日均）']['中位']:.0%}。日報酬相關仍有 {sm['日報酬相關']['中位']:.2f}，"
        f"最慘的月份同一個（{wm['月']}：營量 {P(wm['營量'])}、營飆中位 {P(wm['營飆中位'])}）⇒ 一起跌的時候分散不了多少。</li>",
        "<li>只描述、不計 N；⛔ 沒有調任何策略參數，只是兩條正式權益曲線按資金比例合起來（每日再平衡不計成本）。</li>",
    ]
    intro = (f'<p class="mut">回測線 {e(TIME)}｜參考，不計 N｜主窗 {META["主窗"][0]}～{META["主窗"][1]}｜營飆 200 顆種子 × 營量 1 條</p>'
             f'<div class="card"><p class="big">結論</p><ul>{"".join(concl)}</ul></div>')
    sec = []
    for sg in SEGS:
        b5 = META["0050"][sg]
        rows = []
        for how in METH:
            for w, wn in WTS:
                x = g(how, wn, sg)
                rows.append([f"{METH[how]} {wn}", f"{P(x['年化中位'])}（{P(x['年化p10'])}～{P(x['年化p90'])}）", f"{P(x['回落中位'])}（{P(x['回落p10'])}～{P(x['回落p90'])}）",
                             f"{F(x['比值中位'])}", x["中位對0050"], f"{x['合格比例']:.0%}／{x['另列比例']:.0%}／{x['不合格比例']:.0%}"])
        sec.append(f"<h2>{e(sg)}（{META['SEGP'][sg][0]}～{META['SEGP'][sg][1]}）</h2>"
                   f'<p class="mut">0050 同段：年化 {P(b5["cagr"])}、回落 {P(b5["mdd"])}、比值 {F(b5["cagr"] / abs(b5["mdd"]))}</p>'
                   + TC._tbl(["營飆:營量", "年化 中位（p10～p90）", "最大回落 中位（p10～p90）", "年化÷|回落|", "中位對 0050", "合格／另列／不合格 顆數"], rows))
    yrs = sorted(YS["年"].unique())
    yrows = []
    for how in ("①",):
        for w, wn in WTS:
            q = YS[(YS["合併"] == how) & (YS["比例"] == wn)].set_index("年")
            yrows.append([f"{METH[how]} {wn}"] + [P(q.loc[y, "中位"]) for y in yrs])
    yrows.append(["0050"] + [P(META["0050各年"][str(y)]) for y in yrs])
    sec.append("<h2>各年報酬（每日再平衡，營飆 200 顆中位）</h2>" + TC._tbl(["", *[str(y) for y in yrs]], yrows)
               + '<p class="mut">2017 從 03-02 起、2026 到 08-24 止。不再平衡的各年見 summary_years.csv。</p>')
    srows = [[k, f"{v['中位']:.0%}" if "相關" not in k else f"{v['中位']:.2f}", (f"{v['p10']:.0%}～{v['p90']:.0%}" if "相關" not in k else f"{v['p10']:.2f}～{v['p90']:.2f}")]
             for k, v in sm.items()]
    srows = [[f"候選：營飆候選也是營量候選", f"{cd['候選：營飆候選也是營量候選']:.0%}", f"{cd['營飆候選筆']} 筆"],
             [f"候選：營量候選也是營飆候選", f"{cd['候選：營量候選也是營飆候選']:.0%}", f"{cd['營量候選筆']} 筆"]] + srows
    sec.append("<h2>兩個策略有多像</h2>" + TC._tbl(["項目", "中位", "p10～p90"], srows)
               + '<p class="mut">兩者的候選訊號同一個來源；營飆多了大盤濾網、抱 120 天、10 檔、隨機挑，營量抱 60 天、20 檔、依相對量挑。</p>')
    wr = []
    for x in META["最差月份"]["營量最差 3 個月"]:
        wr.append(["營量最差", x["月"], P(x["營量"]), f"{P(x['營飆中位'])}（{P(x['營飆p10'])}～{P(x['營飆p90'])}）"])
    for x in META["最差月份"]["營飆最差 3 個月（200 顆月報酬中位）"]:
        wr.append(["營飆最差", x["月"], P(x["營量"]), f"{P(x['營飆中位'])}（{P(x['營飆p10'])}～{P(x['營飆p90'])}）"])
    sec.append("<h2>各自最慘的月份，另一個怎麼樣</h2>" + TC._tbl(["", "月", "營量", "營飆 中位（p10～p90）"], wr))
    sec.append("<h2>若要做成單一融合策略</h2><p>例如「抱 90 天、15 檔」這種把兩者揉成一條規則的版本，是新的參數組：持有天數、檔數、挑選方式都要重新決定，"
               "等於一個新策略。依規矩必須先事前登錄、由裁定線給號再跑，⛔ 不在本件；本件只是把兩條既有的正式權益曲線按資金比例相加。</p>")
    gt = META["閘"]
    sec.append(f'<h2>查核</h2><p class="mut">營量、營飆 200 顆權益曲線與 resultsT1fix 逐位元相同：營量 {"是" if gt["營量 r0 ＝ resultsT1fix（eq_sha／first／end／trades／年化回落 repr）"] else "否"}、'
               f'營飆不同 {gt["營飆 ＝ resultsT1fix（不同顆數）"]} 顆；不再平衡端點逐位元不同 {gt["② 端點 ＝ 單一策略逐位元（不同顆數）"]}；每日再平衡端點最大差 {gt["① 端點年化回落最大差"]:.1e}；'
               f'--check {"全部通過" if chk and chk.get("全過") else "見 check.json"}。每日再平衡不計再平衡成本。</p>')
    with open(os.path.join(OUT, "營量營飆合併.html"), "w", encoding="utf-8") as fh:
        fh.write(TC.html_page("營量營飆合併", "".join(sec), intro).replace(TC.HOWTO_READ, "").replace(
            "做法參考 mars-tw/anti-gambling-trader-tw（MIT）的方法論，程式為回測線自寫（backtest/tradecheck.py）。", "backtest/researchYL_blend.py"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--page", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "a", encoding="utf-8")

    def log(m):
        s = f"[{time.strftime('%H:%M:%S')}] {m}"; print(s, flush=True); lf.write(s + "\n"); lf.flush()
    if a.check:
        check(log); return
    if a.page:
        META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    else:
        META = run(log)
    chk = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    page(META, chk)
    log("[網頁] 完成")


if __name__ == "__main__":
    main()

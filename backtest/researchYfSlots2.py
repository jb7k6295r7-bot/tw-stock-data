# -*- coding: utf-8 -*-
"""營飆 v1／營量 v1 各半：兩邊槽數的差異（裁定 seq209；回測線計算助手 2026-09-26）。

⭐ 描述、⛔ 不判、⛔ 不計 N、⛔ 不改現行各半 10＋20。⛔ 不改任何既有 .py。
必附（逐字）：「檔數是看完結果才比的，只供選；兩套本身也還沒在沒看過的年份驗過」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfSlots2 run [--procs 2]
    ... -m backtest.researchYfSlots2 report

═══ 組態（其餘一字不動；只換槽數 N）═══
  營飆 v1 ＝ #1 PREREG10 AND regime=True（t−1 閘）H120，N ∈ {5, 8, 10}｜種子 1000＋r｜引擎呼叫 ＝ researchYear1M.run_engine 的 P10 分支原式
  營量 v1 ＝ #13 P1 AND d=inf relvol H60，N ∈ {5, 10, 15, 20}｜種子 7000＋r｜＝ run_engine 的 P1 分支原式（log=[]、queue_days 0）
  訊號 ＝ researchYear1M.sig_of(…, "eng", w0, w1)（＝ rerun17 主窗讀法）；主窗 2017-03-02～2026-08-24；快照 edc6f8002f
  各半 ＝ researchp17.compose(E營飆, E營量, w＝0.5, 每年第一個交易日調回（窗首不算）, 換手 × 0.585%)（＝ researchYfMix13 AB50）
═══ 讀法（⭐ 看結果前寫定）═══
  S1 單套列直接由序列算（rerun17.win_metrics）⇒ 閘：營飆 10 ＝ regime_t1 t1 #1、營量 20 ＝ rerun17_seeds main #13（逐種子逐位元）
  S2 各半 10×20 ⇒ 閘：逐種子 年化／回落／期末 ＝ resultsYfMix13/mix_seeds.csv.gz AB50 主窗（逐位元）
  S3 持有：由 audit 重建，部位在第 t 天持有 ⇔ 買進日 ≤ t ＜ 賣出日（同 researchYfMix13 K1）；只算 t ∈ [w0, w1]
     實際持有檔數 ＝ 兩套持股的聯集大小（同一檔在兩邊只算一次）；報「逐日平均」與「逐日最大」，每顆種子各算、報 200 顆中位（及 p10～p90）
  S4 單檔占總資金 ＝ Σ_腿（該腿在組合的占比 v_腿[t]÷V[t]）×（該股在腿內的市值 ÷ 腿權益[t]）；同一檔兩邊都有 ⇒ 相加
     腿內市值 ＝ 引擎同式 amt × 收盤[t] ÷ 進場價；腿占比由本檔 legs2（compose 同一順序，逐位元斷言 V 相同）取；
     報每顆種子窗內的最大值、200 顆中位與 p90
  S5 抽籤範圍 ＝ 200 顆年化（與期末金額、回落）的 p10～p90；營量 relvol 排序不抽籤 ⇒ 範圍只來自營飆（本檔驗營量 200 顆逐位元相同）
  S6 標籤 ＝ rerun17_table.label（年化中位、回落中位 對 0050 錨）；比值 ＝ 年化中位 ÷ |回落中位|；100 萬期末 ＝ 1e6 × V[w1]÷V[w0]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import researchYear1M as Y
from . import rerun17 as RR
from . import rerun17_table as RT
from . import research11 as R
from . import research13 as R13

HERE = Y.HERE
OUT = os.path.join(HERE, "resultsYfSlots2")
REPS = 200
CAP = 1_000_000
COST = 0.00585
NA = (5, 8, 10)
NB = (5, 10, 15, 20)
WORD = "檔數是看完結果才比的，只供選；兩套本身也還沒在沒看過的年份驗過"
RTP = dict(float_precision="round_trip")
_G: dict = {}


def sha16(a):
    return hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()[:16]


def sim(arm, N, r, audit):
    """⭐ 引擎呼叫：researchYear1M.run_engine 的 P10／P1 分支原式，只把 N 換掉。"""
    G = Y._G
    if arm == "A":
        return R.simulate_mtm(_G["sigA"], "H120", N, np.random.default_rng(1000 + r), G["closes"], G["opens"], G["NP"],
                              return_equity=True, audit=audit)
    return R.simulate_mtm(_G["sigB"], "H60", N, np.random.default_rng(7000 + r), G["closes"], G["opens"], G["NP"], log=[],
                          d_max=None, pick="relvol", queue_days=0, return_equity=True, audit=audit)


def leg_detail(s, au):
    """S3／S4：回 (窗內權益, 持有布林 [日×股], 腿內占比 [日×股])。"""
    w0, w1 = _G["w0"], _G["w1"]; n = w1 - w0 + 1; col = _G["col"]; cl = Y._G["closes"]
    eq = np.asarray(s["equity"], float)
    H = np.zeros((n, len(col)), bool); Wt = np.zeros((n, len(col)))
    open_ = {}
    pos = []
    for x in au:
        if x["side"] == "buy":
            open_[x["sid"]] = (x["t"], x["amt"], x["px"])
        else:
            tb, amt, ep = open_.pop(x["sid"]); pos.append((x["sid"], tb, x["t"], amt, ep))
    pos += [(sid, tb, 10 ** 9, amt, ep) for sid, (tb, amt, ep) in open_.items()]
    for sid, tb, ts, amt, ep in pos:
        a, b = max(tb, w0), min(ts, w1 + 1)
        if a >= b:
            continue
        j = col[sid]
        H[a - w0:b - w0, j] = True
        Wt[a - w0:b - w0, j] += amt * cl[sid][a:b].astype(float) / ep / eq[a:b]
    return eq[w0:w1 + 1], H, Wt


def legs2(E, B, w, rebal):
    """researchp17.compose 的同一順序（兩腿），另回每日（調回後）兩腿值。"""
    n = len(E); re_ = np.r_[1.0, E[1:] / E[:-1]]; rb_ = np.r_[1.0, B[1:] / B[:-1]]
    V = np.empty(n); VE = np.empty(n); VB = np.empty(n)
    ve, vb = w, 1.0 - w; V[0] = 1.0; VE[0] = ve; VB[0] = vb
    for t in range(1, n):
        ve *= re_[t]; vb *= rb_[t]; v = ve + vb
        if rebal[t]:
            tgt = w * v; c = abs(tgt - ve) * COST; v -= c; ve, vb = w * v, (1.0 - w) * v
        V[t] = v; VE[t] = ve; VB[t] = vb
    return V, VE, VB


def metrics_single(s, eq_full, H, Wt):
    w0, w1 = _G["w0"], _G["w1"]
    c, m, v = RR.win_metrics(eq_full, s["first"], s["end"], w0, w1)
    cnt = H.sum(1)
    return {"cagr": float(c), "mdd": float(m), "vol": float(v), "end_value": CAP * eq_full[w1] / eq_full[w0],
            "first": int(s["first"]), "end": int(min(s["end"], Y._G["ncal"])), "trades": int(s["trades"]),
            "eq_sha": sha16(eq_full[:Y._G["ncal"]]), "held_mean": float(cnt.mean()), "held_max": int(cnt.max()),
            "maxw": float(Wt.max())}


def _single(args):
    arm, N, r = args
    au = []
    s = sim(arm, N, r, au)
    eq_full = np.asarray(s["equity"], float)
    _, H, Wt = leg_detail(s, au)
    return {"arm": arm, "N": N, "r": r, "seed": (1000 if arm == "A" else 7000) + r, **metrics_single(s, eq_full, H, Wt)}


def _combo(args):
    from . import researchp17 as P17
    nA, r = args
    au = []
    s = sim("A", nA, r, au)
    EA, HA, WA = leg_detail(s, au)
    out = []
    n = len(EA)
    for nB in NB:
        EB, HB, WB = _G["B"][nB]
        V, _, cst = P17.compose(EA, EB, np.full(n, 0.5), _G["rebal"], cost=COST)
        V2, VE, VB = legs2(EA, EB, 0.5, _G["rebal"])
        if not np.array_equal(V, V2):
            raise SystemExit("⛔ legs2 與 compose 不逐位元相同")
        c, m = R13.window_stats(V, 0, n, 0, n)
        share = (VE / V)[:, None] * WA + (VB / V)[:, None] * WB
        U = (HA | HB).sum(1)
        out.append({"nA": nA, "nB": nB, "r": r, "cagr": float(c), "mdd": float(m), "end_value": CAP * V[-1] / V[0],
                    "cost_sum": float(cst.sum()), "held_mean": float(U.mean()), "held_max": int(U.max()),
                    "overlap_mean": float((HA & HB).sum(1).mean()), "maxw": float(share.max()),
                    "maxw_date": str(Y._G["cal"][_G["w0"] + int(share.max(1).argmax())].date())})
    return out


def setup(log):
    Y.setup(log)
    cal = Y._G["cal"]; w0, w1 = RR.win_bounds(cal)
    sigA = Y.sig_of(1, "eng", w0, w1); sigB = Y.sig_of(13, "eng", w0, w1)
    sids = sorted(set(sigA["sid"]) | set(sigB["sid"]))
    _G.update(w0=w0, w1=w1, sigA=sigA, sigB=sigB, col={s: i for i, s in enumerate(sids)},
              rebal=np.r_[False, pd.DatetimeIndex(cal[w0 + 1:w1 + 1]).year != pd.DatetimeIndex(cal[w0:w1]).year])
    log(f"[設定] 營飆訊號 {len(sigA)}、營量訊號 {len(sigB)}、股 {len(sids)}；再平衡日 {int(_G['rebal'].sum())}")


def run(procs, log):
    t0 = time.time()
    setup(log)
    # ── 單套（S1、S5）
    jobs = [("A", N, r) for N in NA for r in range(REPS)] + [("B", N, r) for N in NB for r in range(REPS)]
    with Pool(procs) as pool:
        S = pd.DataFrame(pool.map(_single, jobs, chunksize=4))
    S = S.sort_values(["arm", "N", "r"]).reset_index(drop=True)
    S.to_csv(os.path.join(OUT, "single_seeds.csv"), index=False)
    log(f"[單套] {len(S)} 列｜{time.time() - t0:.0f}s")
    gate = {}
    same = {int(N): bool(S[(S["arm"] == "B") & (S["N"] == N)]["eq_sha"].nunique() == 1) for N in NB}
    gate["營量各槽數 200 顆 equity 完全相同"] = {"明細": same, "逐位元": all(same.values())}
    for arm, N, ref, nm in (("A", 10, ("regime_t1/seeds.csv", "t1", 1), "營飆 10 對 regime_t1 t1 #1"),
                            ("B", 20, ("rerun17_seeds.csv", "main", 13), "營量 20 對 rerun17_seeds main #13")):
        rf = pd.read_csv(os.path.join(RR.OUT, ref[0]), dtype={"eq_sha": str}, **RTP)
        rf = rf[(rf["stage"] == ref[1]) & (rf["cell"] == ref[2])].set_index("r").sort_index()
        g = S[(S["arm"] == arm) & (S["N"] == N)].set_index("r").sort_index()
        bad = {k: int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(g[k], rf[k]))) for k in ("cagr", "mdd", "vol")}
        bad.update({k: int((g[k].astype(int) != rf[k].astype(int)).sum()) for k in ("first", "end", "trades")})
        bad["eq_sha"] = int((g["eq_sha"] != rf["eq_sha"].astype(str)).sum())
        gate[nm] = {"不同數": bad, "逐位元": len(g) == REPS and all(v == 0 for v in bad.values())}
    log(f"[閘 單套] {json.dumps(gate, ensure_ascii=False)}")
    # ── 營量四條路徑（r＝0；已驗 200 顆相同）
    B = {}
    for N in NB:
        au = []
        s = sim("B", N, 0, au)
        B[N] = leg_detail(s, au)
    _G["B"] = B
    with Pool(procs) as pool:
        rows = [x for y in pool.map(_combo, [(nA, r) for nA in NA for r in range(REPS)], chunksize=4) for x in y]
    C = pd.DataFrame(rows).sort_values(["nA", "nB", "r"]).reset_index(drop=True)
    C.to_csv(os.path.join(OUT, "combo_seeds.csv"), index=False)
    ref = pd.read_csv(os.path.join(HERE, "resultsYfMix13", "mix_seeds.csv.gz"), **RTP)
    ref = ref[(ref["scope"] == "主窗") & (ref["mix"] == "AB50")].set_index("r").sort_index()
    g = C[(C["nA"] == 10) & (C["nB"] == 20)].set_index("r").sort_index()
    bad = {k: int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(g[k], ref[k]))) for k in ("cagr", "mdd", "end_value", "cost_sum")}
    gate["各半 10×20 對 resultsYfMix13 AB50 主窗"] = {"不同數": bad, "逐位元": len(g) == REPS and all(v == 0 for v in bad.values())}
    gate["全部過"] = all(v["逐位元"] for v in gate.values() if isinstance(v, dict))
    json.dump(gate, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[閘] {json.dumps(gate, ensure_ascii=False)}｜{time.time() - t0:.0f}s")
    if not gate["全部過"]:
        raise SystemExit("⛔ 閘不過")


def q(s, p):
    return float(pd.Series(s).quantile(p))


def report(log):
    S = pd.read_csv(os.path.join(OUT, "single_seeds.csv"), **RTP)
    C = pd.read_csv(os.path.join(OUT, "combo_seeds.csv"), **RTP)
    gate = json.load(open(os.path.join(OUT, "gate.json"), encoding="utf-8"))
    bc, bm = RR.ANCHOR

    def summ(g):
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio, extra = RT.label(c, m, bc, bm)
        return {"年化中位": c, "年化p10": q(g["cagr"], .1), "年化p90": q(g["cagr"], .9), "回落中位": m, "回落p10": q(g["mdd"], .1),
                "回落p90": q(g["mdd"], .9), "比值": ratio, "對0050標籤": lab, "深淺註": extra,
                "期末金額100萬中位": float(g["end_value"].median()), "期末金額100萬p10": q(g["end_value"], .1), "期末金額100萬p90": q(g["end_value"], .9),
                "平均實際持有檔數_中位": float(g["held_mean"].median()), "平均實際持有檔數_p10": q(g["held_mean"], .1),
                "平均實際持有檔數_p90": q(g["held_mean"], .9), "最大同時持有_中位": float(g["held_max"].median()),
                "最大同時持有_最大": int(g["held_max"].max()), "單檔最大占比_中位": float(g["maxw"].median()), "單檔最大占比_p90": q(g["maxw"], .9),
                "種子數": len(g)}
    rows = []
    for arm, NS, nm in (("A", NA, "營飆 v1"), ("B", NB, "營量 v1")):
        for N in NS:
            g = S[(S["arm"] == arm) & (S["N"] == N)]
            rows.append({"列": f"單套 {nm} N{N}", "營飆N": N if arm == "A" else 0, "營量N": N if arm == "B" else 0,
                         "註": ("現行（閘）" if (arm, N) in (("A", 10), ("B", 20)) else ""), **summ(g)})
    ns = pd.read_csv(os.path.join(RR.OUT, "nslots", "cells.csv"), encoding="utf-8-sig", **RTP)
    q20 = ns[ns["檔數N"] == 20].iloc[0]
    rows.append({"列": "單套 營飆 v1 N20（參照：resultsN17/nslots/cells.csv，未重跑）", "營飆N": 20, "營量N": 0, "註": "引用",
                 "年化中位": q20["年化中位"], "年化p10": q20["年化p10"], "年化p90": q20["年化p90"], "回落中位": q20["回落中位"],
                 "回落p10": q20["回落p10"], "回落p90": q20["回落p90"], "比值": q20["比值"], "對0050標籤": q20["標籤（對0050）"],
                 "深淺註": q20["深淺註"], "期末金額100萬中位": q20["100萬放滿主窗中位（萬；eq[w1]÷eq[w0]）"] * 1e4})
    for nA in NA:
        for nB in NB:
            g = C[(C["nA"] == nA) & (C["nB"] == nB)]
            rows.append({"列": f"各半 營飆 {nA} ＋ 營量 {nB}", "營飆N": nA, "營量N": nB, "註": "現行（閘）" if (nA, nB) == (10, 20) else "",
                         **summ(g), "兩邊同時持有同檔_逐日平均_中位": float(g["overlap_mean"].median()),
                         "再平衡成本合計_中位": float(g["cost_sum"].median())})
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    p = lambda x: f"{x * 100:+.2f}%"
    L = [f"# 營飆 v1／營量 v1 各半：槽數差異（裁定 seq209；描述、⛔ 不判、⛔ 不計 N、⛔ 不改現行 10＋20）", "", f"> ⚠ {WORD}", "",
         "主窗 2017-03-02～2026-08-24、快照 edc6f8002f；各半 ＝ researchp17.compose w＝0.5、每年第一個交易日調回、換手 × 0.585%（＝ resultsYfMix13 AB50）。"
         "營飆 t−1 閘 H120 種子 1000＋r；營量 relvol d=inf H60 種子 7000＋r（不抽籤，四種槽數各 200 顆逐位元相同，已驗）。"
         "讀法 S1～S6 見 `backtest/researchYfSlots2.py` 檔頭；查核 `backtest/researchYfSlots2_check.py`。數字全部引自 `cells.csv`。", "",
         "## 閘", "", "| 項 | 結果 |", "|---|---|"]
    L += [f"| {k} | {'✅ 逐位元' if v['逐位元'] else '⛔'} {json.dumps(v.get('不同數', v.get('明細', '')), ensure_ascii=False)} |" for k, v in gate.items() if isinstance(v, dict)]
    L += ["", "## 表（年化、回落為 200 顆中位；抽籤範圍 ＝ 200 顆 p10～p90）", "",
          "| 列 | 年化中位（p10～p90） | 回落中位（p10～p90） | 比值 | 對 0050 | 100 萬放滿主窗（萬，p10～p90） | 平均實際持有檔數 | 最大同時持有 | 單檔最大占比（中位／p90） |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r_ in T.itertuples():
        held = f"{r_.平均實際持有檔數_中位:.2f}" if pd.notna(r_.平均實際持有檔數_中位) else "—"
        mx = f"{r_.最大同時持有_中位:.0f}" if pd.notna(r_.最大同時持有_中位) else "—"
        mw = f"{r_.單檔最大占比_中位 * 100:.1f}%／{r_.單檔最大占比_p90 * 100:.1f}%" if pd.notna(r_.單檔最大占比_中位) else "—"
        ev = (f"{r_.期末金額100萬中位 / 1e4:,.1f}（{r_.期末金額100萬p10 / 1e4:,.1f}～{r_.期末金額100萬p90 / 1e4:,.1f}）" if pd.notna(r_.期末金額100萬p10)
              else f"{r_.期末金額100萬中位 / 1e4:,.1f}")
        lab = r_.對0050標籤 + (f"（{r_.深淺註}）" if isinstance(r_.深淺註, str) and r_.深淺註 else "")
        L.append(f"| {r_.列}{'【' + r_.註 + '】' if isinstance(r_.註, str) and r_.註 else ''} | {p(r_.年化中位)}（{p(r_.年化p10)}～{p(r_.年化p90)}） | "
                 f"{p(r_.回落中位)}（{p(r_.回落p10)}～{p(r_.回落p90)}） | {r_.比值:.3f} | {lab} | {ev} | {held} | {mx} | {mw} |")
    L += ["", "- 實際持有檔數 ＝ 兩套持股聯集（同一檔兩邊都有只算一次）的逐日平均；最大同時持有 ＝ 逐日最大（每顆種子各取、報 200 顆中位）。",
          "- 單檔最大占比 ＝ 該檔市值（兩邊相加）÷ 組合總值，窗內逐日最大；每顆種子各取，報 200 顆中位與 p90。",
          "- 營量不抽籤 ⇒ 單套營量與各半的抽籤範圍全來自營飆那一半。", "", f"> ⚠ {WORD}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
    log(f"[report] cells.csv {len(T)} 列｜REPORT.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "report"])
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")
    T0 = time.time()

    def log(x):
        x = f"[{time.time() - T0:6.0f}s] {x}"
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== researchYfSlots2 {a.stage} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    run(a.procs, log) if a.stage == "run" else report(log)


if __name__ == "__main__":
    main()

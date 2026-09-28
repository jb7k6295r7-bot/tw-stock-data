# -*- coding: utf-8 -*-
"""PREREG營量趨勢 描述臂：T2 拆開（使用者直接指示「T2改單純大於MA20或MA60！」；協調者轉達，2026-09-28）——回測線。
⭐ 使用者直接指示的描述臂；不計 N、不改登錄判定、不挑格。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLtrend_ma [--procs 2] [--seeds 200] [--report]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchYLtrend_ma_check.py

⭐ 只 import researchYLtrend（9e1948f914），⛔ 不改它：build_world、cells_of、run_cell、cr0_mean、label 原樣；營量 v1 T1 版、stop_force 開、資料尾 t1_censor（同原件）
新定義（t−1 ＝ 訊號根 k 收盤；還原價、有效 K 棒；MA ＝ research11._roll_mean，同原件 T2 的算法）：
  T2a 收盤 ＞ MA20｜T2b 收盤 ＞ MA60（NaN ⇒ 不成立）
格：甲族（營量 v1 AND 列 ∧ Tk）、乙族（候選根 ∧ Tk、20 根去重，同原件 Y4）× {T2a, T2b} × H {40, 60, 80} ＝ 12 格；並列原 T2（收盤 ＞ MA20 ＞ MA60）同格
每格報：探索、確認、早年 年化／回落／比值／標籤（對 0050 同段）、通過率（甲）／訊號數（乙）、對營量 v1 同段配對差（原件 Y8 同式、95% CI）、退化旗標（原件 Y7 同式）
閘：原 T2 的 6 格（甲、乙 × H）與營量 v1 200 顆 ＝ resultsYLtrend/seeds_main.csv.gz、seeds_early.csv.gz（年化、回落 repr；主窗另比 eq_sha）
輸出 backtest/resultsYLtrend/ma/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchYLtrend as YT                  # ⭐ 原件，只 import
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import universe_gate as UG

OUT = "backtest/resultsYLtrend/ma"
REF = "backtest/resultsYLtrend"
NEW = ("T2a", "T2b")
TKS = ("T2", "T2a", "T2b")
_G2: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def ma_flags(args):
    sid, mk, ks = args
    B = R11.load_bars(sid, mk, _G2["cal"])
    c = B["c"]
    ma20, ma60 = R11._roll_mean(c, 20), R11._roll_mean(c, 60)
    ks = np.asarray(ks, int)
    with np.errstate(invalid="ignore"):
        return sid, ks, (c[ks] > ma20[ks]), (c[ks] > ma60[ks])


def add_new(Wd, cal, mkmap, w0, w1, procs):
    """ALL 加 T2a、T2b ⇒ 甲（AND 窗內列）加旗標；乙（候選 ∧ Tk ⇒ 20 根去重，原件 Y4 同式）。"""
    ALL = Wd["ALL"]
    _G2["cal"] = cal
    jobs = [(s, mkmap.get(s, "twse"), g["k"].to_numpy(int)) for s, g in ALL.groupby("sid")]
    with Pool(procs) as pool:
        R_ = pool.map(ma_flags, jobs, chunksize=8)
    fl = pd.concat([pd.DataFrame({"sid": s, "k": ks, "T2a": a, "T2b": b}) for s, ks, a, b in R_], ignore_index=True)
    ALL = ALL.merge(fl, on=["sid", "k"], how="left", validate="one_to_one")
    A = Wd["AND"].merge(fl, on=["sid", "k"], how="left", validate="one_to_one")
    A.index = Wd["AND"].index
    SIGB = dict(Wd["SIGB"])
    P = ALL[ALL["候選"]].sort_values(["sid", "k"])
    for tk in NEW:
        q = P[P[tk].astype(bool)]
        keep = np.zeros(len(q), bool)
        last_s, last_k = None, -10 ** 9
        for j, (s, k) in enumerate(zip(q["sid"].to_numpy(), q["k"].to_numpy())):
            if s != last_s:
                last_s, last_k = s, -10 ** 9
            if k - last_k > 20:
                keep[j] = True; last_k = k
        qq = q[keep]; ee = qq["entry_pos"].to_numpy()
        z = qq[(ee >= w0) & (ee <= w1)].copy(); z["relvol"] = z["relvol"].fillna(0.0)
        SIGB[tk] = z
    return A, SIGB


def cells(A, SIGB):
    SIG = {"營量v1": (A, 60)}
    for tk in TKS:
        for H in YT.HS:
            SIG[f"甲_{tk}_H{H}"] = (A[A[tk].to_numpy(bool)], H)
            SIG[f"乙_{tk}_H{H}"] = (SIGB[tk], H)
    return SIG


def run_world(wn, keys, seeds, procs):
    W = YT._W[wn]
    W["KEEP_EQ"] = "營量v1"
    with Pool(procs) as pool:
        res = pool.map(YT.run_cell, [(wn, "營量v1", r) for r in range(seeds)], chunksize=4)
    rows = [x[0] for x in res]; W["V1EQ"] = {r: x[2] for r, x in zip(range(seeds), res)}; W["KEEP_EQ"] = None
    DIFF = {k: {} for k in keys}
    with Pool(procs) as pool:
        for row, diffs, _ in pool.imap_unordered(YT.run_cell, [(wn, k, r) for k in keys for r in range(seeds)], chunksize=4):
            rows.append(row)
            for sg, d in diffs.items():
                DIFF[row["格"]][sg] = d if sg not in DIFF[row["格"]] else DIFF[row["格"]][sg] + d
    return pd.DataFrame(rows), DIFF


def gate(SEED, ref, segs, sha_on):
    bad = {}
    for k, g in SEED.groupby("格"):
        if not (k == "營量v1" or "_T2_" in k):
            continue
        a_ = g.sort_values("r").reset_index(drop=True); b_ = ref[ref["格"] == k].sort_values("r").reset_index(drop=True)
        n = 0
        for i in range(min(len(a_), len(b_))):
            for sg in segs:
                for c_ in (f"{sg}_年化", f"{sg}_回落"):
                    n += repr(float(a_.loc[i, c_])) != repr(float(b_.loc[i, c_]))
            if sha_on:
                n += a_.loc[i, "eq_sha"] != b_.loc[i, "eq_sha"]
        bad[k] = [int(n), int(min(len(a_), len(b_)))]
    return bad


def main():
    global LOGF
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report(); return
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    T0 = time.time()
    log(f"===== researchYLtrend_ma {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜seeds {a.seeds}｜使用者直接指示的描述臂；不計 N、不改登錄判定 =====")
    S = {"件": "PREREG營量趨勢 描述臂：T2 拆成 T2a（收盤＞MA20）、T2b（收盤＞MA60）", "性質": "使用者直接指示的描述臂；不計 N、不改登錄判定"}
    # ── 主 ──
    RR.use_snapshot()
    cal = D.load_calendar(); w0, w1 = RR.win_bounds(cal)
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log, t1=True)
    G = RR._G; AND = G["AND"].copy()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks); uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    mk = uni.set_index("stock_id")["market"]
    mp = pd.read_csv(YT.MPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    tf = lambda s: s.astype(str).isin(["True", "1", "1.0"])
    elig_m = {int(md.year * 12 + md.month - 1): set(g.loc[tf(g["eligible"]).to_numpy(), "stock_id"]) for md, g in mp.groupby("measure_date")}
    rev = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    Wm = YT.build_world("主", cal, w0, w1, list(zip(uni["stock_id"], uni["market"])), AND, rev, elig_m, {}, a.procs, log)
    Am, SBm = add_new(Wm, cal, mk, w0, w1, a.procs)
    closes, opens = dict(G["closes"]), dict(G["opens"])
    extra = sorted((set(Wm["POOL"]["sid"]) | set().union(*[set(v["sid"]) for v in SBm.values()])) - set(closes))
    if extra:
        c2, o2 = RR.load_prices(extra, cal, mk, "branch"); c2, o2 = RR.pad_px_t1(c2, o2); closes.update(c2); opens.update(o2)
    SF = R11.stop_force_days(R11.valid_from_data(sorted(closes), mk, cal), w1)
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in YT.SEG_C.items()}
    bench = RR.load_bench(cal)
    B50 = {sg: RR.bench_row(cal, bench, x, y + 1) for sg, (x, y) in SEGP.items()}
    SIGm = cells(Am, SBm)
    YT._W["主"] = {"SIG": SIGm, "closes": closes, "opens": opens, "ncal": G["ncal"], "SF": SF, "SEGP": SEGP, "SEGP0": SEGP, "w0": w0, "w1": w1, "cal": cal}
    keys = [k for k in SIGm if k != "營量v1"]
    t0 = time.time()
    SEEDm, DIFFm = run_world("主", keys, a.seeds, a.procs)
    log(f"[主] {len(keys) + 1} 格 × {a.seeds}｜{time.time() - t0:.0f}s")
    S["通過率（甲，主）"] = {tk: float(Am[tk].astype(bool).mean()) for tk in TKS}
    S["訊號數（乙，主）"] = {tk: int(len(SBm[tk])) for tk in TKS}
    # ── 早年 ──
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import early_data as E
    from backtest import p4_features as P4F
    V.body_setup("main", log)
    ecal = V._B["cal"]; ew0, ew1 = V._B["w0"], V._B["w1"]; euni = Y._G["uni"]
    EAND = Y.sig_of(13, "mtm", 0, len(ecal) + 5).copy()
    sdir = V.body_paths("main")[1]
    erev = pd.read_csv(os.path.join(sdir, "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    ep = P4F.read_panel(os.path.join(sdir, "panel.csv.gz"))
    eelig = {int(md.year * 12 + md.month - 1): set(g.loc[g["eligible"].astype(bool).to_numpy(), "stock_id"])
             for md, g in ep.groupby("measure_date") if md >= pd.Timestamp("2012-06-01")}
    EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(ecal)}
    EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    We = YT.build_world("早年", ecal, ew0, ew1, [(s, euni.get(s, "twse")) for s in sorted(euni.index)], EAND, erev, eelig, EVD, a.procs, log)
    Ae, SBe = add_new(We, ecal, euni, ew0, ew1, a.procs)
    ecl, eop = dict(Y._G["closes"]), dict(Y._G["opens"])
    extra = sorted((set(We["POOL"]["sid"]) | set().union(*[set(v["sid"]) for v in SBe.values()])) - set(ecl))
    if extra:
        c2, o2 = RR.load_prices(extra, ecal, euni, "branch"); c2, o2 = Y.pad_px(c2, o2); ecl.update(c2); eop.update(o2)
    eSF = R11.stop_force_days(R11.valid_from_data(sorted(ecl), euni, ecal), ew1)
    ESEGP = {"早年": (ew0, ew1)}
    B50["早年"] = RR.bench_row(ecal, RR.load_bench(ecal), ew0, ew1 + 1)
    SIGe = cells(Ae, SBe)
    YT._W["早年"] = {"SIG": SIGe, "closes": ecl, "opens": eop, "ncal": Y._G["NP"], "SF": eSF, "SEGP": ESEGP, "SEGP0": ESEGP, "w0": ew0, "w1": ew1, "cal": ecal}
    SEEDe, DIFFe = run_world("早年", keys, a.seeds, a.procs)
    log(f"[早年] {time.time() - T0:.0f}s")
    S["通過率（甲，早年）"] = {tk: float(Ae[tk].astype(bool).mean()) for tk in TKS}
    S["訊號數（乙，早年）"] = {tk: int(len(SBe[tk])) for tk in TKS}
    # ── 閘 ──
    rm = pd.read_csv(os.path.join(REF, "seeds_main.csv.gz"), float_precision="round_trip")
    re_ = pd.read_csv(os.path.join(REF, "seeds_early.csv.gz"), float_precision="round_trip")
    S["閘（原 T2 與營量 v1 ＝ resultsYLtrend；[不同數, 顆數]）"] = {"主": gate(SEEDm, rm, ("探索", "確認"), True), "早年": gate(SEEDe, re_, ("早年",), False)}
    log(f"[閘] {S['閘（原 T2 與營量 v1 ＝ resultsYLtrend；[不同數, 顆數]）']}")
    # ── 彙總 ──
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in SEGP.items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[ew0 + 1:ew1 + 1]])
    PT = []
    for k in ["營量v1"] + keys:
        g = SEEDm[SEEDm["格"] == k]; ge = SEEDe[SEEDe["格"] == k]
        row = {"格": k, "族": k.split("_")[0] if k != "營量v1" else "—", "Tk": k.split("_")[1] if k != "營量v1" else "—",
               "H": int(k.split("_H")[1]) if k != "營量v1" else 60, "訊號數_主": int(len(SIGm[k][0])), "訊號數_早年": int(len(SIGe[k][0]))}
        for sg, gg in (("探索", g), ("確認", g), ("早年", ge)):
            c, m = float(gg[f"{sg}_年化"].median()), float(gg[f"{sg}_回落"].median())
            row.update({f"{sg}_年化": c, f"{sg}_回落": m, f"{sg}_比值": c / abs(m), f"{sg}_標籤": YT.label(c, m, (B50[sg]["cagr"], B50[sg]["mdd"])),
                        f"{sg}_持股": float(gg[f"{sg}_持股"].median()), f"{sg}_現金": float(gg[f"{sg}_現金"].median())})
            if k != "營量v1":
                dd = (DIFFm if sg != "早年" else DIFFe)[k][sg] / a.seeds
                mm_, se_ = YT.cr0_mean(dd, months[sg])
                row.update({f"{sg}_配對差年化": mm_ * 245, f"{sg}_配對差lo": (mm_ - 1.96 * se_) * 245, f"{sg}_配對差hi": (mm_ + 1.96 * se_) * 245})
        PT.append(row)
    PT = pd.DataFrame(PT)
    PT["退化"] = (PT["格"] != "營量v1") & ((PT["探索_持股"] < 10) | (PT["探索_現金"] > 0.30))
    PT["通過率_主"] = [S["通過率（甲，主）"].get(t) if f == "甲" else None for f, t in zip(PT["族"], PT["Tk"])]
    PT["通過率_早年"] = [S["通過率（甲，早年）"].get(t) if f == "甲" else None for f, t in zip(PT["族"], PT["Tk"])]
    np.savez_compressed(os.path.join(OUT, "pairdiff.npz"), **{f"{k}|{sg}": (DIFFm if sg != "早年" else DIFFe)[k][sg] / a.seeds for k in keys for sg in ("探索", "確認", "早年")})
    PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    SEEDm.to_csv(os.path.join(OUT, "seeds_main.csv.gz"), index=False, float_format="%.17g")
    SEEDe.to_csv(os.path.join(OUT, "seeds_early.csv.gz"), index=False, float_format="%.17g")
    cols = ["sid", "k", "pos", "entry_pos", "relvol", "T2", "T2a", "T2b"] + [f"xpos_H{H}" for H in YT.HS] + [f"g_H{H}" for H in YT.HS]
    for wn, A_, SB_ in (("main", Am, SBm), ("early", Ae, SBe)):
        A_[cols].to_csv(os.path.join(OUT, f"sig_and_{wn}.csv.gz"), index=False, float_format="%.17g")
        pd.concat([SB_[tk][[c for c in cols if c in SB_[tk].columns]].assign(Tk=tk) for tk in NEW]).to_csv(os.path.join(OUT, f"sig_b_{wn}.csv.gz"), index=False, float_format="%.17g")
    S["0050"] = B50; S["秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    bad = any(v[0] for w in S["閘（原 T2 與營量 v1 ＝ resultsYLtrend；[不同數, 顆數]）"].values() for v in w.values())
    report()
    log(f"[完] {S['秒']}s｜閘 {'不過' if bad else '過'}")
    if bad:
        raise SystemExit("⛔ 閘不過")


def _p(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.2f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    PT = pd.read_csv(os.path.join(OUT, "cells.csv")).set_index("格")
    L = ["# PREREG營量趨勢 描述臂：T2 拆成「收盤 ＞ MA20」「收盤 ＞ MA60」", "",
         "**使用者直接指示的描述臂；不計 N、不改登錄判定**", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。使用者逐字：「T2改單純大於MA20或MA60！」（看甲族表之後）；協調者轉達。回測線。"
         "⭐ 停止交易強制出場：開；T1：開。⛔ 不挑格、不判件標籤；PREREG營量趨勢的登錄判定（件標籤不合格、對營量 v1 不穩）不變。", ""]
    v1 = PT.loc["營量v1"]
    best = []
    for fam in ("甲", "乙"):
        for H in (40, 60, 80):
            r2, ra, rb = (PT.loc[f"{fam}_{t}_H{H}"] for t in ("T2", "T2a", "T2b"))
            best.append((fam, H, r2, ra, rb))
    L.append("**摘要（確認段年化；括號 ＝ 標籤）：** " + "；".join(
        f"{fam}H{H} 原T2 {_p(r2['確認_年化'])}（{r2['確認_標籤']}）→ T2a {_p(ra['確認_年化'])}（{ra['確認_標籤']}）、T2b {_p(rb['確認_年化'])}（{rb['確認_標籤']}）"
        for fam, H, r2, ra, rb in best) + f"；營量 v1 {_p(v1['確認_年化'])}。")
    L += ["", "| 格 | 通過率／訊號數 主 | 探索 年化／回落（比值） | 確認 年化／回落（比值） | 確認標籤 | 確認配對差〔95% CI〕 | 早年 年化／回落（比值） | 早年標籤 | 早年配對差〔95% CI〕 | 退化 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in PT.iterrows():
        pr = f"{r['通過率_主']:.3f}" if r["族"] == "甲" else str(int(r["訊號數_主"]))
        cd = "" if k == "營量v1" else f"{_p(r['確認_配對差年化'])}〔{_p(r['確認_配對差lo'])}, {_p(r['確認_配對差hi'])}〕"
        ed = "" if k == "營量v1" else f"{_p(r['早年_配對差年化'])}〔{_p(r['早年_配對差lo'])}, {_p(r['早年_配對差hi'])}〕"
        L.append(f"| {k} | {pr} | {_p(r['探索_年化'])}／{_p(r['探索_回落'])}（{r['探索_比值']:.3f}） | {_p(r['確認_年化'])}／{_p(r['確認_回落'])}（{r['確認_比值']:.3f}） | {r['確認_標籤']} | {cd} | "
                 f"{_p(r['早年_年化'])}／{_p(r['早年_回落'])}（{r['早年_比值']:.3f}） | {r['早年_標籤']} | {ed} | {'是' if r['退化'] else ''} |")
    L += ["", "## 拆開後差多少（新定義 − 原 T2，同族同 H；年化百分點）", "", "| 族 H | T2a−T2 探索／確認／早年 | T2b−T2 探索／確認／早年 |", "|---|---|---|"]
    for fam, H, r2, ra, rb in best:
        f = lambda r: "／".join(_p(r[f"{sg}_年化"] - r2[f"{sg}_年化"]) for sg in ("探索", "確認", "早年"))
        L.append(f"| {fam} H{H} | {f(ra)} | {f(rb)} |")
    L += ["", f"- 通過率（甲，營量 v1 訊號中）：主 {json.dumps({k: round(v, 3) for k, v in S['通過率（甲，主）'].items()}, ensure_ascii=False)}；早年 {json.dumps({k: round(v, 3) for k, v in S['通過率（甲，早年）'].items()}, ensure_ascii=False)}",
          f"- 訊號數（乙，窗內）：主 {S['訊號數（乙，主）']}；早年 {S['訊號數（乙，早年）']}",
          f"- 0050：{json.dumps({k: [round(v['cagr'], 4), round(v['mdd'], 4)] for k, v in S['0050'].items()}, ensure_ascii=False)}",
          f"- 閘（原 T2 與營量 v1 ＝ resultsYLtrend，[不同數, 顆數]）：{json.dumps(S['閘（原 T2 與營量 v1 ＝ resultsYLtrend；[不同數, 顆數]）'], ensure_ascii=False)}",
          "- 配對差 ＝ 原件 Y8 同式（同顆種子日報酬差、200 顆平均、月分群 CR0、×245）；退化 ＝ 原件 Y7 同式（探索段平均持股 ＜ 10 或現金 ＞ 30%）；本表只描述", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[6])


if __name__ == "__main__":
    main()

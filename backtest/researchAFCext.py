# -*- coding: utf-8 -*-
"""W1、F 確認段補跑（裁定 seq257 §三 順 3；背景 backtest/audit_s4/REPORT.md，commit c2b3b10fec）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAFCext.py [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAFCext_check.py

⭐ 與原件 researchAFC.py（commit 4762a3809f）一字不動的部分（直接 import 它的 sim／wstats 路徑與常數）：
   S1 ＝ 門檻B（researchp7.build_sig_gate_b，start 2017-01-01）、H120、n_slots 8、pick＝None、成本 0.585%、tradable＋delist on、
   W1 1,000 顆（種子 102000＋r）、F 200 顆（同種子）、F 剔除 ＝ 量測日 eligible 內 ret_120 rank(pct) ＞ 0.95、F 假訊號臂 30 次 × 200 顆（剔同數量、種子 20260925＋r）、
   主窗 2017-03-02～2026-08-24（researchp12.win_read）、0050 同窗錨 +24.02%／−33.96%
⭐ 唯一改動：面板 resultsAFC/panel.csv.gz（量測日到 2026-03-02）⇒ resultsp9_engine/panel_ext.csv.gz（同一支 build_panel，量測日到 2026-08-03；
   舊段 228,790 列逐位元同：resultsp9_engine/PANEL_SHA.md）
三版：
   V0 閘：panel_ext 截到量測日 ≤ 2026-03-02、stop_force 關 ⇒ W1 1,000 顆與 F 200 顆的年化／回落 ＝ 原件 w1_1000.csv、f_and_fake.csv（逐位元）
   V1 補面板：panel_ext 全段、stop_force 關
   V2 補面板＋停止交易強制出場：開（research11.simulate_mtm stop_force ＝ research11.stop_force_days(valid, 主窗尾)，commit 51a3dc35f3）
判定（K6 新判準，對 0050 同段）：主窗（W1 用 1,000 顆中位、F 用 200 顆中位）；確認段 2022-01-03～2026-08-24 另報（同一條權益切段、research13.window_stats）
假訊號：F ＝ 原件同一臂（30 次 × 200 顆 ⇒ 30 個中位；p ＝ 中位 ≥ F 中位的比例）；
       W1 ＝ ⚠ 本線讀法：同進場日、同筆數，從該進場日「過閘門就算訊號」池（build_sig_gate_b signal="ALL"）隨機抽股（rng 20260925＋r）；
            200 次，引擎種子 102000＋r ⇒ p ＝ 假訊號年化 ≥ W1 中位的比例（原件 W1 沒有假訊號臂）
輸出 backtest/resultsAFCext/
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

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchAFC as AFC                                 # ⭐ 原件（不改）
H2, D, R, R13, P7, P12, P4F, T = AFC.H2, AFC.D, AFC.R, AFC.R13, AFC.P7, AFC.P12, AFC.P4F, AFC.T

OUT = "backtest/resultsAFCext"
PANEL_EXT = "backtest/resultsp9_engine/panel_ext.csv.gz"
CUT = pd.Timestamp("2026-03-02")
CONF = ("2022-01-03", "2026-08-24")
SEED0, N_W1, N_F, FAKE_SEED, N_FAKE = AFC.SEED0, AFC.N_W1, AFC.N_F, AFC.FAKE_SEED, AFC.N_FAKE
N_W1FAKE = 200
SF_TAG = "停止交易強制出場：開"
_S = AFC._S


def sim_sf(sig, seed):
    R.COST = AFC.P12.COST_STD
    return R.simulate_mtm(sig, P12.RULE, P12.N_C1, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                          return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero",
                          tradable=_S["trad"], delist=_S["dl"], stop_force=_S["SF"] if _S.get("sf_on") else None)


def stats(out):
    st = AFC.wstats(out)
    c0, c1 = _S["c0"], _S["c1"]
    lo = min(out["first"], c0)
    cc, cm = R13.window_stats(out["equity"], lo, max(out["end"], c1 + 1), c0, c1 + 1)
    return {"cagr": st["cagr"], "mdd": st["mdd"], "c_cagr": float(cc), "c_mdd": float(cm), "sf_n": int(out.get("x_stop_force_n", 0))}


def job(args):
    kind, seed, j = args
    sg = _S["sig"] if kind == "W1" else (_S["sigF"] if kind == "F" else (_S["fake"][j] if kind == "Ffake" else _S["w1fake"][j]))
    st = stats(sim_sf(sg, seed)); st.update(kind=kind, seed=seed, arm=j); return st


def label(c, m, c0, m0):
    r, r0 = c / abs(m), c0 / abs(m0)
    return "合格" if (c > c0 and r >= r0) else ("另列" if c > c0 else "不合格")


def build(panel, cal, closes, opens, log, sig=None):
    if sig is None:
        sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    Tpos = sig["entry_pos"].to_numpy() - 1
    el = panel[panel["eligible"].astype(bool)].copy()
    el["rk"] = el.groupby("measure_date")["ret_120"].rank(pct=True)
    rk = {(d_, s_): v for d_, s_, v in zip(el["measure_date"], el["stock_id"], el["rk"])}
    sig["Tdate"] = [cal[int(tp)] for tp in Tpos]
    sig["rk120"] = [rk.get((d_, s_), np.nan) for d_, s_ in zip(sig["Tdate"], sig["sid"])]
    sig["F剔"] = sig["rk120"] > 0.95
    sigF = sig[~sig["F剔"]].reset_index(drop=True)
    nrm = sig.groupby("entry_pos")["F剔"].sum()
    fake = []
    for r in range(1, N_FAKE + 1):
        rng = np.random.default_rng(FAKE_SEED + r); drop = []
        for ep, g in sig.groupby("entry_pos", sort=True):
            k = int(nrm.get(ep, 0))
            if k:
                drop += list(rng.choice(g.index.to_numpy(), size=k, replace=False))
        fake.append(sig.drop(index=drop).reset_index(drop=True))
    return sig, sigF, fake


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--only", default=None, help="V3 ⇒ 只補跑 V3（讀既有 summary.json／seeds.csv.gz 的 V0～V2）"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a" if a.only else "w", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t0 = time.time()
    log(f"===== researchAFCext {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜procs {a.procs}｜{SF_TAG}（V2）=====")
    cal = D.load_calendar(); ncal = len(cal)
    pext = P4F.read_panel(PANEL_EXT)
    pcut = pext[pext["measure_date"] <= CUT].reset_index(drop=True)
    uni = D.load_universe().set_index("stock_id")["market"]
    sids = sorted(set(pext["stock_id"]))
    closes, opens, valid = {}, {}, {}
    for s in sids + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float); valid[s] = np.isfinite(c)
    w0, w1 = P12.win_bounds(cal, "全窗"); marks = P12.month_marks(cal, w0, w1)
    c0, c1 = int(cal.searchsorted(pd.Timestamp(CONF[0]))), int(cal.searchsorted(pd.Timestamp(CONF[1])))
    c50 = closes["0050"]
    m_c, m_m = R13.window_stats(c50 / c50[w0], w0, w1 + 1, w0, w1 + 1)
    k_c, k_m = R13.window_stats(c50 / c50[c0], c0, c1 + 1, c0, c1 + 1)
    anchor = abs(m_c - AFC.ANCHOR_0050[0]) <= 5e-5 and abs(m_m - AFC.ANCHOR_0050[1]) <= 5e-5
    log(f"[0050] 主窗 {m_c:+.4%}／{m_m:+.4%}（錨 {anchor}）｜確認段 {k_c:+.4%}／{k_m:+.4%}")
    SF = R.stop_force_days(valid, w1)
    RES = {"面板": {"ext": PANEL_EXT, "ext 量測日迄": str(pext["measure_date"].max().date()), "截斷版": f"量測日 ≤ {CUT.date()}"},
           "0050": {"主窗": [m_c, m_m], "確認段": [k_c, k_m]}, "0050錨": anchor, "停止交易日（主窗尾前停止）": len(SF), "標註": SF_TAG + "（V2）"}
    orig_w1 = pd.read_csv("backtest/resultsAFC/w1_1000.csv"); orig_f = pd.read_csv("backtest/resultsAFC/f_and_fake.csv")
    ALL = []
    if a.only:                                             # 主 session 重啟後續跑：V0～V2 已在 23:25 的 summary.json／seeds.csv.gz
        old = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
        for k, v in old.items():
            if k.startswith("V") or k.startswith("閘"):
                RES[k] = v
        ALL.append(pd.read_csv(os.path.join(OUT, "seeds.csv.gz")))
        log(f"[續跑] 讀回既有 V0～V2（{', '.join(k for k in RES if k.startswith('V'))}）；只跑 {a.only}")
    from backtest import researchYear1M as Y                            # T1：資料尾截斷補回（researchYear1M.sig12／pad_px，PREREGV 已用）
    cP, oP = Y.pad_px(closes, opens)
    for vname, panel, sf_on in (("V0 閘（截到 2026-03-02、stop_force 關）", pcut, False), ("V1 補面板", pext, False), ("V2 補面板＋stop_force", pext, True),
                                ("V3 補面板＋尾端截斷補回＋stop_force", pext, True)):
        if a.only and not vname.startswith(a.only):
            continue
        t1 = vname.startswith("V3")
        if t1:
            _, sigT, infoT = Y.sig12(panel, cal, closes, opens, log, "panel_ext")
            RES["T1 尾端截斷補回"] = infoT
            sig, sigF, fake = build(panel, cal, cP, oP, log, sig=sigT)
            CL, OP, NC = cP, oP, ncal + 1
        else:
            sig, sigF, fake = build(panel, cal, closes, opens, log)
            CL, OP, NC = closes, opens, ncal
        pool0 = None; tsids = set(sig["sid"])
        if t1:
            pool0 = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="ALL").sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
            tsids |= set(pool0["sid"])                     # 假訊號臂會抽到的股也要有 tradable／delist（⛔ 不影響 W1／F：引擎只查訊號列的股）
        trad = T.build(tsids, cal); dl = T.delist_status(trad, cal, official=T.load_official())
        if t1:                                             # 墊檔日：可成交、非漲跌停（只給排程出場在墊檔日的補回列結清；窗在 2026-08-24 已結束）
            trad = {s_: {"trd": np.r_[v["trd"], True], "up_o": np.r_[v["up_o"], False], "dn_o": np.r_[v["dn_o"], False], "dn_c": np.r_[v["dn_c"], False]}
                    for s_, v in trad.items()}
        S = {"closes": CL, "opens": OP, "ncal": NC, "trad": trad, "dl": dl, "w0": w0, "w1": w1, "marks": marks, "c50": m_c, "m50": m_m,
             "sig": sig, "sigF": sigF, "fake": fake, "cal": cal, "c50d": c50, "c0": c0, "c1": c1, "SF": SF, "sf_on": sf_on, "w1fake": []}
        jobs = [("W1", SEED0 + r, -1) for r in range(N_W1)] + [("F", SEED0 + r, -1) for r in range(N_F)]
        if t1:
            jobs += [("Ffake", SEED0 + r, j) for j in range(N_FAKE) for r in range(N_F)]
            byep = {ep: g.index.to_numpy() for ep, g in pool0.groupby("entry_pos")}
            cnt = sig.groupby("entry_pos").size()
            wf = []
            for r in range(N_W1FAKE):
                rng = np.random.default_rng(FAKE_SEED + r); take = []
                for ep, k in cnt.items():
                    cand = byep.get(ep, np.zeros(0, int))
                    take += list(rng.choice(cand, size=min(int(k), len(cand)), replace=False))
                wf.append(pool0.loc[sorted(take)].sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True))
            S["w1fake"] = wf
            jobs += [("W1fake", SEED0 + r, r) for r in range(N_W1FAKE)]
            sig.to_csv(os.path.join(OUT, "sig_ext.csv.gz"), index=False, float_format="%.17g")
        tt = time.time()
        with Pool(a.procs, initializer=AFC._init, initargs=(S,)) as pool:
            res = pool.map(job, jobs, chunksize=10)
        df = pd.DataFrame(res); df["版"] = vname
        ALL.append(df)
        log(f"[{vname}] S1 {len(sig):,} 筆／{sig['sid'].nunique():,} 檔／{sig['month'].nunique()} 月（進場迄 {cal[int(sig['entry_pos'].max())].date()}）｜"
            f"F 剔 {int(sig['F剔'].sum())}｜{len(jobs):,} 次引擎｜{time.time() - tt:.0f}s")
        if vname.startswith("V0"):
            a_ = df[df["kind"] == "W1"].set_index("seed"); b_ = orig_w1.set_index("seed")
            f_ = df[df["kind"] == "F"].set_index("seed"); g_ = orig_f[orig_f["arm"] == -1].set_index("seed")
            eq_w1 = all(float(a_.at[s, "cagr"]) == float(b_.at[s, "cagr"]) and float(a_.at[s, "mdd"]) == float(b_.at[s, "mdd"]) for s in b_.index)
            eq_f = all(float(f_.at[s, "cagr"]) == float(g_.at[s, "cagr"]) and float(f_.at[s, "mdd"]) == float(g_.at[s, "mdd"]) for s in g_.index)
            dmax = max(float((a_["cagr"] - b_["cagr"]).abs().max()), float((a_["mdd"] - b_["mdd"]).abs().max()),
                       float((f_["cagr"] - g_["cagr"]).abs().max()), float((f_["mdd"] - g_["mdd"]).abs().max()))
            nd = int(((a_["cagr"] != b_["cagr"]) | (a_["mdd"] != b_["mdd"])).sum()) + int(((f_["cagr"] != g_["cagr"]) | (f_["mdd"] != g_["mdd"])).sum())
            med_same = (float(a_["cagr"].median()) == float(b_["cagr"].median()) and float(a_["mdd"].median()) == float(b_["mdd"].median())
                        and float(f_["cagr"].median()) == float(g_["cagr"].median()) and float(f_["mdd"].median()) == float(g_["mdd"].median()))
            # 同一環境、同一份現行程式，改用原件面板 resultsAFC/panel.csv.gz ⇒ 與 V0 逐位元比（分開「面板」與「環境／引擎」）
            pafc = P4F.read_panel("backtest/resultsAFC/panel.csv.gz")
            sigA, sigFA, _ = build(pafc, cal, closes, opens, log)
            SA = dict(S); SA.update(sig=sigA, sigF=sigFA, fake=[])
            with Pool(a.procs, initializer=AFC._init, initargs=(SA,)) as pool:
                resA = pd.DataFrame(pool.map(job, [("W1", SEED0 + r, -1) for r in range(N_W1)] + [("F", SEED0 + r, -1) for r in range(N_F)], chunksize=10))
            x0 = df[df["kind"].isin(["W1", "F"])].reset_index(drop=True)
            same_env = bool((resA[["cagr", "mdd"]].to_numpy() == x0[["cagr", "mdd"]].to_numpy()).all()) and len(sigA) == len(sig)
            RES["閘 V0＝原件"] = {"W1 1,000 顆逐位元": eq_w1, "F 200 顆逐位元": eq_f, "S1 筆數": len(sig), "不逐位元的顆數（W1＋F 共 1,200）": nd,
                                "最大差": dmax, "中位數逐位元": med_same, "V0 ＝ 同環境用原件面板重跑（逐位元）": same_env,
                                "說明": ("不逐位元的差都在 1～2 個浮點尾數（≤ 2.3e−16）；同一環境改用原件面板重跑與 V0 逐位元相同 ⇒ 差不是面板造成；"
                                       "另用 4762a3809f 版 research11 重跑 40 顆也同樣有尾數差 ⇒ 也不是引擎改版造成 ⇒ 推定為原件執行時的浮點運算環境差異（未能再定位）")}
            log(f"[閘] V0 ＝ 原件：W1 {eq_w1}、F {eq_f}｜不逐位元 {nd}／1200、最大差 {dmax:.1e}、中位逐位元 {med_same}｜V0 ＝ 同環境原件面板 {same_env}")
            RES["閘 V0＝原件"]["中位數最大差"] = max(abs(float(a_["cagr"].median()) - float(b_["cagr"].median())), abs(float(a_["mdd"].median()) - float(b_["mdd"].median())), abs(float(f_["cagr"].median()) - float(g_["cagr"].median())), abs(float(f_["mdd"].median()) - float(g_["mdd"].median())))
            if not (same_env and dmax <= 2.3e-16):
                pd.concat(ALL).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
                json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
                raise SystemExit("⛔ 閘不過：V0 不能重現原件")
        RES[vname] = {"S1筆": len(sig), "S1檔": int(sig["sid"].nunique()), "S1月": int(sig["month"].nunique()),
                      "S1最後進場日": str(cal[int(sig["entry_pos"].max())].date()), "F剔": int(sig["F剔"].sum())}
        for kind, nm in (("W1", "W1（1,000 顆中位）"), ("F", "F（200 顆中位）")):
            x = df[df["kind"] == kind]
            c, m, cc, cm = x["cagr"].median(), x["mdd"].median(), x["c_cagr"].median(), x["c_mdd"].median()
            RES[vname][nm] = {"主窗": [c, m, c / abs(m)], "主窗判準": label(c, m, m_c, m_m), "確認段": [cc, cm, cc / abs(cm)], "確認段判準": label(cc, cm, k_c, k_m),
                              "強制出場筆_每顆": float(x["sf_n"].mean()), "舊判準（兩腳都不輸 0050）判過顆數": int(sum(bool(a1 >= m_c and b1 >= m_m and (a1 > m_c or b1 > m_m)) for a1, b1 in zip(x["cagr"], x["mdd"])))}
        if t1:
            fk = df[df["kind"] == "Ffake"].groupby("arm").agg(c=("cagr", "median"), m=("mdd", "median"), cc=("c_cagr", "median"))
            fm = RES[vname]["F（200 顆中位）"]
            RES[vname]["F 假訊號臂（30 次 × 200 顆）"] = {"p（假訊號中位年化 ≥ F）": float((fk["c"] >= fm["主窗"][0]).mean()),
                                                     "確認段 p": float((fk["cc"] >= fm["確認段"][0]).mean()),
                                                     "假訊號中位的中位": float(fk["c"].median()), "合格次數": int(sum(label(c_, m_, m_c, m_m) == "合格" for c_, m_ in zip(fk["c"], fk["m"])))}
            wfk = df[df["kind"] == "W1fake"]; wm = RES[vname]["W1（1,000 顆中位）"]
            RES[vname]["W1 假訊號臂（同進場日同筆數、閘門池隨機；200 次）"] = {"p（假訊號年化 ≥ W1 中位）": float((wfk["cagr"] >= wm["主窗"][0]).mean()),
                                                                   "確認段 p": float((wfk["c_cagr"] >= wm["確認段"][0]).mean()),
                                                                   "假訊號年化中位": float(wfk["cagr"].median()), "假訊號回落中位": float(wfk["mdd"].median()),
                                                                   "假訊號合格比例": float(np.mean([label(c_, m_, m_c, m_m) == "合格" for c_, m_ in zip(wfk["cagr"], wfk["mdd"])]))}
        log(f"  {json.dumps({k: v for k, v in RES[vname].items() if isinstance(v, dict)}, ensure_ascii=False, default=float)[:900]}")
    pd.concat(ALL).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    RES["原件"] = {"W1（1,000 顆中位）": [float(orig_w1["cagr"].median()), float(orig_w1["mdd"].median())],
                  "F（200 顆中位）": [float(orig_f[orig_f["arm"] == -1]["cagr"].median()), float(orig_f[orig_f["arm"] == -1]["mdd"].median())]}
    json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG名單出場 乙（台股策略線登錄 seq3 sha 6a81777d9f93b4ee；裁定線 seq189 發號、seq192 定案、seq195 對外稱呼）：
營飆 v1（＝ #1：PREREG10 AND regime=True N10 H120，t−1 大盤閘版）加停損／停利 6 格（判定）＋描述臂。回測線，2026-09-26。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchListExit [--procs 3] [--reps 200] [--out 目錄]

底（登錄 §一，⛔ 一字不動）：listexit_lines.setup_t1()（rerun17 快照 edc6f800、AND 訊號、t−1 大盤閘、主窗 2017-03-02～2026-08-24）
  simulate_mtm(sig, "H120", 10, default_rng(1000＋r), closes, opens, ncal, return_equity=True, **kw)；200 顆；不開 tradable、不傳 delist
判定 6 格（N_組合 ＋6）：S1、S2、T1、T2、S1＋T1、S2＋T1（參數見 ARMS；賣得現金一律 "next"、nx_cap 不給 ＝ 10 槽）
描述臂（⛔ 不判、不計 N）：
  ⓐ 閒置 6 臂（去掉 stop_proceeds／trim_proceeds ＝ 引擎 None 路徑）
     ⚠ 引擎 None 路徑 ＝ 賣得現金併入一般現金、任何槽空出來時一般新部位照 min(equity/10, 現金) 可以用到 ⇒ ⛔ 不是登錄字面「閒置到那檔出場」
  ⓑ 同平均持股對照（6 格；逐種子配對：以該格該顆的 ē 做 p9_controls.ebar_control，營飆 v1 同顆種子為底，cost_mode="engine"）
  ⓒ 跌停賣不掉 4 臂（S1、S2、S1＋T1、S2＋T1 加 stop_block＝tradability.build；只擋停損賣出）
  ⓓ D1「一般新部位優先」4 臂（T1、T2、S1＋T1、S2＋T1 加 nx_order="after"）；
     D2「併池」＝ trim_proceeds=None：T1、T2 的 D2 ＝ ⓐ（同一次跑）；S1＋T1、S2＋T1 的 D2 ＝ 停損照 next、賣半併池（2 臂）
判定（登錄 §一）：對 0050 年化中位 ＞ 0.24020209886370614（嚴格）且 年化中位 ÷ |回落中位| ≥ 0.7073712681980713 ⇒ 合格；只過第一條 ⇒ 另列；否則不合格
  對營飆 v1：resultsN17/regime_t1/seeds.csv t1 #1 同顆種子配對；年化差、回落差（回落變淺記正）兩項皆正 ≥ 190 ⇒ 比原本好；皆負 ≥ 190 ⇒ 比原本差；其餘 分不出
閘門：閘一 0050 錨逐位元；閘二 營飆 v1 原樣臂 200 顆 ＝ regime_t1 t1 #1 逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha）
輸出 backtest/resultsListExit/：cells.csv、seeds_arms.csv、seeds_controls.csv、summary.json、run.log、REPORT.md
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

from . import listexit_lines as L
from . import p9_controls as C
from . import research11 as R11
from . import researchp9 as P9

HERE = os.path.dirname(os.path.abspath(__file__))
REPS = 200
ANCHOR = (0.24020209886370614, -0.3395700527611012)
C50, R50 = 0.24020209886370614, 0.7073712681980713
TR15 = {"kind": "gain", "x": 0.15, "frac": 0.5}
TR30 = {"kind": "gain", "x": 0.30, "frac": 0.5}
JUDGED = ["S1", "S2", "T1", "T2", "S1T1", "S2T1"]
NAME = {"S1": "S1 固定停損 −10%", "S2": "S2 2×ATR 追蹤停損", "T1": "T1 +15% 賣一半", "T2": "T2 +30% 賣一半",
        "S1T1": "S1＋T1", "S2T1": "S2＋T1", "base": "營飆 v1 原樣（抱滿 120 天、不停損不停利）"}
DDK = ("單日暴跌型", "延續下跌型", "混合型")
_G: dict = {}


def arms(S1L, S2L, BLK):
    s1 = dict(stop_line=S1L, stop_line_le=True); s2 = dict(stop_line=S2L); sp = dict(stop_proceeds="next"); nx = dict(trim_proceeds="next")
    A = {"base": ({}, "base"),
         "S1": ({**s1, **sp}, "判定"), "S2": ({**s2, **sp}, "判定"),
         "T1": ({"trim_rule": TR15, **nx}, "判定"), "T2": ({"trim_rule": TR30, **nx}, "判定"),
         "S1T1": ({**s1, **sp, "trim_rule": TR15, **nx}, "判定"), "S2T1": ({**s2, **sp, "trim_rule": TR15, **nx}, "判定")}
    for k in JUDGED:                                     # ⓐ 閒置（＝ 引擎 None 路徑）
        A["a_" + k] = ({kk: vv for kk, vv in A[k][0].items() if kk not in ("stop_proceeds", "trim_proceeds")}, "ⓐ閒置")
    for k in ("S1", "S2", "S1T1", "S2T1"):              # ⓒ 跌停賣不掉
        A["blk_" + k] = ({**A[k][0], "stop_block": BLK}, "ⓒ跌停賣不掉")
    for k in ("T1", "T2", "S1T1", "S2T1"):              # ⓓ D1 一般新部位優先
        A["D1_" + k] = ({**A[k][0], "nx_order": "after"}, "ⓓD1")
    for k in ("S1T1", "S2T1"):                          # ⓓ D2 併池（組合格：停損照 next、賣半併池）
        A["D2_" + k] = ({kk: vv for kk, vv in A[k][0].items() if kk != "trim_proceeds"}, "ⓓD2")
    return A


def _kw_repr(kw):
    return {k: (v if isinstance(v, (str, bool, int, float)) or k.endswith("rule") else f"<{k}>") for k, v in kw.items()}


def _years(cal, w0, w1):
    out = []
    yrs = cal[w0:w1 + 1].year
    for y in sorted(set(yrs)):
        ix = np.flatnonzero(yrs == y) + w0
        out.append((int(y), int(ix[0]) - 1, int(ix[-1])))
    return out


def _one(args):
    key, r = args
    G = _G; ctx = G["ctx"]; RR = ctx["RR"]; w0, w1 = ctx["w0"], ctx["w1"]
    kw = G["ARMS"][key][0]
    au = []
    o = L.sim(ctx, kw, r, audit=au)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c, m, v = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    row = {"arm": key, "r": r, "seed": 1000 + r, "cagr": float(c), "mdd": float(m), "vol": float(v),
           "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"]),
           "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "expo": C.ebar_of(eq, hv, w0, w1)}
    for y, p0, p1 in G["years"]:
        row[f"y{y}"] = float(eq[p1] / eq[p0] - 1.0)
    for sc, pre in (("simple", "dd_"), ("log", "ddlog_")):
        for k in DDK:
            row[pre + k] = 0
        for e_ in P9.dd_events(eq, w0, w1 + 1):
            k, _, _ = P9.dd_type(eq, e_["peak"], e_["trough"], scale=sc)
            row[pre + k] += 1
    row["dd_n"] = row["dd_單日暴跌型"] + row["dd_延續下跌型"] + row["dd_混合型"]
    # ── audit 重建：持股檔數、周轉、成本、停損／賣半、放棄組、再買回
    closes, xmap = ctx["closes"], G["xmap"]
    n = len(eq); dheld = np.zeros(n + 1)
    pos = {}; stops = []; trims = []; P = []; buys = []; buy_amt = 0.0; cost = 0.0; nxsz = []
    for a in au:
        t = int(a["t"])
        if a["side"] == "buy":
            pos[a["sid"]] = (t, float(a["px"]), a.get("kind")); dheld[t] += 1; buys.append((t, a["sid"]))
            if w0 <= t <= w1:
                buy_amt += float(a["amt"])
            if a.get("kind") == "nx" and a["equity_prev"] > 0:
                nxsz.append(float(a["amt"]) / (float(a["equity_prev"]) / 10))
        else:
            if w0 <= t <= w1:
                cost += float(a["cost"])
            s = a["sid"]; e, ep, _ = pos[s]
            x = xmap[(s, e)]
            if a.get("kind") == "trim":
                trims.append((s, e, t, float(a["px"]), float(closes[s][x]) / float(a["px"]) - 1.0))
                continue
            pos.pop(s); dheld[t] -= 1
            stopped = t < x
            P.append((s, e, ep, t, float(a["px"]), stopped))
            if stopped:
                stops.append((t, s, float(a["px"]) / ep - 1.0, float(closes[s][x]) / ep - 1.0))
    held = np.cumsum(dheld)[:n]
    yrs_n = (w1 + 1 - w0) / 245
    meq = float(eq[w0:w1 + 1].mean())
    trig_pos = {(s, e) for s, e, _, _, _ in trims} | {(s, e) for s, e, _, _, _, st in P if st}
    rb = []
    for ts, s, _, _ in stops:
        for s2, e2, ep2, tx, px2, _ in P:
            if s2 == s and 0 <= e2 - ts <= 20:
                rb.append(px2 / ep2 - 1.0)
    rb_n = sum(any(s2 == s and 0 <= tb - ts <= 20 for tb, s2 in buys) for ts, s, _, _ in stops)
    sr = np.array([z[2] for z in stops]); sh = np.array([z[3] for z in stops]); tf = np.array([z[4] for z in trims])
    cf = (eq[w0:w1 + 1] - hv[w0:w1 + 1]) / eq[w0:w1 + 1]
    w_ = np.asarray(o.get("x_nx_waits", []), float)
    row.update({
        "n_stop": int(o.get("sl_exits", 0)), "n_trim": int(o.get("x_trim_n", 0)),
        "trig_pos_frac": len(trig_pos) / max(int(o["trades"]), 1),
        "held_mean": float(held[w0:w1 + 1].mean()), "turnover_yr": buy_amt / meq / yrs_n, "cost_total": cost, "cost_drag_yr": cost / meq / yrs_n,
        "stop_ret_mean": float(sr.mean()) if len(sr) else np.nan, "stop_ret_med": float(np.median(sr)) if len(sr) else np.nan,
        "stop_h120_mean": float(sh.mean()) if len(sh) else np.nan, "stop_h120_med": float(np.median(sh)) if len(sh) else np.nan,
        "stop_h120_better_frac": float((sh > sr).mean()) if len(sr) else np.nan, "stop_h120_ge0_frac": float((sh >= 0).mean()) if len(sh) else np.nan,
        "trim_fwd_mean": float(tf.mean()) if len(tf) else np.nan, "trim_fwd_med": float(np.median(tf)) if len(tf) else np.nan,
        "trim_fwd_p90": float(np.quantile(tf, .9)) if len(tf) else np.nan, "trim_fwd_pos_frac": float((tf > 0).mean()) if len(tf) else np.nan,
        "rebuy20_n": int(rb_n), "rebuy20_ret_mean": float(np.mean(rb)) if rb else np.nan, "rebuy20_ret_med": float(np.median(rb)) if rb else np.nan,
        "cash_mean": float(cf.mean()), "cash_med": float(np.median(cf)), "cash_end": float(cf[-1]),
        "nx_n": int(o.get("x_nx_n", 0)), "nx_stop_lots": int(o.get("x_nx_stop_lots", 0)), "nx_pending_end": int(o.get("x_nx_pending_end", 0)),
        "nx_pending_amt_end_frac": float(o.get("x_nx_pending_amt_end", 0.0)) / float(eq[w1]),
        "nxw_med": float(np.median(w_)) if len(w_) else np.nan, "nxw_p90": float(np.quantile(w_, .9)) if len(w_) else np.nan,
        "nxw_mean": float(w_.mean()) if len(w_) else np.nan, "nxw_max": float(w_.max()) if len(w_) else np.nan,
        "nxsz_med": float(np.median(nxsz)) if nxsz else np.nan, "nxsz_mean": float(np.mean(nxsz)) if nxsz else np.nan,
        "normal_n": int(o["trades"]) - int(o.get("x_nx_n", 0)), "sl_block_days": int(o.get("sl_block_days", 0))})
    return row


def _ctrl(args):
    """ⓑ 同平均持股對照：營飆 v1 同顆種子（audit）⇒ 對每個判定格的 ē 做 ebar_control。"""
    r, params = args
    G = _G; ctx = G["ctx"]; RR = ctx["RR"]; w0, w1 = ctx["w0"], ctx["w1"]
    au = []
    o = L.sim(ctx, {}, r, audit=au)
    out = []
    for k, eb in params:
        rs = C.ebar_control(o["equity"], o["hold_val"], au, ctx["cal"], w0, w1, eb, cost_mode="engine")
        c, m, v = RR.win_metrics(rs["V"], o["first"], o["end"], w0, w1)
        out.append({"cell": k, "r": r, "ebar": float(eb), "ebar_realized": float(rs["ebar_realized"]), "cagr": float(c), "mdd": float(m), "vol": float(v)})
    return out


def label(c, m):
    ratio = c / abs(m)
    return ("合格" if (c > C50 and ratio >= R50) else ("另列" if c > C50 else "不合格")), ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--out", default=os.path.join(HERE, "resultsListExit"))
    a = ap.parse_args()
    OUT = a.out; os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    t00 = time.time()
    log(f"===== researchListExit procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("research11.py", "listexit_lines.py", "rerun17.py", "researchListExit.py")}
    log(f"[程式 sha256] {src}")
    ctx = L.setup_t1(log)
    RR, cal, sig, w0, w1 = ctx["RR"], ctx["cal"], ctx["sig"], ctx["w0"], ctx["w1"]
    bw = RR.bench_row(cal, RR.load_bench(cal), w0, w1 + 1)
    g1 = repr(bw["cagr"]) == repr(ANCHOR[0]) and repr(bw["mdd"]) == repr(ANCHOR[1])
    log(f"[閘一 0050 錨] 逐位元 {g1}")
    if not g1:
        raise SystemExit("⛔ 閘一不過")
    t0 = time.time()
    S1L = L.s1_lines(sig, "H120", ctx["opens"], ctx["closes"])
    S2L, sk = L.s2_lines(sig, "H120", ctx["opens"], ctx["closes"], lambda s: R11.load_bars(s, ctx["mk"].get(s, "twse"), cal), 2.0, "entry_close")
    from . import tradability as T
    BLK = T.build(set(sig["sid"]), cal)
    k114 = int((sig["k"] < 113).sum())
    build = {"訊號列": int(len(sig)), "xpos_H120≥0": int((sig["xpos_H120"] >= 0).sum()), "S1 線": len(S1L), "S2 線": len(S2L), "S2 略過": sk,
             "訊號日有效 K 棒 ＜ 114 根的筆數": k114, "ATR": L.ATR_NOTE, "S2 起點": "entry_close（seq192 ① 甲）"}
    log(f"[建線] {build}｜{time.time() - t0:.0f}s")
    ARMS = arms(S1L, S2L, BLK)
    _G.update(ctx=ctx, ARMS=ARMS, years=_years(cal, w0, w1),
              xmap={(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])})
    ref = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    rows = []
    with Pool(a.procs) as pool:
        t0 = time.time()
        B = pd.DataFrame(pool.map(_one, [("base", r) for r in range(a.reps)], chunksize=4)).set_index("r").sort_index()
        bad = [r for r in B.index if not (all(repr(float(B.loc[r, k])) == repr(float(ref.loc[r, k])) for k in ("cagr", "mdd", "vol"))
                                          and all(int(B.loc[r, k]) == int(ref.loc[r, k]) for k in ("first", "end", "trades"))
                                          and B.loc[r, "eq_sha"] == str(ref.loc[r, "eq_sha"]))]
        g2 = not bad
        log(f"[閘二 營飆 v1 原樣臂 {a.reps} 顆 ＝ regime_t1 t1 #1] 逐位元 {g2}｜不同 {bad[:5]}｜{time.time() - t0:.0f}s")
        if not g2:
            raise SystemExit("⛔ 閘二不過")
        rows.append(B.reset_index())
        for key in [k for k in ARMS if k != "base"]:
            t0 = time.time()
            D = pd.DataFrame(pool.map(_one, [(key, r) for r in range(a.reps)], chunksize=4))
            rows.append(D)
            log(f"  [{key}] {ARMS[key][1]}｜{time.time() - t0:.0f}s")
        A = pd.concat(rows, ignore_index=True)
        E = A[A["arm"].isin(JUDGED)].pivot(index="r", columns="arm", values="expo")
        t0 = time.time()
        CT = pd.DataFrame([z for y in pool.map(_ctrl, [(r, [(k, float(E.loc[r, k])) for k in JUDGED]) for r in range(a.reps)], chunksize=4) for z in y])
        log(f"  [ⓑ 同平均持股對照] {time.time() - t0:.0f}s")
    A.to_csv(os.path.join(OUT, "seeds_arms.csv"), index=False)
    CT.to_csv(os.path.join(OUT, "seeds_controls.csv"), index=False)

    # ── 彙總
    base = ref.loc[range(a.reps)]
    cells = []
    for key, (kw, kind) in ARMS.items():
        g = A[A["arm"] == key].set_index("r").sort_index()
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio = label(c, m)
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        npos = int(((dc > 0) & (dm > 0)).sum()); nneg = int(((dc < 0) & (dm < 0)).sum())
        vs = "比原本好" if npos >= 190 else ("比原本差" if nneg >= 190 else "分不出")
        row = {"arm": key, "類": kind, "名": NAME.get(key, key), "kw": json.dumps(_kw_repr(kw), ensure_ascii=False), "n": len(g),
               "cagr_med": c, "mdd_med": m, "ratio": ratio, "label": lab if kind == "判定" else f"{lab}（描述）",
               "cagr_p10": float(g["cagr"].quantile(.1)), "cagr_p90": float(g["cagr"].quantile(.9)),
               "mdd_p10": float(g["mdd"].quantile(.1)), "mdd_p90": float(g["mdd"].quantile(.9)),
               "vs_v1_both_pos": npos, "vs_v1_both_neg": nneg, "vs_v1": vs if kind in ("判定", "ⓒ跌停賣不掉") else f"{vs}（描述）",
               "d_cagr_med": float(dc.median()), "d_mdd_med": float(dm.median())}
        for q in ("n_stop", "n_trim", "trig_pos_frac", "held_mean", "turnover_yr", "cost_total", "cost_drag_yr", "stop_ret_mean", "stop_ret_med",
                  "stop_h120_mean", "stop_h120_med", "stop_h120_better_frac", "stop_h120_ge0_frac", "trim_fwd_mean", "trim_fwd_med", "trim_fwd_p90",
                  "trim_fwd_pos_frac", "rebuy20_n", "rebuy20_ret_mean", "rebuy20_ret_med", "cash_mean", "cash_med", "cash_end", "nx_n", "nx_stop_lots",
                  "nx_pending_end", "nx_pending_amt_end_frac", "nxw_med", "nxw_p90", "nxsz_med", "nxsz_mean", "normal_n", "trades", "expo",
                  "sl_block_days", "dd_n") + tuple("dd_" + k for k in DDK) + tuple("ddlog_" + k for k in DDK):
            x = g[q].astype(float)
            row[q] = float(x.median()); row[q + "_p10"] = float(x.quantile(.1)); row[q + "_p90"] = float(x.quantile(.9))
        for q in [c_ for c_ in g.columns if c_.startswith("y") and c_[1:].isdigit()]:
            row[q] = float(g[q].median())
        if key in JUDGED:
            ct = CT[CT["cell"] == key].set_index("r").sort_index()
            cc, cm = float(ct["cagr"].median()), float(ct["mdd"].median())
            row.update({"ctrl_ebar_cagr_med": cc, "ctrl_ebar_mdd_med": cm, "ctrl_ebar_label": label(cc, cm)[0] + "（描述）",
                        "ctrl_pair_d_cagr_med": float((g["cagr"] - ct["cagr"]).median()), "ctrl_pair_d_mdd_med": float((g["mdd"] - ct["mdd"]).median())})
        cells.append(row)
    TB = pd.DataFrame(cells)
    TB.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    S = {"登錄": "PREREG名單出場 seq3 sha 6a81777d9f93b4ee（乙）", "閘": {"一_0050錨": g1, "二_營飆v1原樣臂": g2}, "建線": build, "程式": src,
         "判準": {"C50": C50, "R50": R50, "配對門檻": 190}, "N帳": {"N_組合": "+6（S1、S2、T1、T2、S1＋T1、S2＋T1）", "不計": "營飆 v1 原樣臂、ⓐ、ⓑ、ⓒ、ⓓ"},
         "D2註": "T1、T2 的 D2 ＝ ⓐ 閒置（同一次跑）；S1＋T1、S2＋T1 的 D2 ＝ 停損照 next、賣半併池（D2_S1T1、D2_S2T1）",
         "ⓐ註": "ⓐ ＝ 引擎 None 路徑（賣得現金併入一般現金，任何槽空出來時一般新部位照 min(equity/10, 現金) 可用到）⇒ ⛔ 不是登錄字面「閒置到那檔出場」",
         "臂": {k: {"類": v[1], "kw": _kw_repr(v[0])} for k, v in ARMS.items()}, "格": cells, "秒": round(time.time() - t00)}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(TB, S, OUT)
    log(f"[完成] {time.time() - t00:.0f}s")


FOOT = "這是全部選到的股票平均起來的結果，不是對某一檔的預測"


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def report(TB, S, OUT):
    T = TB.set_index("arm")
    Lines = ["# PREREG名單出場 乙：營飆 v1 加停損／停利（判定 6 格＋描述臂）", "",
             f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq3（sha 6a81777d9f93b4ee）；裁定 seq189／seq192／seq195。回測線。", "",
             f"閘一 0050 錨逐位元：{S['閘']['一_0050錨']}｜閘二 營飆 v1 原樣臂 200 顆 ＝ resultsN17/regime_t1/seeds.csv t1 #1 逐位元：{S['閘']['二_營飆v1原樣臂']}", "",
             f"建線：{S['建線']}", "", "## 一、結果句（⛔ 只照登錄 §三查表）", ""]
    good = [k for k in JUDGED if T.loc[k, "vs_v1"] == "比原本好"]
    for k in JUDGED:
        q = T.loc[k]
        s = f"- **{NAME[k]}**：對 0050「{q['label']}」（年化中位 {_p(q['cagr_med'])}、回落中位 {_p(q['mdd_med'])}）；對原本「{q['vs_v1']}」"
        if "blk_" + k in T.index:
            qb = T.loc["blk_" + k]
            lb = qb["label"].replace("（描述）", "")
            if lb != q["label"] or qb["vs_v1"] != q["vs_v1"]:
                s += f"；⚠ 開盤跌停／停牌賣不掉版：對 0050「{lb}」（年化中位 {_p(qb['cagr_med'])}、回落中位 {_p(qb['mdd_med'])}）、對原本「{qb['vs_v1']}」"
        if q["label"] == "合格" and q["vs_v1"] == "比原本好":
            s += f"。這套加〔{NAME[k]}〕，在 2017～2026 這段比原本好；⚠ 事後挑的歷史最好，要進 2012～2014 驗收段＋前瞻紀錄才算數"
        else:
            s += "。名單照原本：第 120 個交易日收盤賣，不停損、不停利"
        if good:
            s += f"。試了 6 種，{len(good)} 種好，可能是運氣"
        Lines.append(s + f"。（{FOOT}）")
    Lines += ["", "## 二、判定 6 格＋營飆 v1 原樣", "",
              "| 格 | 年化中位 | 回落中位 | 比值 | 對 0050 | 對原本（皆正／皆負） | 年化差中位 | 回落差中位 | 停損 | 賣半 | 觸發部位占比 | 平均持股檔數 | 周轉/年 | 成本/年 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in ["base"] + JUDGED:
        q = T.loc[k]
        Lines.append(f"| {NAME[k]} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.4f} | {q['label']} | {q['vs_v1']}（{q['vs_v1_both_pos']}／{q['vs_v1_both_neg']}） | "
                     f"{_p(q['d_cagr_med'])} | {_p(q['d_mdd_med'])} | {q['n_stop']:.0f} | {q['n_trim']:.0f} | {q['trig_pos_frac']:.3f} | {q['held_mean']:.2f} | "
                     f"{q['turnover_yr']:.2f} | {_p(q['cost_drag_yr'])} |")
    Lines += ["", "## 三、必報（200 顆中位；括號 p10～p90）", "",
              "| 格 | 停損 實際報酬中位 | 放棄組：抱到第 120 根 平均／中位 | 放棄組：抱著較好占比／回到進場價以上占比 | 賣掉那一半續抱到第 120 根 平均／中位／p90 | 待買買進 | 一般新部位 | 等待中位／p90 | 期末未買待買（筆／占期末權益） | 現金比例 均值／中位 | 待買大小占 slot | 停損後 20 日內又買回（次／報酬中位） |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in JUDGED:
        q = T.loc[k]
        Lines.append(f"| {NAME[k]} | {_p(q['stop_ret_med'])} | {_p(q['stop_h120_mean'])}／{_p(q['stop_h120_med'])} | {q['stop_h120_better_frac']:.3f}／{q['stop_h120_ge0_frac']:.3f} | "
                     f"{_p(q['trim_fwd_mean'])}／{_p(q['trim_fwd_med'])}／{_p(q['trim_fwd_p90'])} | {q['nx_n']:.0f} | {q['normal_n']:.0f} | {q['nxw_med']:.1f}／{q['nxw_p90']:.1f} | "
                     f"{q['nx_pending_end']:.0f}／{q['nx_pending_amt_end_frac']:.4f} | {q['cash_mean']:.3f}／{q['cash_med']:.3f} | {q['nxsz_med']:.3f} | {q['rebuy20_n']:.0f}／{_p(q['rebuy20_ret_med'])} |")
    Lines += ["", "註：現金比例 ＝ 主窗逐日（現金 ÷ 權益）；期末閒置現金以「模擬結束仍未買出的待買」報（筆數、占主窗末權益）。"
              "⚠ 兩個尾端效應：①主窗最後一天持股很少（最後約 120 天進場的訊號沒有第 120 根收盤 ⇒ 引擎慣例 xpos＝−1 不進模擬）⇒ cells.csv 的 cash_end 多半接近 1，⛔ 不當期末閒置讀；"
              "②最後一個訊號之後停損／賣半拿回的錢沒有候選可買 ⇒ 期末未買待買金額含這段尾巴（S2 的 1.00 ＝ 最後幾筆全被停損、錢都在佇列裡）。",
              "回落分型（log 口徑主；simple 並列）與分年報酬見 cells.csv（ddlog_*、dd_*、yYYYY 欄）；觸發次數與各量的 p10／p90 見 cells.csv 的 *_p10、*_p90。", "",
              "## 四、描述臂（⛔ 不判、不計 N）", "",
              "- ⓐ 閒置 ＝ 引擎 None 路徑：賣得現金併入一般現金、任何槽空出來時一般新部位照 min(equity/10, 現金) 可以用到 ⇒ ⛔ 與登錄字面「閒置到那檔出場」不同（引擎沒有綁到那檔出場的閒置）",
              "- D2（併池）在 T1、T2 ＝ ⓐ（同一次跑）；S1＋T1、S2＋T1 的 D2 ＝ 停損照 next、賣半併池", "",
              "| 臂 | 類 | 年化中位 | 回落中位 | 比值 | 對 0050 | 對原本 | 一般新部位 | 待買買進 | 現金比例 均值／中位 | 待買大小占 slot | 等待中位 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, q in T.iterrows():
        if q["類"] in ("判定", "base"):
            continue
        Lines.append(f"| {k} | {q['類']} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.4f} | {q['label']} | {q['vs_v1']} | {q['normal_n']:.0f} | {q['nx_n']:.0f} | "
                     f"{q['cash_mean']:.3f}／{q['cash_med']:.3f} | {q['nxsz_med']:.3f} | {q['nxw_med']:.1f} |")
    Lines += ["", "ⓑ 同平均持股對照（逐種子 ē、營飆 v1 同顆為底）：", "", "| 格 | 對照 年化中位／回落中位 | 標籤（描述） | 本格 − 對照 年化差中位／回落差中位 |", "|---|---|---|---|"]
    for k in JUDGED:
        q = T.loc[k]
        Lines.append(f"| {NAME[k]} | {_p(q['ctrl_ebar_cagr_med'])}／{_p(q['ctrl_ebar_mdd_med'])} | {q['ctrl_ebar_label']} | {_p(q['ctrl_pair_d_cagr_med'])}／{_p(q['ctrl_pair_d_mdd_med'])} |")
    Lines += ["", "## 五、組合格現金比例的機制", "",
              "引擎規則（登錄乙 ＋ seq3 待買）：賣得現金一筆一檔、全額、待買先配、仍在 10 槽上限內。賣半只拿回半份 ⇒ 待買買進的是一個【小】部位卻佔一整槽；"
              "它再賣半或停損 ⇒ 下一筆更小（碎片化）；10 槽被小部位佔滿 ⇒ 一般現金（含停損後沒配出去的錢、賣半後的零頭）找不到空槽可投 ⇒ 帳上長期是現金。"
              "S1＋T1、S2＋T1 兩條觸發同時作用 ⇒ 換手最快、碎片最細 ⇒ 現金比例最高。D1（一般優先）與 D2（併池）是機制說明，⛔ 不改判定（裁定 seq192）。", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Lines) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG營飆停損（台股策略線登錄 seq1 sha bbd598d26c8f31d8；裁定線 seq200＋附則 ⓓⓔ）：營飆 v1 加六族停損＋停損後補一檔。
回測線，2026-09-26。本檔也放兩件（營飆停損／營飆時停）共用的執行器 run_study；researchYfTime.py 呼叫它。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfStop [--procs 3] [--reps 200] [--out 目錄]

底（登錄 §一 ＝ PREREG名單出場 §一）：listexit_lines.setup_t1()；simulate_mtm(sig, "H120", 10, default_rng(1000＋r), …)；200 顆
判定 6 格（N_組合 ＋6）：P15、T20、A3、M20、M50、F（線 ＝ yfstop_lines，參數照 LINES_REPORT §五／§六）；kw ＝ {stop_line, stop_line_le, stop_proceeds:"next"}
  M20／M50 的 arm ＝ "state"（裁定：照登錄字面「收盤 ＜ 均線」當狀態；只有 M20 21 列、M50 9 列受影響）；另兩種 arm（cross_sig、cross_entry）存在、本件不跑
參照列（⛔ 不重判、不計 N）：S1、S2 ＝ resultsListExit/cells.csv（PREREG名單出場 乙）
描述臂（⛔ 不判、不計 N）：
  ⓐ 補一檔照 equity／10 開整份 ＝ 只給 stop_line、不給 stop_proceeds：停損的錢併回一般現金，空槽照 min(equity/10, 現金) 開一般新部位
     （與登錄字面的差別：現金不足 equity/10 時只開得到現金那麼多；其餘等價——同一個池、同一套抽籤、同一個 10 槽、等下一個有候選的日子）
  ⓑ 開盤跌停／停牌賣不掉版 ＝ 加 stop_block（tradability.build；只擋停損賣出）
  ⓒ 排名補股：登錄事前寫死的條件（PREREG營飆排名 有鍵判好才跑）不成立 ⇒ 不跑；逐字：「排名沒有比抽籤好，補股照抽籤」
  ⓓ 補股池放寬（seq200 ⓓ；--pool）：引擎 nx_pool＝resultsYfStop/pool_and_nodedup.csv.gz 經 yfstop_lines.pool_rows（t−1 三條件、不去重、主窗）
     ⇒ 待買只從這個池挑、一般新部位仍用營飆 v1 訊號；A 6 格＋B 9 格各 200 顆（⛔ 描述、不判、不計 N）；池多的 64 檔用 rerun17.load_prices 補載價格；
     停損線照同一套建構器建在池列上（池 ⊇ v1 訊號列，同 (sid, entry_pos) 同一條線）⇒ 輸出 poolD_*、POOLD_REPORT.md
判準、閘、必報：見 run_study
輸出 backtest/resultsYfStop/：body_cells.csv、body_seeds_arms.csv、body_summary.json、body_run.log、REPORT.md
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
ANCHOR = (0.24020209886370614, -0.3395700527611012)
C50, R50 = 0.24020209886370614, 0.7073712681980713
DDK = ("單日暴跌型", "延續下跌型", "混合型")
FOOT = "這是全部選到的股票平均起來的結果，不是對某一檔的預測"
_G: dict = {}
_BARS: dict = {}


def bars_of(s):
    if s not in _BARS:
        ctx = _G["ctx"]
        _BARS[s] = R11.load_bars(s, ctx["mk"].get(s, "twse"), ctx["cal"])
    return _BARS[s]


def valid_of(s):
    v = np.zeros(_G["ctx"]["ncal"], bool); v[bars_of(s)["idx"]] = True
    return v


def _q(x, p):
    return float(np.quantile(x, p)) if len(x) else np.nan


def _one(args):
    """一顆：跑引擎（audit）⇒ 只回計數與結構量＋ cagr／mdd／vol／分年（判定用）。"""
    key, r = args
    G = _G; ctx = G["ctx"]; RR = ctx["RR"]; w0, w1 = ctx["w0"], ctx["w1"]
    kw = G["ARMS"][key][0]
    au = []
    o = L.sim(ctx, kw, r, audit=au)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c, m, v = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    row = {"arm": key, "r": r, "seed": 1000 + r, "cagr": float(c), "mdd": float(m), "vol": float(v), "first": int(o["first"]), "end": int(o["end"]),
           "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "expo": C.ebar_of(eq, hv, w0, w1)}
    for y, p0, p1 in G["years"]:
        row[f"y{y}"] = float(eq[p1] / eq[p0] - 1.0)
    for sc, pre in (("simple", "dd_"), ("log", "ddlog_")):
        for k in DDK:
            row[pre + k] = 0
        for e_ in P9.dd_events(eq, w0, w1 + 1):
            k, _, _ = P9.dd_type(eq, e_["peak"], e_["trough"], scale=sc)
            row[pre + k] += 1
    closes, xmap, V = ctx["closes"], G["xmap"], G["valid"]
    lines = kw.get("stop_line")
    n = len(eq); dheld = np.zeros(n + 1)
    pos = {}; stops = []; P = []; buys = []; nxb = []; buy_amt = 0.0; cost = 0.0; nxsz = []; dist0 = []
    for a in au:
        t = int(a["t"])
        if a["side"] == "buy":
            s = a["sid"]; pos[s] = (t, float(a["px"]), a.get("kind")); dheld[t] += 1; buys.append((t, s))
            if w0 <= t <= w1:
                buy_amt += float(a["amt"])
            if a.get("kind") == "nx":
                nxb.append((t, s, float(a["px"])))
                if a["equity_prev"] > 0:
                    nxsz.append(float(a["amt"]) / (float(a["equity_prev"]) / 10))
            if lines is not None and (s, t) in lines:          # 停損距離：進場日收盤那條線離進場價
                st0, lv = lines[(s, t)]
                if np.isfinite(lv[0]):
                    dist0.append(1.0 - float(lv[0]) / float(a["px"]))
        else:
            if w0 <= t <= w1:
                cost += float(a["cost"])
            s = a["sid"]; e, ep, kd = pos.pop(s); dheld[t] -= 1
            x = xmap[(s, e)]
            stopped = t < x
            P.append((s, e, ep, t, float(a["px"]), stopped, kd))
            if stopped:
                trig_bar = int(V[s][e:t].sum())                                  # ⓔ 引擎實際：觸發日（t−1）是進場後第幾根有效 K 棒（進場日 ＝ 1）
                stops.append((t, s, float(a["px"]) / ep - 1.0, float(closes[s][x]) / ep - 1.0, float(closes[s][x]) / float(a["px"]) - 1.0, trig_bar))
    held = np.cumsum(dheld)[:n]
    yrs_n = (w1 + 1 - w0) / 245
    meq = float(eq[w0:w1 + 1].mean())
    # 補進來那檔 vs 被停那檔續抱（只有停損產生待買 ⇒ 先進先出一對一）
    done = {(s, e): (px_out / ep - 1.0) for s, e, ep, t, px_out, st, kd in P}
    rep_ret = []; cont = []; better = []
    for i, (t_b, s_b, px_b) in enumerate(nxb):
        if i >= len(stops):
            break
        rr_ = done.get((s_b, t_b))
        if rr_ is None:
            continue                                                              # 補進來那檔模擬結束還沒出場
        rep_ret.append(rr_); cont.append(stops[i][4]); better.append(rr_ > stops[i][4])
    rb = []
    for ts, s, *_ in stops:
        for s2, e2, ep2, tx, px2, _, _ in P:
            if s2 == s and 0 <= e2 - ts <= 20:
                rb.append(px2 / ep2 - 1.0)
    rb_n = sum(any(s2 == s and 0 <= tb - ts <= 20 for tb, s2 in buys) for ts, s, *_ in stops)
    sr = np.array([z[2] for z in stops]); sh = np.array([z[3] for z in stops]); tb_ = np.array([z[5] for z in stops], float)
    cf = (eq[w0:w1 + 1] - hv[w0:w1 + 1]) / eq[w0:w1 + 1]
    w_ = np.asarray(o.get("x_nx_waits", []), float)
    row.update({
        "n_stop": int(o.get("sl_exits", 0)), "stop_frac_pos": len(stops) / max(int(o["trades"]), 1),
        "held_mean": float(held[w0:w1 + 1].mean()), "turnover_yr": buy_amt / meq / yrs_n, "cost_total": cost, "cost_drag_yr": cost / meq / yrs_n,
        "dist0_med": float(np.median(dist0)) if dist0 else np.nan, "dist0_p10": _q(dist0, .1), "dist0_p90": _q(dist0, .9),
        "trig_bar_med": float(np.median(tb_)) if len(tb_) else np.nan, "trig_bar_p10": _q(tb_, .1), "trig_bar_p90": _q(tb_, .9),
        "stop_ret_mean": float(sr.mean()) if len(sr) else np.nan, "stop_ret_med": float(np.median(sr)) if len(sr) else np.nan,
        "stop_ret_p10": _q(sr, .1), "stop_ret_p90": _q(sr, .9),
        "stop_h120_mean": float(sh.mean()) if len(sh) else np.nan, "stop_h120_med": float(np.median(sh)) if len(sh) else np.nan,
        "stop_h120_better_frac": float((sh > sr).mean()) if len(sr) else np.nan,
        "rep_ret_mean": float(np.mean(rep_ret)) if rep_ret else np.nan, "rep_ret_med": float(np.median(rep_ret)) if rep_ret else np.nan,
        "cont_ret_mean": float(np.mean(cont)) if cont else np.nan, "cont_ret_med": float(np.median(cont)) if cont else np.nan,
        "rep_better_frac": float(np.mean(better)) if better else np.nan, "rep_pairs": len(better),
        "rebuy20_n": int(rb_n), "rebuy20_ret_mean": float(np.mean(rb)) if rb else np.nan, "rebuy20_ret_med": float(np.median(rb)) if rb else np.nan,
        "cash_mean": float(cf.mean()), "cash_med": float(np.median(cf)),
        "nx_n": int(o.get("x_nx_n", 0)), "nx_pending_end": int(o.get("x_nx_pending_end", 0)),
        "nxw_med": float(np.median(w_)) if len(w_) else np.nan, "nxw_p90": _q(w_, .9), "nxw_sameday_frac": float((w_ == 0).mean()) if len(w_) else np.nan,
        "nxsz_med": float(np.median(nxsz)) if nxsz else np.nan, "normal_n": int(o["trades"]) - int(o.get("x_nx_n", 0)),
        "sl_block_days": int(o.get("sl_block_days", 0)),
        "nx_pool_n": int(o.get("x_nx_pool_n", 0)), "nx_pool_empty": int(o.get("x_nx_pool_empty_days", 0))})
    return row


def label(c, m):
    ratio = c / abs(m)
    return ("合格" if (c > C50 and ratio >= R50) else ("另列" if c > C50 else "不合格")), ratio


def years_of(cal, w0, w1):
    out = []; yrs = cal[w0:w1 + 1].year
    for y in sorted(set(yrs)):
        ix = np.flatnonzero(yrs == y) + w0
        out.append((int(y), int(ix[0]) - 1, int(ix[-1])))
    return out


QCOLS = ("n_stop", "stop_frac_pos", "held_mean", "turnover_yr", "cost_total", "cost_drag_yr", "dist0_med", "dist0_p10", "dist0_p90",
         "trig_bar_med", "trig_bar_p10", "trig_bar_p90", "stop_ret_mean", "stop_ret_med", "stop_ret_p10", "stop_ret_p90",
         "stop_h120_mean", "stop_h120_med", "stop_h120_better_frac", "rep_ret_mean", "rep_ret_med", "cont_ret_mean", "cont_ret_med",
         "rep_better_frac", "rep_pairs", "rebuy20_n", "rebuy20_ret_mean", "rebuy20_ret_med", "cash_mean", "cash_med", "nx_n", "nx_pending_end",
         "nxw_med", "nxw_p90", "nxw_sameday_frac", "nxsz_med", "normal_n", "trades", "expo", "sl_block_days", "nx_pool_n", "nx_pool_empty") + \
    tuple("ddlog_" + k for k in DDK) + tuple("dd_" + k for k in DDK)


def run_study(title, tag, arms_fn, out_dir, names, judged, n_tries_text, reps, procs, extra_summary, report_fn):
    """兩件共用：閘一 0050 錨、閘二 營飆 v1 原樣臂 ＝ regime_t1 t1 #1 逐位元；判準：對 0050、對營飆 v1（190／200）。"""
    os.makedirs(out_dir, exist_ok=True)
    pre = {"stop": "body_", "time": "", "poolD": "poolD_"}[tag]
    logf = open(os.path.join(out_dir, pre + "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    t00 = time.time()
    log(f"===== {title} procs={procs} reps={reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("research11.py", "listexit_lines.py", "yfstop_lines.py", "researchYfStop.py", "researchYfTime.py") if os.path.exists(os.path.join(HERE, f))}
    log(f"[程式 sha256] {src}")
    ctx = L.setup_t1(log)
    RR, cal, sig, w0, w1 = ctx["RR"], ctx["cal"], ctx["sig"], ctx["w0"], ctx["w1"]
    bw = RR.bench_row(cal, RR.load_bench(cal), w0, w1 + 1)
    g1 = repr(bw["cagr"]) == repr(ANCHOR[0]) and repr(bw["mdd"]) == repr(ANCHOR[1])
    log(f"[閘一 0050 錨] 逐位元 {g1}")
    if not g1:
        raise SystemExit("⛔ 閘一不過")
    _G.update(ctx=ctx, years=years_of(cal, w0, w1), xmap={(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])})
    t0 = time.time()
    ARMS, build = arms_fn(ctx)
    _G["ARMS"] = ARMS
    _G["valid"] = {s: valid_of(s) for s in set(sig["sid"]) | set(_G.get("extra_sids", ()))}
    log(f"[建線] {build}｜{time.time() - t0:.0f}s")
    ref = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r").sort_index()
    rows = []
    with Pool(procs) as pool:
        t0 = time.time()
        B = pd.DataFrame(pool.map(_one, [("base", r) for r in range(reps)], chunksize=4)).set_index("r").sort_index()
        bad = [r for r in B.index if not (all(repr(float(B.loc[r, k])) == repr(float(ref.loc[r, k])) for k in ("cagr", "mdd", "vol"))
                                          and all(int(B.loc[r, k]) == int(ref.loc[r, k]) for k in ("first", "end", "trades"))
                                          and B.loc[r, "eq_sha"] == str(ref.loc[r, "eq_sha"]))]
        g2 = not bad
        log(f"[閘二 營飆 v1 原樣臂 {reps} 顆 ＝ regime_t1 t1 #1] 逐位元 {g2}｜{time.time() - t0:.0f}s")
        if not g2:
            raise SystemExit("⛔ 閘二不過")
        rows.append(B.reset_index())
        for key in [k for k in ARMS if k != "base"]:
            t0 = time.time()
            rows.append(pd.DataFrame(pool.map(_one, [(key, r) for r in range(reps)], chunksize=4)))
            log(f"  [{key}] {ARMS[key][1]}｜{time.time() - t0:.0f}s")
    A = pd.concat(rows, ignore_index=True)
    A.to_csv(os.path.join(out_dir, pre + "seeds_arms.csv"), index=False)
    base = ref.loc[range(reps)]
    cells = []
    for key, (kw, kind) in ARMS.items():
        g = A[A["arm"] == key].set_index("r").sort_index()
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio = label(c, m)
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        npos = int(((dc > 0) & (dm > 0)).sum()); nneg = int(((dc < 0) & (dm < 0)).sum())
        vs = "好" if npos >= 190 else ("差" if nneg >= 190 else "分不出")
        row = {"arm": key, "類": kind, "名": names.get(key, key), "n": len(g), "cagr_med": c, "mdd_med": m, "ratio": ratio,
               "label": lab if kind == "判定" else f"{lab}（描述）", "vs_v1_both_pos": npos, "vs_v1_both_neg": nneg,
               "vs_v1": vs if kind == "判定" else f"{vs}（描述）", "d_cagr_med": float(dc.median()), "d_mdd_med": float(dm.median()),
               "cagr_p10": float(g["cagr"].quantile(.1)), "cagr_p90": float(g["cagr"].quantile(.9)),
               "mdd_p10": float(g["mdd"].quantile(.1)), "mdd_p90": float(g["mdd"].quantile(.9))}
        for q in QCOLS:
            x = g[q].astype(float)
            row[q] = float(x.median()); row[q + "_p10"] = float(x.quantile(.1)); row[q + "_p90"] = float(x.quantile(.9))
        for q in [c_ for c_ in g.columns if c_.startswith("y") and c_[1:].isdigit()]:
            row[q] = float(g[q].median())
        cells.append(row)
    TB = pd.DataFrame(cells)
    TB.to_csv(os.path.join(out_dir, pre + "cells.csv"), index=False)
    S = {"件": title, "閘": {"一_0050錨": g1, "二_營飆v1原樣臂": g2}, "建線": build, "程式": src,
         "判準": {"C50": C50, "R50": R50, "配對門檻": 190}, "臂": {k: v[1] for k, v in ARMS.items()}, "格": cells, "秒": round(time.time() - t00), **extra_summary}
    json.dump(S, open(os.path.join(out_dir, pre + "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report_fn(TB, S, out_dir)
    log(f"[完成] {time.time() - t00:.0f}s")


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def common_tables(T, rows, head):
    Ls = ["", "## 判定格", "",
          "| 格 | 年化中位 | 回落中位 | 比值 | 對 0050 | 對營飆 v1（皆正／皆負） | 年化差中位 | 回落差中位 |", "|---|---|---|---|---|---|---|---|"]
    for k in rows:
        q = T.loc[k]
        Ls.append(f"| {q['名']} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.4f} | {q['label']} | {q['vs_v1']}（{q['vs_v1_both_pos']}／{q['vs_v1_both_neg']}） | "
                  f"{_p(q['d_cagr_med'])} | {_p(q['d_mdd_med'])} |")
    Ls += ["", "## 必報（200 顆中位）", "",
           f"| 格 | {head}次數 | 占部位 | 停損距離 中位〔p10～p90〕 | 觸發根（引擎實際；進場日＝1）中位〔p10～p90〕 | 換掉時報酬 中位〔p10～p90〕 | 放棄組 抱到 120 根 平均／中位／續抱較好 |"
           " 補進那檔 vs 被停那檔續抱（中位；補較好占比） | 等待 中位／p90／當天補到 | 20 日內又買回（次／報酬中位） |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for k in rows:
        q = T.loc[k]
        Ls.append(f"| {q['名']} | {q['n_stop']:.0f} | {q['stop_frac_pos']:.3f} | {_p(q['dist0_med'], 1)}〔{_p(q['dist0_p10'], 1)}～{_p(q['dist0_p90'], 1)}〕 | "
                  f"{q['trig_bar_med']:.0f}〔{q['trig_bar_p10']:.0f}～{q['trig_bar_p90']:.0f}〕 | {_p(q['stop_ret_med'])}〔{_p(q['stop_ret_p10'])}～{_p(q['stop_ret_p90'])}〕 | "
                  f"{_p(q['stop_h120_mean'])}／{_p(q['stop_h120_med'])}／{q['stop_h120_better_frac']:.3f} | {_p(q['rep_ret_med'])} vs {_p(q['cont_ret_med'])}；{q['rep_better_frac']:.3f} | "
                  f"{q['nxw_med']:.1f}／{q['nxw_p90']:.1f}／{q['nxw_sameday_frac']:.3f} | {q['rebuy20_n']:.0f}／{_p(q['rebuy20_ret_med'])} |")
    Ls += ["", "| 格 | 周轉/年 | 成本/年 | 平均持股 | 現金比例 均值／中位 | 待買大小占 slot | 一般新部位／待買 | log 回落分型（單日／延續／混合） |", "|---|---|---|---|---|---|---|---|"]
    for k in ["base"] + rows:
        q = T.loc[k]
        Ls.append(f"| {q['名']} | {q['turnover_yr']:.2f} | {_p(q['cost_drag_yr'])} | {q['held_mean']:.2f} | {q['cash_mean']:.3f}／{q['cash_med']:.3f} | {q['nxsz_med']:.3f} | "
                  f"{q['normal_n']:.0f}／{q['nx_n']:.0f} | {q['ddlog_單日暴跌型']:.0f}／{q['ddlog_延續下跌型']:.0f}／{q['ddlog_混合型']:.0f} |")
    Ls += ["", "分年報酬（yYYYY 欄）、其餘 p10／p90 見 cells.csv。停損距離 ＝ 1 − 進場日收盤那條線 ÷ 進場價（引擎實際買到的部位）；時停的線只在第 d 根 ⇒ 不適用。"]
    return Ls


def desc_table(T, keys):
    Ls = ["", "## 描述臂（⛔ 不判、不計 N）", "", "| 臂 | 年化中位 | 回落中位 | 比值 | 對 0050 | 對營飆 v1 | 一般新部位／待買 | 現金比例均值 | 擋賣天次 |", "|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        q = T.loc[k]
        Ls.append(f"| {q['名']} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.4f} | {q['label']} | {q['vs_v1']} | {q['normal_n']:.0f}／{q['nx_n']:.0f} | "
                  f"{q['cash_mean']:.3f} | {q['sl_block_days']:.0f} |")
    return Ls


# ═════════════════════════════ 營飆停損
FAMS = ["P15", "T20", "A3", "M20", "M50", "F"]
SNAME = {"base": "營飆 v1 原樣", "P15": "P15 −15%", "T20": "T20 追蹤 −20%", "A3": "A3 3×ATR 追蹤", "M20": "M20 跌破 20 日線", "M50": "M50 跌破 50 日線", "F": "F 前低棘輪"}


def stop_arms(ctx):
    from . import tradability as T
    from . import yfstop_lines as Y
    sig, opens, closes = ctx["sig"], ctx["opens"], ctx["closes"]
    _G["ctx"] = ctx
    lines = {"P15": Y.p15_lines(sig, opens, closes), "T20": Y.t20_lines(sig, closes, valid_of), "A3": Y.a3_lines(sig, opens, closes, bars_of)[0],
             "M20": Y.ma_lines(sig, closes, bars_of, 20, arm="state"), "M50": Y.ma_lines(sig, closes, bars_of, 50, arm="state")}
    lines["F"], fk = Y.f_lines(sig, bars_of)
    BLK = T.build(set(sig["sid"]), ctx["cal"])
    A = {"base": ({}, "base")}
    for f in FAMS:
        A[f] = (Y.sim_kw(f, lines[f]), "判定")
    for f in FAMS:
        A["a_" + f] = ({k: v for k, v in A[f][0].items() if k != "stop_proceeds"}, "ⓐ整份")
    for f in FAMS:
        A["b_" + f] = ({**A[f][0], "stop_block": BLK}, "ⓑ跌停賣不掉")
    build = {f: len(lines[f]) for f in FAMS}
    build["F 起點種類"] = {k_: int(sum(1 for v in fk.values() if v == k_)) for k_ in sorted(set(fk.values()))}
    build["M arm"] = "state（另兩種 cross_sig、cross_entry 存在、本件不跑）"
    build["線 sha"] = {f: Y.lines_sha(lines[f]) for f in FAMS}
    return A, build


def stop_report(TB, S, OUT):
    T = TB.set_index("arm")
    ref = pd.read_csv(os.path.join(HERE, "resultsListExit", "cells.csv")).set_index("arm")
    good = [f for f in FAMS if T.loc[f, "vs_v1"] == "好"]
    Ls = ["# PREREG營飆停損：營飆 v1 加六族停損＋停損後補一檔（判定 6 格）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq1（sha bbd598d26c8f31d8）；裁定 seq200（附則 ⓓ 補股池另件、ⓔ 觸發根用引擎實際）。回測線。", "",
          f"閘：{S['閘']}｜建線：{S['建線']}", "", "## 結果句（⛔ 只照登錄 §五查表）", ""]
    for f in FAMS:
        q = T.loc[f]
        s = f"- **{SNAME[f]}**：對 0050「{q['label']}」（年化中位 {_p(q['cagr_med'])}、回落中位 {_p(q['mdd_med'])}）；對營飆 v1「{q['vs_v1']}」"
        qb = T.loc["b_" + f]
        if qb["label"].replace("（描述）", "") != q["label"] or qb["vs_v1"].replace("（描述）", "") != q["vs_v1"]:
            s += f"；⚠ 開盤跌停／停牌賣不掉版：對 0050「{qb['label'].replace('（描述）', '')}」、對營飆 v1「{qb['vs_v1'].replace('（描述）', '')}」"
        if q["label"] == "合格" and q["vs_v1"] == "好":
            s += f"。營飆 v1 加〔{SNAME[f]}〕＋停損後補一檔，在 2017～2026 這段比原本好；⚠ 事後挑的，要升 v2 須裁定定、並進 2012～2014 驗收段＋前瞻紀錄"
        else:
            s += "。營飆 v1 照原本：第 120 個交易日收盤賣、不停損"
        if good:
            s += f"。試了 6 種（加上次 2 種共 8 種），{len(good)} 種好，可能是運氣"
        Ls.append(s + f"。（{FOOT}）")
    Ls += ["", "參照列（⛔ 不重判；PREREG名單出場 乙 resultsListExit/cells.csv）："]
    for k in ("S1", "S2"):
        q = ref.loc[k]
        Ls.append(f"- {k}：年化中位 {_p(q['cagr_med'])}、回落中位 {_p(q['mdd_med'])}；對 0050「{q['label']}」；對營飆 v1「{q['vs_v1']}」")
    Ls += common_tables(T, FAMS, "停損")
    Ls += desc_table(T, [f"a_{f}" for f in FAMS] + [f"b_{f}" for f in FAMS])
    Ls += ["", "- ⓐ 整份 ＝ 只給 stop_line、不給 stop_proceeds：停損的錢併回一般現金、空槽照 min(equity/10, 現金) 開一般新部位（現金不足 equity/10 時只開得到現金那麼多；其餘與登錄字面等價）",
           "- ⓑ 跌停賣不掉 ＝ 加 stop_block（只擋停損賣出；其餘照營飆 v1 原樣）",
           "- ⓒ 排名補股：**排名沒有比抽籤好，補股照抽籤**（PREREG營飆排名 K1～K4 全分不出 ⇒ 登錄事前條件不成立、不跑）",
           "- ⓓ 補股池放寬：另件（seq200 ⓓ）",
           "- M20／M50 用 arm＝state（照登錄字面「收盤 ＜ 均線」當狀態；只影響 M20 21 列、M50 9 列）；另兩種 arm（cross_sig、cross_entry）已建好、本件不跑。", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Ls) + "\n")


# ═════════════════════════════ ⓓ 補股池放寬（A 6 格＋B 9 格；描述）
def pool_arms(ctx):
    from . import yfstop_lines as Y
    from . import researchYfTime as YT
    RR = ctx["RR"]; sig = ctx["sig"]
    P = Y.pool_rows(ctx)
    extra = sorted(set(P["sid"]) - set(ctx["closes"]))
    cz, oz = RR.load_prices(extra, ctx["cal"], ctx["mk"], "branch")
    miss = sorted(set(extra) - set(cz))
    if miss:
        raise SystemExit(f"⛔ 補股池有 {len(miss)} 檔讀不到價格：{miss[:5]}")
    ctx["closes"].update(cz); ctx["opens"].update(oz)
    _G["extra_sids"] = sorted(set(P["sid"]))                 # 有效 K 棒表要涵蓋池裡全部檔（含 AND 有價、但不在主窗 v1 訊號裡的）
    _G["xmap"].update({(s, int(e)): int(x) for s, e, x in zip(P["sid"], P["entry_pos"], P["xpos_H120"])})
    chk_sub = int(len(sig.merge(P[["sid", "entry_pos", "xpos_H120"]], on=["sid", "entry_pos", "xpos_H120"], how="inner")))
    opens, closes = ctx["opens"], ctx["closes"]
    L_ = {"P15": Y.p15_lines(P, opens, closes), "T20": Y.t20_lines(P, closes, valid_of), "A3": Y.a3_lines(P, opens, closes, bars_of)[0],
          "M20": Y.ma_lines(P, closes, bars_of, 20, arm="state"), "M50": Y.ma_lines(P, closes, bars_of, 50, arm="state"), "F": Y.f_lines(P, bars_of)[0]}
    pool = P[["sid", "entry_pos", "xpos_H120", "g_H120"]].copy()
    A = {"base": ({}, "base")}
    for f in FAMS:
        A["d_" + f] = ({**Y.sim_kw(f, L_[f]), "nx_pool": pool}, "ⓓ補股池")
    for k in YT.KINDS:
        for d in YT.DS:
            lines, _ = Y.time_lines(P, opens, closes, bars_of, k, d)
            A[f"d_{k}_{d}"] = ({**Y.time_kw(k, lines), "nx_pool": pool}, "ⓓ補股池")
    ent = P.groupby("entry_pos").size()
    w0, w1 = ctx["w0"], ctx["w1"]
    days = pd.Series(0, index=range(w0, w1 + 1)); days.loc[ent.index[(ent.index >= w0) & (ent.index <= w1)]] = ent[(ent.index >= w0) & (ent.index <= w1)]
    v1 = sig.groupby("entry_pos").size()
    build = {"池列（主窗、t−1 閘）": int(len(P)), "池列 xpos≥0": int((P["xpos_H120"] >= 0).sum()), "池檔數": int(P["sid"].nunique()),
             "補載價格檔數": len(extra), "v1 訊號列 ⊂ 池（同 sid／entry_pos／xpos）": f"{chk_sub}/{len(sig)}",
             "逐日池大小（窗內全部交易日）p10／中位／p90／均": [float(days.quantile(.1)), float(days.median()), float(days.quantile(.9)), round(float(days.mean()), 2)],
             "v1 有訊號日的池大小 中位": float(ent.reindex(v1.index).median()), "池有候選的日子": int((days > 0).sum())}
    return A, build


PNAME = {"base": "營飆 v1 原樣", **{f"d_{f}": f"ⓓ {SNAME[f]}" for f in FAMS}}


def pool_report(TB, S, OUT):
    from . import researchYfTime as YT
    T = TB.set_index("arm")
    st = pd.read_csv(os.path.join(OUT, "body_cells.csv")).set_index("arm")
    tm = pd.read_csv(os.path.join(HERE, "resultsYfTime", "cells.csv")).set_index("arm")
    Ls = ["# ⓓ 補股池放寬（營飆停損 6 格＋營飆時停 9 格；⛔ 描述、不判、不計 N）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq200 ⓓ；引擎 nx_pool。回測線。", "",
          f"閘：{S['閘']}", "", f"池：{S['建線']}", "",
          "| 格 | 年化中位 | 回落中位 | 比值 | 對 0050（描述） | 對營飆 v1（皆正／皆負） | 同格原版（v1 池補）年化／回落 | 待買買進（池） | 當天補到 | 等待 中位／p90 | 池當天沒得補的天次 | 現金比例 均值 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    rows = [f"d_{f}" for f in FAMS] + [f"d_{k}_{d}" for k in YT.KINDS for d in YT.DS]
    for k in rows:
        q = T.loc[k]; base = k[2:]
        o = st.loc[base] if base in st.index else tm.loc[base]
        nm = PNAME.get(k, "ⓓ " + YT.TNAME.get(base, base))
        Ls.append(f"| {nm} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.4f} | {q['label']} | {q['vs_v1']}（{q['vs_v1_both_pos']}／{q['vs_v1_both_neg']}） | "
                  f"{_p(o['cagr_med'])}／{_p(o['mdd_med'])} | {q['nx_pool_n']:.0f} | {q['nxw_sameday_frac']:.3f} | {q['nxw_med']:.1f}／{q['nxw_p90']:.1f} | "
                  f"{q['nx_pool_empty']:.0f} | {q['cash_mean']:.3f} |")
    Ls += ["", "- ⓓ ＝ 待買只從補股池挑（t−1 三條件、不去重的逐日池；池 ⊇ 營飆 v1 訊號），一般新部位仍只用營飆 v1 訊號；池那一抽在一般新部位那一抽之前、同顆種子 rng 接著抽",
           "- 「當天補到」＝ 待買在停損／換掉那天就買到的比例；「池當天沒得補的天次」＝ 有待買、有空槽、但池當天沒有未持有候選的天數",
           f"- {FOOT}", ""]
    open(os.path.join(OUT, "POOLD_REPORT.md"), "w", encoding="utf-8").write("\n".join(Ls) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=os.path.join(HERE, "resultsYfStop"))
    ap.add_argument("--pool", action="store_true", help="ⓓ 補股池放寬（A 6 格＋B 9 格；描述）")
    a = ap.parse_args()
    if a.pool:
        from . import researchYfTime as YT
        names = dict(PNAME); names.update({f"d_{c}": "ⓓ " + YT.TNAME[c] for c in YT.CELLS})
        run_study("ⓓ 補股池放寬（裁定 seq200 ⓓ；營飆停損 6 格＋營飆時停 9 格；描述）", "poolD", pool_arms, a.out, names, [], "—", a.reps, a.procs,
                  {"N帳": "⛔ 不計（描述臂）"}, pool_report)
        return
    names = dict(SNAME); names.update({f"a_{f}": f"ⓐ整份 {SNAME[f]}" for f in FAMS}); names.update({f"b_{f}": f"ⓑ跌停 {SNAME[f]}" for f in FAMS})
    run_study("PREREG營飆停損（登錄 seq1 sha bbd598d26c8f31d8；裁定 seq200）", "stop", stop_arms, a.out, names, FAMS, "6（加上次 2 種共 8 種）",
              a.reps, a.procs, {"ⓒ": "排名沒有比抽籤好，補股照抽籤", "N帳": {"N_組合": "+6", "不計": "S1、S2 參照列、ⓐⓑ、營飆 v1 原樣臂"}}, stop_report)


if __name__ == "__main__":
    main()

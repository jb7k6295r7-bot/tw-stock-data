# -*- coding: utf-8 -*-
"""裁定 seq395 (c)：seq6 X7 的事後重切描述版 X7b／X7c（回測線計算子代理，2026-10-20）。
⛔ 描述、事後重切、不計 N、不判、⛔ 不能升格成規則。看過 seq6 結果後的事後重切，只描述、不能當規則；要升格須另登錄、用沒看過的期間或前瞻驗。
⛔ 只計算：不 commit、不改既有程式與結果（researchExitGen.py、resultsExitGen/ 既有檔一字不動，import 重用）。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExitGen_x7b.py [--procs 4]
    查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExitGen_x7b_check.py

═══ 重用（⛔ 不另寫一份）═══
  researchExitGen（seq6）：setup（母體、段、可用日 avail_map、月營收 load_revenue）、ci_mean（進場月分群 CR0）、COST、SLIP、ZB、HJ
  researchQuad：stock_data、exec_day、_init
═══ 定義（寫死；其他完全照 seq6 X7）═══
  公布序列 ＝ 同 X7：有當月營收的期別、依可用日 A 排序；yoy ＝ 當月 ÷ 去年當月 − 1（去年當月 ＞ 0，否則不可算）
  Xk（k ＝ 連續為負的月數）：公布 i 成立 ⟺ yoy_i, …, yoy_{i−k+1} 全 ＜ 0 且 yoy_{i−k} ≥ 0，這 k＋1 個都可算
      （＝ 由正（≥0）轉負後的第 k 個連續負月；中間任一不可算 ⇒ 該串不判）
  X7 ＝ k＝1（＝ seq6 原版，程式對 researchExitGen.rev_turns 逐股全同）｜X7b ＝ k＝2｜X7c ＝ k＝3
  持有中 ＝ 成立的公布 A_i ∈ [e, x−1]（★ 串裡較早的負月可在進場前公布；只要第 k 個在持有中）；d ＝ A_i、s ＝ d 之後第一個可賣開盤（s ≥ x ⇒ 不做）
  其餘照 seq6：隨便買母體、H120 基準（c[lv(x)]/P0 − 1 − 0.585%）、純單筆賣後記 0、可用日 10／15 日、段（探索／確認／早年）、滑價 ±0.5%
輸出 backtest/resultsExitGen/x7b/：rows_{main,early}.csv.gz、cells.csv、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExitGen as G                                   # ⭐ seq6 本體（import 重用，⛔ 不改）

Q, D, RA, R11 = G.Q, G.D, G.RA, G.R11
HERE = G.HERE
OUT = os.path.join(G.OUT, "x7b")
H = G.HJ
COST, SLIP = G.COST, G.SLIP
KS = {"X7": 1, "X7b": 2, "X7c": 3}
KNAME = {"X7": "年增由正轉負（seq6 原版）", "X7b": "年增連 2 個月為負", "X7c": "年增連 3 個月為負"}
SEGS = {"main": ("explore", "confirm"), "early": ("early",)}
SEGNAME = {"explore": "探索 2017-03～2021", "confirm": "確認 2022～2026-09", "early": "早年 2005～2014（只上市）"}
MUST = "看過 seq6 結果後的事後重切，只描述、不能當規則；要升格須另登錄、用沒看過的期間或前瞻驗"
_W: dict = {}


def rev_events(sid, rev, rly, A):
    """同 G.rev_turns 的公布序列 ⇒ [(A, yoy)]（依可用日排序）。"""
    if rev is None or sid not in rev.columns:
        return []
    rv = rev[sid].to_numpy(float); rl = rly[sid].to_numpy(float); per = list(rev.index)
    ev = []
    for k, p in enumerate(per):
        if not np.isfinite(rv[k]) or p not in A:
            continue
        yoy = rv[k] / rl[k] - 1.0 if (np.isfinite(rl[k]) and rl[k] > 0) else np.nan
        ev.append((A[p], yoy))
    ev.sort(key=lambda z: z[0])
    return ev


def run_events(ev, k):
    """第 k 個連續負月（前面是 ≥0）的公布可用日陣列。"""
    out = []
    for i in range(k, len(ev)):
        w = [ev[j][1] for j in range(i - k, i + 1)]
        if all(np.isfinite(w)) and w[0] >= 0 and all(v < 0 for v in w[1:]):
            out.append(ev[i][0])
    return np.asarray(out, int)


def work(args):
    sid, market, es = args
    cal = Q._G["cal"]; n = len(cal)
    S = Q.stock_data(sid, market)
    if S is None:
        return [{"sid": sid, "market": market, "e": int(e), "st": "無資料"} for e in es], 0
    ev = rev_events(sid, _W["rev"], _W["rly"], _W["A"])
    trig = {X: run_events(ev, k) for X, k in KS.items()}
    t_orig, _ = G.rev_turns(sid, _W["rev"], _W["rly"], _W["A"])
    mism = int(not np.array_equal(t_orig, trig["X7"]))           # X7（k＝1）對 seq6 rev_turns 逐股全同
    o, c = S["o"], S["c"]
    out = []
    for e in es:
        e = int(e); x = e + H - 1
        r = {"sid": sid, "market": market, "e": e, "nrev": len(ev)}
        if x >= n:
            r["st"] = "超出日曆"; out.append(r); continue
        if not S["ok_buy"][e]:
            r["st"] = "進場日漲停或停牌"; out.append(r); continue
        if bool(G.AV.brk_vec(S["cs_pb"], S["cs_g5"], e, x)[0]):
            r["st"] = "硬斷點"; out.append(r); continue
        r["st"] = "保留"
        P0 = float(o[e]); j = int(S["lv"][x]); cj = float(c[j])
        base = cj / P0 - 1.0 - COST
        bsl = cj * (1 - SLIP) / (P0 * (1 + SLIP)) - 1.0 - COST
        r["base"] = base; r["bsl"] = bsl
        for X, tv in trig.items():
            w = tv[(tv >= e) & (tv < x)]
            d = int(w.min()) if len(w) else -1
            s = Q.exec_day(S, d, "sell", x) if d >= 0 else -1
            r[f"d{X}"] = d; r[f"s{X}"] = s; r[f"n{X}"] = int(len(w))
            if s >= 0:
                ret = float(o[s] / P0 - 1.0 - COST)
                r[f"r{X}"] = ret; r[f"D{X}"] = ret - base
                r[f"Dsl{X}"] = float(o[s] * (1 - SLIP) / (P0 * (1 + SLIP)) - 1.0 - COST) - bsl
            else:
                r[f"r{X}"] = np.nan; r[f"D{X}"] = 0.0; r[f"Dsl{X}"] = 0.0
        out.append(r)
    return out, mism


def _init(cal, off, b60, b200, rev, rly, A):
    Q._init(cal, off, b60, b200)
    _W.update(rev=rev, rly=rly, A=A)


def run_world(world, procs, log):
    Wd = G.setup(world, log)
    cal = Wd["cal"]; p = Wd["p"]
    off = RA.TR.load_official()
    b60 = R11.regime_below(Wd["c50ff"], 60)
    tasks = [(sid, Wd["mk"].get(sid, "twse"), sorted(g["e"].astype(int))) for sid, g in p.groupby("stock_id")]
    rows = []; mism = 0
    with Pool(procs, initializer=_init, initargs=(cal, off, b60, Wd["below200"], Wd["rev"], Wd["rly"], Wd["A"])) as pool:
        for r, m in pool.imap_unordered(work, tasks, chunksize=8):
            rows += r; mism += m
    K = pd.DataFrame(rows).sort_values(["sid", "e"]).reset_index(drop=True)
    K["mon"] = K["e"].map(lambda t: str(cal[t])[:7])
    K["seg"] = ""
    for sg, (a, b) in Wd["segs"].items():
        K.loc[(K["e"] >= a) & (K["e"] + H - 1 <= b), "seg"] = sg
    return K, Wd, mism


def reproduce(K, world):
    """seq6 rows_{world}（H120）對帳：保留狀態、base、X7 的 d／s／D／Dsl 逐筆。"""
    R = pd.read_csv(os.path.join(G.OUT, f"rows_{world}.csv.gz"), dtype={"sid": str},
                    usecols=["sid", "e", "status", "st120", "seg120", "mon", "base120", "bsl120", "dX7_120", "sX7_120", "DX7_120", "DslX7_120"])
    R["st120"] = np.where(R["status"] == "無資料", "無資料", R["st120"])
    M = K.merge(R, on=["sid", "e"], how="outer", indicator=True)
    both = M[M["_merge"] == "both"]
    keep = both["st"] == "保留"
    out = {"列不齊": int((M["_merge"] != "both").sum()), "狀態不同": int((both["st"].fillna("") != both["st120"].fillna("")).sum()),
           "段不同": int((both["seg"].fillna("") != both["seg120"].fillna("")).sum()), "月不同": int((both["mon_x"] != both["mon_y"]).sum())}
    kb = both[keep]
    out["保留筆數"] = int(len(kb))
    out["base 最大差"] = float(np.nanmax(np.abs(kb["base"] - kb["base120"]))) if len(kb) else 0.0
    out["bsl 最大差"] = float(np.nanmax(np.abs(kb["bsl"] - kb["bsl120"]))) if len(kb) else 0.0
    out["X7 d 不同"] = int((kb["dX7"] != kb["dX7_120"]).sum()); out["X7 s 不同"] = int((kb["sX7"] != kb["sX7_120"]).sum())
    out["X7 D 最大差"] = float(np.nanmax(np.abs(kb["DX7"] - kb["DX7_120"]))) if len(kb) else 0.0
    out["X7 Dsl 最大差"] = float(np.nanmax(np.abs(kb["DslX7"] - kb["DslX7_120"]))) if len(kb) else 0.0
    out["全同"] = bool(out["列不齊"] == 0 and out["狀態不同"] == 0 and out["段不同"] == 0 and out["月不同"] == 0 and out["X7 d 不同"] == 0
                     and out["X7 s 不同"] == 0 and max(out["base 最大差"], out["bsl 最大差"], out["X7 D 最大差"], out["X7 Dsl 最大差"]) < 1e-12)
    out["註"] = "浮點差 ≤1e−15 來自 pandas 讀 csv 的十進位解析（非 round-trip），容差 1e−12"
    return out


def cells(K, world, cal):
    rows = []
    for sg in SEGS[world]:
        k = K[(K["seg"] == sg) & (K["st"] == "保留")]
        mon = k["mon"].to_numpy(); e = k["e"].to_numpy(); base = k["base"].to_numpy(float)
        d7 = k["DX7"].to_numpy(float)
        for X in KS:
            d = k[f"D{X}"].to_numpy(float); s = k[f"s{X}"].to_numpy(); dd = k[f"d{X}"].to_numpy(); t = s >= 0
            c95 = G.ci_mean(d, mon); cB = G.ci_mean(d, mon, G.ZB)
            hold = np.where(t, s - e, H)
            r = {"world": world, "seg": sg, "exit": X, "mean": c95["mean"], "se": c95["se"], "lo95": c95["lo"], "hi95": c95["hi"],
                 "loB": cB["lo"], "hiB": cB["hi"], "n": c95["n"], "月數": c95["月數"], "n_eff": c95["n_eff"], "median": float(np.median(d)),
                 "trig_frac": float(t.mean()), "trig_n": int(t.sum()), "cond_no_sell": int(((dd >= 0) & ~t).sum()),
                 "trig_day_mean": float((dd[t] - e[t] + 1).mean()) if t.any() else np.nan,
                 "trig_day_median": float(np.median(dd[t] - e[t] + 1)) if t.any() else np.nan,
                 "hold_days_mean": float(hold.mean()), "cost_per_year": COST * 245 / float(hold.mean()),
                 "ret_trig_mean": float(k.loc[t, f"r{X}"].mean()) if t.any() else np.nan,
                 "abandon_base_mean": float(base[t].mean()) if t.any() else np.nan,
                 "hold_better_frac": float((d[t] < 0).mean()) if t.any() else np.nan,
                 "mean_trig_only": float(d[t].mean()) if t.any() else np.nan,
                 "slip_mean": float(k[f"Dsl{X}"].mean()), "base_mean": float(base.mean()),
                 "no_rev_frac": float((k["nrev"] == 0).mean())}
            for m_ in ("twse", "tpex"):
                sel = k["market"].to_numpy() == m_
                r[f"mean_{m_}"] = float(d[sel].mean()) if sel.any() else np.nan; r[f"n_{m_}"] = int(sel.sum())
            # 與 X7 的差（同一筆配對：D_X − D_X7）；X7 觸發而 X 沒觸發 等等的組成
            if X != "X7":
                cd = G.ci_mean(d - d7, mon)
                t7 = k["sX7"].to_numpy() >= 0
                r.update({"vsX7_mean": cd["mean"], "vsX7_lo95": cd["lo"], "vsX7_hi95": cd["hi"], "vsX7_se": cd["se"],
                          "P(X|X7)": float(t[t7].mean()) if t7.any() else np.nan, "P(X7|X)": float(t7[t].mean()) if t.any() else np.nan,
                          "X 觸發而 X7 沒觸發": int((t & ~t7).sum()),
                          "兩者都觸發時 X 晚幾根（平均）": float((dd[t & t7] - k["dX7"].to_numpy()[t & t7]).mean()) if (t & t7).any() else np.nan})
            rows.append(r)
    return pd.DataFrame(rows)


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}%"


def report(C, S):
    L = ["# seq395 (c)：X7 事後重切描述版——月營收年增連 2／3 個月為負（單筆層、H120）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq395 (c)；描述、⛔ 不計 N、⛔ 不判。回測線計算子代理。", "",
         f"**{MUST}。**", "",
         "定義（寫死）：公布序列同 seq6 X7（有當月營收的期別、依可用日排序）；第 i 次公布成立 ⟺ 本次起往回連 k 次年增 ＜ 0、再前一次 ≥ 0（都可算）；"
         "k＝1 即 X7、k＝2 即 X7b、k＝3 即 X7c；成立的公布可用日落在持有中（[e, x−1]）⇒ 隔天開盤全賣。其餘照 seq6。", "",
         "## 一、整體 d（H120；d ＝ 加出場 − 抱 120 天；賣後記 0；CI 進場月分群 CR0）", "",
         "| 段 | 出場 | d 平均 [95% CI] | [z＝3.12 帶，描述] | n／月數 | 觸發比例 | 平均觸發日（中位） | 平均持有 | 與 X7 差 [95% CI]（配對） | 滑價版 d |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for world, segs in SEGS.items():
        for sg in segs:
            for X in KS:
                r = C[(C.seg == sg) & (C.exit == X)].iloc[0]
                vs = "—" if X == "X7" else f"{_p(r['vsX7_mean'])} [{_p(r['vsX7_lo95'])}, {_p(r['vsX7_hi95'])}]"
                L.append(f"| {SEGNAME[sg]} | {X} {KNAME[X]} | {_p(r['mean'])} [{_p(r['lo95'])}, {_p(r['hi95'])}] | [{_p(r['loB'])}, {_p(r['hiB'])}] | "
                         f"{int(r['n']):,}／{int(r['月數'])} | {r['trig_frac']:.3f} | {r['trig_day_mean']:.1f}（{r['trig_day_median']:.0f}） | "
                         f"{r['hold_days_mean']:.1f} | {vs} | {_p(r['slip_mean'])} |")
    L += ["", "z＝3.12 帶 ＝ seq6 判定用的 Bonferroni 寬度，這裡只並列描述、⛔ 不判。", "",
          "## 二、組成（描述）", "",
          "| 段 | 出場 | 觸發時平均報酬 | 被賣的抱滿平均／抱著較好比例 | 只看觸發筆的 d | P(X｜X7 觸發) | X 觸發而 X7 沒觸發 | 兩者都觸發時晚幾根 | 上市／上櫃 d | 成本／年 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for world, segs in SEGS.items():
        for sg in segs:
            for X in KS:
                r = C[(C.seg == sg) & (C.exit == X)].iloc[0]
                ex = ("—", "—", "—") if X == "X7" else (f"{r['P(X|X7)']:.3f}", f"{int(r['X 觸發而 X7 沒觸發'])}", f"{r['兩者都觸發時 X 晚幾根（平均）']:.1f}")
                L.append(f"| {SEGNAME[sg]} | {X} | {_p(r['ret_trig_mean'])} | {_p(r['abandon_base_mean'])}／{r['hold_better_frac']:.3f} | {_p(r['mean_trig_only'])} | "
                         f"{ex[0]} | {ex[1]} | {ex[2]} | {_p(r['mean_twse'])}／{_p(r['mean_tpex'])} | {r['cost_per_year'] * 100:.2f}% |")
    L += ["", "## 三、對帳", ""]
    for world, q in S["X7 重現"].items():
        L.append(f"- {world}：{json.dumps(q, ensure_ascii=False)}")
    L.append(f"- X7（k＝1）觸發序列對 seq6 rev_turns 逐股不同：{S['X7 序列逐股不同']}")
    ck = os.path.join(OUT, "check.json")
    if os.path.exists(ck):
        cj = json.load(open(ck, encoding="utf-8"))
        L.append(f"- 抽 20 筆手算（_check.py）：{json.dumps(cj.get('摘要', {}), ensure_ascii=False)}")
    L += ["", "## 四、註", "",
          "- ★ 串裡較早的負月可以在進場前公布；只要「第 k 個連續負月」的可用日落在持有中就賣（買進時已連 ≥k 個月為負的，要等下一串）。",
          "- ★ 「連續」比的是有營收的前一次公布（同 X7），不另檢查期別是否相鄰；中間任一次年增不可算 ⇒ 該串不判。",
          f"- 必附：{MUST}；隨便買的平均，不是對某一檔的預測；單筆比較、沒算賣掉的錢再拿去做什麼。早年：{G.EARLY_NOTE}。", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.report_only:
        report(pd.read_csv(os.path.join(OUT, "cells.csv")), json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")))
        return
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchExitGen_x7b {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）procs {a.procs} =====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchExitGen_x7b.py", "researchExitGen.py", "researchQuad.py", "research34.py", "exit_signal.py")}
    log(f"[程式 sha256] {src}")
    S = {"裁定": "seq395 (c)：描述、事後重切、不計 N、不判、不能升格成規則", "必附": MUST, "程式": src, "定義": {X: f"連 {k} 個月年增 ＜0（前一次 ≥0）" for X, k in KS.items()},
         "X7 重現": {}, "X7 序列逐股不同": 0}
    Cs = []
    for world in ("main", "early"):
        t0 = time.time()
        K, Wd, mism = run_world(world, a.procs, log)
        S["X7 序列逐股不同"] += mism
        rep = reproduce(K, world)
        S["X7 重現"][world] = rep
        log(f"[{world}] {len(K):,} 列｜{time.time() - t0:.0f}s｜X7 序列逐股不同 {mism}｜重現 {rep}")
        K.to_csv(os.path.join(OUT, f"rows_{world}.csv.gz"), index=False, float_format="%.17g")
        Cs.append(cells(K, world, Wd["cal"]))
    C = pd.concat(Cs, ignore_index=True)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")
    # seq6 cells.csv 的 X7 H120 整體對帳
    C6 = pd.read_csv(os.path.join(G.OUT, "cells.csv"))
    mx = {}
    for _, r in C[C.exit == "X7"].iterrows():
        q = C6[(C6.world == r["world"]) & (C6.seg == r["seg"]) & (C6.H == H) & (C6.exit == "X7") & (C6.cut == "整體")].iloc[0]
        for col in ("mean", "se", "loB", "hiB", "trig_frac", "hold_days_mean", "slip_mean", "base_mean", "ret_trig_mean"):
            mx[col] = max(mx.get(col, 0.0), abs(float(r[col]) - float(q[col])))
        for col in ("n", "月數", "n_eff"):
            mx[col] = max(mx.get(col, 0.0), abs(float(r[col]) - float(q[col])))
    S["X7 對 seq6 cells.csv（H120 整體 3 段）最大差"] = mx
    log(f"[X7 cells 對帳] {mx}")
    S["寫檔時間（台北）"] = f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M:%S}"
    S["格"] = C.to_dict(orient="records")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(C, S)
    log(f"[完成] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

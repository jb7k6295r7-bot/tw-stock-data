# -*- coding: utf-8 -*-
"""⑩ PREREG訊號系統 事後重挑（裁定 seq262 §四 1、§六；稽核 seq3 §二 ⑩：K7 挑中出場 2022 後幾乎不觸發）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSigRe [--procs 2] [--reps 200] [--fake 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchSigRe_check.py

⭐ 標「事後重挑」：重挑取代原挑法（原件 researchSig a7d15bdc06 挑 E1 EVE、E2 EVE ＋ E1 EVE SL10 TP50h）；N 不加
═══ 退化排除（⭐ 看確認段前寫死；＝ researchSigMA 已用的那套，裁定 seq262 §四 1）═══
  探索段每格（E × 9 出場，停損停利 無／無）：
    「每檔平均出場觸發次數／年」＝ 每顆被【出場訊號】賣出的筆數 ÷ 10 檔 ÷ 段長（年，(段尾−段首) 日曆天 ÷ 365.25），200 顆平均
    「段尾未出場比例」＝ Σ段尾未出場 ÷ Σ部位（200 顆合併）
    觸發 ＜ 1 次／年 或 段尾未出場 ＞ 50% ⇒ 不進挑選；該 E 9 格全退化 ⇒ 該 E 依構造不可判定
  其餘照原件：挑法 ＝ researchSig.pick（合格取比值最高；都沒過取比值最高、同分年化高）；停損停利 16 組 ×（E1、E2 各用自己的新挑中出場）⇒ 32 選 1；
  確認段判定格；固定持有 20／60／120 對照；假訊號 A（同進場＋隨機出場）、B（同月同筆數隨機進場）各 --fake 次（原件 fake_arms 原樣）
⭐ 停止交易強制出場：開（research11.stop_force_days(valid_from_data(全部股票), 段尾)，每段各自）⇒ 探索段 9 出場也【在開的狀態下】重跑一次再做退化排除與挑
   另報：原件（強制出場關）探索段數字上的同一套退化排除結果（從 resultsSig/cells.csv 推：X 出場占比 × 已結清筆數）
   ⚠「出場訊號賣出」只算出場訊號（原因 X）的賣出，強制出場的賣出另計、⛔ 不算進觸發
單筆資料尾：本件無固定持有天數的排程出場（段尾按市值）⇒ t1_censor 不適用；固定持有對照照原件（段尾截在段尾次一日）
輸出 backtest/resultsSigRe/：cells.csv、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchSig as RS                                  # ⭐ 原件（a7d15bdc06），只 import
from backtest import listexit_lines as L
from backtest import rerun17 as RR
from backtest import research11 as R11

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsSigRe")
TAG = "停止交易強制出場：開"
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def run_one(args):
    """原件 run_one ＋ stop_force；另數「出場訊號賣出」筆數（排除強制出場那一筆）。"""
    key, r, s0, s1 = args
    sig, kw, reason, cf = RS._G["CELLS"][key]
    cz, oz, ncal, cal = RS._G["cz"], RS._G["oz"], RS._G["ncal"], RS._G["cal"]
    SF = RS._G["SF"][(s0, s1)]
    au = []
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, audit=au, stop_force=SF, **kw)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    res = RS.summarize(key, r, au, eq, hv, c_, m_, reason, cf, s0, s1)
    openb = {}; xtrig = 0; sfn = 0
    for a in au:
        s = a["sid"]; t = int(a["t"])
        if a["side"] == "buy":
            if a.get("kind") != "add":
                openb[s] = t
            continue
        if a.get("kind") == "trim":
            continue
        tb = openb.pop(s, None)
        if tb is None or t > s1:
            continue
        if SF.get(s) is not None and t == SF[s] + 1:
            sfn += 1; continue
        w_, dd = reason.get((s, tb), ("", -1))
        if w_ == "X" and dd >= 0 and t > dd:
            xtrig += 1
    res["xtrig"] = xtrig; res["sfn"] = sfn; res["years"] = (cal[s1] - cal[s0]).days / 365.25
    return res


def run_cells(keys, seg, reps, procs, tag):
    s0, s1 = RS._G["P"][seg]; t0 = time.time(); res = {k: [] for k in keys}
    with Pool(procs) as pool:
        for x in pool.imap_unordered(run_one, [(k, r, s0, s1) for k in keys for r in range(reps)], chunksize=2):
            res[x["key"]].append(x)
    log(f"  [{tag}] {len(keys)} 格 × {reps} 顆｜{time.time() - t0:.0f}s")
    return res


def agg(rows, bench):
    c = RS.agg(rows, bench)
    trades = sum(x["n"] for x in rows); endo = sum(x["endopen"] for x in rows)
    c["每檔出場觸發_次每年"] = float(np.mean([x["xtrig"] / 10 / x["years"] for x in rows]))
    c["段尾未出場比例"] = endo / max(1, trades)
    c["強制出場_每顆"] = float(np.mean([x["sfn"] for x in rows]))
    return c


def degen(c):
    return bool(c["每檔出場觸發_次每年"] < 1.0 or c["段尾未出場比例"] > 0.5)


def orig_degen(cal, P):
    """原件（強制出場關）探索段數字上的同一套排除（從 resultsSig/cells.csv 推）。"""
    T = pd.read_csv(os.path.join(HERE, "resultsSig", "cells.csv"))
    s0, s1 = P["探索"]; yrs = (cal[s1] - cal[s0]).days / 365.25
    out = {}
    for _, r in T[(T["段"] == "探索") & (T["停損"] == "無") & (T["停利"] == "無") & T["出場"].isin(RS.EXITS)].iterrows():
        why = json.loads(r["出場原因占比"]) if isinstance(r["出場原因占比"], str) else {}
        closed = r["交易筆_每顆平均"] - r["段尾未出場_每顆"]
        trig = why.get("X", 0.0) * closed / 10 / yrs
        endr = r["段尾未出場_每顆"] / r["交易筆_每顆平均"]
        out[f"{r['E']}_{r['出場']}"] = {"觸發_次每年": trig, "段尾未出場比例": endr, "排除": bool(trig < 1 or endr > 0.5),
                                      "比值": r["ratio"], "標籤": r["label"]}
    return out


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=1000)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("researchSig.py", "researchSigRe.py", "research11.py", "researchRev.py")}
    log(f"===== researchSigRe procs={a.procs} reps={a.reps} fake={a.fake} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜事後重挑｜{src} =====")
    D = RS.D
    cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in RS.SEG.items()}
    sids, elig, mk = RS.stock_universe(cal, RS.PANEL, os.path.join(RS.RV.H2.H2D, "meta", "stocks.csv"))
    SIG, VAL = pickle.load(open(os.path.join(HERE, "resultsSig", "sig_cache.pkl"), "rb"))
    RR.use_snapshot()
    allsid = sorted(SIG)
    cz, oz = RR.load_prices(allsid, cal, mk, "branch")
    BC = {}
    bars_of = lambda s: BC.setdefault(s, R11.load_bars(s, mk.get(s, "twse"), cal))
    valid_of = lambda s_: np.unpackbits(VAL[s_])[:ncal].astype(bool)
    bench = RR.load_bench(cal)
    B50 = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    valid = {s: valid_of(s) for s in allsid}
    SFS = {(s0, s1): R11.stop_force_days(valid, s1) for s0, s1 in P.values()}
    CELLS = {}
    RS._G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS, VAL=VAL, SF=SFS, P=P)
    S = {"性質": "事後重挑（裁定 seq262 §四 1；取代原挑法、N 不加）", "停止交易強制出場": "開", "程式": src,
         "停止交易股": {seg: len(SFS[P[seg]]) for seg in P}, "0050同段": B50}
    OD = orig_degen(cal, P); S["原件數字上的退化排除（強制出場關）"] = OD
    OUTC = {}; ROWS = {}
    # ── 探索段 9 出場（強制出場開）
    s0, s1 = P["探索"]
    for E in ("E1", "E2"):
        keys = []
        for xo in RS.EXITS:
            R, _, _ = RS.build_rows(SIG, elig, mon, E, xo, s0, s1); R = R.reset_index(drop=True)
            SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
            sig, kw, reason = RS.make_cell(R, SD, s1, "無", "無", cz, oz)
            k = ("探索", E, xo, "無", "無"); CELLS[k] = (sig, kw, reason, None); keys.append(k); ROWS[k] = R
        res = run_cells(keys, "探索", a.reps, a.procs, f"探索 {E} 9 出場")
        for k in keys:
            OUTC[k] = agg(res[k], B50["探索"])
    # ── 退化排除 ⇒ 挑（⛔ 確認段尚未算）
    excl = {}; chosen = {}
    for E in ("E1", "E2"):
        ok = []
        for xo in RS.EXITS:
            c = OUTC[("探索", E, xo, "無", "無")]
            excl[f"{E}_{xo}"] = {"觸發_次每年": c["每檔出場觸發_次每年"], "段尾未出場比例": c["段尾未出場比例"], "排除": degen(c), "比值": c["ratio"], "標籤": c["label"]}
            if not degen(c):
                ok.append((xo, c))
        chosen[E] = RS.pick(ok) if ok else None
    S["退化排除（強制出場開）"] = excl; S["探索段挑出場（事後重挑）"] = chosen
    S["原件挑出場"] = {"E1": "EVE", "E2": "EVE"}; S["原件停損停利"] = ["探索", "E1", "EVE", "SL10", "TP50h"]
    log(f"[退化排除] {json.dumps(excl, ensure_ascii=False)}\n[重挑出場] {chosen}")
    # ── 停損停利 16 組（探索）
    for E in ("E1", "E2"):
        xo = chosen[E]
        if xo is None:
            continue
        R = ROWS[("探索", E, xo, "無", "無")]
        SD = RS.stop_days(R, cz, oz, bars_of, s1, valid_of)
        cf = RS.cf_signal_exit(R, SD, cz, oz, s1)
        keys = []
        for sl in RS.SLS:
            for tp in RS.TPS:
                if sl == "無" and tp == "無":
                    continue
                sig, kw, reason = RS.make_cell(R, SD, s1, sl, tp, cz, oz)
                k = ("探索", E, xo, sl, tp); CELLS[k] = (sig, kw, reason, cf); keys.append(k)
        res = run_cells(keys, "探索", a.reps, a.procs, f"探索 {E} 停損停利 15 組")
        for k in keys:
            OUTC[k] = agg(res[k], B50["探索"])
    cands = [(k, OUTC[k]) for k in OUTC if k[0] == "探索" and chosen.get(k[1]) is not None and k[2] == chosen[k[1]]]
    chosen_st = RS.pick(cands) if cands else None
    S["探索段挑停損停利（事後重挑）"] = list(chosen_st) if chosen_st else None
    log(f"[重挑停損停利] {chosen_st}")
    S["探索段完成"] = time.strftime("%F %T")
    # ═══ 確認段（⛔ 上面挑完才算）
    s0, s1 = P["確認"]; keys = []; CR = {}
    for E in ("E1", "E2"):
        if chosen[E] is None:
            continue
        R, _, _ = RS.build_rows(SIG, elig, mon, E, chosen[E], s0, s1); R = R.reset_index(drop=True); CR[E] = R
        SD = RS.stop_days(R, cz, oz, bars_of, s1, valid_of)
        cf = RS.cf_signal_exit(R, SD, cz, oz, s1)
        sig, kw, reason = RS.make_cell(R, SD, s1, "無", "無", cz, oz)
        k = ("確認", E, chosen[E], "無", "無"); CELLS[k] = (sig, kw, reason, None); keys.append(k); ROWS[k] = R
        if chosen_st and chosen_st[1] == E and not (chosen_st[3] == "無" and chosen_st[4] == "無"):
            sig, kw, reason = RS.make_cell(R, SD, s1, chosen_st[3], chosen_st[4], cz, oz)
            k2 = ("確認", E, chosen[E], chosen_st[3], chosen_st[4]); CELLS[k2] = (sig, kw, reason, cf); keys.append(k2)
    res = run_cells(keys, "確認", a.reps, a.procs, "確認段 判定格")
    for k in keys:
        OUTC[k] = agg(res[k], B50["確認"])
    # 固定持有對照（確認段）
    keys = []
    for E in CR:
        R = CR[E]
        for H in (20, 60, 120):
            xp = np.minimum(R["entry_pos"].to_numpy(int) + H - 1, s1 + 1)
            sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": xp})
            sig["g_X"] = [float(cz[s_][x_]) / L.engine_ep(oz, cz, s_, e_) - 1.0 for s_, e_, x_ in zip(sig["sid"], sig["entry_pos"], xp)]
            reason = {(s_, int(e_)): (f"H{H}", -1) for s_, e_ in zip(sig["sid"], sig["entry_pos"])}
            k = ("確認", E, f"H{H}", "無", "無"); CELLS[k] = (sig, {}, reason, None); keys.append(k)
    res = run_cells(keys, "確認", a.reps, a.procs, "確認 固定持有對照")
    for k in keys:
        OUTC[k] = agg(res[k], B50["確認"])
    # 假訊號臂（原件 fake_arms 原樣；⚠ 原件 fake_one 不帶 stop_force ⇒ 照原件）
    FAKE = {}
    for E in CR:
        base = OUTC[("確認", E, chosen[E], "無", "無")]
        FAKE[E] = RS.fake_arms(E, CR[E], SIG, elig, mon, chosen[E], s0, s1, cz, oz, base, a, log)
    S["假訊號"] = FAKE
    rows = []
    for k, c in OUTC.items():
        rows.append({"段": k[0], "E": k[1], "出場": k[2], "停損": k[3], "停利": k[4],
                     **{kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in c.items() if not kk.startswith("_")}})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "cells.csv"), index=False)
    S["秒"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report()
    log(f"[完成] {time.time() - t00:.0f}s")


def _p(x):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    T = pd.read_csv(os.path.join(OUT, "cells.csv"))
    ch = S["探索段挑出場（事後重挑）"]; st = S["探索段挑停損停利（事後重挑）"]
    B = S["0050同段"]
    L_ = ["# ⑩ PREREG訊號系統 事後重挑（退化排除後重挑出場）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq262 §四 1；稽核 seq3 §二 ⑩。回測線。⭐ **{TAG}**；⭐ **事後重挑**（取代原挑法、N 不加）。", ""]
    conf = {}
    for E in ("E1", "E2"):
        if ch.get(E) is None:
            conf[E] = None; continue
        q = T[(T["段"] == "確認") & (T["E"] == E) & (T["出場"] == ch[E]) & (T["停損"] == "無") & (T["停利"] == "無")].iloc[0]
        conf[E] = q
    parts = []
    for E in ("E1", "E2"):
        if conf[E] is None:
            parts.append(f"{E} 9 格全退化 ⇒ 依構造不可判定")
        else:
            q = conf[E]; fk = S["假訊號"].get(E, {})
            parts.append(f"{E} 重挑〔{RS.XNAME.get(ch[E], ch[E])}〕確認段 {_p(q['cagr_med'])}／{_p(q['mdd_med'])} ⇒ {q['label']}（假訊號 B 隨機進場 p＝{fk.get('B_p（隨機 ≥ 本格）', float('nan')):.3f}）")
    L_.append("**結論：" + "；".join(parts) + f"（0050 確認段 {_p(B['確認']['cagr'])}／{_p(B['確認']['mdd'])}）。**")
    L_ += ["", "| E | 原件挑中 | 事後重挑 | 確認段 年化／回落 | 判定 | 每顆交易／段尾未出場 | 假訊號 A p／B p |", "|---|---|---|---|---|---|---|"]
    for E in ("E1", "E2"):
        q = conf[E]; fk = S["假訊號"].get(E, {})
        if q is None:
            L_.append(f"| {E} | 黃昏之星 | 全退化 | — | 依構造不可判定 | — | — |"); continue
        L_.append(f"| {E} | 黃昏之星 | {RS.XNAME.get(ch[E], ch[E])} | {_p(q['cagr_med'])}／{_p(q['mdd_med'])} | {q['label']} | {q['交易筆_每顆平均']:.1f}／{q['段尾未出場_每顆']:.1f} | "
                  f"{fk.get('A_p（隨機 ≥ 本格）', float('nan')):.3f}／{fk.get('B_p（隨機 ≥ 本格）', float('nan')):.3f} |")
    if st:
        q = T[(T["段"] == "確認") & (T["E"] == st[1]) & (T["出場"] == st[2]) & (T["停損"] == st[3]) & (T["停利"] == st[4])]
        if len(q):
            q = q.iloc[0]
            L_ += ["", f"- 停損停利（32 選 1，事後重挑）：{st[1]} {RS.XNAME.get(st[2], st[2])} {st[3]}／{st[4]} ⇒ 確認段 {_p(q['cagr_med'])}／{_p(q['mdd_med'])}（{q['label']}）"]
        else:
            L_ += ["", f"- 停損停利（32 選 1，事後重挑）：{st[1]} {st[2]} 無／無 ⇒ 與判定格相同"]
    L_ += ["", "## 退化排除（探索段、強制出場開；觸發 ＜ 1 次／年 或 段尾未出場 ＞ 50% ⇒ 不進挑選）", "",
           "| 格 | 觸發 次／年 | 段尾未出場比例 | 比值 | 標籤 | 排除 | 原件數字（強制出場關）觸發／段尾／排除 |", "|---|---|---|---|---|---|---|"]
    for k, v in S["退化排除（強制出場開）"].items():
        o = S["原件數字上的退化排除（強制出場關）"].get(k, {})
        L_.append(f"| {k} | {v['觸發_次每年']:.2f} | {v['段尾未出場比例']:.3f} | {v['比值']:.3f} | {v['標籤']} | {'⛔ 排除' if v['排除'] else '—'} | "
                  f"{o.get('觸發_次每年', float('nan')):.2f}／{o.get('段尾未出場比例', float('nan')):.3f}／{'排除' if o.get('排除') else '—'} |")
    L_ += ["", "## 確認段固定持有對照", ""]
    for E in ("E1", "E2"):
        r = T[(T["段"] == "確認") & (T["E"] == E) & T["出場"].isin(["H20", "H60", "H120"])]
        if len(r):
            L_.append(f"- {E}：" + "；".join(f"{x['出場']} {_p(x['cagr_med'])}／{_p(x['mdd_med'])}（{x['label']}）" for _, x in r.iterrows()))
    L_ += ["", "## 讀法", "",
           "- 退化排除的量與門檻 ＝ researchSigMA（seq252 已用）；⭐ 在跑確認段之前寫死；探索段 9 出場在強制出場開下重跑後才做排除與挑",
           "- 「出場訊號賣出」只算原因 X 的賣出；強制出場那一筆另計", "- 假訊號臂照原件 fake_arms（原件不帶強制出場 ⇒ 照原件）",
           f"- 停止交易股（全部股票、各段）：{S['停止交易股']}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    else:
        main()

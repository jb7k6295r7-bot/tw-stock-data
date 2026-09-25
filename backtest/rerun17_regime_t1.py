# -*- coding: utf-8 -*-
"""裁定線 seq183 ①：候選 17 格裡 regime＝True 的 5 格（#1、#4、#7、#16、#17）改用 t−1（訊號日收盤）判大盤閘，重跑主窗。

原件 research13.py：regime_ok = 0050 還原收盤 > 200MA；pools = pool[regime_ok[entry_pos]]
  ⇒ 判閘用【進場日】收盤，但進場在進場日開盤 ⇒ 日內前視。
本支：只把判閘位置從 entry_pos 改成 entry_pos − 1（＝進場前最後一個已知收盤）；判準、N、規則、種子、主窗讀法一字不動。

⛔ 不改任何既有 .py；全部呼叫 backtest/rerun17.py 的函式（use_snapshot／win_bounds／load_bench／bench_row／setup_and／run_cells／sig_for），
   標籤用 backtest/rerun17_table.label。rerun17.sig_for 以 _G["regime"][entry_pos] 篩選 ⇒ 本支把 _G["regime"] 換成
   右移一格的遮罩 reg_t1[t] ＝ reg[t − 1]（reg_t1[0] ＝ False），使 sig_for 取到的恰是 reg[entry_pos − 1]；
   另外逐列斷言這個等式，並用顯式索引 reg[entry_pos − 1] 重選一次訊號、比對列集合相同。

閘門（先過才跑 t−1）：
  閘一 0050 主窗錨逐位元（年化 0.24020209886370614、回落 −0.3395700527611012）
  閘二 用原件 entry_pos 判閘重跑 5 格 ⇒ 200 顆的 cagr／mdd（另比 vol／first／end／trades／eq_sha）與
       resultsN17/rerun17_seeds.csv 的 main 階段逐位元相同；不同就停。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.rerun17_regime_t1 [--procs 2]
輸出 backtest/resultsN17/regime_t1/：seeds.csv、cells.csv、all17.csv、flips.csv、meta.json、run.log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

from . import data as D
from . import rerun17 as RR
from . import rerun17_table as RT

OUT = os.path.join(RR.OUT, "regime_t1")
REG_CELLS = [1, 4, 7, 16, 17]
RTP = dict(float_precision="round_trip")
CMP_COLS = ["cagr", "mdd", "vol", "first", "end", "trades", "eq_sha"]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--reps", type=int, default=RR.REPS)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== rerun17_regime_t1 procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    for cid in REG_CELLS:
        sp = RR.CELLS[cid - 1][4]
        if not (sp["fam"] == "P10" and sp["reg"] is True):
            raise SystemExit(f"⛔ 格{cid} 不是 PREREG10 regime=True：{RR.CELLS[cid - 1]}")
    others = [c[0] for c in RR.CELLS if c[4]["fam"] == "P10" and c[4].get("reg") is True and c[0] not in REG_CELLS]
    if others:
        raise SystemExit(f"⛔ 17 格裡還有 regime=True 的格沒列：{others}")
    src = {f: _sha(os.path.join(RR.HERE, f)) for f in ("rerun17.py", "rerun17_table.py", "research11.py", "research13.py", "data.py")}
    log(f"[程式 sha256] {json.dumps({k: v[:16] for k, v in src.items()}, ensure_ascii=False)}")

    RR.use_snapshot()
    log(f"[資料] D.DATA ＝ {D.DATA}")
    cal = D.load_calendar()
    w0, w1 = RR.win_bounds(cal)
    bench = RR.load_bench(cal)
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    g1 = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    log(f"[閘一 0050 錨] 年化 {bw['cagr']!r}／回落 {bw['mdd']!r}｜錨 {RR.ANCHOR}｜逐位元 {g1}")
    if not g1:
        raise SystemExit("⛔ 閘一不過，停")
    b_c, b_m, b_v = bw["cagr"], bw["mdd"], bw["vol"]

    and_path = os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz")
    RR.setup_and(cal, and_path, "branch", log)
    G = RR._G
    reg = G["regime"].copy()                       # 原件：reg[t] ＝ 0050 收盤[t] > MA200[t]
    reg_t1 = np.zeros_like(reg); reg_t1[1:] = reg[:-1]   # reg_t1[t] ＝ reg[t − 1]
    AND = G["AND"]
    e = AND["entry_pos"].to_numpy()
    if e.min() < 1 or not np.array_equal(reg_t1[e], reg[e - 1]):
        raise SystemExit("⛔ reg_t1[entry_pos] ≠ reg[entry_pos − 1]")

    # ── 進出訊號筆數（原判開、t−1 判關，與反之）──
    o_on, t_on = reg[e], reg[e - 1]
    inwin = (e >= w0) & (e <= w1)
    pos = AND["pos"].to_numpy()
    fl = AND.assign(entry_date=[str(cal[i].date()) for i in e], sig_close_date=[str(cal[i - 1].date()) for i in e],
                    pos_eq_entry_m1=(pos == e - 1), reg_entry=o_on, reg_t1=t_on, in_main_win=inwin)
    flips = fl[o_on != t_on].copy()
    flips["dir"] = np.where(flips["reg_entry"], "原開→t−1關", "原關→t−1開")
    flips[["sid", "pos", "entry_pos", "entry_date", "sig_close_date", "pos_eq_entry_m1", "dir", "in_main_win"]].to_csv(
        os.path.join(OUT, "flips.csv"), index=False)
    cnt = {
        "AND_all": int(len(AND)), "AND_win": int(inwin.sum()),
        "orig_on_win": int((o_on & inwin).sum()), "t1_on_win": int((t_on & inwin).sum()),
        "out_win": int((o_on & ~t_on & inwin).sum()), "in_win": int((~o_on & t_on & inwin).sum()),
        "out_all": int((o_on & ~t_on).sum()), "in_all": int((~o_on & t_on).sum()),
        "pos_ne_entry_m1": int((pos != e - 1).sum()),
        "pos_ne_entry_m1_win": int(((pos != e - 1) & inwin).sum()),
        "pos_ne_entry_m1_gate_differs_win": int(((pos != e - 1) & (reg[pos] != reg[e - 1]) & inwin).sum()),
        "regime_flip_days_win": int((reg[w0:w1 + 1] != reg[w0 - 1:w1]).sum()),
    }
    log(f"[進出] {cnt}")

    # ── 閘二：原件 entry_pos 判閘 ⇒ 對 rerun17_seeds.csv main ──
    G["regime"] = reg
    t0 = time.time()
    d0 = RR.run_cells("win", a.procs, a.reps, REG_CELLS, log)
    d0.insert(0, "stage", "orig_entry")
    ref = pd.read_csv(os.path.join(RR.OUT, "rerun17_seeds.csv"), dtype={"eq_sha": str}, **RTP)
    ref = ref[(ref["stage"] == "main") & ref["cell"].isin(REG_CELLS)]
    m = d0.merge(ref, on=["cell", "r"], suffixes=("", "_ref"), how="outer", indicator=True)
    bad = {}
    for c in CMP_COLS:
        x, y = m[c], m[c + "_ref"]
        if c in ("cagr", "mdd", "vol"):
            ne = [repr(float(p)) != repr(float(q)) for p, q in zip(x, y)]
        elif c == "eq_sha":
            ne = [str(p) != str(q) for p, q in zip(x, y)]
        else:
            ne = [int(p) != int(q) for p, q in zip(x, y)]
        bad[c] = int(sum(ne))
    g2 = bool((m["_merge"] == "both").all()) and len(m) == len(REG_CELLS) * a.reps and all(v == 0 for v in bad.values())
    log(f"[閘二 原件判閘重跑 vs rerun17_seeds main] 列 {len(m)}（應 {len(REG_CELLS) * a.reps}）｜不同數 {bad}｜逐位元 {g2}｜{time.time() - t0:.0f}s")
    if not g2:
        d0.to_csv(os.path.join(OUT, "seeds_gatefail.csv"), index=False)
        raise SystemExit("⛔ 閘二不過，停（不跑 t−1）")

    # ── t−1 版 ──
    G["regime"] = reg_t1
    for cid in REG_CELLS:           # 顯式索引重選一次，與 sig_for 取到的列集合比對
        sp = RR.CELLS[cid - 1][4]
        s1 = RR.sig_for(sp, "win")
        s2 = AND[reg[e - 1] & inwin]
        if not s1.index.equals(s2.index):
            raise SystemExit(f"⛔ 格{cid}：sig_for（右移遮罩）與顯式 reg[entry_pos−1] 選到的訊號不同")
    t0 = time.time()
    d1 = RR.run_cells("win", a.procs, a.reps, REG_CELLS, log)
    d1.insert(0, "stage", "t1")
    log(f"[t−1] 完成 {time.time() - t0:.0f}s")
    seeds = pd.concat([d0, d1], ignore_index=True)
    seeds.to_csv(os.path.join(OUT, "seeds.csv"), index=False)

    # ── 彙總 ──
    r17 = pd.read_csv(os.path.join(RR.OUT, "rerun17.csv"), **RTP)
    rows = []
    for cid in REG_CELLS:
        _, tier, fam, cell, sp = RR.CELLS[cid - 1]
        g = d1[d1["cell"] == cid]
        c, mm, v = float(g["cagr"].median()), float(g["mdd"].median()), float(g["vol"].median())
        lab, ratio, extra = RT.label(c, mm, b_c, b_m)
        o = r17[r17["編號"] == cid].iloc[0]
        g0 = d0[d0["cell"] == cid]
        oc, om = float(g0["cagr"].median()), float(g0["mdd"].median())
        if repr(oc) != repr(float(o["主窗_年化"])) or repr(om) != repr(float(o["主窗_回落"])):
            raise SystemExit(f"⛔ 格{cid} 原件判閘中位與 rerun17.csv 不同")
        oex = o["主窗_深淺註"] if isinstance(o["主窗_深淺註"], str) else ""
        rows.append({"編號": cid, "層": tier, "族": fam, "格": cell, "N": sp["N"], "rule": sp["rule"],
                     "t1_年化": c, "t1_回落": mm, "t1_比值": ratio, "t1_年化波動": v, "t1_年化÷波動": c / v,
                     "t1_標籤": lab, "t1_深淺註": extra, "t1_條件一": c > b_c, "t1_條件二": ratio >= b_c / abs(b_m),
                     "t1_年化差pp": (c - b_c) * 100, "t1_回落差pp（負＝比0050深）": (mm - b_m) * 100,
                     "t1_trades中位": float(g["trades"].median()), "t1_first": f"{int(g['first'].min())}～{int(g['first'].max())}",
                     "原_年化（含日內前視）": o["主窗_年化"], "原_回落（含日內前視）": o["主窗_回落"], "原_比值（含日內前視）": o["主窗_比值"],
                     "原_年化波動（含日內前視）": o["主窗_年化波動"], "原_年化÷波動（含日內前視）": o["主窗_年化÷波動"],
                     "原_標籤（含日內前視）": o["主窗_標籤"], "原_深淺註（含日內前視）": oex,
                     "原_trades中位": float(g0["trades"].median()),
                     "差_年化pp": (c - o["主窗_年化"]) * 100, "差_回落pp": (mm - o["主窗_回落"]) * 100,
                     "標籤變動": "無" if lab == o["主窗_標籤"] else f"{o['主窗_標籤']} → {lab}",
                     "訊號_窗內AND": cnt["AND_win"], "訊號_原判開": cnt["orig_on_win"], "訊號_t1判開": cnt["t1_on_win"],
                     "訊號_原開t1關": cnt["out_win"], "訊號_原關t1開": cnt["in_win"], "種子數": len(g),
                     "錨_年化": b_c, "錨_回落": b_m, "錨_比值": b_c / abs(b_m), "錨_年化波動": b_v, "錨_年化÷波動": b_c / b_v, "錨_逐位元": g1})
    C = pd.DataFrame(rows)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False)

    # ── 17 格（t−1 後）：5 格換 t−1、其餘照 rerun17.csv main ──
    A = []
    for cid, tier, fam, cell, sp in RR.CELLS:
        o = r17[r17["編號"] == cid].iloc[0]
        if cid in REG_CELLS:
            q = C[C["編號"] == cid].iloc[0]
            c, mm, ratio, lab, srcn = q["t1_年化"], q["t1_回落"], q["t1_比值"], q["t1_標籤"], "t1"
        else:
            c, mm, ratio, lab, srcn = o["主窗_年化"], o["主窗_回落"], o["主窗_比值"], o["主窗_標籤"], "rerun17.csv main"
        n = sp.get("N", RR.P12_N)
        A.append({"編號": cid, "族": fam, "格": cell, "N": n, "混0050": fam in ("P14", "P17"), "年化": c, "回落": mm, "比值": ratio,
                  "標籤": lab, "出處": srcn, "N在8～10": bool(8 <= n <= 10)})
    A = pd.DataFrame(A).sort_values("比值", ascending=False)
    A.to_csv(os.path.join(OUT, "all17.csv"), index=False)
    c1 = C[C["編號"] == 1].iloc[0]
    alt = A[A["N在8～10"]].iloc[0]
    alt_pure = A[A["N在8～10"] & ~A["混0050"]].iloc[0]
    meta = {"bench_win": bw, "gate1": g1, "gate2": g2, "gate2_diff": bad, "counts": cnt, "src_sha256": src,
            "cell1_t1_label": c1["t1_標籤"], "cell1_drops": bool(c1["t1_標籤"] != "合格"),
            "alt_top_N8_10": {"編號": int(alt["編號"]), "格": alt["格"], "比值": float(alt["比值"]), "標籤": alt["標籤"]},
            "alt_top_N8_10_no_mix": {"編號": int(alt_pure["編號"]), "格": alt_pure["格"], "比值": float(alt_pure["比值"]), "標籤": alt_pure["標籤"]}}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        log(C[["編號", "格", "t1_年化", "t1_回落", "t1_比值", "t1_年化波動", "t1_年化÷波動", "t1_標籤", "t1_深淺註",
               "原_年化（含日內前視）", "原_回落（含日內前視）", "原_比值（含日內前視）", "原_標籤（含日內前視）", "標籤變動"]].to_string(index=False))
        log(A.to_string(index=False))
    log(f"[#1] t−1 標籤 {c1['t1_標籤']}｜掉出合格 {meta['cell1_drops']}｜8～10 檔比值最高 {meta['alt_top_N8_10']}｜不含混 0050 {meta['alt_top_N8_10_no_mix']}")
    log(f"[完成] seeds.csv {len(seeds):,} 列")


if __name__ == "__main__":
    main()

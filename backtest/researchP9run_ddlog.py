# -*- coding: utf-8 -*-
"""PREREGP9 12 格報告：回落分型【log 口徑版】（主）＋ simple 版並列（副）（回測線計算助手，2026-09-25）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchP9run_ddlog [--procs 2]

依據：裁定線 seq174 §二（逐字）「登錄方 seq5 的分型用 log 報酬、引擎用 simple ⇒ 0050 的 2022、2025-01 兩次會換型；
      回落深度與 12 格標籤兩種口徑相同 ⇒ 標籤不受影響；受影響的只有分型描述 ⇒ 回測線：補一版照登錄的 log 口徑分型（主），
      simple 版並列（副）」
⛔ 本檔只 import researchP9run／researchp9／rerun17／p9_flags／p4_features，⛔ 不改任何既有檔；
⛔ 12 格標籤（年化、回落、比值、合格／另列／不合格）不重報、不重判；年化／回落只拿來驗決定性。

三處（researchP9run.py 內呼叫 dd_type 預設 simple 的地方）：
  ① measure() 每格每顆種子的分型計數 d["dd_{型}"]  ⇒ 重跑 14 臂 × 200 顆取 equity，dd_events 同一式，分型 log／simple 各算一次
  ② §四④ 0050 自己的回落事件（bq ＝ bench／bench[w0]，事件窗 [w0, w1]）
  ③ §四⑤ 基準臂中位種子（回落最接近 200 顆中位者，同一選法）的事件逐筆（events.csv）
log 口徑 ＝ researchp9.dd_type(scale="log")（策略線 ddtype.py 口徑：peak→trough 的逐日 log 報酬、總跌幅也用 log）；門檻不變
  （最差 2 日占比 ≥ 50% ⇒ 單日暴跌型；否則最差 5 日占比 < 50% ⇒ 延續下跌型；其餘混合型）。
⭐ 事件的切法（dd_events：≥ 20% 跌幅、高點／谷底／回升）兩種口徑相同 ⇒ 事件數不變，只有型別可能換。

查核：
  決定性  重跑的每顆種子 年化／回落／波動 repr 與 eq_sha 必須與 resultsP9run/seeds_arms.csv 逐位元同；
          各格年化中位、回落中位亦須與 seeds_arms.csv、cells.csv 逐位元同 ⇒ 不同就停
  simple 重算  ① 每顆種子 dd_* 三欄＋dd_n 與 seeds_arms.csv 逐筆同、各格中位與 cells.csv 同；
               ② 0050 事件的 simple 分型與 summary.json §四④（＝ 報告 §八表）逐筆同；
               ③ 中位種子事件的 simple 分型、最差2日占比與 events.csv 逐筆同
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

from . import researchP9run as P
from . import researchp9 as P9
from . import rerun17 as RR
from . import p9_flags as F

KINDS = ("單日暴跌型", "延續下跌型", "混合型")
OUTS = ("ddtype_log.csv", "ddtype_log_0050.csv", "ddtype_log_events.csv", "DDTYPE_LOG.md")


def _types(eq, ev):
    out = []
    for e_ in ev:
        ks, s2, s5 = P9.dd_type(eq, e_["peak"], e_["trough"])
        kl, l2, l5 = P9.dd_type(eq, e_["peak"], e_["trough"], scale="log")
        out.append((e_, ks, s2, s5, kl, l2, l5))
    return out


def _seed(args):
    key, r = args
    G = P._G
    au = [] if key in P.EBAR_CELLS else None          # 與 researchP9run._arm 同一呼叫
    o = P.sim(P.engine_kw(key), P.SEED0 + r, audit=au)
    eq = o["equity"]
    c, m, v = RR.win_metrics(eq, o["first"], o["end"], G["w0"], G["w1"])
    ev = P9.dd_events(eq, G["w0"], G["w1"] + 1)
    row = {"arm": key, "r": r, "seed": P.SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": float(v), "eq_sha": P.sha(eq),
           "dd_n": len(ev)}
    for k in KINDS:
        row[f"s_{k}"] = 0
        row[f"l_{k}"] = 0
    sw = []
    for e_, ks, s2, s5, kl, l2, l5 in _types(eq, ev):
        row[f"s_{ks}"] += 1
        row[f"l_{kl}"] += 1
        if ks != kl:
            sw.append((ks, kl))
    row["switch"] = sw
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    OUT = P.OUT
    T0 = time.time()

    def log(x):
        print(f"[{time.time() - T0:6.0f}s] {x}", flush=True)

    log(f"===== researchP9run_ddlog {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    P.setup(log)
    G = P._G
    cal, w0, w1, bench = G["cal"], G["w0"], G["w1"], G["bench"]
    # 閘一（同 researchP9run）
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    if not (repr(bw["cagr"]) == repr(P.ANCHOR[0]) and repr(bw["mdd"]) == repr(P.ANCHOR[1])):
        raise SystemExit("⛔ 0050 錨不同")
    # ⓑ 旗標（同 researchP9run：先驗 panel_ext sha）
    h = hashlib.sha256(open(P.PANEL_EXT, "rb").read()).hexdigest()
    if h != P.PANEL_EXT_SHA:
        raise SystemExit("⛔ panel_ext sha 不同")
    from . import p4_features as P4F
    pext = P4F.read_panel(P.PANEL_EXT)
    G["flags"] = F.build_flags(pext, cal, sids=set(G["sig"]["sid"]))
    del pext
    log("[設定] 0050 錨、panel_ext sha 過；ⓑ 旗標已建")

    # ═════ ① 14 臂 × 200 顆 ═════
    jobs = [(k, r) for k in P.KEYS for r in range(P.REPS)]
    with Pool(a.procs) as pool:
        rows = pool.map(_seed, jobs, chunksize=10)
    X = pd.DataFrame(rows)
    log(f"[①] 重跑 {len(X):,} 條路徑")

    ref = pd.read_csv(os.path.join(OUT, "seeds_arms.csv"), float_precision="round_trip")
    cells = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip").set_index("arm")
    ref = ref.set_index(["arm", "r"]).sort_index()
    Xi = X.set_index(["arm", "r"]).sort_index()
    if not ref.index.equals(Xi.index):
        raise SystemExit("⛔ (arm, r) 索引與 seeds_arms.csv 不同")
    det = {k: bool(all(repr(x) == repr(y) for x, y in zip(Xi[k], ref[k]))) for k in ("cagr", "mdd", "vol")}
    det["eq_sha"] = bool((Xi["eq_sha"] == ref["eq_sha"]).all())
    det["seed"] = bool((Xi["seed"].to_numpy() == ref["seed"].to_numpy()).all())
    med_same = {}
    for k in P.KEYS:
        g = Xi.loc[k]
        gr = ref.loc[k]
        med_same[k] = (repr(float(g["cagr"].median())) == repr(float(gr["cagr"].median())) == repr(float(cells.loc[k, "cagr"]))
                       and repr(float(g["mdd"].median())) == repr(float(gr["mdd"].median())) == repr(float(cells.loc[k, "mdd"])))
    det["各格年化中位、回落中位（對 seeds_arms 與 cells.csv）"] = all(med_same.values())
    log(f"[決定性] {det}")
    if not all(det.values()):
        bad = [k for k, v in med_same.items() if not v]
        raise SystemExit(f"⛔ 決定性不過：{det}；中位不同的格 {bad}")

    chk1 = {"dd_n": bool((Xi["dd_n"].to_numpy() == ref["dd_n"].to_numpy()).all())}
    for k in KINDS:
        chk1[f"dd_{k}"] = bool((Xi[f"s_{k}"].to_numpy() == ref[f"dd_{k}"].to_numpy()).all())
    cell_med_ok = {}
    for arm in P.KEYS:
        g = Xi.loc[arm]
        cell_med_ok[arm] = all(float(g[f"s_{k}"].median()) == float(cells.loc[arm, f"dd_{k}"]) for k in KINDS) \
            and float(g["dd_n"].median()) == float(cells.loc[arm, "dd_n"])
    chk1["各格中位＝cells.csv"] = all(cell_med_ok.values())
    log(f"[查核①] simple 重算 vs seeds_arms.csv／cells.csv：{chk1}")

    T = []
    for arm in P.KEYS:
        g = Xi.loc[arm]
        row = {"arm": arm, "族": P.FAM[arm], "格": P.NAME[arm], "種子數": len(g), "事件數_中位": float(g["dd_n"].median()),
               "事件數_合計": int(g["dd_n"].sum())}
        for k in KINDS:
            row[f"log_{k}_中位"] = float(g[f"l_{k}"].median())
            row[f"log_{k}_合計"] = int(g[f"l_{k}"].sum())
        for k in KINDS:
            row[f"simple_{k}_中位"] = float(g[f"s_{k}"].median())
            row[f"simple_{k}_合計"] = int(g[f"s_{k}"].sum())
        for k in KINDS:
            row[f"差_{k}_中位（log−simple）"] = row[f"log_{k}_中位"] - row[f"simple_{k}_中位"]
            row[f"差_{k}_合計（log−simple）"] = row[f"log_{k}_合計"] - row[f"simple_{k}_合計"]
        sw = [s for L in g["switch"] for s in L]
        row["換型事件數"] = len(sw)
        row["換型事件占比"] = len(sw) / row["事件數_合計"] if row["事件數_合計"] else np.nan
        for a_ in KINDS:
            for b_ in KINDS:
                if a_ != b_:
                    row[f"換型_{a_}→{b_}"] = sum(1 for s in sw if s == (a_, b_))
        row["計數有變的種子數"] = int(sum(any(g.iloc[i][f"l_{k}"] != g.iloc[i][f"s_{k}"] for k in KINDS) for i in range(len(g))))
        T.append(row)
    TB = pd.DataFrame(T)

    # ═════ ② 0050 事件 ═════
    bq = bench / bench[w0]
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    rep50 = S["§四④"]["60"]["0050事件"]
    R50 = []
    for e_, ks, s2, s5, kl, l2, l5 in _types(bq, P9.dd_events(bq, w0, w1 + 1)):
        R50.append({"高點": str(cal[e_["peak"]].date()), "谷底": str(cal[e_["trough"]].date()), "回升": str(cal[e_["recover"]].date()),
                    "回升了": e_["recovered"], "跌幅_simple": e_["dd"], "跌幅_log": float(np.log(bq[e_["trough"]] / bq[e_["peak"]])),
                    "分型_log（主）": kl, "最差2日占比_log": l2, "最差5日占比_log": l5,
                    "分型_simple（副）": ks, "最差2日占比_simple": s2, "最差5日占比_simple": s5, "換型": ks != kl})
    E50 = pd.DataFrame(R50)
    chk2 = {"事件數": len(E50) == len(rep50),
            "逐筆（高點、谷底、跌幅、分型）": len(E50) == len(rep50) and all(
                x["高點"] == y["高點"] and x["谷底"] == y["谷底"] and repr(float(x["跌幅_simple"])) == repr(float(y["跌幅"]))
                and x["分型_simple（副）"] == y["分型"] for x, y in zip(R50, rep50))}
    log(f"[查核②] 0050 事件 simple 重算 vs summary.json §四④：{chk2}")

    # ═════ ③ 中位種子事件 ═════
    base = ref.loc["base"].reset_index()
    med_mdd = base.set_index("r").sort_index()["mdd"].median()
    bs = base.sort_values("seed")
    med_seed = int(bs.iloc[(bs["mdd"] - med_mdd).abs().to_numpy().argsort(kind="stable")[0]]["seed"])
    eb = P.sim(P.engine_kw("base"), med_seed)["equity"]
    EVref = pd.read_csv(os.path.join(OUT, "events.csv"), float_precision="round_trip")
    RE = []
    for e_, ks, s2, s5, kl, l2, l5 in _types(eb, P9.dd_events(eb, w0, w1 + 1)):
        RE.append({"seed": med_seed, "高點": str(cal[e_["peak"]].date()), "谷底": str(cal[e_["trough"]].date()),
                   "回升": str(cal[e_["recover"]].date()), "回升了": e_["recovered"], "日數": e_["recover"] - e_["peak"],
                   "基準回落_simple": e_["dd"], "基準回落_log": float(np.log(eb[e_["trough"]] / eb[e_["peak"]])),
                   "分型_log（主）": kl, "最差2日占比_log": l2, "最差5日占比_log": l5,
                   "分型_simple（副）": ks, "最差2日占比_simple": s2, "最差5日占比_simple": s5, "換型": ks != kl})
    EV = pd.DataFrame(RE)
    chk3 = {"中位種子": med_seed == int(S["§四⑤"]["中位種子"]) and bool((EVref["seed"] == med_seed).all()),
            "事件數": len(EV) == len(EVref),
            "逐筆（高點、谷底、回升、基準回落、分型、最差2日占比）": len(EV) == len(EVref) and all(
                x["高點"] == y["高點"] and x["谷底"] == y["谷底"] and x["回升"] == y["回升"]
                and repr(float(x["基準回落_simple"])) == repr(float(y["基準回落"])) and x["分型_simple（副）"] == y["分型"]
                and repr(float(x["最差2日占比_simple"])) == repr(float(y["最差2日占比"])) for x, y in zip(RE, EVref.to_dict("records")))}
    log(f"[查核③] 中位種子事件 simple 重算 vs events.csv：{chk3}")

    all_ok = all(chk1.values()) and all(chk2.values()) and all(chk3.values())
    if not all_ok:
        raise SystemExit(f"⛔ simple 重算查核不過：①{chk1} ②{chk2} ③{chk3}")

    TB.to_csv(os.path.join(OUT, "ddtype_log.csv"), index=False)
    E50.to_csv(os.path.join(OUT, "ddtype_log_0050.csv"), index=False)
    EV.to_csv(os.path.join(OUT, "ddtype_log_events.csv"), index=False)
    write_md(OUT, TB, E50, EV, det, chk1, chk2, chk3, med_seed)
    log("[完成] ddtype_log.csv／ddtype_log_0050.csv／ddtype_log_events.csv／DDTYPE_LOG.md")


def _p(x):
    return f"{x * 100:.1f}%"


def write_md(OUT, TB, E50, EV, det, chk1, chk2, chk3, med_seed):
    L = []
    A = L.append
    A("# PREREGP9 12 格：回落分型 log 口徑版（主）＋ simple 版並列（副）")
    A("")
    A(f"產生：`backtest/researchP9run_ddlog.py`（{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M} 台北）｜依據：裁定線 seq174 §二｜"
      "對象：已交件 commit 8694b4f173 的 `resultsP9run/`")
    A("")
    A("⛔ **12 格標籤不動**：年化、回落、比值、合格／另列／不合格都照已交件的 `cells.csv`，本檔不重報、不重判。"
      "回落深度與事件切法（≥ 20%、高點／谷底／回升）兩種口徑相同 ⇒ 事件數不變，**只有分型描述會換**。")
    A("")
    A("## 口徑")
    A("")
    A("- **log（主）**：`researchp9.dd_type(scale=\"log\")`＝策略線 seq5 §7-2 `ddtype.py` 的口徑：高點→谷底逐日 log 報酬，"
      "最差 k 日 log 報酬合計 ÷ 事件總 log 跌幅。")
    A("- **simple（副）**：`dd_type` 預設（＝已交件報告與 P9B_REPORT）：逐日單純報酬合計 ÷ 事件總單純跌幅。")
    A("- 門檻兩版相同：最差 2 日占比 ≥ 50% ⇒ 單日暴跌型；否則最差 5 日占比 < 50% ⇒ 延續下跌型；其餘 ⇒ 混合型。")
    A("")
    A("## 查核")
    A("")
    A(f"- 決定性（重跑 14 臂 × 200 顆，對 `seeds_arms.csv`／`cells.csv`）：{det}")
    A(f"- simple 重算 ①（每顆種子 dd_* 對 `seeds_arms.csv`、各格中位對 `cells.csv`）：{chk1}")
    A(f"- simple 重算 ②（0050 事件對 `summary.json` §四④＝報告 §八表）：{chk2}")
    A(f"- simple 重算 ③（中位種子 {med_seed} 事件對 `events.csv`）：{chk3}")
    A("")
    A("## ② 0050 自己的 ≥ 20% 回落事件（報告 §八；主窗）")
    A("")
    A("| 事件（高點→谷底） | 跌幅 | 分型 log（主） | 最差2日／5日占比 log | 分型 simple（副） | 最差2日／5日占比 simple | 換型 |")
    A("|---|---:|---|---|---|---|---|")
    for _, x in E50.iterrows():
        A(f"| {x['高點']} → {x['谷底']} | {x['跌幅_simple'] * 100:.1f}% | **{x['分型_log（主）']}** | {_p(x['最差2日占比_log'])}／{_p(x['最差5日占比_log'])} | "
          f"{x['分型_simple（副）']} | {_p(x['最差2日占比_simple'])}／{_p(x['最差5日占比_simple'])} | {'⚠ 換型' if x['換型'] else '同'} |")
    A("")
    A("## ③ 基準臂中位種子的 ≥ 20% 事件（報告 §九；events.csv）")
    A("")
    A("| 事件（高點→谷底→回升） | 基準回落 | 分型 log（主） | 最差2日／5日占比 log | 分型 simple（副） | 最差2日／5日占比 simple | 換型 |")
    A("|---|---:|---|---|---|---|---|")
    for _, x in EV.iterrows():
        A(f"| {x['高點']} → {x['谷底']} → {x['回升']} | {x['基準回落_simple'] * 100:.1f}% | **{x['分型_log（主）']}** | "
          f"{_p(x['最差2日占比_log'])}／{_p(x['最差5日占比_log'])} | {x['分型_simple（副）']} | "
          f"{_p(x['最差2日占比_simple'])}／{_p(x['最差5日占比_simple'])} | {'⚠ 換型' if x['換型'] else '同'} |")
    A("")
    A("## ① 各臂 200 顆種子的分型計數（報告 §八「回落分兩型」表）")
    A("")
    A("事件數報每顆種子的中位；各型報 200 顆合計（括號內為每顆種子計數的中位）。")
    A("")
    A("| 格 | 事件數 中位 | log 單日暴跌 | log 延續下跌 | log 混合 | simple 單日暴跌 | simple 延續下跌 | simple 混合 | 換型事件（占全部事件） | 計數有變的種子 |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, x in TB.iterrows():
        cs = []
        for sc in ("log", "simple"):
            for k in KINDS:
                cs.append(f"{x[f'{sc}_{k}_合計']}（{x[f'{sc}_{k}_中位']:g}）")
        A(f"| {x['格']} | {x['事件數_中位']:g} | " + " | ".join(cs) +
          f" | {x['換型事件數']}（{x['換型事件占比'] * 100:.1f}%） | {x['計數有變的種子數']}／{x['種子數']} |")
    A("")
    A("換型方向（200 顆合計，simple → log）：")
    A("")
    cols = [c for c in TB.columns if c.startswith("換型_")]
    nz = [c for c in cols if TB[c].sum() > 0]
    if nz:
        A("| 格 | " + " | ".join(c.replace("換型_", "") for c in nz) + " |")
        A("|---|" + "---:|" * len(nz))
        for _, x in TB.iterrows():
            A(f"| {x['格']} | " + " | ".join(str(int(x[c])) for c in nz) + " |")
        rev = [c for c in cols if TB[c].sum() > 0 and (c.startswith("換型_延續下跌型") or c == "換型_混合型→單日暴跌型")]
        A("")
        A("反方向（延續→混合／單日、混合→單日）的換型：" + ("、".join(f"{c.replace('換型_', '')} {int(TB[c].sum())} 次" for c in rev) if rev else "0 次") + "。")
    else:
        A("無換型。")
    A("")
    med_changed = [x["格"] for _, x in TB.iterrows() if any(x[f"差_{k}_中位（log−simple）"] != 0 for k in KINDS)]
    A("各格【每顆種子計數的中位】有變的格：" + ("、".join(med_changed) if med_changed else "無") + "。")
    A("")
    A("## 檔案")
    A("")
    A("- `ddtype_log.csv`：每格 log／simple 三型計數（中位、合計）、差（log − simple）、換型事件數與方向、計數有變的種子數")
    A("- `ddtype_log_0050.csv`：0050 事件逐筆兩版並列（含最差 2／5 日占比、simple 與 log 跌幅）")
    A("- `ddtype_log_events.csv`：基準臂中位種子事件逐筆兩版並列")
    A("")
    A("⛔ 本檔只補分型描述；已交件的 `P9_REPORT.md`、`cells.csv`、`events.csv`、`summary.json` 未改動。")
    open(os.path.join(OUT, "DDTYPE_LOG.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())

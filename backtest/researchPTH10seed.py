# -*- coding: utf-8 -*-
"""高10（PTH 最高 10 檔、N10）「同分隨機打破」種子敏感度——回測線計算子代理（使用者問「高10 裡面是隨便挑？」，2026-10-21）。
⛔ 描述、不判、不計 N；⛔ 不改既有檔、只新增；⛔ 不寫第二份實作：researchPTHpf（build_world、load_events、metrics、常數）、
   researchPTHn（run_slot、trades_df、df_text、same）、researchPTH（stock_job）、researchAscTri（label、ratio）只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10seed [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10seed_check
輸出 backtest/resultsPTH10seed/：seed10.json、seeds_<世界>.csv、summary.csv、ties_<世界>.csv、run.log

讀法（★ 執行者定）：
 S1 唯一更動 ＝ researchPTHpf.load_events 裡「同 PTH 打破」的 rk ＝ default_rng([SEED_TOP, 形成月序 j])。本行程內把模組常數 M.SEED_TOP
    換成 20261021 ＋ k·2³²（k ＝ 1…200）⇒ numpy SeedSequence 把大整數拆成 32 位元字 ⇒ 熵 ＝ [20261021, k, j]，即
    default_rng([20261021, k, j])（本檔開跑前逐 k 斷言兩式前 8 個亂數逐位元相同）。跑完還原 SEED_TOP（⛔ 不改檔）。
 S2 其餘全照 researchPTHn N10（滑價關）：候選 ＝ 跳月各批事件、PTH 由高往下（lexsort(rk, −PTH, 進場日)）、10 格、6 個月、空位 0050、成本
    ＝ researchPTHn.run_slot(ev, W, 10, False) 原樣。
 S3 對帳（必過）：原種子（SEED_TOP ＝ 20261023）⇒ eq/hv/u/pend/nh 與 resultsPTHn/eq_<世界>.npz N10_* 逐位元、交易檔全文與 trades_<世界>_N10
    逐字、段統計與 PTHn_main.csv N＝10 列（%.6g 字面）相同；不同 ⇒ 中止。另斷言每個 k 的事件除 rk 外與原種子逐位元相同。
 S4 段 ＝ 主世界 探索、確認；早年世界 早年。比值 ＝ 年化 ÷ |回落|（AS.ratio）。對 0050「兩項都勝」＝ 年化 ＞ 0050 年化 且 比值 ≥ 0050 比值
    （＝ AS.label 合格；另報「比值 ＞」嚴格版）。原種子百分位 ＝ 200 組中 ≤ 原種子值 的比例（另報 ＜）。
 S5 同分描述（原種子路徑）：每批（月）候選依 PTH 分組；「需抽」＝ 該月買進格數 k＞0 且 邊界組（買到的最低 PTH 值那組）有沒買到的成員
    （扣掉當時已持有、當天賣出的同檔）。報：PTH＝1 組大小、每月買進格數、需抽月比例、需抽月中邊界組大小與從中抽的格數。
 S6 並列：resultsPTHn/random_<世界>.csv.gz N＝10（前 30% 完全隨機、候選依代號、simulate 原生抽籤、200 次）同欄分布。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHn as PN                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10seed"
SRC = PN.OUT
BASE = 20261021
NSEED = 200
N = 10
SEED0 = M.SEED_TOP
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
EVKEYS = ("sid", "j", "jm", "e", "X", "typ", "R", "sd", "sale", "P", "px", "pth", "form")


def same_arr(a, b):
    """逐位元相同；浮點欄 NaN 對 NaN 視為相同（R 有資料尾 NaN）。"""
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype.kind == "f" and b.dtype.kind == "f":
        return a.shape == b.shape and bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))
    return np.array_equal(a, b)


def seed_of(k):
    return BASE + (int(k) << 32)


def seed_selftest():
    for k in range(1, NSEED + 1):
        for j in (0, 7, 140):
            a = np.random.default_rng([seed_of(k), j]).random(8); b = np.random.default_rng([BASE, k, j]).random(8)
            if not np.array_equal(a, b):
                raise SystemExit(f"⛔ 種子編碼 k={k} j={j} ≠ [BASE,k,j]")
    return "k＝1…200 × j∈{0,7,140}：default_rng([BASE＋k·2³², j]) ＝ default_rng([BASE, k, j]) 前 8 亂數逐位元相同"


def events_with(W, wn, RES, top):
    M.SEED_TOP = top
    try:
        ev, info = M.load_events(W, wn, "跳月", RES)
    finally:
        M.SEED_TOP = SEED0
    return ev, info


def seg_row(W, S, sg):
    x, y = W["segp"][sg]
    c_, m_, b = M.metrics(W, S["eq"], x, y)
    return {f"{sg}_年化": c_, f"{sg}_回落": m_, f"{sg}_比值": AS.ratio(c_, m_), f"{sg}_平均持股": float(np.mean(S["nh"][x:y + 1]))}, b


def buyset(ev, S):
    return {(int(t), str(ev["sid"][S["q"][q]])) for t, q, _ in S["buys"]}


def tie_stats(W, ev, S, wn):
    """S5：原種子路徑每批的同分描述。"""
    q2 = S["q"]
    held_at = {}
    sl = {q: t for t, q, amt, proc in S["sells"]}
    for t, q, _ in S["buys"]:
        held_at.setdefault("iv", []).append((int(S["j"][q]), int(t), int(sl.get(q, W["n0"] + 1))))
    iv = np.array(held_at.get("iv", []), np.int64).reshape(-1, 3)
    bought = Counter(int(t) for t, _, _ in S["buys"])
    rows = []
    for e in np.unique(ev["e"]):
        idx = np.flatnonzero(ev["e"] == e)
        p = ev["pth"][idx]; jj = ev["j"][idx]
        # 當天不可買（已持有且未於當天前賣出、或當天賣出）的同檔
        blk = set(int(j) for j, tb, ts in iv if tb < e and ts >= e)
        ok = np.array([int(j) not in blk for j in jj])
        k = bought.get(int(e), 0)
        n1 = int((p == 1.0).sum()); n1ok = int(((p == 1.0) & ok).sum())
        r = {"世界": wn, "進場日": W["dates"][e], "候選": int(len(idx)), "PTH=1組": n1, "PTH=1組(可買)": n1ok, "買進格數": int(k),
             "同分組數(≥2)": int(sum(1 for v, c in Counter(p.tolist()).items() if c >= 2)), "需抽": False, "邊界PTH": np.nan,
             "邊界組(可買)": 0, "邊界組買進": 0, "買進全在PTH=1": False}
        if k > 0:
            bq = [q2[q] for t, q, _ in S["buys"] if t == e]
            bp = ev["pth"][bq]; v = float(bp.min())
            grp = int(((p == v) & ok).sum()); got = int((bp == v).sum())
            r.update({"邊界PTH": v, "邊界組(可買)": grp, "邊界組買進": got, "需抽": bool(grp > got), "買進全在PTH=1": bool((bp == 1.0).all())})
        rows.append(r)
    return pd.DataFrame(rows)


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    J = {"題": "使用者問「高10 裡面是隨便挑？」：PTH N10 同分隨機打破換 200 組種子的分布", "身分": "描述（⛔ 不判、不計 N）",
         "種子": f"default_rng([{BASE}, k, 形成月序 j])，k＝1…{NSEED}（以 SEED_TOP＝{BASE}＋k·2³² 傳入 load_events）；原種子 [{SEED0}, j]",
         "開跑": M.now_tpe(), "種子自測": seed_selftest(), "對帳": {}, "摘要": {}, "同分": {}, "完全隨機對照": {}}
    log(f"[種子] {J['種子自測']}")
    PREF = pd.read_csv(os.path.join(SRC, "PTHn_main.csv"), dtype=str, encoding="utf-8-sig")
    SUM = []
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        # ── 原種子 ＋ 對帳
        ev0, info = events_with(W, wn, RES, SEED0)
        S0 = PN.run_slot(ev0, W, N, False)
        Z = np.load(os.path.join(SRC, f"eq_{wn}.npz"))
        for k_ in ("eq", "hv", "u", "pend", "nh"):
            if not np.array_equal(S0[k_], Z[f"N10_{k_}"]):
                raise SystemExit(f"⛔ 原種子 {wn} {k_} ≠ resultsPTHn N10")
        with gzip.open(os.path.join(SRC, f"trades_{wn}_N10.csv.gz"), "rt", encoding="utf-8") as fh:
            orig = fh.read()
        if PN.df_text(PN.trades_df(W, ev0, S0), "%.17g") != orig:
            raise SystemExit(f"⛔ 原種子 {wn} 交易檔 ≠ resultsPTHn trades_{wn}_N10")
        J["對帳"][f"{wn}|原種子 N10 逐日 eq/hv/u/pend/nh"] = "逐位元相同"
        J["對帳"][f"{wn}|原種子 N10 交易檔（全文）"] = f"逐字相同（{len(S0['buys'])} 筆）"
        row0 = {"k": 0, "種子": f"[{SEED0}, j]（原）", "買進筆": len(S0["buys"]), "與原種子同買進(日,代號)比例": 1.0}
        BEN = {}
        for sg in SEGS[wn]:
            d, b = seg_row(W, S0, sg); row0.update(d); BEN[sg] = b
            ref = PREF[(PREF["世界"] == wn) & (PREF["N"] == "10") & (PREF["滑價"] == "False") & (PREF["段"] == sg)].iloc[0]
            for col in ("年化", "回落", "比值"):
                if "%.6g" % d[f"{sg}_{col}"] != ref[col]:
                    raise SystemExit(f"⛔ 原種子 {wn}/{sg} {col} {d[f'{sg}_{col}']} ≠ PTHn_main {ref[col]}")
            J["對帳"][f"{wn}|原種子 {sg} 年化/回落/比值 vs PTHn_main.csv（%.6g）"] = "相同"
        TS0 = tie_stats(W, ev0, S0, wn)
        TS0.to_csv(os.path.join(OUT, f"ties_{wn}.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
        B0 = buyset(ev0, S0)
        # ── 200 組種子
        ROWS = [row0]; t0 = time.time()
        for k in range(1, NSEED + 1):
            ev, _ = events_with(W, wn, RES, seed_of(k))
            for key in EVKEYS:
                if not same_arr(ev[key], ev0[key]):
                    raise SystemExit(f"⛔ k={k} 事件欄 {key} ≠ 原種子（應只有 rk 不同）")
            S = PN.run_slot(ev, W, N, False)
            Bk = buyset(ev, S)
            r = {"k": k, "種子": f"[{BASE}, {k}, j]", "買進筆": len(S["buys"]), "與原種子同買進(日,代號)比例": len(Bk & B0) / max(len(Bk), 1)}
            for sg in SEGS[wn]:
                r.update(seg_row(W, S, sg)[0])
            ROWS.append(r)
            if k % 50 == 0:
                log(f"[{wn}] 種子 {k}/{NSEED}｜{time.time() - t0:.0f}s")
        DF = pd.DataFrame(ROWS)
        DF.to_csv(os.path.join(OUT, f"seeds_{wn}.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
        D = DF[DF["k"] > 0]
        # ── 完全隨機對照
        RD = pd.read_csv(os.path.join(SRC, f"random_{wn}.csv.gz"))
        RD = RD[RD["N"] == 10]
        for sg in SEGS[wn]:
            b = BEN[sg]; br = AS.ratio(b["cagr"], b["mdd"])
            for src, X, cagr, mdd in (("同分換種子", D, D[f"{sg}_年化"], D[f"{sg}_回落"]), ("前30%完全隨機", RD, RD[f"{sg}_年化"], RD[f"{sg}_回落"])):
                rat = cagr / mdd.abs()
                o = {"世界": wn, "段": sg, "來源": src, "次數": int(len(X)), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": br}
                for nm, v in (("年化", cagr), ("回落", mdd), ("比值", rat)):
                    o.update({f"{nm}_中位": float(v.median()), f"{nm}_p5": float(v.quantile(.05)), f"{nm}_p95": float(v.quantile(.95)),
                              f"{nm}_最小": float(v.min()), f"{nm}_最大": float(v.max())})
                    if src == "同分換種子":
                        o[f"{nm}_原種子"] = float(row0[f"{sg}_{nm}"])
                        o[f"{nm}_原種子百分位(≤)"] = float((v <= row0[f"{sg}_{nm}"]).mean())
                        o[f"{nm}_原種子百分位(<)"] = float((v < row0[f"{sg}_{nm}"]).mean())
                o["對0050兩項都勝(合格:年化>且比值≥)"] = float(((cagr > b["cagr"]) & (rat >= br)).mean())
                o["對0050兩項都勝(嚴格比值>)"] = float(((cagr > b["cagr"]) & (rat > br)).mean())
                o["年化勝0050"] = float((cagr > b["cagr"]).mean()); o["比值勝0050"] = float((rat > br).mean())
                o["標籤比例"] = json.dumps({kk: vv / len(X) for kk, vv in Counter(AS.label(c, m, b) for c, m in zip(cagr, mdd)).items()},
                                          ensure_ascii=False)
                SUM.append(o)
        J["完全隨機對照"][wn] = "resultsPTHn/random_%s.csv.gz N＝10（%d 次）" % (wn, len(RD))
        # ── 同分摘要
        T = TS0[TS0["候選"] > 0]; Tb = T[T["買進格數"] > 0]; Td = Tb[Tb["需抽"]]
        J["同分"][wn] = {"批次(月)": int(len(T)), "候選中位": float(T["候選"].median()), "PTH=1組大小平均": float(T["PTH=1組"].mean()),
                        "PTH=1組大小中位": float(T["PTH=1組"].median()), "PTH=1組(可買)平均": float(T["PTH=1組(可買)"].mean()),
                        "有買進的月": int(len(Tb)), "每月買進格數平均(有買進月)": float(Tb["買進格數"].mean()),
                        "每月買進格數平均(全部月)": float(T["買進格數"].mean()),
                        "需抽月比例(有買進月)": float(Tb["需抽"].mean()) if len(Tb) else np.nan,
                        "買進全在PTH=1的月比例(有買進月)": float(Tb["買進全在PTH=1"].mean()) if len(Tb) else np.nan,
                        "需抽月：邊界組(可買)平均": float(Td["邊界組(可買)"].mean()) if len(Td) else np.nan,
                        "需抽月：從邊界組抽的格數平均": float(Td["邊界組買進"].mean()) if len(Td) else np.nan,
                        "200組與原種子同買進(日,代號)比例中位": float(D["與原種子同買進(日,代號)比例"].median()),
                        "200組與原種子同買進比例 p5／p95": [float(D["與原種子同買進(日,代號)比例"].quantile(.05)),
                                                   float(D["與原種子同買進(日,代號)比例"].quantile(.95))]}
        log(f"[{wn}] 同分 {json.dumps(J['同分'][wn], ensure_ascii=False)}")
        del RES, W, ev0, S0, Z
    SM = pd.DataFrame(SUM)
    SM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["摘要"] = SUM
    log("[摘要]\n" + SM[["世界", "段", "來源", "年化_中位", "年化_p5", "年化_p95", "回落_中位", "比值_中位", "比值_p5", "比值_p95",
                       "對0050兩項都勝(合格:年化>且比值≥)"]].to_string())
    log(f"[對帳] {json.dumps(J['對帳'], ensure_ascii=False)}")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "seed10.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--dry", action="store_true", help="乾跑：只做種子自測與 import，不算報酬")
    a = ap.parse_args()
    if a.dry:
        print(seed_selftest()); print("SEED_TOP 原值", SEED0, "N", N, "SRC", SRC)
        x = np.array([1.0, np.nan, 2.0])
        assert same_arr(x, x.copy()) and not same_arr(x, np.array([1.0, np.nan, 3.0])) and not same_arr(x, np.array([1.0, 0.0, 2.0]))
        assert same_arr(np.array(["a", "b"], object), np.array(["a", "b"], object)) and same_arr(np.arange(3), np.arange(3))
        print("same_arr 自測：NaN＝NaN、值差、NaN≠數、字串、整數 全過"); return
    os.makedirs(OUT, exist_ok=True)
    run(a, RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()

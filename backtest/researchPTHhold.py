# -*- coding: utf-8 -*-
"""接近 52 週新高（PTH）組合層「N 格補空位 × 持有月數」描述——回測線計算子代理（使用者問「抱 3 個月跟 6 個月比呢？」，2026-10-20）。
⛔ 描述、不計 N、不判、⛔ 不改任何判定；看過 resultsPTHpf／resultsPTHn 結果之後才問 ⇒
   「看過結果的參數變體，只描述，不當改規則的依據；前瞻照 seq402 的 10 格抱 6 個月，不因此改」。
⛔ 只計算：不 commit、不改既有檔；researchPTHn（run_slot、rand_job、set_ns、trade_dist、trades_df、df_text、same、NOTE_EARLY）、
   researchPTHpf（build_world、load_events、CELLS、slot_tr、pf_stats、metrics、_G、常數）、researchPTH（stock_job）、
   researchTurtleS2PF（verdict）、researchAscTri（label、ratio）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHhold [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHhold_check
輸出 backtest/resultsPTHhold/：PTHhold.json、PTHhold_main.csv、trade_dist.csv、random_<世界>.csv.gz、trades_<世界>_H<h>_N<n>[s].csv.gz、
    eq_<世界>.npz、run.log

讀法（★ 執行者定）：
 H1 持有月數 h ∈ {3, 6}、格數 N ∈ {10, 15}；做法 ＝ researchPTHn「N 格補空位版」原樣（researchPTHn.run_slot），⛔ 只把持有月數參數化：
    事件 ＝ researchPTHpf.load_events(W, 世界, 格)，格 ＝ {6: "跳月"（L＝2、H＝6）, 3: "跳月_3月"（L＝2、H＝3）}（＝ researchPTHpf CELLS 既有兩格；
    兩格事件逐列 代號、進場日、PTH 相同 ＝ 同一批入選股，只差到期日；本支開跑時驗）。候選順序（PTH 由高往下、R9 種子）、槽數設法、
    0050 撥款、同檔不重複 ⇒ 全同 researchPTHn。
 H2 滑價版 ＝ run_slot(…, slip=True)（同 researchPTHn N2）。
 H3 隨機 ＝ researchPTHn.rand_job（＝ researchPTHpf.rand_job：候選依代號排序、default_rng([20261020, 世界, i])、200 次）⇒ 每個 (h, N) 同一組種子；
    「前 30% 內隨機抽同檔數」＝ 同一批事件、同 N 槽，由 simulate 原生抽籤代替「由高往下」。比值 ＝ 年化 ÷ |回落|；
    「排序版比值 ≥ 隨機比例」＝ 200 次中 隨機比值 ≤ 排序版比值 的比例。
 H4 必報 ＝ researchPTHpf.pf_stats；空位率 ＝ 1 − 平均持股 ÷ N；單筆 ＝ researchPTHn.trade_dist（依買進日歸段、已出場、R用 − 0.585%）。
 H5 對帳（必過）：h ＝ 6 的 N＝10、15（主、滑價）⇒ resultsPTHn 逐日 eq/hv/u/pend/nh 陣列逐位元、交易檔全文逐字、主表統計每欄逐位元、
    單筆分布逐位元、隨機 200 次全文逐字、隨機摘要逐位元；不同 ⇒ 中止。
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
from backtest import researchPTHn as PN                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchTurtleS2PF as TS               # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTHhold"
SRCN = PN.OUT                                               # resultsPTHn
HOLDS = {3: "跳月_3月", 6: "跳月"}
NLIST = (10, 15)
NOTE_EARLY = PN.NOTE_EARLY
SENT_DESC = "看過結果的參數變體，只描述，不當改規則的依據；前瞻照 seq402 的 10 格抱 6 個月，不因此改"


def hold_events(W, wn, h, RES):
    cell = HOLDS[h]
    if M.CELLS[cell] != (2, h):
        raise SystemExit(f"⛔ 格 {cell} {M.CELLS[cell]} ≠ (2, {h})")
    return M.load_events(W, wn, cell, RES)


def rand_summary(z, R_, sg, bench_sg):
    rr = R_[f"{sg}_年化"] / R_[f"{sg}_回落"].abs()
    labs = Counter(AS.label(c_, m_, bench_sg) for c_, m_ in zip(R_[f"{sg}_年化"], R_[f"{sg}_回落"]))
    return {"排序版年化": z["年化"], "排序版比值": z["比值"], "隨機年化p10": float(R_[f"{sg}_年化"].quantile(.1)),
            "隨機年化中位": float(R_[f"{sg}_年化"].median()), "隨機年化p90": float(R_[f"{sg}_年化"].quantile(.9)),
            "隨機回落中位": float(R_[f"{sg}_回落"].median()), "隨機比值中位": float(rr.median()),
            "排序版比值≥隨機的比例": float((rr <= z["比值"]).mean()), "p（隨機比值≥排序版）": float((rr >= z["比值"]).mean()),
            "p（隨機年化≥排序版）": float((R_[f"{sg}_年化"] >= z["年化"]).mean()), "隨機標籤比例": {k: v / len(R_) for k, v in labs.items()},
            "隨機平均持股中位": float(R_[f"{sg}_平均持股"].median()), "次數": int(len(R_))}


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    PJ = json.load(open(os.path.join(SRCN, "PTHn.json"), encoding="utf-8"))
    J = {"題": "使用者問「抱 3 個月跟 6 個月比呢？」：PTH 組合層 N 格補空位寫法、N ∈ " + str(list(NLIST)) + " × 持有 " + str(list(HOLDS)) + " 個月",
         "身分": "描述（⛔ 不判、不計 N）", "結果句必附": SENT_DESC, "早年註": NOTE_EARLY, "開跑": M.now_tpe(), "對帳": {}, "表": [], "隨機": {},
         "單筆": [], "事件": {}}
    TAB = []; DIST = []
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        EV = {}
        for h in HOLDS:
            EV[h], info = hold_events(W, wn, h, RES)
            J["事件"][f"{wn}|抱{h}月"] = info
            log(f"[查核 {wn}/{HOLDS[h]}] 事件 {info['列']:,} 列 ＝ stock_job 重算｜批次 {info['批次數']}｜出場 {info['出場種類']}")
        del RES
        if not (np.array_equal(EV[3]["sid"], EV[6]["sid"]) and np.array_equal(EV[3]["e"], EV[6]["e"]) and np.array_equal(EV[3]["pth"], EV[6]["pth"])
                and np.array_equal(EV[3]["rk"], EV[6]["rk"])):
            raise SystemExit(f"⛔ {wn} 抱 3／6 月事件入選不同")
        J["對帳"][f"{wn}|抱 3／6 月事件 代號、進場日、PTH、R9 種子 逐列相同"] = f"相同（{len(EV[6]['sid']):,} 列）"
        cal = W["cal"]; segp = W["segp"]
        bench = {sg: RR.bench_row(cal, W["bench"], x, y + 1) for sg, (x, y) in segp.items()}
        SIM = {}
        for h in HOLDS:
            for N in NLIST:
                for slip in (False, True):
                    SIM[(h, N, slip)] = PN.run_slot(EV[h], W, N, slip)
                log(f"[組合 {wn}] 抱{h}月 N={N} 買進 {len(SIM[(h, N, False)]['buys'])}／滑價 {len(SIM[(h, N, True)]['buys'])}｜{time.time() - T0:.0f}s")
        # ── 抱 6 月 ⇒ resultsPTHn 對帳（陣列、交易檔）
        Zn = np.load(os.path.join(SRCN, f"eq_{wn}.npz"))
        for N in NLIST:
            for slip in (False, True):
                S = SIM[(6, N, slip)]; key = f"N{N}{'s' if slip else ''}"
                for k in ("eq", "hv", "u", "pend", "nh"):
                    if not np.array_equal(S[k], Zn[f"{key}_{k}"]):
                        raise SystemExit(f"⛔ 抱6月 {wn} {key} {k} ≠ resultsPTHn")
                with gzip.open(os.path.join(SRCN, f"trades_{wn}_{key}.csv.gz"), "rt", encoding="utf-8") as fh:
                    orig = fh.read()
                if PN.df_text(PN.trades_df(W, EV[6], S), "%.17g") != orig:
                    raise SystemExit(f"⛔ 抱6月 {wn} {key} 交易檔 ≠ resultsPTHn")
                J["對帳"][f"{wn}|抱6月 {key} 逐日 eq/hv/u/pend/nh ＋ 交易檔全文"] = f"逐位元／逐字相同（{len(S['buys'])} 筆）"
        # ── 統計
        rows_here = {}
        for h in HOLDS:
            ev = EV[h]
            for N in NLIST:
                for slip in (False, True):
                    S = SIM[(h, N, slip)]
                    typ_q = ev["typ"][S["q"]]
                    for sg, (x, y) in segp.items():
                        c_, m_, b = M.metrics(W, S["eq"], x, y)
                        row = {"世界": wn, "持有月": h, "N": N, "滑價": slip, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_,
                               "比值": AS.ratio(c_, m_), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]),
                               "標籤": AS.label(c_, m_, b), **M.pf_stats(W, S, x, y, typ_q)}
                        nh = S["nh"][x:y + 1]
                        row["空位率"] = float(1 - np.mean(nh) / N); row["有空位日比例"] = float(np.mean(nh < N))
                        row["平均持股<3(退化)"] = bool(np.mean(nh) < M.DEG_HOLD)
                        rows_here[(h, N, slip, sg)] = row; TAB.append(row)
                        if not slip:
                            DIST.append({"世界": wn, "持有月": h, "臂": f"N={N}", "段": sg, **PN.trade_dist(S, x, y)})
        for sg, (x, y) in segp.items():
            b = bench[sg]
            TAB.append({"世界": wn, "持有月": "—", "N": "0050", "滑價": False, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": b["cagr"],
                        "回落": b["mdd"], "比值": AS.ratio(b["cagr"], b["mdd"])})
        # 抱 6 月統計、單筆 ⇒ PTHn.json
        for N in NLIST:
            for slip in (False, True):
                for sg in segp:
                    ref = [z for z in PJ["表"] if z["世界"] == wn and z["N"] == N and z["滑價"] == slip and z["段"] == sg][0]
                    row = rows_here[(6, N, slip, sg)]
                    bad = [k for k in row if k in ref and k not in ("世界", "段", "N") and not PN.same(row[k], ref[k])]
                    nk = sum(1 for k in row if k in ref)
                    if bad or nk < 30:
                        raise SystemExit(f"⛔ 抱6月 {wn}/N{N}/{slip}/{sg} 統計 ≠ PTHn.json：{bad}（{nk} 欄）")
                    J["對帳"][f"{wn}|抱6月 N={N}{'滑價' if slip else ''} {sg} 主表統計（{nk} 欄）"] = "逐位元相同"
            for sg in segp:
                ref = [z for z in PJ["單筆"] if z["世界"] == wn and z["臂"] == f"N={N}" and z["段"] == sg][0]
                mine = [z for z in DIST if z["世界"] == wn and z["持有月"] == 6 and z["臂"] == f"N={N}" and z["段"] == sg][0]
                bad = [k for k in ref if k not in ("世界", "臂", "段") and not PN.same(mine[k], ref[k])]
                if bad:
                    raise SystemExit(f"⛔ 抱6月 {wn}/N{N}/{sg} 單筆 ≠ PTHn.json：{bad}")
                J["對帳"][f"{wn}|抱6月 N={N} {sg} 單筆分布"] = "逐位元相同"
        log(f"[統計 {wn}] 完｜{time.time() - T0:.0f}s")
        # ── 存檔
        np.savez_compressed(os.path.join(OUT, f"eq_{wn}.npz"), Bc=W["Bc"], Bo=W["Bo"],
                            **{f"H{h}_N{N}{'s' if sl else ''}_{k}": SIM[(h, N, sl)][k] for (h, N, sl) in SIM for k in ("eq", "hv", "u", "pend", "nh")})
        for (h, N, sl), S in SIM.items():
            with gzip.open(os.path.join(OUT, f"trades_{wn}_H{h}_N{N}{'s' if sl else ''}.csv.gz"), "wt", encoding="utf-8") as fh:
                PN.trades_df(W, EV[h], S).to_csv(fh, index=False, float_format="%.17g")
        # ── 隨機（每個持有月數各一組候選；同種子）
        RD = []
        for h in HOLDS:
            ev = EV[h]
            o_ = np.lexsort((W["srank"][ev["j"]], ev["e"]))
            M._G[wn] = {"tr": M.slot_tr(ev, False, o_), "n0": W["n0"], "CM": W["CM"], "Bc": W["Bc"], "Bo": W["Bo"], "segp": segp}
            t0 = time.time()
            with Pool(a.procs) as pool:
                RL = pool.map(PN.rand_job, [(wn, N, i) for N in NLIST for i in range(M.NRAND)], chunksize=10)
            PN.set_ns(PN.NS0)
            RDh = pd.DataFrame(RL)
            log(f"[隨機 {wn} 抱{h}月] {len(RDh)} 列｜{time.time() - t0:.0f}s")
            if h == 6:
                with gzip.open(os.path.join(SRCN, f"random_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
                    ol = fh.read().splitlines()
                iN = ol[0].split(",").index("N")
                want = "\n".join([ol[0]] + [l for l in ol[1:] if int(l.split(",")[iN]) in NLIST]) + "\n"
                if PN.df_text(RDh, "%.10g") != want:
                    raise SystemExit(f"⛔ 抱6月 {wn} 隨機 ≠ resultsPTHn random_{wn}（N∈{NLIST}）")
                J["對帳"][f"{wn}|抱6月 隨機 N=10、15 各 200 次（全文）"] = "逐字相同"
            RD.append(RDh.assign(持有月=h)[["持有月"] + list(RDh.columns)])
            for N in NLIST:
                R_ = RDh[RDh["N"] == N]
                for sg in segp:
                    o = rand_summary(rows_here[(h, N, False, sg)], R_, sg, bench[sg])
                    J["隨機"].setdefault(wn, {})[f"抱{h}月|N={N}|{sg}"] = o
                    if h == 6:
                        ref = PJ["隨機"][wn][f"N={N}|{sg}"]
                        bad = [k for k in o if k != "隨機標籤比例" and not PN.same(o[k], ref[k])]
                        if bad or o["隨機標籤比例"] != ref["隨機標籤比例"]:
                            raise SystemExit(f"⛔ 抱6月 {wn} N{N}/{sg} 隨機摘要 ≠ PTHn.json：{bad}")
                        J["對帳"][f"{wn}|抱6月 N={N} {sg} 隨機摘要"] = "逐位元相同"
        pd.concat(RD, ignore_index=True).to_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), index=False, float_format="%.10g")
        del W, SIM, EV, Zn
        M._G.pop(wn, None)
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "PTHhold_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(DIST).to_csv(os.path.join(OUT, "trade_dist.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["表"] = TAB; J["單筆"] = DIST
    J["verdict形式(描述、不判)"] = {}
    for h in HOLDS:
        for N in NLIST:
            def lab(sl, sg, wn="主"):
                return [r for r in TAB if r["世界"] == wn and r["持有月"] == h and r["N"] == N and r["滑價"] == sl and r["段"] == sg][0]["標籤"]
            L = {"主判探索": lab(False, "探索"), "主判確認": lab(False, "確認"), "滑價探索": lab(True, "探索"), "滑價確認": lab(True, "確認"),
                 "主判早年": lab(False, "早年", "早年")}
            J["verdict形式(描述、不判)"][f"抱{h}月|N={N}"] = {**L, "researchTurtleS2PF.verdict 形式": TS.verdict(L)}
    log("[表]\n" + TB[["世界", "持有月", "N", "滑價", "段", "年化", "回落", "比值", "標籤", "平均持股(筆)", "空位率", "換手每年", "成本合計每年(實付)",
                     "平均持有天數"]].to_string())
    log("[單筆]\n" + pd.DataFrame(DIST)[["世界", "持有月", "臂", "段", "筆數", "中位", "平均", "勝率", "p10", "p90"]].to_string())
    for wn in J["隨機"]:
        for k, o in J["隨機"][wn].items():
            log(f"[隨機 {wn} {k}] {json.dumps(o, ensure_ascii=False, default=float)}")
    log(f"[verdict 形式] {json.dumps(J['verdict形式(描述、不判)'], ensure_ascii=False)}")
    log(f"[對帳] {json.dumps(J['對帳'], ensure_ascii=False)}")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "PTHhold.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    run(a, RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""接近 52 週新高（PTH）組合層「檔數 × 報酬分佈」描述——回測線計算子代理（使用者問「52 週檔數報酬分佈？」，2026-10-20）。
⛔ 描述、不計 N、不判、⛔ 不改任何判定；看過 resultsPTHpf 結果之後才問 ⇒「看過結果的參數變體，只描述，不當改規則的依據；
   10 檔版已另開前瞻（seq401／402），其他檔數不另開」。
⛔ 只計算：不 commit、不改既有檔；researchPTHpf（build_world、load_events、slot_tr、slot_sim、keep_order、tranche_sim、pf_stats、metrics、
   rand_job、常數）、researchPTH（stock_job）、researchTurtleS2PF（simulate、verdict、NS）、researchAscTri（label、ratio、NOTE_EARLY）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHn [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHn_check
輸出 backtest/resultsPTHn/：PTHn.json、PTHn_main.csv、random_<世界>.csv.gz、trade_dist.csv、trades_<世界>_N<n>[s].csv.gz、eq_<世界>.npz、run.log

讀法（★ 執行者定）：
 N1 格數 N ∈ {5, 10, 15, 20, 30, 50}；做法 ＝ researchPTHpf 描述①「10 檔版」原樣，⛔ 只把格數參數化：
    researchTurtleS2PF.simulate 讀模組常數 NS（槽數、新部位 ＝ min(前一日淨值 ÷ NS, 可撥 0050)）⇒ 呼叫前設 TS.NS ＝ N、呼叫後還原 10
    （⛔ 不改檔，只在本行程內設值）。候選 ＝ 跳月各批事件、PTH 由高往下（同 PTH 用 R9 種子打破）、不洗牌生成器 ＝ researchPTHpf.slot_sim 原樣。
 N2 滑價版 ＝ slot_tr(…, slip=True)（researchPTHpf Q2 同式：個股買價 ×1.005、賣價 ×0.995；0050 不加）。
 N3 隨機 ＝ researchPTHpf.rand_job 原樣（候選依代號排序、simulate 原生抽籤 default_rng([20261020, 世界, i])、200 次）⇒ 每個 N 同一組種子
    （N ＝ 10 即 resultsPTHpf/random_<世界> 原檔）。比值 ＝ 年化 ÷ |回落|（原式）；「排序版比值 ≥ 隨機」＝ 200 次中 隨機比值 ≤ 排序版比值 的比例。
 N4 必報 ＝ researchPTHpf.pf_stats（換手、成本、平均持股、0050 占淨值…）；空位率 ＝ 1 − 平均持股 ÷ N；有空位日比例 ＝ 持股 ＜ N 的日數比例。
    段、年化、回落、0050 ＝ researchPTHpf.metrics；標籤 ＝ researchAscTri.label；verdict 形式 ＝ researchTurtleS2PF.verdict（⛔ 只描述）。
 N5 單筆交易分布（依買進日歸段、只算已出場；淨報酬 ＝ R用 − 0.585%）：中位、平均、勝率（＞0）、p10、p90；
    前 10% 交易貢獻占比 ＝ 淨報酬最高的 ceil(10%) 筆之淨報酬和 ÷ 全部淨報酬和（等權）；另報金額加權版（金額×淨報酬）。
 N6 並列：主判（前 30% 全部等權、6 份）＝ researchPTHpf.tranche_sim 重算並與 resultsPTHpf/eq_<世界>.npz 逐位元對帳；0050 ＝ 同窗 bench_row。
 N7 對帳（必過）：N ＝ 10 的權益／持股／0050／現金逐日陣列、交易檔、主表統計、200 次隨機 ⇒ 與 resultsPTHpf 既有 10 檔版逐位元相同；不同 ⇒ 中止。
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
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
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchTurtleS2PF as TS               # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTHn"
SRC = M.OUT
NLIST = (5, 10, 15, 20, 30, 50)
NS0 = TS.NS
COST = M.COST
NOTE_EARLY = ["早年用 reduce_v2（減資還原）：" + AS.NOTE_EARLY[0]] + AS.NOTE_EARLY[1:]
SENT_DESC = "看過結果的參數變體，只描述，不當改規則的依據；10 檔版已另開前瞻（seq401／402），其他檔數不另開"


def set_ns(n):
    TS.NS = int(n)


def run_slot(ev, W, N, slip):
    o_ = np.lexsort((ev["rk"], -ev["pth"], ev["e"]))
    set_ns(N)
    try:
        return M.slot_sim(M.slot_tr(ev, slip, o_), W, M.keep_order())
    finally:
        set_ns(NS0)


def rand_job(a):
    wn, N, i = a
    set_ns(N)
    r = M.rand_job((wn, i))
    return {"N": N, **r}


def trade_dist(S, x, y):
    sl = {q: t for t, q, amt, proc in S["sells"]}
    rows = [(q, amt) for t, q, amt in S["buys"] if x <= t <= y and q in sl]
    nopen = sum(1 for t, q, amt in S["buys"] if x <= t <= y and q not in sl)
    if not rows:
        return {"筆數": 0, "資料尾未出場筆": nopen}
    v = np.array([S["g"][q] - COST for q, _ in rows], float); a_ = np.array([amt for _, amt in rows], float)
    k = max(1, math.ceil(0.1 * len(v)))
    top = np.argsort(-v, kind="stable")[:k]
    pnl = a_ * v
    return {"筆數": int(len(v)), "資料尾未出場筆": nopen, "中位": float(np.median(v)), "平均": float(v.mean()), "勝率": float((v > 0).mean()),
            "p10": float(np.quantile(v, .1)), "p90": float(np.quantile(v, .9)), "最好": float(v.max()), "最差": float(v.min()),
            "前10%筆數": int(k), "前10%貢獻占比(等權)": float(v[top].sum() / v.sum()) if v.sum() != 0 else np.nan,
            "前10%貢獻占比(金額加權)": float(pnl[top].sum() / pnl.sum()) if pnl.sum() != 0 else np.nan, "淨報酬和(等權)": float(v.sum())}


def trades_df(W, ev, S):
    """researchPTHpf 存檔段原式（逐字同欄、同格式）。"""
    dates = W["dates"]; TYPN = M.TYPN
    qmap = S["q"] if "q" in S else np.arange(len(ev["e"]))
    sl = {q: (t, proc) for t, q, amt, proc in S["sells"]}
    return pd.DataFrame({"sid": [ev["sid"][qmap[q]] for _, q, _ in S["buys"]], "形成月底": [ev["form"][qmap[q]] for _, q, _ in S["buys"]],
                         "PTH": [ev["pth"][qmap[q]] for _, q, _ in S["buys"]], "買進日": [dates[t] for t, _, _ in S["buys"]],
                         "份": [int(S["tranche"][q]) if "tranche" in S else -1 for _, q, _ in S["buys"]],
                         "金額": [amt for _, _, amt in S["buys"]], "市值基準價": [S["ep"][q] for _, q, _ in S["buys"]],
                         "R用": [S["g"][q] for _, q, _ in S["buys"]], "出場種類": [TYPN[int(ev["typ"][qmap[q]])] for _, q, _ in S["buys"]],
                         "排程賣出日": [dates[S["ext"][q]] if S["ext"][q] >= 0 else "" for _, q, _ in S["buys"]],
                         "賣出日": [dates[sl[q][0]] if q in sl else "" for _, q, _ in S["buys"]],
                         "入帳": [sl[q][1] if q in sl else np.nan for _, q, _ in S["buys"]]})


def df_text(df, fmt):
    b = io.StringIO(); df.to_csv(b, index=False, float_format=fmt); return b.getvalue()


def same(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    a, b = float(a), float(b)
    return (np.isnan(a) and np.isnan(b)) or a == b


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    PJ = json.load(open(os.path.join(SRC, "PTHpf.json"), encoding="utf-8"))
    J = {"題": "使用者問「52 週檔數報酬分佈？」：PTH 組合層 10 格補空位寫法、格數 N ∈ " + str(list(NLIST)), "身分": "描述（⛔ 不判、不計 N）",
         "結果句必附": SENT_DESC, "早年註": NOTE_EARLY, "開跑": M.now_tpe(), "對帳": {}, "表": [], "隨機": {}, "單筆": []}
    TAB = []; DIST = []
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        ev, info = M.load_events(W, wn, "跳月", RES)
        del RES
        log(f"[查核 {wn}/跳月] 事件 {info['列']:,} 列 ＝ stock_job 重算｜批次 {info['批次數']}")
        Z = np.load(os.path.join(SRC, f"eq_{wn}.npz"))
        cal = W["cal"]; segp = W["segp"]
        bench = {sg: RR.bench_row(cal, W["bench"], x, y + 1) for sg, (x, y) in segp.items()}
        # ── 主判（並列）＋ 對帳
        SM = {"M": M.tranche_sim(ev, 6, W, False), "Mslip": M.tranche_sim(ev, 6, W, True)}
        for arm in SM:
            for k in ("eq", "hv", "u", "pend", "nh"):
                if not np.array_equal(SM[arm][k], Z[f"{arm}_{k}"]):
                    raise SystemExit(f"⛔ 主判 {wn}/{arm} {k} ≠ resultsPTHpf")
        J["對帳"][f"{wn}|主判 M、Mslip 逐日 eq/hv/u/pend/nh"] = "逐位元相同"
        SIM = {}
        for N in NLIST:
            for slip in (False, True):
                SIM[(N, slip)] = run_slot(ev, W, N, slip)
            log(f"[組合 {wn}] N={N} 買進 {len(SIM[(N, False)]['buys'])}／滑價 {len(SIM[(N, True)]['buys'])}｜{time.time() - T0:.0f}s")
        # ── N＝10 對帳（陣列、交易檔）
        S10 = SIM[(10, False)]
        for k in ("eq", "hv", "u", "pend", "nh"):
            if not np.array_equal(S10[k], Z[f"S10_{k}"]):
                raise SystemExit(f"⛔ N=10 {wn} {k} ≠ resultsPTHpf S10")
        with gzip.open(os.path.join(SRC, f"trades_{wn}_S10.csv.gz"), "rt", encoding="utf-8") as fh:
            orig = fh.read()
        if df_text(trades_df(W, ev, S10), "%.17g") != orig:
            raise SystemExit(f"⛔ N=10 {wn} 交易檔 ≠ resultsPTHpf trades_{wn}_S10")
        J["對帳"][f"{wn}|N=10 逐日 eq/hv/u/pend/nh"] = "逐位元相同"; J["對帳"][f"{wn}|N=10 交易檔（全文）"] = f"逐字相同（{len(S10['buys'])} 筆）"
        # ── 統計
        rows_here = {}
        for N in NLIST:
            for slip in (False, True):
                S = SIM[(N, slip)]
                typ_q = ev["typ"][S["q"]]
                for sg, (x, y) in segp.items():
                    c_, m_, b = M.metrics(W, S["eq"], x, y)
                    row = {"世界": wn, "N": N, "滑價": slip, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_,
                           "比值": AS.ratio(c_, m_), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]),
                           "標籤": AS.label(c_, m_, b), **M.pf_stats(W, S, x, y, typ_q)}
                    nh = S["nh"][x:y + 1]
                    row["空位率"] = float(1 - np.mean(nh) / N); row["有空位日比例"] = float(np.mean(nh < N))
                    row["平均持股<3(退化)"] = bool(np.mean(nh) < M.DEG_HOLD)
                    rows_here[(N, slip, sg)] = row; TAB.append(row)
                    if not slip:
                        DIST.append({"世界": wn, "臂": f"N={N}", "段": sg, **trade_dist(S, x, y)})
        for arm in ("M", "Mslip"):
            S = SM[arm]
            for sg, (x, y) in segp.items():
                c_, m_, b = M.metrics(W, S["eq"], x, y)
                row = {"世界": wn, "N": "主判(前30%全部)", "滑價": arm == "Mslip", "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_,
                       "比值": AS.ratio(c_, m_), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]),
                       "標籤": AS.label(c_, m_, b), **M.pf_stats(W, S, x, y, ev["typ"])}
                TAB.append(row)
                ref = [z for z in PJ["主表"] if z["世界"] == wn and z["臂"] == arm and z["段"] == sg][0]
                bad = [k for k in row if k in ref and k not in ("世界", "段") and not same(row[k], ref[k])]
                if bad:
                    raise SystemExit(f"⛔ 主判 {wn}/{arm}/{sg} 統計 ≠ PTHpf.json：{bad}")
                if arm == "M":
                    DIST.append({"世界": wn, "臂": "主判(前30%全部)", "段": sg, **trade_dist(S, x, y)})
        for sg, (x, y) in segp.items():
            b = bench[sg]
            TAB.append({"世界": wn, "N": "0050", "滑價": False, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": b["cagr"], "回落": b["mdd"],
                        "比值": AS.ratio(b["cagr"], b["mdd"])})
        # N＝10 統計對 PTHpf.json 主表 S10
        for sg in segp:
            ref = [z for z in PJ["主表"] if z["世界"] == wn and z["臂"] == "S10" and z["段"] == sg][0]
            row = rows_here[(10, False, sg)]
            bad = [k for k in row if k in ref and k not in ("世界", "段", "N") and not same(row[k], ref[k])]
            if bad:
                raise SystemExit(f"⛔ N=10 {wn}/{sg} 統計 ≠ PTHpf.json S10：{bad}")
            J["對帳"][f"{wn}|N=10 {sg} 主表統計（{sum(1 for k in row if k in ref)} 欄）"] = "逐位元相同"
        log(f"[統計 {wn}] 完｜{time.time() - T0:.0f}s")
        # ── 存檔
        np.savez_compressed(os.path.join(OUT, f"eq_{wn}.npz"), Bc=W["Bc"], Bo=W["Bo"],
                            **{f"N{N}{'s' if sl else ''}_{k}": SIM[(N, sl)][k] for (N, sl) in SIM for k in ("eq", "hv", "u", "pend", "nh")})
        for (N, sl), S in SIM.items():
            with gzip.open(os.path.join(OUT, f"trades_{wn}_N{N}{'s' if sl else ''}.csv.gz"), "wt", encoding="utf-8") as fh:
                trades_df(W, ev, S).to_csv(fh, index=False, float_format="%.17g")
        # ── 隨機
        o_ = np.lexsort((W["srank"][ev["j"]], ev["e"]))
        M._G[wn] = {"tr": M.slot_tr(ev, False, o_), "n0": W["n0"], "CM": W["CM"], "Bc": W["Bc"], "Bo": W["Bo"], "segp": segp}
        t0 = time.time()
        with Pool(a.procs) as pool:
            RL = pool.map(rand_job, [(wn, N, i) for N in NLIST for i in range(M.NRAND)], chunksize=10)
        set_ns(NS0)
        RDF = pd.DataFrame(RL)
        RDF.to_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), index=False, float_format="%.10g")
        log(f"[隨機 {wn}] {len(RDF)} 列｜{time.time() - t0:.0f}s")
        with gzip.open(os.path.join(SRC, f"random_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
            orig = fh.read()
        if df_text(RDF[RDF["N"] == 10].drop(columns="N"), "%.10g") != orig:
            raise SystemExit(f"⛔ N=10 {wn} 隨機 200 次 ≠ resultsPTHpf random_{wn}")
        J["對帳"][f"{wn}|N=10 隨機 200 次（全文）"] = "逐字相同"
        J["隨機"][wn] = {}
        for N in NLIST:
            R_ = RDF[RDF["N"] == N]
            for sg in segp:
                z = rows_here[(N, False, sg)]
                rr = R_[f"{sg}_年化"] / R_[f"{sg}_回落"].abs()
                labs = Counter(AS.label(c_, m_, bench[sg]) for c_, m_ in zip(R_[f"{sg}_年化"], R_[f"{sg}_回落"]))
                o = {"排序版年化": z["年化"], "排序版比值": z["比值"], "隨機年化p10": float(R_[f"{sg}_年化"].quantile(.1)),
                     "隨機年化中位": float(R_[f"{sg}_年化"].median()), "隨機年化p90": float(R_[f"{sg}_年化"].quantile(.9)),
                     "隨機回落中位": float(R_[f"{sg}_回落"].median()), "隨機比值中位": float(rr.median()),
                     "排序版比值≥隨機的比例": float((rr <= z["比值"]).mean()), "p（隨機比值≥排序版）": float((rr >= z["比值"]).mean()),
                     "p（隨機年化≥排序版）": float((R_[f"{sg}_年化"] >= z["年化"]).mean()), "隨機標籤比例": {k: v / len(R_) for k, v in labs.items()},
                     "隨機平均持股中位": float(R_[f"{sg}_平均持股"].median()), "次數": int(len(R_))}
                J["隨機"][wn][f"N={N}|{sg}"] = o
                if N == 10:
                    ref = PJ["隨機10檔"][wn][sg]
                    chk = [same(o["隨機年化中位"], ref["隨機 年化中位"]), same(o["隨機比值中位"], ref["隨機 比值中位"]),
                           same(o["p（隨機比值≥排序版）"], ref["p（隨機比值 ≥ 10檔版）"]), same(o["隨機年化p10"], ref["隨機 年化 p10／p90"][0]),
                           same(o["隨機年化p90"], ref["隨機 年化 p10／p90"][1])]
                    if not all(chk):
                        raise SystemExit(f"⛔ N=10 {wn}/{sg} 隨機摘要 ≠ PTHpf.json {chk}")
                    J["對帳"][f"{wn}|N=10 {sg} 隨機摘要（中位、p10／p90、比值中位、p）"] = "逐位元相同"
        del W, Z, SIM, SM, ev
        M._G.pop(wn, None)
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "PTHn_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(DIST).to_csv(os.path.join(OUT, "trade_dist.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["表"] = TAB; J["單筆"] = DIST
    # verdict 形式（⛔ 只描述）
    J["verdict形式(描述、不判)"] = {}
    for N in NLIST:
        def lab(sl, sg, wn="主"):
            return [r for r in TAB if r["世界"] == wn and r["N"] == N and r["滑價"] == sl and r["段"] == sg][0]["標籤"]
        L = {"主判探索": lab(False, "探索"), "主判確認": lab(False, "確認"), "滑價探索": lab(True, "探索"), "滑價確認": lab(True, "確認"),
             "主判早年": lab(False, "早年", "早年")}
        J["verdict形式(描述、不判)"][f"N={N}"] = {**L, "researchTurtleS2PF.verdict 形式": TS.verdict(L)}
    log("[表]\n" + TB[["世界", "N", "滑價", "段", "年化", "回落", "比值", "標籤", "平均持股(筆)", "空位率", "換手每年", "成本合計每年(實付)"]].to_string())
    log("[單筆]\n" + pd.DataFrame(DIST)[["世界", "臂", "段", "筆數", "中位", "平均", "勝率", "p10", "p90", "前10%貢獻占比(等權)", "前10%貢獻占比(金額加權)"]].to_string())
    for wn in J["隨機"]:
        for k, o in J["隨機"][wn].items():
            log(f"[隨機 {wn} {k}] {json.dumps(o, ensure_ascii=False, default=float)}")
    log(f"[verdict 形式] {json.dumps(J['verdict形式(描述、不判)'], ensure_ascii=False)}")
    log(f"[對帳] {json.dumps(J['對帳'], ensure_ascii=False)}")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "PTHn.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    run(a, RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()

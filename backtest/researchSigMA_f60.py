# -*- coding: utf-8 -*-
"""PREREG訊號系統均線 敏感度描述：進場加「訊號日收盤 ＞ MA60」過濾（使用者 09-27 20:0x 直接指示；⛔ 不計 N、⛔ 不改已登錄判定）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSigMA_f60.py run|report [--procs 2] [--reps 200] [--fake 1000]

⭐ import researchSigMA（⛔ 不改它）：只多一條進場過濾——訊號日 t（E2 KD／MACD 底背離 ＝ 確認日）收盤 ＞ MA60[t]（嚴格；MA60 ＝ researchRev.ma_fsum、
   同一套有效 K 棒序列；MA60 無值 ⇒ 不過）⇒ t＋1 開盤買；引擎、10 檔、種子、段、成本、出場定義、再進場一字不動
格：探索、確認 × E1、E2 × 跌破 MA10／20／60（穿越）＋ 同進場（過濾後、MA60 列）固定抱 20／60／120；未過濾版的確認段 MA10、MA20 另補跑（並排用）
假訊號 A：確認段只跑「過濾後最好的一格」——用登錄挑法在【探索段】過濾後 6 格裡挑（⛔ 不看確認段挑）
引擎缺口描述臂：股票最後一根有效收盤 L ＜ 段尾、之後資料裡再也沒有成交 ⇒ L＋1 用 L 的收盤強制出場（扣成本）
   做法：該股 L＋1 的開盤價改成 L 的收盤、停損線在 L 放必觸發 ⇒ 引擎在 L＋1 開盤賣；套在確認段 MA60（未過濾、過濾）
輸出 backtest/resultsSigMA/f60/
"""
from __future__ import annotations
import argparse, hashlib, json, os, pickle, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchSigMA as SMA

RS, RV, D, RR, R11, L = SMA.RS, SMA.RV, SMA.D, SMA.RR, SMA.R11, SMA.L
OUT = os.path.join(SMA.OUT, "f60")
TAG = "敏感度描述（使用者 09-27 20:0x；⛔ 不計 N、⛔ 不改已登錄判定）"


def ma60_cache(SIG, mk, cal, path, log):
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    t0 = time.time(); M = {}
    for sid in SIG:
        st = D.load_stock(sid, mk.get(sid, "twse"), cal)
        c = st.df["close"].to_numpy(float); b = np.flatnonzero(np.isfinite(c))
        ma = np.full(len(c), np.nan); ma[b] = RV.ma_fsum(c[b], 60)
        M[sid] = (c.astype(np.float64), ma)
    pickle.dump(M, open(path, "wb"))
    log(f"[MA60] {len(M)} 檔｜{time.time() - t0:.0f}s")
    return M


def filt(SIGM, MA):
    """E 族訊號日只留 收盤 ＞ MA60 的那些。"""
    out = {}
    for sid, S in SIGM.items():
        c, ma = MA[sid]
        S2 = dict(S)
        for k in list(S):
            if k.startswith("E:"):
                d = np.asarray(S[k], int)
                with np.errstate(invalid="ignore"):
                    ok = np.isfinite(ma[d]) & (c[d] > ma[d]) if len(d) else np.zeros(0, bool)
                S2[k] = d[ok]
        out[sid] = S2
    return out


def stopped(VAL, ncal, s1):
    """最後一根有效收盤 L ＜ 段尾、之後再也沒有成交的股票 ⇒ {sid: L}。"""
    out = {}
    for sid, pv in VAL.items():
        v = np.unpackbits(pv)[:ncal].astype(bool); b = np.flatnonzero(v)
        if len(b) and b[-1] < s1:
            out[sid] = int(b[-1])
    return out


def gap_cell(R, s1, cz, oz, STOP):
    sig, kw, reason = SMA.cell_of(R, s1, cz, oz)
    sl = dict(kw["stop_line"]); nforce = 0
    for s, e in zip(sig["sid"], sig["entry_pos"]):
        Lp = STOP.get(s)
        if Lp is None or e > Lp:
            continue
        old = sl.get((s, int(e)))
        if old is None or old[0] > Lp:
            sl[(s, int(e))] = (Lp, np.array([RS.BIG])); reason[(s, int(e))] = ("停止交易強制出場", Lp); nforce += 1
    return (sig, {**kw, "stop_line": sl}, reason, None), nforce


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["run", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=1000)
    a = ap.parse_args(); os.makedirs(OUT, exist_ok=True)
    if a.mode == "report":
        report(); return
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    HERE = SMA.HERE
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("researchSigMA_f60.py", "researchSigMA.py", "researchSig.py", "researchRev.py")}
    log(f"===== researchSigMA_f60 run procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{src} =====")
    S = {"性質": TAG, "程式": src}
    RR.use_snapshot()
    cal, mon, elig, mk, SIG, VAL = SMA.setup(a, log)
    ncal = len(cal)
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in RS.SEG.items()}
    M = SMA.ma_cache(SIG, mk, cal, a.procs, os.path.join(SMA.OUT, "ma_cache.pkl"), log)
    SIGM = {sid: {**S_, **M.get(sid, {})} for sid, S_ in SIG.items()}
    MA = ma60_cache(SIG, mk, cal, os.path.join(OUT, "ma60_cache.pkl"), log)
    SIGF = filt(SIGM, MA)
    cz, oz = RR.load_prices(sorted(SIGM), cal, mk, "branch")
    bench = RR.load_bench(cal); B50 = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    CELLS = {}
    SMA._init({"cal": cal, "cz": cz, "oz": oz, "ncal": ncal, "CELLS": CELLS, "VAL": VAL})
    OUTC = {}; ROWS = {}; FR = {}
    # ── 列、過濾比例
    for seg, (s0, s1) in P.items():
        for E in ("E1", "E2"):
            for xo in SMA.MAIN_X:
                R0, _, _ = SMA.rows_for(SIGM, elig, mon, E, xo, s0, s1)
                R1, _, _ = SMA.rows_for(SIGF, elig, mon, E, xo, s0, s1)
                ROWS[("過濾", seg, E, xo)] = R1.reset_index(drop=True); ROWS[("未過濾", seg, E, xo)] = R0.reset_index(drop=True)
                FR[f"{seg}|{E}|{xo}"] = {"未過濾列": int(len(R0)), "過濾後列": int(len(R1)), "過濾掉比例": float(1 - len(R1) / max(1, len(R0)))}
    S["過濾比例"] = FR; S["0050同段"] = B50
    for seg in ("探索", "確認"):
        s0, s1 = P[seg]; keys = []
        for E in ("E1", "E2"):
            for xo in SMA.MAIN_X:
                k = ("過濾", seg, E, xo); CELLS[k] = (*SMA.cell_of(ROWS[k], s1, cz, oz), None); keys.append(k)
                if seg == "確認" and xo != "MA60":
                    k0 = ("未過濾", seg, E, xo); CELLS[k0] = (*SMA.cell_of(ROWS[k0], s1, cz, oz), None); keys.append(k0)
            for H in (20, 60, 120):
                k = ("過濾", seg, E, f"H{H}"); CELLS[k] = (*SMA.fixed_cell(ROWS[("過濾", seg, E, "MA60")], H, s1, cz, oz), None); keys.append(k)
        res = SMA.run_cells(keys, s0, s1, a.reps, a.procs, f"{seg}", log)
        for k in keys:
            OUTC[k] = SMA.agg_ma(res[k], B50[seg])
    # ── 並排：未過濾版（resultsSigMA/cells.csv 已有的直接讀；確認段 MA10／MA20 本件補跑）
    C0 = pd.read_csv(os.path.join(SMA.OUT, "cells.csv"), float_precision="round_trip")
    side = []
    for k, c in OUTC.items():
        if k[0] != "過濾":
            continue
        _, seg, E, xo = k
        q = C0[(C0["段"] == seg) & (C0["E"] == E) & (C0["出場"] == xo)]
        if len(q):
            u = {"cagr_med": float(q.iloc[0]["cagr_med"]), "mdd_med": float(q.iloc[0]["mdd_med"]), "ratio": float(q.iloc[0]["ratio"]), "label": q.iloc[0]["label"], "來源": "resultsSigMA/cells.csv"}
        elif ("未過濾", seg, E, xo) in OUTC:
            u0 = OUTC[("未過濾", seg, E, xo)]; u = {"cagr_med": u0["cagr_med"], "mdd_med": u0["mdd_med"], "ratio": u0["ratio"], "label": u0["label"], "來源": "本件補跑"}
        else:
            continue
        side.append({"段": seg, "E": E, "出場": xo, "過濾_年化": c["cagr_med"], "過濾_回落": c["mdd_med"], "過濾_比值": c["ratio"], "過濾_標籤": c["label"],
                     "未過濾_年化": u["cagr_med"], "未過濾_回落": u["mdd_med"], "未過濾_比值": u["ratio"], "未過濾_標籤": u["label"],
                     "年化差_點": (c["cagr_med"] - u["cagr_med"]) * 100, "回落差_點": (c["mdd_med"] - u["mdd_med"]) * 100, "未過濾來源": u["來源"]})
    pd.DataFrame(side).to_csv(os.path.join(OUT, "side_by_side.csv"), index=False)
    # ── 假訊號 A：探索段過濾後 6 格用登錄挑法挑最好的一格 ⇒ 其確認段
    cands = [((E, xo), OUTC[("過濾", "探索", E, xo)]) for E in ("E1", "E2") for xo in SMA.MAIN_X]
    bestE, bestX = RS.pick(cands)
    s0, s1 = P["確認"]; kb = ("過濾", "確認", bestE, bestX)
    cA = SMA.fake_a(ROWS[kb], OUTC[kb]["_hold_pool"], s0, s1, a.fake, a.procs)
    m = OUTC[kb]["cagr_med"]
    S["假訊號A"] = {"格": f"確認|{bestE}|{bestX}（探索段挑法選出）", "本格年化中位": m, "隨機出場_中位年化": float(np.median(cA)),
                  "本格年化贏過的比例": float((m > cA).mean()), "p（隨機 ≥ 本格）": float((cA >= m).mean()), "次數": a.fake}
    log(f"[假訊號 A] {S['假訊號A']}")
    # ── 沒停損那批（nostand）
    NSB = {}
    MAc60 = {}
    for k, c in OUTC.items():
        if k[0] == "過濾" and k[3] in SMA.MAIN_X:
            n = int(k[3][2:]); s1_ = P[k[1]][1]
            MAc = {}
            for s_ in {e[0] for e in c["_endlist"]}:
                cc, _ = MA[s_]; b = np.flatnonzero(np.isfinite(cc))
                ma = np.full(ncal, np.nan); ma[b] = RV.ma_fsum(cc[b], n); MAc[s_] = (cc, pd.Series(ma).ffill().to_numpy())
            NSB["|".join(k[1:])] = SMA.nostand(c["_endlist"], s1_, cz, MAc, a.reps)
    S["一直沒站上就不賣_過濾版"] = NSB
    # ── 引擎缺口描述臂（確認段 MA60：未過濾、過濾）
    s0, s1 = P["確認"]
    STOP = stopped(VAL, ncal, s1)
    off = RV.TR.load_official()
    oz2 = dict(oz)
    for s_, Lp in STOP.items():
        if s_ in oz2 and Lp + 1 < ncal:
            a_ = np.array(oz2[s_], dtype=np.float32, copy=True); a_[Lp + 1] = cz[s_][Lp]; oz2[s_] = a_
    gk = []; GN = {}
    for ver, key in (("未過濾", ("未過濾", "確認")), ("過濾", ("過濾", "確認"))):
        for E in ("E1", "E2"):
            R = ROWS[(ver, "確認", E, "MA60")]
            cell, nf = gap_cell(R, s1, cz, oz2, STOP)
            k = ("缺口臂", ver, E, "MA60"); CELLS[k] = cell; gk.append(k); GN["|".join(k)] = nf
            if ver == "未過濾" and ("未過濾", "確認", E, "MA60") not in OUTC:
                k0 = ("未過濾", "確認", E, "MA60"); CELLS[k0] = (*SMA.cell_of(R, s1, cz, oz), None)
    RS._G["oz"] = oz2
    resg = SMA.run_cells(gk, s0, s1, a.reps, a.procs, "缺口臂", log)
    RS._G["oz"] = oz
    k0s = [("未過濾", "確認", E, "MA60") for E in ("E1", "E2")]
    res0 = SMA.run_cells(k0s, s0, s1, a.reps, a.procs, "缺口臂對照（未過濾原樣）", log)
    GAP = {}
    for k in gk:
        c = SMA.agg_ma(resg[k], B50["確認"])
        base = SMA.agg_ma(res0[("未過濾", "確認", k[2], "MA60")], B50["確認"]) if k[1] == "未過濾" else OUTC[("過濾", "確認", k[2], "MA60")]
        forced = int(sum(x["why"].get("停止交易強制出場", 0) for x in resg[k])) / a.reps
        GAP["|".join(k)] = {"強制出場後_年化": c["cagr_med"], "強制出場後_回落": c["mdd_med"], "原樣_年化": base["cagr_med"], "原樣_回落": base["mdd_med"],
                           "年化差_點": (c["cagr_med"] - base["cagr_med"]) * 100, "回落差_點": (c["mdd_med"] - base["mdd_med"]) * 100,
                           "可能受影響的列": GN["|".join(k)], "實際強制出場_每顆筆數": forced}
    ds_all = {}
    rows_sids = set(ROWS[("未過濾", "確認", "E1", "MA60")]["sid"]) | set(ROWS[("未過濾", "確認", "E2", "MA60")]["sid"])
    for s_, Lp in sorted(STOP.items()):
        if s_ in rows_sids and Lp >= s0:
            tb = RV.TR.one(s_, cal); ds = RV.TR.delist_status({s_: tb}, cal, official=off).get(s_)
            ds_all[s_] = {"最後有效收盤日": str(cal[Lp].date()), "delist 狀態": ds["status"] if ds else None}
    S["引擎缺口"] = {"做法": "最後有效收盤 L ＜ 段尾、之後資料裡再也沒有成交 ⇒ L＋1 開盤價改成 L 收盤、停損線在 L 必觸發 ⇒ L＋1 用最後收盤價強制出場（扣成本）",
                   "確認段內停止交易且出現在進場列的股票": ds_all, "結果": GAP}
    log(f"[引擎缺口] 股票 {len(ds_all)} 檔｜{GAP}")
    # ── 輸出
    rows = [{"版": k[0], "段": k[1], "E": k[2], "出場": k[3], **{kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in c.items() if not kk.startswith("_")}}
            for k, c in OUTC.items()]
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "cells.csv"), index=False)
    for E in ("E1", "E2"):
        ROWS[("過濾", "確認", E, "MA60")].to_csv(os.path.join(OUT, f"rows_filtered_confirm_{E}.csv.gz"), index=False)
        ROWS[("未過濾", "確認", E, "MA60")].to_csv(os.path.join(OUT, f"rows_unfiltered_confirm_{E}.csv.gz"), index=False)
    S["秒"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完成] {time.time() - t00:.0f}s")
    report()


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv")); SB = pd.read_csv(os.path.join(OUT, "side_by_side.csv"))
    p_ = SMA._p
    F = C[C["版"] == "過濾"]
    conf = SB[(SB["段"] == "確認")]
    best = conf.sort_values("過濾_比值", ascending=False).iloc[0]
    L_ = [f"# 訊號系統均線：進場加「訊號日收盤 ＞ 60 日線」過濾（⚠ {TAG}）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。其餘一字不動（引擎、10 檔、種子、段、成本、出場、再進場）。", ""]
    cm = conf[conf["出場"].str.startswith("MA")]
    nq = int((cm["過濾_標籤"].isin(["合格", "另列"])).sum())
    L_.append(f"**結論（描述、⛔ 不當判定）：加 60 日線過濾後，確認段均線出場 6 格{'有 ' + str(nq) + ' 格對 0050 為合格／另列' if nq else '仍全部沒贏 0050'}；"
              f"年化相對未過濾版 {cm['年化差_點'].min():+.1f}～{cm['年化差_點'].max():+.1f} 點（E2 過濾掉約七成候選，改善最多）。**")
    L_ += ["", f"確認段 0050：年化 {p_(S['0050同段']['確認']['cagr'])}、回落 {p_(S['0050同段']['確認']['mdd'])}；探索段 0050：{p_(S['0050同段']['探索']['cagr'])}／{p_(S['0050同段']['探索']['mdd'])}", "",
           "| 確認段 | 過濾後 年化／回落（標籤） | 未過濾 年化／回落（標籤） | 年化差（點） | 回落差（點） | 過濾掉的候選 |", "|---|---|---|---|---|---|"]
    for r in conf.itertuples():
        fr = S["過濾比例"].get(f"確認|{r.E}|{r.出場}", S["過濾比例"][f"確認|{r.E}|MA60"])["過濾掉比例"]
        L_.append(f"| {r.E} {SMA.XN.get(r.出場, '固定抱 ' + r.出場[1:] + ' 天')} | {p_(r.過濾_年化)}／{p_(r.過濾_回落)}（{r.過濾_標籤}） | {p_(r.未過濾_年化)}／{p_(r.未過濾_回落)}（{r.未過濾_標籤}） | "
                  f"{r.年化差_點:+.2f} | {r.回落差_點:+.2f} | {fr:.1%} |")
    L_ += ["", "## 探索段並排", "", "| 探索段 | 過濾後 年化／回落（標籤） | 未過濾 年化／回落（標籤） | 年化差（點） | 過濾掉的候選 |", "|---|---|---|---|---|"]
    for r in SB[SB["段"] == "探索"].itertuples():
        fr = S["過濾比例"].get(f"探索|{r.E}|{r.出場}", S["過濾比例"][f"探索|{r.E}|MA60"])["過濾掉比例"]
        L_.append(f"| {r.E} {SMA.XN.get(r.出場, '固定抱 ' + r.出場[1:] + ' 天')} | {p_(r.過濾_年化)}／{p_(r.過濾_回落)}（{r.過濾_標籤}） | {p_(r.未過濾_年化)}／{p_(r.未過濾_回落)}（{r.未過濾_標籤}） | {r.年化差_點:+.2f} | {fr:.1%} |")
    L_ += ["", "## 過濾後各格（200 顆）", "", "| 段 | E | 出場 | 年化中位 | 回落中位 | 比值 | 對 0050（描述） | 每顆交易 | 勝率 | 平均持有 | 段尾未出場比例 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in F.itertuples():
        xn = SMA.XN.get(r.出場, f"固定抱 {r.出場[1:]} 天")
        L_.append(f"| {r.段} | {r.E} | {xn} | {p_(r.cagr_med)} | {p_(r.mdd_med)} | {r.ratio:.3f} | {r.label} | {r.交易筆_每顆平均:.1f} | {r.勝率:.3f} | {r.持有天數_平均:.1f} | {r.段尾未出場比例:.3f} |")
    L_ += ["", f"## 假訊號 A（確認段、1,000 次；格用登錄挑法在探索段過濾後 6 格裡挑）", "", f"- {S['假訊號A']}", "",
           "## 沒停損那批（過濾版；格式同 researchSigMA nostand）", ""] + [f"- {k}：{json.dumps(v, ensure_ascii=False)}" for k, v in S["一直沒站上就不賣_過濾版"].items()]
    G = S["引擎缺口"]
    L_ += ["", "## 引擎缺口描述臂：停止交易後用最後收盤強制出場（扣成本）", "", f"- 做法：{G['做法']}",
           f"- 確認段內停止交易、且出現在進場列的股票（{len(G['確認段內停止交易且出現在進場列的股票'])} 檔）：{json.dumps(G['確認段內停止交易且出現在進場列的股票'], ensure_ascii=False)}", "",
           "| 格（確認段 MA60） | 原樣 年化／回落 | 強制出場後 年化／回落 | 年化差（點） | 回落差（點） | 實際強制出場（每顆） |", "|---|---|---|---|---|---|"]
    for k, v in G["結果"].items():
        L_.append(f"| {k} | {p_(v['原樣_年化'])}／{p_(v['原樣_回落'])} | {p_(v['強制出場後_年化'])}／{p_(v['強制出場後_回落'])} | {v['年化差_點']:+.2f} | {v['回落差_點']:+.2f} | {v['實際強制出場_每顆筆數']:.2f} |")
    L_ += ["", f"程式：{S['程式']}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")


if __name__ == "__main__":
    main()

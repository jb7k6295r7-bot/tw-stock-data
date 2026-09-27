# -*- coding: utf-8 -*-
"""稽核 ② 7（seq1／seq3 §二 第 7 列；裁定 seq257 順 7）：既有部位出場（跌破破壞價／MA20／MA60）判定量改「續抱 − 賣掉改買 0050」＋基準②。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_7.py [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_7_check.py

原件：researchExit.py（回測 PREREG出場訊號，bd3fa4d69f）。判定量 E ＝ 續抱 H 天原始報酬 R_H 平均 ⇒ 6 格（甲乙丙 × H20／H60）無結果③ ⇒「不構成賣出理由」。
問題（稽核 K4）：R_H 混大盤漂移；未控前 20 日。
═══ ① 用既有數字重判（⛔ 不重跑事件；讀 resultsExit/events_kept.csv.gz）═══
  原件已有描述臂「換成 0050 − 續抱」（B5 對照②：0050 還原收盤(s＋H−1)÷還原開盤(s) − 1 − 0.1425%）⇒ 新判定量 Y ＝ 續抱 − 換 0050 ＝ −(換0050減續抱)
  CI、分群（H20 曆月、H60 60 日區段 blk60）、n_eff、出口照原件 B1／B2；結果③（Y＜0、CI 不含 0）⇒「續抱比賣掉換 0050 差」
  K3 並報：換 0050 實際多付的是 ETF 一次來回 0.385%（買 0.1425%＋賣 0.1425%＋稅 0.1%），原件只扣 0.1425% ⇒ Y_c ＝ Y ＋（0.385% − 0.1425%）；
     「賣掉換 0050 可執行」＝ Y_c 的 CI 上緣 ＜ 0（⚠ 兩邊都要賣這檔股票一次，股票賣出成本兩邊相同互抵）
═══ ② 基準②（⭐ 開跑前寫死；本線讀法）═══
  同一個 T：十分位母體 ＝ gate3 中 T 有效 K 棒、前 20 日報酬（avgdown.r20_cal）可算者（含事件股），avgdown.deciles（股票代號序）；
  配對股 ＝ 與事件股同十分位、非事件股、T＋1 可賣（有成交、開盤有效、非開盤跌停）、[T−60, T＋H] 無硬斷點（researchH2.brk 同式）、R 可算；
  配對股 R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（s＝T＋1、終點 s＋H−1 ＝ T＋H；停牌跨終點 ⇒ 之前最後一根收盤）；
  X2 ＝ 事件 R_H − 配對股 R 等權平均（成本兩邊相同）；判法同 ①；結果③ ⇒「跌破後比前 20 日漲跌相同的股票差」
  沒配對 ⇒ 不進此項、件數必報；H5／H10 同法、描述；H120 依構造不可判定、只描述平均
  「穩」：①② 在三訊號 × 兩個 H 都同出口同結果才寫
  stop_force：原件 delist on（下市了結）＝ 停止交易強制出場：開；單筆層、T＋H ≤ 窗尾 ⇒ 沒有資料尾截斷
輸出 backtest/resultsAudit2/7/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                               # ⭐ D.DATA ⇒ 快照、chdir ⇒ repo（原件同）
D, TR, UG, R11 = H2.D, H2.TR, H2.UG, H2.R
import researchM_freq as RF
from backtest import avgdown as AV

OUT = "backtest/resultsAudit2/7"
SRC = "backtest/resultsExit"
HJ = (20, 60)
HA = (5, 10, 20, 60, 120)
ETF_RT, BUY = 0.00385, 0.001425
RULE_NM = {"甲": "收盤跌破破壞價", "乙": "收盤跌破 MA20", "丙": "收盤跌破 MA60"}
_G: dict = {}


def _init(cal, off):
    _G.update(cal=cal, off=off)


def load(args):
    sid, market = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    return {"sid": sid, "o": o, "cff": pd.Series(c).ffill().to_numpy(), "valid": valid,
            "sell1": np.asarray(tb["trd"], bool) & np.isfinite(o) & ~np.asarray(tb["dn_o"], bool),
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32), "r20": AV.r20_cal(c, bars)}


def judge(x, g):
    x = np.asarray(x, float); g = np.asarray(g); ok = np.isfinite(x); x, g = x[ok], g[ok]
    if len(x) < 2:
        return {"n": int(len(x))}
    cs = R11.cl_stats(x, g)
    ne = int(min(len(x), cs["months"]))
    ex = "出口①" if ne < 30 else ("出口②" if ne < 100 else "出口③")
    rs = "樣本不足以分辨" if ne < 30 else ("結果①" if cs["lo"] <= 0 <= cs["hi"] else ("結果②" if cs["mean"] > 0 else "結果③"))
    return {"n": int(len(x)), "mean": float(cs["mean"]), "lo": float(cs["lo"]), "hi": float(cs["hi"]), "群數": int(cs["months"]), "n_eff": ne, "出口": ex, "結果": rs}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_7（出場訊號：續抱 − 換 0050＋基準②）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    E = pd.read_csv(os.path.join(SRC, "events_kept.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    E = E[E["rule"] == "close"].reset_index(drop=True)
    Sm = json.load(open(os.path.join(SRC, "summary.json"), encoding="utf-8"))
    S = {"原件": "researchExit.py bd3fa4d69f（回測 PREREG出場訊號）", "閘": {}, "結果": {}}
    # 閘：原件 E 與「換0050減續抱」平均重現
    g_ok = {}
    for g in "甲乙丙":
        for H in HJ:
            x = E[(E["g"] == g) & (E["H"] == H)]
            grp = x["month"] if H == 20 else x["blk60"]
            j = judge(x["R"], grp)
            g_ok[f"{g}_H{H}"] = {"n": j["n"], "E": j["mean"], "結果": j["結果"]}
    S["閘"]["原件 6 格 n／E／結果（由 events_kept 重算）"] = g_ok
    log(f"[閘] {g_ok}")
    # ── 價格矩陣（基準②）
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(H2.W0)))
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    off = TR.load_official()
    with Pool(a.procs, initializer=_init, initargs=(cal, off)) as pool:
        L = [r for r in pool.map(load, list(zip(U["stock_id"], U["market"])), chunksize=16) if r is not None]
    sids = [r["sid"] for r in L]; ix = {s: i for i, s in enumerate(sids)}
    O = np.column_stack([r["o"] for r in L]); CF = np.column_stack([r["cff"] for r in L]); V = np.column_stack([r["valid"] for r in L])
    SELL1 = np.column_stack([r["sell1"] for r in L]); CP = np.column_stack([r["cs_pb"] for r in L]); CG = np.column_stack([r["cs_g5"] for r in L])
    R20 = np.column_stack([r["r20"] for r in L]); del L
    log(f"[讀檔] gate3 {len(sids):,}")
    X2 = np.full(len(E), np.nan); NP = np.zeros(len(E), np.int32); why = {}
    for H in HA:
        G = np.full((n, len(sids)), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            G[:n - H] = CF[H:] / np.where(np.isfinite(O[1:n - H + 1]) & (O[1:n - H + 1] > 0), O[1:n - H + 1], np.nan) - 1.0
        Tr = np.arange(61, n - H)
        HB = np.ones((n, len(sids)), bool)
        a4 = Tr - 60 + 4
        HB[Tr] = ((CP[Tr + H] - CP[Tr - 61]) > 0) | ((CG[Tr + H] - CG[a4 - 1]) > 0)
        cache = {}
        for g in "甲乙丙":
            sel = np.flatnonzero(((E["g"] == g) & (E["H"] == H)).to_numpy())
            evday = {}
            for i in sel:
                evday.setdefault(int(E.at[i, "T"]), set()).add(ix.get(E.at[i, "sid"], -1))
            wk = {"r20不可算": 0, "無配對": 0, "不在 gate3 矩陣": 0}
            for i in sel:
                T = int(E.at[i, "T"]); s = ix.get(E.at[i, "sid"], -1)
                if s < 0:
                    wk["不在 gate3 矩陣"] += 1; continue
                if not np.isfinite(R20[T, s]):
                    wk["r20不可算"] += 1; continue
                if T not in cache:
                    base = V[T] & np.isfinite(R20[T])
                    dec = AV.deciles(np.where(base, R20[T], np.nan))
                    cache[T] = dec
                dec = cache[T]
                ev = np.zeros(len(sids), bool); ev[list(evday[T] - {-1})] = True
                peer = (dec == dec[s]) & ~ev & SELL1[T + 1] & ~HB[T] & np.isfinite(G[T])
                if not peer.any():
                    wk["無配對"] += 1; continue
                X2[i] = float(E.at[i, "R"]) - float(G[T, peer].mean()); NP[i] = int(peer.sum())
            why[f"{g}_H{H}"] = wk
        log(f"[基準② H{H}] 沒進 { {k: v for k, v in why.items() if k.endswith(f'H{H}')} }")
    E["X2"] = X2; E["配對股數"] = NP
    E["Y"] = -E["換0050減續抱"]; E["Y_c"] = E["Y"] + (ETF_RT - BUY)
    E[["g", "H", "sid", "T", "T_date", "month", "blk60", "R", "換0050減續抱", "Y", "Y_c", "X2", "配對股數"]].to_csv(
        os.path.join(OUT, "events.csv.gz"), index=False, float_format="%.17g")
    S["基準②沒進"] = why
    for g in "甲乙丙":
        for H in HA:
            x = E[(E["g"] == g) & (E["H"] == H)]
            if H == 120:
                S["結果"][f"{g}_H{H}"] = {"n": int(len(x)), "Y 平均": float(x["Y"].mean()), "X2 平均": float(x["X2"].mean()), "註": "依構造不可判定（描述）"}
                continue
            grp = x["blk60"] if H == 60 else x["month"]
            cell = {"原件 E（續抱原始報酬）": judge(x["R"], grp), "① Y 續抱 − 換 0050（原件口徑，0050 多付 0.1425%）": judge(x["Y"], grp),
                    "① Y_c 續抱 − 換 0050（0050 付一次來回 0.385%）": judge(x["Y_c"], grp), "② X2 續抱 − 基準②": judge(x["X2"], grp),
                    "判定格": H in HJ}
            yc = cell["① Y_c 續抱 − 換 0050（0050 付一次來回 0.385%）"]
            cell["K3 賣掉換 0050 可執行（Y_c CI 上緣 ＜ 0）"] = bool(yc.get("hi", 1) < 0)
            yr = x["year"].to_numpy()
            cell["逐年（Y／X2）"] = {int(y): [float(x["Y"][yr == y].mean()), float(np.nanmean(x["X2"][yr == y]))] for y in sorted(set(yr))}
            S["結果"][f"{g}_H{H}"] = cell
            log(f"[{g} H{H}] E {cell['原件 E（續抱原始報酬）']['mean']:+.3%} {cell['原件 E（續抱原始報酬）']['結果']}｜Y {cell['① Y 續抱 − 換 0050（原件口徑，0050 多付 0.1425%）']['mean']:+.3%} "
                f"{cell['① Y 續抱 − 換 0050（原件口徑，0050 多付 0.1425%）']['結果']}｜Y_c {yc['mean']:+.3%} [{yc['lo']:+.3%}, {yc['hi']:+.3%}] {yc['結果']}｜"
                f"X2 {cell['② X2 續抱 − 基準②']['mean']:+.3%} [{cell['② X2 續抱 − 基準②']['lo']:+.3%}, {cell['② X2 續抱 − 基準②']['hi']:+.3%}] {cell['② X2 續抱 − 基準②']['結果']}")
    for k in ("① Y 續抱 − 換 0050（原件口徑，0050 多付 0.1425%）", "② X2 續抱 − 基準②"):
        S[f"穩_{k[:2]}（三訊號 × H20／H60 同出口同結果）"] = len({(S["結果"][f"{g}_H{H}"][k]["出口"], S["結果"][f"{g}_H{H}"][k]["結果"]) for g in "甲乙丙" for H in HJ}) == 1
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

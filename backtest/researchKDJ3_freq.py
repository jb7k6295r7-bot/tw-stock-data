# -*- coding: utf-8 -*-
"""PREREG KDJ三週期共振 seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha 94378c24e2a8af54，2026-10-20 18:47；裁定 seq394 第 3 題、
seq398 發號；N_前段 ＋1；標籤照常）——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日、股月比例、與日線 KD 的退化比例；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、
   出場日（seq366 乾跑）。用到的價格只有 ≤ T 的日線高低收（及由其組成、在 T 收盤前已收完的週 K、月 K）；T＋1 只判「有沒有成交、開盤是否鎖漲停」。
⛔ 不 commit、不改既有程式與結果夾；researchWeekly（kd、weekly_bars、weeks_of）、researchWR_freq（base、kd_daily、willr、detect_w、detect_k、
   dedup_then_status、st_next_open、run_freq）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKDJ3_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKDJ3_freq_check
輸出 backtest/resultsKDJ3/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格（⭐ 判定只有 J；其餘只報、⛔ 不疊加）：
  J   判定格：日線 K 上穿 D（K[T−1] ≤ D[T−1] ∧ K[T] ＞ D[T]）∧ K[T−1] ＜ 20 ∧ 最近已收完週 K ＜ 20 ∧ 最近已收完月 K ＜ 20
  D   退化分母（描述）：只有日線條件（＝「日線 KD 低檔金叉（K ＜ 20 金叉）」）
  較嚴（只報）：J_週月KD皆<20（週、月 K 與 D 都 ＜ 20）、J_週已金叉（週 K ＞ 週 D）、J_月已金叉、J_J<0（日線 J[T−1] ＜ 0）
  另一讀法（只報）：J_週月暖機9根（週、月 KD 從段內第 9 根起就判，見 K4）
  單條（只報）：D+週（只加週 K ＜ 20）、D+月（只加月 K ＜ 20）

═══ 讀法（K 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 K1 世界、母體、壞根、500 張閘、剔除、段、n_eff ＝ researchWR_freq R1、R7、R10 原樣（base、st_next_open、run_freq 直接呼叫）：
    閘外(500張/pit) → 壞根(T) → 壞根(T+1) → T+1無成交 → T+1開盤鎖漲停。
 K2 KD(9,3,3) ＝ researchWeekly.kd 原樣（RSV ＝ (c − 9 根最低 low) ÷ (9 根最高 high − 9 根最低 low) × 100、區間 0 ⇒ 50；K ＝ ⅔K前 ＋ ⅓RSV、
    D ＝ ⅔D前 ＋ ⅓K、起始 K ＝ D ＝ 50；還原 high／low／close）。日線 ＝ researchWR_freq.kd_daily（每個無壞 K 棒段各自起算）。
    J ＝ 3K − 2D（只描述）。★ 金叉當天 J[T] ＝ K ＋ 2(K − D) ＞ K ≥ 0 ⇒「J ＜ 0」取前一日 J[T−1]〔另一讀法：週或月 J〕。
 K3 週 K ＝ researchWeekly.weeks_of（週一起算的日曆週）＋ weekly_bars（有效 K 棒的週開高低收）；月 K ＝ 同一支 weekly_bars 套日曆月分組
    （本支 months_of，與 weeks_of 同式）。⭐「已收完」：T 是該日曆週（月）在交易日曆上的最後一個交易日 ⇒ T 所在週（月）在 T 收盤已收完、可用；
    否則用前一個有 K 的週（月）。（交易日曆的週末／月底是事先已知的休市表，不是前視。）
 K4 不跨壞根（登錄 §四「壞根後重新起算 KD，前 20 根不判」）：
    日線：kd_daily 每段重算；★ 段內位置 ≥ 20 才判（登錄逐字；%R 件 KD_WARM 30 是另一件的讀法，本件照登錄），T−1 同段。
    週／月：壞 K 棒 q 若是其週（月）第一根 ⇒ 該週（月）起新段；否則該週（月）K 混了斷點前後 ⇒ 作廢，下一週（月）起新段；
    每段 researchWeekly.kd 重算；★ 段內位置 ≥ 20 才判（月線 ⇒ 壞根後 20 個月內不判；登錄逐字）〔另一讀法 J_週月暖機9根：段內位置 ≥ 8，
    即 KD 第一個有值的根〕；另要求所用週（月）K 的第一根有效 K 棒之後到 T 之間沒有壞 K 棒（三個週期同段）。
 K5 同檔 20 日內重複觸發只算第一筆 ＝ researchWR_freq.dedup_then_status（先合併、再剔除；有效 K 棒序號）〔另一讀法：被剔除者不開合併窗〕；每格各自合併。
 K6 seq377 退化檢查（登錄 §三、裁定 seq398 核）：各段 J 保留數 ÷ D 保留數；≥ 90% ⇒ 標【與日線 KD 退化】、判定改寫「等於日線 KD」、停在乾跑。
    另報偵測（合併前）比例。
 K7 股月比例（登錄 §三）：段內每檔已收完、K 可判（K4）的月 K 中 K ＜ 20 的比例（不套 500 張閘；月 K 歸屬於月內最後一根有效 K 棒的日曆位置）；週同式。
 K8 重疊（件數 ÷ 本格保留數）：日線 KD 低檔金叉（%R 件 K 格：K[T] ≤ 30 金叉、暖機 30，researchWR_freq.detect_k）、Williams %R（%R 件 W 格，
    researchWR_freq.detect_w）——兩者都套 %R 件自己的 20 日合併與剔除後取保留集合；同檔同日與 ±20 根兩口徑。
    急跌錯殺、大盤大跌後買什麼：無現成逐筆事件檔可直接比 ⇒ 本乾跑未做（待正式跑）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WR                  # noqa: E402  （⛔ 只 import）
from backtest import researchWeekly as RW                   # noqa: E402  kd、weekly_bars（⛔ 只 import）

REG_SHA = "94378c24e2a8af54"
OUT = "backtest/resultsKDJ3/freq"
TH = 20.0
WARM = 20
WARM_ALT = 8
DEDUP = 20
OVW = 20
DEG = 0.90
CELLS = {
    "J": "判定格：日線 K 上穿 D ∧ K[T−1]<20 ∧ 最近收完週 K<20 ∧ 最近收完月 K<20",
    "D": "退化分母（描述）：只有日線 K[T−1]<20 金叉",
    "J_週月KD皆<20": "較嚴（只報）：週、月 K 與 D 都 <20",
    "J_週已金叉": "較嚴（只報）：最近收完週 K>D",
    "J_月已金叉": "較嚴（只報）：最近收完月 K>D",
    "J_J<0": "較嚴（只報）：日線 J[T−1]=3K−2D<0",
    "J_週月暖機9根": "另一讀法（只報）：週月 KD 段內第 9 根起就判",
    "D+週": "單條（只報）：日線 ∧ 週 K<20",
    "D+月": "單條（只報）：日線 ∧ 月 K<20",
}
PRED = {
    "J": lambda f: f["w"] and f["m"],
    "D": lambda f: True,
    "J_週月KD皆<20": lambda f: f["w"] and f["m"] and f["wD"] and f["mD"],
    "J_週已金叉": lambda f: f["w"] and f["m"] and f["wx"],
    "J_月已金叉": lambda f: f["w"] and f["m"] and f["mx"],
    "J_J<0": lambda f: f["w"] and f["m"] and f["jneg"],
    "J_週月暖機9根": lambda f: f["w9"] and f["m9"],
    "D+週": lambda f: f["w"],
    "D+月": lambda f: f["m"],
}


def months_of(cal):
    """日曆月（weeks_of 同式）：回 每日月號 mo、每月第一日 mf、最後一日 ml。"""
    m = np.asarray(cal.year) * 12 + np.asarray(cal.month)
    mo = pd.factorize(m)[0]
    nm = int(mo.max()) + 1
    mf = np.full(nm, -1); ml = np.full(nm, -1)
    for i, w in enumerate(mo):
        if mf[w] < 0:
            mf[w] = i
        ml[w] = i
    return mo, mf, ml


def period_kd(jq, PH, PL, PC, bad):
    """K4：週（月）K 的分段 KD。jq[q] ＝ 第 q 根有效 K 棒所屬週（月）K 序號。回 K、D、段內位置（作廢 ⇒ −1）、每個週（月）K 的第一根 q。"""
    npb = len(PC)
    K = np.full(npb, np.nan); Dd = np.full(npb, np.nan); pos = np.full(npb, -1, np.int64)
    if npb == 0:
        return K, Dd, pos, np.zeros(0, np.int64)
    _, fq = np.unique(jq, return_index=True)
    cut = np.zeros(npb + 1, bool); cut[0] = True; inval = np.zeros(npb, bool)
    for q in np.flatnonzero(bad):
        if q == 0:
            continue
        j = jq[q]
        if q == fq[j]:
            cut[j] = True
        else:
            inval[j] = True; cut[j] = True; cut[j + 1] = True
    starts = np.flatnonzero(cut[:npb]); ends = np.r_[starts[1:], npb]
    for s, e in zip(starts, ends):
        if inval[s]:
            continue
        k_, d_ = RW.kd(PC[s:e], PH[s:e], PL[s:e])
        K[s:e] = k_; Dd[s:e] = d_; pos[s:e] = np.arange(e - s)
    return K, Dd, pos, fq


def stock_job(a):
    wn, sid = a
    X = WR.base(wn, sid)
    if X is None:
        return sid, None
    W = X["W"]; cal = X["cal"]; n0 = X["n0"]
    if "mo" not in W:                                      # 月號（K3）：每個工作行程算一次
        W["mo"], W["mf"], W["ml"] = months_of(cal)
    df = X["df"]; idx = X["idx"]; nb = X["nb"]; bad = X["bad"]; h, l, c = X["h"], X["l"], X["c"]
    # ── 日線 KD（K2、K4）
    K, Dd, pos = WR.kd_daily(h, l, c, bad)
    k_ = np.arange(1, nb)
    with np.errstate(invalid="ignore"):
        okd = (pos[k_] >= WARM) & (pos[k_ - 1] == pos[k_] - 1) & np.isfinite(K[k_ - 1]) & np.isfinite(K[k_]) & \
              (K[k_ - 1] <= Dd[k_ - 1]) & (K[k_] > Dd[k_]) & (K[k_ - 1] < TH)
    cand = k_[okd]
    # ── 週、月 K（K3、K4）
    o_, h_, l_, c_ = (df[z].to_numpy(float) for z in ("open", "high", "low", "close"))
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    valid = np.asarray(df["traded"].to_numpy(), bool)
    if not (np.flatnonzero(valid) == idx).all():
        raise SystemExit(f"⛔ {wn} {sid} traded ≠ load_bars idx")
    PER = {}
    for nm, (gid, gl) in (("w", (W["wk"], W["wl"])), ("m", (W["mo"], W["ml"]))):
        ids, _, PH, PL, PC, _ = RW.weekly_bars(valid, o_, h_, l_, c_, vol, gid)
        jq = np.searchsorted(ids, gid[idx])
        Kp, Dp, pp, fq = period_kd(jq, PH, PL, PC, bad)
        PER[nm] = {"ids": ids, "K": Kp, "D": Dp, "pos": pp, "fq": fq, "gid": gid, "gl": gl}
    feats = {}
    for k in cand:
        T = int(idx[k]); f = {"why0": None, "kf": int(k)}
        for nm in ("w", "m"):
            P = PER[nm]; g = int(P["gid"][T])
            gmax = g if T == int(P["gl"][g]) else g - 1          # K3 已收完
            j = int(np.searchsorted(P["ids"], gmax, "right")) - 1
            same = j >= 0 and not bool(np.asarray(bad[int(P["fq"][j]) + 1:k + 1], bool).any())
            Kv = float(P["K"][j]) if j >= 0 else np.nan; Dv = float(P["D"][j]) if j >= 0 else np.nan
            ps = int(P["pos"][j]) if j >= 0 else -1
            ok20 = same and ps >= WARM and np.isfinite(Kv); ok9 = same and ps >= WARM_ALT and np.isfinite(Kv)
            f[nm] = bool(ok20 and Kv < TH); f[nm + "9"] = bool(ok9 and Kv < TH)
            f[nm + "D"] = bool(ok20 and Dv < TH); f[nm + "x"] = bool(ok20 and Kv > Dv)
            f[nm + "K"] = round(Kv, 3) if np.isfinite(Kv) else None; f[nm + "Dv"] = round(Dv, 3) if np.isfinite(Dv) else None
            f[nm + "日"] = str(cal[int(idx[P["fq"][j]])].date()) if j >= 0 else ""
            f[nm + "可判"] = bool(ok20)
        f["jneg"] = bool(3 * K[k - 1] - 2 * Dd[k - 1] < 0)
        f.update({"K[T-1]": round(float(K[k - 1]), 3), "D[T-1]": round(float(Dd[k - 1]), 3), "K[T]": round(float(K[k]), 3),
                  "D[T]": round(float(Dd[k]), 3), "J[T-1]": round(float(3 * K[k - 1] - 2 * Dd[k - 1]), 3)})
        feats[int(k)] = f
    # ── 重疊（K8）：%R 件 K 格、W 格保留集合
    WRv = WR.willr(h, l, c, bad)
    Kw, Dw, pw = K, Dd, pos
    ref = {}
    for nm, ks in (("日線KD(K≤30,%R件K格)", WR.detect_k(Kw, Dw, pw)), ("%R(W格)", WR.detect_w(WRv))):
        st, _ = WR.dedup_then_status(ks, lambda kk: WR.st_next_open(X, kk))
        ref[nm] = np.array(sorted(kk for kk in ks if st[kk] == "保留"), np.int64)
    for k, f in feats.items():
        for nm, arr in ref.items():
            f["同日_" + nm] = bool(np.isin(k, arr)); f[f"±{OVW}_" + nm] = bool(((arr >= k - OVW) & (arr <= k + OVW)).any())
    # ── 各格
    EV = {}
    keys = None
    for cell in CELLS:
        ks = sorted(k for k, f in feats.items() if PRED[cell](f))
        st, alt = WR.dedup_then_status(ks, lambda kk: WR.st_next_open(X, kk), win=DEDUP)
        if keys is None and feats:
            keys = [z for z in next(iter(feats.values())) if z not in ("why0", "kf")]
        EV[cell] = [{"sid": sid, "T": int(idx[k]), "k": int(k), **{z: feats[k][z] for z in keys}, "st": st[k], "alt保留": bool(k in alt)} for k in ks]
    # ── K7 股月／股週比例（段內，不套閘）
    share = {}
    for sg, (p0, p1) in W["win"].items():
        d = {}
        for nm in ("w", "m"):
            P = PER[nm]
            lastq = np.r_[P["fq"][1:], nb] - 1                   # 每個週（月）K 的最後一根 q
            lp = idx[lastq] if len(lastq) else np.zeros(0, np.int64)
            sel = (lp >= p0) & (lp <= p1) & (P["pos"] >= WARM) & np.isfinite(P["K"])
            d[nm] = (int(sel.sum()), int((sel & (P["K"] < TH)).sum()))
        share[sg] = d
    return sid, {"ev": EV, "expo": X["expo"], "nb": nb, "share": share, "ncand": int(len(cand))}


def seg_extra(ok, p0, p1, cal):
    wn = "早年" if cal[-1].year <= 2014 else "主"
    sg = next(s for s, w in WR._G[wn]["win"].items() if w == (p0, p1))
    rows = {cell: [e for r in ok.values() for e in r["ev"][cell] if p0 <= e["T"] <= p1] for cell in ("J", "D", "J_週月暖機9根")}
    kept = {cell: [e for e in v if e["st"] == "保留"] for cell, v in rows.items()}
    nJ, nD = len(kept["J"]), len(kept["D"])
    ratio = round(nJ / nD, 4) if nD else None
    mw = [sum(r["share"][sg][z][0] for r in ok.values()) for z in ("w", "m")]
    ml = [sum(r["share"][sg][z][1] for r in ok.values()) for z in ("w", "m")]
    out = {"seq377退化檢查": {"J保留": nJ, "D保留(日線K<20金叉)": nD, "J÷D": ratio,
                          "偵測(合併前)J÷D": round(len(rows["J"]) / len(rows["D"]), 4) if rows["D"] else None,
                          "門檻": DEG, "退化": bool(ratio is not None and ratio >= DEG),
                          "判定": "與日線 KD 退化 ⇒ 等於日線 KD、停在乾跑" if (ratio is not None and ratio >= DEG) else "不退化"},
           "股月": {"可判月K數": mw[1], "月K<20": ml[1], "比例": round(ml[1] / mw[1], 4) if mw[1] else None},
           "股週": {"可判週K數": mw[0], "週K<20": ml[0], "比例": round(ml[0] / mw[0], 4) if mw[0] else None},
           "D保留中週可判": sum(1 for e in kept["D"] if e["w可判"]), "D保留中月可判": sum(1 for e in kept["D"] if e["m可判"])}
    for cell in ("J", "D"):
        n = len(kept[cell]); o = {"保留": n}
        for nm in ("日線KD(K≤30,%R件K格)", "%R(W格)"):
            for pre in ("同日_", f"±{OVW}_"):
                x = sum(1 for e in kept[cell] if e.get(pre + nm)); o[pre + nm] = x; o[pre + nm + "_比例"] = round(x / n, 4) if n else None
        out[f"重疊_{cell}"] = o
    return out


def diag(ok):
    return {"有效K棒": int(sum(r["nb"] for r in ok.values())), "日線K<20金叉候選(全期、合併前)": int(sum(r["ncand"] for r in ok.values()))}


def main():
    WR.run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": tuple(CELLS),
                 "title": "PREREG KDJ三週期共振 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
                 "ruling": "seq394 第 3 題、seq398 發號；N_前段 ＋1；退化門檻 J÷日線KD ≥ 90% ⇒ 等於日線 KD；n_eff ＜ 30 ⇒ 依構造不可判定；乾跑",
                 "doc": __doc__, "seg_extra": seg_extra, "diag": diag})
    out_dir = OUT if "--limit" not in sys.argv else os.path.join(OUT, "_try")
    p = os.path.join(out_dir, "freq.json")
    J = json.load(open(p, encoding="utf-8"))
    jd = {}
    for wn, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for sg in sgs:
            s = J["世界"][wn]["段"][sg]
            jd[f"{wn}/{sg}"] = {"J_n": s["J"]["事件數(保留)"], "J_n_eff": s["J"]["n_eff"], "判斷": s["J"]["判斷"],
                                "D_n": s["D"]["事件數(保留)"], "J÷D": s["附加"]["seq377退化檢查"]["J÷D"], "退化": s["附加"]["seq377退化檢查"]["退化"]}
    J["判斷摘要"] = jd
    J["退化結論"] = "與日線 KD 退化（等於日線 KD），停在乾跑" if any(v["退化"] for k, v in jd.items() if k != "早年/早年") else "不退化"
    json.dump(J, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()

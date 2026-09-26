# -*- coding: utf-8 -*-
"""營飆 v1（#1 t−1）與 #13 的差異與資金分配（裁定 seq205；回測線計算助手 2026-09-26）。

⭐ 全部是描述、⛔ 不判、⛔ 不計 N、⛔ 不改任何一套。⛔ 本檔不改任何既有 .py；引擎一律走 researchYear1M.run_engine
   （fd25d148ee；G1 對主窗逐位元），兩方合成走 researchp17.compose，標籤走 rerun17_table.label。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfMix13 run      # 單行程
    ... -m backtest.researchYfMix13 report

必附（逐字）：
  「兩套都是事後挑出的候選、混法也是看完結果才列 ⇒ 只供使用者選風險檔位，⛔ 不當證據」
  「營飆 v1 的 120 天是尖峰、#13 的 60 天在 30～80 天穩」

═══ 臂 ═══
  營飆 v1 ＝ #1 PREREG10 AND regime=True N10 H120（t−1 閘）｜種子 1000＋r（＝ resultsN17/regime_t1/seeds.csv t1 #1）
  #13     ＝ P1 AND N20 d=inf relvol H60｜種子 7000＋r（＝ resultsN17/rerun17_seeds.csv main #13；relvol 排序、不抽籤 ⇒ 200 顆應完全相同，本檔驗）
  0050    ＝ rerun17.load_bench（還原收盤）；主窗錨 0.24020209886370614／−0.3395700527611012
  主窗 2017-03-02～2026-08-24（引擎原樣版 ＝ 既有數字那一條）；逐年 ＝ researchYear1M 的 11 個固定窗（主版）＋ 最近一年／2026 YTD 的引擎原樣版

═══ 讀法（⭐ 看結果前寫定）═══
  K1 持股：由引擎 audit 重建。部位在第 t 天「持有」⇔ 買進日 ≤ t ＜ 賣出日（＝ 引擎第 t 天收盤市值裡有它；賣出那天引擎先結清再記權益）
  K2 重疊（逐日）＝ |營飆持股 ∩ #13 持股| ÷ |營飆持股|，只算 t ∈ [w0, w1] 且營飆持股非空的日子；每顆種子得「逐日均值」「逐日中位」，
     再報 200 顆的中位與 p10／p25／p75／p90；另報反向（÷ |#13 持股|）
  K3 同檔同週：週 ＝ 進場日的 ISO 年-週。訊號層：兩套訊號都來自同一張 AND 表（營飆只多一道 t−1 大盤閘）⇒ 營飆訊號 ⊂ #13 訊號（依構造）；
     實際進場層：每顆種子 營飆進場 (股, 週) 也出現在 #13 進場 (股, 週) 的比例（及反向），報 200 顆分佈
  K4 相關：日報酬 eq[t]/eq[t−1]−1，t ∈ (w0, w1]；⭐ 選「逐顆算相關再取中位」（#13 只有一條路徑）；全期與逐曆年（2017 自 03-03、2026 至 08-24）
  K5 最大回落起訖：窗內 eq[w0..w1] 的高點日與谷底日；營飆報 200 顆分佈（中位回落那顆、最常見的谷底日）與「和 #13 的 [高點, 谷底] 區間有交集」的顆數比例
  K6 混合：逐種子（營飆第 r 顆 ＋ #13 第 r 顆 ＋ 0050）合成再取中位；每年第一個交易日調回比例（窗首當天不算），
     換手 ＝ 各腿「目標 − 現值」絕對值合計 ÷ 2（＝ 兩腿時 compose 的 |目標 − 現有策略側|），成本 ＝ 換手 × 0.585%，從組合扣
     兩方用 researchp17.compose（同前一件 mix）；三方用本檔 nway（同一順序：各腿走完當天 → 目標 → 換手扣成本 → 依權重重配）
  K7 參照列（純營飆、純 #13、純 0050）直接由序列算（⛔ 不經合成）⇒ 閘：主窗年化／回落中位 與 regime_t1 cells.csv、rerun17.csv #13、0050 錨 逐位元
  K8 標籤 ＝ rerun17_table.label（主窗年化中位、回落中位 對 0050 錨）；比值 ＝ 年化中位 ÷ |回落中位|
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

from . import researchYear1M as Y
from . import rerun17 as RR
from . import rerun17_table as RT
from . import research13 as R13

HERE = Y.HERE
OUT = os.path.join(HERE, "resultsYfMix13")
REPS = 200
COST = 0.00585
CAP = 1_000_000
A, B = 1, 13
MIXES = [  # (鍵, 名稱, 營飆, #13, 0050)
    ("A", "純營飆 v1（參照）", 1.0, 0.0, 0.0),
    ("B", "純 #13（參照）", 0.0, 1.0, 0.0),
    ("Z", "純 0050（參照）", 0.0, 0.0, 1.0),
    ("AB75", "營飆／#13 ＝ 75／25", 0.75, 0.25, 0.0),
    ("AB50", "營飆／#13 ＝ 50／50", 0.50, 0.50, 0.0),
    ("AB25", "營飆／#13 ＝ 25／75", 0.25, 0.75, 0.0),
    ("T33", "營飆／#13／0050 ＝ 1/3 各", 1 / 3, 1 / 3, 1 / 3),
    ("T442", "營飆／#13／0050 ＝ 40／40／20", 0.40, 0.40, 0.20),
    ("T255", "營飆／#13／0050 ＝ 25／25／50", 0.25, 0.25, 0.50),
]
WORD = ["兩套都是事後挑出的候選、混法也是看完結果才列 ⇒ 只供使用者選風險檔位，⛔ 不當證據",
        "營飆 v1 的 120 天是尖峰、#13 的 60 天在 30～80 天穩"]
RTP = dict(float_precision="round_trip")


def sha16(a):
    return hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()[:16]


def year_mask(cal, a, b):
    yr = pd.DatetimeIndex(cal[a:b + 1]).year
    m = np.zeros(b - a + 1, bool); m[1:] = yr[1:] != yr[:-1]
    return m


def nway(series, w, rebal, cost=COST):
    """K6：k 腿權益層合成（researchp17.compose 的同一順序推廣到 k 腿）。series：list of 窗內序列；w：權重（和 ＝ 1）。"""
    S = [np.asarray(s, float) for s in series]; n = len(S[0])
    R_ = [np.r_[1.0, s[1:] / s[:-1]] for s in S]
    w = np.asarray(w, float)
    v_i = w.copy(); V = np.empty(n); V[0] = 1.0; cst = np.zeros(n)
    for t in range(1, n):
        v_i = v_i * np.array([r[t] for r in R_])
        v = float(v_i.sum())
        if rebal[t]:
            tgt = w * v
            tr = float(np.abs(tgt - v_i).sum()) / 2.0
            c = tr * cost; v -= c; cst[t] = c
            v_i = w * v
        V[t] = v
    return V, cst


def mix_series(key, EA, EB, EZ, rebal):
    """回 (合成序列, 成本合計)。參照列直接用原序列（K7）。"""
    from . import researchp17 as P17
    _, _, a, b, z = [m for m in MIXES if m[0] == key][0]
    if key == "A":
        return EA, 0.0
    if key == "B":
        return EB, 0.0
    if key == "Z":
        return EZ, 0.0
    if z == 0.0:
        V, _, cst = P17.compose(EA, EB, np.full(len(EA), a), rebal, cost=COST)
        return V, float(cst.sum())
    V, cst = nway([EA, EB, EZ], [a, b, z], rebal)
    return V, float(cst.sum())


def positions(au, w0, w1):
    """K1：audit ⇒ [(sid, 買進日, 賣出日)]（未賣出 ⇒ 賣出日 ＝ 10**9）。"""
    open_ = {}; out = []
    for x in au:
        if x["side"] == "buy" and x.get("kind") is None:
            open_[x["sid"]] = x["t"]
        elif x["side"] == "sell" and x.get("kind") is None:
            out.append((x["sid"], open_.pop(x["sid"]), x["t"]))
    out += [(s, t, 10 ** 9) for s, t in open_.items()]
    return out


def held_sets(pos, w0, w1):
    H = [set() for _ in range(w1 - w0 + 1)]
    for sid, tb, ts in pos:
        for t in range(max(tb, w0), min(ts, w1 + 1)):
            H[t - w0].add(sid)
    return H


def dd_dates(v):
    v = np.asarray(v, float); pk = np.maximum.accumulate(v); dd = v / pk - 1
    t = int(dd.argmin()); p = int(v[:t + 1].argmax())
    return p, t, float(dd.min())


def run(log):
    t0 = time.time()
    Y.setup(log)
    G = Y._G; cal = G["cal"]; ncal = G["ncal"]; bench = G["bench"]
    w0, w1 = RR.win_bounds(cal); n = w1 - w0 + 1
    dates = pd.DatetimeIndex(cal[w0:w1 + 1])
    week = [f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}" for d in cal]
    EZ = bench[w0:w1 + 1]
    # ── 主窗：兩臂 200 顆
    rows = []; EQ = {A: np.empty((REPS, n)), B: np.empty((REPS, n))}; POS = {A: {}, B: {}}; AUD13 = None; same13 = True
    for r in range(REPS):
        for cid in (A, B):
            au = []
            s = Y.run_engine(cid, Y.sig_of(cid, "eng", w0, w1), r, "eng", audit=au)
            eq = np.asarray(s["equity"], float)
            c, m, v = RR.win_metrics(eq, s["first"], s["end"], w0, w1)
            rows.append({"cell": cid, "r": r, "seed": (1000 if cid == A else 7000) + r, "cagr": float(c), "mdd": float(m), "vol": float(v),
                         "first": int(s["first"]), "end": int(min(s["end"], ncal)), "trades": int(s["trades"]), "eq_sha": sha16(eq[:ncal])})
            EQ[cid][r] = eq[w0:w1 + 1]
            POS[cid][r] = positions(au, w0, w1)
            if cid == B:
                key = [(x["t"], x["sid"], x["side"]) for x in au]
                if AUD13 is None:
                    AUD13 = key
                elif key != AUD13:
                    same13 = False
        if (r + 1) % 20 == 0:
            log(f"  主窗 {r + 1}/{REPS}｜{time.time() - t0:.0f}s")
    M = pd.DataFrame(rows)
    M.to_csv(os.path.join(OUT, "seeds_main.csv"), index=False)
    same13 = same13 and M[M["cell"] == B]["eq_sha"].nunique() == 1 and bool((EQ[B] == EQ[B][0]).all())
    # ── 閘（K7）
    gate = {}
    ref_t1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, **RTP)
    ref_t1 = ref_t1[(ref_t1["stage"] == "t1") & (ref_t1["cell"] == A)].set_index("r").sort_index()
    ref_13 = pd.read_csv(os.path.join(RR.OUT, "rerun17_seeds.csv"), dtype={"eq_sha": str}, **RTP)
    ref_13 = ref_13[(ref_13["stage"] == "main") & (ref_13["cell"] == B)].set_index("r").sort_index()
    for cid, ref, nm in ((A, ref_t1, "營飆 v1 對 regime_t1/seeds.csv t1 #1"), (B, ref_13, "#13 對 rerun17_seeds.csv main #13")):
        g = M[M["cell"] == cid].set_index("r").sort_index()
        bad = {k: int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(g[k], ref[k]))) for k in ("cagr", "mdd", "vol")}
        bad.update({k: int((g[k].astype(int) != ref[k].astype(int)).sum()) for k in ("first", "end", "trades")})
        bad["eq_sha"] = int((g["eq_sha"].astype(str) != ref["eq_sha"].astype(str)).sum())
        gate[nm] = {"顆數": len(g), "不同數": bad, "逐位元": len(g) == REPS and all(v == 0 for v in bad.values())}
    cells_t1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "cells.csv"), **RTP)
    r17 = pd.read_csv(os.path.join(RR.OUT, "rerun17.csv"), **RTP)
    ca = float(M[M["cell"] == A]["cagr"].median()); ma = float(M[M["cell"] == A]["mdd"].median())
    cb = float(M[M["cell"] == B]["cagr"].median()); mb = float(M[M["cell"] == B]["mdd"].median())
    qa = cells_t1[cells_t1["編號"] == A].iloc[0]; qb = r17[r17["編號"] == B].iloc[0]
    gate["營飆中位 對 regime_t1/cells.csv t1_年化／t1_回落"] = {"逐位元": repr(ca) == repr(float(qa["t1_年化"])) and repr(ma) == repr(float(qa["t1_回落"]))}
    gate["#13 中位 對 rerun17.csv 主窗_年化／主窗_回落"] = {"逐位元": repr(cb) == repr(float(qb["主窗_年化"])) and repr(mb) == repr(float(qb["主窗_回落"]))}
    bz = RR.bench_row(cal, bench, w0, w1 + 1)
    cz, mz = R13.window_stats(EZ, 0, n, 0, n)
    gate["0050 對錨"] = {"逐位元": repr(float(cz)) == repr(RR.ANCHOR[0]) and repr(float(mz)) == repr(RR.ANCHOR[1])
                         and repr(bz["cagr"]) == repr(RR.ANCHOR[0])}
    gate["#13 200 顆完全相同（equity 與 audit）"] = {"逐位元": bool(same13)}
    gate["全部過"] = all(v["逐位元"] for v in gate.values() if isinstance(v, dict))
    log(f"[閘] {json.dumps(gate, ensure_ascii=False)}")
    if not gate["全部過"]:
        json.dump(gate, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        raise SystemExit("⛔ 閘不過，停")
    json.dump(gate, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    np.savez_compressed(os.path.join(OUT, "eq_main.npz"), yf=EQ[A], b13=EQ[B][0], z=EZ, w0=w0, w1=w1,
                        dates=np.array([str(d.date()) for d in dates]))
    # ── 持股與重疊（K1～K3）
    prow = []
    for cid in (A, B):
        for r in range(REPS) if cid == A else [0]:
            for sid, tb, ts in POS[cid][r]:
                prow.append({"cell": cid, "r": r, "sid": sid, "t_buy": tb, "t_sell": ts if ts < 10 ** 9 else -1,
                             "buy_date": str(cal[tb].date()), "week": week[tb]})
    P = pd.DataFrame(prow)
    P.to_csv(os.path.join(OUT, "positions.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    H13 = held_sets(POS[B][0], w0, w1)
    e13 = {(s, week[tb]) for s, tb, _ in POS[B][0] if w0 <= tb <= w1}
    ov = []
    for r in range(REPS):
        H1 = held_sets(POS[A][r], w0, w1)
        fr = [len(h & k) / len(h) for h, k in zip(H1, H13) if len(h)]
        fr2 = [len(h & k) / len(k) for h, k in zip(H1, H13) if len(k)]
        both = [len(h & k) for h, k in zip(H1, H13)]
        e1 = [(s, week[tb]) for s, tb, _ in POS[A][r] if w0 <= tb <= w1]
        ov.append({"r": r, "天數_營飆有持股": len(fr), "天數_營飆空手": n - len(fr), "重疊÷營飆_逐日均值": float(np.mean(fr)),
                   "重疊÷營飆_逐日中位": float(np.median(fr)), "重疊÷#13_逐日均值": float(np.mean(fr2)),
                   "重疊÷#13_逐日中位": float(np.median(fr2)), "同時持有檔數_逐日均值": float(np.mean(both)),
                   "營飆持股數_逐日均值": float(np.mean([len(h) for h in H1])), "#13持股數_逐日均值": float(np.mean([len(k) for k in H13])),
                   "營飆進場數": len(e1), "營飆進場_同檔同週也在#13進場": float(np.mean([x in e13 for x in e1])) if e1 else np.nan,
                   "#13進場_同檔同週也在營飆進場": float(np.mean([x in set(e1) for x in e13])) if e13 else np.nan})
    OV = pd.DataFrame(ov); OV.to_csv(os.path.join(OUT, "overlap_seeds.csv"), index=False)
    # 訊號層（依構造）
    sa = Y.sig_of(A, "eng", w0, w1); sb = Y.sig_of(B, "eng", w0, w1)
    ka = {(s, week[e]) for s, e in zip(sa["sid"], sa["entry_pos"])}; kb = {(s, week[e]) for s, e in zip(sb["sid"], sb["entry_pos"])}
    sig_ov = {"營飆訊號數": len(sa), "#13訊號數": len(sb), "營飆訊號(股,週)數": len(ka), "#13訊號(股,週)數": len(kb),
              "營飆訊號同檔同週也在#13訊號": len(ka & kb) / len(ka), "#13訊號同檔同週也在營飆訊號": len(ka & kb) / len(kb),
              "營飆訊號列⊂#13訊號列": bool(sa.index.isin(sb.index).all()),
              "說明": "兩套訊號都來自 resultsN17/sig_edc6f/and_signals.csv.gz；營飆只多一道 t−1 大盤閘 ⇒ 依構造是子集合"}
    # ── 相關（K4）
    ra_ = EQ[A][:, 1:] / EQ[A][:, :-1] - 1; rb_ = EQ[B][0, 1:] / EQ[B][0, :-1] - 1; rz_ = EZ[1:] / EZ[:-1] - 1
    yrs = dates[1:].year
    crow = []
    for r in range(REPS):
        row = {"r": r, "全期_營飆×#13": float(np.corrcoef(ra_[r], rb_)[0, 1]), "全期_營飆×0050": float(np.corrcoef(ra_[r], rz_)[0, 1])}
        for y in sorted(set(yrs)):
            m_ = yrs == y
            row[f"{y}_營飆×#13"] = float(np.corrcoef(ra_[r][m_], rb_[m_])[0, 1])
        crow.append(row)
    CR = pd.DataFrame(crow); CR.to_csv(os.path.join(OUT, "corr_seeds.csv"), index=False)
    corr13z = {"全期": float(np.corrcoef(rb_, rz_)[0, 1]), **{str(y): float(np.corrcoef(rb_[yrs == y], rz_[yrs == y])[0, 1]) for y in sorted(set(yrs))}}
    # ── 回落起訖（K5）
    pb, tb_, mb_ = dd_dates(EQ[B][0]); pz, tz, mz_ = dd_dates(EZ)
    drow = []
    for r in range(REPS):
        p, t, m = dd_dates(EQ[A][r])
        drow.append({"r": r, "mdd": m, "高點": str(dates[p].date()), "谷底": str(dates[t].date()),
                     "與#13區間有交集": bool(p <= tb_ and pb <= t), "與0050區間有交集": bool(p <= tz and pz <= t)})
    DD = pd.DataFrame(drow); DD.to_csv(os.path.join(OUT, "dd_seeds.csv"), index=False)
    med_r = int((DD["mdd"] - DD["mdd"].median()).abs().idxmin())
    ddinfo = {"#13": {"高點": str(dates[pb].date()), "谷底": str(dates[tb_].date()), "回落": mb_},
              "0050": {"高點": str(dates[pz].date()), "谷底": str(dates[tz].date()), "回落": mz_},
              "營飆_中位回落那顆": {"r": med_r, **DD.loc[med_r, ["高點", "谷底", "mdd"]].to_dict()},
              "營飆_谷底日次數前三": DD["谷底"].value_counts().head(3).to_dict(),
              "營飆_高點日次數前三": DD["高點"].value_counts().head(3).to_dict(),
              "營飆_與#13區間有交集的顆數比例": float(DD["與#13區間有交集"].mean()),
              "營飆_與0050區間有交集的顆數比例": float(DD["與0050區間有交集"].mean())}
    json.dump({"訊號層": sig_ov, "相關_#13×0050": corr13z, "回落起訖": ddinfo}, open(os.path.join(OUT, "facts.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    log(f"[持股/相關/回落] 完成｜{time.time() - t0:.0f}s")
    # ── 混合：主窗（K6）
    mrow = []
    rb = year_mask(cal, w0, w1)
    for r in range(REPS):
        for key, *_ in MIXES:
            V, cs = mix_series(key, EQ[A][r], EQ[B][r], EZ, rb)
            c, m = R13.window_stats(V, 0, n, 0, n)
            mrow.append({"scope": "主窗", "mix": key, "r": r, "cagr": float(c), "mdd": float(m), "end_value": CAP * V[-1] / V[0], "cost_sum": cs})
    # 2 腿 nway 與 compose 的差（K6 自檢）
    Vc, _ = mix_series("AB50", EQ[A][0], EQ[B][0], EZ, rb); Vn, _ = nway([EQ[A][0], EQ[B][0]], [0.5, 0.5], rb)
    nway_vs_compose = float(np.abs(Vc / Vn - 1).max())
    # ── 混合：固定窗
    FW = Y.fixed_windows(cal)
    wins = [(w, "mtm") for w in FW] + [(w, "eng") for w in FW if w["key"] in ("L1Y", "YTD26")]
    for i, (w, var) in enumerate(wins):
        a, b = w["w0"], w["w1"]; ez = bench[a:b + 1]; mm = year_mask(cal, a, b)
        e13w = None
        for r in range(REPS):
            ea = np.asarray(Y.run_engine(A, Y.sig_of(A, var, a, b), r, var)["equity"], float)[a:b + 1]
            eb = np.asarray(Y.run_engine(B, Y.sig_of(B, var, a, b), r, var)["equity"], float)[a:b + 1]
            if e13w is None:
                e13w = eb
            elif not np.array_equal(eb, e13w):
                raise SystemExit(f"⛔ #13 在窗 {w['key']} 的種子不相同")
            for key, *_ in MIXES:
                V, cs = mix_series(key, ea, eb, ez, mm)
                ret, dd = Y.seg_stats(V)
                mrow.append({"scope": w["key"] + ("" if var == "mtm" else "_引擎原樣"), "mix": key, "r": r, "cagr": np.nan, "mdd": dd,
                             "end_value": CAP * (1 + ret), "cost_sum": cs})
        log(f"  固定窗 {i + 1}/{len(wins)} {w['key']} {var}｜{time.time() - t0:.0f}s")
    MS = pd.DataFrame(mrow)
    MS.to_csv(os.path.join(OUT, "mix_seeds.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    json.dump({"nway兩腿對compose最大相對差": nway_vs_compose, "窗": [(w["key"], w["d0"], w["d1"], v) for w, v in wins]},
              open(os.path.join(OUT, "mix_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[完成] run｜{time.time() - t0:.0f}s")


def pct(s, q):
    return float(pd.Series(s).quantile(q))


def report(log):
    MS = pd.read_csv(os.path.join(OUT, "mix_seeds.csv.gz"), **RTP)
    OV = pd.read_csv(os.path.join(OUT, "overlap_seeds.csv"), **RTP)
    CR = pd.read_csv(os.path.join(OUT, "corr_seeds.csv"), **RTP)
    F = json.load(open(os.path.join(OUT, "facts.json"), encoding="utf-8"))
    gate = json.load(open(os.path.join(OUT, "gate.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(OUT, "mix_meta.json"), encoding="utf-8"))
    bc, bm = RR.ANCHOR
    scopes = [s for s in dict.fromkeys(MS["scope"]) if s != "主窗"]
    rows = []
    for key, name, a, b, z in MIXES:
        g = MS[(MS["mix"] == key) & (MS["scope"] == "主窗")]
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio, extra = RT.label(c, m, bc, bm)
        row = {"鍵": key, "組合": name, "營飆": a, "#13": b, "0050": z, "主窗年化_中位": c, "主窗回落_中位": m, "比值": ratio,
               "對0050標籤": lab, "深淺註": extra, "主窗100萬期末_中位": float(g["end_value"].median()),
               "主窗100萬期末_p10": pct(g["end_value"], .1), "主窗100萬期末_p90": pct(g["end_value"], .9),
               "年化_p10": pct(g["cagr"], .1), "年化_p90": pct(g["cagr"], .9), "回落_p10": pct(g["mdd"], .1), "回落_p90": pct(g["mdd"], .9),
               "再平衡成本合計_中位": float(g["cost_sum"].median())}
        for s in scopes:
            gs = MS[(MS["mix"] == key) & (MS["scope"] == s)]
            row[f"{s}_期末中位"] = float(gs["end_value"].median())
            row[f"{s}_期末p10"] = pct(gs["end_value"], .1); row[f"{s}_期末p90"] = pct(gs["end_value"], .9)
            row[f"{s}_回落中位"] = float(gs["mdd"].median())
        rows.append(row)
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "mix.csv"), index=False)
    ovs = {}
    for c in ["重疊÷營飆_逐日均值", "重疊÷營飆_逐日中位", "重疊÷#13_逐日均值", "重疊÷#13_逐日中位", "同時持有檔數_逐日均值",
              "營飆持股數_逐日均值", "#13持股數_逐日均值", "營飆進場_同檔同週也在#13進場", "#13進場_同檔同週也在營飆進場", "天數_營飆空手"]:
        ovs[c] = {"中位": pct(OV[c], .5), "p10": pct(OV[c], .1), "p25": pct(OV[c], .25), "p75": pct(OV[c], .75), "p90": pct(OV[c], .9)}
    OS = pd.DataFrame(ovs).T; OS.index.name = "量"; OS.to_csv(os.path.join(OUT, "overlap.csv"))
    cs = {c: {"中位": pct(CR[c], .5), "p10": pct(CR[c], .1), "p90": pct(CR[c], .9)} for c in CR.columns if c != "r"}
    CS = pd.DataFrame(cs).T; CS.index.name = "量"
    CS.to_csv(os.path.join(OUT, "corr.csv"))
    # REPORT.md
    f = lambda x: f"{x * 100:+.2f}%"
    wan = lambda x: f"{x / 1e4:,.1f}"
    L = ["# 營飆 v1 與 #13：差異與資金分配（裁定 seq205；描述、⛔ 不判、⛔ 不計 N）", "",
         *[f"> ⚠ {w}" for w in WORD], "",
         "主窗 2017-03-02～2026-08-24、快照 edc6f8002f；營飆 v1 ＝ #1 PREREG10 AND regime=True N10 H120（t−1 閘）種子 1000＋r；"
         "#13 ＝ P1 AND N20 d=inf relvol H60 種子 7000＋r（200 顆完全相同，已驗）。程式 `backtest/researchYfMix13.py`（讀法 K1～K8 見檔頭），"
         "查核 `backtest/researchYfMix13_check.py`。所有數字引自本資料夾的 csv／json。", "",
         "## 閘（逐位元）", "", "| 項 | 結果 |", "|---|---|"]
    L += [f"| {k} | {'✅' if (v['逐位元'] if isinstance(v, dict) else v) else '⛔'} {json.dumps(v.get('不同數', ''), ensure_ascii=False) if isinstance(v, dict) and '不同數' in v else ''} |"
          for k, v in gate.items() if k != "全部過"]
    L += ["", "## 一、持股重疊（overlap.csv；200 顆營飆各算、報分佈）", "", "| 量 | 中位 | p10 | p25 | p75 | p90 |", "|---|---|---|---|---|---|"]
    for i, q in OS.iterrows():
        pc = "檔" not in i and "天數" not in i
        fm = (lambda x: f"{x * 100:.1f}%") if pc else (lambda x: f"{x:.2f}")
        L.append(f"| {i} | {fm(q['中位'])} | {fm(q['p10'])} | {fm(q['p25'])} | {fm(q['p75'])} | {fm(q['p90'])} |")
    so = F["訊號層"]
    L += ["", f"訊號層（依構造）：營飆 {so['營飆訊號數']} 筆訊號全部是 #13 {so['#13訊號數']} 筆訊號的子集合（同一張 AND 表、營飆多一道 t−1 大盤閘）⇒ "
          f"營飆訊號同檔同週也在 #13 ＝ {so['營飆訊號同檔同週也在#13訊號'] * 100:.1f}%、反向 {so['#13訊號同檔同週也在營飆訊號'] * 100:.1f}%。"
          "兩套的差異不在「挑哪些股」，而在「大盤閘、持有 120 對 60 天、10 對 20 槽、抽籤對 relvol 排序」。", "",
          "## 二、日報酬相關（corr.csv；逐顆算相關再取中位）", "", "| 期間 | 營飆×#13 中位 | p10 | p90 |", "|---|---|---|---|"]
    for i, q in CS.iterrows():
        L.append(f"| {i.replace('_營飆×#13', '').replace('_營飆×0050', '（營飆×0050）')} | {q['中位']:.3f} | {q['p10']:.3f} | {q['p90']:.3f} |")
    L += ["", f"#13×0050 全期 {F['相關_#13×0050']['全期']:.3f}。", "", "### 最大回落起訖", ""]
    d = F["回落起訖"]
    L += [f"- #13：{d['#13']['高點']} → {d['#13']['谷底']}（{f(d['#13']['回落'])}）",
          f"- 0050：{d['0050']['高點']} → {d['0050']['谷底']}（{f(d['0050']['回落'])}）",
          f"- 營飆（中位回落那顆 r={d['營飆_中位回落那顆']['r']}）：{d['營飆_中位回落那顆']['高點']} → {d['營飆_中位回落那顆']['谷底']}（{f(d['營飆_中位回落那顆']['mdd'])}）",
          f"- 營飆 200 顆的谷底日最常見：{json.dumps(d['營飆_谷底日次數前三'], ensure_ascii=False)}；高點日：{json.dumps(d['營飆_高點日次數前三'], ensure_ascii=False)}",
          f"- 營飆的 [高點, 谷底] 與 #13 的區間有交集：{d['營飆_與#13區間有交集的顆數比例'] * 100:.1f}% 的種子；與 0050 有交集：{d['營飆_與0050區間有交集的顆數比例'] * 100:.1f}%", "",
          "## 三、混合（mix.csv；每年第一個交易日調回、換手 × 0.585%；逐種子合成取中位）", "",
          "| 組合 | 主窗年化 | 回落 | 比值 | 對 0050 | 100 萬放滿主窗（萬） | p10～p90（萬） |", "|---|---|---|---|---|---|---|"]
    for q in T.itertuples():
        L.append(f"| {q.組合} | {f(q.主窗年化_中位)} | {f(q.主窗回落_中位)} | {q.比值:.3f} | {q.對0050標籤}{('（' + q.深淺註 + '）') if isinstance(q.深淺註, str) and q.深淺註 else ''} | "
                 f"{wan(q.主窗100萬期末_中位)} | {wan(q.主窗100萬期末_p10)}～{wan(q.主窗100萬期末_p90)} |")
    L += ["", "### 100 萬逐年（期末中位，萬元；窗起點空手；最近一年與 2026 YTD 另列引擎原樣版）", "",
          "| 組合 | " + " | ".join(scopes) + " |", "|---|" + "---|" * len(scopes)]
    for q in T.itertuples():
        L.append(f"| {q.組合} | " + " | ".join(wan(T.loc[q.Index, f'{s}_期末中位']) for s in scopes) + " |")
    L += ["", f"兩腿 nway 對 compose 的最大相對差 {meta['nway兩腿對compose最大相對差']:.2e}（自檢）。",
          "窗：" + "；".join(f"{k} {a}～{b}（{'主版' if v == 'mtm' else '引擎原樣'}）" for k, a, b, v in meta["窗"]), "",
          *[f"> ⚠ {w}" for w in WORD], ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
    log(f"[report] mix.csv {len(T)} 列｜overlap.csv｜corr.csv｜REPORT.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "report"])
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")
    T0 = time.time()

    def log(x):
        x = f"[{time.time() - T0:6.0f}s] {x}"
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== researchYfMix13 {a.stage} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜單行程 =====")
    run(log) if a.stage == "run" else report(log)


if __name__ == "__main__":
    main()

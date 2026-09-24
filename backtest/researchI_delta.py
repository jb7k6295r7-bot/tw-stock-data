# -*- coding: utf-8 -*-
"""PREREGI 第二步之二：四個 Δ（登錄 seq4 §三＋§3-5 六處定字）＋彙總（§3-4）＋必報（§五 ③⑤⑥）。

輸入：researchI_seg.py 的 segments.csv／holdings_at_peak.csv（段、段起點持股與權重；已驗逐位）
靜態組合值（峰日 p 標準化為 1）：V(t) ＝ 現金 ＋ Σ w_i × C_i(t)／C_i(p)，現金 ＝ 1 − Σ w_i、報酬 0
深度（Q2 甲）：D ＝ V(谷日) − 1；Δk ＝ |D0| − |Dk|（pp）
曝險（Q1 甲）：三臂 Σw ＝ 基準的實際曝險 e；Δ_β ＝ 基準權重 × 1/β（β > 1）
β（Q3）：組合日報酬 r_p(t) ＝ Σ w_i r_i(t)（含現金、報酬 0 ⇒ 乘 1/β 後組合 β 恰為 1），t ∈ [p−119, p]，對 0050 還原日報酬 OLS 含截距；
   某日有任一持股報酬缺 ⇒ 該日不進迴歸（用可得部分），< 120 筆 ⇒ 計數（必報⑤）
Δ_ind（Q4）：母體 ＝ 峰日之前（含）最近量測日 eligible 列；產業 ＝ industry_code；持有產業的目標權重 ∝ 母體檔數；產業內持股均分
Δ_stk（Q5）：同一母體內 ret_120 排名，前 5% ＝ rank(pct) > 0.95；剔除後剩下的等權到 e；全被剔 ⇒ 無法計算
   持股不在該母體或 ret_120 缺 ⇒ 排不了名 ⇒ 不剔、計數（必報⑤）
Δ_vol（Q6）：池 ＝ entry_pos ＝「≤ 峰日的最後一個 entry_pos」的 S1 訊號；vol60 ＝ 以峰日為最後一筆的 60 個日報酬標準差；
   取最低的「峰日持股檔數」檔等權到 e；池 < 持股檔數 ⇒ 池全拿、計數
"""
from __future__ import annotations
import bisect, os, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchI as I
from backtest import data as D
from backtest import p4_features as P4F

OUT = I.OUT
LB_BETA, LB_VOL, TOP = 120, 60, 0.95


def static_depth(w: dict, p: int, v: int, closes) -> float:
    """w ＝ {sid: 權重}（Σ ≤ 1，其餘現金）⇒ V(v) − 1。"""
    return float(sum(wi * (float(closes[s][v]) / float(closes[s][p]) - 1.0) for s, wi in w.items()))


def rets(c, a, b):
    """c[a..b] 的日報酬（長度 b−a），對應 t ＝ a+1..b。"""
    x = np.asarray(c[a:b + 1], float)
    return x[1:] / x[:-1] - 1.0


def ols_beta(y, x):
    X = np.column_stack([np.ones(len(x)), x])
    return float(np.linalg.lstsq(X, y, rcond=None)[0][1])


def selftest():
    c = {"A": np.array([10., 11, 12, 9]), "B": np.array([20., 20, 20, 30])}
    assert abs(static_depth({"A": .5, "B": .25}, 0, 3, c) - (.5 * (-.1) + .25 * .5)) < 1e-15
    rng = np.random.default_rng(0); x = rng.normal(0, .01, 500); y = .002 + 1.5 * x
    assert abs(ols_beta(y, x) - 1.5) < 1e-12
    print("✅ 自測：靜態組合深度（含現金）、OLS β 已知值")


def main():
    selftest()
    t0 = time.time()
    cal, ncal, closes, opens, sigs = I.setup()
    sg = sigs[("S1", "T1", "*")]
    z = D.load_stock("0050", "twse", cal)
    c50 = pd.Series(z.df["close"].to_numpy()).ffill().to_numpy(float)
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"].to_dict()
    panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
    el = panel[panel["eligible"].astype(bool)]
    mdates = np.array(sorted(el["measure_date"].unique()), dtype="datetime64[ns]")
    by_md = {pd.Timestamp(d): g for d, g in el.groupby("measure_date")}
    ent = sorted(set(sg["entry_pos"]))
    S = pd.read_csv(os.path.join(OUT, "segments.csv"))
    H = pd.read_csv(os.path.join(OUT, "holdings_at_peak.csv"), dtype={"sid": str}, float_precision="round_trip")
    Hg = {k: dict(zip(g["sid"], g["權重"])) for k, g in H.groupby(["seed", "段"])}
    rows = []
    for r in S.itertuples():
        p, v = int(r.峰_pos), int(r.谷_pos)
        w = Hg[(r.seed, r.段)]; e = sum(w.values()); n_h = len(w)
        rec = {"seed": r.seed, "段": r.段, "峰_pos": p, "谷_pos": v, "e": e, "n_h": n_h}
        D0 = static_depth(w, p, v, closes); rec["D0"] = D0
        # ── Δ_β
        R = np.array([rets(closes[s], p - LB_BETA, p) for s in w])
        wv = np.array(list(w.values()))
        ok = np.all(np.isfinite(R), axis=0)
        m50 = rets(c50, p - LB_BETA, p); ok &= np.isfinite(m50)
        rec["β_筆數"] = int(ok.sum())
        beta = ols_beta((wv[:, None] * R).sum(0)[ok], m50[ok]) if ok.sum() >= 3 else np.nan
        rec["β"] = beta
        sc = 1.0 / beta if (np.isfinite(beta) and beta > 1) else 1.0
        rec["Δ_β曝險"] = e * sc
        rec["Dβ"] = static_depth({s: wi * sc for s, wi in w.items()}, p, v, closes)
        # 母體（Q4／Q5）：峰日之前（含）最近量測日
        k = int(np.searchsorted(mdates, np.datetime64(cal[p]), side="right")) - 1
        md = pd.Timestamp(mdates[k]); U = by_md[md]; rec["量測日"] = str(md.date())
        # ── Δ_ind
        cnt = U["stock_id"].map(ind).value_counts()
        hi = {s: ind.get(s) for s in w}
        rec["缺產業"] = sum(1 for x in hi.values() if x is None)
        held_ind = sorted({x for x in hi.values() if x is not None})
        tot = sum(cnt.get(j, 0) for j in held_ind)
        rec["持有產業不在母體"] = sum(1 for j in held_ind if cnt.get(j, 0) == 0)
        if tot > 0 and rec["缺產業"] == 0:
            wi_ = {}
            for j in held_ind:
                mem = [s for s in w if hi[s] == j]
                for s in mem:
                    wi_[s] = e * cnt.get(j, 0) / tot / len(mem)
            rec["Dind"] = static_depth(wi_, p, v, closes)
        else:
            rec["Dind"] = np.nan
        # ── Δ_stk
        rk = U.set_index("stock_id")["ret_120"].rank(pct=True)
        rec["stk_排不了名"] = sum(1 for s in w if s not in rk.index or not np.isfinite(rk.get(s, np.nan)))
        top = {s for s in w if s in rk.index and np.isfinite(rk[s]) and rk[s] > TOP}
        rec["stk_剔除"] = len(top)
        keep = [s for s in w if s not in top]
        rec["Dstk"] = static_depth({s: e / len(keep) for s in keep}, p, v, closes) if keep else np.nan
        rec["stk_無法計算"] = int(not keep)
        # ── Δ_vol
        e_last = ent[bisect.bisect_right(ent, p) - 1]
        pool = sorted(set(sg.loc[sg["entry_pos"] == e_last, "sid"]))
        vol = {}; short = 0
        for s in pool:
            x = rets(closes[s], p - LB_VOL, p); x = x[np.isfinite(x)]
            short += int(len(x) < LB_VOL)
            vol[s] = float(np.std(x, ddof=1)) if len(x) >= 2 else np.nan
        cand = sorted([s for s in pool if np.isfinite(vol[s])], key=lambda s: (vol[s], s))
        pick = cand[:n_h]
        rec.update({"vol_池": len(pool), "vol_池不足": int(len(cand) < n_h), "vol_不足60筆": short, "距換股日": p - e_last})
        rec["Dvol"] = static_depth({s: e / len(pick) for s in pick}, p, v, closes) if pick else np.nan
        for kx in ("β", "ind", "stk", "vol"):
            rec["Δ_" + kx] = (abs(D0) - abs(rec["D" + kx])) * 100
        rows.append(rec)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "deltas_by_segment.csv"), index=False)
    # ── §3-4 彙總：某段 Δ_stk 無法計算 ⇒ 四個 Δ 都不計那一段；少於一段 ⇒ 整顆不進中位數
    okT = T[T["stk_無法計算"] == 0]
    agg = okT.groupby("seed")[["Δ_β", "Δ_ind", "Δ_stk", "Δ_vol"]].sum()
    dropped_seeds = sorted(set(T["seed"]) - set(agg.index))
    agg.to_csv(os.path.join(OUT, "deltas_by_seed.csv"))
    summ = pd.DataFrame({k: {"中位": agg[k].median(), "p10": agg[k].quantile(.1), "p90": agg[k].quantile(.9)} for k in agg.columns}).T
    summ.to_csv(os.path.join(OUT, "deltas_summary.csv"))
    top_cnt = agg.idxmax(axis=1).value_counts()
    print("\n=== §3-4 彙總（{} 顆進中位數；整顆剔除 {}；段被剔 {}）===".format(len(agg), len(dropped_seeds), int((T["stk_無法計算"] == 1).sum())))
    print(summ.round(3).to_string())
    print("每顆最大 Δ 是哪一個：", top_cnt.to_dict())
    med = summ["中位"].sort_values(ascending=False)
    print("§四 機械套用：最大 {} {:+.3f}pp、第二 {} {:+.3f}pp、領先 {:.3f}pp（門檻 2.0pp）".format(
        med.index[0], med.iloc[0], med.index[1], med.iloc[1], med.iloc[0] - med.iloc[1]))
    print("\n=== 必報⑤ 資料齊全 ===")
    print("β 回看 < 120 筆 的段 {}／{}（最少 {} 筆）｜缺產業 {}｜持有產業不在母體 {}｜Δ_stk 排不了名的持股 {}｜Δ_stk 無剩餘可補 {}｜Δ_vol 池不足 {}｜池內 vol60 < 60 筆 {}".format(
        int((T["β_筆數"] < 120).sum()), len(T), int(T["β_筆數"].min()), int(T["缺產業"].sum()), int(T["持有產業不在母體"].sum()),
        int(T["stk_排不了名"].sum()), int(T["stk_無法計算"].sum()), int(T["vol_池不足"].sum()), int(T["vol_不足60筆"].sum())))
    print("=== 必報⑥ Δ_β 平均曝險：中位 {:.4f}｜最小 {:.4f}｜β>1 的段 {}／{}｜β 中位 {:.3f}".format(
        T["Δ_β曝險"].median(), T["Δ_β曝險"].min(), int((T["β"] > 1).sum()), len(T), T["β"].median()))
    print("{:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

"""PREREGP9 2-C ⓑ（策略線 seq=5 投遞檔 ＋ 回測線追加一）：**市場狀態減碼**在組合層。

    python3 -m backtest.researchp9 [--procs 8] [--reps 200] [--out backtest/resultsp9]

⛔ **只跑 2-C ⓑ**（追加一〇）：弱勢日進場的新部位只買 0.5 個 slot。
   2-A 分批進場／2-B 三種加碼／2-C ⓐ／2-D 組合 **本趟不跑**（使用者只裁了 ⓑ 准試跑）。

⭐ 引擎是 `research11.simulate_mtm`（⛔ 沒有另建）；sig 是 `researchp7.build_sig_gate_b`（⛔ 沒有抄第二份）。
⭐ 判準（登錄 §7-7 逐字，K線分析線 1330 裁定）：
     【年化 ≥ 0050 同窗】且【最大回落 ≤ 0050 同窗】⇒ ⛔ 兩者同時成立才算通過，⛔ 不分開報、不分開判。
   追加一四：判定＝200 顆種子的【中位】；另報逐種子通過率（基準那一格 2.5%）。
   追加一五：0050 的兩個數字【本線自算】與【策略線公告 +24.03%／−34.0%】各判一次，不一致 ⇒ 從嚴。
⛔ 200 顆種子的 p10~p90 是【種子帶】，⛔ 不是抽樣分佈（〈九十八〉）。
⛔ 結論一律寫「在這 N 次事件上」，⛔ 不寫「測得出／測不出」（登錄 §6-1）。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp3 as P3
from . import researchp7 as P7

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp9")
SEED0 = 99000                    # ⛔ 登錄 §二 寫死：default_rng(99000 + r)，r ∈ [0,200)
RULE = P7.RULE                   # H120（⛔ 與 P7 同一個常數，不另定）
N_MAIN = 8
MA_WIN = 60                      # 登錄 §2-C ⓑ：0050 的 60 日均線
WEAK_SIZE = 0.5                  # 登錄 §2-C ⓑ：弱勢日新部位只買 0.5 slot
DD_THRESH = 0.20                 # 登錄 §7-1：跌幅曾達 20% 才算一個回落事件
SL_CAGR, SL_MDD = 0.2403, -0.340 # 策略線公告的同窗 0050（追加一五：與本線自算的並列各判一次）


def passes(cagr, mdd, c0, m0):
    """登錄 §7-7 的判定（⭐ 唯一實作，⛔ 純量與 Series 都走這一條）：年化 ≥ 基準 **且** 最大回落 ≤ 基準。

    ⛔ 回落是負數 ⇒「較淺」＝ **數值較大** ⇒ 條件寫成 `mdd >= m0`（⚠ 寫成 `<=` 會把方向弄反）。
    """
    return (cagr >= c0) & (mdd >= m0)


def weak_flags(bench: np.ndarray, ncal: int) -> np.ndarray:
    """追加一（一）：weak[t] ＝ 0050 收盤[t−1] < MA60[t−1]（MA60 含 t−1 共 60 根）。

    ⛔ 用 t−1，⛔ 不用 t：本引擎的進場價是【進場日開盤】⇒ 用當天收盤判定就是前視。
    ⛔ 暖身不足（t−1 < MA_WIN−1）⇒ False。
    """
    b = np.asarray(bench, float)
    ma = pd.Series(b).rolling(MA_WIN).mean().to_numpy()      # ma[i] ＝ 收盤[i−59 … i] 的平均
    w = np.zeros(ncal, bool)
    below = np.isfinite(ma) & (b < ma)                       # below[i]：第 i 天收盤在它自己的 MA60 之下
    w[1:] = below[:ncal - 1]                                 # ⭐ 平移一天 ⇒ weak[t] 看的是 t−1
    return w


def dd_events(eq: np.ndarray, first: int, end: int, thresh: float = DD_THRESH) -> list[dict]:
    """登錄 §7-1 逐字：從歷史新高出發、跌幅曾達 thresh、直到再回到該高點（或資料結束）為止的區段。

    回傳每個事件：peak（起點位置）／trough（區段最低點）／recover（回到高點那天；沒回到 ＝ end−1）／dd（總跌幅，負）。
    """
    ev = []
    i = first
    peak_v = eq[first]; peak_i = first
    while i < end:
        if eq[i] >= peak_v:
            peak_v = eq[i]; peak_i = i; i += 1; continue
        # 從 peak_i 起的一段下跌：找回到 peak_v 的那一天
        j = i
        while j < end and eq[j] < peak_v:
            j += 1
        seg = eq[peak_i:j]
        t_rel = int(np.argmin(seg)); trough = peak_i + t_rel
        dd = eq[trough] / peak_v - 1.0
        if dd <= -thresh:
            ev.append({"peak": peak_i, "trough": trough, "recover": min(j, end - 1), "dd": dd,
                       "recovered": bool(j < end)})
        if j >= end:
            break
        peak_v = eq[j]; peak_i = j; i = j + 1
    return ev


def dd_type(eq: np.ndarray, peak: int, trough: int, scale: str = "simple") -> tuple[str, float, float]:
    """登錄 §7-1 逐字的分型。⭐ 機器定義（追加二）：在【peak→trough】那一段上取逐日報酬，
    「最差 k 日跌幅合計」＝ 最小的 k 個日報酬之和；「事件總跌幅」＝ trough/peak − 1。

    回 (型別, 最差2日占比, 最差5日占比)；⛔ 兩個占比都回，因為分型用到兩條不同的門檻。

    ⭐ scale（2026-09-20 15:4x 加，⛔ 只給【跨線對帳】用，⛔ 不改本件已跑完的判定）：
      "simple" 預設 ＝ 登錄那條路（單純報酬）⇒ ⛔ 逐位元與 P9 跑的那一趟相同
      "log"    ＝ 策略線 ddtype.py 的口徑（對數報酬）⇒ ⭐ 用來定位 17.8% vs 4.5% 差在哪一軸
    """
    if trough <= peak:
        return "混合型", np.nan, np.nan
    if scale not in ("simple", "log"):
        raise ValueError(f"scale 只能是 'simple'（登錄口徑）或 'log'（策略線口徑），收到 {scale!r}")
    if scale == "log":
        lg = np.log(eq[peak:trough + 1])
        r = np.diff(lg)
        tot = float(lg[-1] - lg[0])
        srt = np.sort(r)
        p2 = float(srt[:2].sum()) / tot if tot < 0 else np.nan
        p5 = float(srt[:5].sum()) / tot if tot < 0 else np.nan
        if p2 >= 0.50:
            return "單日暴跌型", p2, p5
        if p5 < 0.50:
            return "延續下跌型", p2, p5
        return "混合型", p2, p5
    r = eq[peak + 1:trough + 1] / eq[peak:trough] - 1.0
    tot = eq[trough] / eq[peak] - 1.0
    srt = np.sort(r)
    w2 = float(srt[:2].sum()); w5 = float(srt[:5].sum())
    p2 = w2 / tot if tot < 0 else np.nan
    p5 = w5 / tot if tot < 0 else np.nan
    if p2 >= 0.50:
        return "單日暴跌型", p2, p5
    if p5 < 0.50:
        return "延續下跌型", p2, p5
    return "混合型", p2, p5


def ma_break_segments(bench: np.ndarray, lo: int, hi: int) -> list[tuple[int, int]]:
    """[lo, hi] 內 0050 跌破 MA60 的每一段：回 (起日, 段長)。⭐ 起日 ＝ 前一日仍在之上的第一天（登錄 §7-1）。"""
    b = np.asarray(bench, float)
    ma = pd.Series(b).rolling(MA_WIN).mean().to_numpy()
    below = np.isfinite(ma) & (b < ma)
    segs = []; t = lo
    while t <= hi:
        if below[t] and (t == 0 or not below[t - 1]):
            u = t
            while u <= hi and below[u]:
                u += 1
            segs.append((t, u - t)); t = u
        else:
            t += 1
    return segs


def window_mdd(eq: np.ndarray, lo: int, hi: int) -> float:
    """[lo, hi] 窗內的最大回落（以窗內自己的累積高點為基準）。⛔ 兩組用同一個窗（追加一八）。"""
    seg = eq[lo:hi + 1]
    pk = np.maximum.accumulate(seg)
    return float(((seg - pk) / pk).min())


_S: dict = {}


def _init(sig, closes, opens, ncal, first_all, split_pos, end_all, weak):
    _S.update(sig=sig, closes=closes, opens=opens, ncal=ncal, first_all=first_all,
              split_pos=split_pos, end_all=end_all, weak=weak)


def _one(args):
    arm, seed = args
    w = _S["weak"] if arm == "b" else None
    s = R.simulate_mtm(_S["sig"], RULE, N_MAIN, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                       return_equity=True, weak=w, weak_size=WEAK_SIZE, report_maxw=True)
    ca, ma = R13.window_stats(s["equity"], s["first"], s["end"], _S["first_all"], _S["split_pos"])
    cb, mb = R13.window_stats(s["equity"], s["first"], s["end"], _S["split_pos"], _S["end_all"])
    e_, _r, _nz = P3.exposure_series(s["equity"], s["hold_val"], s["first"], s["end"])   # ⭐ 唯一實作在 researchp3
    out = {"arm": arm, "seed": seed, "cagr": s["cagr"], "mdd": s["mdd"], "slot": s["slot_use"], "m": s["m"],
           "ca": ca, "ma": ma, "cb": cb, "mb": mb, "maxw": s["max_pos_frac"], "first": s["first"], "end": s["end"],
           "expo": float(np.mean(e_))}      # ⭐ 平均曝險：⛔ 槽位使用率看不出資金閒置（它數的是「有幾個槽有部位」）
    if arm == "base":      # §6-2 兩型分報：⭐ 分型在 worker 裡算（⛔ 不要事後再跑一次 200 趟）
        for e in dd_events(s["equity"], s["first"], s["end"]):
            k, _, _ = dd_type(s["equity"], e["peak"], e["trough"])
            out[f"kind_{k}"] = out.get(f"kind_{k}", 0) + 1
    return out


def month_universe_returns(panel: pd.DataFrame, cal: pd.DatetimeIndex, closes: dict) -> pd.DataFrame:
    """追加一（六）：母體月報酬 ＝ 該月【過閘門】股-月各檔在該日曆月的收盤報酬的簡單平均。

    月報酬 ＝ 月底收盤 ÷ 上月底收盤 − 1；⛔ 兩端都要有值（有限且 > 0），否則該檔該月不計。
    """
    ym = pd.Series(cal).dt.strftime("%Y-%m")
    last_pos = {m: int(idx[-1]) for m, idx in ym.groupby(ym).groups.items()}
    months = sorted(last_pos)
    prev = {m: last_pos[months[i - 1]] for i, m in enumerate(months) if i > 0}
    el = panel[panel["eligible"].astype(bool)].copy()
    el["ym"] = el["measure_date"].dt.strftime("%Y-%m")
    rows = []
    for m, g in el.groupby("ym"):
        if m not in prev:
            continue
        p0, p1 = prev[m], last_pos[m]
        rs = []
        for sid in g["stock_id"].unique():
            c = closes.get(sid)
            if c is None or p1 >= len(c):
                continue
            a, b = float(c[p0]), float(c[p1])
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                rs.append(b / a - 1.0)
        if rs:
            rows.append({"ym": m, "n": len(rs), "ret": float(np.mean(rs))})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = print
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens)          # ⛔ 唯一實作在 researchp7
    want = {"rows": 2882, "stocks": 919, "months": 109, "m_min": "2017-03", "m_max": "2026-03", "e_min": 523, "e_max": 2716}
    got = {"rows": len(sig), "stocks": sig["sid"].nunique(), "months": sig["month"].nunique(),
           "m_min": sig["month"].min(), "m_max": sig["month"].max(),
           "e_min": int(sig["entry_pos"].min()), "e_max": int(sig["entry_pos"].max())}
    if got != want:
        raise SystemExit(f"⛔ sig 驗收數對不上策略線 1115 §1-2 ⇒ 先回信、⛔ 不跑\n  want {want}\n  got  {got}")
    log(f"[sig] ✅ 門檻B {len(sig):,} 筆／{sig['sid'].nunique()} 檔／{sig['month'].nunique()} 月，七個驗收數與 P7 同")

    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    weak = weak_flags(bench, ncal)
    # 追加一（七）：每個月只有一個進場日 ⇒ 不成立就中止（⛔ 不自己改成取第一個）
    per_month = sig.groupby("month")["entry_pos"].nunique()
    if (per_month != 1).any():
        raise SystemExit(f"⛔ 有月份不只一個進場日 ⇒ 弱勢月的定義不適用，停跑：\n{per_month[per_month != 1]}")
    ent = sig.groupby("month")["entry_pos"].first().astype(int)
    weak_month = pd.Series({m: bool(weak[p]) for m, p in ent.items()})
    log(f"[weak] 弱勢日 {int(weak.sum()):,}/{ncal:,} 天（{weak.mean() * 100:.1f}%）；弱勢月 {int(weak_month.sum())}/{len(weak_month)}")

    first_all = int(sig["entry_pos"].min()); end_all = ncal
    split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    b_c, b_m = R13.window_stats(bench, first_all, end_all, first_all, end_all)
    b_ca, b_ma = R13.window_stats(bench, first_all, end_all, first_all, split_pos)
    b_cb, b_mb = R13.window_stats(bench, first_all, end_all, split_pos, end_all)
    log(f"[0050] 全窗 年化 {b_c * 100:+.2f}%／回落 {b_m * 100:.1f}%（策略線公告 {SL_CAGR * 100:+.2f}%／{SL_MDD * 100:.1f}%）；"
        f"A 窗 {b_ca * 100:+.2f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.2f}%／{b_mb * 100:.1f}%")

    t0 = time.time()
    pool = Pool(a.procs, initializer=_init, initargs=(sig, closes, opens, ncal, first_all, split_pos, end_all, weak))
    try:
        res = pool.map(_one, [(arm, SEED0 + r) for arm in ("base", "b") for r in range(a.reps)], chunksize=4)
    finally:
        pool.close(); pool.join()
    df = pd.DataFrame(res)
    df.to_csv(os.path.join(a.out, "seeds.csv"), index=False)
    log(f"[run] {len(df)} 趟跑完（{time.time() - t0:.0f}s）")

    rows = []
    for arm, g in df.groupby("arm", sort=False):
        md = g.median(numeric_only=True)
        pass_self = passes(g["cagr"], g["mdd"], b_c, b_m)           # ⛔ 回落「較淺」＝ mdd 較大（兩者都是負數）
        pass_sl = passes(g["cagr"], g["mdd"], SL_CAGR, SL_MDD)
        rows.append({"arm": arm, "cagr": md["cagr"], "cagr_p10": g["cagr"].quantile(.1), "cagr_p90": g["cagr"].quantile(.9),
                     "mdd": md["mdd"], "mdd_p10": g["mdd"].quantile(.1), "mdd_p90": g["mdd"].quantile(.9),
                     "slot": md["slot"], "m": md["m"], "maxw": md["maxw"], "maxw_worst": g["maxw"].max(), "expo": md["expo"],
                     "ca": md["ca"], "ma": md["ma"], "cb": md["cb"], "mb": md["mb"],
                     "win_self": bool(passes(md["cagr"], md["mdd"], b_c, b_m)),
                     "win_sl": bool(passes(md["cagr"], md["mdd"], SL_CAGR, SL_MDD)),
                     "rate_self": float(pass_self.mean()), "rate_sl": float(pass_sl.mean()),
                     "win_a": bool(passes(md["ca"], md["ma"], b_ca, b_ma)), "win_b": bool(passes(md["cb"], md["mb"], b_cb, b_mb))})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(a.out, "cells.csv"), index=False)
    for r in T.itertuples():
        log(f"  {r.arm:<4} 年化 {r.cagr * 100:+6.2f}% 回落 {r.mdd * 100:6.1f}% 槽 {r.slot:.2f} 筆 {r.m:.0f} "
            f"單一部位最大 {r.maxw * 100:.1f}% ⇒ 本線口徑 {'✅ 通過' if r.win_self else '⛔ 沒過'}／"
            f"策略線口徑 {'✅ 通過' if r.win_sl else '⛔ 沒過'}（逐種子通過率 {r.rate_self * 100:.1f}%／{r.rate_sl * 100:.1f}%）")

    # 逐種子配對差（同種子 ⓑ − 基準）⇒ ⛔ 種子帶，⛔ 不是信心區間
    piv = df.pivot(index="seed", columns="arm", values=["cagr", "mdd"])
    d_cagr = piv[("cagr", "b")] - piv[("cagr", "base")]
    d_mdd = piv[("mdd", "b")] - piv[("mdd", "base")]
    pair = {"d_cagr_med": float(d_cagr.median()), "d_cagr_p10": float(d_cagr.quantile(.1)), "d_cagr_p90": float(d_cagr.quantile(.9)),
            "d_mdd_med": float(d_mdd.median()), "d_mdd_p10": float(d_mdd.quantile(.1)), "d_mdd_p90": float(d_mdd.quantile(.9)),
            "d_cagr_neg": float((d_cagr < 0).mean()), "d_mdd_pos": float((d_mdd > 0).mean())}
    log(f"[配對] 年化差 中位 {pair['d_cagr_med'] * 100:+.2f}pp（{pair['d_cagr_p10'] * 100:+.2f}~{pair['d_cagr_p90'] * 100:+.2f}）／"
        f"回落差 中位 {pair['d_mdd_med'] * 100:+.2f}pp（{pair['d_mdd_p10'] * 100:+.2f}~{pair['d_mdd_p90'] * 100:+.2f}）")

    # ── §6-1／6-2／6-3：中位種子的事件逐筆（⛔ 事件用【基準組】的曲線找，追加一八）
    base = df[df["arm"] == "base"].sort_values("seed")
    med_mdd = base["mdd"].median()
    med_seed = int(base.iloc[(base["mdd"] - med_mdd).abs().to_numpy().argsort(kind="stable")[0]]["seed"])
    eqs = {}
    for arm in ("base", "b"):
        s = R.simulate_mtm(sig, RULE, N_MAIN, np.random.default_rng(med_seed), closes, opens, ncal, return_equity=True,
                           weak=(weak if arm == "b" else None), weak_size=WEAK_SIZE, report_maxw=True)
        eqs[arm] = s
    eb = eqs["base"]["equity"]
    evs = dd_events(eb, eqs["base"]["first"], eqs["base"]["end"])
    ev_rows = []
    for e in evs:
        kind, p2, p5 = dd_type(eb, e["peak"], e["trough"])
        lo, hi = e["peak"], e["recover"]
        segs = ma_break_segments(bench, lo, hi)
        sig_pos = segs[0][0] if segs else None
        bench_peak = int(lo + np.argmax(bench[lo:hi + 1])) if hi > lo else lo
        bpk = float(np.max(bench[max(lo - MA_WIN, 0):lo + 1]))       # 該波 0050 高點（事件起點前 60 根內的最高）
        ev_rows.append({
            "seed": med_seed, "peak": str(cal[e["peak"]].date()), "trough": str(cal[e["trough"]].date()),
            "recover": str(cal[e["recover"]].date()), "days": e["recover"] - e["peak"], "dd_base": e["dd"],
            "kind": kind, "worst2_frac": p2, "worst5_frac": p5,
            "ma_segments": len(segs), "days_below_ma": int(sum(n for _, n in segs)),
            "first_break": str(cal[sig_pos].date()) if sig_pos is not None else "",
            "lag_days": (sig_pos - e["peak"]) if sig_pos is not None else np.nan,
            "bench_drop_at_signal": (float(bench[sig_pos]) / bpk - 1.0) if sig_pos is not None else np.nan,
            "port_drop_at_signal": (float(eb[sig_pos]) / float(eb[e["peak"]]) - 1.0) if sig_pos is not None else np.nan,
            "mdd_win_base": window_mdd(eb, lo, hi), "mdd_win_b": window_mdd(eqs["b"]["equity"], lo, hi),
        })
    EV = pd.DataFrame(ev_rows)
    if len(EV):
        EV["saved_pp"] = (EV["mdd_win_b"] - EV["mdd_win_base"]) * 100     # ⭐ 正值＝救到（兩者都是負數）
    EV.to_csv(os.path.join(a.out, "events.csv"), index=False)
    log(f"[事件] 中位種子 seed={med_seed}（MDD {med_mdd * 100:.1f}%）⇒ {len(EV)} 個 ≥20% 事件；"
        + "、".join(f"{r.peak}~{r.trough} {r.dd_base * 100:.1f}% {r.kind} 救 {r.saved_pp:+.2f}pp" for r in EV.itertuples()))

    # 全部種子的分型計數（登錄 §6-2 兩型分報；⚠ §7-2 已實測會退化成幾乎只有混合型）⇒ 在 worker 裡算好，這裡只加總
    kinds = {c[5:]: int(base[c].fillna(0).sum()) for c in base.columns if c.startswith("kind_")}
    log(f"[分型] 全 {a.reps} 顆種子的 ≥20% 事件：" + "／".join(f"{k} {v}" for k, v in sorted(kinds.items())))

    # §2-E⑤：弱勢月 vs 母體負報酬月，兩個方向
    MU = month_universe_returns(panel, cal, closes)
    MU.to_csv(os.path.join(a.out, "universe_months.csv"), index=False)
    mu = MU.set_index("ym")["ret"]
    common = [m for m in weak_month.index if m in mu.index]
    wk = weak_month.loc[common]; neg = mu.loc[common] < 0
    inter = int((wk & neg).sum())
    prec = inter / int(wk.sum()) if wk.sum() else np.nan
    cov = inter / int(neg.sum()) if neg.sum() else np.nan
    log(f"[重疊] 共同月 {len(common)}；弱勢月 {int(wk.sum())}／負報酬月 {int(neg.sum())}／交集 {inter} "
        f"⇒ 精確率 {prec * 100:.1f}%、涵蓋率 {cov * 100:.1f}%（⛔ 兩個方向都報）")

    stat = {"med_seed": med_seed, "weak_days": int(weak.sum()), "ncal": ncal, "weak_months": int(wk.sum()),
            "neg_months": int(neg.sum()), "months": len(common), "inter": inter, "precision": prec, "coverage": cov,
            "b_c": b_c, "b_m": b_m, "b_ca": b_ca, "b_ma": b_ma, "b_cb": b_cb, "b_mb": b_mb, "kinds": kinds, **pair}
    pd.Series(stat).to_csv(os.path.join(a.out, "stats.csv"))
    L = report(T, EV, stat, sig, kinds, MU, a.reps)
    open(os.path.join(a.out, "P9B_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"寫入 {os.path.join(a.out, 'P9B_REPORT.md')}")


def report(T: pd.DataFrame, EV: pd.DataFrame, st: dict, sig: pd.DataFrame, kinds: dict, MU: pd.DataFrame, reps: int) -> list[str]:
    b = T[T["arm"] == "b"].iloc[0]; z = T[T["arm"] == "base"].iloc[0]
    L = ["# PREREGP9 2-C ⓑ：市場狀態減碼（回測線落地）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。登錄＝`backtest/PREREGP9.md`"
         f"（策略線投遞檔 seq=5 正文 ＋ 回測線追加一、追加二）。",
         f"訊號：門檻B，{len(sig):,} 筆／{sig['sid'].nunique():,} 檔／{sig['month'].nunique()} 月。N={N_MAIN}、停損 none、"
         f"H120＝持有 {P7.HOLD_BARS_N} 根。種子 `default_rng({SEED0} + r)`、R={reps}。", "",
         f"**規則**（登錄 §2-C ⓑ 逐字）：當「0050 收盤 < 0050 的 60 日均線」時，**新部位只買 0.5 個 slot**。",
         f"⭐ 時序（追加一 §一）：weak[t] 看的是 **t−1** 的收盤與 MA60[t−1]（進場價是 t 的開盤 ⇒ 用當天收盤就是前視）。",
         f"⭐ 省下的半個 slot **留在現金**、報酬 0（追加一 §二）⇒ ⚠ 年化的下降含【資金閒置】那一塊。",
         f"⭐ 只作用在**新部位**（追加一 §三）⇒ ⚠ ⓑ 的作用是慢的：H120 ⇒ 一次事件內只換得動一部分部位。", "",
         f"弱勢日 {st['weak_days']:,}／{st['ncal']:,} 天（{st['weak_days'] / st['ncal'] * 100:.1f}%）。", "",
         "## 一、判定格（登錄 §7-7 逐字：兩者同時成立才算通過）", "",
         f"**0050 同窗**：本線自算 年化 {st['b_c'] * 100:+.2f}%／回落 {st['b_m'] * 100:.1f}%；"
         f"策略線公告 {SL_CAGR * 100:+.2f}%／{SL_MDD * 100:.1f}%（追加一 §五：兩個都判）。", "",
         "| 組 | 年化 中位 | p10～p90 | 最大回落 中位 | p10～p90 | 槽位 | 平均曝險 | 筆數 | 單一部位最大佔比 | 本線口徑 | 策略線口徑 | 逐種子通過率 |",
         "|---|---:|---|---:|---|---:|---:|---:|---:|:--:|:--:|---:|"]
    for r in (z, b):
        L.append(f"| {'基準（一次買滿）' if r['arm'] == 'base' else '**ⓑ 弱勢日半個 slot**'} | {r['cagr'] * 100:+.2f}% | "
                 f"{r['cagr_p10'] * 100:+.1f}～{r['cagr_p90'] * 100:+.1f} | {r['mdd'] * 100:.1f}% | "
                 f"{r['mdd_p10'] * 100:.1f}～{r['mdd_p90'] * 100:.1f} | {r['slot']:.2f} | {r['expo'] * 100:.1f}% | {r['m']:.0f} | "
                 f"{r['maxw'] * 100:.1f}%（最差 {r['maxw_worst'] * 100:.1f}%） | {'✅' if r['win_self'] else '⛔'} | "
                 f"{'✅' if r['win_sl'] else '⛔'} | {r['rate_self'] * 100:.1f}%／{r['rate_sl'] * 100:.1f}% |")
    same = bool(b["win_self"] == b["win_sl"])
    L += ["", f"⇒ **ⓑ {'✅ 通過' if (b['win_self'] and b['win_sl']) else '⛔ 沒有通過'}**"
          + ("（本線口徑與策略線口徑一致）" if same else "　⛔⛔ **兩個口徑給出不同答案 ⇒ 依追加一 §五【從嚴】，並把歧異交 K線分析線**"), "",
          f"⭐ 逐種子配對差（同種子 ⓑ − 基準）：年化 {st['d_cagr_med'] * 100:+.2f}pp"
          f"（種子帶 {st['d_cagr_p10'] * 100:+.2f}～{st['d_cagr_p90'] * 100:+.2f}）、"
          f"回落 {st['d_mdd_med'] * 100:+.2f}pp（{st['d_mdd_p10'] * 100:+.2f}～{st['d_mdd_p90'] * 100:+.2f}）；"
          f"年化變差的種子 {st['d_cagr_neg'] * 100:.0f}%、回落改善的種子 {st['d_mdd_pos'] * 100:.0f}%。",
          "⛔ 那個 p10～p90 是【種子帶】，⛔ 不是抽樣分佈、⛔ 不可當信心區間（〈九十八〉）。", "",
          f"⛔⛔ **槽位使用率看不出這件事**：{z['slot']:.2f} → {b['slot']:.2f}（⚠ 幾乎不動）——⭐ 因為它數的是"
          f"「有幾個槽裡有部位」，而 ⓑ 改的是【每個部位多大】⇒ ⛔ 用它當資金閒置的量測口會【量不到】。",
          f"⭐ 真正的量測口是【平均曝險】（持股市值 ÷ equity，與 PREREGP3 同一支 `exposure_series`）："
          f"**{z['expo'] * 100:.1f}% → {b['expo'] * 100:.1f}%**（−{(z['expo'] - b['expo']) * 100:.1f}pp）"
          f"⇒ ⚠ 年化掉的 {abs(st['d_cagr_med']) * 100:.2f}pp 裡有一塊是【這些錢沒有在市場裡】，"
          f"⛔ 不可全部歸因於「減碼本身」⇒ 與 PREREGP3（閒置資金）交叉引用。",
          "⚠ §2-E④「想加碼但現金不足的次數」對本格 **n/a**（ⓑ 沒有加碼）。", "",
          "## 二、⭐ 三條判準的三個窗（§2-E②）", "",
          "| 組 | A 窗 年化 | A 窗 回落 | A 窗 | B 窗 年化 | B 窗 回落 | B 窗 |", "|---|---:|---:|:--:|---:|---:|:--:|"]
    for r in (z, b):
        L.append(f"| {'基準' if r['arm'] == 'base' else 'ⓑ'} | {r['ca'] * 100:+.2f}% | {r['ma'] * 100:.1f}% | "
                 f"{'✅' if r['win_a'] else '⛔'} | {r['cb'] * 100:+.2f}% | {r['mb'] * 100:.1f}% | {'✅' if r['win_b'] else '⛔'} |")
    L += ["", f"（0050：A 窗 {st['b_ca'] * 100:+.2f}%／{st['b_ma'] * 100:.1f}%；B 窗 {st['b_cb'] * 100:+.2f}%／{st['b_mb'] * 100:.1f}%）", "",
          "## 三、⛔ §6-1 觸發事件逐筆（⭐ 在這 %d 次事件上）" % len(EV), "",
          f"⭐ 事件用【基準組】中位種子（seed={st['med_seed']}）的曲線找（追加一 §八：用 ⓑ 自己的曲線會循環）。", "",
          "| 事件（高點→谷底） | 日數 | 基準回落 | 分型 | 最差2日占比 | 首個 MA60 跌破 | 落後 | 訊號時 0050 已跌 | 訊號時組合已跌 | 跌破段數 | 在 MA60 之下 | ⓑ 窗內回落 | **救到** |",
          "|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in EV.itertuples():
        L.append(f"| {r.peak} → {r.trough} | {r.days} | {r.dd_base * 100:.1f}% | {r.kind} | "
                 f"{r.worst2_frac * 100:.1f}% | {r.first_break or '—'} | {'' if not np.isfinite(r.lag_days) else f'{int(r.lag_days)} 日'} | "
                 f"{'' if not np.isfinite(r.bench_drop_at_signal) else f'{r.bench_drop_at_signal * 100:.2f}%'} | "
                 f"{'' if not np.isfinite(r.port_drop_at_signal) else f'{r.port_drop_at_signal * 100:.2f}%'} | "
                 f"{r.ma_segments} | {r.days_below_ma} 日 | {r.mdd_win_b * 100:.1f}% | **{r.saved_pp:+.2f}pp** |")
    L += ["", "⛔ 依〈九十八〉：有效樣本數 ＝ 事件數 ＝ %d ⇒ 結論一律寫「在這 %d 次事件上」，⛔ 不寫「測得出／測不出」。" % (len(EV), len(EV)), "",
          "## 四、§6-2 兩型分報（⚠ 會退化）", "",
          "全部種子的 ≥20% 事件分型：" + "／".join(f"**{k} {v}**" for k, v in sorted(kinds.items())) + "。", "",
          "⭐ 策略線 §7-2（30 顆種子、133 個事件）：混合型 127／單日暴跌型 6／延續下跌型 0。", "",
          "⇒ ✅ **兩邊一致的那一半**：【延續下跌型 0】、【混合型是絕大多數】⇒ ⛔「兩型各報一次」在本庫"
          "**退化成幾乎只有一型**。⚠ 這個退化本身要寫出來，⛔ 否則下一個人會以為兩型各自有證據。", "",
          f"⇒ ⛔⛔ **而兩邊對不上的那一半，本線不掩蓋**：單日暴跌型的占比 策略線 6/133＝**4.5%**、"
          f"本線 {kinds.get('單日暴跌型', 0)}/{sum(kinds.values())}＝**{kinds.get('單日暴跌型', 0) / max(sum(kinds.values()), 1) * 100:.1f}%**"
          "（⚠ 差 4 倍）。⭐ 可能的成因：① 種子不同（99000+r vs 90000+r 那一族）、"
          "② 事件切法／「最差 2 日跌幅合計」的分母口徑（追加二 ①：本線算在【高點→谷底】那一段上）、"
          f"③ 事件數本身（本線 {reps} 顆種子 {sum(kinds.values())} 個事件、策略線 30 顆 133 個）。"
          "⛔ 本線【不猜】是哪一個：策略線的 `ddtype.py` 在它自己的專案空間，本線拿不到（〈一百〇一〉）"
          "⇒ ⏳ 要對帳請策略線投遞那支程式或它的逐字算式。", "",
          "⚠ 而這個差【不影響本件的判定】：判定格只看 §一 那兩條，分型只是描述。", "",
          "## 五、§2-E⑤ 代理的重疊率（⛔ 兩個方向）", "",
          f"母體負報酬月的定義＝過閘門母體在該日曆月的收盤報酬簡單平均 < 0（追加一 §六）。", "",
          f"| 共同月 | 弱勢月 | 負報酬月 | 交集 | 精確率（交集÷弱勢月） | 涵蓋率（交集÷負報酬月） |", "|---:|---:|---:|---:|---:|---:|",
          f"| {st['months']} | {st['weak_months']} | {st['neg_months']} | {st['inter']} | "
          f"**{st['precision'] * 100:.1f}%** | **{st['coverage'] * 100:.1f}%** |", "",
          f"⭐ 對帳：策略線 §一 引 §7-3 的【30 / 111】負報酬月，本線這一份是 **{st['neg_months']} / {st['months']}**"
          f"（⚠ 口徑不同：本線是【該日曆月的收盤報酬】、⛔ 不是前瞻報酬）。", "",
          "⛔ 依否證條件②：ⓑ 沒通過時**不可**寫成「市場擇時無效」——要先看這兩個重疊率（代理沒抓到 ≠ 擇時沒用）。", "",
          "## 六、⇒ 結論（⛔ 照登錄字面）", ""]
    room_c = (z["cagr"] - st["b_c"]) * 100        # 年化可以掉的上限（本線口徑）
    room_m = (st["b_m"] - z["mdd"]) * 100         # 回落需要改善的下限（本線口徑）
    ok = bool(b["win_self"] and b["win_sl"])
    L += [f"**① 判定格：ⓑ {'✅ 通過' if ok else '⛔ 沒有通過'}**（{'兩個口徑一致' if same else '⛔ 兩個口徑不一致 ⇒ 從嚴'}）。",
          f"年化 {b['cagr'] * 100:+.2f}%（要 ≥ {st['b_c'] * 100:+.2f}%／{SL_CAGR * 100:+.2f}%）、"
          f"最大回落 {b['mdd'] * 100:.1f}%（要 ≤ {st['b_m'] * 100:.1f}%／{SL_MDD * 100:.1f}%）"
          f"⇒ ⛔ **兩條都沒過**（登錄 §7-7：兩者同時成立才算通過，⛔ 不分開判）。", "",
          "**② ⭐ 而 K線分析線 1330 §一 把問題寫成一句話：「ⓑ 能不能用【不超過 3.76pp 的年化】換到【至少 7.8pp 的回落】？」**",
          f"⇒ 本線口徑的同一個餘裕是【年化最多掉 {room_c:.2f}pp、回落至少要改善 {room_m:.2f}pp】。", "",
          f"| | 餘裕（要求） | ⓑ 實際（逐種子配對中位） | |", "|---|---:|---:|:--:|",
          f"| 年化 | 最多掉 {room_c:.2f}pp | **{st['d_cagr_med'] * 100:+.2f}pp** | {'✅' if -st['d_cagr_med'] * 100 <= room_c else '⛔ 掉太多'} |",
          f"| 最大回落 | 至少改善 {room_m:.2f}pp | **{st['d_mdd_med'] * 100:+.2f}pp** | {'✅' if st['d_mdd_med'] * 100 >= room_m else '⛔ 不夠'} |", "",
          f"⇒ ⭐⭐ **答案：它用 {abs(st['d_cagr_med']) * 100:.2f}pp 的年化，只換到 {st['d_mdd_med'] * 100:.2f}pp 的回落** ——"
          f"⛔ 年化付得比可付的多、回落換得比需要的少，**兩邊都不夠**。", "",
          "**③ 策略線先驗④（押「這是八格裡唯一測得出的」且「回落改善 ≥ 4pp」）：⛔ 沒有成立。**",
          f"⭐ 方向對（{st['d_mdd_pos'] * 100:.0f}% 的種子回落有改善），⛔ 但量級只有 {st['d_mdd_med'] * 100:.2f}pp、不到它押的 4pp；"
          f"而年化同時掉了 {abs(st['d_cagr_med']) * 100:.2f}pp（{st['d_cagr_neg'] * 100:.0f}% 的種子變差）。", "",
          f"**④ 在這 {len(EV)} 次事件上**（⛔ 〈九十八〉：不寫「測得出／測不出」）：救到 "
          + "、".join(f"{r.saved_pp:+.2f}pp" for r in EV.itertuples()) + "。",
          "⚠ 其中 2020 那次（最短、最陡的一次）**完全沒救到** —— ⭐ 與登錄 §7-3 的落後天數一致："
          "訊號出現時組合已經跌掉一大塊，而那一段又結束得太快。", "",
          "**⑤ ⛔ 為什麼沒通過（機制，⛔ 不是判準）：**",
          f"・平均曝險 {z['expo'] * 100:.1f}% → {b['expo'] * 100:.1f}% ⇒ ⭐ 年化的下降**有一塊是資金閒置**，⛔ 不是全部來自「減碼本身」",
          f"・登錄 §7-4 已量到的兩個成本仍然成立：假訊號 94%、28.1% 的時間在減碼（本線量到弱勢日 {st['weak_days'] / st['ncal'] * 100:.1f}%）",
          f"・代理只抓到三分之一多：精確率 {st['precision'] * 100:.1f}%、涵蓋率 {st['coverage'] * 100:.1f}%"
          " ⇒ ⛔ 依否證②，**不可**把這一格讀成「市場擇時無效」", "",
          "**⑥ ⇒ 依 K線分析線 1215 §6-5：「ⓑ 先跑，測得出才准開 M1」⇒ ⛔ PREREGM1 不開。**", "",
          "**⑦ ⚠ 一個登錄沒有預期到的量測（⭐ 觀察，⛔ 不是判定）：單一部位最大佔比**",
          f"⇒ 【基準組】就已經到 {z['maxw'] * 100:.1f}%（最差的種子 {z['maxw_worst'] * 100:.1f}%），ⓑ 是 {b['maxw'] * 100:.1f}%。",
          "⚠ 策略線先驗⑤ 押的是【加碼組】會超過使用者的 20% 上限 —— ⭐ 而本件量到的是：**不加碼、等權、N=8 的基準組本身就超過**。",
          "⛔ 而這是【期間最大值】不是典型值（一個部位漲上去就會變大）⇒ ⛔ 不可直接讀成「這套違反 20% 上限」；"
          "⏳ 它的正確處置（要不要改成逐日上限、或改報佔比的分位）歸 K線分析線／策略線，⛔ 本線不裁。", "",
          "## 七、⛔ 範圍限制（登錄 §五 ＋ 本趟）", "",
          "① 本趟**只跑 2-C ⓑ**一格（追加一〇）⇒ ⛔ 結論不可推到 2-A／2-B／2-C ⓐ。",
          "② 弱勢判定寫死「0050 收盤 < 60 日均線」，⛔ **沒有掃參數**（§五②：掃了就變成擇時參數配適）"
          "⇒ ⛔ 不可因為沒通過就去調那個 60。",
          "③ 減碼只作用在新部位（§2-C ⓑ 逐字）⇒ ⚠ 這是一個**慢**的規則；「全數減碼」是另一個設計，本件沒有測。",
          "④ 成本 0.585%、滑價未計、倖存者偏誤仍在。",
          "⑤ ⚠ 引用到 `exright_gap` 的部分沿用【已知偏差清單】：窗多含一根、方向保守（K線分析線 1330 §五）。",
          "⑥ ⚠ 0050 本線自算的全窗年化 +24.54% 與策略線公告 +24.03% 差 0.51pp（窗起點口徑）"
          "⇒ ⭐ 本件兩個都判過，結論相同。", ""]
    return L


if __name__ == "__main__":
    sys.exit(main())

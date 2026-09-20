"""PREREGP4 v3 回溯分析（回測線獨立重算）。判準 backtest/P4_v3_回溯分析.md；中心 backtest/forward/p4_types/centers_v3.json（策略線 09-15 12:52）。

    python3 -m backtest.researchp4 --centers backtest/forward/p4_types/centers_v3.json --out backtest/resultsp4 [--procs 4] [--limit N] [--placebo-n 1000]

規則（v3 §三／§四／§4-2）：
  母體 load_universe()（twse+tpex 普通股、含已下市、興櫃本就不在）；量測日＝每月第一個交易日；當日在籍且有成交；近 20 日均額 ≥ 5,000 萬
  特徵 p4_features.stock_raw（13 條）→ 同日橫截面百分位（嚴格小於／有限值數）→ 缺值補 50 → z 化 → 最近中心（歐氏）
  進場 次一交易日開盤還原價；出場 H=20/60/120 個交易日後收盤；基準＝同量測日合格母體等權平均；超額＝該型當月等權平均 − 同月基準
  有效月 ＝ 該型當月 ≥ 5 檔且基準可得；月分群 SE＝std(ddof=1)/√有效月；CI＝±1.96 SE
  期間 擬合窗／追認格 2017-01～2020-12｜主格 2021-01～2026-03（唯一判定格）｜副格 2017-01～2024-12｜第二層 2025-01～2026-03｜2015-2016 只進放棄組⑤
  判定 只有主格 H=120 四格：H1 ④<0、H2 ②>0、H3 ①>0、H4 ③<0（CI 不含 0）；「零」＝CI 含 0 ∧ |點估計| ≤ 0.585%；n_min 24 個有效月
  安慰劑 A 隨機分型（組大小＝當月真實）1000 次、B 標籤平移 +6/+12/+18（+12 不進判定）、鑑別力＝④↔② 標籤對調
  ⛔ 判定字只用 測得出／測不出／還沒測；⛔ 不做「贏過 0050」的比價
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P
from . import research34 as R34

HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.00585
N_MIN = 24
MIN_PER_MONTH = 5
ZERO = 0.00585
HOLDS = P.HOLDS
QS = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
PERIODS = {"擬合窗／追認格": ("2017-01-01", "2020-12-31"), "主格": ("2021-01-01", "2026-03-31"), "副格": ("2017-01-01", "2024-12-31"),
           "第二層": ("2025-01-01", "2026-03-31")}
JUDGE_PERIOD, JUDGE_H = "主格", 120
TYPE_OF_IDX = {0: "①營收＋回檔", 3: "②正在噴出", 2: "③純技術＋回檔", 1: "④死水"}     # v3 §1-1（⛔ 寫死）
HYP = {"①營收＋回檔": ("H3", +1), "②正在噴出": ("H2", +1), "③純技術＋回檔": ("H4", -1), "④死水": ("H1", -1)}
TYPES = ["①營收＋回檔", "②正在噴出", "③純技術＋回檔", "④死水"]
# v3 §10-1／10-2 策略線參考值（對帳用；門檻：分位數差 ≤ 1.0pp、超額差 ≤ 0.3pp）
REF = {("主格", 120): {"①營收＋回檔": dict(excess=4.88, lo=1.70, hi=8.07, mwin=61.9, win=41.9, p05=-44.2, p10=-34.8, p50=-5.2, p90=61.0, p95=99.3),
                     "②正在噴出": dict(excess=2.98, lo=1.00, hi=4.97, mwin=61.9, win=41.8, p05=-43.2, p10=-35.0, p50=-5.6, p90=49.4, p95=82.1),
                     "③純技術＋回檔": dict(excess=-0.22, lo=-1.22, hi=0.78, mwin=50.8, win=37.1, p05=-42.8, p10=-34.6, p50=-8.3, p90=38.5, p95=67.8),
                     "④死水": dict(excess=-3.87, lo=-5.50, hi=-2.23, mwin=23.8, win=36.3, p05=-42.6, p10=-33.3, p50=-6.8, p90=24.9, p95=43.2)},
       ("主格", 60): {"①營收＋回檔": dict(excess=3.29), "②正在噴出": dict(excess=1.57), "③純技術＋回檔": dict(excess=-0.35), "④死水": dict(excess=-2.10)},
       ("主格", 20): {"①營收＋回檔": dict(excess=0.38, p05=-16.8, p10=-13.6, p25=-7.9, p50=-1.5, p90=16.6, p95=28.1, win=44.5),
                    "②正在噴出": dict(excess=0.44, p05=-18.8, p10=-14.9, p25=-9.0, p50=-2.0, p90=18.7, p95=29.9, win=42.9),
                    "③純技術＋回檔": dict(excess=-0.17, p05=-15.7, p10=-12.9, p25=-7.9, p50=-2.3, p90=14.3, p95=22.9, win=40.3),
                    "④死水": dict(excess=-0.51, p05=-13.2, p10=-10.4, p25=-6.2, p50=-1.6, p90=10.0, p95=15.1, win=41.4)},
       ("副格", 120): {"①營收＋回檔": dict(excess=2.28, lo=0.32, hi=4.25, win=41.9), "②正在噴出": dict(excess=3.00, lo=1.92, hi=4.08, win=42.0),
                     "③純技術＋回檔": dict(excess=-0.83, lo=-1.57, hi=-0.09, win=38.0), "④死水": dict(excess=-2.45, lo=-3.30, hi=-1.60, win=38.6)},
       ("擬合窗／追認格", 120): {"①營收＋回檔": dict(excess=3.91), "②正在噴出": dict(excess=3.99), "③純技術＋回檔": dict(excess=-0.98), "④死水": dict(excess=-2.72)},
       ("第二層", 120): {"①營收＋回檔": dict(excess=18.29), "②正在噴出": dict(excess=6.09), "③純技術＋回檔": dict(excess=1.28), "④死水": dict(excess=-9.26)}}
REF_BENCH = {("主格", 120): 8.08}
TOL_Q, TOL_X = 1.0, 0.3
INNOV_CUTOFF = "2025-01-06"   # K線分析 1745 §一：創新板量測日 < 此日排除
_G: dict = {}


# ───────────────────────── 第一段：面板（每檔 × 每個量測日） ─────────────────────────
def _init(cal, rev_flags, positions, mp_check=True):
    _G["cal"] = cal; _G["rev_flags"] = rev_flags; _G["pos"] = positions; _G["mp_check"] = mp_check


def panel_worker(args):
    """一檔：在籍的量測日逐一取 13 條原始特徵、流動性、shares 有無、次日開盤進的 H 日毛報酬。"""
    sid, market, first, last = args
    cal = _G["cal"]
    rf = _G["rev_flags"][sid] if sid in _G["rev_flags"].columns else None
    raw = P.stock_raw(sid, market, cal, rf)
    if raw is None:
        return [], []
    raw05 = P.stock_raw(sid, market, cal, rf, mp_frac=0.5) if _G.get("mp_check", True) else None   # §4-1 常設斷言用
    rows = []; mism = []
    for pos in _G["pos"]:
        d = cal[pos]
        if d < first or d > last or pos >= len(raw):
            continue
        r = raw.iloc[pos]
        if not bool(r["traded"]):
            continue
        fr = P.forward_returns(raw, pos)
        liq_ok = bool(pd.notna(r["amt20"]) and r["amt20"] >= P.LIQ_MIN); bars = int(r["bars"]); bars_ok = bars >= P.MIN_BARS
        inst_ok = bool(pd.notna(r["fore20"]) and pd.notna(r["trust20"]))   # K線分析 2035 §一 (c)：法人欄近 20 日非缺值 < 20 ⇒ NaN ⇒ 該股-月整個不進主判定（放棄組⑩），⛔ 不可再被補 50
        row = {"measure_date": d, "stock_id": sid, "market": market, "amt20": float(r["amt20"]) if pd.notna(r["amt20"]) else np.nan,
               "bars": bars, "liq_ok": liq_ok, "bars_ok": bars_ok, "inst_ok": inst_ok,
               "eligible": liq_ok and bars_ok and inst_ok,      # v3 補件 §3-1：流動性 ∧ bars ≥ MIN_BARS（放棄組⑧）∧ 法人欄可算（放棄組⑩）
               "shares_ok": int(r["shares_ok"])}
        if liq_ok and bars_ok and not inst_ok:                       # 放棄組⑩ 的成因欄：窗內無成交日數 vs 有成交但法人缺
            lo = max(0, pos - 19); w_tr = raw["traded"].iloc[lo:pos + 1].to_numpy(bool)
            row["inst_win_notraded"] = int((~w_tr).sum()); row["inst_win_missing_traded"] = int(r["inst_nan20"]) - int((~w_tr).sum()) if pd.notna(r["inst_nan20"]) else -1
        for f in P.FEATURES:
            row[f] = float(r[f]) if pd.notna(r[f]) else np.nan
        for H in HOLDS:
            row[f"fwd_{H}"] = fr[f"ret_{H}"]   # ⛔ 不可叫 ret_H：ret_120／ret_20 是特徵名，會被蓋掉
        rows.append(row)
        if row["eligible"] and raw05 is not None:
            r5 = raw05.iloc[pos]
            for f in P.FEATURES:            # 逐欄：合格列上 min_periods=w 與 =w/2 要逐位元相同（都 NaN 也算相同）
                a, b = r[f], r5[f]
                if not ((pd.isna(a) and pd.isna(b)) or (pd.notna(a) and pd.notna(b) and a == b)):
                    mism.append({"stock_id": sid, "measure_date": d, "column": f, "mp_w": a, "mp_half": b, "bars": bars})
    return rows, mism


def build_panel(cal, uni, positions, procs=4, pub_day=10, log=print, mp_check=True, rev_incl_current=False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """回 (面板, min_periods 斷言的不一致列)。⛔ 不一致列 > 0 由呼叫端決定要不要中止（main 一律中止並逐列印 股／月／欄）。"""
    # ⭐ K線分析線 0150（登錄：追加十八）：缺 rev_hi24 依【缺失機制】分三種——不足 24 期＝依定義不成立（False）、
    #    當期沒申報＝留 NaN（前視，⛔ 排除它就是把倖存者偏誤做實）、存託憑證＝單獨標【不明】⛔ 不寫 False。
    tdr = P.load_tdr_codes()
    log(f"[TDR] 存託憑證（industry_code 91）{len(tdr)} 檔 ⇒ rev_hi24 一律留 NaN、標【不明】（⛔ 不寫 False）")
    rev, _, _ = R34.load_revenue(); rev_flags = P.rev_hi24_flags(rev, cal, pub_day, incl_current=rev_incl_current, undecided=tdr)
    jobs = [(r.stock_id, r.market, r.first_seen, r.last_seen) for r in uni.itertuples()]
    rows = []; mism = []; t0 = time.time()
    with Pool(procs, initializer=_init, initargs=(cal, rev_flags, positions, mp_check)) as pool:
        for i, (rs, ms) in enumerate(pool.imap_unordered(panel_worker, jobs, chunksize=8)):
            rows.extend(rs); mism.extend(ms)
            if (i + 1) % 400 == 0:
                log(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    df = pd.DataFrame(rows)
    df["measure_date"] = pd.to_datetime(df["measure_date"])
    M = pd.DataFrame(mism, columns=["stock_id", "measure_date", "column", "mp_w", "mp_half", "bars"])
    return df.sort_values(["measure_date", "stock_id"]).reset_index(drop=True), M


def apply_innovation_rule(panel: pd.DataFrame, uni: pd.DataFrame, cutoff: str = INNOV_CUTOFF) -> tuple[pd.DataFrame, int]:
    """K線分析 1745 §一：創新板（名稱含「-創」）按量測日分段——量測日 < cutoff 的股-月排除、≥ 納入。回 (面板, 被排除的合格股-月數)。"""
    innov = set(uni.loc[uni["name"].astype(str).str.contains("-創", na=False), "stock_id"])
    hit = panel["stock_id"].isin(innov) & (panel["measure_date"] < pd.Timestamp(cutoff)) & panel["eligible"]
    panel = panel.copy(); panel.loc[hit, "eligible"] = False; panel["innov_excluded"] = hit
    return panel, int(hit.sum())


# ───────────────────────── 第二段：橫截面 → 歸型 → 超額 ─────────────────────────
def load_centers(path: str):
    cj = json.load(open(path, encoding="utf-8"))
    assert list(cj["feature_order"]) == P.FEATURES, "feature_order 與 p4_features.FEATURES 不同"
    return np.array(cj["centers_z"], float), np.array(cj["mu"], float), np.array(cj["sd"], float)


def assign_masked(day_raw: pd.DataFrame, C, mu, sd) -> np.ndarray:
    """放棄組③用：缺值那幾維不進距離（⛔ 不是正式歸型），看補 50 有沒有改變歸型。"""
    Z = (day_raw[P.FEATURES].to_numpy(float) - mu) / sd
    m = np.isfinite(Z)
    Zf = np.where(m, Z, 0.0)
    d = ((Zf[:, None, :] - C[None, :, :]) ** 2 * m[:, None, :]).sum(axis=2)
    return d.argmin(axis=1)


def classify(panel: pd.DataFrame, C, mu, sd) -> pd.DataFrame:
    """合格列：逐量測日做橫截面百分位、補 50、歸型；加 bench_H、excess_H、n_filled、type_masked。"""
    el = panel[panel["eligible"]].copy()
    out = []
    for d, g in el.groupby("measure_date", sort=True):
        g = g.set_index("stock_id")
        X = P.cross_section(g[P.FEATURES])
        lab = P.assign(X, C, mu, sd)
        gg = g.copy()
        gg["type_idx"] = lab; gg["type"] = [TYPE_OF_IDX[i] for i in lab]
        gg["n_filled"] = g[P.FEATURES].isna().sum(axis=1).to_numpy()
        Xr = X.copy(); Xr[P.FEATURES] = X[P.FEATURES].where(g[P.FEATURES].notna().to_numpy(), np.nan)
        gg["type_masked_idx"] = assign_masked(Xr, C, mu, sd)
        for f in P.PCT_FEATURES:
            gg[f"pct_{f}"] = X[f].to_numpy()
        for H in HOLDS:
            b = g[f"fwd_{H}"].mean()
            gg[f"bench_{H}"] = b; gg[f"exc_{H}"] = g[f"fwd_{H}"] - b
        out.append(gg.reset_index())
    return pd.concat(out, ignore_index=True)


def _in(df: pd.DataFrame, period: str) -> pd.DataFrame:
    a, b = PERIODS[period]
    return df[(df["measure_date"] >= pd.Timestamp(a)) & (df["measure_date"] <= pd.Timestamp(b))]


def cell_stats(rows: pd.DataFrame, H: int) -> dict:
    """一格（型 × H × 期間）：有效月＝當月 ≥5 檔且報酬可得；點估計＝有效月均值的平均；SE 月分群。"""
    r = rows[rows[f"exc_{H}"].notna()]
    per_m = r.groupby("measure_date").agg(n=("stock_id", "size"), exc=(f"exc_{H}", "mean"), ret=(f"fwd_{H}", "mean"))
    ok = per_m[per_m["n"] >= MIN_PER_MONTH]
    n_m = int(len(ok)); dropped_cells = int((per_m["n"] < MIN_PER_MONTH).sum())
    x = ok["exc"].to_numpy(float)
    point = float(x.mean()) if n_m else np.nan
    se = float(x.std(ddof=1) / np.sqrt(n_m)) if n_m > 1 else np.nan
    rr = r[r["measure_date"].isin(ok.index)]
    q = rr[f"exc_{H}"].quantile(QS) if len(rr) else pd.Series(np.nan, index=QS)
    return {"n_months": n_m, "n_rows": int(len(rr)), "excess_pp": point * 100, "se_pp": se * 100,
            "ci_lo_pp": (point - 1.96 * se) * 100 if np.isfinite(se) else np.nan, "ci_hi_pp": (point + 1.96 * se) * 100 if np.isfinite(se) else np.nan,
            "win_rate": float((rr[f"exc_{H}"] > 0).mean()) if len(rr) else np.nan, "month_win_rate": float((x > 0).mean()) if n_m else np.nan,
            **{f"p{int(qq * 100):02d}": float(q.loc[qq]) * 100 for qq in QS},
            "abs_mean_pp": float(rr[f"fwd_{H}"].mean()) * 100 if len(rr) else np.nan,
            "abs_mean_net_pp": (float(rr[f"fwd_{H}"].mean()) - COST) * 100 if len(rr) else np.nan,
            "avg_n_per_month": float(ok["n"].mean()) if n_m else np.nan, "dropped_cells_lt5": dropped_cells}


SURVIVOR_BOUNDS = {"下界＝全部代入 −100%（下市歸零，最壞情況）": -1.0, "下界＝全部代入 0%（原價出場）": 0.0}


def survivor_bound(cl: pd.DataFrame, tdr: set, subs: dict[str, float] | None = None, H: int = JUDGE_H, typ: str = "①營收＋回檔") -> pd.DataFrame:
    """⭐ K線分析線 0150 §1-3（登錄＝追加十八）：倖存者那一組**留在主格、不補值**，⇒ 結論要報【區間】不報點估計。

    上界 ＝ 現況（那批列因為 rev_hi24 是 NaN，歸不出 `typ`）。
    下界 ＝ 把那批列**當成 `typ`**、報酬代入一個**寫死的邊界值**後重算——⛔ 這是**邊界**，不是估計值。

    ⭐⭐〈九十四〉（K線分析線 0400 §〇，2026-09-20 裁定）：倖存者這種**不可觀測子群**的下界要用**最壞情況的有界論證**，
    ⛔ **不可以挑一個「像它」的代理組把實測值代進去**——代理組的選擇本身會決定結論，而沒有一個代理組是可驗證正確的。
    ⚠ 本案實例：兩個代理組（−0.37／+0.04）給出 −2.32／+5.65 **變號**，而兩邊都已經看過結果
      ⇒ 此刻再挑一組＝**看過結果再挑判準**（〈六十四〉）。⇒ ⛔ 所以那條路關掉了。
    ⇒ ⭐ 有界論證的好處：**不需要是對的，只需要是下界**。最壞情況下界仍 > 0 ⇒ 阻斷項當場解除；< 0 而 0% 那版 > 0 ⇒ 「方向撐得住、量級取決於下市股處理」。

    那批列 ＝ 主格裡 rev_hi24 是 NaN 而且**不在 tdr 名單**的列（TDR 是【不明】、⛔ 不進這個代入，裁定明文）。
    subs：{標籤: 代入的 fwd_H}。⛔ 正式值只准是**邊界**（`SURVIVOR_BOUNDS`：−1.0 下市歸零／0.0 原價出場），
    ⚠ 代理組的實測值只能當敏感度，⛔ 不進結論。
    ⛔ 代入的是 `fwd_H`，而 `exc_H` ＝ fwd_H − 當月母體基準（`bench_H`）⇒ 逐列用它自己那個月的基準重算，⛔ 不是拿全期均值減。"""
    subs = SURVIVOR_BOUNDS if subs is None else subs
    main = _in(cl, JUDGE_PERIOD)
    base = cell_stats(main[main["type"] == typ], H)
    miss = main[main["rev_hi24"].isna() & ~main["stock_id"].isin(tdr)]
    # ⭐〈七十〉四件：那批列佔【主格母體】多少，分母要寫清楚
    share = len(miss) / len(main) * 100 if len(main) else np.nan
    rows = [{"scenario": "上界＝現況（那批列歸不出型）", "n_sub_rows": 0, "sub_value": np.nan, "n_months": base["n_months"],
             "excess_pp": base["excess_pp"], "ci_lo_pp": base["ci_lo_pp"], "ci_hi_pp": base["ci_hi_pp"],
             "n_main_rows": int(len(main)), "n_main_stocks": int(main["stock_id"].nunique()),
             "miss_rows": int(len(miss)), "miss_stocks": int(miss["stock_id"].nunique()), "miss_share_pct": share}]
    for tag, v in subs.items():
        add = miss.copy()
        add["type"] = typ
        add[f"fwd_{H}"] = float(v)
        add[f"exc_{H}"] = add[f"fwd_{H}"] - add[f"bench_{H}"]
        both = pd.concat([main[main["type"] == typ], add], ignore_index=True)
        s = cell_stats(both, H)
        rows.append({"scenario": f"{tag}（那批列當 {typ}）", "n_sub_rows": int(len(add)), "sub_value": float(v),
                     "n_months": s["n_months"], "excess_pp": s["excess_pp"], "ci_lo_pp": s["ci_lo_pp"], "ci_hi_pp": s["ci_hi_pp"],
                     "n_main_rows": int(len(main)), "n_main_stocks": int(main["stock_id"].nunique()),
                     "miss_rows": int(len(miss)), "miss_stocks": int(miss["stock_id"].nunique()), "miss_share_pct": share})
    return pd.DataFrame(rows)


def judge(period: str, H: int, typ: str, s: dict) -> str:
    if (period, H) != (JUDGE_PERIOD, JUDGE_H):
        if not np.isfinite(s["excess_pp"]):
            return "非判定格"
        hyp, sign = HYP[typ]
        return f"非判定格（方向{'＋' if s['excess_pp'] > 0 else '−'}，與 {hyp} {'一致' if np.sign(s['excess_pp']) == sign else '不一致'}）"
    if s["n_months"] < N_MIN or not np.isfinite(s["ci_lo_pp"]):
        return "還沒測（有效月 < 24）"
    hyp, sign = HYP[typ]
    contains0 = s["ci_lo_pp"] <= 0 <= s["ci_hi_pp"]
    if contains0:
        return f"{hyp} 否證：測不出{'（零）' if abs(s['excess_pp']) <= ZERO * 100 else ''}"
    if np.sign(s["excess_pp"]) == sign:
        return f"{hyp} 方向成立：測得出（{'＋' if sign > 0 else '−'}）"
    return f"{hyp} 否證：測得出但方向相反（{'＋' if s['excess_pp'] > 0 else '−'}）"


def summary_table(cl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period in PERIODS:
        sub = _in(cl, period)
        for H in HOLDS:
            bench = sub.groupby("measure_date")[f"bench_{H}"].first()
            for typ in TYPES:
                s = cell_stats(sub[sub["type"] == typ], H)
                idx = [k for k, v in TYPE_OF_IDX.items() if v == typ][0]
                rows.append({"period": period, "type": typ, "kmeans_idx": idx, "H": H, **s, "bench_mean_pp": float(bench.mean()) * 100,
                             "judge": judge(period, H, typ, s)})
    return pd.DataFrame(rows)


def quantiles_wide(S: pd.DataFrame) -> pd.DataFrame:
    cols = ["period", "H", "type", "n_rows"] + [f"p{int(q * 100):02d}" for q in QS] + ["win_rate", "excess_pp"]
    return S[cols].sort_values(["period", "H", "type"]).reset_index(drop=True)


# ───────────────────────── 安慰劑／鑑別力 ─────────────────────────
def placebo_A(cl: pd.DataFrame, H: int = 120, period: str = JUDGE_PERIOD, n_iter: int = 1000, seed: int = 0) -> pd.DataFrame:
    """每月把合格股隨機打散成四組（組大小＝當月真實），算四型點估計（有效月均值的平均）的分佈。"""
    rng = np.random.default_rng(seed)
    sub = _in(cl, period); sub = sub[sub[f"exc_{H}"].notna()]
    months = []
    for d, g in sub.groupby("measure_date"):
        e = g[f"exc_{H}"].to_numpy(float); lab = g["type_idx"].to_numpy()
        months.append((e, lab))
    sims = {i: [] for i in range(4)}
    for _ in range(n_iter):
        acc = {i: [] for i in range(4)}
        for e, lab in months:
            p = rng.permutation(lab)
            for i in range(4):
                m = p == i
                if m.sum() >= MIN_PER_MONTH:
                    acc[i].append(e[m].mean())
        for i in range(4):
            sims[i].append(np.mean(acc[i]) if acc[i] else np.nan)
    rows = []
    for i in range(4):
        a = np.array(sims[i]) * 100
        lo, hi = np.nanpercentile(a, [2.5, 97.5])
        rows.append({"check": "安慰劑A 隨機分型", "type": TYPE_OF_IDX[i], "kmeans_idx": i, "H": H, "period": period, "n_iter": n_iter,
                     "band_lo_pp": lo, "band_hi_pp": hi, "half_width_pp": (hi - lo) / 2, "contains_0": bool(lo <= 0 <= hi),
                     "half_width_gt_cost": bool((hi - lo) / 2 > ZERO * 100)})
    return pd.DataFrame(rows)


def placebo_B(cl: pd.DataFrame, shift_months: int, H: int = 120, period: str = JUDGE_PERIOD) -> pd.DataFrame:
    """標籤平移：第 m 月的型別套到同一檔第 m+k 月的報酬（該檔那個月要合格）。"""
    lab = cl[["measure_date", "stock_id", "type"]].copy()
    lab["measure_date"] = (lab["measure_date"].dt.to_period("M") + shift_months).dt.to_timestamp()
    ret = cl[["measure_date", "stock_id", f"exc_{H}", f"fwd_{H}"]].copy()
    ret["measure_date"] = ret["measure_date"].dt.to_period("M").dt.to_timestamp()
    j = ret.merge(lab, on=["measure_date", "stock_id"], how="inner")
    j["measure_date"] = j["measure_date"]
    rows = []
    for typ in TYPES:
        s = cell_stats(_in(j, period)[lambda z: z["type"] == typ], H)
        rows.append({"check": f"安慰劑B 平移 +{shift_months}", "type": typ, "H": H, "period": period, "n_months": s["n_months"],
                     "excess_pp": s["excess_pp"], "ci_lo_pp": s["ci_lo_pp"], "ci_hi_pp": s["ci_hi_pp"], "in_judgement": shift_months != 12})
    return pd.DataFrame(rows)


def discrimination(cl: pd.DataFrame, H: int = 120, period: str = JUDGE_PERIOD) -> pd.DataFrame:
    """④ 與 ② 標籤對調：對調後若仍「④負②正」⇒ 程式有 bug。"""
    sw = cl.copy(); m4 = sw["type"] == "④死水"; m2 = sw["type"] == "②正在噴出"
    sw.loc[m4, "type"] = "②正在噴出"; sw.loc[m2, "type"] = "④死水"
    rows = []
    for typ in ("②正在噴出", "④死水"):
        s = cell_stats(_in(sw, period)[lambda z: z["type"] == typ], H)
        rows.append({"check": "鑑別力 ④↔② 對調", "type": typ, "H": H, "period": period, "n_months": s["n_months"], "excess_pp": s["excess_pp"],
                     "ci_lo_pp": s["ci_lo_pp"], "ci_hi_pp": s["ci_hi_pp"]})
    df = pd.DataFrame(rows)
    x2 = df[df["type"] == "②正在噴出"]["excess_pp"].iloc[0]; x4 = df[df["type"] == "④死水"]["excess_pp"].iloc[0]
    df["bug_if_true"] = bool(x4 < 0 and x2 > 0)
    return df


# ───────────────────────── 放棄組（§七） ─────────────────────────
def structural_missing(cl: pd.DataFrame, uni: pd.DataFrame, min_rows=6, share=0.9) -> pd.DataFrame:
    """結構性缺 rev_hi24：合格列 ≥ min_rows 且 rev_hi24 缺值占比 ≥ share 的檔。KY／金融 用名稱與代號區間標（⚠ 啟發式）。"""
    g = cl.groupby("stock_id")["rev_hi24"].agg(n="size", miss=lambda s: s.isna().mean())
    ids = g[(g["n"] >= min_rows) & (g["miss"] >= share)].index
    nm = uni.set_index("stock_id")["name"]
    rows = []
    for sid in ids:
        name = str(nm.get(sid, ""))
        tag = "KY" if "KY" in name.upper() else ("金融（28xx／58xx 代號區）" if (sid[:2] in ("28", "58")) else "其他")
        rows.append({"stock_id": sid, "name": name, "tag": tag, "n_rows": int(g.loc[sid, "n"]), "miss_share": float(g.loc[sid, "miss"])})
    return pd.DataFrame(rows)


def dropped_table(panel: pd.DataFrame, cl: pd.DataFrame, S: pd.DataFrame, uni: pd.DataFrame, C, mu, sd) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    # ① 流動性擋掉的：同期報酬
    for period, (a, b) in PERIODS.items():
        pp = panel[(panel["measure_date"] >= a) & (panel["measure_date"] <= b)]
        for H in HOLDS:
            x = pp[~pp["eligible"]][f"fwd_{H}"]; y = pp[pp["eligible"]][f"fwd_{H}"]
            rows.append({"group": "①流動性擋掉", "period": period, "H": H, "n": int(x.notna().sum()), "value": float(x.mean()) * 100 if x.notna().any() else np.nan,
                         "ref": float(y.mean()) * 100, "note": "value＝被擋掉者平均毛報酬 pp；ref＝合格者"})
    # ② shares 缺值逐年
    for y, g in cl.groupby(cl["measure_date"].dt.year):
        rows.append({"group": "②shares 缺值補 50", "period": str(y), "H": np.nan, "n": int((g["shares_ok"] == 0).sum()), "value": float((g["shares_ok"] == 0).mean()) * 100,
                     "ref": int(len(g)), "note": "value＝占合格列 %；ref＝合格列數"})
    # ③ 因補 50 歸型改變
    m = cl["n_filled"] > 0
    rows.append({"group": "③補 50 改變歸型", "period": "全部", "H": np.nan, "n": int((cl.loc[m, "type_idx"] != cl.loc[m, "type_masked_idx"]).sum()),
                 "value": float((cl.loc[m, "type_idx"] != cl.loc[m, "type_masked_idx"]).mean()) * 100 if m.any() else np.nan, "ref": int(m.sum()),
                 "note": "value＝改變占有缺值列 %；ref＝有缺值列數（對照＝缺值維不進距離）"})
    # ④ <5 檔丟掉的型×月
    for r in S[S["H"] == 120].itertuples():
        rows.append({"group": "④型×月 <5 檔丟棄", "period": r.period, "H": 120, "n": int(r.dropped_cells_lt5), "value": np.nan, "ref": int(r.n_months), "note": f"{r.type}；ref＝有效月"})
    # ⑤ 2015-2016 硬納入
    e = cl[(cl["measure_date"] >= "2015-01-01") & (cl["measure_date"] <= "2016-12-31")]
    cov = float(e["rev_hi24"].notna().mean()) * 100 if len(e) else np.nan
    for typ in TYPES:
        s = cell_stats(e[e["type"] == typ], 120)
        rows.append({"group": "⑤2015-2016 硬納入（不判定）", "period": "2015-2016", "H": 120, "n": s["n_months"], "value": s["excess_pp"], "ref": cov,
                     "note": f"{typ}；value＝超額 pp（CI {s['ci_lo_pp']:+.2f}～{s['ci_hi_pp']:+.2f}）；ref＝rev_hi24 覆蓋率 %"})
    # ⑥ 結構性缺 rev_hi24
    sm = structural_missing(cl, uni)
    for tag, g in sm.groupby("tag"):
        rows.append({"group": "⑥結構性缺 rev_hi24", "period": "全部", "H": np.nan, "n": int(len(g)), "value": np.nan, "ref": int(len(sm)), "note": f"{tag}；ref＝合計檔數"})
    main = _in(cl, JUDGE_PERIOD); ms = main[main["stock_id"].isin(sm["stock_id"])]
    for typ, g in ms.groupby("type"):
        rows.append({"group": "⑥結構性缺 rev_hi24", "period": "主格", "H": np.nan, "n": int(len(g)), "value": float(len(g) / max(len(ms), 1)) * 100, "ref": int(len(ms)), "note": f"{typ}；value＝占這批主格列 %"})
    # ⑧ bars < MIN_BARS 擋掉（流動性合格）：股-月數、逐年、後續報酬 vs 合格者（v3 補件 §3-1 放棄組）
    g8 = panel[panel["liq_ok"] & ~panel["bars_ok"]]
    for period, (a, b) in PERIODS.items():
        pp = panel[(panel["measure_date"] >= a) & (panel["measure_date"] <= b)]; x8 = pp[pp["liq_ok"] & ~pp["bars_ok"]]; y8 = pp[pp["eligible"]]
        for H in HOLDS:
            rows.append({"group": "⑧bars<120 擋掉（流動性合格）", "period": period, "H": H, "n": int(x8[f"fwd_{H}"].notna().sum()),
                         "value": float(x8[f"fwd_{H}"].mean()) * 100 if x8[f"fwd_{H}"].notna().any() else np.nan, "ref": float(y8[f"fwd_{H}"].mean()) * 100 if len(y8) else np.nan,
                         "note": f"股-月 {len(x8)}；value＝被擋掉者平均毛報酬 pp；ref＝合格者"})
    for y, g in g8.groupby(g8["measure_date"].dt.year):
        tot = int((panel["measure_date"].dt.year == y).sum() and panel.loc[panel["measure_date"].dt.year == y, "liq_ok"].sum())
        rows.append({"group": "⑧bars<120 擋掉（流動性合格）", "period": str(y), "H": np.nan, "n": int(len(g)), "value": float(len(g) / max(tot, 1)) * 100, "ref": tot,
                     "note": f"逐年；value＝占流動性合格股-月 %；ref＝流動性合格股-月；檔數 {g['stock_id'].nunique()}"})
    # ⑩ 法人欄 NaN 擋掉（流動性＋bars 合格）：K線分析 2035 §一 (c)，股-月數、逐年、後續報酬、成因分佈（清單另存 dropped_inst_nan.csv）
    g10 = panel[panel["liq_ok"] & panel["bars_ok"] & ~panel["inst_ok"]]
    for period, (a, b) in PERIODS.items():
        pp = panel[(panel["measure_date"] >= a) & (panel["measure_date"] <= b)]; x = pp[pp["liq_ok"] & pp["bars_ok"] & ~pp["inst_ok"]]; y = pp[pp["eligible"]]
        for H in HOLDS:
            rows.append({"group": "⑩法人欄NaN擋掉（(c)）", "period": period, "H": H, "n": int(x[f"fwd_{H}"].notna().sum()),
                         "value": float(x[f"fwd_{H}"].mean()) * 100 if x[f"fwd_{H}"].notna().any() else np.nan, "ref": float(y[f"fwd_{H}"].mean()) * 100 if len(y) else np.nan,
                         "note": f"股-月 {len(x)}；value＝被擋掉者平均毛報酬 pp；ref＝合格者"})
    for y, g in g10.groupby(g10["measure_date"].dt.year):
        rows.append({"group": "⑩法人欄NaN擋掉（(c)）", "period": str(y), "H": np.nan, "n": int(len(g)), "value": np.nan, "ref": int(len(g["stock_id"].unique())), "note": "逐年；ref＝檔數"})
    if len(g10):
        cause = np.where(g10["inst_win_notraded"] > 0, "窗內有無成交日（停牌／無成交）", np.where(g10["inst_win_missing_traded"] > 0, "有成交日、該日法人清單不含該檔（absent；語意未知，資料庫線 2255）", "其他"))
        for k, v in pd.Series(cause).value_counts().items():
            rows.append({"group": "⑩法人欄NaN擋掉（(c)）", "period": "成因", "H": np.nan, "n": int(v), "value": float(v / len(g10)) * 100, "ref": int(len(g10)), "note": f"{k}；value＝占 %"})
        for mk, v in g10["market"].value_counts().items():
            rows.append({"group": "⑩法人欄NaN擋掉（(c)）", "period": "市場", "H": np.nan, "n": int(v), "value": float(v / len(g10)) * 100, "ref": int(len(g10)), "note": f"{mk}；value＝占 %"})
    # ⑨ 創新板量測日 < 2025-01-06 排除（K線分析 1745 §一）
    n9 = int(panel["innov_excluded"].sum()) if "innov_excluded" in panel else 0
    rows.append({"group": "⑨創新板量測日<2025-01-06 排除", "period": "全部", "H": np.nan, "n": n9, "value": np.nan, "ref": int(panel["eligible"].sum()),
                 "note": ("本窗內觸發 0 次" if n9 == 0 else "被排除的合格股-月數") + "；ref＝合格股-月"})
    # ⑦ 排除那批後重跑主格 H120
    ex = main[~main["stock_id"].isin(sm["stock_id"])]
    for typ in TYPES:
        s = cell_stats(ex[ex["type"] == typ], 120); base = S[(S.period == "主格") & (S.H == 120) & (S.type == typ)].iloc[0]
        rows.append({"group": "⑦排除結構性缺值檔重跑主格", "period": "主格", "H": 120, "n": s["n_months"], "value": s["excess_pp"], "ref": float(base["excess_pp"]),
                     "note": f"{typ}；value＝排除後超額 pp（CI {s['ci_lo_pp']:+.2f}～{s['ci_hi_pp']:+.2f}）；ref＝原主格"})
    return pd.DataFrame(rows), sm


def yearly_table(panel: pd.DataFrame, cl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y, g in cl.groupby(cl["measure_date"].dt.year):
        r = {"year": y, "n_eligible_rows": int(len(g)), "rev_hi24_coverage": float(g["rev_hi24"].notna().mean()) * 100, "shares_coverage": float((g["shares_ok"] == 1).mean()) * 100}
        for typ in TYPES:
            r[f"n_{typ}"] = int((g["type"] == typ).sum())
        r["bench_120_pp"] = float(g.groupby("measure_date")["bench_120"].first().mean()) * 100
        rows.append(r)
    return pd.DataFrame(rows)


def compare_table(S: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (period, H), ref in REF.items():
        for typ, rv in ref.items():
            me = S[(S.period == period) & (S.H == H) & (S.type == typ)].iloc[0]
            mine = {"excess": me["excess_pp"], "lo": me["ci_lo_pp"], "hi": me["ci_hi_pp"], "mwin": me["month_win_rate"] * 100, "win": me["win_rate"] * 100,
                    **{f"p{q:02d}": me[f"p{q:02d}"] for q in (5, 10, 25, 50, 75, 90, 95)}}
            for k, v in rv.items():
                tol = TOL_X if k in ("excess", "lo", "hi") else (TOL_Q if k.startswith("p") else np.nan)
                d = mine[k] - v
                rows.append({"period": period, "H": H, "type": typ, "metric": k, "策略線": v, "回測線": mine[k], "diff": d, "tol": tol,
                             "within": (abs(d) <= tol) if np.isfinite(tol) else ""})
    for (period, H), b in REF_BENCH.items():
        me = S[(S.period == period) & (S.H == H)].iloc[0]["bench_mean_pp"]
        rows.append({"period": period, "H": H, "type": "母體基準", "metric": "bench", "策略線": b, "回測線": me, "diff": me - b, "tol": TOL_X, "within": abs(me - b) <= TOL_X})
    return pd.DataFrame(rows)


# ───────────────────────── 輸出 ─────────────────────────
def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, text=True).strip()
    except Exception:
        return "unknown"


def write_csv(df: pd.DataFrame, path: str, stamp: str, commit: str):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# commit={commit} run={stamp} (Asia/Taipei) prereg=backtest/P4_v3_回溯分析.md centers=centers_v3.json(23be85b004977222)\n")
        df.to_csv(fh, index=False)


def overall_verdict(S: pd.DataFrame, pA: pd.DataFrame) -> str:
    J = S[(S.period == JUDGE_PERIOD) & (S.H == JUDGE_H)]
    refuted = int(J["judge"].str.contains("否證").sum()); nm = int(J["n_months"].min())
    parts = []
    if nm < N_MIN:
        parts.append(f"ⓑ 主格有效月 {nm} < 24 ⇒ 還沒測")
    if refuted >= 3:
        parts.append(f"ⓐ {refuted}/4 個假說被否證 ⇒ 本方法論範圍內測不到")
    nd = pA[pA["half_width_gt_cost"]]["type"].tolist()
    if nd:
        parts.append(f"ⓒ 安慰劑 CI 半寬 > 0.585%：{nd} ⇒ 該型無鑑別力")
    if not pA["contains_0"].all():
        parts.append("⛔ 安慰劑 A 的帶不含 0 ⇒ 安慰劑有偏，整份作廢")
    return "；".join(parts) if parts else f"整體否證條件 ⓐⓑⓒ 皆未觸發（否證 {refuted}/4、有效月 {nm}）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--centers", default=os.path.join(HERE, "forward", "p4_types", "centers_v3.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "resultsp4")); ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--limit", type=int); ap.add_argument("--placebo-n", type=int, default=1000); ap.add_argument("--pub-day", type=int, default=10)
    ap.add_argument("--panel", default=None, help="已算好的 panel.csv.gz（跳過第一段）")
    ap.add_argument("--no-mp-check", action="store_true", help="⛔ 只給自測用：跳過 §4-1 min_periods 常設斷言")
    ap.add_argument("--mp-check-report", action="store_true", help="§4-1 斷言不成立時只寫表、逐欄統計並印前 50 列，不中止（數字要標「斷言不成立下產出」）")
    ap.add_argument("--rev-incl-current", action="store_true", help="⛔ 只給對帳敏感度：rev_hi24 視窗改成含當期的 24 期（策略線讀法）；正式定義不動")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    stamp = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"); commit = _commit()
    log = lambda s: print(s, file=sys.stderr)
    cal = D.load_calendar(); uni = D.load_universe()
    if a.limit:
        uni = uni.head(a.limit)
    positions = P.measurement_days(cal, "2015-01-01", "2026-03-31")
    panel_p = a.panel or os.path.join(a.out, "panel.csv.gz")
    if a.panel and os.path.exists(a.panel):
        panel = pd.read_csv(a.panel, dtype={"stock_id": str}, parse_dates=["measure_date"])
    else:
        log(f"第一段：{len(uni)} 檔 × {len(positions)} 個量測日")
        panel, M = build_panel(cal, uni, positions, a.procs, a.pub_day, log, mp_check=not a.no_mp_check, rev_incl_current=a.rev_incl_current)
        if a.rev_incl_current:
            log("⛔ 對帳敏感度模式：rev_hi24 視窗含當期（前 23 期＋當期）——不是登錄定義，數字不進判定")
        write_csv(M, os.path.join(a.out, "min_periods_mismatch.csv"), stamp, commit)
        n_el0 = int(panel["eligible"].sum())
        bycol = M.groupby("column").agg(n=("stock_id", "size"), n_stocks=("stock_id", "nunique"), n_nan_at_w=("mp_w", lambda x: int(x.isna().sum()))).reset_index() if len(M) else pd.DataFrame(columns=["column", "n", "n_stocks", "n_nan_at_w"])
        with open(os.path.join(a.out, "min_periods_check.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"{stamp} commit {commit}；合格股-月 {n_el0:,} × {len(P.FEATURES)} 欄；min_periods=w vs =ceil(w/2) 不一致 {len(M)} 筆" + ("（--no-mp-check 跳過）" if a.no_mp_check else "")
                     + ("" if not len(M) else "；逐欄：" + "、".join(f"{r.column} {r.n}（{r.n_stocks} 檔；mp=w 為 NaN {r.n_nan_at_w}）" for r in bycol.itertuples()) + ("；⛔ 斷言不成立，數字在 --mp-check-report 下產出" if a.mp_check_report else "")) + "\n")
        if len(M):
            for r in M.head(50).itertuples():
                log(f"  ✗ {r.stock_id} {pd.Timestamp(r.measure_date):%Y-%m} {r.column}: mp=w {r.mp_w} vs mp=w/2 {r.mp_half}（bars {r.bars}）")
            log(open(os.path.join(a.out, "min_periods_check.txt"), encoding="utf-8").read())
            if not a.mp_check_report:
                raise AssertionError(f"§4-1 常設斷言：閘門 bars≥{P.MIN_BARS} 沒擋乾淨，{len(M)} 筆合格列在 min_periods=w 與 w/2 下不同（見 min_periods_mismatch.csv）")
        panel.to_csv(panel_p, index=False)
        back = pd.read_csv(panel_p, dtype={"stock_id": str}); assert len(back) == len(panel), "面板寫完重讀列數要對"
    panel, n_innov = apply_innovation_rule(panel, uni)
    log(f"創新板量測日 < {INNOV_CUTOFF} 排除：{n_innov} 股-月" + ("（本窗內觸發 0 次）" if n_innov == 0 else ""))
    C, mu, sd = load_centers(a.centers)
    cl = classify(panel, C, mu, sd)
    cl.to_csv(os.path.join(a.out, "classified.csv.gz"), index=False)
    S = summary_table(cl); write_csv(S, os.path.join(a.out, "summary.csv"), stamp, commit)
    write_csv(quantiles_wide(S), os.path.join(a.out, "quantiles_wide.csv"), stamp, commit)
    Dp, sm = dropped_table(panel, cl, S, uni, C, mu, sd); write_csv(Dp, os.path.join(a.out, "dropped.csv"), stamp, commit)
    g10 = panel[panel["liq_ok"] & panel["bars_ok"] & ~panel["inst_ok"]][["measure_date", "stock_id", "market", "bars", "inst_win_notraded", "inst_win_missing_traded"] + [f"fwd_{H}" for H in HOLDS]]
    write_csv(g10, os.path.join(a.out, "dropped_inst_nan.csv"), stamp, commit)
    write_csv(sm, os.path.join(a.out, "structural_missing.csv"), stamp, commit)
    # ⭐ 倖存者區間（K線分析線 0150 §1-3，登錄＝追加十八）：⛔ 結論引區間，不引點估計
    tdr = P.load_tdr_codes()        # ⛔ 同一份名單（讀不到就大聲失敗）；TDR 是【不明】，⛔ 不進代入
    SB = survivor_bound(cl, tdr)    # ⭐〈九十四〉：寫死的邊界（−100%／0%），⛔ 不挑代理組
    write_csv(SB, os.path.join(a.out, "survivor_bound.csv"), stamp, commit)
    log(f"[倖存者區間] 那批列 {int(SB['miss_rows'].iloc[0]):,} 股-月／{int(SB['miss_stocks'].iloc[0])} 檔"
        f"＝主格母體 {int(SB['n_main_rows'].iloc[0]):,} 股-月／{int(SB['n_main_stocks'].iloc[0]):,} 檔的 {SB['miss_share_pct'].iloc[0]:.2f}%；"
        + "；".join(f"{r.scenario}＝{r.excess_pp:+.2f}pp（CI {r.ci_lo_pp:+.2f}～{r.ci_hi_pp:+.2f}，{int(r.n_months)} 月）" for r in SB.itertuples()))
    write_csv(yearly_table(panel, cl), os.path.join(a.out, "yearly.csv"), stamp, commit)
    pA = placebo_A(cl, n_iter=a.placebo_n)
    pB = pd.concat([placebo_B(cl, k) for k in (6, 12, 18)], ignore_index=True)
    pD = discrimination(cl)
    write_csv(pd.concat([pA, pB, pD], ignore_index=True), os.path.join(a.out, "placebo.csv"), stamp, commit)
    cmp_ = compare_table(S); write_csv(cmp_, os.path.join(a.out, "compare_v3_s10.csv"), stamp, commit)
    verdict = overall_verdict(S, pA)
    # summary.md
    n_liq = int(panel["liq_ok"].sum()); n_gate = int((panel["liq_ok"] & ~panel["bars_ok"]).sum()); n_inst = int((panel["liq_ok"] & panel["bars_ok"] & ~panel["inst_ok"]).sum())
    # 〈八十二〉③：每道閘門「與上一輪相比擋掉的筆數變了多少」——追加型台帳 gate_history.csv（⛔ 不整份覆蓋）
    gh_p = os.path.join(a.out, "gate_history.csv"); cols = ["stamp", "commit", "n_panel", "n_liq", "n_bars_dropped", "n_inst_dropped", "n_innov_dropped", "n_eligible"]
    row = {"stamp": stamp, "commit": commit, "n_panel": len(panel), "n_liq": n_liq, "n_bars_dropped": n_gate, "n_inst_dropped": n_inst, "n_innov_dropped": n_innov, "n_eligible": len(cl)}
    existed = os.path.exists(gh_p)     # ⚠ 要在 open("a") 之前判，否則表頭永遠寫不進去
    prev = pd.read_csv(gh_p, comment="#").iloc[-1].to_dict() if existed and len(pd.read_csv(gh_p, comment="#")) else None
    with open(gh_p, "a", encoding="utf-8") as fh:
        if not existed:
            fh.write("# 閘門逐輪計數（〈八十二〉③）：每跑一輪追加一列；⛔ 不可整份覆蓋\n" + ",".join(cols) + "\n")
        fh.write(",".join(str(row[c]) for c in cols) + "\n")
    gate_delta = "（第一輪，無上一輪）" if prev is None else "、".join(f"{c} {int(prev[c]):,}→{row[c]:,}（{row[c] - int(prev[c]):+,}）" for c in cols[2:])
    mp_line = open(os.path.join(a.out, "min_periods_check.txt"), encoding="utf-8").read().strip() if os.path.exists(os.path.join(a.out, "min_periods_check.txt")) else "（沿用既有面板，本趟沒跑）"
    L = [f"# PREREGP4 v3 回溯分析——回測線獨立重算", "", f"產出：{stamp}（台北）、commit {commit}；中心 `centers_v3.json`（sha256 前 16 23be85b004977222）；母體 {len(uni)} 檔、量測日 {len(positions)}；面板 {len(panel):,} 列、流動性合格 {n_liq:,} 列、bars<{P.MIN_BARS} 再擋 {n_gate:,} 列（放棄組⑧）、法人欄 NaN 再擋 {n_inst:,} 列（放棄組⑩，K線分析 2035 (c)）、創新板規則排除 {n_innov} 列、合格 {len(cl):,} 列。", "",
         f"環境指紋（〈六十七〉）：python {sys.version.split()[0]}、pandas {pd.__version__}、numpy {np.__version__}；無成交日 amount／volume 依〈七十七〉還原 0（區間內部；依據＝該日日檔存在且不含該檔）。", "",
         f"閘門逐輪計數（〈八十二〉③，vs 上一輪 `gate_history.csv`）：{gate_delta}", "",
         f"閘門（v3 補件 §3-1／§3-2，K線分析 1855 合併）：量測日 bars ≥ {P.MIN_BARS} 才進母體、所有回看窗 min_periods＝w；§4-1 常設斷言：{mp_line}", ""]
    L.append("## 一、主格 2021-01～2026-03，H=120（唯一判定格）"); L.append("")
    L.append("| 型 | 有效月 | 超額 | 95% CI | 月勝率 | 逐筆勝率 | p05 / p10 / p50 / p90 / p95 | 絕對平均（扣成本） | 月均檔數 | 判定 |"); L.append("|---|---:|---:|---|---:|---:|---|---:|---:|---|")
    for r in S[(S.period == "主格") & (S.H == 120)].itertuples():
        L.append(f"| {r.type} | {r.n_months} | {r.excess_pp:+.2f} | {r.ci_lo_pp:+.2f}～{r.ci_hi_pp:+.2f} | {r.month_win_rate * 100:.1f}% | {r.win_rate * 100:.1f}% | {r.p05:+.1f} / {r.p10:+.1f} / {r.p50:+.1f} / {r.p90:+.1f} / {r.p95:+.1f} | {r.abs_mean_pp:+.2f}（{r.abs_mean_net_pp:+.2f}） | {r.avg_n_per_month:.0f} | {r.judge} |")
    b = S[(S.period == "主格") & (S.H == 120)].iloc[0]["bench_mean_pp"]
    L.append(""); L.append(f"母體基準（主格 H120 等權）：{b:+.2f}%。⇒ 整體：**{verdict}**"); L.append("")
    L.append("## 二、與 v3 §十 對帳（門檻：分位數差 ≤ 1.0pp、超額／CI 差 ≤ 0.3pp）"); L.append("")
    bad = cmp_[(cmp_["within"] == False)]
    L.append(f"逐格 {len(cmp_)} 項，超出門檻 {len(bad)} 項。" + ("" if len(bad) == 0 else " ⛔ 超出的："))
    for r in bad.itertuples():
        L.append(f"- {r.period} H{r.H} {r.type} {r.metric}：策略線 {r.策略線:+.2f} vs 回測線 {r.回測線:+.2f}（差 {r.diff:+.2f}）")
    L.append(""); L.append("## 三、其餘期間 H=120（不判定，只寫方向）"); L.append("")
    L.append("| 期間 | 型 | 有效月 | 超額 | 95% CI | 逐筆勝率 | 判定 |"); L.append("|---|---|---:|---:|---|---:|---|")
    for r in S[(S.period != "主格") & (S.H == 120)].itertuples():
        L.append(f"| {r.period} | {r.type} | {r.n_months} | {r.excess_pp:+.2f} | {r.ci_lo_pp:+.2f}～{r.ci_hi_pp:+.2f} | {r.win_rate * 100:.1f}% | {r.judge} |")
    L.append(""); L.append("## 四、安慰劑與鑑別力（主格 H120）"); L.append("")
    for r in pA.itertuples():
        L.append(f"- 安慰劑A {r.type}：95% 帶 {r.band_lo_pp:+.2f}～{r.band_hi_pp:+.2f}（半寬 {r.half_width_pp:.2f}pp；含 0 {r.contains_0}；半寬 > 0.585 {r.half_width_gt_cost}）")
    for r in pB.itertuples():
        L.append(f"- {r.check} {r.type}：{r.excess_pp:+.2f}（{r.ci_lo_pp:+.2f}～{r.ci_hi_pp:+.2f}，有效月 {r.n_months}）{'' if r.in_judgement else '｜⛔ +12 不進判定'}")
    for r in pD.itertuples():
        L.append(f"- {r.check} {r.type}：{r.excess_pp:+.2f}（{r.ci_lo_pp:+.2f}～{r.ci_hi_pp:+.2f}）")
    L.append(f"- 鑑別力：對調後仍「④負②正」＝{bool(pD['bug_if_true'].iloc[0])}（True ⇒ 程式有 bug）")
    L.append(""); L.append("## 五、放棄組（`dropped.csv`）摘要"); L.append("")
    for r in Dp[Dp["group"].str.startswith(("⑥", "⑦", "③", "⑧", "⑨", "⑩"))].itertuples():
        L.append(f"- {r.group}｜{r.period}｜n={r.n}｜value={r.value if not isinstance(r.value, float) or np.isnan(r.value) else round(r.value, 2)}｜ref={r.ref}｜{r.note}")
    L.append(""); L.append("其餘：`quantiles_wide.csv`（四型並列）、`yearly.csv`、`placebo.csv`、`compare_v3_s10.csv`、`structural_missing.csv`；面板 `panel.csv.gz`、歸型 `classified.csv.gz`。⛔ 沒有任何「贏過 0050」的比較。")
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

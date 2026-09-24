# -*- coding: utf-8 -*-
"""裁定線 20260924-1235 §四 步驟②：重算【四型主格 H=120】與【P8 2-A H120】的 CI。

⛔⛔ 只重算 CI ⇒ ⛔ 不改點估計、⛔ 不改判準、⛔ 不宣告任何一件失效（1235 §四：步驟③ 由裁定線裁）
並列三樣（1235 §四 逐字）：
   ① 月分群 SE（＝原交件的口徑，⭐ 先逐位重現當錨點）
   ② H 長區段分群 SE（以 H 個交易日為長度、從判定窗第一個交易日切的不重疊區段）
   ③ 逐月序列的 lag1～lag5 自相關

⭐ 分群 SE 的寫法（⛔ 為了讓點估計一個字都不動）：
   點估計 x̄ ＝ 逐月值的平均（與原件相同）
   SE ＝ √( G/(G−1) × Σ_g (Σ_{m∈g}(x_m − x̄))² ) ／ n        （CR1，群 ＝ 區段）
   ⭐ 當每個月自成一群時，這個式子【恰好等於】sd(ddof=1)/√n ＝ 原件的月分群 SE
   ⇒ 所以錨點閘門是：本式以「每月一群」算出來的 CI 必須與原件逐位相同。
⚠ 95% 一律用 1.96（與原件同一慣例）⇒ 而 G 只有十幾群時常態近似偏窄 ⇒ 另報 t(G−1) 版當描述。
"""
from __future__ import annotations
import os, sys, math
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import researchp4 as P4
from backtest import researchp8 as P8
from backtest import researchp1 as P1
from backtest import p4_features as P4F
from backtest.p4_type_recheck import bare          # ⭐ 去圈號的唯一實作（classified 是 (甲) 圈號）

try:
    from scipy.stats import t as tdist
    def tcrit(df): return float(tdist.ppf(0.975, df))
except Exception:                                     # ⛔ 沒 scipy 就不報 t 版，⛔ 不自己湊
    def tcrit(df): return float("nan")

OUT = "backtest/results_step2"; os.makedirs(OUT, exist_ok=True)
cal = D.load_calendar(); pos = {d: i for i, d in enumerate(cal)}


def cluster_ci(x: np.ndarray, g: np.ndarray) -> dict:
    x = np.asarray(x, float); n = len(x); xbar = float(x.mean())
    df = pd.DataFrame({"r": x - xbar, "g": g})
    s = df.groupby("g")["r"].sum().to_numpy(); G = len(s)
    se = math.sqrt(G / (G - 1) * float((s ** 2).sum())) / n
    tc = tcrit(G - 1)
    return {"n": n, "G": G, "point_pp": xbar * 100, "se_pp": se * 100,
            "lo_pp": (xbar - 1.96 * se) * 100, "hi_pp": (xbar + 1.96 * se) * 100,
            "lo_t_pp": (xbar - tc * se) * 100, "hi_t_pp": (xbar + tc * se) * 100,
            "ci_has_0": bool((xbar - 1.96 * se) * (xbar + 1.96 * se) <= 0)}


def acf(x: np.ndarray, k: int) -> float:
    s = pd.Series(np.asarray(x, float)); return float(s.autocorr(lag=k))


def seg_ids(dates: pd.Series, start: str, H: int) -> np.ndarray:
    p0 = int(cal.searchsorted(pd.Timestamp(start)))
    return ((dates.map(pos).astype(int).to_numpy() - p0) // H)


rows = []
# ═════════════ A. 四型主格 H=120 ═════════════
H = P4.JUDGE_H
cl = pd.read_csv("backtest/resultsp4/classified.csv.gz", parse_dates=["measure_date"])
cl["type_bare"] = cl["type"].map(bare)
main = P4._in(cl, P4.JUDGE_PERIOD)
S = pd.read_csv("backtest/resultsp4/summary.csv", comment="#")
S = S[(S["period"] == P4.JUDGE_PERIOD) & (S["H"] == H)].copy(); S["type_bare"] = S["type"].map(bare)
start4 = P4.PERIODS[P4.JUDGE_PERIOD][0]
print("══ A. 四型 主格 {} H={}（classified.csv.gz；比對鍵＝bare 型名）══".format(P4.PERIODS[P4.JUDGE_PERIOD], H))
for t in sorted(main["type_bare"].unique()):
    sub = main[main["type_bare"] == t]
    cs = P4.cell_stats(sub, H)                       # ⭐ 原件的函式，⛔ 不重寫
    ref = S[S["type_bare"] == t].iloc[0]
    # 閘門 1：原函式重跑 ＝ 交件 summary.csv
    g1 = all(abs(cs[k] - ref[k]) < 1e-9 for k in ("excess_pp", "ci_lo_pp", "ci_hi_pp")) and cs["n_months"] == ref["n_months"]
    # 逐月序列（與 cell_stats 同一個篩法：當月 ≥ MIN_PER_MONTH 檔）
    r = sub[sub[f"exc_{H}"].notna()]
    pm = r.groupby("measure_date").agg(n=("stock_id", "size"), exc=(f"exc_{H}", "mean"))
    ok = pm[pm["n"] >= P4.MIN_PER_MONTH].sort_index()
    x = ok["exc"].to_numpy(float); dts = ok.index.to_series()
    m = cluster_ci(x, np.arange(len(x)))
    # 閘門 2：本式「每月一群」＝ 原件 CI（⭐ 錨在本線自己的改動上）
    g2 = abs(m["lo_pp"] - cs["ci_lo_pp"]) < 1e-9 and abs(m["hi_pp"] - cs["ci_hi_pp"]) < 1e-9
    assert g1, "⛔ 閘門1 不過：原函式重跑 ≠ summary.csv（{}）".format(t)
    assert g2, "⛔ 閘門2 不過：CR1 每月一群 ≠ 原件 CI（{}）".format(t)
    sgm = cluster_ci(x, seg_ids(dts, start4, H))
    ac = [acf(x, k) for k in range(1, 6)]
    rows.append(dict(件="四型主格", 格=t, H=H, 月數=m["n"], 點估計_pp=m["point_pp"],
                     月分群_lo=m["lo_pp"], 月分群_hi=m["hi_pp"], 月分群含0=m["ci_has_0"],
                     區段數G=sgm["G"], 區段_lo=sgm["lo_pp"], 區段_hi=sgm["hi_pp"], 區段含0=sgm["ci_has_0"],
                     區段_t_lo=sgm["lo_t_pp"], 區段_t_hi=sgm["hi_t_pp"],
                     寬度倍數=(sgm["hi_pp"] - sgm["lo_pp"]) / (m["hi_pp"] - m["lo_pp"]),
                     **{f"lag{k}": ac[k - 1] for k in range(1, 6)}))
    print("  {:<8} 點 {:+6.2f}pp｜月分群 [{:+6.2f},{:+6.2f}] n={}｜H區段 [{:+6.2f},{:+6.2f}] G={}（寬 {:.2f}×）｜lag1..5 {}"
          .format(t, m["point_pp"], m["lo_pp"], m["hi_pp"], m["n"], sgm["lo_pp"], sgm["hi_pp"], sgm["G"],
                  rows[-1]["寬度倍數"], " ".join("{:+.2f}".format(a) for a in ac)))
print("  ✅ 閘門1（原函式重跑＝summary.csv）與閘門2（CR1 每月一群＝原件 CI）四格全過")
print()

# ═════════════ B. P8 2-A H120（D10−D1）═════════════
print("══ B. P8 2-A D10−D1（{}～{}，⭐ 直接重用 researchp8 的函式）══".format(P8.START, P8.END))
panel = P4F.read_panel(os.path.join("backtest", "resultsp4", "panel.csv.gz"))
uni = D.load_universe().set_index("stock_id")["market"]
closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
p = panel[(panel["measure_date"] >= pd.Timestamp(P8.START)) & (panel["measure_date"] <= pd.Timestamp(P8.END))]
el = p[p["eligible"].astype(bool)].copy()
el = P8.add_forward(el, cal, closes, opens)
el["bucket"] = P8.xs_bucket(el, P8.FEATURE, P8.N_DEC)
A = pd.read_csv("backtest/resultsp8/a_single.csv")
for Hh in P8.HOLDS:
    ref = A[A["H"] == Hh].iloc[0]
    col = f"fwd{Hh}"
    g = el.dropna(subset=[col, "bucket"])
    mm = g.groupby(["measure_date", "bucket"])[col].mean().unstack()
    d = (mm[P8.N_DEC - 1] - mm[0]).dropna().sort_index()
    x = d.to_numpy(float); dts = d.index.to_series()
    orig = P8.month_ci(x)
    g1 = abs(orig["diff_pp"] - ref["d10_d1_pp"]) < 1e-9 and abs(orig["lo_pp"] - ref["lo_pp"]) < 1e-9 and orig["n_months"] == ref["n_months"]
    m = cluster_ci(x, np.arange(len(x)))
    g2 = abs(m["lo_pp"] - orig["lo_pp"]) < 1e-9 and abs(m["hi_pp"] - orig["hi_pp"]) < 1e-9
    assert g1, "⛔ P8 閘門1 不過：重跑 ≠ a_single.csv（H={}）".format(Hh)
    assert g2, "⛔ P8 閘門2 不過：CR1 每月一群 ≠ month_ci（H={}）".format(Hh)
    sgm = cluster_ci(x, seg_ids(dts, P8.START, Hh))
    ac = [acf(x, k) for k in range(1, 6)]
    rows.append(dict(件="P8 2-A", 格="D10−D1", H=Hh, 月數=m["n"], 點估計_pp=m["point_pp"],
                     月分群_lo=m["lo_pp"], 月分群_hi=m["hi_pp"], 月分群含0=m["ci_has_0"],
                     區段數G=sgm["G"], 區段_lo=sgm["lo_pp"], 區段_hi=sgm["hi_pp"], 區段含0=sgm["ci_has_0"],
                     區段_t_lo=sgm["lo_t_pp"], 區段_t_hi=sgm["hi_t_pp"],
                     寬度倍數=(sgm["hi_pp"] - sgm["lo_pp"]) / (m["hi_pp"] - m["lo_pp"]),
                     **{f"lag{k}": ac[k - 1] for k in range(1, 6)}))
    print("  H={:<3} 點 {:+6.2f}pp｜月分群 [{:+6.2f},{:+6.2f}] n={}｜H區段 [{:+6.2f},{:+6.2f}] G={}（寬 {:.2f}×）｜lag1..5 {}"
          .format(Hh, m["point_pp"], m["lo_pp"], m["hi_pp"], m["n"], sgm["lo_pp"], sgm["hi_pp"], sgm["G"],
                  rows[-1]["寬度倍數"], " ".join("{:+.2f}".format(a) for a in ac)))
print("  ✅ 閘門1（重跑＝a_single.csv）與閘門2（CR1 每月一群＝month_ci）全過")
out = pd.DataFrame(rows); out.to_csv(os.path.join(OUT, "ci_step2.csv"), index=False, encoding="utf-8")
print("\n⇒ 落檔 {}/ci_step2.csv（{} 列）".format(OUT, len(out)))

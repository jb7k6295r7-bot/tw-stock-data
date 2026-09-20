"""PREREGP7（策略線 2026-09-20 0945／1115 補件）：**比例族停損在組合層**。

    python3 -m backtest.researchp7 [--procs 8] [--reps 200] [--out backtest/resultsp7]

⭐ 引擎是 `research11.simulate_mtm`（⛔ 沒有另建）；本檔只做三件事：
  ① 依策略線 1115 §1-1 的**逐字定義**重建門檻B 的 sig（⛔ 不是它沙箱那份檔，那份從未 commit）
  ② 跑六格 ＋ 兩格敏感度，種子 `default_rng(97000 + r)`（⛔ 不沿用 90000／96000）
  ③ 必報六項寫成表

⛔ **範圍**（策略線 0945 §四末，逐字）：本件只測【比例族】兩種寫法。結構族（前低、箱底）與均線族
（跌破 50 日線）不測；波動率族（ATR 偏移）已有 PREREG19 ⇒ 不在本件。
⇒ ⭐ 所以結論**不可**寫成「停損沒用」——那只對比例族成立。

⛔ **槽位語意**（策略線 1115 §二裁定，逐字寫進結論的範圍限制）：
  「停損觸發日收盤出場，次一交易日該槽位才可再進場。⇒ 本件的停損組比『當日即可再進場』的設計
    少了機會數，⚠ 因此年化的下降幅度含有這一項，⛔ 不可全部歸因於停損本身。」
⇒ ⭐ 所以【平均槽位使用率】與【平均持有天數】都在必報裡——沒有它們就解釋不了年化為什麼掉。

⭐⭐ **追加（回測線 2026-09-20 12:xx，⛔ 寫在跑之前）：門檻B 基準線 7 個 N × 三窗**
  來源：策略線 0810 §二 逐字——「⚠ 本線只算了【全窗】⇒ ⭐ A 窗／B 窗請回測線補（PREREGP1 §4-A 要三個）」。
  ```
  格：stop=None × N ∈ (3, 5, 8, 10, 15, 20, 30)   ⇒ 7 格，⛔ 不是檢定，是【描述＋對帳】
  種子：default_rng(97000 + r)，R=200              ⇒ ⭐ 沿用本件已登錄的種子，⛔ 不另開、⛔ 不沿用策略線的 90000+r
  判準：對 0050 的三條（年化不低於 ∧ 回落較淺），⭐ 全窗／A 窗／B 窗各算一次
  ```
  ⭐ 種子不同 ⇒ 與策略線 0810 §二那張表**不會逐位元相同**；對帳看的是**中位數落在同一個量級**與**三條判準的結論一致**，
  ⛔ 不是看數字一樣。⚠ N=8／stop=None 這一格與主表六格的第一格是**同一格**（同種子）⇒ ⛔ 不重複計數。
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

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp7")
SEED0 = 97000                    # ⛔ 登錄寫死（策略線 0945 §四②）：不沿用 90000／96000
RULE = "H120"
N_MAIN = 8
# 六格（策略線 0945 §四②）：門檻B × N=8 × {none, fix 8/15/20, trail 15/20}
CELLS = [None, ("fix", 0.08), ("fix", 0.15), ("fix", 0.20), ("trail", 0.15), ("trail", 0.20)]
SENS_N = (5, 20)                 # 敏感度（分開寫）：N=5 與 N=20 各跑 none 與 fix 15%
SENS_STOPS = [None, ("fix", 0.15)]
BASE_NS = (3, 5, 8, 10, 15, 20, 30)   # 基準線（stop=None）：策略線 0810 §二 那張表的 7 個 N，⭐ 本線補 A 窗／B 窗
HOLD_BARS_N = 120                # ⭐ H120 ＝**持有 120 根**（進場那根算第 1 根）⇒ xpos ＝ D.exit_pos(entry_pos, 120) ＝ entry_pos+119
                                 # （策略線 1115 §1-1 逐字；⚠ 本庫 P4 的 fwd_120 是持有 **121** 根 ⇒ 兩者差一根，見 P4_v3 追加二十一）
HOLD_BARS = HOLD_BARS_N - 1      # ⛔ 只留給「平均持有天數」那一欄：引擎的 hold_days 是**日數差**（出場日 − 進場日）⇒ 持有根數 − 1


def stop_tag(stop) -> str:
    return "none" if stop is None else f"{stop[0]} {stop[1] * 100:.0f}%"


def build_sig_gate_b(panel: pd.DataFrame, cal: pd.DatetimeIndex, closes: dict, opens: dict, start: str = "2017-01-01",
                     signal: str = "B") -> pd.DataFrame:
    """門檻B 的 sig（策略線 1115 §1-1 逐字定義）。

    PREREGP11（2026-09-20）加 `signal`：⛔ 預設 "B" 時與原版【逐位元相同】。
      "B" 門檻B ＝ rev_hi24 ∧ ¬ma_stack ∧ ma60_up
      "C" 參考C ＝ rev_hi24 ∧ ma60_up（⭐ 就是 B 拿掉 ¬ma_stack，⛔ 沒有其他差別 ⇒ B ⊂ C）

    候選母體＝過閘門股-月（`eligible` ＝ liq_ok ∧ bars_ok ∧ inst_ok，(c) 已套）
    訊號  ＝ `rev_hi24 ∧ ¬ma_stack ∧ ma60_up`（⭐ 三條都是布林、⛔ 零擬合參數、零中心、零橫斷面百分位）
    entry_pos ＝ 量測日位置 + 1；xpos ＝ D.exit_pos(entry_pos, 120) ＝ entry_pos+119（持有 120 根）；g ＝ closes[xpos] / opens[entry] − 1
    剔除：xpos ≥ ncal／opens[entry] 非有限或 ≤ 0／closes[xpos] 非有限
    ⚠ relvol(=amt20)／vol(=vol60) 是**原始值**，⛔ 不是橫斷面百分位。
    """
    pos = {d: i for i, d in enumerate(cal)}
    ncal = len(cal)
    p = panel[panel["measure_date"] >= pd.Timestamp(start)]
    el = p[p["eligible"].astype(bool)]
    if signal not in ("B", "C"):
        raise ValueError(f"signal 只能是 'B'（門檻B）或 'C'（參考C），收到 {signal!r}")
    m = (el["rev_hi24"] == 100) & (el["ma60_up"] == 100)
    if signal == "B":
        m &= el["ma_stack"] == 0
    b = el[m].copy()
    b["entry_pos"] = b["measure_date"].map(pos).astype("Int64") + 1
    b = b[b["entry_pos"].notna()].copy()
    b["entry_pos"] = b["entry_pos"].astype(int)
    b[f"xpos_{RULE}"] = b["entry_pos"].map(lambda e: D.exit_pos(int(e), HOLD_BARS_N))
    rows = []
    for r in b.itertuples():
        sid = r.stock_id
        e, x = int(r.entry_pos), int(getattr(r, f"xpos_{RULE}"))
        if x >= ncal or sid not in closes or sid not in opens:
            continue
        o = float(opens[sid][e]) if e < len(opens[sid]) else np.nan
        c = float(closes[sid][x]) if x < len(closes[sid]) else np.nan
        if not np.isfinite(o) or o <= 0 or not np.isfinite(c):
            continue
        rows.append({"sid": sid, "entry_pos": e, f"xpos_{RULE}": x, f"g_{RULE}": c / o - 1.0,
                     "month": r.measure_date.strftime("%Y-%m"), "relvol": float(r.amt20), "vol": float(r.vol60)})
    return pd.DataFrame(rows)


_S: dict = {}


def _init(sig, closes, opens, ncal, first_all, split_pos, end_all):
    _S.update(sig=sig, closes=closes, opens=opens, ncal=ncal, first_all=first_all, split_pos=split_pos, end_all=end_all)


def _one(args):
    N, stop, seed = args
    s = R.simulate_mtm(_S["sig"], RULE, N, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                       return_equity=True, stop=stop)
    ca, ma = R13.window_stats(s["equity"], s["first"], s["end"], _S["first_all"], _S["split_pos"])
    cb, mb = R13.window_stats(s["equity"], s["first"], s["end"], _S["split_pos"], _S["end_all"])
    out = {"seed": seed, "cagr": s["cagr"], "mdd": s["mdd"], "slot": s["slot_use"], "m": s["m"],
           "ca": ca, "ma": ma, "cb": cb, "mb": mb}
    if stop is None:
        out |= {"stop_rate": 0.0, "stop_max_same_day": 0, "stop_cut_right_tail": 0, "hold_days_mean": float(HOLD_BARS), "stop_months": {}}
    else:
        out |= {"stop_rate": s["stop_rate"], "stop_max_same_day": s["stop_max_same_day"],
                "stop_cut_right_tail": s["stop_cut_right_tail"], "hold_days_mean": s["hold_days_mean"],
                "stop_months": s["stop_days"]}
    return out


def run_cells(sig, closes, opens, cal, bench, cells, ns, reps, procs, log=print) -> tuple[pd.DataFrame, dict]:
    """(N, stop) 逐格跑 reps 顆種子。回 (每格一列的表, {格: 觸發日逐月家數})。"""
    ncal = len(cal)
    split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    first_all = int(sig["entry_pos"].min()); end_all = ncal
    b_c, b_m = R13.window_stats(bench, first_all, end_all, first_all, end_all)
    b_ca, b_ma = R13.window_stats(bench, first_all, end_all, first_all, split_pos)
    b_cb, b_mb = R13.window_stats(bench, first_all, end_all, split_pos, end_all)
    log(f"[0050] 全窗 年化 {b_c * 100:+.2f}%／回落 {b_m * 100:.1f}%；A 窗 {b_ca * 100:+.2f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.2f}%／{b_mb * 100:.1f}%")
    jobs = [(N, st) for N in ns for st in cells]
    rows = []; months = {}
    pool = Pool(procs, initializer=_init, initargs=(sig, closes, opens, ncal, first_all, split_pos, end_all))
    t0 = time.time()
    try:
        for N, st in jobs:
            res = pool.map(_one, [(N, st, SEED0 + r) for r in range(reps)], chunksize=4)
            df = pd.DataFrame(res); md = df.median(numeric_only=True)
            # ⛔ 三條判準要【全窗＋A 窗＋B 窗三個都成立】才算通過（策略線 1115 §三②）
            win_all = bool(md["cagr"] >= b_c and md["mdd"] > b_m)
            win_a = bool(md["ca"] >= b_ca and md["ma"] > b_ma)
            win_b = bool(md["cb"] >= b_cb and md["mb"] > b_mb)
            agg = {}
            for r_ in res:
                for d, k in r_["stop_months"]:
                    agg[int(d)] = agg.get(int(d), 0) + k
            months[(N, stop_tag(st))] = agg
            rows.append({"N": N, "stop": stop_tag(st), "cagr": md["cagr"], "cagr_p10": df["cagr"].quantile(0.1), "cagr_p90": df["cagr"].quantile(0.9),
                         "mdd": md["mdd"], "mdd_p10": df["mdd"].quantile(0.1), "mdd_p90": df["mdd"].quantile(0.9),
                         "ca_p10": df["ca"].quantile(0.1), "ca_p90": df["ca"].quantile(0.9),      # ⭐ 逐窗離散度：沒有它不可以講「A 窗的下降不是噪音」
                         "cb_p10": df["cb"].quantile(0.1), "cb_p90": df["cb"].quantile(0.9),
                         "slot": md["slot"], "m": md["m"], "hold_days": md["hold_days_mean"],
                         "stop_rate": md["stop_rate"], "stop_max_same_day": md["stop_max_same_day"],
                         "stop_max_same_day_worst": int(df["stop_max_same_day"].max()), "cut_right_tail": md["stop_cut_right_tail"],
                         "ca": md["ca"], "ma": md["ma"], "cb": md["cb"], "mb": md["mb"],
                         "win_all": win_all, "win_a": win_a, "win_b": win_b, "win": bool(win_all and win_a and win_b)})
            log(f"  N={N} {stop_tag(st):<9} 年化 {md['cagr'] * 100:+6.2f}% 回落 {md['mdd'] * 100:6.1f}% 槽 {md['slot']:.2f} "
                f"停損率 {md['stop_rate']:.2f} 單日最多 {int(df['stop_max_same_day'].max())} 持有 {md['hold_days_mean']:.0f} 天 "
                f"⇒ {'✅ 三窗全過' if (win_all and win_a and win_b) else '⛔ 沒過'}（{time.time() - t0:.0f}s）")
    finally:
        pool.close(); pool.join()
    return pd.DataFrame(rows), months


def report(T: pd.DataFrame, months: dict, sig: pd.DataFrame, bench_line: str) -> list[str]:
    L = ["# PREREGP7：比例族停損在組合層（回測線落地）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準＝策略線 PREREGP7（0945）＋1115 補件。",
         f"訊號：門檻B `rev_hi24 ∧ ¬ma_stack ∧ ma60_up`，{len(sig):,} 筆／{sig['sid'].nunique():,} 檔／{sig['month'].nunique()} 個月"
         f"（{sig['month'].min()} ~ {sig['month'].max()}），H120 ＝ **持有 {HOLD_BARS_N} 根**（xpos ＝ entry_pos+{HOLD_BARS_N - 1}）。種子 `default_rng({SEED0} + r)`。", "",
         f"⚠ 「平均持有天數」那一欄是**日數差**（出場日 − 進場日）⇒ 排程出場 ＝ {HOLD_BARS_N - 1} 天差 ＝ 持有 {HOLD_BARS_N} 根。", "",
         "⛔ **範圍**：只測【比例族】兩種寫法。結構族（前低、箱底）、均線族（跌破 50 日線）不測；波動率族（ATR 偏移）在 PREREG19。",
         "⇒ ⭐ 結論**不可**寫成「停損沒用」——那只對比例族成立。", "",
         "⛔ **槽位語意**（策略線 1115 §二裁定）：停損觸發日收盤出場，**次一交易日**該槽位才可再進場。",
         "⇒ 本件的停損組比『當日即可再進場』的設計**少了機會數**，⚠ 因此年化的下降幅度含有這一項，⛔ 不可全部歸因於停損本身。", "",
         bench_line, "",
         "| N | 停損 | 年化 中位 | p10～p90 | 最大回落 中位 | p10～p90 | 槽位 | 筆數 | 平均持有天 | 停損出場率 | 單日觸發最多 | 砍掉的右尾 | 全窗 | A 窗 | B 窗 | 三窗全過 |",
         "|---:|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|:--:|:--:|:--:|:--:|"]
    for r in T.itertuples():
        L.append(f"| {r.N} | {r.stop} | {r.cagr * 100:+.2f}% | {r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f} | {r.mdd * 100:.1f}% | "
                 f"{r.mdd_p10 * 100:.1f}～{r.mdd_p90 * 100:.1f} | {r.slot:.2f} | {r.m:.0f} | {r.hold_days:.0f} | {r.stop_rate:.2f} | "
                 f"{int(r.stop_max_same_day_worst)} | {r.cut_right_tail:.0f} | {'✅' if r.win_all else '✗'} | {'✅' if r.win_a else '✗'} | "
                 f"{'✅' if r.win_b else '✗'} | {'✅' if r.win else '⛔'} |")
    L += ["", "⚠ 「停損出場率」是**設計上的必然**（X 越緊越高）⇒ ⛔ 不可當成「停損太緊」的證據（策略線 0945 §四③）。", ""]
    if months:
        L += ["### ⭐ 停損觸發日的時間分佈（必報；200 顆種子累計）", "",
              "⛔ 策略線 0945 §二 押【單日觸發家數最大值 ≥ N/2】⇒ 若成立，停損在本策略上是一條**市場擇時規則**，不是個股風控。", "",
              "| 格 | 累計觸發 | 單日最多（顆種子內） | 最集中的 5 天 | 最集中的 5 個月 |", "|---|---:|---:|---|---|"]
        for key, agg in months.items():
            if not agg:
                continue
            ser = pd.Series(agg)
            worst = int(T[(T["N"] == key[0]) & (T["stop"] == key[1])]["stop_max_same_day_worst"].iloc[0])
            top_d = ser.nlargest(5)
            ym = pd.Series({d: str(_CAL[d])[:7] for d in ser.index})
            top_m = ser.groupby(ym).sum().nlargest(5)
            L.append(f"| N={key[0]} {key[1]} | {int(ser.sum()):,} | **{worst}** | "
                     + "、".join(f"{str(_CAL[d])[:10]} {int(v)}" for d, v in top_d.items()) + " | "
                     + "、".join(f"{k} {int(v)}" for k, v in top_m.items()) + " |")
        L.append("")
    return L


_CAL: list = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    ap.add_argument("--part", choices=("all", "cells", "baseline"), default="all",
                    help="cells＝六格＋敏感度（P7_REPORT.md）；baseline＝門檻B 基準線 7 個 N × 三窗（BASELINE_REPORT.md）；⛔ 分開跑是為了每趟都在前景跑得完")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = print
    cal = D.load_calendar()
    _CAL.extend(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    sids = set(panel["stock_id"])
    closes, opens = P1.load_prices(sids, cal, uni)          # ⭐ 與 P1 同一份載入（closes ffill、opens 不 ffill）
    sig = build_sig_gate_b(panel, cal, closes, opens)
    log(f"[sig] 門檻B {len(sig):,} 筆／{sig['sid'].nunique():,} 檔／{sig['month'].nunique()} 月"
        f"（{sig['month'].min()} ~ {sig['month'].max()}；entry_pos {int(sig['entry_pos'].min())}~{int(sig['entry_pos'].max())}）")
    # ⛔ 策略線 1115 §1-2 的驗收數：對不上就停，⛔ 不先跑六格
    want = {"rows": 2882, "stocks": 919, "months": 109, "m_min": "2017-03", "m_max": "2026-03", "e_min": 523, "e_max": 2716}
    got = {"rows": len(sig), "stocks": sig["sid"].nunique(), "months": sig["month"].nunique(),
           "m_min": sig["month"].min(), "m_max": sig["month"].max(),
           "e_min": int(sig["entry_pos"].min()), "e_max": int(sig["entry_pos"].max())}
    if got != want:
        raise SystemExit(f"⛔ sig 驗收數對不上策略線 1115 §1-2 ⇒ 先回信、⛔ 不跑六格\n  want {want}\n  got  {got}")
    log("[sig] ✅ 七個驗收數與策略線 1115 §1-2 逐項相同")
    sig.to_csv(os.path.join(a.out, "sig_gateB.csv.gz"), index=False)
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    if a.part in ("all", "cells"):
        T, months = run_cells(sig, closes, opens, cal, bench, CELLS, (N_MAIN,), a.reps, a.procs, log)
        S, months_s = run_cells(sig, closes, opens, cal, bench, SENS_STOPS, SENS_N, a.reps, a.procs, log)
        T.to_csv(os.path.join(a.out, "cells.csv"), index=False); S.to_csv(os.path.join(a.out, "sensitivity.csv"), index=False)
        md = []
        for key, agg in {**months, **months_s}.items():
            for d, k in sorted(agg.items()):
                md.append({"N": key[0], "stop": key[1], "cal_pos": d, "date": str(cal[d].date()), "n_triggered": k})
        pd.DataFrame(md).to_csv(os.path.join(a.out, "stop_days.csv"), index=False)
    ncal = len(cal); split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    first_all = int(sig["entry_pos"].min())
    b_c, b_m = R13.window_stats(bench, first_all, ncal, first_all, ncal)
    b_ca, b_ma = R13.window_stats(bench, first_all, ncal, first_all, split_pos)
    b_cb, b_mb = R13.window_stats(bench, first_all, ncal, split_pos, ncal)
    bl = (f"**0050 買進持有**：全窗 年化 {b_c * 100:+.2f}%／最大回落 {b_m * 100:.1f}%；"
          f"A 窗 {b_ca * 100:+.2f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.2f}%／{b_mb * 100:.1f}%。")
    if a.part in ("all", "cells"):
        L = report(T, months, sig, bl) + ["## 敏感度（N=5／N=20，⛔ 分開寫不進主判定）", ""] + report(S, months_s, sig, bl)[9:]
        open(os.path.join(a.out, "P7_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
        log(f"寫入 {os.path.join(a.out, 'P7_REPORT.md')}")
    if a.part in ("all", "baseline"):
        B, _mb2 = run_cells(sig, closes, opens, cal, bench, [None], BASE_NS, a.reps, a.procs, log)
        B.to_csv(os.path.join(a.out, "baseline_gateB.csv"), index=False)
        LB = ["# 門檻B 基準線（stop=None）7 個 N × 三窗（回測線補策略線 0810 §二）", "",
              f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。",
              "⛔ **這是描述＋對帳，不是檢定**（登錄見 `researchp7` 檔頭追加）。種子 `default_rng(97000 + r)`、R=200 ⇒ "
              "⭐ 與策略線 0810 §二那張表**種子不同**，對帳看的是量級與三條判準的結論，⛔ 不是看數字一樣。", "",
              bl, "",
              "| N | 全窗 年化 | p10～p90 | 全窗 回落 | p10～p90 | A 窗 年化（p10～p90） | A 窗 回落 | B 窗 年化（p10～p90） | B 窗 回落 | 槽位 | 筆數 | 全窗 | A 窗 | B 窗 | 三窗全過 |",
              "|---:|---:|---|---:|---|---:|---:|---:|---:|---:|---:|:--:|:--:|:--:|:--:|"]
        for r in B.itertuples():
            LB.append(f"| {r.N} | {r.cagr * 100:+.2f}% | {r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f} | {r.mdd * 100:.1f}% | "
                      f"{r.mdd_p10 * 100:.1f}～{r.mdd_p90 * 100:.1f} | {r.ca * 100:+.2f}%（{r.ca_p10 * 100:+.1f}～{r.ca_p90 * 100:+.1f}） | {r.ma * 100:.1f}% | "
                      f"{r.cb * 100:+.2f}%（{r.cb_p10 * 100:+.1f}～{r.cb_p90 * 100:+.1f}） | {r.mb * 100:.1f}% | {r.slot:.2f} | {r.m:.0f} | "
                      f"{'✅' if r.win_all else '✗'} | {'✅' if r.win_a else '✗'} | {'✅' if r.win_b else '✗'} | {'✅' if r.win else '⛔'} |")
        LB.append("")
        open(os.path.join(a.out, "BASELINE_REPORT.md"), "w", encoding="utf-8").write("\n".join(LB) + "\n")
        log(f"寫入 {os.path.join(a.out, 'BASELINE_REPORT.md')}")


if __name__ == "__main__":
    sys.exit(main())

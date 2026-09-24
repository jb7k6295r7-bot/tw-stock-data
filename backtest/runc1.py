"""PREREGC1 主程式：六幣逐幣跑 ＋ 交件報告 —— 回測線執行端。

⛔ 判準／出口／措辭全部逐字取自 v6，⛔ 本支只跑與報。
⭐ 開跑前先跑 selftest_researchc1（必10 的 fixture ＋ 突變 ＋ 鑑別力）⇒ 不綠就停。
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C   # noqa: E402

OUT = C.OUT
os.makedirs(OUT, exist_ok=True)
L_ = []
A = L_.append


def load(sym: str) -> pd.DataFrame:
    p = os.path.join(C.DATA, "{}.csv".format(sym))
    d = pd.read_csv(p, dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    return d


def main():
    t0 = time.time()
    log = lambda x: print(x, flush=True)

    # ① ⭐ 先跑必10 的自測（⛔ 不綠就停，⛔ 不報任何結果）
    log("[必10] 跑 fixture ＋ 突變 ＋ 鑑別力自測…")
    r = subprocess.run([sys.executable, "-m", "backtest.selftest_researchc1"],
                       cwd=os.path.expanduser("~/tw-p17"),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:]); print(r.stderr[-2000:])
        raise SystemExit("⛔⛔ 必10 自測沒過 ⇒ 停止，⛔ 不出任何結果")
    log("[必10] ✅ 全綠（含第 ⓪ 格鑑別力證明）")

    # ② 資料與逐幣根數（⭐ 裁定線 0038 §四 要求逐幣表加兩個 N 的窗首日）
    raw = {s: load(s) for s in C.COINS}
    for s, d in raw.items():
        if d["date"].iloc[-1] != C.LAST_FULL:
            raise SystemExit("⛔ {} 末日 {} ≠ 登錄寫死的 {} ⇒ 停跑"
                             .format(s, d["date"].iloc[-1], C.LAST_FULL))
        gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
        if gap != len(d):
            raise SystemExit("⛔ {} 有缺口：末−首+1 ＝ {} ≠ 列數 {}".format(s, gap, len(d)))
    log("[資料] ✅ 六幣末日皆 {}，逐幣「末−首+1 ＝ 列數」⇒ 缺口 0（對上口徑 v3 附表一）"
        .format(C.LAST_FULL))

    btc_close = raw["BTC"]["close"].to_numpy(float)
    btc_date = raw["BTC"]["date"].to_numpy()

    rows, plc_rows = [], []
    for s in C.COINS:
        d = raw[s]
        c = d["close"].to_numpy(float)
        dates = d["date"].to_numpy()
        rec = {"coin": s, "rows": len(d), "first": dates[0], "last": dates[-1]}

        for n, tag in ((C.N_MAIN, "n200"), (C.N_ROBUST, "n50")):
            res = C.rule_series(c, n)
            if res is None:
                raise SystemExit("⛔ {} 連 SMA{} 都算不出來".format(s, n))
            w0 = res["w0"]
            rr, rb = res["r_rule"], res["r_bh"]
            cg_r, md_r = C.cagr(rr), C.mdd(rr)
            cg_b, md_b = C.cagr(rb), C.mdd(rb)
            ok, sc, sm = C.judge(cg_r, md_r, cg_b, md_b)
            held = res["held"]
            segs = C.segments(held)
            n_trades = int(np.abs(np.diff(np.insert(held, 0, 0.0))).sum())
            rec.update({
                tag + "_w0_date": dates[w0], tag + "_days": len(rr),
                tag + "_cagr_rule": cg_r, tag + "_mdd_rule": md_r,
                tag + "_cagr_bh": cg_b, tag + "_mdd_bh": md_b,
                tag + "_d_cagr": cg_r - cg_b, tag + "_d_mdd": abs(md_r) - abs(md_b),
                tag + "_pass": ok, tag + "_strict_cagr": sc, tag + "_strict_mdd": sm,
                tag + "_expo": float(held.mean()), tag + "_trades": n_trades,
                tag + "_nseg": len(segs),
                tag + "_hold_len_med": float(np.median([l for v, l in segs if v == 1]))
                    if any(v == 1 for v, l in segs) else np.nan,
                tag + "_cash_len_med": float(np.median([l for v, l in segs if v == 0]))
                    if any(v == 0 for v, l in segs) else np.nan,
            })

            if tag == "n200":                     # ⭐ 判定格只有 N=200（裁定線 0038 §一③）
                Lb = C.politis_white_block(rr - rb)     # ⭐ 抽的是配對差本身（§2-D）
                rng = np.random.default_rng(C.SEED)
                ci1 = C.paired_ci(rr, rb, Lb, rng)
                rng2 = np.random.default_rng(C.SEED)
                ci2 = C.paired_ci(rr, rb, 2 * Lb, rng2)
                ex, why = C.exit_of(ok, sc, sm, ci1, ci2["mdd"])
                rec.update({"L": Lb, "ci_cagr_lo": ci1["cagr"][0], "ci_cagr_hi": ci1["cagr"][1],
                            "ci_mdd_lo": ci1["mdd"][0], "ci_mdd_hi": ci1["mdd"][1],
                            "ci_mdd2_lo": ci2["mdd"][0], "ci_mdd2_hi": ci2["mdd"][1],
                            "exit": ex, "exit_why": why})
                # §五：假訊號欄的兩個結構檢查（⛔ 事前寫死）
                degen = []
                if rec["n200_expo"] >= C.EXPO_DEGEN:
                    degen.append("曝險 {:.1%} ≥ 90% ⇒ 假訊號閘結構上退化（§四④）"
                                 .format(rec["n200_expo"]))
                if n_trades < C.MIN_TRADES:
                    degen.append("進出場 {} 次 < 5 ⇒ 假訊號欄結構上不可得（§五②）".format(n_trades))
                rec["placebo_status"] = "；".join(degen) if degen else "可得"
                if not degen:
                    rngp = np.random.default_rng(C.SEED)
                    pcg, pmd = C.placebo_dist(held, rb, rngp)
                    rec["plc_cagr_pctl"] = float((pcg < cg_r).mean() * 100)
                    rec["plc_mdd_pctl"] = float((pmd > abs(md_r)).mean() * 100)
                    for k in range(len(pcg)):
                        plc_rows.append({"coin": s, "rep": k, "cagr": pcg[k], "mdd_abs": pmd[k]})
                else:
                    rec["plc_cagr_pctl"] = np.nan; rec["plc_mdd_pctl"] = np.nan
                # §五之二 損益兩平成本
                rec["be_cagr"] = C.breakeven_cost(c, n, "CAGR", cg_b, md_b) if sc else np.nan
                rec["be_mdd"] = C.breakeven_cost(c, n, "MDD", cg_b, md_b) if sm else np.nan
                # §2-C② BTC 描述欄（⭐ 逐幣對齊窗）
                i0 = int(np.flatnonzero(btc_date == dates[w0])[0])
                bseg = btc_close[i0:]
                br = np.empty(len(bseg)); br[0] = 0.0
                br[1:] = bseg[1:] / bseg[:-1] - 1.0
                rec["btc_cagr_samewin"] = C.cagr(br[1:])
                rec["btc_mdd_samewin"] = C.mdd(br[1:])
        rows.append(rec)
        log("[{}] N200 窗首 {}（{} 日）｜規則 {:+.2%}/{:.2%}　BH {:+.2%}/{:.2%}｜{}｜{}"
            .format(s, rec["n200_w0_date"], rec["n200_days"],
                    rec["n200_cagr_rule"], rec["n200_mdd_rule"],
                    rec["n200_cagr_bh"], rec["n200_mdd_bh"],
                    "判定格過" if rec["n200_pass"] else "判定格未過", rec["exit"]))

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "per_coin.csv"), index=False)
    if plc_rows:
        pd.DataFrame(plc_rows).to_csv(os.path.join(OUT, "placebo.csv.gz"), index=False)
    log("[完成] {:.0f}s".format(time.time() - t0))
    return df


if __name__ == "__main__":
    main()

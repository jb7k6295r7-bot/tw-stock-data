#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回算 N₁ 的歷史日序列：每天有幾檔通過「近 20 日均額 ≥ 5,000 萬」。

    python3 n1_history.py            # 寫 data/meta/_n1_history.csv 並印分位數

## 定義（**逐字沿用市場情報分析線 2026-09-09 09:55 給回測線那封**，⛔ 不自行調整）

- 用 `amount` 欄（成交金額）
- 視窗 **T−20 ～ T−1**，二十個交易日，**以交易日曆為準**
- **算術平均**
- **沒成交的那天記 0，不是跳過** ← 這一條會讓冷門股的均額被拉低，那是刻意的
- **≥ 50,000,000 等號通過**
- **不含當日**（T 自己不進視窗）

`N₁(t)` ＝ 該日通過此門檻的證券檔數。

## ⚠⚠ 這份序列**不是歷史事實**

回算用的是**現在的資料庫**，而當時的資料可能後來被回補過
（breadth 今天就從 1,401 補到 2,801 天）。
⇒ **只能用來訂門檻的量級，不可以當成「那天實際跑出來是多少」的紀錄。**
這句話也寫進輸出檔的檔頭，免得日後被當成歷史事實引用。
"""
import csv
import glob
import io
import os
import sys

import numpy as np

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CAL = os.path.join(_ROOT, "meta", "calendar_twse.csv")
STOCKS = os.path.join(_ROOT, "stocks")
OUT = os.path.join(_ROOT, "meta", "_n1_history.csv")

WIN = 20
THRESH = 50_000_000.0
NOTE = ("# ⚠ 這份是**用現在的資料庫回算**的，不是當時實際跑出來的數字。"
        "當時的資料可能後來被回補過 ⇒ 只能用來訂門檻的量級，"
        "⛔ 不可以當成「那天實際跑出來是多少」的紀錄。")


def main():
    rl = runlog.Run("n1_history")
    with io.open(CAL, encoding="utf-8") as f:
        days = [r.split(",")[0].strip() for i, r in enumerate(f) if i and r.strip()]
    days.sort()
    pos = {d: i for i, d in enumerate(days)}
    n = len(days)
    # ★ 每天通過的檔數 = 對每一檔算「視窗均額 ≥ 門檻」再逐日相加。
    #   ⛔ 不可以只在「當天有成交」時才算：門檻用的是**過去 20 日**，
    #     而那 20 日裡沒成交的記 0——這正是定義裡那一條。
    #   ⚠ 但一檔要「存在」才算得上：用它自己的第一筆與最後一筆有成交日當存續區間，
    #     否則上市前與下市後也會被算成「均額 0、不通過」，那不影響計數，
    #     可是會讓「母體有幾檔」失去意義。這裡只數通過的，所以不受影響。
    # ★ 母體條件（市場情報分析線 2026-09-09 17:15 補上，取代 09:55 那版）
    #   ⛔ 09:55 那版只寫了「**怎麼算**」沒寫「**算誰**」，
    #     逐字執行的結果把興櫃與 ETF 都收了進來（實測 765 檔裡有 118 檔 ETF、8 檔興櫃）。
    #   ⚠ 這個缺口不是被寫規格的人發現的，是被「回一個沒人問的差集組成」抓到的
    #     ⇒ **規格的完整性缺口，在被別人用之前不會顯現。**
    KIND_OK, MARKET_OK = "stock", ("twse", "tpex")
    meta = {}
    sp = os.path.join(_ROOT, "meta", "stocks.csv")
    try:
        with io.open(sp, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                meta[r["stock_id"]] = (r.get("kind", ""), r.get("market", ""))
    except OSError as ex:                                        # noqa: BLE001
        rl.check("讀得到 stocks.csv（母體條件要用）", False, str(ex))
        return rl.finish()

    cnt = np.zeros(n, dtype=np.int32)
    files = sorted(glob.glob(os.path.join(STOCKS, "*.csv")))
    n_files = n_rows = n_skip = 0
    for fn in files:
        sid = os.path.basename(fn)[:-4]
        k, m = meta.get(sid, ("", ""))
        if k != KIND_OK or m not in MARKET_OK:
            n_skip += 1
            continue
        amt = np.zeros(n, dtype=np.float64)
        got = False
        with io.open(fn, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = (r.get("date") or "").strip()
                i = pos.get(d)
                if i is None:
                    continue
                try:
                    v = float((r.get("amount") or "0").replace(",", "") or 0)
                except ValueError:
                    continue
                amt[i] = v
                got = True
                n_rows += 1
        if not got:
            continue
        n_files += 1
        # 視窗 T−20 ~ T−1 的和：cumsum 差分，再往後挪一天（不含當日）
        cs = np.concatenate(([0.0], np.cumsum(amt)))
        win_sum = cs[WIN:] - cs[:-WIN]          # 長度 n-WIN+1，對應結束於 index WIN-1..n-1
        # 結束於 t-1 的視窗 → 對應 t = WIN..n-1
        mean_prev = win_sum[:-1] / WIN          # 對應 t = WIN..n-1
        ok = mean_prev >= THRESH
        cnt[WIN:] += ok.astype(np.int32)

    rl.info("母體", f"{n_files:,} 檔（{n_rows:,} 列）｜交易日 {n:,} 天"
                    f"｜⛔ 因母體條件排除 {n_skip:,} 檔（非普通股或非上市櫃）")
    rl.info("定義", f"kind=={KIND_OK} 且 market∈{MARKET_OK}｜amount 欄｜"
                    f"T−{WIN}~T−1｜算術平均｜沒成交記 0｜"
                    f"≥ {THRESH:,.0f} 等號通過｜不含當日")

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="") as f:
            # ⛔ 這裡**不寫 `#` 註解行**。情報分析 12:35 要求「檔頭寫那句話」，
            #   我照做之後**兩分鐘內自己就被它咬到**：
            #       csv.DictReader 把 `# ⚠ …` 當成表頭 ⇒ `r['date']` KeyError ⇒
            #       整批被過濾掉，而且**不會報錯**，只是筆數變 0。
            #   ⇒ CSV 保持乾淨（第一行就是表頭），那句話改放三個**會被讀到**的地方：
            #     ① 同名 sidecar `_n1_history.md`　② `_last_run.md` 的 info
            #     ③ 這支的 docstring
            #   ⚠ 已回報情報分析並說明理由，要改回去他們裁。
            w = csv.writer(f)
            w.writerow(["date", "n1"])
            for i in range(WIN, n):          # 前 WIN 天沒有完整視窗，不輸出
                w.writerow([days[i], int(cnt[i])])
        with io.open(OUT[:-4] + ".md", "w", encoding="utf-8") as f:
            f.write("# `_n1_history.csv` 的讀法\n\n")
            f.write(NOTE.lstrip("# ") + "\n\n")
            f.write("## 定義（⛔ 逐字沿用市場情報分析線 2026-09-09 09:55，不自行調整）\n\n")
            f.write(f"- `amount` 欄｜視窗 **T−{WIN} ～ T−1**（以交易日曆為準）｜算術平均\n")
            f.write("- **沒成交的那天記 0，不是跳過**\n")
            f.write(f"- **≥ {THRESH:,.0f} 等號通過**｜**不含當日**\n")
            f.write(f"- `n1` ＝ 該日通過此門檻的證券檔數\n\n")
            f.write(f"⚠ 前 {WIN} 個交易日視窗不完整，**不輸出**（不是 0，是沒有）。\n")
        rl.info("寫出", f"{OUT}（{n - WIN:,} 列，前 {WIN} 天視窗不完整不輸出）"
                        f"＋ sidecar {os.path.basename(OUT)[:-4]}.md")
        rl.info("⚠ 這份不是歷史事實",
                "用**現在的資料庫**回算的；當時的資料可能後來被回補過"
                "⇒ 只能用來訂門檻的量級，⛔ 不可以當成「那天實際跑出來是多少」")
    except OSError as ex:                                        # noqa: BLE001
        rl.check("寫得出 _n1_history.csv", False, str(ex))
        return rl.finish()

    v = cnt[WIN:].astype(np.float64)
    # ★ 單日變化率 N₁(t)/N₁(t−1)。⛔ 前一天是 0 就跳過（除以 0 不是資料，是缺值）。
    prev, cur = v[:-1], v[1:]
    m = prev > 0
    ratio = cur[m] / prev[m]
    qs = [0.1, 1, 5, 50, 95, 99, 99.9]
    pv = np.percentile(ratio, qs)
    rl.info("N₁ 範圍", f"最小 {int(v.min()):,}｜中位 {int(np.median(v)):,}｜"
                       f"最大 {int(v.max()):,}｜最後一天 {int(v[-1]):,}")
    rl.info("N₁(t)/N₁(t−1) 分位數",
            "　".join(f"p{q}={x:.4f}" for q, x in zip(qs, pv))
            + f"（{len(ratio):,} 個樣本，前一天為 0 的 {int((~m).sum())} 個已排除）")
    print("\n".join(f"  p{q}\t{x:.4f}" for q, x in zip(qs, pv)))
    # ⚠ 這一支只產數字，**不訂門檻**——門檻歸 K線線裁定。
    rl.check("有算出分位數", len(ratio) > 100, f"樣本只有 {len(ratio)}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())

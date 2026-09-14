"""p4_features 自測：① shares 只 ffill 不 bfill；② rev_hi24_p4 的 18/24 與 NaN；③ 橫截面百分位＋補 50；④ 歸型取最近中心；
⑤ 真實一檔（2330）的量級。rc != 0 或輸出含 ✗ 才算紅（突變見檔尾）。"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import p4_features as P  # noqa: E402
from backtest import data as D  # noqa: E402

FAIL = 0


def check(cond, msg):
    global FAIL
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAIL += 1


def t_measurement_days():
    cal = D.load_calendar()
    md = P.measurement_days(cal, "2026-01-01", "2026-09-30")
    days = [str(cal[i].date()) for i in md]
    check(days[0] == "2026-01-02" and "2026-09-01" in days and len(days) == 9, f"2026 每月第一個交易日 {days}")


def t_rev_flags():
    periods = [f"{y}-{m:02d}" for y in range(2015, 2018) for m in range(1, 13)]
    cal = D.load_calendar()
    rev = pd.DataFrame({"A": np.arange(1, 37, dtype=float), "B": np.arange(1, 37, dtype=float)}, index=periods)
    rev.loc[periods[5:13], "B"] = np.nan          # B 有 8 期缺 ⇒ 第 25 期時近 24 期只有 16 有效 ⇒ NaN
    rev.loc["2017-06", "A"] = 10.0                # A 在 2017-06 沒創高
    F = P.rev_hi24_flags(rev, cal)
    a = F["A"].dropna(); b = F["B"].dropna()
    # A：2017-01 期（第 25 期）起有值；可得日＝2017-02-10 後第一個交易日
    first = a.index[0]
    check(first > pd.Timestamp("2017-02-10") and first <= pd.Timestamp("2017-02-15"), f"A 第一個有值日 {first.date()}（2017-01 期次月 10 日後）")
    check(a.iloc[0] == 100.0, "A 2017-01 期創高 ⇒ 100")
    # 2017-06 期在 2017-07-1x 生效 ⇒ 0
    v = F["A"].loc[:"2017-07-15"].iloc[-1]   # 07-15 是週六 ⇒ 取之前最後一個交易日
    check(v == 0.0, f"A 2017-06 沒創高 ⇒ 0（讀到 {v}）")
    # B：第 25～32 期（2017-01～2017-08）近 24 期有效 < 18 ⇒ NaN；2017-09 期（近 24 期＝2015-09～2017-08，缺 2015-09～2016-01 五期 ⇒ 19 有效）⇒ 有值
    check(pd.isna(F["B"].loc[:"2017-03-15"].iloc[-1]), "B 有效期數 < 18 ⇒ NaN（不是 0）")
    check(F["B"].loc[:"2017-10-20"].iloc[-1] == 100.0, "B 有效期數 ≥ 18 後恢復 ⇒ 100")


def t_shares_ffill_not_bfill():
    cal = D.load_calendar()
    s = P.load_shares("2330", cal)
    check(s.notna().sum() > 2000 and float(s.iloc[-1]) > 2e10, f"2330 shares 有值 {int(s.notna().sum())} 天、最後 {s.iloc[-1]:.0f}")
    # 不存在的代號 ⇒ 全 NaN（不會被補）
    z = P.load_shares("000000", cal); check(z.isna().all(), "無檔 ⇒ shares 全 NaN")


def t_cross_section_assign():
    day = pd.DataFrame({f: [1.0, 2.0, 3.0, np.nan] for f in P.PCT_FEATURES}, index=list("abcd"))
    for f in P.BOOL_FEATURES:
        day[f] = [100.0, 0.0, np.nan, 100.0]
    X = P.cross_section(day)
    check(list(X.loc["a", P.PCT_FEATURES].round(1)) == [33.3] * 10 and X.loc["c", "ret_20"] == 100.0 and X.loc["d", "ret_20"] == 50.0, "百分位（rank pct×100，NaN 不進分母）：a＝33.3、c＝100、缺值＝50")
    check(X.loc["c", "ma_stack"] == 50.0 and X.loc["a", "ma_stack"] == 100.0, "布林缺值補 50、有值照舊")
    C = np.zeros((4, 13)); C[1] = 2.0; C[2, :5] = 2.0; C[3, 5:] = 2.0   # 中心在標準化空間
    mu = np.full(13, 50.0); sd = np.full(13, 25.0)
    lab = P.assign(X, C, mu, sd)
    check(lab[0] == 0 and lab[3] == 0, f"歸型最近中心 {lab.tolist()}（a、d 靠近 0 向量）")
    X2 = pd.DataFrame([[100.0] * 13], columns=P.FEATURES); check(P.assign(X2, C, mu, sd)[0] == 1, "全 100 ⇒ 中心 1")


def t_real_stock():
    cal = D.load_calendar()
    raw = P.stock_raw("2330", "twse", cal)
    last = raw.dropna(subset=["ret_120", "amt20", "turn20"]).iloc[-1]
    check(abs(last["ret_120"]) < 3 and last["amt20"] > 1e9, f"2330 ret_120 {last['ret_120']:+.3f}、amt20 {last['amt20']:.3e}")
    check(0 < last["turn20"] < 100, f"2330 turn20 {last['turn20']:.3f}（每日成交張數/千張股本）")
    check(np.isfinite(last["fore20"]) and last["shares_ok"] == 1, f"2330 fore20 {last['fore20']:+.3f}、shares_ok")
    md = P.measurement_days(cal, "2024-01-01", "2024-12-31")
    fr = P.forward_returns(raw, int(md[0]))
    check(fr["entry_pos"] == md[0] + 1 and np.isfinite(fr["ret_120"]), f"2024-01 量測日次日進、H120 {fr['ret_120']:+.3f}")
    # 前 120 根 ret_120 必為 NaN（只看過去）
    check(raw["ret_120"].iloc[:120].isna().all(), "ret_120 前 120 根 NaN")


if __name__ == "__main__":
    print("[p4_features] 量測日"); t_measurement_days()
    print("[p4_features] rev_hi24_p4"); t_rev_flags()
    print("[p4_features] shares"); t_shares_ffill_not_bfill()
    print("[p4_features] 橫截面＋歸型"); t_cross_section_assign()
    print("[p4_features] 真實一檔"); t_real_stock()
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變（前後 rm -rf backtest/__pycache__）：
#  M1 REV_MIN_VALID 18 → 10           ⇒ rev 第 4 條紅（B 提早有值）
#  M2 load_shares 的 ffill 改 ffill().bfill() ⇒ 真實一檔不紅（2330 沒有前段缺），⚠ 這條要靠 code review；改用 shares 從 2016 才有的檔才抓得到
#  M3 cross_section 補 50 拿掉         ⇒ 橫截面第 1、2 條紅
#  M4 forward_returns 進場改當日開盤    ⇒ 真實一檔 entry_pos 紅

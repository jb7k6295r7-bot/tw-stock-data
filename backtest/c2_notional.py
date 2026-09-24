# -*- coding: utf-8 -*-
"""C2 §六⑤ 的實作讀法：名目價值要用哪個價（⇐ 加密策略線 20260924-2200 指名回測線寫）。

官方：Funding Amount ＝ **Nominal Value** × Funding Rate，而 Nominal Value ＝ **Mark Price** × Size。
⚠ 本線只有【日線 OHLC】（data/crypto/<SYM>.csv）⇒ Mark Price 拿不到 ⇒ 必須近似。

⛔ 本線不訂約定（那是策略線／裁定線的格子）。本支做兩件本線該做的：
  ① ⭐⭐ 先分清哪些讀法【根本不可用】—— 結算時點在當日盤中 ⇒ 用當日收盤／高低就是看未來
  ② 對【可用的】讀法，用真實月檔量出差多少 ⇒ 讓那個選擇有數字可依

真實資料：backtest/fixtures_c2/SOLUSDT-2022-11.csv（資料庫線交的封存月檔）
         data/crypto/SOL.csv（日線 OHLC）
"""
from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import funding as F

SYM, Y, M = "SOL", 2022, 11
d = F.load_month(SYM, Y, M)
print("=== ① 真實月檔：{}USDT {}-{:02d} ===".format(SYM, Y, M))
print("  結算筆數 {}｜間隔混合 {}".format(len(d), F.interval_mix(d)))
print("  Σ last_funding_rate ＝ {!r}".format(F.cum_cost(d)))
print("  ⇒ ⭐ 加密策略線 2200 說「SOL 2022-11 Σ＝−0.354915」⇒ 本線重算 {:.6f}".format(F.cum_cost(d)))
assert abs(F.cum_cost(d) + 0.354915) < 5e-7, "⛔ Σ 對不上加密策略線寄來的 −0.354915"
print("  ✅ 逐位對上（誤差 < 5e-7）")
print("  ⇒ ⭐ 只做多 ⇒ ΔEquity ＝ −rate × 名目 ⇒ Σ 為負 ⇒ 這個月對多方是【收入】")

px = pd.read_csv("data/crypto/{}.csv".format(SYM), parse_dates=["date"])
px = px.set_index("date").sort_index()
d = d.sort_values("ts").reset_index(drop=True)
d["day"] = d["ts"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
d["hour"] = d["ts"].dt.tz_convert("UTC").dt.hour
print()
print("=== ② 結算時點的 UTC 小時分佈（⭐ 決定哪些讀法可用）===")
print("  " + str(dict(d["hour"].value_counts().sort_index())))
print("  ⇒ 日線的一根 K 棒代表【整個 UTC 日】⇒ 收盤是當日 23:59 才知道的")
print("  ⇒ ⛔ 所以任何落在 00:00~23:59 之間的結算，用【當日收盤／高／低】都是看未來")
n_after_open = int((d["hour"] > 0).sum())
print("  ⇒ 落在 00 時之後的結算 {}／{} 筆 ⇒ ⚠ 連【當日開盤】都只對 00:00 那一筆嚴格成立"
      .format(n_after_open, len(d)))

#  ── 幾種讀法
def series(kind):
    if kind == "prev_close":
        s = px["close"].shift(1)
    elif kind == "open":
        s = px["open"]
    elif kind == "close":
        s = px["close"]
    elif kind == "hl2":
        s = (px["high"] + px["low"]) / 2
    elif kind == "ohlc4":
        s = (px["open"] + px["high"] + px["low"] + px["close"]) / 4
    else:
        raise SystemExit("⛔ 未知讀法 " + kind)
    return s.astype(float)


KINDS = [
    ("prev_close", "前一日收盤", "✅ 可用（⭐ 唯一對【每一筆】結算都不看未來的）"),
    ("open", "當日開盤", "⚠ 只對 00:00 那一筆嚴格成立；之後的結算已經是盤中"),
    ("close", "當日收盤", "⛔ 不可用（當日 23:59 才知道）"),
    ("hl2", "當日 (H+L)/2", "⛔ 不可用（整日才知道）"),
    ("ohlc4", "當日 OHLC 平均", "⛔ 不可用（整日才知道）"),
]
rows = []
for k, lab, adm in KINDS:
    s = series(k)
    p = d["day"].map(s)
    assert p.notna().all(), "⛔ {} 有對不到價的結算日".format(k)
    #  ⭐ 持有 1 顆（size=1）連續整月 ⇒ Σ rate × price ＝ 該月的資金費現金流（USDT）
    cash = float((d["last_funding_rate"] * p).sum())
    rows.append(dict(讀法=k, 說明=lab, 可用性=adm, 現金流USDT=-cash,
                     用到的價_首=float(p.iloc[0]), 用到的價_尾=float(p.iloc[-1])))
T = pd.DataFrame(rows)
print()
print("=== ③ ⭐ 五種讀法各算出多少（持有 1 顆 SOL 整月；ΔEquity ＝ −Σ rate×price）===")
print(T[["讀法", "說明", "現金流USDT", "用到的價_首", "用到的價_尾"]].to_string(index=False))
print()
for _, r in T.iterrows():
    print("  {:11s} {}".format(r["讀法"], r["可用性"]))

adm = T[T["可用性"].str.startswith(("✅", "⚠"))]
lo, hi = adm["現金流USDT"].min(), adm["現金流USDT"].max()
allo, alhi = T["現金流USDT"].min(), T["現金流USDT"].max()
p0 = float(px["close"].loc[str(Y) + "-" + "{:02d}".format(M)].iloc[0])
print()
print("=== ④ ⭐⭐ 差多少（這才是選擇的依據）===")
print("  月初收盤價（做分母，⭐ 讓數字可比）＝ {:.2f} USDT".format(p0))
print("  【可用的兩種】區間 {:.4f} ~ {:.4f} USDT ⇒ 差 {:.4f} USDT ＝ 名目的 {:.4f}%".format(
    lo, hi, hi - lo, (hi - lo) / p0 * 100))
print("  【全部五種】區間 {:.4f} ~ {:.4f} USDT ⇒ 差 {:.4f} USDT ＝ 名目的 {:.4f}%".format(
    allo, alhi, alhi - allo, (alhi - allo) / p0 * 100))
print("  ⇒ 而該月的 Σrate ＝ {:.6f}（＝ {:.2f}% 的名目）".format(
    F.cum_cost(d), abs(F.cum_cost(d)) * 100))
print()
print("=== ④-2 ⭐⭐⭐ 而真正要緊的【不是】用哪個日價，是【逐筆乘】還是【乘一個價】 ===")
p_start = float(px["close"].loc["{}-{:02d}".format(Y, M)].iloc[0])
p_end = float(px["close"].loc["{}-{:02d}".format(Y, M)].iloc[-1])
wrong_start = -F.cum_cost(d) * p_start
wrong_end = -F.cum_cost(d) * p_end
right = float(adm["現金流USDT"].iloc[0])
print("  ✅ 正確（逐筆 rate × 當時的價）              {:8.4f} USDT".format(right))
print("  ⛔ 誤法甲（Σrate × **月初**收盤 {:.2f}）      {:8.4f} USDT ⇒ 是正確值的 {:.2f} 倍".format(
    p_start, wrong_start, wrong_start / right))
print("  ⛔ 誤法乙（Σrate × **月末**收盤 {:.2f}）      {:8.4f} USDT ⇒ 是正確值的 {:.2f} 倍".format(
    p_end, wrong_end, wrong_end / right))
print("  ⇒ ⭐ 成因：該月 SOL 從 {:.2f} 跌到 {:.2f}（−{:.0f}%）⇒ 名目一路縮小".format(
    p_start, p_end, (1 - p_end / p_start) * 100))
print("     ⇒ ⇒ 費率大的那幾天名目已經小了 ⇒ 用單一個價會把現金流放大約【兩倍】")
print("  ⇒ ⭐⭐ 所以實作讀法的重點順序是：")
print("     ① **必須逐筆乘當時的名目**（差兩倍）　② 日價用哪一個（差 0.0007%，⇒ 幾乎不重要）")
print()
print("=== ⑤ ⇒ 本線寫給登錄的【實作讀法】（⛔ 本線不裁，只提字面）===")
print("""  「名目價值 ＝ **前一交易日收盤價** × 部位數量（Mark Price 取不到的近似）。
    ⭐ 理由是【可實作性】，⛔ 不是精確度：日線 K 棒的收盤／高／低都要到當日結束才知道，
      而結算時點落在盤中 ⇒ 用它們會把當日資訊帶進當日的現金流。
    ⚠ 已量的近似誤差（SOL 2022-11，持有 1 顆整月）：
      前一日收盤 vs 當日開盤 差 {:.4f} USDT ＝ 名目的 {:.4f}%；
      若誤用當日收盤／高低 ⇒ 全距 {:.4f}% 名目。
    ⛔ 本近似【不適用】於要逐筆對帳 Binance 實際扣款的場合。」""".format(
    hi - lo, (hi - lo) / p0 * 100, (alhi - allo) / p0 * 100))

# ⛔ 鑑別力自測：把價序列整體乘 2，現金流必須跟著變成 2 倍（⇒ 價真的進了算式）
s = series("prev_close")
p = d["day"].map(s)
c1 = float((d["last_funding_rate"] * p).sum())
c2 = float((d["last_funding_rate"] * (p * 2)).sum())
assert abs(c2 - 2 * c1) < 1e-9 and abs(c1) > 1e-6, "⛔ 價沒有真的進到算式裡"
print()
print("✅ 鑑別力自測：價序列乘 2 ⇒ 現金流恰好變 2 倍（⇒ 價真的進了算式，⛔ 不是常數）")

os.makedirs("backtest/results_step2", exist_ok=True)
T.to_csv("backtest/results_step2/c2_notional_price.csv", index=False, encoding="utf-8")
print("⇒ 落檔 backtest/results_step2/c2_notional_price.csv")

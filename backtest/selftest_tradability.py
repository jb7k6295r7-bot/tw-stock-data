# -*- coding: utf-8 -*-
"""simulate_mtm 新參數 tradable 的手算 fixture（⇐ 裁定線 1714 §一「先做 fixture：一個漲停開盤買不到、
一個停牌中到期 ⇒ 手算、先證明分得出來」〈一百一十三〉）。
⭐ 每個案例都跑【關】與【開】兩次，並斷言兩者不同 ⇒ 證明 fixture 有鑑別力（⛔ 否則開關壞掉也會全綠）。
合成資料：40 個交易日、n_slots＝1、成本 COST＝0.585% 來回（evaluate.COST）。"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R
C = R.COST; N = 40; ok = 0
def arr(v): return np.full(N, float(v))
def flags(): return {"trd": np.ones(N, bool), "up_o": np.zeros(N, bool), "dn_o": np.zeros(N, bool)}
def sig(rows): return pd.DataFrame(rows)
def run(s, cl, op, tr=None, pick=None):
    return R.simulate_mtm(s, "T", 1, np.random.default_rng(0), cl, op, N, return_equity=True, pick=pick, tradable=tr)
def close(a, b): return abs(a - b) < 1e-12

# ── F1 漲停開盤買不到 ＋ ⛔ 不遞補 ─────────────────────
# A、B 同日訊號，relvol 讓 A 排第一；A 在進場日開盤＝漲停
clA, opA = arr(100), arr(100); clA[15:] = 110; clB, opB = arr(50), arr(50)
s1 = sig([{"sid": "A", "entry_pos": 10, "xpos_T": 15, "g_T": 110 / 100 - 1, "relvol": 2.0},
          {"sid": "B", "entry_pos": 10, "xpos_T": 15, "g_T": 0.0, "relvol": 1.0}])
cl = {"A": clA, "B": clB}; op = {"A": opA, "B": opB}
tr = {"A": flags(), "B": flags()}; tr["A"]["up_o"][10] = True
off = run(s1, cl, op, None, "relvol"); on = run(s1, cl, op, tr, "relvol")
assert off["trades"] == 1 and close(off["equity"][20], 1 + 0.10 - C), off["equity"][20]
assert on["trades"] == 0, "⛔ 漲停開盤不該成交"
assert close(on["equity"][20], 1.0), "⛔ 名額應持現金（⛔ 不遞補 B）"
assert on["tr_limit_up"] == 1
assert not close(off["equity"][20], on["equity"][20]); ok += 1
print("✅ F1 漲停開盤買不到：關 ⇒ 買到 A、終值 {:.6f}；開 ⇒ 0 筆、終值 1.000000（⛔ 沒有遞補 B）".format(off["equity"][20]))

# ── F2 停牌中到期 ⇒ 延到第一個可交易日【開盤】 ─────────
# A：10 日開盤 100 進；14 收 110；15～17 停牌（close ffill 110、open 缺）；18 開 90 收 92
clA = arr(100); clA[14:] = 110; clA[18:] = 92
opA = arr(100); opA[15:18] = np.nan; opA[18:] = 90
s2 = sig([{"sid": "A", "entry_pos": 10, "xpos_T": 15, "g_T": 110 / 100 - 1}])
tr = {"A": flags()}; tr["A"]["trd"][15:18] = False
off = run(s2, {"A": clA}, {"A": opA}); on = run(s2, {"A": clA}, {"A": opA}, tr)
assert close(off["equity"][15], 1 + 0.10 - C), "關：原版用停牌前 ffill 收盤『賣出』"
assert close(on["equity"][16], 1.10), "開：停牌期間照 ffill 收盤計值"
assert close(on["equity"][18], 1 + (90 / 100 - 1) - C), on["equity"][18]
assert on["tr_exit_delayed"] == 1
assert not close(off["equity"][25], on["equity"][25]); ok += 1
print("✅ F2 停牌中到期：關 ⇒ 15 日以停牌前舊價 110 賣出、終值 {:.6f}；開 ⇒ 18 日開盤 90 賣出、終值 {:.6f}".format(
    off["equity"][25], on["equity"][25]))

# ── F3 停牌後開盤跌停 ⇒ 再等一天 ───────────────────
opA3 = opA.copy(); opA3[19:] = 85; clA3 = clA.copy(); clA3[19:] = 86
tr = {"A": flags()}; tr["A"]["trd"][15:18] = False; tr["A"]["dn_o"][18] = True
on = run(s2, {"A": clA3}, {"A": opA3}, tr)
assert close(on["equity"][18], 0.92), "18 日開盤跌停賣不掉 ⇒ 照收盤 92 計值"
assert close(on["equity"][19], 1 + (85 / 100 - 1) - C), on["equity"][19]
ok += 1
print("✅ F3 停牌後開盤跌停：18 日賣不掉（計值 0.92）⇒ 19 日開盤 85 賣出、終值 {:.6f}".format(on["equity"][25]))

# ── F4 停牌日進場 ⇒ 跳過（⛔ 不走 613–615 用 ffill 收盤成交的退路）──
clA4 = arr(100); clA4[15:] = 120; opA4 = arr(100); opA4[10] = np.nan
s4 = sig([{"sid": "A", "entry_pos": 10, "xpos_T": 15, "g_T": 120 / 100 - 1}])
tr = {"A": flags()}; tr["A"]["trd"][10] = False
off = run(s4, {"A": clA4}, {"A": opA4}); on = run(s4, {"A": clA4}, {"A": opA4}, tr)
assert off["trades"] == 1, "關：原版走退路，用 ffill 收盤進場"
assert on["trades"] == 0 and on["tr_halt_in"] == 1 and close(on["equity"][20], 1.0)
assert not close(off["equity"][20], on["equity"][20]); ok += 1
print("✅ F4 停牌日進場：關 ⇒ 走退路照樣買（終值 {:.6f}）；開 ⇒ 跳過、持現金".format(off["equity"][20]))
print("\n⇒ {} 個 fixture 全過，⭐ 且 F1／F2／F4 的【關】與【開】都不同 ⇒ 新參數分得出來".format(ok))

# ── B1 builder（tradability.build）在真資料上的不變式 ＋ 人工複算一天 ──
# ⚠ 上面 F1～F4 直接餵旗標，⛔ 沒經過 build() ⇒ 2026-09-24 build() 的唯讀陣列 bug 它們抓不到 ⇒ 補這一條
from backtest import data as D, tradability as T
import math
cal = D.load_calendar()
for sid in ("2330", "2454", "3008"):
    f = T.one(sid, cal)
    assert f["trd"].shape == f["up_o"].shape == f["dn_o"].shape == (len(cal),)
    assert not (f["up_o"] & f["dn_o"]).any(), "同一天不可能開盤既漲停又跌停"
    assert not (f["up_o"] & ~f["trd"]).any() and not (f["dn_o"] & ~f["trd"]).any(), "沒成交的日子不可有漲跌停旗標"
raw = pd.read_csv(os.path.join(D.DATA, "stocks", "2330.csv"), dtype={"date": str})
raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
f = T.one("2330", cal); ks = np.flatnonzero(f["up_o"])
if len(ks):
    k = int(ks[0]); d = cal[k]; prev = raw.loc[:d].iloc[-2]; today = raw.loc[d]
    lim = 0.07 if d < pd.Timestamp("2015-06-01") else 0.10
    x = float(prev["close"]) * (1 + lim)
    tick = 0.01 if x < 10 else 0.05 if x < 50 else 0.1 if x < 100 else 0.5 if x < 500 else 1.0 if x < 1000 else 5.0
    hand = math.floor(x / tick + 1e-9) * tick          # ⭐ 人工照交易所規則複算（⛔ 不呼叫 R.limit_price）
    assert abs(float(today["open"]) - hand) < 1e-6, (d, prev["close"], today["open"], hand)
    print("✅ B1 builder：不變式三檔全過；人工複算 2330 {} 前收 {} ⇒ 漲停 {} ＝ 當日開盤 {}".format(
        d.date(), prev["close"], hand, today["open"]))
else:
    print("✅ B1 builder：不變式三檔全過（2330 全期沒有開盤漲停日，人工複算跳過）")

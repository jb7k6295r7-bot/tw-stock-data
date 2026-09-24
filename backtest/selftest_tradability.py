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
def flags(): return {"trd": np.ones(N, bool), "up_o": np.zeros(N, bool), "dn_o": np.zeros(N, bool), "dn_c": np.zeros(N, bool)}
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
# ── F5 排程出場日【收盤鎖跌停】⇒ 隔日開盤出（⇐ 裁定線 1744 裁 (乙)）────────
# A：10 日開盤 100 進；15 日（排程出場）收盤 90 ＝ 跌停；16 日開盤 93、收盤 95
clA5 = arr(100); clA5[15] = 90; clA5[16:] = 95; opA5 = arr(100); opA5[16:] = 93
s5 = sig([{"sid": "A", "entry_pos": 10, "xpos_T": 15, "g_T": 90 / 100 - 1}])
tr = {"A": flags()}; tr["A"]["dn_c"][15] = True
off = run(s5, {"A": clA5}, {"A": opA5}); on = run(s5, {"A": clA5}, {"A": opA5}, tr)
assert close(off["equity"][15], 1 + (90 / 100 - 1) - C), "關：原版在跌停收盤 90 賣出"
assert close(on["equity"][15], 0.90), "開：收盤鎖跌停賣不掉 ⇒ 照收盤 90 計值"
assert close(on["equity"][16], 1 + (93 / 100 - 1) - C), on["equity"][16]
assert on["tr_close_locked"] == 1 and on["tr_exit_delayed"] == 1
assert not close(off["equity"][20], on["equity"][20]); ok += 1
print("✅ F5 收盤鎖跌停：關 ⇒ 15 日跌停收盤 90 賣出、終值 {:.6f}；開 ⇒ 15 日賣不掉、16 日開盤 93 賣出、終值 {:.6f}".format(
    off["equity"][20], on["equity"][20]))

# ── F6 停損出場當天收盤鎖跌停 ⇒ ⛔ 不延後（停損記的是 t−1 收盤，與當天 dn_c 無關）──
clA6 = arr(100); clA6[12:] = 94; clA6[13] = 85; opA6 = arr(100); opA6[13:] = 90
s6 = sig([{"sid": "A", "entry_pos": 10, "xpos_T": 20, "g_T": 94 / 100 - 1}])
tr = {"A": flags()}; tr["A"]["dn_c"][13] = True
def run_s(s, cl, op, tr=None):
    return R.simulate_mtm(s, "T", 1, np.random.default_rng(0), cl, op, N, return_equity=True, stop=("fix", 0.05), tradable=tr)
off = run_s(s6, {"A": clA6}, {"A": opA6}); on = run_s(s6, {"A": clA6}, {"A": opA6}, tr)
assert off["stop_exits"] == 1 and on["stop_exits"] == 1
assert close(off["equity"][13], 1 + (94 / 100 - 1) - C) and close(on["equity"][13], off["equity"][13]), (off["equity"][13], on["equity"][13])
assert on["tr_close_locked"] == 0
ok += 1
print("✅ F6 停損日收盤鎖跌停：開關兩邊都在 13 日以 12 日收盤 94 出（{:.6f}），tr_close_locked＝0 ⇒ 只管排程出場".format(on["equity"][13]))
print("\n⇒ {} 個 fixture 全過，⭐ 且 F1／F2／F4／F5 的【關】與【開】都不同 ⇒ 新參數分得出來".format(ok))

# ══ F7～F10：delist 參數（裁定線 20260924-2319 seq98 §二，三案＋官方日一案）══════════════
from backtest import tradability as T
def run_n(s, cl, op, n, tr=None, dl=None):
    return R.simulate_mtm(s, "T", 1, np.random.default_rng(0), cl, op, n, return_equity=True, tradable=tr, delist=dl)
def flags_n(n): return {"trd": np.ones(n, bool), "up_o": np.zeros(n, bool), "dn_o": np.zeros(n, bool), "dn_c": np.zeros(n, bool)}
def cal_n(n): return pd.bdate_range("2020-01-01", periods=n)

# F7 停牌後復牌 ⇒ 仍延到第一個可交易日開盤（delist 給了也不能改這一案）
tr = {"A": flags()}; tr["A"]["trd"][15:18] = False
dl = T.delist_status(tr, cal_n(N))
assert dl["A"]["status"] == "live", dl
a = run(s2, {"A": clA}, {"A": opA}, tr); b = run_n(s2, {"A": clA}, {"A": opA}, N, tr, dl)
assert np.array_equal(a["equity"], b["equity"]) and b["tr_delist_settled"] == 0 and b["tr_delist_ambig"] == 0
assert b["tr_exit_delayed"] == 1; ok += 1
print("✅ F7 停牌後復牌：給不給 delist 權益逐位元相同（18 日開盤 90 賣出）；下市了結 0、無法區分 0")

# F8 下市且最後成交離日曆尾 ≥ 60 ⇒ 以最後成交價了結（＝ tradable 關閉時）
M = 100
cl8 = np.full(M, 100.0); cl8[14:] = 110.0; op8 = np.full(M, 100.0); op8[15:] = np.nan
s8 = sig([{"sid": "A", "entry_pos": 10, "xpos_T": 15, "g_T": 110 / 100 - 1}])
tr = {"A": flags_n(M)}; tr["A"]["trd"][15:] = False
dl = T.delist_status(tr, cal_n(M))
assert dl["A"] == {"last": 14, "status": "delisted_gap", "gap": 85}, dl
off = run_n(s8, {"A": cl8}, {"A": op8}, M); old = run_n(s8, {"A": cl8}, {"A": op8}, M, tr); new = run_n(s8, {"A": cl8}, {"A": op8}, M, tr, dl)
assert close(off["equity"][15], 1 + 0.10 - C), "關：15 日以最後價 110 了結"
assert old["tr_open_at_end"] == 1 and close(old["equity"][M - 1], 1.10), "舊（無 delist）：永遠延不到、掛到尾"
assert close(new["equity"][15], off["equity"][15]) and close(new["equity"][M - 1], off["equity"][M - 1])
assert new["tr_delist_settled"] == 1 and new["tr_open_at_end"] == 0
assert not close(old["equity"][M - 1], new["equity"][M - 1]); ok += 1
print("✅ F8 下市（gap 85 ≥ 60）：新 ⇒ 15 日以最後成交價 110 了結、終值 {:.6f}（＝ 關）；舊 ⇒ 掛到尾、終值 {:.6f}".format(
    new["equity"][M - 1], old["equity"][M - 1]))

# F9 最後成交離日曆尾 < 60、沒有官方日 ⇒ 分不出 ⇒ 照停牌（掛到尾）＋ 逐筆報數
cl9 = arr(100); cl9[14:] = 110; op9 = arr(100); op9[15:] = np.nan
tr = {"A": flags()}; tr["A"]["trd"][15:] = False
dl = T.delist_status(tr, cal_n(N))
assert dl["A"] == {"last": 14, "status": "ambig", "gap": 25}, dl
old = run_n(s8, {"A": cl9}, {"A": op9}, N, tr); new = run_n(s8, {"A": cl9}, {"A": op9}, N, tr, dl)
assert np.array_equal(old["equity"], new["equity"]) and new["tr_open_at_end"] == 1
assert new["tr_delist_ambig"] == 1 and new["tr_delist_settled"] == 0; ok += 1
print("✅ F9 最後成交離尾 25 < 60：照停牌掛到尾（權益與舊版逐位元相同）、無法區分 1 筆、了結 0")

# F10 同 F9，但有官方下市日 ⇒ 用官方 ⇒ 了結（⭐ 證明官方日優先於 gap）
dl = T.delist_status(tr, cal_n(N), official={"A": pd.Timestamp("2020-01-22")})
assert dl["A"]["status"] == "delisted_official", dl
new = run_n(s8, {"A": cl9}, {"A": op9}, N, tr, dl)
assert new["tr_delist_settled"] == 1 and close(new["equity"][15], 1 + 0.10 - C) and new["tr_open_at_end"] == 0
ok += 1
print("✅ F10 同 F9 但有官方下市日 ⇒ 15 日以最後成交價了結（官方日優先於 gap）")

# F11 delist 單獨給、tradable 沒給 ⇒ 必須炸（⛔ 不可靜默忽略）
try:
    run_n(s8, {"A": cl9}, {"A": op9}, N, None, dl)
    raise SystemExit("⛔ delist 沒有 tradable 竟然沒炸")
except ValueError:
    ok += 1
    print("✅ F11 delist 不配 tradable ⇒ ValueError")
print("\n⇒ 含 delist 共 {} 個 fixture 全過".format(ok))

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
    assert not (f["dn_c"] & ~f["trd"]).any(), "沒成交的日子不可有收盤跌停旗標"
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

# ── B2 dn_c：不變式 ＋ 人工照交易所規則複算一天（⛔ 不呼叫 R.limit_price）──
hit = None
for sid in ("2330", "2454", "3008", "2603", "2409", "3481", "2002", "1101"):
    f = T.one(sid, cal)
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str})
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for k in np.flatnonzero(f["dn_c"]):
        d = cal[k]; prev = raw.loc[:d].iloc[-2]
        assert float(raw.loc[d, "close"]) < float(prev["close"]), ("dn_c 但收盤沒跌", sid, d)
    if hit is None and f["dn_c"].any():
        hit = (sid, int(np.flatnonzero(f["dn_c"])[0]), raw)
assert hit is not None, "⛔ 八檔全期一天收盤跌停都沒有 ⇒ B2 沒有鑑別力，換樣本"
sid, k, raw = hit; d = cal[k]; prev = raw.loc[:d].iloc[-2]; today = raw.loc[d]
lim = 0.07 if d < pd.Timestamp("2015-06-01") else 0.10
x = float(prev["close"]) * (1 - lim)
tick = 0.01 if x < 10 else 0.05 if x < 50 else 0.1 if x < 100 else 0.5 if x < 500 else 1.0 if x < 1000 else 5.0
hand = math.ceil(x / tick - 1e-9) * tick           # ⭐ 跌停價向上取到升降單位
assert abs(float(today["close"]) - hand) < 1e-6, (sid, d, prev["close"], today["close"], hand)
print("✅ B2 dn_c：八檔不變式全過（旗標日收盤必低於前收）；人工複算 {} {} 前收 {} ⇒ 跌停 {} ＝ 當日收盤 {}".format(
    sid, d.date(), prev["close"], round(hand, 2), today["close"]))

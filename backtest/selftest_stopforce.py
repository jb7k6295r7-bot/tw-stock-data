# -*- coding: utf-8 -*-
"""research11.simulate_mtm(stop_force=…) 的 fixture（裁定線 seq255 §一 4；回測線 2026-09-27）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/selftest_stopforce.py

小例子：日曆 40 天；A 在第 5 天進場、排程出場第 30 天，第 19 天之後停止交易（收盤 ffill 凍結）；B 正常交易；C 第 25 天停止交易但排程第 22 天就出場。
  ① 開關打開：A 在第 20 天（L＋1）出場、價格 ＝ 第 19 天收盤、入帳 ＝ amt×(1＋gross−COST)（扣成本）、x_stop_force_n ＝ 1；C 照排程第 22 天出場（不強制）
  ② 開關關閉：A 抱到第 30 天、用凍結價出場（原引擎行為）
  ③ 帶 tradable（A 停止交易後 trd＝False）：打開時仍在第 20 天出場（⛔ 不因停牌遞延）；關閉時照原本的停牌遞延
  ④ 共用函式 stop_force_days：A→19、C→25（upto＝39）、B 不在；upto ≤ 19 ⇒ A 不在
  ⑤ 鑑別力：故意把強制出場日寫成 L 或 L＋2、或價格改用第 20 天以後的別的價 ⇒ 檢查會抓到（fixture 內自證）
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import research11 as R

N = 40
def series(rng_px, stop=None, base=10.0):
    c = base * np.cumprod(1 + rng_px.normal(0, 0.01, N)); o = c * (1 + rng_px.normal(0, 0.003, N))
    if stop is not None:
        c[stop + 1:] = np.nan; o[stop + 1:] = np.nan
    return c, o


def run(stop_force, tradable=None, audit=None):
    rp = np.random.default_rng(3)                     # 每次同一組價格 ⇒ 開／關可直接比
    cA, oA = series(rp, 19); cB, oB = series(rp, None, 20.0); cC, oC = series(rp, 25, 30.0)
    raw = {"A": (cA, oA), "B": (cB, oB), "C": (cC, oC)}
    closes = {k: pd.Series(c).ffill().to_numpy() for k, (c, o) in raw.items()}
    opens = {k: o for k, (c, o) in raw.items()}
    rows = [("A", 5, 30), ("B", 5, 30), ("C", 5, 22)]
    sig = pd.DataFrame({"sid": [r[0] for r in rows], "entry_pos": [r[1] for r in rows], "xpos_H": [r[2] for r in rows]})
    sig["g_H"] = [closes[s][x] / (opens[s][e] if np.isfinite(opens[s][e]) else closes[s][e]) - 1 for s, e, x in rows]
    o = R.simulate_mtm(sig, "H", 3, np.random.default_rng(0), closes, opens, N, return_equity=True, audit=audit, tradable=tradable, stop_force=stop_force)
    return o, closes, opens


def check(o, au, closes, opens, want_day, tag):
    errs = []
    sells = [a for a in au if a["side"] == "sell" and a["sid"] == "A"]
    buy = [a for a in au if a["side"] == "buy" and a["sid"] == "A"][0]
    if len(sells) != 1 or sells[0]["t"] != want_day:
        errs.append(f"{tag}：A 出場日 {[a['t'] for a in sells]} ≠ {want_day}")
    else:
        s = sells[0]; ep = buy["px"]
        want_px = closes["A"][19] if want_day == 20 else closes["A"][30]
        if not np.isclose(s["px"], want_px, rtol=0, atol=1e-12):
            errs.append(f"{tag}：A 出場價 {s['px']} ≠ {want_px}")
        if not np.isclose(s["cost"], buy["amt"] * R.COST, rtol=0, atol=1e-15):
            errs.append(f"{tag}：成本 {s['cost']} ≠ {buy['amt'] * R.COST}")
    csell = [a for a in au if a["side"] == "sell" and a["sid"] == "C"]
    if [a["t"] for a in csell] != [22]:
        errs.append(f"{tag}：C 出場日 {[a['t'] for a in csell]} ≠ 22")
    return errs


def main():
    errs = []
    # ① 打開
    au = []; o, cl, op = run({"A": 19, "C": 25}, audit=au); errs += check(o, au, cl, op, 20, "①開")
    if o.get("x_stop_force_n") != 1:
        errs.append(f"①：x_stop_force_n {o.get('x_stop_force_n')} ≠ 1")
    eq_on = o["equity"]
    # ② 關閉
    au = []; o, cl, op = run(None, audit=au); errs += check(o, au, cl, op, 30, "②關")
    if "x_stop_force_n" in o:
        errs.append("②：關閉時不該有 x_stop_force_n")
    if np.array_equal(eq_on, o["equity"]):
        errs.append("②：開與關的權益完全一樣（開關沒作用）")
    # ③ 帶 tradable
    trd = {k: {"trd": np.ones(N, bool), "up_o": np.zeros(N, bool), "dn_o": np.zeros(N, bool), "dn_c": np.zeros(N, bool)} for k in "ABC"}
    trd["A"]["trd"][20:] = False; trd["C"]["trd"][26:] = False
    au = []; o, cl, op = run({"A": 19, "C": 25}, tradable=trd, audit=au); errs += check(o, au, cl, op, 20, "③開＋tradable")
    au = []; o, cl, op = run(None, tradable=trd, audit=au)
    a_sell = [a["t"] for a in au if a["side"] == "sell" and a["sid"] == "A"]
    if a_sell and a_sell[0] == 20:
        errs.append("③關＋tradable：不該在第 20 天出場")
    # ④ 共用函式
    v = {"A": np.r_[np.ones(20, bool), np.zeros(20, bool)], "B": np.ones(40, bool), "C": np.r_[np.ones(26, bool), np.zeros(14, bool)]}
    if R.stop_force_days(v, 39) != {"A": 19, "C": 25}:
        errs.append(f"④：{R.stop_force_days(v, 39)}")
    if "A" in R.stop_force_days(v, 19):
        errs.append("④：upto＝19 時 A 不該在")
    # ⑤ 鑑別力：錯的日子／錯的價 ⇒ check 要抓得到
    au = []; o, cl, op = run({"A": 18, "C": 25}, audit=au)
    if not check(o, au, cl, op, 20, "⑤錯日"):
        errs.append("⑤：強制出場寫成 L（第 19 天）時 check 沒抓到")
    au = []; o, cl, op = run({"A": 19, "C": 25}, audit=au)
    fake = [dict(a) for a in au]
    for a in fake:
        if a["side"] == "sell" and a["sid"] == "A":
            a["px"] = a["px"] * 1.01
    if not check(o, fake, cl, op, 20, "⑤錯價"):
        errs.append("⑤：出場價被改掉時 check 沒抓到")
    print("fixture：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))
    for e in errs:
        print("  ⛔", e)
    return errs


if __name__ == "__main__":
    sys.exit(1 if main() else 0)

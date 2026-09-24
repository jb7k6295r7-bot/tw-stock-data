# -*- coding: utf-8 -*-
"""research11.simulate_mtm 的 stop_line（裁定線 seq119 §四）＋ stop_fractal 的 fixture ①～⑤（PREREGD5 seq2 §二）。

① 停損線逐根與手算相同、第二個擺動低點在 s+2 才生效（stop_fractal.fixtures）
② 收盤跌破 ⇒ 出場價 ＝ 次日開盤（⛔ 不是當日收盤）
③ 3×ATR 代用與獨立手算差 < 1e-10；K 棒不足 ⇒ 無停損（stop_fractal.fixtures）
④ 突變：若把出場改回「當日收盤」⇒ ② 必須抓得到（引擎結果 ＝ 開盤版、≠ 收盤版，且兩版在本資料上不同）
⑤ 突變：擺動低點改成 s+1 就生效 ⇒ ① 的手算必須對不上（前視會被抓到）
＋ 條件一：stop_line 與 stop 同時給 ⇒ ValueError
＋ 開盤跌停 ⇒ 順延到下一個可賣的開盤；排程出場當天不搶
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R
from backtest import stop_fractal as SF

N = 30


def run(stop_line=None, stop=None, dn_o_day=None, level=95.0, xpos=20):
    closes = {"A": np.full(N, 100.0)}; opens = {"A": np.full(N, 100.0)}
    closes["A"][9] = 94.0; opens["A"][10] = 93.0; opens["A"][11] = 92.0; closes["A"][10:] = 92.5
    sig = pd.DataFrame({"sid": ["A"], "entry_pos": [2], "xpos_H120": [xpos], "g_H120": [closes["A"][xpos] / 100.0 - 1]})
    trad = {"A": {"trd": np.ones(N, bool), "up_o": np.zeros(N, bool), "dn_o": np.zeros(N, bool), "dn_c": np.zeros(N, bool)}}
    if dn_o_day is not None:
        trad["A"]["dn_o"][dn_o_day] = True
    sl = {("A", 2): (2, np.full(xpos - 2 + 1, level))} if stop_line == "on" else None
    au = []
    out = R.simulate_mtm(sig, "H120", 1, np.random.default_rng(0), closes, opens, N, return_equity=True,
                         tradable=trad, stop_line=sl, stop=stop, audit=au)
    sell = [a for a in au if a["side"] == "sell"]
    return out, sell


def main():
    SF.fixtures()                                               # ① ③
    # ② 收盤 94 < 95（第 9 根）⇒ 第 10 根開盤 93 出
    out, sell = run(stop_line="on")
    assert len(sell) == 1 and sell[0]["t"] == 10 and abs(sell[0]["px"] - 93.0) < 1e-12, sell
    assert out["sl_exits"] == 1
    # ④ 突變：當日收盤版會是 94（第 9 根），開盤版是 93（第 10 根）⇒ 兩版不同、引擎給的是開盤版
    close_version_px, open_version_px = 94.0, 93.0
    assert close_version_px != open_version_px and sell[0]["px"] == open_version_px and sell[0]["px"] != close_version_px
    # 開盤跌停順延：第 10 根開盤跌停 ⇒ 第 11 根開盤 92 出
    _, sell2 = run(stop_line="on", dn_o_day=10)
    assert len(sell2) == 1 and sell2[0]["t"] == 11 and abs(sell2[0]["px"] - 92.0) < 1e-12, sell2
    # 排程出場當天不搶：排程在第 10 根收盤出 ⇒ 停損不搶，照排程收盤 92.5
    _, sell3 = run(stop_line="on", xpos=10)
    assert len(sell3) == 1 and sell3[0]["t"] == 10 and abs(sell3[0]["px"] - 92.5) < 1e-12, sell3
    # 停損線沒被碰到 ⇒ 照排程
    _, sell4 = run(stop_line="on", level=90.0)
    assert len(sell4) == 1 and sell4[0]["t"] == 20, sell4
    # 條件一：與 stop 同時給 ⇒ 報錯
    try:
        run(stop_line="on", stop=("fix", 0.1)); raise SystemExit("⛔ stop_line 與 stop 同給竟然沒報錯")
    except ValueError:
        pass
    # ⑤ 突變：擺動低點改成 s+1 就生效 ⇒ ① 的手算必須對不上
    l = np.array([10, 9, 8, 9, 10, 11, 10, 9.5, 10, 12, 12, 11.5, 12, 13, 14], float)
    h = l + 1; c = l + 0.5; o = l + 0.3
    want = [8, 8, 8, 8, 9.5, 9.5, 9.5, 9.5, 11.5, 11.5]
    lv_ok, _ = SF.stop_line(o, h, l, c, e=5, x=14)
    lv_bad, _ = SF.stop_line(o, h, l, c, e=5, x=14, lag=1)
    assert np.allclose(lv_ok, want) and not np.allclose(lv_bad, want), (lv_ok, lv_bad)
    print("✅ stop_line fixture：②收盤跌破 ⇒ 次日開盤 93 出｜④開盤版 93 ≠ 收盤版 94，引擎給開盤版｜開盤跌停 ⇒ 順延到次日開盤 92｜"
          "排程當天不搶｜沒碰到 ⇒ 照排程｜與 stop 同給 ⇒ ValueError｜⑤ s+1 生效 ⇒ ① 對不上（{} vs 手算 {}）".format(list(lv_bad), want))


if __name__ == "__main__":
    main()

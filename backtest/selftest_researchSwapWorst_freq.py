# -*- coding: utf-8 -*-
"""researchSwapWorst_freq 最少 fixture 自測（回測線計算子代理，2026-11-11）。⛔ 不讀任何真實報酬；全部是合成資料。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchSwapWorst_freq

S1 觸發：未持有、族群轉強、原版沒買到 ⇒ 觸發；原版買到的族群轉強 ⇒ 「直接買」；已持有的族群轉強 ⇒ 不觸發
S2 池：觸發日收盤持有且第 t 日不出場者；第 t 日出場者 ⇒ 排除；第 t 日剛買的 ⇒ 不在池內
S3 換股數 ＝ min(觸發股, 池)；池 0 ⇒ 0；段統計：月數、比例、近似 A／B
S4 引擎（價格 1、毛 0）營量 1 槽：同日兩檔族群轉強 ⇒ relvol 大者被買、另一檔觸發；買完空槽 0；G3 ＝ 0
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchSwapWorst_freq as SW   # noqa: E402
from backtest import researchGroupRevUp_freq as M   # noqa: E402

FAIL = []


def ok(c, msg):
    print(("OK  " if c else "FAIL") + " " + msg)
    if not c:
        FAIL.append(msg)


def t_trigger():
    # 2 槽；持有 A [1,5)、B [2,10)；第 5 日候選：A（族群、A 在 5 出場 ⇒ 未持有）、B（族群、持有中）、C（族群）、D（非族群）
    # 原版第 5 日買 A（補 A 空出的槽）⇒ C 觸發；池 ＝ {B}（A 第 5 日出場 ⇒ 排除 1）
    sig = pd.DataFrame({"sid": ["A", "B", "C", "D"], "entry_pos": [5, 5, 5, 5], "grp": [1, 1, 1, 0]})
    buys = [(1, "A"), (2, "B"), (5, "A")]
    iv = [("A", 1, 5), ("B", 2, 10), ("A", 5, 30)]
    td = SW.trigger_days(sig, buys, iv, 2)[5]
    ok(td["trig"] == ["C"], f"S1 觸發 ＝ C（{td['trig']}）")
    ok(td["direct"] == ["A"], "S1 直接買 ＝ A（原版行為）")
    ok(td["pool"] == 1 and td["excl"] == 1, f"S2 池 1、排除隔天出場 1（{td['pool']}, {td['excl']}）")
    ok(td["swaps"] == 1 and td["free_after"] == 0, "S3 換股 1、買完空槽 0")
    ok(list(td["pool_rem"]) == [5] and list(td["pool_age"]) == [3], "S2 池距到期 5、已持有 3")
    ok(td["g3_bad"] == 0, "G3 買進數 ＝ min(未持有 3, 空槽 1)")
    # 池 0：1 槽、持有 X [1,5)；第 5 日只買 Y、Z 族群觸發 ⇒ 池 ＝ 0（Y 剛買不在池、X 出場排除）
    sig2 = pd.DataFrame({"sid": ["Y", "Z"], "entry_pos": [5, 5], "grp": [0, 1]})
    td2 = SW.trigger_days(sig2, [(1, "X"), (5, "Y")], [("X", 1, 5), ("Y", 5, 20)], 1)[5]
    ok(td2["trig"] == ["Z"] and td2["pool"] == 0 and td2["swaps"] == 0 and td2["excl"] == 1, "S2/S3 池 0 ⇒ 換 0；剛買的不在池")


def t_seg():
    cal = pd.bdate_range("2020-01-01", periods=60)
    sig = pd.DataFrame({"sid": ["A", "C", "E", "F"], "entry_pos": [0, 3, 30, 30], "grp": [0, 1, 1, 1]})
    buys = [(0, "A")]
    iv = [("A", 0, 50)]
    td = SW.trigger_days(sig, buys, iv, 1)
    s = SW.seg_stats(td, buys, cal, 0, 59, 1, 60)
    ok(s["換股數"] == 2 and s["觸發股數"] == 3 and s["觸發股多於池而未買"] == 1, f"S3 段：換 2、觸發 3、未買 1（{s['換股數']},{s['觸發股數']}）")
    ok(s["有換股的不同月數"] == 2, f"S3 有換股月數 2（{s['有換股月份']}）")
    ok(abs(s["換股÷原版買進"] - 2.0) < 1e-12 and abs(s["買進重疊_近似A上限"] - 1 / 3) < 1e-12, "S3 比例與近似 A")
    ok(s["同日觸發股數分布"] == {"1": 1, "2": 1}, f"S3 同日分布（{s['同日觸發股數分布']}）")


def t_engine():
    # 營量 1 槽 H60：第 1 日兩檔族群轉強，relvol P＞Q ⇒ 買 P、Q 觸發；池 0（P 剛買）⇒ 換 0
    NP = 200
    S = pd.DataFrame({"sid": ["P", "Q", "R"], "k": [0, 0, 70], "pos": [0, 0, 70], "entry_pos": [1, 1, 71], "month": ["x"] * 3,
                      "xpos_H60": [60, 60, 130], "xpos_H120": [120, 120, 190], "relvol": [5.0, 3.0, 1.0], "gated": [True] * 3,
                      "grp": [1, 1, 1]})
    ones = {s: np.ones(NP) for s in "PQR"}
    sig = M.cell_sig(S, "營量", "原版")
    ok(float(sig["g_H60"].abs().sum()) == 0.0, "S4 乾跑毛報酬全 0（make_sig dry 預設）")
    buys, sells = M.run_engine(sig, "營量", "原版", 0, ones, NP, None)
    iv = M.intervals(buys, sells, NP)
    td = SW.trigger_days(sig, buys, iv, 20)
    ok(buys[0] == (1, "P") or (1, "P") in buys, f"S4 引擎買 P（{buys}）")
    # 20 槽 ⇒ P、Q 都買、沒有觸發
    ok(td[1]["trig"] == [] and td[1]["g3_bad"] == 0, "S4 20 槽：兩檔都買、無觸發")
    # 1 槽版本：直接用 research11 同參數但 N＝1
    from backtest import research11 as R
    au = []
    R.simulate_mtm(sig, "H60", 1, np.random.default_rng(0), ones, ones, NP, return_equity=True, log=[], d_max=None, pick="relvol",
                   queue_days=0, stop_force=None, audit=au)
    b1 = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] == "buy"]
    s1 = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] != "buy"]
    td1 = SW.trigger_days(sig, b1, M.intervals(b1, s1, NP), 1)
    ok(b1[0] == (1, "P") and td1[1]["trig"] == ["Q"] and td1[1]["pool"] == 0 and td1[1]["free_after"] == 0, f"S4 1 槽：買 P、Q 觸發、池 0（{b1}）")
    ok(td1[71]["trig"] == [] and td1[71]["excl"] == 0 and td1[71]["g3_bad"] == 0, "S4 第 71 日 P 已在 60 出場 ⇒ R 直接買")


if __name__ == "__main__":
    t_trigger(); t_seg(); t_engine()
    print("全部通過" if not FAIL else f"失敗 {len(FAIL)}：{FAIL}")
    sys.exit(1 if FAIL else 0)

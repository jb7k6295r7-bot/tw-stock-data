"""PREREGC3 §八：兩幣（＋三幣）手算 fixture ＋ 鑑別力 ＋ 餵資料層 ＋ 與 C1 交叉核對 —— 回測線執行端。

⛔ 登錄 v4 §八／裁定線 1802、1814 要求 fixture 涵蓋：
   一次進入、一次離開、現金限制路徑、「部分買入後等待補買」、「補買額被缺口封頂、餘額留現金」
   ＋ 加密策略線 1758：「多幣同時等待平分」
⇒ ⭐ 兩幣做不出「兩幣同時在等」（兩幣都不在場時現金＝淨值，進場一定買滿）
   ⇒ F1 用兩幣（前五條路徑），F2 補一組三幣（平分＋封頂＋餘額隔日才再分）
⭐ 價格與成本都取【二進位可精確表示】的數（單邊成本 1/8、價格 7/8/12/16/4）
   ⇒ 手算答案用分數寫在註解裡，斷言用 repr 逐位元比（⛔ 不用容差）
⭐ 第 ⓪ 格先證明 fixture 分得出來：五個已知錯誤的變體必須各自至少在一組 fixture 上【變紅】
   （〈一百一十三〉；⛔ 一個全綠的 fixture 可能只是空對空）
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C1   # noqa: E402
from backtest import researchc3 as C3   # noqa: E402

FAIL = []


def check(name, got, want):
    got = [float(x) for x in np.atleast_1d(got)]
    want = [float(x) for x in np.atleast_1d(want)]
    ok = repr(got) == repr(want)
    print("{} {}".format("PASS" if ok else "⛔FAIL", name))
    if not ok:
        print("     got ", got); print("     want", want)
        FAIL.append(name)


COST_FIX = 0.25          # 單邊 1/8（fixture 專用；⛔ 正式跑是 0.2% 來回）

# ── F1：兩幣 ─────────────────────────────────────────────────────────────────
#   t0 A,B 進場（淨值 1、|S|=2 ⇒ 各目標 1/2、現金 1 ⇒ 各花 1/2 買滿）       ← 一次進入
#   t1 A 翻倍；B 離場 ⇒ 現金 ＝ 7/16×7/8 ＝ 49/128                            ← 一次離開
#   t2 B 再進場：淨值 161/128、|S|=2 ⇒ 目標 161/256；現金只有 49/128 ＝ 98/256
#       ⇒ 買 98/256（部分買入），缺口 63/256 ⇒ 等待中                          ← 現金限制／部分買入
#   t3 A 離場 ⇒ 現金 ＝ 7/8×7/8 ＝ 49/64 ＝ 196/256；B 缺口 63/256
#       ⇒ 補買 min(196/256, 63/256) ＝ 63/256；餘額 133/256 留現金              ← 等待補買／缺口封頂
#       ⭐ 目標仍是 t2 凍結的 161/256（⛔ 不是今天的淨值／1）
#   t4 B 翻倍
#   nav_pre ＝ [1, 21/16, 161/128, 1239/1024, 1659/1024]
F1_P = np.array([[8, 8], [16, 8], [16, 8], [16, 8], [16, 16]], float)
F1_S = np.array([[1, 1], [1, 0], [1, 1], [0, 1], [0, 1]], float)
F1_NAV = [1.0, 21 / 16, 161 / 128, 1239 / 1024, 1659 / 1024]

# ── F2：三幣 ─────────────────────────────────────────────────────────────────
#   t0 只有 A：目標 1、買滿 ⇒ 顆數 1×7/8÷7 ＝ 1/8；現金 0
#   t1 A 漲到 12 ⇒ 淨值 3/2；B 進場 |S|=2 ⇒ 目標 3/4；現金 0 ⇒ 買 0，等待（缺口 3/4）
#   t2 C 進場 |S|=3 ⇒ 目標 (3/2)/3 ＝ 1/2；現金 0 ⇒ 等待（缺口 1/2）
#   t3 A 離場 ⇒ 現金 ＝ 1/8×12×7/8 ＝ 21/16；等待 B、C ⇒ 平分 21/32
#       B 買 min(21/32, 24/32) ＝ 21/32；C 買 min(21/32, 16/32) ＝ 16/32（⭐ 封頂）
#       餘額 5/32 ⭐ 留現金、⛔ 當天不轉給 B
#   t4 只剩 B 在等（缺口 3/32）⇒ 平分額 5/32 ⇒ 買 3/32（⭐ 又封頂），餘 1/16
#   t5 B 翻倍、C 跌一半
#   nav_pre ＝ [1, 3/2, 3/2, 3/2, 299/256, 51/32]
F2_P = np.array([[7, 8, 8], [12, 8, 8], [12, 8, 8], [12, 8, 8], [12, 8, 8], [12, 16, 4]], float)
F2_S = np.array([[1, 0, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1], [0, 1, 1], [0, 1, 1]], float)
F2_NAV = [1.0, 3 / 2, 3 / 2, 3 / 2, 299 / 256, 51 / 32]


def main():
    # ⓪ 鑑別力：每個錯誤變體至少要在一組 fixture 上給出不同答案
    print("── ⓪ 鑑別力（錯誤變體必須變紅）")
    for v in ("nocap", "v3wait", "retarget", "sameday", "lookahead"):
        d1 = repr(list(C3.simulate(F1_P, F1_S, COST_FIX, variant=v))) != repr(F1_NAV)
        d2 = repr(list(C3.simulate(F2_P, F2_S, COST_FIX, variant=v))) != repr(F2_NAV)
        ok = d1 or d2
        print("{} 變體 {:9s} F1 {} F2 {}".format("PASS" if ok else "⛔FAIL", v,
                                                "分得出" if d1 else "同", "分得出" if d2 else "同"))
        if not ok:
            FAIL.append("鑑別力 " + v)
    if FAIL:
        raise SystemExit("⛔⛔ fixture 沒有鑑別力 ⇒ 停止")

    print("── ① F1 兩幣")
    nav, tr = C3.simulate(F1_P, F1_S, COST_FIX, trace=True)
    check("F1 nav_pre 全路徑", nav, F1_NAV)
    check("F1 t2 B 部分買入：成本基礎 49/128、目標 161/256", [tr[2]["basis"][1], tr[2]["target"][1]],
          [49 / 128, 161 / 256])
    check("F1 t2 現金 0", tr[2]["cash"], 0.0)
    check("F1 t3 補買封頂：成本基礎＝目標＝161/256、現金 133/256",
          [tr[3]["basis"][1], tr[3]["target"][1], tr[3]["cash"]], [161 / 256, 161 / 256, 133 / 256])
    check("F1 t3 A 已清倉（顆數 0、目標 0）", [tr[3]["units"][0], tr[3]["target"][0]], [0.0, 0.0])
    check("F1 t4 無交易（目標凍結 ⇒ 不因淨值變動再買）", tr[4]["cash"], 133 / 256)

    print("── ② F2 三幣")
    nav, tr = C3.simulate(F2_P, F2_S, COST_FIX, trace=True)
    check("F2 nav_pre 全路徑", nav, F2_NAV)
    check("F2 t1 B 等待（現金 0 ⇒ 買 0；目標 3/4）", [tr[1]["basis"][1], tr[1]["target"][1]], [0.0, 3 / 4])
    check("F2 t2 C 目標 1/2（|S|=3 凍結）", tr[2]["target"][2], 0.5)
    check("F2 t3 平分＋C 封頂：B 21/32、C 1/2、現金 5/32",
          [tr[3]["basis"][1], tr[3]["basis"][2], tr[3]["cash"]], [21 / 32, 1 / 2, 5 / 32])
    check("F2 t4 餘額隔日才補給 B：B 3/4、現金 1/16",
          [tr[4]["basis"][1], tr[4]["cash"]], [3 / 4, 1 / 16])
    check("F2 t4 顆數 B 21/256、C 7/128", [tr[4]["units"][1], tr[4]["units"][2]], [21 / 256, 7 / 128])

    print("── ③ 餵資料那一層（load_panel：共同窗首、日期對齊、訊號）")
    with tempfile.TemporaryDirectory() as td:
        # 三幣、起始日錯開；N＝3 ⇒ 各幣第 3 列起有 SMA
        days = pd.date_range("2024-01-01", periods=8).strftime("%Y-%m-%d")
        spec = {"AA": (0, [4, 4, 4, 8, 8, 2, 2, 16]),
                "BB": (1, [8, 8, 8, 4, 16, 16, 16]),
                "CC": (2, [2, 2, 2, 2, 4, 1])}
        for s, (off, px) in spec.items():
            pd.DataFrame({"date": days[off:off + len(px)], "close": px}).to_csv(
                os.path.join(td, s + ".csv"), index=False)
        dates, close, sig, w0s = C3.load_panel(td, coins=("AA", "BB", "CC"), n=3)
        # 手算（日期→收盤）：AA 01-01..08 ＝ 4,4,4,8,8,2,2,16；BB 01-02..08 ＝ 8,8,8,4,16,16,16；
        #                    CC 01-03..08 ＝ 2,2,2,2,4,1
        # SMA3 首日：AA 01-03、BB 01-04、CC 01-05 ⇒ 共同窗首 01-05；窗尾 01-08 ⇒ 4 天
        check("③ 窗首 ＝ 最晚那幣（CC）的 SMA 首日",
              [float(dates[0] == "2024-01-05"), float(dates[-1] == "2024-01-08"), float(len(dates))],
              [1.0, 1.0, 4.0])
        # 01-05：AA 8 > SMA(4,8,8)=20/3 ⇒1；BB 4 > SMA(8,8,4)=20/3 ⇒0；CC 2 > SMA(2,2,2)=2 ⇒0（不大於）
        # 01-06：AA 2 > 6 ⇒0；BB 16 > 28/3 ⇒1；CC 2 > 2 ⇒0
        # 01-07：AA 2 > 4 ⇒0；BB 16 > 12 ⇒1；CC 4 > 8/3 ⇒1
        # 01-08：AA 16 > 20/3 ⇒1；BB 16 > 16 ⇒0；CC 1 > 7/3 ⇒0
        check("③ 訊號逐格（手算）", sig.ravel(), [1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0])
        check("③ 收盤逐格對齊日期", close.ravel(), [8, 4, 2, 2, 16, 2, 2, 16, 4, 16, 16, 1])

    print("── ④ 與 C1 交叉核對（真資料 BTC 單幣、成本 0）")
    d = pd.read_csv(os.path.join(C1.DATA, "BTC.csv"), dtype={"date": str}).drop_duplicates("date")
    c = d.sort_values("date")["close"].to_numpy(float)
    res = C1.rule_series(c, C1.N_MAIN)
    held = np.append(res["held"], res["held"][-1])            # rule_series 的 held 少最後一天
    cw = c[res["w0"]:]
    nav = C3.simulate(cw[:, None], held[:, None], 0.0)
    r3 = C3.rets_from_nav(nav)
    diff = float(np.max(np.abs(np.cumprod(1 + r3) - np.cumprod(1 + res["gross"]))))
    ok = diff < 1e-9
    print("{} ④ 單幣零成本 ⇒ C3 引擎權益與 C1 gross 複利最大差 {:.2e}（< 1e-9；⛔ 不要求逐位元：C3 以顆數記帳）"
          .format("PASS" if ok else "⛔FAIL", diff))
    if not ok:
        FAIL.append("④ C1 交叉核對")

    print("\n⇒ {}".format("✅ 全綠" if not FAIL else "⛔ 紅 {} 格：{}".format(len(FAIL), FAIL)))
    if FAIL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

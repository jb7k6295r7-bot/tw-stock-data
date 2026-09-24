# -*- coding: utf-8 -*-
"""查台股策略線 2111 的措辭：「LD ＝ H120＋跌停提前出；64.4% 其實就是 H120」。

⭐ 方向本線同意，⛔ 但「其實就是 H120」有一個條件 —— 本支把它量出來：

  research11.fixed_exit(k, H=120) ⇒ e ＝ exit_pos(k+1,120) ＝ k+120；⛔ e ≥ len(c) 或 e ≥ nb ⇒ **回 None**
  research11.cond_exit  上限      ⇒ last ＝ **min(n−1, k+CAP)**；⛔ last ≥ nb ⇒ 回 None
  ⇒ ⭐ k+120 ≤ n−1 時，兩者的出場根與出場價【完全相同】（都是 k+120 收盤、同一個進場 o[k+1]）
  ⇒ ⛔ 但 k+120 > n−1 時：LD 退到 n−1 收盤【算得出數】，H120 卻【整筆回 None】
     ⇒ ⚠ 所以「LD vs H120」的比較不是同一個樣本 ⇒ 本支數它差幾筆。
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
G = pd.read_csv("results13/g1_signals.csv.gz", dtype={"sid": str}, float_precision="round_trip")
print("=== ① 交件 results13/g1_signals.csv.gz：{:,} 筆 ===".format(len(G)))

ld = G["g_LD"].notna()
h1 = G["g_H120"].notna()
h6 = G["g_H60"].notna()
print("  g_LD   非 NaN {:,}".format(int(ld.sum())))
print("  g_H120 非 NaN {:,}".format(int(h1.sum())))
print("  g_H60  非 NaN {:,}".format(int(h6.sum())))
print()
print("=== ② ⚠ LD 與 H120 的樣本差 ===")
only_ld = int((ld & ~h1).sum())
only_h1 = int((~ld & h1).sum())
both = int((ld & h1).sum())
print("  兩者都有   {:,} 筆".format(both))
print("  只有 LD 有 **{:,} 筆** ⇒ ⭐ H120 回 None（k+120 超過資料尾／壞根窗），而 LD 退到資料尾算得出".format(only_ld))
print("  只有 H120 有 {:,} 筆".format(only_h1))
print("  ⇒ ⛔ 所以「LD 的 64.4% 其實就是 H120」這句，只在【兩者都有】的 {:,} 筆上成立".format(both))

print()
print("=== ③ ⭐ 在兩者都有、且 LD 沒被跌停觸發（t_LD False）的筆上，兩者應該【逐位元相同】 ===")
m = ld & h1 & (~G["t_LD"].astype(bool))
sub = G[m]
print("  這樣的筆數 {:,}".format(len(sub)))
d = (sub["g_LD"].to_numpy(float) - sub["g_H120"].to_numpy(float))
print("  g_LD − g_H120 的最大絕對差 {:.3e}".format(np.abs(d).max() if len(d) else float("nan")))
same_pos = int((sub["xpos_LD"].to_numpy() == sub["xpos_H120"].to_numpy()).sum())
print("  出場日曆位置相同的筆數 {:,}／{:,}".format(same_pos, len(sub)))
n_diff = int((np.abs(d) > 0).sum())
print("  報酬有差的筆數 {:,}".format(n_diff))
if n_diff:
    bad = sub[np.abs(d) > 0][["sid", "g1_pos", "k", "xpos_LD", "xpos_H120", "g_LD", "g_H120"]]
    print("  ⇒ ⚠ 逐筆（前 10）：")
    print(bad.head(10).to_string(index=False))
    print("  ⇒ ⭐ 它們就是【被資料尾截短】的那一批：LD 退到 n−1，H120 也還在 ⇒ 兩者出場根不同")

print()
print("=== ④ ⭐ 結論（給台股策略線 2111 的措辭補一個條件）===")
print("  ✅ 「LD ＝ H120 ＋ 跌停提前出（觸發率 35.6%）」方向正確")
print("  ⚠ 但要補：⛔ 不是所有未觸發的筆都等於 H120 ——")
print("     ・{:,} 筆只有 LD 有值（H120 回 None）".format(only_ld))
print("     ・未觸發且兩者都有值的 {:,} 筆裡，還有 {:,} 筆出場根不同（資料尾截短）".format(len(sub), n_diff))
print("  ⇒ ⭐ 建議字面：「H120 ＋ 當根跌停提前出（觸發率 35.6%）；")
print("     ⛔ 而未觸發的筆也不全等於 H120：{} 筆 H120 根本算不出來、另 {} 筆因資料尾截短而出場根不同」"
      .format(only_ld, n_diff))
print("  ⏳ 措辭歸裁定線／台股策略線，⛔ 本線只報這兩個數")

#  ⛔ 本支第一版斷言「只有 LD 有值的筆必須全部貼在資料尾」⇒ 斷言當場擋下來（只有 362／703）
#  ⭐ 因為漏了一整類：跌停【提前】觸發 ⇒ LD 早就出場了，而 H120 的 k+120 仍落在資料尾之外／壞根窗
if only_ld:
    o = G[ld & ~h1]
    mx = int(G["xpos_LD"].max())
    trig = o["t_LD"].astype(bool)
    print()
    print("=== ⑤ ⭐ 那 {} 筆「只有 LD 有值」要拆兩類（⛔ 不是全部貼在資料尾）===".format(only_ld))
    print("  (甲) 跌停【提前】觸發 ⇒ LD 早就出了，而 H120 的 k+120 還在資料尾之外／壞根窗")
    print("       ⇒ **{:,} 筆**".format(int(trig.sum())))
    print("  (乙) 沒觸發 ⇒ LD 退到資料尾 {} 收盤，而 H120 整筆回 None".format(mx))
    print("       ⇒ **{:,} 筆**".format(int((~trig).sum())))
    assert int(trig.sum()) + int((~trig).sum()) == only_ld
    #  ⛔ 本支第二版斷言「(乙) 全部貼在全域資料尾 2849」⇒ 又被擋下來（362／365，另 3 筆在 2847／2842）
    #  ⭐ 原因：cond_exit 的 n ＝ len(c) 是【那一檔自己】的有效 K 棒數 ⇒ n−1 是【該檔自己的資料尾】
    #     ⇒ 已下市／長期停牌的檔，自己的尾比全域日曆尾早 ⇒ ⛔ 不可用單一個數字去斷言
    #  ⇒ 改成斷言它的【定義性質】：截短 ⇒ 出場必早於 k+120，且沒有被跌停觸發
    yb = o[~trig]
    assert (yb["xpos_LD"].to_numpy() < (yb["pos"].to_numpy() + 120)).all(), \
        "⛔ (乙) 類有出場不早於 k+120 的 ⇒ 那就不是截短"
    at_global = int((yb["xpos_LD"] == mx).sum())
    print("  ⇒ ✅ (乙) 那 {:,} 筆的出場【全部】早於 k+120（＝定義上的截短）".format(len(yb)))
    print("     其中貼在【全域】日曆尾 {} 的 {:,} 筆；另 {:,} 筆貼在【該檔自己的】資料尾".format(
        mx, at_global, len(yb) - at_global))
    odd = yb[yb["xpos_LD"] != mx][["sid", "g1_pos", "pos", "xpos_LD"]]
    if len(odd):
        print("     ⇒ ⭐ 那幾筆逐筆（已下市／長期停牌 ⇒ 自己的尾比日曆尾早）：")
        print(odd.to_string(index=False))
    #  ⭐ (甲) 這一類的出場【必須】早於 k+120
    ja = o[trig]
    assert (ja["xpos_LD"].to_numpy() < (ja["pos"].to_numpy() + 120)).all(), \
        "⛔ (甲) 類有出場不早於 k+120 的"
    print("  ⇒ ✅ (甲) 那 {:,} 筆的出場【全部】早於 k+120".format(len(ja)))
    print()
    print("  ⭐⭐ 所以正確的說法是：LD 比 H120 多算了 {:,} 筆，而那 {:,} 筆分兩種原因，".format(
        only_ld, only_ld))
    print("     ⛔ 只講「資料尾」會漏掉 {:,} 筆真的提前觸發的。".format(int(trig.sum())))

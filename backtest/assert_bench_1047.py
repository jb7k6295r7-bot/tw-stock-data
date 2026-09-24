# -*- coding: utf-8 -*-
"""自測：裁定線 20260924-1047 §一 給的兩組 0050 基準數，本線逐位重算。

⭐ 本線的角色邊界是「裁下來【逐字照抄】**並做成自測斷言**」
   ⇒ ⛔ 只把數字抄進報告【不算做完】——抄錯或對方筆誤都不會有人發現。

驗兩件：
  ① 浮動窗尾（P9ⓑ／P7 用的）：窗 [523, 2855) ＝ 2017-03-02 ~ 2026-09-18
     ⇒ 裁定線 1047 §一 寫的 **+24.5419%**
  ② 釘死窗（P12~P17 用的，裁 (甲)）：窗 [523, 2835] ＝ 2017-03-02 ~ 2026-08-24
     ⇒ 裁定線 1047 §一 寫的 **0.24020209886370614 / 0.3395700527611012**（未捨入）

⚠ ⛔ 本支【不】重新判定任何一件（裁定線 1047：「要重判必須重跑」）——只驗基準數。
"""
from __future__ import annotations
import os, sys
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research13 as R13

cal = D.load_calendar()
bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)

LO = 523                                   # ⭐ 2017-03-02，P7／P9／P12~P17 共同窗頭
FLOAT_HI = len(cal)                         # 浮動窗尾（researchp9：end_all = ncal）
PIN_HI = 2835 + 1                           # 釘死窗 [523, 2835]（裁 (甲)）

c_f, m_f = R13.window_stats(bench, LO, FLOAT_HI, LO, FLOAT_HI)
c_p, m_p = R13.window_stats(bench, LO, PIN_HI,   LO, PIN_HI)

print("① 浮動窗尾 [{}, {})  {} ~ {}".format(LO, FLOAT_HI, cal[LO].date(), cal[FLOAT_HI - 1].date()))
print("     年化 {!r} ＝ {:+.4f}%   回落 {!r}".format(c_f, c_f * 100, m_f))
print("② 釘死窗   [{}, {})  {} ~ {}".format(LO, PIN_HI, cal[LO].date(), cal[PIN_HI - 1].date()))
print("     年化 {!r} ＝ {:+.4f}%   回落 {!r}".format(c_p, c_p * 100, m_p))
print()

# ⛔ 斷言一：浮動窗尾年化 ＝ 裁定線 1047 的 +24.5419%（四位）
assert abs(c_f * 100 - 24.5419) < 5e-5, "① 年化不符 1047：{:+.6f}%".format(c_f * 100)
# ⛔ 斷言二：釘死窗兩個未捨入值【逐位元】相同
assert repr(c_p) in ("0.24020209886370614", "np.float64(0.24020209886370614)"), \
    "② 年化未捨入值不符 1047：{!r}".format(c_p)
assert abs(abs(m_p) - 0.3395700527611012) < 1e-15, "② 回落不符 1047：{!r}".format(m_p)
print("⭐ 斷言一、二皆過 ⇒ 裁定線 1047 §一 的四個數字本線逐位重算相符。")

# ⭐ 斷言三：本線自己發現的那件 —— 兩個窗的【回落相同】、⛔ 而年化不同
assert abs(abs(m_f) - abs(m_p)) < 1e-15, \
    "③ 兩窗回落竟然不同 ⇒ ⚠ 表示 2026-08-24 之後出現了更深的回落，報告註記要改"
assert abs(c_f - c_p) > 1e-4, "③ 兩窗年化竟然相同 ⇒ ⚠ 那 (甲)(乙) 之爭就沒有量上的差別"
print("⭐ 斷言三 過 ⇒ **回落兩窗逐位相同、年化相差 {:+.4f}pp**".format((c_f - c_p) * 100))
print("   ⇒ ⭐ 所以「不可逐格比」實質只對【年化】成立（成因：最大回落發生在 2026-08-24 之前）")
print("   ⇒ ⛔ 但本線不因此放寬裁定線那一句 —— 它是裁定，本線照掛。")

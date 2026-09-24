# -*- coding: utf-8 -*-
"""組態計數 N：本線側的歷史盤點（⇐ 裁定線 1716 §一；台股策略線 N 盤點 seq=6 的 ⏳ 欄）。

⭐ 本線只報【事實】：每件實際跑了幾個臂／格、各自的年化與回落、有沒有被拿去比使用者判準。
⛔ 本線不裁「算不算一格」（那是裁定線的格子）⇒ 逐件把兩個數都報：
   ・跑過的臂數（程式實際產出的格）
   ・被拿去比使用者判準的臂數（⭐ 報告裡有「通過／未過」判定的那些）
⛔ 單筆層與純描述件另列，不混進組合層。
"""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17/backtest"))

rows = []
def add(件, 檔, 跑過, 比判準, 窗, 結果, 註=""):
    rows.append(dict(件=件, 格表=檔, 跑過的臂=跑過, 比過判準=比判準, 窗=窗, 結果=結果, 註=註))

add("P7 停損四族", "resultsp7/cells.csv", 6, 6, "全窗+A+B",
    "0/6 通過（含 stop=none 基準）", "N=8 固定；5 種停損＋無停損")
add("P9ⓑ 弱勢減碼", "resultsp9/cells.csv", 2, 2, "全窗",
    "0/2（win_self、win_sl 皆 False）", "base 與 b 兩臂")
add("P11 訊號集×選擇率", "resultsp11/cells.csv", 16, 16, "全窗",
    "0/16", "sigset(B,C)×mode(var,fix)×rate(4) ＝ 2×2×4")
add("P12 相對落後歸屬", "resultsp12/cells.csv", 48, 0, "主格窗+全窗",
    "⛔ 歸屬診斷，未比判準", "S×C×T×窗×成本 ＝ 48；⭐ 它是拆解，⛔ 不是候選策略")
add("P13 只換權重", "resultsp13/arms.csv", 8, 2, "全窗+主格窗",
    "0/2（W0、W1 全窗）", "4 臂×2 窗 ＝ 8 列；W0p／W0i 是對帳臂")
add("P14 0050 進組合", "resultsp14/w_summary.csv", 5, 5, "全窗",
    "**2/5 通過**（w=0.00、0.25）", "⚠ w=0 就是 0050 本身 ⇒ ⭐ 通過的那兩格含退化解")
add("P15 候選檔數閘門", "resultsp15/summary.csv", 4, 2, "全窗",
    "0/2（G0、G1）", "另二臂：假訊號閘門、排除四月 ⇒ 對照")
add("P16 條件出場", "resultsp16/summary.csv", 6, 5, "全窗",
    "0/5（E0/E1/E1a/E1b/E1c）", "R1 是對照臂")
add("P17 外生算式決定 w", "resultsp17/per_seed_arm.csv", 7, 1, "釘死窗",
    "判定格 R_eq 兩腳過、(i) 落出口③ ⇒ 判【沒有新資訊】",
    "⭐ **七**臂（P17_REPORT §一 逐字「七個臂」）中只有 R_eq 是判定格；W_fix/W_shuf/R_tv/R_rp/W0/W1 只作描述（§九②）。⚠ 本線 2026 §一 誤寫成 6 ⇒ 已訂正；⇒ 合計 205→206、差 68→69。⚠⚠ n_exc69.py 查出 W_fix 與 W_shuf 的中位【通過使用者判準】（〈一百三十四〉必報）")
add("研究十三／PREREG10", "results13/portfolio.csv", 48, 48, "全窗+A+B",
    "0/48", "set×regime×N×rule")
add("研究十三b／PREREG11", "results13b/portfolio.csv", 48, 48, "全窗+A+B",
    "**2/48**（N30 H60、N40 H60）", "⚠ 裁定線 1813 §三：那兩格是【全窗】⇒ 仍缺 A／B 兩腳")
add("D4 放寬三閘門", "results_d4/cells.csv", 8, 2, "釘死窗",
    "0/2（S1′ 主欄、附欄）", "4 臂×2 欄；⭐ S1′ 兩腳都沒過 0050（裁定線 2002）")

df = pd.DataFrame(rows)
os.makedirs("results_step2", exist_ok=True)
df.to_csv("results_step2/n_tally_backtest.csv", index=False, encoding="utf-8")
print("=== ⭐ 組合層：本線實際跑過的臂 vs 被拿去比判準的臂 ===")
print(df.to_string(index=False))
print()
print("跑過的臂合計 **{}**｜被拿去比判準合計 **{}**".format(df["跑過的臂"].sum(), df["比過判準"].sum()))
print()
print("=== ⛔ 另列（⛔ 不進組合層 N）===")
print("  單筆層：四型 P4v3／P8 2-A／P1b／T2P6／研究十九 PREREG19")
print("  純描述：P12（歸屬診斷 48 格）、D4 的對帳欄、I（回落拆解，尚未跑）")
print("  非台股：PREREGC1~C4（加密）、PREREGM1（美股）⇒ 另建分母")
print()
print("⇒ 落檔 backtest/results_step2/n_tally_backtest.csv")

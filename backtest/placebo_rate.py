# -*- coding: utf-8 -*-
"""裁定線 seq84 §三③：組合層判定必附【同窗假訊號臂逐 rep 判過比例】。

本支做兩件：
  ① 盤點本線 12 件組合層 ⇒ 哪幾件真的有【假訊號臂】（＝有自己的年化／回落，可以拿去比判準的臂）
  ② 有的逐 rep 算判過比例；⛔ 沒有的明文標「無假訊號臂」（依 seq84 §三③，引用它的「過」必須標）

判準（seq84 §二 統一版）：兩腳 ≥ 0050，且【至少一腳嚴格優】
⛔ 基準不抄數字 —— 用 assert_bench_1047.py 的同一串呼叫當場重算，並保留它的斷言。
"""
from __future__ import annotations
import os, sys
import pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research13 as R13

cal = D.load_calendar()
bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
LO, FLOAT_HI, PIN_HI = 523, len(cal), 2835 + 1
c_f, m_f = R13.window_stats(bench, LO, FLOAT_HI, LO, FLOAT_HI)
c_p, m_p = R13.window_stats(bench, LO, PIN_HI, LO, PIN_HI)
m_f, m_p = abs(m_f), abs(m_p)
print("=== ① 基準（當場重算，⛔ 不抄）===")
print("  全窗（浮動窗尾）年化 {!r}／回落 {!r}".format(c_f, m_f))
print("  釘死窗          年化 {!r}／回落 {!r}".format(c_p, m_p))
assert abs(c_f * 100 - 24.5419) < 5e-5, "⛔ 全窗年化不符 1047"
assert repr(c_p) in ("0.24020209886370614", "np.float64(0.24020209886370614)"), "⛔ 釘死窗年化不符 1047"
assert abs(m_p - 0.3395700527611012) < 1e-15, "⛔ 釘死窗回落不符 1047"
print("  ✅ 1047 的三條斷言仍成立")


def passes(c, m, bc, bm):
    return bool(c >= bc and m <= bm and (c > bc or m < bm))


print()
print("=== ② 12 件組合層：有沒有【可比判準的假訊號臂】 ===")
INV = [
    ("P7 停損四族",      "resultsp7",   None, "全窗"),
    ("P9ⓑ 弱勢減碼",     "resultsp9",   None, "全窗"),
    ("P11 訊號集×選擇率", "resultsp11",  None, "全窗"),
    ("P12 相對落後歸屬",  "resultsp12",  None, "釘死窗"),
    ("P13 只換權重",     "resultsp13",  None, "全窗"),
    ("P14 0050 進組合",  "resultsp14",  None, "全窗"),
    ("P15 候選檔數閘門",  "resultsp15",  "placebo_by_seed.csv", "全窗"),
    ("P16 條件出場",     "resultsp16",  "placebo.csv", "全窗"),
    ("P17 外生算式",     "resultsp17",  "per_seed_arm.csv", "釘死窗"),
    ("研究十三",         "results13",   None, "全窗"),
    ("研究十三b",        "results13b",  None, "全窗"),
    ("D4 放寬三閘門",     "results_d4",  None, "釘死窗"),
]
rows = []
for name, d, f, win in INV:
    bc, bm = (c_p, m_p) if win == "釘死窗" else (c_f, m_f)
    if f is None:
        rows.append(dict(件=name, 窗=win, 假訊號臂="⛔ 無", rep數="—", 逐rep判過="—",
                         註="⇒ 依 seq84 §三③，引用本件的「過」必須標【無假訊號臂】"))
        continue
    p = os.path.join("backtest", d, f)
    df = pd.read_csv(p, float_precision="round_trip")
    if not {"cagr", "mdd"} <= set(df.columns):
        rows.append(dict(件=name, 窗=win, 假訊號臂="⛔ 無（{} 不是績效臂）".format(f),
                         rep數="—", 逐rep判過="—",
                         註="⭐ 該檔是【共同區間／決定性】檢查（欄：{}），⛔ 沒有自己的年化／回落"
                            .format("／".join(list(df.columns)[:4]))))
        continue
    if "arm" in df.columns:
        df = df[df["arm"].isin(["PLACEBO", "W_shuf"])]
    per = df.groupby("rep").agg(c=("cagr", "median"), m=("mdd", "median"))
    per["m"] = per["m"].abs()
    per["判過"] = [passes(a, b, bc, bm) for a, b in zip(per["c"], per["m"])]
    k = int(per["判過"].sum())
    pooled = passes(df["cagr"].median(), abs(df["mdd"].median()), bc, bm)
    rows.append(dict(件=name, 窗=win, 假訊號臂="✅ 有（{}）".format(f),
                     rep數=len(per), 逐rep判過="**{}／{}**".format(k, len(per)),
                     註="池化中位判過＝{}｜年化中位 {:.4f}／回落中位 {:.4f}".format(
                         pooled, df["cagr"].median(), abs(df["mdd"].median()))))
    per.to_csv("backtest/results_step2/placebo_rate_{}.csv".format(d), encoding="utf-8")

t = pd.DataFrame(rows)
print(t.to_string(index=False))

print()
print("=== ③ ⭐ 一句話 ===")
have = t[t["假訊號臂"].str.startswith("✅")]
print("  12 件組合層裡，只有 **{}** 件有可比判準的假訊號臂：{}".format(
    len(have), "、".join(have["件"])))
print("  ⇒ ⛔ 其餘 {} 件【無假訊號臂】⇒ 引用它們的「過」都要標".format(len(t) - len(have)))

# ⛔ 自測
assert len(have) == 2, "⛔ 有假訊號臂的件數變了：{}".format(list(have["件"]))
_p17 = t.set_index("件").loc["P17 外生算式", "逐rep判過"]
assert _p17 == "**30／30**", "⛔ P17 的 30/30 對不上前一封：{}".format(_p17)
print("  ✅ 兩條斷言通過（恰 2 件有假訊號臂｜P17 仍是 30／30）")

os.makedirs("backtest/results_step2", exist_ok=True)
t.to_csv("backtest/results_step2/placebo_inventory.csv", index=False, encoding="utf-8")
print("⇒ 落檔 backtest/results_step2/placebo_inventory.csv ＋ placebo_rate_*.csv")

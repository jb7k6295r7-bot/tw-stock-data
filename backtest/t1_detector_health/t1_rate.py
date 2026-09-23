"""T1 第③步：觸發率（次／檔／年），分【市值前 50】／【其餘】兩格報。

〈九十二〉：觸發率一定要連同【母體】一起報 ⇒ 本表每一格都把分子與分母都印出來。
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-stock-data"))
from backtest import data as D                    # noqa: E402
from backtest.run import SIG_START, SIG_END       # noqa: E402

T1 = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/scratchpad/t1"

cal = D.load_calendar()
win = cal[(cal >= pd.Timestamp(SIG_START)) & (cal <= pd.Timestamp(SIG_END))]
n_days = len(win)
n_years = (win[-1] - win[0]).days / 365.25
DPY = n_days / n_years
print("═══ 〇 視窗與換算 ═══")
print("  訊號視窗 {} ~ {}".format(win[0].date(), win[-1].date()))
print("  交易日 {:,} 日 ／ {:.2f} 年  ⇒ 一年 {:.1f} 個交易日".format(n_days, n_years, DPY))

exp = pd.read_csv(f"{T1}/exposure.csv", dtype={"stock_id": str})
cap = pd.read_csv(f"{T1}/mktcap.csv", dtype={"stock_id": str})
sig = pd.read_csv(os.path.expanduser("~/tw-stock-data/backtest/results/signals.csv.gz"),
                  dtype={"stock_id": str})
sig["ym"] = sig["signal_date"].str.slice(0, 7)

e = exp.merge(cap[["stock_id", "ym", "top50", "rank"]], on=["stock_id", "ym"], how="left")
print()
print("═══ 〇之二 併表檢查 ═══")
print("  曝險 {:,} 檔-月，其中對不到市值的 {:,} 列（{:.2%}）".format(
    len(e), int(e["top50"].isna().sum()), e["top50"].isna().mean()))
e["tier"] = e["top50"].map({True: "市值前50", False: "其餘"})
e["tier"] = e["tier"].fillna("⚠對不到市值")

s = sig.merge(cap[["stock_id", "ym", "top50"]], on=["stock_id", "ym"], how="left")
s["tier"] = s["top50"].map({True: "市值前50", False: "其餘"}).fillna("⚠對不到市值")
print("  訊號 {:,} 筆，其中對不到市值的 {:,} 筆（{:.2%}）".format(
    len(s), int(s["top50"].isna().sum()), s["top50"].isna().mean()))

# ── 母體（分母）──
den = e.groupby("tier")["gate_days"].sum().rename("gate_days").to_frame()
den["檔年"] = den["gate_days"] / DPY
den["相異檔數"] = e.groupby("tier")["stock_id"].nunique()
print()
print("═══ 一 ⭐ 母體（分母）——〈九十二〉要求連同這一份一起讀 ═══")
print("  " + den.assign(**{"gate_days": den["gate_days"].map("{:,.0f}".format),
                           "檔年": den["檔年"].map("{:,.1f}".format)}
                        ).to_string().replace("\n", "\n  "))

# ── 觸發率 ──
num = s.groupby(["pattern", "tier"]).size().rename("訊號數").reset_index()
tab = num.pivot(index="pattern", columns="tier", values="訊號數").fillna(0)
order = [c for c in ["市值前50", "其餘", "⚠對不到市值"] if c in tab.columns]
tab = tab[order]

print()
print("═══ 二 ⭐⭐ 觸發率（次／檔／年）＝ 訊號數 ÷ 檔年 ═══")
print()
hdr = "  {:<24}".format("型態")
for c in order:
    hdr += "{:>26}".format(c)
hdr += "{:>12}".format("前50 ÷ 其餘")
print(hdr)
print("  " + "─" * (24 + 26 * len(order) + 12))
for pat in tab.index:
    line = "  {:<24}".format(pat)
    rates = {}
    for c in order:
        n = tab.loc[pat, c]
        y = den.loc[c, "檔年"] if c in den.index else float("nan")
        r = n / y if y and y == y else float("nan")
        rates[c] = r
        line += "{:>26}".format("{:>6,.0f} 筆 → {:.4f}".format(n, r))
    if "市值前50" in rates and "其餘" in rates and rates["其餘"]:
        line += "{:>12}".format("{:.2f}x".format(rates["市值前50"] / rates["其餘"]))
    print(line)

tot = tab.sum()
line = "  {:<24}".format("【合計】")
for c in order:
    y = den.loc[c, "檔年"] if c in den.index else float("nan")
    line += "{:>26}".format("{:>6,.0f} 筆 → {:.4f}".format(tot[c], tot[c] / y))
r50 = tot.get("市值前50", 0) / den.loc["市值前50", "檔年"]
rot = tot.get("其餘", 0) / den.loc["其餘", "檔年"]
line += "{:>12}".format("{:.2f}x".format(r50 / rot))
print("  " + "─" * (24 + 26 * len(order) + 12))
print(line)

tab.to_csv(f"{T1}/trigger_counts.csv")
den.to_csv(f"{T1}/denominator.csv")
print()
print("✅ 已寫出 trigger_counts.csv／denominator.csv")

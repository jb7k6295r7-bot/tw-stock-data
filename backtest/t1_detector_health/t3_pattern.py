"""補件 §二 的 T3：【型態訊號候選池】裡市值前 50 佔幾成。

⭐ 為了與 top50_share.py 的 B／C 可比，單位一律換成【股-月】，⛔ 不用訊號筆數：
     門檻B  276 / 2,882 股-月 ＝ 9.6%
     參考C  538 / 5,799 股-月 ＝ 9.3%
⭐ 窗也對齊：2017-03 ~ 2026-03（⛔ 與 P11 判定窗、與 B／C 同一個窗）
⭐ 市值與前 50：直接取正典 researchp13.load_mktcap 的原始碼，⛔ 不維護第二份（四點五）
⚠ 分級日：用【該股該月第一筆型態訊號的訊號日】。
   （B／C 用的是量測日 ＝ entry_pos−1；型態訊號沒有月量測日這個東西。
     ⭐ 已實測月內前 50 名單 Jaccard 中位 0.961 ⇒ 這個選擇的影響量級遠小於結論差距，
     ⛔ 但仍然是一個口徑差，本檔照實寫出來。）
"""
from __future__ import annotations

import ast
import glob
import os
import sys
import types

import numpy as np
import pandas as pd

TREE = os.path.expanduser("~/tw-stock-data")
P16 = os.path.expanduser("~/tw-p16")
sys.path.insert(0, TREE)
os.chdir(TREE)
from backtest import data as D   # noqa: E402

_src = open(os.path.join(P16, "backtest", "researchp13.py"), encoding="utf-8").read()
_lines = _src.splitlines(keepends=True)
_take, _topn = [], None
for node in ast.parse(_src).body:
    if isinstance(node, ast.FunctionDef) and node.name == "load_mktcap":
        _take.append("".join(_lines[node.lineno - 1:node.end_lineno]))
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TOP_N" for t in node.targets):
        _topn = "".join(_lines[node.lineno - 1:node.end_lineno])
assert _take and _topn
_ns = {"np": np, "pd": pd, "os": os, "D": D}
exec(_topn + "\n" + _take[0], _ns)   # noqa: S102
load_mktcap, TOP_N = _ns["load_mktcap"], _ns["TOP_N"]
print("✅ 取自正典 researchp13.py：load_mktcap、TOP_N = {}".format(TOP_N))

WIN = ("2017-03", "2026-03")
cal = D.load_calendar()
all_sids = sorted(b for b in (os.path.basename(p)[:-4]
                              for p in glob.glob(os.path.join(TREE, "data/stocks", "*.csv")))
                  if not b.startswith("_"))
caps = load_mktcap(all_sids, cal)
idx_of = {s: i for i, s in enumerate(all_sids)}
M = np.full((len(all_sids), len(cal)), np.nan)
for s, a in caps.items():
    M[idx_of[s]] = a
top_flag = np.zeros_like(M, bool)
for t in range(len(cal)):
    col = M[:, t]
    ok = np.flatnonzero(np.isfinite(col))
    if len(ok):
        top_flag[ok[np.argsort(-col[ok], kind="stable")][:TOP_N], t] = True

sig = pd.read_csv(os.path.join(TREE, "backtest/results/signals.csv.gz"), dtype={"stock_id": str})
sig["ym"] = sig["signal_date"].str.slice(0, 7)
pos_of = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}
sig["pos"] = sig["signal_date"].map(pos_of)
sig = sig[sig["pos"].notna() & sig["stock_id"].isin(idx_of)].copy()
sig["pos"] = sig["pos"].astype(int)

full = sig.copy()
sig = sig[(sig["ym"] >= WIN[0]) & (sig["ym"] <= WIN[1])].copy()

print()
print("=== 〇 窗對齊 ===")
print("  型態訊號全部            {:,} 筆（{} ~ {}）".format(
    len(full), full["ym"].min(), full["ym"].max()))
print("  對齊到 B/C 的窗之後      {:,} 筆（{} ~ {}）".format(
    len(sig), sig["ym"].min(), sig["ym"].max()))


def share(d, label):
    """股-月單位：每檔每月算一格，用該月第一筆訊號日判前 50。"""
    first = d.sort_values("pos").groupby(["stock_id", "ym"], as_index=False).first()
    hit = top_flag[first["stock_id"].map(idx_of).to_numpy(int), first["pos"].to_numpy(int)]
    n, k = len(first), int(hit.sum())
    by = (pd.DataFrame({"ym": first["ym"], "hit": hit})
          .groupby("ym")["hit"].agg(["sum", "count"]))
    by["p"] = by["sum"] / by["count"]
    print()
    print("=== {} ===".format(label))
    print("  ① 全窗合計：{:,} / {:,} ＝ {:.1%}   （{} 個月）".format(k, n, k / n, by.shape[0]))
    print("  ② 逐月比例：中位 {:.1%}／p10 {:.1%}／p90 {:.1%}".format(
        by["p"].median(), by["p"].quantile(0.10), by["p"].quantile(0.90)))
    print("     ⚠ 逐月分子為 0 的月份 {} / {} ＝ {:.1%}（〈九十二〉：中位要跟這個一起讀）".format(
        int((by["sum"] == 0).sum()), len(by), (by["sum"] == 0).mean()))
    return k, n, by


k, n, by = share(sig, "一 ⭐⭐ 型態訊號候選池（股-月，窗對齊 2017-03~2026-03）")
share(full, "二 參考：不對齊窗（2016-01~2026-07 全部型態訊號）")

print()
print("=== 三 ⭐⭐ 三者並列（同單位【股-月】、同窗、同市值口徑）===")
print()
print("  {:<14}{:>14}{:>10}".format("候選池", "前50 / 總數", "比例"))
print("  " + "-" * 40)
print("  {:<14}{:>14}{:>10}".format("門檻B", "276 / 2,882", "9.6%"))
print("  {:<14}{:>14}{:>10}".format("參考C", "538 / 5,799", "9.3%"))
print("  {:<14}{:>14}{:>10}".format("型態訊號", "{:,} / {:,}".format(k, n), "{:.1%}".format(k / n)))
print()
print("  ⇒ ⭐ 型態訊號候選池碰到市值前 50 的比例，是 B／C 的 {:.2f} 倍".format((k / n) / 0.096))
print("  ⛔ 本行是【描述】：沒有檢定、沒有判定 ⇒ ⛔ 不可寫「測得出／測不出」（〈九十八〉）")

by.to_csv(("/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/"
           "C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/"
           "scratchpad/t1/t3_bymonth.csv"))
print()
print("✅ 已寫出 t3_bymonth.csv")

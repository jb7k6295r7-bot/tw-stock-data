"""T1 訂正版：級距改成【逐日】判定，並改用正典的市值實作。

⛔ 本線第一版的兩個問題（自查出來的）：
  ① 市值與「前 50」早就有一份實作：backtest/researchp13.py 的 load_mktcap／top50_by_month
     （由 backtest/top50_share.py 使用）。本線搜錯了樹又寫一份 ⇒ 四點五。
     ⇒ 本檔改【直接 import 正典那支】，⛔ 不再用本線自己那份。
  ② 第一版用「月底」當量測日。實測前 50 名單在月內會動 1～3 檔（Jaccard 中位 0.961）
     ⇒ ⭐ 而 T1 的曝險本來就是【逐日】的，根本不需要「量測日」這個選擇
     ⇒ 本檔改成【每一個交易日各自判前 50】，⛔ 把那個選擇整個拿掉。

⚠ 資料樹：訊號檔與曝險都出自 ~/tw-stock-data ⇒ 市值也一律從【同一棵樹】讀，
   ⛔ 不可混用 tw-p16 worktree 的 data/（那是 09-18 的舊版）。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

TREE = os.path.expanduser("~/tw-stock-data")
P16 = os.path.expanduser("~/tw-p16")
sys.path.insert(0, TREE)          # ⭐ 先放主樹 ⇒ backtest.data 指向主樹的 data/
os.chdir(TREE)

from backtest import data as D                 # noqa: E402
from backtest.run import SIG_START, SIG_END    # noqa: E402

# ⭐ 正典的市值實作在 p16 樹的 researchp13.py。
#   ⚠ 整個 module import 不進來（它連帶 import researchp7，那支只在 p16 樹）
#   ⇒ ⭐ 改成把【那兩個函式的原始碼原封不動取出來執行】：
#      保證與正典逐字同一份邏輯，⛔ 又不在本線維護第二份拷貝（四點五）。
import ast                                     # noqa: E402
import types                                   # noqa: E402

_src = open(os.path.join(P16, "backtest", "researchp13.py"), encoding="utf-8").read()
_tree = ast.parse(_src)
_want = {"load_mktcap", "top50_by_month"}
_lines = _src.splitlines(keepends=True)
_take = []
_topn = None
for node in _tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in _want:
        _take.append("".join(_lines[node.lineno - 1:node.end_lineno]))
    if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "TOP_N" for t in node.targets):
        _topn = "".join(_lines[node.lineno - 1:node.end_lineno])
assert len(_take) == len(_want) and _topn, "⛔ 沒從正典取到那兩個函式／TOP_N ⇒ 停"
P13 = types.SimpleNamespace()
_ns = {"np": np, "pd": pd, "os": os, "D": D}
exec(_topn + "\n" + "\n".join(_take), _ns)       # noqa: S102
P13.load_mktcap = _ns["load_mktcap"]
P13.top50_by_month = _ns["top50_by_month"]
P13.TOP_N = _ns["TOP_N"]
print("✅ 已從正典 researchp13.py 取出 load_mktcap／top50_by_month（逐字原始碼）")
print("   資料樹：{}".format(D.DATA))

T1 = ("/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/"
      "C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/scratchpad/t1")
TOP_N = P13.TOP_N
print("   TOP_N = {}（取自正典，⛔ 不自訂）".format(TOP_N))

cal = D.load_calendar()
lo = int(cal.searchsorted(pd.Timestamp(SIG_START)))
hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)

exp = pd.read_csv(f"{T1}/exposure.csv", dtype={"stock_id": str})
sig = pd.read_csv(os.path.join(TREE, "backtest/results/signals.csv.gz"), dtype={"stock_id": str})

# 全市場排名池：主樹 data/stocks 下的每一檔
all_sids = sorted(b for b in (os.path.basename(p)[:-4] for p in
                  __import__("glob").glob(os.path.join(TREE, "data/stocks", "*.csv"))) if not b.startswith("_"))
print("   全市場排名池 {:,} 檔".format(len(all_sids)))
caps = P13.load_mktcap(all_sids, cal)
print("   load_mktcap 回了 {:,} 檔".format(len(caps)))

# ── ⭐ 逐日前 50 ──
M = np.full((len(all_sids), len(cal)), np.nan)
idx_of = {s: i for i, s in enumerate(all_sids)}
for s, a in caps.items():
    M[idx_of[s]] = a
top_flag = np.zeros_like(M, bool)
for t in range(lo, hi + 1):
    col = M[:, t]
    ok = np.flatnonzero(np.isfinite(col))
    if len(ok) == 0:
        continue
    order = ok[np.argsort(-col[ok], kind="stable")][:TOP_N]
    top_flag[order, t] = True
print("   逐日前 50 算完：平均每日入榜 {:.1f} 檔".format(top_flag[:, lo:hi + 1].sum(0).mean()))

pos_of = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}

# ── 訊號分級（逐日）──
sig["pos"] = sig["signal_date"].map(pos_of)
sig = sig[sig["pos"].notna()].copy()
sig["pos"] = sig["pos"].astype(int)
sig["si"] = sig["stock_id"].map(idx_of)
ok = sig["si"].notna()
print()
print("=== 併表檢查 ===")
print("  訊號 {:,} 筆，對不到市值檔的 {:,} 筆".format(len(sig), int((~ok).sum())))
sig = sig[ok].copy()
sig["si"] = sig["si"].astype(int)
sig["top50"] = top_flag[sig["si"].to_numpy(), sig["pos"].to_numpy()]

# ── 曝險分級（逐日）：要重走一次 gate，因為曝險表只有月彙總 ──
from backtest import patterns as P            # noqa: E402
uni = D.load_universe()
disp = D.load_disposal_intervals()
win = np.zeros(len(cal), bool)
win[lo:hi + 1] = True
den_top = den_rest = 0
n_done = 0
for sid, market, fs, ls in zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]):
    if sid not in idx_of:
        continue
    st = D.load_stock(sid, market, cal)
    if st is None:
        continue
    f = P.Frame(st.df, st.event_dates)
    g = f.gate & ((cal >= fs) & (cal <= ls)) & ~D.disposal_mask(sid, cal, disp) & win
    if not g.any():
        continue
    tf = top_flag[idx_of[sid]]
    den_top += int((g & tf).sum())
    den_rest += int((g & ~tf).sum())
    n_done += 1
    if n_done % 400 == 0:
        print("  曝險 {}/{}".format(n_done, len(uni)), file=sys.stderr)

n_days = hi - lo + 1
n_years = (cal[hi] - cal[lo]).days / 365.25
DPY = n_days / n_years
yr_top, yr_rest = den_top / DPY, den_rest / DPY

print()
print("=== 一 ⭐ 母體（逐日分級）===")
print("  市值前50   {:>12,} 檔-交易日 ＝ {:>9,.1f} 檔年".format(den_top, yr_top))
print("  其餘       {:>12,} 檔-交易日 ＝ {:>9,.1f} 檔年".format(den_rest, yr_rest))
print("  合計       {:>12,} 檔-交易日 ＝ {:>9,.1f} 檔年".format(
    den_top + den_rest, yr_top + yr_rest))
print("  （一年 {:.1f} 個交易日）".format(DPY))

print()
print("=== 二 ⭐⭐ 觸發率（次／檔／年）逐日分級版 ===")
print()
print("  {:<24}{:>22}{:>24}{:>11}".format("型態", "市值前50", "其餘", "前50÷其餘"))
print("  " + "-" * 81)
rows = []
for pat, g in sig.groupby("pattern"):
    a, b = int(g["top50"].sum()), int((~g["top50"]).sum())
    ra, rb = a / yr_top, b / yr_rest
    print("  {:<24}{:>13,} 筆 → {:.4f}{:>15,} 筆 → {:.4f}{:>11}".format(
        pat, a, ra, b, rb, "{:.2f}x".format(ra / rb) if rb else "n/a"))
    rows.append({"pattern": pat, "n_top50": a, "n_rest": b, "rate_top50": ra, "rate_rest": rb,
                 "ratio": ra / rb if rb else np.nan})
A, B = int(sig["top50"].sum()), int((~sig["top50"]).sum())
RA, RB = A / yr_top, B / yr_rest
print("  " + "-" * 81)
print("  {:<24}{:>13,} 筆 → {:.4f}{:>15,} 筆 → {:.4f}{:>11}".format(
    "【合計】", A, RA, B, RB, "{:.2f}x".format(RA / RB)))

print()
print("=== 三 ⭐ 順帶得到【型態訊號的前 50 佔比】（補件 §二 的 T3）===")
print("  {:,} / {:,} ＝ {:.2%}".format(A, A + B, A / (A + B)))
print("  ⚠ 對照（top50_share.py，1915 §六 逐字口徑、全市場、全窗）：")
print("     門檻B  276 / 2,882 ＝ 9.6%")
print("     參考C  538 / 5,799 ＝ 9.3%")
print("  ⛔ 三者【不是同一個分母單位】：本行是【訊號筆數】，那兩行是【股-月】")
print("     ⇒ ⛔ 不可直接相減，⏳ 要可比就得用同一個單位重算（見交件信）")

pd.DataFrame(rows).to_csv(f"{T1}/trigger_daily.csv", index=False)
pd.DataFrame([{"tier": "市值前50", "gate_days": den_top, "檔年": yr_top},
              {"tier": "其餘", "gate_days": den_rest, "檔年": yr_rest}]
             ).to_csv(f"{T1}/denominator_daily.csv", index=False)
print()
print("✅ 已寫出 trigger_daily.csv／denominator_daily.csv")

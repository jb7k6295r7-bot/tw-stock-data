"""T3 用 P5 新尺重算 ＋ 回答策略線 2047 §七 的分母問題 —— 回測線執行端。

本支回兩件：
  ① 型態線 20260923-2053 §四：「改了 P5 的尺，T3 的 4.3% 需要重新算一次」
  ② 策略線 20260923-2047 §七：「請確認 109 × 50 ＝ 5,450 當分母合不合理
     （即每月是否都有 50 檔前50股-月在池內宇宙裡）」

⭐ 市值與前 50：與 t3_pattern.py 同樣【直接取正典 researchp13.load_mktcap 的原始碼】，
  ⛔ 不維護第二份（2026-09-23「四點五」的教訓）。
⚠ 但這一支跑在 ~/tw-p17（因為 P5 新尺在這裡），⛔ 不是 t3_pattern.py 當時的 ~/tw-stock-data
  ⇒ ⭐ 所以本支【同時重算舊尺的 T3】，讓「舊 vs 新」在同一快照上比，
    ⛔ 並且不拿新尺的數字去減已交件的 4.3%。
"""
from __future__ import annotations

import ast
import glob
import os
import sys

import numpy as np
import pandas as pd

TREE = os.path.expanduser("~/tw-p17")
P16 = os.path.expanduser("~/tw-p16")
OUT = os.path.join(TREE, "backtest", "resultsp5win")
sys.path.insert(0, TREE)
os.chdir(TREE)
from backtest import data as D   # noqa: E402

# ── 正典市值實作（⛔ 不複製，原始碼原封不動取出來執行）────────────────────
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
n_finite = np.zeros(len(cal), int)
for t in range(len(cal)):
    col = M[:, t]
    ok = np.flatnonzero(np.isfinite(col))
    n_finite[t] = len(ok)
    if len(ok):
        top_flag[ok[np.argsort(-col[ok], kind="stable")][:TOP_N], t] = True
print("✅ top_flag 建好：{} 檔 × {} 日".format(*M.shape))

ym_of = pd.Series(cal.strftime("%Y-%m"), index=range(len(cal)))


# ── 候選池 ─────────────────────────────────────────────────────────────────
def pool(p5_file: str) -> pd.DataFrame:
    o = pd.read_csv(os.path.join(OUT, "other8.csv.gz"), dtype={"stock_id": str})
    p5 = pd.read_csv(os.path.join(OUT, p5_file), dtype={"stock_id": str})
    p5 = p5[["pattern", "stock_id", "signal_pos", "entry_pos", "signal_date"]]
    d = pd.concat([o, p5], ignore_index=True)
    d["ym"] = d["signal_date"].str.slice(0, 7)
    d = d[d["stock_id"].isin(idx_of)].copy()
    d["pos"] = d["signal_pos"].astype(int)
    return d[(d["ym"] >= WIN[0]) & (d["ym"] <= WIN[1])].copy()


def share(d, label):
    first = d.sort_values("pos").groupby(["stock_id", "ym"], as_index=False).first()
    hit = top_flag[first["stock_id"].map(idx_of).to_numpy(int), first["pos"].to_numpy(int)]
    n, k = len(first), int(hit.sum())
    by = (pd.DataFrame({"ym": first["ym"], "hit": hit})
          .groupby("ym")["hit"].agg(["sum", "count"]))
    by["p"] = by["sum"] / by["count"]
    print()
    print("=== {} ===".format(label))
    print("  ① 全窗合計：{:,} / {:,} ＝ {:.2%}   （{} 個月）".format(k, n, k / n, by.shape[0]))
    print("  ② 逐月比例：中位 {:.1%}／p10 {:.1%}／p90 {:.1%}".format(
        by["p"].median(), by["p"].quantile(0.10), by["p"].quantile(0.90)))
    print("     逐月分子為 0 的月份 {} / {}".format(int((by["sum"] == 0).sum()), len(by)))
    return k, n, by


print()
print("#" * 70)
print("# 一、T3：舊尺 vs 新尺（⭐ 同一棵樹、同一快照）")
print("#" * 70)
k_old, n_old, by_old = share(pool("p5_k0.csv.gz"), "舊尺（上穿與放量必須同日）")
k_new, n_new, by_new = share(pool("p5_k3.csv.gz"), "⭐ 新尺（對齊窗 ±3 交易日，型態線 2053 裁）")

print()
print("=== ⭐⭐ 並列（同單位【股-月】、同窗、同市值口徑）===")
print()
print("  {:<26}{:>16}{:>10}".format("候選池", "前50 / 總數", "比例"))
print("  " + "-" * 54)
print("  {:<26}{:>16}{:>10}".format("門檻B（K線 1915 裁的全窗值）", "276 / 2,882", "9.6%"))
print("  {:<26}{:>16}{:>10}".format("參考C", "538 / 5,799", "9.3%"))
print("  {:<26}{:>16}{:>10}".format("型態訊號・舊尺", "{:,} / {:,}".format(k_old, n_old),
                                    "{:.1%}".format(k_old / n_old)))
print("  {:<26}{:>16}{:>10}".format("型態訊號・新尺", "{:,} / {:,}".format(k_new, n_new),
                                    "{:.1%}".format(k_new / n_new)))
print()
print("  ⇒ 舊尺是門檻B（9.6%）的 {:.2f} 倍；新尺是 {:.2f} 倍"
      .format((k_old / n_old) / 0.096, (k_new / n_new) / 0.096))
print("  ⛔ 本行是【描述】：沒有檢定、沒有判定 ⇒ ⛔ 不可寫「測得出／測不出」（〈九十八〉）")

print()
print("#" * 70)
print("# 二、⏳ 回策略線 2047 §七：109 × 50 ＝ 5,450 這個分母合不合理")
print("#" * 70)
months = sorted(by_new.index)
rows = []
for ym in months:
    t = np.flatnonzero((ym_of == ym).to_numpy())
    sub = top_flag[:, t]
    any_day = int((sub.any(axis=1)).sum())      # 該月【任一天】進過前 50 的相異檔數
    all_day = int((sub.all(axis=1)).sum())      # 該月【每一天】都在前 50 的相異檔數
    rows.append({"ym": ym, "n_days": len(t), "top_any": any_day, "top_all": all_day,
                 "n_finite_min": int(n_finite[t].min())})
md = pd.DataFrame(rows)
md.to_csv(os.path.join(OUT, "t3_denominator_bymonth.csv"), index=False)
print()
print("  ⭐ 前 50 是【逐日】算的 ⇒ 一個月裡進出前 50 的相異檔數【不等於 50】")
print()
print("  該月任一天進過前50的相異檔數 top_any：")
print("      最小 {}／中位 {:.0f}／p90 {:.0f}／最大 {}"
      .format(int(md["top_any"].min()), md["top_any"].median(),
              md["top_any"].quantile(0.90), int(md["top_any"].max())))
print("      ＝ 50 的月份：{} / {}".format(int((md["top_any"] == 50).sum()), len(md)))
print("  該月每一天都在前50的相異檔數 top_all：")
print("      最小 {}／中位 {:.0f}／最大 {}"
      .format(int(md["top_all"].min()), md["top_all"].median(), int(md["top_all"].max())))
print("  每日有市值的檔數下限（確認 50 這個名額沒有缺額）：最小 {}"
      .format(int(md["n_finite_min"].min())))
print()
tot_any = int(md["top_any"].sum())
print("  ⇒ 策略線用的分母　　109 × 50 ＝ {:,}".format(len(md) * 50))
print("  ⇒ 逐月相異檔數加總　Σ top_any ＝ {:,}（差 {:+.1%}）"
      .format(tot_any, tot_any / (len(md) * 50) - 1))
print("  ⇒ 逐月全月都在前50　Σ top_all ＝ {:,}".format(int(md["top_all"].sum())))
print()
print("  ⭐ 而【每月摸到的前50檔數】那一欄要的是分子：")
for lab, k_ in (("舊尺", k_old), ("新尺", k_new)):
    print("     {}：{:,} / {} 個月 ＝ 每月 {:.1f} 檔"
          "　⇒ ÷50 ＝ {:.1%}　⇒ ÷(Σtop_any/109 ＝ {:.1f}) ＝ {:.1%}"
          .format(lab, k_, len(md), k_ / len(md), k_ / len(md) / 50,
                  tot_any / len(md), k_ / len(md) / (tot_any / len(md))))

by_old.to_csv(os.path.join(OUT, "t3_bymonth_k0.csv"))
by_new.to_csv(os.path.join(OUT, "t3_bymonth_k3.csv"))
print()
print("[輸出] {}".format(OUT))

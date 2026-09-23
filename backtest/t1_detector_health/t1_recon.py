"""⛔ 自我對帳：本線 t1_mktcap.py 與【正典】researchp13.load_mktcap 是不是同一個東西。

背景（⚠ 本線的錯）：
  市值與「當月前 50」早就有一份實作 —— backtest/researchp13.py 的 load_mktcap／top50_by_month，
  由 backtest/top50_share.py 使用。本線因為搜錯了樹（搜 claude/... 分支那個 checkout，
  而 P11~P16 全在 tw-p16 worktree），又寫了一份 ⇒ 四點五。

本檔要回答兩題：
  ① 市值【數值】是不是逐位元相同  ⇒ 若相同，本線那份只是多餘，不是錯
  ② 本線用【月底】當量測日、正典用【量測日 entry_pos−1】⇒ 前 50 名單差多少
     ⇒ 若同一個月內前 50 幾乎不變，T1 的級距結論不受影響
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

P16 = os.path.expanduser("~/tw-p16")
sys.path.insert(0, P16)
os.chdir(P16)
from backtest import data as D            # noqa: E402
from backtest import researchp13 as P13   # noqa: E402

T1 = ("/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/"
      "C--SynologyDrive---------/57a7a54c-a515-48e2-87ab-d32197791f42/scratchpad/t1")

mine = pd.read_csv(f"{T1}/mktcap.csv", dtype={"stock_id": str})
cal = D.load_calendar()
print("p16 樹的日曆：{} ~ {}（{:,} 日）".format(cal[0].date(), cal[-1].date(), len(cal)))

sids = sorted(mine["stock_id"].unique())
print("對帳 {:,} 檔".format(len(sids)))
caps = P13.load_mktcap(sids, cal)
print("正典 load_mktcap 回了 {:,} 檔".format(len(caps)))

# ── ① 市值數值對帳：抽每檔的月底那一天 ──
pos = {d: i for i, d in enumerate(cal)}
ym_cal = pd.Series(cal).dt.strftime("%Y-%m").to_numpy()
# 每個月最後一個日曆位置
last_pos_of_ym = {}
for i, y in enumerate(ym_cal):
    last_pos_of_ym[y] = i

same = diff = miss = 0
worst = 0.0
for sid in sids[:400]:
    a = caps.get(sid)
    if a is None:
        continue
    m = mine[mine["stock_id"] == sid]
    for _, r in m.iterrows():
        t = last_pos_of_ym.get(r["ym"])
        if t is None:
            continue
        # 本線取的是「該月最後一個【有成交】日」⇒ 往回找第一個非 NaN
        v = np.nan
        for k in range(t, max(-1, t - 25), -1):
            if np.isfinite(a[k]):
                v = a[k]
                break
        if not np.isfinite(v):
            miss += 1
            continue
        rel = abs(v - r["mktcap"]) / r["mktcap"]
        if rel < 1e-12:
            same += 1
        else:
            diff += 1
            worst = max(worst, rel)

print()
print("=== ① 市值數值對帳（前 400 檔的所有檔-月）===")
print("  逐位元相同 {:,}　不同 {:,}　正典取不到值 {:,}".format(same, diff, miss))
if diff:
    print("  最大相對差 {:.3e}".format(worst))
    print("  ⇒ ⚠ 兩份【不是】同一個數 ⇒ 要查為什麼")
else:
    print("  ⇒ ✅ 兩份是同一個數 ⇒ 本線那份只是【多餘】，⛔ 不是算錯")

# ── ② 前 50 名單：月底 vs 月內其他日 ──
print()
print("=== ② 前 50 名單在【同一個月內】穩不穩（決定「月底當量測日」有沒有影響）===")
rng = np.random.default_rng(20260923)
yms = sorted({y for y in ym_cal if "2017-03" <= y <= "2026-02"})
sample = [yms[i] for i in rng.choice(len(yms), 18, replace=False)]
jac = []
for y in sorted(sample):
    idx = np.flatnonzero(ym_cal == y)
    if len(idx) < 5:
        continue
    t_end = int(idx[-1])
    t_mid = int(idx[len(idx) // 2])
    def top(t):
        rows = [(caps[s][t], s) for s in sids if s in caps and np.isfinite(caps[s][t])]
        rows.sort(reverse=True)
        return {s for _, s in rows[:50]}
    a, b = top(t_end), top(t_mid)
    if not a or not b:
        continue
    j = len(a & b) / len(a | b)
    jac.append(j)
    print("  {}  月底 vs 月中：共同 {:>2}/50　Jaccard {:.3f}".format(y, len(a & b), j))
print()
print("  ⇒ Jaccard 中位 {:.3f}　最低 {:.3f}".format(float(np.median(jac)), float(np.min(jac))))
if np.min(jac) >= 0.92:
    print("  ⇒ ✅ 前 50 名單在月內【幾乎不動】⇒ 用月底當量測日不影響 T1 的級距結論")
else:
    print("  ⇒ ⚠ 名單在月內會動 ⇒ T1 的級距要改用正典的量測日重算")

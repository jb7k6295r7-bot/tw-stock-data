"""tw-stock-db/SKILL.md：加入「面額變更不在 data/adj/」這條限制與檢核項。只新增、錨點插入。

    python3 backtest/skill_patch/patch_tw_stock_db.py <原 SKILL.md> <輸出 SKILL.md>
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
orig = s

LIMIT = """  已用上市那一半對 TWSE 官方全量核對過、不符 0.00%
- ⚠⚠ **`data/adj/` 不收「面額變更換發新股」（2026-09-08 回測時發現）。** 因子檔只有除權息與減資兩種事件；
  面額 10 元→1 元（或 →2、→5 元）換發新股時，股票停牌約 8 個交易日，復牌首日價格變成原來的 1/10（股數 ×10、×20），
  **還原價在那一天斷掉，長區間報酬會出現單筆 −95% 的假數字，而且不會報錯**。全庫實測 **26 筆、24 檔**，全部落在復牌首日、都不是還原事件日
  （例：5314 世紀 2025-03-31 收盤比 0.055、股數 14.7M → 294M；4763 材料-KY 2025-06-30 比 0.10）。
  → **讀取端要自己擋**：對「上一個有成交日」的收盤比 **< 0.55 或 > 1.8**、且該日不是 `data/adj/` 的事件日 → 視為未還原跳價，
  該檔以跳價日為中心的視窗（前 121 日～後 20 日，涵蓋 120 日持有）整段剔除，**不要用猜的比例去還原**（比例只能猜、猜錯更糟）。
  清單在 `backtest/results/par_change_candidates.csv`；根治要 `adjust.py` 多收一種事件，在那之前這條限制一直存在。
"""

VERIFY = """- [ ] 需要還原報酬時，用的是 `data/adj/` 的累積因子，**沒有把上櫃當成「沒有因子」**
- [ ] 用還原價算跨日報酬時，**已擋掉面額變更的跳價**（對上一個有成交日的收盤比 < 0.55 或 > 1.8 且非還原事件日 → 整段剔除），沒有把 −95% 當成真的"""

for anchor, new in [("  已用上市那一半對 TWSE 官方全量核對過、不符 0.00%\n", LIMIT),
                    ("- [ ] 需要還原報酬時，用的是 `data/adj/` 的累積因子，**沒有把上櫃當成「沒有因子」**", VERIFY)]:
    n = s.count(anchor)
    if n != 1:
        sys.exit(f"錨點出現 {n} 次：{anchor[:50]!r}")
    s = s.replace(anchor, new)

heads_old = re.findall(r"^#{2,4} .*$", orig, flags=re.M); heads_new = re.findall(r"^#{2,4} .*$", s, flags=re.M)
if [h for h in heads_old if h not in heads_new]:
    sys.exit("章節消失")
new_set = set(s.splitlines())
gone = [l for l in orig.splitlines() if l.strip() and l not in new_set]
if gone:
    sys.exit(f"原文有 {len(gone)} 行不見了：{gone[:3]}")
open(dst, "w", encoding="utf-8").write(s)
print(f"原 {len(orig):,} 字元 → 新 {len(s):,} 字元；章節 {len(heads_old)} → {len(heads_new)}（只增不刪）")

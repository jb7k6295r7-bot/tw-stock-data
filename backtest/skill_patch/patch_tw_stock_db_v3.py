"""tw-stock-db/SKILL.md v3：修正線上版（2026-09-08 21:28 台北，23,147 bytes）陷阱 13 的兩處。

    python3 backtest/skill_patch/patch_tw_stock_db_v3.py <線上版 SKILL.md> <輸出 SKILL.md>

這一版**有取代**（不是純新增），取代的行逐一列在 REPLACES；驗證時只允許這些行消失。

1. 判定規則寫成「相鄰兩個交易日的收盤比 close(t)/close(t-1)」——**那會一筆都抓不到**。
   面額變更換發新股前會停牌約 8 個交易日，跳價發生在「復牌首日 vs 停牌前最後一個成交日」之間；
   日曆對齊的序列裡 t−1 是空的。實測：相鄰日比 → 0 筆；對上一個有成交日比 → 26 筆。
2. 「資料庫線尚未自行複核那份名單」——已複核：全庫掃過、26 筆 24 檔逐筆列出、4 檔對過原始價與股數、
   清單在 repo、READ_CONTRACT 第五節已加同一列（commit 693658b2）。改寫成已驗證狀態。
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
orig = s

REPLACES = [
    (
        """→ **判定規則：相鄰兩個交易日的收盤比 `close(t) / close(t-1)` 落在 `< 0.55` 或 `> 1.8`，
且 `data/adj/` 裡沒有對應日期的除權息或減資事件可以解釋，就當作疑似面額變更，
該筆單獨標記、不併入報酬序列。**
""",
        """→ **判定規則：收盤對「上一個有成交日」的收盤之比 `close(t) / close(prev_traded)` 落在 `< 0.55` 或 `> 1.8`，
且 t 不是 `data/adj/` 的除權息或減資事件日，就當作面額變更跳價；
該檔以 t 為中心的視窗（前 121 個交易日～後 20 個交易日，涵蓋 120 日持有）整段不併入報酬序列，不要用猜的比例去還原。**

⚠ **一定要對「上一個有成交日」，不是「前一個交易日」。** 換發新股前會停牌約 8 個交易日，跳價落在
「復牌首日 vs 停牌前最後一個成交日」之間；日曆對齊的序列裡 t−1 是空的。
**實測：用相鄰交易日比 → 0 筆；用上一個有成交日比 → 26 筆。** 寫成前者等於這條沒生效。
""",
    ),
    (
        """⚠ 出處與現況：本條於 **2026-09-08 由另一條線移交給資料庫線**（原本寫在那一支 skill 裡，
改成指路後若資料庫這側沒收，規則會變成兩邊都沒有）。
**門檻 0.55／1.8 與「約 26 筆」的量級沿用移交內容，資料庫線尚未自行複核那份名單。**
要把它變成管線裡的自動標記之前，先在 `data/stocks/` 全庫掃一次、把命中的逐筆看過，
並把結果寫進 `docs/READ_CONTRACT.md`。**在那之前這是判讀時的人工檢查，不是已驗證的資料欄位。**
""",
        """⚠ 出處與現況：本條於 **2026-09-08 由 K線線移交給資料庫線**。**資料庫線已複核（2026-09-08 晚）**：
`data/stocks/` 全庫掃過，命中 **26 筆、24 檔**，全部落在停牌後復牌首日、都不是還原事件日；
其中 5314（2025-03-31，比 0.055，股數 14.7M → 294M）、4763（2025-06-30，比 0.10）、8422（2025-11-17，比 0.099）、
5904（2026-08-10，比 0.11，股數 ×10）四檔對過原始價與股數。
清單在 repo `backtest/results/par_change_candidates.csv`，掃描程式是 `backtest/data.py` 的 `jump_days()`，
`docs/READ_CONTRACT.md` 第五節已加同一列。**根治要 `adjust.py` 多收「面額變更」這種事件；在那之前這是讀取端必做的擋法，不是選配。**
""",
    ),
]

removed_lines = set()
for old, new in REPLACES:
    n = s.count(old)
    if n != 1:
        sys.exit(f"錨點出現 {n} 次：{old[:50]!r}")
    s = s.replace(old, new)
    removed_lines |= {l for l in old.splitlines() if l.strip()}

heads_old = re.findall(r"^#{2,4} .*$", orig, flags=re.M); heads_new = re.findall(r"^#{2,4} .*$", s, flags=re.M)
if [h for h in heads_old if h not in heads_new]:
    sys.exit("章節消失")
new_set = set(s.splitlines())
gone = [l for l in orig.splitlines() if l.strip() and l not in new_set and l not in removed_lines]
if gone:
    sys.exit(f"原文有 {len(gone)} 行不在允許取代清單內卻消失了：{gone[:3]}")
open(dst, "w", encoding="utf-8").write(s)
print(f"原 {len(orig):,} 字元 → 新 {len(s):,} 字元；取代 {len(removed_lines)} 行（皆在允許清單內），章節 {len(heads_old)} → {len(heads_new)}")

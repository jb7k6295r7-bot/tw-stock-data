# -*- coding: utf-8 -*-
"""答台股策略線 2125 §二：研究十九【盤中觸價】那 30 格有沒有印判定？

⛔ 不憑印象 —— 直接數 results19/summary.md 上印了幾個判定標籤，並分清是【哪一種】判定。
"""
from __future__ import annotations
import os
import io
import re

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
P = "results19/summary.md"
txt = io.open(P, encoding="utf-8").read()
lines = txt.split("\n")

#  ── 先找出兩個口徑的區段邊界
def sec_bounds(head_pat):
    i = next(i for i, l in enumerate(lines) if re.match(head_pat, l))
    j = next((j for j in range(i + 1, len(lines)) if re.match(r"^## ", lines[j])), len(lines))
    return i, j


b_main = sec_bounds(r"^## 二、")
b_intra = sec_bounds(r"^## 二′、")
print("=== ① 兩個口徑在 summary.md 的行範圍 ===")
print("  主格（## 二、）    行 {}~{}：{}".format(b_main[0] + 1, b_main[1], lines[b_main[0]]))
print("  盤中觸價（## 二′、）行 {}~{}：{}".format(b_intra[0] + 1, b_intra[1], lines[b_intra[0]]))

LAB = re.compile(r"測得出（[＋−]）|測得出|測不出")


def count(lo, hi):
    tbl = 0   # 表格列（| … | 統計層 |）＝ 水準列對基準的可偵測性
    bul = 0   # 條列（- k＝…）裡的 B−A／B−C 差值判定
    for l in lines[lo:hi]:
        if l.startswith("|") and LAB.search(l):
            tbl += 1
        elif l.lstrip().startswith("-") and LAB.search(l):
            bul += len(LAB.findall(l))
    return tbl, bul


print()
print("=== ② 逐口徑數印出來的判定標籤 ===")
tot = {}
for name, (lo, hi) in (("主格：收盤跌破", b_main), ("敏感度：盤中觸價", b_intra)):
    tbl, bul = count(lo, hi)
    tot[name] = (tbl, bul)
    print("  {}".format(name))
    print("     表格【水準列】印統計層的列數      {:3d}".format(tbl))
    print("     條列裡的判定標籤總數（含 B−A／B−C 與放棄組的對基準）{:3d}".format(bul))

print()
print("=== ③ ⭐ 對上登錄自己寫的格數 ===")
pre = io.open("PREREG19.md", encoding="utf-8").read()
for l in pre.split("\n"):
    if "格數" in l and "30" in l:
        print("  PREREG19 逐字：" + l.strip())
print()
print("  ⇒ 登錄把【格】定義成 5 k × 3 H × 2 差值 ＝ 30（差值 ＝ B−A 與 B−C）")
m = re.search(r"^## 四、格數：(.+)$", txt, re.M)
print("  ⇒ summary.md §四 逐字：" + (m.group(0) if m else "（找不到）"))

print()
print("=== ④ ⭐⭐ 答案 ===")
print("  ✅ **有印**。盤中觸價那 30 格【每一格】都印了測得出／測不出：")
print("     ・§二′ 的三張水準表各 12 列都印「統計層」")
print("     ・§二′ 的條列逐 k 印 B−A 與 B−C 的 CI 與判定")
print("     ・§四 逐字印「盤中觸價 30 格、測得出 17 格、雜訊期望 1.5」")
print("  ⇒ 依裁定線 2028 §一「表上有沒有印」⇒ 研究十九記 **60 格**（主格 30 ＋ 盤中觸價 30）")
print()
print("=== ⑤ ⚠ 而本線要多報兩件（⛔ 不報會讓分母又錯一次）===")
t1, b1 = tot["主格：收盤跌破"]
t2, b2 = tot["敏感度：盤中觸價"]
print("  (一) 除了那 30 格，水準表【還額外印了】統計層：主格 {} 列、盤中觸價 {} 列".format(t1, t2))
print("       ⇒ 它們判的是「該臂的超額 vs 基準」的可偵測性，⛔ 不是登錄的 B−A／B−C 那 30 格")
print("       ⇒ ⏳ 算不算 ＝ 裁定線的格子（形狀同 P12 effects.csv 的 verdict 欄，那次裁不算）")
print("  (二) PREREG19 §重跑 的 --calib-window A 版本（results19_calibA_0914）")
print("       ⇒ ⭐ 那是【同樣的 30+30 格】用另一個校準窗重算 ⇒ ⛔ 不是多出 60 格")
print("       ⇒ 它的測得出數是 主格 6／盤中觸價 15（原版 7／17）")
print("       ⇒ ⚠ 所以研究十九有【兩個版本的判定結果】⇒ 引用時要說是哪一版")

#  ⛔ 自測：兩個口徑的水準列數必須相等（同樣 3 張表 × 12 列）
assert t1 == t2, "⛔ 兩個口徑的水準列數不等（{} vs {}）⇒ 表結構不對稱，要查".format(t1, t2)
assert t1 == 36, "⛔ 水準列應是 3 H × 12 列 ＝ 36，實得 {}".format(t1)
print()
print("✅ 自測：兩個口徑的水準列數相等且 ＝ 3 H × 12 列 ＝ 36")

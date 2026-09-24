# -*- coding: utf-8 -*-
"""核對市場情報分析線 `tw-stock-factor-evidence` 引用的本線數字（⇐ 他們 20260924-2152）。

⛔ 不靠眼睛比 —— 把他們信裡逐條列的值寫成 CLAIMS，逐條去本線交件裡【用字串比對】找。
⭐ 找法：把「+1.78%」這種值連同它的 CI 一起，去對應的那一列裡找 ⇒ 找不到就是對不上。
"""
from __future__ import annotations
import os
import io
import re

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
AMT = io.open("results3_amt/summary.md", encoding="utf-8").read()
FULL = io.open("results3/CONCLUSIONS.md", encoding="utf-8").read()
R5 = io.open("results5/CONCLUSIONS.md", encoding="utf-8").read()

ok, bad = [], []


def chk(name, src_name, src, *frags):
    """frags 全部都要出現在【同一列】裡才算對上。"""
    rows = [l for l in src.split("\n") if all(f in l for f in frags)]
    if rows:
        ok.append((name, src_name, rows[0].strip()[:98]))
    else:
        bad.append((name, src_name, " ＋ ".join(frags)))


print("=== ① 5,000 萬版、持有 20 日（來源 results3_amt/summary.md 訂正段）===")
C20 = [
    ("G1 營收創 24 月新高", "+1.78%", "+1.23% ~ +2.33%"),
    ("G3 創高 ＋ 多頭排列", "+2.87%", "+2.00% ~ +3.73%"),
    ("G1 已漲過", "+2.30%", "+1.58% ~ +3.02%"),
    ("G1 未漲過", "+0.70%", "-0.39% ~ +1.79%"),
    ("C1 只有多頭排列", "+0.51%", "+0.15% ~ +0.86%"),
    ("G2 營收年增 ≥ 15%", "+0.76%", "+0.53% ~ +0.99%"),
    ("G2c 連三月年增 ≥ 15%", "+0.83%", "+0.47% ~ +1.19%"),
    ("G4 年增率第 10 分位", "+0.78%", "+0.28% ~ +1.28%"),
    ("G4 第 10 − 第 1 分位差", "+1.98%", "+1.27% ~ +2.69%"),
    ("G4 年增率第 1 分位", "-1.20%", "-1.58% ~ -0.82%"),
    ("V1 PE8~15", "+0.28%", "-0.26% ~ +0.82%"),
    ("V2 本益比：低 − 高", "-0.32%", "-1.18% ~ +0.54%"),
    ("V3 殖利率：高 − 低", "+0.16%", "-0.76% ~ +1.08%"),
    ("V4 股淨比：低 − 高", "+0.59%", "-0.35% ~ +1.54%"),
]
for nm, v, ci in C20:
    chk(nm + "（20 日）", "results3_amt", AMT, nm, v, ci)

print("=== ② 5,000 萬版、持有 60 日 ===")
for nm, v, ci in [
    ("G1 營收創 24 月新高", "+4.75%", "+2.47% ~ +7.04%"),
    ("V1 PE8~15", "+0.88%", "-0.68% ~ +2.45%"),
    ("V2 本益比：最低十分位", "-1.50%", "-3.39% ~ +0.40%"),
]:
    chk(nm + "（60 日）", "results3_amt", AMT, nm, v, ci)
chk("G3（60 日）點估計 +6.70%", "results3_amt", AMT, "G3 創高 ＋ 多頭排列", "+6.70%")

print("=== ③ 全庫版對照 ===")
chk("全庫版 G1 20 日", "results3/CONCLUSIONS", FULL, "G1 營收創 24 月新高", "+2.02%", "+1.48% ~ +2.56%")

print("=== ④ 面板事實 ===")
chk("面板 60,868 列／1,684 檔", "results3_amt", AMT, "60,868 列", "1,684 檔")
chk("127 換股日與起訖", "results3_amt", AMT, "127", "2016-01-11 ~ 2026-07-13")

print("=== ⑤ 三張「全庫版、訂正前口徑」表 ===")
chk("修剪 前 1%", "results3/CONCLUSIONS", FULL, "前 1%", "+4.09 pp")
chk("修剪 前 5%", "results3/CONCLUSIONS", FULL, "前 5%", "+3.00 pp")
chk("修剪 前 10%", "results3/CONCLUSIONS", FULL, "前 10%", "+2.17 pp")
chk("修剪 不修剪（情報線寫 +4.77）", "results3/CONCLUSIONS", FULL, "| 不拿 |", "+4.77 pp")
chk("修剪 不修剪（本線檔案是 +4.78）", "results3/CONCLUSIONS", FULL, "| 不拿 |", "+4.78 pp")
chk("前 1% 87 筆分散 64 檔", "results3/CONCLUSIONS", FULL, "87 筆分散在 64 檔")
chk("N=3 那一列", "results3/CONCLUSIONS", FULL, "| **3** |", "−3.9%", "+1.5%", "**43%**", "−5.0%", "+4.2%")
chk("N=1 那一列", "results3/CONCLUSIONS", FULL, "| 1 |", "−6.0%", "+0.3%", "49%", "−9.5%", "+1.4%", "47%")
chk("N=50 那一列", "results3/CONCLUSIONS", FULL, "| 50 |", "−1.8%", "+2.9%", "36%", "−0.9%", "+6.0%", "28%")
#  ⭐ 停損表：情報線說出處是 results3 ⇒ 先去 results3 找，再去 results5 找
chk("停損 S15（找 results3）", "results3/CONCLUSIONS", FULL, "32%", "−1.88 pp")
chk("停損 S15（找 results5）", "results5/CONCLUSIONS", R5, "S15", "32%", "−1.88 pp", "−2.18 ~ −1.58")
chk("停損 S20（找 results5）", "results5/CONCLUSIONS", R5, "S20", "20%", "−1.40", "−1.63 ~ −1.16")
chk("停損 S25（找 results5）", "results5/CONCLUSIONS", R5, "S25", "12%", "−0.91", "−1.09 ~ −0.74")
chk("停損 S30（找 results5）", "results5/CONCLUSIONS", R5, "S30", "7%", "−0.60", "−0.72 ~ −0.47")

print()
print("=== ⭐ 對上的 {} 條 ===".format(len(ok)))
for n, s, r in ok:
    print("  ✅ {:34s} [{}]  {}".format(n, s, r))
print()
print("=== ⛔ 沒對上的 {} 條 ===".format(len(bad)))
for n, s, f in bad:
    print("  ⛔ {:34s} [{}]  找不到：{}".format(n, s, f))

print()
print("=== ⑥ ⚠ 停損表的出處與「九種」的定義 ===")
m = re.search(r"^.*九種停損規則.*$", R5, re.M)
print("  results5 §一句話 逐字：{}".format(m.group(0).strip()[:140] if m else "（找不到）"))
m2 = re.search(r"^.*事前沒登錄.*$", R5, re.M)
print("  results5 追加分析 逐字：{}".format(m2.group(0).strip()[:160] if m2 else "（找不到）"))
m3 = re.search(r"^判準：.*$", R5, re.M)
print("  results5 判準 逐字：{}".format(m3.group(0).strip()[:110] if m3 else "（找不到）"))

# ⛔ 鑑別力自測：故意查一個一定不存在的值，必須落進 bad
before = len(bad)
chk("⛔ 鑑別力自測（查一個不存在的值）", "results3_amt", AMT, "G1 營收創 24 月新高", "+9.99%")
assert len(bad) == before + 1, "⛔ 查不存在的值卻對上了 ⇒ 比對邏輯壞了"
bad.pop()
print()
print("✅ 鑑別力自測：查一個不存在的 +9.99% ⇒ 確實落進「沒對上」（⇒ 比對會響）")

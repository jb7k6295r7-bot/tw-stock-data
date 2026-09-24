# -*- coding: utf-8 -*-
"""回測線信箱分流：把每一封 回✖ 的【要本線做什麼】抽出來。

⛔⛔ 這【不是】全文閱讀。本支做的是【動作掃描】：
  ① 抓「要對方做的事／要你們做什麼／本件要」那一節
  ② 抓所有提到「回測線」的行
  ③ 抓所有 ⏳ 開頭的行（本專案用它標待辦）
⇒ ⭐ 目的：確保【沒有一件點名本線的動作被漏掉】
⇒ ⛔ 而本線在回報時必須說清楚「這是動作掃描，不是逐字全文讀」——
  ⚠ 因為本線 2026-09-24 08:2x 就是因為「簽了＝處理了」的錯覺而一次簽了 21 封。
"""
from __future__ import annotations
import os, re, sys, datetime

BOX = "/mnt/c/SynologyDrive/跨線信箱"
names = [n for n in os.listdir(BOX) if os.path.isfile(os.path.join(BOX, n)) and "回✖" in n]


def age(n):
    m = re.search(r"-(20\d{6})-", n)
    if not m:
        return 99
    return (datetime.datetime(2026, 9, 24) - datetime.datetime.strptime(m.group(1), "%Y%m%d")).days


HIT = re.compile(r"回測線")
TODO = re.compile(r"^\s*[⏳]")
SEC = re.compile(r"^#+\s*[^\n]*(要對方做的事|要你們做什麼|本件要|要誰做什麼|本封要)")

rows = []
for n in sorted(names, key=lambda x: (-age(x), x)):
    p = os.path.join(BOX, n)
    try:
        t = open(p, encoding="utf-8").read()
    except Exception as e:
        rows.append((n, age(n), ["⛔ 讀不到：{}".format(e)]))
        continue
    lines = t.split("\n")
    hits = []
    # ① 要對方做的事那一節
    for i, L in enumerate(lines):
        if SEC.match(L):
            seg = []
            for k in range(i, min(len(lines), i + 26)):
                if k > i and lines[k].startswith("#"):
                    break
                seg.append(lines[k])
            hits.append("〔節〕" + " / ".join(x.strip() for x in seg if x.strip())[:420])
            break
    # ② 提到回測線、且同一行帶動作意味的
    for L in lines:
        if HIT.search(L) and re.search(r"⏳|請|要|需|應|補|交|回一封|重跑|重算|落地", L):
            s = L.strip()
            if 6 < len(s) < 300:
                hits.append("〔回〕" + s)
    # ③ ⏳ 行
    for L in lines:
        if TODO.match(L):
            s = L.strip()
            if 6 < len(s) < 300:
                hits.append("〔⏳〕" + s)
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h); out.append(h)
    rows.append((n, age(n), out[:6]))

print("回✖ 共 {} 封（⭐ 依日齡由舊到新）".format(len(rows)))
print()
for n, a, hits in rows:
    if a < int(sys.argv[1] if len(sys.argv) > 1 else 0):
        continue
    print("─" * 100)
    print("【{} 天】{}".format(a, n[:96]))
    if not hits:
        print("   （掃不到任何點名本線的動作行）")
    for h in hits:
        print("   " + h[:280])

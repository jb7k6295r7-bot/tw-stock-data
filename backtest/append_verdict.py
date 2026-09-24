# -*- coding: utf-8 -*-
"""把策略線定版的結案措辭【逐字】接到 P17_REPORT.md 後面。

⛔⛔ 本支【不手打任何一個字】：兩段都是從解讀全文檔裡按行切出來原封不動貼過去的。
  ⇒ ⭐ 理由：本線的角色邊界是「裁下來的措辭【逐字照抄】」
    ⇒ 手打會引入改寫風險，⛔ 而那正是本線不該做的事。

⭐ 先驗來源檔的 sha16（口徑：去檔尾 pw1 行 ⇒ rstrip('\n')+'\n' ⇒ UTF-8 ⇒ sha256 前 16），
  ⛔ 對不上就不動 P17_REPORT.md。
"""
import glob
import hashlib
import os
import re

BOX = "/mnt/c/SynologyDrive/跨線信箱"
REPORT = os.path.expanduser("~/tw-p17/backtest/resultsp17/P17_REPORT.md")
# ⭐ 改版時只改這三行（⛔ 其餘不動）：台股策略線每出一個新 seq 就重抄一次
WANT = "312156a895d4fe12"
SRCPAT = "解讀全文-P17結論解讀與結案措辭_台股策略線_seq4_*"
SEQ = "seq=4"
MARK = "## ⭐⭐ 結案措辭（定版，逐字轉載）"


def sha16(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    if lines and lines[-1].lstrip().startswith("<!-- pw1"):
        lines.pop()
    return hashlib.sha256(("\n".join(lines).rstrip("\n") + "\n").encode("utf-8")).hexdigest()[:16]


c = glob.glob(os.path.join(BOX, SRCPAT))
if len(c) != 1:
    raise SystemExit("⛔ 來源檔比對到 {} 份 ⇒ 停止".format(len(c)))
src = open(c[0], encoding="utf-8").read()
got = sha16(src)
if got != WANT:
    raise SystemExit("⛔⛔ 來源 sha16 {} ≠ 宣稱 {} ⇒ 停止，⛔ 不動 P17_REPORT.md".format(got, WANT))
print("✅ 來源 sha16 {} 相符：{}".format(got, os.path.basename(c[0])))

lines = src.split("\n")


def section(title_re: str) -> list[str]:
    """抓 `## …` 起到【下一個同級 `## `】之前，⛔ 原封不動。"""
    start = None
    for i, L in enumerate(lines):
        if start is None and re.match(title_re, L):
            start = i
            continue
        if start is not None and L.startswith("## "):
            out = lines[start:i]
            while out and out[-1].strip() in ("", "---"):
                out.pop()
            return out
    raise SystemExit("⛔ 找不到節：{}".format(title_re))


sec2 = section(r"^## 二、.*結案措辭")
sec9 = section(r"^## 九、.*引用限制")
print("   §二 {} 行／§九 {} 行（⭐ 逐行原封不動）".format(len(sec2), len(sec9)))

rep = open(REPORT, encoding="utf-8").read()
if MARK in rep:
    # ⭐ 已經有結案節 ⇒ 這是【改版重抄】：把舊的整節切掉，⛔ 不重複接、⛔ 不手動編輯
    i = rep.index(MARK)
    j = rep.rfind("\n---\n", 0, i)          # 連同本線加在它前面的分隔線一起切
    cut = j if j != -1 else i
    print("⚠ 偵測到既有結案節 ⇒ ⭐ 切掉舊的 {:,} 位元組後重抄（＝ 改版，⛔ 不是重複接）"
          .format(len(rep[cut:].encode("utf-8"))))
    rep = rep[:cut].rstrip("\n") + "\n"
    open(REPORT, "w", encoding="utf-8").write(rep)

# ⛔⛔ 機器檢查（⭐ 裁定線 1131 §二：同族第二次出現 ⇒ 處置必須是【機器檢查】，
#    ⛔ 不可留成「下次小心」）。本線 09-24 發現「sha16 **{}**」那一行漏了 .format(WANT)
#    ⇒ ⚠ 而它【沒有報錯】、⛔ 也沒有被既有閘門擋到 ——
#      ⭐ 既有閘門驗的是【來源檔的 sha】，⛔ 不是【產出的字】。
#    ⇒ ⭐⭐ 所以這一道驗的是產出本身：組好的字裡不得殘留未代換的大括號佔位符。
def _no_unrendered(text):
    import re as _re
    bad = _re.findall(r"\{\}|\{[0-9]+\}|\{[A-Za-z_][A-Za-z0-9_]*\}", text)
    assert not bad, (
        "⛔ 產出裡殘留未代換的佔位符 " + repr(bad) + " ⇒ 有一行忘了 .format(...)")


block = "\n".join([
    "",
    "---",
    "",
    MARK,
    "",
    "> ⛔⛔ **這一節不是回測線寫的。** 它是策略線定版的措辭，本線【逐字轉載】。",
    "> ⭐ 本線的角色邊界：⛔ 不訂判定用語 ⇒ 裁下來的措辭一個字都不改寫。",
    ">",
    "> 出處：`{}`".format(os.path.basename(c[0])),
    "> sha16 **{}**（本線已重算相符：去檔尾 pw1 行 ⇒ rstrip+\\n ⇒ UTF-8 ⇒ sha256 前 16）".format(WANT),
    "> 版本：**{}**｜轉載工具：`backtest/append_verdict.py`（⭐ 它會先驗 sha16，對不上就拒絕動檔）".format(SEQ),
    ">",
    "> ⚠ 沿革（⭐ 逐版留著，⛔ 不要只留最新的）：",
    "> - seq=1（sha `23b159c283b2896b`・33,428 B・22:18）⇒ ⛔ 已作廢，本線【沒有】抄它",
    ">   ⇒ ⭐ 本線第一次要抄時 sha 對不上才發現它已被取代 —— 這就是「抄之前先對 sha」擋到的那一次",
    "> - seq=2（sha `0333b2a16203e95a`・36,763 B・22:28）⇒ ✅ 裁定線 2257 過目通過，本線曾抄入",
    "> - seq=3（sha `db079daa1631a57b`・43,472 B・23:15）⇒ 依裁定線 2257 做完四處改字，本線曾抄入",
    "> - **seq=4**（sha `312156a895d4fe12`・45,700 B・09-24 01:50）⇒ ⭐ 含 §九⑧（§六⑤ 前提不成立）",
    ">   ⇒ ⭐ 本節即為 **seq=4** 的轉載（⛔ 舊版轉載已整節切掉，不並存）",
    "",
] + sec2 + [
    "",
    "---",
    "",
] + sec9 + [
    "",
    "---",
    "",
    "### ⭐ 回測線註：上面 §九 的 ⑦ 與 ⑧ 都是本線答出來的，⛔ 本線不再另加補註",
    "",
    "```",
    "⭐ seq=2／seq=3 時本線曾在這裡加過兩段補註（0.96pp 與 §六⑤ 的前提）。",
    "⇒ ✅ seq=4 已經把兩件【都收進 §九 正文】（⑦ 與 ⑧，並逐字引用本線的答案）",
    "⇒ ⭐⭐ 所以本線把補註【拿掉】—— ⛔ 同一件事不要在兩個地方各寫一次，",
    "  ⚠ 那正是本專案一貫避免的「第二個權威來源」。",
    "⇒ 出處：本線 20260923-2245（P14 不再平衡＋拆解）、20260923-2324（B(t)＝甲）",
    "```",
    "",
])

_no_unrendered(block)   # ⛔ 不過就中止，⛔ 不寫檔
open(REPORT, "a", encoding="utf-8").write(block)
print("✅ 已接到 {}（＋{:,} 位元組）".format(REPORT, len(block.encode("utf-8"))))
print("   新 sha256[:16] ＝ {}".format(
    hashlib.sha256(open(REPORT, "rb").read()).hexdigest()[:16]))

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
WANT = "0333b2a16203e95a"
SRCPAT = "解讀全文-P17結論解讀與結案措辭_策略線_seq2_*"
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
    raise SystemExit("⛔ P17_REPORT.md 已經有結案節 ⇒ 停止（⛔ 不重複接）")

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
    "> sha16 **{}**（本線已重算相符：去檔尾 pw1 行 ⇒ rstrip+\\n ⇒ UTF-8 ⇒ sha256 前 16）",
    "> 轉載時戳：2026-09-23 22:50（台北）｜轉載工具：`backtest/append_verdict.py`",
    ">",
    "> ⚠ 沿革：策略線 2220 曾投遞 seq=1（sha 23b159c283b2896b），⭐ 已被本 seq=2 取代",
    ">   ⇒ ⛔ 本線第一次要抄時 sha 對不上，正是因此 ⇒ ⭐ 所以才有這一行。",
    "",
] + sec2 + [
    "",
    "---",
    "",
] + sec9 + [
    "",
    "---",
    "",
    "### ⚠ 回測線對上面 §九⑦ 的一句補註（⛔ 不改上面任何一字）",
    "",
    "```",
    "上面 §九⑦ 寫「§五 5-2 那 0.96pp 在回測線回答之前【不可引用】」。",
    "⇒ ✅ 本線已於 20260923-2245 回答：P14 的 blend 期初一次配置、之後【不再平衡】，",
    "   且【不收成本】⇒ 答案是策略線事前寫死的 (Ⅰ)。",
    "   ・不再平衡 −34.16%（⭐ 與 P14 交件值相同 ⇒ 沒有其他口徑殘差）",
    "   ・月度再平衡・成本 0 −33.18%　・月度再平衡・含成本 −33.20%（＝ W_fix，錨點 200/200 逐位元）",
    "   ⇒ 再平衡毛效果 +0.98pp／成本 −0.02pp／淨 +0.95pp",
    "⛔ 而本線【沒有】宣告「再平衡有效」：一個 w 格、一個窗、一種頻率、無檢定、無登錄。",
    "⏳ 該限制要不要解除，⭐ 由策略線在下一份解讀裡處置，⛔ 本線不自行解除。",
    "```",
    "",
])
open(REPORT, "a", encoding="utf-8").write(block)
print("✅ 已接到 {}（＋{:,} 位元組）".format(REPORT, len(block.encode("utf-8"))))
print("   新 sha256[:16] ＝ {}".format(
    hashlib.sha256(open(REPORT, "rb").read()).hexdigest()[:16]))

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
WANT = "db079daa1631a57b"
SRCPAT = "解讀全文-P17結論解讀與結案措辭_策略線_seq3_*"
SEQ = "seq=3"
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
    "> 版本：**{}**｜轉載工具：`backtest/append_verdict.py`（⭐ 它會先驗 sha16，對不上就拒絕動檔）".format(SEQ),
    ">",
    "> ⚠ 沿革（⭐ 逐版留著，⛔ 不要只留最新的）：",
    "> - seq=1（sha `23b159c283b2896b`・33,428 B・22:18）⇒ ⛔ 已作廢，本線【沒有】抄它",
    ">   ⇒ ⭐ 本線第一次要抄時 sha 對不上才發現它已被取代 —— 這就是「抄之前先對 sha」擋到的那一次",
    "> - seq=2（sha `0333b2a16203e95a`・36,763 B・22:28）⇒ ✅ 裁定線 2257 過目通過，本線曾抄入",
    "> - **seq=3**（sha `db079daa1631a57b`・43,472 B・23:15）⇒ ⭐ 依裁定線 2257 做完四處改字",
    ">   ⇒ ⭐ 本節即為 seq=3 的轉載（⛔ 舊的 seq=2 轉載已整節切掉，不並存）",
    "",
] + sec2 + [
    "",
    "---",
    "",
] + sec9 + [
    "",
    "---",
    "",
    "### ⚠ 回測線的兩句補註（⛔ 不改上面任何一字）",
    "",
    "```",
    "① §九⑦ 的 0.96pp 引用限制 ⇒ ✅ **已由台股策略線 20260923-2318 §三 解除**",
    "   本線 20260923-2245 的答案：P14 的 blend 期初一次配置、之後【不再平衡】且【不收成本】",
    "   ⇒ 答案是事前寫死的 (Ⅰ)。",
    "   ・不再平衡 −34.16%（⭐ 與 P14 交件值相同 ⇒ 兩件之間沒有其他口徑殘差）",
    "   ・月度再平衡・成本 0 −33.18%　・月度再平衡・含成本 −33.20%（＝ W_fix，錨點 200/200 逐位元）",
    "   ⇒ 再平衡毛效果 +0.98pp／成本 −0.02pp／淨 +0.95pp",
    "   ⛔⛔ 解除之後只能當【描述量】，而且三個範圍要一起抄：",
    "      ⛔ 一個窗　⛔ 一個 w 格（0.50）　⛔ 一種再平衡頻率（月頻）",
    "   ⛔⛔「再平衡有效」仍然【不可以寫】—— 沒有檢定、沒有 CI、沒有事前登錄。",
    "",
    "② §六⑤「0050 內扣費用未計」那條限制的【前提】⇒ ⭐ 本線 20260923-2325 已答：",
    "   B(t) ＝ **(甲) 0050 這一檔 ETF 的還原收盤**，⛔ 不是台灣50 指數。",
    "   證據：`data.load_stock(\"0050\",\"twse\",cal)` 讀 `data/stocks/0050.csv`（ETF 自己的成交價），",
    "        並套 `load_adj(\"0050\")` 的 23 筆還原事件（配息已還原回去）。",
    "   ⇒ ⭐ ETF 的成交價本來就是扣完內扣費用之後的 ⇒ 兩腳（W0 與 R_eq 的 0050 那一半）",
    "     都已經含它 ⇒ ⏳ §六⑤ 的處置由台股策略線與裁定線定，⛔ 本線不自行撤銷限制。",
    "```",
    "",
])
open(REPORT, "a", encoding="utf-8").write(block)
print("✅ 已接到 {}（＋{:,} 位元組）".format(REPORT, len(block.encode("utf-8"))))
print("   新 sha256[:16] ＝ {}".format(
    hashlib.sha256(open(REPORT, "rb").read()).hexdigest()[:16]))

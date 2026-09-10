#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chtm_probe.py — 上櫃「變更交易／分盤交易／管理股票」與融資成數調整的端點探針。

⛔ 只測不寫資料。開發容器對交易所一律 403（我方閘道）——看 Actions 的結果。

## 兩支都是情報分析線 2026-09-10 18:00 那封給的

### ① ⭐⭐ `afterTrading/chtm`（上櫃）—— 比上市那支 `TWT85U` 好用

上市只有 `TWT85U` 一欄 `**`（要自己從「變更交易」推「有沒有分盤」）。
⭐ 上櫃這一支**四個狀態各一欄**，而且**直接給撮合循環時間**：

    證券代號／證券名稱／變更交易／分盤交易／屬管理股票
    ／分盤或管理股票撮合循環時間(分鐘)／停止交易／財務資訊重點專區

⚠ 情報分析線實測值有 `030` 與 `045` 兩種（3629 地心引力 030、3664 安瑞-KY 045）
⇒ ⭐ **「30 分鐘」不是固定值，也不是全市場一致** ⇒ ⛔ 判讀裡不可以寫死常數。
（官方 `TWT85U` 的 notes 自己也說「每 30 分鐘為原則，**並得視交易情形公告調整**」。）

⛔ **而它有一種靜默失敗**：情報分析線實測 `date=104/01/05` → 36 列 ✅，
但 `date=98/06/01` **靜靜回今天**（頁面宣稱 97/04/09 起提供，那個日期不可信）。
⇒ 這支探針**逐位元組比對**「越界那一天」與「今天」的回應：
⭐ **一樣 ⇒ 就是靜默回今天**，⛔ 不是「那天沒有資料」。

### ② `marginTrading/BFIB9U`（上市）—— 個股融資成數的**調整幅度**

K線線那條 166.67 的基準值：官方明文「最高融資比率 60%、最低融券保證金成數 90%」
（⚠ 那是**上櫃頁面**的字，上市那一半還沒有逐字 ⇒ ⛔ 先不要套過去）。

⛔ 而 `BFIB9U` 給的是**調整幅度**不是現行成數（值長成 `1`／`6`／`累計：2`），
⚠ 而且**同一檔會因不同原因出現多列** ⇒ 要逐檔彙總再用「基準 − 累計調整」推。
⇒ 這支探針要回答的是：值到底長什麼樣、同一檔會不會重複、有沒有歷史。

## ⛔ 在看到真回應之前不寫 parser

這條規矩今天已經換到兩次回報（借券靠官方 `groups` 解掉段落歧義、
`suspendListing` 的 `status` 是同一站的**第三種**成功旗標寫法）。
"""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import backfill as B

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_chtm_probe.txt")

TP = "https://www.tpex.org.tw/www/zh-tw"
TW = "https://www.twse.com.tw/rwd/zh"

_TODAY = datetime.now(TPE)
_ROC_TODAY = f"{_TODAY.year - 1911}/{_TODAY.month:02d}/{_TODAY.day:02d}"

# ⚠ 民國斜線。⛔ 三個日期各有各的角色，不是隨便挑的：
CHTM_DAYS = [
    ("104/01/05", "⭐ 情報分析線實測回 36 列 ⇒ **有歷史**的證據"),
    ("098/06/01", "⛔ 越界：情報分析線說它**靜靜回今天** ⇒ 本探針要逐位元組證實"),
    (_ROC_TODAY, "對照組：今天（⚠ 越界那一份要跟這一份比）"),
]


def _chtm(day):
    return f"{TP}/afterTrading/chtm?date={day}&response=json"


def probe(label, url, want, out):
    """→ 原始 bytes（拿不到回 None）。⭐ 第一件事一律是攤開全部頂層鍵。"""
    out.append(f"── {label}")
    out.append(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=45)
    if err:
        gw = ("Tunnel connection failed" in str(err)
              or "connect_rejected" in str(err))
        out.append(f"   ✗ {str(err)[:200]}"
                   + ("　⚠ **這是我方閘道擋的**（Actions 上會是通的）" if gw else ""))
        return None
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:                                       # noqa: BLE001
        out.append(f"   ✗ 不是 JSON（{type(e).__name__}）；bytes={len(raw)}；"
                   f"前 200：{raw[:200]!r}")
        return raw
    out += ["   " + s for s in B.describe_response(d, want=want)]
    if isinstance(d, dict):
        out.append(f"   頂層 `fields`：{d.get('fields')}")
    tabs = B._tables(d)
    out.append(f"   `_tables()` 認出 {len(tabs)} 張表")
    for t in tabs[:2]:
        f = [str(x) for x in (t.get("fields") or [])]
        data = t.get("data") or []
        out.append(f"     欄位（{len(f)}）：{f}")
        out.append(f"     列數：{len(data)}")
        for r in data[:4]:
            out.append(f"       樣本：{json.dumps(r, ensure_ascii=False)[:240]}")
        # ⭐ 每一欄出現過哪些相異值——這才看得出「分盤交易」欄是 V／●／1 還是別的
        if data and isinstance(data[0], list):
            for i, name in enumerate(f):
                vals = sorted({str(r[i]).strip() for r in data
                               if isinstance(r, list) and len(r) > i})
                if len(vals) <= 12:
                    out.append(f"     ⭐ 欄 {i}「{name}」的相異值（{len(vals)}）：{vals}")
                else:
                    out.append(f"     欄 {i}「{name}」：{len(vals)} 種相異值，"
                               f"前 8：{vals[:8]}")
    return raw


def main():
    out = ["# 上櫃 chtm（變更交易／分盤／管理股票）與 BFIB9U（融資成數調整）探針",
           "# ⛔ 只測不寫資料。開發容器對交易所一律 403（我方閘道）——看 Actions 的結果",
           "# ⛔ 在看到真回應之前不寫 parser。",
           ""]

    blobs = {}
    for day, why in CHTM_DAYS:
        blobs[day] = probe(f"上櫃 chtm｜date={day}　{why}", _chtm(day),
                           {"date": day}, out)
        out.append("")

    # ══════════════════════════════════════════════════════════
    # ⭐⭐ 這一節才是這支探針的重點：**「越界」與「那天沒有資料」分得開嗎**
    #
    # ⚠ 兩者都會回一份看起來正常的 JSON。唯一分得開的方法是
    #   **拿越界那一份跟「今天」那一份逐位元組比**：
    #   一樣 ⇒ 它根本沒看我送的日期。
    # ⛔ 比「列數」不夠——列數一樣可能只是巧合。
    # ══════════════════════════════════════════════════════════
    over, today = blobs.get("098/06/01"), blobs.get(_ROC_TODAY)
    out.append("── ⭐⭐ 越界那一天 vs 今天：逐位元組比")
    if over is None or today is None:
        out.append("   ⚠ 有一邊沒拿到 ⇒ **不可判定**（⛔ 不要寫成「沒問題」）")
    elif over == today:
        out.append(f"   ⛔ **完全相同（{len(over)} bytes）⇒ 它靜靜回今天**"
                   "　⚠ 那表示越界時它不會說失敗 ⇒ 回補時要自己驗日期")
    else:
        out.append(f"   ✅ 不同（越界 {len(over)}B vs 今天 {len(today)}B）"
                   "　⇒ 越界**不是**靜默回今天，可以靠回應本身分辨")
    out.append("")

    probe("上市 融資成數調整 BFIB9U（不帶日期，看它回什麼）",
          f"{TW}/marginTrading/BFIB9U?startDate=&endDate=&sortType=ALL"
          "&stockNo=&selectType=%E5%85%A8%E9%83%A8&response=json", {}, out)
    out.append("")
    probe("上市 融資成數調整 BFIB9U｜2015-01-05（⚠ 情報分析線說回 126 列）",
          f"{TW}/marginTrading/BFIB9U?startDate=20150105&endDate=20150105"
          "&sortType=ALL&stockNo=&selectType=%E5%85%A8%E9%83%A8&response=json",
          {"startDate": "20150105"}, out)
    out.append("")

    out += [
        "## ⇒ 拿到結果之後要回答的",
        "  Q1 `chtm` 的欄名**逐字**是什麼（我方要拿它當唯一的守衛）？",
        "  ⭐ Q2 「分盤交易」欄的值長什麼樣（V／●／1／空白）？",
        "     ⚠ 而且要看**相異值清單**——⛔ 借券那件的教訓：",
        "       分類欄可能是**複合的**（`XV` 比單獨的 `X` 還多），",
        "       只看第一列會以為它是單一值，寫成 `== 'V'` 會漏掉一整群。",
        "  ⭐ Q3 「撮合循環時間」的相異值有幾種（情報分析線看到 030／045）？",
        "     ⇒ 只要**不只一種**，判讀裡就不可以寫死 30 分鐘。",
        "  ⛔ Q4 越界那一天是不是靜默回今天（上面那一節逐位元組回答）？",
        "  Q5 `BFIB9U` 的值形狀（`1`／`6`／`累計：2`）與**同一檔是否多列**？",
        "     ⛔ 它給的是**調整幅度**不是現行成數 ⇒ 落地前要先確定彙總規則。",
        "  ⚠ Q6 `BFIB9U` 不帶日期時回的是「今天」還是「全部」？",
        "     ⛔ 若是靜默回今天，逐日回補要自己驗日期（跟 Q4 同一族）。",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[chtm_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

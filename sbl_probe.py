#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sbl_probe.py — 借券賣出（SBL）的端點探針。⛔ 只測不寫資料。

## 為什麼開這一支（K線線 2026-09-10 15:45 列為**第一優先**）

情報分析線量出來的：

    借券賣出是融券的 **77.5 倍**（2002 中鋼差 3,225 倍）
    缺口逐年惡化：2015 是 9.2 倍 → 2026 是 72.7 倍
    ⇒ **融券現在只佔空方的 1.4%**

⇒ K線線的 `券資比 = 融券餘額 ÷ 融資餘額` **分子只涵蓋空方的 1.4%**，
⛔ 而「券資比低 ＝ 空方壓力小」是拿那 1.4% 對整體下結論。
⚠ 偏誤方向**單一**：借券賣出越集中的股票（大型權值股、外資愛用），
判讀就越樂觀。⭐ 而且它**不會炸、不會缺值、不會有人抱怨**——
券資比一直算得出來，只是量錯對象，而且**十一年來一直如此、逐年變壞**。

## ⛔ 這一支不寫 parser，它只回答「端點長什麼樣」

照 `docs/NEW_ENDPOINT.md` 的順序：
**第 0 步先把回應整個攤開**（`describe_response`），⛔ 不是先去比對數字。
候選路徑是**推**出來的（照同站其他端點的模式）——⚠ 這一支就是用來淘汰它們的。

## ⚠ 兩件情報分析線 10:22 已經講明、要在這裡驗的

1. **`TWT93U` 每日晚間二次更新（約 20:30 與 22:30）**
   ⇒ ⛔ 排程若落在兩次之間，拿到的是**不完整**的版本，⚠ 而它看起來完全正常。
   ⇒ 這一支要印出回應自述的時間／日期，讓人判得出拿到哪一版。
2. **上櫃 `margin/sbl` 是「兩張表併在一起」**（title 是「信用額度總量管制餘額表」）：
   前段融券、後段借券，⛔ **兩段的「前日餘額」「當日餘額」欄名重複**
   ⇒ 只看欄名一定取錯，要照**兩段**取。

## ⭐ 還要回答 K線線的 Q2

**「當日可借券賣出限額」與「借券賣出餘額」不是同一個量，不可互換。**
⇒ 這一支要把**兩個欄位都印出來**，並標明哪個是哪個。
"""
import io
import json
import os
import sys

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_sbl_probe.txt")

DAY = "2026-09-09"
YMD = DAY.replace("-", "")
SLASH = DAY.replace("-", "/")
TW = "https://www.twse.com.tw/rwd/zh"
TP = "https://www.tpex.org.tw/www/zh-tw"

# ⚠ 這些路徑是**照同站其他端點的模式推的**，⛔ 不是實測過的。
#   第三個元素是「我送出去的參數」——`describe_response(want=…)` 靠它對 `params` 回顯。
CANDIDATES = [
    ("上市 借券賣出餘額 TWT93U（selectType=SLBNLB）",
     f"{TW}/marginTrading/TWT93U?date={YMD}&selectType=SLBNLB&response=json",
     {"date": YMD, "selectType": "SLBNLB"}),
    ("上市 借券賣出餘額 TWT93U（selectType=ALL）",
     f"{TW}/marginTrading/TWT93U?date={YMD}&selectType=ALL&response=json",
     {"date": YMD, "selectType": "ALL"}),
    ("上市 借券賣出餘額 TWT93U（不帶 selectType）",
     f"{TW}/marginTrading/TWT93U?date={YMD}&response=json",
     {"date": YMD}),
    ("上櫃 信用額度總量管制餘額表 margin/sbl",
     f"{TP}/margin/sbl?date={SLASH}&id=&response=json",
     {"date": SLASH}),
    ("上櫃 margin/sbl（不帶 id）",
     f"{TP}/margin/sbl?date={SLASH}&response=json",
     {"date": SLASH}),
]


def _rows(d):
    """→ (fields, data)。⛔ 只取第一張表，其餘照樣印出來讓人看得到。"""
    tabs = B._tables(d)
    if not tabs:
        return [], []
    t = tabs[0]
    return [str(x) for x in (t.get("fields") or [])], (t.get("data") or [])


def probe(label, url, want, out):
    out.append(f"── {label}")
    out.append(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=45)
    if err:
        # ⛔ 我方閘道的 403 與交易所的 403 意思**相反**，要分得出來
        gw = ("Tunnel connection failed" in str(err)
              or "connect_rejected" in str(err))
        out.append(f"   ✗ {err[:200]}"
                   + ("　⚠ **這是我方閘道擋的**，不是端點的問題"
                      "（Actions 上會是通的）" if gw else ""))
        return
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:                                       # noqa: BLE001
        out.append(f"   ✗ 不是 JSON（{type(e).__name__}）；"
                   f"bytes={len(raw)}；前 200：{raw[:200]!r}"
                   "　⚠ 回 HTML 多半是被 CDN 擋，或路徑根本不存在")
        return
    # ⭐ 規矩第一條：先把**全部頂層鍵**攤開，再看資料本身
    out += ["   " + s for s in B.describe_response(d, want=want)]
    fields, data = _rows(d)
    out.append(f"   欄位（{len(fields)}）：{fields}")
    out.append(f"   資料列數：{len(data)}")
    for r in data[:2]:
        out.append(f"     樣本：{r}")

    # ⭐ K線線 Q2：「餘額」與「限額」是兩個量，⛔ 不可互換 ⇒ 兩個都指出來
    bal = [i for i, f in enumerate(fields) if "餘額" in f]
    lim = [i for i, f in enumerate(fields) if "限額" in f]
    out.append(f"   ⭐ 含「餘額」的欄：{[(i, fields[i]) for i in bal]}")
    out.append(f"   ⚠ 含「限額」的欄：{[(i, fields[i]) for i in lim]}"
               "　⛔ 限額 ≠ 餘額，兩者不可互換（K線線 Q2）")
    if len(bal) > 2:
        out.append("   ⛔ **「餘額」欄不只一個** ⇒ 多半是『兩張表併在一起』"
                   "（前段融券、後段借券，欄名重複）"
                   "⇒ ⚠ 只看欄名一定取錯，要照**兩段**取。")


def main():
    out = [f"# 借券賣出（SBL）端點探針　目標日 {DAY}",
           "# ⛔ 只測不寫資料。在開發容器裡跑一定失敗（我方閘道對交易所 403）——看 Actions 的結果",
           "# ⚠ 候選路徑是**照同站其他端點的模式推的**，這一支就是用來淘汰它們的。",
           ""]
    for label, url, want in CANDIDATES:
        try:
            probe(label, url, want, out)
        except Exception as e:                                   # noqa: BLE001
            out.append(f"   ✗ 探針自己炸了：{type(e).__name__}: {e}")
        out.append("")
    out += [
        "## ⇒ 拿到結果之後要回答的四題（K線線 15:45）",
        "  Q1 借券賣出**餘額**有沒有可自動取得的來源？逐檔逐日嗎？回到哪一年？",
        "  Q2 拿到的是「當日可借券賣出**限額**」還是「借券賣出**餘額**」？⛔ 兩者不可互換",
        "  Q3 上櫃那一側有沒有對應來源？",
        "  ⚠ 另外：`TWT93U` 每日晚間**二次更新**（約 20:30／22:30）"
        "⇒ 排程落在兩次之間會拿到不完整的版本，而它看起來完全正常。",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[sbl_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

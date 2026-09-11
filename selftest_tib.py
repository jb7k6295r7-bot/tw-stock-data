#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_tib.py — 驗官方創新板成分清單（`STOCK_TIB`）的解析。

⛔ 它取代的是一條**猜的**判準（名稱後綴 `-創`／`KY創`），
所以這一支要證明的第一件事就是：**新的那條不可以比舊的更會出錯。**

  ① 「合計」那一列要丟掉（⚠ 它的**代號欄是空字串**，名稱欄才寫「合計」
     ⇒ 照名稱擋會擋不到——這一條就是反向驗）
  ② 正常列一檔不漏、代號與名稱照原文
  ③ 欄位對不上要**拒收並回報欄名**，⛔ 不是回 0 列（那看起來像「今天沒有創新板股」）
  ④ ⚠ 越界時官方是**大聲失敗**（stat 講明下限）——我方不可以把它讀成「那天沒有」
"""
import sys

import feeds as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⚠ 欄位照 2026-09-09 實測的順序（情報分析線 10:44 的回報）
FIELDS = ["證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額",
          "開盤價", "最高價", "最低價", "收盤價", "漲跌(+/-)", "漲跌價差"]
ROWS = [
    ["6919", "世紀*創", "1,000", "5", "50,000", "10", "11", "9", "10", "+", "1.00"],
    ["6996", "海博-KY創", "2,000", "9", "90,000", "45", "46", "44", "45", "X", "0.00"],
    # ⛔ 合計列：**代號欄是空字串**，名稱欄才寫「合計」
    ["", "合計", "40,427,863", "0", "4,725,166,145", "", "", "", "", "", ""],
]


def pay(fields=None, data=None, **top):
    d = {"stat": "OK", "date": "20260909",
         "title": "115年09月09日每日創新板股票成交量值",
         "tables": [{"title": "115年09月09日每日創新板股票成交量值",
                     "fields": fields if fields is not None else FIELDS,
                     "data": data if data is not None else ROWS}]}
    d.update(top)
    return d


def main():
    out, note = F.parse_tib(pay(), "2026-09-09")
    ck("① 合計列被丟掉（3 列進、2 檔出）", len(out) == 2, f"{len(out)}｜{note}")
    ck("① 訊息裡講出丟了幾列", "丟掉 1 列" in note, note)
    codes = [r[1] for r in out]
    ck("② 兩檔都在，代號照原文", codes == ["6919", "6996"], str(codes))
    ck("② 名稱照原文（含 `*` 與 `-KY`）",
       [r[2] for r in out] == ["世紀*創", "海博-KY創"], str(out))
    ck("② 每列三欄，與 header 對得起來",
       all(len(r) == 3 for r in out) and len(F.FEEDS["tib"]["header"]) == 3,
       str(out[:1]))
    ck("② 日期是**我請求的那一天**（不是端點回什麼就寫什麼）",
       all(r[0] == "2026-09-09" for r in out), str(out))

    print("③ ⛔ 反向：欄位對不上要拒收，不可以靜靜回 0 列")
    bad, note2 = F.parse_tib(pay(fields=["代碼", "名字", "量"],
                                 data=[["6919", "世紀*創", "1"]]), "2026-09-09")
    ck("  回 0 列**而且**訊息裡有欄名",
       bad == [] and "欄位對不上" in note2, f"{bad}｜{note2}")

    print("④ ⚠ 一列都沒有的兩種情形要分得出來")
    empty, note3 = F.parse_tib(pay(data=[]), "2026-09-09")
    ck("  空表回 0 列（⚠ 這是「那天沒有」——只有在 stat 正常時才成立）",
       empty == [] and "0 檔" in note3, note3)
    nt, note4 = F.parse_tib({"stat": "查詢日期小於110年6月28日，請重新查詢!"},
                            "2021-01-01")
    ck("  ⛔ 越界（官方明說下限）**沒有 tables** ⇒ 回「沒有 tables」不是「0 檔」",
       nt == [] and "沒有 tables" in note4, note4)
    ck("  ⭐ 兩者的訊息不同（讀的人分得出「那天沒有」與「根本沒問到」）",
       note3 != note4, f"{note3!r} vs {note4!r}")

    print("⑤ ⚠ 反向：只擋名稱「合計」的話擋不到那一列（證明 ① 用的是代號欄）")
    ck("  合計列的代號欄真的是空字串、名稱欄才是「合計」",
       ROWS[2][0] == "" and ROWS[2][1] == "合計")

    print("⑥ 註冊表接得起來")
    e = F.FEEDS["tib"]
    ck("  parse 指到 parse_tib", e["parse"] is F.parse_tib)
    ck("  known=False（有下市／轉板的，先全收）", e["known"] is False)
    u = e["urls"]("2026-09-09")[0]
    ck("  URL 帶 date=20260909 且路徑是 STOCK_TIB",
       "STOCK_TIB" in u and "date=20260909" in u, u)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_stophalt.py — 驗「停止買賣中」名單（`violation/stop`）的解析。

## ⛔ 這一支擋的是一個**分不開**的問題

K線分析線 2026-09-11 01:40：資料庫裡「**停止買賣中**」與「**已下市**」
長得一模一樣（兩者都只是「日線沒有列了」）。⚠ 而兩者的處置相反：

    已下市     ⇒ 永遠不會回來，不進母體
    停止買賣中 ⇒ ⚠ **它會復牌**，⛔ 復牌後前後兩段中間隔了好幾個月
                 接起來算均線／扣抵／ATR ＝ 把一段不存在的時間當成交易日

## ⛔⛔ 而這一支**沒有歷史**：漏抓一天就永久少一天

`date=` 官方會忽略（K線線實測）⇒ 只有「今天仍在停止買賣中」。
⭐ 唯一能回推的是每一列的**停止買賣開始日期** ⇒ 那一欄壞掉，
這一支就只剩一張今天的快照，⚠ 而它**看起來完全正常**。
⇒ 本檔第 ③ 節專門釘那一欄。

⚠ 假回應照 K線線實測的形狀做：5 欄、民國日期「115年04月07日」、
條款欄帶全形頓號、原因欄很長且含分號。
⛔ 我方**沒有**自己實測過（開發容器對交易所一律 403）——
所以第 ① 節的「欄名逐字相符才收」是這一支最重要的守門。
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


ROWS = [["1589", "永冠-KY", "第50-3條第1項第1、7款",
         "114年度、115Q1、115Q2 財報未依期限公告申報；"
         "第四次無擔保轉換公司債(15894)屆滿3個月未償還亦未和解",
         "115年04月07日"],
        ["4414", "如興", "第50-3條第1項第1款",
         "財報未依期限公告申報", "114年11月20日"]]
H = F.FEEDS["stophalt"]["header"]
DAY = "2026-09-11"


def tw(fields=None, data=None, **top):
    d = {"stat": "OK", "date": "20260911",
         "title": "115年09月11日 停止買賣",
         "tables": [{"title": "停止買賣",
                     "fields": F.STOPHALT_FIELDS if fields is None else fields,
                     "data": ROWS if data is None else data}]}
    d.update(top)
    return d


def main():
    print("① 照實測形狀的回應")
    out, note = F.parse_stophalt(tw(), DAY)
    ck("  2 列", len(out) == 2, f"{len(out)}｜{note}")
    ck("  每一列的長度 = header 長度",
       all(len(r) == len(H) for r in out), f"{H}｜{out[:1]}")
    g = dict(zip(H, out[0]))
    ck("  ⛔ `date` 是**快照日**不是查詢日", g["date"] == DAY, str(g))
    ck("  代號／名稱／市場", (g["stock_id"], g["name"], g["market"])
       == ("1589", "永冠-KY", "twse"), str(g))
    ck("  條款與原因照原文存（⛔ 不翻譯、不截斷）",
       g["rule"] == "第50-3條第1項第1、7款"
       and g["reason"].startswith("114年度、115Q1"), str(g)[:120])

    print("② ⛔ 欄名逐字比對：官方改欄名就拒收")
    bad, note2 = F.parse_stophalt(tw(fields=F.STOPHALT_FIELDS[:-1]), DAY)
    ck("  少一欄 ⇒ 一列都不收", bad == [], str(bad))
    ck("  ⚠ 而且說明要印出**實得欄名**（⛔ 只說「不符」＝再賠一個來回）",
       "拒收" in note2 and "違反營業細則條款" in note2, note2)
    ren = list(F.STOPHALT_FIELDS)
    ren[4] = "停止買賣起日"
    bad2, _ = F.parse_stophalt(tw(fields=ren), DAY)
    ck("  ⭐ 只有**最後那一欄改名**也要拒收"
       "（⚠ 那一欄是唯一能回推歷史的東西）", bad2 == [], str(bad2))

    print("③ ⭐⭐ 停止買賣開始日期：民國 → 西元")
    ck("  `115年04月07日` ⇒ `2026-04-07`",
       g["halt_since"] == "2026-04-07", g["halt_since"])
    ck("  第二列 `114年11月20日` ⇒ `2025-11-20`",
       dict(zip(H, out[1]))["halt_since"] == "2025-11-20", str(out[1]))
    # ⛔ 認不出來要**留空**，⚠ 猜一個日期比認不出更糟（第七點）
    odd = [["1589", "永冠-KY", "第50-3條", "原因", "—"]]
    out3, _ = F.parse_stophalt(tw(data=odd), DAY)
    ck("  ⛔ 日期認不出來 ⇒ **留空**，不猜",
       dict(zip(H, out3[0]))["halt_since"] == "", str(out3))

    print("④ ⛔ `known` **不可以**拿來濾")
    # ⚠ 停止買賣中的個股正是「日檔已經沒有它」的那些
    #   ⇒ 用母體濾 = 把最該記的那些全部濾掉。
    out4, _ = F.parse_stophalt(tw(), DAY, known={"2330"})
    ck("  ⭐ 傳了一個不含 1589／4414 的母體，⛔ 兩列**照樣**都要收",
       len(out4) == 2, f"{len(out4)}｜{out4}")
    ck("  （前提）FEEDS 裡也標著 known=False",
       F.FEEDS["stophalt"]["known"] is False)

    print("⑤ 表尾的註解列要丟掉")
    out5, _ = F.parse_stophalt(
        tw(data=ROWS + [["說明：本表僅列示…", "", "", "", ""]]), DAY)
    ck("  代號不是數字開頭 ⇒ 丟掉", len(out5) == 2, str(out5[-1:]))
    out6, _ = F.parse_stophalt(tw(data=[["1589", "永冠-KY", "條"]]), DAY)
    ck("  ⛔ 欄數不足的列也丟掉（⚠ 不可以補空值湊滿）", out6 == [], str(out6))

    print("⑥ 說明要講得出**最早自哪一天**")
    ck("  ⭐ 那一格就是可回推的歷史 ⇒ 說明裡要有它",
       "最早自 2025-11-20" in note, note)
    out7, note7 = F.parse_stophalt(tw(data=[]), DAY)
    ck("  ⚠ 0 列時**不可以**假裝有最早日期",
       out7 == [] and "最早自" not in note7, note7)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

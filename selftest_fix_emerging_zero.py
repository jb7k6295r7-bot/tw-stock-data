#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_fix_emerging_zero.py — 驗興櫃 0 價列的修復。

⛔ 這一支要證明的重點**不是「0 有沒有被清掉」**，是
**從那個 0 算出來的 `change` 有沒有一起被清掉**。

K線線 2026-09-10 14:55：那一格才是真正咬人的地方——
一根 −31.6% 的長黑會同時觸發跌破均線、長黑 K、單日停損、爆量下跌，
⛔ **它是一個完整的、會通過所有型別檢查的假出場訊號。**
⭐ 通則：**壞掉的來源欄會沿著「用它算出來的欄位」擴散，而下游只看到後者。**
"""
import sys

import fix_emerging_zero as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


H = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
     "change,limit,shares,transactions,price_basis").split(",")


def row(code, market, close, chg="", basis="", vol="0", amt="0", lim=""):
    d = dict.fromkeys(H, "")
    d.update({"key": f"2026-09-09_{code}", "date": "2026-09-09",
              "stock_id": code, "name": "N", "market": market,
              "close": close, "change": chg, "volume": vol, "amount": amt,
              "limit": lim, "price_basis": basis, "high": close, "low": close})
    return [d[h] for h in H]


def main():
    i = {h: H.index(h) for h in H}
    body = [
        row("7849", "emerging", "0", "-139.50", "均價/額推算"),        # ⭐ 中招
        row("6857", "emerging", "0.00", "-90.00", "均價/額推算"),      # ⭐ 中招（"0.00"）
        row("1260", "emerging", "30.81", "0.27", "均價/額推算"),       # 正常興櫃，不可動
        row("2330", "twse", "0", "-10.00", ""),                        # ⚠ 上市的 0，不歸這支管
        row("6904", "tpex", "", "", "無成交"),                          # 已經是無成交
    ]
    n, samples = F.fix_body(H, body)
    ck("① 只改中招的 2 列", n == 2, str(n))

    print("② ⭐ 重點：`change` 有沒有一起被清掉（衍生欄位）")
    ck("  7849 的 -139.50 被清掉", body[0][i["change"]] == "", body[0][i["change"]])
    ck("  6857 的 -90.00 被清掉", body[1][i["change"]] == "", body[1][i["change"]])
    ck("  ⚠ 而且訊息裡留得下樣本（讓人看得到當初編了什麼）",
       sorted(samples) == ["-139.50", "-90.00"], str(samples))

    print("③ 價格欄清空、`price_basis` 改成 `無成交`")
    for k in ("open", "high", "low", "close", "limit"):
        ck(f"  {k} 清空", body[0][i[k]] == "", body[0][i[k]])
    ck("  price_basis = 無成交", body[0][i["price_basis"]] == "無成交",
       body[0][i["price_basis"]])
    ck("  ⛔ 而不是留著 `均價/額推算`（照 price_basis 篩會篩進來）",
       body[0][i["price_basis"]] != "均價/額推算")

    print("④ ⛔ volume／amount **不動**（照官方原文）")
    ck("  volume 還是 0", body[0][i["volume"]] == "0", body[0][i["volume"]])
    ck("  amount 還是 0", body[0][i["amount"]] == "0", body[0][i["amount"]])

    print("⑤ ⛔ 反向：三種**不可以**被動到的列")
    ck("  正常興櫃（close=30.81）一格都沒變",
       body[2][i["close"]] == "30.81" and body[2][i["change"]] == "0.27"
       and body[2][i["price_basis"]] == "均價/額推算", str(body[2]))
    ck("  ⚠ **上市**的 close=0 不歸這支管（它不是興櫃的無成交）",
       body[3][i["close"]] == "0" and body[3][i["change"]] == "-10.00",
       str(body[3]))
    ck("  已經是「無成交」的列不會被重複處理（n 沒把它算進去）", n == 2)

    print("⑥ ⚠ 判零一定要走 `_isz`（`\"0.00\"` 是 truthy）")
    ck("  `_isz('0.00')` 是 True", F._isz("0.00") is True)
    ck("  ★ 反向：若用 `not close` 判，`'0.00'` 會**漏掉**"
       "（證明 ① 抓到第二列不是碰巧）", bool("0.00") is True)

    print("⑦ 缺欄位時回 None（⛔ 不是靜靜跳過）")
    n2, _ = F.fix_body(["date", "close"], [["2026-09-09", "0"]])
    ck("  回 None", n2 is None, str(n2))

    print("⑧ ⚠ 空字串的 close 不算 0（那是「沒有值」不是「值是 0」）")
    b2 = [row("9999", "emerging", "", "", "無成交")]
    n3, _ = F.fix_body(H, b2)
    ck("  不動它", n3 == 0, str(n3))

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

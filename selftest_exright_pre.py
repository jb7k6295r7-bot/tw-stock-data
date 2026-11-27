#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_exright_pre.py — 除權除息預告表的解析與合併（不連外、不寫 runlog）。

假回應照 2026-11-27 本機實測的形狀做：上市 stat/fields/data（list）、民國中文日期；
上櫃 openapi list of dict、民國 7 碼連寫、除權息寫「除息」。

要證明：
  ① 兩市場日期換算對、kind 統一成 權／息／權息
  ② ETF「待公告實際收益分配金額」⇒ cash_div 留空、原文進 note（⛔ 不寫 0）
  ③ 上市 stat 不是 OK／欄位變了 ⇒ 整份判不可用（⛔ 不是安靜回 0 列）
  ④ 合併：first_seen 留最早、last_seen 更新、值取本趟；本趟沒有的舊列不刪
  ⑤ 日期認不出 ⇒ 進 bad 並講得出是哪一列
"""
import json
import sys

import exright_pre as X

ok = fail = 0


def t(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  ✗    {label}　{detail}")


TW_FIELDS = ['除權除息日期', '股票代號', '名稱', '除權息', '無償配股率', '現金增資配股率', '現金增資認購價', '現金股利',
             '詳細資料', '參考價<br>試算', '最近一次申報資料 季別/日期', '最近一次申報每股 (單位)淨值', '最近一次申報每股 (單位)盈餘']
tw = {"stat": "OK", "title": "除權除息預告表", "fields": TW_FIELDS, "data": [
    ['115年12月08日', '00400A', '主動國泰動能高息', '息', '0.00000000', '0.00000000', '0.00000000',
     '<p style= text-align:center;>待公告實際收益分配金額</p>', '00400A,20261208', '', '', '0.00', ''],
    ['115年12月01日', '00939', '統一台灣高息動能', '息', '0.00000000', '0.00000000', '0.00000000', '0.15000000',
     '00939,20261201', '', '', '21.81', 'N/A'],
    ['115年12月03日', '2330', '台積電', '權息', '0.05000000', '0.00000000', '0.00000000', '5.00000000', '', '', '', '', ''],
]}
rows, bad, err = X.parse_twse(json.dumps(tw, ensure_ascii=False).encode("utf-8"))
t("① 上市 3 列、沒有錯", len(rows) == 3 and not bad and not err, f"{len(rows)} {bad} {err}")
r0 = {r["stock_id"]: r for r in rows}
t("① 上市日期 115年12月08日 → 2026-12-08", r0["00400A"]["ex_date"] == "2026-12-08", r0["00400A"]["ex_date"])
t("① kind 權息 原樣", r0["2330"]["kind"] == "權息")
t("② 待公告 ⇒ cash_div 空白", r0["00400A"]["cash_div"] == "", r0["00400A"]["cash_div"])
t("② 待公告原文進 note", "待公告實際收益分配金額" in r0["00400A"]["note"], r0["00400A"]["note"])
t("② 正常現金股利保留", r0["00939"]["cash_div"] == "0.15000000" and r0["00939"]["note"] == "")

bad_stat = dict(tw, stat="很抱歉，沒有符合條件的資料!")
_, _, e1 = X.parse_twse(json.dumps(bad_stat, ensure_ascii=False).encode("utf-8"))
t("③ stat 不是 OK ⇒ 整份不可用", bool(e1), e1)
bad_f = dict(tw, fields=[f for f in TW_FIELDS if f != "現金股利"])
_, _, e2 = X.parse_twse(json.dumps(bad_f, ensure_ascii=False).encode("utf-8"))
t("③ 欄位少了現金股利 ⇒ 整份不可用", bool(e2) and "現金股利" in e2, e2)

tp = [{'ExRrightsExDividendDate': '1151118', 'SecuritiesCompanyCode': '00758B', 'CompanyName': '復華能源債',
       'ExRrightsExDividend': '除息', 'StockDividendRatio': '0.00000000', 'SubscriptionRatioToNewSharesIssued': '0.00000000',
       'SubscriptionPricePerShare': '0.00', 'CashDividend': '0.62000000', 'AllocatedForPublicUnderwriting': '0'},
      {'ExRrightsExDividendDate': '11513', 'SecuritiesCompanyCode': '9999', 'CompanyName': '壞日期',
       'ExRrightsExDividend': '除權', 'StockDividendRatio': '0.1', 'SubscriptionRatioToNewSharesIssued': '0',
       'SubscriptionPricePerShare': '0', 'CashDividend': '0'}]
rows2, bad2, err2 = X.parse_tpex(json.dumps(tp, ensure_ascii=False).encode("utf-8"))
t("① 上櫃 1151118 → 2026-11-18、除息 → 息", len(rows2) == 1 and rows2[0]["ex_date"] == "2026-11-18"
  and rows2[0]["kind"] == "息" and rows2[0]["market"] == "tpex", str(rows2))
t("⑤ 壞日期進 bad 並講得出代號", len(bad2) == 1 and "9999" in bad2[0], str(bad2))
_, _, e3 = X.parse_tpex(b'{"error":"busy"}')
t("③ 上櫃不是 list ⇒ 整份不可用", bool(e3), e3)

old = [dict(rows2[0], first_seen="2026-11-10", last_seen="2026-11-20"),
       {"ex_date": "2026-11-01", "stock_id": "1101", "name": "台泥", "market": "twse", "kind": "息",
        "stock_div_ratio": "0", "capinc_ratio": "0", "capinc_price": "0", "cash_div": "1.0", "note": "",
        "first_seen": "2026-10-20", "last_seen": "2026-10-31"}]
newer = [dict(rows2[0], cash_div="0.70000000")]
m = X.merge(old, newer, "2026-11-27")
mb = {(r["market"], r["stock_id"]): r for r in m}
r = mb[("tpex", "00758B")]
t("④ first_seen 留最早", r["first_seen"] == "2026-11-10", r["first_seen"])
t("④ last_seen 更新成今天", r["last_seen"] == "2026-11-27", r["last_seen"])
t("④ 值取本趟", r["cash_div"] == "0.70000000", r["cash_div"])
t("④ 本趟沒有的舊列不刪、原封不動", mb.get(("twse", "1101"), {}).get("last_seen") == "2026-10-31", str(mb.get(("twse", "1101"))))
m2 = X.merge([], rows, "2026-11-27")
t("④ 新列 first_seen＝今天", all(x["first_seen"] == "2026-11-27" for x in m2))

print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
sys.exit(1 if fail else 0)

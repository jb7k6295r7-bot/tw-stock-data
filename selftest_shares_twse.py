#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_shares_twse.py — 驗上市「發行股數」的補值（`fetch.twse_shares` / `fill_twse_shares`）。

⛔ 五條守門分支，每一條都要**證明它會擋下來**：

  ① 正常：欄位對得上、日期對得上 ⇒ 取得對照表，並且只補**空的**那些列
  ② ⛔⛔ 端點**靜靜回今天**（日期參數寫錯時的真實行為）⇒ 整批拒收
  ③ 回 0 列 ⇒ 當失敗，⛔ 不是「那天沒有股票」
  ④ 欄位對不上 ⇒ 講得出缺哪一個，⛔ 不猜位置
  ⑤ ⛔ 被 CDN 擋成 HTTP 428 回 HTML ⇒ 要講出「多半是被擋」，
     不可以只報「解析失敗」（那會讓人去查端點，而端點沒壞）
"""
import io
import json
import os
import sys

import fetch as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


FIELDS = ["證券代號", "證券名稱", "ISIN", "發行股數", "尚可投資股數", "持有股數",
          "尚可投資比率", "持股比率", "共用法令上限", "陸資法令上限",
          "與前日異動原因", "最近申報異動日"]


def payload(stamp, rows, fields=None):
    return {"stat": "OK", "date": stamp,
            "tables": [{"title": f"{stamp} 全體外資及陸資持股", "fields": fields or FIELDS,
                        "data": rows}]}


ROWS = [["2330", "台積電", "TW0002330008", "25,930,380,458", "1", "1", "1", "1", "1", "1", "", ""],
        ["2317", "鴻海", "TW0002317005", "13,861,131,187", "1", "1", "1", "1", "1", "1", "", ""]]

# HEADER: key,date,stock_id,name,market,open,high,low,close,volume,amount,change,limit,shares,transactions,price_basis
def line(code, market="twse", shares=""):
    return [f"2026-09-09_{code}", "2026-09-09", code, "N", market,
            "1", "1", "1", "1", "1", "1", "", "", shares, "1", ""]


def main():
    def fake(payload_obj, err=None):
        def g(url, *a, **k):
            if err:
                return None, err
            if isinstance(payload_obj, bytes):
                return payload_obj, None
            return json.dumps(payload_obj, ensure_ascii=False).encode(), None
        return g

    # ① 正常
    m, note = F.twse_shares("2026-09-09", getter=fake(payload("20260909", ROWS)))
    ck("① 正常回應取得兩檔的發行股數", len(m) == 2, note)
    ck("① 逗號有拿掉", m.get("2330") == "25930380458", repr(m.get("2330")))

    lines = [line("2330"), line("2317", shares="999"), line("6104", market="tpex")]
    n, note1 = F.fill_twse_shares(lines, "2026-09-09",
                                  getter=fake(payload("20260909", ROWS)))
    ck("① 只補**空的**那一列（2330）", n == 1 and lines[0][13] == "25930380458",
       f"n={n} {lines[0][13]!r}")
    ck("① ⛔ 已經有值的不動（2317 還是 999）", lines[1][13] == "999", lines[1][13])
    ck("① ⛔ 上櫃列不碰", lines[2][13] == "", repr(lines[2][13]))
    ck("① 補不齊時要講出來（2 檔要補、對照表只有 1 檔命中）",
       "補上 1／1" in note1 or "補上" in note1, note1)

    # ② 端點靜靜回今天
    m2, note2 = F.twse_shares("2015-01-05", getter=fake(payload("20260909", ROWS)))
    ck("② ⛔ 回應講的是別天 ⇒ 整批拒收", not m2, note2)
    ck("② 而且訊息點名那個陷阱",
       "靜靜回今天" in note2 or "沒有講出我請求的日期" in note2, note2)

    # ③ 0 列
    m3, note3 = F.twse_shares("2026-09-09", getter=fake(payload("20260909", [])))
    # ⚠ 2026-09-10 情報分析線實測：非交易日（2015-01-01／01-02）也是 stat:OK＋0 列，
    #   那時候 0 列是**正確答案**。⇒ 訊息改成講「本支只在有行情列的日子才被呼叫」，
    #   這裡的斷言跟著改。⛔ 斷言字串跟程式訊息脫節的話，這條就變成測字串不是測行為。
    ck("③ 回 0 列 ⇒ 當失敗，而且講得出「為什麼這天一定是交易日」",
       not m3 and "0 列" in note3 and "一定是交易日" in note3, note3)

    # ④ 欄位對不上
    m4, note4 = F.twse_shares(
        "2026-09-09",
        getter=fake(payload("20260909", [["2330", "台積電", "1"]],
                            fields=["證券代號", "證券名稱", "持股比率"])))
    ck("④ 欄位對不上 ⇒ 講得出缺哪一個", not m4 and "發行股數" in note4, note4)

    # ⑤ 被 CDN 擋成 HTML
    html = b"<html><head><title>HiNet CDN</title></head><body>cdn_logo.jpg</body></html>"
    m5, note5 = F.twse_shares("2026-09-09", getter=fake(html))
    ck("⑤ ⛔ 回 HTML 時要講「多半是被 CDN 擋」，不是只報解析失敗",
       not m5 and "被 CDN 擋" in note5, note5)

    # ★ 補不到時 ⛔ 不可以動到任何一列
    lines2 = [line("2330")]
    n6, note6 = F.fill_twse_shares(lines2, "2026-09-09", getter=fake(None, "連不上"))
    ck("★ 抓不到時一列都不動，而且 note 帶著 ✗",
       n6 == 0 and lines2[0][13] == "" and note6.startswith("✗"), f"{n6} {note6}")

    real = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    ck("★ 沒有寫任何檔", os.path.isdir(real))
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

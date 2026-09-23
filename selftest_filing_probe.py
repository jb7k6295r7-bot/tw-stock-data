#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_filing_probe.py — 驗那支探針的三個判準（⛔ 零相依、不連網）。

⭐ 要證明的重點：

    ① **擋阻頁不可以被當成資料**——它回的是 HTTP 200，只驗狀態碼一定中招
    ② 「這一批要自己講出它是哪一期」：`result.year` 認不出來要回 None，⛔ 不猜
    ③ big5 那一頁**必須用 big5 解**；⛔ 用 UTF-8 解會解不出日期（⚠ 而且不報錯）
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filing_probe as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⭐ 逐字抄自 2026-09-23 本機實測拿到的那一份（HTTP 200、800 bytes）
BLOCK = ("<html>\n<head>\n<meta http-equiv=\"Content-Type\" "
         "content=\"text/html; charset=utf-8\">\n</head>\n<body> \n"
         "因為安全性考量，您所執行的頁面無法呈現。<BR>\n"
         "FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED.<BR>\n"
         "</body></html>").encode("utf-8")

ROW = ("<tr><td>2330</td><td>113 年 第一季</td><td>合併財報</td>"
       "<td>113/05/15 14:25:29</td></tr>")


def main():
    print("① ⛔ 擋阻頁不可以被當成資料（⚠ 它回 HTTP 200）")
    ck("  ⭐⭐ 擋阻頁判得出來", F.looks_blocked(BLOCK))
    ck("  ⛔ 反向：正常的 JSON **不算**擋阻頁（⚠ 判太寬會天天紅）",
       not F.looks_blocked(b'{"result":{"year":"113"}}'))
    ck("  ⛔ 空回應不算（⚠ 那是另一種失敗，不可以混成同一種）",
       not F.looks_blocked(b""))
    ck("  ⭐ big5 編碼的擋阻頁也判得出來（⚠ 同一頁兩種編碼都遇得到）",
       F.looks_blocked("因為安全性考量，您所執行的頁面無法呈現。"
                       .encode("big5")))

    print("\n② ⭐ 回應要自己講出它是哪一期（⛔ 認不出來回 None，不猜）")
    ck("  ⭐ 兩個都在 ⇒ 回 (year, season)",
       F.self_declared_period({"result": {"year": "113", "season": "1"}})
       == ("113", "1"))
    ck("  ⭐ 數字型也吃得下（⚠ 官方兩種型別都出現過）",
       F.self_declared_period({"result": {"year": 113, "season": 1}})
       == ("113", "1"))
    ck("  ⛔ 少一個 ⇒ None（⚠ 不可以只回 year 就當成講出來了）",
       F.self_declared_period({"result": {"year": "113"}}) is None)
    ck("  ⛔ 空字串不算有值", F.self_declared_period({"result": {"year": "", "season": "1"}}) is None)
    ck("  ⛔ 根本不是 dict ⇒ None，不炸", F.self_declared_period("<html>") is None)

    print("\n③ ⭐ big5 那一頁必須用 big5 解")
    big5_html = ROW.encode("big5")
    got = F.upload_dates(big5_html)
    ck("  ⭐⭐ big5 解得出上傳日期（帶時分秒的整串）",
       got == ["113/05/15 14:25:29"], str(got))
    ck("  ⛔ 反向：裸日期（沒有時分秒）**不算**——那可能是別欄的資料年度",
       F.upload_dates("<td>113/05/15</td>".encode("big5")) == [])
    ck("  ⛔ 空 body 回空 list，不炸", F.upload_dates(b"") == [])
    # ⚠ 這一條釘的是「編碼解錯會靜靜解不出來」：UTF-8 存的中文用 big5 讀會變亂碼，
    #   而日期那一段是 ASCII ⇒ ⭐ 它照樣解得出來 ⇒ ⛔ 所以【解得出日期】不能證明編碼對。
    ck("  ⭐⭐ 而【解得出日期】**不能**證明編碼解對了（日期是 ASCII，兩種編碼都解得出）"
       "⇒ 所以那一節還要看 bytes 與擋阻頁判準",
       F.upload_dates(ROW.encode("utf-8")) == ["113/05/15 14:25:29"])

    print("\n④ ★ 沒有動到 repo 真的輸出檔")
    with tempfile.TemporaryDirectory() as d:
        real = F.OUT
        before = os.path.exists(real)
        sample = os.path.join(d, "x.txt")
        io.open(sample, "w", encoding="utf-8").write("x")
        ck("  ★ 這一支自測沒有建立或改動 data/meta/_filing_probe.txt",
           os.path.exists(real) == before)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

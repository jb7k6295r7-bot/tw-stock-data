# -*- coding: utf-8 -*-
"""selftest_filing_dates.py — t57sb01 上傳日期解析（⛔ 不連網；列內容取自 2026-09-27 實測 2330／1342 民國 113）。

  ① 正常頁：逐列解出代號、西元年、季、檔別、上傳時間（民國 → 西元）
  ② 自述不符（別家／別年的列）⇒ 整發 bad，⛔ 不收
  ③ 擋阻頁（HTTP 200）⇒ bad；沒有「上傳日期」表頭 ⇒ bad；有表頭 0 列 ⇒ empty
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filing_dates as FD

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    OK += bool(cond)
    FAIL += not cond
    print(("  ok   " if cond else "  ✗    ") + name + ("" if cond else f"　⇒ {hint}"))


def page(rows):
    head = "<table><tr><th>公司代號</th><th>資料年度</th><th>上傳日期</th></tr>"
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (head + body + "</table>").encode("big5")


R2330 = [["2330", "113 年 第一季", "財務報告書", "", "", "IFRSs合併財報", "", "202401_2330_AI1.pdf", "8,048,457", "113/05/15 14:25:29", "無"],
         ["2330", "113 年 第四季", "財務報告書", "", "", "IFRSs個體財報", "", "202404_2330_AI3.pdf", "8,558,423", "114/02/27 14:03:03", "無"]]
R1342 = [["1342", "113 年 第一季", "財務報告書", "", "", "IFRSs個別財報", "", "202401_1342_AI2.pdf", "1,305,118", "113/05/09 10:54:03", "無"]]


def main():
    print("① 正常頁")
    rows, st, _ = FD.parse(page(R2330), "2330", 113)
    ck("status ok、2 列", st == "ok" and len(rows) == 2, (st, rows))
    ck("第一列：2330 2024 Q1 AI1 2024-05-15 14:25:29", rows and rows[0][:4] == ["2330", "2024", "1", "AI1"]
       and rows[0][7] == "2024-05-15 14:25:29", rows[:1])
    ck("Q4 年報上傳日在隔年：2025-02-27", len(rows) > 1 and rows[1][2] == "4" and rows[1][7].startswith("2025-02-27"), rows[1:])
    ck("bytes 去千分位", rows and rows[0][6] == "8048457", rows[:1])
    rows, st, _ = FD.parse(page(R1342), "1342", 113)
    ck("個別財報 AI2 照收", st == "ok" and rows[0][3] == "AI2", rows)

    print("② 自述不符 ⇒ bad")
    rows, st, note = FD.parse(page(R2330), "2317", 113)
    ck("別家的列 ⇒ bad、0 列", st == "bad" and not rows, (st, note))
    rows, st, note = FD.parse(page(R2330), "2330", 112)
    ck("別年的列 ⇒ bad、0 列", st == "bad" and not rows, (st, note))

    print("③ 擋阻頁／非正常頁／空頁")
    rows, st, _ = FD.parse("因為安全性考量，您所執行的頁面無法呈現".encode("big5"), "2330", 113)
    ck("擋阻頁 ⇒ bad", st == "bad")
    rows, st, _ = FD.parse("<html>維護中</html>".encode("big5"), "2330", 113)
    ck("沒有上傳日期表頭 ⇒ bad", st == "bad")
    rows, st, _ = FD.parse(page([]), "2330", 113)
    ck("有表頭 0 列 ⇒ empty", st == "empty" and not rows, st)
    rows, st, _ = FD.parse(b"", "2330", 113)
    ck("空回應 ⇒ bad", st == "bad")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

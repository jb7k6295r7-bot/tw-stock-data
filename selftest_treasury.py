# -*- coding: utf-8 -*-
"""selftest_treasury.py — 庫藏股 t35sc09 解析（⛔ 不連網；列內容取自 2026-09-28 實測上市第 1、2 件）。

  ① 正常頁：民國日期 → 西元、千分位去掉、20 格一列
  ② 序號跳號 ⇒ 整份不收（表格解析掉列會安靜少件）
  ③ 頁面自述區間 ≠ 請求 ⇒ 整份不收
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import treasury as T

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    OK += bool(cond)
    FAIL += not cond
    print(("  ok   " if cond else "  ✗    ") + name + ("" if cond else f"　⇒ {hint}"))


R1 = ["1", "1416", "廣豐", "89/08/09", "3", "316,685,349", "5,232,000", "0.00", "13.00", "89/08/10", "89/09/08",
      "Y", "", "5,232,000", "5,232,000", "100.00", "59,000,000", "11.28", "1.50", ""]
R2 = ["2", "2402", "毅嘉", "94/08/30", "1", "2,120,230,584", "10,000,000", "23.00", "35.00", "94/08/31", "94/10/30",
      "Y", "", "9,900,000", "9,900,000", "99.00", "277,122,608", "27.99", "3.38", "期限屆滿無法買回"]


def page(rows, said="089/01/01~115/12/31"):
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr><td>日期：{said}</td></tr>{body}</table>".encode("utf-8")


def main():
    print("① 正常頁")
    rows, note = T.parse(page([R1, R2]), "sii", "0890101", "1151231")
    ck("2 件、序號連續", len(rows) == 2 and "1～2" in note, note)
    ck("決議日 89/08/09 → 2000-08-09", rows[0][4] == "2000-08-09", rows[0][:6])
    ck("預定股數去千分位", rows[1][7] == "10000000", rows[1][:8])
    ck("預定期間轉西元", rows[1][10] == "2005-08-31" and rows[1][11] == "2005-10-30", rows[1][10:12])
    ck("列寬＝表頭", all(len(r) == len(T.HEADER) for r in rows))
    print("② 跳號 ⇒ 不收")
    R3 = list(R2)
    R3[0] = "3"
    try:
        T.parse(page([R1, R3]), "sii", "0890101", "1151231")
        ck("跳號被擋", False, "沒丟例外")
    except ValueError as e:
        ck("跳號被擋", "序號不連續" in str(e), str(e))
    print("③ 自述區間不符 ⇒ 不收")
    try:
        T.parse(page([R1, R2], said="100/01/01~115/12/31"), "sii", "0890101", "1151231")
        ck("區間不符被擋", False, "沒丟例外")
    except ValueError as e:
        ck("區間不符被擋", "自述區間" in str(e), str(e))
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

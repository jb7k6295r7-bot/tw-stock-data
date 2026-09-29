# -*- coding: utf-8 -*-
"""selftest_mops_news.py — 重大訊息 t05st02 解析（⛔ 不連網；列取自 2026-09-29 實測 115/09/25 那一發）。

  ① 正常：民國日期轉西元、主旨去換行、市場別與序號取自 parameters
  ② 發言日期不在查詢日往前 7 天內 ⇒ 整發不收
  ③ code≠200：406／查無 ⇒ empty；其他 ⇒ bad；表頭不對 ⇒ bad
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mops_news as M

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    OK += bool(cond)
    FAIL += not cond
    print(("  ok   " if cond else "  ✗    ") + name + ("" if cond else f"　⇒ {hint}"))


TITLES = [{"sub": [], "main": x} for x in ("發言日期", "發言時間", "公司代號", "公司名稱", "主旨", "詳細資料")]
ROW = ["115/09/24", "17:30:18", "3711", "日月光投控", "代子公司矽品精密工業(股)公司公告\r\n取得營業用機器設備達十億元",
       {"apiName": "t05st02_detail", "parameters": {"marketKind": "sii", "companyId": "3711", "serialNumber": 2,
                                                     "enterDate": "1150924"}}]


def J(rows, code=200, msg="查詢成功", titles=TITLES):
    return {"code": code, "message": msg, "result": {"titles": titles, "data": rows}}


def main():
    print("① 正常")
    rows, st, _ = M.parse(J([ROW]), "2026-09-25")
    ck("status ok、1 則", st == "ok" and len(rows) == 1, (st, rows))
    ck("日期 115/09/24 → 2026-09-24（查 09-25 回前一天晚上）", rows[0][0] == "2026-09-24", rows[0])
    ck("主旨換行壓成空白", "\r" not in rows[0][6] and "公告 取得" in rows[0][6], rows[0][6])
    ck("市場別 sii、序號 2", rows[0][4] == "sii" and rows[0][5] == "2", rows[0])
    print("② 自述日期超出 7 天 ⇒ 不收")
    old = list(ROW)
    old[0] = "115/09/10"
    rows, st, note = M.parse(J([ROW, old]), "2026-09-25")
    ck("整發 bad、0 列", st == "bad" and not rows, (st, note))
    print("③ code 與表頭")
    ck("406 ⇒ empty", M.parse(J([], code=406, msg="查無相符資料"), "2026-09-25")[1] == "empty")
    ck("500 傳入參數異常 ⇒ bad", M.parse(J([], code=500, msg="傳入參數異常"), "2026-09-25")[1] == "bad")
    ck("表頭不對 ⇒ bad", M.parse(J([ROW], titles=[{"main": "別的"}]), "2026-09-25")[1] == "bad")
    ck("200 但 0 列 ⇒ empty", M.parse(J([]), "2026-09-25")[1] == "empty")
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

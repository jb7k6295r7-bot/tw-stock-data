# -*- coding: utf-8 -*-
"""curated/insider_holding/build.py 的離線自測（零相依、不連網）：解析、守門、年月不符、表頭不符、格數不符。"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "curated", "insider_holding"))
import build as B  # noqa: E402

H110 = """<html><body>[IRB110]
<table><tr><td>資 料 年 月 : 11408</td><td>資 料 日 期 :114/09/17</td></tr>
<tr><td>公 司 名 稱</td><td>實 際 發 行 股 票 總 額</td><td>董 事 、 監 察 人 本 月 份</td><td>佔 股 份 總 額 %</td>
<td>經理人本月份 實際持有股數</td><td>百分之十以上 大股東本月份 實際持有股數</td></tr>
<tr><td>增 加 股 數</td><td>減 少 股 數</td><td>實 際 持 有 股 數</td></tr>
<tr><td>1101臺灣水泥股份有限</td><td>7,751,181,742</td><td>0</td><td>0</td><td>610,082,625</td><td>7.87</td><td>11,163,290</td><td>0</td></tr>
<tr><td>674191APP股份有限</td><td>50,000,000</td><td>1,000</td><td>0</td><td>9,000,000</td><td>18.00</td><td>0</td><td>0</td></tr>
</table></body></html>"""

H130 = """<html><body>[IRB130]
<table><tr><td>資 料 年 月 : 11408</td><td>資 料 日 期 :114/09/17</td></tr>
<tr><td>公 司 名 稱</td><td>董 事 、 監 察 人 本 月 份</td><td>佔 持 股 比 例 %</td><td>經理人本月份 實際持有股數</td>
<td>百分之十以上 大股東本月份 實際持有股數</td><td>經理人及百分 之十以上大股 東已設定股數</td><td>佔 持 股 比 例 %</td></tr>
<tr><td>實 際 持 有 股 數</td><td>設 定 股 數</td><td>解 除 股 數</td><td>累 計 設 定 股 數</td></tr>
<tr><td>1108幸福水泥股份有限</td><td>16,004,841</td><td>0</td><td>0</td><td>0</td><td>0.00</td><td>238,914</td><td>52,996,034</td><td>45,310,000</td><td>85.11</td></tr>
</table></body></html>"""

ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print("✗", name)


def raises(name, fn):
    try:
        fn()
    except RuntimeError:
        check(name, True)
        return
    check(name, False)


pub, rows = B.parse(H110, "2025-08", "110")
check("110 發布日＝表頭資料日期", pub == "2025-09-17")
check("110 兩列", len(rows) == 2)
check("110 去千分位", rows[0][5:] == ["7751181742", "0", "0", "610082625", "7.87", "11163290", "0"])
check("110 代號取前 4 碼（91APP 不吃進代號）", rows[1][3] == "6741")
check("110 欄數＝BASE＋cols", len(rows[0]) == len(B.BASE) + len(B.KINDS["110"]["cols"]))
pub, rows = B.parse(H130, "2025-08", "130")
check("130 一列", len(rows) == 1)
check("130 經理人大股東質押比", rows[0][-1] == "85.11" and rows[0][-2] == "45310000")
check("130 欄數", len(rows[0]) == len(B.BASE) + len(B.KINDS["130"]["cols"]))
raises("年月不符要拒", lambda: B.parse(H110, "2025-07", "110"))
raises("拿 130 表頭讀 110 要拒", lambda: B.parse(H110, "2025-08", "130"))
raises("格數不符要拒", lambda: B.parse(H110.replace("<td>0</td></tr>", "</tr>", 1), "2025-08", "110"))
raises("數字欄壞要拒", lambda: B.parse(H110.replace("7.87", "N/A"), "2025-08", "110"))
raises("0 列要拒", lambda: B.parse(H130.replace("1108幸福", "合計幸福"), "2025-08", "130"))
raises("發布日不在資料年月之後要拒", lambda: B.parse(H110.replace("114/09/17", "114/08/17"), "2025-08", "110"))
pub, rows = B.parse(H130.replace("1108幸福水泥股份有限</td>", "1108幸福水泥(?/TD>"), "2025-08", "130")
check("官方壞標籤 ?/TD> 修回後格數照常", len(rows) == 1 and rows[0][5] == "16004841")
check("cp950 逐段解碼：半個字不吃掉 <", B.decode("<td>1626\xa6\xe3\xac</td><td>1</td>".encode("latin-1")).count("<") == 4)
check("指紋：同內容同值", B.fingerprint(B.parse(H110, "2025-08", "110")[1]) == B.fingerprint(B.parse(H110, "2025-08", "110")[1]))
check("months 跨年", list(B.months("2025-11", "2026-02")) == ["2025-11", "2025-12", "2026-01", "2026-02"])
print(f"selftest_insider_holding：{ok}/{ok + fail} 通過")
sys.exit(1 if fail else 0)

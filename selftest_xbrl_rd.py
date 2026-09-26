# -*- coding: utf-8 -*-
"""selftest_xbrl_rd.py — XBRL 研發費用／營收解析（⛔ 不連網；數值取自 2330 2013Q2、2020Q4 實測）。

  ① XML 世代：本期單季、本期累計各取一次；去年同期 context 不收
  ② inline 世代：scale="3" ⇒ ×1000；sign="-" ⇒ 負；Q4 只有全年 ⇒ *_q 空
  ③ ⛔ 性質別明細 WagesAndSalaries-ResearchAndDevelopmentExpenses 不可被當成研發費用（完整 local name 比對）
  ④ 沒有研發費用列 ⇒ 鍵不存在（⛔ 不是 0）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xbrl_rd as X

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    OK += bool(cond)
    FAIL += not cond
    print(("  ok   " if cond else "  ✗    ") + name + ("" if cond else f"　⇒ {hint}"))


XML = """<xbrli:xbrl>
<tifrs-bsci-ci:ResearchAndDevelopmentExpenses contextRef="From20130401To20130630" unitRef="TWD" decimals="-3">11941871000</tifrs-bsci-ci:ResearchAndDevelopmentExpenses>
<tifrs-bsci-ci:ResearchAndDevelopmentExpenses contextRef="From20120401To20120630" unitRef="TWD" decimals="-3">10068390000</tifrs-bsci-ci:ResearchAndDevelopmentExpenses>
<tifrs-bsci-ci:ResearchAndDevelopmentExpenses contextRef="From20130101To20130630" unitRef="TWD" decimals="-3">22592856000</tifrs-bsci-ci:ResearchAndDevelopmentExpenses>
<tifrs-bsci-ci:WagesAndSalaries-ResearchAndDevelopmentExpenses contextRef="From20130401To20130630" unitRef="TWD" decimals="-3">999</tifrs-bsci-ci:WagesAndSalaries-ResearchAndDevelopmentExpenses>
<tifrs-bsci-ci:OperatingRevenue contextRef="From20130401To20130630" unitRef="TWD" decimals="-3">155886320000</tifrs-bsci-ci:OperatingRevenue>
<tifrs-bsci-ci:OperatingRevenue contextRef="From20130101To20130630" unitRef="TWD" decimals="-3">288641316000</tifrs-bsci-ci:OperatingRevenue>
</xbrli:xbrl>"""

IX = """<html><body>
<ix:nonFraction name="ifrs-full:Revenue" contextRef="From20200101To20201231" unitRef="TWD" decimals="-3" scale="3" format="ixt:numdotdecimal">1,339,254,811</ix:nonFraction>
<ix:nonFraction name="ifrs-full:Revenue" contextRef="From20190101To20191231" unitRef="TWD" decimals="-3" scale="3">1,069,985,448</ix:nonFraction>
<ix:nonFraction name="ifrs-full:ResearchAndDevelopmentExpense" contextRef="From20200101To20201231" unitRef="TWD" decimals="-3" scale="3">109,486,089</ix:nonFraction>
<ix:nonFraction name="tifrs-bsci-ci:WagesAndSalaries-ResearchAndDevelopmentExpenses" contextRef="From20200101To20201231" scale="3">7</ix:nonFraction>
</body></html>"""

NEG = """<ix:nonFraction name="ifrs-full:Revenue" contextRef="From20210701To20210930" scale="3" sign="-">1,000</ix:nonFraction>"""


def main():
    print("① XML 世代（2330 2013Q2）")
    f = X.facts(XML, 2013, 2)
    ck("研發 單季 11,941,871,000", f.get("rd_q") == 11941871000, f)
    ck("研發 累計 22,592,856,000", f.get("rd_ytd") == 22592856000, f)
    ck("營收 單季／累計", f.get("rev_q") == 155886320000 and f.get("rev_ytd") == 288641316000, f)
    print("② inline 世代（2330 2020Q4）")
    f = X.facts(IX, 2020, 4)
    ck("營收 全年 ×1000", f.get("rev_ytd") == 1339254811000, f)
    ck("研發 全年 ×1000", f.get("rd_ytd") == 109486089000, f)
    ck("Q4 沒有單季 context ⇒ *_q 不存在", "rd_q" not in f and "rev_q" not in f, f)
    ck("去年同期（2019）不收", f.get("rev_ytd") != 1069985448000, f)
    f = X.facts(NEG, 2021, 3)
    ck("sign=\"-\" ⇒ 負值", f.get("rev_q") == -1000000, f)
    print("③ 性質別明細不可當成研發費用")
    ck("XML：明細 999 沒有蓋掉本體", X.facts(XML, 2013, 2).get("rd_q") == 11941871000)
    only = XML.replace("tifrs-bsci-ci:ResearchAndDevelopmentExpenses ", "x:Other ").replace(
        "</tifrs-bsci-ci:ResearchAndDevelopmentExpenses>", "</x:Other>")
    ck("只有明細、沒有本體 ⇒ 研發鍵不存在", "rd_q" not in X.facts(only, 2013, 2), X.facts(only, 2013, 2))
    print("④ 沒有研發費用列")
    f = X.facts(IX.replace("ResearchAndDevelopmentExpense\"", "Nothing\""), 2020, 4)
    ck("⇒ rd 鍵不存在（⛔ 不是 0）", "rd_ytd" not in f and f.get("rev_ytd") == 1339254811000, f)
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

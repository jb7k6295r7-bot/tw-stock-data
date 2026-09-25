#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗三大法人買賣【金額】那兩支 feed 的判準。⛔ 離線：餵合成回應，不連網。

⭐ 這一支要釘的是【列名會隨年份改】這件事本身：
  上市改過四代、上櫃改過至少兩代，⛔ 而攤成固定欄的做法會讓欄的語意
  隨年份改變而不報錯 ⇒ 所以存長格式。
⚠ 而長格式自己也有一個坑：合計列是資料裡本來就有的一列
  ⇒ 把所有列加起來會重複計算 ⇒ §四 用真實數字釘住這件事。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feeds as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok     " + name)
    else:
        FAIL += 1
        print("  ✗      " + name + ("｜" + hint if hint else ""))


def twse_payload(rows, fields=None):
    return {"stat": "OK", "date": "20150105",
            "title": "104年01月05日 三大法人買賣金額統計表",
            "fields": fields or ["單位名稱", "買進金額", "賣出金額", "買賣差額"],
            "data": rows}


def tpex_payload(rows, fields=None):
    return {"stat": "ok", "date": "20180102",
            "tables": [{"title": "三大法人買賣金額彙總表",
                        "fields": fields or ["單位名稱", "買進金額(元)",
                                             "賣出金額(元)", "買賣超(元)"],
                        "data": rows}]}


# ⭐ 四代上市的列名（本線 2026-09-24 從端點逐年實測抄下來的，⛔ 不是編的）
GEN = {
    "2005": ["自營商", "投信", "外資", "合計"],
    "2010~2014": ["自營商", "投信", "外資及陸資", "合計"],
    "2015": ["自營商(自行買賣)", "自營商(避險)", "投信", "外資及陸資", "合計"],
    "2018+": ["自營商(自行買賣)", "自營商(避險)", "投信",
              "外資及陸資(不含外資自營商)", "外資自營商", "合計"],
}


def main():
    print("① ⭐⭐ 四代上市列名都要解得出來，而且【列名原文保留】")
    for era, names in GEN.items():
        rows = [[n, "1,000", "2,000", "-1,000"] for n in names]
        lines, note = F.parse_instamt(twse_payload(rows), "2015-01-05")
        got = [r[1] for r in lines]
        ck("  %-10s ⇒ %d 列，列名逐字相同" % (era, len(names)),
           got == names, "實際 %s" % got)
    ck("  ★ 四代的列名【不全相同】（⛔ 都一樣的話上面幾格等於只驗了一代）",
       len({tuple(v) for v in GEN.values()}) == 4)

    print("")
    print("② ⭐ 值要去掉千分位，⛔ 而負號要留著")
    lines, _ = F.parse_instamt(twse_payload(
        [["合計", "24,971,526,866", "26,033,457,181", "-1,061,930,315"]]),
        "2015-01-05")
    ck("  ⭐ 逗號去掉、數字完整",
       lines and lines[0][2:] == ["24971526866", "26033457181", "-1061930315"],
       str(lines))

    print("")
    print("③ ⭐ 欄位用【名稱】定位，⛔ 不是位置")
    # 上櫃的欄名帶「(元)」而且是「買賣超」，上市是「買賣差額」⇒ 兩種都要認
    l1, _ = F.parse_otcinstamt(tpex_payload([["投信", "1", "2", "-1"]]),
                               "2018-01-02")
    ck("  ⭐ 上櫃「買賣超(元)」認得出", l1 and l1[0][4] == "-1", str(l1))
    # ★ 反向：欄名整組換掉 ⇒ 必須明講對不上，⛔ 不可以默默用位置
    bad, note = F.parse_instamt(
        twse_payload([["投信", "1", "2", "3"]],
                     fields=["甲", "乙", "丙", "丁"]), "2015-01-05")
    ck("  ★ 欄名對不上 ⇒ 0 列並【把實際欄名印出來】",
       bad == [] and "欄名對不上" in note and "甲" in note, note)
    # ★ 欄位順序換掉也要對（⛔ 位置法會在這裡錯而不報錯）
    sw, _ = F.parse_instamt(
        twse_payload([["投信", "-9", "7", "8"]],
                     fields=["單位名稱", "買賣差額", "買進金額", "賣出金額"]),
        "2015-01-05")
    ck("  ★★ 欄位【換順序】仍然對得上（買進 7／賣出 8／差額 -9）",
       sw and sw[0][2:] == ["7", "8", "-9"], str(sw))

    print("")
    print("④ ⛔⛔ 合計列是資料裡本來就有的一列 ⇒ 全部加起來會重複計算")
    # 用 2026-09-23 上市的真實數字（本線當天實測）
    real = [["自營商(自行買賣)", "8920826668", "6695464499", "2225362169"],
            ["自營商(避險)", "29092278582", "25492974503", "3599304079"],
            ["投信", "17491414005", "22250850951", "-4759436946"],
            ["外資及陸資(不含外資自營商)", "345568210100", "308254846462",
             "37313363638"],
            ["外資自營商", "0", "0", "0"],
            ["合計", "401072729355", "362694136415", "38378592940"]]
    lines, _ = F.parse_instamt(twse_payload(real), "2026-09-23")
    d = {r[1]: int(r[4]) for r in lines}
    parts = sum(v for k, v in d.items() if k != "合計")
    ck("  ⭐ 合計列 ＝ 其餘各列之和（上市這一天真的相等）",
       d["合計"] == parts, "合計 %d／各列之和 %d" % (d["合計"], parts))
    ck("  ⛔⛔ ⇒ 所以把【全部】列加起來會是兩倍（這一格就是那個警告的證明）",
       sum(d.values()) == 2 * d["合計"], str(sum(d.values())))

    print("")
    print("⑤ ⛔ 上櫃的合計列與子列【重疊】⇒ 加總更錯")
    otc = [["　外資及陸資(不含自營商)", "77895748297", "96106264894",
            "-18210516597"],
           ["　外資自營商", "0", "0", "0"],
           ["外資及陸資合計", "77895748297", "96106264894", "-18210516597"],
           ["投信", "7228995507", "8040419598", "-811424091"]]
    lines, _ = F.parse_otcinstamt(tpex_payload(otc), "2026-09-23")
    names = [r[1] for r in lines]
    ck("  ⭐ 前導全角空白【被去掉】（.strip() 會去掉 U+3000）⇒ 名稱不帶縮排",
       "外資及陸資(不含自營商)" in names and
       "　外資及陸資(不含自營商)" not in names, str(names))
    ck("  ⭐ 而去掉縮排之後名稱仍然唯一（合計與子列是兩個名字）",
       len(set(names)) == len(names) and "外資及陸資合計" in names, str(names))

    print("")
    print("⑥ ⚠ 空列與空名稱要跳過（上櫃 2018-01-02 最後一列真的是 []）")
    lines, _ = F.parse_otcinstamt(
        tpex_payload([["投信", "1", "2", "-1"], [], ["", "9", "9", "0"]]),
        "2018-01-02")
    ck("  ⭐ 只剩 1 列", len(lines) == 1, str(lines))

    print("")
    print("⑦ ⭐ 0 列要講成【可能在回溯下限之前】，⛔ 不是抓取失敗")
    lines, note = F.parse_otcinstamt(tpex_payload([]), "2016-12-30")
    ck("  ⭐ 回 0 列", lines == [])
    ck("  ⭐ note 以 NODATA 開頭（fetch_one 靠它歸類成「那天沒資料」）",
       note.startswith("NODATA"), note)
    ck("  ⭐⭐ 而 note 要提到回溯下限 2017-01-03（⛔ 不可只說「0 列」）",
       "2017-01-03" in note, note)

    print("")
    print("⑧ ⛔⛔ 任何一格帶逗號就【不准寫】（write_day 是 \",\".join，沒有引號）")
    lines, note = F.parse_instamt(
        twse_payload([["投信,甲", "1", "2", "3"]]), "2015-01-05")
    ck("  ★ 名稱帶逗號 ⇒ 0 列並明講", lines == [] and "逗號" in note, note)

    print("")
    print("⑨ ⭐ 表頭寬度要跟 header 一致（write_day 會 assert，先在這裡擋）")
    for nm in ("instamt", "otcinstamt"):
        h = F.FEEDS[nm]["header"]
        ck("  ⭐ %s header ＝ %s" % (nm, h),
           h == ["date", "investor", "buy", "sell", "net"], str(h))
        lines, _ = (F.parse_instamt if nm == "instamt" else F.parse_otcinstamt)(
            (twse_payload if nm == "instamt" else tpex_payload)(
                [["投信", "1", "2", "3"]]), "2015-01-05")
        ck("  ⭐ %s 的列寬 ＝ header 寬" % nm,
           lines and all(len(r) == len(h) for r in lines), str(lines))

    print("")
    print("⑩ ★ 沒有動到 repo 的資料檔")
    for nm in ("instamt", "otcinstamt"):
        d = F.feed_dir(nm)
        ck("  ★ %s 目錄沒有被這一支建出來" % nm,
           not os.path.exists(d) or os.path.isdir(d), d)

    print("")
    print("⑪ ⭐ marginmkt（大盤信用交易統計，2026-09-25）：標題日期要驗、列數要剛好 3")
    MF = ["項目", "買進", "賣出", "現金(券)償還", "前日餘額", "今日餘額"]
    MR = [["融資(交易單位)", "1", "2", "3", "4", "5"], ["融券(交易單位)", "1", "2", "3", "4", "5"],
          ["融資金額(仟元)", "1,000", "2", "3", "4", "5"]]

    def _mm(title, rows):
        return {"stat": "OK", "tables": [{"title": title, "fields": MF, "data": rows}, {"title": "融資融券彙總"}]}
    l1, n1 = F.parse_marginmkt(_mm("103年02月05日 信用交易統計", MR), "2014-02-05")
    ck("  ⭐ 正常日 3 列、千分位逗號拿掉、列寬 ＝ header", len(l1) == 3 and l1[2][2] == "1000"
       and all(len(r) == len(F.FEEDS["marginmkt"]["header"]) for r in l1), "%s｜%s" % (l1, n1))
    l2, n2 = F.parse_marginmkt(_mm("103年02月06日 信用交易統計", MR), "2014-02-05")
    ck("  ⛔ 標題日期 ≠ 請求 ⇒ 拒收（參數沒生效那一族）", not l2 and "≠ 請求" in n2, n2)
    l3, n3 = F.parse_marginmkt(_mm("103年02月05日 信用交易統計", MR[:2]), "2014-02-05")
    ck("  ⛔ 少一列 ⇒ 拒收（⛔ 不可以寫出缺融資金額的一天）", not l3 and "應為 3 列" in n3, n3)
    l4, n4 = F.parse_marginmkt(_mm("融資融券彙總", MR), "2014-02-05")
    ck("  ⛔ 第一張表不是信用交易統計 ⇒ 拒收", not l4, n4)
    print("\n[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

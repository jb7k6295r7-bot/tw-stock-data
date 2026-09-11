#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_margin_note.py — 驗融資融券的官方**註記欄**（2026-09-10 新增 `note`）。

## 為什麼這一欄值得一支自測

K線線 2026-09-10 13:10 把它排到最高優先，⛔ 理由不是「少一欄」：

| 表面現象 | 意思 A（判讀規則現在假設的） | 意思 B（官方 `O`） |
|---|---|---|
| 融資餘額低、持續下降 | 槓桿已出清 ⇒ **偏正面** | 停止融資買進 ⇒ **偏負面** |

⇒ **一批負面訊號正在被讀成正面訊號**，而且專打飆股
（被停止融資的往往正是波動最大、最需要看融資水位的那一群）。

## ⛔ 這一欄的失效方式全部是安靜的，所以每一條都要有反向驗

    ① 位置取錯（TWSE 靠位置）⇒ 存進去的是「資券互抵」的數字
       ⚠ 看起來只是「這一欄大部分是空的」
    ② 走 `_blank_num()` ⇒ 文字被清成空字串，整欄空白
    ③ TPEx 找不到「備註」欄 ⇒ 整欄空白，跟「今天大家都沒有註記」一樣

⚠ 假回應照真回應的形狀做：TWSE **16 欄、欄名重複**，TPEx **20 欄、券賣在券買之前**。
"""
import sys

import feeds as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ── TWSE MI_MARGN：2026-09-04 Actions 實測的欄位，**逐字**照抄 ──
TW_F = ["代號", "名稱", "買進", "賣出", "現金償還", "前日餘額", "今日餘額",
        "次一營業日限額", "買進", "賣出", "現券償還", "前日餘額", "今日餘額",
        "次一營業日限額", "資券互抵", "註記"]
# 恆等式要成立：融資 今日 = 前日 + 買 − 賣 − 現償；融券 今日 = 前日 + 賣 − 買 − 券償
#            資買  資賣  現償  資前   資今   資限額   券買 券賣 券償 券前 券今 券限額 互抵 註記
TW_O = ["1447", "強新", "10", "5", "2", "100", "103", "9,999",
        "0", "0", "0", "50", "50", "9,999", "0", "O"]
TW_BLANK = ["2330", "台積電", "10", "5", "2", "100", "103", "9,999",
            "0", "0", "0", "50", "50", "9,999", "0", ""]

# ── TPEx margin/balance：20 欄，**券賣在券買之前** ──
OTC_F = ["代號", "名稱", "前資餘額(張)", "資買", "資賣", "現償", "資餘額",
         "資屬證金", "資使用率(%)", "資限額",
         "前券餘額(張)", "券賣", "券買", "券償", "券餘額", "券屬證金",
         "券使用率(%)", "券限額", "資券相抵(張)", "備註"]
OTC_X = ["6104", "創惟", "100", "10", "5", "2", "103", "0", "1.0", "9,999",
         "50", "0", "0", "0", "50", "0", "1.0", "9,999", "0", "X"]


def rows(fields, data, which):
    payload = {"tables": [{"title": "t", "fields": fields, "data": data}]}
    fn = F.parse_margin if which == "twse" else F.parse_otcmargin
    return fn(payload, "2026-09-09")


def main():
    print("① TWSE：註記存得下來，而且照官方原文")
    out, note = rows(TW_F, [TW_O, TW_BLANK], "twse")
    ck("  兩列都通過恆等式（假資料形狀對）", len(out) == 2, f"{len(out)} 列｜{note}")
    by = {r[1]: r for r in out}
    ck("  `1447` 的 note 是 'O'（⛔ 不是空的，也不是互抵那個 0）",
       by.get("1447", [""] * 14)[13] == "O", str(by.get("1447")))
    ck("  ⚠ 沒有註記的那一列是空字串（不是 '0'、不是 None）",
       by.get("2330", [""] * 14)[13] == "", repr(by.get("2330", [""] * 14)[13]))
    ck("  note 接在**最後一欄**（舊表頭是新表頭的前綴）",
       len(out[0]) == 14, f"{len(out[0])} 欄")

    print("② ⛔ 反向：位置取錯就要被守衛擋下來，不是靜靜存錯")
    bad_f = list(TW_F)
    bad_f[15] = "備註"          # 官方哪天把「註記」改叫「備註」
    out2, note2 = rows(bad_f, [TW_O], "twse")
    ck("  第 16 欄不叫「註記」⇒ 整張表拒收（⚠ 大聲失敗）",
       out2 == [] and "拒收" in note2, f"{len(out2)} 列｜{note2}")
    short_f = TW_F[:15]
    out3, note3 = rows(short_f, [TW_O[:15]], "twse")
    ck("  欄數不是 16 ⇒ 也拒收", out3 == [] and "拒收" in note3, note3)

    print("③ TPEx：靠欄名取「備註」")
    out4, note4 = rows(OTC_F, [OTC_X], "tpex")
    ck("  解得出 1 列", len(out4) == 1, f"{len(out4)} 列｜{note4}")
    ck("  note 是 'X'", out4 and out4[0][13] == "X", str(out4))
    ck("  ⚠ 兩市場的欄位數一樣（同一個 header 才能合併轉置）",
       len(out4[0]) == len(out[0]) == 14, f"{len(out4[0])} vs {len(out[0])}")

    print("④ ⛔ 反向：TPEx 找不到「備註」時要**講出來**，不可以靜靜整欄空白")
    nof = list(OTC_F)
    nof[19] = "其他"
    out5, note5 = rows(nof, [OTC_X], "tpex")
    ck("  仍然解得出資料（⛔ 不因為新欄不見就整條 feed 停掉）", len(out5) == 1, note5)
    ck("  note 留空", out5 and out5[0][13] == "", str(out5))
    ck("  ⭐ 而且訊息裡明講找不到備註欄", "找不到「備註」欄" in note5, note5)

    print("⑤ ⛔ 反向：文字若走 `_blank_num()` 會被清成空字串")
    ck("  `_blank_num('O')` 確實會清掉它（證明 ② 那條防護不是多餘的）",
       F._blank_num("O") == "", repr(F._blank_num("O")))

    print("⑥ ⚠ 恆等式仍然在守門（新欄沒有把驗算弄壞）")
    broken = list(TW_O)
    broken[6] = "999"          # 今日餘額對不上
    out6, note6 = rows(TW_F, [broken], "twse")
    ck("  餘額對不上的列被丟掉並計數", out6 == [] and "丟棄 1 列" in note6, note6)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

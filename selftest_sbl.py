#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_sbl.py — 驗借券賣出（SBL）的解析。

⛔ 這一支的假回應**照真回應的形狀做**（`sbl_probe.py` 2026-09-09 的實測輸出）：
15 欄、兩段併在一起、**兩段的「前日餘額」「當日餘額」欄名重複**、
上市有 `groups` 而上櫃**沒有**。

⚠ 要證明的重點有三個，每一個都對應一種會靜默出錯的取法：

    ① 取到的是**借券賣出當日餘額**（欄 12），⛔ 不是融券的今日餘額（欄 6）
    ② ⛔ `sbl_limit`（次一營業日可限額）**不是餘額**——K線線 Q2
    ③ ⭐ 段落邊界照官方 `groups`，⛔ 不寫死 ⇒ groups 不見時要**拒收**
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


GROUPS = [{"title": "股票", "span": 2}, {"title": "融券", "span": 6},
          {"title": "借券賣出", "span": 6}, {"title": "", "span": 1}]
# ⚠ 逐字照 2026-09-09 實測（`_sbl_probe.txt`）
ROW_A = ["00400A", "主動國泰動能高息", "0", "1,000", "0", "0", "1,000",
         "474,910,000", "22,137,000", "0", "0", "0", "22,137,000",
         "12,553,447", " "]
ROW_B = ["00401A", "主動摩根台灣鑫收", "0", "0", "0", "0", "0", "59,473,750",
         "2,932,000", "175,000", "0", "0", "3,107,000", "2,270,894", "X "]
H = F.FEEDS["sbl"]["header"]


def tw(fields=None, data=None, groups=None, **top):
    d = {"stat": "OK", "date": "20260909", "total": 2,
         "title": "115年09月09日 信用額度總量管制餘額表",
         "groups": GROUPS if groups is None else groups,
         "tables": [{"fields": fields if fields is not None else F.SBL_TWSE_FIELDS,
                     "data": data if data is not None else [ROW_A, ROW_B]}]}
    d.update(top)
    return d


def tp(fields=None, data=None):
    return {"stat": "ok", "date": "20260909",
            "tables": [{"fields": fields if fields is not None else F.SBL_TPEX_FIELDS,
                        "data": data if data is not None else [ROW_A, ROW_B]}]}


def main():
    i = {h: H.index(h) for h in H}

    print("① 上市：解得出來，而且取到的是**借券**那一段")
    out, note = F.parse_sbl(tw(), "2026-09-09")
    ck("  兩列都通過恆等式", len(out) == 2, f"{len(out)}｜{note}")
    a = dict(zip(H, out[0])) if out else {}
    ck("  ⭐ `sbl_balance` = 22137000（欄 12，借券當日餘額）",
       a.get("sbl_balance") == "22137000", str(a.get("sbl_balance")))
    ck("  ⛔ **不是** 融券的今日餘額 1000（欄 6）",
       a.get("sbl_balance") != "1000")
    ck("  融券那一段照樣存著：`s_balance` = 1000",
       a.get("s_balance") == "1000", str(a.get("s_balance")))
    ck("  ⚠ 千分位被清掉（數字欄走 `_blank_num`）",
       "," not in str(a.get("sbl_limit")), str(a.get("sbl_limit")))

    print("② ⛔ K線線 Q2：限額 ≠ 餘額，兩個都存、分得開")
    ck("  `sbl_limit` = 12553447（次一營業日可限額）",
       a.get("sbl_limit") == "12553447", str(a.get("sbl_limit")))
    ck("  ⚠ 而它跟 `sbl_balance` **不相等**",
       a.get("sbl_limit") != a.get("sbl_balance"))

    print("③ `note` 是文字，⛔ 不可以走 `_blank_num`")
    b = dict(zip(H, out[1])) if len(out) > 1 else {}
    ck("  00401A 的 note = 'X'", b.get("note") == "X", repr(b.get("note")))
    ck("  ⚠ 沒有註記的是空字串", a.get("note") == "", repr(a.get("note")))
    ck("  ★ 反向：`_blank_num('X')` 確實會把它清掉（證明這條防護不多餘）",
       F._blank_num("X") == "", repr(F._blank_num("X")))
    # ⛔⛔ 落地當天照出來的：**註記是複合的**。2026-09-09 實測 117 列有註記，
    #   其中 `XV` 有 **55 列，比單獨的 `X`（50）還多**。
    #   ⇒ 寫 `note == 'X'` 會漏掉限制最嚴的那一群。
    rowc = list(ROW_A)
    rowc[14] = "XV! "
    oc, _ = F.parse_sbl(tw(data=[rowc]), "2026-09-09")
    ck("  ⭐ 複合註記 `XV!` 原封不動存下來（⛔ 不拆、不取第一個字）",
       oc and dict(zip(H, oc[0]))["note"] == "XV!",
       str(dict(zip(H, oc[0]))["note"]) if oc else "0 列")
    ck("  ⚠ ⇒ 判準要用「包含」：`'X' in note` 是 True",
       bool(oc) and "X" in dict(zip(H, oc[0]))["note"])
    ck("  ★ 反向：`note == 'X'` 會漏掉它（這就是為什麼契約寫「包含」）",
       bool(oc) and dict(zip(H, oc[0]))["note"] != "X")

    print("④ ⭐ 段落邊界照官方 `groups`，⛔ 不寫死")
    ck("  `_sbl_seg_from_groups` 算出 8", F._sbl_seg_from_groups(tw()) == 8,
       str(F._sbl_seg_from_groups(tw())))
    ck("  ★ 反向：groups 不見 ⇒ **拒收**（⛔ 不退回寫死的 8）",
       F.parse_sbl(tw(groups=None) | {"groups": None}, "2026-09-09")[0] == []
       or F.parse_sbl({**tw(), "groups": []}, "2026-09-09")[0] == [])
    d2 = {**tw()}
    del d2["groups"]
    got2 = F.parse_sbl(d2, "2026-09-09")
    ck("  ★ 沒有 groups 這個鍵 ⇒ 拒收且訊息講得出原因",
       got2[0] == [] and "groups" in got2[1], str(got2[1])[:80])
    # ⚠ groups 說借券從別的地方開始 ⇒ 先拒收（要有人看），⛔ 不要照著取
    g3 = [{"title": "股票", "span": 2}, {"title": "融券", "span": 4},
          {"title": "借券賣出", "span": 6}, {"title": "", "span": 1}]
    got3 = F.parse_sbl(tw(groups=g3), "2026-09-09")
    ck("  ★ groups 說從第 6 欄開始（與實測 8 不同）⇒ **拒收**，不照著取",
       got3[0] == [] and "與實測的 8 不同" in got3[1], str(got3[1])[:90])

    print("⑤ ⛔ 欄位對不上要拒收（⚠ 不是靜靜回 0 列）")
    bad = list(F.SBL_TWSE_FIELDS)
    bad[12] = "今日餘額"
    r5 = F.parse_sbl(tw(fields=bad), "2026-09-09")
    ck("  欄名變了 ⇒ 拒收並回報欄名",
       r5[0] == [] and "拒收" in r5[1], str(r5[1])[:80])

    print("⑥ ⚠ 恆等式：位置取錯時它會整片不符 ⇒ 那一列要被丟掉並計數")
    broken = list(ROW_A)
    broken[12] = "999"          # 當日餘額對不上前日＋賣出−還券＋調整
    r6 = F.parse_sbl(tw(data=[broken]), "2026-09-09")
    ck("  不符的列被丟掉", r6[0] == [], str(r6[0]))
    ck("  ⚠ 而且訊息裡數得出來", "不符丟棄 1 列" in r6[1], r6[1])

    print("⑦ 上櫃：同一套輸出，⛔ 但它**沒有 groups**")
    o2, n2 = F.parse_otcsbl(tp(), "2026-09-09")
    ck("  解得出 2 列", len(o2) == 2, f"{len(o2)}｜{n2}")
    ck("  ⭐ 逐格與上市那一側相同（同一支 `_sbl_rows`）",
       o2 == out, f"{o2[:1]}\n            vs {out[:1]}")
    ck("  ⚠ 訊息裡講明「沒有 groups」", "沒有 groups" in n2, n2)
    badp = list(F.SBL_TPEX_FIELDS)
    badp[8] = "前日餘額(張)"
    ck("  ⛔ 欄名逐字比對是唯一的守衛 ⇒ 差一個字就拒收",
       F.parse_otcsbl(tp(fields=badp), "2026-09-09")[0] == [])

    print("⑧ 註冊表")
    for k in ("sbl", "otcsbl"):
        e = F.FEEDS[k]
        ck(f"  {k} header 15 欄且與另一支相同",
           e["header"] == H, str(len(e["header"])))
        ck(f"  {k} known=False（借券表含 ETF／ETN，先全收）", e["known"] is False)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

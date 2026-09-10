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

    print("⑨ ⛔ 丟棄要**講得出是哪幾列**，不是只給一個數字")
    # ⚠ `feeds:otcsbl` 紅在「1 天有丟棄」，而 runlog 連**哪一天**都沒寫
    #   ⇒ 沒有人追得下去 ⇒ 它就一直紅著。⭐ 這一節釘住「叫得出原因」。
    BADROW = ["5678", "乙", "0", "0", "0", "0", "0", "0",
              "1000", "500", "200", "0", "9999", "999", ""]
    out7, note7 = F.parse_sbl(tw(data=[ROW_A, BADROW]), "2026-09-09")
    ck("  不符的那一列被丟掉（只剩 1 列）", len(out7) == 1, str(len(out7)))
    ck("  ⭐ 說明講得出**代號**", "5678" in note7, note7)
    ck("  ⭐ 說明講得出**差多少**（差 1~2 股是進位、差一個量級是欄位錯位）",
       "差 " in note7, note7)
    ck("  ⚠ 而且五個數字都在（前／賣／還／調／餘）",
       all(x in note7 for x in ("前1000", "賣500", "還200", "調0", "餘9999")),
       note7)
    ck("  ⛔ 丟棄數是 1", F._dropped_in(note7) == 1, note7)

    print("⑩ ⭐ `_dropped_in`：從說明取**數字**，⛔ 不是「有沒有出現『丟棄』兩個字」")
    # ⛔ 這一段是為了 `cmd_feed` 那裡原本的寫法：
    #   `"丟棄" in note and "丟棄 0 列" not in note`
    #   ⚠ 而同一個檔案就記著「訊息字串是給人看的，不是狀態機的輸入」
    #     （休市日被算成失敗那次，就是結尾全形括號對不到）。
    ck("  0 列 ⇒ 0", F._dropped_in("3 列可用（x；驗算不符丟棄 0 列）") == 0)
    ck("  7 列 ⇒ 7",
       F._dropped_in("1 列可用（x；⛔ 驗算不符丟棄 7 列｜前 1 筆：[…]）") == 7)
    ck("  ⚠ 完全沒提丟棄 ⇒ 0（⛔ 不是丟例外）", F._dropped_in("5 列") == 0)
    ck("  ⚠ 非字串也不炸", F._dropped_in(None) == 0)
    ck("  ⭐ 兩位數也取得對（⛔ 不是只認個位數）",
       F._dropped_in("x（驗算不符丟棄 23 列）") == 23)
    # ⭐ 反向：舊寫法在「丟棄 0 列」以外的措辭上會判錯
    _n0 = "3 列可用（x；驗算不符丟棄 0 列）"
    ck("  ⭐⭐ 舊寫法碰到 `丟棄 0 列` 是對的…",
       not ("丟棄" in _n0 and "丟棄 0 列" not in _n0))
    _n1 = "3 列可用（x；驗算不符丟棄 00 列）"
    ck("     …但措辭只要差一點（`00 列`）它就判成**有丟棄**，"
       "⛔ 而 `_dropped_in` 取到的是 0",
       ("丟棄" in _n1 and "丟棄 0 列" not in _n1) and F._dropped_in(_n1) == 0)

    print("⑪ ⭐ `_tally_drop`：呼叫點也要測（⛔ 不是只測那個抽出來的判準）")
    _note = "600 列可用（x；⛔ 驗算不符丟棄 40 列｜前 3 筆：[…]）"
    n_, disp_ = F._tally_drop(600, "2015-01-22", _note)
    ck("  ⭐⭐ 一天丟 40 列就是 **40**，⛔ 不是 1"
       "（用『有沒有丟棄』判就會記成 1）", n_ == 40, str(n_))
    ck("  ⭐ 丟棄不是 0 時，**parser 的原始說明要保留**"
       "（它帶著是哪幾檔、差多少）", "前 3 筆" in disp_, disp_)
    n0_, disp0_ = F._tally_drop(600, "2015-01-22",
                                "600 列可用（x；驗算不符丟棄 0 列）")
    ck("  0 列 ⇒ 0，且說明簡化成「600 列」（⛔ 不要每行拖一串括號）",
       n0_ == 0 and disp0_ == "600 列", f"{n0_}｜{disp0_}")

    print("⑫ ⭐⭐ 恆等式不符的**歸因**：該檔是不是離開了本市場")
    # ⭐ 情報分析線 2026-09-10 23:00 實測查到的那一筆：
    #     2015-01-22　3416 融程電｜前 1,000 賣 0 還 0 調 0 ⇒ 餘額 **0**｜備註**空的**
    #   成因：那天是它在**上櫃的最後一個交易日**（01-23 轉上市），
    #   官方在它離開時把餘額**直接歸零**，⛔ 沒走「還券」也沒走「調整」欄。
    # ⇒ 不是瑕疵，是**恆等式的定義邊界**（與 `exDailyQ` 不含轉上市後同形狀）。
    import io
    import os
    import shutil
    import tempfile
    d = tempfile.mkdtemp(prefix="sbldrop_")
    keep = F.UNI_DIR
    try:
        F.UNI_DIR = d
        os.makedirs(os.path.join(d, "otcsbl"))
        def day(fn, codes):
            with io.open(os.path.join(d, "otcsbl", fn), "w",
                         encoding="utf-8") as f:
                f.write("date,stock_id\n")
                for c in codes:
                    f.write(f"{fn[:-4]},{c}\n")
        DAYS = ["2015-01-21", "2015-01-22", "2015-01-23"]
        day("2015-01-21.csv", ["3416", "1111"])
        day("2015-01-22.csv", ["1111"])          # 3416 那天被丟掉
        day("2015-01-23.csv", ["1111"])          # ⭐ 3416 已經不在表上（轉上市）
        left, un = F._explain_drops("otcsbl", [("2015-01-22", "3416")], DAYS)
        ck("  ⭐ 3416 歸因為**離開本市場**", len(left) == 1 and left[0][1] == "3416",
           str(left))
        ck("  ⛔ 而且**不進**未歸因（⇒ 那條紅燈會轉綠）", not un, str(un))
        ck("  ⚠ 說明講得出是看哪一天",
           left and "2015-01-23" in left[0][2], str(left))

        # ⛔ 反向：同樣不符，但那一檔**次一日還在** ⇒ 必須留在未歸因
        left2, un2 = F._explain_drops("otcsbl", [("2015-01-22", "1111")], DAYS)
        ck("  ⭐⭐ 次一日**仍在表上**的那一檔 ⇒ **未歸因**（⛔ 才是真的要查）",
           not left2 and len(un2) == 1 and un2[0][1] == "1111", f"{left2}｜{un2}")

        # ⚠ 區間最後一天沒有次一日可比 ⇒ ⛔ 一律當未歸因（寧可多查一筆）
        left3, un3 = F._explain_drops("otcsbl", [("2015-01-23", "1111")], DAYS)
        ck("  ⚠ 區間最後一天 ⇒ **不可判定**，當未歸因"
           "（⛔ 不要把真的瑕疵歸成「它離開了」）",
           not left3 and len(un3) == 1 and "無次一日" in un3[0][2], str(un3))
        # ⚠ 次一日**的檔根本不存在**（那天還沒抓到）⇒ ⛔ 不可判定，當未歸因
        left4, un4 = F._explain_drops("otcsbl", [("2015-01-23", "1111")],
                                      DAYS + ["2015-01-26"])
        ck("  ⚠ 次一日的**檔不存在**時當未歸因，⛔ 不是當成離開",
           not left4 and len(un4) == 1 and "沒有檔可比" in un4[0][2],
           f"{left4}｜{un4}")
    finally:
        F.UNI_DIR = keep
        shutil.rmtree(d, ignore_errors=True)

    print("⑬ ⭐ 從說明裡把代號撈回來（歸因那一步的輸入）")
    _n = ("600 列可用（x；⛔ 驗算不符丟棄 1 列｜前 1 筆："
          "[('3416', '前1000+賣0-還0+調0≠餘0（差 +1000）')]）")
    ck("  撈得到 3416", F._drop_codes(_n) and F._drop_codes(_n)[0][0] == "3416",
       str(F._drop_codes(_n)))
    ck("  ⚠ 撈不到時回空清單（⛔ 不是丟例外）", F._drop_codes("600 列") == [])
    ck("  ⚠ 非字串也不炸", F._drop_codes(None) == [])
    ck("  ⭐ 帶英文的代號（`00400A`）也撈得到",
       F._drop_codes("x[('00400A', 'y')]") == [("00400A", "y")],
       str(F._drop_codes("x[('00400A', 'y')]")))

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

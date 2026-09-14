#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_inst_dealer.py — 三大法人的「自營商分項」兩欄（2026-09-14 加）。

## ⛔ 這一支存在的理由

K線分析線 0707 裁定：判籌碼只能看**自行買賣**，避險是法規強制的獨立帳戶、
不代表方向判斷。⚠ 而我方 `dealer` 一直是**合計**，分項根本沒收。

⛔ 而收分項有一個**已經害過 16,394 列**的坑：T86 的欄名互相包含。
2026-09-14 `_keys_probe.txt` 逐字印出來的 19 欄裡：

    [11] 自營商買賣超股數　　　　　　← 合計
    [14] 自營商買賣超股數(自行買賣)
    [17] 自營商買賣超股數(避險)

⇒ **[11] 是 [14] 與 [17] 的子字串**。用「包含」比對 ⇒ 三欄全部撞在一起。
⚠ 而撞在一起之後**不會報錯**：它會算出一個看起來很正常的數字。

## ⭐ 所以這一支的主角是**反向**那幾條

⛔ 「有收到分項」很容易測；⭐ 真正要釘的是：
① 合計欄**不可以**命中分項（子字串）
② 取不到分項時要**留空**，⛔ 不是寫 0（0 ＝「沒買沒賣」，空 ＝「沒有這個欄位」）
③ 而且要**大聲講**（整欄空白與「今天大家都是 0」長得一樣）
④ 自行買賣 ＋ 避險 ≠ 自營合計 ⇒ **丟掉那一列並回報**，⛔ 不靜靜寫進去
⑤ 兩欄**接在最後**（`--need-col` 靠表頭認要重抓的日子；插中間會讓舊檔錯位）
"""
import io
import sys

import backfill as B
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


# ⭐ 照 `_keys_probe.txt` 2026-09-14 逐字抄回來的 19 欄
T86_FIELDS = [
    "證券代號", "證券名稱",
    "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
    "外陸資買賣超股數(不含外資自營商)",
    "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
    "投信買進股數", "投信賣出股數", "投信買賣超股數",
    "自營商買賣超股數",
    "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)",
    "自營商買賣超股數(自行買賣)",
    "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
    "三大法人買賣超股數",
]


def t86(rows, fields=None):
    return {"fields": fields if fields is not None else T86_FIELDS, "data": rows}


def main():
    print("① ⭐⭐ T86：分項收得到，而且合計仍然是合計")
    #   外 1000(=600+400)、投 200、自營合計 300(=自行 100 + 避險 200)、合計 1500
    r = ["2330", "台積電", "700", "100", "600", "500", "100", "400",
         "300", "100", "200", "300",
         "150", "50", "100", "250", "50", "200", "1500"]
    out, note = B.parse_inst(t86([r]), "2026-09-09", None)
    ck("  解析出 1 列", len(out) == 1, note)
    row = dict(zip(B.INST_HEADER, out[0])) if out else {}
    ck("  ⭐ dealer 是**合計** 300（⛔ 不是分項）", row.get("dealer") == "300", str(row))
    ck("  ⭐ dealer_self 100、dealer_hedge 200",
       row.get("dealer_self") == "100" and row.get("dealer_hedge") == "200", str(row))
    ck("  ⚠ 而 foreign 是兩欄相加 600+400=1000",
       row.get("foreign") == "1000", str(row))

    print("\n② ⛔⛔ 子字串陷阱：`自營商買賣超股數` 是另外兩欄的**前綴**")
    ck("  ⭐ 前提：官方欄名真的互相包含（⛔ 否則這一節測不到東西）",
       all(x.startswith("自營商買賣超股數")
           for x in ("自營商買賣超股數(自行買賣)", "自營商買賣超股數(避險)")))
    # ⛔ 反向：把合計欄拿掉，「包含」比對會退而命中分項 ⇒ 完全相等比對要**取不到**
    f2 = [c for c in T86_FIELDS if c != "自營商買賣超股數"]
    r2 = [x for i, x in enumerate(r) if i != 11]
    out2, note2 = B.parse_inst(t86([r2], f2), "2026-09-09", None)
    ck("  ⭐ 合計欄不在時 dealer 取不到 ⇒ 恆等式擋下來（⛔ 不是靜靜用分項頂替）",
       not out2, f"{len(out2)} 列｜{note2}")

    print("\n③ ⭐ 取不到分項 ⇒ **留空**，⛔ 不是 0，而且要大聲講")
    # ⚠ 欄名與值要**同一組索引**一起拿掉——⛔ 只濾欄名會讓兩邊長度對不上，
    #   而那會讓這一節測到的是「列太短被跳過」，不是「分項取不到」。
    _drop = (12, 13, 14, 15, 16, 17)
    f3 = [c for i, c in enumerate(T86_FIELDS) if i not in _drop]
    r3 = [x for i, x in enumerate(r) if i not in _drop]
    out3, note3 = B.parse_inst(t86([r3], f3), "2026-09-09", None)
    row3 = dict(zip(B.INST_HEADER, out3[0])) if out3 else {}
    ck("  那一列照樣留下來（⛔ 不可以因為少了分項就整列丟掉）", len(out3) == 1, note3)
    ck("  ⭐ 兩欄是**空字串**，⛔ 不是 '0'",
       row3.get("dealer_self") == "" and row3.get("dealer_hedge") == "",
       str(row3))
    ck("  ⭐⭐ 而 note 要講出來（⚠ 整欄空白與「今天大家都是 0」長得一樣）",
       "整欄留空" in note3, note3)

    print("\n④ ⛔ 自行買賣 ＋ 避險 ≠ 自營合計 ⇒ 丟掉那一列並回報")
    r4 = list(r)
    r4[17] = "999"                      # 避險被改成別的值
    out4, note4 = B.parse_inst(t86([r4]), "2026-09-09", None)
    ck("  那一列被丟掉", not out4, f"{len(out4)} 列")
    ck("  ⭐ 而且講得出它是為什麼被丟的", "自行買賣＋避險" in note4, note4)
    # ⛔ 反向：⚠ 沒有這條的話，取錯欄會靜靜寫進去
    ck("  ⚠ 正例：同一批沒被動過時 0 筆被丟（⛔ 證明④不是把整批擋掉）",
       "丟棄 0 列" in note and "自行買賣＋避險" not in note, note)

    print("\n⑤ ⭐ 兩欄**接在最後**（`--need-col` 靠表頭認日子）")
    ck("  backfill.INST_HEADER 的最後兩欄",
       B.INST_HEADER[-2:] == ["dealer_self", "dealer_hedge"], str(B.INST_HEADER))
    ck("  ⭐ 而前六欄**一個都沒動**（⛔ 動了舊日檔會整排錯位）",
       B.INST_HEADER[:6] == ["date", "stock_id", "foreign", "trust",
                             "dealer", "total"], str(B.INST_HEADER))
    ck("  feeds 的 otcinst 表頭跟它**逐格相同**（⛔ 兩邊分岔 ⇒ 個股切面會錯位）",
       F.FEEDS["otcinst"]["header"] == B.INST_HEADER,
       f"{F.FEEDS['otcinst']['header']}\n vs {B.INST_HEADER}")

    print("\n⑥ ⭐ 上櫃（24 欄新版）：分項在 16／19，而那是**結構檢查**出來的")
    # 七組各三欄：①2-4 ②5-7 ③8-10 ④11-13 ⑤14-16 ⑥17-19 ⑦20-22，合計 23
    of = (["代號", "名稱"]
          + ["買進股數", "賣出股數", "買賣超股數"] * 7
          + ["三大法人買賣超股數合計"])
    orow = (["6488", "環球晶"]
            + ["0", "0", "600"]        # ①外資及陸資(不含外資自營商)
            + ["0", "0", "400"]        # ②外資自營商
            + ["0", "0", "1000"]       # ③外資合計
            + ["0", "0", "200"]        # ④投信
            + ["0", "0", "100"]        # ⑤自營商(自行買賣)
            + ["0", "0", "200"]        # ⑥自營商(避險)
            + ["0", "0", "300"]        # ⑦自營商合計
            + ["1500"])
    d6 = {"tables": [{"fields": of, "data": [orow]}]}
    o6, n6 = F.parse_otcinst(d6, "2026-09-09", None)
    m6 = dict(zip(B.INST_HEADER, o6[0])) if o6 else {}
    ck("  解析出 1 列", len(o6) == 1, n6)
    ck("  ⭐ dealer 300（⑦合計）、dealer_self 100（⑤）、dealer_hedge 200（⑥）",
       m6.get("dealer") == "300" and m6.get("dealer_self") == "100"
       and m6.get("dealer_hedge") == "200", str(m6))
    # ⛔ 反向：結構不符就整批拒收，⛔ 不是硬取 16／19
    of_bad = list(of)
    of_bad[16] = "別的欄"
    o6b, n6b = F.parse_otcinst({"tables": [{"fields": of_bad, "data": [orow]}]},
                               "2026-09-09", None)
    ck("  ⛔ 第 16 欄不是「買賣超股數」⇒ **整批拒收**（⛔ 不硬取位置）",
       not o6b and "分項欄不在預期位置" in n6b, n6b)

    print("\n⑦ ⭐⭐ `--need-col` 的續跑判準：**用資料自己當進度**")
    # ⛔⛔ 這一節的起因是我自己寫錯的一句註解：我在 INST_HEADER 寫
    #   「`--need-col dealer_self` 靠表頭認日子」——⚠ 而 `--inst` **當時沒有那個參數**，
    #   上市那半只有 `--force`（整段重抓、斷掉要從頭）。
    #   ⇒ ⭐ 現在收成一份 `backfill.days_missing_col()`，兩邊都叫它。
    import os as _os
    import tempfile as _tf
    _d = _tf.mkdtemp()
    io.open(_os.path.join(_d, "2015-01-05.csv"), "w", encoding="utf-8").write(
        "date,stock_id,foreign,trust,dealer,total\n")          # 舊 6 欄
    io.open(_os.path.join(_d, "2026-09-11.csv"), "w", encoding="utf-8").write(
        ",".join(B.INST_HEADER) + "\n")                        # 新 8 欄
    _done = {"2015-01-05", "2026-09-11"}
    _stale = B.days_missing_col(_d, "dealer_self", _done)
    ck("  ⭐ 只有**表頭缺那一欄**的日子要重抓",
       _stale == {"2015-01-05"}, str(_stale))
    ck("  ⛔ 反向：已經有那一欄的日子**不重抓**（⚠ 否則每趟都全庫重跑）",
       "2026-09-11" not in _stale, str(_stale))
    # ⚠ 接住例外再判：⛔ 不接的話整支測試當場中斷，後面一條都不會跑（第七點②）
    try:
        _g = B.days_missing_col(_d, "dealer_self", _done | {"1999-01-01"})
    except Exception as _ex:                                  # noqa: BLE001
        _g = f"⛔ 炸了：{type(_ex).__name__}"
    ck("  ⚠ 而檔不存在時不會炸（⛔ 只是不算它）",
       _g == {"2015-01-05"}, str(_g))
    # ⛔⛔ 要測「完全相等 vs 包含」，光靠上面兩個檔**分不出來**
    #   （兩份表頭都含 `dealer`，兩種比對的答案一樣 ⇒ 突變 E1 全綠）。
    #   ⇒ ⭐ 要一個**有 `dealer_self`、沒有 `dealer`** 的表頭：
    #     完全相等 ⇒ 缺 `dealer` ⇒ 要重抓；包含 ⇒ 被 `dealer_self` 頂替 ⇒ 不重抓。
    io.open(_os.path.join(_d, "2020-01-02.csv"), "w", encoding="utf-8").write(
        "date,stock_id,dealer_self,dealer_hedge\n")
    ck("  ⭐ 欄名是**完全相等**比對（⛔ `dealer_self` 不可以頂替 `dealer`）",
       "2020-01-02" in B.days_missing_col(_d, "dealer", _done | {"2020-01-02"}),
       str(B.days_missing_col(_d, "dealer", _done | {"2020-01-02"})))
    # ⛔ 而「呼叫點真的用了它」要掃原始碼（第七點③，這是第八次）
    _src_b = io.open(B.__file__, encoding="utf-8").read()
    _src_f = io.open(F.__file__, encoding="utf-8").read()
    ck("  ⭐⭐ `--inst` 的呼叫點真的看 stale（⛔ 只測函式的話，"
       "把它從 days 篩選裡拿掉不會紅）",
       "or d in stale" in _src_b and 'dest="need_col"' in _src_b,
       "⛔ cmd_inst 沒有用 stale／argparse 沒有 --need-col")
    ck("  ⭐ 而 feeds 也是叫同一份（⛔ 不是自己再抄一次）",
       "B.days_missing_col(" in _src_f
       and "head = f_.readline()" not in _src_f,
       "⛔ feeds 還留著自己那一份")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

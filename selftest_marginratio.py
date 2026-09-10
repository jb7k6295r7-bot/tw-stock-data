#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_marginratio.py — 驗個股融資融券成數**調整幅度**的解析（BFIB9U）。

⚠ 假回應**照真回應的形狀做**（`chtm_probe.py` 2026-09-10 於 Actions 的實測）。

⭐ 要證明的重點——三個都在實測值裡看得到：

    ① **同一檔多列**：471 列裡只有 94 個相異代號（一個「原因」一列）
       ⇒ ⛔ 主鍵是（日期, 代號, **原因**）
    ② **值不是純數字**：`累計：N` 與 `N` 是**兩件事**
       ⛔ `int()` 會炸、`replace("累計：","")` 會把兩者混成一個數字
    ③ 空值有**兩種寫法**：空字串與**單一半形空白**
       ⛔ 只判 `== ""` 會把那些讀成「有值」

⭐⭐ 外加一件沒有別的東西擋得住的：
這一支的回應**沒有 `date`、`title` 也不帶日期** ⇒ `_same_day` 找不到自述日期
⇒ **一律放行**。⚠ 而不帶日期參數時它回的是**前一個營業日**。
⇒ 日期只寫在 `hints` 裡 ⇒ **本 parser 自己驗**。
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


DAY = "2026-09-09"
HINT = "查詢範圍：全部上市 \n期間：115年09月09日到115年09月09日"
# ⚠ 逐字照實測（含名稱後面那一串補白空格、單一空白的空值、民國點分隔日期）
ROWS = [[1, "1203", "味王            ", "股價波動過度劇烈", "", "", "1", "1"],
        [1, "1203", "味王            ", "成交量過度異常", "115.09.03", "",
         "1", "1"],
        [1, "1203", "味王            ", "監視第二次處置", "", "", " ", " "],
        [2, "2330", "台積電", "股權過度集中", "110.09.24", "115.09.14",
         "累計：6", "累計：2"]]
H = F.FEEDS["marginratio"]["header"]


def tw(fields=None, data=None, hints=HINT, **top):
    d = {"stat": "OK", "title": "調整融資融券成數股票資訊", "hints": hints,
         "fields": F.MRATIO_FIELDS if fields is None else fields,
         "data": ROWS if data is None else data}
    d.update(top)
    return d


def main():
    print("① 照真形狀：解得出來")
    out, note = F.parse_marginratio(tw(), DAY)
    ck("  4 列", len(out) == 4, f"{len(out)}｜{note}")
    ck("  每列長度 = header", all(len(r) == len(H) for r in out), str(H))
    ck("  ⭐ 說明講得出**列數與檔數不同**（4 列／2 檔）",
       "4 列" in note and "2 檔" in note, note)
    ck("  ⚠ 名稱後面的補白空格被清掉",
       out[0][H.index("name")] == "味王", repr(out[0][H.index("name")]))

    print("② ⛔ 主鍵含**原因**：同一檔不可以被壓成一列")
    keys = {(r[0], r[1]) for r in out}
    keys3 = {(r[0], r[1], r[3]) for r in out}
    ck("  ⭐ 用（日期,代號）當鍵只剩 2 個 ⇒ **會壓掉 2 列**",
       len(keys) == 2, str(sorted(keys)))
    ck("  ⭐ 加上原因才是 4 個 ⇒ 主鍵必須含原因",
       len(keys3) == 4, str(len(keys3)))
    ck("  1203 有 3 個不同原因",
       len({r[3] for r in out if r[1] == "1203"}) == 3, str(out))

    print("③ ⭐ `累計：N` 與 `N` 是兩件事")
    m = {(r[1], r[3]): dict(zip(H, r)) for r in out}
    a = m[("2330", "股權過度集中")]
    ck("  `累計：6` ⇒ 值 6、累計旗標 1",
       (a["margin_cut"], a["margin_cum"]) == ("6", "1"), str(a))
    ck("  `累計：2` ⇒ 值 2、累計旗標 1",
       (a["short_raise"], a["short_cum"]) == ("2", "1"), str(a))
    b = m[("1203", "股價波動過度劇烈")]
    ck("  ⭐ 而單次的 `1` ⇒ 值 1、累計旗標 **0**",
       (b["margin_cut"], b["margin_cum"]) == ("1", "0"), str(b))
    ck("  ⛔ 兩者分得開（⚠ 混在一起的話 6 與『累計 6』會變成同一個數字）",
       a["margin_cum"] != b["margin_cum"])
    ck("  ⚠ 全形冒號也吃得下",
       F._mratio_val("累計：3") == ("3", "1"), str(F._mratio_val("累計：3")))
    ck("  ⚠ 半形冒號也吃得下",
       F._mratio_val("累計:3") == ("3", "1"), str(F._mratio_val("累計:3")))

    print("④ ⛔ 空值有兩種寫法，兩種都要是空的")
    c = m[("1203", "監視第二次處置")]
    ck("  ⭐ **單一半形空白** ⇒ 空字串（⛔ 不是 '0'）",
       (c["margin_cut"], c["short_raise"]) == ("", ""), str(c))
    ck("  空字串 ⇒ 空字串", F._mratio_val("") == ("", ""))
    ck("  ⛔ 認不出來回空，**不是 0**（0 是「不調整」的真值）",
       F._mratio_val("abc") == ("", ""), str(F._mratio_val("abc")))
    ck("  ⚠ 而真的 0 讀得出來",
       F._mratio_val("0") == ("0", "0"), str(F._mratio_val("0")))
    # ⭐ 前後有空白的數字：⛔ **不可以把空白一起存進去**
    #   （⚠ `float(" 1 ")` 在 Python 是會過的 ⇒ 少了 strip 不會炸，
    #     只會讓 CSV 裡出現 `" 1 "` 這種值，而下游多半用字串比對）
    ck("  ⭐ `\" 1 \"` ⇒ `(\"1\", \"0\")`，⛔ 存進去的不帶空白",
       F._mratio_val(" 1 ") == ("1", "0"), str(F._mratio_val(" 1 ")))
    ck("  ⚠ `\"累計： 6 \"` 也一樣",
       F._mratio_val("累計： 6 ") == ("6", "1"),
       str(F._mratio_val("累計： 6 ")))

    print("⑤ 民國**點分隔**日期換算")
    ck("  `115.09.03` → 2026-09-03",
       m[("1203", "成交量過度異常")]["adjust_from"] == "2026-09-03", str(m))
    ck("  `110.09.24` → 2021-09-24", a["adjust_from"] == "2021-09-24", str(a))
    ck("  `115.09.14`（恢復日）→ 2026-09-14",
       a["restore_date"] == "2026-09-14", str(a))
    ck("  ⚠ 沒有日期的留空", b["adjust_from"] == "" and b["restore_date"] == "",
       str(b))

    print("⑥ ⭐⭐ 日期只寫在 `hints` 裡 ⇒ 這一支自己驗")
    r6, n6 = F.parse_marginratio(tw(), "2026-09-10")
    ck("  ⭐ hints 說 09-09 而我要 09-10 ⇒ **拒收**", not r6, str(r6))
    ck("  說明講得出兩邊的日期", "20260909" in n6 and "2026-09-10" in n6, n6)
    ck("  ⚠ 而且點出「不帶日期時回前一個營業日」",
       "前一個營業日" in n6, n6)
    r6b, n6b = F.parse_marginratio(tw(hints=""), DAY)
    ck("  ⛔ `hints` 讀不出日期 ⇒ **拒收**，不是放行"
       "（⚠ 這一支沒有 date／title 可比，hints 是唯一的自述）",
       not r6b and "無從確認" in n6b, n6b)
    ck("  ⚠ 而正常的那一批照樣通過（否則這節等於在測「永遠拒收」）",
       len(F.parse_marginratio(tw(), DAY)[0]) == 4)

    print("⑦ ⛔ 欄名逐字比對與各種壞回應")
    ck("  欄位不符 ⇒ 拒收",
       not F.parse_marginratio(tw(fields=F.MRATIO_FIELDS[:7]), DAY)[0])
    ck("  沒有表 ⇒ 拒收且說明有頂層鍵",
       not F.parse_marginratio({"stat": "OK"}, DAY)[0]
       and "stat" in F.parse_marginratio({"stat": "OK"}, DAY)[1])
    ck("  ⛔ 被擋回字串也不炸", not F.parse_marginratio("<html>", DAY)[0])
    ck("  ⛔ 短列不會 IndexError",
       len(F.parse_marginratio(tw(data=[[1, "1203", "味王"]]), DAY)[0]) == 0)
    ck("  合計／空代號不進來",
       len(F.parse_marginratio(
           tw(data=ROWS + [["", "合計", "", "", "", "", "", ""]]), DAY)[0]) == 4)
    ck("  ⚠ `known` 是 False（⛔ 被調成數的往往是飆股，濾掉等於濾掉最該看的）",
       F.FEEDS["marginratio"]["known"] is False)
    u = F.FEEDS["marginratio"]["urls"]("2015-01-05")[0]
    ck("  URL 帶 startDate 與 endDate",
       "startDate=20150105" in u and "endDate=20150105" in u, u)

    print(f"\n{OK} ok, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

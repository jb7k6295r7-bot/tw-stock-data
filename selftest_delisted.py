#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_delisted.py — 驗終止上市（下市）清單的解析與交叉判準。

⛔ 這一支解的是**生存者偏誤**：下市公司從母體消失 ⇒ 回測績效系統性偏樂觀，
⚠ 而且**不會有任何一格數字出錯**——它錯在「該賠錢的標的根本沒被算進來」。

假回應**照真回應的形狀做**（`delist_probe.py` 2026-09-09 於 Actions 的實測）：
`status:"ok"`（⛔ 不是 `stat`）、`total:265`、欄位 3 個、列是 list、
日期是**民國斜線** `"115/09/01"`。

⭐ 要證明的重點：

    ① ⛔ 這一站的第三種寫法：成功旗標叫 `status`。
       **反向**證明：只看 `stat` 的話，`status:"error"` 會**整批被當成成功**。
    ② 民國斜線日期換算得對；換不出來的列**進 bad 並且說明講得出來**
       ——⛔ 不是安靜跳過（那就是「靜默失敗長成 stat:OK」那一族）。
    ③ ⭐ `cross_check`：我方 `last_seen` **晚於**官方終止上市日 ⇒ 抓得出來。
       這是這支程式真正的產出，⚠ 而它只在 Actions 上跑得到 ⇒ 得在這裡驗。
"""
import json
import sys

import delisted as D

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⚠ 逐字照實測樣本
ROWS = [["115/09/01", "三商壽", "2867"],
        ["113/07/31", "亞太電", "3682"],
        ["090/01/20", "老牌", "1111"]]


def pay(data=None, fields=None, **top):
    d = {"status": "ok", "total": 3, "minYear": 2001, "maxYear": 2026,
         "title": "終止上市公司",
         "fields": D.FIELDS if fields is None else fields,
         "data": ROWS if data is None else data}
    d.update(top)
    return d


def main():
    print("① 照真形狀的回應：解得出來")
    rows, note = D.parse(pay())
    ck("  3 列", len(rows) == 3, f"{len(rows)}｜{note}")
    ck("  每一列 4 格（對得上 HEADER）",
       all(len(r) == len(D.HEADER) for r in rows), str(rows[:1]))
    ck("  ⭐ 民國斜線換算：115/09/01 → 2026-09-01",
       ["2026-09-01", "2867", "三商壽"] == rows[-1][:3], str(rows[-1]))
    ck("  113/07/31 → 2024-07-31",
       any(r[0] == "2024-07-31" and r[1] == "3682" for r in rows), str(rows))
    ck("  ⚠ 三位數民國年 090 也認得（涵蓋期最早到 2001）",
       any(r[0] == "2001-01-20" for r in rows), str(rows))
    ck("  照日期排序（最舊在前）", [r[0] for r in rows] == sorted(r[0] for r in rows),
       str([r[0] for r in rows]))
    ck("  說明帶 total 與涵蓋區間",
       "total=3" in note and "2001-01-20 ~ 2026-09-01" in note, note)

    print("② ⭐⭐ 反向：成功旗標叫 `status`，⛔ 不是 `stat`")
    bad = pay(status="error", data=[])
    rows2, note2 = D.parse(bad)
    ck("  `status:\"error\"` ⇒ 0 列", not rows2, str(rows2))
    ck("  說明講得出它自己說失敗", "status='error'" in note2, note2)
    # ⛔ 這才是這一節真正要證明的：**只看 `stat` 的寫法會放它過去**
    only_stat = str(bad.get("stat") or "").strip()
    ck("  ⭐ 只看 `stat` 的話拿到的是空字串 ⇒ 那種寫法會判它「沒說失敗」",
       only_stat == "", repr(only_stat))
    ck("  ⚠ 而正常的 `status:\"ok\"` 照樣通過（否則這條等於永遠拒收）",
       len(D.parse(pay())[0]) == 3)
    ck("  ⚠ 舊寫法 `stat:\"OK\"`（沒有 status）也還是通過",
       len(D.parse({"stat": "OK", "fields": D.FIELDS, "data": ROWS})[0]) == 3)

    print("③ ⛔ 認不出來的列要**被數出來並且說得出是哪幾列**")
    dirty = ROWS + [["", "空日期", "9999"],
                    ["115/09/01", "沒股號", ""],
                    "這根本不是 list",
                    ["115/09/01", "太短"]]
    rows3, note3 = D.parse(pay(data=dirty, total=7))
    ck("  只認 3 列", len(rows3) == 3, f"{len(rows3)}｜{note3}")
    ck("  說明講得出認不出 4 列", "認不出 4" in note3, note3)
    ck("  ⛔ 說明附上原始列（不是只給一個數字）", "空日期" in note3 or "沒股號" in note3,
       note3)
    ck("  ⚠ 官方列數與認出的列數在說明裡分得開",
       "官方 7 列" in note3 and "認得出 3" in note3, note3)

    print("④ ⛔ 這些一律拒收")
    ck("  欄位結構不符 ⇒ 0 列",
       not D.parse(pay(fields=["終止上市日期", "公司名稱"]))[0])
    ck("  說明講得出實際欄位",
       "拒收" in D.parse(pay(fields=["a", "b"]))[1],
       D.parse(pay(fields=["a", "b"]))[1])
    r5, n5 = D.parse(pay(data=[]))
    ck("  ⭐ 回 0 列**當失敗**（累積清單不可能是空的）", not r5, n5)
    ck("  說明說得出理由", "累積清單" in n5, n5)
    ck("  ⛔ 被 CDN 擋回 HTML 字串也不炸", not D.parse("<html>428</html>")[0])
    ck("  說明講得出型別", "str" in D.parse("<html>")[1], D.parse("<html>")[1])
    r6, n6 = D.parse({"status": "ok"})
    ck("  沒有表 ⇒ 0 列，且說明列出頂層鍵", not r6 and "status" in n6, n6)

    print("⑤ ⭐ cross_check：我方 last_seen 晚於官方終止上市日 ⇒ 抓得出來")
    good = {"2867": {"last_seen": "2026-08-29"},
            "3682": {"last_seen": "2024-07-31"}}      # ⚠ 等於當天 ⇒ 合法
    both, after = D.cross_check(rows, good)
    ck("  兩檔對得起來", len(both) == 2, str(both))
    ck("  ⛔ 沒有一檔晚於官方 ⇒ after 是空的", not after, str(after))
    ck("  ⚠ 「等於終止上市日」不算違規（那天還在交易）",
       not any(c == "3682" for c, _, _ in after), str(after))
    bad_meta = {"2867": {"last_seen": "2026-09-05"}}   # 下市後 4 天還有列
    both2, after2 = D.cross_check(rows, bad_meta)
    ck("  ⭐ 晚 4 天的那一檔被抓出來", [x[0] for x in after2] == ["2867"], str(after2))
    ck("  抓出來的內容含官方日與我方日",
       after2 and after2[0][1] == "2026-09-01" and after2[0][2] == "2026-09-05",
       str(after2))
    ck("  ⚠ 我方 meta 沒有的（2001 那檔）不算違規、也不進 both",
       "1111" not in [c for c, _, _ in both2], str(both2))
    ck("  ⛔ last_seen 是空字串時不算違規（沒有資訊 ≠ 違規）",
       not D.cross_check(rows, {"2867": {"last_seen": ""}})[1])
    ck("  ⛔ meta 值是 None 也不炸",
       D.cross_check(rows, {"2867": None})[1] == [])

    print("⑥ ⛔ 這一支不碰 stocks.csv（唯一寫入者是 fetch.merge_stocks_meta）")
    ck("  只寫 data/meta/delisted.csv", D.OUT.endswith("meta/delisted.csv"), D.OUT)
    ck("  ⚠ STOCKS 只被讀（沒有任何 open(..., \"w\") 指向它）",
       D.STOCKS != D.OUT and D.STOCKS != D.LOW, D.STOCKS)

    # ══════════════════════════════════════════════════════════════════
    print("⑦ ⭐⭐ 上櫃那半：`date` 回顯 ＋ 列的年份，兩道都要驗")
    # ⚠ 假回應**照 2026-09-11 於 Actions 的實測形狀**做：
    #   頂層 `stat`/`date`/`tables`，欄位 5 個，列是 list，日期是**民國減號** 104-11-26
    def _otc(year, data, stat="ok", fields=None):
        return {"stat": stat, "date": str(year),
                "tables": [{"fields": fields or D.OTC_FIELDS, "data": data}]}

    REAL = [["5506", "長鴻營造股份有限公司", "104-11-26", "依…第12條之2第1項第5款", "u"],
            ["4927", "泰鼎國際股份有限公司", "104-09-08", "依…第12條之2第1項第1款", "u"]]
    rows, note = D.parse_otc(_otc(2015, REAL), 2015)
    ck("  ⭐ 正常年解得出來，民國 104 換成 2015", len(rows) == 2
       and rows[0][0].startswith("2015"), f"{rows}｜{note}")
    ck("  ⭐ `market` 欄是 tpex（⛔ 上市那半是 twse，同一個檔要分得開）",
       all(r[4] == "tpex" for r in rows), str(rows))
    ck("  ⚠ 列寬跟表頭一致（⛔ 少一格會讓後面整片錯位）",
       all(len(r) == len(D.HEADER) for r in rows), str(rows))

    print("  ⛔ 第一道：`date` 回顯不是我送的那一年 ⇒ 拒收")
    r2, n2 = D.parse_otc(_otc(2026, REAL), 2015)     # 我送 2015、它回 2026
    ck("  ⭐ 拒收，而且說明講出「參數是假的」", not r2 and "參數是假的" in n2, n2)

    print("  ⛔ 第二道：回顯對了，但列的年份不對 ⇒ 那些列不可以收")
    r3, n3 = D.parse_otc(_otc(2015, REAL + [["9999", "別年的", "113-05-06", "x", "u"]]),
                         2015)
    ck("  ⭐ 別年的那一列被擋掉（2 筆不是 3 筆）", len(r3) == 2, str(r3))
    ck("  ⚠ 而且說明**講得出來**（⛔ 安靜跳過就是靜默失敗那一族）",
       "年份對不上" in n3, n3)

    print("  ⛔ 欄位結構不符 ⇒ 拒收（⚠ 官方改欄位時不可以照收）")
    r4, n4 = D.parse_otc(_otc(2015, REAL, fields=["股票代號", "公司名稱"]), 2015)
    ck("  拒收並印出實際欄位", not r4 and "拒收" in n4, n4)
    r5, n5 = D.parse_otc(_otc(2015, REAL, stat="查無資料"), 2015)
    ck("  ⛔ `stat` 不是 ok ⇒ 拒收（⚠ 正例在上面，兩邊都測過）",
       not r5 and "端點自己說失敗" in n5, n5)

    print("⑧ ⭐ `fetch_otc`：⛔ 絕不使用 `date=ALL`＋連續 0 筆要收手")
    seen = []

    def fake_get(url, **kw):
        seen.append(url)
        raw_y = url.split("date=")[1].split("&")[0]
        y = int(raw_y) if raw_y.isdigit() else raw_y      # ⚠ 容得下 "ALL"
        # ⭐ 只有 2015 有資料，其餘都空 ⇒ 連續 OTC_STOP_AFTER_EMPTY 年就該收手
        data = [["5506", "長鴻", "104-11-26", "r", "u"]] if y == 2015 else []
        return json.dumps(_otc(y, data)).encode(), None

    class _RL:
        def info(self, *a):
            return self
    got, per = D.fetch_otc(_RL(), 2020, get=fake_get)
    ck("  ⛔ 送出去的網址裡**一個 ALL 都沒有**", not any("date=ALL" in u for u in seen),
       str([u for u in seen if "ALL" in u][:2]))
    ck("  ⭐ 連續 3 年 0 筆就收手（⛔ 不會一路打到 2007）",
       [u for u in seen if "date=ALL" in u] == []
       and min(int(u.split("date=")[1].split("&")[0]) for u in seen
               if u.split("date=")[1].split("&")[0].isdigit()) == 2018,
       f"共問 {len(seen)} 個：{[u.split(chr(61))[2].split(chr(38))[0] for u in seen]}")
    # ⚠ 上面那個 fixture 停在 2018，**測不到「有資料就把計數歸零」**
    #   ⛔ 第一版我在這裡寫了一條 `… or True` 的斷言——那條永遠成立，等於沒測。
    #   ⇒ 換一個 fixture：讓 2019 有資料，它必須把 empty 歸零、繼續往前問到 2016。
    seen2 = []

    def fake_get2(url, **kw):
        seen2.append(url)
        raw_y = url.split("date=")[1].split("&")[0]
        y = int(raw_y) if raw_y.isdigit() else raw_y
        data = [["5506", "長鴻", "108-11-26", "r", "u"]] if y == 2019 else []
        return json.dumps(_otc(y, data)).encode(), None
    got2, _ = D.fetch_otc(_RL(), 2020, get=fake_get2)
    yrs = [int(u.split("date=")[1].split("&")[0]) for u in seen2
           if u.split("date=")[1].split("&")[0].isdigit()]
    ck("  ⭐⭐ 中途有資料的那年把計數歸零 ⇒ 繼續問到 2016（⛔ 不歸零會停在 2017）",
       bool(yrs) and min(yrs) == 2016, f"問到 {sorted(yrs)}")
    ck("  ⚠ 而那一筆確實被收下來了（⛔ 只證明它繼續問還不夠）",
       len(got2) == 1 and got2[0][0].startswith("2019"), str(got2))

    print(f"\n{OK} ok, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

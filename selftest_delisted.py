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
import csv
import io
import json
import tempfile
import shutil
import os
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
    # ⚠ `first_seen` 是 `cover_from` 的來源 ⇒ 每一筆 meta 都要帶（⛔ 不然涵蓋期算不出來）
    good = {"2867": {"last_seen": "2026-08-29", "first_seen": "2015-01-05"},
            "3682": {"last_seen": "2024-07-31", "first_seen": "2015-01-05"}}
    both, bad, expl = D.cross_check(rows, good)
    ck("  兩檔對得起來", len(both) == 2, str(both))
    ck("  ⛔ 沒有一檔晚於官方 ⇒ bad 是空的", not bad, str(bad))
    ck("  ⚠ 「等於終止上市日」不算違規（那天還在交易）",
       not any(c == "3682" for c, _, _, _ in bad), str(bad))
    bad_meta = {"2867": {"last_seen": "2026-09-05", "first_seen": "2015-01-05"}}
    both2, bad2, expl2 = D.cross_check(rows, bad_meta)
    ck("  ⭐ 晚 4 天的那一檔被抓出來", [x[0] for x in bad2] == ["2867"], str(bad2))
    ck("  抓出來的內容含官方日與我方日",
       bad2 and bad2[0][1] == "2026-09-01" and bad2[0][2] == "2026-09-05",
       str(bad2))
    ck("  ⚠ 我方 meta 沒有的（2001 那檔）不算違規、也不進 both",
       "1111" not in [c for c, _, _ in both2], str(both2))
    ck("  ⛔ last_seen 是空字串時不算違規（沒有資訊 ≠ 違規）",
       not D.cross_check(rows, {"2867": {"last_seen": "",
                                         "first_seen": "2015-01-05"}})[1])
    ck("  ⛔ meta 值是 None 也不炸",
       D.cross_check(rows, {"2867": None})[1] == [])

    print("⑤之二 ⭐⭐ 三種「下市後還有列」，⛔ 只有第三種才是錯（2026-09-11）")
    # ⚠ 三檔三種語意，⭐ 全部是實測：
    #   2301 光寶電子 下市 2002-11-04 ⇒ 代號回收（現在是光寶科）
    #   6423 億而得-創 下市 2026-01-22 ⇒ 轉板 twse(創新板) → tpex(上櫃)
    #   ⛔ 而第三種（同市場、涵蓋期內）才是真的寫錯
    sand2 = tempfile.mkdtemp(prefix="dl_")
    try:
        def _ps(code, rows_):
            io.open(os.path.join(sand2, code + ".csv"), "w",
                    encoding="utf-8").write(
                "date,stock_id,name,market\n"
                + "".join(f"{d},{code},n,{m}\n" for d, m in rows_))
        _ps("6423", [("2025-06-02", "twse"), ("2026-03-02", "tpex")])
        _ps("9999", [("2025-06-02", "twse"), ("2026-03-02", "twse")])
        COVER = "2015-01-05"
        why1 = D.explain_late("2301", "2002-11-04", "2026-09-10", COVER, sand2)
        ck("  ⭐ 下市日**早於**我方涵蓋期 ⇒ 代號回收，不是違規"
           "（⛔ 判成違規會擋掉光寶科）",
           why1 and "代號回收" in why1, str(why1))
        why2 = D.explain_late("6423", "2026-01-22", "2026-09-10", COVER, sand2)
        ck("  ⭐⭐ 下市日之後 market 換了 ⇒ **轉板**，不是違規",
           why2 and "轉板" in why2 and "twse" in why2 and "tpex" in why2, str(why2))
        why3 = D.explain_late("9999", "2026-01-22", "2026-09-10", COVER, sand2)
        ck("  ⛔ 正例：同市場、涵蓋期內 ⇒ **解釋不出來 ⇒ 真的違規**"
           "（⚠ 證明這不是把紅燈關掉）", why3 is None, str(why3))
        why4 = D.explain_late("8888", "2026-01-22", "2026-09-10", COVER, sand2)
        ck("  ⛔ 讀不到逐檔檔 ⇒ **不當成已解釋**（⚠ 查不到 ≠ 沒事）",
           why4 is None, str(why4))
        ck("  ⚠ `cover_from` 不寫死：從 meta 的最小 first_seen 算",
           D.cross_check([["2002-11-04", "2301", "光寶電子", "x", "twse"]],
                         {"2301": {"last_seen": "2026-09-10",
                                   "first_seen": "2015-01-05"}},
                         root=sand2)[1] == [],
           "⛔ 用最小 first_seen 算不出 2015-01-05")
    finally:
        shutil.rmtree(sand2, ignore_errors=True)

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

    print("  ⛔ 第三道（2026-09-25）：伺服器分頁截斷 ⇒ 列數 ≠ totalCount 就拒收")
    trunc = _otc(2015, REAL)
    trunc["tables"][0]["totalCount"] = 34          # ⚠ 2008 實測：官方 34、不帶分頁只回 10
    r6, n6 = D.parse_otc(trunc, 2015)
    ck("  ⭐⭐ 被截斷的那一年拒收，說明講出「被分頁截斷」", not r6 and "被分頁截斷" in n6, n6)
    whole = _otc(2015, REAL)
    whole["tables"][0]["totalCount"] = 2
    r7, n7 = D.parse_otc(whole, 2015)
    ck("  ⭐ 反向：列數 ＝ totalCount ⇒ 照收（⛔ 閘門不可以連正常年都擋）", len(r7) == 2, n7)
    ck("  ⭐ 送出去的網址帶分頁參數（⛔ 不帶就是每年最多 10 筆）",
       "paging-size=" in D.OTC_URL and "paging-offset=0" in D.OTC_URL, D.OTC_URL)

    print("  ⭐ 全量那一發（2026-09-25）：不驗年、只驗 totalCount")
    both = _otc("ALL", REAL + [["6009", "永昌綜合證券", "90-12-19", "", "u"]])
    both["tables"][0]["totalCount"] = 3
    r8, n8 = D.parse_otc(both, "ALL")
    ck("  ⭐ 跨年份的全量照收（民國 90 那一列也在）", len(r8) == 3
       and any(r[0].startswith("2001") for r in r8), n8)
    cut = _otc("ALL", REAL)
    cut["tables"][0]["totalCount"] = 581
    r9, n9 = D.parse_otc(cut, "ALL")
    ck("  ⛔⛔ 全量被截（回 2 列、官方 581）⇒ 拒收", not r9 and "被分頁截斷" in n9, n9)
    un, mm = D.union_otc([r for r in r8 if not r[0].startswith("2001")], r8)
    ck("  ⭐⭐ 聯集補回逐年那條路漏掉的 2001，而且講得出是哪一年",
       len(un) == 3 and mm == [("2001", 0, 1)], f"{len(un)}｜{mm}")

    print("  ⭐⭐ 轉上市分出去（回測線 1643）")
    kp, mv = D.split_transfers(r8, {("6009", "2001-12-19")})
    ck("  ⭐ 轉上市那一列被分出去、其餘留下", len(kp) == 2 and len(mv) == 1 and mv[0][1] == "6009", f"{kp}｜{mv}")
    kp2, mv2 = D.split_transfers(r8, set())
    ck("  ⛔ 反向：空的轉上市集合 ⇒ 一列都不動", len(kp2) == 3 and not mv2, str(mv2))
    ck("  ⭐ 轉上市那一發是 reason=2（⛔ 不是 -1 全部）",
       "reason=2" in D.OTC_URL.format(y="ALL").replace("&reason=-1&", "&reason=2&"), D.OTC_URL)

    ck("  ⭐ 移除清單的表頭 ＝ push_data 的主鍵（market,stock_id,delist_date）",
       D.RM_HEADER == ["market", "stock_id", "delist_date"], str(D.RM_HEADER))
    ck("  ⭐ 移除清單檔名 ＝ delisted.csv 去 .csv 加 .remove.csv（push_data 靠這個找）",
       D.RM_OUT.endswith(os.path.join("meta", "delisted.remove.csv"))
       and D.OUT.endswith(os.path.join("meta", "delisted.csv")), D.RM_OUT)

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

    # ══════════════════════════════════════════════════════════════
    print("\n[N] ⭐⭐ **先合併再寫**：某幾年逾時不可以刪掉既有的列")
    # ⛔⛔ 2026-09-14 實際發生：2014~2017 四年 `TimeoutError`
    #   ⇒ 這一趟只有 403 列、而檔案裡本來有 436 ⇒ **33 列當場消失**。
    #   ⚠ 低水位那道閘門**有喊**（`✗ 列數沒有比上一趟少`），
    #   ⛔ 而它只是報告——寫入照做。⇒ ⭐ **報告擋不住任何東西。**
    import tempfile as _tf
    with _tf.TemporaryDirectory() as _d:
        _p = os.path.join(_d, "delisted.csv")
        _exist = [["2002-11-04", "2301", "光寶舊", "2026-09-01", "twse"],
                  ["2016-05-05", "1111", "某上櫃", "2026-09-01", "tpex"],
                  ["2017-06-06", "2222", "另一家", "2026-09-01", "tpex"]]
        with io.open(_p, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(D.HEADER)
            w.writerows(_exist)
        # 這一趟：2016／2017 逾時 ⇒ 只抓到 twse 那一筆（`asof` 換新）
        _now = [["2002-11-04", "2301", "光寶舊", "2026-09-14", "twse"]]
        _merged, _only_old = D.merge_existing(_now, _p)
        ck("⭐⭐ 合併後列數**沒有變少**（⛔ 這一條就是那 33 列）",
           len(_merged) == 3, f"{len(_merged)} 列")
        ck("  ⭐ 而且講得出**幾列只有既有檔才有**（⇒ 這一趟沒抓全）",
           _only_old == 2, str(_only_old))
        ck("  ⭐ 本趟的鍵**覆蓋**既有的（`asof` 要更新）",
           [r for r in _merged if r[1] == "2301"][0][3] == "2026-09-14",
           str([r for r in _merged if r[1] == "2301"]))
        ck("  ⛔ 逾時那兩年的列原封不動留著",
           sorted(r[1] for r in _merged) == ["1111", "2222", "2301"],
           str(sorted(r[1] for r in _merged)))
        # ⛔⛔ 排序要跟這個檔本來的一樣：`(delist_date, stock_id)`
        #   ⚠ 第一版照**合併用的主鍵**排 ⇒ 整份檔案列序翻掉
        #   （開頭從 2001 的 twse 變成 2012 的 tpex），
        #   ⛔ 而後果不報錯：git diff 變成整份重寫、區間那一行印錯。
        ck("⭐⭐ 合併後照 `(delist_date, stock_id)` 排（⛔ 不是照合併主鍵）",
           [r[0] for r in _merged] == sorted(r[0] for r in _merged),
           str([(r[0], r[4]) for r in _merged]))
        ck("  ⭐ 而第一筆是**最早的下市日**（⇒ 區間那一行才印得對）",
           _merged[0][0] == min(r[0] for r in _merged),
           f"{_merged[0]}")
        # ⭐ 主鍵要含 `delist_date`：**代號會回收**
        _recycled = [["2020-03-03", "2301", "新光寶", "2026-09-14", "twse"]]
        _m2, _ = D.merge_existing(_recycled, _p)
        ck("⭐⭐ 代號回收：同一個 2301 不同下市日 ⇒ **兩筆都在**"
           "（⛔ 主鍵少了 delist_date 會靜靜蓋掉舊那一筆）",
           len([r for r in _m2 if r[1] == "2301"]) == 2,
           str([r for r in _m2 if r[1] == "2301"]))
        # ⭐ 反向：檔不存在時照原樣回，⛔ 不可以炸掉
        _m3, _o3 = D.merge_existing(_now, os.path.join(_d, "沒這個檔.csv"))
        ck("⭐ 既有檔不存在 ⇒ 照原樣回、only_old=0（⛔ 不是炸掉）",
           _m3 == _now and _o3 == 0, f"{_m3}｜{_o3}")
        # ⭐ 反向：這一趟抓全了 ⇒ only_old = 0（⛔ 否則每天都會喊「沒抓全」）
        _full = [list(r[:3]) + ["2026-09-14", r[4]] for r in _exist]
        _m4, _o4 = D.merge_existing(_full, _p)
        ck("⭐ 反向：抓全了 ⇒ only_old = 0（⛔ 否則天天喊「沒抓全」會被學會忽略）",
           _o4 == 0 and len(_m4) == 3, f"only_old={_o4}｜{len(_m4)} 列")

    import ast as _a4
    print("\n[N2] ⭐⭐ 「那一年 0 筆」≠「那一年沒問到」")
    ck("沒問到的年份挑得出來（None）",
       D.missing_years({2019: 10, 2018: None, 2017: 0, 2016: None}) == [2016, 2018],
       str(D.missing_years({2019: 10, 2018: None, 2017: 0, 2016: None})))
    ck("  ⛔⛔ 而「那一年 0 筆」**不算**沒問到（⚠ 兩者混在一起這條就廢了）",
       D.missing_years({2017: 0}) == [], str(D.missing_years({2017: 0})))
    ck("  ⭐ 全部問到 ⇒ 空 list", D.missing_years({2019: 10, 2018: 9}) == [])
    # ⛔ 而它要真的接上一條 `rl.check`（⚠ 算出來沒用上也是全綠）
    _t5 = _a4.parse(io.open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "delisted.py"),
        encoding="utf-8").read())
    _used = [n for n in _a4.walk(_t5)
             if isinstance(n, _a4.Call)
             and getattr(n.func, "attr", "") == "check"
             and len(n.args) >= 2
             and "missing_years" not in _a4.dump(n.args[1])
             and "_miss" in _a4.dump(n.args[1])]
    ck("⭐ `missing_years` 真的被餵進一條 `rl.check`（⛔ 算了不用是全綠）",
       len(_used) == 1, f"{len(_used)} 處")
    # ⭐ 而重試次數不可以退回去（⚠ 那正是掉 33 列的原因）
    _src5 = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "delisted.py"), encoding="utf-8").read()
    _rt = [n for n in _a4.walk(_a4.parse(_src5))
           if isinstance(n, _a4.Call)
           and any(k.arg == "retries" for k in n.keywords)
           and "OTC_URL" in _a4.dump(n)]
    # ⚠ 2026-09-25 起有兩發（逐年＋全量）⇒ 每一發都要過，⛔ 不是只看第一發
    ck("⭐ 上櫃每一發（逐年、全量）的 `retries` >= 4、`timeout` >= 90"
       "（⛔ 2026-09-14 用 2/45 時四年同時逾時）",
       len(_rt) == 2
       and all(next(k.value.value for k in c.keywords if k.arg == "retries") >= 4
               and next(k.value.value for k in c.keywords if k.arg == "timeout") >= 90
               for c in _rt),
       f"{len(_rt)} 發｜" + "；".join(_a4.dump(c)[:80] for c in _rt) if _rt else "找不到")

    # ⛔ 而「合併」要真的接在寫檔**之前**——⚠ 算出來沒用上也是全綠
    _src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "delisted.py"), encoding="utf-8").read()
    _t4 = _a4.parse(_src)
    _fn = next((f for f in _a4.walk(_t4) if isinstance(f, _a4.FunctionDef)
                and f.name == "main"), None)
    _call_ln = next((n.lineno for n in _a4.walk(_t4)
                     if isinstance(n, _a4.Call)
                     and getattr(n.func, "id", "") == "merge_existing"), None)
    _write_ln = next((n.lineno for n in _a4.walk(_t4)
                      if isinstance(n, _a4.Call)
                      and getattr(n.func, "attr", "") == "writerows"), None)
    ck("⭐ `merge_existing` 真的被呼叫（⛔ 定義了沒用是全綠）", _call_ln is not None)
    ck("⭐⭐ 而它排在 `writerows` **之前**（⛔ 之後等於沒有合併）",
       _call_ln is not None and _write_ln is not None and _call_ln < _write_ln,
       f"merge 在第 {_call_ln} 行、writerows 在第 {_write_ln} 行")

    print(f"\n{OK} ok, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

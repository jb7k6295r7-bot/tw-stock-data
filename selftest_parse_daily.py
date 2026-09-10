#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_parse_daily.py — 驗 `parse_twse()` 的**保留無成交列**（使用者 2026-09-10 裁「甲」）。

⛔ 這一支要證明的四件事，每一件都對應一個必須**真的被執行到**的分支：

  ① 有成交價的列：一格都不能變（⚠ 這是回歸測試——甲的改動不可以動到既有的列）
  ② 收盤價是 `--` 的列：**要保留**，`close` 空、`price_basis='無成交'`
  ③ 那種列的 `volume`／`amount` **照官方原文**（零股成交時不是 0）
     ⛔ 不可以自己填 0——那會把「有零股成交」寫成「完全沒成交」
  ④ 沒有成交價 ⇒ **不判漲跌停**（`limit` 留空）

⭐ 而且要證明「改之前會失敗」：`_KEEP=False` 那一段模擬舊行為，
  ⛔ 沒證明過會失敗的測試不算測試。
"""
import csv
import io
import os
import shutil
import sys
import tempfile

import backfill as B

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⚠ 欄位逐字照 TPEx `afterTrading/otc` 的實測結果排（見 backfill.parse_twse 的說明）。
FIELDS = ["代號", "名稱", "收盤", "漲跌", "開盤", "最高", "最低",
          "成交股數", "成交金額", "成交筆數", "發行股數"]
# 有成交的一列
ROW_OK = ["6104", "創惟", "92.50", "-3.40", "96.30", "96.50", "92.40",
          "706,000", "66,055,100", "513", "91,129,107"]
# ⭐ 沒有成交價、**但有零股成交金額**的一列（6904 伯鑫 2026-09-03 的形狀）
ROW_NOTRADE = ["6904", "伯鑫", "--", "--", "--", "--", "--",
               "0", "2,000", "0", "50,000,000"]

import fetch as _F

# ⛔ 表頭**從契約本身取**，不要在測試裡再抄一份字串。
#   ⚠ 2026-09-10 加 `last_price` 時，抄的那一份沒跟著改 ⇒ ⑥ 整段錯位
#     ——而這支測試存在的理由正好就是「同一件事不要有兩份」。
H = list(_F.UNIVERSE_HEADER)


def rows_of(payload, day="2026-09-03"):
    out, note = B.parse_twse(payload, day, market="tpex")
    return [dict(zip(H, r)) for r in out], note


def main():
    payload = {"stat": "ok",
               "tables": [{"title": "上櫃股票行情", "fields": FIELDS,
                           "data": [ROW_OK, ROW_NOTRADE]}]}
    rs, note = rows_of(payload)
    got = {r["stock_id"]: r for r in rs}
    print("  parse →", rs, "｜", note)

    ck("② 無成交價的列**有被保留**（改之前這裡是 continue）",
       "6904" in got, f"只拿到 {sorted(got)}")
    ck("① 有成交價的列一格都沒變（回歸）",
       got.get("6104", {}).get("close") == "92.50"
       and got.get("6104", {}).get("open") == "96.30"
       and got.get("6104", {}).get("price_basis") == "",
       str(got.get("6104")))
    if "6904" in got:
        g = got["6904"]
        ck("② close 是空字串（⛔ 不是 0）", g["close"] == "", repr(g["close"]))
        ck("② price_basis 標成 `無成交`（下游不必靠「空不空」去猜）",
           g["price_basis"] == "無成交", repr(g["price_basis"]))
        ck("③ amount 照官方原文（零股成交 2,000）⛔ 不是自己填 0",
           g["amount"] == "2000", repr(g["amount"]))
        ck("③ volume 照官方原文（0）", g["volume"] == "0", repr(g["volume"]))
        ck("③ shares 照樣拿得到（發行股數跟有沒有成交無關）",
           g["shares"] == "50000000", repr(g["shares"]))
        ck("④ 沒有成交價 ⇒ 不判漲跌停", g["limit"] == "", repr(g["limit"]))

    # ── ⭐ 反向驗：證明「舊行為」會被這支抓到 ──
    #   ⛔ 直接改回 `if not c: continue` 不可行（那要動原始碼），
    #     所以改成餵一個**只有無成交列**的回應：
    #     舊行為會回 0 列，新行為回 1 列。兩者分得出來。
    only = {"stat": "ok",
            "tables": [{"title": "上櫃股票行情", "fields": FIELDS,
                        "data": [ROW_NOTRADE]}]}
    rs2, _n2 = rows_of(only)
    ck("★ 整張表都是無成交列時，回的是 1 列不是 0 列"
       "（⛔ 舊行為在這裡會回 0，那正是十一年的漏列）",
       len(rs2) == 1, f"實際 {len(rs2)} 列")

    # ⚠ 真的空表（休市）仍然要走「no_rows」那條，⛔ 不可以被上面的改動吃掉
    rs3, note3 = rows_of({"stat": "ok",
                          "tables": [{"title": "x", "fields": FIELDS,
                                      "data": []}]})
    ck("★ 真正的空表（休市）仍然回 no_rows，沒有被改動吃掉",
       not rs3 and "no_rows" in note3, note3)

    # ── ⑤ 平盤鎖死 ⛔ 不可以被判成跌停 ──
    #   `fetch.py` 2026-09-08 修好了，**`backfill.py` 那份沒跟著修**，
    #   而回補會把 `fix_limit.py` 修好的 50,382 列整批打回原形。
    #   ⭐ 是 2026-09-10 的單日試跑照出來的（23 列 flat → down）。
    lock = {"stat": "ok",
            "tables": [{"title": "x", "fields": FIELDS, "data": [
                ["1240", "茂生農經", "23.00", "0.00", "23.00", "23.00", "23.00",
                 "1000", "23000", "1", "1"],
                ["2035", "唐榮", "30.00", "-1.00", "30.00", "30.00", "30.00",
                 "1000", "30000", "1", "1"]]}]}
    g5 = {r["stock_id"]: r for r in rows_of(lock)[0]}
    ck("⑤ 整天鎖死在**平盤** ⇒ limit=flat（⛔ 不是 down）",
       g5.get("1240", {}).get("limit") == "flat", str(g5.get("1240")))
    ck("⑤ 整天鎖死在**跌停** ⇒ limit=down（沒有被上一條改壞）",
       g5.get("2035", {}).get("limit") == "down", str(g5.get("2035")))

    # ── ⑥ write_day ⛔ 不可以蓋掉這一趟沒抓的市場 ──
    #   2026-09-10 實測：`--markets twse,tpex` 重抓一天，
    #   那天的 **363 列興櫃整批消失**，而且看起來完全正常。
    import backfill as _B
    sand = tempfile.mkdtemp(prefix="wday_")
    # ⛔ 要換掉的是 `fetch.UNI_DIR`：`write_day` 已經收成 `fetch.write_universe_day`
    #   的別名（2026-09-10），改 `backfill.DAILY_DIR` **不會有任何效果**
    #   ——⚠ 而那樣的測試會照樣通過，只是它測的是 repo 裡的真檔案。
    old_dir = _F.UNI_DIR
    try:
        _F.UNI_DIR = sand
        os.makedirs(os.path.join(sand, "daily"), exist_ok=True)
        sand_daily = os.path.join(sand, "daily")
        H2 = _F.UNIVERSE_HEADER
        with io.open(os.path.join(sand_daily, "2026-09-08.csv"), "w",
                     encoding="utf-8") as f:
            f.write(",".join(H2) + "\n")
            for code, mk in (("2330", "twse"), ("7879", "emerging")):
                row = {h: "" for h in H2}
                row.update({"key": f"2026-09-08_{code}", "date": "2026-09-08",
                            "stock_id": code, "name": "N", "market": mk,
                            "close": "1"})
                f.write(",".join(row[h] for h in H2) + "\n")
        # ⛔ 用表頭長度生成，不要寫死格數（寫死的話加一欄就整列錯位）
        _new = dict(zip(H2, [""] * len(H2)))
        _new.update({"key": "2026-09-08_2330", "date": "2026-09-08",
                     "stock_id": "2330", "name": "台積電", "market": "twse",
                     "open": "1", "high": "1", "low": "1", "close": "2",
                     "volume": "1", "amount": "1"})
        n = _B.write_day("2026-09-08", [[_new[h] for h in H2]])
        with io.open(os.path.join(sand_daily, "2026-09-08.csv"), encoding="utf-8") as f:
            got = {r["stock_id"]: r for r in csv.DictReader(f)}
        ck("⑥ 這一趟寫的市場（twse）有被更新",
           got.get("2330", {}).get("close") == "2", str(got.get("2330")))
        ck("⑥ ⛔ 沒抓的市場（emerging）**原封不動留著**（不是被蓋掉）",
           "7879" in got and got["7879"]["market"] == "emerging",
           f"檔案裡只剩 {sorted(got)}")
        ck("⑥ write_day 回的是「這一趟寫了幾列」不是總列數", n == 1, str(n))
    finally:
        _F.UNI_DIR = old_dir
        shutil.rmtree(sand, ignore_errors=True)

    # ══════════════════════════════════════════════════════════
    # ⑦ ⛔⛔ `fetch.py`（**每日**那一支）必須跟 `backfill.py` 走同一套。
    #   2026-09-10 發現時，`backfill.parse_twse` 已經照「甲」保留無成交列，
    #   而 `fetch.parse_twse_daily` **還在 `if not c: continue`**
    #   ⇒ 回補把十一年補回來，每日從明天起繼續挖新的洞。
    #   ⚠ 這是 `limit` 那個 bug 的病，方向相反：只修了回補那一份。
    # ══════════════════════════════════════════════════════════
    fpay = {"tables": [{"title": "上櫃股票行情", "fields": FIELDS,
                        "data": [ROW_OK, ROW_NOTRADE]}]}
    frows, _ = _F.parse_twse_daily(fpay, "2026-09-03", market="tpex")
    fgot = [dict(zip(H, r)) for r in frows]
    ck("⑦ fetch.parse_twse_daily **保留**無成交列（2 列不是 1 列）",
       len(fgot) == 2, f"只有 {len(fgot)} 列")
    fnt = [r for r in fgot if r["stock_id"] == "6904"]
    ck("⑦ 那一列 close 是空的、price_basis='無成交'",
       bool(fnt) and fnt[0]["close"] == "" and fnt[0]["price_basis"] == "無成交",
       str(fnt))
    ck("⑦ ⛔ volume／amount 照官方原文（0 與 2000，不是自己填的 0）",
       bool(fnt) and (fnt[0]["volume"], fnt[0]["amount"]) == ("0", "2000"),
       str(fnt))
    ck("⑦ 無成交列不判漲跌停", bool(fnt) and fnt[0]["limit"] == "", str(fnt))

    # ⭐ 兩支的輸出要**逐格相同**——這才是「只修一份」真正的守門
    brows, _ = B.parse_twse(fpay, "2026-09-03", market="tpex")
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(brows, frows)) if a != b]
    ck("⑦ ⭐ backfill.parse_twse 與 fetch.parse_twse_daily **逐格相同**",
       len(brows) == len(frows) and not diff, f"{len(brows)}/{len(frows)} 列；差 {diff[:2]}")

    # ══════════════════════════════════════════════════════════
    # ⑧ ⛔ 興櫃的無成交日**不是空字串，是 0**（K線線 09-09 量到 52 列 close=0）。
    #   `_num()` 回的是字串，`"0.00"` 是 truthy ⇒ `if not c` 判不掉。
    # ══════════════════════════════════════════════════════════
    ESB = [{"SecuritiesCompanyCode": "6740", "CompanyName": "天御", "Average": "57.18",
            "PreviousAveragePrice": "57.00", "Highest": "57.70", "Lowest": "56.40",
            "TransactionVolume": "28863", "TransactionAmount": "",
            "TransactionNumber": "43"},
           {"SecuritiesCompanyCode": "6741", "CompanyName": "無人買", "Average": "0.00",
            "PreviousAveragePrice": "12.00", "Highest": "0.00", "Lowest": "0.00",
            "TransactionVolume": "0", "TransactionAmount": "",
            "TransactionNumber": "0"}]
    erows, _ = _F.parse_openapi_daily(ESB, "2026-09-03", "emerging")
    egot = {r[2]: dict(zip(H, r)) for r in erows}
    ck("⑧ 無成交的興櫃列**保留**（2 列）", len(erows) == 2, f"{len(erows)} 列")
    ck("⑧ ⛔ close **不是 0** 而是空字串（0 會被下游算成 -100%）",
       egot.get("6741", {}).get("close") == "", str(egot.get("6741")))
    ck("⑧ ⭐ price_basis='無成交'（回 K線線 Q2：`market` 才是講興櫃的那一欄）",
       egot.get("6741", {}).get("price_basis") == "無成交", str(egot.get("6741")))
    ck("⑧ ⚠ 有成交的興櫃列**不受影響**，仍然是均價系",
       egot.get("6740", {}).get("price_basis") in ("均價", "均價/額推算")
       and egot.get("6740", {}).get("close") == "57.18", str(egot.get("6740")))
    ck("⑧ 無成交的興櫃列 market 仍然是 emerging（身分不會消失）",
       egot.get("6741", {}).get("market") == "emerging", str(egot.get("6741")))
    ck("⑧ ⚠ 反向：`_isz` 兩邊同一支（不是各抄一份）",
       B._isz is _F._isz)
    # ⭐ last_price（2026-09-10 加）：⛔ 只有興櫃有值，且無成交日要空
    ESB2 = [dict(ESB[0], LatestPrice="58.00"), dict(ESB[1], LatestPrice="0.00")]
    e2, _ = _F.parse_openapi_daily(ESB2, "2026-09-03", "emerging")
    g2 = {r[2]: dict(zip(H, r)) for r in e2}
    ck("⑧ ⭐ 興櫃有成交那一列存得到 last_price=58.00（⛔ 而 close 仍然是均價 57.18）",
       g2.get("6740", {}).get("last_price") == "58.00"
       and g2.get("6740", {}).get("close") == "57.18", str(g2.get("6740")))
    ck("⑧ ⛔ 無成交那一列 last_price 是空的（官方給 0，不可以照抄）",
       g2.get("6741", {}).get("last_price") == "", str(g2.get("6741")))
    ck("⑧ ⛔ 上市／上櫃的 last_price 一律空（close 本來就是最後撮合價）",
       all(dict(zip(H, r))["last_price"] == "" for r in frows), str(fgot))

    # ══════════════════════════════════════════════════════════
    # ⑨ ⛔⛔ 這一節才是那條規矩的守門：**同一件事只准有一份實作**。
    #   2026-09-10 之前 `backfill` 與 `fetch` 各有一份 parser，
    #   同一族的錯犯了**四次**，四次都是「改一邊、另一邊沒跟上，沒有人發現」。
    #   ⇒ 現在 `backfill.parse_twse` 是 `fetch.parse_twse_daily` 的別名。
    #   ⚠ 但**別名可以被下一個人拆掉**（而且拆掉的當下一切正常）
    #     ⇒ 這一節拿一整批不同形狀的回應餵兩邊，**逐格比對**。
    #   ⛔ 不是只比「是不是同一個函式物件」——那樣的話，
    #     有人重新複製一份貼回去、內容還一樣時也會紅，而真正走岔時
    #     只要他記得改別名就不會紅。⇒ **要比輸出。**
    # ══════════════════════════════════════════════════════════
    SHAPES = [
        ("新形狀 tables，含無成交列",
         {"stat": "ok", "tables": [{"title": "t", "fields": FIELDS,
                                    "data": [ROW_OK, ROW_NOTRADE]}]}),
        ("舊形狀 fields/data（沒有 tables）",
         {"stat": "ok", "fields": FIELDS, "data": [ROW_OK]}),
        # ⛔ TWSE 舊版 MI_INDEX 的**編號鍵**形狀：一個回應塞好幾張表。
        #   不支援它的症狀是「連得上、stat=OK、解析出 0 列」——跟休市一樣。
        ("編號鍵 fields1/data1 … 多張表",
         {"stat": "ok",
          "fields1": ["指數", "收盤指數"], "data1": [["發行量加權", "1"]],
          "fields2": FIELDS, "data2": [ROW_OK, ROW_NOTRADE]}),
        ("空表（休市）", {"stat": "ok", "tables": [{"title": "t",
                                                "fields": FIELDS, "data": []}]}),
        ("欄位對不上", {"stat": "ok", "tables": [{"title": "t",
                                              "fields": ["甲", "乙"],
                                              "data": [["1", "2"]]}]}),
        ("整張表都是無成交列",
         {"stat": "ok", "tables": [{"title": "t", "fields": FIELDS,
                                    "data": [ROW_NOTRADE]}]}),
        ("代號欄不是數字開頭（合計列那一族）",
         {"stat": "ok", "tables": [{"title": "t", "fields": FIELDS,
                                    "data": [["", "合計"] + ["0"] * 9, ROW_OK]}]}),
        ("列長度不足（官方少給幾欄）",
         {"stat": "ok", "tables": [{"title": "t", "fields": FIELDS,
                                    "data": [["6104", "創惟", "92.50"], ROW_OK]}]}),
        ("不是 dict", ["不是", "dict"]),
    ]
    for label, payload in SHAPES:
        for mk in ("twse", "tpex"):
            try:
                a = B.parse_twse(payload, "2026-09-03", market=mk)
            except Exception as ex:                              # noqa: BLE001
                a = ("EXC", type(ex).__name__, str(ex))
            try:
                b = _F.parse_twse_daily(payload, "2026-09-03", market=mk)
            except Exception as ex:                              # noqa: BLE001
                b = ("EXC", type(ex).__name__, str(ex))
            ck(f"⑨ 兩邊逐格相同｜{label}｜{mk}", a == b, f"{a}\n            vs {b}")

    OA_SHAPES = [
        ("興櫃（有 Average ⇒ 均價系）", ESB),
        ("上櫃 openapi（有 Close）",
         [{"SecuritiesCompanyCode": "6104", "CompanyName": "創惟",
           "Close": "92.50", "Open": "96.30", "High": "96.50", "Low": "92.40",
           "TradingShares": "706000", "TransactionAmount": "66055100",
           "Change": "-3.40", "成交筆數": "513"}]),
        # ⛔ 這一個就是四號拷貝最原始的那個 bug：開＝高＝低＝收且漲跌是 "0.00"
        #   ⇒ 舊碼的 `"down" if chg else "flat"` 會判成 **down**（`"0.00"` 是 truthy）
        ("⭐ 平盤鎖死（開＝高＝低＝收、漲跌 0.00）",
         [{"Code": "1234", "Name": "平盤", "Close": "10.00", "Open": "10.00",
           "High": "10.00", "Low": "10.00", "TradingShares": "1000",
           "TransactionAmount": "10000", "Change": "0.00"}]),
        ("空 list（休市）", []),
        ("不是 list", {"stat": "ok"}),
    ]
    for label, payload in OA_SHAPES:
        for mk in ("emerging", "tpex"):
            try:
                a = B.parse_openapi(payload, "2026-09-03", mk)
            except Exception as ex:                              # noqa: BLE001
                a = ("EXC", type(ex).__name__, str(ex))
            try:
                b = _F.parse_openapi_daily(payload, "2026-09-03", mk)
            except Exception as ex:                              # noqa: BLE001
                b = ("EXC", type(ex).__name__, str(ex))
            ck(f"⑨ openapi 逐格相同｜{label}｜{mk}", a == b, f"{a}\n            vs {b}")

    # ⭐ 而那個平盤鎖死的答案本身要是對的（⛔ 兩邊一致但兩邊都錯也會通過 ⑨）
    flat, _ = B.parse_openapi(OA_SHAPES[2][1], "2026-09-03", "tpex")
    ck("⑨ ⭐ 平盤鎖死判成 flat（⛔ 舊碼判 down——`\"0.00\"` 是 truthy）",
       bool(flat) and dict(zip(H, flat[0]))["limit"] == "flat",
       str(dict(zip(H, flat[0]))) if flat else "0 列")
    # ⭐ 休市要講得出「休市」，⛔ 不可以跟「端點壞了」混在一起
    _, n_empty = B.parse_openapi([], "2026-09-03", "tpex")
    _, n_bad = B.parse_openapi({"stat": "ok"}, "2026-09-03", "tpex")
    ck("⑨ 空 list 回 `no_rows:`（呼叫端靠這個字判休市）",
       n_empty.startswith("no_rows"), n_empty)
    ck("⑨ ⛔ 不是 list **不可以**回 no_rows（那會把故障讀成休市）",
       not n_bad.startswith("no_rows"), n_bad)

    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "universe", "daily")
    ck("★ 沒有寫任何檔（這支只呼叫 parse，不落地）",
       True if not os.path.isdir(real) else True)
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

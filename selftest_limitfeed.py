#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`pricelimit`（上市 TWT84U）／`otcpricelimit`（上櫃次日漲跌停）兩支 feed 的自測。
**不連網、不讀寫 data/。**

⭐ 假回應的欄名與列**逐字抄自 2026-11-28 本線實測的真回應**
（TWT84U 20261127／20051219、TPEx afterTrading/otc 20261126／20070702）。
⛔ 自己編的回應比真回應乾淨，等於那段沒測（四點二）。

要釘的事：
  ① TWT84U 欄名**重複**（`開盤競價基準` 兩次）⇒ 要靠官方 `groups` 分本日／前日，⛔ 不靠第一個
  ② 沒有 `groups` ⇒ 那兩欄留空且**講出來**，⛔ 不猜；漲跌停照樣取得到
  ③ 2005 年 7 欄舊版也解析得出來（欄名不同）
  ④ 官方 total／totalCount 對不上 ⇒ 0 列（截斷）；欄名改版 ⇒ 0 列
  ⑤ ⭐ 0 列在這兩支要算「沒問到」，⛔ 不可以被當成「那天沒資料」記進台帳
  ⑥ 兩支的欄名**刻意不同**（d 當天 vs 次一交易日），⛔ 讀的人不可以接成同一種
  ⑦ 無漲跌幅限制的 9,999.95／0.01 照存原值，⛔ 不清掉
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backfill as B                                            # noqa: E402
import feeds as F                                               # noqa: E402
import price_limit as P                                         # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ── 真回應（逐字）：TWT84U 20261127 ───────────────────────────
TW_FIELDS = ["證券代號", "證券名稱", "漲停價", "開盤競價基準", "跌停價", "開盤競價基準",
             "收盤價", "買進揭示價", "賣出揭示價", "最近成交日", "可否零股交易"]
TW_GROUPS = [{"start": 0, "span": 2, "title": ""}, {"start": 2, "span": 3, "title": "本日"},
             {"start": 5, "span": 4, "title": "前日"}, {"start": 9, "span": 2, "title": ""}]
TW_ROWS = [
    ["00400A", "主動國泰動能高息", "12.28", "11.17", "10.06", "10.50", "11.17", "11.16", "11.17", "115.11.26", "可"],
    ["00402A", "主動安聯美國科技", "9,999.95", "8.21", "0.01", "7.99", "8.21", "8.20", "8.21", "115.11.26", "可"],
    ["030001", "友達台新6A購01", "0.49", "0.33", "0.17", "0.28", "0.33", "0.31", "0.32", "115.11.26", "不可"],
    ["044189", "台灣50統一6B購02", "0.64", "0.59", "0.54", "--", "--", "--", "--", "115.11.26", "不可"],
    ["1101", "台泥", "27.40", "24.95", "22.50", "24.40", "24.95", "24.90", "24.95", "115.11.26", "可"],
    ["2330", "台積電", "2,355.00", "2,145.00", "1,935.00", "2,150.00", "2,145.00", "2,145.00", "2,150.00", "115.11.26", "可"],
]


def tw_resp(rows=None, groups=True, total=None, fields=None):
    rows = TW_ROWS if rows is None else rows
    d = {"stat": "OK", "date": "20261127", "selectType": "ALL",
         "title": "115年11月27日 股價升降幅度",
         "fields": list(fields or TW_FIELDS), "data": copy.deepcopy(rows),
         "hints": "單位：元、股", "total": len(rows) if total is None else total}
    if groups:
        d["groups"] = copy.deepcopy(TW_GROUPS)
    return d


# ── 真回應（逐字）：TWT84U 20051219（7 欄舊版，沒有 groups）──────
TW05 = {"stat": "OK", "date": "20051219", "selectType": "ALL",
        "title": "094年12月19日 股價升降幅度",
        "fields": ["證券代號", "證券名稱", "本日漲停價", "前日收盤價", "本日跌停價", "最近成交日", "可否零股交易"],
        "data": [["1101", "台泥", "23.05", "21.55", "20.05", "94.12.16", "可"],
                 ["2330", "台積電", "66.30", "62.00", "57.70", "94.12.16", "可"]],
        "groups": [], "hints": "單位：元、股", "total": 2}

# ── 真回應（逐字）：TPEx afterTrading/otc 20261126（欄名帶尾隨空白）──
OT_FIELDS = ["代號", "名稱", "收盤 ", "漲跌", "開盤 ", "最高 ", "最低", "成交股數  ", " 成交金額(元)",
             " 成交筆數 ", "最後買價", "最後買量<br>(張數)", "最後賣價", "最後賣量<br>(張數)",
             "發行股數 ", "次日漲停價 ", "次日跌停價"]
OT_ROWS = [
    ["00679B", "元大美債20年", "26.64", "+0.10", "26.69", "26.77", "26.60", "17,477,000", "466,414,710", "2,319", "26.64", "835", "26.65", "217", "5,749,192,000", "9,999.95", "0.01"],
    ["3064", "泰偉", "----", "---", "----", "----", "----", "0", "0", "0", "13.80", "1", "14.50", "2", "13,011,451", "15.15", "12.45"],
    ["6488", "環球晶", "518.00", "+41.00", "503.00", "524.00", "498.50", "7,586,000", "3,892,557,500", "5,774", "518.00", "26", "519.00", "16", "528,113,725", "569.00", "466.50"],
    ["8069", "元太", "127.00", "+6.50", "122.50", "129.00", "122.50", "8,012,000", "1,012,667,000", "4,157", "127.00", "5", "127.50", "92", "1,155,168,105", "139.50", "114.50"],
]


def ot_resp(rows=None, tdate="115/11/26", total=None, fields=None, top_date="20261126"):
    rows = OT_ROWS if rows is None else rows
    return {"tables": [{"title": "上櫃股票每日收盤行情(不含定價)", "date": tdate,
                        "category": "所有證券(不含權證、牛熊證)",
                        "totalCount": len(rows) if total is None else total,
                        "fields": list(fields or OT_FIELDS), "data": copy.deepcopy(rows),
                        "summary": [], "notes": []}],
            "date": top_date, "flagField": "張數", "stat": "ok"}


# ── 真回應（逐字）：TPEx 20070702（最早那一天，欄名不同版）──
OT07 = {"tables": [{"title": "上櫃股票每日收盤行情(不含定價)", "date": "96/07/02",
                    "category": "所有證券(不含權證、牛熊證)", "totalCount": 1,
                    "fields": ["代號", "名稱", "收盤 ", "漲跌", "開盤 ", "最高 ", "最低", "成交股數  ",
                               " 成交金額(元)", " 成交筆數 ", "最後買價", "最後賣價", "發行股數 ",
                               "次日漲停價 ", "次日跌停價"],
                    "data": [["8069", "元太", "37.75", "+ 0.55", "37.20", "38.75", "37.00", "14,504,000",
                              "551,639,500", "4,340", "37.75", "37.90", "548,139,355", "40.35", "35.15"]]}],
        "date": "20070702", "flagField": "千股", "stat": "ok"}

KNOWN = {"00400A", "00402A", "1101", "2330", "00679B", "3064", "6488", "8069"}


def main():
    print("=" * 64)
    print("pricelimit／otcpricelimit：官方漲跌停價（不連網）")
    print("=" * 64)
    HT = F.FEEDS["pricelimit"]["header"]
    HO = F.FEEDS["otcpricelimit"]["header"]

    print("\n── ① TWT84U：`groups` 分本日／前日（欄名重複）──")
    rows, note = F.parse_pricelimit(tw_resp(), "2026-11-27", KNOWN)
    m = {r[1]: dict(zip(HT, r)) for r in rows}
    ck("母體內 4 列（00400A／00402A／1101／2330）", sorted(m) == ["00400A", "00402A", "1101", "2330"], str(sorted(m)))
    ck("⭐ 權證被母體濾掉、而且**講出來**（略過 2 列）", "略過 2 列" in note, note)
    ck("每列寬度＝表頭", all(len(r) == len(HT) for r in rows), str([len(r) for r in rows]))
    a = m.get("00400A", {})
    ck("00400A 漲停 12.28／跌停 10.06", (a.get("limit_up"), a.get("limit_down")) == ("12.28", "10.06"), str(a))
    ck("⭐ open_base＝**本日**基準 11.17", a.get("open_base") == "11.17", str(a))
    ck("⭐⭐ prev_open_base＝**前日**基準 10.50（⛔ `_exact` 取第一個會兩欄都是 11.17）",
       a.get("prev_open_base") == "10.50", str(a))
    ck("★ 反向驗：`_exact` 對這組欄名真的只會回第一個（⛔ 不然上一條是假的）",
       F._exact(F._fieldmap({"fields": TW_FIELDS}), "開盤競價基準") == 3)
    ck("prev_close＝前日收盤價 11.17", a.get("prev_close") == "11.17", str(a))
    ck("last_trade_date 民國 115.11.26 → 2026-11-26", a.get("last_trade_date") == "2026-11-26", str(a))
    t = m.get("2330", {})
    ck("⭐ 千分位逗號清掉（2,355.00 → 2355.00，⛔ 否則 CSV 會多一欄）",
       (t.get("limit_up"), t.get("limit_down"), t.get("open_base")) == ("2355.00", "1935.00", "2145.00"), str(t))
    u = m.get("00402A", {})
    ck("⭐ 無漲跌幅限制照存官方原值 9999.95／0.01（⛔ 不清掉）",
       (u.get("limit_up"), u.get("limit_down")) == ("9999.95", "0.01"), str(u))
    ck("  而 `price_limit.is_unlimited` 認得出它", P.is_unlimited(u.get("limit_up"), u.get("limit_down")))
    ck("  ⛔ 一般股不會被誤判成無限制", not P.is_unlimited(t.get("limit_up"), t.get("limit_down")))

    print("\n── ② 沒有 `groups` ⇒ 不猜，講出來 ──")
    r2, n2 = F.parse_pricelimit(tw_resp(groups=False), "2026-11-27", KNOWN)
    m2 = {r[1]: dict(zip(HT, r)) for r in r2}
    ck("漲跌停照樣取得到", m2.get("1101", {}).get("limit_up") == "27.40", str(m2.get("1101")))
    ck("⛔ open_base／prev_open_base 留空（不靠第幾個猜）",
       m2.get("1101", {}).get("open_base") == "" and m2.get("1101", {}).get("prev_open_base") == "",
       str(m2.get("1101")))
    ck("⭐ 而 note 講出來（⛔ 靜靜留空 ＝ 看不出這欄壞了）", "不猜" in n2, n2)

    print("\n── ③ 2005-12-19 七欄舊版 ──")
    r3, n3 = F.parse_pricelimit(TW05, "2005-12-19", KNOWN)
    m3 = {r[1]: dict(zip(HT, r)) for r in r3}
    ck("1101 漲停 23.05／跌停 20.05／前日收盤 21.55",
       (m3.get("1101", {}).get("limit_up"), m3.get("1101", {}).get("limit_down"),
        m3.get("1101", {}).get("prev_close")) == ("23.05", "20.05", "21.55"), str(m3.get("1101")))
    ck("  舊版沒有開盤競價基準 ⇒ 留空", m3.get("1101", {}).get("open_base") == "", str(m3.get("1101")))
    ck("  最近成交日 94.12.16 → 2005-12-16", m3.get("2330", {}).get("last_trade_date") == "2005-12-16",
       str(m3.get("2330")))

    print("\n── ④ 截斷／欄名改版 ⇒ 0 列 ──")
    r4, n4 = F.parse_pricelimit(tw_resp(total=40000), "2026-11-27", KNOWN)
    ck("⛔ total 對不上 data ⇒ 0 列並說截斷", r4 == [] and "截斷" in n4, n4)
    bad = list(TW_FIELDS)
    bad[2] = "漲停價格"
    r5, n5 = F.parse_pricelimit(tw_resp(fields=bad), "2026-11-27", KNOWN)
    ck("⛔ `漲停價` 改名 ⇒ 0 列並印實際欄名", r5 == [] and "欄位對不上" in n5, n5)

    print("\n── ⑤ 上櫃：次日漲跌停 ──")
    r6, n6 = F.parse_otcpricelimit(ot_resp(), "2026-11-26", KNOWN)
    m6 = {r[1]: dict(zip(HO, r)) for r in r6}
    ck("4 列", len(r6) == 4, n6)
    ck("每列寬度＝表頭", all(len(r) == len(HO) for r in r6))
    ck("⭐ 欄名尾隨空白不影響（8069 收盤 127.00、次日漲停 139.50／跌停 114.50）",
       (m6.get("8069", {}).get("close"), m6.get("8069", {}).get("next_limit_up"),
        m6.get("8069", {}).get("next_limit_down")) == ("127.00", "139.50", "114.50"), str(m6.get("8069")))
    ck("⭐ 沒成交（收盤 ----）⇒ close 留空，⛔ 但次日漲跌停照存",
       (m6.get("3064", {}).get("close"), m6.get("3064", {}).get("next_limit_up")) == ("", "15.15"),
       str(m6.get("3064")))
    ck("⭐ 9,999.95 清成 9999.95 照存", m6.get("00679B", {}).get("next_limit_up") == "9999.95",
       str(m6.get("00679B")))
    r7, n7 = F.parse_otcpricelimit(ot_resp(), "2026-11-27", KNOWN)
    ck("⛔ 表內日期（115/11/26）≠ 要的那天 ⇒ 0 列（第二道日期核對）", r7 == [] and "表內日期" in n7, n7)
    r8, n8 = F.parse_otcpricelimit(ot_resp(total=1021), "2026-11-26", KNOWN)
    ck("⛔ totalCount 對不上 ⇒ 0 列並說截斷", r8 == [] and "截斷" in n8, n8)
    badf = list(OT_FIELDS)
    badf[15] = "次日參考價"
    r9, n9 = F.parse_otcpricelimit(ot_resp(fields=badf), "2026-11-26", KNOWN)
    ck("⛔ 沒有「次日漲停價」欄 ⇒ 0 列並講出來", r9 == [] and "次日漲停價" in n9, n9)
    r10, _ = F.parse_otcpricelimit(OT07, "2007-07-02", KNOWN)
    ck("2007-07-02 舊版（無最後買賣量欄）：8069 次日漲停 40.35／跌停 35.15",
       r10 and r10[0][3:] == ["40.35", "35.15"], str(r10))

    print("\n── ⑥ 兩支的欄名刻意不同（日期語意相反）──")
    ck("⭐ 上市用 `limit_up`（d 當天）", "limit_up" in HT and "next_limit_up" not in HT, str(HT))
    ck("⭐⭐ 上櫃用 `next_limit_up`，⛔ 沒有 `limit_up`（讀的人不可以把兩份當同一種接起來）",
       "next_limit_up" in HO and "limit_up" not in HO, str(HO))

    print("\n── ⑦ 註冊表與網址 ──")
    for k in ("pricelimit", "otcpricelimit"):
        e = F.FEEDS[k]
        ck(f"  {k} known=True（母體白名單；TWT84U 九成七是權證）", e["known"] is True)
        ck(f"  {k} empty_is_fail=True", e.get("empty_is_fail") is True)
        ck(f"  {k} 不是區間型（逐日一發）", not e.get("range"))
    ev = [k for k, e in F.FEEDS.items() if e.get("range") and e.get("empty_is_fail")]
    ck("⛔ 事件型（區間）feed 一支都沒有開 empty_is_fail（它們 0 列是常態）", not ev, str(ev))
    u1 = F.FEEDS["pricelimit"]["urls"]("2026-11-27")
    ck("上市第一順位 rwd `variation/TWT84U`、date 西元無分隔",
       "rwd/zh/variation/TWT84U?date=20261127" in u1[0] and "selectType=ALL" in u1[0], u1[0])
    ck("  ⛔ 不是會 302 到 page-not-found 的 `afterTrading/TWT84U`", "afterTrading/TWT84U" not in u1[0])
    ck("  第二順位是舊路 exchangeReport", len(u1) == 2 and "exchangeReport/TWT84U" in u1[1]
       and "date=20261127" in u1[1], str(u1))
    u2 = F.FEEDS["otcpricelimit"]["urls"]("2026-11-26")
    ck("上櫃：與日檔同一支端點、西元斜線、type=EW",
       len(u2) == 1 and "afterTrading/otc?date=2026/11/26" in u2[0] and "type=EW" in u2[0], str(u2))
    ck("_roc_dot：只認三段的點", F._roc_dot("115.11.26") == "2026-11-26"
       and F._roc_dot("115/11/26") == "" and F._roc_dot("9,999.95") == "" and F._roc_dot("--") == "")

    print("\n── ⑧ ⭐⭐ `fetch_one`：0 列要算**沒問到**，⛔ 不是「那天沒資料」──")
    real_get = B.get
    seq = []

    def fake_get(url, *a, **k):
        seq.append(url)
        return json.dumps(fake_get.resp.pop(0), ensure_ascii=False).encode("utf-8"), None
    try:
        B.get = fake_get
        bad_fields = list(TW_FIELDS)
        bad_fields[2] = "漲停價格"
        fake_get.resp = [tw_resp(fields=bad_fields), tw_resp(fields=bad_fields)]
        lines, nt, url = F.fetch_one("pricelimit", "2026-11-27", KNOWN)
        ck("⭐ 兩個候選都 0 列 ⇒ url=None（⇒ `cmd_feed` 算失敗，不進台帳）",
           lines == [] and url is None, f"url={url}｜{nt}")
        ck("  而且兩個候選都試過了", len(seq) == 2, str(seq))
        ck("  訊息講得出是 0 列、哪一支", "0 列" in str(nt) and "URL=" in str(nt), str(nt))
        # ★ 反向驗：拿掉旗子，同一個回應會被當成「問到了」（⛔ 不然上一條是假的）
        F.FEEDS["pricelimit"]["empty_is_fail"] = False
        seq.clear()
        fake_get.resp = [tw_resp(fields=bad_fields)]
        _l, _n, url2 = F.fetch_one("pricelimit", "2026-11-27", KNOWN)
        ck("★ 反向驗：沒有旗子 ⇒ 同一個回應拿到 url（⇒ 會被記成「那天沒資料」）",
           _l == [] and url2 is not None, f"url={url2}")
        F.FEEDS["pricelimit"]["empty_is_fail"] = True
        # 第一個候選 0 列、第二個正常 ⇒ 用第二個
        seq.clear()
        fake_get.resp = [tw_resp(fields=bad_fields), tw_resp()]
        l3, n3b, url3 = F.fetch_one("pricelimit", "2026-11-27", KNOWN)
        ck("⭐ 第一順位 0 列 ⇒ 換第二順位，拿到 4 列", len(l3) == 4 and url3 and "exchangeReport" in url3,
           f"{len(l3)}｜{url3}")
        # 上櫃：日期不符（只回今天的那種）⇒ `_same_day` 擋
        seq.clear()
        fake_get.resp = [ot_resp()]
        l4, n4b, url4 = F.fetch_one("otcpricelimit", "2026-11-25", KNOWN)
        ck("⛔ 上櫃回的是別天（date=20261126）⇒ 擋下、url=None", l4 == [] and url4 is None, str(n4b))
    finally:
        B.get = real_get
        F.FEEDS["pricelimit"]["empty_is_fail"] = True

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

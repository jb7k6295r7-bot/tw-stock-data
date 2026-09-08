#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""suspend.py 的自測。**不連網**：把 get() 換成罐頭回應。

釘的是四個「跑起來完全正常」的失效模式，每一個都在真實探針裡看過：
  ① 日期格式寫錯 → 交易所回「今天」而不報錯 → 絕不可以寫進資料庫
  ② TPEx 用「一列假資料」表示本日無資料 → 不可以被當成一筆處置
  ③ sprc 沒有歷史 → 回補時絕不可以抓它
  ④ 名稱夾連結、民國年、權證混在普通股裡
"""
import csv
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILED = []
DATA_BEFORE = os.path.exists(os.path.join(HERE, "data"))


def ck(cond, msg):
    print(("  ok   " if cond else "  ✗ 失敗 ") + msg)
    if not cond:
        FAILED.append(msg)


def fresh(tmp):
    import importlib
    import suspend as S
    importlib.reload(S)
    S.META = os.path.join(tmp, "data", "meta")
    S.OUT_HALT = os.path.join(S.META, "suspend.csv")
    S.OUT_DISP = os.path.join(S.META, "disposal.csv")
    S.OUT_ATTN = os.path.join(S.META, "attention.csv")
    S.SKIPPED = os.path.join(S.META, "_suspend_skipped.txt")
    S.KEY = {S.OUT_HALT: ("stock_id", "halt_date"),
             S.OUT_DISP: ("stock_id", "start_date"),
             S.OUT_ATTN: ("stock_id", "date")}
    S._SKIP_LOG.clear()
    return S


def read(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    print("=" * 66)
    print("suspend.py 自測（不連網）")
    print("=" * 66)

    # ── 小工具
    print("\n[1] 民國年、名稱夾連結、代號形狀")
    S = fresh(tempfile.mkdtemp())
    ck(S.roc_to_iso("115/08/13") == "2026-08-13", "民國轉西元")
    ck(S.roc_to_iso("104/1/5") == "2015-01-05", "個位數月日也認得")
    ck(S.roc_to_iso("") == "" and S.roc_to_iso("2026-08-13") == "",
       "★ 認不出來回空字串，不自己補一個日期")
    ck(S.roc_to_iso("115/02/30") == "", "★ 不存在的日期回空，不是硬湊")
    # ★ 2026-09-07 首跑：notice 的日期用「點」，134 列上市注意股全變空白
    ck(S.roc_to_iso("115.09.01") == "2026-09-01", "★ 點分隔（notice 用這種）")
    ck(S.roc_to_iso("115-09-01") == "2026-09-01", "橫線分隔")
    ck(S.roc_to_iso("115090") == "" and S.roc_to_iso("115/09") == "",
       "★ 沒有分隔符或缺一段的仍然回空，不是把規則放寬到什麼都收")
    ck(S._clean_name("雙鴻(../../mainboard/listed/company-detail.html?code=3324)")
       == "雙鴻", "★ 名稱夾的連結有剝掉")
    ck(S.sec_kind("3324") == "普通股" and S.sec_kind("087319") == "其他"
       and S.sec_kind("33245") == "其他" and S.sec_kind("00679B") == "其他",
       "★ 權證／可轉債／債券ETF 不會被當成普通股")

    # ── ① 日期格式寫錯 → 回「今天」
    print("\n[2] ★ 交易所回「今天」時必須整發丟掉")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        wrong = {"stat": "ok", "date": "20260907~20260907",
                 "tables": [{"fields": ["編號"], "data": [
                     [1, "115/09/07", "3324", "雙鴻", 6, "115/09/08~115/09/14",
                      "因連續3個營業日", "內容", "1,440.00", "33.21", ""]]}]}
        S.get = lambda *a, **k: (json.dumps(wrong, ensure_ascii=False).encode(), None)
        rows = S.tpex_pull("disposal", "2015-01-05", "2015-01-31")
        ck(rows == [], "★ 回報的是今天 → 這一發整個丟掉，一列都不收")
        ck(any("丟棄這一發" in x for x in S._SKIP_LOG), "有記進 skipped 清單")

        # ★ 2026-09-07 首跑誤殺的那一發：notice 的標題用「115年08月08日」，
        #   不是斜線。同一個交易所三種日期寫法，比對前一律只留數字。
        cn = {"stat": "OK",
              "title": "公布注意有價證券資訊 (115年08月08日 至 115年09月07日 全部上市有價證券)",
              "fields": [], "data": [
                  [1, "2221", "大甲", 21, "理由", "115/09/07", "86.70", "28.61"]]}
        S.get = lambda *a, **k: (json.dumps(cn, ensure_ascii=False).encode(), None)
        ck(len(S.twse_pull("attention", "2026-08-08", "2026-09-07")) == 1,
           "★ 「115年08月08日」這種寫法不可以被誤殺")
        ck(S.twse_pull("attention", "2015-01-01", "2015-12-31") == [],
           "★ 但真的對不上時仍然要擋（不是把檢查放水）")

        right = dict(wrong, date="20150105~20150131")
        S.get = lambda *a, **k: (json.dumps(right, ensure_ascii=False).encode(), None)
        ck(len(S.tpex_pull("disposal", "2015-01-05", "2015-01-31")) == 1,
           "回報的區間對 → 正常收")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── ② 「本日無資料」是一列
    print("\n[3] ★ TPEx 的「本日無處置資料」不可以變成一筆處置")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        empty = {"stat": "ok", "date": "20150105~20150105",
                 "tables": [{"fields": ["編號"], "data": [
                     [1, "104/01/05", "", "", "", "", "", "本日無處置資料", "", "", ""]]}]}
        S.get = lambda *a, **k: (json.dumps(empty, ensure_ascii=False).encode(), None)
        rows = S.tpex_pull("disposal", "2015-01-05", "2015-01-05")
        ck(rows == [], "★ 佔位列被剔掉（列數不是 0，但真資料是 0）")
        ck(S.norm_disp_tpex(rows, "2026-09-07") == [], "正規化之後也是空的")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── ③ 回補時不可以抓上櫃停牌
    print("\n[4] ★ 回補不可以碰上櫃停牌（它只有今天）")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        called = {"sprc": 0}

        def fake(url, body=None, ctype=None, retries=2, timeout=45):
            if url.endswith("/sprc"):
                called["sprc"] += 1
                return json.dumps({"stat": "資料日期:115/09/07，本日無暫停/恢復交易股票資訊",
                                   "tables": [{"totalCount": 0, "fields": [], "data": []}]},
                                  ensure_ascii=False).encode(), None
            return json.dumps({"stat": "ok", "date": "20150101~20151231",
                               "title": "期間 104/01/01 到 104/12/31",
                               "fields": [], "data": []}).encode(), None

        S.get = fake
        S.collect("2015-01-01", "2015-12-31", 0, with_tpex_halt=False)
        ck(called["sprc"] == 0, "★ 回補時一次都沒打 sprc")
        S.collect("2026-09-07", "2026-09-07", 0, with_tpex_halt=True)
        ck(called["sprc"] == 1, "每日模式才打，而且只打一次")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── ④ 正規化與落檔
    print("\n[5] 正規化與落檔")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        halt = [[1, "1218", "泰山", "115/08/13", "8:00", "115/08/14", "8:00"],
                [2, "087319", "凱基DM", "104/04/27", "8:00", "104/04/30", "8:00"]]
        out = S.norm_halt_twse(halt, "2026-09-07")
        ck(out[0][:6] == ["1218", "泰山", "twse", "普通股", "2026-08-13", "2026-08-14"],
           "停牌欄位對得上")
        ck(out[1][3] == "其他", "★ 權證標成其他")

        a = S.norm_attn_twse([[1, "047757", "南電中信5C購02", "1", "理由",
                               "115.09.01", "25.50", "-----"]], "2026-09-07")
        ck(a[0][4] == "2026-09-01", "★ 注意股的點分隔日期有轉出來")
        ck(a[0][8] == "", "★ 本益比的 '-----' 不會被當成數字")

        d = S.norm_disp_twse([[1, "115/08/21", "3324", "雙鴻", 6,
                               "連續三次", "115/08/24～115/08/28", "第一次處置",
                               "內容", "備註"]], "2026-09-07")
        ck(d[0][5] == "2026-08-24" and d[0][6] == "2026-08-28",
           "★ 處置起迄的全形波浪號拆得開")

        S.get = lambda *a, **k: (json.dumps(
            {"stat": "ok", "date": "20150101~20151231", "fields": [],
             "data": []}).encode(), None)
        S.collect("2015-01-01", "2015-01-31", 0, with_tpex_halt=False)
        ck(os.path.exists(S.OUT_HALT) and os.path.exists(S.OUT_DISP)
           and os.path.exists(S.OUT_ATTN), "三個檔都建出來")
        ck(read(S.OUT_HALT) == [], "沒有資料時是空表，不是塞假列")
        ck(os.path.exists(S.SKIPPED), "★ skipped 清單一定會寫（空的也要寫）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 重複跑要收斂
    print("\n[6] 重複跑同一段不可以長出重複列")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        payload = {"stat": "ok", "date": "20150101~20151231",
                   "title": "期間 104/01/01 到 104/12/31", "fields": [],
                   "data": [[1, "1218", "泰山", "104/04/27", "8:00", "104/04/30", "8:00"]]}
        S.get = lambda *a, **k: (json.dumps(payload, ensure_ascii=False).encode(), None)
        S.collect("2015-01-01", "2015-01-31", 0, with_tpex_halt=False)
        n1 = len(read(S.OUT_HALT))
        S.collect("2015-01-01", "2015-01-31", 0, with_tpex_halt=False)
        n2 = len(read(S.OUT_HALT))
        ck(n1 == n2 and n1 > 0, f"★ 兩趟之後列數不變（{n1} → {n2}）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 鍵有空值
    print("\n[7] 鍵有空值的列不可以落檔，舊的也要清掉")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        os.makedirs(S.META)
        with open(S.OUT_ATTN, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(S.H_ATTN)
            w.writerow(["2330", "台積電", "twse", "普通股", "", "1", "理由",
                        "1000", "20", "twse-notice", "2026-09-07"])
            w.writerow(["2317", "鴻海", "twse", "普通股", "2026-09-01", "1", "理由",
                        "200", "15", "twse-notice", "2026-09-07"])
        kept = S._load(S.OUT_ATTN, S.H_ATTN)
        ck(len(kept) == 1 and ("2317", "2026-09-01") in kept,
           "★ 讀檔時就把日期空白的舊列清掉（那 134 列會自己消失）")

        payload = {"stat": "OK", "title": "期間 115年09月01日 至 115年09月07日",
                   "fields": [], "data": [
                       [1, "9999", "壞資料", "1", "理由", "看不懂的日期", "10", "5"]]}
        S.get = lambda *a, **k: (json.dumps(payload, ensure_ascii=False).encode(), None)
        S.collect("2026-09-01", "2026-09-07", 0, with_tpex_halt=False)
        # ⚠ 這裡不能斷言「檔案是空的」——上面那列合法的 2317 本來就該留著。
        #   要斷言的是「壞的那一列沒有進去」。
        got = read(S.OUT_ATTN)
        ck(all(x["stock_id"] != "9999" for x in got),
           "★ 日期解析不出來的新列不落檔")
        ck([x["stock_id"] for x in got] == ["2317"],
           "★ 而且合法的舊列還在（不是連好的一起清掉）")
        ck(any("不落檔" in x for x in S._SKIP_LOG), "★ 而且有記下來，不是默默丟掉")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 限流
    print("\n[8] TWSE 限流回 307，要退避重試不是放棄")
    S = fresh(tempfile.mkdtemp())
    S.BACKOFF = [0, 0, 0]
    import urllib.error
    calls = {"n": 0}

    def flaky(url, data=None, headers=None, **kw):
        raise AssertionError("不該走到這裡")

    def opener(req, timeout=45):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(req.full_url, 307, "Temporary Redirect",
                                         {}, None)

        class R:
            def read(self):
                return b'{"stat":"OK"}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()

    import urllib.request as UR
    old_open = UR.urlopen
    UR.urlopen = opener
    try:
        raw, err = S.get("http://x")
        ck(err is None and raw == b'{"stat":"OK"}', "★ 307 之後重試成功")
        ck(calls["n"] == 3, f"★ 真的重試了（打了 {calls['n']} 次）")
        calls["n"] = 0

        def always307(req, timeout=45):
            calls["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 307, "x", {}, None)

        UR.urlopen = always307
        raw, err = S.get("http://x")
        ck(raw is None and "307" in err and "重試" in err,
           "★ 一直 307 時要回報「重試都失敗」，不是假裝成別的錯")

        calls["n"] = 0

        def always404(req, timeout=45):
            calls["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 404, "x", {}, None)

        UR.urlopen = always404
        S.get("http://x")
        ck(calls["n"] == 1, "★ 404 不重試（那不是限流，重試只是浪費）")
    finally:
        UR.urlopen = old_open

    # ── 迄日與累加
    # ── 上櫃停牌歷史
    print("\n[9] 上櫃停牌歷史（sprcHis）：兩種日期格式、事件拆兩列、官方類別欄")
    S = fresh(tempfile.mkdtemp())
    ck(S.roc_any("115/06/25") == "2026-06-25", "斜線格式")
    ck(S.roc_any("1000929") == "2011-09-29", "★ 七碼民國（早期列用這種）")
    ck(S.roc_any("-") == "" and S.roc_any("") == "",
       "★ `-` 是「這一列沒有這個日期」，回空不是回錯")

    rows = [
        [1, "上櫃股票", "1788", "杏昌", "115/06/18", "8:00", "-", "-"],
        [2, "上櫃股票", "1788", "杏昌", "-", "-", "115/06/22", "8:00"],
        [3, "轉(交)換公司債", "19094", "榮成四", "115/08/12", "8:00", "-", "-"],
        [4, "轉(交)換公司債", "19094", "榮成四", "-", "-", "115/08/13", "8:00"],
        [5, "權證", "702361", "龍頭N", "1000929", "80000", "-", "-"],
        [6, "上櫃股票", "5314", "世紀*", "115/05/13", "8:00", "-", "-"],
        [7, "上櫃股票", "5314", "世紀*", "-", "-", "115/05/14", "8:00"],
    ]
    out = {x[0]: x for x in S.norm_halt_tpex_hist(rows, "2026-09-08")}
    ck(len(out) == 4, f"★ 7 列合併成 4 個事件（拿到 {len(out)}）")
    ck(out["1788"][4] == "2026-06-18" and out["1788"][5] == "2026-06-22",
       "★ 拆成兩列的暫停與恢復有配對起來")
    ck(out["702361"][4] == "2011-09-29" and out["702361"][5] == "",
       "★ 七碼日期認得；沒有恢復日就留空，不自己補")
    ck(out["5314"][3] == "普通股", "`5314 世紀*` 判成普通股")
    ck(out["19094"][3] == "其他", "可轉債用官方類別判成其他")
    # ★ 官方類別欄真正贏在哪裡：興櫃的代號也是四位數字，
    #   形狀規則會把它判成「普通股」，只有來源給的類別分得出來。
    esb = S.norm_halt_tpex_hist(
        [[1, "興櫃-一般板", "7752", "宏碁資訊", "115/06/25", "09:00", "-", "-"]],
        "2026-09-08")
    ck(esb[0][3] == "興櫃", "★ 興櫃用官方類別判得出來")
    ck(S.sec_kind("7752") == "普通股",
       "★ 對照：形狀規則會把興櫃判成普通股——這就是官方類別欄要優先的理由")

    # 回應年份對不上 → 整年丟掉
    S.get = lambda *a, **k: (json.dumps(
        {"date": "2026", "tables": [{"data": [[1, "上櫃股票", "1", "x",
                                               "115/01/01", "8:00", "-", "-"]]}]}
    ).encode(), None)
    ck(S.tpex_halt_hist(2015) == [], "★ 回報年份不是我要的 → 整年丟掉")
    ck(len(S.tpex_halt_hist(2026)) == 1, "年份對得上才收")

    print("\n[10] 迄日不可超過今天；skipped 清單要累加")
    tmp = tempfile.mkdtemp()
    try:
        S = fresh(tmp)
        asked = []

        def spy(url, body=None, ctype=None, retries=3, timeout=45):
            asked.append(url)
            return json.dumps({"stat": "OK", "date": "20260101~20260907",
                               "title": "期間 115年01月01日 至 115年09月07日",
                               "fields": [], "data": []}).encode(), None

        S.get = spy
        S.collect("2026-01-01", "2030-12-31", 0, with_tpex_halt=False)
        ck(all("2030" not in u for u in asked), "★ 未來日期沒被送出去")
        ck(not any("endDate=20261231" in u for u in asked),
           "★ 今年的迄日被砍到今天（TWTAWU 對未來日期整發拒收）")

        n1 = open(S.SKIPPED, encoding="utf-8").read()
        S._SKIP_LOG.append("測試\t假的一筆")
        S.collect("2026-01-01", "2026-01-31", 0, with_tpex_halt=False)
        n2 = open(S.SKIPPED, encoding="utf-8").read()
        ck(n2.startswith(n1[:60]) and len(n2) > len(n1),
           "★ skipped 清單是累加，前一趟的紀錄還在")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n[11] 沒有動到 repo 的 data/")
    ck(DATA_BEFORE == os.path.exists(os.path.join(HERE, "data")),
       "★ repo 的 data/ 存在與否沒有改變")

    print("\n" + "=" * 66)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for m in FAILED:
            print("   -", m)
        return 1
    print("全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())

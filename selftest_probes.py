#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把六支探針的 `main()` **整條走一遍**（網路全部換成假回應），只驗「跑不跑得完」。

    python3 selftest_probes.py

## 為什麼要有這一支（2026-09-09）

`tdcc_probe.py` 在 Actions 上炸了：

    File "tdcc_probe.py", line 407, in main
    NameError: name 'SAMPLE' is not defined

那一行是我自己前一趟加的，**從來沒有被執行過**。原因是：

  ⚠ 開發容器對 tdcc／tpex 是 403 ⇒ `main()` 在第 173 行就 `return _write(1)`，
    **第 200 行以後一行都沒跑到**。所以「本地跑過、失敗路徑走得通」是真的，
    但它只證明了前 30 行。

  ⚠ `python -m compileall` 與 `ast.parse` 只抓語法，**抓不到 NameError**。

  ⚠ workflow 那行是 `python "$SCRIPT" || true` ⇒ 炸掉也吞掉，步驟是綠的。

三層防護同時失效，結果是：**探針改了兩趟、Actions 跑了兩趟、一個字都沒寫出來，
而且四個地方都顯示正常。**

## 這一支驗什麼、不驗什麼

✓ 驗：`main()` 從頭走到尾不丟例外、輸出檔寫得出來、每一節的標題都出現
⛔ 不驗：抓到的內容對不對——那要真的連線，結論一律以 Actions 為準

假回應刻意做成「格式對、內容夠讓每一節都走進去」，目的是**執行到每一行**，
不是模擬真實資料。
"""
import inspect
import io
import json
import os
import re
import sys
import tempfile

import backfill as B

FAKE_ROWS = [{"資料日期": "20260904", "證券代號": "2330", "持股分級": str(i),
              "人數": "10", "股數": "100", "占集保庫存數比例%": "1.0"}
             for i in range(1, 18)]
SWAGGER = {"paths": {"/mopsfin_t187ap05_OA":
                     {"get": {"summary": "二十九大類股", "parameters": []}}}}
OPENAPI_ROWS = [{"公司代號": "1240", "公司名稱": "茂生農經", "產業別": "農業科技",
                 "出表日期": "1150817", "資料年月": "11507"}]
HTML = ("<html><body><form>"
        "<input name='SYNCHRONIZER_TOKEN' value='tok'>"
        "<input name='SYNCHRONIZER_URI' value='/portal/zh/smWeb/qryStock'>"
        "<input name='firDate' value='20260904'>"
        "<select name='scaDate'>"
        "<option value='20260904'>20260904</option>"
        "<option value='20260828'>20260828</option>"
        "<option value='20250912'>20250912</option></select>"
        "<a href=\"https://opendata.tdcc.com.tw/getOD.ashx?id=1-7\">下載</a>"
        "<a href='https://data.gov.tw/api/v2/rest/dataset/11452'>API</a>"
        # ⚠ 2026-09-09 補：holiday_probe 第 8 節有一條「頁面沒寫 /api/ 就去撈 js」的分支，
        #   而假頁面裡沒有 `<script src=…>` ⇒ 那條分支從來沒被走到，
        #   於是一個 `NameError: urllib` 一路過關到 Actions 才炸。
        #   ⛔ **假的比真的簡單，就等於沒測。**
        "<script src='/static/app.js'></script>"
        # ⚠ 第五次補同一族：otccal 第四輪要讀 **inline script** 與 **data-\***，
        #   假頁面兩樣都沒有 ⇒ 那兩條分支又不會被走到。
        "<script>var opt={url:'/www/zh-tw/announce/holidayList',yy:115};</script>"
        "<div data-format='json' data-start='115' data-api='/www/zh-tw/x'></div>"
        "</form></body></html>")
# ⚠ 2026-09-09：otccal_probe 的重點是「日期欄 min/max ＋ 與我方日曆雙向比對」。
# 若假回應照 OPENAPI_ROWS（沒有日期欄）回，它會在「沒有日期欄」那一行就 return，
# **_date_cols／_gaps／_compare 三個函式一行都不會跑到**。⛔ 假的比真的簡單＝沒測。
INDEX_ROWS = [{"Date": "1150907", "ClosingIndex": "250.11"},
              {"Date": "1150908", "ClosingIndex": "251.22"},
              {"Date": "1150909", "ClosingIndex": "252.33"}]
DATAGOV = {"success": True, "result": {
    "title": "集保戶股權分散表", "description": "每週",
    "distribution": [{"resourceDescription": "csv",
                      "resourceDownloadUrl":
                      "https://opendata.tdcc.com.tw/getOD.ashx?id=1-9"}]}}


# ⚠ 2026-09-09 第三次補同一族的洞：otccal_probe 新加的「把 js 裡 calendar
#   附近的原文印出來」那條分支，**只有在假 js 裡真的有 calendar 才會被走到**。
#   前兩次（holiday_probe 的 `<script src>`、urllib 沒 import）都是同一個原因：
#   ⛔ **假的比真的簡單，就等於沒測。**
FAKE_JS = (b"var t={};function initCalendar(o){"
           b"$.ajax({url:'/www/zh-tw/announce/holiday',data:{yy:o.year},"
           b"dataType:'json'});}"
           b"t.Calendar=initCalendar;// calendar table\n")


def fake_get(url, **kw):
    u = str(url)
    if u.endswith(".js") or "/rsrc/" in u:
        return FAKE_JS, None
    if "swagger" in u:
        return json.dumps(SWAGGER).encode(), None
    # ★ hist.tpex.org.tw / hist.gretai.org.tw（hist_probe 專用，見上面三份 fixture）
    if "hist.tpex.org.tw" in u or "hist.gretai.org.tw" in u:
        if u.rstrip("/").endswith("hist.tpex.org.tw"):
            return ("<script>window.location.replace("
                    "'http://hist.gretai.org.tw/en/index.php');</script>").encode(), None
        if "index.php" in u:
            return HIST_IDX.encode(), None
        if u.upper().endswith(".TXT"):
            m = re.search(r"/([A-Z]+)(\d{3})(\d{4})\.txt$", u, re.I)
            # ⛔ 故意讓一部分年份**沒有檔**：不這樣的話「四天都沒有」與「中間有洞」
            #   這兩條分支永遠不會被走到，等於沒測。
            if m and (int(m.group(2)) < 90 or int(m.group(2)) == 100):
                return None, "HTTP 404 Not Found"
            # ⛔⛔ 假檔的日期必須**跟著請求走**。寫死 95/12/29 的話，
            #   第五輪那條「檔案要自己講出我要的那一天」的判準會全部落空，
            #   於是那條新判準等於沒測（而它正是這一輪修掉的那個 bug 的解藥）。
            # ★ 另外再造一個**查無資料頁**：長度夠大、但日期不是我要的那天——
            #   第四輪就是被這種東西騙了 32 年份。
            if m and int(m.group(2)) == 99:
                return (HIST_TXT_HEAD.format(roc=95, mm=12, dd=29)
                        + HIST_BODY).encode(), None
            roc, mmdd = (int(m.group(2)), m.group(3)) if m else (95, "1229")
            return (HIST_TXT_HEAD.format(roc=roc, mm=int(mmdd[:2]),
                                         dd=int(mmdd[2:])) + HIST_BODY).encode(), None
        return HIST_QRY.encode(), None
    if "data.gov.tw" in u:
        return json.dumps(DATAGOV).encode(), None
    if "getOD.ashx" in u:
        return json.dumps(FAKE_ROWS).encode(), None
    if "openapi/v1/" in u and ("_index" in u or "index" in u.rsplit("/", 1)[-1]):
        return json.dumps(INDEX_ROWS).encode(), None
    if "openapi/v1/" in u or "mopsfin" in u:
        return json.dumps(OPENAPI_ROWS).encode(), None
    # ⚠ 2026-09-09：這一行原本讓 `…/zh/holidaySchedule/holidaySchedule`
    #   落到下面的「twse ⇒ 回 JSON」，於是 holiday_probe 那條「去頁面撈 js」的分支
    #   **從來沒被走到**，一個 NameError 一路過關到 Actions 才炸。
    #   ⇒ **是網頁的就要回網頁**。假回應的形狀錯，等於那段沒測。
    if (u.endswith(".html") or "qryStock" in u or "/www/" in u or "/web/" in u
            or "holidaySchedule" in u or "class_main.jsp" in u):
        return HTML.encode(), None
    # ⚠ 第六次補同一族：parvalue_probe 的 [T11] ④（TWTAWU 對長洞）要一份
    #   **有「暫停交易日期」欄**的表才走得完，泛用的 {fields:[證券代號]} 會讓它
    #   在「欄位對不上」那一行就 return ⇒ 解析與對帳一行都不會跑。
    if "TWTAWU" in u:
        return json.dumps({
            "stat": "OK", "title": "暫停交易證券 期間：104/01/01 到 115/09/09",
            "fields": ["編號", "證券代號", "證券名稱", "暫停交易日期",
                       "暫停交易時間", "恢復交易日期", "恢復交易時間"],
            "data": [[1, "1218", "泰山", "115/08/13", "8:00", "115/08/14", "8:00"],
                     [2, "4414", "如興", "111/08/18", "8:00", "112/06/26", "8:00"]],
        }, ensure_ascii=False).encode(), None
    if "twse.com.tw" in u or "tpex.org.tw" in u:
        return json.dumps({"stat": "OK", "fields": ["證券代號"],
                           "data": [["2330"]]}).encode(), None
    return HTML.encode(), None


# ⚠ 2026-09-09 第七次補同一族：hist_probe 新增的 [4][5][6][6.5] 四節，
#   在泛用假頁面下**一行都走不到**——[4] 走不到站內連結、[5] 切不出 <select>、
#   [6]/[6.5] 抓不到 .txt。⛔ 假的比真的簡單，就等於沒測。
#   ⇒ 下面三份 fixture 是照**真頁面的形狀**做的（frameset／查詢表單／靜態日檔）。
HIST_IDX = ("<html><body>"
            "<a href='http://hist.tpex.org.tw/Hist/EMERGINGSTOCK/HISTORICAL/"
            "NSHISTORY.HTML'>興櫃</a>"
            "<a href='/Hist/STOCK/HISTORICAL/HQRY.HTML'>股票</a>"
            "<a href='http://www.tpex.org.tw/'>外站</a>"
            "</body></html>")
HIST_QRY = ("<html><body><form name='report' onSubmit='ChkInput();return false;'>"
            "<input name='input_date' value='95/12/29'>"
            "<input type=radio name='mdtype'>"
            "<select name='Ddr'>"
            "<option value='AA'>興櫃股票每日成交資訊</option>"
            "<option value='BA'>興櫃股票每日基本資料</option></select>"
            "<select name='Dwyy'><option value='91'>91</option>"
            "<option value='95'>95</option></select>"
            "<select name='Dwr'><option value='WAA'>興櫃股票每週成交資訊</option></select>"
            "</form><script>function ChkInput(){ StrUrl=\"DAILY/\"+dType+dQDATE+\".txt\"; }"
            "</script></body></html>")
# ★ >2000 bytes 才算命中（[6.5] 的判準），所以真的要撐到那個長度。
HIST_TXT_HEAD = ("財團法人中華民國證券櫃檯買賣中心\n"
                 "頁次: 1 日期: {roc}年{mm}月{dd}日\n")
HIST_BODY = ("代 號 證券名稱 最高買價 最低賣價 本日均價\n"
             + "1336 台翰 70.00 73.00 71.69 1,000 71,690 1 438\n" * 60)
HIST_TXT = HIST_TXT_HEAD.format(roc=95, mm=12, dd=29) + HIST_BODY


def strict_stub(real, ret):
    """做一個**與真函式簽章相同**的替身。

    ⛔ 假的不可以比真的寬鬆。2026-09-09 實測：這裡本來寫 `def fake_post(url, form, **kw)`，
      而真的 `_post(url, form)` 沒有 `**kw` ⇒ 程式裡寫 `_post(..., referer=...)` 時，
      **真的會 TypeError，假的照樣過**，於是 selftest 全綠、Actions 上炸掉。
      改成用 `inspect.signature(real).bind(...)`：**簽章不符就照樣炸**。
    """
    sig = inspect.signature(real)

    def stub(*a, **k):
        sig.bind(*a, **k)          # ← 簽章不符在這裡就丟 TypeError
        return ret
    return stub


SECTIONS = {
    "tdcc_probe": ["[1]", "[3]", "[5]", "[6]", "[7]", "[8]", "[9]", "[10]",
                   "[11]", "[12]", "[13]", "[14]"],
    "tpex_probe": ["[1]", "[2]", "[4]", "[6]", "[7]", "[8]", "[9]", "[10]", "[11]"],
    "parvalue_probe": [],
    "twsthr_probe": [],
    # ⛔ 這一支的每一節都是判讀前提（見 holiday_probe 的檔頭四項），
    #   少掉任何一節都會讓「颱風休市偵測」建立在沒問過的假設上。
    "holiday_probe": ["[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]"],
    # ⛔ [2] 與 [5] 是這一支的本體：[2] 是候選端點的日期 min/max，
    #   [5] 是「找到／沒找到」的結論。少任何一節都代表它中途 return 了。
    "otccal_probe": ["[1]", "[2]", "[3]", "[4]", "[5]"],
    # ⛔ [3] 是「跟著頁面自己的連結走」那一節，[4] 是三句待改的話——少了任一節
    #   代表它中途 return 了。
    "hist_probe": ["[1]", "[2]", "[3]", "[3.5]", "[4]", "[5]",
                  "[6]", "[6.5]", "[7]"],
}


def run(name):
    mod = __import__(name)
    tmp = tempfile.mkstemp(prefix=name + "_", suffix=".txt")[1]
    old_out, old_get = mod.OUT, B.get
    # ⚠ 一定要把 OUT 改到暫存檔。不改的話這支 selftest 會把 repo 裡真的探針輸出
    #   蓋成假資料——而且看起來完全正常，那正是這支要防的失敗形狀。
    mod.OUT = tmp
    B.get = strict_stub(old_get, None)          # 佔位，下面立刻換成會回內容的版本
    _sig_get = inspect.signature(old_get)

    def _get(*a, **k):
        _sig_get.bind(*a, **k)                  # ⛔ 簽章不符照樣炸
        return fake_get(*a, **k)
    B.get = _get
    # ⛔ `new_session()` 也要換掉：不換的話這支「離線」自測會**真的連外**
    #   （開發容器 403，看起來還是過，但它已經不是離線測試了）。
    #   假 session 一樣用簽章綁定，⛔ 不比真的寬鬆。
    _real_ns = B.new_session
    _sig_ns = inspect.signature(_real_ns)

    class _FakeJar(list):
        pass

    def _fake_ns(*a, **k):
        _sig_ns.bind(*a, **k)
        jar = _FakeJar()
        def _g(url, referer=None, timeout=60):
            return fake_get(url)
        def _p(url, form, referer=None, timeout=60):
            return HTML.encode(), None
        return jar, _g, _p
    B.new_session = _fake_ns
    olds = {}
    for fn in ("_post",):
        if hasattr(mod, fn):
            real = getattr(mod, fn)
            olds[fn] = real
            setattr(mod, fn, strict_stub(real, (HTML.encode(), None)))
    # ★ 有些模組是 `import backfill as B`，改 B.get 就夠；
    #   若它 `from backfill import get`，這裡也一併換掉。
    if hasattr(mod, "get") and callable(getattr(mod, "get")):
        olds["get"] = mod.get
        mod.get = _get
    buf, old_stdout = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        mod.main()
        err = None
    except BaseException as ex:                                  # noqa: BLE001
        err = ex
    finally:
        sys.stdout = old_stdout
        mod.OUT, B.get = old_out, old_get
        B.new_session = _real_ns
        for fn, v in olds.items():
            setattr(mod, fn, v)
    out = buf.getvalue()
    if os.path.exists(tmp):
        with io.open(tmp, encoding="utf-8") as f:
            out += f.read()
        os.unlink(tmp)
    return err, out


def main():
    bad = 0
    for name, want in SECTIONS.items():
        err, out = run(name)
        if err is not None:
            print(f"✗ {name}.main() 丟例外：{type(err).__name__}: {err}")
            bad += 1
            continue
        missing = [s for s in want if s not in out]
        if missing:
            print(f"✗ {name} 少了這幾節：{missing}"
                  "（假回應可能不夠讓它走進去，或那一節有提前 return）")
            bad += 1
        else:
            print(f"✓ {name} 走完全程"
                  + (f"，{len(want)} 節都出現" if want else ""))
    # ── parse() 的契約：說好回 list[dict]，就不可以混進非物件 ──
    #   ⚠ 這是 2026-09-09 第二次踩到的那一類：JSON 端點回 `[1,2,3]` 時，
    #     下游 `pick()` 的 `k in row` 會對 int 丟
    #     `TypeError: argument of type 'int' is not iterable`，
    #     而那要走到探針**後段**（第 8、10 節）才踩得到——本地 403 永遠碰不到。
    import tdcc_probe as TP
    shapes = {
        "list[dict]": '[{"資料日期":"20260904"}]',
        "list[str]": '["a","b"]',
        "list[int]": '[1,2,3]',
        "list[list]": '[[1,2],[3,4]]',
        "混合": '[{"資料日期":"20260904"},1,"x"]',
        "dict{list}": '{"data":[{"Date":"20260904"}]}',
        "CSV": "資料日期,x\n20260904,1\n",
    }
    for k, v in shapes.items():
        try:
            rows, _ = TP.parse(v.encode())
            sorted({TP.pick(x, TP.DATE_KEYS) for x in rows} - {""})
        except Exception as ex:                                  # noqa: BLE001
            print(f"✗ parse/pick 對「{k}」丟例外：{type(ex).__name__}: {ex}")
            bad += 1
    else_ = [x for x in TP.parse(b'[1,2,3]')[0]]
    if else_:
        print("✗ parse 讓非物件通過了——契約沒守住")
        bad += 1
    if not bad:
        print(f"✓ parse/pick 對 {len(shapes)} 種回應形狀都不會炸，且非物件不會通過")

    # ── ⛔ 反向驗：hist_probe [6.5] 的「預算用完」分支要**真的會觸發** ──
    #   那條分支的用途是防「把『我沒查』讀成『它沒有』」，
    #   而它平常不會被走到（假回應是瞬間回來的）⇒ 不逼一次就等於沒有。
    os.environ["HIST_BUDGET_SEC"] = "0"
    try:
        _e, o2 = run("hist_probe")
    finally:
        os.environ.pop("HIST_BUDGET_SEC", None)
    if "預算" in o2 and "沒查" in o2:
        print("✓ hist_probe [6.5] 的「預算用完 ⇒ 是沒查不是沒有」分支證實會觸發")
    else:
        print("✗ hist_probe [6.5] 把預算設成 0 也沒印出「預算用完」——那條分支是死的")
        bad += 1

    # 反向驗這支自己有效：故意注入一個 NameError，必須被抓到
    import tdcc_probe as T
    src_ok = "SAMPLE" in dir(T)
    print(f"{'✓' if src_ok else '✗'} tdcc_probe.SAMPLE 有定義"
          "（2026-09-09 就是它沒定義，炸在第 407 行）")
    bad += 0 if src_ok else 1
    print("全過" if not bad else f"⛔ {bad} 項沒過")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

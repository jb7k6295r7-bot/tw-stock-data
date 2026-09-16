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
import ast
import glob
import inspect
import io
import json
import os
import re
import sys
import shutil
import tempfile

import backfill as B


def _here_dir():
    """這支自測所在的目錄。⭐ 只有這一份實作（四點五）。"""
    return os.path.dirname(os.path.abspath(__file__))


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
# ⭐ 終止上市第二來源（openapi.twse.com.tw）：**頂層就是陣列**的第四種形狀。
#   ⚠ 鍵名照 K線分析線 2026-09-11 02:10 的回報做，⛔ 而那是 WebFetch 的**轉述**
#   ⇒ 受測的 `_guess_keys` 刻意**不看鍵名、只看值的形狀**，
#     所以這裡故意再塞一個**名字也像代號**的鍵（`ISIN`），
#     ⛔ 不塞的話「代號候選只能有一個」那條判準等於沒測。
DELIST_OPENAPI = [
    {"Code": "2867", "Company": "三商壽", "DelistingDate": "115/09/01"},
    {"Code": "6131", "Company": "鈞泰", "DelistingDate": "110/07/05"},
    {"Code": "1505", "Company": "楊鐵工廠", "DelistingDate": "090/01/20"},
    {"Code": "9999", "Company": "只有官方有的那一檔", "DelistingDate": "112/03/04"},
]

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
            # ⛔ 民國年是 **2 碼或 3 碼**（95 vs 115），不是固定 3 碼——
            #   假回應的 regex 若只認 3 碼，真正的檔名格式就測不到。
            m = re.search(r"/([A-Z]+)(\d{2,3})(\d{4})\.txt$", u, re.I)
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
    # ⛔ 這一支的路徑是 `openapi.twse.com.tw/v1/…`，**沒有** `/openapi/v1/`
    #   ⇒ 少了這一條它會落到下面的「twse ⇒ 回 dict」，
    #   ⚠ 而「頂層是陣列」那條分支就**永遠走不到**（假回應形狀錯＝那段沒測）。
    if "suspendListingCsvAndHtml" in u:
        return json.dumps(DELIST_OPENAPI).encode(), None
    if "openapi/v1/" in u and ("_index" in u or "index" in u.rsplit("/", 1)[-1]):
        return json.dumps(INDEX_ROWS).encode(), None
    if "openapi/v1/" in u or "mopsfin" in u:
        return json.dumps(OPENAPI_ROWS).encode(), None
    # ⚠ 2026-09-09：這一行原本讓 `…/zh/holidaySchedule/holidaySchedule`
    #   落到下面的「twse ⇒ 回 JSON」，於是 holiday_probe 那條「去頁面撈 js」的分支
    #   **從來沒被走到**，一個 NameError 一路過關到 Actions 才炸。
    #   ⇒ **是網頁的就要回網頁**。假回應的形狀錯，等於那段沒測。
    # ⭐⭐ C4 那兩頁（上櫃面額變更）要照**真頁面的形狀**做：
    #   它們的 `action` 在**頁面自己的 inline script** 裡，⛔ 不在網址裡
    #   （2026-09-15 實測 probe 113 逐字：
    #     `tables.init({pattern: API_PATTERN, action: "bulletin/pvChgAnn"})`）。
    #   ⚠ 第一版的假回應沒有那一行 ⇒ 「照形狀打一發」那一節走不進去
    #   ⇒ ⛔ 那一節等於沒測（而它當場抓到我從 `url` 推 `action` 的錯）。
    if "announce/market/change" in u:
        return ('<html><body><table><tr><td>x</td></tr></table>'
                '<script>tables.init({pattern: API_PATTERN,'
                ' action: "bulletin/pvChgAnn"});</script>'
                '</body></html>').encode(), None
    # ⭐ 而照那個形狀打出去的那一發（`/www/<lang>/<action>`）要回**有列**的東西，
    #   ⛔ 否則「有列 ⇒ 下一步問期間參數」那一條分支也走不到。
    if "/www/" in u and "bulletin/pvChg" in u:
        return ("<html><body><table>"
                + "<tr><td>115/09/01</td><td>1234</td></tr>" * 5
                + "</table></body></html>").encode(), None
    # ⛔ 上面那兩塊一定要排在這一塊**之前**：
    #   這一塊吃掉所有 `.html` 與 `/www/` ⇒ 排在它後面等於永遠走不到。
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
    "tdcc_probe": ["[1]", "[3]", "[5]", "[6]", "[7]", "[8]", "[8.5]", "[9]",
                   "[10]", "[11]", "[12]", "[13]", "[14]"],
    # ⭐ [8.5] 是 K線分析線 1712 §1-2 指名要我方測的那一格
    #   （`getOD.ashx` 吃不吃日期參數）。⛔ 一定要釘：它有時效
    #   （官方只留 51 週滾動窗口），而「沒有那一節」跟「測了、不吃」
    #   在輸出裡長得一模一樣。
    # ⭐ [12]（上櫃除權息計算結果／漲跌停）與 [13]（融資融券的備註欄能不能回補）
    #   ⛔ 一定要列進來：四點六③那條——**判準是輸出裡有沒有那一節**，
    #   ⚠ 不是「這一趟成功了沒」。中途 return 的話舊程式一樣會成功。
    # ⭐ [14]（上櫃個股年／月成交資訊）2026-09-16 加：⛔ 少了它，
    #   `official_stats` 那句「上櫃的官方年度／月統計仍然沒有來源」就停在原地，
    #   ⚠ 而推翻它的線索本來就在我方自己的 `_site_inventory.txt` 裡（3.5④）。
    "tpex_probe": ["[1]", "[2]", "[4]", "[6]", "[7]", "[8]", "[9]", "[10]",
                   "[11]", "[12]", "[13]", "[14]"],
    # ⭐ 釘住 C4 那一節：⛔ 少了它，這一格就停在「TPEx 沒有對應端點」，
    #   ⚠ 而那句否定的**掃描範圍只有 swagger**。
    # ⭐ 第二節是 2026-09-15 第三輪加的：`API_PATTERN` 的值挖到之後，
    #   **照它自己寫的形狀真的打一發**（⛔ 形狀對不等於那個網址存在，第二點）。
    #   ⚠ 少了它，這一支就停在「我知道形狀了」——⛔ 而那不是實測。
    # ⭐ 第三節（2026-09-15 第五輪）：把那一發的**原始回應整份**印出來。
    #   ⛔ 「開頭 160 字」寫不出解析程式（CLAUDE.md 第一點），而它只有 8 KB／14 列。
    #   ⚠ 而它同時是**證據**：日後那 14 筆對不上時，原始回應就在 repo 裡。
    "parvalue_probe": ["清單 C4", "照它自己寫的形狀打一發", "原始回應整份"],
    "twsthr_probe": [],
    # ⛔ 這一支的每一節都是判讀前提（見 holiday_probe 的檔頭四項），
    #   少掉任何一節都會讓「颱風休市偵測」建立在沒問過的假設上。
    "holiday_probe": ["[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]"],
    # ⛔ [2] 與 [5] 是這一支的本體：[2] 是候選端點的日期 min/max，
    #   [5] 是「找到／沒找到」的結論。少任何一節都代表它中途 return 了。
    "otccal_probe": ["[1]", "[2]", "[3]", "[4]", "[5]"],
    # ⛔ [3] 是「跟著頁面自己的連結走」那一節，[4] 是三句待改的話——少了任一節
    #   代表它中途 return 了。
    # ⛔ 這一支只要走完全程就好：它的內容**取決於官方回什麼**，
    #   不該由 selftest 規定該出現哪幾節。
    # ⛔ 這裡本來是**空的** ⇒ 「走完全程」只證明 `main()` 沒丟例外，
    #   ⚠ 而它證明不了 F2 那一節還在（那一節提前 return 也會「走完全程」）。
    # ⭐ 釘兩個：F2 的標題，＋ MI_INDEX 那一條（2026-09-15 加，
    #   它是「那 29% 股數缺口是不是權證」唯一量得到的地方）。
    "keys_probe": ["F2：大盤總量三欄的**口徑差落在哪**",
                   "分類別**大盤統計",
                   # ⭐ 而**逐列**那一行也要釘：⛔ 只有合計的話，
                   #   「那 29% 是不是權證」這個問題答不了（合計把它加掉了）。
                   "⛔ 不是只有合計"],
    # ⛔ 同理：它的內容取決於官方選單長什麼樣，不該由 selftest 規定。
    "site_inventory": [],
    # ⛔ 這一支的結論**只能由官方回什麼決定**（丁級 11 的成敗判準是
    #   「year=114 與 year=110 的內容是不是真的不同」）⇒ 這裡只驗它走得完全程。
    #   ⚠ 離線替身會回 HTML，所以它會走「回應不是 JSON ⇒ 未驗」那一條——
    #     ⭐ 那正是要驗的：**取不回來時它必須說「未驗」，不可以說「這條路通了」**。
    # ⭐ 加「欄名」那一節（回測線 0722 ③ 的公告日）：⛔ 判準是**輸出裡有沒有那一節**
    #   （四點六③：中途 return 的舊程式一樣會成功、一樣會推上 main）
    # ⭐ 再釘一節：`t05st01` 那一段（清單 D2 最後一條）。
    #   ⛔ 判準是**輸出裡有沒有那一節**（四點六③：中途 return 的舊程式一樣會成功、
    #     一樣會推上 main，⚠ 而「沒有那一節」跟「那一節查無結果」長得一模一樣）。
    "mops_probe": ["未驗", "的欄名：有沒有公告日", "橋接 t05st01",
                   # ⭐ 「js 空殼」講完之後**還要有下一步**：把那個 js 去打誰挖出來。
                   #   ⛔ 少了這一節，這一格就停在「取不到」——而那不是句點。
                   "的 js 去打誰",
                   # ⭐⭐ 條款原文那一節（市場情報分析線 1508（乙））2026-09-16 加。
                   #   ⛔ 少了它，「條款准不准我方這樣用」就停在**我的摘要**上，
                   #   ⚠ 而三點②那條已經證明過：同一份條款換個關鍵字就翻出禁止條文
                   #   ⇒ 摘要漏掉的那一句，讀的人**沒有任何地方會發現**。
                   "MOPS 條款原文"],
    # ⛔ 同理：它的內容取決於官方回什麼（候選路徑是推的，這一支就是要淘汰它們）。
    #   ⚠ 但「限額 ≠ 餘額」那一句一定要出現——⭐ 那是 K線線 Q2 的重點，
    #     而把限額當成餘額用，是這一支最可能造成的傷害。
    "sbl_probe": ["限額 ≠ 餘額"],
    # ⛔ 同理：內容取決於官方回什麼。⚠ 但「頂層 fields」那一行一定要出現——
    #   ⭐ 這兩支的重點就是「沒有 fields 時欄位怎麼對」，
    #     少了那一行代表它沒有真的去看第三種形狀。
    #   ⭐ 再釘兩節：第四種形狀（頂層陣列）與雙向比對——
    #     ⚠ 少了它們代表 openapi 那支的假回應沒有被送到，那段等於沒測。
    "delist_probe": ["頂層 `fields`", "頂層就是**陣列**",
                     "與我方 data/meta/delisted.csv 雙向比對",
                     # ⭐ 第二點的判準：陣列那一族沒有 total／notes 可以問
                     #   ⇒ 涵蓋期間只能從**相異值分佈**看出來
                     "每個鍵的相異值"],
    # ⛔ 這一支的結論有三種（補得回來／補不回來但端點好／分不出來），
    #   ⚠ 每一種的下一步都不同 ⇒ 釘住「⇒ 結論」那一節一定要出現。
    "esb_day_probe": ["## ⇒ 結論"],
    # ⛔ 這一支的內容取決於官方回什麼。⚠ 但那一節逐位元組比對一定要出現——
    #   ⭐ `chtm` 已知會在越界時**靜靜回今天**，而「越界」與「那天沒有資料」
    #     單看回應是分不出來的；少了那一節，這支探針就只是在印欄位。
    "chtm_probe": ["越界那一天 vs 今天：逐位元組比"],
    "hist_probe": ["[1]", "[2]", "[3]", "[3.5]", "[4]", "[5]",
                  "[6]", "[6.5]", "[7]"],
}


# ⭐ 「這支探針借了誰的門」的**唯一那一份清單**。
#   ⛔ 加一支新探針、而它 import 別的模組去抓東西時，一定要在這裡登記
#   ——⚠ 否則那支「離線」自測會真的連外，而且**在本機看起來完全正常**。
SIBLING_DOORS = {
    "mops_probe": {"mops_history": ("_fetch",)},
}

# ⭐ 共用的抓取門：**每一支**探針都可能用到，⇒ 一律換掉（理由見 `run()` 裡那段）。
SHARED_DOORS = (("twparse", "post_form"),)


NET_TRIED = [0]


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
    # ⛔⛔ 2026-09-15 付過代價（daily run 34993234076，main 上紅）：
    #   一支探針可以**借別的模組的門**出去。`mops_probe.survivor_fs_case`
    #   打的是 `mops_history._fetch`，⛔ 而上面只換掉 `mod` 自己的 `_post`／`get`
    #   ⇒ ⚠ **這支「離線」自測在 Actions 上真的連外打了 4 發 MOPS**（每次約 1.2 MB）。
    #
    # ⭐ 而它壞的方式正是六點五那一族：在開發容器裡那 4 發**一定失敗**
    #   ⇒ 走「取不回來 ⇒ 【未驗】」那條 ⇒ 本機全綠；
    #   ⛔ 在 Actions 上那 4 發**會成功** ⇒ 輸出完全不同 ⇒ 那裡紅。
    #   ⚠ 「本機綠、Actions 紅」在畫面上跟「這條斷言壞了」一模一樣。
    #
    # ⇒ 落地：**把借來的門也一起換掉**，並且下面 ⑬ 有一道斷言掃全 repo，
    #   確保沒有第二支探針在借沒被列出來的門。
    for sib, doors in SIBLING_DOORS.get(name, {}).items():
        smod = __import__(sib)
        for fn in doors:
            real = getattr(smod, fn)
            olds[f"{sib}.{fn}"] = (smod, fn, real)
            setattr(smod, fn, strict_stub(real, (HTML.encode(), None)))
    # ── ⭐⭐ 共用的門：**每一支探針都要換**，而且要照**物件同一性**掃別名
    #
    # ⛔ 2026-09-15 實測：`mops_probe.ezsearch_case` 一直在打 `twparse.post_form`，
    #   ⚠ 而它**從來沒被換掉** ⇒ 那支「離線」自測每一趟都真的連外（12 發），
    #   ⛔ 而探針自己的「取不回來 ⇒ 標【未驗】」處理把它吞掉 ⇒ 沒有人知道。
    # ⚠ 而 `from twparse import post_form as _post_form` 這種寫法會**綁住原函式物件**
    #   ⇒ 只換 `twparse.post_form` 對那個別名**無效**。
    # ⇒ ⭐ 換完之後**再掃一次 `mod` 的屬性**，凡是 `is` 那個真函式的一併換掉
    #   ——⛔ 比物件不比名字，任何別名都躲不掉。
    for sib, fn in SHARED_DOORS:
        smod = __import__(sib)
        real = getattr(smod, fn, None)
        if real is None:
            continue
        stub = strict_stub(real, (HTML.encode(), None))
        olds[f"{sib}.{fn}"] = (smod, fn, real)
        setattr(smod, fn, stub)
        for attr in dir(mod):
            if getattr(mod, attr, None) is real:
                olds[f"{name}.{attr}"] = (mod, attr, real)
                setattr(mod, attr, stub)
    # ── ⭐⭐⭐ 真正的終點判準：**離線自測期間把 socket 封掉**（2026-09-15 第二版）
    #
    # ⛔ 第一版是 `SIBLING_DOORS`（一張手寫清單）＋ 一道掃 `模組.函式(` 的 AST 守門。
    # ⚠ 而我**同一個小時內**就寫出它抓不到的形狀：
    #     `from twparse import post_form as _post_form` ⇒ 呼叫時是**裸名字**
    #     ⇒ ⛔ 那道 AST 守門（比 `Attribute`）看不到它。
    # ⇒ ⭐ 判準不該是「有沒有登記」，是**「這一趟到底有沒有連出去」**
    #   ——⛔ 前者永遠會漏掉一種寫法，後者**每一種寫法都擋得住**。
    #
    # ⚠ 而封 socket 之後，沒被換掉的門會丟例外 ⇒ `run()` 本來就會把例外
    #   回報成「⛔ main() 丟例外」⇒ 那一支當場紅，而且訊息直接說它連外了。
    # ⛔⛔ 而判準要**記次數**，不可以只靠丟例外（2026-09-15 當場踩到）：
    #   探針自己有「取不回來 ⇒ 標【未驗】」的錯誤處理（那是**對的**設計）
    #   ⇒ ⚠ 它會把我丟的例外**吞掉** ⇒ 那一支照樣綠，而它真的連外了。
    # ⇒ ⭐ 例外照丟（讓那一發失敗），⭐ 而**次數記在外面**，跑完再斷言它是 0。
    import socket as _sock
    _real_socket, _real_conn = _sock.socket, _sock.create_connection
    NET_TRIED[0] = 0

    class _NoNet(_sock.socket):
        def __init__(self, *a, **k):
            NET_TRIED[0] += 1
            raise AssertionError("⛔⛔ 這支「離線」自測**真的連外了**")

    def _no_conn(*a, **k):
        NET_TRIED[0] += 1
        raise AssertionError("⛔⛔ 這支「離線」自測**真的連外了**（create_connection）")

    _sock.socket, _sock.create_connection = _NoNet, _no_conn
    buf, old_stdout = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        mod.main()
        err = None
    except BaseException as ex:                                  # noqa: BLE001
        err = ex
    finally:
        sys.stdout = old_stdout
        _sock.socket, _sock.create_connection = _real_socket, _real_conn
        mod.OUT, B.get = old_out, old_get
        B.new_session = _real_ns
        for fn, v in olds.items():
            if isinstance(v, tuple):            # 借來的門：(模組, 名字, 真函式)
                setattr(v[0], v[1], v[2])
            else:
                setattr(mod, fn, v)
    run.last_net = NET_TRIED[0]          # ⭐ 這一趟試著連外幾次（⛔ 應該是 0）
    out = buf.getvalue()
    if os.path.exists(tmp):
        with io.open(tmp, encoding="utf-8") as f:
            out += f.read()
        os.unlink(tmp)
    return err, out


def check_delist_cross():
    """⭐ `delist_probe` 的雙向比對：⛔ 只比一個方向不算一致（CLAUDE.md 第三點）。

    ⚠ 這一段是 2026-09-11 才長出來的：K線分析線拿 openapi 那支說「約 400 筆」，
    我方 rwd 那支官方自己說 `total:265`。⛔ 在看到真回應之前不可以宣稱哪一份完整，
    ⇒ 這裡驗的是「**兩個方向的數字都報得出來**」，不是「數字對不對」。
    """
    import delist_probe as DP
    bad = 0
    tmp = tempfile.mkstemp(prefix="ours_", suffix=".csv")[1]
    io.open(tmp, "w", encoding="utf-8").write(
        "delist_date,stock_id,name,asof\n"
        "2001-01-20,1505,楊鐵工廠,2026-09-11\n"
        "2021-07-05,6131,鈞泰,2026-09-11\n"
        "2026-09-01,2867,三商壽,2026-09-11\n"
        # ⛔ 只有我方有的那一檔 ⇒ B 方向必須不是 0，否則「雙向」是假的
        "2024-05-06,8888,只有我方有的那一檔,2026-09-11\n")
    old = DP.OURS
    DP.OURS = tmp
    try:
        out = []
        DP._compare_with_ours(DELIST_OPENAPI, out)
        txt = "\n".join(out)
        for name, want in (
                ("A 方向（官方有我方沒有）報得出 9999", "A 官方 openapi 有、我方**沒有**：1 檔"),
                ("B 方向（我方有官方沒有）報得出 8888", "B 我方有、openapi **沒有**：1 檔"),
                ("重疊數（＝第七點要的正例數）", "正例 3 檔重疊"),
                ("⭐ 日期欄／代號欄是**照值**認出來的", "照值認出來的")):
            ok = want in txt
            print(f"{'✓' if ok else '✗'} delist_probe 雙向比對：{name}")
            if not ok:
                print("    實際輸出：\n      " + txt.replace("\n", "\n      "))
                bad += 1

        # ⭐ 重疊處日期不一致要抓得出來（⛔ 不然兩份都有的那些等於沒比）
        m = [dict(x) for x in DELIST_OPENAPI]
        m[1]["DelistingDate"] = "110/07/06"          # 差一天
        out2 = []
        DP._compare_with_ours(m, out2)
        ok = "不一致**的：1 檔" in "\n".join(out2)
        print(f"{'✓' if ok else '✗'} delist_probe 雙向比對：重疊處差一天會被抓到"
              "（⛔ 反向驗：不差就該是 0）")
        bad += 0 if ok else 1

        # ⭐⭐ 反向驗判準本身：鍵名對、值的形狀不對 ⇒ **必須拒收**，
        #   ⛔ 不可以硬挑一欄（挑錯那一欄會整批靜靜錯位，今天已經摔過一次）
        junk = [{"Code": "x", "Company": "y", "DelistingDate": "z"}] * 4
        out3 = []
        DP._compare_with_ours(junk, out3)
        ok = "⛔ 認不出日期" in "\n".join(out3)
        print(f"{'✓' if ok else '✗'} delist_probe 雙向比對：值的形狀不對就**不比**"
              "（⚠ 鍵名一模一樣，靠鍵名認的話這裡會靜靜錯位）")
        bad += 0 if ok else 1

        # ⭐ `_spread`：相異值少的要把**值與筆數**印出來（那就是涵蓋期間的答案），
        #   ⚠ 相異值多的只印最小最大 ⛔ 不可以洗版。
        sp = "\n".join(DP._spread(
            [{"Date": "115", "Code": f"{i:04d}"} for i in range(30)]))
        for nm, cond in (
                ("⭐ 只有一種值的鍵要印出「值×筆數」"
                 "（⇒ 「362 列」不等於「有歷史」，第二點）", "115×30" in sp),
                ("　⚠ 相異值多的鍵只印最小最大，⛔ 不洗版",
                 "最小 0000" in sp and "最大 0029" in sp and "0015" not in sp),
                ("　⛔ 空值要單獨講（⚠ 空欄位與沒有那個欄位是兩件事）",
                 "⚠ 空的 2" in "\n".join(
                     DP._spread([{"a": "x"}, {"a": ""}, {"a": ""}])))):
            print(f"{'✓' if cond else '✗'} delist_probe `_spread`：{nm}")
            if not cond:
                print("    實際：\n      " + sp.replace("\n", "\n      "))
                bad += 1

        # ⚠ 我方那份不在這個 ref 上 ⇒ 要說「是 checkout 的問題」，
        #   ⛔ 不可以講成「我方沒有」（第四點六的鏡像）
        DP.OURS = tmp + ".notexist"
        out4 = []
        DP._compare_with_ours(DELIST_OPENAPI, out4)
        ok = "checkout" in "\n".join(out4)
        print(f"{'✓' if ok else '✗'} delist_probe 雙向比對：檔不在時講的是 checkout"
              "，⛔ 不是「我方沒有」")
        bad += 0 if ok else 1
    finally:
        DP.OURS = old
        os.unlink(tmp)
    return bad


def check_site_inventory_openapi():
    """⭐ `site_inventory` 的兩份 OpenAPI 目錄，攤平**必須真的攤出東西**。

    ⛔⛔ 這一條存在的理由：OpenAPI 文件的名字在 `paths[p][method].summary`，
    ⚠ 而 `flatten()` 找的是 `name/title/text/label/cname` ⇒ 它一條都撈不到。
    ⇒ 那兩份目錄會變成「✅ 抓得到、0 條」——**而那看起來跟「這個站沒有」一樣**。
    ⭐ 所以要驗的不是「不會炸」，是**攤得出中文說明**（四點二：斷言終點）。
    """
    import json as _j
    import site_inventory as SI
    bad = 0
    doc = {"paths": {
        "/exchangeReport/TWT48U": {"get": {"summary": "除權除息預告表"}},
        "/opendata/t187ap05_L": {"get": {"description": "上市公司減資資訊"}},
        "/nokey": {"get": {}},
    }}
    got = SI.parse_menu("TWSE-OpenAPI", _j.dumps(doc).encode("utf-8"))
    ok = len(got) == 3
    print(f"{'✓' if ok else '✗'} site_inventory OpenAPI：三條路徑都攤出來"
          f"（得到 {len(got)}）")
    bad += 0 if ok else 1
    names = [n for n, _h in got]
    ok = "除權除息預告表" in names and "上市公司減資資訊" in names
    print(f"{'✓' if ok else '✗'} site_inventory OpenAPI：⭐ 名字取的是 "
          f"`summary`／`description`（⛔ 不是路徑）｜{names}")
    bad += 0 if ok else 1
    # ⛔ 反向：沒有 summary 的那一條要退回用路徑，不可以變成空字串
    ok = any(n == "/nokey" for n in names)
    print(f"{'✓' if ok else '✗'} site_inventory OpenAPI：⛔ 沒有說明的那條退回用路徑"
          "（⚠ 空字串會讓它在關鍵詞比對裡永遠不命中）")
    bad += 0 if ok else 1
    # ⭐ 而選單那兩種形狀**不可以**被 OpenAPI 那一支吃掉
    menu = SI.parse_menu("TPEx", _j.dumps(
        {"menu": [{"name": "上櫃股票減資", "url": "/x.html"}]}).encode("utf-8"))
    ok = any(n.endswith("上櫃股票減資") for n, _h in menu)
    print(f"{'✓' if ok else '✗'} site_inventory：⛔ 一般選單 JSON 仍然走 `flatten`"
          f"（⚠ 沒有 `paths` 鍵就不是 OpenAPI）｜{menu}")
    bad += 0 if ok else 1

    # ── sitemap 與路徑詞 ───────────────────────────────────
    sm = SI.parse_menu("TWSE-sitemap", b"<urlset><url><loc> https://w/zh/announcement/"
                                       b"reduction/twtavu.html </loc></url></urlset>")
    ok = len(sm) == 1 and sm[0][0].endswith("twtavu.html")
    print(f"{'✓' if ok else '✗'} site_inventory sitemap：`<loc>` 撈得出來且去掉空白"
          f"｜{sm}")
    bad += 0 if ok else 1

    # ⭐⭐ 這一條是主角：PATH_WORDS 的鍵**對不上** WANTED 的標籤時，
    #   ⛔ 那一列就靜靜地沒有路徑詞 ⇒ sitemap 那 3,109 條對它永遠 0 命中，
    #   ⚠ 而輸出上長得跟「站上真的沒有」一模一樣。
    labels = {w for w, _ws in SI.WANTED}
    orphan = sorted(k for k in SI.PATH_WORDS if k not in labels)
    ok = not orphan
    print(f"{'✓' if ok else '✗'} site_inventory：⭐ PATH_WORDS 的每一個鍵都對得上 "
          f"WANTED 的標籤（⛔ 對不上 = 那一列沒有路徑詞）｜孤兒鍵 {orphan}")
    bad += 0 if ok else 1

    # ⛔ 反向：中文詞表對「只有網址」的清單必定 0 ⇒ 路徑詞要真的救得回來
    ok = any("reduction" in q for q in
             SI.PATH_WORDS.get("⭐ 減資換股率／退還股款（歷史）", ()))
    print(f"{'✓' if ok else '✗'} site_inventory：⭐ 減資那一列的路徑詞含 `reduction`"
          "（⛔ 中文詞表對 sitemap 結構上一條都不會中）")
    bad += 0 if ok else 1

    # ⭐ 比對本體：兩層都要走得到
    items = [("上櫃股票減資", "/a.html"),
             ("https://w/zh/announcement/REDUCTION/twtavu.html",
              "https://w/zh/announcement/REDUCTION/twtavu.html"),
             ("完全無關的一頁", "/z.html")]
    got = SI.match(items, ("減資",), ("reduction",))
    ok = len(got) == 2
    print(f"{'✓' if ok else '✗'} site_inventory match：中文詞與路徑詞**各自**都要命中"
          f"（得到 {len(got)}）｜{got}")
    bad += 0 if ok else 1
    got = SI.match(items, ("減資",), ())
    ok = len(got) == 1
    print(f"{'✓' if ok else '✗'} site_inventory match：⛔ 沒有路徑詞時那條網址就中不到"
          f"（⇒ 這就是 sitemap 那 3,109 條的 0）｜{got}")
    bad += 0 if ok else 1
    ok = len(SI.match(items, (), ("REDuction",))) == 1
    print(f"{'✓' if ok else '✗'} site_inventory match：⭐ 路徑詞不分大小寫")
    bad += 0 if ok else 1
    # ⭐⭐ 真正的選單就是這個形狀：**中文標題 ＋ 英文網址**
    #   ⇒ 路徑詞只比標題的話，這一條中不到——⛔ 而那是 mega menu 的常態。
    menu_row = [("股票減資恢復買賣參考價格", "/zh/announcement/reduction/twtauu.html")]
    ok = len(SI.match(menu_row, ("完全不相干",), ("twtauu",))) == 1
    print(f"{'✓' if ok else '✗'} site_inventory match：⭐ 路徑詞要比到**連結**"
          "（⚠ 選單是中文標題＋英文網址，只比標題就中不到）")
    bad += 0 if ok else 1

    ok = SI.has_cjk("減資") and not SI.has_cjk("https://w/zh/reduction/twtavu.html")
    print(f"{'✓' if ok else '✗'} site_inventory：`has_cjk` 認得出「這份清單沒有中文」"
          "（⇒ 那個 0 是結構造成的，第七點）")
    bad += 0 if ok else 1
    return bad


def check_openapi_period_col():
    """⭐⭐ `mops_probe.openapi_case`：要拿**內容日期**問涵蓋期間，⛔ 不是快照時戳。

    ⛔⛔ 2026-09-15 付過代價。舊版只認 `年月／出表／年度／月別／Date`
    ⇒ 量 `t187ap04`（每日重大訊息）時只看到 `出表日期` 1 種
    ⇒ 我寫了「只給最新一期，沒有歷史」。**那是量錯了欄。**

        `出表日期`／`Date`  ＝ 我方抓取那一天的**快照時戳**
                            ⚠ 它**必定**只有 1 種 ⇒ 拿它問「有沒有歷史」，
                            ⛔ 答案永遠是「沒有」，而那不是量出來的
        `發言日期`          ＝ **內容日期** ⇒ 它的相異值才回答涵蓋期間

    ⚠ 這正是 CLAUDE.md 二那條：**「這個端點可不可信」問錯了問題，
      要問的是「這個【欄】…」**——同一張表裡，有的欄是時戳、有的欄是內容。

    ⭐ 三種形狀各驗一次（照真回應的形狀做，⛔ 不連外）：
    ①只有時戳 ⇒ **不可判定**｜②內容日期一天 ⇒ 沒有歷史｜③跨多天 ⇒ 含多期。
    ⛔ 少了③，舊版那個 bug 不會紅。
    """
    import json as _j
    import mops_probe as MP
    import backfill as _B
    bad = 0

    def _run(rows):
        saved = _B.get
        _B.get = lambda *a, **k: (_j.dumps(rows).encode("utf-8"), None)
        out = []
        try:
            MP.openapi_case("https://example.invalid/x", out)
        finally:
            _B.get = saved
        return "\n".join(out)

    cases = [
        ("① 只有快照時戳 ⇒ **不可判定**（⛔ 不是「沒有歷史」）",
         [{"出表日期": "1150915", "公司代號": "1101"},
          {"出表日期": "1150915", "公司代號": "2330"}],
         "不可判定", "只給最新一期，沒有歷史"),
        ("② 批次日只有一天 ⇒ 沒有歷史",
         [{"出表日期": "1150915", "發言日期": "1150915", "公司代號": "1101"},
          {"出表日期": "1150915", "發言日期": "1150915", "公司代號": "2330"}],
         "只給最新一期，沒有歷史", "不可判定"),
        ("③ ⭐ 批次日跨多天 ⇒ **含多期**（⛔ 只看快照時戳會誤判成沒有歷史）",
         [{"出表日期": "1150915", "發言日期": f"11509{d:02d}"} for d in range(1, 16)],
         "含多期", "只給最新一期"),
        # ⛔⛔ ④⑤ 是「修過頭到另一邊」那兩個（2026-09-15 同一天付的第二次代價）
        ("④ ⛔ **事件日**散在好幾期，而批次日只有一天 ⇒ 仍然是**沒有歷史**"
         "（⚠ 實測 `t187ap04_L` 的 `事實發生日` 最大值 **1151103 是未來** "
         "⇒ 它不可能是涵蓋期間的上界）",
         [{"出表日期": "1150915", "發言日期": "1150914", "事實發生日": d}
          for d in ("1150629", "1150914", "1151103")],
         "只給最新一期，沒有歷史", "含多期"),
        ("⑤ ⛔ `發言時間` 是**時分秒**、不是日期 ⇒ 它的 80 個相異值不算數",
         [{"出表日期": "1150915", "發言日期": "1150914", "發言時間": f"1{i:05d}"}
          for i in range(20)],
         "只給最新一期，沒有歷史", "含多期"),
        # ⛔⛔ ⑥ 是**為了讓那一道排除真的承重**才存在的（2026-09-15）。
        #   ⚠ 突變「拿掉時分秒的排除」原本**全綠**：`發言時間` 不含 `發言日`
        #     ⇒ 它本來就沒被 BATCH 收進去 ⇒ 那一道排除當時**不承重**。
        #   ⭐ 而它不是沒用——欄名叫 `資料日期時間` 的時候它才是唯一擋得住的
        #     （`資料日` 在 BATCH 裡會中）。⇒ 造一個那樣的欄出來驗它。
        ("⑥ ⭐ 欄名是 `資料日期時間`（**同時**命中批次日與時分秒）⇒ 排時分秒優先",
         [{"出表日期": "1150915", "資料日期時間": f"1150914{i:06d}"}
          for i in range(20)],
         "不可判定", "含多期"),
    ]
    for name, rows, want, unwant in cases:
        txt = _run(rows)
        ok = want in txt and unwant not in txt
        print(("✓ " if ok else "✗ ") + f"openapi_case {name}")
        if not ok:
            print(f"    ⛔ 要有「{want}」、不可有「{unwant}」；實得：{txt[-200:]}")
            bad += 1
    # ⭐ 而④要**講出事件日為什麼不算**（⛔ 只說結論，下一個人會再拿它代打一次）
    txt4 = _run([{"出表日期": "1150915", "發言日期": "1150914", "事實發生日": d}
                 for d in ("1150629", "1150914", "1151103")])
    ok4 = "事件日" in txt4 and "不是歷史" in txt4
    print(("✓ " if ok4 else "✗ ")
          + "openapi_case ④ 講得出**事件日為什麼不算**（⛔ 不是只給一個結論）")
    if not ok4:
        print(f"    實得：{txt4[-200:]}")
        bad += 1
    # ⭐ 而③還要講得出**最小與最大**（⛔「15 種」不等於「涵蓋 15 天」）
    txt3 = _run([{"出表日期": "1150915", "發言日期": f"11509{d:02d}"}
                 for d in range(1, 16)])
    ok = "最小 1150901" in txt3 and "最大 1150915" in txt3
    print(("✓ " if ok else "✗ ")
          + "openapi_case ③ 講得出**最小與最大**（⛔「幾種」≠「涵蓋幾天」）")
    if not ok:
        bad += 1
    return bad


def check_bridge_blank_vs_ignored():
    """⭐⭐ `bridge_case`「兩期相同」有**兩種**成因，⛔ 而下一步完全相反。

    ⛔⛔ 2026-09-15 付過代價：這一段本來**只比位元組、不說回來的是什麼**
    ⇒ 量 `t05st01` 時回「期別參數被忽略，這條路不可用」。
    ⚠ 而兩期都是 22,788 bytes 的小頁面 ⇒ ⭐ 它也可能是**查無資料頁**，
    而那代表**我沒問對**（`t05st01` 是逐檔查的，沒給公司代號本來就查無），
    ⛔ 不是「它沒有歷史」。

    ⚠ CLAUDE.md 二③ 記過同一個坑：hist.tpex 的 4,449 bytes 查無資料頁
    讓 **32 個年份全部命中**。

    ⇒ 三種形狀各一條（⛔ 少了①那一種，這個 bug 不會紅）。
    """
    import mops_probe as MP
    bad = 0

    def _run(a, b):
        out, seq, saved = [], [a, b], MP.one
        MP.one = lambda api, year, out_, **kw: seq.pop(0)
        try:
            MP.bridge_case("X", "114", "110", out)
        finally:
            MP.one = saved
        return "\n".join(out)

    blank = "<html><body>查無資料</body></html>".encode("utf-8")
    full = ("<html><body>" + "<tr><td>重大訊息公告本公司民國</td></tr>" * 30
            + "</body></html>").encode("utf-8")
    cases = [
        ("① ⭐ 兩期相同、**而且都是查無資料頁** ⇒ **不可判定**"
         "（⛔ 不是「這條路不可用」）", blank, blank, "不可判定", "這條路不可用"),
        ("② 兩期相同、而且**有資料** ⇒ 期別參數被忽略 ⇒ 這條路不可用",
         full, full, "這條路不可用", "不可判定"),
        ("③ 兩期不同 ⇒ 期別參數真的生效", full, blank, "真的生效", "不可判定"),
    ]
    for name, a, b, want, unwant in cases:
        txt = _run(a, b)
        ok = want in txt and unwant not in txt
        print(("✓ " if ok else "✗ ") + f"bridge_case {name}")
        if not ok:
            print(f"    ⛔ 要有「{want}」、不可有「{unwant}」；實得：{txt[-220:]}")
            bad += 1
    # ⭐ 而**不論哪一種**都要把「回來的是什麼」講出來（⛔ 只給結論等於沒給證據）
    txt = _run(full, full)
    ok = "<tr> 30 個" in txt and "中文" in txt
    print(("✓ " if ok else "✗ ")
          + "bridge_case 逐期講出**回來的是什麼**（中文字數／<tr> 數／查無字樣）")
    if not ok:
        bad += 1
    # ⛔⛔ 而那三個**數字**仍然分不出第四種形狀：「它回的是**查詢表單**，不是結果」。
    #   ⚠ 表單頁一樣沒有「查無」字樣、一樣有幾個 `<tr>`、一樣每一期都相同。
    #   ⭐ 我為了這一格改過兩次判準，每次都又冒出一種形狀
    #   ⇒ **不要再猜形狀了，把字印出來讓人讀**（CLAUDE.md 第一點）。
    form = ("<html><body><table><tr><td>年度</td><td><select>x</select></td></tr>"
            "<tr><td>請選擇公司代號</td></tr></table></body></html>").encode("utf-8")
    txt = _run(form, form)
    ok = "請選擇公司代號" in txt and "前 160 字" in txt
    print(("✓ " if ok else "✗ ")
          + "bridge_case ⭐ 把**回應的字**印出來"
            "（⇒ 查詢表單那一種只有讀字才分得出來）")
    if not ok:
        print(f"    實得：{txt[-220:]}")
        bad += 1
    # ⛔⛔ ④ 而**真正**回來的是第四種：**js 空殼**（實測 `t05st01`：
    #   22,788 bytes、中文 516 字、`<tr>` 14 個，前 160 字是
    #   `公開資訊觀測站 … window.onload=getMsg;` ⇒ 框架加 JavaScript，一列資料都沒有）。
    #   ⚠ 它**同時**滿足「兩期相同」與「沒有查無字樣」⇒ 舊判準判成「這條路不可用」，
    #   ⛔ 而正確的是「**我方取不到**」——兩句話的下一步完全相反。
    #   ⭐ 而這個判準 `suspend_probe` **早就有**（四點五：收成一份 `backfill.js_shell`）。
    shell = ("<html><head>" + '<script src="a.js"></script>' * 4
             + "</head><body>公開資訊觀測站 全站搜尋 營收 除權息"
               "<table><tr><td>x</td></tr></table></body></html>").encode("utf-8")
    txt = _run(shell, shell)
    ok = "js 空殼" in txt and "我方取不到" in txt and "這條路不可用" not in txt
    print(("✓ " if ok else "✗ ")
          + "bridge_case ④ ⭐ 兩期都是 **js 空殼** ⇒ 「我方取不到」"
            "（⛔ 不是「這條路不可用」，⛔ 也不是「官方沒有」）")
    if not ok:
        print(f"    實得：{txt[-260:]}")
        bad += 1
    # ⭐ 而那一份判準自己也要驗（⛔ 不是只驗呼叫點）
    import backfill as _B
    data = ("<html><body><table>" + "<tr><td>重大訊息</td></tr>" * 40
            + "</table></body></html>").encode("utf-8")
    ok = _B.js_shell(shell)[3] is True and _B.js_shell(data)[3] is False
    print(("✓ " if ok else "✗ ")
          + "backfill.js_shell 本身：空殼 True／資料頁 False")
    if not ok:
        print(f"    空殼 {_B.js_shell(shell)}｜資料 {_B.js_shell(data)}")
        bad += 1
    # ⛔⛔ 而上面那兩個假回應**分不出** `and` 與 `or`（兩個條件同進同出）
    #   ⇒ 「改成任一個就算」的突變**全綠**（2026-09-15 實測）。
    #   ⭐ 而真正會踩到的就是那一種：**真的資料頁也會掛 js**
    #     ⇒ 用 `or` 的話，一份有 40 列資料的頁面會被判成空殼
    #     ⇒ ⛔ 那會把一條**通的**路記成「我方取不到」。
    data_js = ("<html><head>" + '<script src="a.js"></script>' * 5
               + "</head><body><table>" + "<tr><td>重大訊息</td></tr>" * 40
               + "</table></body></html>").encode("utf-8")
    ok = _B.js_shell(data_js)[3] is False
    print(("✓ " if ok else "✗ ")
          + "backfill.js_shell ⭐ **有 40 列資料、而且掛了 5 支 js** ⇒ 仍然**不是**空殼"
            "（⛔ 判準是表格少**且** js 多，不是任一個）")
    if not ok:
        print(f"    實得 {_B.js_shell(data_js)}")
        bad += 1
    return bad


def check_xhr_hunt():
    """⭐ `xhr_hunt`：把那一頁的 js **去打誰**挖出來（⛔ 不是猜端點名）。

    ⚠ 「js 空殼 ⇒ 我方取不到」是**還沒解決的工程問題**，⛔ 不是句點
    ⇒ 下一步是從回應裡讀出那個 js 要打的網址。
    ⭐ 而我方到 2026-09-15 為止**只用過一個** MOPS api 路徑（`redirectToOld`）
      ——全 repo grep 過只有它，⛔ 而那個名字本身就說明還有別的。
    """
    import mops_probe as MP
    bad = 0
    # ⛔⛔ 假回應裡**每個模式要有自己專屬的值**（2026-09-15 付過代價）：
    #   第一版四個線索都寫成 `/mops/api/…` ⇒ 它同時被 ①③④ 撈到
    #   ⇒ 把 ③（`$.ajax` 那一條）整個拿掉的突變 **全綠**。
    #   ⭐ 這是第七點那條的同一個形狀：**斷言要比帶標籤的那一串，
    #     ⛔ 不是比一個裸字串**——而這裡是「假回應讓四條斷言分不開」。
    page = ("""<html><head><script src="/mops/js/a.js"></script>
<script src="/mops/js/b.js"></script><script src="/mops/js/c.js"></script></head>
<body>公開資訊觀測站
<script>window.onload=getMsg;
function getMsg(){ $.ajax({url:"https://mopsov.twse.com.tw/server-java/OnlyInAjax",
  type:"POST", data:{companyId:"2330"}, success:function(d){render(d);} }); }
fetch("/mops/onlyinfetch/list");
var z = "/nas/t05/onlyinfour.json";
</script><table><tr><td>x</td></tr></table></body></html>""").encode("utf-8")
    out, saved = [], MP.one
    MP.one = lambda api, year, out_, **kw: page
    try:
        MP.xhr_hunt("t05st01", out)
    finally:
        MP.one = saved
    txt = "\n".join(out)
    # ⛔⛔ 而斷言要**照標籤分節**比（2026-09-15 第二次付代價）：
    #   我把假回應改成「每個模式有專屬值」之後，突變「拿掉 ③ 那一條」**還是全綠**
    #   ——因為那個字串也出現在 `getMsg` **本體的傾印**裡。
    #   ⭐ 這正是第七點那條的完整版：**比帶標籤的整串**
    #     ⇒ 這裡的「標籤」是**那一節**，所以要先切節再比。
    def _sect(marker):
        """→ 那一節（從標籤那一行到下一個 `  ` 開頭的標籤）的文字。"""
        lines = out
        for i, ln in enumerate(lines):
            if marker in ln:
                body = []
                for nxt in lines[i + 1:]:
                    if nxt.startswith("  ") and not nxt.startswith("      "):
                        break
                    body.append(nxt)
                return "\n".join(body)
        return ""

    for name, marker, want in (
            ("① 挖得出 `$.ajax` 裡那個 url（⭐ 比的是**那一節**）",
             "`$.ajax` / `url:`", "OnlyInAjax"),
            ("② 也挖得出 `fetch(` 那一個", "`fetch(` 的對象", "onlyinfetch"),
            ("③ 也挖得出 `.json` 那一種", "其他 `.ashx`", "onlyinfour.json"),
            ("④ ⭐ 把 `getMsg` 的**本體**印出來（⇒ 參數名也看得到）",
             "`getMsg` 本體", "companyId"),
            ("⑤ 而形狀那一行照樣要講（js 空殼）", "[形狀]", "js 空殼")):
        seg = _sect(marker)
        ok = bool(seg is not None) and (want in seg
                                        or (marker in txt and want in
                                            txt.split(marker, 1)[1][:400]))
        print(("✓ " if ok else "✗ ") + f"xhr_hunt {name}")
        if not ok:
            print(f"    ⛔ 「{marker}」那一節裡找不到「{want}」；實得：{seg[:200]!r}")
            bad += 1
    # ⛔ 取不回來時要**說它沒跑**（⚠ 不可以印一堆 0 種，那跟「站上沒有」長得一樣）
    out, saved = [], MP.one
    MP.one = lambda api, year, out_, **kw: None
    try:
        MP.xhr_hunt("t05st01", out)
    finally:
        MP.one = saved
    txt = "\n".join(out)
    ok = "沒跑" in txt and "0 種" not in txt
    print(("✓ " if ok else "✗ ")
          + "xhr_hunt ⛔ 取不回來 ⇒ 說「這一段**沒跑**」"
            "（⚠ 不是印一堆 `0 種`——那跟「站上沒有」長得一樣）")
    if not ok:
        print(f"    實得：{txt}")
        bad += 1
    return bad


def check_js_followups():
    """⭐ ①~④ 全 0 的時候，答案在**外部 `.js`** 裡——這一層有沒有做。

    ## ⛔ 為什麼一定要有這一層

    2026-09-15 三頁**同時**是 js 空殼、而且 inline 線索幾乎全 0：

    ```
    MOPS  t05st01（重大訊息）                     ①②③④ 全 0
    TPEx  announce/market/change.html             ②③④ 全 0（① 只有字型站）
    TPEx  announce/market/change/reference.html   ②③④ 全 0（① 只有字型站）
    ```

    ⇒ ⭐ 「inline 全 0」**不是**「站上沒有」，⛔ 而兩者在報告上長得一模一樣。
    """
    import backfill as B
    bad = 0

    def ck(name, cond, extra=""):
        nonlocal bad
        print(("✓ " if cond else "✗ ") + name)
        if not cond:
            bad += 1
            if extra:
                print(f"    {extra}")

    page = ('<html><head>'
            '<script src="/js/mine.js"></script>'
            '<script src="https://fonts.googleapis.com/x.js"></script>'
            '<script src="//cdn.jsdelivr.net/y.js"></script>'
            '<script src="data:text/javascript,1"></script>'
            '<script src="/js/mine.js"></script>'      # ⚠ 重複一支，要去重
            '<script>var a=1;</script></head><body></body></html>')
    base = "https://mopsov.twse.com.tw/mops/web/t05st01"

    # ── ① script_srcs 本身
    got = B.script_srcs(page, base=base)
    ck("① `script_srcs` 相對路徑照 base 拼成絕對",
       "https://mopsov.twse.com.tw/js/mine.js" in got, f"實得 {got}")
    ck("② `//` 開頭補成 https", "https://cdn.jsdelivr.net/y.js" in got, f"實得 {got}")
    ck("③ `data:` 不算（⛔ 它不是一個可以去打的網址）",
       not any(u.startswith("data:") for u in got), f"實得 {got}")
    ck("④ 同一支出現兩次只算一支（去重）",
       len([u for u in got if u.endswith("/js/mine.js")]) == 1, f"實得 {got}")
    # ⛔ 沒有 base 就**不猜**：相對路徑會拼到錯的站
    nob = B.script_srcs(page, base=None)
    ck("⑤ ⛔ 沒給 base ⇒ 相對路徑**不猜**（⚠ 猜會拼到錯的站）",
       not any("mine.js" in u for u in nob), f"實得 {nob}")

    # ── ⑥ xhr_clues 的第 ⑤ 節「就算是 0 也一定要印」
    #    ⛔⛔ 這一條是第七點那句：**「沒有這一節」跟「這一節是 0」長得一模一樣**
    lines = B.xhr_clues("<html><body>什麼都沒有</body></html>", base=base)
    ck("⑥ ⭐ 外部 `.js` 那一節**就算 0 支也要印**"
       "（⛔ 沒有那一節跟那一節是 0，在紙上一模一樣）",
       any("外部載入的 `.js`：0 支" in ln for ln in lines), f"實得 {lines}")

    # ── ⑦⑧⑨ js_followups：第三方要**列出來再跳過**、抓不到要說「沒挖」
    calls = []
    saved = B.get

    def fake_get(url, **kw):
        calls.append(url)
        if "mine.js" in url:
            return (b'function q(){ $.ajax({url:"/mops/api/OnlyInExternalJs"}); }', None)
        return (None, "URLError: boom")

    B.get = fake_get
    try:
        got = "\n".join(B.js_followups(page, base=base))
    finally:
        B.get = saved
    ck("⑦ ⭐ 外部 `.js` 裡那個端點**真的挖出來了**（⇒ 這一層有用）",
       "OnlyInExternalJs" in got, f"實得 {got[:400]}")
    ck("⑧ 第三方（字型／CDN）**逐條列出來再跳過**"
       "（⛔ 靜靜篩掉的話，讀的人看不出「⑤ 有 3 支我只抓 1 支」）",
       "跳過（第三方）" in got and "fonts.googleapis" in got and "jsdelivr" in got,
       f"實得 {got[:400]}")
    ck("⑨ ⛔ 第三方**沒有被真的打**（⚠ 跟這件事無關，不該發請求）",
       not any(("googleapis" in u or "jsdelivr" in u) for u in calls),
       f"實際打了 {calls}")

    # ⑦b ⭐⭐ 通用函式庫要**排到最後**（2026-09-15 付過代價）
    #   `mine` 本來照字母排序 ＋ cap ⇒ 額度被 `gsap`／`jquery-*` 吃光
    #   ⇒ ⛔ 站方**自己寫的** `main.js`／`tables.js` 一支都沒挖到，
    #   ⚠ 而報告上只寫「本站另 4 支未挖」——⭐ 那 4 支正是最可能有答案的。
    vend = ('<html>'
            '<script src="/rsrc/asset/js/jquery-3.7.1.min.js"></script>'
            '<script src="/rsrc/asset/js/gsap.min.js"></script>'
            '<script src="/rsrc/asset/js/jquery.cookie.min.js"></script>'
            '<script src="/rsrc/js/tables.js"></script>'
            '<script src="/rsrc/js/main.js"></script>'
            '</html>')
    order = []
    B.get = lambda u, **k: (order.append(u) or (b"x", None))
    try:
        txt7 = "\n".join(B.js_followups(vend, base="https://x.invalid/a.html",
                                        cap=2))
    finally:
        B.get = saved
    ck("⑦b ⭐⭐ 站方自己寫的先挖，通用函式庫**排到最後**"
       "（⛔ 照字母排 ＋ cap ⇒ `main.js`／`tables.js` 永遠挖不到）",
       len(order) == 2 and all("jquery" not in u and "gsap" not in u
                               for u in order), str(order))
    ck("  而且**講出**有幾支是通用函式庫（⛔ 不是靜靜重排）",
       "通用函式庫 3 支" in txt7, txt7[:200])

    # ⑦c ⭐⭐ `around()`：端點名挖到了，**參數還是不知道** ⇒ 原始碼原樣印
    js = ('function getMsg(value) { //var url = "/mops/web/ezsearch_query"; '
          'var keyValue = "pg=ezsearch"; if (lang == "TW") '
          '{ url = "/server-java/AjaxCheck"; } }')
    a = "\n".join(B.around(js, "ezsearch_query", span=200))
    ck("⑦c ⭐ 把端點前後的碼**原樣**印出來（⇒ 參數名讀得到，⛔ 不用猜）",
       "ezsearch_query" in a and "getMsg" in a, a[:200])
    miss = "\n".join(B.around(js, "沒有這個字"))
    ck("  ⛔ 找不到要說「找不到」，⚠ 不是印一片空白"
       "（那跟「沒有這一段」長得一樣）",
       "找不到" in miss and "不是「它不存在」" in miss, miss)
    many = "\n".join(B.around("xAx" * 10, "A", span=6, cap=2))
    ck("  而超過 cap 要講**還有幾處沒印**（⛔ 不是靜靜截斷）",
       "另 8 處未印" in many, many)

    # ⑩ 本站一支都沒有 ⇒ 要說「挖不下去」，⛔ 不可以讀成「官方沒有」
    B.get = fake_get
    try:
        none = "\n".join(B.js_followups("<html><body>x</body></html>", base=base))
    finally:
        B.get = saved
    ck("⑩ 本站一支都沒有 ⇒ 說**挖不下去**，⛔ 並明講「這不是官方沒有」",
       "挖不下去" in none and "不是「官方沒有」" in none, f"實得 {none}")

    # ⑪ 某一支取不回來 ⇒ 要說「這一支沒挖」（⛔ 不是「裡面沒有」）
    B.get = lambda url, **kw: (None, "URLError: boom")
    try:
        fail = "\n".join(B.js_followups(page, base=base))
    finally:
        B.get = saved
    ck("⑪ 某一支取不回來 ⇒ 說「這一支**沒挖**」（⛔ 不是「裡面沒有」）",
       "沒挖" in fail and "不是「裡面沒有」" in fail, f"實得 {fail[:300]}")

    # ── ⑫⑬ ⭐ 測完純函式，再掃一次**呼叫點**（第七點第三個陷阱）
    #    ⚠ `base` 傳 None 的話 ⑤ 永遠是 0 支 ⇒ 上面十一條全綠、而現場挖不到東西。
    import re as _re
    for mod, fnname in (("mops_probe.py", "xhr_hunt"),
                        ("parvalue_probe.py", "main")):
        src = io.open(mod, encoding="utf-8").read()
        body = src.split(f"def {fnname}(", 1)[1]
        hit = _re.search(r"js_followups\(\s*\w+\s*,\s*base\s*=\s*(\w+)", body)
        ok = bool(hit) and hit.group(1) != "None"
        ck(f"⑫ 呼叫點 `{mod}:{fnname}` 真的把 base 傳進去"
           "（⛔ base=None ⇒ 這一層永遠 0 支，而十一條斷言照樣全綠）",
           ok, f"實得 {hit.group(0) if hit else '找不到呼叫'}")

    # ⑬ ⭐⭐ 凡是**判得出 js 空殼**的探針，都要接上 `js_followups`
    #    ⛔ 否則下一支判到空殼的，又會停在「我方取不到」那一句
    #    ——⚠ 而「取不到」是**還沒解決的工程問題**，不是句點。
    #    ⭐ 這一道是「躲得過那道守門的族，要自己帶一道」：`selftest_no_dup`
    #      比的是函式本體，⛔ 它看不出「有人用了 A 卻沒用 B」。
    shell_users, no_dig = [], []
    for _f in sorted(glob.glob(os.path.join(_here_dir(), "*.py"))):
        b = os.path.basename(_f)
        if b.startswith("selftest_") or b == "backfill.py":
            continue
        t = io.open(_f, encoding="utf-8").read()
        if "js_shell(" not in t:
            continue
        shell_users.append(b)
        if "js_followups(" not in t:
            no_dig.append(b)
    ck("⑬ ⭐⭐ 判得出 js 空殼的探針**都**接上了 `js_followups`"
       "（⛔ 少一支，那一支就會停在「我方取不到」那一句）",
       not no_dig, f"⛔ 沒接的：{no_dig}")
    ck(f"  ★ 而這一道真的掃到了（⛔ 0 支跟全部通過長得一樣）｜{len(shell_users)} 支",
       len(shell_users) >= 4, f"只掃到 {shell_users}")

    # ⑭ `visible_text` 只有一份實作（四點五）：⛔ 不可以有人自己 re.sub 去標籤
    # ⚠ 只掃 `.py`：⛔ `grep -rn .` 會去掃 `data/`（1.6 GiB）⇒ 這一條要跑好幾分鐘，
    #   而一條慢到讓人想拿掉的斷言，跟沒有那條斷言是一樣的。
    # ⛔⛔ 這一道本來比**原始碼字串** ⇒ 2026-09-16 當場誤報：
    #   `selftest_workflows.covering_tests` 的 **docstring 裡引用了那段 pattern**
    #   （它在講「⑭ 抓得到」這件事）⇒ 被判成第二份實作。
    #   ⭐ 正是第七點第八個那條，而且這次中的是這道守門自己：
    #     **我們的註解本來就會引用那段程式碼。**
    #   ⇒ 改比 **AST 的呼叫**：`re.sub(<字面 pattern>, …)`，
    #     ⛔ 註解與 docstring 一律看不到。
    hits = []
    for _f in sorted(glob.glob(os.path.join(_here_dir(), "*.py"))):
        if os.path.basename(_f) == "backfill.py":
            continue      # ⭐ 那一份就是**唯一**那一份
        try:
            _tree = ast.parse(io.open(_f, encoding="utf-8").read())
        except SyntaxError:
            continue
        for _n in ast.walk(_tree):
            if (isinstance(_n, ast.Call) and isinstance(_n.func, ast.Attribute)
                    and _n.func.attr == "sub" and _n.args
                    and isinstance(_n.args[0], ast.Constant)
                    and isinstance(_n.args[0].value, str)
                    and re.match(r"^<\[\^>\]\+>$", _n.args[0].value)):
                hits.append(os.path.basename(_f))
                break
    ck("⑭ 去標籤只有 `backfill.visible_text` 一份實作（四點五）",
       not hits, "⛔ 另有一份：" + "；".join(hits[:3]))

    # ── ⑮⑯ ⭐⭐ `sep` 必填而且**沒有預設值**
    #    ⚠ 這一族有兩種相反的語意（`" "` 整頁可讀文字／`""` 取一格的值），
    #    ⛔ 而預設值就是「照抄語意」那個坑的自動化版本：不寫也會跑，
    #      默默套上多數派那一種，而畫面上看不出來。
    #    ⭐ 釘的是 `inspect.signature` 裡**沒有 default**，
    #      ⛔ 不是釘「忘了傳會 TypeError」——後者在有人加上預設值之後照樣全綠。
    sig = inspect.signature(B.visible_text)
    ck("⑮ ⭐⭐ `visible_text(sep)` **沒有預設值**"
       "（⛔ 有預設值＝自動套上多數派的語意，而畫面上看不出來）",
       "sep" in sig.parameters
       and sig.parameters["sep"].default is inspect.Parameter.empty,
       f"實得 {sig}")
    # ⭐ 而「兩種語意都還在」也要盯：只剩一種就代表有人把語意抄平了
    #   （跟 `selftest_lowwater` ⑨ 同一條）。
    seps = set()
    for _f in sorted(glob.glob(os.path.join(_here_dir(), "*.py"))):
        if os.path.basename(_f).startswith("selftest_"):
            continue
        for m in re.finditer(r"visible_text\([^()]*,\s*(\"[^\"]*\")\s*\)",
                             io.open(_f, encoding="utf-8").read()):
            seps.add(m.group(1))
    # ⑰ ⛔ `<script>` 的內容**不是**人看得見的字
    #    ⚠ 實測代價：沒有這兩行的話，`t05st01` 的「前 160 字」印出來是
    #      `… window.onload=getMsg; var MAR = document.querySelector(…`
    #    ⇒ 而這一格存在的理由就是「讓人讀三行就分得出來」⇒ 印 js 等於沒印。
    vt = B.visible_text('<script>window.onload=getMsg;</script>'
                        '<style>.a{color:red}</style><p>公開資訊觀測站</p>', " ")
    ck("⑰ ⛔ `<script>`／`<style>` 的內容不算可見文字"
       "（⚠ 沒這兩行的話「前 160 字」印出來是一串 js）",
       vt == "公開資訊觀測站", f"實得 {vt!r}")

    ck("⑯ 兩種語意**都還在**（`\" \"` 與 `\"\"`）"
       "——⛔ 只剩一種就代表有人把語意抄平了",
       seps == {'" "', '""'}, f"實得 {sorted(seps)}")
    return bad


def check_scale_qualified():
    """⭐⭐ 「這個來源不可用」必須寫成「對 ___ 規模不可用」（三點③）。

    ⚠ 而規模要是**量出來的**：2026-09-13 我寫「1,954 檔 × 245 日」，
    ⛔ 實測母體是 **2,493**（含興櫃）、上市＋上櫃 **2,130**、2025 交易日 **243**。
    ⇒ 一個記得的數字比不寫更糟：它讀起來跟量過的一模一樣。
    """
    import broker_probe as BP
    bad = 0

    def ck(name, cond, extra=""):
        nonlocal bad
        print(("✓ " if cond else "✗ ") + name)
        if not cond:
            bad += 1
            if extra:
                print(f"    {extra}")

    txt = "\n".join(BP.scale_lines())
    ck("① 判死的是**那一格**，⛔ 不是整條路",
       "判死的不是" in txt and "全市場自動化" in txt, txt[:200])
    ck("② 三個障礙**逐項**對照兩種規模（⛔ 不是只講一句「規模有差」）",
       all(w in txt for w in ("驗證碼", "逐檔查", "只有當日", "人做得到")), txt[:200])
    ck("③ ⛔ 跟規模**無關**的那個理由要分開寫（條款禁重製）"
       "（⚠ 並排寫成「兩個都獨立成立」＝看起來到處都成立）",
       "跟規模無關" in txt and "重製" in txt, txt[:200])
    ck("④ ⭐ 規模是**量出來的**（母體與交易日都從 repo 讀）",
       "meta/stocks.csv" in txt and "universe/daily" in txt, txt[:200])
    # ⭐ 而數字要對得上現場，⛔ 不是寫死的
    import csv as _csv
    import os as _os
    n = 0
    pth = _os.path.join(BP._ROOT, "meta", "stocks.csv")
    if _os.path.exists(pth):
        with io.open(pth, encoding="utf-8") as f:
            n = sum(1 for r in _csv.DictReader(f)
                    if r.get("kind") == "stock"
                    and r.get("market") in ("twse", "tpex"))
        ck(f"⑤ 母體數字跟現場一致（實測上市＋上櫃 {n:,}）",
           f"**{n:,}**" in txt, txt[:300])
    else:
        # ⛔ 讀不到就**大聲說沒跑**（六點五：某個 ref 上必然不成立的斷言
        #   等於把那個環境的整條線關掉）
        print("  ⚠⚠ **這一層沒跑**：這個 ref 上沒有 `meta/stocks.csv`"
              "　⇒ ⛔ 不算失敗，⛔ 也不算驗過")
        ck("⑤' 而那種時候要**大聲說算不出來**，⛔ 不可以印一個記得的數字",
           "這一段沒跑" in "\n".join(BP.scale_lines()), txt[:200])
    return bad


def check_f2_numbers():
    """⭐⭐ F2：「口徑差落在哪一欄」——⛔ 沒有數字，這個問題答不了。

    ⚠ 第一版那一節只印 `describe_response`（被丟掉的頂層鍵）⇒ 看得到 `stat: OK`、
    看得到 `title`，⛔ 而**一個總量數字都沒有** ⇒ 那一節回答不了它自己問的問題。
    ⚠ 而且上半段寫死 2026-09-01、下半段打 `DAY` ⇒ **兩個不同的日子並排**，
    ⛔ 讀的人會以為是同一天（錨點要落在同一格）。
    """
    import keys_probe as KP
    bad = 0

    def ck(name, cond, extra=""):
        nonlocal bad
        print(("✓ " if cond else "✗ ") + name)
        if not cond:
            bad += 1
            if extra:
                print(f"    {extra}")

    f = ["日期", "成交股數", "成交金額", "成交筆數", "發行量加權股價指數"]
    rows = [["115/09/09", "1,000", "2,000", "30", "46,948.72"],
            ["115/09/10", "5", "7", "1", "1"]]
    got = KP._sum_by_name(f, rows)
    ck("① 逐欄合計照**欄名**取（⛔ 不是位置——今天在 [1] 不保證 2015 也在 [1]）",
       got == {"成交股數": 1005.0, "成交金額": 2007.0, "成交筆數": 31.0}, str(got))
    ck("② 千分位逗號要吃掉（⛔ 否則 float() 全部失敗、合計靜靜變 0）",
       got.get("成交金額") == 2007.0, str(got))
    ck("③ ⛔ 沒有那幾個欄名 ⇒ 回空 dict（⚠ 不是回 0：0 跟「那天沒成交」一樣）",
       KP._sum_by_name(["a", "b"], rows) == {}, str(KP._sum_by_name(["a", "b"], rows)))
    ck("④ ⛔ 指數那一欄**不加總**（⚠ 它不是總量，加起來沒有意義）",
       "發行量加權股價指數" not in got, str(got))
    ck("⑤ 那一天不在這個 ref 上 ⇒ 回 **None**"
       "（⇒ 呼叫端才說得出「這一格沒量到」，⛔ 回 0 就變成「那天沒成交」）",
       KP._our_twse_total("1999-01-01") is None)
    # ⭐ 而三條路要落在**同一天**——⛔ 兩個日子並排就是錨點錯了
    import inspect
    src = inspect.getsource(KP.f2_kou_jing)
    ck("⑥ ⭐ 三條路用**同一個** `day` 換算出來的 iso"
       "（⛔ 上半段寫死一天、下半段打另一天 ＝ 錨點錯了）",
       'iso = f"{day[:4]}-{day[4:6]}-{day[6:]}"' in src
       and "_our_twse_total(iso)" in src, "⛔ 沒有從 day 換算")

    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ `_row_for_day`：⛔ 沒有它的時候，那一節把 FMTQIK 的**整月合計**
    #   跟我方的**單日**並排印 ⇒ ⚠ 兩個數字長得一樣可比，而它們不是同一個量。
    #   （2026-09-15 實測：FMTQIK 一發回 11 列 ＝ 九月整月。）
    #   ⇒ ⭐ 第三點 5 那條套在錨點上：**只准動一個變數**——
    #     一個月對一天，差異可以被歸給任何一件事。
    # ══════════════════════════════════════════════════════════════
    fl = ["日期", "成交股數", "成交金額", "成交筆數", "發行量加權股價指數"]
    many = [["115/09/08", "1", "2", "3", "1"],
            ["115/09/09", "6,558,338,220", "812,844,043,053", "4,056,475", "1"],
            ["115/09/10", "9", "9", "9", "1"]]
    one = KP._row_for_day(fl, many, "20260909")
    ck("⑦ ⭐⭐ 整月的表裡挑得出**那一天那一列**"
       "（⛔ 沒有這一條就會拿整月合計去跟單日比）",
       one == {"成交股數": 6558338220.0, "成交金額": 812844043053.0,
               "成交筆數": 4056475.0}, str(one))
    ck("⑧ ⭐ 而它跟逐欄合計**不一樣**（⚠ 一樣的話這一條等於沒驗）",
       one != KP._sum_by_name(fl, many),
       f"{one}　vs　{KP._sum_by_name(fl, many)}")
    ck("⑨ 民國與西元兩種日期格式都認得"
       "（⛔ 只認一種 ⇒ 換一個端點就靜靜挑不到）",
       KP._row_for_day(fl, [["2026/09/09", "7", "8", "9", "1"]],
                       "20260909").get("成交股數") == 7.0)
    ck("⑩ ⛔ 那一天不在表裡 ⇒ 回 **{}**（⚠ 不是回第一列、也不是回合計）",
       KP._row_for_day(fl, many, "20260911") == {}, )
    ck("⑪ ⛔ 沒有「日期」欄 ⇒ 回 {}（⚠ 不可以拿第 0 欄當日期硬猜）",
       KP._row_for_day(["證券代號", "成交股數"],
                       [["2330", "5"]], "20260909") == {})
    return bad


def check_js_needles():
    """⭐ `js_followups(..., needles=)`：把某個**常數名**前後的原文印出來。

    ⛔ 加它的理由是 C4 那一格（2026-09-15 第二輪）：
    `page_wiring` 把 inline 挖出來之後，那兩頁逐字寫著

        tables.init({pattern: API_PATTERN, action: "bulletin/pvChgAnn"})

    ⇒ ⭐ **`action` 讀到了**，⛔ 而 `API_PATTERN` 的**值**在別支 js 裡。
    ⚠ 而 `xhr_clues` 只認**寫死的路徑字串** ⇒ 一個常數名它看不到
    ——⛔ 「它沒找到」與「那一支裡沒有」在報告上長得一模一樣。
    """
    import backfill as BB
    bad = 0

    def ck(name, cond, extra=""):
        nonlocal bad
        print(("✓ " if cond else "✗ ") + name)
        if not cond:
            bad += 1
            if extra:
                print(f"    {extra}")

    # ⚠ 這個假 js 要**照真的形狀**做（第七點）：常數的值是**拼出來的**，
    #   ⛔ 不是一個寫死的完整網址——寫死的話 `xhr_clues` 自己就看得到，
    #   ⇒ 那樣 ①「不傳 needles 就挖不到」會是**假的**（我第一版就這樣，當場紅）。
    js = (b'var BASE="/www/"+LANG; const API_PATTERN=BASE+"/api/"+act;'
          b' function go(){tables.init({pattern:API_PATTERN});}')
    seen = {}

    def fake_get(u, **kw):
        seen[u] = seen.get(u, 0) + 1
        return (js, None) if u.endswith(".js") else (b"", "nope")

    old_get = BB.get
    try:
        BB.get = fake_get
        html = '<html><script src="/a.js"></script></html>'
        no_nd = "\n".join(BB.js_followups(html, base="https://h/p.html"))
        with_nd = "\n".join(BB.js_followups(html, base="https://h/p.html",
                                            needles=("API_PATTERN",)))
    finally:
        BB.get = old_get

    ck("① ⛔ 不傳 needles ⇒ 那個常數**怎麼拼的**看不到"
       "（⚠ 這正是 `xhr_clues` 挖不到的那一種：值是拼出來的）",
       "API_PATTERN=BASE" not in no_nd, no_nd[-300:])
    ck("② ⭐ 傳了 needles ⇒ 那一段原文**逐字印出來**",
       "API_PATTERN=BASE" in with_nd, with_nd[-400:])
    ck("③ ⭐ 而兩者真的不同（⛔ 一樣的話上面兩條有一條是假的）",
       no_nd != with_nd)
    with_miss = None
    try:
        BB.get = fake_get
        with_miss = "\n".join(BB.js_followups(html, base="https://h/p.html",
                                              needles=("NOT_THERE_XYZ",)))
    finally:
        BB.get = old_get
    ck("④ ⛔ 找不到那個字時要**明講找不到**（⚠ 空白跟「沒挖」長得一樣）",
       "找不到" in with_miss, with_miss[-300:])
    ck("⑤ ⭐ 而 needles 是**選用**的：呼叫端沒傳時行為不變"
       "（⛔ 有預設值的參數要有一條不傳它的斷言，第七點③）",
       "⑤" in no_nd or "外部載入" in no_nd or len(no_nd) > 0, no_nd[:120])
    return bad


def check_page_wiring():
    """⭐⭐ `page_wiring`：頁面**自己**把參數放在哪裡（inline script ＋ data-*）。

    ⛔ 它存在的理由是一個**錯過的結論**：`otccal_probe` 2026-09-09 第四輪寫著

    > `tables.js` 那 142 處 `calendar` 全是 moment.js 的語系表
    > ⇒ **關鍵字次數多 ≠ 有端點**。11 支 js 裡一條寫死的路徑都沒有。
    > ⇒ 網址只剩兩個地方可能：頁面自己的 inline `<script>`，或 `data-*` 屬性。

    ⚠ 而 `parvalue_probe`（清單 C4）**從來沒挖過那兩個地方**
    ⇒ 它的「沒有端點」是在**沒掃過的範圍**上說的（三點①）。
    """
    import backfill as BB
    bad = 0

    def ck(name, cond, extra=""):
        nonlocal bad
        print(("✓ " if cond else "✗ ") + name)
        if not cond:
            bad += 1
            if extra:
                print(f"    {extra}")

    # ⚠ 這裡的 `src` script **故意帶內容**：空的 `<script src>` 被「內容是空字串」
    #   那一關濾掉了 ⇒ 突變（把 `(?![^>]*\bsrc=)` 拿掉）**什麼都不會變**，
    #   ⛔ 而那看起來跟「這條斷言沒用」一模一樣（第七點第四個陷阱）。
    #   ⭐ 帶了內容，那個突變才真的會多算一段。
    html = ('<html><head><script src="/rsrc/js/tables.js">/*fallback*/z=1;</script>'
            '</head>'
            '<body><script>\n var u = "/api/codeQuery";\n  go(u);\n</script>'
            '<div data-kind="parvalue" data-year="115" data-kind="dup"></div>'
            '<script src="https://x/y.js"></script></body></html>')
    out = "\n".join(BB.page_wiring(html))
    ck("① 帶 src 的 <script> **不算** inline（⛔ 算進去會把外部 js 當成頁面自己的）",
       "**1 段**" in out, out[:200])
    ck("② inline 的內容逐字印出來（⇒ 人讀得到它怎麼拼網址）",
       "/api/codeQuery" in out, out[:300])
    ck("③ `data-*` 抓得到，而且**去重**", "data-kind" in out and "data-year" in out
       and out.count("data-kind = ") == 2, out[:400])
    # ⭐ 反向：完全沒有的時候要**講出來**，⛔ 不是印一片空白
    out0 = "\n".join(BB.page_wiring("<html><body>hi</body></html>"))
    ck("④ ⛔ 一段都沒有時要**明講**（⚠ 空白跟「沒挖」長得一樣）",
       "⛔ 一段都沒有" in out0 and "⛔ 一個都沒有" in out0, out0)
    ck("⑤ 而且仍然印出**0** 這個數字（⇒ 讀得出它掃過了）",
       "**0 段**" in out0 and "**0 種**" in out0, out0)
    # ⭐ 超過 cap 要說「另 N 段未印」，⛔ 不是靜靜截掉
    many = "".join(f"<script>x{i}=1;</script>" for i in range(9))
    outm = "\n".join(BB.page_wiring(many, inline_cap=2))
    ck("⑥ 超過 cap ⇒ 講「另 N 段未印」（⛔ 靜靜截掉就是我今天連錯兩次的那個坑）",
       "另 7 段未印" in outm, outm[-200:])
    long1 = "<script>" + ("a" * 3000) + "</script>"
    outl = "\n".join(BB.page_wiring(long1, inline_chars=300))
    ck("⑦ 單段太長也要講「另 N 字未印」",
       "字未印" in outl, outl[-200:])

    # ⭐⭐ 呼叫點：兩支探針都要走**這一份**（四點五）
    import ast as _a
    _here = _here_dir()
    n_call, n_own = 0, []
    for fn in ("parvalue_probe.py", "otccal_probe.py"):
        src = io.open(os.path.join(_here, fn), encoding="utf-8").read()
        tree = _a.parse(src)
        if any(isinstance(n, _a.Call)
               and getattr(n.func, "attr", "") == "page_wiring"
               for n in _a.walk(tree)):
            n_call += 1
        # ⛔ 而且不可以自己再寫一份：掃有沒有自己在 findall `data-`
        if "data-[a-zA-Z0-9_" in src:
            n_own.append(fn)
    ck("⑧ ⭐ 兩支探針都走 `page_wiring`（⛔ 不是各寫一份）",
       n_call == 2, f"實得 {n_call} 支")
    ck("⑨ ⛔ 而且沒有人自己再 findall 一次 `data-*`（那就是第二份實作）",
       not n_own, str(n_own))
    return bad


def check_no_dup_keys():
    """⛔⛔ `SECTIONS` 這種 dict 字面量**有重複鍵也不會報錯**——Python 靜靜取後面那個。

    2026-09-15 實際發生：我要替 `parvalue_probe` 加一節，⚠ 而它**本來就有一格**
    （空的），我沒看到就在別處又寫了一個 ⇒ 兩個鍵並存。
    ⭐ 這一次剛好是我的那個在後面、**行為是對的**——⛔ 而那正是它危險的地方：
      **它現在是對的，而任何一次重排就會靜靜換成另一個。**

    ⇒ 掃 AST，⛔ 不是掃建好的 dict（建好之後重複鍵已經消失了，看不出來）。
    """
    import ast as _ast
    import collections as _c
    bad = 0
    _here = _here_dir()          # ⭐ 走唯一那一份（四點五）
    src = io.open(os.path.join(_here, "selftest_probes.py"), encoding="utf-8").read()
    tree = _ast.parse(src)
    dups = []
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Dict):
            continue
        keys = [k.value for k in node.keys
                if isinstance(k, _ast.Constant) and isinstance(k.value, str)]
        for k, n in _c.Counter(keys).items():
            if n > 1:
                dups.append((node.lineno, k, n))
    ok = not dups
    print(("✓ " if ok else "✗ ")
          + "selftest_probes 自己沒有**重複的 dict 鍵**"
            "（⛔ Python 靜靜取後面那個，而重排就會換人）")
    if not ok:
        print(f"    ⛔ {dups}")
        bad += 1
    return bad


def check_probe_stamp():
    """⭐⭐ **每一份探針輸出都要自己講出它是哪一趟跑的**（2026-09-15 加）。

    ⛔ 實測那天：17 支會寫 `data/meta/_*.txt` 的探針裡，**只有 1 支**寫時戳
    ⇒ 其餘 16 份，讀的人看不出它是哪一趟——⚠ 而四條線拿那些檔判斷
    「官方到底有沒有」。**一份三天前的 `_mops_probe.txt` 跟今天剛跑的長得一模一樣。**

    ⚠ 而同一天有個 bug 把它放大：`probe.yml` 的 job timeout 15 分、
    裡面有一步自己就是 15 分 ⇒ 四趟 run 被砍在 `Commit 回 repo` **之前**
    ⇒ main 上那幾份停在更早的一趟，⛔ 而沒有任何地方會說。

    ⭐ 這是 CLAUDE.md 第二點那句話套在**我方自己的輸出**上：
    「這一批要自己講出它是哪一天」——⛔ 我們對官方的回應要求這件事，
    ⚠ 而我們寫給別人讀的檔沒有做到。

    ⇒ 判準：凡是宣告 `OUT = …/meta/_*.txt` 的程式，都要叫 `backfill.probe_stamp()`。
    ⛔ 「記得加」不是守門——這一道**掃全 repo**（跟 `lowwater` ⑨ 同一個做法）。
    """
    import glob as _g
    import re as _re
    bad = 0
    here = os.path.dirname(os.path.abspath(__file__))
    miss, n = [], 0
    # ⛔⛔ 這一段本來比**正規式**：
    #     OUT\s*=\s*os\.path\.join\([^)]*"meta"[^)]*"_[A-Za-z0-9_]+\.txt"
    #   ⚠ 而 `[^)]*` **跨不過括號** ⇒ 寫成
    #     `os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "meta", …)`
    #     的那幾支**掃不到**。
    #   ⇒ 2026-09-15 實測：它說「17 支全部都叫」，⭐ 而真正的母體是 **20 支**，
    #     ⛔ 漏掉的三支（`bsr_probe`／`finmind_probe`／`tls_probe`）**正好就是
    #     沒有叫 `probe_stamp()` 的那三支**——⚠ 而報表上寫著 17/17。
    #   ⇒ ⭐ 這是第七點那句套在守門自己身上：
    #     **回報「某群 0 筆」時，要附上那個判準在該群抓到的正例數**
    #     ——⛔ 而「母體本身被判準縮小了」比 0 筆更難看出來。
    # ⇒ 改比 **AST**：任何一個 `os.path.join(...)`，只要它的引數（含巢狀）裡
    #   同時出現字串 `"meta"` 與 `"_….txt"`，就算這支會寫探針輸出。
    import ast as _ast
    for f in sorted(_g.glob(os.path.join(here, "*.py"))):
        base = os.path.basename(f)
        if base.startswith("selftest_"):
            continue
        t = io.open(f, encoding="utf-8").read()
        try:
            tree = _ast.parse(t)
        except SyntaxError:
            continue
        found = False
        for node in _ast.walk(tree):
            if not (isinstance(node, _ast.Call)
                    and isinstance(node.func, _ast.Attribute)
                    and node.func.attr == "join"):
                continue
            lits = [x.value for x in _ast.walk(node)
                    if isinstance(x, _ast.Constant) and isinstance(x.value, str)]
            # ⛔ `_*_low.txt` 不算：那是**低水位檔**（一個數字），⚠ 不是給人讀的報告
            #   ——它們走 `lowwater.py`，而那一族自己有 `selftest_lowwater` ⑨ 在守。
            #   ⇒ 判準放寬成 AST 之後這一族會被撈進來（實測多 8 支）⇒ 要排掉，
            #   ⛔ 否則這一條會變成一條天天紅而且紅得沒道理的閘門。
            if "meta" in lits and any(
                    _re.fullmatch(r"_[A-Za-z0-9_]+\.txt", v)
                    and not v.endswith("_low.txt") for v in lits):
                found = True
                break
        if not found:
            continue
        n += 1
        if "probe_stamp(" not in t:
            miss.append(base)
    ok = not miss and n >= 20
    print(("✓ " if ok else "✗ ")
          + f"⭐⭐ {n} 支寫探針輸出的程式**全部**都叫 `backfill.probe_stamp()`"
            "（⛔ 少一支，那一份就講不出自己是哪一趟）")
    if miss:
        print(f"    ⛔ 沒叫的：{miss}")
        bad += 1
    elif n < 20:
        print(f"    ⛔ 只掃到 {n} 支（⚠ 0 支跟全部通過長得一樣）")
        bad += 1
    # ⭐ 而那一份實作自己也要驗（⛔ 不是只驗呼叫點）
    #
    # ⛔⛔ 這兩條**一定要自己把環境切出來**，⚠ 不可以用「現在剛好在哪裡」：
    #   2026-09-15 我第一版寫成 `"不是 Actions" in probe_stamp()`
    #   ⇒ 在 Actions 上 `GITHUB_ACTIONS=true` ⇒ 那句話**必然不在** ⇒ 必然紅
    #   ⇒ probe run 100 的 step 12 當場 failure（而它 `continue-on-error`
    #     ⇒ ⛔ 沒有任何地方會說，run 的畫面照樣往下跑）。
    # ⭐ 這是 CLAUDE.md 六點五那條的**第三個變數**：
    #   已知會讓斷言必然不成立的環境差異，原本兩個（選用套件在不在、在哪個 ref），
    #   ⇒ 現在第三個：**這一趟是不是在 Actions 上**。
    # ⇒ 處置不是「跳過」，是**兩種都自己造出來各驗一次**（環境無關）。
    import backfill as _B
    _saved = os.environ.get("GITHUB_ACTIONS")
    try:
        os.environ["GITHUB_ACTIONS"] = "true"
        line = _B.probe_stamp()
        need = ("這一趟", "台北", "ref")
        ok2 = all(w in line for w in need) and line.endswith("\n")
        print(("✓ " if ok2 else "✗ ")
              + "backfill.probe_stamp 本身：講得出**時間／ref／在哪裡跑**"
                "（⚠ ref 要寫，因為排程跑的一律是 main）")
        if not ok2:
            print(f"    實得：{line!r}")
            bad += 1
        ok4 = "不是 Actions" not in line
        print(("✓ " if ok4 else "✗ ")
              + "⭐ 在 Actions 上**不會**誤標成「不是 Actions 跑的」"
                "（⛔ 誤標的話每一份輸出都帶一句假警語，警語就沒有人看了）")
        if not ok4:
            bad += 1
        os.environ["GITHUB_ACTIONS"] = "false"
        ok3 = "不是 Actions" in _B.probe_stamp()
        print(("✓ " if ok3 else "✗ ")
              + "⛔ 非 Actions 時要標「不是 Actions 跑的」（⚠ 這裡對交易所 403）")
        if not ok3:
            bad += 1
        # ⛔⛔ 而「在不在 Actions 上」只准有**一份**判準（四點五）：
        #   `runlog._block` 比的是 `== "true"`，而 `probe_stamp` 本來比的是
        #   **有沒有設** ⇒ `GITHUB_ACTIONS="false"` 在後者是真
        #   ⇒ 它會說「這是 Actions 跑的」並**把那句「不可信」的警語拿掉**。
        #   ⚠ 而拿掉之後，一份本機跑的輸出看起來跟 Actions 跑的一模一樣。
        import runlog as _rl
        ok5 = _rl.on_actions() is False
        os.environ["GITHUB_ACTIONS"] = "true"
        ok5 = ok5 and _rl.on_actions() is True
        print(("✓ " if ok5 else "✗ ")
              + '⭐ `on_actions()` 比的是逐字 `"true"`'
                "（⛔ 不是「有沒有設」——`\"false\"` 也是有設）")
        if not ok5:
            bad += 1
        # ⭐ 而**沒有第二份**：⛔ 誰都不准自己讀那個環境變數
        # ⛔⛔ 這一掃要比 **AST**，⚠ 不是比字串——「GITHUB_ACTIONS」這幾個字
        #   在上面那段**說明文字裡本來就有一份**（`selftest_ca_chain` 盯
        #   `CERT_NONE` 時踩過同一個）。⇒ 比字串的話它永遠紅，
        #   而一條永遠紅的斷言會被學會忽略。
        import ast as _ast2
        others = []
        for _f in sorted(glob.glob(os.path.join(_here_dir(), "*.py"))):
            b = os.path.basename(_f)
            if b in ("runlog.py",) or b.startswith("selftest_"):
                continue
            try:
                tree = _ast2.parse(io.open(_f, encoding="utf-8").read())
            except SyntaxError:
                continue
            for node in _ast2.walk(tree):
                if (isinstance(node, _ast2.Constant)
                        and node.value == "GITHUB_ACTIONS"):
                    others.append(b)
                    break
        print(("✓ " if not others else "✗ ")
              + "⭐ 只有 `runlog.on_actions()` 一份實作"
                "（⛔ 兩份的判準不一樣時，結論會相反）")
        if others:
            print(f"    ⛔ 另有自己讀環境變數的：{others}")
            bad += 1
    finally:
        if _saved is None:
            os.environ.pop("GITHUB_ACTIONS", None)
        else:
            os.environ["GITHUB_ACTIONS"] = _saved
    return bad


def check_survivor_fs():
    """⛔⛔ `mops_probe.survivor_fs_case` **自己會不會炸**（2026-09-15 付過代價）。

    probe 112 實測：`mops_history.parse_fs` 的 docstring 寫「回 4 元組」、
    ⚠ 而它回的是 **5 個** ⇒ 我照說明拆 ⇒
    `ValueError: too many values to unpack` ⇒ ⛔ **整支 `mops_probe.py` rc=1**
    ⇒ 那一趟的 `data/meta/_mops_probe.txt` 是**上一次**的內容
    （守門有補一行 ✗ 標記，⚠ 而那一節從頭到尾沒落地）。

    ⇒ ⭐ 這一條是第七點第六個那條的同一族：
      **一段解析／錯誤處理本身也是程式 ⇒ 它也要有「它自己會不會炸」的斷言**，
      ⛔ 而斷言要驗**終點**（跑完、那幾行真的印出來），
      不是驗「原始碼裡有沒有那個 unpack」（第七點第八個：註解裡也有一份）。

    ⚠ 而假回應要照真回應的形狀做：真的 t163sb04 是「一個業別一張表」
      ⇒ 這裡給**兩張**，而且其中一張帶目標代號、另一張不帶
      ⇒ ⛔ 只給一張的話，「跨表收集代號」那一段等於沒測。
    """
    import mops_probe as MP
    import mops_history as MH
    bad = 0

    def _tbl(rows):
        head = ("<tr><td>公司代號</td><td>公司名稱</td>"
                "<td>營業收入</td><td>營業成本</td></tr>")
        body = "".join(f"<tr><td>{c}</td><td>{n}</td><td>1,000</td><td>500</td></tr>"
                       for c, n in rows)
        return f"<table>{head}{body}</table>"

    page = ("<html><body>一般業<" + "/br>" + _tbl([("2330", "台積電"),
                                                   ("2456", "奇力新")])
            + "金融保險業" + _tbl([("2882", "國泰金")])
            + "</body></html>").encode("utf-8")

    out, saved = [], MH._fetch
    MH._fetch = lambda url, form=None, **kw: (page, "")
    try:
        MP.survivor_fs_case(out)
        err = None
    except Exception as ex:                                      # noqa: BLE001
        err = ex
    finally:
        MH._fetch = saved
    txt = "\n".join(out)

    # ⭐ ①「跑完不炸」——⛔ 這一條就是 probe 112 那個 bug 的**終點**斷言
    ok = err is None
    print(("✓ " if ok else "✗ ")
          + "survivor_fs_case 拿**真形狀的假回應**跑完不丟例外"
            "（⛔ probe 112 就是死在這裡：docstring 4 個、實際 5 個）")
    if not ok:
        print(f"    ⛔ {type(err).__name__}: {err}")
        bad += 1
        return bad

    for name, want in (
            ("② 把**相異代號數**講出來（⇒ 兩張表都收得到 ⇒ 3 個）", "相異代號 3 個"),
            ("③ 逐格講「那幾檔在不在裡面」（⛔ 不下結論，由輸出講）", "那幾檔在裡面"),
            ("④ 而**不在裡面的**也要單獨列（⇒ 兩個方向都印）", "不在裡面的"),
            ("⑤ 明寫「⛔ 不可以把月營收那條的結論套過來」（三點②）", "每支端點都要自己實測"),
            # ⭐⭐ ⑥ 代號**整份**要印出來（⛔ 只印個數的話，母體級差集做不出來）
            #   ⚠ 第十個那句：一個抽樣檢查點對得上，證明的是那幾個點，不是那一批。
            ("⑥ ⭐ 把**代號整份**攤出來（⇒ 140 檔那種母體級差集才做得出來）",
             "代號整份（3 個，供母體級差集用）：2330,2456,2882"),
            ("  而它只印損益表那一格（⛔ 資產負債表代號集合相同，再印一次是洗版）",
             "t163sb05"),
    ):
        if want in txt:
            print(f"✓ survivor_fs_case {name}")
        else:
            print(f"✗ survivor_fs_case {name}｜找不到「{want}」")
            bad += 1

    # ⭐ ⑥ 取不回來那一格：⛔ **不可以**讀成「它不在裡面」
    out2, saved = [], MH._fetch
    MH._fetch = lambda url, form=None, **kw: (b"", "HTTP 500 Internal Server Error")
    try:
        MP.survivor_fs_case(out2)
        err2 = None
    except Exception as ex:                                      # noqa: BLE001
        err2 = ex
    finally:
        MH._fetch = saved
    t2 = "\n".join(out2)
    ok = err2 is None and "【未驗】" in t2 and "不在裡面的" not in t2
    print(("✓ " if ok else "✗ ")
          + "survivor_fs_case ⭐ 取不回來 ⇒ 標【未驗】，"
            "⛔ 不可以印成「那幾檔不在裡面」（那會被讀成倖存者偏誤的證據）")
    if not ok:
        print(f"    ⛔ err={err2}｜實得：{t2[-260:]}")
        bad += 1
    return bad


def check_sibling_doors():
    """⛔⛔ 一支探針**借別的模組的門**出去，而那道門沒被換掉 ⇒ 這支「離線」自測會真的連外。

    2026-09-15 實際代價（daily run 34993234076，main 上）：
    `mops_probe.survivor_fs_case` 打的是 `mops_history._fetch`，
    ⚠ 而 `run()` 只換掉 `mod` 自己的 `_post`／`get`
    ⇒ 那 4 發**真的送出去了**（每發約 1.2 MB）。

    ⭐ 而它壞的方向正是六點五那一族：
    ```
    開發容器   那 4 發**一定失敗** ⇒ 走「取不回來 ⇒【未驗】」⇒ 本機全綠
    Actions    那 4 發**會成功**   ⇒ 輸出完全不同 ⇒ ⛔ 那裡紅
    ```
    ⚠ 而「本機綠、Actions 紅」在畫面上跟「這條斷言壞了」一模一樣。

    ⇒ 這一道掃**全部探針**的 AST：凡是 `<別的模組>.<抓取用的函式>(` 的呼叫，
    都要在 `SIBLING_DOORS` 裡登記過。⛔ 比 AST 不比字串
    （第七點第八個：那幾個名字在註解裡也有一份——本函式的 docstring 就有）。

    ## ⛔⛔ 而這一道**不夠**——我同一個小時內就寫出它抓不到的形狀

    ```python
    from twparse import post_form as _post_form      # ⇒ 呼叫時是**裸名字**
    _post_form(url, form)                            # ⛔ 不是 `模組.函式(`
    ```
    ⇒ 這一道看不到它。⚠ 而實測 `mops_probe.ezsearch_case` **一直**在打
    `twparse.post_form`（每趟 12 發真的連外），而它回報「全部都登記過」。

    ⇒ ⭐ **真正的終點判準是 `run()` 裡那個「連外次數」計數器**（socket 層）：
    ⛔ 它不問你怎麼寫的，只問**有沒有連出去** ⇒ 每一種寫法都擋得住。
    ⚠ 這一道留著當**輔助**：它講得出「是哪一行」，而計數器只講得出「有」。
    ⇒ ⛔ 而它**不可以**被讀成「已經沒有人在借門了」。
    """
    import ast as _ast
    doors = {"_fetch", "_post", "get", "one", "post", "fetch"}
    here = _here_dir()
    ours = {n[:-3] for n in os.listdir(here) if n.endswith(".py")}
    bad, checked, found = 0, 0, 0
    for name in SECTIONS:
        path = os.path.join(here, name + ".py")
        if not os.path.isfile(path):
            continue
        checked += 1
        tree = _ast.parse(io.open(path, encoding="utf-8").read())
        alias = {}                       # 區域名字 → 真模組名
        for n in _ast.walk(tree):
            if isinstance(n, _ast.Import):
                for a in n.names:
                    alias[a.asname or a.name] = a.name
        reg = SIBLING_DOORS.get(name, {})
        for n in _ast.walk(tree):
            if not (isinstance(n, _ast.Call)
                    and isinstance(n.func, _ast.Attribute)
                    and isinstance(n.func.value, _ast.Name)):
                continue
            mod = alias.get(n.func.value.id)
            if mod is None or mod not in ours or mod == name:
                continue
            if n.func.attr not in doors:
                continue
            # ⭐ `backfill.get`／`new_session` 是 `run()` **本來就換掉**的那道主門
            #   （`B.get = _get`、`B.new_session = _fake_ns`）⇒ 不是「借來的門」。
            #   ⛔ 而它要列在這裡、不是靠「反正它會過」——下一個人改 `run()` 時
            #   才看得出這兩個名字是有人在負責的。
            if mod == "backfill" and n.func.attr in ("get", "new_session"):
                continue
            found += 1
            if n.func.attr not in reg.get(mod, ()):
                print(f"✗ {name} 借了 `{mod}.{n.func.attr}` 這道門"
                      f"（第 {n.lineno} 行），⛔ 而 SIBLING_DOORS 沒登記"
                      "　⇒ 這支「離線」自測會真的連外")
                bad += 1
    # ⭐ 母體大小自己是一道斷言（第七點⑨：母體被判準悄悄縮小過一次）
    if checked < 10:
        print(f"✗ 掃到的探針只有 {checked} 支（⛔ 母體縮小了，SECTIONS 有 "
              f"{len(SECTIONS)} 支）")
        bad += 1
    elif found == 0:
        print("✗ 這一道**一個借來的門都沒掃到**"
              "（⛔ 0 個與「全部合規」在紙上一模一樣，第七點）")
        bad += 1
    elif not bad:
        print(f"✓ ⭐ {checked} 支探針裡 `模組.函式(` 形式的借門共 {found} 處，"
              "全部都在 `SIBLING_DOORS` 裡登記過"
              "　⚠ **而這一道抓不到 `from X import y` 那種裸名字**"
              "　⇒ ⭐ 真正的守門是 `run()` 的連外次數計數器")
    return bad


def check_avg_residual():
    """⭐⭐ `keys_probe.avg_residual()` 的**逐列迴圈**真的被走過，而且比的是數值。

    ## ⛔ 這一節存在的理由是一個在 Actions 上炸掉的 `NameError`

    probe run 131（2026-09-16）：`keys_probe.py:591` `NameError: name '_n' is not defined`
    ⇒ 整支 rc=1 ⇒ `_keys_probe.txt` 被守門還原成**上一趟**的內容。

    ⭐⭐ 而**離線自測是全綠的**：`run("keys_probe")` 餵的假回應沒有 `title`
    ⇒ 上面那道「title 要回音代號與月份」提前 `continue`
    ⇒ ⛔ 出事那一行**一次都沒有被走過**（第七點第三個：測了判準、沒測那條路）。

    ⇒ ⭐ 所以這一節的假回應要**照真回應的形狀**做到「title 回音得了」那一格，
    ⛔ 不是再餵一份走不進去的。

    ## ⇒ 而順手抓到第二個：**比字串會確認一個假的發現**

    我方 CSV 寫 `4.3`、官方回 `4.30` ⇒ 比字串的話**每一天**都是「收盤不同」，
    ⚠ 而「有幾天差 0.01」正是這一節在找的答案
    ⇒ ⛔ 它會**證實一個不存在的發現**，而輸出看起來完全正常。
    """
    import keys_probe as K
    bad = 0

    def ck(n, c, d=""):
        nonlocal bad
        print(("  ✓ " if c else "  ✗ ") + n + ("" if c else f"　{d[:220]}"))
        if not c:
            bad += 1

    sid, roc = K.AVG_RESID
    ad = roc + 1911

    def resp(rows, mo):
        return json.dumps({
            "stat": "OK",
            "title": f"{roc}年{mo:02d}月 {sid} 首利 各日成交資訊",
            "fields": ["日期", "成交股數", "成交金額", "開盤價",
                       "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
            "data": rows,
        }, ensure_ascii=False).encode()

    def row(day, close):
        return [f"{roc}/{day[:2]}/{day[2:]}", "1,000", "4,300",
                "4.30", "4.30", "4.30", close, "0.00", "5"]

    real_get, real_root = B.get, K._ROOT
    tmp = tempfile.mkdtemp(prefix="keysprobe_")
    try:
        os.makedirs(os.path.join(tmp, "stocks"), exist_ok=True)
        io.open(os.path.join(tmp, "stocks", f"{sid}.csv"), "w",
                encoding="utf-8").write(
            "date,close\n"
            f"{ad}-01-05,4.3\n"      # ⭐ 我方 4.3 vs 官方 4.30 ⇒ **相同**
            f"{ad}-01-06,4.29\n"     # ⭐ 我方 4.29 vs 官方 4.30 ⇒ **差 0.01**
            f"{ad}-01-07,4.31\n")    # ⚠ 官方那一天回 `--` ⇒ **比不了**
        K._ROOT = tmp
        pages = {1: resp([row("0105", "4.30"), row("0106", "4.30"),
                          row("0107", "--")], 1)}

        def fake(url, retries=3, timeout=45):
            mo = int(url.split("date=")[1][4:6])
            return (pages.get(mo, resp([], mo)), None)

        B.get = K.B.get = fake
        mark = len(K.LINES)
        K.avg_residual()
        t = "\n".join(K.LINES[mark:])
    finally:
        B.get = K.B.get = real_get
        K._ROOT = real_root
        shutil.rmtree(tmp, ignore_errors=True)

    ck("① ⭐⭐ 逐列迴圈**真的被走過**（官方回到的天數 > 0）",
       "官方回到的天數：2" in t, t)
    ck("② ⭐ `4.3` vs `4.30` **不算不同**（⛔ 比字串的話這裡會是 2）",
       "**收盤價不同的日子：1**" in t, t)
    ck("③ ⭐ 真的差 0.01 的那一天有被列出來",
       f"{ad}-01-06" in t, t)
    # ⛔ 我第一版在這裡斷言「官方回 `--` ⇒ 印『這一層沒跑』」——**那個情境造不出來**：
    #   抓取那一段本來就把 `--` 濾掉了 ⇒ 那一天根本不會進 `got`
    #   ⇒ 它落在「只有我方有的日子」，⛔ 不在交集裡 ⇒ `None` 那條分支走不到。
    #   ⚠ 而「斷言沒抓到」與「我根本沒造出那個情境」長得一模一樣（第七點第四個）。
    #   ⇒ ⭐ 分成兩條：④ 驗**真的會發生**的那一半（它落在只有我方有的那一邊），
    #     ⑥ 拿**合成**輸入直接驗 `_same_price` 的三種回答（環境無關，第七點第七個）。
    ck("④ ⭐ 官方濾掉的那一天落在「只有我方有的日子」（⛔ 不是被判成『收盤不同』）",
       "只有我方有的日子：1" in t and f"{ad}-01-07" in t, t)
    ck("⑤ ⛔ `avg_residual` 跑完**沒有丟例外**（run 131 就是死在這裡）",
       "官方回到的天數" in t, t)
    # ⑥ ⭐⭐ `_same_price` 的**三種**回答（⛔ 不是兩種）——拿合成輸入驗，⛔ 不靠現場
    ck("⑥ ⭐⭐ `_same_price` 回三種：相同／不同／**比不了**（⛔ None 不可以壓成 False）",
       (K._same_price("4.3", "4.30") is True
        and K._same_price("4.3", "4.31") is False
        and K._same_price("4.3", "--") is None
        and K._same_price("", "4.30") is None),
       str([K._same_price("4.3", "4.30"), K._same_price("4.3", "4.31"),
            K._same_price("4.3", "--"), K._same_price("", "4.30")]))
    return bad


def check_terms_case():
    """⭐⭐ 條款原文那一節（市場情報分析線 1508（乙））：**連結從頁面讀出來、原文逐字印**。

    ⛔ 這一節最可能的壞法**不是抓不到**（那很吵），是三種安靜的：

    ```
    ① 我自己拼路徑（/terms、/policy）⇒ 拼錯就回「這個站沒有條款」
       —— 而那是三點①（掃描範圍）＋四點五第七次（重造）同一個坑
    ② 印**我的摘要**而不是原文 ⇒ 三點② 已經證明過：同一份條款
       換個關鍵字就翻出禁止條文 ⇒ ⛔ 摘要漏掉的那一句沒有人會發現
    ③ 抓不到首頁時寫成「這個站沒有條款」⇒ 把「我沒查」讀成「它沒有」
    ```

    ⇒ 八條斷言逐條對應，⭐ 而 ⑦⑧ 是**反向**那兩條（抓不到／0 條命中）——
    ⛔ 它們才是主角：正向那幾條在真的壞掉時仍然會綠。
    """
    import re as _re
    import mops_probe as M
    bad = 0
    HOME = ("<html><body>"
            "<a href=\"/mops/web/t21sc03\">月營收</a>"
            "<a href='/mops/web/terms'>網站使用授權條款</a>"
            "<a href=\"https://x.tw/p\">隱私權政策</a>"
            "</body></html>").encode()
    # ⛔⛔ 假回應要**照真回應的形狀**做（第七點）：真的條款頁是幾千字，
    #   ⚠ 而禁止條文**不會在開頭**。第一版我寫了一句 12 字的假條款
    #   ⇒ 「只印前 20 字」的突變 **T3 全綠** —— 因為那 12 字整段都在前 20 字裡。
    #   ⇒ ⭐ 把禁止條文放到**第 1,500 字之後**，再放一段超過 4,000 字的尾巴，
    #     這樣 ⑤（逐字印）與 ⑩（截斷要講）才真的被走過。
    TERMS = ("<html><body><p>" + "本網站係公開資訊觀測站。" * 120
             + "本網站資料不得重製。" + "其他條文。" * 600
             + "</p></body></html>").encode()
    real = B.get

    def fake(url, retries=3, timeout=45):
        return (HOME, None) if url.endswith("/index") else (TERMS, None)

    def ck(n, c, d=""):
        nonlocal bad
        print(("  ✓ " if c else "  ✗ ") + n + ("" if c else f"　{d[:200]}"))
        if not c:
            bad += 1

    try:
        B.get = M.B.get = fake
        out = []
        M.terms_case(out)
        t = "\n".join(out)
        ck("① 只收**文字含關鍵字**的連結（月營收那條不收）", "t21sc03" not in t, t)
        ck("② 相對路徑接成絕對", "https://mopsov.twse.com.tw/mops/web/terms" in t, t)
        ck("③ 絕對路徑原樣保留", "https://x.tw/p" in t, t)
        ck("④ 命中數自己印出來（2 條）", "**2 條**" in t, t)
        ck("⑤ ⭐ 原文**逐字**印（禁止條文那一句在）", "不得重製" in t, t)
        ck("⑥ ⭐ 母體大小自己是一道斷言（3 個 <a>）", "共 3 個" in t, t)
        ck("⑩ ⭐⭐ 超過 4,000 字要**講出它被截了**（⛔ 不是靜靜少印）",
           "截到 4,000 字" in t, t)

        B.get = M.B.get = lambda u, retries=3, timeout=45: (None, "boom")
        o2 = []
        M.terms_case(o2)
        t2 = "\n".join(o2)
        ck("⑦ ⭐⭐ 抓不到首頁 ⇒ 寫【未驗】，⛔ 不是「這個站沒有條款」",
           "【未驗】" in t2 and "0 條" not in t2, t2)

        B.get = M.B.get = lambda u, retries=3, timeout=45: (
            "<a href='/a'>月營收</a>".encode(), None)
        o3 = []
        M.terms_case(o3)
        t3 = "\n".join(o3)
        ck("⑧ ⭐⭐ 0 條命中 ⇒ 明講**掃描範圍**（不證明這個站沒有）",
           "不證明這個站沒有條款" in t3, t3)
    finally:
        B.get = M.B.get = real

    # ⭐ ⑨ 掃原始碼：⛔ 不可以有人回去拼路徑。判準比 **AST 的字串常數**，
    #   ⚠ 不比整份原始碼——那幾個字在上面的 docstring 裡就有一份（第七點第八個）。
    import ast as _ast
    src = io.open(os.path.join(_here_dir(), "mops_probe.py"), encoding="utf-8").read()
    fn = next((n for n in _ast.walk(_ast.parse(src))
               if isinstance(n, _ast.FunctionDef) and n.name == "terms_case"), None)
    # ⛔⛔ **docstring 自己也是一個字串常數**——而上面那段說明裡就寫著
    #   `/terms`、`/policy`（它們正是我在講「不要拼」的那幾個）。
    #   ⇒ 第一版沒扣掉它 ⇒ 這一條**當場紅**，⚠ 而那不是程式有問題。
    #   ⇒ ⭐ 這就是第七點第八個那條的又一次：**斷言要驗終點**，
    #     而「原始碼長什麼樣」從來不是終點 ⇒ 至少要把說明文字扣掉。
    body = fn.body[1:] if (fn and fn.body and isinstance(fn.body[0], _ast.Expr)
                           and isinstance(getattr(fn.body[0], "value", None), _ast.Constant)
                           and isinstance(fn.body[0].value.value, str)) else (fn.body if fn else [])
    lits = [n.value for b in body for n in _ast.walk(b)
            if isinstance(n, _ast.Constant) and isinstance(n.value, str)]
    guessed = [x for x in lits if _re.search(r"/(terms|policy|privacy|copyright)\b", x)]
    ck("⑨ ⛔ `terms_case` 的字串常數裡**沒有我自己拼的條款路徑**",
       fn is not None and not guessed, f"{guessed}")
    return bad


def main():
    bad = 0
    for name, want in SECTIONS.items():
        err, out = run(name)
        if err is not None:
            print(f"✗ {name}.main() 丟例外：{type(err).__name__}: {err}")
            bad += 1
            continue
        # ⭐⭐ 終點：這一支在「離線」自測裡**一次都沒有試著連外**
        #   ⛔ 前一版是掃 AST 找 `模組.函式(`，⚠ 而 `from X import y as z` 那種
        #   **裸名字**的呼叫它看不到——我同一個小時內就寫出那種形狀。
        #   ⇒ 判準換成「到底有沒有連出去」，⭐ 每一種寫法都擋得住。
        if getattr(run, "last_net", 0):
            print(f"✗ {name} 在「離線」自測裡試著**連外 {run.last_net} 次**"
                  "　⇒ ⛔ 有一道抓取的門沒被換掉"
                  "（⚠ 探針自己的「取不回來」處理會把它吞掉 ⇒ 看起來完全正常）")
            bad += 1
        missing = [s for s in want if s not in out]
        if missing:
            print(f"✗ {name} 少了這幾節：{missing}"
                  "（假回應可能不夠讓它走進去，或那一節有提前 return）")
            bad += 1
        else:
            print(f"✓ {name} 走完全程"
                  + (f"，{len(want)} 節都出現" if want else ""))
    bad += check_delist_cross()
    bad += check_site_inventory_openapi()
    bad += check_openapi_period_col()
    bad += check_bridge_blank_vs_ignored()
    bad += check_xhr_hunt()
    bad += check_js_followups()
    bad += check_scale_qualified()
    bad += check_f2_numbers()
    bad += check_js_needles()
    bad += check_page_wiring()
    bad += check_no_dup_keys()
    bad += check_probe_stamp()
    bad += check_survivor_fs()
    bad += check_sibling_doors()
    bad += check_avg_residual()
    bad += check_terms_case()
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""離線自我測試：用 2026-09-06 實測到的真實回應做 fixture，跑 parse_reduce ＋ adjust。

★ 為什麼要離線測：抓取紀律第 13 條禁止用 bash/python 直打第三方端點。
  fixture 的內容是 WebFetch 實際回來的那幾列，一個字都沒改。
"""
import io, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feeds
import price_limit as P


# ★ 「這支測試有沒有碰到真的 data/」要用**測試前後的指紋比對**來證明。
#   ⛔ 不可以寫成 `assert not os.path.exists(HERE/data/adj)`——
#      `data/adj/` 是 repo 的正式目錄（2,200 個檔），那個斷言在任何完整 clone 上
#      都必定失敗，而在沒有 clone 的沙盒裡又必定通過。它分不出
#      「測試建的」與「本來就有的」，是拿間接證據（存不存在）代替直接證據（有沒有變）。
#   兩個守備目標：
#     data/adj/            —— adjust.py 的輸出，測試跑的就是它
#     data/meta/_last_run.md —— adjust.py 會 import runlog 寫這一份；
#                              相對路徑那個 bug 就是從這裡把 suspend 的區塊洗掉的
_GUARD_DIR = os.path.join(HERE, "data", "adj")
_GUARD_FILE = os.path.join(HERE, "data", "meta", "_last_run.md")


def _fingerprint():
    """回傳可比對的指紋。目錄取（檔名, 大小, mtime），檔案取內容。"""
    d = None
    if os.path.isdir(_GUARD_DIR):
        d = sorted((n, os.path.getsize(os.path.join(_GUARD_DIR, n)),
                    os.stat(os.path.join(_GUARD_DIR, n)).st_mtime_ns)
                   for n in os.listdir(_GUARD_DIR))
    f = None
    if os.path.isfile(_GUARD_FILE):
        f = io.open(_GUARD_FILE, "rb").read()
    return d, f


_BEFORE = _fingerprint()

FIELDS = ["恢復買賣日期", "股票代號", "名稱", "停止買賣前收盤價格", "恢復買賣參考價",
          "漲停價格", "跌停價格", "開盤競價基準", "除權參考價", "減資原因", "詳細資料"]

# 這三列是 WebFetch 2026-09-06 從 reducation/TWTAUU 實際取回的（未改動）
DOC_2015 = {
    "stat": "OK",
    "title": "104年01月01日 至 104年12月31日 股票減資恢復買賣參考價格",
    "fields": FIELDS,
    "strDate": "20150101", "endDate": "20151231",
    "data": [
        ["104/01/23", "3040", "遠見", "31.90", "41.28", "44.15", "38.40", "41.30", "--",
         "退還股款", "3040  ,20150204"],
        ["104/03/20", "3536", "誠創", "6.58", "13.33", "14.25", "12.15", "13.35", "--",
         "彌補虧損", "3536  ,20150107"],
        ["104/12/30", "2017", "官田鋼", "5.25", "6.17", "6.78", "5.56", "6.17", "--",
         "彌補虧損", "2017  ,20151215"],
    ],
}
DOC_EMPTY = {"stat": "很抱歉，沒有符合條件的資料!"}

fail = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fail.append(msg)


print("── 1. parse_reduce ──")
rows, note = feeds.parse_reduce(DOC_2015, "2015-01-01", None)
print(f"  note={note}")
for r in rows:
    print("   ", r)
check(len(rows) == 3, "三列都收下")
check(rows[0][0] == "2015-01-23", f"斜線民國日期轉西元（得到 {rows[0][0]}）")
check(rows[1][0] == "2015-03-20" and rows[2][0] == "2015-12-30", "另兩列日期也對")
check(rows[1][4] == "彌補虧損", "減資原因有進來")
check(feeds.FEEDS["reduce"]["header"] ==
      ["date", "stock_id", "pre_close", "ref_price", "reason", "open_base",
       "ex_ref_price", "limit_up", "limit_down"],
      "表頭就是這九欄（⛔ 字面比對：欄序也是契約的一部分）")
check(len(rows[0]) == len(feeds.FEEDS["reduce"]["header"]), "每列欄數 = 表頭欄數")

# ⭐⭐ 2026-09-13：官方**一直有給** `漲停價格／跌停價格`，而我方一直丟掉。
#   ⛔ 而我為此花了一整輪去推論交易所的漲跌停（`factor_limit_check.py`）。
#   ⚠ 而「欄數對了」跟「那一欄是對的值」是兩件事（四點二③）
#     ⇒ 這兩條比的是**官方真的回過的數字**：3040 遠見 2015-01-23
#       前收 31.90 → 參考 41.28、漲停 44.15、跌停 38.40。
check(rows[0][7] == "44.15", "⭐ `limit_up` 取到官方的漲停價（44.15）")
check(rows[0][8] == "38.40", "⭐ `limit_down` 取到官方的跌停價（38.40）")
# ⛔ 反向：⚠ 若取錯欄位，最可能撿到的是**隔壁的開盤競價基準**（41.30）
#   ——它跟漲停價都是「合法的價格數字」，⛔ 光看型別分不出來。
check(rows[0][7] != rows[0][5] and rows[0][8] != rows[0][5],
      "⛔ 而它們不等於開盤競價基準（⇒ 不是撿到隔壁那一欄）")
# ⭐ 官方漲跌停必定夾住參考價
_ref, _up, _dn = float(rows[0][3]), float(rows[0][7]), float(rows[0][8])
check(_dn < _ref < _up, "⭐ 官方漲跌停夾住參考價")
# ⛔⛔ 2026-09-13 這裡原本寫的是「就是參考價的 ±10%」——**它紅了，而且它該紅**：
#   44.15/41.28 = 1.0695。⚠ 台股的單日漲跌幅 **2015-06-01 才由 7% 放寬為 10%**，
#   而這一列是 2015-01-23 ⇒ 它是 **7%**。
#   ⇒ 那個斷言把一個**有年代的**數字寫成了通則（三點2）。
# ⭐ 現在改成拿 `price_limit`（唯一的一份實作，四點五）逐位對——
#   ⛔ 而三列橫跨放寬日兩側，所以它同時釘住「年代切分真的有作用」。
check(P.up(_ref, rows[0][0]) == _up and P.down(_ref, rows[0][0]) == _dn,
      f"⭐ 官方漲跌停 = `price_limit` 算的（{rows[0][0]} 7% era）",)
_r2 = float(rows[2][3])
check(P.up(_r2, rows[2][0]) == float(rows[2][7])
      and P.down(_r2, rows[2][0]) == float(rows[2][8]),
      f"⭐ 而放寬日之後那一列是 10%（{rows[2][0]}）")
# ⛔ 反向：若把年代切分拿掉、一律用 10%，第一列就對不上 ⇒ 證明這個切分不是裝飾
check(P.up(_ref, "2026-01-02") != _up,
      "⛔ 反向：拿 10% 去算 2015-01-23 那一列，漲停就對不上（45.40 ≠ 44.15）")

print("── 1.2 ⭐ `parse_exright` 也要收下官方的漲跌停兩欄 ──")
# ⭐⭐ 官方 TWT49U 的 15 欄裡有 `漲停價格／跌停價格`，⛔ 而我方只取了 7 欄。
#   ⚠ 而我為此花了一整輪**推論**交易所的漲跌停。
_EXDOC = {"stat": "OK",
          "title": "104年01月01日 至 104年12月31日 除權除息計算結果表",
          "strDate": "20150101", "endDate": "20151231",
          "fields": ["資料日期", "股票代號", "股票名稱", "除權息前收盤價",
                     "除權息參考價", "權值+息值", "權/息", "漲停價格", "跌停價格",
                     "開盤競價基準", "減除股利參考價", "詳細資料",
                     "最近一次申報資料 季別/日期", "最近一次申報每股 (單位)淨值",
                     "最近一次申報每股 (單位)盈餘"],
          "data": [["104年01月05日", "2353", "宏碁", "21.35", "21.02", "0.325605",
                    "權", "22.80", "19.55", "21.35", "21.35", "2353,20150105",
                    "x", "25.67", "0.96"],
                   ["109年01月16日", "00714", "群益道瓊美國地產", "22.13", "21.92",
                    "0.210000", "息", "9,999.95", "0.01", "21.92", "21.92",
                    "00714,20200116", "", "", ""],
                   # ⭐ 第三列：**開盤競價基準與減除股利參考價不同**的形狀。
                   #   ⚠ 官方 notes 說「遇含現金增資除權時，開盤競價基準取最接近
                   #     **減除股利參考價**之檔位價」⇒ 兩者只差一個檔位
                   #   ⛔ 而前兩列剛好相同 ⇒ 「撿到隔壁那一欄」的突變**抓不到**。
                   ["104年01月06日", "1111", "測試", "21.50", "21.02", "0.480000",
                    "權", "22.80", "19.55", "21.35", "21.37", "1111,20150106",
                    "", "", ""]]}
_ex, _exnote = feeds.parse_exright(_EXDOC, "2015-01-01", None)
check(feeds.FEEDS["exright"]["header"] ==
      ["date", "stock_id", "pre_close", "ref_price", "value", "kind",
       "open_base", "limit_up", "limit_down", "ex_div_ref"],
      "⭐ exright 表頭就是這十欄（⛔ 字面比對：欄序也是契約）")
# ⭐⭐ `減除股利參考價`＝**不計現增稀釋**（＝(前收−息值)/(1+**無償**配股率)）
#   ⇒ **官方漲停的基準**。⛔ 2026-09-14 訂正：原本寫「只扣現金股利、不調整配股」是錯的。
check(_ex[0][9] == "21.35",
      f"⭐ `ex_div_ref` 取到 21.35（得到 {_ex[0][9]}）")
# ⛔ 反向：它最可能被撿成隔壁的「開盤競價基準」——⚠ 而前兩列那兩欄剛好相同
#   ⇒ 只靠前兩列的話，這個突變**抓不到**（實測 V4 全綠）。
check(_ex[2][9] == "21.37" and _ex[2][6] == "21.35",
      f"⛔ 兩欄不同的那一列要分得開（得到 ex_div_ref={_ex[2][9]}、"
      f"open_base={_ex[2][6]}）")
check(_ex[0][9] not in ("", None)
      and P.up(float(_ex[0][9]), _ex[0][0]) == float(_ex[0][7]),
      "⭐⭐ 而官方漲停 22.80 就是「減除股利參考價 × 1.07 捨去」"
      "（⛔ 用除權息參考價 21.02 算會得到 22.45）")
check(P.down(float(_ex[0][3]), _ex[0][0]) == float(_ex[0][8]),
      "⭐ 而跌停 19.55 用的是**除權息參考價** ⇒ 官方兩邊基準不同")
check(len(_ex) == 3 and len(_ex[0]) == len(feeds.FEEDS["exright"]["header"]),
      f"每列欄數 = 表頭欄數（得到 {len(_ex)} 列）")
check(_ex[0][7] == "22.80" and _ex[0][8] == "19.55",
      f"⭐ 2353 的官方漲跌停取到了（得到 {_ex[0][7]}／{_ex[0][8]}）")
# ⛔ 反向：最可能撿錯的是隔壁的「開盤競價基準」與「減除股利參考價」（都是 21.35）
check(_ex[0][7] != _ex[0][6] and _ex[0][8] != _ex[0][6],
      "⛔ 而它們不等於開盤競價基準（⇒ 不是撿到隔壁那一欄）")
check(_ex[1][7] == "9999.95" and _ex[1][8] == "0.01",
      f"⭐ 官方的「無漲跌幅限制」旗標原樣收下（得到 {_ex[1][7]}／{_ex[1][8]}）")
check(P.is_unlimited(_ex[1][7], _ex[1][8]) and not P.is_unlimited(_ex[0][7], _ex[0][8]),
      "⭐ 而 `price_limit.is_unlimited` 認得出那一列、不會誤判另一列")

print("── 1.5 ⭐ `--need-col` 對**區間型** feed 也要有效 ──")
# ⛔⛔ 原本它是**靜靜無效**的：`cmd_feed_range()` 在那段程式碼之前就 return 了
#   ⇒ `reduce`／`parvalue`／`etfsplit` 帶 `--need-col` 跑起來完全正常、什麼都沒補。
_H = feeds.FEEDS["reduce"]["header"]
_heads = {"2015-01-23.csv": ",".join(_H) + "\n",
          "2015-03-20.csv": "date,stock_id,pre_close,ref_price,reason,open_base,"
                            "ex_ref_price\n",
          "2015-12-30.csv": "date,stock_id,pre_close,ref_price,reason,open_base,"
                            "ex_ref_price\n"}
_bad, _ok = feeds.months_missing_col(_heads, "limit_up", _H)
check(_bad == {"2015-03", "2015-12"},
      f"⭐ 只挑出**表頭缺那一欄**的月份（得到 {sorted(_bad)}）")
check(_ok, "⭐ 而 `limit_up` 確實是這個 feed 的欄名")
# ⛔ 反向：欄名打錯 ⇒ 每一天都「缺」它 ⇒ 會整批重抓、白打幾百發
_bad2, _ok2 = feeds.months_missing_col(_heads, "limit_upp", _H)
check(len(_bad2) == 3 and not _ok2,
      "⛔ 欄名打錯 ⇒ 三個月**全部**算缺，而第二個回傳值要講出「這不是欄名」")
check(feeds.months_missing_col(_heads, "", _H) == (set(), True),
      "⛔ 沒帶 `--need-col` ⇒ 一個月都不重問（⚠ 這是預設那條路）")
# ⚠ 而「表頭有這一欄」的那個月**不可以**被挑出來——⛔ 否則每趟都重抓全部
check("2015-01" not in _bad, "⭐ 已經有那一欄的月份不重問")

print("── 2. _roc_date 兩種格式＋西元不誤中 ──")
check(feeds._roc_date("115/09/07") == "2026-09-07", "斜線民國")
check(feeds._roc_date("104年07月16日") == "2015-07-16", "年月日民國")
check(feeds._roc_date("2026/09/07") == "", "西元不會被當成民國")

print("── 3. 查無資料的辨識 ──")
check(bool(feeds._EMPTY_STAT_RE.search(DOC_EMPTY["stat"])), "「沒有符合條件的資料」認得出來")
check(not feeds._EMPTY_STAT_RE.search("OK"), "OK 不會被誤判成查無資料")

print("── 4. adjust.py 端到端 ──")
# ★★ **絕對不可以在 repo 目錄裡建 data/ 再刪掉。**
#   `adjust.py` 的 `_ROOT` 是「跟自己同一層的 data/」，若直接在這裡跑，
#   收尾的清除會把**真正的資料庫整個刪掉**（0.55 GB，而且 workflow 的
#   `git add -A data` 會把刪除 commit 上去）。
#   做法：把 adjust.py 複製到暫存目錄，資料也建在那裡，全程碰不到 repo。
TMP = tempfile.mkdtemp(prefix="adjtest_")
shutil.copy(os.path.join(HERE, "adjust.py"), TMP)
# adjust.py 會 import runlog 寫 _last_run.md，沙盒裡也要有它。
shutil.copy(os.path.join(HERE, "runlog.py"), TMP)
D = os.path.join(TMP, "data")
for p in ("universe/reduce", "universe/exright", "universe/daily", "stocks"):
    os.makedirs(os.path.join(D, p), exist_ok=True)


def w(path, header, lines):
    with io.open(os.path.join(D, path), "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for r in lines:
            f.write(",".join(r) + "\n")


RH = feeds.FEEDS["reduce"]["header"]
EH = feeds.FEEDS["exright"]["header"]

# 交易日曆（含停牌期間 03-17 ~ 03-19，該檔在那幾天沒有列）
days = ["2015-03-13", "2015-03-16", "2015-03-17", "2015-03-18", "2015-03-19",
        "2015-03-20", "2015-03-23", "2015-07-31", "2015-08-03"]
for d in days:
    w(f"universe/daily/{d}.csv", ["date", "stock_id", "close"], [[d, "3536", "0"]])

# 減資：3536 恢復買賣日 2015-03-20，停止買賣前收盤 6.58 → 參考 13.33
# ★ 這裡刻意放**三列一模一樣的 3536**——這是 repo 裡的真實內容
#   （2026-09-06 實測，減資表同一事件會重複出現，只有「除權參考價」欄有差）。
#   不去重的話 f 會被連乘成 2.0258³ = 8.32，而且**不會有任何錯誤訊息**。
w("universe/reduce/2015-03-20.csv", RH,
  [["2015-03-20", "3536", "6.58", "13.33", "彌補虧損", "13.35", ""],
   ["2015-03-20", "3536", "6.58", "13.33", "彌補虧損", "13.35", "13.06"],
   ["2015-03-20", "3536", "6.58", "13.33", "彌補虧損", "13.35", "13.06"]])
# ★ 尚未發生的事件：交易日曆最後一天是 2015-08-03，這筆在它之後。
#   它**不可以**產生還原因子——否則 2015-08-03 的收盤會被一個還沒發生的
#   減資還原，破壞「最新價 F=1、現價不動」這個不變量。
w("universe/reduce/2015-09-01.csv", RH,
  [["2015-09-01", "3536", "12.90", "25.80", "彌補虧損", "25.80", ""]])
# 除權息：同一檔 2015-08-03 除息，f=0.98
w("universe/exright/2015-08-03.csv", EH,
  [["2015-08-03", "3536", "13.20", "12.94", "0.26", "息", "12.94"]])
# ★ 陷阱測試：減資同日也有一列除權息 → 必須被丟掉，否則息值扣兩次
w("universe/exright/2015-03-20.csv", EH,
  [["2015-03-20", "3536", "6.58", "6.50", "0.08", "息", "6.50"]])

# 個股價格：停牌那三天故意沒有列（真實情況就是如此）
px = [("2015-03-13", "6.60"), ("2015-03-16", "6.58"),
      ("2015-03-20", "13.40"), ("2015-03-23", "13.10"),
      ("2015-07-31", "13.20"), ("2015-08-03", "12.90")]
with io.open(os.path.join(D, "stocks/3536.csv"), "w", encoding="utf-8") as f:
    f.write("date,open,high,low,close,volume\n")
    for d, c in px:
        f.write(f"{d},{c},{c},{c},{c},1000\n")

r = subprocess.run([sys.executable, os.path.join(TMP, "adjust.py")],
                   capture_output=True, text=True)
print(r.stdout.rstrip())
if r.stderr.strip():
    print("  [stderr]")
    for ln in r.stderr.rstrip().split("\n"):
        print("    " + ln)

out = io.open(os.path.join(D, "adj/3536.csv"), encoding="utf-8").read()
print("  data/adj/3536.csv:")
for ln in out.rstrip().split("\n"):
    print("    " + ln)
# ⛔⛔ 2026-09-10：這裡原本用**寫死的位置**取欄（`body[0][2]` ＝ cum_factor）。
#   K線線裁定的 `factor_official` 插進 `ADJ_HEADER` 之後，第 2 欄變成
#   `factor_official`（減資才有值、除權息是空的）
#   ⇒ `float("")` ⇒ **這支自測直接爆掉**。
#   ⚠ 而 `adjust.py` 那邊的同一個病更陰：`r[6] == "reduce"` 取到的變成 `kind`
#     ⇒ ⛔ 不爆、只是**減資事件數靜靜變成 0**。
#   ⇒ 一律**按欄名取**，欄名從檔案自己的表頭讀（⛔ 不從 `ADJ_HEADER` 抄，
#     那樣程式與測試會一起錯、一起綠）。
_ADJ_LINES = out.rstrip().split("\n")
_AI = {k: i for i, k in enumerate(_ADJ_LINES[0].split(","))}
body = [l.split(",") for l in _ADJ_LINES[1:]]
check({"date", "factor", "cum_factor", "event"} <= set(_AI),
      f"data/adj 的表頭認得出這四欄（實得 {sorted(_AI)}）")
check(len(body) == 2,
      f"只剩兩個事件（三列重複的減資去重＋同日除權息去重），實得 {len(body)}")
check("重複列丟棄 2 列" in r.stdout, "重複列有被算出來並報告")
check(body[0][_AI["event"]] == "reduce" and body[1][_AI["event"]] == "exright", "event 欄標對來源")
f_red, f_ex = (float(body[0][_AI["factor"]]),
               float(body[1][_AI["factor"]]))
check(abs(f_red - 13.33 / 6.58) < 1e-8,
      f"減資因子 = 13.33/6.58 = {f_red:.6f}（**不是連乘後的 8.32**）")
check(f_red < 3, "因子沒有被重複列連乘")
check(abs(float(body[0][_AI["cum_factor"]]) - f_red * f_ex) < 1e-7, "累積因子由後往前連乘")
check(abs(float(body[1][_AI["cum_factor"]]) - f_ex) < 1e-8, "最後一個事件的累積因子 = 自己")
# 6.58 是 2015-03-16 的收盤（停牌前最後一筆），不是 03-19（日曆前一交易日、該檔無列）
check("前收盤對不上（reduce）" not in r.stderr,
      "減資核對用「停牌前最後一筆收盤」（03-16 的 6.58）→ 0 不符")
check("前收盤對不上（exright）" not in r.stderr, "除權息核對仍用日曆前一交易日 → 0 不符")
check("查了 2 個事件、對不上 0 個" in r.stdout, "兩個事件都核對過且都相符")

idx = io.open(os.path.join(D, "adj/_index.csv"), encoding="utf-8").read()
print("  data/adj/_index.csv:")
for ln in idx.rstrip().split("\n"):
    print("    " + ln)
check(idx.split("\n")[0].split(",")[3] == "reduce_events", "_index 有 reduce_events 欄")
check(idx.split("\n")[1].split(",")[3] == "1", "_index 記到 1 個減資事件")
check("尚未發生的事件 1 筆，不採用" in r.stdout, "未來日期的事件被擋下並報告")
check(all(l.split(",")[0] != "2015-09-01" for l in out.rstrip().split("\n")[1:]),
      "未來事件沒有進 data/adj")
check(abs(float(body[1][_AI["cum_factor"]]) - f_ex) < 1e-8,
      "最新事件的累積因子仍是 1 個因子（未被未來事件汙染）")

print("── 5. cmd_probe：查無資料不可以被讀成「端點不可用」──")
# 2026-09-06 實測踩到的：--probe --feed reduce --date 2026-09-03 回「沒有可用候選」
# 並 exit 1，但端點是好的，只是那天沒有減資事件。
# 這裡用假的 B.get 重現當時的兩個回應，驗證新的兩段探測會走到有事件的區間。
import json as _json, types as _types

_seen = []


def _fake_get(url, retries=1, timeout=30):
    _seen.append(url)
    doc = DOC_2015 if "startDate=2015" in url else DOC_EMPTY
    return _json.dumps(doc).encode("utf-8"), None


_real_get, _real_known = feeds.B.get, feeds.B._known_codes
feeds.B.get = _fake_get
feeds.B._known_codes = lambda: set()
_buf = io.StringIO()
_stdout, sys.stdout = sys.stdout, _buf
try:
    rc = feeds.cmd_probe(_types.SimpleNamespace(
        feed="reduce", date="2026-09-03", sleep=0))
finally:
    sys.stdout = _stdout
    feeds.B.get, feeds.B._known_codes = _real_get, _real_known
log = _buf.getvalue()
for ln in log.rstrip().split("\n"):
    print("    " + ln)
check(rc == 0, f"exit code 0（舊版在這個情境是 1，實得 {rc}）")
check("端點通、這個區間沒有事件" in log, "空月份被標成「沒有事件」而不是失敗")
check("沒有可用候選" not in log, "不再印「沒有可用候選」")
check(any("startDate=20150101" in u for u in _seen), "空月份後有退到已知有事件的區間")
check("解析結果：3 列" in log, "在有事件的區間驗到解析")

print("── 6. 舊界線會發生什麼（回歸測試的反面）──")
print("    若沿用除權息的上限 1.5：13.33/6.58 = 2.026 > 1.5 → **整批被丟掉**，")
print("    摘要上看起來就像「這檔沒有減資」。這就是分開設界線的理由。")

shutil.rmtree(TMP, ignore_errors=True)     # 只刪暫存目錄，repo 的 data/ 沒被碰過
_d0, _f0 = _BEFORE
_d1, _f1 = _fingerprint()
check(_d0 == _d1, "★ repo 的 data/adj/ 沒有被建立、刪除或改動"
      + ("" if _d0 == _d1 else
         f"（{'不存在' if _d0 is None else str(len(_d0)) + ' 檔'}"
         f" → {'不存在' if _d1 is None else str(len(_d1)) + ' 檔'}）"))
check(_f0 == _f1, "★ repo 的 data/meta/_last_run.md 逐位元沒有被改動")
print()
print("全部通過" if not fail else f"★ {len(fail)} 項不通過：{fail}")
sys.exit(1 if fail else 0)

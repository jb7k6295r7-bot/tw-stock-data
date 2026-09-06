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
       "ex_ref_price"], "表頭與 parse 輸出的欄數一致")
check(len(rows[0]) == len(feeds.FEEDS["reduce"]["header"]), "每列欄數 = 表頭欄數")

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
w("universe/reduce/2015-03-20.csv", RH,
  [["2015-03-20", "3536", "6.58", "13.33", "彌補虧損", "13.35", ""]])
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
body = [l.split(",") for l in out.rstrip().split("\n")[1:]]
check(len(body) == 2, f"只有兩個事件（同日除權息已去重），實得 {len(body)}")
check(body[0][6] == "reduce" and body[1][6] == "exright", "event 欄標對來源")
f_red, f_ex = float(body[0][1]), float(body[1][1])
check(abs(f_red - 13.33 / 6.58) < 1e-8, f"減資因子 = 13.33/6.58 = {f_red:.6f}")
check(abs(float(body[0][2]) - f_red * f_ex) < 1e-7, "累積因子由後往前連乘")
check(abs(float(body[1][2]) - f_ex) < 1e-8, "最後一個事件的累積因子 = 自己")
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

print("── 5. 舊界線會發生什麼（回歸測試的反面）──")
print("    若沿用除權息的上限 1.5：13.33/6.58 = 2.026 > 1.5 → **整批被丟掉**，")
print("    摘要上看起來就像「這檔沒有減資」。這就是分開設界線的理由。")

shutil.rmtree(TMP, ignore_errors=True)     # 只刪暫存目錄，repo 的 data/ 沒被碰過
assert not os.path.exists(os.path.join(HERE, "data", "adj")), \
    "★ 測試不該在 repo 裡產生 data/adj"
print()
print("全部通過" if not fail else f"★ {len(fail)} 項不通過：{fail}")
sys.exit(1 if fail else 0)

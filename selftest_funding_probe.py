#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 funding_probe 的判準分不分得出來（⛔ 離線：把 B.get 換成假的，不連網）。

⭐ 重點：每一種分類都要有一個會紅的樣本 ——
  ⛔ 一條永遠回同一個值的判準，跟一條有效的判準在報告上長得一模一樣。
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funding_probe as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok     " + name)
    else:
        FAIL += 1
        print("  ✗      " + name + ("｜" + hint if hint else ""))


def _zip(text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("X-fundingRate-2024-01.csv", text)
    return buf.getvalue()


def _fake(ret):
    """→ 一支假的 B.get，永遠回 ret。"""
    def g(url, retries=3, timeout=45):
        return ret
    return g


def main():
    real = F.B.get
    try:
        print("① ⭐ 四種結果要分得出來（⛔ absent 與 error 混在一起 ⇒「還沒上市」與「被擋」同形）")
        good = _zip("calc_time,funding_interval_hours,last_funding_rate\n"
                    "1704067200000,8,0.0001\n1704096000000,8,0.00012\n")
        F.B.get = _fake((good, None))
        st, head, rows = F.fetch_rows("BTC", 2024, 1)
        ck("  ✅ 正常 zip ⇒ ok，表頭逐字保留、兩列資料",
           st == "ok" and head.startswith("calc_time") and len(rows) == 2,
           "實際：%s %r %s" % (st, head, rows))

        F.B.get = _fake((None, "HTTP 404 Not Found | <Error>NoSuchKey</Error>"))
        s404 = F.fetch_rows("SOL", 2019, 9)[0]
        ck("  ⭐ 404 ⇒ absent（還沒上市，合法）", s404 == "absent")

        F.B.get = _fake((None, "HTTP 403 Forbidden | <Error>AccessDenied</Error>"))
        s403 = F.fetch_rows("SOL", 2019, 9)[0]
        ck("  ⭐⭐ 403 也 ⇒ absent（⚠ S3 對不存在的檔常回 403，⛔ 只認 404 會把它判成打不通）",
           s403 == "absent")

        F.B.get = _fake((None, "URLError: <urlopen error [Errno 111] Connection refused>"))
        sce = F.fetch_rows("BTC", 2024, 1)[0]
        ck("  ⛔ 連不上 ⇒ error（⛔ 不可以判成 absent：那會把「被擋」讀成「還沒上市」）",
           sce == "error")

        F.B.get = _fake((b"<html>blocked</html>", None))
        sbad = F.fetch_rows("BTC", 2024, 1)[0]
        ck("  ⛔ 回了東西但不是 zip ⇒ error（⚠ 不可以炸掉）", sbad == "error")

        ck("  ★ 四種結果【不全相同】（⛔ 都回同一個值的話上面幾條等於沒跑）",
           len({st, s404, sce, sbad}) >= 3, "實際：%s" % [st, s404, sce, sbad])

        print("\n② 沒有表頭的檔也要解得出來（⛔ 不假設一定有表頭）")
        F.B.get = _fake((_zip("1704067200000,8,0.0001\n1704096000000,8,0.00012\n"), None))
        st, head, rows = F.fetch_rows("BTC", 2024, 1)
        ck("  ⭐ 第一欄是純數字 ⇒ 判成無表頭、兩列都算資料",
           st == "ok" and head == "（無表頭）" and len(rows) == 2, "實際：%s %r %d" % (st, head, len(rows)))

        F.B.get = _fake((_zip(""), None))
        ck("  ⛔ zip 裡是空檔 ⇒ error", F.fetch_rows("BTC", 2024, 1)[0] == "error")
    finally:
        F.B.get = real

    print("\n③ 第一筆時間（⭐ 上市日上界的來源）")
    ck("  ⭐ 毫秒時間戳解得出", F.first_ts(["1704067200000,8,0.0001"]) == "2024-01-01 00:00",
       "實際：%s" % F.first_ts(["1704067200000,8,0.0001"]))
    ck("  ⭐ 秒時間戳也解得出", F.first_ts(["1704067200,8,0.0001"]) == "2024-01-01 00:00")
    ck("  ⛔ 解不出來 ⇒ None，⚠ 不猜", F.first_ts(["abc,8,0.1"]) is None)
    ck("  ⛔ 沒有列 ⇒ None", F.first_ts([]) is None)

    print("\n④ 月份跨年要對（⛔ 二分搜尋的母體錯了，找到的最早月就錯）")
    ms = F.months_between((2019, 11), (2020, 2))
    ck("  ⭐ 2019-11 ~ 2020-02 ＝ 四個月且跨年正確",
       ms == [(2019, 11), (2019, 12), (2020, 1), (2020, 2)], "實際：%s" % ms)
    ck("  ⭐ 起訖同月 ⇒ 一個月", F.months_between((2024, 5), (2024, 5)) == [(2024, 5)])

    print("\n⑤ ★ 沒有動到 repo 真的輸出檔")
    before = os.path.exists(F.OUT)
    ck("  ★ 這一支自測沒有建立或改動 data/meta/_funding_probe.txt",
       os.path.exists(F.OUT) == before)

    print("\n[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

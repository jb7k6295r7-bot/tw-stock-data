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

    print("")
    print("⑥ ⭐⭐ 左截 vs 真（⛔ 把封存下限讀成上市日，就是本支要擋的那件）")
    FLOOR = (2020, 1)
    ck("  ⛔ 下限月 ＋ 第一筆是該月第一瞬 ⇒ 左截",
       F.censor_verdict((2020, 1), FLOOR, "2020-01-01 00:00") == "左截")
    # ★ 反向樣本：跟上一格【只差第一筆在月中】⇒ 必須翻成「真」
    #   ⛔ 少了這一格，一條「下限月一律左截」的爛判準也會全綠
    ck("  ★ 下限月 ＋ 第一筆在【月中】 ⇒ 真（⛔ 不可以因為在下限月就判左截）",
       F.censor_verdict((2020, 1), FLOOR, "2020-01-06 08:00") == "真")
    ck("  ⭐ 最早月晚於下限月 ⇒ 真（前一月確實有封存、只是這一幣沒有）",
       F.censor_verdict((2020, 2), FLOOR, "2020-02-10 08:00") == "真")
    ck("  ⛔ 沒有第一筆 ⇒ 不明，⚠ 不猜",
       F.censor_verdict((2020, 1), FLOOR, None) == "不明")
    vs = set([F.censor_verdict((2020, 1), FLOOR, "2020-01-01 00:00"),
              F.censor_verdict((2020, 1), FLOOR, "2020-01-06 08:00"),
              F.censor_verdict((2020, 1), FLOOR, None)])
    ck("  ★ 三種結果【不全相同】（⛔ 都一樣的話上面幾格等於沒跑）", len(vs) == 3,
       "實際：%s" % vs)

    # ⭐⭐ 整支最關鍵的一格：month_start_str 與 first_ts 的【格式必須是同一種】
    #   ⛔ 格式一歪，字串永遠不相等 ⇒ 左截【永遠不會觸發】，而報告看起來完全正常
    #   ⚠ 這正是本庫付過代價的形狀：一條永遠回同一個值的判準，報告上看不出來
    _ms = "1577836800000,8,0.0001"     # 2020-01-01 00:00:00 UTC
    ck("  ★★ first_ts 與 month_start_str 對【同一瞬】給出同一個字串",
       F.first_ts([_ms]) == F.month_start_str((2020, 1)),
       "first_ts=%r month_start_str=%r" % (F.first_ts([_ms]),
                                           F.month_start_str((2020, 1))))

    print("")
    print("⑦ interval 逐列統計（⛔ 寫死 8 會讓成本少算一半）")
    ck("  ⭐ 單一值", F.intervals(["1,8,0.1", "2,8,0.1"]) == {"8": 2})
    ck("  ⭐ 混合值要分開數", F.intervals(["1,8,0.1", "2,4,0.1"]) == {"8": 1, "4": 1})
    ck("  ⛔ 缺欄位歸到 '?'，⚠ 不丟掉", F.intervals(["1", "2,,0.1"]) == {"?": 2},
       "實際：%s" % F.intervals(["1", "2,,0.1"]))

    print("")
    print("⑧ 完整性不變式（⭐ 期望值自己算，⛔ 不寫死 90／93）")
    ck("  ⭐ 2 月是閏月 29 天", F.days_in_month((2020, 2)) == 29)
    ck("  ⭐ 平年 2 月 28 天", F.days_in_month((2021, 2)) == 28)
    ck("  ⭐ 12 月跨年要算對 31 天", F.days_in_month((2020, 12)) == 31)
    full = ["%d,8,0.0001" % i for i in range(30 * 3)]
    ck("  ⭐ 30 天 × 每 8 小時 ＝ 90 列 ⇒ 吻合",
       F.completeness(full, (2020, 6))[0] is True)
    # ★ 反向樣本：少一列就必須紅（⛔ 否則這條不變式等於沒有）
    ck("  ★ 少一列 ⇒ 不吻合（⛔ 只看「有下載到 zip」看不出缺口）",
       F.completeness(full[:-1], (2020, 6))[0] is False)
    ck("  ⚠ interval 不是單一值 ⇒ 不套這條（回 None，⛔ 不謊報吻合）",
       F.completeness(["1,8,0.1", "2,4,0.1"], (2020, 6))[0] is None)
    # ★ 31 天的月期望值是 93 ⇒ ⛔ 擋掉「把期望值寫死成 90」那種實作
    #   ⚠ 只驗 30 天的月，寫死 90 的爛實作也會全綠
    full31 = ["%d,8,0.0001" % i for i in range(31 * 3)]
    ck("  ★ 31 天 × 每 8 小時 ＝ 93 列 ⇒ 吻合（⛔ 期望值不可寫死 90）",
       F.completeness(full31, (2020, 7))[0] is True,
       "實際：%s" % (F.completeness(full31, (2020, 7)),))
    ck("  ★ 31 天的月只有 90 列 ⇒ 不吻合",
       F.completeness(full31[:90], (2020, 7))[0] is False)

    print("")
    print("⑨ ★★ 常設反向樣本本身要有效（⛔ 樣本被改成單一值 ⇒ 規則就變空的）")
    _sym, _ym, _exp = F.MIXED_IV_SAMPLE
    ck("  ★ 樣本的期望值【本身】是混合的（≥ 2 種 interval）",
       len(_exp) >= 2, "實際：%s" % _exp)
    ck("  ★ 而它不是全部同一個值湊出來的（⛔ {'8': n} 那種等於沒有樣本）",
       set(_exp) != {"8"}, "實際：%s" % _exp)
    ck("  ⭐ 樣本的月份在母體的範圍內（⛔ 指到一個沒有的月＝永遠取不到）",
       _ym >= F.EARLIEST and _sym in F.COINS, "%s %s" % (_sym, _ym))
    # ★ 而「混合」這件事要由 intervals() 真的判得出來（⛔ 不是常數比對）
    # ⚠ ⛔ 不可以叫 _fake：模組層已經有一支 _fake()（假的 B.get），
    #   在 main 裡指派同名變數會把它整支遮掉 ⇒ 上面第①節當場 UnboundLocalError
    _synth = (["1,8,0.1"] * _exp.get("8", 0) + ["2,4,0.1"] * _exp.get("4", 0)
              + ["3,2,0.1"] * _exp.get("2", 0))
    ck("  ★★ 用樣本的筆數合成的列，intervals() 算回同一個統計",
       F.intervals(_synth) == _exp, "實際：%s" % F.intervals(_synth))

    print("\n⑤ ★ 沒有動到 repo 真的輸出檔")
    before = os.path.exists(F.OUT)
    ck("  ★ 這一支自測沒有建立或改動 data/meta/_funding_probe.txt",
       os.path.exists(F.OUT) == before)

    print("\n[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

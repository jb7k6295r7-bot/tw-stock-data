#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_otc_reduce_history.py — 驗 `revivt` 的解析與**兩道**守門。不連外、不寫 repo。

⛔ 五條分支：
  ① 正常：民國日期、逗號、factor＝參考價÷最後收盤價
  ② `stat:參數錯誤`（這一支的**大聲失敗**）⇒ 擋下來
  ③ 只回最近的資料 ⇒ 擋下來（⚠ 這一支不會靜默，但仍然做這道，
     因為「對方哪天改行為」不在我的控制範圍內）
  ④ 0 列 ⇒ 當失敗，⛔ 不是「這十一年沒有減資」
  ⑤ 欄位對不上 ⇒ 講得出缺哪一個
"""
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import datetime as _dt0
import otc_reduce_history as R
import half_run
import runlog

# ⚠ 用「今天」而不是寫死日期：這一組要測的正是「今天算、明天不算」的邊界，
#   ⛔ 寫死的話這支測試明天就開始測別的東西了。
_TODAY = _dt0.datetime.now(_dt0.timezone(_dt0.timedelta(hours=8))).strftime('%Y-%m-%d')
# ⭐ 假的「我方資料最後一天」：⛔ 固定寫死，不要跟著 repo 現況跑
#   （跟著跑的話這一節會在週末與盤中給出不同答案，而那正是要測的東西）
_LAST = '2026-09-11'

TPE = timezone(timedelta(hours=8))
OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


F = ["恢復買賣日期", "股票代號", "名稱", "最後交易日之收盤價格",
     "減資恢復買賣開始日參考價格", "減資原因"]


def pack(rows, fields=None, stat="ok"):
    return {"stat": stat,
            "tables": [{"title": "減資恢復買賣", "fields": fields or F, "data": rows}]}


def main():
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "meta", "otc_reduce_history.csv")
    before = os.path.exists(real)

    rows, note = R.parse(pack([
        ["109/06/22", "5227", "立凱-KY", "10.00", "18.58", "彌補虧損"],
        ["106/09/01", "6219", "富旺", "10.10", "10.11", "現金減資"],
    ]), "2013-01-01")
    ck("① 兩列都解得出來", len(rows) == 2, note)
    ck("① 民國 109/06/22 → 2020-06-22",
       rows and rows[0][0] == "2017-09-01" or any(r[0] == "2020-06-22" for r in rows),
       str([r[0] for r in rows]))
    f = {r[1]: r[5] for r in rows}
    ck("① factor ＝ 參考價 ÷ 最後收盤價（5227 → 1.85800000）",
       f.get("5227") == "1.85800000", str(f))
    ck("① 6219 → 1.00099010（情報分析線實測的同一個值）",
       f.get("6219") == "1.00099010", str(f))

    r2, n2 = R.parse(pack([], stat="參數錯誤"), "2013-01-01")
    ck("② `stat:參數錯誤` ⇒ 擋下來，而且照抄它說的",
       not r2 and "參數錯誤" in n2, n2)

    t0 = datetime.now(TPE).strftime("%Y/%m/%d")
    r3, n3 = R.parse(pack([[t0, "5227", "立凱", "10", "18", "彌補虧損"]]),
                     "2013-01-01")
    ck("③ 只回最近的資料 ⇒ 擋下來（⚠ 這一支不會靜默，但仍然做這道）",
       not r3 and "參數多半沒生效" in n3, n3)

    r4, n4 = R.parse(pack([]), "2013-01-01")
    ck("④ 0 列 ⇒ 當失敗，⛔ 不是「這十一年沒有減資」",
       not r4 and "不是" in n4, n4)

    r5, n5 = R.parse(pack([["109/06/22", "5227", "立凱"]],
                          fields=["恢復買賣日期", "股票代號", "名稱"]),
                     "2013-01-01")
    ck("⑤ 欄位對不上 ⇒ 講得出缺哪一個",
       not r5 and "最後收盤" in n5 and "參考價" in n5, n5)

    ck("★ 沒有動到 repo 真的判準檔", os.path.exists(real) == before)
    print("⑥ ⭐ 缺口分堆：涵蓋期內／外是兩件事，⛔ 不可以混在一起數")
    M = [
        # 涵蓋期外（我方日檔還沒開始）⇒ 歷史欠帳，不設 check
        ["2013-01-16", "6248", "x", "1", "2", "1.00000000", "彌補虧損", "a"],
        ["2014-05-02", "3252", "y", "1", "2", "1.00000000", "現金減資", "a"],
        # 涵蓋期內、已歸因（官方自己重複的列）
        ["2020-09-25", "6109", "亞元", "10.50", "10.63", "1.01238095", "現金減資", "a"],
        # ⭐ 涵蓋期內、未歸因 ⇒ **現在就錯的還原因子**
        [_LAST, "6461", "益得", "16.65", "26.92", "1.61681682", "彌補虧損", "a"],
    ]
    inside, named, live = R.classify_gaps(M, "2015-01-05", upper=_LAST)
    ck("  涵蓋期外的兩筆不算進來", len(inside) == 2, str([r[0] for r in inside]))
    ck("  6109 那筆被歸因掉（官方自己重複的列）",
       len(named) == 1 and named[0][1] == "6109", str(named))
    ck("  ⭐ 6461 益得留在**未歸因** ⇒ 這一條要會紅",
       len(live) == 1 and live[0][1] == "6461", str(live))

    print("⑦ ⭐ 恢復買賣日在**未來**的預告列一律排除（⛔ 否則每天假紅）")
    import datetime as _dt
    _tw = _dt.timezone(_dt.timedelta(hours=8))
    _tomorrow = (_dt.datetime.now(_tw) + _dt.timedelta(days=9)).strftime("%Y-%m-%d")
    _M2 = M + [[_tomorrow, "8277", "商丞", "10.00", "23.20", "2.32000000",
                "彌補虧損", "a"]]
    _in, _named, _live = R.classify_gaps(_M2, "2015-01-05", upper=_LAST)
    ck("  未來那一筆不進「涵蓋期內」", len(_in) == 2, str([r[0] for r in _in]))
    ck("  ⭐ 也不進「未歸因」（⛔ 它每天都會出現，會把這條斷言弄成每天紅）",
       all(r[0] != _tomorrow for r in _live), str(_live))
    ck("  ⚠ 而**資料最後一天**那一筆仍然算（邊界是 <= upper，不是 < upper）",
       any(r[1] == "6461" for r in _live), str(_live))

    print("⑦之二 ⛔⛔ 上界是**我方資料最後一天**，⛔ 不是「今天」（2026-09-14 踩到）")
    # ⚠ 實際情形：6129 普誠的恢復買賣日是 2026-09-14（週一），
    #   而我方日檔最後一天是 09-11（週五，週末沒有盤）。
    #   ⇒ 拿「今天」當上界 ⇒ 它被判成**涵蓋期內的未歸因缺口**
    #   ⇒ runlog 寫「那一檔的還原序列在這一天是假報酬」，⛔ 而那一天還沒收盤。
    # ⭐ 同一句話 `otc_exright_check` 2026-09-11 就修過了——⛔ 這一支沒跟上。
    _MID = [["2026-09-14", "6129", "普誠", "13.10", "14.76", "1.12671756",
             "彌補虧損", "a"]]
    _i1, _, _l1 = R.classify_gaps(_MID, "2015-01-05", upper="2026-09-11")
    ck("  ⭐⭐ 事件日晚於資料最後一天（但**不晚於今天**）⇒ 不算缺口",
       not _i1 and not _l1, f"inside={_i1}｜live={_l1}")
    _i2, _, _l2 = R.classify_gaps(_MID, "2015-01-05", upper="2026-09-14")
    ck("  ⛔ 反向：上界改回「今天」⇒ 它就變成未歸因缺口"
       "　⇒ 這一節不是憑空擔心",
       len(_i2) == 1 and len(_l2) == 1, f"inside={_i2}｜live={_l2}")
    # ⭐ 有預設值的參數，一定要有一條**不傳它**的斷言（第七點③）
    import adjust as _adj
    ck("  ⭐ 不傳 `upper` ⇒ 走預設，而預設就是 `adjust.last_data_day()`"
       "（⛔ 這是 Actions 上唯一會走的那條）",
       R.classify_gaps(_MID, "2015-01-05")
       == R.classify_gaps(_MID, "2015-01-05", upper=_adj.last_data_day()[0]),
       str(_adj.last_data_day()))
    # ⛔⛔ 而「測了判準、沒測呼叫點」在本專案已經第七次 ⇒ 掃原始碼
    _src_r = io.open(R.__file__, encoding="utf-8").read()
    ck("  ⭐⭐ `main()` 真的把資料最後一天傳進去（⛔ 只測純函式的話，"
       "呼叫點改回 today 也不會紅）",
       "classify_gaps(miss, cover, upper=upper)" in _src_r
       and "_adjust.last_data_day()" in _src_r,
       "⛔ 呼叫點沒有傳 upper／沒有用 adjust.last_data_day()")
    ck("  ⭐ 而日檔列表也不再自己算一份（⛔ 那是四點五那一族）",
       "os.listdir(dd)" not in _src_r and "_adjust.trading_days()" in _src_r)

    print("⑧ ⛔ 反向：三種會讓這條判準失效的情形")
    ck("  ★ 具名排除清單**是空的**時，6109 也要留在未歸因"
       "（證明 ⑥ 不是靠寫死通過的）",
       len(R.classify_gaps(M, "2015-01-05", known={}, upper=_LAST)[2]) == 2,
       str(R.classify_gaps(M, "2015-01-05", known={}, upper=_LAST)[2]))
    ck("  ★ 涵蓋起點算不出來（沒有日檔）⇒ **一律當涵蓋期外**，"
       "⛔ 不可以反過來全部當成期內（那會憑空生一堆假警報）",
       R.classify_gaps(M, "", upper=_LAST) == ([], [], []),
       str(R.classify_gaps(M, "", upper=_LAST)))
    ck("  ★ 涵蓋起點往前挪到 2013 ⇒ 四筆全部變成期內"
       "（證明它真的在用那個日期，不是寫死 2015）",
       len(R.classify_gaps(M, "2013-01-01", upper=_LAST)[0]) == 4,
       str(len(R.classify_gaps(M, "2013-01-01", upper=_LAST)[0])))
    ck("  ⚠ 邊界：**等於**涵蓋起點那一天算期內（不是 > 而是 >=）",
       len(R.classify_gaps([M[3]], _LAST, upper=_LAST)[0]) == 1)

    print("⑨ ⭐⭐ 第 11 欄：官方自己給的換股比例（2026-09-10 起）")
    # ⚠ 假回應照真回應的形狀做：那一欄是 **HTML**，兩行、帶單位、帶全形空白。
    D0 = ("每壹仟股換發新股票:&nbsp;618.578 股<br/>"
          "每股退還股款:&nbsp;0.00000000 元/股")
    F11 = F[:-1] + ["漲停價格", "跌停價格", "開始交易基準價", "除權參考價",
                    "減資原因", "詳細資料"]
    # ⚠ 日期用 2020：這一支有「只回最近的資料就擋下來」那一道，
    #   ⛔ 拿今天當測試日期會被那一道擋掉，測不到第 11 欄。
    row = ["109/06/22", "6461", "益得", "16.65", "26.92",
           "18.20", "16.20", "26.92", "0.00", "彌補虧損", D0]
    r9, n9 = R.parse({"stat": "ok", "tables": [{"fields": F11, "data": [row]}]},
                     "2013-01-01")
    ck("  解得出來，而且列長 = HEADER − 1（asof 由 main 補）",
       len(r9) == 1 and len(r9[0]) == len(R.HEADER) - 1,
       f"{len(r9[0]) if r9 else 0} vs {len(R.HEADER) - 1}")
    a = r9[0] if r9 else []
    ck("  ⭐ 換股比例 618.578 讀得出來", a and a[7] == "618.578000", str(a[7:] if a else a))
    ck("  ⛔ 退還股款是 **0**，而且與「沒讀到」分得開（存 '0.00000000' 不是空字串）",
       a and a[8] == "0.00000000", str(a[8] if a else None))
    ck("  ⭐ 官方比例回推的 factor 與參考價回推的**幾乎一樣**（差 < 1e-3）",
       a and abs(float(a[9]) - float(a[5])) < 1e-3, f"{a[9]} vs {a[5]}" if a else "")
    ck("  ⚠ 而它們**不完全相等**（官方參考價印到分為止 ⇒ 回推帶殘差）",
       a and a[9] != a[5], f"{a[9]} vs {a[5]}" if a else "")
    ck("  說明講得出第 11 欄的成績", "第 11 欄換股比例 1/1" in n9, n9)

    print("⑩ ⛔ 反向：第 11 欄的每一種讀錯法")
    ck("  認不出來 ⇒ 回 (None, None)，⛔ **不是 (0, 0)**"
       "（0 是真的會發生的值，用 0 當「沒讀到」會讓恆等式看起來過了）",
       R.parse_detail("這一欄改版了") == (None, None),
       str(R.parse_detail("這一欄改版了")))
    ck("  ⚠ 全形冒號＋沒有「壹」＋千分位，照樣讀得出來",
       R.parse_detail("每仟股換發新股票：1,234.5 股　每股退還股款：2.50 元/股")
       == (1234.5, 2.5),
       str(R.parse_detail("每仟股換發新股票：1,234.5 股　每股退還股款：2.50 元/股")))
    ck("  ⛔ 兩個欄位不可以互相污染（只有退還股款那一行時，比例要是 None）",
       R.parse_detail("每股退還股款: 3.00 元/股") == (None, 3.0),
       str(R.parse_detail("每股退還股款: 3.00 元/股")))
    ck("  ⭐ 恆等式算得對：16.65 ÷ 0.618578 ≒ 26.92（情報分析線逐筆驗過的那一筆）",
       abs(R.official_ref(16.65, 618.578, 0.0) - 26.92) < 0.005,
       str(R.official_ref(16.65, 618.578, 0.0)))
    ck("  ⚠ 退還股款要**先扣掉**再除（不扣的話這一筆會差 0.8 以上）",
       abs(R.official_ref(16.65, 618.578, 0.5)
           - R.official_ref(16.65, 618.578, 0.0)) > 0.8,
       str(R.official_ref(16.65, 618.578, 0.5)))
    ck("  ⛔ 比例是 0／None ⇒ 回 None，不是 ZeroDivisionError",
       R.official_ref(16.65, 0, 0) is None and R.official_ref(16.65, None, 0) is None)
    bad_row = row[:-1] + ["<td>官方改版了</td>"]
    rb, nb = R.parse({"stat": "ok", "tables": [{"fields": F11, "data": [bad_row]}]},
                     "2013-01-01")
    ck("  ⭐ 第 11 欄壞掉時**那一列還是要收**（它是加值，不是必要欄）",
       len(rb) == 1 and rb[0][7] == "", str(rb))
    ck("  ⛔ 而說明要附**原文**（283 列全認不出那次的教訓：只給數字＝再打對方一趟）",
       "官方改版了" in nb, nb)
    ck("  ⚠ 沒有第 11 欄的舊形狀照樣解得出來（⛔ 不可以整批停擺）",
       len(R.parse(pack([["109/06/22", "5227", "立凱-KY", "10.00", "18.58",
                          "彌補虧損"]]), "2013-01-01")[0]) == 1)

    print("⑪ ⭐⭐ 捨入的**理論上界**（K線線 20:20 裁的新斷言）")
    # 官方參考價印到分 ⇒ 兩種 factor 的差 ≤ 0.005 ÷ 前收。
    # ⛔ 超過的那些**不是捨入，是解析錯了**（比例讀錯一位／退款漏掉／欄位錯位）。
    def row(lc, f, fo, code="X"):
        return ["2020-01-01", code, "n", str(lc), "1", f"{f:.8f}", "彌補虧損",
                "618.578000", "0.00000000", f"{fo:.8f}"]
    real = 16.65 * 1000 / 618.578 / 16.65          # ＝ 1000/618.578
    ck("  ⭐ 益得那一筆（官方印 26.92 vs 真值 26.9166）在界內",
       not R.over_bound([row(16.65, 26.92 / 16.65, real)]),
       str(R.over_bound([row(16.65, 26.92 / 16.65, real)])))
    ck("  ⛔ 比例讀錯一位（1.5 vs 1.6168）⇒ 超界，被抓出來",
       len(R.over_bound([row(16.65, 1.61681682, 1.5)])) == 1)
    _o = R.over_bound([row(16.65, 1.61681682, 1.5)])
    ck("  抓出來的內容含**差**與**該筆自己的上界**",
       bool(_o) and _o[0][3] == round(0.005 / 16.65 + R.FACTOR_DP, 8), str(_o))

    # ⭐⭐ 上界的**第二項**：兩個 factor 欄各只存 8 位 ⇒ 相減誤差最多 1e-8
    #   ⛔ 2026-09-11 之前漏了這一項 ⇒ 四筆**常駐紅燈**，超出量全是 2~4e-9。
    #   ⚠ 這一節要同時證明兩件事，少一件就變成「放寬門檻」而不是「修正上界」：
    #     ① 超出 ①項 但落在 1e-8 內  ⇒ 界內（原本假紅的那些）
    #     ② 超出 1e-8 一個量級        ⇒ **照樣超界**（⛔ 沒有被放水）
    _lc = 40.5                                   # 8433 那一筆的最後收盤
    _b1 = 0.005 / _lc                            # 第一項（≈1.2346e-4）
    ck("  ⭐⭐ 超出第①項 **3e-9**（8 位小數的捨入做得到）⇒ **界內**"
       "（⛔ 這就是原本那四筆常駐紅）",
       not R.over_bound([row(_lc, 1.0 + _b1 + 3e-9, 1.0, "近界")]),
       str(R.over_bound([row(_lc, 1.0 + _b1 + 3e-9, 1.0, "近界")])))
    ck("     …而超出 **2e-8**（比 8 位小數做得到的還大）⇒ **照樣超界**"
       "（⚠ 正例：⛔ 證明這不是放水）",
       len(R.over_bound([row(_lc, 1.0 + _b1 + 2e-8, 1.0, "真超")])) == 1,
       str(R.over_bound([row(_lc, 1.0 + _b1 + 2e-8, 1.0, "真超")])))
    print("⑪之二 ⭐⭐ 官方恆等式：`x.xx5` 那幾筆不可以常駐紅（2026-09-11）")
    # ⚠ 8433 2013-10-31 實例：我方算出 48.125、官方印 48.13
    #   ⇒ abs(48.125-48.13) = 0.005000000000002558，比容差 0.005 大 **2.5e-15**
    #   ⛔ 而那是**二進位表示誤差**，不是資料錯 ⇒ 五筆天天紅、永遠修不好。
    def _ident_row(lc, ratio, cash, rp):
        # 欄位照 write 出去的順序：r[1]=代號 r[0]=日期 r[3]=last_close
        # r[4]=ref_price r[7]=每壹仟股換發新股 r[8]=每股退還股款
        return ["2013-10-31", "8433", "", str(lc), str(rp), "", "",
                str(ratio), str(cash), "", ""]
    _ok, _bad = R.identity_check([_ident_row(48.125, 1000, 0, 48.13)])
    ck("  ⭐⭐ 差**恰好** 0.005（官方 x.xx5 進位）⇒ 過"
       "（⛔ 沒有這一項，五筆常駐紅）", not _bad and len(_ok) == 1,
       f"ok={_ok}｜bad={_bad}")
    _ok2, _bad2 = R.identity_check([_ident_row(48.10, 1000, 0, 48.13)])
    ck("  ⚠ 正例：真的差 0.03 ⇒ **照樣不符**（⛔ 證明 1e-9 沒有藏住解析錯誤）",
       len(_bad2) == 1 and not _ok2, f"ok={_ok2}｜bad={_bad2}")

    # ⭐ 這一節的重點：上界**跟前收成反比**，⛔ 不是一個固定常數
    gap = 0.0002
    lo = row(10.0, 1.0 + gap, 1.0, "低價")       # 上界 5e-4 ⇒ 界內
    hi = row(100.0, 1.0 + gap, 1.0, "高價")      # 上界 5e-5 ⇒ 超界
    ck("  ⭐⭐ **同樣的差** 0.0002：10 元的股票算界內…",
       not R.over_bound([lo]), str(R.over_bound([lo])))
    ck("     …而 100 元的股票**超界**（⇒ 上界跟前收成反比，"
       "⛔ 用固定常數會對低價股太鬆、對高價股太嚴）",
       len(R.over_bound([hi])) == 1, str(R.over_bound([hi])))
    ck("  ⚠ 缺任一欄（沒有官方比例／沒有前收）⇒ 跳過不誤判",
       not R.over_bound([row(0, 1.0, 2.0)])
       and not R.over_bound([["2020-01-01", "Z", "n", "10", "1", "", "r",
                              "", "", ""]]))
    ck("  ⛔ 欄位是壞字串時不炸",
       R.over_bound([["2020-01-01", "Z", "n", "10", "1", "abc", "r",
                      "1", "0", "def"]]) == [])

    # ═══════════════════════════════════════════════════════════
    # ⑫ ⭐⭐ **兩半場**（市場情報分析線 0020 §三）：先抓 → 再補 → 才掃
    #
    # ⛔ 這一節**真的跑一次 `main()`**，⚠ 不是讀原始碼字串（七點第八個）。
    #   四個旋鈕（OUT／LOW／runlog.PATH／_post）由 `half_run` 一次導走，
    #   ⛔ 兩支姊妹自測共用**同一份**——抄兩份的話下一個人只會修一份（四點五）。
    # ═══════════════════════════════════════════════════════════
    print("⑫ ⭐⭐ --no-scan／--scan-only：兩半場真的跑一次")
    # ⛔ 不可以再用 main() 開頭那個 `real`／`before`——⚠ 中間被別的區段改掉了
    #   （`real` 在這裡已經是一個 float）⇒ ⭐ 從模組屬性自己取一次。
    # ⛔ 不可以先存成 `R.LOW = R.LOW` 再 `io.open(R.LOW, …)`：
    #   `selftest_lowwater` ⑨ 的判準是「**裸的名字**以 LOW 結尾被拿去開檔」
    #   ⇒ 那樣寫會被判成「第九份實作」（實測當場紅）。
    #   ⭐ 而那道判準是對的：`io.open(R.LOW, …)` 是 Attribute ＝「核**別的模組**
    #     的路徑寫了什麼」，⛔ 裸名才是「這個檔自己在讀寫低水位檔」。
    #   ⚠ `run_half` 在 `finally` 把旋鈕還原了 ⇒ 這裡讀到的一律是 repo 真的那條路。
    _b_out = (io.open(R.OUT, "rb").read()
              if os.path.exists(R.OUT) else None)
    _b_low = io.open(R.LOW, "rb").read() if os.path.exists(R.LOW) else None
    _b_run = (io.open(runlog.PATH, "rb").read()
              if os.path.exists(runlog.PATH) else None)
    _payload = json.dumps(pack([
        ["109/06/22", "5227", "立凱-KY", "10.00", "18.58", "彌補虧損"],
    ])).encode()

    with tempfile.TemporaryDirectory() as td:
        try:
            half_run.run_half(R, ["--no-scan", "--scan-only"], td,
                              payload=_payload)
            _both = "⛔ 兩個一起給居然跑完了"
        except SystemExit as ex:                                 # noqa: PERF203
            _both = str(ex)
        ck("  ⭐ `--no-scan` 與 `--scan-only` 同時給 ⇒ **SystemExit**"
           "（⛔ 靜靜擇一是這一族最貴的壞法）",
           "不可以同時給" in _both, _both)

    # ── ① 只抓不掃 ────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        rc1, tx1 = half_run.run_half(R, ["--no-scan"], td, payload=_payload)
        _out1 = os.path.join(td, "out.csv")
        ck("  ⭐ `--no-scan` 把判準檔寫出來了",
           os.path.exists(_out1)
           and len(io.open(_out1, encoding="utf-8").read().splitlines()) == 2,
           f"rc={rc1}")
        ck("  ⭐⭐ 而**掃描那一半沒跑**"
           "（⛔ 跑了的話它掃的是還沒補之前的 `data/adj/` ⇒ 一道天天紅的閘門）",
           "官方有、我方 data/adj 沒有" not in tx1, tx1[:200])
        ck("  ⭐ 區塊名是 `otc_reduce_history:fetch`"
           "（⛔ 同名會蓋掉掃描那一半）",
           "## otc_reduce_history:fetch" in tx1, tx1[:120])

    # ── ② 只掃不抓 ────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as td:
        io.open(os.path.join(td, "out.csv"), "w", encoding="utf-8").write(
            ",".join(R.HEADER) + "\n"
            "2020-06-22,5227,立凱-KY,10.00,18.58,0.5382,彌補虧損,,,,2026-09-16\n")
        # ⭐ `payload=None` ⇒ `_post` 換成**會炸的**那一個
        #   ⇒ 這條斷言的終點是「它沒有炸」＝ **它沒有連外**（⛔ 不是讀原始碼）
        # ⭐ `run_half` 自己接住例外並回 `rc=None`（⛔ 不讓它逃出去中斷整支）。
        rc2, tx2 = half_run.run_half(R, ["--scan-only"], td)
        ck("  ⭐⭐ `--scan-only` **一發都沒有打出去**"
           "（⛔ `_post` 被換成會丟例外的那一個）",
           rc2 is not None and "不可以連外" not in tx2, tx2[:160])
        ck("  ⭐ 而它**讀回**了判準檔並且掃了",
           "官方有、我方 data/adj 沒有" in tx2 and "1 筆" in tx2, tx2[:300])
        ck("  ⭐ 掃描那一半**留原名**（⚠ 別的線與 305 個歷史版本跟的是它）",
           "## otc_reduce_history　" in tx2
           and "otc_reduce_history:fetch" not in tx2, tx2[:120])

        # ⭐⭐ 這一條才是「`LOW` 真的被導走」的**終點**：
        #   ⛔ 「repo 那一份沒變」證明不了它——現場水位已經是 **0**，
        #   而 `lowwater.DOWN` 只在**更低**時才寫 ⇒ 沒導走它也不會變
        #   ⇒ ⚠ 那條斷言的壽命綁在現場水位上（七點第七個）。
        #   ⭐ 而「沙箱裡那一份**被寫出來了**」跟現場無關，每個 ref 都成立。
        ck("  ★ `LOW` 真的被導走（沙箱的 `low.txt` 有被寫出來）",
           os.path.exists(os.path.join(td, "low.txt")),
           os.listdir(td))

    # ── ③ 判準檔不在 ⇒ **大聲失敗**，⛔ 不是靜靜 0 筆（四點六） ──
    with tempfile.TemporaryDirectory() as td:
        rc3, tx3 = half_run.run_half(R, ["--scan-only"], td)
        ck("  ⭐⭐ 判準檔不在 ⇒ **✗**，⛔ 不是當成 0 筆往下跑",
           "**✗**" in tx3 and "要讀的判準檔在不在" in tx3, tx3[:300])

    # ── ④ ⭐ 預設那條路（⛔ 一個旗標都不傳）——七點第三個 ──────
    with tempfile.TemporaryDirectory() as td:
        rc4, tx4 = half_run.run_half(R, [], td, payload=_payload)
        ck("  ⭐⭐ **不傳旗標**時兩半場都跑"
           "（⚠ 那是 `feeds.yml` 走的那條路，⛔ 沒有這條斷言它沒有人走過）",
           "判準檔" in tx4 and "官方有、我方 data/adj 沒有" in tx4
           and "## otc_reduce_history　" in tx4, tx4[:300])

    ck("  ★ 沒有動到 repo 真的 `otc_reduce_history.csv`",
       (io.open(R.OUT, "rb").read()
        if os.path.exists(R.OUT) else None) == _b_out)
    ck("  ★ 沒有動到 repo 真的 `_otc_reduce_gap_low.txt`"
       "（⚠ 寫小一次那道閘門永遠綠。⛔ 而這一條**單獨不夠**——"
       "現場水位已是 0 ⇒ 沒導走它也不會變，⇒ 要跟上面那條一起看）",
       (io.open(R.LOW, "rb").read()
        if os.path.exists(R.LOW) else None) == _b_low)
    ck("  ★ 沒有動到 repo 真的 `_last_run.md`",
       (io.open(runlog.PATH, "rb").read()
        if os.path.exists(runlog.PATH) else None) == _b_run)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`feeds.month_is_open` / `months_to_ask` 的自測。**純函式，不連網、不碰 data/。**

## ⛔⛔ 這一支是為了一個「整趟綠燈」的漏抓生出來的（2026-09-11）

公告型的 feed（除權息／減資／面額變更／ETF 分割）逐月抓，
台帳 `_fetched.json` 記「這個月問過了」⇒ ⛔ 問過就**永遠不再問**。

    2026-09 月初問過一次 ⇒ 台帳記上
    ⇒ 09-10 才公告的那幾檔，這個月**再也不會被問到**
    ⇒ `data/universe/exright/2026-09-10.csv` 根本不存在
    ⇒ `adj_gap` 報 5906／4912／9802／2062／9906／6504 **未歸因**
    ⚠ 而 `feeds:exright` 那一趟是 **✓ 正常**：
      「這個區間的 1 個月台帳裡都問過了，本趟沒有要問的」

⭐ CLAUDE.md 第四點：**續跑判準要用資料自己，⛔ 不要另開台帳**
  ——台帳會跟資料不一致，⚠ 而不一致的方向是「看起來比實際好」。

## 要釘的四件

    ① 當月（今天所在的月）⇒ 台帳有也照樣重問
    ② 已經結束的月 ⇒ 台帳有就跳過（⛔ 否則每趟重打 141 個月）
    ③ 判準是**日曆上的月底**，⛔ 不是 `--end` 夾出來的那一天
    ④ 重問的月份要**被講出來**（⛔ 靜靜重問 ＝ 看不出這道在不在）
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feeds as F                                             # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def main():
    print("=" * 60)
    print("feeds 的逐月台帳判準（不連網）")
    print("=" * 60)

    T = "2026-09-11"          # 「今天」

    print("\n[1] month_is_open：判準是**日曆上的月底**")
    ck("⭐ 當月（2026-09，月底 09-30 ≥ 今天）⇒ 還沒結束",
       F.month_is_open("2026-09", T))
    ck("  上個月（2026-08）⇒ 已經結束", not F.month_is_open("2026-08", T))
    ck("  下個月（2026-10）⇒ 還沒結束", F.month_is_open("2026-10", T))
    ck("⛔ 二月要用真的天數（2024-02 有 29 天）：2024-02-29 當天算還沒結束",
       F.month_is_open("2024-02", "2024-02-29"))
    ck("  而 2024-03-01 那天它已經結束",
       not F.month_is_open("2024-02", "2024-03-01"))
    ck("⭐ 月底當天**算還沒結束**（⛔ 當天盤後還會有公告）",
       F.month_is_open("2026-09", "2026-09-30"))
    # ⛔⛔ 31 天的月份：⚠ 沒有這一條，「把月底寫死成 30」的錯**驗不出來**
    #   （2 月那兩條對 30 天與真天數都成立 ⇒ 突變 M4 第一輪沒紅）
    ck("⛔⛔ 31 天的月份：2026-08-31 當天，8 月**還沒結束**"
       "（⇒ 月底不可以寫死成 30）",
       F.month_is_open("2026-08", "2026-08-31"))
    ck("  而 2026-09-01 那天它結束了",
       not F.month_is_open("2026-08", "2026-09-01"))
    ck("  隔天就結束了", not F.month_is_open("2026-09", "2026-10-01"))

    print("\n[2] months_to_ask：台帳只對**已經結束的月份**有效")
    # ⚠ 照真的形狀做：`_months()` 回的迄日被 `--end` 夾過
    rng = [("2026-07-01", "2026-07-31"),
           ("2026-08-01", "2026-08-31"),
           ("2026-09-01", "2026-09-11")]        # ← 被 --end 夾成 09-11
    led = {"2026-07": "x", "2026-08": "x", "2026-09": "x"}

    todo, reask = F.months_to_ask(rng, led, force=False, today=T)
    ck("⭐⭐ 三個月台帳都有 ⇒ **只重問當月那一個**",
       [m[0][:7] for m in todo] == ["2026-09"], str(todo))
    ck("⭐ 而且要講得出是哪一個月（⛔ 靜靜重問 ＝ 看不出這道在不在）",
       reask == ["2026-09"], str(reask))
    ck("⛔⛔ 判準不是 `--end` 夾出來的 09-11："
       "若拿它比，09 會被當成『已經結束』⇒ 又回到漏抓",
       "2026-09" in [m[0][:7] for m in todo], str(todo))

    print("\n[3] ⛔ 反向：已經結束的月份**不可以**每趟重問（那是 141 發）")
    todo2, _ = F.months_to_ask(rng, led, force=False, today="2026-12-01")
    ck("  三個月都已結束、台帳都有 ⇒ 一個都不問",
       todo2 == [], str(todo2))

    print("\n[4] 台帳沒有的月份照樣要問（⛔ 不可以被新判準吃掉）")
    todo3, reask3 = F.months_to_ask(rng, {"2026-07": "x"}, today=T)
    ck("  08（沒問過、已結束）與 09（當月）都要問",
       [m[0][:7] for m in todo3] == ["2026-08", "2026-09"], str(todo3))
    # ⚠ 這個台帳裡連 09 都沒有 ⇒ 兩個都是**第一次問**，reask 應該是空的。
    #   ⛔ 「重問」的定義是「台帳有、但因為當月而照樣問」，不是「這趟有問」。
    ck("  ⛔ 而 reask 是空的：兩個都是第一次問，⛔ 不算重問",
       reask3 == [], str(reask3))
    # ⭐ 而台帳裡**有** 09 時，它就要被算成重問（⇒ 上面那條不是靠放寬過的）
    _t5, _r5 = F.months_to_ask(rng, {"2026-07": "x", "2026-09": "x"}, today=T)
    ck("  ⭐ 反向：台帳裡有 09 ⇒ 它算重問（⛔ 證明 reask 不是永遠空的）",
       _r5 == ["2026-09"], str(_r5))

    print("\n[5] --force 一律全問，且不算重問")
    todo4, reask4 = F.months_to_ask(rng, led, force=True, today=T)
    ck("  三個月全問", len(todo4) == 3, str(todo4))
    ck("  reask 是空的（⛔ --force 不是『因為當月才重問』）", reask4 == [],
       str(reask4))

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

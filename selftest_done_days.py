#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_done_days.py — 釘住 `backfill.done_days()` **真的用現行欄位判**。

## ⛔ 為什麼要單獨一支：判準有測、**呼叫點沒測**

2026-09-10 的第十一份拷貝：`backfill.HEADER` 停在 16 欄、
`fetch.UNIVERSE_HEADER` 已經是 17 欄（09-10 加了 `last_price`）。

⚠ 而它**不會少寫任何一欄**——列是 `parse_*` 產的（早就 alias 到 fetch），
寫檔的 `write_day` 也是 fetch 那一份。⛔ 走岔的只有這一個**常數**，
而它唯一的用途就在這裡：

    want = ",".join(HEADER)
    head == want ⇒ 這一天算跑過了

⇒ 後果是**判準整個反過來**：

    17 欄的檔（09-10 之後寫的、正確的）⇒ 判成「舊版欄位」⇒ 重抓
    16 欄的檔（真正的舊格式）          ⇒ 判成「現行版本」⇒ **永遠跳過**

⛔ 它不會報錯、不會少資料，只會讓長工重跑一批不必跑的日子，
同時把真正該重跑的那些**一天都不跑**。

## ⭐ 這一支斷言的是**終點**，不是中間（CLAUDE.md 第四點二）

⛔ 不斷言「`HEADER` 是 17 欄」——那只是中間那一步（而且它換個寫法就躲掉了）。
⭐ 斷言的是「**寫檔那一支寫出來的表頭，會被這一支判成跑過了**」
——⚠ 表頭是拿 `fetch.write_universe_day` **實際寫一個檔**得到的，
⛔ 不是在測試裡自己拼一個字串（自己拼的那個和程式一起錯，會一起綠）。
"""
import io
import os
import shutil
import sys
import tempfile

import backfill as B
import fetch as F

_n_ok = _n_bad = 0


def ck(name, cond, detail=""):
    global _n_ok, _n_bad
    if cond:
        _n_ok += 1
        print(f"  ok   {name}")
    else:
        _n_bad += 1
        print(f"  ✗    {name}　{detail}")


def _write_real_day(daily_dir, day):
    """用**正式的寫檔函式**寫一天出來，回傳它實際寫下的表頭。

    ⚠ `write_universe_day` 的輸出目錄是 `fetch.UNI_DIR` 底下的 `daily`
    ⇒ 這裡把 `UNI_DIR` 指到沙盒（⛔ 不可以在測試裡自己拼一個檔出來，
    那樣測的就不是「正式那支會寫出什麼」了）。
    """
    vals = [f"{day}_2330", day, "2330", "台積電", "twse",
            "1000", "1010", "990", "1005", "10000", "10050000",
            "5", "", "", "1234", "", ""]
    assert len(vals) == len(F.UNIVERSE_HEADER), (
        f"⛔ 假列的欄數 {len(vals)} 對不上現行表頭 {len(F.UNIVERSE_HEADER)}")
    F.write_universe_day(day, [vals])
    with io.open(os.path.join(daily_dir, f"{day}.csv"), encoding="utf-8") as f:
        return f.readline().rstrip("\n")


def main():
    sand = tempfile.mkdtemp(prefix="donedays_")
    old_daily, old_cov, old_uni = B.DAILY_DIR, B.COVERAGE, F.UNI_DIR
    try:
        daily = os.path.join(sand, "daily")
        os.makedirs(daily)
        F.UNI_DIR = sand
        B.DAILY_DIR = daily
        B.COVERAGE = os.path.join(sand, "_coverage_backfill.csv")

        # ① 正式寫檔函式寫出來的那一天 ⇒ **必須**算跑過
        head = _write_real_day(daily, "2026-09-10")
        ck("⭐ 寫檔函式實際寫下的表頭有 last_price（⛔ 這是前提，不是結論）",
           head.endswith(",last_price"), head)
        got = B.done_days()
        ck("⭐⭐ 正式寫檔函式寫出來的那一天 ⇒ `done_days()` 判成**跑過了**",
           "2026-09-10" in got, f"got={sorted(got)}")

        # ② 真正的舊格式（少了最後一欄）⇒ **必須**算沒跑過
        old_head = ",".join(F.UNIVERSE_HEADER[:-1])
        io.open(os.path.join(daily, "2026-09-01.csv"), "w",
                encoding="utf-8").write(old_head + "\n")
        got = B.done_days()
        ck("⭐⭐ 少一欄的舊檔 ⇒ 判成**要重抓**（⛔ 反過來的話它永遠補不回來）",
           "2026-09-01" not in got, f"got={sorted(got)}")
        ck("  ⚠ 而且新的那一天不可以被連累",
           "2026-09-10" in got, f"got={sorted(got)}")

        # ③ ⛔ 反向：證明這支測得出「判準用了舊的欄位清單」。
        #   ⚠ 少了這一節，上面兩條在 `HEADER` 走岔時**照樣會綠**——
        #     因為 `done_days()` 讀的是模組層級的 `HEADER`，
        #     而上面沒有任何一條逼它去讀「現行的」那一份。
        real = B.HEADER
        try:
            B.HEADER = list(F.UNIVERSE_HEADER[:-1])      # ← 重現那個 bug
            bad = B.done_days()
            ck("⭐ 反向：把 `HEADER` 改回 16 欄 ⇒ 新的那一天**確實**被判成舊版",
               "2026-09-10" not in bad, f"bad={sorted(bad)}")
            ck("⭐ 反向：而真正的舊檔**確實**被判成現行版本（判準是反的）",
               "2026-09-01" in bad, f"bad={sorted(bad)}")
        finally:
            B.HEADER = real

        # ④ 收口：兩份指的是同一個物件（⛔ 別名可以被下一個人拆掉，
        #    所以①②③那幾條逐格的斷言才是主力，這一條只是加碼）
        ck("`backfill.HEADER` 就是 `fetch.UNIVERSE_HEADER` 本人",
           B.HEADER is F.UNIVERSE_HEADER,
           f"{len(B.HEADER)} vs {len(F.UNIVERSE_HEADER)}")
    finally:
        B.DAILY_DIR, B.COVERAGE, F.UNI_DIR = old_daily, old_cov, old_uni
        shutil.rmtree(sand, ignore_errors=True)

    print(f"\n[selftest] 通過 {_n_ok}｜失敗 {_n_bad}")
    return 1 if _n_bad else 0


if __name__ == "__main__":
    sys.exit(main())

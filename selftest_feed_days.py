#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`feeds.day_is_open` / `days_to_ask` / `save_ledger` 與 `merge_ledger.merge_json`
的自測。**純函式＋臨時目錄，不連網、不碰 data/。**

## ⛔⛔ 這一支釘的是一個「每一趟都有在跑、但永遠跑不完」的缺陷（2026-09-12）

`feeds:tib` 逐日抓。⚠ 端點回「這一天沒有資料」的那些天**不寫任何檔**
⇒ 光看 `data/universe/tib/` **分不出**「那天沒資料」與「從來沒問過」：

    每晚：從區間第一天開始問 → 前 30 天全回「沒有資料」→ 收手
    ⇒ 那 30 天不寫檔 ⇒ 明晚的 `done` 一模一樣 ⇒ **問一模一樣的 30 天**
    ⇒ 2021-06-28 之後的 377 個交易日永遠走不到

⭐ 而逐月那支（`cmd_feed_range`）**一開始就有台帳**——
  ⛔ 同一件事只做了一半，跟 CLAUDE.md 四點六③ `save_done` 同一個形狀。

## ⛔ 而那句診斷是錯的

舊訊息寫「很可能有日期下限」。⚠ 有日期下限的端點是**大聲失敗**：
`STOCK_TIB` 越界回 `stat:"查詢日期小於110年6月28日，請重新查詢!"`
⇒ 那會算進 `failed`。這裡 `failed == 0` ⇒ 端點**明確回答了「沒有資料」**。
⇒ 照著那句話去找一個根本不存在的日期下限，代價是一整個來回。

## 要釘的六件

    ① 台帳裡的日期跳過（⛔ 否則每晚問一樣的 30 天）
    ② **今天**那一天，台帳有也照樣重問（盤中是空的、收盤後才有）
    ③ 有日檔的（`done`）一律跳過，⛔ 而且不算重問
    ④ `--force` 一律全問，且不算重問
    ⑤ `save_ledger` 是**合併**：⛔ 本趟只知道自己那一部分，整份取代 ＝ 洗掉
    ⑥ `merge_json` 合併後的鍵數**不可以少於 main 那一份**
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feeds as F                                             # noqa: E402
import merge_ledger as M                                      # noqa: E402

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
    T = "2026-09-12"

    print("[1] day_is_open：今天還沒結束，昨天結束了")
    ck("  今天 ⇒ 還沒結束", F.day_is_open("2026-09-12", T) is True)
    ck("  昨天 ⇒ 已經結束", F.day_is_open("2026-09-11", T) is False)
    ck("  未來 ⇒ 還沒結束", F.day_is_open("2026-09-30", T) is True)
    # ⛔⛔ 有預設值的參數，一定要有一條**不傳它**的斷言（CLAUDE.md 第七點③）：
    #   `month_is_open` 就是因為 18 條全都傳了 `today=`，
    #   預設值那條路一次都沒走過 ⇒ `runlog.now_tpe` 不存在，掛在 Actions 上。
    try:
        _d = F.day_is_open("1990-01-01")
        ck("  ⭐ 不傳 today（走預設值那條路）⇒ 1990 已經結束", _d is False, str(_d))
    except Exception as ex:                                   # noqa: BLE001
        # ⛔ 不接住的話整支測試當場中斷，後面一條都不會跑（第七點②）
        ck("  ⭐ 不傳 today（走預設值那條路）", False, f"{type(ex).__name__}: {ex}")

    print("\n[2] days_to_ask：台帳裡的跳過，⛔ 但今天照樣重問")
    days = ["2026-09-09", "2026-09-10", "2026-09-11", "2026-09-12"]
    led = {"2026-09-09": "empty", "2026-09-11": "empty", "2026-09-12": "empty"}
    todo, reask = F.days_to_ask(days, set(), led, today=T)
    ck("  09 與 11（台帳有、已結束）被跳過",
       "2026-09-09" not in todo and "2026-09-11" not in todo, str(todo))
    ck("  10（台帳沒有）要問", "2026-09-10" in todo, str(todo))
    ck("  ⭐ 12（今天）台帳有也照樣問", "2026-09-12" in todo, str(todo))
    ck("  重問的那一天要被**講出來**（⛔ 靜靜重問 ＝ 看不出這道在不在）",
       reask == ["2026-09-12"], str(reask))

    print("\n[3] 有日檔的（done）一律跳過，⛔ 而且不算重問")
    todo2, reask2 = F.days_to_ask(days, {"2026-09-10", "2026-09-12"}, led, today=T)
    ck("  10 有日檔 ⇒ 跳過", "2026-09-10" not in todo2, str(todo2))
    # ⭐ 12 是今天、台帳也有，⚠ 但它已經有日檔了 ⇒ `done` 贏
    #   （續跑判準要用**資料自己**，⛔ 台帳只是補「沒有檔的那一半」）
    ck("  ⭐ 12 是今天、台帳也有，⚠ 但有日檔 ⇒ 一樣跳過（資料自己說了算）",
       todo2 == [], str(todo2))
    ck("  ⇒ reask 也空（⛔ 沒有要問的就不可能有重問）", reask2 == [], str(reask2))

    print("\n[4] --force 一律全問，且不算重問")
    todo3, reask3 = F.days_to_ask(days, {"2026-09-10"}, led, force=True, today=T)
    ck("  四天全問", todo3 == days, str(todo3))
    ck("  reask 是空的（⛔ --force 不是『因為是今天才重問』）", reask3 == [],
       str(reask3))

    print("\n[5] save_ledger 是**合併**，⛔ 不是整份取代")
    tmp = tempfile.mkdtemp(prefix="selftest_feed_days_")
    try:
        p = os.path.join(tmp, "sub", "_asked.json")
        n_all, n_new = F.save_ledger(p, {"2021-06-28": "empty", "2021-06-29": "empty"})
        ck("  第一趟：2 鍵、新增 2", (n_all, n_new) == (2, 2), f"{n_all},{n_new}")
        n_all, n_new = F.save_ledger(p, {"2021-06-30": "empty"})
        ck("  ⭐ 第二趟只帶 1 鍵 ⇒ 累計 3（⛔ 不是被洗成 1）",
           n_all == 3, str(n_all))
        ck("  ⇒ 新增只算 1", n_new == 1, str(n_new))
        back = json.load(open(p, encoding="utf-8"))
        # ⭐ 斷言的是**讀回來的內容**，⛔ 不是「寫檔沒丟例外」（四點二）
        ck("  重讀檔案：前一趟那兩鍵**還在**",
           sorted(back) == ["2021-06-28", "2021-06-29", "2021-06-30"], str(sorted(back)))
        # ⛔ 壞掉的台帳要當空的重問，不可以讓整趟停擺
        open(p, "w").write("{ 這不是 JSON")
        ck("  台帳壞掉 ⇒ 讀成空的（⛔ 不是丟例外停擺）", F.load_ledger(p) == {})
        ck("  台帳不存在 ⇒ 空的",
           F.load_ledger(os.path.join(tmp, "nope.json")) == {})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n[6] merge_ledger.merge_json：本趟覆蓋同鍵，⛔ 其餘原封不動")
    out, note = M.merge_json('{"2021-06-28":"empty"}',
                             '{"2021-06-29":"empty","2021-06-30":"ok:3"}')
    got = json.loads(out)
    ck("  三鍵都在", sorted(got) == ["2021-06-28", "2021-06-29", "2021-06-30"],
       str(sorted(got)))
    ck("  說明講得出新增幾鍵", "新增 1" in note, note)
    out2, _ = M.merge_json('{"a":"mine"}', '{"a":"main"}')
    ck("  ⭐ 同鍵取本趟的", json.loads(out2)["a"] == "mine", out2)
    # ⚠ 這一條是這支存在的理由：**它自己絕不可以變成刪東西的那個人**
    for bad, why in (("{}", "本趟是空的"), ("[1,2]", "頂層不是字典"),
                     ("{ 壞", "不是合法 JSON")):
        try:
            M.merge_json(bad, '{"x":1}')
            ck(f"  ⛔ {why} ⇒ 要丟 ValueError", False, "沒丟")
        except ValueError:
            ck(f"  ⛔ {why} ⇒ 丟 ValueError", True)
    # ⭐ main 那一份壞掉也要丟（⛔ 不可以把它當空的、然後整份取本趟的）
    try:
        M.merge_json('{"a":1}', "[1,2]")
        ck("  ⛔ main 那一份頂層不是字典 ⇒ 要丟 ValueError", False, "沒丟")
    except ValueError:
        ck("  ⛔ main 那一份頂層不是字典 ⇒ 丟 ValueError", True)
    # main 上還沒有這個檔（空字串）是正常的 ⇒ 本趟就是全部
    out3, _ = M.merge_json('{"a":1}', "")
    ck("  main 上還沒有這個檔（空字串）⇒ 本趟就是全部", json.loads(out3) == {"a": 1})

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`official_stats.py` 的**涵蓋範圍**自測。⛔ 不連網、不碰 repo 的 data/。

## ⛔ 為什麼要有這一支（2026-09-15）

`official_stats` 的 runlog 寫著「母體 2,492 檔｜已完成 0｜本趟 400」，
而 `_official_stats_done.csv` 只有 325 列 ⇒ 看起來是「跑了 13%，繼續跑就好」。

⭐ 而把第一趟那 400 檔按市場拆開：

```
twse      成功 325 / 嘗試 343  = **94%**
tpex      成功   0 / 嘗試  44  = **0%**
emerging  成功   0 / 嘗試  13  = **0%**
```

⇒ ⛔ **那 75 個失敗不是零星的，是這個端點不涵蓋上櫃與興櫃。**
⚠ 而失敗訊息是 `stat='很抱歉，沒有符合條件的資料!'`
——它講不出「這一檔沒有」還是「這個市場整個沒有」（CLAUDE.md 第二點）
⇒ ⭐ 分辨它的**不是訊息，是拿兩個市場的命中率對一次**
（跟 `TWTB8U` 那次一模一樣：同一發請求裡上市全中、上櫃全不中）。

⇒ 後果如果不修：母體 2,493、可達 1,158 ⇒ **續跑永遠到不了 100%**，
⛔ 而每一趟都像有在跑——那正是「永遠跑不完，每趟都像有在跑」那個形狀。
"""
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import official_stats as O                                     # noqa: E402

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
    d = tempfile.mkdtemp(prefix="offstats_")
    old_meta = O.META
    try:
        O.META = d
        io.open(os.path.join(d, "stocks.csv"), "w", encoding="utf-8").write(
            "stock_id,market,kind\n"
            "1101,twse,stock\n"
            "2330,twse,stock\n"
            "1240,tpex,stock\n"
            "1260,emerging,stock\n"
            "0050,twse,etf\n")

        print("── ① 母體只收這個端點答得出來的市場 ──")
        pool = O.codes()
        ck("⭐ 只回上市的普通股（⛔ 上櫃／興櫃這個端點答不出來）",
           pool == ["1101", "2330"], str(pool))
        ck("  ⛔ 而 ETF 本來就不收（判準是 `kind`）", "0050" not in pool)

        print("\n── ② 被排掉的要**講出來**（⛔ 不是靜靜消失）──")
        ex = O.excluded()
        ck("⭐ 講得出被排掉的是誰、各幾檔",
           ex == {"tpex": 1, "emerging": 1}, str(ex))
        # ⛔ 兩邊加起來要等於全部——⚠ 少一檔就是有人靜靜不見了
        total = len(pool) + sum(ex.values())
        ck("⛔⛔ 母體 ＋ 被排掉的 ＝ **全部普通股**（⚠ 少一檔＝有人靜靜不見）",
           total == 4, f"{len(pool)} + {sum(ex.values())} = {total}"
           + "（⚠ 假料裡普通股是 1101／2330／1240／1260 四檔，0050 是 etf）")

        print("\n── ③ `COVERED` 是參數，⛔ 不是寫死的兩個數字 ──")
        ck("⭐ 換一組 covered，母體跟著變（⇒ 端點日後涵蓋上櫃時改一處就好）",
           O.codes(covered=("tpex",)) == ["1240"],
           str(O.codes(covered=("tpex",))))
        ck("  而 `excluded` 也跟著變（⛔ 兩邊用同一個參數）",
           O.excluded(covered=("tpex",)) == {"twse": 2, "emerging": 1},
           str(O.excluded(covered=("tpex",))))

        print("\n── ④ ⛔⛔ 進度的**分母**是可達母體，不是全部普通股 ──")
        lines = dict(O.progress_lines(pool, {"1101"}, ["2330"], ex))
        ck("⭐ 1/2 ⇒ **50%**（⛔ 用全部 3 檔當分母會是 33%，而那個數永遠爬不上去）",
           "**50%**" in lines["續跑"], lines["續跑"])   # ⛔ 4 檔當分母是 25%
        ck("  而母體那個數字也寫出來了", "**2**" in lines["續跑"], lines["續跑"])

        print("\n── ⑤ 那一行要講清楚「排掉≠缺口」，⛔ 也不可以假裝上櫃有來源 ──")
        k = [x for x in lines if "答不出來" in x][0]
        v = lines[k]
        ck("⭐ 明講這是**涵蓋範圍**，⛔ 不是缺口", "不是缺口" in k, k)
        ck("⭐ 明講判準是**兩個市場的命中率**，⛔ 不是那句「沒有符合條件的資料」",
           "命中率" in v and "講不出它是哪一種" in v, v[:160])
        ck("⛔ 而「上櫃仍然沒有來源」這一條要**留著開著**"
           "（⚠ 排掉它不等於解決它）",
           "仍然沒有來源" in v, v[:160])

        print("\n── ⑥ ⭐⭐ 期中落地：被砍最多賠 FLUSH_EVERY 檔，⛔ 不是整批 ──")
        # ⛔ 這一步實測一趟**超過一小時**，而它本來只在最後寫檔
        #   ⇒ job 被砍／runner 掉／任何例外 ⇒ **整批 400 檔全部白跑**
        #   ⇒ ⭐ 那正是四點六③「永遠跑不完，每趟都像有在跑」。
        old_y, old_m, old_d = O.YEARLY, O.MONTHLY, O.DONE
        try:
            O.YEARLY = os.path.join(d, "y.csv")
            O.MONTHLY = os.path.join(d, "m.csv")
            O.DONE = os.path.join(d, "done.csv")
            Y = {("1101", "114", "1"): ["1101", "114", "1"] + [""] * 8}
            O.land(Y, {}, ["1101"], "20260915")
            ck("⭐ 落地之後台帳**真的**有那一檔（⛔ 不是「land 回了 1」）",
               "1101" in io.open(O.DONE, encoding="utf-8").read(),
               io.open(O.DONE, encoding="utf-8").read())
            # ⛔⛔ 台帳是 **append**：第二次落地不可以把第一次的洗掉（四點六③）
            O.land(Y, {}, ["2330"], "20260915")
            t = io.open(O.DONE, encoding="utf-8").read()
            ck("⛔⛔ 台帳是**追加**：第二次落地之後第一檔**還在**"
               "（⚠ 整份取代就是 `save_done` 那個坑）",
               "1101" in t and "2330" in t, t)
            ck("  而表頭只有一列（⛔ 每次落地都寫一次表頭 ＝ 台帳讀不回來）",
               t.count("stock_id,asof") == 1, t)
            # ⭐⭐ 判準是**行為**，⛔ 不是「原始碼裡有沒有那一行」
            #   ——2026-09-15 我今天第四次踩到那個：把 `if … >= FLUSH_EVERY:`
            #   改成 `if False:` 的突變，**呼叫那一行還在** ⇒ 比字串的斷言全綠。
            # ⇒ ⭐ 做法：讓迴圈跑到一半**炸掉**，再看台帳裡已經有幾檔。
            io.open(os.path.join(d, "done.csv"), "w", encoding="utf-8").write("")
            os.remove(os.path.join(d, "done.csv"))
            io.open(os.path.join(d, "stocks.csv"), "w", encoding="utf-8").write(
                "stock_id,market,kind\n"
                + "".join(f"{1000 + i},twse,stock\n" for i in range(12)))
            old_fe, old_fetch, old_argv = O.FLUSH_EVERY, O.fetch_one, sys.argv
            hit = []

            def boom(sid, today):
                hit.append(sid)
                if len(hit) > 7:                      # ⛔ 第 8 檔炸掉
                    raise RuntimeError("測試用：runner 掛了")
                return ([[sid, "114", "1"] + [""] * 8], [], None)
            try:
                O.FLUSH_EVERY = 3
                O.fetch_one = boom
                sys.argv = ["official_stats.py", "--limit", "12", "--sleep", "0"]
                try:
                    O.main()
                except RuntimeError:
                    pass
            finally:
                O.FLUSH_EVERY, O.fetch_one, sys.argv = old_fe, old_fetch, old_argv
            got = (io.open(O.DONE, encoding="utf-8").read()
                   if os.path.exists(O.DONE) else "")
            n_done = len([x for x in got.splitlines()[1:] if x.strip()])
            ck("⭐⭐ 跑到第 8 檔炸掉 ⇒ 台帳裡**已經有 6 檔**"
               "（FLUSH_EVERY=3 ⇒ 落地過兩次）"
               "　⛔ 只在最後寫的話這裡會是 0 ＝ 整批白跑",
               n_done == 6, f"實得 {n_done} 檔｜{got!r}")
            ck("  而 `FLUSH_EVERY` 是個明示的常數（⛔ 不是散在迴圈裡的數字）",
               isinstance(O.FLUSH_EVERY, int) and O.FLUSH_EVERY > 0,
               str(O.FLUSH_EVERY))
        finally:
            O.YEARLY, O.MONTHLY, O.DONE = old_y, old_m, old_d

        print("\n── ⑦ ★ 沒有動到 repo 真的 stocks.csv ──")
        ck("★ `META` 導到沙箱期間，repo 的 data/meta 沒有被讀寫",
           O.META == d and not os.path.exists(
               os.path.join(d, "_official_stats_done.csv")))
    finally:
        O.META = old_meta
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

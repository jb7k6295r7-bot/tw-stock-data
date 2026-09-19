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
import ast
import io
import json
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


_REPO_META = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "data", "meta")
_REPO_FILES = ("official_yearly_close.csv", "official_monthly_amount.csv",
               "official_yearly_tpex.csv", "_official_stats_done.csv",
               "_official_stats_miss.csv", "official_monthly_tpex.csv",
               "_official_monthly_done_twse.csv", "_official_monthly_done_tpex.csv",
               # ⭐ `_last_run.md` 一定要在裡面：`main()` 會寫它，
               #   ⛔ 而 2026-09-16 我就漏導了 `runlog.PATH` 一次。
               "_last_run.md")


def _snap_repo():
    """repo 真的那幾個判準檔的 (存在?, 位元組數)。⭐ 用來驗「沒有被動到」。

    ⛔ 不是比 mtime：`touch` 不算改內容，而我們要擋的是**內容**被寫掉。
    """
    out = {}
    for n in _REPO_FILES:
        p = os.path.join(_REPO_META, n)
        out[n] = (os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else -1)
    return out


def _raises(fn):
    """⭐ 斷言「它會大聲失敗」——⛔ 不是斷言原始碼裡有 `raise`（第八個陷阱）。"""
    try:
        fn()
    except Exception:
        return True
    return False


def main():
    global _REPO_SNAP
    _REPO_SNAP = _snap_repo()
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

        print("\n── ⑤ 那一行要講清楚「不涵蓋≠缺口」，⛔ 而且兩種不涵蓋要分開 ──")
        k = [x for x in lines if "不涵蓋" in x][0]
        v = lines[k]
        ck("⭐ 明講這是**涵蓋範圍**，⛔ 不是缺口", "不是缺口" in v, v[:160])
        # ⭐⭐ 2026-09-16 接上上櫃之後，被排掉的**有兩種、意義完全不同**：
        #   另一個市場 ＝ 另一趟在做（⛔ 不是缺口）；興櫃 ＝ 兩支端點都不涵蓋（開著）
        #   ⛔ 並排寫成一行的話，`--market tpex` 那一趟會把 twse 1,158 檔
        #     報成「答不出來」——⚠ 而它們只是另一趟在做。
        ck("⭐⭐ 另一個市場要明說是**另一趟在做**（⛔ 不是缺口）",
           "另一趟" in v and "--market" in v, v[:200])
        ck("⭐ 而興櫃那一種要**留著開著**（⚠ 兩支端點都不涵蓋）",
           "emerging" in v and "還開著" in v
           and "已收掉" not in v and "已解決" not in v, v[:240])
        # ⭐ 而上櫃那一半的現況要講得出**年已接上、月還開著**
        k2 = [x for x in lines if "上櫃那一半" in x][0]
        v2 = lines[k2]
        # ⛔⛔ 2026-09-16 月那一半接上之後，這一條差一點變成「改字串讓它綠」。
        #   ⚠ 它原本釘的是「年已接上、月還開著」——⭐ 而**月已經接上了**
        #   ⇒ 那句話從此是**假的**，⛔ 而斷言會逼人把它留著。
        #   ⇒ ⭐ 改成釘**結構**：同一格裡要同時講得出「哪一半已接」與
        #     「哪一半還開著」——⛔ 只剩一種就是把兩半併成一句了。
        ck("⭐⭐ 同一格裡**已接**與**還開著**兩種都要在"
           "（⛔ 併成一句就會有人讀成整條都解決了）",
           ("已接" in v2) and ("還開著" in v2), v2[:240])
        ck("  ⭐ 而「還開著」那一半要點名**是誰**（⛔ 不是一句沒有主詞的『還開著』）",
           "興櫃" in v2 or "emerging" in v2, v2[-260:])
        ck("  ⭐ 月那一半要講得出它一發只回**一年**（⇒ 工作單位是 (代號,年)）",
           "一年" in v2 and "months-years" in v2, v2[-320:])
        ck("  而「只有價那五格進共用表」要寫出來（⛔ 量那三欄是另一種口徑）",
           "價" in v2 and "口徑" in v2, v2[:240])

        # ⭐ 換成 tpex 那一趟：⛔ twse 不可以被寫成「答不出來」
        lt = dict(O.progress_lines(["6488"], set(), ["6488"],
                                   {"twse": 1158, "emerging": 363},
                                   market="tpex"))
        vt = [x for x in lt.values() if "不涵蓋" in str(x)] or [lt[
            [x for x in lt if "不涵蓋" in x][0]]]
        ck("⭐⭐ `--market tpex` 那一趟：twse 1,158 檔被寫成**另一趟在做**",
           "twse 1,158" in vt[0] and "另一趟" in vt[0], vt[0][:200])
        ck("  而母體那一行說得出這一趟是**上櫃**",
           "上櫃" in lt["續跑"], lt["續跑"])

        print("\n── ⑥ ⭐⭐ 期中落地：被砍最多賠 FLUSH_EVERY 檔，⛔ 不是整批 ──")
        # ⛔ 這一步實測一趟**超過一小時**，而它本來只在最後寫檔
        #   ⇒ job 被砍／runner 掉／任何例外 ⇒ **整批 400 檔全部白跑**
        #   ⇒ ⭐ 那正是四點六③「永遠跑不完，每趟都像有在跑」。
        # ⭐⭐ **只有 META 一個旋鈕**：路徑都是呼叫當下才算的函式
        #   ⛔ 舊版是 `O.YEARLY`／`O.MONTHLY`／`O.DONE` 三個常數（import 當下就算好）
        #   ⇒ 那正是第七點第五個那個坑（`mops.CHANGES`）：導一個、漏一個。
        old_meta = O.META
        try:
            O.META = d
            Y = {("1101", "114", "1"): ["1101", "114", "1"] + [""] * 8}
            O.land(Y, {}, ["1101"], "20260915")
            ck("⭐ 落地之後台帳**真的**有那一檔（⛔ 不是「land 回了 1」）",
               "1101" in io.open(O.done_path(), encoding="utf-8").read(),
               io.open(O.done_path(), encoding="utf-8").read())
            ck("⭐⭐ 導走 `META` **一個旋鈕**就夠（⛔ 路徑不可以是 import 當下算好的常數）",
               O.done_path().startswith(d) and O.yearly_path().startswith(d),
               f"{O.done_path()}｜{O.yearly_path()}")
            for _gone in ("DONE", "MISS", "YEARLY", "MONTHLY"):
                ck(f"  ⛔ 而舊的 `{_gone}` 常數**要拿掉**"
                   "（留著的話「只導一個也會對」一次都沒被走過）",
                   not hasattr(O, _gone), f"O.{_gone} 還在")
            # ⛔⛔ 台帳是 **append**：第二次落地不可以把第一次的洗掉（四點六③）
            O.land(Y, {}, ["2330"], "20260915")
            t = io.open(O.done_path(), encoding="utf-8").read()
            ck("⛔⛔ 台帳是**追加**：第二次落地之後第一檔**還在**"
               "（⚠ 整份取代就是 `save_done` 那個坑）",
               "1101" in t and "2330" in t, t)
            ck("  而表頭只有一列（⛔ 每次落地都寫一次表頭 ＝ 台帳讀不回來）",
               t.count("stock_id,asof") == 1, t)
            # ⭐⭐ 判準是**行為**，⛔ 不是「原始碼裡有沒有那一行」
            #   ——2026-09-15 我今天第四次踩到那個：把 `if … >= FLUSH_EVERY:`
            #   改成 `if False:` 的突變，**呼叫那一行還在** ⇒ 比字串的斷言全綠。
            # ⇒ ⭐ 做法：讓迴圈跑到一半**炸掉**，再看台帳裡已經有幾檔。
            # ⛔ 要清的是 `done_path()` 那個檔（⚠ 舊版寫死 `done.csv`
            #   ⇒ 改成函式之後那一行清錯檔，這一節的 6 會變成 8）
            if os.path.exists(O.done_path()):
                os.remove(O.done_path())
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
            got = (io.open(O.done_path(), encoding="utf-8").read()
                   if os.path.exists(O.done_path()) else "")
            n_done = len([x for x in got.splitlines()[1:] if x.strip()])
            ck("⭐⭐ 跑到第 8 檔炸掉 ⇒ 台帳裡**已經有 6 檔**"
               "（FLUSH_EVERY=3 ⇒ 落地過兩次）"
               "　⛔ 只在最後寫的話這裡會是 0 ＝ 整批白跑",
               n_done == 6, f"實得 {n_done} 檔｜{got!r}")
            ck("  而 `FLUSH_EVERY` 是個明示的常數（⛔ 不是散在迴圈裡的數字）",
               isinstance(O.FLUSH_EVERY, int) and O.FLUSH_EVERY > 0,
               str(O.FLUSH_EVERY))
        finally:
            O.META = old_meta

        print("\n── ⑥b ⭐⭐ `--market tpex`：價進共用表、量原樣另存 ──")
        old_meta2 = O.META
        d_tp = tempfile.mkdtemp(prefix="ostpex_")
        old_tf, old_argv2 = O.fetch_one_tpex, sys.argv
        import runlog as _RL2
        old_rl2 = _RL2.PATH
        try:
            O.META = d_tp
            # ⛔⛔ `runlog.PATH` **也要導走**：`main()` 會寫一個區塊，
            #   ⚠ 漏了它就直接寫進 repo 真的 `data/meta/_last_run.md`
            #   （第七點第五個：沙箱導走漏了一個）。
            _RL2.PATH = os.path.join(d_tp, "_last_run.md")
            io.open(os.path.join(d_tp, "stocks.csv"), "w",
                    encoding="utf-8").write(
                "stock_id,market,kind\n6488,tpex,stock\n2330,twse,stock\n")

            def fake_tpex(sid):
                return ([(sid, "115", "1600.00", "7/15", "403.00", "1/02",
                          "749.62")],
                        [(sid, "115", "1323393", "1066891796", "2354",
                          "806.18")], None)
            O.fetch_one_tpex = fake_tpex
            sys.argv = ["official_stats.py", "--market", "tpex",
                        "--limit", "5", "--sleep", "0"]
            # ⛔ 接住例外再判：不接的話整支測試當場中斷，**後面一條都不會跑**
            #   ⇒ 同一個突變會從「紅 5」變成「紅 1」（第七點第二個）。
            _boom = None
            try:
                O.main()
            except Exception as _ex:                             # noqa: BLE001
                _boom = f"{type(_ex).__name__}: {_ex}"
            ck("⭐ `--market tpex` 跑得完（⛔ 炸掉的話後面每一條都測不到）",
               _boom is None, str(_boom))

            ck("⭐ 台帳走 **`_tpex` 那一份**（⛔ 不是跟上市共用一份）",
               O.done_path("tpex").endswith("_official_stats_done_tpex.csv")
               and os.path.exists(O.done_path("tpex")),
               O.done_path("tpex"))
            ck("  ⛔ 而上市那一份**沒有被動到**",
               not os.path.exists(O.done_path("twse")), O.done_path("twse"))

            def _lines(fp, pre):
                if not os.path.exists(fp):
                    return []          # ⛔ 不存在就回空，不要炸（第七點第二個）
                return [ln for ln in io.open(fp, encoding="utf-8")
                        .read().splitlines() if ln.startswith(pre)]
            yrow = _lines(O.yearly_path(), "6488,")
            ck("⭐ 價那五格進了**共用**判準表", len(yrow) == 1, str(yrow))
            cells = yrow[0].split(",") if yrow else []
            ck("⭐⭐ 而 `volume`／`amount`／`transactions` 三欄是**空的**"
               "（⛔ 不是 0——那三欄是另一種口徑，而空 ≠ 0，五點三）",
               len(cells) == 11 and cells[2:5] == ["", "", ""], str(cells))
            ck("  而價那幾格真的寫進去了（收盤平均價 749.62）",
               len(cells) == 11 and cells[9] == "749.62", str(cells))

            trow = _lines(O.tpex_yearly_path(), "6488,")
            ck("⭐ 量那四欄**原樣**另存（保留官方單位：張／仟元／仟筆）",
               len(trow) == 1 and trow[0].split(",")[2:6]
               == ["1323393", "1066891796", "2354", "806.18"], str(trow))
            ck("  ⛔ 而它**沒有**被換算成股／元（那會做出一張兩種單位的表）",
               len(trow) == 1 and "1323393000" not in trow[0], str(trow))
        finally:
            O.fetch_one_tpex, sys.argv = old_tf, old_argv2
            _RL2.PATH = old_rl2
            O.META = old_meta2
            import shutil as _sh
            _sh.rmtree(d_tp, ignore_errors=True)

        print("\n── ⑦ ★ 沒有動到 repo 真的 stocks.csv ──")
        # ⛔ 舊版是斷言「沙箱裡不會出現真的檔名」——⚠ 那個代理判準在
        #   路徑改成函式之後**必然不成立**（沙箱裡本來就會出現那個檔名）。
        # ⇒ ⭐ 改成驗**終點**：repo 真的那幾個檔**逐位元沒變**（四點二）。
        ck("★ 導走 `META` 期間，repo 真的 `data/meta/` 那幾個檔**逐位元沒變**",
           all(_REPO_SNAP[k] == _snap_repo()[k] for k in _REPO_SNAP),
           str({k: (v, _snap_repo()[k]) for k, v in _REPO_SNAP.items()
                if v != _snap_repo()[k]}))
    finally:
        O.META = old_meta
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⑧ ⭐⭐ miss 台帳：⛔ 沒有它，這一條**永遠到不了終點**
    #
    # 2026-09-15 run 34976777901：本趟 400 檔，成功 331／失敗 69，
    # ⚠ 而失敗那 69 檔**沒有被記下來** ⇒ 下一趟還會再問一次。
    #
    # ⭐ 而這一節最重要的是**反向那一條**（第七點）：
    #   端點整個掛掉時 ⇒ `alive=False` ⇒ **一個字都不寫**。
    #   ⛔ 少了它，掛掉兩趟就把全庫判死，⚠ 而畫面上完全正常。
    # ══════════════════════════════════════════════════════════════
    print("\n── ⑧ miss 台帳（合成資料，⛔ 不碰 repo）──")
    d2 = tempfile.mkdtemp(prefix="offmiss_")
    try:
        mp = os.path.join(d2, "_official_stats_miss.csv")
        ck("⛔ 檔不存在 ⇒ 回 {}（⚠ 不是炸掉）", O.load_miss(mp) == {})

        n = O.bump_miss([("1101", "沒有符合條件的資料"), ("1102", "x")],
                        "20260915", path=mp, alive=True)
        ck("⭐ 有成功過（alive）⇒ 失敗的會被記下來", n == 2 and
           set(O.load_miss(mp)) == {"1101", "1102"}, str(O.load_miss(mp)))
        ck("  tries 從 1 開始", O.load_miss(mp)["1101"][0] == 1,
           str(O.load_miss(mp)["1101"]))

        O.bump_miss([("1101", "又一次")], "20260916", path=mp, alive=True)
        ck("⭐ 第二次是**累加**，⛔ 不是覆蓋（四點六③那個坑）",
           O.load_miss(mp)["1101"][0] == 2 and "1102" in O.load_miss(mp),
           str(O.load_miss(mp)))
        ck("  而沒有再失敗的那一檔 tries **沒有被動到**",
           O.load_miss(mp)["1102"][0] == 1, str(O.load_miss(mp)["1102"]))

        # ⛔⛔ 反向那一條：端點掛掉（一檔都沒成功）⇒ 一個字都不寫
        before = io.open(mp, encoding="utf-8").read()
        n2 = O.bump_miss([("2330", "x"), ("2317", "x")], "20260917",
                         path=mp, alive=False)
        ck("⛔⛔ 本趟一檔都沒成功（alive=False）⇒ **一個字都不寫**"
           "（⚠ 少了這條，端點掛兩趟就把全庫判死）",
           n2 == 0 and io.open(mp, encoding="utf-8").read() == before,
           f"回 {n2}｜檔案變了 {io.open(mp, encoding='utf-8').read() != before}")

        # ⭐ 三堆切法
        pool = ["1101", "1102", "1103", "1104"]
        done = {"1101"}
        miss = {"1102": (2, "", ""), "1103": (1, "", "")}
        todo, fresh, gu = O.split_todo(pool, done, miss, limit=10)
        ck("⭐ 放棄的那一檔不在 todo 裡（⛔ 否則每趟都再問一次）",
           "1102" not in todo and gu == ["1102"], f"{todo}｜{gu}")
        ck("  而 tries 還沒到門檻的**仍然要問**（⚠ 一次失敗不等於沒有）",
           "1103" in todo, str(todo))
        ck("  已完成的不在任何一堆裡", "1101" not in todo and "1101" not in gu)
        ck("⭐ limit 有生效（⛔ 切在 fresh 上，不是切在 pool 上）",
           O.split_todo(pool, done, miss, limit=1)[0] == ["1103"],
           str(O.split_todo(pool, done, miss, limit=1)[0]))

        # ⭐ 報表要把三堆分開講，⛔ 而且分母要講清楚
        lines = dict(O.progress_lines(pool, done, todo, {"tpex": 9}, gu))
        txt = " ".join(f"{k}{v}" for k, v in lines.items())
        ck("⭐ 報表講得出「還沒問過」與「問到放棄」是兩堆",
           "還沒問過" in txt and "問到放棄" in txt, txt[:200])
        ck("⛔ 而且明講「問到放棄」不等於「這檔沒有官方統計」",
           "不等於" in txt, txt[:300])
        ck("⭐ 而放棄那幾檔**沒有**從母體裡消失（母體仍然是 4）",
           "**4**" in txt or " 4 " in txt, txt[:160])
    finally:
        import shutil
        shutil.rmtree(d2, ignore_errors=True)

    # ───── [主鍵] ⛔ 年表的第三欄是 volume，⚠ 而月表的第三欄是 month ─────
    print("\n── 主鍵：年表兩格、月表三格 ──")
    _yrow = ["2330", "114", "12740507347", "916448075621", "2829457",
             "78.30", "1/19", "62.20", "8/09", "72.09", "20260909"]
    ck("⭐⭐ 年表主鍵**只有 (代號, 年度)**"
       "（⛔ `r[:3]` 會把**成交股數**寫進主鍵 ⇒ `--force` 重抓多一列而不是覆蓋）",
       O.y_key(_yrow) == ("2330", "114"), str(O.y_key(_yrow)))
    ck("  ⇒ 同一檔同一年、量不同 ⇒ 仍然是**同一個鍵**（覆蓋，⛔ 不是多一列）",
       O.y_key(_yrow) == O.y_key(_yrow[:2] + ["999"] + _yrow[3:]),
       f"{O.y_key(_yrow)} vs {O.y_key(_yrow[:2] + ['999'] + _yrow[3:])}")
    _mrow = ["2330", "115", "1", "1835.00", "1545.00", "1718.05"]
    ck("⭐ 而**月**表的第三格是 `month` ⇒ 主鍵要三格",
       O.m_key(_mrow) == ("2330", "115", "1"), str(O.m_key(_mrow)))
    ck("  ⇒ 同一檔同一年**不同月**是不同的鍵",
       O.m_key(_mrow) != O.m_key(_mrow[:2] + ["2"] + _mrow[3:]))
    import ast as _ast
    _mfn = [n for n in _ast.parse(io.open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "official_stats.py"),
        encoding="utf-8").read()).body
        if isinstance(n, _ast.FunctionDef) and n.name == "main"][0]
    _keyed = {getattr(n.func, "id", "") for n in _ast.walk(_mfn)
              if isinstance(n, _ast.Call)}
    ck("⭐ `main()` 兩個都用了（⛔ 不是還留著 `r[:3]`）",
       {"y_key", "m_key"} <= _keyed, str(sorted(x for x in _keyed if x)))
    # ⭐⭐ 驗**終點**：讀→改量→寫→再讀，同一檔同一年**只能有一列**
    #   ⛔ 寫入端與讀入端用不同的 key ⇒ 會變兩列（半修比原本的 bug 更糟）
    import tempfile as _tf
    _d = _tf.mkdtemp(prefix="oskey_")
    try:
        _fp = os.path.join(_d, "y.csv")
        O._save(_fp, O.Y_HEADER, {O.y_key(_yrow): _yrow})
        _back = O._load(_fp, O.Y_HEADER, O.y_key)
        _chg = _yrow[:2] + ["999"] + _yrow[3:]      # ⚠ 官方把成交股數修正了
        _back[O.y_key(_chg)] = _chg
        O._save(_fp, O.Y_HEADER, _back)
        _lines = [x for x in io.open(_fp, encoding="utf-8").read().splitlines()
                  if x.startswith("2330,114,")]
        ck("⭐⭐ 讀→改量→寫 ⇒ 同一檔同一年**只有一列**（⛔ 不是兩列）",
           len(_lines) == 1 and ",999," in _lines[0], str(_lines))
        import inspect as _insp
        _sig = _insp.signature(O._load)
        ck("⭐ 而 `_load` 的 `key` **沒有預設值**"
           "（⛔ 忘了傳要當場 TypeError，不是靜靜寫出兩列）",
           _sig.parameters["key"].default is _insp.Parameter.empty, str(_sig))
    finally:
        import shutil as _sh2
        _sh2.rmtree(_d, ignore_errors=True)

    # ───── [上櫃年度] ⭐ 假回應**照真的形狀**做（含兩個都叫「日期」的欄） ─────
    #  ⚠ 這一段是 probe 120 真的回應的子集：兩張 tables、fields 有重複欄名、
    #    code／name／curDate／totalCount／notes 都在。⛔ 少一樣就等於那一格沒測。
    print("\n── 上櫃年度統計（yearlyStock） ──")
    TP = ('{"flagField":"張數","tables":[{"title":"6488 環球晶          ",'
          '"fields":["年度","成交張數(A)","金額(仟元)(B)","筆數(仟)",'
          '"加權平均價(B/A)","盤中最高價","日期","盤中最低價","日期","收盤平均價"],'
          '"data":[[115,"1,323,393","1,066,891,796","2,354","806.18","1,600.00",'
          '"7/15","403.00","1/02","749.62"],'
          '[114,"788,658","312,330,604","1,195","396.03","558.00","10/27",'
          '"255.50","4/09","366.43"]],'
          '"totalCount":12,"notes":[],"code":"6488","name":"環球晶          ",'
          '"curDate":1150915,"subtitle":"近年個股成交資訊(當年度統計至 1150915 止)"},'
          '{"title":"","data":[[1600.0000,"115/7/15",63.2000,"105/5/05"]],'
          '"fields":["近年最高價","日期","近年最低價","日期"],"notes":["ETF…"]}],'
          '"stat":"ok"}')
    pr, vr, err = O.parse_tpex_yearly(TP.encode("utf-8"), "6488")
    ck("⭐ 解得出來（bytes 進、兩組列出來）", err is None and len(pr) == 2 and len(vr) == 2,
       f"{err}｜價 {len(pr)}｜量 {len(vr)}")
    ck("⭐⭐ **價**那五格逐位相同（⛔ 兩個都叫「日期」⇒ 一定要用位置取）",
       pr[0] == ("6488", "115", "1600.00", "7/15", "403.00", "1/02", "749.62"),
       str(pr[0]))
    ck("  114 那一列也對（⇒ 不是只讀了第一列）",
       pr[1] == ("6488", "114", "558.00", "10/27", "255.50", "4/09", "366.43"),
       str(pr[1]))
    ck("⭐ **量**那四格保留官方單位（張／仟元／仟筆），⛔ 不在這裡換算",
       vr[0] == ("6488", "115", "1323393", "1066891796", "2354", "806.18"),
       str(vr[0]))
    ck("⭐⭐ 判準是**回應自己回顯的 code**（⛔ 不是「有回列」）",
       O.parse_tpex_yearly(TP, "2330")[2] is not None
       and "沒生效" in O.parse_tpex_yearly(TP, "2330")[2],
       str(O.parse_tpex_yearly(TP, "2330")[2]))
    # ⛔ `monthlyStock` 真的回過的那一種：stat 是 ok、data 空、code 是 null
    NUL = ('{"tables":[{"title":"null ","fields":["年","月"],"data":[],'
           '"date":2026,"totalCount":0,"code":null,"name":""}],'
           '"date":"20260916","stat":"ok","flagField":"張數"}')
    ck("⭐⭐ `stat:\"ok\"` ＋ `data:[]` ＋ `code:null` ⇒ **當失敗**"
       "（⚠ probe 121 真的回過這一種）",
       O.parse_tpex_yearly(NUL, "6488")[2] is not None,
       str(O.parse_tpex_yearly(NUL, "6488")[2]))
    ck("⛔ 不是 JSON ⇒ 講得出它不是 JSON（⚠ 被 CDN 擋時回的是 HTML）",
       "不是 JSON" in (O.parse_tpex_yearly(b"<html>428</html>", "6488")[2] or ""),
       str(O.parse_tpex_yearly(b"<html>428</html>", "6488")[2]))
    ck("⛔ stat 不是 ok ⇒ 把 stat 原文講出來",
       "參數輸入錯誤" in (O.parse_tpex_yearly('{"stat":"參數輸入錯誤"}', "6488")[2] or ""),
       str(O.parse_tpex_yearly('{"stat":"參數輸入錯誤"}', "6488")[2]))
    ck("⭐ 欄名帶單位（⛔ 只叫 volume 的話，下一個人不知道它是張還是股）",
       O.TY_HEADER[2:6] == ["volume_lots", "amount_kntd", "transactions_k",
                            "wavg_price_derived"], str(O.TY_HEADER))

    # ───── [污染] ⛔ 整頁 HTML 被寫進 `why` ⇒ 一列被切成好幾列 ─────
    d3 = tempfile.mkdtemp(prefix="osmiss_")
    try:
        mp = os.path.join(d3, "_miss.csv")
        # ⭐ 假回應照真的形狀做：真的那兩列就是 `<head>` 與 `<meta h`
        with io.open(mp, "w", encoding="utf-8") as f:
            f.write(O.MISS_HEADER)
            f.write("1262,1,20260915,FMSRFK stat='很抱歉；沒有符合條件的資料!'\n")
            f.write("<head>,,,\n")
            f.write("<meta h,,,\n")
            f.write("00679B,2,20260915,x\n")
        got = O.load_miss(mp)
        ck("⛔ 不像代號的列**不會**進 miss 台帳（`<head>`／`<meta h`）",
           set(got) == {"1262", "00679B"}, str(sorted(got)))
        ck("⭐ 而它們有被**數出來**（⛔ 丟掉而不說 ＝ 沒被污染，看起來一樣）",
           O.bad_rows(mp) == ["<head>", "<meta h"], str(O.bad_rows(mp)))
        ck("  ⭐ ETF 那種帶字母的代號**不可以**被誤殺", O.is_code("00679B"))
        ck("  六碼的也不可以（912000 晨訊科-DR）", O.is_code("912000"))
        ck("  ⛔ 而 `<head>` 不是代號", not O.is_code("<head>"))

        # ⭐⭐ 寫入端：整頁 HTML 進去，出來**只能是一列**（驗終點，四點二）
        mp2 = os.path.join(d3, "_miss2.csv")
        html = '<head>\n<meta http-equiv="refresh">\n</head>428, blocked'
        O.bump_miss([("2330", html)], "20260916", path=mp2, alive=True)
        body = io.open(mp2, encoding="utf-8").read().splitlines()
        ck("⭐⭐ `why` 是整頁 HTML ⇒ 寫出來**仍然只有表頭＋1 列**"
           "（⛔ 這就是那兩列的病根）",
           len(body) == 2, f"{len(body)} 行：{body[:4]}")
        ck("  而內容沒有被丟掉（⛔ 六點六：錯誤訊息可行動的部分常在後面）",
           "428" in body[1] and "blocked" in body[1], body[1][:120])
        ck("  重讀回來認得出那一檔（驗終點，⛔ 不是斷言寫檔成功）",
           set(O.load_miss(mp2)) == {"2330"}, str(sorted(O.load_miss(mp2))))
    finally:
        import shutil
        shutil.rmtree(d3, ignore_errors=True)

    # ───────── [對照組] ⭐ 「全失敗」的兩種，⛔ 它們長得一模一樣 ─────────
    #  ⚠ 這一節**不連網**：`endpoint_alive` 的 fetch 是注入的假的。
    pool4 = ["1101", "1102", "1103", "9999"]
    done4 = {"1102", "1101", "5555"}     # 5555 已不在母體 ⇒ ⛔ 不可以當對照組
    ctrl = O.controls(pool4, done4)
    ck("⭐ 對照組取 **母體 ∩ 已完成**（⛔ 不是寫死的代號）",
       ctrl == ["1101", "1102"], str(ctrl))
    ck("  ⛔ 已經不在母體裡的（5555）不會被選進對照組",
       "5555" not in ctrl, str(ctrl))
    ck("  ⭐ 同一批母體每趟挑到**同一組**（可重現）",
       O.controls(pool4[::-1], set(done4)) == ctrl, str(ctrl))
    ck("  limit 有生效", O.controls(pool4, done4, n=1) == ["1101"])

    good = lambda sid, today: ([("x",)], [("y",)], None)
    dead = lambda sid, today: ([], [], "FMSRFK stat='很抱歉，沒有符合條件的資料!'")
    half = lambda sid, today: (([], [], "壞了") if sid == "1101"
                               else ([("x",)], [("y",)], None))
    a1, w1 = O.endpoint_alive(ctrl, "20260916", fetch=good)
    a2, w2 = O.endpoint_alive(ctrl, "20260916", fetch=dead)
    a3, w3 = O.endpoint_alive([], "20260916", fetch=dead)
    a4, w4 = O.endpoint_alive(ctrl, "20260916", fetch=half)
    ck("⭐ 對照組答得出來 ⇒ True（端點是好的 ⇒ 全失敗是那一批自己的性質）",
       a1 is True, f"{a1}｜{w1[:60]}")
    ck("⭐ 對照組也答不出來 ⇒ False（端點側 ⇒ 一個字都不記 miss）",
       a2 is False, f"{a2}｜{w2[:60]}")
    ck("⭐⭐ 沒有對照組 ⇒ **None**，⛔ 不是 False（那是「這一層沒跑」）",
       a3 is None, f"{a3}｜{w3[:60]}")
    ck("  ⚠ 而 None 那一格要**大聲講出它沒跑**（⛔ 一行 skipped 讀起來像 ok）",
       "這一層沒跑" in w3 and "退回舊判準" in w3, w3[:120])
    ck("  ⭐ 只要有一檔答得出來就算活著（⛔ 不是要求全中）",
       a4 is True, f"{a4}｜{w4[:60]}")
    ck("  說明要講得出**幾檔／哪幾檔**（⛔ 不是只講活著）",
       "1102" in w4 and "1／2" in w4, w4[:120])

    # ⭐⭐ 呼叫點（CLAUDE.md 第七點第三個：測了判準、沒測呼叫點）
    src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "official_stats.py"), encoding="utf-8").read()
    import ast
    tree = ast.parse(src)
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n for n in ast.walk(fn)
             if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "bump_miss"]
    ck("⭐ main() 只有一個 bump_miss 呼叫點", len(calls) == 1, str(len(calls)))
    kw = {k.arg: k.value for k in calls[0].keywords}
    ck("⭐⭐ 而它傳的 alive 是**那個變數**，⛔ 不是 bool(ok)"
       "（這就是 2026-09-16 那趟判錯的那一格）",
       isinstance(kw.get("alive"), ast.Name) and kw["alive"].id == "alive",
       ast.dump(kw.get("alive")) if kw.get("alive") else "沒有 alive=")
    probes = [n for n in ast.walk(fn)
              if isinstance(n, ast.Call)
              and getattr(n.func, "id", "") == "endpoint_alive"]
    ck("⭐ main() 真的會去問對照組（⛔ 不是只有函式在那裡沒人叫）",
       len(probes) == 1, str(len(probes)))
    # ⛔ 說明文字要講**實際發生的那一種**（run 158 實測：檢查過了，
    #   而說明印「且對照組也答不出來」⇒ 一個通過的檢查說著相反的話）
    ck("⭐⭐ 全失敗**而對照組答得出來** ⇒ 說明要講「而對照組答得出來」",
       "而對照組答得出來" in O.batch_fail_note(104, 0, True)
       and "也答不出來" not in O.batch_fail_note(104, 0, True),
       O.batch_fail_note(104, 0, True))
    ck("⭐ 全失敗**而且對照組也答不出來** ⇒ 說明要講那一種",
       "也答不出來" in O.batch_fail_note(104, 0, False),
       O.batch_fail_note(104, 0, False))
    ck("  有成功的 ⇒ 講成功幾檔", "成功 3" in O.batch_fail_note(10, 3, False))
    ck("  沒有要問的 ⇒ 講「都問完了」", "都問完了" in O.batch_fail_note(0, 0, False))
    _n = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
          and getattr(n.func, "id", "") == "batch_fail_note"]
    ck("⭐ 而 `main()` 真的用它（⛔ 不是另外寫一段 if）", len(_n) == 1, str(len(_n)))

    checks = [n for n in ast.walk(fn)
              if isinstance(n, ast.Call)
              and getattr(n.func, "attr", "") == "check"]
    batch = [c for c in checks
             if isinstance(c.args[0], ast.Constant) and "整批失敗" in c.args[0].value]
    ck("⭐ 「不是整批失敗」那道閘門還在", len(batch) == 1, str(len(batch)))
    names = {n.id for n in ast.walk(batch[0].args[1]) if isinstance(n, ast.Name)}
    ck("⭐⭐ 而它的判準裡有 **alive**（⛔ 少了它就回到每趟都紅的那一版）",
       "alive" in names, str(sorted(names)))

    # ══════════════════════════════════════════════════════════════
    # ⑩ ⭐⭐ 月表的**年份掃描**（工作單位是 (代號, 年)，⛔ 不是代號）
    #
    # 2026-09-16 加：回測線 0841 §四 4. 要更早年份的月表，
    # ⚠ 而我自己需要它當**外部錨點**（他們量到的 ② ④ 在「年」這一級分不出來）。
    # ══════════════════════════════════════════════════════════════
    print("\n── ⑩ 月表年份掃描 ──")
    snap0 = _snap_repo()

    # ── ⑩a `roc_years`／`parse_years` ──
    import datetime as _dt
    fake = _dt.datetime(2026, 9, 16, tzinfo=O.TPE)
    ck("`roc_years` 從 104 起、上限由**今天**算（⛔ 不是寫死的清單）",
       O.roc_years(fake) == list(range(104, 116)), str(O.roc_years(fake)))
    ck("  ⭐ 跨年那一天會多一年（⇒ 它真的是算出來的）",
       O.roc_years(_dt.datetime(2027, 1, 2, tzinfo=O.TPE))[-1] == 116,
       str(O.roc_years(_dt.datetime(2027, 1, 2, tzinfo=O.TPE))[-1]))
    # ⛔ 第七點第三個：有預設值的參數，一定要有一條**不傳它**的斷言
    ck("  ⭐ 不傳 `today` 那條路也走得通（⛔ 預設值那條是 Actions 上唯一會走的）",
       O.roc_years()[0] == 104 and len(O.roc_years()) >= 12, str(O.roc_years()))
    ck("`parse_years('')` ＝ 不指定 ⇒ 全部", O.parse_years("", fake) == O.roc_years(fake))
    ck("`parse_years('all')` ＝ 全部", O.parse_years("all", fake) == O.roc_years(fake))
    ck("`parse_years('109')` ＝ [109]", O.parse_years("109", fake) == [109])
    ck("`parse_years('104-106,112')`", O.parse_years("104-106,112", fake) == [104, 105, 106, 112])
    ck("⭐ 超出範圍的年被濾掉（⛔ 不是抓一趟必定失敗的年）",
       O.parse_years("99,200,109", fake) == [109], str(O.parse_years("99,200,109", fake)))

    # ── ⑩b `parse_tpex_monthly`：三道判準各驗一次 ──
    def _tm(code="6488", date=2024, vol_field="成交仟股(B)", stat="ok", n=2):
        return json.dumps({"tables": [{
            "title": "", "code": code, "date": date, "totalCount": n,
            "fields": ["年", "月", "收市最高價", "收市最低價", "收市平均價",
                       "成交筆數", "成交金額仟元(A)", vol_field, "成交週轉率(%)"],
            "data": [[113, m, "603.00", "573.00", "587.27", "44,168",
                      "17,258,302", "29,478", "6.65"] for m in range(1, n + 1)],
        }], "stat": "ok" if stat == "ok" else stat}).encode()

    rows, err = O.parse_tpex_monthly(_tm(), "6488", 113)
    ck("⭐ 正常回應 ⇒ 逐列解得出來", err is None and len(rows) == 2, f"{err}｜{rows[:1]}")
    ck("  ⭐ 而**欄的順序**照真回應（⛔ 順序也是形狀的一部分）",
       rows and rows[0] == ["6488", "113", "1", "603.00", "573.00", "587.27",
                            "44168", "17258302", "29478", "6.65"], str(rows[:1]))
    _, e1 = O.parse_tpex_monthly(_tm(code=None), "6488", 113)
    ck("⛔ `code` 回顯是 null ⇒ 失敗（⚠ 而它的 `stat` 仍然是 ok）",
       e1 and "參數沒生效" in e1, str(e1))
    _, e2 = O.parse_tpex_monthly(_tm(date=2020), "6488", 113)
    ck("⛔ 回顯的年**不是我送的那一年** ⇒ 失敗（⚠ 靜靜回別年是第二點①）",
       e2 and "那一年的參數沒生效" in e2, str(e2))
    # ⭐⭐ 2026-09-20 訂正：「成交張數(B)」不是空回應的信號，是民114 起
    #   官方換的新名字（見 official_stats.TM_VOL_FIELDS 上方的訂正）——
    #   run 171 撞到的正是這一格：舊斷言原本寫「不落地」，而那是錯的。
    rows_new, err_new = O.parse_tpex_monthly(_tm(vol_field="成交張數(B)"), "6488", 113)
    ck("⭐⭐ 量欄名是「成交張數(B)」（民114 起的新名字）⇒ **照樣落地**",
       err_new is None and len(rows_new) == 2, f"{err_new}｜{rows_new[:1]}")
    ck("  ⭐ 而落地的欄跟舊名字逐位相同（⇒ 兩個名字底下是同一個量）",
       rows_new == rows, f"{rows_new[:1]} vs {rows[:1]}")
    _, e3 = O.parse_tpex_monthly(_tm(vol_field="別的名字(B)"), "6488", 113)
    ck("⛔ 量欄名是**第三種**（兩個已知名字都不是）⇒ 仍然不落地",
       e3 and "單位可能真的變了" in e3, str(e3))
    ck("  ⭐⭐ `TM_VOL_FIELDS` 是兩個已知名字的集合，⛔ 不是只有一個",
       set(O.TM_VOL_FIELDS) == {"成交仟股(B)", "成交張數(B)"}, str(O.TM_VOL_FIELDS))
    _, e4 = O.parse_tpex_monthly(_tm(stat="參數輸入錯誤"), "6488", 113)
    ck("⛔ stat 不是 ok ⇒ 失敗", e4 and "stat=" in e4, str(e4))
    _, e5 = O.parse_tpex_monthly(_tm(n=0), "6488", 113)
    ck("⛔ 0 列 ⇒ 失敗（⚠ ⛔ 不是「這一檔沒有」——那句話講不出它是哪一種）",
       e5 and "0 列" in e5, str(e5))

    # ── ⑩c 兩個市場**各一份檔**（⛔ 這是這一節存在的理由）──
    f1, p1, h1, k1 = O.sweep_spec("twse")
    f2, p2, h2, k2 = O.sweep_spec("tpex")
    ck("⭐⭐ 上市／上櫃月表是**兩份不同的檔**"
       "（⛔ 併成一張 ＝ 三道靜默的定義接縫，而主鍵不重疊 ⇒ 不會報錯）",
       p1() != p2(), f"{p1()}｜{p2()}")
    ck("  ⭐ 上櫃那份的欄名**自己帶定義**（收盤／仟股）",
       "close_high" in h2 and "close_avg" in h2 and "volume_kshares" in h2, str(h2))
    ck("  ⛔ 而它**沒有**「high／low／avg_price」這種對不上時無法判誰錯的欄名",
       not ({"high", "low", "avg_price"} & set(h2)), str(h2))
    ck("  ⭐ 續跑台帳也各一份", O.sweep_done_path("twse") != O.sweep_done_path("tpex"))
    ck("  ⭐⭐ 而它跟**年**表那一份也不同"
       "（⛔ 混在一起 ＝ 掃過月表的檔會被當成年表也做完了）",
       O.sweep_done_path("tpex") != O.done_path("tpex"),
       f"{O.sweep_done_path('tpex')}｜{O.done_path('tpex')}")

    # ── ⑩d `sweep_todo`：先把一檔的所有年做完 ──
    todo = O.sweep_todo(["A", "B", "C"], [104, 105], set(), 3)
    ck("⭐ 先把**一檔的所有年**做完再換下一檔"
       "（⛔ 先掃完一年 ⇒ 任何時間點每一檔都殘缺，而殘缺跟「沒上市」長得一樣）",
       todo == [("A", 104), ("A", 105), ("B", 104)], str(todo))
    todo2 = O.sweep_todo(["A", "B"], [104, 105], {("A", "104")}, 99)
    ck("  已完成的不再問（⭐ 鍵是字串年）",
       todo2 == [("A", 105), ("B", 104), ("B", 105)], str(todo2))
    ck("  `limit` 真的截斷", len(O.sweep_todo(["A", "B"], [104, 105], set(), 2)) == 2)

    # ── ⑩e 台帳是**追加**，⛔ 不是整份取代（四點六）──
    d10 = tempfile.mkdtemp(prefix="ossweep_")
    old_meta10 = O.META
    try:
        O.META = d10
        dp = O.sweep_done_path("tpex")
        O.save_sweep_done(dp, [("6488", "113")], "20260916")
        O.save_sweep_done(dp, [("6488", "114")], "20260916")
        got = O.load_sweep_done(dp)
        ck("⭐⭐ 第二趟**不會洗掉**第一趟寫的（⇒ 這是合併，不是取代）",
           got == {("6488", "113"), ("6488", "114")}, str(sorted(got)))
        ck("  讀不到檔就是空集合（⛔ 不是炸掉）",
           O.load_sweep_done(os.path.join(d10, "_nope.csv")) == set())
    finally:
        O.META = old_meta10
        shutil.rmtree(d10, ignore_errors=True)

    # ── ⑩f `fetch_month_twse`：`date` 沒生效時它會靜靜回**最新一年** ──
    def _fm(title):
        return json.dumps({"stat": "OK", "title": title, "fields": [
            "年度", "月份", "最高價", "最低價", "加權(股數)平均價", "成交筆數",
            "成交金額(元)", "成交股數", "週轉率(%)"],
            "data": [["114", "1", "1", "1", "1", "1", "1", "1", "1"]]}).encode()
    _got = {}

    def _fake_get(url, **kw):
        _got["url"] = url
        return _fm(_got["title"]), None
    old_get = O.B.get
    try:
        O.B.get = _fake_get
        _got["title"] = "109年2330 台積電  月成交資訊"
        rs, er = O.fetch_month_twse("2330", 109, "20260916")
        ck("⭐ `FMSRFK` 送 `date=<西元>0101`", "date=20200101" in _got["url"], _got["url"])
        ck("  title 同時回音代號**與年度** ⇒ 過", er is None and len(rs) == 1, f"{er}")
        _got["title"] = "115年2330 台積電  月成交資訊"
        _, er2 = O.fetch_month_twse("2330", 109, "20260916")
        ck("⭐⭐ title 回的是**別年** ⇒ 失敗"
           "（⚠ 只比代號的話，這一格會靜靜收下今年的資料當成 109 年）",
           er2 and "沒有回音我送的 109 年" in er2, str(er2))
    finally:
        O.B.get = old_get

    # ── ⑩g ⛔⛔ 一個**通過**的檢查，說明不可以寫著相反的話 ──
    #   2026-09-16 feeds run 163 實測：392／400 成功、那道閘門 **ok**，
    #   ⚠ 而說明印的是「本趟 400 格**全部失敗**」。
    #   ⭐ 而這正是同一支檔裡 `batch_fail_note()` 已經修過一次的那個錯
    #     ——⛔ 我寫 `run_sweep` 時沒去看它，又寫了一次（四點五）。
    ck("⭐⭐ 有成功 ⇒ 說明要講**成功幾格**（⛔ 不可以說「全部失敗」）",
       "成功 392／400" in O.sweep_fail_note([1] * 400, [1] * 392, [("a", "x")] * 8)
       and "全部失敗" not in O.sweep_fail_note([1] * 400, [1] * 392, [("a", "x")] * 8),
       O.sweep_fail_note([1] * 400, [1] * 392, [("a", "x")] * 8))
    ck("  真的全失敗才說「全部失敗」",
       "全部失敗" in O.sweep_fail_note([1] * 400, [], [("a", "x")] * 400),
       O.sweep_fail_note([1] * 400, [], [("a", "x")] * 400))
    ck("  沒有要做的 ⇒ 說「做完了」（⛔ 不是「全部失敗」）",
       "做完了" in O.sweep_fail_note([], [], [])
       and "失敗" not in O.sweep_fail_note([], [], []), O.sweep_fail_note([], [], []))
    ck("  ⭐ 有失敗就要講幾格、⛔ 沒失敗要明說 0",
       "失敗 8 格" in O.sweep_fail_note([1] * 400, [1] * 392, [("a", "x")] * 8)
       and "0 失敗" in O.sweep_fail_note([1] * 9, [1] * 9, []),
       O.sweep_fail_note([1] * 9, [1] * 9, []))
    # ⛔ 而「它真的被 run_sweep 用到」要驗——⚠ 一個沒人叫的具名函式跟 f-string 一樣沒用
    _sw = [n for n in ast.walk(ast.parse(io.open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "official_stats.py"), encoding="utf-8").read()))
        if isinstance(n, ast.FunctionDef) and n.name == "run_sweep"][0]
    _calls = [n for n in ast.walk(_sw) if isinstance(n, ast.Call)
              and getattr(n.func, "id", "") == "sweep_fail_note"]
    ck("⭐ 而 `run_sweep()` 真的用它（⛔ 不是留一個沒人叫的函式）",
       len(_calls) == 1, str(len(_calls)))

    ck("★ ⑩ 全程 repo 真的 `data/meta/` 那幾個檔**逐位元沒變**",
       _snap_repo() == snap0, "有檔被動到了")

    # ══════════════════════════════════════════════════════════════
    # ⑪ ⭐⭐ 月表掃描的**收斂**：「官方說沒有」＋「我方那一年也沒有」⇒ 問完了
    #    ⛔ 不修的話 `save_sweep_done` 只記成功 ⇒ 失敗的每一趟都回到 todo
    #      ⇒ run 166 實測 5,000 格失敗 2,097（42%），而其中 **71%** 是
    #        「我方那一年根本沒有 twse 日檔」那一種 ⇒ **永遠不會成功**
    #    ⇒ 而終局是「剩下的剛好全部失敗」⇒ 七點五第三個那道閘門必然誤判
    # ══════════════════════════════════════════════════════════════
    print("\n⑪ ⭐⭐ 月表掃描的收斂：問完了 vs 還沒問到")
    d11 = tempfile.mkdtemp(prefix="osweep_")
    try:
        os.makedirs(os.path.join(d11, "stocks"))
        io.open(os.path.join(d11, "stocks", "1111.csv"), "w", encoding="utf-8").write(
            "date,stock_id,market,close\n"
            "2019-01-02,1111,twse,10\n"      # 民108 有 twse
            "2016-01-04,1111,tpex,10\n")     # 民105 只有 tpex（＝轉板前）
        NO = "FMSRFK stat='很抱歉，沒有符合條件的資料!'"
        ck("⑪ ⭐ 我方那一年**沒有** twse 日檔 ⇒ **問完了**",
           O.sweep_consistent_nodata(NO, "1111", 104, "twse", d11) is True)
        ck("⑪ ⭐⭐ 那一年只有 **tpex**（轉板前）⇒ 對 twse 來說也是**問完了**"
           "（⛔ 判準是 `market` 欄，不是「有沒有列」）",
           O.sweep_consistent_nodata(NO, "1111", 105, "twse", d11) is True)
        ck("⑪ ⛔ 我方那一年**有** twse 日檔 ⇒ **不是**問完了（⇒ 還要再問）",
           O.sweep_consistent_nodata(NO, "1111", 108, "twse", d11) is False)
        ck("⑪ ⛔⛔ 官方的訊息**不是**那一句（例如逾時）⇒ 一律**不算**問完了"
           "（⚠ 否則一次斷線會把一整批永久記成「沒有」）",
           O.sweep_consistent_nodata("FMSRFK URLError: timed out",
                                     "1111", 104, "twse", d11) is False)
        ck("⑪ ⭐ 那一檔我方**根本沒有檔** ⇒ 回空集合 ⇒ 算問完了（⛔ 不是丟例外）",
           O.sweep_consistent_nodata(NO, "9999", 104, "twse", d11) is True)
        # ⭐ 台帳要分得出兩種：`why` 欄
        lp = os.path.join(d11, "meta", "_x_done.csv")
        O.save_sweep_done(lp, [("1111", "108")], "20260916")
        O.save_sweep_done(lp, [("1111", "104")], "20260916", why="nodata")
        body = io.open(lp, encoding="utf-8").read()
        ck("⑪ ⭐⭐ 台帳把兩種**分得出來**（`why` 欄：空 vs `nodata`）"
           "（⛔ 混在一起的話，日後我方補齊沒辦法重開那幾格）",
           "stock_id,roc_year,asof,why" in body
           and "1111,108,20260916,\n" in body
           and "1111,104,20260916,nodata\n" in body, body)
        ck("⑪ ⭐ 而 `load_sweep_done` 兩種都算**已完成**（⇒ 不再重問）",
           O.load_sweep_done(lp) == {("1111", "108"), ("1111", "104")},
           str(O.load_sweep_done(lp)))
        # ⭐ 呼叫點：`run_sweep` 真的有叫它（⛔ 不是留一個沒人叫的函式）
        import ast as _a11
        src11 = io.open(os.path.join(HERE, "official_stats.py"),
                        encoding="utf-8").read()
        fn11 = next((n for n in _a11.walk(_a11.parse(src11))
                     if isinstance(n, _a11.FunctionDef) and n.name == "run_sweep"), None)
        called = {n.func.id for n in _a11.walk(fn11)
                  if isinstance(n, _a11.Call) and isinstance(n.func, _a11.Name)} if fn11 else set()
        ck("⑪ ⭐⭐ `run_sweep()` **真的呼叫** `sweep_consistent_nodata`"
           "（⛔ 一個沒人叫的函式跟沒寫一樣）",
           "sweep_consistent_nodata" in called, str(sorted(called))[:200])
    finally:
        shutil.rmtree(d11, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # ⑫ ⭐⭐⭐ `avg_close` 的進位規則：**三段**，⛔ 不是「容許 ±0.01」
    #    ⚠ 這幾條全部用**合成**數字（七點第七個：拿現場資料驗判準，
    #      等於把斷言的壽命綁在「那筆資料還在」上）。
    from decimal import Decimal as _DD
    E = O.avg_close_expected
    ck("⑫ ⭐ 上櫃：**無條件捨去**（⛔ 不是四捨五入）",
       E(_DD("4.2999"), 108, "tpex") == _DD("4.29")
       and E(_DD("6.5999"), 104, "tpex") == _DD("6.59"),
       f'{E(_DD("4.2999"), 108, "tpex")}／{E(_DD("6.5999"), 104, "tpex")}')
    ck("⑫ ⭐ 上櫃的規則**不分年**（⛔ 民107 那個分界只作用在上市）",
       E(_DD("4.2999"), 104, "tpex") == E(_DD("4.2999"), 114, "tpex") == _DD("4.29"))
    # ⭐ 真實錨點（1471／民108）：我方均 4.294917… ⇒ 直接四捨五入給 4.29，官方是 4.30
    ck("⑫ ⭐⭐ 上市民107~：先到 3 位再 banker's ⇒ 4.294917… → **4.30**"
       "（⛔ 直接四捨五入會給 4.29）",
       E(_DD("4.294917355371900826"), 108, "twse") == _DD("4.30"),
       str(E(_DD("4.294917355371900826"), 108, "twse")))
    ck("⑫ ⭐⭐ 同一個數字在民104~106 是**另一段** ⇒ **4.29**"
       "（⚠ 分界不對的話這兩條會一起倒）",
       E(_DD("4.294917355371900826"), 106, "twse") == _DD("4.29"),
       str(E(_DD("4.294917355371900826"), 106, "twse")))
    ck("⑫ ⭐ 分界剛好在民107（⛔ 不是 106、也不是 108）",
       O.TPE_ROUND_SWITCH_ROC == 107
       and E(_DD("4.2949"), 107, "twse") == _DD("4.30")
       and E(_DD("4.2949"), 106, "twse") == _DD("4.29"))
    # ⭐⭐ banker's 的**簽名**：帶內（0.45~0.55）進位後的「分」位必定是偶數
    ck("⑫ ⭐⭐ banker's 的簽名：4.294917→4.30（偶）、4.304917→**4.30**（⛔ 不是 4.31）",
       E(_DD("4.304917"), 110, "twse") == _DD("4.30"),
       str(E(_DD("4.304917"), 110, "twse")))
    ck("⑫ ⭐ 而**帶外**兩段給同一個答案（⇒ 只有帶內的格有鑑別力）",
       E(_DD("4.2912"), 106, "twse") == E(_DD("4.2912"), 110, "twse") == _DD("4.29"))
    ck("⑫ ⛔ `market` 傳別的字串要**大聲**丟例外（⛔ 不是靜靜當成上市）",
       _raises(lambda: E(_DD("4.29"), 108, "sii")))
    # ⭐⭐ 四點五那條通則：兩種相反語意的參數，**不可以有預設值**
    import inspect as _i12
    sig12 = _i12.signature(O.avg_close_expected)
    ck("⑫ ⭐⭐ `market` **沒有預設值**（⛔ 預設值＝「照抄語意」那個坑的自動化版本）",
       sig12.parameters["market"].default is _i12.Parameter.empty,
       str(sig12))
    ck("⑫ ⭐ `avg_close_matches()` 逐位比，⛔ 沒有容許值（差 0.01 就是 False）",
       O.avg_close_matches(_DD("4.294917355371900826"), 108, "twse", "4.30")
       and not O.avg_close_matches(_DD("4.294917355371900826"), 108, "twse", "4.29"))
    ck("⑫ ⭐ 這一族**只有一份實作**：`avg_close_matches` 真的走 `avg_close_expected`"
       "（⛔ 不是各自 quantize 一次）",
       "avg_close_expected" in {n.func.id for n in __import__("ast").walk(
           next(x for x in __import__("ast").walk(__import__("ast").parse(io.open(
               os.path.join(HERE, "official_stats.py"), encoding="utf-8").read()))
               if isinstance(x, __import__("ast").FunctionDef)
               and x.name == "avg_close_matches"))
           if isinstance(n, __import__("ast").Call)
           and isinstance(n.func, __import__("ast").Name)})

    # ── ⑫-B ⭐⭐ **月**表的加權均價是**另一欄、另一條規則** ──
    #   ⛔ 它跟上面那個 `avg_close`（收盤價的簡單平均、三段規則）不是同一個量
    #   ——⚠ 兩欄的名字很像（第七點第十個：兩邊的數字都對，而它們不是同一個量）。
    #   ⭐ 這幾格是 2026-09-19 母體級實測（123,847 格）裡**真的那幾格**。
    ck("⑫-B 月均價是**無條件捨去**（1477／民107-11：商 171.4399938892）",
       str(O.monthly_avg_expected(_DD("171.4399938892") * _DD("1000"),
                                  _DD("1000"))) == "171.43")
    ck("⑫-B ⛔ 而官方那一格寫的是 171.44 ⇒ `matches` 要回 **False**"
       "（⚠ 那 45 格**成因不知道**，⛔ 而不知道不可以用容許值蓋掉）",
       not O.monthly_avg_matches(_DD("171.4399938892") * _DD("1000"),
                                 _DD("1000"), "171.44"))
    ck("⑫-B ⭐ 而正常那一格要對得上",
       O.monthly_avg_matches(_DD("25390279924"), _DD("1007670601"), "25.19"),
       str(O.monthly_avg_expected(_DD("25390279924"), _DD("1007670601"))))
    # ⛔ 這一條要**自己接住例外**：不接的話突變會讓整支自測當場中斷，
    #   ⚠ 而「崩潰」跟「這條斷言沒用」在畫面上一模一樣（七點②）。
    try:
        _zero = (O.monthly_avg_expected(1, 0) is None
                 and O.monthly_avg_matches(1, 0, "1.00") is False)
    except Exception as _ex12b:                                     # noqa: BLE001
        _zero = f"⛔ 炸掉了：{type(_ex12b).__name__}"
    ck("⑫-B ⛔ 成交股數是 0 ⇒ 回 None（⚠ 而 `matches` 回 False，⛔ 不是炸掉）",
       _zero is True, f"{_zero}")
    # ⭐⭐ 而「精度不足」那一族被這個反例推翻：2330／民115-5 的商距離下一分
    #   只有 1.86e-09（比那 45 格裡任何一格都近 20 倍）⇒ ⛔ 而官方**捨去**了它。
    #   ⚠ 任何「照相對距離決定要不要進位」的規則都得把它進位 ⇒ 它們全部解釋不了那 45 格。
    ck("⑫-B ⭐⭐ 反例：比那 45 格更接近下一分的那一格，官方**捨去**"
       "（⇒ ⛔ 精度不足那一族解釋不了）",
       O.monthly_avg_matches(_DD("2273.05999577928") * _DD("100000"),
                             _DD("100000"), "2273.05"))
    ck("⑫-B ⭐ 低水位寫下來了（⛔ 只准往下）",
       O.MONTHLY_AVG_RESIDUAL_LOW == 45, str(O.MONTHLY_AVG_RESIDUAL_LOW))
    ck("⑫-B ⭐ 這一族也只有一份實作：`monthly_avg_matches` 真的走 `monthly_avg_expected`",
       "monthly_avg_expected" in {n.func.id for n in __import__("ast").walk(
           next(x for x in __import__("ast").walk(__import__("ast").parse(io.open(
               os.path.join(HERE, "official_stats.py"), encoding="utf-8").read()))
               if isinstance(x, __import__("ast").FunctionDef)
               and x.name == "monthly_avg_matches"))
           if isinstance(n, __import__("ast").Call)
           and isinstance(n.func, __import__("ast").Name)})

    # ═══════════════════════════════════════════════════════════
    # ⒓ ⛔⛔ 「官方說沒有」那一句是**逐市場**的
    #
    # feeds run 167（tpex 月表）實測：5,000 格失敗 1,309，訊息是
    # `monthlyStock stat='查無該筆資料,請重新查詢!!'`
    # ⇒ 而早上幫 twse 修好的那一行比的是 **TWSE** 的話「沒有符合條件的資料」
    # ⇒ ⛔ 那 1,309 格一格都沒被記起來 ⇒ 每一趥都回來 ⇒ **永遠不收斂**。
    # ⭐ 四點五那一族：修好一支、另一支沒跟上，而畫面上看不出來。
    # ═══════════════════════════════════════════════════════════
    d13 = tempfile.mkdtemp(prefix="nodata_")
    try:
        os.makedirs(os.path.join(d13, "stocks"), exist_ok=True)
        # 1111：民108（西元 2019）有 tpex 日檔，民104 沒有
        io.open(os.path.join(d13, "stocks", "1111.csv"), "w",
                encoding="utf-8").write(
            "date,stock_id,market,close\n2019-03-01,1111,tpex,10\n")
        TW = "FMSRFK stat='很抱歉，沒有符合條件的資料!'"
        TP = "monthlyStock stat='查無該筆資料,請重新查詢!!'"
        ck("⒓ ⭐⭐ **tpex** 的那一句話認得出來"
           "（⛔ 這就是 run 167 那 1,309 格掉的地方）",
           O.sweep_consistent_nodata(TP, "1111", 104, "tpex", d13), TP)
        ck("⒓ ⛔ 而**同一句話**在 twse 那邊不算"
           "（⚠ 兩個市場的官方話不一樣）",
           not O.sweep_consistent_nodata(TP, "1111", 104, "twse", d13), TP)
        ck("⒓ ⭐ twse 那一句仍然認得出來（⛔ 不可以改壞舊的）",
           O.sweep_consistent_nodata(TW, "1111", 104, "twse", d13), TW)
        ck("⒓ ⛔ 而我方那一年**有** tpex 日檔 ⇒ 不算「問完了」"
           "（⭐ 兩個條件的「且」沒有因為改逐市場而不見）",
           not O.sweep_consistent_nodata(TP, "1111", 108, "tpex", d13))
        ck("⒓ ⛔⛔ `nodata_mark` 遇到沒登記的市場要**大聲丟例外**"
           "（⚠ 默默套別人那句 ⇒ 掃描永遠不收斂，而畫面正常）",
           _raises(lambda: O.nodata_mark("sii")))
        # ⭐⭐ 四點五那條通則：兩種相反語意的參數不可以有預設值
        import inspect as _i13
        ck("⒓ ⭐⭐ `sweep_consistent_nodata` 的 `market` **沒有預設值**",
           _i13.signature(O.sweep_consistent_nodata)
           .parameters["market"].default is _i13.Parameter.empty)
        ck("⒓ ⭐ 兩個市場都登記了（⛔ 只剩一個就代表有人把語意抄平了）",
           set(O.NODATA_MARK) == {"twse", "tpex"}, str(sorted(O.NODATA_MARK)))
    finally:
        shutil.rmtree(d13, ignore_errors=True)

    # ═══════════════════════════════════════════════════════════
    # ⒔ ⛔ 台帳的**表頭會隨時間增欄** ⇒ 追加時要先把舊表頭升上來
    #
    # `why` 欄是 2026-09-16 早上才加的，而 **tpex 那份台帳是舊表頭**
    # （`stock_id,roc_year,asof`，run 167 寫的 3,691 列）
    # ⇒ 下一趥追加 4 欄的列 ⇒ ⚠ **欄數不齊的 CSV**，
    # ⭐ 而本程式自己讀得下去（只取前兩欄）⇒ ⛔ **沒有任何地方會報錯**。
    # ═══════════════════════════════════════════════════════════
    d14 = tempfile.mkdtemp(prefix="sweephdr_")
    try:
        lp14 = os.path.join(d14, "meta", "_done.csv")
        os.makedirs(os.path.dirname(lp14), exist_ok=True)
        # 舊表頭 ＋ 兩列舊資料（照 run 167 真的形狀）
        io.open(lp14, "w", encoding="utf-8").write(
            "stock_id,roc_year,asof\n1240,107,20260916\n1240,108,20260916\n")
        O.save_sweep_done(lp14, [("2222", "104")], "20260917", why="nodata")
        body14 = io.open(lp14, encoding="utf-8").read()
        rows14 = [r for r in body14.splitlines() if r.strip()]
        ck("⒔ ⭐ 表頭被升上來了",
           rows14[0] == "stock_id,roc_year,asof,why", rows14[0])
        ck("⒔ ⭐⭐ 而舊列**一列都沒少**（四點六：合併不是取代）",
           len(rows14) == 4, str(rows14))
        ck("⒔ ⭐ 舊列補一個**空的** `why`（⛔ 不可以猜它是哪一種）",
           rows14[1] == "1240,107,20260916," and rows14[2] == "1240,108,20260916,",
           str(rows14[1:3]))
        ck("⒔ ⭐ 而新列帶著 `nodata`",
           rows14[3] == "2222,104,20260917,nodata", rows14[3])
        ck("⒔ ⭐ 每一列的欄數一致（⛔ 這就是要防的那件事）",
           len({r.count(",") for r in rows14}) == 1,
           str([r.count(",") for r in rows14]))
        ck("⒔ ⭐ 而 `load_sweep_done` 兩種都讀得到",
           O.load_sweep_done(lp14) == {("1240", "107"), ("1240", "108"),
                                       ("2222", "104")},
           str(sorted(O.load_sweep_done(lp14))))
        # ⭐ 已經是新表頭的不要再動
        ck("⒔ ⛔ 已經是新表頭的 ⇒ 不重寫（回 False）",
           O._upgrade_sweep_header(lp14) is False)
        ck("⒔ ⛔ 檔不存在 ⇒ 也回 False（⚠ 不可以炸）",
           O._upgrade_sweep_header(os.path.join(d14, "meta", "_none.csv")) is False)
    finally:
        shutil.rmtree(d14, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

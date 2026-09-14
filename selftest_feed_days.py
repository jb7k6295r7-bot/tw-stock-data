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
import datetime as _dt3
import io
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

    print("\n── ⑦ `range_note`：⛔ 只問了一部分的那一趟要**自己講出來** ──")
    full = F.range_note("2022-07-01", "2022-07-31", 20)
    part = F.range_note("2022-07-01", "2022-07-31", 1, 1)
    # ⭐ 這一條**沒傳 limit=**，走預設值那條路（CLAUDE.md 第七點第三個陷阱）
    ck("沒帶 --limit ⇒ 不多講（⛔ 每趟都警告會被學會忽略）",
       "limit" not in full and "待處理 20 天" in full, full)
    ck("⛔ 帶了 --limit ⇒ 區塊裡**自己講出**這不是整個區間的結果",
       "--limit 1" in part and "不是整個區間" in part, part)
    ck("★ 反向驗：兩種情形產出的字**真的不同**"
       "（⛔ 一樣的話上面兩條有一條是假的）", full != part)
    # ⛔⛔ 上面三條**測的是判準，不是呼叫點**。突變驗當場證明了這件事：
    #   把呼叫點的 `limit` 拿掉（`range_note(start, end, n)`）⇒ 上面三條**全綠**。
    #   ⚠ 而那正是 Actions 上唯一會走的那條路。⇒ 這一條比**機制**：
    #     `cmd_feed` 裡那個 `range_note(...)` 真的有把第四個引數餵進去。
    import ast as _ast
    with open(os.path.join(HERE, "feeds.py"), encoding="utf-8") as _f:
        _src = _f.read()
    _calls = [n for n in _ast.walk(_ast.parse(_src))
              if isinstance(n, _ast.Call)
              and getattr(n.func, "id", "") == "range_note"]
    ck("★ 呼叫點真的把 `--limit` 餵進 `range_note`"
       "（⛔ 不是比字串——把引數拿掉時上面三條全綠）",
       bool(_calls) and all(len(c.args) >= 4 or c.keywords for c in _calls),
       f"⛔ 掃到 {len(_calls)} 個呼叫，引數個數 "
       f"{[len(c.args) for c in _calls]}")

    print("\n── ⑧ `_why`：錯誤訊息**保留尾巴**（⛔ 可行動的部分在後面）──")
    _ssl = ("URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] "
            "certificate verify failed: unable to get local issuer "
            "certificate (_ssl.c:1000)>")
    _o = F._why(_ssl)
    # ⭐ 這一條沒傳 `cap=`，走預設值那條路（第七點第三個陷阱）
    ck("⛔ 原本的 `err[:50]` 剛好切掉最重要的那一段 ⇒ 現在留得住",
       "unable to get local issuer certificate" in _o, _o)
    ck("★ 反向驗：舊做法（前 50 字）**確實**看不出原因"
       "（⛔ 不然這條斷言是假的）",
       "unable to get local issuer" not in _ssl[:50], _ssl[:50])
    _long = "x" * 400 + "TAIL_MATTERS"
    _c = F._why(_long, cap=60)
    ck("★ 太長時中間省略，⛔ 不砍尾巴",
       len(_c) <= 60 and _c.endswith("TAIL_MATTERS") and "..." in _c, _c)
    ck("★ 短訊息原樣不動（⛔ 不要每一則都加省略號）",
       F._why("短的") == "短的")
    ck("★ 換行被壓成一行（`_last_run.md` 是逐列的）",
       "\n" not in F._why("a\nb\nc"), repr(F._why("a\nb\nc")))
    # ⛔⛔ 上面五條**測的是判準，不是呼叫點**。突變證明過：把呼叫點改回
    #   `err[:50]` ⇒ 上面五條**全綠**。⚠ 而那正是 Actions 上唯一會走的那條路。
    #   （「測了判準沒測呼叫點」今天第四次。）⇒ 這一條比 AST：
    with open(os.path.join(HERE, "feeds.py"), encoding="utf-8") as _f:
        _fs = _f.read()
    import ast as _a2
    _bad = [n for n in _a2.walk(_a2.parse(_fs))
            if isinstance(n, _a2.Subscript)
            and getattr(n.value, "id", "") == "err"]
    ck("★ 原始碼裡**沒有任何** `err[...]` 的切片（⛔ 一律走 `_why()`）",
       not _bad, f"⛔ 還有 {len(_bad)} 處在切 err")

    # ⛔⛔ 2026-09-14：上面那條**只掃 `feeds.py` 一支**。
    #   全 repo 掃過去是 **44 處**在切 `err[:N]`／`note[:N]`
    #   ⇒ 2026-09-13 那次「錯誤訊息不可以砍尾巴」只修了一個檔，其餘從來沒跟上。
    #   ⚠ 實際代價：`mops` 的 `note[:70]` 讓 runlog 上那個 ✗ 只寫「沒回應」、
    #     **沒有原因** ⇒ 憑證鏈壞掉、限流、端點改名在那一行字裡長得一模一樣。
    #
    # ⛔ 而這一條**不可以**寫成「必須是 0」——那會當天就紅、然後被學會忽略
    #   （六點五）。⇒ ⭐ 用**低水位**：只能往下走，退步就紅。
    import glob as _gl
    _LOW = os.path.join(HERE, "data", "meta", "_err_cut_low.txt")
    # ⛔⛔ 名字清單本來是寫死的六個 ⇒ `err2`／`e2`／`e7` **全部逃掉**
    #   （2026-09-14 實測：低水位剛歸零，放寬之後又冒出 6 處）。
    #   ⚠ 一個「看起來已經清乾淨」的閘門，比沒有閘門更容易被相信。
    #   ⇒ ⭐ 改成**名字＋可選數字**的樣式，⛔ 不是一份手抄的清單。
    import re as _re2
    _pat = _re2.compile(r"^(err|note|msg|why|reason|e)\d*$")
    _cuts = []
    for _p in sorted(_gl.glob(os.path.join(HERE, "*.py"))):
        if os.path.basename(_p).startswith("selftest_"):
            continue          # ⚠ 自測裡切 note 是在做斷言，不是在報錯誤
        try:
            _t = _a2.parse(io.open(_p, encoding="utf-8").read())
        except SyntaxError:
            continue
        for _n in _a2.walk(_t):
            if (isinstance(_n, _a2.Subscript)
                    and _pat.match(getattr(_n.value, "id", "") or "")
                    and isinstance(_n.slice, _a2.Slice)):
                _cuts.append(f"{os.path.basename(_p)}:{_n.lineno}")
    # ⭐ 讀寫**只有一份實作**（`lowwater.py`，CLAUDE.md 四點五第九次）。
    #   ⛔ 這一支沒有 `rl` ⇒ 走 read/write，不走 `gate()`。
    #   ⚠ 方向是 `DOWN`：砍尾巴的地方越少越好。
    import lowwater as _LW
    _lo, _loday = _LW.read(_LOW, _LW.DOWN)
    if _lo is None:
        print(f"  ⚠⚠ **這一層沒跑**：沒有 `_err_cut_low.txt`（本趟 {len(_cuts)} 處）"
              "　⇒ ⛔ 不算失敗，⛔ 也不算驗過")
    else:
        ck(f"⭐⭐ 全 repo 砍錯誤訊息尾巴的地方**沒有變多**（低水位 {_lo} 處，{_loday}）",
           _LW.ok(len(_cuts), _lo, _LW.DOWN), f"本趟 {len(_cuts)} 處：{_cuts[:6]}")
    _did, _new = _LW.write(_LOW, len(_cuts), _LW.DOWN)
    if _did and _lo is not None:
        print(f"  ⭐ 低水位下修 {_lo} → {_new} 處")

    print("\n── ⑨ `IncompleteRead`：訊息要**自己講出它是傳輸被切斷** ──")
    # ⭐ 2026-09-13 實測：TPEx 的 openapi/swagger.json（452 KB）連兩次只讀到 24 KB。
    #   ⛔ 原本的訊息只有 `IncompleteRead: IncompleteRead(24064 bytes read, ...)`
    #     ——它跟「這個端點不能用」長得一模一樣，⚠ 而它其實重試就會好。
    #   ⇒ 這一族跟 ⑧ 是同一條規矩：**可行動的部分要留在訊息裡**。
    import http.client as _hc
    import urllib.request as _ur
    import backfill as _B
    _orig = _ur.urlopen

    class _Boom:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            raise _hc.IncompleteRead(b"x" * 24064, 452859)

    try:
        _ur.urlopen = lambda *a, **k: _Boom()
        _raw, _err = _B.get("https://example.invalid/x.json", retries=1, timeout=1)
    finally:
        _ur.urlopen = _orig
    ck("⭐ 訊息講出這是**傳輸被切斷**，⛔ 不是端點壞掉",
       _err is not None and "傳輸被切斷" in _err, str(_err))
    ck("⭐ 而且把「已讀多少／還差多少」帶出來（⇒ 看得出是不是只讀到零頭）",
       _err is not None and "24,064" in _err and "452,859" in _err, str(_err))
    # ⛔ 反向：Python 原本的字串**看不出**這兩件事
    _plain = f"{_hc.IncompleteRead(b'x' * 24064, 452859)!r}"
    ck("★ 反向驗：Python 原本那串裡沒有「傳輸被切斷」（⛔ 不然上面兩條是假的）",
       "傳輸被切斷" not in _plain, _plain[:80])

    # ⭐⭐ 而真正該分開的是這兩種——⛔ 只留最後一次的話它們長得一模一樣：
    #     每次都停在**同一個 byte 數** ⇒ 決定性（重試永遠不會好）
    #     每次不一樣                   ⇒ 偶發（重試有意義）
    #   ⚠ 而處置相反：前者要改路（換參數／換來源），後者只要重試。
    def _boomseq(sizes):
        it = iter(sizes)

        class _B2:
            def __enter__(self):
                self.n = next(it)
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                raise _hc.IncompleteRead(b"x" * self.n, 476923 - self.n)
        return _B2

    try:
        _ur.urlopen = lambda *a, _c=_boomseq([24064, 24064]), **k: _c()
        _, _e1 = _B.get("https://example.invalid/y", retries=2, timeout=1)
        _ur.urlopen = lambda *a, _c=_boomseq([24064, 133700]), **k: _c()
        _, _e2 = _B.get("https://example.invalid/y", retries=2, timeout=1)
    finally:
        _ur.urlopen = _orig
    ck("⭐ 兩次都停在同一個 byte 數 ⇒ 訊息要說**決定性、重試不會好**",
       _e1 is not None and "決定性" in _e1, str(_e1))
    ck("⭐ 兩次停在不同位置 ⇒ 訊息要說**重試通常會好**（⛔ 不可以說決定性）",
       _e2 is not None and "決定性" not in _e2 and "傳輸被切斷" in _e2, str(_e2))
    ck("⭐ 而兩者都要把**每一次**讀到多少列出來（⛔ 只留最後一次就分不出來）",
       _e1 is not None and _e1.count("24,064") >= 2
       and _e2 is not None and "133,700" in _e2 and "24,064" in _e2)

    # ⛔⛔ 而上面那些假回應**每一個都帶了 expected**——⚠ 真回應不一定有。
    #   chunked 傳輸斷在「下一塊的長度」那一行時，Python 丟的是
    #   `IncompleteRead(b'')`，`expected` 是 **None** ⇒ `f"{None:,}"` ⇒ TypeError
    #   ⇒ ⛔ 這個**錯誤處理自己炸掉** ⇒ 例外沒被轉成錯誤字串 ⇒ 不重試、整支當場結束。
    #   ⚠ 代價（2026-09-14 feeds run 143）：otcmargin 回補十二年**每一年**都只跑了
    #     8~9 天就掛，2,850 天只補到 86 天，⛔ 而每一年都照樣 push、看起來有在跑。
    #   ⭐ 教訓就是第七點那句：**假回應比真回應簡單，等於那段沒測。**
    class _BoomNone:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            raise _hc.IncompleteRead(b"x" * 56326)     # ⚠ 不帶 expected

    ck("⭐ 前提：不帶 expected 時 Python 真的給 None（⛔ 否則下面那條測不到東西）",
       _hc.IncompleteRead(b"x" * 3).expected is None)
    try:
        _ur.urlopen = lambda *a, **k: _BoomNone()
        _, _e3 = _B.get("https://example.invalid/z", retries=1, timeout=1)
        _crash = None
    except TypeError as _ex:
        _e3, _crash = None, f"⛔ 錯誤處理自己炸了：{_ex}"
    finally:
        _ur.urlopen = _orig
    ck("⛔⛔ `expected is None` 時**不可以崩潰**——要回一個錯誤字串"
       "（⚠ 崩潰 ⇒ 不重試 ⇒ 整趟回補當場結束）",
       _crash is None and _e3 is not None, _crash or "回了 None")
    ck("⭐ 而訊息要講出「對方沒說還差多少」，⛔ 不是印一個假的數字",
       _e3 is not None and "傳輸被切斷" in _e3 and "沒說還差多少" in _e3,
       str(_e3))
    # ⚠ 這一條要比「**已讀** 56,326」整串——⛔ 只比 "56,326" 會被
    #   後面「各次讀到 ['56,326']」那一段撐著，於是拿掉「已讀」那一格照樣全綠
    #   （突變 N3 實測）。
    ck("⚠ 已讀的位元數照樣要在（⛔ 那是唯一還剩下的量）",
       _e3 is not None and "已讀 56,326" in _e3, str(_e3))
    _calls = [n for n in _a2.walk(_a2.parse(_fs))
              if isinstance(n, _a2.Call) and getattr(n.func, "id", "") == "_why"]
    ck("★ 而 `_why()` 真的有被呼叫", len(_calls) >= 1,
       f"⛔ 呼叫 {len(_calls)} 次")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

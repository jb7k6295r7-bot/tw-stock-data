#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_odd_lot_share.py — 驗 `odd_lot_share.py` 的分格與分母。

## ⛔ 為什麼這一支要用**合成**資料

`odd_lot_share.py` 要回答的是「那三個百分比為什麼不一樣」，而答案是**母體**。
⇒ ⚠ 若拿現場 `data/stocks/` 來驗，斷言就會寫成「twse 全庫大約 89.9%」
  ——⛔ 而那個數字會隨掛牌結構變（新的權證一上市就動），
  ⇒ 那條斷言的壽命等於「今天的比例剛好是這個數」（CLAUDE.md 七點⑦）。
⭐ 所以判準本身一律拿合成數字驗（環境無關），現場資料只用來驗**呼叫點真的那樣叫**。

## ⛔ 沙箱：兩個旋鈕都要導走，而且每一個都要有一條「★ 沒有動到 repo 真的 ___」

⚠ `OUT` 與 `runlog.PATH` 是兩個獨立的旋鈕（七點⑤那一族：漏導一個是常態）
⇒ 每一個各釘一條逐位元比對的斷言。
"""
import io
import os
import shutil
import sys
import tempfile

import odd_lot_share as O
import runlog

FAIL = []
N = [0]


def ck(label, cond, note=""):
    N[0] += 1
    print(f"  {'✓' if cond else '✗'} {label}" + (f"｜{note}" if note else ""))
    if not cond:
        FAIL.append(label)


def _write(d, sid, rows):
    """rows: (date, market, volume)。⚠ 欄位順序照真檔（date 在第 1 欄）。"""
    with io.open(os.path.join(d, f"{sid}.csv"), "w", encoding="utf-8") as f:
        f.write("date,sid,name,market,open,high,low,close,volume\n")
        for date, mk, vol in rows:
            f.write(f"{date},{sid},X,{mk},1,1,1,1,{vol}\n")


def _fixture(d):
    """⭐ 一組**答案自己算得出來**的合成資料。

        2330  twse 個股    4 天：整張 3／零股 1     （2 天在分界前、2 天在分界後）
        0050  twse ETF     2 天：整張 1／零股 1
        06xxxL twse 權證   2 天：整張 2／零股 0     ⇒ ⛔ 權證是**拉低**比例的那一族
        1234  tpex→twse    2 天：整張 1／零股 1     ⇒ 轉板（market 欄變過）
        9999  twse 個股    2 天：**volume = 0**     ⇒ ⛔ 一天都不可以被數到
    """
    _write(d, "2330", [("2019-01-02", "twse", 3000), ("2019-01-03", "twse", 1234),
                       ("2021-01-04", "twse", 2000), ("2021-01-05", "twse", 5000)])
    _write(d, "0050", [("2019-01-02", "twse", 1000), ("2021-01-04", "twse", 77)])
    _write(d, "06001L", [("2019-01-02", "twse", 1000), ("2021-01-04", "twse", 2000)])
    _write(d, "1234", [("2019-01-02", "tpex", 1000), ("2021-01-04", "twse", 555)])
    _write(d, "9999", [("2019-01-02", "twse", 0), ("2021-01-04", "twse", 0)])


def main():
    print("== selftest_odd_lot_share ==")
    tmp = tempfile.mkdtemp(prefix="odd_lot_")
    src = os.path.join(tmp, "stocks")
    os.makedirs(src)
    _fixture(src)

    cells, n_files, transfer, span = O.scan(src)

    # ① 回傳形狀要從**回來的東西**量，⛔ 不是從 docstring 讀（七點⑪）。
    ck("scan 回四個東西", len((cells, n_files, transfer, span)) == 4)
    ck("母體是檔數，⛔ 不是有成交的檔數", n_files == 5, f"{n_files}")

    # ② ⛔ volume == 0 的那兩天一天都不可以被數到。
    tw = cells[("twse", "all", "all")]
    ck("twse 只數有成交的日子", tw[0] == 9, f"{tw[0]} 天（9999 那 2 天要被排除）")
    # ⚠ 3 筆：2330 的 1,234／0050 的 77／1234 轉板後那天的 555。
    ck("twse 非千倍數 3 天", tw[1] == 3, f"{tw[1]}")

    # ③ 分界前後要各自算，⛔ 不是拿全期去套。
    ck("分界之前 4 天／1 筆零股", cells[("twse", "era", "before")] == [4, 1],
       f"{cells[('twse', 'era', 'before')]}")
    ck("分界之後 5 天／2 筆零股", cells[("twse", "era", "after")] == [5, 2],
       f"{cells[('twse', 'era', 'after')]}")

    # ④ ⭐ 這一條就是 #29 的病根：權證是**拉低**比例的那一族
    #    ⇒ 任何「挑長歷史的股票」的抽法把它抽掉 ⇒ 數字必然偏高。
    ck("權證那一格 0／2（⛔ 它會拉低全庫比例）",
       cells[("twse", "shape", "warrant")] == [2, 0])
    ck("ETF 那一格 1／2", cells[("twse", "shape", "etf")] == [2, 1])
    # ⭐ 5 天：2330 那 4 天 ＋ **1234 轉板到 twse 之後**那一天
    #   （⛔ 轉板的檔不是另一族，它逐列各自記在當天的市場）
    ck("個股那一格 2／5", cells[("twse", "shape", "stock")] == [5, 2],
       f"{cells[('twse', 'shape', 'stock')]}")

    # ⑤ 轉板要用**資料自己**（`market` 欄變過），⛔ 不是去 delisted.csv 查。
    ck("轉板抓到 1234", transfer == {"1234"}, f"{sorted(transfer)}")
    ck("轉板的那兩天**分別**記在各自的市場",
       cells[("tpex", "moved", "transfer")][0] == 1
       and cells[("twse", "moved", "transfer")][0] == 1)

    # ⑥ 代號形狀：⛔ 它不是官方證券種類欄。
    ck("shape_of 三種", (O.shape_of("0050"), O.shape_of("06001L"),
                        O.shape_of("2330")) == ("etf", "warrant", "stock"))

    # ⑦ ⭐ 區間要從**有成交的列**來。⚠ 而這一條要標出它**驗不到**什麼：
    #    fixture 裡 volume=0 的那兩天剛好落在區間內 ⇒ ⛔ 這條斷言分不出
    #    「有沒有把 0 成交的列算進區間」——那一件事是上面②在守的。
    ck("span 是有成交的最早與最晚", span == ("2019-01-02", "2021-01-05"), f"{span}")

    # ⑧ 驗終點：報表裡真的印得出那兩個日期與那幾格。
    txt = O.report(cells, n_files, transfer, span)
    ck("報表自己講出它量到哪一段", "2019-01-02" in txt and "2021-01-05" in txt)
    ck("報表印得出全庫那一格", "⭐ 全期" in txt)
    ck("報表逐市場各印一節", "## twse" in txt and "## tpex" in txt)

    # ⑨ 沙箱：兩個旋鈕各導一次，然後**各釘一條沒動到 repo 真的那一份**。
    #    ⚠ 用 `O.OUT`／`runlog.PATH`（Attribute），⛔ 不是裸名字
    #    ——`selftest_lowwater.py` ⑨ 掃的就是裸名字。
    before_out = (io.open(O.OUT, "rb").read() if os.path.exists(O.OUT) else None)
    before_log = (io.open(runlog.PATH, "rb").read()
                  if os.path.exists(runlog.PATH) else None)
    saved = (O.SRC, O.OUT, runlog.PATH)
    try:
        O.SRC = src
        O.OUT = os.path.join(tmp, "out.txt")
        runlog.PATH = os.path.join(tmp, "_last_run.md")
        rc = O.main()
        ck("沙箱跑一趟回 0", rc == 0, f"rc={rc}")
        ck("★ 沙箱的 out.txt 真的被寫出來", os.path.exists(O.OUT))
        sand = io.open(O.OUT, encoding="utf-8").read()
        # ⭐ 呼叫點要驗**行為**，⛔ 不是掃原始碼字串（七點⑧：那幾個字註解裡也有一份）
        #   ⇒ `main()` 自己跑出來的那一份，要跟 `report(scan(...))` 逐位元相同。
        want = O.report(cells, n_files, transfer, span)
        body = "\n".join(sand.splitlines()[2:])
        ck("main 寫出去的那一份 == report(scan()) 的本文（⛔ 只差時戳那兩行）",
           body.strip() == "\n".join(want.splitlines()[2:]).strip())
        ck("沙箱那一份含區間", "2021-01-05" in sand)
    finally:
        O.SRC, O.OUT, runlog.PATH = saved
    after_out = (io.open(O.OUT, "rb").read() if os.path.exists(O.OUT) else None)
    after_log = (io.open(runlog.PATH, "rb").read()
                 if os.path.exists(runlog.PATH) else None)
    ck("★ 沒有動到 repo 真的 _odd_lot_share.txt", before_out == after_out)
    ck("★ 沒有動到 repo 真的 _last_run.md", before_log == after_log)

    # ⑪ ⭐ 四點六那道閘門：**比較舊的一份不可以蓋掉比較新的**。
    #    ⚠ 驗的是**終點**（那個檔的內容有沒有被換掉），⛔ 不是「有沒有印那句話」。
    saved = (O.SRC, O.OUT, runlog.PATH)
    try:
        O.SRC = src
        O.OUT = os.path.join(tmp, "gate.txt")
        runlog.PATH = os.path.join(tmp, "_gate_log.md")
        # 先放一份「量到 2099-12-31」的既有輸出（＝ main 上比較新的那一份）
        newer = O.report(cells, n_files, transfer, ("2019-01-02", "2099-12-31"))
        io.open(O.OUT, "w", encoding="utf-8").write(newer)
        ck("span_of 讀得回既有那一份的最後一天",
           O.span_of(newer) == "2099-12-31", f"{O.span_of(newer)}")
        rc2 = O.main()
        ck("退步的那一趟要 ✗（rc != 0）", rc2 != 0, f"rc={rc2}")
        ck("★ 而且那個檔**一個字都沒被改**",
           io.open(O.OUT, encoding="utf-8").read() == newer)
        # 反向：既有那一份比較舊 ⇒ 照常覆蓋（⛔ 這道閘門不可以變成「永遠不寫」）
        older = O.report(cells, n_files, transfer, ("2019-01-02", "2019-06-30"))
        io.open(O.OUT, "w", encoding="utf-8").write(older)
        rc3 = O.main()
        ck("既有那一份比較舊 ⇒ 照常覆蓋", rc3 == 0 and O.span_of(
            io.open(O.OUT, encoding="utf-8").read()) == "2021-01-05", f"rc={rc3}")
        # ⚠ 第一次跑（檔還不在）也要放行——⛔ 不可以把「沒有前一份」讀成退步
        os.remove(O.OUT)
        ck("第一次跑（沒有前一份）要放行", O.main() == 0)
    finally:
        O.SRC, O.OUT, runlog.PATH = saved

    # ⑩ 有預設值的參數，一定要有一條**不傳它**的斷言（七點③）。
    #    ⚠ `report(..., span=(None, None))` 是 `scan()` 回不出日期時會走的那條路
    #    ⇒ 它不可以炸掉，而且**不可以印出一個看起來像真的區間**。
    bare = O.report(cells, n_files, transfer)
    ck("report 不傳 span 也要印得出來，而且那一格是 —", "**— ~ —**" in bare)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"通過 {N[0] - len(FAIL)}｜失敗 {len(FAIL)}")
    for f in FAIL:
        print(f"  ✗ {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

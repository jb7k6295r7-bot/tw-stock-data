#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`neighbor_floor` 與 `feed_rowcount_check` 的自測。**不連網、不碰真的 data/。**

⭐ 這一支要釘的是那個**最容易變成擺設**的性質：
⛔ 一道天天紅的閘門，跟沒有那道閘門一樣——所以「誤報 0」跟「抓得到」同樣重要。
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import neighbor_floor as NF                                    # noqa: E402
import feed_rowcount_check as FC                               # noqa: E402

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
    print("=" * 64)
    print("neighbor_floor：跟鄰近同類比數量（不連網）")
    print("=" * 64)

    print("\n── ① 判準本體 ──")
    ck("⭐ 真的塌掉會被抓到（2026-08_twse 123 列 vs 鄰月 992）",
       NF.is_short(123, [992] * 6)[0])
    ck("正常的一天不會被抓", not NF.is_short(992, [992] * 6)[0])
    ck("剛好在門檻上（＝med×floor）**不算**塌（⛔ 邊界要往寬的那邊）",
       not NF.is_short(500, [1000] * 6)[0], str(NF.is_short(500, [1000] * 6)))
    ck("低於門檻一點點就算塌", NF.is_short(499, [1000] * 6)[0])

    print("\n── ② ⛔ 「不判」跟「判過沒事」必須分得開 ──")
    short, med, why = NF.is_short(1, [2] * 6)
    ck("量太小 ⇒ 不判，而且**講得出為什麼**", not short and why and "量太小" in why, why)
    short, med, why = NF.is_short(5, [100, 100])
    ck("鄰居太少 ⇒ 不判，而且講得出為什麼", not short and why and "鄰居" in why, why)
    ck("⭐ 而正常那條路的 `why` 是空的（⛔ 否則呼叫端分不出兩者）",
       NF.is_short(992, [992] * 6)[2] == "")

    print("\n── ③ `neighbors`：取序列上的鄰居，⛔ 不含自己 ──")
    seq = list(range(10))
    ck("中間：前後各 3 個、不含自己", NF.neighbors(seq, 4) == [1, 2, 3, 5, 6, 7],
       str(NF.neighbors(seq, 4)))
    ck("最前面：只有右邊", NF.neighbors(seq, 0) == [1, 2, 3], str(NF.neighbors(seq, 0)))
    ck("最後面：只有左邊", NF.neighbors(seq, 9) == [6, 7, 8], str(NF.neighbors(seq, 9)))
    ck("⛔ 自己一定不在鄰居裡（否則塌掉的那天會把自己的中位數拉下來）",
       all(4 not in [i for i in NF.neighbors(list(range(n)), 4)] or True
           for n in (6, 10, 20))
       and 4 not in NF.neighbors(seq, 4))

    print("\n── ④ ⭐ 有預設值的參數，要有一條**不傳它**的斷言（第七點③）──")
    ck("不傳 floor ⇒ 用 FLOOR（0.5）", NF.is_short(499, [1000] * 6)[0]
       and not NF.is_short(501, [1000] * 6)[0])
    ck("不傳 min_median ⇒ 用 MIN_MEDIAN（30）",
       NF.is_short(1, [29] * 6)[2] != "" and NF.is_short(1, [31] * 6)[2] == "",
       f"{NF.is_short(1, [29] * 6)}｜{NF.is_short(1, [31] * 6)}")
    ck("不傳 k ⇒ `neighbors` 用 K（6）", len(NF.neighbors(list(range(50)), 25)) == 6)

    print("\n── ⑤ 週六（補行交易日）──")
    ck("2016-06-04 是週六", FC.is_saturday("2016-06-04"))
    ck("2016-06-03 不是", not FC.is_saturday("2016-06-03"))
    ck("⛔ 壞掉的日期字串不會爆", not FC.is_saturday("not-a-date"))

    print("\n── ⑥ `scan_feed`：⭐ 週六要另計、⛔ 不可以算成殘缺 ──")
    d = tempfile.mkdtemp(prefix="nf_")
    try:
        def put(day, n):
            io.open(os.path.join(d, f"{day}.csv"), "w", encoding="utf-8").write(
                "a,b\n" + "".join("1,2\n" for _ in range(n)))
        # 2016-06-01 ~ 06-08 都當交易日；06-04 是週六
        for day in ("2016-06-01", "2016-06-02", "2016-06-03",
                    "2016-06-06", "2016-06-07", "2016-06-08", "2016-06-09"):
            put(day, 400)
        put("2016-06-04", 100)                  # ⭐ 週六，列數低
        bad, st = FC.scan_feed(d)
        ck("週六列數低 ⇒ 進「週六（另計）」，⛔ 不算疑似殘缺",
           st["週六（另計）"] == 1 and st["疑似殘缺"] == 0 and not bad, str(st))
        # 換成平日同樣低 ⇒ 一定要抓到
        os.remove(os.path.join(d, "2016-06-04.csv"))
        put("2016-06-04", 400)
        put("2016-06-07", 100)                  # 週二
        bad, st = FC.scan_feed(d)
        ck("⭐ 同樣的列數落在平日 ⇒ **一定要抓到**（⛔ 否則週六那條是在放水）",
           st["疑似殘缺"] == 1 and bad and bad[0]["date"] == "2016-06-07", str(st))
        # ⛔ 這裡不可以直接 bad[0]：上一條紅的時候 bad 是空的 ⇒ IndexError
        #   ⇒ 整支測試當場中斷、後面一條都不會跑（CLAUDE.md 第七點第二個陷阱）
        first = bad[0] if bad else {}
        ck("　　而它記下了鄰近中位數與比值",
           first.get("neighbor_median") == "400"
           and first.get("ratio", "").startswith("0.25"), str(first))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ⑦ `day_rows`：扣表頭、讀不到不爆 ──")
    d = tempfile.mkdtemp(prefix="nf2_")
    try:
        io.open(os.path.join(d, "x.csv"), "w", encoding="utf-8").write("h\n1\n2\n3\n")
        ck("3 列資料（扣掉表頭）", FC.day_rows(os.path.join(d, "x.csv")) == 3)
        io.open(os.path.join(d, "e.csv"), "w", encoding="utf-8").write("h\n")
        ck("只有表頭 ⇒ 0，⛔ 不是 −1", FC.day_rows(os.path.join(d, "e.csv")) == 0)
        ck("⛔ 檔不存在 ⇒ None，不爆", FC.day_rows(os.path.join(d, "nope.csv")) is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n⑧ ⭐⭐ `level`：決定「判不判」的量不可以是鄰居自己（2026-09-14 誤報）")
    # ⛔ 實測：fulldelivery（變更交易名單）全期 2,850 天有 2,798 天 ≤ 25 列，
    #   而 2020-08-10／08-17 名單暫時漲到 ~70 ⇒ 鄰近中位數被推過 30
    #   ⇒ 旁邊那兩天的 **21 列（＝常態）** 被判成「塌掉」。
    #   ⭐ 病根：一支 feed **只在自己波動最大的時候才被納入判定**。
    _peers = [70, 68, 70, 21, 22, 21]        # 鄰近中位數 45（被尖峰推上去）
    _short_old, _med_old, _why_old = NF.is_short(21, _peers)
    ck("  ⛔ 舊行為（不傳 level）：21 列被判成塌掉　⇒ 這一節不是憑空擔心",
       _short_old and not _why_old, f"short={_short_old}｜med={_med_old}｜{_why_old}")
    _short, _med, _why = NF.is_short(21, _peers, level=20)
    ck("  ⭐ 傳全期水位 20 ⇒ **不判**（⛔ 不是判成沒事）",
       not _short and "全期中位數" in _why, f"short={_short}｜{_why}")
    ck("  ⚠ 而不判的理由要講出是**哪一個**中位數太小（⛔ 兩者處置不同）",
       "全期中位數 20" in _why, _why)
    # ⛔ 反向：真正的大 feed 不可以因此變得判不動
    ck("  ⭐ 反向：全期水位夠大的 feed **照樣判得到**"
       "（⛔ 否則這個修法等於把閘門關掉）",
       NF.is_short(123, [992] * 6, level=990)[0])
    ck("  ⚠ 而 level 只管「判不判」，**比大小仍然跟鄰近中位數比**"
       "（⛔ 家數十一年會長，拿全期中位數比會讓舊期別門檻太高）",
       not NF.is_short(500, [1000] * 6, level=200)[0]
       and NF.is_short(499, [1000] * 6, level=200)[0])
    # ⭐ 有預設值的參數，要有一條不傳它的斷言（第七點③）——上面 `_short_old` 就是
    # ⛔ 而呼叫點有沒有真的傳：掃原始碼（這是第九次）
    import io as _io2
    _src = _io2.open("feed_rowcount_check.py", encoding="utf-8").read()
    ck("  ⭐⭐ `feed_rowcount_check` 真的把全期水位傳進去了",
       "level=level" in _src and "statistics.median(_lv)" in _src,
       "⛔ 呼叫點沒有傳 level")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

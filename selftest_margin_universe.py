#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_margin_universe.py — 釘住「逐日成員 → 逐檔區間」的四個判準。

⭐⭐ 最重要的是第 ③ 節：**合成一個崩塌日**，證明「不可判定」那道守門真的會抓。
⚠ 實跑時它抓到 **0 天** ⇒ ⛔ 而「0」在報告裡會被讀成「資料乾淨」，
除非有人證明過那個判準抓得到東西（CLAUDE.md 第七點）。

⚠ 而**負控同樣重要**：標的數十一年半從 880 長到 1,297，
⛔ 一個把「緩慢成長」也當成崩塌的守門，會把早年那一整段全部標成不可判定
——⭐ 那比沒有守門更糟：它會**刪掉真的歷史**。

假資料照真資料的形狀做：檔名是日期、有 `stock_id` 欄、成員逐日緩慢增加。
"""
import csv
import io
import os
import shutil
import sys
import tempfile

import margin_universe as M

_ok = _bad = 0


def ck(name, cond, detail=""):
    global _ok, _bad
    if cond:
        _ok += 1
        print(f"  ok   {name}")
    else:
        _bad += 1
        print(f"  ✗    {name}　{detail}")


def build(d, days, members):
    for i, day in enumerate(days):
        with io.open(os.path.join(d, f"{day}.csv"), "w", encoding="utf-8") as f:
            f.write("date,stock_id,m_buy,m_sell,m_balance\n")
            for c in members(i):
                f.write(f"{day},{c},1,2,3\n")


def main():
    sand = tempfile.mkdtemp(prefix="mgu_")
    try:
        d = os.path.join(sand, "margin")
        os.makedirs(d)
        days = [f"2026-01-{i:02d}" for i in range(1, 31)]
        COLLAPSE = 14          # 索引（第 15 天）
        GAP = (19, 20, 21)     # 第 20~22 天：c005 **真的**不在表上
        #   ⚠ 一定要挑**一開始就在**的代號：第一版挑了 `c019`，
        #     而它要到第 21 天（n 長到 20）才第一次出現 ⇒ 那個「缺席」根本不存在，
        #     ⛔ 三條斷言一起紅。**假資料的形狀錯了，不是程式錯了。**

        def members(i):
            # ⚠ 緩慢成長：10 檔起、每兩天多一檔（⛔ 這是負控，不可以被判成崩塌）
            n = 10 + i // 2
            ids = [f"c{k:03d}" for k in range(n)]
            if i == COLLAPSE:              # ⭐ 正例：整批只剩三檔
                return ids[:3]
            if i in GAP:                   # 真的成員變動
                return [c for c in ids if c != "c005"]
            return ids

        build(d, days, members)
        sets = M.day_sets(d)
        ck("讀得到 30 天", len(sets) == 30, str(len(sets)))

        print("── ① 不可判定的日子 ──")
        bad = M.suspect_days(sets, 0.7)
        ck("⭐ 合成的崩塌日**確實**被抓到（正例 1 天）",
           set(bad) == {days[COLLAPSE]}, str(sorted(bad)))
        ck("⭐ 負控：緩慢成長的那 29 天**一天都沒有**被誤判",
           len(bad) == 1, f"抓到 {sorted(bad)}")

        print("── ② 區間：跨過不可判定的那天 ──")
        sp = M.spans(sets, skip=set(bad))
        # ⚠ 挑 `c009`：它在崩塌日**不在**那三檔裡（⇒ 不跳過就會被切成兩段），
        #   ⛔ 而 `c000` 崩塌日還在 ⇒ 拿它當例子等於沒測到「跨過」。
        c9 = [x for x in sp if x[0] == "c009"]
        ck("⭐⭐ `c009` 只有**一段**（區間跨過崩塌日，⛔ 不在那裡斷開）",
           len(c9) == 1, str(c9))
        ck("　那一段從第一天到最後一天",
           c9 and c9[0][1] == days[0] and c9[0][2] == days[-1], str(c9))
        ck("　⛔ 而它的天數是 **29**（崩塌日整天不參與，既不算在也不算不在）",
           c9 and c9[0][3] == 29, str(c9))

        print("── ③ 區間：真的成員變動要斷開 ──")
        c5 = [x for x in sp if x[0] == "c005"]
        ck("⭐ `c005` 真的離開三天 ⇒ **兩段**", len(c5) == 2, str(c5))
        ck("　第一段在缺席前結束（2026-01-19）",
           c5 and c5[0][2] == "2026-01-19", str(c5))
        ck("　第二段在回來那天開始（2026-01-23）",
           len(c5) == 2 and c5[1][1] == "2026-01-23", str(c5))

        print("── ④ 天數總和 ＝ 真的出現的天數（終點斷言）──")
        from collections import Counter
        seen, got = Counter(), Counter()
        for day, ids, _tot in sets:
            if day in bad:
                continue
            for c in ids:
                seen[c] += 1
        for c, _s, _e, n in sp:
            got[c] += n
        ck("⭐ 逐檔逐格相同", got == seen,
           str([k for k in seen if seen[k] != got.get(k)][:5]))

        print("── ⑤ ⛔ 反向：不跳過崩塌日會怎樣 ──")
        sp_bad = M.spans(sets, skip=set())
        n_seg = len(sp_bad)
        ck("⭐ 不跳過 ⇒ 段數**暴增**（假的「集體移除又集體回來」）",
           n_seg > len(sp) + 10, f"跳過 {len(sp)} 段／不跳過 {n_seg} 段")
        c9_bad = [x for x in sp_bad if x[0] == "c009"]
        ck("　⛔ 而 `c009` 這種從頭在到尾的也會被切成兩段",
           len(c9_bad) == 2, str(c9_bad))

        print("── ⑥ 讀不到／空的檔不可以被當成空集合 ──")
        io.open(os.path.join(d, "2026-01-31.csv"), "w",
                encoding="utf-8").write("date,stock_id,m_buy,m_sell,m_balance\n")
        sets2 = M.day_sets(d)
        ck("⛔ 只有表頭的檔**不列入**（否則它會生出一整批假的移除）",
           len(sets2) == 30 and sets2[-1][0] == days[-1],
           f"{len(sets2)} 天，最後 {sets2[-1][0] if sets2 else '—'}")

        print("── ⑦ ⭐ 成員是**子集**時（`chtm.halted`）：判準看的是總列數 ──")
        # ⚠ 這一節是 2026-09-11 加的：同一組函式要壓 `chtm` 的 `halted` 欄，
        #   ⛔ 而那裡的成員只是整檔的一小撮（每天約 20 列裡 3~6 檔停止交易）
        #   ⇒ 「成員數少」是**正常**的，⛔ 拿它當故障判準會天天誤判。
        d2 = os.path.join(sand, "chtm")
        os.makedirs(d2, exist_ok=True)
        for i, day in enumerate(days):
            # 每天 20 列（⛔ 第 15 天故意只剩 4 列 ＝ 真的抓壞了）
            n = 4 if i == 15 else 20
            lines = ["date,stock_id,name,halted"]
            for k in range(n):
                # ⭐ 停止交易的只有 c000~c002，而**第 7 天一檔都沒有**
                h = 1 if (k < 3 and i != 7) else 0
                lines.append(f"{day},c{k:03d},n{k},{h}")
            io.open(os.path.join(d2, day + ".csv"), "w",
                    encoding="utf-8").write("\n".join(lines) + "\n")
        hs = M.day_sets(d2, keep=lambda r: r.get("halted") == "1")
        ck("⭐ 成員**空的**那一天照樣收進來（⛔ 丟掉就會開一個假的洞）",
           len(hs) == 30, f"{len(hs)} 天（應該 30）")
        empt = [x for x in hs if not x[1]]
        ck("　⚠ 而它確實是空的（正例 1 天：第 7 天沒有人停牌）",
           len(empt) == 1 and empt[0][0] == days[7], str([x[0] for x in empt]))
        hbad = M.suspect_days(hs, 0.7)
        ck("⭐⭐ 不可判定只抓到**第 15 天**（總列數 4／20），"
           "⛔ 沒有把「沒人停牌」的第 7 天判成故障",
           set(hbad) == {days[15]}, f"抓到 {sorted(hbad)}")
        hsp = M.spans(hs, skip=set(hbad))
        c0 = [x for x in hsp if x[0] == "c000"]
        ck("⛔ 而 c000 在第 7 天**真的**不在 ⇒ 停牌區間要斷成兩段"
           "（⚠ 那是真的成員變動，不是故障）",
           len(c0) == 2, str(c0))

        print("── ⑧ `halt_spans.py` 整條走一遍（⛔ 它不可以有第二份壓縮實作）──")
        import halt_spans as H
        # ⛔ `"0"` 是**真值** ⇒ 用 truthy 判會把整批當成停牌中
        ck("⛔ `halted=\"0\"` 不是停牌（truthy 判法會整批誤判）",
           not H.is_halted({"halted": "0"}), "0 被判成停牌")
        ck("　`halted=\"1\"` 是停牌（⚠ 正例，⛔ 一個永遠回 False 的判準沒有用）",
           H.is_halted({"halted": "1"}), "1 沒被判成停牌")
        ck("　空字串不是停牌", not H.is_halted({"halted": ""}))
        # ⛔ runlog 也要指到暫存檔。⚠ 不指的話這支自測會把 repo 裡真的
        #   `_last_run.md` 寫進假資料——2026-09-08 已經發生過一次，
        #   ⭐ 現在 `runlog.finish()` 有守門會直接丟例外（見那邊的註解）。
        import runlog as RL
        old_uni, old_out, old_p = M.UNI, H.OUT, RL.PATH
        H.OUT = os.path.join(sand, "halt_spans.csv")
        M.UNI = sand                      # ⇒ compress 會去讀 sand/chtm/
        RL.PATH = os.path.join(sand, "_last_run.md")
        try:
            rc = H.main()
        finally:
            M.UNI, H.OUT, RL.PATH = old_uni, old_out, old_p
        ck("⭐ `halt_spans.main()` 從頭走到尾、runlog 全過", rc == 0, f"rc={rc}")
        out = os.path.join(sand, "halt_spans.csv")
        ck("　寫出了區間檔", os.path.exists(out))
        if os.path.exists(out):
            got = list(csv.DictReader(io.open(out, encoding="utf-8")))
            c0 = [r for r in got if r["stock_id"] == "c000"]
            ck("⭐⭐ c000 是**兩段**（第 7 天復牌 ⇒ ⛔ 不可以連成一段）",
               len(c0) == 2, str([(r["start"], r["end"]) for r in c0]))
            ck("　⚠ 而第 15 天（抓壞的那天）沒有把區間切開",
               all(r["market"] == "tpex" for r in got) and len(c0) == 2,
               str([(r["start"], r["end"], r["days"]) for r in c0]))
            print("── ⑨ ⛔ 反向驗：自測不改 `runlog.PATH` 必須被擋下來 ──")
        H.OUT = os.path.join(sand, "halt_spans2.csv")
        M.UNI = sand
        blocked = False
        try:
            H.main()
        except RuntimeError as ex:
            blocked = "想寫進真的 runlog" in str(ex)
        finally:
            M.UNI, H.OUT = old_uni, old_out
        ck("⭐⭐ 自測想寫進真的 `_last_run.md` ⇒ **丟例外**"
           "（⛔ 2026-09-08 那次只留註解沒守門，2026-09-11 就又發生一次）",
           blocked, "沒有被擋——真的 runlog 會被寫進假資料")

        ck("⛔ c003 以上從來沒停過 ⇒ 一段都不該有",
               not [r for r in got if r["stock_id"] >= "c003"],
               str([r["stock_id"] for r in got if r["stock_id"] >= "c003"][:5]))

        print("── ⑩ ⛔ 鄰居要**日曆上也相鄰**：尾巴孤零零那天不可以被判成壞掉 ──")
        # ⚠ 2026-09-11 實跑撞到的：`chtm` 只回補到 2017、尾巴剩 2026 一天
        #   ⇒ 它的 ±10 個索引鄰居全是九年前的日子（列數比較多）
        #   ⇒ ⛔ 最新那天被判成「抓壞了」而整天跳過
        #   ⇒ 「⭐ 目前仍停止交易中」變成 **0 檔**，⚠ 而那是最重要的一格。
        d3 = os.path.join(sand, "sparse")
        os.makedirs(d3, exist_ok=True)
        for i, day in enumerate(days):          # 30 天連續，每天 30 列
            io.open(os.path.join(d3, day + ".csv"), "w", encoding="utf-8").write(
                "date,stock_id\n" + "".join(f"{day},c{k:03d}\n" for k in range(30)))
        # ⭐ 九年後孤零零一天，列數只有 20（＝正常，只是那個年代規模不同）
        far = "2035-06-01"
        io.open(os.path.join(d3, far + ".csv"), "w", encoding="utf-8").write(
            "date,stock_id\n" + "".join(f"{far},c{k:03d}\n" for k in range(20)))
        sp3 = M.day_sets(d3)
        bad3 = M.suspect_days(sp3, 0.7)
        ck("⭐⭐ 尾巴那天**沒有**被判成不可判定（鄰居在日曆上差九年 ⇒ 不算鄰居）",
           far not in bad3, f"抓到 {sorted(bad3)}")
        ck("　⚠ 正例還在：同一批資料裡真的崩塌的那天照樣抓得到",
           set(M.suspect_days(M.day_sets(d2, keep=lambda r: True), 0.7))
           == {days[15]},
           str(sorted(M.suspect_days(M.day_sets(d2, keep=lambda r: True), 0.7))))
        ck("　⛔ 而 `_near_days` 對認不出來的日期要放行（不擋），"
           "⚠ 否則格式一變整份區間表就啞掉",
           M._near_days("不是日期", "2026-01-01", 10))
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print(f"\n[selftest] 通過 {_ok}｜失敗 {_bad}")
    return 1 if _bad else 0


if __name__ == "__main__":
    sys.exit(main())

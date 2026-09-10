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
        for day, ids in sets:
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
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print(f"\n[selftest] 通過 {_ok}｜失敗 {_bad}")
    return 1 if _bad else 0


if __name__ == "__main__":
    sys.exit(main())

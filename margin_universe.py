#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""margin_universe.py — 「這一檔在哪一段期間是**融資融券標的**」。⛔ 只讀，不連外。

    python3 margin_universe.py        # → data/meta/margin_membership.csv

## ⭐ 這一支存在的理由：那份歷史**我方已經有了**，只是沒有人把它讀出來

市場情報分析線 2026-09-10 的結論：K線線要的「信用交易標的歷史」不必去找端點——
`data/universe/margin/`（上市）與 `otcmargin/`（上櫃）的**逐日成員本身**
就是那份歷史，而且已經有十一年半。⇒ 這一支只做一件事：把**逐日的集合**
壓成**逐檔的區間**。

## ⛔⛔ 而「今天不在表上」有兩種意思，它們長得一模一樣

```
① 這一檔今天**不是**融資融券標的        ← 真的成員變動
② 這一天那個市場**整批沒抓到／抓壞了**  ← ⛔ 假的成員變動
```

⚠ ② 會一次生出**幾百筆**假的「移除」，而且隔天全部又「加入」回來
⇒ 看起來像市場當天大改制。**⛔ 一天壞掉就足以毀掉整份區間表。**

⇒ 判準：一天的列數若低於**前後 ±10 個交易日的中位數**的 `--floor`（預設 70%），
那一天標成**不可判定**，⛔ 它的集合**整天不參與**成員比對
（區間直接**跨過**它，⛔ 不是在那裡斷開）。

⚠ 實跑結果：上市 0 天、上櫃 0 天觸發——⭐ 而**「抓到 0 天」本身不是結論**，
所以本支一定會印出「該判準在該群抓到的正例數」與門檻，
並且 `selftest_margin_universe.py` 用一個**合成的崩塌日**證明它真的會抓。
（第七點：回報「某群 0 筆」時必須附上正例數。）

## ⛔ 「是不是標的」與「有沒有被停止融資」是兩件事

`note` 欄的 `O`／`X` 是**已經是標的、但被暫停**（波動過劇／股權過度集中）；
⛔ 不在表上才是**不是標的**。⚠ 兩者對讀取端的意思完全相反：
被暫停的那一檔**融資餘額還在**，只是不能新增。
⇒ 本支只回答後者，⛔ 一個字都不碰 `note`。
"""
import argparse
import csv
import io
import os
import statistics
import sys
from collections import Counter

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UNI = os.path.join(_ROOT, "universe")
OUT = os.path.join(_ROOT, "meta", "margin_membership.csv")
HEADER = ["market", "stock_id", "start", "end", "days", "open_ended"]
# ⚠ 目錄名 → 市場名。⛔ 用 `market` 欄不行：這兩個目錄的檔裡**沒有** market 欄。
DIRS = (("margin", "twse"), ("otcmargin", "tpex"))
WIN = 10


def day_sets(d):
    """→ [(日期, 代號集合)]，按日期排序。⛔ 讀不到的檔直接跳過，不當成空集合。

    ⚠ 「讀不到」與「那天沒有成員」差很遠：後者會生出一整批假的移除。
    """
    out = []
    if not os.path.isdir(d):
        return out
    for n in sorted(os.listdir(d)):
        if not n.endswith(".csv"):
            continue
        try:
            with io.open(os.path.join(d, n), encoding="utf-8") as f:
                ids = {(r.get("stock_id") or "").strip()
                       for r in csv.DictReader(f)}
        except OSError:
            continue
        ids.discard("")
        if ids:
            out.append((n[:-4], ids))
    return out


def suspect_days(sets, floor=0.7, win=WIN):
    """→ {日期: (該天列數, 鄰近中位數)}，⛔ 這些天**不參與**成員比對。

    ⚠ 用**鄰近中位數**不用全期中位數：十一年半裡標的數本來就從 880 長到 1,297，
    ⛔ 拿全期中位數比，早年那一整段會被整批誤判成「壞掉」。
    """
    bad = {}
    n = len(sets)
    for i, (day, ids) in enumerate(sets):
        near = [len(s) for j, (_, s) in enumerate(sets)
                if j != i and abs(j - i) <= win]
        if not near:
            continue
        med = statistics.median(near)
        if med and len(ids) < med * floor:
            bad[day] = (len(ids), med)
    return bad


def spans(sets, skip=()):
    """→ [(代號, 起, 迄, 天數)]。⭐ `skip` 裡的日子**整天跳過**。

    ⛔ 「跳過」是指那一天**既不算在、也不算不在**：
      區間直接跨過去，⚠ 不是在那裡斷成兩段——斷開就等於承認了那個假的移除。
    """
    use = [(d, s) for d, s in sets if d not in skip]
    open_ = {}          # 代號 → [起, 上一次出現的日子, 出現天數]
    out = []
    for day, ids in use:
        for c in ids:
            if c in open_:
                open_[c][1] = day
                open_[c][2] += 1
            else:
                open_[c] = [day, day, 1]
        for c in [c for c in open_ if c not in ids]:
            st, last, n = open_.pop(c)
            out.append((c, st, last, n))
    for c, (st, last, n) in open_.items():
        out.append((c, st, last, n))
    return sorted(out, key=lambda x: (x[0], x[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", type=float, default=0.7,
                    help="低於鄰近中位數這個比例的日子視為不可判定")
    a = ap.parse_args()

    rl = runlog.Run("margin_universe")
    rl.info("⛔ 這一支只讀不連外",
            "把 `margin/`／`otcmargin/` 的**逐日成員**壓成**逐檔區間**")

    rows, ok_dirs = [], 0
    for dname, market in DIRS:
        sets = day_sets(os.path.join(UNI, dname))
        if not sets:
            rl.check(f"`{dname}/` 讀得到逐日成員", False, "⛔ 一天都沒有")
            continue
        ok_dirs += 1
        bad = suspect_days(sets, a.floor)
        # ⭐ 第七點：報「0 天」時一定要附上判準與門檻，⛔ 否則 0 會被讀成「乾淨」
        rl.info(f"`{dname}/`（{market}）",
                f"{len(sets):,} 天｜列數 {min(len(s) for _, s in sets):,}"
                f" ~ {max(len(s) for _, s in sets):,}")
        rl.info(f"  ⚠ 不可判定的日子（低於鄰近 ±{WIN} 日中位數的 "
                f"{a.floor:.0%}）",
                f"**{len(bad)} 天**"
                + (f"：{sorted(bad)[:5]}" if bad else
                   "　⇒ ⚠ 0 天不代表資料乾淨，代表**這個判準沒抓到**；"
                   "它抓得到的證明在 `selftest_margin_universe.py`（合成崩塌日）"))
        sp = spans(sets, skip=set(bad))
        last_day = sets[-1][0]
        for c, st, en, n in sp:
            rows.append([market, c, st, en, str(n),
                         "1" if en == last_day else "0"])
        # ⭐⭐ 斷言**終點**：壓成區間之後，逐檔天數總和必須等於它真的出現的天數。
        #   ⛔ 不斷言「算得出區間」——區間算錯（多切一刀、少切一刀）照樣算得出來。
        seen = Counter()
        for day, ids in sets:
            if day in bad:
                continue
            for c in ids:
                seen[c] += 1
        got = Counter()
        for c, _st, _en, n in sp:
            got[c] += n
        rl.check(f"⭐ `{dname}`：區間的天數總和 ＝ 該檔真的出現的天數"
                 "（⛔ 這是終點，不是「算得出區間」）",
                 got == seen,
                 f"{len(sp):,} 段／{len(seen):,} 檔"
                 if got == seen else
                 f"⛔ 對不上 {len(set(got.items()) ^ set(seen.items()))} 檔："
                 f"{[k for k in seen if seen[k] != got.get(k)][:5]}")
        multi = sum(1 for c, k in Counter(x[0] for x in sp).items() if k > 1)
        gained = sum(1 for c, st, _e, _n in sp if st != sets[0][0])
        lost = sum(1 for c, _s, en, _n in sp if en != last_day)
        rl.info(f"  {market}：{len(seen):,} 檔曾經是標的",
                f"⭐ 中途**成為**標的 {gained:,} 段｜中途**不再是** {lost:,} 段｜"
                f"⚠ 進出超過一次的 {multi:,} 檔")

    rl.check("兩個市場都讀到了（⛔ 少一個會讓區間表只涵蓋半個市場）",
             ok_dirs == len(DIRS), f"{ok_dirs}／{len(DIRS)}")
    if not rows:
        return rl.finish()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in sorted(rows, key=lambda r: (r[0], r[1], r[2])):
            w.writerow(r)
    # ⭐ 寫完**重讀**再斷言（CLAUDE.md 第四點二：不要斷言「寫檔成功」）
    with io.open(OUT, encoding="utf-8") as f:
        back = list(csv.DictReader(f))
    rl.check("⭐ 寫出去的檔**重讀回來**列數一致（⛔ 不是斷言「寫檔成功」）",
             len(back) == len(rows), f"寫 {len(rows):,}／讀回 {len(back):,}")
    rl.info("判準檔", f"data/meta/margin_membership.csv｜{len(rows):,} 段")
    rl.info("⇒ 讀法", "「某檔在 D 那天是不是融資融券標的」＝ "
                      "有沒有一段 `start ≤ D ≤ end`。"
                      "⛔ 與 `note` 的停止融資是兩件事（見檔頭）。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())

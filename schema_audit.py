#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schema_audit.py — 逐日目錄的**表頭版本**與**每欄填值率**。⛔ 只讀，不連外。

    python3 schema_audit.py            # → data/meta/_schema_audit.md

## ⭐⭐ 這一支存在的理由：2026-09-10 一天之內，兩條線各摔一次，方向相反

```
margin.note      欄位不在，但那九年其實抓得回來   ⇒ **低估**了自己有的
daily.last_price 欄位在，但那兩天一個值都沒有     ⇒ **高估**了自己有的
```

⇒ 市場情報分析線抽的那句我收下：
**【欄位在不在】從來不是【資料有沒有】的答案。**

## ⛔ 但「看填值率」只做對了一半——同一天我方也摔了

`last_price` 在 2026-09-10 的全庫填值率是 **352 / 71 萬列 ≈ 0.05%**。
⚠ 而它**完全正常**：那一欄 09-10 才生效，而且**設計上只有興櫃會有值**
（上市／上櫃的 `close` 本來就是最後撮合價，⛔ 不必再存一次）。
⇒ 兩條線看到「0%／0.05%」就判它是空殼欄——⛔ **判錯了，而且方向是要人去刪一個好欄位。**

### ⇒ 判準：填值率要跟**三件事**一起看，⛔ 一個百分比不算答案

```
① 生效日     這一欄第一次出現在表頭是哪一天（⛔ 生效日之前不算缺值）
② 適用子集   它設計上該有值的那一群（本庫唯一可觀測的分群鍵是 `market`）
③ 子集內填值率
```

⚠ 而 ② 是**推不出來的**——沒有任何欄位記著「這一欄只有興櫃該有值」。
⇒ ⛔ 這一支**不猜**：它把「**每個 market 各自的填值率**」全部列出來，
⭐ 讓「只有某一群有值」這件事**自己顯形**，而不是由這支替它下結論。
（`last_price` 會長成 `emerging 97%／tpex 0%／twse 0%` ⇒ 一眼看得出是設計。）

## ⭐ 而表頭版本本身就是產出，⛔ 不是附帶的

同一天情報分析線把「2023 有 note、2024 沒有」讀成**一次事故**，
⚠ 而它其實是我方回補的**進度前緣**（逐年分批 ⇒ 前緣必然停在某個 12/31）。
⛔ 兩者在資料上長得一模一樣。⇒ 這份報告把每個版本的**日期區間**寫出來，
並且**每天重跑** ⇒ 前緣會動、疤痕不會動，**看兩天就分得出來**。

## ⛔ 成本：表頭掃全部，填值率只掃樣本——而樣本要講出來

表頭只讀每個檔的**第一行**（2,848 個檔 ≈ 1 秒）。
填值率要讀整個檔 ⇒ 只掃**每個表頭版本的最後一天**（每個版本一天）。
⚠ 第七點：回報「某群 0%」時必須附上**該群的列數** ⇒ 每一格都印分母。
"""
import argparse
import csv
import io
import os
import sys
from collections import Counter, OrderedDict

import runlog
from db_status import universe_dirs as _universe_dirs

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UNI = os.path.join(_ROOT, "universe")
OUT = os.path.join(_ROOT, "meta", "_schema_audit.md")
GROUP_KEY = "market"


def read_header(path):
    """→ 表頭欄名 tuple。讀不到回 ()。⛔ 只讀第一行。"""
    try:
        with io.open(path, encoding="utf-8") as f:
            line = f.readline().rstrip("\n").rstrip("\r")
    except OSError:
        return ()
    return tuple(x.strip() for x in line.split(",")) if line else ()


def schema_versions(day_paths):
    """→ [(表頭, [日期…])]，⛔ 按**第一次出現的日期**排序。

    ⚠ 回的是日期清單而不是區間：⛔ 一個版本可以**不連續**
    （回補跑一半、或某幾天被單獨重寫過），而「區間」會把那件事藏起來。
    """
    by = OrderedDict()
    for day, path in sorted(day_paths):
        h = read_header(path)
        if not h:
            continue
        by.setdefault(h, []).append(day)
    return sorted(by.items(), key=lambda kv: kv[1][0])


def col_first_seen(vers):
    """→ {欄名: 它第一次出現在表頭的日期}。⭐ 這就是「生效日」。"""
    out = {}
    for h, days in sorted(vers, key=lambda kv: kv[1][0]):
        for c in h:
            out.setdefault(c, days[0])
    return out


def fill_rates(path, group_key=GROUP_KEY):
    """→ (總列數, {欄: 有值列數}, {群: (列數, {欄: 有值列數})})。

    ⛔ 「有值」＝ `strip()` 之後不是空字串。⚠ **`0` 算有值**——
    `0` 與空是兩件事（興櫃無成交那一列官方給的就是 0，我方刻意留空）。
    """
    tot, hit = 0, Counter()
    grp = {}
    try:
        with io.open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                tot += 1
                g = (r.get(group_key) or "—").strip() or "—"
                if g not in grp:
                    grp[g] = [0, Counter()]
                grp[g][0] += 1
                for k, v in r.items():
                    if k is not None and (v or "").strip():
                        hit[k] += 1
                        grp[g][1][k] += 1
    except OSError:
        return 0, Counter(), {}
    return tot, hit, {g: (n, c) for g, (n, c) in grp.items()}


def day_paths(d):
    """→ [(日期, 路徑)]。⛔ 只認檔名是日期的（逐檔目錄不在本支範圍）。"""
    out = []
    for n in sorted(os.listdir(d)):
        if not n.endswith(".csv"):
            continue
        day = n[:-4]
        if len(day) == 10 and day[4] == "-" and day[7] == "-":
            out.append((day, os.path.join(d, n)))
    return out


def empty_cols(tot, hit, header):
    """→ 生效之後、**整個檔一格都沒有**的欄。⛔ 只回名字，判斷留給人。

    ⚠ 這一支**不設 check**：`last_price` 在 tpex／twse 就是 0%，而那是設計。
    ⭐ 它的用途是把候選挑出來，讓報告去逐群列數字。
    """
    return [c for c in header if tot and not hit.get(c)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-per-version", type=int, default=1,
                    help="每個表頭版本掃幾天算填值率（⛔ 掃全部會很慢）")
    a = ap.parse_args()

    rl = runlog.Run("schema_audit")
    rl.info("⛔ 這一支只讀不寫 data/universe",
            "產出是 `data/meta/_schema_audit.md`")

    L = ["# 逐日目錄的表頭版本與每欄填值率", "",
         "⛔ **一個百分比不是答案。** 每一欄要跟【生效日、適用子集、"
         "子集內填值率】三件事一起看——見 `schema_audit.py` 檔頭。", ""]
    dirs = [(n, os.path.join(UNI, n))
            for n, _cnt, _lo, _hi, shape in _universe_dirs(UNI)
            if shape == "逐日"]
    rl.check("找得到逐日目錄（⛔ 一個都沒有＝這支在空跑）", bool(dirs),
             f"{len(dirs)} 個：{[n for n, _ in dirs]}")
    if not dirs:
        return rl.finish()

    multi = []
    for name, d in dirs:
        paths = day_paths(d)
        if not paths:
            continue
        vers = schema_versions(paths)
        first = col_first_seen(vers)
        L.append(f"## `data/universe/{name}/`　{len(paths):,} 天、"
                 f"**{len(vers)} 個表頭版本**")
        L.append("")
        if len(vers) > 1:
            multi.append((name, len(vers)))
            L.append("⚠ **同一個目錄有多個表頭版本。** ⛔ 把多天 concat 起來時，"
                     "缺的那一欄會被補成空值，**而且不會報錯**。")
            L.append("")
        L.append("| 版本 | 欄數 | 天數 | 第一天 | 最後一天 | 這一版**多出來**的欄 |")
        L.append("|---|---|---|---|---|---|")
        prev = ()
        for i, (h, days) in enumerate(vers, 1):
            added = [c for c in h if c not in prev] if prev else []
            L.append(f"| v{i} | {len(h)} | {len(days):,} | {days[0]} | "
                     f"{days[-1]} | "
                     f"{'、'.join(f'`{c}`' for c in added) or '—'} |")
            prev = h
        L.append("")

        # ── 填值率：每個版本取**最後一天**（那一版最成熟的一天）──
        for i, (h, days) in enumerate(vers, 1):
            for day in days[-a.sample_per_version:]:
                path = os.path.join(d, f"{day}.csv")
                tot, hit, grp = fill_rates(path)
                if not tot:
                    continue
                gs = sorted(grp)
                L.append(f"### v{i} 的填值率（樣本＝`{day}`，{tot:,} 列）")
                L.append("")
                L.append("| 欄 | 生效日 | 全檔 | " +
                         " | ".join(f"{g}（{grp[g][0]:,} 列）" for g in gs) +
                         " |")
                L.append("|---|---|---|" + "---|" * len(gs))
                for c in h:
                    cells = []
                    for g in gs:
                        n, cnt = grp[g]
                        cells.append(f"{cnt.get(c, 0):,}／{n:,}" if n else "—")
                    L.append(f"| `{c}` | {first.get(c, '—')} | "
                             f"{hit.get(c, 0):,}／{tot:,} | " +
                             " | ".join(cells) + " |")
                L.append("")
                blanks = empty_cols(tot, hit, h)
                if blanks:
                    L.append("⚠ 這一天**整欄空白**的："
                             + "、".join(f"`{c}`" for c in blanks))
                    L.append("　⛔ 空白**不等於**壞掉：先看它的生效日，"
                             "再看是不是只有某一群該有值（上表逐群的分母就是為了這個）。")
                    L.append("")

    rl.info("逐日目錄", f"{len(dirs)} 個")
    # ⛔ 這裡**只 info 不 check**：多版本是回補進行中的正常狀態，
    #   ⚠ 設成 check 會在整整幾天的回補期間天天紅 ⇒ 然後被學會忽略。
    rl.info("⚠ 有多個表頭版本的目錄（⛔ concat 會靜靜補出一整欄空值）",
            "、".join(f"{n}（{k} 版）" for n, k in multi) if multi else "（沒有）")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    rl.info("報告", f"data/meta/_schema_audit.md｜{len(L):,} 行")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())

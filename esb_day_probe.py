#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""esb_day_probe.py — 興櫃的「指定某一天」到底有沒有來源。⛔ 只測不寫資料。

## ⚠ 這一支是為了一件**已經發生的資料遺失**

`data/universe/daily/2026-09-08.csv` 的 **363 列興櫃整批不見**：

    2026-09-04  twse=1368 tpex=983  emerging=363
    2026-09-07  twse=1373 tpex=997  emerging=363
    ⛔ 2026-09-08  twse=1382 tpex=1013 emerging=**0**
    2026-09-09  twse=1382 tpex=1014 emerging=363

成因是我方 2026-09-10 那趟「一天實測」：`--markets twse,tpex --force`
而當時的 `write_day` 是**整檔覆蓋** ⇒ 沒抓的市場被無聲刪掉。
⭐ `write_day` 當天就修好了（保留沒抓的市場），⛔ **但那一天沒有補回來**。

⭐ 而 `missing_rows.py` 那條「不得高於歷史最低值」的斷言**正確地抓到了它**
（68,545 vs 歷史最低 67,446，其中 09-08 一天就佔 1,089 檔）
——⚠ 單調收斂那個設計是有效的，這是它第一次抓到真的遺失。

## ⛔ 這一支只回答一個問題

**興櫃有沒有「帶日期參數、回全市場」的來源？**

    有 ⇒ 那 363 列補得回來，順便解掉「興櫃只有 2026-09-03 起」那個限制
    沒有 ⇒ ⛔ 那一天**永久失去**，而且要寫進契約讓讀的人知道

⚠ 候選清單**從 `backfill.candidates()` import**，⛔ 不在這裡抄一份
——那份清單本來就是「未驗證的假設」，這一支就是用來淘汰它們的
（`backfill.py` 的註解逐字：「**這些全是假設，probe 就是用來淘汰它們的**」）。

## ⛔ 判準：回應要**自己講出它是哪一天**

⚠ 興櫃那幾條候選最危險的失敗**不是連不上**，是
**「連得上、回 363 列、但那是今天的資料」**——
⭐ 而寫進 2026-09-08 之後，它看起來跟正常的一天一模一樣。
⇒ 這裡對每一條候選都跑 `_same_day()`，⛔ 不符一律標成不可用。
"""
import io
import json
import os
import sys

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_esb_day_probe.txt")

# ⭐ 要補的那一天。⚠ 另外測一天**已知有資料**的當對照組：
#   ⛔ 只測 09-08 的話，「全部失敗」有兩種意思（端點不行／那天真的沒有），分不出來。
WANT = "2026-09-08"
CONTROL = "2026-09-09"


def probe_day(day, out):
    out.append(f"══ 目標日 {day}")
    # ⛔ 從 backfill 拿候選，不抄一份
    cands = B.candidates(day).get("emerging", [])
    out.append(f"  候選 {len(cands)} 條（來自 `backfill.candidates()`，⚠ 全是未驗證的假設）")
    usable = []
    for u in cands:
        short = u.split("//", 1)[-1][:120]
        raw, err = B.get(u, retries=1, timeout=30)
        if err:
            gw = ("Tunnel connection failed" in str(err)
                  or "connect_rejected" in str(err))
            out.append(f"  ✗ {short}\n      {str(err)[:150]}"
                       + ("　⚠ **我方閘道擋的**（Actions 上會是通的）" if gw else ""))
            continue
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception as e:                                   # noqa: BLE001
            out.append(f"  ✗ {short}\n      不是 JSON（{type(e).__name__}）"
                       f"｜{len(raw)}B｜前 120：{raw[:120]!r}")
            continue
        # ⭐ 規矩第一條：先把全部頂層鍵攤開
        out.append(f"  ○ {short}")
        out += ["      " + s for s in B.describe_response(d, want={"date": day})]
        # ⛔ 最危險的失敗：連得上、有列、但那是**今天**的資料
        same, said = B._same_day(d, day)
        if isinstance(d, dict) and not same:
            out.append(f"      ⛔ **回應說它是 {said}，不是 {day}** ⇒ 不可用"
                       "（⚠ 這正是「靜靜回今天」，寫進去會跟正常的一天一模一樣）")
            continue
        rows, note = (B.parse_openapi(d, day, "emerging") if isinstance(d, list)
                      else B.parse_twse(d, day, "emerging"))
        out.append(f"      解析：{note}｜{len(rows)} 列")
        if rows:
            out.append(f"      ⭐ **可用**（自述日期：{said or '（沒有自述）'}）")
            usable.append((short, len(rows)))
    out.append(f"  ⇒ {day} 可用的候選：{len(usable)} 條"
               + ("｜" + "｜".join(f"{n} 列" for _, n in usable) if usable else ""))
    return usable


def main():
    out = ["# 興櫃「指定某一天」的來源探針",
           "# ⛔ 只測不寫資料。開發容器對交易所一律 403（我方閘道）——看 Actions 的結果",
           f"# ⚠ 要補的是 {WANT} 那 363 列（見檔頭）；{CONTROL} 是**對照組**",
           "#   ⛔ 只測一天的話，「全部失敗」分不出「端點不行」與「那天真的沒有」。",
           ""]
    a = probe_day(WANT, out)
    out.append("")
    b = probe_day(CONTROL, out)
    out += ["", "## ⇒ 結論"]
    if a:
        out.append(f"⭐ **{WANT} 補得回來**：有 {len(a)} 條候選解得出列，"
                   "且回應自述的日期對得上。")
    elif b:
        out.append(f"⛔ **{WANT} 補不回來，但端點是好的**："
                   f"對照組 {CONTROL} 有 {len(b)} 條可用、而 {WANT} 一條都沒有"
                   "　⇒ ⚠ 那一天的興櫃資料**官方那側就查不到**（多半是 latest-only 端點）。")
    else:
        out.append("⛔ **兩天都沒有可用候選** ⇒ 分不出是端點不行還是那天沒有。"
                   "　⚠ 若是我方閘道 403，這一份不算數，要看 Actions 上的結果。")
    out += ["",
            "⚠ 不論結論是哪一個，都要寫進 `docs/READ_CONTRACT.md`：",
            "  補得回來 ⇒ 排回補；補不回來 ⇒ **那一天要標成已知缺口**，",
            "  ⛔ 不可以讓讀的人以為 2026-09-08 的興櫃是「那天沒有交易」。"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[esb_day_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

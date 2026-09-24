# -*- coding: utf-8 -*-
"""可重用的盤點檢查：數 md 交件裡的【判定格】——把本線踩過的數格規矩收成一支。

規矩（出處：本線操作備忘 追六六、N 盤點那幾輪）：
  ① 讀【判定欄】、看【取值集合】，⛔ 不照關鍵字數（關鍵字版漏掉「分不出來」「反向顯著」）
  ② 有「原判定／新判定」兩欄 ⇒ 取最後一欄，並把取的是哪一欄印出來
  ③ 數目一律由 len()／Counter 算，⛔ 不手打
  ④ 0 格要先證明檢查會響：判定欄存在但全是「基準／—」⇒ 印 ⚠，⛔ 不靜靜當 0
  ⑤ 摘要表沒有判定欄 ≠ 沒被判過：沒有判定欄、但格子裡出現判定用語的表 ⇒ 印 ⚠ 讓人去看
  ⑥ 同一組態在兩張表各印一次 ⇒ 用【數字】去重（列內所有數字 token 依表頭順序），⛔ 不用列名去重
  ⑦ 列的欄數 > 表頭 ⇒ 印 ⚠（判定欄會位移）；< 表頭 ⇒ 只記（尾端缺格，不位移）
  ⑧ 格內的 \| 是字，⛔ 不可當分隔切開（results16 的「C2\|B3」就是）

用法：
  python count_verdicts.py FILE.md [FILE2.md ...] [--dedup]
  python count_verdicts.py --selftest
程式呼叫：count_file(path_or_text, dedup=False) -> dict
"""
from __future__ import annotations
import io
import os
import re
import sys
from collections import Counter

VCOL = re.compile(r"^(判定|統計層|新判定|原判定|結果|事前判定|判)$")
NOT_CELL = {"基準", "—", "-", "", "對照"}
VERDICT_WORDS = ("測得出", "測不出", "分不出來", "反向顯著", "判過", "判不過", "較差")
ESC = "\\|"
SPLIT = re.compile(r"(?<!\\)\|")
NUM = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def tables(txt):
    """[(節名, 表頭, 各列)]；分隔列（---）不算列。"""
    out, sec, cur = [], "", None
    for l in txt.split("\n"):
        if l.startswith("#"):
            sec = l.strip("# ").strip()[:44]
        if l.startswith("|"):
            cells = [c.strip().replace(ESC, "|") for c in SPLIT.split(l.strip().strip("|"))]   # ⚠ 格內的 \| 是字，不是分隔
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if cur is None:
                cur = (sec, cells, [])
            else:
                cur[2].append(cells)
        elif cur is not None:
            out.append(cur); cur = None
    if cur is not None:
        out.append(cur)
    return out


def _clean(v):
    return v.replace("*", "").strip()


def count_text(txt, dedup=False):
    res = {"tables": [], "total": 0, "values": Counter(), "warn": [], "note": [], "unique": None}
    keys = []
    for sec, head, rows in tables(txt):
        vidx = [i for i, h in enumerate(head) if VCOL.match(_clean(h))]
        long_ = [n for n, r in enumerate(rows) if len(r) > len(head)]
        short = [n for n, r in enumerate(rows) if len(r) < len(head)]
        if long_:
            res["warn"].append("【{}】{} 列欄數 > 表頭（{} 欄）⇒ 判定欄可能位移".format(sec, len(long_), len(head)))
        if short:
            res["note"].append("【{}】{} 列欄數 < 表頭（{} 欄）⇒ 尾端缺格（顯示為空白，不位移）".format(sec, len(short), len(head)))
        if not vidx:
            hit = sum(1 for r in rows for c in r if any(w in c for w in VERDICT_WORDS))
            if hit:
                res["warn"].append("【{}】沒有判定欄，但格子裡有判定用語 {} 處 ⇒ 摘要表沒判定≠沒被判過，要人工看".format(sec, hit))
            continue
        i = vidx[-1]
        vals = Counter(_clean(r[i]) if i < len(r) else "" for r in rows)
        cells = Counter({v: c for v, c in vals.items() if v not in NOT_CELL})
        n = sum(cells.values())
        if n == 0:
            res["warn"].append("【{}】判定欄「{}」存在但 0 格（取值 {}）⇒ 先確認這張表本來就不判".format(sec, head[i], dict(vals)))
        res["tables"].append(dict(節=sec, 欄=_clean(head[i]), 兩欄取最後=len(vidx) > 1, 格=n, 取值=dict(cells),
                                  不算=dict((v, c) for v, c in vals.items() if v in NOT_CELL)))
        res["total"] += n
        res["values"].update(cells)
        if dedup:
            for r in rows:
                if i < len(r) and _clean(r[i]) not in NOT_CELL:
                    nums = tuple(t for j, c in enumerate(r) if j != i for t in NUM.findall(_clean(c)))
                    keys.append((nums, _clean(r[i])))
    if dedup:
        res["unique"] = len(set(keys))
        res["dup_same_verdict"] = len(keys) - len(set(keys))
        by_num = {}
        for nums, v in keys:
            by_num.setdefault(nums, set()).add(v)
        res["dup_conflict"] = sum(1 for s in by_num.values() if len(s) > 1)   # 同一組數字、判定卻不同 ⇒ 要查
    return res


def count_file(p, dedup=False):
    txt = io.open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else p
    return count_text(txt, dedup)


def show(name, r):
    print("■ {}".format(name))
    for t in r["tables"]:
        print("   【{}】欄「{}」{}⇒ {} 格｜取值 {}{}".format(t["節"], t["欄"], "（兩欄取最後）" if t["兩欄取最後"] else "",
                                               t["格"], t["取值"], "｜⛔不算 {}".format(t["不算"]) if t["不算"] else ""))
    print("   ⇒ 合計 {} 格｜取值 {}".format(r["total"], dict(r["values"].most_common(8))))
    if r["unique"] is not None:
        print("   ⇒ 用數字去重後 {} 格（同數同判重複 {}；⚠ 同數不同判 {}）".format(r["unique"], r["dup_same_verdict"], r["dup_conflict"]))
    for w in r["warn"]:
        print("   ⚠ " + w)
    for w in r["note"]:
        print("   ・" + w)


def selftest():
    fx = """# 一、主表
| 組態 | n | 超額 | 判定 |
|---|---:|---:|---|
| A | 100 | +1.2 | 分不出來 |
| B | 200 | -3.4 | **反向顯著** |
| C | 300 | +5.6 | 分不出來 |
| 基準 | 50 | 0.0 | 基準 |

# 二、同一組態在第二張表又印一次（數字相同）
| 名稱 | n | 超額 | 判定 |
|---|---:|---:|---|
| A 重印 | 100 | +1.2 | 分不出來 |

# 三、原／新判定兩欄
| 組態 | n | 原判定 | 新判定 |
|---|---:|---|---|
| D | 400 | 測得出 | 測不出 |

# 四、摘要表：沒有判定欄，但文字裡有
| 組態 | 讀法 |
|---|---|
| E | 測得出（＋） |

# 五、判定欄全是基準
| 組態 | 判定 |
|---|---|
| F | — |

# 六、斷列
| 組態 | n | 判定 |
|---|---:|---|
| G | 7 | 較差 | 多一欄 |

# 七、格內有跳脫的管線
| 格 | n | 判定 |
|---|---:|---|
| C2\\|B3 | 9 | 測得出 |

# 八、短列
| 組態 | n | 超額 | 判定 |
|---|---:|---:|---|
| I | 11 | +2.2 | 測不出 |
| H | 8 |
"""
    r = count_text(fx, dedup=True)
    got = {t["節"]: t["格"] for t in r["tables"]}
    # ① 關鍵字版會漏的兩個取值必須被數到
    assert r["values"]["分不出來"] == 3 and r["values"]["反向顯著"] == 1, r["values"]
    # ② 兩欄取最後
    t3 = [t for t in r["tables"] if t["節"].startswith("三")][0]
    assert t3["兩欄取最後"] and t3["欄"] == "新判定" and t3["取值"] == {"測不出": 1}, t3
    # ③ 合計＝ 3+1(重印)+1+1(斷列)+1(跳脫管線)+1(短列表的完整列) ＝ 8，由 len 算
    assert r["total"] == 8, (r["total"], got)
    t7 = [t for t in r["tables"] if t["節"].startswith("七")][0]
    assert t7["取值"] == {"測得出": 1}, t7                            # ⑧ 跳脫管線不可切開
    NOTE = " ".join(r["note"])
    assert "八、短列" in NOTE, r["note"]                               # ⑦ 短列只記
    # ⑥ 用數字去重：A 與「A 重印」數字相同 ⇒ 7
    assert r["unique"] == 7 and r["dup_same_verdict"] == 1 and r["dup_conflict"] == 0, r
    W = "\n".join(r["warn"])
    assert "四、摘要表" in W and "判定用語" in W, W          # ⑤
    assert "五、判定欄全是基準" in W and "0 格" in W, W       # ④
    assert "六、斷列" in W and "欄數 >" in W and "七、" not in W and "八、" not in W, W                 # ⑦
    # 同數不同判 ⇒ 要被抓到
    r2 = count_text("| a | n | 判定 |\n|---|---|---|\n| x | 1 | 測得出 |\n| y | 1 | 測不出 |\n", dedup=True)
    assert r2["dup_conflict"] == 1, r2
    print("✅ selftest：取值集合（分不出來／反向顯著）、兩欄取最後、len 合計、數字去重、同數不同判、三種 ⚠ 全會響、跳脫管線不切開、短列只記不警告")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    dd = "--dedup" in sys.argv
    for p in [a for a in sys.argv[1:] if not a.startswith("--")]:
        show(p, count_file(p, dedup=dd))

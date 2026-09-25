# -*- coding: utf-8 -*-
"""查核 rerun17_regime_t1（⛔ 不 import 主程式、也不 import rerun17／rerun17_table；只用標準庫 csv 讀檔）。

從逐種子檔 resultsN17/regime_t1/seeds.csv 獨立重算：
  ① t1 五格的年化／回落／波動中位（200 顆排序後取第 100、101 顆平均）⇒ 對 cells.csv 逐位元
  ② 比值、年化÷波動、條件一／二、標籤、深淺註（自己寫的規則）⇒ 對 cells.csv
  ③ orig_entry 五格逐種子 cagr／mdd／vol／first／end／trades／eq_sha ⇒ 對 resultsN17/rerun17_seeds.csv（main）；中位 ⇒ 對 rerun17.csv 主窗
  ④ 0050 錨：rerun17.csv 的錨欄 ＝ 釘死值
  ⑤ 進出筆數：flips.csv 窗內兩向筆數 ＝ cells.csv；原判開 − 出 ＋ 進 ＝ t1 判開
  ⑥ 17 格（5 格換 t1、其餘 rerun17.csv 主窗）比值排名、8～10 檔的最高者 ⇒ 對 all17.csv 與 meta.json
    python3 backtest/rerun17_regime_t1_check.py   ⇒ 印出並寫 resultsN17/regime_t1/check.log
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
N17 = os.path.join(HERE, "resultsN17")
OUT = os.path.join(N17, "regime_t1")
CELLS = [1, 4, 7, 16, 17]
ANCHOR = (0.24020209886370614, -0.3395700527611012)
LINES, FAILS = [], []


def say(x):
    print(x); LINES.append(x)


def ok(name, cond, detail=""):
    say(f"{'✅' if cond else '❌'} {name}{('｜' + detail) if detail else ''}")
    if not cond:
        FAILS.append(name)


def rd(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def median(xs):
    s = sorted(xs); n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def same(a, b):
    return repr(float(a)) == repr(float(b))


def lab_of(c, m, bc, bm):
    ratio = c / abs(m); k1 = c > bc; k2 = ratio >= bc / abs(bm)
    lab = "合格" if k1 and k2 else ("另列" if k1 else "不合格")
    extra = f"回落比 0050 深 {(bm - m) * 100:.2f} 點、報酬多 {(c - bc) * 100:.2f} 點" if (lab == "合格" and m < bm) else ""
    return lab, ratio, extra, k1, k2


def main():
    seeds = rd(os.path.join(OUT, "seeds.csv"))
    cells = {int(r["編號"]): r for r in rd(os.path.join(OUT, "cells.csv"))}
    r17 = {int(r["編號"]): r for r in rd(os.path.join(N17, "rerun17.csv"))}
    ref = rd(os.path.join(N17, "rerun17_seeds.csv"))
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))

    # ④ 錨
    bc, bm = float(r17[1]["錨_年化"]), float(r17[1]["錨_回落"])
    ok("④ 0050 錨＝釘死值（rerun17.csv）", same(bc, ANCHOR[0]) and same(bm, ANCHOR[1]), f"{bc!r}／{bm!r}")
    ok("④ 0050 錨＝釘死值（meta.json 本次）", same(meta["bench_win"]["cagr"], ANCHOR[0]) and same(meta["bench_win"]["mdd"], ANCHOR[1]))
    bv = float(r17[1]["錨_年化波動"])

    # ③ 閘二獨立重比
    refm = {(int(r["cell"]), int(r["r"])): r for r in ref if r["stage"] == "main" and int(r["cell"]) in CELLS}
    oe = {(int(r["cell"]), int(r["r"])): r for r in seeds if r["stage"] == "orig_entry"}
    ok("③ orig_entry 與 rerun17_seeds main 的 (格, r) 集合相同", set(oe) == set(refm) and len(oe) == 1000, f"{len(oe)} vs {len(refm)}")
    nbad = 0
    for k in oe:
        a, b = oe[k], refm.get(k)
        if b is None:
            nbad += 1; continue
        if not (all(same(a[c], b[c]) for c in ("cagr", "mdd", "vol")) and all(int(float(a[c])) == int(float(b[c])) for c in ("first", "end", "trades"))
                and a["eq_sha"] == b["eq_sha"]):
            nbad += 1
    ok("③ orig_entry 逐種子 7 欄逐位元", nbad == 0, f"不同 {nbad} 顆")
    for cid in CELLS:
        g = [r for r in seeds if r["stage"] == "orig_entry" and int(r["cell"]) == cid]
        c, m = median([float(r["cagr"]) for r in g]), median([float(r["mdd"]) for r in g])
        ok(f"③ 格{cid} orig_entry 中位 ＝ rerun17.csv 主窗", same(c, r17[cid]["主窗_年化"]) and same(m, r17[cid]["主窗_回落"]),
           f"{c!r}／{m!r}")
        ok(f"③ 格{cid} cells.csv 原（含日內前視）欄 ＝ rerun17.csv 主窗", same(cells[cid]["原_年化（含日內前視）"], r17[cid]["主窗_年化"])
           and same(cells[cid]["原_回落（含日內前視）"], r17[cid]["主窗_回落"]) and cells[cid]["原_標籤（含日內前視）"] == r17[cid]["主窗_標籤"])

    # ①② t1
    for cid in CELLS:
        g = [r for r in seeds if r["stage"] == "t1" and int(r["cell"]) == cid]
        c, m, v = (median([float(r[k]) for r in g]) for k in ("cagr", "mdd", "vol"))
        q = cells[cid]
        ok(f"① 格{cid} t1 中位（{len(g)} 顆）", len(g) == 200 and same(c, q["t1_年化"]) and same(m, q["t1_回落"]) and same(v, q["t1_年化波動"]),
           f"年化 {c!r}／回落 {m!r}／波動 {v!r}")
        lab, ratio, extra, k1, k2 = lab_of(c, m, bc, bm)
        ok(f"② 格{cid} 比值／年化÷波動／標籤／深淺註",
           same(ratio, q["t1_比值"]) and same(c / v, q["t1_年化÷波動"]) and lab == q["t1_標籤"] and extra == (q["t1_深淺註"] or "")
           and str(k1) == q["t1_條件一"] and str(k2) == q["t1_條件二"],
           f"比值 {ratio:.6f}｜{lab}｜{extra or '—'}")
        ok(f"② 格{cid} 標籤變動欄", q["標籤變動"] == ("無" if lab == r17[cid]["主窗_標籤"] else f"{r17[cid]['主窗_標籤']} → {lab}"))

    # ⑤ 進出
    fl = rd(os.path.join(OUT, "flips.csv"))
    out_w = sum(1 for r in fl if r["in_main_win"] == "True" and r["dir"].startswith("原開"))
    in_w = sum(1 for r in fl if r["in_main_win"] == "True" and r["dir"].startswith("原關"))
    q = cells[1]
    ok("⑤ flips.csv 窗內兩向筆數 ＝ cells.csv", out_w == int(q["訊號_原開t1關"]) and in_w == int(q["訊號_原關t1開"]), f"出 {out_w}／進 {in_w}")
    ok("⑤ 原判開 − 出 ＋ 進 ＝ t1 判開", int(q["訊號_原判開"]) - out_w + in_w == int(q["訊號_t1判開"]),
       f"{q['訊號_原判開']} − {out_w} ＋ {in_w} ＝ {q['訊號_t1判開']}")
    ok("⑤ flips 的 sig_close_date 都是 entry 前一個交易日（entry_pos − 1）", all(int(r["pos"]) == int(r["entry_pos"]) - 1 or r["pos_eq_entry_m1"] == "False" for r in fl))

    # ⑥ 17 格排名
    allrow = []
    for cid, r in r17.items():
        if cid in CELLS:
            c, m, lab = float(cells[cid]["t1_年化"]), float(cells[cid]["t1_回落"]), cells[cid]["t1_標籤"]
        else:
            c, m, lab = float(r["主窗_年化"]), float(r["主窗_回落"]), r["主窗_標籤"]
        mt = re.search(r"N(\d+)", r["格"])
        n = int(mt.group(1)) if mt else 8          # P14／P17：P12 策略側 N8（另混 0050）
        allrow.append((c / abs(m), cid, n, lab, r["族"] in ("P14", "P17")))
    allrow.sort(reverse=True)
    a17 = rd(os.path.join(OUT, "all17.csv"))
    ok("⑥ all17.csv 排名與比值", [int(r["編號"]) for r in a17] == [x[1] for x in allrow]
       and all(same(r["比值"], x[0]) for r, x in zip(a17, allrow)))
    top = next(x for x in allrow if 8 <= x[2] <= 10)
    top_pure = next(x for x in allrow if 8 <= x[2] <= 10 and not x[4])
    ok("⑥ 8～10 檔比值最高 ＝ meta.json", top[1] == meta["alt_top_N8_10"]["編號"] and top_pure[1] == meta["alt_top_N8_10_no_mix"]["編號"],
       f"含混 0050：格{top[1]}（{top[0]:.6f}）；不含：格{top_pure[1]}（{top_pure[0]:.6f}）")
    lab1 = lab_of(float(cells[1]["t1_年化"]), float(cells[1]["t1_回落"]), bc, bm)[0]
    ok("⑥ #1 是否掉出合格 ＝ meta.json", (lab1 != "合格") == meta["cell1_drops"], f"#1 t1 標籤 {lab1}")

    say(f"==== 查核 {'全過' if not FAILS else '有 ' + str(len(FAILS)) + ' 項不過'}（{len(LINES)} 行）====")
    with open(os.path.join(OUT, "check.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()

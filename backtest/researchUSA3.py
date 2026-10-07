# -*- coding: utf-8 -*-
"""USREG-A3（16 件：A3-1～8、A3-10～17）照登錄算報酬——總入口與彙總。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3 --cache             # 讀檔快取（~/us_work/a3/stocks.pkl）
    ...                                                                         --run g1|g2|g3|g4|surge [--procs 2]
    ...                                                                         --summary                       # 收各件 json ⇒ A3_summary.json、REPORT.md
    ...  -m backtest.researchUSA3_check                                                                      # 獨立查核＋私有資料掃描 ⇒ check.json
    ...  -m backtest.researchUSA3_page                                                                       # 美股價格訊號十六件.html

判準：美股策略線 登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318（以 seq2 發號）、seq319（疑點 16 條裁示）、
      seq316（只 S&P 400 與合併兩者都過才合格）；開跑前清單 researchUSA34_prep.py＋resultsUSA34/prep/PREP_REPORT.md（⛔ 照它、不改）。
分檔：researchUSA3_core.py（共同讀法 C1～C10、快取、基準、引擎）｜researchUSA3_g1.py（A3-1、A3-2、A3-4、A3-8）｜researchUSA3_g2.py（A3-5、A3-13、A3-16）｜
      researchUSA3_g3.py（A3-6、A3-7、A3-14、A3-15）｜researchUSA3_g4.py（A3-3、A3-10、A3-11、A3-12）｜researchUSA3_surge.py（A3-17，只探索段）。
⛔⛔ 私有資料：resultsUSA34/A3/ 只放彙總；逐筆在 ~/us_work/a3/。
"""
from __future__ import annotations

import importlib
import re
import json
import os
import sys

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A3")
ITEMS = ["A3-1", "A3-2", "A3-3", "A3-4", "A3-5", "A3-6", "A3-7", "A3-8", "A3-10", "A3-11", "A3-12", "A3-13", "A3-14", "A3-15", "A3-16", "A3-17"]
GROUP = {"g1": ("A3-1", "A3-2", "A3-4", "A3-8"), "g2": ("A3-5", "A3-13", "A3-16"), "g3": ("A3-6", "A3-7", "A3-14", "A3-15"),
         "g4": ("A3-3", "A3-10", "A3-11", "A3-12"), "surge": ("A3-17",)}
MOD = {"g1": "backtest.researchUSA3_g1", "g2": "backtest.researchUSA3_g2", "g3": "backtest.researchUSA3_g3", "g4": "backtest.researchUSA3_g4",
       "surge": "backtest.researchUSA3_surge"}
N_PREP = {"A3-1": 1, "A3-2": 1, "A3-3": 6, "A3-4": 1, "A3-5": 174, "A3-6": 4, "A3-7": 2, "A3-8": 16, "A3-10": 1, "A3-11": 3, "A3-12": 4,
          "A3-13": 14, "A3-14": 6, "A3-15": 3, "A3-16": 9, "A3-17": None}
# 先驗（登錄 seq1，⛔ 寫下不改）
PRIOR = ["A3 價格訊號：合格 ≤ 1 件（約七成）", "條件出場主臂平均持有短於 60 日（約六成）", "全批「只 S&P 400 過、合併不過」的格數多於反過來（約六成；A3＋A4 合算，A3 部分照實記）"]


def load_cards():
    out = {}
    for it in ITEMS:
        p = os.path.join(OUT, it + ".json")
        if os.path.exists(p):
            out[it] = json.load(open(p, encoding="utf-8"))
    return out


def lab0(s):
    return s.split("（")[0] if isinstance(s, str) else "—"


def summary():
    J = load_cards()
    cards = {k: v["卡片"] for k, v in J.items()}
    miss = [it for it in ITEMS if it not in cards]
    labs = {k: ("多格整族：" + c.get("標籤") if isinstance(c.get("標籤"), str) and re.search(r"（\d+ 格）", c.get("標籤")) else lab0(c.get("標籤"))) for k, c in cards.items()}
    cnt = {}
    for k, l in labs.items():
        if k == "A3-17":
            continue
        cnt[l] = cnt.get(l, 0) + 1
    N = {k: c.get("N") for k, c in cards.items()}
    n_sum = sum(int(v) for k, v in N.items() if k != "A3-17" and isinstance(v, (int, float)))
    n17 = J.get("A3-17", {}).get("N_待裁定")
    holds = {}
    for k, c in cards.items():
        x = c.get("條件出場必報")
        if isinstance(x, dict):
            v = None
            for kk in x:
                if "平均" in kk and "持有" in kk:
                    v = x[kk]; break
            holds[k] = v
    S = {"性質": "USREG-A3 十六件（A3-1～8、A3-10～17）彙總；A3-17 只探索段（⛔ 驗證段未開，待裁定）",
         "登錄": "USREG-A3A4 seq1 0dc16d3267725d7c＋seq2 bc0927fed5996fd4；裁定 seq318、seq319、seq316",
         "件數": len(cards), "缺件": miss, "標籤": labs, "標籤計數（不含 A3-17）": cnt, "N": N,
         "N合計（A3-1～16，不含 A3-17）": n_sum, "N_清單值（PREP）": N_PREP, "A3-17 N 待裁定（＝探索段挑出數）": n17,
         "條件出場主臂平均持有（各件卡片）": holds, "先驗": PRIOR,
         "先驗紀錄": {"合格≤1": (cnt.get("合格", 0) <= 1) if not miss else None}}
    json.dump(S, open(os.path.join(OUT, "A3_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# USREG-A3 十六件交件：美股價格訊號（回測線）", "",
         "| 欄 | 值 |", "|---|---|",
         "| 判準 | 美股登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318 發號、seq319 疑點裁示、seq316 兩母體 |",
         "| 開跑前清單 | researchUSA34_prep.py＋resultsUSA34/prep/PREP_REPORT.md（補讀法 P1～P20、退化格 61 列；⛔ 照它、不改） |",
         "| 共同讀法 | researchUSA3_core.py C1～C10（窗與段、兩欄挑判、三欄、標籤、組合預設、條件出場必報、事件層、ret50、存活者偏差、結果句） |",
         "| 授權 | 逐筆、權益、成交紀錄只在 ~/us_work/a3/（repo 外）；本資料夾只有彙總 |",
         f"| N（美股帳） | A3-1～16 合計 {n_sum}；A3-17 待裁定（探索段挑出 {n17}，開驗證段時計） |", "",
         "## 〇、逐件結論", "",
         "| 件 | 名稱 | 標籤 | N | 合併 | 只 S&P 400 | 只 S&P 500（描述） |", "|---|---|---|---|---|---|---|"]
    for it in ITEMS:
        c = cards.get(it)
        if not c:
            L.append(f"| {it} | （缺件） | — | — | — | — | — |"); continue
        t3 = c.get("三欄", {})
        L.append(f"| {it} | {c.get('名稱', '')} | {c.get('標籤', '')} | {c.get('N') if c.get('N') is not None else '待裁定'} | "
                 f"{t3.get('合併', '')} | {t3.get('只400', '')} | {t3.get('只500', '')} |")
    L += ["", "## 一、結果句（給使用者）", ""]
    for it in ITEMS:
        c = cards.get(it)
        if c:
            L.append(f"- **{it} {c.get('名稱', '')}**：{c.get('結果句', '')}")
    L += ["", "## 二、條件出場必報（主臂：收盤判、次日開盤、⛔ 不設最長天數）", ""]
    for it in ITEMS:
        c = cards.get(it)
        if c and c.get("條件出場必報"):
            L.append(f"- {it}：{json.dumps(c['條件出場必報'], ensure_ascii=False, default=str)}")
    L += ["", "## 三、|ret|＞50% 未確認列敏感度", ""]
    for it in ITEMS:
        c = cards.get(it)
        if c:
            L.append(f"- {it}：{c.get('敏感度_ret50', '—')}")
    L += ["", "## 四、偏離與執行者補讀法", ""]
    for it in ITEMS:
        c = cards.get(it)
        if c:
            L.append(f"- {it} 偏離：{'；'.join(c.get('偏離', []) or ['無'])}")
            L.append(f"  補讀法：{'；'.join(c.get('補讀法', []) or ['無'])}")
    L += ["", "## 五、先驗（登錄 seq1，⛔ 不改判）", ""] + [f"- {x}" for x in PRIOR]
    for it in ITEMS:
        c = cards.get(it)
        if c and c.get("先驗紀錄"):
            L.append(f"- {it}：{c['先驗紀錄']}")
    ck = os.path.join(OUT, "check.json")
    if os.path.exists(ck):
        L += ["", "## 六、獨立查核（researchUSA3_check.py）", "", "```", open(ck, encoding="utf-8").read(), "```"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("寫出 A3_summary.json、REPORT.md；缺件", miss)


def main():
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    if "--cache" in sys.argv:
        from backtest import researchUSA3_core as C
        C.build_cache(procs)
    if "--run" in sys.argv:
        g = sys.argv[sys.argv.index("--run") + 1]
        importlib.import_module(MOD[g]).run(procs)
    if "--summary" in sys.argv:
        summary()


if __name__ == "__main__":
    main()

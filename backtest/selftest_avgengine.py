# -*- coding: utf-8 -*-
"""PREREG攤平停利 乙 引擎擴充（research11.simulate_mtm：add_rule kind="loss"、trim_rule kind="gain"）的 fixture 與兩道回歸閘。
回測線，2026-09-25。依據：台股策略線登錄 PREREG攤平停利 seq2（sha 17449e5624991924）乙一 2-B ⓓ、乙二 2-C ⓘ；裁定線 seq177 §一① 准 (a)。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_avgengine.py fixtures  # 手算小例、等號邊界、只一次、現金不足、漲跌停遞延、無前視突變、鑑別力
    ... gate1      # 回歸閘 1：regress_tradability(18)＋regress_delist(6)＋改前（git blob）／改後 A/B 矩陣（真資料，≥14 種既有組合含 P9 五參數 × 2 種子）
    ... gate2      # 回歸閘 2：selftest_p9engine.py all、selftest_p9_builders fixtures／real／addcount 全過（含 P9 base 臂 +27.69%／−42.5% 逐位元）
    ... nonid      # ⛔ 不是恆等輸出：PREREGP9 主窗設定、ENGINE_KW_B 兩格 ⇒ 與全關不同；⛔ 只報觸發次數與 equity sha 是否不同
    ... all

⭐ 改前引擎一律從 git 物件庫取（ORIG_BLOB ＝ 改動前 HEAD:backtest/research11.py），⛔ 不靠工作目錄裡的副本。
⭐ 改後引擎＝backtest.research11；環境變數 AVG_ENGINE_SRC 指到另一個檔 ⇒ fixtures／gate1 改測那個檔（換檔前先在暫存檔自測用）。
⭐ 突變體（鑑別力）：`# _XLAG` 行的 [t - 1] ⇒ [t]（判定改讀當天）；讀法體：新兩型改回比值式 c/ep − 1（字面式 vs 比值式）。
⛔ 本檔【不跑乙的 2 格】、⛔ 不讀任何年化／回落：nonid 只取 x_ 計數鍵與 equity 的 sha（引擎回傳的其他鍵當場丟掉）。
⚠ gate2 跑的兩支既有 selftest 會改寫 backtest/resultsp9_engine/ 下已入庫的結果檔 ⇒ 本檔跑前把整個目錄的位元組存在記憶體、
   讀完結果後逐檔寫回原位元組（⛔ 不留下對既有檔的改動）；它們這次的輸出摘要寫進本檔的 engine_b_gate2.json。
結果寫到 backtest/resultsAvg/engine_b_{fixtures,gate1,gate2,nonid}.json。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest", "resultsAvg")
PY = sys.executable
ORIG_BLOB = "e25799728f66ea494e1805ceb8b6caf9848a5d7e"      # 改動前 HEAD:backtest/research11.py（HEAD 69cdc62bd8；最後改它的 commit 9c72da5997）
KW_BY = {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}}   # 乙一 2-B ⓓ（ENGINE_KW_B["By"] 建議值）
KW_CI = {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}                   # 乙二 2-C ⓘ（ENGINE_KW_B["Ci"] 建議值）
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9      # noqa: E402  ⭐ 只借小工具（px／run／same_out／trad_of／load_real／_load_src），⛔ 不改它
px, run, same_out, trad_of, close_to, fin, recs, NC = SP9.px, SP9.run, SP9.same_out, SP9.trad_of, SP9.close_to, SP9.fin, SP9.recs, SP9.NC


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"engine_b_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if EXTRA:
        d["extra"] = EXTRA
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


# ─────────────────────────── 引擎：新／改前／突變體／比值式讀法體
def _new_src():
    p = os.environ.get("AVG_ENGINE_SRC")
    if p:
        return open(p, encoding="utf-8").read(), p
    from backtest import research11 as R
    return open(R.__file__, encoding="utf-8").read(), R.__file__


def engine_new():
    p = os.environ.get("AVG_ENGINE_SRC")
    if p:
        return SP9._load_src(open(p, encoding="utf-8").read(), "backtest._r11_new", p)
    from backtest import research11 as R
    return R


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return SP9._load_src(src, "backtest._r11_orig_avg", os.path.join(REPO, "backtest", "research11.py"))


def engine_mutant():
    """鑑別力：`# _XLAG` 行的 [t - 1] ⇒ [t]（判定改讀 t 當天收盤 ＝ 前視）。"""
    src, f = _new_src()
    lines = src.split("\n"); n = 0
    for i, ln in enumerate(lines):
        if "# _XLAG" in ln and "[t - 1]" in ln:
            lines[i] = ln.replace("[t - 1]", "[t]"); n += 1
    if n < 7:
        raise SystemExit(f"⛔ 突變點只找到 {n} 個（應 ≥ 7：P9 的 6 個＋乙一 loss 1 個；乙二 gain 與 2-C ⓐ 共用同一行）")
    return SP9._load_src("\n".join(lines), "backtest._r11_mut_avg", f), n


def engine_ratio():
    """讀法體：新兩型的字面式 c ≤ (1−x)·ep、c ≥ (1+x)·ep 換回既有型的比值式 c/ep − 1 ≤ −x、≥ x。"""
    src, f = _new_src()
    a = "c1 <= (1.0 - add_rule[\"x\"]) * ep"; b = "c1 >= (1.0 + tx) * ep"
    if src.count(a) != 1 or src.count(b) != 1:
        raise SystemExit("⛔ 讀法體：找不到字面式")
    src = src.replace(a, "c1 / ep - 1.0 <= -add_rule[\"x\"]").replace(b, "c1 / ep - 1.0 >= tx")
    return SP9._load_src(src, "backtest._r11_ratio_avg", f)


def strip(o):
    return {k: v for k, v in o.items() if k != "_audit"}


# ─────────────────────────── fixture（預期值一律用獨立手算式，⛔ 不呼叫引擎內部函式；容差 1e-12）
def fixtures():
    R = engine_new(); C = R.COST
    print(f"── 引擎：{'AVG_ENGINE_SRC=' + os.environ['AVG_ENGINE_SRC'] if os.environ.get('AVG_ENGINE_SRC') else R.__file__}")
    chk("浮點前提：1 − 0.10 ＝＝ 0.90、1 + 0.15 ＝＝ 1.15（字面式 (1−x)·ep 就是登錄的 0.90×P0、1.15×P0）", (1.0 - 0.10) == 0.90 and (1.0 + 0.15) == 1.15)
    LOSS = {"add_rule": {"kind": "loss", "x": 0.10}}
    GAIN = {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}
    print("── 乙一 add_rule kind='loss'（跌 10% 加碼半份）")
    pL = {"A": px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, 30, 8.8, 8.8), (30, NC, 7, 7))}
    o = run(R, [("A", 10, 60)], pL, 2, **LOSS)
    want = 0.5 * (0.5 + 0.5 * 0.89) / 2
    exp = (0.5 - want) + (0.5 + want * 10 / 8.8) * 0.7 - (0.5 + want) * C
    ad = [(r["t"], r["px"], round(r["amt"], 12)) for r in recs(o, "add")]
    chk("L1 觸發日：收盤[20]＝8.9 ≤ 9.0 ⇒ t=21 開盤 8.8 加 0.5×slot（slot＝equity[20]/2＝0.4725）；跌到 −30% 不再加（只一次）；期末手算相符",
        close_to(fin(o), exp) and ad == [(21, 8.8, round(want, 12))] and (o["x_add_trig"], o["x_add_n"], o["x_add_short"]) == (1, 1, 0),
        f"期末 {fin(o):.12f} vs {exp:.12f}；加碼 {ad}")
    pE = {"A": px((0, 20, 10, 10), (20, NC, 9.0, 9.0))}
    o = run(R, [("A", 10, 60)], pE, 2, **LOSS)
    exp = 0.95 - (0.5 + 0.2375) * C
    ad = [r["t"] for r in recs(o, "add")]
    chk("L2 等號邊界：收盤＝9.0＝0.90×10 ⇒ 觸發（登錄字面「≤」）；t=21 開盤 9.0 加 0.2375；期末 ＝ 0.95 − 0.7375×COST",
        ad == [21] and close_to(fin(o), exp), f"加碼日 {ad}；期末 {fin(o):.12f} vs {exp:.12f}")
    pE2 = {"A": px((0, 20, 10, 10), (20, NC, 9.01, 9.01))}
    o = run(R, [("A", 10, 60)], pE2, 2, **LOSS)
    chk("L2' 差一點：收盤 9.01 ＞ 9.0 ⇒ 整段不觸發（x_add_trig＝0）；期末 ＝ 0.5 ＋ 0.5×(0.901 − COST)",
        not recs(o, "add") and o["x_add_trig"] == 0 and close_to(fin(o), 0.5 + 0.5 * (0.901 - C)))
    RR_ = engine_ratio()
    o = run(RR_, [("A", 10, 60)], pE, 2, **LOSS)
    chk("L2'' 讀法鑑別：同一個 9.0 用比值式（9.0/10 − 1 ＝ −0.09999999999999998 ≤ −0.10？否）⇒ 不觸發 ⇒ 字面式與比值式在這筆分得出來",
        not recs(o, "add") and o["x_add_trig"] == 0, f"比值式 x_add_trig＝{o['x_add_trig']}")
    pD = {"A": px((0, 10, 10, 10), (10, 11, 10, 8.9), (11, NC, 8.9, 8.9))}
    o = run(R, [("A", 10, 60)], pD, 2, **LOSS)
    chk("L3 進場當天收盤就 ≤ 0.90×進場開盤 ⇒ 次日（t=11）開盤加（與 gain 型、甲 A3「觀察期含 e 當天」同口徑）", [r["t"] for r in recs(o, "add")] == [11])
    pS = {"A": pL["A"], "B": px((0, 15, 10, 10), (15, 16, 10, 1.0), (16, NC, 1.0, 1.0)), "C": px()}
    rows = [("A", 10, 60), ("B", 10, 15), ("C", 10, 25)]
    o = run(R, rows, pS, 3, **LOSS)
    exp = (0.1 - C) / 3 + (1 - C) / 3 + (0.7 - C) / 3
    chk("L4 現金不足（short='skip'，登錄逐字）：t=21 要 0.5×equity[20]/3≈0.105、現金只有 B 賠剩的 0.031 ⇒ 不加、x_add_short＝1；"
        "t=25 C 出場現金回來、A 仍在 −12%～−30% ⇒ 也不再加（機會已用掉）；期末 ＝ 0.6 − COST",
        not recs(o, "add") and (o["x_add_trig"], o["x_add_n"], o["x_add_short"]) == (1, 0, 1) and close_to(fin(o), exp), f"期末 {fin(o):.12f} vs {exp:.12f}")
    o = run(R, rows, pS, 3, add_rule={"kind": "loss", "x": 0.10, "short": "partial"})
    a = (0.1 - C) / 3
    exp = (1 - C) / 3 + (1 / 3 + a * 10 / 8.8) * 0.7 - (1 / 3 + a) * C
    chk("L4' 現金不足（short='partial'，非登錄預設）：只加得到現金那麼多（0.031）、x_add_short＝1；期末手算相符",
        [round(r["amt"], 12) for r in recs(o, "add")] == [round(a, 12)] and o["x_add_short"] == 1 and close_to(fin(o), exp), f"期末 {fin(o):.12f} vs {exp:.12f}")
    want = 0.5 * 0.94 / 2
    exp = (0.5 - want) + (0.5 + want * 10 / 8.8) * 0.7 - (0.5 + want) * C
    o = run(R, [("A", 10, 60)], pL, 2, tradable=trad_of(pL, up=[("A", 21)]), **LOSS)
    chk("L5 漲停遞延：t=21 開盤漲停 ⇒ t=22 開盤 8.8 加（金額用 t=22 的 slot＝equity[21]/2）、x_add_blocked_days＝1；期末手算相符",
        [r["t"] for r in recs(o, "add")] == [22] and o["x_add_blocked_days"] == 1 and close_to(fin(o), exp), f"期末 {fin(o):.12f} vs {exp:.12f}")
    o = run(R, [("A", 10, 60)], pL, 2, tradable=trad_of(pL, halt=[("A", 21), ("A", 22)]), **LOSS)
    chk("L5' 停牌遞延：t=21、22 停牌 ⇒ t=23 加、x_add_blocked_days＝2；期末同 L5", [r["t"] for r in recs(o, "add")] == [23] and o["x_add_blocked_days"] == 2
        and close_to(fin(o), exp))
    o = run(R, [("A", 10, 60)], pL, 2, tradable=trad_of(pL, dn=[("A", 21)]), **LOSS)
    chk("L5'' 加碼日開盤【跌停】不擋買（只有漲停擋買）⇒ t=21 照加", [r["t"] for r in recs(o, "add")] == [21] and o["x_add_blocked_days"] == 0)
    pX = {"A": px((0, 58, 10, 10), (58, NC, 8.9, 8.9))}
    o = run(R, [("A", 10, 60)], pX, 2, tradable=trad_of(pX, up=[("A", 59)]), **LOSS)
    chk("L6 遞延撞到排程出場：收盤[58] 觸發、t=59 漲停、t=60 出場 ⇒ 不加（x_add_trig＝1、x_add_n＝0、blocked 1）",
        not recs(o, "add") and (o["x_add_trig"], o["x_add_n"], o["x_add_blocked_days"]) == (1, 0, 1) and close_to(fin(o), 0.5 + 0.5 * (0.89 - C)))
    pP = {"A": px((0, 15, 10, 10), (15, 20, 12, 12), (20, 25, 10.8, 10.8), (25, NC, 9.0, 9.0))}
    o = run(R, [("A", 10, 60)], pP, 2, **LOSS)
    chk("L7 錨是進場價、⛔ 不是高點：先漲到 12、回到 10.8（離高點 −10%、離進場 +8%）⇒ 不加；收盤[25]＝9.0 ⇒ t=26 加",
        [r["t"] for r in recs(o, "add")] == [26] and o["x_add_trig"] == 1)
    pQ = {"A": px((0, 15, 10, 10), (15, 45, 9.0, 9.0), (45, NC, 8.0, 8.0))}
    o = run(R, [("A", 10, 30), ("A", 40, 70)], pQ, 2, **LOSS)
    chk("L8 逐部位狀態：同一檔兩段持有 ⇒ 第一段（進場 10）收盤[15]＝9.0 ⇒ t=16 加；第二段（進場 9.0）收盤 9.0 不算、收盤[45]＝8.0 ≤ 8.1 ⇒ t=46 加",
        [r["t"] for r in recs(o, "add")] == [16, 46] and o["x_add_n"] == 2, f"{[(r['t'], r['px']) for r in recs(o, 'add')]}")

    print("── 乙二 trim_rule kind='gain'（漲 15% 賣一半）")
    pG = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, 30, 11.8, 11.8), (30, NC, 13, 13))}
    o = run(R, [("A", 10, 60)], pG, 1, **GAIN)
    exp = 0.59 - 0.5 * C + 0.65 - 0.5 * C
    tr = [(r["t"], r["px"], round(r["amt"], 12), round(r["cost"], 15)) for r in recs(o, "trim")]
    chk("G1 觸發日：收盤[20]＝11.6 ≥ 11.5 ⇒ t=21 開盤 11.8 賣一半（拿回 0.59、成本 0.5×COST、現金留著）；漲到 +30% 不再賣；期末 ＝ 1.24 − COST",
        close_to(fin(o), exp) and tr == [(21, 11.8, 0.59, round(0.5 * C, 15))] and o["x_trim_n"] == 1, f"期末 {fin(o):.12f} vs {exp:.12f}；{tr}")
    pGE = {"A": px((0, 20, 10, 10), (20, NC, 11.5, 11.5))}
    o = run(R, [("A", 10, 60)], pGE, 1, **GAIN)
    chk("G2 等號邊界：收盤＝11.5＝1.15×10 ⇒ 觸發（登錄字面「≥」）；t=21 賣半；期末 ＝ 1.15 − COST",
        [r["t"] for r in recs(o, "trim")] == [21] and close_to(fin(o), 1.15 - C), f"期末 {fin(o):.12f}")
    pGE2 = {"A": px((0, 20, 10, 10), (20, NC, 11.49, 11.49))}
    o = run(R, [("A", 10, 60)], pGE2, 1, **GAIN)
    chk("G2' 差一點：收盤 11.49 ⇒ 不觸發；期末 ＝ 1.149 − COST（沒動過的部位走原式）", not recs(o, "trim") and o["x_trim_n"] == 0 and close_to(fin(o), 1.149 - C))
    o = run(RR_, [("A", 10, 60)], pGE, 1, **GAIN)
    chk("G2'' 讀法鑑別：同一個 11.5 用比值式（11.5/10 − 1 ＝ 0.1499999… ≥ 0.15？否）⇒ 不觸發", not recs(o, "trim") and o["x_trim_n"] == 0)
    pGD = {"A": px((0, 10, 10, 10), (10, 11, 10, 11.6), (11, NC, 11.6, 11.6))}
    o = run(R, [("A", 10, 60)], pGD, 1, **GAIN)
    chk("G3 進場當天收盤就 ≥ 1.15×進場開盤 ⇒ t=11 開盤賣半", [r["t"] for r in recs(o, "trim")] == [11])
    exp = 0.59 - 0.5 * C + 0.65 - 0.5 * C
    o = run(R, [("A", 10, 60)], pG, 1, tradable=trad_of(pG, dn=[("A", 21)]), **GAIN)
    chk("G4 跌停遞延：t=21 開盤跌停 ⇒ t=22 開盤 11.8 賣、x_trim_blocked_days＝1；期末同 G1",
        [r["t"] for r in recs(o, "trim")] == [22] and o["x_trim_blocked_days"] == 1 and close_to(fin(o), exp))
    o = run(R, [("A", 10, 60)], pG, 1, tradable=trad_of(pG, halt=[("A", 21)]), **GAIN)
    chk("G4' 停牌遞延：t=21 停牌 ⇒ t=22 賣、blocked 1", [r["t"] for r in recs(o, "trim")] == [22] and o["x_trim_blocked_days"] == 1)
    o = run(R, [("A", 10, 60)], pG, 1, tradable=trad_of(pG, up=[("A", 21)]), **GAIN)
    chk("G4'' 賣出日開盤【漲停】不擋賣（只有跌停擋賣）⇒ t=21 照賣", [r["t"] for r in recs(o, "trim")] == [21] and o["x_trim_blocked_days"] == 0)
    pGX = {"A": px((0, 58, 10, 10), (58, NC, 11.6, 11.6))}
    o = run(R, [("A", 10, 60)], pGX, 1, tradable=trad_of(pGX, dn=[("A", 59)]), **GAIN)
    chk("G5 遞延撞到排程出場：收盤[58] 觸發、t=59 跌停、t=60 出場 ⇒ 不賣半（x_trim_n＝0、blocked 1）；期末 ＝ 1.16 − COST",
        not recs(o, "trim") and (o["x_trim_n"], o["x_trim_blocked_days"]) == (0, 1) and close_to(fin(o), 1.16 - C))
    pGA = {"A": px((0, 15, 10, 10), (15, 20, 8, 8), (20, 25, 9.2, 9.2), (25, NC, 11.5, 11.5))}
    o = run(R, [("A", 10, 60)], pGA, 1, **GAIN)
    chk("G6 錨是進場價、⛔ 不是低點：先跌到 8、反彈到 9.2（離低點 +15%）⇒ 不賣；收盤[25]＝11.5 ⇒ t=26 賣半", [r["t"] for r in recs(o, "trim")] == [26])
    pGQ = {"A": px((0, 15, 10, 10), (15, 45, 11.5, 11.5), (45, NC, 13.3, 13.3))}
    o = run(R, [("A", 10, 30), ("A", 40, 70)], pGQ, 2, **GAIN)
    chk("G7 逐部位狀態：第一段（進場 10）收盤[15]＝11.5 ⇒ t=16 賣半；第二段（進場 11.5）11.5 不算、收盤[45]＝13.3 ≥ 13.225 ⇒ t=46 賣半",
        [r["t"] for r in recs(o, "trim")] == [16, 46] and o["x_trim_n"] == 2, f"{[(r['t'], r['px']) for r in recs(o, 'trim')]}")
    o = run(R, [("A", 10, 60)], pL, 1, **GAIN); o2 = run(R, [("A", 10, 60)], pG, 2, **LOSS)
    chk("G8 方向：跌的路徑上 gain 型不賣、漲的路徑上 loss 型不加", not recs(o, "trim") and not recs(o2, "add"))

    print("── 既有型不變、全關／開著沒觸發 ⇒ 與改前引擎（git blob）逐位元同")
    R0 = engine_orig()
    pT = {"A": px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, 30, 8.8, 8.8), (30, NC, 7, 7))}
    for nm, kw0, kw1 in (("trim 省略 kind", dict(trim_rule={"x": 0.10, "frac": 0.5}), dict(trim_rule={"x": 0.10, "frac": 0.5})),
                         ("trim kind='loss' 明寫", dict(trim_rule={"x": 0.10, "frac": 0.5}), dict(trim_rule={"kind": "loss", "x": 0.10, "frac": 0.5})),
                         ("add gain", dict(add_rule={"kind": "gain", "x": 0.15}), dict(add_rule={"kind": "gain", "x": 0.15}))):
        for pr in (pT, pG):
            a0 = run(R0, [("A", 10, 60)], pr, 2, **kw0); a1 = run(R, [("A", 10, 60)], pr, 2, **kw1)
            ok, why = same_out(strip(a0), strip(a1))
            chk(f"既有型 {nm}（{'跌' if pr is pT else '漲'}路徑）⇒ 改前／改後逐位元同（含 x_ 鍵與 audit）", ok and repr(a0["_audit"]) == repr(a1["_audit"]), why)
    pZ = {"A": pG["A"], "B": pS["B"], "C": pL["A"]}
    rowsZ = [("A", 10, 60), ("B", 10, 15), ("C", 20, 70)]
    a = run(R0, rowsZ, pZ, 2); z = run(R, rowsZ, pZ, 2)
    ok, why = same_out(strip(a), strip(z))
    chk("全關 ⇒ 與改前引擎逐位元同（equity bytes＋全部回傳＋audit）", ok and repr(a["_audit"]) == repr(z["_audit"]), why)
    for nm, kw in (("loss x=0.999（收盤要 ≤ 0.001×進場）", dict(add_rule={"kind": "loss", "x": 0.999})),
                   ("gain trim x=1e9", dict(trim_rule={"kind": "gain", "x": 1e9, "frac": 0.5}))):
        zz = run(R, rowsZ, pZ, 2, **kw)
        ok, why = same_out(strip(a), strip(zz), skip_prefix="x_")
        chk(f"新型開著但沒觸發（{nm}）⇒ 與改前引擎逐位元同（x_ 鍵除外）", ok and repr(a["_audit"]) == repr(zz["_audit"]), why)
    o1 = run(R, [("A", 10, 60)], pL, 2, add_rule={"kind": "loss", "x": 0.10})
    o2 = run(R, [("A", 10, 60)], pL, 2, **KW_BY)
    ok, why = same_out(strip(o1), strip(o2))
    chk("ENGINE_KW_B[By] 明寫 size 0.5／short skip ＝ 省略時的預設（逐位元）", ok and repr(o1["_audit"]) == repr(o2["_audit"]), why)
    o3 = run(R, [("A", 10, 60)], pG, 1, trim_rule={"kind": "gain", "x": 0.15}); o4 = run(R, [("A", 10, 60)], pG, 1, **KW_CI)
    ok, why = same_out(strip(o3), strip(o4))
    chk("ENGINE_KW_B[Ci] 明寫 frac 0.5 ＝ 省略時的預設（逐位元）", ok and repr(o3["_audit"]) == repr(o4["_audit"]), why)

    lookahead(R)

    print("── 防呆")
    for nm, kw in (("loss 沒給 x", dict(add_rule={"kind": "loss"})), ("loss x=0", dict(add_rule={"kind": "loss", "x": 0.0})),
                   ("loss x=1", dict(add_rule={"kind": "loss", "x": 1.0})), ("loss x 給負數", dict(add_rule={"kind": "loss", "x": -0.1})),
                   ("gain trim 沒給 x", dict(trim_rule={"kind": "gain"})), ("gain trim x=0", dict(trim_rule={"kind": "gain", "x": 0.0})),
                   ("gain trim frac=1", dict(trim_rule={"kind": "gain", "x": 0.15, "frac": 1.0})),
                   ("trim kind 打錯", dict(trim_rule={"kind": "gian", "x": 0.15})), ("add kind 打錯", dict(add_rule={"kind": "lose", "x": 0.1})),
                   ("乙一乙二同開", dict(**KW_BY, **KW_CI)), ("loss 與 stop 同開", dict(**KW_BY, stop=("fix", 0.1)))):
        try:
            run(R, rowsZ, pZ, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)


def lookahead(R):
    """無前視突變：改 t=s 的收盤與 s+1 起的開盤／收盤 ⇒ 正確引擎在 t ≤ s 的交易與 equity[:s] 都不變；突變體（改讀當天）必須被抓到。"""
    M, n_mut = engine_mutant()
    print(f"── 無前視＋鑑別力（突變體：{n_mut} 個 `# _XLAG` 讀取點 [t−1] ⇒ [t]）")
    EXTRA["突變點數"] = n_mut

    def pair(eng, rows, pa, pb, N, kw, s):
        oa = run(eng, rows, pa, N, **kw); ob = run(eng, rows, pb, N, **kw)
        ta = [r for r in oa["_audit"] if r["t"] <= s]; tb = [r for r in ob["_audit"] if r["t"] <= s]
        pre = repr(ta) == repr(tb) and oa["equity"][:s].tobytes() == ob["equity"][:s].tobytes()
        post = repr(oa["_audit"]) != repr(ob["_audit"])
        return pre, post

    s = 30
    flat = {"A": px()}
    for nm, pb, N, kw in (("乙一 loss（個股收盤 t=30 起 −20%）", {"A": px((s, s + 1, 10, 8), (s + 1, NC, 8, 8))}, 2, KW_BY),
                          ("乙二 gain（個股收盤 t=30 起 +20%）", {"A": px((s, s + 1, 10, 12), (s + 1, NC, 12, 12))}, 1, KW_CI)):
        pre, post = pair(R, [("A", 10, 60)], flat, pb, N, kw, s)
        chk(f"無前視 {nm}：t ≤ {s} 的交易與 equity[:{s}] 不變、之後確實不同（修改不是空的）", pre and post, f"前段相同 {pre}／後段不同 {post}")
        mpre, _ = pair(M, [("A", 10, 60)], flat, pb, N, kw, s)
        chk(f"鑑別力 {nm}：突變體（判定改讀 t 當天）⇒ 前段就不同（被抓到）", not mpre, f"突變體前段相同 {mpre}")
    # 隨機世界：3 檔隨機漫步、5～7 筆訊號、s 隨機（避開排程出場日：出場日的收盤本來就參與當天記帳）；一半世界開 tradable（隨機漲跌停／停牌）
    rng = np.random.default_rng(20260925)
    stats = {}
    for nm, kw, lab in (("loss", KW_BY, "乙一"), ("gain", KW_CI, "乙二")):
        n_ok = n_post = n_caught = n_trig = 0; n_w = 300
        for w in range(n_w):
            sids = ["A", "B", "C"]
            pa = {}
            for sd in sids:
                c = 10 * np.exp(np.cumsum(rng.normal(0, 0.035, NC)))
                o = np.r_[10.0, c[:-1]] * np.exp(rng.normal(0, 0.01, NC))
                pa[sd] = (o, c)
            rows = []
            for _ in range(int(rng.integers(5, 8))):
                e = int(rng.integers(3, 55)); rows.append((sids[int(rng.integers(0, 3))], e, min(NC - 1, e + int(rng.integers(8, 35)))))
            exits = {x for _, _, x in rows}
            s = int(rng.integers(12, 75))
            while s in exits:
                s += 1
            pb = {}
            for i, sd in enumerate(sids):
                o, c = pa[sd][0].copy(), pa[sd][1].copy()
                f = (0.7 if (w + i) % 2 else 1.35) * np.exp(np.cumsum(rng.normal(0, 0.02, NC - s)))
                c[s:] = c[s:] * f; o[s + 1:] = o[s + 1:] * f[:-1]           # ⭐ t=s 的開盤不動（t 開盤在 t 當下已知）
                pb[sd] = (o, c)
            N = int(rng.integers(2, 4))
            extra = {}
            if w % 2:
                up = [(sd, int(t)) for sd in sids for t in rng.choice(NC, 6, replace=False)]
                dn = [(sd, int(t)) for sd in sids for t in rng.choice(NC, 6, replace=False)]
                ha = [(sd, int(t)) for sd in sids for t in rng.choice(NC, 4, replace=False)]
                extra = dict(tradable=trad_of(pa, up=up, dn=dn, halt=ha))
            pre, post = pair(R, rows, pa, pb, N, {**kw, **extra}, s)
            mpre, _ = pair(M, rows, pa, pb, N, {**kw, **extra}, s)
            oa = run(R, rows, pa, N, **kw, **extra)
            n_trig += int((oa["x_add_trig"] if nm == "loss" else oa["x_trim_n"]) > 0)
            n_ok += pre; n_post += post; n_caught += (not mpre)
        stats[lab] = {"世界": n_w, "正確引擎前段相同": n_ok, "後段確實不同": n_post, "突變體被抓到": n_caught, "有觸發的世界": n_trig}
        chk(f"無前視（隨機 {n_w} 個世界，{lab} {nm}）：正確引擎 t ≤ s 的交易與 equity[:s] 全部不變", n_ok == n_w, json.dumps(stats[lab], ensure_ascii=False))
        chk(f"鑑別力（隨機 {n_w} 個世界，{lab} {nm}）：突變體至少在一部分世界被抓到（被抓到 ＝ 前段就不同）", n_caught > 0, f"{n_caught}/{n_w}")
    EXTRA["隨機無前視"] = stats


# ─────────────────────────── 回歸閘 1
def gate1():
    os.chdir(REPO)
    if not os.environ.get("AVG_ENGINE_SRC"):
        print("── 回歸閘 1-a：既有兩道回歸閘（新參數全關）")
        for scr, n in (("regress_tradability.py", 18), ("regress_delist.py", 6)):
            p = subprocess.run([PY, os.path.join(REPO, "backtest", scr), "check"], cwd=REPO, capture_output=True, text=True)
            tail = [ln for ln in p.stdout.strip().split("\n") if ln][-1:] if p.stdout else []
            chk(f"{scr} check（{n} 組）逐位元相同", p.returncode == 0 and "✅" in p.stdout, " ".join(tail) + (p.stderr[-300:] if p.returncode else ""))
    else:
        print("── 回歸閘 1-a 略過（AVG_ENGINE_SRC 模式：兩支 regress 讀的是工作樹裡的 research11，要換檔後才跑）")
    print("── 回歸閘 1-b：改前（git blob）／改後 A/B 矩陣（真資料、門檻B、H120、N=8、種子 0,1；比 equity bytes＋全部回傳＋log＋audit）")
    from backtest import tradability as T
    R = engine_new(); R0 = engine_orig()
    cal, ncal, uni, panel, closes, opens, sig, bench = SP9.load_real()
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    wk = np.zeros(ncal, bool); wk[1:] = R.regime_below(bench, 60)[:-1]
    caps = np.full(ncal, 8, int); caps[1500:1700] = 5
    sl = {(r.sid, int(r.entry_pos)): (int(r.entry_pos), np.full(130, float(opens[r.sid][int(r.entry_pos)]) * 0.85)) for r in sig.itertuples()}
    hi = {s: (pd.Series(c).rolling(120).max().to_numpy() <= c) for s, c in ((s, np.asarray(closes[s], float)) for s in set(sig["sid"]))}
    CFG = {"plain": {}, "stop_fix": dict(stop=("fix", 0.10)), "stop_trail": dict(stop=("trail", 0.15)), "log": dict(_log=True),
           "queue": dict(d_max=2, queue_days=3, _log=True), "bench": dict(cash_mode="bench", bench=bench),
           "weak_maxw": dict(weak=wk, weak_size=0.5, report_maxw=True, maxw_detail=True),
           "weight_fn": dict(weight_fn=lambda batch, t, eq, cash: [eq / 8 * (1.0 + 0.1 * (i % 2)) for i in range(len(batch))]),
           "caps": dict(n_slots=caps), "cap_fn": dict(cap_fn=lambda sid, t, hs: not (str(sid).startswith("2") and len(hs) >= 4), _log=True),
           "pick": dict(pick="relvol"), "tradable": dict(tradable=trad), "tradable_delist": dict(tradable=trad, delist=dl, _audit=True, _log=True),
           "stop_line": dict(stop_line=sl, tradable=trad),
           # ⭐ P9 的五個參數（改前引擎就有）⇒ 改前／改後必須連 x_ 鍵都逐位元同
           "P9 2-A k=2＋audit": dict(entry_tranches=2, _audit=True), "P9 2-A k=3": dict(entry_tranches=3),
           "P9 2-B ⓐ gain＋audit": dict(add_rule={"kind": "gain", "x": 0.15}, _audit=True),
           "P9 2-B ⓐ gain partial": dict(add_rule={"kind": "gain", "x": 0.15, "short": "partial"}),
           "P9 2-B ⓑ flag": dict(add_rule={"kind": "flag", "flags": hi}), "P9 2-B ⓒ hold": dict(add_rule={"kind": "hold", "days": 40}),
           "P9 2-C ⓐ trim＋audit": dict(trim_rule={"x": 0.10, "frac": 0.5}, _audit=True),
           "P9 2-C ⓐ trim（kind='loss' 明寫）": dict(trim_rule={"kind": "loss", "x": 0.10, "frac": 0.5}),
           "P9 2-C ⓐ trim＋tradable＋delist＋audit＋log": dict(trim_rule={"x": 0.10, "frac": 0.5}, tradable=trad, delist=dl, _audit=True, _log=True),
           "P9 2-B ⓐ gain＋tradable＋delist＋audit": dict(add_rule={"kind": "gain", "x": 0.15}, tradable=trad, delist=dl, _audit=True),
           "P9 2-C ⓒ mult 1.5 MA60": dict(size_mult_by_regime={"mult": 1.5, "ma": 60, "bench": bench}),
           "P9 2-C ⓓ mult 0.5 MA20": dict(size_mult_by_regime={"mult": 0.5, "ma": 20, "bench": bench}),
           "P9 2-C ⓕ regime_trim MA60＋audit": dict(regime_trim={"hold": 0.5, "ma": 60, "bench": bench}, _audit=True),
           "P9 2-C ⓗ regime_trim MA10＋tradable": dict(regime_trim={"hold": 0.5, "ma": 10, "bench": bench}, tradable=trad)}
    n_ok = n_all = 0; bad = []
    for name, cfg in CFG.items():
        for seed in (0, 1):
            outs = []
            for eng in (R0, R):
                kw = dict(cfg); lg = [] if kw.pop("_log", False) else None; au = [] if kw.pop("_audit", False) else None
                N = kw.pop("n_slots", 8)
                o = eng.simulate_mtm(sig, "H120", N, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, log=lg, audit=au, **kw)
                outs.append((o, repr(lg), repr(au)))
            ok, why = same_out(outs[0][0], outs[1][0])
            ok = ok and outs[0][1] == outs[1][1] and outs[0][2] == outs[1][2]
            n_all += 1; n_ok += ok
            if not ok:
                bad.append((name, seed, why))
        print(f"  {name} ✓" if not any(b[0] == name for b in bad) else f"  {name} ✗", flush=True)
    n_p9 = sum(k.startswith("P9") for k in CFG)
    chk(f"A/B 矩陣：{len(CFG)} 種既有參數組合（其中 P9 五參數 {n_p9} 種）× 2 種子 ＝ {n_all} 組，改前／改後逐位元相同（equity bytes、全部回傳鍵含 x_、log、audit）",
        n_ok == n_all, f"{n_ok}/{n_all}；不同 {bad[:3]}")
    EXTRA["A/B 組合"] = list(CFG)


# ─────────────────────────── 回歸閘 2（跑兩支既有 selftest；它們寫的結果檔讀完就寫回原位元組）
def gate2():
    os.chdir(REPO)
    d9 = os.path.join(REPO, "backtest", "resultsp9_engine")
    snap = {f: open(os.path.join(d9, f), "rb").read() for f in os.listdir(d9) if os.path.isfile(os.path.join(d9, f))}
    print(f"── 回歸閘 2（先存 resultsp9_engine/ {len(snap)} 個檔的位元組，跑完寫回）")
    runs = [("selftest_p9engine.py all", [PY, os.path.join(REPO, "backtest", "selftest_p9engine.py"), "all"]),
            ("selftest_p9_builders fixtures", [PY, "-m", "backtest.selftest_p9_builders", "fixtures"]),
            ("selftest_p9_builders real", [PY, "-m", "backtest.selftest_p9_builders", "real"]),
            ("selftest_p9_builders addcount --procs 1", [PY, "-m", "backtest.selftest_p9_builders", "addcount", "--procs", "1"])]
    got = {}
    try:
        for nm, cmd in runs:
            t0 = time.time()
            p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            got[nm] = {"rc": p.returncode, "secs": round(time.time() - t0), "tail": p.stdout[-1500:], "err": p.stderr[-1500:] if p.returncode else ""}
            print(f"  [{nm}] rc={p.returncode}（{got[nm]['secs']}s）", flush=True)
        now = {f: open(os.path.join(d9, f), "rb").read() for f in os.listdir(d9) if os.path.isfile(os.path.join(d9, f))}
        js = {}
        for tag in ("fixtures", "gate1", "gate2", "nonid", "builders_fixtures", "builders_real"):
            js[tag] = json.loads(now[f"{tag}.json"].decode("utf-8"))
        csv_same = now.get("b2_addcounts.csv") == snap.get("b2_addcounts.csv")
        s_old = json.loads(snap["b2_addcounts_summary.json"]); s_new = json.loads(now["b2_addcounts_summary.json"])
        cells_same = json.dumps(s_old["cells"], sort_keys=True) == json.dumps(s_new["cells"], sort_keys=True)
        new_files = sorted(set(now) - set(snap))
    finally:
        for f in list(os.listdir(d9)):
            pth = os.path.join(d9, f)
            if os.path.isfile(pth) and f not in snap:
                os.remove(pth)
        for f, b in snap.items():
            open(os.path.join(d9, f), "wb").write(b)
        back = all(open(os.path.join(d9, f), "rb").read() == b for f, b in snap.items())
        print(f"  已寫回 {len(snap)} 個檔的原位元組：{back}")
    for tag, want_n in (("fixtures", 48), ("gate1", 4), ("gate2", 13), ("nonid", 12)):
        d = js[tag]
        chk(f"selftest_p9engine {tag}：{d['n'] - d['fail']}/{d['n']} 過（P9 交件時 {want_n} 條全過）", d["fail"] == 0 and d["n"] == want_n,
            "; ".join(c["name"][:60] for c in d["checks"] if not c["ok"])[:500])
    chk("selftest_p9engine.py all 結束碼 0", got["selftest_p9engine.py all"]["rc"] == 0, got["selftest_p9engine.py all"]["err"][-300:])
    base = [c for c in js["gate2"]["checks"] if c["name"].startswith("researchp9 base 臂 cells.csv")]
    chk("P9 基準臂在原資料原窗（0dc5d62b2a archive、浮動窗 [523,2855)）重現 年化中位 +27.69%／回落中位 −42.5%（cells.csv 逐位元）",
        len(base) == 1 and base[0]["ok"] and "+27.69%" in base[0]["name"] and "-42.5%" in base[0]["name"],
        (base[0]["name"] + "｜" + base[0]["detail"]) if base else "找不到")
    for tag, want_n in (("builders_fixtures", 34), ("builders_real", 11)):
        d = js[tag]
        chk(f"selftest_p9_builders {tag.split('_')[1]}：{d['n'] - d['fail']}/{d['n']} 過（交件時 {want_n} 條全過）", d["fail"] == 0 and d["n"] == want_n,
            "; ".join(c["name"][:60] for c in d["checks"] if not c["ok"])[:500])
    for nm in ("selftest_p9_builders fixtures", "selftest_p9_builders real", "selftest_p9_builders addcount --procs 1"):
        chk(f"{nm} 結束碼 0", got[nm]["rc"] == 0, got[nm]["err"][-300:])
    chk("selftest_p9_builders addcount：2-B 三格 × 200 顆的加成計數 b2_addcounts.csv 與入庫版逐位元組相同、summary 的 cells 相同",
        csv_same and cells_same, f"csv 同 {csv_same}／cells 同 {cells_same}")
    chk("既有結果檔已逐位元組寫回（⛔ 不留下對 resultsp9_engine/ 的改動）", back and not new_files, f"多出來的檔 {new_files}")
    EXTRA["子行程"] = {k: {"rc": v["rc"], "secs": v["secs"]} for k, v in got.items()}
    EXTRA["P9 gate2 逐條"] = [(c["name"], c["ok"]) for c in js["gate2"]["checks"]]
    EXTRA["P9 gate1 逐條"] = [(c["name"], c["ok"], c["detail"]) for c in js["gate1"]["checks"]]


# ─────────────────────────── ⛔ 不是恆等輸出（真資料；⛔ 只看計數與 sha）
def nonid(seeds=5):
    os.chdir(REPO)
    from backtest import researchP9run as P
    R = engine_new()
    print("── ⛔ 不是恆等輸出：PREREGP9 主窗設定（researchP9run.setup：edc6f8002f 快照、S1、H120、N=8、種子 99000＋r）；⛔ 只報 sha 是否不同與觸發次數")
    info = P.setup(lambda x: None)
    RRa = engine_ratio()
    pre = pd.read_csv(os.path.join(OUT, "pre_B_seeds.csv")).set_index("r")
    KEEP = ("x_new_n", "x_add_trig", "x_add_n", "x_add_short", "x_add_blocked_days", "x_trim_n", "x_trim_blocked_days")
    G = P._G

    def one(eng, kw, seed):
        o = eng.simulate_mtm(G["sig"], P.RULE, P.N_MAIN, np.random.default_rng(seed), G["closes"], G["opens"], G["ncal"],
                             return_equity=True, report_maxw=True, **kw)
        r = {"sha": hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest(), **{k: int(o[k]) for k in KEEP if k in o}}
        del o                                           # ⛔ 年化／回落等鍵不讀、不存
        return r
    rows = []
    for r in range(seeds):
        seed = P.SEED0 + r
        b = one(R, {}, seed); y = one(R, KW_BY, seed); c = one(R, KW_CI, seed)
        yr = one(RRa, KW_BY, seed); cr = one(RRa, KW_CI, seed)
        rows.append({"r": r, "base_sha_eq_pre": b["sha"] == pre.loc[r, "eq_sha"],
                     "By_diff": y["sha"] != b["sha"], **{"By_" + k: v for k, v in y.items() if k != "sha"},
                     "Ci_diff": c["sha"] != b["sha"], **{"Ci_" + k: v for k, v in c.items() if k != "sha"},
                     "By_比值式_sha同": yr["sha"] == y["sha"], "By_比值式_trig": yr["x_add_trig"],
                     "Ci_比值式_sha同": cr["sha"] == c["sha"], "Ci_比值式_trim_n": cr["x_trim_n"],
                     "pre_dn_觸發": int(pre.loc[r, "dn_觸發"]), "pre_dn_成交": int(pre.loc[r, "dn_成交"]),
                     "pre_up_觸發": int(pre.loc[r, "up_觸發"]), "pre_up_成交": int(pre.loc[r, "up_成交"])})
        z = rows[-1]
        print(f"  r={r}：By 觸發 {z['By_x_add_trig']}／加成 {z['By_x_add_n']}／現金不足 {z['By_x_add_short']}／漲停停牌延 {z['By_x_add_blocked_days']}｜"
              f"Ci 賣半 {z['Ci_x_trim_n']}／延 {z['Ci_x_trim_blocked_days']}｜pre(近似) dn 觸發 {z['pre_dn_觸發']}、up 成交 {z['pre_up_成交']}", flush=True)
    D = pd.DataFrame(rows)
    chk(f"基準臂（全關）{seeds} 顆 equity sha ＝ resultsAvg/pre_B_seeds.csv（＝ resultsP9run 基準臂）", bool(D["base_sha_eq_pre"].all()))
    chk(f"乙一 By（add_rule loss 10%）：{seeds} 顆都與全關不同、每顆都有加成", bool(D["By_diff"].all() and (D["By_x_add_n"] > 0).all()),
        f"觸發 {D['By_x_add_trig'].tolist()}／加成 {D['By_x_add_n'].tolist()}／現金不足 {D['By_x_add_short'].tolist()}")
    chk(f"乙二 Ci（trim_rule gain 15%）：{seeds} 顆都與全關不同、每顆都有賣半", bool(D["Ci_diff"].all() and (D["Ci_x_trim_n"] > 0).all()),
        f"賣半 {D['Ci_x_trim_n'].tolist()}")
    EXTRA["setup"] = info
    EXTRA["逐顆（只有計數與 sha 比較）"] = rows
    EXTRA["描述_對 pre_B 近似"] = {"Ci 賣半 − pre up 成交": (D["Ci_x_trim_n"] - D["pre_up_成交"]).tolist(),
                               "By 觸發 − pre dn 觸發": (D["By_x_add_trig"] - D["pre_dn_觸發"]).tolist(),
                               "說明": "pre_B 是在【基準臂】的部位上用比值式數的近似；By／Ci 開啟後現金與之後的進場會變 ⇒ 不要求相等，只描述"}
    EXTRA["描述_字面式 vs 比值式"] = {"By sha 相同顆數": int(D["By_比值式_sha同"].sum()), "Ci sha 相同顆數": int(D["Ci_比值式_sha同"].sum()),
                               "By 觸發差（比值式−字面式）": (D["By_比值式_trig"] - D["By_x_add_trig"]).tolist(),
                               "Ci 賣半差（比值式−字面式）": (D["Ci_比值式_trim_n"] - D["Ci_x_trim_n"]).tolist()}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.chdir(REPO)
    t0 = time.time(); fails = 0
    for m_, fn in (("fixtures", fixtures), ("gate1", gate1), ("gate2", gate2), ("nonid", nonid)):
        if mode in (m_, "all"):
            RESULTS.clear(); EXTRA.clear(); fn(); dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

# -*- coding: utf-8 -*-
"""PREREG攤平停利 seq3 乙二 第三個開關（research11.simulate_mtm 的 trim_proceeds="next"：賣得現金流向下一檔候選）的 fixture 與兩道回歸閘。
回測線，2026-09-25。依據：台股策略線登錄 PREREG攤平停利 seq3（sha 31cc3c4e5d565dda）乙二 ①～④；裁定線 seq180 §二①、seq181 核准。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_avgengine2.py fixtures  # ①～④ 手算小例、不重複買、tradable、同日、連鎖、防呆、
                                                                                        # 隨機不變式（獨立重建）、無前視、鑑別力（突變體）
    ... gate1      # 回歸閘 1：regress_tradability(18)＋regress_delist(6)＋改前（git blob）／改後 A/B（真資料，33 種既有組合 × 2 種子）
    ... gate2      # 回歸閘 2：selftest_avgengine.py all（內含 selftest_p9engine all、selftest_p9_builders fixtures／real／addcount、
                   #           P9 基準臂 +27.69%／−42.5% 逐位元）＋ selftest_avgdown.py（F1～F10，F10 已改寫成驗新 kind）
    ... nonid      # ⛔ 不是恆等輸出：乙要跑的設定（researchP9run 主窗）⇒ 開關開／關 equity 不同；⛔ 只報次數與 sha 是否不同
    ... all

⭐ 改前引擎一律從 git 物件庫取（ORIG_BLOB ＝ 改動前 HEAD:backtest/research11.py，HEAD d609e89a95），⛔ 不靠工作目錄裡的副本。
⭐ 改後引擎 ＝ backtest.research11；環境變數 AVG_ENGINE2_SRC 指到另一個檔 ⇒ fixtures／gate1 改測那個檔（換檔前先在暫存檔自測）。
⭐ 突變體（鑑別力）：M_amt 待買改成半個 slot／M_who 待買配給挑中名單最後一檔／M_slots 待買不受槽位限制／M_drop 池空就把待買丟回
   一般現金／M_held 待買可以買已持有的／M_xlag 賣半觸發改讀當天收盤（前視）⇒ 每一個都必須被至少一條檢查抓到。
⛔ 本檔【不跑乙的 2 格】、⛔ 不讀任何年化／回落：nonid 只取計數鍵與 equity 的 sha（其他鍵當場丟掉）。
⚠ gate2 跑的既有 selftest 會改寫 backtest/resultsAvg/engine_b_*.json 與 backtest/resultsp9_engine/ 下已入庫的結果檔
   ⇒ 跑前存位元組、讀完結果後逐檔寫回原位元組（⛔ 不留下對既有檔的改動）；摘要寫進本檔的 engine_b2_gate2.json。
結果寫到 backtest/resultsAvg/engine_b2_{fixtures,gate1,gate2,nonid}.json。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import deque

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest", "resultsAvg")
PY = sys.executable
ORIG_BLOB = "d8d177e7a597237c0318f1e9473584ee92a022e2"      # 改動前 HEAD:backtest/research11.py（HEAD d609e89a95＝loss／gain 兩型交件）
GAIN = {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}                   # 乙二 2-C ⓘ（ENGINE_KW_B["Ci"]）
NX = {**GAIN, "trim_proceeds": "next"}                                           # 乙二 seq3：賣得現金流向下一檔
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9      # noqa: E402  ⭐ 只借小工具，⛔ 不改它
px, run, same_out, trad_of, close_to, fin, recs, NC = SP9.px, SP9.run, SP9.same_out, SP9.trad_of, SP9.close_to, SP9.fin, SP9.recs, SP9.NC


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"engine_b2_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if EXTRA:
        d["extra"] = EXTRA
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


# ─────────────────────────── 引擎：新／改前／突變體
def _new_src():
    p = os.environ.get("AVG_ENGINE2_SRC")
    if p:
        return open(p, encoding="utf-8").read(), p
    from backtest import research11 as R
    return open(R.__file__, encoding="utf-8").read(), R.__file__


def engine_new():
    p = os.environ.get("AVG_ENGINE2_SRC")
    if p:
        return SP9._load_src(open(p, encoding="utf-8").read(), "backtest._r11_new2", p)
    from backtest import research11 as R
    return R


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return SP9._load_src(src, "backtest._r11_orig_avg2", os.path.join(REPO, "backtest", "research11.py"))


MUTANTS = {
    "M_amt": ('amt, _nx_t = _nx["lots"].pop(0)', '_, _nx_t = _nx["lots"].pop(0); amt = 0.5 * slot'),
    "M_who": ('_nx_buy = _nx is not None and bool(_nx["lots"])', '_nx_buy = _nx is not None and bool(_nx["lots"]) and j == len(take) - 1'),
    "M_slots": ("avail = int(min(slots_free, d_free))", 'avail = int(min(slots_free, d_free)) + (len(_nx["lots"]) if _nx is not None else 0)'),
    "M_drop": ('_nx["empty_days"] += 1', '_nx["empty_days"] += 1; _nx["lots"].clear()'),
    "M_held": ('cand = g[~g["sid"].isin(held)]', 'cand = g[~g["sid"].isin(held)] if (_nx is None or not _nx["lots"]) else g'),
}


def engine_mut(tag):
    src, f = _new_src()
    if tag == "M_xlag":
        lines = src.split("\n"); n = 0
        for i, ln in enumerate(lines):
            if "# _XLAG" in ln and "[t - 1]" in ln:
                lines[i] = ln.replace("[t - 1]", "[t]"); n += 1
        if n < 7:
            raise SystemExit(f"⛔ _XLAG 突變點只找到 {n} 個（應 ≥ 7）")
        src = "\n".join(lines)
    else:
        a, b = MUTANTS[tag]
        if src.count(a) != 1:
            raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一：{a!r}")
        src = src.replace(a, b)
    return SP9._load_src(src, f"backtest._r11_{tag}", f)


def strip(o):
    return {k: v for k, v in o.items() if k != "_audit"}


def nxb(o):
    """待買買進的紀錄 (t, sid, amt)。"""
    return [(r["t"], r["sid"], r["amt"]) for r in o["_audit"] if r["side"] == "buy" and r.get("kind") == "nx"]


def trims(o):
    return [r for r in o["_audit"] if r.get("kind") == "trim"]


# ─────────────────────────── 獨立重建（⛔ 不呼叫引擎內部；只讀 audit 與訊號列）
def replay(o, rows, N):
    """由 audit 逐日重建持有與待買佇列，驗 ①～④ 與不重複買；回 (ok, why, 統計)。"""
    ent = {}
    for s, e, x in rows:
        ent.setdefault(e, []).append(s)
    by_t = {}
    for r in o["_audit"]:
        by_t.setdefault(int(r["t"]), []).append(r)
    held = set(); lots = deque(); waits = []; st = {"full": 0, "empty": 0, "nx": 0, "maxheld": 0, "lots_made": 0}
    for t in sorted(set(by_t) | set(ent)):
        rt = by_t.get(t, []); i = 0
        while i < len(rt) and rt[i]["side"] == "sell":
            r = rt[i]
            if r.get("kind") == "trim":
                lots.append((r["amt"] - r["cost"], t)); st["lots_made"] += 1
            elif "kind" not in r:
                if r["sid"] not in held:
                    return False, f"t={t} 賣出未持有的 {r['sid']}", st
                held.discard(r["sid"])
            else:
                return False, f"t={t} 未預期的賣出 kind {r.get('kind')}", st
            i += 1
        bs = rt[i:]
        if any(r["side"] != "buy" for r in bs):
            return False, f"t={t} 買進之後又有賣出（同日順序錯）", st
        free = N - len(held)
        if t in ent:
            cand = [s for s in ent[t] if s not in held]
            if lots and free <= 0:
                st["full"] += 1
            if lots and free > 0 and not cand:
                st["empty"] += 1
            want = min(free, len(cand), len(lots)) if free > 0 else 0
            kinds = [r.get("kind") for r in bs]
            n_nx = kinds.count("nx")
            if n_nx != want:
                return False, f"t={t} 待買買進 {n_nx} 檔，應 min(空槽 {free}, 候選 {len(cand)}, 待買 {len(lots)}) ＝ {want}", st
            if kinds != sorted(kinds, key=lambda k: 0 if k == "nx" else 1):
                return False, f"t={t} 一般新部位排在待買之前", st
        elif bs:
            return False, f"t={t} 不是量測日卻有買進", st
        for r in bs:
            if r["sid"] in held:
                return False, f"t={t} 買了已持有的 {r['sid']}", st
            if r.get("kind") == "nx":
                a, ts = lots.popleft()
                if repr(float(r["amt"])) != repr(float(a)):
                    return False, f"t={t} 待買金額 {r['amt']!r} ≠ 佇列頭 {a!r}（應全額、先進先出）", st
                waits.append(t - ts); st["nx"] += 1
            held.add(r["sid"])
        st["maxheld"] = max(st["maxheld"], len(held))
        if len(held) > N:
            return False, f"t={t} 持有 {len(held)} 檔 ＞ 槽位 {N}", st
    got = (o.get("x_nx_n"), o.get("x_nx_waits"), o.get("x_nx_full_days"), o.get("x_nx_empty_days"), o.get("x_nx_pending_end"))
    exp = (st["nx"], waits, st["full"], st["empty"], len(lots))
    if got != exp:
        return False, f"引擎計數 {got} ≠ 重建 {exp}", st
    if not close_to(o["x_nx_pending_amt_end"], float(sum(a for a, _ in lots))):
        return False, "期末待買金額不符", st
    return True, "", st


def world(rng, n_sid=5, trad=False):
    """隨機小世界：5 檔上飄的隨機漫步、每 10 天一個量測日、每個量測日隨機 0～4 檔訊號、N ∈ {2,3,4}。"""
    sids = [f"S{i}" for i in range(n_sid)]
    pr = {}
    for s in sids:
        c = 10 * np.exp(np.cumsum(rng.normal(0.004, 0.035, NC)))
        o = np.r_[10.0, c[:-1]] * np.exp(rng.normal(0, 0.01, NC))
        pr[s] = (o, c)
    rows = []
    for d in range(5, 80, 10):
        for s in rng.choice(sids, int(rng.integers(0, 5)), replace=False):
            rows.append((str(s), d, min(NC - 1, d + int(rng.integers(10, 45)))))
    N = int(rng.integers(2, 5))
    extra = {}
    if trad:
        up = [(s, int(t)) for s in sids for t in rng.choice(NC, 6, replace=False)]
        dn = [(s, int(t)) for s in sids for t in rng.choice(NC, 6, replace=False)]
        ha = [(s, int(t)) for s in sids for t in rng.choice(NC, 4, replace=False)]
        extra = dict(tradable=trad_of(pr, up=up, dn=dn, halt=ha))
    return pr, rows, N, extra


# ─────────────────────────── 逐條 fixture（每條回 bool；同一組檢查也拿去跑突變體 ⇒ 鑑別力）
def lot_of(amt, o_px, ep, C, frac=0.5):
    """獨立手算：部位名目 amt、進場 ep、在開盤 o_px 賣 frac ⇒ 淨入帳（成交 − frac×B×COST；沒動過的部位 B＝amt）。"""
    return amt * frac * o_px / ep - amt * frac * C


def fx_list(R, C, verbose=True):
    """回 [(名稱, ok, 細節)]。"""
    out = []

    def add(nm, ok, det=""):
        out.append((nm, bool(ok), det))

    def safe(fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001  ⭐ 突變體可能直接炸 ⇒ 記成沒過
            out.append((fn.__name__, False, f"例外 {type(e).__name__}: {e}"))

    pG = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, 30, 11.8, 11.8), (30, NC, 13, 13))}

    def f1_simple():
        # ① 槽滿等待（N=2）：A、B 在 10 進；A 收盤[20]＝11.6 ⇒ t=21 開盤 11.8 賣半 ⇒ 待買 L；t=30 量測日（C）槽滿 ⇒ 等；
        #   t=35 B 出場；t=40 量測日（D）⇒ D 用 L 全額買；期末手算
        pr = {"A": pG["A"], "B": px(), "C": px(), "D": px()}
        rows = [("A", 10, 60), ("B", 10, 35), ("C", 30, 70), ("D", 40, 80)]
        o = run(R, rows, pr, 2, **NX)
        L = lot_of(0.5, 11.8, 10.0, C)
        exp = 0.5 * (1 - C) + (0.25 * 1.3 - 0.25 * C) + L * (1 - C)
        nb = nxb(o)
        ok = len(nb) == 1 and nb[0][:2] == (40, "D") and close_to(nb[0][2], L) and not [r for r in o["_audit"] if r["side"] == "buy" and r["t"] == 30] \
            and (o["x_nx_full_days"], o["x_nx_empty_days"], o["x_nx_waits"], o["x_nx_pending_end"]) == (1, 0, [19], 0) and close_to(fin(o), exp)
        add("①a 槽滿等待（N=2）：t=21 賣半得 L＝0.5×0.5×11.8/10 − 0.25×COST；t=30 槽滿不買（full_days 1）；t=40 D 用 L 全額買（等 19 天）；期末手算",
            ok, f"待買買進 {nb}；L {L!r}；期末 {fin(o):.12f} vs {exp:.12f}；full {o['x_nx_full_days']}")
        oo = run(R, rows, pr, 2, **GAIN)
        d_off = [r for r in oo["_audit"] if r["side"] == "buy" and r["t"] == 40]
        add("①a' 同一例開關關閉（＝乙三閒置版）：t=40 D 照一般新部位買 min(slot, 現金)（⛔ 沒有 kind nx、金額 ≠ L）⇒ 開與關確實不同",
            len(d_off) == 1 and "kind" not in d_off[0] and not close_to(d_off[0]["amt"], L) and not nxb(oo) and "x_nx_n" not in oo,
            f"關閉時 t=40 買 {[(r['sid'], round(r['amt'], 6)) for r in d_off]}")

    def f1_two_lots():
        # ① 兩筆待買、一個空槽（N=3）：A 收盤[20] 賣半（t=21）、B 收盤[24] 賣半（t=25）⇒ 兩筆待買；C 在 40 出場 ⇒ t=45 量測日（D、E、F）
        #   只有 1 個空槽 ⇒ 只買 1 檔、用【先賣的】A 那筆；t=50 量測日（G）槽滿 ⇒ 等；t=60 A 出場 ⇒ t=65 量測日（H）用 B 那筆
        pr = {"A": pG["A"], "B": px((0, 24, 10, 10), (24, 25, 10, 11.6), (25, NC, 11.8, 11.8)),
              "C": px(), "D": px(), "E": px(), "F": px(), "G": px(), "H": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("C", 10, 40), ("D", 45, 90), ("E", 45, 90), ("F", 45, 90), ("G", 50, 95), ("H", 65, 98)]
        o = run(R, rows, pr, 3, **NX)
        La = lot_of(1 / 3, 11.8, 10.0, C); Lb = lot_of(1 / 3, 11.8, 10.0, C)
        nb = nxb(o)
        b45 = [r for r in o["_audit"] if r["side"] == "buy" and r["t"] == 45]
        ok_ = len(nb) == 2 and [x[0] for x in nb] == [45, 65] and nb[1][1] == "H" and close_to(nb[0][2], La) and close_to(nb[1][2], Lb) \
            and len(b45) == 1 and o["x_nx_waits"] == [24, 40] and o["x_nx_full_days"] == 1
        ok2, why, st = replay(o, rows, 3)
        add("①b 兩筆待買、一個空槽（N=3）：t=45 只買 1 檔（候選 3、空槽 1）且用先賣的那筆；t=50 槽滿等；t=65 用第二筆（等 24／40 天）；持有從未 ＞ 3",
            ok_ and ok2 and st["maxheld"] <= 3, f"待買買進 {[(t, s, round(a, 9)) for t, s, a in nb]}；t=45 買 {len(b45)} 檔；waits {o['x_nx_waits']}；"
                                                 f"full {o['x_nx_full_days']}；重建 {why or 'OK'}")

    def f2_rng():
        # ② 隨機挑同 rng：N=3、A 持有並賣半；t=40 量測日 5 檔候選、2 個空槽 ⇒ 引擎那一次 permutation 的第 1 檔用待買、第 2 檔是一般新部位
        #   預期值：另開同種子 rng，照引擎的抽法重播（t=10 permutation(1)、t=40 permutation(5)）；開關關閉時挑中的 2 檔相同
        pr = {"A": pG["A"], **{s: px() for s in "DEFGH"}}
        rows = [("A", 10, 70)] + [(s, 40, 80) for s in "DEFGH"]
        bad = []
        for seed in range(30):
            r2 = np.random.default_rng(seed); r2.permutation(1); pm = r2.permutation(5)
            want = ["DEFGH"[pm[0]], "DEFGH"[pm[1]]]
            o = run(R, rows, pr, 3, seed=seed, **NX); oo = run(R, rows, pr, 3, seed=seed, **GAIN)
            b = [(r["sid"], r.get("kind")) for r in o["_audit"] if r["side"] == "buy" and r["t"] == 40]
            b0 = [r["sid"] for r in oo["_audit"] if r["side"] == "buy" and r["t"] == 40]
            if b != [(want[0], "nx"), (want[1], None)] or sorted(b0) != sorted(want):
                bad.append((seed, b, b0, want))
        add("② 隨機挑同一顆 rng（30 顆種子）：待買配給引擎同一次 permutation 的第 1 檔、第 2 檔是一般新部位；關閉時挑中的是同 2 檔（⛔ 沒有另外抽）",
            not bad, f"不符 {bad[:2]}")

    def f3_full():
        # ③ 全額（N=4）：A 漲到 50 ⇒ t=21 開盤 50 賣半得 0.625 − 0.125×COST；B 在 30 出場 ⇒ t=35 量測日 E 用全額買，而當天 slot≈0.5
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 50), (21, NC, 50, 50)), "B": px(), "C": px(), "D": px(), "E": px()}
        rows = [("A", 10, 70), ("B", 10, 30), ("C", 10, 70), ("D", 10, 70), ("E", 35, 80)]
        o = run(R, rows, pr, 4, **NX)
        tr = trims(o); nb = nxb(o)
        L = lot_of(0.25, 50.0, 10.0, C)
        slot35 = float(o["equity"][34]) / 4
        ok = len(nb) == 1 and nb[0][:2] == (35, "E") and len(tr) == 1 and repr(float(nb[0][2])) == repr(float(tr[0]["amt"] - tr[0]["cost"])) \
            and close_to(nb[0][2], L) and nb[0][2] > slot35 and not close_to(nb[0][2], 0.5 * slot35)
        add("③ 全額：待買金額 ＝ 賣半那筆的 成交 − 成本（逐位元）＝ 手算 0.625 − 0.125×COST，大於當天 slot（⛔ 不取 min(slot)、⛔ 不是半個 slot）",
            ok, f"待買 {nb}；賣半 {[(r['t'], r['amt'], r['cost']) for r in tr]}；當天 slot {slot35:.6f}")

    def f4_empty():
        # ④ 池空留現金（N=3）：A 賣半（t=21，之後價平 11.8）；t=30 量測日只有 A、B 的訊號（都持有）⇒ 池空、待買留著（empty_days 1）；
        #   t=33 沒有訊號（引擎看不到 ⇒ 不計）；t=45 量測日 E ⇒ 用待買買；t=22～44 equity 不動（現金報酬 0）
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, NC, 11.8, 11.8)), "B": px(), "E": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("A", 30, 75), ("B", 30, 75), ("E", 45, 90)]
        o = run(R, rows, pr, 3, **NX)
        nb = nxb(o); L = lot_of(1 / 3, 11.8, 10.0, C)
        eq = o["equity"]
        ok = len(nb) == 1 and nb[0][:2] == (45, "E") and close_to(nb[0][2], L) and (o["x_nx_empty_days"], o["x_nx_full_days"], o["x_nx_waits"]) == (1, 0, [24]) \
            and eq[22:45].tobytes() == np.full(23, eq[22]).tobytes() and not [r for r in o["_audit"] if r["side"] == "buy" and r["t"] == 30]
        add("④ 池空留現金：t=30 候選全是已持有的 ⇒ 不買、empty_days 1；沒有訊號的 t=33 不計；t=45 用待買全額買 E（等 24 天）；t=22～44 equity 逐位元不動",
            ok, f"待買買進 {nb}；empty {o['x_nx_empty_days']}；waits {o['x_nx_waits']}")

    def f5_held():
        # 不重複買已持有的：N=3、A（賣半）與 B 持有；t=30 量測日 A、B、F 三檔訊號、1 個空槽 ⇒ 50 顆種子都只能買 F
        pr = {"A": px((0, 20, 10, 10), (20, 21, 10, 11.6), (21, NC, 11.8, 11.8)), "B": px(), "F": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("A", 30, 75), ("B", 30, 75), ("F", 30, 75)]
        bad = []
        for seed in range(50):
            o = run(R, rows, pr, 3, seed=seed, **NX)
            nb = nxb(o)
            if [x[:2] for x in nb] != [(30, "F")]:
                bad.append((seed, nb))
        add("不重複買已持有的：候選含已持有的 A（被賣半的那檔）與 B ⇒ 50 顆種子的待買都買 F", not bad, f"不符 {bad[:3]}")

    def f6_trad():
        # tradable：t=40 候選 D、E，2 個空槽（N=3、A 持有並賣半）；引擎那次 permutation 的第 1 檔開盤漲停 ⇒ 不遞補、待買配給第 2 檔；當天只買 1 檔
        pr = {"A": pG["A"], "D": px(), "E": px()}
        rows = [("A", 10, 70), ("D", 40, 80), ("E", 40, 80)]
        r2 = np.random.default_rng(0); r2.permutation(1); pm = r2.permutation(2)
        first, second = "DE"[pm[0]], "DE"[pm[1]]
        o = run(R, rows, pr, 3, tradable=trad_of(pr, up=[(first, 40)]), **NX)
        b = [(r["sid"], r.get("kind")) for r in o["_audit"] if r["side"] == "buy" and r["t"] == 40]
        add("tradable：挑中的第 1 檔開盤漲停 ⇒ 不遞補（當天只買 1 檔）；待買不消耗、配給第 2 檔；x_nx_blocked＝1",
            b == [(second, "nx")] and o["x_nx_blocked"] == 1 and o["tr_limit_up"] == 1, f"t=40 買 {b}；blocked {o['x_nx_blocked']}")

    def f7_sameday():
        # 同日（讀法）：A 收盤[29]＝11.6 ⇒ t=30 開盤賣半；t=30 本身是量測日（E）⇒ 當天就用待買買 E（waits 0）
        pr = {"A": px((0, 29, 10, 10), (29, 30, 10, 11.6), (30, NC, 11.8, 11.8)), "E": px()}
        rows = [("A", 10, 70), ("E", 30, 80)]
        o = run(R, rows, pr, 2, **NX)
        ts = [r["t"] for r in trims(o)]
        seq = [(r["side"], r.get("kind")) for r in o["_audit"] if r["t"] == 30]
        add("同日：賣出日本身是量測日 ⇒ 當天先賣半再用待買買（waits [0]；audit 順序 賣 → 買）",
            ts == [30] and nxb(o)[:1] and nxb(o)[0][:2] == (30, "E") and o["x_nx_waits"] == [0] and seq == [("sell", "trim"), ("buy", "nx")], f"{seq}")

    def f8_chain():
        # 連鎖：待買買進的 E 自己漲 15% 也賣半（每部位一次）⇒ 再成一筆待買 ⇒ 下一個量測日買 F
        pr = {"A": pG["A"], "E": px((0, 49, 10, 10), (49, 50, 10, 11.6), (50, NC, 11.8, 11.8)), "F": px()}
        rows = [("A", 10, 70), ("E", 40, 85), ("F", 60, 95)]
        o = run(R, rows, pr, 3, **NX)
        nb = nxb(o)
        L1 = nb[0][2] if nb else float("nan")                  # E 的名目（進場開盤 10）＝ 第一筆待買全額
        L2 = lot_of(L1, 11.8, 10.0, C)
        add("連鎖：待買買進的 E 在 +16% 賣半（t=50）⇒ 第二筆待買 ＝ E 名目 × 0.5 × 11.8/10 − 成本 ⇒ t=60 買 F；x_trim_n 2、x_nx_n 2",
            len(nb) == 2 and [x[:2] for x in nb] == [(40, "E"), (60, "F")] and close_to(nb[0][2], lot_of(1 / 3, 11.8, 10.0, C)) and close_to(nb[1][2], L2) and (o["x_trim_n"], o["x_nx_n"]) == (2, 2),
            f"{[(t, s, round(a, 9)) for t, s, a in nb]}；L1 {L1!r}")

    for fn in (f1_simple, f1_two_lots, f2_rng, f3_full, f4_empty, f5_held, f6_trad, f7_sameday, f8_chain):
        safe(fn)
    return out


def rand_invariants(R, n_w=300, seed=20260925):
    """隨機 n_w 個世界（tradable 關）：開關開 ⇒ 獨立重建（replay）逐日驗 ①～④、不重複買、全額先進先出、計數鍵。"""
    rng = np.random.default_rng(seed)
    n_ok = 0; agg = {"有待買買進": 0, "有槽滿等待": 0, "有池空等待": 0, "期末仍有待買": 0, "待買買進筆數": 0}; bad = []
    for w in range(n_w):
        pr, rows, N, _ = world(rng)
        if not rows:
            n_ok += 1; continue
        try:
            o = run(R, rows, pr, N, seed=w, **NX)
            ok, why, st = replay(o, rows, N)
        except Exception as e:  # noqa: BLE001
            ok, why, st = False, f"例外 {type(e).__name__}: {e}", {}
        n_ok += ok
        if not ok:
            bad.append((w, why)); continue
        agg["有待買買進"] += st["nx"] > 0; agg["有槽滿等待"] += st["full"] > 0; agg["有池空等待"] += st["empty"] > 0
        agg["期末仍有待買"] += o["x_nx_pending_end"] > 0; agg["待買買進筆數"] += st["nx"]
    return n_ok, n_w, agg, bad


def lookahead(R, n_w=300, seed=20260926):
    """無前視：改 t=s 的收盤與 s+1 起的開盤／收盤 ⇒ t ≤ s 的交易與 equity[:s] 不變；一半世界開 tradable。"""
    rng = np.random.default_rng(seed)
    n_ok = n_post = 0
    for w in range(n_w):
        pa, rows, N, extra = world(rng, trad=bool(w % 2))
        if not rows:
            n_ok += 1; continue
        exits = {x for _, _, x in rows}
        s = int(rng.integers(12, 75))
        while s in exits:
            s += 1
        pb = {}
        for i, sd in enumerate(pa):
            o, c = pa[sd][0].copy(), pa[sd][1].copy()
            f = (0.7 if (w + i) % 2 else 1.35) * np.exp(np.cumsum(rng.normal(0, 0.02, NC - s)))
            c[s:] = c[s:] * f; o[s + 1:] = o[s + 1:] * f[:-1]           # ⭐ t=s 的開盤不動（t 開盤在 t 當下已知）
            pb[sd] = (o, c)
        try:
            oa = run(R, rows, pa, N, seed=w, **NX, **extra); ob = run(R, rows, pb, N, seed=w, **NX, **extra)
            ta = [r for r in oa["_audit"] if r["t"] <= s]; tb = [r for r in ob["_audit"] if r["t"] <= s]
            pre = repr(ta) == repr(tb) and oa["equity"][:s].tobytes() == ob["equity"][:s].tobytes()
            post = repr(oa["_audit"]) != repr(ob["_audit"])
        except Exception:  # noqa: BLE001
            pre, post = False, False
        n_ok += pre; n_post += post
    return n_ok, n_post, n_w


# ─────────────────────────── fixtures
def fixtures():
    R = engine_new(); C = R.COST
    print(f"── 引擎：{'AVG_ENGINE2_SRC=' + os.environ['AVG_ENGINE2_SRC'] if os.environ.get('AVG_ENGINE2_SRC') else R.__file__}")
    import inspect
    sig_ = inspect.signature(R.simulate_mtm).parameters
    chk("開關參數：trim_proceeds，預設 None（關）", "trim_proceeds" in sig_ and sig_["trim_proceeds"].default is None)
    print("── 手算小例（①～④、不重複買、tradable、同日、連鎖）")
    FX = fx_list(R, C)
    for nm, ok, det in FX:
        chk(nm, ok, det)

    print("── 隨機不變式（獨立重建 replay：逐日 待買數 ＝ min(空槽, 候選, 待買)、全額先進先出、不重複買、持有 ≤ N、計數鍵）")
    n_ok, n_w, agg, bad = rand_invariants(R)
    chk(f"隨機 {n_w} 個世界：獨立重建全部相符", n_ok == n_w, f"{n_ok}/{n_w}；{json.dumps(agg, ensure_ascii=False)}；不符 {bad[:2]}")
    chk("隨機世界確實走到各種情形（有待買買進、槽滿等待、池空等待、期末仍有待買 各至少 10 個世界）",
        min(agg["有待買買進"], agg["有槽滿等待"], agg["有池空等待"], agg["期末仍有待買"]) >= 10, json.dumps(agg, ensure_ascii=False))
    EXTRA["隨機不變式"] = agg

    print("── 無前視（開關開；一半世界開 tradable）")
    n_ok, n_post, n_w = lookahead(R)
    chk(f"無前視（隨機 {n_w} 個世界）：t ≤ s 的交易與 equity[:s] 全部不變、且修改不是空的（之後確實不同 ≥ 一半）",
        n_ok == n_w and n_post >= n_w // 2, f"前段相同 {n_ok}/{n_w}；後段不同 {n_post}")
    EXTRA["無前視"] = {"世界": n_w, "前段相同": n_ok, "後段不同": n_post}

    print("── 鑑別力（突變體必須被抓到）")
    mut = {}
    names_fx = [nm for nm, _, _ in FX]
    for tag in ("M_amt", "M_who", "M_slots", "M_drop", "M_held", "M_xlag"):
        M = engine_mut(tag)
        fx_m = fx_list(M, C)
        failed = [nm.split("：")[0] for nm, ok, _ in fx_m if not ok]
        if tag == "M_xlag":
            n_ok_m, _, n_w_m = lookahead(M, n_w=100)
            caught_la = n_w_m - n_ok_m
            mut[tag] = {"fixture 沒過": failed, "無前視被抓到的世界": f"{caught_la}/{n_w_m}"}
            chk(f"鑑別力 {tag}（賣半觸發改讀當天收盤 ＝ 前視）：無前視檢查抓到", caught_la > 0, json.dumps(mut[tag], ensure_ascii=False))
        else:
            n_ok_m, n_w_m, _, _ = rand_invariants(M, n_w=100)
            mut[tag] = {"fixture 沒過": failed, "隨機重建沒過的世界": f"{n_w_m - n_ok_m}/{n_w_m}"}
            chk(f"鑑別力 {tag}：至少一條 fixture 或隨機重建抓到", failed or n_ok_m < n_w_m, json.dumps(mut[tag], ensure_ascii=False))
    EXTRA["突變體"] = mut
    EXTRA["fixture 名"] = names_fx

    print("── 開關關閉 ⇒ 與改前引擎（git blob）逐位元同；None 明寫 ＝ 省略；開著但沒賣半 ⇒ 只差 x_nx 鍵")
    R0 = engine_orig()
    rng = np.random.default_rng(7)
    n_same = n_all = 0; why_ = []
    for w in range(60):
        pr, rows, N, extra = world(rng, trad=bool(w % 3 == 0))
        if not rows:
            continue
        for kw0, kw1 in ((dict(), dict()), (dict(**GAIN), dict(**GAIN)), (dict(**GAIN), dict(**GAIN, trim_proceeds=None)),
                         (dict(add_rule={"kind": "loss", "x": 0.10}), dict(add_rule={"kind": "loss", "x": 0.10}, trim_proceeds=None)),
                         (dict(trim_rule={"x": 0.10, "frac": 0.5}), dict(trim_rule={"x": 0.10, "frac": 0.5}))):
            a0 = run(R0, rows, pr, N, seed=w, **kw0, **extra); a1 = run(R, rows, pr, N, seed=w, **kw1, **extra)
            ok, why = same_out(strip(a0), strip(a1))
            ok = ok and repr(a0["_audit"]) == repr(a1["_audit"])
            n_all += 1; n_same += ok
            if not ok:
                why_.append((w, why))
    chk("開關關閉（省略／None 明寫；全關、乙二 gain、乙一 loss、2-C ⓐ）× 隨機 60 個世界 ⇒ 與改前引擎逐位元同（equity、全部回傳、audit）",
        n_same == n_all, f"{n_same}/{n_all}；{why_[:2]}")
    rng = np.random.default_rng(8); n_same = n_all = 0
    for w in range(40):
        pr, rows, N, extra = world(rng)
        if not rows:
            continue
        a0 = run(R0, rows, pr, N, seed=w, trim_rule={"kind": "gain", "x": 1e9, "frac": 0.5})
        a1 = run(R, rows, pr, N, seed=w, trim_rule={"kind": "gain", "x": 1e9, "frac": 0.5}, trim_proceeds="next")
        ok, why = same_out(strip(a0), strip(a1), skip_prefix="x_nx_")
        ok = ok and repr(a0["_audit"]) == repr(a1["_audit"]) and a1["x_nx_n"] == 0 and a1["x_nx_pending_end"] == 0
        n_all += 1; n_same += ok
    chk("開關開著但從沒賣半（x＝1e9）× 隨機 40 個世界 ⇒ 與改前引擎逐位元同（只多 x_nx_ 鍵、且都是 0）", n_same == n_all, f"{n_same}/{n_all}")

    print("── 防呆")
    rows = [("A", 10, 60)]; pr = {"A": px()}
    for nm, kw in (("next 但沒開 trim_rule", dict(trim_proceeds="next")),
                   ("next ＋ trim_rule 省略 kind（2-C ⓐ）", dict(trim_rule={"x": 0.10, "frac": 0.5}, trim_proceeds="next")),
                   ("next ＋ trim_rule kind＝loss", dict(trim_rule={"kind": "loss", "x": 0.10, "frac": 0.5}, trim_proceeds="next")),
                   ("next ＋ add_rule loss", dict(add_rule={"kind": "loss", "x": 0.10}, trim_proceeds="next")),
                   ("值打錯 'Next'", dict(**GAIN, trim_proceeds="Next")), ("值給 True", dict(**GAIN, trim_proceeds=True)),
                   ("值給 'idle'", dict(**GAIN, trim_proceeds="idle"))):
        try:
            run(R, rows, pr, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)


# ─────────────────────────── 回歸閘 1
def gate1():
    os.chdir(REPO)
    if not os.environ.get("AVG_ENGINE2_SRC"):
        print("── 回歸閘 1-a：既有兩道回歸閘（開關關閉）")
        for scr, n in (("regress_tradability.py", 18), ("regress_delist.py", 6)):
            p = subprocess.run([PY, os.path.join(REPO, "backtest", scr), "check"], cwd=REPO, capture_output=True, text=True)
            tail = [ln for ln in p.stdout.strip().split("\n") if ln][-1:] if p.stdout else []
            chk(f"{scr} check（{n} 組）逐位元相同", p.returncode == 0 and "✅" in p.stdout, " ".join(tail) + (p.stderr[-300:] if p.returncode else ""))
    else:
        print("── 回歸閘 1-a 略過（AVG_ENGINE2_SRC 模式：兩支 regress 讀的是工作樹裡的 research11，要換檔後才跑）")
    print("── 回歸閘 1-b：改前（git blob d8d177e7）／改後 A/B 矩陣（真資料、門檻B、H120、N=8、種子 0,1；比 equity bytes＋全部回傳＋log＋audit）")
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
           "P9 2-C ⓗ regime_trim MA10＋tradable": dict(regime_trim={"hold": 0.5, "ma": 10, "bench": bench}, tradable=trad),
           # ⭐ 乙一／乙二 兩型（d609e89a95 交件、改前引擎就有）⇒ 開關關閉時改前／改後必須連 x_ 鍵都逐位元同
           "乙一 add loss＋audit": dict(add_rule={"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}, _audit=True),
           "乙一 add loss partial＋tradable＋delist": dict(add_rule={"kind": "loss", "x": 0.10, "short": "partial"}, tradable=trad, delist=dl),
           "乙二 trim gain＋audit（＝乙三閒置版）": dict(trim_rule={"kind": "gain", "x": 0.15, "frac": 0.5}, _audit=True),
           "乙二 trim gain＋tradable＋delist＋audit＋log": dict(trim_rule={"kind": "gain", "x": 0.15, "frac": 0.5}, tradable=trad, delist=dl, _audit=True, _log=True),
           "乙二 trim gain（改後明寫 trim_proceeds=None）": dict(trim_rule={"kind": "gain", "x": 0.15, "frac": 0.5}, _audit=True, _none=True)}
    n_ok = n_all = 0; bad = []
    for name, cfg in CFG.items():
        for seed in (0, 1):
            outs = []
            for eng in (R0, R):
                kw = dict(cfg); lg = [] if kw.pop("_log", False) else None; au = [] if kw.pop("_audit", False) else None
                if kw.pop("_none", False) and eng is R:
                    kw["trim_proceeds"] = None
                N = kw.pop("n_slots", 8)
                o = eng.simulate_mtm(sig, "H120", N, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, log=lg, audit=au, **kw)
                outs.append((o, repr(lg), repr(au)))
            ok, why = same_out(outs[0][0], outs[1][0])
            ok = ok and outs[0][1] == outs[1][1] and outs[0][2] == outs[1][2]
            n_all += 1; n_ok += ok
            if not ok:
                bad.append((name, seed, why))
        print(f"  {name} ✓" if not any(b[0] == name for b in bad) else f"  {name} ✗", flush=True)
    n_ab = sum(k.startswith("乙") for k in CFG)
    chk(f"A/B 矩陣：{len(CFG)} 種既有參數組合（含 P9 五參數 14 種、乙一乙二兩型 {n_ab} 種）× 2 種子 ＝ {n_all} 組，改前／改後逐位元相同"
        "（equity bytes、全部回傳鍵含 x_、log、audit）", n_ok == n_all, f"{n_ok}/{n_all}；不同 {bad[:3]}")
    EXTRA["A/B 組合"] = list(CFG)


# ─────────────────────────── 回歸閘 2（跑既有 selftest；它們寫的入庫檔讀完就寫回原位元組）
def _snap(d, pred=lambda f: True):
    return {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and pred(f)}


def gate2():
    os.chdir(REPO)
    d9 = os.path.join(REPO, "backtest", "resultsp9_engine")
    isb = lambda f: f.startswith("engine_b_")                         # noqa: E731  selftest_avgengine 的輸出（入庫檔）
    s9 = _snap(d9); sA = _snap(OUT, isb); sA_all = set(os.listdir(OUT))
    print(f"── 回歸閘 2（先存 resultsp9_engine/ {len(s9)} 個檔、resultsAvg/engine_b_* {len(sA)} 個檔的位元組，跑完寫回）")
    env = {k: v for k, v in os.environ.items() if k not in ("AVG_ENGINE_SRC", "AVG_ENGINE2_SRC")}
    runs = [("selftest_avgengine.py all", [PY, os.path.join(REPO, "backtest", "selftest_avgengine.py"), "all"]),
            ("selftest_avgdown.py（F1～F10）", [PY, os.path.join(REPO, "backtest", "selftest_avgdown.py")])]
    got = {}; js = {}
    try:
        for nm, cmd in runs:
            t0 = time.time()
            p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env)
            got[nm] = {"rc": p.returncode, "secs": round(time.time() - t0), "out": p.stdout, "err": p.stderr[-2000:] if p.returncode else ""}
            print(f"  [{nm}] rc={p.returncode}（{got[nm]['secs']}s）", flush=True)
        for tag in ("fixtures", "gate1", "gate2", "nonid"):
            js[tag] = json.loads(open(os.path.join(OUT, f"engine_b_{tag}.json"), encoding="utf-8").read())
    finally:
        for d, snap, keep in ((d9, s9, None), (OUT, sA, sA_all)):
            for f in list(os.listdir(d)):
                pth = os.path.join(d, f)
                if not os.path.isfile(pth):
                    continue
                if d == d9 and f not in snap:
                    os.remove(pth)
                if d == OUT and isb(f) and f not in snap:
                    os.remove(pth)
            for f, b in snap.items():
                open(os.path.join(d, f), "wb").write(b)
        back = all(open(os.path.join(d9, f), "rb").read() == b for f, b in s9.items()) and \
            all(open(os.path.join(OUT, f), "rb").read() == b for f, b in sA.items())
        new_files = sorted(set(os.listdir(OUT)) - sA_all - {f"engine_b2_{t}.json" for t in ("fixtures", "gate1", "gate2", "nonid")}) + \
            sorted(set(os.listdir(d9)) - set(s9))
        print(f"  已寫回原位元組：{back}；多出來的檔 {new_files}")
    ga = got["selftest_avgengine.py all"]
    chk("selftest_avgengine.py all 結束碼 0", ga["rc"] == 0, ga["err"][-300:])
    for tag, want_n in (("fixtures", 56), ("gate1", 3), ("gate2", 13), ("nonid", 3)):
        d = js[tag]
        chk(f"selftest_avgengine {tag}：{d['n'] - d['fail']}/{d['n']} 過（d609e89a95 交件時 {want_n} 條全過）", d["fail"] == 0 and d["n"] == want_n,
            "; ".join(c["name"][:60] for c in d["checks"] if not c["ok"])[:500])
    g2 = js["gate2"]["checks"]
    for key in ("selftest_p9engine fixtures", "selftest_p9engine gate1", "selftest_p9engine gate2", "selftest_p9engine nonid",
                "selftest_p9engine.py all 結束碼 0", "P9 基準臂", "selftest_p9_builders fixtures", "selftest_p9_builders real",
                "selftest_p9_builders addcount"):
        hit = [c for c in g2 if c["name"].startswith(key)]
        chk(f"（內含）{hit[0]['name'][:110] if hit else key}", len(hit) >= 1 and all(c["ok"] for c in hit), (hit[0]["detail"][:300] if hit else "找不到"))
    base = [c for c in js["gate2"]["extra"]["P9 gate2 逐條"] if c[0].startswith("researchp9 base 臂 cells.csv")]
    chk("P9 基準臂在原資料原窗（0dc5d62b2a archive、浮動窗 [523,2855)）重現 年化中位 +27.69%／回落中位 −42.5%（cells.csv 逐位元）",
        len(base) == 1 and base[0][1] and "+27.69%" in base[0][0] and "-42.5%" in base[0][0], base[0][0] if base else "找不到")
    ad = got["selftest_avgdown.py（F1～F10）"]
    oks = [f"F{i}" for i in range(1, 11) if f"✅ F{i} " in ad["out"] or f"✅ F{i}\n" in ad["out"]]
    chk("selftest_avgdown.py：F1～F10 全過（F10 已改寫成驗 loss／gain 新 kind；F1～F9 一字未動）", ad["rc"] == 0 and len(oks) == 10, f"過 {oks}；{ad['err'][-300:]}")
    try:
        o_ = ad["out"]; f10 = json.loads(o_[o_.index("\n{\n", o_.rindex("✅ F")) + 1:])["F10"]
    except Exception:  # noqa: BLE001
        f10 = None
    chk("selftest_avgdown F10 結論：乙一、乙二 引擎都有對應參數", bool(f10) and f10["結論"]["乙一_引擎有對應參數"] and f10["結論"]["乙二_引擎有對應參數"], json.dumps(f10, ensure_ascii=False)[:400])
    chk("既有結果檔已逐位元組寫回（⛔ 不留下對 resultsp9_engine/、resultsAvg/engine_b_* 的改動）", back and not new_files, f"多出來的檔 {new_files}")
    EXTRA["子行程"] = {k: {"rc": v["rc"], "secs": v["secs"]} for k, v in got.items()}
    EXTRA["avgengine 逐支"] = {t: {"n": js[t]["n"], "fail": js[t]["fail"]} for t in js}
    EXTRA["avgengine gate2 逐條"] = [(c["name"], c["ok"]) for c in g2]
    EXTRA["avgdown F10"] = f10


# ─────────────────────────── ⛔ 不是恆等輸出（真資料；⛔ 只看計數與 sha）
def nonid(seeds=5):
    os.chdir(REPO)
    from backtest import researchP9run as P
    R = engine_new()
    print("── ⛔ 不是恆等輸出：乙要跑的設定（researchP9run.setup：edc6f8002f 快照、S1、H120、N=8、種子 99000＋r）；⛔ 只報 sha 是否不同與次數")
    info = P.setup(lambda x: None)
    pre = pd.read_csv(os.path.join(OUT, "pre_B_seeds.csv")).set_index("r")
    KEEP = ("x_new_n", "x_trim_n", "x_trim_blocked_days", "x_nx_n", "x_nx_full_days", "x_nx_empty_days", "x_nx_blocked", "x_nx_pending_end")
    G = P._G

    def one(kw, seed):
        o = R.simulate_mtm(G["sig"], P.RULE, P.N_MAIN, np.random.default_rng(seed), G["closes"], G["opens"], G["ncal"],
                           return_equity=True, report_maxw=True, **kw)
        r = {"sha": hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest(), **{k: int(o[k]) for k in KEEP if k in o}}
        if "x_nx_waits" in o:
            w = np.asarray(o["x_nx_waits"], int)
            r["waits_中位"] = float(np.median(w)) if len(w) else None; r["waits_最長"] = int(w.max()) if len(w) else None
        del o                                           # ⛔ 年化／回落等鍵不讀、不存
        return r
    rows = []
    for r in range(seeds):
        seed = P.SEED0 + r
        b = one({}, seed); c = one(GAIN, seed); n = one(NX, seed); n0 = one({**GAIN, "trim_proceeds": None}, seed)
        rows.append({"r": r, "base_sha_eq_pre": b["sha"] == pre.loc[r, "eq_sha"], "None明寫_sha同閒置版": n0["sha"] == c["sha"],
                     "next_與閒置版不同": n["sha"] != c["sha"], "next_與全關不同": n["sha"] != b["sha"],
                     **{"閒置_" + k: v for k, v in c.items() if k != "sha"}, **{"next_" + k: v for k, v in n.items() if k != "sha"}})
        z = rows[-1]
        print(f"  r={r}：閒置版 賣半 {z['閒置_x_trim_n']}｜next 賣半 {z['next_x_trim_n']}／待買買進 {z['next_x_nx_n']}／槽滿等 {z['next_x_nx_full_days']}"
              f"／池空等 {z['next_x_nx_empty_days']}／期末未買 {z['next_x_nx_pending_end']}／等待中位 {z['next_waits_中位']}、最長 {z['next_waits_最長']}", flush=True)
    D = pd.DataFrame(rows)
    chk(f"基準臂（全關）{seeds} 顆 equity sha ＝ resultsAvg/pre_B_seeds.csv（＝ resultsP9run 基準臂）", bool(D["base_sha_eq_pre"].all()))
    chk(f"trim_proceeds=None 明寫 ⇒ {seeds} 顆 equity sha ＝ 乙二閒置版（省略開關）", bool(D["None明寫_sha同閒置版"].all()))
    chk(f"乙二 next：{seeds} 顆都與閒置版、全關不同，每顆都有待買買進", bool(D["next_與閒置版不同"].all() and D["next_與全關不同"].all() and (D["next_x_nx_n"] > 0).all()),
        f"待買買進 {D['next_x_nx_n'].tolist()}；賣半 {D['next_x_trim_n'].tolist()}")
    EXTRA["setup"] = info
    EXTRA["逐顆（只有計數與 sha 比較）"] = rows


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.chdir(REPO)
    t0 = time.time(); fails = 0
    for m_, fn in (("fixtures", fixtures), ("gate1", gate1), ("gate2", gate2), ("nonid", nonid)):
        if mode in (m_, "all"):
            RESULTS.clear(); EXTRA.clear(); fn(); dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

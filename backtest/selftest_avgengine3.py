# -*- coding: utf-8 -*-
"""research11.simulate_mtm 的 nx_cap（裁定線 seq186 §三 選（乙）：「賣得現金買下一檔」的總檔數上限放寬到 K）的 fixture 與兩道回歸閘。
回測線，2026-09-26。前一版：12c39cb810（trim_proceeds="next"，selftest_avgengine2.py）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_avgengine3.py fixtures  # 第 9、10 檔由待買買進、第 11 筆要等、總數 ≥ 8 一般新部位不買、
                                                                                        # 同日混合、caps、None ≡ K＝N、隨機獨立重建、無前視、突變體、防呆
    ... gate1      # 回歸閘 1：regress_tradability(18)＋regress_delist(6)＋改前（blob daf1f75d）／改後 A/B（真資料，38 種組合 × 2 種子）
    ... gate2      # 回歸閘 2：selftest_avgengine2.py all（內含 selftest_avgengine all ⇒ P9 全套、P9 基準臂 +27.69%／−42.5%；selftest_avgdown F1～F10）
    ... nonid      # 乙要跑的設定 5 顆：K＝None（8 版）與 nx_cap＝10 並列等待天數分佈；⛔ 只報次數與 sha 是否不同
    ... all

⭐ 讀法（裁定線給的，寫進引擎 docstring）：一般新部位只在【總部位數】＜ n_slots 時才買；待買可以開到總數 ≤ K。
⭐ 改前引擎從 git 物件庫取（ORIG_BLOB ＝ 12c39cb810 的 research11.py），⛔ 不靠工作目錄副本；AVG_ENGINE3_SRC ⇒ 換檔前測暫存檔。
⛔ 不跑乙的 2 格、⛔ 不讀年化／回落（nonid 只取計數鍵、等待天數與 equity sha）。
⚠ gate2 會改寫 resultsAvg/engine_b_*.json、engine_b2_*.json 與 resultsp9_engine/ 下的入庫檔 ⇒ 跑前存位元組、跑完逐檔寫回。
結果寫到 backtest/resultsAvg/engine_b3_{fixtures,gate1,gate2,nonid}.json。
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
ORIG_BLOB = "daf1f75d21548cc11b0da87301d0f200c57a5999"      # 改動前 HEAD:backtest/research11.py（12c39cb810＝trim_proceeds 交件）
GAIN = {"trim_rule": {"kind": "gain", "x": 0.15, "frac": 0.5}}
NX = {**GAIN, "trim_proceeds": "next"}
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9        # noqa: E402  ⭐ 只借小工具
from backtest import selftest_avgengine2 as SA2      # noqa: E402  ⭐ 只借小工具（world、nxb、lot_of、strip）
px, run, same_out, trad_of, close_to, fin, NC = SP9.px, SP9.run, SP9.same_out, SP9.trad_of, SP9.close_to, SP9.fin, SP9.NC
nxb, lot_of, strip, world = SA2.nxb, SA2.lot_of, SA2.strip, SA2.world


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"engine_b3_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if EXTRA:
        d["extra"] = EXTRA
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


def _new_src():
    p = os.environ.get("AVG_ENGINE3_SRC")
    if p:
        return open(p, encoding="utf-8").read(), p
    from backtest import research11 as R
    return open(R.__file__, encoding="utf-8").read(), R.__file__


def engine_new():
    p = os.environ.get("AVG_ENGINE3_SRC")
    if p:
        return SP9._load_src(open(p, encoding="utf-8").read(), "backtest._r11_new3", p)
    from backtest import research11 as R
    return R


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return SP9._load_src(src, "backtest._r11_orig_avg3", os.path.join(REPO, "backtest", "research11.py"))


MUTANTS = {
    # K 沒作用（名單長度回到只看一般容量）⇒ 第 9、10 檔買不到
    "MK_free0": ('slots_free = max(min(len(_nx["lots"]), _nx_kt - len(open_pos)), slots_free)   # _NXK_FREE', 'pass   # _NXK_FREE'),
    # 一般新部位也可以用到 K
    "MK_norm": ('slots_free = max(min(len(_nx["lots"]), _nx_kt - len(open_pos)), slots_free)   # _NXK_FREE',
                'slots_free = max(_nx_kt - len(open_pos), slots_free)   # _NXK_FREE'),
    # 待買可以開到 K＋1（第 11 檔）
    "MK_over": ("_nx_kt = ns_t if _nxk is None else max(_nxk, ns_t)", "_nx_kt = ns_t if _nxk is None else max(_nxk + 1, ns_t)"),
    # 總數 ≥ n_slots 時不進挑股區塊（＝ 12c39cb810 的進場條件）
    "MK_enter": ("if g is not None and (len(open_pos) < ns_t or (_nxk is not None and _nx[\"lots\"] and len(open_pos) < _nx_kt)):",
                 "if g is not None and len(open_pos) < ns_t:"),
    # caps 開啟時不取 max(K, caps[t])（只用 K）
    "MK_caps": ("_nx_kt = ns_t if _nxk is None else max(_nxk, ns_t)", "_nx_kt = ns_t if _nxk is None else _nxk"),
}


def engine_mut(tag):
    src, f = _new_src()
    a, b = MUTANTS[tag]
    if src.count(a) != 1:
        raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一：{a!r}")
    return SP9._load_src(src.replace(a, b), f"backtest._r11_{tag}", f)


# ─────────────────────────── 獨立重建（只讀 audit 與訊號列）
def replay_k(o, rows, N, K):
    """逐日重建；驗：每個量測日 待買買進數 ＝ min(K − 總數, 候選, 待買)、待買排在一般新部位前、一般新部位買進時總數 ＜ N、
    總數 ≤ K、全額先進先出、不重複買、x_nx_over ＝ 總數 ≥ N 時由待買買進的筆數、計數鍵。"""
    ent = {}
    for s, e, x in rows:
        ent.setdefault(e, []).append(s)
    by_t = {}
    for r in o["_audit"]:
        by_t.setdefault(int(r["t"]), []).append(r)
    held = set(); lots = deque(); waits = []
    st = {"full": 0, "empty": 0, "nx": 0, "over": 0, "maxheld": 0, "normal_at_ge_N": 0}
    for t in sorted(set(by_t) | set(ent)):
        rt = by_t.get(t, []); i = 0
        while i < len(rt) and rt[i]["side"] == "sell":
            r = rt[i]
            if r.get("kind") == "trim":
                lots.append((r["amt"] - r["cost"], t))
            elif "kind" not in r:
                if r["sid"] not in held:
                    return False, f"t={t} 賣出未持有的 {r['sid']}", st
                held.discard(r["sid"])
            i += 1
        bs = rt[i:]
        if any(r["side"] != "buy" for r in bs):
            return False, f"t={t} 同日順序錯", st
        if t in ent:
            cand = [s for s in ent[t] if s not in held]
            kf = K - len(held)
            if lots and kf <= 0:
                st["full"] += 1
            if lots and kf > 0 and (len(held) < N or lots) and not cand:
                st["empty"] += 1
            want = min(kf, len(cand), len(lots)) if kf > 0 else 0
            kinds = [r.get("kind") for r in bs]
            if kinds.count("nx") != want:
                return False, f"t={t} 待買買進 {kinds.count('nx')}，應 min(K−總數 {kf}, 候選 {len(cand)}, 待買 {len(lots)}) ＝ {want}", st
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
                    return False, f"t={t} 待買金額不是佇列頭全額", st
                waits.append(t - ts); st["nx"] += 1
                st["over"] += len(held) >= N
            elif len(held) >= N:
                st["normal_at_ge_N"] += 1
                return False, f"t={t} 總數 {len(held)} ≥ n_slots {N} 時買了一般新部位 {r['sid']}", st
            held.add(r["sid"])
        st["maxheld"] = max(st["maxheld"], len(held))
        if len(held) > K:
            return False, f"t={t} 總數 {len(held)} ＞ K {K}", st
    got = (o.get("x_nx_n"), o.get("x_nx_waits"), o.get("x_nx_full_days"), o.get("x_nx_pending_end"), o.get("x_nx_over"))
    exp = (st["nx"], waits, st["full"], len(lots), st["over"])
    if got != exp:
        return False, f"引擎計數 {got} ≠ 重建 {exp}", st
    return True, "", st


def up(t_trig, hi=11.6, after=11.8):
    """t_trig 收盤 11.6（≥ 1.15×10）⇒ t_trig＋1 開盤 after 賣半；之後價平 after。"""
    return px((0, t_trig, 10, 10), (t_trig, t_trig + 1, 10, hi), (t_trig + 1, NC, after, after))


# ─────────────────────────── 手算小例（每條回 bool ⇒ 同一組拿去跑突變體）
def fx_list(R, C):
    out = []

    def add(nm, ok, det=""):
        out.append((nm, bool(ok), det))

    def safe(fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            out.append((fn.__name__, False, f"例外 {type(e).__name__}: {e}"))

    def h1():
        # N=8、K=10：P1..P8 在 10 進（各 1/8）；P1 收盤[20]、P2 收盤[22] 觸發 ⇒ t=21、23 賣半 ⇒ 兩筆待買
        #   t=30 量測日 Q1..Q4 ⇒ 待買開第 9、10 檔、一般 0；P3 收盤[40] ⇒ t=41 第三筆待買；t=45 量測日（R1、R2）總數 10 ⇒ 等（第 11 筆要等）
        #   t=50 P4 出場 ⇒ 9；t=55 量測日（S1..S3）⇒ 第三筆買進（第 10 檔）、一般 0（總數 9 ≥ 8）
        #   t=60、61 P5、P6 出場 ⇒ 8；t=65 量測日（T1、T2）⇒ 沒有待買、總數 8 ⇒ 一般新部位不買
        #   t=66 P7 出場 ⇒ 7；t=70 量測日（U1..U3）⇒ 一般新部位只買 1 檔（到 8 為止）
        pr = {"P1": up(20), "P2": up(22), "P3": up(40), **{f"P{i}": px() for i in range(4, 9)},
              **{s: px() for s in ("Q1", "Q2", "Q3", "Q4", "R1", "R2", "S1", "S2", "S3", "T1", "T2", "U1", "U2", "U3")}}
        ex = {"P4": 50, "P5": 60, "P6": 61, "P7": 66}
        rows = [(f"P{i}", 10, ex.get(f"P{i}", 90)) for i in range(1, 9)] + [(s, 30, 95) for s in ("Q1", "Q2", "Q3", "Q4")] + \
            [(s, 45, 95) for s in ("R1", "R2")] + [(s, 55, 96) for s in ("S1", "S2", "S3")] + [(s, 65, 97) for s in ("T1", "T2")] + \
            [(s, 70, 98) for s in ("U1", "U2", "U3")]
        o = run(R, rows, pr, 8, nx_cap=10, **NX)
        L = lot_of(1 / 8, 11.8, 10.0, C)
        nb = nxb(o)
        by = lambda t: [(r["sid"][0], r.get("kind")) for r in o["_audit"] if r["side"] == "buy" and r["t"] == t]   # noqa: E731
        ok1 = [x[0] for x in nb] == [30, 30, 55] and all(close_to(x[2], L) for x in nb) and by(30) == [("Q", "nx"), ("Q", "nx")]
        add("K1 第 9、10 檔由待買買進：N=8、nx_cap=10，8 檔持有＋2 筆待買 ⇒ t=30 買 2 檔（都是待買、全額 L）、一般新部位 0",
            ok1, f"t=30 {by(30)}；待買 {[(t, s, round(a, 9)) for t, s, a in nb]}")
        add("K2 第 11 筆待買要等：t=45 總數 10 ＝ K ⇒ 不買（full_days 1）；t=50 有檔出場 ⇒ t=55 用它買第 10 檔（等 14 天）、一般 0",
            by(45) == [] and by(55) == [("S", "nx")] and o["x_nx_full_days"] == 1 and o["x_nx_waits"] == [9, 7, 14], f"t=55 {by(55)}；waits {o['x_nx_waits']}；full {o['x_nx_full_days']}")
        add("K3 一般新部位在總數 ≥ 8 時不買：t=65 總數 8（其中 2 檔是待買買進的）、沒有待買 ⇒ 不買；t=70 總數 7 ⇒ 一般新部位只買 1 檔",
            by(65) == [] and by(70) == [("U", None)], f"t=65 {by(65)}；t=70 {by(70)}")
        ok_, why, stt = replay_k(o, rows, 8, 10)
        add("K4 同一例：x_nx_over＝3（總數 ≥ 8 時由待買買進的 3 筆）、最多持有 10 檔、獨立重建相符",
            o["x_nx_over"] == 3 and stt.get("maxheld") == 10 and ok_, f"over {o['x_nx_over']}；maxheld {stt.get('maxheld')}；{why or 'OK'}")
        o8 = run(R, rows, pr, 8, **NX)
        add("K5 同一例 nx_cap=None（＝ 8 版、12c39cb810 路徑）：t=30 總數 8 ⇒ 不買；待買要等 P4 出場（t=55）才買第 1 筆；最多 8 檔",
            not [r for r in o8["_audit"] if r["side"] == "buy" and r["t"] == 30] and [x[0] for x in nxb(o8)][:1] == [55] and replay_k(o8, rows, 8, 8)[2].get("maxheld") == 8,
            f"None 版待買 {[(t, s) for t, s, _ in nxb(o8)]}")

    def h2():
        # 同日混合：N=8、K=10，7 檔持有、2 筆待買、5 檔候選 ⇒ 2 檔待買（到 9）、一般 0（總數已 ≥ 8）
        pr = {"P1": up(20), "P2": up(22), **{f"P{i}": px() for i in range(3, 8)}, **{f"Q{i}": px() for i in range(1, 6)}}
        rows = [(f"P{i}", 10, 90) for i in range(1, 8)] + [(f"Q{i}", 30, 95) for i in range(1, 6)]
        o = run(R, rows, pr, 8, nx_cap=10, **NX)
        b = [r.get("kind") for r in o["_audit"] if r["side"] == "buy" and r["t"] == 30]
        add("K6 同日混合（總數 7、待買 2、候選 5）⇒ 名單長度 max(min(2, 3), 1)＝2：兩檔都是待買、一般 0（買完總數 9）",
            b == ["nx", "nx"] and o["x_nx_over"] == 1, f"t=30 {b}；over {o['x_nx_over']}")
        # 總數 5、待買 1、候選 5 ⇒ 待買 1 ＋ 一般 2（到 8）
        pr = {"P1": up(20), **{f"P{i}": px() for i in range(2, 6)}, **{f"Q{i}": px() for i in range(1, 6)}}
        rows = [(f"P{i}", 10, 90) for i in range(1, 6)] + [(f"Q{i}", 30, 95) for i in range(1, 6)]
        o = run(R, rows, pr, 8, nx_cap=10, **NX)
        b = [r.get("kind") for r in o["_audit"] if r["side"] == "buy" and r["t"] == 30]
        add("K7 同日混合（總數 5、待買 1、候選 5）⇒ 待買 1 ＋ 一般 2（買完總數 8）、x_nx_over 0", b == ["nx", None, None] and o["x_nx_over"] == 0, f"t=30 {b}")

    def h3():
        # caps：容量 8 到 t=39、之後 11；K=10 ⇒ t=30 待買開到 10；t=45 K_t＝max(10, 11)＝11 ⇒ 第三筆待買買第 11 檔
        pr = {"P1": up(20), "P2": up(22), "P3": up(40), **{f"P{i}": px() for i in range(4, 9)},
              **{s: px() for s in ("Q1", "Q2", "Q3", "R1")}}
        rows = [(f"P{i}", 10, 90) for i in range(1, 9)] + [(s, 30, 95) for s in ("Q1", "Q2", "Q3")] + [("R1", 45, 95)]
        caps = np.full(NC, 8, int); caps[40:] = 11
        o = run(R, rows, pr, caps, nx_cap=10, **NX)
        nb = nxb(o)
        add("K8 caps 開啟：K_t ＝ max(K, caps[t])：caps 8 時待買到 10；caps 11 時第三筆待買買第 11 檔、不算「槽滿等待」（full_days 0）",
            [(t, s[0]) for t, s, _ in nb] == [(30, "Q"), (30, "Q"), (45, "R")] and o["x_nx_full_days"] == 0,
            f"{[(t, s) for t, s, _ in nb]}；full {o['x_nx_full_days']}")
        caps5 = np.full(NC, 5, int)
        pr2 = {"P1": up(20), "P2": up(22), **{f"P{i}": px() for i in range(3, 6)}, **{f"Q{i}": px() for i in range(1, 5)}}
        rows2 = [(f"P{i}", 10, 90) for i in range(1, 6)] + [(f"Q{i}", 30, 95) for i in range(1, 5)]
        o2 = run(R, rows2, pr2, caps5, nx_cap=10, **NX)
        b2 = [r.get("kind") for r in o2["_audit"] if r["side"] == "buy" and r["t"] == 30]
        add("K9 caps 5、K=10：5 檔持有＋2 筆待買 ⇒ 待買開到第 6、7 檔、一般 0", b2 == ["nx", "nx"], f"t=30 {b2}")

    for fn in (h1, h2, h3):
        safe(fn)
    return out


def rand_k(R, n_w=300, seed=20260927):
    rng = np.random.default_rng(seed)
    n_ok = 0; agg = {"有待買買進": 0, "有超過 N 的待買（over）": 0, "有到 K 而等": 0, "待買買進筆數": 0}; bad = []
    for w in range(n_w):
        pr, rows, N, _ = world(rng)
        K = N + int(rng.integers(0, 4))
        if not rows:
            n_ok += 1; continue
        try:
            o = run(R, rows, pr, N, seed=w, nx_cap=K, **NX)
            ok, why, st = replay_k(o, rows, N, K)
        except Exception as e:  # noqa: BLE001
            ok, why, st = False, f"例外 {type(e).__name__}: {e}", {}
        n_ok += ok
        if not ok:
            bad.append((w, why)); continue
        agg["有待買買進"] += st["nx"] > 0; agg["有超過 N 的待買（over）"] += st["over"] > 0; agg["有到 K 而等"] += st["full"] > 0
        agg["待買買進筆數"] += st["nx"]
    return n_ok, n_w, agg, bad


def lookahead_k(R, n_w=200, seed=20260928):
    rng = np.random.default_rng(seed); n_ok = n_post = 0
    for w in range(n_w):
        pa, rows, N, extra = world(rng, trad=bool(w % 2))
        K = N + 2
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
            c[s:] = c[s:] * f; o[s + 1:] = o[s + 1:] * f[:-1]
            pb[sd] = (o, c)
        oa = run(R, rows, pa, N, seed=w, nx_cap=K, **NX, **extra); ob = run(R, rows, pb, N, seed=w, nx_cap=K, **NX, **extra)
        ta = [r for r in oa["_audit"] if r["t"] <= s]; tb = [r for r in ob["_audit"] if r["t"] <= s]
        n_ok += repr(ta) == repr(tb) and oa["equity"][:s].tobytes() == ob["equity"][:s].tobytes()
        n_post += repr(oa["_audit"]) != repr(ob["_audit"])
    return n_ok, n_post, n_w


def fixtures():
    R = engine_new(); C = R.COST
    print(f"── 引擎：{'AVG_ENGINE3_SRC=' + os.environ['AVG_ENGINE3_SRC'] if os.environ.get('AVG_ENGINE3_SRC') else R.__file__}")
    import inspect
    p_ = inspect.signature(R.simulate_mtm).parameters
    chk("參數 nx_cap 存在、預設 None", "nx_cap" in p_ and p_["nx_cap"].default is None)
    print("── 手算小例")
    FX = fx_list(R, C)
    for nm, ok, det in FX:
        chk(nm, ok, det)
    print("── 隨機獨立重建（K ＝ N＋0～3）")
    n_ok, n_w, agg, bad = rand_k(R)
    chk(f"隨機 {n_w} 個世界：獨立重建全部相符（待買數 ＝ min(K−總數, 候選, 待買)、一般新部位買進時總數 ＜ N、總數 ≤ K、全額先進先出、計數鍵）",
        n_ok == n_w, f"{n_ok}/{n_w}；{json.dumps(agg, ensure_ascii=False)}；{bad[:2]}")
    chk("隨機世界確實走到：有超過 N 的待買買進、有到 K 而等（各 ≥ 10 個世界）", min(agg["有超過 N 的待買（over）"], agg["有到 K 而等"]) >= 10, json.dumps(agg, ensure_ascii=False))
    EXTRA["隨機重建"] = agg
    n_ok, n_post, n_w = lookahead_k(R)
    chk(f"無前視（nx_cap＝N＋2，隨機 {n_w} 個世界、一半開 tradable）：t ≤ s 的交易與 equity[:s] 全部不變、之後確實不同 ≥ 一半",
        n_ok == n_w and n_post >= n_w // 2, f"{n_ok}/{n_w}；後段不同 {n_post}")
    print("── 鑑別力（突變體）")
    mut = {}
    for tag in MUTANTS:
        M = engine_mut(tag)
        failed = [nm.split("：")[0].split("（")[0] for nm, ok, _ in fx_list(M, C) if not ok]
        n_okm, n_wm, _, _ = rand_k(M, n_w=100)
        mut[tag] = {"fixture 沒過": failed, "隨機重建沒過": f"{n_wm - n_okm}/{n_wm}"}
        chk(f"鑑別力 {tag}：至少一條抓到", bool(failed) or n_okm < n_wm, json.dumps(mut[tag], ensure_ascii=False))
    EXTRA["突變體"] = mut
    print("── None 路徑")
    R0 = engine_orig()
    rng = np.random.default_rng(11); n_same = n_all = 0; n_eqk = 0; why_ = []
    for w in range(60):
        pr, rows, N, extra = world(rng, trad=bool(w % 3 == 0))
        if not rows:
            continue
        for kw0, kw1 in ((dict(**NX), dict(**NX)), (dict(**NX), dict(**NX, nx_cap=None)), (dict(**GAIN), dict(**GAIN)), (dict(), dict())):
            a0 = run(R0, rows, pr, N, seed=w, **kw0, **extra); a1 = run(R, rows, pr, N, seed=w, **kw1, **extra)
            ok, why = same_out(strip(a0), strip(a1)); ok = ok and repr(a0["_audit"]) == repr(a1["_audit"])
            n_all += 1; n_same += ok
            if not ok:
                why_.append((w, why))
        aN = run(R, rows, pr, N, seed=w, **NX, **extra); aK = run(R, rows, pr, N, seed=w, nx_cap=N, **NX, **extra)
        ok, _ = same_out(strip(aN), strip(aK), skip_prefix="x_nx_over")
        n_eqk += ok and repr(aN["_audit"]) == repr(aK["_audit"]) and aK["x_nx_over"] == 0
    chk("nx_cap 省略／None 明寫 × （next、閒置版、全關）× 隨機世界 ⇒ 與改前引擎（12c39cb810）逐位元同", n_same == n_all, f"{n_same}/{n_all}；{why_[:2]}")
    chk("nx_cap＝N（＝ n_slots）⇒ 與 None 逐位元同（只多 x_nx_over＝0）⇒ 裁定 seq188 #1（N＝10、同一個 10 槽上限）就是 None 路徑",
        n_eqk == n_all // 4, f"{n_eqk}/{n_all // 4}")
    print("── 防呆")
    rows = [("A", 10, 60)]; pr = {"A": px()}
    for nm, kw in (("nx_cap 但沒開 next", dict(**GAIN, nx_cap=10)), ("nx_cap 沒開任何東西", dict(nx_cap=10)),
                   ("K ＜ n_slots", dict(**NX, nx_cap=1)), ("K＝True", dict(**NX, nx_cap=True)), ("K＝9.5", dict(**NX, nx_cap=9.5)),
                   ("K＝'10'", dict(**NX, nx_cap="10"))):
        try:
            run(R, rows, pr, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)
    try:
        caps = np.full(NC, 8, int)
        run(R, rows, pr, caps, nx_cap=3, **NX); ok = True
    except ValueError:
        ok = False
    chk("caps 開啟時 K ＜ caps 不報錯（K_t 取 max(K, caps[t])）", ok)


# ─────────────────────────── 回歸閘 1
def gate1():
    os.chdir(REPO)
    if not os.environ.get("AVG_ENGINE3_SRC"):
        print("── 回歸閘 1-a：既有兩道回歸閘")
        for scr, n in (("regress_tradability.py", 18), ("regress_delist.py", 6)):
            p = subprocess.run([PY, os.path.join(REPO, "backtest", scr), "check"], cwd=REPO, capture_output=True, text=True)
            tail = [ln for ln in p.stdout.strip().split("\n") if ln][-1:] if p.stdout else []
            chk(f"{scr} check（{n} 組）逐位元相同", p.returncode == 0 and "✅" in p.stdout, " ".join(tail) + (p.stderr[-300:] if p.returncode else ""))
    else:
        print("── 回歸閘 1-a 略過（AVG_ENGINE3_SRC 模式）")
    print("── 回歸閘 1-b：改前（blob daf1f75d）／改後 A/B（真資料、門檻B、H120、N=8、種子 0,1）")
    from backtest import tradability as T
    R = engine_new(); R0 = engine_orig()
    cal, ncal, uni, panel, closes, opens, sig, bench = SP9.load_real()
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    wk = np.zeros(ncal, bool); wk[1:] = R.regime_below(bench, 60)[:-1]
    caps = np.full(ncal, 8, int); caps[1500:1700] = 5
    sl = {(r.sid, int(r.entry_pos)): (int(r.entry_pos), np.full(130, float(opens[r.sid][int(r.entry_pos)]) * 0.85)) for r in sig.itertuples()}
    hi = {s: (pd.Series(c).rolling(120).max().to_numpy() <= c) for s, c in ((s, np.asarray(closes[s], float)) for s in set(sig["sid"]))}
    G_ = {"kind": "gain", "x": 0.15, "frac": 0.5}
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
           "乙一 add loss＋audit": dict(add_rule={"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}, _audit=True),
           "乙一 add loss partial＋tradable＋delist": dict(add_rule={"kind": "loss", "x": 0.10, "short": "partial"}, tradable=trad, delist=dl),
           "乙二 trim gain＋audit（閒置版）": dict(trim_rule=G_, _audit=True),
           "乙二 trim gain＋tradable＋delist＋audit＋log": dict(trim_rule=G_, tradable=trad, delist=dl, _audit=True, _log=True),
           # ⭐ trim_proceeds="next"（12c39cb810 就有）⇒ nx_cap=None 時改前／改後必須連 x_nx 鍵都逐位元同
           "乙二 next＋audit": dict(trim_rule=G_, trim_proceeds="next", _audit=True),
           "乙二 next＋log": dict(trim_rule=G_, trim_proceeds="next", _log=True),
           "乙二 next＋tradable＋delist＋audit＋log": dict(trim_rule=G_, trim_proceeds="next", tradable=trad, delist=dl, _audit=True, _log=True),
           "乙二 next＋caps＋audit": dict(trim_rule=G_, trim_proceeds="next", n_slots=caps, _audit=True),
           "乙二 next＋pick＋queue＋log": dict(trim_rule=G_, trim_proceeds="next", pick="relvol", d_max=2, queue_days=3, _log=True),
           "乙二 next（改後明寫 nx_cap=None）＋audit": dict(trim_rule=G_, trim_proceeds="next", _audit=True, _none=True)}
    n_ok = n_all = 0; bad = []
    for name, cfg in CFG.items():
        for seed in (0, 1):
            outs = []
            for eng in (R0, R):
                kw = dict(cfg); lg = [] if kw.pop("_log", False) else None; au = [] if kw.pop("_audit", False) else None
                if kw.pop("_none", False) and eng is R:
                    kw["nx_cap"] = None
                N = kw.pop("n_slots", 8)
                o = eng.simulate_mtm(sig, "H120", N, np.random.default_rng(seed), closes, opens, ncal, return_equity=True, log=lg, audit=au, **kw)
                outs.append((o, repr(lg), repr(au)))
            ok, why = same_out(outs[0][0], outs[1][0])
            ok = ok and outs[0][1] == outs[1][1] and outs[0][2] == outs[1][2]
            n_all += 1; n_ok += ok
            if not ok:
                bad.append((name, seed, why))
        print(f"  {name} {'✗' if any(b[0] == name for b in bad) else '✓'}", flush=True)
    n_nx = sum("next" in k for k in CFG)
    chk(f"A/B 矩陣：{len(CFG)} 種既有參數組合（含 trim_proceeds='next' {n_nx} 種、其中 1 種明寫 nx_cap=None）× 2 種子 ＝ {n_all} 組，"
        "改前（12c39cb810）／改後逐位元相同（equity bytes、全部回傳鍵含 x_、log、audit）", n_ok == n_all, f"{n_ok}/{n_all}；{bad[:3]}")
    EXTRA["A/B 組合"] = list(CFG)


# ─────────────────────────── 回歸閘 2
def _snap(d, pred=lambda f: True):
    return {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and pred(f)}


def gate2():
    os.chdir(REPO)
    d9 = os.path.join(REPO, "backtest", "resultsp9_engine")
    isb = lambda f: f.startswith("engine_b_") or f.startswith("engine_b2_")     # noqa: E731
    s9 = _snap(d9); sA = _snap(OUT, isb); sA_all = set(os.listdir(OUT))
    print(f"── 回歸閘 2（先存 resultsp9_engine/ {len(s9)} 個檔、resultsAvg/engine_b_*／engine_b2_* {len(sA)} 個檔，跑完寫回）")
    env = {k: v for k, v in os.environ.items() if k not in ("AVG_ENGINE_SRC", "AVG_ENGINE2_SRC", "AVG_ENGINE3_SRC")}
    js = {}; got = {}
    try:
        t0 = time.time()
        p = subprocess.run([PY, os.path.join(REPO, "backtest", "selftest_avgengine2.py"), "all"], cwd=REPO, capture_output=True, text=True, env=env)
        got = {"rc": p.returncode, "secs": round(time.time() - t0), "err": p.stderr[-2000:] if p.returncode else "", "tail": p.stdout[-3000:]}
        print(f"  [selftest_avgengine2.py all] rc={p.returncode}（{got['secs']}s）", flush=True)
        for tag in ("fixtures", "gate1", "gate2", "nonid"):
            js[tag] = json.loads(open(os.path.join(OUT, f"engine_b2_{tag}.json"), encoding="utf-8").read())
    finally:
        for d, snap, pred in ((d9, s9, lambda f: True), (OUT, sA, isb)):
            for f in list(os.listdir(d)):
                pth = os.path.join(d, f)
                if os.path.isfile(pth) and pred(f) and f not in snap:
                    os.remove(pth)
            for f, b in snap.items():
                open(os.path.join(d, f), "wb").write(b)
        back = all(open(os.path.join(d9, f), "rb").read() == b for f, b in s9.items()) and \
            all(open(os.path.join(OUT, f), "rb").read() == b for f, b in sA.items())
        new_files = sorted(set(os.listdir(OUT)) - sA_all - {f"engine_b3_{t}.json" for t in ("fixtures", "gate1", "gate2", "nonid")}) + \
            sorted(set(os.listdir(d9)) - set(s9))
        print(f"  已寫回原位元組：{back}；多出來的檔 {new_files}")
    chk("selftest_avgengine2.py all 結束碼 0", got["rc"] == 0, got["err"][-300:])
    for tag, want_n in (("fixtures", 29), ("gate1", 3), ("gate2", 18), ("nonid", 3)):
        d = js[tag]
        chk(f"selftest_avgengine2 {tag}：{d['n'] - d['fail']}/{d['n']} 過（12c39cb810 交件時 {want_n} 條全過）", d["fail"] == 0 and d["n"] == want_n,
            "; ".join(c["name"][:60] for c in d["checks"] if not c["ok"])[:500])
    g2 = js["gate2"]["checks"]
    for key in ("selftest_avgengine fixtures", "selftest_avgengine gate1", "selftest_avgengine gate2", "selftest_avgengine nonid",
                "（內含）selftest_p9engine", "（內含）P9 基準臂", "（內含）selftest_p9_builders", "selftest_avgdown.py"):
        hit = [c for c in g2 if c["name"].startswith(key)]
        chk(f"（內含）{hit[0]['name'][:100] if hit else key}{'（共 ' + str(len(hit)) + ' 條）' if len(hit) > 1 else ''}", len(hit) >= 1 and all(c["ok"] for c in hit),
            (hit[0]["detail"][:200] if hit else "找不到"))
    base = [c for c in g2 if c["name"].startswith("P9 基準臂")]
    chk("P9 基準臂在原資料原窗重現 年化中位 +27.69%／回落中位 −42.5%（cells.csv 逐位元）", len(base) == 1 and base[0]["ok"] and "+27.69%" in base[0]["detail"],
        base[0]["detail"][:200] if base else "找不到")
    chk("既有結果檔已逐位元組寫回（resultsp9_engine/、resultsAvg/engine_b_*、engine_b2_*）", back and not new_files, f"多出來的檔 {new_files}")
    EXTRA["子行程"] = {"rc": got["rc"], "secs": got["secs"]}
    EXTRA["avgengine2 逐支"] = {t: {"n": js[t]["n"], "fail": js[t]["fail"]} for t in js}


# ─────────────────────────── nonid：8 版 vs 放寬 10 版（⛔ 只報次數、等待天數、sha 是否不同）
def nonid(seeds=5):
    os.chdir(REPO)
    from backtest import researchP9run as P
    R = engine_new()
    print("── 乙要跑的設定（researchP9run.setup：edc6f8002f 快照、S1、H120、N=8、種子 99000＋r）；⛔ 只報次數與等待天數")
    info = P.setup(lambda x: None)
    pre = pd.read_csv(os.path.join(OUT, "pre_B_seeds.csv")).set_index("r")
    G = P._G
    KEEP = ("x_new_n", "x_trim_n", "x_nx_n", "x_nx_full_days", "x_nx_empty_days", "x_nx_pending_end", "x_nx_over")

    def one(kw, seed):
        o = R.simulate_mtm(G["sig"], P.RULE, P.N_MAIN, np.random.default_rng(seed), G["closes"], G["opens"], G["ncal"],
                           return_equity=True, report_maxw=True, **kw)
        r = {"sha": hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest(), **{k: int(o[k]) for k in KEEP if k in o}}
        w = np.asarray(o.get("x_nx_waits", []), int)
        r["waits"] = w.tolist()
        del o
        return r

    def dist(w):
        w = np.asarray(w, float)
        if not len(w):
            return {}
        return {"筆": int(len(w)), "p10": float(np.percentile(w, 10)), "p25": float(np.percentile(w, 25)), "中位": float(np.median(w)),
                "p75": float(np.percentile(w, 75)), "p90": float(np.percentile(w, 90)), "最長": int(w.max()), "平均": round(float(w.mean()), 1),
                "0天": int((w == 0).sum()), "≤20天": int((w <= 20).sum())}
    rows = []; all8 = []; all10 = []
    for r in range(seeds):
        seed = P.SEED0 + r
        b = one({}, seed); a8 = one(NX, seed); a10 = one({**NX, "nx_cap": 10}, seed); an = one({**NX, "nx_cap": None}, seed)
        all8 += a8["waits"]; all10 += a10["waits"]
        rows.append({"r": r, "base_sha_eq_pre": b["sha"] == pre.loc[r, "eq_sha"], "None明寫_sha同8版": an["sha"] == a8["sha"],
                     "10版與8版不同": a10["sha"] != a8["sha"],
                     **{"8版_" + k: v for k, v in a8.items() if k not in ("sha", "waits")}, "8版_等待": dist(a8["waits"]),
                     **{"10版_" + k: v for k, v in a10.items() if k not in ("sha", "waits")}, "10版_等待": dist(a10["waits"])})
        z = rows[-1]
        print(f"  r={r}：8 版 待買 {z['8版_x_nx_n']}、槽滿等 {z['8版_x_nx_full_days']}、等待 {z['8版_等待']}\n"
              f"        10 版 待買 {z['10版_x_nx_n']}、over {z['10版_x_nx_over']}、到 10 而等 {z['10版_x_nx_full_days']}、等待 {z['10版_等待']}", flush=True)
    D = pd.DataFrame(rows)
    chk(f"基準臂（全關）{seeds} 顆 equity sha ＝ pre_B_seeds.csv", bool(D["base_sha_eq_pre"].all()))
    chk(f"nx_cap=None 明寫 ⇒ {seeds} 顆 sha ＝ 8 版（省略）", bool(D["None明寫_sha同8版"].all()))
    chk(f"放寬 10 版：{seeds} 顆都與 8 版不同、每顆都有超過 8 檔的待買買進（x_nx_over ＞ 0）",
        bool(D["10版與8版不同"].all() and (D["10版_x_nx_over"] > 0).all()), f"over {D['10版_x_nx_over'].tolist()}")
    EXTRA["setup"] = info
    EXTRA["逐顆"] = rows
    EXTRA["5 顆合併的等待天數分佈"] = {"8 版（nx_cap=None）": dist(all8), "放寬 10 版（nx_cap=10）": dist(all10)}
    print(f"  合併：8 版 {dist(all8)}\n        10 版 {dist(all10)}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.chdir(REPO)
    t0 = time.time(); fails = 0
    for m_, fn in (("fixtures", fixtures), ("gate1", gate1), ("gate2", gate2), ("nonid", nonid)):
        if mode in (m_, "all"):
            RESULTS.clear(); EXTRA.clear(); fn(); dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

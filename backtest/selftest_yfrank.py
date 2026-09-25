# -*- coding: utf-8 -*-
"""PREREG營飆排名（裁定 seq199）：引擎 simulate_mtm 的 pick_tie="rng" 的 fixture 與閘門。回測線，2026-09-26。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_yfrank.py fixtures  # 手算（同分照抽籤、NaN 排最後、d_max＋queue、自訂欄）、
                                                                                   # 隨機世界對診斷包裝、常數鍵＝抽籤、突變體、防呆、None 路徑
    ... gate_a   # (a) 引擎 pick=K*, pick_tie="rng" 的買進清單與 equity ＝ pre 的診斷包裝 RankRng（200 顆 × K0～K4）逐筆相同
    ... gate_b   # (b) 常數鍵＋pick_tie ＝ 抽籤版逐位元（200 顆；全部回傳鍵＋audit）
    ... gate_c   # (c) pick_tie 不給 ⇒ #13（P1 AND N20 relvol）rerun17 main／win 20 顆逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha）
    ... gate1    # (d-1) regress_tradability 18＋regress_delist 6＋改前（blob 5331e1cd＝84de67ccaf）／改後 A/B（43 種組合 × 2 種子）
    ... gate2    # (d-2) selftest_listexit.py all（內含 selftest_avgengine3 all ⇒ avgengine2、avgengine、P9 全套、P9 基準臂、avgdown）
    ... all
⛔ 不跑判定格、⛔ 不讀報酬（gate_c 只比 repr、不印）。⚠ gate2 會改寫 resultsListExit/engine_*.json、resultsAvg/engine_b*_、
   resultsp9_engine/ 的入庫檔 ⇒ 跑前存位元組、跑完寫回。結果寫到 backtest/resultsYfRank/engine_{…}.json。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest", "resultsYfRank")
PY = sys.executable
ORIG_BLOB = "5331e1cd65e73d7ef3564e01d5ed625283eec596"      # 改動前 HEAD:backtest/research11.py（84de67ccaf）
KEYS = ["K0", "K1", "K2", "K3", "K4"]
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9        # noqa: E402
from backtest.researchYfRank import RankRng          # noqa: E402  ⭐ pre 的診斷包裝（對照組；⛔ 不改它）
px, same_out, trad_of, close_to, NC = SP9.px, SP9.same_out, SP9.trad_of, SP9.close_to, SP9.NC


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"engine_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if EXTRA:
        d["extra"] = EXTRA
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


def _src():
    p = os.environ.get("YF_ENGINE_SRC")
    if p:
        return open(p, encoding="utf-8").read(), p
    from backtest import research11 as R
    return open(R.__file__, encoding="utf-8").read(), R.__file__


def engine_new():
    s, f = _src()
    if os.environ.get("YF_ENGINE_SRC"):
        return SP9._load_src(s, "backtest._r11_yf_new", f)
    from backtest import research11 as R
    return R


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return SP9._load_src(src, "backtest._r11_orig_yf", os.path.join(REPO, "backtest", "research11.py"))


MUT = {
    "MT_noperm": ("order = _perm[np.argsort(-key[_perm], kind=\"stable\")]         # _PT_ORDER", "order = np.argsort(-key, kind=\"stable\")  # _PT_ORDER"),
    "MT_asc": ("order = _perm[np.argsort(-key[_perm], kind=\"stable\")]         # _PT_ORDER", "order = _perm[np.argsort(key[_perm], kind=\"stable\")]  # _PT_ORDER"),
    "MT_nodraw": ("_perm = rng.permutation(len(cand))                           # _PT_DRAW", "_perm = np.arange(len(cand))  # _PT_DRAW"),
}


def mut_of(tag):
    s, f = _src(); a, b = MUT[tag]
    if s.count(a) != 1:
        raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一")
    return SP9._load_src(s.replace(a, b), f"backtest._r11_{tag}", f)


def sim(R, rows, prices, N, seed=0, rng=None, **kw):
    """rows：(sid, entry, exit, key)；sig 帶 K 欄。"""
    closes = {s: p[1] for s, p in prices.items()}; opens = {s: p[0] for s, p in prices.items()}
    sig = pd.DataFrame([{"sid": s, "entry_pos": e, "xpos_HX": x, "g_HX": float(closes[s][x]) / float(opens[s][e]) - 1.0, "K": k}
                        for s, e, x, k in rows])
    au = []; lg = []
    o = R.simulate_mtm(sig, "HX", N, rng if rng is not None else np.random.default_rng(seed), closes, opens, NC,
                       return_equity=True, audit=au, log=lg, **kw)
    o["_audit"] = au; o["_log"] = lg
    return o


def strip(o):
    return {k: v for k, v in o.items() if k not in ("_audit", "_log")}


def buys(o, t=None):
    return [r["sid"] for r in o["_audit"] if r["side"] == "buy" and (t is None or r["t"] == t)]


def fx_list(R):
    out = []

    def add(nm, ok, det=""):
        out.append((nm, bool(ok), det))

    def safe(fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            out.append((fn.__name__, False, f"例外 {type(e).__name__}: {e}"))

    def f1():
        # 同一天 A、B、C、D 鍵 3、5、5、1，N＝1 ⇒ 取 B 或 C（同分），誰先 ＝ 同顆種子那次 permutation 裡誰在前；pick_tie 不給 ⇒ 永遠 B（列序）
        pr = {s: px() for s in "ABCD"}
        rows = [("A", 10, 60, 3.0), ("B", 10, 60, 5.0), ("C", 10, 60, 5.0), ("D", 10, 60, 1.0)]
        bad = []; seen = set()
        for sd in range(30):
            pm = list(np.random.default_rng(sd).permutation(4)); want = "B" if pm.index(1) < pm.index(2) else "C"
            got = buys(sim(R, rows, pr, 1, seed=sd, pick="K", pick_tie="rng")); seen.add(got[0] if got else None)
            if got != [want]:
                bad.append((sd, got, want))
        g0 = {tuple(buys(sim(R, rows, pr, 1, seed=sd, pick="K"))) for sd in range(10)}
        add("F1 同分照同顆種子的抽籤：鍵 3、5、5、1、N＝1 ⇒ 30 顆都取 B／C 裡 permutation 在前的那檔（兩檔都出現過）；pick_tie 不給 ⇒ 永遠 B（列序）",
            not bad and seen == {"B", "C"} and g0 == {("B",)}, f"不符 {bad[:2]}；出現 {seen}；pick_tie 不給 {g0}")

    def f2():
        pr = {s: px() for s in "ABC"}
        rows = [("A", 10, 60, np.nan), ("B", 10, 60, np.nan), ("C", 10, 60, 1.0)]
        g = {tuple(buys(sim(R, rows, pr, 1, seed=sd, pick="K", pick_tie="rng"))) for sd in range(10)}
        rows2 = [("A", 10, 60, np.nan), ("B", 10, 60, np.nan)]
        bad = []
        for sd in range(20):
            pm = list(np.random.default_rng(sd).permutation(2)); want = "A" if pm.index(0) < pm.index(1) else "B"
            if buys(sim(R, rows2, pr, 1, seed=sd, pick="K", pick_tie="rng")) != [want]:
                bad.append(sd)
        add("F2 NaN 排最後（−∞）：鍵 NaN、NaN、1 ⇒ 永遠 C；全 NaN ⇒ 照抽籤", g == {("C",)} and not bad, f"{g}；不符 {bad}")

    def f3():
        # d_max＝1、queue_days＝2：t＝10 候選鍵 1、2、3 ⇒ 取 3（E3）、其餘排隊；t＝11 隊列（鍵 1、2）＋新訊號（鍵 1.5）⇒ 取隊列的 2（E2）
        pr = {s: px() for s in ("E1", "E2", "E3", "N1")}
        rows = [("E1", 10, 60, 1.0), ("E2", 10, 60, 2.0), ("E3", 10, 60, 3.0), ("N1", 11, 61, 1.5)]
        o = sim(R, rows, pr, 4, seed=3, pick="K", pick_tie="rng", d_max=1, queue_days=2)
        b10, b11, b12 = buys(o, 10), buys(o, 11), buys(o, 12)
        add("F3 d_max＝1＋queue_days＝2：t＝10 取鍵最大 E3；t＝11 隊列（E1 1、E2 2）＋新訊號 N1 1.5 一起排 ⇒ 取 E2（隊列裡的）；t＝12 取 N1",
            (b10, b11, b12) == (["E3"], ["E2"], ["N1"]), f"{b10} {b11} {b12}")

    def f4():
        pr = {s: px() for s in "AB"}
        rows = [("A", 10, 60, 1.0), ("B", 10, 60, 2.0)]
        ok = buys(sim(R, rows, pr, 1, seed=0, pick="K")) == ["B"] and buys(sim(R, rows, pr, 1, seed=0, pick="K", pick_tie="rng")) == ["B"]
        add("F4 自訂鍵欄（不在 _LOG_COLS 裡的 K 欄）可以用（原引擎會 KeyError）", ok)

    for fn in (f1, f2, f3, f4):
        safe(fn)
    return out


def world(rng, n_sid=6):
    sids = [f"S{i}" for i in range(n_sid)]
    pr = {}
    for s in sids:
        c = 10 * np.exp(np.cumsum(rng.normal(0.0, 0.03, NC)))
        pr[s] = (np.r_[10.0, c[:-1]] * np.exp(rng.normal(0, 0.01, NC)), c)
    rows = []
    for d in range(5, 80, 4):
        for s in rng.choice(sids, int(rng.integers(0, 5)), replace=False):
            k = float(rng.integers(0, 3)) if rng.random() > 0.1 else np.nan       # ⭐ 鍵只有 3 個值 ＋ 10% NaN ⇒ 同分很多
            rows.append((str(s), d, min(NC - 1, d + int(rng.integers(8, 40))), k))
    return pr, rows


def rand_equiv(R, n_w=300, seed=20261001):
    """引擎 pick_tie ＝ 診斷包裝 RankRng（pick=None、rng 換成包裝）逐位元；一半世界開 d_max＋queue_days、三分之一開 T1＋待買。"""
    rng = np.random.default_rng(seed); n_ok = 0; bad = []
    for w in range(n_w):
        pr, rows = world(rng)
        if not rows:
            n_ok += 1; continue
        N = int(rng.integers(2, 5)); kw = {}
        if w % 2:
            kw.update(d_max=int(rng.integers(1, 3)), queue_days=int(rng.integers(0, 3)))
        if w % 3 == 0:
            kw.update(trim_rule={"kind": "gain", "x": 0.15, "frac": 0.5}, trim_proceeds="next")
        key = {(s, e): k for s, e, x, k in rows}
        try:
            a = sim(R, rows, pr, N, pick="K", pick_tie="rng", rng=np.random.default_rng(w), **kw)
            b = sim(R, rows, pr, N, rng=RankRng(w, key), **kw)
            ok, why = same_out(strip(a), strip(b)); ok = ok and repr(a["_audit"]) == repr(b["_audit"])
        except Exception as e:  # noqa: BLE001
            ok, why = False, f"例外 {type(e).__name__}: {e}"
        n_ok += ok
        if not ok:
            bad.append((w, why))
    return n_ok, n_w, bad


def rand_const(R, n_w=200, seed=20261002):
    """常數鍵＋pick_tie ＝ 抽籤版（pick=None）逐位元（全部回傳、audit、log 去掉 K 欄）。"""
    rng = np.random.default_rng(seed); n_ok = 0; bad = []
    for w in range(n_w):
        pr, rows = world(rng)
        rows = [(s, e, x, 7.0) for s, e, x, _ in rows]
        if not rows:
            n_ok += 1; continue
        N = int(rng.integers(2, 5)); kw = dict(d_max=1, queue_days=2) if w % 2 else {}
        try:
            a = sim(R, rows, pr, N, seed=w, pick="K", pick_tie="rng", **kw); b = sim(R, rows, pr, N, seed=w, **kw)
            la = [{k: v for k, v in r.items() if k != "K"} for r in a["_log"]]
            ok, why = same_out(strip(a), strip(b)); ok = ok and repr(a["_audit"]) == repr(b["_audit"]) and repr(la) == repr(b["_log"])
        except Exception as e:  # noqa: BLE001
            ok, why = False, f"例外 {type(e).__name__}: {e}"
        n_ok += ok
        if not ok:
            bad.append((w, why))
    return n_ok, n_w, bad


def fixtures():
    R = engine_new()
    print(f"── 引擎 {os.environ.get('YF_ENGINE_SRC') or R.__file__}")
    import inspect
    chk("參數 pick_tie 存在、預設 None", inspect.signature(R.simulate_mtm).parameters["pick_tie"].default is None)
    for nm, ok, det in fx_list(R):
        chk(nm, ok, det)
    a, n, bad = rand_equiv(R)
    chk(f"隨機 {n} 個世界（鍵 3 值＋NaN、一半 d_max＋queue、三分之一 T1＋待買）：引擎 pick_tie ＝ 診斷包裝 RankRng 逐位元（全部回傳＋audit）", a == n, f"{a}/{n}；{bad[:2]}")
    a, n, bad = rand_const(R)
    chk(f"隨機 {n} 個世界：常數鍵＋pick_tie ＝ 抽籤版（pick=None）逐位元（全部回傳、audit、log）", a == n, f"{a}/{n}；{bad[:2]}")
    print("── 鑑別力")
    mut = {}
    for tag in MUT:
        M = mut_of(tag)
        failed = [nm.split(" ")[0] for nm, ok, _ in fx_list(M) if not ok]
        c1 = rand_const(M, n_w=60)[0]; e1 = rand_equiv(M, n_w=60)[0]
        mut[tag] = {"fixture 沒過": failed, "常數鍵＝抽籤 沒過": 60 - c1, "對包裝 沒過": 60 - e1}
        chk(f"鑑別力 {tag}：抓到", bool(failed) or c1 < 60 or e1 < 60, json.dumps(mut[tag], ensure_ascii=False))
    EXTRA["突變體"] = mut
    print("── None 路徑與防呆")
    R0 = engine_orig()
    rng = np.random.default_rng(13); n_same = n_all = 0
    for w in range(60):
        pr, rows = world(rng)
        if not rows:
            continue
        for kw0 in (dict(), dict(d_max=1, queue_days=2), dict(pick="relvol")):
            rows_ = rows
            if "pick" in kw0:                                      # relvol 欄（_LOG_COLS 裡的）
                closes = {s: p[1] for s, p in pr.items()}; opens = {s: p[0] for s, p in pr.items()}
                sig = pd.DataFrame([{"sid": s, "entry_pos": e, "xpos_HX": x, "g_HX": float(closes[s][x]) / float(opens[s][e]) - 1.0, "relvol": k}
                                    for s, e, x, k in rows_])
                outs = []
                for eng, kw1 in ((R0, kw0), (R, dict(kw0, pick_tie=None))):
                    au = []; lg = []
                    o = eng.simulate_mtm(sig, "HX", 3, np.random.default_rng(w), closes, opens, NC, return_equity=True, audit=au, log=lg, **kw1)
                    outs.append((o, repr(au), repr(lg)))
                ok, _ = same_out(outs[0][0], outs[1][0]); ok = ok and outs[0][1] == outs[1][1] and outs[0][2] == outs[1][2]
            else:
                a0 = sim(R0, rows_, pr, 3, seed=w, **kw0); a1 = sim(R, rows_, pr, 3, seed=w, pick_tie=None, **kw0)
                ok, _ = same_out(strip(a0), strip(a1)); ok = ok and repr(a0["_audit"]) == repr(a1["_audit"]) and repr(a0["_log"]) == repr(a1["_log"])
            n_all += 1; n_same += ok
    chk("pick_tie 省略／None 明寫 ×（抽籤、d_max＋queue、pick＝relvol）× 隨機世界 ⇒ 與改前引擎逐位元同（全部回傳、audit、log）", n_same == n_all, f"{n_same}/{n_all}")
    for nm, kw in (("pick_tie 沒給 pick", dict(pick_tie="rng")), ("pick_tie＝'random'", dict(pick="K", pick_tie="random"))):
        try:
            sim(R, [("A", 10, 60, 1.0)], {"A": px()}, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)
    try:
        sim(R0, [("A", 10, 60, 1.0)], {"A": px()}, 2, pick="K"); ok = False
    except KeyError:
        ok = True
    chk("（對照）改前引擎用自訂鍵欄 K 會 KeyError（本件修的限制）", ok)


# ─────────────────────────── 真資料閘（營飆 v1 主窗）
_G: dict = {}


def _ctx():
    from backtest import listexit_lines as L
    ctx = L.setup_t1(lambda x: print("  " + x, flush=True))
    K = pd.read_csv(os.path.join(OUT, "pre_keys.csv"), dtype={"sid": str}, usecols=["sid", "entry_pos"] + KEYS)
    sig = ctx["sig"].merge(K, on=["sid", "entry_pos"], how="left", validate="1:1")
    if sig[KEYS].isna().any().any() or len(sig) != len(ctx["sig"]):
        raise SystemExit("⛔ pre_keys 對不上訊號列")
    sig["KC"] = 1.0
    ctx["sigK"] = sig
    return ctx


def _run(eng, ctx, r, rng, **kw):
    au = []
    o = eng.simulate_mtm(ctx["sigK"], "H120", 10, rng, ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, audit=au, **kw)
    return o, au


def _ga(args):
    r, k = args
    R = engine_new(); ctx = _G["ctx"]
    key = {(s, int(e)): float(v) for s, e, v in zip(ctx["sigK"]["sid"], ctx["sigK"]["entry_pos"], ctx["sigK"][k])}
    a, aa = _run(R, ctx, r, np.random.default_rng(1000 + r), pick=k, pick_tie="rng")
    b, ab = _run(R, ctx, r, RankRng(1000 + r, key))
    ok, why = same_out(a, b)
    return {"r": r, "k": k, "same": bool(ok and repr(aa) == repr(ab)), "why": why,
            "buys_same": [(x["t"], x["sid"]) for x in aa if x["side"] == "buy"] == [(x["t"], x["sid"]) for x in ab if x["side"] == "buy"]}


def _gb(r):
    R = engine_new(); ctx = _G["ctx"]
    a, aa = _run(R, ctx, r, np.random.default_rng(1000 + r), pick="KC", pick_tie="rng")
    b, ab = _run(R, ctx, r, np.random.default_rng(1000 + r))
    ok, why = same_out(a, b)
    return {"r": r, "same": bool(ok and repr(aa) == repr(ab)), "why": why,
            "eq_sha": hashlib.sha256(np.asarray(a["equity"], float).tobytes()).hexdigest()[:16]}


def gate_ab(which, reps=200, procs=2):
    ctx = _ctx(); _G["ctx"] = ctx
    with Pool(procs) as pool:
        if "a" in which:
            A = pd.DataFrame(pool.map(_ga, [(r, k) for k in KEYS for r in range(reps)], chunksize=5))
            per = A.groupby("k")["same"].sum().to_dict()
            chk(f"(a) 引擎 pick=K*, pick_tie='rng' ＝ pre 的診斷包裝 RankRng：{reps} 顆 × 5 鍵逐位元（全部回傳、audit；買進清單逐筆）",
                bool(A["same"].all() and A["buys_same"].all()), f"逐鍵相同 {per}；不同 {A.loc[~A['same'], ['r', 'k', 'why']].head(3).values.tolist()}")
        if "b" in which:
            B = pd.DataFrame(pool.map(_gb, range(reps), chunksize=5))
            ref = pd.read_csv(os.path.join(ctx["RR"].OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str})
            ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r")
            e_ok = bool((B.set_index("r")["eq_sha"] == ref.loc[range(reps), "eq_sha"]).all())
            chk(f"(b) 常數鍵＋pick_tie ＝ 抽籤版（pick=None）{reps} 顆逐位元（全部回傳、audit），且 eq_sha ＝ regime_t1 t1 #1", bool(B["same"].all()) and e_ok,
                f"相同 {int(B['same'].sum())}/{reps}；eq_sha ＝ regime_t1 {e_ok}")


def gate_c(reps=20):
    from backtest import data as D, rerun17 as RR
    RR.use_snapshot()
    cal = D.load_calendar()
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", lambda x: print("  " + x, flush=True))
    ref = pd.read_csv(os.path.join(RR.OUT, "rerun17_seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["stage"] == "main") & (ref["mode"] == "win") & (ref["cell"] == 13)].set_index("r")
    sp = RR.CELLS[12]
    assert sp[0] == 13 and sp[4]["pick"] == "relvol"
    bad = []
    for r in range(reps):
        row = RR._one((13, "win", r)); q = ref.loc[r]
        same = all(repr(float(row[k])) == repr(float(q[k])) for k in ("cagr", "mdd", "vol")) and \
            all(int(row[k]) == int(q[k]) for k in ("first", "end", "trades")) and row["eq_sha"] == str(q["eq_sha"])
        if not same:
            bad.append(r)
    chk(f"(c) pick_tie 不給 ⇒ #13（{sp[3]}）rerun17 main／win {reps} 顆逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha；⛔ 數值不印）",
        not bad, f"不同 {bad}")


def gate1():
    os.chdir(REPO)
    if not os.environ.get("YF_ENGINE_SRC"):
        for scr, n in (("regress_tradability.py", 18), ("regress_delist.py", 6)):
            p = subprocess.run([PY, os.path.join(REPO, "backtest", scr), "check"], cwd=REPO, capture_output=True, text=True)
            tail = [ln for ln in p.stdout.strip().split("\n") if ln][-1:] if p.stdout else []
            chk(f"{scr} check（{n} 組）逐位元相同", p.returncode == 0 and "✅" in p.stdout, " ".join(tail) + (p.stderr[-300:] if p.returncode else ""))
    from backtest import selftest_listexit as SL
    src = open(SL.__file__, encoding="utf-8").read()
    a = src.index("def gate1():"); b = src.index("\n\n# ─────────────────────────── 回歸閘 2")
    g = src[a:b]

    def rp(x, y):
        nonlocal g
        if g.count(x) != 1:
            raise SystemExit(f"⛔ gate1 改寫找不到：{x[:60]!r}")
        g = g.replace(x, y)
    rp("R = engine_new(); R0 = engine_orig()", "R = _NEW(); R0 = _ORIG()")
    rp('"stop_line（改後明寫 stop_line_le=False、stop_proceeds=None、stop_block=None）＋audit": dict(stop_line=sl, _audit=True, _none=True)}',
                  '"stop_line（改後明寫 stop_line_le=False、stop_proceeds=None、stop_block=None）＋audit": dict(stop_line=sl, _audit=True, _none=True),\n'
                  '           "pick relvol＋d_max＋queue＋log（改後明寫 pick_tie=None）": dict(pick="relvol", d_max=2, queue_days=3, _log=True, _pt=True)}')
    rp('                if kw.pop("_none", False) and eng is R:', '                if kw.pop("_pt", False) and eng is R:\n                    kw["pick_tie"] = None\n                if kw.pop("_none", False) and eng is R:')
    rp("改前（blob 52ce7677）", "改前（blob 5331e1cd）"); rp("改前（b1717d5c19）", "改前（84de67ccaf）")
    rp('    if not os.environ.get("LX_ENGINE_SRC"):\n', '    if False:\n')
    ns = dict(SL.__dict__); ns.update(_NEW=engine_new, _ORIG=engine_orig, chk=chk, EXTRA=EXTRA)
    exec(compile(g, "<gate1_yf>", "exec"), ns)
    ns["gate1"]()


def _snap(d, pred=lambda f: True):
    return {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and pred(f)}


def gate2():
    os.chdir(REPO)
    dirs = [(os.path.join(REPO, "backtest", "resultsp9_engine"), lambda f: True),
            (os.path.join(REPO, "backtest", "resultsAvg"), lambda f: f.startswith(("engine_b_", "engine_b2_", "engine_b3_"))),
            (os.path.join(REPO, "backtest", "resultsListExit"), lambda f: f.startswith("engine_"))]
    snaps = [(d, p, _snap(d, p), set(os.listdir(d))) for d, p in dirs]
    print(f"── 回歸閘 2（先存 {sum(len(s) for _, _, s, _ in snaps)} 個入庫檔，跑完寫回）")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AVG_ENGINE", "LX_", "YF_"))}
    js = {}
    try:
        t0 = time.time()
        p = subprocess.run([PY, os.path.join(REPO, "backtest", "selftest_listexit.py"), "all"], cwd=REPO, capture_output=True, text=True, env=env)
        got = {"rc": p.returncode, "secs": round(time.time() - t0), "err": p.stderr[-2000:] if p.returncode else ""}
        print(f"  [selftest_listexit.py all] rc={p.returncode}（{got['secs']}s）", flush=True)
        for tag in ("fixtures", "gate1", "gate2", "t1gate", "nonid"):
            js[tag] = json.loads(open(os.path.join(REPO, "backtest", "resultsListExit", f"engine_{tag}.json"), encoding="utf-8").read())
    finally:
        for d, pred, snap, _ in snaps:
            for f in list(os.listdir(d)):
                pth = os.path.join(d, f)
                if os.path.isfile(pth) and pred(f) and f not in snap:
                    os.remove(pth)
            for f, b in snap.items():
                open(os.path.join(d, f), "wb").write(b)
        back = all(open(os.path.join(d, f), "rb").read() == b for d, _, snap, _ in snaps for f, b in snap.items())
        new_files = [f for d, _, _, before in snaps for f in sorted(set(os.listdir(d)) - before)]
        print(f"  已寫回原位元組：{back}；多出來的檔 {new_files}")
    chk("selftest_listexit.py all 結束碼 0", got["rc"] == 0, got["err"][-300:])
    for tag, want in (("fixtures", 48), ("gate1", 3), ("gate2", 13), ("t1gate", 3), ("nonid", 3)):
        d = js[tag]
        chk(f"selftest_listexit {tag}：{d['n'] - d['fail']}/{d['n']} 過（84de67ccaf 交件時 {want} 條全過）", d["fail"] == 0 and d["n"] == want,
            "; ".join(c["name"][:60] for c in d["checks"] if not c["ok"])[:400])
    g2 = js["gate2"]["checks"]
    for key in ("selftest_avgengine3", "（內含）selftest_avgengine2", "P9 基準臂", "既有結果檔"):
        hit = [c for c in g2 if key in c["name"]]
        chk(f"（內含）{key}（{len(hit)} 條）", len(hit) >= 1 and all(c["ok"] for c in hit), hit[0]["name"][:120] if hit else "找不到")
    chk("入庫檔已逐位元組寫回（resultsp9_engine、resultsAvg/engine_b*_、resultsListExit/engine_*）", back and not new_files, f"{new_files}")
    EXTRA["子行程秒"] = got["secs"]


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.chdir(REPO)
    t0 = time.time(); fails = 0
    steps = (("fixtures", fixtures), ("gate_a", lambda: gate_ab("a")), ("gate_b", lambda: gate_ab("b")), ("gate_c", gate_c),
             ("gate1", gate1), ("gate2", gate2))
    for m_, fn in steps:
        if mode in (m_, "all"):
            RESULTS.clear(); EXTRA.clear(); fn(); dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

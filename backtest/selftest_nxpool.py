# -*- coding: utf-8 -*-
"""裁定 seq200 ⓓ：引擎 simulate_mtm 的 nx_pool（補股池放寬）fixture 與閘門。回測線，2026-09-26。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 python backtest/selftest_nxpool.py fixtures  # 手算（池補股、池空等、不用 sig 補、尾端延長、同顆 rng）、突變體、None 路徑、防呆
    ... gate1   # regress_tradability 18＋regress_delist 6＋改前（blob e237a0f8＝e8939d4ba8）／改後 A/B（借 selftest_yfrank.gate1 的 43 種組合 × 2 種子）
    ... gate2   # selftest_yfrank.py all（內含 selftest_listexit all ⇒ selftest_avgengine3 all ⇒ …、P9 基準臂）；入庫檔跑完寫回
    ... all
⛔ 不讀報酬。結果寫到 backtest/resultsYfStop/nxpool_{fixtures,gate1,gate2}.json。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest", "resultsYfStop")
PY = sys.executable
ORIG_BLOB = "e237a0f8b0f908593699a8fbb13a57bd1a898fbd"      # 改動前 HEAD:backtest/research11.py（e8939d4ba8）
RESULTS: list = []
EXTRA: dict = {}

from backtest import selftest_p9engine as SP9        # noqa: E402
px, same_out, trad_of, close_to, NC = SP9.px, SP9.same_out, SP9.trad_of, SP9.close_to, SP9.NC


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"nxpool_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS), "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if EXTRA:
        d["extra"] = EXTRA
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


def _src():
    p = os.environ.get("NP_ENGINE_SRC")
    if p:
        return open(p, encoding="utf-8").read(), p
    from backtest import research11 as R
    return open(R.__file__, encoding="utf-8").read(), R.__file__


def engine_new():
    s, f = _src()
    if os.environ.get("NP_ENGINE_SRC"):
        return SP9._load_src(s, "backtest._r11_np_new", f)
    from backtest import research11 as R
    return R


def engine_orig():
    src = subprocess.check_output(["git", "-C", REPO, "cat-file", "-p", ORIG_BLOB]).decode("utf-8")
    return SP9._load_src(src, "backtest._r11_orig_np", os.path.join(REPO, "backtest", "research11.py"))


MUT = {
    "MP_main": ("_nx_buy = False                  # seq200 ⓓ", "_nx_buy = _nx_buy                  # seq200 ⓓ"),        # sig 也拿去補
    "MP_held": ('cp = gp[~gp["sid"].isin(held)] if gp is not None else None', "cp = gp"),                                  # 池沒排除持股
    "MP_nodraw": ("permp = rng.permutation(len(cp))", "permp = np.arange(len(cp))"),                                      # 不照抽籤
    "MP_last": ("last = max(last, int(_nxp[\"exit_pos\"].max()))", "last = last"),                                        # 尾端沒延
}


def mut_of(tag):
    s, f = _src(); a, b = MUT[tag]
    if s.count(a) != 1:
        raise SystemExit(f"⛔ 突變點 {tag} 找不到或不唯一")
    return SP9._load_src(s.replace(a, b), f"backtest._r11_{tag}", f)


def mk(rows, closes, opens):
    return pd.DataFrame([{"sid": s, "entry_pos": e, "xpos_HX": x, "g_HX": float(closes[s][x]) / float(opens[s][e]) - 1.0} for s, e, x in rows])


def sim(R, rows, pool_rows, prices, N, seed=0, **kw):
    closes = {s: p[1] for s, p in prices.items()}; opens = {s: p[0] for s, p in prices.items()}
    au = []
    kw = dict(kw)
    if pool_rows is not None:
        kw["nx_pool"] = mk(pool_rows, closes, opens)
    o = R.simulate_mtm(mk(rows, closes, opens), "HX", N, np.random.default_rng(seed), closes, opens, NC, return_equity=True, audit=au, **kw)
    o["_audit"] = au
    return o


def sl_of(rows, lv=9.0):
    return {(s, e): (e, np.full(x - e + 1, lv)) for s, e, x in rows}


def buys(o):
    return [(r["t"], r["sid"], r.get("kind")) for r in o["_audit"] if r["side"] == "buy"]


def fx_list(R):
    out = []

    def add(nm, ok, det=""):
        out.append((nm, bool(ok), det))

    def safe(fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            out.append((fn.__name__, False, f"例外 {type(e).__name__}: {e}"))

    C = R.COST
    down = px((0, 20, 10, 10), (20, 21, 10, 8.9), (21, NC, 8.8, 8.8))

    def p1():
        # N＝3：A、B 在 10 進；A t＝21 開盤停損 ⇒ 待買 L；t＝25 sig 沒有訊號、池有 D ⇒ 用 L 買 D（kind nx）；t＝30 sig 的 C ⇒ 一般新部位
        pr = {"A": down, "B": px(), "C": px(), "D": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("C", 30, 80)]
        pool = rows + [("D", 25, 75)]
        o = sim(R, rows, pool, pr, 3, stop_line=sl_of(pool), stop_line_le=True, stop_proceeds="next")
        L = (1 / 3) * (1 + (8.8 / 10.0 - 1.0) - C)
        b = buys(o); nb = [(r["t"], r["sid"], r["amt"]) for r in o["_audit"] if r.get("kind") == "nx"]
        add("P1 池補股：sig 沒訊號的 t＝25、池有 D ⇒ 停損的錢全額買 D（kind nx、等 4 天）；t＝30 sig 的 C 照一般新部位",
            [x for x in b if x[0] >= 25] == [(25, "D", "nx"), (30, "C", None)] and close_to(nb[0][2], L) and o["x_nx_pool_n"] == 1 and o["x_nx_waits"] == [4],
            f"{b}；{nb}")

    def p2():
        # 池當天只有已持有的 B ⇒ 等（pool_empty）；下一個池日 E ⇒ 買
        pr = {"A": down, "B": px(), "E": px()}
        rows = [("A", 10, 60), ("B", 10, 70)]
        pool = rows + [("B", 25, 70), ("E", 28, 78)]
        o = sim(R, rows, pool, pr, 3, stop_line=sl_of(pool), stop_line_le=True, stop_proceeds="next")
        b = [x for x in buys(o) if x[0] >= 21]
        add("P2 池只有已持有的 B ⇒ 不重買、等（x_nx_pool_empty_days ≥ 1）；t＝28 池有 E ⇒ 買", b == [(28, "E", "nx")] and o["x_nx_pool_empty_days"] >= 1,
            f"{b}；empty {o['x_nx_pool_empty_days']}")

    def p3():
        # sig 在 t＝22 有 E、池沒有 E ⇒ E 照一般新部位（⛔ 不用待買）；待買等到池有 F（t＝26）
        pr = {"A": down, "B": px(), "E": px(), "F": px()}
        rows = [("A", 10, 60), ("B", 10, 70), ("E", 22, 72)]
        pool = [("A", 10, 60), ("B", 10, 70), ("F", 26, 76)]
        o = sim(R, rows, pool, pr, 4, stop_line=sl_of(rows + pool), stop_line_le=True, stop_proceeds="next")
        b = [x for x in buys(o) if x[0] >= 21]
        add("P3 待買只從池挑：sig 的 E（池裡沒有）⇒ 一般新部位；待買等到池的 F", b == [(22, "E", None), (26, "F", "nx")], f"{b}")

    def p4():
        # 池列的出場（t＝95）晚於 sig 的最後出場（t＝70）⇒ 模擬延到 95、D 在 95 收盤出場
        pr = {"A": down, "B": px(), "D": px()}
        rows = [("A", 10, 60), ("B", 10, 70)]
        pool = rows + [("D", 25, 95)]
        o = sim(R, rows, pool, pr, 3, stop_line=sl_of(pool), stop_line_le=True, stop_proceeds="next")
        sd = [r["t"] for r in o["_audit"] if r["side"] == "sell" and r["sid"] == "D"]
        add("P4 池列持有期超過 sig 的最後出場 ⇒ 模擬尾端延長、D 在自己的 xpos（95）出場", sd == [95] and o["end"] >= 96, f"D 賣 {sd}；end {o['end']}")

    def p5():
        # 同顆種子 rng 接著抽：t＝10 sig 兩檔（抽 permutation(2)）；t＝25 池 3 檔（抽 permutation(3)）⇒ 買的是 perm3[0]
        pr = {"A": down, "B": px(), "P": px(), "Q": px(), "R": px()}
        rows = [("A", 10, 60), ("B", 10, 70)]
        pool = rows + [("P", 25, 80), ("Q", 25, 80), ("R", 25, 80)]
        bad = []; seen = set()
        for sd in range(20):
            g = np.random.default_rng(sd); g.permutation(2); pm = g.permutation(3); want = "PQR"[pm[0]]
            o = sim(R, rows, pool, pr, 3, seed=sd, stop_line=sl_of(pool), stop_line_le=True, stop_proceeds="next")
            got = [x[1] for x in buys(o) if x[2] == "nx"]; seen.add(got[0] if got else None)
            if got != [want]:
                bad.append((sd, got, want))
        add("P5 池那一抽 ＝ 同顆種子 rng 接著抽（t＝10 sig 抽 2、t＝25 池抽 3 ⇒ 買 perm[0]；20 顆）", not bad and len(seen) >= 2, f"不符 {bad[:2]}；出現 {seen}")

    for fn in (p1, p2, p3, p4, p5):
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
        for s in rng.choice(sids, int(rng.integers(0, 4)), replace=False):
            rows.append((str(s), d, min(NC - 1, d + int(rng.integers(8, 40)))))
    return pr, rows


def fixtures():
    R = engine_new()
    print(f"── 引擎 {os.environ.get('NP_ENGINE_SRC') or R.__file__}")
    import inspect
    chk("參數 nx_pool 存在、預設 None", inspect.signature(R.simulate_mtm).parameters["nx_pool"].default is None)
    for nm, ok, det in fx_list(R):
        chk(nm, ok, det)
    mut = {}
    for tag in MUT:
        failed = [nm.split(" ")[0] for nm, ok, _ in fx_list(mut_of(tag)) if not ok]
        mut[tag] = failed
        chk(f"鑑別力 {tag}：抓到", bool(failed), json.dumps(failed, ensure_ascii=False))
    EXTRA["突變體"] = mut
    R0 = engine_orig()
    rng = np.random.default_rng(21); n_same = n_all = 0
    for w in range(60):
        pr, rows = world(rng)
        if not rows:
            continue
        sl = sl_of(rows, 9.5)
        for kw in (dict(), dict(stop_line=sl, stop_proceeds="next"), dict(trim_rule={"kind": "gain", "x": 0.15, "frac": 0.5}, trim_proceeds="next"),
                   dict(d_max=1, queue_days=2)):
            a0 = sim(R0, rows, None, pr, 3, seed=w, **kw); a1 = sim(R, rows, None, pr, 3, seed=w, nx_pool=None, **kw)
            ok, _ = same_out({k: v for k, v in a0.items() if k != "_audit"}, {k: v for k, v in a1.items() if k != "_audit"})
            n_all += 1; n_same += ok and repr(a0["_audit"]) == repr(a1["_audit"])
    chk("nx_pool 省略／None 明寫 ×（全關、停損＋待買、T1＋待買、d_max＋queue）× 隨機世界 ⇒ 與改前引擎逐位元同", n_same == n_all, f"{n_same}/{n_all}")
    pr = {"A": px()}; rows = [("A", 10, 60)]
    for nm, kw in (("nx_pool 沒開待買", dict()), ("nx_pool＋pick", dict(stop_line=sl_of(rows), stop_proceeds="next", pick="g_HX")),
                   ("nx_pool＋d_max", dict(stop_line=sl_of(rows), stop_proceeds="next", d_max=1))):
        try:
            sim(R, rows, rows, pr, 2, **kw); ok = False
        except ValueError:
            ok = True
        chk(f"防呆：{nm} ⇒ ValueError", ok)


def gate1():
    from backtest import selftest_yfrank as SY
    orig_chk = SY.chk

    def chk2(name, cond, detail=""):
        return chk(name.replace("84de67ccaf", "e8939d4ba8").replace("5331e1cd", "e237a0f8"), cond, detail)
    SY.chk = chk2; SY.EXTRA = EXTRA; SY.engine_new = engine_new; SY.engine_orig = engine_orig
    os.environ.pop("YF_ENGINE_SRC", None)
    try:
        SY.gate1()
    finally:
        SY.chk = orig_chk


def _snap(d, pred=lambda f: True):
    return {f: open(os.path.join(d, f), "rb").read() for f in os.listdir(d) if os.path.isfile(os.path.join(d, f)) and pred(f)}


def gate2():
    os.chdir(REPO)
    B = os.path.join(REPO, "backtest")
    dirs = [(os.path.join(B, "resultsp9_engine"), lambda f: True),
            (os.path.join(B, "resultsAvg"), lambda f: f.startswith(("engine_b_", "engine_b2_", "engine_b3_"))),
            (os.path.join(B, "resultsListExit"), lambda f: f.startswith("engine_")),
            (os.path.join(B, "resultsYfRank"), lambda f: f.startswith("engine_"))]
    snaps = [(d, p, _snap(d, p), set(os.listdir(d))) for d, p in dirs]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AVG_ENGINE", "LX_", "YF_", "NP_"))}
    js = {}
    try:
        t0 = time.time()
        p = subprocess.run([PY, os.path.join(B, "selftest_yfrank.py"), "all"], cwd=REPO, capture_output=True, text=True, env=env)
        got = {"rc": p.returncode, "secs": round(time.time() - t0), "err": p.stderr[-2000:] if p.returncode else ""}
        print(f"  [selftest_yfrank.py all] rc={p.returncode}（{got['secs']}s）", flush=True)
        for tag in ("fixtures", "gate_a", "gate_b", "gate_c", "gate1", "gate2"):
            js[tag] = json.loads(open(os.path.join(B, "resultsYfRank", f"engine_{tag}.json"), encoding="utf-8").read())
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
    chk("selftest_yfrank.py all 結束碼 0", got["rc"] == 0, got["err"][-300:])
    for tag, want in (("fixtures", 14), ("gate_a", 1), ("gate_b", 1), ("gate_c", 1), ("gate1", 3), ("gate2", 11)):
        d = js[tag]
        chk(f"selftest_yfrank {tag}：{d['n'] - d['fail']}/{d['n']} 過（e8939d4ba8 交件時 {want} 條全過）", d["fail"] == 0 and d["n"] == want)
    chk("入庫檔已逐位元組寫回（resultsp9_engine、resultsAvg/engine_b*_、resultsListExit/engine_*、resultsYfRank/engine_*）", back and not new_files, f"{new_files}")
    EXTRA["子行程秒"] = got["secs"]


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.chdir(REPO)
    fails = 0; t0 = time.time()
    for m_, fn in (("fixtures", fixtures), ("gate1", gate1), ("gate2", gate2)):
        if mode in (m_, "all"):
            RESULTS.clear(); EXTRA.clear(); fn(); dump(m_); fails += sum(not r["ok"] for r in RESULTS)
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if fails else 0)

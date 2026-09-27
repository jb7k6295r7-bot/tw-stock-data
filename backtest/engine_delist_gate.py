# -*- coding: utf-8 -*-
"""research11.simulate_mtm(stop_force=…) 的閘門（裁定線 seq255 §一 4；回測線 2026-09-27）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/engine_delist_gate.py --orig <HEAD 版 research11.py 的路徑> [--procs 2]

閘 0 fixture：backtest/selftest_stopforce.py 全過
閘 1 關閉時逐位元相同：
  1a 營飆 v1 骨架 regime_t1 #1（N10）、#17（N20）各 200 顆 ⇒ cagr／mdd／vol repr、first／end／trades、eq_sha ＝ resultsN17/regime_t1/seeds.csv（stage t1）
  1b researchSigMA 確認段挑中格（E1、E2 × 跌破 MA60）各 10 顆 ⇒ 新引擎（開關關）與 HEAD 版引擎的 equity 陣列、回傳 dict 逐位元相同；
     前 5 顆的 cagr／mdd ＝ resultsSigMA/confirm_audit5.csv.gz
閘 2 共用函式：research11.stop_force_days ＝ researchSigMA_f60.stopped（確認段 upto＝段尾）逐檔相同
閘 3 開關打開 ⇒ 重現 f60 描述臂：未過濾 E2 MA60（−0.07 點）、過濾 E2 MA60（−0.04 點）的強制出場後年化／回落 ＝ resultsSigMA/f60/summary.json
閘 4（描述，裁定追加）開關打開：營飆 v1 #1 200 顆 ⇒ 年化／回落中位與原件差多少（K5 下市處理不一致）
輸出 backtest/resultsEngineDelist/：gate.json、yf_seeds.csv、GATE.md
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, subprocess, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import listexit_lines as LX
from backtest import rerun17 as RR
from backtest import research11 as R
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsEngineDelist")
_G = {}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def one_t1(args):
    N, r, on = args
    C = _G["CTX"]
    kw = {"stop_force": _G["SF"]} if on else {}
    s = R.simulate_mtm(C["sig"], "H120", N, np.random.default_rng(1000 + r), C["closes"], C["opens"], C["ncal"], return_equity=True, **kw)
    c, m, v = RR.win_metrics(s["equity"], s["first"], s["end"], C["w0"], C["w1"])
    return {"N": N, "r": r, "on": on, "cagr": c, "mdd": m, "vol": v, "first": int(s["first"]), "end": int(s["end"]), "trades": int(s["trades"]),
            "eq_sha": sha(s["equity"]), "forced": int(s.get("x_stop_force_n", -1))}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--orig", required=True); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); G = {}; t00 = time.time()
    G["程式"] = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("research11.py", "selftest_stopforce.py", "engine_delist_gate.py")}
    G["HEAD 版 research11.py"] = hashlib.sha256(open(a.orig, "rb").read()).hexdigest()[:16]
    # 閘 0
    r0 = subprocess.run([sys.executable, os.path.join(HERE, "selftest_stopforce.py")], capture_output=True, text=True)
    G["閘0_fixture"] = r0.stdout.strip(); print(G["閘0_fixture"])
    # 閘 1a
    CTX = LX.setup_t1(log=lambda x: None); _G["CTX"] = CTX
    with Pool(a.procs) as p:
        d = pd.DataFrame(p.map(one_t1, [(N, r, False) for N in (10, 20) for r in range(200)], chunksize=8))
    ref = pd.read_csv(os.path.join(HERE, "resultsN17/regime_t1/seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    g1a = {}
    for N, cell in ((10, 1), (20, 17)):
        x = d[d["N"] == N].sort_values("r").reset_index(drop=True); y = ref[(ref["stage"] == "t1") & (ref["cell"] == cell)].sort_values("r").reset_index(drop=True)
        bad = {k: int(sum(repr(float(u)) != repr(float(w)) for u, w in zip(x[k], y[k]))) for k in ("cagr", "mdd", "vol")}
        bad.update({k: int((x[k].astype(str) != y[k].astype(str)).sum()) for k in ("eq_sha", "trades", "first", "end")})
        g1a[f"#{cell}（N{N}）200 顆"] = bad
    G["閘1a_關閉＝regime_t1"] = g1a; print(g1a)
    # 閘 1b：researchSigMA 確認段挑中格 10 顆，新（關）vs HEAD 版
    spec = importlib.util.spec_from_file_location("backtest.r11orig", a.orig); R0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(R0)
    import researchSigMA_f60 as F6
    SMA, RS = F6.SMA, F6.RS
    RR.use_snapshot()

    class A_: pass
    cal, mon, elig, mk, SIG, VAL = SMA.setup(A_(), print)
    ncal = len(cal)
    s0, s1 = (int(cal.searchsorted(pd.Timestamp(v))) for v in RS.SEG["確認"])
    M = SMA.ma_cache(SIG, mk, cal, 1, os.path.join(SMA.OUT, "ma_cache.pkl"), print)
    SIGM = {sid: {**S_, **M.get(sid, {})} for sid, S_ in SIG.items()}
    MA = F6.ma60_cache(SIG, mk, cal, os.path.join(F6.OUT, "ma60_cache.pkl"), print)
    SIGF = F6.filt(SIGM, MA)
    cz, oz = RR.load_prices(sorted(SIGM), cal, mk, "branch")
    A5 = pd.read_csv(os.path.join(SMA.OUT, "confirm_audit5.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    g1b = {}
    cells = {}
    for ver, SG in (("未過濾", SIGM), ("過濾", SIGF)):
        for E in ("E1", "E2"):
            R_, _, _ = SMA.rows_for(SG, elig, mon, E, "MA60", s0, s1)
            cells[(ver, E)] = SMA.cell_of(R_.reset_index(drop=True), s1, cz, oz)
    for E in ("E1", "E2"):
        sig, kw, _ = cells[("未過濾", E)]; bad = 0; m5 = 0
        for r in range(10):
            n = R.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, **kw)
            o = R0.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, **kw)
            same = np.array_equal(n["equity"], o["equity"]) and set(n) == set(o) and all(
                (repr(n[k]) == repr(o[k])) if not isinstance(n[k], np.ndarray) else np.array_equal(n[k], o[k]) for k in n)
            bad += not same
            if r < 5:
                c_, m_, _ = RR.win_metrics(np.asarray(n["equity"], float), n["first"], n["end"], s0, s1)
                ref5 = A5[(A5["cell"] == f"確認|{E}|MA60") & (A5["r"] == r) & (A5["sid"] == "_metrics")].iloc[0]
                m5 += not (repr(float(c_)) == repr(float(ref5["amt"])) and repr(float(m_)) == repr(float(ref5["px"])))
        g1b[f"researchSigMA 確認 {E} MA60"] = {"10 顆 新（關）≠ HEAD 版": bad, "前 5 顆 ≠ confirm_audit5": m5}
    G["閘1b_關閉＝HEAD 版"] = g1b; print(g1b)
    # 閘 2
    valid = {s_: np.unpackbits(VAL[s_])[:ncal].astype(bool) for s_ in VAL}
    SFc = R.stop_force_days(valid, s1)
    G["閘2_共用函式＝f60.stopped"] = {"相同": SFc == F6.stopped(VAL, ncal, s1), "檔數": len(SFc)}; print(G["閘2_共用函式＝f60.stopped"])
    # 閘 3：開關打開 ⇒ 重現 f60 描述臂
    S6 = json.load(open(os.path.join(F6.OUT, "summary.json"), encoding="utf-8"))["引擎缺口"]["結果"]
    B50 = RR.bench_row(cal, RR.load_bench(cal), s0, s1 + 1)
    g3 = {}
    for ver in ("未過濾", "過濾"):
        for E in ("E1", "E2"):
            sig, kw, _ = cells[(ver, E)]
            cg, mg = [], []
            for r in range(200):
                n = R.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, stop_force=SFc, **kw)
                c_, m_, _ = RR.win_metrics(np.asarray(n["equity"], float), n["first"], n["end"], s0, s1); cg.append(c_); mg.append(m_)
            ref = S6[f"缺口臂|{ver}|{E}|MA60"]
            cm, mm = float(np.median(cg)), float(np.median(mg))
            g3[f"{ver}|{E}"] = {"開關_年化": cm, "開關_回落": mm, "f60_年化": ref["強制出場後_年化"], "f60_回落": ref["強制出場後_回落"],
                                "逐位元相同": repr(cm) == repr(float(ref["強制出場後_年化"])) and repr(mm) == repr(float(ref["強制出場後_回落"])),
                                "對原樣_年化差點": (cm - ref["原樣_年化"]) * 100}
    G["閘3_開關＝f60 描述臂"] = g3; print(g3)
    # 閘 4：營飆 v1 #1 開關打開 200 顆
    RR.use_snapshot()
    vy = R.valid_from_data(sorted(set(CTX["sig"]["sid"])), CTX["mk"], CTX["cal"])
    SF = R.stop_force_days(vy, CTX["w1"]); _G["SF"] = SF
    with Pool(a.procs) as p:
        on = pd.DataFrame(p.map(one_t1, [(10, r, True) for r in range(200)], chunksize=8))
    on.to_csv(os.path.join(OUT, "yf_seeds.csv"), index=False)
    off = d[d["N"] == 10].set_index("r").sort_index(); on_ = on.set_index("r").sort_index()
    bw = RR.bench_row(CTX["cal"], RR.load_bench(CTX["cal"]), CTX["w0"], CTX["w1"] + 1)
    c1, m1 = float(on_["cagr"].median()), float(on_["mdd"].median()); c0, m0 = float(off["cagr"].median()), float(off["mdd"].median())
    r50 = bw["cagr"] / abs(bw["mdd"])
    lab = lambda c, m: "合格" if (c > bw["cagr"] and c / abs(m) >= r50) else ("另列" if c > bw["cagr"] else "不合格")
    G["閘4_營飆v1_#1_開關打開"] = {"停止交易股（訊號股內、主窗內）": len(SF), "強制出場每顆平均": float(on_["forced"].mean()),
                              "原件_年化": c0, "原件_回落": m0, "開關_年化": c1, "開關_回落": m1, "年化差_點": (c1 - c0) * 100, "回落差_點": (m1 - m0) * 100,
                              "標籤_原件": lab(c0, m0), "標籤_開關": lab(c1, m1), "逐顆_年化變動顆數": int((on_["cagr"] != off["cagr"]).sum()),
                              "例（最多 10 檔）": {s_: str(CTX["cal"][L_].date()) for s_, L_ in list(sorted(SF.items()))[:10]}}
    print(G["閘4_營飆v1_#1_開關打開"])
    G["秒"] = round(time.time() - t00)
    json.dump(G, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    ok = ("全過" in G["閘0_fixture"] and all(v == 0 for g in g1a.values() for v in g.values())
          and all(v == 0 for g in g1b.values() for v in g.values()) and G["閘2_共用函式＝f60.stopped"]["相同"] and all(x["逐位元相同"] for x in g3.values()))
    G["全部過"] = ok
    json.dump(G, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("閘門：" + ("全過" if ok else "⛔ 有不過"))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""使用者 09-26（直接對回測線）：「營飆檔數幫我測一下10、20、30檔（含交易成本）結果」
⭐ 敏感度描述：⛔ 不計 N、⛔ 不換營飆 v1 的 10 檔。其餘（訊號、t−1 大盤閘、H120、200 顆種子 1000＋r、主窗、成本 0.585% 來回）一字不動。
閘：N10 ＝ regime_t1 t1 #1（營飆 v1）逐位元；N20 ＝ regime_t1 t1 #17（AND regime=True N20 H120）逐位元
輸出 backtest/resultsN17/nslots/：seeds.csv、cells.csv、run.log
"""
import os, sys, hashlib, json
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import listexit_lines as LX
from backtest import rerun17 as RR
from backtest import research11 as E
from backtest import rerun17_table as RT

OUT = "backtest/resultsN17/nslots"; os.makedirs(OUT, exist_ok=True)
NS = [10, 20, 30]
CTX = LX.setup_t1(log=lambda x: None)


def one(args):
    N, r = args
    s = E.simulate_mtm(CTX["sig"], "H120", N, np.random.default_rng(1000 + r), CTX["closes"], CTX["opens"], CTX["ncal"], return_equity=True)
    eq, hv = s["equity"], s["hold_val"]
    c, m, v = RR.win_metrics(eq, s["first"], s["end"], CTX["w0"], CTX["w1"])
    w0, w1 = CTX["w0"], CTX["w1"]
    cash = 1 - hv[w0:w1 + 1] / eq[w0:w1 + 1]
    return {"N": N, "r": r, "seed": 1000 + r, "cagr": c, "mdd": m, "vol": v, "first": int(s["first"]), "end": int(s["end"]),
            "trades": int(s["trades"]), "eq_sha": hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16],
            "cash_mean": float(cash.mean()), "cash_med": float(np.median(cash)), "tot": float(eq[w1] / eq[w0])}


if __name__ == "__main__":
    with Pool(3) as p:
        d = pd.DataFrame(p.map(one, [(N, r) for N in NS for r in range(200)], chunksize=8))
    ref = pd.read_csv("backtest/resultsN17/regime_t1/seeds.csv", dtype={"eq_sha": str}, float_precision="round_trip")
    gate = {}
    for N, cell in ((10, 1), (20, 17)):
        a = d[d["N"] == N].sort_values("r").reset_index(drop=True)
        b = ref[(ref["stage"] == "t1") & (ref["cell"] == cell)].sort_values("r").reset_index(drop=True)
        bad = {k: int(sum(repr(float(x)) != repr(float(y)) for x, y in zip(a[k], b[k]))) for k in ("cagr", "mdd", "vol")}
        bad.update({k: int((a[k].astype(str) != b[k].astype(str)).sum()) for k in ("eq_sha", "trades", "first", "end")})
        gate[f"N{N}＝regime_t1 #{cell}"] = bad
    ok = all(v == 0 for g in gate.values() for v in g.values())
    print("閘", gate, ok)
    if not ok:
        raise SystemExit("⛔ 閘不過")
    d.to_csv(f"{OUT}/seeds.csv", index=False)
    bw = RR.bench_row(CTX["cal"], RR.load_bench(CTX["cal"]), CTX["w0"], CTX["w1"] + 1)
    b_c, b_m = bw["cagr"], bw["mdd"]
    assert repr(b_c) == repr(RR.ANCHOR[0])
    base = d[d["N"] == 10].set_index("r")
    rows = []
    for N in NS:
        g = d[d["N"] == N].set_index("r")
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio, extra = RT.label(c, m, b_c, b_m)
        rows.append({"檔數N": N, "年化中位": c, "回落中位": m, "比值": ratio, "標籤（對0050）": lab, "深淺註": extra,
                     "年化p10": float(g["cagr"].quantile(.1)), "年化p90": float(g["cagr"].quantile(.9)),
                     "回落p10": float(g["mdd"].quantile(.1)), "回落p90": float(g["mdd"].quantile(.9)),
                     "年化波動中位": float(g["vol"].median()), "交易筆數中位": float(g["trades"].median()),
                     "現金比例均值中位": float(g["cash_mean"].median()),
                     "100萬放滿主窗中位（萬；eq[w1]÷eq[w0]）": float(g["tot"].median() * 100),
                     "同顆種子_兩項皆好於N10": int(((g["cagr"] > base["cagr"]) & (g["mdd"] > base["mdd"])).sum()),
                     "同顆種子_兩項皆差於N10": int(((g["cagr"] < base["cagr"]) & (g["mdd"] < base["mdd"])).sum())})
    C = pd.DataFrame(rows); C.to_csv(f"{OUT}/cells.csv", index=False, encoding="utf-8-sig")
    json.dump({"gate": gate, "bench": bw}, open(f"{OUT}/meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(C.to_string(index=False))

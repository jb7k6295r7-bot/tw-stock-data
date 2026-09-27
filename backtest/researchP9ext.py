# -*- coding: utf-8 -*-
"""P9run 12 格 K5 截斷補跑（裁定 seq260 §二；背景 backtest/audit_trunc/REPORT.md，commit 853e9e9fc1）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchP9ext [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python -m backtest.researchP9ext_check

⭐ 原件：researchP9run.py（commit 8694b4f173）12 格＋基準臂＋參照臂；攤平停利 B 乙一 By（researchAvg.py，commit cd2ee7c513）附一列
⭐ 與原件一字不動的部分（直接 import researchP9run 的 engine_kw／measure／label／shuffle_state／常數）：
   快照 rerun17.use_snapshot、價格 rerun17.load_prices("branch")、0050 rerun17.load_bench、H120、N8、種子 99000＋r（200 顆）、
   COST 0.585%、pick None、cash zero、tradable／delist 關、訊號只留 entry_pos ∈ [w0, w1]、ⓑ 旗標 p9_flags.build_flags(panel_ext)、
   假訊號臂（ⓒ～ⓗ：線上／線下段打亂，30 次 × r ∈ [0,50)，rng 20260925＋j）、判準 researchP9run.label（seq141）
⭐ 唯一改動 ＝ AFCext V3 的補法（三步，分版報）：
   V0 閘：panel_ext 截到量測日 ≤ 2026-03-02、stop_force 關 ⇒ 全部臂（14 臂 × 200 顆、By 200 顆、假訊號 9,000 顆）＝ 原件逐種子檔
   V1 補面板：訊號改由 panel_ext 全段建（量測日到 2026-08-03；build_sig_gate_b 原函式 ⇒ 出場超過資料尾的列仍被丟）
   V2 補面板＋停止交易強制出場：開（research11.stop_force_days(valid_from_data, 主窗尾)）
   V3 補面板＋尾端截斷補回（researchYear1M.sig12 / pad_px：出場設墊檔日、報酬照最後收盤；T1 讀法）＋stop_force ⇒ 【主版】
   ⚠ 墊檔日：closes 延用最後收盤、opens NaN；0050 延用最後收盤（regime_below 用延伸序列）；ⓑ 旗標墊 False（＝ researchYear1M.setup 同式）
By 參數（researchAvg.ENGINE_KW_B["By"]，cd2ee7c513 起未改）：add_rule kind loss x 0.10 size 0.5 short skip
輸出 backtest/resultsP9ext/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import researchP9run as P9R
from . import rerun17 as RR
from . import research11 as R
from . import p9_flags as F
from . import researchYear1M as Y

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsP9ext")
CUT = pd.Timestamp("2026-03-02")
SF_TAG = "停止交易強制出場：開"
BY_KW = {"add_rule": {"kind": "loss", "x": 0.10, "size": 0.5, "short": "skip"}}
KEYS = P9R.KEYS + ["By"]
NAME = dict(P9R.NAME); NAME["By"] = "攤平停利 B 乙一 By（2-B ⓓ 個股收盤 ≤ 進場 −10% ⇒ 加 0.5 slot）"
JUDGED = P9R.JUDGED + ["By"]
VERS = [("V0", "V0 閘（截到 2026-03-02、stop_force 關）"), ("V1", "V1 補面板"), ("V2", "V2 補面板＋stop_force"),
        ("V3", "V3 補面板＋尾端截斷補回＋stop_force（主版）")]
# audit_trunc/REPORT.md 與裁定 seq260 §二 的事前估計（⛔ 看結果前抄入）
PRIOR = {"Cc": "大概翻合格", "Bb": "大概翻合格", "Ba": "大概翻合格", "A2": "邊緣", "Bc": "邊緣", "Ce": "邊緣", "Cf": "邊緣", "Cg": "邊緣",
         "A3": "邊緣", "Ca": "邊緣", "Cd": "邊緣", "Ch": "翻不了（差 3.3 點）", "By": "低（到合格要 +3.25 點）"}
G = P9R._G


def sim(kw, seed, audit=None):
    ex = {"stop_force": G["SF"]} if G.get("SF") is not None else {}
    return R.simulate_mtm(G["sig"], P9R.RULE, P9R.N_MAIN, np.random.default_rng(seed), G["closes"], G["opens"], G["ncal"],
                          return_equity=True, report_maxw=True, audit=audit, **kw, **ex)


def _arm(args):
    key, r = args
    kw = BY_KW if key == "By" else P9R.engine_kw(key)
    o = sim(kw, P9R.SEED0 + r)
    return {"ver": G["ver"], "arm": key, "r": r, "seed": P9R.SEED0 + r, **P9R.measure(o)}


def _fake(args):
    key, j, r = args
    o = sim(P9R.engine_kw(key, below=G["fake"][(P9R.MA_OF[key], j)]), P9R.SEED0 + r)
    c, m, v = RR.win_metrics(o["equity"], o["first"], o["end"], G["w0"], G["w1"])
    return {"ver": G["ver"], "cell": key, "j": j, "r": r, "seed": P9R.SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": float(v)}


def fake_seqs(below):
    return {(n, j): P9R.shuffle_state(below[n], G["w0"] - 1, G["w1"], np.random.default_rng(P9R.FAKE_SEED0 + j))
            for n in (60, 20, 10) for j in range(1, P9R.N_FAKE + 1)}


def win(sig):
    e = sig["entry_pos"].to_numpy()
    return sig[(e >= G["w0"]) & (e <= G["w1"])].reset_index(drop=True)


def cell_rows(A):
    out = {}
    for k in KEYS:
        g = A[A["arm"] == k]
        c, m, v = float(g["cagr"].median()), float(g["mdd"].median()), float(g["vol"].median())
        lab, ratio, extra = P9R.label(c, m)
        out[k] = {"cagr": c, "mdd": m, "ratio": ratio, "vol": v, "label": lab, "note": extra,
                  "sf_n_med": float(g["x_stop_force_n"].median()) if "x_stop_force_n" in g and g["x_stop_force_n"].notna().any() else None,
                  "trades_med": float(g["trades"].median())}
    return out


def fake_rows(FK, A):
    out = {}
    for k in P9R.FAKE_CELLS:
        labs = []
        for j in range(1, P9R.N_FAKE + 1):
            g = FK[(FK["cell"] == k) & (FK["j"] == j)]
            c, m = float(g["cagr"].median()), float(g["mdd"].median())
            labs.append((c, m, P9R.label(c, m)[0]))
        g0 = A[(A["arm"] == k) & (A["r"] < P9R.FAKE_REPS)]
        c0, m0 = float(g0["cagr"].median()), float(g0["mdd"].median())
        out[k] = {"x_Q": sum(l == "合格" for *_, l in labs), "x_R": sum(l == "另列" for *_, l in labs), "n": P9R.N_FAKE,
                  "fake_cagr_med": float(np.median([c for c, _, _ in labs])), "real50_cagr": c0, "real50_label": P9R.label(c0, m0)[0],
                  "real_cagr_rank": int(sum(c <= c0 for c, _, _ in labs))}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8")
    T0 = time.time()

    def log(x):
        x = f"[{time.time() - T0:6.0f}s] {x}"
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    log(f"===== researchP9ext {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜procs {a.procs}｜{SF_TAG}（V2、V3）=====")
    if abs(R.COST - 0.00585) > 1e-15:
        raise SystemExit(f"⛔ COST {R.COST}")
    S = {"原件": {"P9run": "researchP9run.py 8694b4f173", "By": "researchAvg.py cd2ee7c513"}, "閘": {}, "標註": [SF_TAG + "（V2、V3）"]}
    S["設定_P9run原樣"] = P9R.setup(log)                   # ⭐ 原件 setup：快照、價格、0050、窗、years、periods、below、原件訊號（AFC 面板）
    from . import data as D
    from . import p4_features as P4F
    from . import researchp7 as P7
    cal, ncal, w0, w1, bench, uni = G["cal"], G["ncal"], G["w0"], G["w1"], G["bench"], G["uni"]
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    ok1 = repr(bw["cagr"]) == repr(P9R.ANCHOR[0]) and repr(bw["mdd"]) == repr(P9R.ANCHOR[1])
    S["閘"]["0050錨"] = ok1
    if not ok1:
        raise SystemExit("⛔ 0050 錨不過")
    G.update(c50=bw["cagr"], m50=bw["mdd"], v50=bw["vol"])
    S["0050"] = {"主窗": [bw["cagr"], bw["mdd"]], "比值": bw["cagr"] / abs(bw["mdd"])}
    h = hashlib.sha256(open(P9R.PANEL_EXT, "rb").read()).hexdigest()
    if h != P9R.PANEL_EXT_SHA:
        raise SystemExit(f"⛔ panel_ext sha {h}")
    pext = P4F.read_panel(P9R.PANEL_EXT)
    pcut = pext[pext["measure_date"] <= CUT].reset_index(drop=True)
    sig_orig = G["sig"].copy()
    closes0, opens0 = G["closes"], G["opens"]
    miss = sorted(set(pext["stock_id"]) - set(closes0))
    if miss:                                               # panel_ext 比 AFC 面板多的股 ⇒ 補讀價格（同一支 load_prices）
        c_, o_ = RR.load_prices(miss, cal, uni, "branch"); closes0.update(c_); opens0.update(o_)
    valid = R.valid_from_data(set(closes0), uni, cal)
    SF = R.stop_force_days(valid, w1)
    S["停止交易日（主窗尾前停止）"] = len(SF)
    below0 = G["below"]
    closesP, opensP = Y.pad_px(closes0, opens0)
    benchP = np.r_[bench, bench[-1]]
    belowP = {n: R.regime_below(benchP, n) for n in (60, 20, 10)}
    assert all(np.array_equal(belowP[n][:ncal], below0[n]) for n in (60, 20, 10)), "⛔ 延伸 0050 改到了原日曆的 below"
    orig_A = pd.read_csv(os.path.join(HERE, "resultsP9run", "seeds_arms.csv"), float_precision="round_trip")
    orig_FK = pd.read_csv(os.path.join(HERE, "resultsP9run", "seeds_fake.csv"), float_precision="round_trip")
    orig_By = pd.read_csv(os.path.join(HERE, "resultsAvg", "B_seeds_arms.csv"), float_precision="round_trip")
    orig_By = orig_By[orig_By["arm"] == "By"]
    ALL_A, ALL_F = [], []
    for vk, vname in VERS:
        tt = time.time()
        if vk == "V0":
            sig = win(P7.build_sig_gate_b(pcut, cal, closes0, opens0, start="2017-01-01", signal="B"))
            S["閘"]["V0 訊號＝原件訊號（AFC 面板）"] = bool(sig.equals(sig_orig))
        elif vk in ("V1", "V2"):
            sig = win(P7.build_sig_gate_b(pext, cal, closes0, opens0, start="2017-01-01", signal="B"))
        else:
            _, sT, infoT = Y.sig12(pext, cal, closes0, opens0, log, "panel_ext")
            S["T1 尾端截斷補回"] = infoT
            sig = win(sT)
        t1 = vk == "V3"
        fl = F.build_flags(pext, cal, sids=set(sig["sid"]))
        if t1:
            fl = {s: np.r_[v, False] for s, v in fl.items()}
        G.update(ver=vk, sig=sig, flags=fl, closes=closesP if t1 else closes0, opens=opensP if t1 else opens0, ncal=ncal + 1 if t1 else ncal,
                 below=belowP if t1 else below0, SF=SF if vk in ("V2", "V3") else None)
        do_fake = vk in ("V0", "V3")
        if do_fake:
            G["fake"] = fake_seqs(G["below"])
        info = {"訊號筆": len(sig), "檔": int(sig["sid"].nunique()), "最後進場日": str(cal[int(sig["entry_pos"].max())].date()),
                "墊檔日出場筆": int((sig["xpos_H120"] >= ncal).sum())}
        with Pool(a.procs) as pool:
            A = pd.DataFrame(pool.map(_arm, [(k, r) for k in KEYS for r in range(P9R.REPS)], chunksize=10))
            FK = pd.DataFrame(pool.map(_fake, [(k, j, r) for k in P9R.FAKE_CELLS for j in range(1, P9R.N_FAKE + 1) for r in range(P9R.FAKE_REPS)],
                                       chunksize=25)) if do_fake else None
        ALL_A.append(A)
        if FK is not None:
            ALL_F.append(FK)
        S[vname] = {"訊號": info, "格": cell_rows(A)}
        if FK is not None:
            S[vname]["假訊號臂"] = fake_rows(FK, A)
        log(f"[{vname}] {json.dumps(info, ensure_ascii=False)}｜{len(A):,}＋{0 if FK is None else len(FK):,} 次引擎｜{time.time() - tt:.0f}s")
        if vk == "V0":
            x = A[A["arm"] != "By"].set_index(["arm", "r"]).sort_index()
            y = orig_A.set_index(["arm", "r"]).sort_index().loc[x.index]
            nd = {k: int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(x[k], y[k]))) for k in ("cagr", "mdd", "vol")}
            sha_same = int((x["eq_sha"] == y["eq_sha"]).sum())
            dmax = float(max((x[k] - y[k]).abs().max() for k in ("cagr", "mdd", "vol")))
            bx = A[A["arm"] == "By"].set_index("r").sort_index(); by_ = orig_By.set_index("r").sort_index().loc[bx.index]
            nd_by = int(sum(repr(float(p)) != repr(float(q)) or repr(float(p2)) != repr(float(q2))
                            for p, q, p2, q2 in zip(bx["cagr"], by_["cagr"], bx["mdd"], by_["mdd"])))
            by_sha = int((bx["eq_sha"] == by_["eq_sha"]).sum())
            fx = FK.set_index(["cell", "j", "r"]).sort_index(); fy = orig_FK.set_index(["cell", "j", "r"]).sort_index().loc[fx.index]
            nd_fk = int(sum(repr(float(p)) != repr(float(q)) or repr(float(p2)) != repr(float(q2))
                            for p, q, p2, q2 in zip(fx["cagr"], fy["cagr"], fx["mdd"], fy["mdd"])))
            dmax_all = max(dmax, float((bx["cagr"] - by_["cagr"]).abs().max()), float((bx["mdd"] - by_["mdd"]).abs().max()),
                           float((fx["cagr"] - fy["cagr"]).abs().max()), float((fx["mdd"] - fy["mdd"]).abs().max()))
            oc = pd.read_csv(os.path.join(HERE, "resultsP9run", "cells.csv"))
            lab_same = all(S[vname]["格"][k]["label"] == (oc.set_index("arm").at[k, "label_desc"]) for k in P9R.KEYS)
            g0 = {"14 臂 × 200 顆 不逐位元（年化／回落／波動）": nd, "equity sha 相同": f"{sha_same}／{len(x)}",
                  "By 200 顆 不逐位元": nd_by, "By equity sha 相同": f"{by_sha}／{len(bx)}", "假訊號 9,000 顆 不逐位元": nd_fk,
                  "最大差": dmax_all, "標籤＝原件 cells.csv": lab_same, "訊號＝原件": S["閘"]["V0 訊號＝原件訊號（AFC 面板）"]}
            ok0 = S["閘"]["V0 訊號＝原件訊號（AFC 面板）"] and lab_same and dmax_all <= 2.3e-16
            g0["過"] = bool(ok0)
            g0["說明"] = ("逐位元 ⇒ 過" if (sum(nd.values()) + nd_by + nd_fk == 0) else
                        "有末位浮點差（≤ 2.3e−16，照 AFCext 慣例）：訊號逐列相同、標籤相同 ⇒ 差不是面板或訊號造成，見 REPORT §閘")
            S["閘"]["V0＝原件"] = g0
            log(f"[閘 V0] {json.dumps(g0, ensure_ascii=False, default=str)}")
            if not ok0:
                pd.concat(ALL_A).to_csv(os.path.join(OUT, "seeds_arms.csv.gz"), index=False, float_format="%.17g")
                json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
                raise SystemExit("⛔ 閘不過：V0 不能重現原件")
    pd.concat(ALL_A).to_csv(os.path.join(OUT, "seeds_arms.csv.gz"), index=False, float_format="%.17g")
    pd.concat(ALL_F).to_csv(os.path.join(OUT, "seeds_fake.csv.gz"), index=False, float_format="%.17g")
    sT = G["sig"]; sT.to_csv(os.path.join(OUT, "sig_v3.csv.gz"), index=False, float_format="%.17g")
    # 翻不翻表：原件（P9run cells.csv／resultsAvg B_cells.csv）vs V3
    oc = pd.read_csv(os.path.join(HERE, "resultsP9run", "cells.csv")).set_index("arm")
    ob = pd.read_csv(os.path.join(HERE, "resultsAvg", "B_cells.csv")).set_index("arm")
    v3 = S[VERS[3][1]]["格"]; v1 = S[VERS[1][1]]["格"]; v2 = S[VERS[2][1]]["格"]
    rows = []
    for k in KEYS:
        src = ob if k == "By" else oc
        c0, m0 = float(src.at[k, "cagr"]), float(src.at[k, "mdd"])
        l0 = P9R.label(c0, m0)[0]
        x = v3[k]
        rows.append({"arm": k, "格": NAME[k], "判定": k in JUDGED, "原件_年化": c0, "原件_回落": m0, "原件_比值": c0 / abs(m0), "原件_標籤": l0,
                     "V1_年化": v1[k]["cagr"], "V1_標籤": v1[k]["label"], "V2_年化": v2[k]["cagr"], "V2_標籤": v2[k]["label"],
                     "V3_年化": x["cagr"], "V3_回落": x["mdd"], "V3_比值": x["ratio"], "V3_標籤": x["label"],
                     "差_年化點": (x["cagr"] - c0) * 100, "差_回落點": (x["mdd"] - m0) * 100, "差_比值": x["ratio"] - c0 / abs(m0),
                     "翻": (f"{l0}→{x['label']}" if l0 != x["label"] else "不翻"), "事前估計": PRIOR.get(k, "")})
    TB = pd.DataFrame(rows)
    TB.to_csv(os.path.join(OUT, "flip_table.csv"), index=False, float_format="%.17g")
    S["翻不翻"] = {r["arm"]: r["翻"] for r in rows if r["判定"]}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[翻不翻] {json.dumps(S['翻不翻'], ensure_ascii=False)}")
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

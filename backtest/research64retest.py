# -*- coding: utf-8 -*-
"""六四 v1 重測（裁定 seq257 §三 順 2；稽核 seq3 §七之三）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.research64retest [--dtb3 <路徑>]
    獨立查核：~/tw-p16/.venv/bin/python backtest/research64retest_check.py

六四 v1 ＝ 0050 60%＋00685L 40%、每年 1 月第一個交易日調回、ETF 成本 0.385%（窗首建倉與每次調回都扣：researchMix70.sim 同一支）
⛔ 固定配比 ⇒ 沒有挑選、只判定；判準 ＝ 使用者判準（年化 ＞ 0050 同段 且 年化÷|MDD| ≥ 0050 ⇒ 合格；只過第一條 ⇒ 另列）
═══ 項目（稽核 §七之三）═══
 ① 同窗判定：窗 A ＝ 2018-01-15（researchLev2 R1「上市滿 200 個交易日」起點、researchMix70 W18）～2026-08-24；描述另跑 A0 ＝ 00685L 上市首日 2017-03-30 起，用【真的 00685L】；窗 B ＝ 確認段 2022-01-03～2026-08-24；
    兩窗都對 0050 同窗（還原收盤、窗首為基、不含成本：researchLev2.bench_perf 同式）；另報 00631L 代 00685L 的差（描述）
 ② 隨機配比臂：00685L 比例 x ∈ {0, 10, …, 100}%、調回月份 m ∈ {1…12} 各均勻抽、1,000 次（rng default_rng(20260928)）
    ⇒ 六四在年化、比值分佈裡的百分位（隨機 ≤ 六四 的比例）、隨機合格的比例；⭐ 實作：132 種組合各算一次、再照抽到的組合取值（與逐次重算相同）
 ③ 2008 合成＋資金成本：窗 2006-09-12～2014-12-31（researchMix70 STRESS，同 −67.80% 那一列）與 2008-01-02～2009-03-31；
    合成槓桿 ETF 收盤 L_c[t] ＝ L_c[t−1]×(1＋2 r_t − 經理費／245 − 年利率_t／245 ×（2−1））、開盤 L_o[t] ＝ L_c[t−1]×(1＋2×隔夜報酬)
    （researchMix70.syn 同式，只多扣資金成本）；00685L 合成 ＝ 0050×2 扣 0.3%／年（⚠ 資料庫沒有加權指數早年序列 ⇒ 逐字：「00685L 用 0050×2 合成」）；
    00631L 合成扣 1.0%／年；利率 ＝ FRED DTB3（美國 3 個月國庫券，t−1 以前最近一筆、年化 %）；⚠ 逐字：「台灣短期利率序列資料庫沒有現成 ⇒ 用美國 DTB3 代，另報固定 1%／2%／3%」
    ⇒ 最大回落、100 萬在高點谷底剩多少、是否超過使用者上限 −70%
 ④ 1990 起加權指數合成（1990 崩盤、2000～2002 長空頭）：資料庫 main（b6cce05ba3）與早年 3edc0e2206 都沒有 1990 起的加權指數
    （data/history/market_index.csv 自 2026-09-01 起；早年只有 2004 起個股日線）⇒ 【等資料】
 ⑤ 並列同窗：一直抱 0050、一直抱 00685L／00631L、PREREG低頻擇時三格（甲 D200_a、乙 s40_L60_a、丙 B_x20_R2_M；正2 用 00631L，researchLowFreq 同式）；
    ③ 的壓力窗也並列（低頻擇時用合成正2＋同一資金成本）
閘：六四 窗 A 年化／回落 ＝ researchMix70 mix3_grid 60／0／40 列（逐位元）；③ 不扣資金成本的六四壓力窗回落 ＝ 同列 −67.80%（1e−9）；0050 主窗錨
輸出 backtest/results64retest/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd

from . import researchLev2 as L2
from . import researchMix70 as MX
from . import researchLowFreq as LF
from . import rerun17 as RR
from . import data as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results64retest")
DTB3_DEF = "/mnt/c/SynologyDrive/跨線信箱/DTB3.csv"
WA = ("2018-01-15", "2026-08-24"); WB = ("2022-01-03", "2026-08-24")
STRESS = MX.STRESS; P08 = MX.P08
LIMIT = -0.70
SEED = 20260928; NREP = 1000
W64 = (0.6, 0.4)
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


def bench(C50, i0, i1):
    seg = C50[i0:i1 + 1]; c, m = L2.R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg))
    return float(c), float(m)


def perf_row(eq, cal, i0, c50, m50, acts=None, crel=0.0):
    st = MX.stats(eq, cal, i0, acts, crel)
    c, m = st["年化"], st["最大回落"]
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p); dd = (p - pk) / pk; it = int(np.argmin(dd)); ip = int(np.argmax(p[:it + 1]))
    back = np.flatnonzero(p[it:] >= p[ip])
    return {**st, "比值": L2.ratio(c, m), "判準": L2.label(c, m, c50, m50), "100萬在高點_谷底剩（萬）": float((1 + m) * 100),
            "高點日": cal[i0 + ip - 1] if ip > 0 else "起點", "回到高點交易日數": int(back[0]) if len(back) else "窗內未回本"}


def load_rate(path, cal):
    d = pd.read_csv(path)
    d.columns = ["date", "v"]
    d["v"] = pd.to_numeric(d["v"], errors="coerce"); d = d.dropna()
    s = d.set_index("date")["v"]
    out = np.full(len(cal), np.nan); j = -1; ds = list(s.index); vs = s.to_numpy(float); k = 0
    for t, day in enumerate(cal):                      # t 日用 t−1 以前（< day）最近一筆
        while k < len(ds) and ds[k] < day:
            j = k; k += 1
        out[t] = vs[j] / 100.0 if j >= 0 else np.nan
    return out, hashlib.sha256(open(path, "rb").read()).hexdigest()[:16], [str(d["date"].iloc[0]), str(d["date"].iloc[-1])]


def synth(o50, c50, f0, fee, rate):
    """rate：日曆長度（年化小數）或純量；回 (Lo, Lc)。"""
    N = len(c50); Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[f0] = 1.0
    r = np.broadcast_to(np.asarray(rate, float), (N,)) if np.ndim(rate) == 0 else rate
    for t in range(f0 + 1, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o50[t] / c50[t - 1] - 1)) if np.isfinite(o50[t]) else np.nan
        rr = r[t] if np.isfinite(r[t]) else 0.0
        Lc[t] = Lc[t - 1] * (1 + 2 * (c50[t] / c50[t - 1] - 1) - fee / 245 - rr / 245 * (2 - 1))
    return Lo, Lc


def main():
    global LOGF
    ap = argparse.ArgumentParser(); ap.add_argument("--dtb3", default=DTB3_DEF); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log"); open(LOGF, "w").close()
    log(f"===== research64retest {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜裁定 seq257 §三 順 2＋稽核 seq3 §七之三 =====")
    X = MX.load(); cal, pos = X["cal"], X["pos"]; N = len(cal)
    O, C = X["O"], X["C"]
    a0, a1 = pos[WA[0]], pos[WA[1]]; b0, b1 = pos[WB[0]], pos[WB[1]]; s0, s1 = pos[STRESS[0]], pos[STRESS[1]]; q0, q1 = pos[P08[0]], pos[P08[1]]
    S = {"定義": "六四 v1 ＝ 0050 60%＋00685L 40%、每年 1 月第一個交易日調回、ETF 成本 0.385%（建倉與調回皆扣）", "挑選": "無（固定配比；只判定）"}
    # 閘
    calm = D.load_calendar(); w0, w1 = RR.win_bounds(calm)
    bw = RR.bench_row(calm, RR.load_bench(calm), w0, w1 + 1)
    g_anchor = abs(bw["cagr"] - RR.ANCHOR[0]) < 1e-12 and abs(bw["mdd"] - RR.ANCHOR[1]) < 1e-12
    raw685 = pd.read_csv(os.path.join(D.DATA, "stocks", "00685L.csv"), dtype={"date": str}, usecols=["date", "close"])
    first685_raw = str(raw685["date"].min())
    # ① 同窗判定
    R1 = {}
    z0 = pos["2017-03-30"]
    WINS1 = (("A 2018-01-15～2026-08-24", (a0, a1)), ("B 確認段 2022-01-03～2026-08-24", (b0, b1)), ("A0 2017-03-30～2026-08-24（00685L 上市首日起；描述）", (z0, a1)))
    for wn, (i0, i1) in WINS1:
        c50, m50 = bench(C["0050"], i0, i1)
        rows = {"0050（判準，還原、不含成本）": {"年化": c50, "最大回落": m50, "比值": L2.ratio(c50, m50)}}
        for nm, assets, w in (("六四 v1（真 00685L）", ("0050", "00685L"), W64), ("六四（00631L 代，描述）", ("0050", "00631L"), W64),
                              ("一直抱 0050（含建倉成本）", ("0050",), (1.0,)), ("一直抱 00685L", ("00685L",), (1.0,)), ("一直抱 00631L", ("00631L",), (1.0,))):
            eq, acts, crel, dl = MX.sim(assets, w, i0, i1, O, C, cal, "Y", 1)
            rows[nm] = {**perf_row(eq, cal, i0, c50, m50, acts, crel), "R8延後": dl}
        R1[wn] = rows
    ga = R1["A 2018-01-15～2026-08-24"]["六四 v1（真 00685L）"]
    g_mix = repr(ga["年化"]) == repr(0.3200982606577789) and repr(ga["最大回落"]) == repr(-0.39775198512106774)
    log(f"[閘] 0050 錨 {g_anchor}｜六四 窗A ＝ researchMix70 60／0／40（逐位元）{g_mix}｜00685L 第一筆 {first685_raw}")
    # ⑤ 低頻擇時三格（同窗、真 00631L）
    G = LF.load(); I = LF.indicators(G); SEGS, WS, g0, E0 = LF.build(G, I)
    assert list(G["cal"]) == list(cal)
    PK = {"甲": ("甲", "D200_a"), "乙": ("乙", "s40_L60_a"), "丙": ("丙", "B_x20_R2_M")}
    for wn, (i0, i1) in WINS1:
        c50, m50 = R1[wn]["0050（判準，還原、不含成本）"]["年化"], R1[wn]["0050（判準，還原、不含成本）"]["最大回落"]
        for f, key in PK.values():
            r = LF.run_seg(G, WS[(f, key)][0], i0, i1, "00631L")
            R1[wn][f"低頻擇時 {f} {key}"] = perf_row(r["eq"], cal, i0, c50, m50)
    S["① 同窗判定＋⑤ 並列"] = R1
    for wn, rows in R1.items():
        log(f"[① {wn}] " + "｜".join(f"{k} {v['年化']:.2%}／{v['最大回落']:.2%}／{v.get('判準', '')}" for k, v in rows.items()))
    # ② 隨機配比臂
    R2 = {}
    rng = np.random.default_rng(SEED)
    xs = rng.integers(0, 11, size=NREP); ms = rng.integers(1, 13, size=NREP)
    for wn, (i0, i1) in (("A 2018-01-15～2026-08-24", (a0, a1)), ("B 確認段 2022-01-03～2026-08-24", (b0, b1))):
        c50, m50 = bench(C["0050"], i0, i1)
        grid = {}
        for x in range(11):
            for m in range(1, 13):
                eq, _, _, _ = MX.sim(("0050", "00685L"), (1 - x / 10, x / 10), i0, i1, O, C, cal, "Y", m)
                c, mm = L2.perf(eq); grid[(x, m)] = (c, mm, L2.ratio(c, mm), L2.label(c, mm, c50, m50))
        draws = [grid[(int(x), int(m))] for x, m in zip(xs, ms)]
        cg = np.array([d[0] for d in draws]); rg = np.array([d[2] for d in draws]); lab = [d[3] for d in draws]
        me = R1[wn]["六四 v1（真 00685L）"]
        R2[wn] = {"六四 年化百分位（隨機 ≤ 六四）": float(np.mean(cg <= me["年化"])), "六四 比值百分位": float(np.mean(rg <= me["比值"])),
                  "隨機合格比例": float(np.mean([l_ == "合格" for l_ in lab])), "隨機另列比例": float(np.mean([l_ == "另列" for l_ in lab])),
                  "隨機年化中位": float(np.median(cg)), "隨機年化 p10～p90": [float(np.percentile(cg, 10)), float(np.percentile(cg, 90))],
                  "132 組合（不抽樣）合格比例": float(np.mean([v[3] == "合格" for v in grid.values()])),
                  "六四同配比 12 個調回月份 年化範圍": [float(min(grid[(4, m)][0] for m in range(1, 13))), float(max(grid[(4, m)][0] for m in range(1, 13)))],
                  "六四（1 月）是否 ＝ grid[(4,1)]": bool(repr(grid[(4, 1)][0]) == repr(me["年化"]))}
        pd.DataFrame([{"00685L%": x * 10, "調回月": m, "年化": v[0], "回落": v[1], "比值": v[2], "判準": v[3]} for (x, m), v in grid.items()]).to_csv(
            os.path.join(OUT, f"random_grid_{wn[0]}.csv"), index=False, encoding="utf-8")
    pd.DataFrame({"x（00685L 十分之幾）": xs, "月": ms}).to_csv(os.path.join(OUT, "random_draws.csv"), index=False)
    S["② 隨機配比臂"] = R2
    log(f"[②] {json.dumps(R2, ensure_ascii=False)}")
    # ③ 2008 合成＋資金成本
    rate, rsha, rrng = load_rate(a.dtb3, cal)
    f0 = int(np.flatnonzero(np.isfinite(C["0050"]))[0]); o50, c50s = O["0050"], C["0050"]
    VAR = {"不扣資金成本（researchMix70 原式）": 0.0, "DTB3（美國 3 個月國庫券，代）": rate, "固定 1%": 0.01, "固定 2%": 0.02, "固定 3%": 0.03}
    R3 = {}; rows3 = []
    for vn, rt in VAR.items():
        SO = dict(O); SC = dict(C)
        SO["00685L"], SC["00685L"] = synth(o50, c50s, f0, 0.003, rt)
        SO["00631L"], SC["00631L"] = synth(o50, c50s, f0, 0.010, rt)
        R3[vn] = {}
        for win, (i0, i1) in (("壓力窗 2006-09-12～2014-12-31", (s0, s1)), ("2008-01-02～2009-03-31", (q0, q1))):
            cb, mb = bench(C["0050"], i0, i1)
            res = {}
            for nm, assets, w in (("六四 v1（合成 00685L）", ("0050", "00685L"), W64), ("一直抱合成正2（00631L 式）", ("00631L",), (1.0,)),
                                  ("一直抱 0050", ("0050",), (1.0,))):
                eq, acts, crel, dl = MX.sim(assets, w, i0, i1, SO, SC, cal, "Y", 1)
                res[nm] = perf_row(eq, cal, i0, cb, mb, acts, crel); res[nm]["超過 −70%"] = bool(res[nm]["最大回落"] < LIMIT)
            G["O"]["SYN"], G["C"]["SYN"] = SO["00631L"], SC["00631L"]
            _, WSv, _, _ = LF.build(G, I)
            for f, key in PK.values():
                r = LF.run_seg(G, WSv[(f, key)][0], i0, i1, "SYN")
                res[f"低頻擇時 {f} {key}"] = perf_row(r["eq"], cal, i0, cb, mb); res[f"低頻擇時 {f} {key}"]["超過 −70%"] = bool(res[f"低頻擇時 {f} {key}"]["最大回落"] < LIMIT)
            R3[vn][win] = res
            for nm, v in res.items():
                rows3.append({"資金成本": vn, "窗": win, "對象": nm, **{k: v[k] for k in ("年化", "最大回落", "100萬在高點_谷底剩（萬）", "高點日", "谷底日", "判準")}, "超過−70%": v["超過 −70%"]})
    pd.DataFrame(rows3).to_csv(os.path.join(OUT, "stress.csv"), index=False, encoding="utf-8")
    g_st = abs(R3["不扣資金成本（researchMix70 原式）"]["壓力窗 2006-09-12～2014-12-31"]["六四 v1（合成 00685L）"]["最大回落"] - (-0.6779767203437201)) < 1e-9
    S["③ 2008 合成＋資金成本"] = R3
    S["③ 利率"] = {"DTB3 檔": a.dtb3, "sha256[:16]": rsha, "期間": rrng, "壓力窗平均年利率": float(np.nanmean(rate[s0:s1 + 1])),
                  "標註": "台灣短期利率序列資料庫沒有現成 ⇒ 用美國 DTB3 代，另報固定 1%／2%／3%；00685L 用 0050×2 合成（資料庫沒有加權指數早年序列）"}
    log(f"[閘] 不扣資金成本的六四壓力窗回落 ＝ researchMix70 −67.80%：{g_st}")
    for vn, v in R3.items():
        x = v["壓力窗 2006-09-12～2014-12-31"]["六四 v1（合成 00685L）"]
        log(f"[③ {vn}] 六四 壓力窗 {x['年化']:.2%}／{x['最大回落']:.2%}（剩 {x['100萬在高點_谷底剩（萬）']:.1f} 萬、超過 −70% {x['超過 −70%']}）")
    # ④
    S["④ 1990 起加權指數合成"] = {"狀態": "等資料", "查過": ["tw-stock-data main b6cce05ba3：data/history/market_index.csv 自 2026-09-01 起（10 列）、data/latest 同",
                                                   "早年 3edc0e2206：data/early 只有 daily（個股 2004 起）、exright、inst、instamt、marginmkt、per、otcper、reduce、revenue；沒有指數",
                                                   "data/extra 只有 0050 2012～2014"],
                                 "要什麼": "加權指數（TAIEX）日收盤 1990-01 起（含 1990 崩盤、2000～2002）；有報酬指數更好"}
    S["閘"] = {"0050主窗錨": g_anchor, "六四窗A＝Mix70 逐位元": g_mix, "六四壓力窗不扣資金成本＝Mix70 −67.80%": g_st, "00685L 第一筆": first685_raw}
    if not (g_anchor and g_mix and g_st):
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        raise SystemExit("⛔ 閘不過")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("[完]")


if __name__ == "__main__":
    main()

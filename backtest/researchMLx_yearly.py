# -*- coding: utf-8 -*-
"""MLx 挑中格 A_GB_季_N20 的逐年描述表（裁定 seq267；使用者問「0050 也不是每年都強，碰到弱的時候可以補強報酬是否？」）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMLx_yearly
    查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMLx_yearly_check

⛔ 描述表：不判、N 不加、不重挑；只讀既有序列（MLx commit db0ebafae9 的 eq_pick.npy）＋重跑營量 v1（T1）一條路徑（閘門逐位元）。
序列：
  ML   ＝ backtest/resultsMLx/eq_pick.npy（挑中格 A_GB_季_N20；MX.sim_book 換股簿、無抽籤 ⇒ 單一路徑）
         閘：R13.window_stats 兩段 ＝ resultsMLx/summary.json 挑格 探索／確認 年化、回落（逐位元）
  0050 ＝ researchMLx 同一條：D.DATA＝H2.H2D、D.load_stock("0050") 收盤 ffill（MX.load_world 的 bench）；閘：兩段 ＝ summary.json 0050（逐位元）
  營量 v1（T1）＝ researchT1fix.build_ctx(True)（內含 rerun17.setup_and(t1=True)）＋ stop_force、種子 0（relvol 不抽籤）
         閘：cagr／mdd／vol／first／end／trades／eq_sha／sf_n ＝ resultsT1fix/seeds.csv.gz（c13｜t1｜r＝0）逐位元
口徑：
  逐年 ＝ 前一年最後交易日收盤 → 當年最後交易日收盤（2026 到確認段尾 2026-08-24）；ML 2019 起點 ＝ 起始資金 1（eq[2018-12-28]＝1，換股簿 2019-01-02 開盤才進場）
     ⭐ ML 2019-01-02 收盤權益也是 1 ⇒ 與 resultsMLx/summary.json「挑中格各年」（ML 2019 以 01-02 收盤起算）逐位元相同（閘）
  月報酬 ＝ 月底收盤對月底收盤（段首月以前一月底為起點；2026-08 到 08-24）；相關 ＝ Pearson
  段 ＝ researchMLx SEGS；段內年化／回落 ＝ R13.window_stats（段首日收盤為起點、245 日／年）
  0050 最大回落期間 ＝ 段內 0050 收盤（window_stats 同一段）的高點日 → 低點日；同期 ML、營量 ＝ 低點日收盤 ÷ 高點日收盤 − 1
  混合 ＝ 每段各自起算：段首日收盤 0050 與 ML 各 50%（不扣成本，同純 0050 基準不扣）；段內每年 1 月第一個交易日收盤再平衡回 50／50
     再平衡成本（本線讀法）：調整量 d ＝ |0050 部位 − 扣成本前總值 ÷ 2|；0050 側扣 d × 0.385%（ETF 來回）、ML 側扣 d × 0.585%（個股來回；ML 序列已內含自己的個股成本，
     這裡只對再平衡多買賣的那部分照比例扣）⇒ 兩側都照「來回」扣（保守）；扣完總值再切 50／50
輸出 backtest/resultsMLx/yearly/
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd

from backtest import researchMLlite as ML
from backtest import research13 as R13

D, H2 = ML.D, ML.H2
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "resultsMLx")
OUT = os.path.join(SRC, "yearly")
SEGS = {"探索": ("2019-01-01", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}   # ＝ researchMLx.SEGS
PICK = "A_GB_季_N20"
C_ETF, C_STK = 0.00385, 0.00585
YEARS = range(2019, 2027)


def _sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def ws(eq, a, b):
    c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
    return float(c), float(m)


def mix_path(e, b, a, z, cal, c_etf=C_ETF, c_stk=C_STK):
    """段 [a, z]：回 (混合權益 seg（長 z−a＋1）, 再平衡紀錄)。e＝ML 權益、b＝0050 收盤。"""
    E, M = 0.5, 0.5; out = [1.0]; reb = []
    for t in range(a + 1, z + 1):
        E *= b[t] / b[t - 1]; M *= e[t] / e[t - 1]
        if cal[t].year != cal[t - 1].year:                    # 1 月第一個交易日收盤
            T = E + M; d = abs(E - T / 2); cost = d * (c_etf + c_stk)
            reb.append({"日": str(cal[t].date()), "再平衡前 0050 比重": E / T, "調整量÷總值": d / T, "成本÷總值": cost / T})
            T -= cost; E = M = T / 2
        out.append(E + M)
    return np.array(out), reb


def main():
    os.makedirs(OUT, exist_ok=True)
    S = json.load(open(os.path.join(SRC, "summary.json"), encoding="utf-8"))
    assert S["挑格"]["格"] == PICK, S["挑格"]["格"]
    # ── ML、0050（MLx 同一個日曆）
    D.DATA = H2.H2D
    cal = D.load_calendar(); n = len(cal)
    eq = np.load(os.path.join(SRC, "eq_pick.npy"))
    assert len(eq) == n, (len(eq), n)
    bc = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    SEGP = {nm: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), side="right") - 1)) for nm, (x, y) in SEGS.items()}
    x0, z1 = SEGP["探索"][0], SEGP["確認"][1]
    assert str(cal[x0].date()) == "2019-01-02" and str(cal[z1].date()) == "2026-08-24", (cal[x0], cal[z1])
    assert eq[x0 - 1] == 1.0 and np.all(eq[:x0] == 1.0), "ML 權益在 2019-01-02 前不是 1"
    G = {}
    for nm, (a, z) in SEGP.items():
        c, m = ws(eq, a, z); c0, m0 = ws(bc, a, z)
        G[f"ML {nm} ＝ summary 挑格"] = (c == S["挑格"][nm]["年化"]) and (m == S["挑格"][nm]["回落"])
        G[f"0050 {nm} ＝ summary 0050"] = (c0 == S["0050"][nm]["年化"]) and (m0 == S["0050"][nm]["回落"])
    print("[閘 ML／0050]", G, flush=True)
    if not all(G.values()):
        raise SystemExit("⛔ ML／0050 序列與 summary.json 不逐位元相同 ⇒ 停")
    # ── 營量 v1（T1）
    from backtest import researchT1fix as RT
    from backtest import research11 as R
    from backtest import rerun17 as RR
    ctx = RT.build_ctx(True)
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), ctx["w1"])
    o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0 + 0), ctx["closes"], ctx["opens"], ctx["ncal"],
                       log=[], d_max=None, pick="relvol", queue_days=0, return_equity=True, stop_force=SF)
    e13 = np.asarray(o["equity"], float)
    c_, m_, v_ = RR.win_metrics(e13, o["first"], o["end"], ctx["w0"], ctx["w1"])
    mine = {"cagr": float(c_), "mdd": float(m_), "vol": float(v_), "first": int(o["first"]), "end": int(o["end"]),
            "trades": int(o["trades"]), "eq_sha": _sha(e13), "sf_n": int(o["x_stop_force_n"])}
    ref = pd.read_csv(os.path.join(HERE, "resultsT1fix", "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)].iloc[0]
    gt = {k: (repr(mine[k]) == repr(float(ref[k])) if k in ("cagr", "mdd", "vol") else (str(mine[k]) == str(ref[k]) if k == "eq_sha" else int(mine[k]) == int(ref[k])))
          for k in mine}
    print("[閘 T1]", gt, mine, flush=True)
    if not all(gt.values()):
        raise SystemExit("⛔ 營量 v1（T1）重跑與 resultsT1fix 不逐位元相同 ⇒ 停")
    c1 = ctx["cal"]
    ix = c1.get_indexer(cal[x0 - 1:z1 + 1])
    assert (ix >= 0).all() and (np.diff(ix) == 1).all(), "T1 日曆對不上 MLx 日曆"
    assert o["first"] <= ix[0] and o["end"] >= ix[-1], (o["first"], o["end"], ix[0], ix[-1])
    t1 = np.full(n, np.nan); t1[x0 - 1:z1 + 1] = e13[ix]
    D.DATA = H2.H2D
    # ── 日序列存檔（查核用）
    ser = pd.DataFrame({"date": [str(d.date()) for d in cal[x0 - 1:z1 + 1]], "ML": eq[x0 - 1:z1 + 1], "0050": bc[x0 - 1:z1 + 1], "營量v1_T1": t1[x0 - 1:z1 + 1]})
    ser.to_csv(os.path.join(OUT, "series.csv.gz"), index=False, float_format="%.17g")
    # ── ① 逐年
    yr = np.asarray(cal.year)
    rows = []
    for y in YEARS:
        idx = np.flatnonzero((yr == y) & (np.arange(n) <= z1) & (np.arange(n) >= x0))
        p, q = idx[0] - 1, idx[-1]
        r = {"年": f"{y}" + ("（YTD 到 08-24）" if y == 2026 else ""), "段": "探索（挑選段）" if y <= 2021 else "確認",
             "起": str(cal[p].date()), "迄": str(cal[q].date()),
             "ML": eq[q] / eq[p] - 1, "0050": bc[q] / bc[p] - 1, "營量v1_T1": t1[q] / t1[p] - 1}
        r["ML−0050"] = r["ML"] - r["0050"]
        r["0050 下跌"] = bool(r["0050"] < 0); r["0050 落後 ML"] = bool(r["0050"] < r["ML"])
        rows.append(r)
    SY = S["挑中格各年（本格／0050）"]
    G["各年 ＝ summary 挑中格各年"] = all(r["ML"] == SY[r["年"][:4]][0] and r["0050"] == SY[r["年"][:4]][1] for r in rows)
    Y = pd.DataFrame(rows); Y.to_csv(os.path.join(OUT, "yearly.csv"), index=False, float_format="%.17g")
    # ── ② 月相關、0050 最大回落期間
    me = [t for t in range(x0 - 1, z1 + 1) if t == z1 or cal[t + 1].month != cal[t].month]      # 月底（含 2018-12-28 起點、2026-08-24 段尾）
    COR, DD = {}, {}
    for nm, (a, z) in SEGP.items():
        pts = [t for t in me if a - 1 <= t <= z]
        rm = np.array([eq[j] / eq[i] - 1 for i, j in zip(pts[:-1], pts[1:])]); rb = np.array([bc[j] / bc[i] - 1 for i, j in zip(pts[:-1], pts[1:])])
        COR[nm] = {"月數": int(len(rm)), "相關": float(np.corrcoef(rm, rb)[0, 1]), "起": str(cal[pts[1]].date())[:7], "迄": str(cal[pts[-1]].date())[:7],
                   "0050 跌的月數": int((rb < 0).sum()), "0050 跌的月 ML 平均": float(rm[rb < 0].mean()), "0050 跌的月 0050 平均": float(rb[rb < 0].mean()),
                   "0050 跌的月 ML 也跌比例": float((rm[rb < 0] < 0).mean())}
        seg = bc[a:z + 1]; pk = np.maximum.accumulate(seg); dd = (seg - pk) / pk
        lo = int(np.argmin(dd)); hi = int(np.flatnonzero(seg[:lo + 1] == pk[lo])[0])
        tp, tl = a + hi, a + lo
        assert float(dd[lo]) == S["0050"][nm]["回落"], (dd[lo], S["0050"][nm]["回落"])
        DD[nm] = {"高點日": str(cal[tp].date()), "低點日": str(cal[tl].date()), "0050": float(bc[tl] / bc[tp] - 1),
                  "ML 同期": float(eq[tl] / eq[tp] - 1), "營量v1_T1 同期": float(t1[tl] / t1[tp] - 1)}
    # ── ③ 混合
    MIX = {}
    for nm, (a, z) in SEGP.items():
        mp, rb_ = mix_path(eq, bc, a, z, cal)
        m0p, _ = mix_path(eq, bc, a, z, cal, 0.0, 0.0)
        cm, mm = R13.window_stats(mp, 0, len(mp), 0, len(mp)); cz, mz = R13.window_stats(m0p, 0, len(m0p), 0, len(m0p))
        c0, m0 = ws(bc, a, z); c2, m2 = ws(eq, a, z); c3, m3 = ws(t1, a, z)
        MIX[nm] = {"混合 50／50（扣再平衡成本）": {"年化": float(cm), "回落": float(mm), "比值": float(cm) / abs(float(mm))},
                   "混合（不扣成本，參考）": {"年化": float(cz), "回落": float(mz), "比值": float(cz) / abs(float(mz))},
                   "純 0050": {"年化": c0, "回落": m0, "比值": c0 / abs(m0)},
                   "純 ML": {"年化": c2, "回落": m2, "比值": c2 / abs(m2)},
                   "營量 v1（T1）": {"年化": c3, "回落": m3, "比值": c3 / abs(m3)},
                   "再平衡": rb_}
        if nm == "探索":
            np.save(os.path.join(OUT, "mix_探索.npy"), mp)
        else:
            np.save(os.path.join(OUT, "mix_確認.npy"), mp)
    # 營量兩段也對 MLx summary（同一條 T1 路徑）
    G["營量 v1 兩段 ＝ summary 營量"] = all(MIX[nm]["營量 v1（T1）"]["年化"] == S["營量 v1（T1 版、stop_force 開、種子 0）"][nm]["年化"] and
                                     MIX[nm]["營量 v1（T1）"]["回落"] == S["營量 v1（T1 版、stop_force 開、種子 0）"][nm]["回落"] for nm in SEGP)
    # ── ④ 讀法
    weak = Y[Y["0050 下跌"]]
    down = "；".join(f"{r['年'][:4]} 0050 {r['0050']:+.1%}、ML {r['ML']:+.1%}" for _, r in weak.iterrows())
    read = (f"0050 下跌的年份只有 {'、'.join(r['年'][:4] for _, r in weak.iterrows())}（{down}）；"
            f"0050 跌的月份，ML 平均 探索 {COR['探索']['0050 跌的月 ML 平均']:+.1%}（0050 {COR['探索']['0050 跌的月 0050 平均']:+.1%}）、"
            f"確認 {COR['確認']['0050 跌的月 ML 平均']:+.1%}（0050 {COR['確認']['0050 跌的月 0050 平均']:+.1%}）；"
            f"0050 最大回落期間 ML 同期 探索 {DD['探索']['ML 同期']:+.1%}（0050 {DD['探索']['0050']:+.1%}）、確認 {DD['確認']['ML 同期']:+.1%}（0050 {DD['確認']['0050']:+.1%}）；"
            f"月報酬相關 探索 {COR['探索']['相關']:.2f}、確認 {COR['確認']['相關']:.2f}。")
    OUTJ = {"性質": "描述表（裁定 seq267）：⛔ 不判、N 不加、不重挑", "格": PICK, "MLx commit": "db0ebafae9",
            "閘": {**{k: bool(v) for k, v in G.items()}, "營量 v1（T1）＝ resultsT1fix seeds c13｜t1｜r＝0": {"全過": all(gt.values()), "逐欄": gt, "本檔": mine}},
            "讀法": read, "逐年": Y.to_dict("records"), "月相關": COR, "0050 最大回落期間": DD, "混合": MIX,
            "口徑": {"逐年": "前一年最後交易日收盤 → 當年最後交易日收盤；2026 到 2026-08-24；ML 2019 起點 ＝ 起始資金 1",
                   "月": "月底收盤對月底收盤；2026-08 到 08-24", "段": "R13.window_stats（段首日收盤起、245 日／年）",
                   "混合": "每段段首日收盤 50／50 起算（不扣成本）；段內每年 1 月第一個交易日收盤再平衡；調整量 d ＝ |0050 − 總值÷2|，0050 側扣 d×0.385%、ML 側扣 d×0.585%（本線讀法：兩側都照來回扣）"},
            "summary 各年對照": S["挑中格各年（本格／0050）"]}
    json.dump(OUTJ, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # ── REPORT
    P = lambda v: f"{v:+.2%}"
    L = [f"# MLx 挑中格 {PICK} 逐年描述（裁定 seq267；⛔ 不判、N 不加、不重挑）", "",
         f"**讀法**：{read}", "",
         "## 一、逐年報酬（前一年底收盤 → 當年底收盤）", "",
         "| 年 | 段 | ML 挑中格 | 0050 | 營量 v1（T1） | ML−0050 | 標記 |", "|---|---|---:|---:|---:|---:|---|"]
    for _, r in Y.iterrows():
        tag = "、".join(t for t, f in (("0050 下跌", r["0050 下跌"]), ("0050 落後 ML", r["0050 落後 ML"])) if f)
        L.append(f"| {r['年']} | {r['段']} | {P(r['ML'])} | {P(r['0050'])} | {P(r['營量v1_T1'])} | {P(r['ML−0050'])} | {tag} |")
    L += ["", "⚠ 2019～2021 屬**挑選段**：挑中格是從 36 格裡挑探索段最好的，2021 那年 +181% 也在挑選依據內 ⇒ 這三年不是樣本外。",
          f"註：ML 2019 起點 ＝ 起始資金 1（2019-01-02 收盤權益也是 1）；ML、0050 各年與 resultsMLx/summary.json「挑中格各年」逐位元相同：{G['各年 ＝ summary 挑中格各年']}。", "",
          "## 二、月報酬相關（ML 對 0050）與 0050 最大回落期間", "",
          "| 段 | 月數 | 相關 | 0050 跌的月數 | 那些月 ML 平均 | 那些月 0050 平均 | 那些月 ML 也跌 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for nm, c in COR.items():
        L.append(f"| {nm}（{c['起']}～{c['迄']}） | {c['月數']} | {c['相關']:.3f} | {c['0050 跌的月數']} | {P(c['0050 跌的月 ML 平均'])} | {P(c['0050 跌的月 0050 平均'])} | {c['0050 跌的月 ML 也跌比例']:.0%} |")
    L += ["", "| 段 | 0050 高點日 → 低點日 | 0050 | ML 同期 | 營量 v1（T1）同期 |", "|---|---|---:|---:|---:|"]
    for nm, d in DD.items():
        L.append(f"| {nm} | {d['高點日']} → {d['低點日']} | {P(d['0050'])} | {P(d['ML 同期'])} | {P(d['營量v1_T1 同期'])} |")
    L += ["", "## 三、混合 0050＋ML 各 50%（每年 1 月再平衡、扣再平衡成本）", "",
          "| 段 | 組合 | 年化 | 回落 | 比值 |", "|---|---|---:|---:|---:|"]
    for nm, M in MIX.items():
        for k in ("混合 50／50（扣再平衡成本）", "純 0050", "純 ML", "營量 v1（T1）", "混合（不扣成本，參考）"):
            v = M[k]; L.append(f"| {nm} | {k} | {P(v['年化'])} | {P(v['回落'])} | {v['比值']:.3f} |")
    L += ["", "成本（本線讀法）：每段段首日收盤 50／50 起算（不扣，同純 0050 基準）；段內每年 1 月第一個交易日收盤再平衡，調整量 d ＝ |0050 部位 − 總值÷2|，"
          "0050 側扣 d×0.385%（ETF 來回）、ML 側扣 d×0.585%（個股來回；ML 序列本身已內含選股的個股成本，這裡只對再平衡多買賣的部分照比例扣）⇒ 兩側都照來回扣，偏保守。",
          "段內年化／回落照 R13.window_stats（段首日收盤起、245 日／年），與 resultsMLx 同口徑。", "",
          f"閘：ML、0050 兩段 ＝ resultsMLx/summary.json 逐位元 {all(G[k] for k in G if not k.startswith('營量'))}；"
          f"營量 v1（T1）重跑 ＝ resultsT1fix/seeds.csv.gz c13｜t1｜r＝0 逐位元（8 欄）{all(gt.values())}；營量兩段 ＝ MLx summary {G['營量 v1 兩段 ＝ summary 營量']}。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L), flush=True)


if __name__ == "__main__":
    main()

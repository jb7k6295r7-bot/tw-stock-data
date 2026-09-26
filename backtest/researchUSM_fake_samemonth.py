# -*- coding: utf-8 -*-
"""USREG-M 補跑：假訊號臂「同檔同月」描述臂（美股登錄 seq4 §一：台股原登錄的「同檔同月」仍為描述臂）。⛔ 只描述、判定不動、不計 N。

照台股 researchM.py B9（台股原登錄 §八 那一臂的落地）：每個（檔, 曆月）有 k 筆保留真事件 ⇒ 在該檔該月、T ∈ [窗首, 窗尾−21]、
當天在指數且有有效 K 棒的日子中不放回抽 k 天（不足 ⇒ 全取、另報）；之後照同一順序（合併 20 日 → 硬斷點 [T, T+21]（S1）→ T+1 停牌）；
種子 default_rng(20260925＋r)，依（檔, 曆月）排序逐組抽，r＝0…29；判過 ＝ 95% CI（月分群）不含 0。
母體、基準、斷點、成本 ＝ researchUSM_body.py 同一套（import，⛔ 未改）。
輸出（只有彙總）：resultsUSM/body_fake_samemonth.csv（每次）、body_fake_samemonth.json（三格彙總）。
"""
from __future__ import annotations
import os, sys, time, json
from collections import Counter
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import us_data as U
from backtest import researchUSM_body as MB

OUT = MB.OUT
REPS = 30


def main():
    t0 = time.time()
    U.assert_pinned()
    calF = U.load_calendar(); cal = calF[calF >= MB.CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1])); wE = w1 - MB.H_OUT
    MB._G["cap"] = -(-(wE - w0 + 1) // MB.BLOCK)
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    with Pool(2, initializer=MB._init, initargs=(cal, w0, w1)) as pool:
        res = pool.map(MB.load_one, tick, chunksize=4)
    ST = {r["S"].t: r for r in res if r is not None}
    sids = sorted(ST); SS = {s: ST[s]["S"] for s in sids}
    O = np.column_stack([SS[s].o for s in sids]); okM = np.column_stack([SS[s].okO & SS[s].member for s in sids])
    PX = np.column_stack([SS[s].px for s in sids]); CSPB = np.column_stack([SS[s].cs_pb for s in sids])
    EW20 = MB.ew_us(O, okM, PX, CSPB, 20)
    ref = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    mon = np.array([str(d)[:7] for d in cal])
    rows, summ = [], {}
    for m in MB.MAIN:
        real = Counter()
        for s in sids:
            for T, first, pay, stt in ST[s]["cfgs"][(m, 5, "close")]:
                if stt == "保留":
                    real[(s, mon[T])] += 1
        assert sum(real.values()) == ref["判定三格"][m]["n"], (m, sum(real.values()), ref["判定三格"][m]["n"])
        dayset = {}
        for s in sids:
            S = SS[s]; idx = np.arange(w0, wE + 1)
            idx = idx[S.member[w0:wE + 1] & S.valid[w0:wE + 1]]
            for mo in np.unique(mon[idx]):
                dayset[(s, mo)] = idx[mon[idx] == mo]
        grp = sorted(real); short = 0; ok_all = True
        for r in range(REPS):
            rng = np.random.default_rng(MB.SEED + r)
            drawn = {}
            for g in grp:
                days = dayset.get(g, np.array([], int)); k = real[g]
                if k > len(days):
                    short += int(r == 0); k = len(days)
                if k:
                    drawn.setdefault(g[0], []).extend(int(x) for x in np.sort(rng.choice(days, size=k, replace=False)))
            got = Counter((s, mon[t]) for s, ts in drawn.items() for t in ts)
            ok_all &= all(got[g] == min(real[g], len(dayset.get(g, []))) for g in grp)
            xs, Ts = [], []; acc = Counter()
            for s in sorted(drawn):
                S = SS[s]
                for T, first, _, stt in S.status([(t, t, None) for t in sorted(drawn[s])]):
                    acc[stt] += 1
                    if stt == "保留":
                        xs.append(S.px[T + MB.H_OUT] / S.o[T + 1] - 1.0 - EW20[T + 1]); Ts.append(T)
            sf = MB.summ(xs, Ts, cal, w0)
            pas = not (sf["lo"] <= 0 <= sf["hi"])
            rows.append({"畫法": m, "版本": "同檔同月（描述）", "r": r, "抽出": int(sum(acc.values())), "保留": sf["n"], "合併掉": acc["合併掉"],
                         "剔除": int(sum(acc.values()) - acc["保留"] - acc["合併掉"]), "平均X": sf["平均"], "中位X": sf["中位"],
                         "lo": sf["lo"], "hi": sf["hi"], "n_eff": sf["n_eff"], "判過": bool(pas),
                         "判過_正": bool(pas and sf["平均"] > 0), "判過_負": bool(pas and sf["平均"] < 0)})
        F = pd.DataFrame([x for x in rows if x["畫法"] == m])
        summ[m] = {"x／30（CI不含0，兩側）": int(F["判過"].sum()), "其中(+)": int(F["判過_正"].sum()), "其中(−)": int(F["判過_負"].sum()),
                   "平均X的平均": float(F["平均X"].mean()), "平均X範圍": [float(F["平均X"].min()), float(F["平均X"].max())],
                   "平均保留數": float(F["保留"].mean()), "(檔,曆月)組數": len(grp), "可抽天數不足的組數": short,
                   "每組抽出筆數＝真事件數（不足者全取）": bool(ok_all), "真事件平均X": ref["判定三格"][m]["平均"]}
        print("[同檔同月 {}] {}／30（＋{}／−{}）｜30 次平均 X {:+.4%}｜真事件 {:+.4%}｜{:.0f}s".format(
            m, summ[m]["x／30（CI不含0，兩側）"], summ[m]["其中(+)"], summ[m]["其中(−)"], summ[m]["平均X的平均"], summ[m]["真事件平均X"], time.time() - t0), flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "body_fake_samemonth.csv"), index=False, encoding="utf-8")
    json.dump({"性質": "USREG-M 假訊號臂 同檔同月（描述；seq4 §一；⛔ 判定不動、不計 N）", "讀法": "台股 researchM B9 原樣（含合併 20 日）＋美股母體／S1 斷點",
               "資料commit": U.data_commit(), "三格": summ}, open(os.path.join(OUT, "body_fake_samemonth.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

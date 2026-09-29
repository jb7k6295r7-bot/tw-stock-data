# -*- coding: utf-8 -*-
"""surge_feat_daily 的閘門 G1：5 個歷史日期（2022、2024、2026 各至少 1 天）全部股票，與 s5work Q 表（及 F 表原值欄）逐格比。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.surge_feat_daily_check [--mode stitched|daily]
    stitched ＝ 與 s5work 建表同一份資料（接合版面＋main b53f5540a8 archive＋早年營收）⇒ 驗「式子一字不差」
    daily    ＝ 每日名單實際用的資料形態（main b53f5540a8 的每日 archive＋另 archive 的融資／法人／財報／meta＋固定的早年營收）⇒ 驗「換成每日資料仍相同」
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

from backtest import researchSurge5 as S5
from backtest import surge_feat_daily as SFD

DATES = ["2022-03-15", "2022-11-10", "2024-05-20", "2024-12-12", "2026-08-20"]
OUT = "backtest/resultsDaily/surge_feat_G1"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="stitched"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.mode == "stitched":
        price, aux, early = S5.ST, S5.MAIN, S5.EARLY
    else:
        price = os.path.expanduser(f"~/h2data/{S5.MAIN_SHA}/data"); aux = SFD.ensure_aux(S5.MAIN_SHA); early = SFD.EARLY
    W, uni = SFD.world(price, aux, early)
    cal = W["cal"]; pos = [int(cal.get_loc(pd.Timestamp(d))) for d in DATES]
    R = SFD.compute(price, aux, min(pos), max(pos), W=W, uni=uni)
    Q = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); F = np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r")
    u5 = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); i5 = {s: i for i, s in enumerate(u5["stock_id"])}
    D5 = S5.D; D5.DATA = S5.ST; cal5 = D5.load_calendar()
    res = {}; det = []
    for d, p in zip(DATES, pos):
        t = p - R["d0"]; p5 = int(cal5.get_loc(pd.Timestamp(d)))
        ids = [s for s in uni["stock_id"] if s in i5]; mi = np.array([uni.index[uni["stock_id"] == s][0] for s in ids]); m5 = np.array([i5[s] for s in ids])
        only_new = sorted(set(uni["stock_id"][R["bar"][:, t]]) - set(ids)); bar5 = np.asarray(np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")[:, p5])
        only_old = sorted(set(u5["stock_id"][bar5]) - set(uni["stock_id"][R["bar"][:, t]]))
        r = {"有K棒檔數（新）": int(R["bar"][:, t].sum()), "有K棒檔數（s5work）": int(bar5.sum()), "只在新母體": only_new[:10], "只在 s5work": only_old[:10]}
        for col in SFD.QCOLS + SFD.LCOLS:
            mine = R["code"][col][mi, t]; ref = np.asarray(Q[S5.FIX[col], :, p5])[m5]
            bad = np.flatnonzero(mine != ref); r[col] = int(len(bad))
            for b in bad[:5]:
                det.append({"日": d, "欄": col, "代號": ids[b], "新": int(mine[b]), "s5work": int(ref[b]), "新原值": float(R["raw"][col][mi[b], t]), "s5work原值": float(F[S5.FIX[col], m5[b], p5])})
        for col in SFD.RCOLS:
            mine = R["raw"][col][mi, t]; ref = np.asarray(F[S5.FIX[col], :, p5])[m5]
            r[col] = int((~((mine == ref) | (np.isnan(mine) & np.isnan(ref)))).sum())
        r["14 特徵合計不同"] = int(sum(r[c] for _, c, _ in SFD.FEATS)); res[d] = r
        print(d, {k: v for k, v in r.items() if not isinstance(v, list)})
    tot = sum(v["14 特徵合計不同"] for v in res.values()) + sum(v[c] for v in res.values() for c in SFD.QCOLS + SFD.LCOLS + SFD.RCOLS if c not in [x[1] for x in SFD.FEATS])
    out = {"模式": a.mode, "資料": {"price": price, "aux": aux, "early": early}, "日期": res, "全部欄不同合計": int(tot), "不同明細（每欄每日前 5）": det}
    json.dump(out, open(os.path.join(OUT, f"G1_{a.mode}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"G1 {a.mode}：全部欄不同合計 {tot}")


if __name__ == "__main__":
    main()

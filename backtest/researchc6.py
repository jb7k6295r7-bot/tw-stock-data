# -*- coding: utf-8 -*-
"""PREREGC6（BTC 長歷史重做 C1，SMA200）v2（sha 0e37bfefb8fe402c）——回測線執行端。批2（批1 已結算，裁定線 seq118 §四）。

資料：data/crypto/BTC.csv 釘 commit 22465b5bc2cc83a2c6dc1702280057a0bef80391（與 C2 同一份唯讀副本 ~/c2data/<sha>/）
規則／CI／判準／出口／假訊號：一律 researchc1（同一支；⛔ 不抄第二份）

⭐ 落地讀法（⛔ 看任何結果前寫在這裡；交件逐條列出）：
 G1 拼接：source＝bitstamp 且 date ≤ 2017-08-16 為 Bitstamp 段；其後為 Binance 段（逐列 source 欄驗）
    主格：Bitstamp 段 OHLC 整段 × k，k ＝ Binance 首日 open ÷ Bitstamp 末日 close（比例還原）；穩健性：不還原直接接
 G2 窗：拼接後 SMA200 首個有值日 ～ 2026-09-19（C1 同一末日）；第 i 期＝close(i)→close(i+1)，期的「日期」＝起點那一天
 G3 新段（判定格）＝ 起點日 ≤ 2018-03-03 的期（C1 BTC 格的第一期起點是 2018-03-04）；全窗連續跑一次再切段
    ⇒ 新段從窗首空手起算（窗首即 SMA 首日），不另重置
 G4 重疊段錨點＝ 用【只含 Binance 段】的收盤跑 C1 同一支 rule_series ⇒ 窗首 2018-03-04、空手起算 ⇒ 對 resultsc1/per_coin.csv 的 BTC n200 年化／回落逐位比
    （⚠ C1 當時的資料快照與本件不同；對不上就據實報差多少、查是哪幾列資料變了，⛔ 不硬對）
 G5 假訊號：新段 held 段落重排 1,000 組（C1.placebo_dist，種子 20260923）；聯合判過比例＝ 1,000 組中過 C1.judge（對新段買進持有）的比例
 G6 成本敏感度 0.1／0.2／0.4／0.8% 來回：只換 C1 的 COST_RT 重算新段淨報酬（描述）
"""
from __future__ import annotations
import os, sys, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C

SHA = "22465b5bc2cc83a2c6dc1702280057a0bef80391"
ROOT = os.path.expanduser(f"~/c2data/{SHA}")
OUT = "backtest/resultsc6"
END, NEW_LAST = "2026-09-19", "2018-03-03"
SEAM_BS, SEAM_BN = "2017-08-16", "2017-08-17"


def load(scale=True):
    d = pd.read_csv(os.path.join(ROOT, "data", "crypto", "BTC.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    d = d[d["date"] <= END].reset_index(drop=True)
    gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
    assert gap == len(d), "⛔ BTC 日線有缺口"
    bs = d["date"] <= SEAM_BS
    assert set(d.loc[bs, "source"]) == {"bitstamp"} and set(d.loc[~bs, "source"]) == {"binance"}, "⛔ source 欄與接縫日對不上"
    k = float(d.loc[d["date"] == SEAM_BN, "open"].iloc[0]) / float(d.loc[d["date"] == SEAM_BS, "close"].iloc[0])
    if scale:
        for col in ("open", "high", "low", "close"):
            d.loc[bs, col] = d.loc[bs, col].astype(float) * k
    return d, k


def seg(res, dates, last):
    w0 = res["w0"]; n = len(res["r_rule"])
    start_dates = dates[w0:w0 + n]
    m = start_dates <= last
    return m


def analyse(d, tag):
    c = d["close"].to_numpy(float); dates = d["date"].to_numpy()
    res = C.rule_series(c, C.N_MAIN)
    m = seg(res, dates, NEW_LAST)
    rr, rb, held = res["r_rule"][m], res["r_bh"][m], res["held"][m]
    cg_r, md_r, cg_b, md_b = C.cagr(rr), C.mdd(rr), C.cagr(rb), C.mdd(rb)
    ok, sc, sm = C.judge(cg_r, md_r, cg_b, md_b)
    out = {"版本": tag, "窗首": dates[res["w0"]], "新段末期起點": dates[res["w0"] + int(m.sum()) - 1], "新段期數": int(m.sum()),
           "新段_規則": [cg_r, md_r], "新段_買進持有": [cg_b, md_b], "新段_判定格": "過" if ok else "未過", "嚴格優": [sc, sm],
           "新段曝險": float(held.mean()), "新段進出場": int(np.abs(np.diff(np.insert(held, 0, 0.0))).sum())}
    fr, fb = res["r_rule"], res["r_bh"]
    out["全窗_描述"] = {"期數": len(fr), "規則": [C.cagr(fr), C.mdd(fr)], "買進持有": [C.cagr(fb), C.mdd(fb)], "判定格形": "過" if C.judge(C.cagr(fr), C.mdd(fr), C.cagr(fb), C.mdd(fb))[0] else "未過"}
    return out, (rr, rb, held, ok, sc, sm, cg_r, md_r, cg_b, md_b), res, m


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    d_main, k = load(True); d_raw, _ = load(False)
    R_ = {"資料commit": SHA, "k（比例還原係數）": k}
    main_, (rr, rb, held, ok, sc, sm, cg_r, md_r, cg_b, md_b), res, m = analyse(d_main, "比例還原（主格）")
    raw_, raw_t, _, _ = analyse(d_raw, "不還原（穩健性）")
    R_["主格"] = main_; R_["不還原"] = raw_
    R_["接縫兩版新段判定是否相同"] = main_["新段_判定格"] == raw_["新段_判定格"] and main_["嚴格優"] == raw_["嚴格優"]
    # CI（新段）
    Lb = C.politis_white_block(rr - rb)
    ci1 = C.paired_ci(rr, rb, Lb, np.random.default_rng(C.SEED))
    ci2 = C.paired_ci(rr, rb, 2 * Lb, np.random.default_rng(C.SEED))
    ex, why = C.exit_of(ok, sc, sm, ci1, ci2["mdd"])
    R_["新段CI"] = {"L": Lb, "年化差": ci1["cagr"], "回落深度差": ci1["mdd"], "回落深度差_2L": ci2["mdd"], "出口": ex, "理由": why}
    # 假訊號（新段）
    degen = []
    if main_["新段曝險"] >= C.EXPO_DEGEN:
        degen.append("曝險 ≥ 90%")
    if main_["新段進出場"] < C.MIN_TRADES:
        degen.append("進出場 < 5")
    if not degen:
        pcg, pmd = C.placebo_dist(held, rb, np.random.default_rng(C.SEED))
        joint = np.mean([C.judge(a, -b, cg_b, md_b)[0] for a, b in zip(pcg, pmd)])
        R_["新段假訊號"] = {"年化百分位": float((pcg < cg_r).mean() * 100), "回落百分位": float((pmd > abs(md_r)).mean() * 100),
                         "聯合判過比例": float(joint)}
        pd.DataFrame({"cagr": pcg, "mdd_abs": pmd}).to_csv(os.path.join(OUT, "placebo_newseg.csv.gz"), index=False)
    else:
        R_["新段假訊號"] = {"狀態": "；".join(degen)}
    # 成本敏感度（新段、描述）
    cs = {}
    for rt in (0.001, 0.002, 0.004, 0.008):
        prev = np.insert(held[:-1], 0, 0.0)
        net = held * rb - np.abs(held - prev) * (rt / 2.0)
        cs[f"{rt:.1%}"] = {"年化": C.cagr(net), "回落": C.mdd(net), "判定格": "過" if C.judge(C.cagr(net), C.mdd(net), cg_b, md_b)[0] else "未過"}
    R_["新段成本敏感度"] = cs
    # 損益兩平（新段、嚴格優的腳；C1 同法但只在新段）
    be = {}
    for leg, flag in (("CAGR", sc), ("MDD", sm)):
        if not flag:
            continue
        def strict_at(rt):
            prev = np.insert(held[:-1], 0, 0.0); net = held * rb - np.abs(held - prev) * (rt / 2.0)
            return C.cagr(net) > cg_b if leg == "CAGR" else abs(C.mdd(net)) < abs(md_b)
        lo, hi = C.COST_RT, 0.5
        if strict_at(hi):
            be[leg] = "≥ 50%"
        else:
            for _ in range(60):
                mid = (lo + hi) / 2; lo, hi = (mid, hi) if strict_at(mid) else (lo, mid)
            be[leg] = (lo + hi) / 2
    R_["新段損益兩平來回成本"] = be
    # 錨點：只含 Binance 段跑 C1（G4）
    bn = d_main[d_main["date"] >= SEAM_BN].reset_index(drop=True)
    r1 = C.rule_series(bn["close"].to_numpy(float), C.N_MAIN)
    a_c, a_m = C.cagr(r1["r_rule"]), C.mdd(r1["r_rule"])
    c1 = pd.read_csv("backtest/resultsc1/per_coin.csv", float_precision="round_trip")
    c1b = c1[c1["coin"] == "BTC"].iloc[0]
    R_["重疊段錨點（C1 BTC n200）"] = {"本件窗首": bn["date"].iloc[r1["w0"]], "C1窗首": c1b["n200_w0_date"],
                                  "本件": [a_c, a_m], "C1交件": [float(c1b["n200_cagr_rule"]), float(c1b["n200_mdd_rule"])],
                                  "逐位相同": bool(a_c == float(c1b["n200_cagr_rule"]) and a_m == float(c1b["n200_mdd_rule"])),
                                  "期數": [len(r1["r_rule"]), int(c1b["n200_days"])]}
    json.dump(R_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

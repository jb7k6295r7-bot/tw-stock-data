# -*- coding: utf-8 -*-
"""researchYLnoDup 獨立查核（不 import researchYLnoDup／researchYFallin；從存檔的逐筆、逐日與訊號表 DataFrame 重建）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLnoDup_check

 K1 逐日重建兩本帳持倉（r＝0～2、兩世界、營飆＋原版／X1／X2）：由 sample_trades 的買賣配對得 [tb, ts)，每個交易日持股檔數 ＝ sample_daily「持股」（不符日數）；
    另列抽樣日（每段 3 天）兩本帳持股名單、交集
 K2 X1／X2 規則：營量每筆買進 sid ∉ 營飆當天買進（X1）／∉ 營飆 [tb, ts) 持有（X2）（不符筆數）；原版同式算「會碰到的」筆數（應 ＞ 0，證明查核非空轉）
 K3 遞補規則（訊號表 DataFrame 直接重建，不經 build_days）：每個營量買進日或有排除檔出現的日，合格候選 ＝ 當天訊號 − 營量持有（tb＜t＜ts）− 排除檔，
    依 relvol 遞減（NaN 最後、同值保原序）；實買 ＝ 合格候選前 len(實買) 名；len(實買) ≤ 空位；skip 全屬排除檔且在當天訊號；repl ⊆ 實買
 K4 被跳過假想淨報酬：由訊號表 g_H60／xpos_H60／開盤價／強制出場重算 ＝ 存檔 net（最大差）
 K5 各段年化／回落：由 sample_daily 權益以 rerun17.win_metrics 重算 ＝ seeds（repr）；合併帳以本檔自寫的年調迴圈重算 ＝ 存檔「合併」（最大差）
 K6 營飆 eq_sha（r＝0～2）＝ resultsYF_N；cells 中位 ＝ seeds 重算（最大差）
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYLvsYF as YV                   # noqa: E402

OUT = "backtest/resultsYLnoDup"
COST = R.COST
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}


def pairs(T):
    """買賣 ⇒ [(sid, tb, ts)]。"""
    op_, P = {}, []
    T = T.assign(o=T["side"].map({"sell": 0, "buy": 1})).sort_values(["t", "o"], kind="stable")
    for s, t, sd in zip(T["sid"], T["t"], T["side"]):
        if sd == "buy":
            assert s not in op_
            op_[s] = t
        else:
            P.append((s, op_.pop(s), t))
    assert not op_
    return P


def compose_own(EA, EB, rebal, w=0.5, c=0.00585):
    n = len(EA); V = np.empty(n); a, b = w, 1 - w; V[0] = 1.0
    for t in range(1, n):
        a *= EA[t] / EA[t - 1]; b *= EB[t] / EB[t - 1]; v = a + b
        if rebal[t]:
            v -= abs(w * v - a) * c; a, b = w * v, (1 - w) * v
        V[t] = v
    return V


def main():
    log = YV.log_to(os.path.join(OUT, "run_check.log"))
    log(f"[查核開始] {YV.now_tpe()}（台北）")
    TR = pd.read_csv(os.path.join(OUT, "sample_trades.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    DY = pd.read_csv(os.path.join(OUT, "sample_daily.csv.gz"), float_precision="round_trip")
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"營飆_eq_sha": str}, float_precision="round_trip")
    CE = pd.read_csv(os.path.join(OUT, "cells.csv"))
    rf = pd.read_csv("backtest/resultsYF_N/seeds.csv.gz", dtype={"eq_sha": str})
    Wm, _ = IG.main_world(log)
    We, _ = IG.early_world(log, 3)
    WD = {"主": Wm, "早年": We}
    K = {}; samples = []
    for wn, W in WD.items():
        cal = W["cal"]; NP = W["NP"]
        sig = W["SIG"][False].dropna(subset=["sid", "entry_pos", "xpos_H60", "g_H60"])
        sig = sig[sig["xpos_H60"] >= 0]
        byday = {int(k): g for k, g in sig.groupby("entry_pos")}
        w0, w1 = W["w0"], W["w1"]
        rebal = np.r_[False, pd.DatetimeIndex(cal[w0 + 1:w1 + 1]).year != pd.DatetimeIndex(cal[w0:w1]).year]
        for r in sorted(TR[TR["世界"] == wn]["r"].unique()):
            T_ = TR[(TR["世界"] == wn) & (TR["r"] == r)]; D_ = DY[(DY["世界"] == wn) & (DY["r"] == r)]
            acc = {}
            for v in ("營飆", "原版", "X1", "X2"):
                P = pairs(T_[(T_["帳"] == v) & T_["side"].isin(["buy", "sell"])])
                cnt = np.zeros(NP + 2, int)
                for s, tb, ts in P:
                    cnt[tb:ts] += 1
                d = D_[D_["帳"] == v].sort_values("t")
                K.setdefault("K1 持股檔數逐日重建不符（日）", 0)
                K["K1 持股檔數逐日重建不符（日）"] += int((cnt[d["t"].to_numpy()] != d["持股"].to_numpy()).sum())
                acc[v] = (P, d, T_[T_["帳"] == v])
            PF = acc["營飆"][0]
            fbuy = {}
            fheld = {}
            for s, tb, ts in PF:
                fbuy.setdefault(tb, set()).add(s)
                for t in range(tb, ts):
                    fheld.setdefault(t, set()).add(s)
            # K6 營飆 sha
            eF = acc["營飆"][1]["權益"].to_numpy(float)
            sh = hashlib.sha256(eF.tobytes()).hexdigest()[:16]
            ref = rf[(rf["世界"] == wn) & (rf["N"] == 10) & (rf["r"] == r)]["eq_sha"].iloc[0]
            K.setdefault("K6 營飆 eq_sha ≠ YF_N（顆）", 0); K["K6 營飆 eq_sha ≠ YF_N（顆）"] += int(sh != ref)
            for v in ("原版", "X1", "X2"):
                P, d, Tv = acc[v]
                ex_of = (lambda t: fbuy.get(t, set())) if v == "X1" else (lambda t: fheld.get(t, set()))
                buys = Tv[Tv["side"] == "buy"]
                for rule in ("X1", "X2"):
                    exf = (lambda t: fbuy.get(t, set())) if rule == "X1" else (lambda t: fheld.get(t, set()))
                    nb = int(sum(1 for s, t in zip(buys["sid"], buys["t"]) if s in exf(int(t))))
                    if v == "原版":
                        K.setdefault(f"K2 原版若套 {rule} 會碰到（筆，應＞0）", 0); K[f"K2 原版若套 {rule} 會碰到（筆，應＞0）"] += nb
                    elif v == rule:
                        K.setdefault("K2 X1／X2 規則不符（筆）", 0); K["K2 X1／X2 規則不符（筆）"] += nb
                if v == "原版":
                    continue
                # K3 遞補
                B = {}
                for s, t in zip(buys["sid"], buys["t"]):
                    B.setdefault(int(t), []).append(s)
                SK = Tv[Tv["side"] == "skip"]; RP = Tv[Tv["side"] == "repl"]
                days = sorted(set(B) | {t for t, g in byday.items() if ex_of(t) & set(g["sid"])})
                intervals = {}
                for s, tb, ts in P:
                    intervals.setdefault(s, []).append((tb, ts))
                bad3 = 0; cashlim = 0
                for t in days:
                    g = byday.get(t)
                    held = {s for s, iv in intervals.items() if any(tb < t < ts for tb, ts in iv)}
                    exs = ex_of(t)
                    if g is None:
                        bad3 += int(t in B); continue
                    el = g[~g["sid"].isin(held | exs)]
                    key = el["relvol"].to_numpy(float); key = np.where(np.isnan(key), -np.inf, key)
                    order = list(el["sid"].to_numpy()[np.argsort(-key, kind="stable")])
                    bt = B.get(t, [])
                    free = 20 - len(held)
                    bad3 += int(bt != order[:len(bt)]) + int(len(bt) > max(free, 0))
                    cashlim += int(len(bt) < min(max(free, 0), len(order)))
                bad3 += int(sum(1 for s, t in zip(SK["sid"], SK["t"]) if s not in ex_of(int(t)) or s not in set(byday[int(t)]["sid"])))
                bad3 += int(sum(1 for s, t in zip(RP["sid"], RP["t"]) if s not in B.get(int(t), [])))
                K.setdefault("K3 遞補規則不符", 0); K["K3 遞補規則不符"] += bad3
                K.setdefault("K3 資訊：現金不足少買日（非錯）", 0); K["K3 資訊：現金不足少買日（非錯）"] += cashlim
                # K4 假想淨報酬
                mx = 0.0
                for s, t, net in zip(SK["sid"], SK["t"], SK["net"]):
                    t = int(t); row = byday[t][byday[t]["sid"] == s].iloc[0]
                    ep = float(W["opens"][s][t]); ep = ep if (np.isfinite(ep) and ep > 0) else float(W["closes"][s][t])
                    x = int(row["xpos_H60"]); gross = float(row["g_H60"]); L = W["SF"].get(s)
                    if L is not None and t <= L and L + 1 < x:
                        gross = float(W["closes"][s][L]) / ep - 1
                    mx = max(mx, abs(gross - COST - net))
                K.setdefault("K4 被跳過假想淨報酬最大差", 0.0); K["K4 被跳過假想淨報酬最大差"] = max(K["K4 被跳過假想淨報酬最大差"], mx)
                # K5 段值、合併
                eY = d["權益"].to_numpy(float)
                srow = SE[(SE["世界"] == wn) & (SE["r"] == r)].iloc[0]
                for sg in SEGS[wn]:
                    x, y = W["segp"][sg]
                    # first／end：與主程式同（sim 的 first ＝ 訊號表最早進場、end ＝ 最晚出場＋2）
                    f0 = int(sig["entry_pos"].min()); e0 = min(NP, int(sig["xpos_H60"].max()) + 2)
                    c_, m_, _ = RR.win_metrics(eY, f0, e0, x, y)
                    K.setdefault("K5 營量段值 ≠ seeds（項）", 0)
                    K["K5 營量段值 ≠ seeds（項）"] += int(repr(c_) != repr(float(srow[f"{sg}_{v}_年化"]))) + int(repr(m_) != repr(float(srow[f"{sg}_{v}_回落"])))
                Vs = d["合併"].to_numpy(float)[w0:w1 + 1]
                Vo = compose_own(eF[w0:w1 + 1], eY[w0:w1 + 1], rebal)
                K.setdefault("K5 合併帳自寫年調迴圈最大差", 0.0); K["K5 合併帳自寫年調迴圈最大差"] = max(K["K5 合併帳自寫年調迴圈最大差"], float(np.max(np.abs(Vs - Vo))))
            # 抽樣日名單（r＝0）
            if r == 0:
                for sg in SEGS[wn]:
                    x, y = W["segp"][sg]
                    for t in (x + (y - x) // 4, x + (y - x) // 2, x + 3 * (y - x) // 4):
                        hf = sorted(s for s, tb, ts in PF if tb <= t < ts)
                        for v in ("原版", "X1", "X2"):
                            hy = sorted(s for s, tb, ts in acc[v][0] if tb <= t < ts)
                            samples.append({"世界": wn, "段": sg, "日期": str(cal[t].date()), "帳": v, "營飆持股": len(hf), "營量持股": len(hy),
                                            "交集": len(set(hf) & set(hy)), "交集名單": " ".join(sorted(set(hf) & set(hy)))})
    # K6 cells 中位 ＝ seeds
    mx = 0.0
    for _, c in CE.iterrows():
        A = SE[SE["世界"] == c["世界"]]
        for k in ("年化", "回落", "合併年化", "合併回落", "F中也在Y", "Y中也在F", "相異檔數", "日報酬相關", "被跳過筆", "替補筆"):
            mx = max(mx, abs(float(A[f"{c['段']}_{c['變體']}_{k}"].median()) - float(c[k])))
    K["K6 cells 中位 vs seeds 重算最大差（cells 存 %.10g ⇒ 容差 1e−8）"] = mx
    SM = pd.DataFrame(samples)
    SM.to_csv(os.path.join(OUT, "check_samples.csv"), index=False, encoding="utf-8-sig")
    log("\n" + SM.drop(columns=["交集名單"]).to_string(index=False))
    log(f"[查核] {json.dumps(K, ensure_ascii=False)}")
    hard = [k for k, v in K.items() if ("應＞0" in k and v <= 0) or ("資訊" not in k and "應＞0" not in k and (v > (1e-8 if "容差 1e−8" in k else 1e-9) if "最大差" in k else v != 0))]
    json.dump({"查核": K, "不過": hard, "完成（台北）": YV.now_tpe()}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[結果] {'全過' if not hard else '⛔ 不過 ' + str(hard)}｜{YV.now_tpe()}（台北）")


if __name__ == "__main__":
    main()

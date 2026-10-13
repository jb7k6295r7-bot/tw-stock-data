# -*- coding: utf-8 -*-
"""漲多加碼：反事實——加碼訊號的「時點」本身有沒有價值（描述性；外部建議「先做反事實」）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；描述性、⛔ 不計 N、⛔ 不判定；用語「假訊號」；⛔ 不給買賣建議。
⚠ 加碼已看過結果（researchAddOn、truetop、exit5、feat）⇒ 本件全是事後描述。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_cf

═══ 讀法（CF 標）═══
 CF0 樣本 ＝ resultsAddOn/feat/feat_rows.csv.gz 的 400 筆（researchAddOn 主臂唯一加碼、A1／A2 去重取 A1、營量營飆同檔兩筆都留、資料尾仍持有不算）；
     段 ＝ feat 的「段」（依 A 的加碼日 ta：主 探索、確認；早年）；主窗 ＝ 探索＋確認
     出場 ＝ exit5/exits.csv.gz 的 S（原持股同日同價賣：S_價、S_價根）；400 筆全是「同原持股」
 CF1 A 立即加碼 ＝ S_價 ÷ op[ta] − 1 − COST（0.585%）；閘：＝ feat 淨報酬（≤ 1e−9）、加碼價 ＝ 世界開盤 op[ta]
 CF2 B_k 延後 k 個交易日：買在 ta 之後第 k 個「有效開盤」（ta 算第 0 個；有效 ＝ 有 K 棒、開盤有值且 ＞ 0），同日（S）賣；k ＝ 5、10
     買進日 ＞ S_價根 ⇒ 不加（缺、照報）；(t, 買進日] 有壞根 ⇒ 不加（缺、照報）
 CF3 R 隨機日：候選 ＝ 該持股 [tb＋9, S_價根 − 5]（tb 為第 1 根 ⇒ 第 10 根～出場前 5 根）中的有效開盤、且 (tb, d] 無壞根；
     每筆抽 200 次（放回；default_rng([20261013, crc32(世界|策略|sid|tb)])），同日（S）賣；R_i ＝ 200 抽淨報酬平均；候選 0 ⇒ 缺
     另記 A 在該筆 200 抽中的百分位（R ＜ A 的比例，同值算半）；R_精確期望 ＝ 候選日等權平均（查核用）
 CF4 配對差 D_i ＝ A_i − R_i；CI ＝ 按 A 加碼月（世界|年月）群集 bootstrap 5000 次（default_rng(20261013)）百分位 95%
 CF5 固定期間：從買進日 d 開盤買，第 H 根有效 K 棒收盤（d 算第 1 根）賣，H ＝ 5／10／20／40，扣 COST；
     (d, 目標根] 有壞根、或資料尾不足 H 根 ⇒ 缺；A 用 d ＝ ta；R 用同 200 抽的 d（每筆平均，缺的抽不算）；A、R 都有才進配對
 CF6 右尾移除：各段依 A 由大到小去掉 ⌈1%·n⌉、⌈5%·n⌉ 筆後 A 平均／中位；同一批剔除後 A−R 配對差平均
 壞根 ＝ researchAddOn.market 同一套（主：bad_main.pkl；早年：bad_early ∪ R8 ∪ reduce_v2 ∪ 未解釋 22 筆）
輸出 backtest/resultsAddOn/cf/：cf.json、cf_table.csv、cf_rows.csv.gz
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import zlib

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa: E402
from backtest import universe_gate as UG                      # noqa: E402

OUT = "backtest/resultsAddOn/cf"
AO_OUT = "backtest/resultsAddOn"
COST = AO.COST
SEED = 20261013
NDRAW = 200
NBOOT = 5000
DELAYS = (5, 10)
HZ = (5, 10, 20, 40)
SEGN = ("探索", "確認", "主窗", "早年")


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def fixed_ret(d, H, op, cl, bar, BADC, n):
    """d 開盤買，第 H 根有效 K 棒（d 算第 1 根）收盤賣。"""
    vb = np.flatnonzero(bar[d:n] & np.isfinite(cl[d:n]))
    if len(vb) < H:
        return np.nan
    tg = d + int(vb[H - 1])
    if BADC[tg + 1] - BADC[d + 1] > 0:           # (d, tg] 有壞根
        return np.nan
    return cl[tg] / op[d] - 1.0 - COST


def boot_ci(x, cl_, rng):
    x = np.asarray(x, float); ok = np.isfinite(x); x = x[ok]; cl_ = np.asarray(cl_)[ok]
    if len(x) < 2:
        return {"n": int(len(x)), "平均": float(x.mean()) if len(x) else None}
    u, inv = np.unique(cl_, return_inverse=True); G = len(u)
    s = np.bincount(inv, weights=x, minlength=G); c = np.bincount(inv, minlength=G).astype(float)
    bs = np.empty(NBOOT)
    for b in range(NBOOT):
        k = rng.integers(G, size=G); bs[b] = s[k].sum() / c[k].sum()
    return {"n": int(len(x)), "群集月數": int(G), "平均": float(x.mean()), "中位": float(np.median(x)),
            "CI95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))], "bootstrap 平均≤0 比例": float((bs <= 0).mean())}


def desc(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "平均": float(v.mean()), "中位": float(np.median(v)), "賺錢比例": float((v > 0).mean())}


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    f = pd.read_csv(os.path.join(AO_OUT, "feat", "feat_rows.csv.gz"), dtype={"sid": str},
                    usecols=["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "淨報酬"])
    ex = pd.read_csv(os.path.join(AO_OUT, "exit5", "exits.csv.gz"), dtype={"sid": str},
                     usecols=["世界", "策略", "sid", "tb", "格", "加碼價", "S_出場日", "S_價", "S_價根", "S_種類"])
    d = f.merge(ex, on=["世界", "策略", "sid", "tb", "格"], how="left", validate="1:1")
    assert len(d) == 400 and d["S_價"].notna().all(), (len(d), d["S_價"].isna().sum())
    info = {"樣本": int(len(d)), "各段": d["段"].value_counts().to_dict(), "S 種類": d["S_種類"].value_counts().to_dict()}
    WS = AO.worlds(log, 1)
    UG.set_gate_v2(True)
    HBW = {}; X = None
    for wn in ("主", "早年"):
        hs = sorted(set(d.loc[d["世界"] == wn, "sid"]))
        M, HB, X, minfo = AO.market(wn, WS[wn], X, log, hs)
        HBW[wn] = HB; del M
    gate_a = 0.0; gate_px = 0.0
    rows = []
    for r in d.to_dict("records"):
        wn, sn, sid, tb, t, ta = r["世界"], r["策略"], r["sid"], int(r["tb"]), int(r["t"]), int(r["ta"])
        W = WS[wn]; n = len(W["cal"])
        op = np.asarray(W["opens"][sid][:n], float); cl = np.asarray(W["closes"][sid][:n], float)
        bar, bad = HBW[wn][sid]; bar = np.asarray(bar[:n], bool); bad = np.asarray(bad[:n], bool)
        BADC = np.r_[0, np.cumsum(bad)]                      # (a, b] 壞根數 ＝ BADC[b+1] − BADC[a+1]
        valid = bar & np.isfinite(op) & (op > 0)
        sb = int(r["S_價根"]); sp = float(r["S_價"])
        A = sp / op[ta] - 1.0 - COST
        gate_px = max(gate_px, abs(op[ta] / r["加碼價"] - 1.0)); gate_a = max(gate_a, abs(A - r["淨報酬"]))
        o = {k: r[k] for k in ("世界", "策略", "sid", "tb", "格", "t", "ta", "段")}
        o.update(S_價根=sb, 持有根=sb - tb + 1, A=A, 加碼月=str(W["cal"][ta])[:7])
        # B
        fut = np.flatnonzero(valid[ta + 1:n]) + ta + 1
        for k in DELAYS:
            o[f"B{k}"] = np.nan; o[f"B{k}_日"] = np.nan
            if len(fut) < k:
                o[f"B{k}_缺因"] = "資料尾"; continue
            db = int(fut[k - 1])
            if db > sb:
                o[f"B{k}_缺因"] = "超過出場"; continue
            if BADC[db + 1] - BADC[t + 1] > 0:
                o[f"B{k}_缺因"] = "壞根"; continue
            o[f"B{k}"] = sp / op[db] - 1.0 - COST; o[f"B{k}_缺因"] = ""; o[f"B{k}_日"] = db
        # R
        lo, hi = tb + 9, sb - 5
        cand = np.arange(lo, hi + 1) if hi >= lo else np.zeros(0, int)
        if len(cand):
            cand = cand[valid[cand] & ((BADC[cand + 1] - BADC[tb + 1]) == 0)]
        o["R候選數"] = int(len(cand))
        for H in HZ:
            o[f"A_{H}"] = fixed_ret(ta, H, op, cl, bar, BADC, n); o[f"R_{H}"] = np.nan
        if len(cand):
            rng = np.random.default_rng([SEED, zlib.crc32(f"{wn}|{sn}|{sid}|{tb}".encode())])
            dd = cand[rng.integers(len(cand), size=NDRAW)]
            rr = sp / op[dd] - 1.0 - COST
            o["R"] = float(rr.mean()); o["R中位"] = float(np.median(rr)); o["R_精確期望"] = float((sp / op[cand] - 1.0 - COST).mean())
            o["A在R百分位"] = float(((rr < A).sum() + 0.5 * (rr == A).sum()) / NDRAW)
            o["A在候選日"] = bool(ta in set(cand.tolist()))
            for H in HZ:
                rv = np.array([fixed_ret(int(x), H, op, cl, bar, BADC, n) for x in dd])
                o[f"R_{H}"] = float(np.nanmean(rv)) if np.isfinite(rv).any() else np.nan
        else:
            o["R"] = np.nan; o["R中位"] = np.nan; o["R_精確期望"] = np.nan; o["A在R百分位"] = np.nan; o["A在候選日"] = False
        rows.append(o)
    R_ = pd.DataFrame(rows)
    gates = {"A 重現 vs feat 淨報酬 最大差": gate_a, "加碼價 vs 世界開盤 最大相對差": gate_px}
    log(f"[閘] {gates}")
    if gate_a > 1e-9 or gate_px > 1e-9:
        raise SystemExit("⛔ A 重現閘不過")
    R_["D"] = R_["A"] - R_["R"]
    for H in HZ:
        R_[f"D_{H}"] = R_[f"A_{H}"] - R_[f"R_{H}"]
    R_["clu"] = R_["世界"] + "|" + R_["加碼月"]
    R_.to_csv(os.path.join(OUT, "cf_rows.csv.gz"), index=False, float_format="%.10g")

    def seg(sg):
        return R_[R_["段"].isin(("探索", "確認"))] if sg == "主窗" else R_[R_["段"] == sg]
    rng = np.random.default_rng(SEED)
    J = {"時間": now_tpe() + "（台北）", "讀法": __doc__.split("═══ 讀法（CF 標）═══")[1].strip(), "資訊": info, "閘": gates, "段": {}}
    TB = []
    for sg in SEGN:
        s = seg(sg); z = {}
        for arm in ("A", "B5", "B10", "R"):
            z[arm] = desc(s[arm])
            TB.append({"段": sg, "項": arm, **z[arm]})
        z["B 缺因"] = {f"B{k}": s[f"B{k}_缺因"].value_counts().to_dict() for k in DELAYS}
        z["R 候選 0（缺）"] = int((s["R候選數"] == 0).sum())
        z["R 精確期望平均"] = float(s["R_精確期望"].mean())
        z["A 加碼日落在 R 候選區間內的比例"] = float(s.loc[s["R"].notna(), "A在候選日"].mean())
        ok = s[s["R"].notna()]
        z["A−R 配對"] = boot_ci(ok["D"], ok["clu"], rng)
        z["A 勝過 R 平均 比例"] = float((ok["A"] > ok["R"]).mean())
        z["A 在 R 百分位（平均／中位）"] = [float(ok["A在R百分位"].mean()), float(ok["A在R百分位"].median())]
        z["A 在 R 百分位 五分位筆數（0-20,20-40,40-60,60-80,80-100）"] = np.histogram(ok["A在R百分位"], bins=[0, .2, .4, .6, .8, 1.0001])[0].tolist()
        for k in DELAYS:
            okb = s[s[f"B{k}"].notna()]
            z[f"A−B{k} 配對（同一批有 B{k} 的）"] = boot_ci(okb["A"] - okb[f"B{k}"], okb["clu"], rng)
        fx = {}
        for H in HZ:
            q = s[s[f"A_{H}"].notna() & s[f"R_{H}"].notna()]
            fx[f"{H}日"] = {"A": desc(q[f"A_{H}"]), "R": desc(q[f"R_{H}"]), "A−R": boot_ci(q[f"D_{H}"], q["clu"], rng)}
            ci = fx[f"{H}日"]["A−R"].get("CI95", [None, None])
            TB.append({"段": sg, "項": f"固定{H}日 A", **desc(q[f"A_{H}"])}); TB.append({"段": sg, "項": f"固定{H}日 R", **desc(q[f"R_{H}"])})
            TB.append({"段": sg, "項": f"固定{H}日 A−R", "n": fx[f"{H}日"]["A−R"]["n"], "平均": fx[f"{H}日"]["A−R"].get("平均"),
                       "中位": fx[f"{H}日"]["A−R"].get("中位"), "CI低": ci[0], "CI高": ci[1]})
        fx["持有到出場（同 A−R 配對那批）"] = {"A": desc(ok["A"]), "R": desc(ok["R"])}
        z["固定期間"] = fx
        TB.append({"段": sg, "項": "A−R 配對（到出場）", "n": z["A−R 配對"]["n"], "平均": z["A−R 配對"]["平均"], "中位": z["A−R 配對"]["中位"],
                   "CI低": z["A−R 配對"]["CI95"][0], "CI高": z["A−R 配對"]["CI95"][1], "A勝R比例": z["A 勝過 R 平均 比例"]})
        rt = {}
        srt = s.sort_values("A", ascending=False)
        for p in (0.01, 0.05):
            m = math.ceil(p * len(s)); rest = srt.iloc[m:]
            rk = rest[rest["R"].notna()]
            rt[f"去掉前 {int(p * 100)}%（{m} 筆）"] = {"A 平均": float(rest["A"].mean()), "A 中位": float(rest["A"].median()),
                                                   "賺錢比例": float((rest["A"] > 0).mean()), "A−R 配對平均": float(rk["D"].mean()),
                                                   "R 平均（同批）": float(rk["R"].mean()), "去掉的 A": [float(v) for v in srt["A"].iloc[:m]]}
            TB.append({"段": sg, "項": f"A 去右尾 {int(p * 100)}%", **desc(rest["A"]), "A−R": float(rk["D"].mean())})
        z["右尾移除"] = rt
        J["段"][sg] = z
    json.dump(J, open(os.path.join(OUT, "cf.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.DataFrame(TB).to_csv(os.path.join(OUT, "cf_table.csv"), index=False, float_format="%.6g")
    log(f"[完成] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

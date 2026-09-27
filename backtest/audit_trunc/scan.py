# -*- coding: utf-8 -*-
"""K5 新檢查（裁定 seq259 §三）：掃「資料尾截斷丟訊號」——哪些已判件的訊號產生器把出場日超出資料尾的訊號整筆丟掉。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.audit_trunc.scan

⛔ 只計數、只讀既有檔，不跑引擎、不重跑任何判定、不改任何既有 .py。輸出 backtest/audit_trunc/scan.json。

量什麼（全部在 edc6f8002f 快照、主窗 2017-03-02～2026-08-24 上）：
  ① 靜態掃描：backtest/*.py 裡「丟尾端」的寫法（build_sig_gate_b 呼叫端、x ≥ ncal continue、xpos＝−1 → 引擎 xpos ≥ 0 過濾）與
     「段尾按市值計」的寫法（xpos＝段尾次一日、min(e＋H−1, s1＋1)）各在哪些檔
  ② AND 訊號（resultsN17/sig_edc6f/and_signals.csv.gz；research11.fixed_exit ⇒ 超出該股最後一根就 xpos＝−1，
     simulate_mtm 以 xpos ≥ 0 過濾 ⇒ 整筆丟）：主窗內各 H 被丟的筆數、其中屬「資料尾」的筆數（日曆近似：exit_pos(e, H) ≥ ncal）、
     各子集（全部／進場日 regime／t−1 regime ＝ 營飆 v1）、逐月、以及被丟訊號從進場開盤到 w1 收盤的報酬分佈（對照 0050 同段）
  ③ 門檻B（researchp7.build_sig_gate_b；x ≥ ncal ⇒ continue）：用 AFCext V3 的 sig_ext.csv.gz（補回列 xpos ≥ ncal）計數與報酬
  ④ 0050 在各「最早受影響日 → w1」的報酬與段內回落
"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np
import pandas as pd

from backtest import rerun17 as RR

RR.use_snapshot()

from backtest import data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "scan.json")


def static_scan():
    """① 靜態：哪些檔用了哪種尾端處理（只做字串比對，⛔ 不 import）。"""
    pats = {
        "calls_build_sig_gate_b": r"build_sig_gate_b\(",
        "drop_x_ge_ncal": r"if\s+x\s*>=\s*(ncal|n|len\(cal\))\b",
        "xpos_minus1": r"else\s+-1\b|xpos_H\{H\}\"\]\s*=|\(np\.nan,\s*-1\)",
        "segment_end_mark": r"s1\s*\+\s*1|段尾次一",
        "t1_pad": r"pad_px|and_censor|REG_T1",
        "fixed_exit_or_setup_and": r"fixed_exit\(|setup_and\(|setup_t1\(|and_signals\.csv",
    }
    res = {k: [] for k in pats}
    for f in sorted(glob.glob(os.path.join(BT, "*.py"))):
        name = os.path.basename(f)
        try:
            txt = open(f, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        for k, p in pats.items():
            if re.search(p, txt):
                res[k].append(name)
    res["calls_build_sig_gate_b_excl_selftest"] = [f for f in res["calls_build_sig_gate_b"]
                                                   if not f.startswith("selftest_") and f != "researchp7.py"]
    return res


def qd(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "mean": float(x.mean()), "p10": float(np.percentile(x, 10)), "median": float(np.median(x)),
            "p90": float(np.percentile(x, 90)), "share_pos": float((x > 0).mean())}


def main():
    cal = D.load_calendar(); ncal = len(cal)
    w0, w1 = RR.win_bounds(cal)
    bench = RR.load_bench(cal)
    reg = RR.regime_mask(bench)
    reg_t1 = np.r_[False, reg[:-1]]
    out = {"日曆": f"{ncal} 根 {cal[0].date()}～{cal[-1].date()}", "主窗": [str(cal[w0].date()), str(cal[w1].date()), int(w1 - w0 + 1)],
           "static": static_scan()}

    uni = D.load_universe().set_index("stock_id")["market"]

    # ② AND
    A = pd.read_csv(os.path.join(BT, "resultsN17", "sig_edc6f", "and_signals.csv.gz"), dtype={"sid": str})
    e = A["entry_pos"].to_numpy(int)
    A = A[(e >= w0) & (e <= w1)].copy()
    e = A["entry_pos"].to_numpy(int)
    subsets = {"全部（P1／P3乙／PREREG10 regime=False）": np.ones(len(A), bool),
               "進場日 regime（PREREG10 #1 #7 #16 #17 原件）": reg[e],
               "t−1 regime（營飆 v1 與其衍生件）": reg_t1[e]}
    need = set()
    tail_rows = {}
    AND = {"主窗訊號列": int(len(A))}
    for H in (60, 120):
        xp = A[f"xpos_H{H}"].to_numpy()
        drop = xp < 0
        tail = np.array([D.exit_pos(int(k), H) >= ncal for k in e])
        AND[f"H{H}"] = {}
        for nm, m in subsets.items():
            d_ = drop & m; t_ = d_ & tail
            mon = pd.Series(A.loc[t_, "month"]).value_counts().sort_index()
            AND[f"H{H}"][nm] = {"訊號列": int(m.sum()), "引擎會丟（xpos<0）": int(d_.sum()), "其中資料尾（日曆近似）": int(t_.sum()),
                                "占比": float(t_.sum() / max(1, m.sum())),
                                "資料尾進場日": [str(cal[int(A['entry_pos'].to_numpy()[t_].min())].date()), str(cal[int(A['entry_pos'].to_numpy()[t_].max())].date())] if t_.any() else None,
                                "逐月（訊號月）": {k: int(v) for k, v in mon.items()}}
        tail_rows[H] = A[drop & tail]
        need |= set(tail_rows[H]["sid"])
    ld = A["xpos_LD"].to_numpy()
    AND["LD"] = {"引擎會丟（xpos<0）": int((ld < 0).sum()), "出場在 w1 之後（窗內照市值計、不丟）": int((ld > w1).sum()),
                 "讀法": "research11.cond_exit 上限 min(n−1, k＋CAP) ⇒ 資料尾的 LD 訊號出場設在最後一根、⛔ 不丟"}

    # ③ 門檻B（AFCext V3 的 sig_ext：原函式列 ＋ T1 補回列）
    G = pd.read_csv(os.path.join(BT, "resultsAFCext", "sig_ext.csv.gz"), dtype={"sid": str})
    gt = G[G["xpos_H120"] >= ncal]
    gb = {"sig_ext 列數（V3）": int(len(G)), "x ≥ ncal（build_sig_gate_b 會丟）": int(len(gt)),
          "補回進場日": [str(cal[int(gt['entry_pos'].min())].date()), str(cal[int(gt['entry_pos'].max())].date())] if len(gt) else None,
          "補回列在主窗內": int((gt["entry_pos"] <= w1).sum()),
          "逐月（量測月）": {k: int(v) for k, v in gt["month"].value_counts().sort_index().items()},
          "原面板 resultsAFC 最後進場": None}
    pa = pd.read_csv(os.path.join(BT, "resultsAFC", "panel.csv.gz"), usecols=["measure_date"], parse_dates=["measure_date"])
    lastm = pa["measure_date"].max()
    gb["原面板 resultsAFC 最後量測日"] = str(lastm.date())
    gb["原面板 resultsAFC 最後進場"] = str(cal[int(cal.searchsorted(lastm)) + 1].date())
    gb["面板截斷＋函式丟尾：主窗內 w1 前沒有新進場的交易日數"] = int(w1 - (int(cal.searchsorted(lastm)) + 1))
    need |= set(gt["sid"])

    # 價格（只讀被丟那些股票）
    closes, opens = RR.load_prices(sorted(need), cal, uni, "branch")

    def rets(df):
        r_w1, r_end, worst, b_w1 = [], [], [], []
        for s, en in zip(df["sid"], df["entry_pos"]):
            en = int(en)
            if s not in closes or en > w1:
                continue
            o = float(opens[s][en]); c = closes[s]
            if not (np.isfinite(o) and o > 0):
                continue
            r_w1.append(float(c[w1]) / o - 1.0)
            r_end.append(float(c[ncal - 1]) / o - 1.0)
            worst.append(float(np.nanmin(c[en:w1 + 1])) / o - 1.0)
            b_w1.append(bench[w1] / bench[en - 1] - 1.0)
        return {"進場開盤→w1 收盤": qd(r_w1), "進場開盤→資料尾收盤": qd(r_end), "進場→w1 期間最低收盤": qd(worst),
                "0050 同段（進場前一日收盤→w1）": qd(b_w1),
                "超額（等權平均 − 0050 平均）": float(np.mean(r_w1) - np.mean(b_w1)) if r_w1 else None}

    for H in (60, 120):
        sub_all = tail_rows[H]
        e2 = sub_all["entry_pos"].to_numpy(int)
        AND[f"H{H}"]["報酬（資料尾被丟列，全部）"] = rets(sub_all)
        AND[f"H{H}"]["報酬（資料尾被丟列，t−1 regime）"] = rets(sub_all[reg_t1[e2]])
    gb["報酬（補回列）"] = rets(gt)
    out["AND"] = AND
    out["門檻B"] = gb

    # ④ 0050 各尾段
    def seg(d0):
        a = int(cal.searchsorted(pd.Timestamp(d0)))
        b = bench[a - 1:w1 + 1]
        pk = np.maximum.accumulate(b)
        return {"起": str(cal[a].date()), "交易日數到w1": int(w1 - a + 1), "報酬（前一日收盤→w1）": float(bench[w1] / bench[a - 1] - 1),
                "段內最大回落": float(((b - pk) / pk).min())}
    b2 = bench[w1:]; pk2 = np.maximum.accumulate(b2)
    out["0050"] = {"門檻B 面板最後進場後": seg("2026-03-04"), "門檻B 函式丟尾起（2026-04-02）": seg("2026-04-02"),
                   "AND H120 丟尾起（2026-04-09）": seg("2026-04-09"), "AND H60 丟尾起（2026-07-03）": seg("2026-07-03"),
                   "w1→資料尾": {"報酬": float(bench[-1] / bench[w1] - 1), "段內最大回落": float(((b2 - pk2) / pk2).min())},
                   "主窗 年化／回落（錨）": list(RR.ANCHOR)}

    # 估計用常數（⛔ 估計，沒跑引擎）：年化改變 ≈ (1＋CAGR) × ln(1 ＋ κ × (L/H) × r̄) ÷ Y；κ 由 W1、F 的 V3 實測校準
    Y = (w1 - w0 + 1) / 245
    out["估計"] = {"Y（主窗年）": Y,
                   "W1 實測（AFCext V3 − V2）年化 pp": 1.64, "F 實測年化 pp": 2.67,
                   "說明": "κ＝實測 ÷ 以 r̄（補回列進場→w1 等權平均）與 L/H 算出的預測；AND 各格用同一 κ 帶入自己的 r̄、L/H"}
    rb = gb["報酬（補回列）"]["進場開盤→w1 收盤"].get("mean")
    if rb is not None:
        LH_B = (w1 - int(cal.searchsorted(pd.Timestamp("2026-05-05"))) + 1) / 120
        pred = lambda cagr, LH, r: (1 + cagr) * np.log1p(LH * r) / Y
        k_w1 = 0.0164 / pred(0.2749, LH_B, rb); k_f = 0.0267 / pred(0.2614, LH_B, rb)
        out["估計"]["門檻B L/H（補回段 05-05→w1）"] = LH_B
        out["估計"]["κ（W1／F）"] = [float(k_w1), float(k_f)]
        est = {}
        for H, d0 in ((120, "2026-04-09"), (60, "2026-07-03")):
            LH = min(1.0, (w1 - int(cal.searchsorted(pd.Timestamp(d0))) + 1) / H)
            for nm in ("全部", "t−1 regime"):
                r = AND[f"H{H}"][f"報酬（資料尾被丟列，{nm}）"]["進場開盤→w1 收盤"].get("mean")
                if r is None:
                    continue
                est[f"H{H}｜{nm}"] = {"L/H": LH, "r̄": r,
                                      "每 1＋CAGR＝1.30 的年化 pp（κ 取 W1／F）": [float(k * pred(0.30, LH, r) * 100) for k in (k_w1, k_f)]}
        out["估計"]["AND 各 H"] = est

    # ⑤ 既有引擎實測（resultsYear1M，⛔ 不重跑）：最近一年／今年以來兩窗，主版（T1 補回）vs 引擎原樣（丟尾）
    fw = pd.read_csv(os.path.join(BT, "resultsYear1M", "fixed_windows.csv"))
    fw = fw[fw["窗鍵"].isin(["L1Y", "YTD26"]) & (fw["版本"] != "—")]
    y1 = {}
    for (wk, cell), g in fw.groupby(["窗鍵", "格"]):
        m = g[g["版本"].str.startswith("主版")].iloc[0]; r = g[g["版本"].str.startswith("引擎原樣")].iloc[0]
        y1.setdefault(wk, {})[cell] = {"主版 報酬／回落": [float(m["窗內報酬_中位"]), float(m["最大回落_中位"])],
                                       "引擎原樣 報酬／回落": [float(r["窗內報酬_中位"]), float(r["最大回落_中位"])],
                                       "差 報酬／回落": [float(m["窗內報酬_中位"] - r["窗內報酬_中位"]), float(m["最大回落_中位"] - r["最大回落_中位"])]}
    out["Year1M 兩版對照（窗到 2026-09-24，含 w1 之後一個月）"] = y1

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: out[k] for k in ("日曆", "主窗")}, ensure_ascii=False))
    print(json.dumps(out["AND"], ensure_ascii=False, indent=1, default=str)[:6000])
    print(json.dumps(out["門檻B"], ensure_ascii=False, indent=1, default=str)[:3000])
    print(json.dumps(out["0050"], ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out["估計"], ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

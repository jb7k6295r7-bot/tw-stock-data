# -*- coding: utf-8 -*-
"""稽核 ② 8（seq1／seq3 §二 第 8 列；裁定 seq257 順 7）：突破後過濾（直接買）、限價（直接買）⇒ 20／60／120 都列判定格。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_8.py
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_8_check.py

原件：
  甲 突破過濾 researchBF.py（回測 PREREG突破過濾，1344491855）：判定只有 H60（14 格：Δ ＝ r(過濾) − r(A 直接買)、60 日區段 CR0）；
     H20、H120 只描述（body_events.csv.gz 已有逐筆 r20_*、r120_*）
  乙 限價 researchLimit.py（回測 PREREG限價，074d29f6c1）：判定只有 H20（3 格：D ＝ r(L_k) − r(M0)、量測月 CR0）；H120 只描述；H60 沒算
═══ 本件（⭐ 開跑前寫死）═══
  甲 H20：用既有逐筆 r20（⛔ 不重跑；原件 P3：終點 T＋20、進場日 ＞ T＋20 ⇒ 該臂記 0）⇒ 判定格；分群 ＝ T 的曆月（單筆層 H20 慣例；原件限價 L7 同）
     H60：原件判定照抄（重算驗逐位元）
  乙 H60：import researchLimit，HS 改 (20, 60, 120)，同一套 entries／exits（LE.exit_engine）／returns ⇒ H20、H120 逐筆 ＝ 原件 trades.csv.gz（閘）；
     H60 判定：分群 ＝ 以主窗起點切的 60 交易日區段（依 e；單筆層 H60 慣例，出口上限 ②）；n_eff ＝ min(n, 區段數)
  H120（甲、乙）：120 日區段上限 19 ⇒ n_eff ＜ 30 ⇒ 依構造不可判定（〈一百一十一〉附則：⛔ 不把區段切小）⇒ 照寫、只描述點估計
  Bonferroni：甲 H20 照原件 α ＝ 0.05／14；另報「三個 H 合計 28 格」的 α ＝ 0.05／28（描述；N 由裁定線定）
  出口／結果句：照各原件（甲 sentence、乙 LE.verdict）；「直接買」維持的條件 ＝ 沒有任何判定格落「過濾（限價）比較好」
  stop_force：兩件原件都 delist on（下市了結）＝ 停止交易強制出場：開；單筆層 ⇒ T1 不適用（甲：T ≤ 窗尾−60；乙：出場超出日曆者整列剔除，件數照報）
  「穩」：三個 H 的判定都不出現「過濾（限價）較好」才寫「直接買」穩
輸出 backtest/resultsAudit2/8/
"""
from __future__ import annotations

import json
import os
import sys
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchLimit as RL                      # ⭐ 原件（researchH2 已把 D.DATA 指到快照、chdir 到 repo）
import limit_entry as LE
from backtest import research11 as R11
import researchBF as BF

OUT = "backtest/resultsAudit2/8"
W0 = "2017-03-02"


def z_of(k):
    return NormalDist().inv_cdf(1 - 0.05 / k / 2)


def bf_cells(X, H, w0, zb):
    rows = []
    for typ in BF.TYPES:
        Y = X[X["type"] == typ]
        if H == 120:
            Y = Y[Y["in120"] == 1]
        T = pd.to_datetime(Y["T"])
        g = T.dt.strftime("%Y-%m").to_numpy() if H == 20 else (Y["blk"].to_numpy() if H == 60 else ((T.map(lambda d: POS[d]) - w0) // 120).to_numpy())
        for arm in BF.ARMS[typ]:
            d = (Y[f"r{H}_{arm}"] - Y[f"r{H}_A"]).to_numpy(float)
            cs = R11.cl_stats(d, g)
            n_ = int(len(d)); ng = int(cs["months"]); ne = min(n_, ng)
            ex = "出口①" if ne < 30 else ("出口②" if ne < 100 else "出口③")
            blo = cs["mean"] - zb * cs["se"]
            if H == 120:
                s, cat = "依構造不可判定（120 日區段 {} 段）".format(ng), "依構造不可判定"
            else:
                s, cat = BF.sentence(cs["mean"], cs["lo"], cs["hi"], blo, ex, BF.FNAME[arm])
            rows.append({"H": H, "型態": BF.NAME[typ], "買法": arm, "買法名": BF.ARM_NAME[arm], "事件數": n_, "群數": ng, "n_eff": ne, "出口": ex,
                         "E_A": float(Y[f"r{H}_A"].mean()), "E_過濾": float(Y[f"r{H}_{arm}"].mean()), "Δ": cs["mean"],
                         "CI95_lo": cs["lo"] if H != 120 else np.nan, "CI95_hi": cs["hi"] if H != 120 else np.nan,
                         "Bonf_lo": blo if H != 120 else np.nan, "Bonf28_lo": (cs["mean"] - z_of(28) * cs["se"]) if H != 120 else np.nan,
                         "結果類": cat, "結果句": s})
    return pd.DataFrame(rows)


POS = {}


def main():
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_8（突破過濾、限價：20／60／120）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    S_ = {"原件": {"甲 突破過濾": "researchBF.py 1344491855", "乙 限價": "researchLimit.py 074d29f6c1"}, "閘": {}}
    # ── 甲
    D = RL.D
    cal = D.load_calendar(); w0 = int(cal.searchsorted(pd.Timestamp(W0)))
    POS.update({pd.Timestamp(d): i for i, d in enumerate(cal)})
    X = pd.read_csv("backtest/resultsBF/body_events.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    C60 = bf_cells(X, 60, w0, z_of(14))
    ref = pd.read_csv("backtest/resultsBF/body_cells.csv", float_precision="round_trip")
    S_["閘"]["甲 H60 14 格 Δ／CI／結果類 ＝ 原件 body_cells（逐位元）"] = bool(
        all(repr(float(a)) == repr(float(b)) for a, b in zip(C60["Δ"], ref["Δ"])) and all(repr(float(a)) == repr(float(b)) for a, b in zip(C60["CI95_lo"], ref["CI95_lo"]))
        and (C60["結果類"].values == ref["結果類"].values).all())
    C20 = bf_cells(X, 20, w0, z_of(14)); C120 = bf_cells(X, 120, w0, z_of(14))
    CB = pd.concat([C20, C60, C120], ignore_index=True)
    CB.to_csv(os.path.join(OUT, "bf_cells.csv"), index=False, float_format="%.17g")
    log(f"[甲] 閘 {S_['閘']}\n" + CB[["H", "型態", "買法", "Δ", "CI95_lo", "CI95_hi", "出口", "結果類"]].to_string())
    # ── 乙
    RL.HS = (20, 60, 120)
    S = RL.setup()
    E = RL.entries(S)
    for k in LE.KS:
        E[f"L{k}_F"] = [S["RAW"][s]["F"][int(t)] if np.isfinite(t) else np.nan for s, t in zip(E["sid"], E[f"L{k}_t"])]
    E = RL.exits(S, E)
    E = RL.returns(E, S)
    old = pd.read_csv("backtest/resultsLimit/trades.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    gl = {}
    for H in (20, 120):
        for a in RL.ARMS:
            u, v = E[f"r{H}_{a}"].to_numpy(float), old[f"r{H}_{a}"].to_numpy(float)
            gl[f"r{H}_{a}"] = int(sum(not ((np.isnan(p) and np.isnan(q)) or repr(float(p)) == repr(float(q))) for p, q in zip(u, v)))
    S_["閘"]["乙 H20／H120 逐筆 ＝ 原件 trades（不逐位元列數）"] = gl
    S_["閘"]["乙 訊號數"] = [len(E), len(old)]
    log(f"[乙 閘] {gl}")
    if len(E) != len(old) or any(gl.values()):
        json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        raise SystemExit("⛔ 乙 閘不過")
    J = {}
    for H in (20, 60, 120):
        ok_st = E[f"x{H}_status"].value_counts().to_dict()
        for k in LE.KS:
            a = f"L{k}"
            d = E[f"r{H}_{a}"] - E[f"r{H}_M0"]; ok = d.notna()
            x = d[ok].to_numpy(float)
            g = E.loc[ok, "month"].to_numpy() if H == 20 else ((E.loc[ok, "e"].to_numpy(int) - w0) // H)
            cs = R11.cl_stats(x, g)
            ne = int(min(len(x), cs["months"]))
            if H == 120:
                ex, res = "出口①", RL.H120_SENTENCE
            else:
                ex, res = LE.verdict(cs["mean"], cs["lo"], cs["hi"], ne, len(x))
            J[f"H{H}_{a}"] = {"n": int(len(x)), "群數": int(cs["months"]), "n_eff": ne, "D": float(cs["mean"]),
                             "lo": float(cs["lo"]) if H != 120 else None, "hi": float(cs["hi"]) if H != 120 else None,
                             "E_臂": float(E.loc[ok, f"r{H}_{a}"].mean()), "E_M0": float(E.loc[ok, f"r{H}_M0"].mean()), "出口": ex, "結果": res,
                             "出場狀態": ok_st}
            log(f"[乙 H{H} {a}] n {len(x)}｜D {cs['mean']:+.3%} [{cs['lo']:+.3%}, {cs['hi']:+.3%}]｜{ex} {res}")
    ref20 = json.load(open("backtest/resultsLimit/summary.json", encoding="utf-8"))["判定_H20"]
    S_["閘"]["乙 H20 三格 D ＝ 原件 summary"] = {k: (abs(J[f"H20_L{k[-1]}"]["D"] - v["D"]) < 1e-15) for k, v in (ref20.items() if isinstance(ref20, dict) else [])}
    E[["i", "sid", "e", "month", "x60_status", "x60_t", "x60_px"] + [f"r60_{a}" for a in RL.ARMS]].to_csv(os.path.join(OUT, "limit_h60.csv.gz"), index=False, float_format="%.17g")
    S_["乙 限價"] = J
    S_["甲 突破過濾 結果類計數"] = {f"H{H}": CB[CB["H"] == H]["結果類"].value_counts().to_dict() for H in (20, 60, 120)}
    S_["直接買 穩（兩件、H20／H60 皆無「過濾／限價較好」）"] = bool(
        not CB[CB["H"] != 120]["結果類"].isin(["加過濾比較好"]).any() and not any(v["結果"].startswith("結果②") for k, v in J.items() if not k.startswith("H120")))
    json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

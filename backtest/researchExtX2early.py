# -*- coding: utf-8 -*-
"""PREREG外部三件 X2（CGO＋低波動，TEJ）早年段補跑（只上市）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtX2early.py [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchExtX2early_check.py

依據：台股策略線 外部三件 登錄 seq1（sha d412ffe18178b3be）§三「早年段用 data/early（只上市）」；裁定 seq245 §二（X2 ⛔ 不計 N、全段描述＋前瞻紀錄；
      結果句必附「原文期間內、等於已看過」）⇒ ⭐ 早年段照登錄與裁定 ＝【描述】，⛔ 不判、不計 N。
原件：researchExt.py（9e752a6247）X2：主窗描述 5 個月 +15.99%／−22.97%；早年段當時缺 shares 沒跑。
資料：tw-stock-data main 950ad26e12（資料庫線 0254：data/early/daily 上市列 shares 補齊 2004-02-11～2014-12-31）
      ⇒ early_data.body_build(950ad26e12, "main")（git archive 唯讀）⇒ ~/earlydata/950ad26e12/main/data；
      ⭐ 與 3edc0e2206/main 比：除 stocks/*.csv 的 shares 欄外逐檔逐位元相同（本檔另驗），shares 有值 29% → 99%
═══ 照原件、⛔ 不改 ═══
  import researchExt：load_one（A1 CGO、A2 TV100、A3 年齡 ≥ 100 根）、pick_at 同式（A4：TV100 升冪前 ⌈10%⌉ ⇒ CGO 降冪前 50）、
  換股 A5（月初開盤進、下一個換股日前一交易日收盤出；5 個月以 2005-01 起算的節奏）、引擎 research11.simulate_mtm（n_slots 50、cash zero、tradable＋delist）
═══ 本件加（⭐ 開跑前寫死）═══
  母體 ＝ 早年版面 gate3（只上市；含已下市、上市→上櫃者以上市末日為止）
  ⭐ 停止交易強制出場：開（research11.stop_force_days(valid, 窗尾)）；原件主窗沒開 ⇒ 本件另報「關」版對照
  資料尾：最後一期出場 ＝ 日曆最後一日（2014-12-31）收盤 ⇒ 沒有超出資料尾的出場（照實寫）
  窗：⭐ 描述窗 ＝ 2005-01-03～2014-12-31（原文期間內）；另報 2004 殘段（原文期間外、不足 1 年：只報期間報酬）
  0050 同窗（早年版面還原收盤）；標籤只描述（⛔ 不判）
  描述：只含存活股（早年版面內未下市）、假訊號臂（低波動池隨機 50 檔、30 次、種子 20260925＋r，同原件）
輸出 backtest/resultsExtX2early/
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExt as X                              # ⭐ 原件（import 時 researchH2 把 D.DATA 指到主快照；下面改指早年版面）
D, TR, UG, R11 = X.D, X.TR, X.UG, X.R11
from backtest import rerun17 as RR

OUT = "backtest/resultsExtX2early"
EARLY_SHA = "950ad26e1293592457ec28194f0c5eaebfd3e53b"
DATA = os.path.expanduser("~/earlydata/950ad26e12/main/data")
DESC = ("2005-01-03", "2014-12-31")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    st = json.load(open(os.path.join(os.path.dirname(DATA), "STATUS.json"), encoding="utf-8"))
    if not (st.get("complete") and st.get("sha") == EARLY_SHA):
        raise SystemExit("⛔ 早年版面不是 950ad26e12 或不完整")
    D.DATA = DATA
    log(f"===== researchExtX2early {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜資料 {DATA}（{EARLY_SHA[:10]}）=====")
    cal = D.load_calendar(); n = len(cal)
    per = cal.to_period("M"); mfirst = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    U = UG.gate3(pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str))
    off = TR.load_official(); X._G["off"] = off
    with Pool(a.procs, initializer=X._init, initargs=(cal, mfirst, None)) as pool:
        res = pool.map(X.load_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}; sids = sorted(ST)
    log(f"[讀檔] gate3 {len(U):,}｜可用 {len(ST):,}｜市場 {pd.Series([ST[s]['market'] for s in sids]).value_counts().to_dict()}")
    months = [k for k, d in enumerate(mfirst) if d > 0]

    def pick_at(k, surv=False):
        rows = [(s, ST[s]["tv"][k], ST[s]["cgo"][k]) for s in sids if ST[s]["age"][k] >= 100 and np.isfinite(ST[s]["tv"][k]) and np.isfinite(ST[s]["cgo"][k])
                and (not surv or not ST[s]["delisted"])]
        if not rows:
            return [], [], 0
        rows.sort(key=lambda r: (r[1], r[0]))
        lv = rows[:math.ceil(X.LOWVOL * len(rows))]
        top = sorted(lv, key=lambda r: (-r[2], r[0]))[:X.N_PICK]
        return [r[0] for r in top], [r[0] for r in lv], len(rows)
    sel = {k: pick_at(k) for k in months}
    first_k = min(k for k in months if sel[k][2] > 0)
    base_m = 2005 * 12
    closes = {s: pd.Series(ST[s]["c"]).ffill().to_numpy() for s in sids}; opens = {s: ST[s]["o"] for s in sids}
    trad = {s: {"trd": ST[s]["trd"], "up_o": ST[s]["up_o"], "dn_o": ST[s]["dn_o"], "dn_c": ST[s]["dn_c"]} for s in sids}
    dl = TR.delist_status({s: trad[s] for s in sids}, cal, official=off)
    w1 = n - 1
    SF = R11.stop_force_days({s: ST[s]["valid"] for s in sids}, w1)
    d0, d1 = int(cal.searchsorted(pd.Timestamp(DESC[0]))), int(cal.searchsorted(pd.Timestamp(DESC[1]), side="right") - 1)
    bench = RR.load_bench(cal)
    c50, m50, _ = RR.win_metrics(bench, 0, n, d0, d1)
    shares_na = int(sum(1 for s in sids for k in months if ST[s]["age"][k] >= 100 and np.isfinite(ST[s]["tv"][k]) and not np.isfinite(ST[s]["cgo"][k])))
    S = {"依據": "登錄 d412ffe18178b3be §三；裁定 seq245 §二（X2 不計 N、全段描述）⇒ 早年段 ＝ 描述", "資料": f"{DATA}（tw-stock-data {EARLY_SHA}）",
         "母體": {"gate3 早年（只上市）": int(len(U)), "可用": len(ST), "每月初母體中位": float(np.median([sel[k][2] for k in months if sel[k][2] > 0])),
                "低波動池中位": float(np.median([len(sel[k][1]) for k in months if sel[k][2] > 0])), "第一個可選月": str(cal[mfirst[first_k]].date()),
                "V>1截到1的股日": int(sum(ST[s]["v_gt1"] for s in sids)), "TV100可算而CGO不可算（shares 缺等）的股-月": shares_na},
         "停止交易（窗尾前）檔數": len(SF), "0050同窗（描述窗）": {"年化": c50, "回落": m50, "比值": c50 / abs(m50)}, "描述窗": list(DESC), "X2": {}}
    log(f"[母體] {S['母體']}｜0050 {c50:+.2%}／{m50:+.2%}")

    def sig_of(cad, surv=False, rng=None):
        rb = [k for k in months if k >= first_k and (cal[mfirst[k]].year * 12 + cal[mfirst[k]].month - 1 - base_m) % cad == 0]
        rows = []
        for i, k in enumerate(rb):
            e = mfirst[k]
            if rng is None:
                names = pick_at(k, True)[0] if surv else sel[k][0]
            else:
                pool_ = sel[k][1]
                names = list(rng.choice(pool_, size=min(X.N_PICK, len(pool_)), replace=False)) if pool_ else []
            x = (mfirst[rb[i + 1]] - 1) if i + 1 < len(rb) else n - 1
            for s in names:
                o_ = opens[s][e]; c_ = closes[s][x]
                if not (np.isfinite(o_) and o_ > 0 and np.isfinite(c_)):
                    continue
                rows.append({"sid": s, "entry_pos": e, "xpos_X": x, "g_X": c_ / o_ - 1.0, "month": cal[e].strftime("%Y-%m")})
        return pd.DataFrame(rows), rb

    def run(sig, sf=True):
        return R11.simulate_mtm(sig, "X", X.N_PICK, np.random.default_rng(0), closes, opens, n, return_equity=True, pick=None, d_max=None,
                                queue_days=0, cash_mode="zero", tradable=trad, delist=dl, stop_force=SF if sf else None)
    EQ = {}; x2 = {}
    for nm, cad in X.CAD.items():
        sg, rb = sig_of(cad)
        o_ = run(sg); eq = o_["equity"]
        c, m, _ = RR.win_metrics(eq, 0, n, d0, d1)
        e0 = mfirst[rb[0]]
        r04 = float(eq[min(d0 - 1, n - 1)] / eq[e0 - 1] - 1) if e0 < d0 else None
        b04 = float(bench[d0 - 1] / bench[e0 - 1] - 1) if e0 < d0 else None
        o2 = run(sg, sf=False); c2, m2, _ = RR.win_metrics(o2["equity"], 0, n, d0, d1)
        x2[nm] = {"年化": c, "回落": m, "比值": c / abs(m), "標籤（描述，⛔ 不判）": X.label(c, m, c50, m50), "換股次數": len(rb),
                  "第一次換股": str(cal[e0].date()), "2004 殘段期間報酬（原文期間外、不足 1 年）": r04, "0050 同段": b04,
                  "停止交易強制出場筆": int(o_.get("x_stop_force_n", 0)), "stop_force 關（對照）": {"年化": c2, "回落": m2}}
        EQ[nm] = eq
        log(f"[X2 {nm}] 描述窗 {c:+.2%}／{m:+.2%}（{c / abs(m):.3f}）{x2[nm]['標籤（描述，⛔ 不判）']}｜2004 殘段 {r04}｜stop_force 關 {c2:+.2%}／{m2:+.2%}")
    sg, _ = sig_of(5, surv=True); o_ = run(sg); c, m, _ = RR.win_metrics(o_["equity"], 0, n, d0, d1)
    x2["只含存活股（描述，5個月）"] = {"年化": c, "回落": m, "比值": c / abs(m)}
    fk = []
    for r in range(30):
        sg, _ = sig_of(5, rng=np.random.default_rng(20260925 + r)); o_ = run(sg); c, m, _ = RR.win_metrics(o_["equity"], 0, n, d0, d1)
        fk.append({"r": r, "年化": c, "回落": m, "標籤": X.label(c, m, c50, m50)})
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "fake_arm.csv"), index=False, float_format="%.17g")
    x2["假訊號臂_低波動池隨機50檔（描述，5個月，30次）"] = {"年化中位": float(FK["年化"].median()), "回落中位": float(FK["回落"].median()),
                                              "主格年化的百分位": float((FK["年化"] < x2["5個月（主格）"]["年化"]).mean() * 100), "標籤分佈": FK["標籤"].value_counts().to_dict()}
    S["X2"] = x2
    S["主窗（原件 9e752a6247，描述）"] = {"5個月": "+15.99%／−22.97% 不合格", "0050 主窗": "+24.02%／−33.96%"}
    S["必附"] = "原文期間內、等於已看過；出處為公開研究、原文數字未必可重現"
    pd.DataFrame([{"換股日": str(cal[mfirst[k]].date()), "名次": i + 1, "sid": s} for k in months if sel[k][0] for i, s in enumerate(sel[k][0])]).to_csv(
        os.path.join(OUT, "picks_monthly.csv.gz"), index=False)
    pd.DataFrame({"date": [str(d.date()) for d in cal], "0050": bench, **{f"X2_{k}": v for k, v in EQ.items()}}).to_csv(
        os.path.join(OUT, "equity.csv.gz"), index=False, float_format="%.17g")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

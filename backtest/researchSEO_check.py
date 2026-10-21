# -*- coding: utf-8 -*-
"""現金增資、可轉債公告後偏弱 seq2 正式跑【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsSEO/（freq/ 外）與資料，不寫任何既有檔；
輸出 resultsSEO/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSEO_check

C1 策略鎖相符（25 支）。
C2 頻率表逐列重建：recon_freq.csv 18 欄全 0 不同；正式跑保留事件 ＝ 頻率表 st＝保留（exright 差異列另計）。
C3 抽 12 筆手算（S、C 主窗 1 年）：事件與配對公司 R 用 Indep 逐根迴圈重算 ⇒ X（容差 1e−9）。
C4 配對合法：配對公司 ≠ 發行公司；在 [公告日 − 3 年, ＋3 年] 內事件表全部列（任何 class）都沒有它；與發行公司同 T 市值十分位（主配對另要同前 12 個月報酬五分位）；
   e 進場保留（exright 版）；是同池中 e 可買者裡市值最接近者。
C5 不前視：T ＜ e、日曆[T] ≤ 公告日 ＜ 日曆[e]；前 12 個月報酬窗只到 T。
C6 彙總：SEO_表.csv 判定（描述）列 n、n_eff、X̄、lo、hi 由 events 重算（容差 1e−12）。
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSEO as SX                      # noqa: E402
from backtest import researchSEO_freq as SQ                 # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom_check as IC             # noqa: E402

OUT = SX.OUT
LOG = IC.LOG
OK = IC.OK
log = IC.log
chk = IC.chk


def main():
    IC.lock_check()
    EV = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str, "配對公司": str})
    TB = pd.read_csv(os.path.join(OUT, "SEO_表.csv"))
    RC = pd.read_csv(os.path.join(OUT, "recon_freq.csv"))
    EXD = pd.read_csv(os.path.join(OUT, "exright_diff.csv"), dtype=str)
    EF = pd.read_csv(os.path.join(SX.FREQ_DIR, "events.csv.gz"), dtype=str, keep_default_na=False)
    chk("C2a recon_freq 18 欄全同", len(RC) == 18 and int(RC["不同列數"].sum()) == 0)
    kf = set(zip(EF.loc[EF["st"] == "保留", "sid"], EF.loc[EF["st"] == "保留", "date"], EF.loc[EF["st"] == "保留", "組"]))
    km = set(zip(EV["sid"], EV["date"], EV["組"]))
    exs = set(zip(EXD["sid"], EXD["date"], EXD["組"])) if len(EXD) else set()
    chk("C2b 保留事件 ＝ 頻率表 st＝保留", len({k for k in kf ^ km if k not in exs}) == 0, f"頻率表 {len(kf)}、本檔 {len(km)}、exright 差異 {len(exs)}")
    DATA = IMX.pinned_data(SX.PIN_SHA)
    ev = SQ.load_events(DATA)
    iss = defaultdict(list)
    for s, d in zip(ev["stock_id"], ev["d"]):
        iss[s].append(d)
    Zo = IMX.aux2(IM.panel_aux(IM.build_panel("主", 2)))
    Zx = IMX.make_x(Zo, IMX.build_exr(Zo))
    cal = Zx["cal"]; ix = {s: i for i, s in enumerate(Zx["sids"])}
    IP = IC.Indep("主")
    rng = np.random.default_rng(20261021)
    m12 = EV[(EV["世界"] == "主") & (EV["H12"] == "ok") & EV["組"].isin(["S", "C"])]
    errs = []
    for _, r in m12.iloc[rng.choice(len(m12), 12, replace=False)].iterrows():
        e = int(cal.searchsorted(pd.Timestamp(r["e"]))); x = int(cal.searchsorted(pd.Timestamp(r["e"]) + pd.DateOffset(months=12), side="right")) - 1
        Re, _ = IP.ret(r["sid"], e, x); Rm, _ = IP.ret(r["配對公司"], e, x)
        errs.append(max(abs(Re - r["R12"]), abs(Rm - r["R配對12"]), abs(Re - Rm - r["X12"])))
        log(f"   {r['組']} {r['date']} {r['sid']}↔{r['配對公司']}：X {Re - Rm:+.6f}／{r['X12']:+.6f}")
    chk("C3 抽 12 筆 事件／配對 R、X 手算", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
    # C4、C5
    bad = defaultdict(int); memo = {}
    sub = EV[(EV["世界"] == "主") & EV["配對實際"].isin(["主配對", "放寬配對"])]
    for _, r in sub.iterrows():
        d = pd.Timestamp(r["date"]); e = int(cal.searchsorted(pd.Timestamp(r["e"]))); T = e - 1
        bad["T<e∧日曆T≤d<日曆e"] += not (cal[T] <= d < cal[e])
        m = r["配對公司"]; i = ix[r["sid"]]; j = ix[m]
        bad["≠自己"] += m == r["sid"]
        lo, hi = d - pd.DateOffset(years=3), d + pd.DateOffset(years=3)
        bad["±3年非發行"] += any(lo <= q <= hi for q in iss.get(m, []))
        out, qm, qr = SQ.xsec(Zx, T, memo)
        dm = lambda k: int(np.searchsorted(qm, out[k][0], "right")); dr = lambda k: int(np.searchsorted(qr, out[k][1], "right"))
        bad["同市值十分位"] += dm(i) != dm(j)
        if r["配對實際"] == "主配對":
            bad["主配對同報酬五分位"] += dr(i) != dr(j)
        bad["配對e保留"] += IM.entry_flag(Zx, j, T, e) != "保留"
        # 最近可買
        def non(k):
            s = Zx["sids"][k]
            return not any(lo <= q <= hi for q in iss.get(s, []))
        pool = [k for k in out if k != i and non(k) and dm(k) == dm(i) and (r["配對實際"] == "放寬配對" or dr(k) == dr(i))
                and IM.entry_flag(Zx, k, T, e) == "保留"]
        best = min(pool, key=lambda k: (abs(out[k][0] - out[i][0]), Zx["sids"][k]))
        bad["最近可買"] += best != j
    for k, v in bad.items():
        log(f"   C4／C5 {k}：違反 {v}／{len(sub)}")
    chk("C4 配對合法（≠自己、±3年非發行、同十分位／五分位、可買、最近）", all(v == 0 for k, v in bad.items() if k != "T<e∧日曆T≤d<日曆e"), json.dumps(dict(bad), ensure_ascii=False))
    chk("C5 不前視 日曆[T] ≤ 公告日 ＜ 日曆[e]", bad["T<e∧日曆T≤d<日曆e"] == 0)
    # C6
    worst = 0.0; nb = 0
    edt = pd.to_datetime(EV["e"])
    for _, r in TB[TB["身分"] == "判定(描述)"].iterrows():
        x_, y_ = SX.SEGS[r["段"]]
        insg = (edt >= pd.Timestamp(x_)) & (edt <= (cal[-1] if y_ is None else pd.Timestamp(y_)))
        g = EV[insg & (EV["組"] == r["組"]) & (EV["H12"] == "ok")]
        st = IMX.stats(g["X12"], g["公告月"])
        for k in ("X̄", "lo", "hi"):
            worst = max(worst, abs(st[k] - r[k]))
        nb += (st["n"] != r["n"]) or (st["n_eff"] != r["n_eff"]) or (st["結果"] != r["結果"])
    chk("C6 判定（描述）列重算", worst < 1e-12 and nb == 0, f"最大誤差 {worst:.2e}、不符 {nb}")
    allok = all(OK.values())
    log(f"{'✅ 全部通過' if allok else '❌ 有不通過'}（{sum(OK.values())}／{len(OK)}）")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

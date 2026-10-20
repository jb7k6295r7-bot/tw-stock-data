# -*- coding: utf-8 -*-
"""researchFinQ_freq 對帳（獨立寫法；⛔ 不讀、不算任何進場後報酬）——回測線計算子代理，2026-10-21。
 C1 登錄 sha 獨立重算
 C2 抽樣手算：picks 抽 40 列（default_rng(20261021)），用 csv 模組直接讀 fs_xbrl_<FY>.csv 原檔重算 Q-A、Q-I（cr 優先）⇒ 相對差 ≤ 1e−12、有無值相同
 C3 十分位重選：每年由 picks 的值獨立排序、⌈n/10⌉、同值併入 ⇒ 入選旗標全同
 C4 不前視：全部有值列，用 filing_dates.csv 原檔（AI1 優先、取最早）查 FY Y−1、Y−2 上傳日 ≤ 排序日 t；FY 期末 ＜ t ⇒ 違反 0 筆
 C5 500 張閘：每年抽 3 檔母體股，重讀 research11.load_bars＋patterns.Frame.gate[t]∧pit_valid ⇒ 皆真
 C6 策略鎖相符
輸出 backtest/resultsFinQ/freq/check.json
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom_freq_check as IC        # noqa: E402  sha、策略鎖（新檔）
from backtest import researchFinQ_freq as FQ                # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import patterns as P                          # noqa: E402

OUT = FQ.OUT


def raw_q4(DATA, fy, sid):
    p = os.path.join(DATA, "meta", "fs_xbrl", f"fs_xbrl_{fy}.csv")
    if not os.path.exists(p):
        return None
    rows = [r for r in csv.DictReader(open(p, encoding="utf-8")) if r["stock_id"] == sid and r["period"] == f"{fy}Q4"]
    if not rows:
        return None
    rows.sort(key=lambda r: r["report"] != "cr")
    f = lambda x: float(x) if x not in ("", None) else float("nan")
    r = rows[0]
    return {"ta": f(r["total_assets"]), "ni": f(r["net_income_ytd"]), "ocf": f(r["operating_cash_flow_ytd"])}


def main():
    CK = {"C1_登錄sha": IC.reg_ok(FQ.REG_SHA)}
    sha, DATA = IM.ensure_main()
    with gzip.open(os.path.join(OUT, "picks.csv.gz"), "rt", encoding="utf-8") as fh:
        PK = pd.read_csv(fh, dtype={"sid": str})
    BY = pd.read_csv(os.path.join(OUT, "by_year.csv"))
    tmap = dict(zip(BY["排序年"], BY["排序日t"]))
    rng = np.random.default_rng(20261021)
    # C2
    C2 = []
    for k in rng.choice(len(PK), 40, replace=False):
        r = PK.iloc[int(k)]; Y = int(r["排序年"]); s = r["sid"]
        a = raw_q4(DATA, Y - 1, s); b = raw_q4(DATA, Y - 2, s)
        qi = qa = float("nan")
        if a and b and a["ta"] > 0 and b["ta"] > 0:
            qi = a["ta"] / b["ta"] - 1
            if not (math.isnan(a["ni"]) or math.isnan(a["ocf"])):
                qa = (a["ni"] - a["ocf"]) / ((a["ta"] + b["ta"]) / 2)

        def same(x, y):
            return (math.isnan(x) and math.isnan(y)) or (not math.isnan(x) and not math.isnan(y) and abs(x - y) <= 1e-12 * max(1, abs(y)))
        C2.append({"排序年": Y, "sid": s, "Q-A(手/主)": [qa, r["Q-A"]], "Q-I(手/主)": [qi, r["Q-I"]], "相同": bool(same(qa, float(r["Q-A"])) and same(qi, float(r["Q-I"])))})
    CK["C2_手算"] = C2
    # C3
    C3 = []
    for Y, g in PK.groupby("排序年"):
        for c in ("Q-A", "Q-I"):
            v = g[c].to_numpy(float); m = np.isfinite(v)
            if m.sum() == 0:
                C3.append({"排序年": int(Y), "格": c, "有值": 0, "相同": not g[f"{c}入選"].any()}); continue
            n = int(m.sum()); k = math.ceil(n / 10); cut = sorted(v[m])[k - 1]
            mine = m & (v <= cut)
            C3.append({"排序年": int(Y), "格": c, "有值": n, "入選": int(mine.sum()), "相同": bool((mine == g[f"{c}入選"].to_numpy(bool)).all())})
    CK["C3_十分位重選"] = C3
    # C4
    fd = {}
    for r in csv.DictReader(open(os.path.join(DATA, "meta", "filing_dates.csv"), encoding="utf-8")):
        if r["season"] != "4" or not r["uploaded_at"]:
            continue
        key = (r["stock_id"], int(r["year"]))
        cand = (0 if r["doc_code"] == "AI1" else 1, r["uploaded_at"])
        if key not in fd or cand < fd[key]:
            fd[key] = cand
    viol = 0; nchk = 0
    for Y, s, qa, qi in zip(PK["排序年"], PK["sid"], PK["Q-A"], PK["Q-I"]):
        t = tmap[int(Y)]
        need = [Y - 1] + ([Y - 2] if np.isfinite(qi) or np.isfinite(qa) else [])
        for fy in need:
            nchk += 1
            u = fd.get((s, int(fy)))
            if u is None or u[1][:10] > t or f"{int(fy)}-12-31" >= t:
                viol += 1
    CK["C4_不前視"] = {"檢查筆": nchk, "違反": viol}
    # C5
    C5 = []
    W = {wn: AT.load_world(wn) for wn in ("早年", "主")}
    import backtest.data as D
    for Y, g in PK.groupby("排序年"):
        wn = "早年" if Y <= 2014 else "主"; Wd = W[wn]; D.DATA = Wd["data"]; cal = Wd["cal"]
        t = int(cal.searchsorted(pd.Timestamp(tmap[int(Y)])))
        for s in rng.choice(g["sid"].to_numpy(), 3, replace=False):
            B = R.load_bars(s, Wd["mk"].get(s, "twse"), cal)
            ok = B is not None and bool(np.asarray(P.Frame(B["df"], set()).gate, bool)[t]) and bool(Wd["PV"][Wd["ix"][s]][t])
            C5.append({"排序年": int(Y), "sid": s, "閘內": ok})
    CK["C5_500張閘"] = C5
    CK["C6_策略鎖"] = IC.lock_ok()
    CK["全過"] = bool(CK["C1_登錄sha"][0] and all(x["相同"] for x in C2) and all(x["相同"] for x in C3) and viol == 0
                    and all(x["閘內"] for x in C5) and CK["C6_策略鎖"][0])
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("全過" if CK["全過"] else "⛔ 有不符", {"C2不同": sum(not x["相同"] for x in C2), "C3不同": sum(not x["相同"] for x in C3), "C4違反": viol,
                                            "C5閘外": sum(not x["閘內"] for x in C5), "鎖": CK["C6_策略鎖"]})


if __name__ == "__main__":
    main()

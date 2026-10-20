# -*- coding: utf-8 -*-
"""researchDelistRev 獨立查核（回測線計算子代理，2026-10-21）。⛔ 不改任何檔；只寫 resultsDelistRev/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDelistRev_check [--procs 2]

 K1 策略鎖：python -m backtest.strategy_lock --check 必須 exit 0
 K2 summary.json 所有閘 ＝ 0
 K3 null AND 檔 ＝ 定版 sig_edc6f/and_signals.csv.gz（解壓逐位元組，重驗一次）
 K4 注入列可用日（獨立算，不呼叫 research34）：抽樣 40 列 finmind 來源＋全部 15 日口徑列；
    進場日 ＝ 期別次月 10 日（2026-01 期起 15 日）之後第一個交易日、訊號日 ＝ 前一交易日；訊號日必須 ＞ 期末
 K5 新增 AND 列（獨立重算，不呼叫 research34／research13）：原始 revenue_hist＋revenue_delisted 合併後，訊號日前 45 個交易日內存在一期
    「當月 ≥ 前 24 個月最大、24 個月都有值」且可用 ⇒ 每一筆新增列都要成立
 K6 交易重算（不經 researchYL_integrate）：rerun17.setup_and(t1) ＋ simulate_mtm 直呼；merged_a／merged_b 的營量 r0、營飆 r ∈ {0, 99, 199} eq_sha ＝ seeds.csv.gz
 K7 ⓑ 補出場列：末根日 ＝ 快照 stocks.csv 的 last_seen（確實是停止交易，不是停牌中段）
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR                           # noqa: E402

RR.use_snapshot()
from backtest import data as D                               # noqa: E402
from backtest import research11 as R                         # noqa: E402

OUT = "backtest/resultsDelistRev"
DLD = os.path.expanduser("~/dlrevdata/1ab51f2820")
LOCK = os.path.join(RR.OUT, "sig_edc6f")


def sha16(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.parse_args()
    K = {}; logf = open(os.path.join(OUT, "check.log"), "a", encoding="utf-8")

    def log(m):
        print(m, flush=True); logf.write(m + "\n"); logf.flush()
    # K1
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    K["K1 策略鎖 --check exit"] = p.returncode
    log(f"[K1] exit {p.returncode}｜{(p.stdout + p.stderr).strip()[-300:]}")
    # K2
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    K["K2 summary 閘非 0 項數"] = int(sum(v != 0 for v in S["閘"].values()))
    # K3
    K["K3 null AND ≠ 定版"] = int(gzip.open(os.path.join(OUT, "sig_null", "and_signals.csv.gz")).read() != gzip.open(os.path.join(LOCK, "and_signals.csv.gz")).read())
    # K4
    cal = D.load_calendar(); cd = cal.normalize()
    inj = pd.read_csv(os.path.join(OUT, "sig_merged", "panel_injected_rows.csv.gz"), dtype={"stock_id": str, "period": str})
    fm = inj[inj["rev_src"] == "finmind"]
    smp = pd.concat([fm.sample(min(40, len(fm)), random_state=20261021), fm[fm["period"] >= "2026-01"]]).drop_duplicates(["stock_id", "period"])
    bad4 = []
    for s, per, sp, ep in zip(smp["stock_id"], smp["period"], smp["signal_pos"], smp["entry_pos"]):
        y, m = int(per[:4]), int(per[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        day = 15 if per >= "2026-01" else 10
        cut = pd.Timestamp(year=y2, month=m2, day=day)
        e = int(np.flatnonzero(cd > cut)[0]); pend = pd.Timestamp(year=y2, month=m2, day=1)
        if not (e == int(ep) and e - 1 == int(sp) and cd[int(sp)] >= pend):
            bad4.append((s, per, int(sp), int(ep), e))
    K["K4 可用日抽樣（列數）"] = int(len(smp)); K["K4 可用日不符"] = len(bad4)
    K["K4 15 日口徑列"] = int((smp["period"] >= "2026-01").sum())
    K["K4 抽樣例"] = [f"{s} {per} 訊號 {cal[int(sp)].date()} 進場 {cal[int(ep)].date()}" for s, per, sp, ep in
                    zip(smp["stock_id"][:5], smp["period"][:5], smp["signal_pos"][:5], smp["entry_pos"][:5])]
    log(f"[K4] {len(smp)} 列｜不符 {bad4[:5]}")
    # K5
    fs = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    rh = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
    rh["v"] = pd.to_numeric(rh["當月營收"], errors="coerce")
    dl = pd.read_csv(os.path.join(DLD, "revenue_delisted", "revenue_delisted.csv"), dtype={"stock_id": str, "period": str})
    periods = sorted(rh["period"].unique())
    new = pd.read_csv(os.path.join(OUT, "new_signals.csv"), dtype={"sid": str})
    ok5 = 0; bad5 = []
    for s, g in new.groupby("sid"):
        a = rh[rh["stock_id"] == s].set_index("period")["v"].reindex(periods)
        b = dl[dl["stock_id"] == s].set_index("period")["revenue_k"].astype(float).reindex(periods)
        v = a.where(a.notna(), b).to_numpy(float)
        sigpos = []
        for per in periods:
            y, m = int(per[:4]), int(per[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            src15 = per >= "2026-01" and np.isnan(a[per])
            cut = pd.Timestamp(year=y2, month=m2, day=15 if src15 else 10)
            ii = np.flatnonzero(cd > cut)
            sigpos.append(int(ii[0]) - 1 if len(ii) else 10 ** 9)
        sigpos = np.array(sigpos)
        hi = np.array([j >= 24 and np.all(np.isfinite(v[j - 24:j])) and np.isfinite(v[j]) and v[j] >= np.max(v[j - 24:j]) for j in range(len(v))])
        for k, pos in zip(g["k"], g["pos"]):
            okp = (sigpos <= pos) & (pos - sigpos <= 45) & hi
            if okp.any():
                ok5 += 1
            else:
                bad5.append((s, int(k), str(cal[int(pos)].date())))
    K["K5 新增列數"] = int(len(new)); K["K5 獨立重算成立"] = ok5; K["K5 不成立"] = len(bad5)
    log(f"[K5] 新增 {len(new)}｜成立 {ok5}｜不成立 {bad5[:5]}")
    # K6
    seeds = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str})
    bad6 = []; n6 = 0
    for vn, fn in (("merged_a", "and_signals.csv.gz"), ("merged_b", "and_signals_delistexit.csv.gz")):
        RR.setup_and(cal, os.path.join(OUT, "sig_merged", fn), "branch", log, t1=True)
        G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy(); reg = G["regime"]
        base = AND[(e >= G["w0"]) & (e <= G["w1"])]
        mk = D.load_universe().set_index("stock_id")["market"]
        SF = R.stop_force_days(R.valid_from_data(sorted(G["closes"]), mk, cal), G["w1"])
        o = R.simulate_mtm(base, "H60", 20, np.random.default_rng(7000), G["closes"], G["opens"], G["ncal"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
        ref = seeds[(seeds["變體"] == vn) & (seeds["策略"] == "營量")].iloc[0]["eq_sha"]; n6 += 1
        if sha16(o["equity"]) != ref:
            bad6.append((vn, "營量", 0))
        sig = base[reg[base["entry_pos"].to_numpy() - 1]]
        for r in (0, 99, 199):
            o = R.simulate_mtm(sig, "H120", 10, np.random.default_rng(1000 + r), G["closes"], G["opens"], G["ncal"], return_equity=True, stop_force=SF)
            ref = seeds[(seeds["變體"] == vn) & (seeds["策略"] == "營飆") & (seeds["r"] == r)].iloc[0]["eq_sha"]; n6 += 1
            if sha16(o["equity"]) != ref:
                bad6.append((vn, "營飆", r))
    K["K6 交易重算項數"] = n6; K["K6 eq_sha 不符"] = len(bad6)
    log(f"[K6] {n6} 項｜不符 {bad6}")
    # K7
    st = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["last_seen"]
    bad7 = 0; n7 = 0
    for d in ("sig_null", "sig_merged"):
        f = os.path.join(OUT, d, "delistexit_rows.csv")
        x = pd.read_csv(f, dtype={"sid": str}) if os.path.getsize(f) > 5 else pd.DataFrame(columns=["sid", "末根日"])
        for s, dd in zip(x["sid"], x["末根日"]):
            n7 += 1; bad7 += str(st.get(s, ""))[:10] != str(dd)
    K["K7 ⓑ 補出場列"] = n7; K["K7 末根日 ≠ last_seen"] = bad7
    K["結論"] = "全過" if (K["K1 策略鎖 --check exit"] == 0 and K["K2 summary 閘非 0 項數"] == 0 and K["K3 null AND ≠ 定版"] == 0 and K["K4 可用日不符"] == 0
                         and K["K5 不成立"] == 0 and K["K6 eq_sha 不符"] == 0 and K["K7 末根日 ≠ last_seen"] == 0) else "有不過項"
    json.dump(K, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] {json.dumps(K, ensure_ascii=False, default=float)}")


if __name__ == "__main__":
    main()

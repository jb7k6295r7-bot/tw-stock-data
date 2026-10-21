# -*- coding: utf-8 -*-
"""財報品質 第 3 格 Q-G 正式跑【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsFinQ/G/ 與資料，不寫任何既有檔；輸出 resultsFinQ/G/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_G_check

C1 策略鎖相符（25 支）。
C2 乾跑對帳：recon_dry.csv 13 年全同；正式事件（H12、R 可算）＝ 乾跑 picks「Q-G入選 ∧ Q-G_stx＝保留」（2015～2025；2014 接縫不收）。
   新快照 Q-A、Q-I 名單與已提交 resultsFinQ/freq/picks.csv.gz 相同（overlap.csv 名單差 0）。
C3 Q-G 值獨立重算：抽 30 檔入選，直接讀 fs_xbrl 原始 csv（該年 Q4、cr 優先）算（營收 − 營業成本）÷ 總資產（容差 1e−12）；
   每年十分位切點由 picks 值重算 ⇒ 入選旗標全同（最高十分位、同值併入）。
C4 抽 12 筆手算：事件 R、20 檔對照 R 用 Indep 逐根迴圈 ⇒ X（容差 1e−9）。
C5 不前視：全部事件 FY(Y−1) 年報最早上傳日（AI1 優先）≤ 排序日 t ＜ e。
C6 對照名單 ≠ 自己、無重複、檔數 ＝ min(20, 池 − 1)；Σd − X ＜ 1e−12；FinQ_G_表 n、X̄、假訊號 x 由 events／fake_reps 重算。
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchFinQ_G as FG                   # noqa: E402
from backtest import researchFinQ_freq as FQ                # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402
from backtest import researchIndMom_check as IC             # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402

OUT = FG.OUT
LOG = IC.LOG
OK = IC.OK
log = IC.log
chk = IC.chk


def main():
    IC.lock_check()
    EV = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str, "對照": str})
    TB = pd.read_csv(os.path.join(OUT, "FinQ_G_表.csv"))
    FK = pd.read_csv(os.path.join(OUT, "fake_reps.csv"))
    RC = pd.read_csv(os.path.join(OUT, "recon_dry.csv"))
    PK = pd.read_csv(os.path.join(FG.DRY, "picks.csv.gz"), dtype={"sid": str})
    OV = pd.read_csv(os.path.join(FG.DRY, "overlap.csv"))
    sha = json.load(open(os.path.join(FG.DRY, "freq.json"), encoding="utf-8"))["資料"]["origin/main"]
    DATA = IMX.pinned_data(sha)
    chk("C2a recon_dry 全同", bool(RC["相同"].all()) and len(RC) == 13, f"{int(RC['相同'].sum())}／{len(RC)}")
    pk = PK[PK["Q-G入選"].astype(bool) & (PK["Q-G_stx"] == "保留") & PK["排序年"].between(2015, 2025)]
    e12 = EV[(EV["H"] == 12) & EV["R可算"].astype(bool)]
    chk("C2b 正式事件 ＝ 乾跑入選∧保留（2015～2025）", set(zip(pk["排序年"], pk["sid"])) == set(zip(e12["排序年"], e12["sid"])), f"{len(pk)} vs {len(e12)}")
    chk("C2c 新快照 Q-A、Q-I 名單 ＝ 已提交 picks", int(OV["Q-A新舊快照名單差"].sum()) == 0 and int(OV["Q-I新舊快照名單差"].sum()) == 0 and int(OV["母體新舊快照差"].sum()) == 0)
    # C3
    raw = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}) for f in sorted(glob.glob(os.path.join(DATA, "meta", "fs_xbrl", "fs_xbrl_*.csv")))])
    raw = raw[raw["period"].str.endswith("Q4")]
    rng = np.random.default_rng(20261021)
    sel = PK[PK["Q-G入選"].astype(bool)]
    errs = []
    for _, r in sel.iloc[rng.choice(len(sel), 30, replace=False)].iterrows():
        q = raw[(raw["stock_id"] == r["sid"]) & (raw["period"] == f"{int(r['排序年']) - 1}Q4")]
        q = q.sort_values("report", key=lambda s: (s != "cr").astype(int)).iloc[0]
        v = (q["revenue_ytd"] - q["cost_of_sales_ytd"]) / q["total_assets"]
        errs.append(abs(v - r["Q-G"]))
    chk("C3a 抽 30 檔 Q-G 值由原始 csv 重算", max(errs) < 1e-12, f"最大誤差 {max(errs):.2e}")
    nb = 0
    for Y, g in PK.groupby("排序年"):
        v = g["Q-G"].to_numpy(float); ok = np.isfinite(v); n = int(ok.sum()); k = int(math.ceil(n / 10))
        cut = np.sort(v[ok])[::-1][k - 1]
        nb += int(((v >= cut) & ok).astype(bool).tolist() != g["Q-G入選"].astype(bool).tolist())
    chk("C3b 每年最高十分位入選旗標重算", nb == 0, f"不符年 {nb}")
    # C4
    IP = IC.Indep("主")
    cal = IP.cal; ME, MK = PF.month_ends(cal); me_of = {(int(y), int(m)): int(p) for p, (y, m) in zip(ME, MK)}
    Zm = {"cal": cal}
    errs = []
    for _, r in e12.iloc[rng.choice(len(e12), 12, replace=False)].iterrows():
        Y = int(r["排序年"]); t, e = FQ.sort_points(Zm, Y); x = me_of[(Y + 1, 4)]
        Re, _ = IP.ret(r["sid"], e, x); Rc = np.mean([IP.ret(s, e, x)[0] for s in r["對照"].split("|")])
        errs.append(max(abs(Re - r["R"]), abs(Rc - r["對照R"]), abs(Re - Rc - r["X"])))
        log(f"   {Y} {r['sid']}：R {Re:+.6f}／{r['R']:+.6f}  對照 {Rc:+.6f}／{r['對照R']:+.6f}")
    chk("C4 抽 12 筆 R、對照、X 手算", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
    # C5
    FD = FQ.load_filing(DATA)
    bad = 0
    for _, r in EV[EV["R可算"].astype(bool)].drop_duplicates(["排序年", "sid"]).iterrows():
        Y = int(r["排序年"]); t, e = FQ.sort_points(Zm, Y); f1 = FD.get((r["sid"], Y - 1))
        bad += not (f1 is not None and f1[0] < cal[t].normalize() + pd.Timedelta(days=1) and t < e)
    chk("C5 FY(Y−1) 年報上傳日 ≤ t ＜ e（全部事件）", bad == 0, f"違反 {bad}")
    # C6
    vb = sum((r["sid"] in r["對照"].split("|")) or len(set(r["對照"].split("|"))) != len(r["對照"].split("|"))
             or len(r["對照"].split("|")) != min(20, int(r["池大小"]) - 1) for _, r in EV[EV["R可算"].astype(bool)].iterrows())
    chk("C6a 對照名單合法", vb == 0, f"違反 {vb}")
    chk("C6b Σd − X", float(EV["Σd−X"].abs().max()) < 1e-12, f"{EV['Σd−X'].abs().max():.2e}")
    worst = 0.0; nb = 0
    for _, r in TB.iterrows():
        g = EV[(EV["H"] == r["H"]) & EV["排序年"].isin(FG.SEGY[r["段"]]) & EV["R可算"].astype(bool)]
        worst = max(worst, abs(g["X"].mean() - r["X̄"])); nb += len(g) != r["n"]
        if r["身分"] == "判定":
            fk = FK[FK["段"] == r["段"]]
            nb += int((fk["結果"] == "結果②").sum()) != int(r["假訊號x(／30)"]) or len(fk) != 30
    chk("C6c 彙總 n、X̄、假訊號 x 重算", worst < 1e-12 and nb == 0, f"最大誤差 {worst:.2e}、不符 {nb}")
    allok = all(OK.values())
    log(f"{'✅ 全部通過' if allok else '❌ 有不通過'}（{sum(OK.values())}／{len(OK)}）")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""財報品質 seq1 正式跑（Q-A、Q-I）【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsFinQ/（freq/ 外）與資料，不寫任何既有檔；
輸出 resultsFinQ/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_check

C1 策略鎖相符（25 支）。
C2 頻率表逐列重建：recon_freq.csv 13 個排序年全同；H12 事件（R 可算）⊆ 頻率表 picks 入選 ∧ 頻率表狀態「保留」（exright 差異列另計），筆數同頻率表 freq.csv 事件數。
C3 抽 12 筆手算（兩格、探索／確認）：事件 R、20 檔對照各自 R 用 Indep 逐根迴圈重算 ⇒ X（容差 1e−9）。
C4 不前視：每筆事件 FY(Y−1) 年報最早上傳日（filing_dates，AI1 優先）≤ 排序日 t ＜ 進場日 e；Q-I 用的 FY(Y−2) 亦 ≤ t。
C5 對照名單：每筆 ≠ 自己、無重複、檔數 ＝ min(20, 池 − 1)；持有月拆解 Σd − X 最大誤差 ＜ 1e−12。
C6 彙總：FinQ_表.csv 各列 n、X̄ 由 events 重算（容差 1e−12）；假訊號 x 由 fake_reps.csv 重數。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchFinQ as FX                     # noqa: E402
from backtest import researchFinQ_freq as FQ                # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402
from backtest import researchIndMom_check as IC             # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402

OUT = FX.OUT
LOG = IC.LOG
OK = IC.OK
log = IC.log
chk = IC.chk


def main():
    IC.lock_check()
    EV = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str, "對照": str})
    TB = pd.read_csv(os.path.join(OUT, "FinQ_表.csv"))
    FK = pd.read_csv(os.path.join(OUT, "fake_reps.csv"))
    RC = pd.read_csv(os.path.join(OUT, "recon_freq.csv"))
    EXD = pd.read_csv(os.path.join(OUT, "exright_diff.csv"), dtype={"sid": str})
    PK = pd.read_csv(os.path.join(FX.FREQ_DIR, "picks.csv.gz"), dtype={"sid": str})
    FF = pd.read_csv(os.path.join(FX.FREQ_DIR, "freq.csv"))
    chk("C2a recon_freq 全同", bool(RC["相同"].all()) and len(RC) == 13, f"{int(RC['相同'].sum())}／{len(RC)}")
    exs = set(zip(EXD["排序年"], EXD["格"], EXD["sid"])) if len(EXD) else set()
    nbad = 0
    for c in FX.CELLS:
        ok_ = set(zip(PK.loc[PK[f"{c}入選"].astype(bool) & (PK[f"{c}_st"] == "保留"), "排序年"], PK.loc[PK[f"{c}入選"].astype(bool) & (PK[f"{c}_st"] == "保留"), "sid"]))
        e12 = EV[(EV["格"] == c) & (EV["H"] == 12) & EV["R可算"].astype(bool)]
        mine = set(zip(e12["排序年"], e12["sid"]))
        nbad += len({k for k in mine ^ {q for q in ok_ if q[0] in set(e12["排序年"])} if (k[0], c, k[1]) not in exs})
        for sg, ys in (("探索", FX.SEGY["探索"]), ("確認", FX.SEGY["確認"])):
            nf = int(FF[(FF["段"] == sg) & (FF["格"] == c)]["事件數(保留)"].iloc[0])
            nm_ = int(e12["排序年"].isin(ys).sum())
            nbad += nf != nm_
            log(f"   {c} {sg}：本檔 H12 事件 {nm_}｜頻率表 {nf}")
    chk("C2b 事件 ＝ 頻率表入選∧保留、段筆數同頻率表", nbad == 0, f"不符 {nbad}")
    # C3
    IP = IC.Indep("主")
    cal = IP.cal; ME, MK = PF.month_ends(cal); me_of = {(int(y), int(m)): int(p) for p, (y, m) in zip(ME, MK)}
    Zm = {"cal": cal}
    rng = np.random.default_rng(20261021)
    errs = []
    e12 = EV[(EV["H"] == 12) & EV["R可算"].astype(bool) & EV["排序年"].between(2017, 2025)]
    for _, r in e12.iloc[rng.choice(len(e12), 12, replace=False)].iterrows():
        Y = int(r["排序年"]); t, e = FQ.sort_points(Zm, Y); x = me_of[(Y + 1, 4)]
        Re, _ = IP.ret(r["sid"], e, x)
        Rc = np.mean([IP.ret(s, e, x)[0] for s in r["對照"].split("|")])
        errs.append(max(abs(Re - r["R"]), abs(Rc - r["對照R"]), abs((Re - Rc) - r["X"])))
        log(f"   {r['格']} {Y} {r['sid']}：R {Re:+.6f}／{r['R']:+.6f}  對照 {Rc:+.6f}／{r['對照R']:+.6f}")
    chk("C3 抽 12 筆 R、對照、X 手算", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
    # C4
    DATA = IMX.pinned_data(FX.PIN_SHA)
    FD = FQ.load_filing(DATA)
    bad = 0
    for _, r in EV[EV["R可算"].astype(bool)].drop_duplicates(["格", "排序年", "sid"]).iterrows():
        Y = int(r["排序年"]); t, e = FQ.sort_points(Zm, Y)
        f1 = FD.get((r["sid"], Y - 1)); f2 = FD.get((r["sid"], Y - 2))
        lim = cal[t].normalize() + pd.Timedelta(days=1)
        bad += not (f1 is not None and f1[0] < lim and t < e)
        bad += not (f2 is not None and f2[0] < lim)
    chk("C4 年報 FY(Y−1)、FY(Y−2) 上傳日 ≤ t ＜ e（全部事件）", bad == 0, f"違反 {bad}")
    # C5
    vb = 0
    for _, r in EV[EV["R可算"].astype(bool)].iterrows():
        cl = r["對照"].split("|")
        vb += (r["sid"] in cl) or (len(set(cl)) != len(cl)) or (len(cl) != min(20, int(r["池大小"]) - 1))
    chk("C5a 對照名單 ≠ 自己、無重複、數量 ＝ min(20, 池−1)", vb == 0, f"違反 {vb}")
    chk("C5b 持有月拆解 Σd − X", float(EV["Σd−X"].abs().max()) < 1e-12, f"{EV['Σd−X'].abs().max():.2e}")
    # C6
    worst = 0.0; nb = 0
    for _, r in TB.iterrows():
        ys = FX.SEGY[r["段"]]
        g = EV[(EV["格"] == r["格"]) & (EV["H"] == r["H"]) & EV["排序年"].isin(ys) & EV["R可算"].astype(bool)]
        worst = max(worst, abs(g["X"].mean() - r["X̄"])); nb += len(g) != r["n"]
        if r["身分"] == "判定":
            fk = FK[(FK["格"] == r["格"]) & (FK["段"] == r["段"])]
            nb += int((fk["結果"] == "結果②").sum()) != int(r["假訊號x(／30)"]) or len(fk) != 30
    chk("C6 彙總 n、X̄、假訊號 x 重算", worst < 1e-12 and nb == 0, f"最大誤差 {worst:.2e}、不符 {nb}")
    allok = all(OK.values())
    log(f"{'✅ 全部通過' if allok else '❌ 有不通過'}（{sum(OK.values())}／{len(OK)}）")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

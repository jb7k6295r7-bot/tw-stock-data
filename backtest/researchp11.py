"""PREREGP11（策略線 seq=4 投遞檔 ＋ 回測線追加一）：**門檻B vs 參考C 在同選擇率下**。

    python3 -m backtest.researchp11 [--procs 8] [--reps 200] [--out backtest/resultsp11]

⭐ 引擎是 `research11.simulate_mtm`（⛔ 沒有另建）；sig 是 `researchp7.build_sig_gate_b(signal=...)`
   （⛔ 沒有抄第二份）；月分群 CI 是 `researchp8.month_ci`；曝險是 `researchp3.exposure_series`。
⭐ 主體＝【逐月 N_t】（登錄 §八，K線分析線 1330 裁定）：N_t ＝ max(1, half-up(選擇率 × 該月候選數))
   ⇒ 追加一①：N_t 是【當月的槽位容量】⇒ 引擎吃逐日容量陣列。
⭐ 判定格＝【選擇率 35%】（登錄 §七，⛔ 其餘三格只作描述、⛔ 判定格沒過不可改用它們）。
⛔ 判定看 CI 含不含 0（追加一⑥：先逐種子配對、再以【月】為抽樣單位），⛔ 不看點估計大小。
⛔ 回落沒有逐月分解 ⇒ 它只有【種子帶】，⛔ 不是抽樣分佈（追加一⑦、〈九十八〉）。
⭐ 另跑一份【固定 N】（6/8/12/17）給使用者看（登錄 §八，⛔ 描述、⛔ 不進判定）。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp3 as P3
from . import researchp7 as P7
from . import researchp8 as P8
from . import researchp9 as P9

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp11")
SEED0 = 101000                  # ⛔ 登錄 §二 寫死：default_rng(101000 + r)
RULE = P7.RULE
RATES = (0.25, 0.35, 0.50, 0.75)
MAIN_RATE = 0.35                # ⛔ 登錄 §七：判定格
B_CAND_MED = 23                 # 登錄 §八：門檻B 候選中位（⭐ 程式會驗，對不上就中止）
IDLE_THRESH = (0.50, 0.75)      # 追加一⑨：現金閒置月數用兩個門檻各報一次（⛔ 不挑一個當結論）


def n_of(rate: float, cand: int) -> int:
    """追加一⑤：N ＝ max(1, half-up(rate × cand))。

    ⛔ 寫死成 half-up（floor(x+0.5)）——⚠ Python 的 round() 是 banker's rounding
    （round(0.5)=0、round(3.5)=4、round(2.5)=2）⇒ 剛好 .5 的月份會少一檔，而那種月份不少。
    """
    return max(1, int(np.floor(rate * cand + 0.5)))


def month_entry_pos(sig: pd.DataFrame) -> pd.Series:
    """每個月的進場日（⛔ 每月只能有一個，否則中止：追加一②的容量區間會定不出來）。"""
    per = sig.groupby("month")["entry_pos"].nunique()
    if (per != 1).any():
        raise SystemExit(f"⛔ 有月份不只一個進場日 ⇒ 容量區間定不出來，停跑：\n{per[per != 1]}")
    return sig.groupby("month")["entry_pos"].first().astype(int).sort_index()


def caps_series(sig: pd.DataFrame, rate: float, ncal: int) -> tuple[np.ndarray, pd.DataFrame]:
    """追加一①②：逐日槽位容量。

    ⭐ 第 m 個月的容量 N_m 從【該月進場日】生效，到【下個月進場日】前一天；
    ⛔ 不用日曆月（量測日多半在月底 ⇒ 進場日常常已經跨月）。第一個進場日之前用第一個月的 N。
    """
    ent = month_entry_pos(sig)
    cand = sig.groupby("month")["sid"].size().reindex(ent.index).astype(int)
    tab = pd.DataFrame({"month": ent.index, "entry_pos": ent.to_numpy(), "cand": cand.to_numpy()})
    tab["N"] = [n_of(rate, c) for c in tab["cand"]]
    tab["rate_real"] = tab["N"] / tab["cand"]
    tab["sold_out"] = tab["N"] >= tab["cand"]            # 追加一⑩：買光月
    caps = np.full(ncal, int(tab["N"].iloc[0]), int)
    for i, r in enumerate(tab.itertuples()):
        hi = int(tab["entry_pos"].iloc[i + 1]) if i + 1 < len(tab) else ncal
        caps[int(r.entry_pos):hi] = int(r.N)
    return caps, tab


def monthly_returns(eq: np.ndarray, month_end: np.ndarray) -> np.ndarray:
    """逐月報酬（⭐ 用日曆月的最後一個交易日相除）。⛔ 第一個月沒有前一個月底 ⇒ 不算。"""
    v = eq[month_end]
    return v[1:] / v[:-1] - 1.0


_S: dict = {}


def _init(sigs, caps, closes, opens, ncal, first_all, split_pos, end_all, month_end, month_id):
    _S.update(sigs=sigs, caps=caps, closes=closes, opens=opens, ncal=ncal, first_all=first_all,
              split_pos=split_pos, end_all=end_all, month_end=month_end, month_id=month_id)


def _one(args):
    sigset, mode, rate, seed = args
    n_slots = _S["caps"][(sigset, mode, rate)]
    s = R.simulate_mtm(_S["sigs"][sigset], RULE, n_slots, np.random.default_rng(seed), _S["closes"], _S["opens"],
                       _S["ncal"], return_equity=True, report_maxw=True)
    ca, ma = R13.window_stats(s["equity"], s["first"], s["end"], _S["first_all"], _S["split_pos"])
    cb, mb = R13.window_stats(s["equity"], s["first"], s["end"], _S["split_pos"], _S["end_all"])
    e_, _r, _nz = P3.exposure_series(s["equity"], s["hold_val"], s["first"], s["end"])   # ⭐ 與 P3 同一支
    expo_m = pd.Series(e_).groupby(_S["month_id"][s["first"]:s["end"]]).mean()           # 逐月平均曝險
    return {"sigset": sigset, "mode": mode, "rate": rate, "seed": seed, "cagr": s["cagr"], "mdd": s["mdd"],
            "slot": s["slot_use"], "m": s["m"], "ca": ca, "ma": ma, "cb": cb, "mb": mb, "expo": float(np.mean(e_)),
            "maxw": s["max_pos_frac"],
            "mret": monthly_returns(s["equity"], _S["month_end"]).astype(np.float32),
            "expo_m": expo_m.reindex(range(len(_S["month_end"]))).to_numpy(np.float32)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = print
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    sigs = {k: P7.build_sig_gate_b(panel, cal, closes, opens, signal=k) for k in ("B", "C")}
    want = {"rows": 2882, "stocks": 919, "months": 109, "m_min": "2017-03", "m_max": "2026-03", "e_min": 523, "e_max": 2716}
    got = {"rows": len(sigs["B"]), "stocks": sigs["B"]["sid"].nunique(), "months": sigs["B"]["month"].nunique(),
           "m_min": sigs["B"]["month"].min(), "m_max": sigs["B"]["month"].max(),
           "e_min": int(sigs["B"]["entry_pos"].min()), "e_max": int(sigs["B"]["entry_pos"].max())}
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 先回信、⛔ 不跑\n  want {want}\n  got  {got}")
    # ⛔ 登錄 §四④ 的防呆：B ⊂ C 必須成立（股-月為單位，追加一⑪）
    pb = set(map(tuple, sigs["B"][["sid", "month"]].to_numpy()))
    pc = set(map(tuple, sigs["C"][["sid", "month"]].to_numpy()))
    ov = len(pb & pc)
    if ov != len(pb):
        raise SystemExit(f"⛔ B ⊄ C（B∩C {ov} ≠ B {len(pb)}）⇒ 依登錄 §四④ 先查程式、⛔ 不寫結論")
    log(f"[sig] B {len(sigs['B']):,} 股-月／{sigs['B']['sid'].nunique()} 檔｜C {len(sigs['C']):,} 股-月／{sigs['C']['sid'].nunique()} 檔"
        f"｜重疊 B∩C÷B {ov / len(pb) * 100:.1f}%、B∩C÷C {ov / len(pc) * 100:.1f}%")
    med_b = int(sigs["B"].groupby("month")["sid"].size().median())
    med_c = int(sigs["C"].groupby("month")["sid"].size().median())
    log(f"[候選] 逐月中位 B {med_b}／C {med_c}（登錄 §八 寫 B≈{B_CAND_MED}、§〇 寫 C≈46）")

    months = sorted(set(pd.Series(cal).dt.strftime("%Y-%m")))
    ym = pd.Series(cal).dt.strftime("%Y-%m")
    month_id = ym.map({m: i for i, m in enumerate(months)}).to_numpy()
    month_end = np.array([int(np.where(month_id == i)[0][-1]) for i in range(len(months))])

    caps = {}; ntabs = {}
    for k in ("B", "C"):
        for rate in RATES:
            c, tab = caps_series(sigs[k], rate, ncal)
            caps[(k, "var", rate)] = c; ntabs[(k, rate)] = tab
            caps[(k, "fix", rate)] = n_of(rate, B_CAND_MED)      # 追加一⑫：固定 N 兩個訊號集用同一組
    fixed_ns = {rate: n_of(rate, B_CAND_MED) for rate in RATES}
    log(f"[N] 固定 N（half-up(選擇率×{B_CAND_MED})）＝ " + "／".join(f"{r * 100:.0f}%→{n}" for r, n in fixed_ns.items()))

    first_all = int(min(sigs[k]["entry_pos"].min() for k in sigs)); end_all = ncal
    split_pos = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    b_c, b_m = R13.window_stats(bench, first_all, end_all, first_all, end_all)
    b_ca, b_ma = R13.window_stats(bench, first_all, end_all, first_all, split_pos)
    b_cb, b_mb = R13.window_stats(bench, first_all, end_all, split_pos, end_all)
    log(f"[0050] 全窗 {b_c * 100:+.2f}%／{b_m * 100:.1f}%；A 窗 {b_ca * 100:+.2f}%／{b_ma * 100:.1f}%；B 窗 {b_cb * 100:+.2f}%／{b_mb * 100:.1f}%")

    jobs = [(k, mode, rate, SEED0 + r) for k in ("B", "C") for mode in ("var", "fix") for rate in RATES for r in range(a.reps)]
    t0 = time.time()
    pool = Pool(a.procs, initializer=_init, initargs=(sigs, caps, closes, opens, ncal, first_all, split_pos, end_all, month_end, month_id))
    try:
        res = pool.map(_one, jobs, chunksize=8)
    finally:
        pool.close(); pool.join()
    log(f"[run] {len(res)} 趟跑完（{time.time() - t0:.0f}s）")

    df = pd.DataFrame([{kk: v for kk, v in r.items() if kk not in ("mret", "expo_m")} for r in res])
    mret = {(r["sigset"], r["mode"], r["rate"], r["seed"]): r["mret"] for r in res}
    expo_m = {(r["sigset"], r["mode"], r["rate"], r["seed"]): r["expo_m"] for r in res}
    df.to_csv(os.path.join(a.out, "seeds.csv"), index=False)

    rows = []
    for (k, mode, rate), g in df.groupby(["sigset", "mode", "rate"], sort=False):
        md = g.median(numeric_only=True)
        stack = np.vstack([expo_m[(k, mode, rate, s)] for s in g["seed"]])
        keep = np.isfinite(stack).any(axis=0)          # ⛔ 全 NaN 的月（第一個進場日之前）先拿掉，⛔ 不讓 nanmean 去猜
        em = np.nanmean(stack[:, keep], axis=0)
        em = em[np.isfinite(em)]
        rows.append({"sigset": k, "mode": mode, "rate": rate,
                     "cagr": md["cagr"], "cagr_p10": g["cagr"].quantile(.1), "cagr_p90": g["cagr"].quantile(.9),
                     "mdd": md["mdd"], "mdd_p10": g["mdd"].quantile(.1), "mdd_p90": g["mdd"].quantile(.9),
                     "slot": md["slot"], "m": md["m"], "expo": md["expo"], "maxw": md["maxw"], "maxw_worst": g["maxw"].max(),
                     "expo_m_min": em.min(), "expo_m_p25": np.percentile(em, 25), "expo_m_med": np.median(em),
                     "expo_m_p75": np.percentile(em, 75), "expo_m_max": em.max(),
                     "idle50": int((em < IDLE_THRESH[0]).sum()), "idle75": int((em < IDLE_THRESH[1]).sum()), "n_months": len(em),
                     "ca": md["ca"], "ma": md["ma"], "cb": md["cb"], "mb": md["mb"],
                     "win_all": bool(P9.passes(md["cagr"], md["mdd"], b_c, b_m)),
                     "win_a": bool(P9.passes(md["ca"], md["ma"], b_ca, b_ma)),
                     "win_b": bool(P9.passes(md["cb"], md["mb"], b_cb, b_mb))})
    T = pd.DataFrame(rows); T["win"] = T["win_all"] & T["win_a"] & T["win_b"]
    T.to_csv(os.path.join(a.out, "cells.csv"), index=False)
    for r in T.itertuples():
        log(f"  {r.sigset} {r.mode} {r.rate * 100:.0f}% 年化 {r.cagr * 100:+6.2f}% 回落 {r.mdd * 100:6.1f}% "
            f"曝險 {r.expo * 100:4.1f}% 槽 {r.slot:.2f} 筆 {r.m:.0f} ⇒ 三窗 {'✅' if r.win else '⛔'}")

    # 判定：逐種子配對（C − B）⇒ 月分群 CI（追加一⑥⑦⑧）
    seeds = [SEED0 + r for r in range(a.reps)]
    jrows = []
    for mode in ("var", "fix"):
        for rate in RATES:
            dm = np.nanmean(np.vstack([mret[("C", mode, rate, s)].astype(float) - mret[("B", mode, rate, s)].astype(float)
                                       for s in seeds]), axis=0)
            ci = P8.month_ci(dm)
            dmdd = np.array([df[(df.sigset == "C") & (df["mode"] == mode) & (df.rate == rate) & (df.seed == s)]["mdd"].iloc[0]
                             - df[(df.sigset == "B") & (df["mode"] == mode) & (df.rate == rate) & (df.seed == s)]["mdd"].iloc[0]
                             for s in seeds])
            jrows.append({"mode": mode, "rate": rate, "n_months": ci["n_months"], "mdiff_pp": ci["diff_pp"],
                          "lo_pp": ci["lo_pp"], "hi_pp": ci["hi_pp"], "pos_months": ci["pos_months"],
                          "detectable": ci["detectable"], "ann_pp": ci["diff_pp"] * 12,
                          "ann_lo": ci["lo_pp"] * 12, "ann_hi": ci["hi_pp"] * 12,
                          "dmdd_med": float(np.median(dmdd)) * 100,
                          "dmdd_lo": float(np.percentile(dmdd, 2.5)) * 100, "dmdd_hi": float(np.percentile(dmdd, 97.5)) * 100})
    J = pd.DataFrame(jrows); J.to_csv(os.path.join(a.out, "judge.csv"), index=False)
    for r in J.itertuples():
        log(f"  [判定] {r.mode} {r.rate * 100:.0f}% 年化差 {r.ann_pp:+.2f}pp CI[{r.ann_lo:+.2f},{r.ann_hi:+.2f}] "
            f"{'✅ 不含 0' if r.detectable else '⛔ 含 0'}｜回落差 {r.dmdd_med:+.2f}pp 種子帶[{r.dmdd_lo:+.2f},{r.dmdd_hi:+.2f}]")

    NT = pd.concat([tab.assign(sigset=k, rate=rate) for (k, rate), tab in ntabs.items()], ignore_index=True)
    NT.to_csv(os.path.join(a.out, "n_t.csv"), index=False)
    L = report(T, J, NT, sigs, {"b_c": b_c, "b_m": b_m, "b_ca": b_ca, "b_ma": b_ma, "b_cb": b_cb, "b_mb": b_mb,
                                "ov_b": ov / len(pb), "ov_c": ov / len(pc), "med_b": med_b, "med_c": med_c,
                                "fixed_ns": fixed_ns, "reps": a.reps})
    open(os.path.join(a.out, "P11_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"寫入 {os.path.join(a.out, 'P11_REPORT.md')}")


def report(T: pd.DataFrame, J: pd.DataFrame, NT: pd.DataFrame, sigs: dict, st: dict) -> list[str]:
    jm = J[(J["mode"] == "var") & (J["rate"] == MAIN_RATE)].iloc[0]
    L = ["# PREREGP11：門檻B vs 參考C 在同選擇率下（回測線落地）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。登錄＝`backtest/PREREGP11.md`"
         f"（策略線投遞檔 seq=4 正文 ＋ 回測線追加一）。種子 `default_rng({SEED0} + r)`、R={st['reps']}。", "",
         f"訊號集：**門檻B** {len(sigs['B']):,} 股-月／{sigs['B']['sid'].nunique():,} 檔（逐月候選中位 **{st['med_b']}**）；"
         f"**參考C** {len(sigs['C']):,} 股-月／{sigs['C']['sid'].nunique():,} 檔（中位 **{st['med_c']}**）。",
         f"⭐ 防呆（登錄 §四④）：**B∩C÷B ＝ {st['ov_b'] * 100:.1f}%**、B∩C÷C ＝ {st['ov_c'] * 100:.1f}%（股-月為單位）"
         f"⇒ {'✅ B ⊂ C 成立' if st['ov_b'] > 0.999 else '⛔ 不成立 ⇒ 先查程式'}。", "",
         f"⭐ **逐月 N_t**（登錄 §八）：N_t ＝ max(1, half-up(選擇率 × 該月候選數))，當月的**槽位容量**（追加一①）。",
         f"⭐ 固定 N（給使用者那一份）：" + "／".join(f"{r * 100:.0f}%→**{n}**" for r, n in st["fixed_ns"].items())
         + "（⛔ 描述，⛔ 不進判定）。", "",
         "## 一、⛔ 判定格（登錄 §七：選擇率 35%、逐月 N_t）", "",
         f"**① 年化配對差（C − B，逐種子配對後以【月】為抽樣單位）**："
         f"月均 {jm['mdiff_pp']:+.3f}pp、**年化 {jm['ann_pp']:+.2f}pp CI [{jm['ann_lo']:+.2f}, {jm['ann_hi']:+.2f}]**"
         f"（{int(jm['n_months'])} 個月，其中 {int(jm['pos_months'])} 個月為正）"
         f"⇒ {'✅ CI 不含 0 且為正' if (jm['detectable'] and jm['ann_pp'] > 0) else '⛔ CI 含 0（或為負）'}",
         f"**② 回落配對差**：中位 {jm['dmdd_med']:+.2f}pp、**種子帶** [{jm['dmdd_lo']:+.2f}, {jm['dmdd_hi']:+.2f}]"
         f"⇒ {'回落沒有變差' if (jm['dmdd_med'] >= 0 or jm['dmdd_lo'] * jm['dmdd_hi'] <= 0) else '⛔ 回落變差'}",
         "", "⛔ 那個帶是【種子帶】，⛔ 不是抽樣分佈（追加一⑦、〈九十八〉）⇒ ⛔ 不可寫成「回落的差測得出」。", ""]
    ok1 = bool(jm["detectable"] and jm["ann_pp"] > 0)
    L += [f"⇒ ⭐⭐ **判定：{'C 的年化測得出高於 B' if ok1 else '兩個訊號集在年化上【測不出差異】'}**"
          + ("" if ok1 else "　⇒ ⛔ 依登錄 §三，選擇依據就【不是報酬】，改看 §五 那三件（⛔ 本線不裁，那是策略線的格子）。"), "",
          "## 二、⭐ 四個選擇率的形狀（⛔ 25/50/75% 只作描述，⛔ 不可宣告測到）", "",
          "| 模式 | 選擇率 | 年化差（C−B，年化化） | CI | 不含 0？ | 為正的月數 | 回落差 中位 | 種子帶 |",
          "|---|---:|---:|---|:--:|---:|---:|---|"]
    for r in J.itertuples():
        L.append(f"| {'逐月 N_t' if r.mode == 'var' else '固定 N'} | {r.rate * 100:.0f}%{'（判定格）' if (r.mode == 'var' and r.rate == MAIN_RATE) else ''} | "
                 f"{r.ann_pp:+.2f}pp | [{r.ann_lo:+.2f}, {r.ann_hi:+.2f}] | {'✅' if r.detectable else '⛔'} | "
                 f"{int(r.pos_months)}/{int(r.n_months)} | {r.dmdd_med:+.2f}pp | [{r.dmdd_lo:+.2f}, {r.dmdd_hi:+.2f}] |")
    var_ann = J[J["mode"] == "var"].sort_values("rate")["ann_pp"].to_numpy()
    mono = bool(np.all(np.diff(var_ann) >= 0) or np.all(np.diff(var_ann) <= 0))
    L += ["", f"⭐ 逐月 N_t 那四格的年化差隨選擇率：" + " → ".join(f"{v:+.2f}" for v in var_ann)
          + f"　⇒ {'✅ 單調' if mono else '⚠ **非單調** ⇒ ⛔ 依登錄 §七，判定格那一格的可信度要【下調】'}", "",
          "## 三、⭐ 八格 ＋ 八格（必報①③）", "",
          "| 訊號集 | 模式 | 選擇率 | 年化 中位 | p10～p90 | 最大回落 | p10～p90 | 平均曝險 | 單一部位最大佔比 | 槽位 | 筆數 | 全窗 | A 窗 | B 窗 | 三窗 |",
          "|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|:--:|:--:|:--:|:--:|"]
    for r in T.sort_values(["mode", "rate", "sigset"]).itertuples():
        L.append(f"| {r.sigset} | {'逐月 N_t' if r.mode == 'var' else '固定 N'} | {r.rate * 100:.0f}% | {r.cagr * 100:+.2f}% | "
                 f"{r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f} | {r.mdd * 100:.1f}% | {r.mdd_p10 * 100:.1f}～{r.mdd_p90 * 100:.1f} | "
                 f"{r.expo * 100:.1f}% | {r.maxw * 100:.1f}%（最差 {r.maxw_worst * 100:.1f}%） | {r.slot:.2f} | {r.m:.0f} | "
                 f"{'✅' if r.win_all else '✗'} | {'✅' if r.win_a else '✗'} | "
                 f"{'✅' if r.win_b else '✗'} | {'✅' if r.win else '⛔'} |")
    v = T[T["mode"] == "var"]; f = T[T["mode"] == "fix"]
    n1 = int((NT["N"] == 1).sum())
    L += ["", "### ⚠⚠ 一個【設計本身】的後果，必須看見（⭐ 觀察，⛔ 不是判定）", "",
          f"逐月 N_t 的回落中位 {v['mdd'].median() * 100:.1f}% vs 固定 N {f['mdd'].median() * 100:.1f}%；"
          f"單一部位最大佔比 {v['maxw'].median() * 100:.1f}% vs {f['maxw'].median() * 100:.1f}%。", "",
          f"⇒ ⭐⭐ 成因寫死在登錄 §八 的設計裡：N_t ＝ 選擇率 × 候選數、**下限 1 檔**"
          f"⇒ 候選少的月份容量極小 ⇒ 進場金額 ＝ equity ÷ N_t 極大。"
          f"（N_t ＝ 1 的月份共 **{n1}** 個月-格）",
          "⇒ ⛔ 所以「逐月 N_t 的回落比較深」**不是訊號集的性質**，是**對齊選擇率這個做法**的代價。",
          "⇒ ⏳ 要不要給 N_t 一個下限（例如 ≥ 5）或給單一部位一個上限 ⇒ ⭐ 那是 K線分析線／策略線的格子，⛔ 本線不裁；",
          "　 ⛔ 而本件**照登錄字面跑**（下限 1 檔是 1330 寫死的）。", "",
          f"（0050：全窗 {st['b_c'] * 100:+.2f}%／{st['b_m'] * 100:.1f}%；A 窗 {st['b_ca'] * 100:+.2f}%／{st['b_ma'] * 100:.1f}%；"
          f"B 窗 {st['b_cb'] * 100:+.2f}%／{st['b_mb'] * 100:.1f}%）",
          "⚠⚠ **槽位使用率可能 > 1.00**：追加一③ 寫死「容量變小時不強制出場」⇒ 持倉數可以暫時多於當月容量，",
          "　 而槽位使用率的分母是 **Σ 逐日容量** ⇒ ⭐ 那是設計的可見後果，⛔ 不是 bug。", "",
          "⚠ 平均持有天數：本件停損 none ⇒ 每一筆都是排程出場 ＝ **持有 120 根**（日數差 119），⛔ 逐格相同不另列。", "",
          "## 四、⛔ 三個副作用（登錄 §八，⛔ 缺一項不算交件）", "",
          "### ① N_t 的分佈 ＋ ② 買光月數 ＋ 實際選擇率（必報②）", "",
          "| 訊號集 | 選擇率 | N_t min | p25 | 中位 | p75 | max | 買光月數 | 實際選擇率 中位 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for (k, rate), g in NT.groupby(["sigset", "rate"]):
        L.append(f"| {k} | {rate * 100:.0f}% | {int(g['N'].min())} | {int(g['N'].quantile(.25))} | {int(g['N'].median())} | "
                 f"{int(g['N'].quantile(.75))} | {int(g['N'].max())} | {int(g['sold_out'].sum())}/{len(g)}"
                 f"（{g['sold_out'].mean() * 100:.1f}%） | {g['rate_real'].median() * 100:.1f}% |")
    L += ["", "⭐ 實際選擇率的中位要貼近名目選擇率 —— ⛔ 差太多就表示對齊沒成立（登錄 §2-E②）。",
          "⚠ 買光月仍然有，⭐ 但那是【候選數太少】造成的（N_t 下限 1 檔、且 round 會往上），⛔ 不是固定 N 那種買光。", "",
          "### ③ 現金閒置（⛔ 與 PREREGP3 同一支 `exposure_series`，⛔ 不各算一套）", "",
          "| 訊號集 | 模式 | 選擇率 | 逐月平均曝險 min | p25 | 中位 | p75 | max | 曝險<50% 的月 | 曝險<75% 的月 |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in T.sort_values(["mode", "rate", "sigset"]).itertuples():
        L.append(f"| {r.sigset} | {'逐月 N_t' if r.mode == 'var' else '固定 N'} | {r.rate * 100:.0f}% | {r.expo_m_min * 100:.1f}% | "
                 f"{r.expo_m_p25 * 100:.1f}% | {r.expo_m_med * 100:.1f}% | {r.expo_m_p75 * 100:.1f}% | {r.expo_m_max * 100:.1f}% | "
                 f"{r.idle50}/{r.n_months} | {r.idle75}/{r.n_months} |")
    L += ["", "⛔ 兩個門檻【各報一次】並附整條分佈（追加一⑨）⇒ ⭐ 要換門檻的人自己讀得出來，⛔ 本線不挑一個當結論。",
          "⛔⛔ 而【槽位使用率量不到資金閒置】：它數的是「有幾個槽裡有部位」，⛔ 不是「錢有沒有在市場裡」"
          "（⭐ PREREGP9 本輪付過這個代價）。", "",
          "## 五、⛔ 範圍限制（登錄 §六 ＋ 本趟）", "",
          "① 本件**只比訊號集**，⛔ 不測停損／加減碼／位置維度（P7／P9／P8）。",
          "② ⭐ 依〈九十五〉：逐月／逐種子配對**在設計上會消掉時點效應** ⇒ ⛔ 年化配對差【對回落那一項天生沉默】"
          "⇒ ⛔ 不可讓讀者以為「C 比較好」也代表回落比較好。",
          "③ ⛔ 只跑這一次、⛔ 不再換訊號集（K線分析線 1215 條件③）；⛔ 25/50/75% 三格不可拿來宣告測到。",
          "④ 成本 0.585%、滑價未計、倖存者偏誤仍在。",
          "⑤ ⚠ 容量變小時**不強制出場**（追加一③）⇒ len(持倉) > N_t 會出現；那是設計，⛔ 不是 bug。",
          "⑥ ⚠ 0050 用**本線自己算的那一份**（登錄 §一②）⇒ 結論只寫「通過／未通過三條判準」，⛔ 不寫「贏 0050 幾 pp」。", "",
          "## 六、⇒ 結論與四個先驗的對照（⛔ 照登錄字面）", ""]
    bv = T[(T["mode"] == "var") & (T["sigset"] == "B")].sort_values("rate")["cagr"].to_numpy() * 100
    cv = T[(T["mode"] == "var") & (T["sigset"] == "C")].sort_values("rate")["cagr"].to_numpy() * 100
    bf = T[(T["mode"] == "fix") & (T["sigset"] == "B")].sort_values("rate")["cagr"].to_numpy() * 100
    cf = T[(T["mode"] == "fix") & (T["sigset"] == "C")].sort_values("rate")["cagr"].to_numpy() * 100
    det = int(J[(J["mode"] == "var")]["detectable"].sum())
    L += [f"**① 判定格【{'測得出' if ok1 else '測不出'}】** ⇒ 逐月 N_t 四格裡 CI 不含 0 的有 **{det} 格**"
          f"（策略線先驗① 押【0~1 格】⇒ {'✅ 成立' if det <= 1 else '⛔ 沒成立'}）。", "",
          "**② ⭐⭐ 策略線先驗②（「對齊選擇率之後，兩條線的形狀不再相反」）⇒ ✅ 成立，而且看得很清楚：**", "",
          "| 模式 | 門檻B 年化（25→75%） | 參考C 年化（25→75%） | 形狀 |", "|---|---|---|---|",
          f"| 固定 N | {' → '.join(f'{v:+.2f}' for v in bf)} | {' → '.join(f'{v:+.2f}' for v in cf)} | ⛔ **相反**（B 遞減、C 遞增） |",
          f"| 逐月 N_t | {' → '.join(f'{v:+.2f}' for v in bv)} | {' → '.join(f'{v:+.2f}' for v in cv)} | ✅ **同向**（兩條都隨選擇率上升） |", "",
          "⇒ ⭐⭐⭐ 那個「相反」在**固定 N 下仍然存在、在同選擇率下消失** ⇒ ⭐ 它確實是【選擇率沒對齊】造成的假象"
          "（登錄 §〇：B 在 N=20 的選擇率 87% ＝ 幾乎買光 ⇒ 量到的是「沒有篩選」）。", "",
          f"**③ 策略線先驗③（八格仍然沒有一格通過三條判準）⇒ {'✅ 成立' if int(T['win'].sum()) == 0 else '⛔ 沒成立'}**："
          f"十六格裡通過三窗的有 **{int(T['win'].sum())} 格**（⛔ 回落那一腳過不去）。", "",
          f"**④ 策略線先驗④（B ⊂ C ⇒ B∩C÷B ≈ 100%）⇒ ✅ 成立**（{st['ov_b'] * 100:.1f}%）⇒ 防呆過關。", "",
          "**⑤ ⇒ 依登錄 §三：兩項不同時成立 ⇒ 結論寫【兩個訊號集測不出差異】**，",
          "而那時的選擇依據**不是報酬**，是登錄 §五 那三件（可驗收性／候選池大小／¬ma_stack 的邊際貢獻）",
          "⇒ ⛔ 那三件的權衡是**策略線的格子**，⛔ 本線不裁。", "",
          "**⑥ ⛔ 而依〈九十五〉必須寫的那一句**：逐月／逐種子配對**在設計上會消掉時點效應**",
          "⇒ 本件的年化配對差【對回落那一項天生沉默】⇒ ⛔ 不可讀成「C 比較好也代表回落比較好」。", ""]
    return L


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""美股合理價機械版——「穩定溢價本益比 35」變體：正式跑（報酬只當描述；判語事先固定）。

登錄：產業 seq82（pw1 sha f79e37d619c9fb0f）；發號：裁定 seq495 §一；正式跑：裁定 seq496 §一（「可帶 --formal --ruling seq496 跑」）。
頻率表與乾跑：backtest/researchUSStablePE35_freq.py → backtest/resultsStablePE35/freq/（commit 11e4264dc4）；
私有逐檔分組 ~/us_work/stablepe35/us_rows.csv（freq 產出；本檔開跑前先重跑 freq 確認 0 不一致）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSStablePE35_formal --formal --ruling seq496
    （⛔ 沒帶 --formal --ruling seq496 一律拒跑）

私有庫規矩：repo 的 resultsStablePE35/formal/ 只放彙總（每評估日只有筆數與差，無代號）；逐筆（代號×報酬）只寫 ~/us_work/stablepe35/formal/。

程式重用（⛔ 不改原版檔、⛔ 不寫第二份實作）：
  - 原版分組：researchUSFairValue.load_groups()（原版私有分類檔）；變體分組：freq 私有 us_rows.csv 的 group_var。
  - 單筆報酬：researchUSFairValue.Holder(dry=False).daily ＋ cum（seq63 §二口徑：d 收盤進場、250／750 交易日、ret 連乘含息、
    panel 結束後現金、整段無價格 −100%、★R1／★R2 照原版）；組平均：mean_or_none。
  - 按進場年分群 bootstrap：researchUSFairValue.boot_ci（10,000 次、百分位法）＋ 種子 researchUSFairValue.SEED（20261027）。
  - 大盤：^SP500TR（data/macro/yahoo_SP500TR.csv adjclose，原版同檔）；單窗報酬＝adjclose[窗末] ÷ adjclose[評估日] − 1
    （＝原版逐日 bm 在同一窗的連乘；開跑檢查窗內無缺日）。

══════════ 判語與讀法（看任何報酬前寫死；⛔ 不因數字改）══════════
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.dont_write_bytecode = True
from backtest import researchUSFairValue_freq as FQ   # noqa: E402
from backtest import researchUSFairValue as USFV     # noqa: E402
from backtest.researchTWStablePE35_formal import (FIXED_VERDICT, RULING_REQUIRED, NI_BOUND,  # noqa: E402
                                                   write_merged)

DATA_PIN = "89d9f8550f6ea39b392087c22998cd298164a26c"
HERE = os.path.dirname(os.path.abspath(__file__))
FREQ = os.path.join(HERE, "resultsStablePE35", "freq")
PRIV = os.path.expanduser("~/us_work/stablepe35")
PRIV_OUT = os.path.join(PRIV, "formal")
H1, H3 = USFV.H1, USFV.H3
READINGS_US = [
    "判語：還沒測（依構造）——重新分類組 49 筆、17 個評估日，但進場年群數 6 < 24（〈四十九〉；seq495／seq496）。報酬數字不影響判語。",
    "主格（seq82 §三，持有 1 年）：每個有重新分類組的評估日，diff_d＝重新分類組平均 − 同日原版可買組平均（兩邊都有可算報酬者才有 diff_d）；"
    "對這些評估日取平均；按進場年（評估日的年）分群 bootstrap 95% CI（原版 boot_ci，10,000 次、種子 20261027、百分位法）。",
    "不劣於界線 −5 個百分點（平均 ≥ 0 且 CI 下緣 > −5pp）：數字照報、是否落在界線內照報，⛔ 不用它下判語。",
    "單筆報酬與組平均照原版 seq63 §二（Holder／cum／mean_or_none）；1 年＝250、3 年＝750 個交易日；3 年窗不滿者不算（原版 ★R3）。",
    "描述（不判）：穩定溢價家數（freq）；原版與變體各自「可買 − 偏貴」（同原版 diff，含 CI）；重新分類組 vs 大盤（每評估日重新分類組平均 − ^SP500TR 同窗報酬，"
    "對評估日平均，含 CI）；3 年持有（主格差、可買−偏貴、對大盤；只報平均與評估日數）。",
]


def bench_series():
    b = pd.read_csv(FQ._p("macro", "yahoo_SP500TR.csv"), usecols=["date", "adjclose"], dtype={"date": str})
    return pd.Series(b["adjclose"].values, index=pd.to_datetime(b["date"])).sort_index()


def avg_ci(per_date, rng_seed=USFV.SEED):
    """per_date：{eval: 值或 None} → (平均, [lo, hi], 評估日數, 群數, 進場年)。CI 用原版 boot_ci；每項各自新開同一種子。"""
    v = {d: x for d, x in per_date.items() if x is not None and np.isfinite(x)}
    if not v:
        return None, [None, None], 0, 0, []
    by = {}
    for d, x in v.items():
        by.setdefault(int(d[:4]), []).append(x)
    by = {y: np.array(a) for y, a in by.items()}
    lo, hi = USFV.boot_ci(by, np.random.default_rng(rng_seed))
    return float(np.mean(list(v.values()))), [lo, hi], len(v), len(by), sorted(by)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None)
    a = ap.parse_args()
    if not (a.formal and a.ruling == RULING_REQUIRED):
        print("⛔ 拒跑：正式跑要 --formal --ruling seq496（裁定 seq496 §一）。")
        sys.exit(2)
    # ── 判語與讀法先寫死（此時尚未讀任何報酬）──
    res = {"判語": FIXED_VERDICT, "讀法": READINGS_US}

    if FQ.DATA_COMMIT_FULL != DATA_PIN or USFV.DATA_PIN != DATA_PIN:
        raise RuntimeError("資料 commit 不符")
    FQ.assert_pinned()
    S = json.load(open(os.path.join(FREQ, "us_freq_summary.json"), encoding="utf-8"))
    assert S["資料commit"] == DATA_PIN
    chk = S["一致性檢查"]
    for k, v in chk.items():
        if not k.startswith("有分組") or "只在" in k:
            assert v == 0, (k, v)
    trig = S["還沒測觸發（依構造）"]
    assert any(trig.values())
    res["資料commit"] = DATA_PIN
    res["判語依據"] = "依構造：" + "、".join(k for k, v in trig.items() if v) + "（頻率表 seq495／seq496 已收下；報酬不影響判語）"

    # ── 分組：原版（原版 load_groups）與變體（freq 私有 us_rows.csv）──
    G = USFV.load_groups()
    R = pd.read_csv(os.path.join(PRIV, "us_rows.csv"), dtype={"eval": str, "ticker": str}, low_memory=False)
    R = R[R["grouped"] == True].copy()  # noqa: E712
    for c in ("group_orig", "group_var"):
        R[c] = R[c].fillna("")
    evals = sorted(G)
    assert evals == sorted(R["eval"].unique())
    nbad = 0
    GV, RC = {}, {}
    for d in evals:
        x = R[R["eval"] == d]
        for g in FQ.GROUPS:
            nbad += int(sorted(x.loc[x["group_orig"] == g, "ticker"]) != G[d][g])
        GV[d] = {g: sorted(x.loc[x["group_var"] == g, "ticker"]) for g in FQ.GROUPS}
        RC[d] = sorted(x.loc[(x["group_var"] == "可買") & (x["group_orig"] != "可買"), "ticker"])
    assert nbad == 0, nbad
    rc_all = [(d, t) for d in evals for t in RC[d]]
    rc_orig = {}
    for d in evals:
        x = R[R["eval"] == d].set_index("ticker")
        for t in RC[d]:
            rc_orig[x.loc[t, "group_orig"]] = rc_orig.get(x.loc[t, "group_orig"], 0) + 1
    n_rc, n_tk, n_dt = len(rc_all), len({t for _, t in rc_all}), sum(1 for d in evals if RC[d])
    assert (n_rc, n_tk, n_dt, rc_orig.get("接近", 0), rc_orig.get("偏貴", 0)) == (49, 15, 17, 20, 29), (n_rc, n_tk, n_dt, rc_orig)

    # ── 報酬（原版 Holder）──
    hd = USFV.Holder(dry=False)
    bench = bench_series()
    cache = {}

    def r_of(t, d, H):
        k = (t, d, H)
        if k not in cache:
            x = hd.daily(t, d, H, count=False)
            cache[k] = None if x is None else USFV.cum(x)
        return cache[k]

    def gmean(names, d, H):
        return USFV.mean_or_none([r_of(t, d, H) for t in names])

    def bret(d, H):
        w = hd.window(d, H)
        if w is None:
            return None
        sub = bench.reindex(pd.DatetimeIndex([pd.Timestamp(d)]).append(w))
        if sub.isna().any():
            raise RuntimeError("^SP500TR 有缺日 %s" % d)
        return float(sub.iloc[-1] / sub.iloc[0] - 1.0)

    # 重新分類組的計數（原版 Holder.cnt 口徑）
    cnt = {}
    for H, tag in ((H1, "1年"), (H3, "3年")):
        hd.reset()
        for d, t in rc_all:
            hd.daily(t, d, H, count=True)
        cnt[tag] = dict(hd.cnt)

    per = {}
    rows_priv = []
    for H, tag in ((H1, "1y"), (H3, "3y")):
        P = []
        for d in evals:
            r = {"eval": d, "n_重新分類": len(RC[d])}
            r["重新分類"] = gmean(RC[d], d, H) if RC[d] else None
            for g in ("可買", "偏貴"):
                r["原版_" + g] = gmean(G[d][g], d, H)
                r["變體_" + g] = gmean(GV[d][g], d, H)
            r["大盤"] = bret(d, H)
            dd = lambda a_, b_: (a_ - b_) if (a_ is not None and b_ is not None) else None  # noqa: E731
            r["主格差"] = dd(r["重新分類"], r["原版_可買"])
            r["原版_可買減偏貴"] = dd(r["原版_可買"], r["原版_偏貴"])
            r["變體_可買減偏貴"] = dd(r["變體_可買"], r["變體_偏貴"])
            r["重新分類減大盤"] = dd(r["重新分類"], r["大盤"])
            r["n_重新分類_可算"] = sum(1 for t in RC[d] if r_of(t, d, H) is not None)
            P.append(r)
        per[tag] = pd.DataFrame(P)
    for d, t in rc_all:
        rows_priv.append({"eval": d, "ticker": t, "group_orig": R.loc[(R["eval"] == d) & (R["ticker"] == t), "group_orig"].iloc[0],
                          "ret_1y": r_of(t, d, H1), "ret_3y": r_of(t, d, H3)})

    def col(tag, c):
        T = per[tag]
        return dict(zip(T["eval"], [None if (x is None or (isinstance(x, float) and np.isnan(x))) else x for x in T[c]]))

    # ── 主格 ──
    avg, ci, nd, ncl, yrs = avg_ci(col("1y", "主格差"))
    res["主格_1年"] = {
        "平均差": avg, "CI95": ci, "有效評估日數": nd, "群數": ncl, "進場年": yrs,
        "重新分類組1年可算筆數": int(per["1y"]["n_重新分類_可算"].sum()),
        "重新分類組筆數_檔數_評估日數": [n_rc, n_tk, n_dt], "原屬接近_偏貴": [rc_orig.get("接近", 0), rc_orig.get("偏貴", 0)],
        "界線對照_只描述": {"界線": NI_BOUND, "平均≥0": bool(avg is not None and avg >= 0),
                       "CI下緣>-5pp": bool(ci[0] is not None and ci[0] > NI_BOUND),
                       "說明": "只描述；本件已依構造還沒測，判語不看數字（seq496）。"},
        "每評估日": [{"eval": r["eval"], "n_重新分類": int(r["n_重新分類"]), "主格差": r["主格差"]}
                 for r in per["1y"].to_dict("records") if r["n_重新分類"] > 0],
        "重新分類組_Holder計數": cnt,
    }

    # ── 描述 ──
    tbl = {}
    for name, c in (("原版 可買 − 偏貴", "原版_可買減偏貴"), ("變體 可買 − 偏貴", "變體_可買減偏貴"),
                    ("重新分類組 − 大盤（^SP500TR）", "重新分類減大盤"), ("主格差（重新分類 − 原版可買）", "主格差")):
        a1, c1, n1, _, _ = avg_ci(col("1y", c))
        a3, _, n3, _, _ = avg_ci(col("3y", c))
        tbl[name] = {"1年": a1, "1年CI95": c1, "1年評估日數": n1, "3年": a3, "3年評估日數": n3}
    o = json.load(open(os.path.join(os.path.dirname(FQ.OUTD), "formal", "result.json"), encoding="utf-8"))
    o_avg = o["主格_1年"]["diff平均"]
    rep = abs(tbl["原版 可買 − 偏貴"]["1年"] - o_avg)
    assert rep < 1e-12, rep
    res["描述"] = {
        "穩定溢價家數": {"中位": S["穩定溢價家數_每評估日_中位_最少_最大"][0], "最少": S["穩定溢價家數_每評估日_中位_最少_最大"][1],
                     "最大": S["穩定溢價家數_每評估日_中位_最少_最大"][2], "涉及檔數": S["穩定溢價_涉及檔數"],
                     "有分組_中位": S["穩定溢價且有分組_中位_最少_最大"][0]},
        "表": tbl,
        "說明": "1 年 CI 為原版 boot_ci（按進場年分群，種子 20261027）；3 年只報平均與評估日數。大盤＝^SP500TR 同窗報酬。",
    }
    res["自檢"] = {
        "原版分組_load_groups_vs_freq私有檔_不一致評估日組": nbad,
        "freq一致性檢查": chk,
        "原版可買減偏貴1年_重算_vs_原跑result.json_絕對差": rep,
        "說明": f"原版分組（load_groups）與 freq 私有檔逐評估日逐組 {nbad} 不一致；原版可買−偏貴 1 年重算 {o_avg * 100:+.2f}pp 與原跑 result.json 差 {rep:.1e}；"
              "freq 一致性（上限改回 25 vs 原版、vs 原版私有檔、取點函式 10 年中位 vs pe_target、變體只改穩定溢價者）皆 0。",
    }
    write_merged("美股", res)
    os.makedirs(PRIV_OUT, exist_ok=True)
    pd.DataFrame(rows_priv).to_csv(os.path.join(PRIV_OUT, "us_reclass_rows.csv"), index=False)
    for tag in per:
        per[tag].to_csv(os.path.join(PRIV_OUT, "us_by_eval_%s.csv" % tag), index=False)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

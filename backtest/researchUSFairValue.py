# -*- coding: utf-8 -*-
"""美股合理價機械版——描述欄與判定（正式跑程式）。⛔ 目前只准 --dry（裁定 seq480：先交頻率表＋全部描述欄乾跑，核後正式跑）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSFairValue --dry
    （正式：... --ruling seq480 ；⛔ 沒帶 --ruling seq480 一律拒跑正式；seq366：⛔ 不准任何含報酬的試跑或子樣本）

登錄：產業 seq63（ab44c6850399ff57）§二報酬、§三判定；發號 裁定 seq480 §一（N_單筆 +1、N_組合 +1；3 年只描述）；
描述欄：裁定 seq458（全部描述欄都要有）。分組來源 ＝ researchUSFairValue_freq 的逐檔分類（同一支程式、同一資料 commit）。

報酬口徑（seq63 §二，逐條）：
  - 評估日 d 收盤進場；1 年 ＝ d 之後 250 個交易日（日曆＝yahoo_GSPC），3 年 ＝ 750 個交易日；ret 連乘（panel 的 ret 已含息）。
  - 持有期間 panel 結束（下市、被併）⇒ 結束前累積報酬，之後算現金 0%。
  - 在指數期間整段沒有價格的（no_ohlc，SIVB、FRC、SBNY 等 35 檔）若進了任一組 ⇒ 該筆記 −100%，報筆數。
  - 來源切換日 ret 空白 ⇒ 該日記 0，報筆數。
  ★R1 panel 中途沒有列的交易日（gap 段、跨日列）⇒ 該日沒有報酬（記 0，下一列的 ret 本來就跨日者照用）；報筆數。
  ★R2 移出指數後（in_index=0）的列照用到 panel 結束（登錄字面「panel 結束」才停）；報筆數。〔另一讀法：移出即停〕
  ★R3 3 年只收 d+750 個交易日在資料尾之內的評估日；不滿的不算 3 年（報筆數）。
判定（seq63 §三，主格 1 年）：
  - 每評估日 diff_d ＝ 可買平均 − 偏貴平均（★R4 兩組都非空的評估日才有 diff_d；空的報筆數）。
  - 平均 diff ＞ 0、按進場年（評估日的年）分群 bootstrap（★R5 10,000 次、種子 20261027、百分位法）95% CI 下緣 ＞ 0、
    前段（2019–2021 進場）與後段（2022–2025）各自平均 ＞ 0 ⇒ 通過；其餘（含方向為負）⇒ 測不出。
  - 樣本不足：可買或偏貴任一組在一半以上評估日 < 3 檔 ⇒ 判樣本不足、不下判定（優先）。
  - 對大盤（次要，N_組合）：可買袖（每評估日開一袖、持 250 日、袖內同權買進持有；★R6 空袖 ＝ 現金 0%；
    組合每日報酬 ＝ 當天所有存續袖的日報酬平均）年化 ＞ 大盤年化，且 年化÷|最大回落| ≥ 大盤同比值，兩格都成立。
    大盤 ＝ ^SP500TR（data/macro/yahoo_SP500TR.csv adjclose，總報酬）。★R7 年化 ＝ NAV^(252/交易日數)−1；
    ★R8 最大回落 ＝ 0 時 年化÷|最大回落| 記 None（不除以 0），該格判「不可比」。區間 ＝ 第一個評估日次日到最後一袖結束。
  - 3 年：只描述（各組平均、diff 平均），不判。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSFairValue_freq as FQ   # noqa: E402

H1, H3 = 250, 750
SEED, NBOOT = 20261027, 10000
FRONT = (2019, 2021)
BACK = (2022, 2025)
ANN_DAYS = 252


# ═════════════ 讀分組（同一支 freq 程式的輸出）═════════════
def load_groups():
    p = os.path.join(FQ.PRIVD, "classify_by_eval_ticker.csv")
    sj = os.path.join(FQ.OUTD, "freq_summary.json")
    S = json.load(open(sj, encoding="utf-8"))
    if S["資料commit"] != FQ.DATA_COMMIT_FULL:
        raise RuntimeError("分組檔的資料 commit 不符")
    R = pd.read_csv(p, dtype={"eval": str, "ticker": str}, low_memory=False)
    ok = R[(R["stage"] == "pop") & (R["all_pass"] == True) & (R["val"] == "ok")]  # noqa: E712
    G = {}
    for d in sorted(R["eval"].unique()):
        x = ok[ok["eval"] == d]
        G[d] = {g: sorted(x.loc[x["group"] == g, "ticker"]) for g in FQ.GROUPS}
        G[d]["過門檻全部"] = sorted(x["ticker"])
    return G


# ═════════════ 單筆持有 ═════════════
class Holder:
    def __init__(self, dry):
        self.dry = dry
        self.cal = FQ.calendar()
        self.no_ohlc = self._no_ohlc()
        self.reset()

    def reset(self):
        self.cnt = {"minus100": 0, "switch_blank_days": 0, "gap_days": 0, "post_removal_days": 0,
                    "panel_end_cash": 0, "incomplete_window": 0, "entries": 0}

    def _no_ohlc(self):
        s = pd.read_csv(FQ._p("panel", "_segments.csv"), dtype=str, keep_default_na=False)
        cov = set(s.loc[s["kind"] == "covered", "ticker"])
        return set(FQ.universe_table()["ticker"]) - cov

    def window(self, d, H):
        i = self.cal.get_loc(pd.Timestamp(d))
        w = self.cal[i + 1:i + 1 + H]
        return w if len(w) == H else None

    def daily(self, t, d, H, count=True):
        """→ np.array（長 H）每日報酬，或 None（窗不滿）。"""
        w = self.window(d, H)
        if count:
            self.cnt["entries"] += 1
        if w is None:
            if count:
                self.cnt["incomplete_window"] += 1
            return None
        r = np.zeros(H)
        if t in self.no_ohlc:                      # seq63：整段無價格進組 ⇒ −100%
            if count:
                self.cnt["minus100"] += 1
            r[0] = -1.0
            return r
        pn = FQ.panel(t)
        sub = pn.reindex(w)
        last = pn.index.max()
        blank = sub["in_index"].notna().values & sub["ret"].isna().values
        gap = (~sub["in_index"].notna().values) & (w <= last)
        post = sub["in_index"].notna().values & (sub["in_index"].fillna(1).values == 0)
        if count:
            self.cnt["switch_blank_days"] += int(blank.sum())
            self.cnt["gap_days"] += int(gap.sum())
            self.cnt["post_removal_days"] += int(post.sum())
            if last < w[-1]:
                self.cnt["panel_end_cash"] += 1
        if self.dry:
            return r                                # ⛔ 乾跑：ret 全設 0
        v = sub["ret"].values.astype(float)
        v[~np.isfinite(v)] = 0.0
        r[:] = v
        return r


def cum(r):
    return float(np.prod(1.0 + r) - 1.0)


# ═════════════ 統計 ═════════════
def mean_or_none(x):
    x = [v for v in x if v is not None and np.isfinite(v)]
    return float(np.mean(x)) if x else None


def boot_ci(diffs_by_year, rng):
    yrs = sorted(diffs_by_year)
    if len(yrs) < 2:
        return None, None
    out = np.empty(NBOOT)
    for b in range(NBOOT):
        pick = rng.choice(len(yrs), len(yrs), replace=True)
        vals = np.concatenate([diffs_by_year[yrs[k]] for k in pick])
        out[b] = vals.mean()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def nav_stats(daily):
    nav = np.cumprod(1.0 + np.asarray(daily))
    n = len(nav)
    if n == 0:
        return None, None, None
    ann = float(nav[-1] ** (ANN_DAYS / n) - 1.0) if nav[-1] > 0 else -1.0
    mdd = float(np.min(nav / np.maximum.accumulate(np.r_[1.0, nav])[1:] - 1.0))
    mdd = min(mdd, 0.0)
    ratio = None if mdd == 0 else ann / abs(mdd)       # ★R8
    return ann, mdd, ratio


def run(dry):
    FQ.assert_pinned()
    G = load_groups()
    S0 = json.load(open(os.path.join(FQ.OUTD, "freq_summary.json"), encoding="utf-8"))
    hd = Holder(dry)
    evals = sorted(G)
    res = {"dry": dry, "資料commit": FQ.data_commit(), "評估日數": len(evals)}
    # ── 1 年／3 年 各組 ──
    per = {}
    cnts = {}
    for H, tag in ((H1, "1y"), (H3, "3y")):
        hd.reset()
        rows = []
        for d in evals:
            r = {"eval": d}
            for g in FQ.GROUPS + ("過門檻全部",):
                vals = []
                for t in G[d][g]:
                    x = hd.daily(t, d, H, count=(g != "過門檻全部"))
                    if x is not None:
                        vals.append(cum(x))
                r[g] = mean_or_none(vals)
                r["n_" + g] = len(vals)
            r["diff"] = (r["可買"] - r["偏貴"]) if (r["可買"] is not None and r["偏貴"] is not None) else None
            rows.append(r)
        per[tag] = pd.DataFrame(rows)
        cnts[tag] = dict(hd.cnt)
    res["筆數（可買／接近／偏貴 的 (評估日,檔)）"] = cnts
    # ── 主格（1 年）──
    T = per["1y"]
    dv = T.dropna(subset=["diff"])
    by_year = {}
    for d, x in zip(dv["eval"], dv["diff"]):
        by_year.setdefault(int(d[:4]), []).append(x)
    by_year = {y: np.array(v) for y, v in by_year.items()}
    rng = np.random.default_rng(SEED)
    lo, hi = boot_ci(by_year, rng)
    avg = float(dv["diff"].mean()) if len(dv) else None
    fr = dv[dv["eval"].str[:4].astype(int).between(*FRONT)]["diff"]
    bk = dv[dv["eval"].str[:4].astype(int).between(*BACK)]["diff"]
    front = float(fr.mean()) if len(fr) else None
    back = float(bk.mean()) if len(bk) else None
    insufficient = bool(S0["樣本不足"]["觸發"])
    if insufficient:
        verdict = "樣本不足（不下判定）"
    elif None in (avg, lo, front, back):
        verdict = "測不出（有格不可算）"
    elif avg > 0 and lo > 0 and front > 0 and back > 0:
        verdict = "通過"
    else:
        verdict = "測不出"
    res["主格_1年"] = {"diff平均": avg, "CI95": [lo, hi], "前段2019-2021": front, "後段2022-2025": back,
                     "有diff的評估日": int(len(dv)), "兩組有空的評估日": int(len(T) - len(dv)),
                     "分群數": len(by_year), "判定": verdict}
    res["各組平均"] = {tag: {g: mean_or_none(per[tag][g].tolist()) for g in FQ.GROUPS + ("過門檻全部",)}
                   for tag in per}
    res["各組平均_評估日數"] = {tag: {g: int(per[tag][g].notna().sum()) for g in FQ.GROUPS + ("過門檻全部",)}
                        for tag in per}
    T3 = per["3y"].dropna(subset=["diff"])
    res["3年_只描述"] = {"diff平均": float(T3["diff"].mean()) if len(T3) else None, "評估日數": int(len(T3))}
    # ── 對大盤（可買袖）──
    cal = FQ.calendar()
    i0 = cal.get_loc(pd.Timestamp(evals[0])) + 1
    i1 = cal.get_loc(pd.Timestamp(evals[-1])) + H1
    days = cal[i0:i1 + 1]
    pos = {d: k for k, d in enumerate(days)}
    acc = np.zeros(len(days))
    cnt = np.zeros(len(days))
    empty_sleeves = 0
    for d in evals:
        w = hd.window(d, H1)
        names = G[d]["可買"]
        paths = [hd.daily(t, d, H1, count=False) for t in names]
        paths = [p for p in paths if p is not None]
        if not paths:
            empty_sleeves += 1
            sr = np.zeros(H1)
        else:
            navs = np.cumprod(1.0 + np.vstack(paths), axis=1).mean(axis=0)
            prev = np.r_[1.0, navs[:-1]]
            sr = np.where(prev > 0, navs / prev - 1.0, 0.0)
        for k, day in enumerate(w):
            j = pos[day]
            acc[j] += sr[k]
            cnt[j] += 1
    port = np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0)
    if dry:
        bm = np.zeros(len(days))
    else:
        b = pd.read_csv(FQ._p("macro", "yahoo_SP500TR.csv"), usecols=["date", "adjclose"], dtype={"date": str})
        b = pd.Series(b["adjclose"].values, index=pd.to_datetime(b["date"])).sort_index()
        b = b.reindex(cal[i0 - 1:i1 + 1])
        if b.isna().any():
            raise RuntimeError("^SP500TR 有缺日")
        bm = (b.values[1:] / b.values[:-1] - 1.0)
    a1, m1, r1 = nav_stats(port)
    a2, m2, r2 = nav_stats(bm)
    c1 = (a1 is not None and a2 is not None and a1 > a2)
    c2 = None if (r1 is None or r2 is None) else bool(r1 >= r2)
    res["對大盤"] = {"可買袖": {"年化": a1, "最大回落": m1, "年化÷|回落|": r1},
                  "大盤SP500TR": {"年化": a2, "最大回落": m2, "年化÷|回落|": r2},
                  "格1_年化勝": bool(c1), "格2_比值不輸": c2 if c2 is not None else "不可比（回落為 0）",
                  "判定": ("通過" if (c1 and c2) else "不通過"), "空袖數": empty_sleeves,
                  "區間": [str(days[0].date()), str(days[-1].date())], "交易日數": int(len(days))}
    return res, per


def selftest():
    """乾跑自檢：空組、單一分群、回落 0、全 −100%。"""
    out = {}
    out["mean_空"] = mean_or_none([])
    out["boot_單一群"] = boot_ci({2019: np.array([0.0])}, np.random.default_rng(1))
    out["boot_兩群"] = boot_ci({2019: np.array([0.0]), 2020: np.array([0.0, 0.0])}, np.random.default_rng(1))
    out["nav_零"] = nav_stats(np.zeros(10))
    out["nav_空"] = nav_stats(np.zeros(0))
    out["nav_全賠"] = nav_stats(np.r_[-1.0, np.zeros(9)])
    out["cum_-100"] = cum(np.r_[-1.0, np.zeros(H1 - 1)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default=None)
    a = ap.parse_args()
    if not a.dry and a.ruling != "seq480":
        print("⛔ 拒跑正式：要 --ruling seq480（裁定 seq480 §一：核後才正式跑）。乾跑請加 --dry。")
        sys.exit(2)
    res, per = run(a.dry)
    res["selftest"] = selftest()
    if a.dry:
        res["說明"] = "乾跑：ret 與大盤全設 0；只驗程式路徑（無除以 0、空組不出錯）與筆數。⛔ 不含任何報酬。"
        p = os.path.join(FQ.OUTD, "dry_run.json")
    else:
        p = os.path.join(os.path.dirname(FQ.OUTD), "formal", "result.json")
    FQ.jdump(res, p)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

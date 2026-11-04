# -*- coding: utf-8 -*-
"""美股合理價機械版——「穩定溢價本益比 35」變體：頻率表＋描述欄乾跑（⛔ 不算任何報酬）。

登錄：產業 seq82（pw1 sha f79e37d619c9fb0f）；發號：裁定 seq495 §一（N_單筆 +2：台股、美股各 1；判語照〈四十九〉）。
原版：美股合理價機械版（產業 seq63 ab44c6850399ff57；backtest/researchUSFairValue_freq.py＋researchUSFairValue.py，
      資料 us-stock-data 89d9f8550f6ea39b392087c22998cd298164a26c＝原跑那一版，~/usdata/89d9f8550 唯讀快照，.commit 開跑先驗）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSStablePE35_freq

私有庫規矩：repo 的 resultsStablePE35/freq/ 只放彙總數字與每評估日筆數；逐檔明細（代號）只寫 ~/us_work/stablepe35/（repo 外）。

程式重用（⛔ 不改原版檔、不寫第二份實作）：
  - 母體、四條品質門檻、E0、g、配息率、分組：直接呼叫 researchUSFairValue_freq.classify()（原版逐字；★1～★22 全照舊）。
  - 本益比中位數（未截頂）：呼叫原版 pe_target()，呼叫期間把模組常數 PE_CAP 暫設 inf，呼叫完復原。
  - 變體合理價：原版 fair_value()（折現 10%）＋ group_of()（門檻 1.00／1.15）；只換 pe_T。
  - 財年窗、年度淨利／權益／營業利益、單季 EPS、近四季 EPS、價格與分割：原版 Fund.fy_window／annual_sum／row／eps_q／ttm_eps、
    price_file、split_list。
  - 描述欄乾跑：researchUSFairValue.Holder(dry=True)（ret 一律 0，只判窗滿不滿）。

══════════ 新登錄規則（seq82 §二逐字）══════════
 穩定溢價（評估日當天三條全過才算）：
  1. 最近 5 個完整財年，每年 ROE ≥ 20%。
  2. 5 年沒有虧損，而且沒有任何一年 EPS 比前一年跌超過 30%。
  3. 評估日前 5 年（最少 3 年）季末本益比的第 25 百分位 ≥ 30。
 變體估值：穩定溢價者 pe_T＝min(評估日前本益比中位數, 35)；其餘照原版 min(中位數, 25)。折現 10%、分組門檻不變。
 重新分類組：變體判「可買」、原版不是「可買」的（公司 × 評估日）。

══════════ ★ 執行者定（看任何數字前寫死；另一讀法寫在〔〕）══════════
 ★S1 「最近 5 個完整財年」＝原版 ★4 的 fy_window（e* 與往前 4 年）；★17 資料過舊照原版 ⇒ 不可算。
      ROE＝年度淨利（4 季相加）÷ 第四季末權益（★16：equity 缺用 equity_incl_nci）；權益 ≤ 0 ⇒ 該年不過。
      有缺值：已知任一年不過 ⇒ 不過；否則有缺 ⇒ 不可算（原版 ★5 精神：結果與缺值無關才判）。
 ★S2 虧損年照原版 ★5②（年度淨利 < 0 且年度營業利益 ≤ 0；營業利益缺 ⇒ 不可判）。
      EPS＝年度稀釋 EPS（4 季單季 EPS 照原版裁定① eps_q 相加、調同基礎；同原版 ③）。
      「任何一年比前一年跌超過 30%」只比 5 年窗內相鄰 4 對；前一年 EPS ≤ 0 ⇒ 該對不過；任一年 EPS 不可算 ⇒ 該對不可算。
      第 2 條＝已知虧損或已知跌 > 30% ⇒ 不過；否則有不可算 ⇒ 不可算；否則過。
      〔另一讀法：連窗首年也和前一年比（共 5 對）⇒ 描述欄照報，不改判〕。
 ★S3 季末本益比點＝原版 ★1／★3 的同一組季末點（quarter_points：季末日曆日前最後一個交易日）、同一算法
      （評估日 panel src 價格檔收盤 ÷ 當時可得近四季 EPS；近四季 EPS ≤ 0 或不可算 ⇒ 該點略過；只收 > 0）。
      窗＝[評估日 − 5 年, 評估日]（原版 ★3 含評估日當天的點）；「最少 3 年」＝最早一點 ≤ 評估日 − 3 年（原版 ★3 同寫法）；
      不滿 ⇒ 第 3 條不可算。第 25 百分位用 numpy 線性內插。
      自檢：同一取點函式改 10 年窗取中位數，須與原版 pe_target（未截頂）逐筆相同。
 ★S4 任一條不可算 ⇒ 不算穩定溢價（變體 pe_T 照原版 25）；照報筆數。分母＝原版母體（stage＝pop：在指數、市值 ≥ 100 億）；
      另報其中四條品質門檻全過且合理價可算（有分組）者。
 ★S5 進場年＝評估日所在年（原版 researchUSFairValue 同）；群數＝重新分類組出現的評估日之進場年個數。
 ★S6 描述欄乾跑：1 年／3 年可算＝Holder(dry).daily 窗滿（不讀 ret 值）；大盤可算＝窗內每日都在 ^SP500TR 檔的日期內（只讀日期欄）。
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.dont_write_bytecode = True
from backtest import researchUSFairValue_freq as FQ   # noqa: E402
from backtest import researchUSFairValue as USFV     # noqa: E402

DATA_PIN = "89d9f8550f6ea39b392087c22998cd298164a26c"
REG = "產業 seq82 pw1 f79e37d619c9fb0f"
RULING = "裁定 seq495 §一"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsStablePE35", "freq")
PRIV = os.path.expanduser("~/us_work/stablepe35")
H1, H3 = USFV.H1, USFV.H3
PE_CAP_STABLE = 35.0
ROE_STABLE, EPS_DROP_MAX, PE_P25_MIN = 0.20, -0.30, 30.0
PE_WIN_YEARS = 5
MIN_N, MIN_DATES, MIN_CLUSTERS = 20, 8, 24


# ═════════════ 小工具（呼叫原版函式）═════════════
def pe_median_uncapped(F, d, src, splits, close):
    old = FQ.PE_CAP
    FQ.PE_CAP = float("inf")
    try:
        return FQ.pe_target(F, d, src, splits, close)[0]
    finally:
        FQ.PE_CAP = old


def pe_points(F, d, splits, close, years):
    """★S3：原版 pe_target 的同一取點（只把回看年數當參數）。→ (vals, dates)。"""
    vals, dates = [], []
    for q in FQ.quarter_points():
        if q > d or q < d - pd.DateOffset(years=years):
            continue
        if q not in close.index:
            continue
        ttm, _ = F.ttm_eps(q, splits)
        if ttm is None or ttm <= 0:
            continue
        pe = close.loc[q] / ttm
        if pe > 0:
            vals.append(pe)
            dates.append(q)
    return vals, dates


def annual_eps(F, qs, d, splits):
    if qs is None:
        return None
    tot = 0.0
    for pe in qs:
        v, _ = F.eps_q(pe, d, splits)
        if v is None:
            return None
        tot += v
    return tot


def year_before(F, estar, d):
    """另一讀法用：e* 往前第 5 年的財年 4 季（同 fy_window 的 ±20 日找法）。"""
    ni = F.F["net_income"]
    tgt = estar - pd.DateOffset(years=5)
    for pe in ni["period_end"][(ni["period_end"] - tgt).abs() <= pd.Timedelta(days=20)]:
        qq = F.fy_quarters(pe)
        if qq is not None:
            return qq
    return None


def cond12(F, d, splits):
    W = F.fy_window(d)
    if W is None:
        return "na", "na", "no_fy", None
    if (d - W[0][0]).days > FQ.STALE_FY_DAYS:
        return "na", "na", "stale_fy", None
    # 1. ROE ≥ 20% 每年
    fail = miss = 0
    nis = []
    for e, qs in W:
        n = F.annual_sum("net_income", qs, d)
        nis.append(n)
        eq = F.row("equity", e, d) if qs is not None else None
        if eq is None and qs is not None and not FQ.ALT["equity_strict"]:
            eq = F.row("equity_incl_nci", e, d)
        if eq is not None and eq["value"] <= 0:
            fail += 1
            continue
        if n is None or eq is None:
            miss += 1
            continue
        if n / eq["value"] < ROE_STABLE:
            fail += 1
    c1 = "fail" if fail else ("na" if miss else "pass")
    # 2. 無虧損（原版 ②）＋ EPS 未跌 > 30%
    loss = unk = 0
    for (e, qs), n in zip(W, nis):
        if n is None:
            unk += 1
        elif n < 0:
            oi = F.annual_sum("operating_income", qs, d)
            if oi is None:
                unk += 1
            elif oi <= 0:
                loss += 1
    eps = [annual_eps(F, qs, d, splits) for _, qs in reversed(W)]      # 舊→新

    def pair_state(a, b):
        if a is None or b is None:
            return "na"
        if a <= 0 or (b / a - 1) < EPS_DROP_MAX:
            return "fail"
        return "pass"
    ps = [pair_state(a, b) for a, b in zip(eps[:-1], eps[1:])]
    if loss or "fail" in ps:
        c2 = "fail"
    elif unk or "na" in ps:
        c2 = "na"
    else:
        c2 = "pass"
    # 另一讀法：多比窗首年與前一年
    alt = None
    if c2 == "pass":
        e0 = annual_eps(F, year_before(F, W[0][0], d), d, splits)
        alt = pair_state(e0, eps[0])
    return c1, c2, "ok", alt


def cond3(F, d, splits, close):
    vals, dates = pe_points(F, d, splits, close, PE_WIN_YEARS)
    if not dates or dates[0] > d - pd.DateOffset(years=FQ.PE_MIN_YEARS):
        return "na", None, len(vals)
    p25 = float(np.percentile(np.asarray(vals, dtype=float), 25))
    return ("pass" if p25 >= PE_P25_MIN else "fail"), p25, len(vals)


def var_group(rec, med, cap):
    if rec.get("E0_le0"):
        return FQ.group_of(float("inf"))
    peT = min(med, cap)
    fv = FQ.fair_value(rec["E0"], rec["g"], peT, rec["payout"])
    return FQ.group_of(rec["close"] / fv if fv > 0 else float("inf"))


# ═════════════ 主程式 ═════════════
def main():
    import time
    t0 = time.time()
    if FQ.DATA_COMMIT_FULL != DATA_PIN:
        raise RuntimeError("原版 freq 的資料 commit ≠ %s" % DATA_PIN)
    FQ.assert_pinned()
    evs = list(FQ.eval_dates())
    univ = list(FQ.universe_table()["ticker"])
    hd = USFV.Holder(dry=True)
    bdates = set(pd.to_datetime(pd.read_csv(FQ._p("macro", "yahoo_SP500TR.csv"), usecols=["date"], dtype=str)["date"]))
    orig = pd.read_csv(os.path.join(FQ.PRIVD, "classify_by_eval_ticker.csv"), dtype={"eval": str, "ticker": str},
                       usecols=["eval", "ticker", "stage", "all_pass", "val", "group"], low_memory=False)
    orig = orig[(orig["stage"] == "pop") & (orig["all_pass"] == True) & (orig["val"] == "ok")]  # noqa: E712
    OG = dict(zip(zip(orig["eval"], orig["ticker"]), orig["group"]))

    recs = []
    for d in evs:
        st = Counter()
        ds = str(d.date())
        for t in univ:
            r = FQ.classify(t, d, st)
            if r.get("stage") != "pop":
                continue
            src, cik = r["src"], r.get("cik")
            F = FQ.fund(t, cik)
            close, _ = FQ.price_file(src)
            splits, _ = FQ.split_list(t, src, cik)
            c1, c2, why, alt = cond12(F, d, splits)
            c3, p25, npts = cond3(F, d, splits, close)
            stable = c1 == "pass" and c2 == "pass" and c3 == "pass"
            grouped = bool(r.get("all_pass")) and r.get("val") == "ok"
            rec = dict(eval=ds, entry_year=d.year, ticker=t, c1=c1, c2=c2, c3=c3, why12=why, pe_p25=p25, pe_q_pts=npts,
                       stable=stable, stable_alt5pairs=bool(stable and alt == "pass"),
                       all_pass=bool(r.get("all_pass")), val=r.get("val"), grouped=grouped,
                       group_orig=r.get("group") if grouped else "", group_orig_file=OG.get((ds, t), ""))
            rec["group_var"] = rec["group_chk25"] = ""
            rec["pe_med_check_ok"] = None
            if grouped:
                med = pe_median_uncapped(F, d, src, splits, close)
                v10, _ = pe_points(F, d, splits, close, FQ.PE_LOOKBACK_YEARS)
                rec["pe_med_check_ok"] = bool(len(v10) and float(np.median(v10)) == med)
                rec["pe_med"] = med
                rec["group_var"] = var_group(r, med, PE_CAP_STABLE if stable else FQ.PE_CAP)
                rec["group_chk25"] = var_group(r, med, FQ.PE_CAP)
                for H, tag in ((H1, "1y"), (H3, "3y")):
                    w = hd.window(d, H)
                    rec["ok_" + tag] = hd.daily(t, d, H, count=False) is not None
                    rec["mkt_" + tag] = bool(w is not None and d in bdates and all(x in bdates for x in w))
            recs.append(rec)
        print(ds, "done %.0fs" % (time.time() - t0), flush=True)
    R = pd.DataFrame(recs)
    for c in ("ok_1y", "ok_3y", "mkt_1y", "mkt_3y"):
        R[c] = R[c].fillna(False).astype(bool)
    R["reclass"] = (R["group_var"] == "可買") & (R["group_orig"] != "可買")
    os.makedirs(PRIV, exist_ok=True)
    R.to_csv(os.path.join(PRIV, "us_rows.csv"), index=False)     # 私有：逐檔明細

    # Holder 計數（只對重新分類組，count=True 重走一次；dry ⇒ 不讀 ret 值）
    hd.reset()
    for ds, t in R.loc[R["reclass"], ["eval", "ticker"]].itertuples(index=False):
        hd.daily(t, ds, H1, count=True)
    holder_cnt_1y = dict(hd.cnt)

    G = R[R["grouped"]]
    chk = {
        "有分組(評估日,檔)_本檔": int(len(G)), "有分組_原版私有檔": int(len(OG)),
        "有分組只在本檔": len(set(zip(G["eval"], G["ticker"])) - set(OG)),
        "有分組只在原版檔": len(set(OG) - set(zip(G["eval"], G["ticker"]))),
        "原版分組_重跑classify_vs_原版私有檔_不一致": int((G["group_orig"] != G["group_orig_file"]).sum()),
        "變體上限改回25_vs_原版分組_不一致": int((G["group_chk25"] != G["group_orig"]).sum()),
        "變體上限改回25_vs_原版私有檔_不一致": int((G["group_chk25"] != G["group_orig_file"]).sum()),
        "變體只改穩定溢價者_非穩定溢價卻改組": int(((G["group_var"] != G["group_orig"]) & ~G["stable"]).sum()),
        "取點函式10年中位_vs_原版pe_target未截頂_不一致": int((G["pe_med_check_ok"] != True).sum()),  # noqa: E712
    }

    rows = []
    for (ds, ey), d in R.groupby(["eval", "entry_year"], sort=True):
        g = d[d["grouped"]]
        rc = d[d["reclass"]]
        ob = d[d["group_orig"] == "可買"]
        r = {"eval": ds, "entry_year": int(ey), "母體": int(len(d)), "有分組": int(len(g)),
             "穩定溢價": int(d["stable"].sum()), "穩定溢價_有分組": int(g["stable"].sum()),
             "條1_ROE20_過": int((d["c1"] == "pass").sum()), "條2_無虧損且EPS未跌30_過": int((d["c2"] == "pass").sum()),
             "條3_季末PE_p25ge30_過": int((d["c3"] == "pass").sum()),
             "條1_不可算": int((d["c1"] == "na").sum()), "條2_不可算": int((d["c2"] == "na").sum()),
             "條3_不可算": int((d["c3"] == "na").sum()), "穩定溢價_另一讀法5對": int(d["stable_alt5pairs"].sum())}
        for gg in FQ.GROUPS:
            r["原版_" + gg] = int((d["group_orig"] == gg).sum())
            r["變體_" + gg] = int((d["group_var"] == gg).sum())
        r["重新分類組"] = int(len(rc))
        r["重新分類組_原接近"] = int((rc["group_orig"] == "接近").sum())
        r["重新分類組_原偏貴"] = int((rc["group_orig"] == "偏貴").sum())
        r["乾跑_重新分類_1年可算"] = int(rc["ok_1y"].sum())
        r["乾跑_原版可買_1年可算"] = int(ob["ok_1y"].sum())
        r["乾跑_主格差可算"] = bool(rc["ok_1y"].sum() > 0 and ob["ok_1y"].sum() > 0)
        for tag in ("orig", "var"):
            b = d[(d["group_" + tag] == "可買") & d["ok_1y"]]
            e = d[(d["group_" + tag] == "偏貴") & d["ok_1y"]]
            r["乾跑_%s_可買減偏貴_1年可算" % tag] = bool(len(b) > 0 and len(e) > 0)
        r["乾跑_重新分類對大盤_1年可算"] = bool(rc["ok_1y"].sum() > 0 and rc["mkt_1y"].all())
        r["乾跑_重新分類_3年可算"] = int(rc["ok_3y"].sum())
        r["乾跑_主格差_3年可算"] = bool(rc["ok_3y"].sum() > 0 and ob["ok_3y"].sum() > 0)
        rows.append(r)
    T = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    T.to_csv(os.path.join(OUT, "us_freq_by_eval.csv"), index=False, encoding="utf-8-sig")

    rc = R[R["reclass"]]
    dates_rc = sorted(rc["eval"].unique())
    yrs_rc = sorted(int(x) for x in rc["entry_year"].unique())
    main_dates = T[T["乾跑_主格差可算"]]
    trig = {"重新分類組<20筆": bool(len(rc) < MIN_N), "出現評估日<8": bool(len(dates_rc) < MIN_DATES),
            "進場年群數<24": bool(len(yrs_rc) < MIN_CLUSTERS)}
    pop = R
    S = {
        "登錄": REG, "發號": RULING, "資料commit": FQ.data_commit(),
        "評估日數": int(len(T)), "評估日": [T["eval"].iloc[0], T["eval"].iloc[-1]],
        "原版可能的進場年": sorted({d.year for d in evs}), "原版可能的群數上限": len({d.year for d in evs}),
        "穩定溢價家數_每評估日_中位_最少_最大": [float(T["穩定溢價"].median()), int(T["穩定溢價"].min()), int(T["穩定溢價"].max())],
        "穩定溢價且有分組_中位_最少_最大": [float(T["穩定溢價_有分組"].median()), int(T["穩定溢價_有分組"].min()),
                                int(T["穩定溢價_有分組"].max())],
        "穩定溢價_涉及檔數": int(R.loc[R["stable"], "ticker"].nunique()),
        "三條各自通過_每評估日中位": {c: float(T[c].median()) for c in ("條1_ROE20_過", "條2_無虧損且EPS未跌30_過", "條3_季末PE_p25ge30_過")},
        "另一讀法（EPS 比 5 對）穩定溢價_中位_最大": [float(T["穩定溢價_另一讀法5對"].median()), int(T["穩定溢價_另一讀法5對"].max())],
        "原版可買_中位_最少_最大": [float(T["原版_可買"].median()), int(T["原版_可買"].min()), int(T["原版_可買"].max())],
        "變體可買_中位_最少_最大": [float(T["變體_可買"].median()), int(T["變體_可買"].min()), int(T["變體_可買"].max())],
        "重新分類組": {"總筆數": int(len(rc)), "出現評估日數": len(dates_rc), "出現評估日": dates_rc,
                   "進場年": yrs_rc, "群數": len(yrs_rc), "涉及檔數": int(rc["ticker"].nunique()),
                   "原組_接近": int((rc["group_orig"] == "接近").sum()), "原組_偏貴": int((rc["group_orig"] == "偏貴").sum())},
        "還沒測觸發（依構造）": trig, "判語（依構造，不看報酬）": "還沒測" if any(trig.values()) else "未觸發（須正式跑）",
        "一致性檢查": chk,
        "描述欄乾跑（⛔ 只報筆數／算不算得出，不含報酬）": {
            "主格：重新分類組 1 年可算筆數": int(rc["ok_1y"].sum()), "主格：重新分類組 3 年可算筆數": int(rc["ok_3y"].sum()),
            "主格差（重新分類−原版可買）1 年算得出的評估日數": int(len(main_dates)),
            "其進場年群數": len(set(main_dates["entry_year"])),
            "原版 可買−偏貴 1 年算得出的評估日數": int(T["乾跑_orig_可買減偏貴_1年可算"].sum()),
            "變體 可買−偏貴 1 年算得出的評估日數": int(T["乾跑_var_可買減偏貴_1年可算"].sum()),
            "重新分類組對大盤 1 年算得出的評估日數": int(T["乾跑_重新分類對大盤_1年可算"].sum()),
            "主格差 3 年算得出的評估日數": int(T["乾跑_主格差_3年可算"].sum()),
            "重新分類組 1 年 Holder 計數（筆數，非報酬）": holder_cnt_1y,
            "穩定溢價家數": "每評估日皆算得出（見 us_freq_by_eval.csv）",
            "說明": "1 年／3 年可算＝Holder(dry) 窗滿；大盤＝窗內日期都在 ^SP500TR 檔內。⛔ 未讀任何 ret／adjclose 值。"},
        "資料缺口（母體內，(評估日,檔) 筆數；代號清單只在 ~/us_work/stablepe35/）": {
            "條1條2不可算_原因": {k: int(v) for k, v in pop.loc[pop["why12"] != "ok", "why12"].value_counts().items()},
            "條1_ROE不可算（年度淨利或權益缺）": int(((pop["c1"] == "na") & (pop["why12"] == "ok")).sum()),
            "條2_不可算（虧損不可判或年度 EPS 缺）": int(((pop["c2"] == "na") & (pop["why12"] == "ok")).sum()),
            "條3_季末PE不可算（不滿 3 年）": int((pop["c3"] == "na").sum()),
            "條1不可算_涉及檔數": int(pop.loc[pop["c1"] == "na", "ticker"].nunique()),
            "條2不可算_涉及檔數": int(pop.loc[pop["c2"] == "na", "ticker"].nunique()),
            "條3不可算_涉及檔數": int(pop.loc[pop["c3"] == "na", "ticker"].nunique()),
            "有分組者中任一條不可算": int(((G["c1"] == "na") | (G["c2"] == "na") | (G["c3"] == "na")).sum()),
            "處理": "任一條不可算 ⇒ 不算穩定溢價（pe_T 照原版 25）。"},
        "用時秒": round(time.time() - t0),
    }
    FQ.jdump(S, os.path.join(OUT, "us_freq_summary.json"))
    # 私有：資料缺口的代號清單
    gap = {k: pop.loc[pop[k] == "na", "ticker"].value_counts().to_dict() for k in ("c1", "c2", "c3")}
    gap["reclass_rows"] = rc[["eval", "ticker", "group_orig"]].values.tolist()
    FQ.jdump(gap, os.path.join(PRIV, "us_gaps_and_reclass.json"))
    pd.set_option("display.width", 250)
    print(T[["eval", "母體", "有分組", "穩定溢價", "穩定溢價_有分組", "條1_ROE20_過", "條2_無虧損且EPS未跌30_過",
             "條3_季末PE_p25ge30_過", "原版_可買", "變體_可買", "重新分類組"]].to_string(index=False))
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

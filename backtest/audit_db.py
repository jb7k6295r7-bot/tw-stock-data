"""資料庫稽核（讀取端、只讀不改）：找資料錯誤與缺失，寫 backtest/results_audit/DB_AUDIT.md 與逐筆異常清單。

    python3 -m backtest.audit_db [--procs 4]

檢查的原則（每一項都寫在報告裡）：
  A 結構不變量：日期唯一且在日曆內、OHLC 互相一致、價量非負、金額≈量×價
  B 交易規則不變量：有漲跌幅限制的普通股，相鄰交易日收盤比落在 ±10%（超出 ⇒ 不是事件缺漏就是資料錯）
  C 跨檔一致性：還原因子與實際價格接得起來；法人 total＝三者和；營收檔「上月營收」＝上個月檔的「當月營收」
  D 獨立來源交叉核對：data/history/*_price|inst|margin|per|revenue（另一組端點）vs 主表
  E 涵蓋率：每檔在 first_seen～last_seen 內有幾成交易日有列；每一層相對價格層缺了哪些日子；全市場每日家數有沒有塌陷
  F 母體檔自洽：stocks.csv 的 first_seen／last_seen 等於檔案首尾
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_audit")
LIM_HI, LIM_LO = 1.105, 0.895   # ±10% 漲跌幅 ＋ 升降單位容差

_G: dict = {}


def _init(cal):
    _G["cal"] = cal
    _G["calset"] = set(cal)
    _G["pos"] = {d: i for i, d in enumerate(cal)}


def check_stock(job):
    sid, market, kind, first_seen, last_seen = job
    cal, calset, pos = _G["cal"], _G["calset"], _G["pos"]
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return {"sid": sid, "missing_file": True}
    raw = pd.read_csv(p, dtype={"stock_id": str, "date": str, "name": str, "limit": str})
    for c in ("open", "high", "low", "close", "volume", "amount", "change"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw["date"] = pd.to_datetime(raw["date"])
    r = {"sid": sid, "market": market, "kind": kind, "rows": len(raw), "ex": []}
    r["dup_dates"] = int(raw["date"].duplicated().sum())
    r["unsorted"] = int((raw["date"].diff().dt.days < 0).sum())
    r["not_in_cal"] = int((~raw["date"].isin(calset)).sum())
    raw = raw.drop_duplicates("date").sort_values("date")
    fmin, fmax = raw["date"].iloc[0], raw["date"].iloc[-1]
    r["file_min"], r["file_max"] = fmin, fmax
    r["first_seen_ok"] = bool(fmin == pd.Timestamp(first_seen)); r["last_seen_ok"] = bool(fmax == pd.Timestamp(last_seen))
    o, h, l, c, v, a = (raw[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume", "amount"))
    traded = ~np.isnan(c)
    r["nonpos_price"] = int(((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0)).sum())
    with np.errstate(invalid="ignore"):
        bad_hl = (h < np.maximum(o, c) - 1e-9) | (l > np.minimum(o, c) + 1e-9)
    r["ohlc_bad"] = int(np.nansum(bad_hl))
    if r["ohlc_bad"]:
        r["ex"].append(("ohlc", raw["date"].iloc[int(np.flatnonzero(bad_hl)[0])].strftime("%Y-%m-%d")))
    r["vol_nonpos"] = int(np.nansum(v <= 0))
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio_amt = a / (v * c)
    ok = (v > 0) & (c > 0) & ~np.isnan(a)
    r["amt_ratio_bad"] = int(np.nansum(ok & ((ratio_amt < 0.5) | (ratio_amt > 2.0))))
    r["amt_missing"] = int(np.nansum((v > 0) & (np.isnan(a) | (a <= 0))))
    # 相鄰交易日（日曆位置差 1）且無還原事件 ⇒ 漲跌幅檢查（只對普通股）
    adj = D.load_adj(sid)
    ev = set(adj["date"].tolist()) if adj is not None else set()
    idx = np.array([pos.get(d, -1) for d in raw["date"]])
    r["limit_viol"] = 0; r["limit_viol_hl"] = 0; r["limit_examples"] = []
    if kind == "stock" and market in ("twse", "tpex"):
        adjpos = (idx[1:] - idx[:-1] == 1) & (idx[1:] >= 0)
        rc = c[1:] / c[:-1]; rh = h[1:] / c[:-1]; rl = l[1:] / c[:-1]
        dates_t = raw["date"].iloc[1:].to_numpy()
        is_ev = np.array([d in ev for d in raw["date"].iloc[1:]])
        young = np.arange(1, len(c)) < 5                     # 上市前 5 日無漲跌幅
        cand = adjpos & ~is_ev & ~young & ~np.isnan(rc)
        viol = cand & ((rc > LIM_HI) | (rc < LIM_LO))
        viol_hl = cand & ((rh > LIM_HI) | (rl < LIM_LO))
        r["limit_viol"] = int(viol.sum()); r["limit_viol_hl"] = int(viol_hl.sum())
        for k in np.flatnonzero(viol | viol_hl)[:5]:
            r["limit_examples"].append((pd.Timestamp(dates_t[k]).strftime("%Y-%m-%d"), round(float(rc[k]), 4), round(float(rh[k]), 4), round(float(rl[k]), 4)))
    # 還原因子與實際價格接得起來？事件日收盤 ÷（前一有成交日收盤 × factor）應在 ±10% 內
    r["adj_events"] = 0; r["adj_bad"] = 0; r["adj_examples"] = []; r["adj_preclose_bad"] = 0
    if adj is not None and len(adj):
        dates = raw["date"].to_numpy()
        for _, e in adj.iterrows():
            r["adj_events"] += 1
            k = np.searchsorted(dates, np.datetime64(e["date"]))
            if k >= len(dates) or k == 0:
                continue
            pc, cc = c[k - 1], c[k]
            fac = float(e["factor"]) if not pd.isna(e.get("factor", np.nan)) else np.nan
            if np.isnan(fac) or np.isnan(pc) or np.isnan(cc):
                continue
            pre = pd.to_numeric(e.get("pre_close", np.nan), errors="coerce")
            if not np.isnan(pre) and abs(pre - pc) / pc > 0.005:
                r["adj_preclose_bad"] += 1
            q = cc / (pc * fac)
            if q > 1.105 or q < 0.895:
                r["adj_bad"] += 1
                if len(r["adj_examples"]) < 3:
                    r["adj_examples"].append((str(e["date"])[:10], e.get("kind", ""), round(fac, 4), round(float(q), 3)))
    # 涵蓋率：first_seen～last_seen 內的日曆天 vs 有列的天
    lo = max(pd.Timestamp(first_seen), cal[0]); hi = min(pd.Timestamp(last_seen), cal[-1])
    ncal = int(((cal >= lo) & (cal <= hi)).sum())
    r["cal_days"] = ncal; r["traded_days"] = int(traded.sum()); r["coverage"] = r["traded_days"] / ncal if ncal else np.nan
    r["names"] = int(raw["name"].nunique()) if "name" in raw else 1
    # 全市場家數用：有列的日曆位置
    r["traded_pos"] = idx[idx >= 0]
    # change 欄 vs 收盤差（非事件日、相鄰日）
    if "change" in raw:
        ch = raw["change"].to_numpy(float)
        d_close = c[1:] - c[:-1]
        m = (idx[1:] - idx[:-1] == 1) & ~np.isnan(ch[1:]) & ~np.isnan(d_close) & ~np.array([d in ev for d in raw["date"].iloc[1:]])
        r["change_checked"] = int(m.sum()); r["change_bad"] = int((m & (np.abs(ch[1:] - d_close) > 0.011)).sum())
    r["dates"] = raw["date"].to_numpy()
    r["close"] = c; r["volume"] = v
    return r


def layer_coverage(sid, dates_price, layer):
    p = os.path.join(D.DATA, layer, f"{sid}.csv")
    if not os.path.exists(p):
        return None
    x = pd.read_csv(p, dtype={"date": str})
    d = pd.to_datetime(x["date"]).to_numpy()
    if len(d) == 0:
        return {"rows": 0}
    lo = d.min()
    price_after = dates_price[dates_price >= lo]
    missing = np.setdiff1d(price_after, d)
    out = {"rows": len(x), "first": pd.Timestamp(lo).strftime("%Y-%m-%d"), "missing_vs_price": int(len(missing)), "price_days_after": int(len(price_after)),
           "dup": int(pd.Series(d).duplicated().sum())}
    if layer == "stocks_inst":
        for c in ("foreign", "trust", "dealer", "total"):
            x[c] = pd.to_numeric(x[c], errors="coerce")
        out["identity_bad"] = int((np.abs(x["foreign"] + x["trust"] + x["dealer"] - x["total"]) > 1).sum())
    if layer == "stocks_margin":
        for c in ("m_buy", "m_sell", "m_balance", "m_limit", "s_balance"):
            x[c] = pd.to_numeric(x[c], errors="coerce")
        out["neg"] = int(((x["m_balance"] < 0) | (x["s_balance"] < 0)).sum())
        out["over_limit"] = int(((x["m_limit"] > 0) & (x["m_balance"] > x["m_limit"])).sum())
    if layer == "stocks_per":
        for c in ("per", "pbr", "yield_pct"):
            x[c] = pd.to_numeric(x[c], errors="coerce")
        out["per_nonpos"] = int((x["per"] <= 0).sum()); out["pbr_nonpos"] = int((x["pbr"] <= 0).sum())
        out["yield_out"] = int((x["yield_pct"] < 0).sum() + (x["yield_pct"] > 40).sum())
        out["per_missing"] = int(x["per"].isna().sum())
    return out


def per_layers(job):
    sid, dates_price = job
    return sid, {L: layer_coverage(sid, dates_price, L) for L in ("stocks_inst", "stocks_margin", "stocks_per")}


def history_crosscheck(cal):
    """data/history/<sid>_price.csv（另一組端點）vs data/stocks/<sid>.csv：同日收盤、成交量是否一致。"""
    rows = []
    for f in sorted(glob.glob(os.path.join(D.DATA, "history", "*_price.csv"))):
        sid = os.path.basename(f).split("_")[0]
        h = pd.read_csv(f, dtype={"date": str}); h["date"] = pd.to_datetime(h["date"])
        m = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close", "volume"]); m["date"] = pd.to_datetime(m["date"])
        j = h.merge(m, on="date", suffixes=("_h", "_m"))
        if not len(j):
            rows.append((sid, 0, 0, 0, 0)); continue
        close_bad = int((np.abs(j["close_h"] - j["close_m"]) > 0.011).sum())
        vol_bad = int((np.abs(j["volume_h"] - j["volume_m"]) > 0.5 * np.maximum(1, j["volume_m"].abs()) * 0 + 1).sum())
        only_h = int((~h["date"].isin(m["date"])).sum())
        rows.append((sid, len(j), close_bad, vol_bad, only_h))
    return pd.DataFrame(rows, columns=["stock_id", "overlap_days", "close_mismatch", "volume_mismatch", "history_only_days"])


def history_layer_crosscheck(layer, suffix, cols):
    rows = []
    for f in sorted(glob.glob(os.path.join(D.DATA, "history", f"*_{suffix}.csv"))):
        sid = os.path.basename(f).split("_")[0]
        mp = os.path.join(D.DATA, layer, f"{sid}.csv")
        if not os.path.exists(mp):
            rows.append((sid, 0, "no main file")); continue
        h = pd.read_csv(f, dtype={"date": str}); m = pd.read_csv(mp, dtype={"date": str})
        h = h.rename(columns={"margin_balance": "m_balance", "short_balance": "s_balance", "margin_limit": "m_limit"})
        common = [c for c in cols if c in h and c in m]
        if not common or "date" not in h:
            rows.append((sid, 0, f"no common cols {list(h.columns)[:6]}")); continue
        j = h.merge(m, on="date", suffixes=("_h", "_m"))
        bad = 0
        for c in common:
            bad += int((np.abs(pd.to_numeric(j[f"{c}_h"], errors="coerce") - pd.to_numeric(j[f"{c}_m"], errors="coerce")) > 1).sum())
        rows.append((sid, len(j), f"mismatch {bad} on {common}"))
    return pd.DataFrame(rows, columns=["stock_id", "overlap", "result"])


def revenue_checks(stocks):
    files = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*_twse.csv")) + glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*_tpex.csv")))
    by = {}
    for f in files:
        x = pd.read_csv(f, dtype=str)
        x["period"] = os.path.basename(f)[:7]; x["market"] = os.path.basename(f)[8:12]
        by.setdefault(x["period"].iloc[0], []).append(x)
    periods = sorted(by)
    frames = {p: pd.concat(by[p], ignore_index=True) for p in periods}
    rows = []; prev = None
    alive = stocks[(stocks["kind"] == "stock") & stocks["market"].isin(["twse", "tpex"])]
    for p in periods:
        x = frames[p]
        for c in ("當月營收", "上月營收", "去年當月營收", "去年同月增減(%)"):
            x[c] = pd.to_numeric(x[c], errors="coerce")
        dup = int(x["stock_id"].duplicated().sum())
        neg = int((x["當月營收"] < 0).sum())
        mend = pd.Timestamp(p + "-01") + pd.offsets.MonthEnd(0)
        n_alive = int(((alive["first_seen"] <= mend) & (alive["last_seen"] >= pd.Timestamp(p + "-01"))).sum())
        cov = x["stock_id"].isin(alive["stock_id"]).sum() / n_alive if n_alive else np.nan
        # 上月營收 vs 上個月檔的當月營收
        chain_bad = chain_n = 0
        if prev is not None:
            j = x[["stock_id", "上月營收"]].merge(prev[["stock_id", "當月營收"]].rename(columns={"當月營收": "prev_cur"}), on="stock_id")
            chain_n = len(j); chain_bad = int((np.abs(j["上月營收"] - j["prev_cur"]) > 1).sum())
        # 去年當月 vs 12 個月前檔
        ly_bad = ly_n = 0
        p12 = (pd.Timestamp(p + "-01") - pd.DateOffset(years=1)).strftime("%Y-%m")
        if p12 in frames:
            f12 = frames[p12]; f12["當月營收"] = pd.to_numeric(f12["當月營收"], errors="coerce")
            j = x[["stock_id", "去年當月營收"]].merge(f12[["stock_id", "當月營收"]].rename(columns={"當月營收": "ly_cur"}), on="stock_id")
            ly_n = len(j); ly_bad = int((np.abs(j["去年當月營收"] - j["ly_cur"]) > 1).sum())
        # yoy% 重算
        with np.errstate(divide="ignore", invalid="ignore"):
            yoy = (x["當月營收"] / x["去年當月營收"] - 1) * 100
        m = x["去年當月營收"] > 0
        yoy_bad = int((m & (np.abs(yoy - x["去年同月增減(%)"]) > 0.06)).sum())
        rows.append({"period": p, "rows": len(x), "dup": dup, "neg": neg, "alive_universe": n_alive, "coverage": round(cov, 3),
                     "chain_n": chain_n, "chain_bad": chain_bad, "ly_n": ly_n, "ly_bad": ly_bad, "yoy_bad": yoy_bad})
        prev = x
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    stocks["first_seen"] = pd.to_datetime(stocks["first_seen"]); stocks["last_seen"] = pd.to_datetime(stocks["last_seen"])
    tw = stocks[stocks["market"].isin(["twse", "tpex"])]
    jobs = list(zip(tw["stock_id"], tw["market"], tw["kind"], tw["first_seen"], tw["last_seen"]))
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        res = pool.map(check_stock, jobs, chunksize=16)
    print(f"價格檔 {len(res)} 檔，{time.time() - t0:.0f}s", file=sys.stderr)
    # 全市場每日家數（普通股）
    n = len(cal); cnt = np.zeros(n, int); cnt_all = np.zeros(n, int)
    for r in res:
        if r.get("missing_file"):
            continue
        cnt_all[r["traded_pos"]] += 1
        if r["kind"] == "stock":
            cnt[r["traded_pos"]] += 1
    daily = pd.DataFrame({"date": cal, "stocks_traded": cnt, "all_traded": cnt_all})
    med = pd.Series(cnt).rolling(20, min_periods=5).median()
    daily["collapse"] = cnt < 0.5 * med.to_numpy()
    daily.to_csv(os.path.join(OUT, "daily_counts.csv"), index=False)
    # 逐檔表
    rows = []
    for r in res:
        if r.get("missing_file"):
            rows.append({"stock_id": r["sid"], "missing_file": True}); continue
        rows.append({k: r[k] for k in ("sid", "market", "kind", "rows", "dup_dates", "unsorted", "not_in_cal", "first_seen_ok", "last_seen_ok",
                                       "nonpos_price", "ohlc_bad", "vol_nonpos", "amt_ratio_bad", "amt_missing", "limit_viol", "limit_viol_hl",
                                       "adj_events", "adj_bad", "adj_preclose_bad", "cal_days", "traded_days", "coverage", "names", "change_checked", "change_bad")}
                    | {"limit_examples": r["limit_examples"], "adj_examples": r["adj_examples"], "file_min": r["file_min"].strftime("%Y-%m-%d"), "file_max": r["file_max"].strftime("%Y-%m-%d")})
    T = pd.DataFrame(rows).rename(columns={"sid": "stock_id"})
    T.to_csv(os.path.join(OUT, "per_stock.csv"), index=False)
    # 其他層
    price_dates = {r["sid"]: r["dates"] for r in res if not r.get("missing_file")}
    stock_only = [(r["sid"], r["dates"]) for r in res if not r.get("missing_file") and r["kind"] == "stock"]
    with Pool(a.procs) as pool:
        lay = dict(pool.map(per_layers, stock_only, chunksize=16))
    print(f"其他層 {len(lay)} 檔，{time.time() - t0:.0f}s", file=sys.stderr)
    L = {}
    for layer in ("stocks_inst", "stocks_margin", "stocks_per"):
        vals = [(sid, v[layer]) for sid, v in lay.items()]
        have = [(sid, x) for sid, x in vals if x is not None]
        L[layer] = {"stocks_without_file": len(vals) - len(have), "files": len(have),
                    "missing_vs_price_total": sum(x["missing_vs_price"] for _, x in have), "price_days_total": sum(x["price_days_after"] for _, x in have),
                    "dup_total": sum(x["dup"] for _, x in have),
                    "worst": sorted(((x["missing_vs_price"], sid) for sid, x in have), reverse=True)[:8]}
        for k in ("identity_bad", "neg", "over_limit", "per_nonpos", "pbr_nonpos", "yield_out", "per_missing"):
            if have and k in have[0][1]:
                L[layer][k] = sum(x.get(k, 0) for _, x in have)
    hist_price = history_crosscheck(cal)
    hist_inst = history_layer_crosscheck("stocks_inst", "inst", ["foreign", "trust", "dealer", "total"])
    hist_margin = history_layer_crosscheck("stocks_margin", "margin", ["m_balance", "s_balance"])
    hist_per = history_layer_crosscheck("stocks_per", "per", ["per", "pbr", "yield_pct"])
    rev = revenue_checks(stocks)
    rev.to_csv(os.path.join(OUT, "revenue_checks.csv"), index=False)
    # 日曆 vs 全市場：有 ≥ 200 檔成交但不在日曆的日子？（raw 日期已限制在日曆內才會被計數，所以另外用 not_in_cal）
    disp = pd.read_csv(os.path.join(D.DATA, "meta", "disposal.csv"), dtype=str)
    disp_bad = int((pd.to_datetime(disp["start_date"]) > pd.to_datetime(disp["end_date"])).sum())

    # ── 報告 ──
    S = T[T["kind"] == "stock"]
    Ln = ["# 資料庫稽核報告（讀取端、只讀）", "",
          f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。程式 `backtest/audit_db.py`。逐檔明細 `per_stock.csv`、每日家數 `daily_counts.csv`、營收 `revenue_checks.csv`。",
          f"母體：`stocks.csv` 上市＋上櫃全部 {len(T):,} 檔（普通股 {len(S):,}、ETF／其他 {len(T) - len(S):,}）；日曆 {len(cal):,} 天（{cal[0].date()} ~ {cal[-1].date()}）。", "",
          "## A. 結構不變量（價格檔）", "",
          "| 檢查 | 違反檔數 | 違反列數 | 說明 |", "|---|---:|---:|---|"]
    def row(name, col, note, sub=T):
        Ln.append(f"| {name} | {int((sub[col] > 0).sum()):,} | {int(sub[col].sum()):,} | {note} |")
    row("日期重複", "dup_dates", "同一檔同一天兩列")
    row("日期未排序", "unsorted", "")
    row("日期不在交易日曆", "not_in_cal", "日檔有、日曆沒有的日子")
    row("價格 ≤ 0", "nonpos_price", "任一 OHLC ≤ 0")
    row("OHLC 互相矛盾", "ohlc_bad", "high < max(open,close) 或 low > min(open,close)")
    row("成交量 ≤ 0", "vol_nonpos", "有列但量為 0（日檔只收有成交的證券，理論上 0 筆）")
    row("金額 ÷（量×收盤）超出 0.5～2", "amt_ratio_bad", "單位錯或金額欄錯")
    row("有量無金額", "amt_missing", "")
    row("change 欄 ≠ 收盤差", "change_bad", f"相鄰交易日、非還原事件日；核對 {int(T['change_checked'].sum()):,} 筆")
    Ln += ["", f"`first_seen`／`last_seen` 與檔案首尾不符：{int((~T['first_seen_ok']).sum()):,}／{int((~T['last_seen_ok']).sum()):,} 檔（stocks.csv 自洽）。", "",
           "## B. 交易規則不變量：普通股相鄰交易日漲跌幅 ±10%", "",
           f"只查普通股、相鄰兩個交易日都有成交、當日不是 `data/adj/` 事件日、排除上市前 5 日。**收盤比超出 [0.895, 1.105]：{int(S['limit_viol'].sum()):,} 筆／{int((S['limit_viol'] > 0).sum()):,} 檔；最高或最低價超出：{int(S['limit_viol_hl'].sum()):,} 筆／{int((S['limit_viol_hl'] > 0).sum()):,} 檔。**",
           "超出的每一筆只有三種解釋：① 那天有公司行動但 `data/adj/` 沒收（缺事件）；② 該股當時無漲跌幅限制（新上市首五日、全額交割以外的特例）；③ 資料錯。逐筆清單見 `limit_violations.csv`。", ""]
    lv = []
    for _, r in S[S["limit_viol"] + S["limit_viol_hl"] > 0].iterrows():
        for e in r["limit_examples"]:
            lv.append({"stock_id": r["stock_id"], "date": e[0], "close_ratio": e[1], "high_ratio": e[2], "low_ratio": e[3]})
    pd.DataFrame(lv).to_csv(os.path.join(OUT, "limit_violations.csv"), index=False)
    top = S.sort_values("limit_viol", ascending=False).head(10)
    Ln.append("| 代號 | 收盤比違反 | 高低價違反 | 例（日期, 收盤比, 高/前收, 低/前收） |"); Ln.append("|---|---:|---:|---|")
    for _, r in top.iterrows():
        if r["limit_viol"] + r["limit_viol_hl"] == 0:
            break
        Ln.append(f"| {r['stock_id']} | {r['limit_viol']} | {r['limit_viol_hl']} | {r['limit_examples'][:3]} |")
    Ln += ["", "## C. 跨檔一致性", "",
           f"- **還原因子 vs 實際價格**：{int(T['adj_events'].sum()):,} 個事件裡，事件日收盤 ÷（前一有成交日收盤 × factor）超出 ±10% 的有 **{int(T['adj_bad'].sum()):,} 個／{int((T['adj_bad'] > 0).sum()):,} 檔**；因子檔的 `pre_close` 與實際前收差 > 0.5% 的 **{int(T['adj_preclose_bad'].sum()):,} 個**。前者超出代表因子與價格接不起來（或復牌首日連續跳），清單見 `adj_mismatch.csv`。",
           f"- **三大法人 total ＝ 外資＋投信＋自營**：違反 {L['stocks_inst'].get('identity_bad', 0):,} 列。",
           f"- **融資餘額**：負值 {L['stocks_margin'].get('neg', 0):,} 列；餘額超過限額 {L['stocks_margin'].get('over_limit', 0):,} 列。",
           f"- **本益比檔**：PE ≤ 0 {L['stocks_per'].get('per_nonpos', 0):,} 列、PBR ≤ 0 {L['stocks_per'].get('pbr_nonpos', 0):,} 列、殖利率 < 0 或 > 40% {L['stocks_per'].get('yield_out', 0):,} 列、PE 空白 {L['stocks_per'].get('per_missing', 0):,} 列（虧損公司本益比本來就空白，空白不是錯）。",
           f"- **月營收鏈**（每個月檔的「上月營收」對上個月檔的「當月營收」、「去年當月營收」對 12 個月前的檔、年增率重算）：{len(rev)} 個月，鏈接不符 {int(rev['chain_bad'].sum()):,}／{int(rev['chain_n'].sum()):,} 筆，去年同月不符 {int(rev['ly_bad'].sum()):,}／{int(rev['ly_n'].sum()):,} 筆，年增率重算不符 {int(rev['yoy_bad'].sum()):,} 筆，重複代號 {int(rev['dup'].sum()):,}，負營收 {int(rev['neg'].sum()):,}。",
           f"- 處置檔 start_date > end_date：{disp_bad} 列。", ""]
    am = []
    for _, r in T[T["adj_bad"] > 0].iterrows():
        for e in r["adj_examples"]:
            am.append({"stock_id": r["stock_id"], "date": e[0], "kind": e[1], "factor": e[2], "close_over_expected": e[3]})
    pd.DataFrame(am).to_csv(os.path.join(OUT, "adj_mismatch.csv"), index=False)
    Ln += ["## D. 獨立來源交叉核對（`data/history/`，另一組端點抓的核心個股）", "",
           "| 層 | 檔數 | 重疊列 | 不符 |", "|---|---:|---:|---|",
           f"| 價格（收盤／量） | {len(hist_price)} | {int(hist_price['overlap_days'].sum()):,} | 收盤不符 {int(hist_price['close_mismatch'].sum())}、量不符 {int(hist_price['volume_mismatch'].sum())}、history 有主表沒有 {int(hist_price['history_only_days'].sum())} 天 |",
           f"| 三大法人 | {len(hist_inst)} | {int(hist_inst['overlap'].sum()):,} | {'; '.join(f'{r.stock_id}:{r.result}' for r in hist_inst.itertuples() if 'mismatch 0' not in r.result) or '全部一致'} |",
           f"| 融資融券 | {len(hist_margin)} | {int(hist_margin['overlap'].sum()):,} | {'; '.join(f'{r.stock_id}:{r.result}' for r in hist_margin.itertuples() if 'mismatch 0' not in r.result) or '全部一致'} |",
           f"| 本益比 | {len(hist_per)} | {int(hist_per['overlap'].sum()):,} | {'; '.join(f'{r.stock_id}:{r.result}' for r in hist_per.itertuples() if 'mismatch 0' not in r.result) or '全部一致'} |", ""]
    hist_price.to_csv(os.path.join(OUT, "history_price_crosscheck.csv"), index=False)
    Ln += ["## E. 涵蓋率與缺失", "",
           f"- 普通股在 `first_seen`～`last_seen` 內的交易日涵蓋率：中位數 {S['coverage'].median() * 100:.1f}%，< 90% 的 {int((S['coverage'] < 0.9).sum()):,} 檔，< 50% 的 {int((S['coverage'] < 0.5).sum()):,} 檔（日檔只收有成交的證券，低涵蓋 ＝ 冷門，不是漏抓；要分辨得看全市場家數有沒有同時塌）。",
           f"- **全市場每日普通股家數**：中位數 {int(np.median(cnt[cnt > 0]))}，最小 {int(cnt[cnt > 0].min())}（{cal[int(np.argmin(np.where(cnt > 0, cnt, 10**9)))].date()}）；低於近 20 日中位數一半的日子 **{int(daily['collapse'].sum())} 天**（清單 `daily_counts.csv`）。",
           f"- 日曆天沒有任何普通股有列：{int((cnt == 0).sum())} 天。"]
    for layer, lab in (("stocks_inst", "三大法人"), ("stocks_margin", "融資融券"), ("stocks_per", "本益比")):
        x = L[layer]
        Ln.append(f"- **{lab}**：普通股沒有檔 {x['stocks_without_file']:,}；有檔者自該層第一天起，價格層有列而該層沒有的 **{x['missing_vs_price_total']:,}／{x['price_days_total']:,} 天（{x['missing_vs_price_total'] / max(1, x['price_days_total']) * 100:.2f}%）**；重複日期 {x['dup_total']:,}；缺最多的：{x['worst'][:5]}。")
    Ln += ["", "營收逐月涵蓋（普通股母體裡當月存活的檔數為分母）：", "", "| 期別 | 列數 | 涵蓋 | 鏈接不符 | 年增率不符 |", "|---|---:|---:|---:|---:|"]
    for _, r in rev.iterrows():
        if r["coverage"] < 0.9 or r["chain_bad"] > 0 or r["yoy_bad"] > 5 or r["period"] in (rev["period"].iloc[0], rev["period"].iloc[-1]):
            Ln.append(f"| {r['period']} | {r['rows']:,} | {r['coverage'] * 100:.1f}% | {r['chain_bad']}／{r['chain_n']} | {r['yoy_bad']} |")
    Ln += ["", "（只列涵蓋 < 90%、鏈接有不符、年增率不符 > 5 筆、以及首尾月份。）", ""]
    with open(os.path.join(OUT, "DB_AUDIT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(Ln) + "\n")
    print(f"寫入 {OUT}/DB_AUDIT.md，{time.time() - t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()

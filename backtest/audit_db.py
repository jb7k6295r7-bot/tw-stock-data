"""資料庫稽核（讀取端、只讀不改）：找資料錯誤與缺失，寫 backtest/results_audit/DB_AUDIT.md 與逐筆異常清單。

    python3 -m backtest.audit_db [--procs 4]

檢查的原則（每一項都寫在報告裡）：
  A 結構不變量：日期唯一且在日曆內、OHLC 互相一致、價量非負、金額≈量×價
  B 交易規則不變量：有漲跌幅限制的普通股，相鄰交易日收盤比落在 ±10%（超出 ⇒ 不是事件缺漏就是資料錯）
  C 跨檔一致性：還原因子與實際價格接得起來；法人 total＝三者和；營收檔「上月營收」＝上個月檔的「當月營收」
  D 獨立來源交叉核對：data/history/*_price|inst|margin|per|revenue（另一組端點）vs 主表
  E 涵蓋率：每檔在 first_seen～last_seen 內有幾成交易日有列；每一層相對價格層缺了哪些日子；全市場每日家數有沒有塌陷
  F 母體檔自洽：stocks.csv 的 first_seen／last_seen 等於檔案首尾
  G 官方統計交叉核對（資料庫線抓進 data/meta/ 的 TWSE FMNPTK 年表／FMSRFK 月表、TPEx yearlyStock 年表）：
    年收盤簡單平均、年最高／最低（含日期）、年成交股數／金額／筆數（只有上市有量）；月成交股數／金額／筆數、月最高／最低、月加權均價
    ⛔ 上櫃的量三欄口徑不同（資料庫線 0737：比值 1.04／1.04／2.06），只描述比值分佈、不判對錯
  C 另加：每個 data/adj/ 事件日，前收 × factor 對 ref_price 的差 ≤ 0.5%（2026-09-09 20:14 給市場情報分析線那封的第 3 條）

    python3 -m backtest.audit_db --selftest      # G 的合成資料自測（會紅也會綠：見 _selftest）
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
    r["adj_events"] = 0; r["adj_bad"] = 0; r["adj_examples"] = []; r["adj_preclose_bad"] = 0; r["adj_ref_bad"] = 0; r["adj_ref_checked"] = 0
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
            ref = pd.to_numeric(e.get("ref_price", np.nan), errors="coerce")
            if not np.isnan(ref) and ref > 0:
                r["adj_ref_checked"] += 1
                if abs(pc * fac - ref) / ref > 0.005:
                    r["adj_ref_bad"] += 1
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
    r["close"] = c; r["volume"] = v; r["high"] = h; r["low"] = l; r["amount"] = a
    r["tx"] = pd.to_numeric(raw["transactions"], errors="coerce").to_numpy(float) if "transactions" in raw else np.full(len(c), np.nan)
    r["mkt"] = raw["market"].astype(str).to_numpy() if "market" in raw else np.full(len(c), market)
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


def _official_date_ok(ours, official):
    """官方 high_date／low_date 是 'M/DD'（無年）；同一年內比月日。ours 是 numpy datetime64 或 NaT。"""
    if pd.isna(ours) or pd.isna(official):
        return np.nan
    try:
        m, d = str(official).split("/")
        t = pd.Timestamp(ours)
        return 1.0 if (t.month == int(m) and t.day == int(d)) else 0.0
    except (ValueError, AttributeError):
        return np.nan


def _trunc2(x: float) -> float:
    """兩位小數無條件捨去（官方上櫃年表的收盤平均、上市月表的加權均價都是這樣印的：實測相符率 99.98%／99.9%，四捨五入只有 50%）。"""
    return float(np.floor(x * 100 + 1e-9) / 100)


def _stock_frame(r):
    """單檔日資料 ⇒ DataFrame（只取有收盤的列＝有成交日）；官方的年／月統計都是對有成交日算的。"""
    df = pd.DataFrame({"date": pd.to_datetime(r["dates"]), "close": r["close"], "high": r["high"], "low": r["low"],
                       "volume": r["volume"], "amount": r["amount"], "tx": r["tx"], "mkt": r.get("mkt", np.full(len(r["close"]), ""))})
    return df[~df["close"].isna()].copy()


def aggregate_ours(res, freq, market: str | None = None):
    """所有檔按年（freq='Y'）或年月（freq='M'）聚合：收盤簡單平均、最高（含日期）、最低（含日期）、量／金額／筆數合計、加權均價、
    n_markets（該期內 market 欄有幾種：>1 ＝ 轉板年，資料庫線 0922——資料自己講得出來，不必靠 delisted.csv）。
    market 給了就只取那個市場的列（官方上市表只算上市段、上櫃表只算上櫃段）。回傳 DataFrame，鍵 stock_id＋roc_year（＋month）。"""
    out = []
    for r in res:
        if r.get("missing_file"):
            continue
        df = _stock_frame(r)
        if market is not None:
            df = df[df["mkt"] == market]
        if not len(df):
            continue
        df["roc_year"] = df["date"].dt.year - 1911
        keys = ["roc_year"] + (["month"] if freq == "M" else [])
        if freq == "M":
            df["month"] = df["date"].dt.month
        for k, g in df.groupby(keys, sort=False):
            k = (k,) if not isinstance(k, tuple) else k
            hv, lv = g["high"].to_numpy(), g["low"].to_numpy()
            hmax, lmin = np.nanmax(hv) if g["high"].notna().any() else np.nan, np.nanmin(lv) if g["low"].notna().any() else np.nan
            # 官方的最高／最低日期＝同值時取【最後一次】出現（實測上市 high 99.85%／low 99.87%、上櫃 high 100%，取第一次只有 85～94%）
            ih = int(np.flatnonzero(hv == hmax)[-1]) if not np.isnan(hmax) else -1
            il = int(np.flatnonzero(lv == lmin)[-1]) if not np.isnan(lmin) else -1
            mean_c = float(g["close"].mean()); vsum = float(g["volume"].sum()); asum = float(g["amount"].sum())
            row = {"stock_id": r["sid"], "days": int(len(g)), "n_markets": int(g["mkt"].nunique()), "avg_close_ours": round(mean_c, 2), "avg_close_trunc_ours": _trunc2(mean_c),
                   "high_ours": float(hmax), "high_date_ours": g["date"].iloc[ih] if ih >= 0 else pd.NaT,
                   "low_ours": float(lmin), "low_date_ours": g["date"].iloc[il] if il >= 0 else pd.NaT,
                   "volume_ours": vsum, "amount_ours": asum,
                   "tx_ours": float(g["tx"].sum()) if g["tx"].notna().any() else np.nan,
                   "avg_price_ours": _trunc2(asum / vsum) if vsum > 0 else np.nan}
            for kk, vv in zip(keys, k):
                row[kk] = int(vv)
            out.append(row)
    return pd.DataFrame(out)


def official_yearly_check(res, official: pd.DataFrame, transfer: set | None = None, cal_days: dict | None = None) -> pd.DataFrame:
    """G1：官方年表（上市 FMNPTK＝含量三欄；上櫃 yearlyStock＝只有價五格，量三欄留空 ⇒ 用「量欄是否空白」分市場）vs 我方日檔按年聚合。
    判準：avg_close 逐位相同——⚠ 上市是四捨五入、上櫃是無條件捨去（實測：上市 round 95.9%／trunc 50%，上櫃 trunc 99.98%／round 50%）；
    high／low 逐位相同；high_date／low_date 月日相同（同值取最後一次）；量三欄只在官方有值時比、逐位相同。
    轉板年＝我方日檔該年 market 欄不只一種（資料庫線 0922：資料自己講得出來）⇒ 價五格只比官方那個市場的那一段、量三欄不比（口徑不同）。
    transfer 已不用（保留參數相容），cal_days＝{roc_year: 日曆交易日數} ⇒ 多一欄 days_short（我方該年少於日曆的天數；缺日或無成交都會讓它 > 0）。
    量三欄的差另標 qty_note：官方多且不是 1,000 的倍數 ⇒「零股（口徑）」（資料庫線 0922 §一：官方年表含零股、我方日檔不含）。"""
    all_ = aggregate_ours(res, "Y")[["stock_id", "roc_year", "days", "n_markets"]]
    j = official.merge(all_, on=["stock_id", "roc_year"], how="left")
    j["is_tpex"] = j["volume"].isna()
    seg = pd.concat([aggregate_ours(res, "Y", "twse").assign(is_tpex=False), aggregate_ours(res, "Y", "tpex").assign(is_tpex=True)], ignore_index=True)
    seg = seg.drop(columns=["days", "n_markets"]).rename(columns={})
    j = j.merge(seg, on=["stock_id", "roc_year", "is_tpex"], how="left")
    multi = (j["n_markets"] > 1).to_numpy()
    j["status"] = np.where(j["days"].isna(), "我方該年無成交列", np.where(j["avg_close_ours"].isna(), "我方該年無該市場段", np.where(multi, "轉板年（價比該市場段、量不比）", "比對")))
    j["days_short"] = (j["roc_year"].map(cal_days or {}) - j["days"]) if cal_days else np.nan
    cmp = j["status"].isin(["比對", "轉板年（價比該市場段、量不比）"]).to_numpy()
    _ok = lambda cond: np.where(cmp, cond.to_numpy(float), np.nan)   # 1.0／0.0／NaN（沒得比）
    ours_avg = np.where(j["is_tpex"], j["avg_close_trunc_ours"], j["avg_close_ours"])
    j["avg_ok"] = _ok((pd.Series(ours_avg, index=j.index) - j["avg_close"]).abs() <= 1e-9)
    j["high_ok"] = _ok((j["high_ours"] - j["high"]).abs() <= 1e-9)
    j["low_ok"] = _ok((j["low_ours"] - j["low"]).abs() <= 1e-9)
    j["high_date_ok"] = np.where(cmp, [_official_date_ok(a, b) for a, b in zip(j["high_date_ours"], j["high_date"])], np.nan)
    j["low_date_ok"] = np.where(cmp, [_official_date_ok(a, b) for a, b in zip(j["low_date_ours"], j["low_date"])], np.nan)
    qcmp = cmp & ~multi
    for c in ("volume", "amount", "transactions"):
        oc = "tx_ours" if c == "transactions" else f"{c}_ours"
        j[f"{c}_ok"] = np.where(~qcmp | j[c].isna() | j[oc].isna(), np.nan, ((j[oc] - j[c]).abs() <= 0.5).astype(float))
    j["qty_note"] = _qty_note(j)
    return j


def _qty_note(j: pd.DataFrame) -> np.ndarray:
    """量差註記（資料庫線 1010：算術下界，⛔ 不是充要條件）：
    Δvol ÷ Δtx < 1,000 股/筆 ⇒「零股（口徑）」（整股每筆至少一張，做不出來 ⇒ 必含零股；可當結論）；
    ≥ 1,000 ⇒「不排除有零股」（⛔ 判不出來，不可讀成沒有零股；6949/113 那種 681 張／1 筆／整數單價是鉅額的形狀，未證實）；
    Δvol < 0 ⇒「我方多」。⚠ 原本「差額是不是 1,000 的倍數」那條在 1603/107（1,000 股／4 筆＝每筆 250 股）會判錯，已換掉。"""
    dv = j["volume"] - j["volume_ours"]
    dtx = j["transactions"] - j["tx_ours"]
    with np.errstate(divide="ignore", invalid="ignore"):
        per_tx = np.where(dtx > 0, dv / dtx, np.inf)
    return np.where(j["volume_ok"] == 0, np.where(dv < 0, "我方多", np.where(per_tx < 1000, "零股（口徑）", "不排除有零股")), "")


def official_monthly_check(res, official: pd.DataFrame) -> pd.DataFrame:
    """G2：官方月表（上市 FMSRFK）vs 我方日檔按年月聚合。量三欄逐位相同；high／low 逐位；avg_price（加權＝金額÷股數、兩位小數無條件捨去）逐位相同。"""
    ours = aggregate_ours(res, "M")
    j = official.merge(ours, on=["stock_id", "roc_year", "month"], how="left")
    j["status"] = np.where(j["days"].isna(), "我方該月無成交列", "比對")
    cmp = (j["status"] == "比對").to_numpy()
    _ok = lambda cond: np.where(cmp, cond.to_numpy(float), np.nan)
    j["high_ok"] = _ok((j["high_ours"] - j["high"]).abs() <= 1e-9)
    j["low_ok"] = _ok((j["low_ours"] - j["low"]).abs() <= 1e-9)
    j["avg_price_ok"] = _ok((j["avg_price_ours"] - j["avg_price"]).abs() <= 1e-9)
    for c in ("volume", "amount", "transactions"):
        oc = "tx_ours" if c == "transactions" else f"{c}_ours"
        j[f"{c}_ok"] = np.where(~cmp | j[c].isna() | j[oc].isna(), np.nan, ((j[oc] - j[c]).abs() <= 0.5).astype(float))
    j["qty_note"] = _qty_note(j)
    return j


def official_tpex_ratios(res, tpex: pd.DataFrame) -> pd.DataFrame:
    """G3（描述、不判）：上櫃官方量三欄（張／仟元／千筆）換算後 ÷ 我方年合計 的比值分佈——資料庫線 0737 說口徑不同，母體級分佈它沒量。"""
    ours = aggregate_ours(res, "Y", "tpex")
    if not len(ours):
        return pd.DataFrame(columns=["stock_id", "roc_year", "volume_ratio", "amount_ratio", "tx_ratio"])
    j = tpex.merge(ours, on=["stock_id", "roc_year"], how="inner")
    j["volume_ratio"] = j["volume_lots"] * 1000 / j["volume_ours"].replace(0, np.nan)
    j["amount_ratio"] = j["amount_kntd"] * 1000 / j["amount_ours"].replace(0, np.nan)
    j["tx_ratio"] = j["transactions_k"] * 1000 / j["tx_ours"].replace(0, np.nan)
    return j


def official_summary(yc: pd.DataFrame, mc: pd.DataFrame, tp: pd.DataFrame, miss: pd.DataFrame | None) -> list[str]:
    """G 報告段落。每一欄：比了幾列、不符幾列／幾檔、前幾個例子。"""
    def col_stat(j, c, label):
        v = j[c].dropna()
        if not len(v):
            return f"| {label} | 0 | — | — | — |"
        bad = j.loc[v.index][v.astype(float) < 0.5]
        ex = "、".join(f"{r.stock_id}/{int(r.roc_year)}" + (f"-{int(r.month)}" if "month" in j else "") for r in bad.head(4).itertuples())
        return f"| {label} | {len(v):,} | {len(bad):,} | {bad['stock_id'].nunique():,} | {ex} |"
    twse_y = yc[yc["volume"].notna()]; tpex_y = yc[yc["volume"].isna()]
    nomatch = yc[yc["status"] == "我方該年無成交列"]; pre = int((nomatch["roc_year"] < 104).sum())
    vb = yc[yc["volume_ok"] == 0]
    short = int((vb["days_short"] > 0).sum()) if "days_short" in vb and vb["days_short"].notna().any() else 0
    zl = int((vb["qty_note"] == "零股（口徑）").sum()); mzl = int((mc["qty_note"] == "零股（口徑）").sum()) if len(mc) else 0
    ab = yc[(yc["amount_ok"] == 0) & (yc["volume_ok"] == 1)]
    ab_by_year = ab.groupby("roc_year").size().to_dict()
    L = ["## G. 官方統計交叉核對（`data/meta/official_*.csv`，資料庫線 0737 抓）", "",
         f"年表 {len(yc):,} 列（上市 {len(twse_y):,}、上櫃 {len(tpex_y):,}；民國 {int(yc['roc_year'].min())}～{int(yc['roc_year'].max())}）；"
         f"我方該年無成交列 {len(nomatch):,} 列（其中民國 104 之前＝資料起點前 {pre:,}，**104 起 {len(nomatch) - pre:,}**）；轉板年（我方日檔該年 market 不只一種）{int((yc['status'].str.startswith('轉板')).sum()):,} 列＝價只比該市場段、量不比；我方無該市場段 {int((yc['status'] == '我方該年無該市場段').sum()):,} 列；比對 {int((yc['status'] == '比對').sum()):,} 列。"
         + (f" 官方端點查無（`_official_stats_miss.csv`）{len(miss):,} 檔——是「查無」不是「不符」。" if miss is not None else ""), "",
         "約定（實測出來的，不是文件寫的）：官方兩位小數——上市年表收盤平均＝四捨五入、上櫃年表收盤平均＝無條件捨去、上市月表加權均價＝無條件捨去；最高／最低日期同值取最後一次。", "",
         "| 欄（年表） | 比對列 | 不符列 | 不符檔 | 例 |", "|---|---:|---:|---:|---|",
         col_stat(yc, "avg_ok", "收盤簡單平均（上市四捨五入／上櫃捨去）"), col_stat(yc, "high_ok", "年最高價"), col_stat(yc, "high_date_ok", "年最高價日期"),
         col_stat(yc, "low_ok", "年最低價"), col_stat(yc, "low_date_ok", "年最低價日期"),
         col_stat(yc, "volume_ok", "年成交股數（只上市）"), col_stat(yc, "amount_ok", "年成交金額（只上市）"), col_stat(yc, "transactions_ok", "年成交筆數（只上市）"), "",
         f"年成交股數不符 {len(vb):,} 列裡，**零股口徑（Δvol÷Δtx < 1,000 股/筆，算術下界）{zl:,} 列**（官方年表含零股、我方日檔不含——資料庫線 0922／1010，⛔ 不是缺資料）；其餘 {len(vb) - zl:,} 列（{vb[vb['qty_note'] != '零股（口徑）']['qty_note'].value_counts().to_dict()}；「不排除有零股」＝判不出來，⛔ 不可讀成沒有零股；6949/113 是鉅額的形狀、未證實）。我方天數少於日曆的 {short:,} 列（缺日或該股無成交都會如此，⛔ 分不出）。",
         f"年成交金額不符而股數相同：{len(ab):,} 列，逐年 {ab_by_year}——⚠ 民國 109 那一年是**另一個口徑**（資料庫線 0950：股數不符率十二年最低、金額 70.9%，只作用在金額欄、方向單一、量級 1e-9），⛔ 逐年趨勢裡 109 那格是假尖峰，標註不濾。", "",
         f"月表（上市 FMSRFK）{len(mc):,} 列（民國 {sorted(mc['roc_year'].unique().tolist()) if len(mc) else '—'}）；我方該月無成交列 {int((mc['status'] != '比對').sum()):,} 列；月量不符裡零股口徑 {mzl:,} 列。", "",
         "| 欄（月表） | 比對列 | 不符列 | 不符檔 | 例 |", "|---|---:|---:|---:|---|",
         col_stat(mc, "volume_ok", "月成交股數"), col_stat(mc, "amount_ok", "月成交金額"), col_stat(mc, "transactions_ok", "月成交筆數"),
         col_stat(mc, "high_ok", "月最高價"), col_stat(mc, "low_ok", "月最低價"), col_stat(mc, "avg_price_ok", "月加權均價（金額÷股數，無條件捨去）"), ""]
    if len(tp):
        q = lambda c: "／".join(f"{tp[c].quantile(x):.3f}" for x in (0.05, 0.5, 0.95))
        L += [f"上櫃量三欄（官方 yearlyStock ÷ 我方年合計，{len(tp):,} 列；⛔ 只描述不判）：股數 p05／p50／p95 ＝ {q('volume_ratio')}；金額 {q('amount_ratio')}；筆數 {q('tx_ratio')}。", ""]
    return L


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


def _selftest() -> int:
    """G 的合成資料自測（照真回應的形狀：官方兩位小數、日期 'M/DD'、上櫃量三欄空白）。rc != 0 或輸出含 ✗ 才算紅。"""
    fail = 0
    def check(cond, msg):
        nonlocal fail
        print(("  ✓ " if cond else "  ✗ ") + msg); fail += 0 if cond else 1
    d = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-02-03", "2025-12-30", "2026-01-05"]).to_numpy()
    close = np.array([10.0, 10.1, np.nan, 10.4, 20.0]); high = np.array([10.2, 10.5, np.nan, 10.5, 21.0]); low = np.array([9.8, 9.9, np.nan, 10.0, 19.0])
    vol = np.array([1000., 2000., np.nan, 3000., 500.]); amt = np.array([10000., 20400., np.nan, 31500., 10000.]); tx = np.array([5., 6., np.nan, 7., 1.])
    res = [{"sid": "1111", "dates": d, "close": close, "high": high, "low": low, "volume": vol, "amount": amt, "tx": tx, "mkt": np.array(["twse"] * 5)}]
    # 2025：有成交 3 天；簡單平均 (10+10.1+10.4)/3 = 10.1666 → 10.17；最高 10.5 兩天（1/03 與 12/30，取第一個）；最低 9.8 於 1/02；量 6000、金額 61900、筆 18
    Y = pd.DataFrame([{"stock_id": "1111", "roc_year": 114, "volume": 6000, "amount": 61900, "transactions": 18, "high": 10.5, "high_date": "1/03", "low": 9.8, "low_date": "1/02", "avg_close": 10.17},
                      {"stock_id": "1111", "roc_year": 113, "volume": np.nan, "amount": np.nan, "transactions": np.nan, "high": 1.0, "high_date": "1/02", "low": 1.0, "low_date": "1/02", "avg_close": 1.0},
                      {"stock_id": "2222", "roc_year": 114, "volume": 1, "amount": 1, "transactions": 1, "high": 1.0, "high_date": "1/02", "low": 1.0, "low_date": "1/02", "avg_close": 1.0}])
    yc = official_yearly_check(res, Y)
    r = yc[(yc.stock_id == "1111") & (yc.roc_year == 114)].iloc[0]
    check(r["status"] == "比對" and r["days"] == 3, "無收盤的列不算成交日 ⇒ 2025 有 3 天")
    check(r["avg_ok"] == 1.0 and r["avg_close_ours"] == 10.17, "收盤簡單平均 10.17（四捨五入到兩位）")
    check(r["high_ok"] == 1.0 and r["low_ok"] == 1.0, "年最高 10.5／最低 9.8 逐位相同")
    check(r["high_date_ok"] == 0.0 and r["low_date_ok"] == 1.0, "最高價同值兩天（1/03、12/30）官方取最後一次 ⇒ 官方寫 1/03 判不符；最低價日期 1/02 合")
    check(pd.Timestamp(r["high_date_ours"]) == pd.Timestamp("2025-12-30"), "我方最高價日期＝最後一次出現 12/30")
    check(r["volume_ok"] == 1.0 and r["amount_ok"] == 1.0 and r["transactions_ok"] == 1.0, "量／金額／筆數合計逐位相同")
    r13 = yc[(yc.stock_id == "1111") & (yc.roc_year == 113)].iloc[0]
    check(r13["status"] == "我方該年無成交列" and pd.isna(r13["avg_ok"]) and pd.isna(r13["volume_ok"]), "我方沒有那一年 ⇒ 狀態標出、各欄不判")
    r22 = yc[yc.stock_id == "2222"].iloc[0]
    check(r22["status"] == "我方該年無成交列", "我方無檔 ⇒ 我方該年無成交列")
    Y2 = Y.copy(); Y2.loc[0, "avg_close"] = 10.18; Y2.loc[0, "volume"] = 6001; Y2.loc[0, "high_date"] = "12/30"
    y2 = official_yearly_check(res, Y2).iloc[0]
    check(y2["avg_ok"] == 0.0 and y2["volume_ok"] == 0.0 and y2["high_date_ok"] == 1.0, "官方改 10.18／6001／12/30 ⇒ 平均、量判不符；日期 12/30＝最後一次 ⇒ 合")
    Y4 = Y.copy(); Y4.loc[0, "volume"] = np.nan; Y4.loc[0, "amount"] = np.nan; Y4.loc[0, "transactions"] = np.nan; Y4.loc[0, "avg_close"] = 10.16
    res_tpex = [dict(res[0], mkt=np.array(["tpex"] * 5))]
    y4 = official_yearly_check(res_tpex, Y4).iloc[0]
    check(pd.isna(y4["volume_ok"]) and y4["avg_ok"] == 1.0 and bool(y4["is_tpex"]), "上櫃形狀（量三欄空白）⇒ 量不判、收盤平均用無條件捨去 10.16 ⇒ 合")
    Y4.loc[0, "avg_close"] = 10.17
    check(official_yearly_check(res_tpex, Y4).iloc[0]["avg_ok"] == 0.0, "上櫃寫 10.17（四捨五入值）⇒ 不符（上櫃是捨去）")
    y4b = official_yearly_check(res, Y4).iloc[0]
    check(y4b["status"] == "我方該年無該市場段" and pd.isna(y4b["avg_ok"]), "官方上櫃列、我方該年全是 twse ⇒ 我方該年無該市場段、不比")
    yt = official_yearly_check(res, Y, None, cal_days={114: 5, 113: 5}).iloc[0]
    check(yt["status"] == "比對" and yt["days_short"] == 2, "days_short＝日曆 5 − 我方 3 ＝ 2")
    # 轉板年：1/02 在 tpex、其餘 twse ⇒ 官方上市表只算 twse 段（1/03、12/30：平均 10.25、最低 9.9 於 1/03）、量不比
    rt = [dict(res[0], mkt=np.array(["tpex", "twse", "twse", "twse", "twse"]))]
    Yt = Y.copy(); Yt.loc[0, "avg_close"] = 10.25; Yt.loc[0, "low"] = 9.9; Yt.loc[0, "low_date"] = "1/03"
    yt2 = official_yearly_check(rt, Yt).iloc[0]
    check(yt2["status"].startswith("轉板年") and yt2["n_markets"] == 2 and yt2["avg_ok"] == 1.0 and yt2["low_ok"] == 1.0 and yt2["low_date_ok"] == 1.0 and pd.isna(yt2["volume_ok"]), "轉板年：價只比 twse 段（平均 10.25、最低 9.9）、量不比")
    Yt2 = Yt.copy(); Yt2.loc[0, "volume"] = np.nan; Yt2.loc[0, "amount"] = np.nan; Yt2.loc[0, "transactions"] = np.nan; Yt2.loc[0, "avg_close"] = 10.0; Yt2.loc[0, "high"] = 10.2; Yt2.loc[0, "high_date"] = "1/02"; Yt2.loc[0, "low"] = 9.8; Yt2.loc[0, "low_date"] = "1/02"
    yt3 = official_yearly_check(rt, Yt2).iloc[0]
    check(yt3["avg_ok"] == 1.0 and yt3["high_ok"] == 1.0 and yt3["high_date_ok"] == 1.0, "同一轉板年、上櫃表那列 ⇒ 只比 tpex 段（1/02：10.0／10.2）")
    Yz = Y.copy(); Yz.loc[0, "volume"] = 6001; Yz.loc[0, "transactions"] = 19
    yz = official_yearly_check(res, Yz).iloc[0]
    check(yz["volume_ok"] == 0.0 and yz["qty_note"] == "零股（口徑）", "官方多 1 股 1 筆 ⇒ 1 股/筆 < 1,000 ⇒ 零股（口徑）")
    Yz.loc[0, "volume"] = 5000
    check(official_yearly_check(res, Yz).iloc[0]["qty_note"] == "我方多", "官方少 ⇒ 我方多")
    Yz.loc[0, "volume"] = 7000; Yz.loc[0, "transactions"] = 22
    check(official_yearly_check(res, Yz).iloc[0]["qty_note"] == "零股（口徑）", "1603/107 型：官方多 1,000 股／4 筆＝250 股/筆 ⇒ 零股（口徑）（舊判準「千的倍數」會判錯）")
    Yz.loc[0, "volume"] = 687000; Yz.loc[0, "transactions"] = 19
    check(official_yearly_check(res, Yz).iloc[0]["qty_note"] == "不排除有零股", "6949/113 型：官方多 681,000 股／1 筆 ⇒ ≥ 1,000 ⇒ 不排除有零股（判不出來）")
    Yz.loc[0, "volume"] = 7000; Yz.loc[0, "transactions"] = 18
    check(official_yearly_check(res, Yz).iloc[0]["qty_note"] == "不排除有零股", "官方多 1,000 股但筆數相同（Δtx=0）⇒ 判不出來 ⇒ 不排除有零股")
    Yz.loc[0, "volume"] = 8000; Yz.loc[0, "transactions"] = 20
    check(official_yearly_check(res, Yz).iloc[0]["qty_note"] == "不排除有零股", "剛好 1,000 股/筆（2,000 股／2 筆）＝整股做得出來 ⇒ 不排除有零股（界線不含等號）")
    M = pd.DataFrame([{"stock_id": "1111", "roc_year": 114, "month": 1, "high": 10.5, "low": 9.8, "avg_price": 10.13, "transactions": 11, "amount": 30400, "volume": 3000, "turnover": 0.1},
                      {"stock_id": "1111", "roc_year": 114, "month": 2, "high": 1.0, "low": 1.0, "avg_price": 1.0, "transactions": 1, "amount": 1, "volume": 1, "turnover": 0.1}])
    mc = official_monthly_check(res, M)
    m1 = mc.iloc[0]; m2 = mc.iloc[1]
    check(m1["status"] == "比對" and m1["volume_ok"] == 1.0 and m1["amount_ok"] == 1.0 and m1["transactions_ok"] == 1.0, "月量／金額／筆數合計逐位相同")
    check(m1["avg_price_ok"] == 1.0 and m1["avg_price_ours"] == 10.13, "月加權均價 30400÷3000 = 10.1333 → 10.13")
    M3 = M.copy(); M3.loc[0, "amount"] = 30590; M3.loc[0, "avg_price"] = 10.19
    res3 = [dict(res[0], amount=np.array([10000., 20590., np.nan, 31500., 10000.]))]
    check(official_monthly_check(res, M.assign(volume=[3001, 1], transactions=[12, 1])).iloc[0]["qty_note"] == "零股（口徑）", "月表：官方多 1 股 1 筆 ⇒ 零股（口徑）")
    check(official_monthly_check(res3, M3).iloc[0]["avg_price_ok"] == 1.0 and official_monthly_check(res3, M3).iloc[0]["avg_price_ours"] == 10.19, "30590÷3000 = 10.1966 ⇒ 捨去 10.19（四捨五入會是 10.20）")
    check(_trunc2(10.1966) == 10.19 and _trunc2(10.2) == 10.2 and _trunc2(0.29) == 0.29, "_trunc2：捨去、整值不動、浮點 0.29 不掉成 0.28")
    check(m1["high_ok"] == 1.0 and m1["low_ok"] == 1.0, "月最高 10.5／最低 9.8")
    check(m2["status"] == "我方該月無成交列" and pd.isna(m2["volume_ok"]), "2 月只有無收盤列 ⇒ 我方該月無成交列")
    M2 = M.copy(); M2.loc[0, "avg_price"] = 10.14
    check(official_monthly_check(res, M2).iloc[0]["avg_price_ok"] == 0.0, "均價差 0.01 ⇒ 不符")
    TP = pd.DataFrame([{"stock_id": "1111", "roc_year": 114, "volume_lots": 6.222, "amount_kntd": 64.2, "transactions_k": 0.037, "wavg_price_derived": 10.3}])
    tp = official_tpex_ratios(res_tpex, TP)
    check(abs(tp.iloc[0]["volume_ratio"] - 6222 / 6000) < 1e-9 and abs(tp.iloc[0]["tx_ratio"] - 37 / 18) < 1e-9, "上櫃比值＝官方換算÷我方（張×1000／仟元×1000／千筆×1000）")
    tpr = official_tpex_ratios(rt, TP)
    check(abs(tpr.iloc[0]["volume_ratio"] - 6222 / 1000) < 1e-9 and len(official_tpex_ratios(res, TP)) == 0, "轉板年只取 tpex 段（1/02 量 1000）；全 twse 的檔 ⇒ 沒有列")
    check(_official_date_ok(np.datetime64("2025-07-22"), "7/22") == 1.0 and _official_date_ok(np.datetime64("2025-07-22"), "07/23") == 0.0 and np.isnan(_official_date_ok(pd.NaT, "7/22")), "日期比月日、缺值 ⇒ NaN")
    L = official_summary(yc, mc, tp, None)
    check(any("| 收盤簡單平均" in x and "| 1 |" in x for x in L) and any("上櫃量三欄" in x for x in L), "報告段落：年表比對列數與上櫃比值行都在")
    print("結果：", "全綠" if fail == 0 else f"✗ {fail} 條")
    return 1 if fail else 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
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
                                       "adj_events", "adj_bad", "adj_preclose_bad", "adj_ref_checked", "adj_ref_bad", "cal_days", "traded_days", "coverage", "names", "change_checked", "change_bad")}
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
    # G 官方統計
    meta = os.path.join(D.DATA, "meta")
    Y = pd.read_csv(os.path.join(meta, "official_yearly_close.csv"), dtype={"stock_id": str})
    M = pd.read_csv(os.path.join(meta, "official_monthly_amount.csv"), dtype={"stock_id": str})
    TP = pd.read_csv(os.path.join(meta, "official_yearly_tpex.csv"), dtype={"stock_id": str})
    if not (len(Y) and len(M)):
        raise SystemExit("⛔ data/meta/official_*.csv 沒有內容（分支上的 data/ 比 main 舊？先 git checkout origin/main -- data/meta）")
    miss_p = os.path.join(meta, "_official_stats_miss.csv")
    miss = pd.read_csv(miss_p, dtype=str) if os.path.exists(miss_p) else None
    cal_days = pd.Series(cal.year - 1911).value_counts().to_dict()
    yc = official_yearly_check(res, Y, None, cal_days); mc = official_monthly_check(res, M); tp = official_tpex_ratios(res, TP)
    yc.to_csv(os.path.join(OUT, "official_yearly_check.csv"), index=False); mc.to_csv(os.path.join(OUT, "official_monthly_check.csv"), index=False)
    tp.to_csv(os.path.join(OUT, "official_tpex_ratios.csv"), index=False)
    print(f"官方統計 年 {len(yc):,} 列、月 {len(mc):,} 列，{time.time() - t0:.0f}s", file=sys.stderr)
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
           f"- **還原因子 vs 實際價格**：{int(T['adj_events'].sum()):,} 個事件裡，事件日收盤 ÷（前一有成交日收盤 × factor）超出 ±10% 的有 **{int(T['adj_bad'].sum()):,} 個／{int((T['adj_bad'] > 0).sum()):,} 檔**；因子檔的 `pre_close` 與實際前收差 > 0.5% 的 **{int(T['adj_preclose_bad'].sum()):,} 個**；前收 × factor 對 `ref_price` 差 > 0.5% 的 **{int(T['adj_ref_bad'].sum()):,}／{int(T['adj_ref_checked'].sum()):,} 個**（有 ref_price 的事件）。前者超出代表因子與價格接不起來（或復牌首日連續跳），清單見 `adj_mismatch.csv`。",
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
    Ln += official_summary(yc, mc, tp, miss)
    with open(os.path.join(OUT, "DB_AUDIT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(Ln) + "\n")
    print(f"寫入 {OUT}/DB_AUDIT.md，{time.time() - t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG正2現金 描述件（裁定 seq219；⛔ 不判、⛔ 不計 N）——使用者：「回落深沒關係的情況下呢？正二？」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLev2_desc
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLev2_desc_check.py

一、純抱（買了不動）：00631L、00685L、0050、0052 × 探索段／確認段／全段
    ・口徑同本體（researchLev2.engine）：窗首開盤買進、付一次 0.385%、之後不動；年化 ＝ 末值^(245／窗內日數) − 1；
      回落含 1.0 起點；「100 萬期末」＝ 窗尾收盤市值；「最慘時剩」＝ 路徑最低點 × 100 萬
    ・窗：三檔 探索 2015-11-02～2021-12-30、確認 2022-01-03～2026-08-24、全段 2015-11-02～2026-08-24；
      00685L 探索 2018-01-15～2021-12-30、全段 2018-01-15～2026-08-24（照實寫）
二、事後改挑法（⚠ 逐字標「事後改挑法」）：探索段只看年化最高 ⇒ 報確認段年化
    ・問一 264 格：三檔組 132 格（00631L，三檔窗）與 00685L 132 格（00685L 窗）分開挑（窗不同、不混比）
    ・問二主讀法池 12 格（裁定 seq218：X3 退化格不進池）
    ・同分取正2 比例較低；數字直接讀 body_q1.csv／body_q2.csv（本體已算、已查核）
三、壓力描述（⚠ 逐字標「合成、非實際 ETF」）：
    ・0050 早年日 K：tw-stock-data main data/early/daily（釘 EARLY_SHA；與 3edc0e2206 的 0050 列 md5 相同）
    ・除息：data/early/exright 的 0050 列；還原照 early_data.adj_0050（58ffe37b65）：factor ＝ 官方參考價 ÷ 除息前收盤、
      F(d) ＝ 事件日嚴格大於 d 的 factor 連乘
    ・錨：2012～2014 的日 K 對 data/extra/0050_2012_2014.csv、factor 對 data/extra/0050_adj_2012_2014.csv；
      每筆除息的 pre_close 對前一交易日收盤
    ・合成正2：L_t ＝ L_{t−1} ×（1 ＋ 2 r_t − 0.01／245），r_t ＝ 0050 還原收盤日報酬（每日重設、每日扣內扣費）
    ・期間：2008-01～2009-03、2011-01～2011-12；起點 ＝ 期間前一個交易日收盤 ＝ 1.0（期間第一天的報酬算在內）
    ・另報：同一合成法在 2015-11-02～2026-08-24 對真實 00631L 的差（合成法本身的誤差量級，描述）
"""
from __future__ import annotations

import io
import json
import os
import subprocess

import numpy as np
import pandas as pd

from . import data as D
from . import rerun17 as RR
from . import researchLev2 as L2

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsLev2")
DB = os.path.expanduser("~/tw-stock-data")
EARLY_SHA = "c9623901f2"            # main（≥ 3edc0e2206）；啟動時展開成完整 sha 並寫進 summary
FEE = 0.01 / 245
ANN = 245
PERIODS = {"2008 金融海嘯（2008-01～2009-03）": ("2008-01-01", "2009-03-31"), "2011 歐債（2011-01～2011-12）": ("2011-01-01", "2011-12-31")}
WIN = {"三檔": {"探索": ("2015-11-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "全段": ("2015-11-02", "2026-08-24")},
       "00685L": {"探索": ("2018-01-15", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "全段": ("2018-01-15", "2026-08-24")}}
LOGF = os.path.join(OUT, "desc_run.log")


def log(m):
    print(m, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(m + "\n")


def git(*a):
    return subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True, check=True).stdout


def early_0050(sha):
    rows = git("grep", "-h", "_0050,", sha, "--", "data/early/daily/")
    cols = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
            "shares", "transactions", "price_basis", "last_price"]
    d = pd.read_csv(io.StringIO(rows), header=None, names=cols, dtype=str)
    d = d[d["stock_id"] == "0050"].copy()
    d["close"] = pd.to_numeric(d["close"]); d = d.sort_values("date").reset_index(drop=True)
    files = [x.split("/")[-1][:-4] for x in git("ls-tree", "-r", "--name-only", sha, "data/early/daily").split()]
    ex = git("grep", "-h", ",0050,", sha, "--", "data/early/exright/")
    e = pd.read_csv(io.StringIO(ex), header=None, names=["date", "stock_id", "pre_close", "ref_price", "value", "kind", "open_base",
                                                         "limit_up", "limit_down", "ex_div_ref"], dtype={"date": str, "stock_id": str})
    e = e[e["stock_id"] == "0050"].sort_values("date").reset_index(drop=True)
    e["factor"] = e["ref_price"].astype(float) / e["pre_close"].astype(float)       # early_data.adj_0050 同式
    return d, sorted(files), e


def adjusted(d, e):
    ev = e["date"].to_numpy(); f = e["factor"].to_numpy(float)
    F = np.array([np.prod(f[ev > x]) for x in d["date"].to_numpy()])
    return d["close"].to_numpy(float) * F


def synth(adj, dates, a, b):
    """期間 [a,b] 內每日：L ← L×(1＋2r−FEE)；起點＝期間前一交易日收盤（1.0）。回傳 (0050 路徑, 合成路徑, 日期)。"""
    i0 = int(np.searchsorted(dates, a)); i1 = int(np.searchsorted(dates, b, side="right")) - 1
    r = adj[i0:i1 + 1] / adj[i0 - 1:i1] - 1
    lev = np.cumprod(1 + 2 * r - FEE); b50 = adj[i0:i1 + 1] / adj[i0 - 1]
    return b50, lev, dates[i0:i1 + 1], dates[i0 - 1]


def dd_stats(path):
    p = np.concatenate([[1.0], path]); pk = np.maximum.accumulate(p)
    dd = (p - pk) / pk
    return float(dd.min()), float(p.min()), int(np.argmin(p)) - 1, float(path[-1])


def main():
    os.makedirs(OUT, exist_ok=True); open(LOGF, "w").close()
    log(f"===== researchLev2_desc {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜裁定 seq219｜⛔ 不判、不計 N =====")
    S = {"性質": "描述（裁定 seq219）；⛔ 不判、⛔ 不計 N"}

    # ── 一、純抱
    RR.use_snapshot()
    cal = D.load_calendar(); O, C = L2.load_px(cal)
    bh = []
    for sid in ("00631L", "00685L", "0050", "0052"):
        w = WIN["00685L" if sid == "00685L" else "三檔"]
        for seg, (a, b) in w.items():
            i0, i1 = L2.seg_idx(cal, a, b); n = i1 - i0 + 1
            r = L2.engine((sid,), np.ones((n, 1)), np.zeros(n, bool), i0, O, C)
            c_, m_ = L2.perf(r["eq"]); low = float(min(1.0, r["eq"].min()))
            bh.append({"檔": sid, "段": seg, "窗": f"{a}～{b}", "交易日": n, "年化": c_, "回落": m_,
                       "100萬期末": float(r["eq"][-1] * 1e6), "最慘時剩": low * 1e6,
                       "最慘日": str(cal[i0 + int(np.argmin(r["eq"]))].date()) if r["eq"].min() < 1.0 else "起點"})
    bh = pd.DataFrame(bh); bh.to_csv(os.path.join(OUT, "desc_buyhold.csv"), index=False, encoding="utf-8")
    log("[純抱]\n" + bh.to_string())

    # ── 二、事後改挑法（只看年化最高）
    q1 = pd.read_csv(os.path.join(OUT, "body_q1.csv"), dtype={"ETF": str, "正2": str})
    q2 = pd.read_csv(os.path.join(OUT, "body_q2.csv"), dtype={"ETF": str, "正2": str})
    mx = []

    def pick(df, keys, levkey):
        d = df.copy(); d["_o"] = range(len(d))
        return d.sort_values(["年化", levkey, "_o"], ascending=[False, True, True]).iloc[0]
    for nm, grp in (("問一 三檔組 132 格（00631L）", "挑選池"), ("問一 00685L 132 格（00685L 窗）", "00685L描述")):
        ex = q1[(q1["段"] == "探索") & (q1["組"] == grp)]
        p = pick(ex, None, "正2%")
        c = q1[(q1["段"] == "確認") & (q1["組"] == grp) & (q1["ETF"] == p["ETF"]) & (q1["正2"] == p["正2"]) & (q1["ETF%"] == p["ETF%"]) & (q1["正2%"] == p["正2%"])].iloc[0]
        mx.append({"標": "事後改挑法", "池": nm, "挑中": f"{p['ETF']} {p['ETF%']}%＋{p['正2']} {p['正2%']}%＋現金 {p['現金%']}%",
                   "探索年化": p["年化"], "探索回落": p["回落"], "確認年化": c["年化"], "確認回落": c["回落"], "確認對0050（描述）": c["標籤"]})
    ex2 = q2[(q2["段"] == "探索") & (q2["組"] == "挑選池")]
    p = pick(ex2, None, "平均正2權重")
    c = q2[(q2["段"] == "確認") & (q2["條件"] == p["條件"]) & (q2["換法"] == p["換法"]) & (q2["ETF"] == p["ETF"]) & (q2["正2"] == p["正2"])].iloc[0]
    mx.append({"標": "事後改挑法", "池": "問二 主讀法池 12 格", "挑中": f"{p['條件']}×{p['換法']}×ETF {p['ETF']}×{p['正2']}",
               "探索年化": p["年化"], "探索回落": p["回落"], "確認年化": c["年化"], "確認回落": c["回落"], "確認對0050（描述）": c["標籤"]})
    mx = pd.DataFrame(mx); mx.to_csv(os.path.join(OUT, "desc_maxcagr.csv"), index=False, encoding="utf-8")
    log("[事後改挑法]\n" + mx.to_string())

    # ── 三、壓力（合成、非實際 ETF）
    sha = git("rev-parse", EARLY_SHA).strip()
    S["早年資料"] = {"sha": sha, "與3edc0e2206的0050列相同": None}
    d, files, e = early_0050(sha)
    d3, _, e3 = early_0050("3edc0e2206")
    S["早年資料"]["與3edc0e2206的0050列相同"] = bool(d.equals(d3) and e.equals(e3))
    dates = d["date"].to_numpy()
    gaps = sorted(set(files) - set(dates))
    # 錨一：2012～2014 日 K 對 data/extra/0050_2012_2014.csv
    xd = pd.read_csv(io.StringIO(git("show", f"{sha}:data/extra/0050_2012_2014.csv")), dtype={"date": str})
    m = d.merge(xd[["date", "close"]], on="date", how="inner", suffixes=("", "_x"))
    x_only = sorted(set(xd["date"]) - set(dates)); e_only = sorted(set(dates[(dates >= "2012-01-01") & (dates <= "2014-12-31")]) - set(xd["date"]))
    # 錨二：factor 對 data/extra/0050_adj_2012_2014.csv
    xa = pd.read_csv(io.StringIO(git("show", f"{sha}:data/extra/0050_adj_2012_2014.csv")), dtype={"date": str})
    fa = e.merge(xa[["date", "factor"]], on="date", suffixes=("", "_x"))
    # 錨三：pre_close ＝ 前一交易日收盤
    pc = []
    for r in e.itertuples():
        j = int(np.searchsorted(dates, r.date))
        pc.append(abs(float(r.pre_close) - float(d["close"].iloc[j - 1])) if 0 < j < len(dates) and dates[j] == r.date else np.nan)
    S["錨"] = {"0050早年日K列": len(d), "early/daily 檔數": len(files), "0050缺日": gaps,
              "2012～2014 對 extra 同日列": len(m), "收盤最大差": float((m["close"] - m["close_x"]).abs().max()),
              "只在extra": x_only, "只在early": e_only,
              "除息事件": len(e), "2012～2014 factor 對 extra 列": len(fa), "factor 最大差": float((fa["factor"] - fa["factor_x"]).abs().max()),
              "pre_close 對前一日收盤最大差": float(np.nanmax(pc)), "除息日不是交易日": int(np.isnan(pc).sum())}
    log(f"[早年錨] {S['錨']}")
    ok = (not gaps and S["錨"]["收盤最大差"] == 0 and not x_only and not e_only and S["錨"]["factor 最大差"] < 5e-9
          and S["錨"]["pre_close 對前一日收盤最大差"] == 0 and S["錨"]["除息日不是交易日"] == 0)
    S["錨"]["全過"] = bool(ok)
    if not ok:
        raise SystemExit("⛔ 早年 0050 錨不過")
    adj = adjusted(d, e)
    st = []
    for nm, (a, b) in PERIODS.items():
        b50, lev, dd_, base = synth(adj, dates, a, b)
        for who, path in (("合成正2（0050 日報酬×2、每日重設、扣 1%／年；合成、非實際 ETF）", lev), ("0050（還原、參照）", b50)):
            mdd, low, il, end = dd_stats(path)
            st.append({"期間": nm, "起點（=1.0）": f"{base} 收盤", "迄": dd_[-1], "交易日": len(path), "對象": who,
                       "最大跌幅": mdd, "100萬谷底剩": low * 1e6, "谷底日": dd_[il] if il >= 0 else "起點", "100萬期末": end * 1e6,
                       "期間內除息": ",".join(e["date"][(e["date"] >= dd_[0]) & (e["date"] <= dd_[-1])])})
    st = pd.DataFrame(st); st.to_csv(os.path.join(OUT, "desc_stress.csv"), index=False, encoding="utf-8")
    log("[壓力]\n" + st.to_string())

    # 合成法對真實 00631L（2015-11-02～2026-08-24）
    i0, i1 = L2.seg_idx(cal, "2015-11-02", "2026-08-24")
    bb = RR.load_bench(cal)[i0 - 1:i1 + 1]; rr = bb[1:] / bb[:-1] - 1
    syn = np.cumprod(1 + 2 * rr - FEE); real = C["00631L"][i0:i1 + 1] / C["00631L"][i0 - 1]
    n = len(syn)
    S["合成法校驗_對00631L"] = {"窗": "2015-11-02～2026-08-24（收盤對收盤、不含成本）", "合成年化": float(syn[-1] ** (ANN / n) - 1),
                           "真實年化": float(real[-1] ** (ANN / n) - 1), "合成回落": dd_stats(syn)[0], "真實回落": dd_stats(real)[0],
                           "日報酬差標準差": float(np.std(np.diff(np.log(syn), prepend=0) - np.diff(np.log(real), prepend=0), ddof=1))}
    log(f"[合成法校驗] {S['合成法校驗_對00631L']}")
    S["必附"] = "正2 每日重設、盤整耗損；00631L 上市 2014，真實資料沒經歷 2008 那種熊市"
    json.dump(S, open(os.path.join(OUT, "desc_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[完]")


if __name__ == "__main__":
    main()

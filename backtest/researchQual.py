# -*- coding: utf-8 -*-
"""PREREG品質 seq1（台股策略線 登錄 sha 24e7fb594193b9c0；裁定 seq256 發號 N_組合 ＋2、§二 4；seq259 §四）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchQual [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchQual_check.py

═══ 登錄定義（§二、§三，逐字照做）═══
  Q1 ROE ＝ TTM 母公司淨利 ÷ 近兩期母公司權益平均（母公司欄空 ⇒ ni／equity_total）｜Q2 營業利益÷資產（非毛利）＝ TTM 營業利益 ÷ 期末總資產
  Q3 ROA ＝ TTM 稅後淨利 ÷ 近兩期總資產平均｜Q4 研發強度 ＝ TTM 研發費用 ÷ TTM 營收（研發空白 ⇒ 不排名）；分母 ≤ 0 或不足 4 季 ⇒ 不排名
  TTM ＝ 上年度全年 ＋ 本年 YTD − 上年同期 YTD（Q4 ＝ 全年；⛔ 不用 *_q 相加）
  甲族：每期依 Qk 取前 N｜乙族：池 ＝ 最新可用月營收創 24 月新高（營飆同定義）的股票，池內依 Qk 取前 N；並列同池依「成交量相對放大」挑（營量 v1 挑法）
  頻率 月／季／半年 × N 10／20 ⇒ 每族 4 × 3 × 2 ＝ 24 格；金融保險業不參與排名；等權、0.585%、仍入選續抱
═══ 本線落地讀法（⭐ 看任何報酬前寫死）═══
  B1 財報：fin_hist（tw-stock-data main a2dadbca4a ＝ fin_hist 最新一次變動，git archive 到 ~/msdata/<sha>，唯讀）；同 (stock_id, period) 重複取最後一列
  B2 可用日 ⭐ A2 暫定（逐字）：「季財報可用日 A2 暫定（有 t57sb01 時戳用時戳；其餘法定期限＋5 個交易日緩衝）；A0 落地後重跑定案」
     時戳 ＝ meta/filing_dates.csv uploaded_at 的日期 ⇒ 之後第一個交易日；其餘 ⇒ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 次年 3/31）之後第一個交易日再往後 5 個交易日
     換股日 e 可用 ⇔ 可用日位置 ≤ e（e 開盤買，可用日當天開盤前已知）；取可用的最新一季
  B3「近兩期」＝ 該季與前一季的期末值（例 2020Q1 ⇒ 2020Q1、2019Q4）；兩期都要有限、平均 ＞ 0
     Q1 母公司欄空 ＝ TTM nip 算不出 或 兩期 equity_parent 任一缺 ⇒ 改 TTM ni ÷ equity_total 兩期平均
  B4 金融保險業 ＝ 快照 meta/industry.csv 名稱「金融保險業／金融業／金融保險」（強勢類股 U5 同）
  B5 換股日 e ＝ 當月 W1 量測日的次一交易日；季 ＝ 1、4、7、10 月；半年 ＝ 1、7 月（強勢類股 U3 延伸）
  B6 乙族池 ＝ p4_features.rev_hi24_flags 在 e ＝ 100 ∩ 當月 eligible ∩ 非金融；成交量相對放大 ＝ 量測日（e−1）那根有效 K 棒的成交金額 ÷ 前 60 根有效 K 棒金額中位（researchp1 relvol 同式）
  B7 換股簿 ＝ researchMomX.sim_book（強勢類股 sim_book＋停止交易強制出場：開）⇒ 按月／季／半年換股、窗尾照市值 ⇒ 沒有固定持有天數出場 ⇒ 依構造不因資料尾截斷（t1_censor 不適用，照實寫）
  B8 退化格（K7）：探索段 平均持股 ＜ N÷2 或 現金 ＞ 30% ⇒ 不參與挑格
  B9 挑格：每族探索段（2017-03～2021-12）過使用者判準者取比值最高；都沒過取比值最高；平手取年化高、再 月＜季＜半年、N 小、Q1＜Q2＜Q3＜Q4
     判定：確認段、早年段各照使用者判準；兩段都合格 ⇒「合格」；只確認段合格 ⇒「只在一段合格」；其餘照實（兩段標籤並列）
  B10 早年段 2014-06～2016-12（只上市）：主快照日曆 2015-01-05 起、panel_ext eligible 2015-08 起 ⇒
      甲 ＝ 早年版面（~/earlydata/3edc0e2206/main，W1 eligible 2012-06 起有）換股日 2014-06～2014-12；乙 ＝ 主快照、只上市、換股日 2015-08～2016-12；
      兩段各自期初全現金，逐日報酬串成一條（中間 2015-01～07 空窗不計）；0050 同日串接
  B10b 乙族在早年乙：主快照月營收 2015-01 起 ⇒ 24 月新高到 2017 才算得出（池 ＝ 0）⇒ 早年乙的月營收改用「早年版面 2003～2014 ＋ 主快照 2015 起」接起來（月營收是原始值、不涉還原）；
       主窗照主快照（營飆同定義）不動
  B11 假訊號（同池隨機）：挑中格的頻率與 N；每個換股日從同一個排名母體（甲：eligible∩非金融∩Qk 可算；乙：乙族池）不放回抽 N；1,000 次；p ＝ 隨機年化 ≥ 本格
  B12 描述：挑中格另報 全賣全買、含金融版；確認段合格／另列 ⇒ 出場敏感度（新規矩 ③）跌破 MA60 次日開盤賣
  B13 營量 v1 並列（主窗 resultsYfMix13）與持股重疊；Q1～Q4 兩兩 Spearman（主窗每個換股日橫斷面、取平均）
輸出 backtest/resultsQual/
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchMomX as MX            # ⭐ 換股簿、世界載入（本線 5290e58851）
from backtest import research13 as R13
from backtest import research34 as R34
from backtest import p4_features as P4F
D, TR, UG, H2 = MX.D, MX.TR, MX.UG, MX.H2

OUT = "backtest/resultsQual"
FIN_SHA = "a2dadbca4ad165fc31f76edf67be34ee8ee7bc38"
FD = os.path.expanduser(f"~/msdata/{FIN_SHA}/data")
A2TAG = "季財報可用日 A2 暫定（有 t57sb01 時戳用時戳；其餘法定期限＋5 個交易日緩衝）；A0 落地後重跑定案"
QS = ("Q1", "Q2", "Q3", "Q4"); QN = {"Q1": "ROE", "Q2": "營業利益÷資產（非毛利）", "Q3": "ROA", "Q4": "研發強度"}
FREQS = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7)}; NS = (10, 20)
FIN_NAMES = {"金融保險業", "金融業", "金融保險"}
MAINW = {"data": H2.H2D, "panel": "backtest/resultsp9_engine/panel_ext.csv.gz", "elig": "eligible", "w": ("2017-03-02", "2026-08-24"),
         "segs": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}}
EA = {"data": os.path.expanduser("~/earlydata/3edc0e2206/main/data"), "panel": os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz"),
      "elig": "eligible", "w": ("2014-06-01", "2014-12-31"), "segs": {"早年甲": ("2014-06-01", "2014-12-31")}}
EB = {"data": H2.H2D, "panel": "backtest/resultsp9_engine/panel_ext.csv.gz", "elig": "eligible", "w": ("2015-08-01", "2016-12-30"),
      "segs": {"早年乙": ("2015-08-01", "2016-12-30")}, "twse_only": True, "rev_extra": os.path.expanduser("~/earlydata/3edc0e2206/main/data")}


# ═════════════ 財報 ═════════════
def load_fin(log):
    fs = sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv")))
    cols = ["stock_id", "period", "industry", "rev_ytd", "opi_ytd", "ni_ytd", "nip_ytd", "assets", "equity_parent", "equity_total", "rd_ytd"]
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=cols) for f in fs], ignore_index=True)
    F = F.drop_duplicates(["stock_id", "period"], keep="last")
    F["y"] = F["period"].str[:4].astype(int); F["q"] = F["period"].str[-1].astype(int)
    K = {(s, y, q): r for s, y, q, r in zip(F["stock_id"], F["y"], F["q"], F.to_dict("records"))}
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce")
    fd = fd.dropna(subset=["d"]).groupby(["stock_id", "year", "season"])["d"].min().to_dict()

    def ttm(s, y, q, col):
        cur = K.get((s, y, q), {}).get(col, np.nan)
        if q == 4:
            return float(cur)
        fy = K.get((s, y - 1, 4), {}).get(col, np.nan); ly = K.get((s, y - 1, q), {}).get(col, np.nan)
        return float(fy + cur - ly) if np.isfinite(fy) and np.isfinite(cur) and np.isfinite(ly) else np.nan

    def pq(y, q):
        return (y, q - 1) if q > 1 else (y - 1, 4)
    rows = []
    for (s, y, q), r in K.items():
        py, pqq = pq(y, q); prv = K.get((s, py, pqq), {})
        nip, ni, opi, rev, rd = (ttm(s, y, q, c) for c in ("nip_ytd", "ni_ytd", "opi_ytd", "rev_ytd", "rd_ytd"))
        ep = (r["equity_parent"], prv.get("equity_parent", np.nan)); et = (r["equity_total"], prv.get("equity_total", np.nan))
        at = (r["assets"], prv.get("assets", np.nan))

        def avg2(v):
            return (v[0] + v[1]) / 2 if np.isfinite(v[0]) and np.isfinite(v[1]) else np.nan
        if np.isfinite(nip) and np.isfinite(avg2(ep)):
            q1, q1src = (nip / avg2(ep) if avg2(ep) > 0 else np.nan), "parent"
        else:
            q1, q1src = (ni / avg2(et) if np.isfinite(ni) and np.isfinite(avg2(et)) and avg2(et) > 0 else np.nan), "total"
        q2 = opi / r["assets"] if np.isfinite(opi) and np.isfinite(r["assets"]) and r["assets"] > 0 else np.nan
        q3 = ni / avg2(at) if np.isfinite(ni) and np.isfinite(avg2(at)) and avg2(at) > 0 else np.nan
        q4 = rd / rev if np.isfinite(rd) and np.isfinite(rev) and rev > 0 else np.nan
        ts = fd.get((s, y, q))
        rows.append({"sid": s, "y": y, "q": q, "Q1": q1, "Q1src": q1src, "Q2": q2, "Q3": q3, "Q4": q4, "ts": ts, "industry_tpl": r["industry"]})
    Q = pd.DataFrame(rows).sort_values(["sid", "y", "q"]).reset_index(drop=True)
    log(f"[財報] fin_hist {FIN_SHA[:10]}（{len(fs)} 季檔、{len(F):,} 列）｜有時戳的季 {int(Q['ts'].notna().sum()):,}／{len(Q):,}｜"
        f"Q1 母公司版 {int((Q['Q1src'] == 'parent').sum()):,}、總額版 {int(((Q['Q1src'] == 'total') & Q['Q1'].notna()).sum()):,}")
    return Q


def avail_pos(Q, cal):
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
    pos = []; src = []
    for y, q, ts in zip(Q["y"], Q["q"], Q["ts"]):
        if ts is not None and not pd.isna(ts):
            pos.append(int(cal.searchsorted(pd.Timestamp(ts), side="right"))); src.append("ts")
        else:
            d = pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, *dl[q])
            pos.append(int(cal.searchsorted(d, side="right")) + 5); src.append("dl")
    return np.array(pos), np.array(src)


def q_at(Q, pos, e):
    """每檔在 e 可用的最新一季 ⇒ {Qk: {sid: v}}、來源計數。"""
    m = pos <= e
    sub = Q[m]
    last = sub.groupby("sid").tail(1)
    out = {k: {s: v for s, v in zip(last["sid"], last[k]) if np.isfinite(v)} for k in QS}
    return out


# ═════════════ 世界 ═════════════
def world(W, procs, log, Q):
    Wd = MX.load_world(W, procs, log)
    cal = Wd["cal"]
    ind = pd.read_csv(os.path.join(W["data"], "meta", "industry.csv"), dtype=str)
    fin = set(ind.loc[ind["industry_name"].isin(FIN_NAMES), "stock_id"])
    stocks = pd.read_csv(os.path.join(W["data"], "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
    if W.get("twse_only"):
        for e in Wd["reb"]:
            Wd["reb"][e] = [s for s in Wd["reb"][e] if stocks.get(s) == "twse"]
    pos, src = avail_pos(Q, cal)
    D.DATA = W["data"]
    if W.get("rev_extra"):                                                   # B10b：主快照月營收 2015-01 起 ⇒ 24 月新高要接早年版面的月營收（原始值、不涉還原）
        fs = sorted(glob.glob(os.path.join(W["rev_extra"], "mops", "revenue_hist", "*.csv"))) + sorted(glob.glob(os.path.join(W["data"], "mops", "revenue_hist", "*.csv")))
        df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
        df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
        rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    else:
        rev, _, _ = R34.load_revenue()
    rf = P4F.rev_hi24_flags(rev, cal)
    # 成交金額相對放大（量測日 e−1）
    amt = {}
    for s in Wd["sids"]:
        st = D.load_stock(s, stocks.get(s, "twse"), cal)
        amt[s] = st.df["amount"].to_numpy(float) if st is not None else None
    RB = {}
    for e in Wd["pre"] + Wd["rebs"]:
        qa = q_at(Q, pos, e)
        el = [s for s in Wd["reb"][e] if s not in fin]
        row = rf.iloc[e] if e < len(rf) else None
        pool = set(row.index[row.to_numpy() == 100]) if row is not None else set()
        rv = {}
        for s in el:
            if s in pool and amt.get(s) is not None:
                v = Wd["P"][s]["valid"]; m_ = e - 1
                if not v[m_]:
                    continue
                b = np.flatnonzero(v[:m_ + 1])
                if len(b) < 61:
                    continue
                med = float(np.nanmedian(amt[s][b[-61:-1]])); a_ = amt[s][m_]
                if med > 0 and np.isfinite(a_):
                    rv[s] = a_ / med
        RB[e] = {"el": el, "pool": [s for s in el if s in pool], "Q": {k: {s: qa[k][s] for s in el if s in qa[k]} for k in QS},
                 "Qall": {k: {s: qa[k][s] for s in Wd["reb"][e] if s in qa[k]} for k in QS}, "relvol": rv}
    Wd["RB"] = RB; Wd["fin"] = fin
    log(f"[世界] {W['data']}｜財報可用日 時戳 {int((src == 'ts').sum()):,}／期限＋5 {int((src == 'dl').sum()):,}｜金融保險 {len(fin)}｜"
        f"乙族池中位 {np.median([len(RB[e]['pool']) for e in Wd['rebs']]):.0f}")
    return Wd


def topn(d, N):
    return [s for s, _ in sorted(d.items(), key=lambda t: (-t[1], t[0]))[:N]]


def select(Wd, fam, k, fq, N, with_fin=False):
    months = FREQS[fq]
    sel = {}; short = 0; nreb = 0
    for e in Wd["rebs"]:
        if months is not None and Wd["cal"][e].month not in months:
            continue
        R = Wd["RB"][e]; nreb += 1
        if fam == "甲":
            d = R["Qall" if with_fin else "Q"][k]
        else:
            base = R["relvol"] if k == "量" else R["Q"][k]
            d = {s: base[s] for s in R["pool"] if s in base}
            short += int(len(d) < N)
        sel[e] = topn(d, N)
    return sel, (short / nreb if nreb else None)


def stats(Wd, res, a, b, N, sel):
    eq = res["eq"]
    c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
    rs = [e for e in sorted(sel) if a <= e <= b]
    tv = [res["buys"][e] / N for e in rs[1:] if e in res["buys"]]
    yrs = (b - a + 1) / 245
    cy = float(sum(res["costd"][t] / eq[t - 1] for t in range(a, b + 1) if res["costd"][t] > 0) / yrs)
    return {"年化": float(c), "回落": float(m), "比值": float(c) / abs(float(m)), "換手": float(np.mean(tv)) if tv else float("nan"), "成本／年": cy,
            "平均持股": float(np.mean(res["npos"][a:b + 1])), "現金比例": float(np.nanmean(res["cashf"][a:b + 1]))}


def chain(parts):
    """[(eq, a, b)] ⇒ 串成一條（各段以段首為 1、接續前段末值）。"""
    out = []; lvl = 1.0
    for eq, a, b in parts:
        seg = eq[a:b + 1] / eq[a] * lvl
        out.append(seg); lvl = seg[-1]
    return np.concatenate(out)


def cstats(arr):
    c, m = R13.window_stats(arr, 0, len(arr), 0, len(arr))
    return float(c), float(m)


LORD = {"合格": 0, "另列": 1, "不合格": 2}


def _fake(args):
    fam, k, fq, N, r, wn = args
    Wd = _G[wn]; months = FREQS[fq]
    rng = np.random.default_rng([20260928, {"甲": 1, "乙": 2}[fam], r])
    sel = {}
    for e in Wd["rebs"]:
        if months is not None and Wd["cal"][e].month not in months:
            continue
        R = Wd["RB"][e]
        pool = sorted(R["Q"][k]) if fam == "甲" else sorted(R["pool"])
        sel[e] = list(rng.choice(pool, size=min(N, len(pool)), replace=False)) if pool else []
    res = MX.sim_book(sel, Wd, N)
    return res["eq"]


_G: dict = {}


def fake_job(args):
    fam, k, fq, N, r = args
    out = {"族": fam, "r": r}
    eqm = _fake((fam, k, fq, N, r, "M"))
    for nm, (a, b) in _G["SEG"]["M"].items():
        c, m = R13.window_stats(eqm, 0, len(eqm), a, b + 1); out[f"{nm}_年化"] = float(c); out[f"{nm}_回落"] = float(m)
    ea = _fake((fam, k, fq, N, r, "A")); eb = _fake((fam, k, fq, N, r, "B"))
    arr = chain([(ea, *_G["SEG"]["A"]), (eb, *_G["SEG"]["B"])])
    c, m = cstats(arr); out["早年_年化"] = c; out["早年_回落"] = m
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchQual（PREREG品質 seq1）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{A2TAG} =====")
    S = {"登錄": "PREREG品質 seq1 sha 24e7fb594193b9c0；裁定 seq256 §二 4、seq259 §四", "財報": f"fin_hist {FIN_SHA}（~/msdata，唯讀）", "可用日": A2TAG, "閘": {}}
    Q = load_fin(log)
    Wm = world(MAINW, a.procs, log, Q)
    c_, m_ = R13.window_stats(Wm["bench"], 0, Wm["n"], Wm["w0"], Wm["w1"] + 1)
    S["閘"]["0050 主窗錨逐位元"] = repr(float(c_)) == repr(MX.ANCHOR[0]) and repr(float(m_)) == repr(MX.ANCHOR[1])
    if not S["閘"]["0050 主窗錨逐位元"]:
        raise SystemExit("⛔ 0050 錨")
    Wa = world(EA, a.procs, log, Q)
    Wb = world(EB, a.procs, log, Q)
    D.DATA = H2.H2D
    SEGm = {nm: (max(int(Wm["cal"].searchsorted(pd.Timestamp(x))), Wm["w0"]), min(int(Wm["cal"].searchsorted(pd.Timestamp(y), side="right") - 1), Wm["w1"]))
            for nm, (x, y) in MAINW["segs"].items()}
    SA, SB = (Wa["w0"], Wa["w1"]), (Wb["w0"], Wb["w1"])
    Z = {nm: R13.window_stats(Wm["bench"], 0, Wm["n"], x, y + 1) for nm, (x, y) in SEGm.items()}
    Z["早年"] = cstats(chain([(Wa["bench"], *SA), (Wb["bench"], *SB)]))
    S["0050"] = {nm: {"年化": float(v[0]), "回落": float(v[1]), "比值": float(v[0]) / abs(float(v[1]))} for nm, v in Z.items()}
    S["早年段實際窗"] = {"甲（早年版面）": [str(Wa["cal"][SA[0]].date()), str(Wa["cal"][SA[1]].date())], "乙（主快照、只上市）": [str(Wb["cal"][SB[0]].date()), str(Wb["cal"][SB[1]].date())]}
    log(f"[0050] {S['0050']}｜早年窗 {S['早年段實際窗']}")
    rows = []; EQ = {}; SEL = {}
    for fam in ("甲", "乙"):
        ks = QS + (("量",) if fam == "乙" else ())
        for k in ks:
            for fq in FREQS:
                for N in NS:
                    key = f"{fam}_{k}_{fq}_N{N}"
                    selm, sh = select(Wm, fam, k, fq, N); res = MX.sim_book(selm, Wm, N)
                    sa, sha = select(Wa, fam, k, fq, N); ra = MX.sim_book(sa, Wa, N)
                    sb, shb = select(Wb, fam, k, fq, N); rb = MX.sim_book(sb, Wb, N)
                    EQ[key] = (res["eq"], ra["eq"], rb["eq"]); SEL[key] = (selm, sa, sb)
                    base = {"族": fam, "量測": k, "格": key, "頻率": fq, "N": N, "判定格": k != "量"}
                    for nm, (x, y) in SEGm.items():
                        st = stats(Wm, res, x, y, N, selm)
                        st["標籤"] = MX.label(st["年化"], st["回落"], *Z[nm])
                        rows.append({**base, "段": nm, **st, "湊不滿N的換股比例": sh})
                    arr = chain([(ra["eq"], *SA), (rb["eq"], *SB)]); c, m = cstats(arr)
                    rows.append({**base, "段": "早年", "年化": c, "回落": m, "比值": c / abs(m), "標籤": MX.label(c, m, *Z["早年"]),
                                 "平均持股": float(np.mean(np.r_[ra["npos"][SA[0]:SA[1] + 1], rb["npos"][SB[0]:SB[1] + 1]])), "湊不滿N的換股比例": shb})
            log(f"  [{fam}] {k} 完成")
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    # ── 挑格
    PK = {}
    for fam in ("甲", "乙"):
        ex = T[(T["族"] == fam) & (T["段"] == "探索") & T["判定格"]].copy()
        ex["退化"] = (ex["平均持股"] < ex["N"] / 2) | (ex["現金比例"] > 0.30)
        pool = ex[~ex["退化"]]
        c0, m0 = Z["探索"]; ps = pool[(pool["年化"] > c0) & (pool["比值"] >= c0 / abs(m0))]
        pp = (ps if len(ps) else pool).copy()
        pp["_f"] = pp["頻率"].map({"月": 0, "季": 1, "半年": 2}); pp["_q"] = pp["量測"].map({k: i for i, k in enumerate(QS)})
        best = pp.sort_values(["比值", "年化", "_f", "N", "_q"], ascending=[False, False, True, True, True]).iloc[0]
        key = best["格"]
        cf = T[(T["格"] == key) & (T["段"] == "確認")].iloc[0]; ea = T[(T["格"] == key) & (T["段"] == "早年")].iloc[0]
        if cf["標籤"] == "合格" and ea["標籤"] == "合格":
            fin = "合格"
        elif cf["標籤"] == "合格":
            fin = "只在一段合格"
        else:
            fin = f"確認 {cf['標籤']}／早年 {ea['標籤']}"
        PK[fam] = {"格": key, "量測": best["量測"], "頻率": best["頻率"], "N": int(best["N"]), "探索過判準格數": int(len(ps)), "退化排除格數": int(ex["退化"].sum()),
                   "探索": {k: float(best[k]) for k in ("年化", "回落", "比值")},
                   "確認": {k: (cf[k] if k == "標籤" else float(cf[k])) for k in ("年化", "回落", "比值", "換手", "成本／年", "平均持股", "標籤")},
                   "早年": {k: (ea[k] if k == "標籤" else float(ea[k])) for k in ("年化", "回落", "比值", "平均持股", "標籤")}, "件標籤": fin}
        if fam == "乙":
            vk = key.replace(f"_{best['量測']}_", "_量_")
            v1 = T[(T["格"] == vk) & (T["段"] == "確認")].iloc[0]; v2 = T[(T["格"] == vk) & (T["段"] == "早年")].iloc[0]
            PK[fam]["同池用量挑（營量 v1 挑法）"] = {"格": vk, "確認": {"年化": float(v1["年化"]), "回落": float(v1["回落"]), "標籤": v1["標籤"]},
                                           "早年": {"年化": float(v2["年化"]), "回落": float(v2["回落"]), "標籤": v2["標籤"]},
                                           "確認 品質 − 量（點）": float((cf["年化"] - v1["年化"]) * 100)}
            PK[fam]["池"] = {"乙族池中位（主窗換股日）": float(np.median([len(Wm["RB"][e]["pool"]) for e in Wm["rebs"]])),
                            "湊不滿 N 的換股比例（主窗）": float(cf["湊不滿N的換股比例"])}
        log(f"[挑格 {fam}] {key}｜探索 {best['年化']:+.2%}／{best['回落']:+.2%}（{best['比值']:.3f}）｜確認 {cf['年化']:+.2%}／{cf['回落']:+.2%} {cf['標籤']}｜"
            f"早年 {ea['年化']:+.2%}／{ea['回落']:+.2%} {ea['標籤']} ⇒ {fin}")
    S["挑格"] = PK
    # ── 假訊號
    _G.update(M=Wm, A=Wa, B=Wb, SEG={"M": SEGm, "A": SA, "B": SB})
    FK = []
    for fam in ("甲", "乙"):
        pk = PK[fam]
        with Pool(a.procs) as pool:
            FK += pool.map(fake_job, [(fam, pk["量測"], pk["頻率"], pk["N"], r) for r in range(a.reps)], chunksize=20)
        log(f"[假訊號 {fam}] {a.reps} 次")
    FKd = pd.DataFrame(FK); FKd.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
    for fam in ("甲", "乙"):
        f = FKd[FKd["族"] == fam]
        for nm in ("確認", "早年"):
            x = f[f"{nm}_年化"].to_numpy(float)
            PK[fam][f"假訊號_{nm}"] = {"p（隨機年化 ≥ 本格）": float(np.mean(x >= PK[fam][nm]["年化"])), "隨機年化中位": float(np.median(x))}
    # ── 營量 v1、重疊、相關
    z13 = np.load("backtest/resultsYfMix13/eq_main.npz"); t0, t1 = Wm["w0"], Wm["w1"]
    b13 = np.ones(Wm["n"]); b13[t0:t1 + 1] = z13["b13"]; b13[t1 + 1:] = z13["b13"][-1]
    S["營量v1"] = {nm: dict(zip(("年化", "回落"), map(float, R13.window_stats(b13, 0, Wm["n"], x, y + 1)))) for nm, (x, y) in SEGm.items()}
    pos13 = pd.read_csv("backtest/resultsYfMix13/positions.csv.gz", dtype={"sid": str}); pos13 = pos13[pos13["cell"] == 13]
    H13 = [set() for _ in range(Wm["n"])]
    for s, tb, ts in zip(pos13["sid"], pos13["t_buy"], pos13["t_sell"]):
        ts = Wm["n"] if ts < 0 else ts
        for t in range(max(tb, t0), min(ts, t1 + 1)):
            H13[t].add(s)
    OV = {}
    for fam in ("甲", "乙"):
        for k in QS + (("量",) if fam == "乙" else ()):
            key = f"{fam}_{k}_{PK[fam]['頻率']}_N{PK[fam]['N']}"
            res = MX.sim_book(SEL[key][0], Wm, PK[fam]["N"])
            cur = set(); ov = []
            x, y = SEGm["確認"]
            for t in range(t0, t1 + 1):
                if t in res["hold"]:
                    cur = set(res["hold"][t])
                if x <= t <= y and cur:
                    ov.append(len(cur & H13[t]) / len(cur))
            OV[key] = float(np.mean(ov)) if ov else None
    S["與營量v1持股重疊（確認段，挑中頻率與檔數下各量測）"] = OV
    cor = {f"{i}×{j}": [] for ii, i in enumerate(QS) for j in QS[ii + 1:]}
    for e in Wm["rebs"]:
        qd = pd.DataFrame(Wm["RB"][e]["Q"])
        for ii, i in enumerate(QS):
            for j in QS[ii + 1:]:
                d_ = qd[[i, j]].dropna()
                if len(d_) >= 30:
                    cor[f"{i}×{j}"].append(d_[i].rank().corr(d_[j].rank()))
    S["Q 兩兩 Spearman（主窗換股日平均）"] = {k: float(np.mean(v)) for k, v in cor.items()}
    S["Q4 研發可排名占甲族母體（主窗換股日平均）"] = float(np.mean([len(Wm["RB"][e]["Q"]["Q4"]) / max(1, len(Wm["RB"][e]["el"])) for e in Wm["rebs"]]))
    # ── 描述：全賣全買、含金融、出場敏感度
    for fam in ("甲", "乙"):
        pk = PK[fam]; k, fq, N = pk["量測"], pk["頻率"], pk["N"]
        dsc = {}
        for vn, kw, wf in (("全賣全買", {"mode": "all"}, False), ("含金融（甲族）", {}, True)):
            if wf and fam == "乙":
                continue
            sm, _ = select(Wm, fam, k, fq, N, with_fin=wf); rm = MX.sim_book(sm, Wm, N, **kw)
            sa_, _ = select(Wa, fam, k, fq, N, with_fin=wf); ra_ = MX.sim_book(sa_, Wa, N, **kw)
            sb_, _ = select(Wb, fam, k, fq, N, with_fin=wf); rb_ = MX.sim_book(sb_, Wb, N, **kw)
            c, m = R13.window_stats(rm["eq"], 0, Wm["n"], SEGm["確認"][0], SEGm["確認"][1] + 1)
            ce, me_ = cstats(chain([(ra_["eq"], *SA), (rb_["eq"], *SB)]))
            dsc[vn] = {"確認": [float(c), float(m), MX.label(float(c), float(m), *Z["確認"])], "早年": [ce, me_, MX.label(ce, me_, *Z["早年"])]}
        if pk["確認"]["標籤"] in ("合格", "另列"):
            sm, _ = select(Wm, fam, k, fq, N); sa_, _ = select(Wa, fam, k, fq, N); sb_, _ = select(Wb, fam, k, fq, N)
            rm = MX.sim_book(sm, Wm, N, ma_stop=MX.ma_table(Wm, sorted({s for v in sm.values() for s in v})))
            ra_ = MX.sim_book(sa_, Wa, N, ma_stop=MX.ma_table(Wa, sorted({s for v in sa_.values() for s in v})))
            rb_ = MX.sim_book(sb_, Wb, N, ma_stop=MX.ma_table(Wb, sorted({s for v in sb_.values() for s in v})))
            c, m = R13.window_stats(rm["eq"], 0, Wm["n"], SEGm["確認"][0], SEGm["確認"][1] + 1)
            ce, me_ = cstats(chain([(ra_["eq"], *SA), (rb_["eq"], *SB)]))
            dsc["出場敏感度：跌破 MA60 次日開盤賣（新規矩 ③）"] = {"確認": [float(c), float(m), MX.label(float(c), float(m), *Z["確認"])], "早年": [ce, me_, MX.label(ce, me_, *Z["早年"])]}
        pk["描述"] = dsc
    rows = []
    for fam in PK:
        for wi, wn in enumerate(("主", "早年甲", "早年乙")):
            for e, s_ in SEL[PK[fam]["格"]][wi].items():
                Wd = (Wm, Wa, Wb)[wi]
                for i, s in enumerate(s_):
                    rows.append({"族": fam, "世界": wn, "換股日": str(Wd["cal"][e].date()), "名次": i + 1, "sid": s})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""產業營收加速 seq2（台股策略線登錄 sha 728b0293c996fd50）甲 現況快照（描述、⛔ 不計 N、⛔ 不給買賣建議）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRev_snapshot [--check | --page]

═══ 讀法（寫死於 2026-10-02 01:24（台北），在算任何數字之前；乙、丙等裁定發號，本檔不做）═══
 S0 資料：tw-stock-data 最新 main（origin/main，執行時取 sha；git archive meta、mops/revenue_hist、stocks、adj、stocks_per 到 ~/h2data/indrev_<sha12>/data，唯讀）；
    早年營收 ＝ surge_feat_daily.EARLY（~/earlydata/950ad26e12 的 mops/revenue_hist，2003～2014）＋ main，同 (代號, 期別) 取 main（同 list_yl13_watch／daily 的營收來源）
    價格日 ＝ main 日曆最後一天（執行當下若已有 2026-10-01 就用、否則照實標實際日期）
 S1 產業別（登錄 §一）：main data/meta/industry.csv（上市＋上櫃）的 industry_name，名稱相同合併；⚠ 只有現值 ⇒ 頁首標「產業別後見（現值套回）」
    排除：金融保險、其他、存託憑證（industry_code 91／名稱含 -DR）、ETF（stocks.csv kind ＝ etf）；只留 stocks.csv kind ＝ stock；⛔ 不用題材名稱
    名稱空白的類別（上櫃代碼 32、33）不猜名稱 ⇒ 以「上櫃代碼 NN（名稱空白）」自成一類，照實標
 S2 產業營收（同公司基準）：月 m 的產業營收年增 ＝ Σ_{c∈C_m} rev[c,m] ÷ Σ_{c∈C_m} rev[c,m−12] − 1，
    C_m ＝ 該產業內 rev[c,m] 與 rev[c,m−12] 都有值且 ＞ 0 的公司（rev ＝ 月營收「當月營收」，m−12 取同一份 revenue_hist 的 m−12 期，⛔ 不用「去年當月營收」欄）
    多月合計：近 k 月合計年增 ＝ Σ_m Σ_{c∈C_m} rev[c,m] ÷ Σ_m Σ_{c∈C_m} rev[c,m−12] − 1（每個月各自的同公司集合）
    公司數 ＝ |C_M|（M ＝ 最新可用月）；公司數 ＜ 5 ⇒ 該產業不排名（照列、標「不排名」）
    可用日：M 月營收 ⇒ M＋1 月 10 日之後第一個交易日（research34.rebalance_dates，pub_day 10）；最新可用月 ＝ 可用日 ≤ 價格日的最後一個月（預期 2026-08）
 S3 加速 A（登錄 §一）：A1 ＝ 近 3 月合計年增（M−2～M）；A2 ＝ A1 − 近 12 月合計年增（M−11～M）；A3 ＝ A1(M) − A1(M−3)（M−5～M−3 的同一數字）
    排名：三個 A 各自由大到小，只排公司數 ≥ 5 的產業；同值依產業名稱
    產業營收規模 ＝ 最新月 Σ_{c∈C_M} rev[c,M] 與近 12 月合計（億元；營收原單位千元）
 S4 前 5 名產業的成員股（產業內全部 kind＝stock 成員，依市值大到小）：
    市值 ＝ 價格日未還原收盤 × shares（stocks/<代號>.csv 同列；億元；當天無成交 ⇒ 取最後一筆有收盤的列並標日期）
    近 3 月營收年增 ＝ Σ_{M−2..M} rev ÷ Σ rev[m−12] − 1（6 個值都要有且 ＞ 0，否則空白）
    營收創 24 月新高 ＝ rev[M] ≥ 前 24 期最高（24 期都要有值；同 list_yl13_watch 的 rev_hi24 口徑）
    近 250 日報酬 ＝ 還原收盤（data.load_stock，ffill）c[T] ÷ c[T−250] − 1；距 250 日低點 ＝ c[T] ÷ min(c[T−249..T]) − 1（T ＝ 價格日；日曆位置）
    本益比 ＝ main data/stocks_per 該檔價格日（或之前最後一列）的 per，附 per 那列的日期與 fs_quarter（財報期，民國年／季）；空白 ⇒「—」
 S5 查核（--check）：抽 2 個有排名的產業（random_state 20261002），直接逐檔讀 revenue_hist 原始 csv、逐公司迴圈重算 A1、A2、A3、公司數 ⇒ 差 ＞ 1e−12 才算不同
輸出 backtest/resultsIndRev/snapshot/：rank_industry.csv、members_top5.csv、industry_monthly.csv、meta.json、check.json、產業營收加速現況快照.html
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research34 as R34

TIME = "2026-10-02 01:24（台北）"
OUT = "backtest/resultsIndRev/snapshot"
EARLY = os.path.expanduser("~/earlydata/950ad26e12/main/data")
PARTS = ["data/meta", "data/mops/revenue_hist", "data/stocks", "data/adj", "data/stocks_per"]
EXCL = {"金融保險", "其他", "存託憑證", "ETF"}
AS = ("A1", "A2", "A3")
ANAME = {"A1": "A1 近 3 月年增（水準）", "A2": "A2 近 3 月 − 近 12 月（短長差）", "A3": "A3 近 3 月 − 三個月前（動能）"}
TOPK = 5


def ensure_data(log):
    sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.expanduser(f"~/h2data/indrev_{sha[:12]}")
    if not os.path.isdir(os.path.join(root, "data", "stocks_per")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        log(f"[資料] git archive {sha[:10]} ⇒ {root}")
    return sha, os.path.join(root, "data")


def load_rev(DATA):
    fs = sorted(glob.glob(os.path.join(EARLY, "mops", "revenue_hist", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    return df.pivot(index="period", columns="stock_id", values="rev").sort_index()


def per_of(m):
    y, mm = int(m[:4]), int(m[5:])
    return lambda k: f"{y + (mm - 1 + k) // 12:04d}-{(mm - 1 + k) % 12 + 1:02d}"


def universe(DATA):
    ind = pd.read_csv(os.path.join(DATA, "meta", "industry.csv"), dtype=str).fillna("")
    stk = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    kind = stk.drop_duplicates("stock_id", keep="last").set_index("stock_id")["kind"]
    ind["kind"] = ind["stock_id"].map(kind).fillna("（stocks.csv 無）")
    ind["產業"] = [n if n else (f"存託憑證" if c == "91" else f"{'上櫃' if m == 'tpex' else '上市'}代碼 {c}（名稱空白）")
                 for n, c, m in zip(ind["industry_name"], ind["industry_code"], ind["market"])]
    ind.loc[ind["name"].str.contains("-DR", regex=False), "產業"] = "存託憑證"
    cnt = {"industry.csv 列": int(len(ind)), "kind 分佈": ind["kind"].value_counts().to_dict()}
    keep = ind[(ind["kind"] == "stock") & (~ind["產業"].isin(EXCL))].drop_duplicates("stock_id", keep="last").copy()
    cnt["排除後檔數"] = int(len(keep)); cnt["排除的產業（檔數）"] = ind[ind["產業"].isin(EXCL)]["產業"].value_counts().to_dict()
    cnt["非 stock 而剔除（產業未排除者）"] = int(((ind["kind"] != "stock") & (~ind["產業"].isin(EXCL))).sum())
    return keep.reset_index(drop=True), cnt


def ind_yoy(rev, sids, months):
    """⇒ (Σ本期, Σ去年同期, 各月公司數 list)，同公司基準、每月各自集合。"""
    num = den = 0.0; ns = []
    cols = [s for s in sids if s in rev.columns]
    for m in months:
        ly = per_of(m)(-12)
        if m not in rev.index or ly not in rev.index:
            ns.append(0); continue
        a = rev.loc[m, cols].to_numpy(float); b = rev.loc[ly, cols].to_numpy(float)
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0) & (b > 0)
        num += a[ok].sum(); den += b[ok].sum(); ns.append(int(ok.sum()))
    return num, den, ns


def compute_ind(rev, members, M):
    P = per_of(M); last3 = [P(-2), P(-1), P(0)]; last12 = [P(-k) for k in range(11, -1, -1)]; prev3 = [P(-5), P(-4), P(-3)]
    rows = []; mon = []
    for name, g in members.groupby("產業"):
        sids = g["stock_id"].tolist()
        n3, d3, c3 = ind_yoy(rev, sids, last3); n12, d12, c12 = ind_yoy(rev, sids, last12); np3, dp3, cp3 = ind_yoy(rev, sids, prev3)
        y3 = n3 / d3 - 1 if d3 > 0 else np.nan; y12 = n12 / d12 - 1 if d12 > 0 else np.nan; yp3 = np3 / dp3 - 1 if dp3 > 0 else np.nan
        rows.append({"產業": name, "成員檔數": len(sids), "上市": int((g["market"] == "twse").sum()), "上櫃": int((g["market"] == "tpex").sum()),
                     "公司數": c3[-1], "近3月各月公司數": "/".join(map(str, c3)), "最新月營收（億）": np.nan, "近12月營收（億）": n12 / 1e5,
                     "近3月年增": y3, "近12月年增": y12, "三個月前的近3月年增": yp3, "A1": y3, "A2": y3 - y12, "A3": y3 - yp3})
        nM, _, _ = ind_yoy(rev, sids, [M]); rows[-1]["最新月營收（億）"] = nM / 1e5
        for m in last12:
            a, b, c = ind_yoy(rev, sids, [m]); mon.append({"產業": name, "月": m, "公司數": c[0], "營收（億）": a / 1e5, "去年同月（億）": b / 1e5, "年增": a / b - 1 if b > 0 else np.nan})
    T = pd.DataFrame(rows); ok = T["公司數"] >= 5
    for a in AS:
        T[f"{a} 名次"] = np.nan
        sub = T[ok].sort_values([a, "產業"], ascending=[False, True])
        T.loc[sub.index, f"{a} 名次"] = np.arange(1, len(sub) + 1)
    T["排名"] = np.where(ok, "排名", "不排名（公司數＜5）")
    return T, pd.DataFrame(mon)


def stock_rows(DATA, rev, cal, T_pos, sids, mk, M):
    P = per_of(M); n = len(cal)
    out = []
    for s in sids:
        r = {"代號": s}
        raw = pd.read_csv(os.path.join(DATA, "stocks", f"{s}.csv"), dtype={"stock_id": str, "date": str}, usecols=["date", "name", "close", "shares"])
        raw["close"] = pd.to_numeric(raw["close"], errors="coerce"); raw["shares"] = pd.to_numeric(raw["shares"], errors="coerce")
        raw = raw[raw["date"] <= str(cal[T_pos].date())]
        x = raw.dropna(subset=["close"]).tail(1)
        if len(x):
            x = x.iloc[0]; r["名稱"] = x["name"]; r["收盤"] = float(x["close"]); r["收盤日"] = x["date"]
            r["市值（億）"] = float(x["close"]) * float(x["shares"]) / 1e8 if np.isfinite(x["shares"]) else np.nan
        st = D.load_stock(s, mk[s], cal)
        if st is not None:
            c = st.df["close"].ffill().to_numpy(float)
            if T_pos >= 250 and np.isfinite(c[T_pos - 250]):
                r["近250日報酬"] = c[T_pos] / c[T_pos - 250] - 1
            w = c[max(0, T_pos - 249):T_pos + 1]
            if np.isfinite(w).sum() >= 1:
                r["距250日低點"] = c[T_pos] / np.nanmin(w) - 1
        if s in rev.columns:
            col = rev[s]
            a = np.array([col.get(P(-k), np.nan) for k in (2, 1, 0)], float); b = np.array([col.get(P(-k - 12), np.nan) for k in (2, 1, 0)], float)
            if np.isfinite(a).all() and np.isfinite(b).all() and (a > 0).all() and (b > 0).all():
                r["近3月營收年增"] = a.sum() / b.sum() - 1
            prev = np.array([col.get(P(-k), np.nan) for k in range(24, 0, -1)], float); cur = col.get(M, np.nan)
            r["最新月營收（億）"] = cur / 1e5 if np.isfinite(cur) else np.nan
            r["營收創24月新高"] = ("是" if cur >= prev.max() else "否") if (np.isfinite(prev).all() and np.isfinite(cur)) else "—（不足 24 期或缺值）"
        else:
            r["營收創24月新高"] = "—（無營收）"
        pp = os.path.join(DATA, "stocks_per", f"{s}.csv")
        if os.path.exists(pp):
            pe = pd.read_csv(pp, dtype=str); pe = pe[pe["date"] <= str(cal[T_pos].date())].tail(1)
            if len(pe):
                pe = pe.iloc[0]; v = pd.to_numeric(pe["per"], errors="coerce")
                r["本益比"] = float(v) if np.isfinite(v) and v > 0 else np.nan
                r["本益比日期"] = pe["date"]; r["財報期"] = pe.get("fs_quarter", "") if isinstance(pe.get("fs_quarter", ""), str) else ""
        out.append(r)
    return out


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    sha, DATA = ensure_data(log)
    D.DATA = DATA; cal = D.load_calendar(); T_pos = len(cal) - 1; asof = str(cal[T_pos].date())
    rev = load_rev(DATA)
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    avail = [p for p in rev.index if p in rd and rd[p][1] <= T_pos]
    M = avail[-1]
    log(f"[資料] main {sha[:10]}｜價格日 {asof}｜最新可用營收月 {M}（可用日 {cal[rd[M][1]].date()}）｜營收期 {rev.index[0]}～{rev.index[-1]}")
    mem, ucnt = universe(DATA)
    T, MON = compute_ind(rev, mem, M)
    T.sort_values("A1 名次").to_csv(os.path.join(OUT, "rank_industry.csv"), index=False, float_format="%.17g")
    MON.to_csv(os.path.join(OUT, "industry_monthly.csv"), index=False, float_format="%.8g")
    mk = dict(zip(mem["stock_id"], mem["market"]))
    rows = []
    tops = {a: T.dropna(subset=[f"{a} 名次"]).sort_values(f"{a} 名次").head(TOPK)["產業"].tolist() for a in AS}
    for ind in sorted(set(sum(tops.values(), []))):
        g = mem[mem["產業"] == ind]
        for r in stock_rows(DATA, rev, cal, T_pos, g["stock_id"].tolist(), mk, M):
            r["產業"] = ind; r["市場"] = "上市" if mk[r["代號"]] == "twse" else "上櫃"
            r["入前5"] = "、".join(f"{a} 第{int(T.loc[T['產業'] == ind, f'{a} 名次'].iloc[0])}" for a in AS if ind in tops[a])
            rows.append(r)
    MB = pd.DataFrame(rows).sort_values(["產業", "市值（億）"], ascending=[True, False])
    MB.to_csv(os.path.join(OUT, "members_top5.csv"), index=False, float_format="%.8g")
    META = {"讀法寫死": TIME, "main": sha, "價格日": asof, "價格日說明": ("已有 2026-10-01" if asof >= "2026-10-01" else f"main 最新資料日為 {asof}，尚無 2026-10-01"),
            "最新可用營收月": M, "其可用日": str(cal[rd[M][1]].date()), "母體": ucnt, "產業數": int(len(T)), "有排名產業數": int((T["公司數"] >= 5).sum()),
            "前5": tops, "前5成員檔數": int(len(MB)), "成員缺市值": int(MB["市值（億）"].isna().sum()), "成員缺本益比": int(MB["本益比"].isna().sum()) if "本益比" in MB else None,
            "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(META, ensure_ascii=False, default=str)}")


# ═════════════ 查核 ═════════════
def check(log):
    sha, DATA = ensure_data(log)
    T = pd.read_csv(os.path.join(OUT, "rank_industry.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8")); M = META["最新可用營收月"]
    mem, _ = universe(DATA)
    pick = T[T["公司數"] >= 5].sample(2, random_state=20261002)["產業"].tolist()
    # 原始 csv 逐列讀（main 優先）
    raw = {}
    need = {per_of(M)(-k) for k in range(0, 24)}                       # M−23～M（A1～A3 只用到 M−23）
    fs = [f for f in sorted(glob.glob(os.path.join(EARLY, "mops", "revenue_hist", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv")))
          if os.path.basename(f)[:7] in need]
    for f in fs:
        for _, x in pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]).iterrows():
            try:
                v = float(x["當月營收"])
            except (TypeError, ValueError):
                v = float("nan")
            raw[(x["stock_id"], x["period"])] = v

    def mshift(m, k):
        y, mm = int(m[:4]), int(m[5:]); t = y * 12 + mm - 1 + k
        return f"{t // 12:04d}-{t % 12 + 1:02d}"

    def yoy(sids, months):
        num = den = 0.0; cnt = 0
        for m in months:
            cnt = 0
            for s in sids:
                a = raw.get((s, m), float("nan")); b = raw.get((s, mshift(m, -12)), float("nan"))
                if a == a and b == b and a > 0 and b > 0:
                    num += a; den += b; cnt += 1
        return num / den - 1, cnt
    out = {}; nd = 0
    for ind in pick:
        sids = mem[mem["產業"] == ind]["stock_id"].tolist()
        a1, c = yoy(sids, [mshift(M, -2), mshift(M, -1), M]); y12, _ = yoy(sids, [mshift(M, -k) for k in range(11, -1, -1)])
        p3, _ = yoy(sids, [mshift(M, -5), mshift(M, -4), mshift(M, -3)])
        mine = {"A1": a1, "A2": a1 - y12, "A3": a1 - p3, "公司數": c}
        r = T[T["產業"] == ind].iloc[0]
        diff = {k: (float(mine[k]), float(r[k])) for k in mine}
        bad = [k for k, (x, y) in diff.items() if abs(x - y) > 1e-12 * max(1, abs(y))]
        nd += len(bad); out[ind] = {"逐公司重算／主程式": diff, "不同": bad}
    res = {"讀法寫死": TIME, "抽樣": f"有排名產業抽 2 個（random_state 20261002）：{pick}", "比對": out, "不同項數": nd, "通過": nd == 0}
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {res}")


# ═════════════ 網頁 ═════════════
def page(log):
    T = pd.read_csv(os.path.join(OUT, "rank_industry.csv")); MB = pd.read_csv(os.path.join(OUT, "members_top5.csv"), dtype={"代號": str})
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            "details{margin:.6em 0}summary{font-weight:600;cursor:pointer;padding:4px 0}.pane{display:none}.pane.on{display:block}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    N0 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:,.0f}"
    N1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:,.1f}"
    e = html.escape
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>產業營收加速現況快照</title>", f"<style>{CSS}</style></head><body><main>",
         f"<h1>產業營收加速：現況快照（營收到 {META['最新可用營收月']}，股價 {META['價格日']}）</h1>",
         "<p class='warn'>⚠ <b>產業別後見（現值套回）</b>：資料庫只有現在的產業別，過去改過類別的公司也用現在的歸類。"
         "這是描述，不計檢定數、<b>不是買賣建議</b>；只給台股線挑「四段分析」的對象用。</p>"]
    top = META["前5"]
    H.append("<div class='ok big'><b>三種加速的前 5 名產業</b><ul>" + "".join(f"<li>{ANAME[a]}：{'、'.join(e(x) for x in top[a])}</li>" for a in AS) + "</ul></div>")
    H.append(f"<p class='lead'>讀法寫死 {e(META['讀法寫死'])}。產業營收用<b>同公司基準</b>：每個月只加總「當月與去年同月都有營收」的公司再算年增；"
             f"最新月有這種公司不到 5 家的產業不排名。8 月營收的可用日是 {e(META['其可用日'])}。{e(META['價格日說明'])}。"
             + (f"查核：抽 2 個產業逐公司重算，{CK['不同項數']} 項不同。" if CK else "") + "</p>")
    H.append("<h2>一、產業排名</h2><div class='sel'>依 <select id='s1' onchange='sw()'>" + "".join(f"<option value='{a}'>{ANAME[a]}</option>" for a in AS) + "</select></div>")
    for a in AS:
        S = T.copy(); S["_k"] = S[f"{a} 名次"].fillna(1e9); S = S.sort_values(["_k", "產業"])
        H.append(f"<div class='pane' id='p{a}'><div class='wrap'><table><tr><th>名次</th><th class='l'>產業</th><th>{a}</th><th>近 3 月<br><small>年增</small></th><th>近 12 月<br><small>年增</small></th>"
                 "<th>三個月前<br><small>近 3 月年增</small></th><th>公司數</th><th>最新月營收<br><small>億</small></th><th>近 12 月營收<br><small>億</small></th></tr>")
        for _, r in S.iterrows():
            rk = "—" if not np.isfinite(r[f"{a} 名次"]) else f"{int(r[f'{a} 名次'])}"
            H.append(f"<tr><td>{rk}</td><td class='l'>{e(r['產業'])}{'' if r['公司數'] >= 5 else '<br><small>不排名</small>'}</td><td><b>{PT(r[a]) if a != 'A1' else P1(r[a])}</b></td>"
                     f"<td>{P1(r['近3月年增'])}</td><td>{P1(r['近12月年增'])}</td><td>{P1(r['三個月前的近3月年增'])}</td><td>{int(r['公司數'])}</td>"
                     f"<td>{N0(r['最新月營收（億）'])}</td><td>{N0(r['近12月營收（億）'])}</td></tr>")
        H.append("</table></div></div>")
    H.append("<h2>二、前 5 名產業的成員股</h2><p class='note'>依市值大到小；點產業名稱展開。本益比是公開資料的值，日期與財報期附在下方小字（財報期為民國年／季）。</p>")
    for ind in sorted(set(sum(top.values(), [])), key=lambda x: min(top[a].index(x) if x in top[a] else 99 for a in AS)):
        g = MB[MB["產業"] == ind]
        tag = g["入前5"].iloc[0] if len(g) else ""
        H.append(f"<details><summary>{e(ind)}（{len(g)} 檔；{e(tag)}）</summary><div class='wrap'><table><tr><th class='l'>代號 名稱</th><th>市值<br><small>億</small></th>"
                 "<th>近 3 月<br><small>營收年增</small></th><th>營收創<br><small>24 月新高</small></th><th>近 250 日<br><small>報酬</small></th><th>距 250 日<br><small>低點</small></th><th>本益比</th></tr>")
        for _, r in g.iterrows():
            pe = "—" if not np.isfinite(r.get("本益比", np.nan)) else f"{r['本益比']:.1f}"
            sm = f"<br><small>{e(str(r.get('本益比日期', '')))} {e(str(r.get('財報期', '')) if isinstance(r.get('財報期', ''), str) else '')}</small>"
            H.append(f"<tr><td class='l'>{e(str(r['代號']))} {e(str(r.get('名稱', '')))}<br><small>{e(r['市場'])}</small></td><td>{N1(r.get('市值（億）', np.nan))}</td>"
                     f"<td>{P1(r.get('近3月營收年增', np.nan))}</td><td>{e(str(r.get('營收創24月新高', '')))}</td><td>{P1(r.get('近250日報酬', np.nan))}</td>"
                     f"<td>{P1(r.get('距250日低點', np.nan))}</td><td>{pe}{sm}</td></tr>")
        H.append("</table></div></details>")
    H.append("<h2>名詞</h2><ul class='note'><li>A1 ＝ 近 3 個月合計營收年增率；A2 ＝ A1 − 近 12 個月合計年增率（正 ＝ 最近比過去一年更快）；A3 ＝ A1 − 三個月前的 A1（正 ＝ 在加速）。</li>"
             "<li>產業別：上市、上櫃官方產業別，名稱相同合併；排除金融保險、其他、存託憑證、ETF。資料裡名稱空白的上櫃類別照代碼列出、不猜名稱。</li>"
             "<li>市值 ＝ 收盤 × 股數；近 250 日報酬、距 250 日低點用還原收盤。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value;document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p'+a))}sw()</script></main></body></html>")
    open(os.path.join(OUT, "產業營收加速現況快照.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""早年段加上櫃重跑（裁定 seq281 §三：上櫃早年資料已過 G1 ⇒ 營量 v1、營量趨勢的早年段加上櫃版；只描述早年段、⛔ 不改營量 v1 暫定解除方式、⛔ 不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchEarlyOTC_rerun [--procs 3] [--seeds 200] | --check | --page

═══ 讀法（寫死於 2026-10-02 10:00（台北），在算任何報酬之前）═══
 Q0 查證（repo 內照實記；協調者背景說「早年段 2005～2014、950ad26e12 加 main 接合」⇒ 查到的不一樣，照查到的做）：
    營量 v1 的早年段正式數字 ＝ researchYLretest b2e「main|開|N20|H60」（commit e0d4a55d15 那批；backtest/resultsYLretest/b2_early_seeds.csv，200 顆）
      ＝ researchV.body_setup("main")（早年版面 tw-stock-data 3edc0e2206、~/earlydata/3edc0e2206/main/data、訊號 sig_main/and_signals.csv.gz）
        ＋ researchYear1M.sig_of(13, "mtm")（T1 ＝ and_censor、R8 減資截斷 ＝ reduce_events.csv）＋ stop_force 開；窗 2012-06-04～2014-12-31（PREREGV W_MAIN）、只上市
      ⚠ 950ad26e12＋main 的接合版面（researchEvt.ST）是飆股／長線等件用的，⛔ 不是營量 v1 的早年版面
    營量趨勢 ＝ backtest/researchYLtrend.py（commit 9e1948f914）；早年 ＝ 同一份早年版面、同窗；挑中格 乙_T3_H40（resultsYLtrend/cells.csv、seeds_early.csv.gz）
    早年版面的 AND 訊號本來就從 2005-02-01 起建（researchV SIG_START）⇒ 2005～2014 可以照同一條管線延伸（W_B，見 Q4）
 Q1 兩版：L ＝ 只上市（原版面一字不動）｜O ＝ 上市＋上櫃（新版面 ~/earlydata/eotc_<main10>/otc/data）
    O 版面 ＝ L 版面的全部檔（上市股的 stocks／adj／營收／處置等逐檔沿用，⇒ 上市部分逐位元同 L）＋ 上櫃部分（main 最新 f65bb03e11 的 data/early/daily 上櫃列）：
      ① 純上櫃股（四碼、首碼 1～9、非 91xx；kind 照 main stocks.csv，查不到 ⇒ R2 規則同 early_data）：上櫃列成檔，market＝tpex，first／last_seen ＝ 上櫃首末日
      ② 轉上市股（L 版面已把轉上市前的上櫃列併在檔裡當歷史）：檔不動，first_seen 改成上櫃首日（⇒ 上櫃期間也在母體）
      ③ 上市後轉上櫃（L 版面不收上市末日之後的上櫃列）：把上櫃列接在後面，last_seen 延到上櫃末日
      ⚠ 先驗證：L 版面的上櫃列（3edc0e2206）與 main 最新上櫃列逐欄相同；上市列只差 shares 欄（流動性閘用成交量、不用 shares ⇒ 不影響）
    上櫃除權息（還原）：main data/meta/otc_exright_history.csv（≤ 2014-12-31；2008-01 起）⇒ 只取事件日落在該檔上櫃期間的列；
      因子照 early_data.adj_events 的上櫃規則（ref ÷ pre、範圍 (0.05, 1.5]、＞1.0001 且 value 非負者丟、同日 (前收, 參考價) 去重）⇒ adj_lines 連乘
      ⚠ 2007-07～2007-12 沒有除權息資料 ⇒ 照報、⛔ 不補推估
    上櫃減資（R8 剔除／截斷，與上市同一條 researchV.apply_events）：2013 起 otc_reduce_history.csv（官方，e ＝ date、L ＝ e 之前最後有收盤日）；
      2007-07～2012-12 otc_reduce_early/otc_reduce_detected_2007_2012.csv 只取 shares_down＝1 且 exright_in_gap＝0（148 列；e ＝ resume_day、L ＝ last_trade_day），標「偵測、非官方」
    上櫃本益比、法人、融資：營量 v1 與營量趨勢的規則都不用 ⇒ 不放（⇒「法人 2014-12 前不可判定」這條對本件不適用，照記）
 Q2 訊號：O 版面照 researchV.body_sig 的 ①～④ 同一串函式重建（research34.process_stock、research11.stock_features、research13.and_flags、researchp1.attach_features；
    SIG 2005-02-01～2014-12-31、liq_mode shares、母體 load_universe ∩ gate3）；⑤ 門檻B 面板不建（兩件都不用）
    閘 S1：同一支建構函式在 L 版面重建 ⇒ and_signals 與 sig_main 逐列相同；閘 S2：O 的 AND 中「非轉上市、非上市轉上櫃」的上市股列 ＝ L 逐列相同
 Q3 引擎：營量 v1 ＝ simulate_mtm(sig, "H60", 20, default_rng(7000＋r), closesP, opensP, ncal＋1, log=[], d_max=None, pick="relvol", queue_days=0, stop_force)（同 b2e）
    營量趨勢 乙_T3_H40 ＝ researchYLtrend.build_world 的 SIGB["T3"]、H40、同引擎參數（_eng）；T4 用不到 ⇒ elig 傳空
    stop_force ＝ stop_force_days(valid_from_data(價格檔), 窗尾)；200 顆；成本照引擎
    閘 E1：L、W_A 的營量 v1 200 顆 ＝ b2_early_seeds main|開|N20|H60（年化、回落 repr）；閘 E2：L、W_A 的 乙_T3_H40 200 顆 ＝ resultsYLtrend/seeds_early.csv.gz（早年_年化、早年_回落 repr）
 Q4 窗：W_A ＝ 2012-06-04～2014-12-31（原正式早年窗）；W_B ＝ 2005-02-01～2014-12-31（協調者要的 2005～2014；AND 訊號起點）
    W_B 另切三段讀同一條權益：2005-02～2008-06（上櫃還沒有可進場的股：上櫃資料 2007-07 起、要 250 根）｜2008-07～2012-05｜2012-06～2014-12
    R8 事件：W_A ＝ L 原事件（reduce_events.csv，官方 TWTAUU 2011 起＋轉上市股上櫃期）［O 再加上櫃事件］；
            W_B 另加上市偵測事件（detected_events.csv、exright_in_gap＝False；同 researchV desc 段，標「偵測、非官方」）［O 再加上櫃事件］
 Q5 判準：年化中位、回落中位 vs 0050 同窗（使用者判準：年化 ＞ 0050 且 年化÷|回落| ≥ 0050 ⇒ 合格；只過第一條 ⇒ 另列；否則不合格）；0050 ＝ 早年版面 0050 還原
    差異來源：窗內 AND／乙族訊號數依「訊號日當時在上櫃」與否分；200 顆的買進筆中上櫃期間買進的比例；O−L 同顆年化差的中位
 Q6 上櫃資料品質（描述）：上櫃股檔數、有除權息事件的檔數與逐年事件數；還原後相鄰有效 K 棒收盤跌幅 ＞ 7.5%（2015-06 前漲跌幅 7%，正常日不會出現）
    的次數 ⇒ 還原前 vs 還原後（＝ 還原因子覆蓋率 ＝ 1 − 還原後 ÷ 還原前；扣掉 R8 事件日）；壞根（research11.load_bars 的 bad）數、斷點（data.breakpoints 套 applies）數；上市同口徑並列
 Q7 查核（--check）：抽 20 筆 O 版上櫃期間 AND 訊號，從 main 原始日 K＋otc_exright_history 逐日重算還原收盤、c1～c5、分數、營收 24 月新高（原始營收 csv）、H60 出場（無跌停順延的筆）；
    抽 30 檔上櫃股的 adj 檔 cum_factor 逐筆重乘；抽 20 個上櫃 R8 事件重找 L ⇒ 0 不同才算過；並附主程式各閘
    ⚠ 2026-10-02 10:51（台北）改查核（主程式結果已出、看過）：第一次查核營收那項 2 筆不同 ⇒ 查是查核自己用「訊號日當下最新可用月」，
      而 research13.and_flags 用的是「最新一列面板」——最新月的面板列被 research34 gate（流動性／處置／斷點窗）擋掉時會用前一期；
      ⇒ 查核改讀主程式面板的期別，可用日與 24 月新高仍從原始營收 csv 逐月重算；被擋而改用前一期的筆照計數。主程式一字不改
輸出 backtest/resultsEarlyOTC/：summary.json、cells.csv、seeds.csv.gz、quality.csv、quality_year.csv、check.json、早年段加上櫃重跑.html
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import early_data as E
from backtest import research11 as R
from backtest import rerun17 as RR

TIME = "2026-10-02 10:00（台北）"
OUT = "backtest/resultsEarlyOTC"
BASE = os.path.expanduser("~/earlydata/3edc0e2206")
L_DATA, L_SIG = os.path.join(BASE, "main", "data"), os.path.join(BASE, "sig_main")
SIG_START, SIG_END = "2005-02-01", "2014-12-31"
WIN = {"W_A": ("2012-06-04", "2014-12-31"), "W_B": ("2005-02-01", "2014-12-31")}
SUBSEG = {"2005-02～2008-06": ("2005-02-01", "2008-06-30"), "2008-07～2012-05": ("2008-07-01", "2012-05-31"), "2012-06～2014-12": ("2012-06-01", "2014-12-31")}
OTC_MAX = "2014-12-31"
SEED0 = 7000
CELLS = ("營量v1", "乙_T3_H40")
_W: dict = {}


def label(c, m, b):
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def main_sha():
    return subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()


def odirs(msha):
    root = os.path.expanduser(f"~/earlydata/eotc_{msha[:10]}")
    return root, os.path.join(root, "raw", "data"), os.path.join(root, "otc", "data"), os.path.join(root, "sig_otc"), os.path.join(root, "sig_Lrebuild")


# ═════════════ 資料 ═════════════
def extract(msha, log):
    root, raw, _, _, _ = odirs(msha)
    if os.path.isdir(os.path.join(raw, "early", "daily")) and os.path.exists(os.path.join(raw, "meta", "otc_exright_history.csv")):
        return
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    paths = ["data/early/daily", "data/early/revenue", "data/meta/otc_exright_history.csv", "data/meta/otc_reduce_history.csv", "data/meta/otc_reduce_early",
             "data/meta/stocks.csv", "data/early/_structure.csv"]
    p = subprocess.run(["git", "archive", "--format=tar", msha] + paths, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", os.path.join(root, "raw")], input=p.stdout, check=True)
    log(f"[取出] main {msha[:10]} ⇒ {root}/raw")


def read_daily_m(msha):
    root, raw, _, _, _ = odirs(msha)
    cache = os.path.join(root, "daily_all.pkl")
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    parts = []
    for f in sorted(glob.glob(os.path.join(raw, "early", "daily", "*.csv"))):
        x = pd.read_csv(f, dtype=str, keep_default_na=False)
        if list(x.columns) != E.DAILY_COLS:
            raise SystemExit(f"⛔ {f} 表頭不對")
        parts.append(x)
    df = pd.concat(parts, ignore_index=True)
    for c in E.NUM:
        df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce")
    df["market"] = df["market"].astype("category")
    pickle.dump(df, open(cache, "wb"), protocol=4)
    return df


def otc_adj_rows(H, sid, d_lo, d_hi_set):
    """上櫃除權息 ⇒ [(date, f, pre, ref, kind, src, fo)]（early_data.adj_events 的上櫃規則）。d_hi_set：該檔上櫃列的日期集合（只收落在上櫃期間的事件）。"""
    out = []; seen = set(); cnt = {"收": 0, "丟_範圍": 0, "丟_方向": 0, "去重": 0, "不在上櫃期": 0}
    for r in H.get(sid, []):
        d = r["date"]
        if d > OTC_MAX:
            continue
        if not (d_lo[0] <= d <= d_lo[1]):
            cnt["不在上櫃期"] += 1; continue
        pre, ref = E._fnum(r.get("pre_close")), E._fnum(r.get("ref_price"))
        if not pre or not ref or pre <= 0 or ref <= 0:
            continue
        val = E._fnum(r.get("value"))
        f = ref / pre
        if not (0.05 < f <= 1.5):
            cnt["丟_範圍"] += 1; continue
        if f > 1.0001 and not (val is not None and val < 0):
            cnt["丟_方向"] += 1; continue
        k = (d, round(pre, 4), round(ref, 4))
        if k in seen:
            cnt["去重"] += 1; continue
        seen.add(k)
        out.append((d, f, pre, ref, str(r.get("kind") or "").strip(), "exright", None)); cnt["收"] += 1
    return out, cnt


def build_otc_layout(msha, log):
    """⇒ O 版面（Q1）＋ 上櫃 R8 事件表；已建 ⇒ 直接回 STATUS。"""
    root, raw, O, _, _ = odirs(msha)
    st_p = os.path.join(root, "otc", "STATUS.json")
    if os.path.exists(st_p):
        return json.load(open(st_p, encoding="utf-8"))
    extract(msha, log)
    M = read_daily_m(msha)
    Bd = pickle.load(open(os.path.join(BASE, "daily_all.pkl"), "rb"))
    info = {"main": msha}
    # 先驗：上櫃列逐欄相同；上市列只差 shares
    k = ["date", "stock_id", "market"]; cols = ["open", "high", "low", "close", "volume", "amount", "shares"]
    for mk in ("twse", "tpex"):
        a = Bd[Bd["market"] == mk].set_index(k)[cols].astype(float); b = M[M["market"] == mk].set_index(k)[cols].astype(float)
        cm = a.index.intersection(b.index); aa, bb = a.loc[cm], b.loc[cm]
        neq = ~((aa == bb) | (aa.isna() & bb.isna()))
        info[f"日K 3edc0e2206 vs main（{mk}）"] = {"只在舊": int(len(a.index.difference(b.index))), "只在新": int(len(b.index.difference(a.index))),
                                                 "不同列（各欄）": {c: int(v) for c, v in neq.sum().items()}}
    del Bd
    os.makedirs(O, exist_ok=True)
    for d in ("meta", "stocks", "adj", "stocks_per", "stocks_inst", os.path.join("mops", "revenue_hist")):
        os.makedirs(os.path.join(O, d), exist_ok=True)
    for f in os.listdir(os.path.join(L_DATA, "meta")):
        if f != "stocks.csv":
            with open(os.path.join(L_DATA, "meta", f), "rb") as s, open(os.path.join(O, "meta", f), "wb") as t:
                t.write(s.read())
    for d in ("stocks_per", "stocks_inst", os.path.join("mops", "revenue_hist")):
        for f in os.listdir(os.path.join(L_DATA, d)):
            os.symlink(os.path.join(L_DATA, d, f), os.path.join(O, d, f))
    roster = pd.read_csv(os.path.join(L_DATA, "meta", "stocks.csv"), dtype=str)
    tw_first, tw_last = dict(zip(roster["stock_id"], roster["first_seen"])), dict(zip(roster["stock_id"], roster["last_seen"]))
    mst = pd.read_csv(os.path.join(raw, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")
    tp = M[(M["market"] == "tpex") & M["stock_id"].str.fullmatch(r"[1-9]\d{3}") & ~M["stock_id"].str.startswith("91")].copy()
    H = {}
    for r in pd.read_csv(os.path.join(raw, "meta", "otc_exright_history.csv"), dtype=str, keep_default_na=False).to_dict("records"):
        H.setdefault(str(r["stock_id"]).strip(), []).append(r)
    newrows = []; acnt = {"收": 0, "丟_範圍": 0, "丟_方向": 0, "去重": 0, "不在上櫃期": 0}; kinds = {"純上櫃": 0, "轉上市（first_seen 提前）": 0, "上市後轉上櫃（接上櫃列）": 0}
    changed = set(); periods = {}
    for sid, g in tp.groupby("stock_id", sort=True):
        g = g.sort_values("date")
        dts = g["date"].tolist()
        if sid in tw_first:
            pre = g[g["date"] < tw_first[sid]]; post = g[g["date"] > tw_last[sid]]; mid = g[(g["date"] >= tw_first[sid]) & (g["date"] <= tw_last[sid])]
            if len(mid):
                raise SystemExit(f"⛔ {sid} 上市期間內有上櫃列 {len(mid)}")
            Lf = pd.read_csv(os.path.join(L_DATA, "stocks", f"{sid}.csv"), dtype={"stock_id": str, "date": str})
            parts = [Lf]
            if len(post):
                x = post.drop(columns=["key"]).copy(); x["market"] = x["market"].astype(str)
                x["valid_bar"] = np.where(x["close"].notna() & (x["close"] > 0), 1, 0)
                parts.append(x[E.STOCK_COLS]); kinds["上市後轉上櫃（接上櫃列）"] += 1
            if len(pre):
                lset = set(Lf["date"])
                if not set(pre["date"]) <= lset:
                    raise SystemExit(f"⛔ {sid} 轉上市前上櫃列不在 L 檔")
                kinds["轉上市（first_seen 提前）"] += 1
            per_ = []
            if len(pre):
                per_.append((pre["date"].min(), pre["date"].max()))
            if len(post):
                per_.append((post["date"].min(), post["date"].max()))
            periods[sid] = per_
            if len(post):
                pd.concat(parts, ignore_index=True).to_csv(os.path.join(O, "stocks", f"{sid}.csv"), index=False); changed.add(sid)
            # 上櫃期新事件（L 版面的上櫃除權息 0 筆 ⇒ 全部是新的）
            ev = []
            for lo, hi in per_:
                rows, c_ = otc_adj_rows(H, sid, (lo, hi), None)
                ev += rows
                for kk in acnt:
                    acnt[kk] += c_[kk] if kk != "不在上櫃期" else 0
            if ev:
                Lev = []
                pa = os.path.join(L_DATA, "adj", f"{sid}.csv")
                if os.path.exists(pa):
                    a = pd.read_csv(pa, dtype=str, keep_default_na=False)
                    for r in a.to_dict("records"):
                        Lev.append((r["date"], float(r["factor"]), float(r["pre_close"]), float(r["ref_price"]), r["kind"], r["event"],
                                    float(r["factor_official"]) if r["factor_official"] else None))
                allev = sorted(Lev + ev, key=lambda z: (z[0], z[5]))
                E.adj_lines(allev).to_csv(os.path.join(O, "adj", f"{sid}.csv"), index=False); changed.add(sid + "#adj")
            newrows.append({"stock_id": sid, "first_seen": min(dts[0], tw_first[sid]), "last_seen": max(dts[-1], tw_last[sid])})
        else:
            x = g.drop(columns=["key"]).copy(); x["market"] = "tpex"
            x["valid_bar"] = np.where(x["close"].notna() & (x["close"] > 0), 1, 0)
            x[E.STOCK_COLS].to_csv(os.path.join(O, "stocks", f"{sid}.csv"), index=False)
            rows, c_ = otc_adj_rows(H, sid, (dts[0], dts[-1]), None)
            for kk in acnt:
                acnt[kk] += c_[kk]
            if rows:
                E.adj_lines(rows).to_csv(os.path.join(O, "adj", f"{sid}.csv"), index=False)
            kd = mst["kind"].get(sid) if sid in mst.index else None
            if kd is None or (isinstance(kd, float) and np.isnan(kd)):
                kd = "stock"                                    # R2：四碼、首碼 1～9、非 91xx（tp 已篩）
            nm = g["name"].iloc[-1]
            newrows.append({"stock_id": sid, "name": nm, "market": "tpex", "kind": kd, "first_seen": dts[0], "last_seen": dts[-1], "_new": True})
            periods[sid] = [(dts[0], dts[-1])]; kinds["純上櫃"] += 1
    # 其餘上市檔：symlink
    for f in os.listdir(os.path.join(L_DATA, "stocks")):
        sid = f[:-4]
        if not os.path.exists(os.path.join(O, "stocks", f)):
            os.symlink(os.path.join(L_DATA, "stocks", f), os.path.join(O, "stocks", f))
    for f in os.listdir(os.path.join(L_DATA, "adj")):
        if not os.path.exists(os.path.join(O, "adj", f)):
            os.symlink(os.path.join(L_DATA, "adj", f), os.path.join(O, "adj", f))
    R2 = roster.copy().set_index("stock_id")
    for r in newrows:
        if r.get("_new"):
            continue
        R2.loc[r["stock_id"], "first_seen"] = r["first_seen"]; R2.loc[r["stock_id"], "last_seen"] = r["last_seen"]
    add = pd.DataFrame([r for r in newrows if r.get("_new")]).drop(columns=["_new"]).set_index("stock_id")
    R2 = pd.concat([R2, add]).reset_index().rename(columns={"index": "stock_id"})
    R2[["stock_id", "name", "market", "kind", "first_seen", "last_seen"]].to_csv(os.path.join(O, "meta", "stocks.csv"), index=False)
    json.dump(periods, open(os.path.join(root, "otc", "otc_periods.json"), "w"))
    # 上櫃 R8 事件
    rows = []
    rh = pd.read_csv(os.path.join(raw, "meta", "otc_reduce_history.csv"), dtype=str, keep_default_na=False)
    rh = rh[rh["date"] <= OTC_MAX]
    trd = tp[np.isfinite(tp["close"]) & (tp["close"] > 0)][["stock_id", "date"]]
    byk = {s: np.array(sorted(g)) for s, g in trd.groupby("stock_id")["date"]}
    inper = lambda s, d: any(lo <= d <= hi for lo, hi in periods.get(s, []))
    for s, e in zip(rh["stock_id"].str.strip(), rh["date"].str.strip()):
        if not inper(s, e):
            continue
        arr = byk.get(s, np.array([])); i = int(np.searchsorted(arr, e))
        rows.append({"stock_id": s, "e": e, "L": arr[i - 1] if i > 0 else None, "src": "otc_reduce_history（官方）"})
    de = pd.read_csv(os.path.join(raw, "meta", "otc_reduce_early", "otc_reduce_detected_2007_2012.csv"), dtype=str, keep_default_na=False)
    de = de[(de["shares_down"] == "1") & (de["exright_in_gap"] == "0")]
    info["上櫃減資偵測取用列"] = int(len(de))
    for s, e, L_ in zip(de["stock_id"], de["resume_day"], de["last_trade_day"]):
        if inper(s, e):
            rows.append({"stock_id": s, "e": e, "L": L_, "src": "otc_reduce_detected（偵測、非官方）"})
    EVO = pd.DataFrame(rows).drop_duplicates(["stock_id", "e"])
    EVO.to_csv(os.path.join(root, "otc", "otc_reduce_events.csv"), index=False)
    info.update({"上櫃股": kinds, "上櫃除權息因子": acnt, "改寫或新增的上市檔": sorted(changed), "新增上櫃檔": int(len(add)),
                 "上櫃 R8 事件": EVO["src"].value_counts().to_dict(), "上櫃 R8 事件 L 缺": int(EVO["L"].isna().sum()), "complete": True})
    json.dump(info, open(st_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[O 版面] {json.dumps(info, ensure_ascii=False, default=str)[:1500]}")
    return info


# ═════════════ 訊號（researchV.body_sig ①～④ 同一串）═════════════
def build_sig(data_dir, out, procs, log):
    if os.path.exists(os.path.join(out, "and_signals.csv.gz")):
        return json.load(open(os.path.join(out, "INFO.json"), encoding="utf-8"))
    from backtest import patterns as PT
    from backtest import research13 as R13
    from backtest import research34 as R34
    from backtest import researchp1 as P1
    from backtest import universe_gate as UG
    D.DATA = data_dir; os.makedirs(out, exist_ok=True); t0 = time.time()
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    PT.PARAMS["liq_mode"] = "shares"
    bdf = D.load_benchmark(cal)
    bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = R34.load_revenue()
    rdates = R34.rebalance_dates(list(rev.index), cal, 10)
    lo = int(cal.searchsorted(pd.Timestamp(SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    rows = []
    with Pool(procs, initializer=R34._init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
        for r in pool.imap_unordered(R34.process_stock, jobs, chunksize=8):
            if r:
                rows += r
    panel = pd.DataFrame(rows)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in panel:
            panel[c] = panel[c].astype("boolean")
    panel["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["signal_pos"]]
    panel["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["entry_pos"]]
    panel.to_csv(os.path.join(out, "panel_rev.csv.gz"), index=False, compression="gzip")
    tasks = [(r.stock_id, r.market, r.first_seen) for r in uni.itertuples()]
    main_rows = []
    with Pool(procs, initializer=R._init, initargs=(cal,)) as pool:
        for r in pool.imap_unordered(R.stock_features, tasks, chunksize=8):
            if r is not None:
                main_rows.extend(r["main"])
    S_full = pd.DataFrame(main_rows)
    S_full.to_csv(os.path.join(out, "signals_S_full.csv.gz"), index=False)
    pnl = pd.read_csv(os.path.join(out, "panel_rev.csv.gz"), dtype={"stock_id": str})
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    S = pd.read_csv(os.path.join(out, "signals_S_full.csv.gz"), dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    flags, _ = R13.and_flags(S, pnl)
    AND = S[flags].copy()
    missing, mism = P1.attach_features(AND, S, cal, uni.set_index("stock_id")["market"], procs)
    if mism:
        raise SystemExit("⛔ k 與 pos 對不上")
    AND.to_csv(os.path.join(out, "and_signals.csv.gz"), index=False)
    S.to_csv(os.path.join(out, "signals_S.csv.gz"), index=False)
    info = {"data": data_dir, "母體": int(len(uni)), "上櫃母體": int((uni["market"] == "tpex").sum()), "營收面板列": int(len(panel)), "S": int(len(S)), "AND": int(len(AND)),
            "SIG": [str(cal[lo].date()), str(cal[hi].date())], "秒": round(time.time() - t0)}
    json.dump(info, open(os.path.join(out, "INFO.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[訊號] {json.dumps(info, ensure_ascii=False)}")
    return info


# ═════════════ 世界 ═════════════
def events(ver, win, msha):
    EV = pd.read_csv(os.path.join(BASE, "reduce_events.csv"), dtype=str)[["stock_id", "e", "L"]]
    parts = [EV]
    if win == "W_B":
        X = pd.read_csv(os.path.join(BASE, "detected_events.csv"), dtype={"stock_id": str, "L": str, "e": str})
        X = X[~X["exright_in_gap"].astype(bool)]
        parts.append(X[["stock_id", "e", "L"]])
    if ver == "O":
        root = odirs(msha)[0]
        O_ = pd.read_csv(os.path.join(root, "otc", "otc_reduce_events.csv"), dtype=str)
        parts.append(O_.dropna(subset=["L"])[["stock_id", "e", "L"]])
    return pd.concat(parts).drop_duplicates(["stock_id", "e"]).reset_index(drop=True)


def make_world(ver, win, msha, procs, log):
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import researchYLtrend as YT
    data_dir = L_DATA if ver == "L" else odirs(msha)[2]
    sig_dir = L_SIG if ver == "L" else odirs(msha)[3]
    D.DATA = data_dir
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(os.path.join(sig_dir, "and_signals.csv.gz"), dtype={"sid": str})
    w0 = int(cal.searchsorted(pd.Timestamp(WIN[win][0]))); w1 = int(cal.searchsorted(pd.Timestamp(WIN[win][1])))
    EV = events(ver, win, msha)
    closes, opens = RR.load_prices(sorted(set(AND["sid"])), cal, uni, "branch")
    AND_m, cA = Y.and_censor(AND, cal, uni, lambda x: None)
    T, cE = V.apply_events(AND_m, EV, cal, "AND", px=(closes, opens))
    cE.pop("_short_keys", None)
    # 營量趨勢 world（全表 AND_mtm ⇒ 窗在 build_world 切）
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(cal)}
    EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    rev = pd.read_csv(os.path.join(sig_dir, "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    esids = [(s, uni.get(s, "twse")) for s in sorted(uni.index)]
    We = YT.build_world(f"{ver}{win}", cal, w0, w1, esids, T.copy(), rev, {}, EVD, procs, log)
    cl, op = dict(closes), dict(opens)
    extra = sorted((set(We["POOL"]["sid"]) | set(We["SIGB"]["T3"]["sid"])) - set(cl))
    if extra:
        c2, o2 = RR.load_prices(extra, cal, uni, "branch"); cl.update(c2); op.update(o2)
    clP, opP = Y.pad_px(cl, op)
    SF = R.stop_force_days(R.valid_from_data(sorted(cl), uni, cal), w1)
    bench = RR.load_bench(cal)
    v1 = T[(T["entry_pos"] >= w0) & (T["entry_pos"] <= w1)]
    segp = {"全窗": (w0, w1)}
    if win == "W_B":
        for nm, (a, b) in SUBSEG.items():
            segp[nm] = (int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1)
    b50 = {nm: RR.bench_row(cal, bench, x, y + 1) for nm, (x, y) in segp.items()}
    # 上櫃期間判定
    per = json.load(open(os.path.join(odirs(msha)[0], "otc", "otc_periods.json"))) if ver == "O" else {}
    pp = {s: [(int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1) for a, b in v] for s, v in per.items()}
    isotc = lambda s, t: any(a <= t <= b for a, b in pp.get(s, []))
    W = {"ver": ver, "win": win, "cal": cal, "w0": w0, "w1": w1, "closes": clP, "opens": opP, "ncal": ncal + 1, "SF": SF, "segp": segp, "b50": b50,
         "SIG": {"營量v1": (v1, 60), "乙_T3_H40": (We["SIGB"]["T3"], 40)}, "isotc": isotc, "AND_full": T}
    cnt = {}
    for k, (s, H) in W["SIG"].items():
        o_ = [isotc(a, int(b)) for a, b in zip(s["sid"], s["pos"])]
        cnt[k] = {"訊號數": int(len(s)), "訊號日在上櫃": int(sum(o_))}
    W["info"] = {"窗": [str(cal[w0].date()), str(cal[w1].date())], "R8 事件": int(len(EV)), "T1": cA, "R8": cE, "訊號": cnt, "0050": b50,
                 "營量趨勢 H60 閘": We["gate_exit"], "停止交易股": len(SF)}
    return W


def run_one(job):
    wk, cell, r = job
    W = _W[wk]; sig, H = W["SIG"][cell]; au = []
    o = R.simulate_mtm(sig, f"H{H}", 20, np.random.default_rng(SEED0 + r), W["closes"], W["opens"], W["ncal"], return_equity=True,
                       log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
    eq = np.asarray(o["equity"], float)
    row = {"版": W["ver"], "窗": W["win"], "格": cell, "r": r}
    for nm, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{nm}_年化"] = float(c_); row[f"{nm}_回落"] = float(m_)
    w0, w1 = W["w0"], W["w1"]
    buys = [a for a in au if a["side"] == "buy" and w0 <= a["t"] <= w1]
    row["買進筆"] = len(buys); row["上櫃期買進筆"] = int(sum(W["isotc"](a["sid"], int(a["t"])) for a in buys))
    row["強制出場"] = int(o.get("x_stop_force_n", -1))
    return row


# ═════════════ 品質 ═════════════
def q_one(args):
    sid, mk, otcper = args
    B = R.load_bars(sid, mk, _W["qcal"])
    if B is None:
        return None
    idx, c, rc, dates = B["idx"], B["c"], B["rc"], B["dates"]
    nb = B["next_bad"]; bad = np.array([nb[k] == k for k in range(len(idx))])
    st = D.load_stock(sid, mk, _W["qcal"])
    nbp = sum(1 for b in D.breakpoints(st.df, st.event_dates) if D.applies(b))
    evd = set(_W["qev"].get(sid, []))
    out = []
    cut = pd.Timestamp("2015-06-01")
    for k in range(1, len(idx)):
        if idx[k] - idx[k - 1] != 1 or dates[k] >= cut:
            continue
        d = dates[k].strftime("%Y-%m-%d")
        if d in evd:
            continue
        mk_ = "tpex" if any(a <= d <= b for a, b in otcper) else "twse"
        out.append((mk_, d[:4], bool(rc[k] / rc[k - 1] < 0.925), bool(c[k] / c[k - 1] < 0.925)))
    return sid, out, int(bad.sum()), nbp, len(idx)


def quality(msha, procs, log):
    root, raw, O, _, _ = odirs(msha)
    D.DATA = O
    cal = D.load_calendar()
    st = pd.read_csv(os.path.join(O, "meta", "stocks.csv"), dtype=str)
    st = st[st["kind"] == "stock"]
    per = json.load(open(os.path.join(root, "otc", "otc_periods.json")))
    ev = pd.concat([events("O", "W_B", msha)])
    _W["qcal"] = cal; _W["qev"] = {s: list(g) for s, g in ev.groupby("stock_id")["e"]}
    jobs = [(s, m, per.get(s, [])) for s, m in zip(st["stock_id"], st["market"])]
    rows = []; meta = []
    with Pool(procs) as pool:
        for r in pool.imap_unordered(q_one, jobs, chunksize=8):
            if r is None:
                continue
            sid, out, nbad, nbp, nbars = r
            rows += [(sid, *x) for x in out]
            meta.append({"sid": sid, "上櫃股": sid in per, "壞根": nbad, "斷點": nbp, "有效K棒": nbars})
    Q = pd.DataFrame(rows, columns=["sid", "市場", "年", "還原前跌逾7.5%", "還原後跌逾7.5%"])
    G = Q.groupby(["市場", "年"]).agg(相鄰K棒=("sid", "size"), 還原前=("還原前跌逾7.5%", "sum"), 還原後=("還原後跌逾7.5%", "sum")).reset_index()
    G["覆蓋率"] = 1 - G["還原後"] / G["還原前"].where(G["還原前"] > 0)
    tot = Q.groupby("市場").agg(相鄰K棒=("sid", "size"), 還原前=("還原前跌逾7.5%", "sum"), 還原後=("還原後跌逾7.5%", "sum")).reset_index()
    tot["覆蓋率"] = 1 - tot["還原後"] / tot["還原前"]
    MT = pd.DataFrame(meta)
    hx = pd.read_csv(os.path.join(raw, "meta", "otc_exright_history.csv"), dtype=str)
    hx = hx[hx["date"] <= OTC_MAX]
    adjc = {"上櫃除權息事件（≤2014，逐年）": hx["date"].str[:4].value_counts().sort_index().to_dict(),
            "上櫃股有 adj 檔": int(sum(os.path.exists(os.path.join(O, "adj", f"{s}.csv")) for s in per)), "上櫃股": len(per)}
    pm = {"上櫃（含轉上市前、轉上櫃後）": MT[MT["上櫃股"]], "只上市": MT[~MT["上櫃股"]]}
    bb = {k: {"檔": int(len(v)), "壞根": int(v["壞根"].sum()), "斷點": int(v["斷點"].sum()), "有效K棒": int(v["有效K棒"].sum()),
              "每萬根壞根": float(v["壞根"].sum() / max(v["有效K棒"].sum(), 1) * 1e4)} for k, v in pm.items()}
    G.to_csv(os.path.join(OUT, "quality_year.csv"), index=False, float_format="%.6g"); tot.to_csv(os.path.join(OUT, "quality.csv"), index=False, float_format="%.6g")
    log(f"[品質] {tot.to_dict('records')}｜{bb}")
    return {"覆蓋（全期）": tot.to_dict("records"), "壞根斷點": bb, "還原事件": adjc}


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    msha = main_sha(); S = {"讀法寫死": TIME, "main": msha, "L 版面": "tw-stock-data 3edc0e2206（~/earlydata/3edc0e2206/main）"}
    S["O 版面"] = build_otc_layout(msha, log)
    # 閘 S1：同一支建構函式在 L 版面重建 ⇒ 與 sig_main 逐列相同
    _, _, O, sigO, sigL = odirs(msha)
    build_sig(L_DATA, sigL, a.procs, log)
    A0 = pd.read_csv(os.path.join(L_SIG, "and_signals.csv.gz"), dtype={"sid": str}); A1 = pd.read_csv(os.path.join(sigL, "and_signals.csv.gz"), dtype={"sid": str})
    k0 = A0.sort_values(["sid", "k"]).reset_index(drop=True); k1 = A1.sort_values(["sid", "k"]).reset_index(drop=True)
    S["閘"] = {"S1 L 版面重建 AND ＝ sig_main（列數、sid／k／xpos_H60 不同列、g_H60 最大差）": [len(k0), len(k1),
               int((k0[["sid", "k", "xpos_H60"]] != k1[["sid", "k", "xpos_H60"]]).any(axis=1).sum()) if len(k0) == len(k1) else -1,
               float(np.nanmax(np.abs(k0["g_H60"].to_numpy(float) - k1["g_H60"].to_numpy(float)))) if len(k0) == len(k1) else -1]}
    S["O 訊號"] = build_sig(O, sigO, a.procs, log)
    AO = pd.read_csv(os.path.join(sigO, "and_signals.csv.gz"), dtype={"sid": str})
    ch = {x.split("#")[0] for x in S["O 版面"]["改寫或新增的上市檔"]} | set(json.load(open(os.path.join(BASE, "transferred.json"))))
    a_ = A0[~A0["sid"].isin(ch)].sort_values(["sid", "k"]).reset_index(drop=True)
    roster = set(pd.read_csv(os.path.join(L_DATA, "meta", "stocks.csv"), dtype=str)["stock_id"])
    b_ = AO[AO["sid"].isin(roster) & ~AO["sid"].isin(ch)].sort_values(["sid", "k"]).reset_index(drop=True)
    cols = ["sid", "k", "pos", "entry_pos", "xpos_H60"]
    S["閘"]["S2 O 版上市股（非轉上市／轉上櫃）AND ＝ L（L 列、O 列、不同列）"] = [len(a_), len(b_), int((a_[cols] != b_[cols]).any(axis=1).sum()) if len(a_) == len(b_) else -1]
    log(f"[閘] {S['閘']}")
    # 世界與引擎
    seeds = list(range(a.seeds)); ROWS = []; WI = {}
    for ver in ("L", "O"):
        for win in ("W_A", "W_B"):
            wk = f"{ver}|{win}"
            _W[wk] = make_world(ver, win, msha, a.procs, log); WI[wk] = _W[wk]["info"]
            log(f"[世界 {wk}] {json.dumps(WI[wk], ensure_ascii=False, default=str)[:800]}｜{time.time() - T0:.0f}s")
            with Pool(a.procs) as pool:
                ROWS += pool.map(run_one, [(wk, c, r) for c in CELLS for r in seeds], chunksize=4)
            for k in list(_W[wk]):
                if k not in ("info", "b50", "segp"):
                    _W[wk].pop(k)
    SE = pd.DataFrame(ROWS); SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    S["世界"] = WI
    # 閘 E1、E2
    ref1 = pd.read_csv("backtest/resultsYLretest/b2_early_seeds.csv", float_precision="round_trip")
    ref1 = ref1[ref1["key"] == "main|開|N20|H60"].sort_values("r").reset_index(drop=True)
    m1 = SE[(SE["版"] == "L") & (SE["窗"] == "W_A") & (SE["格"] == "營量v1")].sort_values("r").reset_index(drop=True)
    n1 = min(len(ref1), len(m1))
    S["閘"]["E1 L W_A 營量v1 ＝ b2e main|開|N20|H60（不同顆數／比較顆數）"] = [int(sum(repr(float(ref1.loc[i, "cagr"])) != repr(float(m1.loc[i, "全窗_年化"]))
                                                                        or repr(float(ref1.loc[i, "mdd"])) != repr(float(m1.loc[i, "全窗_回落"])) for i in range(n1))), n1]
    ref2 = pd.read_csv("backtest/resultsYLtrend/seeds_early.csv.gz", float_precision="round_trip")
    ref2 = ref2[ref2["格"] == "乙_T3_H40"].sort_values("r").reset_index(drop=True)
    m2 = SE[(SE["版"] == "L") & (SE["窗"] == "W_A") & (SE["格"] == "乙_T3_H40")].sort_values("r").reset_index(drop=True)
    n2 = min(len(ref2), len(m2))
    S["閘"]["E2 L W_A 乙_T3_H40 ＝ resultsYLtrend seeds_early（不同顆數／比較顆數）"] = [int(sum(repr(float(ref2.loc[i, "早年_年化"])) != repr(float(m2.loc[i, "全窗_年化"]))
                                                                             or repr(float(ref2.loc[i, "早年_回落"])) != repr(float(m2.loc[i, "全窗_回落"])) for i in range(n2))), n2]
    # 彙總
    C = []
    for (ver, win, cell), g in SE.groupby(["版", "窗", "格"]):
        segs = ["全窗"] + (list(SUBSEG) if win == "W_B" else [])
        for sg in segs:
            b = WI[f"{ver}|{win}"]["0050"][sg]
            c_, m_ = float(np.median(g[f"{sg}_年化"])), float(np.median(g[f"{sg}_回落"]))
            row = {"版": ver, "窗": win, "段": sg, "格": cell, "年化中位": c_, "年化p10": float(np.quantile(g[f"{sg}_年化"], .1)), "年化p90": float(np.quantile(g[f"{sg}_年化"], .9)),
                   "回落中位": m_, "比值": c_ / abs(m_) if m_ else np.nan, "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"]), "標籤": label(c_, m_, b),
                   "買進筆中位": float(g["買進筆"].median()), "上櫃期買進占比": float(g["上櫃期買進筆"].sum() / max(g["買進筆"].sum(), 1)),
                   "訊號數": WI[f"{ver}|{win}"]["訊號"][cell]["訊號數"], "訊號日在上櫃": WI[f"{ver}|{win}"]["訊號"][cell]["訊號日在上櫃"]}
            if ver == "O":
                gl = SE[(SE["版"] == "L") & (SE["窗"] == win) & (SE["格"] == cell)].sort_values("r")
                go = g.sort_values("r")
                d = go[f"{sg}_年化"].to_numpy() - gl[f"{sg}_年化"].to_numpy()
                row["對L年化差中位"] = float(np.median(d)); row["O贏L顆數比例"] = float(np.mean(d > 1e-12))
            C.append(row)
    C = pd.DataFrame(C); C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.6g")
    S["品質"] = quality(msha, a.procs, log)
    S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] 閘 {S['閘']}｜{S['耗時秒']}s")
    g = S["閘"]
    bad = g["S1 L 版面重建 AND ＝ sig_main（列數、sid／k／xpos_H60 不同列、g_H60 最大差）"][2] != 0 or \
        g["E1 L W_A 營量v1 ＝ b2e main|開|N20|H60（不同顆數／比較顆數）"][0] or g["E2 L W_A 乙_T3_H40 ＝ resultsYLtrend seeds_early（不同顆數／比較顆數）"][0]
    if bad:
        raise SystemExit(f"⛔ 閘不過 {g}")


# ═════════════ 查核 ═════════════
def check(a, log):
    from backtest import research34 as R34
    msha = main_sha(); root, raw, O, sigO, _ = odirs(msha)
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    per = json.load(open(os.path.join(root, "otc", "otc_periods.json")))
    M = read_daily_m(msha)
    hx = pd.read_csv(os.path.join(raw, "meta", "otc_exright_history.csv"), dtype=str, keep_default_na=False)
    D.DATA = O; cal = D.load_calendar(); pos = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}
    errs = []; info = {}
    # ① adj cum_factor 逐筆重乘（30 檔上櫃股）
    rng = np.random.default_rng(20261002)
    have = sorted(s for s in per if os.path.exists(os.path.join(O, "adj", f"{s}.csv")))
    nd = 0
    for s in rng.choice(have, size=min(30, len(have)), replace=False):
        a_ = pd.read_csv(os.path.join(O, "adj", f"{s}.csv"), dtype=str, keep_default_na=False)
        fs = [float(x) if not fo else float(fo) for x, fo in zip(a_["factor"], a_["factor_official"])]
        for i in range(len(a_)):
            prod = 1.0
            for j in range(i, len(a_)):
                prod *= fs[j]
            if abs(prod - float(a_["cum_factor"].iloc[i])) > 5e-8:
                nd += 1; errs.append(f"adj {s} {a_['date'].iloc[i]} {prod} {a_['cum_factor'].iloc[i]}")
        hs = hx[(hx["stock_id"] == s) & (hx["date"] <= OTC_MAX)]
        hs = hs[[any(lo <= d <= hi for lo, hi in per[s]) for d in hs["date"]]]
        mine = set(a_.loc[a_["event"] == "exright", "date"]) if s not in set(pd.read_csv(os.path.join(L_DATA, "meta", "stocks.csv"), dtype=str)["stock_id"]) else None
        if mine is not None:
            want = {d for d, p, r in zip(hs["date"], hs["pre_close"], hs["ref_price"]) if 0.05 < float(r) / float(p) <= 1.0001}
            if not want <= mine:
                nd += 1; errs.append(f"adj {s} 少事件 {sorted(want - mine)[:3]}")
    info["① adj 重乘不同"] = nd
    # ② R8 L 重找（20 個上櫃事件）
    EVO = pd.read_csv(os.path.join(root, "otc", "otc_reduce_events.csv"), dtype=str)
    smp = EVO[EVO["src"].str.startswith("otc_reduce_history")]
    nd2 = 0
    for r in smp.sample(min(20, len(smp)), random_state=20261002).itertuples():
        g = M[(M["stock_id"] == r.stock_id) & (M["market"] == "tpex") & (M["close"] > 0)]
        Ls = g[g["date"] < r.e]["date"].max()
        if Ls != r.L:
            nd2 += 1; errs.append(f"R8 {r.stock_id} {r.e} L {Ls}/{r.L}")
    info["② R8 L 不同"] = nd2
    # ③ 20 筆上櫃期 AND 訊號逐日重算
    AO = pd.read_csv(os.path.join(sigO, "and_signals.csv.gz"), dtype={"sid": str})
    isotc = [any(lo <= cal[int(p)].strftime("%Y-%m-%d") <= hi for lo, hi in per.get(s, [])) for s, p in zip(AO["sid"], AO["pos"])]
    smp = AO[np.array(isotc)].sample(20, random_state=20261002)
    revs = {}
    for f in sorted(glob.glob(os.path.join(O, "mops", "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"])
        for s_, p_, v_ in zip(x["stock_id"], x["period"], x["當月營收"]):
            try:
                revs[(s_, p_)] = float(str(v_).replace(",", ""))
            except ValueError:
                pass
    nd3 = 0; skipped = 0; gated = 0
    PANEL = pd.read_csv(os.path.join(sigO, "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos"])
    for r in smp.itertuples():
        s = r.sid; why = []
        raw_ = pd.read_csv(os.path.join(O, "stocks", f"{s}.csv"), dtype={"date": str})
        raw_ = raw_[raw_["date"].isin(pos)].drop_duplicates("date")
        okp = np.ones(len(raw_), bool)
        for col in ("open", "high", "low", "close"):
            v_ = pd.to_numeric(raw_[col], errors="coerce").to_numpy(float)
            okp &= ~(v_ <= 0)
        okp &= pd.to_numeric(raw_["close"], errors="coerce").notna().to_numpy()
        raw_ = raw_[okp].sort_values("date").reset_index(drop=True)
        dl = raw_["date"].tolist()
        ev = []
        pa = os.path.join(O, "adj", f"{s}.csv")
        if os.path.exists(pa):
            aa = pd.read_csv(pa, dtype=str, keep_default_na=False)
            ev = [(d, float(fo) if fo else float(f)) for d, f, fo in zip(aa["date"], aa["factor"], aa["factor_official"])]
        cf = np.array([np.prod([f for d, f in ev if d > dd]) if ev else 1.0 for dd in raw_["date"]])
        rc = raw_["close"].astype(float).to_numpy(); c = rc * cf; o = raw_["open"].astype(float).to_numpy() * cf; amt = raw_["amount"].astype(float).to_numpy()
        k = int(np.flatnonzero(raw_["date"].to_numpy() == cal[int(r.pos)].strftime("%Y-%m-%d"))[0])
        if k != int(r.k):
            why.append(f"k {k}/{r.k}")
        ma100 = c[k - 99:k + 1].mean(); hi250 = c[k - 249:k + 1].max()
        c1 = c[k] / c[k - 20] - 1 >= 0.30; c3 = amt[k] / amt[k - 20:k].mean() >= 3.0; c4 = c[k] > ma100; c5 = c[k] >= hi250
        import bisect
        evk = {bisect.bisect_left(dl, d) for d, _ in ev}
        nup = 0
        for j in range(k - 19, k + 1):
            if j in evk:
                continue
            lim = 0.07 if raw_["date"].iloc[j] < "2015-06-01" else 0.10
            if abs(rc[j] - R.limit_price(rc[j - 1], True, lim)) < 1e-6:
                nup += 1
        c2 = nup >= 3
        sc = int(c1) + int(c2) + int(c3) + int(c4) + int(c5)
        if sc < 3:
            why.append(f"分數 {sc}（c1 {c1} c2 {c2} c3 {c3} c4 {c4} c5 {c5}）")
        # 營收：主程式面板中訊號日當下最新的一列（signal_pos ≤ pos、距離 ≤ 45）⇒ 期別 p；p 的可用日照「次月 10 日後第一交易日」逐日重找；
        #       rev_hi24 從原始營收 csv 重算（當月 ≥ 前 24 期最高、24 期都有值）。最新可用月的面板列若被 research34 gate 擋（流動性／處置／斷點窗）⇒ 改用前一期，照計數
        pr = PANEL[(PANEL["stock_id"] == s) & (PANEL["signal_pos"] <= int(r.pos))].sort_values("signal_pos").tail(1)
        ok_rev = False; p = None
        if len(pr):
            p = pr["period"].iloc[0]; y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            av = int(cal.searchsorted(pd.Timestamp(year=y2, month=m2, day=10), side="right"))
            prev = []; yy, mm = y, m
            for _ in range(24):
                mm -= 1
                if mm == 0:
                    yy -= 1; mm = 12
                prev.append(revs.get((s, f"{yy:04d}-{mm:02d}"), np.nan))
            ok_rev = (av - 1 == int(pr["signal_pos"].iloc[0])) and int(r.pos) - (av - 1) <= 45 and (s, p) in revs and \
                bool(np.all(np.isfinite(prev)) and revs[(s, p)] >= max(prev))
            sd = cal[int(r.pos)]; lm = (sd.year * 12 + sd.month - 2) - (1 if sd.day <= 10 else 0)
            if y * 12 + m - 1 < lm:
                gated += 1
        if not ok_rev:
            why.append(f"營收 24 月新高不成立（{p}）")
        # H60：進場根算第 1 根、第 60 根收盤（research11.fixed_exit：exit_pos(k＋1, 60) ＝ k＋60）
        if int(r.xpos_H60) >= 0:
            j = k + 60
            if j >= len(c) or pos[raw_["date"].iloc[j]] != int(r.xpos_H60) or abs(c[j] / o[k + 1] - 1 - float(r.g_H60)) > 1e-6:
                why.append(f"H60 {pos[raw_['date'].iloc[j]] if j < len(c) else None}/{r.xpos_H60} g {(c[j] / o[k + 1] - 1) if j < len(c) else np.nan:.6f}/{float(r.g_H60):.6f}")
        else:
            skipped += 1
        if why:
            nd3 += 1; errs.append(f"AND {s} pos {r.pos}：{'；'.join(why)}")
    info["③ 上櫃期 AND 20 筆不同"] = nd3; info["③ H60 無出場（xpos＝−1）未比"] = skipped
    info["③ 最新可用月面板列被 gate 擋、改用較早一期的筆（照主程式面板；只計數）"] = gated
    out = {"讀法寫死": TIME, "比對": info, "不同的筆": errs[:20], "主程式閘": S["閘"], "通過": not errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {info}｜{errs[:5]}")


# ═════════════ 網頁 ═════════════
def page(log):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")); C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    QY = pd.read_csv(os.path.join(OUT, "quality_year.csv"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    e = html.escape
    g = lambda ver, win, sg, cell: C[(C["版"] == ver) & (C["窗"] == win) & (C["段"] == sg) & (C["格"] == cell)].iloc[0]
    NM = {"營量v1": "營量 v1", "乙_T3_H40": "營量趨勢（乙_T3_H40）"}
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>早年段加上櫃重跑</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>早年段加上櫃重跑：營量 v1、營量趨勢</h1>",
         "<p class='warn'>⚠ 只描述早年段，不改營量 v1 的暫定解除方式、不計檢定數。上櫃早年資料 2007-07 起；2005-01～2007-06 只有上市。</p>"]
    L = []
    for cell in CELLS:
        a_l, a_o = g("L", "W_A", "全窗", cell), g("O", "W_A", "全窗", cell)
        b_l, b_o = g("L", "W_B", "全窗", cell), g("O", "W_B", "全窗", cell)
        L.append(f"<li><b>{NM[cell]}</b>：原早年窗（2012-06～2014-12）只上市 {P1(a_l['年化中位'])}／{P1(a_l['回落中位'])}（{a_l['標籤']}）→ 加上櫃 "
                 f"{P1(a_o['年化中位'])}／{P1(a_o['回落中位'])}（<b>{a_o['標籤']}</b>；0050 {P1(a_l['0050年化'])}／{P1(a_l['0050回落'])}）；"
                 f"2005-02～2014-12 只上市 {P1(b_l['年化中位'])}／{P1(b_l['回落中位'])}（{b_l['標籤']}）→ 加上櫃 {P1(b_o['年化中位'])}／{P1(b_o['回落中位'])}（<b>{b_o['標籤']}</b>；"
                 f"0050 {P1(b_l['0050年化'])}／{P1(b_l['0050回落'])}）。</li>")
    H.append("<div class='ok big'><b>先講結論</b><ul>" + "".join(L) + "</ul></div>")
    gs = S["閘"]
    H.append(f"<p class='lead'>讀法寫死 {e(S['讀法寫死'])}。只上市版用原早年版面一字不動，"
             f"原早年窗的營量 v1 與營量趨勢 200 顆和原交件逐位元相同（不同顆數 {gs['E1 L W_A 營量v1 ＝ b2e main|開|N20|H60（不同顆數／比較顆數）'][0]}、"
             f"{gs['E2 L W_A 乙_T3_H40 ＝ resultsYLtrend seeds_early（不同顆數／比較顆數）'][0]}）。加上櫃版只多放上櫃的日 K、除權息、減資，上市部分沿用同一批檔。"
             + (f"查核：{'通過' if CK['通過'] else '有不同'}。" if CK else "") + "</p>")
    H.append("<h2>一、組合層（200 顆種子中位）</h2><div class='wrap'><table><tr><th class='l'>策略</th><th class='l'>窗／段</th><th class='l'>版</th><th>年化<br><small>p10～p90</small></th><th>回落</th>"
             "<th>0050</th><th>標籤</th><th>加上櫃<br><small>年化差中位</small></th><th>訊號數<br><small>（上櫃期）</small></th><th>上櫃期<br><small>買進占比</small></th></tr>")
    for cell in CELLS:
        for win in ("W_A", "W_B"):
            for sg in ["全窗"] + (list(SUBSEG) if win == "W_B" else []):
                for ver in ("L", "O"):
                    x = g(ver, win, sg, cell)
                    wn = ("2012-06～2014-12（原窗）" if win == "W_A" else ("2005-02～2014-12" if sg == "全窗" else f"　└ {sg}"))
                    H.append(f"<tr><td class='l'>{NM[cell] if ver == 'L' else ''}</td><td class='l'>{wn if ver == 'L' else ''}</td><td class='l'>{'只上市' if ver == 'L' else '上市＋上櫃'}</td>"
                             f"<td>{P1(x['年化中位'])}<br><small>{P1(x['年化p10'])}～{P1(x['年化p90'])}</small></td><td>{P1(x['回落中位'])}</td>"
                             f"<td>{P1(x['0050年化'])}<br><small>{P1(x['0050回落'])}</small></td><td>{x['標籤']}</td>"
                             f"<td>{PT(x['對L年化差中位']) if ver == 'O' else '—'}</td><td>{int(x['訊號數'])}<br><small>（{int(x['訊號日在上櫃'])}）</small></td>"
                             f"<td>{P_(x['上櫃期買進占比']) if sg == '全窗' else ''}</td></tr>")
    H.append("</table></div><p class='note'>判準：年化 ＞ 0050 且 年化÷|回落| ≥ 0050 ⇒ 合格；只過第一條 ⇒ 另列。分段是同一條 2005-02 起的權益曲線切出來讀。</p>")
    Q = S["品質"]
    H.append("<h2>二、差異來源</h2><ul class='note'>"
             f"<li>加上櫃後，窗內多出的訊號幾乎都是上櫃期間的訊號（見表「訊號數（上櫃期）」）；上櫃期買進占比是 200 顆所有買進中，買在上櫃期間的比例。</li>"
             f"<li>上櫃股 {S['O 版面']['上櫃股']}；轉上市股原本只把上櫃時期當歷史，現在上櫃期間也可以買。</li>"
             f"<li>上櫃減資事件（剔除與截斷）：{e(json.dumps(S['O 版面']['上櫃 R8 事件'], ensure_ascii=False))}；2007～2012 是偵測、非官方。</li></ul>")
    H.append("<h2>三、上櫃早年資料品質</h2>")
    cov = {r["市場"]: r for r in Q["覆蓋（全期）"]}
    H.append("<div class='wrap'><table><tr><th class='l'>市場</th><th>相鄰 K 棒</th><th>還原前<br><small>跌逾 7.5%</small></th><th>還原後</th><th>還原覆蓋率</th></tr>" +
             "".join(f"<tr><td class='l'>{'上櫃' if m == 'tpex' else '上市'}</td><td>{int(r['相鄰K棒']):,}</td><td>{int(r['還原前'])}</td><td>{int(r['還原後'])}</td><td>{P_(r['覆蓋率'])}</td></tr>" for m, r in cov.items())
             + "</table></div>")
    H.append("<p class='note'>2015-06 以前漲跌幅 7%，相鄰兩個交易日收盤跌超過 7.5% 幾乎一定是除權息、減資或資料問題；還原後還剩下的就是沒被還原到的。減資事件日已扣掉。</p>")
    qo = QY[QY["市場"] == "tpex"]
    H.append("<div class='wrap'><table><tr><th>年</th><th>上櫃還原前</th><th>還原後</th><th>覆蓋率</th></tr>" +
             "".join(f"<tr><td>{r['年']}</td><td>{int(r['還原前'])}</td><td>{int(r['還原後'])}</td><td>{P_(r['覆蓋率'])}</td></tr>" for _, r in qo.iterrows()) + "</table></div>")
    bb = Q["壞根斷點"]
    H.append("<ul class='note'>" + "".join(f"<li>{e(k)}：{v['檔']} 檔、壞根 {v['壞根']}（每萬根 {v['每萬根壞根']:.1f}）、斷點 {v['斷點']}</li>" for k, v in bb.items())
             + f"<li>上櫃除權息事件（≤2014）逐年：{e(json.dumps(Q['還原事件']['上櫃除權息事件（≤2014，逐年）'], ensure_ascii=False))}；2007-07～12 沒有資料（照報、不推估）。</li></ul>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, "早年段加上櫃重跑.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "a", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(a, log)
    elif a.page:
        page(log)
    else:
        run(a, log)
        page(log)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG外部三件 之 X1 多因子（FinLab 2026 公開文〈多因子選股策略教學〉）——回測線落地。
判準＝台股策略線 外部研究三件 登錄 seq1（sha d412ffe18178b3be，2026-09-27 17:08）§二；裁定 seq239、seq241、seq242、seq245 §二（X1：取原文程式逐條照做）、
      seq275（等 A0 2019～2026 全補齊才跑）；資料庫 2026-10-04 10:23（A0 全部完成）。X2、X3 已交（9e752a6247，researchExt.py）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExtX1 [--procs 4] [--reps 1000]
    抽樣查核：同一支加 --check（⛔ 查核段不呼叫本體的因子、可用日、換股簿函式，自己從原始 CSV 重算）

⭐ 讀法寫死時間：2026-10-04 11:40（台北）；寫死前 ⛔ 沒看任何本件在本專案母體上的數字（原文公開數字 +29.45%／−26.07% 已讀過，登錄已聲明）。
⚠ 沿革（照實記）：11:42～11:52 以假訊號 2 次試跑＋試跑 --check（測程式）；11:42 修一個 pandas 唯讀陣列錯誤（程式錯、非讀法）；
  試跑 --check 的輸出顯示了早年段主格的年化／回落（主格不受假訊號次數影響 ⇒ 等於看過判定數字）；之後讀法 ⛔ 一字未改，正式跑只把假訊號改回 1,000 次。

═══「原始碼」是什麼（狀態檔「X1 等財報與原始碼」）═══
  ＝ FinLab 公開文附的 strategy.py（https://www.finlab.finance/blog/multi-factor-stock-selection-beat-0050/strategy.py，5.1KB，2026-10-04 11:5x 以網頁讀取取得全文）
  ⭐ 已取得 ⇒ 照裁定 seq245 §二「逐條照原文程式」；與登錄 §二文字不同處以原文為準（下列「與登錄差異」）。⛔ 本線沒有 finlab 套件、⛔ 沒有執行原文程式；只照它的算式自寫。
  原文程式要點（摘述）：
    rev ＝ monthly_revenue「去年同月增減(%)」；roe ＝ fundamental_features「ROE稅後」.index_str_to_date()（對齊財報公布日）；
    monthly(df) ＝ reindex 到交易日 ffill 後取每月最後一筆；revm、momm ＝ close.pct_change(60)、roem、volm ＝ close.pct_change().rolling(60).std()（close ＝ price:收盤價）
    pool ＝ (revm ＞ 10) & (revm ＜ 150) & ((revm ＞ 0).rolling(3).sum() ＝＝ 3)
    rk(df) ＝ df.where(pool).rank(axis=1, pct=True[, ascending=False 用於低波動]).fillna(0)；score ＝ 四個 rk 相加
    mask ＝ score.rank(axis=1, ascending=False) ≤ 40；w ＝ (score 在 mask 內)² 正規化；sim(w, resample='M', resample_offset='14D')（手續費 0.1425%＋證交稅 0.3%）
  與登錄 §二文字的差異（以原文為準）：
    ①「連 3 個月營收正成長」＝ 連 3 個月【年增率 ＞ 0】（不是月增）；② 營收動能分數 ＝ 最新月營收年增率的池內百分位；
    ③ 價格動能、波動用【未還原】收盤（price:收盤價）；④ ROE 欄 ＝ FinLab「ROE稅後」（公式不在程式裡，見 K4）；⑤ 換股 ＝ 月底資料、延後 14 天換股

═══ 本線落地讀法（⭐ 看數字前寫死；原文沒寫清楚、本線自補者標「執行者補」）═══
  K1 母體 ＝ 三道閘（UG.gate3：main 快照名冊、排除 -DR、排除 -創）、含已下市股（登錄 §一）；⛔ 不加 W1 流動性條件（原文用全市場）
  K2 月底 me(m) ＝ 該月最後一個交易日；因子都在 me(m) 收盤後計算（只用 ≤ me(m) 的資料）
  K3 revm(m) ＝ 期別 m−1 的「去年同月增減(%)」（公告當時值；裁定 1054 營收口徑）——期別 p 的可得日 ＝ 次月 10 日（原文 FinLab 月營收以公布期限對齊，
     執行者補：與 research34.rebalance_dates pub_day 10 同口徑）⇒ 月底 m 最新可得 ＝ m−1；該期空白 ⇒ NaN（⚠ FinLab resample.last() 遇空白會拿當月較早一筆，
     本線不補，執行者補）；pool 用 m−1、m−2、m−3 三期
  K4 roem(m) ＝ 可用日 ≤ me(m) 的最新一季 ROE；ROE ＝ 單季歸屬母公司淨利 ÷ 該季與前一季期末母公司權益平均（母公司欄空 ⇒ 本期淨利／權益總計，seq214 ②）
     （執行者補：FinLab「ROE稅後」公式不在原文程式裡，取其季頻、稅後、平均權益的字面；只拿來排名，年化與否不影響）
     單季 ＝ 累計相減（Q4 ＝ 全年 − Q3 累計）；財報 ＝ fin_hist（main 1fb8815e81，含已下市）
     ⭐ 可用日 ＝ 大師三套 A0（登錄 §二）：t57sb01 該季【最早】上傳日期的下一個交易日（盤中盤後不分，同 researchMaster4 讀法）；
     缺時戳（2019 年以前幾乎全部、2019～2020 少數 Q1／Q3）⇒ A2 補位：法定期限之後第一個交易日再往後 5 個交易日（裁定 seq245 §三的 A2「其餘」口徑；
     執行者補：不用法定期限下一交易日，因 seq231 禁 A1）；⚠ 早年段（2013～2017）全部是補位 ⇒ 結果句必附
  K5 momm(m) ＝ 未還原收盤 c[me]／c[me−60] − 1（交易日曆上 60 根、收盤 ffill，同 pandas pct_change 預設補值）；
     volm(m) ＝ 未還原收盤日報酬（ffill 後）最近 60 個的樣本標準差（ddof＝1）；me(m) 當天須有成交（執行者補：避免下市後 ffill 出 0 波動）
     另報「還原價版」（描述）
  K6 排名：池內百分位（pandas rank pct=True、average）、不在池內或因子缺 ⇒ 0；score 四項相加；
     全母體 score 由大到小 rank（average）≤ 40 入選；權重 ∝ score²（原文逐字）
  K7 換股日 e ＝ me(m) 曆日 ＋14 天當天或之後第一個交易日；e 開盤依目標權重整批調整（原文每月調回目標權重，含續抱者）；
     ⚠ 原文 sim 的成交價口徑沒寫進程式 ⇒ 用本專案慣例「換股日開盤」（登錄 §一 進場欄）
  K8 換股簿（自寫，含成本與成交限制）：e 開盤以開盤價計值 ⇒ 先賣（落選與超配）後買（新選與不足）；
     成本 買 0.1425%、賣 0.4425%（來回 0.585%＝原文 0.1425%＋0.3% 同級）；開盤漲停／停牌買不到 ⇒ 該部分持現金、⛔ 不遞補；
     開盤跌停／停牌賣不掉 ⇒ 之後每天開盤再試；停止交易（最後有效收盤 L ＜ 段尾、之後再也沒有）⇒ L＋1 以 L 收盤了結、扣成本；逐日收盤（還原、ffill）計值
     ⭐ 持股計值與成交用【還原】價（報酬才對）；只有因子 K5 照原文用未還原價
  K9 窗：
     判定窗（原文期間外；登錄 §二）＝ 早年段，兩段串接（各段期初全現金、段內一條權益、段間逐日報酬接起來；品質件 B10 同法）：
       早年甲 ＝ 早年版面 ~/earlydata/3edc0e2206/main（只上市；2014-12-31 止），起點 ＝ ROE 在池內可算比例首次 ≥ 90% 的月底之後第一個換股日（執行者補）
       早年乙 ＝ 主快照（上市＋上櫃），起點 ＝ 月營收 2015-01 起、pool 需三期 ⇒ 第一個有池的換股日，～2017-12-29
       早年段可得年數 ≥ 3 才判（登錄）；2026-07～2026-08（2 個月）只描述，⛔ 不併入判定（執行者補：太短算不出年化）
     描述：原文期間 2018-01-02～2026-06-30（同一條主快照權益切段）；含已下市 vs 只含存活股
  K10 判定：使用者判準（對 0050 同窗：年化 ＞ 0050 且 比值 ≥ 0050 比值 ⇒ 合格；只過前者 ⇒ 另列）；N_組合 ＋1（seq245 發號）
  K11 假訊號（新預設，同池隨機）：每個換股日從當月 pool 不放回隨機抽 min(40, 池數) 檔、等權（不用分數平方：分數就是被拿掉的東西）；
      1,000 次（default_rng([20261004, 1, r])）；p ＝ 隨機年化 ≥ 本格的比例；判定窗與原文期間各報
  K12 描述：換股頻率 季（3、6、9、12 月底資料）／半年（6、12 月底）（登錄 §一、seq241 ②）；還原價版；只含存活股版；月分群（逐月超額對 0050、以月為群 95% t 區間）；
      現實版（researchSlip 定義落到換股簿：C1 每邊 ＋0.3%、C2 50 萬：每筆 Q ＝ 50 萬 × 該筆金額 ÷ 前一日權益、單邊衝擊 σ20 √(Q÷ADV20)、C4 均價成交）
  K13 判定窗合格／另列 ⇒ 固定跟進出場敏感度（seq242 ②）：停損 −10／−20%（收盤 ≤ 進場價×(1−x) ⇒ 次日開盤賣、現金等下次換股）、
      停利 +30／+50% 賣半、檔數 5／10／20；⚠ 2ATR、時停 R0-40 本輪不做（執行者補）
  K14（裁定 seq290 追加，2026-10-04 13:0x）：--sens-lag 20 ⇒ 早年段 ROE 缺時戳補位改「法定期限＋20 交易日」、其餘一字不變、只重跑早年段主格；
      窗沿用主跑；標籤翻轉 ⇒ 對外寫「不可判定（可用日敏感）」，沒翻 ⇒「另列（弱）」；讀法時間由腳本當場 TZ=Asia/Taipei date 寫進 sens_lag20.json
輸出 backtest/resultsExtX1/
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                # D.DATA ⇒ edc6f8002f 快照；chdir ⇒ repo
D, TR, UG, R = H2.D, H2.TR, H2.UG, H2.R
from backtest import research13 as R13

OUT = "backtest/resultsExtX1"
MS_SHA = "1fb8815e81aa53edf91aacb8ebb4125c716ead3f"
FD = os.path.expanduser(f"~/msdata/{MS_SHA}/data")
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
TAGT = "2026-10-04 11:40（台北）"
BUY_C, SELL_C = 0.001425, 0.004425
NPICK = 40
A2_LAG = 5                                             # 缺時戳補位：法定期限之後第一個交易日 ＋A2_LAG 個交易日（主格 5；--sens-lag 只改這一個數）
ORIG = ("2018-01-02", "2026-06-30")
TAIL = ("2026-07-01", "2026-08-24")
MAIN_END = "2026-08-24"
ANCHOR = (0.24020209886370614, -0.3395700527611012)
_G: dict = {}


def deadline(y, q):
    return pd.Timestamp(f"{y + 1}-03-31") if q == 4 else pd.Timestamp(f"{y}-{('05-15', '08-14', '11-14')[q - 1]}")


# ═════════════ ROE（季）與 A0 可用日 ═════════════
def load_roe():
    cols = ["stock_id", "period", "ni_ytd", "nip_ytd", "equity_parent", "equity_total"]
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=cols) for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv")))])
    F = F.drop_duplicates(["stock_id", "period"], keep="last")
    for c in cols[2:]:
        F[c] = pd.to_numeric(F[c], errors="coerce")
    F["p"] = F["period"].str[:4].astype(int) * 4 + F["period"].str[-1].astype(int) - 1
    K = {(s, p): r for s, p, r in zip(F["stock_id"], F["p"], F[cols[2:]].to_numpy(float))}
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fd["ts"] = pd.to_datetime(fd["uploaded_at"], errors="coerce")
    TS = {(s, int(y) * 4 + int(q) - 1): t.normalize() for (s, y, q), t in fd.dropna(subset=["ts"]).groupby(["stock_id", "year", "season"])["ts"].min().items()}
    rows = []
    for (s, p), r in K.items():
        ni_y, nip_y, ep, et = r
        prv = K.get((s, p - 1))
        q0 = p % 4

        def single(i):
            cur = r[i]
            if q0 == 0:
                return cur
            pr = K.get((s, p - 1))
            return cur - pr[i] if pr is not None else np.nan
        nip = single(1); ni = single(0)
        roe = np.nan; src = ""
        if prv is not None and np.isfinite(nip) and np.isfinite(ep) and np.isfinite(prv[2]):
            a = (ep + prv[2]) / 2; roe = nip / a if a > 0 else np.nan; src = "parent"
        elif prv is not None and np.isfinite(ni) and np.isfinite(et) and np.isfinite(prv[3]):
            a = (et + prv[3]) / 2; roe = ni / a if a > 0 else np.nan; src = "total"
        rows.append((s, p, roe, src, TS.get((s, p))))
    return pd.DataFrame(rows, columns=["sid", "p", "roe", "src", "ts"])


def roe_avail(RO, cal):
    """每列可用日位置：時戳 ⇒ 上傳日之後第一個交易日；缺 ⇒ 法定期限之後第一個交易日 ＋5。"""
    pos = np.empty(len(RO), int); src = []
    for i, (p, ts) in enumerate(zip(RO["p"], RO["ts"])):
        if ts is not None and not pd.isna(ts):
            pos[i] = int(cal.searchsorted(pd.Timestamp(ts), side="right")); src.append("ts")
        else:
            y, q0 = divmod(int(p), 4)
            pos[i] = int(cal.searchsorted(deadline(y, q0 + 1), side="right")) + A2_LAG; src.append("a2")
    return pos, np.array(src)


# ═════════════ 世界 ═════════════
def load_rev(dirs):
    fs = []
    for d in dirs:
        fs += sorted(glob.glob(os.path.join(d, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "去年同月增減(%)"]) for f in fs])
    df["yoy"] = pd.to_numeric(df["去年同月增減(%)"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    return df.pivot(index="period", columns="stock_id", values="yoy").sort_index()


def _init(cal, data):
    D.DATA = data; _G["cal"] = cal


def load_px(args):
    s, mk = args
    cal = _G["cal"]
    st = D.load_stock(s, mk, cal)
    if st is None:
        return s, None
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    rc = np.array(pd.to_numeric(raw["close"], errors="coerce"), dtype=float); rc[~(rc > 0)] = np.nan
    rc = pd.Series(rc, pd.to_datetime(raw["date"])).reindex(cal).to_numpy(float)
    c = st.df["close"].to_numpy(float)
    tb = TR.one(s, cal)
    return s, {"c": pd.Series(c).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "valid": np.isfinite(c),
               "rc": pd.Series(rc).ffill().to_numpy(float), "rvalid": np.isfinite(rc),
               "trd": np.asarray(tb["trd"], bool), "up_o": np.asarray(tb["up_o"], bool), "dn_o": np.asarray(tb["dn_o"], bool)}


def build_world(name, data, rev_dirs, w_end, procs, log, RO):
    D.DATA = data
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    with Pool(procs, initializer=_init, initargs=(cal, data)) as pool:
        P = dict(pool.map(load_px, list(zip(G["stock_id"], G["market"])), chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    sids = sorted(P)
    w1 = int(cal.searchsorted(pd.Timestamp(w_end), side="right") - 1)
    dl = TR.delist_status({s: {"trd": P[s]["trd"]} for s in sids}, cal, official=TR.load_official())
    SF = {}
    for s in sids:
        b = np.flatnonzero(P[s]["valid"])
        if len(b) and b[-1] < w1:
            SF[s] = int(b[-1])
    rev = load_rev(rev_dirs)
    ym = cal.year * 12 + cal.month
    mends = [int(np.flatnonzero(ym == m)[-1]) for m in np.unique(ym)]
    mends = [t for t in mends if t <= w1]
    # ROE 可用位置（本世界日曆）
    pos, src = roe_avail(RO, cal)
    RO = RO.assign(pos=pos, asrc=src)
    RO = RO[RO["sid"].isin(set(sids))].sort_values(["sid", "pos", "p"])
    byS = {s: (g["pos"].to_numpy(), g["p"].to_numpy(), g["roe"].to_numpy(float), g["asrc"].to_numpy()) for s, g in RO.groupby("sid")}
    RC = np.column_stack([P[s]["rc"] for s in sids]); RV = np.column_stack([P[s]["rvalid"] for s in sids])
    AC = np.column_stack([P[s]["c"] for s in sids]); AV = np.column_stack([P[s]["valid"] for s in sids])
    with np.errstate(invalid="ignore", divide="ignore"):
        RR_ = RC[1:] / RC[:-1] - 1.0; AR_ = AC[1:] / AC[:-1] - 1.0
    XS = {}
    for t in mends:
        m = int(ym[t]); per = [f"{(m - k - 1) // 12}-{(m - k - 1) % 12 + 1:02d}" for k in (1, 2, 3)]
        if not all(p_ in rev.index for p_ in per):
            continue
        y1, y2, y3 = (rev.loc[p_] for p_ in per)
        d = {}
        if t < 61:
            continue
        mom = RC[t] / RC[t - 60] - 1.0; vol = np.nanstd(RR_[t - 60:t], axis=0, ddof=1)
        mom_a = AC[t] / AC[t - 60] - 1.0; vol_a = np.nanstd(AR_[t - 60:t], axis=0, ddof=1)
        nn = np.sum(np.isfinite(RR_[t - 60:t]), axis=0)
        roe_d = {}; asrc_d = {}
        for s in sids:
            if s in byS:
                ps, pp, rr, aa = byS[s]
                k = int(np.searchsorted(ps, t, side="right"))
                if k:
                    j = int(np.argmax(pp[:k])); roe_d[s] = rr[j]; asrc_d[s] = aa[j]
        rows = []
        for i, s in enumerate(sids):
            a1, a2, a3 = y1.get(s, np.nan), y2.get(s, np.nan), y3.get(s, np.nan)
            inpool = bool(np.isfinite(a1) and 10 < a1 < 150 and a1 > 0 and np.isfinite(a2) and a2 > 0 and np.isfinite(a3) and a3 > 0 and RV[t, i])
            rows.append((s, inpool, a1, mom[i], roe_d.get(s, np.nan), vol[i] if nn[i] >= 60 else np.nan, mom_a[i], vol_a[i] if nn[i] >= 60 else np.nan,
                         asrc_d.get(s, "")))
        df = pd.DataFrame(rows, columns=["sid", "pool", "rev", "mom", "roe", "vol", "mom_a", "vol_a", "asrc"]).set_index("sid")
        XS[t] = df
    e_of = {}
    for t in XS:
        e = int(cal.searchsorted(cal[t] + pd.Timedelta(days=14)))
        if e <= w1:
            e_of[t] = e
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    log(f"[世界 {name}] {data}｜日曆 {cal[0].date()}～{cal[-1].date()}｜gate3 {len(G):,}、可讀 {len(sids):,}｜月底截面 {len(XS)}（{cal[min(XS)].date()}～{cal[max(XS)].date()}）｜停止交易 {len(SF)}")
    return {"name": name, "cal": cal, "n": n, "P": P, "sids": sids, "dl": dl, "SF": SF, "XS": XS, "e_of": e_of, "w1": w1, "bench": bench}


# ═════════════ 選股 ═════════════
def score_table(df, adj=False):
    pool = df["pool"].to_numpy(bool)
    out = np.zeros(len(df))
    for col, asc in (("rev", True), ("mom_a" if adj else "mom", True), ("roe", True), ("vol_a" if adj else "vol", False)):
        x = df[col].where(pool)
        out += x.rank(pct=True, ascending=asc).fillna(0).to_numpy()
    return pd.Series(out, df.index)


def weights_at(df, N=NPICK, adj=False, surv=None):
    if surv is not None:
        df = df[df.index.isin(surv)]
    sc = score_table(df, adj)
    rk = sc.rank(ascending=False)
    m = rk <= N
    w = sc.where(m, 0.0) ** 2
    tot = w.sum()
    return {} if tot <= 0 else {s: float(v / tot) for s, v in w.items() if v > 0}


def schedule(W, months=None, **kw):
    """{e: 目標權重}；months ＝ 月底所在月份的集合（季：3、6、9、12）。"""
    out = {}
    for t, e in sorted(W["e_of"].items()):
        if months is not None and W["cal"][t].month not in months:
            continue
        out[e] = weights_at(W["XS"][t], **kw)
    return out


# ═════════════ 換股簿 ═════════════
def book(W, sched, t0, t1, extra=0.0, real=None, stop=None, tp=None):
    """逐日：e 開盤調到目標權重。回 (權益, 統計)。real ＝ (X 表, 資金) ⇒ C2 衝擊＋C4 均價；extra ＝ 每邊加成本。"""
    P, SF, dl = W["P"], W["SF"], W["dl"]
    n = W["n"]; eq = np.ones(n); cash = 1.0; units = {}; ep = {}; half = set()
    pend_sell = {}; cnt = {"buy": 0, "sell": 0, "limit_up": 0, "halt_buy": 0, "sell_delayed": 0, "stop_force": 0, "delist": 0, "stop": 0, "tp": 0}
    turn = []; costsum = 0.0; npos = []
    bc, sc = BUY_C + extra, SELL_C + extra
    Xr, cap = (real if real else (None, None))

    def px_buy(s, t):
        if Xr is not None and Xr.get(s) is not None and np.isfinite(Xr[s]["avg"][t]):
            return Xr[s]["avg"][t]
        return P[s]["o"][t]

    def impact(s, t, amt, eqp):
        if Xr is None or Xr.get(s) is None:
            return 0.0
        a = Xr[s]["adv20"][t]; sg = Xr[s]["sig20"][t]
        if not (np.isfinite(a) and a > 0 and np.isfinite(sg)):
            return 0.0
        return min(float(sg * math.sqrt(cap * amt / eqp / a)), 0.99)

    def sell(s, t, frac=1.0, px=None, force=False):
        nonlocal cash, costsum
        x = P[s]
        if px is None:
            o = px_buy(s, t)
            if not (x["trd"][t] and not x["dn_o"][t] and np.isfinite(o) and o > 0):
                return False
            px = o
            px *= 1 - impact(s, t, units[s] * frac * px, max(eq[t - 1], 1e-12))
        u = units[s] * frac; v = u * px
        c = v * sc; cash += v - c; costsum += c
        units[s] -= u
        if units[s] <= 1e-15 or frac >= 1.0:
            units.pop(s, None); ep.pop(s, None); half.discard(s)
        cnt["sell"] += 1
        return True
    for t in range(t0, t1 + 1):
        # 停止交易／下市了結
        for s in list(units):
            if (s in SF and t > SF[s]):
                sell(s, t, px=P[s]["c"][t]); cnt["stop_force"] += 1; pend_sell.pop(s, None)
        # 延後的賣單
        for s in list(pend_sell):
            if s not in units:
                pend_sell.pop(s); continue
            if sell(s, t, frac=pend_sell[s]):
                pend_sell.pop(s)
            else:
                cnt["sell_delayed"] += 1
        # 停損／停利（前一日收盤觸發 ⇒ 今日開盤）
        if (stop or tp) and t > t0:
            for s in list(units):
                if s in pend_sell:
                    continue
                c1 = P[s]["c"][t - 1]
                if stop and P[s]["valid"][t - 1] and c1 <= ep[s] * (1 - stop):
                    cnt["stop"] += 1
                    if not sell(s, t):
                        pend_sell[s] = 1.0
                elif tp and s not in half and P[s]["valid"][t - 1] and c1 >= ep[s] * (1 + tp):
                    cnt["tp"] += 1; half.add(s)
                    if not sell(s, t, frac=0.5):
                        pend_sell[s] = 0.5
        tw = sched.get(t)
        if tw is not None:
            ov = {s: units[s] * (P[s]["o"][t] if np.isfinite(P[s]["o"][t]) and P[s]["o"][t] > 0 else P[s]["c"][t - 1]) for s in units}
            eqo = cash + sum(ov.values())
            tgt = {s: w * eqo for s, w in tw.items()}
            traded = 0.0
            for s in sorted(units):                                   # 先賣
                want = tgt.get(s, 0.0)
                if ov[s] > want + 1e-12:
                    frac = 1.0 if want <= 0 else (ov[s] - want) / ov[s]
                    if sell(s, t, frac=frac):
                        traded += ov[s] - want
                    else:
                        pend_sell[s] = frac if want <= 0 else frac
                        cnt["sell_delayed"] += 1
            for s in sorted(tgt, key=lambda z: -tgt[z]):              # 後買（權重大者先）
                have = units.get(s, 0.0) * (P[s]["o"][t] if (s in units and np.isfinite(P[s]["o"][t])) else 0.0)
                need = tgt[s] - have
                if need <= 1e-12:
                    continue
                x = P[s]; o = px_buy(s, t)
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or (s in SF and t > SF[s]):
                    cnt["halt_buy"] += 1; continue
                if x["up_o"][t]:
                    cnt["limit_up"] += 1; continue
                amt = min(need, cash / (1 + bc))
                if amt <= 1e-12:
                    break
                o2 = o * (1 + impact(s, t, amt, max(eq[t - 1], 1e-12)))
                c = amt * bc; cash -= amt + c; costsum += c
                u0 = units.get(s, 0.0); u1 = amt / o2
                ep[s] = (ep.get(s, o2) * u0 + o2 * u1) / (u0 + u1) if s in units else o2
                units[s] = u0 + u1; traded += amt; cnt["buy"] += 1
            turn.append(traded / eqo if eqo > 0 else np.nan)
        eq[t] = cash + sum(u * P[s]["c"][t] for s, u in units.items())
        npos.append(len(units))
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    return eq, {"cnt": cnt, "換手（每次調整金額÷權益）": float(np.nanmean(turn)) if turn else np.nan, "平均持股": float(np.mean(npos)), "成本合計（期初＝1）": costsum}


def wst(eq, a, b):
    c, m = R13.window_stats(np.asarray(eq, float), 0, len(eq), a, b + 1)
    return float(c), float(m)


def chain(parts):
    out = []; lvl = 1.0
    for eq, a, b in parts:
        seg = np.asarray(eq[a:b + 1], float) / eq[a] * lvl; out.append(seg); lvl = seg[-1]
    return np.concatenate(out)


def cst(arr):
    c, m = R13.window_stats(arr, 0, len(arr), 0, len(arr))
    return float(c), float(m)


def label(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def mci(arr, barr, dates):
    a = pd.Series(arr, pd.DatetimeIndex(dates)).resample("ME").last(); b = pd.Series(barr, pd.DatetimeIndex(dates)).resample("ME").last()
    a = pd.concat([pd.Series([arr[0]]), a.reset_index(drop=True)]); b = pd.concat([pd.Series([barr[0]]), b.reset_index(drop=True)])
    x = (a.pct_change() - b.pct_change()).dropna().to_numpy()
    k = len(x); m = float(np.mean(x)); se = float(np.std(x, ddof=1) / math.sqrt(k))
    return {"月數": k, "月超額平均": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se}


def _fake(args):
    r = args
    out = {"r": r}
    rng = np.random.default_rng([20261004, 1, r])
    eqs = {}
    for wn in ("A", "B"):
        W = _G[wn]; sc = {}
        for t, e in sorted(W["e_of"].items()):
            df = W["XS"][t]; pool = sorted(df.index[df["pool"].to_numpy(bool)])
            pick = list(rng.choice(pool, size=min(NPICK, len(pool)), replace=False)) if pool else []
            sc[e] = {s: 1.0 / len(pick) for s in pick}
        a, b = _G["SEG"][wn]
        eqs[wn] = book(W, sc, a, b)[0]
    arr = chain([(eqs["A"], *_G["SEG"]["A"]), (eqs["B"], *_G["SEG"]["B"])])
    out["早年_年化"], out["早年_回落"] = cst(arr)
    return out


def _fake_orig(args):
    r = args
    rng = np.random.default_rng([20261004, 2, r])
    W = _G["B"]; sc = {}
    for t, e in sorted(W["e_of"].items()):
        df = W["XS"][t]; pool = sorted(df.index[df["pool"].to_numpy(bool)])
        pick = list(rng.choice(pool, size=min(NPICK, len(pool)), replace=False)) if pool else []
        sc[e] = {s: 1.0 / len(pick) for s in pick}
    a, b = _G["SEG"]["orig"]
    eq = book(W, sc, _G["SEG"]["B"][0], W["w1"])[0]
    return {"r": r, "原文期間_年化": wst(eq, a, b)[0], "原文期間_回落": wst(eq, a, b)[1]}


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--sens-lag", type=int, default=None); a = ap.parse_args()
    if a.check:
        return check()
    if a.sens_lag is not None:
        return sens_lag(a)
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchExtX1（PREREG外部三件 X1 多因子）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TAGT} =====")
    S = {"登錄": "PREREG外部三件 seq1 sha d412ffe18178b3be §二；裁定 seq239、241、242、245 §二、275", "讀法寫死": TAGT,
         "原始碼": "FinLab 公開文附 strategy.py（已取得全文；照算式自寫，未執行原文程式）", "必附": "出處為公開研究、原文數字未必可重現"}
    RO = load_roe()
    S["ROE 列"] = {"季數": int(len(RO)), "可算": int(RO["roe"].notna().sum()), "有 A0 時戳": int(RO["ts"].notna().sum()), "母公司版": int((RO["src"] == "parent").sum())}
    WB = build_world("主快照", H2.H2D, [H2.H2D], MAIN_END, a.procs, log, RO)
    WA = build_world("早年版面", EARLY, [EARLY], "2014-12-31", a.procs, log, RO)
    D.DATA = H2.H2D
    # 0050 錨
    calB = WB["cal"]; m0 = int(calB.searchsorted(pd.Timestamp("2017-03-02"))); m1 = int(calB.searchsorted(pd.Timestamp(MAIN_END), side="right") - 1)
    ca, ma = R13.window_stats(WB["bench"], 0, WB["n"], m0, m1 + 1)
    S["閘"] = {"0050 主窗錨逐位元": repr(float(ca)) == repr(ANCHOR[0]) and repr(float(ma)) == repr(ANCHOR[1])}
    if not S["閘"]["0050 主窗錨逐位元"]:
        raise SystemExit("⛔ 0050 錨")
    # 早年甲起點：ROE 在池內可算比例首次 ≥ 90% 的月底
    cov = {t: float(df.loc[df["pool"], "roe"].notna().mean()) if df["pool"].any() else 0.0 for t, df in WA["XS"].items()}
    tA = min(t for t, v in cov.items() if v >= 0.90 and t in WA["e_of"])
    a0 = WA["e_of"][tA]; a1 = WA["w1"]
    tB = min(t for t, df in WB["XS"].items() if df["pool"].any() and t in WB["e_of"])
    b0 = WB["e_of"][tB]; b1 = int(calB.searchsorted(pd.Timestamp("2017-12-29"), side="right") - 1)
    o0 = int(calB.searchsorted(pd.Timestamp(ORIG[0]))); o1 = int(calB.searchsorted(pd.Timestamp(ORIG[1]), side="right") - 1)
    z0 = int(calB.searchsorted(pd.Timestamp(TAIL[0]))); z1 = WB["w1"]
    yrsE = (a1 - a0 + 1 + b1 - b0 + 1) / 245
    S["窗"] = {"早年甲（早年版面、只上市）": [str(WA["cal"][a0].date()), str(WA["cal"][a1].date())], "早年乙（主快照）": [str(calB[b0].date()), str(calB[b1].date())],
              "早年段年數": yrsE, "可判定（≥ 3 年）": yrsE >= 3, "原文期間（描述）": [str(calB[o0].date()), str(calB[o1].date())],
              "原文期間後（描述）": [str(calB[z0].date()), str(calB[z1].date())], "早年甲 ROE 池內可算比例（起點月）": cov[tA]}
    log(f"[窗] {S['窗']}")
    _G.update(A=WA, B=WB, SEG={"A": (a0, a1), "B": (b0, b1), "orig": (o0, o1)})
    # 0050
    bE = chain([(WA["bench"], a0, a1), (WB["bench"], b0, b1)]); c0E, m0E = cst(bE)
    c0O, m0O = wst(WB["bench"], o0, o1); c0Z, m0Z = wst(WB["bench"], z0, z1)
    S["0050"] = {"早年段": [c0E, m0E, c0E / abs(m0E)], "原文期間": [c0O, m0O, c0O / abs(m0O)], "原文期間後": [c0Z, m0Z]}
    # ── 主格（月換）
    schA = schedule(WA); schB = schedule(WB)
    eqA, stA = book(WA, schA, a0, a1); eqB, stB = book(WB, schB, b0, WB["w1"])
    arr = chain([(eqA, a0, a1), (eqB, b0, b1)]); cE, mE = cst(arr)
    labE = label(cE, mE, c0E, m0E)
    cO, mO = wst(eqB, o0, o1); cZ, mZ = wst(eqB, z0, z1)
    S["判定（早年段，月換主格）"] = {"年化": cE, "回落": mE, "比值": cE / abs(mE), "標籤": labE, "0050": [c0E, m0E], "A段統計": stA, "B段統計": stB}
    S["描述_原文期間 2018-01～2026-06"] = {"年化": cO, "回落": mO, "標籤（描述）": label(cO, mO, c0O, m0O), "原文": [0.2945, -0.2607], "0050": [c0O, m0O]}
    S["描述_2026-07～08"] = {"區間報酬": float(eqB[z1] / eqB[z0 - 1] - 1), "0050": float(WB["bench"][z1] / WB["bench"][z0 - 1] - 1)}
    log(f"[判定 早年段] {cE:+.2%}／{mE:+.2%}（{cE / abs(mE):.3f}）vs 0050 {c0E:+.2%}／{m0E:+.2%} ⇒ {labE}")
    # 池與持股
    S["池大小（中位）"] = {"早年甲": float(np.median([WA["XS"][t]["pool"].sum() for t in WA["e_of"] if WA["e_of"][t] >= a0])),
                       "早年乙": float(np.median([WB["XS"][t]["pool"].sum() for t in WB["e_of"] if b0 <= WB["e_of"][t] <= b1])),
                       "原文期間": float(np.median([WB["XS"][t]["pool"].sum() for t in WB["e_of"] if o0 <= WB["e_of"][t] <= o1]))}
    S["ROE 可用日來源（入選股）"] = {}
    for wn, W, lo, hi in (("早年", WA, a0, a1), ("早年乙", WB, b0, b1), ("原文期間", WB, o0, o1)):
        srcs = []
        for t, e in W["e_of"].items():
            if lo <= e <= hi:
                w = weights_at(W["XS"][t])
                srcs += list(W["XS"][t].loc[list(w), "asrc"])
        vc = pd.Series(srcs).value_counts().to_dict()
        S["ROE 可用日來源（入選股）"][wn] = {k: int(v) for k, v in vc.items()}
    # ── 描述臂
    dsc = {}
    for vn, kw in (("季換", {"months": {3, 6, 9, 12}}), ("半年換", {"months": {6, 12}}), ("還原價版（月）", {"adj": True})):
        sA, sB = schedule(WA, **kw), schedule(WB, **kw)
        ea, _ = book(WA, sA, a0, a1); eb, _ = book(WB, sB, b0, WB["w1"])
        c, m = cst(chain([(ea, a0, a1), (eb, b0, b1)])); co, mo = wst(eb, o0, o1)
        dsc[vn] = {"早年": [c, m, label(c, m, c0E, m0E)], "原文期間": [co, mo, label(co, mo, c0O, m0O)]}
    surv = {s for s in WB["sids"] if WB["dl"].get(s, {}).get("status", "live") == "live"}
    sS = schedule(WB, surv=surv); es, _ = book(WB, sS, b0, WB["w1"]); co, mo = wst(es, o0, o1)
    dsc["只含存活股（原文期間）"] = {"原文期間": [co, mo], "含已下市 − 只含存活（年化點）": (cO - co) * 100}
    from backtest import researchSlip as SL
    D.DATA = EARLY                                                          # 早年版面只有上市
    XA = {s: SL.stock_extra(s, "twse", WA["cal"], WA["n"]) for s in {x for v in schA.values() for x in v}}
    D.DATA = H2.H2D
    mkB = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
    XB = {s: SL.stock_extra(s, mkB.get(s, "twse"), calB, WB["n"]) for s in {x for v in schB.values() for x in v}}
    ea, _ = book(WA, schA, a0, a1, extra=0.003, real=(XA, 500_000)); eb, _ = book(WB, schB, b0, WB["w1"], extra=0.003, real=(XB, 500_000))
    c, m = cst(chain([(ea, a0, a1), (eb, b0, b1)])); co, mo = wst(eb, o0, o1)
    dsc["現實版（C1 0.3%＋C2 50 萬＋C4）"] = {"早年": [c, m, label(c, m, c0E, m0E)], "原文期間": [co, mo, label(co, mo, c0O, m0O)]}
    dates = list(WA["cal"][a0:a1 + 1]) + list(calB[b0:b1 + 1])
    dsc["月分群（早年段，逐月超額對 0050）"] = mci(arr, bE, dates)
    dsc["月分群（原文期間）"] = mci(eqB[o0:o1 + 1], WB["bench"][o0:o1 + 1], calB[o0:o1 + 1])
    S["描述"] = dsc
    # ── 假訊號
    with Pool(a.procs, initializer=_G.update, initargs=({},)) as pool:
        FK = pool.map(_fake, range(a.reps), chunksize=10)
        FO = pool.map(_fake_orig, range(a.reps), chunksize=10)
    FK = pd.DataFrame(FK).merge(pd.DataFrame(FO), on="r")
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
    S["假訊號（同池隨機 40 檔等權，1,000 次）"] = {"早年 p（隨機年化 ≥ 本格）": float((FK["早年_年化"] >= cE).mean()), "早年 隨機年化中位": float(FK["早年_年化"].median()),
                                         "早年 隨機合格比例": float(np.mean([label(c, m, c0E, m0E) == "合格" for c, m in zip(FK["早年_年化"], FK["早年_回落"])])),
                                         "原文期間 p": float((FK["原文期間_年化"] >= cO).mean()), "原文期間 隨機年化中位": float(FK["原文期間_年化"].median())}
    log(f"[假訊號] {S['假訊號（同池隨機 40 檔等權，1,000 次）']}")
    # ── 跟進出場敏感度
    if labE in ("合格", "另列"):
        sens = {}
        for vn, kw, N in (("停損 −10%", {"stop": 0.10}, NPICK), ("停損 −20%", {"stop": 0.20}, NPICK), ("停利 +30% 賣半", {"tp": 0.30}, NPICK),
                          ("停利 +50% 賣半", {"tp": 0.50}, NPICK), ("檔數 5", {}, 5), ("檔數 10", {}, 10), ("檔數 20", {}, 20)):
            sA, sB = (schedule(WA, N=N), schedule(WB, N=N)) if N != NPICK else (schA, schB)
            ea, _ = book(WA, sA, a0, a1, **kw); eb, _ = book(WB, sB, b0, WB["w1"], **kw)
            c, m = cst(chain([(ea, a0, a1), (eb, b0, b1)]))
            sens[vn] = [c, m, label(c, m, c0E, m0E)]
        sens["2ATR、時停 R0-40"] = "本輪未做（執行者補）"
        S["出場敏感度（seq242 ②，描述）"] = sens
    else:
        S["出場敏感度（seq242 ②，描述）"] = "判定窗不合格 ⇒ 不跟進"
    # 名單
    rows = []
    for wn, W, sch in (("早年版面", WA, schA), ("主快照", WB, schB)):
        for e, w in sorted(sch.items()):
            for s, v in sorted(w.items(), key=lambda z: -z[1]):
                rows.append({"世界": wn, "換股日": str(W["cal"][e].date()), "sid": s, "權重": v})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "picks.csv.gz"), index=False, float_format="%.17g")
    np.savez_compressed(os.path.join(OUT, "eq.npz"), A=eqA, B=eqB, early=arr)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


def sens_lag(a):
    """裁定 seq290：早年段 ROE 缺時戳補位改「法定期限＋a.sens_lag 交易日」、其餘一字不變，只重跑早年段主格（月換、40 檔、分數平方）。
    ⭐ 窗沿用主跑 summary.json 的早年甲／乙起訖（只改可用日；起點規則在新補位下會落在哪一天另報、⛔ 不用來改窗——執行者補）。
    輸出 resultsExtX1/sens_lag{N}.json；⛔ 不覆寫主跑的 summary／picks（--check 照舊）。"""
    global A2_LAG
    import subprocess
    ts = subprocess.run(["bash", "-c", "TZ=Asia/Taipei date '+%F %H:%M'"], capture_output=True, text=True).stdout.strip()
    A2_LAG = int(a.sens_lag)
    S0 = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    log = lambda m: print(m, flush=True)
    log(f"===== X1 敏感度：缺時戳補位 期限＋{A2_LAG}（主跑 ＋5）｜讀法時間 {ts}（台北，腳本當場 date）=====")
    RO = load_roe()
    WB = build_world("主快照", H2.H2D, [H2.H2D], MAIN_END, a.procs, log, RO)
    WA = build_world("早年版面", EARLY, [EARLY], "2014-12-31", a.procs, log, RO)
    D.DATA = H2.H2D
    pos = lambda W, d: int(np.searchsorted(W["cal"].values, np.datetime64(pd.Timestamp(d))))
    a0, a1 = (pos(WA, d) for d in S0["窗"]["早年甲（早年版面、只上市）"])
    b0, b1 = (pos(WB, d) for d in S0["窗"]["早年乙（主快照）"])
    cov = {t: float(df.loc[df["pool"], "roe"].notna().mean()) if df["pool"].any() else 0.0 for t, df in WA["XS"].items()}
    tA = min(t for t, v in cov.items() if v >= 0.90 and t in WA["e_of"])
    eqA, stA = book(WA, schedule(WA), a0, a1); eqB, stB = book(WB, schedule(WB), b0, WB["w1"])
    c, m = cst(chain([(eqA, a0, a1), (eqB, b0, b1)]))
    c0, m0 = cst(chain([(WA["bench"], a0, a1), (WB["bench"], b0, b1)]))
    lab = label(c, m, c0, m0); J = S0["判定（早年段，月換主格）"]
    srcs = []
    for W, lo, hi in ((WA, a0, a1), (WB, b0, b1)):
        for t, e in W["e_of"].items():
            if lo <= e <= hi:
                srcs += list(W["XS"][t].loc[list(weights_at(W["XS"][t])), "asrc"])
    out = {"讀法時間": f"{ts}（台北）", "依據": "裁定 seq290：早年段 ROE 可用日改法定期限＋20 交易日，其餘一字不變", "補位": f"法定期限之後第一個交易日 ＋{A2_LAG}",
           "窗（沿用主跑）": {"早年甲": S0["窗"]["早年甲（早年版面、只上市）"], "早年乙": S0["窗"]["早年乙（主快照）"]},
           "新補位下早年甲起點規則會落在": str(WA["cal"][WA["e_of"][tA]].date()),
           "早年段": {"年化": c, "回落": m, "比值": c / abs(m), "標籤（計算）": lab}, "0050": {"年化": c0, "回落": m0, "比值": c0 / abs(m0)},
           "主跑（＋5）": {"年化": J["年化"], "回落": J["回落"], "標籤（計算）": J["標籤"]},
           "標籤翻轉": lab != J["標籤"],
           "對外標籤（seq290）": "不可判定（可用日敏感）" if lab != J["標籤"] else "另列（弱）",
           "入選股 ROE 可用日來源": {k: int(v) for k, v in pd.Series(srcs).value_counts().items()}}
    json.dump(out, open(os.path.join(OUT, f"sens_lag{A2_LAG}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


# ═════════════ 抽樣查核（⛔ 不呼叫 load_roe／roe_avail／build_world／score_table／weights_at／book）═════════════
def check():
    """① 抽 12 個換股日：自讀月營收、未還原收盤、fin_hist、filing_dates（最早上傳日＋1 交易日；缺 ⇒ 期限＋1＋5）重算因子、排名、權重 ⇒ ＝ picks.csv.gz
    ② 自寫換股簿（同 K8 規則、另一份程式）由 picks 重算早年兩段串接權益 ⇒ 年化／回落 ＝ summary"""
    out = {"時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    PK = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str})
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    fin = {}
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv"))):
        for r in pd.read_csv(f, dtype=str).to_dict("records"):
            fin[(r["stock_id"], r["period"])] = r
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype=str)
    first = {}
    for s, y, q, u in zip(fd["stock_id"], fd["year"], fd["season"], fd["uploaded_at"]):
        d = pd.Timestamp(str(u)).normalize(); k = (s, f"{y}Q{q}")
        first[k] = min(first.get(k, d), d)

    def fnum(x):
        try:
            v = float(x)
            return v if np.isfinite(v) else np.nan
        except (TypeError, ValueError):
            return np.nan
    rng = np.random.default_rng(3)
    bad = []; nchk = 0; W = {}
    for wn, data in (("早年版面", EARLY), ("主快照", H2.H2D)):
        D.DATA = data
        cal = D.load_calendar(); calv = cal.values; n = len(cal)
        stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
        G = UG.gate3(stocks); mk = dict(zip(G["stock_id"], G["market"]))
        revf = sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
        rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "去年同月增減(%)"]) for f in revf]).drop_duplicates(["stock_id", "period"], keep="last")
        rvd = {(s, p): fnum(v) for s, p, v in zip(rv["stock_id"], rv["period"], rv["去年同月增減(%)"])}
        RAW = {}; ADJ = {}
        for s in sorted(mk):
            p = os.path.join(data, "stocks", f"{s}.csv")
            if not os.path.exists(p):
                continue
            st = D.load_stock(s, mk[s], cal)
            if st is None:
                continue
            raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
            rc = np.array(pd.to_numeric(raw["close"], errors="coerce"), dtype=float); rc[~(rc > 0)] = np.nan
            RAW[s] = pd.Series(rc, pd.to_datetime(raw["date"])).reindex(cal).to_numpy(float)
            ADJ[s] = (st.df["open"].to_numpy(float), st.df["close"].to_numpy(float))
        W[wn] = (cal, mk, RAW, ADJ)
        sub = PK[PK["世界"] == wn]
        dates = sorted(sub["換股日"].unique())
        ym = cal.year * 12 + cal.month
        for dstr in [dates[i] for i in sorted(rng.choice(len(dates), size=min(6, len(dates)), replace=False))]:
            e = int(np.searchsorted(calv, np.datetime64(pd.Timestamp(dstr))))
            t = [x for x in range(max(e - 40, 0), e) if (x + 1 < n and ym[x + 1] != ym[x])
                 and int(np.searchsorted(calv, np.datetime64(cal[x] + pd.Timedelta(days=14)))) == e][0]
            m = int(ym[t]); per = [f"{(m - k - 1) // 12}-{(m - k - 1) % 12 + 1:02d}" for k in (1, 2, 3)]
            df = []
            for s, rc in RAW.items():
                a1, a2, a3 = (rvd.get((s, p), np.nan) for p in per)
                inpool = bool(np.isfinite(a1) and 10 < a1 < 150 and np.isfinite(a2) and a2 > 0 and np.isfinite(a3) and a3 > 0 and np.isfinite(rc[t]))
                c = pd.Series(rc).ffill().to_numpy()
                mom = c[t] / c[t - 60] - 1
                rr = c[t - 60:t + 1][1:] / c[t - 60:t + 1][:-1] - 1
                vol = float(np.std(rr, ddof=1)) if np.isfinite(rr).all() else np.nan
                best = None
                for y in range(cal[t].year - 2, cal[t].year + 1):
                    for q in (1, 2, 3, 4):
                        k = (s, f"{y}Q{q}")
                        if k not in fin:
                            continue
                        if k in first:
                            av = int(np.searchsorted(calv, np.datetime64(first[k]), side="right"))
                        else:
                            dd = pd.Timestamp(f"{y + 1}-03-31") if q == 4 else pd.Timestamp(f"{y}-{('05-15', '08-14', '11-14')[q - 1]}")
                            av = int(np.searchsorted(calv, np.datetime64(dd), side="right")) + 5
                        if av <= t and (best is None or (y, q) > best):
                            best = (y, q)
                roe = np.nan
                if best is not None:
                    y, q = best
                    py, pq = (y, q - 1) if q > 1 else (y - 1, 4)
                    cur, prv = fin[(s, f"{y}Q{q}")], fin.get((s, f"{py}Q{pq}"))
                    if prv is not None:
                        def sq(col):
                            return fnum(cur[col]) if q == 1 else fnum(cur[col]) - fnum(prv[col])
                        nip, ni = sq("nip_ytd"), sq("ni_ytd")
                        ep, ep0 = fnum(cur["equity_parent"]), fnum(prv["equity_parent"])
                        et, et0 = fnum(cur["equity_total"]), fnum(prv["equity_total"])
                        if np.isfinite(nip) and np.isfinite(ep) and np.isfinite(ep0):
                            a_ = (ep + ep0) / 2; roe = nip / a_ if a_ > 0 else np.nan
                        elif np.isfinite(ni) and np.isfinite(et) and np.isfinite(et0):
                            a_ = (et + et0) / 2; roe = ni / a_ if a_ > 0 else np.nan
                df.append((s, inpool, a1, mom, roe, vol))
            X = pd.DataFrame(df, columns=["sid", "pool", "rev", "mom", "roe", "vol"]).set_index("sid")
            sc = np.zeros(len(X))
            for col, asc in (("rev", True), ("mom", True), ("roe", True), ("vol", False)):
                sc += X[col].where(X["pool"]).rank(pct=True, ascending=asc).fillna(0).to_numpy()
            sc = pd.Series(sc, X.index)
            w = sc.where(sc.rank(ascending=False) <= NPICK, 0) ** 2
            w = w[w > 0] / w[w > 0].sum()
            got = sub[sub["換股日"] == dstr].set_index("sid")["權重"]
            nchk += 1
            diff = set(got.index) ^ set(w.index)
            if diff or float(np.max(np.abs(got.reindex(w.index).to_numpy() - w.to_numpy()))) > 1e-9:
                bad.append((wn, dstr, sorted(diff)[:5]))
    out["① 名單與權重（抽 12 個換股日；自算因子＋A0／A2 可用日）"] = {"檢查日數": nchk, "不同": len(bad), "例": bad[:5]}

    def mybook(wn, a, b):
        cal, mk, RAW, ADJ = W[wn]; n = len(cal)
        D.DATA = EARLY if wn == "早年版面" else H2.H2D
        sub = PK[PK["世界"] == wn]
        sched = {int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(d)))): dict(zip(g["sid"], g["權重"])) for d, g in sub.groupby("換股日")}
        need = sorted(set(sub["sid"]))
        TB = {s: TR.one(s, cal) for s in need}
        O = {s: ADJ[s][0] for s in need}
        C = {s: pd.Series(ADJ[s][1]).ffill().to_numpy() for s in need}
        last = {s: int(np.flatnonzero(np.isfinite(ADJ[s][1]))[-1]) for s in need}
        wend = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(MAIN_END if wn == "主快照" else "2014-12-31")), side="right")) - 1
        cash = 1.0; U = {}; pend = {}; eq = np.ones(n)

        def can_sell(s, t):
            return bool(TB[s]["trd"][t]) and not TB[s]["dn_o"][t] and np.isfinite(O[s][t]) and O[s][t] > 0
        for t in range(a, b + 1):
            for s in list(U):
                if last[s] < wend and t > last[s]:
                    cash += U.pop(s) * C[s][t] * (1 - SELL_C); pend.pop(s, None)
            for s in list(pend):
                if s in U and can_sell(s, t):
                    u = U[s] * pend[s]; cash += u * O[s][t] * (1 - SELL_C); U[s] -= u
                    if pend[s] >= 1.0 or U[s] <= 1e-15:
                        U.pop(s)
                    pend.pop(s)
                elif s not in U:
                    pend.pop(s)
            if t in sched:
                tw = sched[t]
                val = {s: U[s] * (O[s][t] if np.isfinite(O[s][t]) and O[s][t] > 0 else C[s][t - 1]) for s in U}
                tot = cash + sum(val.values())
                for s in sorted(U):
                    want = tw.get(s, 0.0) * tot
                    if val[s] > want + 1e-12:
                        fr = 1.0 if want <= 0 else (val[s] - want) / val[s]
                        if can_sell(s, t):
                            u = U[s] * fr; cash += u * O[s][t] * (1 - SELL_C); U[s] -= u
                            if fr >= 1.0 or U[s] <= 1e-15:
                                U.pop(s)
                        else:
                            pend[s] = fr
                for s in sorted(tw, key=lambda z: -tw[z]):
                    have = U[s] * O[s][t] if (s in U and np.isfinite(O[s][t])) else 0.0
                    nd = tw[s] * tot - have
                    if nd <= 1e-12:
                        continue
                    if (not TB[s]["trd"][t]) or not (np.isfinite(O[s][t]) and O[s][t] > 0) or (last[s] < wend and t > last[s]) or TB[s]["up_o"][t]:
                        continue
                    amt = min(nd, cash / (1 + BUY_C))
                    if amt <= 1e-12:
                        break
                    cash -= amt * (1 + BUY_C); U[s] = U.get(s, 0.0) + amt / O[s][t]
            eq[t] = cash + sum(u * C[s][t] for s, u in U.items())
        return eq
    aA, bA = (int(np.searchsorted(W["早年版面"][0].values, np.datetime64(pd.Timestamp(x)))) for x in S["窗"]["早年甲（早年版面、只上市）"])
    aB, bB = (int(np.searchsorted(W["主快照"][0].values, np.datetime64(pd.Timestamp(x)))) for x in S["窗"]["早年乙（主快照）"])
    eA = mybook("早年版面", aA, bA); eB = mybook("主快照", aB, bB)
    segA = eA[aA:bA + 1] / eA[aA]; segB = eB[aB:bB + 1] / eB[aB] * segA[-1]; arr = np.r_[segA, segB]
    c, m = R13.window_stats(arr, 0, len(arr), 0, len(arr))
    J = S["判定（早年段，月換主格）"]
    out["② 自寫換股簿：早年串接年化／回落"] = {"自算": [float(c), float(m)], "summary": [J["年化"], J["回落"]],
                                    "差": [abs(float(c) - J["年化"]), abs(float(m) - J["回落"])]}
    D.DATA = H2.H2D
    ok = len(bad) == 0 and max(out["② 自寫換股簿：早年串接年化／回落"]["差"]) < 1e-9
    out["結論"] = "✅ 全過（0 不同）" if ok else "⛔ 有不同"
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

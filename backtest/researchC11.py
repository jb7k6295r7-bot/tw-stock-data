# -*- coding: utf-8 -*-
"""PREREGC11「幣本位小槓桿＋低位才開 v1」（sha f68c36ed064e3408）——回測線執行端。裁定 seq291：核准，N＝0（比照 seq289 甲案）。

⭐ 讀法寫死：2026-10-04 13:04（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何數字之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法標【執行者補】；登錄與裁定衝突時以較新的裁定為準（標【依 seq291】）。

資料：與 C10 同一份唯讀副本 main 1fb8815e81（~/c10data/<sha>/）；資金費、強平、成本、讀檔全部沿用 researchC10（import，⛔ 不抄第二份）
   現貨（算高點與長歷史臂）：data/crypto/<SYM>.csv（main 版：BTC 2013 起〔2013～2017 bitstamp〕、ETH 2017-08、BNB 2017-11、XRP 2018-05、DOGE 2019-07、SOL 2020-08）

⭐ 落地讀法
 S1 主窗＝C10 同窗（各幣第一根幣本位日 K ～ 2026-09-30）
 S2 dd(t)＝現貨收盤(t) ÷ 現貨收盤自檔案起點到 t 的累計最高 − 1（只用 t 當日收盤以前；⚠ XRP、DOGE 檔起點晚於 2018 高點 ⇒ 高點偏低，照實用）
 S3 訊號（登錄 §二）：空手且 dd(t) ≤ −D ⇒ 開倉訊號；在場且 dd(t) ≥ −X ⇒ 平倉訊號；平倉後 dd ≥ −X ＞ −D，所以要再跌破 −D 才會再開
    ⭐ 用「水位」判（登錄：dd ≤ −D 即開），所以窗首當天若已在 −D 以下，窗首訊號就開【執行者補】
 S4 執行【依 seq291】：訊號日收盤判、次一可交易時點執行＝次日（UTC）開盤價（主臂用幣本位成交價 open；長歷史臂用現貨 open），⛔ 不回填
    （登錄 §二 原寫「當日收盤建倉」；seq291 較新 ⇒ 改次日開盤）
 S5 開倉：名目 N＝(E−1) × 當時全部幣數 × 執行價；手續費 0.05% × N ÷ 執行價（以幣付）；全部幣都是保證金；開著不再平衡、不加減
    平倉：幣數＝W ＋ N(1/Pe − 1/執行價) − 費率 × N ÷ 執行價；窗尾未平 ⇒ 以窗尾成交價收盤估值、不付平倉費（登錄 §二）
 S6 資金費（沿用 C10 R2／R3：逐筆、以幣計 − rate × N ÷ 前一日標記價收盤）；在場區間＝（開倉當天 00:00 結算之後，平倉當天 00:00 結算〕
    ⇒ 開倉當天只扣 00:00 以後各筆；平倉當天只扣 00:00 那筆；中間每天全扣【執行者補】
 S7 強平（沿用 C10 R5）：Lp＝N(1+m)/(W+N/Pe)；每日順序：先扣當日資金費 ⇒ 重算 Lp ⇒ 當日低 ≤ Lp 即強平；開倉當天也查當日低；平倉當天（開盤就平）不查
    強平：全部幣歸零、之後 0（全部存幣都是保證金）；m ∈ {0.5、1、2%}（分級表未到，官方最低一級＝待定）；標記價日低為主、成交價日低並報
 S8 軸：E {1.1、1.2、1.3} × D {50、60、70%} × X {30、15、0%} × m 三值 × 價格口徑 2 × 成本 ×0.5／×1／×2／×4（成本只進 csv）
 S9 對照：同幣一直存 1 顆（同窗）；期末幣數比＝本規則期末幣數 ÷ 1；美元期末值＝幣數 × 窗尾收盤
 S10 逐段故事表（seq291）：每段＝訊號日、執行日（開倉日）、開倉價、dd、之後最深再跌（持有期間日低最低 ÷ 開倉價 − 1；標記價、成交價各一）、
    距強平線最近時剩多少（min 日低 ÷ Lp − 1，標記價、m＝1% 那條）、有沒有強平（6 種 m×口徑逐一）、平倉訊號日、平倉執行日、這段期間幣數變化
    （平倉後幣數 − 開倉前幣數；未平＝窗尾估值；強平＝−開倉前幣數）、這段資金費（幣）
    ⭐ 沒強平時路徑跟 m、口徑無關 ⇒ 故事以 m＝1%、標記價那條為代表，強平與否 6 種逐一列【執行者補】
 S11 長歷史描述臂（登錄 §四⑤、seq291）：現貨當合約價（執行＝現貨次日 open、強平＝現貨日低、估值＝現貨收盤），⛔ 不計資金費；窗＝各幣現貨起點～2026-09-30；
    標「無永續合約、無資金費、強平為近似」；現貨檔若有缺日，「次一可交易時點」＝下一列【執行者補】
 S12 先驗對答（主臂、成本 ×1）：
    ① BTC、BNB：E1.1、1.2 全部 D、X、m（標記價主；成交價另報）零強平
    ② SOL：E1.1 至少一格強平（任一 D、X、m、標記價）
    ③ ETH：E1.3、D50% 至少一格強平（任一 X、m、標記價）
    ④ X＝0%：逐幣看 X＝0% 各格（E 不影響段落日期；取 E1.1、m 1%、標記價）的段落，到窗尾仍未出場的占過半 ⇒ 該幣算；≥4 幣（有段落的幣過半）⇒ 中【執行者補：「多數幣」的計法】
 S13 --check：沿用 C10 fixture a～d（先跑 C10 自己的 run_fixtures 確認共用實作；再把 a、b、d 接到本支引擎；c 改成本件對應的「重開後強平價重算」）；
    新增 fixture e（跨線才開、跨回才關、關後再跌破才再開、次日開盤執行）＋反例（關後不重開／在場重複開／當日收盤執行＝回填）；
    再用逐筆參考迴圈抽樣重算真資料路徑（種子 20260923），逐位比
⛔ 不寫「哪組 D／X 最好」、不寫任何倍數建議（登錄 §七、seq291）；故事逐段寫。

〔高點更正＋長歷史臂順延 2026-10-04 18:47（台北，TZ=Asia/Taipei date；裁定 seq293 §一、seq294 §二：資料瑕疵更正，N＝0）〕
 S14 現貨長序列（S2 的高點與 S11 的長歷史臂都改用它）：私有 repo ~/us-stock-data（本機 clone）data/crypto_private/ 的早年檔
     ＋ 公開 main 1fb8815e81 data/crypto/<SYM>.csv，接法照私有 README：
     BTC＝BTC.csv（2010-07-17～2012，Mt.Gox→Bitstamp）＋BTC_bitstamp_2013_2017.csv＋公開檔 2017-08-17 起；ETH 2015-08-07、XRP 2015-02-20、DOGE 2018-08-31、SOL 2020-04-10 起各接公開檔；
     BNB 沒有更早的美元價 ⇒ 照舊 2017-11-06；⛔ *_btcquoted、*_overlap 不用；只在接縫換來源，接縫必須是「早年最後一天＋1＝公開檔第一天」，否則停
 S15 主臂 dd 也改用長序列（XRP 高點因此含 2018-01，收盤約 2.77）；其他幣的主窗高點理論上不變（--check／交件時比對）
 S16 長歷史臂窗＝各幣最早美元價～2026-09-30；缺日照實不補（BTC 2011-06-20～25 Mt.Gox 停機、ETH 2015 五天）⇒ 次一可交易時點＝下一列（S11）
     資料品質照實標：BTC 2010-07～2011 Mt.Gox（第三方鏡像）、XRP 2015 零成交 162 天（與 BTC 計價換算差 26～85%，2015-11 才收斂）、ETH 2015 缺 5 天且成交極薄；
     逐幣報長歷史臂有幾段落在這些期間
 S17 ⛔ 私有資料不進公開 repo：長歷史臂的結果只放彙總（日期、比例、幣數變化），故事表與 csv ⛔ 不放開倉價等原始價格【執行者補】
 S18 換標（seq294 §三，不重判）：主格標示改「官方分級表最低一級（現值口徑）」，數值沿用 researchC10.TIER1；強平清算費在強平那一刻從剩餘保證金扣、不改觸發時點，
     強平期本來就記全部歸零 ⇒ 不影響
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, html
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchC10 as C10

OUT = os.path.join(C10.REPO, "backtest", "resultsC11")
COINS = C10.COINS
ES = (1.1, 1.2, 1.3)
DS = (0.5, 0.6, 0.7)
XS = (0.3, 0.15, 0.0)
MMRS = C10.MMRS
BASES = C10.BASES
CMULTS = C10.CMULTS
COST_SIDE = C10.COST_SIDE
W_END = C10.W_END
SEED = 20260923
FROZEN = "2026-10-04 13:04（台北）"


# ───────────────────────── 資料 ─────────────────────────
PRIV = os.path.expanduser("~/us-stock-data/data/crypto_private")
EARLY = {"BTC": ("BTC.csv", "BTC_bitstamp_2013_2017.csv"), "ETH": ("ETH.csv",), "XRP": ("XRP.csv",), "DOGE": ("DOGE.csv",), "SOL": ("SOL.csv",), "BNB": ()}
QUALITY = {"BTC": [("2010-07-17", "2011-12-31", "Mt.Gox 段（第三方鏡像；含 2011-06-20～25 停機缺日）")],
           "ETH": [("2015-08-07", "2015-12-31", "2015 年 Kraken 成交極薄、缺 5 天")],
           "XRP": [("2015-02-20", "2015-10-31", "2015 年零成交 162 天、與 BTC 計價換算差 26～85%")]}
_SPOT = {}


def spot_full(sym):
    """S14：早年私有檔＋公開檔（接縫處換來源），dd 用累計最高收盤。"""
    if sym in _SPOT:
        return _SPOT[sym].copy()
    pub = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str}).drop_duplicates("date").sort_values("date")
    cols = ["date", "open", "high", "low", "close", "volume"]
    parts = [pd.read_csv(os.path.join(PRIV, f), dtype={"date": str})[cols] for f in EARLY[sym]]
    if parts:
        early = pd.concat(parts).sort_values("date")
        assert not early["date"].duplicated().any(), f"⛔ {sym} 早年檔日期重複"
        last = early["date"].iloc[-1]
        pub = pub[pub["date"] > last]
        seam = (pd.Timestamp(pub["date"].iloc[0]) - pd.Timestamp(last)).days
        assert seam == 1, f"⛔ {sym} 接縫不連續：{last} → {pub['date'].iloc[0]}"
        sp = pd.concat([early, pub[cols]])
    else:
        sp = pub[cols]
    sp = sp[sp["date"] <= W_END].reset_index(drop=True)
    assert sp["date"].is_monotonic_increasing and not sp["date"].duplicated().any()
    sp["hi_cum"] = sp["close"].cummax(); sp["dd"] = sp["close"] / sp["hi_cum"] - 1.0
    _SPOT[sym] = sp
    return sp.copy()


def load_main(sym):
    d = C10.load(sym)
    p = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto_cm_perp", f"{sym}USD_PERP.csv"))
    p["date"] = pd.to_datetime(p["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    d["open"] = p.drop_duplicates("date").set_index("date").reindex(d["dates"])["open"].to_numpy(float)
    assert np.isfinite(d["open"]).all()
    f = pd.read_csv(os.path.join(C10.ROOT, "data", "meta", "crypto_cm_funding_rest", f"{sym}USD_PERP.csv"))
    f["sec"] = f["funding_time"] // 1000; f = f.drop_duplicates("sec")
    ts = pd.to_datetime(f["sec"], unit="s", utc=True)
    f["date"] = ts.dt.strftime("%Y-%m-%d"); f["tod0"] = (f["sec"] % 86400) == 0
    g0 = f[f["tod0"]].groupby("date")["funding_rate"].sum(); g1 = f[~f["tod0"]].groupby("date")["funding_rate"].sum()
    d["f0"] = g0.reindex(d["dates"]).fillna(0.0).to_numpy(float)       # 當天 00:00 那筆
    d["f1"] = g1.reindex(d["dates"]).fillna(0.0).to_numpy(float)       # 當天 00:00 以後各筆
    assert np.allclose(d["f0"] + d["f1"], d["fsum"], atol=1e-15)
    sp = spot_full(sym).set_index("date")
    d["dd"] = sp["dd"].reindex(d["dates"]).to_numpy(float)
    assert np.isfinite(d["dd"]).all()
    return d


def load_long(sym):
    sp = spot_full(sym)
    n = len(sp)
    return {"sym": sym, "dates": sp["date"].to_numpy(), "close": sp["close"].to_numpy(float), "open": sp["open"].to_numpy(float),
            "tlow": sp["low"].to_numpy(float), "mlow": sp["low"].to_numpy(float), "mclose": sp["close"].to_numpy(float),
            "f0": np.zeros(n), "f1": np.zeros(n), "dd": sp["dd"].to_numpy(float),
            "缺日": int((pd.to_datetime(sp["date"].iloc[-1]) - pd.to_datetime(sp["date"].iloc[0])).days + 1 - n),
            "缺日清單": sorted(set(pd.date_range(sp["date"].iloc[0], sp["date"].iloc[-1]).strftime("%Y-%m-%d")) - set(sp["date"]))}


# ───────────────────────── 引擎（單一路徑、狀態機）─────────────────────────
def path(d, low, E, D, X, m, cost, mut=None, want_eq=False, lp_low=None):
    """回 dict：liq（索引或 −1）、segs（每段明細）、coins（窗尾幣數）、eq（收盤幣數陣列，選用）。
    mut：None｜usd_margin｜fund_sign｜ideal_lp｜no_relp（強平價沿用第一段）｜no_reopen｜double_open｜same_day（訊號日收盤執行＝回填）。"""
    close, opx, mclose, f0, f1, dd = d["close"], d["open"], d["mclose"], d["f0"], d["f1"], d["dd"]
    T = len(close); L = E - 1.0
    W = 1.0; N = 0.0; Pe = 1.0; inpos = False; pend = None; liq = -1; segs = []; cur = None; Lp_first = None; opened_once = False
    eq = np.full(T, np.nan) if want_eq else None
    lpl = low if lp_low is None else lp_low

    def val(P):
        if not inpos:
            return W
        if mut == "usd_margin":
            return (W * Pe + N * (P / Pe - 1.0)) / P
        return W + N * (1.0 / Pe - 1.0 / P)

    def lp_now():
        if mut == "ideal_lp":
            return Pe * L / (1.0 + L)
        if mut == "no_relp" and Lp_first is not None:
            return Lp_first
        den = W + N / Pe
        return N * (1 + m) / den if den > 0 else math.inf

    def do_open(t, px, sig_t):
        nonlocal W, N, Pe, inpos, cur, Lp_first, opened_once
        before = val(px)
        N = L * W * px; fz = cost * N / px; W -= fz; Pe = px; inpos = True; opened_once = True
        if Lp_first is None:
            Lp_first = N * (1 + m) / (W + N / Pe)
        cur = {"訊號日": d["dates"][sig_t], "開倉日": d["dates"][t], "開倉價": float(px), "dd": float(dd[sig_t]), "開倉前幣數": float(before),
               "最低_成交": math.inf, "最低_標記": math.inf, "距強平最近": math.inf, "資金費": 0.0, "手續費": float(fz)}

    def do_close(t, px, sig_t):
        nonlocal W, N, inpos, cur
        W = W + N * (1.0 / Pe - 1.0 / px); fz = cost * N / px; W -= fz; N = 0.0; inpos = False
        cur.update({"平倉訊號日": d["dates"][sig_t], "平倉日": d["dates"][t], "強平": False, "期末幣數": float(W)}); cur["手續費"] += float(fz)
        segs.append(cur); cur = None

    sig_day = None
    for t in range(T):
        if liq >= 0:
            if want_eq:
                eq[t] = 0.0
            continue
        if t > 0:
            if pend == "open":
                do_open(t, opx[t], sig_day); pend = None
                dW = -(f1[t] if mut != "fund_sign" else -f1[t]) * N / mclose[t - 1]
                W += dW; cur["資金費"] += dW
            elif pend == "close":
                dW = -(f0[t] if mut != "fund_sign" else -f0[t]) * N / mclose[t - 1]
                W += dW; cur["資金費"] += dW
                do_close(t, opx[t], sig_day); pend = None
            elif inpos:
                ft = f0[t] + f1[t]
                dW = -(ft if mut != "fund_sign" else -ft) * N / mclose[t - 1]
                W += dW; cur["資金費"] += dW
            if inpos:
                Lp = lp_now()
                cur["最低_成交"] = min(cur["最低_成交"], d["tlow"][t]); cur["最低_標記"] = min(cur["最低_標記"], d["mlow"][t])
                cur["距強平最近"] = min(cur["距強平最近"], lpl[t] / Lp - 1.0 if Lp > 0 else math.inf)
                if low[t] <= Lp:
                    liq = t; cur.update({"平倉訊號日": "", "平倉日": d["dates"][t], "強平": True, "期末幣數": 0.0}); segs.append(cur); cur = None
                    W = 0.0; N = 0.0; inpos = False
                    if want_eq:
                        eq[t] = 0.0
                    continue
        # 訊號日收盤
        if pend is None:
            if (not inpos) and dd[t] <= -D and not (mut == "no_reopen" and opened_once):
                if mut == "same_day":
                    do_open(t, close[t], t)
                else:
                    pend, sig_day = "open", t
            elif inpos and dd[t] >= -X:
                if mut == "same_day":
                    do_close(t, close[t], t)
                else:
                    pend, sig_day = "close", t
            elif inpos and mut == "double_open" and dd[t] <= -D:
                do_open(t, close[t], t)            # 反例：在場又開一次（重設部位）
        if want_eq:
            eq[t] = val(close[t])
    if cur is not None:
        cur.update({"平倉訊號日": "", "平倉日": "", "強平": False, "期末幣數": float(val(close[-1]))}); segs.append(cur)
    for s in segs:
        s["幣數變化"] = s["期末幣數"] - s["開倉前幣數"]
        s["之後最深再跌_成交"] = s["最低_成交"] / s["開倉價"] - 1.0 if math.isfinite(s["最低_成交"]) else float("nan")
        s["之後最深再跌_標記"] = s["最低_標記"] / s["開倉價"] - 1.0 if math.isfinite(s["最低_標記"]) else float("nan")
    return {"liq": liq, "segs": segs, "coins": 0.0 if liq >= 0 else float(val(close[-1])), "eq": eq}


# ───────────────────────── fixture ─────────────────────────
def adapter(mut=None):
    """把 C10 fixture 的介面 run(close, low, mclose, fbd, rmask, E, m, cost) 接到本支引擎：
    第 0 天＝訊號日（dd −99%、永不出場），第 1 天開盤價＝C10 的 close[0]（＝C10 的建倉價），各筆資金費當作 08:00（開倉當天要扣）。"""
    def run(close, low, mclose, fbd, rmask, E, m, cost):
        T = len(close); o = np.array(close, float).copy(); o[1] = close[0]
        d = {"dates": np.array([f"2000-01-{i + 1:02d}" for i in range(T)]), "close": np.array(close, float), "open": o,
             "tlow": np.array(low, float), "mlow": np.array(low, float), "mclose": np.array(mclose, float),
             "f0": np.zeros(T), "f1": np.array([float(np.sum(a)) for a in fbd]), "dd": np.full(T, -0.99)}
        r = path(d, d["mlow"], E, 0.5, 0.0, m, cost, mut=mut, want_eq=True)
        eq = list(r["eq"]); eq[0] = 1.0 - cost * (E - 1)           # C10 的第 0 天＝建倉後
        return r["liq"], eq, []
    return run


def _mk(close, opx, low, dd, f1=None):
    T = len(close)
    return {"dates": np.array([f"2000-01-{i + 1:02d}" for i in range(T)]), "close": np.array(close, float), "open": np.array(opx, float),
            "tlow": np.array(low, float), "mlow": np.array(low, float), "mclose": np.array(close, float),
            "f0": np.zeros(T), "f1": np.zeros(T) if f1 is None else np.array(f1, float), "dd": np.array(dd, float)}


def fx_c11(run_path):
    """c（本件版）：平倉後再開，強平價要用新部位重算。E2、m1%：第 1 天開 100 ⇒ 第 3 天開盤 150 平 ⇒ 第 5 天開盤 120 再開；
    再開後 W＝4/3、N＝160 ⇒ Lp＝161.6/(8/3)＝60.6；第 6 天日低 58 ⇒ 強平（沿用第一段 Lp 50.5 就不會）。"""
    # 訊號：t0 dd −0.6 開訊號 ⇒ t1 開盤 100 開；t2 dd −0.1 ≥ −0.3 平訊號 ⇒ t3 開盤 150 平；t4 dd −0.6 開訊號 ⇒ t5 開盤 120 再開；t6 日低 58
    c = [100, 100, 140, 150, 130, 120, 100, 100]; o = [100, 100, 140, 150, 130, 120, 100, 100]
    lo = [100, 100, 140, 150, 130, 120, 58, 100]
    d = _mk(c, o, lo, [-0.6, -0.6, -0.1, -0.1, -0.6, -0.6, -0.6, -0.6])
    r = run_path(d, d["mlow"], 2.0, 0.5, 0.3, 0.01, 0.0)
    return bool(len(r["segs"]) == 2 and r["liq"] == 6 and abs(r["segs"][1]["開倉價"] - 120.0) < 1e-12)


def fx_e(run_path):
    """e. 跨線才開、跨回才關、關後再跌破才再開、次日開盤執行（D50%、X30%）：
    dd：−0.10、−0.55（開訊號）、−0.60、−0.25（平訊號）、−0.40、−0.45、−0.51（再開訊號）、−0.55、−0.52、−0.40
    ⇒ 兩段：第 2 天開盤開、第 4 天開盤平；第 7 天開盤再開、到窗尾未平；開倉價＝次日開盤（開盤價刻意 ≠ 前一日收盤）。"""
    dd = [-0.10, -0.55, -0.60, -0.25, -0.40, -0.45, -0.51, -0.55, -0.52, -0.40]
    c = [100.0] * 10; o = [100.0 + t for t in range(10)]
    d = _mk(c, o, [99.0] * 10, dd)
    r = run_path(d, d["mlow"], 1.2, 0.5, 0.3, 0.01, 0.0)
    s = r["segs"]
    return bool(len(s) == 2 and s[0]["開倉日"] == d["dates"][2] and s[0]["平倉日"] == d["dates"][4] and s[1]["開倉日"] == d["dates"][7]
                and s[1]["平倉日"] == "" and abs(s[0]["開倉價"] - 102.0) < 1e-12 and abs(s[1]["開倉價"] - 107.0) < 1e-12 and s[0]["訊號日"] == d["dates"][1])


def run_fixtures():
    ok10, fx10 = C10.run_fixtures()
    res = [{"案": f"C10-{r['案']}", "本支引擎": "（C10 自身引擎）", "反例": r["反例"], "結果": f"{r['向量引擎']}／反例{r['反例結果']}"} for r in fx10]
    for name, fx, mut, why in (("a", C10.fx_a, "usd_margin", "保證金當成美元"), ("b", C10.fx_b, "fund_sign", "費率符號反過來"),
                               ("d", C10.fx_d, "ideal_lp", "用理想強平價（不含 m、費用、資金費）")):
        g = fx(adapter()); red = not fx(adapter(mut))
        res.append({"案": name, "本支引擎": "綠" if g else "紅", "反例": why, "結果": "反例紅（抓得到）" if red else "⛔ 反例仍綠"})
    for name, fx, muts in (("c（重開後強平價重算）", fx_c11, (("no_relp", "強平價沿用第一段"),)),
                           ("e（跨線開、跨回關、關後再跌破才開、次日開盤）", fx_e, (("no_reopen", "關後不重開"), ("double_open", "在場重複開"), ("same_day", "訊號日收盤就執行（回填）")))):
        g = fx(lambda *a, **k: path(*a, **k))
        for mut, why in muts:
            red = not fx(lambda *a, _m=mut, **k: path(*a, mut=_m, **k))
            res.append({"案": name, "本支引擎": "綠" if g else "紅", "反例": why, "結果": "反例紅（抓得到）" if red else "⛔ 反例仍綠"})
    allok = ok10 and all((r["本支引擎"] in ("綠", "（C10 自身引擎）")) and ("⛔" not in r["結果"]) for r in res)
    return allok, res


# ───────────────────────── 參考實作（抽樣用；逐筆資金費、逐日迴圈、另寫一次）─────────────────────────
def ref_check(sym, d_raw_fund, d, low, E, D, X, m, cost):
    """逐筆讀原始資金費列（含時間），獨立重算一條路徑的強平日與窗尾幣數。"""
    rows = d_raw_fund
    dates = list(d["dates"]); idx = {x: i for i, x in enumerate(dates)}
    by_day = {}
    for sec, rate in rows:
        dt = time.strftime("%Y-%m-%d", time.gmtime(sec))
        if dt in idx:
            by_day.setdefault(idx[dt], []).append((sec % 86400, rate))
    W, N, Pe, pos, pend = 1.0, 0.0, 1.0, False, None
    for t in range(len(dates)):
        if t > 0:
            rs = by_day.get(t, [])
            if pend == "open":
                px = d["open"][t]; N = (E - 1) * W * px; W -= cost * N / px; Pe = px; pos = True; pend = None
                for tod, r in rs:
                    if tod > 0:
                        W -= r * N / d["mclose"][t - 1]
            elif pend == "close":
                for tod, r in rs:
                    if tod == 0:
                        W -= r * N / d["mclose"][t - 1]
                px = d["open"][t]; W += N * (1 / Pe - 1 / px) - cost * N / px; N = 0.0; pos = False; pend = None
            elif pos:
                for tod, r in rs:
                    W -= r * N / d["mclose"][t - 1]
            if pos:
                if low[t] <= N * (1 + m) / (W + N / Pe):
                    return dates[t], 0.0
        if pend is None:
            if not pos and d["dd"][t] <= -D:
                pend = "open"
            elif pos and d["dd"][t] >= -X:
                pend = "close"
    P = d["close"][-1]
    return "", (W + N * (1 / Pe - 1 / P)) if pos else W


# ───────────────────────── 主計算 ─────────────────────────
def run_arm(data, arm):
    maps, stories = [], []
    for s in COINS:
        d = data[s]
        for E in ES:
            for D in DS:
                for X in XS:
                    for basis in BASES:
                        low = d["mlow"] if basis == "mark" else d["tlow"]
                        for m in MMRS:
                            for cm in CMULTS:
                                if arm == "long" and cm != 1.0:
                                    continue
                                r = path(d, low, E, D, X, m, COST_SIDE * cm, lp_low=d["mlow"])
                                sg = r["segs"]
                                maps.append({"arm": arm, "coin": s, "E": E, "D": D, "X": X, "basis": basis, "MMR": m, "cost_mult": cm,
                                             "進場次數": len(sg), "強平次數": int(r["liq"] >= 0), "強平日": d["dates"][r["liq"]] if r["liq"] >= 0 else "",
                                             "窗尾未平": int(bool(sg) and sg[-1]["平倉日"] == "" and not sg[-1]["強平"]),
                                             "期末幣數": r["coins"], "存幣期末幣數": 1.0, "期末美元": r["coins"] * d["close"][-1], "存幣期末美元": d["close"][-1],
                                             "資金費（幣）": float(sum(x["資金費"] for x in sg)), "手續費（幣）": float(sum(x["手續費"] for x in sg)),
                                             "窗首": d["dates"][0], "窗尾": d["dates"][-1]})
                                if cm == 1.0:
                                    for k, x in enumerate(sg):
                                        if arm == "long":
                                            x = {kk: vv for kk, vv in x.items() if kk != "開倉價"}       # S17：私有資料段不放原始價格
                                            x["開倉價"] = float("nan")
                                        stories.append({"arm": arm, "coin": s, "E": E, "D": D, "X": X, "basis": basis, "MMR": m, "段": k + 1,
                                                        **{kk: x[kk] for kk in ("訊號日", "開倉日", "開倉價", "dd", "之後最深再跌_標記", "之後最深再跌_成交", "距強平最近",
                                                                                 "強平", "平倉訊號日", "平倉日", "開倉前幣數", "期末幣數", "幣數變化", "資金費", "手續費")}})
        print(f"  [{arm}] {s} 完成", flush=True)
    return pd.DataFrame(maps), pd.DataFrame(stories)


def quality_lines(Sl, longd):
    out = []
    base = Sl[(Sl.MMR == 0.01) & (Sl.basis == "mark")]
    for s, lst in QUALITY.items():
        for a, b, txt in lst:
            g = base[base.coin == s]
            end = g["平倉日"].where(g["平倉日"] != "", "9999-12-31")
            n = int(((g["開倉日"] <= b) & (end >= a)).sum())
            out.append(f"{s} {a}～{b} {txt}：長歷史臂 m1%・標記價的 {len(g)} 段中有 {n} 段持有期間碰到這段")
    for s in COINS:
        if longd[s]["缺日"]:
            out.append(f"{s} 長序列缺日 {longd[s]['缺日']} 天（{'、'.join(longd[s]['缺日清單'])}），照實不補，次一可交易時點＝下一列")
    return out


def story_view(St):
    """S10：以 m1%・標記價為代表，附 6 種 m×口徑的強平與否。"""
    base = St[(St.MMR == 0.01) & (St.basis == "mark")].copy()
    flags = St.groupby(["arm", "coin", "E", "D", "X", "段", "basis", "MMR"])["強平"].first()
    def fl(r):
        out = []
        for b in BASES:
            v = []
            for m in MMRS:
                try:
                    v.append("強" if flags.loc[(r.arm, r.coin, r.E, r.D, r.X, r.段, b, m)] else "○")
                except KeyError:
                    v.append("·")
            out.append(("標" if b == "mark" else "成") + "".join(v))
        return " ".join(out)
    base["強平_6種"] = base.apply(fl, axis=1) if len(base) else []
    return base


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.{nd}f}%"


def build_html(meta, Mm, Ml, SV, SVl, fx, chk):
    e = html.escape
    css = C10_CSS
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>小槓桿低位才開</title><style>{css}</style></head><body><main>"]
    h.append("<h1>小槓桿低位才開：強平地圖與逐段故事</h1>")
    h.append(f"<div class='sub'>PREREGC11 v1（N＝0，確定性描述）｜回測線｜資料 main {C10.SHA[:10]}｜主窗到 {W_END}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論（主臂：幣本位永續、標記價日低；維持保證金率 0.5～2%）</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             "<div class='small'>⛔ 每幣在窗內只有個位數段落，下面是逐段的歷史故事，不是哪組最好、也不是安全倍數。</div></div>")
    h.append("<div class='card'><b>規則</b>：存幣全部當保證金。現貨距歷史高點跌到 −D 以下，次日開盤開一張名目＝(E−1)×存幣的幣本位多單；回到距高點 −X 以內，次日開盤平倉、只留幣；平倉後要再跌破 −D 才再開。開著不再平衡。"
             "E＝1.1／1.2／1.3、D＝50／60／70%、X＝30／15／0%。</div>")
    # 強平地圖：主臂
    h.append("<h2>一、強平地圖（主臂：2020～2026 幣本位永續）</h2><div class='small'>每格：進場次數／強平次數。強平格標日期。維持保證金率三值都一樣時只寫一次，不一樣時逐一寫「m0.5%: …」；成交價日低不同時另列一行。成本 ×1。</div>")
    for s in COINS:
        g = Mm[(Mm.coin == s) & (Mm.cost_mult == 1.0)]
        h.append(f"<h3>{s}（{g['窗首'].iloc[0]}～{g['窗尾'].iloc[0]}）</h3><div class='tw'><table><tr><th>E／D</th>" + "".join(f"<th>X {int(x * 100)}%</th>" for x in XS) + "</tr>")
        for E in ES:
            for D in DS:
                cells = []
                for X in XS:
                    q = g[(g.E == E) & (g.D == D) & (g.X == X)]
                    mk, tr = map_cell(q[q.basis == "mark"]), map_cell(q[q.basis == "trade"])
                    cls = " class='no'" if q[q.basis == "mark"]["強平次數"].sum() > 0 else ""
                    cells.append(f"<td{cls}>{e(mk)}" + ("" if tr == mk else f"<br><span class='small'>成交價：{e(tr)}</span>") + "</td>")
                h.append(f"<tr><td>{E:g}／{int(D * 100)}%</td>" + "".join(cells) + "</tr>")
        h.append("</table></div>")
    # 故事表
    h.append("<h2>二、逐段故事（主臂）</h2><div class='small'>以維持保證金率 1%、標記價那條為代表（沒強平時路徑跟 m、口徑無關）。「強平」欄：標＝標記價、成＝成交價，三格依序 m＝0.5／1／2%，強＝強平、○＝沒有。"
             "幣數變化＝這段結束時幣數 − 開倉前幣數（未平＝窗尾估值）。dd＝訊號日距高點跌幅。最深再跌＝持有期間日低相對開倉價。</div>")
    h.append(story_tables(SV, e))
    # 期末幣數
    h.append("<h2>三、期末幣數（主臂，對一直存 1 顆）</h2><div class='small'>m＝1%、標記價、成本 ×1。1.000＝跟一直存幣一樣（窗內沒進場就是 1）。只描述，不比好壞。</div>")
    h.append("<div class='tw'><table><tr><th>幣</th><th>E</th>" + "".join(f"<th>D{int(D * 100)}・X{int(X * 100)}</th>" for D in DS for X in XS) + "</tr>")
    for s in COINS:
        for E in ES:
            g = Mm[(Mm.coin == s) & (Mm.E == E) & (Mm.basis == "mark") & (Mm.MMR == 0.01) & (Mm.cost_mult == 1.0)]
            h.append(f"<tr><td>{s}</td><td>{E:g}</td>" + "".join(f"<td>{g[(g.D == D) & (g.X == X)]['期末幣數'].iloc[0]:.3f}</td>" for D in DS for X in XS) + "</tr>")
    h.append("</table></div>")
    # 長歷史臂
    h.append("<h2>四、長歷史描述臂（⚠ 無永續合約、無資金費、強平為近似）</h2><div class='small'>用現貨價當合約價、現貨日低判強平，⛔ 不計資金費；窗＝各幣最早的美元價～2026-09-30（BTC 2010-07、ETH 2015-08、XRP 2015-02、DOGE 2018-08、SOL 2020-04；BNB 沒有更早的美元價，照舊 2017-11），涵蓋 2011、2014–15、2018–19 熊市。⛔ 只回答更深的熊市裡會不會觸線，不是主結果。"
             + "<br>資料品質：" + "；".join(meta["資料品質"]) + ""
             "格式同上（標記價欄＝現貨日低）。</div>")
    for s in COINS:
        g = Ml[(Ml.coin == s) & (Ml.basis == "mark")]
        h.append(f"<h3>{s}（{g['窗首'].iloc[0]}～{g['窗尾'].iloc[0]}）</h3><div class='tw'><table><tr><th>E／D</th>" + "".join(f"<th>X {int(x * 100)}%</th>" for x in XS) + "</tr>")
        for E in ES:
            for D in DS:
                cells = []
                for X in XS:
                    z = g[(g.E == E) & (g.D == D) & (g.X == X)]
                    t = map_cell(z)
                    cells.append(f"<td{' class=no' if any(int(c) for c in z['強平次數']) else ''}>{e(t)}</td>")
                h.append(f"<tr><td>{E:g}／{int(D * 100)}%</td>" + "".join(cells) + "</tr>")
        h.append("</table></div>")
    h.append("<details><summary>長歷史臂逐段故事（展開；私有資料段不列價格）</summary>" + story_tables(SVl, e, show_px=False) + "</details>")
    h.append("<h2>五、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>六、驗證</h2><div class='tw'><table><tr><th>案</th><th>本支引擎</th><th>反例</th><th>結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td style='white-space:normal'>{e(r['案'])}</td><td>{e(r['本支引擎'])}</td><td style='white-space:normal'>{e(r['反例'])}</td><td>{e(r['結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>抽樣重算（逐筆讀原始資金費列的另一支迴圈）：{chk.get('一致數', '—')}／{chk.get('抽樣數', '—')} 條一致。</div>")
    h.append("<h2>七、讀的時候要注意</h2><ul><li>每幣窗內只有個位數段落（0～6 段），任何比較都是挑樣本；⛔ 不寫哪組 D／X 最好、不提供倍數建議。</li>"
             "<li>高點用含早年的長序列：XRP 已含 2018-01 高點；DOGE 長序列從 2018-08 起，晚於 2018-01 高點，但那個高點比主臂窗首價格低，主臂不受影響，長歷史臂 2018～2020 的 dd 偏淺。</li>"
             "<li>" + C10.tier_note_html() + "</li>"
             "<li>" + C10.LIQ_FEE_NOTE + " 強平只看日低。</li>"
             "<li>開、平倉都在訊號日收盤判、次日開盤執行（不回填）。</li>"
             "<li>模型外風險：交易所倒閉、自動減倉、插針、規格變動、提幣限制。</li></ul>")
    h.append("<h2>沿革</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in meta["沿革"]) + "</ul>")
    h.append("<h2>八、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in meta["執行者補"]) + "</ul></main></body></html>")
    return "\n".join(h)


def map_cell(z):
    """進場次數／強平次數（強平日）；三個 m 一樣只寫一次，不一樣逐 m 寫。"""
    z = z.sort_values("MMR")
    txt = [f"{int(a)}／{int(c)}" + (f"（{dt}）" if dt else "") for a, c, dt in zip(z["進場次數"], z["強平次數"], z["強平日"])]
    if len(set(txt)) == 1:
        return txt[0]
    return "；".join(f"m{m * 100:g}%: {t}" for m, t in zip(z["MMR"], txt))


def story_tables(SV, e, show_px=True):
    out = []
    for s in COINS:
        g = SV[SV.coin == s]
        if not len(g):
            out.append(f"<h3>{s}</h3><div class='small'>窗內沒有任何一格進場。</div>"); continue
        out.append(f"<details open><summary><b>{s}</b>（{len(g)} 段，含各 E／D／X）</summary><div class='tw'><table><tr><th>E／D／X</th><th>開倉日</th><th>dd</th>" + ("<th>開倉價</th>" if show_px else "") + "<th>最深再跌<br>標記／成交</th><th>距強平最近</th><th>強平</th><th>平倉日</th><th>幣數變化</th><th>資金費（幣）</th></tr>")
        for _, r in g.sort_values(["D", "X", "E", "段"]).iterrows():
            out.append(f"<tr><td>{r.E:g}／{int(r.D * 100)}／{int(r.X * 100)}</td><td>{r.開倉日}</td><td>{pct(r.dd)}</td>" + (f"<td>{r.開倉價:.6g}</td>" if show_px else "") +
                       f"<td>{pct(r.之後最深再跌_標記)}／{pct(r.之後最深再跌_成交)}</td><td>{pct(r.距強平最近)}</td><td>{e(r.強平_6種)}</td>"
                       f"<td>{r.平倉日 or '未平'}</td><td>{r.幣數變化:+.4f}</td><td>{r.資金費:+.4f}</td></tr>")
        out.append("</table></div></details>")
    return "".join(out)


C10_CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--card:#ffffff;--line:#e4e1da;--acc:#9a3412;--accbg:#fff1e8;--warn:#b45309}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f;--acc:#fb923c;--accbg:#2a1d14;--warn:#fbbf24}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f;--acc:#fb923c;--accbg:#2a1d14;--warn:#fbbf24}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:900px;margin:0 auto;padding:20px 16px 60px}h1{font-size:1.4rem;margin:.2em 0 .3em}h2{font-size:1.15rem;margin:1.8em 0 .5em;border-top:1px solid var(--line);padding-top:1em}
h3{font-size:1rem;margin:1.1em 0 .3em}.sub{color:var(--mut);font-size:.88rem}.lead{background:var(--accbg);border-left:4px solid var(--acc);padding:12px 14px;border-radius:6px;margin:14px 0}
.lead b{color:var(--acc)}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0}table{border-collapse:collapse;font-size:.84rem;min-width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600}.no{color:var(--warn);font-weight:600}ul{padding-left:1.2em}li{margin:.25em 0}.small{font-size:.84rem;color:var(--mut)}
summary{cursor:pointer;margin:8px 0}
"""

EXEC_SUPPLIED = [
    "S3 用水位判：窗首當天已在 −D 以下就開（登錄寫 dd ≤ −D 即開）",
    "S4 次一可交易時點＝次日 UTC 開盤價（依 seq291；登錄原寫當日收盤，以較新的裁定為準）",
    "S6 資金費在場區間：開倉當天只扣 00:00 以後各筆，平倉當天只扣 00:00 那筆",
    "S10 故事以 m 1%、標記價為代表（沒強平時路徑與 m、口徑無關），強平與否 6 種逐一列；距強平最近用標記價日低",
    "S11 長歷史臂現貨檔若有缺日，次一可交易時點＝下一列",
    "S15 主臂 dd 也改用含早年的長序列（只有 XRP 的主窗高點因此改變）",
    "S17 長歷史臂的故事表與 csv 不放開倉價等原始價格（私有資料不進公開 repo）",
    "S18 主格標示改官方分級表最低一級（現值口徑），不重判；強平清算費不改觸發時點、強平期本來就記全部歸零",
    "S12 先驗④「多數幣」：逐幣看 X＝0% 段落（E1.1、m1%、標記價），到窗尾仍未平的占過半就算該幣；6 幣都有段落時要 ≥4 幣，不足 6 幣時要過半",
    "沿用 C10 的執行者補：資金費換幣用前一日標記價收盤、強平公式 Lp＝N(1+m)/(W+N/Pe)、不計強平清算費、窗尾＝2026-09-30",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['本支引擎']}｜反例「{r['反例']}」⇒ {r['結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    data = {s: load_main(s) for s in COINS}
    longd = {s: load_long(s) for s in COINS}
    for s in COINS:
        print(f"[{s}] 主窗 {data[s]['dates'][0]}～{data[s]['dates'][-1]}｜窗首 dd {data[s]['dd'][0]:+.3f}｜長臂 {longd[s]['dates'][0]}～{longd[s]['dates'][-1]}（缺日 {longd[s]['缺日']}）")
    if a.check:
        rng = np.random.default_rng(SEED); rows = []
        combos = [(s, E, D, X, b, m) for s in COINS for E in ES for D in DS for X in XS for b in BASES for m in MMRS]
        Mm, _ = run_arm(data, "main")
        liqc = Mm[(Mm["強平次數"] > 0) & (Mm.cost_mult == 1.0)]
        pick = [combos[i] for i in rng.choice(len(combos), 10, replace=False)]
        if len(liqc):
            r0 = liqc.iloc[int(rng.integers(len(liqc)))]; pick.append((r0.coin, r0.E, r0.D, r0.X, r0.basis, r0.MMR))
        for (s, E, D, X, b, m) in pick:
            f = pd.read_csv(os.path.join(C10.ROOT, "data", "meta", "crypto_cm_funding_rest", f"{s}USD_PERP.csv"))
            f["sec"] = f["funding_time"] // 1000; f = f.drop_duplicates("sec")
            d = data[s]; low = d["mlow"] if b == "mark" else d["tlow"]
            ld, coins = ref_check(s, list(zip(f["sec"].tolist(), f["funding_rate"].tolist())), d, low, E, D, X, m, COST_SIDE)
            r = path(d, low, E, D, X, m, COST_SIDE)
            ld2 = d["dates"][r["liq"]] if r["liq"] >= 0 else ""
            mrow = Mm[(Mm.coin == s) & (Mm.E == E) & (Mm.D == D) & (Mm.X == X) & (Mm.basis == b) & (Mm.MMR == m) & (Mm.cost_mult == 1.0)].iloc[0]
            same = (ld == ld2 == mrow["強平日"]) and abs(coins - r["coins"]) < 1e-9 and abs(coins - mrow["期末幣數"]) < 1e-9
            rows.append({"coin": s, "E": E, "D": D, "X": X, "basis": b, "MMR": m, "參考強平日": ld, "引擎強平日": ld2, "參考期末幣數": coins, "引擎期末幣數": r["coins"], "一致": bool(same)})
        tiers = pd.read_csv(os.path.join(PRIV, "cm_specs", "cm_margin_tiers.csv"), encoding="utf-8-sig")
        t1 = {r.symbol.replace("USD_PERP", ""): float(r.maint_margin_rate) for r in tiers[tiers.tier == 1].itertuples()}
        tier_ok = all(abs(t1[k] - v[0]) < 1e-12 for k, v in C10.TIER1.items())
        seam = {s: (longd[s]["dates"][0], longd[s]["缺日"]) for s in COINS}
        bit = pd.read_csv(os.path.join(PRIV, "BTC_bitstamp_2013_2017.csv"), dtype={"date": str}).set_index("date")["close"]
        arch = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto", "BTC.csv"), dtype={"date": str}).set_index("date")["close"]
        com = bit.index.intersection(arch.index)
        chk = {"讀法寫死": FROZEN, "高點更正補記": "2026-10-04 18:47（台北）", "fixture全過": ok, "fixture": fx, "抽樣數": len(rows), "一致數": int(sum(x["一致"] for x in rows)), "抽樣": rows, "種子": SEED,
               "分級表最低一級與 C10.TIER1 一致": bool(tier_ok), "長序列起點與缺日數": seam,
               "BTC 2013～2017 私有 bitstamp 與公開舊版逐日收盤相同": f"{int((bit.loc[com] == arch.loc[com]).sum())}／{len(com)}"}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"[check] 抽樣 {chk['一致數']}／{chk['抽樣數']} 一致")
        for x in rows:
            print("   ", x)
        assert chk["一致數"] == chk["抽樣數"], "⛔ 抽樣重算不一致"
        return
    Mm, Sm = run_arm(data, "main"); Ml, Sl = run_arm(longd, "long")
    Mm.to_csv(os.path.join(OUT, "map_main.csv"), index=False); Ml.to_csv(os.path.join(OUT, "map_long.csv"), index=False)
    Sm.to_csv(os.path.join(OUT, "stories_main.csv"), index=False); Sl.to_csv(os.path.join(OUT, "stories_long.csv"), index=False)
    SV, SVl = story_view(Sm), story_view(Sl)
    M1 = Mm[Mm.cost_mult == 1.0]
    # 先驗
    pri = []
    def liq_cells(q):
        return q[q["強平次數"] > 0]
    q1 = M1[M1.coin.isin(["BTC", "BNB"]) & M1.E.isin([1.1, 1.2])]
    pri.append(f"① BTC、BNB 在 E1.1、1.2 全部 D、X、m 零強平：標記價 {len(liq_cells(q1[q1.basis == 'mark']))} 格強平、成交價 {len(liq_cells(q1[q1.basis == 'trade']))} 格（共 {len(q1) // 2} 格／口徑）⇒ "
               + ("中" if len(liq_cells(q1[q1.basis == 'mark'])) == 0 else "未中"))
    q2 = M1[(M1.coin == "SOL") & (M1.E == 1.1) & (M1.basis == "mark")]
    pri.append(f"② SOL 至少一個 E1.1 格強平：標記價 {len(liq_cells(q2))}／{len(q2)} 格強平" + (f"（例：{liq_cells(q2).iloc[0]['強平日']}）" if len(liq_cells(q2)) else "") + " ⇒ " + ("中" if len(liq_cells(q2)) else "未中"))
    q3 = M1[(M1.coin == "ETH") & (M1.E == 1.3) & (M1.D == 0.5) & (M1.basis == "mark")]
    pri.append(f"③ ETH 在 E1.3、D50% 有格強平：標記價 {len(liq_cells(q3))}／{len(q3)} 格強平" + (f"（{'、'.join(sorted(set(liq_cells(q3)['強平日'])))}）" if len(liq_cells(q3)) else "") + " ⇒ " + ("中" if len(liq_cells(q3)) else "未中"))
    s4 = Sm[(Sm.X == 0.0) & (Sm.E == 1.1) & (Sm.MMR == 0.01) & (Sm.basis == "mark")]
    hit, have = [], []
    for s in COINS:
        g = s4[s4.coin == s]
        if len(g):
            have.append(s)
            if (g["平倉日"] == "").mean() > 0.5:
                hit.append(s)
    pri.append(f"④ X＝0% 多數幣到窗尾還沒出場：有段落的幣 {len(have)} 個（{'、'.join(have)}），其中 X＝0% 段落過半未平的 {len(hit)} 個（{'、'.join(hit) or '無'}）⇒ "
               + ("中" if len(hit) >= (4 if len(have) == 6 else len(have) // 2 + 1) and len(hit) > 0 else "未中"))
    # 結論行
    lines = []
    for E in ES:
        q = M1[(M1.E == E) & (M1.basis == "mark")]
        cnt = q.groupby("MMR").apply(lambda z: (int((z["強平次數"] > 0).sum()), len(z)))
        coins_liq = sorted(set(q[q["強平次數"] > 0].coin))
        ent = int(q[q.MMR == 0.01]["進場次數"].sum())
        lines.append(f"<b>E＝{E:g}</b>：主臂 6 幣 × 27 組 D／X 中，強平的格數 " + "／".join(f"{a}" for a, _ in cnt) + f"（m＝0.5／1／2%，共 {cnt.iloc[0][1]} 格）；"
                     + (f"出現在 {'、'.join(coins_liq)}" if coins_liq else "沒有任何幣強平") + f"；總進場 {ent} 段（m1%）。")
    ql = Ml[Ml.basis == "mark"]
    ll = sorted(set(ql[ql["強平次數"] > 0].coin))
    lines.append("長歷史描述臂（無永續、無資金費、強平近似）：" + (f"有格強平的幣 {'、'.join(ll)}" if ll else "沒有任何格強平") + "。")
    meta = {"登錄": "PREREGC11 小槓桿低位才開 v1 shaf68c36ed064e3408", "裁定": "seq291（N＝0）", "讀法寫死": FROZEN, "資料commit": C10.SHA,
            "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "E": ES, "D": DS, "X": XS, "MMR": MMRS, "官方最低一級": {k: v[0] for k, v in C10.TIER1.items()}, "主格標示": "官方分級表最低一級（現值口徑）", "強平清算費": C10.LIQ_FEE,
            "主窗": {s: [data[s]["dates"][0], data[s]["dates"][-1], float(data[s]["dd"][0])] for s in COINS},
            "長臂窗": {s: [longd[s]["dates"][0], longd[s]["dates"][-1], longd[s]["缺日"], longd[s]["缺日清單"]] for s in COINS},
            "結論行": lines, "先驗對答": pri, "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1),
            "資料品質": quality_lines(Sl, longd),
            "沿革": ["2026-10-04 13:04 讀法寫死、初版交件",
                     "2026-10-04 18:47 高點更正（seq293、seq294 §二，資料瑕疵更正、N＝0）：高點改用含早年的長序列，XRP 高點因此含 2018-01（收盤約 2.77）；主臂與長歷史臂都重跑，長歷史臂順延到各幣最早美元價；本頁數字全是更正後",
                     "2026-10-04 18:47 換標（seq294 §三）：主格標示改官方分級表最低一級（現值口徑），不重判；補強平清算費說明"]}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "小槓桿低位才開.html"), "w", encoding="utf-8").write(build_html(meta, Mm, Ml, SV, SVl, fx, chk))
    for x in lines + pri:
        print(re_strip(x))
    print(f"完成 {time.time() - t0:.0f}s")


def re_strip(x):
    import re
    return re.sub(r"<[^>]+>", "", x)


if __name__ == "__main__":
    main()

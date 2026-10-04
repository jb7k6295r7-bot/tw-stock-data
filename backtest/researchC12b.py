# -*- coding: utf-8 -*-
"""PREREGC12b「價格區間預測校準——早年新段 v1」（sha c06764755e711a2a）——回測線執行端。裁定 seq294 §一：核准，N＝42，批4。

⭐ 讀法寫死：2026-10-04 18:52（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何新段數字之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法標【執行者補】。母登錄 PREREGC12 v1 的模型、目標、容忍帶、bootstrap 全部照抄（import researchC12，⛔ 不抄第二份）。

⚠ 照實標（seq294 §一）：新段的【價格】以前看過、【命中】結果未算過——BTC 2013～2014 用於 C11 長歷史臂與 C12 暖機；ETH 2018 用於 C11 長歷史臂；
   另外回測線在本件之前（同日 18:47）重跑 C11 長歷史臂時，已用過 BTC 2010～2012、ETH 2015～2017、XRP 2015～2018、DOGE 2018～2019、SOL 2020 的早年價格（只算強平，沒算任何區間命中）

資料：與 C11 同一條長序列（researchC11.spot_full：私有 ~/us-stock-data data/crypto_private 早年檔＋公開 main 1fb8815e81 data/crypto；接縫處換來源、⛔ *_btcquoted 不用）
   ⛔ 私有資料不進公開 repo：結果檔只放彙總與 0／1 命中、相對寬度；⛔ 不放任何價格列、⛔ 不放逐起點的實現報酬

⭐ 落地讀法
 B1 幣：BTC、ETH、XRP、DOGE、SOL（SOL 只描述）；BNB 沒有早於 2017-11-06 的美元價 ⇒ 不納入（登錄 §二）
 B2 日曆：長序列攤成逐日日曆（早年起點～2026-09-30），缺日（BTC 2011-06-20～25、ETH 2015 五天）留空、照實不補【執行者補：用日曆日，h 天＝h 個日曆日，與 C12 同義】
 B3 原段首起點（C12 的第一個起點，寫死）：BTC 2015-01-01、ETH 2019-08-17、XRP 2020-05-03、DOGE 2021-07-04、SOL 2022-08-11
 B4 新段起點 t：早年起點＋730 日曆日起，每 h 天一個；必須 t＋h ＜ 原段首起點（嚴格小於）；起點當天收盤必須有值
 B5 模型（同 C12 Q2～Q5，只多處理缺日）：r_t＝ln(C_t/C_{t−1})，任一端缺 ⇒ 缺
    M1＝近 90 個日曆日的 r（去掉缺值）樣本標準差；M3＝EWMA λ0.94，缺值那天不更新，初值＝最早 30 個有值 r² 的平均；
    M2＝擴張窗：所有 t′＋h ≤ t 且兩端都有值的 h 天對數報酬（T1 分位）、所有 t′＋h ≤ t 的「h 天內途中最低」（缺日略過，全缺 ⇒ 不算）的 5% 分位（T2）
    含缺日的 h 窗：照算（端點有值者），另報筆數【執行者補】；沒有缺日時與 researchC12 的函式逐位相同（--check 回歸閘門）
 B6 命中：T1＝下緣 ≤ C_{t+h} ≤ 上緣；T2＝t＋1～t＋h 的日低最小值 ≥ 單邊 95% 下緣（同 C12 Q6）
 B7 判定格＝起點數 ≥ 20 的 (幣, h)：預期 BTC／ETH／XRP 的 h7、h30＋DOGE h7＝7 組 × 3 模型 × 2 目標＝42 格；實算若不是 42 ⇒ 停、照實回報
    起點 ＜ 20 的格（含 SOL 全部、各幣 h90、DOGE h30）只描述
 B8 CI：stationary block bootstrap（researchc1，L＝Politis–White），2,000 次、每格種子 20260923，信賴水準 1−0.05/42；
    Clopper-Pearson 精確區間同信賴水準（researchC12.clopper_pearson）
 B9 判準（登錄 §四＋seq293）：判過＝bootstrap CI 與 CP【都】整條在容忍帶（T1 80～100%、T2 85～100%）；偏窄＝兩者上界都 ＜ 名目；偏寬＝兩者下界都 ＞ 名目；其他＝測不出
    判過與偏窄（或偏寬）同時成立時，依登錄列的順序判過，另註「略窄／略寬」【執行者補，同 C12 Q8】
 B10 描述：起點 ＜ 20 的格、80% 區間、沒守住時平均跌破多少、200 日線／200 週線（近 200／1,400 列收盤均，列＝有值的日子【執行者補】）、
    逐幣資料品質（來源、接縫、缺日、M2 歷史窗碰到缺日或低品質段的筆數、新段結果窗碰到的筆數）
    C12 原段同格命中率只【並列】、⛔ 不合併、⛔ 不算全期命中率
 B11 先驗對答：① M1／M3 的 T2 在 BTC、XRP h7（4 格）都偏窄 ⇒ 中；部分 ⇒ 部分中 ② M2 判定格中至少一格 T1 或 T2 測不出或偏窄 ⇒ 中 ③ 沒有任何 h30 判定格判過 ⇒ 中
 B12 --check：沿用 C12 fixture a～d、f（researchC12.run_fixtures）；新增 e「t＋h 必須 ＜ 原段首起點」（反例：結果窗伸進原段）、
    g「h 天報酬用日曆位移」（反例：缺日時用列位移）；回歸閘門：無缺日幣（SOL）上本支模型＝researchC12 函式；逐列參考迴圈抽樣重算命中（種子 20260923）
⛔ 結果句只說「區間大小準不準」；⛔ 不寫能預測漲跌、⛔ 不寫某價位是底、⛔ 不用下緣推倍數；⛔ 新段與原段不合併成全期命中率。
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, html
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchc1 as C1
import researchC12 as C12
import researchC11 as C11

OUT = os.path.join(C12.REPO, "backtest", "resultsC12b")
COINS = ("BTC", "ETH", "XRP", "DOGE", "SOL")
HS = C12.HS
MODELS = C12.MODELS
MODEL_ZH = C12.MODEL_ZH
TARGETS = C12.TARGETS
NOM, BAND = C12.NOM, C12.BAND
Z90, Z80 = C12.Z90, C12.Z80
LAM = C12.LAM
W_END = C12.W_END
WARM = 730
N_CELLS = 42
MIN_N = 20
SEED = 20260923
N_BOOT = 2000
ORIG_FIRST = {"BTC": "2015-01-01", "ETH": "2019-08-17", "XRP": "2020-05-03", "DOGE": "2021-07-04", "SOL": "2022-08-11"}
FROZEN = "2026-10-04 18:52（台北）"
QUALITY = {"BTC": [("2010-07-17", "2011-12-31", "Mt.Gox 段（第三方鏡像）")], "ETH": [("2015-08-07", "2015-12-31", "Kraken 2015 成交極薄")],
           "XRP": [("2015-02-20", "2015-12-31", "2015 年零成交 162 天、與 BTC 計價換算差 26～85%")]}


# ───────────────────────── 資料（日曆化）─────────────────────────
def load(sym):
    sp = C11.spot_full(sym)
    cal = pd.date_range(sp["date"].iloc[0], W_END).strftime("%Y-%m-%d")
    s = sp.set_index("date").reindex(cal)
    return {"sym": sym, "dates": np.array(cal), "close": s["close"].to_numpy(float), "low": s["low"].to_numpy(float),
            "vol": s["volume"].to_numpy(float), "缺日": [d for d, v in zip(cal, s["close"].to_numpy(float)) if not np.isfinite(v)]}


def logret(c):
    r = np.full(len(c), np.nan); r[1:] = np.log(c[1:]) - np.log(c[:-1]); return r


def ewma_var(c):
    r = logret(c); v = np.full(len(c), np.nan)
    ok = np.flatnonzero(np.isfinite(r))
    v0 = float(np.mean(r[ok[:30]] ** 2)); prev = v0
    first_upd = ok[30] if len(ok) > 30 else len(c)
    for t in range(1, len(c)):
        if t >= first_upd and np.isfinite(r[t]):
            prev = LAM * prev + (1 - LAM) * r[t] ** 2
        v[t] = prev if t >= ok[0] else np.nan
    return v


def sigma_m1(c, s):
    w = logret(c)[s - 89:s + 1]; w = w[np.isfinite(w)]
    return float(np.std(w, ddof=1))


def hret(c, h, mut=None):
    """hr[t]＝ln(C_{t+h}/C_t)（日曆位移；任一端缺 ⇒ NaN）。mut＝rows ⇒ 去掉缺日後用列位移（反例）。"""
    if mut == "rows":
        ok = np.isfinite(c); cc = c[ok]; out = np.full(len(c), np.nan)
        hr = np.log(cc[h:]) - np.log(cc[:-h]); idx = np.flatnonzero(ok)[:len(hr)]; out[idx] = hr
        return out
    out = np.full(len(c), np.nan); out[:-h] = np.log(c[h:]) - np.log(c[:-h]); return out


def pathmin(c, low, h):
    """pm[t]＝min(low_{t+1..t+h}，缺略過)/C_t − 1；全缺或 C_t 缺 ⇒ NaN。"""
    lw = pd.Series(low).rolling(h, min_periods=1).min().to_numpy()
    out = np.full(len(c), np.nan); out[:-h] = lw[h:] / c[:-h] - 1.0; return out


def bounds(c, low, s, h, model, ev=None, hr=None, pm=None, mut=None):
    p0 = c[s]
    if model == "M2":
        hr = hret(c, h, mut) if hr is None else hr
        pm = pathmin(c, low, h) if pm is None else pm
        H = hr[: s - h + 1]; H = H[np.isfinite(H)]
        P = pm[: s - h + 1]; P = P[np.isfinite(P)]
        q05, q95, q10, q90 = np.percentile(H, [5, 95, 10, 90])
        return p0 * math.exp(q05), p0 * math.exp(q95), p0 * math.exp(q10), p0 * math.exp(q90), p0 * (1.0 + float(np.percentile(P, 5)))
    sg = sigma_m1(c, s) if model == "M1" else math.sqrt((ewma_var(c) if ev is None else ev)[s])
    a = sg * math.sqrt(h)
    return p0 * math.exp(-Z90 * a), p0 * math.exp(Z90 * a), p0 * math.exp(-Z80 * a), p0 * math.exp(Z80 * a), p0 * math.exp(-Z90 * a)


def starts_new(dates, close, sym, h, mut=None):
    """B4。mut＝leak ⇒ 只要求 t ＜ 原段首起點（結果窗可伸進原段，反例）。"""
    d0 = pd.Timestamp(dates[0]) + pd.Timedelta(days=WARM)
    i0 = int(np.flatnonzero(dates == d0.strftime("%Y-%m-%d"))[0])
    lim = ORIG_FIRST[sym]
    out = []
    for t in range(i0, len(dates) - h, h):
        endd = dates[t + h]
        if (dates[t] < lim) if mut == "leak" else (endd < lim):
            if np.isfinite(close[t]):
                out.append(t)
        else:
            break
    return np.array(out, int)


# ───────────────────────── CI 與判準 ─────────────────────────
def ci_of(x):
    x = np.asarray(x, float); c = float(x.mean())
    if x.min() == x.max():
        return c, c, c, 1
    L = C1.politis_white_block(x); rng = np.random.default_rng(SEED)
    bs = np.array([x[C1.stationary_idx(len(x), L, rng)].mean() for _ in range(N_BOOT)])
    a = 0.05 / N_CELLS / 2
    return c, float(np.percentile(bs, 100 * a)), float(np.percentile(bs, 100 * (1 - a))), int(L)


def verdict(tg, lo, hi, cpl, cpu):
    blo, bhi = BAND[tg]; nom = NOM[tg]
    if lo >= blo and hi <= bhi and cpl >= blo and cpu <= bhi:
        note = "（略窄，在容忍帶內）" if (hi < nom and cpu < nom) else ("（略寬，在容忍帶內）" if (lo > nom and cpl > nom) else "")
        return "判過" + note
    if hi < nom and cpu < nom:
        return "偏窄"
    if lo > nom and cpl > nom:
        return "偏寬"
    return "測不出"


# ───────────────────────── fixture ─────────────────────────
def fx_e(mut=None):
    """e. 新段結果窗不得碰原段：每個起點 t 的 t＋h ＜ 原段首起點（用 BTC 的真日期軸、合成價格）。"""
    d = pd.date_range("2010-07-17", "2016-01-01").strftime("%Y-%m-%d").to_numpy(); c = np.ones(len(d))
    ok = True
    for h in HS:
        st = starts_new(d, c, "BTC", h, mut)
        ok &= len(st) > 0 and all(d[t + h] < ORIG_FIRST["BTC"] for t in st) and d[st[0]] == "2012-07-16" and np.all(np.diff(st) == h)
    return bool(ok)


def fx_g(mut=None):
    """g. h 天報酬用日曆位移：中間缺 3 天時，ln(C_{t+7}/C_t) 必須是 7 個日曆日之後那天，而不是第 7 列。"""
    c = np.exp(0.01 * np.arange(40)); c[10:13] = np.nan
    hr = hret(c, 7, mut)
    return bool(abs(hr[8] - 0.07) < 1e-12 and np.isnan(hr[3]) and abs(hr[20] - 0.07) < 1e-12)       # t＝8 的窗跨過缺日、兩端有值


def run_fixtures():
    ok12, fx12 = C12.run_fixtures()
    res = [{"案": f"C12-{r['案']}", "結果": r["結果"], "反例": r["反例"], "反例結果": r["反例結果"]} for r in fx12]
    for name, fx, mut, why in (("e 新段 t＋h ＜ 原段首起點", fx_e, "leak", "只要求起點早於原段（結果窗伸進原段）"),
                               ("g h 天報酬用日曆位移（缺日）", fx_g, "rows", "缺日時用列位移")):
        g = fx(); red = not fx(mut)
        res.append({"案": name, "結果": "綠" if g else "紅", "反例": why, "反例結果": "紅（抓得到）" if red else "⛔ 仍綠"})
    return ok12 and all(r["結果"] == "綠" and r["反例結果"].startswith("紅") for r in res), res


# ───────────────────────── 主計算 ─────────────────────────
def run_coin(d):
    c, low, dates = d["close"], d["low"], d["dates"]
    ev = ewma_var(c)
    rowsma = pd.Series(c).dropna()
    ma200 = rowsma.rolling(200).mean().reindex(range(len(c))).to_numpy(); ma1400 = rowsma.rolling(1400).mean().reindex(range(len(c))).to_numpy()
    gapmask = ~np.isfinite(c)
    rows = []
    for h in HS:
        hr = hret(c, h); pm = pathmin(c, low, h)
        for s in starts_new(dates, c, d["sym"], h):
            hist_gap = int(sum(gapmask[t:t + h + 1].any() for t in range(0, s - h + 1)))
            for model in MODELS:
                b = bounds(c, low, s, h, model, ev=ev, hr=hr, pm=pm)
                end = c[s + h]; pmin = float(np.nanmin(low[s + 1:s + h + 1]))
                rows.append({"coin": d["sym"], "h": h, "model": model, "start": dates[s], "end": dates[s + h],
                             "T1": int(b[0] <= end <= b[1]), "T2": int(pmin >= b[4]), "T1_80": int(b[2] <= end <= b[3]),
                             "T1下寬": b[0] / c[s] - 1, "T1上寬": b[1] / c[s] - 1, "T2下寬": b[4] / c[s] - 1,
                             "_T2破幅": (pmin / b[4] - 1) if pmin < b[4] else np.nan, "_T1破幅": (end / b[0] - 1) if end < b[0] else np.nan,
                             "_MA200破": (int(pmin < ma200[s]) if (np.isfinite(ma200[s]) and c[s] > ma200[s]) else np.nan),
                             "_MA1400破": (int(pmin < ma1400[s]) if (np.isfinite(ma1400[s]) and c[s] > ma1400[s]) else np.nan),
                             "_MA200下": (int(c[s] <= ma200[s]) if np.isfinite(ma200[s]) else np.nan),
                             "_MA1400下": (int(c[s] <= ma1400[s]) if np.isfinite(ma1400[s]) else np.nan),
                             "結果窗含缺日": int(gapmask[s:s + h + 1].any()), "M2歷史窗含缺日筆數": hist_gap})
    return pd.DataFrame(rows)


def cells(R, C12cells):
    out = []
    for (coin, h, model), g in R.groupby(["coin", "h", "model"], sort=False):
        g = g.sort_values("start"); n = len(g)
        for tg in TARGETS:
            x = g[tg].to_numpy(); k = int(x.sum())
            c, lo, hi, L = ci_of(x)
            cpl, cpu = C12.clopper_pearson(k, n, 0.05 / N_CELLS)
            judged = (n >= MIN_N) and coin != "SOL"
            ref = C12cells[(C12cells.coin == coin) & (C12cells.h == h) & (C12cells.model == model) & (C12cells.target == tg)]
            tail = float(g["_T2破幅" if tg == "T2" else "_T1破幅"].mean()) if g["_T2破幅" if tg == "T2" else "_T1破幅"].notna().any() else float("nan")
            out.append({"coin": coin, "h": h, "model": model, "target": tg, "起點數": n, "第一個起點": g["start"].iloc[0], "最後起點": g["start"].iloc[-1],
                        "最後結果日": g["end"].iloc[-1], "命中數": k, "命中率": c, "CI下": lo, "CI上": hi, "L": L, "CP下": cpl, "CP上": cpu,
                        "判定格": judged, "判定": verdict(tg, lo, hi, cpl, cpu) if judged else "只描述（起點 < 20）" if coin != "SOL" else "只描述（SOL）",
                        "沒守住時平均跌破": tail, "80%區間命中（描述）": float(g["T1_80"].mean()) if tg == "T1" else float("nan"),
                        "C12原段命中率（只並列）": float(ref["命中率"].iloc[0]) if len(ref) else float("nan"),
                        "C12原段判定（只並列）": ref["判定"].iloc[0] if len(ref) else "",
                        "結果窗含缺日的起點": int(g["結果窗含缺日"].sum())})
    return pd.DataFrame(out)


def ref_hit(c, low, s, h, model):
    """逐列純迴圈參考實作（日曆、缺值略過）。"""
    p0 = c[s]
    def lr(t):
        return math.log(c[t] / c[t - 1]) if (t >= 1 and np.isfinite(c[t]) and np.isfinite(c[t - 1])) else None
    if model == "M1":
        rs = [x for x in (lr(t) for t in range(s - 89, s + 1)) if x is not None]
        mu = sum(rs) / len(rs); sg = math.sqrt(sum((x - mu) ** 2 for x in rs) / (len(rs) - 1)); lo1 = p0 * math.exp(-Z90 * sg * math.sqrt(h)); hi1 = p0 * math.exp(Z90 * sg * math.sqrt(h)); lo2 = lo1
    elif model == "M3":
        rs = [x for x in (lr(t) for t in range(1, s + 1)) if x is not None]
        v0 = sum(x * x for x in rs[:30]) / 30; v = v0
        for k, x in enumerate(rs):
            if k >= 30:
                v = LAM * v + (1 - LAM) * x * x
        sg = math.sqrt(v); lo1 = p0 * math.exp(-Z90 * sg * math.sqrt(h)); hi1 = p0 * math.exp(Z90 * sg * math.sqrt(h)); lo2 = lo1
    else:
        H, P = [], []
        for t in range(0, s - h + 1):
            if np.isfinite(c[t]) and np.isfinite(c[t + h]):
                H.append(math.log(c[t + h] / c[t]))
            seg = [x for x in low[t + 1:t + h + 1] if np.isfinite(x)]
            if np.isfinite(c[t]) and seg:
                P.append(min(seg) / c[t] - 1)
        lo1, hi1 = p0 * math.exp(float(np.percentile(H, 5))), p0 * math.exp(float(np.percentile(H, 95))); lo2 = p0 * (1 + float(np.percentile(P, 5)))
    end = c[s + h]; pmin = min(x for x in low[s + 1:s + h + 1] if np.isfinite(x))
    return int(lo1 <= end <= hi1), int(pmin >= lo2)


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return C12.pct(x, nd)


def build_html(meta, Cc, fx, chk):
    e = html.escape
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>區間校準早年新段</title><style>{C12.CSS}</style></head><body><main>"]
    h.append("<h1>價格區間預測：早年新段（只判補出來的資料）</h1>")
    h.append(f"<div class='sub'>PREREGC12b v1（N＝42，批4）｜回測線｜早年長序列（私有庫）＋公開 main {C12.SHA[:10]}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論（只談區間大小準不準；新段 42 格）</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             "<div class='small'>⛔ 不是漲跌方向的預測、不表示哪個價位是底；「判過」只代表在 ±10pp 容忍帶內分不出偏差。⛔ 新段與 C12 原段只並列、不合併。</div></div>")
    h.append("<div class='card'><b>⚠ 先講清楚</b>：新段的<b>價格</b>以前看過、<b>命中結果</b>沒算過——BTC 2013～2014 用於 C11 長歷史臂與 C12 暖機；ETH 2018 用於 C11 長歷史臂；"
             "回測線同日重跑 C11 長歷史臂時也用過各幣早年價格（只算強平）。<br>新段＝各幣早年起點＋730 天起、每 h 天一個起點，而且結果窗結束日早於 C12 原段第一個起點；起點不到 20 個的格只描述；BNB 沒有早年美元價、不納入；SOL 只描述。"
             "<br>判過＝bootstrap CI 與 Clopper-Pearson 精確區間（信賴水準 1−0.05/42）<b>都</b>在容忍帶（T1 80～100%、T2 85～100%）；偏窄／偏寬＝兩者同向。</div>")
    for tg in TARGETS:
        h.append(f"<h2>{'一' if tg == 'T1' else '二'}、{tg}：{'第 h 天收盤落在 90% 區間' if tg == 'T1' else 'h 天內最低價守住 95% 下緣'}</h2>")
        h.append("<div class='small'>每格：命中數／起點數＝命中率；boot＝bootstrap CI；CP＝精確區間；判定。灰字＝C12 原段同格（只並列）。</div>")
        h.append("<div class='tw'><table><tr><th>幣（新段起點）</th><th>h</th>" + "".join(f"<th>{MODEL_ZH[m]}</th>" for m in MODELS) + "</tr>")
        for s in COINS:
            for hh in HS:
                g = Cc[(Cc.coin == s) & (Cc.h == hh) & (Cc.target == tg)]
                if not len(g):
                    continue
                cl = []
                for m in MODELS:
                    r = g[g.model == m].iloc[0]
                    cls = "narrow" if r["判定"] == "偏窄" else ("pass" if r["判定"].startswith("判過") else "")
                    ci = f"<br>boot［{pct(r['CI下'])}～{pct(r['CI上'])}］<br>CP［{pct(r['CP下'])}～{pct(r['CP上'])}］" if r["判定格"] else ""
                    cl.append(f"<td>{int(r['命中數'])}／{int(r['起點數'])}＝{pct(r['命中率'])}{ci}<br><span class='{cls}'>{e(r['判定'])}</span>"
                              f"<br><span class='small'>原段 {pct(r['C12原段命中率（只並列）'])}</span></td>")
                r0 = g.iloc[0]
                h.append(f"<tr><td>{s}（{r0['第一個起點']}～）</td><td>{hh}</td>" + "".join(cl) + "</tr>")
        h.append("</table></div>")
    J = Cc[Cc["判定格"]]
    h.append("<h2>三、判定彙總（42 格）</h2><div class='tw'><table><tr><th>目標</th><th>模型</th><th>判過</th><th>偏窄</th><th>偏寬</th><th>測不出</th></tr>")
    for tg in TARGETS:
        for m in MODELS:
            g = J[(J.target == tg) & (J.model == m)]
            k = lambda p: int(g["判定"].str.startswith(p).sum())
            h.append(f"<tr><td>{tg}</td><td>{MODEL_ZH[m]}</td><td>{k('判過')}</td><td>{k('偏窄')}</td><td>{k('偏寬')}</td><td>{k('測不出')}</td></tr>")
    h.append("</table></div>")
    h.append("<h2>四、描述</h2><h3>80% 區間、沒守住時平均跌破</h3><div class='tw'><table><tr><th>幣</th><th>h</th><th>模型</th><th>80% 命中</th><th>T2 沒守住平均跌破</th></tr>")
    for _, r in Cc[Cc.target == "T1"].iterrows():
        t2 = Cc[(Cc.coin == r.coin) & (Cc.h == r.h) & (Cc.model == r.model) & (Cc.target == "T2")].iloc[0]
        h.append(f"<tr><td>{r.coin}</td><td>{r.h}</td><td>{r.model}</td><td>{pct(r['80%區間命中（描述）'])}</td><td>{pct(t2['沒守住時平均跌破'], 1)}</td></tr>")
    h.append("</table></div>")
    h.append("<h3>200 日線、200 週線當下緣（只描述）</h3><div class='small'>只算起點在均線之上的起點：h 天內日低跌破均線的比例（括號＝起點已在均線下的比例）。均線＝近 200／1,400 個有值日子的收盤平均。</div>")
    h.append("<div class='tw'><table><tr><th>幣</th><th>均線</th>" + "".join(f"<th>h{x}</th>" for x in HS) + "</tr>")
    for row in meta["均線描述"]:
        h.append(f"<tr><td>{row['coin']}</td><td>{row['均線']}</td>" + "".join(f"<td>{row[str(x)]}</td>" for x in HS) + "</tr>")
    h.append("</table></div>")
    h.append("<h3>逐幣資料品質</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["資料品質"]) + "</ul>")
    h.append("<h2>五、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>六、驗證</h2><div class='tw'><table><tr><th>fixture</th><th>結果</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td style='white-space:normal'>{e(r['案'])}</td><td>{r['結果']}</td><td style='white-space:normal'>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>抽樣逐列重算：{chk.get('一致數', '—')}／{chk.get('抽樣數', '—')} 一致；無缺日幣回歸閘門（本支模型＝C12 函式）：{e(str(chk.get('回歸閘門', '—')))}。</div>")
    h.append("<h2>七、讀的時候要注意</h2><ul><li>h30 只有 20～40 個起點，依構造幾乎判不出「判過」。</li><li>早年交易所價差大（ETH 接縫最大 4.2%）、Mt.Gox 末期價格偏離；照實用。T2 用現貨日低；合約插針可能更深。</li>"
             "<li>私有資料只放彙總：本頁與 csv 沒有任何價格列。</li><li>⛔ 不得把區間當價格預測對外講、⛔ 不得用下緣推倍數、⛔ 不構成買賣建議。</li></ul>")
    h.append("<h2>八、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in EXEC_SUPPLIED) + "</ul></main></body></html>")
    return "\n".join(h)


EXEC_SUPPLIED = [
    "B2 用日曆日：缺日留空、不補；h 天＝h 個日曆日（與 C12 同義）",
    "B5 缺日處理：M1 去掉缺值；M3 缺值那天不更新；M2 端點缺就不算、途中最低略過缺日；含缺日的 h 窗照算並另報筆數",
    "B9 判過與偏窄／偏寬同時成立時依登錄順序判過、另註略窄／略寬（同 C12 Q8）",
    "B10 均線用近 200／1,400 個有值日子（列）",
    "B13 私有資料：結果檔只放 0／1 命中與區間相對寬度，不放價格、不放逐起點實現報酬",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['結果']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    data = {s: load(s) for s in COINS}
    for s in COINS:
        d = data[s]
        print(f"[{s}] {d['dates'][0]}～{d['dates'][-1]}｜缺日 {len(d['缺日'])}｜新段起點數 " + "／".join(str(len(starts_new(d['dates'], d['close'], s, hh))) for hh in HS))
    if a.check:
        # 回歸閘門：SOL（無缺日）上本支模型＝C12 函式
        d = data["SOL"]; c, low = d["close"], d["low"]; evb = ewma_var(c); ev12 = C12.ewma_var(c); gate = []
        for s_ in (800, 1200, 1800):
            for model in MODELS:
                for h in HS:
                    b1 = bounds(c, low, s_, h, model, ev=evb); b2 = C12.bounds(c, low, s_, h, model, ev=ev12)
                    gate.append(float(np.max(np.abs(np.array(b1) / np.array(b2) - 1))))
        R = pd.concat([run_coin(data[s]) for s in COINS], ignore_index=True)
        rng = np.random.default_rng(SEED); idx = rng.choice(len(R), 30, replace=False); rows = []
        for i in idx:
            r = R.iloc[int(i)]; d = data[r.coin]; s_ = int(np.flatnonzero(d["dates"] == r.start)[0])
            t1, t2 = ref_hit(d["close"], d["low"], s_, int(r.h), r.model)
            rows.append({"coin": r.coin, "h": int(r.h), "model": r.model, "start": r.start, "一致": bool(t1 == r.T1 and t2 == r.T2)})
        chk = {"讀法寫死": FROZEN, "fixture全過": ok, "fixture": fx, "回歸閘門": f"SOL 27 組最大相對差 {max(gate):.1e}", "抽樣數": len(rows), "一致數": int(sum(x["一致"] for x in rows)), "抽樣": rows, "種子": SEED}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"[check] 回歸閘門 {chk['回歸閘門']}｜抽樣 {chk['一致數']}／{chk['抽樣數']} 一致")
        assert max(gate) < 1e-12 and chk["一致數"] == chk["抽樣數"]
        return
    R = pd.concat([run_coin(data[s]) for s in COINS], ignore_index=True)
    C12cells = pd.read_csv(os.path.join(C12.OUT, "cells.csv"))
    Cc = cells(R, C12cells)
    nj = int(Cc["判定格"].sum())
    assert nj == N_CELLS, f"⛔ 判定格 {nj} ≠ 42，停"
    Cc.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    R[[c for c in R.columns if not c.startswith("_")]].to_csv(os.path.join(OUT, "starts.csv"), index=False)
    # 均線描述
    mad = []
    for s in COINS:
        for col, nm in (("_MA200", "200 日線"), ("_MA1400", "200 週線（1,400 列）")):
            row = {"coin": s, "均線": nm}
            for hh in HS:
                g = R[(R.coin == s) & (R.h == hh) & (R.model == "M1")]
                br = g[col + "破"].dropna(); dn = g[col + "下"].dropna()
                row[str(hh)] = f"{pct(br.mean()) if len(br) else '—'}（{pct(dn.mean()) if len(dn) else '—'}；n＝{len(dn)}）"
            mad.append(row)
    # 資料品質
    ql = []
    for s in COINS:
        d = data[s]; g = R[(R.coin == s) & (R.model == "M1")]
        line = f"{s}：長序列 {d['dates'][0]} 起；缺日 {len(d['缺日'])} 天" + (f"（{'、'.join(d['缺日'])}）" if d["缺日"] else "")
        line += f"；新段結果窗含缺日的起點 {int(g['結果窗含缺日'].sum())} 個；M2 歷史窗含缺日（最後一個 h7 起點時）{int(g[g.h == 7]['M2歷史窗含缺日筆數'].max()) if len(g[g.h == 7]) else 0} 筆"
        for a_, b_, txt in QUALITY.get(s, []):
            line += f"；{a_}～{b_} {txt}：新段結果窗碰到 {int(((g['start'] <= b_) & (g['end'] >= a_)).sum())} 個起點，M2 歷史全部含這段"
        if s == "XRP":
            zv = int(((data[s]["vol"] == 0) & (data[s]["dates"] < "2017-01-01")).sum())
            line += f"；零成交日（2016 年以前）{zv} 天，全在暖機內"
        ql.append(line)
    # 先驗
    J = Cc[Cc["判定格"]]
    p1 = J[(J.target == "T2") & (J.h == 7) & J.coin.isin(["BTC", "XRP"]) & J.model.isin(["M1", "M3"])]
    n1 = int((p1["判定"] == "偏窄").sum())
    pri = [f"① M1／M3 的 T2 在 BTC、XRP h7 偏窄：{n1}／{len(p1)} 格偏窄（{'、'.join(f'{r.coin} {r.model} {r.判定}' for r in p1.itertuples())}）⇒ " + ("中" if n1 == len(p1) else ("部分中" if n1 else "未中"))]
    p2 = J[(J.model == "M2") & (J["判定"].isin(["測不出", "偏窄"]))]
    pri.append(f"② M2 在新段至少一格測不出或偏窄：{len(p2)} 格（{'、'.join(f'{r.coin} h{r.h} {r.target} {r.判定}' for r in p2.itertuples()) or '無'}）⇒ " + ("中" if len(p2) else "未中"))
    p3 = J[(J.h == 30) & J["判定"].str.startswith("判過")]
    pri.append(f"③ 沒有任何 h30 格判過：h30 判過 {len(p3)} 格 ⇒ " + ("中" if len(p3) == 0 else "未中"))
    lines = []
    for tg in TARGETS:
        for m in MODELS:
            g = J[(J.target == tg) & (J.model == m)]
            k = lambda p: int(g["判定"].str.startswith(p).sum())
            lines.append(f"<b>{tg}・{MODEL_ZH[m]}</b>：7 格中 判過 {k('判過')}、偏窄 {k('偏窄')}、偏寬 {k('偏寬')}、測不出 {k('測不出')}；命中率 {pct(g['命中率'].min())}～{pct(g['命中率'].max())}（名目 {pct(NOM[tg])}）。")
    meta = {"登錄": "PREREGC12b 早年新段 v1 shac06764755e711a2a", "裁定": "seq294 §一（N＝42，批4）", "讀法寫死": FROZEN, "公開資料commit": C12.SHA, "私有資料": "~/us-stock-data data/crypto_private（本機 clone）",
            "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "原段首起點": ORIG_FIRST,
            "新段": {s: {str(hh): [int(len(starts_new(data[s]['dates'], data[s]['close'], s, hh)))] for hh in HS} for s in COINS},
            "判定格數": nj, "結論行": lines, "先驗對答": pri, "均線描述": mad, "資料品質": ql, "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1)}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "價格區間預測校準_早年新段.html"), "w", encoding="utf-8").write(build_html(meta, Cc, fx, chk))
    import re
    for x in lines + pri + ql:
        print(re.sub(r"<[^>]+>", "", x))
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

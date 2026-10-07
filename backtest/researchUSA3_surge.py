# -*- coding: utf-8 -*-
"""USREG-A3-17：飆股回推比對【價量特徵部分】在美股（S&P 500＋400 聯集）——只做探索段挑特徵；⛔ 挑定後就停，⛔ 不開驗證段 2024～2026-09。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_surge --run [--procs 2] [--limit 80]
    ...                                                                                       --check

判準：台股 PREREG飆股回推 seq7（sha 15a22c6b6c2c36d0；§十 取代舊參數、§十一 近年版：找 2021～2023、驗 2024～）；
      裁定 seq311（飆股＝seq6 網格、取格中位，⛔ 不寫「N 天漲一倍」）、seq318（美股母體重算網格、⛔ 不搬台股門檻）、
      seq319 Q16（先用美股母體網格產生標籤，在探索段 2021～2023 挑特徵；挑定後交裁定，才開驗證段；N 照驗證段實際驗的特徵數）。
台股原程式（只參考移植、⛔ 未改）：researchSurge5.py（stock()、qtie、S1～S19）、researchSurge5_feat.py（levels、ratio_stats、family）、researchSurge6.py（U1～U12）。
共用底座：researchUSA3_core.py（C1～C10）。開跑前清單：researchUSA34_prep.py P1（飆股 2021-01～、找 2021～2023）、PREP_REPORT A3-17 列。

═══ 美股補讀法（G 標；⭐ 寫死於 2026-10-07 11:55（台北），寫死前 ⛔ 沒看任何美股飆股標籤、提升倍數或報酬）═══
 G1 列 ＝ 觀察日 t × 股；母體 ＝ t 當天在 S&P 500 或 S&P 400（聯集，P2）且有有效 K 棒（台股 S2「全部上市櫃普通股」的美股對應；
    ⛔ 不套流動性閘）。三欄：合併（挑選用，C2）、只 S&P 400、只 S&P 500（t 當天歸屬；描述）。
 G2 壞根（台股 S3）＝ 轉接層 hard_break（seam／split_div，cache 的 pb）；純停牌缺口不算壞根（同 S3）；下市／移出資料後收盤沿用最後一價（同 S4）。
    ⚠ 台股的「幽靈還原、價格斷點」美股對應就是 hard_break；RU.prep 的跳躍旗標（jb）不當壞根（A2 全批同規則）。
 G3 標籤（S4～S7＋§十一）：資料尾 ＝ 窗尾 2026-09-30（U4b 同義）；hdef ＝ min(250, 資料尾−t, 下一個壞根−1−t)；
    起漲日 t 只取探索段 2021-01-04～2023-12-29（⭐ 驗證段的 t 一律不建事件、不算任何量）；鏈從 2021-01-04 起算、只在母體列上數（不在母體的日子不成事件、也不在分母）；
    網格 H ∈ {10,…,250}（25）× g ∈ {50,100,150,200,250,300,400,500,700,1000%}（10）＝ 250 格；「≥ g」以 收盤 ≥ t 收盤 ×（1＋g）×（1−1e−9）判。
    P ＝ (t, t＋H] 最高收盤那天（同價取最早）；P 後回落 x%（x ∈ 10,20,30,50,70）觀察到 min(最後有效 K 棒, 下一個壞根−1, 資料尾)。
 G4 特徵（價量部分；S9 回看 5／10／20／60／120／250 並列；門檻型改連續值五等分；原門檻版只描述 ⛔ 不進挑選）：
    價：報酬、距 L 日最高／最低、收盤÷MA_L−1、L 日區間寬度、L 日帶寬÷自身 250 根中位、L 日抗跌（^SP500TR 下跌日的個股−指數平均日報酬；台股 0050 的美股對應）、
        前 L 日 MA5/10/20 糾結度｜量：當日額÷前 L 日均額、近 L 日均額÷再前 L 日均額、L 日均額、L 日平均周轉率｜
    技術：KD 的 K、K＞80 連續天數、RSI14、RSI6−RSI12、收盤÷布林上軌−1、EMA5/10/20 最大÷最小−1、EMA20＞SMA20 連續天數、收盤÷修正箱上箱價−1、均線多頭排列段數｜
    規模：市值、股數、股價｜大盤：^GSPC 收盤÷MA_L−1（時序五等分：自身前 750 日分位，同 S10）｜產業：GICS sector 的 L 日報酬（成分平均、≥3 檔、≥5 類）在類間五等分。
    原門檻描述：均線多頭排列 5>20>60>100、站上 MA100、^GSPC 在 200 日線上、K1（K>80 連 3 日）與級距、K2、K3 兩版、K4、K5 周轉率 ≥10%／≥20%、V1、V2 級距、V3、X1、X2、X3、量縮狀態。
    拿掉（美股沒有，PREP_REPORT）：漲停天數、法人、融資、借券、集保、注意／處置、新聞；營收、財報類屬 A4-10（本件不做）。
    額 ＝ 還原收盤 × Yahoo 拆股調整量（近似美元成交額；⚠ 早年含息調整使水準略低，只影響 L 日均額的橫斷面五等分）；
    股數 ＝ SEC 封面股數（filed＜t 的最新 as_of，同 as_of 多類別相加，as_of 距 t ＞400 天當缺；同 as_of 多次申報取最晚 filed）＋ Yahoo 拆股乘回（P8）；
    周轉率 ＝ 拆股調整量 ÷ 股數乘到今天基準（P8）；市值 ＝ t 原始收盤 × 股數（t 基準）；股價 ＝ t 原始收盤（台股元級距 → 價位五等分，PREP_REPORT）。
    G4b（⚠ 補寫於 2026-10-07 14:50（台北），A4 子代理發現、協調者轉達；第一次全量跑之後）：prices_yahoo 的 close 已按「日後拆股」調整（AAPL 2020-08-28 close 124.8、原始約 499），
        prep 的 raw_close_aligned 當原始收盤用 ⇒ 日後有拆股的股票市值、股價被低估。改為 yahoo 來源 close × Π(拆股比，拆股日 > 該日)；prices（tiingo）來源 close 本來就是原始。
        只影響 mcap、price 兩個特徵（周轉率不受影響）；修正後全部重跑。
    產業層級：GICS sector（B3 sector_pit 直接有的層級）。⚠ seq319 Q8 的 industry group 是 A4-5／A4-6 的裁示；本件只一個描述性特徵類 ⇒ 不另建對照表，照實標。
 G5 ①②（S11）：① ＝ 有特徵者（該格 H 定義域內）事件比例 ÷ 同段「該特徵有值」者事件比例，曆月分群 CR0（依 t 的月份）95% CI；② ＝ 事件中有特徵的比例。
    挑選（S12＋§十一之二）：探索段 250 格中 ≥125 格「① 95% 下緣 ＞ 1 且 ② ≥ 5%」⇒ 進驗證段（⛔ 不設名額上限）；只用合併欄挑（C2）；只 400、只 500 欄同式只報格數（描述）。
    「網格中位」（seq311）：每個特徵級距的頭條數 ＝ 250 格 ① 的中位（附 p10～p90）、② 的中位。
 G6 妖股族（S15）：各格事件內，特徵（看 t）對「P 後回落 30／50／70%」的 ①②；挑法同 G5（每個 x 一族）。
    結束族（S16）：各格、x ∈ {10,20,30}（P 後曾回落 x% 的事件）× k ∈ {1,3,5,10,20}：陽性 ＝ P−k 那天、對照 ＝ 同事件漲勢中段 t＋(P−t)//2（須 P−中段 ＞ 20、中段 ＞ t）；
    挑法同 G5（每個 x×k 一族）。⚠ P−k、中段可落在 2024（事件 t 在探索段、月份依 t）⇒ 特徵表存到 2024-12-31，只供這兩個位置讀，⛔ 不產生任何 2024 起漲日的量。
 G7 N（S17）＝ 驗證段實際驗的級距數（各族加總）＝ 本步挑出的數；⛔ 本步不驗，交裁定。
 G8 ③ 可交易曲線、買不買得到（S13、S14）、結束可交易（S19）：本步不算（只用 ①② 挑；美股無漲停鎖死、處置 ⇒ S14 只剩 t＋1 無成交，驗證時一起報）。
 G9 |ret|＞50% 敏感度（C8）：S&P 400 未確認 23 列也當壞根，重建標籤與定義域、重挑（特徵不重算），報挑出名單變化。
 G10 輸出只有彙總（級距 × 網格中位、格數、挑出名單）；逐列特徵、事件表只在 ~/us_work/a3/surge/。
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_core as C
U = C.U

READ_TS = "2026-10-07 11:55（台北）"
WORKS = os.path.join(C.WORK, "surge")
HS = tuple(range(10, 251, 10))
GS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
NC = len(HS) * len(GS)
HALF = NC // 2
LB = (5, 10, 20, 60, 120, 250)
DD = (0.10, 0.20, 0.30, 0.50, 0.70)
KEND = (1, 3, 5, 10, 20)
Z95 = 1.959963984540054
SURGE0 = pd.Timestamp("2021-01-04")
EXP_LAST = pd.Timestamp("2023-12-31")
STORE_LAST = pd.Timestamp("2024-12-31")
HI_OF_CELL = np.array([c // len(GS) for c in range(NC)])
_G: dict = {}


def cell_of(hi, gi):
    return hi * len(GS) + gi


def cell_name(c):
    return f"H{HS[c // len(GS)]}_g{int(round(GS[c % len(GS)] * 100))}%"


def feature_specs():
    """(欄, 名稱, 類別, 型態)；q＝橫斷面五等分｜qts＝時序五等分（已是 1～5）｜x＝類間五等分（已是 1～5）｜dbin／dlvl＝原門檻描述。"""
    F = []
    for L in LB:
        F += [(f"r_{L}", f"{L}日報酬", "價", "q"), (f"dhi_{L}", f"距{L}日最高", "價", "q"), (f"dlo_{L}", f"距{L}日最低", "價", "q"),
              (f"ma_{L}", f"收盤÷MA{L}−1", "價", "q"), (f"rng_{L}", f"{L}日區間寬度", "價", "q"), (f"bbw_{L}", f"{L}日帶寬÷自身250根中位", "價", "q"),
              (f"anti_{L}", f"{L}日抗跌（對^SP500TR）", "價", "q"), (f"tang_{L}", f"前{L}日均線5/10/20糾結度", "價", "q"),
              (f"ar_{L}", f"當日額÷前{L}日均額", "量", "q"), (f"achg_{L}", f"近{L}日均額÷再前{L}日均額", "量", "q"),
              (f"amt_{L}", f"{L}日均額", "量", "q"), (f"turn_{L}", f"{L}日平均周轉率", "量", "q")]
    F += [("kdK", "KD的K值", "技術", "q"), ("kdrun", "K＞80連續天數", "技術", "q"), ("rsi14", "RSI14", "技術", "q"),
          ("rsid", "RSI6−RSI12", "技術", "q"), ("bbup", "收盤÷布林上軌(20,2)−1", "技術", "q"), ("x3", "EMA5/10/20最大÷最小−1", "技術", "q"),
          ("v2run", "EMA20＞SMA20連續天數", "技術", "q"), ("v3box", "收盤÷修正箱上箱價−1", "技術", "q"),
          ("maalign", "均線多頭排列段數(5/10/20/60/120/250)", "技術", "q"),
          ("mcap", "市值", "規模", "q"), ("shares", "股數", "規模", "q"), ("price", "股價（原始收盤）", "規模", "q")]
    for L in LB:
        F += [(f"mkt_{L}", f"^GSPC收盤÷MA{L}−1（時序）", "大盤", "qts")]
    for L in LB:
        F += [(f"indrk_{L}", f"GICS sector {L}日報酬排名", "產業", "x")]
    F += [("d_bull", "原：均線多頭排列5>20>60>100", "價", "dbin"), ("d_ma100", "原：收盤站上MA100", "價", "dbin"),
          ("d_mkt200", "原：^GSPC在200日線上（0050的代理）", "大盤", "dbin"),
          ("d_K1", "原K1 KD高檔鈍化(K>80連3日)", "技術", "dbin"), ("d_K1l", "原K1 K>80連續天數級距", "技術", "dlvl"),
          ("d_K2", "原K2 布林上軌帶量突破", "技術", "dbin"), ("d_K3a", "原K3 RSI14>50", "技術", "dbin"),
          ("d_K3b", "原K3 RSI6上穿RSI12", "技術", "dbin"), ("d_K4", "原K4 均線糾結後發動", "技術", "dbin"),
          ("d_K5a", "原K5 周轉率≥10%", "量", "dbin"), ("d_K5b", "原K5 周轉率≥20%", "量", "dbin"),
          ("d_V1", "原V1 量縮盤整後帶量突破", "技術", "dbin"), ("d_V2l", "原V2 EMA20>SMA20連續天數級距", "技術", "dlvl"),
          ("d_V3", "原V3 修正箱突破", "技術", "dbin"), ("d_X1", "原X1 熊狗篩選", "技術", "dbin"),
          ("d_X2", "原X2 區間突破後量縮", "技術", "dbin"), ("d_X3", "原X3 EMA糾結向上", "技術", "dbin"),
          ("d_shrink", "原：量縮狀態(20日均額≤前120日均額×0.7)", "量", "dbin")]
    return F


SPECS = feature_specs()
FCOL = [f[0] for f in SPECS]
FIX = {c: i for i, c in enumerate(FCOL)}
LVLN = {"d_K1l": {0: "0 天", 1: "1～2 天", 2: "3～5 天", 3: "≥6 天"}, "d_V2l": {0: "0 天", 1: "1～4 天", 2: "5～9 天", 3: "≥10 天"}}


def levels():
    """(欄索引, 欄, 級距碼, 級距名, 名稱, 類別, 型態, 進挑選)"""
    out = []
    for col, name, cat, kind in SPECS:
        fi = FIX[col]
        if kind in ("q", "qts", "x"):
            for q in range(1, 6):
                out.append((fi, col, q, f"Q{q}", name, cat, kind, True))
        elif kind == "dbin":
            out.append((fi, col, 2, "是", name, cat, kind, False))
        elif kind == "dlvl":
            for v, nm in LVLN[col].items():
                out.append((fi, col, v + 1, nm, name, cat, kind, False))
    return out


# ═════════════ 小工具（台股 researchSurge5／surge_features 同式，逐字移植）═════════════
def _roll(x, w, fn):
    return getattr(pd.Series(x).rolling(w, min_periods=w), fn)().to_numpy()


def _prev(x, k=1):
    return np.r_[np.full(k, np.nan), x[:-k]] if k < len(x) else np.full(len(x), np.nan)


def kd(Cc, Hh, Ll):
    n = len(Cc); K = np.full(n, np.nan); k0 = d0 = 50.0
    for t in range(8, n):
        lo, hi = Ll[t - 8:t + 1].min(), Hh[t - 8:t + 1].max()
        rsv = 50.0 if hi - lo <= 0 else (Cc[t] - lo) / (hi - lo) * 100
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3; K[t] = k0
    return K


def rsi(Cc, n_):
    out = np.full(len(Cc), np.nan)
    if len(Cc) <= n_:
        return out
    d = np.diff(Cc); g = np.maximum(d, 0); l_ = np.maximum(-d, 0)
    ag, al = g[:n_].mean(), l_[:n_].mean()
    for t in range(n_, len(Cc)):
        if t > n_:
            ag = (ag * (n_ - 1) + g[t - 1]) / n_; al = (al * (n_ - 1) + l_[t - 1]) / n_
        out[t] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def ema(x, n_):
    a = 2.0 / (n_ + 1); out = np.empty(len(x)); out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = a * x[t] + (1 - a) * out[t - 1]
    return out


def run_len(flag):
    out = np.zeros(len(flag), int); r = 0
    for i, f in enumerate(flag):
        r = r + 1 if f else 0; out[i] = r
    return out


def qtie(v):
    """同值同組五等分（S10）：rank ＝ 嚴格小於的個數；q ＝ rank×5÷k＋1；NaN ⇒ 0。"""
    out = np.zeros(len(v), np.int8); ok = np.flatnonzero(np.isfinite(v)); k = len(ok)
    if k == 0:
        return out
    x = v[ok]; srt = np.sort(x)
    out[ok] = (np.searchsorted(srt, x, side="left") * 5 // k + 1).astype(np.int8)
    return out


def ratio_stats(e, nn, eall, nall, cov_num, cov_den, z):
    """台股 researchSurge5_feat.ratio_stats 原式。"""
    N = nn.sum(1); Nall = nall.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = e.sum(1) / N
        se = np.sqrt(((e - p[:, None] * nn) ** 2).sum(1)) / N
        base = eall.sum(1) / Nall
        lift = p / base; lo = (p - z * se) / base; hi = (p + z * se) / base
        cov = cov_num / cov_den
    lift[~(base > 0)] = np.nan; lo[~(base > 0)] = np.nan
    return lift, lo, hi, cov


# ═════════════ 外部序列：股數、拆股、原始收盤、大盤、產業 ═════════════
def load_shares():
    sh = pd.read_csv(U._p("fundamentals", "shares_outstanding.csv"), dtype={"ticker": str, "share_class": str})
    sh["as_of_date"] = pd.to_datetime(sh["as_of_date"]); sh["filed"] = pd.to_datetime(sh["filed"])
    sh = sh.dropna(subset=["shares"])
    sh = sh.groupby(["ticker", "as_of_date", "filed"], as_index=False)["shares"].sum()
    out = {t: (g["as_of_date"].values.astype("datetime64[D]").astype(np.int64), g["filed"].values.astype("datetime64[D]").astype(np.int64),
               g["shares"].to_numpy(float)) for t, g in sh.groupby("ticker")}
    spl = {}
    for fn in os.listdir(U._p("events_yahoo")):
        d = pd.read_csv(U._p("events_yahoo", fn), dtype=str)
        d = d[d["type"] == "split"]
        if len(d):
            r = d["value"].str.split("/", expand=True).astype(float)
            spl[fn[:-4]] = (pd.to_datetime(d["date"]).values.astype("datetime64[D]").astype(np.int64), (r[0] / r[1]).to_numpy())
    return out, spl


def shares_daily(sh, spl, cald):
    """→ (股數_當日基準, 股數_今天基準)：filed＜e 的最新 as_of（同 as_of 取最晚 filed）、as_of 距 e ＞400 天當缺、拆股乘回（P8）。"""
    n = len(cald); a = np.full(n, np.nan); b = np.full(n, np.nan)
    if sh is None:
        return a, b
    ad, fd, v = sh
    order = np.argsort(fd, kind="stable")
    ad, fd, v = ad[order], fd[order], v[order]
    sd, r = spl if spl is not None else (np.zeros(0, np.int64), np.zeros(0))
    best_ad, best_v = None, np.nan; j = 0
    for i in range(n):
        e = cald[i]
        while j < len(fd) and fd[j] < e:
            if best_ad is None or ad[j] >= best_ad:
                best_ad, best_v = ad[j], v[j]
            j += 1
        if best_ad is None or e - best_ad > 400:
            continue
        m1 = (sd > best_ad) & (sd <= e); m2 = sd > best_ad
        a[i] = best_v * (float(np.prod(r[m1])) if m1.any() else 1.0)
        b[i] = best_v * (float(np.prod(r[m2])) if m2.any() else 1.0)
    return a, b


_RC = {}


def raw_close_aligned(t, cal, valid, spl=None):
    """原始收盤：照 panel 每列 src 讀 close；yahoo 來源再乘回日後拆股比（G4b；prep 同名函式沒乘 ⇒ 偏離 prep、照實寫）。"""
    pn = U.panel(t)
    R = np.full(len(cal), np.nan)
    for src, g in pn.groupby("src", sort=False):
        if src not in _RC:
            kind, f = src.split(":", 1)
            d = pd.read_csv(U._p("prices_yahoo" if kind == "yahoo" else "prices", f + ".csv"), usecols=["date", "close"], dtype={"date": str})
            _RC[src] = pd.Series(d["close"].to_numpy(float), index=pd.DatetimeIndex(pd.to_datetime(d["date"])))
        idx = g.index[g.index.isin(cal)]
        v = _RC[src].reindex(idx).to_numpy(float)
        if src.startswith("yahoo:") and spl is not None:
            sd, r = spl
            dd = idx.values.astype("datetime64[D]").astype(np.int64)
            v = v * np.array([float(np.prod(r[sd > x])) if (sd > x).any() else 1.0 for x in dd])
        R[cal.get_indexer(idx)] = v
    R[~valid] = np.nan
    return R


def market(cal):
    g = pd.read_csv(U._p("macro", "yahoo_GSPC.csv"), usecols=["date", "close"], dtype={"date": str})
    gs = pd.Series(g["close"].to_numpy(float), pd.DatetimeIndex(pd.to_datetime(g["date"]))).sort_index()
    # 時序五等分要前 750 日 ⇒ 用 ^GSPC 自己的日子算，再對齊 cal
    b_full = gs.to_numpy(); n_ = len(b_full)
    MK = {}
    for L in LB:
        v = b_full / pd.Series(b_full).rolling(L, min_periods=L).mean().to_numpy() - 1
        q = np.full(n_, np.nan)
        start = max(0, int(gs.index.searchsorted(cal[0])) - 5)
        for t in range(start, n_):
            if not np.isfinite(v[t]):
                continue
            h = v[max(0, t - 750):t]; h = h[np.isfinite(h)]
            if len(h) >= 250:
                q[t] = min(5, int((h < v[t]).sum() * 5 // len(h)) + 1)
        MK[L] = pd.Series(q, gs.index).reindex(cal).to_numpy()
    m200 = pd.Series(np.where(np.arange(n_) >= 199, (b_full > pd.Series(b_full).rolling(200).mean().to_numpy()).astype(float), np.nan), gs.index).reindex(cal).to_numpy()
    tr = C.bench_tr(cal)
    return MK, m200, tr


def sectors_daily(t, cal):
    s = _G.get("SEC", {}).get(t)
    out = np.full(len(cal), "", dtype=object)
    if not s:
        return out
    cv = cal.values
    for a, b, sec in s:
        m = (cv >= np.datetime64(a)) & ((cv <= np.datetime64(b)) if b is not None else True)
        out[m] = sec
    return out


def load_sectors():
    s = pd.read_csv(U._p("sectors", "sector_pit.csv"), dtype=str, keep_default_na=False)
    out = {}
    for r in s.itertuples():
        out.setdefault(r.ticker, []).append((pd.Timestamp(r.valid_from), pd.Timestamp(r.valid_to) if r.valid_to else None, r.gics_sector))
    return out


# ═════════════ 每檔：特徵、定義域、事件（worker）═════════════
def _init(d):
    _G.update(d)


def build_events(cff, c_bar, idx, pp_rows, bad_day, last, n, p0, pX, w1):
    """台股 researchSurge5.stock() 標籤段的美股版（G3）：pp_rows ＝ 母體列（日曆位置，已排序），只建 t ∈ [p0, pX] 的事件。
    → hdef（日曆長度 int16）、事件 list[(cell, t, P, dd 命中天數 x5)]"""
    nxt = np.full(n + 2, 10 ** 9)
    for p in range(n - 1, -1, -1):
        nxt[p] = p if bad_day[p] else nxt[p + 1]
    hdef = np.zeros(n, np.int16)
    hd = np.minimum.reduce([np.full(len(idx), 250), w1 - idx, nxt[np.minimum(idx + 1, n)] - 1 - idx])
    hdef[idx] = np.maximum(hd, 0)
    rows = pp_rows[(pp_rows >= p0) & (pp_rows <= pX)]
    cr = cff[rows]
    ev = []; cP = {}
    for hi, H in enumerate(HS):
        rmx = pd.Series(cff[::-1]).rolling(H, min_periods=1).max().to_numpy()[::-1]
        fm = np.r_[rmx[1:], np.nan]
        okH = hdef[rows] >= H
        for gi, g in enumerate(GS):
            q = rows[np.flatnonzero(okH & (fm[rows] >= cr * (1 + g) * (1 - 1e-9)))]
            if len(q) == 0:
                continue
            lastE = -10 ** 9; j = 0
            while j < len(q):
                t = int(q[j])
                if t - lastE > H:
                    seg = cff[t + 1:t + H + 1]; P = t + 1 + int(np.argmax(seg))
                    ev.append((cell_of(hi, gi), t, P))
                    lastE = t
                    j = int(np.searchsorted(q, t + H + 1))
                else:
                    j += 1
    out = []
    for cc, t, P in ev:
        if P not in cP:
            endobs = min(last, int(nxt[P + 1]) - 1 if P + 1 <= n else n - 1, w1)
            aft = cff[P + 1:endobs + 1]; pk = cff[P]
            hits = []
            for x in DD:
                w_ = np.flatnonzero(aft <= pk * (1 - x)); hits.append(int(w_[0]) + 1 if len(w_) else -1)
            cP[P] = hits
        out.append((cc, t, P, *cP[P]))
    return hdef, out


def stock(t):
    cal, n, p0, pX, pE, w1 = _G["cal"], _G["n"], _G["p0"], _G["pX"], _G["pE"], _G["w1"]
    d = _G["ST"][t]
    valid = d["valid"]; idx = np.flatnonzero(valid); m = len(idx)
    if m < 30:
        return None
    member = d["member"]
    cA = d["C"]; c, o, h, l = cA[idx], d["O"][idx], d["H"][idx], d["L"][idx]
    l = np.where(np.isfinite(l), l, np.fmin(o, c))
    vol = np.nan_to_num(d["V"][idx]); amt = c * vol
    rcA = raw_close_aligned(t, cal, valid, _G["SPL"].get(t)); rc = rcA[idx]
    shA, shT = shares_daily(_G["SH"].get(t), _G["SPL"].get(t), _G["cald"])
    sh = shA[idx]; shT_ = shT[idx]
    bad_k = d["pb"][idx].astype(bool)
    cbk = np.r_[0, np.cumsum(bad_k)]
    Fk = {}; span = {}
    rS = lambda w_: np.r_[np.full(w_, np.nan), c[w_:] / c[:-w_] - 1] if w_ < m else np.full(m, np.nan)
    ma = {w_: _roll(c, w_, "mean") for w_ in (5, 10, 20, 60, 100, 120, 250)}
    mtr = _G["TR"][idx]; rm = np.r_[np.nan, mtr[1:] / mtr[:-1] - 1]; rs = np.r_[np.nan, c[1:] / c[:-1] - 1]
    down = (rm < 0) & np.isfinite(rs)
    dd_ = np.where(down, rs - rm, 0.0); dn_ = down.astype(float)
    mas = np.vstack([ma[5], ma[10], ma[20]])
    okm = np.isfinite(mas).all(0)
    mxm = np.where(okm, np.where(okm, mas, -np.inf).max(0), np.nan); mnm = np.where(okm, np.where(okm, mas, np.inf).min(0), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        turn = vol / shT_
    for L in LB:
        Fk[f"r_{L}"] = rS(L); span[f"r_{L}"] = L + 1
        hi_, lo_ = _roll(c, L, "max"), _roll(c, L, "min")
        Fk[f"dhi_{L}"] = c / hi_ - 1; Fk[f"dlo_{L}"] = c / lo_ - 1; Fk[f"rng_{L}"] = hi_ / lo_ - 1
        mL = _roll(c, L, "mean"); Fk[f"ma_{L}"] = c / mL - 1
        bw = pd.Series(c).rolling(L, min_periods=L).std(ddof=0).to_numpy() / mL
        Fk[f"bbw_{L}"] = bw / pd.Series(bw).rolling(250, min_periods=250).median().to_numpy(); span[f"bbw_{L}"] = L + 250
        cnt = _roll(dn_, L, "sum")
        with np.errstate(invalid="ignore", divide="ignore"):
            Fk[f"anti_{L}"] = np.where(cnt > 0, _roll(dd_, L, "sum") / np.where(cnt > 0, cnt, 1), np.nan)
            Fk[f"tang_{L}"] = _prev(_roll(mxm, L, "max") / _roll(mnm, L, "min") - 1)
            Fk[f"ar_{L}"] = amt / _prev(_roll(amt, L, "mean"))
            aL = _roll(amt, L, "mean"); Fk[f"amt_{L}"] = aL; Fk[f"achg_{L}"] = aL / _prev(aL, L) if L < m else np.full(m, np.nan)
        Fk[f"turn_{L}"] = _roll(turn, L, "mean")
        for k_ in ("dhi", "dlo", "rng", "ma", "anti", "turn", "amt"):
            span[f"{k_}_{L}"] = L + 1
        span[f"tang_{L}"] = L + 21; span[f"ar_{L}"] = L + 1; span[f"achg_{L}"] = 2 * L + 1
    K = kd(c, h, l); Kr = run_len(np.nan_to_num(K) > 80)
    R14, R6, R12 = rsi(c, 14), rsi(c, 6), rsi(c, 12)
    sd20 = pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy(); bu, bl = ma[20] + 2 * sd20, ma[20] - 2 * sd20
    e5, e10, e20 = ema(c, 5), ema(c, 10), ema(c, 20)
    ex = np.vstack([e5, e10, e20]); x3 = ex.max(0) / ex.min(0) - 1; x3[:20] = np.nan
    v2 = run_len(e20 > np.nan_to_num(ma[20], nan=np.inf))
    v3 = np.zeros(m, bool); v3box = np.full(m, np.nan); last_touch = -1; box = np.nan; low_since = False
    for i in range(m):
        if last_touch >= 0 and i - last_touch - 1 >= 20 and low_since:
            v3box[i] = c[i] / box - 1; v3[i] = c[i] > box
        if np.isfinite(bu[i]) and c[i] >= bu[i]:
            last_touch = i; box = h[i]; low_since = False
        elif np.isfinite(bl[i]) and c[i] <= bl[i]:
            low_since = True
    Fk["kdK"] = K; Fk["kdrun"] = np.where(np.isfinite(K), Kr, np.nan).astype(float)
    Fk["rsi14"] = R14; Fk["rsid"] = R6 - R12; Fk["bbup"] = c / bu - 1; Fk["x3"] = x3
    Fk["v2run"] = np.where(np.isfinite(ma[20]), v2, np.nan).astype(float); Fk["v3box"] = v3box
    mseq = [ma[5], ma[10], ma[20], ma[60], ma[120], ma[250]]
    al = np.zeros(m)
    for a_, b_ in zip(mseq[:-1], mseq[1:]):
        al += (a_ > b_)
    Fk["maalign"] = np.where(np.isfinite(ma[250]), al, np.nan)
    for k_ in ("kdK", "kdrun", "rsi14", "rsid", "bbup", "x3", "v2run", "v3box"):
        span[k_] = 30
    span["maalign"] = 251
    Fk["mcap"] = rc * sh; Fk["shares"] = sh; Fk["price"] = rc
    pos_d = idx
    for L in LB:
        Fk[f"mkt_{L}"] = _G["MKTQ"][L][pos_d]
        Fk[f"indrk_{L}"] = np.full(m, np.nan)                                 # 橫斷面階段填
    Fk["d_mkt200"] = _G["MKT200"][pos_d]
    amt20p = _prev(_roll(amt, 20, "mean")); amt20 = _roll(amt, 20, "mean")
    Fk["d_bull"] = np.where(np.isfinite(ma[100]), ((ma[5] > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[100])).astype(float), np.nan)
    Fk["d_ma100"] = np.where(np.isfinite(ma[100]), (c > ma[100]).astype(float), np.nan)
    Fk["d_K1"] = np.where(np.isfinite(K), (Kr >= 3).astype(float), np.nan)
    Fk["d_K1l"] = np.where(np.isfinite(K), np.where(Kr == 0, 0, np.where(Kr <= 2, 1, np.where(Kr <= 5, 2, 3))), np.nan).astype(float)
    Fk["d_K2"] = np.where(np.isfinite(amt20p) & np.isfinite(bu), ((c > bu) & (amt >= 2 * amt20p)).astype(float), np.nan)
    Fk["d_K3a"] = np.where(np.isfinite(R14), (R14 > 50).astype(float), np.nan)
    Fk["d_K3b"] = np.r_[np.nan, np.where(np.isfinite(R6[1:]) & np.isfinite(R12[:-1]), ((R6[:-1] <= R12[:-1]) & (R6[1:] > R12[1:])).astype(float), np.nan)]
    tang20 = np.full(m, np.nan)
    for i in range(40, m):
        blk = mas[:, i - 20:i]
        tang20[i] = blk.max() / blk.min() - 1 if np.isfinite(blk).all() else np.nan
    Fk["d_K4"] = np.where(np.isfinite(tang20) & np.isfinite(ma[100]) & np.isfinite(amt20p),
                          ((tang20 <= 0.02) & (c / o - 1 >= 0.04) & (c > ma[20]) & (c > ma[100]) & (amt >= 2 * amt20p)).astype(float), np.nan)
    Fk["d_K5a"] = np.where(np.isfinite(turn), (turn >= 0.10).astype(float), np.nan); Fk["d_K5b"] = np.where(np.isfinite(turn), (turn >= 0.20).astype(float), np.nan)
    mx60p, mn60p = _prev(_roll(c, 60, "max")), _prev(_roll(c, 60, "min"))
    a120p = _prev(_roll(amt, 120, "mean"))
    Fk["d_V1"] = np.where(np.isfinite(mx60p) & np.isfinite(a120p) & np.isfinite(amt20p),
                          ((mx60p / mn60p - 1 <= 0.25) & (_prev(amt20) <= 0.7 * a120p) & (c > mx60p) & (amt >= 2 * amt20p)).astype(float), np.nan)
    Fk["d_V2l"] = np.where(np.isfinite(ma[20]), np.where(v2 == 0, 0, np.where(v2 <= 4, 1, np.where(v2 <= 9, 2, 3))), np.nan).astype(float)
    Fk["d_V3"] = np.where(np.isfinite(bu), v3.astype(float), np.nan)
    brk = c > _prev(_roll(c, 20, "max"))
    nxt10 = np.full(m, np.nan)
    if m > 11:
        cs = np.r_[0, np.cumsum(np.nan_to_num(amt))]
        j = np.arange(m - 10); nxt10[j] = (cs[j + 11] - cs[j + 1]) / 10
    okb = (brk & (nxt10 <= 0.4 * amt)).astype(float)
    x2 = np.zeros(m)
    for i in range(m):
        a_, b_ = i - 59, i - 10
        if b_ >= max(a_, 0):
            x2[i] = okb[max(a_, 0):b_ + 1].max()
    Fk["d_X2"] = np.where(np.arange(m) >= 80, x2, np.nan)
    e3 = [e5, e10, e20]
    Fk["d_X3"] = np.where(np.isfinite(x3), ((x3 <= 0.02) & np.all([e_ > _prev(e_, 3) for e_ in e3], axis=0)).astype(float), np.nan)
    a120pre = _prev(_roll(amt, 120, "mean"), 20)
    Fk["d_shrink"] = np.where(np.isfinite(a120pre) & np.isfinite(amt20), (amt20 <= 0.7 * a120pre).astype(float), np.nan)
    span["d_shrink"] = 141
    Fk["d_X1"] = np.full(m, np.nan)                                            # 橫斷面階段填（20 日均額 ≥ 當日母體中位）
    for k_, sp in span.items():
        if k_ in Fk:
            kk = np.arange(m); nb_ = cbk[kk + 1] - cbk[np.maximum(kk + 1 - sp, 0)]
            Fk[k_] = np.where(nb_ > 0, np.nan, Fk[k_])
    # 只存 [p0, pE] 的母體列
    nd = pE - p0 + 1
    keep = (idx >= p0) & (idx <= pE) & member[idx]
    kpos = idx[keep] - p0
    Fout = np.full((len(FCOL), nd), np.nan, np.float32)
    for k_, v_ in Fk.items():
        Fout[FIX[k_], kpos] = np.asarray(v_, float)[keep]
    bar = np.zeros(nd, bool); bar[kpos] = True
    m4 = d["m4"][p0:pE + 1] & bar
    # 標籤（G3）
    cff = d["closes"]
    rows = idx[member[idx]]
    last = int(idx[-1])
    bad_day = np.zeros(n + 1, bool); bad_day[idx[bad_k]] = True
    hdef, E = build_events(cff, c, idx, rows, bad_day, last, n, p0, pX, w1)
    out = {"t": t, "F": Fout, "bar": bar, "m4": m4, "hdef": hdef[p0:pE + 1], "E": E,
           "sec": sectors_daily(t, cal)[p0:pE + 1], "nbad": int(bad_k.sum())}
    f50 = d["f50"]
    if f50.any():
        bad2 = bad_day.copy(); bad2[np.flatnonzero(f50)] = True
        h2, E2 = build_events(cff, c, idx, rows, bad2, last, n, p0, pX, w1)
        out["hdef50"] = h2[p0:pE + 1]; out["E50"] = E2
    return out


# ═════════════ 主程式 ═════════════
def build(procs, lim):
    os.makedirs(WORKS, exist_ok=True)
    meta, ST = C.load_cache()
    cal, w0, w1 = meta["cal"], meta["w0"], meta["w1"]; n = len(cal)
    p0 = int(cal.searchsorted(SURGE0)); pX = int(cal.searchsorted(EXP_LAST, side="right")) - 1; pE = int(cal.searchsorted(STORE_LAST, side="right")) - 1
    assert cal[p0] == SURGE0
    sids = sorted(ST)
    if lim:
        sids = sids[::max(1, len(sids) // lim)]
    t0 = time.time()
    SH, SPL = load_shares()
    MK, M200, TR = market(cal)
    G = {"cal": cal, "cald": cal.values.astype("datetime64[D]").astype(np.int64), "n": n, "p0": p0, "pX": pX, "pE": pE, "w1": w1,
         "ST": ST, "SH": SH, "SPL": SPL, "MKTQ": MK, "MKT200": M200, "TR": TR, "SEC": load_sectors()}
    print("[surge] 外部序列 %.0fs｜探索 %s～%s｜存到 %s｜%d 檔" % (time.time() - t0, cal[p0].date(), cal[pX].date(), cal[pE].date(), len(sids)), flush=True)
    _init(G)
    res = []
    with Pool(procs, initializer=_init, initargs=(G,)) as pool:
        for k, r in enumerate(pool.imap(stock, sids, chunksize=4)):
            if r is not None:
                res.append(r)
            if (k + 1) % 100 == 0:
                print("[surge] %d／%d %.0fs" % (k + 1, len(sids), time.time() - t0), flush=True)
    return meta, cal, p0, pX, pE, res


def cross_q(F, bar, sec):
    """五等分（S10）＋ 產業排名（類間五等分）＋ X1（20 日均額 ≥ 當日母體中位）。F：(nf, S, nd) float32 ⇒ Q int8。"""
    nf, S, nd = F.shape
    for L in LB:
        r = F[FIX[f"r_{L}"]]; out = np.full((S, nd), np.nan, np.float32)
        for t in range(nd):
            ok = bar[:, t] & np.isfinite(r[:, t]) & (sec[:, t] != "")
            if ok.sum() < 10:
                continue
            s_ = pd.Series(r[ok, t]).groupby(sec[ok, t]).agg(["mean", "size"])
            s_ = s_[s_["size"] >= 3]
            if len(s_) < 5:
                continue
            rk = qtie(s_["mean"].to_numpy()).astype(float)
            mp = dict(zip(s_.index, rk))
            b_ = bar[:, t]
            out[b_, t] = [mp.get(z, np.nan) for z in sec[b_, t]]
        F[FIX[f"indrk_{L}"]] = out
    r60, r20, a20 = F[FIX["r_60"]], F[FIX["r_20"]], F[FIX["amt_20"]]
    med = np.array([np.nanmedian(np.where(bar[:, t], a20[:, t], np.nan)) if bar[:, t].any() else np.nan for t in range(nd)])
    with np.errstate(invalid="ignore"):
        X1 = np.where(np.isfinite(r60) & np.isfinite(r20) & np.isfinite(a20), ((r60 >= 0.10) & (r60 <= 0.30) & (r20 <= 0.03) & (a20 >= med[None, :])).astype(float), np.nan)
    F[FIX["d_X1"]] = np.where(bar, X1, np.nan)
    Q = np.zeros((nf, S, nd), np.int8)
    for col, name, cat, kind in SPECS:
        X = F[FIX[col]]
        if kind == "q":
            for t in range(nd):
                b_ = bar[:, t]
                if b_.any():
                    Q[FIX[col], b_, t] = qtie(X[b_, t])
        elif kind in ("qts", "x"):
            Q[FIX[col]] = np.where(np.isfinite(X) & bar, X, 0).astype(np.int8)
        else:
            Q[FIX[col]] = np.where(np.isfinite(X) & bar, X + 1, 0).astype(np.int8)
    return Q


def analyze(Q, bar, m4, hdef, E, mi, NM, pX_off, use_rows=None, use_ev=None):
    """探索段 ①②（G5）＋ 妖股族、結束族（G6）。use_rows／use_ev：欄遮罩（只 400／只 500 描述）。→ dict。"""
    LV = levels()
    S, nd = bar.shape
    rowsel = bar.copy(); rowsel[:, pX_off + 1:] = False
    if use_rows is not None:
        rowsel &= use_rows
    bidx = np.flatnonzero(rowsel.ravel()); b_day = bidx % nd; b_mi = mi[b_day]
    b_h = np.minimum(hdef.ravel()[bidx].astype(np.int64), 250)
    ec, es, ed, EP = E["cell"], E["s"], E["d"], E["P"]
    keepE = np.ones(len(ec), bool) if use_ev is None else use_ev
    ec, es, ed, EP = ec[keepE], es[keepE], ed[keepE], EP[keepE]
    ddh = {x: E[f"dd{x}"][keepE] for x in (10, 20, 30, 50, 70)}
    e_mi = mi[ed]
    CODES = 7

    def base_counts(qf):
        keep = qf > 0
        key = (qf[keep].astype(np.int64) * NM + b_mi[keep]) * 251 + b_h[keep]
        c = np.bincount(key, minlength=CODES * NM * 251).reshape(CODES, NM, 251)
        ge = np.cumsum(c[:, :, ::-1], axis=2)[:, :, ::-1]
        return ge[:, :, list(HS)]

    def ev_counts(code_e, mon, cells, w=None):
        keep = code_e > 0
        key = (code_e[keep].astype(np.int64) * NC + cells[keep]) * NM + mon[keep]
        return np.bincount(key, weights=None if w is None else w[keep], minlength=CODES * NC * NM).reshape(CODES, NC, NM)

    def summ(lift, lo, cov, ev, nn):
        ok = np.isfinite(lift)
        return {"提升中位": float(np.nanmedian(lift)) if ok.any() else np.nan,
                "提升p10": float(np.nanpercentile(lift, 10)) if ok.any() else np.nan, "提升p90": float(np.nanpercentile(lift, 90)) if ok.any() else np.nan,
                "涵蓋率中位": float(np.nanmedian(cov)) if np.isfinite(cov).any() else np.nan,
                "下緣>1且涵蓋≥5%格數": int(np.sum((lo > 1) & (cov >= 0.05))), "下緣>1格數": int(np.sum(lo > 1)), "提升>1格數": int(np.sum(lift > 1)),
                "H60g100_提升": float(lift[cell_of(5, 1)]), "H60g100_下緣": float(lo[cell_of(5, 1)]), "H60g100_涵蓋率": float(cov[cell_of(5, 1)]),
                "事件數中位（有特徵）": float(np.median(ev)), "定義域列中位（有特徵）": float(np.median(nn))}
    A = {}
    fis = sorted({x[0] for x in LV})
    for fi_ in fis:
        q = Q[fi_]; qf = q.ravel()[bidx]
        NC_ = base_counts(qf)
        code_e = q[es, ed]
        EC_ = ev_counts(code_e, e_mi, ec)
        nrow = NC_[:, :, HI_OF_CELL].transpose(0, 2, 1)
        eall = EC_[1:].sum(0).astype(float); nall = nrow[1:].sum(0).astype(float)
        for lv in [x for x in LV if x[0] == fi_]:
            code = lv[2]
            e = EC_[code].astype(float); nn = nrow[code].astype(float)
            if nn.sum() == 0:
                continue
            lift, lo, hi, cov = ratio_stats(e, nn, eall, nall, e.sum(1), eall.sum(1), Z95)
            A[(lv[1], code)] = summ(lift, lo, cov, e.sum(1), nn.sum(1))
    pk = [lv for lv in LV if lv[7] and (lv[1], lv[2]) in A and A[(lv[1], lv[2])]["下緣>1且涵蓋≥5%格數"] >= HALF]
    # 妖股族
    YA = {}; YPK = {}
    for x in (30, 50, 70):
        hit = (ddh[x] > 0).astype(float); FA = {}
        for fi_ in fis:
            code_e = Q[fi_][es, ed]
            ea_ = ev_counts(code_e, e_mi, ec, w=hit); na_ = ev_counts(code_e, e_mi, ec)
            eA = ea_[1:].sum(0).astype(float); nA = na_[1:].sum(0).astype(float)
            for lv in [v for v in LV if v[0] == fi_]:
                e = ea_[lv[2]].astype(float); nn = na_[lv[2]].astype(float)
                if nn.sum() == 0:
                    continue
                lift, lo, hi, cov = ratio_stats(e, nn, eA, nA, e.sum(1), eA.sum(1), Z95)
                FA[(lv[1], lv[2])] = summ(lift, lo, cov, e.sum(1), nn.sum(1))
        YA[x] = FA
        YPK[x] = [lv for lv in LV if lv[7] and (lv[1], lv[2]) in FA and FA[(lv[1], lv[2])]["下緣>1且涵蓋≥5%格數"] >= HALF]
    # 結束族
    EA = {}; EPK = {}
    for x in (10, 20, 30):
        ended = ddh[x] > 0
        for kk in KEND:
            pos = EP - kk; mid = ed + (EP - ed) // 2
            ii = np.flatnonzero(ended & (pos > ed) & (EP - mid > 20) & (mid > ed))
            cc = ec[ii]; mm_ = e_mi[ii]; ss = es[ii]; pp_ = pos[ii]; md_ = mid[ii]
            FA = {}
            for fi_ in fis:
                q = Q[fi_]; cp = q[ss, pp_].astype(np.int64); cq = q[ss, md_].astype(np.int64)
                cel = np.r_[cc, cc]; mon = np.r_[mm_, mm_]; code = np.r_[cp, cq]; y = np.r_[np.ones(len(cp)), np.zeros(len(cq))]
                ea_ = ev_counts(code, mon, cel, w=y); na_ = ev_counts(code, mon, cel)
                eA = ea_[1:].sum(0).astype(float); nA = na_[1:].sum(0).astype(float)
                for lv in [v for v in LV if v[0] == fi_]:
                    e = ea_[lv[2]].astype(float); nn = na_[lv[2]].astype(float)
                    if nn.sum() == 0:
                        continue
                    lift, lo, hi, cov = ratio_stats(e, nn, eA, nA, e.sum(1), eA.sum(1), Z95)
                    FA[(lv[1], lv[2])] = summ(lift, lo, cov, e.sum(1), nn.sum(1))
            EA[(x, kk)] = FA
            EPK[(x, kk)] = [lv for lv in LV if lv[7] and (lv[1], lv[2]) in FA and FA[(lv[1], lv[2])]["下緣>1且涵蓋≥5%格數"] >= HALF]
    return {"A": A, "pk": pk, "YA": YA, "YPK": YPK, "EA": EA, "EPK": EPK}


def grid_desc(E, mi, NM, m4ev):
    """探索段網格描述：每格事件數（合併／只 400／只 500）、樣本少（＜30）格數。"""
    out = {}
    for g, msk in (("合併", np.ones(len(E["cell"]), bool)), ("只400", m4ev), ("只500", ~m4ev)):
        cnt = np.bincount(E["cell"][msk], minlength=NC)
        out[g] = {"事件總數（格加總）": int(cnt.sum()), "每格事件數中位": float(np.median(cnt)), "p10": float(np.percentile(cnt, 10)),
                  "p90": float(np.percentile(cnt, 90)), "樣本少（＜30）格數": int((cnt < 30).sum()),
                  "H60g100格事件數": int(cnt[cell_of(5, 1)]), "H250g50格事件數": int(cnt[cell_of(24, 0)]), "H10g1000格事件數": int(cnt[cell_of(0, 9)])}
    return out


def lvname(lv):
    return f"{lv[4]}｜{lv[3]}"


def run(procs=2, lim=None):
    t0 = time.time()
    meta, cal, p0, pX, pE, res = build(procs, lim)
    sids = [r["t"] for r in res]; S = len(sids); nd = pE - p0 + 1
    print("[surge] 讀檔＋特徵＋事件 %d 檔 %.0fs" % (S, time.time() - t0), flush=True)
    F = np.empty((len(FCOL), S, nd), np.float32)                           # (nf, S, nd)
    for si, r in enumerate(res):
        F[:, si, :] = r["F"]; r["F"] = None
    bar = np.stack([r["bar"] for r in res]); m4 = np.stack([r["m4"] for r in res]); hdef = np.stack([r["hdef"] for r in res])
    sec = np.stack([r["sec"] for r in res])
    Q = cross_q(F, bar, sec)
    del F
    print("[surge] 五等分 %.0fs" % (time.time() - t0), flush=True)
    days = cal[p0:pE + 1]
    mon = np.array([d.year * 12 + d.month for d in days]); mi = (mon - mon.min()).astype(np.int64); NM = int(mi[:pX - p0 + 1].max()) + 1
    mi = np.minimum(mi, NM - 1)                                              # 2024 的日子只當 P−k／中段位置用，月份依 t（不會用到）

    def ev_table(key):
        rows = []
        for si, r in enumerate(res):
            Ev = r.get(key, r["E"]) if key != "E" else r["E"]
            for e in Ev:
                rows.append((e[0], si, e[1] - p0, e[2] - p0, *e[3:]))
        a = np.array(rows, np.int64) if rows else np.zeros((0, 8), np.int64)
        return {"cell": a[:, 0], "s": a[:, 1], "d": a[:, 2], "P": a[:, 3], **{f"dd{x}": a[:, 4 + i] for i, x in enumerate((10, 20, 30, 50, 70))}}
    E = ev_table("E")
    assert (E["d"] <= pX - p0).all() and (E["P"] <= pE - p0).all(), "事件超出探索段或存檔範圍"
    m4ev = m4[E["s"], E["d"]]
    pX_off = pX - p0
    print("[surge] 事件列 %d｜分析中…" % len(E["cell"]), flush=True)
    R = {"合併": analyze(Q, bar, m4, hdef, E, mi, NM, pX_off)}
    R["只400"] = analyze(Q, bar, m4, hdef, E, mi, NM, pX_off, use_rows=m4, use_ev=m4ev)
    R["只500"] = analyze(Q, bar, m4, hdef, E, mi, NM, pX_off, use_rows=bar & ~m4, use_ev=~m4ev)
    print("[surge] ①② 三欄完成 %.0fs" % (time.time() - t0), flush=True)
    # 敏感度：f50 當壞根（G9）
    hdef50 = np.stack([r.get("hdef50", r["hdef"]) for r in res])
    E50 = ev_table("E50")
    R50 = analyze(Q, bar, m4, hdef50, E50, mi, NM, pX_off)
    n50 = sum(1 for r in res if "E50" in r)
    # 工作檔（repo 外）
    os.makedirs(WORKS, exist_ok=True)
    pE_ = os.path.join(WORKS, "events_explore.npz"); np.savez(pE_, **E, sids=np.array(sids))
    shas = {"events_explore.npz": {"rows": int(len(E["cell"])), "sha256": C.sha256f(pE_)}}
    LV = levels()

    def fam_rows(FA, pk, col_tag):
        rows = []
        for lv in LV:
            v = FA.get((lv[1], lv[2]))
            if v is None:
                continue
            rows.append({"欄": lv[1], "碼": lv[2], "特徵": lvname(lv), "類別": lv[5], "型態": lv[6], "進挑選": lv[7], "進驗證段": lv in pk, **v})
        return rows
    os.makedirs(C.OUT, exist_ok=True)
    main = pd.DataFrame(fam_rows(R["合併"]["A"], R["合併"]["pk"], "合併"))
    for g in ("只400", "只500"):
        x = pd.DataFrame(fam_rows(R[g]["A"], R[g]["pk"], g)).set_index(["欄", "碼"])
        main[f"{g}_下緣>1且涵蓋≥5%格數"] = [x["下緣>1且涵蓋≥5%格數"].get((a, b), np.nan) for a, b in zip(main["欄"], main["碼"])]
        main[f"{g}_提升中位"] = [x["提升中位"].get((a, b), np.nan) for a, b in zip(main["欄"], main["碼"])]
    x50 = pd.DataFrame(fam_rows(R50["A"], R50["pk"], "ret50")).set_index(["欄", "碼"])
    main["敏感度ret50_下緣>1且涵蓋≥5%格數"] = [x50["下緣>1且涵蓋≥5%格數"].get((a, b), np.nan) for a, b in zip(main["欄"], main["碼"])]
    main.to_csv(os.path.join(C.OUT, "A3-17_探索段_飆股族_級距彙總.csv"), index=False, float_format="%.5g")
    fam = []
    for x in (30, 50, 70):
        for r_ in fam_rows(R["合併"]["YA"][x], R["合併"]["YPK"][x], "合併"):
            fam.append({"族": f"妖股（P後回落{x}%）", **r_})
    for (x, kk) in R["合併"]["EA"]:
        for r_ in fam_rows(R["合併"]["EA"][(x, kk)], R["合併"]["EPK"][(x, kk)], "合併"):
            fam.append({"族": f"結束（回落{x}%｜P−{kk}日）", **r_})
    famD = pd.DataFrame(fam)
    famD.to_csv(os.path.join(C.OUT, "A3-17_探索段_妖股與結束族_級距彙總.csv.gz"), index=False, float_format="%.4g")

    def pick_list(pk, FA):
        return [{"特徵": lvname(lv), "欄": lv[1], "碼": lv[2], "網格中位提升": FA[(lv[1], lv[2])]["提升中位"],
                 "提升p10": FA[(lv[1], lv[2])]["提升p10"], "提升p90": FA[(lv[1], lv[2])]["提升p90"],
                 "涵蓋率中位": FA[(lv[1], lv[2])]["涵蓋率中位"], "過門檻格數": FA[(lv[1], lv[2])]["下緣>1且涵蓋≥5%格數"]} for lv in pk]
    PKS = {"飆股（起漲前）": pick_list(R["合併"]["pk"], R["合併"]["A"])}
    for x in (30, 50, 70):
        PKS[f"妖股（P後回落{x}%）"] = pick_list(R["合併"]["YPK"][x], R["合併"]["YA"][x])
    for (x, kk) in R["合併"]["EA"]:
        PKS[f"結束（回落{x}%｜P−{kk}日）"] = pick_list(R["合併"]["EPK"][(x, kk)], R["合併"]["EA"][(x, kk)])
    Nsel = {k: len(v) for k, v in PKS.items()}
    N_total = int(sum(Nsel.values()))
    base_pk = {(p["欄"], p["碼"]) for p in PKS["飆股（起漲前）"]}
    pk50 = {(lv[1], lv[2]) for lv in R50["pk"]}
    dcard = []
    for lv in LV:
        if lv[6] in ("dbin", "dlvl"):
            v = R["合併"]["A"].get((lv[1], lv[2]))
            if v:
                dcard.append({"特徵": lvname(lv), "網格中位提升": v["提升中位"], "提升p10": v["提升p10"], "提升p90": v["提升p90"],
                              "涵蓋率中位": v["涵蓋率中位"], "下緣>1且涵蓋≥5%格數": v["下緣>1且涵蓋≥5%格數"]})
    GD = grid_desc(E, mi, NM, m4ev)
    nsel400 = len(R["只400"]["pk"]); nsel500 = len(R["只500"]["pk"])
    top = sorted(PKS["飆股（起漲前）"], key=lambda r_: -r_["網格中位提升"])[:8]
    tops = "、".join(f"{p['特徵']}（網格中位提升 {p['網格中位提升']:.2f} 倍、涵蓋 {p['涵蓋率中位'] * 100:.0f}%）" for p in top) if top else "無"
    ccnt = np.bincount(E["cell"], minlength=NC)
    n_has, n_30 = int((ccnt > 0).sum()), int((ccnt >= 30).sum())
    near = main[main["進挑選"]].sort_values(["下緣>1且涵蓋≥5%格數", "提升中位"], ascending=False).head(6)
    nears = "、".join(f"{r_.特徵}（{int(r_['下緣>1且涵蓋≥5%格數'])} 格、網格中位提升 {r_.提升中位:.1f} 倍、涵蓋 {r_.涵蓋率中位 * 100:.0f}%）" for _, r_ in near.iterrows())
    struct = (f"⚠ 依構造：美股大中型股探索段 250 格裡只有 {n_has} 格有任何起漲事件、{n_30} 格有 ≥30 件（漲 300% 以上的格幾乎全空）⇒「≥125 格過門檻」"
              f"只能靠有事件的格湊；最接近門檻的是 {nears}。")
    sent = (f"探索段（2021～2023）在美股 S&P 500＋400 聯集照台股 seq7 的網格規則挑：起漲前價量特徵進驗證段 {Nsel['飆股（起漲前）']} 個級距"
            f"（{tops}）。{struct} 妖股族 {sum(Nsel[k] for k in Nsel if k.startswith('妖股'))} 個、結束族 {sum(Nsel[k] for k in Nsel if k.startswith('結束'))} 個；"
            f"合計 {N_total} 個 ＝ 若開驗證段時的 N。⭐ 這只是「長得像飆股」的挑選，還沒驗、也還沒看買了賺不賺；⛔ 驗證段 2024～2026-09 尚未打開，等裁定。"
            f"{C.IDEA}；{C.SURV}。")
    card = {"件": "A3-17", "名稱": "飆股回推比對 價量特徵部分（探索段挑選；⛔ 驗證段未開）",
            "台股原登錄": "登錄全文-飆股回推比對_起漲前特徵與可交易性_登錄_台股策略線_seq7_sha15a22c6b6c2c36d0-22678B-20261002-0029.md（sha 15a22c6b6c2c36d0）",
            "出場型": "描述（單筆層探勘；③ 可交易曲線驗證時另標）", "N": None, "N_待裁定（＝挑出級距數，若開驗證段）": N_total,
            "標籤": "待裁定（探索段挑選完成；⛔ 未驗證）", "判定格": "250 格網格（H10～250 × g50%～≥1000%），挑選＝≥125 格「① 95% 下緣＞1 且 ② ≥5%」",
            "三欄": {"合併": f"挑出 飆股族 {Nsel['飆股（起漲前）']}、妖股族 {sum(Nsel[k] for k in Nsel if k.startswith('妖股'))}、結束族 {sum(Nsel[k] for k in Nsel if k.startswith('結束'))} 個級距（挑選用欄）",
                     "只400": f"同式只看 S&P 400 列：飆股族過門檻 {nsel400} 個級距（描述）", "只500": f"同式只看 S&P 500 列：飆股族過門檻 {nsel500} 個級距（描述）"},
            "條件出場必報": None, "結果句": sent,
            "敏感度_ret50": f"S&P 400 未確認 |ret|>50% 列當壞根（{n50} 檔受影響）重挑：飆股族 {len(pk50)} 個（與主結果相同 {len(pk50 & base_pk)}、只主結果有 {len(base_pk - pk50)}、只敏感度有 {len(pk50 - base_pk)}）",
            "偏離": ["只做探索段（seq319 Q16）：③ 可交易曲線、買不買得到、結束可交易、驗證段 Bonferroni 一律未算",
                     "產業排名用 GICS sector（11 類）而非台股約 30 類產業別；seq319 Q8 的 industry group 只裁 A4-5／A4-6",
                     "額＝還原收盤×拆股調整量（美股無成交金額欄）；母體＝S&P 500＋400 聯集（台股為全部上市櫃普通股）",
                     "G4b：prep 的「原始收盤」實為 Yahoo 日後拆股調整價 ⇒ 本件改 close×日後拆股比（A4 同法）；只影響市值、股價特徵；第一次全量跑後發現、修正後全部重跑（修正前飆股族挑出 0、結束族 9）"],
            "補讀法": ["G1～G10（researchUSA3_surge.py docstring，台北 2026-10-07 11:55 寫死）"],
            "先驗紀錄": "台股先驗 ①～④ 針對確認段；驗證段未開 ⇒ 本步不記對錯"}
    out = {"卡片": card, "登錄": C.REG, "讀法寫死": READ_TS, "資料commit": meta["data_commit"],
           "探索段": [str(cal[p0].date()), str(cal[pX].date())], "存檔範圍（P−k 位置用）": str(cal[pE].date()), "檔數": S,
           "網格描述（探索段）": GD, "挑出（合併）": PKS, "各族挑出數": Nsel, "N_待裁定": N_total,
           "原門檻描述（⛔ 不進挑選）": dcard, "只400挑出數（描述）": nsel400, "只500挑出數（描述）": nsel500,
           "敏感度_ret50": {"受影響檔數": n50, "飆股族挑出": len(pk50), "與主結果同": len(pk50 & base_pk)},
           "覆蓋_存活者偏差": C.coverage_cached(cal, meta["w0"], meta["w1"]), "逐筆檔sha（repo外）": shas, "耗時秒": round(time.time() - t0, 1),
           "⛔": "驗證段 2024-01～2026-09 未打開：沒有任何驗證段起漲日、提升倍數或報酬被計算"}
    C.jdump(out, os.path.join(C.OUT, "A3-17.json"))
    print("[surge] 完成：挑出 %s｜合計 %d｜%.0fs" % (Nsel, N_total, time.time() - t0), flush=True)
    return out


# ═════════════ 獨立查核（⭐ 不呼叫 build_events／analyze／ratio_stats）═════════════
def check(nstock=6, seed=20261007):
    """① 抽 nstock 檔：逐日暴力重算 H60／g100%、H250／g50% 兩格的事件（定義域、鏈）＝ events_explore.npz 該檔該格；
    ② 抽 3 個級距：用逐列 Python 迴圈重算某格的 ① 提升與 ② 涵蓋率 vs 彙總 csv 的 H60g100 欄（需要 Q ⇒ 重建該特徵；只驗 qts 大盤類與產業以外的價格類 r_20）。"""
    meta, ST = C.load_cache()
    cal, w1 = meta["cal"], meta["w1"]; n = len(cal)
    p0 = int(cal.searchsorted(SURGE0)); pX = int(cal.searchsorted(EXP_LAST, side="right")) - 1
    z = np.load(os.path.join(WORKS, "events_explore.npz"))
    sids = list(z["sids"])
    rng = np.random.default_rng(seed)
    pick = [int(i) for i in rng.choice(len(sids), size=min(nstock, len(sids)), replace=False)]
    diff = 0; tot = 0
    for si in pick:
        t = sids[si]; d = ST[t]
        valid = d["valid"]; member = d["member"]; cff = d["closes"]; pb = d["pb"]
        idx = np.flatnonzero(valid)
        badpos = set(int(x) for x in idx[pb[idx].astype(bool)])
        for hi, gi in ((5, 1), (24, 0), (0, 0)):
            H, g = HS[hi], GS[gi]; cc = cell_of(hi, gi)
            mine = []; lastE = -10 ** 9
            for p in range(p0, pX + 1):
                if not (valid[p] and member[p]):
                    continue
                # 定義域：p+H ≤ w1 且 (p, p+H] 無壞根
                if p + H > w1 or any((p < b <= p + H) for b in badpos):
                    continue
                mx = max(cff[p + 1:p + H + 1])
                if mx >= cff[p] * (1 + g) * (1 - 1e-9) and p - lastE > H:
                    mine.append(p); lastE = p
            sel = (z["s"] == si) & (z["cell"] == cc)
            theirs = sorted(int(x) + p0 for x in z["d"][sel])
            tot += 1; diff += int(mine != theirs)
    return {"件": "A3-17", "抽樣": tot, "不同": diff, "說明": f"抽 {len(pick)} 檔 × 3 格（H60g100、H250g50、H10g50）逐日暴力重算起漲事件（定義域、壞根、鏈）對 events_explore.npz"}


if __name__ == "__main__":
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    if "--run" in sys.argv:
        run(procs, lim)
    if "--check" in sys.argv:
        print(json.dumps(check(), ensure_ascii=False))

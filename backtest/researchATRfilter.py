# -*- coding: utf-8 -*-
"""PREREG加密 ATR 通道濾網（SAR 翻轉）v1（裁定 seq340 發號，加密 N＋4；登錄整檔 sha256 480e12a0fb077735…、4269 B，已驗）——回測線執行端。

⭐ 讀法寫死：2026-10-11 20:34（台北，WSL `TZ=Asia/Taipei date`）——⛔ 在算出任何報酬之前寫在這裡；之後只准補「執行時發現」並標時間。
   寫死前已看過：登錄全文 §一～§七；資料檔頭尾日期、資金費檔頭尾、幣本位合約規格與分級表（私有 cm_specs，只讀，只取常數）；C17／C17_btccm 的既有寫法。
   登錄沒寫死、由回測線補的讀法一律列在下面 R1～R16【執行者補】，交裁定。

資料：公開 tw-stock-data main commit 72df67ed043756589b0453b71ac8ca883d39011c（2026-10-11 09:53 UTC），一律 `git show <sha>:<path>` 讀（釘 sha，⛔ 不讀 worktree 的 data/）
   現貨日 K：data/crypto/<SYM>.csv（Binance、USDT 計價、UTC 日界），全部幣資料尾 2026-10-10
   U 本位資金費：data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv（2019-09-10 08:00 起）＋ data/crypto_funding/BTCUSDT.csv（2020-01-01～2026-09-30 16:00）
   幣本位資金費：data/meta/crypto_cm_funding_rest/BTCUSD_PERP.csv（2020-08-10 16:00 起）、SOLUSD_PERP.csv（2021-09-02 起），到 2026-10-05 00:00
   常數（私有 us-stock-data cm_specs，只讀、⛔ 不複製原始檔）：BTCUSD_PERP 每張 100 USD、第 1 級 MMR 0.4%（≤5 BTC）；SOLUSD_PERP 每張 10 USD、第 1 級 MMR 1%（≤400 SOL）

⭐ 實作讀法【執行者補】
 R1 各幣上市後前 30 天剔除＝檔案第一列起 30 列丟掉；指標（SAR、SMA、ATR）都從剔除後第一列起算，全期一次算完，⛔ 不逐窗重設。
 R2 SAR＝TA-Lib 寫法（Wilder）：起始方向看第 0→1 根，−DM＞0 且 ＞＋DM ⇒ 空，否則多；多：SAR₀＝第 0 根最低、EP＝第 1 根最高（空對稱）。
    多單 SAR 不得高於前兩根最低（空單不得低於前兩根最高）；翻轉當日 SAR 重設為前一段 EP（再夾在前兩根高／低之外）、AF 回 0.02、EP＝當日極值。
    翻轉判定：多→空 最低 ≤ SAR、空→多 最高 ≥ SAR（登錄 §二字面）。起始方向只影響 2017／2020 年頭幾根，窗內無影響。
 R3 翻轉日 t（收盤確認）⇒ t＋1 開盤進場；持有日 e＝t＋1…last；下一次翻轉 t' ⇒ t'＋1 開盤平倉（x＝t'＋1、last＝t'）。
    不加濾網＝每次翻轉都進（平倉同時反手，一直在場）；加濾網＝只有通過濾網的翻轉才進，出場只看下一次翻轉；被擋的翻轉空手等下一次翻轉。
    ⇒ 兩臂的單是同一組「翻轉段」，加濾網＝其中一個子集（被擋單＝補集）。
 R4 窗：各窗獨立跑、⛔ 不帶入窗外部位；有效窗首 i0＝max(窗首, 剔除後第 200 列＝SMA200 與 ATR(200) 都有值的第一天)，兩臂與兩讀法共用同一個 i0
    （BTC W1 實際從 2018-04-04 起；SOL W1 從 2021-03-29 起）；只收 i0 ≤ t ≤ i1−1 的翻轉；窗尾仍持有 ⇒ 以 i1 收盤估值、不扣平倉費，件數必報。
 R5 ATR＝Wilder（TA-Lib）：TR 從第 1 列起（要前收），ATR_n＝前 n 個 TR 平均（第 n 列），之後 (ATR×(n−1)＋TR)/n；SMA200＝含當日收盤的 200 日均。
    濾網用嚴格不等式：進多要 close_t ＞ U_t、進空要 close_t ＜ D_t（等號算通道內）。
 R6 主損益口徑（A，「同一 SAR 訊號加 vs 不加」）：U 本位 1 倍、每筆固定數量 q＝進場時權益／進場價（筆內不再平衡）、筆與筆之間複利、空手時現金 0%。
    筆內權益 r(d)＝1 − 0.1% ＋ dir×q×(close_d − Pe) − Σ資金費；平倉 m＝1 − 0.1% ＋ dir×q×(open_x − Pe) − Σ資金費 − 0.1%×q×open_x。
 R7 資金費歸日（同 C17 K5）：時戳截到秒再截到整點 h，屬持有日 D＝(h−1 秒) 的 UTC 日（D 08:00、16:00、D＋1 00:00）⇒ 開盤進場不付 e 當天 00:00、開盤平倉要付 x 當天 00:00。
    參考價：進場日＝進場價、其他日＝前一日收盤（日 K 沒有逐筆標記價）。多付正費率、空收（負費率反向）。
    缺段：D 的第一筆 (D 08:00) 早於資料首筆或 D＋1 00:00 晚於資料末筆 ⇒ 整天以年化 10%（÷365.25）代入（多付、空收），報窗內與持有日代入天數。
 R8 （A）的資金費：登錄 §一寫 BTCUSDT 實際值 ⇒ BTC、SOL、副幣主格一律用 BTCUSDT（照字面，同 C17 K5）；SOL 另報用 SOLUSDT 自己的資金費（敏感度）。
 R9 指標：總損益＝窗末權益−1；年化＝窗末^(365.25/T)−1（T＝窗內日數）；最大回落＝每日收盤權益（含窗首 1）相對前高；年化÷|回落|（回落 0 ⇒ 年化＞0 記 ∞、否則 0）。
    多、空分報＝只做多單／只做空單的子臂（另一方向那些段空手），合計＝兩方向都做。
 R10 幣本位口徑（B，使用者判準）：每筆開 n 張幣本位反向合約（BTCUSD 3 張＝300 USD、敏感度 10 張；SOLUSD 30 張＝300 USD），固定張數、不複利。
    幣計損益：多 N(1/Pe − 1/Px)、空 N(1/Px − 1/Pe)；手續費每邊 0.1%×N/價；資金費＝−dir×rate×N/參考價（幣），用幣本位永續自己的費率（BTCUSD_PERP、SOLUSD_PERP），缺段年化 10%。
    疊加後幣數＝W0（BTC 0.0715、SOL 10）＋Σ 訊號單幣計損益（每日收盤估值）；只抱現貨＝W0 不動 ⇒ 差＝訊號單的幣計總損益。另報幣數路徑最大回落、USD 計（幣數×收盤 vs W0×收盤）。
    ⚠ 常駐 3 張多單兩邊都有 ⇒ 不進「幣數 vs 現貨」的差，只進強平計算。
 R11 強平（主：逐筆靜態）：每筆進場時帳戶＝錢包 W0（BTC 0.0715、SOL 10）＋常駐多單（BTC 3 張，以本筆進場價重設成本；SOL 無）＋本筆訊號單；全倉、雙向持倉模式
    （hedge mode：常駐多與訊號空分開計，維持保證金＝MMR×(|常駐|＋|訊號|)/P；⚠ 單向模式下兩者會互抵，不在此列）。
    每持有日先扣兩部位當日資金費，再以 E(P)＝W＋Σ Nᵢ/Peᵢ − ΣNᵢ/P、MM(P)＝MMR×Σ|Nᵢ|/P 判 E ≤ MM；
    淨多側強平價 Lp＝(ΣN＋MMR Σ|N|)/(W＋ΣN/Pe)，距離＝日低/Lp − 1；淨空側距離＝Lp/日高 − 1；無解 ⇒ ∞（例：常駐 3 多＋訊號 3 空＝對沖）。
    價格用現貨日高低（⚠ 幣安以標記價強平，未用）；強平清算費不改觸發點；第 1 級 MMR（BTC 13 張在 BTC ≥ 260 USD、SOL 30 張在 SOL ≥ 0.75 USD 都在第 1 級）。
    敏感度（連續帳戶）：窗首 i0 開盤起常駐多單進場（BTC），錢包 W0 隨訊號單實現損益與兩部位資金費逐日變動，全窗逐日判強平；另報「只有常駐單」的同一路徑。
 R12 假濾網臂：在同窗全部翻轉段（＝不加濾網的單）中，均勻隨機擋掉與實際濾網「相同筆數」（同比例）的單，2,000 次；種子 default_rng([20261011, 幣序, 窗序, k, 讀法序])；
    p＝(1＋#{假濾網 年化÷|回落| ≥ 實際})／2,001（單尾）。敏感度：多空分層同筆數（多擋幾筆、空擋幾筆都照實際），種子多加一層 1。
 R13 出口 ① 的「濾網版總損益（幣本位）＞0」讀成 BTC W1、BTC W2、SOL W2 三格的濾網版幣計總損益（BTC 3 張主）都 ＞ 0；各 k 逐條列。
 R14 被擋單統計：占不加濾網單數的比例、賺錢單（每筆（A）報酬 ＞ 0）比例、合計損益（Σ 每筆（A）報酬、Σ 幣計損益）、報酬與持有天數分位（5/25/50/75/95）；被擋與留下各報。
 R15 SOL W1（2021-03-29～2023-12-31）、讀法 ①（ATR14）、副幣 7 支（主格 ATR200，資金費 BTCUSDT）：只描述、不判、不計 N。
 R16 一筆的持有天數＝last − e ＋ 1；（A）每筆報酬＝m − 1（窗尾仍持有＝r(i1) − 1）。
〔執行時發現 2026-10-11 20:39 台北〕首跑在副幣 DOGE 撞到（A）1 倍空單收盤權益 ≤ 0（價格翻倍以上；BTC、SOL 前的五幣都已跑完、未看數字）⇒ 補：
 R17 （A）口徑任一持有日收盤權益 ≤ 0 ⇒ 視為爆倉：該日起權益 0、之後整窗 0（年化 −100%、回落 −100%），各格報爆倉筆數。
⛔ 不寫任何買賣建議、不寫「開幾張安全」；用語一律「假濾網／假訊號」。
"""
from __future__ import annotations
import os, io, json, subprocess, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "resultsATRfilter")
FROZEN = "2026-10-11 20:34（台北）"
SHA = "72df67ed043756589b0453b71ac8ca883d39011c"
END = "2026-10-10"
WINS = (("W1", "2018-01-01", "2023-12-31"), ("W2", "2024-01-01", END))
MAIN = ("BTC", "SOL")
SIDE = ("ETH", "BNB", "XRP", "ADA", "DOGE", "LINK", "LTC")
COINS = MAIN + SIDE
KS = (1, 2, 3)
READS = (("main", 200), ("r1", 14))     # 主格＝讀法②ATR(200)；描述＝讀法①ATR(14)
SMAN = 200
AF0, AFSTEP, AFMAX = 0.02, 0.02, 0.20
FEE = 0.001
FILL = 0.10 / 365.25
NFAKE = 2000
SEED = 20261011
DROP = 30
DAY = 86400
QS = (5, 25, 50, 75, 95)
CM = {"BTC": dict(W0=0.0715, FACE=100.0, n=3, n_sens=10, resident=3, MMR=0.004, fund="BTCUSD_PERP"),
      "SOL": dict(W0=10.0, FACE=10.0, n=30, n_sens=None, resident=0, MMR=0.01, fund="SOLUSD_PERP")}


# ───────────────────────── 資料 ─────────────────────────
def git_text(rel):
    r = subprocess.run(["git", "show", f"{SHA}:{rel}"], cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        raise FileNotFoundError(f"git show {SHA}:{rel} 失敗：{r.stderr.strip()[:200]}")
    return r.stdout


def load_px(sym):
    d = pd.read_csv(io.StringIO(git_text(f"data/crypto/{sym}.csv")), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date")
    d = d[d["date"] <= END].reset_index(drop=True)
    dt = pd.to_datetime(d["date"])
    assert (dt.diff().dropna() == pd.Timedelta(days=1)).all(), f"{sym} 現貨有缺日"
    first_raw = d["date"].iloc[0]
    d = d.iloc[DROP:].reset_index(drop=True)
    s = {"sym": sym, "dates": d["date"].to_numpy(str), "first_raw": first_raw, "last": d["date"].iloc[-1]}
    for c in ("open", "high", "low", "close"):
        s[c] = d[c].astype(float).to_numpy()
    s["day0"] = ((pd.to_datetime(d["date"]) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy("int64")
    return s


FUND_FILES = {
    "BTCUSDT": [("data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv", "calc_time", "last_funding_rate"),
                ("data/crypto_funding/BTCUSDT.csv", "calc_time", "last_funding_rate")],
    "SOLUSDT": [("data/crypto_funding/SOLUSDT.csv", "calc_time", "last_funding_rate")],
    "BTCUSD_PERP": [("data/meta/crypto_cm_funding_rest/BTCUSD_PERP.csv", "funding_time", "funding_rate")],
    "SOLUSD_PERP": [("data/meta/crypto_cm_funding_rest/SOLUSD_PERP.csv", "funding_time", "funding_rate")],
}


def fund_events(kind):
    parts = []
    for rel, tc, rc in FUND_FILES[kind]:
        f = pd.read_csv(io.StringIO(git_text(rel)))
        sec = f[tc].astype("int64") // 1000
        parts.append(pd.DataFrame({"h": (sec // 3600) * 3600, "r": f[rc].astype(float)}))
    ev = pd.concat(parts, ignore_index=True)
    ndup = int(ev["h"].duplicated().sum())
    ev = ev.drop_duplicates("h", keep="first").sort_values("h").reset_index(drop=True)
    info = {"筆數": int(len(ev)), "重複時點丟棄": ndup,
            "首筆UTC": str(pd.Timestamp(int(ev["h"].iloc[0]), unit="s")), "末筆UTC": str(pd.Timestamp(int(ev["h"].iloc[-1]), unit="s"))}
    return ev, info


def fund_daily(day0, ev):
    D = (ev["h"].to_numpy() - 1) // DAY * DAY
    sums = pd.Series(ev["r"].to_numpy()).groupby(D).sum()
    f = pd.Series(day0).map(sums).fillna(0.0).to_numpy(float)
    first, last = int(ev["h"].iloc[0]), int(ev["h"].iloc[-1])
    cov = (first <= day0 + 8 * 3600) & (last >= day0 + DAY)
    return np.where(cov, f, FILL), ~cov


# ───────────────────────── 指標 ─────────────────────────
def sar_talib(h, l):
    n = len(h)
    out = np.full(n, np.nan)
    pos = np.zeros(n, int)
    flip = np.zeros(n, bool)
    up = h[1] - h[0]
    dn = l[0] - l[1]
    is_long = not (dn > 0 and dn > up)
    af = AF0
    if is_long:
        ep, s = h[1], l[0]
    else:
        ep, s = l[1], h[0]
    new_l, new_h = l[1], h[1]
    pos[0] = 1 if is_long else -1
    for i in range(1, n):
        prev_l, prev_h = new_l, new_h
        new_l, new_h = l[i], h[i]
        if is_long:
            if new_l <= s:
                is_long = False
                flip[i] = True
                s = max(ep, prev_h, new_h)
                out[i] = s
                af = AF0
                ep = new_l
                s = s + af * (ep - s)
                s = max(s, prev_h, new_h)
            else:
                out[i] = s
                if new_h > ep:
                    ep = new_h
                    af = min(af + AFSTEP, AFMAX)
                s = s + af * (ep - s)
                s = min(s, prev_l, new_l)
        else:
            if new_h >= s:
                is_long = True
                flip[i] = True
                s = min(ep, prev_l, new_l)
                out[i] = s
                af = AF0
                ep = new_h
                s = s + af * (ep - s)
                s = min(s, prev_l, new_l)
            else:
                out[i] = s
                if new_l < ep:
                    ep = new_l
                    af = min(af + AFSTEP, AFMAX)
                s = s + af * (ep - s)
                s = max(s, prev_h, new_h)
        pos[i] = 1 if is_long else -1
    return out, pos, flip


def atr_wilder(h, l, c, n):
    m = len(c)
    tr = np.full(m, np.nan)
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    a = np.full(m, np.nan)
    if m > n:
        a[n] = tr[1:n + 1].mean()
        for i in range(n + 1, m):
            a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return a


def prep(sym):
    s = load_px(sym)
    s["sar"], s["pos"], s["flip"] = sar_talib(s["high"], s["low"])
    s["sma"] = pd.Series(s["close"]).rolling(SMAN).mean().to_numpy()
    s["atr"] = {n: atr_wilder(s["high"], s["low"], s["close"], n) for _, n in READS}
    s["ivalid"] = max(SMAN - 1, max(n for _, n in READS))     # 第 200 列（0 起算）
    return s


def window_idx(s, a, b):
    d = s["dates"]
    i0 = max(int(np.searchsorted(d, a)), s["ivalid"])
    i1 = int(np.searchsorted(d, b, side="right")) - 1
    return i0, i1


# ───────────────────────── 交易 ─────────────────────────
def segments(s, i0, i1):
    fl = np.flatnonzero(s["flip"])
    out = []
    for t in fl[(fl >= i0) & (fl <= i1 - 1)]:
        nxt = fl[fl > t]
        tn = int(nxt[0]) if len(nxt) else None
        x = tn + 1 if (tn is not None and tn + 1 <= i1) else None
        out.append({"t": int(t), "dir": int(s["pos"][t]), "e": int(t) + 1, "last": (x - 1) if x is not None else i1, "x": x})
    return out


def passes(s, tr, k, n):
    t = tr["t"]
    m, a, c = s["sma"][t], s["atr"][n][t], s["close"][t]
    if tr["dir"] > 0:
        return bool(c > m + k * a)
    return bool(c < m - k * a)


def unit_path(s, tr, fund):
    o, c = s["open"], s["close"]
    e, last, x, sd = tr["e"], tr["last"], tr["x"], tr["dir"]
    Pe = o[e]
    q = 1.0 / Pe
    pref = np.r_[Pe, c[e:last]]
    cf = np.cumsum(-sd * fund[e:last + 1] * q * pref)
    r = 1.0 - FEE + sd * q * (c[e:last + 1] - Pe) + cf
    m = (1.0 - FEE + sd * q * (o[x] - Pe) + cf[-1] - FEE * q * o[x]) if x is not None else None
    # 〔執行時發現 2026-10-11 20:39 台北〕副幣 DOGE 有 1 倍空單收盤權益 ≤ 0（價格翻倍以上）⇒ R17：該日起權益 0（爆倉），之後整窗 0
    bad = np.flatnonzero(r <= 0)
    if len(bad):
        r = r.copy(); r[bad[0]:] = 0.0
        m = 0.0 if x is not None else None
    elif m is not None and m <= 0:
        m = 0.0
    return r, m


def _ratio(num, den):
    return np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)


def coin_path(s, tr, fund, N):
    o, c = s["open"], s["close"]
    e, last, x, sd = tr["e"], tr["last"], tr["x"], tr["dir"]
    Pe = o[e]
    pref = np.r_[Pe, c[e:last]]
    cf = np.cumsum(-sd * fund[e:last + 1] * N / pref)
    fin = FEE * N / Pe
    path = -fin + cf + sd * N * (1.0 / Pe - 1.0 / c[e:last + 1])
    final = (-fin + cf[-1] + sd * N * (1.0 / Pe - 1.0 / o[x]) - FEE * N / o[x]) if x is not None else path[-1]
    return path, float(final)


def stats_from_values(v, T):
    """v：含起點的每日權益序列。"""
    end = v[-1] / v[0]
    mdd = float((v / np.maximum.accumulate(v) - 1.0).min())
    ann = float(end ** (365.25 / T) - 1.0) if end > 0 else -1.0
    if mdd < 0:
        ratio = ann / abs(mdd)
    else:
        ratio = float("inf") if ann > 0 else 0.0
    return {"總損益": float(end - 1.0), "年化": ann, "MDD": mdd, "年化÷|MDD|": ratio}


def equity(i0, i1, trades, paths, take):
    T = i1 - i0 + 1
    ratio = np.ones(T)
    for j, tr in enumerate(trades):
        if not take[j]:
            continue
        r, m = paths[j]
        e, last, x = tr["e"], tr["last"], tr["x"]
        ratio[e - i0:last - i0 + 1] *= _ratio(r, np.r_[1.0, r[:-1]])
        if x is not None:
            ratio[x - i0] *= _ratio(np.array(m), np.array(r[-1]))
    E = np.cumprod(ratio)
    return np.r_[1.0, E]


def fake_ratios(i0, i1, trades, paths, takes):
    """takes：(S, J) bool。向量化算每列的 年化÷|MDD|。"""
    T = i1 - i0 + 1
    J = len(trades)
    fa = np.ones(T); own = np.full(T, J)
    fb = np.ones(T); ex = np.full(T, J)
    for j, tr in enumerate(trades):
        r, m = paths[j]
        e, last, x = tr["e"], tr["last"], tr["x"]
        fa[e - i0:last - i0 + 1] = _ratio(r, np.r_[1.0, r[:-1]])
        own[e - i0:last - i0 + 1] = j
        if x is not None:
            fb[x - i0] = _ratio(np.array(m), np.array(r[-1])); ex[x - i0] = j
    tk = np.concatenate([takes, np.zeros((takes.shape[0], 1), bool)], axis=1)
    inc = np.where(tk[:, own], fa, 1.0) * np.where(tk[:, ex], fb, 1.0)
    E = np.concatenate([np.ones((takes.shape[0], 1)), np.cumprod(inc, axis=1)], axis=1)
    mdd = (E / np.maximum.accumulate(E, axis=1) - 1.0).min(axis=1)
    ann = E[:, -1] ** (365.25 / T) - 1.0
    with np.errstate(divide="ignore", invalid="ignore"):
        rat = np.where(mdd < 0, ann / np.abs(mdd), np.where(ann > 0, np.inf, 0.0))
    return rat


def coin_level(i0, i1, trades, cps, take, W0):
    T = i1 - i0 + 1
    L = np.zeros(T)
    for j, tr in enumerate(trades):
        if not take[j]:
            continue
        path, final = cps[j]
        e, last, x = tr["e"], tr["last"], tr["x"]
        L[e - i0:last - i0 + 1] += path
        if x is not None:
            L[x - i0:] += final
    return np.r_[W0, W0 + L]


def coin_stats(s, i0, i1, trades, cps, take, W0):
    v = coin_level(i0, i1, trades, cps, take, W0)
    T = i1 - i0 + 1
    pnl = float(v[-1] - W0)
    px = np.r_[s["close"][i0 - 1], s["close"][i0:i1 + 1]]
    usd = stats_from_values(v * px, T)
    hold = stats_from_values(W0 * px, T)
    long_pnl = sum(cps[j][1] for j, tr in enumerate(trades) if take[j] and tr["dir"] > 0)
    short_pnl = sum(cps[j][1] for j, tr in enumerate(trades) if take[j] and tr["dir"] < 0)
    return {"窗末幣數": float(v[-1]), "只抱現貨幣數": W0, "幣計總損益": pnl, "幣計總損益÷W0": pnl / W0,
            "多單幣計": float(long_pnl), "空單幣計": float(short_pnl),
            "幣數路徑MDD": float((v / np.maximum.accumulate(v) - 1.0).min()),
            "USD_疊加": usd, "USD_只抱現貨": hold}


# ───────────────────────── 強平 ─────────────────────────
def liq_dist(W, A, SN, SA, mmr, lo, hi):
    B = SN + mmr * SA
    WA = W + A
    if B > 0 and WA > 0:
        Lp = B / WA
        return lo / Lp - 1.0, Lp
    if B < 0 and WA < 0:
        Lp = B / WA
        return Lp / hi - 1.0, Lp
    if B <= 0 and WA >= 0:
        return float("inf"), None
    return -1.0, None


def liq_static(s, tr, fund, cm, n):
    o, c, lo, hi = s["open"], s["close"], s["low"], s["high"]
    e, last, sd = tr["e"], tr["last"], tr["dir"]
    N = n * cm["FACE"]; Nr = cm["resident"] * cm["FACE"]
    Pe = o[e]
    W = cm["W0"] - FEE * N / Pe
    SN = Nr + sd * N; SA = Nr + N; A = SN / Pe
    mind, touched, tday, Lp_e = float("inf"), False, "", None
    for d in range(e, last + 1):
        pref = Pe if d == e else c[d - 1]
        W -= fund[d] * SN / pref
        dist, Lp = liq_dist(W, A, SN, SA, cm["MMR"], lo[d], hi[d])
        if d == e:
            Lp_e = Lp
        if dist < mind:
            mind = dist
        if dist <= 0 and not touched:
            touched, tday = True, s["dates"][d]
    return {"min_dist": mind, "touched": touched, "touch_day": tday, "Lp_entry": Lp_e}


def liq_account(s, i0, i1, trades, take, fund, cm, n, signals=True):
    """連續帳戶：i0 開盤常駐多單進場，錢包逐日變動，全窗逐日判強平。"""
    o, c, lo, hi = s["open"], s["close"], s["low"], s["high"]
    N = n * cm["FACE"]; Nr = cm["resident"] * cm["FACE"]
    W = cm["W0"]
    Pr = o[i0]
    if Nr > 0:
        W -= FEE * Nr / Pr
    by_e = {tr["e"]: tr for j, tr in enumerate(trades) if take[j]} if signals else {}
    cur = None; Pe = None
    mind_all = float("inf"); liq_day = None
    per = {}
    for d in range(i0, i1 + 1):
        if cur is not None and cur["x"] == d:
            W += cur["dir"] * N * (1.0 / Pe - 1.0 / o[d]) - FEE * N / o[d]
            cur = None
        if d in by_e:
            cur = by_e[d]; Pe = o[d]
            W -= FEE * N / Pe
            per[cur["e"]] = float("inf")
        pr_r = Pr if d == i0 else c[d - 1]
        W -= fund[d] * Nr / pr_r
        SN, SA, A = Nr, Nr, (Nr / Pr if Nr > 0 else 0.0)
        if cur is not None:
            pr_s = Pe if d == cur["e"] else c[d - 1]
            W -= fund[d] * cur["dir"] * N / pr_s
            SN += cur["dir"] * N; SA += N; A += cur["dir"] * N / Pe
        if SA == 0:
            continue
        dist, _ = liq_dist(W, A, SN, SA, cm["MMR"], lo[d], hi[d])
        mind_all = min(mind_all, dist)
        if cur is not None:
            per[cur["e"]] = min(per[cur["e"]], dist)
        if dist <= 0:
            liq_day = s["dates"][d]
            break
    return {"強平日": liq_day, "全窗最近距離": mind_all, "每筆最近距離": per}


# ───────────────────────── 一格 ─────────────────────────
def qtl(a):
    a = np.asarray(a, float)
    if len(a) == 0:
        return None
    return {f"p{q}": float(np.percentile(a, q)) for q in QS}


def run_cell(s, ci, wi, i0, i1, fund_u, k, ri, n, fund_cm=None, cm=None, do_fake=True):
    trades = segments(s, i0, i1)
    J = len(trades)
    paths = [unit_path(s, tr, fund_u) for tr in trades]
    keep = np.array([passes(s, tr, k, n) for tr in trades], bool)
    allm = np.ones(J, bool)
    isl = np.array([tr["dir"] > 0 for tr in trades], bool)
    T = i1 - i0 + 1
    rets = np.array([(m if m is not None else r[-1]) - 1.0 for r, m in paths])
    days = np.array([tr["last"] - tr["e"] + 1 for tr in trades])
    wiped = np.array([bool((r <= 0).any()) for r, m in paths], bool)
    res = {"筆數_不加": J, "筆數_加": int(keep.sum()), "被擋": int(J - keep.sum()),
           "A口徑爆倉筆_不加": int(wiped.sum()), "A口徑爆倉筆_加": int((wiped & keep).sum())}
    for arm, take in (("不加", allm), ("加", keep)):
        res[arm] = {"合計": stats_from_values(equity(i0, i1, trades, paths, take), T),
                    "多": stats_from_values(equity(i0, i1, trades, paths, take & isl), T),
                    "空": stats_from_values(equity(i0, i1, trades, paths, take & ~isl), T),
                    "筆數": int(take.sum()), "多筆": int((take & isl).sum()), "空筆": int((take & ~isl).sum()),
                    "窗尾仍持有": int(any(take[j] and trades[j]["x"] is None for j in range(J)))}
    blk = ~keep
    res["被擋單"] = {"占比": float(blk.mean()) if J else None, "筆數": int(blk.sum()),
                  "賺錢比例": float((rets[blk] > 0).mean()) if blk.any() else None,
                  "Σ每筆報酬": float(rets[blk].sum()), "報酬分位": qtl(rets[blk]), "持有天數分位": qtl(days[blk]),
                  "多被擋": int((blk & isl).sum()), "空被擋": int((blk & ~isl).sum())}
    res["留下單"] = {"筆數": int(keep.sum()), "賺錢比例": float((rets[keep] > 0).mean()) if keep.any() else None,
                  "Σ每筆報酬": float(rets[keep].sum()), "報酬分位": qtl(rets[keep]), "持有天數分位": qtl(days[keep])}
    if do_fake and J > 0:
        b = int(blk.sum())
        obs = res["加"]["合計"]["年化÷|MDD|"]
        rng = np.random.default_rng([SEED, ci, wi, k, ri])
        U = rng.random((NFAKE, J))
        takes = np.ones((NFAKE, J), bool)
        if b > 0:
            idx = np.argsort(U, axis=1)[:, :b]
            np.put_along_axis(takes, idx, False, axis=1)
        fr = fake_ratios(i0, i1, trades, paths, takes)
        chk = fake_ratios(i0, i1, trades, paths, keep[None, :])[0]
        assert abs(chk - obs) <= 1e-9 * max(1, abs(obs)) or (np.isinf(chk) and np.isinf(obs)), (chk, obs)
        p = (1 + int((fr >= obs - 1e-12).sum())) / (NFAKE + 1)
        # 分層敏感度
        rng2 = np.random.default_rng([SEED, ci, wi, k, ri, 1])
        takes2 = np.ones((NFAKE, J), bool)
        for grp in (isl, ~isl):
            gi = np.flatnonzero(grp); bg = int((blk & grp).sum())
            if bg > 0:
                U2 = rng2.random((NFAKE, len(gi)))
                sel = gi[np.argsort(U2, axis=1)[:, :bg]]
                np.put_along_axis(takes2, sel, False, axis=1)
        fr2 = fake_ratios(i0, i1, trades, paths, takes2)
        p2 = (1 + int((fr2 >= obs - 1e-12).sum())) / (NFAKE + 1)
        res["假濾網"] = {"次數": NFAKE, "擋單數": b, "實際": obs, "p": p, "假濾網中位": float(np.median(fr)),
                      "假濾網p5": float(np.percentile(fr, 5)), "假濾網p95": float(np.percentile(fr, 95)),
                      "實際在假濾網分布的分位": float((fr < obs).mean()), "前50次": [float(v) for v in fr[:50]],
                      "分層p": p2, "分層中位": float(np.median(fr2))}
    if fund_cm is not None:
        for tag, nn in (("主", cm["n"]), ("敏感度", cm["n_sens"])):
            if nn is None:
                continue
            N = nn * cm["FACE"]
            cps = [coin_path(s, tr, fund_cm, N) for tr in trades]
            res[f"幣本位_{tag}"] = {"張數": nn,
                                  "不加": coin_stats(s, i0, i1, trades, cps, allm, cm["W0"]),
                                  "加": coin_stats(s, i0, i1, trades, cps, keep, cm["W0"]),
                                  "被擋單Σ幣計": float(sum(cps[j][1] for j in range(J) if blk[j]))}
            lq = [liq_static(s, tr, fund_cm, cm, nn) for tr in trades]
            def lsum(mask):
                sel = [lq[j] for j in range(J) if mask[j]]
                fin = [q["min_dist"] for q in sel if np.isfinite(q["min_dist"])]
                return {"筆數": len(sel), "觸及筆數": int(sum(q["touched"] for q in sel)),
                        "最近距離最小": (min(fin) if fin else None), "最近距離分位": qtl(fin),
                        "無強平價筆數": int(sum(not np.isfinite(q["min_dist"]) for q in sel))}
            res[f"強平_{tag}"] = {"靜態_加": lsum(keep), "靜態_不加": lsum(allm),
                                 "靜態_加_多": lsum(keep & isl), "靜態_加_空": lsum(keep & ~isl)}
            acc = {}
            for arm, take in (("加", keep), ("不加", allm)):
                a = liq_account(s, i0, i1, trades, take, fund_cm, cm, nn)
                fin = [v for v in a["每筆最近距離"].values() if np.isfinite(v)]
                acc[arm] = {"強平日": a["強平日"], "全窗最近距離": a["全窗最近距離"], "訊號單最近距離最小": (min(fin) if fin else None)}
            if cm["resident"] > 0:
                a = liq_account(s, i0, i1, trades, allm, fund_cm, cm, nn, signals=False)
                acc["只有常駐單"] = {"強平日": a["強平日"], "全窗最近距離": a["全窗最近距離"]}
            res[f"強平_{tag}"]["連續帳戶"] = acc
            if tag == "主":
                res["_trades_coin"] = [cps[j][1] for j in range(J)]
                res["_trades_liq"] = [lq[j]["min_dist"] for j in range(J)]
    res["_trades"] = trades
    res["_keep"] = keep.tolist()
    res["_rets"] = rets.tolist()
    return res


def hold_stats(s, i0, i1):
    px = np.r_[s["close"][i0 - 1], s["close"][i0:i1 + 1]]
    return stats_from_values(px / px[0], i1 - i0 + 1)


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        if np.isinf(f):
            return "inf" if f > 0 else "-inf"
        if np.isnan(f):
            return None
        return f
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main():
    os.makedirs(OUT, exist_ok=True)
    ev_u, info_u = fund_events("BTCUSDT")
    ev_su, info_su = fund_events("SOLUSDT")
    ev_cm = {k: fund_events(v["fund"]) for k, v in CM.items()}
    out = {"登錄": "PREREG加密ATR通道濾網_SAR翻轉_v1 sha480e12a0fb077735", "讀法寫死": FROZEN, "資料commit": SHA, "資料尾": END,
           "資金費": {"BTCUSDT": info_u, "SOLUSDT": info_su, **{CM[k]["fund"]: v[1] for k, v in ev_cm.items()}},
           "格": {}, "現貨": {}}
    rows, trows = [], []
    for ci, sym in enumerate(COINS):
        s = prep(sym)
        fu, fu_miss = fund_daily(s["day0"], ev_u)
        out["現貨"][sym] = {"檔首": s["first_raw"], "剔除後首": s["dates"][0], "資料尾": s["last"], "有效首日": s["dates"][s["ivalid"]]}
        variants = [("BTCUSDT", fu, fu_miss)]
        if sym == "SOL":
            fsu, fsu_miss = fund_daily(s["day0"], ev_su)
            variants.append(("SOLUSDT", fsu, fsu_miss))
        fcm = fcm_miss = None
        if sym in CM:
            fcm, fcm_miss = fund_daily(s["day0"], ev_cm[sym][0])
        for wi, (wn, a, b) in enumerate(WINS):
            i0, i1 = window_idx(s, a, b)
            if i1 - i0 < 30:
                continue
            for ri, (rn, n) in enumerate(READS):
                if sym not in MAIN and rn != "main":
                    continue
                for fk, fu_, fm_ in variants:
                    if fk == "SOLUSDT" and rn != "main":
                        continue
                    for k in KS:
                        key = f"{sym}|{wn}|{rn}|k{k}|{fk}"
                        main_like = sym in CM and fk == "BTCUSDT"
                        res = run_cell(s, ci, wi, i0, i1, fu_, k, ri, n,
                                       fund_cm=fcm if main_like else None, cm=CM.get(sym) if main_like else None,
                                       do_fake=True)
                        trades = res.pop("_trades"); keep = res.pop("_keep"); rets = res.pop("_rets")
                        tcoin = res.pop("_trades_coin", None); tliq = res.pop("_trades_liq", None)
                        held = np.zeros(i1 - i0 + 1, bool)
                        for tr in trades:
                            held[tr["e"] - i0:tr["last"] - i0 + 1] = True
                        res["窗"] = {"有效首": s["dates"][i0], "尾": s["dates"][i1], "天數": i1 - i0 + 1,
                                    "資金費代入天數_窗內": int(fm_[i0:i1 + 1].sum()), "資金費代入天數_持有日": int((fm_[i0:i1 + 1] & held).sum())}
                        if main_like:
                            res["窗"]["幣本位資金費代入天數_窗內"] = int(fcm_miss[i0:i1 + 1].sum())
                            res["窗"]["幣本位資金費代入天數_持有日"] = int((fcm_miss[i0:i1 + 1] & held).sum())
                        res["只抱現貨_A"] = hold_stats(s, i0, i1)
                        out["格"][key] = res
                        for arm in ("不加", "加"):
                            for side in ("合計", "多", "空"):
                                st = res[arm][side]
                                row = {"coin": sym, "window": wn, "reading": rn, "k": k, "funding": fk, "arm": arm, "side": side,
                                       "start": s["dates"][i0], "end": s["dates"][i1],
                                       "trades": res[arm]["筆數"] if side == "合計" else res[arm]["多筆" if side == "多" else "空筆"],
                                       "total_pnl": st["總損益"], "ann": st["年化"], "mdd": st["MDD"], "ann_over_mdd": st["年化÷|MDD|"]}
                                if side == "合計":
                                    row["open_at_end"] = res[arm]["窗尾仍持有"]
                                    if "幣本位_主" in res:
                                        cs = res["幣本位_主"][arm]
                                        row.update({"coin_pnl": cs["幣計總損益"], "coin_pnl_over_W0": cs["幣計總損益÷W0"],
                                                    "coin_end": cs["窗末幣數"], "spot_coins": cs["只抱現貨幣數"]})
                                    if arm == "加" and "假濾網" in res:
                                        row["fake_p"] = res["假濾網"]["p"]
                                rows.append(row)
                        if sym in MAIN and fk == "BTCUSDT":
                            for j, tr in enumerate(trades):
                                trows.append({"coin": sym, "window": wn, "reading": rn, "k": k, "t": s["dates"][tr["t"]],
                                              "dir": tr["dir"], "entry": s["dates"][tr["e"]], "entry_px": s["open"][tr["e"]],
                                              "exit": s["dates"][tr["x"]] if tr["x"] is not None else "",
                                              "exit_px": s["open"][tr["x"]] if tr["x"] is not None else np.nan,
                                              "days": tr["last"] - tr["e"] + 1, "close_t": s["close"][tr["t"]],
                                              "U_t": s["sma"][tr["t"]] + k * s["atr"][n][tr["t"]],
                                              "D_t": s["sma"][tr["t"]] - k * s["atr"][n][tr["t"]],
                                              "kept": int(keep[j]), "ret_unit": rets[j],
                                              "coin_pnl": tcoin[j] if tcoin is not None else np.nan,
                                              "liq_min_dist": tliq[j] if tliq is not None else np.nan})
        print(sym, "done", flush=True)
    # 出口
    ex = {}
    G = out["格"]
    for k in KS:
        b1 = G[f"BTC|W1|main|k{k}|BTCUSDT"]; b2 = G[f"BTC|W2|main|k{k}|BTCUSDT"]; s2 = G[f"SOL|W2|main|k{k}|BTCUSDT"]
        c = {}
        for lab, g in (("BTC_W1", b1), ("BTC_W2", b2)):
            c[f"{lab}_比值勝"] = g["加"]["合計"]["年化÷|MDD|"] > g["不加"]["合計"]["年化÷|MDD|"]
            c[f"{lab}_p<0.10"] = g["假濾網"]["p"] < 0.10
        c["SOL_W2_比值勝"] = s2["加"]["合計"]["年化÷|MDD|"] > s2["不加"]["合計"]["年化÷|MDD|"]
        for lab, g in (("BTC_W1", b1), ("BTC_W2", b2), ("SOL_W2", s2)):
            c[f"{lab}_幣計>0"] = g["幣本位_主"]["加"]["幣計總損益"] > 0
        c["全部滿足"] = all(c.values())
        ex[f"k{k}"] = c
    nsat = sum(ex[f"k{k}"]["全部滿足"] for k in KS)
    out["出口"] = {"逐k": ex, "滿足的k數": nsat, "判": "① 成立" if nsat >= 2 else "② 測不出"}
    with open(os.path.join(OUT, "ATRfilter.json"), "w", encoding="utf-8") as f:
        json.dump(jsonable(out), f, ensure_ascii=False, indent=1)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "ATRfilter_main.csv"), index=False, encoding="utf-8")
    pd.DataFrame(trows).to_csv(os.path.join(OUT, "ATRfilter_trades.csv"), index=False, encoding="utf-8")
    print(json.dumps(jsonable(out["出口"]), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

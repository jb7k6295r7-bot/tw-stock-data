# -*- coding: utf-8 -*-
"""PREREGC17「爆量大漲日開多（合約加碼、條件出場）v1」（sha 6fd7cca8b425a8c5，3548 B）——回測線執行端（獨立重跑）。
裁定 seq330：發號、探索後確認 ⇒ 出口 ① 最多「暫定成立（探索後）」；加密 N 帳 ＋82（累計 297）；補三條（使用者判準、強平風險、與現行計畫重疊天數）。

⭐ 讀法寫死：2026-10-11 00:45（台北，WSL `TZ=Asia/Taipei date` 取得）——⛔ 在算出任何報酬之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法一律標【執行者補】。
   寫死前已看過的：登錄 §一～§四、§六（⛔ 沒讀 §五 本線數字）；裁定 seq330；加密線 0035 信（第 8 行未讀）；加密線現況檔（使用者現行槓桿、買點、B3／B4）；
   資料庫 1005-1321 用法陷阱；資料檔頭尾幾列與資金費起訖（未碰任何報酬）。

資料：公開 tw-stock-data main commit 69e257c882067f4d652d39749b1635dabf54b911 ⇒ git archive 到 ~/c17data/<sha>/（唯讀；同 C10 做法）
   現貨日 K：data/crypto/<SYM>.csv（Binance，USDT 計價，UTC 日界；量用 quote_volume＝USDT）
   資金費：data/crypto_funding/BTCUSDT.csv（U 本位永續，calc_time 毫秒）；幣本位版：data/meta/crypto_cm_funding_rest/BTCUSD_PERP.csv
   標記價（強平敏感度）：data/crypto_mark/BTCUSDT.csv（2020-01-01～2026-09-30）
   早年 BTC：私有 ~/us-stock-data/data/crypto_private/BTC_bitstamp_2013_2017.csv（⛔ 私有原始資料不進 repo，結果只放彙總）

⭐ 落地讀法
 K1 訊號（§二）：UTC 日 t 收盤，qv_t ＞ 2 × mean(qv_{t−20..t−1}) 且 close_t／close_{t−1} − 1 ＞ 5%；需前 20 日都在（保留資料內）才算。
 K2 進場（主臂）：t＋1 開盤；持有日＝第一個持有日 e＝t＋1 起。敏感度「t 收盤進場」：進場價 close_t，持有日同樣從 t＋1 起，另付 t＋1 00:00 那筆資金費。
 K3 出場（主臂）：k ≥ e 的每天收盤，若 close_k ＜ min(low_t（訊號日）, min(low_{k−10..k−1})) ⇒ k＋1 開盤平倉；最後持有日＝k【執行者補：「前 10 日」＝k 之前 10 天、不含 k】。
    ⛔ 不設最長天數；窗尾仍持有 ⇒ 以窗尾收盤估值、不扣平倉費，件數必報；出場觸發在窗尾那天也算窗尾仍持有【執行者補】。
    持倉中（收盤時仍持有）的訊號不加碼、不重設；出場開盤那天（x）已空手，x 當天訊號可進場（x＋1 開盤）【執行者補】。
 K4 每日淨報酬（每 1 單位名目）【執行者補：日界與開收口徑】：持有日 d 的毛報酬 g_d＝close_d／open_d（進場日，開盤進場）或 close_d／close_{d−1}（其他日）；
    最後持有日再乘 open_{x}／close_{x−1}（平倉在 x 開盤）；淨＝g−1 − 當日資金費 − 0.1%（進場日）− 0.1%（平倉的最後持有日）。
 K5 資金費：每筆時戳先截到秒、再截到整點（陷阱 d）；整點 h 屬於「持有日 D」，D＝(h−1 秒) 的 UTC 日期——即 D 08:00、16:00 與 D＋1 00:00 三筆屬 D
    （開盤進場不付進場當天 00:00、開盤平倉要付平倉當天 00:00）【執行者補】；逐筆加總，⛔ 不假設一天 3 筆；多方付正值。
    缺段：持有日 D 的整段 (D 00:00, D＋1 00:00] 不完全落在資料首筆～末筆之間 ⇒ 整天以年化 10%（÷365.25）代入；報窗內與持有日的代入天數。
    8 幣：登錄寫「資金費照上」⇒ 主格一律用 BTCUSDT 實際值（缺段 10%）【執行者補：照字面】；敏感度＝各幣自己的 USDT 永續資金費（DB 有 BNB、DOGE、ETH、SOL、XRP；ADA、LINK、LTC 沒有 ⇒ 用 BTCUSDT）。
    幣本位版（§一）：BTC 改用 BTCUSD_PERP 資金費另報。
 K6 窗（§三）：BTC W1 2018-01-01～2023-12-31、W2 2024-01-01～2026-10-09，各窗獨立跑（窗外訊號不帶入）【執行者補】；
    8 幣：各幣上市後前 30 根剔除（陷阱 b；剔除的列也不進 20 日均量）；各幣窗＝保留資料第 21 天～2026-10-09。
    早年 BTC：登錄寫 Coin Metrics PriceUSD＋volume_reported_spot_usd_1d（2013～2017），但資料庫私有 coinmetrics/btc_daily.csv 沒有 volume 欄、也沒有日高低
    ⇒ 該格照登錄無法算，標「待資料庫補」；改用私有 Bitstamp 2013-01-01～2017-08-16 日 K（qv＝volume×close，USD）跑【替代版，偏離，只描述、不當判定】，
    窗＝保留資料第 21 天～2017-08-16；⛔ 不接 Binance（接縫兩所量級不可比）。
 K7 判定量「每天多賺」＝窗內持有日淨報酬平均 − 窗內全部日 close/close−1 平均（不扣成本）；8 幣合併＝各幣持有日（淨 − 該幣窗平均）全部持有日等權平均【執行者補】，
    另報各幣等權。另報：總損益（Σ 每筆複利報酬，每 1 單位名目）、筆數、勝率（每筆報酬 ＞ 0）、中位持有天數、單筆最差、期間最大浮虧（min(持有日低)／進場價 − 1）。
 K8 假訊號臂：窗內持倉遮罩（含進出場位置，成本與 open 調整照 K4 從遮罩重建）循環平移 k～U{1..T−1}，2,000 次，種子 20260923；
    單尾 p＝(1＋#{平移 ≥ 實際})／2,001；8 幣合併每次每幣各抽 k。窗尾段重建規則同 K3（在窗尾的段不扣平倉費）。
    隨機進場臂：同筆數、同持有天數（實際各筆天數），每筆進場日在窗內均勻抽（整筆落在窗內，可重疊），2,000 次，同 p 算法。
 K9 出口（§三）：① 方向與本線一致 且 BTC W1、W2、早年 BTC、8 幣合併四項「每天多賺」都 ＞ 0 且 8 幣合併假訊號 p ＜ 0.05 ⇒ 「暫定成立（探索後）」；
    ② 任一 ≤ 0 或合併 p ≥ 0.05 ⇒ 測不出；③ 對帳差 ＞ 0.05%／天或方向相反 ⇒ 先對帳。早年格若只有替代版 ⇒ ① 加註「早年格待正式資料」。
 K10 使用者判準（seq330 補 1）：主臂 1 倍（全部資金當名目、空手時現金 0%）每日權益複利 vs 同窗一直抱 BTC 現貨（收盤）；
    年化＝期末^(365.25／天數)−1；MDD＝收盤權益最大回落；合格＝年化 ＞ 持有 且 年化÷|MDD| ≥ 持有；另列＝只年化 ＞ 持有；不合格＝其餘。BTC 兩窗各判。
 K11 強平（seq330 補 2；照 C10 R5 思路改 U 本位逐倉）：使用者現行槓桿＝5 倍（加密線現況：BTCUSD 幣本位全倉 5 倍；SOL 提醒 5 倍）⇒ 每筆 5 倍逐倉、保證金＝名目／5；
    錢包 W（每 1 USDT 名目）＝0.2 − 進場費 0.1% − Σ 資金費（rate × 前一日收盤／進場價；進場日用進場價）；每持有日先扣當日資金費，再算
    Lp＝Pe ×（1 − W）／（1 − m），日低 ≤ Lp ⇒ 觸及強平；m ∈ {0.5%、1%、2%} 全報（主句用 2%）；價格用現貨日低，BTC 2020 起另報標記價日低。
    每筆報：期間最大浮虧、「最低點距強平價」＝min(日低／Lp − 1)、有無觸及。⚠ 使用者實際是全倉（帳戶其他餘額會撐住），逐倉是較嚴口徑。
 K12 與現行計畫（seq330 補 3）：⛔ 不改計畫；報 W2 持有日中日低 ≤ 買點 72,000／66,000／58,625／54,000 的天數、收盤 ＜ 58,625（A1）天數；
    B3（2029-05-01 起）、B4（2029-04 起破 200 日線）尚未生效 ⇒ 歷史重疊 0；另描述 W2 持有日收盤 ＜ 200 日線天數（只是條件本身）。
 K13 鄰格（描述、不判、不計 N）：量倍數 {1.5、2、2.5} × 漲幅 {4%、5%、7%}；出場 {前 5／10／20 日低（同 K3 與訊號日低取小）、收盤 ＜ 10／20 日均線（含當日）、
    收盤 ＜ 持有以來最高收盤 ×(1−8／12／15%)、固定 7／14／28 個持有日（第 N 個持有日收盤後次日開盤平）}；報 BTC W1、W2、早年替代、8 幣合併的每天多賺。
 K14 --check：fixture＋會變紅的反例（a 均量不含 t、b 平倉用次日開盤、c 資金費毫秒尾數歸日、d 持倉中不重設）；
    另寫一支純迴圈參考實作重算主格與抽樣鄰格（種子 20260923）的交易清單與每天多賺、20 個平移，逐位比，差異須 0。
 K15 前瞻（§六）：2026-10-12 起，BTC 每次訊號記：訊號日、進場日與價、出場日與價、持有天數、每天多賺、是否實際交易（不交易也記）；累積 20 筆再判。
⛔ 不寫任何買賣建議、不寫「開幾倍安全」；用語一律「假訊號」。

〔執行時發現 2026-10-11 00:46 台北〕--check fixture c 抓到資金費歸日的日期秒數換算錯（pandas 日期解析度不是奈秒 ⇒ 全部被當缺段）；在跑主格之前修正，主格只跑過修正後版本。
〔執行時發現 2026-10-11 00:48 台北〕independent.json 寫檔（00:47:45）之後才讀登錄 §五；字面讀法與 §五 差 ＞ 0.05%／天且 W2、8 幣方向相反 ⇒ 出口 ③。
   之後加的 --recon（變體對照）與 --diag-lowmax（出場讀成「收盤破訊號日低或破前 10 日低，任一條就出」＝max）只作對帳診斷，⛔ 不改主格、不改讀法、不當判定。
〔補記 2026-10-11 00:55 台北｜資料庫 1011-0044 轉知〕BTCUSDT 永續資金費 2019-09-10～2019-12-31 已補（main 283eec12b2 data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv），
   與主檔 2020-01-01 起連續 ⇒ v2（--fund2019）把這段併入；2019-09-10 以前永續不存在 ⇒ 照登錄年化 10% 並報天數；2026-10-01 起月封存未發布 ⇒ 照實代入並報。
   ⛔ 規則、讀法不變；v1 independent.json（00:47:45）原樣保留為獨立紀錄，v2 另存 *_v2.json。
〔執行時發現〕LINK 2020-03-12 現貨日低 0.0001（Binance 插針，原始資料如此、不改）⇒ LINK 最大浮虧、強平描述被這根拉低；ADA、DOGE、LINK 2025-10-10 也有長下影。
"""
from __future__ import annotations
import os, sys, json, math, argparse, html
import numpy as np
import pandas as pd

SHA = "69e257c882067f4d652d39749b1635dabf54b911"
ROOT = os.path.expanduser(f"~/c17data/{SHA}")
PRIV = os.path.expanduser("~/us-stock-data/data/crypto_private")
REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest", "resultsC17")
# v2（資料庫 1011-0044 轉知）：BTCUSDT 2019-09-10～2019-12-31 資金費補檔，main 283eec12b2 data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv
SHA_F2019 = "283eec12b2bc0eb17ffa756c5a0efe3a49d16d92"
F2019 = os.path.expanduser(f"~/c17data/{SHA_F2019}/data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv")
FUND2019 = False      # v1（independent.json）＝False；v2 以 --fund2019 開
FROZEN = "2026-10-11 00:45（台北）"
COINS8 = ["SOL", "ETH", "BNB", "XRP", "ADA", "DOGE", "LINK", "LTC"]
OWN_FUND = {"ETH", "BNB", "SOL", "XRP", "DOGE"}
W1 = ("2018-01-01", "2023-12-31")
W2 = ("2024-01-01", "2026-10-09")
END = "2026-10-09"
EARLY_END = "2017-08-16"
COST = 0.001
FILL = 0.10 / 365.25
SEED = 20260923
NPERM = 2000
LEV = 5
MMRS = (0.005, 0.01, 0.02)
BUY = (72000, 66000, 58625, 54000)
A1 = 58625
MAIN_SIG = (2.0, 0.05)
MAIN_EXIT = ("low", 10)
EXITS = [("low", 5), ("low", 10), ("low", 20), ("ma", 10), ("ma", 20), ("trail", 0.08), ("trail", 0.12), ("trail", 0.15),
         ("fixed", 7), ("fixed", 14), ("fixed", 28)]
SIGS = [(vm, up) for vm in (1.5, 2.0, 2.5) for up in (0.04, 0.05, 0.07)]
DAY = 86400


# ───────────────────────── 資料 ─────────────────────────
def _consec(dates):
    d = pd.to_datetime(pd.Series(dates))
    return (d.iloc[-1] - d.iloc[0]).days + 1 == len(d)


def load_binance(sym, drop30=True):
    d = pd.read_csv(os.path.join(ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date")
    d = d[d["date"] <= END].reset_index(drop=True)
    assert _consec(d["date"]), f"⛔ {sym} 現貨有缺日"
    assert d["date"].iloc[-1] == END, (sym, d["date"].iloc[-1])
    if drop30:
        d = d.iloc[30:].reset_index(drop=True)
    return _pack(sym, d, d["quote_volume"].astype(float).to_numpy())


def load_bitstamp():
    d = pd.read_csv(os.path.join(PRIV, "BTC_bitstamp_2013_2017.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date")
    d = d[(d["date"] >= "2013-01-01") & (d["date"] <= EARLY_END)].reset_index(drop=True)
    assert _consec(d["date"]), "⛔ Bitstamp 有缺日"
    return _pack("BTC_early", d, (d["volume"].astype(float) * d["close"].astype(float)).to_numpy())


def _pack(name, d, qv):
    s = {"name": name, "dates": d["date"].to_numpy(str)}
    for c in ("open", "high", "low", "close"):
        s[c] = d[c].astype(float).to_numpy()
    s["qv"] = np.asarray(qv, float)
    c = s["close"]
    s["rcc"] = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
    return s


def _funding_events(path, tcol, rcol, mut=None):
    f = pd.read_csv(path)
    sec = (f[tcol].astype("int64") // 1000)
    h = (sec // 3600) * 3600
    if mut == "ms_date":   # 反例：直接用毫秒時戳的日期歸日（00:00:00.002 會被歸到 D 而不是 D−1）
        h = f[tcol].astype("int64") // 1000
    f = pd.DataFrame({"h": h.astype("int64"), "r": f[rcol].astype(float)}).drop_duplicates("h").sort_values("h")
    return f


def funding_arrays(dates, ev, mut=None):
    """回 fund[d]（持有日 D 的資金費和）、fend[d]（D＋1 00:00 那一筆）、miss[d]（整天代入 10%）。"""
    day0 = ((pd.to_datetime(pd.Series(dates)) - pd.Timestamp("1970-01-01")).dt.total_seconds()).round().astype("int64").to_numpy()
    if mut == "ms_date":
        dd = ev["h"].to_numpy() // DAY * DAY
    else:
        dd = (ev["h"].to_numpy() - 1) // DAY * DAY
    g = pd.Series(ev["r"].to_numpy()).groupby(dd).sum()
    is_mid = (ev["h"].to_numpy() % DAY) == 0
    ge = pd.Series(ev["r"].to_numpy()[is_mid]).groupby(dd[is_mid]).sum()
    first, last = int(ev["h"].min()), int(ev["h"].max())
    cov = (first <= day0 + 8 * 3600) & (day0 + DAY <= last)   # 當天第一個 8 小時時點（D 08:00）起都有＝整天有【v2 修：原寫 D 00:00:01，會把首日 08:00 才開始的那天誤當缺】
    fund = np.where(cov, g.reindex(day0).fillna(0.0).to_numpy(), FILL)
    fend = np.where(cov, ge.reindex(day0).fillna(0.0).to_numpy(), FILL / 3.0)
    cnt = pd.Series(1, index=dd).groupby(level=0).sum().reindex(day0).fillna(0).to_numpy()
    return fund, fend, ~cov, cnt


def fund_src(kind):
    if kind == "BTCUSDT":
        ev = _funding_events(os.path.join(ROOT, "data", "crypto_funding", "BTCUSDT.csv"), "calc_time", "last_funding_rate")
        if FUND2019:
            e19 = _funding_events(F2019, "calc_time", "last_funding_rate")
            ev = pd.concat([e19, ev]).drop_duplicates("h").sort_values("h").reset_index(drop=True)
        return ev
    if kind == "BTCUSD_CM":
        return _funding_events(os.path.join(ROOT, "data", "meta", "crypto_cm_funding_rest", "BTCUSD_PERP.csv"), "funding_time", "funding_rate")
    return _funding_events(os.path.join(ROOT, "data", "crypto_funding", f"{kind}USDT.csv"), "calc_time", "last_funding_rate")


def attach_funding(s, ev, mut=None):
    if ev is None:
        n = len(s["dates"])
        s["fund"], s["fend"], s["fmiss"], s["fcnt"] = np.full(n, FILL), np.full(n, FILL / 3), np.ones(n, bool), np.zeros(n)
    else:
        s["fund"], s["fend"], s["fmiss"], s["fcnt"] = funding_arrays(s["dates"], ev, mut)
    return s


# ───────────────────────── 引擎 ─────────────────────────
def signals(s, vm, up, mut=None):
    qv = pd.Series(s["qv"])
    avg = qv.rolling(20).mean().shift(1) if mut != "avg_incl_t" else qv.rolling(20).mean()
    c = s["close"]
    ret = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
    sig = (qv.to_numpy() > vm * avg.to_numpy()) & (ret > up)
    sig[:20] = False
    return sig


def exit_hit(s, k, t, e, rule):
    kind, p = rule
    c, lo = s["close"], s["low"]
    if kind == "low":
        lv = min(lo[t], lo[max(k - p, 0):k].min())
        return c[k] < lv
    if kind == "lowmax":      # 對帳診斷用（讀 §五 之後才加）：收盤 ＜ max(訊號日低, 前 N 日低)，即「任一條破就出」
        lv = max(lo[t], lo[max(k - p, 0):k].min())
        return c[k] < lv
    if kind == "lowonly":     # 對帳診斷用：只看前 N 日低
        return c[k] < lo[max(k - p, 0):k].min()
    if kind == "sigonly":     # 對帳診斷用：只看訊號日低
        return c[k] < lo[t]
    if kind == "ma":
        if k - p + 1 < 0:
            return False
        return c[k] < c[k - p + 1:k + 1].mean()
    if kind == "trail":
        return c[k] < c[e:k + 1].max() * (1 - p)
    if kind == "fixed":
        return (k - e + 1) >= p
    raise ValueError(kind)


def simulate(s, i0, i1, sig, rule, mode="open", mut=None):
    """回 trades：dict(t, e, last, x)；x＝平倉開盤日索引，窗尾仍持有 ⇒ x＝None。只收 i0 ≤ t、e ≤ i1。
    mut＝reset：持倉中再出訊號就把訊號日低重設（反例）。"""
    trades = []
    t = i0
    while t <= i1:
        if sig[t] and t + 1 <= i1:
            e = t + 1
            tref = t
            k = e
            x = None
            while k <= i1:
                if mut == "reset" and sig[k]:
                    tref = k
                if exit_hit(s, k, tref, e, rule):
                    if k + 1 <= i1:
                        x = k + 1
                    break
                k += 1
            last = min(k, i1)
            trades.append({"t": t, "e": e, "last": last, "x": x})
            if x is None:
                break
            t = x
            continue
        t += 1
    return trades


def flags_from_trades(n, trades):
    held = np.zeros(n, bool); ent = np.zeros(n, bool); lastx = np.zeros(n, bool)
    for tr in trades:
        held[tr["e"]:tr["last"] + 1] = True
        ent[tr["e"]] = True
        if tr["x"] is not None:
            lastx[tr["last"]] = True
    return held, ent, lastx


def net_series(s, held, ent, lastx, mode="open", mut=None):
    """K4：每日淨報酬（未持有日 0）。"""
    o, c = s["open"], s["close"]
    n = len(c)
    prevc = np.r_[np.nan, c[:-1]]
    nexto = np.r_[o[1:], np.nan]
    g = np.where(ent & (mode == "open"), c / o, c / prevc)
    if mut == "exit_close":   # 反例：在觸發日收盤平（不是次日開盤）
        adj = np.ones(n)
    else:
        adj = np.where(lastx, nexto / c, 1.0)
    g = g * adj
    net = g - 1.0 - s["fund"] - COST * ent - COST * lastx
    if mode == "close":
        prevfend = np.r_[0.0, s["fend"][:-1]]
        net = net - np.where(ent, prevfend, 0.0)
    return np.where(held, net, 0.0)


def trade_table(s, trades, net, mode="open"):
    rows = []
    for tr in trades:
        e, l = tr["e"], tr["last"]
        pe = s["open"][e] if mode == "open" else s["close"][tr["t"]]
        r = float(np.prod(1.0 + net[e:l + 1]) - 1.0)
        rows.append({"signal": s["dates"][tr["t"]], "entry": s["dates"][e], "entry_px": pe,
                     "exit": s["dates"][tr["x"]] if tr["x"] is not None else "", "exit_px": s["open"][tr["x"]] if tr["x"] is not None else np.nan,
                     "days": l - e + 1, "ret": r, "maxdd": float(s["low"][e:l + 1].min() / pe - 1.0), "open_at_end": tr["x"] is None})
    return rows


def unit_run(s, i0, i1, vm, up, rule, mode="open", mut=None):
    sig = signals(s, vm, up, mut)
    tr = simulate(s, i0, i1, sig, rule, mode, mut)
    held, ent, lastx = flags_from_trades(len(s["close"]), tr)
    net = net_series(s, held, ent, lastx, mode, mut)
    wm = float(np.mean(s["rcc"][i0:i1 + 1]))
    hd = held[i0:i1 + 1]
    return {"trades": tr, "held": held, "ent": ent, "lastx": lastx, "net": net, "wmean": wm,
            "hsum": float(net[i0:i1 + 1][hd].sum()), "hdays": int(hd.sum()),
            "excess": float(net[i0:i1 + 1][hd].mean() - wm) if hd.any() else np.nan}


def summary(s, run, i0, i1, mode="open"):
    rows = trade_table(s, run["trades"], run["net"], mode)
    rets = np.array([r["ret"] for r in rows]) if rows else np.array([])
    return {"每天多賺": run["excess"], "持有日淨平均": (run["hsum"] / run["hdays"]) if run["hdays"] else np.nan, "窗全部日平均": run["wmean"],
            "筆數": len(rows), "持有日數": run["hdays"], "窗天數": i1 - i0 + 1, "持有比例": run["hdays"] / (i1 - i0 + 1),
            "總損益_每1單位名目": float(rets.sum()) if len(rets) else 0.0, "勝率": float((rets > 0).mean()) if len(rets) else np.nan,
            "中位持有天數": float(np.median([r["days"] for r in rows])) if rows else np.nan,
            "單筆最差": float(rets.min()) if len(rets) else np.nan, "單筆最好": float(rets.max()) if len(rets) else np.nan,
            "期間最大浮虧": float(min(r["maxdd"] for r in rows)) if rows else np.nan,
            "窗尾仍持有件數": int(sum(r["open_at_end"] for r in rows)),
            "持有日資金費代入天數": int((run["held"] & s["fmiss"])[i0:i1 + 1].sum()), "窗內資金費代入天數": int(s["fmiss"][i0:i1 + 1].sum()),
            "窗": f"{s['dates'][i0]}～{s['dates'][i1]}"}


def window_idx(s, a, b):
    d = s["dates"]
    i0 = max(int(np.searchsorted(d, a)), 20)
    i1 = int(np.searchsorted(d, b, side="right")) - 1
    return i0, i1


# ───────────────────────── 對照臂 ─────────────────────────
def rebuild(held):
    T = len(held)
    prev = np.r_[False, held[:-1]]
    nxt = np.r_[held[1:], False]
    ent = held & ~prev
    lastx = held & ~nxt
    lastx[T - 1] = False      # 在窗尾的段：窗尾仍持有，不扣平倉費、不做 open 調整
    return ent, lastx


def sub(s, i0, i1):
    keys = ("open", "high", "low", "close", "rcc", "fund", "fend", "fmiss")
    t = {k: s[k][i0:i1 + 1].copy() for k in keys}
    # 第一天的 close/prevclose 要用窗前一天
    t["_prevc0"] = s["close"][i0 - 1]
    return t


def net_masked(w, held, mode="open"):
    ent, lastx = rebuild(held)
    o, c = w["open"], w["close"]
    prevc = np.r_[w["_prevc0"], c[:-1]]
    nexto = np.r_[o[1:], np.nan]
    g = np.where(ent & (mode == "open"), c / o, c / prevc)
    g = g * np.where(lastx, nexto / c, 1.0)
    net = g - 1.0 - w["fund"] - COST * ent - COST * lastx
    if mode == "close":
        prevfend = np.r_[0.0, w["fend"][:-1]]
        net = net - np.where(ent, prevfend, 0.0)
    return np.where(held, net, 0.0)


def shift_stat(units, ks, mode="open"):
    """units：[(w, held_window, wmean)]；ks：每個 unit 的平移量。回合併每天多賺（持有日等權）。"""
    tot, nd = 0.0, 0
    for (w, h, wm), k in zip(units, ks):
        hh = np.roll(h, k)
        net = net_masked(w, hh, mode)
        tot += float(net[hh].sum() - wm * hh.sum()); nd += int(hh.sum())
    return tot / nd if nd else np.nan


def perm_test(units, obs, rng, mode="open", n=NPERM):
    Ts = [len(u[1]) for u in units]
    vals = np.empty(n)
    for i in range(n):
        ks = [int(rng.integers(1, T)) for T in Ts]
        vals[i] = shift_stat(units, ks, mode)
    p = (1 + int((vals >= obs - 1e-15).sum())) / (n + 1)
    return p, vals


def rand_entry_test(units_tr, obs, rng, n=NPERM):
    """units_tr：[(w, lengths(list), open_end_flags, wmean)]；每筆進場日均勻抽、整筆落在窗內、可重疊。"""
    pre = []
    for w, Ls, oe, wm in units_tr:
        o, c = w["open"], w["close"]
        prevc = np.r_[w["_prevc0"], c[:-1]]
        rcc = c / prevc - 1.0
        base = rcc - w["fund"]
        CS = np.r_[0.0, np.cumsum(base)]
        FA = (c / o - 1.0) - rcc
        nexto = np.r_[o[1:], np.nan]
        q = nexto / c
        pre.append((len(c), CS, FA, rcc, c / o, q, np.asarray(Ls), np.asarray(oe), wm))
    vals = np.empty(n)
    for i in range(n):
        tot, nd = 0.0, 0
        for T, CS, FA, rcc, co, q, Ls, oe, wm in pre:
            if len(Ls) == 0:
                continue
            e = (rng.random(len(Ls)) * (T - Ls + 1)).astype(np.int64)
            lst = e + Ls - 1
            sm = CS[lst + 1] - CS[e] + FA[e] - COST
            closed = lst < T - 1
            la = np.where(Ls >= 2, (1 + rcc[lst]) * (q[np.minimum(lst, T - 1)] - 1), co[e] * (q[np.minimum(lst, T - 1)] - 1))
            sm = sm + np.where(closed, la - COST, 0.0)
            tot += float(sm.sum() - wm * Ls.sum()); nd += int(Ls.sum())
        vals[i] = tot / nd
    p = (1 + int((vals >= obs - 1e-15).sum())) / (n + 1)
    return p, vals


# ───────────────────────── 使用者判準、強平、計畫重疊 ─────────────────────────
def equity_stats(path_ret):
    eq = np.cumprod(1.0 + path_ret)
    eq0 = np.r_[1.0, eq]
    T = len(path_ret)
    ann = eq0[-1] ** (365.25 / T) - 1.0
    mdd = float((eq0 / np.maximum.accumulate(eq0) - 1.0).min())
    return {"年化": float(ann), "MDD": mdd, "年化÷|MDD|": float(ann / abs(mdd)) if mdd < 0 else np.nan, "期末倍數": float(eq0[-1])}


def user_criterion(s, run, i0, i1):
    st = equity_stats(run["net"][i0:i1 + 1])
    hold = equity_stats(s["rcc"][i0:i1 + 1])
    win_r = st["年化"] > hold["年化"]
    win_c = (st["年化÷|MDD|"] >= hold["年化÷|MDD|"]) if not (np.isnan(st["年化÷|MDD|"]) or np.isnan(hold["年化÷|MDD|"])) else (st["MDD"] == 0)
    lab = "合格" if (win_r and win_c) else ("另列" if win_r else "不合格")
    return {"主臂1倍": st, "抱BTC現貨": hold, "判": lab}


def liq_table(s, trades, mode="open", mark_low=None):
    rows = []
    for tr in trades:
        e, l = tr["e"], tr["last"]
        pe = s["open"][e] if mode == "open" else s["close"][tr["t"]]
        out = {"signal": s["dates"][tr["t"]], "entry": s["dates"][e], "days": l - e + 1}
        for m in MMRS:
            W = 1.0 / LEV - COST
            if mode == "close":
                W -= s["fend"][tr["t"]]
            mind, hit, hitd = np.inf, False, ""
            for d in range(e, l + 1):
                pref = pe if d == e else s["close"][d - 1]
                W -= s["fund"][d] * pref / pe
                Lp = pe * (1.0 - W) / (1.0 - m)
                lo = s["low"][d] if mark_low is None or np.isnan(mark_low[d]) else mark_low[d]
                dist = lo / Lp - 1.0
                if dist < mind:
                    mind = dist
                if lo <= Lp and not hit:
                    hit, hitd = True, s["dates"][d]
            out[f"距強平_m{m}"] = float(mind); out[f"觸及_m{m}"] = hit; out[f"觸及日_m{m}"] = hitd
        lows = s["low"][e:l + 1] if mark_low is None else np.where(np.isnan(mark_low[e:l + 1]), s["low"][e:l + 1], mark_low[e:l + 1])
        out["最大浮虧"] = float(lows.min() / pe - 1.0)
        out["5倍最大浮虧佔保證金"] = float((lows.min() / pe - 1.0) * LEV)
        rows.append(out)
    return rows


def lev_equity(s, run, i0, i1, m=0.02):
    """5 倍（全部資金當保證金）收盤權益；任一筆觸及強平 ⇒ 該筆起歸零。描述用。"""
    net = run["net"]
    eq = 1.0; path = []; dead = False
    liq = {r["entry"]: r for r in liq_table(s, [t for t in run["trades"]])}
    hitdays = set(r[f"觸及日_m{m}"] for r in liq.values() if r[f"觸及_m{m}"])
    for d in range(i0, i1 + 1):
        if dead:
            path.append(0.0); continue
        if s["dates"][d] in hitdays:
            dead = True; path.append(0.0); continue
        eq *= max(1.0 + LEV * net[d], 0.0)
        path.append(eq)
    p = np.r_[1.0, np.array(path)]
    T = i1 - i0 + 1
    ann = p[-1] ** (365.25 / T) - 1.0 if p[-1] > 0 else -1.0
    mdd = float((p / np.maximum.accumulate(p) - 1.0).min())
    return {"年化": float(ann), "MDD_收盤": mdd, "歸零": bool(dead), "期末倍數": float(p[-1])}


def plan_overlap(s, run, i0, i1):
    held = run["held"][i0:i1 + 1]
    lo, c = s["low"][i0:i1 + 1], s["close"][i0:i1 + 1]
    sma = pd.Series(s["close"]).rolling(200).mean().to_numpy()[i0:i1 + 1]
    out = {"持有日數": int(held.sum())}
    for b in BUY:
        out[f"日低≤{b:,}"] = int((held & (lo <= b)).sum())
        out[f"窗內全部日低≤{b:,}"] = int((lo <= b).sum())
    out["收盤<58,625（A1）"] = int((held & (c < A1)).sum())
    out["B3_B4重疊（2029起才生效）"] = 0
    out["收盤<200日線（B4條件本身，描述）"] = int((held & (c < sma)).sum())
    out["窗內全部日收盤<200日線"] = int((c < sma).sum())
    return out


# ───────────────────────── 主流程 ─────────────────────────
def build_units(fund_mode="BTCUSDT"):
    ev_btc = fund_src("BTCUSDT")
    btc = attach_funding(load_binance("BTC", drop30=False), ev_btc if fund_mode != "CM" else fund_src("BTCUSD_CM"))
    early = attach_funding(load_bitstamp(), None)
    coins = {}
    for c in COINS8:
        s = load_binance(c, drop30=True)
        if fund_mode == "own" and c in OWN_FUND:
            attach_funding(s, fund_src(c))
        else:
            attach_funding(s, ev_btc)
        coins[c] = s
    return btc, early, coins


def run_cell(btc, early, coins, vm, up, rule, mode="open"):
    res = {}
    for key, (a, b) in (("BTC_W1", W1), ("BTC_W2", W2)):
        i0, i1 = window_idx(btc, a, b)
        r = unit_run(btc, i0, i1, vm, up, rule, mode)
        res[key] = (btc, i0, i1, r)
    i0, i1 = window_idx(early, "2013-01-01", EARLY_END)
    res["BTC_early_bitstamp"] = (early, i0, i1, unit_run(early, i0, i1, vm, up, rule, mode))
    for c, s in coins.items():
        i0, i1 = window_idx(s, s["dates"][0], END)
        res[c] = (s, i0, i1, unit_run(s, i0, i1, vm, up, rule, mode))
    return res


def merged(res):
    tot = sum(r["hsum"] - r["wmean"] * r["hdays"] for k, (s, i0, i1, r) in res.items() if k in COINS8)
    nd = sum(r["hdays"] for k, (s, i0, i1, r) in res.items() if k in COINS8)
    eqw = np.nanmean([r["excess"] for k, (s, i0, i1, r) in res.items() if k in COINS8])
    ntr = sum(len(r["trades"]) for k, (s, i0, i1, r) in res.items() if k in COINS8)
    return {"每天多賺": tot / nd if nd else np.nan, "各幣等權": float(eqw), "持有日數": nd, "筆數": ntr}


def fmt_pct(x, d=3):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.{d}f}%"


def main_run(rule=None, tag=""):
    """tag＝""：登錄字面主格（獨立結果）。tag＝"_lowmax"：讀 §五 之後的對帳診斷（出場改「任一條破就出」），⛔ 不是判定。"""
    MAIN_EXIT_ = rule or MAIN_EXIT
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    btc, early, coins = build_units("BTCUSDT")
    vm, up = MAIN_SIG
    res = run_cell(btc, early, coins, vm, up, MAIN_EXIT_, "open")
    J = {"讀法寫死": FROZEN, "資料commit": SHA, "出場規則": f"{MAIN_EXIT_[0]}{MAIN_EXIT_[1]}",
         "資金費版本": ("v2：BTCUSDT 2019-09-10 起實際值（補檔 main " + SHA_F2019[:10] + "）" if FUND2019 else "v1：BTCUSDT 2020-01-01 起實際值"),
         "主格": {}, "對照": {}}
    # 主格摘要
    for k, (s, i0, i1, r) in res.items():
        J["主格"][k] = summary(s, r, i0, i1)
    J["主格"]["8幣合併"] = merged(res)
    # 假訊號臂、隨機進場臂
    for k in ("BTC_W1", "BTC_W2", "BTC_early_bitstamp"):
        s, i0, i1, r = res[k]
        w = sub(s, i0, i1)
        u = [(w, r["held"][i0:i1 + 1].copy(), r["wmean"])]
        p1, v1 = perm_test(u, r["excess"], rng)
        rows = trade_table(s, r["trades"], r["net"])
        ut = [(sub(s, i0, i1), [x["days"] for x in rows], [x["open_at_end"] for x in rows], r["wmean"])]
        p2, v2 = rand_entry_test(ut, r["excess"], rng)
        J["對照"][k] = {"假訊號p": p1, "假訊號中位": float(np.median(v1)), "假訊號95分位": float(np.quantile(v1, 0.95)),
                       "隨機進場p": p2, "隨機進場中位": float(np.median(v2)), "隨機進場95分位": float(np.quantile(v2, 0.95))}
    uc = [(sub(s, i0, i1), r["held"][i0:i1 + 1].copy(), r["wmean"]) for k, (s, i0, i1, r) in res.items() if k in COINS8]
    obs = J["主格"]["8幣合併"]["每天多賺"]
    p1, v1 = perm_test(uc, obs, rng)
    ut = []
    for k, (s, i0, i1, r) in res.items():
        if k in COINS8:
            rows = trade_table(s, r["trades"], r["net"])
            ut.append((sub(s, i0, i1), [x["days"] for x in rows], [x["open_at_end"] for x in rows], r["wmean"]))
    p2, v2 = rand_entry_test(ut, obs, rng)
    J["對照"]["8幣合併"] = {"假訊號p": p1, "假訊號中位": float(np.median(v1)), "假訊號95分位": float(np.quantile(v1, 0.95)),
                        "隨機進場p": p2, "隨機進場中位": float(np.median(v2)), "隨機進場95分位": float(np.quantile(v2, 0.95))}
    # 出口（不含對帳）
    four = [J["主格"]["BTC_W1"]["每天多賺"], J["主格"]["BTC_W2"]["每天多賺"], J["主格"]["BTC_early_bitstamp"]["每天多賺"], obs]
    allpos = all(x > 0 for x in four if not np.isnan(x))
    J["出口_未對帳"] = ("①候選（四項>0 且合併 p<0.05；早年格為 Bitstamp 替代版、待正式資料）" if (allpos and p1 < 0.05)
                     else "②測不出（" + ("有一項 ≤ 0" if not allpos else "") + ("；" if (not allpos and p1 >= 0.05) else "") + ("合併假訊號 p ≥ 0.05" if p1 >= 0.05 else "") + "）")
    # 使用者判準
    J["使用者判準"] = {k: user_criterion(res[k][0], res[k][3], res[k][1], res[k][2]) for k in ("BTC_W1", "BTC_W2")}
    # 強平
    mk = pd.read_csv(os.path.join(ROOT, "data", "crypto_mark", "BTCUSDT.csv"))
    mk["date"] = pd.to_datetime(mk["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    mlow = mk.drop_duplicates("date").set_index("date")["low"].astype(float).reindex(btc["dates"]).to_numpy()
    LQ = {}
    allrows = []
    for k in ("BTC_W1", "BTC_W2", "BTC_early_bitstamp") + tuple(COINS8):
        s, i0, i1, r = res[k]
        rows = liq_table(s, r["trades"])
        for x in rows:
            x["unit"] = k
        allrows += rows
        LQ[k] = {"筆數": len(rows)}
        for m in MMRS:
            LQ[k][f"觸及筆數_m{m}"] = int(sum(x[f"觸及_m{m}"] for x in rows))
            LQ[k][f"最近距強平_m{m}"] = float(min(x[f"距強平_m{m}"] for x in rows)) if rows else np.nan
        LQ[k]["最大浮虧"] = float(min(x["最大浮虧"] for x in rows)) if rows else np.nan
        if k.startswith("BTC_W"):
            rm = liq_table(s, r["trades"], mark_low=mlow)
            LQ[k]["標記價_觸及筆數_m0.02"] = int(sum(x["觸及_m0.02"] for x in rm))
            LQ[k]["標記價_最近距強平_m0.02"] = float(min(x["距強平_m0.02"] for x in rm)) if rm else np.nan
            LQ[k]["5倍全資金權益_描述"] = lev_equity(s, r, i0, i1)
    J["強平_5倍逐倉"] = LQ
    # 與現行計畫重疊
    J["計畫重疊"] = {k: plan_overlap(res[k][0], res[k][3], res[k][1], res[k][2]) for k in ("BTC_W1", "BTC_W2")}
    # 資金費缺段
    i0, i1 = window_idx(btc, *W1); j0, j1 = window_idx(btc, *W2)
    ev = fund_src("BTCUSDT")
    J["資金費"] = {"BTCUSDT首筆": pd.to_datetime(ev["h"].min(), unit="s", utc=True).strftime("%Y-%m-%d %H:%M UTC"),
                 "BTCUSDT末筆": pd.to_datetime(ev["h"].max(), unit="s", utc=True).strftime("%Y-%m-%d %H:%M UTC"),
                 "W1代入天數": int(btc["fmiss"][i0:i1 + 1].sum()), "W2代入天數": int(btc["fmiss"][j0:j1 + 1].sum()),
                 "W1持有日代入": int((btc["fmiss"] & res["BTC_W1"][3]["held"])[i0:i1 + 1].sum()),
                 "W2持有日代入": int((btc["fmiss"] & res["BTC_W2"][3]["held"])[j0:j1 + 1].sum()),
                 "覆蓋日中筆數≠3的天數": int(((btc["fcnt"] != 3) & ~btc["fmiss"]).sum()),
                 "早年全部代入": int(early["fmiss"].sum()),
                 "W1實際年化（覆蓋日）": float(btc["fund"][i0:i1 + 1][~btc["fmiss"][i0:i1 + 1]].mean() * 365.25),
                 "W2實際年化（覆蓋日）": float(btc["fund"][j0:j1 + 1][~btc["fmiss"][j0:j1 + 1]].mean() * 365.25)}
    # 敏感度：t 收盤進場、各幣自己資金費、幣本位資金費
    rc = run_cell(btc, early, coins, vm, up, MAIN_EXIT_, "close")
    J["敏感度_t收盤進場"] = {k: rc[k][3]["excess"] for k in rc}
    J["敏感度_t收盤進場"]["8幣合併"] = merged(rc)["每天多賺"]
    b2, e2, c2 = build_units("own")
    ro = run_cell(b2, e2, c2, vm, up, MAIN_EXIT_, "open")
    J["敏感度_各幣自己資金費"] = {"8幣合併": merged(ro)["每天多賺"], **{k: ro[k][3]["excess"] for k in COINS8}}
    b3, _, _ = build_units("CM")
    J["敏感度_幣本位資金費"] = {}
    for key, (a, b) in (("BTC_W1", W1), ("BTC_W2", W2)):
        i0, i1 = window_idx(b3, a, b)
        J["敏感度_幣本位資金費"][key] = unit_run(b3, i0, i1, vm, up, MAIN_EXIT_)["excess"]
    if not tag:  # 鄰格（只在字面主格跑）
        cells = []
        for (vv, uu) in SIGS:
            for rule in EXITS:
                if rule != MAIN_EXIT and (vv, uu) != MAIN_SIG:
                    continue
                rr = run_cell(btc, early, coins, vv, uu, rule, "open")
                row = {"量倍數": vv, "漲幅": uu, "出場": f"{rule[0]}{rule[1]}", "主格": (vv, uu) == MAIN_SIG and rule == MAIN_EXIT}
                for k in ("BTC_W1", "BTC_W2", "BTC_early_bitstamp"):
                    row[k] = rr[k][3]["excess"]; row[k + "_筆數"] = len(rr[k][3]["trades"])
                mg = merged(rr)
                row["8幣合併"] = mg["每天多賺"]; row["8幣合併_筆數"] = mg["筆數"]
                cells.append(row)
        pd.DataFrame(cells).to_csv(os.path.join(OUT, "neighbors.csv"), index=False, encoding="utf-8-sig")
        J["鄰格"] = cells
    # 交易清單（公開資料：BTC 兩窗；8 幣只放彙總以外的逐筆亦為公開 Binance，可放；早年 Bitstamp 私有 ⇒ 只放彙總）
    tl = []
    for k in ("BTC_W1", "BTC_W2") + tuple(COINS8):
        s, i0, i1, r = res[k]
        for x in trade_table(s, r["trades"], r["net"]):
            x["unit"] = k; tl.append(x)
    pd.DataFrame(tl).to_csv(os.path.join(OUT, f"trades_public{tag}.csv"), index=False, encoding="utf-8-sig")
    lq = pd.DataFrame([x for x in allrows if x["unit"] != "BTC_early_bitstamp"])
    lq.to_csv(os.path.join(OUT, f"liquidation_5x{tag}.csv"), index=False, encoding="utf-8-sig")
    # 現況（描述）：BTC 最後一個訊號與 10-09 收盤時是否仍持有
    s, i0, i1, r = res["BTC_W2"]
    last = r["trades"][-1] if r["trades"] else None
    J["窗尾狀態_W2"] = {"最後一筆訊號日": s["dates"][last["t"]] if last else "", "10-09收盤仍持有": bool(last and last["x"] is None)}
    return J, res


def recon(stamp):
    """讀登錄 §五 之後才寫（2026-10-11 00:48 台北讀 §五）：找差異原因的診斷，⛔ 不改判定、不改主格。"""
    global COST
    rng = np.random.default_rng(SEED + 5)
    btc, early, coins = build_units("BTCUSDT")
    vm, up = MAIN_SIG
    out = {"讀§五時間": "2026-10-11 00:48（台北）", "寫檔時間": stamp, "變體": []}
    # 訊號天數（不管持倉）
    sigb = signals(btc, vm, up)
    for key, (a, b) in (("BTC_W1", W1), ("BTC_W2", W2)):
        i0, i1 = window_idx(btc, a, b)
        out[f"{key}_訊號天數"] = int(sigb[i0:i1 + 1].sum())
        out[f"{key}_訊號日"] = list(btc["dates"][i0:i1 + 1][sigb[i0:i1 + 1]])
    for c, s in coins.items():
        i0, i1 = window_idx(s, s["dates"][0], END)
        out[f"{c}_訊號天數"] = int(signals(s, vm, up)[i0:i1 + 1].sum())
    for rule in (("low", 10), ("lowmax", 10), ("lowonly", 10), ("sigonly", 0)):
        for mode in ("open", "close"):
            for gross in (False, True):
                if gross:
                    COST = 0.0
                    bz = dict(btc); bz["fund"] = np.zeros_like(btc["fund"]); bz["fend"] = np.zeros_like(btc["fend"])
                    cz = {k: {**v, "fund": np.zeros_like(v["fund"]), "fend": np.zeros_like(v["fend"])} for k, v in coins.items()}
                    ez = {**early, "fund": np.zeros_like(early["fund"]), "fend": np.zeros_like(early["fend"])}
                else:
                    COST = 0.001; bz, cz, ez = btc, coins, early
                rr = run_cell(bz, ez, cz, vm, up, rule, mode)
                row = {"出場": f"{rule[0]}{rule[1]}", "進場": mode, "毛（不扣成本與資金費）": gross}
                for k in ("BTC_W1", "BTC_W2", "BTC_early_bitstamp") + tuple(COINS8):
                    s, i0, i1, r = rr[k]
                    rows = trade_table(s, r["trades"], r["net"], mode)
                    row[k] = r["excess"]; row[k + "_筆數"] = len(rows)
                    row[k + "_中位持有"] = float(np.median([x["days"] for x in rows])) if rows else None
                row["8幣合併"] = merged(rr)["每天多賺"]
                if (not gross) and rule[0] in ("low", "lowmax"):
                    for k in ("BTC_W1", "BTC_W2"):
                        s, i0, i1, r = rr[k]
                        p, _ = perm_test([(sub(s, i0, i1), r["held"][i0:i1 + 1].copy(), r["wmean"])], r["excess"], rng, mode)
                        row[k + "_假訊號p"] = p
                out["變體"].append(row)
    COST = 0.001
    # 早年：訊號後 14 天報酬 − 全部日 14 天報酬（事件描述，對 §五「+12.0%」）
    s = early; i0, i1 = window_idx(s, "2013-01-01", EARLY_END)
    sg = signals(s, vm, up)
    c = s["close"]
    f14 = np.r_[c[14:] / c[:-14] - 1.0, np.full(14, np.nan)]
    idx = [t for t in range(i0, i1 - 13) if sg[t]]
    out["早年_訊號後14天_減_全部日"] = float(np.nanmean(f14[idx]) - np.nanmean(f14[i0:i1 - 13])) if idx else None
    out["早年_訊號天數"] = len(idx)
    out["早年_持倉中也算的訊號天數"] = int(sg[i0:i1 + 1].sum())
    return out


def write_forward_template():
    # 出場讀法在對帳（出口 ③）未定 ⇒ 兩種讀法的出場都記，裁定後只取一欄判
    cols = ["序號", "訊號日(UTC)", "訊號日量倍數", "訊號日漲幅", "訊號日最低價", "進場日(UTC)", "進場價(次日開盤)",
            "出場觸發日_登錄字面min(UTC)", "出場日_登錄字面min(UTC)", "出場價_登錄字面min(次日開盤)",
            "出場觸發日_任一條破max(UTC)", "出場日_任一條破max(UTC)", "出場價_任一條破max(次日開盤)",
            "持有天數", "持有期間淨報酬", "同期間全部日平均", "每天多賺", "期間最大浮虧", "5倍逐倉距強平最近", "持倉中再出訊號日(不加碼不重設)",
            "是否實際交易", "記錄時間(台北)", "備註"]
    pd.DataFrame(columns=cols).to_csv(os.path.join(OUT, "forward_template.csv"), index=False, encoding="utf-8-sig")


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float):
        return None if math.isnan(o) else o
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--stamp", default="")
    ap.add_argument("--recon", action="store_true")
    ap.add_argument("--diag-lowmax", action="store_true")
    ap.add_argument("--fund2019", action="store_true")
    a = ap.parse_args()
    FUND2019 = bool(a.fund2019)
    V = "_v2" if FUND2019 else ""
    if a.diag_lowmax:
        J, _ = main_run(("lowmax", 10), "_lowmax")
        J["性質"] = "⛔ 對帳診斷（讀登錄 §五 之後才跑）：出場改讀成「收盤破訊號日低或破前 10 日低任一條就出」＝max；不是判定、不是獨立結果"
        J["寫檔時間"] = a.stamp
        with open(os.path.join(OUT, f"diag_lowmax{V}.json"), "w", encoding="utf-8") as f:
            json.dump(to_jsonable(J), f, ensure_ascii=False, indent=1)
        print("diag OK")
    elif a.recon:
        Rj = recon(a.stamp)
        with open(os.path.join(OUT, f"reconcile{V}.json"), "w", encoding="utf-8") as f:
            json.dump(to_jsonable(Rj), f, ensure_ascii=False, indent=1)
        print("recon OK")
    elif a.check:
        import researchC17_check as CK
        CK.R.FUND2019 = FUND2019
        CK.main()
    else:
        J, _ = main_run()
        write_forward_template()
        J["寫檔時間"] = a.stamp
        with open(os.path.join(OUT, f"independent{V}.json"), "w", encoding="utf-8") as f:
            json.dump(to_jsonable(J), f, ensure_ascii=False, indent=1)
        print("OK", a.stamp)

# -*- coding: utf-8 -*-
"""交易紀錄檢驗：一份逐筆交易表，回答「這是有優勢，還是運氣、還是賭博」。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python -m backtest.tradecheck 交易.csv [--frac 0.05] [--html 輸出.html] [--json 輸出.json]
    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python -m backtest.tradecheck --check        # 合成資料自我查核

做法參考開源專案 mars-tw/anti-gambling-trader-tw（MIT，「反詐投資王」）docs/methodology.md 的關卡設計
（期望值 → t 檢定＋置中 bootstrap → 樣本外 → 賭博特徵 → 五級裁決），程式為本專案自寫，只用 numpy／pandas／標準庫。
與原專案不同處（本專案自己加的，只會讓裁決更嚴）：
  ① 分月重抽：同月出場的交易互相相關，逐筆獨立的檢定會高估顯著；分月重抽不顯著 ⇒ 不給「統計優勢」，降為「脆弱優勢」
  ② 樣本外：兩段都檢定得出來、而後段沒延續 ⇒ 不給「統計優勢」，降為「脆弱優勢」（原專案把樣本外另外報、不進裁決）
  ③ 可選「基準報酬」欄 ⇒ 另報「超額 ＝ 報酬 − 基準」的同一套檢驗（回答「贏不贏同期隨便買」，而不只是「賺不賺」）
  ④ 「照規則／實際」兩欄對照（前瞻紀錄用）：配對差的平均與是不是運氣

⚠ p 值的意思：「假如其實沒有優勢（真實期望值 ＝ 0），光靠抽樣波動，出現這麼好或更好成績的機率」。
   ⛔ 它不是「有優勢的機率」，1 − p 也不是「信心度」。

輸入欄位（中英文別名皆可；只有一列表頭；# 開頭的列當註解）：
  代號 / 進場日 / 進場價 / 出場日 / 出場價 / 股數 或 權重 / 成本 / 標籤 / 報酬 / 持有天數 / 基準報酬
  報酬 ＝ 已扣成本的淨報酬率（小數，或寫成 12.3%）；有這欄就直接用，否則由 出場價 ÷ 進場價 − 1 − 成本 算
  成本 ＝ 來回成本比率（小數，≤ 0.2）；大於 0.2 當成金額（元），除以 股數 × 進場價；沒有這欄用 --cost（預設 0.585%）
  出場價、報酬都沒有 ⇒ 未平倉：另列，不進任何統計
  兩欄對照：同時有「照規則報酬」與「實際報酬」欄（或「規則出場價」與「實際出場價」，進場價可分「規則進場價」「實際進場價」）
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import sys

import numpy as np
import pandas as pd

COST = 0.00585          # 台股來回成本（同回測引擎）
ALPHA = 0.05
MIN_TRADES = 30         # 低於此筆數 ⇒ 樣本不足（原專案同值）
MIN_SEG = 10            # 樣本外每段至少筆數
SEED = 20261002
SKEW_LEFT = -1.0        # 報酬偏態 < −1 ⇒ 左偏警訊（高），檢定偏寬鬆，最多給脆弱優勢

LEVELS = {
    "neg": ("負期望", "#c0392b"),
    "insufficient": ("樣本不足", "#d68910"),
    "luck": ("像運氣", "#b7950b"),
    "fragile": ("脆弱優勢", "#b7950b"),
    "edge": ("統計優勢（仍不是保證）", "#1e8449"),
}

ALIASES = {
    "sid": ["代號", "股票代號", "sid", "symbol", "ticker", "code"],
    "entry_date": ["進場日", "買進日", "entry_date", "entry", "open_date"],
    "entry_price": ["進場價", "買進價", "entry_price", "open_price"],
    "exit_date": ["出場日", "賣出日", "exit_date", "exit", "close_date"],
    "exit_price": ["出場價", "賣出價", "exit_price", "close_price"],
    "qty": ["股數", "數量", "qty", "shares", "quantity"],
    "weight": ["權重", "金額", "weight", "notional"],
    "cost": ["成本", "cost", "fee"],
    "tag": ["標籤", "策略", "來源", "tag", "strategy"],
    "ret": ["報酬", "淨報酬", "淨報酬率", "報酬率", "ret", "return", "net_return"],
    "days": ["持有天數", "天數", "days", "hold_days"],
    "bench": ["基準報酬", "基準", "bench", "benchmark"],
    "rule_ret": ["照規則報酬", "規則報酬", "rule_ret"],
    "act_ret": ["實際報酬", "act_ret", "actual_ret"],
    "rule_entry_price": ["規則進場價", "rule_entry_price"],
    "rule_exit_price": ["規則出場價", "rule_exit_price"],
    "act_entry_price": ["實際進場價", "act_entry_price"],
    "act_exit_price": ["實際出場價", "act_exit_price"],
}


# ════════════════════════ 讀檔 ════════════════════════
def _num(s):
    """數字欄：空白 ⇒ NaN；'12.3%' ⇒ 0.123；千分位逗號去掉。"""
    def one(v):
        if v is None:
            return np.nan
        t = str(v).strip().replace(",", "")
        if t == "" or t.lower() in ("nan", "none"):
            return np.nan
        pct = t.endswith("%")
        try:
            x = float(t.rstrip("%"))
        except ValueError:
            return np.nan
        return x / 100 if pct else x
    return pd.Series([one(v) for v in s], index=s.index, dtype=float)


def _date(s):
    return pd.to_datetime(s.astype(str).str.strip().replace({"": None, "nan": None, "None": None}), errors="coerce")


def normalize(raw: pd.DataFrame, cost: float = COST):
    """任意欄名的交易表 ⇒ (已平倉 df, 未平倉 df, 註記 list)。已平倉 df 一定有 ret、pnl；沒有的欄留 NaN。"""
    notes = []
    raw = raw.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    col = {}
    for k, names in ALIASES.items():
        for n in names:
            hit = [c for c in raw.columns if c.lower() == n.lower()]
            if hit:
                col[k] = hit[0]
                break
    n = len(raw)
    df = pd.DataFrame(index=range(n))
    df["row"] = np.arange(1, n + 1)
    df["sid"] = raw[col["sid"]].astype(str).str.strip().to_numpy() if "sid" in col else ""
    df["tag"] = (raw[col["tag"]].astype(str).str.strip().replace({"nan": ""}).to_numpy() if "tag" in col else "")
    df["tag"] = df["tag"].replace({"": "（無標籤）"})
    for k in ("entry_date", "exit_date"):
        df[k] = _date(raw[col[k]]).to_numpy() if k in col else pd.NaT
    for k in ("entry_price", "exit_price", "qty", "weight", "cost", "ret", "days", "bench",
              "rule_ret", "act_ret", "rule_entry_price", "rule_exit_price", "act_entry_price", "act_exit_price"):
        df[k] = _num(raw[col[k]]).to_numpy() if k in col else np.nan

    # 成本：比率或金額
    cf = df["cost"].to_numpy(float).copy()
    notional_px = df["qty"].to_numpy(float) * df["entry_price"].to_numpy(float)
    big = np.isfinite(cf) & (cf > 0.2)
    if big.any():
        cf[big] = cf[big] / notional_px[big]
        notes.append(f"成本欄有 {int(big.sum())} 列大於 0.2，當成金額（元）÷ 股數 × 進場價")
    cf = np.where(np.isfinite(cf), cf, cost)

    # 兩欄對照：價格 ⇒ 報酬
    for side in ("rule", "act"):
        r = df[f"{side}_ret"].to_numpy(float).copy()
        ep = df[f"{side}_entry_price"].to_numpy(float)
        ep = np.where(np.isfinite(ep), ep, df["entry_price"].to_numpy(float))
        xp = df[f"{side}_exit_price"].to_numpy(float)
        calc = ~np.isfinite(r) & np.isfinite(xp) & np.isfinite(ep) & (ep > 0)
        r[calc] = xp[calc] / ep[calc] - 1 - cf[calc]
        df[f"{side}_ret"] = r
    paired = bool(np.isfinite(df["rule_ret"]).any() and np.isfinite(df["act_ret"]).any())

    # 主欄報酬：報酬欄 > 出場價 > （兩欄對照時）實際報酬
    ret = df["ret"].to_numpy(float).copy()
    ep, xp = df["entry_price"].to_numpy(float), df["exit_price"].to_numpy(float)
    calc = ~np.isfinite(ret) & np.isfinite(xp) & np.isfinite(ep) & (ep > 0)
    ret[calc] = xp[calc] / ep[calc] - 1 - cf[calc]
    if calc.any() and "cost" not in col:
        notes.append(f"{int(calc.sum())} 筆由價格算報酬；沒有成本欄，扣來回成本 {cost:.3%}")
    if paired:
        fill = ~np.isfinite(ret) & np.isfinite(df["act_ret"].to_numpy(float))
        ret[fill] = df["act_ret"].to_numpy(float)[fill]
        fill = ~np.isfinite(ret) & np.isfinite(df["rule_ret"].to_numpy(float))
        ret[fill] = df["rule_ret"].to_numpy(float)[fill]
    df["ret"] = ret

    # 部位大小 ⇒ 金額損益（只用在獲利因子、單筆貢獻；檢定一律用每筆報酬率）
    w = df["weight"].to_numpy(float)
    notional = np.where(np.isfinite(w), w, notional_px)
    df["sized"] = np.isfinite(notional) & (notional > 0)
    df["notional"] = np.where(df["sized"], notional, 1.0)
    df["pnl"] = df["ret"] * df["notional"]

    # 持有天數：欄位優先；否則以週一～五估（未扣國定假日）
    d = df["days"].to_numpy(float).copy()
    ok = ~np.isfinite(d) & df["entry_date"].notna().to_numpy() & df["exit_date"].notna().to_numpy()
    if ok.any():
        a = df.loc[ok, "entry_date"].to_numpy("datetime64[D]")
        b = df.loc[ok, "exit_date"].to_numpy("datetime64[D]")
        d[ok] = np.busday_count(a, b) + 1
        notes.append("持有天數由進出場日估（週一～五，未扣國定假日，含進場當天）")
    df["days"] = d

    closed_mask = np.isfinite(df["ret"].to_numpy(float))
    closed = df[closed_mask].copy()
    openp = df[~closed_mask].copy()
    if paired:
        notes.append("有「照規則／實際」兩欄：主檢驗用實際（缺實際用規則），另報兩欄配對差")
    return closed, openp, notes, paired


def load_csv(path, cost=COST):
    """# 開頭的列當註解。第一個非註解列若不是欄名、而註解裡有「欄位：a,b,c」⇒ 用註解裡的欄名（共用持股檔就是這種寫法）。"""
    import csv
    import io
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    known = {n.lower() for v in ALIASES.values() for n in v}
    hdr_comment = None
    for ln in lines:
        s = ln.strip()
        if s.startswith("#"):
            for sep in ("欄位：", "欄位:"):
                if sep in s:
                    hdr_comment = [x.strip() for x in s.split(sep, 1)[1].split(",")]
    data = [ln for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not data:
        return normalize(pd.DataFrame(columns=hdr_comment or ["代號"]), cost)
    first = next(csv.reader([data[0]]))
    if not any(c.strip().lower() in known for c in first) and hdr_comment:
        data = [",".join(hdr_comment)] + data
    raw = pd.read_csv(io.StringIO("\n".join(data)), dtype=str, keep_default_na=False)
    return normalize(raw, cost)


# ════════════════════════ 統計 ════════════════════════
def _betacf(a, b, x):
    """正則化不完全 beta 的連分式（Lentz 法）。"""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-14:
            break
    return h


def _ibeta(x, a, b):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lb) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lb) * _betacf(b, a, 1 - x) / b


def t_sf(t, df):
    """Student-t 上尾機率 P(T ≥ t)。"""
    if not math.isfinite(t):
        return 0.0 if t > 0 else 1.0
    tail = 0.5 * _ibeta(df / (df + t * t), df / 2.0, 0.5)
    return tail if t > 0 else 1.0 - tail


def _boot_means(x, B, rng, chunk=2000):
    n = len(x)
    out = np.empty(B)
    for i in range(0, B, chunk):
        k = min(chunk, B - i)
        out[i:i + k] = x[rng.integers(0, n, size=(k, n))].mean(axis=1)
    return out


def sig_test(x, B=10000, seed=SEED, alpha=ALPHA):
    """H0：真實平均 ≤ 0。t 檢定（單尾）＋置中 bootstrap（shift method，單尾）；兩者都 < alpha 且平均 > 0 ⇒ 顯著。
    CI ＝ 原樣本重抽平均的 2.5%／97.5% 分位（雙尾，描述用）。"""
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return {"n": n, "mean": float(x.mean()) if n else float("nan"), "p_t": float("nan"), "p_boot": float("nan"),
                "ci_lo": float("nan"), "ci_hi": float("nan"), "significant": False}
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    if sd == 0:
        p_t = 0.0 if mu > 0 else 1.0
    else:
        p_t = t_sf(mu / (sd / math.sqrt(n)), n - 1)
    rng = np.random.default_rng(seed)
    bm = _boot_means(x - mu, B, rng)          # 置中：模擬「真實期望 ＝ 0」的世界
    p_boot = (int((bm >= mu).sum()) + 1) / (B + 1)
    raw = bm + mu                              # 同一批重抽的原樣本平均
    ci_lo, ci_hi = (float(v) for v in np.quantile(raw, [alpha / 2, 1 - alpha / 2]))
    return {"n": n, "mean": mu, "sd": sd, "p_t": float(p_t), "p_boot": float(p_boot), "ci_lo": ci_lo, "ci_hi": ci_hi,
            "significant": bool(p_t < alpha and p_boot < alpha and mu > 0)}


def month_cluster_test(x, months, B=5000, seed=SEED, alpha=ALPHA):
    """分月重抽（cluster bootstrap，置中）：整個月一起抽，承認同月交易互相相關。月數 < 12 ⇒ 不算。"""
    x = np.asarray(x, float)
    months = np.asarray(months)
    keys, inv = np.unique(months, return_inverse=True)
    G = len(keys)
    if G < 12:
        return {"months": G, "p": float("nan"), "significant": None}
    mu = float(x.mean())
    y = x - mu
    s = np.bincount(inv, weights=y, minlength=G)
    c = np.bincount(inv, minlength=G).astype(float)
    rng = np.random.default_rng(seed + 1)
    hit = 0
    for i in range(0, B, 1000):
        k = min(1000, B - i)
        idx = rng.integers(0, G, size=(k, G))
        m = s[idx].sum(1) / c[idx].sum(1)
        hit += int((m >= mu).sum())
    p = (hit + 1) / (B + 1)
    return {"months": G, "p": float(p), "significant": bool(p < alpha and mu > 0)}


def streak_prob(n, k, q):
    """n 筆、每筆虧損機率 q（獨立）時，出現 ≥ k 連虧的機率（精確 DP）。"""
    if k <= 0:
        return 1.0
    if n < k or q <= 0:
        return 0.0
    st = np.zeros(k)       # st[j] ＝ 目前連虧 j 筆、尚未達 k 的機率
    st[0] = 1.0
    hit = 0.0
    for _ in range(n):
        new = np.zeros(k)
        new[0] = st.sum() * (1 - q)
        new[1:] = st[:-1] * q
        hit += st[-1] * q
        st = new
    return float(hit)


def skewness(x):
    """樣本偏態（Fisher-Pearson，未校正）；筆數 < 3 或零變異 ⇒ 0。"""
    x = np.asarray(x, float)
    if len(x) < 3:
        return 0.0
    d = x - x.mean()
    s2 = (d ** 2).mean()
    return float((d ** 3).mean() / s2 ** 1.5) if s2 > 0 else 0.0


def max_streak(neg):
    best = cur = 0
    for v in neg:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def max_dd(eq):
    eq = np.concatenate([[1.0], np.asarray(eq, float)])
    peak = np.maximum.accumulate(eq)
    return float((1 - eq / peak).max())


# ════════════════════════ 各關 ════════════════════════
def order_closed(df):
    """依出場日排序（同日依進場日、再依原列）；缺出場日 ⇒ 回傳 None（不拿檔案列順序冒充時間）。"""
    if df["exit_date"].isna().any():
        return None
    return df.sort_values(["exit_date", "entry_date", "row"], kind="mergesort").reset_index(drop=True)


def metrics(df, frac):
    r = df["ret"].to_numpy(float)
    pnl = df["pnl"].to_numpy(float)
    n = len(r)
    win, loss = r > 0, r < 0
    m = {"n": n, "wins": int(win.sum()), "losses": int(loss.sum()), "flat": int((r == 0).sum())}
    m["win_rate"] = m["wins"] / n if n else float("nan")
    m["avg_win"] = float(r[win].mean()) if win.any() else 0.0
    m["avg_loss"] = float(-r[loss].mean()) if loss.any() else 0.0
    m["payoff"] = m["avg_win"] / m["avg_loss"] if m["avg_loss"] > 0 else float("inf")
    m["expectancy"] = float(r.mean()) if n else float("nan")
    m["skew"] = skewness(r)
    m["median"] = float(np.median(r)) if n else float("nan")
    gp, gl = float(pnl[pnl > 0].sum()), float(-pnl[pnl < 0].sum())
    m["profit_factor"] = gp / gl if gl > 0 else float("inf")
    tot = float(pnl.sum())
    m["total_pnl"] = tot
    m["sized"] = bool(df["sized"].all()) if n else False
    if n and gp > 0:
        top = float(pnl.max())
        m["top_share"] = top / tot if tot > 0 else top / gp
        m["top_share_base"] = "淨利" if tot > 0 else "總獲利"
        i = int(np.argmax(pnl))
        m["top_trade"] = f"{df['sid'].iloc[i]} {_d(df['entry_date'].iloc[i])}（{r[i]:+.1%}）"
        m["mean_wo_top"] = float(np.delete(r, i).mean()) if n > 1 else float("nan")
    else:
        m["top_share"] = float("nan"); m["top_share_base"] = ""; m["top_trade"] = ""; m["mean_wo_top"] = float("nan")
    d = df["days"].to_numpy(float)
    m["days_mean"] = float(np.nanmean(d)) if np.isfinite(d).any() else float("nan")
    m["days_median"] = float(np.nanmedian(d)) if np.isfinite(d).any() else float("nan")
    od = order_closed(df)
    if od is not None and n:
        ro = od["ret"].to_numpy(float)
        m["seq_ok"] = True
        m["max_streak"] = max_streak(ro < 0)
        m["max_dd_seq"] = max_dd(np.cumprod(1 + frac * ro))
        m["first_exit"], m["last_exit"] = _d(od["exit_date"].iloc[0]), _d(od["exit_date"].iloc[-1])
    else:
        m["seq_ok"] = False
        m["max_streak"] = None; m["max_dd_seq"] = float("nan"); m["first_exit"] = m["last_exit"] = ""
    return m


def oos_test(df, B=5000, seed=SEED, split_ratio=0.7):
    """依出場時間單一切點：前段約 70%、兩段各 ≥ 10 筆、同一出場日不拆。"""
    od = order_closed(df)
    if od is None:
        return {"status": "無法驗證", "why": "有交易缺出場日，不拿檔案列順序冒充時間"}
    n = len(od)
    if n < 2 * MIN_SEG:
        return {"status": "無法驗證", "why": f"已平倉只有 {n} 筆，切兩段湊不到各 {MIN_SEG} 筆"}
    xd = od["exit_date"].to_numpy()
    target = min(max(MIN_SEG, int(n * split_ratio)), n - MIN_SEG)
    valid = [i for i in range(MIN_SEG, n - MIN_SEG + 1) if xd[i - 1] != xd[i]]
    if not valid:
        return {"status": "無法驗證", "why": "同一出場日的交易太集中，找不到不拆開同日、兩段各 ≥ 10 筆的切點"}
    sp = min(valid, key=lambda i: (abs(i - target), i))
    a, b = od["ret"].to_numpy(float)[:sp], od["ret"].to_numpy(float)[sp:]
    sa, sb = sig_test(a, B, seed), sig_test(b, B, seed + 7)
    decay = 1 - sb["mean"] / sa["mean"] if sa["mean"] > 0 else float("nan")
    ok = sa["significant"] and sb["significant"] and np.isfinite(decay) and decay < 0.5
    if ok:
        status, why = "延續", "前後兩段都顯著為正，後段衰減 < 50%"
    else:
        rs = []
        if not sa["significant"]:
            rs.append("前段沒有顯著正期望")
        if not sb["significant"]:
            rs.append("後段沒有顯著正期望" if sb["mean"] > 0 else "後段期望值 ≤ 0")
        if np.isfinite(decay) and decay >= 0.5:
            rs.append(f"後段比前段衰減 {decay:.0%}（≥ 50%）")
        status, why = "未延續", "；".join(rs)
    return {"status": status, "why": why, "split_date": _d(od["exit_date"].iloc[sp]), "n_in": len(a), "n_out": len(b),
            "in": sa, "out": sb, "decay": decay, "in_range": (_d(od["exit_date"].iloc[0]), _d(od["exit_date"].iloc[sp - 1])),
            "out_range": (_d(od["exit_date"].iloc[sp]), _d(od["exit_date"].iloc[-1]))}


def red_flags(m, sig, frac):
    f = []
    if m["expectancy"] < 0:
        f.append(("high", "負期望", f"每筆平均淨報酬 {m['expectancy']:+.2%}：方法不變，做越多賠越多"))
    if np.isfinite(m["top_share"]) and m["top_share"] > 0.5 and m["wins"] >= 1:
        f.append(("high", "單筆暴賺撐場", f"最賺的一筆 {m['top_trade']} 占{m['top_share_base']} {m['top_share']:.0%}"))
    if m["win_rate"] > 0.7 and m["payoff"] < 0.4 and m["losses"] > 0:
        f.append(("high", "賺小賠大", f"勝率 {m['win_rate']:.0%} 但盈虧比只有 {m['payoff']:.2f}：一次大賠吃掉很多次小賺"))
    if m["expectancy"] > 0 and m["wins"] > 0 and m["losses"] > 0:
        be = (m["losses"] / m["n"]) / m["win_rate"]
        margin = m["payoff"] - be
        if 0 < margin < 0.25 * be:
            f.append(("medium", "安全邊際薄", f"盈虧比 {m['payoff']:.2f} 只比打平門檻 {be:.2f} 高一點，勝率或成本稍差就翻負"))
    if m["seq_ok"] and m["max_dd_seq"] > 0.5:
        f.append(("high", "極端回撤", f"每筆投入 {frac:.0%} 資金、依出場順序複利時，最大回落 {m['max_dd_seq']:.0%}"))
    if m["seq_ok"] and m["max_streak"] is not None and m["max_streak"] >= 8:
        q = m["losses"] / m["n"]
        p = streak_prob(m["n"], m["max_streak"], q)
        f.append(("medium", "長連虧", f"曾連虧 {m['max_streak']} 筆（以這個虧損率、{m['n']} 筆裡出現這麼長連虧的機率約 {p:.0%}；"
                                    "機率高代表它是筆數多的自然結果，但實際要撐得過）"))
    if m["n"] >= MIN_TRADES and m["skew"] < SKEW_LEFT:
        f.append(("high", "左偏（常小賺、偶爾大賠）", f"報酬偏態 {m['skew']:.1f}：這種分布下 t 檢定與 bootstrap 都偏寬鬆（合成查核：均值 0 時誤判約一成多），"
                                             "顯著也不給統計優勢"))
    if 0 < m["profit_factor"] < 1.1 and m["n"] >= 20:
        f.append(("low", "獲利因子接近 1", f"獲利因子 {m['profit_factor']:.2f}：沒有安全邊際，成本稍高就虧"))
    return f


def breakeven(m):
    """固定平均賺／平均賠，勝率要多少；固定勝率，盈虧比要多少。期望值已正 ⇒ 改報「可以退到多少還不虧」。"""
    n = m["n"]
    if not n or m["avg_win"] <= 0 or m["avg_loss"] <= 0:
        return {"ok": False}
    active = (m["wins"] + m["losses"]) / n
    req_wr = active * m["avg_loss"] / (m["avg_win"] + m["avg_loss"])
    req_payoff = (m["losses"] / n) / m["win_rate"] if m["win_rate"] > 0 else float("inf")
    return {"ok": True, "positive": m["expectancy"] > 0, "req_wr": req_wr, "req_payoff": req_payoff,
            "wr": m["win_rate"], "payoff": m["payoff"], "cost_room": m["expectancy"]}


def per_tag(df):
    tags = list(dict.fromkeys(df["tag"]))
    if len(tags) < 2:
        return None
    allr = df["ret"].to_numpy(float)
    tot = float(df["pnl"].sum())
    rows = []
    for t in tags:
        s = df[df["tag"] == t]
        r = s["ret"].to_numpy(float)
        rest = df[df["tag"] != t]
        rr = rest["ret"].to_numpy(float)
        rp = rest["pnl"].to_numpy(float)
        gl = -rp[rp < 0].sum()
        rows.append({"tag": t, "n": len(r), "win_rate": float((r > 0).mean()), "mean": float(r.mean()), "median": float(np.median(r)),
                     "pnl": float(s["pnl"].sum()), "share": float(s["pnl"].sum()) / tot if tot != 0 else float("nan"),
                     "enough": len(r) >= MIN_TRADES,
                     "cf_n": len(rr), "cf_mean": float(rr.mean()) if len(rr) else float("nan"),
                     "cf_pf": float(rp[rp > 0].sum() / gl) if gl > 0 else float("inf"), "cf_pnl": float(rp.sum())})
    return {"rows": rows, "all_mean": float(allr.mean()), "all_pnl": tot}


def risk_sim(r, n_future, frac, loss_x, paths=5000, seed=SEED):
    """用自己的報酬分布有放回重抽 N 筆、每筆投入 frac 資金依序複利：回落分佈、虧損超過 X% 的比例。情境，不是預測。"""
    r = np.asarray(r, float)
    rng = np.random.default_rng(seed + 2)
    dd = np.empty(paths); fin = np.empty(paths)
    for i in range(0, paths, 1000):
        k = min(1000, paths - i)
        eq = np.cumprod(1 + frac * r[rng.integers(0, len(r), size=(k, n_future))], axis=1)
        eq = np.concatenate([np.ones((k, 1)), eq], axis=1)
        dd[i:i + k] = (1 - eq / np.maximum.accumulate(eq, axis=1)).max(1)
        fin[i:i + k] = eq[:, -1]
    return {"n_future": n_future, "frac": frac, "loss_x": loss_x, "paths": paths,
            "dd_med": float(np.median(dd)), "dd_p90": float(np.quantile(dd, 0.9)), "dd_p95": float(np.quantile(dd, 0.95)),
            "p_dd_gt_x": float((dd > loss_x).mean()), "p_final_loss": float((fin < 1).mean()),
            "p_final_loss_gt_x": float((fin < 1 - loss_x).mean()), "final_med": float(np.median(fin) - 1)}


def paired_test(df, B=10000, seed=SEED, alpha=ALPHA):
    """照規則 vs 實際：配對差 d ＝ 實際 − 規則。雙尾 t ＋ 置中 bootstrap 雙尾；兩者都 < alpha ⇒ 差距不像運氣。"""
    a = df["rule_ret"].to_numpy(float); b = df["act_ret"].to_numpy(float)
    ok = np.isfinite(a) & np.isfinite(b)
    d = b[ok] - a[ok]
    n = len(d)
    out = {"n": n, "rule_mean": float(a[ok].mean()) if n else float("nan"), "act_mean": float(b[ok].mean()) if n else float("nan")}
    if n < 2:
        out.update(mean=float(d.mean()) if n else float("nan"), significant=False, p_t=float("nan"), p_boot=float("nan"))
        return out
    mu, sd = float(d.mean()), float(d.std(ddof=1))
    if sd == 0:
        p_t = 0.0 if mu != 0 else 1.0
    else:
        p_t = min(1.0, 2 * t_sf(abs(mu) / (sd / math.sqrt(n)), n - 1))
    rng = np.random.default_rng(seed + 3)
    bm = _boot_means(d - mu, B, rng)
    p_boot = (int((np.abs(bm) >= abs(mu)).sum()) + 1) / (B + 1)
    lo, hi = (float(v) for v in np.quantile(bm + mu, [alpha / 2, 1 - alpha / 2]))
    out.update(mean=mu, median=float(np.median(d)), better=float((d > 1e-12).mean()), worse=float((d < -1e-12).mean()),
               p_t=float(p_t), p_boot=float(p_boot), ci_lo=lo, ci_hi=hi, significant=bool(p_t < alpha and p_boot < alpha),
               sum_diff=float(d.sum()))
    return out


def judge(m, sig, mc, oos, flags):
    """五級裁決（由壞到好依序判）。"""
    reasons = []
    if m["n"] < MIN_TRADES:
        lvl = "insufficient"
        reasons.append(f"已平倉只有 {m['n']} 筆（< {MIN_TRADES}），再好再壞都分不出是方法還是運氣")
    elif m["expectancy"] < 0:
        lvl = "neg"
        reasons.append(f"每筆平均淨報酬 {m['expectancy']:+.2%} < 0")
        if sig["ci_hi"] > 0:
            reasons.append(f"註：平均的 95% 區間 [{sig['ci_lo']:+.2%}, {sig['ci_hi']:+.2%}] 上緣仍 > 0；判負期望是保守原則（負的就先停），不是已證明必輸")
    elif not sig["significant"]:
        lvl = "luck"
        reasons.append(f"t 檢定 p＝{sig['p_t']:.3f}、bootstrap p＝{sig['p_boot']:.3f}，沒有兩個都 < 0.05：和「其實沒有優勢、只是抽樣波動」分不開")
    else:
        why = [x for x in flags if x[0] == "high" or x[1] == "安全邊際薄"]
        down = [f"{x[1]}" for x in why]
        if mc.get("significant") is False:
            down.append(f"分月重抽 p＝{mc['p']:.3f} 不顯著（同月交易互相相關，逐筆檢定高估了）")
        if oos.get("status") == "未延續":
            down.append(f"樣本外未延續（{oos['why']}）")
        if down:
            lvl = "fragile"
            reasons.append("逐筆兩個檢定都顯著，但：" + "；".join(down))
        else:
            lvl = "edge"
            reasons.append(f"t 檢定 p＝{sig['p_t']:.3f}、bootstrap p＝{sig['p_boot']:.3f}，兩者都 < 0.05")
            if mc.get("significant"):
                reasons.append(f"分月重抽 p＝{mc['p']:.3f} 也顯著")
            if oos.get("status") == "延續":
                reasons.append("樣本外前後兩段都顯著、衰減 < 50%")
            elif oos.get("status") == "無法驗證":
                reasons.append(f"樣本外無法驗證（{oos['why']}）")
            if sig["ci_lo"] <= 0:
                reasons.append("但 95% 區間下緣 ≤ 0，屬邊際證據")
            reasons.append("這是到目前為止的證據，不是未來的保證")
    return lvl, reasons


def analyze(df, name="", frac=0.1, loss_x=0.2, sim_n=None, B=10000, seed=SEED, openp=None, notes=None, paired=False, do_excess=True):
    """一份已平倉表 ⇒ 完整報告 dict（可被 import 直接用）。"""
    rep = {"name": name, "frac": frac, "notes": list(notes or []), "n_open": 0 if openp is None else len(openp)}
    if openp is not None and len(openp):
        rep["open_list"] = [f"{s}" + (f" {_d(e)}" if pd.notna(e) else "") for s, e in zip(openp["sid"], openp["entry_date"])]
        rep["open_missing"] = int((openp["entry_date"].isna() | ~np.isfinite(openp["entry_price"].to_numpy(float))).sum())
    n = len(df)
    rep["n"] = n
    if n == 0:
        rep["level"] = "insufficient"
        rep["reasons"] = ["沒有任何已平倉交易，無法檢驗" + (f"（未平倉 {rep['n_open']} 筆不進統計）" if rep["n_open"] else "")]
        return rep
    m = metrics(df, frac)
    sig = sig_test(df["ret"].to_numpy(float), B, seed)
    if df["exit_date"].notna().all():
        mc = month_cluster_test(df["ret"].to_numpy(float), df["exit_date"].dt.to_period("M").astype(str).to_numpy(), max(2000, B // 2), seed)
    else:
        mc = {"months": 0, "p": float("nan"), "significant": None}
    oos = oos_test(df, max(2000, B // 2), seed)
    flags = red_flags(m, sig, frac)
    lvl, reasons = judge(m, sig, mc, oos, flags)
    rep.update(metrics=m, sig=sig, month=mc, oos=oos, flags=flags, level=lvl, reasons=reasons, breakeven=breakeven(m),
               tags=per_tag(df), risk=risk_sim(df["ret"].to_numpy(float), sim_n or max(n, 100), frac, loss_x, seed=seed))
    if paired:
        rep["paired"] = paired_test(df, B, seed)
    if do_excess and np.isfinite(df["bench"].to_numpy(float)).all():
        ex = df.copy()
        ex["ret"] = df["ret"] - df["bench"]
        ex["pnl"] = ex["ret"] * ex["notional"]
        rep["excess"] = analyze(ex, name + "｜超額（報酬 − 基準）", frac, loss_x, sim_n, B, seed, None, None, False, False)
        rep["excess"]["bench_mean"] = float(df["bench"].mean())
    return rep


# ════════════════════════ 輸出 ════════════════════════
def _d(x):
    try:
        return "" if pd.isna(x) else str(pd.Timestamp(x).date())
    except Exception:
        return str(x)


def _p(x, k=1):
    return "—" if x is None or not np.isfinite(x) else f"{x:+.{k}%}"


def _pp(x, k=0):
    return "—" if x is None or not np.isfinite(x) else f"{x:.{k}%}"


def _f(x, k=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "∞" if x == float("inf") else "—"
    return f"{x:.{k}f}"


def text_report(rep):
    L = [f"══ {rep['name']} ══", f"裁決：{LEVELS[rep['level']][0]}"]
    L += [f"  - {r}" for r in rep["reasons"]]
    if rep.get("n_open"):
        L.append(f"未平倉 {rep['n_open']} 筆（不進統計）")
    if "metrics" not in rep:
        return "\n".join(L)
    m, s = rep["metrics"], rep["sig"]
    L.append(f"筆數 {m['n']}｜勝率 {_pp(m['win_rate'])}｜平均賺 {_p(m['avg_win'])}｜平均賠 {_p(-m['avg_loss'])}｜盈虧比 {_f(m['payoff'])}｜"
             f"期望值 {_p(m['expectancy'], 2)}｜中位 {_p(m['median'])}｜獲利因子 {_f(m['profit_factor'])}｜最大連虧 {m['max_streak']}｜"
             f"單筆最大占{m['top_share_base']} {_pp(m['top_share'])}｜持有 {_f(m['days_mean'], 1)} 天")
    L.append(f"顯著性：t p＝{s['p_t']:.4f}｜bootstrap p＝{s['p_boot']:.4f}｜95% 區間 [{_p(s['ci_lo'], 2)}, {_p(s['ci_hi'], 2)}]｜"
             f"分月重抽 p＝{_f(rep['month']['p'], 4)}（{rep['month']['months']} 個月）")
    o = rep["oos"]
    L.append(f"樣本外：{o['status']}｜{o['why']}" + (f"｜切點 {o['split_date']}，前 {o['n_in']} 筆 {_p(o['in']['mean'], 2)}（p {o['in']['p_boot']:.3f}）、"
                                                    f"後 {o['n_out']} 筆 {_p(o['out']['mean'], 2)}（p {o['out']['p_boot']:.3f}）" if "in" in o else ""))
    for sev, k, msg in rep["flags"]:
        L.append(f"警訊［{sev}］{k}：{msg}")
    rk = rep["risk"]
    L.append(f"風險情境（重抽 {rk['n_future']} 筆、每筆 {rk['frac']:.0%}）：回落中位 {_pp(rk['dd_med'])}、九成 {_pp(rk['dd_p90'])}；"
             f"回落超過 {rk['loss_x']:.0%} 的比例 {_pp(rk['p_dd_gt_x'], 1)}；期末虧超過 {rk['loss_x']:.0%} 的比例 {_pp(rk['p_final_loss_gt_x'], 1)}")
    if rep.get("paired"):
        pr = rep["paired"]
        L.append(f"兩欄對照：{pr['n']} 筆，實際 − 規則 平均 {_p(pr['mean'], 2)}，t p＝{_f(pr['p_t'], 4)}、bootstrap p＝{_f(pr['p_boot'], 4)}")
    out = "\n".join(L)
    if rep.get("excess"):
        out += "\n" + text_report(rep["excess"])
    return out


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mut:#6b6b70;--card:#fff;--line:#e4e2dc;--acc:#2c5d8a;--tbl:#f4f2ee}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17181a;--fg:#ececec;--mut:#a0a0a6;--card:#212225;--line:#34363a;--acc:#7fb0de;--tbl:#2a2b2f}}
:root[data-theme=dark]{--bg:#17181a;--fg:#ececec;--mut:#a0a0a6;--card:#212225;--line:#34363a;--acc:#7fb0de;--tbl:#2a2b2f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}h1{font-size:1.35rem;margin:.4em 0}h2{font-size:1.12rem;margin:1.4em 0 .4em;border-bottom:1px solid var(--line);padding-bottom:.2em}
h3{font-size:1rem;margin:1em 0 .3em}.mut{color:var(--mut);font-size:.9em}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;color:#fff;font-weight:600;font-size:.92em}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}table{border-collapse:collapse;width:100%;font-size:.88em;font-variant-numeric:tabular-nums}
th,td{border-bottom:1px solid var(--line);padding:5px 7px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{background:var(--tbl);font-weight:600}
ul{padding-left:1.2em;margin:.3em 0}li{margin:.15em 0}.big{font-size:1.05em;font-weight:600}
"""


def badge(lvl):
    name, color = LEVELS[lvl]
    return f'<span class="badge" style="background:{color}">{html.escape(name)}</span>'


def _tbl(head, rows):
    h = "".join(f"<th>{html.escape(str(x))}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def html_section(rep, show_detail=True):
    e = html.escape
    o = [f'<div class="card"><h3>{e(rep["name"])}　{badge(rep["level"])}</h3><ul>' + "".join(f"<li>{e(r)}</li>" for r in rep["reasons"]) + "</ul>"]
    if rep.get("n_open"):
        o.append(f'<p class="mut">未平倉 {rep["n_open"]} 筆另列，不進統計。</p>')
    if "metrics" not in rep:
        o.append("</div>")
        return "".join(o)
    m, s, mc, oo = rep["metrics"], rep["sig"], rep["month"], rep["oos"]
    o.append(_tbl(["項目", "數字"], [
        ["已平倉筆數", m["n"]], ["出場期間", f"{m['first_exit']}～{m['last_exit']}" if m["first_exit"] else "—"],
        ["勝率", _pp(m["win_rate"])], ["平均賺／平均賠", f"{_p(m['avg_win'])}／{_p(-m['avg_loss'])}"], ["盈虧比", _f(m["payoff"])],
        ["期望值（每筆平均淨報酬）", _p(m["expectancy"], 2)], ["中位數", _p(m["median"])], ["獲利因子", _f(m["profit_factor"])],
        ["最大連虧", m["max_streak"] if m["max_streak"] is not None else "—"],
        [f"單筆最大貢獻占{m['top_share_base'] or '淨利'}", _pp(m["top_share"])], ["拿掉最賺一筆後的期望值", _p(m["mean_wo_top"], 2)],
        ["平均持有天數", _f(m["days_mean"], 1)],
        ["t 檢定 p（單尾）", _f(s["p_t"], 4)], ["置中 bootstrap p（單尾）", _f(s["p_boot"], 4)],
        ["平均的 95% 區間", f"{_p(s['ci_lo'], 2)}～{_p(s['ci_hi'], 2)}"],
        ["分月重抽 p", f"{_f(mc['p'], 4)}（{mc['months']} 個月）"],
    ]))
    if show_detail:
        if "in" in oo:
            o.append(f"<p><b>樣本外：{e(oo['status'])}</b>　{e(oo['why'])}</p>")
            o.append(_tbl(["段", "出場期間", "筆數", "期望值", "t p", "bootstrap p"], [
                ["前段", f"{oo['in_range'][0]}～{oo['in_range'][1]}", oo["n_in"], _p(oo["in"]["mean"], 2), _f(oo["in"]["p_t"], 3), _f(oo["in"]["p_boot"], 3)],
                ["後段", f"{oo['out_range'][0]}～{oo['out_range'][1]}", oo["n_out"], _p(oo["out"]["mean"], 2), _f(oo["out"]["p_t"], 3), _f(oo["out"]["p_boot"], 3)]]))
        else:
            o.append(f"<p><b>樣本外：{e(oo['status'])}</b>　{e(oo['why'])}</p>")
        if rep["flags"]:
            o.append("<p><b>賭博特徵</b></p><ul>" + "".join(f"<li>［{ {'high': '高', 'medium': '中', 'low': '低'}[sv]}］{e(k)}：{e(msg)}</li>" for sv, k, msg in rep["flags"]) + "</ul>")
        else:
            o.append("<p><b>賭博特徵</b>：沒有掃到。</p>")
        be = rep["breakeven"]
        if be.get("ok"):
            if be["positive"]:
                o.append(f"<p><b>離打平還有多遠</b>：平均賺賠不變，勝率可以從 {_pp(be['wr'])} 退到 {_pp(be['req_wr'])}；"
                         f"勝率不變，盈虧比可以從 {_f(be['payoff'])} 退到 {_f(be['req_payoff'])}；每筆成本再多 {abs(be['cost_room']):.2%} 就打平。</p>")
            else:
                o.append(f"<p><b>轉正數字</b>：平均賺賠不變，勝率要從 {_pp(be['wr'])} 提高到 {_pp(be['req_wr'])}；"
                         f"或勝率不變，盈虧比要從 {_f(be['payoff'])} 提高到 {_f(be['req_payoff'])}；或每筆成本少 {abs(be['cost_room']):.2%}。</p>")
        rk = rep["risk"]
        o.append(f"<p><b>風險情境</b>（用自己的報酬重抽 {rk['n_future']} 筆、每筆投入 {rk['frac']:.0%} 資金依序複利、{rk['paths']} 條路徑；"
                 f"情境不是預測，也不算同時持有的重疊）：最大回落中位 {_pp(rk['dd_med'])}、十條裡最差一條約 {_pp(rk['dd_p90'])}；"
                 f"回落超過 {rk['loss_x']:.0%} 的比例 {_pp(rk['p_dd_gt_x'], 1)}；做完 {rk['n_future']} 筆仍虧錢 {_pp(rk['p_final_loss'], 1)}、"
                 f"虧超過 {rk['loss_x']:.0%} {_pp(rk['p_final_loss_gt_x'], 1)}。</p>")
        tg = rep.get("tags")
        if tg:
            o.append("<p><b>逐標籤（只描述，不認證任何單一標籤有優勢）</b></p>")
            o.append(_tbl(["標籤", "筆數", "勝率", "平均", "中位", "占總損益", "停掉它後：平均", "停掉後：獲利因子"],
                          [[t["tag"] + ("" if t["enough"] else "（筆數少）"), t["n"], _pp(t["win_rate"]), _p(t["mean"], 2), _p(t["median"]),
                            _pp(t["share"]), _p(t["cf_mean"], 2), _f(t["cf_pf"])] for t in tg["rows"]]))
            o.append('<p class="mut">停掉某標籤的「反事實」只是會計式對照；事後挑最差的停掉，改善會被高估（回歸平均）。</p>')
        pr = rep.get("paired")
        if pr and pr["n"]:
            word = ("實際比規則" + ("多賺" if pr["mean"] > 0 else "少賺") + f" {abs(pr['mean']):.2%}／筆，" +
                    ("兩個檢定都 < 0.05，不像運氣" if pr["significant"] else "和運氣分不開"))
            o.append(f"<p><b>照規則 vs 實際</b>（{pr['n']} 筆配對）：照規則平均 {_p(pr['rule_mean'], 2)}、實際 {_p(pr['act_mean'], 2)}；{e(word)}"
                     f"（t p＝{_f(pr['p_t'], 3)}、bootstrap p＝{_f(pr['p_boot'], 3)}，雙尾；實際較好 {_pp(pr.get('better'))}、較差 {_pp(pr.get('worse'))}）。</p>")
    if rep.get("excess"):
        ex = rep["excess"]
        o.append(f'<p><b>超額</b>（報酬 − 基準，基準平均 {_p(ex["bench_mean"], 2)}／筆）：{badge(ex["level"])}　期望值 {_p(ex["metrics"]["expectancy"], 2)}、'
                 f't p＝{_f(ex["sig"]["p_t"], 4)}、bootstrap p＝{_f(ex["sig"]["p_boot"], 4)}、分月 p＝{_f(ex["month"]["p"], 4)}、樣本外 {e(ex["oos"]["status"])}</p>')
    if rep.get("notes"):
        o.append('<p class="mut">' + "；".join(e(x) for x in rep["notes"]) + "</p>")
    o.append("</div>")
    return "".join(o)


HOWTO_READ = """<h2>怎麼讀</h2><ul>
<li><b>五級</b>：負期望 → 樣本不足 → 像運氣 → 脆弱優勢 → 統計優勢（仍不是保證）。由壞到好依序判，先碰到哪一級就停。</li>
<li><b>p 值</b>：「假如其實沒有優勢，光靠運氣出現這麼好成績的機率」。⛔ 不是「有優勢的機率」，1 − p 也不是信心度。</li>
<li>t 檢定與置中 bootstrap 兩個都 &lt; 0.05 才算「不像運氣」；另外分月重抽（同月交易互相相關）不顯著、樣本外沒延續、或有高嚴重度賭博特徵，最多只給「脆弱優勢」。</li>
<li>逐標籤只描述；同時檢定很多標籤，總有幾個會碰巧顯著。</li></ul>"""


def html_page(title, sections_html, intro=""):
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main><h1>{html.escape(title)}</h1>{intro}{sections_html}{HOWTO_READ}'
            f'<p class="mut">做法參考 mars-tw/anti-gambling-trader-tw（MIT）的方法論，程式為回測線自寫（backtest/tradecheck.py）。</p></main></body></html>')


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


# ════════════════════════ 自我查核 ════════════════════════
def _synth(rng, n, mean, sd, start="2018-01-01", skew=False):
    """合成交易：出場日每筆往後推 3 個工作日（月數充足）；skew ＞ 0 ⇒ 右偏、＜ 0 ⇒ 左偏（對數常態平移到指定平均）。"""
    if skew:
        z = rng.lognormal(0, 1.0, n)
        r = np.sign(skew) * (z - math.exp(0.5)) / math.sqrt((math.e - 1) * math.e) * sd + mean
    else:
        r = rng.normal(mean, sd, n)
    ent = pd.bdate_range(start, periods=n * 3, freq="B")[::3][:n]
    ex = ent + pd.offsets.BDay(20)
    return pd.DataFrame({"代號": [f"S{i % 50:02d}" for i in range(n)], "進場日": ent.strftime("%Y-%m-%d"), "出場日": ex.strftime("%Y-%m-%d"),
                         "報酬": [f"{v:.10f}" for v in r], "標籤": np.where(np.arange(n) % 2 == 0, "甲", "乙")})


def selfcheck(reps=1000, B_rep=1000):
    rng = np.random.default_rng(SEED)
    res = {"seed": SEED}
    ok_all = True

    def run(dfraw):
        c, op, nt, pa = normalize(dfraw.astype(str))
        return analyze(c, "check", B=4000, openp=op, notes=nt, paired=pa)

    # ① 已知有優勢
    r1 = run(_synth(rng, 300, 0.02, 0.06))
    res["① 有優勢（n300，平均 +2%，sd 6%）"] = LEVELS[r1["level"]][0]
    ok1 = r1["level"] == "edge"
    # ② 均值 0（單次）
    r2 = run(_synth(rng, 300, 0.0, 0.06))
    res["② 均值 0（單次）"] = LEVELS[r2["level"]][0]
    ok2 = r2["level"] != "edge" and r2["level"] != "fragile"
    # ③ 負期望
    r3 = run(_synth(rng, 300, -0.01, 0.06))
    res["③ 負期望（n300，平均 −1%）"] = LEVELS[r3["level"]][0]
    ok3 = r3["level"] == "neg"
    # ④ 均值 0 多次重抽：「兩個檢定都顯著」的比例（＝ 逐筆層的誤判率；裁決層再加分月、樣本外只會更低）
    fp = {}
    for kind, skew in (("常態", 0), ("右偏", 1), ("左偏", -1)):
        hit_both = hit_t = hit_b = hit_lvl = 0
        for k in range(reps):
            x = _synth(rng, 100, 0.0, 0.08, skew=skew)["報酬"].astype(float).to_numpy()
            s = sig_test(x, B_rep, seed=SEED + k)
            hit_both += s["significant"]; hit_t += s["p_t"] < ALPHA and s["mean"] > 0; hit_b += s["p_boot"] < ALPHA and s["mean"] > 0
            hit_lvl += s["significant"] and skewness(x) >= SKEW_LEFT          # 過檢定、又沒被左偏警訊擋下
        fp[kind] = {"兩者都顯著": hit_both / reps, "t": hit_t / reps, "bootstrap": hit_b / reps, "顯著且未被左偏擋": hit_lvl / reps}
    res["④ 均值 0 重抽 %d 次（n100）誤判率" % reps] = fp
    ok4 = all(v["顯著且未被左偏擋"] <= 0.065 for v in fp.values())
    res["④ 註"] = "左偏（賺小賠大型）時兩個檢定本身偏寬鬆；靠「偏態 < −1 ⇒ 高嚴重度警訊、最多脆弱優勢」擋下"
    # ⑤ 樣本不足
    r5 = run(_synth(rng, 20, 0.05, 0.05))
    res["⑤ 20 筆（平均 +5%）"] = LEVELS[r5["level"]][0]
    ok5 = r5["level"] == "insufficient"
    # ⑥ 樣本外：前段有優勢、後段 0 ⇒ 未延續
    a = _synth(rng, 210, 0.03, 0.05, start="2015-01-01"); b = _synth(rng, 90, 0.0, 0.05, start="2020-01-01")
    r6 = run(pd.concat([a, b], ignore_index=True))
    res["⑥ 前 210 筆 +3%、後 90 筆 0 ⇒ 樣本外"] = r6["oos"]["status"] + "／" + LEVELS[r6["level"]][0]
    ok6 = r6["oos"]["status"] == "未延續" and r6["level"] != "edge"
    # ⑦ 兩欄對照：實際 ＝ 規則 − 0.5%（滑價） ⇒ 顯著少賺；實際 ＝ 規則 ＋ 雜訊 ⇒ 分不開
    base = _synth(rng, 200, 0.01, 0.06)
    rr = base["報酬"].astype(float)
    p1 = base.drop(columns=["報酬"]).assign(照規則報酬=rr.map("{:.10f}".format), 實際報酬=(rr - 0.005 + rng.normal(0, 0.002, len(rr))).map("{:.10f}".format))
    p2 = base.drop(columns=["報酬"]).assign(照規則報酬=rr.map("{:.10f}".format), 實際報酬=(rr + rng.normal(0, 0.01, len(rr))).map("{:.10f}".format))
    q1, q2 = run(p1)["paired"], run(p2)["paired"]
    res["⑦ 兩欄：實際少 0.5%"] = f"差 {q1['mean']:+.3%}，{'顯著' if q1['significant'] else '不顯著'}"
    res["⑦ 兩欄：實際＝規則＋雜訊"] = f"差 {q2['mean']:+.3%}，{'顯著' if q2['significant'] else '不顯著'}"
    ok7 = q1["significant"] and q1["mean"] < 0 and not q2["significant"]
    # ⑧ 未平倉：沒有出場 ⇒ 不進統計
    raw = pd.DataFrame({"代號": ["1101", "2330"], "進場日": ["2026-09-29", "2026-09-30"], "進場價": ["40", "1000"], "出場日": ["", ""], "出場價": ["", ""]})
    r8 = run(raw)
    res["⑧ 2 筆未平倉"] = f"已平倉 {r8['n']}、未平倉 {r8['n_open']}、{LEVELS[r8['level']][0]}"
    ok8 = r8["n"] == 0 and r8["n_open"] == 2
    # ⑨ t 分布尾機率對照已知值（df 10, t 1.812 ⇒ 0.05；df 30, t 2.457 ⇒ 0.01）
    tv = (t_sf(1.812461, 10), t_sf(2.457262, 30))
    res["⑨ t 尾機率"] = [round(tv[0], 5), round(tv[1], 5)]
    ok9 = abs(tv[0] - 0.05) < 1e-5 and abs(tv[1] - 0.01) < 1e-5
    oks = {"①": ok1, "②": ok2, "③": ok3, "④": ok4, "⑤": ok5, "⑥": ok6, "⑦": ok7, "⑧": ok8, "⑨": ok9}
    res["通過"] = oks
    ok_all = all(oks.values())
    res["全過"] = ok_all
    return res


# ════════════════════════ 命令列 ════════════════════════
def main(argv=None):
    ap = argparse.ArgumentParser(description="交易紀錄檢驗：優勢、運氣，還是賭博")
    ap.add_argument("csv", nargs="*", help="逐筆交易表（可多個）")
    ap.add_argument("--cost", type=float, default=COST, help="沒有成本欄時的來回成本比率（預設 0.00585）")
    ap.add_argument("--frac", type=float, default=0.1, help="回落與風險情境用：每筆投入資金比例（預設 0.1）")
    ap.add_argument("--loss-x", type=float, default=0.2, help="風險情境的虧損門檻 X（預設 0.2）")
    ap.add_argument("--sim-n", type=int, default=None, help="風險情境模擬幾筆（預設 ＝ 已平倉筆數，至少 100）")
    ap.add_argument("--boot", type=int, default=10000, help="bootstrap 次數")
    ap.add_argument("--html", default=None, help="輸出網頁路徑")
    ap.add_argument("--json", default=None, help="輸出 json 路徑")
    ap.add_argument("--check", action="store_true", help="合成資料自我查核")
    a = ap.parse_args(argv)
    if a.check:
        r = selfcheck()
        print(json.dumps(r, ensure_ascii=False, indent=1, default=_json_default))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=1, default=_json_default)
        return 0 if r["全過"] else 1
    if not a.csv:
        ap.error("要給交易表，或用 --check")
    reps = []
    for p in a.csv:
        c, op, nt, pa = load_csv(p, a.cost)
        rep = analyze(c, os.path.basename(p), a.frac, a.loss_x, a.sim_n, a.boot, openp=op, notes=nt, paired=pa)
        reps.append(rep)
        print(text_report(rep)); print()
    if a.html:
        with open(a.html, "w", encoding="utf-8") as f:
            f.write(html_page("交易紀錄檢驗", "".join(html_section(r) for r in reps)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(reps, f, ensure_ascii=False, indent=1, default=_json_default)
    return 0


if __name__ == "__main__":
    sys.exit(main())

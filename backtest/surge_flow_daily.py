# -*- coding: utf-8 -*-
"""買賣流程追蹤（使用者買進才加）——回測線，給每日名單（daily_list.py）用；每天從買進日重播、不存中間狀態。

流程（使用者 2026-09-30 決定：W1 賣 3 成、留 7 成；剩 7 成出場 ＝ W2 或回落 30%（另案研究結果：現行最好，commit 075078d9ae））：
  全部持有 ── 連 40 天沒創新高（使用者 2026-09-30 定的退場規則；逐字同 researchSurge6_restexit R4 乙群 N＝40）：新高 ＝ 收盤 ＞ 買進日以來最高收盤（買進日本身算新高日）；
               最後一個新高日 h 之後的 K 棒數（(h, d] 內有 K 棒的日子）第一次 ≥ 40 的那天 ⇒ 次一開盤賣全部（結束）；只在 W1 還沒出現前適用（同一天 W1 也出現 ⇒ 以這條為準）
             ── W1 第一頂警示（收盤創 20 日新高 ∧ 過去 60 日無處置 ∧ 10 日注意次數 Q5 ∧（5 日漲停天數 Q5 或 5 日報酬 Q5））第一次出現 ⇒ 次一開盤賣 3 成
  已賣 3 成 ── 剩 7 成：等 W2 第二頂警示（收盤在含當天 20 根最高收盤 10% 內 ∧（再次進入處置：當天是處置起日且前 60 個交易日內另有起日｜處置出關：當天是迄日下一交易日））
               在賣 3 成之後第一次出現（兩種取先到者）⇒ 次一開盤賣剩 7 成
  已出清／待買回 ── 只在出清後才適用：收盤「從買進以來最高收盤回落第一次達到 20%」（跨過那天）且 bottomjudge 當下版分數（x＝20%、K＝5）≥ 探索段讀法 m* ⇒ 次一開盤買回
  第二段持有 ── 買回後 W2 第一次出現 ⇒ 次一開盤賣
  結束 ── 任何時候收盤 ≤ 買進以來最高收盤 × 0.7（本筆結束；還有部位 ⇒ 次一開盤賣）；或第二段 W2 賣出
  參考停損（只提示、⛔ 不進流程）：階段「全部持有」且 W1 從未出現時，今天收盤 ≤ 買進價 × 0.85 ⇒ 加一句提示
     （買進價是未還原價 ⇒ 換成還原價比：買進價 ×（買進日還原收盤 ÷ 買進日未還原收盤）× 0.85）
  價格一律還原收盤（ffill）、還原開盤；「次一開盤」＝ 之後第一根有效 K 棒（有成交、開盤 ＞ 0）
讀檔 backtest/holdings_flow.txt（每行：代號, 買進日, 買進價；# 開頭為註解）；測試可用環境變數 HOLDINGS_FLOW 指到別的檔
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import researchSurge5_feat as FT
from backtest import researchSurge6_mid_desc as MD
from backtest import researchSurge6_bottomjudge as BJ

HERE = os.path.dirname(os.path.abspath(__file__))
FLOW = os.environ.get("HOLDINGS_FLOW", os.path.join(HERE, "holdings_flow.txt"))
BJDIR = os.path.join(HERE, "resultsSurge6", "bottomjudge")
X = 0.20


def read_flow(path=None):
    p = path or FLOW
    if not os.path.exists(p):
        return []
    out = []
    for ln in open(p, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        a = [x.strip() for x in ln.replace("，", ",").split(",")]
        out.append((a[0], a[1], float(a[2])))
    return out


def bj_scorer():
    sel = pd.read_csv(os.path.join(BJDIR, "part2_selected.csv")); meta = json.load(open(os.path.join(BJDIR, "meta.json"), encoding="utf-8"))
    names = sel[(sel["x"] == "20%") & (sel["K"].astype(str) == "5")].sort_values("順位")["特徵"].tolist()
    return names, int(meta["當下可用版 m*"]["20%_K5"]), {k: v for k, v in meta["五等分分界（探索段低點）"].items() if k.endswith("_x20")}


def stock_ctx(sid, mk, cal, n, price_dir, aux_dir, DISP, disp_row):
    """同 researchSurge6_bottomjudge.stock_ctx，路徑參數化（價量 price_dir；法人、融資 aux_dir）。"""
    D.DATA = price_dir
    st = D.load_stock(sid, mk, cal); df = st.df
    c = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
    amt = np.nan_to_num(pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)); bar = np.isfinite(df["close"].to_numpy(float))
    raw = pd.read_csv(os.path.join(price_dir, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); sh = pd.to_numeric(raw["shares"].reindex(cal), errors="coerce").ffill().to_numpy(float).copy(); sh[~(sh > 0)] = np.nan
    fo = np.zeros(n); tr = np.zeros(n); mb = np.full(n, np.nan)
    p_ = os.path.join(aux_dir, "stocks_inst", sid + ".csv")
    if os.path.exists(p_):
        it = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last"); it.index = pd.to_datetime(it["date"])
        fo = pd.to_numeric(it["foreign"], errors="coerce").reindex(cal).fillna(0.0).to_numpy(); tr = pd.to_numeric(it["trust"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
    p_ = os.path.join(aux_dir, "stocks_margin", sid + ".csv")
    if os.path.exists(p_):
        mg = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "m_balance"]).drop_duplicates("date", keep="last"); mg.index = pd.to_datetime(mg["date"])
        mb = pd.to_numeric(mg["m_balance"], errors="coerce").reindex(cal).ffill().to_numpy()
    idx = np.flatnonzero(bar); cb = c[idx]
    ma = {}
    for w in (20, 60):
        m_ = np.full(n, np.nan); m_[idx] = pd.Series(cb).rolling(w, min_periods=w).mean().to_numpy(); ma[w] = pd.Series(m_).ffill().to_numpy()
    below = {w: np.r_[0, np.cumsum(bar & (c < ma[w]))] for w in (20, 60)}
    ends = np.array(sorted(b for a, b in DISP.get(sid, []))); starts = np.array(sorted(a for a, b in DISP.get(sid, [])))
    return {"c": c, "ca": np.r_[0, np.cumsum(amt)], "cn": np.r_[0, np.cumsum(bar)], "cf": np.r_[0, np.cumsum(fo)], "ct": np.r_[0, np.cumsum(tr)], "mb": mb, "sh": sh,
            "ma": ma, "below": below, "ends": ends, "starts": starts, "disp": disp_row, "o": df["open"].to_numpy(float), "bar": bar}


def bj_has(name, f, bounds, qv):
    """同 researchSurge6_topwarn.bj_has（x＝20%）。"""
    feat, lev = name.split("｜", 1)
    if feat in BJ.CONT:
        v = f[feat]
        if not np.isfinite(v):
            return False
        bd = bounds[f"{feat}_x20"]; code = int(lev.split("（")[0][1:])
        return int(np.searchsorted(bd, v, "right") + 1) == code
    if feat in BJ.BOOL:
        v = f[feat]
        return np.isfinite(v) and (v == 1) == (lev == "是")
    if feat in BJ.CNTF:
        return f[feat] == (3 if lev.startswith("3") else int(lev))
    return qv(name)


def signals_for(R, s, X_, DISP, sid):
    """W1、W2a、W2b（日曆位置 d0..d1 的旗標）與 20 日高相關旗標。"""
    d0, d1 = R["d0"], R["d1"]; n = len(R["cal"]); c = X_["c"]; bar = X_["bar"]
    idx = np.flatnonzero(bar); cb = c[idx]
    mx20 = pd.Series(cb).rolling(20, min_periods=20).max().to_numpy(); pmx = np.r_[np.nan, mx20[:-1]]
    HI20 = np.zeros(n, bool); NEAR = np.zeros(n, bool); HI20[idx] = cb > pmx; NEAR[idx] = cb >= 0.9 * mx20
    rng = np.arange(d0, d1 + 1); t = rng - d0
    cd = R["code"]
    w1 = HI20[rng] & (cd["att_10"][s, t] == 5) & ((cd["lu_5"][s, t] == 5) | (cd["r_5"][s, t] == 5)) & (R["raw"]["disp_60"][s, t] == 0) & bar[rng]
    iv = DISP.get(sid, []); st_ = sorted(a for a, b in iv)
    START = np.zeros(n, bool); EXIT = np.zeros(n, bool); RE60 = np.zeros(n, bool)
    for a, b in iv:
        if 0 <= a < n:
            START[a] = True
            if any(0 < a - x <= 60 for x in st_ if x != a):
                RE60[a] = True
        if 0 <= b + 1 < n:
            EXIT[b + 1] = True
    w2a = RE60[rng] & NEAR[rng] & bar[rng]; w2b = EXIT[rng] & NEAR[rng] & bar[rng]
    return w1, w2a, w2b


def nohigh_day(c, bar, e, last, N=40):
    """restexit R4 乙群（run_rules，st0 ＝ e、lo_ ＝ e）逐字：[e, last] 內第一個「最後新高日之後 K 棒數 ≥ N」的日子；沒有 ⇒ None。"""
    cbar = np.cumsum(bar)
    sg = c[e:last + 1]; r_ = np.maximum.accumulate(sg)
    isnh = np.r_[True, sg[1:] > r_[:-1]]; lastnh = e + np.maximum.accumulate(np.where(isnh, np.arange(len(sg)), 0))
    nbar = cbar[e:last + 1] - cbar[lastnh]
    hh = np.flatnonzero(nbar >= N)
    return e + int(hh[0]) if len(hh) else None


def replay(R, code, buy_date, buy_px, price_dir, aux_dir, names_bj=None):
    """⇒ dict（階段、今日訊號、今天收盤後該做什麼、歷程）。階段：全部持有／已賣 3 成／已出清／待買回／第二段持有／結束。"""
    cal = R["cal"]; n = len(cal); W = R["W"]; uni = R["uni"]; d0, d1 = R["d0"], R["d1"]; T = d1
    row = uni.index[uni["stock_id"] == code]
    if not len(row):
        return {"代號": code, "錯誤": "不在母體（上市櫃普通股 gate3）"}
    s = int(row[0]); mk = uni.loc[s, "market"]
    bd = pd.Timestamp(buy_date)
    if bd > cal[T]:
        return {"代號": code, "錯誤": f"買進日 {buy_date} 在資料日 {cal[T].date()} 之後"}
    e = int(cal.searchsorted(bd))
    if e < d0:
        return {"代號": code, "錯誤": f"買進日早於計算範圍（{cal[d0].date()}）"}
    disp = np.zeros(n, bool)
    for a_, b_ in W["DISP"].get(code, []):
        disp[max(a_, 0):min(b_, n - 1) + 1] = True
    X_ = stock_ctx(code, mk, cal, n, price_dir, aux_dir, W["DISP"], disp)
    c, o, bar = X_["c"], X_["o"], X_["bar"]
    okop = np.isfinite(o) & (o > 0) & bar
    nxo = lambda d: next((p for p in range(d + 1, T + 1) if okop[p]), None)            # 次一有效開盤（資料內）
    w1, w2a, w2b = signals_for(R, s, X_, W["DISP"], code)
    names, mstar, bounds = bj_scorer() if names_bj is None else names_bj
    rmx = np.maximum.accumulate(c[e:T + 1]); dd_now = c[T] / rmx[-1] - 1
    stopw = np.flatnonzero(c[e:T + 1] <= rmx * 0.7); stop = e + int(stopw[0]) if len(stopw) else None
    lastday = stop if stop is not None else T
    hist = []
    O = lambda st, today, act: _out(code, uni, buy_date, buy_px, st, today, act, hist, c, rmx, T)
    REST = "剩 7 成：等 W2（再次處置或出關）或從最高回落 30%"
    raw = pd.read_csv(os.path.join(price_dir, "stocks", code + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); rcl = pd.to_numeric(raw["close"].reindex(cal), errors="coerce").to_numpy(float)
    fac = c[e] / rcl[e] if np.isfinite(rcl[e]) and rcl[e] > 0 else np.nan
    hint = "參考：已跌破買進價 15%（研究建議的停損線，要不要賣你決定）" if np.isfinite(fac) and c[T] <= buy_px * fac * 0.85 else ""

    def w2first(frm):
        return next(((d, "再次進入處置" if w2a[d - d0] else "處置出關") for d in range(frm, lastday + 1) if w2a[d - d0] or w2b[d - d0]), None)

    def ended_by_stop(stage_if_pending, what):
        hist.append(f"回落 30% {cal[stop].date()}")
        ex = nxo(stop)
        if ex is None:
            o_ = O(stage_if_pending, ["回落 30%（本筆結束）"], f"明天開盤賣{what}（從最高回落 30%，本筆結束）")
            if stage_if_pending == "全部持有":
                o_["參考"] = hint
            return o_
        hist.append(f"賣{what} {cal[ex].date()}")
        return O("結束", [], f"已結束（{cal[stop].date()} 從最高回落 30%，{cal[ex].date()} 賣{what}）")
    # ① 全部持有 ⇒ 連 40 天沒創新高（賣全部）或 W1 賣 3 成
    d1_ = next((d for d in range(e, lastday + 1) if w1[d - d0] and (stop is None or d < stop)), None)
    n40 = nohigh_day(c, bar, e, lastday)
    if n40 is not None and (d1_ is None or n40 <= d1_):
        hist.append(f"連 40 天沒新高 {cal[n40].date()}")
        ex = nxo(n40)
        if ex is None:
            o_ = O("全部持有", ["買進後連續 40 個交易日沒創新高"], "明天開盤賣全部（買進後連續 40 個交易日沒創新高，你定的退場規則）"); o_["參考"] = hint
            return o_
        hist.append(f"賣全部 {cal[ex].date()}")
        return O("結束", [], f"已結束（{cal[n40].date()} 買進後連續 40 個交易日沒創新高，{cal[ex].date()} 賣全部）")
    if d1_ is None:
        if stop is not None:
            return ended_by_stop("全部持有", "全部")
        o_ = O("全部持有", [], "續抱（W1 第一頂警示未出現）"); o_["參考"] = hint
        return o_
    hist.append(f"W1 {cal[d1_].date()}")
    ex1 = nxo(d1_)
    if ex1 is None:
        return O("全部持有", ["W1 第一頂警示"], f"明天開盤賣 3 成、留 7 成（W1 第一頂警示第一次出現；{REST}）")
    hist.append(f"賣 3 成 {cal[ex1].date()}")
    # ② 剩 7 成：W2 或回落 30%（出場規則待定，暫用）
    w2 = w2first(ex1)
    if w2 is None or (stop is not None and w2[0] >= stop):
        if stop is not None:
            return ended_by_stop("已賣 3 成", "剩 7 成")
        return O("已賣 3 成", [], f"續抱（{REST}；W2 未出現）")
    hist.append(f"W2（{w2[1]}）{cal[w2[0]].date()}")
    ex2 = nxo(w2[0])
    if ex2 is None:
        return O("已賣 3 成", [f"W2 第二頂警示（{w2[1]}）"], f"明天開盤賣剩 7 成（W2：{w2[1]}；{REST}）")
    hist.append(f"賣剩 7 成 {cal[ex2].date()}")
    # ③ 已出清 ⇒ 中段底買回（bottomjudge 當下版）
    thr = rmx * (1 - X) * (1 + 1e-9); below = c[e:T + 1] <= thr
    cross = [e + k for k in np.flatnonzero(below[1:] & ~below[:-1]) + 1 if e + k > ex2 and (stop is None or e + k < stop)]
    eb = None; last = None
    for d2 in cross:
        A = e + int(np.argmax(c[e:d2 + 1]))
        cuts = [(e + a, e + b) for a, b, lo, hi in MD.pullbacks(c[e:A + 1]) if a > 0 and lo <= hi * (1 - X) * (1 + 1e-9)] if A - e > 2 else []
        Lp = cuts[-1][1] if cuts else e
        f = {k_: float(v_[0]) for k_, v_ in BJ.pull_feats(X_, np.array([A]), np.array([d2]), np.array([Lp]), np.array([e]), np.array([len(cuts)]), np.array([np.nan])).items()}
        sc = sum(bj_has(nm_, f, bounds, lambda nm: _qv(R, s, d2, nm)) for nm_ in names); last = (d2, sc)
        if sc >= mstar:
            hist.append(f"回落 20% {cal[d2].date()} 分數 {sc}/{len(names)}")
            eb = nxo(d2)
            if eb is None:
                return O("已出清／待買回", [f"中段底買回訊號（分數 {sc}/{len(names)} ≥ {mstar}）"], "明天開盤買回")
            hist.append(f"買回 {cal[eb].date()}")
            break
        hist.append(f"回落 20% {cal[d2].date()} 分數 {sc}/{len(names)}（未達 {mstar}）")
    if eb is None:
        if stop is not None:
            hist.append(f"回落 30% {cal[stop].date()}")
            return O("結束", [], f"已結束（{cal[stop].date()} 從最高回落 30%；出清後沒有買回）")
        tt = [f"今天回落 20%、分數 {last[1]}/{len(names)}（未達 {mstar}）"] if last and last[0] == T else []
        return O("已出清／待買回", tt, f"等待：從最高收盤回落第一次達到 20% 且分數 ≥ {mstar}")
    # ④ 第二段持有 ⇒ W2 或回落 30%
    w2b_ = w2first(eb)
    if w2b_ is not None and (stop is None or w2b_[0] < stop):
        hist.append(f"W2（{w2b_[1]}）{cal[w2b_[0]].date()}")
        ex3 = nxo(w2b_[0])
        if ex3 is None:
            return O("第二段持有", [f"W2 第二頂警示（{w2b_[1]}）"], f"明天開盤賣（W2：{w2b_[1]}）")
        hist.append(f"賣 {cal[ex3].date()}")
        return O("結束", [], f"已結束（{cal[ex3].date()} 第二段 W2 賣出）")
    if stop is not None:
        return ended_by_stop("第二段持有", "")
    return O("第二段持有", [], "續抱（W2 第二頂警示未出現）")


def _qv(R, s, d, name):
    lv = next(l for l in FT.levels() if f"{l[4]}｜{l[3]}" == name)
    if lv[1] not in R["code"]:
        raise KeyError(f"⛔ 每日模組沒有算「{name}」（{lv[1]}）；bottomjudge 選的特徵換了要補 surge_feat_daily.QCOLS")
    return R["code"][lv[1]][s, d - R["d0"]] == lv[2]


def _out(code, uni, bd, bp, stage, today, action, hist, c, rmx, T):
    nm = str(uni.loc[uni["stock_id"] == code, "name"].iloc[0]) if (uni["stock_id"] == code).any() else ""
    return {"代號": code, "名稱": nm, "買進日": bd, "買進價": bp, "階段": stage, "今日訊號": "、".join(today) if today else "無", "今天收盤後該做什麼": action,
            "歷程": " → ".join(hist) if hist else "—", "距最高": (np.nan if stage == "結束" else float(c[T] / rmx[-1] - 1))}

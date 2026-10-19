# -*- coding: utf-8 -*-
"""VIX 飆高時一筆閒錢怎麼進場（使用者接著 researchVIXbuy 問「怎麼進場比較好？」）。回測線計算子代理。
⛔ 描述，不是買賣建議；⛔ 不計 N、不判合格、不是登錄件；看過結果才比較各方式 ⇒ 結果句必附「樣本極少、看過結果才比較」。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXentry
    查核：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXentry_check

═══ 讀法（⭐ 寫死於 2026-10-20（台北），寫死前 ⛔ 沒看任何進場方式的報酬；只看過 researchVIXbuy 的 E1 型結果）═══
重用（import，不改）researchUSC13：load_vix／load_us／load_tw、segments（段止 ＝ VIX 收盤 ≤ 20）、buy_index（VIX 日期 d ⇒ 市場日期 ＞ d 的第一個有效開盤；
台股 ＝ 台北 d＋1 含之後第一個有 K 棒日開盤）、next_valid、month_tables、wealth（C7／C13 財富式：未投入現金照 CI 複利、買進成本照比例扣）。
 E0 段 ＝ C.segments(門檻 40)；觸發日 d0 ＝ 段起日（VIX 收盤首次 ≥ 40）；美股段 1990-01-02～2026-09-30、台股段 2003-06-30 起（同 C13-7）。
    標的資料首日晚於 d0 的段 ⇒ 該標的「無資料」不列。
 E1 一次全買：d0 的 buy_index 開盤（記 b0）全部買。
 E2 分兩次：b0 買一半；段內（d0 當天起）第一個 VIX 收盤 ≥ 50 的日子 ⇒ 其 buy_index 開盤買剩下全部（d0 當天就 ≥ 50 ⇒ 同 b0 兩筆＝一次全買）；
    段內沒有 ≥ 50 ⇒ 段止日（VIX ≤ 20）的 buy_index 開盤買剩下全部；段到資料末未止 ⇒ 剩下一半一直是現金。
 E3 等回落：d0 之後（不含 d0）第一個 VIX 收盤 ＜ 30 的日子 ⇒ 其 buy_index 開盤全部買（段止日 ≤ 20 必在其後或同日，故必在段內）。
 E4 分 3 個月：b0 買 1/3；b0 所在月之後第 1、2 個月的第一個交易日（有效開盤）各買「剩餘現金 ÷ 剩餘筆數」（＝ C7 定額式；台股 0 利率 ⇒ 各 1/3）。
 E5 同 E1 但門檻 30（對照）：含 d0 的那個 ≥30 段（段止同為 VIX ≤ 20 ⇒ 每個 ≥40 段恰屬一個 ≥30 段）的段起日 d30 ⇒ 其 buy_index 開盤全部買；
    E5 的錢從它自己的買進日起算（早於 b0；d30 ＝ d0 時 ＝ E1），結束日同其他方式；其他方式在 d30～d0 之間的現金利息不計（⚠ 照寫）。
    ⚠ 這裡只含「之後真的到 40」的 ≥30 段（事後挑），全部 ≥30 段一次全買的結果見 researchVIXbuy（≥30 首日 1 年落後）。
 E6 結束日：d0 ＋ 12 個月、＋ 36 個月（日曆）⇒ 日期 ≤ 該日的最後一個交易日收盤；該日 ＞ 標的資料末日 ⇒「未滿期」不計。結束日前沒買到的錢 ＝ 現金。
 E7 期末財富：同一筆本金 1.0（表上寫成 100 萬），C.wealth 原式；未投入：美股（^SP500TR、SSO、合成 SSO）放 DTB3（C13-1 CI）、台股（0050、00631L）0 報酬（同 C13 台股臂）；
    成本：美股 0.05%、台股 0.1425%（買進額，同 C13）；不賣。
 E8 必報：① 期末財富（萬）與「對 E1 差」；② 買進後最深再跌 ＝ 各筆 min(0, 該筆買進日起到結束日的最低收盤 ÷ 該筆買價 − 1) 以買進金額加權；
    ③ 帳面最深 ＝ min(0, 起算日到結束日每日財富的最低 − 1)（相對本金）；④ 平均買進成本 ＝ 買進金額 ÷ 股數（開盤價、不含成本），
    對「觸發日收盤」（日期 ≤ d0 的最後一個收盤；E5 也對 d0）的差；結束日前沒買完 ⇒ 只算已買部分、另報期末現金占比。
 E9 逐段勝負：每段 E2～E5 期末財富對 E1（贏／輸／平：|差| ＜ 1e-9 為平）；另報每段第一名次數。
 E10 標的：^SP500TR（1990 起）、0050（2004-02-11 起，C13 台股臂序列）。
⭐ 追加標的（使用者看過 0050／美股結果【前】追加「正二呢？」；進場方式 E1～E5 與讀法不變，只是描述格）：
 E11 00631L 元大台灣50正2：data.load_stock 主快照（edc6f）還原開收（researchTri.load_all 同讀法），只用有效 K 棒；時差、成本、0 利率同 0050 台股臂；
     上市 2014-10-31 ⇒ 只有之後的段。
 E12 SSO 真實價：researchUSA1_data.load_market 的 SSO（adjclose÷close 還原開收），2006-06-21 起；時差、DTB3、成本同 ^SP500TR。
 E13 合成 SSO（⚠ 合成、非實際 ETF）：researchUSA1_data.synth(M, "SSO")（A1 seq3：2r −（DTB3_{t−1}＋0.25%）/252 − 0.89%/252），1990 起；同 E12。
 ⚠ 正二含槓桿與每日重設耗損；段數更少 ⇒ 結果句必附「樣本極少」與「正二含槓桿與每日重設耗損」。

⛔⛔ 私有資料：us-stock-data 私有 ⇒ resultsVIXentry/ 只放彙總（平均、中位、勝負次數）；美股三個標的逐段明細只放 ~/us_work/vixentry/。
   台股（0050、00631L）逐段事件層級放 resultsVIXentry/（同 VIXbuy_events.csv 台股先例；不放逐日價）。
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC13 as C

OUT = os.path.expanduser("~/tw-p17/backtest/resultsVIXentry")
WORK = os.path.expanduser("~/us_work/vixentry")
THR = 40.0
HM = (12, 36)
HN = {12: "1年", 36: "3年"}
METH = ("E1", "E2", "E3", "E4", "E5")
MN = {"E1": "E1 一次全買", "E2": "E2 分兩次（≥50 或段止）", "E3": "E3 等回落 <30", "E4": "E4 分 3 個月", "E5": "E5 門檻 30 一次全買"}
DISC = "描述，不是買賣建議；樣本極少、看過結果才比較"
EPS = 1e-9


def jdump(obj, path):
    def cv(o):
        if isinstance(o, dict):
            return {str(k): cv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [cv(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(cv(obj), open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ═════════════ 標的 ═════════════
def mk_us(U, o, c, label, priv=True, note=""):
    o = np.asarray(o, float); c = np.asarray(c, float)
    ok = np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0)
    cf = pd.Series(np.where(np.isfinite(c) & (c > 0), c, np.nan)).ffill().to_numpy()
    first = int(np.flatnonzero(ok)[0])
    return {"label": label, "dates": U["dates"], "o": o, "cf": cf, "ok": ok, "CI": U["CI"], "cost": C.COST_US, "lo": None,
            "d_first": str(U["dates"][first]), "priv": priv, "note": note}


def load_00631L():
    from backtest import researchRev as RV        # 匯入時把 D.DATA 指到快照 edc6f（同 C.load_tw）
    D = RV.D
    cal = D.load_calendar()
    st = D.load_stock("00631L", "twse", cal); df = st.df
    dates = np.array([str(x.date()) for x in cal])
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    v = np.isfinite(c)
    dates, o, c = dates[v], o[v], c[v]
    ok = np.isfinite(o) & (o > 0) & np.isfinite(c) & (c > 0)
    r = c[1:] / c[:-1]
    jumps = [(str(dates[i + 1]), float(r[i])) for i in np.flatnonzero((r <= 0.55) | (r >= 1.8))]
    info = {"序列首日": str(dates[0]), "序列末日": str(dates[-1]), "有效 K 棒": int(len(dates)), "開盤缺值": int((~ok).sum()),
            "還原收盤相鄰比 ≤0.55 或 ≥1.8（斷點檢查）": jumps, "還原事件數": len(st.events) if hasattr(st, "events") else None}
    return {"label": "00631L 元大台灣50正2", "dates": dates, "o": o, "cf": c, "ok": ok, "CI": np.ones(len(dates)), "cost": C.COST_TW,
            "lo": C.TW_SEG0, "d_first": str(dates[0]), "priv": False, "info": info, "note": "使用者看過結果前追加；正二含槓桿與每日重設耗損"}


# ═════════════ 計畫 ═════════════
def plans(X, vd, vv, g, g30, bidx, nv, ym, first):
    """→ {方式: (起算位置, [(位置, 用當時現金比例)])}；位置 ≥ n 表示沒有。"""
    j0, je = g["_j"], g["_je"]
    ended = g["段止日（VIX≤20）"] != "資料末仍 ＞ 20"
    b0 = int(bidx[j0]); n = len(X["dates"])
    P = {"E1": (b0, [(b0, 1.0)])}
    # E2
    j50 = next((j for j in range(j0, je + 1) if vv[j] >= 50.0), None)
    if j50 is not None:
        b2 = int(bidx[j50]); why = f"VIX≥50 {vd[j50]}"
    elif ended:
        b2 = int(bidx[je]); why = f"段止 {vd[je]}"
    else:
        b2 = n; why = "段未止（剩下一半一直現金）"
    P["E2"] = (b0, [(b0, 0.5), (b2, 1.0)])
    # E3
    j3 = next((j for j in range(j0 + 1, len(vd)) if vv[j] < 30.0), None)
    b3 = int(bidx[j3]) if j3 is not None else n
    P["E3"] = (b0, [(b3, 1.0)])
    # E4
    m0 = int(ym[b0]); bb = [(b0, 1 / 3)]
    for k, fr in ((1, 1 / 2), (2, 1.0)):
        bb.append((int(nv[first[m0 + k]]) if (m0 + k) in first else n, fr))
    P["E4"] = (b0, bb)
    # E5
    b5 = int(bidx[g30["_j"]])
    P["E5"] = (b5, [(b5, 1.0)])
    meta = {"E2第二筆依據": why, "E2第二筆VIX日": vd[j50] if j50 is not None else (vd[je] if ended else None),
            "E3回落<30日": vd[j3] if j3 is not None else None, "E5的≥30段起日": g30["段起日"]}
    return P, meta


def path_wealth(o, cf, CI, s, buys, e, cost):
    """C.wealth 同式但回傳每日財富與各筆金額（最後一天須 ＝ C.wealth，見 run）。"""
    sh = 0.0; cash_at = 1.0; tc = s - 1; bi = 0
    V = np.empty(e - s + 1); tr = []
    for t in range(s, e + 1):
        while bi < len(buys) and buys[bi][0] == t:
            c_open = cash_at * CI[t - 1] / CI[tc]
            amt = c_open * buys[bi][1]
            sh += amt * (1 - cost) / o[t]
            cash_at = c_open - amt; tc = t - 1
            tr.append((t, amt)); bi += 1
        cash_t = cash_at * CI[t] / CI[tc]
        V[t - s] = sh * cf[t] + cash_t
    return V, tr, cash_t


def end_index(dates, d0, hm):
    tgt = (pd.Timestamp(str(d0)) + pd.DateOffset(months=hm)).strftime("%Y-%m-%d")
    if tgt > dates[-1]:
        return -1, tgt
    return int(np.searchsorted(dates, tgt, side="right") - 1), tgt


def run(X, vd, vv):
    dates, o, cf, CI, cost = X["dates"], X["o"], X["cf"], X["CI"], X["cost"]
    n = len(dates); nv = C.next_valid(X["ok"]); bidx = C.buy_index(vd, dates, nv)
    ym, first, _ = C.month_tables(dates)
    s40 = C.segments(vd, vv, THR, X["lo"]); s30 = C.segments(vd, vv, 30.0, X["lo"])
    rows = []; skipped = []
    for g in s40:
        g30 = [h for h in s30 if h["_je"] == g["_je"] and h["_j"] <= g["_j"]]
        assert len(g30) == 1, g["段起日"]
        g30 = g30[0]
        if g["段起日"] < X["d_first"] or int(bidx[g["_j"]]) >= n:
            skipped.append(g["段起日"]); continue
        P, meta = plans(X, vd, vv, g, g30, bidx, nv, ym, first)
        e5_na = g30["段起日"] < X["d_first"]
        iref = int(np.searchsorted(dates, g["段起日"], side="right") - 1)
        ref = cf[iref]
        for hm in HM:
            e, tgt = end_index(dates, g["段起日"], hm)
            base = {"標的": X["label"], "段起日d0": g["段起日"], "段起VIX": g["段起VIX收盤"], "段內最高VIX": g["段內最高VIX收盤"],
                    "段止日": g["段止日（VIX≤20）"], "持有": HN[hm], "結束目標日": tgt, "觸發日收盤日": dates[iref], **meta}
            if e < 0:
                rows.append({**base, "方式": "全部", "狀態": "未滿期"}); continue
            for m in METH:
                if m == "E5" and e5_na:
                    rows.append({**base, "方式": m, "狀態": "E5 起點早於資料"}); continue
                s, bb = P[m]
                bb = [(t, f) for t, f in bb if t <= e and t < n]
                V, tr, cash_e = path_wealth(o, cf, CI, s, bb, e, cost)
                Wc, _ = C.wealth(o, cf, CI, s, bb, e, cost)
                assert abs(Wc - V[-1]) < 1e-12, (m, g["段起日"])
                amt = np.array([a for _, a in tr]); tp = [t for t, _ in tr]
                avg = amt.sum() / sum(a / o[t] for t, a in tr) if len(tr) else np.nan
                ddb = (sum(a * min(0.0, cf[t:e + 1].min() / o[t] - 1) for t, a in tr) / amt.sum()) if len(tr) else np.nan
                rows.append({**base, "方式": m, "狀態": "ok", "起算日": dates[s], "結束日": dates[e],
                             "買進日": ";".join(dates[t] for t in tp), "買進金額": ";".join(f"{a:.4f}" for a in amt),
                             "期末財富": float(V[-1]), "期末現金占比": float(cash_e / V[-1]),
                             "平均成本": float(avg), "觸發日收盤": float(ref), "平均成本對觸發日收盤": float(avg / ref - 1) if len(tr) else np.nan,
                             "買進後最深再跌": float(ddb), "帳面最深": float(min(0.0, V.min() - 1.0))})
    return pd.DataFrame(rows), skipped, len(s40)


def summarize(df):
    S = {}
    ok = df[df["狀態"] == "ok"]
    for hm in HM:
        h = HN[hm]; d = ok[ok["持有"] == h]
        piv = d.pivot(index="段起日d0", columns="方式", values="期末財富")
        cell = {"段數（滿期）": int(piv["E1"].notna().sum()) if "E1" in piv else 0}
        for m in METH:
            if m not in piv:
                continue
            x = d[d["方式"] == m]
            w = x["期末財富"].to_numpy()
            c = {"n": int(len(x)), "期末財富平均（萬）": float(w.mean() * 100), "期末財富中位（萬）": float(np.median(w) * 100),
                 "期末財富最差（萬）": float(w.min() * 100), "期末財富最好（萬）": float(w.max() * 100),
                 "平均成本對觸發日收盤_平均": float(x["平均成本對觸發日收盤"].mean()), "平均成本對觸發日收盤_中位": float(x["平均成本對觸發日收盤"].median()),
                 "買進後最深再跌_中位": float(x["買進後最深再跌"].median()), "買進後最深再跌_最差": float(x["買進後最深再跌"].min()),
                 "帳面最深_中位": float(x["帳面最深"].median()), "帳面最深_最差": float(x["帳面最深"].min()),
                 "期末仍有現金段數（占比＞0.1%）": int((x["期末現金占比"] > 0.001).sum())}
            if m != "E1":
                both = piv[[m, "E1"]].dropna()
                dif = (both[m] - both["E1"]).to_numpy() * 100
                c["對E1差_平均（萬）"] = float(dif.mean()); c["對E1差_中位（萬）"] = float(np.median(dif))
                c["對E1_贏輸平"] = [int((dif > EPS * 100).sum()), int((dif < -EPS * 100).sum()), int((np.abs(dif) <= EPS * 100).sum())]
            cell[m] = c
        full = piv.dropna()
        if len(full):
            best = full.idxmax(axis=1)
            cell["第一名次數（五種都有值的段）"] = {m: int((best == m).sum()) for m in METH}
            cell["第一名_段數"] = int(len(full))
        S[h] = cell
    return S


def fmtw(v):
    return "—" if v is None or not np.isfinite(v) else f"{v:.1f}"


def fmtp(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"


def table(lbl, S, nseg, skipped, note=""):
    L = [f"## {lbl}（≥40 段 {nseg}、有資料 {nseg - len(skipped)}{'；' + note if note else ''}；{DISC}）",
         "方式 | 1年 期末平均/中位（萬） | 1年 對E1 平均差 / 贏輸平 | 3年 期末平均/中位（萬） | 3年 對E1 平均差 / 贏輸平 | 平均成本對觸發日收盤（1年窗，平均） | 買進後最深再跌 中位/最差（1年窗） | 帳面最深 中位/最差（1年窗） | 3年窗 買進後最深再跌 中位/最差"]
    for m in METH:
        a = S.get("1年", {}).get(m); b = S.get("3年", {}).get(m)
        if a is None and b is None:
            continue

        def wcell(c):
            return "—" if c is None else f"{fmtw(c['期末財富平均（萬）'])}/{fmtw(c['期末財富中位（萬）'])} (n{c['n']})"

        def dcell(c):
            if c is None:
                return "—"
            if m == "E1":
                return "基準"
            return f"{c['對E1差_平均（萬）']:+.1f} 萬 / {c['對E1_贏輸平'][0]}-{c['對E1_贏輸平'][1]}-{c['對E1_贏輸平'][2]}"
        L.append(f"{MN[m]} | {wcell(a)} | {dcell(a)} | {wcell(b)} | {dcell(b)} | "
                 f"{fmtp(a['平均成本對觸發日收盤_平均']) if a else '—'} | "
                 f"{(fmtp(a['買進後最深再跌_中位']) + '/' + fmtp(a['買進後最深再跌_最差'])) if a else '—'} | "
                 f"{(fmtp(a['帳面最深_中位']) + '/' + fmtp(a['帳面最深_最差'])) if a else '—'} | "
                 f"{(fmtp(b['買進後最深再跌_中位']) + '/' + fmtp(b['買進後最深再跌_最差'])) if b else '—'}")
    for h in ("1年", "3年"):
        c = S.get(h, {})
        if "第一名次數（五種都有值的段）" in c:
            L.append(f"{h} 第一名次數（{c['第一名_段數']} 段）：" + "、".join(f"{m} {k}" for m, k in c["第一名次數（五種都有值的段）"].items()))
    if skipped:
        L.append(f"無資料的段（標的資料首日之後才有）：{', '.join(skipped)}")
    L.append("")
    return L


def main():
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    vd, vv, vinfo = C.load_vix()
    U = C.load_us(); T = C.load_tw()
    M = U["M"]
    from backtest import researchUSA1_data as A
    Lo, Lc = A.synth(M, "SSO", A.SPREAD)
    XS = [mk_us(U, U["o"], U["cf"], "美股 ^SP500TR"),
          {**T, "label": "台股 0050", "lo": C.TW_SEG0, "d_first": str(T["dates"][0]), "priv": False, "note": ""},
          load_00631L(),
          mk_us(U, M["O"]["SSO"], M["C"]["SSO"], "美股 SSO（真實 2 倍）", note="使用者看過結果前追加；正二含槓桿與每日重設耗損"),
          mk_us(U, Lo, Lc, "美股 合成 SSO（⚠ 合成、非實際 ETF）", note="使用者看過結果前追加；合成（A1 seq3 式）；正二含槓桿與每日重設耗損")]
    res = {"題": "VIX 收盤首次 ≥40 時一筆閒錢怎麼進場（E1～E5）：觸發後 1 年／3 年同一筆本金的期末財富（描述）",
           "聲明": DISC + "；⛔ 不計 N、不判合格", "讀法": "E0～E13 見 researchVIXentry.py docstring", "標的": {}}
    lines = []; allrows = []
    for X in XS:
        df, skipped, nseg = run(X, vd, vv)
        S = summarize(df)
        res["標的"][X["label"]] = {"≥40段數（期間內）": nseg, "無資料段": skipped, "資料首日": X["d_first"], "註": X.get("note", ""),
                                 "彙總": S, **({"資料檢查": X["info"]} if "info" in X else {})}
        lines += table(X["label"], S, nseg, skipped, X.get("note", ""))
        df["私有"] = X["priv"]; allrows.append(df)
    A_ = pd.concat(allrows, ignore_index=True)
    A_.drop(columns=["私有"]).to_csv(os.path.join(WORK, "VIXentry_segments_all.csv"), index=False, encoding="utf-8", float_format="%.6f")
    pub = A_[~A_["私有"]].drop(columns=["私有"])
    pub.to_csv(os.path.join(OUT, "VIXentry_segments_tw.csv"), index=False, encoding="utf-8", float_format="%.4f")
    # 觸發日、E2／E3 日期（VIX 為 FRED 公開；不含價格）
    trig = A_[(A_["方式"] == "E1") & (A_["持有"] == "1年")][["標的", "段起日d0", "段起VIX", "段內最高VIX", "段止日", "E2第二筆依據", "E3回落<30日", "E5的≥30段起日"]]
    trig.to_csv(os.path.join(OUT, "VIXentry_triggers.csv"), index=False, encoding="utf-8")
    res["精簡表"] = lines
    res["資料"] = {"VIX": vinfo, "美股快照": A.data_commit(), "0050": T["info"], "SSO首日": XS[3]["d_first"]}
    res["算於"] = C.now_tpe(); res["秒"] = round(time.time() - T0)
    jdump(res, os.path.join(OUT, "VIXentry.json"))
    open(os.path.join(OUT, "VIXentry_table.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    print(json.dumps(res["標的"]["00631L 元大台灣50正2"]["資料檢查"], ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()

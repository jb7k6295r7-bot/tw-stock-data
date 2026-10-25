# -*- coding: utf-8 -*-
"""美股小部位前瞻簿 v4（依產業線〈大漲主題框架 v4.1〉買賣的前瞻紀錄；BE、LRCX）——回測線程式子代理建，2026-10-25（台北）。

依據：美股策略線登錄 seq3（sha b7d6948dc451af71）＋ seq4（sha 21561951bb6fc473）；規則本身＝產業 v4.1 逐字字串（雜湊 f63147396ffc4ee9），
      本程式與 RULE.md ⛔ 不抄規則。性質：前瞻紀錄；⛔ 不判、不計 N；金額不記（只記「份」）；規則欄＋實際欄兩欄；⚠ v4 是判斷，未經回測。

⭐ 核准閘：APPROVED＝None（裁定尚未核 seq3／seq4）⇒ 一律只乾跑、⛔ 不寫任何檔（book、state、runlog、私有檔都不寫）。
   主 session 收到裁定核准後，把 APPROVED 改成裁定號（例 "seq474"）才開始記。

本程式做的事（⛔ 不自動判加碼或賣出——那些是產業線的新聞判斷；產業寄信 ⇒ 主 session 在下方設定加列）：
  ① 起點：CARDS 各卡起點日（或之後第一個有 K 棒日）美股開盤 1 份（Yahoo 原始 open，只寫私有檔）。
     LINE 推不到 ⇒ 起點順延（裁定 seq472 §二）⇒ 主 session 改 CARDS 的 start。
  ② 加碼／賣出：ADDS／SELLS 設定日（無 K 棒 ⇒ 順延到下一個有 K 棒日）開盤成交；賣出＝賣光該卡規則欄持股。
  ③ 實際欄：使用者回報成交寫在私有檔 ~/us_work/forward_us/v4_user_fills.csv（欄：date,ticker,shares,price；賣出 shares 填負數）；
     repo 只記「實際成交」事件與日期（股數、價格私有）；報表同時列規則欄與實際欄報酬 %。
  ④ 報酬：還原價（× adjclose ÷ close）含息、0.05%／邊（未賣先扣賣出邊）；^SP500TR 同期＝各份「成交日前一交易日收盤 → 資料日收盤
     （已賣：賣出日前一交易日收盤）」按份數平均；賣後回 SPY（登錄 §二.5）＝描述欄：賣出日 SPY 開盤 → 資料日收盤（yahoo_SPY 還原價）。
     每月最後一個美股交易日記「月底淨值」列（登錄 §三）。股息未扣 30% 預扣（結果句註明）。
  ⑤ K1 影子（產業附件〈進場候選 K1 至 K4 判定口徑〉；登錄 §四；⛔ 不影響買賣）：
     K1a＝燈亮月月底收盤 ÷ 6 個月前月底收盤（Adj Close）；K1b＝K1a ÷ 同期 ^SP500TR；K1c＝燈亮月月底收盤 ÷ 含燈亮月在內 24 個月
     （M−23～M）最低月收盤（此窗與產業 56 案 csv 的美股案對得上：LLY、FSLR、ENPH 三案只有此窗相符）。
     燈亮月尚未結束 ⇒ ★ 用開卡前最後一個收盤代替月底（列「K1影子（代替月底）」），燈亮月最後交易日之後再算一次（列「K1影子（月底）」）。

⛔ 私有：repo（book.csv／state.json／runlog.md）只放日期、份數、事件、狀態、報酬 %、K1 比值；
   價格寫 ~/us_work/forward_us/v4_{fills,daily,k1}.csv（repo 外）；使用者回報檔 v4_user_fills.csv 只讀。

用法：
  cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_v4 [--asof YYYY-MM-DD] [--dry]
  資料讀法同 forward_us_smallpos（git fetch 後 git show origin/main:<檔>，⛔ 不動私有庫工作目錄）；--no-fetch／--root（fixture）／--fwd／--priv。
  冪等、只追加；最後一行＝「美股 v4 小部位：…」彙總（排程 log 用）。
"""
from __future__ import annotations

import argparse
import csv
import json
import os

import numpy as np
import pandas as pd

from backtest.forward_us_smallpos import (Src, load_cal, load_px, load_tr, month_ends, now_tpe, pct, read_rows,  # noqa: F401
                                          US_REPO, REPO, nyse_holidays, next_td_pred)

# ═════════════ 設定（主 session 依裁定／產業來信改這裡；每改一次記 runlog 沿革）═════════════
APPROVED = None          # ⭐ 裁定核准 seq3／seq4 後改成裁定號字串（例 "seq474"）；None ⇒ 只乾跑、⛔ 不寫

TAG = "美股小部位 v4 前瞻紀錄（登錄 seq3 sha b7d6948dc451af71＋seq4 sha 21561951bb6fc473；規則＝產業 v4.1 逐字字串 雜湊 f63147396ffc4ee9）"
CARDS = {   # 代號: IB 全名、起點日（美股）、燈亮月、燈亮事件、主題與型別（卡片內容產業記、回測只讀，⛔ 不抄）
    "BE": {"ib": "BLOOM ENERGY CORP（Class A）", "start": "2026-10-26", "light": "2026-10",
           "light_ev": "10/22 第 3 次上修財測", "theme": "產業卡記（產業 seq31；回測只讀）", "type": "新需求",
           "src": "使用者 10/25 10:41 同意（產業 seq31）；登錄 seq4 §五"},
    "LRCX": {"ib": "LAM RESEARCH CORP", "start": "2026-10-26", "light": "2026-10",
             "light_ev": "10/21 季報", "theme": "產業卡記（產業 seq32；回測只讀）", "type": "產業卡記",
             "src": "使用者 10/25 10:42 同意（產業 seq32）；登錄 seq4 §五"},
}
ADDS = {}    # 代號: (日期, 份數, 理由, 出處)  或  [(…), (…)]；產業寄信 ⇒ 主 session 加列
SELLS = {}   # 代號: (日期, 理由, 出處)；賣光該卡規則欄持股
COST = 0.0005                                                  # 0.05%／邊（登錄 §二.8）
FWD = os.path.join(REPO, "backtest", "forward", "us_v4")
PRIV = os.path.expanduser("~/us_work/forward_us")
COLS = ["seq", "ticker", "name", "event", "sched_date", "trade_date", "units", "status", "reason", "source",
        "k1_basis", "k1_month", "k1_close_date", "k1_base_date", "k1a", "k1b", "k1c",
        "ret_rule", "ret_sp500tr", "ret_spy_after", "ret_actual", "note", "recorded_at", "data_commit"]
BUY_EV = ("起點買進", "加碼")
SELL_EV = "賣出"
K1P, K1M = "K1影子（代替月底）", "K1影子（月底）"
NAV_EV = "月底淨值"
USER_EV = "實際成交"
ALL = "全部"


def _adds(t):
    a = ADDS.get(t)
    return [] if not a else ([a] if isinstance(a, tuple) else list(a))


# ═════════════ 讀檔 ═════════════
def load_spy(src):
    d = src.csv("data/macro/yahoo_SPY.csv", dtype={"date": str}).drop_duplicates("date", keep="last")
    d["date"] = pd.to_datetime(d["date"]); d = d.set_index("date").sort_index()
    for c in ("open", "close", "adjclose"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[(d["open"] > 0) & (d["close"] > 0) & (d["adjclose"] > 0)].copy()
    d["aopen"] = d["open"] * d["adjclose"] / d["close"]; d["aclose"] = d["adjclose"]
    return d[["aopen", "aclose"]]


def load_user_fills(priv):
    fp = os.path.join(priv, "v4_user_fills.csv")
    if not os.path.exists(fp):
        return []
    out = []
    for i, r in enumerate(read_rows(fp)):
        try:
            out.append({"i": i, "date": pd.Timestamp(r["date"]), "ticker": r["ticker"].strip().upper(),
                        "shares": float(r["shares"]), "price": float(r["price"])})
        except (KeyError, ValueError, TypeError):
            continue
    return out


def last_le(s, d):
    x = s[s.index <= d]
    return (x.index[-1], float(x.iloc[-1])) if len(x) else (None, np.nan)


def last_lt(s, d):
    x = s[s.index < d]
    return (x.index[-1], float(x.iloc[-1])) if len(x) else (None, np.nan)


# ═════════════ K1 ═════════════
def k1(aclose, tr, M, close_date):
    """M＝燈亮月 Period；close_date＝當作「燈亮月月底」的收盤日（月底或代替日）。回比值與私有細項。"""
    a = aclose[aclose.index <= close_date]
    cd, c = last_le(a, close_date)
    mc = a.groupby(a.index.to_period("M")).last()
    mdt = a.index.to_series().groupby(a.index.to_period("M")).last()
    base_m = M - 6
    if cd is None or base_m not in mc.index:
        return None
    b0 = float(mc[base_m]); bd = mdt[base_m]
    win = mc[(mc.index >= M - 23) & (mc.index <= M - 1)]
    lo = min(list(win.to_numpy(float)) + [c])
    _, tr1 = last_le(tr, cd); _, tr0 = last_le(tr, bd)
    ka = c / b0
    kb = ka / (tr1 / tr0) if np.isfinite(tr1) and np.isfinite(tr0) else np.nan
    return {"k1a": ka, "k1b": kb, "k1c": c / lo, "close_date": cd, "base_date": bd, "close": c, "base": b0,
            "min24": lo, "tr_close": tr1, "tr_base": tr0, "n_win": len(win) + 1}


# ═════════════ 主步驟（⛔ 不改舊列）═════════════
def step(rows, D, cal, PX, tr, spy, commit, now, ufills):
    new, nfill, k1priv, log = [], {}, [], []
    rec = now.strftime("%Y-%m-%d %H:%M:%S")

    def allr():
        return rows + new

    def mine(t, ev):
        evs = ev if isinstance(ev, tuple) else (ev,)
        return [r for r in allr() if r["ticker"] == t and r["event"] in evs]

    def add(t, ev, **kw):
        r = {c: "" for c in COLS}
        r.update(seq=str(len(rows) + len(new) + 1), ticker=t, name=CARDS[t]["ib"] if t in CARDS else t, event=ev,
                 recorded_at=rec, data_commit=commit[:10])
        r.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
        new.append(r); return r

    def trade_day(t, sched):
        """sched 起第一個有 K 棒的日（≤ D）；回（日, 順延跳過的日）。"""
        skipped = []
        for d in cal[cal >= pd.Timestamp(sched)]:
            if d in PX[t].index:
                return d, skipped
            skipped.append(str(d.date()))
        return None, skipped

    def fill(t, ev, sched, units, **kw):
        d, sk = trade_day(t, sched)
        if d is None:
            return None
        note = kw.pop("note", "")
        if sk:
            note = (note + "；" if note else "") + f"順延：{'、'.join(sk)} 無 K 棒"
        r = add(t, ev, sched_date=sched, trade_date=d.date(), units=units, status="成交", note=note, **kw)
        nfill[r["seq"]] = (float(PX[t].at[d, "open"]), str(d.date()), t, ev)
        return r

    for t, c in CARDS.items():
        px = PX[t]
        S = pd.Timestamp(c["start"])
        M = pd.Period(c["light"], "M")
        # ⑤ K1 影子：代替月底（開卡前最後一個收盤）
        if not mine(t, K1P):
            pre = px.index[(px.index < S) & (px.index <= D)]
            if len(pre) and next_td_pred(pre[-1]) >= S:          # 開卡前最後一個收盤（下一交易日已是起點）
                k = k1(px["aclose"], tr, M, pre[-1])
                if k:
                    add(t, K1P, k1_basis="★ 燈亮月未結束 ⇒ 用開卡前最後一個收盤代替月底", k1_month=str(M),
                        k1_close_date=k["close_date"].date(), k1_base_date=k["base_date"].date(),
                        k1a=f"{k['k1a']:.3f}", k1b=f"{k['k1b']:.3f}", k1c=f"{k['k1c']:.3f}",
                        reason=f"燈亮：{c['light_ev']}", note="只記影子、⛔ 不影響買賣；燈亮月結束後另記「K1影子（月底）」")
                    k1priv.append((t, K1P, k))
        # ⑤' K1 影子：燈亮月月底
        if not mine(t, K1M):
            me = [d for d in month_ends(cal, D) if d.to_period("M") == M]
            if me:
                k = k1(px["aclose"], tr, M, me[0])
                if k:
                    add(t, K1M, k1_basis="燈亮月最後一個美股交易日收盤", k1_month=str(M),
                        k1_close_date=k["close_date"].date(), k1_base_date=k["base_date"].date(),
                        k1a=f"{k['k1a']:.3f}", k1b=f"{k['k1b']:.3f}", k1c=f"{k['k1c']:.3f}",
                        reason=f"燈亮：{c['light_ev']}", note="只記影子、⛔ 不影響買賣")
                    k1priv.append((t, K1M, k))
        # ① 起點
        if not mine(t, "起點買進"):
            fill(t, "起點買進", c["start"], 1, reason=f"起點 1 份（{c['type']}）", source=c["src"],
                 note=f"Yahoo open；資料日 {D.date()} 記")
        started = bool(mine(t, "起點買進"))
        sold = mine(t, SELL_EV)
        # ② 加碼（設定列；已記過的同日同份數同理由不重記）
        for (sd, u, why, srcs) in _adds(t):
            if any(r["sched_date"] == str(pd.Timestamp(sd).date()) and r["units"] == str(int(u)) and r["reason"] == why
                   for r in mine(t, "加碼")):
                continue
            if sold and pd.Timestamp(sd) >= pd.Timestamp(sold[0]["trade_date"]):
                log.append(f"{t} 加碼 {sd} 在賣出後、未記（v4 新買請開新卡）"); continue
            if not started:
                log.append(f"{t} 加碼 {sd} 但起點尚未成交、暫不記"); continue
            fill(t, "加碼", str(pd.Timestamp(sd).date()), int(u), reason=why, source=srcs)
        # ③ 賣出（賣光規則欄持股）
        if t in SELLS and not sold and started:
            sd, why, srcs = SELLS[t]
            held = sum(int(r["units"] or 0) for r in mine(t, BUY_EV) if r["status"] == "成交" and pd.Timestamp(r["trade_date"]) <= pd.Timestamp(sd))
            fill(t, SELL_EV, str(pd.Timestamp(sd).date()), -held, reason=why, source=srcs, note="賣後錢回 SPY（登錄 §二.5，描述欄）")
        # 實際欄事件（股數、價格私有）
        k_seen = {(r["trade_date"], r["note"]) for r in mine(t, USER_EV)}
        for f in [f for f in ufills if f["ticker"] == t and f["date"] <= D]:
            key = (str(f["date"].date()), f"使用者回報第 {f['i'] + 1} 筆（股數、價格私有）")
            if key not in k_seen:
                add(t, USER_EV, trade_date=key[0], status="買進" if f["shares"] > 0 else "賣出", note=key[1])
    # ④ 月底淨值（每月最後一個美股交易日；記當時資料下的值、之後不改）
    for me in month_ends(cal, D):
        for t in list(CARDS) + [ALL]:
            if any(r["ticker"] == t and r["event"] == NAV_EV and r["trade_date"] == str(me.date()) for r in allr()):
                continue
            per, port, _ = value(allr(), me, PX, tr, spy, ufills)
            p = port if t == ALL else per.get(t, {})
            if not p.get("_u"):
                continue
            add(t, NAV_EV, trade_date=me.date(), units=p.get("份數", ""), status="持有中" if p.get("份數") else "已賣",
                ret_rule=pct(p.get("累計報酬")), ret_sp500tr=pct(p.get("^SP500TR同期")), ret_spy_after=pct(p.get("賣後回SPY")),
                ret_actual=pct(p.get("實際報酬")), note="規則欄每份等額；股息未扣 30% 預扣")
    return new, nfill, k1priv, log


def value(rows, X, PX, tr, spy, ufills):
    """X 當日（含）為止。回 {代號: dict}、全部 dict、私有逐日 ratio。"""
    per, lots_all = {}, []
    trX = tr[tr.index <= X]
    tu = 0
    for t in CARDS:
        px = PX[t][PX[t].index <= X]
        lots = [r for r in rows if r["ticker"] == t and r["event"] in BUY_EV and r["status"] == "成交" and pd.Timestamp(r["trade_date"]) <= X]
        sell = next((r for r in rows if r["ticker"] == t and r["event"] == SELL_EV and r["status"] == "成交" and pd.Timestamp(r["trade_date"]) <= X), None)
        u = sum(int(r["units"]) for r in lots)
        p = {"份數": 0}
        if u and len(px):
            sd = pd.Timestamp(sell["trade_date"]) if sell else None
            ex = float(px.at[sd, "aopen"]) if sd is not None else float(px["aclose"].iloc[-1])
            trx = last_lt(trX, sd)[1] if sd is not None else float(trX.iloc[-1])
            rs = bs = 0.0
            for r in lots:
                d = pd.Timestamp(r["trade_date"]); w = int(r["units"]); e = float(px.at[d, "aopen"])
                rs += w * (ex / e - 1 - 2 * COST)
                bs += w * (trx / last_lt(trX, d)[1] - 1)
                v = px["aclose"][px.index >= d] / e * w
                if sd is not None:
                    v = v[v.index < sd].reindex(px.index[px.index >= d]).fillna(ex / e * w)
                lots_all.append((v, pd.Series(float(w), index=v.index)))
            p = {"份數": 0 if sell else u, "累計報酬": rs / u, "^SP500TR同期": bs / u, "_rs": rs, "_bs": bs, "_u": u}
            if sd is not None and spy is not None:
                s = spy[(spy.index >= sd) & (spy.index <= X)]
                if len(s):
                    p["賣後回SPY"] = float(s["aclose"].iloc[-1]) / float(s["aopen"].iloc[0]) - 1
            tu += u
        # 實際欄（使用者回報；還原價口徑、0.05%／邊）
        uf = [f for f in ufills if f["ticker"] == t and f["date"] <= X]
        if uf and len(px):
            inv = proc = held = 0.0
            for f in uf:
                kd = PX[t].index[PX[t].index <= f["date"]]
                k = float(PX[t].at[kd[-1], "adjclose"] / PX[t].at[kd[-1], "close"]) if len(kd) else 1.0
                if f["shares"] > 0:
                    inv += f["shares"] * f["price"] * k * (1 + COST)
                else:
                    proc += -f["shares"] * f["price"] * k * (1 - COST)
                held += f["shares"]
            if inv > 0:
                p["實際報酬"] = (proc + max(held, 0) * float(px["aclose"].iloc[-1]) * (1 - COST)) / inv - 1
                p["實際持股"] = "有" if held > 0 else "無"
        per[t] = p
    port = {"份數": sum(p["份數"] for p in per.values()), "_u": tu}
    if tu:
        port["累計報酬"] = sum(p.get("_rs", 0) for p in per.values()) / tu
        port["^SP500TR同期"] = sum(p.get("_bs", 0) for p in per.values()) / tu
        idx = sorted(set().union(*[v.index for v, _ in lots_all]))
        V = sum(v.reindex(idx).fillna(0) for v, _ in lots_all); I_ = sum(i.reindex(idx).fillna(0) for _, i in lots_all)
        ratio = (V / I_).dropna()
        port["最大回落"] = float((ratio / ratio.cummax() - 1).min()) if len(ratio) else np.nan
        port["_ratio"] = ratio
    return per, port, None


# ═════════════ 主流程 ═════════════
def run(src, fwd=FWD, priv=PRIV, asof=None, dry=False, now=None, quiet=False, approved="__const__"):
    approved = APPROVED if approved == "__const__" else approved
    now = now if now is not None else now_tpe()
    P = (lambda *a: None) if quiet else print
    gate = approved is None
    if gate:
        dry = True
    PX = {t: load_px(src, t) for t in CARDS}
    D = min(px.index[-1] for px in PX.values())
    if asof:
        D = min(D, pd.Timestamp(asof))
    cal = load_cal(src, [px.index for px in PX.values()])
    cal = cal[cal <= D]
    tr = load_tr(src)
    spy = load_spy(src)
    commit = src.commit()
    ufills = load_user_fills(priv)
    fp = os.path.join(fwd, "book.csv")
    rows = read_rows(fp)
    new, nfill, k1priv, log = step(rows, D, cal, PX, tr, spy, commit, now, ufills)
    allrows = rows + new
    per, port, _ = value(allrows, D, PX, tr, spy, ufills)
    st = {"件": TAG, "核准": approved or "未核（只乾跑）", "資料日": str(D.date()), "資料commit": commit,
          "寫入時間（台北）": now.strftime("%Y-%m-%d %H:%M"), "卡": {}}
    parts = []
    for t, c in CARDS.items():
        mr = [r for r in allrows if r["ticker"] == t]
        b0 = next((r for r in mr if r["event"] == "起點買進"), None)
        kp = next((r for r in mr if r["event"] == K1P), None); km = next((r for r in mr if r["event"] == K1M), None)
        p = per.get(t, {})
        status = ("已賣（規則欄）" if any(r["event"] == SELL_EV for r in mr) else "持有中（規則欄）" if b0
                  else f"資料未到起點（起點 {c['start']}）")
        kk = km or kp
        ktxt = (f"K1{'' if km else '★'} a{kk['k1a']}／b{kk['k1b']}／c{kk['k1c']}" if kk else "K1 未算")
        st["卡"][t] = {"IB 全名": c["ib"], "起點": c["start"], "燈亮月": c["light"], "型別": c["type"], "狀態": status,
                      "份數": p.get("份數", 0), "起點成交": f"{b0['trade_date']} {b0['status']}" if b0 else "未記",
                      "加碼次數": sum(1 for r in mr if r["event"] == "加碼"),
                      "規則欄累計報酬": pct(p.get("累計報酬")), "^SP500TR同期": pct(p.get("^SP500TR同期")),
                      "賣後回SPY（描述）": pct(p.get("賣後回SPY")),
                      "實際欄": (f"{pct(p.get('實際報酬'))}（持股{p.get('實際持股')}）" if "實際報酬" in p else "未回報"),
                      "K1影子（代替月底）": ({k: kp[k] for k in ("k1_close_date", "k1a", "k1b", "k1c")} if kp else None),
                      "K1影子（月底）": ({k: km[k] for k in ("k1_close_date", "k1a", "k1b", "k1c")} if km else None)}
        parts.append(f"{t} {status} {p.get('份數', 0)} 份"
                     + (f" 規則 {pct(p.get('累計報酬'))}（^SP500TR {pct(p.get('^SP500TR同期'))}）" if p.get("_u") else "")
                     + (f" 實際 {pct(p.get('實際報酬'))}" if "實際報酬" in p else "") + f"｜{ktxt}")
    st["全部（規則欄）"] = {k: (pct(v) if k in ("累計報酬", "^SP500TR同期", "最大回落") else v) for k, v in port.items() if not k.startswith("_")}
    summ = (f"美股 v4 小部位：資料日 {D.date()}｜資料 {commit[:10]}｜"
            + (f"核准 {approved}" if not gate else "未核（APPROVED=None）⇒ 只乾跑、不寫")
            + f"｜新增 {len(new)} 列｜" + "；".join(parts)
            + (f"｜全部照規則 {pct(port.get('累計報酬'))}、^SP500TR {pct(port.get('^SP500TR同期'))}" if port.get("_u") else "")
            + ("｜⚠ " + "；".join(log) if log else "") + ("｜乾跑（未寫檔）" if dry and not gate else ""))
    if not dry:
        os.makedirs(fwd, exist_ok=True); os.makedirs(priv, exist_ok=True)
        if new or not os.path.exists(fp):
            with open(fp, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(allrows)
        if nfill:
            ffp = os.path.join(priv, "v4_fills.csv"); hdr = not os.path.exists(ffp)
            with open(ffp, "a", encoding="utf-8-sig" if hdr else "utf-8", newline="") as f:
                w = csv.writer(f)
                if hdr:
                    w.writerow(["seq", "ticker", "event", "trade_date", "yahoo_open_raw", "recorded_at"])
                for s, (o, d, t, e) in nfill.items():
                    w.writerow([s, t, e, d, repr(o), now.strftime("%Y-%m-%d %H:%M:%S")])
        if k1priv:
            kfp = os.path.join(priv, "v4_k1.csv"); hdr = not os.path.exists(kfp)
            with open(kfp, "a", encoding="utf-8-sig" if hdr else "utf-8", newline="") as f:
                w = csv.writer(f)
                if hdr:
                    w.writerow(["ticker", "event", "close_date", "close_adj", "base_date", "base_adj", "min24_adj", "n_months",
                                "sp500tr_close", "sp500tr_base", "k1a", "k1b", "k1c", "recorded_at"])
                for t, e, k in k1priv:
                    w.writerow([t, e, k["close_date"].date(), repr(k["close"]), k["base_date"].date(), repr(k["base"]), repr(k["min24"]),
                                k["n_win"], repr(k["tr_close"]), repr(k["tr_base"]), repr(k["k1a"]), repr(k["k1b"]), repr(k["k1c"]),
                                now.strftime("%Y-%m-%d %H:%M:%S")])
        dd = []
        for t, c in CARDS.items():
            x = PX[t][PX[t].index <= D][["open", "close", "adjclose", "aopen", "aclose"]].copy(); x["ticker"] = t
            dd.append(x[x.index >= pd.Timestamp(c["start"])])
        x = pd.concat(dd)
        if len(x):
            if "_ratio" in port:
                x["port_value_over_invested"] = port["_ratio"].reindex(x.index).to_numpy()
            x["SP500TR"] = tr.reindex(x.index).to_numpy()
            x.to_csv(os.path.join(priv, "v4_daily.csv"), index_label="date", float_format="%.10g")
        sp = os.path.join(fwd, "state.json")
        old = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
        json.dump(st, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if new or log or old.get("資料日") != st["資料日"]:
            with open(os.path.join(fwd, "runlog.md"), "a", encoding="utf-8") as f:
                f.write(f"- {now.strftime('%Y-%m-%d %H:%M')}（台北）｜核准 {approved}｜資料 {commit[:10]}（資料日 {D.date()}）｜新增 {len(new)} 列"
                        + ("：" + "、".join(f"{r['ticker']} {r['event']} {r['status'] or ('a' + r['k1a'] + '／b' + r['k1b'] + '／c' + r['k1c'])}" for r in new) if new else "")
                        + (f"｜全部照規則 {pct(port.get('累計報酬'))}、最大回落 {pct(port.get('最大回落'))}、^SP500TR {pct(port.get('^SP500TR同期'))}" if port.get("_u") else "")
                        + ("｜⚠ " + "；".join(log) if log else "") + "\n")
    else:
        for r in new:
            P("（乾跑新列）" + "｜".join(f"{k}={r[k]}" for k in COLS if r[k] and k not in ("recorded_at", "data_commit")))
    P(summ)
    return {"D": D, "new": new, "state": st, "log": log, "rows": allrows, "summary": summ, "nfill": nfill, "k1priv": k1priv,
            "dry": dry, "per": per, "port": port}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof"); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--root", help="改讀一般資料夾（fixture）"); ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--no-fetch", action="store_true"); ap.add_argument("--fwd", default=FWD); ap.add_argument("--priv", default=PRIV)
    a = ap.parse_args()
    src = Src(a.root, None) if a.root else Src(US_REPO, a.ref, fetch=not a.no_fetch)
    try:
        run(src, a.fwd, a.priv, a.asof, a.dry)
    except Exception as e:                                                          # 排程：失敗印一行、exit 1
        print(f"美股 v4 小部位：失敗 {type(e).__name__}: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

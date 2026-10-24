# -*- coding: utf-8 -*-
"""美股長線候選「確認前先小部位」前瞻紀錄簿（ETN＝Eaton）——回測線計算子代理建，2026-10-24（台北）。

依據：登錄全文 seq2 定版（sha f15b918fa43f360f；seq1 c1db5cf2088ac1a6 內容裁定 seq461 §四 核；起點改 2026-10-23（五）美股開盤，裁定 seq462 §一）。
性質：前瞻紀錄；⛔ 不判、不計 N；金額不記（股數用「份」）；LINE 只推事件行。規則全文見 backtest/forward/us_smallpos/RULE.md（⛔ 之後不改）。

規則（照登錄）：
  起點：ETN 1 份 ＝ 2026-10-23 美股開盤（原始開盤價）。
  轉強 ＝ 甲 或 乙（SEC 10-Q／10-K 季營收，第一次公布值、可用日 ＝ first_filed）：
    甲 最新一季營收年增率 ≥ 前 4 季合計營收年增率 ＋ 5 個百分點
    乙 最新一季營收首次創 8 季（2 年）新高
  每月最後一個美股交易日判「當月新可用的季報」⇒ 轉強 ⇒ 次一交易日開盤加 2 份（只加一次）；當月沒有新季報 ⇒ 不判（不算未轉強）。
  放棄：起點後第 1～4 份新季報都沒判轉強 ⇒ 第 4 份那次月底判定後、次一交易日開盤賣出、記「未確認」。
  起點前最近一份已可用季報已達轉強 ⇒ 標「進場時已轉強」（檢查時不當確認前樣本）；起點後第 1 份新季報仍轉強即加 2 份。

讀法（執行者定，寫進 RULE.md「讀法」節）：
  R1 甲「前 4 季合計年增率」＝ 近 4 季（含最新一季）合計 ÷ 再前 4 季合計 − 1（對應台股「近 3 月 ≥ 前 12 月」的實作＝近 12 月含近 3 月）；
     另算「不含最新一季」讀法，只寫私有檔；兩讀法甲結果不同 ⇒ 公開列註「讀法敏感」（不改判定）。
  R2 乙 8 季新高 ＝ 最新一季 ≥ 前 8 季最大且前 8 季全有值；首次 ＝ 上一季不是 8 季新高（上一季無法判 ⇒ 當作「沒創」，同台股 T(NaN)＝False）。
  R3 新季報 ＝ first_filed ≥ 起點日的季（起點日當天申報算起點後）；起點前最近一份 ＝ first_filed < 起點日的最新一季。
     月底判定看 first_filed ≤ 該月最後交易日、尚未判過的起點後季報（通常一份）。
  R4 資料晚到：季營收檔每週更新 ⇒ first_filed 落在已判「不判」的月份、之後才進庫 ⇒ 進庫那個資料日補判（列寫「補判（資料晚到）」），
     次一交易日開盤成交（照規則本應是該月底次一交易日，照實註明）。
  R5 月底：資料日曆（^GSPC ∪ 候選日線）已有下個月的日子 ⇒ 該月最後一個資料日；資料日本身是否月底 ⇒ 用 NYSE 休市規則外推下一交易日是否跨月。
  R6 成交價：Yahoo 日線 open（Yahoo 口徑已按日後拆股調整；ETN 起點後無拆股則 ＝ 原始）；當日無 K 棒 ⇒ 買進記「買不到」（算這一次）、賣出順延。
  R7 報酬（照規則欄、每份等額）：還原價（× adjclose ÷ close）、含息；每份扣 0.05%／邊（買、賣各一次；未賣者也先扣賣出邊，同台股作法）。
     最大回落 ＝ 每日 市值÷投入（未扣成本）。^SP500TR 同期 ＝ 各份「成交日前一交易日收盤 → 資料日收盤（已賣：賣出日前一交易日收盤）」按份數平均。
  R8 資料日 D ＝ 候選日線最後一日（各檔取最小；--asof 再截）；季營收只取 first_filed ≤ D。

⛔ 私有：book.csv／state.json／runlog.md（repo）只放事件（日期、份數、判定、狀態）與彙總報酬（%）；
   價格、營收值、年增率數字只寫 ~/us_work/forward_us/smallpos_{daily,rev,fills}.csv（repo 外）。

用法：
  cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_smallpos [--asof YYYY-MM-DD] [--dry] [--line-out 檔]
  預設：git -C ~/us-stock-data fetch origin main 後用 git show origin/main:<檔> 讀（⛔ 不動私有庫工作目錄）；--no-fetch 不 fetch；
  --root 目錄 ＝ 改讀一般資料夾（自測 fixture 用）；--fwd／--priv 改紀錄夾（自測用）。
  輸出：事件行（行首「美股小部位：」，同一資料日重跑原樣再印）；最後一行 ＝ 一行彙總（行首「美股小部位前瞻：」）給排程 log。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

TAG = "美股長線候選「確認前先小部位」前瞻紀錄 seq2 定版（sha f15b918fa43f360f；裁定 seq461 §四、seq462 §一）"
CANDS = {"ETN": {"name": "Eaton", "start": "2026-10-23"}}     # 增減照產業分析線來信、本線記沿革後改這裡
N_REPORTS, ADD_UNITS, COST = 4, 2, 0.0005                      # 第 4 份新季報放棄；加 2 份；0.05%／邊
UP_PP = 0.05                                                   # 甲：＋5 個百分點
NH_Q = 8                                                       # 乙：8 季新高
US_REPO = os.path.expanduser("~/us-stock-data")
REPO = os.path.expanduser("~/tw-p17")
FWD = os.path.join(REPO, "backtest", "forward", "us_smallpos")
PRIV = os.path.expanduser("~/us_work/forward_us")
COLS = ["seq", "ticker", "name", "event", "trade_date", "units", "status", "judge_date", "report_q", "report_filed",
        "report_n", "judge", "judge_detail", "note", "recorded_at", "data_commit"]
BUY_EV = ("起點買進", "轉強加碼")
SELL_EV = "放棄賣出"
JUDGE_EV = ("月底判定", "補判（資料晚到）")
NOJUDGE = "不判（當月無新季報）"
WD = "一二三四五六日"


# ═════════════ 讀檔 ═════════════
class Src:
    """root＝資料夾；ref 給定 ⇒ git show ref:path（⛔ 不動工作目錄）。"""
    def __init__(self, root=US_REPO, ref=None, fetch=False):
        self.root, self.ref = root, ref
        if ref and fetch:
            r = subprocess.run(["git", "-C", root, "fetch", "-q", "origin", "main"], capture_output=True, text=True)
            if r.returncode:
                print(f"⚠ git fetch 失敗（用本機現有 {ref}）：{r.stderr.strip()[-200:]}")

    def text(self, rel):
        if self.ref:
            r = subprocess.run(["git", "-C", self.root, "show", f"{self.ref}:{rel}"], capture_output=True)
            if r.returncode:
                raise FileNotFoundError(f"{self.ref}:{rel}")
            return r.stdout.decode("utf-8")
        return io.open(os.path.join(self.root, rel), encoding="utf-8").read()

    def csv(self, rel, **kw):
        return pd.read_csv(io.StringIO(self.text(rel)), **kw)

    def commit(self):
        if self.ref:
            return subprocess.run(["git", "-C", self.root, "rev-parse", self.ref], capture_output=True, text=True).stdout.strip()
        p = os.path.join(self.root, ".commit")
        return io.open(p, encoding="utf-8").read().strip() if os.path.exists(p) else "fixture"


def load_px(src, t):
    d = src.csv(f"data/prices_yahoo/{t}.csv", dtype={"date": str})
    d = d.drop_duplicates("date", keep="last")
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date").sort_index()
    for c in ("open", "close", "adjclose"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[(d["open"] > 0) & (d["close"] > 0) & (d["adjclose"] > 0)].copy()
    k = d["adjclose"] / d["close"]
    d["aopen"], d["aclose"] = d["open"] * k, d["adjclose"]
    return d[["open", "close", "adjclose", "aopen", "aclose"]]


def load_cal(src, extra):
    g = src.csv("data/macro/yahoo_GSPC.csv", usecols=["date"], dtype=str)["date"]
    s = set(pd.to_datetime(g))
    for x in extra:
        s |= set(x)
    return pd.DatetimeIndex(sorted(s))


def load_tr(src):
    d = src.csv("data/macro/yahoo_SP500TR.csv", usecols=["date", "adjclose"], dtype={"date": str}).drop_duplicates("date", keep="last")
    s = pd.Series(pd.to_numeric(d["adjclose"], errors="coerce").to_numpy(float), index=pd.to_datetime(d["date"])).sort_index()
    return s[s > 0]


def load_rev(src, tickers):
    q = src.csv("data/fundamentals/quarterly_revenue.csv", dtype={"ticker": str, "first_form": str})
    q = q[q["ticker"].isin(tickers)].copy()
    q["period_end"] = pd.to_datetime(q["period_end"]); q["first_filed"] = pd.to_datetime(q["first_filed"])
    q["value"] = pd.to_numeric(q["value"], errors="coerce")       # ⛔ 不讀 latest_value
    q["q"] = q["period_end"].dt.to_period("Q")
    q = q.sort_values(["ticker", "q", "first_filed"]).drop_duplicates(["ticker", "q"], keep="first")
    return {t: g.set_index("q").sort_index() for t, g in q.groupby("ticker")}


# ═════════════ 日曆（NYSE 休市規則，只用來外推「資料日是不是月底」）═════════════
def _easter(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451; mo = (h + l_ - 7 * m + 114) // 31; da = (h + l_ - 7 * m + 114) % 31 + 1
    return dt.date(y, mo, da)


def _nth_wd(y, m, wd, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _last_wd(y, m, wd):
    d = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)


def nyse_holidays(y):
    def obs(d):
        return d - dt.timedelta(days=1) if d.weekday() == 5 else d + dt.timedelta(days=1) if d.weekday() == 6 else d
    H = set()
    nd = dt.date(y, 1, 1)
    if nd.weekday() == 6:
        H.add(dt.date(y, 1, 2))
    elif nd.weekday() < 5:
        H.add(nd)                                                  # 週六元旦 ⇒ 不補（NYSE 規則）
    H |= {_nth_wd(y, 1, 0, 3), _nth_wd(y, 2, 0, 3), _easter(y) - dt.timedelta(days=2), _last_wd(y, 5, 0),
          obs(dt.date(y, 7, 4)), _nth_wd(y, 9, 0, 1), _nth_wd(y, 11, 3, 4), obs(dt.date(y, 12, 25))}
    if y >= 2022:
        H.add(obs(dt.date(y, 6, 19)))
    return H


def next_td_pred(d):
    d = pd.Timestamp(d).date() + dt.timedelta(days=1)
    while d.weekday() >= 5 or d in nyse_holidays(d.year):
        d += dt.timedelta(days=1)
    return pd.Timestamp(d)


def month_ends(cal, D):
    """cal（≤ D）裡的每月最後交易日；D 本身 ⇒ 用休市規則外推下一交易日是否跨月。"""
    out = []
    for i, d in enumerate(cal):
        nxt = cal[i + 1] if i + 1 < len(cal) else (next_td_pred(d) if d == D else None)
        if nxt is not None and (nxt.year, nxt.month) != (d.year, d.month):
            out.append(d)
    return out


# ═════════════ 轉強判定 ═════════════
def metrics(R, q):
    """R ＝ 該檔季營收（index＝季 Period，value＝第一次公布）；回甲乙與私有數字。"""
    v = R["value"].where(R["value"] > 0)

    def val(k):
        x = v.get(q - k, np.nan)
        return float(x) if pd.notna(x) else np.nan

    def ssum(a, b):
        xs = [val(k) for k in range(a, b + 1)]
        return sum(xs) if all(np.isfinite(xs)) else np.nan

    def nh(k):
        cur = val(k); h = [val(j) for j in range(k + 1, k + NH_Q + 1)]
        return bool(cur >= max(h)) if (np.isfinite(cur) and all(np.isfinite(h))) else None
    yq = val(0) / val(4) - 1 if np.isfinite(val(0)) and np.isfinite(val(4)) else np.nan
    ttm = ssum(0, 3) / ssum(4, 7) - 1
    alt = ssum(1, 4) / ssum(5, 8) - 1
    A = bool(np.isfinite(yq) and np.isfinite(ttm) and yq >= ttm + UP_PP - 1e-12)
    A_alt = bool(np.isfinite(yq) and np.isfinite(alt) and yq >= alt + UP_PP - 1e-12)
    n0, n1 = nh(0), nh(1)
    B = bool(n0 is True and n1 is not True)
    return {"q": str(q), "value": val(0), "yoy_q": yq, "yoy_ttm": ttm, "yoy_ttm_alt": alt, "A": A, "A_alt": A_alt,
            "A_ok": bool(np.isfinite(yq) and np.isfinite(ttm)), "nh8": n0, "nh8_prev": n1, "B": B, "up": A or B}


def detail(m):
    a = ("成立" if m["A"] else "不成立") if m["A_ok"] else "無法判（缺季）"
    nh = {True: "是", False: "否", None: "無法判"}
    b = "成立" if m["B"] else "不成立"
    s = f"甲 {a}｜乙 {b}（本季 8 季新高：{nh[m['nh8']]}；上一季 8 季新高：{nh[m['nh8_prev']]}）"
    return s


def note_sens(m):
    return "；讀法敏感（甲改用「前 4 季不含最新一季」結果不同，不改判定）" if m["A_ok"] and m["A"] != m["A_alt"] else ""


# ═════════════ 紀錄 ═════════════
def read_rows(fp):
    if not os.path.exists(fp):
        return []
    return list(csv.DictReader(open(fp, encoding="utf-8-sig")))


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").tz_localize(None)


def step(rows, D, cal, PX, REV, commit, now, fills):
    """回（新列, 新成交價{seq: (raw open, 日期)}, 補判差異 log）。⛔ 不改舊列。"""
    new, nfill, log = [], {}, []
    rec = now.strftime("%Y-%m-%d %H:%M:%S")
    allr = lambda: rows + new                                                    # noqa: E731

    def mine(t, ev=None):
        return [r for r in allr() if r["ticker"] == t and (ev is None or r["event"] == ev or (isinstance(ev, tuple) and r["event"] in ev))]

    def add(t, ev, **kw):
        r = {c: "" for c in COLS}
        r.update(seq=str(len(rows) + len(new) + 1), ticker=t, name=CANDS[t]["name"], event=ev, recorded_at=rec, data_commit=commit[:10])
        r.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
        new.append(r); return r

    def fill(t, ev, d, units, **kw):
        px = PX[t]
        if d in px.index:
            r = add(t, ev, trade_date=d.date(), units=units, status="成交", **kw)
            nfill[r["seq"]] = (float(px.at[d, "open"]), str(d.date()), t, ev)
        else:
            add(t, ev, trade_date=d.date(), units=0, status="買不到（當日無 K 棒）", **kw)

    MEs = month_ends(cal, D)
    for t, c in CANDS.items():
        S = pd.Timestamp(c["start"]); px = PX[t]; R = REV.get(t)
        R = R[R["first_filed"] <= D] if R is not None else None
        # ① 起點
        d0 = cal[cal >= S]
        if len(d0) and not mine(t, "起點買進"):
            fill(t, "起點買進", d0[0], 1, note=f"補記：起點 {c['start']} 美股開盤 1 份（Yahoo open）；資料日 {D.date()} 晚補記")
        if len(d0) and not mine(t, "進場檢查"):
            pre = R[R["first_filed"] < S] if R is not None else None
            if pre is None or pre.empty:
                add(t, "進場檢查", judge="無法判（起點前無季報）", note="查無起點前已可用季報")
            else:
                q = pre.index[-1]; m = metrics(R[R["first_filed"] < S], q)
                add(t, "進場檢查", report_q=str(q), report_filed=pre.at[q, "first_filed"].date(),
                    judge="進場時已轉強" if m["up"] else "進場時未轉強", judge_detail=detail(m),
                    note=("⇒ 檢查時另標、不當「確認前」樣本；起點後第 1 份新季報仍轉強即加 2 份" if m["up"] else "起點前最近一份季報未達轉強")
                    + note_sens(m))
        if not len(d0):
            continue
        # ② 判定（月底；資料晚到補判）
        def state():
            js = mine(t, JUDGE_EV)
            done = any(r["judge"] == "轉強" for r in js) or any("放棄判定" in r["note"] for r in js)
            judged = {r["report_q"] for r in js if r["report_q"]}
            n = sum(1 for r in js if r["report_q"])
            return js, done, judged, n

        def judge_q(q, jd, ev, extra=""):
            js, done, judged, n = state()
            i = n + 1
            m = metrics(R[R["first_filed"] <= jd], q)
            note = f"第 {i} 份新季報" + extra + note_sens(m)
            if not m["up"] and i >= N_REPORTS:
                note += f"；放棄判定（第 {N_REPORTS} 份新季報仍未轉強 ⇒ 次一交易日開盤賣、記未確認）"
            add(t, ev, judge_date=jd.date(), report_q=str(q), report_filed=R.at[q, "first_filed"].date(), report_n=i,
                judge="轉強" if m["up"] else "未轉強", judge_detail=detail(m), note=note)
            return m["up"] or i >= N_REPORTS

        post = R[R["first_filed"] >= S] if R is not None else R
        js, done, judged, n = state()
        lastME = max([pd.Timestamp(r["judge_date"]) for r in js if r["event"] == "月底判定"], default=None)
        # 資料晚到：first_filed ≤ 已判過的月底、尚未判 ⇒ 本資料日補判
        if not done and lastME is not None and post is not None:
            for q in post.index:
                if str(q) in judged or post.at[q, "first_filed"] > lastME:
                    continue
                ff = post.at[q, "first_filed"]
                if judge_q(q, D, "補判（資料晚到）", f"；first_filed {ff.date()} 在 {ff.strftime('%Y-%m')}（該月底已判，當時庫內尚無）⇒ 資料日 {D.date()} 補判、次一交易日開盤成交"):
                    break
        for me in MEs:
            if me < S:
                continue
            js, done, judged, n = state()
            if done:
                break
            if any(r["judge_date"] == str(me.date()) for r in js):
                continue
            qs = [q for q in (post.index if post is not None else []) if str(q) not in judged and post.at[q, "first_filed"] <= me]
            if not qs:
                add(t, "月底判定", judge_date=me.date(), judge=NOJUDGE, note="當月沒有新可用季報 ⇒ 不判（不算未轉強）")
                continue
            for q in qs:
                if judge_q(q, me, "月底判定"):
                    break
        # 舊判定列重算核對（只記 log、保留已寫）
        for r in mine(t, JUDGE_EV):
            if r in new or not r["report_q"]:
                continue
            q = pd.Period(r["report_q"], "Q")
            if R is not None and q in R.index:
                up = metrics(R[R["first_filed"] <= pd.Timestamp(r["judge_date"])], q)["up"]
                if ("轉強" if up else "未轉強") != r["judge"]:
                    log.append(f"{t} seq{r['seq']} {r['report_q']} 重算 {'轉強' if up else '未轉強'} ≠ 已寫 {r['judge']}（保留已寫）")
        # ③ 加碼（只一次）
        cf = next((r for r in mine(t, JUDGE_EV) if r["judge"] == "轉強"), None)
        if cf and not mine(t, "轉強加碼"):
            nd = cal[cal > pd.Timestamp(cf["judge_date"])]
            if len(nd):
                fill(t, "轉強加碼", nd[0], ADD_UNITS, judge_date=cf["judge_date"], report_q=cf["report_q"],
                     note=f"判定轉強（{cf['judge_date']}）⇒ 次一交易日開盤加 {ADD_UNITS} 份（只加一次）")
        # ④ 放棄賣出
        ab = next((r for r in mine(t, JUDGE_EV) if "放棄判定" in r["note"]), None)
        if ab and not mine(t, SELL_EV):
            held = sum(int(r["units"] or 0) for r in mine(t, BUY_EV) if r["status"] == "成交")
            days = cal[cal > pd.Timestamp(ab["judge_date"])]
            skipped = []
            for d in days:
                if not held:
                    add(t, SELL_EV, trade_date=d.date(), units=0, status="未確認（無持股）", judge_date=ab["judge_date"], report_q=ab["report_q"]); break
                if d not in px.index:
                    skipped.append(str(d.date())); continue
                r = add(t, SELL_EV, trade_date=d.date(), units=-held, status="未確認賣出", judge_date=ab["judge_date"], report_q=ab["report_q"],
                        note=f"第 {N_REPORTS} 份新季報仍未轉強 ⇒ 次一交易日開盤賣出" + (f"（順延：{'、'.join(skipped)} 無 K 棒）" if skipped else ""))
                nfill[r["seq"]] = (float(px.at[d, "open"]), str(d.date()), t, SELL_EV)
                break
    return new, nfill, log


def line_events(rows, D, now):
    """今晚事件行：判定日 ＝ 資料日的轉強／放棄判定（同一資料日重跑原樣再印）＋新候選前一晚通知。"""
    out = []
    for r in rows:
        if r["event"] in JUDGE_EV and r["judge_date"] == str(D.date()):
            if r["judge"] == "轉強":
                out.append(f"美股小部位：{r['ticker']} 轉強 ⇒ 明天開盤加 {ADD_UNITS} 份")
            elif "放棄判定" in r["note"]:
                out.append(f"美股小部位：{r['ticker']} 第 {N_REPORTS} 份新季報仍未轉強 ⇒ 明天開盤賣")
    for t, c in CANDS.items():
        S = pd.Timestamp(c["start"])
        if any(r["ticker"] == t and r["event"] == "起點買進" for r in rows):
            continue
        if next_td_pred(D) == S and now < S + pd.Timedelta(hours=21):     # 起點當天台北 21:00 前（美股開盤前）才出
            out.append(f"美股小部位：{t} 新增 ⇒ 明天開盤買 1 份")
    return out


def value(rows, D, PX, tr):
    """照規則欄（每份等額、還原價含息、0.05%／邊）。回 {代號: dict}、組合 dict、私有逐日表。"""
    per, lots_all, daily = {}, [], {}
    trD = tr[tr.index <= D]
    for t in CANDS:
        px = PX[t][PX[t].index <= D]
        lots = [r for r in rows if r["ticker"] == t and r["event"] in BUY_EV and r["status"] == "成交" and pd.Timestamp(r["trade_date"]) <= D]
        sell = next((r for r in rows if r["ticker"] == t and r["event"] == SELL_EV and r["status"] == "未確認賣出" and pd.Timestamp(r["trade_date"]) <= D), None)
        u = sum(int(r["units"]) for r in lots)
        if not u:
            per[t] = {"份數": 0}; continue
        sd = pd.Timestamp(sell["trade_date"]) if sell else None
        ex = float(px.at[sd, "aopen"]) if sd is not None else float(px["aclose"].iloc[-1])
        trx = float(trD[trD.index < sd].iloc[-1]) if sd is not None else float(trD.iloc[-1])
        rs = bs = 0.0
        for r in lots:
            d = pd.Timestamp(r["trade_date"]); w = int(r["units"]); e = float(px.at[d, "aopen"])
            rs += w * (ex / e - 1 - 2 * COST)
            b0 = float(trD[trD.index < d].iloc[-1]); bs += w * (trx / b0 - 1)
            v = px["aclose"][px.index >= d] / e * w
            if sd is not None:
                v = v[v.index < sd].reindex(px.index[px.index >= d]).fillna(ex / e * w)
            lots_all.append((v, pd.Series(float(w), index=v.index)))
        per[t] = {"份數": 0 if sell else u, "累計報酬": rs / u, "^SP500TR同期": bs / u, "_rs": rs, "_bs": bs, "_u": u}
        daily[t] = px
    tu = sum(p.get("_u", 0) for p in per.values())
    port = {"份數（持有中）": sum(p["份數"] for p in per.values()), "投入份數": tu}
    if tu:
        port["累計報酬"] = sum(p["_rs"] for p in per.values()) / tu
        port["^SP500TR同期"] = sum(p["_bs"] for p in per.values()) / tu
        idx = sorted(set().union(*[v.index for v, _ in lots_all]))
        V = sum(v.reindex(idx).fillna(0) for v, _ in lots_all); I = sum(i.reindex(idx).fillna(0) for _, i in lots_all)
        ratio = (V / I).dropna()
        port["最大回落"] = float((ratio / ratio.cummax() - 1).min()) if len(ratio) else np.nan
        port["_ratio"] = ratio
    return per, port, daily


def pct(x):
    return "" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"


# ═════════════ 主流程 ═════════════
def run(src, fwd=FWD, priv=PRIV, asof=None, dry=False, now=None, quiet=False):
    now = now if now is not None else now_tpe()
    P = (lambda *a: None) if quiet else print
    PX = {t: load_px(src, t) for t in CANDS}
    D = min(px.index[-1] for px in PX.values())
    if asof:
        D = min(D, pd.Timestamp(asof))
    cal = load_cal(src, [px.index for px in PX.values()])
    cal = cal[cal <= D]
    tr = load_tr(src)
    REV = load_rev(src, list(CANDS))
    commit = src.commit()
    fp = os.path.join(fwd, "book.csv")
    rows = read_rows(fp)
    fills_fp = os.path.join(priv, "smallpos_fills.csv")
    fills = read_rows(fills_fp)
    new, nfill, log = step(rows, D, cal, PX, REV, commit, now, fills)
    allrows = rows + new
    ev = line_events(allrows, D, now)
    per, port, daily = value(allrows, D, PX, tr)
    # 彙總
    st = {"件": TAG, "資料日": str(D.date()), "資料commit": commit, "寫入時間（台北）": now.strftime("%Y-%m-%d %H:%M"), "候選": {}}
    parts = []
    for t, c in CANDS.items():
        mr = [r for r in allrows if r["ticker"] == t]
        S = c["start"]
        b0 = next((r for r in mr if r["event"] == "起點買進"), None)
        ent = next((r for r in mr if r["event"] == "進場檢查"), None)
        js = [r for r in mr if r["event"] in JUDGE_EV]
        nq = sum(1 for r in js if r["report_q"])
        status = ("已賣（未確認）" if any(r["event"] == SELL_EV for r in mr) else "已確認（加碼）" if any(r["event"] == "轉強加碼" for r in mr)
                  else "已判轉強、待加碼" if any(r["judge"] == "轉強" for r in js) else "已放棄、待賣" if any("放棄判定" in r["note"] for r in js)
                  else "確認前（小部位）" if b0 else f"資料未到起點（起點 {S}）")
        p = per.get(t, {})
        st["候選"][t] = {"名稱": c["name"], "起點": S, "狀態": status, "份數": p.get("份數", 0),
                         "起點成交": (f"{b0['trade_date']} {b0['status']}" if b0 else "未記"),
                         "進場檢查": (ent["judge"] if ent else "未記"), "已判新季報數": nq,
                         "最近判定": (f"{js[-1]['judge_date']} {js[-1]['judge']}" if js else ""),
                         "累計報酬": pct(p.get("累計報酬")), "^SP500TR同期": pct(p.get("^SP500TR同期"))}
        parts.append(f"{t} {status} {p.get('份數', 0)} 份" + (f"（{ent['judge']}）" if ent and ent["judge"] == "進場時已轉強" else ""))
    st["組合（照規則欄）"] = {k: (pct(v) if k in ("累計報酬", "^SP500TR同期", "最大回落") else v) for k, v in port.items() if not k.startswith("_")}
    st["今晚事件行"] = ev
    summ = (f"美股小部位前瞻：資料日 {D.date()}｜資料 {commit[:10]}｜新增 {len(new)} 列｜" + "；".join(parts)
            + (f"｜照規則累計 {pct(port.get('累計報酬'))}、^SP500TR 同期 {pct(port.get('^SP500TR同期'))}" if port.get("投入份數") else "")
            + ("｜⚠ " + "；".join(log) if log else "") + ("｜乾跑（未寫檔）" if dry else ""))
    if not dry:
        os.makedirs(fwd, exist_ok=True); os.makedirs(priv, exist_ok=True)
        if new or not os.path.exists(fp):
            with open(fp, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(allrows)
        if nfill:
            hdr = not os.path.exists(fills_fp)
            with open(fills_fp, "a", encoding="utf-8-sig" if hdr else "utf-8", newline="") as f:
                w = csv.writer(f)
                if hdr:
                    w.writerow(["seq", "ticker", "event", "trade_date", "yahoo_open", "recorded_at"])
                for s, (o, d, t, e) in nfill.items():
                    w.writerow([s, t, e, d, repr(o), now.strftime("%Y-%m-%d %H:%M:%S")])
        # 私有：逐日、季營收明細（衍生檔，每次重寫）
        dd = []
        for t, px in daily.items():
            x = px[["open", "close", "adjclose", "aopen", "aclose"]].copy(); x["ticker"] = t
            dd.append(x[x.index >= pd.Timestamp(CANDS[t]["start"])])
        if dd:
            x = pd.concat(dd)
            if "_ratio" in port:
                x["port_value_over_invested"] = port["_ratio"].reindex(x.index).to_numpy()
            x["SP500TR"] = tr.reindex(x.index).to_numpy()
            x.to_csv(os.path.join(priv, "smallpos_daily.csv"), index_label="date", float_format="%.10g")
        rr = []
        for t, R in REV.items():
            R = R[R["first_filed"] <= D]
            for q in R.index[-12:]:
                m = metrics(R, q); m.update(ticker=t, first_filed=str(R.at[q, "first_filed"].date()), first_form=R.at[q, "first_form"])
                rr.append(m)
        pd.DataFrame(rr).to_csv(os.path.join(priv, "smallpos_rev.csv"), index=False, float_format="%.10g")
        old = {}
        sp = os.path.join(fwd, "state.json")
        if os.path.exists(sp):
            old = json.load(open(sp, encoding="utf-8"))
        json.dump(st, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if new or log or old.get("資料日") != st["資料日"]:
            with open(os.path.join(fwd, "runlog.md"), "a", encoding="utf-8") as f:
                f.write(f"- {now.strftime('%Y-%m-%d %H:%M')}（台北）｜資料 {commit[:10]}（資料日 {D.date()}）｜新增 {len(new)} 列"
                        + ("：" + "、".join(f"{r['ticker']} {r['event']} {r['judge'] or r['status']}" for r in new) if new else "")
                        + (f"｜照規則累計 {pct(port.get('累計報酬'))}、最大回落 {pct(port.get('最大回落'))}、^SP500TR 同期 {pct(port.get('^SP500TR同期'))}" if port.get("投入份數") else "")
                        + ("｜事件行：" + " / ".join(ev) if ev else "") + ("｜⚠ " + "；".join(log) if log else "") + "\n")
    else:
        for r in new:
            P("（乾跑新列）" + "｜".join(f"{k}={r[k]}" for k in COLS if r[k] and k not in ("recorded_at", "data_commit")))
    for e in ev:
        P(e)
    P(summ)
    return {"D": D, "new": new, "ev": ev, "state": st, "log": log, "rows": allrows, "summary": summ}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof"); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--root", help="改讀一般資料夾（fixture）"); ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--no-fetch", action="store_true"); ap.add_argument("--fwd", default=FWD); ap.add_argument("--priv", default=PRIV)
    ap.add_argument("--line-out", help="事件行另寫一檔（無事件 ⇒ 空檔）")
    a = ap.parse_args()
    src = Src(a.root, None) if a.root else Src(US_REPO, a.ref, fetch=not a.no_fetch)
    try:
        out = run(src, a.fwd, a.priv, a.asof, a.dry)
    except Exception as e:                                                          # 排程：失敗印一行、exit 1
        print(f"美股小部位前瞻：失敗 {type(e).__name__}: {e}")
        raise SystemExit(1)
    if a.line_out:
        io.open(a.line_out, "w", encoding="utf-8").write("".join(x + "\n" for x in out["ev"]))


if __name__ == "__main__":
    main()

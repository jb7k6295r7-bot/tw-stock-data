# -*- coding: utf-8 -*-
"""每日名單第六節「加碼條件（大盤濾網 seq1）」——回測線，2026-10-13。
依據：信箱 登錄全文-營量營飆漲多加碼大盤濾網_加權指數站上20日線才加碼_登錄_台股策略線_seq1_sha53ec3726a0d1c393（2026-10-13 20:00）§一、§二、§四。
⛔ 看盤參考、尚未驗證；⛔ 只讀持股檔與資料，不寫任何檔（daily_list 把本節行接在 NOTE 之前）。

    單獨試跑（不寫信箱）：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.addon_daily [--sha <main sha>] [--procs 2]

定義（登錄 §一 ＝ 漲多加碼 seq2 §一，逐式照 researchAddOn U2／U3／U4；以資料日 T 收盤判）：
 持股：跨線信箱 _持股/持股.csv（backtest.holdings，只讀）來源含「營量」或「營飆」者；營飆營量 ⇒ 兩策略各判一次
 進場日 e ＝ 第 6 欄正式進場日（有填）否則買進日（cal 中 ≥ 該日的第一個交易日）；h ＝ t − e ＋ 1（e 算第 1 根）；h ＜ 10 不判
 只判 t ≤ xbar − 1（xbar ＝ D.exit_pos(e, H)；營量 H＝60、營飆 H＝120；加碼日 t＋1 要 ≤ 原持股出場根）
 g ＝ 還原收盤[t] ÷ 還原開盤[e] − 1；t 當天要有 K 棒；(e, t] 有壞根 ⇒ 不判、之後也不再判
 q(h, t) ＝ t 日 R1 母體裡「有 K 棒、C[t−h] 有值、(t−h, t] 無壞根」者 C[t] ÷ C[t−h] − 1 的第 99（營量 A2）／95（營飆 A1）百分位（np.percentile 線性內插）；
   有效檔數 ＜ 20 ⇒ 不判
 R1：每日「UG.gate3（GATE_V2 開）∩ 四碼首碼 1～9 非 91xx ∧ 有 K 棒 ∧ pit_valid ∧ amt20 有值」依 amt20 大到小前 ⌈X × 檔數⌉（同值依代號序）；
   X ＝ 0.20091623036649214（researchAddOn 主世界 2016-01-04：307／1528，固定；與 resultsAddOn/AddOn.json 比對）
   C ＝ D.load_stock 還原收盤 ffill；amt20 ＝ 含當日最近 20 根有效 K 棒原始成交金額平均（researchRevLimitUp._wjob 同式；不排金融）
 壞根（全線 seq335）：researchBARR.bad_part ∪ adj 減資／面額事件日（researchCrashOversold._badjob 同式）
 大盤：t 日加權指數收盤 ＞ 含 t 最近 20 個交易日收盤的簡單平均（MA20 寫死）；
   來源優先公開庫 tw-stock-data（同一 main sha）data/history/market_index.csv；該檔沒有 t ⇒ 退回唯讀 ~/us-stock-data/data/macro/twse_taiex.csv
   （⛔ 私有庫來源只輸出布林、不印指數值）
 每筆持股每策略只認第一次觸發（h ≥ 10 ∧ g ≥ q）：第一次在 T ⇒ 大盤成立「明天開盤可加碼一份」／不成立「照規則不加」；
   第一次在 T 之前 ⇒「已於 … 觸發過」不再提示（登錄 §一：大盤不成立 ⇒ 這次不加、之後也不再判；⛔ 不等大盤站回再加）
   T 之前的觸發另照 researchAddOn U2：t＋1 是壞根 ⇒ 不加且不再判；t＋1 沒有有效開盤 ⇒ 當天不加、之後照常再判

2026-10-14 改（裁定 seq350 §一：大盤濾網 seq2 結案不採用；「明天開盤可加碼」提醒照推、⛔ 不再加大盤條件）：
  節名「六、加碼提醒（漲到全市場前段）」、節首固定句改 FIXED（加碼那份平均有賺但中位約 0、一半會賠；歷史上加碼沒有讓策略變好）
  判定只剩 h ≥ 10 ∧ g ≥ q（營量第 99、營飆第 95 百分位）；每筆每策略第一次達門檻在 T ⇒「明天開盤可加碼一份（金額＝原買進金額）；與原持股同日賣（日期）」
  大盤那行留作資訊（加權指數是否站上 20 日線；「參考，不影響加碼提醒」），⛔ 不影響判定
  第一次達門檻在 T 之前 ⇒ 用新規則（不看大盤）重算第一次達門檻日 t：舊規則當時已提示（t ≥ PROMPT_START 且 t 日大盤站上 20 日線）⇒「已於 t 觸發過」；
    否則（大盤不符、讀不到大盤、或第六節還沒上線）⇒「已於 t 達門檻（當時未提示）」，⛔ 不補提示
    PROMPT_START ＝ 2026-10-12（第六節第一次出現的資料日：_營量觀察/daily_2026-10-12.md）
  持股.csv 備註含「60 天同日賣」（H60_NOTE；使用者 10/14 定營飆超額那份第 60 個交易日跟營量同日賣）⇒ 該筆營飆那份 H＝60（判定窗 t ≤ xbar−1、出場日、「與原持股同日賣」都用 60）
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import gate_b_status as GB
from . import holdings as HD
from . import universe_gate as UG

REPO = os.path.expanduser("~/tw-p17")
PRIV = os.path.expanduser("~/us-stock-data/data/macro/twse_taiex.csv")
X_R1 = 0.20091623036649214                                   # researchAddOn 主世界 2016-01-04：307／1528
HMIN, MINPOP, MA_N = 10, 20, 20
PCT = {"營量": 99.0, "營飆": 95.0}                           # 營量 A2、營飆 A1（漲多加碼 seq2 探索段挑中格）
HOLD = {"營量": 60, "營飆": 120}
PORTION = {"營量": "那 1/3", "營飆": "那 2/3"}               # 營飆營量（金額 2:1 分兩份）
TITLE = "## 六、加碼提醒（漲到全市場前段）"
FIXED = "加碼那一份平均有賺（營量 +10.5%、營飆 +12.5%），但中位約 0、一半會賠，平均靠少數大賺；歷史上加碼沒有讓策略變好，加碼金額自行控制"
MK_REF = "（參考，不影響加碼提醒）"
PROMPT_START = pd.Timestamp("2026-10-12")                     # 第六節第一次出現的資料日（之前的達門檻日當時一定沒提示）
H60_NOTE = "60 天同日賣"                                      # 持股.csv 備註含此字樣 ⇒ 營飆那份第 60 個交易日跟營量同日賣（使用者 10/14）
_G: dict = {}


def hold_days(sn, note=""):
    """策略 sn 那份的持有天數：營量 60；營飆 120，備註含 H60_NOTE ⇒ 60（使用者 10/14 定，⛔ 不改營飆規則）。"""
    if sn == "營飆" and H60_NOTE in str(note or ""):
        return 60
    return HOLD[sn]


def okcode(s):
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and s[0] in "123456789" and not s.startswith("91")


# ═════════════ 每檔讀取（pool）═════════════
def _job(a):
    sid, mk = a
    D.DATA = _G["DATA"]; cal = _G["cal"]; n = len(cal); lo = _G["lo"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c0 = df["close"].to_numpy(float)
    bar = np.isfinite(c0)
    if bar.sum() < 2:
        return sid, None
    c = pd.Series(c0).ffill().to_numpy(float)
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)
    idx = np.flatnonzero(bar)
    a20 = np.full(n, np.nan)
    a20[idx] = pd.Series(amt[idx]).rolling(20, min_periods=20).mean().to_numpy()
    pv = np.asarray(UG.pit_valid(sid, cal, D.DATA), bool)
    o = df["open"].to_numpy(float)
    return sid, {"c": c[lo:], "bar": bar[lo:], "a20": a20[lo:], "pv": pv[lo:], "o": np.where(np.isfinite(o) & (o > 0), o, np.nan)[lo:]}


def _badjob(sid):
    from . import researchBARR as BARR
    DATA, cal = _G["DATA"], _G["cal"]; n = len(cal); lo = _G["lo"]
    bad = BARR.bad_part(sid, DATA, cal).copy()
    D.DATA = DATA
    adj = D.load_adj(sid) if os.path.exists(os.path.join(DATA, "stocks", f"{sid}.csv")) else None
    if adj is not None and len(adj) and "event" in adj:
        for d, e in zip(adj["date"], adj["event"].astype(str)):
            if e in ("reduce", "parvalue"):
                k = int(cal.searchsorted(d))
                if k < n:
                    bad[k] = True
    return sid, bad[lo:]


# ═════════════ 大盤 ═════════════
def taiex(sha, cal, need):
    """⇒ (函式 pos ⇒ (成立?, 收盤, MA20) 或 None, 來源說明, 是否可印數值)。need ＝ 要判的日曆位置。"""
    srcs = []
    try:
        txt = subprocess.run(["git", "-C", REPO, "show", f"{sha}:data/history/market_index.csv"], capture_output=True, text=True, check=True).stdout
        srcs.append((pd.read_csv(io.StringIO(txt)), f"公開庫 tw-stock-data main {sha[:10]} data/history/market_index.csv", True))
    except Exception:
        pass
    if os.path.exists(PRIV):
        srcs.append((pd.read_csv(PRIV, usecols=["date", "close"]), "私有庫 us-stock-data data/macro/twse_taiex.csv（唯讀、只用布林）", False))
    for df, nm, show in srcs:
        s = pd.Series(pd.to_numeric(df["close"], errors="coerce").to_numpy(float), index=pd.to_datetime(df["date"])).dropna()
        s = s[~s.index.duplicated(keep="last")].sort_index()
        if all(cal[p] in s.index for p in need):
            def f(p, s=s):
                w = s[s.index <= cal[p]].iloc[-MA_N:]
                if len(w) < MA_N or w.index[-1] != cal[p]:
                    return None
                return bool(w.iloc[-1] > w.mean()), float(w.iloc[-1]), float(w.mean())
            return f, nm, show
    return (lambda p: None), "（公開庫、私有庫都沒有資料日的加權指數）", False


# ═════════════ 本節 ═════════════
def section(sha, DATA, procs=2, log=print, asof=None):
    """⇒ 第六節的行（list[str]）。asof ＝ 只給測試（截斷日曆到該日，模擬過去的資料日；daily_list 不帶）。"""
    T0 = time.time()
    D.DATA = DATA
    cal = D.load_calendar()
    if asof is not None:
        cal = cal[cal <= pd.Timestamp(asof)]
    n = len(cal); T = n - 1; asof = str(cal[T].date())
    nxt = GB.future_trading_days(cal, 2)[0][0].date()
    fut, basis = GB.future_trading_days(cal, 2 * 120 + 10, fixed_holidays_uncovered=True)
    cal_ext = cal.append(fut)
    stocks = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    nm_of = stocks.drop_duplicates("stock_id", keep="last").set_index("stock_id")["name"].to_dict()
    mk_of = stocks.drop_duplicates("stock_id", keep="last").set_index("stock_id")["market"].to_dict()
    # 持股（營量／營飆）
    try:
        rows = HD.read_csv()
    except Exception as ex:
        log(f"[加碼] 讀持股失敗 {type(ex).__name__}: {ex}")
        rows = []
    ED = HD.entry_dates()
    H = []                                                    # (代號, 來源, 策略, 進場日字串, e, 持有天數)
    for c_, bd_, bp_, nt_, src in rows:
        if src not in ("營量", "營飆", "營飆營量") or bd_ is None:
            continue
        ed_ = ED.get(c_) or bd_
        e = int(cal.searchsorted(pd.Timestamp(ed_)))
        if e > T:                                             # 資料日之後才進場（重跑舊資料日時）⇒ 不列
            continue
        for sn in ("營量", "營飆"):
            if sn in src and not any(x[0] == c_ and x[2] == sn for x in H):
                H.append((c_, src, sn, ed_, e, hold_days(sn, nt_)))
    L = [TITLE, "", FIXED, ""]
    if not H:
        L.append("- 持股檔裡沒有營量／營飆持股")
        return L
    lo = max(min(x[4] for x in H) - 1, 0)
    # 要判的日子（每筆 [e, min(xbar−1, T)]，含 h ＜ 10 的參考門檻只在 T）
    days = set()
    for c_, src, sn, ed_, e, Hs in H:
        xb = D.exit_pos(e, Hs)
        days.update(range(max(e + HMIN - 1, e), min(xb - 1, T) + 1))
        days.add(T)
    days = sorted(days)
    # 母體
    prev = UG.GATE_V2
    UG.set_gate_v2(True)
    try:
        U = UG.gate3(stocks)
        U = U[U["stock_id"].map(okcode)].reset_index(drop=True)
        hold_extra = [(c_, mk_of.get(c_, "twse")) for c_ in sorted({h[0] for h in H}) if c_ not in set(U["stock_id"])]
        _G.update(DATA=DATA, cal=cal, lo=lo)
        jobs = list(zip(U["stock_id"], U["market"])) + hold_extra
        with Pool(procs) as pool:
            res = dict(pool.map(_job, jobs, chunksize=16))
    finally:
        UG.set_gate_v2(prev)
    usids = [s for s in U["stock_id"] if res.get(s) is not None]
    m = n - lo
    C = np.vstack([res[s]["c"] for s in usids]); BAR = np.vstack([res[s]["bar"] for s in usids])
    A20 = np.vstack([res[s]["a20"] for s in usids]); PV = np.vstack([res[s]["pv"] for s in usids])
    MKT = BAR & PV & np.isfinite(A20)
    R1 = {}
    for d in days:
        k = d - lo
        ii = np.flatnonzero(MKT[:, k])
        R1[d] = ii[np.argsort(-A20[ii, k], kind="stable")[:int(np.ceil(X_R1 * len(ii)))]] if len(ii) else ii
    need_bad = sorted({usids[i] for d in days for i in R1[d]} | {h[0] for h in H})
    with Pool(procs) as pool:
        BADD = dict(pool.map(_badjob, need_bad, chunksize=8))
    log(f"[加碼] 母體 {len(usids)} 檔、判 {len(days)} 天、壞根算 {len(need_bad)} 檔｜{time.time() - T0:.0f}s")
    ix = {s: i for i, s in enumerate(usids)}
    BADM = {s: np.cumsum(np.r_[0, BADD[s]]) for s in BADD}    # CB[k] ＝ 窗內位置 < k 的壞根數

    QC = {}

    def q_of(pct, h, t):
        key = (pct, h, t)
        if key not in QC:
            k = t - lo; k0 = k - h
            if k0 < 0:
                QC[key] = (np.nan, 0); return QC[key]
            v = []
            for i in R1[t]:
                s = usids[i]
                if not BAR[i, k] or not np.isfinite(C[i, k0]):
                    continue
                cb = BADM[s]
                if cb[k + 1] - cb[k0 + 1] > 0:                # (t−h, t] 有壞根
                    continue
                v.append(C[i, k] / C[i, k0] - 1.0)
            v = np.asarray(v, float); v = v[np.isfinite(v)]
            QC[key] = (float(np.percentile(v, pct)) if len(v) >= MINPOP else np.nan, int(len(v)))
        return QC[key]
    # 大盤
    MK, msrc, mshow = taiex(sha, cal, [T])
    mT = MK(T)
    if mT is None:
        L.append(f"- 大盤（{asof}）{MK_REF}：讀不到加權指數（{msrc}）")
    elif mshow:
        L.append(f"- 大盤（{asof}）{MK_REF}：加權指數收盤 {mT[1]:,.2f}、含當天 20 日平均 {mT[2]:,.2f} ⇒ {'站上 20 日線' if mT[0] else '在 20 日線下'}（來源：{msrc}）")
    else:
        L.append(f"- 大盤（{asof}）{MK_REF}：加權指數收盤{'站上 20 日線' if mT[0] else '在 20 日線下'}（來源：{msrc}）")
    L += ["- 判定：營量、營飆持股各自判；持有第 h 天（正式進場日算第 1 天）h ≥ 10，且持有報酬 g ＝ 收盤 ÷ 進場日開盤 − 1（還原價）≥ 當天 R1 母體同 h 天報酬的"
          "第 99 百分位（營量）／第 95 百分位（營飆）；每筆每策略只認第一次漲到門檻那天 ⇒ 明天開盤可加碼一份；不看大盤", ""]

    def series(s):
        if s in ix:
            i = ix[s]; return C[i], BAR[i], res[s]["o"]
        r = res.get(s)
        if r is None:
            return None
        return r["c"], r["bar"], r["o"]

    def exit_txt(xb):
        if xb < len(cal_ext):
            b = basis[xb - n] if xb >= n else ""
            return f"{cal_ext[xb].date()}" + ("（未公告年度只扣週末與固定日期國定假日，實際只會更晚）" if "只扣週末" in b else "")
        return "（超出外推範圍）"
    for c_, src, sn, ed_, e, Hs in H:
        nm = nm_of.get(c_, "")
        xb = D.exit_pos(e, Hs); h_T = T - e + 1
        own = "（你定與營量同日賣）" if Hs != HOLD[sn] else ""
        part = PORTION[sn] if src == "營飆營量" else ""
        head = f"- {c_} {nm}｜{sn}{part}（正式進場 {cal[e].date()}，今天第 {h_T} 天）"
        sr = series(c_)
        if sr is None:
            L.append(f"{head}｜⚠ 讀不到股價，不判"); continue
        cc, bb, oo = sr
        ep = oo[e - lo]
        if not np.isfinite(ep):
            L.append(f"{head}｜⚠ 進場日沒有有效開盤價，不判"); continue
        cb = BADM.get(c_)
        state, info = "未觸發", None
        for t in range(e + HMIN - 1, min(xb - 1, T) + 1):
            k = t - lo
            if cb is not None and cb[k + 1] - cb[e - lo + 1] > 0:     # (e, t] 有壞根 ⇒ 之後不判
                state = "壞根"; info = t; break
            if not bb[k]:
                continue
            h = t - e + 1
            q, npop = q_of(PCT[sn], h, t)
            if not np.isfinite(q):
                continue
            g = cc[k] / ep - 1.0
            if g >= q:
                if t < T:
                    if cb is not None and cb[k + 2] - cb[k + 1] > 0:  # 加碼日 t＋1 是壞根 ⇒ 不加且不再判
                        state = "加碼日壞根"; info = t; break
                    if not np.isfinite(oo[k + 1]):                    # t＋1 沒有有效開盤 ⇒ 當天不加、之後照常再判
                        continue
                state = "觸發"; info = (t, g, q, MK(t)); break
        g_T = cc[T - lo] / ep - 1.0 if bb[T - lo] else np.nan
        q_T, _ = q_of(PCT[sn], h_T, T)
        gq = (f"g {g_T * 100:+.1f}%" if np.isfinite(g_T) else "g —（今天沒有 K 棒）") + (f"、門檻 {q_T * 100:.1f}%" if np.isfinite(q_T) else "、門檻 —")
        if T >= xb:
            L.append(f"{head}｜已到出場日（{exit_txt(xb)}），不判")
        elif state == "觸發" and info[0] == T:
            t, g, q, mk = info
            L.append(f"{head}｜g {g * 100:+.1f}% ≥ 門檻 {q * 100:.1f}%｜**明天（{nxt}）開盤可加碼一份（金額＝原買進金額{part}）；"
                     f"與原持股同日賣（{sn}第 {Hs} 天{own}，{exit_txt(xb)} 收盤）**")
        elif state == "觸發":
            t, g, q, mk = info
            said = mk is not None and mk[0] and cal[t] >= PROMPT_START       # 舊規則（大盤濾網 seq1）當時已提示
            if said:
                L.append(f"{head}｜已於 {cal[t].date()} 觸發過（第 {t - e + 1} 天 g {g * 100:+.1f}% ≥ 門檻 {q * 100:.1f}%；當時已提示加碼），不再提示｜今天 {gq}")
            else:
                L.append(f"{head}｜已於 {cal[t].date()} 達門檻（當時未提示；第 {t - e + 1} 天 g {g * 100:+.1f}% ≥ 門檻 {q * 100:.1f}%），不補提示｜今天 {gq}")
        elif state == "壞根":
            L.append(f"{head}｜持有期間 {cal[info].date()} 有壞根（缺口 ≥ 5 日／減資等），照規則不判｜今天 {gq}")
        elif state == "加碼日壞根":
            L.append(f"{head}｜{cal[info].date()} 漲到門檻但隔天是壞根，照規則不加、不再判｜今天 {gq}")
        elif h_T < HMIN:
            L.append(f"{head}｜持有 {h_T} 天｜{gq}｜未滿 10 天，第 10 天（{exit_txt(e + HMIN - 1)}）起才判")
        elif not bb[T - lo]:
            L.append(f"{head}｜持有 {h_T} 天｜今天沒有 K 棒，不判")
        else:
            L.append(f"{head}｜持有 {h_T} 天｜{gq}｜未達門檻，不提示")
    log(f"[加碼] 第六節 {len(H)} 列｜大盤來源 {msrc}｜{time.time() - T0:.0f}s")
    return L


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sha", default=None); ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--asof", default=None, help="測試用：截斷日曆到該日"); a = ap.parse_args()
    sha = a.sha or subprocess.run(["git", "-C", REPO, "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", sha], capture_output=True, text=True).stdout.strip()
    DATA = os.path.expanduser(f"~/h2data/{sha}/data")
    try:
        x = json.load(open(os.path.join(REPO, "backtest", "resultsAddOn", "AddOn.json"), encoding="utf-8"))["母體"]["主"]["R1 X"]["X"]
        print(f"[閘] X ＝ {X_R1} vs AddOn.json {x}：{'同' if x == X_R1 else '⛔ 不同'}")
    except Exception as ex:
        print(f"[閘] 讀不到 AddOn.json（{ex}）")
    print("\n".join(section(sha, DATA, a.procs, asof=a.asof)))


if __name__ == "__main__":
    main()

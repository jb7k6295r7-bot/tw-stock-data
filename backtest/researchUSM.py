# -*- coding: utf-8 -*-
"""USREG-M（美股移植 PREREGM：下降趨勢線被收盤向上突破，三種畫法並測）——【pre 段：頻率盤點＋可判定性算術】。

判準：美股登錄 seq2（sha a3c98a07e882a574，正文）＋seq3（81bfc48eff6258f5）＋seq4（cbfc7610923b9e53）＋seq5（ffb22ecb1bd749ff）；
     移植來源 ＝ 台股 PREREGM seq1（sha 9316840579a8d33a）§一～§三、§五、§六 第一欄；台股已裁讀法 ＝ 裁定 seq156（M1～M8、Q1～Q8）。
     裁定線 seq163、seq168、seq176（假訊號臂只排除過去）、seq182（暖身 scope＝panel、UA 無效 K 棒、CVC 照硬斷點）。

⛔⛔ 本支不算、不印、不存任何報酬：不讀任何事件的 T+1 以後價格做比值、不算 R_e／X／基準／勝率。
   剔除只判「資料斷不斷、能不能成交」（與台股 researchM_freq.py 同一原則）。
⛔⛔ 授權：us-stock-data 是私有 repo ⇒ 逐筆事件、逐檔數字一律寫到 ~/us_work/usm/（repo 外），並列 sha；
   backtest/resultsUSM/ 只寫彙總（計數、分位數、區段數、判語、sha 清單）；⛔ 不寫任何「代號＋日期」逐筆列、⛔ 不寫逐檔數值。
資料：us_data 轉接層（46e74a0c8b），釘 us-stock-data 0043f97（seq4 §三、seq5 §三；窗到 2026-08-31 ≤ 2026-09-22 ⇒ 不改釘）。
偵測器：backtest/trendline_m.py（台股同一支，⛔ 一行未改）。
fixture：selftest_trendline_m.run_all()（台股 F1～F8）＋本支 usm_fixtures()（美股資料型態 UF1～UF8）⇒ 全過才開跑。

⭐ 讀法（登錄已寫 ⇒ 照寫；台股已裁 ⇒ 沿用；登錄沒寫 ⇒ 標【待定】、兩邊件數都報，⛔ 本支不替登錄選）：
 U1 價格：us_data.load_ohlc(scope="panel")（seq5 ④：暖身可用入指數前的價格；同一 src 檔、只取面板有列的日子）。還原 OHLC 照 seq2 §一。
    ⚠ 0043f97 面板最早 2015-12-01 ⇒ 期初就在指數的檔只有 22 根暖身（資料事實，⛔ 不是讀法）。
 U2 無效 K 棒：low ≤ min(開,收) 且 max(開,收) ≤ high 不成立 ⇒ 該根當作沒有 K 棒（seq5 ⑤ UA 2021-05-05；計數必報）。
    該根若帶 hard_break ⇒ 旗標移到下一根有效 K 棒（0043f97 實測不發生）。
 U3 日曆 ＝ NYSE（yahoo_GSPC 日期；seq2 §一、資料庫 1639）；不在日曆上的 K 棒（窗外 2026-09-22）丟掉、計數。
 U4 事件母體：T 當天 member（面板 in_index＝1）且有有效 K 棒；T ∈ [窗首, 窗尾−21]（seq2 §一、seq5 ④）。
    ⚠【待定 R-合併】不在母體的偵測事件：主讀法「不是事件、⛔ 不開合併窗」（同台股 Q1：窗外事件先濾掉再合併）；
      另一讀法「在窗內但不在指數的事件也照 Q2 開合併窗」⇒ 保留件數並報。
 U5 合併與剔除順序 ＝ 台股 Q2（裁定 seq156 已裁）：同檔同畫法依時間走 ⇒ T ∈ (t0, t0+20]（t0＝上一個保留事件）⇒ 合併掉；
    否則依序判 硬斷點 → T+1 停牌（只記第一個原因）；被剔除者 ⛔ 不開合併窗。另報「純合併」件數。
    ⛔ 台股的「T+1 開盤漲停」拿掉（seq1 §一：美股沒有每日漲跌停；LULD、熔斷不另建模）。
 U6 硬斷點（登錄已寫的部分；台股 Q4 同形，範圍 [最早取點（丙：回歸窗起點）, T+21]）：
    ① 轉接層 hard_break（seam：IR 2020-03-02；split_div：DHR 2016-07-05、XRX 2017-01-03；seq2 §一）；
    ② 連續 ≥ 5 個交易日無有效 K 棒（5 個缺日全在範圍內；seq2 §二④、seq5 ⑤ CVC）；該股最後一根 K 棒之後的缺日不算（＝下市，同台股 Q5）。
    ⚠【待定 R-跳躍】seq1「還原因子解釋不了的跳躍」美股怎麼認：P0＝只認 ①；P1＝另加台股 Q4 同式
      「相鄰有效 K 棒還原收盤比 ≤ 0.55 或 ≥ 1.8」（美股沒有除權息事件表可拿來解釋 ⇒ 全算）。狀態欄用 P0，P1 另計件數。
    ⚠【待定 R-停牌】seq1 把「停牌（面板該日無列）」列為硬斷點：S0＝只有 T+1 無 K 棒 ⇒ 剔除（台股同形）；
      S1＝範圍內任一天無 K 棒 ⇒ 硬斷點。狀態欄用 S0，S1 另計件數。
 U7 T+1 停牌 ＝ T+1（交易日曆）沒有有效 K 棒（含 T 之後就沒資料＝已下市，另計）。
 U8 下市：該股最後一根 K 棒 < T+21 ⇒ 持有期內下市（最後成交價了結，seq1 §一）；保留、計數。
 U9 ⚠【待定 R-移出】持有期 (T, T+21] 內被移出指數：E0＝照常抱到 T+21（scope＝panel 有移出後的價格）；
      E1＝移出視同下市（最後在指數那天收盤了結）；E2＝剔除。狀態欄不因移出改變；件數與「移出後到 T+21 仍有 K 棒」件數另報。
 U10 每檔每年：分子＝保留事件數；分母＝該檔在 [窗首, 窗尾−21] 內「member 且有有效 K 棒」的交易日數 ÷ 每年交易日數
     （台股 Q6 分母是首末 K 棒跨距；美股母體逐日變動 ⇒ 改用在指數日；跨距版並報）。分佈只取曝露 ≥ 1 年的檔（含零事件）。
 U11 20 日區段：從窗首每 20 個交易日切（區段號＝(T−窗首)//20）；T ≤ 窗尾−21 ⇒ 最多 ceil(可用日／20) 段（台股 Q7／B4 同式）。
 U12 描述臂 R＝3、10 只影響 (甲)(乙)（台股 Q8）。
 U13 暖身依賴（seq5 ④ 的影響，描述）：事件的最早取點早於 T 所在那段指數區間的起點 ⇒ 計數（分「期中加入」與「期初已在、用到 2015-12」）；
     另以 scope＝covered（舊預設、無暖身、無移出後價格）重跑主三格，報保留件數（描述）。
"""
from __future__ import annotations
import os, sys, time, json, hashlib, io, csv
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import us_data as U
from backtest import trendline_m as TM
from backtest import selftest_trendline_m as STM

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSM")
WORK = os.path.expanduser("~/us_work/usm")
H_OUT, MERGE, BLOCK = 21, 20, 20
H_C = 60                                           # 描述臂 c（持有 60 日）只做區段算術
CONFIGS = [("甲", 5), ("乙", 5), ("丙", 5), ("甲", 3), ("乙", 3), ("甲", 10), ("乙", 10)]
MAIN = [("甲", 5), ("乙", 5), ("丙", 5)]
JUMP_LO, JUMP_HI = 0.55, 1.8                       # 台股 Q4 同式（只給 R-跳躍 P1 計數）
_G = {}


def cfg_name(meth, R):
    return meth if (meth, R) in MAIN else "{}_R{}".format(meth, R)


def _cnt(cs, a, b):
    """cs 的區間 [a, b] 內 True 的個數（a>b ⇒ 0；b 截到尾）。＝ researchH2._cnt。"""
    b = min(b, len(cs) - 1)
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def _g5(valid, last, first=0):
    """第 d 天是否為「連續缺 ≥ 5 日」的第 5 天以後；只數 [first, last]（第一根～最後一根有效 K 棒）之間的缺日：
    last 之後＝下市（同台股 Q5）、first 之前＝還沒有資料（面板還沒開始）⇒ 都不算缺。"""
    n = len(valid); run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        miss = (not valid[i]) and first <= i <= last
        r_ = r_ + 1 if miss else 0
        run[i] = r_
    return run >= 5


# ═════════════ 讀檔 → 對齊日曆 ═════════════
def prep(df, cal):
    """df：load_ohlc 形狀（index＝date；open,high,low,close,hard_break）。→ 對齊日曆的陣列與計數。"""
    on = df.index.isin(cal)
    n_off = int((~on).sum())
    df = df[on]
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    hb = df["hard_break"].to_numpy(bool)
    ok = (l <= np.fmin(o, c)) & (np.fmax(o, c) <= h)
    bad_dates = list(df.index[~ok])
    n = len(cal)
    pos = cal.get_indexer(df.index)
    O = np.full(n, np.nan); Hh = np.full(n, np.nan); C = np.full(n, np.nan)
    O[pos[ok]] = o[ok]; Hh[pos[ok]] = h[ok]; C[pos[ok]] = c[ok]
    pb = np.zeros(n, bool)
    pb[pos[ok & hb]] = True
    valid = np.isfinite(C)
    moved = 0
    for p in pos[(~ok) & hb]:                       # U2：無效那根若帶斷點 ⇒ 移到下一根有效 K 棒
        nx = np.flatnonzero(valid[p + 1:])
        if len(nx):
            pb[p + 1 + nx[0]] = True; moved += 1
    bars = np.flatnonzero(valid)
    jb = np.zeros(n, bool)                          # R-跳躍 P1：相鄰有效 K 棒收盤比（不含 ① 已標的斷點）
    if len(bars) > 1:
        ratio = C[bars[1:]] / C[bars[:-1]]
        hit = ((ratio <= JUMP_LO) | (ratio >= JUMP_HI)) & ~pb[bars[1:]]
        jb[bars[1:][hit]] = True
    return {"O": O, "H": Hh, "C": C, "valid": valid, "pb": pb, "jb": jb, "bars": bars,
            "n_off": n_off, "bad_dates": bad_dates, "moved": moved}


def member_array(ticker, cal):
    """→ 對齊日曆的 member（面板 in_index＝1；無列日取 spans；窗首以前一律 False）。"""
    f = U.in_index(ticker)
    m = pd.Series(False, index=cal)
    m.loc[f.index] = f["member"].values
    return m.to_numpy(bool)


def span_start_array(ticker, cal):
    """→ 每個日曆位置所在指數區間的起點（Timestamp 陣列；不在任何區間 ⇒ NaT）。"""
    out = np.full(len(cal), np.datetime64("NaT"), dtype="datetime64[ns]")
    cv = cal.values
    for a, b in U._spans(ticker):
        sel = (cv >= np.datetime64(a)) & ((cv < np.datetime64(b)) if b is not None else True)
        out[sel] = np.datetime64(a)
    return out


# ═════════════ 狀態機（台股 Q2 同一順序）═════════════
def assign(evs):
    """evs：依 T 排序的 [{T, reason（'' ＝ 可保留；否則剔除原因）}]。→ 狀態 list 與純合併件數。
    同檔同畫法依時間走：T ∈ (t_keep, t_keep+20] ⇒ 合併掉；否則有剔除原因 ⇒ 剔除（⛔ 不開合併窗）；否則保留。"""
    st = []; t_keep = -10 ** 9; t_pure = -10 ** 9; n_pure = 0
    for e in evs:
        T = e["T"]
        if not (t_pure < T <= t_pure + MERGE):
            n_pure += 1; t_pure = T
        if t_keep < T <= t_keep + MERGE:
            st.append("合併掉")
        elif e["reason"]:
            st.append("剔除_" + e["reason"])
        else:
            st.append("保留"); t_keep = T
    return st, n_pure


def events_one(A, member, spanst, cal, w0, wE, meth, R):
    """一檔、一格：偵測 → 母體 → 旗標 → 狀態。回 (rows, stats, n_raw_all, alt_kept)。⛔ 不讀任何價格比值（jb 只是資料斷點旗標）。"""
    r = TM.detect_calendar(A["O"], A["H"], A["C"], meth, R)
    valid, bars = A["valid"], A["bars"]
    n = len(valid)
    if len(bars) == 0:
        return [], r["stats"], 0, 0
    last = int(bars[-1])
    cs_pb = np.cumsum(A["pb"]); cs_g5 = np.cumsum(_g5(valid, last, int(bars[0]))); cs_jb = np.cumsum(A["jb"])
    miss = ~valid; miss[:bars[0]] = False; miss[last + 1:] = False; cs_miss = np.cumsum(miss)
    cs_nm = np.cumsum(~member)
    w_start = np.datetime64(cal[w0])
    win = [e for e in r["events"] if w0 <= e["T"] <= wE]
    uni, alt = [], []
    for e in win:
        T, a = e["T"], e["first"]
        f_brk = _cnt(cs_pb, a, T + H_OUT) > 0 or _cnt(cs_g5, a + 4, T + H_OUT) > 0
        f_halt = not bool(valid[T + 1]) if T + 1 < n else True
        reason = "硬斷點" if f_brk else ("T+1停牌" if f_halt else "")
        inu = bool(member[T] and valid[T])
        d = {"T": T, "first": a, "anchors": e.get("anchors"), "conf": e.get("conf"), "reason": reason,
             "f_brk": f_brk, "f_halt": f_halt,
             "f_jump": _cnt(cs_jb, a, T + H_OUT) > 0,
             "f_gap1": _cnt(cs_miss, a, T + H_OUT) > 0,
             "f_exit": _cnt(cs_nm, T + 1, T + H_OUT) > 0,
             "f_exit_bar": bool(_cnt(cs_nm, T + 1, T + H_OUT) > 0 and last >= T + H_OUT),
             "f_dl_in": last < T + H_OUT, "f_dl_t1": last <= T,
             "f_warm_join": False, "f_warm_2015": False}
        ss = spanst[T]
        if not np.isnat(ss):
            fd = np.datetime64(cal[a])
            if ss > w_start and fd < ss:
                d["f_warm_join"] = True
            elif ss <= w_start and fd < w_start:
                d["f_warm_2015"] = True
        alt.append(dict(d, inu=inu))
        if inu:
            uni.append(d)
    st, n_pure = assign(uni)
    for d, s in zip(uni, st):
        d["狀態"] = s
    # 另一讀法 R-合併：窗內但不在指數的事件也開合併窗（它們本身不計入保留）
    alt_kept = 0; t_keep = -10 ** 9
    for d in alt:
        if t_keep < d["T"] <= t_keep + MERGE:
            continue
        if d["reason"]:
            continue
        t_keep = d["T"]
        alt_kept += int(d["inu"])
    return uni, dict(r["stats"], n_pure=n_pure, n_win=len(win)), len(r["events"]), alt_kept


# ═════════════ 每檔 ═════════════
def _init(cal, w0, wE):
    _G.update(cal=cal, w0=w0, wE=wE)


def load_one(t):
    cal, w0, wE = _G["cal"], _G["w0"], _G["wE"]
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = prep(df, cal)
    if len(A["bars"]) == 0:
        return None
    member = member_array(t, cal)
    spanst = span_start_array(t, cal)
    valid = A["valid"]
    expo_mem = int(np.sum(member[w0:wE + 1] & valid[w0:wE + 1]))
    b = A["bars"]; lo_, hi_ = max(int(b[0]), w0), min(int(b[-1]), wE)
    expo_span = max(0, hi_ - lo_ + 1)
    out = {"t": t, "expo_mem": expo_mem, "expo_span": expo_span, "n_invalid": len(A["bad_dates"]),
           "bad_dates": [str(x.date()) for x in A["bad_dates"]], "n_off": A["n_off"], "moved": A["moved"],
           "n_pb": int(A["pb"].sum()), "n_jb_win": int(A["jb"][w0:wE + 1 + H_OUT].sum()),
           "g5_win": int(_g5(valid, int(b[-1]), int(b[0]))[w0:wE + 1 + H_OUT].sum()), "cfg": {}, "cov": {}}
    for meth, R in CONFIGS:
        rows, stt, n_raw, alt_kept = events_one(A, member, spanst, cal, w0, wE, meth, R)
        out["cfg"][(meth, R)] = {"rows": rows, "stats": stt, "n_raw_all": n_raw, "alt_kept": alt_kept}
    # U13：scope＝covered（舊預設）主三格保留件數（描述）
    dfc = U.load_ohlc(t, scope="covered")
    if len(dfc):
        Ac = prep(dfc, cal)
        if len(Ac["bars"]):
            for meth, R in MAIN:
                rows, _, _, _ = events_one(Ac, member, spanst, cal, w0, wE, meth, R)
                out["cov"][(meth, R)] = sum(1 for d in rows if d["狀態"] == "保留")
    return out


# ═════════════ 彙總（⛔ 只寫計數）═════════════
def qd(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "平均": round(float(x.mean()), 4), "中位": round(float(np.median(x)), 4),
            "p90": round(float(np.percentile(x, 90)), 4), "零事件佔比": round(float((x == 0).mean()), 4)}


def summarize(ST, meth, R, cal, w0, wE, DPY, nblk):
    acc = {"偵測_全期": 0, "偵測_窗內": 0, "窗內但不在母體": 0, "母體內_原始": 0, "純合併後_不看剔除": 0,
           "合併掉": 0, "剔除_硬斷點": 0, "剔除_T+1停牌": 0, "保留": 0}
    flag = {"硬斷點": 0, "T+1停牌": 0, "T+1停牌_其中已下市": 0}
    kf = {"R-跳躍P1_會多剔除": 0, "R-停牌S1_會多剔除": 0, "R-移出_持有期內移出指數": 0, "R-移出_其中移出後到T+21仍有K棒": 0,
          "持有期內下市（最後成交價了結）": 0, "暖身_期中加入且用到入指數前": 0, "暖身_期初已在且用到2015-12": 0}
    lines = {"樞紐": 0, "線成立": 0, "突破結束": 0, "逾60日結束": 0, "被新樞紐取代": 0}
    per = []; kept = []; csv_rows = []; alt_kept = 0; cov_kept = 0
    for s in sorted(ST):
        S = ST[s]; X = S["cfg"][(meth, R)]
        acc["偵測_全期"] += X["n_raw_all"]; acc["偵測_窗內"] += X["stats"]["n_win"]
        acc["純合併後_不看剔除"] += X["stats"]["n_pure"]
        alt_kept += X["alt_kept"]; cov_kept += S["cov"].get((meth, R), 0)
        if meth != "丙":
            for k in lines:
                lines[k] += X["stats"][k]
        nk = 0
        for d in X["rows"]:
            acc["母體內_原始"] += 1; acc[d["狀態"]] += 1
            if d["狀態"] != "合併掉":
                flag["硬斷點"] += d["f_brk"]; flag["T+1停牌"] += d["f_halt"]
                flag["T+1停牌_其中已下市"] += int(d["f_halt"] and d["f_dl_t1"])
            if d["狀態"] == "保留":
                nk += 1; kept.append((s, d["T"]))
                kf["R-跳躍P1_會多剔除"] += int(d["f_jump"])
                kf["R-停牌S1_會多剔除"] += int(d["f_gap1"])
                kf["R-移出_持有期內移出指數"] += int(d["f_exit"])
                kf["R-移出_其中移出後到T+21仍有K棒"] += int(d["f_exit_bar"])
                kf["持有期內下市（最後成交價了結）"] += int(d["f_dl_in"])
                kf["暖身_期中加入且用到入指數前"] += int(d["f_warm_join"])
                kf["暖身_期初已在且用到2015-12"] += int(d["f_warm_2015"])
            row = {"ticker": s, "T": str(cal[d["T"]].date()), "first": str(cal[d["first"]].date())}
            if meth != "丙":
                row["anchors"] = "|".join(str(cal[a].date()) for a in d["anchors"]); row["conf"] = str(cal[d["conf"]].date())
            row["狀態"] = d["狀態"]
            for k in ("f_brk", "f_halt", "f_jump", "f_gap1", "f_exit", "f_exit_bar", "f_dl_in", "f_warm_join", "f_warm_2015"):
                row[k] = int(d[k])
            csv_rows.append(row)
        if S["expo_mem"] > 0:
            per.append({"yrs": S["expo_mem"] / DPY, "yrs_span": S["expo_span"] / DPY, "n": nk})
    acc["窗內但不在母體"] = acc["偵測_窗內"] - acc["母體內_原始"]
    P = pd.DataFrame(per); P["rate"] = P["n"] / P["yrs"]; P1 = P[P["yrs"] >= 1.0]
    Ps = P[P["yrs_span"] > 0].copy(); Ps["rate"] = Ps["n"] / Ps["yrs_span"]; Ps1 = Ps[Ps["yrs_span"] >= 1.0]
    K = pd.DataFrame(kept, columns=["t", "T"])
    blk = int(((K["T"] - w0) // BLOCK).nunique()) if len(K) else 0
    n_eff = int(min(len(K), blk))
    res = {"事件帳": acc, "剔除旗標_逐項（未被合併者；可重複）": flag, "保留事件的待定讀法旗標": kf,
           "R-合併_另一讀法保留件數": int(alt_kept),
           "U13_scope_covered_保留件數（描述）": int(cov_kept) if (meth, R) in MAIN else None,
           "保留事件數": int(len(K)), "相異檔數": int(K["t"].nunique()) if len(K) else 0,
           "有事件的曆月數": int(pd.Series([str(cal[t])[:7] for t in K["T"]]).nunique()) if len(K) else 0,
           "有事件的20日區段數": blk, "區段上限": nblk, "n_eff": n_eff,
           "出口": "出口③" if n_eff >= 100 else ("出口②" if n_eff >= 30 else "出口①"),
           "每檔每年_在指數日分母（主）": {**qd(P1["rate"]), "合併比率_事件每股票年": round(float(P["n"].sum() / P["yrs"].sum()), 4),
                                  "股票年": round(float(P["yrs"].sum()), 1)},
           "每檔每年_首末K棒跨距分母（台股Q6式，並報）": {**qd(Ps1["rate"]), "合併比率_事件每股票年": round(float(Ps["n"].sum() / Ps["yrs_span"].sum()), 4),
                                         "股票年": round(float(Ps["yrs_span"].sum()), 1)},
           "逐年保留事件數": {str(k): int(v) for k, v in pd.Series([cal[t].year for t in K["T"]]).value_counts().sort_index().items()} if len(K) else {},
           "最早保留事件年月": str(cal[int(K["T"].min())])[:7] if len(K) else None}
    if meth != "丙":
        res["線的帳（全期，含窗外）"] = lines
    return res, pd.DataFrame(csv_rows)


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ═════════════ 美股資料型態 fixture（UF1～UF8）═════════════
def _mkdf(o, h, c, dates, hb=None):
    l = np.fmin(o, c) - 0.37
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                       "hard_break": np.zeros(len(c), bool) if hb is None else hb}, index=pd.DatetimeIndex(dates))
    return df


def usm_fixtures():
    cal = U.load_calendar()
    out = []
    i0 = int(cal.searchsorted(pd.Timestamp("2016-10-03")))    # 教科書序列放在跨感恩節、聖誕、元旦的 NYSE 日曆上
    o, h, l, c = STM.build(n_after=40)
    m = len(c)
    k = 0.7351938217                                          # 非跳動單位的還原價（浮點）
    dates = cal[i0:i0 + m]
    wE = len(cal) - 1
    mem = np.ones(len(cal), bool)
    sps = np.full(len(cal), np.datetime64("2010-01-01"), dtype="datetime64[ns]")

    def run(df, member=mem, meth="甲", w0=0):
        A = prep(df, cal)
        rows, _, _, _ = events_one(A, member, sps, cal, w0, wE, meth, 5)
        return A, rows

    # UF1 NYSE 日曆＋浮點還原價：三畫法都抓在第 70 根對應的 NYSE 日；等比例縮放不改事件（線值對價格是一次齊次）
    base = _mkdf(o * k, h * k, c * k, dates)
    for meth in ("甲", "乙", "丙"):
        _, rows = run(base, meth=meth)
        assert rows and rows[0]["T"] == i0 + 70 and rows[0]["狀態"] == "保留", (meth, rows[:1])
        _, r2 = run(_mkdf(o, h, c, dates), meth=meth)
        assert [(d["T"], d["狀態"]) for d in rows] == [(d["T"], d["狀態"]) for d in r2], meth
    hol = [d for d in pd.bdate_range(dates[0], dates[-1]) if d not in set(dates)]
    assert len(hol) >= 3, hol
    out.append("UF1 NYSE 日曆（區間內 {} 個平日休市）＋浮點還原價 ×{}：甲乙丙 都抓在第 70 根＝{}；等比例縮放事件逐筆相同".format(
        len(hol), k, dates[70].date()))

    # UF2 無效 K 棒（seq5 ⑤）：第 85 根 high < 收盤 ⇒ 當作沒有 K 棒、計數 1；該日變成缺一天 ⇒ S0 不剔除、S1 旗標亮
    hb_ = h * k; hb_ = hb_.copy(); hb_[85] = c[85] * k - 0.01
    A, rows = run(_mkdf(o * k, hb_, c * k, dates))
    assert len(A["bad_dates"]) == 1 and not A["valid"][i0 + 85], A["bad_dates"]
    assert rows[0]["T"] == i0 + 70 and rows[0]["狀態"] == "保留" and rows[0]["f_gap1"] and not rows[0]["f_brk"], rows[0]
    out.append("UF2 無效 K 棒：高＜收那一根被丟掉（計數 1）；持有期內缺 1 天 ⇒ S0 照保留、S1 旗標亮")

    # UF3 轉接層硬斷點（seam／split_div）：範圍 [最早取點, T+21] 內 ⇒ 剔除；範圍外 ⇒ 照保留
    for pos_, meth, want in ((40, "甲", "剔除_硬斷點"), (91, "甲", "剔除_硬斷點"), (92, "甲", "保留"),
                             (20, "甲", "保留"), (20, "乙", "剔除_硬斷點"), (9, "乙", "保留"), (30, "甲", "剔除_硬斷點")):
        hb = np.zeros(m, bool); hb[pos_] = True
        _, rows = run(_mkdf(o * k, h * k, c * k, dates, hb), meth=meth)
        assert rows[0]["狀態"] == want, (pos_, meth, rows[0]["狀態"])
    out.append("UF3 硬斷點：甲（取點 30、50；T＝70）斷點在 30／40／91（＝T+21）⇒ 剔除，92、20 ⇒ 保留；乙（最早取點 10）斷點 20 ⇒ 剔除、9 ⇒ 保留")

    # UF4 連續缺日：持有期內缺 5 個交易日 ⇒ 硬斷點；缺 4 天 ⇒ 不是（S1 旗標亮）
    for nmiss, want in ((5, "剔除_硬斷點"), (4, "保留")):
        keep = np.ones(m, bool); keep[80:80 + nmiss] = False
        _, rows = run(_mkdf((o * k)[keep], (h * k)[keep], (c * k)[keep], dates[keep]))
        assert rows[0]["T"] == i0 + 70 and rows[0]["狀態"] == want and rows[0]["f_gap1"], (nmiss, rows[0])
    # 下市：最後一根在 T+10 ⇒ 之後缺日不算硬斷點、保留、f_dl_in
    keep = np.arange(m) <= 80
    _, rows = run(_mkdf((o * k)[keep], (h * k)[keep], (c * k)[keep], dates[keep]))
    assert rows[0]["狀態"] == "保留" and rows[0]["f_dl_in"] and not rows[0]["f_gap1"], rows[0]
    out.append("UF4 缺日：持有期內連缺 5 日 ⇒ 剔除、連缺 4 日 ⇒ 保留（S1 旗標亮）；T+10 後沒資料（下市）⇒ 不算缺日、保留、記持有期內下市")

    # UF5 T+1 沒有 K 棒 ⇒ 剔除_T+1停牌；T 之後全沒資料 ⇒ 另記已下市
    keep = np.ones(m, bool); keep[71] = False
    _, rows = run(_mkdf((o * k)[keep], (h * k)[keep], (c * k)[keep], dates[keep]))
    assert rows[0]["狀態"] == "剔除_T+1停牌" and not rows[0]["f_dl_t1"], rows[0]
    keep = np.arange(m) <= 70
    _, rows = run(_mkdf((o * k)[keep], (h * k)[keep], (c * k)[keep], dates[keep]))
    assert rows[0]["狀態"] == "剔除_T+1停牌" and rows[0]["f_dl_t1"], rows[0]
    out.append("UF5 T+1 無 K 棒 ⇒ 剔除_T+1停牌；T 之後全無資料 ⇒ 同剔除、另記已下市")

    # UF6 母體：T 當天不在指數 ⇒ 不是事件；持有期中移出 ⇒ 保留、旗標亮；窗首之前 ⇒ 不是事件
    mm = mem.copy(); mm[i0 + 70] = False
    _, rows = run(_mkdf(o * k, h * k, c * k, dates), member=mm)
    assert all(d["T"] != i0 + 70 for d in rows), rows[:1]
    mm = mem.copy(); mm[i0 + 80:] = False
    _, rows = run(_mkdf(o * k, h * k, c * k, dates), member=mm)
    assert rows[0]["T"] == i0 + 70 and rows[0]["狀態"] == "保留" and rows[0]["f_exit"] and rows[0]["f_exit_bar"], rows[0]
    _, rows = run(_mkdf(o * k, h * k, c * k, dates), w0=i0 + 71)
    assert all(d["T"] >= i0 + 71 for d in rows)
    out.append("UF6 母體：T 當天 member＝0 ⇒ 不成事件；持有期內移出 ⇒ 保留、記 R-移出；T 在窗首前 ⇒ 不成事件")

    # UF7 狀態機（台股 Q2 同一順序）：合併 20 日、被剔除者不開合併窗、純合併另計
    ev = [{"T": 10, "reason": ""}, {"T": 30, "reason": ""}, {"T": 31, "reason": ""}, {"T": 55, "reason": "硬斷點"},
          {"T": 60, "reason": ""}, {"T": 70, "reason": ""}]
    st, npure = assign(ev)
    assert st == ["保留", "合併掉", "保留", "剔除_硬斷點", "保留", "合併掉"], st
    assert npure == 3, npure                              # 純合併：10、31、55 各開一窗
    out.append("UF7 狀態機：T＝[10,30,31,55(斷點),60,70] ⇒ 保留／合併／保留／剔除／保留（被剔除的 55 不開窗）／合併；純合併 {} 筆".format(npure))

    # UF8 前視（真實美股資料型態）：隨機 12 檔、每檔 15 個日子 d；只給 d 以前的資料（截斷）或把 d 以後換成別檔的價格（突變）
    #     ⇒ T ≤ d 的偵測事件（T、最早取點、取點）完全相同；破壞版（樞紐提早一根確認）必須被同一比法抓到差異
    rng = np.random.default_rng(20260927)
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    pick = []
    for t in rng.permutation(tick):                           # 只取有 ≥ 600 根有效 K 棒的檔（前後各留空間）
        if len(prep(U.load_ohlc(t, scope="panel"), cal)["bars"]) >= 600:
            pick.append(str(t))
        if len(pick) == 12:
            break
    n_cmp = n_ev = bad = 0
    for t in pick:
        A = prep(U.load_ohlc(t, scope="panel"), cal)
        b = A["bars"]
        donor = prep(U.load_ohlc(pick[(pick.index(t) + 1) % len(pick)], scope="panel"), cal)
        for meth, R in (("甲", 5), ("乙", 5), ("丙", 5), ("甲", 3), ("乙", 10)):
            full = TM.detect_calendar(A["O"], A["H"], A["C"], meth, R)["events"]
            n_ev += len(full)
            for d in rng.choice(b[200:-30], 15, replace=False):
                d = int(d)
                key = lambda evs: [(e["T"], e["first"], e.get("anchors")) for e in evs if e["T"] <= d]
                cut = {x: A[x].copy() for x in ("O", "H", "C")}
                for x in cut:
                    cut[x][d + 1:] = np.nan
                assert key(TM.detect_calendar(cut["O"], cut["H"], cut["C"], meth, R)["events"]) == key(full), ("截斷", t, meth, R, d)
                mut = {x: A[x].copy() for x in ("O", "H", "C")}
                s = A["C"][d] / np.nanmedian(donor["C"])
                for x in mut:
                    mut[x][d + 1:] = donor[x][d + 1:] * s
                assert key(TM.detect_calendar(mut["O"], mut["H"], mut["C"], meth, R)["events"]) == key(full), ("突變", t, meth, R, d)
                n_cmp += 2
        # 鑑別力：lag＝R−1 的破壞版在同一組截斷比法下要抓到差異
        Ob, Hb, Cb = A["O"][b], A["H"][b], A["C"][b]
        piv = np.flatnonzero(TM.pivot_highs(Hb, 5))
        for s_ in piv[:25]:
            T_ = int(s_ + 4)
            if T_ + 1 >= len(b):
                continue
            f1 = TM.detect_pivot(Ob, Hb, Cb, "甲", 5, lag=4, trace=True)
            f2 = TM.detect_pivot(Ob[:T_ + 1], Hb[:T_ + 1], Cb[:T_ + 1], "甲", 5, lag=4, trace=True)
            if list(f1["trace"][:T_ + 1]) != list(f2["trace"][:T_ + 1]):
                bad += 1
            g1 = TM.detect_pivot(Ob, Hb, Cb, "甲", 5, trace=True)
            g2 = TM.detect_pivot(Ob[:T_ + 1], Hb[:T_ + 1], Cb[:T_ + 1], "甲", 5, trace=True)
            assert list(g1["trace"][:T_ + 1]) == list(g2["trace"][:T_ + 1]), ("正式版截斷後現行線不同", t, T_)
    assert n_ev > 0 and bad > 0, (n_ev, bad)
    out.append("UF8 前視（真實美股還原價 12 檔）：{} 次比對（截斷＋換成別檔價格）T≤d 事件全相同；該批偵測事件 {} 筆；"
               "破壞版（樞紐提早一根確認）截斷後被抓到 {} 次差異、正式版 0 次".format(n_cmp, n_ev, bad))
    for s in out:
        print("✅", s, flush=True)
    return out


def main():
    t0 = time.time()
    U.assert_pinned()
    fx_tw = STM.run_all()                                   # 台股 F1～F8（任一 assert 失敗 ⇒ 例外中止）
    fx_us = usm_fixtures()                                  # 美股資料型態 UF1～UF8
    if "--fixtures-only" in sys.argv:
        return
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cal = U.load_calendar()
    w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1]))
    assert cal[w0] == U.WINDOW[0] and cal[w1] == U.WINDOW[1], (cal[w0], cal[w1])
    wE = w1 - H_OUT
    usable = wE - w0 + 1
    nblk = -(-usable // BLOCK)
    DPY = usable / ((cal[wE] - cal[w0]).days / 365.25)
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    if lim:
        tick = tick[:lim]
    print("[資料] us-stock-data {}｜日曆 {} 根｜判定窗 {}～{} {} 日｜T 可落 {}～{}（{} 日）｜20 日區段上限 {}｜每年交易日 {:.2f}｜有 OHLC {} 檔".format(
        U.data_commit()[:10], len(cal), cal[w0].date(), cal[w1].date(), w1 - w0 + 1, cal[w0].date(), cal[wE].date(),
        usable, nblk, DPY, len(tick)), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, w0, wE)) as pool:
        res = pool.map(load_one, tick, chunksize=4)
    ST = {r["t"]: r for r in res if r is not None}
    print("[讀檔＋偵測] 可用 {} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)

    # 母體佔比（35 檔無 OHLC）＝ 窗內在指數股-日
    tot = no = 0
    nos = set(U.no_ohlc_tickers())
    for t in U.universe_table()["ticker"]:
        f = U.in_index(t); f = f[(f.index >= U.WINDOW[0]) & (f.index <= U.WINDOW[1])]
        k_ = int(f["member"].sum()); tot += k_
        if t in nos:
            no += k_
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    R_ = {"性質": "USREG-M pre 段：頻率盤點＋可判定性算術（⛔ 未計算任何報酬）",
          "登錄": {"seq2": "a3c98a07e882a574", "seq3": "81bfc48eff6258f5", "seq4": "cbfc7610923b9e53", "seq5": "ffb22ecb1bd749ff",
                 "台股原件PREREGM_seq1": "9316840579a8d33a"},
          "資料commit": U.data_commit(), "轉接層": "46e74a0c8b（backtest/us_data.py）",
          "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "窗交易日": int(w1 - w0 + 1),
          "T可落窗": [str(cal[w0].date()), str(cal[wE].date())], "T可落日數": int(usable),
          "20日區段上限": int(nblk), "60日區段上限（描述臂c）": int(-(-(w1 - H_C - 1 - w0 + 1) // H_C)),
          "每年交易日": round(DPY, 3), "有OHLC檔數": len(tick), "可用檔數": len(ST),
          "窗內在指數股日": int(tot), "其中無OHLC35檔": int(no), "35檔股日佔比": round(no / tot, 5),
          "設計參數": {"R主格": TM.R_MAIN, "描述臂R": [3, 10], "跨度": TM.MAX_SPAN, "有效期": TM.LIFE, "乙第三點": TM.TOL3,
                   "丙N": TM.REG_N, "丙R2": TM.REG_R2, "合併": MERGE, "區段": BLOCK, "硬斷點連缺": U.GAP_BREAK_DAYS},
          "fixture_台股F1_F8": fx_tw, "fixture_美股UF1_UF8": fx_us,
          "資料診斷": {"無效K棒（seq5⑤）": int(sum(S["n_invalid"] for S in ST.values())),
                   "無效K棒_檔數": int(sum(1 for S in ST.values() if S["n_invalid"])),
                   "無效K棒帶斷點而移位": int(sum(S["moved"] for S in ST.values())),
                   "不在NYSE日曆的K棒": int(sum(S["n_off"] for S in ST.values())),
                   "轉接層硬斷點根數（scope＝panel，全期）": int(sum(S["n_pb"] for S in ST.values())),
                   "P1跳躍根數（窗首～窗尾，含 T+21 延伸）": int(sum(S["n_jb_win"] for S in ST.values())),
                   "P1跳躍_檔數": int(sum(1 for S in ST.values() if S["n_jb_win"])),
                   "連缺≥5日的缺日天數（同範圍）": int(sum(S["g5_win"] for S in ST.values())),
                   "連缺≥5日_檔數": int(sum(1 for S in ST.values() if S["g5_win"]))},
          "畫法": {}}
    shas = []
    for meth, R in CONFIGS:
        nm = cfg_name(meth, R)
        s, dfc = summarize(ST, meth, R, cal, w0, wE, DPY, nblk)
        R_["畫法"][nm] = s
        p = os.path.join(WORK, "events_{}.csv".format(nm))
        dfc.to_csv(p, index=False, encoding="utf-8")
        shas.append((os.path.basename(p), len(dfc), sha256f(p)))
        a = s["事件帳"]
        print("[{}] 偵測窗內 {:,}｜母體內 {:,}｜純合併 {:,}｜合併掉 {:,}｜剔除 斷點 {:,}／停牌 {:,}｜保留 {:,}｜檔 {}｜月 {}｜區段 {}/{}｜n_eff {}｜{}".format(
            nm, a["偵測_窗內"], a["母體內_原始"], a["純合併後_不看剔除"], a["合併掉"], a["剔除_硬斷點"], a["剔除_T+1停牌"],
            a["保留"], s["相異檔數"], s["有事件的曆月數"], s["有事件的20日區段數"], nblk, s["n_eff"], s["出口"]), flush=True)
    # 逐檔診斷（⛔ 只放 ~/us_work）
    diag = pd.DataFrame([{"ticker": S["t"], "expo_mem_days": S["expo_mem"], "expo_span_days": S["expo_span"],
                          "n_invalid": S["n_invalid"], "invalid_dates": "|".join(S["bad_dates"]), "n_pb": S["n_pb"],
                          "n_jb_win": S["n_jb_win"], "g5_win": S["g5_win"],
                          **{"kept_" + cfg_name(m_, r_): sum(1 for d in S["cfg"][(m_, r_)]["rows"] if d["狀態"] == "保留") for m_, r_ in CONFIGS}}
                         for S in ST.values()])
    p = os.path.join(WORK, "per_ticker.csv"); diag.to_csv(p, index=False, encoding="utf-8")
    shas.append((os.path.basename(p), len(diag), sha256f(p)))
    with io.open(os.path.join(OUT, "pre_work_sha.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usm/，repo 外）", "rows", "sha256"]); w.writerows(shas)
    R_["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    R_["耗時秒"] = round(time.time() - t0, 1)
    json.dump(R_, open(os.path.join(OUT, "pre_freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in R_.items() if k != "畫法"}, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(R_["畫法"], ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

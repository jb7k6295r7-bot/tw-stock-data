# -*- coding: utf-8 -*-
"""集保 400 張以上大戶比例 4 週升幅前 5%：買進抱 60 日（全收版、10 檔版）組合層 seq1（台股策略線 sha b6c00cb614caa84e；裁定 seq507 發號、seq508 核頻率表）

    頻率表＋逐筆對照（⛔ 不出報酬）：
        cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigHolderRise
    正式跑（⛔ 沒帶閘就不出報酬；逐筆一致率 < 98% 也不出）：
        cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigHolderRise --formal --ruling seq508
    selftest：backtest/selftest_researchBigHolderRise.py

═══ 訊號（裁定 seq508：照情報 #76 run.py 讀法；情報交件 `_交付-大戶比例上升76事件清單與程式_情報線-20261117-1546/` §二）═══
 資料：tw-stock-data commit e2fdcdef9（＝ #76 同 sha）git archive 到 ~/h2data/<sha>/data（唯讀）
 母體候選：meta/stocks.csv kind＝stock、market∈{twse,tpex}、代號 ^[1-9]\\d{3}$（含已下市）
 價格：stocks/<代號>.csv 只取 market∈{twse,tpex} 列；有效成交 ＝ valid_bar＝1 且 close＞0；
   還原 ＝ adj/<代號>.csv 的 factor：事件日之前的開盤、收盤乘上去（事件日當天開盤已是除權後價）
 交易日 ＝ 當天 ≥ 300 檔有效成交（排除零星列）
 集保：tdcc_hist parquet ＋ tdcc csv（重疊資料日以 csv 為準）、排除 2023-10-20；
   大戶比例 ＝ 第 12～15 級 shares ÷ 第 1～15 級 shares；週 ＝ (資料日 − 2017-01-02)//7，同週取較晚那份
   Δ4 ＝ 比例(週 w) − 比例(週 w−4)：只認剛好 4 週前那一週（⛔ 沒有天數容差；那週缺 ⇒ 沒有 Δ4）
 每週母體：資料日前 6 天內有有效成交；前 20 個交易日平均成交額 ≥ 5,000 萬（停牌日記 0、資料日當天或之前最後一個交易日往回 20 個）；
   前 20 日報酬、進場開盤、出場收盤都要有值；有集保比例
 每週（Δ4 有值的母體）< 50 檔 ⇒ 不算；B ＝ Δ4 ≥ 第 95 百分位（pandas 線性內插）且 > 0
 進場 ＝ 資料日 +2 日曆日當天或之後第一個交易日開盤（那檔當天沒開盤 ⇒ 不在母體，⛔ 不順延）；
 出場 ＝ 進場日算第 1 天的第 60 個交易日收盤；停牌、下市用最後有效收盤（ffill）；60 日出場超過資料尾的週不算
 段：依進場日 探索 2018-11-01～2021-12-31｜確認 2022-01-01～資料尾；兩段各自空倉起算

═══ 組合（位置模擬；頻率表與正式跑同一條路）═══
 全收版：12 份輪動；每週用一份「已出場（排程出場根 < 本次進場根）」的空份，等權買進當週全部訊號、抱滿 60 根；
   每份金額 ＝ 前一日權益 ÷ 12（不超過現金）；12 份都還沒出場 ⇒ 本週略過（週數照報）
 10 檔版：最多 10 檔、每檔 ＝ 前一日權益 ÷ 10（不超過現金）；進場日空位 ＝ 10 − 持有中（出場根 ≥ 進場根）；
   從當週訊號依 Δ4 大到小補；已持有的同一檔不重複買
 成本：來回 0.585%，出場時以進場金額一次扣（research11／sim_swap 同口徑）
 真實成本版：researchSlip 現實版（C1 每邊 +0.3%、C2 平方根衝擊 50 萬 ÷ 檔數、C3 一字漲跌停、C4 均價）——
   researchSlip.stock_extra／arm_inputs 算毛報酬與可成交旗標，researchSwapWorst.can_trade 判買不買得到；跌停賣不掉延後同 sim_swap
 年化／回落 ＝ benchmark_rejudge.estat；大盤 ＝ benchmark_rejudge.bstat（origin/main data/history/market_tri.csv）；0050 ＝ benchmark_rejudge.bench0050

═══ 與營量 v1 的重疊（頻率表）═══
 ① 持倉重疊 ② 新買前後 5 日 ③ 候選前後 5 日（只 2025-08～2026-06）；出處見 load_yl

輸出：freq/（頻率表.md、freq.csv、weekly.csv、signals.csv、align76.md、align76_diff.csv、equiv76.md、data_check.csv、event_inventory.csv、run.log）
      formal/（結果.md、result.json、cells.csv、curves.csv、random200.csv、trades.csv、run.log）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from backtest import data as D

SHA = "e2fdcdef97bd527f8c4d754bb3657434e9a9851e"
DATA = os.path.expanduser(f"~/h2data/{SHA}/data")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsBigHolderRise", "freq")
OUTF = os.path.join(HERE, "resultsBigHolderRise", "formal")
YFA = os.path.join(HERE, "resultsYFallin")
YLL = os.path.join(HERE, "resultsYLlist")
B60_CSV = "/mnt/c/SynologyDrive/跨線信箱/_交付-大戶比例上升76事件清單與程式_情報線-20261117-1546/B60_事件清單.csv"
AMT_MIN = 5e7
Q = 0.95
HOLD = 60
NFULL = 12
NTEN = 10
MIN_UNI = 50
CAL_MIN = 300
COST = 0.00585
EXCL_DATE = "2023-10-20"
WK0 = "2017-01-02"
RULING = "seq508"
ALIGN_MIN = 0.98
NRAND = 200
SEED_RAND = 20261117
REAL_SPEC = dict(s=0.003, cap=500_000, c3=True, c4=True)      # researchSlip「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」
SEGS = {"探索": ("2018-11-01", "2021-12-31"), "確認": ("2022-01-01", "2099-12-31")}
LOGS: list[str] = []


def log(s=""):
    print(s, flush=True); LOGS.append(str(s))


# ───────── 閘 ─────────
def parse_args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None)
    ap.add_argument("--b60", default=B60_CSV)
    ap.add_argument("--procs", type=int, default=3)
    return ap.parse_args(argv)


def formal_allowed(a) -> bool:
    """正式跑閘：--formal 且 --ruling seq508 兩個都要。"""
    return bool(a.formal) and a.ruling == RULING


# ───────── 訊號核心（#76 讀法；純函式，selftest 用）─────────
def sig_mask(x: pd.Series) -> pd.Series:
    """當週 Δ4 ≥ 第 95 百分位（pandas 線性內插）且 > 0。"""
    q = x.quantile(Q)
    return (x >= q) & (x > 0)   # _MUT_SIG


def week_no(dates) -> np.ndarray:
    return np.asarray((pd.DatetimeIndex(dates) - pd.Timestamp(WK0)).days // 7)


def delta4_frame(B: pd.DataFrame):
    """B：資料日 × 股 的大戶比例（index 已排序）。回 (bw 週×股, dates 週→資料日, D4 週×股)。
    同一週兩份取較晚那份；Δ4 只認剛好 4 週前那一週（缺 ⇒ NaN）。"""
    B = B.sort_index()
    wk = week_no(B.index)
    keep = ~pd.Index(wk).duplicated(keep="last")
    bw = B[keep].copy(); dates = pd.Series(B.index[keep], index=wk[keep])
    bw.index = wk[keep]
    full = bw.reindex(range(int(bw.index.min()), int(bw.index.max()) + 1))
    D4 = (full - full.shift(4)).reindex(bw.index)   # _MUT_D4
    return bw, dates, D4


# ───────── 讀資料（#76 run.py 同式）─────────
def load_px(ids):
    px = {}
    for sid in ids:
        p = os.path.join(DATA, "stocks", f"{sid}.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, usecols=["date", "market", "open", "close", "amount", "valid_bar"], dtype={"market": str})
        d = d[d.market.isin(["twse", "tpex"])]
        d["date"] = pd.to_datetime(d.date)
        d = d.sort_values("date").drop_duplicates("date")
        m = np.ones(len(d))
        a = os.path.join(DATA, "adj", f"{sid}.csv")
        if os.path.exists(a):
            e = pd.read_csv(a, usecols=["date", "factor"])
            e = e[pd.to_numeric(e.factor, errors="coerce").notna()]
            e["date"] = pd.to_datetime(e.date, errors="coerce"); e = e.dropna()
            dd = d.date.values
            for ed, f in zip(e.date.values, e.factor.astype(float).values):
                m[dd < ed] *= f
        d["ao"] = d.open * m; d["ac"] = d.close * m
        d["ok"] = (d.valid_bar == 1) & d.close.notna() & (d.close > 0)
        px[sid] = d.set_index("date")
    return px


def load_tdcc76(ids):
    ids = set(ids)
    frames = []
    for f in sorted(glob.glob(os.path.join(DATA, "tdcc_hist", "*.parquet"))):
        t = pd.read_parquet(f, columns=["date", "stock_id", "level", "shares"])
        t["stock_id"] = t.stock_id.astype(str); t["date"] = pd.to_datetime(t.date.astype(str))
        frames.append(t[t.stock_id.isin(ids) & (t.level <= 15)])
    H = pd.concat(frames)
    C = pd.concat([pd.read_csv(f, dtype={"stock_id": str}, usecols=["date", "stock_id", "level", "shares"])
                   for f in sorted(glob.glob(os.path.join(DATA, "tdcc", "*.csv")))])
    C["date"] = pd.to_datetime(C.date); C = C[C.stock_id.isin(ids) & (C.level <= 15)]
    H = H[~H.date.isin(set(C.date))]          # 重疊資料日以 tdcc csv 為準
    T = pd.concat([H, C])
    T = T[T.date != pd.Timestamp(EXCL_DATE)]
    g = T.assign(big=np.where(T.level >= 12, T.shares, 0)).groupby(["date", "stock_id"])[["shares", "big"]].sum()
    g = g[g.shares > 0]
    return (g.big / g.shares).unstack().sort_index()


def build76():
    """回 dict：cal、寬表、週列表、面板、訊號表。"""
    meta = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    meta = meta[meta.stock_id.str.match(r"^[1-9]\d{3}$") & meta.market.isin(["twse", "tpex"]) & (meta.kind == "stock")]
    ids = sorted(set(meta.stock_id))
    mk = dict(zip(meta.stock_id, meta.market))
    log(f"[母體候選] 四碼普通股（上市櫃，含已下市）{len(ids)}")
    px = load_px(ids)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(v.index) for v in px.values()])))
    cnt = pd.Series(0, index=cal)
    for v in px.values():
        cnt = cnt.add(v.ok.astype(int).reindex(cal, fill_value=0), fill_value=0)
    cal = cnt[cnt >= CAL_MIN].index
    log(f"[價量] 有日線 {len(px)}｜交易日（≥{CAL_MIN} 檔有效成交）{len(cal)} 個 {cal[0].date()}～{cal[-1].date()}")
    AC = pd.DataFrame({s: v.ac.where(v.ok) for s, v in px.items()}).reindex(cal)
    AO = pd.DataFrame({s: v.ao.where(v.ok) for s, v in px.items()}).reindex(cal)
    AMT = pd.DataFrame({s: v.amount.where(v.ok) for s, v in px.items()}).reindex(cal)
    OK = AC.notna()
    ACf = AC.ffill()
    AMT20 = AMT.fillna(0).rolling(20, min_periods=20).mean()
    Bdt = load_tdcc76(ids)
    bw, dates, D4 = delta4_frame(Bdt)
    allw = set(range(int(bw.index.min()), int(bw.index.max()) + 1))
    log(f"[集保] 資料日 {len(Bdt)}（同週去重後 {len(bw)} 週）{dates.iloc[0].date()}～{dates.iloc[-1].date()}｜缺週 {len(allw - set(bw.index))}")
    n = len(cal)
    weeks = []; rows = []
    for w, d in dates.items():
        wrow = {"wk": int(w), "d": d, "lag": (dates.get(w - 4, pd.NaT)), "e": None, "x": None, "uni": 0, "uni_all": 0, "nsig": 0,
                "buys": [], "buys_ranked": [], "d4": [], "q95": np.nan, "nobuy": 0, "status": ""}
        i_d = int(cal.searchsorted(d, side="right")) - 1
        if i_d < 25:
            wrow["status"] = "交易日不足"; weeks.append(wrow); continue
        ent = int(cal.searchsorted(d + pd.Timedelta(days=2), side="left"))
        if ent >= n:
            wrow["status"] = "進場日超過資料尾"; weeks.append(wrow); continue
        ex = ent + HOLD - 1
        wrow["e"] = ent
        if ex >= n:
            wrow["status"] = "60日出場超過資料尾"; weeks.append(wrow); continue
        wrow["x"] = ex
        wk_lo = int(cal.searchsorted(d - pd.Timedelta(days=6), side="left"))
        okw = OK.iloc[wk_lo:i_d + 1].any()
        liq = AMT20.iloc[i_d] >= AMT_MIN
        r20 = ACf.iloc[i_d] / ACf.iloc[i_d - 20] - 1
        eo = AO.iloc[ent]
        ret = ACf.iloc[ex] / eo - 1
        uni = okw & liq & eo.notna() & r20.notna() & ret.notna()
        uni = uni[uni].index.intersection(bw.columns)
        dv = D4.loc[w, uni]
        x = dv.dropna()
        wrow["uni_all"] = len(uni); wrow["uni"] = len(x)
        for s in uni:
            rows.append((int(w), d, s, float(dv[s]) if pd.notna(dv[s]) else np.nan, ent, ex, float(ret[s])))
        if len(x) < MIN_UNI:
            wrow["status"] = "Δ4母體<50"; weeks.append(wrow); continue
        m = sig_mask(x)
        sg = x[m].sort_values(ascending=False, kind="mergesort")
        wrow.update(status="ok", q95=float(x.quantile(Q)), nsig=len(sg), buys=list(sg.index), buys_ranked=list(sg.index), d4=list(sg.values))
        weeks.append(wrow)
    P = pd.DataFrame(rows, columns=["wk", "date", "sid", "d4", "e", "x", "ret"])
    sr = []
    for w in weeks:
        if w["status"] != "ok":
            continue
        for rk, (s, v) in enumerate(zip(w["buys"], w["d4"]), 1):
            sr.append({"資料日": w["d"].date(), "前4週資料日": (w["lag"].date() if pd.notna(w["lag"]) else ""), "進場日": cal[w["e"]].date(),
                       "出場日": cal[w["x"]].date(), "sid": s, "升幅_pp": round(v * 100, 6), "當週名次": rk, "當週母體": w["uni"],
                       "第95百分位_pp": round(w["q95"] * 100, 6), "e": w["e"], "x": w["x"]})
    SIG = pd.DataFrame(sr)
    log(f"[訊號] 週 {len(weeks)}（ok {sum(w['status'] == 'ok' for w in weeks)}）｜訊號 {len(SIG)}｜面板列 {len(P)}")
    return {"cal": cal, "AO": AO, "ACf": ACf, "OK": OK, "AMT20": AMT20, "D4": D4, "bw": bw, "dates": dates, "weeks": weeks,
            "P": P, "SIG": SIG, "mk": mk, "ids": ids, "Bdt": Bdt}


# ───────── 逐筆對照（情報 B60 事件清單）─────────
def align(Bx, path):
    them = pd.read_csv(path, dtype={"代號": str}, encoding="utf-8-sig")
    them = them[them["格"] == "B60"]
    them["k"] = them["資料日"].astype(str) + "|" + them["代號"]
    SIG = Bx["SIG"]
    me = SIG.assign(k=SIG["資料日"].astype(str) + "|" + SIG["sid"])
    A, Bk = set(me["k"]), set(them["k"])
    inter = A & Bk; uni = A | Bk
    J = me.merge(them[["k", "升幅_百分點"]], on="k")
    dmax = float((J["升幅_pp"] - J["升幅_百分點"]).abs().max()) if len(J) else np.nan
    P = Bx["P"]; weeks = {w["d"]: w for w in Bx["weeks"]}
    pidx = P.set_index(["date", "sid"])
    diff = []
    for k in sorted(uni - inter):
        ds, s = k.split("|"); d = pd.Timestamp(ds); side = "只本線" if k in A else "只情報"
        w = weeks.get(d)
        if w is None:
            typ = "該資料日本線沒有（同週去重或排除日）"; info = ""
        elif w["status"] != "ok":
            typ = f"該週本線不算（{w['status']}）"; info = ""
        elif (d, s) not in pidx.index:
            typ = "不在本線母體"; info = ""
        else:
            v = pidx.loc[(d, s), "d4"]
            if pd.isna(v):
                typ = "本線 Δ4 缺"; info = ""
            else:
                typ = "門檻邊緣" if side == "只情報" else "本線過門檻、情報沒有"; info = f"本線Δ4={v * 100:.4f}pp 門檻={w['q95'] * 100:.4f}pp"
        diff.append({"資料日": ds, "代號": s, "邊": side, "類型": typ, "說明": info})
    DF = pd.DataFrame(diff, columns=["資料日", "代號", "邊", "類型", "說明"])
    r = {"本線筆數": len(A), "情報筆數": len(Bk), "交集": len(inter), "聯集": len(uni),
         "一致率_交集除聯集": len(inter) / len(uni) if uni else np.nan,
         "情報被本線覆蓋": len(inter) / len(Bk) if Bk else np.nan, "本線被情報覆蓋": len(inter) / len(A) if A else np.nan,
         "交集升幅最大差_pp": dmax, "差異類型": DF.groupby(["邊", "類型"]).size().to_dict() if len(DF) else {}}
    return r, DF


# ───────── 組合模擬（只用位置；頻率表用）─────────
def sim_full(W, cal, last_pos, seg_lo, seg_hi):
    """全收版：W ＝ 段內週列表（dict：d, e, buys[sid...]）。回 cohorts、positions、conflicts。"""
    slot_exit = [-1] * NFULL; cohorts = []; pos = []; conflict = []
    for w in W:
        e = w["e"]
        free = [i for i in range(NFULL) if slot_exit[i] < e]
        if not w["buys"]:
            cohorts.append({"d": w["d"], "slot": -1, "n": 0, "e": e}); continue
        if not free:
            conflict.append({"d": w["d"], "slot": -1, "n": len(w["buys"])}); continue
        k = free[0]
        x = D.exit_pos(e, HOLD)
        slot_exit[k] = x
        cohorts.append({"d": w["d"], "slot": k, "n": len(w["buys"]), "e": e, "x": x})
        for s in w["buys"]:
            pos.append({"sid": s, "e": e, "x": x, "w": 1 / NFULL / len(w["buys"]), "slot": k})
    return cohorts, pos, conflict


def rigid_conflict(W):
    """另一讀法：死板輪（週序 mod 12）時，輪到的那份還沒出場的週數。"""
    slot_exit = [-1] * NFULL; n = 0
    d0 = W[0]["d"] if W else None
    for w in W:
        if not w["buys"]:
            continue
        k = int(round((w["d"] - d0).days / 7)) % NFULL
        if slot_exit[k] >= w["e"]:
            n += 1; continue
        slot_exit[k] = D.exit_pos(w["e"], HOLD)
    return n


def sim_ten(W):
    held = []  # (sid, e, x)
    pos = []; st = {"free_no_sig": 0, "full_skip": 0, "dup_skip": 0, "free_weeks": 0, "weeks": 0}
    for w in W:
        e = w["e"]; st["weeks"] += 1
        held = [h for h in held if h[2] >= e]
        free = NTEN - len(held)
        hs = {h[0] for h in held}
        cand = [s for s in w["buys_ranked"] if s not in hs]
        st["dup_skip"] += len(w["buys_ranked"]) - len(cand)
        if free > 0:
            st["free_weeks"] += 1
            if not w["buys_ranked"]:
                st["free_no_sig"] += 1
        take = cand[:max(free, 0)]
        st["full_skip"] += len(cand) - len(take)
        x = D.exit_pos(e, HOLD)
        for s in take:
            held.append((s, e, x)); pos.append({"sid": s, "e": e, "x": x, "w": 1 / NTEN})
    return pos, st


def daily_occupancy(pos, lo, hi, nslot, kind, cohorts=None):
    """lo..hi（含）每個交易日：持有部位數、不同檔數、空份比例。"""
    n = hi - lo + 1
    cnt = np.zeros(n); occ = np.zeros(n)
    sets = [set() for _ in range(n)]
    for p in pos:
        a = max(p["e"], lo); b = min(p["x"], hi)
        if a > b:
            continue
        cnt[a - lo:b - lo + 1] += 1
        for t in range(a, b + 1):
            sets[t - lo].add(p["sid"])
    if kind == "full":
        for c in cohorts or []:
            if c.get("n", 0) == 0 or "x" not in c:
                continue
            a = max(c["e"], lo); b = min(c["x"], hi)
            if a <= b:
                occ[a - lo:b - lo + 1] += 1
    else:
        occ = cnt.copy()
    dist = np.array([len(s) for s in sets], float)
    cash = 1 - np.minimum(occ, nslot) / nslot
    return cnt, dist, cash


# ───────── 組合模擬（報酬；正式跑用）─────────
def sim_book(kind, W, x, y, C, O, cost=COST, pick="top", rng=None, drop=None, real=None):
    """kind ∈ {full, ten}；W ＝ 週列表（dict：e、cols＝欄位序（Δ4 大到小）、sids）；在 [x, y] 逐日模擬。
    C ＝ 還原收盤（ffill）T×S、O ＝ 還原開盤 T×S。drop ＝ {(e, col)}：那筆照買（佔份）但改持現金、不扣成本。
    real ＝ None 或 dict（g：{(e,col)：毛報酬}、op：{sid：均價}、trd：tradable、dl：delist、cost）。
    每日順序：延後賣出（開盤）→ 買進（開盤）→ 排程出場（收盤）→ 記權益。"""
    nd = y - x + 1
    eq = np.ones(nd); cash = 1.0; prev = 1.0
    openp = []        # [ex, col, sid, amt, ep, e, dropped]
    trades = []; skipped = []; entries = []; slot_exit = [-1] * NFULL
    st = {"買進": 0, "略過週": 0, "略過訊號": 0, "已持有略過": 0, "滿了沒買": 0, "一字漲停買不到": 0, "跌停延後": 0, "下市結算": 0}
    if real is not None:
        cost = real["cost"]
        from backtest.researchSwapWorst import can_trade
    byE: dict = {}
    for w in W:                       # 兩個資料週可能同一進場日（連假）⇒ 依序各自處理（頻率表 sim_full／sim_ten 同）
        if x <= w["e"] <= y:
            byE.setdefault(w["e"], []).append(w)
    delayed = set()

    def sell(p, gross, t, how):
        nonlocal cash
        ex, col, sid, amt, ep, e, dropped = p
        if dropped:
            cash += amt; g = 0.0
        else:
            cash += amt * (1 + gross - cost)   # _MUT_COST
            g = gross
        trades.append({"e": e, "col": col, "sid": sid, "t_sell": t, "amt": amt, "gross": g, "dropped": bool(dropped), "how": how})

    for t in range(x, y + 1):
        # ① 延後賣出（真實成本版：排程出場日賣不掉 ⇒ 第一個賣得掉的開盤）
        if real is not None and openp:
            still = []
            for p in openp:
                ex, col, sid, amt, ep, e, dropped = p
                if ex < t:
                    tb = real["trd"][sid]; o_t = float(real["op"][sid][t]); dl = real["dl"].get(sid)
                    if dl is not None and (not tb["trd"][t]) and t > dl["last"] and str(dl["status"]).startswith("delisted"):
                        st["下市結算"] += 1; sell(p, real["g"][(e, col)], t, "下市"); continue
                    if (not tb["trd"][t]) or tb["dn_o"][t] or not np.isfinite(o_t) or o_t <= 0:
                        still.append(p); continue
                    e_avg = float(real["op"][sid][e])
                    sell(p, o_t / e_avg - 1.0, t, "延後"); continue
                still.append(p)
            openp = still
        # ② 買進
        for w in byE.get(t, []):
            if kind == "full":
                free = [i for i in range(NFULL) if slot_exit[i] < t]   # _MUT_SLOT
                if not free:
                    st["略過週"] += 1; st["略過訊號"] += len(w["cols"]); skipped.append(w["e"])
                else:
                    k = free[0]; slot_exit[k] = t + HOLD - 1
                    per = min(prev / NFULL, cash) / len(w["cols"])
                    for col, sid in zip(w["cols"], w["sids"]):
                        if real is not None and not can_trade(real["trd"], real["op"], sid, t, "buy"):
                            st["一字漲停買不到"] += 1; continue
                        ep = float(real["op"][sid][t]) if real is not None else float(O[t, col])
                        cash -= per
                        openp.append([t + HOLD - 1, col, sid, per, ep, t, (t, col) in drop if drop else False]); st["買進"] += 1; entries.append(t)
            else:
                held = {p[1] for p in openp}
                free = NTEN - len(openp)
                cand = [(c, s) for c, s in zip(w["cols"], w["sids"]) if c not in held]   # _MUT_DUP
                st["已持有略過"] += len(w["cols"]) - len(cand)
                if pick == "rand":
                    cand = [cand[i] for i in rng.permutation(len(cand))]
                take = cand[:max(free, 0)]
                st["滿了沒買"] += len(cand) - len(take)
                for col, sid in take:
                    if real is not None and not can_trade(real["trd"], real["op"], sid, t, "buy"):
                        st["一字漲停買不到"] += 1; continue
                    amt = min(prev / NTEN, cash)
                    if amt <= 1e-12:
                        break
                    ep = float(real["op"][sid][t]) if real is not None else float(O[t, col])
                    cash -= amt
                    openp.append([t + HOLD - 1, col, sid, amt, ep, t, (t, col) in drop if drop else False]); st["買進"] += 1; entries.append(t)
        # ③ 排程出場（收盤）
        still = []
        for p in openp:
            ex, col, sid, amt, ep, e, dropped = p
            if ex == t:
                if real is None:
                    sell(p, C[ex, col] / ep - 1.0, t, "排程"); continue
                tb = real["trd"][sid]
                if tb["trd"][t] and not tb["dn_c"][t]:
                    sell(p, real["g"][(e, col)], t, "排程"); continue
                dl = real["dl"].get(sid)
                if dl is not None and (not tb["trd"][t]) and t > dl["last"] and str(dl["status"]).startswith("delisted"):
                    st["下市結算"] += 1; sell(p, real["g"][(e, col)], t, "下市"); continue
                st["跌停延後"] += 1
            still.append(p)
        openp = still
        hv = 0.0
        for ex, col, sid, amt, ep, e, dropped in openp:
            hv += amt if dropped else amt * C[t, col] / (O[e, col] if real is not None else ep)
        eq[t - x] = cash + hv; prev = eq[t - x]
    return {"eq": eq, "trades": trades, "skipped": skipped, "entries": entries, "st": st, "open_end": len(openp)}


def full_eq(r, x, T):
    """段內權益 ⇒ 全日曆長度（段前 1、段後延尾），給 benchmark_rejudge.estat。"""
    e = np.ones(T); e[x:x + len(r["eq"])] = r["eq"]; e[x + len(r["eq"]):] = r["eq"][-1]
    return e


# ───────── 營量 v1 ─────────
def load_yl():
    d = pd.read_csv(os.path.join(YFA, "daily_W.csv.gz"), usecols=["世界", "帳", "t", "日期"])
    d = d[(d["世界"] == "主") & (d["帳"] == "YL")]
    t2d = dict(zip(d["t"].astype(int), pd.to_datetime(d["日期"])))
    T = pd.read_csv(os.path.join(YFA, "trades_W.csv.gz"), usecols=["世界", "帳", "side", "t", "sid"], dtype={"sid": str})
    T = T[(T["世界"] == "主") & (T["帳"] == "YL")].sort_values("t")
    yl_end = max(t2d.values())
    iv = {}; buys = {}
    for s, g in T.groupby("sid"):
        b = g[g["side"] == "buy"]["t"].astype(int).tolist(); se = g[g["side"] == "sell"]["t"].astype(int).tolist()
        for bt in b:
            st = next((x for x in se if x > bt), None)
            bd = t2d[bt]; sd = t2d.get(st, yl_end) if st is not None else yl_end
            iv.setdefault(s, []).append((bd, sd)); buys.setdefault(s, []).append(bd)
    cands = []
    for f in glob.glob(os.path.join(YLL, "營量v1名單_*.csv")) + glob.glob(os.path.join(YLL, "營量v1未入選候選_*.csv")):
        c = pd.read_csv(f, usecols=["進場日", "代號"], dtype={"代號": str}, encoding="utf-8-sig")
        cands.append(c)
    C = pd.concat(cands); C["進場日"] = pd.to_datetime(C["進場日"])
    cset = {}
    for s, g in C.groupby("代號"):
        cset[s] = sorted(g["進場日"].tolist())
    return iv, buys, cset, yl_end, (C["進場日"].min(), C["進場日"].max(), len(C), len(glob.glob(os.path.join(YLL, "營量v1*候選*.csv"))))


def overlap(rows, cal, iv, buys, cset, yl_end):
    """rows：list of (sid, entry_pos)。回 dict。"""
    cpos = {d: i for i, d in enumerate(cal)}
    n = n1 = n2 = 0; m3 = h3 = 0
    for s, e in rows:
        ed = cal[e]
        if ed > yl_end:
            continue
        n += 1
        if any(a <= ed <= b for a, b in iv.get(s, [])):
            n1 += 1
        if any(abs(cpos.get(bd, -10**6) - e) <= 5 for bd in buys.get(s, [])):
            n2 += 1
        if pd.Timestamp("2025-08-01") <= ed <= pd.Timestamp("2026-06-30"):
            m3 += 1
            if any(abs(cpos.get(cd, -10**6) - e) <= 5 for cd in cset.get(s, [])):
                h3 += 1
    f = lambda a, b: (a / b if b else np.nan)
    return {"n": n, "持倉重疊": n1, "持倉重疊比": f(n1, n), "新買±5日重疊": n2, "新買±5日重疊比": f(n2, n),
            "候選n_2025-08~2026-06": m3, "候選±5日重疊": h3, "候選±5日重疊比": f(h3, m3)}


# ───────── 事件資料（盤點＋逐訊號旗標）─────────
def event_inventory(sig):
    """sig：DataFrame（sid、d）。回 (盤點表, 覆蓋 {類: (命中, 分母)}, 旗標 {類: bool 陣列})；訊號窗 ＝ 資料日前 28 日～資料日。"""
    M = os.path.join(DATA, "meta")
    out = []
    E = pd.read_csv(os.path.join(M, "seo_cb_events", "seo_cb_events.csv"), dtype=str)
    E["date"] = pd.to_datetime(E["date"]); E["y"] = E["date"].dt.year
    for k, msk in {"現金增資決議（一般，非私募非承銷）": (E["class"] == "seo") & (E["private"] != "1") & (E["ipo"] != "1"),
                   "私募決議（現增＋可轉債）": E["private"] == "1",
                   "可轉債發行決議（非私募）": (E["class"] == "cb") & (E["private"] != "1")}.items():
        x = E[msk]
        out.append({"類": k, "來源": "data/meta/seo_cb_events/seo_cb_events.csv（news 主旨分類；決議日）",
                    "起": str(x["date"].min().date()), "迄": str(x["date"].max().date()), "筆數": len(x),
                    "2018-11起筆數": int((x["date"] >= "2018-11-01").sum())})
    P = pd.read_csv(os.path.join(M, "placement_detail", "placement_detail.csv"), dtype=str)
    P["decide_date"] = pd.to_datetime(P["decide_date"], errors="coerce")
    out.append({"類": "私募明細（僅 E3 名單公司）", "來源": "data/meta/placement_detail/placement_detail.csv",
                "起": str(P["decide_date"].min().date()), "迄": str(P["decide_date"].max().date()), "筆數": len(P),
                "2018-11起筆數": int((P["decide_date"] >= "2018-11-01").sum())})
    nf = sorted(glob.glob(os.path.join(DATA, "mops", "news", "*.csv")))
    N = pd.concat([pd.read_csv(f, dtype=str, usecols=["date", "stock_id", "subject"]) for f in nf])
    sub = N["subject"].fillna("").str.replace(r"\s", "", regex=True)
    conv = sub.str.contains("轉換") & sub.str.contains("公司債") & sub.str.contains("普通股|發行新股|換發|轉換股數|股本")
    x = N[conv]; xd = pd.to_datetime(x["date"])
    out.append({"類": "可轉債轉換（無專表；news 主旨關鍵字代理）", "來源": "data/mops/news/<年>.csv 主旨含 轉換＋公司債＋(普通股|發行新股|換發|轉換股數|股本)",
                "起": str(xd.min().date()), "迄": str(xd.max().date()), "筆數": len(x), "2018-11起筆數": int((xd >= "2018-11-01").sum())})
    out.append({"類": "ETF 申贖成分調整", "來源": "資料庫沒有 ETF 申購買回清單（PCF）；只有 data/meta/tw50（0050 成分異動）、data/universe/etfsplit（ETF 分割）",
                "起": "", "迄": "", "筆數": 0, "2018-11起筆數": 0})
    T50 = pd.read_csv(os.path.join(M, "tw50", "tw50_changes.csv"), dtype=str)
    dc = next((c for c in T50.columns if "date" in c.lower() or "日" in c), T50.columns[0])
    td = pd.to_datetime(T50[dc], errors="coerce")
    out.append({"類": "（旁證）0050 成分異動", "來源": "data/meta/tw50/tw50_changes.csv", "起": str(td.min().date()) if td.notna().any() else "",
                "迄": str(td.max().date()) if td.notna().any() else "", "筆數": len(T50), "2018-11起筆數": int((td >= "2018-11-01").sum())})
    ev = {}
    for k, msk in {"現增": (E["class"] == "seo") & (E["private"] != "1") & (E["ipo"] != "1"), "私募": E["private"] == "1",
                   "可轉債發行": (E["class"] == "cb") & (E["private"] != "1")}.items():
        ev[k] = E[msk].groupby("stock_id")["date"].apply(lambda s: np.array(sorted(s), dtype="datetime64[ns]")).to_dict()
    ev["轉換公告"] = x.assign(d=xd).groupby("stock_id")["d"].apply(lambda s: np.array(sorted(s), dtype="datetime64[ns]")).to_dict()
    cover = {}; flags = {}
    for k, m in ev.items():
        f = np.zeros(len(sig), bool)
        for i, (s, d) in enumerate(zip(sig["sid"], sig["d"])):
            a = m.get(s)
            if a is None:
                continue
            lo = np.datetime64(d - pd.Timedelta(days=28)); hi = np.datetime64(d)
            j = np.searchsorted(a, lo)
            if j < len(a) and a[j] <= hi:
                f[i] = True
        flags[k] = f; cover[k] = (int(f.sum()), len(sig))
    return pd.DataFrame(out), cover, flags


def pct(x):
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{100 * x:.1f}%"


def write_md(F, agg, extra, cover, inv, dc, cinfo, yl_end, AL):
    g = lambda seg, ver: F[(F["段"] == seg) & (F["版"] == ver)].iloc[0]
    L = ["# 集保大戶比例 4 週升幅前 5%・組合層 seq1（裁定 seq507、seq508）頻率表（對齊情報 #76 讀法後重產）", "",
         f"回測線計算子代理｜資料 tw-stock-data `{SHA[:10]}`（＝ 情報 #76 同 sha）｜程式 `backtest/researchBigHolderRise.py`｜⛔ 不附任何報酬", ""]
    mx = max(F["持倉重疊比"].max(), F["新買±5日重疊比"].max(), F["候選±5日重疊比"].fillna(0).max())
    L += ["## 〇、與營量 v1 重疊（裁定附註：≥ 50% 先回信）", "",
          f"**最大重疊 {pct(mx)} ＜ 50% ⇒ 不觸發**。" if mx < 0.5 else f"⚠⚠ **重疊 {pct(mx)} ≥ 50% ⇒ 先回信**", "",
          "| 段 | 版 | 分母（進場日 ≤ " + str(yl_end.date()) + "） | ① 營量 v1 持倉中 | ② 營量 v1 前後 5 日新買 | ③ 營量 v1 候選前後 5 日（只 2025-08～2026-06） |", "|---|---|---:|---:|---:|---:|"]
    for seg in SEGS:
        for ver in ("全收版", "10檔版"):
            r = g(seg, ver)
            L.append(f"| {seg} | {ver} | {r['n']} | {r['持倉重疊']}（{pct(r['持倉重疊比'])}） | {r['新買±5日重疊']}（{pct(r['新買±5日重疊比'])}） | "
                     f"{r['候選±5日重疊']}／{r['候選n_2025-08~2026-06']}（{pct(r['候選±5日重疊比'])}） |")
        o = extra[seg]["全部訊號"]
        L.append(f"| {seg} | 全部訊號（不經組合） | {o['n']} | {o['持倉重疊']}（{pct(o['持倉重疊比'])}） | {o['新買±5日重疊']}（{pct(o['新買±5日重疊比'])}） | "
                 f"{o['候選±5日重疊']}／{o['候選n_2025-08~2026-06']}（{pct(o['候選±5日重疊比'])}） |")
    L += ["", "營量 v1 名單出處：① ② `backtest/resultsYFallin/trades_W.csv.gz` 世界「主」帳 YL（＋daily_W 日期，2015-01-05～2026-09-24）；"
          f"③ `backtest/resultsYLlist/營量v1名單＋營量v1未入選候選_20260928.csv`（{cinfo[2]} 列，{cinfo[0].date()}～{cinfo[1].date()}）。只讀 日期／代號 欄。", ""]
    L += ["## 一、逐筆對照情報 #76 B60 事件清單（裁定 seq508：≥ 98% 才正式跑）", "",
          f"- 本線 {AL['本線筆數']} 筆｜情報 {AL['情報筆數']} 筆｜交集 {AL['交集']}｜聯集 {AL['聯集']}",
          f"- **一致率（交集 ÷ 聯集）{AL['一致率_交集除聯集'] * 100:.2f}%**｜情報被本線覆蓋 {AL['情報被本線覆蓋'] * 100:.2f}%｜本線被情報覆蓋 {AL['本線被情報覆蓋'] * 100:.2f}%",
          f"- 交集升幅最大差 {AL['交集升幅最大差_pp']:.6f} 個百分點（情報清單四位小數）",
          "- 差異類型：" + ("無" if not AL["差異類型"] else "；".join(f"{k[0]}・{k[1]} {v}" for k, v in AL["差異類型"].items())),
          "- 逐筆見 `align76.md`、`align76_diff.csv`。", f"- 與營量 v1 不等價（上表 ≤ {pct(mx)}）。", ""]
    L += ["## 二、訊號頻率（依進場日分段）", "", "| 項 | 探索 | 確認 |", "|---|---:|---:|"]
    a, b = g("探索", "全收版"), g("確認", "全收版")
    for k in ["段起", "段迄", "段長_年", "集保週數(段內)", "缺週(間隔>10日推估)", "可算B週數", "Δ4母體<50週", "母體_平均", "母體_中位",
              "週訊號_平均", "週訊號_中位", "週訊號_最少", "週訊號_最多", "0訊號週", "訊號總數"]:
        L.append(f"| {k} | {a[k]} | {b[k]} |")
    L += ["", f"集保缺口：探索 {a['缺口']}｜確認 {b['缺口']}", ""]
    L += ["## 三、組合（只用日期與份數）", "", "| 項 | 探索 全收 | 探索 10檔 | 確認 全收 | 確認 10檔 |", "|---|---:|---:|---:|---:|"]
    rr = [g("探索", "全收版"), g("探索", "10檔版"), g("確認", "全收版"), g("確認", "10檔版")]
    for k in ["買進筆數", "買進批數", "有進場不同月數", "四十九", "平均持股部位", "平均不同檔數", "現金比例", "現金比例_2019_07起",
              "年換手_筆每年", "年換手_份額每年", "輪到份未出場_略過週", "輪到份未出場_略過訊號", "死板輪_略過週",
              "空位但當週0訊號週", "滿了沒買訊號", "已持有同檔略過"]:
        L.append(f"| {k} | " + " | ".join(str(r[k]) for r in rr) + " |")
    L += ["", "- 〈四十九〉：任一段有進場的不同月數 < 24 ⇒ 該格還沒測；10 檔版兩段固定「還沒測（依構造）」（裁定 seq508）。",
          "- 10 檔版每次都是 10 格同時空出、同一週補滿 ⇒ 進場集中成批（約每 60 個交易日一批），不同月數因此少。",
          "- 全收版平均持股部位含同一檔在不同份重複持有；不同檔數另列。",
          "- 現金比例_2019_07起：探索段扣掉 2019-01～06 集保缺資料那半年（那半年沒訊號、全現金）。",
          "- #76 讀法下 60 日出場超過資料尾的週不算 ⇒ 確認段最後約 12 週沒有訊號（資料尾前 60 個交易日）。", ""]
    L += ["## 四、事件拆解資料可得性", "", "| 類 | 來源 | 起 | 迄 | 筆數 | 2018-11 起 |", "|---|---|---|---|---:|---:|"]
    for r in inv.itertuples():
        L.append(f"| {r.類} | {r.來源} | {r.起} | {r.迄} | {r.筆數} | {r._6} |")
    L += ["", "訊號窗（資料日前 28 日～資料日）內同檔有公告的訊號比例（決議／公告日口徑）："]
    for k, (h, n) in cover.items():
        L.append(f"- {k}：{h}／{n}（{pct(h / n)}）")
    L += ["", "- ETF 申贖：資料庫沒有 ETF 申購買回清單（PCF）⇒ 這一類拆不到；0050 成分異動只是旁證。",
          "- 可轉債「轉換」沒有專表，只能用重訊主旨關鍵字代理；實際轉換多半不發重訊（月報股本變動），覆蓋偏低。", ""]
    L += ["## 五、資料檢查", "",
          f"- 集保（#76 同讀法：tdcc_hist＋tdcc csv、重疊日以 csv 為準、排除 {EXCL_DATE}）2018-11 起每資料日檔數：最少 {int(dc[dc['資料日'] >= pd.Timestamp('2018-11-01').date()]['四碼普通股檔數'].min())}、"
          f"最多 {int(dc[dc['資料日'] >= pd.Timestamp('2018-11-01').date()]['四碼普通股檔數'].max())}（逐日見 data_check.csv）。",
          "- 缺週：2018-12-28 → 2019-06-28 整段約 25 週沒有資料（探索段實際只有 2018-11～12 與 2019-07 起）；其餘缺口多為春節或單週缺。",
          f"- 交易日 ＝ 當天 ≥ {CAL_MIN} 檔有效成交（valid_bar＝1）；成交額門檻 ＝ 前 20 個交易日 amount 平均（停牌日記 0）≥ 5,000 萬。", ""]
    L += ["## 六、讀法（裁定 seq508：以情報 #76 讀法為準；與上一版頻率表的差別）", "",
          "1. 週 ＝ (資料日 − 2017-01-02)//7、同週取較晚；Δ4 只認剛好 4 週前那一週（上一版：與 d−28 相差 ≤ 3 日 ⇒ 拿掉）。",
          "2. 母體加：資料日前 6 天內有有效成交、前 20 日報酬／進場開盤／出場收盤都要有值；Δ4 母體 < 50 檔的週不算。",
          "3. 進場日當天沒開盤 ⇒ 不在母體（上一版：過門檻後才剔除）；60 日出場超過資料尾的週不算。",
          "4. 交易日 ＝ ≥ 300 檔有效成交；門檻 pandas 線性內插（與 numpy linear 同值）；四碼代號 ^[1-9]\\d{3}$。",
          "5. 全收版：每週動用一份已出場的空份；12 份都未出場 ⇒ 本週不買（件數見表）。10 檔版：已持有的同一檔不重複買。",
          "6. 兩段各自從空倉開始。", "", "描述，不是買賣建議", ""]
    with open(os.path.join(OUT, "頻率表.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    E = ["# 對情報 #76 的條件等價檢查（seq377／seq508）", "",
         f"- 逐筆一致率（交集 ÷ 聯集）{AL['一致率_交集除聯集'] * 100:.2f}%（見 align76.md）",
         f"- 彙總：可算週且 60 日到期 {agg['可算B週數_且60日到期']} 週（#76：B60 360 週）；母體平均 {agg['母體平均(全段)']}（#76：約 570）；週訊號平均 {agg['週訊號平均(全段)']}（#76：約 29）",
         f"- 與營量 v1：重疊最多 {pct(mx)}（見頻率表〇），遠低於 90% ⇒ 不是營量 v1 的名單。", ""]
    with open(os.path.join(OUT, "equiv76.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(E))


def write_align(AL, DF, path):
    L = ["# 逐筆對照：本線 vs 情報 #76 B60 事件清單", "", f"情報清單：`{path}`（{AL['情報筆數']} 列）｜鍵：資料日＋代號", "",
         "| 項 | 值 |", "|---|---:|"]
    for k in ["本線筆數", "情報筆數", "交集", "聯集"]:
        L.append(f"| {k} | {AL[k]} |")
    for k in ["一致率_交集除聯集", "情報被本線覆蓋", "本線被情報覆蓋"]:
        L.append(f"| {k} | {AL[k] * 100:.3f}% |")
    L.append(f"| 交集升幅最大差（百分點） | {AL['交集升幅最大差_pp']:.6f} |")
    L += ["", f"**{'≥' if AL['一致率_交集除聯集'] >= ALIGN_MIN else '<'} 98%** ⇒ {'可正式跑' if AL['一致率_交集除聯集'] >= ALIGN_MIN else '⛔ 不正式跑，先回信'}", "",
          "## 差異類型", "", "| 邊 | 類型 | 筆數 |", "|---|---|---:|"]
    for k, v in AL["差異類型"].items():
        L.append(f"| {k[0]} | {k[1]} | {v} |")
    if len(DF):
        L += ["", "## 例子（每類最多 5 筆）", ""]
        for (sd, ty), g in DF.groupby(["邊", "類型"]):
            for r in g.head(5).itertuples():
                L.append(f"- {sd}｜{ty}｜{r.資料日} {r.代號} {r.說明}")
    with open(os.path.join(OUT, "align76.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    DF.to_csv(os.path.join(OUT, "align76_diff.csv"), index=False, encoding="utf-8-sig")


# ───────── 頻率表 ─────────
def seg_bounds(cal, a, b):
    lo = int(cal.searchsorted(pd.Timestamp(a))); hi = min(int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1, len(cal) - 1)
    return lo, hi


def freq(Bx, AL):
    cal = Bx["cal"]; weeks = Bx["weeks"]; SIG = Bx["SIG"]; last_pos = len(cal) - 1
    Bdt = Bx["Bdt"]
    cnt = Bdt.notna().sum(axis=1)
    dc = pd.DataFrame({"資料日": [d.date() for d in cnt.index], "四碼普通股檔數": cnt.values})
    dc["距上一資料日_日"] = pd.Series(cnt.index).diff().dt.days.values
    dc.to_csv(os.path.join(OUT, "data_check.csv"), index=False, encoding="utf-8-sig")
    SIG.drop(columns=["e", "x"]).to_csv(os.path.join(OUT, "signals.csv"), index=False, encoding="utf-8-sig")
    WK = pd.DataFrame([{"資料日": w["d"].date(), "週": w["wk"], "前4週資料日": (w["lag"].date() if pd.notna(w["lag"]) else ""),
                        "進場日": (cal[w["e"]].date() if w["e"] is not None else ""), "出場日": (cal[w["x"]].date() if w["x"] is not None else ""),
                        "狀態": w["status"], "母體(含Δ4缺)": w["uni_all"], "母體(Δ4有值)": w["uni"],
                        "第95百分位_pp": round(w["q95"] * 100, 6) if np.isfinite(w["q95"]) else "", "訊號": w["nsig"]} for w in weeks])
    WK.to_csv(os.path.join(OUT, "weekly.csv"), index=False, encoding="utf-8-sig")
    iv, ylbuys, cset, yl_end, cinfo = load_yl()
    log(f"[營量 v1] resultsYFallin 帳 YL 持倉 {sum(len(v) for v in iv.values())} 筆、資料尾 {yl_end.date()}｜候選檔 {cinfo[2]} 列 {cinfo[0].date()}～{cinfo[1].date()}")
    rows = []; extra = {}
    for seg, (a, b) in SEGS.items():
        lo, hi = seg_bounds(cal, a, b)
        Wseg = [w for w in weeks if w["status"] == "ok" and lo <= w["e"] <= hi]
        Wall = [w for w in weeks if w["e"] is not None and lo <= w["e"] <= hi]
        ns = np.array([w["nsig"] for w in Wseg]); nu = np.array([w["uni"] for w in Wseg])
        yrs = (cal[hi] - cal[lo]).days / 365.25
        d_in = [w["d"] for w in weeks if pd.Timestamp(a) <= w["d"] <= pd.Timestamp(b)]
        gaps = [(d_in[i - 1].date(), d_in[i].date(), (d_in[i] - d_in[i - 1]).days) for i in range(1, len(d_in)) if (d_in[i] - d_in[i - 1]).days > 10]
        miss_weeks = sum(int(round(g_[2] / 7)) - 1 for g_ in gaps)
        base = {"段": seg, "段起": cal[lo].date(), "段迄": cal[hi].date(), "段長_年": round(yrs, 3),
                "集保週數(段內)": len(d_in), "缺週(間隔>10日推估)": miss_weeks, "缺口": "; ".join(f"{g_[0]}→{g_[1]}({g_[2]}日)" for g_ in gaps),
                "可算B週數": len(Wseg), "Δ4母體<50週": sum(w["status"] == "Δ4母體<50" for w in Wall),
                "母體_平均": round(nu.mean(), 1) if len(nu) else np.nan, "母體_中位": float(np.median(nu)) if len(nu) else np.nan,
                "週訊號_平均": round(ns.mean(), 2) if len(ns) else np.nan, "週訊號_中位": float(np.median(ns)) if len(ns) else np.nan,
                "週訊號_最少": int(ns.min()) if len(ns) else np.nan, "週訊號_最多": int(ns.max()) if len(ns) else np.nan,
                "0訊號週": int((ns == 0).sum()), "訊號總數": int(ns.sum())}
        coh, posF, conf = sim_full(Wseg, cal, last_pos, lo, hi)
        cntF, distF, cashF = daily_occupancy(posF, lo, hi, NFULL, "full", coh)
        mF = sorted({cal[p["e"]].strftime("%Y-%m") for p in posF})
        lo2 = max(lo, int(cal.searchsorted(pd.Timestamp("2019-07-01"))))
        rF = dict(base, 版="全收版", 買進筆數=len(posF), 買進批數=sum(1 for c in coh if c.get("n", 0) > 0 and "x" in c),
                  輪到份未出場_略過週=len(conf), 輪到份未出場_略過訊號=sum(c["n"] for c in conf), 死板輪_略過週=rigid_conflict(Wseg),
                  現金比例_2019_07起=round(cashF[lo2 - lo:].mean(), 4),
                  有進場不同月數=len(mF), 四十九=("還沒測(<24)" if len(mF) < 24 else "可判(≥24)"),
                  平均持股部位=round(cntF.mean(), 2), 平均不同檔數=round(distF.mean(), 2), 現金比例=round(cashF.mean(), 4),
                  年換手_筆每年=round(len(posF) / yrs, 1), 年換手_份額每年=round(sum(p["w"] for p in posF) / yrs, 3),
                  空位但當週0訊號週="", 滿了沒買訊號="", 已持有同檔略過="")
        rF.update(overlap([(p["sid"], p["e"]) for p in posF], cal, iv, ylbuys, cset, yl_end))
        rows.append(rF)
        posT, st = sim_ten(Wseg)
        cntT, distT, cashT = daily_occupancy(posT, lo, hi, NTEN, "ten")
        mT = sorted({cal[p["e"]].strftime("%Y-%m") for p in posT})
        rT = dict(base, 版="10檔版", 買進筆數=len(posT), 買進批數=len({p["e"] for p in posT}),
                  輪到份未出場_略過週="", 輪到份未出場_略過訊號="", 死板輪_略過週="",
                  現金比例_2019_07起=round(cashT[lo2 - lo:].mean(), 4),
                  有進場不同月數=len(mT), 四十九=("還沒測(<24)" if len(mT) < 24 else "可判(≥24)"),
                  平均持股部位=round(cntT.mean(), 2), 平均不同檔數=round(distT.mean(), 2), 現金比例=round(cashT.mean(), 4),
                  年換手_筆每年=round(len(posT) / yrs, 1), 年換手_份額每年=round(sum(p["w"] for p in posT) / yrs, 3),
                  空位但當週0訊號週=st["free_no_sig"], 滿了沒買訊號=st["full_skip"], 已持有同檔略過=st["dup_skip"])
        rT.update(overlap([(p["sid"], p["e"]) for p in posT], cal, iv, ylbuys, cset, yl_end))
        rows.append(rT)
        sg = SIG[(SIG["e"] >= lo) & (SIG["e"] <= hi)]
        extra[seg] = {"全部訊號": overlap(list(zip(sg["sid"], sg["e"])), cal, iv, ylbuys, cset, yl_end),
                      "全收版月": mF, "10檔版月": mT, "10檔版空位週": st["free_weeks"], "10檔版週": st["weeks"]}
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    inv, cover, _ = event_inventory(SIG.assign(d=pd.to_datetime(SIG["資料日"])))
    inv.to_csv(os.path.join(OUT, "event_inventory.csv"), index=False, encoding="utf-8-sig")
    okw = [w for w in weeks if w["status"] == "ok"]
    agg = {"可算B週數_且60日到期": len(okw), "其中有訊號週": sum(1 for w in okw if w["nsig"] > 0),
           "母體平均(全段)": round(np.mean([w["uni"] for w in okw]), 1), "週訊號平均(全段)": round(np.mean([w["nsig"] for w in okw]), 2),
           "B60訊號筆數(到期)": int(sum(w["nsig"] for w in okw))}
    J = {"sha": SHA, "agg76": agg, "align76": {k: (v if not isinstance(v, dict) else {"|".join(kk): vv for kk, vv in v.items()}) for k, v in AL.items()},
         "extra": extra, "cover": cover, "ylcand": [str(cinfo[0].date()), str(cinfo[1].date()), cinfo[2]]}
    with open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=str)
    log(json.dumps(agg, ensure_ascii=False))
    log(F.T.to_string())
    write_md(F, agg, extra, cover, inv, dc, cinfo, yl_end, AL)
    return F


# ───────── 正式跑 ─────────
def verdict_seg(c, m, bc, bm):
    """年化 > 大盤 且 比值 ≥ 大盤 ⇒ 合格；只贏年化 ⇒ 另列；其餘 ⇒ 不合格。"""
    from backtest.researchAscTri import ratio
    if not (np.isfinite(c) and np.isfinite(bc)):
        return "—"
    if c > bc and ratio(c, m) >= ratio(bc, bm):
        return "合格"
    if c > bc:
        return "另列"
    return "不合格"


def verdict_cell(segv, months, fixed=None):
    if fixed:
        return fixed
    if any(mn < 24 for mn in months):
        return "還沒測"
    if all(v == "合格" for v in segv):
        return "合格（暫定）"
    if all(v in ("合格", "另列") for v in segv):
        return "另列"
    return "不合格"


def real_inputs(Bx, Wseg_all, procs):
    """researchSlip 現實版的毛報酬（C4＋C2）、可成交旗標（C3）與成本（C1）。"""
    from multiprocessing import Pool
    from backtest import researchSlip as SL
    from backtest import tradability as TR
    cal = Bx["cal"]; n = len(cal); mk = Bx["mk"]
    sids = sorted({s for w in Wseg_all for s in w["sids"]})
    D.DATA = DATA
    SL._G.update(cal=cal, NP=n)
    with Pool(procs, initializer=SL._G.update, initargs=({"cal": cal, "NP": n},)) as pool:
        X = dict(pool.map(SL._load, [(s, mk.get(s, "twse")) for s in sids], chunksize=8))
    bad = [s for s, v in X.items() if v is None]
    if bad:
        raise SystemExit(f"⛔ 真實成本版：{len(bad)} 檔沒有每檔資料（例 {bad[:5]}）⇒ 停")
    trad_full = {s: {"trd": v["trd"][:n]} for s, v in X.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status(trad_full, cal, official=off)
    SL._G.update(dl=dl, SF=None)
    O = Bx["AO"]; Cf = Bx["ACf"]
    opens = {s: O[s].to_numpy(float) for s in sids}
    g = {}; op = None; cost = None; trd = None
    SL.CELLS[99] = {"名": "大戶比例", "rule": "H60", "N": NTEN, "seed0": 0, "A": 50_000}
    for kind in ("ten", "full"):
        for w in Wseg_all:
            SL.CELLS[99]["N"] = NTEN if kind == "ten" else NFULL * len(w["sids"])
            e = w["e"]; xx = e + HOLD - 1
            base_g = [float(Cf[s].iloc[xx] / O[s].iloc[e] - 1.0) for s in w["sids"]]
            sg = pd.DataFrame({"sid": w["sids"], "entry_pos": e, "xpos_H60": xx, "g_H60": base_g})
            sg2, op_, cost_, kw = SL.arm_inputs(99, REAL_SPEC, sg, X, None, opens)
            for col, gg in zip(w["cols"], sg2["g_H60"].to_numpy(float)):
                g[(kind, e, col)] = float(gg)
            if op is None:
                op, cost = op_, cost_
            trd = trd or {}
            trd.update(kw["tradable"])
    del SL.CELLS[99]
    reals = {}
    for kind in ("ten", "full"):
        reals[kind] = {"g": {(e, col): v for (k, e, col), v in g.items() if k == kind}, "op": op, "trd": trd, "dl": dl, "cost": cost}
    return reals, {"缺每檔資料": bad, "成本_來回": cost, "檔數": len(sids)}


def formal(a, Bx, AL):
    if not formal_allowed(a):
        raise SystemExit("⛔ 沒帶 --formal --ruling seq508 ⇒ 不出報酬")
    if not (AL["一致率_交集除聯集"] >= ALIGN_MIN):
        raise SystemExit(f"⛔ 逐筆一致率 {AL['一致率_交集除聯集']:.4f} < 98% ⇒ 不正式跑（裁定 seq508）")
    from backtest import benchmark_rejudge as BR
    from backtest.researchAscTri import ratio
    from backtest.researchGroupRevUp import TRI_SRC
    os.makedirs(OUTF, exist_ok=True)
    LOGS.clear()
    t0 = time.time()
    cal = Bx["cal"]; T = len(cal)
    cols = {s: i for i, s in enumerate(Bx["ACf"].columns)}
    C = Bx["ACf"].to_numpy(float); O = Bx["AO"].to_numpy(float)
    tri_s = BR.read_series(TRI_SRC)
    tri = tri_s.reindex(cal).ffill().to_numpy(float)
    b50 = BR.bench0050(DATA).reindex(cal).ffill().to_numpy(float)
    log(f"[正式] 閘 --formal --ruling {a.ruling}｜一致率 {AL['一致率_交集除聯集'] * 100:.2f}%｜大盤 {TRI_SRC}｜日曆 {cal[0].date()}～{cal[-1].date()}")
    SIG = Bx["SIG"]
    inv, cover, flags = event_inventory(SIG.assign(d=pd.to_datetime(SIG["資料日"])))
    evf = flags["現增"] | flags["私募"] | flags["轉換公告"]
    ev_keys = set(zip(SIG["e"][evf], SIG["sid"][evf]))
    W_all = []
    for w in Bx["weeks"]:
        if w["status"] != "ok":
            continue
        W_all.append({"e": w["e"], "d": w["d"], "sids": list(w["buys"]), "cols": [cols[s] for s in w["buys"]], "d4": list(w["d4"])})
    W_ev = []
    for w in W_all:
        keep = [i for i, s in enumerate(w["sids"]) if (w["e"], s) not in ev_keys]
        if keep:
            W_ev.append({"e": w["e"], "d": w["d"], "sids": [w["sids"][i] for i in keep], "cols": [w["cols"][i] for i in keep], "d4": [w["d4"][i] for i in keep]})
    reals, rinfo = real_inputs(Bx, W_all, a.procs)
    log(f"[真實成本] researchSlip 現實版：每檔資料 {rinfo['檔數']}（缺 {len(rinfo['缺每檔資料'])}）｜成本來回 {rinfo['成本_來回']:.5f}")
    segp = {sg: seg_bounds(cal, x_, y_) for sg, (x_, y_) in SEGS.items()}
    cells = []; curves = {"date": [str(d.date()) for d in cal], "大盤報酬指數": tri / tri[0], "0050": b50 / b50[np.isfinite(b50)][0]}
    trades_out = []; rnd = []; res = {}
    kinds = {"全收版": "full", "10檔版": "ten"}
    for ver, kind in kinds.items():
        for sg, (x, y) in segp.items():
            Wseg = [w for w in W_all if x <= w["e"] <= y]
            bt = BR.bstat(cal, tri, x, y); b5 = BR.bstat(cal, b50, x, y)
            row = {"版": ver, "段": sg, "起": str(cal[x].date()), "迄": str(cal[y].date()),
                   "大盤年化": bt["cagr"], "大盤回落": bt["mdd"], "大盤比值": bt["ratio"],
                   "0050年化": b5["cagr"] if b5 else np.nan, "0050回落": b5["mdd"] if b5 else np.nan, "0050比值": b5["ratio"] if b5 else np.nan}
            # 主口徑
            r0 = sim_book(kind, Wseg, x, y, C, O)
            e0 = full_eq(r0, x, T); c0, m0 = BR.estat(e0, x, y)
            mset = sorted({cal[e_].strftime("%Y-%m") for e_ in r0["entries"]})
            row.update(年化=c0, 回落=m0, 比值=ratio(c0, m0), 有進場不同月數=len(mset), 買進=r0["st"]["買進"], 略過週=r0["st"]["略過週"],
                       略過訊號=r0["st"]["略過訊號"], 已持有略過=r0["st"]["已持有略過"], 滿了沒買=r0["st"]["滿了沒買"], 資料尾仍持有=r0["open_end"])
            row["判_段"] = verdict_seg(c0, m0, bt["cagr"], bt["mdd"])
            curves[f"{ver}_{sg}"] = e0
            for t in r0["trades"]:
                trades_out.append({"版": ver, "段": sg, "進場日": str(cal[t["e"]].date()), "sid": t["sid"], "賣出日": str(cal[t["t_sell"]].date()),
                                   "金額_進場時_段初權益1": t["amt"], "毛報酬": t["gross"], "賣法": t["how"]})
            # 真實成本版
            rr = sim_book(kind, Wseg, x, y, C, O, real=reals[kind])
            er = full_eq(rr, x, T); cr, mr = BR.estat(er, x, y)
            row.update(真實_年化=cr, 真實_回落=mr, 真實_比值=ratio(cr, mr), 真實_判_段=verdict_seg(cr, mr, bt["cagr"], bt["mdd"]),
                       真實_一字漲停買不到=rr["st"]["一字漲停買不到"], 真實_跌停延後=rr["st"]["跌停延後"], 真實_下市結算=rr["st"]["下市結算"])
            curves[f"{ver}_{sg}_真實成本"] = er
            # 去掉報酬最大 1%、5% 的筆
            gs = sorted(r0["trades"], key=lambda t: -t["gross"])
            for p_ in (0.01, 0.05):
                k = max(1, int(round(len(gs) * p_)))
                drop = {(t["e"], t["col"]) for t in gs[:k]}
                rd = sim_book(kind, Wseg, x, y, C, O, drop=drop)
                cd, md = BR.estat(full_eq(rd, x, T), x, y)
                row[f"去前{int(p_ * 100)}%_筆數"] = k; row[f"去前{int(p_ * 100)}%_年化"] = cd; row[f"去前{int(p_ * 100)}%_回落"] = md
            # 事件拆解
            Wse = [w for w in W_ev if x <= w["e"] <= y]
            re_ = sim_book(kind, Wse, x, y, C, O)
            ce, me = BR.estat(full_eq(re_, x, T), x, y)
            nsig = sum(len(w["sids"]) for w in Wseg); nev = nsig - sum(len(w["sids"]) for w in Wse)
            row.update(事件剔除_訊號數=nev, 事件剔除_比例=nev / nsig if nsig else np.nan, 事件剔除後_年化=ce, 事件剔除後_回落=me,
                       事件剔除後_比值=ratio(ce, me))
            # 隨機挑 10 檔 200 次
            if kind == "ten":
                rc = []
                for r in range(NRAND):
                    rg = np.random.default_rng(SEED_RAND + r)
                    rs = sim_book("ten", Wseg, x, y, C, O, pick="rand", rng=rg)
                    c_, m_ = BR.estat(full_eq(rs, x, T), x, y)
                    rc.append((c_, m_)); rnd.append({"段": sg, "r": r, "年化": c_, "回落": m_, "比值": ratio(c_, m_)})
                rcv = np.array([z[0] for z in rc]); rrv = np.array([ratio(*z) for z in rc])
                row.update(隨機_年化_p10=float(np.percentile(rcv, 10)), 隨機_年化_中位=float(np.median(rcv)), 隨機_年化_p90=float(np.percentile(rcv, 90)),
                           隨機_年化百分位=float(100 * ((rcv < c0).mean() + 0.5 * (rcv == c0).mean())),
                           隨機_比值百分位=float(100 * ((rrv < ratio(c0, m0)).mean() + 0.5 * (rrv == ratio(c0, m0)).mean())))
            cells.append(row)
            log(f"[{ver}・{sg}] 年化 {c0:+.4f} 回落 {m0:+.4f}｜大盤 {bt['cagr']:+.4f}/{bt['mdd']:+.4f}｜{row['判_段']}｜真實 {cr:+.4f}/{mr:+.4f}｜略過週 {row['略過週']}")
    CE = pd.DataFrame(cells)
    for ver in kinds:
        sub = CE[CE["版"] == ver]
        fixed = "還沒測（依構造）" if ver == "10檔版" else None
        res[ver] = {"判": verdict_cell(sub["判_段"].tolist(), sub["有進場不同月數"].tolist(), fixed),
                    "真實成本_判": verdict_cell(sub["真實_判_段"].tolist(), sub["有進場不同月數"].tolist(), fixed)}
    CE.to_csv(os.path.join(OUTF, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.8g")
    pd.DataFrame(curves).to_csv(os.path.join(OUTF, "curves.csv"), index=False, encoding="utf-8-sig", float_format="%.8g")
    pd.DataFrame(rnd).to_csv(os.path.join(OUTF, "random200.csv"), index=False, encoding="utf-8-sig", float_format="%.8g")
    pd.DataFrame(trades_out).to_csv(os.path.join(OUTF, "trades.csv"), index=False, encoding="utf-8-sig", float_format="%.8g")
    J = {"sha": SHA, "ruling": a.ruling, "align76": AL["一致率_交集除聯集"], "判": res, "真實成本": rinfo | {"缺每檔資料": rinfo["缺每檔資料"][:50]},
         "事件拆解覆蓋": cover, "大盤": TRI_SRC, "cells": cells}
    with open(os.path.join(OUTF, "result.json"), "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    write_formal_md(CE, res, cover, rinfo, AL)
    log(f"[完成] 正式 {time.time() - t0:.0f}s")
    with open(os.path.join(OUTF, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOGS) + "\n")


def _p(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


def _f(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.2f}"


def result_sentences(CE, res):
    g = lambda ver, sg: CE[(CE["版"] == ver) & (CE["段"] == sg)].iloc[0]
    S = []
    for ver in ("全收版", "10檔版"):
        a, b = g(ver, "探索"), g(ver, "確認")
        segtxt = "；".join(f"{sg} 年化 {_p(r['年化'])}、回落 {_p(r['回落'])}、比值 {_f(r['比值'])}（大盤 {_p(r['大盤年化'])}／{_p(r['大盤回落'])}／{_f(r['大盤比值'])}；"
                          f"0050 {_p(r['0050年化'])}／{_p(r['0050回落'])}）⇒ 段判 {r['判_段']}" for sg, r in (("探索", a), ("確認", b)))
        S.append(f"- **{ver}：{res[ver]['判']}**。{segtxt}。真實成本版：探索 {_p(a['真實_年化'])}、確認 {_p(b['真實_年化'])} ⇒ {res[ver]['真實成本_判']}。")
        if ver == "全收版":
            S.append(f"  - 12 份都沒出場而略過的週：探索 {a['略過週']} 週（{a['略過訊號']} 筆訊號）、確認 {b['略過週']} 週（{b['略過訊號']} 筆訊號）；有進場不同月數 {a['有進場不同月數']}／{b['有進場不同月數']}。")
        else:
            S.append(f"  - 〈四十九〉：有進場不同月數 {a['有進場不同月數']}／{b['有進場不同月數']} < 24 ⇒ 兩段固定「還沒測（依構造）」（裁定 seq508），以上報酬只描述。")
            for sg, r in (("探索", a), ("確認", b)):
                p_ = r["隨機_年化百分位"]
                mid = 25 <= p_ <= 75
                S.append(f"  - 隨機挑 10 檔 200 次：{sg} 10 檔版落在第 {p_:.0f} 百分位（比值第 {r['隨機_比值百分位']:.0f}）"
                         + ("⇒ 落在中段，挑法沒有幫助。" if mid else "（不在中段）。"))
        S.append(f"  - 去掉報酬最大 1%／5% 的筆：探索 {_p(a['去前1%_年化'])}／{_p(a['去前5%_年化'])}、確認 {_p(b['去前1%_年化'])}／{_p(b['去前5%_年化'])}（原 {_p(a['年化'])}／{_p(b['年化'])}）。")
        S.append(f"  - 事件剔除（現增、私募、轉換公告）：探索剔 {a['事件剔除_訊號數']} 筆 ⇒ {_p(a['事件剔除後_年化'])}、確認剔 {b['事件剔除_訊號數']} 筆 ⇒ {_p(b['事件剔除後_年化'])}。")
    S += ["- 集保 2018-12-28～2019-06-28 缺約 25 週：探索段那半年沒有訊號、全現金，探索段實際從 2019-07 起為主。",
          "- 事件層平均靠少數大漲股，組合層要分散才吃得到。",
          "- 大戶比例變動含增資、轉換、借券等非買進。",
          "- 沒拆到的部分：ETF 申贖成分調整（資料庫沒有）、借券、可轉債轉換（重訊關鍵字代理、覆蓋偏低）；剔除只用決議／公告日落在訊號窗內的那幾類。"]
    v10, vF = res["10檔版"]["判"], res["全收版"]["判"]
    S.append("- 先驗（登錄 §五，寫下不改）：① 10 檔版不合格（約六成五）⇒ " +
             ("依構造還沒測，無從對照（不算命中也不算落空）" if v10.startswith("還沒測") else ("命中" if v10 == "不合格" else "沒命中")) +
             f"；② 全收版另列或不合格（約六成）⇒ 結果「{vF}」" + ("，命中。" if vF in ("另列", "不合格") else ("，還沒測、無從對照。" if vF.startswith("還沒測") else "，沒命中。")))
    return S


def write_formal_md(CE, res, cover, rinfo, AL):
    L = ["# 集保大戶比例 4 週升幅前 5%・組合層 seq1 正式結果（裁定 seq507、seq508）", "",
         f"回測線計算子代理｜資料 tw-stock-data `{SHA[:10]}`｜程式 `backtest/researchBigHolderRise.py --formal --ruling seq508`｜逐筆一致率 {AL['一致率_交集除聯集'] * 100:.2f}%", "",
         "## 〇、判語", ""]
    for ver, r in res.items():
        L.append(f"- **{ver}：{r['判']}**（真實成本版：{r['真實成本_判']}）")
    L += ["", "## 一、兩格兩段（成本來回 0.585%；對大盤報酬指數）", "",
          "| 版 | 段 | 起～迄 | 年化 | 回落 | 比值 | 大盤年化 | 大盤回落 | 大盤比值 | 0050 年化 | 0050 回落 | 段判 | 有進場月數 | 略過週 |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|"]
    for _, r in CE.iterrows():
        L.append(f"| {r['版']} | {r['段']} | {r['起']}～{r['迄']} | {_p(r['年化'])} | {_p(r['回落'])} | {_f(r['比值'])} | {_p(r['大盤年化'])} | {_p(r['大盤回落'])} | {_f(r['大盤比值'])} | "
                 f"{_p(r['0050年化'])} | {_p(r['0050回落'])} | {r['判_段']} | {r['有進場不同月數']} | {r['略過週'] if r['版'] == '全收版' else '—'} |")
    L += ["", "## 二、真實成本版（researchSlip 現實版：C1 每邊 +0.3%、C2 平方根衝擊 50 萬 ÷ 檔數、C3 一字漲跌停、C4 均價）", "",
          "| 版 | 段 | 年化 | 回落 | 比值 | 段判 | 一字漲停買不到 | 跌停延後 |", "|---|---|---:|---:|---:|---|---:|---:|"]
    for _, r in CE.iterrows():
        L.append(f"| {r['版']} | {r['段']} | {_p(r['真實_年化'])} | {_p(r['真實_回落'])} | {_f(r['真實_比值'])} | {r['真實_判_段']} | {r['真實_一字漲停買不到']} | {r['真實_跌停延後']} |")
    L += ["", "## 三、10 檔版 vs 隨機挑 10 檔 200 次（只描述）", "", "| 段 | 10 檔版年化 | 隨機 p10 | 隨機中位 | 隨機 p90 | 年化百分位 | 比值百分位 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in CE[CE["版"] == "10檔版"].iterrows():
        L.append(f"| {r['段']} | {_p(r['年化'])} | {_p(r['隨機_年化_p10'])} | {_p(r['隨機_年化_中位'])} | {_p(r['隨機_年化_p90'])} | 第 {r['隨機_年化百分位']:.0f} | 第 {r['隨機_比值百分位']:.0f} |")
    L += ["", "（★ 中段 ＝ 第 25～75 百分位 ⇒ 寫「挑法沒有幫助」）", "", "## 四、去掉報酬最大 1%、5% 的筆（那幾筆改持現金，其他筆不動）", "",
          "| 版 | 段 | 原年化 | 去前 1%（筆） | 去前 5%（筆） |", "|---|---|---:|---:|---:|"]
    for _, r in CE.iterrows():
        L.append(f"| {r['版']} | {r['段']} | {_p(r['年化'])} | {_p(r['去前1%_年化'])}（{r['去前1%_筆數']}） | {_p(r['去前5%_年化'])}（{r['去前5%_筆數']}） |")
    L += ["", "## 五、事件拆解（訊號窗＝資料日前 28 日～資料日 內有 現增／私募（seo_cb_events）／可轉債轉換（重訊主旨關鍵字代理）的訊號剔除）", "",
          "| 版 | 段 | 剔除訊號 | 原年化 | 剔除後年化 | 剔除後回落 | 剔除後比值 |", "|---|---|---:|---:|---:|---:|---:|"]
    for _, r in CE.iterrows():
        L.append(f"| {r['版']} | {r['段']} | {r['事件剔除_訊號數']}（{r['事件剔除_比例'] * 100:.1f}%） | {_p(r['年化'])} | {_p(r['事件剔除後_年化'])} | {_p(r['事件剔除後_回落'])} | {_f(r['事件剔除後_比值'])} |")
    L += ["", "覆蓋（全部訊號）：" + "；".join(f"{k} {h}／{n}" for k, (h, n) in cover.items()),
          "", "沒拆到的部分：ETF 申贖成分調整（資料庫沒有 PCF）、借券（沒有逐檔借券餘額變動對到集保週）、可轉債轉換（多半不發重訊，關鍵字代理覆蓋偏低）。", ""]
    L += ["## 六、結果句", ""] + result_sentences(CE, res) + ["", "描述，不是買賣建議", ""]
    with open(os.path.join(OUTF, "結果.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main(argv=None):
    a = parse_args(sys.argv[1:] if argv is None else argv)
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    D.DATA = DATA
    log(f"[資料] tw-stock-data {SHA[:10]}｜{'正式跑（閘 ' + a.ruling + '）' if formal_allowed(a) else '只頻率表＋逐筆對照（⛔ 不出報酬）'}")
    Bx = build76()
    AL, DF = align(Bx, a.b60)
    write_align(AL, DF, a.b60)
    log(f"[逐筆對照] 一致率 {AL['一致率_交集除聯集'] * 100:.3f}%｜情報覆蓋 {AL['情報被本線覆蓋'] * 100:.3f}%｜本線覆蓋 {AL['本線被情報覆蓋'] * 100:.3f}%｜{AL['差異類型']}")
    freq(Bx, AL)
    log(f"[完成] 頻率表 {time.time() - t0:.0f}s")
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOGS) + "\n")
    if formal_allowed(a):
        formal(a, Bx, AL)


if __name__ == "__main__":
    main()

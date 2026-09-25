# -*- coding: utf-8 -*-
"""PREREGM §六 第一欄【趨勢線頻率盤點】——只數事件的日期與個數、剔除計數。判準＝台股策略線 PREREGM seq1（sha 9316840579a8d33a）。

⛔⛔ 本支不算、不印、不存任何報酬：不讀 open(T+21)、不算 R_e／X／基準／勝率／任何 T+21 價格比。
   剔除只判「能不能成交／資料斷不斷」：T+1 開盤漲停（tradability.one，原始價）、T+1 停牌、硬斷點 ⇒ ⛔ 不看價差。

資料、母體、讀檔、硬斷點：與 PREREGH1／H2 同一份快照與同一套函式（import researchH2：main edc6f8002f、gate3、H2.brk）。
偵測器：backtest/trendline_m.py（fixture：backtest/selftest_trendline_m.py，⭐ 本支開跑前先全跑、任一條不過即中止）。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率之前寫在這裡；交件逐條列出；偵測器本身的讀法 M1～M8 見 trendline_m.py）：
 Q1 事件須 T ∈ [窗起點, 窗尾−21]（交易日曆；T+21 ≤ 窗尾）。T 是有效 K 棒；T+1、T+21 是交易日曆位置。
 Q2 處理順序（同 H2 R5）：同檔同畫法依時間走 ⇒ 若 T 落在「上一個被保留事件 t0」的 (t0, t0+20]（交易日曆）⇒ 合併掉；
    否則判剔除（硬斷點 → T+1 停牌 → T+1 開盤漲停，依此順序只記第一個原因；各旗標另外逐項計數）；被剔除者 ⛔ 不開合併窗。
    另報「純合併」（不看剔除、只照 20 日合併）的件數，讓兩種順序都查得到。
 Q3 T+1 停牌 ＝ T+1（交易日曆）無成交（tradability.one 的 trd 為假）或還原開盤缺值；T+1 開盤漲停 ＝ tradability.one 的 up_o。
 Q4 硬斷點（同 H2 R3）：① 價格：相鄰有效 K 棒 close 比 ≤ 0.55 或 ≥ 1.8 且 (前一根, 這一根] 內無 data/adj 事件，
    斷點日落在 [最早取點（丙：回歸窗起點）, T+21] 內；② 時間：該範圍內有連續 ≥ 5 個交易日無有效 K 棒（5 個缺日全在範圍內）。
 Q5 delist on：tradability.delist_status 判為 delisted_official／delisted_gap 的股票，【最後成交之後】的無成交日是下市、
    ⛔ 不算 ② 的「連續缺日」（照 delist on：以最後成交價了結）；ambig 與未下市照停牌算。
    ⇒ 另報：保留事件中「持有期 (T, T+21] 內下市」件數，以及「若照 H2 字面（下市後缺日也算硬斷點）會多剔除」的件數。
 Q6 每檔每年：分子＝該檔保留事件數；分母＝該檔在 [窗起點, 窗尾−21] 內、從首個到最後一個有效 K 棒所跨的交易日數
    ÷ 每年交易日數（＝該段交易日數 ÷ 該段曆年數）。分佈（平均／中位／p90）只取曝露 ≥ 1 年的股票（含零事件者）；
    另報合併母體比率（總事件 ÷ 總股票年，含曝露 < 1 年者）。上市／上櫃依快照 stocks.csv 的 market 欄（⚠ 會變的欄，取快照當下值）。
 Q7 20 日獨立區段：從判定窗起點以交易日曆每 20 日切一段（區段號＝(T − 窗起點)//20，上限 115）；報「有保留事件的區段數」
    與 min(保留事件數, 區段數)（純計數，⛔ 不算 X）。
 Q8 描述臂 R＝3、10 只影響 (甲)(乙)；(丙) 不用樞紐 ⇒ 只有一格。
"""
from __future__ import annotations
import os, sys, time, json
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                            # ⭐ 同一份快照、同一套讀檔／斷點（D.DATA 已被指到快照）
D, TR, UG = H2.D, H2.TR, H2.UG
from backtest import trendline_m as TM
from backtest import selftest_trendline_m as STM

OUT = "backtest/resultsM"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
H_OUT = 21            # T+21 ≤ 窗尾
MERGE = 20
BLOCK, BLOCK_CAP = 20, 115
CONFIGS = [("甲", 5), ("乙", 5), ("丙", 5), ("甲", 3), ("乙", 3), ("甲", 10), ("乙", 10)]
MAIN = [("甲", 5), ("乙", 5), ("丙", 5)]
_G = {}


def cfg_name(meth, R):
    return meth if (meth, R) in MAIN else "{}_R{}".format(meth, R)


def _init(cal, w0, w1, off):
    _G.update(cal=cal, w0=w0, w1=w1, off=off)


def _g5(valid, upto=None):
    """第 d 天是否為「連續缺 ≥ 5 日」的第 5 天以後；upto：該位置之後的缺日不算缺（下市後）。"""
    n = len(valid); run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        miss = (not valid[i]) and (upto is None or i <= upto)
        r_ = r_ + 1 if miss else 0
        run[i] = r_
    return run >= 5


def load_one(args):
    sid, market = args
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]; n = len(cal); wE = w1 - H_OUT
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    lo_, hi_ = max(int(bars[0]), w0), min(int(bars[-1]), wE)
    expo = max(0, hi_ - lo_ + 1)
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5_lit = _g5(valid)
    g5_dl = _g5(valid, upto=ds["last"]) if delisted else g5_lit
    S_dl = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5_dl).astype(np.int32)}
    S_lit = {"cs_pb": S_dl["cs_pb"], "cs_g5": np.cumsum(g5_lit).astype(np.int32)}
    nan_hi = int(np.sum(valid & ~np.isfinite(h))); nan_op = int(np.sum(valid & ~np.isfinite(o)))
    out = {"sid": sid, "market": market, "expo": expo, "nan_high": nan_hi, "nan_open": nan_op,
           "status": ds["status"] if ds else None, "cfg": {}}
    for meth, R in CONFIGS:
        r = TM.detect_calendar(o, h, c, meth, R)
        evs = [e for e in r["events"] if w0 <= e["T"] <= wE]
        rows = []; t_keep = -10 ** 9; t_pure = -10 ** 9; n_pure = 0
        for e in evs:
            T = e["T"]
            if not (t_pure < T <= t_pure + MERGE):
                n_pure += 1; t_pure = T
            f_brk = H2.brk(S_dl, e["first"], T + H_OUT)
            f_brk_lit = H2.brk(S_lit, e["first"], T + H_OUT)
            f_halt = (not bool(tb["trd"][T + 1])) or (not np.isfinite(o[T + 1]))
            f_lim = bool(tb["up_o"][T + 1])
            f_dl_in = bool(delisted and ds["last"] < T + H_OUT)
            f_dl_t1 = bool(delisted and ds["last"] <= T)
            if t_keep < T <= t_keep + MERGE:
                stt = "合併掉"
            elif f_brk:
                stt = "剔除_硬斷點"
            elif f_halt:
                stt = "剔除_T+1停牌"
            elif f_lim:
                stt = "剔除_T+1開盤漲停"
            else:
                stt = "保留"; t_keep = T
            rows.append({"T": T, "first": e["first"], "anchors": e.get("anchors"), "conf": e.get("conf"),
                         "狀態": stt, "f_brk": f_brk, "f_brk_lit": f_brk_lit, "f_halt": f_halt, "f_lim": f_lim,
                         "f_dl_in": f_dl_in, "f_dl_t1": f_dl_t1})
        out["cfg"][(meth, R)] = {"rows": rows, "n_pure": n_pure, "stats": r["stats"],
                                 "n_raw_all": len(r["events"])}
    return out


def qd(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "平均": round(float(x.mean()), 4), "中位": round(float(np.median(x)), 4),
            "p90": round(float(np.percentile(x, 90)), 4), "零事件佔比": round(float((x == 0).mean()), 4)}


def summarize(ST, meth, R, cal, w0, DPY):
    acc = {"原始事件_窗內": 0, "純合併後_不看剔除": 0, "合併掉": 0, "剔除_硬斷點": 0, "剔除_T+1停牌": 0,
           "剔除_T+1開盤漲停": 0, "保留": 0}
    flag = {"硬斷點": 0, "T+1停牌": 0, "T+1停牌_其中已下市": 0, "T+1開盤漲停": 0}
    kept_dl = kept_lit_extra = 0
    per_stock = []; kept = []; rows_csv = []
    lines = {"樞紐": 0, "線成立": 0, "突破結束": 0, "逾60日結束": 0, "被新樞紐取代": 0}
    for s in sorted(ST):
        S = ST[s]; X = S["cfg"][(meth, R)]
        acc["純合併後_不看剔除"] += X["n_pure"]
        if meth != "丙":
            for k in lines:
                lines[k] += X["stats"][k]
        nk = 0
        for r in X["rows"]:
            acc["原始事件_窗內"] += 1; acc[r["狀態"]] += 1
            if r["狀態"] != "合併掉":
                flag["硬斷點"] += r["f_brk"]; flag["T+1停牌"] += r["f_halt"]; flag["T+1開盤漲停"] += r["f_lim"]
                flag["T+1停牌_其中已下市"] += int(r["f_halt"] and r["f_dl_t1"])
            if r["狀態"] == "保留":
                nk += 1; kept.append((s, S["market"], r["T"]))
                kept_dl += r["f_dl_in"]; kept_lit_extra += int(r["f_brk_lit"] and not r["f_brk"])
            if meth == "丙":
                ad = str(cal[r["first"]].date()); cd = ""
            else:
                ad = "|".join(str(cal[a].date()) for a in r["anchors"]); cd = str(cal[r["conf"]].date())
            rows_csv.append({"sid": s, "market": S["market"], "T": str(cal[r["T"]].date()),
                             ("回歸窗起點" if meth == "丙" else "取點"): ad, **({} if meth == "丙" else {"確認日": cd}),
                             "狀態": r["狀態"]})
        if S["expo"] > 0:
            per_stock.append({"sid": s, "market": S["market"], "yrs": S["expo"] / DPY, "n": nk})
    P = pd.DataFrame(per_stock)
    P["rate"] = P["n"] / P["yrs"]
    P1 = P[P["yrs"] >= 1.0]
    rate = {"全體": {**qd(P1["rate"]), "合併母體比率_事件每股票年": round(float(P["n"].sum() / P["yrs"].sum()), 4),
                   "股票年": round(float(P["yrs"].sum()), 1)}}
    for mk in ("twse", "tpex"):
        Pm = P[P["market"] == mk]; P1m = P1[P1["market"] == mk]
        rate[{"twse": "上市", "tpex": "上櫃"}[mk]] = {**qd(P1m["rate"]), "合併母體比率_事件每股票年": round(float(Pm["n"].sum() / Pm["yrs"].sum()), 4)}
    K = pd.DataFrame(kept, columns=["sid", "market", "T"])
    blocks = int(np.minimum((K["T"] - w0) // BLOCK, BLOCK_CAP - 1).nunique()) if len(K) else 0
    res = {"事件帳": acc, "剔除旗標_逐項（未被合併者；可重複）": flag,
           "保留中_持有期內下市（delist on 以最後成交價了結，未剔除）": int(kept_dl),
           "保留中_若照H2字面下市後缺日也算硬斷點會多剔除": int(kept_lit_extra),
           "保留事件數": int(len(K)), "相異檔數": int(K["sid"].nunique()) if len(K) else 0,
           "有事件的曆月數": int(pd.Series([str(cal[t])[:7] for t in K["T"]]).nunique()) if len(K) else 0,
           "有事件的20日區段數": blocks, "min(保留事件數,區段數)": int(min(len(K), blocks)),
           "每檔每年（合併後、剔除後）": rate,
           "逐年保留事件數": {str(k): int(v) for k, v in pd.Series([cal[t].year for t in K["T"]]).value_counts().sort_index().items()} if len(K) else {},
           "市場別保留事件數": {({"twse": "上市", "tpex": "上櫃"}.get(k, k)): int(v) for k, v in K["market"].value_counts().items()} if len(K) else {}}
    if meth != "丙":
        res["線的帳（全期，含窗外）"] = lines
    return res, pd.DataFrame(rows_csv)


def main():
    t0 = time.time()
    fx = STM.run_all()                                     # ⭐ fixture 全過才開跑（任一條 assert 失敗 ⇒ 例外中止）
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 4
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS, (cal[w0], cal[w1])
    wE = w1 - H_OUT
    DPY = (wE - w0 + 1) / ((cal[wE] - cal[w0]).days / 365.25)
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    print("[資料] 快照 {}｜日曆 {} 根｜判定窗 [{}, {}] {} 日｜T 可落 [{}, {}]｜每年交易日 {:.2f}｜gate3 {:,} 檔｜官方下市 {:,}".format(
        SHA[:10], n, W0, W1, WIN_DAYS, cal[w0].date(), cal[wE].date(), DPY, len(U), len(off)), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, off)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    print("[讀檔＋偵測] 可用 {:,} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    R_ = {"性質": "PREREGM §六 第一欄 頻率盤點（⛔ 未計算任何報酬）", "快照": SHA, "判定窗": [W0, W1], "T可落窗": [str(cal[w0].date()), str(cal[wE].date())],
          "gate3母體": int(len(U)), "可用檔數": int(len(ST)), "每年交易日": round(DPY, 3),
          "設計參數": {"R主格": TM.R_MAIN, "描述臂R": [3, 10], "跨度": TM.MAX_SPAN, "有效期": TM.LIFE, "乙第三點": TM.TOL3,
                    "丙N": TM.REG_N, "丙R2": TM.REG_R2, "合併": MERGE, "區段": BLOCK, "區段上限": BLOCK_CAP},
          "fixture": fx,
          "資料診斷": {"有效K棒但還原high缺值": int(sum(S["nan_high"] for S in ST.values())),
                    "有效K棒但還原open缺值": int(sum(S["nan_open"] for S in ST.values())),
                    "下市狀態": pd.Series([S["status"] for S in ST.values()]).value_counts(dropna=False).to_dict()},
          "畫法": {}}
    for meth, R in CONFIGS:
        nm = cfg_name(meth, R)
        s, csv = summarize(ST, meth, R, cal, w0, DPY)
        R_["畫法"][nm] = s
        csv.to_csv(os.path.join(OUT, "events_{}.csv".format(nm)), index=False, encoding="utf-8")
        a = s["事件帳"]
        print("[{}] 原始 {:,}｜純合併 {:,}｜合併掉 {:,}｜剔除 斷點 {:,}／停牌 {:,}／漲停 {:,}｜保留 {:,}｜檔 {:,}｜月 {}｜區段 {}｜每股票年 {}".format(
            nm, a["原始事件_窗內"], a["純合併後_不看剔除"], a["合併掉"], a["剔除_硬斷點"], a["剔除_T+1停牌"], a["剔除_T+1開盤漲停"],
            a["保留"], s["相異檔數"], s["有事件的曆月數"], s["有事件的20日區段數"], s["每檔每年（合併後、剔除後）"]["全體"]["合併母體比率_事件每股票年"]), flush=True)
    json.dump(R_, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R_["畫法"], ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

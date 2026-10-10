# -*- coding: utf-8 -*-
"""減資價格斷點查核（裁定 seq329 §五；情報 1011-0021 C 題「減資董事會決議後 20 天月差 −124.7%」）。回測線計算子代理。

⛔ 唯讀分析：不改任何既有程式、結果夾、正式結果；不碰信箱；不 commit。只寫 backtest/resultsCapRedAudit/（彙總）與 ~/capred_work/（逐筆中間檔，不進 repo）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchCapRedAudit scan [--procs 3]   # 掃六個資料版面
    ...                                                       -m backtest.researchCapRedAudit report                # 交叉比對＋REPORT.md

═══ 問什麼（裁定 seq329 §五）═══
 Q1 正式引擎（營量 v1、營飆 v1 ＝ rerun17／research11.load_bars 的 next_bad；0050 錨 ＝ rerun17.load_bench）有沒有擋到現金減資、彌補虧損的恢復買賣日
 Q2 data/adj 是否涵蓋減資；逐事件看恢復交易日前後還原收盤跳動、該日有沒有被標壞根
 Q3 營量 v1、營飆 v1 實際成交（resultsYL_flowexit/trades_A_entries：正式 T1 A 出場、全部種子）持有期跨過「沒被還原、也沒被擋」的跳動的筆數與報酬差；0050 錨
 Q4 近期研究：重大訊息類別（researchNewsCat 減資類）、地雷股（researchMine，s5 飆股名單）、F4 系列（researchF4Launch）

═══ 讀法（寫死；Z 標）═══
 Z1 有效 K 棒 ＝ data.load_stock 還原收盤非空（＝ 正式引擎）；相鄰兩根有效 K 棒 p→t（跨洞讀，tw-stock-price-breaks〈十一〉）
 Z2 還原比 ＝ 還原收(t)/還原收(p)；原始比 ＝ 原始收(t)/原始收(p)；gap ＝ t−p−1（版面交易日曆）
 Z3 事件歸屬 ＝ data/adj 事件日 ∈ (日期 p, 日期 t]（＝ data.breakpoints 同式；＝ research11 searchsorted 同式）
 Z4「還原後連續」⇔ 還原比 ∈ [0.895, 1.105]（± 漲跌幅 10% 加取整容差；research11 幽靈事件同門檻）
 Z5「沒解釋的跳動」⇔ (p, t] 內沒有任何 adj 事件 且 還原比 ∉ [0.895, 1.105]
 Z6 引擎壞根（正式；research11.load_bars 逐式）＝ 幽靈事件（原始收比÷因子 ∉ [0.895,1.105]）∨ gap ≥ 5 ∨ data.breakpoints 且 applies()
    價格規則壞根（researchNewsCat S7、researchF4Launch bad.json 同式）＝ 幽靈事件 ∨ data.breakpoints rule ∈ {price, price+gap}
 Z7「污染」＝ 沒解釋的跳動 ∧ 該規則沒標壞根（正式 → 引擎壞根；NewsCat／F4 → 價格規則壞根）
 Z8 跳動分類（依序第一個命中；官方、偵測、股數減少、新聞 ＝「減資類」RED）：
    官方減資表有 ＝ 上櫃 otc_reduce_history（官方 revivt）或 上市早年 TWTAUU（earlydata 3edc0e2206 reduce_events.csv）日期 ∈ (p, t]
    偵測減資有   ＝ 上櫃 otc_reduce_early（2007～2012 偵測）resume_day ∈ (p, t] 或 早年 detected_events（規則 A／B）e ∈ (p, t]
    上市後前5根  ＝ 該檔第 1～5 根有效 K 棒（新上市前 5 日無漲跌幅；不是減資）
    股數減少     ＝ 日檔 shares(t)/shares(p) ＜ 0.999（疑減資）
    新聞有減資   ＝ 重大訊息主旨含「減資」且公告日 ∈ [t−540 天, t]（8425186bd2 news 1998～2026；寬鬆旁證，會撈到無關跳動）
    其他         ＝ 以上皆無（成因不明）
 Z9 交易跨過 ＝ 進場位置 e ＜ t ≤ min(出場位置, 日曆尾)（進場 e 開盤、出場收盤；t ＝ e 當天開盤已在新基準，不算跨）
 Z10 正式交易的「另一份資料」報酬 ＝ 同日期、改用 origin/main 69e257c882 版面的還原價重算（收盤 ffill，同引擎）；差 ＝ 新 − 原
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D  # noqa: E402

H = os.path.expanduser
WORK = H("~/capred_work")
OUT = "backtest/resultsCapRedAudit"
LO, HI = 0.895, 1.105
WORLDS = {
    "main69":  (H("~/h2data/69e257c882067f4d652d39749b1635dabf54b911/data"), "origin/main 69e257c882（2026-10-10，最新）"),
    "edc":     (H("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data"), "正式引擎快照 edc6f8002f（營量 v1、營飆 v1、0050 錨）"),
    "nc8425":  (H("~/h2data/8425186bd20cdef4d39ac039ad2a6eda0903a8bb/data"), "重大訊息類別 主快照 8425186bd2"),
    "mine796": (H("~/h2data/mine_796d94c9dafd/data"), "地雷股 主快照 796d94c9da"),
    "stitch":  (H("~/evtdata/stitch_950ad26e12_b53f5540a8/data"), "接合版面 950ad26e12＋b53f5540a8（s5 飆股名單、F4 系列，2004～2026）"),
    "eotc":    (H("~/earlydata/eotc_f65bb03e11/otc/data"), "早年上市＋上櫃版面 eotc_f65bb03e11（重大訊息類別早年段，2004～2014）"),
}
NEWS = H("~/msdata/8425186bd20cdef4d39ac039ad2a6eda0903a8bb/data/mops/news")
EARLY_TWTAUU = H("~/earlydata/3edc0e2206/reduce_events.csv")
EARLY_DET = H("~/earlydata/3edc0e2206/detected_events.csv")
_G: dict = {}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ═════════════ scan：逐檔找「含減資事件的相鄰對」與「沒解釋的跳動」 ═════════════
def _init(data):
    D.DATA = data
    _G["cal"] = D.load_calendar()


def _one(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return []
    df = st.df
    c = df["close"].to_numpy(float)
    idx = np.flatnonzero(np.isfinite(c))
    n = len(idx)
    if n < 2:
        return []
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=lambda x: x in ("date", "close", "shares"))
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.drop_duplicates("date").set_index("date")
    rc = pd.to_numeric(raw["close"].reindex(cal), errors="coerce").to_numpy(float)[idx]
    sh = (pd.to_numeric(raw["shares"].reindex(cal), errors="coerce").to_numpy(float)[idx] if "shares" in raw else np.full(n, np.nan))
    sh[~(sh > 0)] = np.nan
    cc = c[idx]
    dates = cal[idx]
    adj = D.load_adj(sid)
    phantom = np.zeros(n, bool)
    ev = {}
    if adj is not None and len(adj):
        for d, f, kind, event in zip(adj["date"], adj["factor"].astype(float), adj["kind"].astype(str), adj["event"].astype(str)):
            k = int(np.searchsorted(dates, d))
            if k >= n:
                continue
            ev.setdefault(k, []).append((str(pd.Timestamp(d).date()), kind, event, float(f)))
            if k > 0 and not np.isnan(rc[k]) and not np.isnan(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < LO or r > HI:
                    phantom[k] = True
    gap = np.r_[0, np.diff(idx) - 1]
    bpm = {}
    for b in D.breakpoints(df, st.event_dates):
        bpm[int(np.searchsorted(idx, b["pos"]))] = b
    ratio = np.r_[np.nan, cc[1:] / cc[:-1]]
    rraw = np.r_[np.nan, rc[1:] / rc[:-1]]
    rows = []
    for k in range(1, n):
        evs = ev.get(k, [])
        red = [e for e in evs if e[2] == "reduce"]
        unexpl = (not evs) and (ratio[k] < LO or ratio[k] > HI)
        if not (red or unexpl):
            continue
        b = bpm.get(k)
        bp_applies = bool(b is not None and D.applies(b))
        bp_price = bool(b is not None and b["rule"] in ("price", "price+gap"))
        eng_bad = bool(phantom[k] or gap[k] >= 5 or bp_applies)
        px_bad = bool(phantom[k] or bp_price)
        rows.append({"sid": sid, "mk": mk, "p_pos": int(idx[k - 1]), "t_pos": int(idx[k]),
                     "p_date": str(dates[k - 1].date()), "t_date": str(dates[k].date()), "gap": int(gap[k]),
                     "adj_ratio": float(ratio[k]), "raw_ratio": float(rraw[k]),
                     "type": "reduce" if red else "unexplained",
                     "red_date": red[0][0] if red else "", "red_kind": red[0][1] if red else "",
                     "red_factor": red[0][3] if red else np.nan, "n_ev": len(evs),
                     "other_ev": ";".join(f"{e[1]}" for e in evs if e[2] != "reduce"),
                     "phantom": bool(phantom[k]), "bp_rule": (b["rule"] if b is not None else ""),
                     "bp_liq": (bool(b["liq_ok"]) if b is not None else False),
                     "eng_bad": eng_bad, "px_bad": px_bad,
                     "continuous": bool(LO <= ratio[k] <= HI), "bar_k": int(k),
                     "shares_ratio": float(sh[k] / sh[k - 1]) if np.isfinite(sh[k]) and np.isfinite(sh[k - 1]) else np.nan,
                     "beyond_compound": bool(ratio[k] < LO ** (gap[k] + 1) or ratio[k] > HI ** (gap[k] + 1))})
    return rows


def scan(procs):
    os.makedirs(WORK, exist_ok=True)
    meta = {}
    for w, (data, desc) in WORLDS.items():
        T0 = time.time()
        D.DATA = data
        cal = D.load_calendar()
        uni = D.load_universe()
        args = list(zip(uni["stock_id"], uni["market"]))
        with Pool(procs, initializer=_init, initargs=(data,)) as P:
            res = P.map(_one, args, chunksize=8)
        rows = [r for rr in res for r in rr]
        R = pd.DataFrame(rows)
        R.insert(0, "world", w)
        R.to_pickle(os.path.join(WORK, f"scan_{w}.pkl"))
        meta[w] = {"desc": desc, "data": data, "日曆": [str(cal[0].date()), str(cal[-1].date()), len(cal)],
                   "母體檔數": len(args), "列": len(R), "秒": round(time.time() - T0)}
        log(f"[scan] {w} {meta[w]}")
    json.dump(meta, open(os.path.join(WORK, "scan_meta.json"), "w"), ensure_ascii=False, indent=1)


# ═════════════ report ═════════════
def load_news():
    out = {}
    for f in sorted(glob.glob(os.path.join(NEWS, "*.csv"))):
        n = pd.read_csv(f, dtype=str, usecols=["date", "stock_id", "subject"])
        n = n[n["subject"].fillna("").str.contains("減資")]
        for s, d in zip(n["stock_id"], n["date"]):
            out.setdefault(s, []).append(np.datetime64(d))
    return {s: np.sort(np.array(v, dtype="datetime64[D]")) for s, v in out.items()}


def load_official():
    m = WORLDS["main69"][0]
    oh = pd.read_csv(os.path.join(m, "meta", "otc_reduce_history.csv"), dtype=str)[["stock_id", "date"]]
    tw = pd.read_csv(EARLY_TWTAUU, dtype=str).rename(columns={"e": "date"})[["stock_id", "date"]]
    off = pd.concat([oh, tw])
    oe = pd.read_csv(os.path.join(m, "meta", "otc_reduce_early", "otc_reduce_detected_2007_2012.csv"), dtype=str)
    de = pd.read_csv(EARLY_DET, dtype=str)
    det = pd.concat([oe.rename(columns={"resume_day": "date"})[["stock_id", "date"]], de.rename(columns={"e": "date"})[["stock_id", "date"]]])

    def todict(x):
        o = {}
        for s, d in zip(x["stock_id"], x["date"]):
            o.setdefault(s, []).append(np.datetime64(d))
        return {s: np.sort(np.array(v, dtype="datetime64[D]")) for s, v in o.items()}
    return todict(off), todict(det), {"官方": len(off), "偵測": len(det)}


def classify(R, off, det, news):
    cls = []
    for s, p, t, k, shr in zip(R["sid"], R["p_date"], R["t_date"], R["bar_k"], R["shares_ratio"]):
        p = np.datetime64(p); t = np.datetime64(t)
        a = off.get(s)
        if a is not None and ((a > p) & (a <= t)).any():
            cls.append("官方減資表有"); continue
        a = det.get(s)
        if a is not None and ((a > p) & (a <= t)).any():
            cls.append("偵測減資有"); continue
        if k <= 5:
            cls.append("上市後前5根"); continue
        if np.isfinite(shr) and shr < 0.999:
            cls.append("股數減少"); continue
        a = news.get(s)
        if a is not None and ((a >= t - np.timedelta64(540, "D")) & (a <= t)).any():
            cls.append("新聞有減資"); continue
        cls.append("其他")
    return cls


def md_table(df, cols=None):
    cols = cols or list(df.columns)
    L = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        L.append("| " + " | ".join("" if (isinstance(r[c], float) and np.isnan(r[c])) else (f"{r[c]:.4f}" if isinstance(r[c], float) else str(r[c])) for c in cols) + " |")
    return "\n".join(L)


def report():
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    meta = json.load(open(os.path.join(WORK, "scan_meta.json")))
    S = {w: pd.read_pickle(os.path.join(WORK, f"scan_{w}.pkl")) for w in WORLDS}
    news = load_news(); off, det, ocnt = load_official()
    log(f"news 減資 {sum(len(v) for v in news.values())} 則／{len(news)} 檔｜官方 {ocnt}")
    SUM = {"讀法": "見程式 docstring Z1～Z10", "版面": meta, "減資名單筆數": ocnt}
    for w in S:
        R = S[w]
        R["period"] = np.where(R["t_date"] < "2015-01-01", "2004-2014", "2015-")
        u = R["type"] == "unexplained"
        R.loc[u, "cls"] = classify(R[u], off, det, news)
        R.loc[~u, "cls"] = "adj 減資事件"
        R["dir"] = np.where(R["adj_ratio"] > 1, "上跳", "下跳")
        R["gapb"] = pd.cut(R["gap"], [-1, 0, 4, 10_000], labels=["0", "1-4", ">=5"]).astype(str)
        S[w] = R

    # ── Q2：adj 減資事件逐筆（各版面）
    q2 = []
    for w, R in S.items():
        A = R[R["type"] == "reduce"]
        q2.append({"版面": w, "adj 減資事件（落在有效 K 棒上）": len(A),
                   "上市": int((A["mk"] == "twse").sum()), "上櫃": int((A["mk"] == "tpex").sum()),
                   "還原後連續": int(A["continuous"].sum()), "不連續": int((~A["continuous"]).sum()),
                   "不連續且引擎壞根": int((~A["continuous"] & A["eng_bad"]).sum()),
                   "不連續且價格規則壞根": int((~A["continuous"] & A["px_bad"]).sum()),
                   "引擎壞根（含連續）": int(A["eng_bad"].sum()), "其中 gap≥5": int((A["gap"] >= 5).sum()),
                   "最早": A["t_date"].min() if len(A) else "", "最晚": A["t_date"].max() if len(A) else ""})
    Q2 = pd.DataFrame(q2)
    A69 = S["main69"][S["main69"]["type"] == "reduce"].copy()
    A69[["sid", "mk", "red_date", "red_kind", "red_factor", "p_date", "t_date", "gap", "raw_ratio", "adj_ratio", "continuous",
         "phantom", "eng_bad", "px_bad", "bp_rule"]].to_csv(os.path.join(OUT, "reduce_events_main.csv"), index=False, float_format="%.6g")


    # ── 沒解釋的跳動彙總（各版面 × 期 × 分類）
    q3 = []
    for w, R in S.items():
        U = R[R["type"] == "unexplained"]
        for (per, cl), g in U.groupby(["period", "cls"]):
            q3.append({"版面": w, "期": per, "分類": cl, "筆": len(g), "檔": g["sid"].nunique(),
                       "上跳": int((g["adj_ratio"] > 1).sum()), "超出逐日複利帶": int(g["beyond_compound"].sum()),
                       "引擎壞根": int(g["eng_bad"].sum()), "引擎沒擋": int((~g["eng_bad"]).sum()),
                       "價格規則壞根": int(g["px_bad"].sum()), "價格規則沒擋": int((~g["px_bad"]).sum()),
                       "gap0": int((g["gap"] == 0).sum()), "gap1-4": int(g["gap"].between(1, 4).sum()), "gap≥5": int((g["gap"] >= 5).sum())})
    Q3 = pd.DataFrame(q3)
    Q3.to_csv(os.path.join(OUT, "unexplained_summary.csv"), index=False)
    JJ = pd.concat([R[(R["type"] == "unexplained") & (R["cls"].isin(RED))] for R in S.values()])
    JJ[["world", "sid", "mk", "cls", "p_date", "t_date", "gap", "raw_ratio", "adj_ratio", "shares_ratio", "eng_bad", "px_bad", "bp_rule"]].to_csv(
        os.path.join(OUT, "unexplained_reduce_like.csv"), index=False, float_format="%.6g")

    # ── Q3：正式交易（edc；resultsYL_flowexit/trades_A_entries ＝ 正式 T1 A 出場）
    D.DATA = WORLDS["edc"][0]
    cal = D.load_calendar(); ncal = len(cal)
    TR = pd.read_csv("backtest/resultsYL_flowexit/trades_A_entries.csv.gz", dtype={"sid": str},
                     usecols=["sid", "e", "策略", "r", "A_xpos", "A_g", "進場日"])
    bad_date = int((pd.to_datetime(TR["進場日"]).to_numpy() != cal[TR["e"].to_numpy()].to_numpy()).sum())
    U = TR.drop_duplicates(["策略", "sid", "e", "A_xpos"]).reset_index(drop=True)
    E = S["edc"]
    q4 = {"交易列（含全部種子）": len(TR), "不重複交易": len(U), "進場日≠引擎日曆": bad_date,
          "種子數": {k: int(v) for k, v in TR.groupby("策略")["r"].nunique().items()},
          "不重複交易／策略": {k: int(v) for k, v in U.groupby("策略").size().items()}}
    # 對照（驗 cross 有作用）：持有期跨過 adj 除權息事件的不重複交易
    exr = []
    for s in U["sid"].unique():
        a = D.load_adj(s)
        if a is None:
            continue
        for d in a.loc[a["event"] == "exright", "date"]:
            exr.append({"sid": s, "t_pos": int(cal.searchsorted(d))})
    EXR = pd.DataFrame(exr)
    q4["對照：持有期跨過 adj 除權息事件的不重複交易"] = len(set(i for i, _ in cross(U["sid"].to_numpy(), U["e"].to_numpy(), U["A_xpos"].to_numpy(), EXR, ncal)))
    det_rows = []
    for lab, J in (("adj 減資事件", E[E["type"] == "reduce"]), ("沒解釋的跳動", E[E["type"] == "unexplained"])):
        hits = cross(U["sid"].to_numpy(), U["e"].to_numpy(), U["A_xpos"].to_numpy(), J, ncal)
        q4[f"持有期跨過｜{lab}"] = len(set(i for i, _ in hits))
        for i, j in hits:
            r = U.loc[i]; jr = J.loc[j]
            nseed = int(((TR["策略"] == r["策略"]) & (TR["sid"] == r["sid"]) & (TR["e"] == r["e"]) & (TR["A_xpos"] == r["A_xpos"])).sum())
            det_rows.append({"類": lab, "策略": r["策略"], "sid": r["sid"], "進場日": r["進場日"],
                             "出場日": str(cal[min(int(r['A_xpos']), ncal - 1)].date()), "種子數": nseed, "A_g": r["A_g"],
                             "跳動日": jr["t_date"], "gap": jr["gap"], "還原比": jr["adj_ratio"], "連續": jr["continuous"],
                             "引擎壞根": jr["eng_bad"], "分類": jr["cls"]})
    X = pd.DataFrame(det_rows)
    X.to_csv(os.path.join(OUT, "formal_trades_cross.csv"), index=False, float_format="%.6g")
    # 正式引擎有沒有「擋到」減資恢復日：edc adj 減資事件的恢復根是否都是引擎壞根
    Ae = E[E["type"] == "reduce"]
    q4["edc adj 減資恢復根｜引擎壞根"] = f"{int(Ae['eng_bad'].sum())}/{len(Ae)}"
    Ue = E[(E["type"] == "unexplained") & E["cls"].isin(RED)]
    q4["edc 減資類沒解釋跳動｜引擎壞根"] = f"{int(Ue['eng_bad'].sum())}/{len(Ue)}"

    # ── 0050 錨
    b0 = {}
    for w in ("edc", "main69"):
        D.DATA = WORLDS[w][0]
        cw = D.load_calendar()
        st = D.load_stock("0050", "twse", cw)
        cl = st.df["close"].dropna()
        rr = cl / cl.shift(1)
        out = rr[(rr < LO) | (rr > HI)]
        b0[w] = {"有效 K 棒": int(len(cl)), "還原日比超出 [0.895,1.105] 的日": {str(k.date()): round(float(v), 4) for k, v in out.items()},
                 "還原日比 最小／最大": [round(float(rr.min()), 4), round(float(rr.max()), 4)],
                 "adj 事件": {k: int(v) for k, v in D.load_adj("0050")["event"].value_counts().items()}}
    D.DATA = WORLDS["edc"][0]

    # ── Q4a：重大訊息類別（~/ncwork/events.pkl；main ＝ nc8425、early ＝ eotc；S7 ＝ 價格規則壞根）
    EV = pd.read_pickle(H("~/ncwork/events.pkl"))
    EV = EV[EV["status"] == "保留"].reset_index(drop=True)
    nc_rows = []
    for wname, wkey in (("main", "nc8425"), ("early", "eotc")):
        Ew = EV[EV["world"] == wname]
        J = S[wkey][(S[wkey]["type"] == "unexplained") & (~S[wkey]["px_bad"])]
        for Hh in (1, 5, 20):
            xend = np.where(Ew["type"] == "C", Ew["epos"] + Hh, Ew["epos"] + Hh - 1)
            ok = Ew[f"R{Hh}"].notna().to_numpy()
            ii = np.flatnonzero(ok)
            for i, j in cross(Ew["stock_id"].to_numpy()[ok], Ew["epos"].to_numpy()[ok], xend[ok], J, 10 ** 9):
                r = Ew.iloc[ii[i]]; jr = J.loc[j]
                nc_rows.append({"world": wname, "H": Hh, "cat": int(r["cat"]), "sub3": r["sub3"], "seg": r["seg"], "date": r["date"],
                                "time": r["time"], "serial": r["serial"], "stock_id": r["stock_id"], "type": r["type"], "X": r[f"X{Hh}"],
                                "jump_date": jr["t_date"], "adj_ratio": jr["adj_ratio"], "gap": jr["gap"], "cls": jr["cls"], "red": jr["cls"] in RED})
    NCX = pd.DataFrame(nc_rows)
    NCX.to_csv(os.path.join(OUT, "newscat_cross.csv"), index=False, float_format="%.6g")
    names = {1: "注意交易", 2: "澄清", 3: "減資", 4: "併購合資", 5: "增資發債", 6: "得標接單", 7: "取得處分資產", 8: "8", 9: "9", 10: "10", 11: "11", 12: "其他"}
    ncr = []
    key = lambda df: set(zip(df["stock_id"], df["date"], df["time"], df["serial"]))
    for seg in ("早年", "探索", "確認"):
        for cat in sorted(EV["cat"].unique()):
            for Hh in (1, 5, 20):
                base = EV[(EV["cat"] == cat) & (EV["seg"] == seg) & EV[f"X{Hh}"].notna()]
                bx = NCX[(NCX["H"] == Hh) & (NCX["cat"] == cat) & (NCX["seg"] == seg)] if len(NCX) else NCX
                kall = key(bx) if len(bx) else set(); kred = key(bx[bx["red"]]) if len(bx) else set()
                kb = np.array([k in kall for k in zip(base["stock_id"], base["date"], base["time"], base["serial"])], bool)
                ncr.append({"段": seg, "cat": int(cat), "類": names.get(int(cat), str(cat)), "H": Hh, "則": len(base),
                            "跨過沒擋跳動": int(kb.sum()), "其中減資類跳動": len(kred),
                            "X 平均": float(base[f"X{Hh}"].mean()) if len(base) else np.nan,
                            "剔除後 X 平均": float(base.loc[~kb, f"X{Hh}"].mean()) if len(base) else np.nan})
    NCR = pd.DataFrame(ncr)
    NCR["差（剔除後−原）"] = NCR["剔除後 X 平均"] - NCR["X 平均"]
    NCR.to_csv(os.path.join(OUT, "newscat_effect.csv"), index=False, float_format="%.6g")
    sub = {}
    for seg in ("早年", "探索", "確認"):
        base = EV[(EV["cat"] == 3) & (EV["seg"] == seg) & (EV["sub3"] == "現金減資／彌補虧損") & EV["X20"].notna()]
        bx = NCX[(NCX["H"] == 20) & (NCX["cat"] == 3) & (NCX["seg"] == seg) & (NCX["sub3"] == "現金減資／彌補虧損")] if len(NCX) else NCX
        kb = np.array([k in key(bx) for k in zip(base["stock_id"], base["date"], base["time"], base["serial"])], bool) if len(bx) else np.zeros(len(base), bool)
        sub[seg] = {"則": len(base), "跨過": int(kb.sum()), "X20 平均": float(base["X20"].mean()), "剔除後": float(base.loc[~kb, "X20"].mean()),
                    "X20 最小": float(base["X20"].min()), "X20 ≤ −100% 筆": int((base["X20"] <= -1).sum())}

    # ── Q4b：s5 飆股名單（stitch；S3 壞根 ＝ 價格規則）——網格列跨過沒擋的上跳；扣掉跳動後掉到門檻下 ⇒「假飆股」
    s5 = np.load(H("~/s5work/events.npz"))
    uni5 = pd.read_csv(H("~/s5work/uni.csv"), dtype=str)
    D.DATA = WORLDS["stitch"][0]; calS = D.load_calendar()
    GS5 = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
    EP = pd.DataFrame({"cell": s5["cell"], "s": s5["s"], "d": s5["d"], "P": s5["P"], "M": s5["M"]})
    EP["sid"] = uni5["stock_id"].to_numpy()[EP["s"].to_numpy()]
    EP["g"] = np.array(GS5)[EP["cell"].to_numpy() % len(GS5)]
    EP["per"] = np.where(calS[EP["d"].to_numpy()] < pd.Timestamp("2015-01-01"), "2004-2014", "2015-")
    JS = S["stitch"]
    J = JS[(JS["type"] == "unexplained") & (~JS["px_bad"]) & (JS["adj_ratio"] > 1)]
    hits = cross(EP["sid"].to_numpy(), EP["d"].to_numpy(), EP["P"].to_numpy(), J, len(calS))
    H5 = pd.DataFrame(hits, columns=["i", "j"])
    H5["ratio"] = J.loc[H5["j"], "adj_ratio"].to_numpy(); H5["red"] = J.loc[H5["j"], "cls"].isin(RED).to_numpy(); H5["strong"] = J.loc[H5["j"], "cls"].isin(STRONG).to_numpy()
    agg = H5.groupby("i").agg(prod=("ratio", "prod"), red=("red", "any"), strong=("strong", "any"))
    agg = agg.join(EP[["M", "g", "per", "sid", "cell", "d"]])
    agg["fake"] = (1 + agg["M"]) / agg["prod"] - 1 < agg["g"]
    s5r = {"網格事件列": int(len(EP))}
    for per in ("2004-2014", "2015-"):
        a = agg[agg["per"] == per]
        s5r[per] = {"網格事件列": int((EP["per"] == per).sum()), "網格不重複(s,d)": int(EP[EP["per"] == per].drop_duplicates(["sid", "d"]).shape[0]), "跨過沒擋上跳": int(len(a)), "其中減資類跳動": int(a["red"].sum()),
                    "扣掉跳動後低於門檻（假飆股）": int(a["fake"].sum()), "假飆股｜減資類（含新聞旁證）": int((a["fake"] & a["red"]).sum()), "跨過｜強證據減資（官方、偵測、股數減少）": int(a["strong"].sum()), "假飆股｜強證據減資": int((a["fake"] & a["strong"]).sum()), "假飆股｜強證據減資｜檔數": int(a.loc[a["fake"] & a["strong"], "sid"].nunique()), "假飆股｜強證據減資｜不重複(s,d)": int(a.loc[a["fake"] & a["strong"]].drop_duplicates(["sid", "d"]).shape[0]),
                    "涉及檔數": int(a["sid"].nunique()), "假飆股涉及檔數": int(a.loc[a["fake"], "sid"].nunique())}
    agg.reset_index().groupby(["per", "strong", "red", "fake"]).size().rename("列").reset_index().to_csv(os.path.join(OUT, "s5_cross_summary.csv"), index=False)

    # ── Q4c：F4Launch 逐筆出場（stitch；bad ＝ 價格規則）
    EX = pd.read_pickle(H("~/f4lwork/exits.pkl"))
    EX["sid"] = uni5["stock_id"].to_numpy()[EX["s"].to_numpy()]
    JF = JS[(JS["type"] == "unexplained") & (~JS["px_bad"])]
    f4 = {"出場列": int(len(EX))}
    f4rows = []
    for v in ("E1b", "E1r", "E2b", "E2r"):
        okv = (EX[f"{v}_xpos"] >= 0).to_numpy()
        ii = np.flatnonzero(okv)
        hits = cross(EX["sid"].to_numpy()[okv], EX["e"].to_numpy()[okv], EX[f"{v}_xpos"].to_numpy()[okv], JF, len(calS))
        Hf = pd.DataFrame(hits, columns=["i", "j"])
        if len(Hf) == 0:
            f4[v] = {"跨過": 0}; continue
        Hf["ratio"] = JF.loc[Hf["j"], "adj_ratio"].to_numpy(); Hf["red"] = JF.loc[Hf["j"], "cls"].isin(RED).to_numpy(); Hf["strong"] = JF.loc[Hf["j"], "cls"].isin(STRONG).to_numpy()
        Hf["cls"] = JF.loc[Hf["j"], "cls"].to_numpy(); Hf["jd"] = JF.loc[Hf["j"], "t_date"].to_numpy()
        ag = Hf.groupby("i").agg(prod=("ratio", "prod"), red=("red", "any"), strong=("strong", "any"), cls=("cls", lambda x: "+".join(sorted(set(x)))), jd=("jd", "first"))
        ag["row"] = ii[ag.index.to_numpy()]
        ag["g"] = EX[f"{v}_g"].to_numpy()[ag["row"]]
        ag["g_扣跳動"] = (1 + ag["g"]) / ag["prod"] - 1
        ag["進場日"] = [str(calS[int(x)].date()) for x in EX["e"].to_numpy()[ag["row"]]]
        ag["sid"] = EX["sid"].to_numpy()[ag["row"]]
        ag["主窗"] = np.array(ag["進場日"]) >= "2017-03-02"
        f4[v] = {"跨過沒擋跳動": int(len(ag)), "其中主窗": int(ag["主窗"].sum()), "其中減資類跳動（含新聞旁證）": int(ag["red"].sum()), "其中強證據減資": int(ag["strong"].sum()), "強證據者 g 合計": float(ag.loc[ag["strong"], "g"].sum()), "強證據者扣跳動後 g 合計": float(ag.loc[ag["strong"], "g_扣跳動"].sum()),
                 "g 合計（跨過者）": float(ag["g"].sum()), "扣跳動後 g 合計": float(ag["g_扣跳動"].sum()),
                 "跳動分類": {k: int(x) for k, x in ag["cls"].value_counts().items()}}
        for _, r in ag.iterrows():
            f4rows.append({"變體": v, "sid": r["sid"], "進場日": r["進場日"], "跳動日": r["jd"], "跳動積": r["prod"], "分類": r["cls"],
                           "g": r["g"], "g_扣跳動": r["g_扣跳動"]})
    pd.DataFrame(f4rows).to_csv(os.path.join(OUT, "f4launch_cross.csv"), index=False, float_format="%.6g")
    # 組合層實際成交（~/f4lwork/trades.pkl：{(段, 臂, 格, 版), 種子} → [(進場位置, 'sid#pos', 進場價, 出場位置, 出場價)]）
    TP = pd.read_pickle(H("~/f4lwork/trades.pkl"))
    byj = {s: (g["t_pos"].to_numpy(), g["adj_ratio"].to_numpy(), g["cls"].isin(STRONG).to_numpy()) for s, g in JF.groupby("sid")}
    f4p = {}
    f4prow = {}
    for (cellk, seed), lst in TP.items():
        ck = "｜".join(cellk)
        d = f4p.setdefault(ck, {"種子": 0, "成交筆（種子合計）": 0, "跨過沒擋跳動": 0, "跨過強證據減資": 0, "受影響種子": set(), "強證據受影響種子": set(),
                                "報酬差合計（強證據，扣跳動−原）": 0.0})
        d["種子"] += 1
        for e, key, pin, x, pout in lst:
            d["成交筆（種子合計）"] += 1
            s = key.split("#")[0]
            g = byj.get(s)
            if g is None:
                continue
            m = (g[0] > e) & (g[0] <= min(x, len(calS) - 1))
            if not m.any():
                continue
            d["跨過沒擋跳動"] += 1; d["受影響種子"].add(seed)
            if g[2][m].any():
                d["跨過強證據減資"] += 1; d["強證據受影響種子"].add(seed)
                r0 = pout / pin - 1; r1 = (1 + r0) / float(np.prod(g[1][m & g[2]])) - 1
                d["報酬差合計（強證據，扣跳動−原）"] += r1 - r0
                f4prow[(key, x)] = {"key": key, "進場日": str(calS[int(e)].date()), "出場日": str(calS[min(int(x), len(calS) - 1)].date()),
                                    "報酬": r0, "扣跳動後": r1}
    for ck, d in f4p.items():
        d["受影響種子"] = len(d["受影響種子"]); d["強證據受影響種子"] = len(d["強證據受影響種子"])
    f4["組合層成交（trades.pkl）"] = {k: v for k, v in f4p.items() if v["跨過沒擋跳動"] > 0}
    f4["組合層成交｜強證據跨過的不重複成交"] = list(f4prow.values())

    SUM.update({"Q2_adj減資事件": Q2.to_dict("records"), "Q3_正式交易": q4, "0050": b0,
                "NewsCat_現金減資彌補虧損_H20": sub, "s5飆股網格": s5r, "F4Launch": f4, "秒": round(time.time() - T0)})
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    Q2.to_csv(os.path.join(OUT, "reduce_coverage_by_world.csv"), index=False)
    log("report 完")
    print(json.dumps({k: v for k, v in SUM.items() if k != "版面"}, ensure_ascii=False, indent=1, default=str)[:20000])
    print(Q3.to_string())
    print(NCR[(NCR["跨過沒擋跳動"] > 0)].to_string())
    if len(X):
        print(X.to_string())


RED = {"官方減資表有", "偵測減資有", "股數減少", "新聞有減資"}
STRONG = {"官方減資表有", "偵測減資有", "股數減少"}


def cross(trades_sid, trades_e, trades_x, J, ncal):
    """回傳 list of (trade_i, jump_row_label)：e < t ≤ min(x, ncal−1)。"""
    by = {s: (g["t_pos"].to_numpy(), g.index.to_numpy()) for s, g in J.groupby("sid")}
    out = []
    for i, (s, e, x) in enumerate(zip(trades_sid, trades_e, trades_x)):
        g = by.get(s)
        if g is None:
            continue
        x = min(int(x), ncal - 1)
        tp, lab = g
        for h in np.flatnonzero((tp > e) & (tp <= x)):
            out.append((i, lab[h]))
    return out


# ═════════════ focus：資料庫 1011-0059 點名的四筆（3073、8101、4415、6131）逐研究查 ═════════════
FOUR = ("3073", "8101", "4415", "6131")


def _jumps(w):
    R = pd.read_pickle(os.path.join(WORK, f"scan_{w}.pkl"))
    J = R[R["sid"].isin(FOUR) & (R["type"] == "unexplained") & ((R["adj_ratio"] < 0.6) | (R["adj_ratio"] > 1.4))]
    return {s: (int(r["t_pos"]), float(r["adj_ratio"]), r["t_date"], bool(r["eng_bad"]), bool(r["px_bad"])) for s, r in J.set_index("sid").iterrows()}


def _hit(J, sid, e, x):
    j = J.get(str(sid))
    return j is not None and int(e) < j[0] <= int(x)


def focus():
    import pickle
    os.makedirs(OUT, exist_ok=True)
    F = {}
    # ① 引擎：data.breakpoints／applies 與 research11 缺口規則
    D.DATA = WORLDS["edc"][0]; cal = D.load_calendar()
    uni = D.load_universe().set_index("stock_id")["market"]
    eng = {}
    for s in FOUR:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        bps = [b for b in D.breakpoints(st.df, st.event_dates) if abs(b["ratio"] - 1) > 0.4]
        eng[s] = [{"T": str(cal[b["pos"]].date()), "rule": b["rule"], "ratio": round(b["ratio"], 4), "gap": b["gap"], "liq_ok": b["liq_ok"],
                   "applies()": D.applies(b), "research11 缺口≥5": b["gap"] >= 5,
                   "正式引擎壞根（research11.load_bars）": bool(D.applies(b) or b["gap"] >= 5)} for b in bps]
    F["①引擎"] = eng
    Je = _jumps("edc")
    F["跳動（edc）"] = {s: {"恢復日": v[2], "還原比": v[1], "引擎壞根": v[3], "價格規則壞根": v[4]} for s, v in Je.items()}
    # ② 正式：實際成交、AND 訊號
    TR = pd.read_csv("backtest/resultsYL_flowexit/trades_A_entries.csv.gz", dtype={"sid": str}, usecols=["sid", "e", "策略", "r", "A_xpos", "進場日"])
    t4 = TR[TR["sid"].isin(FOUR)]
    F["②正式成交｜四檔任何時點"] = {f"{k[0]}｜{k[1]}": int(v) for k, v in t4.groupby(["策略", "sid"]).size().items()}
    F["②正式成交｜跨過跳動"] = int(sum(_hit(Je, s, e, x) for s, e, x in zip(t4["sid"], t4["e"], t4["A_xpos"])))
    AND = pd.read_csv("backtest/resultsN17/sig_edc6f/and_signals.csv.gz", dtype={"sid": str})
    a4 = AND[AND["sid"].isin(FOUR)]
    F["②AND 訊號（營飆／營量母表）｜四檔列"] = {s: int(v) for s, v in a4.groupby("sid").size().items()}
    F["②AND 訊號｜持有窗跨過（xpos≥0）"] = {c: int(sum(_hit(Je, s, e, x) for s, e, x in zip(a4["sid"], a4["entry_pos"], a4[c]) if x >= 0))
                                     for c in ("xpos_H60", "xpos_H120", "xpos_LD") if c in a4}
    F["②AND 訊號｜跳動後 250 根內出訊號（回看窗跨跳動）"] = {s: [str(cal[int(p)].date()) for p in a4.loc[a4["sid"] == s, "pos"]
                                                   if s in Je and 0 < int(p) - Je[s][0] < 250] for s in FOUR}
    # ③ PRE5 系（seq323 五件中的四件；無壞根剔除、收盤 ffill）＋ RevLimitUp、YL3m、YLmargin
    pre = {}
    for nm in ("TrendAll", "RevPriceOK", "PreFinRev", "EPSqoq"):
        x = pickle.load(open(H(f"~/pre5work/{nm}_run.pkl"), "rb"))
        d = {"挑中格": x["chosen"]}
        for arm in ("FB", "FR"):
            for cell, df in x[arm].items():
                sub = df[df["sid"].isin(FOUR)]
                h = [(s, int(e), int(xx), float(g)) for s, e, xx, g in zip(sub["sid"], sub["e"], sub["xpos"], sub["g"]) if _hit(Je, s, e, xx)]
                if h:
                    d[f"{arm}｜{cell}"] = [{"sid": s, "進場": str(cal[e].date()), "出場": str(cal[min(xx, len(cal) - 1)].date()), "g": round(g, 4),
                                           "g_扣跳動": round((1 + g) / Je[s][1] - 1, 4)} for s, e, xx, g in h]
        iv = [(s, a, b, w) for s, a, b, w, p in x["iv0"] if s in FOUR and _hit(Je, s, a, b)]
        d["第 0 顆實際持有跨過"] = [{"sid": s, "買": str(cal[a].date()), "賣": str(cal[min(b, len(cal) - 1)].date()), "權重": round(w, 4)} for s, a, b, w in iv]
        pre[nm] = d
    rl = pd.read_csv("backtest/resultsRevLimitUp/signals.csv.gz", dtype={"sid": str})
    r4 = rl[rl["sid"].isin(FOUR)]
    pre["RevLimitUp"] = {v: [{"sid": s, "進場": str(cal[int(e)].date()), "g": round(float(g), 4)} for s, e, xx, g in zip(r4["sid"], r4["e"], r4[f"{v}_xpos"], r4[f"{v}_g"])
                             if xx >= 0 and _hit(Je, s, e, xx)] for v in ("E1", "E2")}
    pre["RevLimitUp"]["四檔訊號列"] = int(len(r4))
    a3 = pd.read_csv(H("~/pre5work/and3m_signals.csv.gz"), dtype={"sid": str}); a3 = a3[a3["sid"].isin(FOUR)]
    pre["YL3m（and3m）"] = {"四檔列": int(len(a3)), **{c: int(sum(_hit(Je, s, e, x) for s, e, x in zip(a3["sid"], a3["entry_pos"], a3[c]) if x >= 0))
                                                  for c in ("xpos_H20", "xpos_H60", "xpos_H120", "xpos_LD")}}
    ym = pd.read_csv("backtest/resultsYLmargin/signals.csv.gz", dtype={"sid": str}); ym = ym[ym["sid"].isin(FOUR)]
    pre["YLmargin"] = {"四檔列": int(len(ym)), "H60 跨過": int(sum(_hit(Je, s, e, D.exit_pos(e, 60)) for s, e in zip(ym["sid"], ym["entry_pos"]))),
                       "H120 跨過": int(sum(_hit(Je, s, e, D.exit_pos(e, 120)) for s, e in zip(ym["sid"], ym["entry_pos"])))}
    F["③近期研究（edc 版面）"] = pre
    # ④ 地雷股 乙（月底判定 × 股；R ＝ m＋1 開盤 → m＋H 收盤 ffill；無壞根剔除）
    W = pickle.load(open(H("~/minework/world_main.pkl"), "rb"))
    FL = np.load(H("~/minework/flags_main.npz"))
    Jm = _jumps("mine796")
    me = W["me"]; segm = np.array([str(W["cal"][m])[:7] for m in me])
    yi = []
    for Hh in (20, 60, 120, 250):
        Y = np.load(H(f"~/minework/yi_main_H{Hh}.npz")); Rm, Bm = Y["R"], Y["BASE"]
        X = Rm - Bm
        Xc = X.copy()
        hits = []
        for s in FOUR:
            if s not in W["ix"] or s not in Jm:
                continue
            j = W["ix"][s]; tp, rat = Jm[s][0], Jm[s][1]
            for i, m in enumerate(me):
                if m + 1 < tp <= D.exit_pos(m + 1, Hh) and np.isfinite(X[i, j]) and W["EL"][i, j]:
                    Xc[i, j] = (1 + Rm[i, j]) / rat - 1 - Bm[i, j]; hits.append((i, j, s))
        for seg, (a, b) in (("探索", ("2017-03", "2021-12")), ("確認", ("2022-01", "2026-08"))):
            sm = (segm >= a) & (segm <= b)
            for f in ("G1", "G2", "G3", "F1_50", "F2_1", "F3_half", "F4", "F5"):
                ev = W["EL"] & sm[:, None] & FL[f] & np.isfinite(X)
                nh = sum(1 for i, j, s in hits if ev[i, j])
                if nh == 0:
                    continue
                yi.append({"H": Hh, "段": seg, "旗": f, "事件": int(ev.sum()), "跨過跳動": nh, "檔": ",".join(sorted({s for i, j, s in hits if ev[i, j]})),
                           "X 平均": float(X[ev].mean()), "扣跳動後 X 平均": float(Xc[ev].mean())})
            nf = W["EL"] & sm[:, None] & ~FL["G1"] & np.isfinite(X)
            nh = sum(1 for i, j, s in hits if nf[i, j])
            if nh:
                yi.append({"H": Hh, "段": seg, "旗": "無 G1", "事件": int(nf.sum()), "跨過跳動": nh, "檔": ",".join(sorted({s for i, j, s in hits if nf[i, j]})),
                           "X 平均": float(X[nf].mean()), "扣跳動後 X 平均": float(Xc[nf].mean())})
    YI = pd.DataFrame(yi)
    if len(YI):
        YI["差（點）"] = (YI["扣跳動後 X 平均"] - YI["X 平均"]) * 100
        YI.to_csv(os.path.join(OUT, "focus_mine_yi.csv"), index=False, float_format="%.6g")
    F["④地雷股乙｜受影響格數"] = int(len(YI))
    F["④地雷股乙｜最大差（點）"] = float(YI["差（點）"].abs().max()) if len(YI) else 0.0
    # ⑤ s5（地雷股甲丙、F4 系列）＋ F4Launch ＋ NewsCat ＋ BARR
    s5 = np.load(H("~/s5work/events.npz")); uni5 = pd.read_csv(H("~/s5work/uni.csv"), dtype=str)
    Js = _jumps("stitch")
    EP = pd.DataFrame({"s": s5["s"], "d": s5["d"], "P": s5["P"]}); EP["sid"] = uni5["stock_id"].to_numpy()[EP["s"].to_numpy()]
    e4 = EP[EP["sid"].isin(FOUR)]
    hh = [(s, d) for s, d, p in zip(e4["sid"], e4["d"], e4["P"]) if _hit(Js, s, d, p)]
    F["⑤s5 網格列跨過｜依檔"] = {s: int(sum(1 for x in hh if x[0] == s)) for s in FOUR}
    F["⑤s5 不重複起漲點跨過"] = len(set(hh))
    if "3073" in W["ix"]:
        j = W["ix"]["3073"]
        F["⑤3073 帶 F4 旗的月份（2019-06～2021-02）"] = [str(W["cal"][m])[:7] for i, m in enumerate(me) if FL["F4"][i, j] and "2019-06" <= str(W["cal"][m])[:7] <= "2021-02"]
    TP = pickle.load(open(H("~/f4lwork/trades.pkl"), "rb"))
    f4 = {}
    for (ck, seed), lst in TP.items():
        for e, key, pin, x, pout in lst:
            s = key.split("#")[0]
            if s in FOUR and _hit(Js, s, e, x):
                k = "｜".join(ck); f4.setdefault(k, {"種子": set(), "成交": key, "報酬": round(pout / pin - 1, 4), "扣跳動": round(pout / pin / Js[s][1] - 1, 4)})["種子"].add(seed)
    F["⑤F4Launch 組合層"] = {k: {**v, "種子": len(v["種子"])} for k, v in f4.items()}
    EV = pd.read_pickle(H("~/ncwork/events.pkl")); EV = EV[(EV["status"] == "保留") & (EV["world"] == "main") & EV["stock_id"].isin(FOUR)]
    Jn = _jumps("nc8425")
    nc = []
    for Hh in (1, 5, 20):
        for _, r in EV[EV[f"R{Hh}"].notna()].iterrows():
            xend = r["epos"] + Hh if r["type"] == "C" else r["epos"] + Hh - 1
            if _hit(Jn, r["stock_id"], r["epos"], xend):
                nc.append({"H": Hh, "sid": r["stock_id"], "date": r["date"], "cat": int(r["cat"]), "seg": r["seg"], "R": round(float(r[f"R{Hh}"]), 4)})
    F["⑤NewsCat 主段跨過"] = nc
    B = pd.read_csv("backtest/resultsBARR/events_freq.csv.gz", dtype={"sid": str}); B = B[B["sid"].isin(FOUR)]
    bh = []
    for _, r in B.iterrows():
        j = Je.get(r["sid"])
        if j is not None and r["H1日"] < j[2] <= r["日期"]:
            bh.append({"sid": r["sid"], "H1日": r["H1日"], "T": r["日期"], "hard": bool(r["hard"]), "剔": bool(r["剔"])})
    F["⑤BARR 頻率事件窗跨過"] = bh
    json.dump(F, open(os.path.join(OUT, "focus_four.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(F, ensure_ascii=False, indent=1, default=str))
    if len(YI):
        print(YI.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["scan", "report", "focus"])
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    {"scan": lambda: scan(a.procs), "report": report, "focus": focus}[a.mode]()

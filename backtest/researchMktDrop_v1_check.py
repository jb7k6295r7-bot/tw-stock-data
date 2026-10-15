# -*- coding: utf-8 -*-
"""PREREG大盤大跌後買什麼 seq1 —— 獨立重算（事件清單＋主出場結果），對 researchMktDrop_v1 的輸出差 ≤ 1e−9。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_v1_check [--procs 4]

獨立寫法（⛔ 不呼叫 v1 與初測的事件、籃子、出場函式；只共用資料層：market_index.csv、DB.load_world、R.load_bars、patterns.Frame.gate、
industry PIT、營收面板、research13.and_flags）：
 E1 指數：pandas 讀 git show 同一 sha；r ＝ pct_change；q(t) ＝ np.quantile(2005-01-03～t−1 的 r, 0.02)（每天重算、不用插入排序）；
    去重 ＝ 逐日回看 20 列；鎖 ＝ while 迴圈；收復 ＝ 逐日往後找
 E2 逐股：每個接受事件 p，逐股用 for 迴圈走 K 棒：母體、當天報酬、可買、主出場（壞根先、收復後第一根可賣開盤、下市／窗尾）
    C／D 用 sorted、E 用 dict 聚合產業、F 用自算 5 取 3（pandas rolling）＋and_flags；A／B 直接讀 ETF 日線
 E3 對 v1 的 event_rows.csv（q2 × 主出場）：選出檔數、買到檔數、淨報酬、配對 0050；對 events.csv：日期、跌幅、門檻、判定、收復日、持有中又遇事件次數
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO); os.chdir(REPO)
V1 = os.path.join(REPO, "backtest/resultsMktDrop/v1")
TOL = 1e-9
_G: dict = {}


def chk(name, ok, info=""):
    print(("✔ " if ok else "✘ ") + name + (f"｜{info}" if info else ""), flush=True)
    _G.setdefault("fail", []).append(name) if not ok else None
    return ok


# ═════ E1 指數 ═════
def index_check(sha):
    raw = subprocess.run(["git", "show", f"{sha}:data/history/market_index.csv"], capture_output=True, check=True).stdout
    df = pd.read_csv(io.BytesIO(raw), dtype={"date": str})
    df["date"] = pd.to_datetime(df["date"]); df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    r = df["close"].pct_change().to_numpy()
    dates = df["date"].to_numpy(); cl = df["close"].to_numpy(float); n = len(df)
    w0 = int(np.searchsorted(dates, np.datetime64("2005-01-03")))
    q = np.full(n, np.nan)
    for t in range(w0, n):
        win = r[w0:t]; win = win[~np.isnan(win)]
        if len(win) >= 250:
            q[t] = np.quantile(win, 0.02)
    raw_ev = np.zeros(n, bool)
    for t in range(n):
        if not np.isnan(q[t]) and r[t] <= q[t]:
            raw_ev[t] = True
    first = [t for t in range(n) if raw_ev[t] and not raw_ev[max(0, t - 20):t].any()]
    rec = {}
    for t in first:
        d = -1
        for j in range(t + 1, n):
            if cl[j] >= cl[t - 1]:
                d = j; break
        rec[t] = d
    acc = []; blocked = {}
    i = 0; until = -1; cur = None
    while i < len(first):
        t = first[i]
        if t <= until:
            blocked[t] = cur
        else:
            acc.append(t); cur = t; until = rec[t] if rec[t] >= 0 else n + 1
        i += 1
    E = pd.read_csv(os.path.join(V1, "events.csv"))
    E = E[E["定義"] == "q2"].reset_index(drop=True)
    mine = pd.DataFrame({"日期": [str(pd.Timestamp(dates[t]).date()) for t in first], "r": [r[t] for t in first], "q": [q[t] for t in first],
                         "接受": [t in acc for t in first], "收復日": [str(pd.Timestamp(dates[rec[t]]).date()) if rec[t] >= 0 else None for t in first],
                         "擋": [sum(1 for v in blocked.values() if v == t) if t in acc else None for t in first]})
    ok = len(mine) == len(E) and (mine["日期"].tolist() == E["日期"].tolist())
    chk("E1 事件日（去重）清單相同", ok, f"本檢查 {len(mine)}／v1 {len(E)}")
    if ok:
        chk("E1 跌幅 ≤1e−9", float(np.max(np.abs(mine["r"] - E["指數報酬"]))) <= TOL)
        chk("E1 門檻 ≤1e−9", float(np.max(np.abs(mine["q"] - E["門檻"]))) <= TOL, f"最大差 {float(np.max(np.abs(mine['q'] - E['門檻']))):.2e}")
        chk("E1 接受／持有中又遇事件 相同", (mine["接受"] == (E["判定"] == "接受")).all())
        chk("E1 收復日相同", (mine["收復日"].fillna("") == E["收復日"].fillna("")).all())
        a_ = mine[mine["接受"]]; b_ = E[E["判定"] == "接受"]
        chk("E1 持有中又遇事件次數相同", (a_["擋"].to_numpy(float) == b_["持有中又遇事件次數"].to_numpy(float)).all())
    return df, dates, cl, acc, rec


# ═════ E2 逐股 ═════
def stock_events(args):
    wn, sid = args
    from backtest import data as D, research11 as R, patterns as P
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = np.asarray(B["idx"], np.int64); nb = len(idx)
    o = np.asarray(B["o"], float); c = np.asarray(B["c"], float); nbad_arr = np.asarray(B["next_bad"])
    gate = np.asarray(P.Frame(B["df"], set()).gate, bool)
    bad = [bool(nbad_arr[k] == k) for k in range(nb)]
    for pz in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, pz))
        if k < nb:
            bad[k] = True
    pos2k = {int(p): k for k, p in enumerate(idx)}
    out = {}
    for p, Dp in W["EVP"]:
        k = pos2k.get(p)
        if k is None:
            continue
        mem = bool(gate[idx[k]] and W["PV"][i, p] and k >= 20 and not any(bad[k - 20:k + 1]))
        ret = c[k] / c[k - 1] - 1.0 if k >= 1 else np.nan
        buy = (k + 1 < nb and idx[k + 1] == p + 1 and W["TRD"][i, p + 1] and np.isfinite(W["O"][i, p + 1]) and W["O"][i, p + 1] > 0
               and not W["UPL"][i, p + 1] and not bad[k + 1])
        sale = None
        if k + 1 < nb:
            for j in range(k + 2, nb):
                if bad[j]:
                    sale = (int(idx[j - 1]), float(c[j - 1]), 1); break
                q_ = idx[j]
                if q_ > Dp and W["TRD"][i, q_] and np.isfinite(W["O"][i, q_]) and W["O"][i, q_] > 0 and not W["DNL"][i, q_]:
                    sale = (int(q_), float(o[j]), 0); break
            if sale is None:
                sale = (n0 - 1, float(c[-1]), 3) if idx[-1] == n0 - 1 else (int(idx[-1]), float(c[-1]), 2)
        out[p] = {"mem": mem, "ret": ret, "buy": bool(buy), "bp": float(o[k + 1]) if k + 1 < nb else np.nan, "sale": sale}
    # F：自算 5 取 3（pandas rolling）
    s_c = pd.Series(c); s_amt = pd.Series(np.asarray(B["amt"], float)); up = pd.Series(np.asarray(B["up"], bool).astype(float))
    ret20 = (s_c / s_c.shift(20) - 1).to_numpy().copy()
    nup = up.rolling(20).sum().to_numpy()
    amtp = s_amt.shift(1).rolling(20).mean().to_numpy().copy(); amtp[:21] = np.nan
    ar = s_amt.to_numpy() / amtp
    ma100 = s_c.rolling(100).mean().to_numpy(); hi250 = s_c.rolling(250).max().to_numpy()
    skip = np.asarray(B["skip"], bool)
    picks = []; last = -10 ** 9
    for k in range(nb):
        if k < 249 or skip[k] or np.isnan(ma100[k]) or np.isnan(ar[k]) or not (nbad_arr[max(0, k - 20)] > k):
            continue
        sc = int(ret20[k] >= 0.30) + int(nup[k] >= 3) + int(ar[k] >= 3.0) + int(c[k] > ma100[k]) + int(c[k] >= hi250[k])
        if sc >= 3 and k - last > 20:
            picks.append((int(k), int(idx[k]))); last = k
    evset = {p for p, _ in W["EVP"]}
    return sid, {"ev": out, "picks": [x for x in picks if x[1] in evset]}


def etf_event(W, df, p, Dp, n0):
    tr = df["traded"].to_numpy(bool); o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    if not (p + 1 < n0 and tr[p] and tr[p + 1] and np.isfinite(o[p + 1]) and o[p + 1] > 0):
        return None
    bars = np.flatnonzero(tr)
    for q_ in bars[bars > p + 1]:
        if q_ > Dp and np.isfinite(o[q_]) and o[q_] > 0:
            return o[p + 1], (int(q_), float(o[q_]), 0)
    return o[p + 1], ((n0 - 1, float(c[bars[-1]]), 3) if bars[-1] == n0 - 1 else (int(bars[-1]), float(c[bars[-1]]), 2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); a = ap.parse_args()
    S = json.load(open(os.path.join(V1, "MktDrop_v1.json"), encoding="utf-8"))
    sha = S["指數"]["origin/main sha"]
    df, dates, cl, acc, rec = index_check(sha)
    from backtest import researchDumb as DB, data as D, research13 as R13, universe_gate as UG
    from backtest import researchIndRev_prereg as PRE
    UG.set_gate_v2(True)
    DB.SEGS = {"早年": {"2006～2014": ("2006-01-01", "2014-12-31")}, "主": {"2015～2021": ("2015-01-01", "2021-12-31"), "2022～": ("2022-01-01", None)}}
    IND_DATA = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
    PIT = PRE.PIT(IND_DATA, PRE.load_rev(IND_DATA)[2])
    PANEL = {"主": "backtest/resultsN17/sig_edc6f/panel_rev.csv.gz", "早年": os.path.expanduser("~/earlydata/eotc_f65bb03e11/sig_otc/panel_rev.csv.gz")}
    ER = pd.read_csv(os.path.join(V1, "event_rows.csv"), dtype={"日期": str})
    ER = ER[(ER["定義"] == "q2") & (ER["出場"] == "主")]
    worst = 0.0; ncmp = 0; mism = []
    for wn in ("早年", "主"):
        W = DB.load_world(wn, lambda m: None); _G[wn] = W
        cal = W["cal"]; n0 = W["n0"]
        lo, hi = W["segp"][list(W["segp"])[0]][0], W["segp"][list(W["segp"])[-1]][1]
        EVP = []
        for t in acc:
            d = pd.Timestamp(dates[t])
            if d not in set(cal):
                continue
            p = int(cal.get_loc(d))
            if not (lo <= p <= hi and p + 1 < n0):
                continue
            Dp = int(cal.searchsorted(pd.Timestamp(dates[rec[t]]))) if rec[t] >= 0 else 10 ** 9
            EVP.append((p, Dp))
        W["EVP"] = EVP
        with Pool(a.procs) as pool:
            RES = dict(pool.imap_unordered(stock_event_wrap, [(wn, s) for s in W["sids"]], chunksize=8))
        RES = {k: v for k, v in RES.items() if v is not None}
        D.DATA = W["data"]
        etf = {s: D.load_stock(s, "twse", cal) for s in ("0050", "00631L")}
        BC = pd.Series(etf["0050"].df["close"].to_numpy(float)).ffill().to_numpy()
        BOr = etf["0050"].df["open"].to_numpy(float)
        BO = np.array([BOr[j] if np.isfinite(BOr[j]) and BOr[j] > 0 else (BC[j - 1] if j else np.nan) for j in range(n0)])
        pn = pd.read_csv(PANEL[wn], dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "signal_date", "rev_hi24"])
        cp = {str(d.date()): j for j, d in enumerate(cal)}
        pn["signal_pos"] = pn["signal_date"].map(cp); pn = pn.dropna(subset=["signal_pos"]); pn["signal_pos"] = pn["signal_pos"].astype(int)
        pn["rev_hi24"] = pn["rev_hi24"].fillna(False).astype(bool)
        Sx = pd.DataFrame([(s, k, pz) for s, v in RES.items() for k, pz in v["picks"]], columns=["sid", "k", "pos"])
        fl = R13.and_flags(Sx, pn)[0] if len(Sx) else np.zeros(0, bool)
        ACH = set(zip(Sx["sid"][fl], Sx["pos"][fl])) if len(Sx) else set()
        for p, Dp in EVP:
            day = str(cal[p].date())
            pop = [(s, v["ev"][p]["ret"]) for s, v in RES.items() if p in v["ev"] and v["ev"][p]["mem"] and np.isfinite(v["ev"][p]["ret"])]
            baskets = {}
            for cd in ("A", "B"):
                if cd == "B" and wn == "早年":
                    continue
                r_ = etf_event(W, etf["0050" if cd == "A" else "00631L"].df, p, Dp, n0)
                baskets[cd] = ([] if r_ is None else [("ETF", r_[0], r_[1])], 1 if r_ else 0, 0.00385)
            if len(pop) >= 20:
                srt = sorted(pop, key=lambda z: z[1]); m_ = int(np.ceil(len(pop) * 0.1))
                # 同值時 v1 用 argsort(stable) 依股票代號序；這裡同樣先依代號排序再 sorted（stable）
                srt = sorted(sorted(pop, key=lambda z: z[0]), key=lambda z: z[1])
                selC = [s for s, _ in srt[:m_]]
                srtD = sorted(sorted(pop, key=lambda z: z[0]), key=lambda z: z[1])[::-1]
                selD = [s for s, _ in srtD[:m_]]
                grp = {}
                for s, rv in pop:
                    ind = PIT._at(s, cal[p], "pit")[0]
                    if ind is None or ind in ("其他", "存託憑證", "ETF"):
                        continue
                    grp.setdefault(ind, []).append((s, rv))
                gm = sorted([(np.mean([x[1] for x in v]), g) for g, v in grp.items() if len(v) >= 5])
                selE = [s for _, g in gm[:2] for s, _ in grp[g]] if len(gm) >= 2 else []
            else:
                selC = selD = selE = []
            selF = [s for s in RES if (s, p) in ACH]
            for cd, sel in (("C", selC), ("D", selD), ("E", selE), ("F", selF)):
                rows = [(s, RES[s]["ev"][p]["bp"], RES[s]["ev"][p]["sale"]) for s in sel if RES[s]["ev"][p]["buy"]]
                baskets[cd] = (rows, len(sel), 0.00585)
            for cd, (rows, nsel, cost) in baskets.items():
                v1 = ER[(ER["世界"] == wn) & (ER["日期"] == day) & (ER["候選"] == cd)]
                if len(v1) != 1:
                    mism.append((wn, day, cd, "v1 列數", len(v1))); continue
                v1 = v1.iloc[0]
                if int(v1["選出檔數"]) != nsel or int(v1["買到檔數"]) != len(rows):
                    mism.append((wn, day, cd, "檔數", (nsel, len(rows)), (int(v1["選出檔數"]), int(v1["買到檔數"])))); continue
                if not rows:
                    continue
                g = np.mean([sx / bp - 1 for _, bp, (sp, sx, kd) in rows]); net = (1 + g) * (1 - cost) - 1
                b = np.mean([(BO[sp] if kd == 0 else BC[sp]) / BO[p + 1] - 1 for _, bp, (sp, sx, kd) in rows]); b50 = (1 + b) * (1 - 0.00385) - 1
                d1 = abs(net - v1["報酬"]); d2 = abs(b50 - v1["配對0050"])
                worst = max(worst, d1, d2); ncmp += 1
                if d1 > TOL or d2 > TOL:
                    mism.append((wn, day, cd, "報酬", net, float(v1["報酬"]), b50, float(v1["配對0050"])))
        print(f"[{wn}] 事件 {len(EVP)}｜股 {len(RES)}", flush=True)
    chk("E2 主出場：選出／買到檔數、淨報酬、配對 0050 全對（≤1e−9）", not mism, f"比對 {ncmp} 格、最大差 {worst:.2e}" + (f"｜不符 {mism[:8]}" if mism else ""))
    print("全部通過" if not _G.get("fail") else f"⛔ 未通過：{_G['fail']}")


def stock_event_wrap(a):
    return stock_events(a)


if __name__ == "__main__":
    main()

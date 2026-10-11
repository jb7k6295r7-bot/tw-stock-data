# -*- coding: utf-8 -*-
"""急跌延伸四件 —— 抽樣獨立查核（回測線計算子代理）。
⭐ 獨立寫法：⛔ 不 import researchCrashExt、researchCrashOversold（主程式）、researchRevLimitUp、researchIndRev_prereg、research34；
   價格、K 棒、壞根用急跌錯殺 seq1 的獨立查核程式 researchCrashOversold_check.load_layout（它自己讀 csv 算還原價、壞根，並已對 research11.load_bars 查過）；
   月營收用同檔 ind_tools（自己讀 csv）；法人、融資、重大訊息、成交量自己讀 csv。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchCrashExt_check --case rev [--n 120] [--days 6] [--procs 4]

查（逐件）：
 ① 全部急跌事件的進場條件與進場日：rev（V1、V2、D）、stop（S1、S2）、inst（I1、I2、D）⇒ 對 entries.csv.gz；
    margin：比重、降幅（entries 存 8 位有效數字 ⇒ 相對 1e-7）、以及每個事件日自己重建 R1（20 日均成交金額排名前 X%、有 K 棒、pit_valid、非金融；
    X 取主程式值，X 本身已由急跌錯殺 check ② 查過）算的比重中位、降幅前 10%、M1 ⇒ 對 entries
 ② 全部「條件成立」事件的進場檢查（資料尾、(t,e] 壞根、公司事件 [t−10, e−1]、已修復、e 開盤）⇒ 對 entries.csv.gz 的 _hyg
 ③ margin 抽 days 個事件日列出 ① 的當日門檻明細
 ④ 從 exits.csv.gz（主程式 `exits` 子命令用它的 exits_x 對每筆可進場列寫出）抽 n 列：自己重算 X1（修復／進場當天或之後才可用的月營收年增 ≤ 0）、
    X2（回落 20%）的出場種類、位置、原因（含壞根前收盤強制出）⇒ 對主程式
輸出 backtest/resultsCrashExt/<件名>/check.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchCrashOversold_check as COC     # noqa: E402  （獨立查核程式，非主程式）

UG.set_gate_v2(True)
H2D = COC.H2D; EOTC = COC.EOTC
TW = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
EXT = os.path.expanduser("~/crashextwork/tw_283eec12b2bc/data")
ROOT = os.path.expanduser("~/tw-p17/backtest/resultsCrashExt")
NAME = {"rev": "急跌後等營收證實", "stop": "急跌後等止跌", "inst": "急跌中有人逆勢買", "margin": "融資大減型錯殺"}
TYPES = {"rev": ["V1", "V2", "Dv"], "stop": ["S1", "S2"], "inst": ["I1", "I2", "Di"], "margin": ["M1", "Dm"]}
KW = COC.KW
BUY_IN = ["董事會決議買回庫藏股", "決議買回本公司股份"]
BUY_EX = ["轉讓", "註銷", "執行情形", "期間屆滿"]


def same(a, b):
    a = float(a) if a is not None else np.nan; b = float(b) if b is not None else np.nan
    return (np.isnan(a) and np.isnan(b)) or a == b


def evpos(cal, df):
    n = len(cal); calv = cal.values
    dt = pd.to_datetime(df["date"]).values
    p0 = np.searchsorted(calv, dt, side="left")
    istd = (p0 < n) & (calv[np.minimum(p0, n - 1)] == dt)
    late = df["time"].str.slice(0, 5).to_numpy() > "13:30"
    return np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))


def close8(x, y):
    """entries.csv.gz 以 8 位有效數字存 ⇒ 相對 1e-7。"""
    if not (np.isfinite(x) and np.isfinite(y)):
        return bool(np.isnan(x) and np.isnan(y))
    return abs(x - y) <= 1e-7 * max(abs(x), abs(y), 1e-300)


def margin_days(Lm, days, X, ind_at):
    """③ 自己重建每個事件日的 R1（20 日均成交金額前 X%、有 K 棒、pit_valid、非金融），算融資比重中位、降幅前 10%。
    ⇒ {t: (中位, (None, 前10%代號集合, 降幅可算代號集合), 門檻, 比重母體數, 降幅母體數)}"""
    cal, ST = Lm[0], Lm[1]; n = len(cal); sids = sorted(ST); S_ = len(sids)
    MB = np.full((S_, n), np.nan); V20 = np.full((S_, n), np.nan)
    for i, s in enumerate(sids):
        p = os.path.join(EXT, "stocks_margin", f"{s}.csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype=str).drop_duplicates("date", keep="last")
            ix = cal.get_indexer(pd.to_datetime(x["date"])); ok = ix >= 0
            MB[i, ix[ok]] = pd.to_numeric(x["m_balance"], errors="coerce").to_numpy(float)[ok]
        q = pd.read_csv(os.path.join(H2D, "stocks", f"{s}.csv"), dtype=str).drop_duplicates("date")
        ix = cal.get_indexer(pd.to_datetime(q["date"])); vv = pd.to_numeric(q["volume"], errors="coerce").to_numpy(float) / 1000
        m = ix >= 0; ix, vv = ix[m], vv[m]
        ok = ST[s]["bar"][ix] & np.isfinite(vv); ix, vv = ix[ok], vv[ok]
        if len(vv) >= 20:
            cs = np.cumsum(np.r_[0.0, vv]); V20[i, ix[19:]] = (cs[20:] - cs[:-20]) / 20
    A20 = np.vstack([ST[s]["a20"] for s in sids]); BAR = np.vstack([ST[s]["bar"] for s in sids]); PV = np.vstack([ST[s]["pv"] for s in sids])
    finc = {}
    out = {}
    for d in days:
        mf = COC.month_first(cal, d)
        if mf not in finc:
            finc[mf] = np.array([ind_at(s, mf) == "金融保險" for s in sids])
        base = np.flatnonzero(BAR[:, d] & PV[:, d] & np.isfinite(A20[:, d]) & ~finc[mf])
        o = sorted(base.tolist(), key=lambda i: (-A20[i, d], i))
        U = np.array(sorted(o[:int(np.ceil(X * len(o)))]), int)
        with np.errstate(invalid="ignore", divide="ignore"):
            ra = np.where(np.isfinite(V20[U, d - 10]) & (V20[U, d - 10] > 0), MB[U, d - 10] / V20[U, d - 10], np.nan)
            dc = np.where((MB[U, d - 10] > 0) & np.isfinite(MB[U, d]), (MB[U, d - 10] - MB[U, d]) / MB[U, d - 10], np.nan)
        okr = np.isfinite(ra); med = float(np.median(ra[okr])) if okr.any() else np.nan
        okd = np.flatnonzero(np.isfinite(dc)); k = int(np.ceil(0.10 * len(okd)))
        oo = okd[np.argsort(-dc[okd], kind="stable")]
        top = {sids[U[j]] for j in oo[:k]}; alld = {sids[U[j]] for j in okd}
        out[d] = (med, (None, top, alld), float(dc[oo[k - 1]]) if k else np.nan, int(okr.sum()), int(len(okd)))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--case", required=True); ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--days", type=int, default=6); ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    t0 = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    for ck in a.case.split(","):
        check(ck, a, t0)


def check(ck, a, t0):
    OUT = os.path.join(ROOT, NAME[ck])
    EN = pd.read_csv(os.path.join(OUT, "entries.csv.gz"), dtype={"sid": str}, low_memory=False)
    EX = pd.read_csv(os.path.join(OUT, "exits.csv.gz"), dtype={"sid": str}, low_memory=False)
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    rng = np.random.default_rng(20261012)
    res = {"執行時間": t0 + "（台北）", "件": NAME[ck], "寫法": "獨立（見檔頭）"}
    total = 0
    ind_at, REV, periods, mshift = COC.ind_tools(TW)

    def yoy(s, M):
        v = REV.get((s, M))
        if v is None or not (np.isfinite(v[0]) and np.isfinite(v[1]) and v[1] > 0):
            return np.nan
        return v[0] / v[1] - 1

    NWf = sorted(f for f in glob.glob(os.path.join(TW, "mops", "news", "*.csv")) if os.path.basename(f)[:4].isdigit() and int(os.path.basename(f)[:4]) >= 2004)
    NW = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in NWf], ignore_index=True).drop_duplicates(["date", "time", "stock_id", "serial"])
    NW["stock_id"] = NW["stock_id"].str.strip()
    NK = NW[[any(k in s for k in KW) for s in NW["subject"]]]
    NB = NW[[any(k in s for k in BUY_IN) and not any(k in s for k in BUY_EX) for s in NW["subject"]]]
    parts = ["main", "early"] if ck in ("rev", "stop", "inst") else ["main"]
    L = {}
    for part in parts:
        cal, ST = COC.load_layout(H2D if part == "main" else EOTC, a.procs)
        n = len(cal)
        av = []
        for M in periods:
            y, m = int(M[:4]), int(M[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            j = int(cal.searchsorted(pd.Timestamp(y2, m2, 10 if M <= "2025-12" else 15), side="right"))
            if 0 < j < n:
                av.append((j, M))
        NPk = {}
        for s, p in zip(NK["stock_id"], evpos(cal, NK)):
            NPk.setdefault(s, []).append(int(p))
        NPb = {}
        for s, p in sorted(zip(NB["stock_id"], evpos(cal, NB)), key=lambda z: z[1]):
            if p < n:
                NPb.setdefault(s, []).append(int(p))
        L[part] = (cal, ST, av, NPk, NPb)
    # ── ① 進場條件 ──
    out1 = {}
    for part in parts:
        cal, ST, av, NPk, NPb = L[part]; n = len(cal)
        avP = np.array([x[0] for x in av]); avM = [x[1] for x in av]
        E = EN[EN["版面"] == part].reset_index(drop=True)
        mine = {ty: [] for ty in TYPES[ck]}
        if ck == "margin":
            MBc, VLc = {}, {}
        for s, t in zip(E["sid"], E["t"].astype(int)):
            v = ST[s]; c = v["c"]; bar = v["bar"]
            if ck == "rev":
                kk = int(np.searchsorted(avP, t, side="right"))
                if kk >= len(avP):
                    for ty in ("V1", "V2", "Dv"):
                        mine[ty].append((np.nan, -1))
                    continue
                tr, M = int(avP[kk]), avM[kk]
                r0 = REV.get((s, M), (np.nan, np.nan))[0]
                pr = [REV.get((s, mshift(M, -k)), (np.nan, np.nan))[0] for k in range(1, 13)]
                full = np.isfinite(r0) and all(np.isfinite(x) for x in pr)
                y, yp = yoy(s, M), yoy(s, mshift(M, -1))
                v1 = float(r0 > max(pr)) if full else np.nan
                v2 = 0.0 if (np.isfinite(y) and y <= 0) else (float(y > 0 and y - yp >= 0) if (np.isfinite(y) and np.isfinite(yp)) else np.nan)
                dv = 1.0 if ((full and r0 < min(pr)) or (np.isfinite(y) and y <= 0)) else (0.0 if (full and np.isfinite(y)) else np.nan)
                far = tr - t > 30
                for ty, cv in (("V1", v1), ("V2", v2), ("Dv", dv)):
                    mine[ty].append((cv, tr if (cv == 1.0 and not far) else -1))
            elif ck == "stop":
                k1 = next((k for k in range(t + 1, min(t + 20, n - 1) + 1) if bar[k] and c[k] > np.mean(c[k - 19:k + 1])), None)
                k2 = None
                for k in range(t + 5, min(t + 20, n - 1) + 1):
                    if bar[k] and min(c[k - 4:k + 1]) >= min(c[t:k - 4]):
                        k2 = k; break
                tr_ = t + 20 > n - 1
                for ty, k in (("S1", k1), ("S2", k2)):
                    mine[ty].append((1.0, k + 1) if k is not None else ((np.nan if tr_ else 0.0), -1))
            elif ck == "inst":
                if part == "main":
                    p = os.path.join(EXT, "stocks_inst", f"{s}.csv")
                    x = pd.read_csv(p, dtype=str) if os.path.exists(p) else None
                    ds = set(str(d.date()) for d in cal[t - 9:t + 1])
                    if x is not None:
                        x = x.drop_duplicates("date", keep="last"); x = x[x["date"].isin(ds)]
                    sm = float((pd.to_numeric(x["foreign"], errors="coerce").fillna(0) + pd.to_numeric(x["trust"], errors="coerce").fillna(0)).sum()) if (x is not None and len(x)) else np.nan
                else:
                    sm = np.nan
                i1 = np.nan if not np.isfinite(sm) else float(sm > 0); di = np.nan if not np.isfinite(sm) else float(sm < 0)
                mine["I1"].append((i1, t + 1 if i1 == 1.0 else -1)); mine["Di"].append((di, t + 1 if di == 1.0 else -1))
                hit = [p for p in NPb.get(s, []) if t - 9 <= p <= t + 20]
                mine["I2"].append((1.0, max(hit[0] + 1, t + 1)) if hit else ((np.nan if t + 20 > n - 1 else 0.0), -1))
            elif ck == "margin":
                if s not in MBc:
                    p = os.path.join(EXT, "stocks_margin", f"{s}.csv")
                    mb = np.full(n, np.nan)
                    if os.path.exists(p):
                        x = pd.read_csv(p, dtype=str).drop_duplicates("date", keep="last")
                        ix = cal.get_indexer(pd.to_datetime(x["date"])); ok = ix >= 0
                        mb[ix[ok]] = pd.to_numeric(x["m_balance"], errors="coerce").to_numpy(float)[ok]
                    q = pd.read_csv(os.path.join(H2D, "stocks", f"{s}.csv"), dtype=str).drop_duplicates("date")
                    ix = cal.get_indexer(pd.to_datetime(q["date"])); ok = ix >= 0
                    vol = np.full(n, np.nan); vol[ix[ok]] = pd.to_numeric(q["volume"], errors="coerce").to_numpy(float)[ok] / 1000
                    MBc[s] = mb; VLc[s] = vol
                mb, vol = MBc[s], VLc[s]
                bi = [k for k in range(t - 10, -1, -1) if bar[k] and np.isfinite(vol[k])][:20]
                v20 = float(np.mean(vol[bi])) if len(bi) == 20 and (t - 10) in bi else np.nan
                ra = mb[t - 10] / v20 if (np.isfinite(v20) and v20 > 0) else np.nan
                dc = (mb[t - 10] - mb[t]) / mb[t - 10] if (mb[t - 10] > 0 and np.isfinite(mb[t])) else np.nan
                mine.setdefault("_比重", []).append(ra); mine.setdefault("_降幅", []).append(dc)
        nd = {}
        for ty in TYPES[ck]:
            if ck == "margin":
                break
            cv = [z[0] for z in mine[ty]]; ee = [z[1] for z in mine[ty]]
            dcond = sum(not same(x, y) for x, y in zip(cv, E[f"{ty}_cond"]))
            de = sum(int(x) != int(y) for x, y in zip(ee, E[f"{ty}_e"]))
            nd[ty] = {"條件不同": int(dcond), "進場日不同": int(de), "成立": int(sum(x == 1.0 for x in cv))}
            total += dcond + de
        if ck == "margin":
            rr = np.array(mine["_比重"], float); dd = np.array(mine["_降幅"], float)
            d_r = int(sum(not close8(x, y) for x, y in zip(rr, E["比重"].astype(float))))
            d_d = int(sum(not close8(x, y) for x, y in zip(dd, E["降幅"].astype(float))))
            DAY = margin_days(L["main"], sorted(set(E["t"].astype(int))), S["meta"]["R1"]["X"], ind_at)
            res["_DAY"] = DAY
            m1 = []
            for s, t, x in zip(E["sid"], E["t"].astype(int), rr):
                med, top, *_ = DAY[t]
                m1.append(float(x >= med and s in top[1]) if (np.isfinite(x) and np.isfinite(med) and s in top[2]) else np.nan)
            d_m = int(sum(not same(x, y) for x, y in zip(m1, E["M1_cond"])))
            d_t = int(sum(not (close8(DAY[t][0], md) and close8(DAY[t][2], th) and DAY[t][3] == int(nr) and DAY[t][4] == int(nd_))
                          for t, md, th, nr, nd_ in zip(E["t"].astype(int), E["比重中位"].astype(float), E["降幅前10%門檻"].astype(float), E["比重母體"], E["降幅母體"])
                          if np.isfinite(md)))
            nd = {"比重不同（8 位有效數字）": d_r, "降幅不同（8 位有效數字）": d_d, "自建 R1 的 M1 不同": d_m, "自建 R1 的當日中位／門檻／母體數不同（事件列）": d_t,
                  "M1 成立": int(sum(x == 1.0 for x in m1)), "事件日數": len(DAY)}
            total += d_r + d_d + d_m + d_t
        out1[part] = {"事件": int(len(E)), **nd}
        L[part] = L[part] + (avP, avM)
    res["① 進場條件（全部事件）"] = out1
    # ── ② 進場檢查 ──
    out2 = {}
    for part in parts:
        cal, ST, av, NPk, NPb, avP, avM = L[part]; n = len(cal)
        E = EN[EN["版面"] == part]
        d2 = 0; m2 = 0
        for ty in TYPES[ck]:
            G = E[E[f"{ty}_e"] >= 0]
            for s, t, e, h in zip(G["sid"], G["t"].astype(int), G[f"{ty}_e"].astype(int), G[f"{ty}_hyg"]):
                v = ST[s]
                if e >= n:
                    me = "超出資料尾"
                elif v["BAD"][t + 1:e + 1].any():
                    me = "(t,e] 有壞根"
                elif any(t - 10 <= p <= e - 1 for p in NPk.get(s, [])):
                    me = "公司事件"
                elif v["c"][e - 1] >= v["c"][t - 10] * (1 - 1e-12):
                    me = "進場前已修復"
                elif not np.isfinite(v["o"][e]):
                    me = "e 無有效開盤"
                else:
                    me = ""
                h = "" if (isinstance(h, float) and np.isnan(h)) else str(h)
                m2 += 1; d2 += int(me != h)
        out2[part] = {"查筆": m2, "不同": d2}
        total += d2
    res["② 進場檢查（條件成立全部）"] = out2
    # ── ③ margin：自己重建 R1 算當日門檻 ──
    if ck == "margin":
        cal = L["main"][0]; DAY = res.pop("_DAY")
        E = EN[(EN["版面"] == "main") & np.isfinite(EN["比重中位"].astype(float))]
        days = sorted(rng.choice(sorted(set(E["t"].astype(int))), size=min(a.days, E["t"].nunique()), replace=False).tolist())
        out3 = []
        for d in days:
            g = E[E["t"].astype(int) == d].iloc[0]
            out3.append({"日": str(cal[d].date()), "比重母體": DAY[d][3], "主程式": int(g["比重母體"]), "中位": DAY[d][0], "主程式中位": float(g["比重中位"]),
                         "降幅母體": DAY[d][4], "主程式降幅母體": int(g["降幅母體"]), "門檻": DAY[d][2], "主程式門檻": float(g["降幅前10%門檻"])})
        res["③ 自建 R1 的當日門檻（抽樣日明細；不同已計入 ①）"] = out3
    # ── ④ 出場抽樣 ──
    out4 = []; nd4 = 0; k4 = 0
    EXs = EX.iloc[sorted(rng.choice(len(EX), size=min(a.n, len(EX)), replace=False))]
    for r in EXs.itertuples(index=False):
        part = r.版面
        cal, ST, av, NPk, NPb, avP, avM = L[part]; n = len(cal)
        s, t, e = r.sid, int(r.t), int(r.e); v = ST[s]
        c, bar, BAD = v["c"], v["bar"], v["BAD"]
        okb = np.flatnonzero(bar & np.isfinite(v["o"]))
        ref = c[t - 10]
        rep = next((k for k in range(e, n) if bar[k] and c[k] >= ref * (1 - 1e-12)), None)
        rv_ = next((int(p_) for p_, M in zip(avP, avM) if p_ >= e and np.isfinite(yoy(s, M)) and yoy(s, M) <= 0), None)
        mx = -np.inf; dd_ = None
        for k in range(e, n):
            mx = max(mx, c[k])
            if c[k] <= mx * 0.8 + 1e-12:
                dd_ = k; break
        kb = next((k for k in range(e + 1, n) if BAD[k]), None)
        for x, trig in (("X1", [(rep, "修復"), (rv_, "轉壞（營收）")]), ("X2", [(dd_, "回落20%")])):
            tr = [z for z in trig if z[0] is not None]
            k_t, why = min(tr, key=lambda z: z[0]) if tr else (None, None)
            sell = None
            if k_t is not None and k_t + 1 < n:
                q = okb[okb >= k_t + 1]; sell = int(q[0]) if len(q) else None
            if kb is not None and (sell is None or kb <= sell):
                y = max(k for k in range(e, kb) if bar[k]); me = ("close", y, "壞根前收盤強制出")
            elif k_t is not None and k_t + 1 < n:
                me = ("open", k_t + 1, why)
            else:
                me = ("open", -1, "未完")
            th = (getattr(r, f"{x}_xk"), int(getattr(r, f"{x}_x")), getattr(r, f"{x}_why"))
            k4 += 1
            if me != th:
                nd4 += 1; out4.append({"版面": part, "sid": s, "t": str(cal[t].date()), "e": str(cal[e].date()), "出場": x, "獨立": list(me), "主程式": list(th)})
    res["④ 出場抽樣"] = {"抽列": int(len(EXs)), "比對（列×出場）": k4, "不同": nd4, "不同明細": out4[:20]}
    total += nd4
    res["總不同"] = int(total)
    res["摘要"] = {"①": {p: {k: v for k, v in d.items() if "不同" in k or isinstance(v, dict)} for p, d in out1.items()}, "②": out2, "④不同": nd4}
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:5000])


if __name__ == "__main__":
    main()

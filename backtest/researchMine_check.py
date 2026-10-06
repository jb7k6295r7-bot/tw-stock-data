# -*- coding: utf-8 -*-
"""PREREG地雷股濾網 seq3 抽樣查核（researchMine --check）。⛔ 不呼叫本體的旗、報酬、分類、彙總函式；從原始 CSV 用另一套寫法自算，再跟本體輸出比。

  ① 旗：主快照 400 股-月（母體內 300＋全體 100）、早年 150 股-月 ⇒ F1～F5、G1～G3、母體 EL 逐項比
     還原價自算：data/adj 的 cum_factor（第一個事件日 ＞ d 那列；另一套寫法，不經 data.load_stock）；有任一價格 ≤ 0 的列整列作廢；只留交易日曆內的日子
  ② 乙：6 個判定日 × 4 個 H 的整個橫斷面 R、基準② 逐格比；再用本體存的 R／BASE ＋ 旗，以另一套彙總重算 4 格 yi.csv 的 X 平均與 CI
  ③ 甲：delist.csv 全部列的「財務性_主／並報」逐列比；再重算 2 格 jia.csv 的精準度
  ④ 丙：600 個事件的旗逐項比；重算「探索＋確認」G1、G3 的網格中位與登錄主格
  容差：布林逐一相同；浮點相對 1e-9
"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np
import pandas as pd

MAIN = os.path.expanduser("~/h2data/mine_796d94c9dafd/data")
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
PANEL = os.path.expanduser("~/tw-p17/backtest/resultsp9_engine/panel_ext.csv.gz")
EARLY_PANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
WORK = os.path.expanduser("~/minework")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsMine")
S5W = os.path.expanduser("~/s5work")
RS = np.random.default_rng(20261007)
_cache: dict = {}


def cal_of(data):
    return pd.to_datetime(pd.read_csv(os.path.join(data, "meta", "calendar_twse.csv"))["date"]).sort_values().reset_index(drop=True)


def px(data, sid, cal):
    """回 DataFrame(index＝cal)：adj_close、adj_open、raw_close（NaN＝無效）。"""
    k = (data, sid)
    if k in _cache:
        return _cache[k]
    f = os.path.join(data, "stocks", f"{sid}.csv")
    if not os.path.exists(f):
        _cache[k] = None; return None
    r = pd.read_csv(f, dtype=str)
    r = r.drop_duplicates("date", keep="first")
    r["date"] = pd.to_datetime(r["date"])
    for c in ("open", "high", "low", "close"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    bad = (r[["open", "high", "low", "close"]] <= 0).any(axis=1)
    r.loc[bad, ["open", "high", "low", "close"]] = np.nan
    r = r.set_index("date").sort_index()
    fac = np.ones(len(r))
    af = os.path.join(data, "adj", f"{sid}.csv")
    if os.path.exists(af):
        a = pd.read_csv(af, dtype={"date": str}); a["date"] = pd.to_datetime(a["date"]); a = a.sort_values("date")
        ev = a["date"].to_numpy(); cf = a["cum_factor"].to_numpy(float)
        # 日子 d 的因子 ＝ 第一個事件日 ＞ d 那列的 cum_factor（＝ 之後所有事件的連乘，資料庫給的 8 位小數版；
        #   ⚠ 自己用 factor 欄連乘會因每個因子各自四捨五入到 8 位而差 1e-7 相對 ⇒ 用資料庫的 cum_factor 欄）
        pos = np.searchsorted(ev, r.index.to_numpy(), side="right")
        fac = np.where(pos < len(ev), cf[np.minimum(pos, len(ev) - 1)], 1.0)
    out = pd.DataFrame({"adj_close": r["close"].to_numpy() * fac, "adj_open": r["open"].to_numpy() * fac, "raw_close": r["close"].to_numpy()}, index=r.index)
    out = out.reindex(pd.DatetimeIndex(cal))
    _cache[k] = out
    return out


def par_of(sid, date):
    P = _cache.setdefault("par", pd.read_csv(os.path.join(MAIN, "meta", "par_timeline.csv"), dtype=str))
    x = P[P["stock_id"] == sid]
    for vf, vt, p in zip(x["valid_from"], x["valid_to"], x["par"]):
        if (not isinstance(vf, str) or pd.Timestamp(vf) <= date) and (not isinstance(vt, str) or date < pd.Timestamp(vt)):
            if isinstance(p, str) and p.strip():
                return float(p)
    return 10.0


def fin_tables():
    if "fin" in _cache:
        return _cache["fin"]
    fd = pd.read_csv(os.path.join(MAIN, "meta", "filing_dates.csv"), dtype=str)
    fd["dt"] = pd.to_datetime(fd["uploaded_at"].str.slice(0, 10), errors="coerce")
    fdm = {}
    for s, y, q, dt in zip(fd["stock_id"], fd["year"], fd["season"], fd["dt"]):
        if pd.notna(dt):
            kk = (s, int(y), int(q))
            fdm[kk] = min(fdm.get(kk, dt), dt)
    bs = {}                                                                  # 同檔同期重複 ⇒ 檔名排序後者覆蓋
    for f in sorted(glob.glob(os.path.join(MAIN, "mops", "bs_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str)
        for s, per, v in zip(x["stock_id"], x["period"], x["每股參考淨值"]):
            try:
                bs.setdefault(s, {})[per] = float(v)
            except (TypeError, ValueError):
                bs.setdefault(s, {})[per] = np.nan
    eps = {}
    for f in sorted(glob.glob(os.path.join(MAIN, "mops", "fin_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str)
        for s, per, q_, y_ in zip(x["stock_id"], x["period"], x["eps_q"], x["eps_ytd"]):
            eps.setdefault(s, {})[per] = (pd.to_numeric(q_, errors="coerce"), pd.to_numeric(y_, errors="coerce"))
    _cache["fin"] = (fdm, bs, eps)
    return _cache["fin"]


def avail_day(fdm, cal, s, per):
    y, q = int(per[:4]), int(per[-1])
    if (s, y, q) in fdm:
        dt = fdm[(s, y, q)]
        k = int(np.searchsorted(cal.to_numpy(), np.datetime64(dt), side="right"))
    else:
        dl = {1: f"{y}-05-15", 2: f"{y}-08-14", 3: f"{y}-11-14", 4: f"{y + 1}-03-31"}[q]
        k = int(np.searchsorted(cal.to_numpy(), np.datetime64(dl), side="right")) + 5
    return k


def per_sub(per, n):
    y, q = int(per[:4]), int(per[-1])
    t = y * 4 + q - 1 - n
    return f"{t // 4}Q{t % 4 + 1}"


def my_flags(data, cal, sid, mpos, early):
    d = px(data, sid, cal)
    out = {}
    m = cal[mpos]
    if d is None:
        return None
    c = d["adj_close"].to_numpy()[: mpos + 1]
    vb = np.flatnonzero(np.isfinite(c))
    if len(vb) >= 251:
        now, old = c[vb[-1]], c[vb[-251]]; ma = c[vb[-250:]].mean()
        out["F1_50"] = bool(now <= old * 0.5 and now < ma); out["F1_70"] = bool(now <= old * 0.3 and now < ma)
    else:
        out["F1_50"] = out["F1_70"] = False
    par = par_of(sid, m)
    if len(vb):
        rc = d["raw_close"].to_numpy()[vb[-1]]
        out["F2_1"] = bool(rc < par); out["F2_05"] = bool(rc < par * 0.5)
    else:
        out["F2_1"] = out["F2_05"] = False
    if early:
        for k in ("F3_half", "F3_neg", "F4a", "F4b", "F5a", "F5b"):
            out[k] = False
    else:
        fdm, bs, eps = fin_tables()
        av = [(per, avail_day(fdm, cal, sid, per)) for per in bs.get(sid, {})]
        av = [p for p, k in av if k <= mpos]
        out["F3_half"] = out["F3_neg"] = False
        if av:
            lp = max(av, key=lambda p: (int(p[:4]), int(p[-1])))
            v = bs[sid][lp]
            if np.isfinite(v):
                out["F3_half"] = bool(v < par / 2); out["F3_neg"] = bool(v < 0)
        E = eps.get(sid, {})
        av = [per for per in E if avail_day(fdm, cal, sid, per) <= mpos]
        out["F4a"] = out["F4b"] = False
        if av:
            lp = max(av, key=lambda p: (int(p[:4]), int(p[-1])))

            def single(per):
                if per not in E:
                    return np.nan
                q_, y_ = E[per]
                if per.endswith("Q1"):
                    v = y_
                else:
                    pv = E.get(per_sub(per, 1), (np.nan, np.nan))[1]
                    v = y_ - pv
                if not np.isfinite(v):
                    v = q_
                return v
            e = [single(per_sub(lp, i)) for i in range(8)]
            if all(np.isfinite(e[:4])):
                out["F4a"] = bool(sum(e[:4]) < 0 and e[0] < 0)
            if all(np.isfinite(e)):
                out["F4b"] = bool(sum(1 for v in e if v < 0) >= 6)
        # F5：判定日前一個交易日那份快照（檔名）
        prev = None
        for k in range(mpos - 1, -1, -1):
            ds = cal[k].strftime("%Y-%m-%d")
            if os.path.exists(os.path.join(MAIN, "universe", "fulldelivery", ds + ".csv")):
                prev = ds; break
        a_ = b_ = False
        if prev:
            x = pd.read_csv(os.path.join(MAIN, "universe", "fulldelivery", prev + ".csv"), dtype=str); a_ |= sid in set(x["stock_id"].str.strip())
            x = pd.read_csv(os.path.join(MAIN, "universe", "chtm", prev + ".csv"), dtype=str)
            x = x[(x["changed"] == "1") | (x["managed"] == "1")]; a_ |= sid in set(x["stock_id"].str.strip())
            x = pd.read_csv(os.path.join(MAIN, "universe", "marginratio", prev + ".csv"), dtype=str)
            x = x[x["reason"].isin(["股價波動過度劇烈", "成交量過度異常", "股權過度集中", "監視第二次處置"])]; b_ |= sid in set(x["stock_id"].str.strip())
            x = pd.read_csv(os.path.join(MAIN, "universe", "otcmargin", prev + ".csv"), dtype=str)
            x = x[x["note"].fillna("").str.contains("[ABCD]", regex=True)]; b_ |= sid in set(x["stock_id"].str.strip())
        out["F5a"], out["F5b"] = bool(a_), bool(b_)
    out["F4"] = out["F4a"] or out["F4b"]; out["F5"] = out["F5a"] or out["F5b"]
    n = sum([out["F1_50"], out["F2_1"], out["F3_half"], out["F4"], out["F5"]])
    out["G1"] = n >= 1; out["G2"] = n >= 2; out["G3"] = out["F3_half"] or out["F5"]; out["G3n"] = out["F3_neg"] or out["F5"]
    return out


def my_pit(data, sid, date):
    f = os.path.join(data, "stocks", f"{sid}.csv")
    r = pd.read_csv(f, dtype=str, usecols=lambda c: c in ("date", "name", "market"))
    r = r.drop_duplicates("date", keep="last"); r = r[pd.to_datetime(r["date"]) <= date]
    if not len(r):
        return True
    last = r.sort_values("date").iloc[-1]
    return bool(last["market"] in ("twse", "tpex") and not re.search(r"-(?:KY)?創", str(last["name"])))


def elig_sets():
    if "el" in _cache:
        return _cache["el"]
    p = pd.read_csv(PANEL, dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "eligible"])
    a = set(zip(p.loc[p["eligible"].astype(bool), "stock_id"], p.loc[p["eligible"].astype(bool), "measure_date"].str[:7]))
    e = pd.read_csv(EARLY_PANEL, dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "liq_ok", "bars_ok"])
    mm = e["liq_ok"].astype(bool) & e["bars_ok"].astype(bool)
    b = set(zip(e.loc[mm, "stock_id"], e.loc[mm, "measure_date"].str[:7]))
    _cache["el"] = (a, b)
    return a, b


def check_flags(res):
    bad = []; n = 0
    for tag, data, early, nsamp_el, nsamp_all in (("main", MAIN, False, 300, 100), ("early", EARLY, True, 120, 30)):
        z = np.load(os.path.join(WORK, f"flags_{tag}.npz"))
        cal = cal_of(data); me = pd.DatetimeIndex(z["me"]); sids = z["sids"]; EL = z["EL"]
        mpos = np.searchsorted(cal.to_numpy(), me.to_numpy())
        ii, jj = np.nonzero(EL)
        pick = RS.choice(len(ii), nsamp_el, replace=False)
        smp = [(ii[p], jj[p]) for p in pick] + [(RS.integers(len(me)), RS.integers(len(sids))) for _ in range(nsamp_all)]
        # 加幾個帶旗的（確保旗為真的情形也被查到）
        for f in ("G3", "F4", "F1_50", "F2_1") if not early else ("F1_50", "F2_1"):
            a_, b_ = np.nonzero(z[f] & EL)
            if len(a_):
                for p in RS.choice(len(a_), min(25, len(a_)), replace=False):
                    smp.append((a_[p], b_[p]))
        ela, ele = elig_sets()
        for i, j in smp:
            sid = str(sids[j]); m = me[i]
            mf = my_flags(data, cal, sid, int(mpos[i]), early)
            if mf is None:
                continue
            n += 1
            for k, v in mf.items():
                if bool(z[k][i, j]) != v:
                    bad.append({"世界": tag, "sid": sid, "m": str(m.date()), "旗": k, "本體": bool(z[k][i, j]), "查核": v})
            myel = ((sid, str(m)[:7]) in (ele if early else ela)) and my_pit(data, sid, m)
            if bool(EL[i, j]) != myel:
                bad.append({"世界": tag, "sid": sid, "m": str(m.date()), "旗": "EL", "本體": bool(EL[i, j]), "查核": myel})
    res["① 旗"] = {"股-月": n, "不同": len(bad), "例": bad[:10]}


def check_yi(res):
    bad = 0; cnt = 0; ex = []
    for tag, data in (("main", MAIN), ("early", EARLY)):
        z = np.load(os.path.join(WORK, f"flags_{tag}.npz"))
        cal = cal_of(data); me = pd.DatetimeIndex(z["me"]); sids = [str(s) for s in z["sids"]]; EL = z["EL"]
        mpos = np.searchsorted(cal.to_numpy(), me.to_numpy())
        rows = RS.choice(np.arange(24, len(me) - 13), 3, replace=False)
        for H in (20, 60, 120, 250):
            y = np.load(os.path.join(WORK, f"yi_{tag}_H{H}.npz")); R0, B0 = y["R"], y["BASE"]
            for i in rows:
                m = int(mpos[i])
                if m + H >= len(cal):
                    continue
                Rm = np.full(len(sids), np.nan); r20 = np.full(len(sids), np.nan)
                for j in np.flatnonzero(EL[i]):
                    d = px(data, sids[j], cal)
                    if d is None:
                        continue
                    cf = d["adj_close"].ffill().to_numpy(); o = d["adj_open"].to_numpy()
                    if np.isfinite(o[m + 1]) and o[m + 1] > 0:
                        Rm[j] = cf[m + H] / o[m + 1] - 1
                    if m >= 20:
                        r20[j] = cf[m] / cf[m - 20] - 1
                ok = EL[i] & np.isfinite(Rm) & np.isfinite(r20)
                idx = np.flatnonzero(ok)
                order = sorted(idx, key=lambda j: (r20[j], j))          # 同值依欄序（＝ rank method first）
                N = len(order); base = np.full(len(sids), np.nan)
                grp = {}
                for rnk, j in enumerate(order):
                    q = min(9, sum(1 for t in range(1, 10) if 10 * rnk > t * (N - 1)))
                    grp.setdefault(q, []).append(j)
                for q, js in grp.items():
                    mu = np.mean([Rm[j] for j in js])
                    for j in js:
                        base[j] = mu
                for j in idx:
                    cnt += 1
                    for a_, b_ in ((Rm[j], R0[i, j]), (base[j], B0[i, j])):
                        if not (np.isfinite(b_) and abs(a_ - b_) <= 1e-9 * max(1, abs(a_))):
                            bad += 1
                            if len(ex) < 5:
                                ex.append({"世界": tag, "H": H, "m": str(me[i].date()), "sid": sids[j], "查核": float(a_), "本體": float(b_)})
    res["② 乙 R／基準② 橫斷面"] = {"格": cnt, "不同": bad, "例": ex}
    # 彙總重算
    Y = pd.read_csv(os.path.join(OUT, "yi.csv"))
    z = np.load(os.path.join(WORK, "flags_main.npz")); cal = cal_of(MAIN); me = pd.DatetimeIndex(z["me"]); EL = z["EL"]
    mpos = np.searchsorted(cal.to_numpy(), me.to_numpy())
    agg = []
    for seg, a_, b_, f, H in (("確認", "2022-01", "2026-08", "G3", 20), ("探索", "2017-03", "2021-12", "G1", 60), ("確認", "2022-01", "2026-08", "G2", 120), ("探索", "2017-03", "2021-12", "G3", 250)):
        y = np.load(os.path.join(WORK, f"yi_main_H{H}.npz")); X = y["R"] - y["BASE"]
        last = int(np.flatnonzero(cal.dt.strftime("%Y-%m").to_numpy() <= b_)[-1])
        xs = []; gs = []
        for i in range(len(me)):
            mo = str(me[i])[:7]
            if not (a_ <= mo <= b_) or mpos[i] + H > last:
                continue
            for j in np.flatnonzero(EL[i] & z[f][i] & np.isfinite(X[i])):
                xs.append(X[i, j]); gs.append(i)
        xs = np.array(xs); gs = np.array(gs); mu = xs.mean()
        S = np.array([(xs[gs == g] - mu).sum() for g in np.unique(gs)]); G = len(S)
        se = np.sqrt(G / (G - 1) * (S ** 2).sum()) / len(xs)
        r = Y[(Y["段"] == seg) & (Y["旗"] == f) & (Y["H"] == H)].iloc[0]
        d = max(abs(mu - r["X 平均"]), abs(mu + 1.96 * se - r["hi"])); agg.append({"段": seg, "旗": f, "H": H, "事件 查核／本體": [len(xs), int(r["事件"])], "最大差": float(d)})
    res["② 乙 彙總重算"] = {"格": agg, "不同": sum(1 for x in agg if x["最大差"] > 1e-9 or x["事件 查核／本體"][0] != x["事件 查核／本體"][1])}


def check_jia(res):
    T = pd.read_csv(os.path.join(OUT, "delist.csv"), dtype={"sid": str})
    rs = pd.read_csv(os.path.join(MAIN, "meta", "otc_delist_reason", "otc_delist_reason.csv"), dtype=str)
    lab = {(s.strip(), d): l for s, d, l in zip(rs["stock_id"], rs["delist_date"], rs["reason_label"])}
    calm, cale = cal_of(MAIN), cal_of(EARLY)
    fdm, bs, _ = fin_tables()
    disp = pd.read_csv(os.path.join(MAIN, "meta", "disposal.csv"), dtype=str); disp = disp[disp["sec_kind"] == "普通股"]
    bad = []
    T = T[T["在名冊"]]                                                   # 名冊外（DR、早年上櫃）不進任何結果 ⇒ 不查
    for r in T.itertuples():
        Dt = pd.Timestamp(r.delist_date); early = Dt <= pd.Timestamp("2014-12-31")
        cal, data = (cale, EARLY) if early else (calm, MAIN)
        L = lab.get((r.sid, r.delist_date)) if r.market == "tpex" else None
        off = "非地雷" if L in ("被合併", "金控", "轉上市") else ("財務性" if L in ("拒絕往來", "管理股票") else "代理")
        pD = int(np.searchsorted(cal.to_numpy(), np.datetime64(Dt), side="left"))
        d = px(data, r.sid, cal)
        drop = np.nan
        if d is not None:
            c = d["adj_close"].to_numpy()[:pD]; vb = np.flatnonzero(np.isfinite(c))
            if len(vb) > 60:
                drop = c[vb[-1]] / c[vb[-61]] - 1
        bvn = np.nan
        if not early and r.sid in bs:
            av = [p for p in bs[r.sid] if avail_day(fdm, cal, r.sid, p) <= pD]
            if av:
                bvn = bs[r.sid][max(av, key=lambda p: (int(p[:4]), int(p[-1])))]
        mp = (np.isfinite(drop) and drop < -0.5) or (np.isfinite(bvn) and bvn < 0)
        db = False
        if not early:
            for k in range(max(pD - 250, 0), min(pD, len(cal))):
                ds = cal[k].strftime("%Y-%m-%d")
                if not os.path.exists(os.path.join(MAIN, "universe", "fulldelivery", ds + ".csv")):
                    continue
                key = ("snap", ds)
                if key not in _cache:
                    st = set()
                    x = pd.read_csv(os.path.join(MAIN, "universe", "fulldelivery", ds + ".csv"), dtype=str); st |= set(x["stock_id"].str.strip())
                    x = pd.read_csv(os.path.join(MAIN, "universe", "chtm", ds + ".csv"), dtype=str); st |= set(x.loc[(x["changed"] == "1") | (x["managed"] == "1"), "stock_id"].str.strip())
                    x = pd.read_csv(os.path.join(MAIN, "universe", "marginratio", ds + ".csv"), dtype=str)
                    st |= set(x.loc[x["reason"].isin(["股價波動過度劇烈", "成交量過度異常", "股權過度集中", "監視第二次處置"]), "stock_id"].str.strip())
                    x = pd.read_csv(os.path.join(MAIN, "universe", "otcmargin", ds + ".csv"), dtype=str)
                    st |= set(x.loc[x["note"].fillna("").str.contains("[ABCD]", regex=True), "stock_id"].str.strip())
                    _cache[key] = st
                if r.sid in _cache[key]:
                    db = True; break
        lo = cal[max(pD - 250, 0)]; hi = cal[min(pD, len(cal) - 1)]
        x = disp[disp["stock_id"].str.strip() == r.sid]
        for a_, b_ in zip(pd.to_datetime(x["start_date"]), pd.to_datetime(x["end_date"])):
            if a_ <= hi and b_ >= lo and a_ < Dt:
                db = True
        fm = off == "財務性" or (off == "代理" and mp); fb = off == "財務性" or (off == "代理" and db)
        if fm != bool(r.財務性_主) or fb != bool(r.財務性_並報):
            bad.append({"sid": r.sid, "下市日": r.delist_date, "主 本體／查核": [bool(r.財務性_主), fm], "並報 本體／查核": [bool(r.財務性_並報), fb]})
    res["③ 甲 下市分類（全部列）"] = {"列": int(len(T)), "不同": len(bad), "例": bad[:10]}
    # 精準度重算
    J = pd.read_csv(os.path.join(OUT, "jia.csv"))
    z = np.load(os.path.join(WORK, "flags_main.npz")); me = pd.DatetimeIndex(z["me"]); sids = [str(s) for s in z["sids"]]; EL = z["EL"]
    fin = T[T["財務性_主"]]
    out = []
    for seg, a_, b_, f, k in (("確認", "2022-01", "2026-08", "G3", 12), ("探索", "2017-03", "2021-12", "G1", 36)):
        n1 = y1 = 0
        for i in range(len(me)):
            mo = str(me[i])[:7]
            if not (a_ <= mo <= b_) or me[i] + pd.DateOffset(months=k) > calm.iloc[-1]:
                continue
            end = me[i] + pd.DateOffset(months=k)
            for j in np.flatnonzero(EL[i] & z[f][i]):
                n1 += 1
                y1 += int(((fin["sid"] == sids[j]) & (pd.to_datetime(fin["delist_date"]) > me[i]) & (pd.to_datetime(fin["delist_date"]) <= end)).any())
        r = J[(J["段"] == seg) & (J["代理"] == "主") & (J["k月"] == k) & (J["旗"] == f)].iloc[0]
        out.append({"段": seg, "旗": f, "k": k, "查核 帶旗／下市": [n1, y1], "本體": [int(r["帶旗股-月"]), int(r["帶旗下市"])]})
    res["③ 甲 精準度重算"] = {"格": out, "不同": sum(1 for x in out if x["查核 帶旗／下市"] != x["本體"])}


def check_bing(res):
    E = np.load(os.path.join(WORK, "bing_events.npz"))
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)["stock_id"].to_numpy()
    c1 = pd.read_csv(os.path.join(EARLY, "meta", "calendar_twse.csv"))["date"].tolist(); c2 = pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"].tolist()
    cal5 = pd.to_datetime(pd.Series(c1 + [x for x in c2 if x <= "2026-09-24"]))
    zm = np.load(os.path.join(WORK, "flags_main.npz")); ze = np.load(os.path.join(WORK, "flags_early.npz"))
    mm = pd.to_datetime(pd.Series(zm["me"])); mE = pd.to_datetime(pd.Series(ze["me"]))
    sm = {s: j for j, s in enumerate(zm["sids"])}; se = {s: j for j, s in enumerate(ze["sids"])}
    bad = []; n = 0
    pick = RS.choice(len(E["d"]), 600, replace=False)
    for p in pick:
        t = cal5[int(E["d"][p])]; sid = uni[int(E["s"][p])]
        prevE = mE[mE < t]; prevM = mm[mm < t]
        if len(prevM):
            z, i, j = zm, int(prevM.index[-1]), sm.get(sid)
        elif len(prevE):
            z, i, j = ze, int(prevE.index[-1]), se.get(sid)
        else:
            z, i, j = None, None, None
        known = j is not None and z is not None
        if bool(E["known"][p]) != known:
            bad.append({"事件": int(p), "項": "known", "本體": bool(E["known"][p]), "查核": known}); continue
        if not known:
            continue
        n += 1
        for f in ("G1", "G2", "G3", "F1_50", "F2_1", "F3_half", "F4", "F5"):
            if bool(E[f][p]) != bool(z[f][i, j]):
                bad.append({"事件": int(p), "項": f, "本體": bool(E[f][p]), "查核": bool(z[f][i, j])})
        if bool(E["elig"][p]) != bool(z["EL"][i, j]):
            bad.append({"事件": int(p), "項": "EL", "本體": bool(E["elig"][p]), "查核": bool(z["EL"][i, j])})
    res["④ 丙 事件旗"] = {"事件": n, "不同": len(bad), "例": bad[:10]}
    # 網格中位重算（探索＋確認、全部）
    BG = pd.read_csv(os.path.join(OUT, "bing_grid.csv"))
    mon = cal5.dt.strftime("%Y-%m").to_numpy()[E["d"]]
    seg = (mon >= "2017-03") & (mon <= "2026-08") & E["known"]
    out = []
    for f in ("G1", "G3"):
        rates = []; main = None
        for c in range(250):
            q = seg & (E["cell"] == c)
            if q.sum() >= 1:
                rates.append(E[f][q].mean())
            if c == 11 * 10 + 1:                                     # H120（第 12 個 H）× g100%（第 2 個 g）
                main = E[f][q].mean()
        r = BG[(BG["段"] == "探索＋確認") & (BG["版本"] == "全部") & (BG["旗"] == f)].iloc[0]
        out.append({"旗": f, "查核 網格中位／主格": [float(np.median(rates)), float(main)], "本體": [float(r["網格中位"]), float(r["登錄主格 H120 g100%"])]})
    res["④ 丙 網格中位重算"] = {"格": out, "不同": sum(1 for x in out if max(abs(a - b) for a, b in zip(x["查核 網格中位／主格"], x["本體"])) > 1e-12)}


def main():
    res = {"時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "種子": 20261007}
    for fn in (check_flags, check_yi, check_jia, check_bing):
        fn(res)
        k = list(res)[-1]; print(k, json.dumps({kk: vv for kk, vv in res[k].items() if kk != "例"}, ensure_ascii=False, default=str), flush=True)
    tot = sum(v.get("不同", 0) for k, v in res.items() if isinstance(v, dict))
    res["合計不同"] = tot; res["過"] = tot == 0
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不同", tot)


if __name__ == "__main__":
    main()

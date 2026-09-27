# -*- coding: utf-8 -*-
"""PREREG訊號系統均線 seq1（台股策略線登錄 sha 39c29b1596b81dba；裁定 seq252 發號、N_組合 ＋2）。
E1 築底起漲／E2 底部反轉進（＝ PREREG訊號系統 原樣）、收盤「跌破」10／20／60 日線 ⇒ 次日開盤賣；可再進場。回測線，2026-09-27。
⚠ 聲明：看過前一版結果才加測（登錄 §聲明）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSigMA.py pre|body|early|report [--procs 2] [--reps 200] [--fake 1000]

═══ 沿用（⭐ import researchSig，⛔ 不改它）═══
  進場列、同日出場不進、再進場、引擎（營飆 v1 骨架、200 顆、種子 1000＋r）、彙總、挑法 ＝ researchSig（2fe5809e9b）原樣；訊號快取 ＝ resultsSig/sig_cache.pkl
  面板 ＝ panel_ext；早年 ＝ researchSig 的做法（個股 2012-06～2016 只上市、受個股法人資料限制；0050 層 2004 起全段），只描述
═══ 出場（登錄 §一、§二；裁定 seq252 補定接受）═══
  均線 ＝ 有效 K 棒還原收盤簡單平均（researchRev.ma_fsum：math.fsum÷N、含當根）；N ∈ {10, 20, 60}
  主版「跌破」＝ 由上往下穿越：前一根有效 K 棒 收盤 ≥ MA 且 當根 收盤 ＜ MA；只看持有期間（穿越日 d ≥ 進場日 e）⇒ d＋1 開盤賣
  並列描述「收盤 ＜ MA 即賣」版（⛔ 不判、不計 N）：d ＝ 持有期間第一個 收盤 ＜ MA 的日子；⚠ 讀法：這一版的「出場訊號」是狀態、不是事件
     ⇒ 不套「同日有出場訊號就不進」（否則進場日在均線下的訊號全數不進，與登錄 §二「很多筆會在進場隔天就被賣掉」的構造描述相反）
═══ 事前排除退化格（登錄 §三；seq246）═══
  探索段每格：「每檔平均出場觸發次數／年」＝ 每顆被均線賣出的筆數 ÷ 10 檔 ÷ 段長（年），200 顆平均；「段尾未出場比例」＝ Σ段尾未出場 ÷ Σ部位（200 顆合併）
  觸發 ＜ 1 次／年 或 段尾未出場 ＞ 50% ⇒ 不進挑選、只描述；該族 3 格全退化 ⇒ 該族「依構造不可判定」
輸出 backtest/resultsSigMA/
"""
from __future__ import annotations
import argparse, hashlib, json, os, pickle, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchSig as RS

RV, D, RR, R11, L = RS.RV, RS.D, RS.RR, RS.R11, RS.L
HERE = RS.HERE
OUT = os.path.join(HERE, "resultsSigMA")
NS = (10, 20, 60)
MAIN_X = [f"MA{n}" for n in NS]
STATE_X = [f"MAs{n}" for n in NS]
XN = {**{f"MA{n}": f"跌破 {n} 日線（穿越）" for n in NS}, **{f"MAs{n}": f"收盤 ＜ {n} 日線即賣（並列描述）" for n in NS}}
SAY = "看過前一版結果才加測"
_G: dict = {}


# ═════════════════════════════ 均線出場日（每檔）
def ma_days_arr(c):
    valid = np.isfinite(c); b = np.flatnonzero(valid); cb = c[b]; out = {}
    for n in NS:
        ma = RV.ma_fsum(cb, n)
        with np.errstate(invalid="ignore"):
            cross = np.isfinite(ma[1:]) & np.isfinite(ma[:-1]) & (cb[:-1] >= ma[:-1]) & (cb[1:] < ma[1:])
            below = np.isfinite(ma) & (cb < ma)
        out[f"X:MA{n}"] = b[1:][cross].astype(int)
        out[f"X:MAs{n}"] = b[below].astype(int)
    return out


def ma_one(args):
    sid, market = args
    st = D.load_stock(sid, market, _G["cal"])
    if st is None:
        return sid, None
    return sid, ma_days_arr(st.df["close"].to_numpy(float))


def ma_cache(SIG, mk, cal, procs, path, log):
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    t0 = time.time(); M = {}
    with Pool(procs, initializer=_init, initargs=({"cal": cal},)) as pool:
        for sid, d in pool.imap_unordered(ma_one, [(s, mk.get(s, "twse")) for s in SIG], chunksize=8):
            if d is not None:
                M[sid] = d
    pickle.dump(M, open(path, "wb"))
    log(f"[均線出場日] {len(M)} 檔｜{time.time() - t0:.0f}s")
    return M


def _init(d):
    _G.update(d); RS._G.update(d)


def rows_for(SIGM, elig, mon, E, xo, s0, s1):
    """主版 ＝ researchSig.build_rows 原樣（含同日不進）；並列 MAs ＝ 不套同日不進（讀法見檔頭）。"""
    if xo in MAIN_X:
        return RS.build_rows(SIGM, elig, mon, E, xo, s0, s1)
    rows = []; by = {}
    for sid, S in SIGM.items():
        em = elig.get(sid)
        if not em:
            continue
        codes = RS.E1 if E == "E1" else RS.E2
        parts = [(k, S.get("E:" + k, np.zeros(0, int))) for k in codes]
        psets = [(k, set(p_.tolist())) for k, p_ in parts]
        ent = np.unique(np.concatenate([p for _, p in parts]))
        ent = ent[(ent + 1 >= s0) & (ent + 1 <= s1)]
        if not len(ent):
            continue
        ent = ent[np.array([mon[t] in em for t in ent], bool)]
        Xd = S.get("X:" + xo, np.zeros(0, int))
        for t in ent:
            e = int(t) + 1; i = int(np.searchsorted(Xd, e))
            dX = int(Xd[i]) if i < len(Xd) and Xd[i] <= s1 else -1
            srcs = "+".join(k for k, ps in psets if int(t) in ps)
            rows.append((sid, int(t), e, dX, srcs))
    return pd.DataFrame(rows, columns=["sid", "t", "entry_pos", "dX", "src"]), 0, by


# ═════════════════════════════ 引擎一顆（researchSig.summarize ＋ 換手成本、段尾未出場清單）
def run_ma(args):
    key, r, s0, s1 = args
    sig, kw, reason, cf = RS._G["CELLS"][key]
    cz, oz, ncal, cal = RS._G["cz"], RS._G["oz"], RS._G["ncal"], RS._G["cal"]
    au = []
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, audit=au, **kw)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    res = RS.summarize(key, r, au, eq, hv, c_, m_, reason, cf, s0, s1)
    yrs = (cal[s1] - cal[s0]).days / 365.25
    cost = sum(float(a.get("cost", 0.0)) / float(a["equity_prev"]) for a in au if a["side"] == "sell" and s0 <= int(a["t"]) <= s1 and a.get("equity_prev"))
    openb = {}
    for a in au:
        if a["side"] == "buy" and a.get("kind") != "add":
            openb[a["sid"]] = (int(a["t"]), float(a["px"]))
        elif a["side"] == "sell" and a.get("kind") != "trim" and int(a["t"]) <= s1:
            openb.pop(a["sid"], None)
    res["costyr"] = cost / yrs; res["years"] = yrs
    res["endlist"] = [(s, tb, px) for s, (tb, px) in openb.items()]
    res["xtrig"] = int(res["why"].get("X", 0))
    return res


def run_cells(keys, s0, s1, reps, procs, tag, log):
    t0 = time.time(); res = {k: [] for k in keys}
    with Pool(procs) as pool:
        for x in pool.imap_unordered(run_ma, [(k, r, s0, s1) for k in keys for r in range(reps)], chunksize=2):
            res[x["key"]].append(x)
    log(f"  [{tag}] {len(keys)} 格 × {reps} 顆｜{time.time() - t0:.0f}s")
    return res


def agg_ma(rows, bench):
    c = RS.agg(rows, bench)
    trades = sum(x["n"] for x in rows); endo = sum(x["endopen"] for x in rows)
    c["每檔出場觸發_次每年"] = float(np.mean([x["xtrig"] / 10 / x["years"] for x in rows]))
    c["段尾未出場比例"] = endo / max(1, trades)
    c["換手成本_每年"] = float(np.mean([x["costyr"] for x in rows]))
    c["_endlist"] = [e for x in rows for e in x["endlist"]]
    return c


def nostand(endlist, s1, cz, MAc, reps):
    """裁定 seq252：段尾未出場（主版：一直沒『站上再跌破』⇒ 不賣）那批：筆數、段尾未實現報酬分佈、最長持有天數；其中「持有期間從未收在均線上」的子集。"""
    if not endlist:
        return {"筆數每顆": 0.0}
    un = np.array([float(cz[s][s1]) / px - 1.0 for s, tb, px in endlist]); hd = np.array([s1 - tb for s, tb, px in endlist])
    never = []
    for s, tb, px in endlist:
        c, ma = MAc.get(s, (None, None))
        if c is None:
            never.append(False); continue
        seg = slice(tb, s1 + 1)
        with np.errstate(invalid="ignore"):
            never.append(not bool(np.any(np.isfinite(ma[seg]) & (c[seg] >= ma[seg]))))
    nv = np.array(never)
    q = lambda x: {"平均": float(x.mean()), "p10": float(np.percentile(x, 10)), "中位": float(np.median(x)), "p90": float(np.percentile(x, 90)),
                   "最差": float(x.min()), "虧損比例": float((x < 0).mean())}
    return {"筆數每顆": len(endlist) / reps, "段尾未實現報酬": q(un), "最長持有天數": int(hd.max()), "持有天數中位": float(np.median(hd)),
            "其中持有期間從未收在均線上": {"筆數每顆": float(nv.sum()) / reps, **({"段尾未實現報酬": q(un[nv]), "最長持有天數": int(hd[nv].max())} if nv.any() else {})}}


def fake_a(R, hold, s0, s1, n_fake, procs):
    RS._G["FAKEA"] = {"R": R, "hold": hold, "s0": s0, "s1": s1}
    with Pool(procs) as pool:
        return np.array(list(pool.imap_unordered(fake_a_one, range(n_fake), chunksize=4)))


def fake_a_one(i):
    J = RS._G["FAKEA"]; R, s0, s1 = J["R"], J["s0"], J["s1"]
    cz, oz, ncal = RS._G["cz"], RS._G["oz"], RS._G["ncal"]
    rng = np.random.default_rng([20260927, i])
    dA = R["entry_pos"].to_numpy(int) + rng.choice(J["hold"], size=len(R), replace=True) - 1 if len(J["hold"]) else np.full(len(R), 10 ** 9)
    sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": s1 + 1})
    sig["g_X"] = [float(cz[s][s1 + 1]) / L.engine_ep(oz, cz, s, e) - 1.0 for s, e in zip(sig["sid"], sig["entry_pos"])]
    sl = {(s, int(e)): (int(d), np.array([RS.BIG])) for s, e, d in zip(sig["sid"], sig["entry_pos"], dA) if d <= s1}
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + i % 200), cz, oz, ncal, return_equity=True, stop_line=sl)
    return float(RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)[0])


def cell_of(R, s1, cz, oz):
    SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
    return RS.make_cell(R, SD, s1, "無", "無", cz, oz)


def fixed_cell(R, H, s1, cz, oz):
    xp = np.minimum(R["entry_pos"].to_numpy(int) + H - 1, s1 + 1)
    sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": xp})
    sig["g_X"] = [float(cz[s_][x_]) / L.engine_ep(oz, cz, s_, e_) - 1.0 for s_, e_, x_ in zip(sig["sid"], sig["entry_pos"], xp)]
    return sig, {}, {(s_, int(e_)): (f"H{H}", -1) for s_, e_ in zip(sig["sid"], sig["entry_pos"])}


# ═════════════════════════════ 主程式
def setup(a, log, data=None, panel=None, twse_only=False, sig_path=None):
    if data:
        D.DATA = data
    cal = D.load_calendar(); mon = np.array([str(x)[:7] for x in cal])
    sids, elig, mk = RS.stock_universe(cal, panel or RS.PANEL, os.path.join(D.DATA, "meta", "stocks.csv"), twse_only=twse_only)
    SIG, VAL = pickle.load(open(sig_path or os.path.join(RS.OUT, "sig_cache.pkl"), "rb"))
    SIG = {k: v for k, v in SIG.items() if k in set(sids)}
    return cal, mon, elig, mk, SIG, VAL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pre", "body", "early", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=1000)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.mode == "report":
        report(); return
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("researchSigMA.py", "researchSig.py", "researchRev.py", "research11.py")}
    log(f"===== researchSigMA {a.mode} procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{src} =====")
    SP = os.path.join(OUT, "summary.json"); S = json.load(open(SP, encoding="utf-8")) if os.path.exists(SP) else {}
    S.update({"登錄": "PREREG訊號系統均線 seq1 sha 39c29b1596b81dba；裁定 seq252", "聲明": SAY, "程式": src,
              "訊號快取": {"路徑": os.path.join(RS.OUT, "sig_cache.pkl"), "sha256": RS.sha16(os.path.join(RS.OUT, "sig_cache.pkl"))},
              "面板": {"路徑": RS.PANEL, "sha256": RS.sha16(RS.PANEL)}})
    if a.mode == "early":
        early(a, S, log); json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str); report(); return
    RR.use_snapshot()
    cal, mon, elig, mk, SIG, VAL = setup(a, log)
    ncal = len(cal)
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in RS.SEG.items()}
    M = ma_cache(SIG, mk, cal, a.procs, os.path.join(OUT, "ma_cache.pkl"), log)
    SIGM = {sid: {**S_, **M.get(sid, {})} for sid, S_ in SIG.items()}
    if a.mode == "pre":
        pre = []
        for seg, (s0, s1) in P.items():
            for E in ("E1", "E2"):
                for xo in MAIN_X + STATE_X:
                    R, drop, _ = rows_for(SIGM, elig, mon, E, xo, s0, s1)
                    pre.append({"段": seg, "E": E, "出場": xo, "進場列": int(len(R)), "同日有出場而不進": int(drop),
                                "有出場訊號的列": int((R["dX"] >= 0).sum()), "沒有出場訊號（段尾計值）的列": int((R["dX"] < 0).sum()),
                                "沒有出場訊號比例": float((R["dX"] < 0).mean()) if len(R) else np.nan,
                                "進場到出場訊號的天數_中位": float(np.median((R["dX"] - R["entry_pos"])[R["dX"] >= 0])) if (R["dX"] >= 0).any() else np.nan})
        json.dump(pre, open(os.path.join(OUT, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        S["pre完成"] = time.strftime("%F %T"); json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        log(f"[pre] 完成｜{time.time() - t00:.0f}s"); return
    # ═══ body
    cz, oz = RR.load_prices(sorted(SIGM), cal, mk, "branch")
    bench = RR.load_bench(cal); B50 = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    CELLS = {}
    _init({"cal": cal, "cz": cz, "oz": oz, "ncal": ncal, "CELLS": CELLS, "VAL": VAL})
    OUTC = {}; ROWS = {}
    s0, s1 = P["探索"]
    for E in ("E1", "E2"):
        keys = []
        for xo in MAIN_X + STATE_X:
            R, _, _ = rows_for(SIGM, elig, mon, E, xo, s0, s1); R = R.reset_index(drop=True)
            k = ("探索", E, xo); CELLS[k] = (*cell_of(R, s1, cz, oz), None); keys.append(k); ROWS[k] = R
        res = run_cells(keys, s0, s1, a.reps, a.procs, f"探索 {E}", log)
        for k in keys:
            OUTC[k] = agg_ma(res[k], B50["探索"])
    # 事前排除退化格 ⇒ 挑
    excl = {}; chosen = {}
    for E in ("E1", "E2"):
        ok = []
        for xo in MAIN_X:
            c = OUTC[("探索", E, xo)]
            bad = c["每檔出場觸發_次每年"] < 1.0 or c["段尾未出場比例"] > 0.5
            excl[f"{E}_{xo}"] = {"觸發_次每年": c["每檔出場觸發_次每年"], "段尾未出場比例": c["段尾未出場比例"], "排除": bool(bad)}
            if not bad:
                ok.append((xo, c))
        chosen[E] = RS.pick(ok) if ok else None
    S["退化排除"] = excl; S["探索段挑出場"] = chosen
    log(f"[退化排除] {excl}\n[挑出場] {chosen}")
    S["探索段完成"] = time.strftime("%F %T")
    # ═══ 確認段（⛔ 上面挑完才算）
    s0, s1 = P["確認"]; keys = []
    for E in ("E1", "E2"):
        xs = ([chosen[E]] if chosen[E] else []) + STATE_X
        for xo in xs:
            R, _, _ = rows_for(SIGM, elig, mon, E, xo, s0, s1); R = R.reset_index(drop=True)
            k = ("確認", E, xo); CELLS[k] = (*cell_of(R, s1, cz, oz), None); keys.append(k); ROWS[k] = R
    res_c = run_cells(keys, s0, s1, a.reps, a.procs, "確認段", log)
    for k in keys:
        OUTC[k] = agg_ma(res_c[k], B50["確認"])
    # 固定持有對照（兩段）
    for seg in ("探索", "確認"):
        s0_, s1_ = P[seg]; keys = []
        for E in ("E1", "E2"):
            base = chosen[E] or "MA60"
            R = ROWS[(seg, E, base)] if (seg, E, base) in ROWS else rows_for(SIGM, elig, mon, E, base, s0_, s1_)[0].reset_index(drop=True)
            for H in (20, 60, 120):
                k = (seg, E, f"H{H}"); CELLS[k] = (*fixed_cell(R, H, s1_, cz, oz), None); keys.append(k)
        res = run_cells(keys, s0_, s1_, a.reps, a.procs, f"{seg} 固定持有", log)
        for k in keys:
            OUTC[k] = agg_ma(res[k], B50[seg])
    # 一直沒站上就不賣（裁定 seq252）：探索、確認的主版格
    MAc = {}
    need = {e[0] for k, c in OUTC.items() if k[2] in MAIN_X for e in c["_endlist"]}
    for s_ in need:
        st = D.load_stock(s_, mk.get(s_, "twse"), cal); c = st.df["close"].to_numpy(float)
        b = np.flatnonzero(np.isfinite(c))
        for n in NS:
            ma = np.full(ncal, np.nan); ma[b] = RV.ma_fsum(c[b], n); MAc[(s_, n)] = (c, pd.Series(ma).ffill().to_numpy())
    NSB = {}
    for k, c in OUTC.items():
        if k[2] in MAIN_X:
            n = int(k[2][2:]); s1_ = P[k[0]][1]
            NSB["|".join(k)] = nostand(c["_endlist"], s1_, cz, {s_: MAc[(s_, n)] for s_ in {e[0] for e in c["_endlist"]}}, a.reps)
    S["一直沒站上就不賣"] = NSB
    # 假訊號（確認段挑中格）
    FK = {}
    s0, s1 = P["確認"]
    for E in ("E1", "E2"):
        if not chosen[E]:
            continue
        k = ("確認", E, chosen[E]); hold = OUTC[k]["_hold_pool"]
        cA = fake_a(ROWS[k], hold, s0, s1, a.fake, a.procs)
        m = OUTC[k]["cagr_med"]
        FK[E] = {"隨機出場_中位年化": float(np.median(cA)), "本格年化贏過的比例": float((m > cA).mean()), "p（隨機 ≥ 本格）": float((cA >= m).mean()),
                 "次數": a.fake, "持有天數池": int(len(hold))}
        log(f"  [假訊號 {E}] {FK[E]}")
    S["假訊號"] = FK
    # 0050 層（描述）：E1∪E2 進、各均線穿越出
    Mm, Ms, info = RV.market_series()
    Em, _ = RS.l0050_signals(Mm); Es, _ = RS.l0050_signals(Ms)
    L50 = {}
    dS = list(Ms["dates"]); e0, e1 = dS.index(RS.EARLY[0]), dS.index(RS.EARLY[1])
    for n in NS:
        xm = {"MA": ma_days_arr(Mm["c"])[f"X:MA{n}"]}; xs = {"MA": ma_days_arr(Ms["c"])[f"X:MA{n}"]}
        for seg, (s0_, s1_) in P.items():
            L50[f"MA{n}|{seg}"] = RS.l0050_run(Mm, Em, xm, s0_, s1_)
        L50[f"MA{n}|早年"] = RS.l0050_run(Ms, Es, xs, e0, e1)
    S["0050層"] = L50; S["0050同段"] = B50
    rows = [{"段": k[0], "E": k[1], "出場": k[2], **{kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in c.items() if not kk.startswith("_")}}
            for k, c in OUTC.items()]
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "cells.csv"), index=False)
    for E in ("E1", "E2"):
        if chosen[E]:
            k = ("確認", E, chosen[E])
            ROWS[k].to_csv(os.path.join(OUT, f"confirm_rows_{E}.csv.gz"), index=False)
    # 查核用：確認段挑中格前 5 顆 audit
    aud = []
    for E in ("E1", "E2"):
        if not chosen[E]:
            continue
        k = ("確認", E, chosen[E]); sig_, kw_, _, _ = CELLS[k]
        for r in range(5):
            au = []
            o = R11.simulate_mtm(sig_, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, audit=au, **kw_)
            c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
            for x in au:
                aud.append({"cell": "|".join(k), "r": r, **{kk: x.get(kk) for kk in ("t", "sid", "side", "kind", "amt", "px", "cost")}})
            aud.append({"cell": "|".join(k), "r": r, "t": -1, "sid": "_metrics", "side": "", "kind": "", "amt": c_, "px": m_, "cost": np.nan})
    pd.DataFrame(aud).to_csv(os.path.join(OUT, "confirm_audit5.csv.gz"), index=False, float_format="%.17g")
    S["body完成"] = time.strftime("%F %T"); S["秒_body"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[body 完成] {time.time() - t00:.0f}s")
    report()


def early(a, S, log):
    """早年段個股（描述、⛔ 不判；⚠ 受個股法人資料限制）：A 2012-06-01～2014-12-30（early 版面）、B 2015-08-03～2016-12-30（主快照）；只上市；挑中格照跑。"""
    ch = S["探索段挑出場"]; OUTE = {}
    for part, (lo_d, hi_d) in (("A", RS.EARLY_A), ("B", RS.EARLY_B)):
        if part == "A":
            cal, mon, elig, mk, SIG, VAL = setup(a, log, data=RS.EARLY_DATA, panel=RS.EARLY_PANEL, twse_only=True, sig_path=os.path.join(RS.OUT, "sig_cache_earlyA.pkl"))
        else:
            cal, mon, elig, mk, SIG, VAL = setup(a, log, data=RV.H2.H2D, twse_only=True)
        ncal = len(cal)
        s0, s1 = int(cal.searchsorted(pd.Timestamp(lo_d))), int(cal.searchsorted(pd.Timestamp(hi_d)))
        M = ma_cache(SIG, mk, cal, a.procs, os.path.join(OUT, f"ma_cache_early{part}.pkl"), log)
        SIGM = {sid: {**S_, **M.get(sid, {})} for sid, S_ in SIG.items()}
        cz, oz = RR.load_prices(sorted(SIGM), cal, mk, "branch")
        b50 = RR.bench_row(cal, RR.load_bench(cal), s0, s1 + 1)
        CELLS = {}
        _init({"cal": cal, "cz": cz, "oz": oz, "ncal": ncal, "CELLS": CELLS, "VAL": VAL})
        keys = []
        for E in ("E1", "E2"):
            if not ch.get(E):
                continue
            R, _, _ = rows_for(SIGM, elig, mon, E, ch[E], s0, s1); R = R.reset_index(drop=True)
            k = (f"早年{part}", E, ch[E]); CELLS[k] = (*cell_of(R, s1, cz, oz), None); keys.append(k)
        res = run_cells(keys, s0, s1, a.reps, a.procs, f"早年 {part}", log)
        for k in keys:
            OUTE["|".join(k)] = {kk: v for kk, v in agg_ma(res[k], b50).items() if not kk.startswith("_")}
        OUTE[f"早年{part}_0050"] = b50; OUTE[f"早年{part}_窗"] = [lo_d, hi_d]
    D.DATA = RV.H2.H2D
    S["早年個股"] = OUTE
    S["早年個股_註"] = "⚠ 受個股法人資料限制：只跑 2012-06～2016、只上市（A 段 early 版面 3edc0e2206、B 段主快照；2015-01～07 面板無人合格）；描述、⛔ 不判、⛔ 不計 N"


def _p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    ch = S["探索段挑出場"]; B = S["0050同段"]; FK = S.get("假訊號", {}); NSB = S.get("一直沒站上就不賣", {})

    def cell(seg, E, x):
        q = C[(C["段"] == seg) & (C["E"] == E) & (C["出場"] == x)]
        return q.iloc[0] if len(q) else None
    L = ["# PREREG訊號系統均線：築底起漲／底部反轉進、跌破 10／20／60 日線出（可再進場）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq1（sha 39c29b1596b81dba）；裁定 seq252。回測線。⚠ **{SAY}**", ""]
    labs = {E: (cell("確認", E, ch[E])["label"] if ch.get(E) else "依構造不可判定") for E in ("E1", "E2")}
    if all(v == "不合格" or v == "依構造不可判定" for v in labs.values()):
        L.append(f"**結論：訊號進、跌破均線出，沒有贏 0050（確認段 E1 {labs['E1']}、E2 {labs['E2']}）。**")
    else:
        L.append(f"**結論：確認段 E1 {labs['E1']}、E2 {labs['E2']}（使用者判準；{SAY}）。**")
    L += ["", f"確認段 0050：年化 {_p(B['確認']['cagr'])}、回落 {_p(B['確認']['mdd'])}（比值 {B['確認']['cagr'] / abs(B['確認']['mdd']):.3f}）", "",
          "| 族（確認段） | 出場（探索段挑） | 年化中位 | 回落中位 | 比值 | 判定 | vs 固定抱 20／60／120（年化差，點） | 假訊號 p |", "|---|---|---|---|---|---|---|---|"]
    for E in ("E1", "E2"):
        if not ch.get(E):
            L.append(f"| {E} | 三格全退化 | — | — | — | 依構造不可判定 | — | — |"); continue
        q = cell("確認", E, ch[E]); h = {H: cell("確認", E, f"H{H}") for H in (20, 60, 120)}
        dd = "／".join(f"{(q['cagr_med'] - h[H]['cagr_med']) * 100:+.2f}" for H in (20, 60, 120))
        L.append(f"| {E} | {XN[ch[E]]} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.3f} | **{q['label']}** | {dd} | {FK.get(E, {}).get('p（隨機 ≥ 本格）', float('nan')):.3f} |")
    L += ["", "## 結果句（⛔ 照登錄 §三）", ""]
    for E in ("E1", "E2"):
        if not ch.get(E):
            L.append(f"- 〔{E}〕三格全被事前退化排除 ⇒ 依構造不可判定。（{SAY}）"); continue
        q = cell("確認", E, ch[E]); h60 = cell("確認", E, "H60"); p = FK.get(E, {}).get("p（隨機 ≥ 本格）", np.nan)
        pre_ = "隨機出場也做得到：" if np.isfinite(p) and p >= 0.05 else ""
        n = ch[E][2:]
        if q["label"] == "合格":
            s_ = f"{pre_}〔{E}〕進、跌破〔{n}〕日線出，2022～2026 年化 {_p(q['cagr_med'])}／回落 {_p(q['mdd_med'])}，贏 0050（{_p(B['確認']['cagr'])}）且風險調整後不輸"
        elif q["label"] == "另列":
            s_ = f"{pre_}〔{E}〕進、跌破〔{n}〕日線出：報酬贏 0050，但回落比例上不划算（年化 {_p(q['cagr_med'])}／回落 {_p(q['mdd_med'])}）"
        else:
            s_ = f"{pre_}〔{E}〕訊號進、跌破均線出，沒有贏 0050（年化 {_p(q['cagr_med'])}／回落 {_p(q['mdd_med'])}）"
        h = {H: cell("確認", E, f"H{H}") for H in (20, 60, 120)}
        s_ += (f"。用均線出場 vs 固定抱 60 天：年化差 {(q['cagr_med'] - h60['cagr_med']) * 100:+.2f} 點（20 天 {(q['cagr_med'] - h[20]['cagr_med']) * 100:+.2f}、"
               f"120 天 {(q['cagr_med'] - h[120]['cagr_med']) * 100:+.2f}）。{SAY}")
        L.append(f"- {s_}")
    L += ["", "## 事前排除退化格（探索段；觸發 ＜ 1 次／年 或 段尾未出場 ＞ 50% ⇒ 不進挑選）", "", "| 格 | 每檔出場觸發 次／年 | 段尾未出場比例 | 排除 |", "|---|---|---|---|"]
    for k, v in S["退化排除"].items():
        L.append(f"| {k} | {v['觸發_次每年']:.2f} | {v['段尾未出場比例']:.3f} | {'⛔ 排除' if v['排除'] else '—'} |")
    L += ["", "## 各格（200 顆；均線出場主版＋並列「收盤 ＜ MA」版＋固定持有對照）", "",
          "| 段 | E | 出場 | 年化中位 | 回落中位 | 比值 | 判定 | 每顆交易 | 勝率 | 持有 平均／中位（10／90） | 再進場 每顆／平均／勝率 | 段尾未出場 | 持股／現金 | 換手成本／年 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in C.itertuples():
        mark = "⭐ " if r.段 in ("探索", "確認") and ch.get(r.E) == r.出場 else ""
        xn = XN.get(r.出場, f"固定抱 {r.出場[1:]} 天" if r.出場.startswith("H") else r.出場)
        L.append(f"| {r.段} | {r.E} | {mark}{xn} | {_p(r.cagr_med)} | {_p(r.mdd_med)} | {r.ratio:.3f} | {r.label} | {r.交易筆_每顆平均:.1f} | {r.勝率:.3f} | "
                 f"{r.持有天數_平均:.1f}／{r.持有天數_中位:.0f}（{r.持有天數_p10:.0f}／{r.持有天數_p90:.0f}） | {r.再進場_筆數每顆:.1f}／{_p(r.再進場_平均淨報酬)}／{r.再進場_勝率:.3f} | "
                 f"{r.段尾未出場_每顆:.1f} | {r.平均持股檔數:.2f}／{r.現金比例:.3f} | {_p(r.換手成本_每年)} |")
    L += ["", "每年交易次數（每顆平均）見 cells.csv 的「每年交易」欄。", "",
          "## 一直沒站上就不賣的那批（裁定 seq252；主版段尾未出場＝沒有停損）", ""]
    for k, v in NSB.items():
        L.append(f"- {k}：{json.dumps(v, ensure_ascii=False)}")
    L += ["", "## 假訊號（確認段挑中格；同進場＋隨機出場、持有天數抽自本格；1,000 次）", ""] + [f"- {E}：{v}" for E, v in FK.items()]
    L += ["", "## 0050 層（描述；E1∪E2 進、各均線穿越出）", "", "| 均線 | 段 | 年化 | 回落 | 一直抱 年化／回落 | 交易筆 | 持股時間比例 |", "|---|---|---|---|---|---|---|"]
    for k, v in S.get("0050層", {}).items():
        n, seg = k.split("|")
        L.append(f"| {n} | {seg} | {_p(v['cagr'])} | {_p(v['mdd'])} | {_p(v['抱0050_cagr'])}／{_p(v['抱0050_mdd'])} | {v['交易筆']} | {v['持股時間比例']:.3f} |")
    if S.get("早年個股"):
        L += ["", "## 早年段個股（描述、⛔ 不判；⚠ 受個股法人資料限制：只跑 2012-06～2016、只上市）", "", f"{S.get('早年個股_註')}", "",
              "| 格 | 年化中位 | 回落中位 | 比值 | 對 0050（描述） | 0050 同段 |", "|---|---|---|---|---|---|"]
        for k, v in S["早年個股"].items():
            if "|" in k:
                b_ = S["早年個股"][f"{k.split('|')[0]}_0050"]
                L.append(f"| {k} | {_p(v['cagr_med'])} | {_p(v['mdd_med'])} | {v['ratio']:.3f} | {v['label']} | {_p(b_['cagr'])}／{_p(b_['mdd'])} |")
    L += ["", "## 讀法與沿用", "",
          "- 沿用 researchSig（2fe5809e9b）原樣：進場列、同日出場不進、再進場、引擎（營飆 v1 骨架、200 顆取中位、成本 0.585%）、挑法；面板 panel_ext",
          "- 「跌破」＝ 由上往下穿越（前一根有效 K 棒收盤 ≥ MA、當根 ＜ MA；穿越日 ≥ 進場日），裁定 seq252 接受；均線 ＝ researchRev.ma_fsum",
          "- 並列「收盤 ＜ MA 即賣」版：出場訊號是狀態 ⇒ 不套「同日有出場訊號就不進」（讀法，只影響描述格）",
          "- 換手成本／年 ＝ 每筆賣出付的成本 ÷ 前一日淨值，段內加總 ÷ 段長（年），200 顆平均",
          f"- 面板 {S.get('面板')}；訊號快取 {S.get('訊號快取')}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

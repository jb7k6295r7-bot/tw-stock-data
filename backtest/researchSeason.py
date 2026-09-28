# -*- coding: utf-8 -*-
"""PREREG季節性 seq1（台股策略線 登錄 sha 8b763863d5b15258；裁定 seq256 §一 發號、§二 2 年 CI、§二 3 依附本體；seq262 §四 4 照原登錄開跑；N ＋2）。
回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSeason [--procs 2] [--seeds 200] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchSeason_check.py

問：營量 v1、營飆 v1 在年初先不買新股、或把新錢改抱 0050，能不能比照常做多賺或少跌？

═══ 本體（⛔ 一字不改；協調者 09-28：T1 正式版）═══
  營飆 v1 ＝ researchT1fix #1：build_ctx(True)（rerun17.setup_and(t1=True)、1e7229c101）的 sig（t−1 大盤閘）、simulate_mtm H120 N10 default_rng(1000＋r)
  營量 v1 ＝ researchT1fix #13：sig13、simulate_mtm H60 N20 default_rng(7000＋r)、log=[]、d_max=None、pick="relvol"、queue_days=0
  兩者 stop_force ＝ stop_force_days(valid_from_data(全部股票), 主窗尾)；200 顆
  早年段 ＝ researchV.body_setup("main")（早年版面、AND_mtm ＝ T1 讀法、#1 t−1 閘、#13 同參數；Y.run_engine 同式）＋ stop_force（早年版面自算，窗尾 2014-12-31）
═══ 本線讀法（⭐ 看任何季節性數字前寫死）═══
 S1 月份集合 M ∈ {1 月, 1～2 月, 1～3 月}；做法：
    甲 停買：進場日落在 M 的訊號一律不進（空位留現金）；已持有照原規則
    乙 改抱 0050：同甲不進新股；M 期間閒置現金全在 0050（M 第一個交易日開盤買、期間出場的錢當日收盤轉入）；
       M 結束後第一個交易日開盤賣 0050 ⇒ 回原規則。實作 ＝ simulate_mtm cash_mode="bench"、bench_cost＝0，bench 序列：
       M 內逐日 0050 報酬（首日 收盤÷開盤）、M 後首日 開盤÷前收 ×(1 − 0.385%)（0050 來回成本一次扣在賣出日、對當時整筆 0050）、其餘日 ＝ 平（＝ 現金）
    丙 整組換 0050：同乙，且 M 第一個交易日把「進場早於該日、預定出場不早於該日」的部位全部以該日開盤出場（開盤無效 ⇒ 前一日收盤）、付 0.585%；
       M 結束後照原規則重建（新訊號照常進）
 S2 段：探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24（主窗一條權益）｜早年 ＝ 早年版面 2012-06-04～2014-12-31（登錄寫 2012-05～2016；
    早年訊號只到 2014 ⇒ 照 PREREGV 實際窗，照寫）；段內年化／回落 ＝ rerun17.win_metrics
 S3 格：每策略 M 3 × 做法 3 ＝ 9；退化（K7）：探索段 M 內原策略實際新進場（200 顆中位）＜ 20 筆 ⇒ 不進挑選
    挑法：探索段「格年化 − 原策略年化」（同顆配對差的 200 顆中位）最高；同分取比值高
 S4 判定（確認、早年）：多賺 x 點 ＝ 同顆配對年化差中位；回落差同法；
    ⭐ seq256 §二 2：年為單位 ⇒ 該段每個「有 1 月在段內」的曆年，差 ＝ 200 顆平均（格當年報酬 − 原策略當年報酬）；
       bootstrap by year（B＝20,000、default_rng(20260928)）平均差 95% CI：下緣 ＞ 0 ⇒「多賺」、上緣 ＜ 0 ⇒「少賺」、否則「測不出」；
       年初 ＜ 3 個 ⇒ 依構造不可判定；另報每段年初個數與逐年差
    件句：兩段都多賺 ⇒「年初避開有用」｜只一段 ⇒「不穩」｜都沒 ⇒「不必避開」；並報使用者判準（對 0050 同段）
 S5 假訊號（K4）：挑中格同做法、同長度 L，每年隨機一段連續 L 個月（起月 1～13−L 均勻；default_rng([20260928, 策略, k])），1,000 次、
    第 k 次用第 k mod 200 顆；統計量 ＝ 該顆年化 − 同顆原策略年化；p ＝ 隨機 ≥ 挑中格配對差中位 的比例；p ≥ 0.05 ⇒ 句前「隨便挑一段月份也做得到」
 S6 並列：原策略各曆月平均報酬（200 顆逐日權益 ⇒ 每顆每月報酬 ⇒ 平均；段內逐月描述）
 S7 新規矩 ③：挑中格確認或早年「合格／另列」⇒ 出場敏感度（描述、同 200 顆）：SL10／SL20（stop fix）、TP30h／TP50h（trim_rule gain，⚠ 與 cash_mode bench 不可同開 ⇒ 乙丙不適用）、
    檔數（營飆 5／20、營量 10／5）；AT2（進場以來最高收盤 − 2×ATR14，前一日值 ⇒ 收盤 ≤ 線當日收盤出場）、R0-40（第 40 根有效 K 棒收盤 ≤ 進場價 ⇒ 當日收盤出場）
    逐筆改寫出場日（只看排定出場日之前的 K 棒；丙的切倉先做）；⚠ S7 的 AT2／R0-40 落地在 3 顆種子除錯試跑之後補寫（試跑只為抓錯，定義照 PREREG事件 同式）
 S8 資料尾：主窗 T1（窗內以收盤計值）；早年窗尾 ＝ 早年版面末日（AND_mtm ＝ T1 讀法）
 S9 閘：主窗原策略 200 顆 ＝ resultsT1fix seeds t1（cagr、mdd repr、eq_sha）；早年原策略（stop_force 關）200 顆 ＝ resultsV body_seeds main（cagr、mdd repr）；
    做法甲 1 月 種子 0 重跑逐位元
輸出 backtest/resultsSeason/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR

OUT = "backtest/resultsSeason"
MONTHS = {"1月": (1,), "1～2月": (1, 2), "1～3月": (1, 2, 3)}
METHODS = ("甲", "乙", "丙")
STRATS = {"營飆": {"rule": "H120", "N": 10, "seed0": 1000}, "營量": {"rule": "H60", "N": 20, "seed0": 7000}}
COST050 = 0.00385
SEG = {"main": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}, "early": {"早年": ("2012-06-04", "2014-12-31")}}
K7_MIN = 20
B_BOOT = 20_000
_G: dict = {}


def cells():
    return [(m, mo) for mo in MONTHS for m in METHODS]


# ═════════════ 世界 ═════════════
def world_main(log):
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    b = RR.load_bench(cal); bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float)
    return {"kind": "main", "data": D.DATA, "cal": cal, "NP": NP, "w0": w0, "w1": w1, "closes": ctx["closes"], "opens": ctx["opens"], "SF": SF,
            "sig": {"營飆": ctx["sig"], "營量": ctx["sig13"]}, "b": b, "bo": bo}


def world_early(log):
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    V.body_setup("main", log)
    G = V._B; YG = Y._G
    cal = G["cal"]; w0, w1 = G["w0"], G["w1"]
    s1 = Y.sig_of(1, "mtm", w0, w1); s13 = Y.sig_of(13, "mtm", w0, w1)
    sids = sorted(set(s1["sid"]) | set(s13["sid"]))
    SF = R.stop_force_days(R.valid_from_data(sids, YG["uni"], cal), w1)
    b = RR.load_bench(cal); bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float)
    return {"kind": "early", "data": D.DATA, "cal": cal, "NP": YG["NP"], "w0": w0, "w1": w1, "closes": YG["closes"], "opens": YG["opens"], "SF": SF,
            "sig": {"營飆": s1, "營量": s13}, "b": b, "bo": bo}


# ═════════════ 變體 ═════════════
def mmask(W, ym):
    cal = W["cal"]; m = np.zeros(W["NP"], bool)
    m[:len(cal)] = np.array([(y, mo) in ym for y, mo in zip(cal.year, cal.month)])
    return m


def ym_of(W, months):
    return {(y, mo) for y in sorted(set(W["cal"].year)) for mo in months}


def bench_series(W, mask):
    c = pd.Series(np.r_[W["b"], W["b"][-1]]).ffill().to_numpy(float)
    o = np.r_[W["bo"], np.nan]; o = np.where(np.isfinite(o) & (o > 0), o, np.r_[c[0], c[:-1]])
    B = np.ones(len(c))
    for t in range(1, len(c)):
        if mask[t] and not mask[t - 1]:
            r = c[t] / o[t]
        elif mask[t] and mask[t - 1]:
            r = c[t] / c[t - 1]
        elif (not mask[t]) and mask[t - 1]:
            r = o[t] / c[t - 1] * (1.0 - COST050)
        else:
            r = 1.0
        B[t] = B[t - 1] * r
    return B


def var_sig(W, strat, method, mask):
    rule = STRATS[strat]["rule"]; xs, gs = f"xpos_{rule}", f"g_{rule}"
    s = W["sig"][strat]
    s = s[~mask[s["entry_pos"].to_numpy(int)]].copy()
    cut = 0
    if method == "丙":
        starts = np.flatnonzero(mask & ~np.r_[False, mask[:-1]])
        X = s[xs].to_numpy(int).copy(); G = s[gs].to_numpy(float).copy()
        for i, (sid, e, x) in enumerate(zip(s["sid"], s["entry_pos"].to_numpy(int), X)):
            j = np.searchsorted(starts, e, side="right")
            if j < len(starts) and starts[j] <= x:
                f = int(starts[j]); o = W["opens"][sid]; c = W["closes"][sid]
                px = o[f] if np.isfinite(o[f]) and o[f] > 0 else c[f - 1]
                X[i] = f; G[i] = px / o[e] - 1.0; cut += 1
        s[xs] = X; s[gs] = G
    return s, cut


def exit_mod(W, sig, rule):
    """AT2、R0-40：逐筆改 xpos、g（只看排定出場日之前的有效 K 棒）。"""
    old = D.DATA; D.DATA = W["data"]
    cal = W["cal"]; xs, gs = f"xpos_{rule}", f"g_{rule}"
    A2 = sig.copy(); R4 = sig.copy(); cache = {}; cA = cR = 0
    ja, ga = A2.columns.get_loc(xs), A2.columns.get_loc(gs)
    for i, (sid, e, x) in enumerate(zip(sig["sid"], sig["entry_pos"].to_numpy(int), sig[xs].to_numpy(int))):
        if sid not in cache:
            df = D.load_stock(sid, "twse", cal).df
            c = df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c))
            h = df["high"].to_numpy(float)[idx]; l_ = df["low"].to_numpy(float)[idx]; cc = c[idx]
            tr = np.r_[h[0] - l_[0], np.maximum.reduce([h[1:] - l_[1:], np.abs(h[1:] - cc[:-1]), np.abs(l_[1:] - cc[:-1])])] if len(idx) else np.array([])
            atr = np.full(len(idx), np.nan)
            if len(idx) >= 14:
                atr[13] = tr[:14].mean()
                for k in range(14, len(idx)):
                    atr[k] = (atr[k - 1] * 13 + tr[k]) / 14
            cache[sid] = (idx, cc, atr)
        idx, cc, atr = cache[sid]; oe = W["opens"][sid][e]
        ke = int(np.searchsorted(idx, e))
        if ke >= len(idx) or idx[ke] != e or not (np.isfinite(oe) and oe > 0):
            continue
        kx = int(np.searchsorted(idx, x, side="left") - 1)
        mx = cc[ke]
        for k in range(ke + 1, kx + 1):
            if np.isfinite(atr[k - 1]) and cc[k] <= mx - 2 * atr[k - 1]:
                A2.iat[i, ja] = int(idx[k]); A2.iat[i, ga] = cc[k] / oe - 1.0; cA += 1
                break
            mx = max(mx, cc[k])
        k40 = ke + 39
        if k40 <= kx and cc[k40] <= oe:
            R4.iat[i, ja] = int(idx[k40]); R4.iat[i, ga] = cc[k40] / oe - 1.0; cR += 1
    D.DATA = old
    return {"AT2": A2, "R0-40": R4}, {"AT2 提前": cA, "R0-40 提前": cR}


def _run(W, strat, sig, r, bench=None, audit=None, sf=True, nslot=None, **extra):
    sp = STRATS[strat]
    kw = dict(return_equity=True, audit=audit)
    if strat == "營量":
        kw.update(log=[], d_max=None, pick="relvol", queue_days=0)
    if sf:
        kw["stop_force"] = W["SF"]
    if bench is not None:
        kw.update(cash_mode="bench", bench=bench, bench_cost=0.0)
    kw.update(extra)
    return R.simulate_mtm(sig, sp["rule"], nslot or sp["N"], np.random.default_rng(sp["seed0"] + r), W["closes"], W["opens"], W["NP"], **kw)


def stats(W, o):
    eq = np.asarray(o["equity"], float); cal = W["cal"]; n = len(cal)
    row = {"first": int(o["first"]), "end": int(o["end"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16]}
    for sg, (a, b) in SEG[W["kind"]].items():
        ia = int(cal.searchsorted(pd.Timestamp(a))); ib = int(cal.searchsorted(pd.Timestamp(b), side="right") - 1)
        c, m, _ = RR.win_metrics(eq, o["first"], o["end"], ia, ib)
        row[f"{sg}_年化"] = c; row[f"{sg}_回落"] = m
    yrs = cal.year.to_numpy()
    for y in sorted(set(yrs)):
        ix = np.flatnonzero(yrs == y); p = ix[0] - 1
        row[f"y{y}"] = float(eq[ix[-1]] / eq[p] - 1.0) if p >= 0 else np.nan
    return row, eq


def _job(args):
    W = _G["W"]
    kind, strat, key, r = args
    if kind == "base":
        au = []; o = _run(W, strat, W["sig"][strat], r, audit=au)
        row, eq = stats(W, o)
        cal = W["cal"]
        buys = pd.Series([f"{cal[a['t']].year}-{cal[a['t']].month:02d}" for a in au if a["side"] == "buy" and a["t"] < len(cal)]).value_counts()
        row.update({f"b{k}": int(v) for k, v in buys.items()})
        mret = pd.Series(eq[:len(cal)], index=cal).resample("ME").last()
        row.update({f"m{d:%Y-%m}": float(v) for d, v in (mret / mret.shift(1) - 1).dropna().items()})
    elif kind == "base_nosf":
        o = _run(W, strat, W["sig"][strat], r, sf=False); row, _ = stats(W, o)
    elif kind == "cell":
        method, mo = key
        mask = mmask(W, ym_of(W, MONTHS[mo]))
        sig, _ = var_sig(W, strat, method, mask)
        o = _run(W, strat, sig, r, bench=None if method == "甲" else bench_series(W, mask))
        row, _ = stats(W, o)
    elif kind == "fake":
        method, mo, k = key
        L = len(MONTHS[mo]); rng = np.random.default_rng([20260928, list(STRATS).index(strat), k])
        ym = set()
        for y in sorted(set(W["cal"].year)):
            u = int(rng.integers(1, 14 - L))
            ym |= {(y, u + j) for j in range(L)}
        mask = mmask(W, ym)
        sig, _ = var_sig(W, strat, method, mask)
        o = _run(W, strat, sig, r, bench=None if method == "甲" else bench_series(W, mask))
        row, _ = stats(W, o); row["fake_k"] = k
    elif kind == "sens":
        method, mo, vname, kw = key
        mask = mmask(W, ym_of(W, MONTHS[mo]))
        sig, _ = var_sig(W, strat, method, mask)
        sig = _G.get("SIGV", {}).get((W["kind"], strat, vname), sig)
        kw = dict(kw); ns = kw.pop("nslot", None)
        o = _run(W, strat, sig, r, bench=None if method == "甲" else bench_series(W, mask), nslot=ns, **kw)
        row, _ = stats(W, o); row["變體"] = vname
    row.update({"kind": kind, "strat": strat, "cell": key if isinstance(key, str) else "_".join(map(str, key[:2])), "r": r})
    return row


def boot_year(d, rng):
    d = np.asarray(d, float)
    if len(d) < 3:
        return None
    idx = rng.integers(0, len(d), size=(B_BOOT, len(d)))
    m = d[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchSeason {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜PREREG季節性 seq1 sha 8b763863d5b15258 =====")
    S = {"登錄": "PREREG季節性 seq1 sha 8b763863d5b15258", "閘": {}}
    SEEDS = range(a.seeds)
    ROWS = []
    Wd = {}
    PICK = {}
    for wk in ("main", "early"):
        RR.use_snapshot()
        W = world_main(log) if wk == "main" else world_early(log)
        Wd[wk] = W; _G["W"] = W
        cal = W["cal"]
        log(f"[{wk}] 日曆 {cal[0].date()}～{cal[-1].date()}｜窗 {cal[W['w0']].date()}～{cal[W['w1']].date()}｜訊號 營飆 {len(W['sig']['營飆'])}、營量 {len(W['sig']['營量'])}｜停止交易 {len(W['SF'])}")
        jobs = [("base", s, "base", r) for s in STRATS for r in SEEDS] + [("cell", s, c, r) for s in STRATS for c in cells() for r in SEEDS]
        if wk == "early":
            jobs += [("base_nosf", s, "base_nosf", r) for s in STRATS for r in SEEDS]
        with Pool(a.procs) as pool:
            rows = pool.map(_job, jobs, chunksize=8)
        for x in rows:
            x["world"] = wk
        ROWS += rows
        DF = pd.DataFrame(rows)
        # 閘
        if wk == "main":
            ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
            g = {}
            for s, key in (("營飆", "c1"), ("營量", "c13")):
                rf = ref[(ref["key"] == key) & (ref["var"] == "t1")].set_index("r")
                mine = DF[(DF["kind"] == "base") & (DF["strat"] == s)].set_index("r")
                ok = 0
                for r in mine.index:
                    ok += int(mine.at[r, "eq_sha"] == rf.at[r, "eq_sha"])
                g[s] = {"顆": int(len(mine)), "eq_sha 相同": ok}
            S["閘"]["主窗原策略 ＝ resultsT1fix t1"] = g
        else:
            ref = pd.read_csv("backtest/resultsV/body_seeds.csv.gz", float_precision="round_trip")
            ref = ref[ref["variant"] == "main"]
            g = {}
            for s, cid in (("營飆", 1), ("營量", 13)):
                rf = ref[ref["cell"] == cid].set_index("r")
                mine = DF[(DF["kind"] == "base_nosf") & (DF["strat"] == s)].set_index("r")
                ok = sum(int(repr(float(mine.at[r, "早年_年化"])) == repr(float(rf.at[r, "cagr"])) and repr(float(mine.at[r, "早年_回落"])) == repr(float(rf.at[r, "mdd"]))) for r in mine.index)
                g[s] = {"顆": int(len(mine)), "年化回落逐位元相同": ok}
            S["閘"]["早年原策略（stop_force 關）＝ resultsV body_seeds main"] = g
        log(f"[閘 {wk}] {S['閘']}")
        # 挑格（主窗探索）
        if wk == "main":
            for s in STRATS:
                base = DF[(DF["kind"] == "base") & (DF["strat"] == s)].set_index("r")
                cand = []
                for (m, mo) in cells():
                    c = DF[(DF["kind"] == "cell") & (DF["strat"] == s) & (DF["cell"] == f"{m}_{mo}")].set_index("r")
                    d = float((c["探索_年化"] - base["探索_年化"]).median())
                    months = MONTHS[mo]
                    bcols = [k for k in base.columns if k.startswith("b") and k[1:5].isdigit() and int(k[6:8]) in months and "2017-03" <= k[1:] <= "2021-12"]
                    nb = float(base[bcols].fillna(0).sum(axis=1).median()) if bcols else 0.0
                    cand.append({"格": f"{m}_{mo}", "探索差": d, "比值": float(c["探索_年化"].median() / abs(c["探索_回落"].median())), "月份內原策略進場": nb, "退化": nb < K7_MIN})
                C = pd.DataFrame(cand)
                ok = C[~C["退化"]]
                log(f"[挑格候選 {s}] " + "；".join(f"{r.格} 差{r.探索差:+.4f} 進場{r.月份內原策略進場:.0f}{'（退化）' if r.退化 else ''}" for r in C.itertuples()))
                if len(ok):
                    best = ok.sort_values(["探索差", "比值"], ascending=[False, False]).iloc[0]
                    PICK[s] = best["格"]
                S.setdefault("挑格", {})[s] = {"格": PICK.get(s, "依構造不可判定（9 格全退化）"), "候選": C.to_dict("records")}
            log(f"[挑格] {PICK}")
        # 假訊號
        jobs = [("fake", s, (PICK[s].split("_")[0], PICK[s].split("_")[1], k), k % a.seeds) for s in PICK for k in range(a.reps)]
        with Pool(a.procs) as pool:
            rows = pool.map(_job, jobs, chunksize=8)
        for x in rows:
            x["world"] = wk
        ROWS += rows
        log(f"[假訊號 {wk}] 完成 {len(rows)}")
    DF = pd.DataFrame(ROWS)
    DF.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # 0050
    Z = {}
    for wk, W in Wd.items():
        cal = W["cal"]
        for sg, (x, y) in SEG[wk].items():
            ia = int(cal.searchsorted(pd.Timestamp(x))); ib = int(cal.searchsorted(pd.Timestamp(y), side="right") - 1)
            c, m, _ = RR.win_metrics(W["b"], 0, len(cal), ia, ib); Z[sg] = (c, m)
    S["0050"] = {k: {"年化": v[0], "回落": v[1], "比值": v[0] / abs(v[1])} for k, v in Z.items()}

    def lab(c, m, sg):
        c0, m0 = Z[sg]
        return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")
    # 全格表
    rows = []; rngb = np.random.default_rng(20260928)
    for wk in ("main", "early"):
        for s in STRATS:
            base = DF[(DF["world"] == wk) & (DF["kind"] == "base") & (DF["strat"] == s)].set_index("r")
            for sg, (x, y) in SEG[wk].items():
                yrs = [yy for yy in range(pd.Timestamp(x).year, pd.Timestamp(y).year + 1) if pd.Timestamp(yy, 1, 31) >= pd.Timestamp(x) and pd.Timestamp(yy, 1, 1) <= pd.Timestamp(y)]
                rows.append({"世界": wk, "策略": s, "格": "原策略", "段": sg, "年化中位": float(base[f"{sg}_年化"].median()), "回落中位": float(base[f"{sg}_回落"].median()),
                             "標籤": lab(float(base[f"{sg}_年化"].median()), float(base[f"{sg}_回落"].median()), sg)})
                for (m, mo) in cells():
                    c = DF[(DF["world"] == wk) & (DF["kind"] == "cell") & (DF["strat"] == s) & (DF["cell"] == f"{m}_{mo}")].set_index("r")
                    dA = (c[f"{sg}_年化"] - base[f"{sg}_年化"]); dM = (c[f"{sg}_回落"] - base[f"{sg}_回落"])
                    yd = {yy: float((c[f"y{yy}"] - base[f"y{yy}"]).mean()) for yy in yrs if f"y{yy}" in c}
                    ci = boot_year(list(yd.values()), rngb)
                    v = "依構造不可判定（年初 ＜ 3）" if ci is None else ("多賺" if ci[0] > 0 else ("少賺" if ci[1] < 0 else "測不出"))
                    cA, cM = float(c[f"{sg}_年化"].median()), float(c[f"{sg}_回落"].median())
                    rows.append({"世界": wk, "策略": s, "格": f"{m}_{mo}", "段": sg, "年化中位": cA, "回落中位": cM, "標籤": lab(cA, cM, sg),
                                 "年化差中位": float(dA.median()), "回落差中位": float(dM.median()), "年初個數": len(yd), "逐年差": json.dumps({str(k): round(v_, 6) for k, v_ in yd.items()}),
                                 "年差平均": float(np.mean(list(yd.values()))) if yd else np.nan, "年CI下": ci[0] if ci else np.nan, "年CI上": ci[1] if ci else np.nan, "年判定": v})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    # 挑中格判定＋假訊號
    J = {}
    for s in STRATS:
        if s not in PICK:
            J[s] = {"格": "依構造不可判定（9 格全退化）", "件句": "依構造不可判定"}; continue
        pk = PICK[s]; out = {"格": pk}
        for wk, sg in (("main", "確認"), ("early", "早年"), ("main", "探索")):
            r_ = T[(T["策略"] == s) & (T["格"] == pk) & (T["段"] == sg)].iloc[0]
            base = DF[(DF["world"] == wk) & (DF["kind"] == "base") & (DF["strat"] == s)].set_index("r")
            fk = DF[(DF["world"] == wk) & (DF["kind"] == "fake") & (DF["strat"] == s)]
            fd = fk[f"{sg}_年化"].to_numpy() - base.loc[fk["r"].to_numpy(), f"{sg}_年化"].to_numpy()
            out[sg] = {k: (r_[k] if not isinstance(r_[k], (np.floating, float)) else float(r_[k])) for k in ("年化中位", "回落中位", "標籤", "年化差中位", "回落差中位", "年初個數", "逐年差", "年CI下", "年CI上", "年判定")}
            out[sg]["假訊號 p（隨機 ≥ 配對差中位）"] = float(np.mean(fd >= r_["年化差中位"]))
            out[sg]["原策略"] = T[(T["策略"] == s) & (T["格"] == "原策略") & (T["段"] == sg)].iloc[0][["年化中位", "回落中位", "標籤"]].to_dict()
        n_more = sum(out[sg]["年判定"] == "多賺" for sg in ("確認", "早年"))
        out["件句"] = "年初避開有用" if n_more == 2 else ("不穩" if n_more == 1 else "不必避開")
        J[s] = out
    S["判定"] = J
    log(f"[判定] {json.dumps(J, ensure_ascii=False, default=str)[:1500]}")
    # 月份描述
    MD = {}
    for wk in ("main", "early"):
        for s in STRATS:
            base = DF[(DF["world"] == wk) & (DF["kind"] == "base") & (DF["strat"] == s)]
            mc = [k for k in base.columns if k.startswith("m") and k[1:5].isdigit() and base[k].notna().any()]
            for sg, (x, y) in SEG[wk].items():
                sel = [k for k in mc if x[:7] <= k[1:] <= y[:7]]
                mm = base[sel].mean(axis=0)
                MD[f"{s}_{sg}"] = {str(mo): float(mm[[k for k in sel if int(k[6:8]) == mo]].mean()) for mo in range(1, 13)}
    S["原策略各曆月平均報酬（200 顆平均）"] = MD
    # 新規矩 ③
    need = {s: [sg for sg in ("確認", "早年") if J[s][sg]["標籤"] in ("合格", "另列")] for s in PICK}
    S["新規矩③"] = {s: ("要跑" if v else "不適用") for s, v in need.items()}
    SENS = []
    for s, v in need.items():
        if not v:
            continue
        m, mo = PICK[s].split("_")
        var = {"SL10": {"stop": ("fix", 0.10)}, "SL20": {"stop": ("fix", 0.20)}}
        if m == "甲":
            var.update({"TP30h": {"trim_rule": {"kind": "gain", "x": 0.30, "frac": 0.5}}, "TP50h": {"trim_rule": {"kind": "gain", "x": 0.50, "frac": 0.5}}})
        for ns in ((5, 20) if s == "營飆" else (5, 10)):
            var[f"N{ns}"] = {"nslot": ns}
        var["AT2"] = {}; var["R0-40"] = {}
        for wk in ("main", "early"):
            _G["W"] = Wd[wk]
            sg0, _ = var_sig(Wd[wk], s, m, mmask(Wd[wk], ym_of(Wd[wk], MONTHS[mo])))
            mods, cnt = exit_mod(Wd[wk], sg0, STRATS[s]["rule"])
            _G.setdefault("SIGV", {}).update({(wk, s, k): v for k, v in mods.items()})
            S.setdefault("新規矩③ 提前出場筆數", {})[f"{s}_{wk}"] = cnt
            with Pool(a.procs) as pool:
                rr = pool.map(_job, [("sens", s, (m, mo, vn, kw), r) for vn, kw in var.items() for r in SEEDS], chunksize=8)
            for x in rr:
                x["world"] = wk
            SENS += rr
    if SENS:
        SD = pd.DataFrame(SENS); SD.to_csv(os.path.join(OUT, "sens_seeds.csv.gz"), index=False, float_format="%.17g")
        S["新規矩③ 出場敏感度（描述；各段 [年化中位, 回落中位]）"] = {
            f"{s}_{vn}": {sg: [float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())] for sg in ("探索", "確認", "早年") if f"{sg}_年化" in g and g[f"{sg}_年化"].notna().any()}
            for (s, vn), g in SD.groupby(["strat", "變體"])}
        S["新規矩③ 註"] = "乙、丙（cash_mode bench）與 trim_rule 不可同開（引擎限制）⇒ TP30h／TP50h 只在做法甲；AT2、R0-40 逐筆改出場日（丙的切倉先做）"
    # 閘：甲 1月 種子 0 重跑
    W = Wd["main"]; _G["W"] = W
    r1 = _job(("cell", "營量", ("甲", "1月"), 0)); r2 = _job(("cell", "營量", ("甲", "1月"), 0))
    S["閘"]["甲 1月 營量 種子0 重跑逐位元"] = r1["eq_sha"] == r2["eq_sha"]
    mask = mmask(W, ym_of(W, MONTHS["1～3月"]))
    S["丙 1～3月 被切部位數"] = {s: var_sig(W, s, "丙", mask)[1] for s in STRATS}
    S["窗"] = SEG
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[閘] {S['閘']}")
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

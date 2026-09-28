# -*- coding: utf-8 -*-
"""PREREG低週轉 seq1（台股策略線 登錄 sha 47ac98f3c6b5fb02；裁定 seq268 §三 發號、N ＋1）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLowTO [--procs 2] [--reps 1000] [--report]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLowTO_check.py

問：挑「平常很少人交易」（周轉率低）的股票，扣成本後能不能贏 0050？營收創高池內改挑周轉率低的，會不會比營量式「量放大」挑法好？

═══ 本線讀法（⭐ 看任何本件數字前寫死）═══
 L1 周轉率 TO(L) ＝ 換股日 e 的前 L 個交易日（日曆位置 e−L … e−1）「成交股數 ÷ 發行股數」的平均；L ∈ {20, 60, 120}
    成交股數 ＝ stocks/<代號>.csv volume（無成交日 ⇒ 0）；發行股數 ＝ shares（只 ffill、⛔ 不 bfill；≤ 0 ⇒ 缺）；窗內任一日發行股數缺 ⇒ 該股該期不進候選（⛔ 不補）
    資料：主 ＝ main 快照 edc6f8002f；早年 ＝ 早年版面 950ad26e12（登錄「發行股數 950ad26e12 已補 2004 起」；價格、面板用 researchMomX.EARLY 的 3edc0e2206，兩版面日曆逐日相同）
 L2 換股簿 ＝ researchMomX.sim_book（落選開盤賣、跌停／停牌延後、漲停／停牌不買不遞補、min(前日權益÷N, 現金)、0.585%；⭐ 停止交易強制出場：開）；
    換股日 e ＝ 當月 W1 量測日次一交易日（researchMomX.load_world）；季 ＝ 1、4、7、10 月；半年 ＝ 1、7 月；等權、續抱仍入選
    ⇒ 按期換、窗尾照市值，⛔ 沒有固定持有天數的出場 ⇒ 依構造不因資料尾截斷（t1_censor 不適用，照實寫）
 L3 甲族 ＝ 當期 eligible 全體中 TO(L) 最低 N 檔（同值依代號）｜乙族 ＝ 當期 eligible ∩ 營收池 中 TO(L) 最低 N 檔（池不足 ⇒ 剩餘現金）
    營收池 ＝ p4_features.rev_hi24_flags 在 e ＝ 100（最新可用月營收創 24 月新高；researchQual B6 同式，⛔ 不剔金融）；月營收：主 ＝ research34.load_revenue（快照）、早年 ＝ 早年版面 2003 起
    乙族並列「同池 relvol 挑法」（營量式量放大；relvol ＝ e−1 那根有效 K 棒成交金額 ÷ 前 60 根有效 K 棒金額中位，researchQual B6 同式；描述、不挑格）
 L4 格：每族 L 3 × 頻率 3 × N 2 ＝ 18 格，兩族共 36 格
 L5 段：主 2017-03-02～2026-08-24 一條權益（探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24）；
    早年 2005-01-01～2014-12-31（只上市；researchMomX.EARLY 世界、eligible ＝ liq_ok ∧ bars_ok ＝ 動能改良讀法 2）
 L6 退化（挑前排除）：探索段平均持股 ＜ N÷2 或現金比例 ＞ 30%；挑格：每族探索段先合格、再比值（年化÷|回落|）；平手 ⇒ 年化高、月＜季＜半年、N 小、L 小
    判定：確認、早年各自對 0050 同段（使用者判準）；族標籤 ＝ 兩段較嚴者
 L7 對照（K4）：同池隨機 1,000 次（挑中格頻率與 N；每期從排名池不放回抽 N；default_rng([20260928, 族, r])；p ＝ 隨機年化 ≥ 本格）｜反向臂（TO 最高 N 檔、同格、描述）｜
    營量 v1（T1；resultsYLtrend/cells.csv 同段）｜品質乙族（resultsQual 挑中）｜0050
 L8 現實版（K3；裁定 seq268 §三 必含 C5）：換股簿版滑價 ＝ researchSlip 的定義搬到換股簿：C1 每邊 +0.3%；C2 資金 50 萬、每檔 Q ＝ 50 萬÷N、衝擊 ＝ σ20 × √(Q÷ADV20)（買價 ×(1＋衝擊)、賣價 ×(1−衝擊)）；
    C4 均價成交（(開＋高＋低＋收)÷4，缺 ⇒ 開盤）；C5 零股低消 20 元：每邊加 max(20÷A − 0.1425%, 0)，A ＝ 25 萬 ÷ N（researchSlip 營量／營飆 A 同尺度）；
    C3 一字鎖：換股簿本來就擋「開盤漲停不買、開盤跌停延後賣」（比一字鎖嚴）⇒ 沿用、不另加；σ20、ADV20、均價 ＝ researchSlip.stock_extra
    閘：現實版函式在「全關」時 ＝ researchMomX.sim_book 逐位元
 L9 必報：挑中格持股 20 日平均成交金額 10／50／90 分位、持股 60 日波動在當期 eligible 內的分位（平均）、持股 TO 分位、各年報酬、換手與成本；與 X2（researchExt x2_picks_monthly，同換股月）持股重疊率
 L10 新規矩 ③：任一族挑中格確認或早年「合格／另列」⇒ (a) 全賣全買（sim_book mode="all"）、(b) 跌破 MA60 次日開盤賣（researchMomX.ma_table、sim_book ma_stop）⇒ 描述
輸出 backtest/resultsLowTO/
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchMomX as MX            # ⭐ 換股簿、世界載入（只 import）
from backtest import research13 as R13
from backtest import research34 as R34
from backtest import p4_features as P4F
D, TR, H2 = MX.D, MX.TR, MX.H2

OUT = "backtest/resultsLowTO"
COST = MX.COST
LS = (20, 60, 120); FREQS = {"月": None, "季": (1, 4, 7, 10), "半年": (1, 7)}; NS = (10, 20)
FORD = {"月": 0, "季": 1, "半年": 2}
MAINW = dict(MX.MAIN)
EARLYW = dict(MX.EARLY, w=("2005-01-01", "2014-12-31"), segs={"早年": ("2005-01-01", "2014-12-31")})
SHARES_E = os.path.expanduser("~/earlydata/950ad26e12/main/data")
CAP = 500_000; SLIP = 0.003; BASE_CAPITAL = 250_000
_G: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def label(c, m, b):
    return MX.label(c, m, b["cagr"], b["mdd"])


# ═════════════ 世界 ═════════════
def _vol_sh(args):
    sid, src, cal = args
    p = os.path.join(src, "stocks", sid + ".csv")
    if not os.path.exists(p):
        return sid, None
    x = pd.read_csv(p, dtype={"date": str}, usecols=["date", "volume", "shares", "amount"]).drop_duplicates("date")
    x.index = pd.to_datetime(x["date"]); x = x.reindex(cal)
    v = np.nan_to_num(pd.to_numeric(x["volume"], errors="coerce").to_numpy(float), nan=0.0)
    sh = pd.to_numeric(x["shares"], errors="coerce"); sh = sh.where(sh > 0).ffill().to_numpy(float)
    return sid, (v, sh, pd.to_numeric(x["amount"], errors="coerce").to_numpy(float))


def world(W, shares_src, procs, log):
    Wd = MX.load_world(W, procs, log)
    cal = Wd["cal"]; n = Wd["n"]
    with Pool(procs) as pool:
        VS = dict(pool.map(_vol_sh, [(s, shares_src, cal) for s in Wd["sids"]], chunksize=16))
    D.DATA = W["data"]
    rev, _, _ = R34.load_revenue()
    rf = P4F.rev_hi24_flags(rev, cal)
    RB = {}; rows = []; miss_sh = 0; tot = 0
    for e in Wd["rebs"]:
        el = Wd["reb"][e]
        row = rf.iloc[e] if e < len(rf) else None
        pool = set(row.index[row.to_numpy() == 100]) if row is not None else set()
        TO = {L: {} for L in LS}; rv = {}
        for s in el:
            z = VS.get(s)
            tot += 1
            if z is None:
                miss_sh += 1; continue
            v, sh, amt = z
            for L in LS:
                if e - L < 0:
                    continue
                w_ = sh[e - L:e]
                if np.all(np.isfinite(w_)):
                    TO[L][s] = float(np.mean(v[e - L:e] / w_))
            if not np.isfinite(sh[e - 1]):
                miss_sh += 1
            if s in pool:
                vv = Wd["P"][s]["valid"]; m_ = e - 1
                if vv[m_]:
                    b = np.flatnonzero(vv[:m_ + 1])
                    if len(b) >= 61:
                        med = float(np.nanmedian(amt[b[-61:-1]])); a_ = amt[m_]
                        if med > 0 and np.isfinite(a_):
                            rv[s] = a_ / med
        RB[e] = {"el": el, "pool": sorted(s for s in el if s in pool), "TO": TO, "relvol": rv}
        for s in el:
            rows.append((e, s, *(TO[L].get(s, np.nan) for L in LS), s in pool, rv.get(s, np.nan)))
    Wd["RB"] = RB; Wd["VS"] = VS
    Wd["TOtab"] = pd.DataFrame(rows, columns=["e", "sid", "TO20", "TO60", "TO120", "營收池", "relvol"])
    Wd["segp"] = {nm: (max(int(cal.searchsorted(pd.Timestamp(x))), Wd["w0"]), min(int(cal.searchsorted(pd.Timestamp(y), side="right") - 1), Wd["w1"]))
                  for nm, (x, y) in W["segs"].items()}
    Wd["B50"] = {nm: dict(zip(("cagr", "mdd"), map(float, R13.window_stats(Wd["bench"], 0, n, x, y + 1)))) for nm, (x, y) in Wd["segp"].items()}
    log(f"[世界] {W['data']}｜換股日 {len(Wd['rebs'])}｜eligible 股-期 {tot:,}、發行股數缺（e−1）{miss_sh:,}｜營收池中位 {np.median([len(RB[e]['pool']) for e in Wd['rebs']]):.0f}")
    return Wd


def select(Wd, fam, L, fq, N, how="low"):
    months = FREQS[fq]; sel = {}; short = 0; nreb = 0
    for e in Wd["rebs"]:
        if months is not None and Wd["cal"][e].month not in months:
            continue
        R = Wd["RB"][e]; nreb += 1
        if how == "relvol":
            d = {s: R["relvol"][s] for s in R["pool"] if s in R["relvol"]}
            items = sorted(d.items(), key=lambda t: (-t[1], t[0]))
        else:
            base = R["TO"][L]
            d = {s: base[s] for s in (R["el"] if fam == "甲" else R["pool"]) if s in base}
            items = sorted(d.items(), key=lambda t: (t[1], t[0])) if how == "low" else sorted(d.items(), key=lambda t: (-t[1], t[0]))
        short += int(len(d) < N)
        sel[e] = [s for s, _ in items[:N]]
    return sel, (short / nreb if nreb else None)


def seg_row(Wd, res, sel, N):
    out = {}
    eq = res["eq"]
    for nm, (a, b) in Wd["segp"].items():
        c, m = R13.window_stats(eq, 0, len(eq), a, b + 1)
        rs = [e for e in sorted(sel) if a <= e <= b]
        tv = [res["buys"][e] / N for e in rs[1:] if e in res["buys"]]
        yrs = (b - a + 1) / 245
        cy = float(sum(res["costd"][t] / eq[t - 1] for t in range(a, b + 1) if res["costd"][t] > 0) / yrs)
        out.update({f"{nm}_年化": float(c), f"{nm}_回落": float(m), f"{nm}_比值": float(c) / abs(float(m)) if m < 0 else float("nan"),
                    f"{nm}_持股": float(np.mean(res["npos"][a:b + 1])), f"{nm}_現金": float(np.nanmean(res["cashf"][a:b + 1])),
                    f"{nm}_換手": float(np.mean(tv)) if tv else float("nan"), f"{nm}_成本年": cy})
    return out


def years(Wd, eq):
    cal = Wd["cal"]; yr = np.asarray(cal.year); out = {}
    for y in sorted(set(yr[Wd["w0"]:Wd["w1"] + 1])):
        ii = np.flatnonzero(yr == y); a = max(ii[0], Wd["w0"]); b = min(ii[-1], Wd["w1"])
        p = a - 1 if a > Wd["w0"] else a
        out[int(y)] = float(eq[b] / eq[p] - 1.0)
    return out


# ═════════════ 現實版換股簿（researchMomX.sim_book 同一套＋價格／成本掛鉤）═════════════
def sim_book_x(sel, Wd, N, X=None, spec=None):
    spec = spec or {}
    P, dl, SF = Wd["P"], Wd["dl"], Wd["SF"]
    t0, t1, n = Wd["w0"], Wd["w1"], Wd["n"]
    cr = COST + 2 * spec.get("s", 0.0)
    if spec.get("m5"):
        cr += 2 * max(spec["m5"] / (BASE_CAPITAL / N) - 0.001425, 0.0)
    Q = CAP / N

    def imp(s, t):
        if not spec.get("cap") or X is None or X.get(s) is None:
            return 0.0
        a, sg = X[s]["adv20"][t], X[s]["sig20"][t]
        return float(sg * math.sqrt(Q / a)) if (np.isfinite(a) and a > 0 and np.isfinite(sg)) else 0.0

    def px_of(s, t, o_t):
        if spec.get("c4") and X is not None and X.get(s) is not None:
            v = X[s]["avg"][t]
            if np.isfinite(v) and v > 0:
                return v
        return o_t
    eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    npos = np.zeros(n, np.int16); cashf = np.zeros(n); costd = np.zeros(n); buys = {}; hold = {}
    for t in range(t0, t1 + 1):
        s_ = sel.get(t)
        if s_ is not None:
            pend = (pend | (set(pos) - set(s_))) - set(s_)
        for s in sorted(set(pend) | {s for s in pos if s in SF and t > SF[s]}):
            if s not in pos:
                pend.discard(s); continue
            x = P[s]; o_t = x["o"][t]
            if s in SF and t > SF[s]:
                px = x["c"][t]
            elif x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = px_of(s, t, o_t) * (1 - min(imp(s, t), 0.99))
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]
            else:
                continue
            u, amt = pos.pop(s)
            cash += u * px - amt * cr; costd[t] += amt * cr
            pend.discard(s)
        if s_ is not None:
            free = N - len(pos)
            new = [s for s in s_ if s not in pos][:max(free, 0)]
            nb = 0
            for s in new:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0) or (s in SF and t > SF[s]):
                    continue
                if x["up_o"][t]:
                    continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                bp = px_of(s, t, o_t) * (1 + imp(s, t))
                cash -= amt; pos[s] = [amt / bp, amt]; nb += 1
            buys[t] = nb; hold[t] = sorted(pos)
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buys": buys, "hold": hold}


# ═════════════ 工作 ═════════════
def cell_job(args):
    wn, fam, L, fq, N, how = args
    Wd = _G[wn]
    sel, short = select(Wd, fam, L, fq, N, how)
    res = MX.sim_book(sel, Wd, N)
    return {"世界": wn, "族": fam, "L": L, "頻率": fq, "N": N, "挑法": how, "池不足比例": short, **seg_row(Wd, res, sel, N)}


def fake_job(args):
    wn, fam, L, fq, N, r = args
    Wd = _G[wn]; months = FREQS[fq]
    rng = np.random.default_rng([20260928, {"甲": 1, "乙": 2}[fam], r])
    sel = {}
    for e in Wd["rebs"]:
        if months is not None and Wd["cal"][e].month not in months:
            continue
        R = Wd["RB"][e]
        pool = sorted(s for s in (R["el"] if fam == "甲" else R["pool"]) if s in R["TO"][L])
        sel[e] = list(rng.choice(pool, size=min(N, len(pool)), replace=False)) if pool else []
    res = MX.sim_book(sel, Wd, N)
    out = {"世界": wn, "族": fam, "r": r}
    for nm, (a, b) in Wd["segp"].items():
        c, m = R13.window_stats(res["eq"], 0, len(res["eq"]), a, b + 1); out[f"{nm}_年化"] = float(c); out[f"{nm}_回落"] = float(m)
    return out


def _xload(args):
    from backtest import researchSlip as SL
    sid, mk, data = args
    D.DATA = data
    return sid, SL.stock_extra(sid, mk, _G["xcal"], _G["xn"])


def hold_profile(Wd, res, sel, L, segs):
    """挑中格持股：20 日平均成交金額分位、60 日波動在當期 eligible 的分位、TO 分位。"""
    out = {}
    C = Wd["C"]; ix = Wd["ix"]
    for nm, (a, b) in segs.items():
        adv, vq, tq = [], [], []
        for e in [e for e in sorted(sel) if a <= e <= b]:
            H = res["hold"].get(e, [])
            if not H:
                continue
            el = Wd["RB"][e]["el"]
            vol = {}
            for s in el:
                seg = C[e - 61:e, ix[s]] if e >= 61 else None
                if seg is None:
                    continue
                with np.errstate(invalid="ignore", divide="ignore"):
                    rr = seg[1:] / seg[:-1] - 1.0
                rr = rr[np.isfinite(rr)]
                if len(rr) >= 40:
                    vol[s] = float(np.std(rr, ddof=1) * math.sqrt(245))
            vs = np.array(sorted(vol.values()))
            TOe = Wd["RB"][e]["TO"][L]; ts = np.array(sorted(TOe.values()))
            for s in H:
                z = Wd["VS"].get(s)
                if z is not None:
                    amt = z[2]; vv = Wd["P"][s]["valid"]
                    bb = np.flatnonzero(vv[:e])[-20:]
                    if len(bb) == 20:
                        adv.append(float(np.nanmean(amt[bb])))
                if s in vol and len(vs) > 1:
                    vq.append(float(np.searchsorted(vs, vol[s], side="left") / (len(vs) - 1)))
                if s in TOe and len(ts) > 1:
                    tq.append(float(np.searchsorted(ts, TOe[s], side="left") / (len(ts) - 1)))
        out[nm] = {"20日均額 p10／p50／p90（元）": [float(np.percentile(adv, q)) for q in (10, 50, 90)] if adv else None,
                   "60日波動分位 平均": float(np.mean(vq)) if vq else None, f"TO{L} 分位 平均": float(np.mean(tq)) if tq else None, "持股-期數": len(adv)}
    return out


def main():
    global LOGF
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report(); return
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    T0 = time.time()
    log(f"===== researchLowTO {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜procs {a.procs} reps {a.reps}｜停止交易強制出場：開｜換股簿依構造不截斷 =====")
    S = {"件": "PREREG低週轉 seq1（登錄 sha 47ac98f3c6b5fb02；裁定 seq268 §三）"}
    WM = world(MAINW, MAINW["data"], a.procs, log)
    WE = world(EARLYW, SHARES_E, a.procs, log)
    _G.update(M=WM, E=WE)
    D.DATA = MAINW["data"]
    S["0050"] = {**WM["B50"], **WE["B50"]}
    S["早年段實際窗"] = [str(WE["cal"][WE["w0"]].date()), str(WE["cal"][WE["w1"]].date())]
    # 閘：現實版函式全關 ＝ MX.sim_book
    sel0, _ = select(WM, "甲", 60, "月", 20)
    r0 = MX.sim_book(sel0, WM, 20); r1 = sim_book_x(sel0, WM, 20)
    S["閘"] = {"sim_book_x 全關 ＝ MX.sim_book（權益逐位元）": bool(np.array_equal(r0["eq"], r1["eq"]))}
    log(f"[閘] {S['閘']}")
    jobs = [(wn, fam, L, fq, N, "low") for wn in ("M", "E") for fam in ("甲", "乙") for L in LS for fq in FREQS for N in NS] + \
           [(wn, "乙", None, fq, N, "relvol") for wn in ("M", "E") for fq in FREQS for N in NS]
    t0 = time.time()
    with Pool(a.procs) as pool:
        R_ = pool.map(cell_job, jobs, chunksize=2)
    log(f"[格] {len(R_)}｜{time.time() - t0:.0f}s")
    T = pd.DataFrame(R_)
    key = lambda r: f"{r['族']}_{'量' if r['挑法'] == 'relvol' else 'L' + str(int(r['L']))}_{r['頻率']}_N{r['N']}"
    T["格"] = [key(r) for r in T.to_dict("records")]
    M_ = T[T["世界"] == "M"].set_index("格"); E_ = T[T["世界"] == "E"].set_index("格")
    PT = M_[[c for c in M_.columns if c.startswith(("探索", "確認")) or c in ("族", "L", "頻率", "N", "挑法", "池不足比例")]].join(
        E_[[c for c in E_.columns if c.startswith("早年")] + ["池不足比例"]].rename(columns={"池不足比例": "早年池不足比例"}))
    for sg in ("探索", "確認", "早年"):
        PT[f"{sg}_標籤"] = [label(c, m, S["0050"][sg]) for c, m in zip(PT[f"{sg}_年化"], PT[f"{sg}_回落"])]
    PT["退化"] = (PT["探索_持股"] < PT["N"] / 2) | (PT["探索_現金"] > 0.30)
    PT = PT.reset_index()
    picks = {}
    for fam in ("甲", "乙"):
        c_ = PT[(PT["族"] == fam) & (PT["挑法"] == "low") & ~PT["退化"]].copy()
        if not len(c_):
            picks[fam] = None; continue
        q = c_[c_["探索_標籤"] == "合格"] if (c_["探索_標籤"] == "合格").any() else c_
        q = q.assign(_f=q["頻率"].map(FORD))
        picks[fam] = q.sort_values(["探索_比值", "探索_年化", "_f", "N", "L"], ascending=[False, False, True, True, True]).iloc[0]["格"]
    S["退化（挑前排除）"] = PT.loc[PT["退化"], "格"].tolist(); S["挑中格"] = picks
    log(f"[挑格] {picks}｜退化 {S['退化（挑前排除）']}")
    PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    for wn, W_ in (("main", WM), ("early", WE)):
        W_["TOtab"].assign(日期=[str(W_["cal"][e].date()) for e in W_["TOtab"]["e"]]).to_csv(os.path.join(OUT, f"to_{wn}.csv.gz"), index=False, float_format="%.17g")
    # 判定、對照
    J = {}; FK = {}
    PTi = PT.set_index("格")
    X2 = pd.read_csv("backtest/resultsExt/x2_picks_monthly.csv.gz", dtype={"sid": str})
    x2 = {m: set(g["sid"]) for m, g in X2.groupby("換股月")}
    yl = pd.read_csv("backtest/resultsYLtrend/cells.csv").set_index("格").loc["營量v1"]
    SLX = {}
    for fam, pk in picks.items():
        if pk is None:
            continue
        r = PTi.loc[pk]; L = int(r["L"]); fq = r["頻率"]; N = int(r["N"])
        J[fam] = {"格": pk, "確認標籤": r["確認_標籤"], "早年標籤": r["早年_標籤"], "族標籤": max((r["確認_標籤"], r["早年_標籤"]), key=lambda x: MX.LORD[x])}
        with Pool(a.procs) as pool:
            FR = pd.DataFrame(pool.map(fake_job, [(wn, fam, L, fq, N, i) for wn in ("M", "E") for i in range(a.reps)], chunksize=8))
        FR.to_csv(os.path.join(OUT, f"fake_{fam}.csv.gz"), index=False, float_format="%.17g")
        FK[fam] = {}
        for sg, wn in (("探索", "M"), ("確認", "M"), ("早年", "E")):
            g = FR[FR["世界"] == wn]
            FK[fam][sg] = {"p（隨機年化 ≥ 本格）": float(np.mean(g[f"{sg}_年化"] >= r[f"{sg}_年化"])), "隨機年化中位": float(g[f"{sg}_年化"].median())}
        # 反向臂、挑中格明細
        det = {}
        for wn, W_ in (("M", WM), ("E", WE)):
            sel, _ = select(W_, fam, L, fq, N, "low"); res = MX.sim_book(sel, W_, N)
            selh, _ = select(W_, fam, L, fq, N, "high"); resh = MX.sim_book(selh, W_, N)
            det[wn] = {"持股輪廓": hold_profile(W_, res, sel, L, W_["segp"]), "逐年": years(W_, res["eq"]),
                       "反向臂（TO 最高）": seg_row(W_, resh, selh, N), "sel": sel, "res": res}
        J[fam]["反向臂（TO 最高 N 檔，描述）"] = {**{k: v for k, v in det["M"]["反向臂（TO 最高）"].items() if k.endswith(("年化", "回落"))},
                                          **{k: v for k, v in det["E"]["反向臂（TO 最高）"].items() if k.endswith(("年化", "回落"))}}
        J[fam]["持股輪廓"] = {**det["M"]["持股輪廓"], **det["E"]["持股輪廓"]}
        J[fam]["逐年報酬"] = {**det["M"]["逐年"], **det["E"]["逐年"]}
        J[fam]["換手與成本"] = {sg: [float(r[f"{sg}_換手"]), float(r[f"{sg}_成本年"])] for sg in ("探索", "確認", "早年")}
        ov = []
        for e in sorted(det["M"]["sel"]):
            H = det["M"]["res"]["hold"].get(e, [])
            m = str(WM["cal"][e].date())[:7]
            if H and m in x2:
                ov.append(len(set(H) & x2[m]) / len(H))
        J[fam]["與 X2 持股重疊率（主窗、同換股月、平均）"] = float(np.mean(ov)) if ov else None
        J[fam]["與 X2 比對換股期數"] = len(ov)
        if fam == "乙":
            rq = PTi.loc[f"乙_量_{fq}_N{N}"]
            J[fam]["同池 relvol 挑法（同頻率同 N）"] = {sg: [float(rq[f"{sg}_年化"]), float(rq[f"{sg}_回落"]), rq[f"{sg}_標籤"]] for sg in ("探索", "確認", "早年")}
            J[fam]["低週轉挑 − relvol 挑（年化點）"] = {sg: float(r[f"{sg}_年化"] - rq[f"{sg}_年化"]) for sg in ("探索", "確認", "早年")}
        SLX[fam] = (det, L, fq, N)
    S["判定"] = J; S["假訊號（同池隨機）"] = FK
    S["營量v1（T1，resultsYLtrend）"] = {sg: [float(yl[f"{sg}_年化"]), float(yl[f"{sg}_回落"])] for sg in ("探索", "確認", "早年")}
    try:
        q = json.load(open("backtest/resultsQual/summary.json", encoding="utf-8"))["挑格"]["乙"]
        S["品質乙族（resultsQual 挑中）"] = {"格": q.get("格"), **{sg: [q[sg]["年化"], q[sg]["回落"]] for sg in ("探索", "確認", "早年") if sg in q}}
    except Exception as ex:                                              # noqa: BLE001
        S["品質乙族（resultsQual 挑中）"] = f"讀不到：{ex}"
    # 現實版（主、早年；挑中格）
    arms = {"現實版（C1 0.3%＋C2 50 萬＋C4）": dict(s=SLIP, cap=CAP, c4=True), "現實版＋C5 低消 20 元": dict(s=SLIP, cap=CAP, c4=True, m5=20)}
    REAL = {}
    for wn, W_, data in (("M", WM, MAINW["data"]), ("E", WE, EARLYW["data"])):
        need = sorted(set().union(*[set(s for v in det_[wn]["sel"].values() for s in v) for det_, *_ in SLX.values()])) if SLX else []
        stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
        _G.update(xcal=W_["cal"], xn=W_["n"])
        with Pool(a.procs) as pool:
            X = dict(pool.map(_xload, [(s, stocks.get(s, "twse"), data) for s in need], chunksize=8))
        D.DATA = data
        for fam, (det_, L, fq, N) in SLX.items():
            sel = det_[wn]["sel"]
            for arm, sp in arms.items():
                rr = sim_book_x(sel, W_, N, X, sp)
                for nm, (a_, b_) in W_["segp"].items():
                    c, m = R13.window_stats(rr["eq"], 0, len(rr["eq"]), a_, b_ + 1)
                    REAL.setdefault(f"{fam}｜{arm}", {})[nm] = [float(c), float(m), label(float(c), float(m), S["0050"][nm])]
    D.DATA = MAINW["data"]
    S["現實版（挑中格；描述）"] = REAL
    log(f"[現實版] {REAL}")
    # 新規矩 ③
    trig = any(J[f]["確認標籤"] in ("合格", "另列") or J[f]["早年標籤"] in ("合格", "另列") for f in J)
    S["新規矩③"] = "要跑" if trig else "不適用（兩族挑中格確認、早年皆非合格／另列）"
    if trig:
        SENS = {}
        for fam, (det_, L, fq, N) in SLX.items():
            for wn, W_, data in (("M", WM, MAINW["data"]), ("E", WE, EARLYW["data"])):
                sel = det_[wn]["sel"]
                ra = MX.sim_book(sel, W_, N, mode="all")
                sids = sorted(set(s for v in sel.values() for s in v))
                rb = MX.sim_book(sel, W_, N, ma_stop=MX.ma_table(W_, sids))
                for vn, rr in (("(a) 全賣全買", ra), ("(b) 跌破 MA60 次日開盤賣", rb)):
                    for nm, (a_, b_) in W_["segp"].items():
                        c, m = R13.window_stats(rr["eq"], 0, len(rr["eq"]), a_, b_ + 1)
                        SENS.setdefault(f"{fam}｜{vn}", {})[nm] = [float(c), float(m)]
        S["新規矩③ 描述"] = SENS
    S["秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for fam, (det_, *_r) in SLX.items():
        rows = [(wn, str(W_["cal"][e].date()), s) for wn, W_ in (("M", WM), ("E", WE)) for e, H in det_[wn]["res"]["hold"].items() for s in H]
        pd.DataFrame(rows, columns=["世界", "換股日", "sid"]).to_csv(os.path.join(OUT, f"holdings_{fam}.csv.gz"), index=False)
        rows = [(wn, str(W_["cal"][e].date()), i, s) for wn, W_ in (("M", WM), ("E", WE)) for e, L_ in det_[wn]["sel"].items() for i, s in enumerate(L_)]
        pd.DataFrame(rows, columns=["世界", "換股日", "名次", "sid"]).to_csv(os.path.join(OUT, f"sel_{fam}.csv.gz"), index=False)
    report()
    bad = not S["閘"]["sim_book_x 全關 ＝ MX.sim_book（權益逐位元）"]
    log(f"[完] {S['秒']}s｜閘 {'不過' if bad else '過'}")
    if bad:
        raise SystemExit("⛔ 閘不過")


def _p(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.2f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    PT = pd.read_csv(os.path.join(OUT, "cells.csv")).set_index("格")
    J = S["判定"]; B = S["0050"]
    L_ = ["# PREREG低週轉 seq1（低週轉選股：單用／營收創高池內）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 sha 47ac98f3c6b5fb02；裁定 seq268 §三（N ＋1）。回測線。"
          "⭐ 停止交易強制出場：開；換股簿按期換、窗尾照市值 ⇒ 依構造不因資料尾截斷（t1_censor 不適用）。引用請寫「回測 PREREG低週轉」。", ""]
    parts = []
    for fam in ("甲", "乙"):
        if fam not in J:
            continue
        j = J[fam]; r = PT.loc[j["格"]]
        rl = S["現實版（挑中格；描述）"].get(f"{fam}｜現實版＋C5 低消 20 元", {})
        parts.append(f"{fam}族挑中 {j['格']}：確認 {_p(r['確認_年化'])}（{j['確認標籤']}）、早年 {_p(r['早年_年化'])}（{j['早年標籤']}）⇒ {j['族標籤']}；"
                     f"現實版＋C5 確認 {_p(rl.get('確認', [None])[0])}；與 X2 持股重疊 {j['與 X2 持股重疊率（主窗、同換股月、平均）'] * 100:.1f}%" if j['與 X2 持股重疊率（主窗、同換股月、平均）'] is not None else "")
    L_.append("**結論：" + "；".join(parts) + f"。0050 確認 {_p(B['確認']['cagr'])}、早年 {_p(B['早年']['cagr'])}。**")
    L_ += ["", "| | 探索 | 確認 | 早年 | 族標籤 |", "|---|---|---|---|---|"]
    for fam in ("甲", "乙"):
        if fam in J:
            r = PT.loc[J[fam]["格"]]
            L_.append(f"| {fam} {J[fam]['格']} | {_p(r['探索_年化'])}／{_p(r['探索_回落'])} | {_p(r['確認_年化'])}／{_p(r['確認_回落'])}（{r['確認_標籤']}） | "
                      f"{_p(r['早年_年化'])}／{_p(r['早年_回落'])}（{r['早年_標籤']}） | {J[fam]['族標籤']} |")
            fk = S["假訊號（同池隨機）"][fam]
            L_.append(f"| {fam} 同池隨機 p | {fk['探索']['p（隨機年化 ≥ 本格）']:.3f} | {fk['確認']['p（隨機年化 ≥ 本格）']:.3f} | {fk['早年']['p（隨機年化 ≥ 本格）']:.3f} | |")
    v = S["營量v1（T1，resultsYLtrend）"]
    L_.append(f"| 營量 v1（T1） | {_p(v['探索'][0])}／{_p(v['探索'][1])} | {_p(v['確認'][0])}／{_p(v['確認'][1])} | （早年窗 2012-06～2014-12）{_p(v['早年'][0])} | |")
    L_.append(f"| 0050 | {_p(B['探索']['cagr'])}／{_p(B['探索']['mdd'])} | {_p(B['確認']['cagr'])}／{_p(B['確認']['mdd'])} | {_p(B['早年']['cagr'])}／{_p(B['早年']['mdd'])} | |")
    L_ += ["", "## 一、36 格（＋乙族同池 relvol 挑法 6 格，描述）", "",
           "| 格 | 探索 年化／回落（比值） | 探索 持股／現金 | 確認 年化／回落 | 確認標籤 | 早年 年化／回落 | 早年標籤 | 換手／成本年（確認） | 退化 |", "|---|---|---|---|---|---|---|---|---|"]
    for k, r in PT.iterrows():
        L_.append(f"| {k} | {_p(r['探索_年化'])}／{_p(r['探索_回落'])}（{r['探索_比值']:.3f}） | {r['探索_持股']:.1f}／{r['探索_現金'] * 100:.0f}% | {_p(r['確認_年化'])}／{_p(r['確認_回落'])} | "
                  f"{r['確認_標籤']} | {_p(r['早年_年化'])}／{_p(r['早年_回落'])} | {r['早年_標籤']} | {r['確認_換手']:.2f}／{r['確認_成本年'] * 100:.2f}% | {'是' if r['退化'] else ''} |")
    L_ += ["", f"- 退化（挑前排除）：{S['退化（挑前排除）']}；挑中：{S['挑中格']}", ""]
    for fam in ("甲", "乙"):
        if fam not in J:
            continue
        L_ += [f"## 二{'甲乙'.index(fam) + 1}、{fam}族挑中格必報", "", "```", json.dumps({k: v for k, v in J[fam].items() if k != "格"}, ensure_ascii=False, indent=1), "```", ""]
    L_ += ["## 三、現實版（挑中格；描述）", "", "```", json.dumps(S["現實版（挑中格；描述）"], ensure_ascii=False, indent=1), "```", "",
           "## 四、新規矩 ③", "", str(S["新規矩③"]), ""]
    if S.get("新規矩③ 描述"):
        L_ += ["```", json.dumps(S["新規矩③ 描述"], ensure_ascii=False, indent=1), "```", ""]
    L_ += ["## 五、對照與閘", "", f"- 品質乙族：{json.dumps(S['品質乙族（resultsQual 挑中）'], ensure_ascii=False)}",
           f"- 閘：{json.dumps(S['閘'], ensure_ascii=False)}", f"- 早年段實際窗：{S['早年段實際窗']}",
           "- 「穩」照 seq253 收緊讀法（組合層本表不寫「穩」）；先驗見登錄 §五", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")
    print(L_[4])


if __name__ == "__main__":
    main()

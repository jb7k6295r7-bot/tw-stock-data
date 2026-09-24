# -*- coding: utf-8 -*-
"""PREREGH2（144／200MA 雙翻揚：20 日內觸及 ×1.3）——回測線落地。判準＝台股策略線 PREREGH2 seq2（sha 239b4fac2cd6b856）。

資料（§二①）：main commit edc6f8002fed8803795e3486ad57db513f7e9f65 的 data/stocks、data/adj、data/meta
   ⇒ 用 `git archive` 取到 ~/h2data/<sha>/data（唯讀；⛔ 不讀「跑的那天的 main」）；本程式把 backtest.data.DATA 指到那裡
母體（§二②）：data.load_universe 同條件（上市＋上櫃普通股、含已下市）⇒ gate3（排除 -DR、排除 -創，依名稱）
還原價（§二③）：backtest/data.py load_stock（價 × F(d)）；漲跌停＝ tradability.one（原始價、tick、2015-06-01 前 7%／後 10%）

⭐ 登錄沒逐字寫、本線的落地讀法（⛔ 在看任何結果之前寫在這裡；交件逐條列出）：
 R1 均線、「t−1」、「t−5」一律在【該股自己的有效 K 棒序列】上數（技術指標慣例；research11.load_bars 同）；
    T+1、t+20、判定窗、20 日區段一律用【交易日曆】（「t+1 停牌 ⇒ 不成交」只在日曆上才可能發生）
 R2 訊號需要 MA200(t−5) ⇒ 實際至少 205 根有效 K 棒；資格「至少 200 根」照寫，前者自然更嚴
 R3 硬斷點＝ ① 價格：相鄰有效 K 棒 close 比 ≤ 0.55 或 ≥ 1.8、且 (前一根, 這一根] 內無 data/adj 事件（data.breakpoints 的價格規則）
            ② 時間：窗內有連續 ≥ 5 個交易日無有效 K 棒（登錄字面，⛔ 不帶 data.breakpoints 的 500 張流動性前提）
    斷點落在窗內 ＝ ① 的斷點日（復牌那根）落在窗內；② 的 5 個缺日全在窗內
 R4 資格分兩截：t 日可知的部分（≥ 200 根、[t−199, t] 無斷點、vol60 可算）決定【候選池】；
    (t, t+20] 無斷點是抽到之後才查（⇒ §七⑧ 訊號與對照分開報），不成立 ⇒ 該事件／該抽剔除、⛔ 不補抽
 R5 合併：依時間逐一走；若 t 落在「上一個被保留事件 t0」的 (t0, t0+20] ⇒ 合併掉；被剔除（斷點／不成交）的事件不開合併窗
 R6 「t 日沒有觸發訊號」＝ 原始訊號條件在 t 為假（不論該事件後來是否被合併或剔除）
 R7 vol60 ＝ [t−59, t] 內有效 K 棒的日報酬（對前一根有效 K 棒）標準差 ddof=1；五分位＝ t 日資格母體（R4 前半）內 rank 後等分 5 組
 R8 非重疊 SE ＝ 以判定窗起點切的 20 交易日區段為單位：區段內 d_e 平均 ⇒ 區段平均的標準差／√區段數
 R9 對照組達成筆數 ＝ 所有實際成交的對照抽樣中 hit＝1 的筆數
 R10 g（20 日報酬）：close 取 ≤ t+20 最後一根有效 K 棒（下市者即最後成交價，delist 規則）
"""
from __future__ import annotations
import os, sys, time, json
from multiprocessing import Pool
import numpy as np
import pandas as pd

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
H2D = os.path.expanduser(f"~/h2data/{SHA}/data")
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
D.DATA = H2D                                    # ⭐ 一律讀釘住的快照
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import research11 as R

OUT = "backtest/resultsH2"
W0, W1 = "2017-03-02", "2026-08-24"
WIN_DAYS = 2313
SEED = 20260925
M_CTRL = 10
MAS = (120, 144, 200, 240)
COMBOS = {"main": (144, 200, 5), "a_k1": (144, 200, 1), "a_k10": (144, 200, 10), "b_120_240": (120, 240, 5)}
COST_RT = 0.00585

_G = {}


def _init(cal):
    _G["cal"] = cal


def load_one(args):
    sid, market = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c)
    bars = np.flatnonzero(valid)
    if len(bars) < 206:
        return None
    cb = c[bars]
    ma = {}
    for m in MAS:
        mb = pd.Series(cb).rolling(m, min_periods=m).mean().to_numpy()
        ma[m] = mb
    sig = {}
    for key, (a, b, k) in COMBOS.items():
        ua = np.zeros(len(bars), bool); ub = np.zeros(len(bars), bool)
        ua[k:] = ma[a][k:] > ma[a][:-k]; ub[k:] = ma[b][k:] > ma[b][:-k]
        mx = np.fmax(ma[a], ma[b]); mx[np.isnan(ma[a]) | np.isnan(ma[b])] = np.nan
        above = cb >= mx
        s = np.zeros(len(bars), bool)
        s[1:] = ua[1:] & ub[1:] & above[1:] & (cb[:-1] < mx[:-1])
        s &= np.isfinite(mx); s[1:] &= np.isfinite(mx[:-1])
        cal_s = np.zeros(n, bool); cal_s[bars] = s
        sig[key] = cal_s
        if key == "main":
            state = ua & ub & above & np.isfinite(mx)      # 續抱條件＝進場條件的狀態部分（描述臂 f）
            st_cal = np.zeros(n, bool); st_cal[bars] = state
    mn = np.full(n, np.nan); mn[bars] = np.fmin(ma[144], ma[200]); mn[bars[np.isnan(ma[144]) | np.isnan(ma[200])]] = np.nan
    # vol60（R7）
    rb = np.full(n, np.nan); rb[bars[1:]] = cb[1:] / cb[:-1] - 1.0
    vol = pd.Series(rb).rolling(60, min_periods=2).std(ddof=1).to_numpy()
    nb = np.cumsum(valid)
    # 硬斷點（R3）
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        r_ = r_ + 1 if not valid[i] else 0
        run[i] = r_
    g5 = run >= 5                                        # d 為「連續缺 5 日」的第 5 天以後
    tb = TR.one(sid, cal)
    return {"sid": sid, "o": o, "h": h, "c": c,
            "valid": valid, "nb": nb.astype(np.int32), "vol": vol, "mn": mn,
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32),
            "trd": tb["trd"], "up_o": tb["up_o"], "state": st_cal, **{"sig_" + k: v for k, v in sig.items()}}


def _cnt(cs, a, b):
    """cs 的區間 [a, b] 內 True 的個數（a>b ⇒ 0）。"""
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def brk(S, a, b):
    """[a, b] 內有沒有硬斷點（R3）。"""
    return _cnt(S["cs_pb"], a, b) > 0 or _cnt(S["cs_g5"], a + 4, b) > 0


def elig_t(S, t):
    """R4 前半：t 日可知的資格。"""
    return bool(S["valid"][t]) and S["nb"][t] >= 200 and not brk(S, t - 199, t) and np.isfinite(S["vol"][t])


def outcome(S, t, H, P_mn=True):
    """(t) 事件在 H 的結果；回 None ⇒ 未來窗斷點（'brk'）或不成交（'halt'／'limit'）。"""
    if brk(S, t + 1, t + H):
        return "brk"
    if not S["trd"][t + 1] or not np.isfinite(S["o"][t + 1]):
        return "halt"
    if S["up_o"][t + 1]:
        return "limit"
    P0 = float(S["o"][t + 1])
    hh = S["h"][t + 1:t + H + 1]; mx = float(np.nanmax(hh)) if np.isfinite(hh).any() else np.nan
    cc = S["c"][t + 1:t + H + 1]; vi = np.flatnonzero(np.isfinite(cc))
    cH = float(cc[vi[-1]]) if len(vi) else np.nan
    mn = float(S["mn"][t])
    return {"P0": P0, "hit": ge13(mx, P0), "g": cH / P0 - 1.0,
            "hit_lit": ge13(mx, mn) if np.isfinite(mn) else np.nan, "r": P0 / mn if np.isfinite(mn) else np.nan}


def ge13(mx, base):
    """mx ≥ 1.3 × base；⚠ 1.3×10 在浮點是 13.000000000000002 ⇒ 相對容差 1e-12，⛔ 否則恰好等於的會被判沒碰到。"""
    return int(np.isfinite(mx) and mx >= 1.3 * base * (1 - 1e-12))


def selftest():
    """⭐ 先證明會響：斷點（價格／連續缺 5 日的窗邊界）、hit 恰好 1.3 倍、不成交三種。"""
    n = 60
    pb = np.zeros(n, bool); pb[10] = True
    valid = np.ones(n, bool); valid[20:25] = False
    run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        r_ = r_ + 1 if not valid[i] else 0; run[i] = r_
    S = {"cs_pb": np.cumsum(pb), "cs_g5": np.cumsum(run >= 5)}
    assert brk(S, 5, 15) and not brk(S, 11, 19)
    assert brk(S, 18, 26) and not brk(S, 21, 26), "⛔ 窗內只有 4 個缺日不算"
    o = np.full(n, 10.0); h = np.full(n, 10.0); c = np.full(n, 10.0); h[35] = 13.0
    S2 = {"cs_pb": np.zeros(n, int), "cs_g5": np.zeros(n, int), "trd": np.ones(n, bool), "up_o": np.zeros(n, bool),
          "o": o, "h": h, "c": c, "mn": np.full(n, 10.0)}
    r = outcome(S2, 30, 20)
    assert r["hit"] == 1 and r["hit_lit"] == 1, "⛔ 恰好 1.3 倍要算碰到"
    h[35] = 12.99; assert outcome(S2, 30, 20)["hit"] == 0
    S2["up_o"] = np.zeros(n, bool); S2["up_o"][31] = True; assert outcome(S2, 30, 20) == "limit"
    S2["up_o"][31] = False; S2["trd"] = np.ones(n, bool); S2["trd"][31] = False; assert outcome(S2, 30, 20) == "halt"
    S2["trd"][31] = True; S2["cs_pb"] = np.cumsum(np.eye(1, n, 40, dtype=bool)[0]); assert outcome(S2, 30, 20) == "brk"
    assert outcome(S2, 30, 5) != "brk", "⛔ 斷點在窗外不該擋"
    print("✅ 自測：斷點窗邊界、恰好 1.3 倍、漲停開／停牌／未來斷點 三種剔除 ⇒ 都會響")


# ═════════════ 事件、對照、統計 ═════════════
class Ctx:
    def __init__(self, ST, cal, w0, w1):
        self.ST = ST; self.cal = cal; self.w0 = w0; self.w1 = w1
        self.sids = sorted(ST)
        self._pool = {}

    def day(self, t, sigkey):
        """t 日資格母體（R4 前半）⇒ (sids, vol, 五分位, 原始訊號)。"""
        k = (t, sigkey)
        if k not in self._pool:
            ss, vv, sg = [], [], []
            for s in self.sids:
                S = self.ST[s]
                if elig_t(S, t):
                    ss.append(s); vv.append(float(S["vol"][t])); sg.append(bool(S["sig_" + sigkey][t]))
            vv = np.array(vv)
            q = pd.qcut(pd.Series(vv).rank(method="first"), 5, labels=False).to_numpy() if len(vv) >= 5 else np.zeros(len(vv), int)
            self._pool[k] = (ss, vv, q, np.array(sg))
        return self._pool[k]


def build_events(C: Ctx, sigkey, H):
    """原始觸發 ⇒ 依時間走、合併（R5）、資格（R4）、成交 ⇒ 保留事件；回 (保留事件列表, 帳)。"""
    acc = {"原始觸發": 0, "合併掉": 0, "樣本不足或過去斷點": 0, "未來窗斷點": 0, "不成交_停牌": 0, "不成交_漲停開": 0}
    ev = []
    for s in C.sids:
        S = C.ST[s]
        ts = np.flatnonzero(S["sig_" + sigkey][C.w0:C.w1 - H + 1]) + C.w0
        acc["原始觸發"] += len(ts)
        t0 = -10 ** 9
        for t in ts:
            if t0 < t <= t0 + 20:
                acc["合併掉"] += 1; continue
            if not elig_t(S, t):
                acc["樣本不足或過去斷點"] += 1; continue
            o = outcome(S, t, H)
            if o == "brk":
                acc["未來窗斷點"] += 1; continue
            if o == "halt":
                acc["不成交_停牌"] += 1; continue
            if o == "limit":
                acc["不成交_漲停開"] += 1; continue
            ev.append({"sid": s, "t": int(t), **o}); t0 = t
    ev.sort(key=lambda e: (e["t"], e["sid"]))
    return ev, acc


def draw_controls(C: Ctx, ev, sigkey, H, seed, by_vol=True, m=M_CTRL):
    """每事件抽 m 檔對照（§五）；回 每事件的對照結果列表＋帳。"""
    rng = np.random.default_rng(seed)
    acc = {"池不足10": 0, "對照_未來窗斷點": 0, "對照_t+1停牌": 0, "對照_漲停開": 0, "無對照成交而剔除": 0, "對照抽樣數": 0}
    out = []
    for e in ev:
        ss, vv, q, sg = C.day(e["t"], sigkey)
        i = ss.index(e["sid"]) if e["sid"] in ss else None
        if i is None:
            out.append((e, [], [], [])); continue
        msk = ~sg
        if by_vol:
            msk &= q == q[i]
        pool = [ss[j] for j in np.flatnonzero(msk) if ss[j] != e["sid"]]
        if len(pool) < m:
            acc["池不足10"] += 1
        pick = list(rng.choice(pool, size=min(m, len(pool)), replace=False)) if pool else []
        res = []
        for s in pick:
            acc["對照抽樣數"] += 1
            o = outcome(C.ST[s], e["t"], H)
            if o == "brk":
                acc["對照_未來窗斷點"] += 1; continue
            if o == "halt":
                acc["對照_t+1停牌"] += 1; continue
            if o == "limit":
                acc["對照_漲停開"] += 1; continue
            res.append(o)
        if not res:
            acc["無對照成交而剔除"] += 1
        out.append((e, res, pool, pick))
    return out, acc


def judge(C: Ctx, pairs, H, key="hit"):
    """§六：d_e、D、月分群 CI、非重疊 SE、n_eff、出口與結果。"""
    rows = []
    for e, res, _, _ in pairs:
        if not res:
            continue
        ce = np.array([r[key] for r in res], float)
        if key == "hit_lit" and (not np.isfinite(e[key]) or not np.isfinite(ce).any()):
            continue
        rows.append({"t": e["t"], "sid": e["sid"], "sig": float(e[key]), "ctl": float(np.nanmean(ce)),
                     "ctl_hits": int(np.nansum(ce)) if key != "g" else 0, "n_ctl": int(np.isfinite(ce).sum())})
    X = pd.DataFrame(rows)
    if X.empty:
        return {"n": 0}, X
    X["d"] = X["sig"] - X["ctl"]
    X["month"] = [str(C.cal[t])[:7] for t in X["t"]]
    X["block"] = (X["t"] - C.w0) // H
    cs = R.cl_stats(X["d"].to_numpy(float), X["month"].to_numpy())
    bm = X.groupby("block")["d"].mean()
    se_blk = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    n_ev, n_blk = len(X), int(X["block"].nunique())
    n_eff = min(n_ev, n_blk)
    sig_hits = int(X["sig"].sum()) if key != "g" else None
    ctl_hits = int(X["ctl_hits"].sum()) if key != "g" else None
    out = {"n": n_ev, "D": cs["mean"], "lo": cs["lo"], "hi": cs["hi"], "se_月": cs["se"], "months": cs["months"],
           "se_非重疊": se_blk, "lo_非重疊": cs["mean"] - 1.96 * se_blk, "hi_非重疊": cs["mean"] + 1.96 * se_blk,
           "n_blocks": n_blk, "n_eff": n_eff, "n_eff_尺度": "事件數" if n_ev <= n_blk else "20日區段數",
           "訊號達成": sig_hits, "訊號分母": n_ev, "對照達成": ctl_hits, "對照分母": int(X["n_ctl"].sum()),
           "訊號達成率": X["sig"].mean(), "對照達成率": (X["ctl"] * X["n_ctl"]).sum() / X["n_ctl"].sum()}
    if key in ("hit", "hit_lit"):
        if n_eff < 30 or sig_hits < 30 or ctl_hits < 30:
            out["出口"] = "出口①"; out["結果"] = "—（出口①：樣本不足以分辨）"
        else:
            out["出口"] = "出口②" if n_eff < 100 else "出口③"
            if cs["lo"] <= 0 <= cs["hi"]:
                out["結果"] = "結果①（測不出）"
            else:
                out["結果"] = "結果②（測得出（＋））" if cs["mean"] > 0 else "結果③（測得出（−））"
    return out, X


def fake_arm(C: Ctx, ev, pairs, sigkey, H, r):
    """§九：每事件從自己的對照池另抽 1 檔當訊號（排除已抽到的對照），同一套重抽 10 檔對照 ⇒ D、CI。"""
    rng = np.random.default_rng(SEED + r)
    fev = []
    for e, res, pool, pick in pairs:
        drawn = set(pick)
        cand = [s for s in pool if s not in drawn]
        if not cand:
            continue
        f = str(rng.choice(cand))
        o = outcome(C.ST[f], e["t"], H)
        if isinstance(o, dict):
            fev.append({"sid": f, "t": e["t"], **o})
    fev.sort(key=lambda x: (x["t"], x["sid"]))
    fp, _ = draw_controls(C, fev, sigkey, H, SEED + r)
    js, _ = judge(C, fp, H)
    return js


def rolling_arm(C: Ctx, pairs, w1):
    """描述臂 f：每 20 交易日檢查點收盤判續抱條件（狀態部分），不符 ⇒ 次日開盤出；hit ＝ 持有期間最高價曾達 1.3×P0。
    對照：與配對事件同長度。⚠ 續抱期間超過 t+20 的部分不再查硬斷點（描述臂，簡化照寫）。"""
    rows = []
    for e, res, pool, pick in pairs:
        if not res:
            continue
        S = C.ST[e["sid"]]; t = e["t"]; cp = t + 20
        while cp + 20 <= w1:
            vi = np.flatnonzero(S["valid"][t + 1:cp + 1])
            ok = bool(S["state"][t + 1 + vi[-1]]) if len(vi) else False
            if not ok:
                break
            cp += 20
        L = cp - t
        def hit_L(S2, P0):
            hh = S2["h"][t + 1:t + L + 1]
            return int(np.nanmax(hh) >= 1.3 * P0) if np.isfinite(hh).any() else 0
        hs = hit_L(S, e["P0"])
        hc = [hit_L(C.ST[s], float(C.ST[s]["o"][t + 1])) for s in pick
              if np.isfinite(C.ST[s]["o"][t + 1]) and C.ST[s]["trd"][t + 1] and not C.ST[s]["up_o"][t + 1] and not brk(C.ST[s], t + 1, t + 20)]
        if hc:
            rows.append({"t": t, "L": L, "sig": hs, "ctl": float(np.mean(hc))})
    X = pd.DataFrame(rows)
    X["d"] = X["sig"] - X["ctl"]; X["month"] = [str(C.cal[t])[:7] for t in X["t"]]
    cs = R.cl_stats(X["d"].to_numpy(float), X["month"].to_numpy())
    keep = float((X["L"] > 20).mean())
    flag = "近似買進持有" if keep > 0.9 else ("近似固定 H＝20" if keep <= 0.1 else "—")
    return {"n": len(X), "D": cs["mean"], "lo": cs["lo"], "hi": cs["hi"], "續抱率": keep, "平均持有天數": float(X["L"].mean()), "旗標": flag}


def qstats(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return {"中位": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90))} if len(x) else {}


def main():
    selftest()
    t0 = time.time()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 4
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--fake") + 1]) if "--fake" in sys.argv else 30
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS, (cal[w0], cal[w1], w1 - w0 + 1)
    stocks = pd.read_csv(os.path.join(H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    print("[資料] 快照 {}｜日曆 {} 根、尾 {}｜判定窗 [{}, {}] {} 日｜gate3 母體 {:,} 檔".format(SHA[:10], n, cal[-1].date(), W0, W1, WIN_DAYS, len(U)), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal,)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=16)
    ST = {r["sid"]: r for r in res if r is not None}
    print("[讀檔] 可用 {:,} 檔（有效 K 棒 ≥ 206）｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    C = Ctx(ST, cal, w0, w1)
    os.makedirs(OUT, exist_ok=True)
    R_ = {"快照": SHA, "gate3母體": len(U), "可用檔數": len(ST)}
    # ── 主格
    ev, acc = build_events(C, "main", 20)
    pairs, cacc = draw_controls(C, ev, "main", 20, SEED)
    js, X = judge(C, pairs, 20)
    X.to_csv(os.path.join(OUT, "main_events.csv"), index=False)
    R_["①事件帳"] = {**acc, "保留事件": len(ev), "相異檔數": len({e["sid"] for e in ev}), "合併佔比": acc["合併掉"] / max(1, acc["原始觸發"])}
    rr = [e["r"] for e in ev]
    R_["②白拿段"] = {"r": qstats(rr), "1.3/r−1": qstats([1.3 / x - 1 for x in rr if np.isfinite(x)])}
    R_["③判定"] = js
    nct = [len(p[1]) for p in pairs]
    R_["④對照"] = {**cacc, "每事件成交對照數分佈": pd.Series(nct).value_counts().sort_index().to_dict(), "成交對照 < 10 的事件": int(sum(1 for x in nct if x < 10))}
    # ⑧ 未來窗排除比例（訊號 vs 對照，分開）
    den_s = acc["未來窗斷點"] + acc["不成交_停牌"] + acc["不成交_漲停開"] + len(ev)
    ps = (acc["未來窗斷點"] + acc["不成交_停牌"]) / max(1, den_s)
    pc = (cacc["對照_未來窗斷點"] + cacc["對照_t+1停牌"]) / max(1, cacc["對照抽樣數"])   # ⭐ 與訊號同口徑：斷點＋停牌（漲停開另列、不算）
    R_["⑧未來窗排除"] = {"訊號_斷點": acc["未來窗斷點"], "訊號_t+1停牌": acc["不成交_停牌"], "訊號分母": den_s, "訊號比例": ps,
                      "對照_斷點": cacc["對照_未來窗斷點"], "對照_t+1停牌": cacc["對照_t+1停牌"], "對照_漲停開(不算)": cacc["對照_漲停開"], "對照分母": cacc["對照抽樣數"], "對照比例": pc,
                      "相差逾兩倍": bool(max(ps, pc) > 2 * min(ps, pc)) if min(ps, pc) > 0 else bool(max(ps, pc) > 0)}
    # ⑦ 逐年、市場
    mk = U.set_index("stock_id")["market"]
    R_["⑦分佈"] = {"逐年": pd.Series([str(cal[e["t"]].year) for e in ev]).value_counts().sort_index().to_dict(),
                  "市場": pd.Series([mk.get(e["sid"]) for e in ev]).value_counts().to_dict()}
    print("[主格] 保留事件 {:,}｜D {:+.4f}（CI {:+.4f}～{:+.4f}）｜{} {}｜{:.0f}s".format(len(ev), js.get("D", np.nan), js.get("lo", np.nan), js.get("hi", np.nan), js.get("出口"), js.get("結果"), time.time() - t0), flush=True)
    # ── ⑤ 假訊號臂
    fk = []
    for r in range(1, reps + 1):
        fj = fake_arm(C, ev, pairs, "main", 20, r)
        fk.append({"r": r, "n": fj.get("n"), "D": fj.get("D"), "lo": fj.get("lo"), "hi": fj.get("hi"),
                   "判過": bool(fj.get("n", 0) and not (fj["lo"] <= 0 <= fj["hi"]))})
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "fake_arm.csv"), index=False)
    R_["⑤假訊號臂"] = {"判過": int(FK["判過"].sum()), "次數": reps}
    print("[假訊號臂] 判過 {}／{}｜{:.0f}s".format(int(FK["判過"].sum()), reps, time.time() - t0), flush=True)
    # ── ⑥ 描述臂
    dsc = {}
    for key in ("a_k1", "a_k10", "b_120_240"):
        e2, a2 = build_events(C, key, 20); p2, _ = draw_controls(C, e2, key, 20, SEED); j2, _ = judge(C, p2, 20)
        dsc[key] = {"事件帳": {**a2, "保留事件": len(e2)}, "判定形": j2}
    for H in (60, 120):
        e2, a2 = build_events(C, "main", H); p2, _ = draw_controls(C, e2, "main", H, SEED); j2, _ = judge(C, p2, H)
        dsc[f"c_H{H}"] = {"降級理由": "結構上不可得（⌊2313／{}⌋＝{}）".format(H, WIN_DAYS // H), "事件帳": {**a2, "保留事件": len(e2)}, "判定形": j2}
    jd, _ = judge(C, pairs, 20, key="hit_lit"); dsc["d_原說法字面"] = {"判定形": jd}
    pe, _ = draw_controls(C, ev, "main", 20, SEED, by_vol=False); je, _ = judge(C, pe, 20); dsc["e_只對日期"] = {"判定形": je}
    dsc["f_滾動續抱"] = rolling_arm(C, pairs, w1)
    jg, Xg = judge(C, pairs, 20, key="g")
    dsc["g_20日報酬"] = {"訊號毛": float(Xg["sig"].mean()), "對照毛": float(Xg["ctl"].mean()),
                       "訊號淨": float(Xg["sig"].mean() - COST_RT), "對照淨": float(Xg["ctl"].mean() - COST_RT),
                       "差": jg.get("D"), "差_CI": [jg.get("lo"), jg.get("hi")]}
    R_["⑥描述臂"] = dsc
    json.dump(R_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

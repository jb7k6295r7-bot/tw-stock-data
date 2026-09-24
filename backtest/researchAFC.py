# -*- coding: utf-8 -*-
"""本批 A／F／C（台股策略線 PREREGA／F／C seq2）——回測線落地。三件共用：main edc6f8002f 快照、一次 W1 同資料重跑、同一組 1,000 顆種子。

共同設定（登錄逐字）：W1 ＝ P12 (S1, C1, T1)：rule H120、n_slots 8、pick=None、d_max=None、queue_days=0、cash_mode="zero"；
   新跑件：gate3（面板已在 gate3 內建，researchAFC_panel.py）＋ tradable（漲跌停／停牌新參數）＋ delist on（3b6437307c+）
判定窗 2017-03-02～2026-08-24（P12.win_bounds「全窗」）；判準＝年化、最大回落兩腳都不輸 0050、至少一腳嚴格優。

⭐ 落地讀法（⛔ 看任何結果前寫在這裡；交件逐條列出）：
 S1 訊號表：P7.build_sig_gate_b 在新面板上建（同一支）；⛔ 不斷言舊的七個驗收數（資料換了、數字本來就會變）⇒ 改報新數
 價格：D.load_stock 讀快照（⛔ 不用 researchp1.load_prices —— 它會讀分支舊快照的 closes.npz 快取）；closes ffill、opens 原樣（同 P1 的做法）
 0050 同窗：同一條 window_stats 路徑算 0050 買進持有 ⇒ 對登錄寫的 +24.02%／−33.96% 當錨（對不上就停、回報）
 A vol60：以訊號日 T（＝ entry_pos − 1）為最後一根，該股【有效 K 棒】上最近 61 個還原收盤 ⇒ 60 個日報酬 ⇒ 標準差 ddof=1；不足 ⇒ NaN
 C 月報酬：各股與 0050 的月末還原收盤（該月最後一根有效 K 棒）相除；T 所在月＝t，只用 t−1 以前的完整月；
    [t−36, t−1] 36 個月任一缺 ⇒ NaN；OLS 含截距；e 取 t−12～t−2（11 個）⇒ score ＝ Σe ／ sd(e, ddof=1)
 同分：訊號表先依 (entry_pos, sid) 排好再傳 pick（引擎 argsort 為 stable）⇒ 同分代號小者先
 F：候選的 T 本身就是量測日 ⇒ 在該量測日 eligible 列內把面板 ret_120 重新 rank(pct)，> 0.95 剔；不在 eligible 或缺值 ⇒ 不剔、計數
 F 假訊號臂：每個訊號日（entry_pos）從候選中隨機剔與 F 同數量（rng 種子 20260925＋r，依 entry_pos 排序後依序抽）；30 次 × 200 顆
 pick 用到的換股日：引擎 log 中出現「a（槽滿）」的進場日 ／ 有候選的進場日
 同現金比例 × 0050：日報酬 ＝ 前一日曝險 e(t−1) × 0050 日報酬（e ＝ 持股市值／權益）
"""
from __future__ import annotations
import os, sys, time, json, bisect
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                               # D.DATA ⇒ 快照
D = H2.D
from backtest import research11 as R
from backtest import research13 as R13
from backtest import researchp7 as P7
from backtest import researchp12 as P12
from backtest import p4_features as P4F
from backtest import tradability as T

OUT = "backtest/resultsAFC"
SEED0, N_W1, N_F = 102000, 1000, 200
FAKE_SEED, N_FAKE = 20260925, 30
ANCHOR_0050 = (0.2402, -0.3396)
COSTS = (0.00585, 0.008, 0.010, 0.015)
_S = {}


def _init(d):
    _S.update(d)


def sim(sig, seed, pick=None, cost=None, log=None, audit=None):
    R.COST = cost if cost is not None else P12.COST_STD
    try:
        return R.simulate_mtm(sig, P12.RULE, P12.N_C1, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                              return_equity=True, pick=pick, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero",
                              tradable=_S["trad"], delist=_S["dl"], log=log, audit=audit)
    finally:
        R.COST = P12.COST_STD


def wstats(out):
    w0, w1 = _S["w0"], _S["w1"]
    r = P12.win_read(out, w0, w1, _S["marks"])
    return {"cagr": r["cagr"], "mdd": r["mdd"], "tr": r["tr"], "expo": r["expo"]}


def passes(c, m):
    a, b = _S["c50"], _S["m50"]
    return bool(c >= a and m >= b and (c > a or m > b))


def _w1(seed):
    st = wstats(sim(_S["sig"], seed)); st["seed"] = seed; st["pass"] = passes(st["cagr"], st["mdd"]); return st


def _f(args):
    seed, which = args
    sg = _S["sigF"] if which < 0 else _S["fake"][which]
    st = wstats(sim(sg, seed)); st.update(seed=seed, arm=which, **{"pass": passes(st["cagr"], st["mdd"])}); return st


# ── 分數 ──
def vol_last(c_valid, idx_map, sid, T_pos, n):
    """sid 在日曆位置 T_pos（含）以前最近 n+1 根有效收盤 ⇒ n 個日報酬的 sd；不足 ⇒ NaN。"""
    bars = idx_map[sid]
    k = bisect.bisect_right(bars, T_pos)
    if k < n + 1:
        return np.nan
    x = c_valid[sid][k - n - 1:k]
    r = x[1:] / x[:-1] - 1.0
    return float(np.std(r, ddof=1))


def monthly(c_cal, cal):
    """月末（該月最後一根有效 K 棒）還原收盤 ⇒ 月報酬 Series（index ＝ Period）。"""
    s = pd.Series(c_cal, index=cal).dropna()
    me = s.groupby(s.index.to_period("M")).last()
    full = pd.period_range(me.index.min(), me.index.max(), freq="M")
    me = me.reindex(full)
    return me / me.shift(1) - 1.0


def resid_score(ri: pd.Series, r0: pd.Series, t: pd.Period):
    """C 的殘差動能分數（只用 t−1 以前）。"""
    win = pd.period_range(t - 36, t - 1, freq="M")
    y = ri.reindex(win); x = r0.reindex(win)
    if y.isna().any() or x.isna().any():
        return np.nan
    X = np.column_stack([np.ones(36), x.to_numpy()])
    b = np.linalg.lstsq(X, y.to_numpy(), rcond=None)[0]
    e = y.to_numpy() - X @ b
    form = e[24:35]                                     # t−12 … t−2（win[24] ＝ t−12，win[34] ＝ t−2）
    sd = np.std(form, ddof=1)
    return float(form.sum() / sd) if sd > 0 else np.nan


def fixtures_C():
    """登錄 §二 三件 fixture（⭐ 三個都過才開跑；⭐ 先證明會響：分數不可是 0）。
    構造：e 在整個 36 個月估計窗內與 1、r0050 正交（⇒ OLS 殘差恰為 e），形成期的和不為 0（⇒ 分數不為 0）。"""
    rng = np.random.default_rng(7)
    per = pd.period_range("2015-01", "2020-12", freq="M")
    t = pd.Period("2020-06", "M")
    win = pd.period_range(t - 36, t - 1, freq="M"); fm = pd.period_range(t - 12, t - 2, freq="M")
    r0 = pd.Series(rng.normal(0.01, 0.05, len(per)), index=per)
    v = rng.normal(0, 0.03, 36); A = np.column_stack([np.ones(36), r0.loc[win].to_numpy()])
    v = v - A @ np.linalg.lstsq(A, v, rcond=None)[0]
    e = pd.Series(0.0, index=per); e.loc[win] = v
    ri = 0.002 + 1.3 * r0 + e
    s = resid_score(ri, r0, t)
    ef = e.loc[fm].to_numpy(); hand = ef.sum() / np.std(ef, ddof=1)
    assert abs(hand) > 0.1, "⛔ fixture 本身退化：手算分數接近 0，驗不到變號"
    assert abs(s - hand) < 1e-10, (s, hand)
    e2 = e.copy(); e2.loc[fm] = -e2.loc[fm]
    s2 = resid_score(0.002 + 1.3 * r0 + e2, r0, t)
    assert s2 * s < 0, ("⛔ 形成期變號後 score 沒變號", s, s2)
    s3 = resid_score(0.002 + 0.7 * r0 + e, r0, t)
    assert abs(s3 - s) < 1e-10, ("⛔ b 改 0.7 score 變了", s, s3)
    ri4 = ri.copy(); ri4.loc[t - 20] = np.nan
    assert np.isnan(resid_score(ri4, r0, t)), "⛔ 缺月沒給 NaN"
    print("✅ fixture C：①已知殘差 score {:+.6f} 手算 {:+.6f} 差 {:.1e}｜②形成期變號 {:+.6f}→{:+.6f}（符號相反）、b 1.3→0.7 差 {:.1e}｜③缺月 NaN".format(s, hand, abs(s - hand), s, s2, abs(s3 - s)))
    return {"①score": s, "①手算": hand, "①差": abs(s - hand), "②變號後": s2, "②b改0.7差": abs(s3 - s), "③缺月": "NaN"}


def simp(sig, seed, col, **kw):
    """⭐ 引擎只帶 _LOG_COLS 那幾欄（relvol、month…）⇒ 自訂分數放進 relvol 再 pick="relvol"（⛔ 不改共用引擎；relvol 在本件無其他用途）。"""
    return sim(sig.assign(relvol=sig[col]), seed, pick="relvol", **kw)


# ═════════════ 描述量 ═════════════
def path_desc(out, log=None, audit=None):
    """單一路徑的必報：持有天數、年換手與年成本、平均現金、同現金比例×0050、逐年、去掉最好一年、組合 vol60／β、最大回落段。"""
    w0, w1, cal = _S["w0"], _S["w1"], _S["cal"]
    eq, hv = out["equity"], out["hold_val"]
    d = {}
    e = np.where(eq[w0:w1 + 1] > 0, hv[w0:w1 + 1] / eq[w0:w1 + 1], np.nan)
    d["平均曝險"] = float(np.nanmean(e)); d["平均現金比例"] = 1 - d["平均曝險"]
    r50 = _S["c50d"][w0 + 1:w1 + 1] / _S["c50d"][w0:w1] - 1.0
    ex = np.r_[np.nan, e[:-1]][1:]
    eqx = np.r_[1.0, np.cumprod(1 + ex * r50)]
    yrs = (w1 - w0) / 245
    d["同現金比例×0050"] = {"cagr": float(eqx[-1] ** (1 / yrs) - 1), "mdd": float((eqx / np.maximum.accumulate(eqx) - 1).min())}
    ys = pd.Series(eq[w0:w1 + 1], index=cal[w0:w1 + 1])
    ye = ys.groupby(ys.index.year).last(); prev = ye.shift(1); prev.iloc[0] = ys.iloc[0]
    d["逐年"] = {int(k): float(v) for k, v in (ye / prev - 1).items()}      # 年末 ÷ 前一年末（首年 ÷ 窗首）
    best = max(d["逐年"], key=d["逐年"].get)
    rest = [v for k, v in d["逐年"].items() if k != best]
    d["去掉最好一年"] = {"最好一年": best, "其餘年幾何平均": float(np.prod([1 + v for v in rest]) ** (1 / len(rest)) - 1)}
    rp = pd.Series(eq[w0:w1 + 1]).pct_change().to_numpy()[1:]
    d["組合vol60中位"] = float(pd.Series(rp).rolling(60).std().median() * np.sqrt(245))
    beta = []
    for k in range(120, len(rp), 20):
        y_, x_ = rp[k - 120:k], r50[k - 120:k]; ok = np.isfinite(y_) & np.isfinite(x_)
        if ok.sum() > 60:
            beta.append(np.cov(y_[ok], x_[ok])[0, 1] / np.var(x_[ok], ddof=1))
    d["組合β中位（120日、每20日）"] = float(np.median(beta))
    pk, tr, dep = P12.deepest_episode(eq, out["first"], out["end"], cal)
    d["最大回落段"] = {"峰": str(cal[pk].date()), "谷": str(cal[tr].date()), "深度（全期）": dep}
    if audit is not None:
        buys = {}; hold = []; amt_tr = 0.0; cost = 0.0
        for a in sorted(audit, key=lambda x: (x["t"], 0 if x["side"] == "sell" else 1)):
            if a["side"] == "buy":
                buys[a["sid"]] = a["t"]
            else:
                if a["sid"] in buys:
                    hold.append(a["t"] - buys.pop(a["sid"]))
                if w0 <= a["t"] <= w1:
                    amt_tr += a["amt"] / a["equity_prev"]; cost += a["cost"] / a["equity_prev"]
        h = np.array(hold)
        d["①持有天數"] = {"中位": float(np.median(h)), "p10": float(np.percentile(h, 10)), "p90": float(np.percentile(h, 90)), "筆數": len(h)}
        d["②年換手率（賣出額／權益）"] = amt_tr / yrs; d["②年成本（權益 %）"] = cost / yrs
        mk = _S["mkt"]; wmk = {}
        for a in audit:
            if a["side"] == "buy":
                wmk[mk.get(a["sid"], "?")] = wmk.get(mk.get(a["sid"], "?"), 0) + 1
        d["進場筆數證券別"] = wmk
    if log is not None:
        L = pd.DataFrame(log)
        if len(L) and "t" in L:
            g = L.groupby("t")["reason"].apply(lambda s: ("a" in set(s)) or ("b" in set(s)))
            d["pick用到的換股日"] = {"有候選的進場日": int(len(g)), "候選>可進場數的日": int(g.sum()), "佔比": float(g.mean())}
    return d


def main():
    t0 = time.time()
    fx = fixtures_C()
    cal = D.load_calendar(); ncal = len(cal)
    panel = P4F.read_panel(os.path.join(OUT, "panel.csv.gz"))
    uni = D.load_universe().set_index("stock_id")["market"]
    sids = sorted(set(panel["stock_id"]))
    closes, opens, c_valid, idx_map = {}, {}, {}, {}
    for s in sids + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float)
        v = np.flatnonzero(np.isfinite(c)); idx_map[s] = v.tolist(); c_valid[s] = c[v]
    w0, w1 = P12.win_bounds(cal, "全窗"); marks = P12.month_marks(cal, w0, w1)
    assert str(cal[w0].date()) == "2017-03-02" and str(cal[w1].date()) == "2026-08-24"
    # 0050 錨
    c50 = closes["0050"]; eq50 = c50 / c50[w0]
    c50_cagr, c50_mdd = R13.window_stats(eq50, w0, w1 + 1, w0, w1 + 1)
    print("[0050 同窗] 年化 {:+.4%}｜回落 {:+.4%}（登錄 +24.02%／−33.96%）".format(c50_cagr, c50_mdd), flush=True)
    if abs(c50_cagr - ANCHOR_0050[0]) > 5e-5 or abs(c50_mdd - ANCHOR_0050[1]) > 5e-5:
        raise SystemExit("⛔ 0050 同窗錨點對不上登錄 ⇒ 停、回報")
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    print("[S1] 門檻B 訊號 {:,} 筆／{:,} 檔／{} 月（新資料；⛔ 不對舊七數）｜{:.0f}s".format(len(sig), sig["sid"].nunique(), sig["month"].nunique(), time.time() - t0), flush=True)
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    # A 分數
    Tpos = sig["entry_pos"].to_numpy() - 1
    sig["negvol60"] = [-vol_last(c_valid, idx_map, s, int(tp), 60) for s, tp in zip(sig["sid"], Tpos)]
    sig["negvol120"] = [-vol_last(c_valid, idx_map, s, int(tp), 120) for s, tp in zip(sig["sid"], Tpos)]
    sig["vol60"] = -sig["negvol60"]
    # C 分數
    mret = {s: monthly(closes_raw, cal) for s, closes_raw in ((s, np.where(np.isin(np.arange(ncal), idx_map[s]), closes[s], np.nan)) for s in set(sig["sid"]) | {"0050"})}
    sig["rmom"] = [resid_score(mret[s], mret["0050"], pd.Period(cal[int(tp)], "M")) for s, tp in zip(sig["sid"], Tpos)]
    # F 剔除
    el = panel[panel["eligible"].astype(bool)].copy()
    el["rk"] = el.groupby("measure_date")["ret_120"].rank(pct=True)
    rk = {(d_, s_): v for d_, s_, v in zip(el["measure_date"], el["stock_id"], el["rk"])}
    sig["Tdate"] = [cal[int(tp)] for tp in Tpos]
    sig["rk120"] = [rk.get((d_, s_), np.nan) for d_, s_ in zip(sig["Tdate"], sig["sid"])]
    sig["F剔"] = sig["rk120"] > 0.95
    sigF = sig[~sig["F剔"]].reset_index(drop=True)
    nrm = sig.groupby("entry_pos")["F剔"].sum()
    fake = []
    for r in range(1, N_FAKE + 1):
        rng = np.random.default_rng(FAKE_SEED + r); drop = []
        for ep, g in sig.groupby("entry_pos", sort=True):
            k = int(nrm.get(ep, 0))
            if k:
                drop += list(rng.choice(g.index.to_numpy(), size=k, replace=False))
        fake.append(sig.drop(index=drop).reset_index(drop=True))
    S = {"closes": closes, "opens": opens, "ncal": ncal, "trad": trad, "dl": dl, "w0": w0, "w1": w1, "marks": marks,
         "c50": c50_cagr, "m50": c50_mdd, "sig": sig, "sigF": sigF, "fake": fake, "cal": cal, "c50d": c50, "mkt": uni.to_dict()}
    _init(S)
    R_ = {"快照": H2.SHA, "fixture_C": fx, "0050同窗": [c50_cagr, c50_mdd],
          "S1訊號": {"筆": len(sig), "檔": int(sig["sid"].nunique()), "月": int(sig["month"].nunique())}}
    with Pool(4, initializer=_init, initargs=(S,)) as pool:
        W1 = pd.DataFrame(pool.map(_w1, [SEED0 + r for r in range(N_W1)], chunksize=10))
        W1.to_csv(os.path.join(OUT, "w1_1000.csv"), index=False)
        print("[W1] 1,000 顆：年化中位 {:+.4%}、回落中位 {:+.4%}、判過 {}／1000｜{:.0f}s".format(W1["cagr"].median(), W1["mdd"].median(), int(W1["pass"].sum()), time.time() - t0), flush=True)
        FF = pd.DataFrame(pool.map(_f, [(SEED0 + r, -1) for r in range(N_F)] + [(SEED0 + r, j) for j in range(N_FAKE) for r in range(N_F)], chunksize=20))
        FF.to_csv(os.path.join(OUT, "f_and_fake.csv"), index=False)
    print("[F＋假訊號] 完成｜{:.0f}s".format(time.time() - t0), flush=True)
    w1_200 = W1[W1["seed"] < SEED0 + N_F].set_index("seed")
    R_["W1"] = {"n": N_W1, "年化中位": W1["cagr"].median(), "回落中位": W1["mdd"].median(), "判過": int(W1["pass"].sum()),
                "判過比例": float(W1["pass"].mean()), "200顆年化中位": w1_200["cagr"].median(), "200顆回落中位": w1_200["mdd"].median()}
    # ── A／C：單一路徑
    def single(name, pick):
        lg, au = [], []
        out = simp(sig, SEED0, pick, log=lg, audit=au)
        st = wstats(out)
        res = {"年化": st["cagr"], "回落": st["mdd"], "判過": passes(st["cagr"], st["mdd"]),
               "百分位_年化（W1 1000 顆中 ≤ 它的比例）": float((W1["cagr"] <= st["cagr"]).mean()),
               "百分位_回落（W1 1000 顆中 ≤ 它的比例；越大越淺）": float((W1["mdd"] <= st["mdd"]).mean())}
        res["成本敏感度"] = {f"{c:.3%}": dict(zip(("年化", "回落"), (lambda o: (o["cagr"], o["mdd"]))(wstats(simp(sig, SEED0, pick, cost=c))))) for c in COSTS}
        res["描述"] = path_desc(out, log=lg, audit=au)
        return res
    R_["A"] = single("A", "negvol60")
    R_["A"]["描述臂"] = {"vol120最低": dict(zip(("年化", "回落"), (lambda o: (o["cagr"], o["mdd"]))(wstats(simp(sig, SEED0, "negvol120"))))),
                       "vol60最高": dict(zip(("年化", "回落"), (lambda o: (o["cagr"], o["mdd"]))(wstats(simp(sig, SEED0, "vol60")))))}
    R_["A"]["vol60為NaN的候選"] = int(sig["negvol60"].isna().sum())
    R_["C"] = single("C", "rmom")
    R_["C"]["score為NaN的候選佔比"] = float(sig["rmom"].isna().mean())
    lg, au = [], []
    ow = sim(sig, SEED0, log=lg, audit=au)
    R_["W1_種子102000_描述"] = path_desc(ow, log=lg, audit=au)
    # ── F
    Fm = FF[FF["arm"] == -1].set_index("seed"); Fk = FF[FF["arm"] >= 0]
    pair_c = (Fm["cagr"] - w1_200["cagr"]); pair_m = (Fm["mdd"] - w1_200["mdd"])
    fk_med = Fk.groupby("arm").agg(cagr=("cagr", "median"), mdd=("mdd", "median"))
    fk_pass = [passes(c_, m_) for c_, m_ in zip(fk_med["cagr"], fk_med["mdd"])]
    R_["F"] = {"年化中位": Fm["cagr"].median(), "回落中位": Fm["mdd"].median(), "判過": passes(Fm["cagr"].median(), Fm["mdd"].median()),
               "配對差（含抽籤雜訊）": {"年化中位": pair_c.median(), "年化為正顆": int((pair_c > 0).sum()), "回落中位": pair_m.median(), "回落為正顆": int((pair_m > 0).sum())},
               "假訊號臂": {"判過": int(sum(fk_pass)), "次數": N_FAKE,
                          "F年化中位在30次中的位置（≤它的次數）": int((fk_med["cagr"] <= Fm["cagr"].median()).sum()),
                          "F回落中位在30次中的位置（≤它的次數）": int((fk_med["mdd"] <= Fm["mdd"].median()).sum())},
               "每訊號日被剔數": {"平均": float(nrm.mean()), "分佈": nrm.value_counts().sort_index().to_dict()},
               "被剔佔候選": float(sig["F剔"].mean()), "排不了名": int(sig["rk120"].isna().sum()), "候選總數": len(sig)}
    rm = sig[sig["F剔"]]
    rr = {}
    for H in (20, 60):
        v = [closes[s][min(ncal - 1, e + H - 1)] / opens[s][e] - 1 for s, e in zip(rm["sid"], rm["entry_pos"]) if np.isfinite(opens[s][e]) and opens[s][e] > 0]
        rr[f"H{H}"] = {"n": len(v), "平均": float(np.mean(v)) if v else None, "中位": float(np.median(v)) if v else None}
    R_["F"]["被剔股進場後報酬"] = rr
    lg, au = [], []
    R_["F"]["種子102000_描述"] = path_desc(sim(sigF, SEED0, log=lg, audit=au), log=lg, audit=au)
    json.dump(R_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

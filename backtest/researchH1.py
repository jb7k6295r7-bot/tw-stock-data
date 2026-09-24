# -*- coding: utf-8 -*-
"""PREREGH1（月線 3 日站回：分類器讀法）——回測線落地。判準＝台股策略線 PREREGH1 seq2（sha a2d23aa8f7dc400c）。

資料、母體、還原、漲跌停、硬斷點：與 PREREGH2 同一份快照與同一套函式（researchH2：main edc6f8002f、gate3、R3 斷點）。

⭐ 登錄沒逐字寫、本線的落地讀法（⛔ 看任何結果之前寫在這裡；交件逐條列出）：
 Q1 SMA、「t0−1」、上揚的「t0−5」在【該股有效 K 棒序列】上數；t0+s、t0+4、t0+23、20 日區段用【交易日曆】（同 H2 的 R1）
 Q2 分組：s ∈ {1,2,3} 用日曆日 t0+s；(t0, t0+3] 任一天無有效 K 棒 ⇒「無法分組」（登錄 §二⑤ 字面）；
    否則 ∃ s：close(t0+s) ≥ SMA20(t0+s) ⇒ 站回組（SMA 以該日那根 K 棒的 SMA）
 Q3 處理順序：原始事件 ⇒ 合併（被保留事件 t0 的 (t0, t0+23]）⇒ 過去窗資格（≥ 25 根、[t0−24, t0] 無斷點）⇒ 無法分組
    ⇒ 未來窗 (t0, t0+23] 斷點（逐組）⇒ open(t0+4) 停牌／漲停開（逐組）⇒ 保留；被剔除者不開合併窗
 Q4 gate3 資格母體等權報酬：entry 日 d＝t0+4 有有效開盤的 gate3 股票，各自 close(≤ d+19 最後一根)／open(d) − 1 的等權平均
    （下市者以最後成交價；與 H2 的 R10 同）
 Q5 主 CI：OLS X ＝ α ＋ β·站回，β 的 SE 以 t0 曆月分群（CR0，與 research11.cl_stats 一致、無小樣本修正）
    非重疊 SE（第二欄）：同一迴歸改以「判定窗起點切的 20 交易日區段」分群
 Q6 描述臂 c（期限 2／5 天）：分組在 t0+d 收盤確定 ⇒ P0＝open(t0+d+1)、終點 close(t0+d+20)、合併窗 t0+d+20、未來窗 (t0, t0+d+20]
    描述臂 d（H＝60／120）：P0＝open(t0+4)、終點 close(t0+3+H)、合併窗與未來窗同延長、區段長 H
 Q7 描述臂 e（進場讀法）：只用站回組；站回日 s* 收盤確認 ⇒ open(t0+s*+1) 進、close(t0+s*+20) 出；對照＝同段 gate3 等權；毛、淨（−0.585%）
 Q8 描述臂 a：close(t0+23)／close(t0) − 1 的兩組差（原始、不扣母體）；④ 機械差：close(t0+3)／close(t0) − 1 兩組平均與差
"""
from __future__ import annotations
import os, sys, time, json
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                            # ⭐ 同一份快照、同一套讀檔／斷點（D.DATA 已被指到快照）
D, TR, UG = H2.D, H2.TR, H2.UG

OUT = "backtest/resultsH1"
W0, W1, WIN_DAYS, SEED = H2.W0, H2.W1, H2.WIN_DAYS, H2.SEED
COST_RT = H2.COST_RT
SMAS, KS = (10, 20, 60), (1, 5, 10)
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
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    cb = c[bars]
    ma_cal, ev = {}, {}
    for m in SMAS:
        mb = pd.Series(cb).rolling(m, min_periods=m).mean().to_numpy()
        a = np.full(n, np.nan); a[bars] = mb; ma_cal[m] = a
        for k in KS:
            if (m != 20 and k != 5):
                continue                                 # 只要 SMA20×k{1,5,10} 與 SMA10／60×k5
            up = np.zeros(len(bars), bool); up[k:] = mb[k:] > mb[:-k]
            e = np.zeros(len(bars), bool)
            e[1:] = up[1:] & (cb[1:] < mb[1:]) & (cb[:-1] >= mb[:-1])
            e &= np.isfinite(mb); e[1:] &= np.isfinite(mb[:-1])
            x = np.zeros(n, bool); x[bars] = e; ev[(m, k)] = x
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        r_ = r_ + 1 if not valid[i] else 0; run[i] = r_
    tb = TR.one(sid, cal)
    cff = pd.Series(c).ffill().to_numpy()
    return {"sid": sid, "o": o, "c": c, "cff": cff, "valid": valid, "nb": np.cumsum(valid).astype(np.int32),
            "ma": ma_cal, "ev": ev, "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(run >= 5).astype(np.int32),
            "trd": tb["trd"], "up_o": tb["up_o"]}


def market_ew(ST, n, Hh):
    """EW[d] ＝ d 日有有效開盤的 gate3 股票：close(≤ d+Hh−1 最後一根)／open(d) − 1 的等權平均（Q4）。"""
    num = np.zeros(n); den = np.zeros(n)
    for S in ST.values():
        o = S["o"]; cf = S["cff"]
        ok = np.isfinite(o) & (o > 0)
        idx = np.flatnonzero(ok); idx = idx[idx + Hh - 1 < n]
        r = cf[idx + Hh - 1] / o[idx] - 1.0
        g = np.isfinite(r)
        np.add.at(num, idx[g], r[g]); np.add.at(den, idx[g], 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


def build(ST, cal, w0, w1, EW, m=20, k=5, dl=3, Hh=20):
    """cfg：SMA m、上揚 k、站回期限 dl、持有 Hh ⇒ 保留事件表＋帳（Q3）。"""
    end_off = dl + Hh                                    # 終點 ＝ t0 + dl + Hh（主格 3+20 ＝ 23）
    acc = {"原始事件": 0, "合併掉": 0, "樣本不足或過去斷點": 0, "無法分組": 0,
           "站回_未來窗斷點": 0, "未站回_未來窗斷點": 0, "站回_不成交停牌": 0, "未站回_不成交停牌": 0,
           "站回_不成交漲停開": 0, "未站回_不成交漲停開": 0}
    rows = []
    for s in sorted(ST):
        S = ST[s]; ma = S["ma"][m]
        ts = np.flatnonzero(S["ev"][(m, k)][w0:w1 - end_off + 1]) + w0
        acc["原始事件"] += len(ts)
        t_keep = -10 ** 9
        for t in ts:
            if t_keep < t <= t_keep + end_off:
                acc["合併掉"] += 1; continue
            if not (S["nb"][t] >= 25 and not H2.brk(S, t - 24, t)):
                acc["樣本不足或過去斷點"] += 1; continue
            if not S["valid"][t + 1:t + dl + 1].all():
                acc["無法分組"] += 1; continue
            back = [j for j in range(1, dl + 1) if S["c"][t + j] >= ma[t + j]]
            grp = "站回" if back else "未站回"
            if H2.brk(S, t + 1, t + end_off):
                acc[grp + "_未來窗斷點"] += 1; continue
            e = t + dl + 1
            if not S["trd"][e] or not np.isfinite(S["o"][e]):
                acc[grp + "_不成交停牌"] += 1; continue
            if S["up_o"][e]:
                acc[grp + "_不成交漲停開"] += 1; continue
            P0 = float(S["o"][e]); cE = float(S["cff"][t + end_off])
            R = cE / P0 - 1.0
            rows.append({"sid": s, "t": int(t), "grp": grp, "站回": int(bool(back)), "s_first": back[0] if back else 0,
                         "R": R, "X": R - float(EW[e]), "a_R_from_t0": cE / float(S["c"][t]) - 1.0,
                         "mech": float(S["c"][t + dl]) / float(S["c"][t]) - 1.0})
            t_keep = t
    return pd.DataFrame(rows), acc


def cluster_reg(y, g, cl):
    """y ＝ α ＋ β g，β 與其分群 SE（CR0）。"""
    X = np.column_stack([np.ones(len(y)), g.astype(float)])
    XtX_inv = np.linalg.inv(X.T @ X); b = XtX_inv @ X.T @ y; u = y - X @ b
    meat = np.zeros((2, 2))
    for c_ in np.unique(cl):
        m_ = cl == c_; s_ = X[m_].T @ u[m_]; meat += np.outer(s_, s_)
    V = XtX_inv @ meat @ XtX_inv
    return float(b[1]), float(np.sqrt(V[1, 1]))


def judge(E, cal, w0, Hh=20, col="X"):
    if E.empty or E["站回"].nunique() < 2:
        return {"n": len(E), "出口": "出口①", "結果": "—（出口①：樣本不足以分辨）"}
    y = E[col].to_numpy(float); g = E["站回"].to_numpy()
    mon = np.array([str(cal[t])[:7] for t in E["t"]]); blk = ((E["t"] - w0) // Hh).to_numpy()
    b, se = cluster_reg(y, g, mon); _, se2 = cluster_reg(y, g, blk)
    nb = E[E["站回"] == 0]; n0 = len(nb); nblk0 = int(((nb["t"] - w0) // Hh).nunique())
    n_eff = min(n0, nblk0)
    out = {"D": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "se_月": se, "months": int(len(np.unique(mon))),
           "se_非重疊": se2, "lo_非重疊": b - 1.96 * se2, "hi_非重疊": b + 1.96 * se2,
           "n_站回": int(g.sum()), "n_未站回": n0, "未站回區段數": nblk0, "n_eff": n_eff,
           "n_eff_尺度": "未站回事件數" if n0 <= nblk0 else "有未站回事件的20日區段數",
           "平均X_站回": float(E.loc[E["站回"] == 1, "X"].mean()), "平均X_未站回": float(nb["X"].mean()),
           "平均R_站回": float(E.loc[E["站回"] == 1, "R"].mean()), "平均R_未站回": float(nb["R"].mean())}
    if n_eff < 30 or n0 < 30:
        out["出口"] = "出口①"; out["結果"] = "—（出口①：樣本不足以分辨）"
    else:
        out["出口"] = "出口②" if n_eff < 100 else "出口③"
        out["結果"] = "結果①（測不出）" if out["lo"] <= 0 <= out["hi"] else ("結果②（測得出（＋））" if b > 0 else "結果③（測得出（−））")
    return out


def selftest():
    """⭐ 先證明會響：分群迴歸係數＝兩組平均差；月內打亂保留每月兩組筆數。"""
    rng = np.random.default_rng(0)
    y = np.r_[rng.normal(1, 1, 50), rng.normal(0, 1, 70)]; g = np.r_[np.ones(50), np.zeros(70)]
    cl = rng.integers(0, 12, 120)
    b, se = cluster_reg(y, g, cl)
    assert abs(b - (y[:50].mean() - y[50:].mean())) < 1e-12 and se > 0
    E = pd.DataFrame({"m": cl, "站回": g.astype(int)})
    sh = shuffle_within(E, np.random.default_rng(1))
    assert (E.groupby("m")["站回"].sum() == pd.Series(sh, index=E.index).groupby(E["m"]).sum()).all()
    print("✅ 自測：分群迴歸係數＝兩組平均差、月內打亂保留每月兩組筆數")


def shuffle_within(E, rng, key="m"):
    lab = E["站回"].to_numpy().copy()
    for _, idx in E.groupby(key).indices.items():
        lab[idx] = rng.permutation(lab[idx])
    return lab


def main():
    selftest()
    t0 = time.time()
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert w1 - w0 + 1 == WIN_DAYS
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    with Pool(4, initializer=_init, initargs=(cal,)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=16)
    ST = {r["sid"]: r for r in res if r is not None}
    print("[資料] 快照 {}｜gate3 {:,} 檔、可用 {:,}｜{:.0f}s".format(H2.SHA[:10], len(U), len(ST), time.time() - t0), flush=True)
    EW = {h: market_ew(ST, n, h) for h in (20, 60, 120)}
    os.makedirs(OUT, exist_ok=True)
    R_ = {"快照": H2.SHA, "gate3母體": len(U), "可用檔數": len(ST)}
    E, acc = build(ST, cal, w0, w1, EW[20])
    E.to_csv(os.path.join(OUT, "main_events.csv"), index=False)
    js = judge(E, cal, w0)
    R_["①事件帳"] = {**acc, "保留事件": len(E), "相異檔數": int(E["sid"].nunique()), "合併佔比": acc["合併掉"] / max(1, acc["原始事件"])}
    R_["②站回"] = {"站回率": float(E["站回"].mean()), "分母": len(E), "s1": int((E["s_first"] == 1).sum()),
                  "s2": int((E["s_first"] == 2).sum()), "s3": int((E["s_first"] == 3).sum()),
                  "措辭前提（站回率≥80%）": bool(E["站回"].mean() >= 0.8)}
    R_["③判定"] = js
    mech = E.groupby("grp")["mech"].mean()
    R_["④分組窗機械差"] = {"站回": float(mech.get("站回")), "未站回": float(mech.get("未站回")), "差": float(mech.get("站回") - mech.get("未站回"))}
    R_["⑤逐年"] = {g_: E[E["grp"] == g_]["t"].map(lambda t: cal[t].year).value_counts().sort_index().to_dict() for g_ in ("站回", "未站回")}
    # ⑧ 未來窗排除（逐組；分母 ＝ 該組到了未來窗那一關的事件數）
    ex = {}
    for g_ in ("站回", "未站回"):
        num = acc[g_ + "_未來窗斷點"] + acc[g_ + "_不成交停牌"]
        den = acc[g_ + "_未來窗斷點"] + acc[g_ + "_不成交停牌"] + acc[g_ + "_不成交漲停開"] + int((E["grp"] == g_).sum())
        ex[g_] = {"斷點": acc[g_ + "_未來窗斷點"], "t0+4停牌": acc[g_ + "_不成交停牌"], "分母": den, "比例": num / max(1, den)}
    a_, b_ = ex["站回"]["比例"], ex["未站回"]["比例"]
    ex["相差逾兩倍"] = bool(max(a_, b_) > 2 * min(a_, b_)) if min(a_, b_) > 0 else bool(max(a_, b_) > 0)
    ex["無法分組"] = acc["無法分組"]
    R_["⑧未來窗排除"] = ex
    print("[主格] 保留 {:,}（站回 {:,}／未站回 {:,}）｜D {:+.4f}（CI {:+.4f}～{:+.4f}）｜{} {}｜{:.0f}s".format(
        len(E), js.get("n_站回", 0), js.get("n_未站回", 0), js.get("D", np.nan), js.get("lo", np.nan), js.get("hi", np.nan),
        js.get("出口"), js.get("結果"), time.time() - t0), flush=True)
    # ⑥ 假訊號臂：t0 曆月內打亂標籤
    Em = E.assign(m=[str(cal[t])[:7] for t in E["t"]])
    fk = []
    for r in range(1, 31):
        lab = shuffle_within(Em, np.random.default_rng(SEED + r))
        j = judge(Em.assign(站回=lab), cal, w0)
        fk.append({"r": r, "D": j["D"], "lo": j["lo"], "hi": j["hi"], "判過": bool(not (j["lo"] <= 0 <= j["hi"]))})
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "fake_arm.csv"), index=False)
    R_["⑥假訊號臂"] = {"判過": int(FK["判過"].sum()), "次數": 30}
    # ⑦ 描述臂
    dsc = {"a_從t0起算": judge(E, cal, w0, col="a_R_from_t0"), "g_原始報酬": judge(E, cal, w0, col="R")}
    for kk in (1, 10):
        e2, a2 = build(ST, cal, w0, w1, EW[20], k=kk)
        dsc[f"b_k{kk}"] = {"事件帳": {**a2, "保留": len(e2)}, "站回率": float(e2["站回"].mean()), "判定形": judge(e2, cal, w0)}
    for dl in (2, 5):
        e2, a2 = build(ST, cal, w0, w1, EW[20], dl=dl)
        dsc[f"c_期限{dl}天"] = {"事件帳": {**a2, "保留": len(e2)}, "站回率": float(e2["站回"].mean()), "判定形": judge(e2, cal, w0)}
    for hh in (60, 120):
        e2, a2 = build(ST, cal, w0, w1, EW[hh], Hh=hh)
        dsc[f"d_H{hh}"] = {"降級理由": "結構上不可得（⌊2313／{}⌋＝{}）".format(hh, WIN_DAYS // hh), "事件帳": {**a2, "保留": len(e2)},
                            "判定形": judge(e2, cal, w0, Hh=hh)}
    for mm in (10, 60):
        e2, a2 = build(ST, cal, w0, w1, EW[20], m=mm)
        dsc[f"f_SMA{mm}"] = {"事件帳": {**a2, "保留": len(e2)}, "站回率": float(e2["站回"].mean()), "判定形": judge(e2, cal, w0)}
    # e 進場讀法（Q7）
    rows = []
    for r in E[E["站回"] == 1].itertuples():
        S = ST[r.sid]; e = r.t + r.s_first + 1; x = r.t + r.s_first + 20
        if x >= n or not S["trd"][e] or not np.isfinite(S["o"][e]) or S["up_o"][e]:
            continue
        g_ = float(S["cff"][x]) / float(S["o"][e]) - 1.0
        rows.append({"t": r.t, "g": g_, "ew": float(EW[20][e])})
    Xe = pd.DataFrame(rows); Xe["d"] = Xe["g"] - Xe["ew"]
    cs = H2.R.cl_stats(Xe["d"].to_numpy(float), np.array([str(cal[t])[:7] for t in Xe["t"]]))
    dsc["e_進場讀法"] = {"n": len(Xe), "毛": float(Xe["g"].mean()), "淨": float(Xe["g"].mean() - COST_RT), "對照等權": float(Xe["ew"].mean()),
                       "差": cs["mean"], "差_CI": [cs["lo"], cs["hi"]]}
    R_["⑦描述臂"] = dsc
    json.dump(R_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

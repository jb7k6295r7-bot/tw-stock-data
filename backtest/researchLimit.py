# -*- coding: utf-8 -*-
"""PREREG限價【開盤市價 vs 掛低 1／2／3%】——回測線落地。
判準＝台股策略線 PREREG限價 seq3（sha fddc47686e5339f9，2026-09-25 17:53）；裁定線 seq165（判定改 H20、月區段、H120 描述
「依構造不可判定」、出場 H〈n〉＝entry＋(n−1) 收盤）、seq166（多格都過取 D 最大那格、句子附該格 CI 下緣）。

資料（同 ref_interval_close.py）：main edc6f8002f 快照（researchH2 把 D.DATA 指過去）；resultsAFC/panel.csv.gz；
   P7.build_sig_gate_b(signal="B") ⇒ entry_pos 落主窗 [2017-03-02, 2026-08-24] 的 2,881 列（旁證 ANCHOR_S1_MAIN）；
   T.build ＋ T.delist_status(official)；還原 ＝ 未還原 × F(d)（data.cum_factor_series）。規則核心在 limit_entry.py。

用法：  python researchLimit.py pre     ⇒ 開跑前報（⛔ 不算任何報酬：只算成交／放棄、漲停、成交時點、區段數與可能出口）
        python researchLimit.py body    ⇒ 本體（判定 3 格、§四 必報、描述臂、查核）

⭐ 登錄沒逐字寫、本線的落地讀法（⛔ 在看任何報酬之前寫在這裡；交件逐條列出）：
 L1 訊號日 m ＝ 量測日 ＝ entry_pos − 1（build_sig_gate_b：entry_pos ＝ 量測日位置＋1）。
    P 用 m 的【未還原】收盤；m 當天無成交 ⇒ 用 m 以前最後一個有成交日的未還原收盤（件數另報）。
 L2 ⚠【兩種讀法處①】除權息／減資事件落在 (m, 成交日]：
    ⭐ 主讀法（甲）＝ 未還原：P 是掛在交易所的實際價、拿當日【未還原】最低比（使用者真的掛單就是這樣）。
      讀法（乙）＝ 還原：P 換到當日的還原尺度（P × F(m)／F(t)，不取整）再比 ⇒ 只作敏感度欄、⛔ 不判；受影響筆數必報。
 L3 5 個交易日數在【交易日曆】上（e … e+4）：停牌日照樣佔一天、當天不可能成交（同 W1 的 xpos 數法）。
 L4 成交價 ＝ min(當日未還原開盤, P)；當日開盤缺值（有收盤、無開盤）⇒ 以 P 成交（件數另報）。
    報酬用還原尺度：成交未還原價 × F(成交日) 當進場還原價。
 L5 M0 放棄 ＝ e 停牌（halt_in）、e 開盤非有限（no_open）、e 開盤＝漲停（limit_up，tradability.up_o）⇒ 報酬 0、進分母。
    M0' ＝ 只把 limit_up 改成以開盤價買到；halt_in／no_open 仍放棄。⚠ 登錄只明寫「開盤漲停＝放棄」，停牌也放棄是本線讀法（件數另報）。
 L6 ⚠【兩種讀法處②】出場量不到（delist_ambig／unresolved／beyond_cal）的訊號：
    ⭐ 主讀法 ＝ 該 H 下【整列從五臂同時剔除】（成對比較，分母一致）；另一讀法（沒買到的臂記 0、買到的剔除）⛔ 不採（會讓分母隨臂變）。件數必報。
 L7 D ＝ 逐訊號成對差 d_i ＝ r_i(L_k) − r_i(M0) 的平均（＝ E(L_k) − E(M0)）；主 CI ＝ research11.cl_stats 同式（CR0、量測月分群、1.96）。
    n_eff ＝ min(訊號數, 有訊號的量測月數)（PREREGM B5 同形；區段＝月，裁定 seq165）；出口 <30 ①、30～99 ②、≥100 ③。
    非重疊 SE（第二欄）＝ 以主窗起點切的 20 交易日區段（依 entry_pos）內 d 平均 ⇒ 區段平均標準差／√區段數（H2 R8）。
 L8 「訊號日漲幅」＝ 還原 close(m)／還原 close(m 前最後一根有效 K 棒) − 1；三分位 ＝ 主窗全部訊號合併 pd.qcut(3)。分年 ＝ entry 日曆年。
 L9 「平均等待天數」＝ 成交日 − m（1～5 個交易日）；M0 恆為 1。「省了多少」＝ 成交還原價 ÷ 還原 open(e) − 1（e 開盤非有限者不計、另報件數）。
 L10 H120：描述；逐字寫「以 120 日區段只有約 18 段 ⇒ 依構造不可判定」；⛔ 不印月分群 CI（裁定 seq165 §二：會假性變窄）。
 L11 假訊號臂：登錄 §一～§六 沒有寫 ⇒ 本件不做（交件寫一句）。
"""
from __future__ import annotations
import os, sys, json, time
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import ref_interval as RI                        # researchH2 已把 D.DATA 指到快照、chdir 到 repo
import ref_interval_close as RIC                 # 只 import（出場規則逐筆比對）
import limit_entry as LE
from backtest import research11 as R11, tradability as T

D = RI.D
OUT = os.path.join("backtest", "resultsLimit")
HS = (20, 120)
H_JUDGE = 20
ARMS = ("M0", "M0p", "L1", "L2", "L3")
ARM_NAME = {"M0": "M0（開盤市價；漲停開盤＝買不到）", "M0p": "M0'（漲停開盤也買到，描述）",
            "L1": "L1（掛低 1%）", "L2": "L2（掛低 2%）", "L3": "L3（掛低 3%）"}
H120_SENTENCE = "以 120 日區段只有約 18 段 ⇒ 依構造不可判定"


def load_raw(sid, cal):
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    out = {}
    for c in ("open", "low", "close"):
        a = np.array(pd.to_numeric(raw[c].reindex(cal), errors="coerce"), dtype=float)
        a[~(a > 0)] = np.nan
        out[c] = a
    out["F"] = D.cum_factor_series(cal, D.load_adj(sid))
    adj = D.load_adj(sid)
    out["ev_pos"] = [] if adj is None else sorted(int(cal.searchsorted(pd.Timestamp(d))) for d in adj["date"])
    return out


def setup():
    t0 = time.time()
    cal, ncal, sig, closes, opens, highs, stk = RI.load_all()
    w0, w1 = RI.P12.win_bounds(cal, "全窗")
    assert cal[w0] == pd.Timestamp("2017-03-02") and cal[w1] == pd.Timestamp("2026-08-24")
    sig = sig[(sig["entry_pos"] >= w0) & (sig["entry_pos"] <= w1)].reset_index(drop=True)
    assert len(sig) == RI.ANCHOR_S1_MAIN, len(sig)
    sids = sorted(set(sig["sid"]))
    trad = T.build(sids, cal); dl = T.delist_status(trad, cal, official=T.load_official())
    RAW = {s: load_raw(s, cal) for s in sids}
    print("[資料] 快照 {}｜主窗 {:,} 列／{:,} 檔／{} 個量測月｜{:.0f}s".format(
        RI.H2.SHA[:10], len(sig), len(sids), sig["month"].nunique(), time.time() - t0), flush=True)
    return dict(cal=cal, ncal=ncal, sig=sig, closes=closes, opens=opens, stk=stk, w0=w0, w1=w1, trad=trad, dl=dl, RAW=RAW)


def entries(S):
    """每個訊號：M0／M0' 狀態、L1～L3 的 P、成交日、成交價（⛔ 不算報酬）。"""
    cal, sig, RAW, trad, closes = S["cal"], S["sig"], S["RAW"], S["trad"], S["closes"]
    rows = []
    for i, r in enumerate(sig.itertuples()):
        s, e = r.sid, int(r.entry_pos); m = e - 1
        rw = RAW[s]; tb = trad[s]
        rc, ro, rl, F = rw["close"], rw["open"], rw["low"], rw["F"]
        mm = m; cm_fallback = False
        while mm >= 0 and not np.isfinite(rc[mm]):
            mm -= 1; cm_fallback = True
        cm = float(rc[mm])
        # 訊號日漲幅（還原；L8）
        ca = S["stk"][s].df["close"].to_numpy(float)
        pv = np.flatnonzero(np.isfinite(ca[:mm]))
        sret = ca[mm] / ca[pv[-1]] - 1.0 if len(pv) else np.nan
        st0, f0 = LE.fill_m0(e, ro, tb["trd"], tb["up_o"])
        st1, f1 = LE.fill_m0(e, ro, tb["trd"], tb["up_o"], allow_limit_up=True)
        oa_e = float(S["opens"][s][e]) if np.isfinite(S["opens"][s][e]) else np.nan
        rec = {"i": i, "sid": s, "m_pos": m, "e": e, "m_date": cal[m].date(), "e_date": cal[e].date(), "month": r.month,
               "year": cal[e].year, "close_m_raw": cm, "close_m_fallback": cm_fallback, "sigret": sret,
               "open_adj_e": oa_e, "M0_status": st0, "M0_fill_raw": f0, "M0p_status": st1, "M0p_fill_raw": f1,
               "M0_t": e if f0 is not None else np.nan, "M0p_t": e if f1 is not None else np.nan}
        for k in LE.KS:
            P = LE.limit_px(cm, k)
            t, px = LE.fill_limit(e, P, ro, rl, tb["trd"])
            rec[f"L{k}_P"] = P; rec[f"L{k}_t"] = t if t is not None else np.nan; rec[f"L{k}_fill_raw"] = px
            rec[f"L{k}_wait"] = (t - m) if t is not None else np.nan
            rec[f"L{k}_open_missing"] = bool(t is not None and not (np.isfinite(ro[t]) and ro[t] > 0))
            # 事件落在 (m, t]（或未成交時 (m, e+4]）⇒ 兩種讀法可能分岔
            hi = t if t is not None else min(e + LE.VALID_DAYS - 1, len(cal) - 1)
            rec[f"L{k}_event_in"] = bool(any(m < p <= hi for p in rw["ev_pos"]))
            # 讀法（乙）：還原尺度比（P × F(m)／F(t)，不取整）
            tb2, px2 = None, None
            for tt in range(e, min(e + LE.VALID_DAYS, len(cal))):
                if not tb["trd"][tt] or not (np.isfinite(rl[tt]) and rl[tt] > 0):
                    continue
                Pt = P * F[m] / F[tt]
                if rl[tt] <= Pt + LE.EPS:
                    tb2 = tt; px2 = min(ro[tt], Pt) if (np.isfinite(ro[tt]) and ro[tt] > 0) else Pt; break
            rec[f"L{k}b_t"] = tb2 if tb2 is not None else np.nan; rec[f"L{k}b_fill_raw"] = px2
        rows.append(rec)
    E = pd.DataFrame(rows)
    return E


def fill_mask(E, a):
    col = {"M0": "M0_fill_raw", "M0p": "M0p_fill_raw"}.get(a, f"{a}_fill_raw")
    return E[col].notna()


def pre(S):
    """開跑前報：⛔ 不看報酬。"""
    E = entries(S); n = len(E)
    out = {"快照": RI.H2.SHA, "訊號數": n, "相異檔": int(E["sid"].nunique())}
    fr = {}
    for a in ARMS:
        f = fill_mask(E, a)
        rec = {"成交": int(f.sum()), "放棄": int((~f).sum()), "成交率": float(f.mean())}
        if a.startswith("L"):
            w = E.loc[f, f"{a}_wait"].astype(int)
            rec["成交時點分佈（m+j）"] = {f"m+{j}": int((w == j).sum()) for j in range(1, 6)}
            rec["平均等待天數"] = float(w.mean())
            rec["成交日開盤缺值（以 P 成交）"] = int(E[f"{a}_open_missing"].sum())
            rec["事件落在 (m, 成交日或 e+4]（讀法甲乙可能分岔）"] = int(E[f"{a}_event_in"].sum())
            rec["讀法乙成交率（敏感度）"] = float(E[f"{a}b_fill_raw"].notna().mean())
        fr[ARM_NAME[a]] = rec
    out["各臂成交"] = fr
    st = E["M0_status"].value_counts().to_dict()
    out["M0狀態"] = {k: int(v) for k, v in st.items()}
    out["M0開盤漲停"] = {"筆數": int((E["M0_status"] == "limit_up").sum()), "比例": float((E["M0_status"] == "limit_up").mean())}
    out["訊號日收盤缺值（用前一有成交日收盤）"] = int(E["close_m_fallback"].sum())
    # 開跑前算術：H20 月區段下最多幾段、可能出口
    months = E["month"].nunique()
    blk20 = int(((E["e"] - S["w0"]) // 20).nunique())
    ndays = S["w1"] - S["w0"] + 1
    out["開跑前算術"] = {
        "主窗交易日": int(ndays), "有訊號的量測月（月區段數上限）": int(months), "20 日區段（有訊號）": blk20,
        "20 日區段理論上限": int(ndays // 20), "120 日區段理論上限": int(ndays // 120),
        "n_eff 上限 ＝ min(訊號數, 月數)": int(min(n, months)),
        "可能出口（判定 3 格同）": "n_eff 上限 {} ≥ 100 ⇒ 若無大量剔除，依構造落出口③；出口③ 內 結果①（CI 含 0）②（＋）③（−）三種都可能 ⇒ 不是退化解".format(min(n, months)),
        "出場剔除可把 n_eff 壓到 < 100 嗎": "要剔掉 ≥ {} 個整月才會；出場量不到的訊號見本體報（開跑前不算出場）".format(min(n, months) - 99),
        "H120": "120 日區段上限 {} ⇒ {}（描述）".format(int(ndays // 120), H120_SENTENCE)}
    os.makedirs(OUT, exist_ok=True)
    out["時戳"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")
    json.dump(out, open(os.path.join(OUT, "pre_run.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    E.to_csv(os.path.join(OUT, "pre_entries.csv.gz"), index=False)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return E


def exits(S, E):
    cal, ncal, trad, dl, closes, opens = S["cal"], S["ncal"], S["trad"], S["dl"], S["closes"], S["opens"]
    for H in HS:
        st, tx, px = [], [], []
        for r in E.itertuples():
            tb = trad[r.sid]; info = dl.get(r.sid, {"last": ncal - 1, "status": "live"})
            x = D.exit_pos(r.e, H)
            assert x == r.e + H - 1
            a, b, c = LE.exit_engine(r.e, H, closes[r.sid], opens[r.sid], tb["trd"], tb["dn_c"], tb["dn_o"], info["last"], info["status"])
            st.append(a); tx.append(b if b is not None else np.nan); px.append(c if c is not None else np.nan)
        E[f"x{H}_status"] = st; E[f"x{H}_t"] = tx; E[f"x{H}_px"] = px
    return E


def returns(E, S):
    RAW = S["RAW"]
    for H in HS:
        ok = E[f"x{H}_status"].isin(["ok", "exit_delayed", "delist_settled"])
        for a in ARMS:
            fcol = {"M0": "M0_fill_raw", "M0p": "M0p_fill_raw"}.get(a, f"{a}_fill_raw")
            tcol = {"M0": "M0_t", "M0p": "M0p_t"}.get(a, f"{a}_t")
            rr = []
            for r, g in zip(E.itertuples(), ok):
                if not g:
                    rr.append(np.nan); continue
                f = getattr(r, fcol)
                if f is None or not np.isfinite(f):
                    rr.append(0.0); continue
                t = int(getattr(r, tcol))
                rr.append(LE.arm_return(f, RAW[r.sid]["F"][t], getattr(r, f"x{H}_px")))
            E[f"r{H}_{a}"] = rr
        for k in LE.KS:                                   # 讀法（乙）敏感度
            rr = []
            for r, g in zip(E.itertuples(), ok):
                if not g:
                    rr.append(np.nan); continue
                f = getattr(r, f"L{k}b_fill_raw")
                if f is None or not np.isfinite(f):
                    rr.append(0.0); continue
                t = int(getattr(r, f"L{k}b_t"))
                rr.append(LE.arm_return(f, RAW[r.sid]["F"][t], getattr(r, f"x{H}_px")))
            E[f"r{H}_L{k}b"] = rr
    return E


def judge_cell(E, H, a, base="M0", w0=0):
    d = E[f"r{H}_{a}"] - E[f"r{H}_{base}"]
    ok = d.notna()
    x = d[ok].to_numpy(float); mon = E.loc[ok, "month"].to_numpy()
    cs = R11.cl_stats(x, mon)
    Dv, se, lo, hi, nm = LE.cluster_mean(x, mon)
    assert abs(Dv - cs["mean"]) < 1e-12 and abs(se - cs["se"]) < 1e-12, "⛔ cluster_mean 與 research11.cl_stats 不一致"
    blk = ((E.loc[ok, "e"] - w0) // 20).to_numpy()
    bm = pd.Series(x).groupby(blk).mean()
    se2 = float(bm.std(ddof=1) / np.sqrt(len(bm)))
    n_eff = int(min(len(x), nm))
    ex, res = LE.verdict(Dv, lo, hi, n_eff, len(x))
    return {"D": Dv, "se_月": se, "lo": lo, "hi": hi, "月數": nm, "n": len(x), "n_eff": n_eff, "n_eff_尺度": "量測月數" if nm <= len(x) else "訊號數",
            "se_非重疊20日": se2, "lo_非重疊": Dv - 1.96 * se2, "hi_非重疊": Dv + 1.96 * se2, "20日區段數": int(len(bm)),
            "E_臂": float(E.loc[ok, f"r{H}_{a}"].mean()), "E_M0": float(E.loc[ok, f"r{H}_{base}"].mean()), "出口": ex, "結果": res}


def arm_report(E, H, a):
    ok = E[f"r{H}_{a}"].notna(); Eo = E[ok]
    f = fill_mask(Eo, a)
    r = Eo[f"r{H}_{a}"]; rM0 = Eo[f"r{H}_M0"]; rM0p = Eo[f"r{H}_M0p"]
    rec = {"分母": int(len(Eo)), "成交": int(f.sum()), "成交率": float(f.mean()), "E（放棄＝0）": float(r.mean()),
           "成交那批平均報酬": float(r[f].mean()) if f.any() else np.nan,
           "放棄": int((~f).sum()),
           "放棄那批照 M0 買（M0 自己放棄記 0）": float(rM0[~f].mean()) if (~f).any() else np.nan,
           "放棄那批照 M0' 買（漲停也買到）": float(rM0p[~f].mean()) if (~f).any() else np.nan,
           "放棄那批照 M0 買_只算 M0 買得到的": float(rM0[~f & fill_mask(Eo, "M0")].mean()) if (~f & fill_mask(Eo, "M0")).any() else np.nan}
    if a.startswith("L"):
        rec["平均等待天數"] = float(Eo.loc[f, f"{a}_wait"].mean())
        adj_fill = np.array([fr * S_F for fr, S_F in zip(Eo.loc[f, f"{a}_fill_raw"], Eo.loc[f, f"{a}_F"])])
        oe = Eo.loc[f, "open_adj_e"].to_numpy(float)
        g = np.isfinite(oe)
        rec["成交那批：成交價比 M0 開盤省了（平均價差）"] = float(np.mean(adj_fill[g] / oe[g] - 1.0))
        rec["省了多少_分母（e 開盤有效）"] = int(g.sum())
        rec["成交那批同一筆照 M0 買（M0 放棄記 0）"] = float(rM0[f].mean())
        rec["成交時點分佈"] = {f"m+{j}": int((Eo.loc[f, f"{a}_wait"] == j).sum()) for j in range(1, 6)}
    else:
        rec["平均等待天數"] = 1.0 if f.any() else np.nan
    return rec


def split_table(E, H, key):
    rows = []
    for gv, g in E[E[f"r{H}_M0"].notna()].groupby(key, observed=True):
        rec = {key: str(gv), "訊號數": len(g), "M0漲停開盤": int((g["M0_status"] == "limit_up").sum())}
        for a in ARMS:
            rec[f"{a}_成交率"] = float(fill_mask(g, a).mean()); rec[f"{a}_E"] = float(g[f"r{H}_{a}"].mean())
        for k in LE.KS:
            rec[f"D_L{k}"] = rec[f"L{k}_E"] - rec["M0_E"]
        rec["M0p−M0"] = rec["M0p_E"] - rec["M0_E"]
        rows.append(rec)
    return pd.DataFrame(rows)


def body(S):
    t0 = time.time()
    E = entries(S)
    # 與開跑前報的成交完全一致（⛔ 開跑後不得改規則）
    pe = pd.read_csv(os.path.join(OUT, "pre_entries.csv.gz"), dtype={"sid": str})
    for c in ("M0_status", "L1_t", "L2_t", "L3_t", "L1_fill_raw", "L2_fill_raw", "L3_fill_raw"):
        a_, b_ = E[c].to_numpy(), pe[c].to_numpy()
        if E[c].dtype == object and c.endswith("status"):
            assert (a_ == b_).all(), c
        else:
            a_ = pd.to_numeric(pd.Series(a_), errors="coerce").to_numpy(float); b_ = pd.to_numeric(pd.Series(b_), errors="coerce").to_numpy(float)
            assert np.allclose(a_, b_, equal_nan=True, atol=1e-9), c
    for k in LE.KS:
        E[f"L{k}_F"] = [S["RAW"][s]["F"][int(t)] if np.isfinite(t) else np.nan for s, t in zip(E["sid"], E[f"L{k}_t"])]
    E = exits(S, E)
    E = returns(E, S)
    R_ = {"快照": RI.H2.SHA, "登錄": "PREREG限價 seq3 sha fddc47686e5339f9", "訊號數": len(E)}
    # ── 查核 A：M0 出場與 ref_interval_close.measure_close 逐筆相同（同一條引擎）
    M = RIC.measure_close(S["sig"], S["cal"], S["closes"], S["opens"], {s: S["stk"][s].df["high"].to_numpy(float) for s in S["RAW"]},
                          S["trad"], S["dl"], lambda e, h: D.exit_pos(e, h))
    chk = {}
    for H in HS:
        m = M[(M["h"] == H) & M["ret"].notna()].set_index("i")
        mine = E.set_index("i").loc[m.index, f"r{H}_M0"]
        chk[f"H{H}"] = {"比對筆數": int(len(m)), "最大差": float(np.nanmax(np.abs(mine.to_numpy(float) - m["ret"].to_numpy(float))))}
        st_m = M[M["h"] == H].set_index("i")["status"]
        both = E.set_index("i")[f"x{H}_status"]
        filled = st_m[~st_m.isin(["halt_in", "limit_up", "no_open"])]
        chk[f"H{H}_出場狀態相同"] = bool((both.loc[filled.index] == filled).all())
    g = S["sig"]["g_H120"].to_numpy(float)
    k_ = E[(E["x120_status"] == "ok") & fill_mask(E, "M0")]
    chk["g_H120 逐筆（status ok、M0 成交）最大差"] = float(np.max(np.abs(k_["r120_M0"].to_numpy(float) - (g[k_["i"]] - LE.COST_RT))))
    R_["查核A_引擎一致"] = chk
    print("[查核A] " + json.dumps(chk, ensure_ascii=False), flush=True)
    for H in HS:
        assert chk[f"H{H}"]["最大差"] < 1e-12 and chk[f"H{H}_出場狀態相同"]
    assert chk["g_H120 逐筆（status ok、M0 成交）最大差"] < 1e-12
    # ── 出場帳
    R_["出場帳"] = {f"H{H}": {k: int(v) for k, v in E[f"x{H}_status"].value_counts().items()} for H in HS}
    # ── 判定（H20）
    J = {}
    for k in LE.KS:
        J[f"L{k}"] = judge_cell(E, H_JUDGE, f"L{k}", w0=S["w0"])
    R_["判定_H20"] = J
    passed = {a: j for a, j in J.items() if j["結果"].startswith("結果②")}
    worse = {a: j for a, j in J.items() if j["結果"].startswith("結果③")}
    if passed:
        best = max(passed, key=lambda a: passed[a]["D"])
        k = int(best[1:])
        sent = ("進場 20 個交易日內，掛低 {}% 等買比隔天開盤直接買好：D {:+.2f}pp（CI 下緣 {:+.2f}pp）；區間＝訊號日收盤 ×（1 − {}%）以下、5 個交易日內"
                .format(k, passed[best]["D"] * 100, passed[best]["lo"] * 100, k))
        others = {a: {"D": j["D"], "lo": j["lo"], "hi": j["hi"], "結果": j["結果"]} for a, j in J.items() if a != best}
        R_["給使用者"] = {"取D最大那格": best, "句子": sent, "其餘格": others}
    else:
        R_["給使用者"] = {"句子": "直接進場（隔天開盤買）",
                        "理由": "三格沒有一格 D ＞ 0 且 CI 不含 0（{}）".format("；".join("{} {}".format(a, j["結果"]) for a, j in J.items())),
                        "較差的格": list(worse)}
    # ── §四 必報
    R_["必報"] = {}
    for H in HS:
        rep = {ARM_NAME[a]: arm_report(E, H, a) for a in ARMS}
        ok = E[f"r{H}_M0"].notna()
        lu = E[ok & (E["M0_status"] == "limit_up")]
        rep["M0 開盤漲停"] = {"筆數": int(len(lu)), "比例": float(len(lu) / ok.sum()), "那批照 M0' 買到的平均報酬": float(lu[f"r{H}_M0p"].mean()) if len(lu) else np.nan}
        dd = E.loc[ok, f"r{H}_M0p"] - E.loc[ok, f"r{H}_M0"]
        rep["M0' − M0（描述）"] = {"點估計": float(dd.mean())}
        if H == H_JUDGE:
            m_, se_, lo_, hi_, nm_ = LE.cluster_mean(dd.to_numpy(float), E.loc[ok, "month"].to_numpy())
            rep["M0' − M0（描述）"].update({"月分群CI（描述，⛔ 不判）": [lo_, hi_]})
        R_["必報"][f"H{H}"] = rep
    # H120：描述
    R_["H120描述"] = {"逐字": H120_SENTENCE, "點估計 D": {f"L{k}": float((E["r120_L%d" % k] - E["r120_M0"]).mean()) for k in LE.KS},
                    "120日區段數（有訊號）": int(((E.loc[E["r120_M0"].notna(), "e"] - S["w0"]) // 120).nunique())}
    # 讀法（乙）敏感度（H20、描述）
    sens = {}
    for k in LE.KS:
        d = (E[f"r20_L{k}b"] - E["r20_M0"]).dropna()
        m_, se_, lo_, hi_, nm_ = LE.cluster_mean(d.to_numpy(float), E.loc[d.index, "month"].to_numpy())
        sens[f"L{k}"] = {"D": m_, "CI（描述）": [lo_, hi_], "成交率": float(E.loc[d.index, f"L{k}b_fill_raw"].notna().mean()),
                         "兩讀法成交日不同的筆數": int((E[f"L{k}_t"].fillna(-1) != E[f"L{k}b_t"].fillna(-1)).sum())}
    R_["敏感度_讀法乙_還原尺度比價"] = sens
    # 分年、分訊號日漲幅三分位
    E["sigret_q"] = pd.qcut(E["sigret"], 3, labels=["低", "中", "高"])
    E["sigret_q"] = E["sigret_q"].astype(str)
    edges = pd.qcut(E["sigret"], 3, retbins=True)[1]
    R_["訊號日漲幅三分位切點"] = [float(x) for x in edges]
    for H in HS:
        split_table(E, H, "year").to_csv(os.path.join(OUT, f"by_year_H{H}.csv"), index=False, encoding="utf-8")
        split_table(E, H, "sigret_q").to_csv(os.path.join(OUT, f"by_sigret_H{H}.csv"), index=False, encoding="utf-8")
    R_["分年_H20"] = split_table(E, 20, "year").to_dict(orient="records")
    R_["分訊號日漲幅_H20"] = split_table(E, 20, "sigret_q").to_dict(orient="records")
    R_["假訊號臂"] = "登錄 §一～§六 沒有寫假訊號臂 ⇒ 本件不做"
    R_["時戳"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")
    R_["耗時秒"] = round(time.time() - t0)
    cols = ["i", "sid", "m_pos", "e", "m_date", "e_date", "month", "year", "close_m_raw", "close_m_fallback", "sigret", "sigret_q",
            "open_adj_e", "M0_status", "M0_fill_raw", "M0p_fill_raw"]
    for k in LE.KS:
        cols += [f"L{k}_P", f"L{k}_t", f"L{k}_fill_raw", f"L{k}_F", f"L{k}_wait", f"L{k}_event_in", f"L{k}b_t", f"L{k}b_fill_raw"]
    for H in HS:
        cols += [f"x{H}_status", f"x{H}_t", f"x{H}_px"] + [f"r{H}_{a}" for a in ARMS] + [f"r{H}_L{k}b" for k in LE.KS]
    E[cols].to_csv(os.path.join(OUT, "trades.csv.gz"), index=False)
    json.dump(R_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "pre"
    S = setup()
    if stage == "pre":
        pre(S)
    elif stage == "body":
        body(S)
    else:
        raise SystemExit("stage 只能是 pre／body")

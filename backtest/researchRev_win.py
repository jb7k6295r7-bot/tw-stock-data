# -*- coding: utf-8 -*-
"""PREREG反轉訊號 前瞻視窗補跑 {5, 10, 20, 60} 日（裁定 seq249；⚠ 事後追加）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchRev_win.py run|report [--procs 3]

⭐ 原程式一字不動：import researchRev（502cf9761f）的偵測、確認、0050 序列、讀檔；本檔只把「H＝20 寫死」的三處（事件窗、剔除範圍、報酬／基準）
   換成 H ∈ {5, 10, 20, 60}；個股層用延伸面板（resultsp9_engine/panel_ext.csv.gz，＝ supp_panelext 那一套）
═══ 口徑（照原件；每個 H 各自一套）═══
  事件：窗內 T ∈ [w0, w1 − H]（事件窗整個落在段內 ⇒ H 越長、段尾可用事件越少，照報）；同一訊號 20 個交易日內只取第一筆（先合併、再剔除）
  個股剔除：T＋1 停牌／開盤漲停／開盤跌停、[first, T＋H] 硬斷點；確認版：T＋1～T＋5 確認日 C、C＋H ≤ w1、[first, C＋H] 硬斷點、C＋1 同剔除
  報酬 R_H ＝ c[b＋H] ÷ o[b＋1] − 1（b＝T 或 C；b＋H 無成交 ⇒ 之前最後一根有效收盤）；⛔ 不扣成本（基準同）
  大盤層：X ＝ R_H − 同窗所有交易日 R_H 平均；CI 以 20 日區段分群（原件）；個股層：X ＝ R_H − 基準②（同月、同一天前 20 日報酬十分位同格的 R_H 平均）；CI 以月分群
  n_eff ＜ 10 ⇒ 依構造不可判定（seq246 先剔除、不計 k）；Bonferroni α ＝ 0.05／k，k ＝ 該層「訊號 × 版本 × 視窗」的可判定格數（照實算、不打折）
  通過 ＝ 高點 結果③、低點 結果②（出口照 PREREGH1 §五）
  扣成本版：X 往不利方向移 0.585%（低點 X − 0.585%、高點 X ＋ 0.585%；CI 同移）⇒「扣成本後仍過」＝ 移後 CI 仍整段在有利方向
  穩不穩（裁定 seq249 讀法）：通過的視窗，其相鄰視窗（5↔10↔20↔60）的差 X 與有利方向同號 ⇒「穩」；任一相鄰視窗反向 ⇒「只在 X 天看得到、不穩」
閘：H＝20 的每格事件數與差 X ＝ 原件（大盤層 resultsRev/cells.csv；個股層 resultsRev/supp_panelext_run/cells.csv）逐格相同
輸出 resultsRev/win_cells.csv、win_events_market.csv.gz、win_events_stock.csv.gz、win_stock_days.csv.gz、win_summary.json、win_run.log、WIN_REPORT.md
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from multiprocessing import Pool
from statistics import NormalDist
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchRev as RV

D, TR, H2, AV, MF = RV.D, RV.TR, RV.H2, RV.AV, RV.MF
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsRev")
PANEL = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
HS = (5, 10, 20, 60)
COST = 0.00585
TAG = "事後追加（裁定 seq249）"
_G: dict = {}


def universe(cal):
    from backtest import p4_features as P4F
    U = RV.UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    p = P4F.read_panel(PANEL)
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {sid: set(str(x)[:7] for x in g["measure_date"]) for sid, g in p.groupby("stock_id")}
    return sorted(elig), elig, U.set_index("stock_id")["market"]


# ═════════════════════════════ 個股（每檔）
def stock_win(args):
    sid, market = args
    cal, w0, w1, off, elig, mon = _G["cal"], _G["w0"], _G["w1"], _G["off"], _G["elig"], _G["mon"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df; n = len(cal)
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    ro, rh, rl, rc, _ = RV.load_raw(sid, cal)
    sel = lambda x: np.asarray(x, float)[bars]
    ev = RV.detect(sel(o), sel(h), sel(l), c[bars], sel(v), sel(ro), sel(rh), sel(rl), sel(rc))
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = MF._g5(valid, upto=ds["last"]) if delisted else MF._g5(valid)
    S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    lv = AV.last_valid(valid); em = elig.get(sid, set())
    halt = ~tb["trd"] | ~np.isfinite(o)

    def entry_bad(t):
        return "剔除_停牌" if halt[t + 1] else ("剔除_開盤漲停" if tb["up_o"][t + 1] else ("剔除_開盤跌停" if tb["dn_o"][t + 1] else None))
    rows = []
    for code in RV.CODES:
        top = RV.SIDE[code] == "高"
        if not ev[code]:
            continue
        T0 = bars[np.array([t for t, _ in ev[code]], int)]; F0 = bars[np.array([f for _, f in ev[code]], int)]
        for H in HS:
            m = (T0 >= w0) & (T0 <= w1 - H)
            T, F = T0[m], F0[m]
            if len(T):
                m2 = np.array([mon[t] in em for t in T], bool); T, F = T[m2], F[m2]
            keep = RV.merge20(T)
            for t, f, k in zip(T, F, keep):
                if not k:
                    continue
                r = {"sid": sid, "market": market, "code": code, "H": H, "T": int(t), "first": int(f)}
                why = "剔除_硬斷點" if H2.brk(S, int(f), int(t) + H) else entry_bad(t)
                r["st"] = why or "保留"
                C = RV.confirm_day(c, valid, h[t], l[t], int(t), top, w1)
                r["C"] = int(C)
                if C >= 0:
                    cw = "窗外" if C + H > w1 else ("剔除_硬斷點" if H2.brk(S, int(f), int(C) + H) else entry_bad(C))
                    r["st_c"] = cw or "保留"
                else:
                    r["st_c"] = "沒確認"
                if r["st"] == "保留":
                    r["R"] = float(c[lv[t + H]] / o[t + 1] - 1.0)
                if r["st_c"] == "保留":
                    r["Rc"] = float(c[lv[C + H]] / o[C + 1] - 1.0)
                rows.append(r)
    dd = np.arange(w0, w1 - HS[0] + 1)
    dd = dd[np.array([mon[t] in em for t in dd], bool)] if em else np.zeros(0, int)
    days = {"d": dd.astype(np.int32), "r20p": AV.r20_cal(c, bars)[dd]}
    for H in HS:
        R = np.full(len(dd), np.nan)
        m = dd + H <= w1
        if m.any():
            d_ = dd[m]
            ok = valid[d_] & ~halt[d_ + 1] & ~tb["up_o"][d_ + 1] & ~tb["dn_o"][d_ + 1] & ~AV.brk_vec(S["cs_pb"], S["cs_g5"], d_, d_ + H)
            with np.errstate(invalid="ignore", divide="ignore"):
                Rall = c[lv[d_ + H]] / o[d_ + 1] - 1.0
            R[m] = np.where(ok, Rall, np.nan)
        days[f"R{H}"] = R
    return {"sid": sid, "rows": rows, "days": days}


def _init(d):
    _G.update(d)


# ═════════════════════════════ 統計
def zb(k):
    return NormalDist().inv_cdf(1 - (0.05 / max(k, 1)) / 2)


def judge(code, X, g, z):
    X = np.asarray(X, float); n = len(X)
    if n == 0:
        return {"n": 0, "n_eff": 0, "判定": "不可判定"}
    m, se, ng = AV.cr0(X, np.asarray(g)); ne = int(min(n, ng))
    out = {"n": n, "n_eff": ne, "mean": m, "se": se}
    if ne < RV.NEFF_MIN:
        out.update(判定="不可判定", 出口="依構造不可判定", 結果="—")
        return out
    lo, hi = m - z * se, m + z * se
    ex, rs = AV.exit_result(m, lo, hi, n, ne)
    top = RV.SIDE[code] == "高"
    ok = rs == ("結果③" if top else "結果②")
    sh = COST if top else -COST                       # 扣成本：往不利方向移
    lo_n, hi_n = lo + sh, hi + sh
    ok_n = ok and (hi_n < 0 if top else lo_n > 0)
    out.update(lo=lo, hi=hi, 出口=ex, 結果=rs, 判定="通過" if ok else "不通過", mean_net=m + sh, lo_net=lo_n, hi_net=hi_n,
               扣成本後="仍過" if ok_n else ("不過" if ok else "—"))
    return out


def stability(C):
    """裁定 seq249 讀法：每個（層、訊號、版本）⇒ 描述字串。"""
    out = {}
    for (lay, code, ver), g in C.groupby(["層", "code", "版"]):
        g = g.set_index("H").reindex(list(HS))
        top = RV.SIDE[code] == "高"
        fav = lambda x: (x < 0) if top else (x > 0)
        passed = [H for H in HS if g.at[H, "判定"] == "通過"]
        if not passed:
            out[(lay, code, ver)] = "四個視窗都不通過" if (g["判定"] != "不可判定").any() else "四個視窗都依構造不可判定"
            continue
        parts = []
        for H in passed:
            i = HS.index(H); nb = [HS[j] for j in (i - 1, i + 1) if 0 <= j < len(HS)]
            nb_ok = [H2_ for H2_ in nb if np.isfinite(g.at[H2_, "mean"]) and fav(g.at[H2_, "mean"])]
            if len(nb_ok) == len(nb):
                nb_pass = [x for x in nb if g.at[x, "判定"] == "通過"]
                note = "相鄰也通過" if len(nb_pass) == len(nb) else ("相鄰同向但本身不顯著" if not nb_pass else f"相鄰 {'／'.join(str(x) for x in nb_pass)} 天也通過")
                parts.append(f"{H} 天通過、相鄰視窗（{'／'.join(str(x) for x in nb)} 天）同向（{note}）⇒ 穩（照裁定 seq249 字面）")
            else:
                bad = [x for x in nb if x not in nb_ok]
                parts.append(f"只在 {H} 天看得到、不穩（相鄰 {'／'.join(str(x) for x in bad)} 天方向相反）")
        out[(lay, code, ver)] = "；".join(parts)
    return out


# ═════════════════════════════ 主程式
def run(a):
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "win_run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("researchRev_win.py", "researchRev.py")}
    log(f"===== researchRev_win run procs={a.procs} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜{src} =====")
    cal = D.load_calendar(); mon = np.array([str(d)[:7] for d in cal])
    w0, w1 = int(cal.searchsorted(pd.Timestamp(RV.W0))), int(cal.searchsorted(pd.Timestamp(RV.W1)))
    S = {"性質": TAG, "程式": src, "面板": {"路徑": PANEL, "sha256": hashlib.sha256(open(PANEL, "rb").read()).hexdigest()[:16]}}
    cells = []; evm = []
    # ── 大盤層（主窗）
    Mm, Ms, info = RV.market_series()
    ev = RV.detect_series(Mm)
    dM = Mm["dates"]; lo, hi = int(np.searchsorted(dM, RV.W0)), int(np.searchsorted(dM, RV.W1))
    for H in HS:
        bd = RV.base_days(Mm, lo, hi, H)
        base = np.array([RV.fwd(Mm, d, H, hi) for d in bd]); bm = float(base.mean())
        S[f"大盤基準_H{H}"] = {"R平均": bm, "日數": int(len(base)), "跌比例": float((base < 0).mean()), "漲比例": float((base > 0).mean())}
        for code in RV.CODES:
            top = RV.SIDE[code] == "高"
            T = np.array([t for t, _ in ev[code]], int); F = np.array([f for _, f in ev[code]], int)
            m = (T >= lo) & (T <= hi - H); T, F = T[m], F[m]
            keep = RV.merge20(T)
            E = []
            for t, f, k in zip(T, F, keep):
                if not k:
                    continue
                st = "保留" if np.isfinite(Mm["o"][t + 1]) else "剔除_停牌"
                C = RV.confirm_day(Mm["c"], Mm["valid"], Mm["h"][t], Mm["l"][t], t, top, hi)
                stc = "沒確認" if C < 0 else ("窗外" if C + H > hi else ("保留" if np.isfinite(Mm["o"][C + 1]) else "剔除_停牌"))
                E.append((t, C, st, stc))
            for ver in ("原版", "確認版"):
                b = np.array([t for t, C, st, stc in E if st == "保留"] if ver == "原版" else [C for t, C, st, stc in E if stc == "保留"], int)
                R = np.array([RV.fwd(Mm, d, H, hi) for d in b])
                for d, r in zip(b, R):
                    evm.append({"code": code, "版": ver, "H": H, "基準日": dM[d], "R": r})
                cells.append({"層": "大盤", "code": code, "名": RV.NAME[code], "邊": RV.SIDE[code], "版": ver, "H": H, "_X": R - bm, "_g": (b - lo) // 20,
                              "成功率": RV.succ(code, R) if len(R) else np.nan, "基準成功率": RV.succ(code, base),
                              "R平均": float(R.mean()) if len(R) else np.nan, "基準R平均": bm, "候選事件（窗內、合併後）": int(keep.sum())})
    # ── 個股層
    sids, elig, mk = universe(cal)
    init = {"cal": cal, "w0": w0, "w1": w1, "off": TR.load_official(), "elig": elig, "mon": mon}
    res = []; t0 = time.time()
    with Pool(a.procs, initializer=_init, initargs=(init,)) as pool:
        for i, r in enumerate(pool.imap_unordered(stock_win, [(s, mk.get(s, "twse")) for s in sids], chunksize=4)):
            if r is not None:
                res.append(r)
            if (i + 1) % 400 == 0:
                log(f"  [個股] {i + 1}/{len(sids)}｜{time.time() - t0:.0f}s")
    rows = pd.DataFrame([r for x in res for r in x["rows"]])
    rows.to_csv(os.path.join(OUT, "win_events_stock.csv.gz"), index=False, float_format="%.17g")
    DD = pd.concat([pd.DataFrame({"sid": x["sid"], **x["days"]}) for x in res if len(x["days"]["d"])], ignore_index=True).sort_values(["d", "sid"]).reset_index(drop=True)
    dec = np.full(len(DD), -1, int)
    for d, idx in DD.groupby("d").indices.items():
        dec[idx] = AV.deciles(DD["r20p"].to_numpy()[idx])
    DD["dec"] = dec; DD["m"] = mon[DD["d"].to_numpy()]
    DD.drop(columns=["m"]).to_csv(os.path.join(OUT, "win_stock_days.csv.gz"), index=False, float_format="%.17g")
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], DD["dec"])}
    S["個股股日"] = int(len(DD))
    for H in HS:
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec"] >= 0)]
        B2 = f.groupby(["m", "dec"])[f"R{H}"].mean()
        side_neg = f.assign(x=f[f"R{H}"] < 0).groupby(["m", "dec"])["x"].mean(); side_pos = f.assign(x=f[f"R{H}"] > 0).groupby(["m", "dec"])["x"].mean()
        S[f"個股基準_H{H}"] = {"有報酬股日": int(np.isfinite(DD[f"R{H}"]).sum()), "R平均": float(DD[f"R{H}"].mean())}
        e = rows[rows["H"] == H]
        for code in RV.CODES:
            ec = e[e["code"] == code]
            for ver in ("原版", "確認版"):
                k = ec[ec["st"] == "保留"] if ver == "原版" else ec[ec["st_c"] == "保留"]
                bd = k["T"].to_numpy(int) if ver == "原版" else k["C"].to_numpy(int)
                R = k["R"].to_numpy(float) if ver == "原版" else k["Rc"].to_numpy(float)
                mm = mon[bd] if len(bd) else np.zeros(0, str)
                q = [key.get((s, int(d)), -1) for s, d in zip(k["sid"], bd)]
                b2 = np.array([B2.get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
                sneg = np.array([side_neg.get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
                spos = np.array([side_pos.get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
                ok = np.isfinite(b2)
                cells.append({"層": "個股", "code": code, "名": RV.NAME[code], "邊": RV.SIDE[code], "版": ver, "H": H, "_X": R[ok] - b2[ok], "_g": mm[ok],
                              "成功率": RV.succ(code, R[ok]) if ok.any() else np.nan,
                              "基準成功率": float((sneg if RV.SIDE[code] == "高" else spos)[ok].mean()) if ok.any() else np.nan,
                              "R平均": float(R[ok].mean()) if ok.any() else np.nan, "基準R平均": float(b2[ok].mean()) if ok.any() else np.nan,
                              "候選事件（窗內、合併後）": int(len(ec)), "基準2缺": int((~ok).sum())})
    # ── 判定
    for lay in ("大盤", "個股"):
        L_ = [c for c in cells if c["層"] == lay]
        for c in L_:
            c["n_eff"] = int(min(len(c["_X"]), len(np.unique(c["_g"])))) if len(c["_X"]) else 0
        k = sum(1 for c in L_ if c["n_eff"] >= RV.NEFF_MIN)
        z = zb(k); S[f"Bonferroni_{lay}"] = {"k": k, "α": 0.05 / max(k, 1), "z": z, "k 的算法": "訊號 × 版本 × 視窗 可判定格（n_eff ≥ 10）"}
        for c in L_:
            c.update(judge(c["code"], c["_X"], c["_g"], z)); c["事件"] = int(len(c["_X"]))
    C = pd.DataFrame([{k: v for k, v in c.items() if not k.startswith("_")} for c in cells])
    stab = stability(C)
    C["穩不穩"] = [stab[(r.層, r.code, r.版)] for r in C.itertuples()]
    C.to_csv(os.path.join(OUT, "win_cells.csv"), index=False)
    pd.concat([pd.DataFrame({"層": c["層"], "code": c["code"], "版": c["版"], "H": c["H"], "X": c["_X"], "g": c["_g"]}) for c in cells],
              ignore_index=True).to_csv(os.path.join(OUT, "win_cell_x.csv.gz"), index=False, float_format="%.17g")
    pd.DataFrame(evm).to_csv(os.path.join(OUT, "win_events_market.csv.gz"), index=False, float_format="%.17g")
    # ── 閘：H＝20 ＝ 原件
    A = pd.read_csv(os.path.join(OUT, "cells.csv")); Bsup = pd.read_csv(os.path.join(OUT, "supp_panelext_run", "cells.csv"))
    bad = []
    for r in C[C["H"] == 20].itertuples():
        ref = (A[(A["層"] == "大盤") & (A["段"] == "主窗")] if r.層 == "大盤" else Bsup[Bsup["層"] == "個股"])
        q = ref[(ref["code"] == r.code) & (ref["版"] == r.版)].iloc[0]
        if int(q["事件"]) != int(r.事件) or (r.事件 and not np.isclose(float(q["mean"]), float(r.mean), rtol=0, atol=1e-12)):
            bad.append((r.層, r.code, r.版, int(q["事件"]), int(r.事件)))
    S["閘_H20＝原件"] = {"不一致": len(bad), "例": bad[:5]}
    log(f"[閘 H20＝原件] {S['閘_H20＝原件']}")
    S["秒"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(OUT, "win_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if bad:
        raise SystemExit("⛔ 閘不過：H＝20 與原件不同")
    report()
    log(f"[完成] {time.time() - t00:.0f}s")


def report():
    S = json.load(open(os.path.join(OUT, "win_summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "win_cells.csv"))
    stab = stability(C); C["穩不穩"] = [stab[(r.層, r.code, r.版)] for r in C.itertuples()]
    C.to_csv(os.path.join(OUT, "win_cells.csv"), index=False)
    p_ = lambda x: "—" if not np.isfinite(x) else f"{x * 100:+.2f}%"
    r_ = lambda x: "—" if not np.isfinite(x) else f"{x * 100:.1f}%"
    P = C[C["判定"] == "通過"]
    L = [f"# PREREG反轉訊號 前瞻視窗 {{5, 10, 20, 60}} 日（⚠ {TAG}）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。個股層用延伸面板（panel_ext）；Bonferroni k：大盤 {S['Bonferroni_大盤']['k']}、個股 {S['Bonferroni_個股']['k']}"
         "（訊號 × 版本 × 視窗 的可判定格，照實算）。", ""]
    if len(P):
        L.append("**結論（事後追加）：通過的格 " + "、".join(f"{r.層}{r.版}〔{r.名}〕{r.H} 天" for r in P.itertuples()) + "；其餘看不出比基準準。**")
    else:
        L.append("**結論（事後追加）：四個視窗、兩層、兩版全部沒有通過的格。**")
    L += ["", "小表：每格寫 5／10／20／60 天（✓ 通過、✗ 不通過、· 依構造不可判定；✓ 後括號＝扣 0.585% 後仍過／不過）", "",
          "| 訊號 | 邊 | 大盤 原版 | 大盤 確認版 | 個股 原版 | 個股 確認版 |", "|---|---|---|---|---|---|"]

    def mark(lay, code, ver):
        g = C[(C["層"] == lay) & (C["code"] == code) & (C["版"] == ver)].set_index("H")
        s_ = []
        for H in HS:
            v = g.at[H, "判定"]
            s_.append(f"{H}{'✓' + ('(仍過)' if g.at[H, '扣成本後'] == '仍過' else '(不過)') if v == '通過' else ('✗' if v == '不通過' else '·')}")
        return " ".join(s_)
    for code in RV.CODES:
        L.append(f"| {RV.NAME[code]} | {RV.SIDE[code]}點 | {mark('大盤', code, '原版')} | {mark('大盤', code, '確認版')} | {mark('個股', code, '原版')} | {mark('個股', code, '確認版')} |")
    L += ["", "## 讀法（裁定 seq249）：通過的格穩不穩", ""]
    for r in C.drop_duplicates(["層", "code", "版"]).itertuples():
        if r.穩不穩.startswith(("只在", "5 天", "10 天", "20 天", "60 天")):
            L.append(f"- {r.層} {r.版}〔{r.名}〕：{r.穩不穩}")
    L += ["", "## 每視窗事件數（段尾可用事件隨 H 變少）", "", "| 層 | 版 | " + " | ".join(f"H{H} 事件合計" for H in HS) + " |", "|---|---|" + "---|" * len(HS)]
    for lay in ("大盤", "個股"):
        for ver in ("原版", "確認版"):
            L.append(f"| {lay} | {ver} | " + " | ".join(str(int(C[(C['層'] == lay) & (C['版'] == ver) & (C['H'] == H)]['事件'].sum())) for H in HS) + " |")
    for lay in ("大盤", "個股"):
        L += ["", f"## {lay}層 明細（差 ＝ R_H − 基準{'（同窗所有交易日）' if lay == '大盤' else '②'}；CI 為 Bonferroni）", "",
              "| 訊號 | 版 | H | 事件 | n_eff | 成功率／基準 | 差 X | CI | 扣成本後差（CI） | 出口／結果 | 判定 | 扣成本後 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in C[C["層"] == lay].sort_values(["code", "版", "H"]).itertuples():
            L.append(f"| {r.名} | {r.版} | {r.H} | {r.事件} | {r.n_eff} | {r_(r.成功率)}／{r_(r.基準成功率)} | {p_(r.mean) if r.事件 else '—'} | "
                     f"[{p_(r.lo)}, {p_(r.hi)}] | {p_(r.mean_net)}（[{p_(r.lo_net)}, {p_(r.hi_net)}]） | {r.出口}／{r.結果} | {r.判定} | {r.扣成本後 if isinstance(r.扣成本後, str) else '—'} |")
    L += ["", "## 沿革", "", f"- {TAG}：20 日原結果保留不動（resultsRev/REPORT.md；個股層以延伸版為準見其「沿革」）；本表的 20 日格因 Bonferroni k 改為訊號 × 版本 × 視窗而另判，⛔ 不取代原判定",
          f"- 閘：H＝20 的每格事件數與差 ＝ 原件（大盤層 cells.csv、個股層 supp_panelext_run/cells.csv）：{S.get('閘_H20＝原件')}",
          f"- 面板：{S.get('面板')}；程式：{S.get('程式')}", ""]
    open(os.path.join(OUT, "WIN_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["run", "report"]); ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    run(a) if a.mode == "run" else report()

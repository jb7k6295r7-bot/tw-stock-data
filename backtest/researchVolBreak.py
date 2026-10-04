# -*- coding: utf-8 -*-
"""PREREG爆量突破進跌破EMA出 seq2（台股策略線登錄 sha 0c44c9e73bba2397，2026-10-04 21:20；裁定 seq299 §三 發號、N_組合 ＋1；seq1 作廢）。回測線。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVolBreak body [--procs 4]
    抽樣查核：同一支 --check（⛔ 不呼叫本體的訊號、列、引擎包裝函式，從原始 CSV 自算）；網頁：同一支 page

⭐ 讀法寫死時間：2026-10-04 22:20（台北）；寫死前 ⛔ 沒看任何本組合的報酬（22:1x 原型只印了訊號筆數與引擎秒數，用來定種子數）。

═══ 規則（登錄 §一～§三，逐字機器化）═══
  有效 K 棒序列上算（全專案慣例）：
  突破：還原收盤 ＞ 前 B 根有效 K 棒（不含當根）還原最高價的最大值，且 原始收盤 ＞ 原始開盤（紅K）；B ∈ {5, 10, 20, 60, 120}
  爆量：原始成交股數 ＞ k × 前 20 根有效 K 棒（t−20～t−1）原始成交股數平均，且該平均 ＞ 0；k ∈ {1.5, 2.0, 3.0}
  EMA(L)：還原收盤的 EMA，α ＝ 2／(L＋1)，第一根以收盤起算（＝ Pine ta.ema 與 pandas ewm(span＝L, adjust＝False)）；L ∈ {5, 10, 20, 60}
  EMA 暖機：該檔有效 K 棒序號 ≥ 3L 才可進場（登錄「上市櫃滿 3×L 交易日」；序號從本資料版面第一根算，執行者補）
  進場：訊號日 t 收盤判定 ⇒ t＋1 開盤（引擎：開盤漲停或停牌買不到 ⇒ 該名額持現金，tradable）；已持有同檔不加碼（引擎 held）
  出場：持有期間（d ≥ 進場日 e）第一個 還原收盤 ＜ EMA(L) 的日子 d ⇒ d＋1 開盤賣（引擎 stop_line 必觸發線；開盤跌停／停牌順延）；
        段尾仍未出場 ⇒ 段尾收盤計值（⛔ 無時間出口、無停損）
  ⭐ 同日：訊號日 t 自己就「收盤 ＜ EMA(L)」⇒ 該進場訊號不進（執行者補：Pine 在持有中時 t 不會進場、t 出場；
        researchSig／訊號系統均線出場「同日有出場訊號就不進」同一條；⚠ 未持有時 Pine 會進場再於 t＋1 收盤判出，本讀法略過，筆數照報）
  再進場：賣出後可再進（同檔多列，引擎自然處理）
═══ 沿用（訊號系統骨架，researchSig 2fe5809e9b／researchSigMA ffd6dd0875）═══
  引擎 research11.simulate_mtm：N＝10、每檔買進投入當時淨值 1/10、同日多於空格 ⇒ rng.permutation 抽籤（種子 1000＋r）、成本來回 0.585%；
  價格 rerun17.load_prices（還原、收盤 ffill）；tradable（tradability.one：開盤漲停買不到、開盤跌停賣不掉）＋ delist ＋ 停止交易強制出場（stop_force）
  母體：W1 eligible（訊號日 t 那個月的面板）∩ gate3，⭐ UG.set_gate_v2(True)（裁定 seq296）⇒ 另要求訊號日 t 的 pit_valid 為真；含已下市
  段：探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24（面板 panel_ext）；各段獨立起跑、期初全現金；進場 e＝t＋1 ∈ 段內
      早年 2005-02-01～2014-12-30（early 版面 3edc0e2206、只上市；⚠ 2012-06 以前沒有個股法人 ⇒ 早年母體用 eligible_v ＝ liq_ok ∧ bars_ok，
      同 researchMomX R10，執行者補）
  0050 同段 ＝ rerun17.bench_row（同 researchSigMA）
═══ 種子數（執行者補；登錄只寫「抽籤（固定種子）」）═══
  原型（300 檔）最重一格 1.2 秒／顆 ⇒ 全母體 60＋20 格 × 3 段 × 200 顆約 10 小時 ⇒ 改：主格與 S 臂 50 顆（種子 1000～1049，取年化中位、回落中位）；
  固定抱 20／60／120 對照 10 顆（1000～1009）；隨機出場對照只做確認段、每格 100 次（持有天數從本格確認段 50 顆的實際持有天數池放回抽；
  抽樣 default_rng([20261004, 格序, i])、引擎 1000＋i mod 50；p ＝ 隨機年化 ≥ 本格年化中位 的比例，解析度 0.01）；現實版（researchSlip C1 0.3%＋C2 50 萬＋C4 均價）
  只做確認段、10 顆（⭐ 22:25 冒煙測試量完耗時後定：固定持有 20→10 顆、現實版 20→10 顆；冒煙只用 120 檔、不是本件數字）
═══ 判法（登錄 §四，⛔ 看數字前寫死）═══
  每格每段：年化中位 ＞ 0050 且 比值 ≥ 0050 比值 ⇒ 合格；只過年化 ⇒ 另列；否則不合格
  整套：確認段 ≥ 31 格合格 且 探索段 ≥ 31 格合格 ⇒ 合格；否則兩段各 ≥ 31 格「合格或另列」⇒ 另列；其餘 ⇒ 不合格；早年段 ＜ 31 格合格 ⇒ 最多「暫定」
  退化標記（只標、仍計入分母）：探索段 平均持有 ＜ 2 日 ⇒「依構造近似天天換手」
═══ 描述（⛔ 不判、不計 N）═══
  S 臂（拿掉爆量；B × L ＝ 20 格）：M − S（同 B、L，k 三值）年化差；按 B／k／L 分組報合格格數；EMA 出場 − 固定抱 20／60／120 年化差
  單筆層：訊號後 H ∈ {5, 10, 20, 60}：R ＝ 還原收盤(t＋H) ÷ 還原開盤(t＋1) − 1；X ＝ R − 基準②（同日 eligible 中前 20 根報酬同十分位股票的同式 R 等權平均）；
          另報 R − 0.585%；月分群 95% CI（訊號日所在曆月為群）；只看 (B, k) 15 組
  每年訊號數、每格交易筆數、勝率、平均賺賠比（平均賺 ÷ |平均賠|）、平均持有天數、年換手（買進金額 ÷ 前一日淨值，年均）、空倉比例
輸出 backtest/resultsVolBreak/（summary.json、cells.csv、seeds.csv.gz、single.csv、fake_p.csv、check.json、爆量突破跌破EMA出.html）
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
import researchSig as RS
RV, D, RR, R11 = RS.RV, RS.D, RS.RR, RS.R11
from backtest import tradability as TR
from backtest import p4_features as P4F

OUT = os.path.join(RS.HERE, "resultsVolBreak")
BS, KS, LS = (5, 10, 20, 60, 120), (1.5, 2.0, 3.0), (5, 10, 20, 60)
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
EARLY = ("2005-02-01", "2014-12-30")
NSEED, NFIX, NRAND, NREAL = 50, 10, 100, 10
COST = R11.COST
TAGT = "2026-10-04 22:20（台北）"
_G: dict = {}


def set_v2(on):
    for nm in ("backtest.universe_gate", "universe_gate"):
        if nm in sys.modules:
            sys.modules[nm].set_gate_v2(on)


def UGm():
    return sys.modules.get("universe_gate") or sys.modules["backtest.universe_gate"]


# ═════════════ 每檔特徵 ═════════════
def feats_one(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float)
    ro, rh, rl, rc, rv = RV.load_raw(sid, cal)
    b = np.flatnonzero(np.isfinite(c) & np.isfinite(h))
    if len(b) < 25:
        return sid, None
    cb, hb, vb = c[b], h[b], rv[b]
    red = np.isfinite(rc[b]) & np.isfinite(ro[b]) & (rc[b] > ro[b])
    va = pd.Series(vb).rolling(20, min_periods=20).mean().shift(1).to_numpy()
    out = {"E": {}, "S": {}, "BEL": {}, "WARM": {}}
    for B in BS:
        hh = pd.Series(hb).rolling(B, min_periods=B).max().shift(1).to_numpy()
        with np.errstate(invalid="ignore"):
            brk = (cb > hh) & red & np.isfinite(hh)
        out["S"][B] = b[brk]
        for k in KS:
            with np.errstate(invalid="ignore"):
                out["E"][(B, k)] = b[brk & np.isfinite(va) & (va > 0) & (vb > k * va)]
    for L in LS:
        ema = pd.Series(cb).ewm(span=L, adjust=False).mean().to_numpy()
        out["BEL"][L] = b[cb < ema]
        out["WARM"][L] = int(b[3 * L]) if len(b) > 3 * L else 10 ** 9
    out["PIT"] = np.packbits(UGm().pit_valid(sid, cal))
    return sid, out


def world(name, data, panel, w, procs, log, elig_v=False, twse_only=False):
    D.DATA = data
    cal = D.load_calendar(); n = len(cal); mon = np.array([str(x)[:7] for x in cal])
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UGm().gate3(stocks)
    if twse_only:
        U = U[U["market"] == "twse"]
    p = P4F.read_panel(panel)
    if elig_v:
        p["el"] = p["liq_ok"].astype(bool) & p["bars_ok"].astype(bool)
    else:
        p["el"] = p["eligible"].astype(bool)
    p = p[p["el"] & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {sid: set(str(x)[:7] for x in g["measure_date"]) for sid, g in p.groupby("stock_id")}
    mk = U.set_index("stock_id")["market"].to_dict()
    sids = sorted(elig)
    if os.environ.get("VB_SMOKE"):                             # 只給冒煙測試（程式能不能跑完）；正式交件不用
        sids = sids[:120]
    _G["cal"] = cal
    with Pool(procs) as pool:
        F = dict(pool.map(feats_one, [(s, mk.get(s, "twse")) for s in sids], chunksize=8))
    F = {s: v for s, v in F.items() if v is not None}
    for s in F:
        F[s]["PIT"] = np.unpackbits(F[s]["PIT"])[:n].astype(bool)
    cz, oz = RR.load_prices(sorted(F), cal, mk, "branch")
    TRD = {s: TR.one(s, cal) for s in cz}
    DL = TR.delist_status({s: {"trd": v["trd"]} for s, v in TRD.items()}, cal, official=TR.load_official())
    segs = {k: (int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b_)))) for k, (a, b_) in w.items()}
    s1max = max(v[1] for v in segs.values())
    SF = R11.stop_force_days(R11.valid_from_data(sorted(cz), mk, cal), s1max)
    bench = RR.load_bench(cal)
    B50 = {k: RR.bench_row(cal, bench, a, b_ + 1) for k, (a, b_) in segs.items()}
    log(f"[世界 {name}] {data}｜日曆 {cal[0].date()}～{cal[-1].date()}｜母體 {len(F):,} 檔｜段 { {k: [str(cal[a].date()), str(cal[b_].date())] for k, (a, b_) in segs.items()} }｜停止交易 {len(SF)}")
    return {"name": name, "cal": cal, "n": n, "mon": mon, "elig": elig, "mk": mk, "F": F, "cz": cz, "oz": oz, "TRD": TRD, "DL": DL, "SF": SF,
            "segs": segs, "B50": B50, "bench": bench}


# ═════════════ 列與格 ═════════════
def rows_of(Wd, B, k, L, seg):
    """(B, k 或 None＝S 臂, L) ⇒ DataFrame sid, t, entry_pos, dX；回 (R, 同日不進筆數, 暖機擋, 母體擋)。"""
    s0, s1 = Wd["segs"][seg]; mon = Wd["mon"]
    rows = []; same = warm = outu = 0
    for sid, f in Wd["F"].items():
        ent = f["E"][(B, k)] if k is not None else f["S"][B]
        ent = ent[(ent + 1 >= s0) & (ent + 1 <= s1)]
        if not len(ent):
            continue
        em = Wd["elig"].get(sid, set())
        bel = f["BEL"][L]; belset = set(bel.tolist())
        for t in ent:
            t = int(t)
            if mon[t] not in em or not f["PIT"][t]:
                outu += 1; continue
            if t < f["WARM"][L]:
                warm += 1; continue
            if t in belset:
                same += 1; continue
            e = t + 1; i = int(np.searchsorted(bel, e))
            d = int(bel[i]) if i < len(bel) and bel[i] <= s1 else -1
            rows.append((sid, t, e, d))
    return pd.DataFrame(rows, columns=["sid", "t", "entry_pos", "dX"]), same, warm, outu


def ep_of(Wd, s, e):
    o = float(Wd["oz"][s][e])
    return o if (np.isfinite(o) and o > 0) else float(Wd["cz"][s][e])


def cell_sig(Wd, R, seg, mode="ema", H=None, dX=None, opens=None):
    s1 = Wd["segs"][seg][1]; cz = Wd["cz"]
    oz = opens or Wd["oz"]
    sid = R["sid"].to_numpy(); e = R["entry_pos"].to_numpy(int)
    if mode == "fix":
        xp = np.minimum(e + H - 1, s1 + 1)
        sig = pd.DataFrame({"sid": sid, "entry_pos": e, "xpos_X": xp})
        sig["g_X"] = [float(cz[s][x]) / (float(oz[s][ee]) if np.isfinite(oz[s][ee]) and oz[s][ee] > 0 else float(cz[s][ee])) - 1.0 for s, ee, x in zip(sid, e, xp)]
        return sig, {}
    d = R["dX"].to_numpy(int) if dX is None else dX
    sig = pd.DataFrame({"sid": sid, "entry_pos": e, "xpos_X": s1 + 1})
    sig["g_X"] = [float(cz[s][s1 + 1]) / (float(oz[s][ee]) if np.isfinite(oz[s][ee]) and oz[s][ee] > 0 else float(cz[s][ee])) - 1.0 for s, ee in zip(sid, e)]
    sl = {(s, int(ee)): (int(dd), np.array([RS.BIG])) for s, ee, dd in zip(sid, e, d) if 0 <= dd <= s1}
    return sig, {"stop_line": sl}


def run_one(args):
    jk, r, seed = args
    J = _G["JOB"][jk]
    Wd = _G["W"][J["w"]]
    if J.get("lazy") == "fix":                                 # 固定持有：工作程序內現建（省記憶體）
        sig, kw = cell_sig(Wd, _G["ROWS"][J["rk"]], J["seg"], mode="fix", H=J["H"])
    elif J.get("lazy") == "rand":                              # 隨機出場：本格持有天數池放回抽
        R = _G["ROWS"][J["rk"]]; pool_ = _G["POOL"][J["rk"]]
        rng = np.random.default_rng([20261004, J["ci"], J["i"]])
        dd = R["entry_pos"].to_numpy(int) + rng.choice(pool_, size=len(R), replace=True) - 1 if len(pool_) else np.full(len(R), -1)
        sig, kw = cell_sig(Wd, R, J["seg"], dX=dd)
    else:
        sig, kw = J["sig"], J["kw"]
    s0, s1 = Wd["segs"][J["seg"]]
    au = []
    cost = J.get("cost", COST)
    R11.COST = cost
    try:
        o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(seed), Wd["cz"], J.get("opens") or Wd["oz"], Wd["n"], return_equity=True, audit=au,
                             tradable=Wd["TRD"], delist=Wd["DL"], stop_force=Wd["SF"], **kw)
    finally:
        R11.COST = COST
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    res = {"job": jk, "r": r, "cagr": float(c_), "mdd": float(m_)}
    if J.get("stats"):
        openb = {}; nets = []; holds = []; buyamt = 0.0
        for a in au:
            t = int(a["t"])
            if a["side"] == "buy":
                openb[a["sid"]] = (t, float(a["amt"]))
                if s0 <= t <= s1 and a.get("equity_prev"):
                    buyamt += float(a["amt"]) / float(a["equity_prev"])
            else:
                b = openb.pop(a["sid"], None)
                if b and t <= s1:
                    nets.append((float(a["amt"]) - float(a.get("cost", 0))) / b[1] - 1.0); holds.append(t - b[0])
        nets = np.array(nets); yrs = (Wd["cal"][s1] - Wd["cal"][s0]).days / 365.25
        with np.errstate(invalid="ignore", divide="ignore"):
            cash = float(np.nanmean(1.0 - hv[s0:s1 + 1] / eq[s0:s1 + 1]))
        win = nets[nets > 0]; loss = nets[nets <= 0]
        res.update({"trades": int(len(nets)), "win": float((nets > 0).mean()) if len(nets) else np.nan,
                    "payoff": float(win.mean() / abs(loss.mean())) if len(win) and len(loss) and loss.mean() != 0 else np.nan,
                    "hold": float(np.mean(holds)) if holds else np.nan, "turn": buyamt / yrs, "cash": cash, "holds": holds if J.get("keep_hold") else None,
                    "years": yrs})
    return res


def label(c, m, b):
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def run_jobs(jobs, procs, log, tag):
    t0 = time.time(); out = []
    with Pool(procs) as pool:
        for x in pool.imap_unordered(run_one, jobs, chunksize=2):
            out.append(x)
    log(f"  [{tag}] {len(jobs):,} 次｜{time.time() - t0:.0f}s")
    return out


# ═════════════ 單筆層（描述）═════════════
def single_layer(Wd, seg_all):
    cal = Wd["cal"]; n = Wd["n"]; sids = sorted(Wd["F"]); ix = {s: i for i, s in enumerate(sids)}
    C = np.column_stack([np.asarray(Wd["cz"][s], float) for s in sids]); O = np.column_stack([np.asarray(Wd["oz"][s], float) for s in sids])
    V = np.column_stack([np.isfinite(np.asarray(Wd["oz"][s], float)) & (np.asarray(Wd["oz"][s], float) > 0) for s in sids])
    mon = Wd["mon"]
    EL = np.zeros((n, len(sids)), bool)
    for s in sids:
        em = Wd["elig"].get(s, set()); j = ix[s]
        EL[:, j] = np.array([m in em for m in mon]) & Wd["F"][s]["PIT"]
    with np.errstate(invalid="ignore", divide="ignore"):
        r20 = np.full_like(C, np.nan); r20[20:] = C[20:] / C[:-20] - 1.0
    rows = []
    for H in (5, 10, 20, 60):
        Rh = np.full_like(C, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            Rh[:n - H] = np.where(V[1:n - H + 1], C[H:n] / O[1:n - H + 1] - 1.0, np.nan)
        base = np.full_like(C, np.nan)
        for t in range(n - H):
            m = EL[t] & np.isfinite(r20[t]) & np.isfinite(Rh[t])
            if m.sum() < 20:
                continue
            x = r20[t, m]; rk = pd.Series(x).rank(method="first").to_numpy(); mm = len(x)
            dec = ((10 * (rk - 1))[:, None] > (np.arange(1, 10) * (mm - 1))[None, :]).sum(axis=1)      # researchPatAll decile_int 同式
            rr = Rh[t, m]; mu = np.array([rr[dec == q].mean() for q in range(10)])
            bt = np.full(len(sids), np.nan); bt[np.flatnonzero(m)] = mu[dec]
            base[t] = bt
        for B in BS:
            for k in KS:
                for seg, (s0, s1) in seg_all.items():
                    ev = []
                    for s, f in Wd["F"].items():
                        j = ix[s]
                        for t in f["E"][(B, k)]:
                            t = int(t)
                            if s0 <= t + 1 <= s1 and t + H <= s1 and EL[t, j] and np.isfinite(Rh[t, j]) and np.isfinite(base[t, j]):
                                ev.append((t, Rh[t, j], Rh[t, j] - base[t, j]))
                    if not ev:
                        continue
                    E = pd.DataFrame(ev, columns=["t", "R", "X"]); E["m"] = mon[E["t"].to_numpy()]
                    g = E.groupby("m")["X"].mean(); k_ = len(g)
                    mx = float(E["X"].mean()); se = float(np.std(g.to_numpy(), ddof=1) / math.sqrt(k_)) if k_ > 1 else np.nan
                    rows.append({"段": seg, "B": B, "k": k, "H": H, "n": len(E), "月數": k_, "R−成本 平均": float(E["R"].mean() - COST), "X 平均": mx,
                                 "lo": mx - 1.96 * se, "hi": mx + 1.96 * se, "X>0 比例": float((E["X"] > 0).mean())})
    return pd.DataFrame(rows)


# ═════════════ 主程式 ═════════════
def body(a):
    global OUT, NSEED, NFIX, NRAND, NREAL
    if os.environ.get("VB_SMOKE"):
        OUT = os.path.expanduser("~/ugwork/vb_smoke"); NSEED, NFIX, NRAND, NREAL = 2, 1, 2, 1
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchVolBreak body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TAGT} =====")
    set_v2(True)
    RR.use_snapshot()
    Wm = world("主快照", D.DATA, RS.PANEL, SEG, a.procs, log)
    We = world("早年版面（只上市）", RS.EARLY_DATA, RS.EARLY_PANEL, {"早年": EARLY}, a.procs, log, elig_v=True, twse_only=True)
    RR.use_snapshot()
    _G["W"] = {"M": Wm, "E": We}
    S = {"登錄": "PREREG爆量突破進跌破EMA出 seq2 sha 0c44c9e73bba2397；裁定 seq299 §三", "讀法寫死": TAGT, "GATE_V2": True,
         "種子": {"主格與S臂": NSEED, "固定持有": NFIX, "隨機出場（確認段）": NRAND, "現實版（確認段）": NREAL},
         "0050": {**{k: v for k, v in Wm["B50"].items()}, **We["B50"]}}
    JOB = {}; ROWINFO = {}; ROWS = {}
    cells = [(B, k, L) for B in BS for k in KS for L in LS]; scells = [(B, None, L) for B in BS for L in LS]
    for wk, Wd in (("M", Wm), ("E", We)):
        for seg in Wd["segs"]:
            for (B, k, L) in cells + scells:
                R, same, warm, outu = rows_of(Wd, B, k, L, seg)
                key = (wk, seg, B, k, L)
                ROWS[key] = R; ROWINFO[key] = {"列": int(len(R)), "同日收在EMA下不進": same, "暖機擋": warm, "母體擋": outu, "段尾未出場列": int((R["dX"] < 0).sum())}
                sig, kw = cell_sig(Wd, R, seg)
                JOB[("ema",) + key] = {"w": wk, "seg": seg, "sig": sig, "kw": kw, "stats": True, "keep_hold": (seg == "確認")}
                if k is not None and seg in ("探索", "確認"):
                    for H in (20, 60, 120):
                        JOB[(f"H{H}",) + key] = {"w": wk, "seg": seg, "lazy": "fix", "rk": key, "H": H}
    log(f"[列] 建好 {len(ROWS)} 組｜{time.time() - T0:.0f}s")
    _G["JOB"] = JOB; _G["ROWS"] = ROWS
    jobs = [(jk, r, 1000 + r) for jk in JOB if jk[0] == "ema" for r in range(NSEED)]
    res = run_jobs(jobs, a.procs, log, "主格＋S 臂")
    jobs = [(jk, r, 1000 + r) for jk in JOB if jk[0].startswith("H") for r in range(NFIX)]
    res += run_jobs(jobs, a.procs, log, "固定持有對照")
    SD = pd.DataFrame([{k: v for k, v in x.items() if k != "holds"} for x in res])
    SD["job"] = SD["job"].map(lambda j: "|".join(str(z) for z in j))
    SD.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    byj = {}
    for x in res:
        byj.setdefault(x["job"], []).append(x)
    # ── 彙總
    rows = []
    for jk, L_ in byj.items():
        mode, wk, seg, B, k, L = jk
        Wd = _G["W"][wk]
        cg = np.array([x["cagr"] for x in L_]); mg = np.array([x["mdd"] for x in L_])
        c_, m_ = float(np.median(cg)), float(np.median(mg))
        row = {"出場": mode, "段": seg, "B": B, "k": ("—" if k is None else k), "L": L, "臂": "S（不看量）" if k is None else "M", "顆": len(L_),
               "年化中位": c_, "回落中位": m_, "比值": c_ / abs(m_) if m_ else np.nan, "標籤": label(c_, m_, Wd["B50"][seg]),
               "0050年化": Wd["B50"][seg]["cagr"], "0050回落": Wd["B50"][seg]["mdd"]}
        if mode == "ema":
            for kk in ("trades", "win", "payoff", "hold", "turn", "cash"):
                row[kk] = float(np.nanmean([x[kk] for x in L_]))
            row.update(ROWINFO[(wk, seg, B, k, L)])
            row["退化標記"] = "依構造近似天天換手" if (seg == "探索" and row["hold"] < 2) else ""
        rows.append(row)
    C = pd.DataFrame(rows)
    # ── 隨機出場（確認段 M 格）
    FP = []; POOL = {}
    for ci, (B, k, L) in enumerate(cells):
        rk = ("M", "確認", B, k, L)
        hl = [np.array(x["holds"], int) for x in byj[("ema",) + rk] if x["holds"]]
        POOL[rk] = np.concatenate(hl) if hl else np.zeros(0, int)
        for i in range(NRAND):
            JOB[("rand", "M", "確認", B, k, L, i)] = {"w": "M", "seg": "確認", "lazy": "rand", "rk": rk, "ci": ci, "i": i}
    _G["JOB"] = JOB; _G["POOL"] = POOL
    jobs = [(jk, jk[-1], 1000 + jk[-1] % NSEED) for jk in JOB if jk[0] == "rand"]
    rr = run_jobs(jobs, a.procs, log, "隨機出場（確認段）")
    for jk in [j for j in list(JOB) if j[0] == "rand"]:
        del JOB[jk]
    RD = {}
    for x in rr:
        RD.setdefault(x["job"][3:6], []).append(x["cagr"])
    for (B, k, L) in cells:
        m = C[(C["出場"] == "ema") & (C["段"] == "確認") & (C["B"] == B) & (C["k"] == k) & (C["L"] == L)]["年化中位"].iloc[0]
        x = np.array(RD[(B, k, L)])
        FP.append({"B": B, "k": k, "L": L, "本格年化中位": m, "隨機年化中位": float(np.median(x)), "p（隨機 ≥ 本格）": float((x >= m).mean()), "次數": len(x)})
    FPd = pd.DataFrame(FP); FPd.to_csv(os.path.join(OUT, "fake_p.csv"), index=False)
    # ── 現實版（確認段 M 格，researchSlip C1＋C2＋C4）
    from backtest import researchSlip as SL
    need = sorted({s for (B, k, L) in cells for s in ROWS[("M", "確認", B, k, L)]["sid"]})
    X = {s: SL.stock_extra(s, Wm["mk"].get(s, "twse"), Wm["cal"], Wm["n"]) for s in need}
    ops = {s: (X[s]["avg"] if X.get(s) is not None else Wm["oz"][s]) for s in Wm["oz"]}
    for (B, k, L) in cells:
        R = ROWS[("M", "確認", B, k, L)]
        sig, kw = cell_sig(Wm, R, "確認", opens=ops)
        e_ = sig["entry_pos"].to_numpy(int); s1c = Wm["segs"]["確認"][1]
        Qc = 500_000 / 10
        ie = np.nan_to_num(np.array([X[s]["sig20"][ee] * math.sqrt(Qc / X[s]["adv20"][ee]) if (X.get(s) is not None and np.isfinite(X[s]["adv20"][ee]) and X[s]["adv20"][ee] > 0) else 0.0
                                     for s, ee in zip(sig["sid"], e_)]))
        sig["g_X"] = (1 + sig["g_X"].to_numpy()) / (1 + ie) - 1.0          # ★ 出場衝擊：stop_line 出場價由引擎決定 ⇒ 只在進場加衝擊（執行者補，照實寫）
        JOB[("real", "M", "確認", B, k, L)] = {"w": "M", "seg": "確認", "sig": sig, "kw": kw, "cost": COST + 2 * 0.003, "opens": ops}
    _G["JOB"] = JOB
    jobs = [(jk, r, 1000 + r) for jk in JOB if jk[0] == "real" for r in range(NREAL)]
    rl = run_jobs(jobs, a.procs, log, "現實版（確認段）")
    RL = {}
    for x in rl:
        RL.setdefault(x["job"][3:6], []).append((x["cagr"], x["mdd"]))
    real = []
    for (B, k, L), v in RL.items():
        c_, m_ = float(np.median([z[0] for z in v])), float(np.median([z[1] for z in v]))
        real.append({"B": B, "k": k, "L": L, "現實版年化中位": c_, "現實版回落中位": m_, "標籤": label(c_, m_, Wm["B50"]["確認"])})
    REAL = pd.DataFrame(real)
    # ── 整套判定
    M_ = C[(C["出場"] == "ema") & (C["臂"] == "M")]
    cnt = {seg: {lab: int((M_[M_["段"] == seg]["標籤"] == lab).sum()) for lab in ("合格", "另列", "不合格")} for seg in ("探索", "確認", "早年")}
    q = lambda seg: cnt[seg]["合格"]; qo = lambda seg: cnt[seg]["合格"] + cnt[seg]["另列"]
    if q("確認") >= 31 and q("探索") >= 31:
        verdict = "合格"
    elif qo("確認") >= 31 and qo("探索") >= 31:
        verdict = "另列"
    else:
        verdict = "不合格"
    if verdict in ("合格", "另列") and q("早年") < 31:
        verdict_full = f"{verdict}（早年段只有 {q('早年')} 格合格 ⇒ 最多暫定）"
    else:
        verdict_full = verdict
    S["各段標籤格數（M 臂 60 格）"] = cnt; S["整套判定"] = verdict_full
    # ── 描述：分組、M−S、EMA vs 固定
    grp = {}
    for seg in ("探索", "確認", "早年"):
        x = M_[M_["段"] == seg]
        grp[seg] = {f"{p}={v}": int(((x[p] == v) & (x["標籤"] == "合格")).sum()) for p, vals in (("B", BS), ("k", KS), ("L", LS)) for v in vals}
    S["分組合格格數（描述）"] = grp
    ms = []
    for seg in ("探索", "確認", "早年"):
        for B in BS:
            for L in LS:
                sv = C[(C["出場"] == "ema") & (C["段"] == seg) & (C["臂"] != "M") & (C["B"] == B) & (C["L"] == L)]["年化中位"].iloc[0]
                for k in KS:
                    mv = M_[(M_["段"] == seg) & (M_["B"] == B) & (M_["k"] == k) & (M_["L"] == L)]["年化中位"].iloc[0]
                    ms.append({"段": seg, "B": B, "k": k, "L": L, "M年化": mv, "S年化": sv, "M−S（點）": (mv - sv) * 100})
    MS = pd.DataFrame(ms)
    S["M−S（描述）"] = {seg: {"M−S＞0 的格數／60": int((MS[MS["段"] == seg]["M−S（點）"] > 0).sum()), "中位（點）": float(MS[MS["段"] == seg]["M−S（點）"].median())}
                       for seg in ("探索", "確認", "早年")}
    fx = []
    for seg in ("探索", "確認"):
        for (B, k, L) in cells:
            ev = M_[(M_["段"] == seg) & (M_["B"] == B) & (M_["k"] == k) & (M_["L"] == L)]["年化中位"].iloc[0]
            d = {"段": seg, "B": B, "k": k, "L": L}
            for H in (20, 60, 120):
                hv = C[(C["出場"] == f"H{H}") & (C["段"] == seg) & (C["B"] == B) & (C["k"] == k) & (C["L"] == L)]["年化中位"].iloc[0]
                d[f"EMA−H{H}（點）"] = (ev - hv) * 100
            fx.append(d)
    FX = pd.DataFrame(fx)
    S["EMA 出場 − 固定抱（描述）"] = {seg: {f"H{H}": {"EMA 較好格數／60": int((FX[FX["段"] == seg][f"EMA−H{H}（點）"] > 0).sum()),
                                                  "中位（點）": float(FX[FX["段"] == seg][f"EMA−H{H}（點）"].median())} for H in (20, 60, 120)} for seg in ("探索", "確認")}
    S["隨機出場（確認段）"] = {"p＜0.05 的格數／60": int((FPd["p（隨機 ≥ 本格）"] < 0.05).sum()), "p 中位": float(FPd["p（隨機 ≥ 本格）"].median())}
    S["現實版（確認段）"] = {"合格格數／60": int((REAL["標籤"] == "合格").sum()), "另列": int((REAL["標籤"] == "另列").sum())}
    S["早年方向"] = {"早年合格格數": q("早年"), "早年合格或另列": qo("早年")}
    S["退化標記格數（探索段）"] = int((M_[(M_["段"] == "探索")]["退化標記"] != "").sum())
    S["先驗（登錄 §六）"] = {"①整套合格：否": verdict.startswith("不") or verdict.startswith("另"),
                         "②爆量有加分（M−S＞0 過半、兩段同向）：否或測不出": not (S["M−S（描述）"]["探索"]["M−S＞0 的格數／60"] > 30 and S["M−S（描述）"]["確認"]["M−S＞0 的格數／60"] > 30),
                         "③EMA 比固定抱 60 天好（過半）：否": not (S["EMA 出場 − 固定抱（描述）"]["確認"]["H60"]["EMA 較好格數／60"] > 30),
                         "④隨機出場 p＜0.05 過半：否": S["隨機出場（確認段）"]["p＜0.05 的格數／60"] <= 30}
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")
    MS.to_csv(os.path.join(OUT, "m_minus_s.csv"), index=False, float_format="%.6g"); FX.to_csv(os.path.join(OUT, "ema_vs_fixed.csv"), index=False, float_format="%.6g")
    REAL.to_csv(os.path.join(OUT, "real.csv"), index=False, float_format="%.10g")
    # 每年訊號數（M 臂，主快照＋早年，(B,k)）
    yr = {}
    for wk, Wd in (("M", Wm), ("E", We)):
        for B in BS:
            for k in KS:
                ys = {}
                for s, f in Wd["F"].items():
                    for t in f["E"][(B, k)]:
                        y = int(Wd["cal"][int(t)].year); ys[y] = ys.get(y, 0) + 1
                yr[f"{wk}|B{B}|k{k}"] = dict(sorted(ys.items()))
    S["每年訊號數（全母體、未套母體閘）"] = yr
    # 單筆層
    log("[單筆層] 開始")
    SG = pd.concat([single_layer(Wm, Wm["segs"]), single_layer(We, We["segs"])], ignore_index=True)
    SG.to_csv(os.path.join(OUT, "single.csv"), index=False, float_format="%.6g")
    S["耗時s"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    set_v2(False)
    log(f"[完] 整套 {verdict_full}｜{json.dumps(cnt, ensure_ascii=False)}")


# ═════════════ 查核（⛔ 不呼叫 feats_one／rows_of／cell_sig／run_one）═════════════
def check(a):
    out = {"時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    set_v2(True)
    RR.use_snapshot()
    cal = D.load_calendar(); n = len(cal); calv = cal.values
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    UG = UGm()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    G = set(UG.gate3(stocks)["stock_id"]); mk = stocks.set_index("stock_id")["market"].to_dict()
    p = P4F.read_panel(RS.PANEL); p = p[p["eligible"].astype(bool) & p["stock_id"].isin(G)]
    elig = {s: set(str(x)[:7] for x in g["measure_date"]) for s, g in p.groupby("stock_id")}
    rng = np.random.default_rng(11)
    sids = sorted(elig); pick = [sids[i] for i in rng.choice(len(sids), size=40, replace=False)]
    # 自算列（逐日迴圈寫法）：B=20,k=2.0,L=20 與 B=5,k=1.5,L=60，確認段
    s0, s1 = int(cal.searchsorted(pd.Timestamp(SEG["確認"][0]))), int(cal.searchsorted(pd.Timestamp(SEG["確認"][1])))
    mine = {}
    for (B, k, L) in ((20, 2.0, 20), (5, 1.5, 60)):
        rows = []
        for s in pick:
            st = D.load_stock(s, mk.get(s, "twse"), cal)
            raw = pd.read_csv(os.path.join(D.DATA, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "open", "close", "volume"]).drop_duplicates("date")
            raw["date"] = pd.to_datetime(raw["date"]); raw = raw.set_index("date").reindex(cal)
            ro = np.array(pd.to_numeric(raw["open"], errors="coerce"), dtype=float); rc = np.array(pd.to_numeric(raw["close"], errors="coerce"), dtype=float)
            rv = np.array(pd.to_numeric(raw["volume"], errors="coerce"), dtype=float)
            ro[~(ro > 0)] = np.nan; rc[~(rc > 0)] = np.nan
            c = st.df["close"].to_numpy(float); h = st.df["high"].to_numpy(float)
            bars = [i for i in range(n) if np.isfinite(c[i]) and np.isfinite(h[i])]
            ema = None; emas = {}
            al = 2.0 / (L + 1)
            for j, i in enumerate(bars):
                ema = c[i] if ema is None else al * c[i] + (1 - al) * ema
                emas[i] = ema
            pv = UG.pit_valid(s, cal)
            pos_in = None
            for j, i in enumerate(bars):
                if j < max(B, 20):
                    continue
                prevh = max(h[bars[j - q]] for q in range(1, B + 1)); va = sum(rv[bars[j - q]] for q in range(1, 21)) / 20.0
                cond = c[i] > prevh and np.isfinite(rc[i]) and np.isfinite(ro[i]) and rc[i] > ro[i] and va > 0 and rv[i] > k * va
                if not cond or not (s0 <= i + 1 <= s1) or str(cal[i])[:7] not in elig.get(s, set()) or not pv[i] or j < 3 * L or c[i] < emas[i]:
                    continue
                d = -1
                for jj in range(j + 1, len(bars)):
                    ii = bars[jj]
                    if ii > s1:
                        break
                    if c[ii] < emas[ii]:
                        d = ii; break
                rows.append((s, i, i + 1, d))
        mine[(B, k, L)] = rows
    # 主程式的列：重建同一格（只看抽到的 40 檔）⇒ 由 seeds 無法還原列 ⇒ 用主程式模組函式產列比對（列建構以外的獨立性：引擎權益另驗）
    import importlib
    M = importlib.import_module("backtest.researchVolBreak")
    Wf = M.world("主快照", D.DATA, RS.PANEL, SEG, a.procs, print)
    Wm = dict(Wf); Wm["F"] = {s: v for s, v in Wf["F"].items() if s in set(pick)}
    bad = {}
    for key, rows in mine.items():
        R, _, _, _ = M.rows_of(Wm, key[0], key[1], key[2], "確認")
        a_ = sorted(map(tuple, R[["sid", "t", "entry_pos", "dX"]].values.tolist())); b_ = sorted(rows)
        bad[str(key)] = {"主程式列": len(a_), "自算列": len(b_), "不同": len(set(a_) ^ set(b_))}
    out["① 進出場列（確認段、抽 40 檔、兩格）"] = bad
    # ② 引擎：B=20,k=2.0,L=20 確認段種子 1000：用 audit 自算權益
    B, k, L = 20, 2.0, 20
    R, _, _, _ = M.rows_of(Wf, B, k, L, "確認")
    sig, kw = M.cell_sig(Wf, R, "確認")
    au = []
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000), Wf["cz"], Wf["oz"], Wf["n"], return_equity=True, audit=au,
                         tradable=Wf["TRD"], delist=Wf["DL"], stop_force=Wf["SF"], **kw)
    eq = np.asarray(o["equity"], float)
    cash = 1.0; pos = {}; my = np.full(n, np.nan); ev = {}
    for x in au:
        ev.setdefault(int(x["t"]), []).append(x)
    badpx = 0
    for t in range(n):
        for x in ev.get(t, []):
            if x["side"] == "sell":
                pos.pop(x["sid"], None); cash += x["amt"] - x["cost"]
            else:
                pos[x["sid"]] = (x["amt"], x["px"]); cash -= x["amt"]
        my[t] = cash + sum(am * float(Wf["cz"][s][t]) / px for s, (am, px) in pos.items())
    lo, hi = int(o["first"]), int(min(o["end"], s1 + 1))
    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    SDs = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"))
    ref = SDs[(SDs["job"] == f"ema|M|確認|{B}|{k}|{L}") & (SDs["r"] == 0)]
    out["② 引擎權益自算（B20 k2.0 L20 確認段 種子 1000）"] = {"成交筆數": len(au), "自算權益最大差": float(np.nanmax(np.abs(my[lo:hi] - eq[lo:hi]))),
                                                       "與 seeds.csv 年化差": float(abs(c_ - ref["cagr"].iloc[0])) if len(ref) else None}
    # ③ 整套判定由 cells.csv 重數
    M_ = C[(C["出場"] == "ema") & (C["臂"] == "M")]
    cnt = {seg: int((M_[M_["段"] == seg]["標籤"] == "合格").sum()) for seg in ("探索", "確認", "早年")}
    out["③ 合格格數重數＝summary"] = cnt == {k_: v["合格"] for k_, v in S["各段標籤格數（M 臂 60 格）"].items()}
    ok = all(v["不同"] == 0 for v in bad.values()) and out["② 引擎權益自算（B20 k2.0 L20 確認段 種子 1000）"]["自算權益最大差"] < 1e-6 and \
        (out["② 引擎權益自算（B20 k2.0 L20 確認段 種子 1000）"]["與 seeds.csv 年化差"] or 0) < 1e-12 and out["③ 合格格數重數＝summary"]
    out["結論"] = "✅ 全過（0 不同）" if ok else "⛔ 有不同"
    set_v2(False)
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        return check(a)
    if a.mode == "page":
        from backtest import researchVolBreak_page as P
        return P.main()
    body(a)


if __name__ == "__main__":
    main()

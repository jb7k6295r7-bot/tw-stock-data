# -*- coding: utf-8 -*-
"""USREG-A2-W1b（組合層）：W1(b)「季營收連續 8 個會計季新高 ∧ ¬ma_stack ∧ ma60_up」在 S&P 500＋400 重跑；主臂改「不再符合才換」。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA2_w1b [--procs 3] [--seeds 200]

判準：USREG-A2 seq1（sha 8be74b36592db3f4）§三 ＋ 裁定 seq316（合格＝只 S&P 400 與合併兩者都過）＋ 裁定 seq308 §四 第 2 點（條件出場新規）；
     正文 USREG-W1b（美股登錄 seq2 §五、seq3 §四、seq4 §二§三、seq5 §一～§三；讀法 Z1～Z10 ＝ backtest/researchUSW1b.py docstring）。
既有程式（只 import、⛔ 未改）：researchUSW1b（load_one、rev_flags、window_metrics、label、w1b_fixtures、_src_raw）、research11.simulate_mtm、tradability.delist_status。
資料：researchUSA2_data（聯集轉接層 D1～D7；us-stock-data 881c86a9）；季營收 ＝ fundamentals/quarterly_revenue.csv（S&P 500）＋ quarterly_revenue_sp400.csv（S&P 400）。

⭐ A2 改動（登錄 §三）：
   主臂「不再符合才換」：持有中每個月量測日 d′（> 訊號量測日 d）檢查「最近一個已公布季營收仍為近 8 季最高（Z5 同一套：8 個會計季、相鄰 ≤ 140 天、value ≤ 0 當缺、
      容差 1e-4）∧ ma60_up ∧ ¬ma_stack」；任一不成立 ⇒ 次一交易日（d′＋1）開盤賣出；⛔ 不設最長天數；窗尾仍持有 ⇒ 2026-09-30 收盤結算、件數必報。
   空出名額照原規則（下一個量測日候選池抽籤）補。描述對照（⛔ 不判）：固定持有 20／60／120／240 交易日各一臂。
   預設照 seq242：8 槽、等權、種子 102000＋r（200 顆）、T＋1 開盤、成本 0.05%（敏感度 0.02／0.10%）、無停損停利。
   判準：對 ^SP500TR 同窗（2016-01-04～2026-09-30）：條件一 年化中位 ＞ 基準年化；條件二 年化中位 ÷ |回落中位| ≥ 基準比值 ⇒ 合格／另列／不合格；母體等權並列（描述）。

⭐ 執行者補讀法（登錄沒寫清楚 ⇒ 先寫死，台北 2026-10-07）：
 W1 三個母體各自一組組合回測：候選 ＝ 量測日 d 當天 在該母體（合併 ＝ m500 ∨ m400；只 S&P 400 ＝ m400；只 S&P 500 ＝ m500）∧ 有效 K 棒 ∧ bars ≥ 120 ∧ 營收 ∧ 技術。
    持有中移出母體 ⇒ 照抱（seq214 R4 E0），出場只看條件（主臂）或天數（固定臂）。
 W2 季營收序列：候選當天在 S&P 500 ⇒ 讀 quarterly_revenue.csv 該代號；在 S&P 400 ⇒ 讀 quarterly_revenue_sp400.csv 該代號，
    代號重用分段（cik_map_sp400 的 seg_from／seg_to：AZPN COHR CR CZR HR RBC RCM VAL）依 d 挑段、該段只用該段 CIK（＋前身表對到該 CIK 的列）；
    同段同 period_end 重複 ⇒ 取 first_filed 最早的一列（計數）。持有中的條件檢查一律用【進場那筆訊號】的序列（同一家公司）。
 W3 條件檢查的量測日 d′ ＝ d 之後的每個月第一個交易日，且 d′＋1 ≤ 窗尾；ma_stack／ma60_up 用 d′ 的值（Z3 同式：收盤日曆 ffill）；值缺 ⇒ 視為不成立。
    賣出日 d′＋1 沒有有效 K 棒 ⇒ 引擎照停牌延到第一個可成交開盤（tradable＋delist 同原件）；下市 ⇒ 最後成交價了結（原件 Z8）。
 W4 固定臂 xpos ＝ entry＋H−1（收盤出，原件 Z6 同式）；超過窗尾 ⇒ 窗尾收盤結算（與主臂同規則；原件「xpos ≥ 日曆長度即剔除」在本批改成窗尾結算，偏離另報）。
 W5 Z7 斷點：特徵回看窗或【該臂】持有期 [entry, 出場日] 跨轉接層斷點 ⇒ 剔除（原件定案②）；保留版（keep_pb）只在合併跑描述。
 W6 |ret|＞50% 敏感度（裁定 seq316）：S&P 400 未確認 23 列當斷點，回看窗或持有期碰到 ⇒ 剔除（臂名 ret50；合併、只 S&P 400）。
 W7 A2 標籤：合格 ＝ 合併與只 S&P 400 都「合格」；合併合格、只 400 不是 ⇒「事後擴母體」；合併另列 ⇒ 只 400 至少另列時標「另列」，否則「事後擴母體（另列）」；
    合併不合格 ⇒ 不合格。只 S&P 500 照舊描述。
 W8 持有天數 ＝ 賣出成交日 − 買進成交日（交易日數；引擎成交紀錄逐筆配對）；窗尾仍持有 ＝ 窗尾收盤結算的部位數；四種固定天數的配對差 ＝ 同一顆種子 年化（主臂 − 固定臂）。
 W9 母體等權（描述）：每天在該母體、前一天也有收盤的股票，日報酬等權平均（硬斷點那天不收）；同窗年化與回落。

⛔⛔ 授權：權益、逐月面板、訊號表、成交紀錄只放 ~/us_work/a2/（repo 外）並列 sha；resultsUSA2/ 只有彙總。
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSW1b as W          # ⚠ 這支在 import 時會改 us_data 的資料根目錄 ⇒ 必須先 import、再 install()
from backtest import researchUSA2_data as A2
A2.install()
from backtest import us_data as U
from backtest import research11 as R
from backtest import tradability as TRD

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA2")
WORK = os.path.expanduser("~/us_work/a2")
COST = U.COST_ROUNDTRIP
COST_SENS = U.COST_SENSITIVITY
N_SLOTS, SEED0, NSEED = 8, 102000, 200
MIN_BARS = 120
FIXH = (20, 60, 120, 240)
RULE = "A2"
POPS = ("合併", "只S&P400", "只S&P500")
REG = {"A2": "8be74b36592db3f4", "裁定": "seq316、seq308 §四", "正文": "USREG-W1b seq2～seq5（讀法 Z1～Z10）"}
_G = {}


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ═════════════ 季營收序列（W2）═════════════
def _p(*a):
    return os.path.join(A2.ROOT, "data", *a)


def load_rev(cal):
    cols = ["ticker", "cik", "period_start", "period_end", "value", "first_filed", "first_form", "tag", "derived"]
    q5 = pd.read_csv(_p("fundamentals", "quarterly_revenue.csv"), usecols=cols, dtype={"ticker": str, "cik": str})
    q4 = pd.read_csv(_p("fundamentals", "quarterly_revenue_sp400.csv"), usecols=cols, dtype={"ticker": str, "cik": str})
    cm4 = pd.read_csv(_p("fundamentals", "cik_map_sp400.csv"), dtype=str, keep_default_na=False)
    pr4 = pd.read_csv(_p("fundamentals", "cik_predecessor_sp400.csv"), dtype=str, keep_default_na=False)
    pred = {}
    for r in pr4.itertuples():
        if r.verdict == "ok":
            pred.setdefault(r.cik_now, set()).add(r.pred_cik)
    for q in (q5, q4):
        for c in ("period_end", "first_filed"):
            q[c] = pd.to_datetime(q[c])
        i = cal.searchsorted(q["first_filed"].values, side="right")
        q["avail_date"] = pd.DatetimeIndex([cal[k] if k < len(cal) else pd.NaT for k in i])
        q["cal_q"] = q["period_end"].dt.to_period("Q").astype(str)
    series, segs, cnt = {}, {}, {"S&P400_分段代號": 0, "分段外而丟掉的列": 0, "同段同期重複而丟掉的列": 0}
    for t, g in q5.groupby("ticker"):
        series[("sp500", t, 0)] = g
    seg_t = cm4[(cm4["seg_from"] != "") | (cm4["seg_to"] != "")]
    multi = set(seg_t["ticker"])
    cnt["S&P400_分段代號"] = sorted(multi)
    for t, g in q4.groupby("ticker"):
        if t in multi:
            rows = cm4[cm4["ticker"] == t].reset_index(drop=True)
            segs[t] = []
            used = np.zeros(len(g), bool)
            for k, r in rows.iterrows():
                ciks = {r["cik"]} | pred.get(r["cik"], set())
                m = g["cik"].isin(ciks).to_numpy()
                series[("sp400", t, k)] = g[m]; used |= m
                segs[t].append((k, pd.Timestamp(r["seg_from"]) if r["seg_from"] else None, pd.Timestamp(r["seg_to"]) if r["seg_to"] else None))
            cnt["分段外而丟掉的列"] += int((~used).sum())
        else:
            series[("sp400", t, 0)] = g
    for k in list(series):
        g = series[k].sort_values(["period_end", "first_filed"])
        d = g.duplicated("period_end", keep="first")
        cnt["同段同期重複而丟掉的列"] += int(d.sum())
        series[k] = g[~d]
    return series, segs, cnt


def seg_at(segs, t, d):
    if t not in segs:
        return 0
    for k, a, b in segs[t]:
        if (a is None or d >= a) and (b is None or d < b):
            return k
    return None


# ═════════════ 每檔（worker）═════════════
def w_init(cal, w0, w1, meas):
    W._init(cal, w0, w1, meas); _G.update(cal=cal, w0=w0, w1=w1, meas=meas)


def w_work(t):
    r = W.load_one(t)
    if r is None:
        return None
    cal, meas = _G["cal"], _G["meas"]
    m5, m4 = A2.idx_member(t, cal)
    r["M"]["m5"] = m5[meas]; r["M"]["m4"] = m4[meas]
    r["f50"] = A2.flag50_pos(t, cal)
    r["mem_full"] = (m5 | m4)
    r["m4_full"] = m4; r["m5_full"] = m5
    return r


# ═════════════ 引擎 ═════════════
_S = {}


def _run(args):
    seed, key = args
    s = _S["arms"][key]
    R.COST = s["cost"]
    aud = [] if s["audit"] else None
    try:
        out = R.simulate_mtm(s["sig"], RULE, N_SLOTS, np.random.default_rng(seed), s["closes"], s["opens"], _S["ncal"],
                             return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero",
                             tradable=_S["trad"], delist=_S["dl"], audit=aud)
    finally:
        R.COST = U.COST_ROUNDTRIP
    eq = out["equity"]; w0, w1 = _S["w0"], _S["w1"]
    c, m = W.window_metrics(eq, w0, w1)
    r = {"pop": s["pop"], "arm": s["arm"], "seed": seed, "cagr": c, "mdd": m, "trades": out["trades"], "slot_use": out["slot_use"],
         "delist_settled": out.get("tr_delist_settled"), "delist_ambig": out.get("tr_delist_ambig"), "halt_in": out.get("tr_halt_in"),
         "exit_delayed": out.get("tr_exit_delayed"), "open_at_end": out.get("tr_open_at_end")}
    if aud is not None:
        endh = s["endhold"]; buy = {}; hold = []; nend = 0
        for a in aud:
            if a["side"] == "buy":
                buy[a["sid"]] = a["t"]
            elif a["side"] == "sell" and a["sid"] in buy:
                b = buy.pop(a["sid"]); hold.append(a["t"] - b)
                if a["t"] == w1 and endh.get((a["sid"], b), False):
                    nend += 1
        hold = np.array(hold, float)
        r.update({"hold_mean": float(hold.mean()) if len(hold) else np.nan, "hold_med": float(np.median(hold)) if len(hold) else np.nan,
                  "hold_max": float(hold.max()) if len(hold) else np.nan, "n_sells": int(len(hold)), "n_end_hold": nend,
                  "still_open_after_loop": len(buy)})
    if seed == SEED0 and s["pop"] == "合併" and s["arm"] == "main":
        r["equity"] = eq.astype(float); r["audit"] = aud
    return r


def main():
    t0 = time.time()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 3
    nseed = int(sys.argv[sys.argv.index("--seeds") + 1]) if "--seeds" in sys.argv else NSEED
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    fx = {"A2資料轉接": A2.selftest(), "W1b_FW1_FW3": W.w1b_fixtures()}
    calF = U.load_calendar(); cal = calF[calF >= W.MB.CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(A2.WINDOW[0])); w1 = int(cal.searchsorted(A2.WINDOW[1]))
    assert cal[w0] == A2.WINDOW[0] and cal[w1] == A2.WINDOW[1]
    per = cal.to_period("M")
    meas = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    meas = meas[meas + 1 <= w1]
    nos = set(A2.no_ohlc_tickers())
    tick = [t for t in A2.tickers_all() if t not in nos]
    if lim:
        tick = tick[:lim]
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    print("[W1b] 資料 {}｜窗 {}～{}｜量測日 {}（{}～{}）｜{} 檔".format(A2.data_commit()[:10], cal[w0].date(), cal[w1].date(), len(meas),
          cal[meas[0]].date(), cal[meas[-1]].date(), len(tick)), flush=True)
    with Pool(procs, initializer=w_init, initargs=(cal, w0, w1, meas)) as pool:
        res = pool.map(w_work, tick, chunksize=4)
    ST = {r["t"]: r for r in res if r is not None}
    sids = sorted(ST)
    print("[W1b] 讀檔 {} 檔｜{:.0f}s".format(len(sids), time.time() - t0), flush=True)
    series, segs, rcnt = load_rev(cal)
    FL = {}                                                   # 序列 ⇒ 每個量測日的旗標（W.rev_flags 原式）
    for k, q in series.items():
        if k[1] in ST and len(q):
            FL[k] = W.rev_flags(q, cal, meas).set_index("d")
    # ── 逐月面板
    parts = []
    for t in sids:
        Mx = ST[t]["M"].copy()
        keys = []
        for d, a5, a4 in zip(Mx["d"], Mx["m5"], Mx["m4"]):
            if a5:
                keys.append(("sp500", t, 0))
            elif a4:
                sg = seg_at(segs, t, cal[d]); keys.append(("sp400", t, sg) if sg is not None else None)
            else:
                keys.append(None)
        Mx["skey"] = keys
        ok, ex, why, cq = [], [], [], []
        for d, k in zip(Mx["d"], keys):
            if k is None or k not in FL:
                ok.append(False); ex.append(False); why.append("不適用（無營收序列）"); cq.append(False)
            else:
                f = FL[k].loc[d]; ok.append(bool(f["rev_ok"])); ex.append(bool(f["rev_exact"])); why.append(f["why"]); cq.append(bool(f["cal_ok"]))
        Mx["rev_ok"] = ok; Mx["rev_exact"] = ex; Mx["why"] = why; Mx["cal_ok"] = cq
        parts.append(Mx)
    P = pd.concat(parts, ignore_index=True)
    P["base"] = P["member"] & (P["bars"] >= MIN_BARS)
    P["tech"] = (P["ma_stack"] == 0) & (P["ma60_up"] == 100)
    P["sig"] = P["base"] & P["rev_ok"] & P["tech"]
    P["sig_exact"] = P["base"] & P["rev_exact"] & P["tech"]
    P["sig_cal"] = P["base"] & P["cal_ok"] & P["rev_ok"] & P["tech"]
    print("[W1b] 面板 {:,} 股月｜訊號 {:,}｜{:.0f}s".format(len(P), int(P["sig"].sum()), time.time() - t0), flush=True)
    # ── 每檔每量測日的「持有條件」（W3：用指定序列）
    midx = {d: i for i, d in enumerate(meas)}
    techA = {t: ((ST[t]["M"]["ma_stack"].to_numpy() == 0) & (ST[t]["M"]["ma60_up"].to_numpy() == 100)) for t in sids}
    revA = {}

    def rev_arr(k):
        if k not in revA:
            revA[k] = FL[k]["rev_ok"].reindex(meas).fillna(False).to_numpy(bool) if k in FL else np.zeros(len(meas), bool)
        return revA[k]
    # ── 訊號表：每臂各自的出場
    rows = []; drop = {"開盤不可用": 0, "收盤不可用": 0}
    F50C = {t: np.cumsum(ST[t]["f50"]) for t in sids}
    for r in P[P["sig"] | P["sig_exact"]].itertuples():
        t = r.t; S = ST[t]; d = int(r.d); e = d + 1
        o = S["opens"][e]
        if not (np.isfinite(o) and o > 0):
            drop["開盤不可用"] += 1; continue
        cs = S["cs_pb"]
        vb = np.flatnonzero(S["valid"]); kk = np.searchsorted(vb, d, side="right"); lo = int(vb[max(kk - 120, 0)]) if kk >= 120 else 0
        f50c = F50C[t]
        row = {"sid": t, "entry_pos": e, "measure": d, "month": cal[d].strftime("%Y-%m"), "tol": bool(r.sig), "exact": bool(r.sig_exact),
               "pb_feat": bool(r.pb_feat), "f50_feat": bool(f50c[d] - (f50c[lo - 1] if lo > 0 else 0) > 0),
               "m4": bool(r.m4), "m5": bool(r.m5), "skey": "|".join(map(str, r.skey)) if r.skey else ""}
        # 主臂：條件換股
        ta, ra = techA[t], rev_arr(r.skey)
        j0 = midx[d] + 1; x = None
        for j in range(j0, len(meas)):
            if not (ta[j] and ra[j]):
                x = int(meas[j]) + 1; break
        if x is None:
            x = w1; g = S["closes"][w1] / o - 1.0; endh = True
        else:
            ox = S["opens"][x]; g = (ox if (np.isfinite(ox) and ox > 0) else S["closes"][x]) / o - 1.0; endh = False
        row.update({"xpos_main": x, "g_main": g, "endhold_main": endh})
        for H in FIXH:
            xh = min(e + H - 1, w1)
            row[f"xpos_fix{H}"] = xh; row[f"g_fix{H}"] = S["closes"][xh] / o - 1.0; row[f"endhold_fix{H}"] = bool(e + H - 1 > w1)
        for a in ["main"] + [f"fix{H}" for H in FIXH]:
            xa = row[f"xpos_{a}"]
            row[f"pb_hold_{a}"] = bool(cs[xa] - cs[e - 1] > 0)
            row[f"f50_hold_{a}"] = bool(f50c[xa] - f50c[e - 1] > 0)
        if not all(np.isfinite(row[f"g_{a}"]) for a in ["main"] + [f"fix{H}" for H in FIXH]):
            drop["收盤不可用"] += 1; continue
        rows.append(row)
    SG = pd.DataFrame(rows).sort_values(["entry_pos", "sid"]).reset_index(drop=True)
    print("[W1b] 訊號表 {:,}（剔除 {}）｜{:.0f}s".format(len(SG), drop, time.time() - t0), flush=True)
    # ── 臂
    closes = {s: ST[s]["closes"] for s in sids}; opens = {s: ST[s]["opens"] for s in sids}
    closes_n = {s: ST[s]["closes_net"] for s in sids}; opens_n = {s: ST[s]["opens_net"] for s in sids}
    popm = {"合併": np.ones(len(SG), bool), "只S&P400": SG["m4"].to_numpy(), "只S&P500": SG["m5"].to_numpy()}

    def mk(pop, arm_exit, sel_extra=None, keep_pb=False, exact=False, f50=False, net=False):
        m = popm[pop] & (SG["exact"].to_numpy() if exact else SG["tol"].to_numpy())
        if not keep_pb:
            m &= ~(SG["pb_feat"].to_numpy() | SG[f"pb_hold_{arm_exit}"].to_numpy())
        if f50:
            m &= ~(SG["f50_feat"].to_numpy() | SG[f"f50_hold_{arm_exit}"].to_numpy())
        d = SG[m]
        out = pd.DataFrame({"sid": d["sid"].to_numpy(), "entry_pos": d["entry_pos"].to_numpy(), f"xpos_{RULE}": d[f"xpos_{arm_exit}"].to_numpy(),
                            f"g_{RULE}": d[f"g_{arm_exit}"].to_numpy(), "month": d["month"].to_numpy()})
        if net:
            gg = []
            for s, e, x, a in zip(d["sid"], d["entry_pos"], d[f"xpos_{arm_exit}"], d[f"endhold_{arm_exit}"]):
                if arm_exit == "main" and not a:
                    ox = opens_n[s][x]; v = ox if (np.isfinite(ox) and ox > 0) else closes_n[s][x]
                else:
                    v = closes_n[s][x]
                gg.append(v / opens_n[s][e] - 1.0)
            out[f"g_{RULE}"] = gg
        endh = {(s, int(e)): bool(a) for s, e, a in zip(d["sid"], d["entry_pos"], d[f"endhold_{arm_exit}"])}
        return out.reset_index(drop=True), endh
    ARMS = {}
    for pop in POPS:
        arms = [("main", "main", {}), *[(f"fix{H}", f"fix{H}", {}) for H in FIXH]]
        if pop != "只S&P500":
            arms += [("cost_0.02%", "main", {"cost": COST_SENS[0]}), ("cost_0.10%", "main", {"cost": COST_SENS[1]}), ("ret50", "main", {"f50": True})]
        if pop == "合併":
            arms += [("exact", "main", {"exact": True}), ("keep_pb", "main", {"keep_pb": True}), ("div_net30", "main", {"net": True})]
        for nm, ax, kw in arms:
            sig, endh = mk(pop, ax, keep_pb=kw.get("keep_pb", False), exact=kw.get("exact", False), f50=kw.get("f50", False), net=kw.get("net", False))
            ARMS[(pop, nm)] = {"pop": pop, "arm": nm, "sig": sig, "endhold": endh, "cost": kw.get("cost", COST),
                               "closes": closes_n if kw.get("net") else closes, "opens": opens_n if kw.get("net") else opens,
                               "audit": nm in ("main",) + tuple(f"fix{H}" for H in FIXH)}
    z = np.zeros(n, bool)
    trad = {s: {"trd": ST[s]["trd"], "up_o": z, "dn_o": z, "dn_c": z} for s in sids}
    dl = TRD.delist_status(trad, cal)
    _S.update(arms=ARMS, ncal=n, trad=trad, dl=dl, w0=w0, w1=w1)
    jobs = [(SEED0 + r, k) for k in ARMS for r in range(nseed)]
    print("[W1b] 引擎 {} 次（{} 臂 × {} 顆）…".format(len(jobs), len(ARMS), nseed), flush=True)
    with Pool(procs) as pool:
        out = pool.map(_run, jobs, chunksize=8)
    print("[W1b] 引擎完成｜{:.0f}s".format(time.time() - t0), flush=True)
    shas = []
    s0 = [r for r in out if "equity" in r][0]
    eq0 = s0.pop("equity"); aud0 = s0.pop("audit")
    p = os.path.join(WORK, "W1b_equity_seed102000_main_comb.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal], "equity": eq0}).to_csv(p, index=False); shas.append((os.path.basename(p), n, sha256f(p)))
    A_ = pd.DataFrame(aud0); A_["date"] = [str(cal[t].date()) for t in A_["t"]]
    p = os.path.join(WORK, "W1b_audit_seed102000_main_comb.csv"); A_.to_csv(p, index=False); shas.append((os.path.basename(p), len(A_), sha256f(p)))
    D = pd.DataFrame(out)
    p = os.path.join(WORK, "W1b_seeds.csv"); D.to_csv(p, index=False); shas.append((os.path.basename(p), len(D), sha256f(p)))
    p = os.path.join(WORK, "W1b_signals.csv.gz"); SG.to_csv(p, index=False); shas.append((os.path.basename(p), len(SG), sha256f(p)))
    p = os.path.join(WORK, "W1b_panel_monthly.csv.gz")
    P.assign(skey=P["skey"].map(lambda k: "|".join(map(str, k)) if k else "")).to_csv(p, index=False); shas.append((os.path.basename(p), len(P), sha256f(p)))
    # ── 基準
    bench = U.benchmark_tr("SP500TR").reindex(cal).ffill().to_numpy(float)
    spy = U.benchmark_tr("SPY").reindex(cal).ffill().to_numpy(float)
    gspc = pd.read_csv(A2._p("macro", "yahoo_GSPC.csv"), usecols=["date", "close"], dtype={"date": str})
    gspc = pd.Series(gspc["close"].to_numpy(float), pd.DatetimeIndex(pd.to_datetime(gspc["date"]))).reindex(cal).ffill().to_numpy()
    br = bench[1:] / bench[:-1]; gr = gspc[1:] / gspc[:-1]
    bench_net = np.r_[1.0, np.cumprod(gr + W.NET_DIV * (br - gr))] * bench[0]
    B = {}
    for nm, s_ in (("SP500TR", bench), ("SPY備援（描述）", spy), ("SP500TR_扣30%股息（描述）", bench_net)):
        c_, m_ = W.window_metrics(s_, w0, w1)
        B[nm] = {"年化": c_, "回落": m_, "比值": c_ / abs(m_)}
    # 母體等權（W9）
    Cm = np.column_stack([ST[s]["closes"] for s in sids]); V = np.column_stack([ST[s]["valid"] for s in sids])
    PB = np.column_stack([np.r_[False, np.diff(ST[s]["cs_pb"]) > 0] for s in sids])
    MM = {"合併": np.column_stack([ST[s]["mem_full"] for s in sids]), "只S&P400": np.column_stack([ST[s]["m4_full"] for s in sids]),
          "只S&P500": np.column_stack([ST[s]["m5_full"] for s in sids])}
    with np.errstate(invalid="ignore", divide="ignore"):
        rr = Cm[1:] / Cm[:-1] - 1.0
    okr = V[1:] & V[:-1] & ~PB[1:] & np.isfinite(rr)
    for pop in POPS:
        mk_ = okr & MM[pop][:-1]
        ew = np.where(mk_.sum(axis=1) > 0, np.where(mk_, rr, 0).sum(axis=1) / np.maximum(mk_.sum(axis=1), 1), 0.0)
        lvl = np.r_[1.0, np.cumprod(1 + ew)]
        c_, m_ = W.window_metrics(lvl, w0, w1)
        B[f"母體等權_{pop}（描述）"] = {"年化": c_, "回落": m_, "比值": c_ / abs(m_)}
    del Cm, V, PB
    RES = {"性質": "USREG-A2-W1b（組合層；主臂條件換股；判定 × 兩個母體；美股 N 組合 +1）", "登錄": REG, "資料commit": A2.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "ANN": W.ANN, "種子數": nseed, "可用檔數": len(sids), "fixture": fx,
           "基準": B, "季營收序列帳": rcnt, "訊號表筆數": int(len(SG)), "訊號表剔除": drop, "結果": {}}
    inb = P[P["base"]]
    RES["Z4_liq_amt20美元"] = {"最小": float(inb["amt20"].min()), "p0.1": float(inb["amt20"].quantile(0.001)), "台幣5000萬換算上限": 50e6 / 25,
                               "最小值高於換算上限": bool(inb["amt20"].min() > 50e6 / 25)}
    for pop in POPS:
        pm = {"合併": inb.index, "只S&P400": inb.index[inb["m4"]], "只S&P500": inb.index[inb["m5"]]}[pop]
        ib = inb.loc[pm]
        RES.setdefault("候選盤點", {})[pop] = {"在母體且bars_ok股月": int(len(ib)), "營收判定帳": {k: int(v) for k, v in ib["why"].value_counts().items()},
                                              "訊號股月": int(ib["sig"].sum()), "訊號_曆季逐字版（描述）": int(ib["sig_cal"].sum()),
                                              "營收不適用的股月": int(ib["why"].astype(str).str.startswith("不適用").sum())}
    for pop in POPS:
        g = D[D["pop"] == pop]; R_ = {}
        for arm, x in g.groupby("arm"):
            bref = B["SP500TR_扣30%股息（描述）"] if arm == "div_net30" else B["SP500TR"]
            cm, mm = float(x["cagr"].median()), float(x["mdd"].median())
            lab, ratio, rb = W.label(cm, mm, bref["年化"], bref["回落"])
            seedlab = [W.label(c_, m_, bref["年化"], bref["回落"])[0] for c_, m_ in zip(x["cagr"], x["mdd"])]
            a = {"年化中位": cm, "回落中位": mm, "比值": ratio, "基準比值": rb, "標籤": lab,
                 "年化p10": float(x["cagr"].quantile(0.1)), "年化p90": float(x["cagr"].quantile(0.9)),
                 "回落p10": float(x["mdd"].quantile(0.1)), "回落p90": float(x["mdd"].quantile(0.9)),
                 "逐種子標籤比例": {k: float(np.mean([y == k for y in seedlab])) for k in ("合格", "另列", "不合格")},
                 "交易數中位": float(x["trades"].median()), "槽位使用率中位": float(x["slot_use"].median()),
                 "下市了結中位": float(x["delist_settled"].median()), "出場延後中位": float(x["exit_delayed"].median()),
                 "訊號表筆數": int(len(ARMS[(pop, arm)]["sig"])), "描述或判定": "判定" if arm == "main" else "描述（⛔ 不判）"}
            if "hold_mean" in x and x["hold_mean"].notna().any():
                a.update({"持有天數_平均（逐種子平均的中位）": float(x["hold_mean"].median()), "持有天數_中位（逐種子中位的中位）": float(x["hold_med"].median()),
                          "最長持有（200 顆中最大）": float(x["hold_max"].max()), "最長持有（逐種子的中位）": float(x["hold_max"].median()),
                          "窗尾仍持有件數（逐種子中位）": float(x["n_end_hold"].median()), "窗尾仍持有件數（範圍）": [int(x["n_end_hold"].min()), int(x["n_end_hold"].max())]})
            R_[arm] = a
        mainx = g[g["arm"] == "main"].set_index("seed")
        pair = {}
        for H in FIXH:
            fx_ = g[g["arm"] == f"fix{H}"].set_index("seed")
            dd = (mainx["cagr"] - fx_["cagr"]).dropna(); dm = (mainx["mdd"] - fx_["mdd"]).dropna()
            pair[f"主臂−固定{H}日"] = {"年化差中位": float(dd.median()), "年化差p10": float(dd.quantile(0.1)), "年化差p90": float(dd.quantile(0.9)),
                                   "主臂年化較高的種子比例": float((dd > 0).mean()), "回落差中位": float(dm.median())}
        R_["配對差（同種子）"] = pair
        RES["結果"][pop] = R_
        print("[W1b {}] 主臂 年化中位 {:+.2%} 回落中位 {:+.2%} 比值 {:.3f} ⇒ {}（基準 {:+.2%}／{:+.2%}／{:.3f}）".format(pop, R_["main"]["年化中位"], R_["main"]["回落中位"],
              R_["main"]["比值"], R_["main"]["標籤"], B["SP500TR"]["年化"], B["SP500TR"]["回落"], B["SP500TR"]["比值"]), flush=True)
    order = {"合格": 2, "另列": 1, "不合格": 0}
    lc, l4 = RES["結果"]["合併"]["main"]["標籤"], RES["結果"]["只S&P400"]["main"]["標籤"]
    if lc == "合格" and l4 == "合格":
        fin = "合格（兩個母體都合格）"
    elif lc == "合格":
        fin = "事後擴母體（合併合格、只 S&P 400 {}；最多暫定、只進前瞻紀錄）".format(l4)
    elif lc == "另列":
        fin = "另列（合併與只 S&P 400 都至少另列）" if order[l4] >= 1 else "事後擴母體（合併另列、只 S&P 400 不合格）"
    else:
        fin = "不合格（合併不合格；只 S&P 400 {}）".format(l4)
    RES["A2標籤"] = fin
    RES["先驗_主臂仍不合格（只記錄）"] = bool(lc == "不合格")
    RES["先驗_平均持有天數短於120（只記錄）"] = bool(RES["結果"]["合併"]["main"].get("持有天數_平均（逐種子平均的中位）", 999) < 120)
    RES["覆蓋_存活者偏差"] = A2.coverage(cal, w0, w1)
    RES["倒閉銀行"] = {b: {"訊號數": int((SG["sid"] == b).sum())} for b in ("SIVB", "FRC", "SBNY")}
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    RES["耗時秒"] = round(time.time() - t0, 1)
    json.dump(RES, open(os.path.join(OUT, "W1b_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("[W1b] A2 標籤：{}｜完成 {:.0f}s".format(fin, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()

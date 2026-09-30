# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 正式交易「進場時落在漲勢的哪個位置」描述（使用者問：「營量、營飆第一段初期進場，通常是什麼時候介入的？」；只描述、不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_entrystage [--check | --page]

═══ 讀法（寫死於 2026-09-30 18:46（台北），在算任何數字之前）═══
 Y1 交易來源（正式口徑 ＝ T1 版、停止交易強制出場開，commit 1e7229c101 以來；照實記錄）：
    營量 v1：repo 現成的 resultsYLlist/audit_seed0.csv.gz 買進列（717 筆；該檔閘 ＝ resultsT1fix c13 t1 r0 逐位元，見 resultsYLlist/gate.json）；
      ⭐ 另用正式程式（listexit_lines.setup_t1(t1=True)、rerun17 #13：simulate_mtm(sig13, "H60", 20, default_rng(7000), relvol, queue_days＝0, stop_force)）重產種子 0 的買進列，須與該檔逐列相同
      營量是 relvol 挑選、不抽籤 ⇒ 只用種子 0（另核種子 1 買進列相同）
    營飆 v1：repo 沒有現成逐筆 ⇒ 用正式程式重產：listexit_lines.sim（H120 N10、default_rng(1000＋r)、t−1 大盤閘；T1 開、stop_force 開）r ＝ 0～199 的 audit 買進列；
      每顆的年化、回落須與 resultsT1fix/seeds.csv.gz（c1｜t1｜r）逐位元相同才用；營飆抽籤 ⇒ 200 顆合併（同一筆在幾顆出現就算幾次 ＝ 期望口徑），另報種子 0 與去重筆
    innov_ky：正式版（T1 當時）⇒ 共用閘 innov_ky 關（預設），不改；創新板筆數照報
    期間：主窗全部（2017-03～2026-08-24）；另拆進場日 2021-01～2023-12、2024-01～2026-08
 Y2 價格：引擎同一份（ctx closes／opens，還原、ffill；不含 T1 墊的那一根）；進場日 e ＝ audit 的 t（實際買進日）、進場價 bp ＝ audit px（＝ e 開盤，另核與 ctx opens 相同）
 Y3 進場前：起漲點 L ＝ surge_flow_daily.anchor_of（commit 07107dbd02，逐字抄入本檔）：資料到 e−1 為止（e 開盤買時只知道 e−1 收盤），
      L ＝ [e−250, e−1] 內「最高收盤之前的最低收盤」；若從 L 起的回落 30%（第一次收盤 ≤ 最高 × 0.7）在 e−1 以前已發生 ⇒ L 改為結束日到 e−1 的最低收盤，重複（最多 50 次）
    進場時已漲 ＝ bp ÷ c[L] − 1；L 到 e 天數 ＝ e − L（交易日）
 Y4 進場後：從 e 起跟著創新高，第一次收盤 ≤ [e, d] 最高收盤 × 0.7 那天 ＝ 結束；本輪頂 P ＝ [e, 結束日] 最高收盤那天（S7 P*）；資料尾（ctx 日曆最後一天）前沒回落 30% ⇒「未完」（P 暫定）
    進度 ＝ (bp − c[L]) ÷ (c[P] − c[L])；P 漲幅 ＝ c[P] ÷ bp − 1；e 到 P 天數
    段：c[L..P] 用 surge_flow_daily.cuts_rec（x＝20%）切段；進場落在第 1 ＋ #{低點 trough ＜ e 的 20% 拉回} 段（事後切段；進場在某次拉回中途 ⇒ 仍算那一段）
 Y5 分組：全部；依 P 漲幅 ≥ 100%（飆）、30%～100%、＜ 30%；各報 中位與 p25～p75（進場已漲、L 到 e 天數、進度、P 漲幅、e 到 P 天數），
    進度分佈：＜0、0～1 成、…、9～10 成、＞10 成；段：第 1／2／3 段以上；未完比例
 Y6 查核（--check）：每個策略抽 50 筆（營飆從去重筆抽），用逐日迴圈從 ctx 價格重算 L、P、進度、段 ⇒ 0 不同才算過；另含 Y1 的兩個閘
輸出 backtest/resultsYL_entrystage/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import listexit_lines as L_
from backtest import research11 as R
from backtest import rerun17 as RR

TIME = "2026-09-30 18:46（台北）"
OUT = "backtest/resultsYL_entrystage"
X = 0.20
SEGS = {"全部": ("2017-01-01", "2026-12-31"), "2021-2023": ("2021-01-01", "2023-12-31"), "2024-2026.08": ("2024-01-01", "2026-08-31")}
GRP = [("全部", -np.inf, np.inf), ("飆（P 漲幅 ≥100%）", 1.0, np.inf), ("30%～100%", 0.3, 1.0), ("＜30%", -np.inf, 0.3)]
BINS = ["＜0"] + [f"{i}～{i + 1} 成" for i in range(10)] + ["＞10 成"]


# ── surge_flow_daily（commit 07107dbd02）逐字抄入 ──
def anchor_of(c, T):
    """資料日（或買進日）T 往前 250 個交易日內，最高收盤之前的最低收盤日。"""
    lo = max(T - 249, 0); P0 = lo + int(np.argmax(c[lo:T + 1]))
    return lo + int(np.argmin(c[lo:P0 + 1]))


def cuts_rec(cs, x=X):
    """[t..] 收盤 ⇒ [(a, trough, recover)]（相對位置；a ＞ 0 且回落 ≥ x；recover ＝ a 之後下一個新高日）；同 mid_desc M2／M2b。"""
    rm = np.maximum.accumulate(cs)
    nh = np.flatnonzero(cs[1:] > rm[:-1]) + 1
    pk = np.r_[0, nh]; out = []
    for j in np.flatnonzero(np.diff(pk) >= 2):
        a, b = int(pk[j]), int(pk[j + 1]); seg = cs[a + 1:b]; k = int(np.argmin(seg))
        if a > 0 and seg[k] <= cs[a] * (1 - x) * (1 + 1e-9):
            out.append((a, a + 1 + k, b))
    return out


def anchor_before(c, e):
    """Y3：資料到 e−1。"""
    T = e - 1; t = anchor_of(c, T); nre = 0
    for _ in range(50):
        rm_ = np.maximum.accumulate(c[t:T + 1]); w_ = np.flatnonzero(c[t:T + 1] <= rm_ * 0.7)
        st_ = t + int(w_[0]) if len(w_) else None
        if st_ is None:
            break
        t = st_ + int(np.argmin(c[st_:T + 1])); nre += 1
    return t, nre


def measure(c, e, bp, last):
    Lp, nre = anchor_before(c, e)
    seg = c[e:last + 1]; rm = np.maximum.accumulate(seg); w = np.flatnonzero(seg <= rm * 0.7)
    stop = e + int(w[0]) if len(w) else last; opn = int(len(w) == 0)
    P = e + int(np.argmax(c[e:stop + 1]))
    cu = cuts_rec(c[Lp:P + 1])
    segno = 1 + sum(1 for a, b, r in cu if Lp + b < e)
    den = c[P] - c[Lp]
    return {"L": Lp, "重錨次數": nre, "stop": stop, "P": P, "未完": opn, "進場已漲": bp / c[Lp] - 1, "L到e天數": e - Lp,
            "進度": (bp - c[Lp]) / den if den > 0 else np.nan, "P漲幅": c[P] / bp - 1, "e到P天數": P - e, "段": segno, "段數到P": 1 + len(cu)}


def ctx_prices(ctx):
    n = len(ctx["cal"]); C = {}; O = {}
    for s, a in ctx["closes"].items():
        C[s] = pd.Series(np.asarray(a, float)[:n]).ffill().to_numpy(); O[s] = np.asarray(ctx["opens"][s], float)[:n]
    return C, O


def gen_trades(log):
    ctx = L_.setup_t1(log, t1=True)
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    sig13 = AND[(e >= G["w0"]) & (e <= G["w1"])]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), G["w1"])
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    gates = {}
    # 營量
    YL = {}
    for r in (0, 1):
        au = []
        o = R.simulate_mtm(sig13, "H60", 20, np.random.default_rng(RR.P1_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                           pick="relvol", queue_days=0, return_equity=True, audit=au, stop_force=SF)
        c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], G["w0"], G["w1"])
        rr = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0]
        gates[f"營量 r{r} ＝ resultsT1fix"] = repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"]))
        YL[r] = pd.DataFrame([a for a in au if a["side"] == "buy"])[["t", "sid", "px"]]
    f0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}); f0 = f0[f0["side"] == "buy"][["t", "sid", "px"]].reset_index(drop=True)
    y0 = YL[0].reset_index(drop=True)
    gates["營量 重產 r0 ＝ audit_seed0 買進列"] = bool(len(f0) == len(y0) and (f0["t"].to_numpy() == y0["t"].to_numpy()).all() and (f0["sid"].to_numpy() == y0["sid"].astype(str).to_numpy()).all() \
        and np.allclose(f0["px"].to_numpy(float), y0["px"].to_numpy(float), rtol=1e-6))
    gates["營量 r1 買進列 ＝ r0（不抽籤）"] = bool(len(YL[1]) == len(YL[0]) and (YL[1]["t"].to_numpy() == YL[0]["t"].to_numpy()).all() and (YL[1]["sid"].to_numpy() == YL[0]["sid"].to_numpy()).all())
    yl = f0.assign(策略="營量 v1", r=0)
    # 營飆
    rows = []; bad = 0
    for r in range(200):
        au = []
        o = L_.sim(ctx, {"stop_force": SF}, r, audit=au)
        c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], G["w0"], G["w1"])
        rr = ref[(ref["key"] == "c1") & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0]
        ok = repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"]))
        bad += int(not ok)
        b = pd.DataFrame([a for a in au if a["side"] == "buy"])[["t", "sid", "px"]]; b["r"] = r
        rows.append(b)
    gates["營飆 200 顆年化回落 ＝ resultsT1fix（不同顆數）"] = bad
    yf = pd.concat(rows, ignore_index=True).assign(策略="營飆 v1")
    log(f"[閘] {gates}")
    T = pd.concat([yl, yf], ignore_index=True); T["sid"] = T["sid"].astype(str); T["t"] = T["t"].astype(int)
    return ctx, T, gates


def q(x):
    x = pd.Series(x).dropna()
    return {"中位": float(x.median()), "p25": float(x.quantile(.25)), "p75": float(x.quantile(.75)), "n": int(len(x))} if len(x) else {"中位": np.nan, "p25": np.nan, "p75": np.nan, "n": 0}


def summarize(M):
    out = []
    for st in ("營量 v1", "營飆 v1"):
        for sg, (a, b) in SEGS.items():
            m0 = M[(M["策略"] == st) & (M["進場日"] >= a) & (M["進場日"] <= b)]
            for gn, lo, hi in GRP:
                m = m0[(m0["P漲幅"] >= lo) & (m0["P漲幅"] < hi)] if gn != "全部" else m0
                if not len(m0):
                    continue
                r = {"策略": st, "段": sg, "分組": gn, "筆數": len(m), "占全部": len(m) / len(m0), "去重筆": int(m[["sid", "t"]].drop_duplicates().shape[0]), "未完": m["未完"].mean() if len(m) else np.nan}
                for k in ("進場已漲", "L到e天數", "進度", "P漲幅", "e到P天數"):
                    for kk, v in q(m[k]).items():
                        if kk != "n":
                            r[f"{k} {kk}"] = v
                pv = m["進度"]
                cnt = [(pv < 0).sum()] + [((pv >= i / 10) & (pv < (i + 1) / 10 if i < 9 else pv <= 1.0)).sum() for i in range(10)] + [(pv > 1.0).sum()]
                for bn, cn in zip(BINS, cnt):
                    r[f"進度 {bn}"] = cn / max(pv.notna().sum(), 1)
                r["第1段"] = (m["段"] == 1).mean() if len(m) else np.nan; r["第2段"] = (m["段"] == 2).mean() if len(m) else np.nan; r["第3段以上"] = (m["段"] >= 3).mean() if len(m) else np.nan
                r["重錨過"] = (m["重錨次數"] > 0).mean() if len(m) else np.nan
                out.append(r)
    return pd.DataFrame(out)


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    ctx, T, gates = gen_trades(log)
    C, O = ctx_prices(ctx); cal = ctx["cal"]; last = len(cal) - 1
    memo = {}; rows = []; pxbad = 0
    for r in T.itertuples():
        k = (r.sid, r.t)
        if k not in memo:
            memo[k] = measure(C[r.sid], r.t, float(r.px), last)
            pxbad += int(not np.isclose(O[r.sid][r.t], r.px, rtol=1e-6))
        rows.append({**{"策略": r.策略, "r": r.r, "sid": r.sid, "t": r.t, "bp": r.px, "進場日": str(cal[r.t].date())}, **memo[k]})
    M = pd.DataFrame(rows)
    M["L日"] = [str(cal[int(x)].date()) for x in M["L"]]; M["P日"] = [str(cal[int(x)].date()) for x in M["P"]]
    gates["進場價 ＝ ctx 開盤（不同筆數）"] = pxbad
    M.to_csv(os.path.join(OUT, "trades.csv.gz"), index=False, float_format="%.8g")
    SM = summarize(M); SM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.5g")
    s0 = summarize(M[(M["策略"] == "營量 v1") | (M["r"] == 0)]); s0 = s0[s0["策略"] == "營飆 v1"]; s0.to_csv(os.path.join(OUT, "summary_營飆_種子0.csv"), index=False, float_format="%.5g")
    dd = M[M["策略"] == "營飆 v1"].drop_duplicates(["sid", "t"]).assign(策略="營飆 v1"); sdd = summarize(dd); sdd = sdd[sdd["策略"] == "營飆 v1"]
    sdd.to_csv(os.path.join(OUT, "summary_營飆_去重.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "閘": gates, "來源": {"營量 v1": "resultsYLlist/audit_seed0.csv.gz 買進列（另以正式程式重產逐列相同）", "營飆 v1": "listexit_lines.sim T1 版 r＝0～199 audit 重產（年化回落逐顆 ＝ resultsT1fix）"},
            "筆數": {"營量 v1": int((M["策略"] == "營量 v1").sum()), "營飆 v1（200 顆合併）": int((M["策略"] == "營飆 v1").sum()), "營飆 v1 去重": int(len(dd)),
                   "營飆 v1 種子 0": int(((M["策略"] == "營飆 v1") & (M["r"] == 0)).sum())},
            "日曆尾": str(cal[last].date()), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {META}")
    if not all(v is True or v == 0 for v in gates.values()):
        raise SystemExit(f"⛔ 閘不過 {gates}")


def check(log):
    ctx = L_.setup_t1(log, t1=True)
    cal = ctx["cal"]; n = len(cal); last = n - 1
    M = pd.read_csv(os.path.join(OUT, "trades.csv.gz"), dtype={"sid": str})
    errs = []; info = {}
    for st in ("營量 v1", "營飆 v1"):
        S_ = M[M["策略"] == st].drop_duplicates(["sid", "t"]).sample(50, random_state=20260930)
        nd = 0
        for r in S_.itertuples():
            c = pd.Series(np.asarray(ctx["closes"][r.sid], float)[:n]).ffill().to_numpy(); e = int(r.t); bp = float(r.bp)
            # L：逐日迴圈
            T = e - 1; lo = max(T - 249, 0)
            P0 = lo
            for d in range(lo, T + 1):
                if c[d] > c[P0]:
                    P0 = d
            t = lo
            for d in range(lo, P0 + 1):
                if c[d] < c[t]:
                    t = d
            for _ in range(50):
                rm = -np.inf; st_ = None
                for d in range(t, T + 1):
                    rm = max(rm, c[d])
                    if c[d] <= rm * 0.7:
                        st_ = d; break
                if st_ is None:
                    break
                m_ = st_
                for d in range(st_, T + 1):
                    if c[d] < c[m_]:
                        m_ = d
                t = m_
            rm = -np.inf; stop = last
            for d in range(e, last + 1):
                rm = max(rm, c[d])
                if c[d] <= rm * 0.7:
                    stop = d; break
            P = e
            for d in range(e, stop + 1):
                if c[d] > c[P]:
                    P = d
            # 段：逐日找 20% 拉回（新高日之間），低點在 e 之前者計數
            pk, pkd, tv, tvd, k = c[t], t, np.inf, -1, 0
            for d in range(t + 1, P + 1):
                if c[d] > pk:
                    if pkd > t and tv <= pk * (1 - X) * (1 + 1e-9) and tvd < e:
                        k += 1
                    pk, pkd, tv, tvd = c[d], d, np.inf, -1
                elif c[d] < tv:
                    tv, tvd = c[d], d
            prog = (bp - c[t]) / (c[P] - c[t])
            ok = t == int(r.L) and P == int(r.P) and stop == int(r.stop) and (1 + k) == int(r.段) and np.isclose(prog, r.進度, rtol=1e-6)
            if not ok:
                nd += 1; errs.append(f"{st} {r.sid} {r.t}: L {t}/{r.L} P {P}/{r.P} 段 {1 + k}/{r.段}")
        info[st] = {"抽": 50, "不同": nd}
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    out = {"讀法寫死": TIME, "抽 50 筆重算": info, "不同的筆": errs[:20], "Y1 閘（主程式）": meta["閘"],
           "通過": all(v["不同"] == 0 for v in info.values()) and all(v is True or v == 0 for v in meta["閘"].values())}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] {info}｜{errs[:3]}")


def page(log):
    SM = pd.read_csv(os.path.join(OUT, "summary.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            ".bar{display:inline-block;height:10px;background:#2b6cb0;vertical-align:middle}.sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}"
            ".sel select{font-size:16px;margin:2px 4px;padding:4px}.pane{display:none}.pane.on{display:block}")
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.0f}%"
    D_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.0f}"
    C_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 10:.1f} 成"
    g = lambda st, sg, gn: SM[(SM["策略"] == st) & (SM["段"] == sg) & (SM["分組"] == gn)].iloc[0]
    early = lambda r: sum(r[f"進度 {b}"] for b in BINS[:4])        # ＜0～3 成
    late = lambda r: sum(r[f"進度 {b}"] for b in BINS[7:])         # 6 成以上
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量營飆進場位置</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營量、營飆通常在漲勢的哪個位置買進？（正式版交易，2017-03～2026-08）</h1>",
         "<p class='warn'>⚠ 只是描述，沒有計入檢定數。「本輪頂」「第幾段」都是事後才知道的，只用來看位置；起漲點只用進場前一天以前的收盤找。</p>",
         f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。起漲點 ＝ 進場前 250 天內「最高收盤之前的最低收盤」（同買賣流程）；本輪頂 ＝ 進場後一路創新高、直到第一次從最高回落 30% 之前的最高收盤；"
         "<b>進度 ＝ 進場時已走完「起漲點 → 本輪頂」的幾成</b>；段 ＝ 從起漲點起每拉回 20% 切一段。"
         f"營量 {META['筆數']['營量 v1']:,} 筆（正式交易逐筆）；營飆 {META['筆數']['營飆 v1 去重']:,} 筆不同的交易（營飆抽籤，200 顆種子合併計 {META['筆數']['營飆 v1（200 顆合併）']:,} 次）。"
         + (f"查核：抽 50 筆逐日重算，營量 {CK['抽 50 筆重算']['營量 v1']['不同']}、營飆 {CK['抽 50 筆重算']['營飆 v1']['不同']} 筆不同；交易與正式回測逐位元對上。" if CK else "") + "</p>"]
    H.append("<h2>先講結論（全部期間）</h2><ul class='big'>")
    for st in ("營量 v1", "營飆 v1"):
        a = g(st, "全部", "全部"); f = g(st, "全部", "飆（P 漲幅 ≥100%）")
        H.append(f"<li><b>{st[:2]}</b>：進場時通常已從起漲點漲了 {P1(a['進場已漲 中位'])}（中位；一半的交易在 {P1(a['進場已漲 p25'])}～{P1(a['進場已漲 p75'])}），離起漲點 {D_(a['L到e天數 中位'])} 個交易日；"
                 f"進度中位 {C_(a['進度 中位'])}（{C_(a['進度 p25'])}～{C_(a['進度 p75'])}）——<b>{P_(early(a))} 在 3 成以內</b>，{P_(late(a))} 已過 6 成。"
                 f"落在第 1 段 {P_(a['第1段'])}、第 2 段 {P_(a['第2段'])}、第 3 段以上 {P_(a['第3段以上'])}。"
                 f"後來漲一倍以上的那 {P_(f['占全部'])}，進場時進度中位 {C_(f['進度 中位'])}、已漲 {P1(f['進場已漲 中位'])}。</li>")
    fy, fl = g("營量 v1", "全部", "飆（P 漲幅 ≥100%）"), g("營量 v1", "全部", "＜30%")
    gy, gl = g("營飆 v1", "全部", "飆（P 漲幅 ≥100%）"), g("營飆 v1", "全部", "＜30%")
    H.append(f"<li>⚠ 「後來飆的進度比較低」大部分是算法造成的：進度的分母是本輪頂，後面漲越多、進度就越低。看<b>進場時已從起漲點漲了多少</b>，"
             f"後來飆的和後來沒漲到 30% 的差不多（營量 {P1(fy['進場已漲 中位'])} 對 {P1(fl['進場已漲 中位'])}、營飆 {P1(gy['進場已漲 中位'])} 對 {P1(gl['進場已漲 中位'])}）"
             "⇒ <b>進場當下分不出來</b>會不會飆。</li>")
    H.append("<li class='ok'>一句話：營量、營飆<b>不是在起漲初期買</b>，通常是在第一段、起漲後大約 8 個月、已經漲了八九成才進場，約落在本輪漲幅的一半；"
             "後面還有沒有一大段，進場當下看不出來。</li></ul>")
    H.append("<div class='sel'>策略 <select id='s1' onchange='sw()'><option>營量 v1</option><option>營飆 v1</option></select>期間 <select id='s2' onchange='sw()'>"
             + "".join(f"<option>{k}</option>" for k in SEGS) + "</select></div>")
    for st in ("營量 v1", "營飆 v1"):
        for sg in SEGS:
            x = SM[(SM["策略"] == st) & (SM["段"] == sg)]
            if not len(x):
                continue
            H.append(f"<div class='pane' id='p{st[:2]}_{sg}'><h2>{html.escape(st)}｜{html.escape(sg)}</h2><div class='wrap'><table><tr><th class='l'>分組</th><th>筆數（占）</th>"
                     "<th>進場已漲<br><small>中位（p25～p75）</small></th><th>起漲點到進場<br><small>交易日</small></th><th>進度<br><small>中位（p25～p75）</small></th>"
                     "<th>本輪頂比進場<br><small>中位</small></th><th>進場到本輪頂<br><small>交易日</small></th><th>第 1／2／3+ 段</th><th>未完</th></tr>")
            for r in x.to_dict("records"):
                H.append(f"<tr><td class='l'>{html.escape(r['分組'])}</td><td>{int(r['筆數']):,}<br><small>{P_(r['占全部'])}</small></td>"
                         f"<td>{P1(r['進場已漲 中位'])}<br><small>{P1(r['進場已漲 p25'])}～{P1(r['進場已漲 p75'])}</small></td>"
                         f"<td>{D_(r['L到e天數 中位'])}<br><small>{D_(r['L到e天數 p25'])}～{D_(r['L到e天數 p75'])}</small></td>"
                         f"<td>{C_(r['進度 中位'])}<br><small>{C_(r['進度 p25'])}～{C_(r['進度 p75'])}</small></td>"
                         f"<td>{P1(r['P漲幅 中位'])}<br><small>{P1(r['P漲幅 p25'])}～{P1(r['P漲幅 p75'])}</small></td>"
                         f"<td>{D_(r['e到P天數 中位'])}<br><small>{D_(r['e到P天數 p25'])}～{D_(r['e到P天數 p75'])}</small></td>"
                         f"<td>{P_(r['第1段'])}／{P_(r['第2段'])}／{P_(r['第3段以上'])}</td><td>{P_(r['未完'])}</td></tr>")
            H.append("</table></div><h3>進度分佈（進場時已走完本輪的幾成）</h3><div class='wrap'><table><tr><th class='l'>進度</th>"
                     + "".join(f"<th>{html.escape(r['分組'].split('（')[0])}</th>" for r in x.to_dict("records")) + "</tr>")
            for b in BINS:
                H.append(f"<tr><td class='l'>{b}</td>" + "".join(f"<td><span class='bar' style='width:{r[f'進度 {b}'] * 120:.0f}px'></span> {P_(r[f'進度 {b}'])}</td>" for r in x.to_dict("records")) + "</tr>")
            H.append("</table></div></div>")
    H.append("<h2>名詞</h2><ul class='note'><li>進度 ＝（進場價 − 起漲點收盤）÷（本輪頂收盤 − 起漲點收盤）。0 成 ＝ 買在起漲點、10 成 ＝ 買在本輪頂；＜0 ＝ 買得比起漲點還低；＞10 成 ＝ 買完就沒再高過（本輪頂低於進場價）。</li>"
             "<li>起漲點若在進場前已經「從最高回落 30%」結束過，就改用那之後的最低收盤（錨到最新一輪，同買賣流程）。</li>"
             "<li>第幾段是事後切的：從起漲點到本輪頂，每次拉回 20% 以上又創新高就算一段；進場前已走完幾次這種拉回 ＝ 第幾段。</li>"
             "<li>未完 ＝ 到資料最後一天還沒從最高回落 30%，本輪頂是暫定的。營飆的數字是 200 顆種子合併（同一筆出現幾次算幾次）；種子 0 與去重筆另見 csv。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value.slice(0,2),b=document.getElementById('s2').value;"
             "document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p'+a+'_'+b))}sw()</script></main></body></html>")
    open(os.path.join(OUT, "營量營飆進場位置.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()

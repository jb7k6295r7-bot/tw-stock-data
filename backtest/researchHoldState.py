# -*- coding: utf-8 -*-
"""使用者 7 檔持股的「歷史同狀態」後續報酬分佈（台股 seq346、seq348 §三；⛔ 描述、不判、不計 N、不挑格）——回測線，2026-09-29。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchHoldState [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchHoldState_check.py

使用者原話（逐字）：「真的都沒辦法分析後續走勢!?」⇒ 選「2+3」（2 ＝ 本件）
⚠ 頁首逐字：「歷史同狀態的平均分佈，不是對這一檔的預測」
持股：6282 康舒｜8289 泰藝｜2609 陽明｜6209 今國光｜6443 元晶｜4164 承業醫｜6469 大樹；興櫃 7879 益材科技、3117 年程 不做（興櫃不在母體、沒有同格歷史）
═══ 定義（seq346 寫死）＋ 本線讀法（H 標，⭐ 看任何分佈前寫死）═══
 資料：tw-stock-data 最新 main（git archive 唯讀 ~/h2data/<sha>；本次 312d2aebca、資料日 2026-09-24）；早年 ＝ 早年版面 ~/earlydata/3edc0e2206/main（只上市）
 狀態日 d 收盤、還原價、有效 K 棒：
   A 收盤 ＞ MA60（上／下）× MA60 方向（MA60[d] ＞ MA60[d 前 20 根]：上／下）⇒ 4 類
   B 收盤 ＞ MA20（上／下）
   C 最新可用月營收創 24 月新高 ＝ p4_features.rev_hi24_flags（營量 v1 營收條件同一條：近 24 期不含當期、次月 10 日後第一個交易日生效）在 d 的值 ＝ 100；
     0 ⇒ 否；NaN ⇒ 該股-日不進 C 條件的格（計數必報）；月營收 ＝ 早年版面 2003～2014 ＋ main（researchMLlite 同一份接法）
   D 近 5 個交易日（d−4～d）三大法人合計淨買賣（stocks_inst 的 total 欄；某日無列 ⇒ 0；整檔沒有法人檔 ⇒ NaN）＞ 0 ⇒ ＋；≤ 0 ⇒ −
   E 距 250 根最高收盤（含 d）：≥ −10%｜−30% ≤ x ＜ −10%｜＜ −30%
   ⇒ 格 ＝ A×B×C×D×E（96）；早年去 D（48）
   ⚠ 等號歸屬：「上」一律用嚴格 ＞（相等歸下）；D 的 0 歸 −（seq346）
 H1 後續報酬 R_h ＝ c_ff[d＋h] ÷ c_ff[d] − 1（收盤到收盤、交易日曆 h 日；c_ff ＝ 收盤 ffill ⇒ 停止交易／下市以最後收盤計）；h ∈ {20, 60, 120}
    d＋h 超出資料 ⇒ 該 h 不計；(d, d＋h] 有壞根（research11.load_bars：相位事件、斷點、≥ 5 日缺口）⇒ 該 h 不計
    對 0050 超額 ＝ R_h − 0050 同期（同式）；「比 0050 好」＝ 超額 ＞ 0 的比例
 H2 樣本 ＝ 全市場 W1 eligible 股-日（量測日面板 eligible、到下一個量測日前有效；主 panel_ext 舊快取、早年 sig_main/panel：2012-06 起 W1、之前 liq∧bars）
    ∩ gate3（innov_ky 開：「-創」「-KY創」剔）∩ 該日有有效 K 棒 ∩ 狀態可算（≥ 250 根）
    段：主窗 狀態日 2017-03-01～2026-08-31｜早年 2005-01-01～2014-12-31（只上市）；無條件基準 ＝ 同段所有樣本股-日
 H3 持股的狀態 ＝ 最新資料日 t 的同一套定義（⛔ 不要求 eligible：那是持股本身）；樣本 ＜ 200 股-日 ⇒ 照報、標「樣本少」、⛔ 不併格、不換定義
 H4 報：n（股-日）、不同股-月數、上漲機率（R ＞ 0）、中位數、p25～p75、p10～p90、超額中位數、比 0050 好的比例；各 h
輸出 backtest/resultsHoldState/（網頁、LINE 純文字、明細）
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import universe_gate as UG
UG.set_innov_ky(True)
from backtest import research11 as R11
from backtest import p4_features as P4F

OUT = "backtest/resultsHoldState"
F_HTML = "持股歷史同狀態_20260929.html"
F_LINE = "持股歷史同狀態_LINE.txt"
RAW = "真的都沒辦法分析後續走勢!?"
HEAD = "歷史同狀態的平均分佈，不是對這一檔的預測"
HOLD = [("6282", "康舒"), ("8289", "泰藝"), ("2609", "陽明"), ("6209", "今國光"), ("6443", "元晶"), ("4164", "承業醫"), ("6469", "大樹")]
SKIP = [("7879", "益材科技"), ("3117", "年程")]
HS = (20, 60, 120)
EARLY_DATA = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
EARLY_REV = os.path.join(EARLY_DATA, "mops", "revenue_hist")
MPANEL = "backtest/resultsp9_engine/panel_ext.csv.gz"
EPANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
SEG = {"主窗": ("2017-03-01", "2026-08-31"), "早年": ("2005-01-01", "2014-12-31")}
ANAME = {3: "季線上、季線上揚", 2: "季線上、季線下彎", 1: "季線下、季線上揚", 0: "季線下、季線下彎"}
ENAME = {0: "離一年高點 10% 內", 1: "離一年高點 10～30%", 2: "離一年高點 30% 以上"}
_G: dict = {}


def _init(g):
    D.DATA = g["data"]; _G.update(g)


def one(args):
    """一檔：回 樣本股-日（窗內、eligible）的狀態碼與後續報酬，以及最後一根的狀態。"""
    sid, mk = args
    cal = _G["cal"]; n = len(cal)
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        return sid, None
    st = D.load_stock(sid, mk, cal)
    c = st.df["close"].to_numpy(float); cff = pd.Series(c).ffill().to_numpy()
    idx = B["idx"]; cb = B["c"]; nb = B["next_bad"]
    bad_day = np.zeros(n + 1, bool); bb = np.flatnonzero(nb[:len(idx)] == np.arange(len(idx))); bad_day[idx[bb]] = True
    cbad = np.r_[0, np.cumsum(bad_day)]
    ma60 = pd.Series(cb).rolling(60).mean().to_numpy(); ma20 = pd.Series(cb).rolling(20).mean().to_numpy()
    hi = pd.Series(cb).rolling(250).max().to_numpy()
    m60p = np.r_[np.full(20, np.nan), ma60[:-20]]
    ok = np.isfinite(ma60) & np.isfinite(m60p) & np.isfinite(hi) & np.isfinite(ma20)
    A = np.where(ok, 2 * (cb > ma60) + (ma60 > m60p), -1)
    Bc = np.where(ok, (cb > ma20).astype(int), -1)
    dist = cb / hi - 1
    E = np.where(ok, np.where(dist >= -0.10, 0, np.where(dist >= -0.30, 1, 2)), -1)
    FL = _G["FL"]
    fc = FL.get(sid)
    Cc = np.full(len(idx), -1)
    if fc is not None:
        v = fc[idx]; Cc = np.where(np.isfinite(v), (v == 100).astype(int), -1)
    Dc = np.full(len(idx), -1)
    if _G["inst"]:
        p = os.path.join(_G["data"], "stocks_inst", sid + ".csv")
        if os.path.exists(p):
            it = pd.read_csv(p, dtype={"date": str}, usecols=["date", "total"]).drop_duplicates("date", keep="last")
            tot = pd.to_numeric(it.set_index(pd.to_datetime(it["date"]))["total"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
            s5 = pd.Series(tot).rolling(5).sum().to_numpy()
            first = int(cal.searchsorted(pd.to_datetime(it["date"]).min()))
            d5 = np.where(np.arange(n) - 4 >= first, (s5 > 0).astype(int), -1)
            Dc = d5[idx]
    R = np.full((len(idx), len(HS)), np.nan); X = np.full((len(idx), len(HS)), np.nan)
    b50 = _G["b50"]
    for j, h in enumerate(HS):
        e = idx + h
        okh = (e <= n - 1)
        e2 = np.minimum(e, n - 1)
        clean = (cbad[e2 + 1] - cbad[idx + 1]) == 0
        m = okh & clean
        R[m, j] = cff[e2[m]] / cff[idx[m]] - 1
        X[m, j] = R[m, j] - (b50[e2[m]] / b50[idx[m]] - 1)
    last = {"日": str(cal[idx[-1]].date()), "A": int(A[-1]), "B": int(Bc[-1]), "C": int(Cc[-1]), "D": int(Dc[-1]), "E": int(E[-1]),
            "收盤": float(cb[-1]), "MA20": float(ma20[-1]), "MA60": float(ma60[-1]), "MA60_20根前": float(m60p[-1]), "距250高": float(dist[-1])}
    el = _G["EL"].get(sid)
    keep = np.zeros(len(idx), bool)
    if el is not None:
        keep = el[idx] & ok & (idx >= _G["d0"]) & (idx <= _G["d1"])
    k = np.flatnonzero(keep)
    rows = {"d": idx[k].astype(np.int32), "A": A[k].astype(np.int8), "B": Bc[k].astype(np.int8), "C": Cc[k].astype(np.int8), "D": Dc[k].astype(np.int8),
            "E": E[k].astype(np.int8), "R": R[k].astype(np.float32), "X": X[k].astype(np.float32)}
    return sid, {"rows": rows, "last": last}


def elig_arrays(cal, panel, early):
    pan = pd.read_csv(panel, dtype={"stock_id": str}, parse_dates=["measure_date"])
    tf = lambda s: s.astype(str).isin(["True", "1", "1.0"])
    mds = sorted(pan["measure_date"].unique()); n = len(cal)
    EL = {}
    for i, md in enumerate(mds):
        g = pan[pan["measure_date"] == md]
        el = (tf(g["eligible"]) if (not early or md >= pd.Timestamp("2012-06-01")) else (tf(g["liq_ok"]) & tf(g["bars_ok"])))
        a = int(cal.searchsorted(md)); b = int(cal.searchsorted(mds[i + 1])) if i + 1 < len(mds) else n
        for s in g.loc[el.to_numpy(), "stock_id"]:
            EL.setdefault(s, np.zeros(n, bool))[a:b] = True
    return EL


def rev_flag_cols(cal, main_data, include_main):
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv")))
    if include_main:
        fs += sorted(glob.glob(os.path.join(main_data, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    fl = P4F.rev_hi24_flags(rev, cal)
    return {s: fl[s].to_numpy(float) for s in fl.columns}, (str(rev.index.min()), str(rev.index.max()))


def world(tag, data, panel, early, procs, log, S):
    D.DATA = data
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    sids = list(zip(uni["stock_id"], uni["market"]))
    if not early:
        have = {s for s, _ in sids}
        for s, _ in HOLD:
            if s not in have:
                sids.append((s, stocks.set_index("stock_id").loc[s, "market"]))
    EL = elig_arrays(cal, panel, early)
    FL, rr = rev_flag_cols(cal, data, not early)
    b50 = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy()
    d0 = int(cal.searchsorted(pd.Timestamp(SEG[tag][0]))); d1 = int(cal.searchsorted(pd.Timestamp(SEG[tag][1]), side="right")) - 1
    g = {"data": data, "cal": cal, "EL": EL, "FL": FL, "b50": b50, "d0": d0, "d1": d1, "inst": not early}
    t0 = time.time()
    with Pool(procs, initializer=_init, initargs=(g,)) as pool:
        res = dict(pool.map(one, sids, chunksize=16))
    parts = []
    for s, v in res.items():
        if v is None or len(v["rows"]["d"]) == 0:
            continue
        r = v["rows"]
        parts.append(pd.DataFrame({"sid": s, "d": r["d"], "A": r["A"], "B": r["B"], "C": r["C"], "D": r["D"], "E": r["E"],
                                   **{f"R{h}": r["R"][:, j] for j, h in enumerate(HS)}, **{f"X{h}": r["X"][:, j] for j, h in enumerate(HS)}}))
    T = pd.concat(parts, ignore_index=True)
    T["月"] = np.array([str(x)[:7] for x in cal[T["d"].to_numpy()]])
    S["資料"][tag] = {"日曆": [str(cal[0].date()), str(cal[-1].date())], "月營收期別": rr, "樣本股-日": int(len(T)), "檔數": int(T["sid"].nunique()),
                    "C 缺（NaN）股-日": int((T["C"] < 0).sum()), "D 缺股-日": int((T["D"] < 0).sum()) if not early else "早年不用 D",
                    "狀態日": [str(cal[d0].date()), str(cal[d1].date())]}
    log(f"[{tag}] {S['資料'][tag]}｜{time.time() - t0:.0f}s")
    last = {s: res[s]["last"] for s, _ in HOLD if res.get(s)} if not early else {}
    return T, last, cal


def stats(T, h):
    r = T[f"R{h}"].to_numpy(float); x = T[f"X{h}"].to_numpy(float); m = np.isfinite(r)
    r, x, mon = r[m], x[m], T.loc[m, ["sid", "月"]]
    if len(r) == 0:
        return {"n": 0}
    q = np.percentile(r, [10, 25, 50, 75, 90])
    return {"n": int(len(r)), "股月": int(len(mon.drop_duplicates())), "上漲機率": float((r > 0).mean()), "中位": float(q[2]), "p25": float(q[1]), "p75": float(q[3]),
            "p10": float(q[0]), "p90": float(q[4]), "超額中位": float(np.median(x)), "贏0050": float((x > 0).mean())}


def cell_of(T, st, use_d):
    m = (T["A"] == st["A"]) & (T["B"] == st["B"]) & (T["C"] == st["C"]) & (T["E"] == st["E"])
    if use_d:
        m &= T["D"] == st["D"]
    return T[m]


def describe(st):
    return [ANAME[st["A"]], "月線上" if st["B"] == 1 else "月線下", "營收創 24 月新高" if st["C"] == 1 else ("營收沒創 24 月新高" if st["C"] == 0 else "營收旗標不明"),
            ("近 5 日法人買超" if st["D"] == 1 else ("近 5 日法人賣超（含 0）" if st["D"] == 0 else "法人資料不明")), ENAME[st["E"]]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    sha = subprocess.run(["git", "-C", os.path.expanduser("~/tw-p17"), "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    MAIN_DATA = os.path.expanduser(f"~/h2data/{sha}/data")
    assert os.path.isdir(os.path.join(MAIN_DATA, "stocks_inst")), MAIN_DATA
    log(f"===== researchHoldState {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜main {sha[:10]} =====")
    S = {"性質": "描述、不判、不計 N、不挑格（台股 seq346、seq348 §三）", "使用者原話": RAW, "頁首": HEAD, "main": sha, "資料": {}, "閘": {}}
    Tm, last, calm = world("主窗", MAIN_DATA, MPANEL, False, a.procs, log, S)
    Te, _, cale = world("早年", EARLY_DATA, EPANEL, True, a.procs, log, S)
    D.DATA = MAIN_DATA
    tday = str(calm[-1].date())
    S["狀態日 t"] = tday
    S["閘"]["持股最後一根 ＝ 資料日"] = {s: last[s]["日"] == tday for s, _ in HOLD}
    S["閘"]["innov_ky 開"] = UG.INNOV_KY
    base = {tag: {h: stats(T, h) for h in HS} for tag, T in (("主窗", Tm), ("早年", Te))}
    OUTR = {}
    for s, nm in HOLD:
        st = last[s]
        r = {"名稱": nm, "狀態": st, "描述": describe(st), "主窗": {}, "早年": {}}
        cm = cell_of(Tm, st, True); ce = cell_of(Te, st, False)
        for h in HS:
            r["主窗"][h] = stats(cm, h); r["早年"][h] = stats(ce, h)
        OUTR[s] = r
        log(f"[{s} {nm}] {r['描述']}｜主窗 n {r['主窗'][60].get('n')}｜60 天 上漲 {r['主窗'][60].get('上漲機率', float('nan')):.0%}")
    S["持股"] = OUTR; S["無條件基準"] = base
    # 明細（只存持股格的樣本摘要與全表的狀態碼分佈）
    np.savez_compressed(os.path.join(OUT, "rows_main.npz"), **{c: Tm[c].to_numpy() for c in ("d", "A", "B", "C", "D", "E", "R20", "R60", "R120", "X20", "X60", "X120")},
                        sid=Tm["sid"].to_numpy().astype("U6"))
    np.savez_compressed(os.path.join(OUT, "rows_early.npz"), **{c: Te[c].to_numpy() for c in ("d", "A", "B", "C", "D", "E", "R20", "R60", "R120", "X20", "X60", "X120")},
                        sid=Te["sid"].to_numpy().astype("U6"))
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda z: z.item() if hasattr(z, "item") else str(z))
    page(S); line(S)
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{time.time() - T0:.0f}s")


P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.1f}%"
Q = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.0f}%"


def line(S):
    L = [f"【持股：歷史同狀態】{HEAD}（資料 {S['狀態日 t']}；比對 2017～2026 全市場同狀態的股票）"]
    for s, r in S["持股"].items():
        z = r["主窗"][60]
        tag = "（樣本少）" if z.get("n", 0) < 200 else ""
        if z.get("n", 0) == 0:
            L.append(f"{s} {r['名稱']}：歷史上沒有跟它同狀態的股票（格內 0 筆）"); continue
        L.append(f"{s} {r['名稱']}：歷史上跟它同狀態的股票，60 天後上漲 {Q(z['上漲機率'])}、中間值 {P(z['中位'])}、比 0050 好 {Q(z['贏0050'])}{tag}")
    b = S["無條件基準"]["主窗"][60]
    L.append(f"（對照：全部股票任一天，60 天後上漲 {Q(b['上漲機率'])}、中間值 {P(b['中位'])}、比 0050 好 {Q(b['贏0050'])}）")
    open(os.path.join(OUT, F_LINE), "w", encoding="utf-8").write("\n".join(L) + "\n")


def page(S):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + \
          "\n.few{color:#c62828;font-weight:bold}td.l,th.l{text-align:left}.base td{color:#666}.st{margin:4px 0 8px;line-height:1.7}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>持股歷史同狀態</title>", f"<style>{CSS}</style></head><body><main>",
         f"<h1>{HEAD}</h1>",
         f"<p class='lead'>使用者原話：「{html.escape(RAW)}」<br>狀態日：{S['狀態日 t']}（資料庫最新資料日）。每一檔看它今天的五個狀態，找出歷史上全市場「五個狀態都一樣」的股票-日，"
         "看它們之後 20／60／120 個交易日的漲跌分佈。⛔ 只是描述，不是買賣建議。</p>",
         "<p class='note'>五個狀態：① 收盤在季線上／下 × 季線上揚／下彎 ② 收盤在月線上／下 ③ 最新月營收是否創 24 個月新高 ④ 近 5 日三大法人合計買超或賣超 ⑤ 離一年最高收盤多遠（10% 內／10～30%／30% 以上）。"
         "主窗 ＝ 2017～2026 上市櫃；早年 ＝ 2005～2014 只有上市、沒有法人資料（少看 ④）。樣本 ＜ 200 筆標「樣本少」。「中間 50%」＝ p25～p75、「中間 80%」＝ p10～p90。</p>"]
    base = S["無條件基準"]

    def tbl(title, d, bd):
        rows = [f"<h3>{title}</h3><div class='wrap'><table><tr><th class='l'></th><th>樣本（股-日／股-月）</th><th>上漲機率</th><th>中間值</th><th>中間 50%</th><th>中間 80%</th><th>比 0050 好</th><th>超額中間值</th></tr>"]
        for h in HS:
            z = d[h]; b = bd[h]
            few = z.get("n", 0) < 200
            if z.get("n", 0) == 0:
                rows.append(f"<tr><td class='l'>{h} 天後</td><td class='few'>0（沒有同格歷史）</td><td colspan=6></td></tr>")
            else:
                rows.append(f"<tr><td class='l'>{h} 天後</td><td class='{'few' if few else ''}'>{z['n']:,}／{z['股月']:,}{'（樣本少）' if few else ''}</td><td>{Q(z['上漲機率'])}</td><td>{P(z['中位'])}</td>"
                            f"<td>{P(z['p25'])}～{P(z['p75'])}</td><td>{P(z['p10'])}～{P(z['p90'])}</td><td>{Q(z['贏0050'])}</td><td>{P(z['超額中位'])}</td></tr>")
            rows.append(f"<tr class='base'><td class='l'>　全部股票</td><td>{b['n']:,}</td><td>{Q(b['上漲機率'])}</td><td>{P(b['中位'])}</td><td>{P(b['p25'])}～{P(b['p75'])}</td>"
                        f"<td>{P(b['p10'])}～{P(b['p90'])}</td><td>{Q(b['贏0050'])}</td><td>{P(b['超額中位'])}</td></tr>")
        return "".join(rows) + "</table></div>"
    for s, r in S["持股"].items():
        z = r["主窗"][60]
        head = (f"60 天後上漲 {Q(z['上漲機率'])}、中間值 {P(z['中位'])}、比 0050 好 {Q(z['贏0050'])}" if z.get("n", 0) else "沒有同格歷史")
        H.append(f"<details class='card' open><summary><b>{s} {html.escape(r['名稱'])}</b>｜{head}</summary>"
                 f"<div class='st'>今天的狀態：{'、'.join(r['描述'])}（收盤 {r['狀態']['收盤']:.2f}、月線 {r['狀態']['MA20']:.2f}、季線 {r['狀態']['MA60']:.2f}、離一年高點 {P(r['狀態']['距250高'])}）</div>"
                 + tbl("主窗 2017～2026（五個狀態都一樣）", r["主窗"], base["主窗"]) + tbl("早年 2005～2014（只上市、不看法人）", r["早年"], base["早年"]) + "</details>")
    H.append(f"<p class='note'>興櫃 {'、'.join(f'{s} {n}' for s, n in SKIP)} 不做：興櫃不在全市場母體裡，沒有同格歷史可比。報酬 ＝ 收盤到收盤、還原價、未扣成本；"
             f"比 0050 好 ＝ 同一段期間報酬高過 0050 的比例。資料：tw-stock-data main {S['main'][:10]}。</p>")
    H.append(f"<p class='note'>⚠ {HEAD}。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))


if __name__ == "__main__":
    main()

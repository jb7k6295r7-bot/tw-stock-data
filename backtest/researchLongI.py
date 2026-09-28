# -*- coding: utf-8 -*-
"""PREREG長線戰法 seq2 件 I：一目均衡表三役好轉（台股策略線 登錄 sha 04f9758bb33bc345；裁定 seq272；件 I 計 N ＋1）——回測線，2026-09-29。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLongI [--procs 2] [--seeds 200] [--seeds-yi 20] [--reps 200] [--tw50-base CSV]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLongI_check.py

⭐ 新件 ⇒ UG.set_innov_ky(True)（裁定 seq271 §二）；母體再與 gate3（開）交集
═══ 規則（登錄 §三；照 TEJ）＋ 本線讀法（I 標，⭐ 看任何數字前寫死）═══
 轉換線 ＝ (9 根最高 ＋ 9 根最低)÷2｜基準線 ＝ (26 根高＋低)÷2｜先行 A ＝ (轉換＋基準)÷2 前移 26｜先行 B ＝ (52 根高＋低)÷2 前移 26｜延遲線 ＝ 收盤後移 26
 I1 一律有效 K 棒、還原價；「前移 26」⇒ 第 t 根的雲 ＝ 第 t−26 根算出的先行 A、B；「延遲線在價上」⇒ 收盤[t] ＞ 收盤[t−26]
 I2 條件 ＝ 轉換[t] ＞ 基準[t]×1.01 ∧ 收盤[t] ＞ 收盤[t−26] ∧ 收盤[t] ＞ max(先行 A, 先行 B)[t]；⭐ 訊號 ＝ 條件由不成立轉成立那一根（三役「好轉」）；需第 77 根起（52＋26−1）
    ⇒ 下一根有效 K 棒開盤買（要是下一個交易日、可買：有成交、開盤有效、非開盤漲停）；壞根與前後 1 根不產生訊號
 I3 出場：ATR(14) Wilder（首值 ＝ 前 14 根 TR 平均）；第 j 根（進場根之後）收盤 ＜ max(收盤[進場根 … j−1]) − k × ATR[j−1] ⇒ 第 j＋1 根開盤賣；k ∈ {2, 3}
    持有中碰到壞根 ⇒ 壞根前一根收盤出；資料尾：T1（活到日曆尾 ⇒ xpos ＝ ncal、末日收盤）／停止交易 ⇒ 引擎 stop_force
 I4 母體：甲 ＝ 訊號日當時的臺灣50 成分（成分調整檔 tw50_changes：信箱附件、資料庫線 0123、sha256 ad506ee5b82f3b6e…；main 上找不到 ⇒ 用 ~/evtdata 那份，照實寫）
         ⚠ 調整檔只有「變動」、沒有任何一天的完整名單 ⇒ 要一份基底名單（某日 50 檔）才能逐季重建；--tw50-base 給（欄 stock_id、as_of）⇒ 往前往後套調整檔；沒給 ⇒ 甲不跑（照實寫）
         乙 ＝ 訊號日 W1 eligible（researchEvt.eligibility；2015 以前只上市）
 I5 組合：最多 20 檔、等權；同日候選多時 轉換÷基準 大者先（pick="relvol"）；成本 0.585%；stop_force 開；種子 default_rng(1000＋r)
    甲 --seeds 顆；乙（描述）--seeds-yi 顆（乙母體大、訊號多，照實寫）
 I6 段（一條權益 2009-01-05～2026-08-24；乙另一條 2005-01-03～2008-12-31）：判定 A ＝ 2009-01～2019-03、B ＝ 2024-04～2026-08（登錄原文；與 TEJ 段重疊 2024-04 一個月，照原文）；
    TEJ 段 2019-04～2024-04 只做重現描述；乙另報 2005～2008；判定格 ＝ 甲 k3（seq2 補行），件標籤 ＝ A、B 較嚴；其餘 3 格只描述
    退化（事前）：主格 A 段平均持股 ＜ 10 或現金 ＞ 30% ⇒ 標退化（主格已事前指定，照報）
 I7 假訊號臂（登錄 K4「同母體隨機日進場、同出場規則」）：主格每一筆換成「同一曆月、同母體（當日成分）隨機一檔、隨機一日」、隔日開盤進、同 I3 出場；
    reps 次、引擎種子 1000＋i、抽樣 default_rng([20260929, 9, i])；p ＝ 假年化 ≥ 本格年化中位 的比例（A、B 各報）
 I8 新規矩 ③：主格 A 或 B「合格／另列」⇒ 描述 檔數 10／30
輸出 backtest/resultsLongI/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG
UG.set_innov_ky(True)                                          # ⭐ 新件
from backtest import data as D
from backtest import tradability as TR
from backtest import research11 as R11
from backtest import rerun17 as RR
from backtest import researchEvt as EV
from backtest import chart_svg as CS

ST = EV.ST
OUT = "backtest/resultsLongI"
F_HTML = "長線戰法_件I_一目三役_20260929.html"
TW50 = os.path.expanduser("~/evtdata/tw50_changes.csv"); TW50_SHA = "ad506ee5b82f3b6e"
COST = 0.00585
KS = (2, 3)
WINS = {"主": ("2009-01-05", "2026-08-24"), "早年": ("2005-01-03", "2008-12-31")}
SEGS = {"A 2009-01～2019-03（判）": ("主", "2009-01-05", "2019-03-29"), "TEJ 2019-04～2024-04（重現描述）": ("主", "2019-04-01", "2024-04-30"),
        "B 2024-04～2026-08（判）": ("主", "2024-04-01", "2026-08-24"), "乙早年 2005～2008（描述）": ("早年", "2005-01-03", "2008-12-31")}
SA, SB = "A 2009-01～2019-03（判）", "B 2024-04～2026-08（判）"
ORDER = {"不合格": 0, "另列": 1, "合格": 2}
_G: dict = {}
_W: dict = {}


def wilder_atr(h, l, c, n=14):
    tr = np.r_[h[0] - l[0], np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])]
    atr = np.full(len(c), np.nan)
    if len(c) >= n:
        atr[n - 1] = tr[:n].mean()
        for k in range(n, len(c)):
            atr[k] = (atr[k - 1] * (n - 1) + tr[k]) / n
    return atr


def rmax(x, w):
    return pd.Series(x).rolling(w, min_periods=w).max().to_numpy(float)


def rmin(x, w):
    return pd.Series(x).rolling(w, min_periods=w).min().to_numpy(float)


def ichimoku(h, l, c):
    tk = (rmax(h, 9) + rmin(l, 9)) / 2; kj = (rmax(h, 26) + rmin(l, 26)) / 2
    sa0 = (tk + kj) / 2; sb0 = (rmax(h, 52) + rmin(l, 52)) / 2
    n = len(c); sa = np.full(n, np.nan); sb = np.full(n, np.nan); lag = np.full(n, np.nan)
    sa[26:] = sa0[:-26]; sb[26:] = sb0[:-26]; lag[26:] = c[:-26]
    with np.errstate(invalid="ignore"):
        cond = (tk > kj * 1.01) & (c > lag) & (c > np.fmax(sa, sb))
    ok = np.isfinite(tk) & np.isfinite(kj) & np.isfinite(sa) & np.isfinite(sb) & np.isfinite(lag)
    return cond & ok, ok, tk, kj, sa, sb


def atr_exit(k_mult, ke, c, o, atr, bad_k, idx, n_cal):
    """進場根 ke ⇒ (出場日曆位置, g, 類別)。"""
    nb = len(c); mx = c[ke]
    for j in range(ke + 1, nb):
        if bad_k[j]:
            return int(idx[j - 1]), float(c[j - 1] / o[ke] - 1.0), "壞根前出"
        if np.isfinite(atr[j - 1]) and c[j] < mx - k_mult * atr[j - 1]:
            if j + 1 < nb and not bad_k[j + 1]:
                return int(idx[j + 1]), float(o[j + 1] / o[ke] - 1.0), "ATR 停損"
            return int(idx[j]), float(c[j] / o[ke] - 1.0), "ATR 停損（無下一根，收盤）"
        mx = max(mx, c[j])
    if int(idx[-1]) == n_cal - 1:
        return n_cal, float(c[-1] / o[ke] - 1.0), "T1 補"
    return n_cal, float(c[-1] / o[ke] - 1.0), "停止交易（引擎 stop_force）"


def _init(cal):
    D.DATA = ST
    _G.update(cal=cal)


def load_one(args):
    sid, mk = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c_full = df["close"].to_numpy(float); valid = np.isfinite(c_full)
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "market", "amount"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    twse = (raw["market"].ffill() == "twse").to_numpy(); amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)
    out = {"valid": valid, "nbars": np.cumsum(valid), "amt": amt, "twse": twse, "rows": []}
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        return sid, out
    tb = TR.one(sid, cal); trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    idx, o, h, l, c = B["idx"], B["o"], B["h"], B["l"], B["c"]
    bad_k = B["next_bad"][:len(idx)] == np.arange(len(idx))
    near = bad_k.copy(); near[1:] |= bad_k[:-1]; near[:-1] |= bad_k[1:]
    cond, ok, tk, kj, sa, sb = ichimoku(h, l, c)
    atr = wilder_atr(h, l, c)
    sig = np.flatnonzero(cond[1:] & ok[:-1] & ~cond[:-1]) + 1
    for k_ in sig:
        if k_ < 77 or near[k_] or k_ + 1 >= len(idx):
            continue
        ed = int(idx[k_ + 1])
        if ed != int(idx[k_]) + 1 or not (trd[ed] and np.isfinite(o[k_ + 1]) and o[k_ + 1] > 0 and not up[ed]):
            continue
        row = {"sid": sid, "pos": int(idx[k_]), "entry_pos": ed, "ratio": float(tk[k_] / kj[k_])}
        for km in KS:
            xp, g, kd_ = atr_exit(km, k_ + 1, c, o, atr, bad_k, idx, n)
            row[f"xpos_k{km}"] = xp; row[f"g_k{km}"] = g; row[f"kind_k{km}"] = kd_
            row[f"hold_k{km}"] = int(np.searchsorted(idx, min(xp, n - 1), side="right") - (k_ + 1))
        out["rows"].append(row)
    out["bars"] = (idx, o, c, atr, bad_k, trd, up)
    return sid, out


def tw50_membership(cal, base_csv):
    """調整檔 ＋ 基底名單 ⇒ M[日曆位置] ＝ 成分集合（往前往後套）。"""
    ch = pd.read_csv(TW50, dtype=str, encoding="utf-8-sig")
    ch = ch[ch["action"].isin(["add", "delete"])].copy()
    ch["ep"] = [int(cal.searchsorted(pd.Timestamp(d))) for d in ch["effective_date"]]
    base = pd.read_csv(base_csv, dtype=str)
    asof = pd.Timestamp(base["as_of"].iloc[0]); b0 = int(cal.searchsorted(asof, side="right")) - 1
    S = set(base["stock_id"])
    n = len(cal); M = [None] * n
    ev = {}
    for p, a, s in zip(ch["ep"], ch["action"], ch["stock_id"]):
        ev.setdefault(p, []).append((a, s))
    cur = set(S)
    for t in range(b0, n):                                  # 往後：生效日當天起
        if t > b0:
            for a, s in ev.get(t, []):
                (cur.add if a == "add" else cur.discard)(s)
        M[t] = frozenset(cur)
    cur = set(S)
    for t in range(b0, -1, -1):                             # 往前：t 當天的名單 ⇒ 撤銷 t 生效的調整即得 t−1
        M[t] = frozenset(cur) if t != b0 else M[t]
        for a, s in ev.get(t, []):
            (cur.discard if a == "add" else cur.add)(s)
    return M, {"基底日": str(asof.date()), "基底檔數": len(S), "調整列": int(len(ch))}


def _stats(o, segs):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float); row = {}
    for sg, (x, y) in segs.items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_); row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
    return row, eq


def run_cell(job):
    fam, win, km, N, r = job
    W = _W; sig = W["SIG"][(fam, win, km)]
    aud = []
    o = R11.simulate_mtm(sig, f"k{km}", N, np.random.default_rng(1000 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                         log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=aud)
    row, eq = _stats(o, W["SEGP"][win])
    cnt = np.zeros(len(eq) + 1)
    for a_ in aud:
        cnt[a_["t"]] += 1 if a_["side"] == "buy" else -1
    hold = np.cumsum(cnt)[:len(eq)]
    for sg, (x, y) in W["SEGP"][win].items():
        row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1]))
    row.update({"fam": fam, "win": win, "k": km, "N": N, "r": r, "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16]})
    return row


def run_fake(job):
    i, km = job
    W = _W; base = W["SIG"][("甲", "主", km)]
    rng = np.random.default_rng([20260929, 9, i]); rows = []
    for m, g in base.groupby("_m"):
        days = W["MDAYS"][m]
        for _ in range(len(g)):
            for _try in range(50):
                t = int(days[rng.integers(0, len(days))]); mem = sorted(W["MEM"][t])
                s = mem[rng.integers(0, len(mem))]
                X = W["BARS"].get(s)
                if X is None:
                    continue
                idx, o, c, atr, bad_k, trd, up = X
                k_ = int(np.searchsorted(idx, t))
                if k_ + 1 >= len(idx) or idx[k_] != t or int(idx[k_ + 1]) != t + 1 or bad_k[k_]:
                    continue
                ed = t + 1
                if not (trd[ed] and np.isfinite(o[k_ + 1]) and o[k_ + 1] > 0 and not up[ed]):
                    continue
                xp, gg, _ = atr_exit(km, k_ + 1, c, o, atr, bad_k, idx, W["NP"] - 1)
                rows.append((s, t, ed, xp, gg, 1.0))
                break
    sig = pd.DataFrame(rows, columns=["sid", "pos", "entry_pos", f"xpos_k{km}", f"g_k{km}", "relvol"])
    o_ = R11.simulate_mtm(sig, f"k{km}", 20, np.random.default_rng(1000 + i), W["closes"], W["opens"], W["NP"], return_equity=True,
                          log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
    row, _ = _stats(o_, W["SEGP"]["主"])
    row.update({"i": i, "筆": len(sig)})
    return row


def label(c, m, b):
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--seeds-yi", type=int, default=20); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--tw50-base", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchLongI {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜seeds 甲 {a.seeds}／乙 {a.seeds_yi}｜reps {a.reps}｜UG.INNOV_KY＝{UG.INNOV_KY}｜tw50 基底 {a.tw50_base} =====")
    S = {"件": "PREREG長線戰法 seq2 件 I 一目三役好轉（登錄 sha 04f9758bb33bc345；裁定 seq272；主格 甲 臺灣50 × k3）", "共用閘 -KY創": UG.INNOV_KY}
    import hashlib as _h
    S["tw50 調整檔 sha256"] = _h.sha256(open(TW50, "rb").read()).hexdigest()[:16]
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(roster); mk = dict(zip(roster["stock_id"], roster["market"]))
    sids = sorted(set(U["stock_id"]) & {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))})
    if a.limit:
        sids = sids[::max(1, len(sids) // a.limit)]
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        P = {s: v for s, v in pool.imap_unordered(load_one, [(s, mk.get(s, "twse")) for s in sids], chunksize=16) if v is not None}
    sids = [s for s in sids if s in P]
    log(f"[讀檔] {len(sids)} 檔｜{time.time() - T0:.0f}s")
    E, _ = EV.eligibility(cal, P, sids, log)
    ix = {s: i for i, s in enumerate(sids)}
    bi = int(cal.searchsorted(pd.Timestamp("2015-01-05")))
    T = pd.DataFrame([r for s in sids for r in P[s]["rows"]])
    T["乙"] = [bool(E[ix[s], p]) and (p >= bi or bool(P[s]["twse"][p])) for s, p in zip(T["sid"], T["pos"])]
    MEM = None
    if a.tw50_base:
        MEM, minfo = tw50_membership(cal, a.tw50_base)
        S["臺灣50 成分重建"] = minfo
        T["甲"] = [s in MEM[p] for s, p in zip(T["sid"], T["pos"])]
    else:
        T["甲"] = False
        S["臺灣50 成分重建"] = "⛔ 沒有基底名單（調整檔只有變動）⇒ 甲不跑；需要某一天完整 50 檔名單（--tw50-base）"
    WP = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in WINS.items()}
    T["win"] = np.select([(T["entry_pos"] >= WP["主"][0]) & (T["entry_pos"] <= WP["主"][1]), (T["entry_pos"] >= WP["早年"][0]) & (T["entry_pos"] <= WP["早年"][1])], ["主", "早年"], "")
    T.to_csv(os.path.join(OUT, "signals.csv.gz"), index=False, float_format="%.17g")
    SEGP = {"主": {}, "早年": {}}
    for sg, (w, x, y) in SEGS.items():
        SEGP[w][sg] = (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y))))
    fams = (["甲"] if MEM is not None else []) + ["乙"]
    SIG = {}
    for fam in fams:
        for win in (("主",) if fam == "甲" else ("主", "早年")):
            g = T[T[fam] & (T["win"] == win)].sort_values(["entry_pos", "sid"]).reset_index(drop=True)
            for km in KS:
                SIG[(fam, win, km)] = g[["sid", "pos", "entry_pos", f"xpos_k{km}", f"g_k{km}"]].assign(relvol=g["ratio"])
    S["訊號數"] = {f"{f}｜{w}": int(len(SIG[(f, w, 2)])) for (f, w, k) in SIG if k == 2}
    need = sorted(set().union(*[set(v["sid"]) for v in SIG.values()]))
    closes, opens = RR.load_prices(need, cal, pd.Series(mk), "branch"); closes, opens = RR.pad_px_t1(closes, opens)
    SF = R11.stop_force_days(R11.valid_from_data(need, pd.Series(mk), cal), WP["主"][1])
    _W.update(SIG=SIG, closes=closes, opens=opens, NP=n + 1, SF=SF, SEGP=SEGP)
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    B50 = {sg: RR.bench_row(cal, bench, SEGP[w][sg][0], SEGP[w][sg][1] + 1) for sg, (w, x, y) in SEGS.items()}
    S["0050"] = B50
    jobs = []
    for (fam, win, km) in SIG:
        ns = a.seeds if fam == "甲" else a.seeds_yi
        jobs += [(fam, win, km, 20, r) for r in range(ns)]
    t0 = time.time()
    with Pool(a.procs) as pool:
        SEED = pd.DataFrame(pool.map(run_cell, jobs, chunksize=2))
    SEED.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    log(f"[組合] {len(jobs)} 次｜{time.time() - t0:.0f}s")
    PT = []
    for fam in fams:
        for km in KS:
            row = {"格": f"{fam}_k{km}", "fam": fam, "k": km, "主格": fam == "甲" and km == 3}
            for sg, (w, x, y) in SEGS.items():
                g = SEED[(SEED["fam"] == fam) & (SEED["win"] == w) & (SEED["k"] == km)]
                if not len(g):
                    continue
                c, mm = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                row.update({f"{sg}_年化": c, f"{sg}_回落": mm, f"{sg}_比值": c / abs(mm), f"{sg}_標籤": label(c, mm, B50[sg]),
                            f"{sg}_持股": float(g[f"{sg}_持股"].median()), f"{sg}_現金": float(g[f"{sg}_現金"].median())})
            row["退化"] = bool(row.get(f"{SA}_持股", 99) < 10 or row.get(f"{SA}_現金", 0) > 0.30)
            PT.append(row)
    PT = pd.DataFrame(PT); PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    # 逐筆
    TS = {}
    for fam in fams:
        for km in KS:
            for sg, (w, x, y) in SEGS.items():
                x0, y0 = SEGP[w][sg]
                g = T[T[fam] & (T["entry_pos"] >= x0) & (T["entry_pos"] <= y0)]
                if len(g):
                    net = g[f"g_k{km}"] - COST
                    TS[f"{fam}_k{km}｜{sg}"] = {"筆": int(len(g)), "平均淨報酬": float(net.mean()), "勝率": float((net > 0).mean()), "平均持有根數": float(g[f"hold_k{km}"].mean()),
                                               "持有根數 p10／p50／p90": [float(q) for q in g[f"hold_k{km}"].quantile([0.1, 0.5, 0.9])]}
    S["逐筆（母體內全部訊號）"] = TS
    J = {}
    if MEM is not None:
        pr = PT.set_index("格").loc["甲_k3"]
        J = {"A": pr[f"{SA}_標籤"], "B": pr[f"{SB}_標籤"], "件標籤": min((pr[f"{SA}_標籤"], pr[f"{SB}_標籤"]), key=lambda x: ORDER[x]), "主格退化": bool(pr["退化"])}
        # 假訊號
        T["_m"] = [str(cal[p])[:7] for p in T["pos"]]
        SIG[("甲", "主", 3)] = SIG[("甲", "主", 3)].assign(_m=[str(cal[p])[:7] for p in SIG[("甲", "主", 3)]["pos"]])
        MD = {}
        for t in range(WP["主"][0] - 1, WP["主"][1]):
            MD.setdefault(str(cal[t])[:7], []).append(t)
        _W.update(SIG=SIG, MEM=MEM, MDAYS={k: np.array(v) for k, v in MD.items()}, BARS={s: P[s].get("bars") for s in sids})
        with Pool(a.procs) as pool:
            FR = pd.DataFrame(pool.map(run_fake, [(i, 3) for i in range(a.reps)], chunksize=4))
        FR.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
        J["假訊號臂（同母體隨機日）"] = {sg: {"p（假年化 ≥ 本格）": float(np.mean(FR[f"{sg}_年化"] >= pr[f"{sg}_年化"])), "假年化中位": float(FR[f"{sg}_年化"].median())}
                                   for sg in (SA, SB)}
        trig = J["A"] in ("合格", "另列") or J["B"] in ("合格", "另列")
        J["新規矩③"] = "要跑" if trig else "不適用（主格 A、B 皆非合格／另列）"
        if trig:
            sens = {}
            for NN in (10, 30):
                with Pool(a.procs) as pool:
                    SR = pd.DataFrame(pool.map(run_cell, [("甲", "主", 3, NN, r) for r in range(a.seeds)], chunksize=4))
                sens[f"檔數 {NN}"] = {sg: [float(SR[f"{sg}_年化"].median()), float(SR[f"{sg}_回落"].median())] for sg in (SA, SB)}
            J["新規矩③ 描述"] = sens
    S["判定（主格 甲_k3）"] = J
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(S, PT)
    page(S, PT, T, cal, mk)
    log(f"[完] {time.time() - T0:.0f}s｜{J}")


def P_(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report(S, PT):
    J = S["判定（主格 甲_k3）"]; B = S["0050"]
    L = ["# PREREG長線戰法 seq2 件 I：一目三役好轉", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 sha 04f9758bb33bc345；裁定 seq272。回測線。⭐ stop_force 開；T1 開；共用閘「-KY創」開。引用請寫「回測 PREREG長線戰法 件I」。", ""]
    if J:
        pr = PT.set_index("格").loc["甲_k3"]
        L.append(f"**結論：主格 甲（臺灣50）k3：A 2009-01～2019-03 {P_(pr[f'{SA}_年化'])}／{P_(pr[f'{SA}_回落'])}（{J['A']}）、B 2024-04～2026-08 {P_(pr[f'{SB}_年化'])}／{P_(pr[f'{SB}_回落'])}（{J['B']}）⇒ 件標籤 {J['件標籤']}；"
                 f"TEJ 段重現 {P_(pr['TEJ 2019-04～2024-04（重現描述）_年化'])}（TEJ 原文 +23.6%，MSCI 91 檔）。**")
    else:
        L.append(f"**⛔ 主格（甲 臺灣50）沒跑：{S['臺灣50 成分重建']}。下表只有乙（W1 全體，描述）。**")
    L += ["", "| 格 | " + " | ".join(SEGS) + " |", "|---" * (len(SEGS) + 1) + "|"]
    for _, r in PT.iterrows():
        L.append(f"| {r['格']}{'（主格）' if r['主格'] else '（描述）'} | " + " | ".join(
            (f"{P_(r[f'{sg}_年化'])}／{P_(r[f'{sg}_回落'])}（{r[f'{sg}_標籤']}）" if f"{sg}_年化" in r and pd.notna(r.get(f'{sg}_年化')) else "—") for sg in SEGS) + " |")
    L.append("| 0050 | " + " | ".join(f"{P_(B[sg]['cagr'])}／{P_(B[sg]['mdd'])}" for sg in SEGS) + " |")
    L += ["", "## 逐筆（持有天數分佈）", "", "```", json.dumps(S["逐筆（母體內全部訊號）"], ensure_ascii=False, indent=1), "```", "",
          f"- 訊號數：{json.dumps(S['訊號數'], ensure_ascii=False)}", f"- 臺灣50 成分：{json.dumps(S['臺灣50 成分重建'], ensure_ascii=False)}；調整檔 sha256 {S['tw50 調整檔 sha256']}",
          f"- 判定與假訊號：{json.dumps(J, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))


def page(S, PT, T, cal, mk):
    B = S["0050"]
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\ntd.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>長線戰法 件I 一目三役</title>", f"<style>{CSS}</style></head><body><main>", "<h1>長線戰法 件 I：一目均衡表三役好轉</h1>",
         "<p class='lead'>進場：轉換線 ＞ 基準線×1.01、收盤高於 26 天前（延遲線在價上）、收盤在雲上 ⇒ 三個條件剛轉成全部成立的那天收盤 ⇒ 隔天開盤買；"
         "出場：持有以來最高收盤 − k × ATR(14)，收盤跌破 ⇒ 隔天開盤賣。主格＝臺灣50 成分 × k＝3。都扣成本 0.585%。</p>"]
    if not S["判定（主格 甲_k3）"]:
        H.append(f"<p class='note'><b>⛔ 主格沒跑：</b>{html.escape(str(S['臺灣50 成分重建']))}</p>")
    H.append("<div class='wrap'><table><tr><th class='l'>格</th>" + "".join(f"<th>{html.escape(sg)}</th>" for sg in SEGS) + "</tr>")
    for _, r in PT.iterrows():
        H.append(f"<tr><td class='l'>{r['格']}{'（主格）' if r['主格'] else ''}</td>" + "".join(
            (f"<td>{P_(r[f'{sg}_年化'])}／{P_(r[f'{sg}_回落'])}<br>{r[f'{sg}_標籤']}</td>" if f"{sg}_年化" in r and pd.notna(r.get(f'{sg}_年化')) else "<td>—</td>") for sg in SEGS) + "</tr>")
    H.append("<tr><td class='l'>0050</td>" + "".join(f"<td>{P_(B[sg]['cagr'])}／{P_(B[sg]['mdd'])}</td>" for sg in SEGS) + "</tr></table></div>")
    # 例子：主格（或乙 k3）B 段、淨報酬 最差／中位／最好
    fam = "甲" if S["判定（主格 甲_k3）"] else "乙"
    x0, y0 = int(cal.searchsorted(pd.Timestamp("2024-04-01"))), int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    g = T[T[fam] & (T["entry_pos"] >= x0) & (T["entry_pos"] <= y0)].sort_values("g_k3").reset_index(drop=True)
    H.append(f"<h2>例子（{fam}、k3、2024-04 起）</h2>" + CS.legend_html())
    D.DATA = ST
    names = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id").set_index("stock_id")["name"]
    for lab, i in ([] if not len(g) else [("最差", 0), ("中位", len(g) // 2), ("最好", len(g) - 1)]):
        r = g.iloc[i]; s = r["sid"]; e = int(r["entry_pos"]); x = min(int(r["xpos_k3"]), len(cal) - 1)
        df = D.load_stock(s, mk.get(s, "twse"), cal).df; o = df["open"].to_numpy(float)
        i0 = max(0, e - 80); i1 = min(len(cal) - 1, x + 15); sl = slice(i0, i1 + 1)
        cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        marks = [{"i": e - i0, "px": float(o[e]), "kind": "entry", "label": f"買 {o[e]:.2f}"}, {"i": x - i0, "px": float(cf[x]), "kind": "exit", "label": f"賣（{r['kind_k3']}）"}]
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl],
                           df["close"].to_numpy(float)[sl], df["volume"].to_numpy(float)[sl] / 1000.0, ma={k: CS.moving_avg(cf, k)[sl] for k in (20, 60)}, marks=marks, title=s, show_title=False)
        H.append(f"<details class='card' open><summary><b>{lab}</b>｜{s} {html.escape(str(names.get(s, '')))}｜進場 {cal[e].date()}｜{P_(r['g_k3'] - COST)}（扣成本）｜持有 {int(r['hold_k3'])} 天</summary>{svg}</details>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))


if __name__ == "__main__":
    main()

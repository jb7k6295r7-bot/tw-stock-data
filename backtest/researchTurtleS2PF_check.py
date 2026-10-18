# -*- coding: utf-8 -*-
"""PREREG海龜系統2組合層 seq1【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsTurtleS2PF/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtleS2PF_check [--procs 3]

C1 成交價（抽樣逐筆、獨立重寫）：從 research11.load_bars 原始還原 K 棒重算 買價 ＝ max(T 開盤, 前 55 根最高)、N（Wilder 20 自寫、壞根重起）、
   停損 ＝ 買價 − 2N[k−1]、逐根出場（20 日低點／2N、價 min(開, 線)、同根取低、鎖死跌停順延、壞根前收盤、下市末根、資料尾）⇒ 對 events 表。
C2 逐日重建持倉與淨值（每一臂、兩世界、全部日子）：只用 trades 表（買進日、金額、市值基準價、排程出場、R）＋ 0050 開收盤 ＋ 快取收盤，
   自己記 0050 單位數（T 開盤賣 0.2425% 撥款、賣出當天留現金、隔天開盤買回 0.1425%）⇒ 對 eq npz 逐日；並驗每筆金額 ＝ min(前日淨值÷10, 可撥 0050)、
   入帳 ＝ 金額×(1＋R−0.585%)、持股 ≤ 10、同檔不重複、當天賣出不再買、候選有剩而槽有空的日子 0 天；另印 5 個抽樣日的明細。
C3 0050 價：npz 的 Bc／Bo ＝ data.load_stock("0050") 還原收盤（ffill）／開盤（缺 ⇒ 前一日收盤）。
C4 滑價：Mslip 每筆 市值基準價 ＝ 買價×1.005、R ＝ 賣價×0.995÷(買價×1.005)−1（買價、賣價取主判 events 表）；主判與滑價同一批買進日與代號？（只報）。
C5 段指標：自寫年化（(末/首)^(245/(日數))−1）與最大回落、0050 同窗 ⇒ 對主表；判準標籤重算。
C6 操作負擔：抽 8 天，全部股票從 load_bars 原始 K 棒重算「前一日收盤 ≥ 0.97 × 前 55 根最高 ∧ 前一日在母體」檔數 ⇒ 對 burden 表。
C7 隨機：200 列齊、有限（隨機臂與主判同一個組合迴圈，迴圈本身由 C2 驗）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTurtleS2PF as M                # noqa: E402  只取常數、rand_rows（C7 重跑）
from backtest import researchAscTri as AS                   # noqa: E402  load_world
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402
from backtest import data as D                              # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = M.OUT
COST = 0.00585; BUY = 0.001425; SELL = 0.002425; SLIP = 0.005
_G: dict = {}


def bars(W, sid):
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"])
    idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    return B, idx, o, h, l, c, bad


def wilder(h, l, c, bad, n=20):
    nb = len(c); out = np.full(nb, np.nan); seg0 = 0; trs = []; v = None
    for j in range(nb):
        if j == 0 or bad[j]:
            seg0 = j; trs = []; v = None; continue
        tr = max(h[j] - l[j], abs(h[j] - c[j - 1]), abs(l[j] - c[j - 1]))
        if v is None:
            trs.append(tr)
            if len(trs) == n:
                v = sum(trs) / n; out[j] = v
        else:
            v = (v * (n - 1) + tr) / n; out[j] = v
    return out


def replay(W, sid, Tpos):
    """C1：獨立逐根重算一筆 S2 主讀法。"""
    B, idx, o, h, l, c, bad = bars(W, sid)
    n0 = W["n0"]; i = W["ix"][sid]; DNL = W["DNL"][i]
    k = int(np.searchsorted(idx, Tpos)); assert idx[k] == Tpos
    pm = max(h[k - 55:k]); assert h[k] > pm
    Pp = max(o[k], pm)
    N = wilder(h, l, c, bad)
    stop = Pp - 2 * N[k - 1]
    nb = len(idx); delisted = (n0 - 1 - idx[-1]) >= 5
    j = k + 1
    while True:
        if j >= nb:
            return Pp, stop, (int(idx[-1]), c[-1], "末根") if delisted else (-1, np.nan, "資料尾")
        if bad[j]:
            return Pp, stop, (int(idx[j - 1]), c[j - 1], "壞根")
        cl = min(l[j - 20:j])
        a_ = l[j] < cl; b_ = l[j] <= stop
        if a_ or b_:
            if DNL[idx[j]]:
                y = j + 1
                while y < nb:
                    if bad[y]:
                        return Pp, stop, (int(idx[y - 1]), c[y - 1], "壞根")
                    if not DNL[idx[y]]:
                        return Pp, stop, (int(idx[y]), o[y] if (np.isfinite(o[y]) and o[y] > 0) else c[y], "順延")
                    y += 1
                return Pp, stop, (int(idx[-1]), c[-1], "末根") if delisted else (-1, np.nan, "資料尾")
            ok = np.isfinite(o[j]) and o[j] > 0
            pa = min(o[j], cl) if ok else cl; pb = min(o[j], stop) if ok else stop
            px = min(pa, pb) if (a_ and b_) else (pa if a_ else pb)
            return Pp, stop, (int(idx[j]), px, "觸")
        j += 1


def c1(W, ev, rng, n, log):
    dates = np.array([str(d.date()) for d in W["cal"]]); dpos = {d: q for q, d in enumerate(dates)}
    pick = rng.choice(len(ev), size=min(n, len(ev)), replace=False)
    bad = []
    for q in pick:
        r = ev.iloc[q]
        Pp, stop, (xp, px, kind) = replay(W, r["sid"], dpos[r["T"]])
        okP = abs(Pp / float(r["買價"]) - 1) < 1e-12
        okx = (xp == (dpos[r["出場日"]] if r["出場日"] else -1))
        rr = px / Pp - 1 if xp >= 0 else np.nan
        okR = (np.isnan(rr) and r["R"] == "") or (r["R"] != "" and abs(rr - float(r["R"])) < 1e-12)
        if not (okP and okx and okR):
            bad.append((r["sid"], r["T"], Pp, r["買價"], xp, r["出場日"], rr, r["R"], kind))
    log(f"[C1 {W['name']}] 抽 {len(pick)} 筆逐根重算：不同 {len(bad)} {bad[:3]}")
    return {"抽樣": int(len(pick)), "不同": len(bad), "例": [str(b) for b in bad[:5]]}


def c2(W, CM, Bc, Bo, df, Z, arm, ev, log):
    n0 = W["n0"]; ix = W["ix"]; mode = M.ARMS[arm]["mode"]
    eq_s = Z[f"{arm}_eq"]; nh_s = Z[f"{arm}_nh"]
    df = df.reset_index(drop=True)
    buys_by = {}; sells_by = {}
    for q, (t, x) in enumerate(zip(df["買進日pos"], df["排程出場pos"])):
        buys_by.setdefault(int(t), []).append(q)
        if x >= 0:
            sells_by.setdefault(int(x), []).append(q)
    units = 0.0 if mode == "cash" else 1.0 / Bc[0]; cash = 1.0 if mode == "cash" else 0.0; pend = 0.0
    hold = {}; nav = np.zeros(n0); nh = np.zeros(n0, int)
    e_amt = 0.0; e_proc = 0.0; e_dup = 0; e_same = 0; e_over = 0; miss = 0; miss_ex = []; chk_t = {}; starve = 0
    cand = {}
    if ev is not None:
        dpos = {str(x.date()): q for q, x in enumerate(W["cal"])}
        for s_, Td in zip(ev["sid"], ev["T"]):
            cand.setdefault(dpos[Td], set()).add(ix[s_])
    J_ = np.array([ix[s] for s in df["sid"]])
    amt = df["金額"].to_numpy(float); ep = df["市值基準價"].to_numpy(float); Rr = df["R"].to_numpy(float)
    proc = df["入帳"].to_numpy(float)
    for t in range(n0):
        if pend:
            if mode == "cash":
                cash += pend
            else:
                units += pend * (1 - BUY) / Bo[t]
            pend = 0.0
        sold = set()
        for q in sells_by.get(t, []):
            if q in hold and int(df.at[q, "買進日pos"]) < t:
                p_ = amt[q] * (1 + Rr[q] - COST); pend += p_; e_proc = max(e_proc, abs(p_ / proc[q] - 1))
                del hold[q]; sold.add(J_[q])
        if ev is not None and t in cand:          # 槽有空且有未持有候選 ⇒ 買進數應 ＝ min(空槽, 可買候選)
            hs = {J_[x] for x in hold}
            av_ = cand[t] - hs - sold
            exp_ = min(10 - len(hold), len(av_)); got = len(buys_by.get(t, []))
            if exp_ != got:
                chk_t[t] = (exp_, got)
        for q in buys_by.get(t, []):
            if J_[q] in {J_[x] for x in hold}:
                e_dup += 1
            if J_[q] in sold:
                e_same += 1
            slot = (eq_s[t - 1] if t > 0 else 1.0) / 10
            av = cash if mode == "cash" else units * Bo[t] * (1 - SELL)
            e_amt = max(e_amt, abs(min(slot, av) / amt[q] - 1))
            if mode == "cash":
                cash -= amt[q]
            else:
                units -= amt[q] / ((1 - SELL) * Bo[t])
            hold[q] = True
            if len(hold) > 10:
                e_over += 1
        if t in chk_t:                            # 少買 ⇒ 必須是撥款用盡（買完後可撥 ≤ 1e−9；K2 當天賣出現金不撥當天）
            av_end = cash if mode == "cash" else units * Bo[t] * (1 - SELL)
            if chk_t[t][1] < chk_t[t][0] and av_end <= 1e-9:
                starve += 1
            else:
                miss += 1; miss_ex.append((str(W["cal"][t].date()),) + chk_t[t] + (av_end,))
        for q in sells_by.get(t, []):
            if q in hold and int(df.at[q, "買進日pos"]) == t:
                p_ = amt[q] * (1 + Rr[q] - COST); pend += p_; e_proc = max(e_proc, abs(p_ / proc[q] - 1))
                del hold[q]
        hv = sum(amt[q] * CM[J_[q], t] / ep[q] for q in hold)
        nav[t] = (cash if mode == "cash" else units * Bc[t]) + pend + hv; nh[t] = len(hold)
    d = float(np.max(np.abs(nav / eq_s - 1)))
    out = {"淨值逐日最大相對差": d, "持股數逐日不同天數": int((nh != nh_s).sum()), "金額式最大相對差": e_amt, "入帳式最大相對差": e_proc,
           "同檔重複持有": e_dup, "當天賣出又買": e_same, "超過10檔": e_over, "筆數": int(len(df))}
    if ev is not None:
        out["買進數≠min(空槽,可買候選)且非撥款用盡的日子"] = miss; out["例"] = miss_ex[:3]
        out["撥款用盡而少買的日子(K2)"] = starve
    log(f"[C2 {W['name']} {arm}] {out}")
    return out, nav


def detail(W, CM, Bc, Bo, df, Z, arm, days, log):
    for t in days:
        h = df[(df["買進日pos"] <= t) & ((df["排程出場pos"] > t) | (df["排程出場pos"] < 0))]
        rows = [(s, round(float(a * CM[W["ix"][s], t] / e), 6)) for s, a, e in zip(h["sid"], h["金額"], h["市值基準價"])]
        log(f"  [明細 {W['name']} {arm} {W['cal'][t].date()}] 持股 {len(rows)}：{rows}｜個股市值 {Z[f'{arm}_hv'][t]:.6f}｜0050 {Z[f'{arm}_u'][t]:.6f}｜待買回 {Z[f'{arm}_pend'][t]:.6f}｜淨值 {Z[f'{arm}_eq'][t]:.6f}")


def c6_job(a):
    wn, sid, days = a
    W = _G[wn]
    try:
        B, idx, o, h, l, c, bad = bars(W, sid)
    except Exception:
        return sid, {}
    if B is None:
        return sid, {}
    gate = np.asarray(P.Frame(B["df"], set()).gate, bool); PV = W["PV"][W["ix"][sid]]
    out = {}
    for t in days:
        k = int(np.searchsorted(idx, t - 1))
        if k >= len(idx) or idx[k] != t - 1 or k < 54:
            continue
        if bad[k - 53:k + 1].any():
            continue
        lv = max(h[k - 54:k + 1])
        if c[k] >= 0.97 * lv and gate[t - 1] and PV[t - 1]:
            out[t] = 1
    return sid, out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    log = RA.log_to(os.path.join(OUT, "check.log")); T0 = time.time()
    J = {"時間": M.now_tpe()}
    TB = pd.read_csv(os.path.join(OUT, "TurtleS2PF_main.csv"), encoding="utf-8-sig")
    rng = np.random.default_rng(20261018)
    allok = True
    for wn in ("主", "早年"):
        W = AS.load_world(wn, log); cal = W["cal"]; n0 = W["n0"]; _G[wn] = W
        CM = pd.DataFrame(np.asarray(W["C"], float)).ffill(axis=1).to_numpy(float)
        Z = np.load(os.path.join(OUT, f"eq_{wn}.npz"))
        Bc, Bo = Z["Bc"], Z["Bo"]
        # C3
        D.DATA = W["data"]; st = D.load_stock("0050", "twse", cal).df
        bc = pd.Series(st["close"].to_numpy(float)).ffill().to_numpy(); bo = st["open"].to_numpy(float).copy()
        miss = ~(np.isfinite(bo) & (bo > 0)); bo[miss] = np.r_[bc[0], bc[:-1]][miss]
        c3 = {"Bc 最大差": float(np.max(np.abs(bc - Bc))), "Bo 最大差": float(np.max(np.abs(bo - Bo))), "開盤缺補": int(miss.sum())}
        log(f"[C3 {wn}] {c3}"); J[f"C3_{wn}"] = c3
        allok &= c3["Bc 最大差"] == 0 and c3["Bo 最大差"] == 0
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)   # 全讀字串、用 Python float() 精確還原
        # C1
        J[f"C1_{wn}"] = c1(W, ev, rng, 60 if wn == "主" else 40, log); allok &= J[f"C1_{wn}"]["不同"] == 0
        # C2
        evf = ev.copy()
        for arm in M.ARMS:
            df = pd.read_csv(os.path.join(OUT, f"trades_{wn}_{arm}.csv.gz"), dtype={"sid": str}, keep_default_na=False)
            for col in ("金額", "市值基準價", "R", "入帳"):
                df[col] = pd.to_numeric(df[col].replace("", np.nan))
            o, nav = c2(W, CM, Bc, Bo, df, Z, arm, evf if arm in ("M", "Mslip") else None, log)
            J[f"C2_{wn}_{arm}"] = o
            allok &= (o["淨值逐日最大相對差"] < 1e-9 and o["持股數逐日不同天數"] == 0 and o["金額式最大相對差"] < 1e-9 and o["入帳式最大相對差"] < 1e-9
                      and o["同檔重複持有"] == 0 and o["當天賣出又買"] == 0 and o["超過10檔"] == 0 and o.get("買進數≠min(空槽,可買候選)且非撥款用盡的日子", 0) == 0)
            if arm == "M":
                days = sorted(rng.choice(np.arange(300, n0), 5, replace=False).tolist())
                detail(W, CM, Bc, Bo, df, Z, arm, days, log)
            if arm == "Mslip":                    # C4
                evk = {(s, t): (float(p), float(x) if x != "" else np.nan) for s, t, p, x in zip(ev["sid"], ev["T"], ev["買價"], ev["賣價"])}
                e1 = e2 = 0.0; nn = 0
                for s, t, epx, rr in zip(df["sid"], df["T"], df["市值基準價"], df["R"]):
                    p, x = evk[(s, t)]; nn += 1
                    e1 = max(e1, abs(epx / (p * 1.005) - 1))
                    if np.isfinite(x):
                        e2 = max(e2, abs((1 + rr) / (x * 0.995 / (p * 1.005)) - 1))
                dm = pd.read_csv(os.path.join(OUT, f"trades_{wn}_M.csv.gz"), dtype={"sid": str}, keep_default_na=False)
                same = set(zip(dm["sid"], dm["買進日"])) == set(zip(df["sid"], df["買進日"]))
                J[f"C4_{wn}"] = {"筆": nn, "買價×1.005 最大相對差": e1, "滑價R 最大相對差": e2, "與主判買進完全相同（只報）": bool(same)}
                log(f"[C4 {wn}] {J[f'C4_{wn}']}"); allok &= e1 < 1e-12 and e2 < 1e-12
        # C5
        bad5 = []
        for _, r in TB[TB["世界"] == wn].iterrows():
            x, y = W["segp"][r["段"]]
            eq = Z[f"{r['臂']}_eq"][x:y + 1]; b = Bc[x:y + 1]
            yrs = len(eq) / 245
            cg = (eq[-1] / eq[0]) ** (1 / yrs) - 1; md = float(np.min(eq / np.maximum.accumulate(eq) - 1))
            bg = (b[-1] / b[0]) ** (1 / yrs) - 1; bm = float(np.min(b / np.maximum.accumulate(b) - 1))
            lab = "合格" if (cg > bg and cg / abs(md) >= bg / abs(bm)) else ("另列" if cg > bg else "不合格")
            if not (abs(cg - r["年化"]) < 1e-5 and abs(md - r["回落"]) < 1e-5 and abs(bg - r["0050年化"]) < 1e-5 and lab == r["標籤"]):
                bad5.append((r["臂"], r["段"], cg, r["年化"], md, r["回落"], lab, r["標籤"]))
        J[f"C5_{wn}"] = {"列": int((TB["世界"] == wn).sum()), "不同": len(bad5), "例": [str(b) for b in bad5[:3]]}
        log(f"[C5 {wn}] {J[f'C5_{wn}']}"); allok &= not bad5
        # C6
        bur = pd.read_csv(os.path.join(OUT, f"burden_{wn}.csv.gz"))
        x0, y0 = list(W["segp"].values())[0][0], list(W["segp"].values())[-1][1]
        days = sorted(rng.choice(np.arange(x0, y0 + 1), 8, replace=False).tolist())
        cnt = {t: 0 for t in days}
        with Pool(a.procs) as pool:
            for sid, o in pool.imap_unordered(c6_job, [(wn, s, days) for s in W["sids"]], chunksize=16):
                for t in o:
                    cnt[t] += 1
        diff = {str(cal[t].date()): (cnt[t], int(bur["候選檔數"].iloc[t])) for t in days if cnt[t] != int(bur["候選檔數"].iloc[t])}
        J[f"C6_{wn}"] = {"抽樣日": {str(cal[t].date()): cnt[t] for t in days}, "不同": diff}
        log(f"[C6 {wn}] {J[f'C6_{wn}']}"); allok &= not diff
        # C7
        rd = pd.read_csv(os.path.join(OUT, f"random_{wn}.csv.gz"))
        J[f"C7_{wn}"] = {"列": int(len(rd)), "全有限": bool(np.isfinite(rd.select_dtypes("number")).all().all())}
        log(f"[C7 {wn}] {J[f'C7_{wn}']}"); allok &= len(rd) == 200 and J[f"C7_{wn}"]["全有限"]
    J["全部通過"] = bool(allok); J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 全部通過 {allok}｜{J['耗時秒']}s")


if __name__ == "__main__":
    main()

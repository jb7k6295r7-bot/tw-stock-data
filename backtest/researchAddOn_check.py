# -*- coding: utf-8 -*-
"""researchAddOn 獨立查核（回測線計算子代理，2026-10-12）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_check

獨立寫法（⛔ 不 import researchAddOn）：
 C1 引擎權益：~/addonwork/engine_200.pkl 每條 eq 自算 sha256 前 16 碼 ＝ resultsYL_integrate/seeds.csv.gz（同世界、同格、同 r）
 C2 持股配對：audit 轉表、同股依 t 排序後「第 k 次買」配「第 k 次賣」（主程式是先進先出佇列）
 C3 R1：每日依 (−amt20, 列序) lexsort 取前 ⌈X×檔數⌉；X 自算；壞根窗改用「最後一個壞根位置 ≤ t」矩陣判（主程式是累計和差）；
    門檻只算用得到的 (h, t)：逐一抽母體向量 np.percentile（主程式是整列 nanpercentile）
 C4 觸發：逐持股逐日迴圈 ⇒ 與 triggers.csv.gz 比（有無、t、ta 相同；g、q 差 ≤ 1e−9）
 C5 主臂記帳：逐日事件迴圈（開倉字典）重算讀法 A、B、C 的 NAV，自寫年化／回落（(b−a)/245 年、逐日最高）⇒ 與 seeds.csv.gz 主臂列比（差 ≤ 1e−9）
    營量 r0 全格全段；營飆 200 顆全格全段
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))

OUT = "backtest/resultsAddOn"
WORK = os.path.expanduser("~/addonwork")
V2EXT = os.path.expanduser("~/earlydata/950ad26e12/reduce_ext_b45c9e94dc")
KEYS = {"營量": "H60·S20·無·relvol", "營飆": "H120·S10·閘·抽籤"}
HOF = {"營量": 60, "營飆": 120}
PCT = {"A1": 95.0, "A2": 99.0}
SEGN = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
COST = 0.00585
TOL = 1e-9


def P(*a):
    print(*a, flush=True)


def sha16(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def wstats(nav):
    """[a, b) 的段：年化（(b−a)/245 年）與最大回落。"""
    if len(nav) < 245:
        return np.nan, np.nan
    yrs = len(nav) / 245
    c = (nav[-1] / nav[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(nav)
    return c, float(((nav - pk) / pk).min())


def main():
    T0 = time.time()
    from backtest import research11 as R
    assert abs(R.COST - COST) < 1e-15, R.COST
    WS = {wn: pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
    ENG = pickle.load(open(os.path.join(WORK, "engine_200.pkl"), "rb"))
    res = {}
    # C1
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    res["C1 eq_sha 不同條數"] = int(sum(sha16(v["eq"]) != REF[(wn, KEYS[sn], r)] for (wn, sn, r), v in ENG.items()))
    res["C1 條數"] = len(ENG)
    P("C1", res["C1 eq_sha 不同條數"], len(ENG))
    # C2 持股
    HOLD = {}
    for key, v in ENG.items():
        A = pd.DataFrame(v["au"], columns=["t", "side", "sid", "amt", "cost", "px"])
        A["k"] = A.groupby(["sid", "side"]).cumcount()
        b = A[A["side"] == "buy"].set_index(["sid", "k"]); s = A[A["side"] == "sell"].set_index(["sid", "k"])
        M = b.join(s[["t", "px"]], rsuffix="_s", how="left").reset_index()
        HOLD[key] = M[["sid", "t", "amt", "px", "t_s", "px_s"]].sort_values(["t", "sid"]).reset_index(drop=True)
    # C3 母體
    TRG = pd.read_csv(os.path.join(OUT, "triggers.csv.gz"), dtype={"sid": str})
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"))
    X = None
    trig_bad = 0; trig_n = 0; gq_max = 0.0
    acc_max = 0.0; acc_n = 0; orig_max = 0.0
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n = len(cal); NP = W["NP"]
        Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{'main' if wn == '主' else 'early'}.pkl"), "rb"))
        sids = Z["sids"]; ix = {s: i for i, s in enumerate(sids)}
        C = Z["c"]; BAR = Z["bar"]; A20 = Z["a20"]; MKT = BAR & Z["pv"] & np.isfinite(A20)
        S = len(sids)
        Bk = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{'main' if wn == '主' else 'early'}.pkl"), "rb"))
        BAD = np.zeros((S, n), bool)
        for s, (a_, b_) in Bk.items():
            if s in ix:
                BAD[ix[s], np.r_[a_, b_].astype(int)] = True
        extra = {}
        if wn == "早年":
            cv = cal.values

            def pos(d):
                k = int(np.searchsorted(cv, np.datetime64(pd.Timestamp(d))))
                return k if k < n else None
            EV = W["EV"]
            lst = list(zip(EV["stock_id"], EV["e"]))
            t_ = pd.read_csv(os.path.join(V2EXT, "twse_reduce_detected_2004_2010.csv"), dtype=str, keep_default_na=False); lst += list(zip(t_["stock_id"], t_["date"]))
            o_ = pd.read_csv(os.path.join(V2EXT, "otc_reduce_detected_2007_2012.csv"), dtype=str, keep_default_na=False)
            o_ = o_[(o_["shares_down"].str.strip() == "1") & (o_["exright_in_gap"].str.strip() == "0")]; lst += list(zip(o_["stock_id"], o_["resume_day"]))
            u_ = pd.read_csv(os.path.join(V2EXT, "twse_jump_unexplained_2004_2010.csv"), dtype=str, keep_default_na=False); lst += list(zip(u_["stock_id"], u_["date"]))
            for s, d in lst:
                s = str(s).strip(); d = str(d).strip()
                if not d:
                    continue
                k = pos(d)
                if k is None:
                    continue
                extra.setdefault(s, set()).add(k)
                if s in ix:
                    BAD[ix[s], k] = True
        if X is None:
            d = int(np.flatnonzero(cal == pd.Timestamp("2016-01-04"))[0])
            X = int((MKT[:, d] & (A20[:, d] >= 5e7)).sum()) / int(MKT[:, d].sum())
            res["C3 X"] = X
        R1 = np.zeros((S, n), bool)
        rows = np.arange(S)
        for d in range(n):
            m = MKT[:, d]
            if not m.any():
                continue
            ii = rows[m]
            o = np.lexsort((ii, -A20[ii, d]))
            R1[ii[o[:int(np.ceil(X * len(ii)))]], d] = True
        # 最後一個壞根位置（≤ t）
        idxm = np.where(BAD, np.arange(n)[None, :], -1)
        LB = np.maximum.accumulate(idxm, axis=1)
        okC = np.isfinite(C)
        QC = {}

        def qv(h, t):
            k = (h, t)
            if k not in QC:
                if t - h < 0 or t >= n:
                    QC[k] = (np.nan, np.nan)
                else:
                    m = R1[:, t] & BAR[:, t] & okC[:, t - h] & (LB[:, t] <= t - h)
                    v = C[m, t] / C[m, t - h] - 1.0
                    QC[k] = (np.percentile(v, 95.0), np.percentile(v, 99.0)) if len(v) >= 20 else (np.nan, np.nan)
            return QC[k]
        # 持股股票的 K 棒、壞根（快取沒有 ⇒ 現場）
        from backtest import researchBARR as BARR
        from backtest import data as D
        SB = {}

        def stock(sid):
            if sid in SB:
                return SB[sid]
            if sid in ix:
                bar = BAR[ix[sid]]; lbr = LB[ix[sid]]
            else:
                D.DATA = W["data"]
                st = D.load_stock(sid, W["uni"].get(sid, "twse"), cal)
                bar = np.isfinite(st.df["close"].to_numpy(float))
                bd = BARR.bad_part(sid, W["data"], cal).copy()
                adj = D.load_adj(sid)
                if adj is not None and len(adj) and "event" in adj:
                    for dd, e in zip(adj["date"], adj["event"].astype(str)):
                        if e in ("reduce", "parvalue"):
                            k = int(cal.searchsorted(dd))
                            if k < n:
                                bd[k] = True
                for k in extra.get(sid, ()):
                    bd[k] = True
                lbr = np.maximum.accumulate(np.where(bd, np.arange(n), -1))
            barP = np.r_[bar, np.zeros(NP - n, bool)]
            lbP = np.r_[lbr, np.full(NP - n, lbr[-1])]
            SB[sid] = (barP, lbP)
            return SB[sid]
        base = W["SIG"][False]
        XP = {H: dict(zip(zip(base["sid"], base["entry_pos"].astype(int)), base[f"xpos_H{H}"].astype(int))) for H in (60, 120)}
        # C4 觸發（唯一持股）
        uniq = {}
        for (w_, sn, r), Hd in HOLD.items():
            if w_ != wn:
                continue
            for sid, tb, amt, ep, ts, pxs in Hd.itertuples(index=False):
                uniq[(sn, sid, int(tb))] = (float(ep), None if pd.isna(ts) else int(ts), None if pd.isna(pxs) else float(pxs))
        INFO = {}
        for (sn, sid, tb), (ep, ts, pxs) in uniq.items():
            cl = W["closes"][sid]; op = W["opens"][sid]
            bar, lb = stock(sid)
            xp = XP[HOF[sn]].get((sid, tb)); L = W["SF"].get(sid)
            if ts is None:
                xbar = len(cl) - 1
            elif ts == xp:
                xbar = ts
            else:
                assert L is not None and ts == L + 1 and ts < xp, (wn, sn, sid, tb, ts, xp, L)
                xbar = L
            out = {}
            for c, pc in PCT.items():
                tr = None
                for t in range(tb + 9, xbar):
                    if not bar[t]:
                        continue
                    if lb[t] > tb:                      # (tb, t] 有壞根
                        break
                    h = t - tb + 1
                    q = qv(h, t)[0 if c == "A1" else 1]
                    if not np.isfinite(q):
                        continue
                    g = float(cl[t]) / ep - 1.0
                    if g >= q:
                        if lb[t + 1] > tb:
                            break
                        o = float(op[t + 1])
                        if not (np.isfinite(o) and o > 0):
                            continue
                        tr = (t, t + 1, g, q, o); break
                out[c] = tr
            INFO[(sn, sid, tb)] = {"ep": ep, "ts": ts, "pxs": pxs, "xbar": xbar, "tr": out, "cl": cl, "bar": bar, "lb": lb}
            for c in PCT:
                m = TRG[(TRG["世界"] == wn) & (TRG["策略"] == sn) & (TRG["sid"] == sid) & (TRG["tb"] == tb) & (TRG["格"] == c)]
                trig_n += 1
                if len(m) != 1:
                    trig_bad += 1; continue
                m = m.iloc[0]; tr = out[c]
                has = isinstance(m["結果"], str) and m["結果"] == "加碼"
                if (tr is None) != (not has):
                    trig_bad += 1; continue
                if tr is not None:
                    if int(m["t"]) != tr[0] or int(m["ta"]) != tr[1]:
                        trig_bad += 1; continue
                    gq_max = max(gq_max, abs(float(m["g"]) - tr[2]), abs(float(m["q"]) - tr[3]), abs(float(m["ep_a"]) - tr[4]))
        P(f"C4 {wn}：唯一持股×格 {trig_n}｜不同 {trig_bad}｜g、q、加碼價最大差 {gq_max:.3g}｜{time.time() - T0:.0f}s")

        # C5 主臂記帳
        def addon_exit(I, ta):
            bar, lb = I["bar"], I["lb"]
            hi = I["xbar"]
            kb = None
            if lb[hi] > ta:                              # (ta, xbar] 有壞根 ⇒ 找第一個
                for k in range(ta + 1, hi + 1):
                    if lb[k] >= k and lb[k] > ta:
                        kb = k; break
            if kb is not None:
                v = ta
                for k in range(kb - 1, ta - 1, -1):
                    if bar[k]:
                        v = k; break
                return v, float(I["cl"][v])
            if I["ts"] is None:
                return None, None
            return I["ts"], I["pxs"]
        for (w_, sn, r), Hd in HOLD.items():
            if w_ != wn:
                continue
            E = ENG[(w_, sn, r)]; eq = np.asarray(E["eq"], float); first, end = E["first"], E["end"]
            for c in PCT:
                POS = []
                for sid, tb, amt, ep, ts, pxs in Hd.itertuples(index=False):
                    I = INFO[(sn, sid, int(tb))]; tr = I["tr"][c]
                    if tr is None:
                        continue
                    sd, px = addon_exit(I, tr[1])
                    POS.append((tr[1], float(amt), tr[4], sid, sd, px))
                for sg in SEGN[wn]:
                    x, y = W["segp"][sg]; a = max(x, first); yy = min(y, end - 1)
                    pos = [p for p in POS if a < p[0] <= yy]
                    byadd = {}; bysell = {}
                    for p in pos:
                        byadd.setdefault(p[0], []).append(p)
                        if p[4] is not None and p[4] <= yy:
                            bysell.setdefault(p[4], []).append(p)
                    openp = []; K = 0.0
                    navA = [eq[a]]; navC = [eq[a]]; Wprev = eq[a]; Fs = []; Wl = [eq[a]]
                    mvprev = 0.0
                    for t in range(a + 1, yy + 1):
                        F = 0.0; newA = 0.0
                        for p in byadd.get(t, []):
                            newA += p[1]
                        if newA > 0:
                            use = min(K, newA); K -= use; F = newA - use
                        openp += byadd.get(t, [])
                        proc = 0.0
                        for p in bysell.get(t, []):
                            proc += p[1] * (p[5] / p[2] - COST)
                            openp.remove(p)
                        K += proc
                        mv = sum(p[1] * float(WS[wn]["closes"][p[3]][t]) / p[2] for p in openp)
                        Wt = eq[t] + K + mv
                        navA.append(navA[-1] * Wt / (Wprev + F))
                        navC.append(navC[-1] * (1.0 + (eq[t] - eq[t - 1] + mv + proc - mvprev - newA) / (eq[t - 1] + mvprev + newA)))
                        Fs.append(F); Wl.append(Wt); Wprev = Wt; mvprev = mv
                    Itot = float(np.sum(Fs)); cum = np.r_[0.0, np.cumsum(Fs)]
                    WB = np.asarray(Wl) + (Itot - cum)
                    navB = eq[a] * WB / WB[0]
                    co, mo = wstats(eq[x:y + 1])                 # rerun17.win_metrics 的窗 ＝ [x, y]（first 之前權益 ＝ 1，照算）
                    row = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["r"] == r) & (SE["格"] == c) & (SE["段"] == sg) & (SE["臂"] == "主臂")]
                    assert len(row) == 1
                    row = row.iloc[0]
                    orig_max = max(orig_max, abs(co - row["原_年化"]), abs(mo - row["原_回落"]))
                    for rd, nav in (("A", np.asarray(navA)), ("B", navB), ("C", np.asarray(navC))):
                        cc, mm = wstats(np.r_[eq[x:a], nav])
                        acc_max = max(acc_max, abs(cc - row[f"{rd}_年化"]), abs(mm - row[f"{rd}_回落"]))
                    acc_n += 1
        P(f"C5 {wn}：路徑×格×段 {acc_n}｜三讀法年化回落最大差 {acc_max:.3g}｜原策略最大差 {orig_max:.3g}｜{time.time() - T0:.0f}s")
    res.update({"C4 唯一持股×格": trig_n, "C4 不同": trig_bad, "C4 g、q、加碼價最大差": gq_max,
                "C5 路徑×格×段": acc_n, "C5 三讀法年化回落最大差": acc_max, "C5 原策略年化回落最大差": orig_max})
    res["通過"] = bool(res["C1 eq_sha 不同條數"] == 0 and trig_bad == 0 and gq_max <= TOL and acc_max <= TOL and orig_max <= TOL)
    res["秒"] = round(time.time() - T0)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    P(json.dumps(res, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()

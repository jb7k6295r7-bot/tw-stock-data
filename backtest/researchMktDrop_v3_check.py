# -*- coding: utf-8 -*-
"""PREREG大盤大跌後買什麼 seq3 —— 獨立重算 C＋ 與買法四臂，對 researchMktDrop_v3 的輸出差 ≤ 1e−9。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_v3_check [--procs 2]

獨立寫法（⛔ 不呼叫 v1／v3／初測的事件、籃子、出場、營收、曲線函式；只共用資料層：market_index.csv、DB.load_world、R.load_bars、patterns.Frame.gate、
industry PIT、revenue_hist csv、D.load_stock、research13.window_stats（年化／回落公式））：
 K1 指數：pct_change；q(t) ＝ np.quantile(2005-01-03～t−1, 0.02) 每天重算；去重回看 20 列；鎖 while；收復逐日往後找
 K2 營收：自己讀 revenue_hist（早年＋主世界，逐格主世界優先）；可得日 ＝ 次月 10 日（≤2025-12 期）／15 日（≥2026-01 期）之後第一個交易日；
    取可得日 ≤ t、當月營收有值的期中（可得日, 期別）最大者；年增 ＝ 當月 ÷ 去年當月 − 1（去年 ≤0／缺 ⇒ 缺）
 K3 逐股 for 迴圈：母體、當天報酬、主出場賣出（壞根先、收復後第一根可賣開盤、下市／窗尾）、t＋1／t＋2／t＋3 開盤與 t 收盤的可買性與價格
    C ＝ (報酬, 代號) 排序前 ceil(10%)；C＋ ＝ C 中年增 ＞ 0；E ＝ 產業 dict 聚合；A／B 直接讀 ETF 日線
 K4 比對：v3 event_rows（q2 主出場 C＋：選出、買到、淨報酬、配對 0050）；buyarm_rows（A、B、C、C＋、E × P主／P0／P1／P2／P3：選出、可買、進場、報酬；跳空）；
    MktDrop_v3.json 主表（C＋ 兩主段＋早年：平均、中位、配對差平均、② 年化、② 回落、② 比值、一直抱 0050）與 C＋ 判語（自算 ② 曲線）
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO); os.chdir(REPO)
V3 = os.path.join(REPO, "backtest/resultsMktDrop/v3")
TOL = 1e-9
CS, CE_ = 0.00585, 0.00385
_G: dict = {}


def chk(name, ok, info=""):
    print(("✔ " if ok else "✘ ") + name + (f"｜{info}" if info else ""), flush=True)
    if not ok:
        _G.setdefault("fail", []).append(name)
    return ok


def index_events(sha):
    raw = subprocess.run(["git", "show", f"{sha}:data/history/market_index.csv"], capture_output=True, check=True).stdout
    df = pd.read_csv(io.BytesIO(raw), dtype={"date": str})
    df["date"] = pd.to_datetime(df["date"]); df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    r = df["close"].pct_change().to_numpy(); cl = df["close"].to_numpy(float); n = len(df); dates = df["date"].to_numpy()
    w0 = int(np.searchsorted(dates, np.datetime64("2005-01-03")))
    q = np.full(n, np.nan)
    for t in range(w0, n):
        win = r[w0:t]; win = win[~np.isnan(win)]
        if len(win) >= 250:
            q[t] = np.quantile(win, 0.02)
    raw_ev = np.array([(not np.isnan(q[t])) and r[t] <= q[t] for t in range(n)])
    first = [t for t in range(n) if raw_ev[t] and not raw_ev[max(0, t - 20):t].any()]
    rec = {}
    for t in first:
        rec[t] = next((j for j in range(t + 1, n) if cl[j] >= cl[t - 1]), -1)
    acc = []; until = -1
    for t in first:
        if t > until:
            acc.append(t); until = rec[t] if rec[t] >= 0 else n + 1
    return dates, acc, rec


def load_rev():
    from backtest import researchDumb as DB
    out = {}
    for wn in ("主", "早年"):                     # 主世界先 ⇒ 逐格優先
        fs = sorted(glob.glob(os.path.join(DB.WORLDS[wn]["data"], "mops", "revenue_hist", "*.csv")))
        for f in fs:
            d = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
            for s, p, a, b in zip(d["stock_id"], d["period"], pd.to_numeric(d["當月營收"], errors="coerce"), pd.to_numeric(d["去年當月營收"], errors="coerce")):
                key = (s, p)
                cur = out.setdefault(wn, {})
                cur[key] = (a, b)                 # 同世界內後檔覆蓋（同 drop_duplicates keep last）
    REV = {}
    for key in set(out.get("主", {})) | set(out.get("早年", {})):
        am, bm = out.get("主", {}).get(key, (np.nan, np.nan)); ae, be = out.get("早年", {}).get(key, (np.nan, np.nan))
        a = am if np.isfinite(am) else ae; b = bm if np.isfinite(bm) else be
        REV.setdefault(key[0], []).append((key[1], a, b))
    return REV


def yoy_at(REV, sid, cal, p):
    best = None
    for per, a, b in REV.get(sid, []):
        if not np.isfinite(a):
            continue
        y, m = int(per[:4]), int(per[5:])
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        day = pd.Timestamp(year=y2, month=m2, day=10 if per <= "2025-12" else 15)
        av = int(np.searchsorted(cal.values, np.datetime64(day), side="right"))
        if av <= p and (best is None or (av, per) > best[0]):
            best = ((av, per), (a / b - 1.0) if (np.isfinite(b) and b > 0) else np.nan)
    return np.nan if best is None else best[1]


def stock_events(args):
    wn, sid = args
    from backtest import data as D, research11 as R, patterns as P
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = [int(x) for x in B["idx"]]; nb = len(idx)
    o = np.asarray(B["o"], float); c = np.asarray(B["c"], float); nbad = np.asarray(B["next_bad"]); up = np.asarray(B["up"], bool)
    gate = np.asarray(P.Frame(B["df"], set()).gate, bool)
    bad = [bool(nbad[k] == k) for k in range(nb)]
    for pz in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, pz))
        if k < nb:
            bad[k] = True
    pos2k = {p: k for k, p in enumerate(idx)}
    TRD, O, UPL, DNL = W["TRD"][i], W["O"][i], W["UPL"][i], W["DNL"][i]

    def can_open(q):
        return bool(q < n0 and TRD[q] and np.isfinite(O[q]) and O[q] > 0)
    out = {}
    for p, Dp in W["EVP"]:
        k = pos2k.get(p)
        if k is None:
            continue
        mem = bool(gate[idx[k]] and W["PV"][i, p] and k >= 20 and not any(bad[k - 20:k + 1]))
        ret = c[k] / c[k - 1] - 1.0 if k >= 1 else np.nan
        sale = None
        if k + 1 < nb:
            for j in range(k + 2, nb):
                if bad[j]:
                    sale = (idx[j - 1], float(c[j - 1]), 1); break
                if idx[j] > Dp and can_open(idx[j]) and not DNL[idx[j]]:
                    sale = (idx[j], float(o[j]), 0); break
            if sale is None:
                sale = (n0 - 1, float(c[-1]), 3) if idx[-1] == n0 - 1 else (idx[-1], float(c[-1]), 2)
        legs = {}
        legs["P主"] = (2 * (p + 1), float(o[k + 1])) if (k + 1 < nb and idx[k + 1] == p + 1 and can_open(p + 1) and not UPL[p + 1] and not bad[k + 1]) else None
        legs["P0"] = (2 * p + 1, float(c[k])) if (k + 1 < nb and not bad[k + 1] and not up[k] and c[k] > 0) else None
        for a_, j in (("P1", 2), ("P2", 3)):
            qd = p + j; kb = pos2k.get(qd)
            ok = kb is not None and can_open(qd) and not UPL[qd] and not any(bad[k + 1:kb + 1])
            legs[a_] = (2 * qd, float(o[kb])) if ok else None
        gap = float(o[k + 1] / c[k] - 1.0) if legs["P主"] is not None else None
        out[p] = {"mem": mem, "ret": ret, "sale": sale, "legs": legs, "gap": gap}
    return sid, out


def etf_events(df, EVP, n0):
    tr = df["traded"].to_numpy(bool); o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    bars = np.flatnonzero(tr); out = {}
    for p, Dp in EVP:
        if not tr[p]:
            continue
        later = bars[bars > p]
        sale = None
        for q_ in later[1:] if len(later) else []:
            if q_ > Dp and np.isfinite(o[q_]) and o[q_] > 0:
                sale = (int(q_), float(o[q_]), 0); break
        if not len(later):
            continue
        if sale is None:
            sale = (n0 - 1, float(c[bars[-1]]), 3) if bars[-1] == n0 - 1 else (int(bars[-1]), float(c[bars[-1]]), 2)
        legs = {"P主": (2 * (p + 1), float(o[p + 1])) if (p + 1 < n0 and tr[p + 1] and np.isfinite(o[p + 1]) and o[p + 1] > 0) else None,
                "P0": (2 * p + 1, float(c[p])) if (np.isfinite(c[p]) and c[p] > 0) else None}
        for a_, j in (("P1", 2), ("P2", 3)):
            qd = p + j
            legs[a_] = (2 * qd, float(o[qd])) if (qd < n0 and tr[qd] and np.isfinite(o[qd]) and o[qd] > 0) else None
        gap = float(o[p + 1] / c[p] - 1.0) if legs["P主"] is not None else None
        out[p] = {"sale": sale, "legs": legs, "gap": gap}
    return out


def wrap(a):
    return stock_events(a)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    S3 = json.load(open(os.path.join(V3, "MktDrop_v3.json"), encoding="utf-8"))
    sha = S3["指數"]["origin/main sha"]
    dates, acc, rec = index_events(sha)
    from backtest import researchDumb as DB, data as D, research13 as R13, universe_gate as UG
    from backtest import researchIndRev_prereg as PRE
    UG.set_gate_v2(True)
    DB.SEGS = {"早年": {"2006～2014": ("2006-01-01", "2014-12-31")}, "主": {"2015～2021": ("2015-01-01", "2021-12-31"), "2022～": ("2022-01-01", None)}}
    IND_DATA = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
    PIT = PRE.PIT(IND_DATA, PRE.load_rev(IND_DATA)[2])
    REV = load_rev()
    print(f"[營收] {len(REV)} 檔", flush=True)
    ER = pd.read_csv(os.path.join(V3, "event_rows.csv"), dtype={"日期": str})
    ER = ER[(ER["定義"] == "q2") & (ER["出場"] == "主") & (ER["候選"] == "C+")]
    AR = pd.read_csv(os.path.join(V3, "buyarm_rows.csv"), dtype={"日期": str})
    MT = {(r["候選"], r["段"]): r for r in S3["主表"]}
    mism = []; misa = []; worst = 0.0; ncmp = 0; nar = 0
    CPV = {}                                                   # 段 ⇒ C＋ 事件 (淨, 配對 0050)
    for wn in ("早年", "主"):
        W = DB.load_world(wn, lambda m: None); _G[wn] = W
        cal = W["cal"]; n0 = W["n0"]; cset = set(cal)
        lo, hi = W["segp"][list(W["segp"])[0]][0], W["segp"][list(W["segp"])[-1]][1]
        EVP = []
        for t in acc:
            d = pd.Timestamp(dates[t])
            if d not in cset:
                continue
            p = int(cal.get_loc(d))
            if not (lo <= p <= hi and p + 1 < n0):
                continue
            EVP.append((p, int(cal.searchsorted(pd.Timestamp(dates[rec[t]]))) if rec[t] >= 0 else 10 ** 9))
        W["EVP"] = EVP
        with Pool(a.procs) as pool:
            RES = dict(pool.imap_unordered(wrap, [(wn, s) for s in W["sids"]], chunksize=8))
        RES = {k: v for k, v in RES.items() if v is not None}
        D.DATA = W["data"]
        etf = {s: D.load_stock(s, "twse", cal) for s in ("0050", "00631L")}
        BC = pd.Series(etf["0050"].df["close"].to_numpy(float)).ffill().to_numpy()
        BOr = etf["0050"].df["open"].to_numpy(float)
        BO = np.array([BOr[j] if np.isfinite(BOr[j]) and BOr[j] > 0 else (BC[j - 1] if j else np.nan) for j in range(n0)])
        ETF = {s: etf_events(etf[s].df, EVP, n0) for s in ("0050", "00631L") if etf[s] is not None}
        Cmat = np.asarray(W["C"], float)
        sleeves = []                                           # C＋ ② 用：(e, end, V, 最後一批是否開盤賣)
        for p, Dp in EVP:
            day = str(cal[p].date())
            sg = next(s for s, (x0, y0) in W["segp"].items() if x0 <= p <= y0)
            pop = sorted([(v[p]["ret"], s) for s, v in RES.items() if p in v and v[p]["mem"] and np.isfinite(v[p]["ret"])])
            if len(pop) >= 20:
                m_ = math.ceil(len(pop) * 0.1)
                selC = [s for _, s in pop[:m_]]
                selCp = [s for s in selC if (lambda y: np.isfinite(y) and y > 0)(yoy_at(REV, s, cal, p))]
                grp = {}
                for rv, s in pop:
                    ind = PIT._at(s, cal[p], "pit")[0]
                    if ind is None or ind in ("其他", "存託憑證", "ETF"):
                        continue
                    grp.setdefault(ind, []).append((s, rv))
                gm = sorted([(sum(x[1] for x in v) / len(v), g) for g, v in grp.items() if len(v) >= 5])
                selE = [s for _, g in gm[:2] for s, _ in grp[g]] if len(gm) >= 2 else []
            else:
                selC = selCp = selE = []
            # ── C＋ 主出場事件層 ──
            rows = [(s, RES[s][p]["legs"]["P主"][1], RES[s][p]["sale"]) for s in selCp if RES[s][p]["legs"]["P主"] is not None]
            v3 = ER[(ER["世界"] == wn) & (ER["日期"] == day)]
            if len(v3) != 1:
                mism.append((wn, day, "C+ v3 列數", len(v3)))
            else:
                v3 = v3.iloc[0]
                if int(v3["選出檔數"]) != len(selCp) or int(v3["買到檔數"]) != len(rows):
                    mism.append((wn, day, "C+ 檔數", (len(selCp), len(rows)), (int(v3["選出檔數"]), int(v3["買到檔數"]))))
                elif rows:
                    g = sum(sx / bp - 1 for _, bp, (sp, sx, kd) in rows) / len(rows); net = (1 + g) * (1 - CS) - 1
                    b = sum((BO[sp] if kd == 0 else BC[sp]) / BO[p + 1] - 1 for _, bp, (sp, sx, kd) in rows) / len(rows); b50 = (1 + b) * (1 - CE_) - 1
                    d1 = abs(net - v3["報酬"]); d2 = abs(b50 - v3["配對0050"]); worst = max(worst, d1, d2); ncmp += 1
                    if d1 > TOL or d2 > TOL:
                        mism.append((wn, day, "C+ 報酬", net, float(v3["報酬"]), b50, float(v3["配對0050"])))
                    CPV.setdefault(sg, []).append((net, b50))
                    # ② 籃子路徑（自算）：已賣的檔固定在賣價
                    e = p + 1; end = min(max(max(sp for _, _, (sp, _, _) in rows), e), n0 - 1)
                    V = []
                    for tt in range(e, end + 1):
                        vals = [(sx / bp) if tt >= sp else Cmat[W["ix"][s], tt] / bp for s, bp, (sp, sx, kd) in rows]
                        vals = [v for v in vals if np.isfinite(v)]
                        V.append(sum(vals) / len(vals))
                    spmax = max(sp for _, _, (sp, _, _) in rows)
                    reopen = all(kd == 0 for _, _, (sp, _, kd) in rows if sp == spmax)
                    sleeves.append((e, end, V, reopen))
            # ── 買法四臂 ──
            for cd, sel in (("A", ["0050"]), ("B", ["00631L"]), ("C", selC), ("C+", selCp), ("E", selE)):
                if cd == "B" and wn == "早年":
                    continue
                cost = CE_ if cd in ("A", "B") else CS
                info = {}
                for s in sel:
                    x = (ETF[s].get(p) if cd in ("A", "B") else RES[s].get(p))
                    if x is None or x["sale"] is None:
                        continue
                    info[s] = x
                res = {}
                for arm in ("P主", "P0", "P1", "P2"):
                    feas = 0; gs = []
                    for s, x in info.items():
                        lg = x["legs"][arm]
                        if lg is None:
                            continue
                        feas += 1
                        sp, sx, kd = x["sale"]; ts = 2 * sp + (0 if kd == 0 else 1)
                        if ts > lg[0]:
                            gs.append(sx / lg[1] - 1)
                    res[arm] = (len(sel), feas, len(gs), ((1 + sum(gs) / len(gs)) * (1 - cost) - 1) if gs else None)
                hm = res["P主"][3] if res["P主"][3] is not None else 0.0; h1 = res["P1"][3] if res["P1"][3] is not None else 0.0
                p3 = (0.5 * hm + 0.5 * h1) if (res["P主"][3] is not None or res["P1"][3] is not None) else None
                res["P3"] = (len(sel), None, res["P主"][2] + res["P1"][2], p3)
                gl = [x["gap"] for x in info.values() if x["gap"] is not None]
                gap = sum(gl) / len(gl) if gl else None
                for arm, (ns, nf, ne, rv) in res.items():
                    q = AR[(AR["世界"] == wn) & (AR["日期"] == day) & (AR["候選"] == cd) & (AR["買法"] == arm)]
                    if len(q) != 1:
                        misa.append((wn, day, cd, arm, "v3 列數", len(q))); continue
                    q = q.iloc[0]; nar += 1
                    bad_ = int(q["選出檔數"]) != ns or int(q["進場檔數"]) != ne or (nf is not None and int(q["可買檔數"]) != nf)
                    if (rv is None) != (not bool(q["進場"])):
                        bad_ = True
                    elif rv is not None:
                        worst = max(worst, abs(rv - q["報酬"])); bad_ = bad_ or abs(rv - q["報酬"]) > TOL
                    gq = q["跳空（t＋1開÷t收−1，P主可買檔平均）"]
                    if (gap is None) != (not np.isfinite(gq)) or (gap is not None and abs(gap - gq) > TOL):
                        bad_ = True
                    elif gap is not None:
                        worst = max(worst, abs(gap - gq))
                    if bad_:
                        misa.append((wn, day, cd, arm, (ns, nf, ne, rv, gap), (q["選出檔數"], q["可買檔數"], q["進場檔數"], q["報酬"], gq)))
        # ── C＋ ②（自算曲線：平時 0050；事件 t＋1 開盤換 20%；全籃賣完換回）──
        hold = BC / BC[0]
        eq = np.ones(n0); core = 1.0; act = None; byE = {s_[0]: s_ for s_ in sleeves}
        for j in range(1, n0):
            op = BO[j]
            core = core * op / BC[j - 1]
            if j in byE and act is None:
                e0, end, V, ro = byE[j]
                act = [e0, end, V, ro, core * 0.2 * (1 - CS) * (1 - CE_)]; core *= 0.8
            sv = 0.0
            if act is not None and j == act[1] and act[3]:
                core += act[4] * act[2][j - act[0]]; act = None
            core = core * BC[j] / op
            if act is not None:
                if j == act[1]:
                    core += act[4] * act[2][j - act[0]]; act = None
                else:
                    sv = act[4] * act[2][j - act[0]]
            eq[j] = core + sv
        for sg, (x0, y0) in W["segp"].items():
            c2, m2 = R13.window_stats(eq, 0, n0, x0, y0 + 1); ch, mh = R13.window_stats(hold, 0, n0, x0, y0 + 1)
            v = np.array(CPV.get(sg, []))
            mine = {"平均報酬": v[:, 0].mean(), "中位報酬": float(np.median(v[:, 0])), "配對差平均": (v[:, 0] - v[:, 1]).mean(),
                    "②平時0050換20%_年化": c2, "②最大回落": m2, "②比值": c2 / abs(m2), "一直抱0050_年化": ch, "一直抱0050_最大回落": mh,
                    "②年化減0050": c2 - ch, "②比值減0050": c2 / abs(m2) - ch / abs(mh)}
            ref = MT[("C+", sg)]
            dd = max(abs(mine[k_] - ref[k_]) for k_ in mine)
            worst = max(worst, dd)
            chk(f"K4 C＋ {sg} 段彙總＋②（自算曲線）≤1e−9", dd <= TOL, f"最大差 {dd:.2e}｜平均 {mine['平均報酬']:.6f} 配對差 {mine['配對差平均']:+.6f} ②年化差 {mine['②年化減0050']:+.6f} ②比值差 {mine['②比值減0050']:+.6f}")
            _G.setdefault("seg", {})[sg] = mine
        print(f"[{wn}] 事件 {len(EVP)}｜股 {len(RES)}", flush=True)
    chk("K4 C＋ 事件層（選出／買到檔數、淨報酬、配對 0050）全對 ≤1e−9", not mism, f"比對 {ncmp} 事件" + (f"｜不符 {mism[:6]}" if mism else ""))
    chk("K4 買法四臂（A、B、C、C＋、E × 5 臂：檔數、進場、報酬、跳空）全對 ≤1e−9", not misa, f"比對 {nar} 列" + (f"｜不符 {misa[:6]}" if misa else ""))
    sgv = _G["seg"]
    ok_dir = all(sgv[s]["配對差平均"] > 0 and sgv[s]["②年化減0050"] >= 0 and sgv[s]["②比值減0050"] >= 0 for s in ("2015～2021", "2022～"))
    v3v = S3["方向判語"]["C+"]["判語"]
    chk("K4 C＋ 判語（自算）＝ v3", ("方向一致（暫定）" if ok_dir else "方向不一致") == v3v, f"自算 {'方向一致（暫定）' if ok_dir else '方向不一致'}／v3 {v3v}")
    print(f"最大差 {worst:.2e}")
    print("全部通過" if not _G.get("fail") else f"⛔ 未通過：{_G['fail']}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""型態補條件 B 組 seq1 事件層 獨立查核（⛔ 不 import researchPatB、researchPatB_freq 任何一行；
只 import 資料層：researchAscTri_freq.load_world（世界、pit_valid、T＋1 旗標、壞根來源）、research11.load_bars（有效 K 棒、壞根）。
本體跑完後：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatB_check [--sample 20] [--sample_alt 10]

K1 從逐筆檔 events/events_<世界>_<段>_<格>_H<H>.csv.gz 重算主表每一列：X ＝ R − 對照平均、n、d×X̄、中位、勝率、最差；
   CR0 分群 SE（自己寫）、95% CI、Bonferroni（z 用二分法解 erfc(z/√2)＝0.05／2）、n_eff、出口、結果 ⇒ 與 PatB_main.csv 逐列比（≤ 1e−9、標籤同）；
   逐筆列數 ＝ 頻率表 freq.csv「去重後n(保留)」。
K2 假訊號臂：由 fake_acc.npz 逐群 (n, Σ) 自己重算 30 次 × 兩版 ⇒ x／30 與 PatB_main.csv 比。
K3 確認版 − 原版（PatB_compare.csv）、描述格（只配 r10、未配對、上市／上櫃：PatB_desc.csv）、先驗③（PatB_alt.csv：X_alt、X_day、X_rest、
   確認版同批、占比與其線性化 CI）從逐筆檔自己重算 ⇒ 比（≤ 1e−9）。
K4 抽 --sample 筆（主、早年各半；種子 20261017）：全市場逐檔獨立重建 K 棒對照組——k ＝ 3（B1、B2）／2（K25、K56）；
   b ＝ T 那根有效 K 棒；r10_k ＝ c[b−k]／c[b−k−10] − 1、期間報酬_k ＝ c[b]／c[b−k] − 1；十分位 ＝ pd.qcut(rank(first), 10)
   （橫斷面 ＝ T 當天 pit_valid ∧ 有效 ∧ 兩量可算）；原始偵測取頻率表已提交事件檔（任何狀態）；r10_k ＜ 0；T＋1 可成交（世界旗標）；
   硬斷點逐日掃 [自己的第 b−k＋1 根, T＋H]（⛔ 不用累加和）；R ＝ ≤ T＋H 最後有效收盤 ÷ T＋1 開盤 − 1 ⇒ 與逐筆檔的 R、對照平均、對照數、
   只配 r10 對照平均／對照數比。
K4b 抽 --sample_alt 筆先驗③ 事件：在 T2 用 k ＝ 2、原版原始偵測、H＋1 與確認日報酬重建 ⇒ 與 alt 逐筆檔的 R_alt、對照_alt、R_day、對照_day、對照數比。
K5 原版 K25、K56 對 PREREG型態全量 既有結果（resultsPatAll/body/events_K25、K56、cells.csv；同一快照 edc6f8002f）：
   兩邊都有的 (sid, T) 逐筆比 R（應逐位元同）；對照平均不同屬母體差（PatAll ＝ 靜態 gate3 v1、本件 ＝ pit_valid GATE_V2、斷點來源不同）
   ⇒ 報差的分佈、相關與 d×X̄（同窗）、結果標籤，⛔ 不算差異。
結果寫 resultsPatB/check.json。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT      # noqa: E402  資料層（世界）
from backtest import research11 as R11              # noqa: E402  只用 load_bars
from backtest import universe_gate as UG            # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsPatB"
FREQ = "backtest/resultsPatB/freq"
PATALL = "backtest/resultsPatAll/body"
TOL = 1e-9
SEGS = {"主": {"主全窗": ("2017-03-02", None), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
KOF = {"B1": 3, "B2": 3, "K25": 2, "K56": 2}
BASEOF = {"B1": "K25", "B2": "K56"}


def z_of(alpha):
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if math.erfc(mid / math.sqrt(2)) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


Z95 = 1.96
ZB = z_of(0.05 / 2)


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = float(x.mean()); acc = {}
    for xi, gi in zip(x, g):
        acc[gi] = acc.get(gi, 0.0) + (xi - m)
    return m, math.sqrt(sum(v * v for v in acc.values())) / n, len(acc)


def lab(m, se, ne):
    if ne < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if ne < 100 else "出口③"
    lo, hi = m - Z95 * se, m + Z95 * se
    return ex, ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))


def segpos(cal, wn, sg):
    return int(cal.searchsorted(pd.Timestamp(SEGS[wn][sg][0])))


def keyof(cal, Tstr, H, p0):
    pos = cal.searchsorted(pd.to_datetime(pd.Series(list(Tstr))))
    if H == 20:
        return [cal[p].year * 12 + cal[p].month for p in pos]
    return [(p - p0) // 60 for p in pos]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", type=int, default=20); ap.add_argument("--sample_alt", type=int, default=10)
    a = ap.parse_args()
    MAIN = pd.read_csv(os.path.join(OUT, "PatB_main.csv"), encoding="utf-8-sig")
    CMP = pd.read_csv(os.path.join(OUT, "PatB_compare.csv"), encoding="utf-8-sig")
    DESC = pd.read_csv(os.path.join(OUT, "PatB_desc.csv"), encoding="utf-8-sig")
    ALT = pd.read_csv(os.path.join(OUT, "PatB_alt.csv"), encoding="utf-8-sig")
    FQ = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig")
    CHK = {}
    cals = {}
    import backtest.data as D
    for wn in ("主", "早年"):
        D.DATA = AT.WORLDS[wn]["data"]; cals[wn] = D.load_calendar()
    # ── K1
    worst = 0.0; nrow = 0; bad = []
    EVD = {}
    for _, r in MAIN.iterrows():
        wn, sg, cell, H = r["世界"], r["段"], r["格"], int(r["H"])
        cal = cals[wn]; p0 = segpos(cal, wn, sg)
        fr = pd.read_csv(os.path.join(OUT, "events", f"events_{wn}_{sg}_{cell}_H{H}.csv.gz"), dtype={"sid": str})
        EVD[(wn, sg, cell, H)] = fr
        nf = int(FQ[(FQ["世界"] == wn) & (FQ["段"] == sg) & (FQ["格"] == cell)][f"去重後n(保留)_H{H}"].iloc[0])
        if len(fr) != nf or int(r["保留"]) != nf:
            bad.append((wn, sg, cell, H, "列數", len(fr), nf))
        x = (fr["R"] - fr["對照平均"]).to_numpy()
        ok = np.isfinite(x)
        worst = max(worst, float(np.nanmax(np.abs(x[ok] - fr["dX"].to_numpy()[ok]))) if ok.any() else 0.0)
        x = x[ok]; k = keyof(cal, fr["T"][ok], H, p0)
        if len(x) == 0:
            continue
        m, se, ng = cr0(x, k); ne = min(len(x), ng); ex, rs = lab(m, se, ne)
        mine = {"n": len(x), "dX̄": m, "中位": float(np.median(x)), "勝率": float((x > 0).mean()), "最差": float(x.min()),
                "se": se, "lo": m - Z95 * se, "hi": m + Z95 * se, "bonf_lo": m - ZB * se, "bonf_hi": m + ZB * se, "n_eff": ne,
                "扣成本": m - 0.00585}
        for kk, v in mine.items():
            d = abs(float(r[kk]) - v)
            worst = max(worst, d)
            if d > TOL:
                bad.append((wn, sg, cell, H, kk, float(r[kk]), v))
        if r["結果"] != rs or r["出口"] != ex:
            bad.append((wn, sg, cell, H, "標籤", r["結果"], rs))
        nrow += 1
    CHK["K1 主表重算"] = {"列數": nrow, "最大差": worst, "不同": bad[:20], "過": not bad}
    print("K1", CHK["K1 主表重算"], flush=True)
    # ── K2
    Z = np.load(os.path.join(OUT, "fake_acc.npz"))
    bad2 = []
    for key, acc in zip(Z["keys"], Z["acc"]):
        wn, sg, cell, h = str(key).split("|"); H = int(h[1:])
        r = MAIN[(MAIN["世界"] == wn) & (MAIN["段"] == sg) & (MAIN["格"] == cell) & (MAIN["H"] == H)].iloc[0]
        for ver, vn in ((0, "新預設"), (1, "不排除")):
            x2 = 0
            for rep in range(acc.shape[0]):
                nn = acc[rep, ver, :, 0]; S = acc[rep, ver, :, 1]; N = nn.sum()
                if N == 0:
                    continue
                m = S.sum() / N; se = math.sqrt(float(((S - nn * m) ** 2).sum())) / N; ne = int(min(N, (nn > 0).sum()))
                if lab(m, se, ne)[1] == "結果②":
                    x2 += 1
            if x2 != int(r[f"假訊號_{vn}_x2"]):
                bad2.append((str(key), vn, x2, int(r[f"假訊號_{vn}_x2"])))
    CHK["K2 假訊號 x／30"] = {"格數": int(len(Z["keys"])), "不同": bad2, "過": not bad2}
    print("K2", CHK["K2 假訊號 x／30"], flush=True)
    # ── K3
    bad3 = []; w3 = 0.0

    def cmpv(tag, got, want):
        nonlocal w3
        if want is None or (isinstance(want, float) and not np.isfinite(want)):
            return
        d = abs(float(got) - float(want)); w3 = max(w3, d)
        if d > TOL:
            bad3.append((tag, float(got), float(want)))

    for _, r in CMP.iterrows():
        wn, sg, H = r["世界"], r["段"], int(r["H"]); new, old = [s.strip() for s in r["比較"].split("−")]
        cal = cals[wn]; p0 = segpos(cal, wn, sg)
        f1 = EVD[(wn, sg, new, H)]; f2 = EVD[(wn, sg, old, H)]
        f1 = f1[np.isfinite(f1["dX"])]; f2 = f2[np.isfinite(f2["dX"])]
        m1, m2 = f1["dX"].mean(), f2["dX"].mean()
        acc = {}
        for x, g in zip(f1["dX"], keyof(cal, f1["T"], H, p0)):
            acc[g] = acc.get(g, 0.0) + (x - m1) / len(f1)
        for x, g in zip(f2["dX"], keyof(cal, f2["T"], H, p0)):
            acc[g] = acc.get(g, 0.0) - (x - m2) / len(f2)
        se = math.sqrt(sum(v * v for v in acc.values()))
        cmpv((wn, sg, r["比較"], H, "差"), r["差"], m1 - m2); cmpv((wn, sg, r["比較"], H, "se"), r["se"], se)
    for _, r in DESC.iterrows():
        wn, sg, H, par, sub = r["世界"], r["段"], int(r["H"]), r["母格"], r["子集"]
        cal = cals[wn]; p0 = segpos(cal, wn, sg)
        f = EVD[(wn, sg, par, H)]
        ok = (f["配對"] == "有").to_numpy()
        if sub == "只配r10":
            x = (f["R"] - f["對照平均_r10"]).to_numpy(); m_ = np.isfinite(x)
        elif sub == "未配對_dXu":
            x = (f["R"] - f["EW"]).to_numpy(); m_ = ok & np.isfinite(x)
        else:
            x = f["dX"].to_numpy(); m_ = ok & (f["market"] == ("twse" if sub == "上市" else "tpex")).to_numpy()
        xs = x[m_]
        if int(r["n"]) != len(xs):
            bad3.append((wn, sg, par, sub, H, "n", int(r["n"]), len(xs))); continue
        if len(xs) >= 2:
            m, se, ng = cr0(xs, keyof(cal, f["T"][m_], H, p0))
            for kk, v in (("平均", m), ("lo", m - Z95 * se), ("hi", m + Z95 * se)):
                cmpv((wn, sg, par, sub, H, kk), r[kk], v)
    for _, r in ALT.iterrows():
        wn, sg, cell, H = r["世界"], r["段"], r["格"], int(r["H"])
        cal = cals[wn]; p0 = segpos(cal, wn, sg)
        f = pd.read_csv(os.path.join(OUT, "events", f"alt_{wn}_{sg}_{cell}_H{H}.csv.gz"), dtype={"sid": str})
        u = f["可算"].astype(str).eq("True").to_numpy()
        fe = EVD[(wn, sg, cell, H)]
        if not (len(f) == len(fe) and (f["sid"].to_numpy() == fe["sid"].to_numpy()).all() and (f["T"].to_numpy() == fe["T"].to_numpy()).all()):
            bad3.append((wn, sg, cell, H, "alt 列與事件檔不同")); continue
        xa = (f["R_alt"] - f["對照_alt"]).to_numpy()[u]; xd = (f["R_day"] - f["對照_day"]).to_numpy()[u]
        xc = fe["dX"].to_numpy()[u]
        kk_ = keyof(cal, f["T"][u], H, p0)
        if int(r["可算"]) != int(u.sum()):
            bad3.append((wn, sg, cell, H, "可算數", int(r["可算"]), int(u.sum()))); continue
        for nm_, x in (("X_alt全段", xa), ("X_day確認日", xd), ("X_rest之後", xa - xd)):
            m, se, _ = cr0(x, kk_)
            cmpv((wn, sg, cell, H, nm_, "平均"), r[f"{nm_}_平均"], m)
            cmpv((wn, sg, cell, H, nm_, "lo"), r[f"{nm_}_lo"], m - Z95 * se)
        okc = np.isfinite(xc)
        m, se, _ = cr0(xc[okc], [k_ for k_, o_ in zip(kk_, okc) if o_])
        cmpv((wn, sg, cell, H, "X_確認版同批", "平均"), r["X_確認版同批_平均"], m)
        ma, md = xa.mean(), xd.mean(); rr = md / ma
        z = (xd - rr * xa) / ma; zm = z.mean(); accz = {}
        for zi, g in zip(z, kk_):
            accz[g] = accz.get(g, 0.0) + (zi - zm)
        sez = math.sqrt(sum(v * v for v in accz.values())) / len(z)
        cmpv((wn, sg, cell, H, "占比"), r["確認日占比"], rr); cmpv((wn, sg, cell, H, "占比_lo"), r["占比_lo"], rr - Z95 * sez)
    CHK["K3 比較、描述格、先驗③"] = {"比較列": len(CMP), "描述列": len(DESC), "先驗③列": len(ALT), "最大差": w3, "不同": bad3[:20], "過": not bad3}
    print("K3", CHK["K3 比較、描述格、先驗③"], flush=True)
    # ── K4、K4b 獨立重建對照組
    rng = np.random.default_rng(20261017)
    res4 = []; res4b = []; w4 = 0.0
    for wn, ns, nsa in (("主", (a.sample + 1) // 2, (a.sample_alt + 1) // 2), ("早年", a.sample // 2, a.sample_alt // 2)):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        D.DATA = W["data"]
        cand = [(sg, cell, H) for sg in SEGS[wn] for cell in KOF for H in (20, 60)]
        picks = []
        for q in range(ns):
            sg, cell, H = cand[int(rng.integers(len(cand)))]
            f = EVD[(wn, sg, cell, H)]; f = f[f["配對"] == "有"]
            if len(f):
                picks.append((sg, cell, H, f.iloc[int(rng.integers(len(f)))]))
        picksA = []
        for q in range(nsa):
            sg = list(SEGS[wn])[int(rng.integers(len(SEGS[wn])))]; cell = ("B1", "B2")[int(rng.integers(2))]; H = (20, 60)[int(rng.integers(2))]
            f = pd.read_csv(os.path.join(OUT, "events", f"alt_{wn}_{sg}_{cell}_H{H}.csv.gz"), dtype={"sid": str})
            f = f[f["可算"].astype(str) == "True"]
            if len(f):
                picksA.append((sg, cell, H, f.iloc[int(rng.integers(len(f)))]))
        ST = {}
        for sid in W["sids"]:
            B = R11.load_bars(sid, W["mk"].get(sid, "twse"), cal)
            if B is None:
                continue
            df = B["df"]; idx = np.asarray(B["idx"], np.int64)
            badb = set(int(k) for k in np.flatnonzero(B["next_bad"][:len(idx)] == np.arange(len(idx))))
            for p_ in W["BADPOS"].get(sid, ()):
                k = int(np.searchsorted(idx, p_, "left"))
                if k < len(idx):
                    badb.add(k)
            ST[sid] = {"c": df["close"].to_numpy(float), "o": df["open"].to_numpy(float), "idx": idx,
                       "badpos": set(int(idx[k]) for k in badb)}
        RAW = {}
        for cell in KOF:
            s_ = set()
            for sg in SEGS[wn]:
                e = pd.read_csv(os.path.join(FREQ, f"events_{wn}_{sg}_{cell}.csv.gz"), dtype=str)
                s_ |= set(zip(e["sid"], e["T"]))
            RAW[cell] = s_
        ixd = W["ix"]

        def feats(sid, T, k):
            c = ST[sid]["c"]; idx = ST[sid]["idx"]
            if not np.isfinite(c[T]):
                return np.nan, np.nan, -1
            b = int(np.searchsorted(idx, T))
            if b - k - 10 < 0:
                return np.nan, np.nan, -1
            return c[idx[b - k]] / c[idx[b - k - 10]] - 1.0, c[idx[b]] / c[idx[b - k]] - 1.0, int(idx[b - k + 1])

        def Rof(sid, T, H):
            c, o = ST[sid]["c"], ST[sid]["o"]
            if T + H > n0 - 1 or not np.isfinite(c[T + 1]) or not np.isfinite(o[T + 1]) or not o[T + 1] > 0:
                return np.nan
            j = T + H
            while j >= 0 and not np.isfinite(c[j]):
                j -= 1
            return c[j] / o[T + 1] - 1.0

        def brk(sid, f, e):
            idx = ST[sid]["idx"]; bp = ST[sid]["badpos"]
            for p in range(f, e + 1):
                if p in bp:
                    return True
            kH = int(np.searchsorted(idx, e, "right")) - 1
            if 0 <= kH < len(idx) - 1 and idx[kH + 1] - idx[kH] - 1 >= 5 and e - idx[kH] >= 5:
                return True
            return False

        def rebuild(T, k, H, sid0, rawcell, Hs):
            vals = {}
            for sid in ST:
                if not W["PV"][ixd[sid], T]:
                    continue
                r10, prd, f = feats(sid, T, k)
                if np.isfinite(r10) and np.isfinite(prd):
                    vals[sid] = (r10, prd, f)
            sr = pd.Series({s: v[0] for s, v in vals.items()}); sp = pd.Series({s: v[1] for s, v in vals.items()})
            d1 = pd.qcut(sr.rank(method="first"), 10, labels=False); d2 = pd.qcut(sp.rank(method="first"), 10, labels=False)
            a1, a2 = d1[sid0], d2[sid0]
            out = {h: [] for h in Hs}; out10 = []
            for sid in vals:
                if sid == sid0 or d1[sid] != a1 or not vals[sid][0] < 0:
                    continue
                if (sid, str(cal[T].date())) in RAW[rawcell]:
                    continue
                j = ixd[sid]; e1 = T + 1
                if not (W["TRD"][j, e1] and np.isfinite(W["O"][j, e1]) and W["O"][j, e1] > 0 and not W["UPL"][j, e1] and not W["DNL"][j, e1]):
                    continue
                if brk(sid, vals[sid][2], T + H):
                    continue
                gs = {h: Rof(sid, T, h) for h in Hs}
                if not all(np.isfinite(v) for v in gs.values()):
                    continue
                out10.append(gs[Hs[0]])
                if d2[sid] == a2:
                    for h in Hs:
                        out[h].append(gs[h])
            return out, out10

        for sg, cell, H, ev in picks:
            T = int(cal.searchsorted(pd.Timestamp(ev["T"]))); sid0 = ev["sid"]
            out, out10 = rebuild(T, KOF[cell], H, sid0, cell, (H,))
            r0 = Rof(sid0, T, H)
            cm = float(np.mean(out[H])) if out[H] else np.nan; c10 = float(np.mean(out10)) if out10 else np.nan
            d1 = abs(r0 - float(ev["R"])); d2 = abs(cm - float(ev["對照平均"])); d3 = abs(c10 - float(ev["對照平均_r10"]))
            w4 = max(w4, d1, d2, d3)
            res4.append({"世界": wn, "段": sg, "格": cell, "H": H, "sid": sid0, "T": ev["T"], "R差": d1, "對照平均差": d2, "只配r10對照差": d3,
                         "對照數_重建": len(out[H]), "對照數_本體": int(ev["對照數"]), "r10對照數_重建": len(out10), "r10對照數_本體": int(ev["對照數_r10"]),
                         "同": bool(d1 <= TOL and d2 <= TOL and d3 <= TOL and len(out[H]) == int(ev["對照數"]) and len(out10) == int(ev["對照數_r10"]))})
            print("K4", res4[-1], flush=True)
        for sg, cell, H, ev in picksA:
            T2 = int(cal.searchsorted(pd.Timestamp(ev["T2"]))); sid0 = ev["sid"]
            out, _ = rebuild(T2, 2, H + 1, sid0, BASEOF[cell], (H + 1, 1))
            ra = Rof(sid0, T2, H + 1); rd = Rof(sid0, T2, 1)
            ca = float(np.mean(out[H + 1])) if out[H + 1] else np.nan; cd = float(np.mean(out[1])) if out[1] else np.nan
            ds = [abs(ra - float(ev["R_alt"])), abs(rd - float(ev["R_day"])), abs(ca - float(ev["對照_alt"])), abs(cd - float(ev["對照_day"]))]
            w4 = max(w4, *ds)
            res4b.append({"世界": wn, "段": sg, "格": cell, "H": H, "sid": sid0, "T": ev["T"], "T2": ev["T2"], "最大差": max(ds),
                          "對照數_重建": len(out[H + 1]), "對照數_本體": int(ev["對照數"]),
                          "同": bool(max(ds) <= TOL and len(out[H + 1]) == int(ev["對照數"]))})
            print("K4b", res4b[-1], flush=True)
    CHK["K4 獨立重建對照組"] = {"筆數": len(res4), "最大差": w4, "全同": all(x["同"] for x in res4), "明細": res4}
    CHK["K4b 先驗③ 獨立重建"] = {"筆數": len(res4b), "全同": all(x["同"] for x in res4b), "明細": res4b}
    # ── K5 原版 vs PatAll 既有結果
    k5 = {}
    cells = pd.read_csv(os.path.join(PATALL, "cells.csv"), encoding="utf-8-sig", dtype={"vid": str})
    calm = cals["主"]
    for cell in ("K25", "K56"):
        P = pd.read_csv(os.path.join(PATALL, "events", f"events_{cell}.csv.gz"), dtype={"sid": str})
        for H in (20, 60):
            p = P[P["H"] == H]; m = EVD[("主", "主全窗", cell, H)]
            jn = p.merge(m, on=["sid", "T"], suffixes=("_P", "_B"))
            dR = (jn["R_P"] - jn["R_B"]).abs()
            okc = np.isfinite(jn["對照平均_P"]) & np.isfinite(jn["對照平均_B"])
            dc = (jn["對照平均_P"] - jn["對照平均_B"])[okc]
            Tmax = p["T"].max()
            mm = m[(m["T"] <= Tmax) & np.isfinite(m["dX"])]
            p0 = segpos(calm, "主", "主全窗")
            mB, seB, ngB = cr0(mm["dX"].to_numpy(), keyof(calm, mm["T"], H, p0))
            cr = cells[(cells["vid"] == cell) & (cells["H"] == H)].iloc[0]
            k5[f"{cell}_H{H}"] = {
                "PatAll保留": int(len(p)), "本件主全窗保留": int(len(m)), "共同(sid,T)": int(len(jn)),
                "共同_first相同": bool((jn["first_P"] == jn["first_B"]).all()),
                "共同_R最大差": float(dR.max()) if len(dR) else None, "共同_R逐位元同": bool((dR == 0).all()),
                "共同_對照平均差_平均": float(dc.mean()), "共同_對照平均差_絕對中位": float(dc.abs().median()), "共同_對照平均相關": float(np.corrcoef(jn["對照平均_P"][okc], jn["對照平均_B"][okc])[0, 1]),
                "共同_dX差_平均": float(((jn["R_P"] - jn["對照平均_P"]) - (jn["R_B"] - jn["對照平均_B"]))[okc].mean()),
                "共同_PatAll_dX̄": float((jn["dX_P"])[okc].mean()), "共同_本件_dX̄": float((jn["dX_B"])[okc].mean()),
                "PatAll_cells_dX̄": float(cr["dX̄"]), "PatAll_cells_CI": [float(cr["lo"]), float(cr["hi"])], "PatAll_cells_結果": cr["結果"],
                "本件同窗(T≤PatAll最後T)_dX̄": mB, "本件同窗_CI": [mB - Z95 * seB, mB + Z95 * seB], "本件同窗_結果": lab(mB, seB, min(len(mm), ngB))[1],
                "結果標籤相同": bool(cr["結果"] == lab(mB, seB, min(len(mm), ngB))[1])}
            print("K5", cell, H, k5[f"{cell}_H{H}"], flush=True)
    CHK["K5 原版對PatAll既有結果"] = k5
    CHK["K5_R逐位元同"] = all(v["共同_R逐位元同"] and v["共同_first相同"] for v in k5.values())
    CHK["全部過"] = bool(CHK["K1 主表重算"]["過"] and CHK["K2 假訊號 x／30"]["過"] and CHK["K3 比較、描述格、先驗③"]["過"]
                       and CHK["K4 獨立重建對照組"]["全同"] and CHK["K4b 先驗③ 獨立重建"]["全同"] and CHK["K5_R逐位元同"])
    json.dump(CHK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部過" if CHK["全部過"] else "⛔ 有不同", flush=True)


if __name__ == "__main__":
    main()

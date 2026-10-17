# -*- coding: utf-8 -*-
"""型態補條件 C 組 seq1 事件層 獨立查核（⛔ 不 import researchPatC、researchPatC_freq 任何一行；
只 import 資料層：researchAscTri_freq.load_world（世界、pit_valid、T＋1 旗標、壞根來源）、research11.load_bars（有效 K 棒、壞根）。
本體跑完後：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatC_check [--sample 20]

K1 從逐筆檔 events/events_<世界>_<段>_<格>_H<H>.csv.gz 重算主表每一列：X ＝ R − 對照平均、n、d×X̄、中位、勝率、最差；
   CR0 分群 SE（自己寫：Σ_g(Σ_{i∈g}(x_i − x̄))² 開根號 ÷ n；H20 曆月、H60 (T−段起點)//60）、95% CI、
   Bonferroni（z 用二分法解 erfc(z/√2)＝0.05／2，自己算）、n_eff、出口、結果 ⇒ 與 PatC_main.csv 逐列比（數值差 ≤ 1e−9、標籤相同）；
   逐筆列數 ＝ 頻率表 freq.csv「去重後n(保留)」。
K2 假訊號臂：由 fake_acc.npz 逐群 (n, Σ) 自己重算 30 次 × 兩版 ⇒ x／30 與 PatC_main.csv 比。
K3 比較（K1−K1b、K2−K2b）與描述格（嚴版、K1∖K1b、Adam／Eve、量遞減）從逐筆檔自己重算 ⇒ 與 PatC_compare.csv、PatC_desc.csv 比（≤ 1e−9）。
K4 抽 --sample 筆（主、早年各半；種子 20261017）：全市場逐檔獨立重建對照組——r60 ＝ 第 first 根前一根收盤 ÷ 再往前 60 根收盤 − 1（有效 K 棒逐根數）；
   十分位 ＝ pd.qcut(rank(method="first"), 10)（橫斷面 ＝ first 當天 pit_valid ∧ 有效 ∧ r60 可算）；原始偵測取頻率表已提交事件檔（任何狀態）；
   T＋1 可成交（世界旗標）；硬斷點逐日掃（⛔ 不用累加和）；R ＝ ≤ T＋H 最後有效收盤 ÷ T＋1 開盤 − 1 ⇒ 與逐筆檔的 R、對照平均、對照數比。
結果寫 resultsPatC/check.json。
"""
from __future__ import annotations

import argparse
import gzip
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
OUT = "backtest/resultsPatC"
FREQ = "backtest/resultsPatC/freq"
TOL = 1e-9
SEGS = {"主": {"主全窗": ("2017-03-02", None), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}


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
    x, y = SEGS[wn][sg]
    p0 = int(cal.searchsorted(pd.Timestamp(x)))
    return p0


def keyof(cal, Tstr, H, p0):
    pos = cal.searchsorted(pd.to_datetime(Tstr))
    if H == 20:
        return [cal[p].year * 12 + cal[p].month for p in pos]
    return [(p - p0) // 60 for p in pos]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", type=int, default=20)
    a = ap.parse_args()
    MAIN = pd.read_csv(os.path.join(OUT, "PatC_main.csv"), encoding="utf-8-sig")
    CMP = pd.read_csv(os.path.join(OUT, "PatC_compare.csv"), encoding="utf-8-sig")
    DESC = pd.read_csv(os.path.join(OUT, "PatC_desc.csv"), encoding="utf-8-sig")
    FQ = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig")
    CHK = {}
    cals = {}
    for wn in ("主", "早年"):
        import backtest.data as D
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
                "se": se, "lo": m - Z95 * se, "hi": m + Z95 * se, "bonf_lo": m - ZB * se, "bonf_hi": m + ZB * se, "n_eff": ne}
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
        for kk, v in (("差", m1 - m2), ("se", se)):
            d = abs(float(r[kk]) - v); w3 = max(w3, d)
            if d > TOL:
                bad3.append((wn, sg, r["比較"], H, kk, float(r[kk]), v))
    for _, r in DESC.iterrows():
        wn, sg, H, par, sub = r["世界"], r["段"], int(r["H"]), r["母格"], r["子集"]
        cal = cals[wn]; p0 = segpos(cal, wn, sg)
        f = EVD[(wn, sg, par, H)]; f = f[np.isfinite(f["dX"])]
        if par == "K1":
            kb = set(zip(EVD[(wn, sg, "K1b", H)]["sid"], EVD[(wn, sg, "K1b", H)]["T"]))
            inb = np.array([(s, t) in kb for s, t in zip(f["sid"], f["T"])], bool)
            m_ = inb if sub.startswith("嚴版") else ~inb
        elif sub.startswith("量遞減"):
            m_ = f["量遞減"].astype(str).eq("True").to_numpy()
        else:
            m_ = f["Adam/Eve"].eq(sub).to_numpy()
        x = f["dX"].to_numpy()[m_]
        if int(r["n"]) != len(x):
            bad3.append((wn, sg, par, sub, H, "n", int(r["n"]), len(x))); continue
        if len(x) >= 2:
            m, se, ng = cr0(x, keyof(cal, f["T"][m_], H, p0))
            for kk, v in (("平均", m), ("lo", m - Z95 * se), ("hi", m + Z95 * se)):
                d = abs(float(r[kk]) - v); w3 = max(w3, d)
                if d > TOL:
                    bad3.append((wn, sg, par, sub, H, kk, float(r[kk]), v))
    CHK["K3 比較與描述格"] = {"比較列": len(CMP), "描述列": len(DESC), "最大差": w3, "不同": bad3[:20], "過": not bad3}
    print("K3", CHK["K3 比較與描述格"], flush=True)
    # ── K4 獨立重建對照組
    rng = np.random.default_rng(20261017)
    res4 = []; w4 = 0.0
    for wn, ns in (("主", (a.sample + 1) // 2), ("早年", a.sample // 2)):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        import backtest.data as D
        D.DATA = W["data"]
        cand = [(sg, cell, H) for sg in SEGS[wn] for cell in ("K1", "K1b", "K2", "K2b") for H in (20, 60)]
        picks = []
        for q in range(ns):
            sg, cell, H = cand[int(rng.integers(len(cand)))]
            f = EVD[(wn, sg, cell, H)]; f = f[f["配對"] == "有"]
            if len(f):
                picks.append((sg, cell, H, f.iloc[int(rng.integers(len(f)))]))
        # 全市場
        ST = {}
        for sid in W["sids"]:
            B = R11.load_bars(sid, W["mk"].get(sid, "twse"), cal)
            if B is None:
                continue
            df = B["df"]; idx = B["idx"]
            badb = set(int(k) for k in np.flatnonzero(B["next_bad"][:len(idx)] == np.arange(len(idx))))
            for p_ in W["BADPOS"].get(sid, ()):
                k = int(np.searchsorted(idx, p_, "left"))
                if k < len(idx):
                    badb.add(k)
            ST[sid] = {"c": df["close"].to_numpy(float), "o": df["open"].to_numpy(float), "idx": idx,
                       "badpos": set(int(idx[k]) for k in badb)}
        RAW = {}
        for cell in ("K1", "K1b", "K2", "K2b"):
            s_ = set()
            for sg in SEGS[wn]:
                p_ = os.path.join(FREQ, f"events_{wn}_{sg}_{cell}.csv.gz")
                e = pd.read_csv(p_, dtype=str)
                s_ |= set(zip(e["sid"], e["T"]))
            RAW[cell] = s_
        ixd = W["ix"]

        def r60(sid, fpos):
            c = ST[sid]["c"]
            if not np.isfinite(c[fpos]):
                return np.nan
            prev = []
            for p in range(fpos - 1, -1, -1):
                if np.isfinite(c[p]):
                    prev.append(p)
                    if len(prev) == 61:
                        break
            if len(prev) < 61:
                return np.nan
            return c[prev[0]] / c[prev[60]] - 1.0

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
            last = [k for k in range(len(idx)) if idx[k] <= e]
            if last:
                kH = last[-1]
                if kH < len(idx) - 1 and idx[kH + 1] - idx[kH] - 1 >= 5 and e - idx[kH] >= 5:
                    return True
            return False

        for sg, cell, H, ev in picks:
            T = int(cal.searchsorted(pd.Timestamp(ev["T"]))); f = int(cal.searchsorted(pd.Timestamp(ev["first"])))
            sid0 = ev["sid"]
            vals = {}
            for sid in ST:
                j = ixd[sid]
                if not W["PV"][j, f]:
                    continue
                v = r60(sid, f)
                if np.isfinite(v):
                    vals[sid] = v
            sr = pd.Series(vals)
            dec = pd.qcut(sr.rank(method="first"), 10, labels=False)
            d0 = dec[sid0]
            ctrl = []
            for sid in ST:
                if sid == sid0 or sid not in dec.index or dec[sid] != d0:
                    continue
                j = ixd[sid]
                if not W["PV"][j, T] or not np.isfinite(ST[sid]["c"][T]):
                    continue
                if (sid, str(cal[T].date())) in RAW[cell]:
                    continue
                e1 = T + 1
                if not (W["TRD"][j, e1] and np.isfinite(W["O"][j, e1]) and W["O"][j, e1] > 0 and not W["UPL"][j, e1] and not W["DNL"][j, e1]):
                    continue
                if brk(sid, f, T + H):
                    continue
                g = Rof(sid, T, H)
                if not np.isfinite(g):
                    continue
                ctrl.append(g)
            r0 = Rof(sid0, T, H)
            cm = float(np.mean(ctrl)) if ctrl else np.nan
            d1 = abs(r0 - float(ev["R"])); d2 = abs(cm - float(ev["對照平均"]))
            w4 = max(w4, d1, d2)
            res4.append({"世界": wn, "段": sg, "格": cell, "H": H, "sid": sid0, "T": ev["T"], "R差": d1, "對照平均差": d2,
                         "對照數_重建": len(ctrl), "對照數_本體": int(ev["對照數"]), "同": bool(d1 <= TOL and d2 <= TOL and len(ctrl) == int(ev["對照數"]))})
            print("K4", res4[-1], flush=True)
    CHK["K4 獨立重建對照組"] = {"筆數": len(res4), "最大差": w4, "全同": all(x["同"] for x in res4), "明細": res4}
    CHK["全部過"] = bool(CHK["K1 主表重算"]["過"] and CHK["K2 假訊號 x／30"]["過"] and CHK["K3 比較與描述格"]["過"] and CHK["K4 獨立重建對照組"]["全同"])
    json.dump(CHK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部過" if CHK["全部過"] else "⛔ 有不同", flush=True)


if __name__ == "__main__":
    main()

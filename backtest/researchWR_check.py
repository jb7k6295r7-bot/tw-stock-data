# -*- coding: utf-8 -*-
"""Williams %R 對日線 KD seq1 事件層 獨立對帳（⛔ 不 import researchWR、researchWR_freq、researchPatC 任何一行；
只 import 資料層：researchAscTri_freq.load_world（世界、pit_valid、T＋1 旗標、壞根來源）、research11.load_bars（有效 K 棒、壞根）；
原始偵測／保留狀態取已提交的頻率表 resultsWR/freq/events_<世界>.csv.gz（頻率表自己的對帳已驗偵測）。本體跑完後：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWR_check [--sample 20]

K1 從逐筆檔 events/trades_<世界>_<段>_<格>_H<H>.csv.gz 重算 WR_main.csv 每一列：X ＝ R − 對照平均、n、X̄、中位、X 勝率、
   CR0 分群 SE（自己寫：√Σ_g(Σ_{i∈g}(x_i − x̄))² ÷ n；H20 曆月、H60 (T−段起點)//60）、95% CI、n_eff、出口、結果、X̄ − 0.585%、
   淨報酬平均、勝率 ⇒ 逐列比（≤ 1e−9、標籤相同）；逐筆列數 ＝ 頻率表 freq.csv「事件數(保留)」。
K2 假訊號臂：由 fake_acc.npz 逐群 (n, Σ) 自己重算 30 次 × 兩版 ⇒ x／30 與 WR_main.csv 比；seq322 五條自己重判。
K3 W − K 差（自己寫的曆月線性化 SE）、重疊拆解描述格、週線版 X̄ 從逐筆檔自己重算 ⇒ 與 WR_diff.csv、WR_desc.csv、WR_week.csv 比。
K4 抽 --sample 筆（主：W 6、K 4；早年：W 6、K 4；探索／確認輪流；種子 20261019）逐根手算：
   事件：%R(14)（W；日曆 df 逐列取最近 14 個有成交日的還原高低收）或 KD 逐段迴圈（K）⇒ 訊號條件成立；
   r20 ＝ 往前數 20 個有成交日（只用 ≤ T 的資料；窗內無壞 K 棒）；R ＝ ≤ T＋H 最後有效收盤 ÷ T＋1 還原開盤 − 1（H20、H60）；
   對照：全市場逐檔獨立重建——母體（自算 T−20～T−1 日均量 ≥ 500,000 股 ∧ 含 T 的 20 日都有成交 ∧ pit_valid）、r20、
   十分位 ＝ pd.qcut(rank(method="first"), 10)、原始偵測取頻率表事件檔（任何狀態）、T＋1 可買（世界旗標＋下一根 ＝ T＋1 且非壞 K 棒）、
   硬斷點逐日掃（⛔ 不用累加和）、R 可算 ⇒ 對照平均、對照數，與逐筆檔比。
K5 不前視：同 20 筆，把該股 K 棒截在 T（⛔ 不看 T 之後）重算 %R／KD／r20 ⇒ 與全序列算的同；進場日 ＝ 日曆 T＋1 ＞ T、出場日 ＝ 日曆 T＋H。
結果寫 resultsWR/check.json、check.log。
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
OUT = "backtest/resultsWR"
FREQ = "backtest/resultsWR/freq"
TOL = 1e-9
COST = 0.00585
Z95 = 1.96
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "主全窗": ("2017-03-02", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = float(x.mean()); acc = {}
    for xi, gi in zip(x, g):
        acc[gi] = acc.get(gi, 0.0) + (xi - m)
    return m, math.sqrt(sum(v * v for v in acc.values())) / n, len(acc), acc


def lab(m, se, ne):
    if ne < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if ne < 100 else "出口③"
    lo, hi = m - Z95 * se, m + Z95 * se
    return ex, ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))


def p0_of(cal, wn, sg):
    return int(cal.searchsorted(pd.Timestamp(SEGS[wn][sg][0])))


def keyof(cal, Tstr, H, p0):
    pos = cal.searchsorted(pd.to_datetime(pd.Series(Tstr)))
    if H == 20:
        return [cal[p].year * 12 + cal[p].month for p in pos]
    return [(p - p0) // 60 for p in pos]


def main():
    global OUT
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", type=int, default=20); ap.add_argument("--out", default=None)
    ap.add_argument("--dry", action="store_true", help="對乾跑輸出驗流程：手算 R 一律寫 0（⛔ 不讀報酬）")
    a = ap.parse_args()
    if a.out:
        OUT = a.out
    MAIN = pd.read_csv(os.path.join(OUT, "WR_main.csv"), encoding="utf-8-sig")
    DIFF = pd.read_csv(os.path.join(OUT, "WR_diff.csv"), encoding="utf-8-sig")
    DESC = pd.read_csv(os.path.join(OUT, "WR_desc.csv"), encoding="utf-8-sig")
    WEEK = pd.read_csv(os.path.join(OUT, "WR_week.csv"), encoding="utf-8-sig")
    FQ = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig")
    CHK = {}
    cals = {}
    import backtest.data as D
    for wn in ("主", "早年"):
        D.DATA = AT.WORLDS[wn]["data"]; cals[wn] = D.load_calendar()
    # ── K1
    worst = 0.0; nrow = 0; bad = []; EVD = {}
    for _, r in MAIN.iterrows():
        wn, sg, cell, H = r["世界"], r["段"], r["格"], int(r["H"])
        cal = cals[wn]; p0 = p0_of(cal, wn, sg)
        fr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{sg}_{cell}_H{H}.csv.gz"), dtype={"sid": str})
        EVD[(wn, sg, cell, H)] = fr
        nf = int(FQ[(FQ["世界"] == wn) & (FQ["段"] == sg) & (FQ["格"] == cell)]["事件數(保留)"].iloc[0])
        if len(fr) != nf or int(r["保留"]) != nf:
            bad.append((wn, sg, cell, H, "列數", len(fr), nf))
        x = (fr["R"] - fr["對照平均"]).to_numpy()
        ok = (fr["配對"] == "有").to_numpy()
        if not (np.isfinite(fr["X"].to_numpy()) == ok).all():
            bad.append((wn, sg, cell, H, "配對與X有值不一致"))
        worst = max(worst, float(np.max(np.abs(x[ok] - fr["X"].to_numpy()[ok]))) if ok.any() else 0.0)
        Rv = fr["R"].to_numpy()[ok]; x = x[ok]; k = keyof(cal, fr["T"][ok], H, p0)
        if len(x) == 0:
            continue
        m, se, ng, accm = cr0(x, k); ne = min(len(x), ng); ex, rs = lab(m, se, ne)
        net = Rv - COST
        mine = {"n": len(x), "X̄": m, "中位": float(np.median(x)), "X勝率": float((x > 0).mean()), "se": se, "lo": m - Z95 * se, "hi": m + Z95 * se,
                "n_eff": ne, "X̄扣成本": m - COST, "淨報酬平均(R−0.585%)": float(net.mean()), "勝率(淨>0)": float((net > 0).mean())}
        for kk, v in mine.items():
            d = abs(float(r[kk]) - v); worst = max(worst, d)
            if d > TOL:
                bad.append((wn, sg, cell, H, kk, float(r[kk]), v))
        if r["結果"] != rs or r["出口"] != ex:
            bad.append((wn, sg, cell, H, "標籤", r["結果"], rs))
        if H == 20:
            mm = pd.Series(x).groupby(k).mean()
            EVD[("月同號", wn, sg, cell)] = bool(np.sign(mm.median()) == np.sign(m))
        nrow += 1
    CHK["K1 主表重算"] = {"列數": nrow, "最大差": worst, "不同": bad[:20], "過": not bad}
    log(f"K1 {CHK['K1 主表重算']}")
    # ── K2
    Z = np.load(os.path.join(OUT, "fake_acc.npz"))
    bad2 = []; g322 = {}
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
            if ver == 0:
                mine322 = bool(r["結果"] == "結果②" and float(r["bonf_lo"]) > 0 and x2 <= 1 and float(r["X̄扣成本"]) > 0 and EVD.get(("月同號", wn, sg, cell), False))
                g322[str(key)] = mine322
                if mine322 != (str(r["過seq322門檻"]) == "True"):
                    bad2.append((str(key), "seq322", mine322, r["過seq322門檻"]))
    CHK["K2 假訊號 x／30 與 seq322"] = {"格數": int(len(Z["keys"])), "seq322自判": g322, "不同": bad2, "過": not bad2}
    log(f"K2 {CHK['K2 假訊號 x／30 與 seq322']}")
    # ── K3
    bad3 = []; w3 = 0.0
    for _, r in DIFF.iterrows():
        wn, sg, H = r["世界"], r["段"], int(r["H"]); cal = cals[wn]; p0 = p0_of(cal, wn, sg)
        f1 = EVD[(wn, sg, "W", H)]; f2 = EVD[(wn, sg, "K", H)]
        f1 = f1[f1["配對"] == "有"]; f2 = f2[f2["配對"] == "有"]
        m1, m2 = f1["X"].mean(), f2["X"].mean(); acc = {}
        for x, g in zip(f1["X"], keyof(cal, f1["T"], H, p0)):
            acc[g] = acc.get(g, 0.0) + (x - m1) / len(f1)
        for x, g in zip(f2["X"], keyof(cal, f2["T"], H, p0)):
            acc[g] = acc.get(g, 0.0) - (x - m2) / len(f2)
        se = math.sqrt(sum(v * v for v in acc.values()))
        for kk, v in (("差(W−K)", m1 - m2), ("se", se), ("lo", m1 - m2 - Z95 * se), ("hi", m1 - m2 + Z95 * se)):
            d = abs(float(r[kk]) - v); w3 = max(w3, d)
            if d > TOL:
                bad3.append((wn, sg, H, kk, float(r[kk]), v))
    for _, r in DESC.iterrows():
        wn, sg, H, sub = r["世界"], r["段"], int(r["H"]), r["子集"]; cal = cals[wn]; p0 = p0_of(cal, wn, sg)
        if "（W 的對照）" in sub or sub.startswith("W 獨有"):
            f = EVD[(wn, sg, "W", H)]; fl = f["同日K"].astype(str).eq("True")
        else:
            f = EVD[(wn, sg, "K", H)]; fl = f["同日W"].astype(str).eq("True")
        m_ = (f["配對"] == "有") & (fl if "同日" in sub else ~fl)
        x = f["X"][m_].to_numpy()
        if int(r["n"]) != len(x):
            bad3.append((wn, sg, sub, H, "n", int(r["n"]), len(x))); continue
        if len(x) >= 2:
            m, se, ng, _ = cr0(x, keyof(cal, f["T"][m_], H, p0))
            for kk, v in (("平均", m), ("lo", m - Z95 * se), ("hi", m + Z95 * se)):
                d = abs(float(r[kk]) - v); w3 = max(w3, d)
                if d > TOL:
                    bad3.append((wn, sg, sub, H, kk, float(r[kk]), v))
    nweek = 0
    for _, r in WEEK.iterrows():
        if r["格"] not in ("週_W", "週_K") or not (r.get("n", 0) and np.isfinite(r.get("n", np.nan))):
            continue
        wn, sg, k = r["世界"], r["段"], int(r["持有週"]); cal = cals[wn]
        f = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{sg}_{r['格']}_K{k}w.csv.gz"), dtype={"sid": str})
        f = f[f["配對"] == "有"]; x = (f["R"] - f["對照平均"]).to_numpy()
        m, se, ng, _ = cr0(x, keyof(cal, f["T"], 20, 0))
        for kk, v in (("n", len(x)), ("平均", m), ("lo", m - Z95 * se), ("hi", m + Z95 * se)):
            d = abs(float(r[kk]) - v); w3 = max(w3, d)
            if d > TOL:
                bad3.append((wn, sg, r["格"], k, kk, float(r[kk]), v))
        nweek += 1
    CHK["K3 W−K 差、描述格、週線"] = {"差列": len(DIFF), "描述列": len(DESC), "週線列": nweek, "最大差": w3, "不同": bad3[:20], "過": not bad3}
    log(f"K3 {CHK['K3 W−K 差、描述格、週線']}")
    # ── K4／K5 抽樣逐根手算
    rng = np.random.default_rng(20261019)
    res4 = []; w4 = 0.0
    plan = {"主": [("W", 6), ("K", 4)], "早年": [("W", 6), ("K", 4)]}
    if a.sample != 20:
        plan = {"主": [("W", (a.sample * 3 + 9) // 10), ("K", a.sample // 5)], "早年": [("W", (a.sample * 3) // 10), ("K", a.sample // 5)]}
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; ixd = W["ix"]
        D.DATA = W["data"]
        picks = []
        for cell, m in plan[wn]:
            segs = ["探索", "確認"] if wn == "主" else ["早年"]
            for q in range(m):
                sg = segs[q % len(segs)]
                f = EVD[(wn, sg, cell, 20)]; f = f[f["配對"] == "有"]
                picks.append((sg, cell, f.iloc[int(rng.integers(len(f)))]))
        ST = {}
        for sid in W["sids"]:
            B = R11.load_bars(sid, W["mk"].get(sid, "twse"), cal)
            if B is None:
                continue
            df = B["df"]; idx = B["idx"].astype(np.int64)
            badk = set(int(k) for k in np.flatnonzero(B["next_bad"][:len(idx)] == np.arange(len(idx))))
            for p_ in W["BADPOS"].get(sid, ()):
                k = int(np.searchsorted(idx, p_, "left"))
                if k < len(idx):
                    badk.add(k)
            ST[sid] = {"c": df["close"].to_numpy(float), "o": df["open"].to_numpy(float), "h": df["high"].to_numpy(float),
                       "l": df["low"].to_numpy(float), "trd": df["traded"].to_numpy(bool), "vol": df["volume"].to_numpy(float),
                       "idx": idx, "posset": set(int(p) for p in idx), "badpos": set(int(idx[k]) for k in badk)}
        ev = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str, usecols=["格", "sid", "T"])
        RAW = {c: set(zip(ev[ev["格"] == c]["sid"], ev[ev["格"] == c]["T"])) for c in ("W", "K")}

        def bars_le(sid, T, n):
            """≤ T 的最近 n 個有效 K 棒日曆位置（由新到舊）。"""
            idx = ST[sid]["idx"]; k = int(np.searchsorted(idx, T, "right")) - 1
            return [int(idx[j]) for j in range(k, max(k - n, -1), -1)]

        def r20(sid, T, cut=None):
            s = ST[sid]
            if T not in s["posset"]:
                return np.nan
            b = bars_le(sid, T, 21)
            if len(b) < 21:
                return np.nan
            if any(p in s["badpos"] for p in b[:20]):          # (b−20, b] 內有壞 K 棒
                return np.nan
            c = s["c"] if cut is None else np.where(np.arange(len(s["c"])) <= cut, s["c"], np.nan)
            return c[b[0]] / c[b[20]] - 1.0

        def gate(sid, T):
            s = ST[sid]
            if T < 20:
                return False
            v = s["vol"][T - 20:T]
            return bool(s["trd"][T - 19:T + 1].all() and np.isfinite(v).all() and v.mean() >= 500_000 and W["PV"][ixd[sid]][T])

        def t1ok(sid, T):
            s = ST[sid]; j = ixd[sid]; e = T + 1
            return bool(T in s["posset"] and e in s["posset"] and e not in s["badpos"] and W["TRD"][j][e] and np.isfinite(W["O"][j][e])
                        and W["O"][j][e] > 0 and not W["UPL"][j][e])

        def brk(sid, T, H):
            s = ST[sid]
            if T + H > n0 - 1:
                return True
            for p in range(T + 1, T + H + 1):
                if p in s["badpos"]:
                    return True
            idx = s["idx"]; last = [k for k in range(len(idx)) if idx[k] <= T + H]
            if last:
                kH = last[-1]
                if kH < len(idx) - 1 and idx[kH + 1] - idx[kH] - 1 >= 5 and (T + H) - idx[kH] >= 5:
                    return True
            return False

        def Rof(sid, T, H):
            s = ST[sid]
            if T + H > n0 - 1 or (T + 1) not in s["posset"] or not (np.isfinite(s["o"][T + 1]) and s["o"][T + 1] > 0):
                return np.nan
            j = T + H
            while j >= 0 and j not in s["posset"]:
                j -= 1
            v = s["c"][j] / s["o"][T + 1] - 1.0
            return 0.0 * v if a.dry else v

        def wr_at(sid, T):
            s = ST[sid]; b = bars_le(sid, T, 14)
            hh = max(s["h"][p] for p in b); ll = min(s["l"][p] for p in b)
            return (hh - s["c"][T]) / (hh - ll) * -100.0 if hh > ll else np.nan

        def kd_at(sid, T):
            s = ST[sid]; idx = [int(p) for p in s["idx"] if p <= T]
            st = 0
            for q in range(len(idx)):
                if idx[q] in s["badpos"]:
                    st = q
            seg = idx[st:]; k0 = d0 = 50.0; KK = []; DD = []
            for t in range(len(seg)):
                if t < 8:
                    KK.append(np.nan); DD.append(np.nan); continue
                w_ = seg[t - 8:t + 1]
                lo = min(s["l"][p] for p in w_); hi = max(s["h"][p] for p in w_)
                rsv = 50.0 if hi - lo <= 0 else (s["c"][seg[t]] - lo) / (hi - lo) * 100
                k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3; KK.append(k0); DD.append(d0)
            return KK, DD, len(seg) - 1

        for sg, cell, e in picks:
            T = int(cal.searchsorted(pd.Timestamp(e["T"]))); sid0 = e["sid"]
            chk = {}
            if cell == "W":
                prevT = bars_le(sid0, T, 2)[1]
                a_, b_ = wr_at(sid0, prevT), wr_at(sid0, T)
                chk["訊號 %R[T−1]<−80≤%R[T]"] = bool(a_ < -80 <= b_)
            else:
                KK, DD, pos = kd_at(sid0, T)
                chk["訊號 K上穿D且K≤30、段內≥30"] = bool(KK[-2] <= DD[-2] and KK[-1] > DD[-1] and KK[-1] <= 30 and pos >= 30)
            chk["母體"] = gate(sid0, T); chk["T+1可買"] = t1ok(sid0, T)
            chk["進場日＝日曆T+1"] = str(cal[T + 1].date()) == e["進場日"]
            # K5 不前視：截在 T
            rv_full = r20(sid0, T); rv_cut = r20(sid0, T, cut=T)
            chk["r20 截在T相同"] = bool(rv_full == rv_cut and abs(rv_full - float(e["r20"])) <= TOL)
            for H in (20, 60):
                fH = EVD[(wn, sg, cell, H)]; row = fH[(fH["sid"] == sid0) & (fH["T"] == e["T"])]
                if not len(row) or row.iloc[0]["配對"] != "有":
                    continue
                row = row.iloc[0]
                chk[f"出場日＝日曆T+{H}"] = str(cal[T + H].date()) == row["出場日"]
                vals = {}
                for sid in ST:
                    if gate(sid, T):
                        v = r20(sid, T)
                        if np.isfinite(v):
                            vals[sid] = v
                sr = pd.Series(vals)
                dec = pd.qcut(sr.rank(method="first"), 10, labels=False)
                d0_ = dec[sid0]
                ctrl = []
                for sid in dec.index:
                    if sid == sid0 or dec[sid] != d0_:
                        continue
                    if (sid, str(cal[T].date())) in RAW[cell]:
                        continue
                    if not t1ok(sid, T) or brk(sid, T, H):
                        continue
                    g = Rof(sid, T, H)
                    if np.isfinite(g):
                        ctrl.append(g)
                r0 = Rof(sid0, T, H); cm = float(np.mean(ctrl)) if ctrl else np.nan
                d1 = abs(r0 - float(row["R"])); d2 = abs(cm - float(row["對照平均"])); d3 = abs((r0 - cm) - float(row["X"]))
                w4 = max(w4, d1, d2, d3)
                chk[f"H{H} R同"] = bool(d1 <= TOL); chk[f"H{H} 對照平均同"] = bool(d2 <= TOL); chk[f"H{H} X同"] = bool(d3 <= TOL)
                chk[f"H{H} 對照數同"] = bool(len(ctrl) == int(row["對照數"])); chk[f"H{H} 十分位同"] = bool(int(d0_) == int(row["十分位"]))
                chk[f"H{H} 自身無斷點"] = not brk(sid0, T, H)
                chk[f"H{H} 手算"] = {"R": r0, "對照平均": cm, "對照數": len(ctrl)}
            okall = all(v for v in chk.values() if isinstance(v, bool))
            res4.append({"世界": wn, "段": sg, "格": cell, "sid": sid0, "T": e["T"], "全同": okall, **chk})
            log(f"K4 {res4[-1]}")
    CHK["K4／K5 抽樣逐根手算（含不前視）"] = {"筆數": len(res4), "最大差": w4, "全同": all(x["全同"] for x in res4), "明細": res4}
    CHK["全部過"] = bool(CHK["K1 主表重算"]["過"] and CHK["K2 假訊號 x／30 與 seq322"]["過"] and CHK["K3 W−K 差、描述格、週線"]["過"]
                     and CHK["K4／K5 抽樣逐根手算（含不前視）"]["全同"])
    json.dump(CHK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("全部過" if CHK["全部過"] else "⛔ 有不同")
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

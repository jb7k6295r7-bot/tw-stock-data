# -*- coding: utf-8 -*-
"""KDJ 三週期共振 seq1 事件層 獨立對帳（⛔ 不 import researchKDJ3、researchKDJ3_freq、researchWR、researchWR_freq、researchPatC、researchWeekly
任何一行；只 import 資料層：researchAscTri_freq.load_world（世界、pit_valid、T＋1 旗標、壞根來源）、research11.load_bars（有效 K 棒、壞根）；
原始偵測／保留狀態取已提交的頻率表 resultsKDJ3/freq/events_<世界>.csv.gz）。本體跑完後：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchKDJ3_check [--sample 20]

C1 彙總重算：從逐筆檔 events/trades_<世界>_<段>_<格>_H<H>.csv.gz 重算 KDJ3_main.csv 每一列（X ＝ R − 對照平均、n、X̄、中位、X 勝率、
   CR0 分群 SE（自己寫；H20 曆月、H60／H120 (T−段起點)//H）、CI、n_eff、出口、結果、X̄ − 0.585%、淨報酬平均、勝率）⇒ 逐列比（≤ 1e−9、標籤同）；
   逐筆列數 ＝ 頻率表 freq.csv「事件數(保留)」。
C2 假訊號臂：fake_acc.npz 逐群 (n, Σ) 自己重算 30 次 × 兩版 ⇒ x／30；seq322 五條自己重判。
C3 J − D 差（自己寫的曆月線性化 SE）；重疊（急跌錯殺、大盤大跌）從逐筆檔＋來源檔自己重數；空頭年占比從頻率表事件檔自己重數。
C4 抽 --sample 筆（主：J 8、D 2；早年：J 8、D 2；探索／確認輪流；種子 20261021）逐根手算：日線 KD（逐段迴圈）、週／月 K（自寫日曆週（週一起算）／
   日曆月分組、已收完規則、壞根分段與作廢、段內位置 ≥ 20、同段）⇒ 訊號條件；母體（自算 500 張閘）、T＋1 可買、r60、R（H20／60／120）；
   對照：全市場逐檔獨立重建（r60 十分位 ＝ pd.qcut(rank(first), 10)、原始偵測取頻率表事件檔、硬斷點逐日掃）⇒ 與逐筆檔比。
C5 不前視：同一批，把資料截在 T（⛔ 不看 T 之後）重算日 KD、週月 K、r60 ⇒ 與全序列相同；進場日 ＝ 日曆 T＋1、出場日 ＝ 日曆 T＋H。
結果寫 resultsKDJ3/check.json、check.log。
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
OUT = "backtest/resultsKDJ3"
FREQ = "backtest/resultsKDJ3/freq"
TOL = 1e-9
COST = 0.00585
Z95 = 1.96
HS = (20, 60, 120)
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
    pos = cal.searchsorted(pd.to_datetime(pd.Series(list(Tstr))))
    if H == 20:
        return [cal[p].year * 12 + cal[p].month for p in pos]
    return [(int(p) - p0) // H for p in pos]


# ═════════════ C1／C2／C3a 共用（三重底件 import）═════════════
def check_main(MAIN, FQ, cals, out, fq_cell_map=None, judge="J"):
    worst = 0.0; nrow = 0; bad = []; EVD = {}; samesign = {}
    for _, r in MAIN.iterrows():
        wn, sg, cell, H = r["世界"], r["段"], r["格"], int(r["H"])
        cal = cals[wn]; p0 = p0_of(cal, wn, sg)
        fr = pd.read_csv(os.path.join(out, "events", f"trades_{wn}_{sg}_{cell}_H{H}.csv.gz"), dtype={"sid": str})
        EVD[(wn, sg, cell, H)] = fr
        nf = int(FQ[(FQ["世界"] == wn) & (FQ["段"] == sg) & (FQ["格"] == cell)]["事件數(保留)"].iloc[0])
        if len(fr) != nf or int(r["保留"]) != nf:
            bad.append((wn, sg, cell, H, "列數", len(fr), nf))
        x = (fr["R"] - fr["對照平均"]).to_numpy()
        ok = (fr["配對"] == "有").to_numpy()
        if not (np.isfinite(fr["X"].to_numpy()) == ok).all():
            bad.append((wn, sg, cell, H, "配對與X有值不一致"))
        if ok.any():
            worst = max(worst, float(np.max(np.abs(x[ok] - fr["X"].to_numpy()[ok]))))
        Rv = fr["R"].to_numpy()[ok]; x = x[ok]; k = keyof(cal, fr["T"][ok], H, p0)
        if len(x) == 0:
            if int(r["n"]) != 0:
                bad.append((wn, sg, cell, H, "n", r["n"], 0))
            continue
        m, se, ng, _ = cr0(x, k); ne = min(len(x), ng); ex, rs = lab(m, se, ne)
        net = Rv - COST
        mine = {"n": len(x), "X̄": m, "中位": float(np.median(x)), "X勝率": float((x > 0).mean()), "se": se, "lo": m - Z95 * se, "hi": m + Z95 * se,
                "n_eff": ne, "X̄扣成本": m - COST, "淨報酬平均(R−0.585%)": float(net.mean()), "勝率(淨>0)": float((net > 0).mean())}
        for kk, v in mine.items():
            d = abs(float(r[kk]) - v); worst = max(worst, d)
            if d > TOL:
                bad.append((wn, sg, cell, H, kk, float(r[kk]), v))
        if r["結果"] != rs or r["出口"] != ex:
            bad.append((wn, sg, cell, H, "標籤", r["結果"], rs))
        if H == 20 and cell == judge:
            mm = pd.Series(x).groupby(k).mean()
            samesign[(wn, sg)] = bool(np.sign(mm.median()) == np.sign(m))
        nrow += 1
    return {"列數": nrow, "最大差": worst, "不同": bad[:20], "過": not bad}, EVD, samesign


def check_fake(MAIN, out, samesign):
    Z = np.load(os.path.join(out, "fake_acc.npz"))
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
                mine322 = bool(r["結果"] == "結果②" and float(r["bonf_lo"]) > 0 and x2 <= 1 and float(r["X̄扣成本"]) > 0 and samesign.get((wn, sg), False))
                g322[str(key)] = mine322
                if mine322 != (str(r["過seq322門檻"]) == "True"):
                    bad2.append((str(key), "seq322", mine322, r["過seq322門檻"]))
    return {"格數": int(len(Z["keys"])), "seq322自判": g322, "不同": bad2, "過": not bad2}


def check_diff(DIFF, EVD, cals, a_cell, b_cell, keyname, colmap):
    bad3 = []; w3 = 0.0; nrow = 0
    for _, r in DIFF.iterrows():
        if keyname and r.get("比較") != keyname:
            continue
        wn, sg, H = r["世界"], r["段"], int(r["H"]); cal = cals[wn]; p0 = p0_of(cal, wn, sg)
        f1 = EVD[(wn, sg, a_cell, H)]; f2 = EVD[(wn, sg, b_cell, H)]
        f1 = f1[f1["配對"] == "有"]; f2 = f2[f2["配對"] == "有"]
        if not len(f1) or not len(f2):
            continue
        m1, m2 = f1["X"].mean(), f2["X"].mean(); acc = {}
        for x, g in zip(f1["X"], keyof(cal, f1["T"], H, p0)):
            acc[g] = acc.get(g, 0.0) + (x - m1) / len(f1)
        for x, g in zip(f2["X"], keyof(cal, f2["T"], H, p0)):
            acc[g] = acc.get(g, 0.0) - (x - m2) / len(f2)
        se = math.sqrt(sum(v * v for v in acc.values()))
        for kk, v in ((colmap["差"], m1 - m2), ("se", se), ("lo", m1 - m2 - Z95 * se), ("hi", m1 - m2 + Z95 * se)):
            d = abs(float(r[kk]) - v); w3 = max(w3, d)
            if d > TOL:
                bad3.append((wn, sg, H, keyname, kk, float(r[kk]), v))
        nrow += 1
    return nrow, w3, bad3


# ═════════════ 逐根手算工具 ═════════════
class Mkt:
    """全市場逐檔資料（只用資料層）。"""

    def __init__(self, wn):
        import backtest.data as D
        W = AT.load_world(wn); self.W = W; self.cal = W["cal"]; self.n0 = W["n0"]; self.ix = W["ix"]
        D.DATA = W["data"]
        self.ST = {}
        for sid in W["sids"]:
            B = R11.load_bars(sid, W["mk"].get(sid, "twse"), self.cal)
            if B is None:
                continue
            df = B["df"]; idx = B["idx"].astype(np.int64)
            badk = set(int(k) for k in np.flatnonzero(B["next_bad"][:len(idx)] == np.arange(len(idx))))
            for p_ in W["BADPOS"].get(sid, ()):
                k = int(np.searchsorted(idx, p_, "left"))
                if k < len(idx):
                    badk.add(k)
            self.ST[sid] = {"c": df["close"].to_numpy(float), "o": df["open"].to_numpy(float), "h": df["high"].to_numpy(float),
                            "l": df["low"].to_numpy(float), "trd": df["traded"].to_numpy(bool),
                            "vol": pd.to_numeric(df["volume"], errors="coerce").to_numpy(float),
                            "idx": idx, "posset": set(int(p) for p in idx), "badk": badk, "badpos": set(int(idx[k]) for k in badk)}

    def bars_le(self, sid, T, n):
        idx = self.ST[sid]["idx"]; k = int(np.searchsorted(idx, T, "right")) - 1
        return [int(idx[j]) for j in range(k, max(k - n, -1), -1)]

    def gate(self, sid, T):
        s = self.ST[sid]
        if T < 20:
            return False
        v = s["vol"][T - 20:T]
        return bool(s["trd"][T - 19:T + 1].all() and np.isfinite(v).all() and v.mean() >= 500_000 and self.W["PV"][self.ix[sid]][T])

    def t1ok(self, sid, T):
        s = self.ST[sid]; j = self.ix[sid]; e = T + 1; W = self.W
        return bool(T in s["posset"] and e in s["posset"] and e not in s["badpos"] and W["TRD"][j][e] and np.isfinite(W["O"][j][e])
                    and W["O"][j][e] > 0 and not W["UPL"][j][e])

    def brk(self, sid, a, b):
        """(a, b] 有壞 K 棒或 b 落在 ≥ 5 日缺口；b 超出資料尾 ⇒ True。"""
        s = self.ST[sid]
        if b > self.n0 - 1:
            return True
        for p in range(a + 1, b + 1):
            if p in s["badpos"]:
                return True
        idx = s["idx"]; kH = int(np.searchsorted(idx, b, "right")) - 1
        if 0 <= kH < len(idx) - 1 and idx[kH + 1] - idx[kH] - 1 >= 5 and b - idx[kH] >= 5:
            return True
        return False

    def Rof(self, sid, T, H, dry=False):
        s = self.ST[sid]
        if T + H > self.n0 - 1 or (T + 1) not in s["posset"] or not (np.isfinite(s["o"][T + 1]) and s["o"][T + 1] > 0):
            return np.nan
        j = T + H
        while j >= 0 and j not in s["posset"]:
            j -= 1
        v = s["c"][j] / s["o"][T + 1] - 1.0
        return 0.0 * v if dry else v

    def rN_T(self, sid, T, N=60, cut=False):
        """c[b]÷c[b−N]−1，(b−N, b] 無壞 K 棒。"""
        s = self.ST[sid]
        if T not in s["posset"]:
            return np.nan
        b = self.bars_le(sid, T, N + 1)
        if len(b) < N + 1 or any(p in s["badpos"] for p in b[:N]):
            return np.nan
        c = s["c"] if not cut else np.where(np.arange(len(s["c"])) <= T, s["c"], np.nan)
        return c[b[0]] / c[b[N]] - 1.0

    def rN_pre(self, sid, f, N=60, cut=None):
        """c[f−1 根]÷c[f−1−N 根]−1，(f−1−N, f−1] 根無壞 K 棒（型態第一點錨點）。"""
        s = self.ST[sid]
        if f not in s["posset"]:
            return np.nan
        b = self.bars_le(sid, f, N + 2)
        if len(b) < N + 2 or any(p in s["badpos"] for p in b[1:N + 1]):
            return np.nan
        c = s["c"] if cut is None else np.where(np.arange(len(s["c"])) <= cut, s["c"], np.nan)
        return c[b[1]] / c[b[N + 1]] - 1.0


def kd_loop(C, H, L):
    k0 = d0 = 50.0; K = []; D = []
    for t in range(len(C)):
        if t < 8:
            K.append(np.nan); D.append(np.nan); continue
        lo = min(L[t - 8:t + 1]); hi = max(H[t - 8:t + 1])
        rsv = 50.0 if hi - lo <= 0 else (C[t] - lo) / (hi - lo) * 100
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3
        K.append(k0); D.append(d0)
    return K, D


def daily_kd(M, sid, T, cut_at=None):
    """⇒ K[k−1], D[k−1], K[k], D[k], 段內位置 pos[k], pos[k−1]（k ＝ T 那根）。"""
    s = M.ST[sid]; idx = [int(p) for p in s["idx"] if cut_at is None or p <= cut_at]
    k = idx.index(T)
    st = max([q for q in range(1, k + 1) if q in s["badk"]], default=0)
    seg = idx[st:k + 1]
    K, D = kd_loop([s["c"][p] for p in seg], [s["h"][p] for p in seg], [s["l"][p] for p in seg])
    pk = len(seg) - 1
    return K[-2] if pk >= 1 else np.nan, D[-2] if pk >= 1 else np.nan, K[-1], D[-1], pk, (pk - 1 if pk >= 1 else -1)


def period_k(M, sid, T, kind, cut_at=None):
    """週（月）K：已收完規則、壞根分段（週月首根壞 ⇒ 該週月起新段；週月內壞 ⇒ 作廢、下一週月起新段）、段內位置、同段。
    ⇒ (K, D, 段內位置, 同段, 所用週月第一根日曆位置)。"""
    cal = M.cal; s = M.ST[sid]
    if kind == "w":
        keyc = np.asarray((cal - pd.to_timedelta(cal.weekday, unit="D")).normalize().asi8)
    else:
        keyc = np.asarray(cal.year * 12 + cal.month)
    lastday = {}
    for p, kk in enumerate(keyc):
        lastday[kk] = p
    idx = [int(p) for p in s["idx"] if cut_at is None or p <= cut_at]
    kT = idx.index(T)
    gT = keyc[T]
    gmax_closed = (lastday[gT] == T)
    pkeys = []; pbars = []
    for q, p in enumerate(idx):
        kk = keyc[p]
        if not pkeys or pkeys[-1] != kk:
            pkeys.append(kk); pbars.append([])
        pbars[-1].append(q)
    sel = None
    for j, kk in enumerate(pkeys):
        if kk < gT or (kk == gT and gmax_closed):
            sel = j
    if sel is None:
        return np.nan, np.nan, -1, False, -1
    npb = len(pkeys)
    cutf = [False] * (npb + 1); inval = [False] * npb; cutf[0] = True
    for j, qs in enumerate(pbars):
        for q in qs:
            if q == 0 or q not in s["badk"]:
                continue
            if q == qs[0]:
                cutf[j] = True
            else:
                inval[j] = True; cutf[j] = True; cutf[j + 1] = True
    starts = [j for j in range(npb) if cutf[j]]
    ends = starts[1:] + [npb]
    Kp = [np.nan] * npb; Dp = [np.nan] * npb; pos = [-1] * npb
    for a, b in zip(starts, ends):
        if inval[a]:
            continue
        Cs = [s["c"][idx[pbars[j][-1]]] for j in range(a, b)]
        Hs = [max(s["h"][idx[q]] for q in pbars[j]) for j in range(a, b)]
        Ls = [min(s["l"][idx[q]] for q in pbars[j]) for j in range(a, b)]
        k_, d_ = kd_loop(Cs, Hs, Ls)
        for t, j in enumerate(range(a, b)):
            Kp[j] = k_[t]; Dp[j] = d_[t]; pos[j] = t
    q0 = pbars[sel][0]
    same = not any(q in s["badk"] for q in range(q0 + 1, kT + 1))
    return Kp[sel], Dp[sel], pos[sel], same, idx[q0]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", type=int, default=20); ap.add_argument("--out", default=None)
    ap.add_argument("--dry", action="store_true", help="對乾跑輸出驗流程：手算 R 一律寫 0（⛔ 不讀報酬）")
    a = ap.parse_args()
    out = a.out or OUT
    MAIN = pd.read_csv(os.path.join(out, "KDJ3_main.csv"), encoding="utf-8-sig")
    DIFF = pd.read_csv(os.path.join(out, "KDJ3_diff.csv"), encoding="utf-8-sig")
    OVL = pd.read_csv(os.path.join(out, "KDJ3_overlap.csv"), encoding="utf-8-sig")
    JS = json.load(open(os.path.join(out, "KDJ3.json"), encoding="utf-8"))
    FQ = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig")
    CHK = {}
    cals = {}
    import backtest.data as D
    for wn in ("主", "早年"):
        D.DATA = AT.WORLDS[wn]["data"]; cals[wn] = D.load_calendar()
    CHK["C1 彙總重算"], EVD, samesign = check_main(MAIN, FQ, cals, out)
    log(f"C1 {CHK['C1 彙總重算']}")
    CHK["C2 假訊號 x／30 與 seq322"] = check_fake(MAIN, out, samesign)
    log(f"C2 {CHK['C2 假訊號 x／30 與 seq322']}")
    nd, w3, bad3 = check_diff(DIFF, EVD, cals, "J", "D", None, {"差": "差(J−D)"})
    # 重疊重數
    co = pd.read_csv("backtest/resultsCrashOversold/events.csv.gz", dtype=str, usecols=["sid", "日期t", "版面"])
    md = pd.read_csv("backtest/resultsMktDrop/events.csv", dtype=str); md = md[md["定義"] == "q2"]
    for _, r in OVL.iterrows():
        wn, sg = r["世界"], r["段"]; cal = cals[wn]
        fr = EVD[(wn, sg, "J", 20)]
        if len(fr) != int(r["保留"]):
            bad3.append((wn, sg, "重疊保留數", len(fr), int(r["保留"]))); continue
        cw = co[co["版面"] == ("main" if wn == "主" else "早年")]
        cset = set(zip(cw["sid"], cw["日期t"]))
        same = sum(1 for s_, t_ in zip(fr["sid"], fr["T"]) if (s_, t_) in cset)
        cpos = {}
        for s_, d_ in zip(cw["sid"], cw["日期t"]):
            ts = pd.Timestamp(d_)
            p = int(cal.searchsorted(ts))
            if p < len(cal) and cal[p] == ts:
                cpos.setdefault(s_, []).append(p)
        near = 0
        for s_, t_ in zip(fr["sid"], fr["T"]):
            p = int(cal.searchsorted(pd.Timestamp(t_)))
            if any(abs(p - q) <= 20 for q in cpos.get(s_, [])):
                near += 1
        mdp = sorted({int(cal.searchsorted(pd.Timestamp(d_))) for d_ in md["日期"] if pd.Timestamp(d_) in set(cal)})
        s1 = s2 = 0
        for t_ in fr["T"]:
            p = int(cal.searchsorted(pd.Timestamp(t_)))
            s1 += int(p in mdp); s2 += int(any(0 <= p - q <= 20 for q in mdp))
        for kk, v in (("急跌錯殺_同檔同日", same), ("急跌錯殺_同檔±20", near), ("大盤大跌q2_同日", s1), ("大盤大跌q2_之後20日內", s2)):
            if int(r[kk]) != v:
                bad3.append((wn, sg, kk, int(r[kk]), v))
    # 空頭年占比
    yc = {}
    for wn in ("主", "早年"):
        ev = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str, usecols=["格", "T", "st"])
        ev = ev[(ev["格"] == "J") & (ev["st"] == "保留")]
        for t_ in ev["T"]:
            yc[int(t_[:4])] = yc.get(int(t_[:4]), 0) + 1
    tot = sum(yc.values())
    for y in (2008, 2011, 2022):
        if JS["空頭年占比"][str(y)]["件數"] != yc.get(y, 0):
            bad3.append(("空頭年", y, JS["空頭年占比"][str(y)]["件數"], yc.get(y, 0)))
    if JS["空頭年占比"]["J保留(兩世界全期)"] != tot:
        bad3.append(("空頭年總數", JS["空頭年占比"]["J保留(兩世界全期)"], tot))
    CHK["C3 J−D 差、重疊、空頭年"] = {"差列": nd, "重疊列": len(OVL), "最大差": w3, "空頭年(自數)": {y: yc.get(y, 0) for y in (2008, 2011, 2022)},
                                  "J保留總數": tot, "不同": bad3[:20], "過": not bad3}
    log(f"C3 {CHK['C3 J−D 差、重疊、空頭年']}")
    # ── C4／C5
    rng = np.random.default_rng(20261021)
    res4 = []; w4 = 0.0
    nJ = max(1, round(a.sample * 0.4)); nD = max(1, a.sample // 2 - nJ)
    plan = {"主": [("J", nJ), ("D", nD)], "早年": [("J", nJ), ("D", nD)]}
    for wn in ("主", "早年"):
        M = Mkt(wn); cal = M.cal; n0 = M.n0
        ev = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str)
        RAW = {c: set(zip(ev[ev["格"] == c]["sid"], ev[ev["格"] == c]["T"])) for c in ("J", "D")}
        picks = []
        for cell, m in plan[wn]:
            segs = ["探索", "確認"] if wn == "主" else ["早年"]
            for q in range(m):
                sg = segs[q % len(segs)]
                f = EVD[(wn, sg, cell, 20)]; f = f[f["配對"] == "有"]
                picks.append((sg, cell, f.iloc[int(rng.integers(len(f)))]))
        for sg, cell, e in picks:
            T = int(cal.searchsorted(pd.Timestamp(e["T"]))); sid0 = e["sid"]
            erow = ev[(ev["格"] == cell) & (ev["sid"] == sid0) & (ev["T"] == e["T"])].iloc[0]
            chk = {}
            kp, dp, kk_, dk, pk, pk1 = daily_kd(M, sid0, T)
            chk["日線 K 上穿 D、K[T−1]<20、段內≥20"] = bool(kp <= dp and kk_ > dk and kp < 20 and pk >= 20 and pk1 == pk - 1)
            chk["日線 K[T−1] 與事件檔同"] = bool(abs(kp - float(erow["K[T-1]"])) <= 5e-4)
            kc = daily_kd(M, sid0, T, cut_at=T)
            chk["不前視：日 KD 截在 T 相同"] = bool(all((np.isnan(x) and np.isnan(y)) or x == y for x, y in zip(kc[:4], (kp, dp, kk_, dk))))
            for nm in ("w", "m"):
                Kv, Dv, ps, same, d0 = period_k(M, sid0, T, nm)
                cond = bool(same and ps >= 20 and np.isfinite(Kv) and Kv < 20)
                if cell == "J":
                    chk[f"{nm} K<20（已收完、段內≥20、同段）"] = cond
                fileK = erow[nm + "K"]
                if fileK not in ("", "nan") and np.isfinite(Kv):
                    chk[f"{nm} K 與事件檔同"] = bool(abs(Kv - float(fileK)) <= 5e-4)
                kc2 = period_k(M, sid0, T, nm, cut_at=T)
                chk[f"不前視：{nm} K 截在 T 相同"] = bool((np.isnan(kc2[0]) and np.isnan(Kv)) or kc2[0] == Kv)
                chk[f"{nm} 所用週月第一根 ≤ T"] = bool(d0 <= T)
            chk["母體"] = M.gate(sid0, T); chk["T+1可買"] = M.t1ok(sid0, T)
            chk["進場日＝日曆T+1"] = str(cal[T + 1].date()) == e["進場日"]
            rv = M.rN_T(sid0, T); rvc = M.rN_T(sid0, T, cut=True)
            chk["不前視：r60 截在 T 相同"] = bool(rv == rvc)
            chk["r60 同逐筆檔"] = bool(abs(rv - float(e["r60"])) <= TOL)
            vals = {}
            for sid in M.ST:
                if M.gate(sid, T):
                    v = M.rN_T(sid, T)
                    if np.isfinite(v):
                        vals[sid] = v
            dec = pd.qcut(pd.Series(vals).rank(method="first"), 10, labels=False)
            d0_ = dec[sid0]
            for H in HS:
                fH = EVD[(wn, sg, cell, H)]; row = fH[(fH["sid"] == sid0) & (fH["T"] == e["T"])]
                if not len(row) or row.iloc[0]["配對"] != "有":
                    continue
                row = row.iloc[0]
                chk[f"H{H} 出場日＝日曆T+{H}"] = str(cal[T + H].date()) == row["出場日"]
                ctrl = []
                for sid in dec.index:
                    if sid == sid0 or dec[sid] != d0_ or (sid, e["T"]) in RAW[cell]:
                        continue
                    if not M.t1ok(sid, T) or M.brk(sid, T, T + H):
                        continue
                    g = M.Rof(sid, T, H, a.dry)
                    if np.isfinite(g):
                        ctrl.append(g)
                r0 = M.Rof(sid0, T, H, a.dry); cm = float(np.mean(ctrl)) if ctrl else np.nan
                d1 = abs(r0 - float(row["R"])); d2 = abs(cm - float(row["對照平均"])); d3 = abs((r0 - cm) - float(row["X"]))
                w4 = max(w4, d1, d2, d3)
                chk[f"H{H} R同"] = bool(d1 <= TOL); chk[f"H{H} 對照平均同"] = bool(d2 <= TOL); chk[f"H{H} X同"] = bool(d3 <= TOL)
                chk[f"H{H} 對照數同"] = bool(len(ctrl) == int(row["對照數"])); chk[f"H{H} 十分位同"] = bool(int(d0_) == int(row["十分位"]))
                chk[f"H{H} 自身無斷點"] = not M.brk(sid0, T, T + H)
                chk[f"H{H} 手算"] = {"R": r0, "對照平均": cm, "對照數": len(ctrl)}
            okall = all(v for v in chk.values() if isinstance(v, bool))
            res4.append({"世界": wn, "段": sg, "格": cell, "sid": sid0, "T": e["T"], "全同": okall, **chk})
            log(f"C4 {res4[-1]}")
        del M
    CHK["C4／C5 抽樣逐根手算（含不前視）"] = {"筆數": len(res4), "最大差": w4, "全同": all(x["全同"] for x in res4), "明細": res4}
    CHK["全部過"] = bool(CHK["C1 彙總重算"]["過"] and CHK["C2 假訊號 x／30 與 seq322"]["過"] and CHK["C3 J−D 差、重疊、空頭年"]["過"]
                     and CHK["C4／C5 抽樣逐根手算（含不前視）"]["全同"])
    json.dump(CHK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("全部過" if CHK["全部過"] else "⛔ 有不同")
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchATRfilter 的獨立重算（--check）。

另一種寫法重算：SAR（AF 用「加速次數」計、不累加）、ATR（pandas ewm 接種子）、SMA（逐日切片平均）、資金費歸日（searchsorted 區間和）、
交易清單（逐日狀態機，不經「翻轉段」清單）、（A）權益（逐日 USD 帳：現金＋固定數量市值，不用每筆倍數分解）、（B）幣計錢包逐日帳、
逐筆靜態強平（直接判 E(P) ≤ MM(P)）與連續帳戶強平、假濾網前 50 次（同種子、用逐日狀態機重跑）。
與 resultsATRfilter/ATRfilter.json、ATRfilter_trades.csv 逐項比：|差| ≤ 1e−9 × max(1, |值|) 判同；交易日期、方向、留下／被擋逐字相同。
跑法：PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchATRfilter_check.py
"""
from __future__ import annotations
import os, io, json, subprocess, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RES = os.path.join(HERE, "resultsATRfilter")
J = json.load(open(os.path.join(RES, "ATRfilter.json"), encoding="utf-8"))
SHA = J["資料commit"]
END = J["資料尾"]
COINS = ["BTC", "SOL", "ETH", "BNB", "XRP", "ADA", "DOGE", "LINK", "LTC"]
WINS = [("W1", "2018-01-01", "2023-12-31"), ("W2", "2024-01-01", END)]
READS = [("main", 200), ("r1", 14)]
FEE = 0.001
FILL = 0.10 / 365.25
SEED = 20261011
NFAKE = 2000
NCHK = 50
TOL = 1e-9
CMX = {"BTC": (0.0715, 100.0, 3, 10, 3, 0.004, "BTCUSD_PERP"), "SOL": (10.0, 10.0, 30, None, 0, 0.01, "SOLUSD_PERP")}

fails = []
ncmp = 0


def same(a, b, what):
    global ncmp
    ncmp += 1
    if isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        fa = float("inf") if a == "inf" else a
        fb = float("inf") if b == "inf" else b
        if fa is None or fb is None:
            ok = fa is None and fb is None
        else:
            ok = (np.isinf(float(fa)) and np.isinf(float(fb))) or abs(float(fa) - float(fb)) <= TOL * max(1.0, abs(float(fa)))
    elif np.isinf(a) or np.isinf(b):
        ok = a == b
    else:
        ok = abs(a - b) <= TOL * max(1.0, abs(a))
    if not ok:
        fails.append(f"{what}: 主={b} 重算={a}")


def show(rel):
    r = subprocess.run(["git", "show", f"{SHA}:{rel}"], cwd=REPO, capture_output=True, text=True, check=True)
    return r.stdout


def px(sym):
    d = pd.read_csv(io.StringIO(show(f"data/crypto/{sym}.csv")), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date")
    d = d[d["date"] <= END].iloc[30:].reset_index(drop=True)
    return {"d": list(d["date"]), "o": d["open"].to_numpy(float), "h": d["high"].to_numpy(float),
            "l": d["low"].to_numpy(float), "c": d["close"].to_numpy(float),
            "sec": np.array([int(pd.Timestamp(x, tz="UTC").timestamp()) for x in d["date"]], dtype=np.int64)}


SRC = {"BTCUSDT": [("data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv", 0, 2), ("data/crypto_funding/BTCUSDT.csv", 0, 2)],
       "SOLUSDT": [("data/crypto_funding/SOLUSDT.csv", 0, 2)],
       "BTCUSD_PERP": [("data/meta/crypto_cm_funding_rest/BTCUSD_PERP.csv", 0, 1)],
       "SOLUSD_PERP": [("data/meta/crypto_cm_funding_rest/SOLUSD_PERP.csv", 0, 1)]}


def funding(kind, secs):
    hs, rs = [], []
    for rel, tc, rc in SRC[kind]:
        lines = show(rel).strip().splitlines()[1:]
        for ln in lines:
            p = ln.split(",")
            hs.append(int(p[tc]) // 1000 // 3600 * 3600); rs.append(float(p[rc]))
    seen = {}
    for h, r in zip(hs, rs):
        if h not in seen:
            seen[h] = r
    H = np.array(sorted(seen)); R = np.array([seen[h] for h in H])
    cum = np.r_[0.0, np.cumsum(R)]
    lo = np.searchsorted(H, secs, side="right")          # h > D 00:00
    hi = np.searchsorted(H, secs + 86400, side="right")  # h ≤ D+1 00:00
    f = cum[hi] - cum[lo]
    ok = (H[0] <= secs + 8 * 3600) & (H[-1] >= secs + 86400)
    return np.where(ok, f, FILL), ~ok


def sar_ref(H, L):
    n = len(H)
    res = np.full(n, np.nan); tr = np.zeros(n, int); rev = np.zeros(n, bool)
    lng = not ((L[0] - L[1]) > 0 and (L[0] - L[1]) > (H[1] - H[0]))
    cnt = 0
    ext = H[1] if lng else L[1]
    cur = L[0] if lng else H[0]
    tr[0] = 1 if lng else -1
    for i in range(1, n):
        j = max(i - 1, 1)
        pl, ph = L[j], H[j]
        if lng:
            if L[i] <= cur:
                lng = False; rev[i] = True
                cur = max(ext, ph, H[i]); res[i] = cur
                cnt = 0; ext = L[i]
                cur = max(cur + 0.02 * (ext - cur), ph, H[i])
            else:
                res[i] = cur
                if H[i] > ext:
                    ext = H[i]; cnt += 1
                af = min(0.02 + 0.02 * cnt, 0.20)
                cur = min(cur + af * (ext - cur), pl, L[i])
        else:
            if H[i] >= cur:
                lng = True; rev[i] = True
                cur = min(ext, pl, L[i]); res[i] = cur
                cnt = 0; ext = H[i]
                cur = min(cur + 0.02 * (ext - cur), pl, L[i])
            else:
                res[i] = cur
                if L[i] < ext:
                    ext = L[i]; cnt += 1
                af = min(0.02 + 0.02 * cnt, 0.20)
                cur = max(cur + af * (ext - cur), ph, H[i])
        tr[i] = 1 if lng else -1
    return res, tr, rev


def atr_ref(H, L, C, n):
    prev = pd.Series(C).shift(1)
    trs = pd.concat([pd.Series(H - L), (pd.Series(H) - prev).abs(), (pd.Series(L) - prev).abs()], axis=1).max(axis=1, skipna=False)
    out = np.full(len(C), np.nan)
    seed = trs.iloc[1:n + 1].mean()
    tail = pd.Series(np.r_[seed, trs.iloc[n + 1:].to_numpy()])
    out[n:] = tail.ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    return out


def sma_ref(C, n=200):
    out = np.full(len(C), np.nan)
    for i in range(n - 1, len(C)):
        out[i] = C[i - n + 1:i + 1].mean()
    return out


def stats(v, T):
    v = np.asarray(v, float)
    end = v[-1] / v[0]
    peak = v[0]; mdd = 0.0
    for x in v:
        peak = max(peak, x); mdd = min(mdd, x / peak - 1)
    ann = end ** (365.25 / T) - 1 if end > 0 else -1.0
    rat = ann / abs(mdd) if mdd < 0 else (float("inf") if ann > 0 else 0.0)
    return end - 1, ann, mdd, rat


def engine_A(P, fu, i0, i1, ok):
    """逐日狀態機；ok(t, dir) 決定翻轉 t 是否進場。回 (權益序列, 交易清單)。"""
    o, c = P["o"], P["c"]
    V = 1.0; pos = 0; qty = 0.0; Pe = 0.0; ent = -1; dead = False
    eq = [1.0]; trades = []
    for d in range(i0, i1 + 1):
        if P["rev"][d - 1] and (pos != 0 or d - 1 >= i0):     # 爆倉後仍照記交易清單（權益 0）
            if pos != 0:
                V = V + pos * qty * (o[d] - Pe) - FEE * qty * o[d]
                trades[-1]["x"] = d
                pos = 0
            nd = int(P["tr"][d - 1])
            if d - 1 >= i0 and ok(d - 1, nd):
                Pe = o[d]; qty = V / Pe; V = V - FEE * qty * Pe; pos = nd; ent = d
                trades.append({"t": d - 1, "dir": nd, "e": d, "x": None})
        if dead:
            eq.append(0.0); continue
        if pos != 0:
            ref = Pe if d == ent else c[d - 1]
            V -= pos * fu[d] * qty * ref
            m = V + pos * qty * (c[d] - Pe)
            if m <= 0:
                dead = True; eq.append(0.0); continue
            eq.append(m)
        else:
            eq.append(V)
    return eq, trades


def engine_B(P, fc, i0, i1, ok, N, W0):
    o, c = P["o"], P["c"]
    W = W0; pos = 0; Pe = 0.0; ent = -1
    path = [W0]; lsum = {1: 0.0, -1: 0.0}; tstart = 0.0
    for d in range(i0, i1 + 1):
        if P["rev"][d - 1] and (pos != 0 or d - 1 >= i0):
            if pos != 0:
                W += pos * N * (1 / Pe - 1 / o[d]) - FEE * N / o[d]
                lsum[pos] += W - tstart
                pos = 0
            nd = int(P["tr"][d - 1])
            if d - 1 >= i0 and ok(d - 1, nd):
                tstart = W
                Pe = o[d]; W -= FEE * N / Pe; pos = nd; ent = d
        if pos != 0:
            ref = Pe if d == ent else c[d - 1]
            W -= pos * fc[d] * N / ref
            path.append(W + pos * N * (1 / Pe - 1 / c[d]))
        else:
            path.append(W)
    if pos != 0:
        lsum[pos] += path[-1] - tstart
    return path, lsum


def liq_trade(P, fc, tr, N, Nr, W0, mmr):
    o, c, lo, hi = P["o"], P["c"], P["l"], P["h"]
    e = tr["e"]; last = (tr["x"] - 1) if tr["x"] is not None else tr["i1"]; s = tr["dir"]
    Pe = o[e]; W = W0 - FEE * N / Pe
    best = float("inf")
    for d in range(e, last + 1):
        ref = Pe if d == e else c[d - 1]
        W -= fc[d] * (Nr + s * N) / ref
        def E(p):
            return W + Nr * (1 / Pe - 1 / p) + s * N * (1 / Pe - 1 / p)
        def MM(p):
            return mmr * (Nr + N) / p
        num = Nr + s * N + mmr * (Nr + N)
        den = W + (Nr + s * N) / Pe
        hit = E(lo[d]) <= MM(lo[d]) or E(hi[d]) <= MM(hi[d])
        if den > 0 and num > 0:
            dist = lo[d] / (num / den) - 1
        elif den < 0 and num < 0:
            dist = (num / den) / hi[d] - 1
        elif num <= 0 and den >= 0:
            dist = float("inf")
        else:
            dist = -1.0
        assert hit == (dist <= 0), "強平：不等式判定與距離不一致"
        best = min(best, dist)
    return best


def liq_acc(P, fc, i0, i1, trades, N, Nr, W0, mmr, signals=True):
    o, c, lo, hi = P["o"], P["c"], P["l"], P["h"]
    W = W0; Pr = o[i0]
    if Nr:
        W -= FEE * Nr / Pr
    E = {t["e"]: t for t in trades} if signals else {}
    cur = None; best = float("inf"); day = None; Pe = 0.0
    for d in range(i0, i1 + 1):
        if cur is not None and cur["x"] == d:
            W += cur["dir"] * N * (1 / Pe - 1 / o[d]) - FEE * N / o[d]; cur = None
        if d in E:
            cur = E[d]; Pe = o[d]; W -= FEE * N / Pe
        W -= fc[d] * Nr / (Pr if d == i0 else c[d - 1])
        pos = [(Nr, Pr)] if Nr else []
        if cur is not None:
            W -= fc[d] * cur["dir"] * N / (Pe if d == cur["e"] else c[d - 1])
            pos.append((cur["dir"] * N, Pe))
        if not pos:
            continue
        num = sum(n for n, _ in pos) + mmr * sum(abs(n) for n, _ in pos)
        den = W + sum(n / p for n, p in pos)
        if den > 0 and num > 0:
            dist = lo[d] / (num / den) - 1
        elif den < 0 and num < 0:
            dist = (num / den) / hi[d] - 1
        elif num <= 0 and den >= 0:
            dist = float("inf")
        else:
            dist = -1.0
        best = min(best, dist)
        if dist <= 0:
            day = P["d"][d]; break
    return best, day


def main():
    import researchATRfilter as M
    tcsv = pd.read_csv(os.path.join(RES, "ATRfilter_trades.csv"), dtype={"t": str, "entry": str, "exit": str})
    G = J["格"]
    for ci, sym in enumerate(COINS):
        P = px(sym)
        P["sar"], P["tr"], P["rev"] = sar_ref(P["h"], P["l"])
        sma = sma_ref(P["c"])
        atr = {n: atr_ref(P["h"], P["l"], P["c"], n) for _, n in READS}
        # 與主程式的指標逐日比
        s2, p2, f2 = M.sar_talib(P["h"], P["l"])
        assert (p2 == P["tr"]).all() and (f2 == P["rev"]).all(), f"{sym} SAR 方向／翻轉不同"
        msk = ~np.isnan(P["sar"])
        assert np.allclose(s2[msk], P["sar"][msk], rtol=TOL, atol=0), f"{sym} SAR 值不同"
        ms = pd.Series(P["c"]).rolling(200).mean().to_numpy()
        same(float(np.nanmax(np.abs(ms - sma) / np.maximum(1, np.abs(sma)))), 0.0, f"{sym} SMA 最大相對差")
        for _, n in READS:
            ma = M.atr_wilder(P["h"], P["l"], P["c"], n)
            same(float(np.nanmax(np.abs(ma - atr[n]) / np.maximum(1, np.abs(atr[n])))), 0.0, f"{sym} ATR{n} 最大相對差")
        fu, fum = funding("BTCUSDT", P["sec"])
        variants = [("BTCUSDT", fu, fum)]
        if sym == "SOL":
            variants.append(("SOLUSDT",) + funding("SOLUSDT", P["sec"]))
        fc = fcm = None
        if sym in CMX:
            fc, fcm = funding(CMX[sym][6], P["sec"])
        iv = 200
        for wi, (wn, a, b) in enumerate(WINS):
            i0 = max(int(np.searchsorted(P["d"], a)), iv)
            i1 = int(np.searchsorted(P["d"], b, side="right")) - 1
            if i1 - i0 < 30:
                continue
            T = i1 - i0 + 1
            for ri, (rn, n) in enumerate(READS):
                if sym not in ("BTC", "SOL") and rn != "main":
                    continue
                for fk, fu_, fm_ in variants:
                    if fk == "SOLUSDT" and rn != "main":
                        continue
                    for k in (1, 2, 3):
                        key = f"{sym}|{wn}|{rn}|k{k}|{fk}"
                        g = G[key]
                        U = sma + k * atr[n]; D = sma - k * atr[n]
                        filt = lambda t, dr: (P["c"][t] > U[t]) if dr > 0 else (P["c"][t] < D[t])
                        allok = lambda t, dr: True
                        eqU, trU = engine_A(P, fu_, i0, i1, allok)
                        eqF, trF = engine_A(P, fu_, i0, i1, filt)
                        for arm, okf, eq in (("不加", allok, eqU), ("加", filt, eqF)):
                            for side, sd in (("合計", 0), ("多", 1), ("空", -1)):
                                if sd == 0:
                                    v = eq
                                else:
                                    v, _ = engine_A(P, fu_, i0, i1, (lambda t, dr, okf=okf, sd=sd: dr == sd and okf(t, dr)))
                                st = stats(v, T)
                                ref = g[arm][side]
                                for nm, x in zip(("總損益", "年化", "MDD", "年化÷|MDD|"), st):
                                    same(x, ref[nm], f"{key} {arm} {side} {nm}")
                        # 被擋單
                        keptset = {t["t"] for t in trF}
                        # 每筆報酬用閉式（與主程式不同路徑）：權益在 x 開盤平倉後的現金
                        rr = []
                        for t in trU:
                            Pe = P["o"][t["e"]]; q = 1 / Pe; V = 1 - FEE
                            last = (t["x"] - 1) if t["x"] is not None else i1
                            for d in range(t["e"], last + 1):
                                V -= t["dir"] * fu_[d] * q * (Pe if d == t["e"] else P["c"][d - 1])
                                if V + t["dir"] * q * (P["c"][d] - Pe) <= 0:
                                    V = None; break
                            if V is None:
                                rr.append(-1.0); continue
                            if t["x"] is not None:
                                V = V + t["dir"] * q * (P["o"][t["x"]] - Pe) - FEE * q * P["o"][t["x"]]
                                rr.append(max(V, 0.0) - 1)
                            else:
                                rr.append(V + t["dir"] * q * (P["c"][i1] - Pe) - 1)
                        rr = np.array(rr); blk = np.array([t["t"] not in keptset for t in trU])
                        same(float(blk.mean()), g["被擋單"]["占比"], f"{key} 被擋占比")
                        same(float((rr[blk] > 0).mean()) if blk.any() else None, g["被擋單"]["賺錢比例"], f"{key} 被擋賺錢比例")
                        same(float(rr[blk].sum()), g["被擋單"]["Σ每筆報酬"], f"{key} 被擋Σ報酬")
                        same(float(rr[~blk].sum()), g["留下單"]["Σ每筆報酬"], f"{key} 留下Σ報酬")
                        hp = np.r_[P["c"][i0 - 1], P["c"][i0:i1 + 1]]
                        for nm, x in zip(("總損益", "年化", "MDD", "年化÷|MDD|"), stats(hp, T)):
                            same(x, g["只抱現貨_A"][nm], f"{key} 現貨 {nm}")
                        same(int(fm_[i0:i1 + 1].sum()), g["窗"]["資金費代入天數_窗內"], f"{key} 代入天數")
                        # 交易清單逐字
                        if sym in ("BTC", "SOL") and fk == "BTCUSDT":
                            sub = tcsv[(tcsv.coin == sym) & (tcsv.window == wn) & (tcsv.reading == rn) & (tcsv.k == k)].reset_index(drop=True)
                            assert len(sub) == len(trU), f"{key} 交易筆數 {len(sub)} vs {len(trU)}"
                            for j, t in enumerate(trU):
                                row = sub.iloc[j]
                                assert row["t"] == P["d"][t["t"]] and int(row["dir"]) == t["dir"] and row["entry"] == P["d"][t["e"]], f"{key} 第{j}筆不同"
                                ex_ = P["d"][t["x"]] if t["x"] is not None else ""
                                assert (row["exit"] if isinstance(row["exit"], str) else "") == ex_, f"{key} 第{j}筆出場不同"
                                assert int(row["kept"]) == int(t["t"] in keptset), f"{key} 第{j}筆留下／被擋不同"
                                same(rr[j], float(row["ret_unit"]), f"{key} 第{j}筆報酬")
                                same(float(U[t["t"]]), float(row["U_t"]), f"{key} 第{j}筆 U")
                                same(float(D[t["t"]]), float(row["D_t"]), f"{key} 第{j}筆 D")
                        # 幣本位與強平
                        if sym in CMX and fk == "BTCUSDT":
                            W0, FACE, n1, n2, res_, mmr, _ = CMX[sym]
                            for tag, nn in (("主", n1), ("敏感度", n2)):
                                if nn is None:
                                    continue
                                N = nn * FACE; Nr = res_ * FACE
                                for arm, okf in (("不加", allok), ("加", filt)):
                                    path, ls = engine_B(P, fc, i0, i1, okf, N, W0)
                                    cs = g[f"幣本位_{tag}"][arm]
                                    same(path[-1] - W0, cs["幣計總損益"], f"{key} {tag} {arm} 幣計總損益")
                                    same(ls[1], cs["多單幣計"], f"{key} {tag} {arm} 多單幣計")
                                    same(ls[-1], cs["空單幣計"], f"{key} {tag} {arm} 空單幣計")
                                    pk = path[0]; md = 0.0
                                    for x in path:
                                        pk = max(pk, x); md = min(md, x / pk - 1)
                                    same(md, cs["幣數路徑MDD"], f"{key} {tag} {arm} 幣數MDD")
                                    trs = trF if arm == "加" else trU
                                    dists = [liq_trade(P, fc, dict(t, i1=i1), N, Nr, W0, mmr) for t in trs]
                                    fin = [x for x in dists if np.isfinite(x)]
                                    ls_ = g[f"強平_{tag}"][f"靜態_{arm}"]
                                    same(min(fin) if fin else None, ls_["最近距離最小"], f"{key} {tag} {arm} 靜態最近距離")
                                    same(sum(x <= 0 for x in dists), ls_["觸及筆數"], f"{key} {tag} {arm} 觸及筆數")
                                    if tag == "主" and arm == "不加" and fk == "BTCUSDT":
                                        sub = tcsv[(tcsv.coin == sym) & (tcsv.window == wn) & (tcsv.reading == rn) & (tcsv.k == k)].reset_index(drop=True)
                                        for j, x in enumerate(dists):
                                            same(x, float(sub.iloc[j]["liq_min_dist"]), f"{key} 第{j}筆強平距離")
                                    bst, dy = liq_acc(P, fc, i0, i1, trs, N, Nr, W0, mmr)
                                    ac = g[f"強平_{tag}"]["連續帳戶"][arm]
                                    same(bst, ac["全窗最近距離"], f"{key} {tag} {arm} 連續帳戶最近距離")
                                    assert dy == ac["強平日"], f"{key} {tag} {arm} 強平日不同"
                                if res_:
                                    bst, dy = liq_acc(P, fc, i0, i1, [], N, Nr, W0, mmr, signals=False)
                                    same(bst, g[f"強平_{tag}"]["連續帳戶"]["只有常駐單"]["全窗最近距離"], f"{key} {tag} 只有常駐單")
                        # 假濾網前 50 次
                        if sym in ("BTC", "SOL") and fk == "BTCUSDT" and rn == "main":
                            Jn = len(trU); bcount = int(blk.sum())
                            rng = np.random.default_rng([SEED, ci, wi, k, ri])
                            Ur = rng.random((NFAKE, Jn))
                            ts = [t["t"] for t in trU]
                            for si in range(NCHK):
                                bl = set(np.array(ts)[np.argsort(Ur[si])[:bcount]].tolist()) if bcount else set()
                                v, _ = engine_A(P, fu_, i0, i1, (lambda t, dr, bl=bl: t not in bl))
                                same(stats(v, T)[3], g["假濾網"]["前50次"][si], f"{key} 假濾網第{si}次")
        print(sym, "checked", flush=True)
    print(f"比對 {ncmp} 項；不同 {len(fails)} 項")
    for f in fails[:40]:
        print("  ✗", f)
    if fails:
        sys.exit(1)
    print("✅ 全部相同（≤1e−9）")


if __name__ == "__main__":
    main()

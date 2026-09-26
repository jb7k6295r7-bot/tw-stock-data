# -*- coding: utf-8 -*-
"""researchQuad 的獨立查核（⛔ 不 import researchQuad）。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchQuad_check.py [--n 600] [--out backtest/resultsQuad]

① 從 explore_diffs／confirm_diffs 自己重算：平均、以進場月分群的 CR0 標準誤、CI、n_eff、出口／結果、觸發比例、上市／上櫃平均、分年平均、放棄組 ⇒ 對 cells 檔
② 自己重挑每類最好的一種（平均最高；同分取觸發比例較低；再同取規則序）、平均 ≤ 0 ⇒ 不進確認 ⇒ 對 summary.json
③ 抽 n 筆持有，用【逐日迴圈】的寫法（狀態機，⛔ 不用主程式的向量化線）重算每一種規則的配對差與觸發 ⇒ 對 diffs 檔（容差 1e−12）
④ 筆數：diffs 列數 ＝ pre.json 的保留數；段的界線（整筆落在段內）逐列驗；無重複持有
"""
from __future__ import annotations
import argparse, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchAvg as RA                      # 只用 prep（資料讀取）；D.DATA ⇒ 快照
from backtest import research11 as R11       # 只用 wilder_atr（Wilder 14 的公式本身）

D = RA.D
COST = 0.00585
H = 120
BOUNDS = {"explore": ("2017-03-02", "2021-12-30"), "confirm": ("2022-01-03", "2026-08-24")}
CODES = ["SL5", "SL10", "SL15", "SL20", "TR10", "TR20", "AT2", "AT3", "MA20", "MA50", "TP20", "TP30", "TP50", "TP100",
         "RU15", "RU30", "RU50", "RD10", "RD20", "RG60", "RG200", "AU10", "AU20", "AD10", "AD20", "AH40"]
CLS = {**{c: "停損" for c in CODES[:10]}, **{c: "停利" for c in CODES[10:14]}, **{c: "減碼" for c in CODES[14:21]}, **{c: "加碼" for c in CODES[21:]}}


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    tot = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((tot ** 2).sum()) / n, len(tot)


def exit_res(m, lo, hi, n_eff):
    if n_eff < 30:
        return "出口①", "—（樣本不足以分辨）"
    ex = "出口②" if n_eff < 100 else "出口③"
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果③" if m < 0 else "結果②")


def check_cells(K, cells, codes, cal, errs, tag):
    mon = np.array([str(cal[t])[:7] for t in K["e"]]); yr = np.array([cal[t].year for t in K["e"]])
    C = cells.set_index("code")
    mk = K["market"].to_numpy()
    for code in codes:
        d = K[f"d_{code}"].to_numpy(float); t = K[f"t_{code}"].to_numpy(bool)
        m, se, ng = cr0(d, mon); lo, hi = m - 1.96 * se, m + 1.96 * se
        ne = min(len(d), ng); ex, rs = exit_res(m, lo, hi, ne)
        r = C.loc[code]
        for k_, v in (("mean", m), ("se", se), ("lo", lo), ("hi", hi), ("trig_frac", t.mean()),
                      ("mean_twse", d[mk == "twse"].mean()), ("mean_tpex", d[mk == "tpex"].mean())):
            if not np.isclose(r[k_], v, rtol=0, atol=1e-12, equal_nan=True):
                errs.append(f"{tag} {code} {k_}: 檔 {r[k_]!r} ≠ 重算 {v!r}")
        for y in sorted(set(yr)):
            if not np.isclose(r[f"y{y}"], d[yr == y].mean(), rtol=0, atol=1e-12, equal_nan=True):
                errs.append(f"{tag} {code} y{y}")
        got = (int(r["n"]), int(r["月數"]), int(r["n_eff"]), r["出口"], r["結果"])
        if got != (len(d), ng, ne, ex, rs):
            errs.append(f"{tag} {code} n/月數/出口: 檔 {got} ≠ {(len(d), ng, ne, ex, rs)}")
        if t.any():
            b = K["base"].to_numpy(float)[t]
            if not np.isclose(r["base_trig_mean"], b.mean(), rtol=0, atol=1e-12) or not np.isclose(r["hold_better_frac_trig"], (d[t] < 0).mean(), rtol=0, atol=1e-12):
                errs.append(f"{tag} {code} 放棄組")


# ───────── 逐日迴圈的單筆重算（狀態機；⛔ 不用主程式）
def can(S, t, side):
    o = S["o"][t]
    lim = S["dn_o"][t] if side == "sell" else S["up_o"][t]
    return bool(S["trd"][t]) and not bool(lim) and np.isfinite(o) and o > 0


def first_exec(S, d, x, side):
    for t in range(d + 1, x):
        if can(S, t, side):
            return t
    return -1


def loop_one(code, S, e, x, P0, cj, bl60, bl200, atr_bars, bpos):
    o, c, v = S["o"], S["c"], S["valid"]
    base = cj / P0 - 1 - COST
    if code in ("RG60", "RG200"):
        bl = bl60 if code == "RG60" else bl200
        half = bool(bl[e - 1])
        sh = (0.5 if half else 1.0) / P0; cash = 0.5 if half else 0.0; inv = 0.5 if half else 1.0; n_act = 0
        for t in range(e + 1, x):
            if bl[t - 1] and not half and can(S, t, "sell"):
                cash += (sh / 2) * o[t]; sh /= 2; half = True; n_act += 1
            elif (not bl[t - 1]) and half and can(S, t, "buy"):
                sh += cash / o[t]; inv += cash; cash = 0.0; half = False; n_act += 1
        return sh * cj + cash - inv * COST - 1 - base, (n_act > 0 or bool(bl[e - 1]))
    trig = -1
    if code == "AH40":
        k = 0
        for t in range(e, x):
            if v[t]:
                k += 1
                if k == 40:
                    trig = t if c[t] > P0 else -1
                    break
    else:
        hi = -np.inf; ma_n = {"MA20": 20, "MA50": 50}.get(code); line = None
        if code.startswith("AT"):
            mlt = float(code[2:]); kb = bpos[e] - 1
            a0 = atr_bars[kb] if kb >= 0 else np.nan
            line = P0 - mlt * a0 if np.isfinite(a0) else None
        for t in range(e, x):
            if not v[t]:
                continue
            ct = c[t]
            if code[:2] in ("SL", "RD", "AD"):
                hit = ct <= P0 * (100 - int(code[2:])) / 100.0
            elif code[:2] in ("TP", "RU", "AU"):
                hit = ct >= P0 * (100 + int(code[2:])) / 100.0
            elif code.startswith("TR"):
                hi = max(hi, ct); hit = ct <= hi * (100 - int(code[2:])) / 100.0
            elif code.startswith("AT"):
                if line is None:
                    break
                if ct > hi:
                    hi = ct
                    a = atr_bars[bpos[t]]
                    if np.isfinite(a):
                        line = max(line, ct - mlt * a)
                hit = ct < line
            else:
                i = bpos[t]
                if i + 1 < ma_n:
                    continue
                ma = math.fsum(S["c"][S["bars"][i + 1 - ma_n:i + 1]]) / ma_n
                hit = ct < ma
            if hit:
                trig = t
                break
    if trig < 0:
        return 0.0, False
    cl = CLS[code]
    s = first_exec(S, trig, x, "buy" if cl == "加碼" else "sell")
    if s < 0:
        return 0.0, False
    if cl in ("停損", "停利"):
        return o[s] / P0 - 1 - COST - base, True
    if cl == "減碼":
        return 0.5 * (o[s] - cj) / P0, True
    return 0.5 * (cj / o[s] - 1 - COST), True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--out", default=os.path.expanduser("~/tw-p17/backtest/resultsQuad"))
    a = ap.parse_args()
    OUT = a.out
    cal = D.load_calendar(); errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    pre = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    segs = {"explore": ("explore_diffs.csv.gz", "explore_cells.csv", CODES)}
    sel = [v["code"] for v in S["探索段挑選"].values() if v["進確認"]]
    if sel:
        segs["confirm"] = ("confirm_diffs.csv.gz", "confirm_cells.csv", sel)
    Ks = {}
    for seg, (fd, fc, codes) in segs.items():
        K = pd.read_csv(os.path.join(OUT, fd), dtype={"sid": str}); Ks[seg] = K
        cells = pd.read_csv(os.path.join(OUT, fc))
        lo, hi = (int(cal.searchsorted(pd.Timestamp(s))) for s in BOUNDS[seg])
        if not ((K["e"] >= lo).all() and ((K["e"] + H - 1) <= hi).all()):
            errs.append(f"{seg} 有持有沒有整筆落在段內")
        if len(K) != pre["保留"][seg]:
            errs.append(f"{seg} 列數 {len(K)} ≠ pre 保留 {pre['保留'][seg]}")
        if K.duplicated(["sid", "e"]).any():
            errs.append(f"{seg} 有重複持有")
        check_cells(K, cells, codes, cal, errs, seg)
        info[f"{seg}_列數"] = int(len(K))
    # ② 挑選
    E = pd.read_csv(os.path.join(OUT, "explore_cells.csv"))
    for cls in ("停損", "停利", "減碼", "加碼"):
        g = E[E["類"] == cls]
        best = sorted(g.itertuples(), key=lambda r: (-r.mean, r.trig_frac, CODES.index(r.code)))[0]
        got = S["探索段挑選"][cls]
        if got["code"] != best.code or got["進確認"] != bool(best.mean > 0):
            errs.append(f"挑選 {cls}: 檔 {got['code']} ≠ 重挑 {best.code}")
        info[f"挑選_{cls}"] = [best.code, int((g["mean"] == best.mean).sum())]
    # ③ 逐日迴圈重算
    off = RA.TR.load_official()
    s50 = D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)
    c50 = pd.Series(s50).ffill().to_numpy()
    bl = {}
    for n in (60, 200):
        ma = pd.Series(c50).rolling(n).mean().to_numpy()
        bl[n] = np.isfinite(ma) & (c50 < ma)
    rng = np.random.default_rng(7)
    nchk = 0; worst = 0.0; ntr = 0
    for seg, K in Ks.items():
        codes = segs[seg][2]
        idx = rng.choice(len(K), size=min(a.n, len(K)), replace=False)
        sub = K.iloc[idx]
        for sid, g in sub.groupby("sid"):
            mk = g["market"].iloc[0]
            P = RA.prep(sid, mk, cal, off)
            df = D.load_stock(sid, mk, cal).df
            b = P["bars"]; bpos = np.full(len(cal), -1); bpos[b] = np.arange(len(b))
            atr_bars = R11.wilder_atr(df["high"].to_numpy(float)[b], df["low"].to_numpy(float)[b], P["c"][b])
            for r in g.itertuples():
                e = int(r.e); x = e + H - 1; P0 = float(P["o"][e])
                j = x
                while not P["valid"][j]:
                    j -= 1
                cj = float(P["c"][j])
                if not np.isclose(r.base, cj / P0 - 1 - COST, rtol=0, atol=1e-15):
                    errs.append(f"base {sid} {e}")
                for code in codes:
                    dv, tr = loop_one(code, P, e, x, P0, cj, bl[60], bl[200], atr_bars, bpos)
                    fv = getattr(r, f"d_{code}"); ft = bool(getattr(r, f"t_{code}"))
                    worst = max(worst, abs(dv - fv)); nchk += 1; ntr += tr
                    if abs(dv - fv) > 1e-12 or tr != ft:
                        errs.append(f"逐日 {seg} {sid} e={e} {code}: 檔 ({fv!r},{ft}) ≠ 迴圈 ({dv!r},{tr})")
    info.update(逐日比對格數=nchk, 其中觸發=int(ntr), 最大差=worst, 錯誤數=len(errs))
    print(json.dumps(info, ensure_ascii=False, default=str))
    for e_ in errs[:20]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs[:200]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()

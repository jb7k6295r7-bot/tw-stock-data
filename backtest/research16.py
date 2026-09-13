"""研究十六：確認機制拆解——在研究十五的 B3 訊號集上只改進場時點／進場 K 棒條件。判準 backtest/PREREG16.md。

    python3 -m backtest.research16 [--procs 4] [--limit N]

訊號集 ＝ results15/signals.csv.gz（不重新偵測）；K 棒／出場／CI ＝ research11（同一件事只有一份實作）；去重 ＝ research15.dedup。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import research15 as R15

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results16")
R15DIR = os.path.join(HERE, "results15")
COST = R.COST
HOLDS = (20, 60, 120)
DELAYS = (1, 3, 5)
VARS = ("main", "D_3pens")
G_THR = {"G1": 0.618, "G2": 0.5, "G3": 0.75, "G4": 0.80}
SEED_BOOT = 20260916
_G: dict = {}


def _init(cal):
    R._init(cal); _G["cal"] = cal


def atr20_simple(h, l, c):
    """真實波幅 20 根簡單平均（含當根）。PREREG16 三節：⚠ 不是 Wilder-14。"""
    pc = np.roll(c, 1); pc[0] = np.nan
    tr = np.nanmax(np.stack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy(float)


def worker(args):
    """一檔：對每個 B3 訊號根 k 算 P1／P2／P3_j／P2raw 與進場根的 p。"""
    sid, market, ks = args
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return [{"sid": sid, "k": k, "err": "no_bars"} for k, _ in ks]
    o, c, h, l, rc, next_bad = (B[kk] for kk in ("o", "c", "h", "l", "rc", "next_bad"))
    n = len(c); a20 = atr20_simple(h, l, c)
    out = []
    for k, rid in ks:
        row = {"rid": rid}
        for H in HOLDS:
            r = R.fixed_exit(o, c, k, H, next_bad[k + 1])                       # P1：open[k+1] → close[k+H]
            row[f"P1_H{H}"] = r[1] if r else np.nan
            e = k + H
            ok = e < n and e < next_bad[k + 1]
            row[f"P2_H{H}"] = (c[e] / c[k] - 1) if ok and c[k] > 0 else np.nan      # P2：close[k] → close[k+H]
            row[f"P2raw_H{H}"] = (rc[e] / rc[k] - 1) if ok and np.isfinite(rc[k]) and np.isfinite(rc[e]) and rc[k] > 0 else np.nan
            for j in DELAYS:                                                    # P3_j：open[k+1+j] → close[k+H+j]
                s, e2 = k + 1 + j, k + H + j
                okj = e2 < n and e2 < next_bad[s] and np.isfinite(o[s]) and o[s] > 0
                row[f"P3_{j}_H{H}"] = (c[e2] / o[s] - 1) if okj else np.nan
        hl = h[k] - l[k]
        row["lock"] = bool(hl <= 0)
        row["p"] = ((c[k] - l[k]) / hl) if hl > 0 else (1.0 if (k > 0 and c[k] >= c[k - 1]) else 0.0)
        row["amp_ok"] = bool(np.isfinite(a20[k]) and hl >= 0.5 * a20[k])
        out.append(row)
    return out


# ── 統計 ──
def boot_diff(xa, ma, xb, mb, reps=2000, seed=SEED_BOOT):
    """子集 a 對子集 b 的平均差，月分群 bootstrap（重抽月份）。回傳 dict(mean, lo, hi, n_a, n_b)。"""
    xa = np.asarray(xa, float); xb = np.asarray(xb, float); ma = np.asarray(ma); mb = np.asarray(mb)
    oka, okb = ~np.isnan(xa), ~np.isnan(xb)
    xa, ma, xb, mb = xa[oka], ma[oka], xb[okb], mb[okb]
    if len(xa) == 0 or len(xb) == 0:
        return {"n_a": len(xa), "n_b": len(xb)}
    months = np.array(sorted(set(ma) | set(mb)))
    idx = {m: i for i, m in enumerate(months)}
    sa = np.zeros(len(months)); ca = np.zeros(len(months)); sb = np.zeros(len(months)); cb = np.zeros(len(months))
    np.add.at(sa, [idx[m] for m in ma], xa); np.add.at(ca, [idx[m] for m in ma], 1)
    np.add.at(sb, [idx[m] for m in mb], xb); np.add.at(cb, [idx[m] for m in mb], 1)
    rng = np.random.default_rng(seed)
    sel = rng.integers(0, len(months), size=(reps, len(months)))
    Ta = sa[sel].sum(1) / np.maximum(ca[sel].sum(1), 1); Tb = sb[sel].sum(1) / np.maximum(cb[sel].sum(1), 1)
    T = Ta - Tb
    return {"mean": float(xa.mean() - xb.mean()), "lo": float(np.percentile(T, 2.5)), "hi": float(np.percentile(T, 97.5)), "n_a": len(xa), "n_b": len(xb)}


def _p(x, d=2):
    return R._p(x, d)


def _ci(s):
    return f"{s['mean'] * 100:+.2f} pp（{s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {'測不出' if s['lo'] <= 0 <= s['hi'] else '測得出'}"


def cell_row(name, d, col, base_m):
    """一格：n／平均／中位／勝率／p10／最壞／CI／基準／超額 月配對 CI。"""
    x = d[col].to_numpy(float) - COST
    s = R.cl_stats(x, d["month"].to_numpy())
    if s["n"] == 0:
        return f"| {name} | 0 | | | | | | | | | |", None
    ex = d[col].to_numpy(float) - d["month"].map(base_m).to_numpy(float)
    se = R.cl_stats(ex, d["month"].to_numpy())
    b = float(np.nanmean(d["month"].map(base_m).to_numpy(float))) - COST
    v = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
    return (f"| {name} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['p10'])} | {_p(s['worst'])} | "
            f"{_p(s['lo'])} ~ {_p(s['hi'])} | {_p(b)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {v} |"), se


HDR = ["| 格 | n | 平均 | 中位 | 勝率 | p10 | 最壞 | 月分群 95% CI | 基準 | 超額 | 超額 月配對 CI | 統計層 |", "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--limit", type=int); ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe().set_index("stock_id")["market"]
    S = pd.read_csv(os.path.join(R15DIR, "signals.csv.gz"), dtype={"sid": str}, low_memory=False)
    S = S[(S["kind"] != "ERROR") & S["variant"].isin(VARS)].copy()
    S["gate_all"] = S["gate_ok"] & S["liq_ok"]
    S = R15.dedup(S)
    E = pd.read_csv(os.path.join(R15DIR, "eligible.csv.gz"), dtype={"sid": str})
    base = {"gate": {H: E[E["liq"]].groupby("month")[f"g{H}"].mean() for H in HOLDS},
            "nogate": {H: E.groupby("month")[f"g{H}"].mean() for H in HOLDS}}
    B3 = S[(S["kind"] == "B3") & S["gate_all"]].copy()
    B3["rid"] = np.arange(len(B3))
    if a.limit:
        B3 = B3[B3["sid"].isin(B3["sid"].unique()[:a.limit])]
    jobs = [(sid, uni.get(sid), [(int(k), int(rid)) for k, rid in zip(g["k"], g["rid"])]) for sid, g in B3.groupby("sid")]
    print(f"B3 過閘門去重 {len(B3):,} 筆／{len(jobs):,} 檔（main {int((B3.variant == 'main').sum()):,}、D {int((B3.variant == 'D_3pens').sum()):,}）", file=sys.stderr)
    rows = []
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, jobs, chunksize=8)):
            rows.extend(r)
            if (i + 1) % 300 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", file=sys.stderr)
    P = pd.DataFrame(rows)
    errs = P[P.get("err").notna()] if "err" in P else P.iloc[0:0]
    P = P[P["rid"].notna()].copy() if "rid" in P else P
    M = B3.merge(P.drop(columns=[c for c in ("err", "sid", "k") if c in P]), on="rid", how="left")
    M.to_csv(os.path.join(RESULTS, "rows.csv.gz"), index=False)
    L = ["# 研究十六：確認機制拆解——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG16.md`。訊號集 `results15/signals.csv.gz`（B3、過閘門＋流動性、去重 20）。", ""]
    if len(errs):
        L.append(f"⚠ 讀不到 K 棒的檔：{len(errs)}"); L.append("")
    # 對帳
    L.append("## 〇、對帳：P1 重算 vs 研究十五存的 g_H*"); L.append("")
    stop = False
    for H in HOLDS:
        a_ = M[f"P1_H{H}"].to_numpy(float); b_ = M[f"g_H{H}"].to_numpy(float)
        both = ~np.isnan(a_) & ~np.isnan(b_); mism = int((np.abs(a_[both] - b_[both]) > 1e-9).sum()); nanmis = int((np.isnan(a_) != np.isnan(b_)).sum())
        L.append(f"- H{H}：可比 {both.sum():,}，數值不等 {mism}，缺值不一致 {nanmis}")
        stop |= (mism > 0 or nanmis > 0)
    L.append("")
    if stop:
        L.append("⛔ 對帳不過，停在這裡，不出報表。")
        open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L)); print("\n".join(L)); sys.exit(1)
    # 一、進場時點
    L.append("## 一、進場時點（同一批 B3；基準 ＝ 研究十五同月母體，過閘門）"); L.append("")
    cols1 = [("P1（現行 open[k+1]）", "P1"), ("P2（close[k]）", "P2")] + [(f"P3_{j}（open[k+1+{j}]）", f"P3_{j}") for j in DELAYS] + [("P2raw（未還原 close）", "P2raw")]
    for v in VARS:
        d = M[M.variant == v]
        L.append(f"### {v}（n＝{len(d):,}）"); L.append("")
        for H in HOLDS:
            L.append(f"#### H{H}"); L.append(""); L += HDR
            for nm, pre in cols1:
                L.append(cell_row(nm, d, f"{pre}_H{H}", base["gate"][H])[0])
            L.append("")
            L.append("配對（每筆差、月分群 CI）：")
            L.append(f"- P2 − P1：{_ci(R.cl_stats((d[f'P2_H{H}'] - d[f'P1_H{H}']).to_numpy(float), d['month'].to_numpy()))}")
            for j in DELAYS:
                L.append(f"- P3_{j} − P1：{_ci(R.cl_stats((d[f'P3_{j}_H{H}'] - d[f'P1_H{H}']).to_numpy(float), d['month'].to_numpy()))}")
            dv = d[d[f"div_H{H}"].astype(str) == "False"]
            L.append(f"- P2raw − P2（同筆、還原 vs 原始）：{_ci(R.cl_stats((d[f'P2raw_H{H}'] - d[f'P2_H{H}']).to_numpy(float), d['month'].to_numpy()))}；窗內無還原事件那批 n {len(dv):,}：{_ci(R.cl_stats((dv[f'P2raw_H{H}'] - dv[f'P2_H{H}']).to_numpy(float), dv['month'].to_numpy())) if len(dv) else '—'}")
            L.append("")
    # 二、等回抽值多少
    L.append("## 二、等回抽值多少（同一個中樞：C2 對後來的 B3；過閘門、去重）"); L.append("")
    for v in VARS:
        d = S[S.variant == v]
        kinds = d.groupby(["sid", "center"])["kind"].agg(lambda x: set(x))
        c2 = d[(d.kind == "C2") & d.gate_all].copy()
        key = list(zip(c2["sid"], c2["center"]))
        c2["has_b3"] = [("B3" in kinds.get(kk, set())) for kk in key]; c2["has_ab"] = [("ABANDON" in kinds.get(kk, set())) for kk in key]
        c2["grp"] = np.where(c2.has_b3, "C2|B3", np.where(c2.has_ab, "C2|ABANDON", "C2|none（三部曲沒完成）"))
        L.append(f"### {v}"); L.append("")
        for H in HOLDS:
            L.append(f"#### H{H}"); L.append(""); L += HDR
            for g in ("C2|B3", "C2|ABANDON", "C2|none（三部曲沒完成）"):
                L.append(cell_row(g, c2[c2.grp == g], f"g_H{H}", base["gate"][H])[0])
            b3 = d[(d.kind == "B3") & d.gate_all]
            first_b3 = b3.sort_values("k").groupby(["sid", "center"]).first()
            pr = c2[c2.has_b3].merge(first_b3[[f"g_H{H}", "month"]].rename(columns={f"g_H{H}": "b3_g", "month": "b3_month"}), left_on=["sid", "center"], right_index=True, how="inner")
            L.append(cell_row("B3（同一批中樞）", pr.assign(**{f"g_H{H}": pr["b3_g"]}), f"g_H{H}", base["gate"][H])[0])
            L.append("")
            L.append(f"- C2|B3 − B3（同中樞配對，月 ＝ C2 月）：{_ci(R.cl_stats((pr[f'g_H{H}'] - pr['b3_g']).to_numpy(float), pr['month'].to_numpy()))}")
            L.append(f"- 中樞數：C2 過閘門 {len(c2):,}；其中後來 B3 {int(c2.has_b3.sum()):,}、ABANDON（無 B3） {int((c2.grp == 'C2|ABANDON').sum()):,}、沒完成 {int((c2.grp.str.startswith('C2|none')).sum()):,}")
            L.append("")
    # 三、敏感度 G
    L.append("## 三、敏感度 G：B3 確認根的收盤位置 p（H20 主判定；每格對補集 ＝ 月分群 bootstrap）"); L.append("")
    for v in VARS:
        d = M[M.variant == v].copy()
        nlock = int(d["lock"].sum())
        L.append(f"### {v}（n＝{len(d):,}；high == low 鎖死 {nlock} 筆，A 案 p ∈ {{0,1}} 進四等級、B 案另列）"); L.append("")
        for H in HOLDS:
            L.append(f"#### H{H}"); L.append("")
            L.append("| 格 | 版 | n | 砍掉 | 平均 | 中位 | 超額 | 超額 CI | 統計層 | 格 − 補集 | CI | 判 |"); L.append("|---|---|---:|---:|---:|---:|---:|---|---|---:|---|---|")
            col = f"P1_H{H}"; bm = base["gate"][H]
            for case, dd in (("A", d), ("B", d[~d["lock"]])):
                for gname, thr in [("G0", None)] + list(G_THR.items()):
                    for ver in ("a", "b"):
                        m = pd.Series(True, index=dd.index) if thr is None else (dd["p"] >= thr)
                        if ver == "b":
                            m = m & dd["amp_ok"]
                        sub, comp = dd[m], dd[~m]
                        if len(sub) == 0:
                            L.append(f"| {gname} | {case}{ver} | 0 | | | | | | | | | |"); continue
                        ex = sub[col].to_numpy(float) - sub["month"].map(bm).to_numpy(float); se = R.cl_stats(ex, sub["month"].to_numpy())
                        bd = boot_diff(sub[col].to_numpy(float), sub["month"].to_numpy(), comp[col].to_numpy(float), comp["month"].to_numpy(), reps=a.reps) if len(comp) else {}
                        vv = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
                        bds = f"{bd['mean'] * 100:+.2f} pp | {bd['lo'] * 100:+.2f} ~ {bd['hi'] * 100:+.2f} | {'測不出' if bd['lo'] <= 0 <= bd['hi'] else '測得出'}" if "mean" in bd else "— | — | —"
                        L.append(f"| {gname} | {case}{ver} | {se['n']:,} | {(1 - len(sub) / len(dd)) * 100:.0f}% | {_p(np.nanmean(sub[col]) - COST)} | {_p(np.nanmedian(sub[col]) - COST)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {vv} | {bds} |")
                        if gname == "G0" and ver == "a":
                            pass
                    if gname == "G0":
                        continue
                if case == "B":
                    lk = d[d["lock"]]
                    if len(lk):
                        se = R.cl_stats(lk[col].to_numpy(float) - lk["month"].map(bm).to_numpy(float), lk["month"].to_numpy())
                        L.append(f"| 鎖死 | B | {se['n']:,} | — | {_p(np.nanmean(lk[col]) - COST)} | {_p(np.nanmedian(lk[col]) - COST)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | | | | |")
            L.append("")
    # 四、閘門差
    L.append("## 四、無流動性閘門 − 有閘門（研究十五主格 B3、去重；月分群 bootstrap）"); L.append("")
    d = S[(S.variant == "main") & (S.kind == "B3") & S.gate_ok]
    for H in HOLDS:
        exn = d[f"g_H{H}"].to_numpy(float) - d["month"].map(base["nogate"][H]).to_numpy(float)
        g = d[d.liq_ok]; exg = g[f"g_H{H}"].to_numpy(float) - g["month"].map(base["gate"][H]).to_numpy(float)
        T = boot_diff(exn, d["month"].to_numpy(), exg, g["month"].to_numpy(), reps=a.reps)
        rj = d[~d.liq_ok]
        exr = rj[f"g_H{H}"].to_numpy(float) - rj["month"].map(base["nogate"][H]).to_numpy(float)
        exg2 = g[f"g_H{H}"].to_numpy(float) - g["month"].map(base["nogate"][H]).to_numpy(float)
        T2 = boot_diff(exr, rj["month"].to_numpy(), exg2, g["month"].to_numpy(), reps=a.reps)
        L.append(f"- H{H}：超額(無閘門 n {T['n_a']:,}) − 超額(有閘門 n {T['n_b']:,}) ＝ {_ci(T)}；被砍掉那批 − 留下那批（同一基準＝無閘門母體）＝ {_ci(T2)}")
    L.append("")
    open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L))
    print(f"完成 {time.time() - t0:.0f}s → {RESULTS}/summary.md", file=sys.stderr)


if __name__ == "__main__":
    main()

"""研究十七：共同骨架拆解——確認機制 vs 指標（A 純確認／B TD＋確認／C 純指標／D 出場也用確認器）。判準 backtest/PREREG17.md。

    python3 -m backtest.research17 [--procs 4] [--limit N] [--reps 2000]

K 棒／出場／CI：research11；閘門與母體：research15（同一份實作）；bootstrap：research16.boot_diff。
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
from . import research16 as R16

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results17")
COST = R.COST
HOLDS = (20, 60, 120)
MS = (1, 2, 3)
LENS = (9, 8, 13)          # 主格 9；8／13 敏感度
CAP_D = 120
SEED = 20260914
A_KEEP = 0.03              # A 的逐筆蓄水池：每根候選以 2% 機率留逐筆（A_full 用月彙總，不靠它）
_G: dict = {}


def _init(cal, disp, att, marg):
    R._init(cal); _G.update(cal=cal, disp=disp, att=att, marg=marg)


def run_counts(c, up=True):
    """TD Setup 計數：連續 close[i] > close[i-4]（up）或 <（down）的長度，中斷歸零。"""
    n = len(c); cnt = np.zeros(n, int)
    for i in range(4, n):
        ok = (c[i] > c[i - 4]) if up else (c[i] < c[i - 4])
        cnt[i] = cnt[i - 1] + 1 if ok else 0
    return cnt


def confirm(c, k, box_hi, M):
    """k 之後 M 根內第一根 close > box_hi 的索引；沒有 ⇒ -1。"""
    n = len(c)
    for j in range(k + 1, min(k + M, n - 1) + 1):
        if c[j] > box_hi:
            return j
    return -1


def ret(c, e, x, k, next_bad):
    """close[e] → close[x]；窗 [k, x] 內不可有壞根。"""
    if x >= len(c) or x >= next_bad[k] or not (c[e] > 0):
        return np.nan
    return c[x] / c[e] - 1


def d_exit(c, h, l, dn_cnt, j, k, next_bad, M):
    """D 組出場：j 之後的 TD 賣方 Setup 完成根 s → 箱 → s 後 M 根內 close < low[s] 出／close > high[s] 失敗續抱；上限 j+CAP_D。回傳 (exit_idx, kind)。"""
    n = len(c); cap = j + CAP_D
    s = j + 1
    while s <= min(cap, n - 1):
        if dn_cnt[s] == 9:
            done = False
            for t in range(s + 1, min(s + M, n - 1, cap) + 1):
                if c[t] < l[s]:
                    return t, "confirm"
                if c[t] > h[s]:
                    s = t; done = True; break            # 止漲失敗，從失敗根往後再找
            if not done:
                s = s + M                                 # 沒觸發，續抱
        s += 1
    return min(cap, n - 1), "cap"


def worker(args):
    sid, market = args
    cal, disp, att, marg = _G["cal"], _G["disp"], _G["att"], _G["marg"]
    B = R.load_bars(sid, market, cal)
    if B is None:
        return None
    dates, o, c, h, l, amt, next_bad = (B[k] for k in ("dates", "o", "c", "h", "l", "amt", "next_bad"))
    n = len(c)
    liq_ok = pd.Series(amt).shift(1).rolling(20, min_periods=20).mean().to_numpy(float) >= R15.LIQ
    dmask = D.disposal_mask(sid, cal, disp)[B["idx"]]
    a_dates = att.get(sid, set()); m_dates = marg.get(sid, set())
    gate = ~dmask & np.array([d not in a_dates and d not in m_dates for d in dates]) & liq_ok & (dates >= R15.SIG_START)
    month = dates.strftime("%Y-%m")
    ma20 = pd.Series(c).rolling(20).mean().to_numpy(float); ma60 = pd.Series(c).rolling(60).mean().to_numpy(float)
    rng = np.random.default_rng(SEED + int(sid) if sid.isdigit() else SEED)
    out = {"sid": sid, "rows": [], "a_agg": [], "a_res": [], "base": []}
    # 基準：所有過閘門 K 棒 close→close
    for t in np.flatnonzero(gate):
        rec = {"month": month[t]}
        for H in HOLDS:
            rec[f"g{H}"] = ret(c, t, t + H, t, next_bad)
        out["base"].append(rec)
    # A：任一根
    a_rows = {}
    for k in np.flatnonzero(gate):
        r = {"month": month[k]}
        keep = rng.random() < A_KEEP
        for M in MS:
            j = confirm(c, k, h[k], M)
            r[f"j{M}"] = j
            for H in HOLDS:
                r[f"g{M}_H{H}"] = ret(c, j, j + H, k, next_bad) if j >= 0 else np.nan
                r[f"ab{M}_H{H}"] = ret(c, k + M, k + M + H, k, next_bad) if (j < 0 and k + M < n) else np.nan
        out["a_agg"].append(r)
        if keep:
            out["a_res"].append(r)
    # B／C／D：TD 買方 Setup 完成根
    up_cnt = run_counts(c, True); dn_cnt = run_counts(c, False)
    for L in LENS:
        for k in np.flatnonzero((up_cnt == L) & gate):
            row = {"sid": sid, "k": int(k), "pos": int(B["idx"][k]), "month": month[k], "L": L, "date": str(dates[k].date()),
                   "above20": bool(c[k] > ma20[k]) if np.isfinite(ma20[k]) else None, "above60": bool(c[k] > ma60[k]) if np.isfinite(ma60[k]) else None,
                   "ma20_up": bool(ma20[k] > ma20[k - 1]) if k > 0 and np.isfinite(ma20[k - 1]) else None}
            for H in HOLDS:
                row[f"C_H{H}"] = ret(c, k, k + H, k, next_bad)                      # C：當根收盤進
            for M in MS:
                j = confirm(c, k, h[k], M); row[f"j{M}"] = j
                for H in HOLDS:
                    row[f"B{M}_H{H}"] = ret(c, j, j + H, k, next_bad) if j >= 0 else np.nan
                    row[f"ab{M}_H{H}"] = ret(c, k + M, k + M + H, k, next_bad) if (j < 0 and k + M < n) else np.nan
                if j >= 0:
                    x, kind = d_exit(c, h, l, dn_cnt, j, k, next_bad, M)
                    row[f"D{M}"] = ret(c, j, x, k, next_bad); row[f"D{M}_kind"] = kind; row[f"D{M}_bars"] = x - j
                else:
                    row[f"D{M}"] = np.nan; row[f"D{M}_kind"] = None; row[f"D{M}_bars"] = np.nan
                if L == 9 and M == 2:                                                 # N1：箱高＝第 1 根的高點
                    j1 = confirm(c, k, h[k - 8], M) if k >= 8 else -1
                    row["N1_j"] = j1
                    for H in HOLDS:
                        row[f"N1_H{H}"] = ret(c, j1, j1 + H, k, next_bad) if j1 >= 0 else np.nan
            out["rows"].append(row)
    return out


# ── 統計 ──
def _p(x, d=2):
    return R._p(x, d)


def _ci(s):
    if not s or s.get("n", 0) == 0 and "mean" not in s:
        return "n 0"
    return f"{s['mean'] * 100:+.2f} pp（{s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {'測不出' if s['lo'] <= 0 <= s['hi'] else '測得出'}"


def cell(name, x, m, base_m):
    x = np.asarray(x, float); m = np.asarray(m); ok = ~np.isnan(x); x, m = x[ok], m[ok]
    if len(x) == 0:
        return f"| {name} | 0 | | | | | | | |", None
    s = R.cl_stats(x - COST, m)
    ex = x - pd.Series(m).map(base_m).to_numpy(float); se = R.cl_stats(ex, m)
    v = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
    return (f"| {name} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['p10'])} | "
            f"{se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {v} |"), se


def agg_cell(name, agg, base_m, reps, seed=SEED):
    """A_full：只有月彙總（sum／count）。平均、超額、月 bootstrap CI。"""
    if agg["cnt"].sum() == 0:
        return f"| {name} | 0 | | | | | | | |", None
    n = int(agg["cnt"].sum()); mean = float(agg["sum"].sum() / n)
    agg = agg[agg["cnt"] > 0]
    bm = agg.index.map(base_m).to_numpy(float)
    ex_sum = (agg["sum"] - agg["cnt"] * bm).fillna(0.0); exm = float(ex_sum.sum() / n)
    rng = np.random.default_rng(seed); k = len(agg)
    sel = rng.integers(0, k, size=(reps, k))
    T = ex_sum.to_numpy()[sel].sum(1) / np.maximum(agg["cnt"].to_numpy()[sel].sum(1), 1)
    lo, hi = float(np.percentile(T, 2.5)), float(np.percentile(T, 97.5))
    v = "測不出" if lo <= 0 <= hi else ("測得出（＋）" if exm > 0 else "測得出（−）")
    return f"| {name} | {n:,} | {_p(mean - COST)} | — | — | — | {exm * 100:+.2f} pp | {lo * 100:+.2f} ~ {hi * 100:+.2f} | {v} |", {"mean": exm, "lo": lo, "hi": hi, "n": n}


def boot_diff_agg(xa, ma, agg_b, reps, seed=SEED):
    """子集 a（逐筆）對 A_full（月彙總 sum／cnt）的平均差，月 bootstrap。"""
    xa = np.asarray(xa, float); ma = np.asarray(ma); ok = ~np.isnan(xa); xa, ma = xa[ok], ma[ok]
    months = np.array(sorted(set(ma) | set(agg_b.index)))
    idx = {m: i for i, m in enumerate(months)}
    sa = np.zeros(len(months)); ca = np.zeros(len(months)); sb = np.zeros(len(months)); cb = np.zeros(len(months))
    np.add.at(sa, [idx[m] for m in ma], xa); np.add.at(ca, [idx[m] for m in ma], 1)
    for m, r in agg_b.iterrows():
        sb[idx[m]] = r["sum"]; cb[idx[m]] = r["cnt"]
    rng = np.random.default_rng(seed); sel = rng.integers(0, len(months), size=(reps, len(months)))
    T = sa[sel].sum(1) / np.maximum(ca[sel].sum(1), 1) - sb[sel].sum(1) / np.maximum(cb[sel].sum(1), 1)
    return {"mean": float(xa.mean() - sb.sum() / max(cb.sum(), 1)), "lo": float(np.percentile(T, 2.5)), "hi": float(np.percentile(T, 97.5)), "n_a": len(xa), "n_b": int(cb.sum())}


HDR = ["| 格 | n | 平均 | 中位 | 勝率 | p10 | 超額 | 超額 月配對 CI | 統計層 |", "|---|---:|---:|---:|---:|---:|---:|---|---|"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--limit", type=int); ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True); t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"]
    uni = uni[~uni["stock_id"].map(ind).isin(R15.EXCL_IND)]
    if a.limit:
        uni = uni.head(a.limit)
    disp = D.load_disposal_intervals(); att = D.load_attention_dates(); marg = R15.load_margin_o()
    rows, a_agg, a_res, base = [], [], [], []
    with Pool(a.procs, initializer=_init, initargs=(cal, disp, att, marg)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, list(zip(uni["stock_id"], uni["market"])), chunksize=8)):
            if r is None:
                continue
            rows.extend(r["rows"]); a_res.extend(r["a_res"]); base.extend(r["base"])
            if r["a_agg"]:
                a_agg.append(pd.DataFrame(r["a_agg"]).drop(columns=[f"j{M}" for M in MS]).groupby("month").agg(["sum", "count"]))
            if (i + 1) % 300 == 0:
                print(f"  {i + 1}/{len(uni)} {time.time() - t0:.0f}s", file=sys.stderr)
    S = pd.DataFrame(rows); AR = pd.DataFrame(a_res); BASE = pd.DataFrame(base)
    AG = pd.concat(a_agg).groupby(level=0).sum()          # A_full 月彙總：每欄 (sum, count)
    base_m = {H: BASE.groupby("month")[f"g{H}"].mean() for H in HOLDS}
    S.to_csv(os.path.join(RESULTS, "signals.csv.gz"), index=False); AR.to_csv(os.path.join(RESULTS, "a_reservoir.csv.gz"), index=False)
    print(f"訊號 {len(S):,}（L=9：{int((S.L == 9).sum()):,}）、A 蓄水池 {len(AR):,}、基準股票日 {len(BASE):,}，{time.time() - t0:.0f}s", file=sys.stderr)
    L = ["# 研究十七：共同骨架拆解——細表", "", f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG17.md`。", ""]
    B9 = S[S.L == 9]
    k_sig = 0
    L.append(f"## 〇、訊號量：TD 買方 Setup（9）過閘門 {len(B9):,} 筆／{B9.sid.nunique():,} 檔；每月中位 {B9.groupby('month').size().median():.0f}；A 候選 {len(BASE):,} 根（過閘門有效 K 棒），有確認 M＝1／2／3：" + "／".join(f"{int(AG[(f'g{M}_H20', 'count')].sum()):,}" for M in MS))
    for M in MS:
        conf = B9[f"j{M}"] >= 0
        L.append(f"- M＝{M}：B 有確認 {int(conf.sum()):,}（{conf.mean() * 100:.0f}%）、放棄 {int((~conf).sum()):,}")
    L.append("")
    # 一、各組各格
    for M in MS:
        L.append(f"## 一、M＝{M}：四組（基準＝同月過閘門 K 棒 close→close）"); L.append("")
        for H in HOLDS:
            L.append(f"#### H{H}"); L.append(""); L += HDR
            ag = pd.DataFrame({"sum": AG[(f"g{M}_H{H}", "sum")], "cnt": AG[(f"g{M}_H{H}", "count")]})
            L.append(agg_cell("A_full 純確認（全部候選，月彙總）", ag, base_m[H], a.reps)[0])
            # A_matched：每月抽 B 有確認的數量
            rng = np.random.default_rng(SEED); picks = []
            bcnt = B9[B9[f"j{M}"] >= 0].groupby("month").size()
            for mth, nb in bcnt.items():
                cand = AR[(AR.month == mth) & AR[f"g{M}_H{H}"].notna()]
                if len(cand):
                    picks.append(cand.iloc[rng.choice(len(cand), size=min(nb, len(cand)), replace=False)])
            AM = pd.concat(picks) if picks else AR.iloc[0:0]
            L.append(cell("A_matched 純確認（同月同數量抽）", AM[f"g{M}_H{H}"], AM["month"], base_m[H])[0])
            rowB, seB = cell("B 指標＋確認", B9[f"B{M}_H{H}"], B9["month"], base_m[H]); L.append(rowB)
            L.append(cell("C 純指標（當根收盤進）", B9[f"C_H{H}"], B9["month"], base_m[H])[0])
            if H == 120:
                L.append(cell("D 進出場都用確認器（上限 120 根）", B9[f"D{M}"], B9["month"], base_m[H])[0])
            L.append(cell("放棄組 B（M 根內沒確認；close[k+M] 起算）", B9[f"ab{M}_H{H}"], B9["month"], base_m[H])[0])
            agab = pd.DataFrame({"sum": AG[(f"ab{M}_H{H}", "sum")], "cnt": AG[(f"ab{M}_H{H}", "count")]})
            L.append(agg_cell("放棄組 A（月彙總）", agab, base_m[H], a.reps)[0])
            L.append("")
            L.append("比較：")
            d1 = boot_diff_agg(B9[f"B{M}_H{H}"].to_numpy(float), B9["month"].to_numpy(), ag, a.reps)
            d1m = R16.boot_diff(B9[f"B{M}_H{H}"].to_numpy(float), B9["month"].to_numpy(), AM[f"g{M}_H{H}"].to_numpy(float), AM["month"].to_numpy(), reps=a.reps) if len(AM) else {}
            pr = B9[B9[f"j{M}"] >= 0]
            d2 = R.cl_stats((pr[f"B{M}_H{H}"] - pr[f"C_H{H}"]).to_numpy(float), pr["month"].to_numpy())
            d2all = R16.boot_diff(B9[f"B{M}_H{H}"].to_numpy(float), B9["month"].to_numpy(), B9[f"C_H{H}"].to_numpy(float), B9["month"].to_numpy(), reps=a.reps)
            L.append(f"- B − A_full：{_ci(d1)}（n {d1['n_a']:,} vs {d1['n_b']:,}）")
            if d1m:
                L.append(f"- B − A_matched：{_ci(d1m)}（n {d1m['n_a']:,} vs {d1m['n_b']:,}）"); k_sig += int(not (d1m["lo"] <= 0 <= d1m["hi"]))
            L.append(f"- B − C（同關鍵 K 配對，只取 B 有確認）：{_ci(d2)}（n {d2.get('n', 0):,}）；B − C 全體：{_ci(d2all)}"); k_sig += int(d2.get("n", 0) > 0 and not (d2["lo"] <= 0 <= d2["hi"]))
            if H == 120:
                d3 = R.cl_stats((pr[f"D{M}"] - pr[f"B{M}_H120"]).to_numpy(float), pr["month"].to_numpy())
                kinds = pr[f"D{M}_kind"].value_counts().to_dict()
                L.append(f"- D − B（H120，同筆配對）：{_ci(d3)}（n {d3.get('n', 0):,}；D 出場種類 {kinds}；D 平均持有 {pr[f'D{M}_bars'].mean():.0f} 根）"); k_sig += int(d3.get("n", 0) > 0 and not (d3["lo"] <= 0 <= d3["hi"]))
            L.append("")
    # 二、敏感度（B、H20、M=2）
    L.append("## 二、敏感度（B、H20、M＝2）"); L.append(""); L += HDR
    for Lx in LENS:
        d = S[S.L == Lx]; L.append(cell(f"TD 長度 {Lx}", d["B2_H20"], d["month"], base_m[20])[0])
    L.append(cell("N1（箱高＝第 1 根高點）", B9["N1_H20"], B9["month"], base_m[20])[0])
    L.append("")
    sens = []
    b9 = R.cl_stats(B9["B2_H20"].to_numpy(float) - B9["month"].map(base_m[20]).to_numpy(float), B9["month"].to_numpy())
    for Lx in (8, 13):
        d = S[S.L == Lx]; bd = R16.boot_diff(d["B2_H20"].to_numpy(float), d["month"].to_numpy(), B9["B2_H20"].to_numpy(float), B9["month"].to_numpy(), reps=a.reps)
        L.append(f"- 長度 {Lx} − 長度 9：{_ci(bd)}"); k_sig += int(not (bd["lo"] <= 0 <= bd["hi"]))
    pn = B9[B9["N1_H20"].notna() & B9["B2_H20"].notna()]
    dn = R.cl_stats((pn["N1_H20"] - pn["B2_H20"]).to_numpy(float), pn["month"].to_numpy())
    L.append(f"- N1 − 主格（同筆配對）：{_ci(dn)}"); k_sig += int(dn.get("n", 0) > 0 and not (dn["lo"] <= 0 <= dn["hi"]))
    L.append("")
    # 三、趨勢狀態分佈
    L.append("## 三、B 訊號日的趨勢狀態分佈（我方定義；只報分佈）"); L.append("")
    for col in ("above20", "above60", "ma20_up"):
        vc = B9[col].value_counts(dropna=False, normalize=True)
        L.append(f"- {col}：" + "、".join(f"{k} {v * 100:.0f}%" for k, v in vc.items()))
    L.append("")
    L.append(f"## 四、格數：24 格、測得出 {k_sig} 格、雜訊期望 1.2 格"); L.append("")
    open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L))
    print(f"完成 {time.time() - t0:.0f}s → {RESULTS}/summary.md；測得出 {k_sig}/24", file=sys.stderr)


if __name__ == "__main__":
    main()

"""研究三（營收動能）與研究四（價值型）執行器。判準見 backtest/PREREG3.md。

    python3 -m backtest.research34                # 全市場 → backtest/results3/
    python3 -m backtest.research34 --stocks 2330 2454 --out /tmp/x

做法：每檔每個月度換股日 D_M 產出一列「面板」（閘門、營收特徵、估值、技術、20/60 日報酬），
策略只是面板上的布林遮罩，十分位在主程式做（需要橫斷面）。
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import evaluate as E
from . import patterns as P

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results3")
SIG_START, SIG_END, SPLIT = "2016-01-04", "2026-07-31", "2021-01-04"
HOLDS = (20, 60)
LOOKBACK_DAYS = 60                                    # 技術特徵最長回看：ma60、mom60（估值 ffill 25 日比它短）
H_FORWARD = 1 + max(HOLDS) + E.DEFER_MAX              # 斷點視窗 H（PREREG3 更正一）：次日進場 ＋ 最長持有 ＋ 跌停順延
L_LOOKBACK = LOOKBACK_DAYS                            # 斷點視窗 L
_G: dict = {}


# ---------- 營收 ----------
def load_revenue() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fs = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收", "產業別"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce")
    df["rev_ly"] = pd.to_numeric(df["去年當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    rev_ly = df.pivot(index="period", columns="stock_id", values="rev_ly").sort_index()
    ind = df.groupby("stock_id")["產業別"].last()
    return rev, rev_ly, ind


def rebalance_dates(periods: list[str], cal: pd.DatetimeIndex) -> dict[str, tuple[int, int]]:
    """period 'YYYY-MM' → (signal_pos, entry_pos)：M+1 月 10 日之後第一個交易日進場。"""
    out = {}
    for p in periods:
        y, m = int(p[:4]), int(p[5:])
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cutoff = pd.Timestamp(year=y2, month=m2, day=10)
        e = int(cal.searchsorted(cutoff, side="right"))   # 第一個 > 10 日的交易日
        if e >= len(cal) or e == 0:
            continue
        out[p] = (e - 1, e)
    return out


def _init(cal, bench, disp, rev, rev_ly, rdates, lo, hi):
    _G.update(cal=cal, bench=bench, disp=disp, rev=rev, rev_ly=rev_ly, rdates=rdates, lo=lo, hi=hi)


def _hold_ret(arr, entry, n):
    """固定持有 n 日（第 n 日收盤），跌停順延；回傳毛報酬或 NaN。"""
    old = E.HOLD
    E.HOLD = n
    try:
        r = E.hold_exit(arr, entry)
    finally:
        E.HOLD = old
    if r is None:
        return np.nan, -1
    return r[1] / arr["o"][entry] - 1, r[0]


def load_per(sid: str, cal: pd.DatetimeIndex) -> pd.DataFrame | None:
    p = os.path.join(D.DATA, "stocks_per", f"{sid}.csv")
    if not os.path.exists(p):
        return None
    x = pd.read_csv(p, usecols=["date", "yield_pct", "per", "pbr"])
    x["date"] = pd.to_datetime(x["date"])
    x = x.drop_duplicates("date").set_index("date").sort_index()
    for c in ("yield_pct", "per", "pbr"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    return x.reindex(cal).ffill(limit=25)   # 訊號日之前最後一筆（最多回看 25 個交易日）


def process_stock(args):
    sid, market, first_seen, last_seen = args
    cal, bench, disp, rev, rev_ly, rdates, lo, hi = (_G[k] for k in ("cal", "bench", "disp", "rev", "rev_ly", "rdates", "lo", "hi"))
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    f = P.Frame(df, st.event_dates)
    in_life = (cal >= first_seen) & (cal <= last_seen)
    dmask = D.disposal_mask(sid, cal, disp)
    # 斷點：換股日 s ∈ [T−H, T+L−1] 不進面板（PREREG3 更正一；規則見 data.breakpoints）
    jw = D.breakpoint_window(D.breakpoints(df, st.event_dates), len(cal), H_FORWARD, L_LOOKBACK)
    gate = f.gate & in_life & ~dmask & ~jw
    arr = {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c, "atr14": f.atr14}
    c = pd.Series(f.c)
    ma60 = c.rolling(60, min_periods=60).mean().to_numpy(float)
    mom60 = (c / c.shift(60) - 1).to_numpy(float)
    per = load_per(sid, cal)
    has_rev = sid in rev.columns
    rv = rev[sid] if has_rev else None
    rl = rev_ly[sid] if has_rev else None
    periods = list(rev.index)
    rows = []
    for k, p in enumerate(periods):
        if p not in rdates:
            continue
        sp, ep = rdates[p]
        if not (lo <= sp <= hi) or ep >= len(cal):
            continue
        row = {"stock_id": sid, "market": market, "period": p, "signal_pos": sp, "entry_pos": ep,
               "gate": bool(gate[sp]) and not np.isnan(f.o[ep])}
        if not row["gate"]:
            continue
        # 營收特徵
        if has_rev and not np.isnan(rv.iloc[k]):
            r0 = rv.iloc[k]
            for w in (12, 24, 36):
                hist = rv.iloc[max(0, k - w):k]
                row[f"rev_hi{w}"] = bool(len(hist) == w and hist.notna().all() and r0 >= hist.max())
            ly = rl.iloc[k]
            row["yoy"] = r0 / ly - 1 if (not np.isnan(ly) and ly > 0) else np.nan
            yoys = []
            for j in (k - 1, k - 2):
                if j >= 0 and not np.isnan(rv.iloc[j]) and not np.isnan(rl.iloc[j]) and rl.iloc[j] > 0:
                    yoys.append(rv.iloc[j] / rl.iloc[j] - 1)
                else:
                    yoys.append(np.nan)
            row["yoy_1"], row["yoy_2"] = yoys
        # 技術
        row["bull"] = bool(f.c[sp] > f.ma20[sp] > ma60[sp]) if not np.isnan(ma60[sp]) else False
        row["mom60"] = mom60[sp]
        # 估值
        if per is not None:
            row["per"], row["pbr"], row["yld"] = per["per"].iloc[sp], per["pbr"].iloc[sp], per["yield_pct"].iloc[sp]
        # 報酬
        for n in HOLDS:
            g, xp = _hold_ret(arr, ep, n)
            row[f"ret{n}"] = g
            row[f"bench{n}"] = (bench["c"][xp] / bench["o"][ep] - 1) if xp >= 0 and not np.isnan(bench["o"][ep]) else np.nan
        rows.append(row)
    return rows


# ---------- 統計與報表 ----------
def stats(df: pd.DataFrame, col: str, hold: int, baseline: float = 0.0) -> dict:
    d = df[[col, "stock_id", "entry_pos"]].dropna(subset=[col])
    x = d[col].to_numpy(float) - E.COST
    n = len(x)
    if n == 0:
        return {"n": 0}
    n_no = E.nonoverlap_count(d, gap=hold)
    mean = float(x.mean()); sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / np.sqrt(max(1, n_no))
    wins = x[x > 0]
    return {"n": n, "n_nonoverlap": n_no, "mean": mean, "median": float(np.median(x)), "se": se,
            "ci_lo": mean - 1.96 * se, "ci_hi": mean + 1.96 * se, "excess": mean - baseline,
            "excess_ci_lo": mean - baseline - 1.96 * se, "excess_ci_hi": mean - baseline + 1.96 * se,
            "win_rate": len(wins) / n, "worst": float(x.min()), "best": float(x.max())}


def _pct(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.2f}%"


def block(name: str, sel: pd.DataFrame, panel: pd.DataFrame, hold: int, split_pos: int, spread: pd.DataFrame | None = None) -> list[str]:
    """一個策略 × 一個持有期的表格與判定。spread：十分位差（每月一列，欄 'diff'）。"""
    col = f"ret{hold}"
    L = [f"#### {name}，持有 {hold} 日", ""]
    if spread is not None:
        if spread.empty or "diff" not in spread:
            return L + ["- 沒有足夠的月份（每月至少 50 檔才分十分位）。", ""]
        x = spread["diff"].dropna().to_numpy(float)
        pre = spread[spread["signal_pos"] < split_pos]["diff"].dropna().to_numpy(float)
        post = spread[spread["signal_pos"] >= split_pos]["diff"].dropna().to_numpy(float)
        if len(x) < 2:
            return L + ["- 沒有足夠的月份。", ""]
        # 月度差值：每月一個觀察，60 日持有時相鄰三個月重疊 → 有效 n 除以 (hold/20)
        eff = max(1, len(x) // max(1, hold // 20))
        se = x.std(ddof=1) / np.sqrt(eff)
        L.append(f"- 月份 {len(x)}（有效 {eff}）；差值平均 **{_pct(x.mean())}**，95% CI {_pct(x.mean() - 1.96 * se)} ~ {_pct(x.mean() + 1.96 * se)}；前段 {_pct(pre.mean()) if len(pre) else '—'}、後段 {_pct(post.mean()) if len(post) else '—'}；月勝率 {(x > 0).mean() * 100:.0f}%")
        ok = (x.mean() - 1.96 * se > 0) and len(pre) and len(post) and pre.mean() > 0 and post.mean() > 0
        L.append("- 判定：" + ("**通過事前門檻**" if ok else "**測不出效果**") + "。")
        return L + [""]
    base_all = panel[col].dropna().mean()
    base_pre = panel[panel["signal_pos"] < split_pos][col].dropna().mean()
    base_post = panel[panel["signal_pos"] >= split_pos][col].dropna().mean()
    s_all = stats(sel, col, hold, base_all - E.COST)
    s_pre = stats(sel[sel["signal_pos"] < split_pos], col, hold, base_pre - E.COST)
    s_post = stats(sel[sel["signal_pos"] >= split_pos], col, hold, base_post - E.COST)
    if s_all.get("n", 0) == 0:
        return L + ["- 沒有訊號。", ""]
    L.append("| 期間 | n | 非重疊 | 平均淨報酬 | 中位數 | 母體基準 | 超額 | 超額 CI | 勝率 | 最差 | 最好 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for lab, s, b in (("全期", s_all, base_all), ("前段", s_pre, base_pre), ("後段", s_post, base_post)):
        if s.get("n", 0) == 0:
            L.append(f"| {lab} | 0 | | | | | | | | | |"); continue
        L.append(f"| {lab} | {s['n']:,} | {s['n_nonoverlap']:,} | {_pct(s['mean'])} | {_pct(s['median'])} | {_pct(b - E.COST)} | **{_pct(s['excess'])}** | {_pct(s['excess_ci_lo'])} ~ {_pct(s['excess_ci_hi'])} | {s['win_rate'] * 100:.1f}% | {_pct(s['worst'])} | {_pct(s['best'])} |")
    if "bench20" in sel:
        L.append("")
        L.append(f"- 0050 同窗平均 {_pct(sel[f'bench{hold}'].mean())}")
    ok_n = s_all["n_nonoverlap"] >= 50
    c1 = s_all["excess_ci_lo"] > 0
    c2 = s_pre.get("n", 0) > 0 and s_post.get("n", 0) > 0 and s_pre["excess"] > 0 and s_post["excess"] > 0
    if not ok_n:
        v = f"**樣本不足**（非重疊 {s_all['n_nonoverlap']} < 50）"
    elif c1 and c2:
        v = "**通過事前門檻**"
    else:
        why = []
        if not c1:
            why.append("全期超額 CI 含 0" if s_all["excess"] > 0 else "全期超額 ≤ 0")
        if not c2:
            why.append(f"子期間不一致（前 {_pct(s_pre.get('excess', np.nan))}、後 {_pct(s_post.get('excess', np.nan))}）")
        v = "**測不出效果**：" + "；".join(why)
    L.append(f"- 判定：{v}。")
    return L + [""]


def decile_spread(panel: pd.DataFrame, feat: pd.Series, hold: int, low_is_good: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """每月依 feat 分十等份；回傳（第 10 分位列、第 1 分位列、每月差值表）。low_is_good=True 時差值 ＝ 低 − 高。"""
    col = f"ret{hold}"
    d = panel.loc[feat.notna() & panel[col].notna()].copy()
    d["_f"] = feat.loc[d.index]
    tops, bots, rows = [], [], []
    for p, g in d.groupby("period"):
        if len(g) < 50:
            continue
        q = g["_f"].rank(pct=True, method="first")   # 同值（例：殖利率 0）用序號打散，否則最低十分位會整月空掉
        top, bot = g[q > 0.9], g[q <= 0.1]
        tops.append(top); bots.append(bot)
        diff = (bot[col].mean() - top[col].mean()) if low_is_good else (top[col].mean() - bot[col].mean())
        rows.append({"period": p, "signal_pos": int(g["signal_pos"].iloc[0]), "diff": diff, "top": top[col].mean(), "bot": bot[col].mean()})
    return (pd.concat(tops) if tops else d.iloc[0:0]), (pd.concat(bots) if bots else d.iloc[0:0]), pd.DataFrame(rows)


def write_report(out: str, panel: pd.DataFrame, cal, split_pos: int, ind: pd.Series):
    L = ["# 研究三（營收動能）與研究四（價值型）——結果", ""]
    L.append(f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準見 `backtest/PREREG3.md`，面板見 `panel.csv.gz`。")
    L.append("")
    L.append(f"面板：{len(panel):,} 列（通過閘門的股票 × 月度換股日），{panel['stock_id'].nunique():,} 檔，{panel['period'].nunique()} 個換股日。")
    L.append("母體基準 ＝ 同一批換股日所有通過閘門股票的平均（扣成本）。")
    L.append("")
    for hold in HOLDS:
        col = f"ret{hold}"
        L.append(f"- 母體基準 持有 {hold} 日：全期 {_pct(panel[col].mean() - E.COST)}、前段 {_pct(panel[panel['signal_pos'] < split_pos][col].mean() - E.COST)}、後段 {_pct(panel[panel['signal_pos'] >= split_pos][col].mean() - E.COST)}")
    L.append("")

    yoy = panel["yoy"]
    strategies_g = {
        "G1 營收創 24 月新高": panel["rev_hi24"] == True,
        "G2 營收年增 ≥ 15%": yoy >= 0.15,
        "G2c 連三月年增 ≥ 15%": (yoy >= 0.15) & (panel["yoy_1"] >= 0.15) & (panel["yoy_2"] >= 0.15),
        "G3 創高 ＋ 多頭排列": (panel["rev_hi24"] == True) & panel["bull"],
        "C1 只有多頭排列（控制組）": panel["bull"] == True,
    }
    L.append("## 研究三：成長型（主表持有 20 日）"); L.append("")
    for hold in HOLDS:
        for name, m in strategies_g.items():
            L += block(name, panel[m.fillna(False)], panel, hold, split_pos)
        top, bot, sp = decile_spread(panel, yoy, hold)
        L += block("G4 年增率第 10 分位（最高）", top, panel, hold, split_pos)
        L += block("G4 年增率第 1 分位（最低）", bot, panel, hold, split_pos)
        L += block("G4 第 10 − 第 1 分位差", None, panel, hold, split_pos, spread=sp)
    # 拆解：G1 依前 60 日報酬中位數分半
    L.append("### 拆解：G1 依「訊號日前 60 日報酬」在當月母體的中位數分半"); L.append("")
    med = panel.groupby("period")["mom60"].transform("median")
    g1 = panel["rev_hi24"] == True
    for hold in HOLDS:
        for lab, m in (("已漲過（≥ 中位數）", g1 & (panel["mom60"] >= med)), ("未漲過（< 中位數）", g1 & (panel["mom60"] < med))):
            L += block(f"G1 {lab}", panel[m.fillna(False)], panel, hold, split_pos)

    L.append("## 研究四：價值型（主表持有 60 日）"); L.append("")
    v1 = (panel["per"] >= 8) & (panel["per"] <= 15) & (panel["pbr"] <= 1.5) & (panel["yld"] >= 4)
    for hold in (60, 20):
        L += block("V1 本益比 8～15 且股淨比 ≤ 1.5 且殖利率 ≥ 4%", panel[v1.fillna(False)], panel, hold, split_pos)
        for code, feat, lig in (("V2 本益比", panel["per"], True), ("V3 殖利率", panel["yld"], False), ("V4 股淨比", panel["pbr"], True)):
            top, bot, sp = decile_spread(panel, feat, hold, low_is_good=lig)
            good, bad = (bot, top) if lig else (top, bot)
            L += block(f"{code}：{'最低' if lig else '最高'}十分位", good, panel, hold, split_pos)
            L += block(f"{code}：{'最高' if lig else '最低'}十分位", bad, panel, hold, split_pos)
            L += block(f"{code}：{'低 − 高' if lig else '高 − 低'}", None, panel, hold, split_pos, spread=sp)

    L.append("## 敏感度"); L.append("")
    excl = panel["stock_id"].map(ind).isin(["金融保險業", "金融業", "生技醫療業"])
    L.append(f"排除金融保險與生技醫療（依營收檔產業別，{int(excl.sum()):,} 列）：")
    L.append("")
    for name, m in (("G1 創 12 月新高", panel["rev_hi12"] == True), ("G1 創 36 月新高", panel["rev_hi36"] == True),
                    ("G2 年增 ≥ 10%", yoy >= 0.10), ("G2 年增 ≥ 25%", yoy >= 0.25),
                    ("G1 創 24 月新高，排除金融生技", (panel["rev_hi24"] == True) & ~excl),
                    ("G2 年增 ≥ 15%，排除金融生技", (yoy >= 0.15) & ~excl),
                    ("V1，排除金融生技", v1 & ~excl)):
        hold = 60 if name.startswith("V") else 20
        s = stats(panel[m.fillna(False)], f"ret{hold}", hold, panel[f"ret{hold}"].mean() - E.COST)
        if s.get("n", 0):
            L.append(f"- {name}（持有 {hold} 日）：n {s['n']:,}，淨報酬 {_pct(s['mean'])}，超額 **{_pct(s['excess'])}**（CI {_pct(s['excess_ci_lo'])} ~ {_pct(s['excess_ci_hi'])}）")
    L.append("")
    L.append("## 必須揭露")
    L.append("")
    L.append("- 營收以「次月 10 日之後第一個交易日」為可用日；提早申報的公司實際可更早，這裡偏保守。")
    L.append("- 殖利率是交易所依上一年度現金股利算的歷史值，不是預期值。")
    L.append("- ROE 與負債比未納入（見 PREREG3）；股淨比 ＝ 本益比 × ROE，原比較表的三個門檻同時成立會排除高 ROE 公司。")
    L.append("- 持有 60 日時每檔相鄰三個月的訊號重疊，標準誤用非重疊筆數；十分位差用「月份數 ÷ 3」當有效觀察數。")
    L.append("- 上櫃還原因子來自 FinMind；面額變更跳價已剔除（同研究二更正二）。")
    with open(os.path.join(out, "summary.md"), "w") as fh:
        fh.write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stocks", nargs="*"); ap.add_argument("--limit", type=int)
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--report-only", action="store_true", help="只用既有 panel.csv.gz 重做報表")
    ap.add_argument("--liq", choices=["shares", "amount"], default="shares", help="流動性閘門：shares＝500 張（主表）；amount＝近 20 日成交金額均值 ≥ 5,000 萬（PREREG3 更正三）")
    a = ap.parse_args()
    P.PARAMS["liq_mode"] = a.liq          # 在建 Pool 之前改，fork 出去的 worker 才會帶到
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    if a.report_only:
        _, _, ind = load_revenue()
        panel = pd.read_csv(os.path.join(a.out, "panel.csv.gz"))
        for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
            panel[c] = panel[c].astype("boolean")
        write_report(a.out, panel, cal, int(cal.searchsorted(pd.Timestamp(SPLIT))), ind)
        return
    if a.stocks:
        uni = uni[uni["stock_id"].isin(a.stocks)]
    if a.limit:
        uni = uni.head(a.limit)
    bdf = D.load_benchmark(cal)
    bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = load_revenue()
    rdates = rebalance_dates(list(rev.index), cal)
    lo = int(cal.searchsorted(pd.Timestamp(SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
    split = int(cal.searchsorted(pd.Timestamp(SPLIT)))
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    print(f"母體 {len(jobs)} 檔，營收 {rev.shape[0]} 期 × {rev.shape[1]} 檔，換股日 {len(rdates)}", file=sys.stderr)
    rows = []
    if a.procs <= 1 or len(jobs) <= 4:
        _init(cal, bench, disp, rev, rev_ly, rdates, lo, hi)
        for j in jobs:
            r = process_stock(j)
            if r:
                rows += r
    else:
        with Pool(a.procs, initializer=_init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
            for i, r in enumerate(pool.imap_unordered(process_stock, jobs, chunksize=8)):
                if r:
                    rows += r
                if (i + 1) % 300 == 0:
                    print(f"  {i + 1}/{len(jobs)}  {time.time() - t0:.0f}s", file=sys.stderr)
    panel = pd.DataFrame(rows)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in panel:
            panel[c] = panel[c].astype("boolean")
    os.makedirs(a.out, exist_ok=True)
    panel["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["signal_pos"]]
    panel["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["entry_pos"]]
    panel.to_csv(os.path.join(a.out, "panel.csv.gz"), index=False, compression="gzip")
    print(f"面板 {len(panel)} 列，{time.time() - t0:.0f}s", file=sys.stderr)
    write_report(a.out, panel, cal, split, ind)


if __name__ == "__main__":
    main()

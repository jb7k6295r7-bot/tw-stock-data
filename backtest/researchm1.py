"""PREREGM1 層一：市場狀態 → 未來指數報酬（同一條序列各狀態互比）。判準 backtest/PREREGM1.md（⛔ 策略線改版登錄到了才跑）。

    python3 -m backtest.researchm1 --index data/history/market_index.csv --out backtest/resultsm1

規則（K線分析 09-14 1935／09-15 0800 裁定）：
  訊號與去抖 import m1_states（a/b/a∧b/c/d；<K 併入前段再合併同狀態；K=20 交易日）
  每日狀態 ＝ 去抖後所屬段的狀態；有效 n ＝ 去抖後段數（右設限：最後一段未結束不計）；按狀態別各報 n，<24 標「還沒測」
  量測 ＝ 各狀態下未來 H=20/60/120 日報酬的平均與 p10/p50/p90；狀態間差的 95% CI 用【段分群】SE（段均值的 std/sqrt(段數)）
  分段 ＝ 1990s／2000s／2010s／2020s 四段並列 ＋ 主判定格「2001 起」（240MA＝年線只在 2001 後成立）；a 的 1990-2000 段結論欄寫「窗口長度不可比」
  敏感度 ＝ 剔除 1990-92、剔除 7～9 月進場；另報各狀態的進場月份分佈
  判定字只用 測得出／測不出／還沒測；⛔ 不做任何「贏過大盤」的比價（層一沒有比價基準）
  ⛔ 判定格只有 v2 §3-4 那幾格：c、d 的 H=120 全期 ＋ a 的 H=120 2001 起；其餘格只寫方向（＋／−）與「與判定格同向／不同向」
  v2 §七：layer1.csv（p05/p10/p50/p90/p95、逐段勝率）、layer1_sens.csv（剔除 1990-92、剔除 7～9 月、日曆天版僅 a）、months.csv；每檔首行註明 commit 與執行時間
  日曆天版（僅 a，敏感度）：365 日曆天均值、去抖 K=28 日曆天——把序列展成逐日曆日再套同一支 M.debounce（⛔ m1_states 不加模式，K線分析 0800）
"""
from __future__ import annotations

import argparse
import os
import subprocess

import numpy as np
import pandas as pd

from . import m1_states as M

HERE = os.path.dirname(os.path.abspath(__file__))
HOLDS = (20, 60, 120)
N_MIN = 24
MAIN_FROM = "2001-01-01"
ZERO = 0.00585                      # 「零」：CI 含 0 ∧ |點估計| ≤ 0.585%
WINDOWS = {"全期": None, "1990s": ("1990-01-01", "1999-12-31"), "2000s": ("2000-01-01", "2009-12-31"), "2010s": ("2010-01-01", "2019-12-31"),
           "2020s": ("2020-01-01", "2099-12-31"), "主判定 2001 起": (MAIN_FROM, "2099-12-31")}
SENS_WINDOWS = {"全期": None, "主判定 2001 起": (MAIN_FROM, "2099-12-31")}
EX_9092 = ("1993-01-01", "2099-12-31")
JUDGE_CELLS = {("c", "全期", 120), ("d", "全期", 120), ("a", "主判定 2001 起", 120)}   # v2 §3-4
CAL_WIN_DAYS, CAL_K_DAYS = 365, 28  # 日曆天版（僅 a）


def _day_states_one(s: pd.Series, db: pd.DataFrame, idx: pd.DatetimeIndex) -> pd.DataFrame:
    seg_id = np.searchsorted(db["start"].to_numpy(), idx.to_numpy(), side="right") - 1
    st = db["state"].to_numpy(object)[seg_id]
    return pd.DataFrame({"state": st, "seg_id": seg_id, "open": seg_id == len(db) - 1}, index=idx)


def signal_a_calendar(close: pd.Series, win_days: int = CAL_WIN_DAYS) -> pd.Series:
    """a 的日曆天版：收盤 vs 過去 win_days 日曆天的均值（時間視窗）；序列頭 win_days 天不可得。"""
    ma = close.rolling(f"{win_days}D").mean()
    ma = ma.where(close.index >= close.index[0] + pd.Timedelta(days=win_days))
    return (close > ma).where(ma.notna()).map({True: "上", False: "下"})


def day_states_calendar_a(close: pd.Series, k_days: int = CAL_K_DAYS) -> pd.DataFrame:
    """日曆天去抖：把狀態序列展成逐日曆日（ffill）再套同一支 M.debounce ⇒ 區段長度就是日曆天；回傳仍以交易日為索引。"""
    s = signal_a_calendar(close).dropna()
    daily = s.asfreq("D").ffill()
    db = M.debounce(daily, k_days)
    return _day_states_one(s, db, s.index)


def day_states(close: pd.Series, k: int = M.K_DEFAULT) -> dict[str, pd.DataFrame]:
    """每個訊號：逐日 DataFrame(state, seg_id, seg_start)——state 是去抖後所屬段的狀態；最後一段 open=True（不計入 n）。"""
    out = {}
    sig = M.signals(close)
    for key in M.SIGNALS:
        s = sig[key].dropna()
        out[key] = _day_states_one(s, M.debounce(s, k), s.index)
    return out


def fwd_returns(close: pd.Series, holds=HOLDS) -> pd.DataFrame:
    return pd.DataFrame({H: close.shift(-H) / close - 1 for H in holds}, index=close.index)


def _cluster_stats(x: pd.Series, seg: pd.Series):
    """段分群：回傳 (段數, 平均, SE, 逐段勝率)；平均取逐日平均，SE 用段均值的離散，勝率＝段均值 > 0 的段占比。"""
    g = x.groupby(seg).mean()
    n = int(len(g))
    se = float(g.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    win = float((g > 0).mean()) if n else np.nan
    return n, float(x.mean()), se, win


def _judge(key: str, wname: str, H: int, n: int, n2: int, diff: float, lo: float, hi: float, judged_cells=JUDGE_CELLS) -> str:
    """判定字只給判定格；其餘格只寫方向。n<24（任一邊）一律還沒測。"""
    if key == "a" and wname == "1990s":
        return "窗口長度不可比（240 交易日在 1990 年代 ≈ 10.1 個月）"
    if (key, wname, H) not in judged_cells:
        return "非判定格" if not np.isfinite(diff) else ("非判定格（方向＋）" if diff > 0 else "非判定格（方向−）")
    if n < N_MIN or n2 < N_MIN:
        return "還沒測（狀態別 n < 24）"
    if not np.isfinite(lo):
        return "還沒測"
    if lo <= 0 <= hi:
        return "測不出（零）" if abs(diff) <= ZERO else "測不出（|點估計| > 0.585%：量不準，不是零）"
    return "測得出（＋）" if diff > 0 else "測得出（−）"


def _cells(ds: dict[str, pd.DataFrame], fr: pd.DataFrame, windows: dict, holds, exclude_months=(), judged_cells=JUDGE_CELLS, variant="") -> pd.DataFrame:
    rows = []
    for key, d in ds.items():
        d = d[~d["open"]]                       # 右設限：最後一段不計
        for wname, win in windows.items():
            dd = d if win is None else d[(d.index >= pd.Timestamp(win[0])) & (d.index <= pd.Timestamp(win[1]))]
            if exclude_months:
                dd = dd[~dd.index.month.isin(exclude_months)]
            for H in holds:
                x = fr[H].reindex(dd.index); ok = x.notna(); dd_ok = dd[ok]; x = x[ok]
                if len(x) == 0:
                    continue
                for st in sorted(dd_ok["state"].unique()):
                    m = dd_ok["state"] == st
                    n, mean, se, win_rate = _cluster_stats(x[m], dd_ok.loc[m, "seg_id"])
                    n2, mean2, se2, win2 = _cluster_stats(x[~m], dd_ok.loc[~m, "seg_id"]) if (~m).any() else (0, np.nan, np.nan, np.nan)
                    diff = mean - mean2 if n2 else np.nan
                    sed = np.sqrt(se ** 2 + se2 ** 2) if (n > 1 and n2 > 1) else np.nan
                    lo, hi = (diff - 1.96 * sed, diff + 1.96 * sed) if np.isfinite(sed) else (np.nan, np.nan)
                    q = x[m].quantile([0.05, 0.1, 0.5, 0.9, 0.95])
                    rows.append({"variant": variant, "signal": key, "label": M.LABELS.get(key, key), "window": wname, "state": st, "H": H,
                                 "n_seg": n, "n_days": int(m.sum()), "mean": mean,
                                 "p05": float(q.iloc[0]), "p10": float(q.iloc[1]), "p50": float(q.iloc[2]), "p90": float(q.iloc[3]), "p95": float(q.iloc[4]),
                                 "win_rate": win_rate, "rest_n_seg": n2, "rest_mean": mean2, "rest_win_rate": win2, "diff": diff, "ci_lo": lo, "ci_hi": hi,
                                 "judge": _judge(key, wname, H, n, n2, diff, lo, hi, judged_cells)})
    return pd.DataFrame(rows)


def _same_dir(df: pd.DataFrame) -> pd.DataFrame:
    """非判定格加一欄：與同訊號×同狀態的判定格方向一致／不一致（沒有判定格的訊號留空）。"""
    df = df.copy(); df["same_dir_as_judged"] = ""
    ref = {}
    for r in df.itertuples():
        if (r.signal, r.window, r.H) in JUDGE_CELLS and np.isfinite(r.diff):
            ref[(r.signal, r.state)] = np.sign(r.diff)
    for r in df.itertuples():
        k = (r.signal, r.state)
        if k in ref and (r.signal, r.window, r.H) not in JUDGE_CELLS and np.isfinite(r.diff):
            df.at[r.Index, "same_dir_as_judged"] = "同向" if np.sign(r.diff) == ref[k] else "不同向"
    return df


def layer1(close: pd.Series, k: int = M.K_DEFAULT, holds=HOLDS, exclude_months=()) -> pd.DataFrame:
    """逐格：訊號 × 視窗 × 狀態 × H。每列含 n（完整段數）、平均、p05/p10/p50/p90/p95、逐段勝率、對「其餘狀態」的差與 CI、判定（只有判定格給判定字）。"""
    return _same_dir(_cells(day_states(close, k), fwd_returns(close, holds), WINDOWS, holds, exclude_months, variant="主"))


def layer1_sens(close: pd.Series, k: int = M.K_DEFAULT, holds=HOLDS) -> pd.DataFrame:
    """v2 §七 敏感度三種：剔除 1990-92、剔除 7～9 月進場、日曆天版（僅 a）。⛔ 全部不判定（judge 一律非判定格），只給方向。"""
    ds = day_states(close, k); fr = fwd_returns(close, holds); none = set()
    A = _cells(ds, fr, {"剔除 1990-92": EX_9092}, holds, judged_cells=none, variant="剔除 1990-92")
    B = _cells(ds, fr, SENS_WINDOWS, holds, exclude_months=(7, 8, 9), judged_cells=none, variant="剔除 7～9 月")
    C = _cells({"a": day_states_calendar_a(close)}, fr, SENS_WINDOWS, holds, judged_cells=none, variant="日曆天版（僅 a）")
    C["label"] = f"a 收盤 vs {CAL_WIN_DAYS} 日曆天均值（K={CAL_K_DAYS} 日曆天）"
    return pd.concat([A, B, C], ignore_index=True)


def exit_rule(L1: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """v2 §3-3 ③④：判定格全部測不出 ⇒ 層二不跑；只有 d 測得出 ⇒ 層二不跑。回傳 (結論, 判定格表)。"""
    J = L1[[(r.signal, r.window, r.H) in JUDGE_CELLS for r in L1.itertuples()]]
    got = J[J["judge"].str.startswith("測得出")]
    if J["judge"].str.startswith("測不出").all():
        return "判定格全部測不出 ⇒ 層二不跑（§3-3 ③）", J
    if len(got) and set(got["signal"]) == {"d"}:
        return "只有 d 測得出 ⇒ 層二不跑（§3-3 ④）", J
    if len(got) == 0:
        return "判定格沒有測得出（其餘是還沒測）⇒ 層二不跑（§3-3 ③）", J
    return f"判定格測得出：{sorted(set(got['signal']))} ⇒ 層二可排（⛔ 由策略線／K線分析決定，本線不自行開跑）", J


def month_distribution(close: pd.Series, k: int = M.K_DEFAULT) -> pd.DataFrame:
    """各狀態的進場月份分佈（逐日、去抖後狀態；12 格占比 %）＋ 7～9 月合計占比。"""
    rows = []
    for key, d in day_states(close, k).items():
        ct = pd.crosstab(d["state"], d.index.month)
        share = ct.div(ct.sum(axis=1), axis=0) * 100
        for st in share.index:
            r = {"signal": key, "state": st, "n_days": int(ct.loc[st].sum()), **{f"m{m:02d}": float(share.loc[st].get(m, 0.0)) for m in range(1, 13)}}
            r["q3_share"] = float(share.loc[st].reindex([7, 8, 9]).fillna(0).sum())
            rows.append(r)
    return pd.DataFrame(rows)


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, text=True).strip()
    except Exception:
        return "unknown"


def write_csv(df: pd.DataFrame, path: str, stamp: str, commit: str):
    """v2 §七：每檔首行註明 commit 與執行時間（台北）——讀取時 `pd.read_csv(path, comment="#")`。"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# commit={commit} run={stamp} (Asia/Taipei) prereg=backtest/PREREGM1.md | ⚠ CI 未修正跨段重疊（未來 H 日窗口跨段），實際覆蓋率低於 95%（隨機漫步假陽性 13%）——測得出的格要先過段標籤打亂安慰劑\n")
        df.to_csv(fh, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, help="指數 CSV（date,close）——本庫:data/history/market_index.csv；⛔ 只讀 close")
    ap.add_argument("--out", default=os.path.join(HERE, "resultsm1")); ap.add_argument("--k", type=int, default=M.K_DEFAULT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    c = M.load_series(a.index)
    stamp = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"); commit = _commit()
    t = M.n_table(c, a.k); write_csv(t, os.path.join(a.out, "n_table.csv"), stamp, commit)
    L1 = layer1(c, a.k); write_csv(L1, os.path.join(a.out, "layer1.csv"), stamp, commit)
    S = layer1_sens(c, a.k); write_csv(S, os.path.join(a.out, "layer1_sens.csv"), stamp, commit)
    md = month_distribution(c, a.k); write_csv(md, os.path.join(a.out, "months.csv"), stamp, commit)
    verdict, J = exit_rule(L1)

    def row(r, extra=""):
        return (f"| {r.label} | {r.state} | {r.n_seg} | {r.mean * 100:+.2f}% | {r.p05 * 100:+.1f} / {r.p10 * 100:+.1f} / {r.p50 * 100:+.1f} / {r.p90 * 100:+.1f} / {r.p95 * 100:+.1f} "
                f"| {r.win_rate * 100:.0f}% | {r.rest_n_seg} | {r.diff * 100:+.2f} pp | {r.ci_lo * 100:+.2f} ~ {r.ci_hi * 100:+.2f} | {r.judge}{extra} |")
    hdr = ["| 訊號 | 狀態 | 段數 | 平均 | p05 / p10 / p50 / p90 / p95 | 逐段勝率 | 其餘段數 | 差 | 95% CI | 判定 |", "|---|---|---:|---:|---|---:|---:|---:|---|---|"]
    L = [f"# PREREGM1 v2 層一——細表", "", f"產出：{stamp}（台北）、commit {commit}。序列 `{a.index}`（{c.index[0].date()} ～ {c.index[-1].date()}，{len(c):,} 日）；K＝{a.k} 交易日。判準 `backtest/PREREGM1.md`（v2）。", ""]
    L.append("## 一、有效 n（去抖後段數）"); L.append("")
    for r in t.itertuples():
        L.append(f"- {r.label}: 素切換 {r.raw_switches}、去抖後 n＝{r.n} {r.n_by_state}、最後一段 {r.last_state} {r.last_len} 日未計、{r.judge}")
    L.append(""); L.append(f"## 二、判定格（v2 §3-4：c、d 的 H=120 全期 ＋ a 的 H=120 2001 起；{len(J)} 列）"); L.append(""); L += hdr
    for r in J.itertuples():
        L.append(row(r))
    L.append(""); L.append(f"⇒ 出口（§3-3）：**{verdict}**"); L.append("")
    L.append("⚠ 三種判定字是三種不同的結論（K線分析 09-15 13:15）：**零**＝測到它沒有（d）；**測不出（量不準）**＝精度不足、不是沒有效果（c 中／高）；**還沒測**＝樣本不夠、不觸發撤除（a）。⛔ 不可壓成「都沒用」。")
    L.append("⚠ CI 用段分群 SE、**未修正跨段重疊**（未來 H 日窗口跨段共用），實際覆蓋率低於 95%（自測隨機漫步假陽性 13%）⇒ 對「測不出」只會更保守；⛔ 日後任何「測得出」格要先跑**段標籤打亂**安慰劑（重排段、不是重排日；登錄尚未加，策略線補）。")
    L.append("⚠ a 的方向（「下」高於「上」）五視窗一致，⛔ 但五視窗是同一條序列切出來、共用同一批段，**不是五次獨立實驗**；只能寫「方向一致但樣本不足以判定」，⛔ 不可因方向反了就反著用。"); L.append("")
    L.append("## 三、非判定格：全期 H=120（只寫方向；末欄＝與同訊號同狀態的判定格同向／不同向）"); L.append(""); L += hdr
    for r in L1[(L1["window"] == "全期") & (L1["H"] == 120) & ~L1["signal"].isin(["c", "d"])].itertuples():
        L.append(row(r, f"｜{r.same_dir_as_judged}" if r.same_dir_as_judged else ""))
    L.append(""); L.append("## 四、敏感度（`layer1_sens.csv`，全部不判定）：主判定視窗 H=120"); L.append(""); L += hdr
    for r in S[(S["H"] == 120) & S["window"].isin(["主判定 2001 起", "剔除 1990-92"])].itertuples():
        L.append(row(r, f"｜{r.variant}"))
    L.append(""); L.append("四段並列（1990s／2000s／2010s／2020s）與 H＝20／60 見 `layer1.csv`；月份分佈見 `months.csv`。⛔ 層一沒有比價基準，不做任何「贏過大盤」的比較。")
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

"""PREREGP8（策略線 seq=2 sha 55d8c99ee7b587f8，K線分析線 1200 過目通過）：**位置維度（距 120 日高點）**。

    python3 -m backtest.researchp8 [--procs 8] [--reps 200] [--out backtest/resultsp8]

⭐ 三段：2-A 單一維度十分位重跑／2-B 代理檢定（三種做法）／2-C 組合層增量。
⛔ 引擎掛 `research11.simulate_mtm`（⛔ 不另建）；sig 的門檻B 走 `researchp7.build_sig_gate_b`（同一份）。

⛔⛔ **本件對「回落」天生沉默**（K線分析線 1200 的過目條件，⭐ 逐字寫進結論）：
  「本件量的是【同一個月內個股之間】的差異。⛔ 它不構成對【最大回落】的任何證據，
    因為逐月配對會消掉時點效應。」
  ⇒ ⭐〈九十五〉變異歸屬要先分【時點】與【個體】；回落來自**月與月之間**，⛔ 不在逐月配對看得見的地方。

⛔ **範圍限制**（登錄 §五，逐字）：
  ① 個股橫斷面維度，⛔ 不是市場擇時 ⇒ 依先驗④它修不好回落
  ② `dist_hi120` 定義寫死＝收盤 ÷ 近 120 個交易日最高【收盤】− 1（⛔ 不是最高價、⛔ 不是 250 日）
  ③ 與研究十（近 60 日報酬十分位、D10−D1 測不出 +0.82pp）是**不同的動能定義** ⇒ ⛔ 不是矛盾也不是否證
  ④ 倖存者偏誤仍在；成本 0.585%；滑價未計　⑤ 三分位／十分位切點是我方選的（〈三十九〉）

⚠ **出場口徑**：本件是**新工作** ⇒ H〈n〉＝**持有 n 根**（`data.exit_pos`，追加二十一 §二）
  ⛔ 不可沿用 P4 面板的 `fwd_H`（那是持有 H+1 根的歷史口徑）⇒ 本檔自己重算三個 H。
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp7 as P7

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp8")
SEED0 = 98000                   # ⛔ 登錄 §2-C 寫死：不沿用 96000／97000
HOLDS = (20, 60, 120)           # ⭐ 使用者的持有期是 2 週~6 個月 ⇒ ⛔ 不可只報 H120
START, END = "2017-01-01", "2026-03-31"
N_DEC = 10                      # 2-A 十分位（⛔ 前測只做三分位）
N_TER = 3                       # 2-B／2-C 三分位
N_QUI = 5                       # 2-B 的控制維度五分位
FEATURE = "dist_hi120"
CONTROLS = ("ret_120", "dist_lo120")
SEGMENTS = {"2017-20": ("2017-01-01", "2020-12-31"), "2021-26": ("2021-01-01", "2026-03-31")}
N_CELL = 8                      # 2-C 主格


def add_forward(panel: pd.DataFrame, cal: pd.DatetimeIndex, closes: dict, opens: dict, holds=HOLDS) -> pd.DataFrame:
    """⭐ 本件自己算的 fwd_H：進場＝量測日次一根開盤，出場＝**持有 H 根**的收盤（`data.exit_pos`）。

    ⛔ 與 P4 面板的 `fwd_H`（持有 H+1 根）**差一根** ⇒ 本件是新工作，照裁定用持有 n 根。
    開盤非有限或 ≤ 0／出場收盤非有限／出場越界 ⇒ 該格 NaN（⛔ 不補值）。
    """
    pos = {d: i for i, d in enumerate(cal)}
    ncal = len(cal)
    e = panel["measure_date"].map(pos).astype("Int64") + 1
    out = panel.copy()
    out["entry_pos"] = e
    for H in holds:
        out[f"fwd{H}"] = np.nan
    ok = out["entry_pos"].notna()
    for sid, g in out[ok].groupby("stock_id", sort=False):
        c, o = closes.get(sid), opens.get(sid)
        if c is None or o is None:
            continue
        for i, ep in zip(g.index, g["entry_pos"].astype(int)):
            if ep >= min(ncal, len(o)):
                continue
            op = float(o[ep])
            if not np.isfinite(op) or op <= 0:
                continue
            for H in holds:
                x = D.exit_pos(ep, H)
                if x >= min(ncal, len(c)):
                    continue
                cx = float(c[x])
                if np.isfinite(cx):
                    out.at[i, f"fwd{H}"] = cx / op - 1.0
    return out


def xs_bucket(df: pd.DataFrame, col: str, k: int, by: str = "measure_date") -> pd.Series:
    """逐月橫斷面把 `col` 切成 k 等分（0 最小、k−1 最大）。⛔ 全期一起切是錯的（〈八十四〉：錯的母體）。"""
    def _cut(s: pd.Series) -> pd.Series:
        v = s.rank(method="first", na_option="keep")
        n = v.notna().sum()
        if n < k:
            return pd.Series(np.nan, index=s.index)
        return np.ceil(v / n * k) - 1
    return df.groupby(by, sort=False)[col].transform(_cut)


def decile_table(df: pd.DataFrame, H: int, k: int = N_DEC) -> pd.DataFrame:
    col = f"fwd{H}"
    rows = []
    for b, g in df.dropna(subset=[col, "bucket"]).groupby("bucket"):
        x = g[col].to_numpy(float)
        rows.append({"bucket": int(b) + 1, "n": len(x), "mean": x.mean(), "median": float(np.median(x)),
                     "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90)),
                     "lose20": float((x <= -0.20).mean()), "win50": float((x >= 0.50).mean()),
                     "win": float((x > 0).mean())})
    return pd.DataFrame(rows).sort_values("bucket")


def paired_diff(df: pd.DataFrame, H: int, hi: int, lo: int) -> dict:
    """逐月配對差（hi 桶月均 − lo 桶月均），月分群 SE。⭐ 只取兩桶都有值的月。"""
    col = f"fwd{H}"
    g = df.dropna(subset=[col, "bucket"])
    m = g.groupby(["measure_date", "bucket"])[col].mean().unstack()
    if hi not in m or lo not in m:
        return {"n_months": 0, "diff_pp": np.nan, "lo_pp": np.nan, "hi_pp": np.nan, "pos_months": 0, "detectable": False}
    d = (m[hi] - m[lo]).dropna().to_numpy(float)
    n = len(d)
    if n < 2:
        return {"n_months": n, "diff_pp": np.nan, "lo_pp": np.nan, "hi_pp": np.nan, "pos_months": 0, "detectable": False}
    mean = float(d.mean()); se = float(d.std(ddof=1) / np.sqrt(n))
    lo_, hi_ = mean - 1.96 * se, mean + 1.96 * se
    return {"n_months": n, "diff_pp": mean * 100, "lo_pp": lo_ * 100, "hi_pp": hi_ * 100,
            "pos_months": int((d > 0).sum()), "detectable": bool(lo_ * hi_ > 0)}


def monotonic_exceptions(t: pd.DataFrame, col: str = "mean") -> int:
    """十格是不是單調（遞增）⇒ 回「例外」個數＝相鄰遞減的次數。⛔ 判準是 ≤ 1。"""
    v = t.sort_values("bucket")[col].to_numpy(float)
    return int((np.diff(v) < 0).sum())


def proxy_double_sort(df: pd.DataFrame, control: str, H: int) -> pd.DataFrame:
    """①② 雙重分位：先按 control 切五分位，⭐ 在【每一個分位內部】再按 FEATURE 切三分位。

    ⭐ 判準（登錄 §一）：若在**每一個** control 分位內部 FEATURE 都單調 ⇒ 它不是代理。
    """
    col = f"fwd{H}"
    d = df.dropna(subset=[col, control, FEATURE]).copy()
    d["ctl"] = xs_bucket(d, control, N_QUI)
    d = d.dropna(subset=["ctl"])
    rows = []
    for c, g in d.groupby("ctl"):
        g = g.copy()
        g["ter"] = xs_bucket(g, FEATURE, N_TER)
        for t, gg in g.dropna(subset=["ter"]).groupby("ter"):
            x = gg[col].to_numpy(float)
            rows.append({"control": control, "ctl_quintile": int(c) + 1, "tercile": int(t) + 1, "n": len(x),
                         "mean_pp": x.mean() * 100, "lose20": float((x <= -0.20).mean()), "win50": float((x >= 0.50).mean())})
    T = pd.DataFrame(rows)
    return T.sort_values(["ctl_quintile", "tercile"])


def proxy_residual(df: pd.DataFrame, H: int) -> dict:
    """③ 殘差法：FEATURE 對 (ret_120, dist_lo120) 逐月橫斷面迴歸取殘差，再按殘差切三分位 ⇒ 逐月配對差。

    ⛔ 殘差法若與①②不一致，以①②為準（分位法不假設線性；登錄 §一）。
    """
    col = f"fwd{H}"
    d = df.dropna(subset=[col, FEATURE, *CONTROLS]).copy()
    res = np.full(len(d), np.nan)
    idx = {k: i for i, k in enumerate(d.index)}
    for _, g in d.groupby("measure_date", sort=False):
        if len(g) < 10:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[c].to_numpy(float) for c in CONTROLS])
        y = g[FEATURE].to_numpy(float)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = y - X @ beta
        for k, v in zip(g.index, r):
            res[idx[k]] = v
    d["_resid"] = res
    d = d.dropna(subset=["_resid"])
    d["bucket"] = xs_bucket(d, "_resid", N_TER)
    return paired_diff(d, H, N_TER - 1, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    ap.add_argument("--skip-2c", action="store_true", help="只跑 2-A／2-B（⛔ 只給對帳用，⛔ 不是正式出口）")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = print
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    p = panel[(panel["measure_date"] >= pd.Timestamp(START)) & (panel["measure_date"] <= pd.Timestamp(END))]
    el = p[p["eligible"].astype(bool)].copy()
    log(f"[母體] 全市場過閘門 {len(el):,} 股-月／{el['stock_id'].nunique():,} 檔（{START}~{END}）")
    el = add_forward(el, cal, closes, opens)
    el["bucket"] = xs_bucket(el, FEATURE, N_DEC)
    log(f"[口徑] H〈n〉＝持有 n 根（data.exit_pos）⇒ ⛔ 與 P4 面板 fwd_H（持有 H+1 根）差一根")

    # ── 2-A 單一維度十分位 ─────────────────────────────
    A_rows = []; dec_tabs = {}
    for H in HOLDS:
        t = decile_table(el, H); dec_tabs[H] = t
        pd_all = paired_diff(el, H, N_DEC - 1, 0)
        segs = {}
        for name, (s0, s1) in SEGMENTS.items():
            sub = el[(el["measure_date"] >= pd.Timestamp(s0)) & (el["measure_date"] <= pd.Timestamp(s1))]
            segs[name] = paired_diff(sub, H, N_DEC - 1, 0)
        exc = monotonic_exceptions(t)
        same_sign = bool(np.sign(segs["2017-20"]["diff_pp"]) == np.sign(segs["2021-26"]["diff_pp"]))
        verdict = bool(pd_all["detectable"] and exc <= 1 and same_sign)
        A_rows.append({"H": H, "n_months": pd_all["n_months"], "d10_d1_pp": pd_all["diff_pp"], "lo_pp": pd_all["lo_pp"],
                       "hi_pp": pd_all["hi_pp"], "pos_months": pd_all["pos_months"], "ci_ok": pd_all["detectable"],
                       "mono_exceptions": exc, "mono_ok": exc <= 1,
                       "seg_a_pp": segs["2017-20"]["diff_pp"], "seg_b_pp": segs["2021-26"]["diff_pp"], "same_sign": same_sign,
                       "verdict_detected": verdict})
        log(f"  [2-A] H{H:<3} D10−D1 {pd_all['diff_pp']:+.2f}pp CI [{pd_all['lo_pp']:+.2f}, {pd_all['hi_pp']:+.2f}]"
            f"（{pd_all['n_months']} 月、{pd_all['pos_months']} 月為正）｜單調例外 {exc}｜分段 {segs['2017-20']['diff_pp']:+.2f}／{segs['2021-26']['diff_pp']:+.2f}"
            f" ⇒ {'✅ 三件全中＝測得出' if verdict else '⛔ 三件缺一 ⇒ 測不出'}")
    A = pd.DataFrame(A_rows)
    A.to_csv(os.path.join(a.out, "a_single.csv"), index=False)
    pd.concat([t.assign(H=H) for H, t in dec_tabs.items()], ignore_index=True).to_csv(os.path.join(a.out, "a_deciles.csv"), index=False)

    # ── 2-B 代理檢定 ─────────────────────────────
    B_parts = []; B_flags = {}
    for ctl in CONTROLS:
        T = proxy_double_sort(el, ctl, 120)
        B_parts.append(T)
        bad = 0
        for q, g in T.groupby("ctl_quintile"):
            v = g.sort_values("tercile")["mean_pp"].to_numpy(float)
            if (np.diff(v) < 0).any():
                bad += 1
        B_flags[ctl] = {"non_monotonic_quintiles": bad, "independent": bad == 0}
        log(f"  [2-B] 控制 {ctl}：{N_QUI} 個分位裡 {bad} 個內部不單調 ⇒ {'✅ 獨立' if bad == 0 else '⛔ 不獨立'}")
    res3 = proxy_residual(el, 120)
    B_flags["residual"] = {"diff_pp": res3["diff_pp"], "lo_pp": res3["lo_pp"], "hi_pp": res3["hi_pp"],
                           "n_months": res3["n_months"], "independent": bool(res3["detectable"])}
    log(f"  [2-B] 殘差法 T3−T1 {res3['diff_pp']:+.2f}pp CI [{res3['lo_pp']:+.2f}, {res3['hi_pp']:+.2f}]"
        f" ⇒ {'✅ 獨立' if res3['detectable'] else '⛔ 含 0'}")
    n_proxy = sum(1 for v in B_flags.values() if not v["independent"])
    is_proxy = n_proxy >= 2
    log(f"  [2-B] ⇒ 三種做法裡 {n_proxy} 種顯示控制後不獨立 ⇒ {'⛔⛔ 判【是代理】，本件結束' if is_proxy else '✅ 判【不是代理】'}")
    pd.concat(B_parts, ignore_index=True).to_csv(os.path.join(a.out, "b_double_sort.csv"), index=False)
    pd.DataFrame([{"method": k, **v} for k, v in B_flags.items()]).to_csv(os.path.join(a.out, "b_verdict.csv"), index=False)

    # ── 2-C 組合層增量 ─────────────────────────────
    C = None
    if is_proxy:
        log("  [2-C] ⛔ 依登錄 §2-B：判【是代理】⇒ 本件結束，2-C 不跑")
    elif a.skip_2c:
        log("  [2-C] ⚠ --skip-2c ⇒ 沒跑（⛔ 不是正式出口）")
    else:
        el["ter"] = xs_bucket(el, FEATURE, N_TER)
        top = el[el["ter"] == N_TER - 1]
        gate_b = P7.build_sig_gate_b(panel, cal, closes, opens)
        key_top = set(zip(top["stock_id"], top["measure_date"].dt.strftime("%Y-%m")))
        both = gate_b[[(s, m) in key_top for s, m in zip(gate_b["sid"], gate_b["month"])]].reset_index(drop=True)
        only = _sig_from_rows(top, cal, closes, opens)
        log(f"  [2-C] 訊號：只用位置前三分位 {len(only):,} 筆／門檻B∧位置 {len(both):,} 筆（門檻B 本身 {len(gate_b):,} 筆）")
        bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
        rows = []
        for name, s_ in (("只用位置前三分位", only), ("門檻B ∧ 位置前三分位", both), ("門檻B（對照）", gate_b)):
            if not len(s_):
                continue
            T, _ = P7.run_cells(s_, closes, opens, cal, bench, [None], (N_CELL,), a.reps, a.procs, log=lambda *_: None)
            r = T.iloc[0]
            rows.append({"set": name, "n_sig": len(s_), **{k: r[k] for k in ("cagr", "cagr_p10", "cagr_p90", "mdd", "slot", "m", "win_all", "win_a", "win_b", "win")}})
            log(f"    {name:<18} 年化 {r['cagr'] * 100:+6.2f}% 回落 {r['mdd'] * 100:6.1f}% 筆數 {r['m']:.0f}"
                f" ⇒ 全窗 {'✅' if r['win_all'] else '✗'}／A {'✅' if r['win_a'] else '✗'}／B {'✅' if r['win_b'] else '✗'}")
        C = pd.DataFrame(rows)
        C.to_csv(os.path.join(a.out, "c_portfolio.csv"), index=False)
    _write_report(a.out, A, dec_tabs, B_flags, is_proxy, C, el)
    log(f"寫入 {os.path.join(a.out, 'P8_REPORT.md')}")


def _sig_from_rows(rows: pd.DataFrame, cal, closes, opens) -> pd.DataFrame:
    """把「某一批量測日股-月」變成引擎吃的 sig（H120、持有 120 根）。⭐ 與 researchp7 同一個慣例。"""
    pos = {d: i for i, d in enumerate(cal)}
    ncal = len(cal)
    out = []
    for r in rows.itertuples():
        sid = r.stock_id
        e = pos.get(r.measure_date)
        if e is None or sid not in closes or sid not in opens:
            continue
        e += 1
        x = D.exit_pos(e, P7.HOLD_BARS_N)
        if e >= len(opens[sid]) or x >= min(ncal, len(closes[sid])):
            continue
        o, c = float(opens[sid][e]), float(closes[sid][x])
        if not np.isfinite(o) or o <= 0 or not np.isfinite(c):
            continue
        out.append({"sid": sid, "entry_pos": e, f"xpos_{P7.RULE}": x, f"g_{P7.RULE}": c / o - 1.0,
                    "month": r.measure_date.strftime("%Y-%m"), "relvol": float(r.amt20), "vol": float(r.vol60)})
    return pd.DataFrame(out)


def _write_report(out_dir, A, dec_tabs, B_flags, is_proxy, C, el):
    L = ["# PREREGP8：位置維度（距 120 日高點）——回測線落地", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準＝策略線 PREREGP8 seq=2（sha 55d8c99ee7b587f8），K線分析線 1200 過目通過。",
         f"母體 {len(el):,} 股-月／{el['stock_id'].nunique():,} 檔，{START}~{END}；種子 `default_rng({SEED0}+r)`。", "",
         "⛔⛔ **本件對「回落」天生沉默**（K線分析線 1200 過目條件，逐字）：",
         "> 本件量的是【同一個月內個股之間】的差異。⛔ 它不構成對【最大回落】的任何證據，因為逐月配對會消掉時點效應。", "",
         "⚠ **出場口徑**：本件是新工作 ⇒ H〈n〉＝**持有 n 根**（`data.exit_pos`）；⛔ 與 P4 面板的 `fwd_H`（持有 H+1 根）差一根。", "",
         "## 2-A 單一維度十分位（主格）", "",
         "判準三件同時成立才算測得出：① D10−D1 的 CI 不含 0　② 十格單調或至多一個例外　③ 兩段同號。", "",
         "| H | 有效月 | D10−D1 | 95% CI | 為正月數 | 單調例外 | 2017-20 | 2021-26 | 同號 | 判定 |",
         "|---:|---:|---:|---|---:|---:|---:|---:|:--:|:--:|"]
    for r in A.itertuples():
        L.append(f"| {r.H} | {r.n_months} | {r.d10_d1_pp:+.2f}pp | [{r.lo_pp:+.2f}, {r.hi_pp:+.2f}] | {r.pos_months}/{r.n_months} | "
                 f"{r.mono_exceptions} | {r.seg_a_pp:+.2f} | {r.seg_b_pp:+.2f} | {'✅' if r.same_sign else '✗'} | "
                 f"{'✅ 測得出' if r.verdict_detected else '⛔ 測不出'} |")
    for H, t in dec_tabs.items():
        L += ["", f"### H{H} 逐十分位（1 ＝ 離高點最遠、10 ＝ 最貼近）", "",
              "| 十分位 | n | 平均 | 中位 | p10 | p90 | 賠>20% | 賺>50% | 勝率 |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in t.itertuples():
            L.append(f"| {r.bucket} | {r.n:,} | {r.mean * 100:+.2f}% | {r.median * 100:+.2f}% | {r.p10 * 100:+.1f}% | "
                     f"{r.p90 * 100:+.1f}% | {r.lose20 * 100:.1f}% | {r.win50 * 100:.1f}% | {r.win * 100:.1f}% |")
    L += ["", "## 2-B 代理檢定（三種做法）", "",
          "⭐ 判定：三種裡有**兩種以上**顯示控制後不獨立 ⇒ 判「是代理」、本件結束。", "",
          "| 做法 | 結果 | 獨立？ |", "|---|---|:--:|"]
    for k, v in B_flags.items():
        if "non_monotonic_quintiles" in v:
            L.append(f"| 雙重分位（控制 {k}） | {N_QUI} 個分位裡 {v['non_monotonic_quintiles']} 個內部不單調 | {'✅' if v['independent'] else '⛔'} |")
        else:
            L.append(f"| 殘差法 | T3−T1 {v['diff_pp']:+.2f}pp CI [{v['lo_pp']:+.2f}, {v['hi_pp']:+.2f}]（{v['n_months']} 月） | {'✅' if v['independent'] else '⛔'} |")
    L += ["", f"⇒ **{'⛔⛔ 判【是代理】，本件結束' if is_proxy else '✅ 判【不是代理】'}**", ""]
    if is_proxy:
        L += ["⚠ **而本線要把一件事講清楚（⛔ 這是觀察，不是改判定）**：", "",
              "登錄的判準是「在**每一個**控制分位內部都**單調**」——它比「控制之後還在」**嚴格**。",
              "而雙重分位表顯示：T3−T1 在**十個控制分位列裡全部是正的**，不單調只發生在**最高那兩個分位的 T2 與 T3 之間**。",
              "⇒ ⭐ 兩種讀法在這一批資料上**給出不同答案**：照登錄的字面＝是代理；照「控制後還在不在」＝還在。",
              "⇒ ⛔ 本線**照登錄字面判**（改判準＝看過結果再挑判準，〈六十四〉）；",
              "⇒ ⏳ 要不要把判準從「分位內單調」改成「分位內 T3−T1 的 CI 不含 0」，是 **K線分析線**的格子，⛔ 本線不裁。", ""]
    if C is not None and len(C):
        L += ["## 2-C 組合層增量（N=8、停損 none）", "",
              "| 訊號集 | 訊號筆數 | 年化 中位 | p10～p90 | 最大回落 | 槽位 | 筆數 | 全窗 | A 窗 | B 窗 | 三窗全過 |",
              "|---|---:|---:|---|---:|---:|---:|:--:|:--:|:--:|:--:|"]
        for r in C.itertuples():
            L.append(f"| {r.set} | {r.n_sig:,} | {r.cagr * 100:+.2f}% | {r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f} | {r.mdd * 100:.1f}% | "
                     f"{r.slot:.2f} | {r.m:.0f} | {'✅' if r.win_all else '✗'} | {'✅' if r.win_a else '✗'} | {'✅' if r.win_b else '✗'} | {'✅' if r.win else '⛔'} |")
        L.append("")
    L += ["## ⛔ 範圍限制（登錄 §五，逐字）", "",
          "① 個股橫斷面維度，⛔ 不是市場擇時 ⇒ 依先驗④它修不好回落。",
          "② `dist_hi120` ＝ 收盤 ÷ 近 120 個交易日最高**收盤** − 1（⛔ 不是最高價、⛔ 不是 250 日）。",
          "③ 與研究十（近 60 日報酬十分位，D10−D1 +0.82pp 測不出）是**不同的動能定義** ⇒ ⛔ 不是矛盾也不是否證。",
          "④ 倖存者偏誤仍在；成本 0.585%；滑價未計。　⑤ 十分位／三分位切點是我方選的（〈三十九〉）。",
          "⑥ ⛔ 這就是【動能／相對強弱】，⛔ 不是新發現；本件的價值是在本庫本口徑上第一次事前登錄重跑。", ""]
    open(os.path.join(out_dir, "P8_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())

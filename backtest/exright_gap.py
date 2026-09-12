"""上櫃除權息未進 data/adj/ 的曝險量化（情報分析 2026-09-09 20:55 急件、CODE 21:10）。

候選：2018 起、當日有成交、`change` 空白、前後 ±5 日曆日 data/adj/ 無事件的「股票×日」（CODE 的代理指標，上界）。
輸出：
  results_audit/exright_gap_candidates.csv   逐筆（含當日對前收的開盤跳空、收盤漲跌，供縮上界）
  results_audit/exright_gap_exposure.md      研究三面板（500 張版、5,000 萬版）與研究二訊號的曝險、剔除後 G1 超額
只讀，不改資料層。
"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import data as D, evaluate as E, research34 as R34

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "results_audit")
START = "2018-01-01"


def candidates() -> pd.DataFrame:
    st = pd.read_csv(os.path.join(ROOT, "data/meta/stocks.csv"), dtype=str)
    ids = st[(st["kind"] == "stock") & (st["market"].isin(["twse", "tpex"]))]["stock_id"].tolist()
    rows = []
    for sid in ids:
        p = os.path.join(ROOT, "data/stocks", f"{sid}.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p, dtype={"stock_id": str, "change": float}, usecols=["date", "market", "open", "close", "volume", "change"])
        df = df[df["volume"].fillna(0) > 0].reset_index(drop=True)
        if df.empty:
            continue
        df["prev_close"] = df["close"].shift(1)
        m = (df["date"] >= START) & df["change"].isna() & df["prev_close"].notna()
        if not m.any():
            continue
        adj = D.load_adj(sid)
        ev = pd.to_datetime(adj["date"]).sort_values().to_numpy() if adj is not None and len(adj) else np.array([], dtype="datetime64[ns]")
        for _, r in df[m].iterrows():
            d = pd.Timestamp(r["date"])
            if len(ev):
                i = np.searchsorted(ev, np.datetime64(d))
                near = False
                for j in (i - 1, i):
                    if 0 <= j < len(ev) and abs((pd.Timestamp(ev[j]) - d).days) <= 5:
                        near = True; break
                if near:
                    continue
            rows.append(dict(stock_id=sid, date=r["date"], market=r["market"], prev_close=r["prev_close"], open=r["open"], close=r["close"],
                             gap_open=r["open"] / r["prev_close"] - 1 if r["prev_close"] else np.nan,
                             ret_close=r["close"] / r["prev_close"] - 1 if r["prev_close"] else np.nan))
    return pd.DataFrame(rows, columns=["stock_id", "date", "market", "prev_close", "open", "close", "gap_open", "ret_close"])


def exposure(panel: pd.DataFrame, cand: pd.DataFrame, cal: pd.DatetimeIndex, hold: int) -> np.ndarray:
    """每列：持有期 (entry_pos, entry_pos+hold] 內是否含候選日。"""
    pos = {}
    cpos = cal.searchsorted(pd.to_datetime(cand["date"]))
    for sid, p in zip(cand["stock_id"], cpos):
        pos.setdefault(sid, []).append(int(p))
    pos = {k: np.array(sorted(v)) for k, v in pos.items()}
    out = np.zeros(len(panel), dtype=bool)
    for i, (sid, ep) in enumerate(zip(panel["stock_id"], panel["entry_pos"])):
        a = pos.get(sid)
        if a is None:
            continue
        lo = np.searchsorted(a, ep, side="right"); hi = np.searchsorted(a, ep + hold, side="right")
        out[i] = hi > lo
    return out


def g1_block(panel: pd.DataFrame, flag: dict, hold: int) -> list[str]:
    col = f"ret{hold}"; f = flag[hold]
    g1 = panel["rev_hi24"] == True
    L = []
    for name, keep in (("含曝險列（現況）", np.ones(len(panel), bool)), ("剔除曝險列", ~f)):
        pan = panel[keep]; base = pan[col].mean() - E.COST
        s = R34.stats(pan[g1[keep]], col, hold, base)
        L.append(f"| {hold} | {name} | {len(pan):,} | {s['n']:,} | {s['n_nonoverlap']:,} | {base * 100:+.2f}% | {s['mean'] * 100:+.2f}% | **{s['excess'] * 100:+.2f} pp** | {s['excess_ci_lo'] * 100:+.2f} ~ {s['excess_ci_hi'] * 100:+.2f} |")
    return L


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    cal = D.load_calendar()
    cand = candidates()
    cand.to_csv(os.path.join(OUT, "exright_gap_candidates.csv"), index=False)
    L = ["# 上櫃除權息未進 `data/adj/` 的曝險量化", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。程式 `backtest/exright_gap.py`，只讀。候選定義（CODE 21:10 的代理指標，上界）：2018 起、當日有成交、`change` 空白、±5 日曆日 `data/adj/` 無事件；母體 `kind == stock`、`market ∈ {{twse, tpex}}`（以日檔逐列 `market` 分市場）。", ""]
    L.append("## 一、候選筆數（重算）"); L.append("")
    by = cand.groupby([cand["date"].str[:4], "market"]).size().unstack(fill_value=0)
    L.append("| 年 | " + " | ".join(by.columns) + " |"); L.append("|---|" + "---:|" * len(by.columns))
    for y, r in by.iterrows():
        L.append(f"| {y} | " + " | ".join(f"{int(v):,}" for v in r) + " |")
    L.append(f"| 合計 | " + " | ".join(f"{int(v):,}" for v in by.sum()) + " |"); L.append("")
    tp = cand[cand["market"] == "tpex"]
    L.append("### 縮上界：候選日當天對前收的開盤跳空（除權息日開盤應貼近參考價，跳空為負且幅度 ≈ 配息率）"); L.append("")
    q = tp["gap_open"].quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    L.append(f"- 上櫃候選 {len(tp):,} 筆：開盤跳空 p5 {q[0.05] * 100:+.2f}%、p25 {q[0.25] * 100:+.2f}%、中位 {q[0.5] * 100:+.2f}%、p75 {q[0.75] * 100:+.2f}%、p95 {q[0.95] * 100:+.2f}%")
    for th in (-0.005, -0.01, -0.02):
        L.append(f"- 開盤跳空 ≤ {th * 100:.1f}%：{int((tp['gap_open'] <= th).sum()):,} 筆（{(tp['gap_open'] <= th).mean() * 100:.0f}%）")
    L.append(f"- 開盤跳空 > 0（不像除權息）：{int((tp['gap_open'] > 0).sum()):,} 筆")
    L.append(f"- 合理下界（跳空 ≤ −0.5% 且收盤跌）：{int(((tp['gap_open'] <= -0.005) & (tp['ret_close'] < 0)).sum()):,} 筆")
    L.append("")
    # 面板曝險
    for tag, folder in (("研究三 500 張版", "results3"), ("研究三 5,000 萬版", "results3_amt")):
        p = os.path.join(HERE, folder, "panel.csv.gz")
        if not os.path.exists(p):
            continue
        panel = pd.read_csv(p, dtype={"stock_id": str})
        flag = {h: exposure(panel, tp, cal, h) for h in (20, 60)}
        g1 = (panel["rev_hi24"] == True).to_numpy()
        L.append(f"## 二、{tag}：面板 {len(panel):,} 列（上櫃 {int((panel['market'] == 'tpex').sum()):,} 列）"); L.append("")
        L.append("| 持有 | 曝險列（持有期跨過候選日） | 占面板 | 占上櫃列 | G1 內曝險列 | 占 G1 | 非 G1 內曝險 | 占非 G1 |")
        L.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for h in (20, 60):
            f = flag[h]; tpx = (panel["market"] == "tpex").to_numpy()
            L.append(f"| {h} | {int(f.sum()):,} | {f.mean() * 100:.2f}% | {f[tpx].mean() * 100:.2f}% | {int((f & g1).sum()):,} | {f[g1].mean() * 100:.2f}% | {int((f & ~g1).sum()):,} | {f[~g1].mean() * 100:.2f}% |")
        L.append("")
        L.append("| 持有 | 版本 | 面板列 | G1 n | 非重疊 n | 母體基準（扣成本） | G1 淨報酬 | G1 超額 | 超額 CI |")
        L.append("|---:|---|---:|---:|---:|---:|---:|---:|---|")
        for h in (20, 60):
            L += g1_block(panel, flag, h)
        L.append("")
        # 偏誤方向的粗估：把曝險列的報酬按候選日開盤跳空回推（假設跳空全是除權息、市場當天不動）
        for h in (20, 60):
            col = f"ret{h}"; f = flag[h]
            if f.sum() == 0:
                continue
            adj_ret = panel[col].to_numpy(float).copy()
            cpos = cal.searchsorted(pd.to_datetime(tp["date"]))
            gm = {}
            for sid, pp, g in zip(tp["stock_id"], cpos, tp["gap_open"]):
                gm.setdefault(sid, []).append((int(pp), g))
            for i in np.where(f)[0]:
                sid = panel["stock_id"].iat[i]; ep = int(panel["entry_pos"].iat[i]); k = 1.0
                for pp, g in gm.get(sid, []):
                    if ep < pp <= ep + h and np.isfinite(g) and g < 0:
                        k /= (1 + g)
                adj_ret[i] = (1 + adj_ret[i]) * k - 1
            base0 = np.nanmean(panel[col]) - E.COST; base1 = np.nanmean(adj_ret) - E.COST
            e0 = np.nanmean(panel[col][g1]) - E.COST - base0; e1 = np.nanmean(adj_ret[g1]) - E.COST - base1
            L.append(f"- 粗估回推（把曝險列的報酬乘回 1/(1+開盤跳空)，只用負跳空；上界情形）持有 {h} 日：G1 超額 {e0 * 100:+.2f} → {e1 * 100:+.2f} pp（差 {(e1 - e0) * 100:+.2f} pp）")
        L.append("")
    # 研究二訊號
    for tag, folder in (("研究二 500 張版", "results"), ("研究二 5,000 萬版", "results_amt")):
        p = os.path.join(HERE, folder, "signals.csv.gz")
        if not os.path.exists(p):
            continue
        sig = pd.read_csv(p, dtype={"stock_id": str})
        if "entry_pos" not in sig.columns:
            L.append(f"## {tag}：signals 欄位無 entry_pos（{sig.columns.tolist()[:12]}），略"); continue
        L.append(f"## 三、{tag}：訊號 {len(sig):,} 筆"); L.append("")
        f20 = exposure(sig, tp, cal, 20)
        L.append("| 型態 | 訊號 | 曝險（20 日持有期跨候選日） | 占比 | 曝險列淨報酬均值 | 其餘均值 |"); L.append("|---|---:|---:|---:|---:|---:|")
        pcol = "pattern" if "pattern" in sig.columns else sig.columns[1]
        rcol = "ret_hold_net" if "ret_hold_net" in sig.columns else None
        for pat, g in sig.groupby(pcol):
            f = f20[g.index.to_numpy()]
            a = g[rcol][f].mean() * 100 if rcol and f.any() else np.nan; b = g[rcol][~f].mean() * 100 if rcol else np.nan
            L.append(f"| {pat} | {len(g):,} | {int(f.sum()):,} | {f.mean() * 100:.2f}% | {a:+.2f}% | {b:+.2f}% |")
        L.append("")
    L.append(f"（{time.time() - t0:.0f} 秒）")
    with open(os.path.join(OUT, "exright_gap_exposure.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

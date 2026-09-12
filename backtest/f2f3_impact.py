"""F2（疑似幽靈除權）與 F3（2022-02 上櫃營收缺半）對研究二／三的影響量化。只讀。

F2：`results_audit/adj_mismatch.csv` 裡上市普通股、事件日收盤 ÷（前收 × factor）> 1.105 的事件——因子套了但價格沒跌，
    還原序列在事件日出現 1/factor 的假跳升。量：持有期跨過事件日的訊號／面板列數、G1 內外、剔除後 G1 超額。
F3：`revenue_hist/2022-02_tpex.csv` 缺的上櫃股——research34 的 rev_hi24 要求 24 個月齊全，缺一個月 ⇒ 之後 24 個月 rev_hi24 一律 False。
    量：缺哪些檔、面板裡受影響的列數（2022-02～2024-01 期的上櫃列）、其中本來可能是 G1 的上界。
"""
import os, sys, glob
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import data as D, evaluate as E, research34 as R34
from backtest.exright_gap import exposure, HERE, ROOT, OUT

cal = D.load_calendar()
st = pd.read_csv(os.path.join(ROOT, "data/meta/stocks.csv"), dtype=str).set_index("stock_id")
L = ["# F2／F3 影響量化", f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。程式 `backtest/f2f3_impact.py`。", ""]

# ── F2 ──
mm = pd.read_csv(os.path.join(OUT, "adj_mismatch.csv"), dtype={"stock_id": str})
mm["kind_sec"] = mm["stock_id"].map(st["kind"]); mm["market"] = mm["stock_id"].map(st["market"])
f2 = mm[(mm["kind_sec"] == "stock") & (mm["close_over_expected"] > 1.105) & (~mm["kind"].astype(str).str.contains("減資|reduce"))].copy()
f2["fake_jump"] = 1 / f2["factor"] - 1
L.append(f"## F2：疑似幽靈除權 {len(f2)} 筆（上市普通股、事件日收盤 ÷ 前收×因子 > 1.105、非減資）"); L.append("")
L.append("| 代號 | 事件日 | 因子 | 還原序列假跳升 |"); L.append("|---|---|---:|---:|")
for _, r in f2.sort_values("date").iterrows():
    L.append(f"| {r.stock_id} | {r.date} | {r.factor:.3f} | +{r.fake_jump * 100:.1f}% |")
L.append("")
cand = f2.rename(columns={})[["stock_id", "date"]].copy(); cand["market"] = "twse"
for tag, folder in (("研究三 500 張版", "results3"), ("研究三 5,000 萬版", "results3_amt")):
    panel = pd.read_csv(os.path.join(HERE, folder, "panel.csv.gz"), dtype={"stock_id": str})
    g1 = (panel["rev_hi24"] == True).to_numpy()
    L.append(f"### {tag}（{len(panel):,} 列）"); L.append("")
    L.append("| 持有 | 跨過事件日的列 | G1 內 | 非 G1 | G1 超額 現況 | 剔除後 |"); L.append("|---:|---:|---:|---:|---:|---:|")
    for h in (20, 60):
        f = exposure(panel, cand, cal, h); col = f"ret{h}"
        base0 = panel[col].mean() - E.COST; s0 = R34.stats(panel[g1], col, h, base0)
        pan = panel[~f]; base1 = pan[col].mean() - E.COST; s1 = R34.stats(pan[g1[~f]], col, h, base1)
        L.append(f"| {h} | {int(f.sum())} | {int((f & g1).sum())} | {int((f & ~g1).sum())} | {s0['excess'] * 100:+.2f} pp | {s1['excess'] * 100:+.2f} pp |")
    L.append("")
for tag, folder in (("研究二 500 張版", "results"), ("研究二 5,000 萬版", "results_amt")):
    sig = pd.read_csv(os.path.join(HERE, folder, "signals.csv.gz"), dtype={"stock_id": str})
    f = exposure(sig, cand, cal, 20)
    L.append(f"### {tag}（{len(sig):,} 筆）：20 日持有期跨過事件日 **{int(f.sum())}** 筆")
    if f.any():
        L.append("、".join(f"{k} {v}" for k, v in sig[f].groupby("pattern").size().items()))
    # 事件日當天或前一日發出的訊號（假跳升本身觸發的突破）
    pos = cal.searchsorted(pd.to_datetime(cand["date"]))
    key = set(zip(cand["stock_id"], pos))
    trig = sum((s, p) in key or (s, p - 1) in key for s, p in zip(sig["stock_id"], sig["entry_pos"]))
    L.append(f"- 進場日落在事件日或次日（可能是假跳升觸發的訊號）：{trig} 筆"); L.append("")

# ── F3 ──
fs = {os.path.basename(p)[:7]: p for p in glob.glob(os.path.join(ROOT, "data/mops/revenue_hist/*_tpex.csv"))}
def ids(ym): return set(pd.read_csv(fs[ym], dtype=str)["stock_id"])
feb, jan, mar = ids("2022-02"), ids("2022-01"), ids("2022-03")
missing = (jan & mar) - feb
L.append(f"## F3：2022-02 上櫃營收 {len(feb)} 檔（前後月 {len(jan)}／{len(mar)}）；1 月與 3 月都有、2 月沒有的 **{len(missing)} 檔**"); L.append("")
for tag, folder in (("研究三 500 張版", "results3"), ("研究三 5,000 萬版", "results3_amt")):
    panel = pd.read_csv(os.path.join(HERE, folder, "panel.csv.gz"), dtype={"stock_id": str})
    win = (panel["period"] >= "2022-02") & (panel["period"] <= "2024-01")
    aff = win & panel["stock_id"].isin(missing)
    n_g1_win = int(((panel["rev_hi24"] == True) & win).sum())
    # 受影響列裡 rev_hi24 一律 False；上界：用同一批股票在窗外的 G1 比例估「本來會是 G1」的列數
    outside = (~win) & panel["stock_id"].isin(missing)
    rate = float((panel.loc[outside, "rev_hi24"] == True).mean()) if outside.any() else float("nan")
    L.append(f"### {tag}")
    L.append(f"- 2022-02～2024-01 期的面板列 {int(win.sum()):,}，其中缺 2022-02 營收的上櫃股 **{int(aff.sum()):,} 列**（這些列 rev_hi24 被迫為 False；實際 False 率 {float((panel.loc[aff, 'rev_hi24'] == True).mean()) * 100:.1f}% 為 True——應為 0）。")
    L.append(f"- 同一批股票在窗外的 G1 比例 {rate * 100:.1f}% ⇒ 估計**漏掉的 G1 訊號約 {int(aff.sum() * rate):,} 筆**，占該窗 G1 {n_g1_win:,} 筆的 {aff.sum() * rate / max(n_g1_win, 1) * 100:.1f}%、占全期 G1 {int((panel['rev_hi24'] == True).sum()):,} 筆的 {aff.sum() * rate / max(int((panel['rev_hi24'] == True).sum()), 1) * 100:.1f}%。")
    L.append("- 方向：只會**少訊號**（漏掉真的創高），不會多訊號；漏掉的是隨機的上櫃股，不偏向哪一邊。")
    L.append("")
with open(os.path.join(OUT, "f2f3_impact.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("\n".join(L))

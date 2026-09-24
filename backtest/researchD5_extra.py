# -*- coding: utf-8 -*-
"""D5 必報補齊（⛔ 不改判定）：①停損距離（初始／觸發時，200 顆彙總）②成本敏感度、平均持有天數、年換手與成本、逐月現金
③MA60 重疊率（觸發根 d 起 [d−5, d] 任一根收盤 < MA60）④3×ATR 代用與無停損筆數（見 summary：全為碎形）⑤被停後 20 日同檔報酬
⑦逐年＋去掉最好一年＋進場證券別（種子 102000 路徑）"""
import os, sys, json, bisect
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchD5 as M
D = M.D; R = M.R; P12 = M.P12
OUT = M.OUT


def _cost(args):
    seed, c = args
    out = M.sim(M._S["sig"], seed, stop_line=M._S["lines"], cost=c); return {"seed": seed, "cost": c, **dict(zip(("cagr", "mdd"), M.wst(out)))}


def main():
    cal = D.load_calendar(); ncal = len(cal)
    panel = M.P4F.read_panel(os.path.join(M.AFC, "panel.csv.gz"))
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens, ohlc, idx_map, ma60 = {}, {}, {}, {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float)
        v = np.flatnonzero(np.isfinite(c)); idx_map[s] = v.tolist()
        ohlc[s] = tuple(st.df[k].to_numpy(float)[v] for k in ("open", "high", "low", "close"))
        ma60[s] = pd.Series(c[v]).rolling(60, min_periods=60).mean().to_numpy()
    w0, w1 = P12.win_bounds(cal, "全窗"); marks = P12.month_marks(cal, w0, w1)
    sig = M.P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B").sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    trad = M.T.build(set(sig["sid"]), cal); dl = M.T.delist_status(trad, cal, official=M.T.load_official())
    lines, _ = M.build_lines(sig, ohlc, idx_map)
    xpos_of = {(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])}
    S = {"closes": closes, "opens": opens, "ncal": ncal, "trad": trad, "dl": dl, "w0": w0, "w1": w1, "marks": marks, "sig": sig, "lines": lines, "xpos_of": xpos_of}
    M._init(S)
    R_ = {}
    with Pool(4, initializer=M._init, initargs=(S,)) as pool:
        CS = pd.DataFrame(pool.map(_cost, [(M.SEED0 + r, c) for c in M.COSTS for r in range(M.NS)], chunksize=10))
    R_["②成本敏感度（200顆中位）"] = {f"{c:.3%}": [float(g["cagr"].median()), float(g["mdd"].median())] for c, g in CS.groupby("cost")}
    ev = pd.read_csv(os.path.join(OUT, "stop_events.csv"), dtype={"sid": str})
    d0, d1, ov, post, hold = [], [], [], [], []
    for r in ev.itertuples():
        bars = idx_map[r.sid]; o, h, l, c = ohlc[r.sid]
        e = bisect.bisect_left(bars, r.entry); x = bisect.bisect_left(bars, r.t) - 1
        s_ent, arr = lines[(r.sid, int(r.entry))]
        p0 = opens[r.sid][r.entry]
        d0.append(1 - arr[0] / p0); d1.append(arr[min(len(arr) - 1, bars[x] - s_ent)] / p0 - 1)
        m = ma60[r.sid][max(0, x - 5):x + 1]; cc = c[max(0, x - 5):x + 1]
        ov.append(bool(np.any(np.isfinite(m) & (cc < m))))
        end = min(ncal - 1, r.t + 19)
        if np.isfinite(opens[r.sid][r.t]) and opens[r.sid][r.t] > 0:
            post.append(closes[r.sid][end] / opens[r.sid][r.t] - 1)
        hold.append(bars[x] - r.entry + 1 if x >= 0 else np.nan)
    q = lambda a: {"中位": float(np.nanmedian(a)), "p10": float(np.nanpercentile(a, 10)), "p90": float(np.nanpercentile(a, 90))}
    R_["①停損距離（200顆全部停損事件）"] = {"初始（1−停損／進場開盤）": q(d0), "觸發時（停損／進場開盤−1）": q(d1), "初始停損高於進場開盤的比例": float(np.mean(np.array(d0) < 0)), "事件數": len(ev)}
    R_["③MA60重疊率"] = float(np.mean(ov))
    R_["⑤被停後20日同檔報酬"] = {**q(post), "平均": float(np.mean(post)), "n": len(post)}
    R_["②進場到觸發根的日曆天數"] = q(hold)
    # ⑦ 種子 102000 路徑
    au = []; out = M.sim(sig, M.SEED0, stop_line=lines, audit=au)
    eq = out["equity"]; ys = pd.Series(eq[w0:w1 + 1], index=cal[w0:w1 + 1])
    ye = ys.groupby(ys.index.year).last(); prev = ye.shift(1); prev.iloc[0] = ys.iloc[0]; yr = ye / prev - 1
    best = int(yr.idxmax()); rest = [v for k, v in yr.items() if k != best]
    mk = uni.to_dict(); buys = [a for a in au if a["side"] == "buy"]
    sells = [a for a in au if a["side"] == "sell" and w0 <= a["t"] <= w1]
    yrs = (w1 - w0) / 245
    e = np.where(eq > 0, out["hold_val"] / eq, 0.0)
    cash_m = pd.Series(1 - e[w0:w1 + 1], index=cal[w0:w1 + 1]).groupby(cal[w0:w1 + 1].to_period("M")).mean()
    R_["⑦種子102000"] = {"逐年": {int(k): float(v) for k, v in yr.items()}, "去掉最好一年": {"最好一年": best, "其餘幾何平均": float(np.prod([1 + v for v in rest]) ** (1 / len(rest)) - 1)},
                         "進場筆數證券別": pd.Series([mk.get(a["sid"], "?") for a in buys]).value_counts().to_dict(),
                         "年換手（賣出額／權益）": sum(a["amt"] / a["equity_prev"] for a in sells) / yrs, "年成本（權益 %）": sum(a["cost"] / a["equity_prev"] for a in sells) / yrs,
                         "逐月現金比例（中位／最小／最大）": [float(cash_m.median()), float(cash_m.min()), float(cash_m.max())]}
    json.dump(R_, open(os.path.join(OUT, "extra.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()

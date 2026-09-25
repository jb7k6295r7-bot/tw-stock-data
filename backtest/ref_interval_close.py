# -*- coding: utf-8 -*-
"""歷史參考區間 ⇒ 台股狀態標籤規則 seq3（1af1484ba2f2b9d4）§二：出場改【第 n 根收盤】（n＝20／60／120；H〈n〉＝進場日＋(n−1)）。

只換「出場價」一處，其餘（母體、進場、剔除、bootstrap、種子）與 ref_interval.py（5035359a27、seq2 開盤版）完全相同。
出場規則照 W1 引擎（research11.simulate_mtm tradable 路徑，註解 ②④）逐字搬：
  ① 排程出場根 x ＝ D.exit_pos(entry, n)：該日有成交且【收盤≠跌停價】（⛔ dn_c）⇒ 以 x 的還原收盤出（status＝ok）
  ② x 停牌、或 x 收盤＝跌停價 ⇒ 之後第一個「有成交且開盤≠跌停價」的交易日【開盤】出（status＝exit_delayed）
  ③ 最後成交之後都無成交：下市（delisted_*）⇒ 以最後成交收盤了結；ambig ⇒ 量不到、剔除計數（同開盤版）
期間最高點：收盤出 ⇒ max(還原 high[entry … x])；延後開盤出 ⇒ max(還原 high[entry … t−1], 還原 open[t])（同開盤版口徑）
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
import ref_interval as RI

D = RI.D
OUT = os.path.join("backtest", "resultsSR")


def measure_close(sig, cal, closes, opens, highs, trad, dl, k_of):
    ncal = len(cal); rows = []
    for i, (s, e) in enumerate(zip(sig["sid"], sig["entry_pos"])):
        e = int(e); tb = trad[s]; o = opens[s]; c = closes[s]
        base = {"i": i, "sid": s, "entry_pos": e, "entry_date": cal[e], "emonth": cal[e].strftime("%Y-%m")}
        if not tb["trd"][e]:
            for h in RI.HS:
                rows.append({**base, "h": h, "status": "halt_in"})
            continue
        if tb["up_o"][e] or not (np.isfinite(o[e]) and o[e] > 0):
            for h in RI.HS:
                rows.append({**base, "h": h, "status": "limit_up" if tb["up_o"][e] else "no_open"})
            continue
        ep = float(o[e])
        info = dl.get(s, {"last": ncal - 1, "status": "live"})
        for h in RI.HS:
            x = k_of(e, h)
            r = {**base, "h": h, "x_sched": x, "ep": ep}
            if x >= ncal:
                r["status"] = "beyond_cal"; rows.append(r); continue
            done = False
            if tb["trd"][x] and not tb["dn_c"][x] and np.isfinite(c[x]) and c[x] > 0:
                r.update(status="ok", t_exit=x, px=float(c[x]), how="close"); done = True
            else:
                t = x + 1
                while t < ncal:
                    if tb["trd"][t] and not tb["dn_o"][t] and np.isfinite(o[t]) and o[t] > 0:
                        r.update(status="exit_delayed", t_exit=t, px=float(o[t]), how="open"); done = True; break
                    if (not tb["trd"][t]) and t > info["last"]:
                        if info["status"].startswith("delisted"):
                            r.update(status="delist_settled", t_exit=t, px=float(c[t]), how="settle"); done = True
                        else:
                            r.update(status="delist_ambig")
                        break
                    t += 1
            if not done:
                r.setdefault("status", "unresolved"); rows.append(r); continue
            te = r["t_exit"]
            if r["how"] == "close":
                hh = highs[s][e:te + 1]
                mx = np.nanmax(hh) if np.isfinite(hh).any() else r["px"]
            else:
                hh = highs[s][e:te]; hh = hh[np.isfinite(hh)]
                mx = max(hh.max() if len(hh) else -np.inf, r["px"] if r["status"] != "delist_settled" else -np.inf)
                if not np.isfinite(mx):
                    mx = r["px"]
            r["ret"] = r["px"] / ep - 1.0 - RI.COST_RT
            r["maxup"] = mx / ep - 1.0
            rows.append(r)
    return pd.DataFrame(rows)


def main():
    cal, ncal, sig, closes, opens, highs, stk = RI.load_all()
    w0, w1 = RI.P12.win_bounds(cal, "全窗")
    sig = sig[(sig["entry_pos"] >= w0) & (sig["entry_pos"] <= w1)].reset_index(drop=True)
    assert len(sig) == RI.ANCHOR_S1_MAIN, len(sig)
    trad = RI.T.build(set(sig["sid"]), cal); dl = RI.T.delist_status(trad, cal, official=RI.T.load_official())
    M = measure_close(sig, cal, closes, opens, highs, trad, dl, lambda e, h: D.exit_pos(e, h))
    te = M["t_exit"] if "t_exit" in M else pd.Series(np.nan, index=M.index)
    print("出場根超出主窗尾的列：", int((te > w1).sum()))
    cnt = M.groupby(["h", "status"]).size().unstack(fill_value=0)
    print(cnt.to_string())
    months = np.array(sorted(M["emonth"].unique()))
    rng = np.random.default_rng(RI.SEED)
    rng_idx = rng.integers(0, len(months), size=(RI.B, len(months)))
    TB = RI.table(M, rng_idx, months, "主表（收盤版 seq3）")
    TB.to_csv(os.path.join(OUT, "ref_interval_close.csv"), index=False, encoding="utf-8")
    M.to_csv(os.path.join(OUT, "ref_interval_close_trades.csv.gz"), index=False)
    cnt.to_csv(os.path.join(OUT, "ref_interval_close_counts.csv"), encoding="utf-8")
    # 查核：build_sig_gate_b 的 g_H120 ＝ closes[xpos]/opens[entry]−1（收盤出場）⇒ status＝ok 的 120 日列應逐筆相同
    g = dict(zip(sig.index, sig["g_H120"].to_numpy(float)))
    k = M[(M["h"] == 120) & (M["status"] == "ok")]
    d = np.abs(k["ret"].to_numpy(float) - (np.array([g[i] for i in k["i"]]) - RI.COST_RT))
    print("查核 g_H120：status＝ok 的 120 日列 {:,} 筆，最大差 {:.2e}".format(len(k), float(np.nanmax(d))))
    fmt = TB.copy()
    for c in fmt.columns:
        if c.startswith("p") or c == "平均":
            fmt[c] = (fmt[c] * 100).map("{:+.2f}".format)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(fmt[["持有", "量", "筆數", "相異檔數", "p10", "p25", "p50", "p50_lo", "p50_hi", "p75", "p90", "平均"]].to_string(index=False))


if __name__ == "__main__":
    main()

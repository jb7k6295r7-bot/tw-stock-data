# -*- coding: utf-8 -*-
"""歷史參考區間（台股策略線 起草全文 seq2 §二，sha f41e5f4420657e84；裁定線 seq152 已過目）——回測線落地。

⭐ 性質：描述，⛔ 不判定、⛔ 不計 N、⛔ 不是目標價或賣出條件；⛔ 只用主窗 2017-03-02～2026-08-24、⛔ 不讀不算 2015 以前的報酬。

資料／訊號：與 researchAFC 同一份（main edc6f8002f 快照；resultsAFC/panel.csv.gz；P7.build_sig_gate_b(signal="B")；
   D.load_stock 還原價；T.build ＋ T.delist_status(official)）。

母體（§二 逐字）：門檻B【訊號集合】：主窗內每個量測日所有符合門檻B 進場條件的股票，T+1 開盤進場；⛔ 不隨機挑、⛔ 不受 8 檔名額；
   同一檔重複入選各算一筆。

⭐ 落地讀法（⛔ 看任何結果之前寫在這裡；交件逐條列出）：
 Q1 母體 ＝ build_sig_gate_b 的每一列、entry_pos 落在主窗 [w0, w1]（P12.win_bounds「全窗」，兩端含）
    ⇒ 與 S1 在主窗的列數相同（旁證 2,881）。⚠ build_sig_gate_b 本身已剔 xpos(＝entry+119) ≥ 日曆長度、進場開盤非有限、
    xpos 收盤非有限的列 ⇒ 20／60／120 三個持有期用【同一組列】（⛔ 不因 20 日較短而多收列），各期再各自剔不能成交的。
 Q2 「第 k 個交易日」＝ D.exit_pos(entry_pos, k)（進場日算第 1 個交易日；repo 唯一的持有期實作）；數在【交易日曆】上
    （同 W1 的 xpos）。報酬 ＝ 還原 open[x_k] ÷ 還原 open[entry] − 1 − 0.585%。
    ⚠ 另一種讀法「entry＋k（進場日算第 0 個）」只作敏感度欄（sens_k0），⛔ 不是主表。
 Q3 W1 引擎（research11.simulate_mtm, tradable＋delist 開）的規則逐條搬到「單筆、開盤出場」：
    進場：entry 日停牌（trd＝False）⇒ 不成交（halt_in）；開盤＝漲停價（up_o）⇒ 不成交（limit_up）；開盤非有限 ⇒ 不成交
          ⇒ 剔除並計數（引擎：該名額持現金、⛔ 不遞補 ⇒ 該訊號沒有報酬）
    出場：x_k 日停牌或開盤＝跌停價（dn_o）⇒ 延到第一個「有成交且開盤非跌停」日的【開盤】（引擎 ②，exit_delayed）
          ⚠ 引擎 ④（排程出場日收盤＝跌停 dn_c）是針對「收盤出場」；本件出場在開盤 ⇒ 對應的是 dn_o，⛔ 不另套 dn_c
          出場日之後再也沒有成交（t > last）：status delisted_official／delisted_gap ⇒ 以最後成交收盤了結（引擎 ⑤ 的「原 gross」）
          ＝ delist_settled；status ambig ⇒ 引擎照停牌處理、⛔ 不猜 ⇒ 本件量不到報酬 ⇒ 剔除並計數（delist_ambig）
          延後到日曆尾仍賣不掉 ⇒ 剔除並計數（unresolved）
 Q4 硬斷點：⛔ W1 引擎沒有硬斷點規則（simulate_mtm 無此參數；面板 eligible 只管量測日）⇒ 主表照引擎【不剔】；
    另用 data.breakpoints（兩條規則、不帶流動性前提，同 researchH2 R3）數「持有區間 (entry, 出場日] 內有斷點」的筆數，
    並報「剔除這些筆」的敏感度分位。
 Q5 期間內最高點 ＝ max(還原 high[entry … 出場日−1], 還原 open[出場日]) ÷ 進場開盤 − 1（出場在開盤 ⇒ 出場日只算開盤；
    停牌日無 K 棒自然略過）；⛔ 不扣成本（它是價位描述，不是報酬）。
 Q6 分位 ＝ numpy.quantile 預設（linear）；月分群 bootstrap：群 ＝ 進場月（entry 日曆月），有放回重抽「月」B＝2,000 次、
    每次抽與原月數相同的月、把抽中月的全部筆接起來重算分位；種子 20260923（numpy default_rng），同一組重抽索引給所有欄；
    CI ＝ 2,000 個重抽分位的 2.5／97.5 百分位（percentile 法）。
 Q7 相異檔數 ＝ 該期有報酬的列的相異 sid 數。
"""
from __future__ import annotations
import os, sys, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                               # D.DATA ⇒ 快照
D = H2.D
from backtest import researchp7 as P7, researchp12 as P12, p4_features as P4F, tradability as T

OUT = "backtest/resultsSR"
AFC = "backtest/resultsAFC"
COST_RT = 0.00585
HS = (20, 60, 120)
QS = (0.10, 0.25, 0.50, 0.75, 0.90)
B, SEED = 2000, 20260923
ANCHOR_S1_MAIN = 2881


def load_all():
    cal = D.load_calendar(); ncal = len(cal)
    panel = P4F.read_panel(os.path.join(AFC, "panel.csv.gz"))
    p = panel[(panel["measure_date"] >= pd.Timestamp(P12.START)) & panel["eligible"].astype(bool)]
    p = p[(p["rev_hi24"] == 100) & (p["ma60_up"] == 100) & (p["ma_stack"] == 0)]
    sids = sorted(set(p["stock_id"]))                     # ⭐ 只載有門檻B 訊號的股（其他股 build 本來就用不到）
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens, highs, stk = {}, {}, {}, {}
    for s in sids:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float)
        highs[s] = st.df["high"].to_numpy(float); stk[s] = st
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    return cal, ncal, sig, closes, opens, highs, stk


def measure(sig, cal, closes, opens, highs, trad, dl, k_of):
    """每列 × 每個持有期：回 DataFrame（列 × h）與計數。k_of(e, h) ⇒ 排程出場的日曆位置。"""
    ncal = len(cal); rows = []
    for i, (s, e) in enumerate(zip(sig["sid"], sig["entry_pos"])):
        e = int(e); tb = trad[s]; o = opens[s]
        base = {"i": i, "sid": s, "entry_pos": e, "entry_date": cal[e], "emonth": cal[e].strftime("%Y-%m")}
        if not tb["trd"][e]:
            for h in HS:
                rows.append({**base, "h": h, "status": "halt_in"})
            continue
        if tb["up_o"][e] or not (np.isfinite(o[e]) and o[e] > 0):
            for h in HS:
                rows.append({**base, "h": h, "status": "limit_up" if tb["up_o"][e] else "no_open"})
            continue
        ep = float(o[e])
        info = dl.get(s, {"last": ncal - 1, "status": "live"})
        for h in HS:
            x = k_of(e, h)
            r = {**base, "h": h, "x_sched": x, "ep": ep}
            if x >= ncal:
                r["status"] = "beyond_cal"; rows.append(r); continue
            t = x; done = False
            while t < ncal:
                if tb["trd"][t] and not tb["dn_o"][t] and np.isfinite(o[t]) and o[t] > 0:
                    r.update(status="ok" if t == x else "exit_delayed", t_exit=t, px=float(o[t])); done = True; break
                if (not tb["trd"][t]) and t > info["last"]:
                    if info["status"].startswith("delisted"):
                        r.update(status="delist_settled", t_exit=t, px=float(closes[s][t])); done = True
                    else:
                        r.update(status="delist_ambig")
                    break
                t += 1
            if not done:
                r.setdefault("status", "unresolved"); rows.append(r); continue
            te = r["t_exit"]
            hh = highs[s][e:te]; hh = hh[np.isfinite(hh)]
            mx = max(hh.max() if len(hh) else -np.inf, r["px"] if r["status"] != "delist_settled" else -np.inf)
            if not np.isfinite(mx):
                mx = r["px"]
            r["ret"] = r["px"] / ep - 1.0 - COST_RT
            r["maxup"] = mx / ep - 1.0
            rows.append(r)
    return pd.DataFrame(rows)


def boot(df_h: pd.DataFrame, cols, rng_idx, months):
    """月分群 bootstrap：rng_idx 是 B × M 的月索引（對 months 陣列）；回 {col: (B × len(QS)) 陣列}。"""
    g = {m: df_h.loc[df_h["emonth"] == m, cols].to_numpy(float) for m in months}
    out = {c: np.empty((B, len(QS))) for c in cols}
    for b in range(B):
        X = np.concatenate([g[months[j]] for j in rng_idx[b] if len(g[months[j]])], axis=0)
        qs = np.quantile(X, QS, axis=0)
        for ci, c in enumerate(cols):
            out[c][b] = qs[:, ci]
    return out


def table(M: pd.DataFrame, rng_idx, months, tag=""):
    recs = []
    for h in HS:
        d = M[(M["h"] == h) & M["ret"].notna()]
        bs = boot(d, ["ret", "maxup"], rng_idx, months)
        for col, nm in (("ret", "報酬（扣0.585%）"), ("maxup", "期間最高點（未扣成本）")):
            q = np.quantile(d[col].to_numpy(float), QS)
            lo, hi = np.percentile(bs[col], 2.5, axis=0), np.percentile(bs[col], 97.5, axis=0)
            rec = {"版本": tag, "持有": h, "量": nm, "筆數": len(d), "相異檔數": d["sid"].nunique(), "月數": d["emonth"].nunique()}
            for j, qq in enumerate(QS):
                p = "p{:d}".format(int(round(qq * 100)))
                rec[p] = q[j]; rec[p + "_lo"] = lo[j]; rec[p + "_hi"] = hi[j]
            rec["平均"] = float(d[col].mean())
            recs.append(rec)
    return pd.DataFrame(recs)


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    cal, ncal, sig, closes, opens, highs, stk = load_all()
    w0, w1 = P12.win_bounds(cal, "全窗")
    assert cal[w0] == pd.Timestamp("2017-03-02") and cal[w1] == pd.Timestamp("2026-08-24"), (cal[w0], cal[w1])
    n_all = len(sig)
    sig = sig[(sig["entry_pos"] >= w0) & (sig["entry_pos"] <= w1)].reset_index(drop=True)
    assert cal[int(sig["entry_pos"].min())] >= pd.Timestamp("2017-03-02"), "⛔ 讀到主窗以前"
    print("[母體] build_sig_gate_b 全部 {:,} 列 ⇒ entry 落主窗 {:,} 列（旁證 {:,}）／{:,} 檔／{} 個量測月｜entry {}～{}｜{:.0f}s".format(
        n_all, len(sig), ANCHOR_S1_MAIN, sig["sid"].nunique(), sig["month"].nunique(), cal[int(sig["entry_pos"].min())].date(),
        cal[int(sig["entry_pos"].max())].date(), time.time() - t0), flush=True)
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    M = measure(sig, cal, closes, opens, highs, trad, dl, lambda e, h: D.exit_pos(e, h))
    M0 = measure(sig, cal, closes, opens, highs, trad, dl, lambda e, h: e + h)        # 敏感度：進場日算第 0 個
    # 最後出場日不得超過資料尾；主窗外的報酬只用到持有期（entry 在窗內）
    # 硬斷點：持有區間 (entry, 出場日] 內
    bp = {s: [b["pos"] for b in D.breakpoints(stk[s].df, stk[s].event_dates)] for s in set(sig["sid"])}
    M["bp_in_hold"] = [bool(pd.notna(te) and any(e < p_ <= te for p_ in bp[s])) for s, e, te in zip(M["sid"], M["entry_pos"], M.get("t_exit", pd.Series(np.nan, index=M.index)))]
    cnt = M.groupby(["h", "status"]).size().unstack(fill_value=0)
    cnt["硬斷點在持有區間（未剔）"] = M[M["ret"].notna()].groupby("h")["bp_in_hold"].sum()
    print("[計數]\n" + cnt.to_string(), flush=True)
    # bootstrap 月索引（一次抽、所有欄共用）
    months = np.array(sorted(M["emonth"].unique()))
    rng = np.random.default_rng(SEED)
    rng_idx = rng.integers(0, len(months), size=(B, len(months)))
    TB = table(M, rng_idx, months, "主表")
    TBbp = table(M[~M["bp_in_hold"]], rng_idx, months, "敏感度：剔硬斷點")
    TB0 = table(M0, rng_idx, months, "敏感度：entry+k")
    ALL = pd.concat([TB, TBbp, TB0], ignore_index=True)
    ALL.to_csv(os.path.join(OUT, "ref_interval.csv"), index=False, encoding="utf-8")
    M.to_csv(os.path.join(OUT, "ref_interval_trades.csv.gz"), index=False)
    cnt.to_csv(os.path.join(OUT, "ref_interval_counts.csv"), encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    fmt = ALL.copy()
    for c in fmt.columns:
        if c.startswith("p") or c == "平均":
            fmt[c] = (fmt[c] * 100).map("{:+.2f}".format)
    print(fmt.to_string())
    # 查核①：總筆數
    n_sig = len(sig)
    # 查核②：120 日報酬另一種寫法抽 20 筆手算
    chk = hand_check(M, cal, n=20)
    # 查核③：與 build 的 g_H120（收盤出場）同列比較中位（只當旁證：出場價不同，應接近）
    g = sig["g_H120"].to_numpy(float) - COST_RT
    summ = {"快照": H2.SHA, "主窗": [str(cal[w0].date()), str(cal[w1].date())], "build全部列": n_all, "主窗列": n_sig,
            "旁證2881相符": bool(n_sig == ANCHOR_S1_MAIN), "相異檔": int(sig["sid"].nunique()), "月數": int(len(months)),
            "計數": {int(h): {k: int(v) for k, v in cnt.loc[h].items()} for h in cnt.index},
            "手算20筆最大差": chk, "build_g_H120扣成本中位": float(np.median(g)), "B": B, "種子": SEED,
            "耗時秒": round(time.time() - t0)}
    json.dump(summ, open(os.path.join(OUT, "ref_interval_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))


def hand_check(M, cal, n=20):
    """120 日報酬用【另一條路】重算：直接讀 data/stocks 原始 open 的 CSV（字串→float）、自己從 data/adj 逐事件連乘還原因子
    （⛔ 不呼叫 load_stock／cum_factor_series），日期用字串對；抽 status＝ok 的 n 筆（種子 20260923）。"""
    import csv
    d = M[(M["h"] == 120) & (M["status"] == "ok")]
    pick = d.sample(n=n, random_state=SEED)
    diffs = []
    for r in pick.itertuples():
        rows = {x["date"]: x for x in csv.DictReader(open(os.path.join(D.DATA, "stocks", r.sid + ".csv"), encoding="utf-8"))}
        ev = []
        pa = os.path.join(D.DATA, "adj", r.sid + ".csv")
        if os.path.exists(pa):
            ev = [(x["date"], float(x["factor"])) for x in csv.DictReader(open(pa, encoding="utf-8"))]
        def adj_open(ds):
            f = 1.0
            for dd, fac in ev:
                if dd > ds:
                    f *= fac                               # F(d) ＝ 事件日嚴格大於 d 的 factor 連乘
            return float(rows[ds]["open"]) * f
        de, dx = cal[r.entry_pos].strftime("%Y-%m-%d"), cal[int(r.t_exit)].strftime("%Y-%m-%d")
        hand = adj_open(dx) / adj_open(de) - 1 - COST_RT
        # 第 120 個交易日：用日曆字串清單自己數（進場日算第 1 個）
        cal_s = [x.strftime("%Y-%m-%d") for x in cal]
        assert cal_s[cal_s.index(de) + 119] == dx, (r.sid, de, dx)
        diffs.append(abs(hand - r.ret))
        print("  手算 {} 進 {} 出 {}：程式 {:+.6f}｜手算 {:+.6f}｜差 {:.1e}".format(r.sid, de, dx, r.ret, hand, abs(hand - r.ret)))
    return float(max(diffs))


if __name__ == "__main__":
    main()

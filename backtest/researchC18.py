"""C18 候選「弱訊號合成分數」獨立重跑（回測線計算子代理，照寫死定義自寫，未看對方腳本）。

定義（寫死）：
  幣 12：BTC ETH SOL BNB XRP ADA DOGE LINK LTC BCH TRX XLM（data/crypto/*.csv 日線）
  7 特徵（當日收盤可得）與符號：
    c17   近 10 日內（含當日）曾有「quote_volume > 前 20 日均額×2 且 當日漲 >5%」(0/1)  +
    trend ln(close / 200 日均收盤)                                                      +
    mom20 20 日報酬 close_t/close_{t-20}-1                                               +
    rev3  3 日報酬 close_t/close_{t-3}-1                                                 +
    taker7 taker_buy_quote/quote_volume 的 7 日均                                       -
    hi20  close / 近 20 日（含當日）最高收盤 - 1                                          +
    vol20 日報酬 20 日標準差（ddof=1）                                                   -
  各幣自身擴張視窗 z（有效值≥250 才算，只用當日及以前），缺值補 0；分數＝Σ(符號×z)/7。
  部位：分數 > 0.383 當日收盤持多，吃次日 close-to-close；否則空手。
  成本：進出各 0.1%（進場成本記在持倉第一天、出場成本記在持倉最後一天）＋持倉日資金費 10%/365。
  兩段：S1 2018-01-01～2023-12-31、S2 2024-01-01～資料末（以訊號日歸段；段內部位獨立，
        跨段的連續持有在各段各算一筆、各收進出成本）。
  評估：持倉日日均淨報酬 − 該段無條件日均（次日毛報酬的段內平均）。
  假訊號：段內部位序列循環平移 300 次，平移量 k~U{30..n-30}，種子 [18, 段號, 幣號]，
        單尾 p＝(1+#{null≥obs})/(1+300)。
⚠ 污染註記：c17、trend 兩個特徵是對方看過 2024～ 後挑進來的，S2 不是乾淨的樣本外。
"""
import json, os, sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "crypto")
OUT = os.path.join(ROOT, "backtest", "resultsC18")

COINS = "BTC ETH SOL BNB XRP ADA DOGE LINK LTC BCH TRX XLM".split()
FEATS = [("c17", 1), ("trend", 1), ("mom20", 1), ("rev3", 1), ("taker7", -1), ("hi20", 1), ("vol20", -1)]
THR = 0.383
COST = 0.001
FUND = 0.10 / 365
NSH = 300
MINP = 250
SEGS = [("S1", "2018-01-01", "2023-12-31"), ("S2", "2024-01-01", "2099-12-31")]


def load(c):
    d = pd.read_csv(os.path.join(DATA, f"{c}.csv"), parse_dates=["date"]).sort_values("date")
    return d.set_index("date")


def features(d):
    cl, qv = d["close"], d["quote_volume"]
    ret = cl / cl.shift(1) - 1
    ev = ((qv > 2 * qv.shift(1).rolling(20, min_periods=20).mean()) & (ret > 0.05)).astype(float)
    ev[qv.shift(1).rolling(20, min_periods=20).mean().isna() | ret.isna()] = np.nan
    f = pd.DataFrame(index=d.index)
    f["c17"] = ev.rolling(10, min_periods=1).max()  # 有任何一天可判即可；全 NaN 則 NaN
    f["trend"] = np.log(cl / cl.rolling(200, min_periods=200).mean())
    f["mom20"] = cl / cl.shift(20) - 1
    f["rev3"] = cl / cl.shift(3) - 1
    f["taker7"] = (d["taker_buy_quote"] / qv).rolling(7, min_periods=7).mean()
    f["hi20"] = cl / cl.rolling(20, min_periods=20).max() - 1
    f["vol20"] = ret.rolling(20, min_periods=20).std()
    return f, ret


def expz(x):
    m = x.expanding(min_periods=MINP).mean()
    s = x.expanding(min_periods=MINP).std()
    z = (x - m) / s
    return z.replace([np.inf, -np.inf], np.nan)


def build(c):
    d = load(c)
    f, ret = features(d)
    z = pd.DataFrame({k: expz(f[k]) for k, _ in FEATS})
    sc = sum(sg * z[k].fillna(0.0) for k, sg in FEATS) / 7.0
    rnext = d["close"].shift(-1) / d["close"] - 1
    out = pd.DataFrame({"score": sc, "rnext": rnext, "c17": f["c17"].fillna(0.0),
                        "nz": z.notna().sum(axis=1)})
    return out


def seg_slice(df, s0, s1):
    m = (df.index >= s0) & (df.index <= s1) & df["rnext"].notna()
    return df.loc[m]


def net_series(pos, r):
    pos = pos.astype(int)
    prev = np.r_[0, pos[:-1]]
    nxt = np.r_[pos[1:], 0]
    net = r - FUND - COST * (prev == 0) - COST * (nxt == 0)
    return net, prev


def excess(pos, r):
    held = pos == 1
    if held.sum() == 0:
        return np.nan
    net, _ = net_series(pos, r)
    return net[held].mean() - r.mean()


def trades(pos, r):
    pos = pos.astype(int)
    net, prev = net_series(pos, r)
    out, cur = [], None
    for i in range(len(pos)):
        if pos[i] == 1:
            cur = (1 + net[i]) if (prev[i] == 0) else cur * (1 + net[i])
            if i == len(pos) - 1 or pos[i + 1] == 0:
                out.append(cur - 1)
    return np.array(out)


def evaluate(pos, r, seed):
    pos = np.asarray(pos, dtype=int)
    r = np.asarray(r, dtype=float)
    n = len(r)
    obs = excess(pos, r)
    tr = trades(pos, r)
    res = {"n_days": int(n), "hold_days": int(pos.sum()), "n_trades": int(len(tr)),
           "uncond_mean": float(r.mean()), "excess": None if np.isnan(obs) else float(obs)}
    if pos.sum() > 0:
        net, _ = net_series(pos, r)
        res["hold_net_mean"] = float(net[pos == 1].mean())
        res["hold_gross_mean"] = float(r[pos == 1].mean())
        res["trade_win"] = float((tr > 0).mean())
        res["trade_median"] = float(np.median(tr))
    rng = np.random.default_rng(seed)
    ks = rng.integers(30, n - 30 + 1, size=NSH)
    if np.isnan(obs):
        res["p"] = None
        return res
    nul = np.array([excess(np.roll(pos, k), r) for k in ks])
    ge = int(np.sum(np.nan_to_num(nul, nan=-np.inf) >= obs))
    res["p"] = (1 + ge) / (1 + NSH)
    res["null_ge"] = ge
    return res


def run_variant(B, posfun, label, do_p=True):
    out = {}
    for si, (sn, s0, s1) in enumerate(SEGS):
        rows = {}
        for ci, c in enumerate(COINS):
            df = B[c]
            pfull = posfun(df)
            dfs = seg_slice(df.assign(pos=pfull), s0, s1)
            if len(dfs) < 61:
                continue
            seed = [18, si, ci]
            if do_p:
                rows[c] = evaluate(dfs["pos"].values, dfs["rnext"].values, seed)
            else:
                rows[c] = evaluate_nop(dfs["pos"].values, dfs["rnext"].values)
        out[sn] = {"coins": rows, "summary": summarize(rows)}
    return out


def evaluate_nop(pos, r):
    pos = np.asarray(pos, dtype=int)
    obs = excess(pos, r)
    return {"n_days": int(len(r)), "hold_days": int(pos.sum()),
            "excess": None if np.isnan(obs) else float(obs)}


def summarize(rows):
    ex = [v["excess"] for v in rows.values() if v["excess"] is not None]
    ps = [v.get("p") for v in rows.values() if v.get("p") is not None]
    return {"n_coins": len(rows), "n_with_hold": len(ex), "n_pos": int(sum(e > 0 for e in ex)),
            "n_p_lt_0.1": int(sum(p < 0.1 for p in ps)),
            "median_excess": float(np.median(ex)) if ex else None}


def main():
    os.makedirs(OUT, exist_ok=True)
    B = {c: build(c) for c in COINS}

    # 門檻核對：12 幣 2018～2023 全部分數（訊號日）分位
    pool = pd.concat([seg_slice(B[c], "2018-01-01", "2023-12-31") for c in COINS])
    q_all = {q: float(np.percentile(pool["score"], q)) for q in (70, 80, 90)}
    nzpool = pool[pool["nz"] > 0]
    q_nz = {q: float(np.percentile(nzpool["score"], q)) for q in (70, 80, 90)}
    full = pool[pool["nz"] == 7]
    q_full = {q: float(np.percentile(full["score"], q)) for q in (70, 80, 90)}
    thr_info = {"fixed": THR, "pool_all": q_all, "pool_any_z": q_nz, "pool_all7_z": q_full,
                "n_pool_all": int(len(pool)), "n_pool_any_z": int(len(nzpool)), "n_pool_all7": int(len(full)),
                "diff_p80_all_minus_0.383": q_all[80] - THR, "diff_p80_anyz_minus_0.383": q_nz[80] - THR,
                "diff_p80_all7_minus_0.383": q_full[80] - THR}

    res = {"definition": __doc__, "threshold_check": thr_info}
    res["main"] = run_variant(B, lambda df: (df["score"] > THR).astype(int), "main")
    res["c17_control"] = run_variant(B, lambda df: (df["c17"] > 0.5).astype(int), "c17")
    rob = {}
    for q in (70, 90):
        t = q_all[q]
        rob[f"thr_p{q}_all"] = {"thr": t, **run_variant(B, lambda df, t=t: (df["score"] > t).astype(int), "q")}
    rob["thr_p80_all"] = {"thr": q_all[80], **run_variant(B, lambda df: (df["score"] > q_all[80]).astype(int), "q")}
    rob["lag1"] = run_variant(B, lambda df: (df["score"] > THR).astype(int).shift(1).fillna(0).astype(int), "lag")
    # 解讀差異變體：段內只算「7 個 z 都已可得」的日子
    def full7(df):
        return (df["score"] > THR).astype(int)
    rv = {}
    for si, (sn, s0, s1) in enumerate(SEGS):
        rows = {}
        for ci, c in enumerate(COINS):
            dfs = seg_slice(B[c], s0, s1)
            dfs = dfs[dfs["nz"] == 7]
            if len(dfs) < 61:
                continue
            rows[c] = evaluate((dfs["score"] > THR).astype(int).values, dfs["rnext"].values, [18, si, ci])
        rv[sn] = {"coins": rows, "summary": summarize(rows)}
    rob["only_full7_days"] = rv
    res["robust"] = rob

    # 逐年（12 幣中位）：主規則與 C17 對照，年內獨立切段
    yearly = {}
    for y in range(2018, 2027):
        yy = {}
        for name, fn in (("C18", lambda df: (df["score"] > THR).astype(int)),
                         ("C17", lambda df: (df["c17"] > 0.5).astype(int))):
            ex, hd = [], 0
            for c in COINS:
                dfs = seg_slice(B[c].assign(pos=fn(B[c])), f"{y}-01-01", f"{y}-12-31")
                if len(dfs) < 30:
                    continue
                e = excess(dfs["pos"].values, dfs["rnext"].values)
                hd += int(dfs["pos"].sum())
                if not np.isnan(e):
                    ex.append(e)
            yy[name] = {"n_coins": len(ex), "n_pos": int(sum(e > 0 for e in ex)),
                        "median_excess": float(np.median(ex)) if ex else None, "hold_days_total": hd}
        yearly[str(y)] = yy
    res["yearly"] = yearly

    # IC：分數對次日報酬 Spearman
    ic = {}
    for sn, s0, s1 in SEGS:
        per, pooled = {}, []
        for c in COINS:
            dfs = seg_slice(B[c], s0, s1)
            per[c] = float(dfs["score"].rank().corr(dfs["rnext"].rank()))
            d2 = dfs[dfs["nz"] > 0]
            pooled.append(d2[["score", "rnext"]])
        P = pd.concat(pooled)
        ic[sn] = {"per_coin": per, "median": float(np.median(list(per.values()))),
                  "n_pos": int(sum(v > 0 for v in per.values())),
                  "pooled_anyz": float(P["score"].rank().corr(P["rnext"].rank()))}
    res["ic"] = ic

    # 對方自跑數字核對
    claim = {"S1": {"n_pos": 9, "median_excess": 0.0024, "BTC_excess": 0.0030, "BTC_p": 0.007},
             "S2": {"n_pos": 10, "n_p_lt_0.1": 7, "median_excess": 0.0045, "BTC_excess": 0.0020, "BTC_p": 0.013,
                    "BTC_hold_days": 185, "BTC_trades": 41}}
    mine = {}
    for sn in ("S1", "S2"):
        m = res["main"][sn]
        b = m["coins"]["BTC"]
        mine[sn] = {"n_pos": m["summary"]["n_pos"], "n_p_lt_0.1": m["summary"]["n_p_lt_0.1"],
                    "median_excess": m["summary"]["median_excess"], "BTC_excess": b["excess"], "BTC_p": b["p"],
                    "BTC_hold_days": b["hold_days"], "BTC_trades": b["n_trades"]}
    res["claim_vs_mine"] = {"claim": claim, "mine": mine}

    with open(os.path.join(OUT, "C18.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)

    # 主表 CSV
    rows = []
    for var in ("main", "c17_control"):
        for sn in ("S1", "S2"):
            for c, v in res[var][sn]["coins"].items():
                rows.append({"variant": var, "seg": sn, "coin": c, **{k: v.get(k) for k in
                             ("excess", "hold_days", "n_trades", "p", "n_days", "uncond_mean", "hold_net_mean",
                              "trade_win", "trade_median")}})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "C18_main_table.csv"), index=False)

    # 印出摘要
    pd.set_option("display.width", 200)
    print("threshold:", json.dumps(thr_info, indent=1))
    for var in ("main", "c17_control"):
        for sn in ("S1", "S2"):
            t = pd.DataFrame(res[var][sn]["coins"]).T[["excess", "hold_days", "n_trades", "p", "n_days",
                                                       "trade_win", "trade_median"]]
            print(f"\n== {var} {sn} ==", res[var][sn]["summary"])
            print(t.to_string())
    for k, v in rob.items():
        for sn in ("S1", "S2"):
            print("robust", k, v.get("thr", ""), sn, v[sn]["summary"], "BTC",
                  {kk: v[sn]["coins"]["BTC"].get(kk) for kk in ("excess", "p", "hold_days", "n_trades")})
    print("\nyearly", json.dumps(yearly))
    print("\nic", json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "per_coin"} for k, v in ic.items()}))
    print("ic per coin", json.dumps({k: v["per_coin"] for k, v in ic.items()}))
    print("\nclaim vs mine", json.dumps(res["claim_vs_mine"], indent=1))


if __name__ == "__main__":
    main()

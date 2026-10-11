# -*- coding: utf-8 -*-
"""PREREGC17 早年格重報 --check（researchC17_early 讀法 E10）：獨立寫法——csv 模組讀原始檔、純迴圈，不 import researchC17／researchC17_early／researchC17_btccm 任何函式。
重算並與 resultsC17/early/C17_early.json 逐位比（容差 1e-12）：
  ① 早年主格、窗到 0816、Bitstamp 價兩格的交易清單（訊號／進場／出場日）與每天多賺、筆數；
  ② 幣本位錢包（強平改用「權益（以日低計）≤ 維持保證金」不等式直接判，不解 Lp）：3／24 張固定與按今日比例的窗末權益、強平日、逐年增減；
  ③ 其他三項（BTC 2018～2023、2024～、8 幣合併）每天多賺：資金費用 datetime 逐筆歸日、自己判覆蓋；
  ④ 重疊期訊號計數（Binance 對 CM 價量、舊替代版對 CM 新版）；
  ⑤ 兩個會變紅的反例：出場讀成 min、均量含 t ⇒ 早年主格交易清單必須和 JSON 不同。
"""
import csv, os, json, math, datetime as dt

H = os.path.expanduser("~")
PRIV = f"{H}/us-stock-data/data/crypto_private"
PUB = f"{H}/c17data/69e257c882067f4d652d39749b1635dabf54b911/data"
F2019 = f"{H}/c17data/283eec12b2bc0eb17ffa756c5a0efe3a49d16d92/data/meta/crypto_usdt_funding_early/BTCUSDT_2019.csv"
OUTD = f"{H}/tw-p17/backtest/resultsC17/early"
FILL = 0.10 / 365.25
COST = 0.001
END = "2026-10-09"
TOL = 1e-12


def rd(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cm_table():
    return {r["date_utc"]: (float(r["PriceUSD"]) if r["PriceUSD"] else None, float(r["volume_reported_spot_usd_1d"]) if r["volume_reported_spot_usd_1d"] else None)
            for r in rd(f"{PRIV}/coinmetrics/btc_daily.csv")}


def bitstamp_rows():
    out = {}
    for r in rd(f"{PRIV}/BTC.csv"):
        if r["source"] == "bitstamp:btcusd":
            out[r["date"]] = r
    for r in rd(f"{PRIV}/BTC_bitstamp_2013_2017.csv"):
        out.setdefault(r["date"], r)
    return out


def binance_rows(sym="BTC"):
    out = {}
    for r in rd(f"{PUB}/crypto/{sym}.csv"):
        if r["date"] <= END:
            out.setdefault(r["date"], r)
    return out


def days(a, b):
    d0, d1 = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    return [(d0 + dt.timedelta(i)).isoformat() for i in range((d1 - d0).days + 1)]


def early_series(price, end, tail=True, vol="cm"):
    cm, bs, bn = cm_table(), bitstamp_rows(), binance_rows()
    S = {"d": [], "o": [], "h": [], "l": [], "c": [], "q": []}
    prev = None
    for d in days("2012-01-01", end):
        src = bs.get(d) if d <= "2017-08-16" else (bn.get(d) if tail else None)
        assert src is not None, d
        p, v = cm[d]
        if price == "cm":
            o = prev if prev is not None else p
            c = p
        else:
            o, c = float(src["open"]), float(src["close"])
        S["d"].append(d); S["o"].append(o); S["c"].append(c); S["h"].append(float(src["high"])); S["l"].append(float(src["low"]))
        S["q"].append(v if vol == "cm" else float(src["volume"]) * float(src["close"]))
        prev = p
    S["f"] = [FILL] * len(S["d"])
    return S


def sig_list(S, vm=2.0, up=0.05, incl_t=False):
    q, c = S["q"], S["c"]
    out = [False] * len(c)
    for t in range(20, len(c)):
        lo, hi = (t - 20, t) if not incl_t else (t - 19, t + 1)
        avg = sum(q[lo:hi]) / 20.0
        out[t] = (q[t] > vm * avg) and (c[t] / c[t - 1] - 1.0 > up)
    return out


def engine(S, a, b, use_max=True, incl_t=False):
    d = S["d"]
    i0 = max(next(i for i, x in enumerate(d) if x >= a), 20)
    i1 = max(i for i, x in enumerate(d) if x <= b)
    sig = sig_list(S, incl_t=incl_t)
    o, c, lo, f = S["o"], S["c"], S["l"], S["f"]
    trades, net = [], {}
    t = i0
    while t <= i1:
        if not (sig[t] and t + 1 <= i1):
            t += 1; continue
        e = t + 1; k = e; x = None
        while k <= i1:
            m10 = min(lo[k - 10:k])
            thr = max(lo[t], m10) if use_max else min(lo[t], m10)
            g = (c[k] / o[k]) if k == e else (c[k] / c[k - 1])
            cost = COST if k == e else 0.0
            if c[k] < thr:
                if k + 1 <= i1:
                    x = k + 1; g *= o[k + 1] / c[k]; cost += COST
                net[k] = g - 1.0 - f[k] - cost
                break
            net[k] = g - 1.0 - f[k] - cost
            k += 1
        last = min(k, i1)
        trades.append((t, e, last, x))
        if x is None:
            break
        t = x
    wm = sum(c[j] / c[j - 1] - 1.0 for j in range(i0, i1 + 1)) / (i1 - i0 + 1)
    ex = sum(net.values()) / len(net) - wm
    return {"i0": i0, "i1": i1, "trades": trades, "net": net, "wm": wm, "excess": ex,
            "list": [(d[t], d[e], d[x] if x is not None else "") for t, e, l, x in trades]}


# ───────── 幣本位錢包（不等式直接判）─────────
def wallet(S, R, n, ratio=None, W0=0.0715, MMR=0.004, FEE=0.001):
    d, o, c, lo, f = S["d"], S["o"], S["c"], S["l"], S["f"]
    i0, i1 = R["i0"], R["i1"]
    ent = {e: (t, e, l, x) for t, e, l, x in R["trades"]}
    W = W0; pos = None; dead = None; eq = []
    for j in range(i0, i1 + 1):
        if dead:
            eq.append(0.0); continue
        if pos and pos[3] == j:
            N, Pe = pos[4], pos[5]
            W += N / Pe - N / o[j] - FEE * N / o[j]; pos = None
        if j in ent:
            Pe = o[j]; N = n * 100.0 if ratio is None else ratio * W0 * Pe
            W -= FEE * N / Pe
            pos = ent[j] + (N, Pe)
        if pos and pos[1] <= j <= pos[2]:
            N, Pe = pos[4], pos[5]
            W -= f[j] * N / (Pe if j == pos[1] else c[j - 1])
            eq_low = W + N / Pe - N / lo[j]
            if eq_low <= MMR * N / lo[j]:
                dead = d[j]; W = 0.0; eq.append(0.0); continue
            eq.append(W + N / Pe - N / c[j])
        else:
            eq.append(W)
    yrs, start = [], W0
    for y in sorted(set(x[:4] for x in d[i0:i1 + 1])):
        last = max(k for k in range(i0, i1 + 1) if d[k][:4] == y)
        yrs.append(eq[last - i0] - start); start = eq[last - i0]
    usd = [W0 * c[i0 - 1]] + [eq[k] * c[i0 + k] for k in range(len(eq))]
    T = i1 - i0 + 1
    ann = (usd[-1] / usd[0]) ** (365.25 / T) - 1 if usd[-1] > 0 else -1.0
    return {"W_end": eq[-1], "liq": dead, "yrs": yrs, "ann": ann}


# ───────── 其他三項：Binance＋BTCUSDT 資金費（datetime 歸日）─────────
def funding_by_day():
    acc = {}
    rows = rd(F2019) + rd(f"{PUB}/crypto_funding/BTCUSDT.csv")
    hs = []
    for r in rows:
        ts = dt.datetime(1970, 1, 1) + dt.timedelta(seconds=int(r["calc_time"]) // 1000)
        ts = ts.replace(minute=0, second=0)
        hs.append(ts)
        day = (ts - dt.timedelta(seconds=1)).date().isoformat()
        acc.setdefault(day, {}).setdefault(ts, float(r["last_funding_rate"]))
    return acc, min(hs), max(hs)


def binance_series(sym, drop30, fund):
    acc, first, last = fund
    rows = binance_rows(sym)
    ds = sorted(rows)
    if drop30:
        ds = ds[30:]
    S = {"d": ds, "o": [], "h": [], "l": [], "c": [], "q": [], "f": []}
    for d in ds:
        r = rows[d]
        S["o"].append(float(r["open"])); S["h"].append(float(r["high"])); S["l"].append(float(r["low"])); S["c"].append(float(r["close"]))
        S["q"].append(float(r["quote_volume"]))
        d0 = dt.datetime.fromisoformat(d)
        cov = first <= d0 + dt.timedelta(hours=8) and d0 + dt.timedelta(days=1) <= last
        S["f"].append(sum(acc.get(d, {}).values()) if cov else FILL)
    return S


def agree(a, b):
    both = sum(1 for x, y in zip(a, b) if x and y); oa = sum(1 for x, y in zip(a, b) if x and not y); ob = sum(1 for x, y in zip(a, b) if y and not x)
    return both, oa, ob


def main():
    J = json.load(open(f"{OUTD}/C17_early.json", encoding="utf-8"))
    res = {"比對": [], "反例": []}
    nd = 0; maxd = 0.0

    def cmp(name, a, b):
        nonlocal nd, maxd
        if isinstance(a, float) or isinstance(b, float):
            if a is None or b is None:
                ok = a == b; dd = 0.0 if ok else float("inf")
            else:
                dd = abs(a - b); ok = dd <= TOL
            maxd = max(maxd, dd if math.isfinite(dd) else 0.0)
        else:
            ok = a == b; dd = None
        nd += int(not ok)
        res["比對"].append({"項": name, "相同": bool(ok), "差": dd})

    E = J["早年格"]
    S_main = early_series("cm", "2017-12-31")
    S_bs2 = early_series("cm", "2017-08-16", tail=False)
    S_px = early_series("bs", "2017-12-31")
    S_px2 = early_series("bs", "2017-08-16", tail=False)
    R_main = engine(S_main, "2013-01-01", "2017-12-31")
    R_bs2 = engine(S_bs2, "2013-01-01", "2017-08-16")
    for key, S, R in (("主格_CM價量_日高低Bitstamp接Binance_全窗", S_main, R_main), ("敏感度_CM價量_日高低Bitstamp_窗到0816", S_bs2, R_bs2),
                      ("敏感度_Bitstamp開高低收_CM量_全窗", S_px, engine(S_px, "2013-01-01", "2017-12-31")),
                      ("敏感度_Bitstamp開高低收_CM量_窗到0816", S_px2, engine(S_px2, "2013-01-01", "2017-08-16"))):
        cmp(f"{key}｜每天多賺", R["excess"], E[key]["摘要"]["每天多賺"])
        cmp(f"{key}｜筆數", len(R["trades"]), E[key]["摘要"]["筆數"])
    jl = [(t["signal"], t["entry"], t["exit"]) for t in J["早年主格交易清單_只日期與報酬"]]
    cmp("早年主格交易清單", R_main["list"], jl)
    jl2 = [(t["signal"], t["entry"], t["exit"]) for t in J["早年敏感度0816交易清單_只日期與報酬"]]
    cmp("早年0816交易清單", R_bs2["list"], jl2)
    # 每筆報酬
    for (t, e, l, x), jt in zip(R_main["trades"], J["早年主格交易清單_只日期與報酬"]):
        r = 1.0
        for k in range(e, l + 1):
            r *= 1 + R_main["net"][k]
        cmp(f"早年主格每筆報酬｜{jt['entry']}", r - 1, jt["ret"])
    # 幣本位
    bn = binance_rows()
    close_today = float(bn[END]["close"])
    C = J["幣本位_seq334口徑_早年"]
    for blk, S, R in (("主格全窗", S_main, R_main), ("敏感度窗到0816", S_bs2, R_bs2)):
        for n in (3, 24):
            for tag, ratio in (("固定", None), ("按今日比例", n * 100.0 / (0.0715 * close_today))):
                w = wallet(S, R, n, ratio)
                j = C[blk][f"{n}張_{tag}"]
                cmp(f"幣本位{blk}{n}張{tag}｜窗末權益", w["W_end"], j["窗末錢包權益BTC"])
                cmp(f"幣本位{blk}{n}張{tag}｜強平日", w["liq"], j["強平日"])
                cmp(f"幣本位{blk}{n}張{tag}｜USD年化", w["ann"], j["USD_囤幣加訊號"]["年化"])
                for y, (a, jy) in enumerate(zip(w["yrs"], j["逐年"])):
                    cmp(f"幣本位{blk}{n}張{tag}｜{jy['年']}增減", a, jy["增減BTC"])
    # 其他三項
    fund = funding_by_day()
    O = J["其他三項_v2max同引擎重算"]
    B = binance_series("BTC", False, fund)
    cmp("BTC_W1每天多賺", engine(B, "2018-01-01", "2023-12-31")["excess"], O["BTC_W1"]["每天多賺"])
    cmp("BTC_W2每天多賺", engine(B, "2024-01-01", "2026-10-09")["excess"], O["BTC_W2"]["每天多賺"])
    tot, nh = 0.0, 0
    for sym in ("SOL", "ETH", "BNB", "XRP", "ADA", "DOGE", "LINK", "LTC"):
        S = binance_series(sym, True, fund)
        R = engine(S, S["d"][0], END)
        tot += sum(R["net"].values()) - R["wm"] * len(R["net"]); nh += len(R["net"])
        cmp(f"8幣各幣_{sym}", R["excess"], O["8幣各幣"][sym])
    cmp("8幣合併每天多賺", tot / nh, O["8幣合併"]["每天多賺"])
    # 重疊期訊號（CM 對 Binance）
    cm = cm_table()
    ds = sorted(bn)
    Sb = {"d": ds, "q": [float(bn[d]["quote_volume"]) for d in ds], "c": [float(bn[d]["close"]) for d in ds]}
    Sc = {"d": ds, "q": [cm[d][1] for d in ds], "c": [cm[d][0] for d in ds]}
    sb, sc = sig_list(Sb), sig_list(Sc)
    OV = J["來源可信度"]["ⓑ_CM與Binance"]["窗"]
    for wk, (a, b) in (("全段", (ds[0], END)), ("BTC_W1", ("2018-01-01", "2023-12-31")), ("BTC_W2", ("2024-01-01", END))):
        i0 = max(next(i for i, x in enumerate(ds) if x >= a), 20); i1 = max(i for i, x in enumerate(ds) if x <= b)
        both, oa, ob = agree(sb[i0:i1 + 1], sc[i0:i1 + 1])
        jj = OV[wk]["訊號_B對C"]
        cmp(f"重疊ⓑ{wk}｜兩版都有／只A／只B", (both, oa, ob), (jj["兩版都有"], jj["只A"], jj["只B"]))
    # 重疊 ⓒ：舊替代版（Bitstamp 價與量，2013-01-01 起）對 CM 新版
    bs = bitstamp_rows()
    d2 = days("2013-01-01", "2017-08-16")
    So = {"q": [float(bs[d]["volume"]) * float(bs[d]["close"]) for d in d2], "c": [float(bs[d]["close"]) for d in d2]}
    so = sig_list(So)[20:]
    sn_all = sig_list(S_bs2)
    k0 = S_bs2["d"].index("2013-01-21")
    sn = sn_all[k0:]
    both, oa, ob = agree(so, sn)
    jj = J["來源可信度"]["ⓒ_CM與Bitstamp"]["訊號_舊替代版(A)對CM新版(B)"]
    cmp("重疊ⓒ｜兩版都有／只A／只B", (both, oa, ob), (jj["兩版都有"], jj["只A"], jj["只B"]))
    # 反例
    for name, kw in (("出場讀成 min", {"use_max": False}), ("均量含 t", {"incl_t": True})):
        Rm = engine(S_main, "2013-01-01", "2017-12-31", **kw)
        red = Rm["list"] != jl
        res["反例"].append({"反例": name, "交易清單和JSON不同(變紅)": red, "反例每天多賺": Rm["excess"]})
        nd += int(not red)
    res["比對次數"] = len(res["比對"]); res["不同數"] = nd; res["最大差"] = maxd
    with open(f"{OUTD}/check.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("check: 比對", len(res["比對"]), "不同(含反例沒變紅)", nd, "最大差", maxd)


if __name__ == "__main__":
    main()

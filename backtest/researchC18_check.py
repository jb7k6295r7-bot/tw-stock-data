"""C18 獨立核對：不 import researchC18，以 csv 模組＋逐日迴圈／Welford／彙總式成本重算主結果與 C17 對照。

與主程式的寫法差異：
  - 讀檔用 csv 模組，滾動統計全部自寫迴圈（不用 pandas rolling/expanding）
  - 擴張 z 用 Welford 線上更新
  - 超額報酬用彙總式：(Σr_持倉 − FUND×H − COST×2×筆數)/H − mean(r)，不逐日記成本
  - 假訊號用同一種子 [18, 段號, 幣號] 與同一平移量抽法（p 可相同）
判同：每段每幣 excess、hold_days、n_trades、p 差 ≤ 1e-9。
"""
import csv, json, math, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "LINK", "LTC", "BCH", "TRX", "XLM"]
SIGNS = {"c17": 1, "trend": 1, "mom20": 1, "rev3": 1, "taker7": -1, "hi20": 1, "vol20": -1}
THR, COST, FUND, NSH, MINP = 0.383, 0.001, 0.10 / 365, 300, 250
SEGS = [("S1", "2018-01-01", "2023-12-31"), ("S2", "2024-01-01", "2099-12-31")]
NAN = float("nan")


def read(c):
    with open(os.path.join(ROOT, "data", "crypto", c + ".csv"), newline="") as fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda x: x["date"])
    g = lambda k: [float(x[k]) for x in rows]
    return [x["date"] for x in rows], g("close"), g("quote_volume"), g("taker_buy_quote")


def window_ok(a, i, w):
    if i - w + 1 < 0:
        return None
    seg = a[i - w + 1:i + 1]
    if any(math.isnan(v) for v in seg):
        return None
    return seg


def feats(cl, qv, tq):
    n = len(cl)
    ret = [NAN] + [cl[i] / cl[i - 1] - 1 for i in range(1, n)]
    ev = [NAN] * n
    for i in range(20, n):
        base = sum(qv[i - 20:i]) / 20.0
        ev[i] = 1.0 if (qv[i] > 2 * base and ret[i] > 0.05) else 0.0
    F = {k: [NAN] * n for k in SIGNS}
    ratio = [tq[i] / qv[i] for i in range(n)]
    for i in range(n):
        vals = [v for v in ev[max(0, i - 9):i + 1] if not math.isnan(v)]
        if vals:
            F["c17"][i] = max(vals)
        if i >= 199:
            F["trend"][i] = math.log(cl[i] / (sum(cl[i - 199:i + 1]) / 200.0))
        if i >= 20:
            F["mom20"][i] = cl[i] / cl[i - 20] - 1
        if i >= 3:
            F["rev3"][i] = cl[i] / cl[i - 3] - 1
        if i >= 6:
            F["taker7"][i] = sum(ratio[i - 6:i + 1]) / 7.0
        if i >= 19:
            F["hi20"][i] = cl[i] / max(cl[i - 19:i + 1]) - 1
        s = window_ok(ret, i, 20)
        if s is not None:
            m = sum(s) / 20.0
            F["vol20"][i] = math.sqrt(sum((v - m) ** 2 for v in s) / 19.0)
    return F


def welford_z(x):
    out, cnt, mean, m2 = [NAN] * len(x), 0, 0.0, 0.0
    for i, v in enumerate(x):
        if math.isnan(v):
            continue
        cnt += 1
        d = v - mean
        mean += d / cnt
        m2 += d * (v - mean)
        if cnt >= MINP:
            sd = math.sqrt(m2 / (cnt - 1))
            if sd > 0:
                out[i] = (v - mean) / sd
    return out


def coin_series(c):
    dates, cl, qv, tq = read(c)
    F = feats(cl, qv, tq)
    Z = {k: welford_z(F[k]) for k in SIGNS}
    n = len(cl)
    score = []
    for i in range(n):
        s = 0.0
        for k, sg in SIGNS.items():
            z = Z[k][i]
            s += 0.0 if math.isnan(z) else sg * z
        score.append(s / 7.0)
    rnext = [cl[i + 1] / cl[i] - 1 for i in range(n - 1)] + [NAN]
    c17 = [0.0 if math.isnan(v) else v for v in F["c17"]]
    return dates, np.array(score), np.array(rnext), np.array(c17)


def stat(pos, r):
    H = int(pos.sum())
    if H == 0:
        return NAN, 0, 0
    ntr = int(pos[0] == 1) + int(np.sum((pos[1:] == 1) & (pos[:-1] == 0)))
    ex = (r[pos == 1].sum() - FUND * H - COST * 2 * ntr) / H - r.mean()
    return ex, H, ntr


def evaluate(pos, r, seed):
    ex, H, ntr = stat(pos, r)
    n = len(r)
    ks = np.random.default_rng(seed).integers(30, n - 30 + 1, size=NSH)
    if H == 0:
        return {"excess": None, "hold_days": 0, "n_trades": 0, "p": None}
    ge = 0
    for k in ks:
        e2 = stat(np.roll(pos, int(k)), r)[0]
        if not math.isnan(e2) and e2 >= ex:
            ge += 1
    return {"excess": ex, "hold_days": H, "n_trades": ntr, "p": (1 + ge) / (1 + NSH)}


def main():
    S = {c: coin_series(c) for c in COINS}
    res = {}
    for var in ("main", "c17_control"):
        res[var] = {}
        for si, (sn, s0, s1) in enumerate(SEGS):
            rows = {}
            for ci, c in enumerate(COINS):
                dates, sc, rn, c17 = S[c]
                idx = [i for i, d in enumerate(dates) if s0 <= d <= s1 and not math.isnan(rn[i])]
                if len(idx) < 61:
                    continue
                sig = sc if var == "main" else c17
                th = THR if var == "main" else 0.5
                pos = (sig[idx] > th).astype(int)
                rows[c] = evaluate(pos, rn[idx], [18, si, ci])
            res[var][sn] = rows
    with open(os.path.join(ROOT, "backtest", "resultsC18", "C18.json"), encoding="utf-8") as fh:
        M = json.load(fh)
    cmp, maxd, nmis = [], 0.0, 0
    for var in res:
        for sn in res[var]:
            for c, v in res[var][sn].items():
                m = M[var][sn]["coins"][c]
                for k in ("excess", "hold_days", "n_trades", "p"):
                    a, b = v[k], m[k]
                    if a is None or b is None:
                        d = 0.0 if a is None and b is None else float("inf")
                    else:
                        d = abs(float(a) - float(b))
                    maxd = max(maxd, d)
                    if d > 1e-9:
                        nmis += 1
                        cmp.append({"var": var, "seg": sn, "coin": c, "key": k, "check": a, "main": b})
    out = {"max_abs_diff": maxd, "n_mismatch_gt_1e-9": nmis, "mismatches": cmp,
           "verdict": "同" if nmis == 0 else "不同", "check_results": res}
    with open(os.path.join(ROOT, "backtest", "resultsC18", "check.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("max_abs_diff", maxd, "mismatch", nmis, "verdict", out["verdict"])
    for x in cmp[:20]:
        print(x)


if __name__ == "__main__":
    main()

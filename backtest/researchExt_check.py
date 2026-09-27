# -*- coding: utf-8 -*-
"""PREREG外部三件 X2／X3 本體的【獨立路】查核。⛔ 不 import researchExt／research34／p4_features／research11／data。
 ① X3 事件完整性：自己讀月營收原始檔（快照 mops/revenue_hist ＋ 早年 revenue_hist），自己判「創紀錄」（嚴格 ＞ 之前所有有值月份、之前 ≥ 24 個月），
    自己算公告日（次月 10 日之後第一個交易日）⇒ 上市 gate3、T 在窗內且 T＋21 ≤ 窗尾 的件數 ＝ 主程式事件帳總數；抽 30 筆保留事件逐筆比對
 ② X3 報酬：researchM_check（csv 讀原始日線＋還原事件、自己還原）抽 20 筆 R_e、5 天 EW_20（母體 ＝ 上市 gate3）
 ③ X3 各段平均與月分群 CI：從 x3_events.csv.gz 自己算 ⇒ 與 summary.json 比
 ④ X2 因子：抽 12 個（檔, 換股月），自己從原始日線（成交金額、股數、發行股數、還原因子）重算 CGO（Grinblatt-Han 權重）與 TV100 ⇒ 與選股檔比
 ⑤ X2 權益：從 x2_equity.csv.gz 自己算窗內年化／回落（245）；0050 自己從原始檔還原 ⇒ 與 summary.json 比
輸出 backtest/resultsExt/check.json、check_detail.csv。"""
import os, sys, csv, json, math, glob
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchM_check as MC

OUT = os.path.expanduser("~/tw-p17/backtest/resultsExt")
SNAP = MC.SNAP
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data/mops/revenue_hist")
W0, W1 = "2017-03-02", "2026-08-24"


def cl(x, mon):
    x = np.asarray(x, float); n = len(x); m = x.mean(); d = x - m
    s = pd.Series(d).groupby(np.asarray(mon)).sum().to_numpy()
    se = math.sqrt(float((s ** 2).sum())) / n
    return m, m - 1.96 * se, m + 1.96 * se


def rev_table():
    rows = {}
    for f in sorted(glob.glob(os.path.join(EARLY, "*.csv"))) + sorted(glob.glob(os.path.join(SNAP, "mops", "revenue_hist", "*.csv"))):
        with open(f, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    v = float(r["當月營收"])
                except (TypeError, ValueError):
                    v = math.nan
                rows[(r["stock_id"], r["period"])] = v          # 後讀的覆蓋前讀的（快照優先、同檔同期取最後）
    return rows


def ann_day(cal, period):
    y, m = int(period[:4]), int(period[5:])
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    cut = "{:04d}-{:02d}-10".format(y2, m2)
    for i, d in enumerate(cal):
        if d > cut:
            return i
    return None


def raw_daily(sid):
    p = os.path.join(SNAP, "stocks", sid + ".csv"); out = {}
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["date"] in out:
                continue
            out[r["date"]] = {k: MC._num(r.get(k)) for k in ("open", "close", "volume", "amount", "shares")}
    return out


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    P = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    cal = MC.calendar(); pos = {d: i for i, d in enumerate(cal)}
    w0, w1 = pos[W0], pos[W1]; wE = w1 - 21
    res = {}; det = []
    from backtest import universe_gate as UG
    stocks = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks); lst = sorted(G.loc[G["market"] == "twse", "stock_id"])
    # ① 完整性
    R = rev_table()
    by = {}
    for (s, p), v in R.items():
        by.setdefault(s, []).append((p, v))
    ev = []
    ann = {}
    for s in lst:
        m = -math.inf; cnt = 0
        for p, v in sorted(by.get(s, [])):
            if not math.isfinite(v):
                continue
            if cnt >= 24 and v > m:
                if p not in ann:
                    ann[p] = ann_day(cal, p)
                T = ann[p]
                if T is not None and w0 <= T <= wE:
                    ev.append((s, T))
            m = max(m, v); cnt += 1
    ev_set = sorted(set(ev))
    main_total = sum(P["X3"]["事件帳（合併早年營收史）"].values())
    E = pd.read_csv(os.path.join(OUT, "x3_events.csv.gz"), dtype={"sid": str})
    kept = set(zip(E["sid"], E["T"]))
    res["①X3事件完整性"] = {"獨立路件數": len(ev_set), "主程式事件帳總數": main_total, "相同": len(ev_set) == main_total,
                         "保留事件都在獨立路集合內": bool(kept <= set(ev_set))}
    print("① X3 件數 獨立 {}／主程式 {}｜保留 ⊂ 獨立 {}".format(len(ev_set), main_total, res["①X3事件完整性"]["保留事件都在獨立路集合內"]), flush=True)
    # ② R_e／EW
    rng = np.random.default_rng(20260927)
    pick = []
    for i in rng.choice(len(E), 20, replace=False):
        r = E.iloc[int(i)]; T = int(r["T"])
        pick.append({"畫法": "X3", "sid": r["sid"], "T": cal[T], "T1": cal[T + 1], "T21": cal[T + 21], "R": float(r["R"]), "EW20": float(r["EW"])})
    ck = MC.run(pick, lst, n_days=5)
    res["②X3報酬"] = {"R_e最大差": ck["R_e最大差"], "基準最大差": ck["基準最大差"], "判": ck["判"]}
    print("② R_e 最大差 {:.1e}｜基準最大差 {:.1e}".format(ck["R_e最大差"], ck["基準最大差"]), flush=True)
    # ③ 各段
    md = 0.0
    for key, sub in (("判定格_T≥2025-01", E[E["期間"] == "判定（原文外）"]), ("原文期間內（描述）", E[E["期間"] == "原文期間內"]), ("全窗（描述）", E)):
        m, lo, hi = cl(sub["X"], [cal[int(t)][:7] for t in sub["T"]]); J = S["X3"][key]
        md = max(md, abs(m - J["平均"]), abs(lo - J["lo"]), abs(hi - J["hi"])); same_n = len(sub) == J["n"]
        det.append({"查核": "③", "段": key, "n": len(sub), "平均": m, "差": abs(m - J["平均"]), "n相同": same_n})
    res["③X3各段"] = {"最大差": md}
    print("③ X3 各段最大差 {:.1e}".format(md), flush=True)
    # ④ X2 因子
    pk = pd.read_csv(os.path.join(OUT, "x2_picks_monthly.csv.gz"), dtype={"sid": str})
    mfirst = {}
    for i, d in enumerate(cal):
        mfirst.setdefault(d[:7], i)
    dmax = 0.0; n4 = 0
    for i in rng.choice(len(pk), 12, replace=False):
        r = pk.iloc[int(i)]; s = r["sid"]; t = mfirst[r["換股月"]] - 1
        raw = raw_daily(s); _, adj = MC.stock(s)
        days = cal[t - 99:t + 1]
        sh = None; shs = []
        for d in cal[:t + 1]:
            v = raw.get(d, {}).get("shares", math.nan)
            if math.isfinite(v) and v > 0:
                sh = v
            if d in days:
                shs.append(sh)
        cs, Vs, Ps = [], [], []
        for d, sh_ in zip(days, shs):
            x = raw.get(d)
            ok = x is not None and all(math.isfinite(x[k]) and x[k] > 0 for k in ("open", "close"))
            f = MC.factor(adj, d)
            cs.append(x["close"] * f if ok else math.nan)
            if ok and math.isfinite(x["volume"]) and x["volume"] > 0:
                Vs.append(min(x["volume"] / sh_, 1.0)); Ps.append(x["amount"] / x["volume"] * f)
            else:
                Vs.append(0.0); Ps.append(math.nan)
        cv = [c for c in cs if math.isfinite(c)]
        rets = [cv[j] / cv[j - 1] - 1 for j in range(1, len(cv))]
        tv = float(np.std(rets, ddof=1))
        num = den = 0.0; cp = 1.0
        for nn in range(100):
            j = 99 - nn
            w = Vs[j] * cp
            if math.isfinite(Ps[j]) and w > 0:
                num += Ps[j] * w; den += w
            cp *= (1 - Vs[j])
        cgo = (cs[-1] - num / den) / cs[-1]
        d_ = max(abs(tv - r["TV100"]), abs(cgo - r["CGO"])); dmax = max(dmax, d_); n4 += 1
        det.append({"查核": "④", "sid": s, "月": r["換股月"], "TV100差": abs(tv - r["TV100"]), "CGO差": abs(cgo - r["CGO"])})
    res["④X2因子"] = {"抽": n4, "最大差": dmax}
    print("④ X2 因子 {} 筆最大差 {:.1e}".format(n4, dmax), flush=True)
    # ⑤ X2 權益與 0050
    EQ = pd.read_csv(os.path.join(OUT, "x2_equity.csv.gz"))
    def wm(x):
        x = np.asarray(x, float); y = len(x) / 245
        c = (x[-1] / x[0]) ** (1 / y) - 1; pk_ = np.maximum.accumulate(x)
        return c, float(((x - pk_) / pk_).min())
    d5 = 0.0
    for col in [c for c in EQ.columns if c.startswith("X2_")]:
        c_, m_ = wm(EQ[col].to_numpy()[w0:w1 + 1]); J = S["X2"][col[3:]]
        d5 = max(d5, abs(c_ - J["年化"]), abs(m_ - J["回落"]))
    px, adj = MC.stock("0050")
    cl50 = pd.Series([px[d][1] * MC.factor(adj, d) if d in px and math.isfinite(px[d][1]) else math.nan for d in cal]).ffill().to_numpy()
    c50, m50 = wm(cl50[w0:w1 + 1])
    d5 = max(d5, abs(c50 - S["0050同窗"]["年化"]), abs(m50 - S["0050同窗"]["回落"]))
    res["⑤X2權益與0050"] = {"最大差": d5}
    print("⑤ X2 權益與 0050 最大差 {:.1e}".format(d5), flush=True)
    pd.DataFrame(det).to_csv(os.path.join(OUT, "check_detail.csv"), index=False)
    allok = res["①X3事件完整性"]["相同"] and res["①X3事件完整性"]["保留事件都在獨立路集合內"] and ck["判"] and md < 1e-12 and dmax < 1e-9 and d5 < 1e-9
    res["全部通過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if allok else "⛔ 有不符", flush=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""加碼真頂出場：訊號落在「整段漲勢最高點」的哪裡（使用者 2026-10-12：「我指到最高點的真頂（不是中間頂喔）」）——回測線計算子代理，描述性、⛔ 不計 N。
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python <本檔>
 P 定義：從起漲點 t 起，到第一次收盤 ≤ 0.7 × [t, j] 最高收盤那天（結束日）為止，[t, 結束日] 最高收盤日 P；到資料尾沒回落 30% ⇒ 未完結（P ＝ 至今最高，另計）
 t ＝ 訊號當天的起漲點 t(d)（truetopT U2，進場日 tb 錨定）；另報 t ＝ t(tb) 敏感度
 價格 ＝ 引擎還原收盤（世界 closes；同 truetop 的 SA["c"]）；天數 ＝ 引擎日曆位置差
 1. 加碼部位提早賣筆（resultsAddOn/truetop/trades_T.csv.gz 提早賣＝True），主窗（ta ∈ 主窗），營量 A2/A1、營飆 A1/A2（唯一持股去重 (sid,tb)）
 2. d ＜ P 者：H ＝ [t, d] 最高收盤；d 之後第一次收盤 ＞ H 之前，最低收盤 ≤ 0.9H ⇒「先跌超過 10% 再創新高（中間頂）」；另版以賣價為基準
 3. 原持股（researchAddOn 全部持股，主窗 tb；營飆唯一持股）持有 [tb, min(xbar,n0)) 第一個 W2（W2a ∪ W2b）⇒ 次一有效開盤價，同 1、2
"""
import json, os, pickle, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa
from backtest import researchYL_truetopT as TTT               # noqa
from backtest import researchYL_flowexit as FX0               # noqa
from backtest import rerun17 as RR                            # noqa

OUT = "backtest/resultsAddOn/truetop/peak_check"; os.makedirs(OUT, exist_ok=True)
WN = "主"
CELLS = {"營量": ("A2", "A1"), "營飆": ("A1", "A2")}


def peak(c, t, n0):
    seg = c[t:n0]; rm = np.fmax.accumulate(seg)
    with np.errstate(invalid="ignore"):
        w = np.flatnonzero(seg <= rm * 0.7)
    done = len(w) > 0
    end = t + int(w[0]) if done else n0 - 1
    return t + int(np.nanargmax(c[t:end + 1])), end, done


def mid_top(c, t, d, P, base):
    """d < P：d 之後第一次收盤 > H 之前，最低收盤是否 ≤ 0.9 × base。⇒ (是否, 最深回落 ÷ base − 1, 創新高日 − d)"""
    H = np.nanmax(c[t:d + 1])
    j = d + 1 + int(np.flatnonzero(c[d + 1:P + 1] > H)[0])
    mn = np.nanmin(c[d + 1:j]) if j > d + 1 else np.inf
    return bool(mn <= 0.9 * base), (float(mn / base - 1) if np.isfinite(mn) else 0.0), int(j - d)


def q(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "q25": float(np.quantile(v, .25)), "q75": float(np.quantile(v, .75))}


def describe(df):
    out = {"筆數": int(len(df)), "未完結（到資料尾沒回落30%）": int((~df["完結"]).sum())}
    for lab, g in (("完結", df[df["完結"]]), ("未完結（P＝至今最高，暫定）", df[~df["完結"]])):
        if not len(g):
            out[lab] = {"n": 0}; continue
        dd = g["d−P"]; r = g["賣價÷cP"]; bef = g[dd < 0]
        o = {"n": int(len(g)), "d在P之前": float((dd < 0).mean()), "d在P當天": float((dd == 0).mean()), "d在P之後": float((dd > 0).mean()),
             "d−P（交易日）": q(dd), "賣價÷P收盤": q(r), "賣價距P不到10%（賣價≥0.9×cP）": float((r >= 0.9).mean()),
             "訊號後到P還漲（cP÷賣價−1，d在P之前者）": q(bef["cP÷賣價−1"]),
             "d在P之前：先跌>10%再創新高（中間頂，以H＝[t,d]最高收盤為準）": float(bef["中間頂H"].mean()) if len(bef) else None,
             "d在P之前：先跌>10%再創新高（以賣價為準）": float(bef["中間頂賣價"].mean()) if len(bef) else None,
             "d在P之前：沒跌10%就直接創新高": float(1 - bef["中間頂H"].mean()) if len(bef) else None,
             "d在P之前：訊號後最深回落（÷H−1，創新高前）": q(bef["回落H"]), "d在P之前：訊號到創新高（交易日）": q(bef["到新高天"]),
             "敏感度 t＝t(tb)：d在P之前／當天／之後": [float((g["d−P_te"] < 0).mean()), float((g["d−P_te"] == 0).mean()), float((g["d−P_te"] > 0).mean())],
             "敏感度 t＝t(tb)：P 與主版不同筆數": int((g["d−P_te"] != dd).sum())}
        out[lab] = o
    return out


def rowstats(c, t, te, d, sell, n0):
    P, end, done = peak(c, t, n0); P2, _, _ = peak(c, te, n0)
    cP = float(c[P]); r = {"t": t, "P": P, "結束日": end, "完結": done, "d−P": d - P, "d−P_te": d - P2, "cP": cP, "賣價": sell,
                           "賣價÷cP": sell / cP, "cP÷賣價−1": cP / sell - 1}
    if d < P:
        a, b, k = mid_top(c, t, d, P, np.nanmax(c[t:d + 1])); a2, _, _ = mid_top(c, t, d, P, sell)
        r.update({"中間頂H": a, "回落H": b, "到新高天": k, "中間頂賣價": a2})
    else:
        r.update({"中間頂H": np.nan, "回落H": np.nan, "到新高天": np.nan, "中間頂賣價": np.nan})
    return r


def main():
    W = pickle.load(open(os.path.join(AO.WORK, f"world_{WN}.pkl"), "rb")); cal = W["cal"]; n0 = len(cal)
    x0, y0 = W["segp"]["主窗"]
    TR = pd.read_csv("backtest/resultsAddOn/triggers.csv.gz", dtype={"sid": str}); TR = TR[TR["世界"] == WN]
    H = TR[TR["格"] == "A1"][["策略", "sid", "tb", "xbar"]].drop_duplicates(["策略", "sid", "tb"])
    TD = pd.read_csv("backtest/resultsAddOn/truetop/trades_T.csv.gz", dtype={"sid": str})
    sids = sorted(set(H["sid"]))
    ctx = {"mk": W["uni"], "cal": cal, "closes": W["closes"], "opens": W["opens"]}
    SA = {s: FX0.stock_arrays(ctx, s, n0) for s in sids}
    SWD, gi, mstar, sinfo = TTT.surge_world(sids, cal, print)
    RR.use_snapshot()
    gates = {}
    # ── 1／2 加碼提早賣 ──
    rows1 = []; mism = 0
    for sn, cells in CELLS.items():
        for c_ in cells:
            g = TD[(TD["策略"] == sn) & (TD["格"] == c_) & TD["提早賣"] & (TD["ta"] > x0) & (TD["ta"] <= y0)].drop_duplicates(["sid", "tb"])
            for r in g.itertuples(index=False):
                S = SA[r.sid]; c = S["c"]; d = int(r.訊號日); tb = int(r.tb)
                hi = min(int(H[(H["策略"] == sn) & (H["sid"] == r.sid) & (H["tb"] == tb)]["xbar"].iloc[0]), n0)
                tt, w2a, w2b, _, _ = TTT.signals_row(S, SWD.get(r.sid), gi, mstar, tb, hi)
                k = np.flatnonzero((w2a | w2b)[int(r.ta) - tb:])
                mism += int(not len(k) or int(r.ta) + int(k[0]) != d or int(tt[d - tb]) != int(r.訊號起漲點))
                te = int(tt[0])
                rr = rowstats(c, int(r.訊號起漲點), te, d, float(r.T_價), n0)
                rows1.append({"件": "1 加碼提早賣", "策略": sn, "格": c_, "sid": r.sid, "tb": tb, "ta": int(r.ta), "d": d, "訊號日期": str(cal[d].date()),
                              "訊號來源": r.訊號來源, "P日期": str(cal[rr["P"]].date()), **rr})
    gates["加碼提早賣：重算訊號日／起漲點 與 trades_T 不同筆數"] = mism
    # ── 3 原持股第一個 W2 ──
    rows3 = []; nh = {}
    for sn in CELLS:
        h = H[(H["策略"] == sn) & (H["tb"] > x0) & (H["tb"] <= y0)]
        nh[sn] = int(len(h)); nsig = 0; nnoopen = 0
        for r in h.itertuples(index=False):
            S = SA[r.sid]; c = S["c"]; tb = int(r.tb); hi = min(int(r.xbar), n0)
            tt, w2a, w2b, _, _ = TTT.signals_row(S, SWD.get(r.sid), gi, mstar, tb, hi)
            k = np.flatnonzero(w2a | w2b)
            if not len(k):
                continue
            nsig += 1; d = tb + int(k[0]); u = TTT.TT.nxo_of(S, n0)(d)
            if u is None:
                nnoopen += 1; continue
            rr = rowstats(c, int(tt[d - tb]), int(tt[0]), d, float(S["o"][u]), n0)
            rows3.append({"件": "3 原持股第一個W2", "策略": sn, "格": "", "sid": r.sid, "tb": tb, "ta": -1, "d": d, "訊號日期": str(cal[d].date()),
                          "訊號來源": "W2a" if w2a[k[0]] else "W2b", "P日期": str(cal[rr["P"]].date()), "賣出開盤日": u, "早於正式出場": bool(u <= int(r.xbar)), **rr})
        gates[f"{sn} 原持股（主窗、唯一）"] = {"持股": nh[sn], "持有中有W2": nsig, "比例": nsig / nh[sn] if nh[sn] else None, "訊號後無有效開盤": nnoopen}
    D1 = pd.DataFrame(rows1); D3 = pd.DataFrame(rows3)
    RES = {"說明": __doc__, "主窗": [str(cal[x0 + 1].date()), str(cal[y0].date())], "閘與筆數": gates, "1／2 加碼提早賣": {}, "3 原持股第一個W2": {}}
    for sn, cells in CELLS.items():
        for c_ in cells:
            RES["1／2 加碼提早賣"][f"{sn}·{c_}"] = describe(D1[(D1["策略"] == sn) & (D1["格"] == c_)])
        RES["3 原持股第一個W2"][sn] = describe(D3[D3["策略"] == sn])
        RES["3 原持股第一個W2"][sn + "（只算早於正式出場者）"] = describe(D3[(D3["策略"] == sn) & D3["早於正式出場"]])
    RES["4 既有研究"] = {
        "resultsYL_truetopT/summary_trigger.csv（營量／營飆 v1 全部 A 交易、T1＝W2、P*從 t(e) 起、K 棒數）": "T1 提早賣筆：賣出−真頂 中位 營量 −21、營飆 −9；賣在真頂以前 營量 74.7%、營飆 75.3%；離真頂5根內 20.9%／26.7%；賣價÷真頂−1 中位 −20.6%／−15.7%",
        "resultsSurge6/topwarn/A_events.csv（seq6 飆股事件、從t起版、±5日歸最近段頂）": "W2a 訊號日落在 P 附近 36.5%、H1 附近 6.2%、H2 以後 5.1%、都不在 52.2%；W2b 33.0%／9.3%／4.3%／51.5%；第一次出現離最近段頂中位 −5 日",
        "resultsSurge6/topwarn/Bp_signals.csv（起漲特徵≥5 進場、60日版）": "W2a 有出現 4.3%、真頂附近 26.7%、賣出日−真頂 中位 −12、之後又創新高 79.7%；W2b 9.0%、31.6%、−9、72.7%",
        "resultsSurge6/topjudge": "沒有報 W2 訊號距真頂（只有段頂特徵分數 T5），不引用"}
    json.dump(RES, open(os.path.join(OUT, "peak_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    pd.concat([D1, D3], ignore_index=True).to_csv(os.path.join(OUT, "peak_rows.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    # 精簡表
    T = []
    for key, blk in [(f"1 加碼·{k}", v) for k, v in RES["1／2 加碼提早賣"].items()] + [(f"3 原持股·{k}", v) for k, v in RES["3 原持股第一個W2"].items()]:
        o = blk.get("完結", {})
        if not o.get("n"):
            T.append({"群": key, "筆": blk["筆數"], "未完結": blk["未完結（到資料尾沒回落30%）"]}); continue
        T.append({"群": key, "筆": blk["筆數"], "未完結": blk["未完結（到資料尾沒回落30%）"], "完結n": o["n"],
                  "d在P前": o["d在P之前"], "d在P當天": o["d在P當天"], "d在P後": o["d在P之後"],
                  "d−P中位": o["d−P（交易日）"]["中位"], "d−P q25": o["d−P（交易日）"]["q25"], "d−P q75": o["d−P（交易日）"]["q75"],
                  "賣價÷cP中位": o["賣價÷P收盤"]["中位"], "÷cP q25": o["賣價÷P收盤"]["q25"], "÷cP q75": o["賣價÷P收盤"]["q75"],
                  "距P<10%": o["賣價距P不到10%（賣價≥0.9×cP）"], "訊號後還漲中位": o["訊號後到P還漲（cP÷賣價−1，d在P之前者）"].get("中位"),
                  "P前中間頂(H)": o["d在P之前：先跌>10%再創新高（中間頂，以H＝[t,d]最高收盤為準）"],
                  "P前中間頂(賣價)": o["d在P之前：先跌>10%再創新高（以賣價為準）"]})
    pd.DataFrame(T).to_csv(os.path.join(OUT, "peak_summary.csv"), index=False, encoding="utf-8-sig", float_format="%.4g")
    print(pd.DataFrame(T).to_string()); print(json.dumps(gates, ensure_ascii=False))
    for k, v in list(RES["1／2 加碼提早賣"].items()) + list(RES["3 原持股第一個W2"].items()):
        u = v.get("未完結（P＝至今最高，暫定）", {})
        if u.get("n"):
            print(k, "未完結", u["n"], "d<P", round(u["d在P之前"], 3), "÷cP", round(u["賣價÷P收盤"]["中位"], 3))
        f = v.get("完結", {})
        if f.get("n"):
            print(k, "敏感度", f["敏感度 t＝t(tb)：d在P之前／當天／之後"], f["敏感度 t＝t(tb)：P 與主版不同筆數"], "回落", f["d在P之前：訊號後最深回落（÷H−1，創新高前）"].get("中位"), "到新高天", f["d在P之前：訊號到創新高（交易日）"].get("中位"))


if __name__ == "__main__":
    main()

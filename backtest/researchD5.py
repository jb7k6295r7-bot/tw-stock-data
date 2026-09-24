# -*- coding: utf-8 -*-
"""PREREGD5（W1 ＋ 結構族停損：5 根碎形前低棘輪）seq2（sha d37706de4b549e17）——回測線落地。裁定線 seq122 §一 可開跑。

資料／W1／窗／0050 錨：與本批 A／F／C 同一份（main edc6f8002f 快照、resultsAFC/panel.csv.gz、gate3＋tradable＋delist on）
⇒ W1 同種子（102000..102199）直接讀 resultsAFC/w1_1000.csv（同資料同參數；⛔ 不重跑）
停損線：backtest/stop_fractal.py（fixture ①③⑤）；引擎：research11.simulate_mtm(stop_line=…)（fixture ②④、兩道閘門）

⭐ 落地讀法（⛔ 看任何結果前寫在這裡；交件逐條列出）：
 D1 每一個訊號列 (sid, entry_pos) 事先算停損線：e ＝ entry_pos 那一根有效 K 棒、x ＝ ≤ xpos 的最後一根有效 K 棒；
    逐根停損 ⇒ 對到日曆位置 [entry_pos, xpos]，非 K 棒日沿用前一根（停牌日）；entry_pos 不是有效 K 棒 ⇒ 該列無停損（計數）
 D2 停損出場＝ 稽核紀錄裡賣出日 t < 該部位排程出場日（引擎只會延後排程出場、不會提前）
 D3 假訊號臂：取 D5 同一顆種子的真實停損出場日 {t}；在「W1＋無真實停損」的路徑上，每個 t 日開盤出場【當下持股中隨機一檔】
    （排除當天本來就排程出場的、排除 D5 那天停掉的同一檔）；實作：自訂停損線物件，於 t 日由引擎即時寫出的稽核紀錄還原持股後抽一檔、令其停損線在 t−1 為 +∞
    ⇒ ⛔ 不改共用引擎；隨機種子 20260925＋r（r＝1…30）
 D4 同現金 × 0050：第 r 顆 D5 的每日曝險 e_t ＝ 持股市值／權益 ⇒ 對照臂日報酬 ＝ e_{t−1} × 0050 日報酬（現金 0%）（裁定線 seq119 §三②）
 D5 停損距離：初始 ＝ 1 − 初始停損／進場開盤；觸發時 ＝ 觸發當根停損／進場開盤 − 1（棘輪上移後可為正）
 D6 MA60 重疊：觸發根 d（收盤跌破那一根）起算 [d−5, d] 內有任一根還原收盤 < MA60（有效 K 棒上的 60 根均線）
 D7 被停後 20 日：出場日開盤 → 出場日＋19 的收盤（同一檔，還原、ffill）
 D8 W1 最大回落段內被停權重：2020-01-20 ～ 2020-03-19（PREREGI 的 W1 常見峰谷）內停損賣出額 ÷ 當日權益 的總和，200 顆取中位
"""
from __future__ import annotations
import os, sys, json, time, bisect
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
D = H2.D
from backtest import research11 as R, research13 as R13, researchp7 as P7, researchp12 as P12, p4_features as P4F, tradability as T
from backtest import stop_fractal as SF

OUT = "backtest/resultsD5"
AFC = "backtest/resultsAFC"
SEED0, NS, NF, FSEED = 102000, 200, 30, 20260925
COSTS = (0.00585, 0.008, 0.010, 0.015)
SEG = ("2020-01-20", "2020-03-19")
_S = {}


def _init(d):
    _S.update(d)


def sim(sig, seed, stop_line=None, cost=None, audit=None):
    R.COST = cost if cost is not None else P12.COST_STD
    try:
        return R.simulate_mtm(sig, P12.RULE, P12.N_C1, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                              return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero",
                              tradable=_S["trad"], delist=_S["dl"], audit=audit, stop_line=stop_line)
    finally:
        R.COST = P12.COST_STD


def wst(out):
    r = P12.win_read(out, _S["w0"], _S["w1"], _S["marks"]); return r["cagr"], r["mdd"]


def build_lines(sig, ohlc, idx_map, k=SF.K_SIDE):
    lines, kinds = {}, {}
    for s, e_pos, x_pos in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"]):
        bars = idx_map[s]; o, h, l, c = ohlc[s]
        j = bisect.bisect_left(bars, e_pos)
        if j >= len(bars) or bars[j] != e_pos:
            kinds[(s, e_pos)] = "進場日非 K 棒"; continue
        jx = bisect.bisect_right(bars, x_pos) - 1
        lv, kind = SF.stop_line(o, h, l, c, j, jx, k=k)
        arr = np.full(x_pos - e_pos + 1, np.nan)
        for b, v in zip(range(j, jx + 1), lv):
            arr[bars[b] - e_pos] = v
        arr = pd.Series(arr).ffill().to_numpy()
        lines[(s, int(e_pos))] = (int(e_pos), arr); kinds[(s, e_pos)] = kind
    return lines, kinds


class _Forced:
    """假訊號臂的停損線：只在指定日 t 對「當天抽中的那一檔」給一個極大的有限值（⇒ t−1 收盤必定「跌破」⇒ t 開盤出），其餘 NaN。"""
    def __init__(self, key, xpos, ctl):
        self.key, self.xpos, self.ctl = key, xpos, ctl; self.st0 = key[1]

    def __len__(self):
        return 10 ** 9

    def __getitem__(self, i):
        t = self.st0 + i + 1
        return 1e300 if self.ctl.chosen(t) == self.key else np.nan      # ⚠ 引擎先查 isfinite ⇒ ⛔ 不可用 +inf


class _Ctl:
    def __init__(self, days, avoid, audit, xpos_of, seed):
        self.days, self.avoid, self.audit, self.xpos_of = set(days), avoid, audit, xpos_of
        self.rng = np.random.default_rng(seed); self.cache = {}

    def chosen(self, t):
        if t not in self.days:
            return None
        if t not in self.cache:
            held = {}
            for a in self.audit:
                if a["t"] >= t:
                    continue
                if a["side"] == "buy":
                    held[a["sid"]] = a["t"]
                else:
                    held.pop(a["sid"], None)
            cand = sorted((s, e) for s, e in held.items() if self.xpos_of.get((s, e), -1) > t and s != self.avoid.get(t))
            self.cache[t] = cand[int(self.rng.integers(len(cand)))] if cand else None
        return self.cache[t]


def stop_exits(audit, xpos_of):
    buys = {}; ev = []
    for a in sorted(audit, key=lambda x: (x["t"], 0 if x["side"] == "sell" else 1)):
        if a["side"] == "buy":
            buys[a["sid"]] = (a["t"], a["px"])
        else:
            if a["sid"] in buys:
                e, p0 = buys.pop(a["sid"])
                if a["t"] < xpos_of.get((a["sid"], e), 10 ** 9):
                    ev.append({"sid": a["sid"], "entry": e, "t": a["t"], "px": a["px"], "p0": p0, "amt": a["amt"], "eq_prev": a["equity_prev"]})
    return ev


def _d5(seed):
    au = []
    out = sim(_S["sig"], seed, stop_line=_S["lines"], audit=au)
    c, m = wst(out)
    ev = stop_exits(au, _S["xpos_of"])
    w0, w1 = _S["w0"], _S["w1"]
    e = np.where(out["equity"] > 0, out["hold_val"] / out["equity"], 0.0)
    r50 = _S["c50"][w0 + 1:w1 + 1] / _S["c50"][w0:w1] - 1.0
    eqx = np.r_[1.0, np.cumprod(1 + e[w0:w1] * r50)]
    yrs = (w1 - w0) / 245
    cash_c, cash_m = float(eqx[-1] ** (1 / yrs) - 1), float((eqx / np.maximum.accumulate(eqx) - 1).min())
    trades = sum(1 for a in au if a["side"] == "buy")
    s0, s1 = _S["seg"]
    segw = sum(x["amt"] / x["eq_prev"] for x in ev if s0 <= x["t"] <= s1)
    return {"seed": seed, "cagr": c, "mdd": m, "cash_cagr": cash_c, "cash_mdd": cash_m, "n_stop": len(ev), "trades": trades,
            "avg_cash": float(1 - e[w0:w1 + 1].mean()), "seg_stop_w": segw,
            "ev": [(x["sid"], x["entry"], x["t"]) for x in ev]}


def _fake(args):
    seed, j, days, avoid = args
    au = []
    ctl = _Ctl(days, avoid, au, _S["xpos_of"], FSEED + j)
    lines = {k: (k[1], _Forced(k, v, ctl)) for k, v in _S["xpos_of"].items()}
    out = sim(_S["sig"], seed, stop_line=lines, audit=au)
    c, m = wst(out)
    return {"seed": seed, "j": j, "cagr": c, "mdd": m}


def _arm(args):
    seed, which = args
    out = sim(_S["sig"], seed, stop_line=_S["arms"][which]); c, m = wst(out)
    return {"seed": seed, "arm": which, "cagr": c, "mdd": m}


def passes(c, m, a, b):
    return bool(c >= a and m >= b and (c > a or m > b))


def main():
    global NS, NF
    t0 = time.time()
    if "--ns" in sys.argv:
        NS = int(sys.argv[sys.argv.index("--ns") + 1])
    if "--nf" in sys.argv:
        NF = int(sys.argv[sys.argv.index("--nf") + 1])
    os.makedirs(OUT, exist_ok=True)
    print("[ATR_MIN_BARS] research11.ATR_MIN_BARS ＝ {}".format(R.ATR_MIN_BARS), flush=True)
    cal = D.load_calendar(); ncal = len(cal)
    panel = P4F.read_panel(os.path.join(AFC, "panel.csv.gz"))
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens, ohlc, idx_map = {}, {}, {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float)
        v = np.flatnonzero(np.isfinite(c)); idx_map[s] = v.tolist()
        ohlc[s] = tuple(st.df[k].to_numpy(float)[v] for k in ("open", "high", "low", "close"))
    w0, w1 = P12.win_bounds(cal, "全窗"); marks = P12.month_marks(cal, w0, w1)
    c50 = closes["0050"]; c50_c, c50_m = R13.window_stats(c50 / c50[w0], w0, w1 + 1, w0, w1 + 1)
    assert abs(c50_c - 0.2402) < 5e-5 and abs(c50_m + 0.3396) < 5e-5, (c50_c, c50_m)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    xpos_of = {(s, int(e)): int(x) for s, e, x in zip(sig["sid"], sig["entry_pos"], sig["xpos_H120"])}
    lines, kinds = build_lines(sig, ohlc, idx_map)
    arms = {f"碎形k{k}": build_lines(sig, ohlc, idx_map, k=k)[0] for k in (1, 3)}
    kc = pd.Series(kinds).value_counts().to_dict()
    print("[停損線] {:,} 列｜初始類型 {}｜{:.0f}s".format(len(sig), kc, time.time() - t0), flush=True)
    seg = (int(cal.searchsorted(pd.Timestamp(SEG[0]))), int(cal.searchsorted(pd.Timestamp(SEG[1]))))
    S = {"closes": closes, "opens": opens, "ncal": ncal, "trad": trad, "dl": dl, "w0": w0, "w1": w1, "marks": marks, "sig": sig,
         "lines": lines, "xpos_of": xpos_of, "c50": c50, "seg": seg, "arms": arms}
    _init(S)
    W1 = pd.read_csv(os.path.join(AFC, "w1_1000.csv")).set_index("seed")
    with Pool(4, initializer=_init, initargs=(S,)) as pool:
        DR = pool.map(_d5, [SEED0 + r for r in range(NS)], chunksize=5)
        print("[D5] 200 顆完成｜{:.0f}s".format(time.time() - t0), flush=True)
        jobs = []
        for d in DR:
            days = sorted({t for _, _, t in d["ev"]}); avoid = {t: s for s, _, t in d["ev"]}
            jobs += [(d["seed"], j, days, avoid) for j in range(1, NF + 1)]
        FK = pd.DataFrame(pool.map(_fake, jobs, chunksize=20))
        print("[假訊號臂] 30×200 完成｜{:.0f}s".format(time.time() - t0), flush=True)
        AR = pd.DataFrame(pool.map(_arm, [(SEED0 + r, a) for a in arms for r in range(NS)], chunksize=10))
    X = pd.DataFrame([{k: v for k, v in d.items() if k != "ev"} for d in DR]).set_index("seed")
    X.to_csv(os.path.join(OUT, "d5_200.csv")); FK.to_csv(os.path.join(OUT, "fake_arm.csv"), index=False); AR.to_csv(os.path.join(OUT, "desc_arms.csv"), index=False)
    med_c, med_m = X["cagr"].median(), X["mdd"].median()
    ok = passes(med_c, med_m, c50_c, c50_m)
    fk = FK.groupby("j").agg(cagr=("cagr", "median"), mdd=("mdd", "median"))
    fk_pass = int(sum(passes(a, b, c50_c, c50_m) for a, b in zip(fk["cagr"], fk["mdd"])))
    cash_c, cash_m = X["cash_cagr"].median(), X["cash_mdd"].median()
    better_c, better_m = cash_c > med_c, cash_m > med_m
    stop_rate = X["n_stop"].sum() / X["trades"].sum()
    if not ok:
        res = "結果③（D5 沒判過）"
    else:
        subs = []
        if fk_pass >= 2:
            subs.append("②a")
        if better_c and better_m:
            subs.append("②c")
        elif better_c or better_m:
            subs.append("②b")
        res = "結果①" if not subs else "結果②（" + "、".join(subs) + "）"
    w1s = W1.loc[X.index]
    pc, pm = X["cagr"] - w1s["cagr"], X["mdd"] - w1s["mdd"]
    R_ = {"快照": H2.SHA, "ATR_MIN_BARS": int(R.ATR_MIN_BARS), "0050同窗": [c50_c, c50_m], "停損線初始類型": kc,
          "D5_200顆中位": [med_c, med_m], "判過": ok, "結果": res, "結果④觸發（出場率<5%）": bool(stop_rate < 0.05),
          "W1同資料200顆中位": [float(w1s["cagr"].median()), float(w1s["mdd"].median())],
          "配對差（含抽籤雜訊）": {"年化中位": float(pc.median()), "年化為正": int((pc > 0).sum()), "回落中位": float(pm.median()), "回落為正": int((pm > 0).sum())},
          "假訊號臂": {"判過": fk_pass, "次數": NF, "30次中位的中位": [float(fk["cagr"].median()), float(fk["mdd"].median())]},
          "同現金×0050（200顆中位）": [float(cash_c), float(cash_m)], "同現金在年化／回落比D5好": [bool(better_c), bool(better_m)],
          "停損出場率": float(stop_rate), "每顆停損次數中位": float(X["n_stop"].median()), "平均現金比例中位": float(X["avg_cash"].median()),
          "W1最大回落段內被停權重（中位）": float(X["seg_stop_w"].median()),
          "描述臂": {a: [float(AR[AR.arm == a]["cagr"].median()), float(AR[AR.arm == a]["mdd"].median())] for a in arms}}
    json.dump(R_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # 逐筆停損事件（D6／D7／D5 距離用）
    evs = pd.DataFrame([(d["seed"], s, e, t) for d in DR for s, e, t in d["ev"]], columns=["seed", "sid", "entry", "t"])
    evs.to_csv(os.path.join(OUT, "stop_events.csv"), index=False)
    print(json.dumps(R_, ensure_ascii=False, indent=1, default=float))
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()

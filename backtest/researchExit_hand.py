# -*- coding: utf-8 -*-
"""PREREG出場訊號 硬性查核②：抽 20 筆（hand_pick20.csv，本體以種子 20260926 從 6 格保留事件抽）用【原始價＋還原因子】手算。
⛔ 不 import researchExit／exit_signal／data.py／stop_fractal／tradability：直接讀快照 data/stocks/{sid}.csv 與 data/adj/{sid}.csv（csv 模組）。

每筆驗：
 ① 還原因子兩條路：路二（判定）＝ 第一個事件日 ＞ d 那列的 cum_factor；路一（旁證）＝ Π factor（事件日 ＞ d）自乘
    ⚠ cum_factor 只存到 8 位小數 ⇒ 兩路差 ~1e-8（相對），R 為同一檔兩價之比、差會相消
 ② 訊號日 T：至 T 有效 K 棒 ≥ 80 根；線（甲 ＝ 右 5 根走完的最近擺動低點的還原 low，暴力找；乙丙 ＝ 最近 20／60 根還原收盤的 sum／n）；
    close_T ＜ 線_T 且 close_{T−1} ≥ 線_{T−1}（甲的 T−1 比 Y_T）；線值與逐筆檔的 line 相對差
 ③ 賣出日 s：T 之後第一個「有成交、開盤非缺、開盤 ≠ 跌停價」的交易日（跌停價獨立寫：前收 × 0.9 向上取跳動；除權息日不判），被跳過的日子逐筆列出；
    賣出價 ＝ 原始 open(s) × F(s)
 ④ 終點：s＋(H−1)（交易日曆）當天或之前最後一個有成交日的原始 close × F；R ＝ 終點價 ÷ 賣出價 − 1
"""
import os, csv, json

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
DATA = os.path.expanduser("~/h2data/{}/data".format(SHA))
OUT = os.path.expanduser("~/tw-p17/backtest/resultsExit")


def pf(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def limit_down(pc):
    """獨立寫法：跌停價 ＝ 前收 × 0.9 向上取到該價位的最小跳動（2015-06-01 後 10%；本窗 2017 起）。"""
    raw = pc * 0.9
    tick = 0.01 if raw < 10 else 0.05 if raw < 50 else 0.1 if raw < 100 else 0.5 if raw < 500 else 1.0 if raw < 1000 else 5.0
    import math
    return round(math.ceil(raw / tick - 1e-9) * tick, 4)


MODE = "cum"


def main(mode="cum"):
    global MODE
    MODE = mode
    cal = sorted(r["date"] for r in csv.DictReader(open(os.path.join(DATA, "meta", "calendar_twse.csv"), encoding="utf-8")))
    pos = {d: i for i, d in enumerate(cal)}
    picks = list(csv.DictReader(open(os.path.join(OUT, "hand_pick20.csv"), encoding="utf-8")))
    out = []; mx = {"line": 0.0, "P_s": 0.0, "P_end": 0.0, "R": 0.0}; nbad = 0
    for p in picks:
        sid, g, H, T = p["sid"], p["g"], int(p["H"]), p["T_date"]
        raw = {}
        for r in csv.DictReader(open(os.path.join(DATA, "stocks", sid + ".csv"), encoding="utf-8")):
            if r["date"] in raw:
                continue
            v = [pf(r[k]) for k in ("open", "high", "low", "close")]
            if any(x is not None and x <= 0 for x in v):          # 任一價 ≤ 0 ⇒ 整根視為缺（資料約定）
                v = [None] * 4
            raw[r["date"]] = v
        adj = []
        ap = os.path.join(DATA, "adj", sid + ".csv")
        if os.path.exists(ap):
            adj = [(r["date"], float(r["factor"]), float(r["cum_factor"])) for r in csv.DictReader(open(ap, encoding="utf-8"))]
        def F_prod(d):                        # 路一：factor 欄自乘（事件日 > d）
            f = 1.0
            for ed, fac, _ in adj:
                if ed > d:
                    f *= fac
            return f
        def F_cum(d):                         # 路二：第一個事件日 > d 那列的 cum_factor（資料約定；8 位小數）
            for ed, _, cf in sorted(adj):
                if ed > d:
                    return cf
            return 1.0
        F = F_cum if MODE == "cum" else F_prod
        vd = [d for d in cal if d in raw and raw[d][3] is not None]       # 有效 K 棒 ＝ 收盤非缺
        iT = vd.index(T)
        closes = [raw[d][3] * F(d) for d in vd[:iT + 1]]
        lows = [raw[d][2] * F(d) for d in vd[:iT + 1]]
        ok = {"≥80根": iT + 1 >= 80}
        if g == "甲":
            def Y_at(i):
                sw = [s for s in range(5, i - 4) if lows[s] < min(lows[s - 5:s]) and lows[s] < min(lows[s + 1:s + 6])]
                return lows[sw[-1]] if sw else None
            L = Y_at(iT); Lp = L
        else:
            n = 20 if g == "乙" else 60
            L = sum(closes[iT - n + 1:iT + 1]) / n; Lp = sum(closes[iT - n:iT]) / n
        ok["訊號成立"] = closes[iT] < L and closes[iT - 1] >= Lp
        dl = abs(L / float(p["line"]) - 1)
        # 賣出
        t = pos[T] + 1; skipped = []
        while True:
            d = cal[t]
            if d in raw and raw[d][3] is not None and raw[d][0] is not None:
                prev = max(x for x in vd if x < d); pc = raw[prev][3]
                ld = limit_down(pc) if not any(prev < ed <= d for ed, _, _ in adj) else None
                if ld is not None and abs(raw[d][0] - ld) < 1e-6:
                    skipped.append((d, "開盤＝跌停價（前收 {}、跌停 {}）".format(pc, ld))); t += 1; continue
                break
            skipped.append((d, "停牌" if (d not in raw or raw[d][3] is None) else "開盤缺")); t += 1
        s = cal[t]
        Ps = raw[s][0] * F(s)
        x = pos[s] + H - 1
        je = max(d for d in vd if pos[d] <= x)
        Pe = raw[je][3] * F(je)
        R = Pe / Ps - 1
        ok["賣出日同"] = s == p["s_date"]; ok["終點日同"] = je == p["end_date"]
        d = {"sid": sid, "訊號": g, "H": H, "T": T, "線_手算": L, "線相對差": dl, "close_T": closes[iT], "close_T−1": closes[iT - 1],
             "s": s, "跳過": skipped, "賣出價_手算": Ps, "賣出價差": abs(Ps / float(p["P_s"]) - 1), "終點日": je,
             "終點價_手算": Pe, "終點價差": abs(Pe / float(p["P_end"]) - 1), "R_手算": R, "R差": abs(R - float(p["R"])), **ok}
        mx["line"] = max(mx["line"], dl); mx["P_s"] = max(mx["P_s"], d["賣出價差"]); mx["P_end"] = max(mx["P_end"], d["終點價差"]); mx["R"] = max(mx["R"], d["R差"])
        good = all(ok.values()) and dl < 1e-9 and d["賣出價差"] < 1e-9 and d["終點價差"] < 1e-9 and d["R差"] < 1e-9
        d["判"] = "✅" if good else "⛔"; nbad += int(not good)
        out.append(d)
        print("{} {} H{} T {}｜線 {:.4f}（差 {:.1e}）close {:.4f}／前 {:.4f}｜s {}{}｜賣 {:.4f} 終 {} {:.4f}｜R {:+.4f}%（差 {:.1e}）｜{}".format(
            sid, g, H, T, L, dl, closes[iT], closes[iT - 1], s, "（跳過 {}）".format(len(skipped)) if skipped else "", Ps, je, Pe, R * 100, d["R差"], d["判"]))
    res = {"筆數": len(out), "不符": nbad, "最大相對差": mx, "逐筆": out, "判": "✅ 20 筆全符" if nbad == 0 else "⛔ 有 {} 筆不符".format(nbad)}
    return res


def run():
    """路二（cum_factor）⇒ 判定：差 < 1e-9；路一（factor 自乘）⇒ 只報差（cum_factor 只存 8 位小數 ⇒ 預期 ~1e-8 級，R 的差會相消）。"""
    a = main("cum")
    print("—— 路一：factor 自乘（只報差）")
    b = main("prod")
    res = {"主（路二 cum_factor 欄）": a, "旁證（路一 factor 自乘）": {k: b[k] for k in ("筆數", "最大相對差")},
           "判": a["判"], "最大相對差": a["最大相對差"], "路一最大相對差": b["最大相對差"]}
    json.dump(res, open(os.path.join(OUT, "check_hand20.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(a["判"], "｜路二最大相對差", {k: "{:.1e}".format(v) for k, v in a["最大相對差"].items()},
          "｜路一（factor 自乘）最大相對差", {k: "{:.1e}".format(v) for k, v in b["最大相對差"].items()})


if __name__ == "__main__":
    run()

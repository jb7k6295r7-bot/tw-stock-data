# -*- coding: utf-8 -*-
"""美股參考組「每年買去年 S&P 500 漲最多那檔」的分散版本（描述）——使用者問「我又不會重壓，依照這個有更優化的方式嗎？」。
性質：⛔ 看過段（2016 年後 IG 原文已公開）⇒ 所有變體只能描述、⛔ 不能當驗證、⛔ 不計 N、⛔ 不判；10 個變體一起看本身就是多重比較。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSTopPrev_var

重用（⛔ 不另寫一套）：researchUSTopPrev 的 world()（窗、資料尾、換股日 e）、rank_year()（年換排名 ⇒ 名單逐位元同主檔）、
run()（逐日引擎：開盤賣舊買新、0.05% 來回、斷點／下市結清、現金 DTB3 計息）、summarize()（年化、回落、回本年數）、
drop_best_bench()、dtb3_daily()；排名報酬 ＝ researchUSC.period_ret（同主檔 T2：錨點 5 根、不跨斷點、母體 m5 point-in-time）。

變體（全部窗 ＝ [2016-12-30 收盤, 資料尾]，第一個換股日 2017-01-03，成本 0.05% 來回同主檔 T3）
 A 年換、前 N 名等權（N ＝ 1、3、5、10、20）：每年第一個交易日開盤等權買、年中不再平衡（N＝1、3 應與主檔逐位元同，當閘）。
 H 半年換（每年 1 月、7 月第一個交易日開盤），排名 ＝ 換股日前一交易日 s 對「12 個月前同一換股日前一交易日 b0」的 period_ret
   （1 月換股 ⇒ 與年換同名單；7 月換股 ⇒ 上年 6 月底 → 本年 6 月底），N ＝ 5、10，等權、兩次換股之間不再平衡。
 M 搭配大盤：前 5 名等權佔 w（20%／30%／50%）＋ 1−w 放 ^SP500TR，每年第一個交易日再平衡。
   股票腿 ＝ A 的 N＝5 逐日路徑（開盤→開盤，成本已含）；大盤腿 ＝ ^SP500TR 收盤（換股日前一交易日收盤 → 下一換股日前一交易日收盤，
   年與年首尾相接、無重疊無缺口）；兩腿在「換股日前一收盤～換股日開盤」之間再平衡，大盤腿成交額 × 0.025%（來回 0.05% 的單邊）。
   ⚠ ^SP500TR 是指數、不可直接買，未扣 ETF 管理費（約 0.03～0.09%／年）。
 對照：^SP500TR（同主檔）、USREG-C3s 主臂（resultsUSC/C3s/summary.json；⚠ 其窗尾 2026-09-30，比本件資料尾 2026-10-05 短 3 個交易日；
   回本、拿掉最好一年、2026 占比由 repo 外逐日權益 ~/us_work/c/c3s/c3s_eq_trades.pkl 唯讀算出，最大單一持股取 summary「b 集中度」）。

每變體報：年化、最大回落、回本年數、年化÷|回落|、拿掉最好一年後年化（該曆年權益持平、之後整段除以 1＋r，同主檔 T7）、最差一年、
勝 ^SP500TR 的年數（曆年，策略「開盤→開盤」對基準「收盤→收盤」，同主檔逐年表；2026 ＝ 至資料尾）、
2026 貢獻占比 ＝ (權益_尾 − 權益_2026年初) ÷ (權益_尾 − 1)、
最大單一持股占總獲利 ＝ 同一代號全窗各次持有損益（進場金額 → 出場所得，扣成本）加總 ÷ (權益_尾 − 1)；混合版股票腿損益按當年權重換算。
私有資料：resultsUSC/topprev/var/ 只放彙總與代號；逐日權益寫 ~/us_work/topprev/var/（repo 外）並列 sha。
存活者偏差（同 K10）：S&P 500 有 18 檔不在母體 ⇒ 偏樂觀。
"""
from __future__ import annotations

import csv
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K               # noqa: E402
from backtest import researchUSTopPrev as TP        # noqa: E402

OUTD = os.path.join(TP.OUTD, "var")
WORKD = os.path.join(TP.WORKD, "var")
NA = (1, 3, 5, 10, 20)
NH = (5, 10)
MIXW = (0.2, 0.3, 0.5)
NMIX = 5
C3S_SUM = os.path.join(K.OUT, "C3s", "summary.json")
C3S_PKL = os.path.expanduser("~/us_work/c/c3s/c3s_eq_trades.pkl")
NOTE = ("⛔ 看過段（2016 年後 IG 原文已公開）：全部變體只描述、不能當驗證、不計 N、不判；"
        "10 個變體（A×5、H×2、M×3）一起看＝多重比較，挑最好看的那個會高估")


def rank_at(W, s, b0):
    """同主檔 T2：母體 m5[s]、period_ret(b0, s)、遞減、同分依代號序。"""
    r = K.period_ret(b0, s)
    el = np.flatnonzero(W["m5"][s] & np.isfinite(r))
    return [int(x) for x in el[np.lexsort((el, -r[el]))]]


def half_dates(cal, tail):
    """1、7 月第一個交易日（鍵 ＝ 年＋0.0／年＋0.5）。"""
    eh = {}
    for y in sorted(set(cal.year)):
        for m, k in ((1, 0.0), (7, 0.5)):
            ix = np.flatnonzero((cal.year == y) & (cal.month == m))
            if len(ix) and ix[0] <= tail:
                eh[y + k] = int(ix[0])
    return eh


def cal_starts(yst, years, key=lambda y: y):
    return {y: float(yst[key(y)]) for y in years}


def cal_years(eq, S, years, tail):
    out = {}
    for i, y in enumerate(years):
        nx = S[years[i + 1]] if i + 1 < len(years) else eq[tail]
        out[y] = float(nx / S[y] - 1)
    return out


def flatten(eq, S, yb, e, years, tail):
    """拿掉 yb 年：該曆年權益持平於年初值、之後整段除以 1＋r（同主檔 drop_best_arm 的結果）。"""
    t0 = e[yb]
    nxt = yb + 1 if (yb + 1) in S else None
    t1 = (e[nxt] - 1) if nxt else tail
    eq2 = eq.copy(); eq2[t0:t1 + 1] = S[yb]
    if nxt:
        eq2[t1 + 1:tail + 1] = eq[t1 + 1:tail + 1] * S[yb] / S[nxt]
    return eq2


def attrib(W, cal, ek, picks, weights, yst, ev, tail, scale=None):
    """逐次持有損益（同 run 的出場規則）⇒ 依代號加總。scale：{鍵: 換算係數}（混合版用）。"""
    O, CF, last = W["O"], W["CF"], W["last"]
    keys = sorted(picks); out = {}
    evx = {(x["年"], x["代號"]): x for x in ev if x["事件"] in ("斷點", "下市")}
    for i, k in enumerate(keys):
        t0 = ek[k]; nx = ek[keys[i + 1]] if i + 1 < len(keys) else None
        for j, w in zip(picks[k], weights[k]):
            amt = yst[k] * w; u = amt / O[t0, j]; tk = str(W["tick"][j])
            x = evx.get((k, tk))
            if x is not None:
                t = int(cal.get_loc(pd.Timestamp(x["日"])))
                px = CF[t - 1, j] if x["事件"] == "斷點" else CF[last[j], j]; c = amt * TP.COST
            elif nx is not None:
                px = O[nx, j]; c = amt * TP.COST
            else:
                px = CF[tail, j]; c = 0.0
            p = (u * px - c - amt) * (1.0 if scale is None else scale[k])
            out[tk] = out.get(tk, 0.0) + float(p)
    return out


def describe(name, eq, S, years, e, a, tail, cal, byr, pnl=None, extra=None):
    m = TP.summarize(eq, a, tail, cal)
    yr = cal_years(eq, S, years, tail)
    yb = max(yr, key=lambda y: yr[y])
    db = TP.summarize(flatten(eq, S, yb, e, years, tail), a, tail, cal)
    tot = float(eq[tail] - 1)
    wy = min(yr, key=lambda y: yr[y])
    d = {"變體": name, "年化": m["年化"], "最大回落": m["回落"], "回本年數": m["回本年數"], "年化÷|回落|": m["比值"],
         "高點日": m["高點日"], "谷底日": m["谷底日"], "回本日": m["回本日"], "期末倍數": m["期末倍數"],
         "拿掉最好一年": {"年": int(yb), "該年報酬": yr[yb], "年化": db["年化"], "最大回落": db["回落"], "年化÷|回落|": db["比值"]},
         "最差一年": {"年": int(wy), "報酬": yr[wy]},
         "勝^SP500TR年數": int(sum(yr[y] > byr[y] for y in years)), "年數": len(years),
         "勝的年": [int(y) for y in years if yr[y] > byr[y]],
         "2026貢獻占比": float((eq[tail] - S[2026]) / tot) if tot > 0 else None,
         "逐年": yr}
    if pnl is not None:
        top = sorted(pnl.items(), key=lambda kv: -kv[1])
        d["最大單一持股"] = {"代號": top[0][0], "占總獲利": top[0][1] / tot}
        d["前5檔占總獲利"] = [(k, v / tot) for k, v in top[:5]]
        d["持有過檔數"] = len(pnl)
        d["損益恆等式殘差（現金利息等）"] = float(tot - sum(pnl.values()))
    if extra:
        d.update(extra)
    return d


def main():
    os.makedirs(OUTD, exist_ok=True); os.makedirs(WORKD, exist_ok=True)
    R, W, cal, tail, e = TP.world()
    years = [y for y in sorted(e) if y >= TP.Y0 and e[y] <= tail]
    a = e[TP.Y0] - 1
    g, gsrc = TP.dtb3_daily(cal)
    tk = W["tick"]
    gates = {}

    # 基準
    B = R["B"]
    beq = np.full(len(cal), np.nan); beq[a:tail + 1] = B[a:tail + 1] / B[a]
    byr = {}
    for y in years:
        t1 = (e[y + 1] - 1) if (y + 1) in e and e[y + 1] <= tail else tail
        byr[y] = float(B[t1] / B[e[y] - 1] - 1)

    # A 年換
    rk = {y: TP.rank_year(R, W, cal, e, y)["order"] for y in years}
    for y in years:                                              # 閘：rank_at 對年換 ＝ rank_year
        assert rank_at(W, e[y] - 1, e[y - 1] - 1) == rk[y], y
    gates["rank_at＝rank_year（年換逐年）"] = True
    arms = {}; daily = {}; picks_tab = []
    for n in NA:
        P = {y: rk[y][:n] for y in years}; Wt = {y: [1 / n] * n for y in years}
        eq, yr, ev, opn, yst = TP.run(W, cal, e, tail, P, Wt, stop=None, cash_g=g)
        S = cal_starts(yst, years)
        pnl = attrib(W, cal, e, P, Wt, yst, ev, tail)
        k = "A 年換 前%d名等權" % n
        arms[k] = describe(k, eq, S, years, e, a, tail, cal, byr, pnl, {"事件": ev, "窗尾持股": opn})
        daily[k] = eq
        if n == NMIX:
            A5 = (eq, yst, P, Wt, ev)
        for y in years:
            picks_tab.append({"變體": k, "換股日": str(cal[e[y]].date()), "名單": " ".join(str(tk[j]) for j in P[y])})
    # 閘：N＝1、3 與主檔逐位元
    tpj = json.load(open(os.path.join(TP.OUTD, "topprev.json"), encoding="utf-8"))["全窗"]
    for n, kk in ((1, "第1名"), (3, "前3名等權")):
        gates["A N=%d 年化與主檔差" % n] = abs(arms["A 年換 前%d名等權" % n]["年化"] - tpj[kk]["年化"])
        gates["A N=%d 回落與主檔差" % n] = abs(arms["A 年換 前%d名等權" % n]["最大回落"] - tpj[kk]["回落"])
        gates["A N=%d 拿掉最好一年年化與主檔差（flatten vs 重跑）" % n] = abs(
            arms["A 年換 前%d名等權" % n]["拿掉最好一年"]["年化"] - tpj[kk]["拿掉最好一年"]["年化"])

    # H 半年換
    eh = half_dates(cal, tail)
    hk = [k for k in sorted(eh) if k >= TP.Y0]
    rh = {}
    for k in hk:
        s = eh[k] - 1; b0 = eh[k - 1] - 1
        assert cal[s].year * 12 + cal[s].month - (cal[b0].year * 12 + cal[b0].month) == 12, k
        rh[k] = rank_at(W, s, b0)
        if k == int(k):
            assert rh[k] == rk[int(k)], k
    gates["半年換 1 月名單＝年換"] = True
    for n in NH:
        P = {k: rh[k][:n] for k in hk}; Wt = {k: [1 / n] * n for k in hk}
        eq, yr, ev, opn, yst = TP.run(W, cal, eh, tail, P, Wt, stop=None, cash_g=g)
        S = cal_starts(yst, years, key=lambda y: float(y))
        pnl = attrib(W, cal, eh, P, Wt, yst, ev, tail)
        name = "H 半年換 前%d名等權" % n
        arms[name] = describe(name, eq, S, years, e, a, tail, cal, byr, pnl,
                              {"事件": ev, "窗尾持股": opn, "逐半年": {str(k): float(v) for k, v in yr.items()},
                               "7月換股與1月名單重疊率_平均": float(np.mean([len(set(rh[k][:n]) & set(rh[k - 0.5][:n])) / n
                                                                    for k in hk if k != int(k)]))})
        daily[name] = eq
        for k in hk:
            picks_tab.append({"變體": name, "換股日": str(cal[eh[k]].date()), "名單": " ".join(str(tk[j]) for j in P[k])})

    # M 搭配大盤
    eqs, ysts, P5, W5, ev5 = A5
    for w in MIXW:
        eq = np.full(len(cal), np.nan); eq[a] = 1.0; V = 1.0; S = {}; scale = {}; bcost = 0.0
        for i, y in enumerate(years):
            t0 = e[y]; nx = years[i + 1] if i + 1 < len(years) else None
            t1 = (e[nx] - 1) if nx else tail
            S[y] = V; scale[y] = V * w / ysts[y]
            eq[t0:t1 + 1] = V * (w * eqs[t0:t1 + 1] / ysts[y] + (1 - w) * B[t0:t1 + 1] / B[t0 - 1])
            if nx:
                Vs = V * w * ysts[nx] / ysts[y]; Vb = V * (1 - w) * B[t1] / B[t0 - 1]
                c = abs((Vs + Vb) * (1 - w) - Vb) * TP.COST / 2
                bcost += c; V = Vs + Vb - c
        pnl = attrib(W, cal, e, P5, W5, ysts, ev5, tail, scale=scale)
        name = "M 前5名%d%%＋^SP500TR %d%%" % (round(w * 100), round(100 - w * 100))
        d = describe(name, eq, S, years, e, a, tail, cal, byr, pnl, {"大盤腿再平衡成本合計（權益單位）": bcost})
        bt = float(eq[tail] - 1)
        d["^SP500TR腿占總獲利"] = float((bt - sum(pnl.values())) / bt)
        d.pop("損益恆等式殘差（現金利息等）", None)
        arms[name] = d; daily[name] = eq
    # 閘：w＝1 退化 ＝ A5、w＝0 退化 ＝ 基準（不輸出，只核）
    for w, ref in ((1.0, eqs), (0.0, None)):
        eq = np.full(len(cal), np.nan); eq[a] = 1.0; V = 1.0
        for i, y in enumerate(years):
            t0 = e[y]; nx = years[i + 1] if i + 1 < len(years) else None
            t1 = (e[nx] - 1) if nx else tail
            eq[t0:t1 + 1] = V * (w * eqs[t0:t1 + 1] / ysts[y] + (1 - w) * B[t0:t1 + 1] / B[t0 - 1])
            if nx:
                Vs = V * w * ysts[nx] / ysts[y]; Vb = V * (1 - w) * B[t1] / B[t0 - 1]
                V = Vs + Vb - abs((Vs + Vb) * (1 - w) - Vb) * TP.COST / 2
        r = ref if ref is not None else beq
        gates["混合退化 w=%.0f 最大相對差" % w] = float(np.nanmax(np.abs(eq[a:tail + 1] / r[a:tail + 1] - 1)))

    # 對照：^SP500TR
    Sb = {y: float(beq[e[y] - 1]) for y in years}
    bm = describe("^SP500TR", beq, Sb, years, e, a, tail, cal, byr)
    dbb = TP.drop_best_bench(beq, byr, e, a, tail, cal)
    gates["基準拿掉最好一年 flatten vs drop_best_bench 年化差"] = abs(bm["拿掉最好一年"]["年化"] - dbb["年化"])
    bm["最大單一持股"] = {"代號": "（指數）", "占總獲利": None}
    bm["勝^SP500TR年數"] = "—"; bm["勝的年"] = []                # 自己對自己（浮點差會誤算 1 年）
    arms["^SP500TR"] = bm

    # 對照：C3s
    cs = json.load(open(C3S_SUM, encoding="utf-8"))
    ca = cs["a 看過段"]
    with open(C3S_PKL, "rb") as f:
        ceq = np.asarray(pickle.load(f)["eq"], float)
    w1 = int(cal.searchsorted(pd.Timestamp(cs["窗"][1])))
    assert str(cal[w1].date()) == cs["窗"][1] and len(ceq) == len(cal)
    Sc = {y: float(ceq[e[y] - 1]) for y in years}
    cyr = cal_years(ceq, Sc, years, w1)
    bwin = {y: (byr[y] if y < 2026 else float(B[w1] / B[e[y] - 1] - 1)) for y in years}
    gates["C3s 逐年與 summary 最大差"] = max(abs(cyr[y] - ca["逐年"][str(y) if y < 2026 else "2026（1～9 月）"]["策略"]) for y in years)
    c3 = describe("USREG-C3s 主臂（窗尾 2026-09-30）", ceq / ceq[a], {y: v / ceq[a] for y, v in Sc.items()}, years, e, a, w1, cal, bwin)
    gates["C3s 年化與 summary 差"] = abs(c3["年化"] - ca["年化"])
    gates["C3s 回落與 summary 差"] = abs(c3["最大回落"] - ca["回落"])
    t10 = cs["b 集中度"]["前10檔"]
    c3["最大單一持股"] = {"代號": t10[0]["代號"], "占總獲利": t10[0]["占總獲利"]}
    c3["前5檔占總獲利"] = [(x["代號"], x["占總獲利"]) for x in t10[:5]]
    c3["說明"] = "年化、回落取自 summary.json（已核等於逐日權益）；回本、拿掉最好一年、2026 占比由 repo 外逐日權益唯讀算；勝年數以同窗 ^SP500TR（2026 至 09-30）比"
    arms["USREG-C3s 主臂"] = c3

    # 輸出
    dpath = os.path.join(WORKD, "equity_daily_var.csv")
    pd.DataFrame({k: v[a:tail + 1] for k, v in daily.items()} | {"^SP500TR": beq[a:tail + 1]}, index=cal[a:tail + 1]).to_csv(dpath)
    order = list(arms)
    out = {"件": "美股參考組「每年買去年 S&P 500 漲最多那檔」分散版本（描述）", "性質": NOTE, "問": "我又不會重壓，依照這個有更優化的方式嗎？",
           "重用": "researchUSTopPrev（world、rank_year、run、summarize、drop_best_bench、dtb3_daily）；researchUSC.period_ret",
           "附註": [K.SURV, "^SP500TR 為指數、不可直接買，未扣 ETF 管理費", "混合版大盤腿再平衡成交額扣 0.025%（單邊）",
                  "C3s 窗尾 2026-09-30，比本件資料尾短 3 個交易日"],
           "資料": {"窗": [str(cal[a].date()), str(cal[tail].date())], "現金": gsrc, "成本": TP.COST},
           "閘": gates, "變體": arms, "名單": picks_tab,
           "逐日權益（repo外）": {"path": dpath, "sha256": K.sha256f(dpath)}, "產出時間": K.now_tpe()}
    K.jdump(out, os.path.join(OUTD, "var.json"))

    def f(x):
        return "" if x is None else (x if isinstance(x, str) else round(float(x), 6))
    with open(os.path.join(OUTD, "var_summary.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["變體", "年化", "最大回落", "回本年數", "年化÷|回落|", "拿掉的年", "拿掉最好一年後年化", "最差一年", "最差一年報酬",
                     "勝^SP500TR年數", "年數", "2026貢獻占比", "最大單一持股", "最大單一持股占總獲利", "期末倍數"])
        for k in order:
            d = arms[k]
            wr.writerow([k, f(d["年化"]), f(d["最大回落"]), f(d["回本年數"]), f(d["年化÷|回落|"]), d["拿掉最好一年"]["年"],
                         f(d["拿掉最好一年"]["年化"]), d["最差一年"]["年"], f(d["最差一年"]["報酬"]), d["勝^SP500TR年數"], d["年數"],
                         f(d["2026貢獻占比"]), d["最大單一持股"]["代號"], f(d["最大單一持股"]["占總獲利"]), f(d["期末倍數"])])
    with open(os.path.join(OUTD, "var_years.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["年"] + order)
        for y in years:
            wr.writerow([y] + [f(arms[k]["逐年"][y]) for k in order])
    with open(os.path.join(OUTD, "var_picks.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["變體", "換股日", "名單"]); wr.writeheader(); [wr.writerow(r) for r in picks_tab]

    print("閘", json.dumps(gates, ensure_ascii=False, default=str))
    for k in order:
        d = arms[k]
        print("%-28s 年化 %+7.1f%% 回落 %6.1f%% 回本 %-8s 比 %.2f | 拿%d %+6.1f%% | 最差 %d %+6.1f%% | 勝 %s/%d | 26占 %s | 單一 %s %s" % (
            k, d["年化"] * 100, d["最大回落"] * 100,
            ("%.2f" % d["回本年數"]) if not isinstance(d["回本年數"], str) else "未回本", d["年化÷|回落|"],
            d["拿掉最好一年"]["年"], d["拿掉最好一年"]["年化"] * 100, d["最差一年"]["年"], d["最差一年"]["報酬"] * 100,
            str(d["勝^SP500TR年數"]), d["年數"], None if d["2026貢獻占比"] is None else round(d["2026貢獻占比"], 3),
            d["最大單一持股"]["代號"], None if d["最大單一持股"]["占總獲利"] is None else round(d["最大單一持股"]["占總獲利"], 3)))
        if "事件" in d and d["事件"]:
            print("   事件", d["事件"])
        if "損益恆等式殘差（現金利息等）" in d:
            print("   殘差", d["損益恆等式殘差（現金利息等）"], "回本日", d["回本日"], "高點", d["高點日"], "谷底", d["谷底日"])
    print("資料尾", cal[tail].date())


if __name__ == "__main__":
    main()

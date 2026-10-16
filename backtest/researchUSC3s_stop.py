# -*- coding: utf-8 -*-
"""USREG-C3s 停用條件 seq1（美股策略線登錄 sha 66e76e0d71ac3cd9；裁定 seq353 §三.1 核；監控規則、⛔ 不計 N）§四 ①②③ ——回測線計算子代理。
登錄：「登錄全文-USREG-C3s停用條件_seq1_美股策略線_sha66e76e0d71ac3cd9-3471B-20261016-2330.md」（整檔 sha 已驗）；結構比照台股〈營量營飆停用條件 seq2〉
（sha dc15709ec3e4d123）與其回測實作 backtest/researchStopRule.py（狀態機 SR.levels、月底統計 SR.path_stats、SR.lev_days 直接 import 重用）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC3s_stop            # ①② 算 x、Dmax、歷史驗算
    ... -m backtest.researchUSC3s_stop --month 2026-11-30                 # ③ 前瞻簿某月底的「停用條件級別」一行
    ... -m backtest.researchUSC3s_stop --order 2026-11-30                 # ③ ops 前瞻換股單＋級別一行（不改 ops 原檔）
    獨立查核：... -m backtest.researchUSC3s_stop_check

═══ 讀法（⭐ 寫死於 2026-10-16 23:46（台北），在算任何本件數字之前；本線看過的只有登錄所引 C3s 看過段年化 +24.5%、回落 −44.5%；
    ⛔ 沒看過任何月底 R12 分布、⛔ 沒看過 C3s 早年段任何數字）═══
 S1 淨值來源（⛔ 不改引擎）：C3s 主臂 ＝ researchUSC3s_ops.run_book(tables(), t0, w1)（＝ researchUSC3s.rank_main 內同一個 K.book 呼叫）；
    閘：權益 對 ~/us_work/c/c3s/c3s_eq_trades.pkl 逐日差 ≤ 1e−12。看過段 ＝ [a0 ＝ 2016-12-30 收盤（權益 1.0）, w1 ＝ 2026-09-30]（登錄 §二）。
    基準 ＝ K.rworld()["B"]（A4.bench_series ＝ ^SP500TR 含息，ffill）。⛔ 早年段 2000～2015 不讀、不定門檻（登錄 §二，覆蓋約 77%）。
 S2 月底 ＝ (a0, w1] 內每個日曆月最後一個交易日（下一交易日換月者）；M0 ＝ a0（2016-12-30 本身是月底，只當基準點、⛔ 不當第 1 個月底）。
    第 j 個月底：j ≥ 12 ⇒ R12 ＝ (E[Mj]/E[Mj−12] − 1) − (B[Mj]/B[Mj−12] − 1)；D ＝ E[Mj] ÷ a0 起逐日最高 − 1（＝ SR.path_stats）。
 S3 ① x ＝ 看過段所有 j ≥ 12 月底 R12 的第 5 百分位（np.percentile 線性內插；SR.pct5）；Dmax ＝ 看過段逐日最深回落（閘：＝ C3s summary.json a 看過段.回落，差 ≤ 1e−12）。
    寫死 ＝ 原始浮點（repr），另附百分比一位小數；本檔常數 X_FIX、DMAX_FIX 由本次結果填入，run 時閘「重算 ＝ 常數」。
 S4 ② 歷史滾動驗算：看過段當成一次前瞻（a0 級 0、月數與高點自 a0 起算）；判斷值 R：j ＜ 6 不判；6 ≤ j ＜ 12 累計差；j ≥ 12 R12。
    狀態機 ＝ researchStopRule.levels（台股 seq2 讀法 ①～③ 原樣：級 2 恢復回級 1 期間遇 T1／警戒起 3 個月時鐘；前 6 個月改善／恢復只看 D）。
    T3（資料源缺漏）無法回測 ⇒ 不套。
 S5 ② 報：每年進級 1（0→1）／進級 2 次數、各級生效月數（第 j 個月生效級 ＝ 第 j−1 個月底判後）、級 1／級 2 段數與長度；
    觸發後 12 個月 策略 − ^SP500TR（Mj → Mj+12；不足 12 個月另標「未滿」）。
    「太敏感」＝ 進級 2 次數 ÷ 年數 ＞ 0.5（每 2 年超過 1 次）；「太鈍」＝ 2018-10～2018-12 三個月底與 2022 全年 12 個月底，判後級別都沒有 ≥ 1。
    ⚠ 循環：x、Dmax 取自同一看過段 ⇒ T1 依構造約 5% 月底觸發；T2 停用線＝看過段最深那一次 ⇒ 月底最多碰一次 ⇒ 照數、⛔ 不據此說明前瞻觸發頻率。
 S6 照規則減碼／停用的帳戶模擬（⭐ 真模擬，不是逐筆重播；⛔ 不改 K.book）：book_lv ＝ K.book 同式另加級別乘數與 SPY 子帳。
    級別一律由【紙上淨值】（原 C3s、不減碼）判（登錄 §三：停用期間照記紙上淨值）⇒ 級別序列與模擬帳戶無關；生效日 ＝ 月底的下一交易日（＝ 換股日 e）。
    每檔新買 ＝ m × 前一日帳戶總值 ÷ 8（m：級 0 ＝ 1、級 1 ＝ 0.5、級 2 ＝ 不新買）；級 1 時另一半（同額，現金夠才買）買 SPY；買股現金不足先賣 SPY 補。
    進級 2 生效日：當日換股賣出後現金全轉 SPY；級 2 期間出場淨入帳當日轉 SPY；回級 0 生效日：SPY 開盤全賣回現金；級 2→恢復級 1：SPY 留著、買股時賣。
    SPY ＝ us-stock-data 881c86a（＝ world 同一快照）yahoo_SPY 還原價（開 ＝ open × adjclose ÷ close、收 ＝ adjclose），一律以生效日【開盤】進出、
    每次單邊付 COST/2（0.025%；K.book 0.05% 是來回、出場一次扣）。停用期間空出的槽，恢復後照當時名單補（真模擬 ⇒ 不像台股逐筆重播那樣偏少）。
    閘：級別全 0 ⇒ book_lv 權益 ＝ K.book 逐日差 ≤ 1e−12。
 S7 ③ 前瞻：month_level(月底) ＝ 前瞻 ② 簿（researchUSC3s_ops FWD_START_MONTH：2026-10 最後交易日收盤選、11 月第一個交易日開盤買）的紙上淨值
    （ops.run_book 同一呼叫，自 b0 跑到該月底；E[b0−1] ＝ 1.0）＋ ^SP500TR 同日；月底自 2026-11 起；狀態機與 S4 同、x、Dmax 用寫死常數。
    第一次判 2026-11-30（T2 從起點判；T1 第 6 個月底 2027-04-30 起判）。輸出一行「停用條件級別：L（原因；動作）」。
 輸出 backtest/resultsUSC/C3s/stop/：stop.json、levels_monthly.csv（只放月底的 R、D、級別；⛔ 不放逐日權益）；逐日模擬權益 → ~/us_work/c/c3s/stop/。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K            # noqa: E402
from backtest import researchUSC3s as C3S        # noqa: E402
from backtest import researchUSC3s_ops as OPS    # noqa: E402
from backtest import researchStopRule as SR      # noqa: E402  狀態機、月底統計（只 import）

READ_TS = "2026-10-16 23:46（台北）"
SHA = "66e76e0d71ac3cd9"
REGFILE = "登錄全文-USREG-C3s停用條件_seq1_美股策略線_sha66e76e0d71ac3cd9-3471B-20261016-2330.md"
RULING = "裁定 seq353 §三.1（2026-10-16 23:35）"
OUTD = os.path.join(C3S.OUTD, "stop")
PRIVD = os.path.join(C3S.WORKD, "stop")
SEEN = ("2016-12-30", "2026-09-30")
SPY_ROOT = os.path.expanduser("~/usdata/881c86a")       # ＝ world.npz 同一快照
BC = K.COST / 2
MULT = {0: 1.0, 1: 0.5, 2: 0.0}

# ⭐ 寫死（① 結果；run 時閘「重算 ＝ 常數」）——看過段 2016-12-30～2026-09-30
X_FIX = -0.2526105731574773         # x ＝ −25.3%：106 個月底 R12（2017-12-29～2026-09-30）第 5 百分位
DMAX_FIX = -0.4450480185832988      # Dmax ＝ −44.5%：高點 2018-06-01 → 低點 2020-03-23；警戒 0.8×Dmax ＝ −35.6%


def jd(obj, name):
    os.makedirs(OUTD, exist_ok=True)
    return K.jdump(obj, os.path.join(OUTD, name))


def pc(v, d=1):
    return None if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


# ═════════════ 月底 ═════════════
def month_ends(cal, a0, b):
    """(a0, b] 內每月最後一個交易日（下一交易日換月者；b 是資料最後一日時，b 本身不算）。"""
    per = cal.to_period("M")
    return [p for p in range(a0 + 1, b + 1) if p + 1 < len(cal) and per[p + 1] != per[p]]


# ═════════════ SPY 子帳價格（S6）═════════════
def spy_px(cal, root=SPY_ROOT):
    y = pd.read_csv(os.path.join(root, "data", "macro", "yahoo_SPY.csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")
    for c in ("open", "close", "adjclose"):
        y[c] = pd.to_numeric(y[c], errors="coerce")
    y.index = pd.DatetimeIndex(y.index)
    k = y["adjclose"] / y["close"]
    o = (y["open"] * k).reindex(cal).to_numpy(float)
    c = y["adjclose"].reindex(cal).ffill().to_numpy(float)
    o = np.where(np.isfinite(o) & (o > 0), o, c)
    return o, c


# ═════════════ 減碼／停用帳戶（S6；K.book 同式＋級別＋SPY 子帳）═════════════
def book_lv(Wd, keep, buy, N, t0, t1, levd, so, sc, cost=K.COST):
    O, CF, valid, last, brk = Wd["O"], Wd["CF"], Wd["valid"], Wd["last"], Wd["pb"]
    n = len(Wd["cal"]); eq = np.ones(n); cash = 1.0; Z = 0.0; pos = {}; pend = set()
    zf = np.zeros(n)
    rset = set(int(e) for e in keep if t0 <= e <= t1)
    nbuy = {0: 0, 1: 0}

    def to_spy(t):
        nonlocal cash, Z
        if cash > 0:
            Z += cash * (1 - BC) / so[t]; cash = 0.0
    for t in range(t0, t1 + 1):
        lt = int(levd[t]); lp = int(levd[t - 1])
        for j in list(pos):
            u, amt, b, hi = pos[j]
            if t > b and brk[t, j]:
                px = CF[t - 1, j]
            elif t > last[j]:
                px = CF[last[j], j]
            else:
                continue
            pos.pop(j); pend.discard(j); cash += u * px - amt * cost
        if lt != lp:
            if lt == 0 and Z > 0:
                cash += Z * so[t] * (1 - BC); Z = 0.0
        isreb = t in rset
        if isreb:
            ks = keep.get(t, set())
            pend |= (set(pos) - set(ks)); pend -= set(ks)
        for j in sorted(pend):
            if j not in pos:
                pend.discard(j); continue
            o_t = O[t, j]
            if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                continue
            u, amt, b, hi = pos.pop(j); cash += u * o_t - amt * cost; pend.discard(j)
        if lt == 2:
            to_spy(t)
        elif isreb:
            m = MULT[lt]; slot = eq[t - 1] / N
            free = N - len(pos)
            for j in [j for j in buy.get(t, []) if j not in pos][:max(free, 0)]:
                o_t = O[t, j]
                if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                    continue
                want = m * slot
                if cash < want and Z > 0:
                    units = min((want - cash) / (so[t] * (1 - BC)), Z)
                    cash += units * so[t] * (1 - BC); Z -= units
                amt = min(want, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[j] = [amt / o_t, amt, t, o_t]; nbuy[lt] += 1
                if lt == 1:
                    h = min(0.5 * slot, cash)
                    if h > 0:
                        Z += h * (1 - BC) / so[t]; cash -= h
        hv = 0.0
        for j, p in pos.items():
            c = CF[t, j]; hv += p[0] * c
            if c > p[3]:
                p[3] = c
        eq[t] = cash + Z * sc[t] + hv; zf[t] = Z * sc[t] / eq[t]
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    return eq, zf, nbuy


# ═════════════ ① ② ═════════════
def main_path():
    R = K.rworld(); cal = R["cal"]; w1 = R["w1"]
    T = OPS.tables(); t0 = T["t0"]; a0 = t0 - 1
    assert str(cal[a0].date()) == SEEN[0] and str(cal[w1].date()) == SEEN[1], (cal[a0], cal[w1])
    res, tr = OPS.run_book(T, t0, w1)
    return R, T, res, t0, a0, w1


def run():
    T0 = time.time(); os.makedirs(OUTD, exist_ok=True); os.makedirs(PRIVD, exist_ok=True)
    R, T, res, t0, a0, w1 = main_path(); cal = R["cal"]; B = R["B"]; W = R["Wd"]
    eq = res["eq"]; gates = {}
    pk = pd.read_pickle(os.path.join(C3S.WORKD, "c3s_eq_trades.pkl"))
    gates["G1 主臂權益 對 c3s_eq_trades.pkl 最大差"] = float(np.max(np.abs(eq[:w1 + 1] - pk["eq"][:w1 + 1])))
    summ = json.load(open(os.path.join(C3S.OUTD, "summary.json"), encoding="utf-8"))
    MEs = month_ends(cal, a0, w1)
    s = SR.path_stats(eq, B, a0, w1, MEs)
    x = SR.pct5(s["R12"]); Dm = float(s["mdd"])
    gates["G2 Dmax 對 summary.json 回落 差"] = abs(Dm - summ["a 看過段"]["回落"])
    if X_FIX is not None:
        gates["G3 重算 x ＝ 寫死常數（差）"] = abs(x - X_FIX); gates["G3 重算 Dmax ＝ 寫死常數（差）"] = abs(Dm - DMAX_FIX)
    TH = {"x": x, "x_百分比": pc(x), "Dmax": Dm, "Dmax_百分比": pc(Dm), "警戒線 0.8×Dmax": 0.8 * Dm, "警戒線_百分比": pc(0.8 * Dm),
          "x 出處": f"看過段 {SEEN[0]}～{SEEN[1]} 每個月底 R12（j ≥ 12，共 {int(np.isfinite(s['R12']).sum())} 個：{cal[MEs[11]].date()}～{cal[MEs[-1]].date()}）的第 5 百分位（np.percentile 線性內插）",
          "Dmax 出處": f"看過段逐日最深回落：高點 {cal[s['peak']].date()} → 低點 {cal[s['trough']].date()}",
          "R12 分布（參考）": {"最小": float(np.nanmin(s["R12"])), "p10": float(np.nanpercentile(s["R12"], 10)), "中位": float(np.nanmedian(s["R12"])),
                           "最大": float(np.nanmax(s["R12"]))},
          "月底個數": len(MEs), "首月底": str(cal[MEs[0]].date()), "末月底": str(cal[MEs[-1]].date()),
          "⛔": "早年段 2000～2015 不讀、不定門檻（登錄 §二）"}
    K.log(f"[C3s停用] ① x {x!r}（{pc(x)}）｜Dmax {Dm!r}（{pc(Dm)}）", "c3s_stop.log")
    # ② 狀態機
    lv = SR.levels(s["RJ"], s["D"], x, Dm)
    Kn = len(lv); eff = [0] + [lv[j]["L"] for j in range(Kn - 1)]
    rows, yt, trig = [], {}, []
    for j in range(Kn):
        d = cal[s["P"][j + 1]]; y = int(d.year)
        Y = yt.setdefault(str(y), {"進級1": 0, "進級2": 0, "月_級0": 0, "月_級1": 0, "月_級2": 0})
        Y[f"月_級{eff[j]}"] += 1
        L, prev = lv[j]["L"], lv[j]["prev"]
        if L == 1 and prev == 0:
            Y["進級1"] += 1
        if L == 2 and prev != 2:
            Y["進級2"] += 1
        if (L == 1 and prev == 0) or (L == 2 and prev != 2):
            jj = j + 1; je = min(jj + 12, Kn)
            trig.append({"月": str(d.to_period("M")), "進": f"級{L}", "原因": lv[j]["why"], "滿12月": bool(jj + 12 <= Kn),
                         "策略": float(s["E"][je] / s["E"][jj] - 1), "^SP500TR": float(s["B"][je] / s["B"][jj] - 1),
                         "策略−^SP500TR": float((s["E"][je] / s["E"][jj] - 1) - (s["B"][je] / s["B"][jj] - 1))})
        rows.append({"月": str(d.to_period("M")), "月底日": str(d.date()), "月序": j + 1, "R_類": s["kind"][j], "R": s["RJ"][j], "R12": s["R12"][j], "D": s["D"][j],
                     "T1": int(lv[j]["t1"]), "T2警戒": int(lv[j]["warn"]), "T2停用": int(lv[j]["stop"]), "改善": int(lv[j]["imp"]), "恢復條件": int(lv[j]["rok"]),
                     "判前級": lv[j]["prev"], "判後級": L, "恢復級1": int(lv[j]["rec"]), "生效級（本月）": eff[j], "變動原因": lv[j]["why"]})
    effs = eff[1:] + [lv[-1]["L"]]
    runs = [(int(g.iloc[0]), len(g)) for _, g in pd.Series(effs).groupby((pd.Series(effs) != pd.Series(effs).shift()).cumsum())]
    yrs = Kn / 12.0; n2 = sum(int(v["進級2"]) for v in yt.values())
    q4 = [r for r in rows if r["月"] in ("2018-10", "2018-11", "2018-12")]; y22 = [r for r in rows if r["月"].startswith("2022-")]
    q4_hit = any(r["判後級"] >= 1 for r in q4); y22_hit = any(r["判後級"] >= 1 for r in y22)
    # S6 帳戶模擬
    so, sc = spy_px(cal)
    levd = SR.lev_days(len(eq), MEs, lv, w1)
    V0, _, _ = book_lv(W, T["KEEP"], T["BUY"], K.N_SLOTS, t0, w1, np.zeros(len(eq), np.int8), so, sc)
    gates["G4 book_lv（級別全 0）對 K.book 最大差"] = float(np.max(np.abs(V0[:w1 + 1] - eq[:w1 + 1])))
    V, zf, nb = book_lv(W, T["KEEP"], T["BUY"], K.N_SLOTS, t0, w1, levd, so, sc)
    m0 = K.metrics(eq, a0, w1); m1 = K.metrics(V, a0, w1); mb = K.metrics(B, a0, w1)
    spy_m = K.metrics(sc, a0, w1)
    pd.DataFrame({"日期": cal[a0:w1 + 1].strftime("%Y-%m-%d"), "C3s原": eq[a0:w1 + 1], "照規則": V[a0:w1 + 1], "SPY占比": zf[a0:w1 + 1],
                  "生效級": levd[a0:w1 + 1]}).to_csv(os.path.join(PRIVD, "sim_daily.csv"), index=False, float_format="%.12g")
    VER = {"太敏感 定義": "進級 2 次數 ÷ 年數 ＞ 0.5（每 2 年超過 1 次）", "進級2 次數": n2, "年數（月底數÷12）": yrs, "進級2 每年": n2 / yrs,
           "太敏感": bool(n2 / yrs > 0.5),
           "太鈍 定義": "2018-10～12 三個月底與 2022 全年月底，判後級別都沒有 ≥ 1", "2018Q4 有級≥1": bool(q4_hit), "2022 有級≥1": bool(y22_hit),
           "太鈍": bool(not q4_hit and not y22_hit),
           "2018Q4 月底": [{k: r[k] for k in ("月", "R_類", "R", "D", "判後級", "變動原因")} for r in q4],
           "2022 月底最深 D": float(min(r["D"] for r in y22)), "2022 月底最低 R": float(np.nanmin([r["R"] for r in y22]))}
    OUT = {"件": "USREG-C3s 停用條件 seq1 §四 ①②（監控規則、⛔ 不計 N）", "登錄": f"美股策略線 seq1 sha {SHA}（{REGFILE}）", "裁定": RULING,
           "讀法寫死": READ_TS, "閘": gates, "①": TH,
           "② 歷史驗算（看過段，描述、⛔ 不改條件）": {
               "判斷": VER, "每年": yt, "觸發後12月": trig,
               "生效級月數": {f"級{k}": int(sum(1 for e_ in eff if e_ == k)) for k in (0, 1, 2)},
               "級1段長（月）": [ln for l_, ln in runs if l_ == 1], "級2段長（月）": [ln for l_, ln in runs if l_ == 2],
               "月底 T1 觸發數": int(sum(z["t1"] for z in lv)), "R12＜x 月數 ÷ R12 月數": float(np.nansum(s["R12"] < x) / np.isfinite(s["R12"]).sum()),
               "月底碰 T2警戒 次數": int(sum(z["warn"] for z in lv)), "月底碰 T2停用 次數": int(sum(z["stop"] for z in lv)),
               "照規則減碼／停用後": {"原 年化": m0["年化"], "原 回落": m0["回落"], "原 比值": m0["比值"],
                              "規則後 年化": m1["年化"], "規則後 回落": m1["回落"], "規則後 比值": m1["比值"],
                              "年化差（點）": (m1["年化"] - m0["年化"]) * 100, "回落差（點）": (m1["回落"] - m0["回落"]) * 100,
                              "^SP500TR": mb, "SPY（子帳標的，參考）": spy_m,
                              "新買筆數（級0／級1）": nb, "SPY 平均占比": float(zf[a0 + 1:w1 + 1].mean())},
               "循環": "x、Dmax 取自同一看過段 ⇒ 驗算是樣本內：T1 觸發率依構造約 5%；T2 停用線就是最深那次的逐日低點，月底要剛好在低點才碰得到 ⇒ "
                     "⛔ 不能拿來說明前瞻 T2 多常觸發；T3 無法回測"},
           "近似與口徑": ["級別由紙上淨值（原 C3s、不減碼）判；模擬帳戶只量照規則後的年化與回落",
                     "真模擬（K.book 同式＋級別乘數）：級 1 每檔新買 ＝ 0.5 × 前一日總值 ÷ 8、另一半買 SPY；級 2 不新買、現金與出場入帳轉 SPY；回級 0 SPY 全賣；"
                     "SPY 以生效日開盤進出、單邊 0.025%；停用期間空槽恢復後照當時名單補",
                     "SPY ＝ us-stock-data 881c86a yahoo_SPY 還原價（含息）"],
           "存活者偏差": "看過段母體事後縮成 S&P 500、18 檔不在母體 ⇒ 門檻可能偏寬鬆（登錄 §六）",
           "③ 前瞻接口": "month_level(月底) / level_line(月底) / order_with_level(月底)（本檔）；第一次判 2026-11-30",
           "私有": {"逐日模擬": os.path.join(PRIVD, "sim_daily.csv")},
           "算於": K.now_tpe() + "（台北）", "秒": round(time.time() - T0)}
    jd(OUT, "stop.json")
    with open(os.path.join(OUTD, "levels_monthly.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader()
        for r in rows:
            wr.writerow({k: (repr(float(v)) if isinstance(v, (float, np.floating)) and np.isfinite(v) else ("" if isinstance(v, (float, np.floating)) else v))
                         for k, v in r.items()})
    print(json.dumps({"閘": gates, "①": {k: TH[k] for k in ("x", "x_百分比", "Dmax", "Dmax_百分比", "警戒線_百分比", "x 出處", "Dmax 出處")},
                      "判斷": {k: VER[k] for k in ("進級2 次數", "進級2 每年", "太敏感", "2018Q4 有級≥1", "2022 有級≥1", "太鈍")},
                      "照規則": OUT["② 歷史驗算（看過段，描述、⛔ 不改條件）"]["照規則減碼／停用後"]}, ensure_ascii=False, indent=1, default=K._jdef))
    return OUT


# ═════════════ ③ 前瞻接口 ═════════════
def fwd_b0():
    R = K.rworld(); y, m = OPS.FWD_START_MONTH
    k0 = y * 12 + m - 1
    if k0 not in R["last"] or R["last"][k0] + 1 >= R["n"]:
        return None
    return R["last"][k0] + 1


ACT = {0: "正常", 1: "之後新買減半、空出的錢放 SPY", 2: "停止新買、持股照原規則出清、資金轉 SPY"}


def month_level(month, x=None, Dmax=None):
    """前瞻 ② 簿在月底 month（YYYY-MM-DD，當月最後交易日）判後的級別。⇒ dict（級別、原因、R、D、逐月序列）。
    x、Dmax 預設用寫死常數 X_FIX、DMAX_FIX（seq2 定版後）。"""
    x = X_FIX if x is None else x; Dmax = DMAX_FIX if Dmax is None else Dmax
    if x is None or Dmax is None:
        raise SystemExit("X_FIX／DMAX_FIX 尚未寫死")
    R = K.rworld(); cal = R["cal"]
    M, _virtual = OPS.month_end_index(month)          # 驗：資料內交易日、且為當月最後交易日（資料最後一日視為月底）
    b0 = fwd_b0()
    if b0 is None or M < b0:
        return {"月底": month, "級別": None, "原因": "未生效（前瞻 ② 簿 2026-11 起、第一次判 2026-11-30）", "序列": []}
    T = OPS.tables()
    res, _ = OPS.run_book(T, b0, M)
    a0 = b0 - 1
    MEs = [p for p in range(a0 + 1, M + 1) if (p + 1 < R["n"] and R["ym"][p + 1] != R["ym"][p]) or p == M]
    s = SR.path_stats(res["eq"], R["B"], a0, M, MEs)
    lv = SR.levels(s["RJ"], s["D"], x, Dmax)
    seq = [{"月底": str(cal[s["P"][j + 1]].date()), "R_類": s["kind"][j], "R": (float(s["RJ"][j]) if np.isfinite(s["RJ"][j]) else None),
            "D": float(s["D"][j]), "判後級": lv[j]["L"], "恢復級1": lv[j]["rec"], "變動原因": lv[j]["why"]} for j in range(len(lv))]
    cur = lv[-1]; L = cur["L"]
    why = cur["why"]
    if not why and L > 0:                       # 沿用：最近一次變動的原因
        why = next((z["why"] for z in reversed(lv) if z["why"]), "")
    return {"月底": month, "級別": L, "恢復級1": cur["rec"], "原因": why or "正常", "本月變動": bool(cur["why"]) and cur["prev"] != L,
            "R": seq[-1]["R"], "R_類": seq[-1]["R_類"], "D": seq[-1]["D"], "x": x, "Dmax": Dmax, "警戒線": 0.8 * Dmax, "序列": seq}


def level_line(month):
    """每月換股單加的一行：「停用條件級別：L（原因；動作）」。"""
    v = month_level(month)
    if v["級別"] is None:
        return f"停用條件級別：—（{v['原因']}）"
    if v["級別"] == 0:
        return "停用條件級別：0（正常" + (f"；本月{v['原因']}回級 0）" if v["本月變動"] else "）")
    return f"停用條件級別：{v['級別']}（{v['原因']}；{ACT[v['級別']]}）"


def order_with_level(month, book="forward"):
    """＝ researchUSC3s_ops.run_month 同一流程（order_for → order_view → order_row），只在 view 加「停用條件級別」、備註欄尾加同一行；
    寫 resultsUSC/C3s/ops/order_<YYYYMMDD>_forward_lv.csv（⛔ 不覆寫 ops 原檔）。"""
    R = K.rworld(); cal = R["cal"]
    M, virtual = OPS.month_end_index(month)
    o, T = OPS.order_for(M, book)
    v = OPS.order_view(o, T)
    line = level_line(month)
    v["停用條件級別"] = line
    cols, row = OPS.order_row(o, T)
    row[cols[-1]] = (row[cols[-1]] + "；" if row[cols[-1]] else "") + line
    p = os.path.join(OPS.OPSD, f"order_{cal[M].strftime('%Y%m%d')}{'_forward' if book == 'forward' else ''}_lv.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(cols); wr.writerow([row[c] for c in cols])
    print(json.dumps(v, ensure_ascii=False, indent=1, default=K._jdef)); print("→", p)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="月底 YYYY-MM-DD ⇒ 前瞻簿停用條件級別一行")
    ap.add_argument("--order", help="月底 YYYY-MM-DD ⇒ ops 前瞻換股單＋級別一行")
    a = ap.parse_args()
    if a.month:
        v = month_level(a.month); print(level_line(a.month)); print(json.dumps({k: v[k] for k in v if k != "序列"}, ensure_ascii=False, default=K._jdef))
    elif a.order:
        order_with_level(a.order)
    else:
        run()


if __name__ == "__main__":
    main()

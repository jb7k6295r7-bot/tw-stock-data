# -*- coding: utf-8 -*-
"""PREREGC14「六幣之內強幣續強（橫斷面動能）」v1（sha e312eee71dfbfaf1）——回測線執行端。裁定 seq298：核准，N＝4。

⭐ 讀法寫死：2026-10-04 21:11（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何價差之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法標【執行者補】。
⚠ 照實寫（seq298）：MDE 約 1.13%／週；論文（Liu, Tsyvinski & Wu 2022, JF）全市場 3 週動能 4.1%／週；6 大幣內依構造只有大效果判得出。
⚠ 價格 2019～2026 本專案各件都看過；六幣排序價差從未算過。

資料：公開 main 1fb8815e81 data/crypto/<SYM>.csv（唯讀副本 ~/c10data/<sha>）現貨日 K，只用公開檔（登錄 §九①）；描述①的合約段另用 C10 的幣本位永續（成交價、標記價、資金費）

⭐ 落地讀法
 P1 週與週報酬：同 C13（researchC13.weekly：W-SUN＝週日 UTC 收盤；r＝對數週報酬；週日缺 ⇒ 缺）
 P2 排名時點 t＝週日收盤；幣 i 在 t 可排名＝t、t−1 週、…、t−L 週的週收盤都有（≥ L＋1 週資料）且下一週報酬 r_{i,t+1} 有值
    排名分數＝過去 L 週對數報酬之和（只用 t 以前，含 t）；L ∈ {1、2、3、4}
 P3 判定量：下一週「前 2 名平均 r_{t+1} − 後 2 名平均 r_{t+1}」（同權、對數報酬）；可排名幣 < 4 ⇒ 該週不算；5、6 幣時中間的不算
 P4 樣本外窗：持有週（t＋1 週的週日）落在 2019-01-06～2026-09-27【執行者補：以持有週定窗，對上登錄的 404 週】
 P5 CI：價差序列 stationary block bootstrap（researchc1，L_b＝Politis–White），2,000 次、種子 20260923，信賴水準 1−0.05/4（雙尾各 0.05/8）
    出口②：下界 > 0｜出口③：上界 < 0｜出口①：含 0
 P6 描述（不判、N＝0、⛔ 不寫倍數建議）：
    ① 「存 6 幣不動＋每週把多開的 0.2 倍（名目＝0.2 × 組合美元值）放在 L 週最強的 1 幣」vs「0.2 倍平分給 6 幣（各 0.2/6）」vs「只存幣」：
       起點 2020-08-16（週日收盤，6 幣都有現貨）各幣等美元；每週日收盤排名、週一（UTC）開盤調整名目（C10 再平衡寫法：權益不變、手續費 0.05% × |名目變動|）；
       各幣逐倉、保證金＝該幣全部持幣；強平＝該幣持幣歸零、之後不再參與【執行者補】；
       幣本位永續上市前用現貨代理（⛔ 不計資金費），上市後用永續成交價、標記價日低、資金費（C11 S6 的 00:00 歸屬）；m 0.5／1／2%
       報期末組合美元值（相對起點）、各幣期末幣數（相對起點）、強平幣與日期
    ② BTC 對 SOL：兩幣都有資料的週（持有週在窗內），上週（L＝1）誰強，下週是否仍強——仍強比例與平均差
    ③ 逐年價差（依持有週年份）；4 幣版本（排除 SOL、DOGE）；前 1 名 − 後 1 名版本
 P7 先驗對答：① 4 個 L 全部出口① ② 沒有出口③
 P8 --check：fixture a 排名只用 t 以前（反例：含 t＋1）、b 新幣上市前不入排名（反例：缺值補 0）、c 5 幣時前 2／後 2 不重疊、中間不算（反例：中位數重複計入）；
    參考實作（純迴圈）重算 4 個 L 的價差序列逐位比；描述①引擎閘門：名目 0 時期末值＝只存幣
⛔ 出口②也不是「每週換到最強幣」的建議；出口①只能寫「6 幣內測不出」，⛔ 不寫「強幣續強無效」。
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, html
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchc1 as C1
import researchC10 as C10
import researchC11 as C11
import researchC12 as C12
import researchC13 as C13

OUT = os.path.join(C10.REPO, "backtest", "resultsC14")
COINS = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE")
LS = (1, 2, 3, 4)
W0, W1 = "2019-01-06", "2026-09-27"
N_CELLS = 4
SEED = 20260923
N_BOOT = 2000
EXTRA = 0.2
D1_START = "2020-08-16"
FROZEN = "2026-10-04 21:11（台北）"


def daily_pub(sym):
    d = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str})[["date", "open", "high", "low", "close"]]
    d = d.drop_duplicates("date").sort_values("date")
    return d[d["date"] <= "2026-09-30"].reset_index(drop=True)


def weekly_table(daily):
    """各幣週報酬並成一張表（index＝週日）。"""
    R = pd.DataFrame({s: C13.weekly(daily[s]) for s in daily})
    return R.sort_index()


def spreads(R, L, coins=COINS, top=2, mut=None):
    """P2～P4：回 DataFrame(持有週, 價差, 可排名幣數, 前段, 後段)。
    mut：leak（分數含 t＋1）｜fill0（缺值補 0、上市前也排）｜median（前後段各取 ceil(n/2)，5 幣時中位數重複）"""
    V = R[list(coins)]
    weeks = V.index.to_numpy(); out = []
    for i in range(L, len(weeks) - 1):
        hold = weeks[i + 1]
        if hold < W0 or hold > W1:
            continue
        past = V.iloc[i - L + 1:i + 1]
        nxt = V.iloc[i + 1]
        if mut == "fill0":
            past = past.fillna(0.0); nxt = nxt.fillna(0.0)
        score = past.sum(min_count=L) if mut != "fill0" else past.sum()
        if mut == "leak":
            score = score + nxt
        ok = [c for c in coins if np.isfinite(score[c]) and np.isfinite(nxt[c]) and past[c].notna().sum() == L] if mut != "fill0" else list(coins)
        if len(ok) < 4:
            continue
        order = sorted(ok, key=lambda c: -score[c])
        n = len(order)
        if mut == "median":
            k = math.ceil(n / 2); hi, lo = order[:k], order[n - k:]
        else:
            hi, lo = order[:top], order[-top:]
        out.append({"持有週": hold, "價差": float(np.mean([nxt[c] for c in hi]) - np.mean([nxt[c] for c in lo])), "幣數": n,
                    "前段": "、".join(hi), "後段": "、".join(lo), "最強": order[0]})
    return pd.DataFrame(out)


def ci_mean(x):
    L = C1.politis_white_block(x); rng = np.random.default_rng(SEED)
    bs = np.array([x[C1.stationary_idx(len(x), L, rng)].mean() for _ in range(N_BOOT)])
    a = 0.05 / N_CELLS / 2
    return float(np.percentile(bs, 100 * a)), float(np.percentile(bs, 100 * (1 - a))), int(L)


# ───────────────────────── fixture ─────────────────────────
def _synR(n=500, late=None):
    rng = np.random.default_rng(11)
    idx = pd.date_range("2018-01-07", periods=n, freq="7D").strftime("%Y-%m-%d")
    R = pd.DataFrame(rng.normal(0, 0.1, (n, 6)), index=idx, columns=list(COINS))
    if late:
        R.loc[R.index < late, "SOL"] = np.nan
    return R


def fx_a(mut=None):
    """a. 排名只用 t 以前：某一週手算（過去 3 週和）的前 2／後 2 價差必須相等。"""
    R = _synR(); S = spreads(R, 3, mut=mut)
    w = S.iloc[20]["持有週"]; i = int(np.flatnonzero(R.index == w)[0]) - 1
    sc = R.iloc[i - 2:i + 1].sum(); nx = R.iloc[i + 1]
    o = sc.sort_values(ascending=False).index
    want = nx[o[:2]].mean() - nx[o[-2:]].mean()
    return bool(abs(S.iloc[20]["價差"] - want) < 1e-15)


def fx_b(mut=None):
    """b. 新幣上市前不入排名：SOL 2020-08-23 才有第一筆週報酬 ⇒ L＝2 時，持有週 2020-08-30 以前可排名幣數只有 5，2020-09-06 起 6。"""
    R = _synR(late="2020-08-23"); S = spreads(R, 2, mut=mut)
    pre = S[S["持有週"] <= "2020-08-30"]; post = S[S["持有週"] >= "2020-09-06"]
    return bool((pre["幣數"] == 5).all() and (post["幣數"] == 6).all() and len(pre) > 0)


def fx_c(mut=None):
    """c. 5 幣時前 2／後 2 不重疊、中位數不算。"""
    R = _synR(late="2030-01-01"); S = spreads(R, 1, mut=mut)
    r = S.iloc[5]
    hi, lo = set(r["前段"].split("、")), set(r["後段"].split("、"))
    return bool(len(hi) == 2 and len(lo) == 2 and not (hi & lo) and r["幣數"] == 5)


def run_fixtures():
    res = []
    for name, fx, mut, why in (("a 排名只用 t 以前", fx_a, "leak", "分數含 t＋1 週"), ("b 新幣上市前不入排名", fx_b, "fill0", "缺值補 0"),
                               ("c 5 幣時前 2／後 2 不重疊", fx_c, "median", "中位數重複計入")):
        g = fx(); red = not fx(mut)
        res.append({"案": name, "結果": "綠" if g else "紅", "反例": why, "反例結果": "紅（抓得到）" if red else "⛔ 仍綠"})
    return all(r["結果"] == "綠" and r["反例結果"].startswith("紅") for r in res), res


def ref_spreads(R, L):
    """純迴圈參考實作。"""
    out = []
    idx = list(R.index)
    for i in range(L, len(idx) - 1):
        if not (W0 <= idx[i + 1] <= W1):
            continue
        sc = {}
        for c in COINS:
            vals = [R.iloc[j][c] for j in range(i - L + 1, i + 1)]
            nx = R.iloc[i + 1][c]
            if all(np.isfinite(v) for v in vals) and np.isfinite(nx):
                sc[c] = (sum(vals), nx)
        if len(sc) < 4:
            continue
        o = sorted(sc, key=lambda c: -sc[c][0])
        out.append((idx[i + 1], (sc[o[0]][1] + sc[o[1]][1]) / 2 - (sc[o[-1]][1] + sc[o[-2]][1]) / 2))
    return out


# ───────────────────────── 描述①：0.2 倍放最強幣 ─────────────────────────
def coin_daily(sym, dates):
    """日曆 dates 上的合約價：永續上市後用永續（open、close、標記價日低、前日標記收盤、f0／f1），之前用現貨（無資金費）。"""
    sp = daily_pub(sym).set_index("date").reindex(dates)
    m = C11.load_main(sym)
    pm = pd.DataFrame({"open": m["open"], "close": m["close"], "low": m["mlow"], "mclose": m["mclose"], "f0": m["f0"], "f1": m["f1"]}, index=m["dates"]).reindex(dates)
    isp = pm["close"].notna().to_numpy()
    o = np.where(isp, pm["open"], sp["open"]); c = np.where(isp, pm["close"], sp["close"]); lo = np.where(isp, pm["low"], sp["low"])
    mc = np.where(isp, pm["mclose"], sp["close"]); f0 = np.where(isp, pm["f0"], 0.0); f1 = np.where(isp, pm["f1"], 0.0)
    assert np.isfinite(c).all() and np.isfinite(o).all() and np.isfinite(lo).all(), sym
    return {"open": o, "close": c, "low": lo, "mclose": mc, "f0": f0, "f1": f1, "perp": isp}


def run_extra(Dd, dates, R, L, m, mode, extra=EXTRA, cost=C10.COST_SIDE):
    """mode：top1｜equal｜hold。回 (期末組合值/起點, 各幣期末幣數/起點, 強平清單)。"""
    T = len(dates); W = {}; N = {s: 0.0 for s in COINS}; Pe = {s: 1.0 for s in COINS}; alive = {s: True for s in COINS}; liqs = []
    c0 = {s: Dd[s]["close"][0] for s in COINS}
    for s in COINS:
        W[s] = 1.0 / c0[s]                                   # 每幣 1 美元
    W0_ = dict(W)
    target = {s: 0.0 for s in COINS}; pend = False
    widx = {d: i for i, d in enumerate(R.index)}
    for t in range(T):
        dt = dates[t]
        if t > 0:
            for s in COINS:
                if not alive[s]:
                    continue
                d = Dd[s]
                if pend:
                    if N[s] > 0:
                        W[s] -= d["f0"][t] * N[s] / d["mclose"][t - 1]
                    P = d["open"][t]
                    e = W[s] + N[s] * (1 / Pe[s] - 1 / P) if N[s] > 0 else W[s]
                    Nn = target[s]
                    W[s] = e - cost * abs(Nn - N[s]) / P; N[s] = Nn; Pe[s] = P
                    if N[s] > 0:
                        W[s] -= d["f1"][t] * N[s] / d["mclose"][t - 1]
                elif N[s] > 0:
                    W[s] -= (d["f0"][t] + d["f1"][t]) * N[s] / d["mclose"][t - 1]
                if N[s] > 0:
                    den = W[s] + N[s] / Pe[s]
                    Lp = N[s] * (1 + m) / den if den > 0 else math.inf
                    if d["low"][t] <= Lp:
                        alive[s] = False; W[s] = 0.0; N[s] = 0.0; liqs.append((s, dt))
            pend = False
        if pd.Timestamp(dt).weekday() == 6 and mode != "hold" and t < T - 1:
            V = sum((W[s] + (N[s] * (1 / Pe[s] - 1 / Dd[s]["close"][t]) if N[s] > 0 else 0.0)) * Dd[s]["close"][t] for s in COINS if alive[s])
            target = {s: 0.0 for s in COINS}
            if mode == "equal":
                al = [s for s in COINS if alive[s]]
                for s in al:
                    target[s] = extra * V / len(al)
            elif dt in widx:
                i = widx[dt]
                if i >= L - 1:
                    past = R.iloc[i - L + 1:i + 1]
                    ok = [s for s in COINS if alive[s] and past[s].notna().sum() == L]
                    if ok:
                        best = max(ok, key=lambda s: past[s].sum())
                        target[best] = extra * V
            pend = True
    endv = {s: (W[s] + (N[s] * (1 / Pe[s] - 1 / Dd[s]["close"][-1]) if N[s] > 0 else 0.0)) if alive[s] else 0.0 for s in COINS}
    V = sum(endv[s] * Dd[s]["close"][-1] for s in COINS)
    return V / 6.0, {s: endv[s] / W0_[s] for s in COINS}, liqs


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return C12.pct(x, nd)


def build_html(meta, T, Y, V4, V1, BS, EX, fx, chk):
    e = html.escape
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>六幣強幣續強</title><style>{C12.CSS}</style></head><body><main>"]
    h.append("<h1>六幣之內：強幣下週還強嗎？</h1>")
    h.append(f"<div class='sub'>PREREGC14 v1（N＝4）｜回測線｜Liu, Tsyvinski & Wu（2022, JF）參數｜持有週 {W0}～{W1}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             "<div class='small'>MDE 約 1.13%／週；論文全市場效果 4.1%／週；6 大幣內依構造，只有大效果判得出。⛔ 出口②也不是「每週換到最強幣」的建議；出口①只代表「6 幣內測不出」。</div></div>")
    h.append("<div class='card'><b>怎麼測</b>：每個週日 UTC 收盤，依過去 L 週（L＝1～4）報酬把可排名的幣排序，看下一週「前 2 名平均 − 後 2 名平均」（對數週報酬、同權）。"
             "2019 年 4 幣、2019-07 加 DOGE、2020-08 加 SOL。CI：block bootstrap 2,000 次、信賴水準 1−0.05/4。</div>")
    h.append("<h2>一、判定（6 幣、前 2 − 後 2）</h2><div class='tw'><table><tr><th>L</th><th>週數</th><th>週平均價差［CI］</th><th>前段勝出週比例</th><th>出口</th></tr>")
    for _, r in T.iterrows():
        cls = "pass" if r["出口"] == "出口②" else ("narrow" if r["出口"] == "出口③" else "")
        h.append(f"<tr><td>{r.L}</td><td>{r.週數}</td><td>{r.平均價差 * 100:+.2f}%［{r.CI下 * 100:+.2f}%～{r.CI上 * 100:+.2f}%］</td><td>{pct(r.正價差比例)}</td><td class='{cls}'>{r.出口}</td></tr>")
    h.append("</table></div>")
    h.append("<h2>二、描述（不判）</h2><h3>逐年價差（6 幣，前 2 − 後 2）</h3><div class='tw'><table><tr><th>L</th>" + "".join(f"<th>{y}</th>" for y in Y.columns) + "</tr>")
    for L in LS:
        h.append(f"<tr><td>{L}</td>" + "".join(f"<td>{Y.loc[L, y] * 100:+.2f}%</td>" for y in Y.columns) + "</tr>")
    h.append("</table></div>")
    h.append("<h3>其他版本（只描述）</h3><div class='tw'><table><tr><th>L</th><th>4 幣（排除 SOL、DOGE）前 2 − 後 2</th><th>6 幣 前 1 − 後 1</th></tr>")
    for L in LS:
        a, b = V4[L], V1[L]
        h.append(f"<tr><td>{L}</td><td>{a[0] * 100:+.2f}%（{a[1]} 週）</td><td>{b[0] * 100:+.2f}%（{b[1]} 週）</td></tr>")
    h.append("</table></div>")
    h.append(f"<h3>BTC 對 SOL（上週誰強，下週是否仍強）</h3><div class='card'>{e(BS)}</div>")
    h.append("<h3>「多開 0.2 倍放最強幣」vs「平分給 6 幣」vs「只存幣」（只描述、⛔ 不是倍數建議）</h3>"
             "<div class='small'>2020-08-16 起各幣等美元；每週日收盤排名、週一開盤調整；各幣逐倉、保證金＝該幣全部持幣；永續上市前用現貨代理、不計資金費。數字＝期末組合美元值 ÷ 起點（m＝1%）；強平欄列 0.5／1／2% 的情形。</div>")
    h.append("<div class='tw'><table><tr><th>L</th><th>放最強幣</th><th>平分</th><th>只存幣</th><th>放最強幣的強平</th></tr>")
    for L in LS:
        g = EX[(EX.L == L)]
        a = g[(g["mode"] == "top1") & (g.MMR == 0.01)].iloc[0]; b = g[(g["mode"] == "equal") & (g.MMR == 0.01)].iloc[0]; c = g[(g["mode"] == "hold")].iloc[0]
        lq = "；".join(f"m{r.MMR * 100:g}%：{r.強平 or '無'}" for r in g[g["mode"] == "top1"].itertuples())
        h.append(f"<tr><td>{L}</td><td>{a.期末倍數:.2f}</td><td>{b.期末倍數:.2f}</td><td>{c.期末倍數:.2f}</td><td style='white-space:normal'>{e(lq)}</td></tr>")
    h.append("</table></div><div class='small'>平分臂每幣名目＝0.2 × 組合值 ÷ 6（不是各幣自己的 0.2 倍）；組合裡漲多的幣佔比變大後，其他幣的名目相對自己的持幣變大，所以平分臂也會強平。平分臂的強平：" + e("；".join(f"L{r.L} m{r.MMR * 100:g}%：{r.強平}" for r in EX[(EX["mode"] == "equal") & (EX["強平"] != "")].itertuples()) or "無") + "。各幣期末幣數見 extra_0p2.csv。</div>")
    h.append("<h2>三、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>四、驗證</h2><div class='tw'><table><tr><th>fixture</th><th>結果</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td>{e(r['案'])}</td><td>{r['結果']}</td><td>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>參考實作重算價差：{e(str(chk.get('價差重算', '—')))}；描述①引擎閘門：{e(str(chk.get('引擎閘門', '—')))}。</div>")
    h.append("<h2>五、讀的時候要注意</h2><ul><li>只有 4～6 個幣，前 2／後 2 的價差雜訊大；判不出不代表沒有。</li><li>價格源：交易所現貨（同 C13）；週切點 W-SUN。</li>"
             "<li>描述①的「放最強幣」會讓那一幣的名目相對它自己的持幣很大，逐倉下強平風險集中在那一幣。</li><li>⛔ 不提供倍數或換幣建議。</li></ul>")
    h.append("<h2>六、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in EXEC_SUPPLIED) + "</ul></main></body></html>")
    return "\n".join(h)


EXEC_SUPPLIED = [
    "P4 樣本外窗以持有週（t＋1 週）落在 2019-01-06～2026-09-27 定，對上登錄的 404 週",
    "P6① 起點 2020-08-16 各幣等美元；週一開盤用 C10 再平衡寫法調名目；各幣逐倉、保證金＝該幣全部持幣，強平＝該幣歸零後不再參與；平分臂只分給還沒強平的幣",
    "P6① 永續上市前用現貨代理（不計資金費），上市後用永續成交價、標記價日低、資金費（00:00 歸屬同 C11 S6）",
    "P6② BTC 對 SOL 用 L＝1（上週）",
    "P6① 平分臂每幣名目＝0.2 × 組合值 ÷ 6（照登錄「0.2 倍平均分給 6 幣」字面），不是各幣自己 E1.2；持幣比例漂移後各幣實際槓桿不同",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['結果']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    daily = {s: daily_pub(s) for s in COINS}; R = weekly_table(daily)
    dates = pd.date_range(D1_START, "2026-09-30").strftime("%Y-%m-%d").to_numpy()
    Dd = {s: coin_daily(s, dates) for s in COINS}
    if a.check:
        res = []
        for L in LS:
            S = spreads(R, L); ref = ref_spreads(R, L)
            same = len(S) == len(ref) and all(w == x and abs(v - y) < 1e-15 for w, v, (x, y) in zip(S["持有週"], S["價差"], ref))
            res.append(f"L{L} {len(S)} 週{'一致' if same else '⛔不一致'}")
        v0, cz, _ = run_extra(Dd, dates, R, 1, 0.01, "top1", extra=0.0, cost=0.0); vh, ch, _ = run_extra(Dd, dates, R, 1, 0.01, "hold")
        gate = abs(v0 - vh) < 1e-12
        chk = {"讀法寫死": FROZEN, "fixture全過": ok, "fixture": fx, "價差重算": "；".join(res), "引擎閘門": f"名目 0 時期末值 {v0:.6f} ＝ 只存幣 {vh:.6f}：{'一致' if gate else '⛔不一致'}"}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("[check]", chk["價差重算"], "｜", chk["引擎閘門"])
        assert all("一致" in x and "不一致" not in x for x in res) and gate
        return
    rows, allS = [], []
    for L in LS:
        S = spreads(R, L); x = S["價差"].to_numpy(); lo, hi, Lb = ci_mean(x)
        ex = "出口②" if lo > 0 else ("出口③" if hi < 0 else "出口①")
        rows.append({"L": L, "週數": len(S), "首週": S["持有週"].iloc[0], "末週": S["持有週"].iloc[-1], "平均價差": float(x.mean()), "CI下": lo, "CI上": hi, "L_block": Lb,
                     "正價差比例": float((x > 0).mean()), "出口": ex})
        S["L"] = L; allS.append(S)
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    SS = pd.concat(allS); SS.to_csv(os.path.join(OUT, "weekly_spreads.csv"), index=False)
    SS["年"] = SS["持有週"].str[:4]; Y = SS.groupby(["L", "年"])["價差"].mean().unstack(); Y.to_csv(os.path.join(OUT, "yearly.csv"))
    V4 = {L: (lambda S: (float(S["價差"].mean()), len(S)))(spreads(R, L, coins=("BTC", "ETH", "BNB", "XRP"))) for L in LS}
    V1 = {L: (lambda S: (float(S["價差"].mean()), len(S)))(spreads(R, L, top=1)) for L in LS}
    # BTC 對 SOL
    bs = []
    idx = R.index.to_numpy()
    for i in range(len(idx) - 1):
        if not (W0 <= idx[i + 1] <= W1):
            continue
        a_, b_ = R.iloc[i][["BTC", "SOL"]], R.iloc[i + 1][["BTC", "SOL"]]
        if a_.notna().all() and b_.notna().all() and a_["BTC"] != a_["SOL"]:
            w, l = ("BTC", "SOL") if a_["BTC"] > a_["SOL"] else ("SOL", "BTC")
            bs.append((w, b_[w] - b_[l]))
    bsd = pd.DataFrame(bs, columns=["上週強者", "下週差"])
    BS = (f"兩幣都有資料的 {len(bsd)} 週中，上週較強者下週仍較強的比例 {pct(float((bsd['下週差'] > 0).mean()))}、下週平均差 {bsd['下週差'].mean() * 100:+.2f}%；"
          f"上週 BTC 較強 {int((bsd['上週強者'] == 'BTC').sum())} 週（下週仍強 {pct(float((bsd[bsd['上週強者'] == 'BTC']['下週差'] > 0).mean()))}），"
          f"上週 SOL 較強 {int((bsd['上週強者'] == 'SOL').sum())} 週（下週仍強 {pct(float((bsd[bsd['上週強者'] == 'SOL']['下週差'] > 0).mean()))}）。")
    ex_rows = []
    for L in LS:
        for mode in ("top1", "equal", "hold"):
            for m in (C10.MMRS if mode != "hold" else (0.01,)):
                v, cz, lq = run_extra(Dd, dates, R, L, m, mode)
                ex_rows.append({"L": L, "mode": mode, "MMR": m, "期末倍數": v, **{f"{s}幣數倍數": cz[s] for s in COINS}, "強平": "、".join(f"{s} {d}" for s, d in lq)})
    EX = pd.DataFrame(ex_rows); EX.to_csv(os.path.join(OUT, "extra_0p2.csv"), index=False)
    n2 = int((T["出口"] == "出口②").sum()); n3 = int((T["出口"] == "出口③").sum()); n1 = int((T["出口"] == "出口①").sum())
    pri = [f"① 4 個 L 全部出口①：出口① {n1}／4 ⇒ " + ("中" if n1 == 4 else "未中"), f"② 沒有出口③：出口③ {n3} 格 ⇒ " + ("中" if n3 == 0 else "未中")]
    lines = [f"4 個 L：出口② {n2}、出口③ {n3}、出口① {n1}；週平均價差 " + "、".join(f"L{r.L} {r.平均價差 * 100:+.2f}%" for r in T.itertuples()) + "。"]
    meta = {"登錄": "PREREGC14 六幣強幣續強 v1 shae312eee71dfbfaf1", "裁定": "seq298（N＝4）", "讀法寫死": FROZEN, "資料": f"公開 main {C10.SHA[:10]}",
            "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "結論行": lines, "先驗對答": pri, "BTC對SOL": BS, "4幣版": V4, "前1後1": V1,
            "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1)}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "六幣強幣續強.html"), "w", encoding="utf-8").write(build_html(meta, T, Y, V4, V1, BS, EX, fx, chk))
    import re
    print(T.round(4).to_string()); print(Y.round(4).to_string()); print("4幣", V4, "前1後1", V1); print(BS)
    print(EX[["L", "mode", "MMR", "期末倍數", "強平"]].round(3).to_string())
    for x in lines + pri:
        print(re.sub(r"<[^>]+>", "", x))
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREGC13「加密週報酬動能——Liu & Tsyvinski（2021）發表後樣本外重驗」v2（sha dd495fd671327be0）——回測線執行端。
裁定 seq296（核准 N＝24）、seq298（v2 週切點出處核准）。

⭐ 讀法寫死：2026-10-04 21:07（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何 ρ 之前寫在這裡；之後只准補「執行時發現」並標時間；週切點 ⛔ 跑後不改。
   登錄沒寫到、由回測線補的讀法標【執行者補】。
⚠ 照實標：價格 2018～2026 本專案各件都看過，週報酬自相關 ρ 從未算過（「價格看過、ρ 未算過」）；論文價格源 CoinDesk，本件用交易所現貨。

資料：公開 main 1fb8815e81 data/crypto/<SYM>.csv（git archive 唯讀副本 ~/c10data/<sha>）；BTC 2017-08-17 以前改讀私有 ~/us-stock-data data/crypto_private
   （接法照私有 README，與 researchC11.spot_full 同一條；⛔ 私有價格不進結果檔，結果只放統計量）
   其餘五幣只用公開檔（登錄 §二）：ETH 2017-08-17、BNB 2017-11-06、XRP 2018-05-04、DOGE 2019-07-05、SOL 2020-08-11 起

⭐ 落地讀法
 W1 週切點（seq296／298 寫死）：W-SUN＝週日 UTC 23:59:59 收盤＝該週日那根 UTC 日 K 的 close；週以結束的週日標記
    週日那天沒有日 K ⇒ 該週收盤缺（⛔ 不拿週六補）【執行者補】；週報酬 r_t＝ln(P_t／P_{t−7 天})，任一端缺 ⇒ 缺
 W2 樣本外窗：r_t 的週日在 2018-06-03～2026-09-27；配對 (r_t, r_{t+k}) 兩週都要在窗內【執行者補：兩端都在窗內】
    r_{t+k}＝第 k 週後【那一週】的報酬（⛔ 不是累積）；k ∈ {1、2、3、4}
 W3 判定量 ρ_k＝corr(r_t, r_{t+k})（＝β_k·sd(r_t)/sd(r_{t+k})）；另報 β_k、β_k·sd(r_t)（論文式「+1 sd ⇒ 下週 +x%」，對數報酬）、OLS t
 W4 CI：配對 stationary block bootstrap（researchc1），L＝Politis–White 套在去均值乘積 (r_t−均)(r_{t+k}−均)【執行者補：L 用哪條序列】，
    2,000 次、每格種子 20260923，每次重算相關係數；信賴水準 1−0.05/24（雙尾各 0.05/48）
 W5 出口：下界 > 0 ⇒ ②；上界 < 0 ⇒ ③；含 0 ⇒ ①。論文三幣 BTC／ETH／XRP 與延伸三幣 BNB／SOL／DOGE 分開寫；N＝24 不變
 W6 描述（不判、N＝0）：
    ① 「上週（r_t > 0）漲才多開 0.2 倍（E 1.2）、上週跌（r_t ≤ 0）就關」vs「一直開 E＝1＋0.2×在場比例、每月再平衡」：
       訊號在週日收盤、次日（週一 UTC）開盤執行（同 C11 S4／S6，直接用 researchC11.path 引擎：週日把 r_t>0 編成開倉訊號、r_t≤0 編成平倉訊號，平日中性）；
       對照臂用 researchC10.engine（每月再平衡）；兩段分開、各自從 1 顆幣起算【執行者補】：
       現貨代理段＝2018-06-03～該幣幣本位永續第一天前一日（現貨 open／low／close、⛔ 不計資金費）；合約段＝永續第一天～2026-09-30（成交價、標記價日低、資金費）
       報期末幣數、在場比例、強平與否（m 0.5／1／2%，成本 0.05% 單邊）；⛔ 不寫倍數建議
    ② 論文五分位法：r_t 落在「t 以前全部週報酬（從該幣序列起點）」的五分位，下一週平均報酬；歷史不足 52 週的 t 不算【執行者補】
    ③ 逐年（依 r_t 年份）ρ_1
    ④ 論文窗對帳：只做 BTC（登錄給了 BTC 的論文數字）：r_t 在 2011-01-01～2018-05-31，對數與簡單報酬並列 β·sd、OLS t，對照論文 3.16／3.66／3.49／1.50%（t 3.73／4.52／4.26／1.72）
       ETH／XRP 論文窗不重算（論文數字未給；XRP 2015-02 前沒有美元價）【執行者補】
 W7 先驗對答：① BTC k＝1 出口① ② 24 格中出口② ≤ 2 格 ③ 沒有任何出口③
 W8 --check：fixture a～d（登錄 §九②）各附反例：a 單週非累積（反例：累積）b W-SUN（反例：W-MON）c 樣本外首週 2018-06-03（反例：含論文窗）
    d 五分位界線只用 t 以前（反例：全期分位）；再用純迴圈參考實作重算 24 格 ρ 逐位比
⛔ 出口②也只能說「樣本外週報酬有正自相關」，⛔ 不是操作建議；出口①只能說「樣本外測不出」，⛔ 不寫「動能無效」。
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

OUT = os.path.join(C10.REPO, "backtest", "resultsC13")
PAPER = ("BTC", "ETH", "XRP")
EXT = ("BNB", "SOL", "DOGE")
COINS = PAPER + EXT
KS = (1, 2, 3, 4)
OOS0, OOS1 = "2018-06-03", "2026-09-27"
PAPER0, PAPER1 = "2011-01-01", "2018-05-31"
N_CELLS = 24
SEED = 20260923
N_BOOT = 2000
FROZEN = "2026-10-04 21:07（台北）"
PAPER_BTC = {1: (3.16, 3.73), 2: (3.66, 4.52), 3: (3.49, 4.26), 4: (1.50, 1.72)}


# ───────────────────────── 資料 ─────────────────────────
def daily(sym):
    if sym == "BTC":
        d = C11.spot_full("BTC")[["date", "open", "high", "low", "close"]]
    else:
        d = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str})[["date", "open", "high", "low", "close"]]
        d = d.drop_duplicates("date").sort_values("date")
    return d[d["date"] <= "2026-09-30"].reset_index(drop=True)


def weekly(d, rule="W-SUN"):
    """W1：週日（mut W-MON ⇒ 週一）那根日 K 的收盤；r_t＝ln(P_t/P_{t−7})，任一端缺 ⇒ NaN。回 Series（index＝週末日字串）。"""
    s = pd.Series(d["close"].to_numpy(float), index=pd.to_datetime(d["date"]))
    wd = 6 if rule == "W-SUN" else 0
    days = pd.date_range(s.index[0], s.index[-1], freq="D")
    ends = days[days.weekday == wd]
    P = s.reindex(ends)
    r = np.log(P) - np.log(P.shift(1))
    r.index = ends.strftime("%Y-%m-%d")
    return r


def pairs(r, k, lo=OOS0, hi=OOS1, mut=None):
    """W2：(r_t, r_{t+k})，兩端都在窗內且有值。mut＝cum ⇒ y 用 t+1～t+k 累積（反例）；mut＝nowin ⇒ 不限窗起點（反例）。"""
    v = r.to_numpy(float); idx = r.index.to_numpy()
    x, y, tt = [], [], []
    for i in range(len(v) - k):
        if mut != "nowin" and idx[i] < lo:
            continue
        if idx[i + k] > hi:
            break
        yy = np.nansum(v[i + 1:i + k + 1]) if mut == "cum" and np.all(np.isfinite(v[i + 1:i + k + 1])) else (v[i + k] if mut != "cum" else np.nan)
        if np.isfinite(v[i]) and np.isfinite(yy):
            x.append(v[i]); y.append(yy); tt.append(idx[i])
    return np.array(x), np.array(y), np.array(tt)


def ols(x, y):
    xm, ym = x.mean(), y.mean()
    b = float(np.sum((x - xm) * (y - ym)) / np.sum((x - xm) ** 2)); a = ym - b * xm
    e = y - a - b * x; se = math.sqrt(float(np.sum(e ** 2)) / (len(x) - 2) / float(np.sum((x - xm) ** 2)))
    return b, b / se


def ci_corr(x, y):
    z = (x - x.mean()) * (y - y.mean())
    L = C1.politis_white_block(z); rng = np.random.default_rng(SEED)
    bs = np.empty(N_BOOT)
    for i in range(N_BOOT):
        j = C1.stationary_idx(len(x), L, rng); bs[i] = np.corrcoef(x[j], y[j])[0, 1]
    a = 0.05 / N_CELLS / 2
    return float(np.percentile(bs, 100 * a)), float(np.percentile(bs, 100 * (1 - a))), int(L)


def quintile_desc(r, mut=None, min_hist=52):
    """W6②：r_t 在 t 以前歷史的五分位 ⇒ 下一週平均報酬。mut＝full ⇒ 全期界線（反例）。"""
    v = r.to_numpy(float); idx = r.index.to_numpy(); allv = v[np.isfinite(v)]
    buck = {q: [] for q in range(5)}; qs = []
    for i in range(len(v) - 1):
        if idx[i] < OOS0 or idx[i + 1] > OOS1 or not (np.isfinite(v[i]) and np.isfinite(v[i + 1])):
            continue
        hist = allv if mut == "full" else v[:i][np.isfinite(v[:i])]
        if len(hist) < min_hist:
            continue
        cuts = np.percentile(hist, [20, 40, 60, 80])
        q = int(np.searchsorted(cuts, v[i], side="right")); buck[q].append(v[i + 1]); qs.append((idx[i], q, tuple(cuts)))
    return {q: (float(np.mean(b)) if b else float("nan"), len(b)) for q, b in buck.items()}, qs


# ───────────────────────── fixture ─────────────────────────
def _syn():
    dates = pd.date_range("2017-01-01", "2026-09-30").strftime("%Y-%m-%d")
    rng = np.random.default_rng(3); c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, len(dates))))
    return pd.DataFrame({"date": dates, "open": c, "high": c, "low": c, "close": c})


def fx_a(mut=None):
    """a. r_{t+k} 是第 k 週後那一週的單週報酬：y 必須等於 r 往後移 k 週。"""
    r = weekly(_syn()); x, y, tt = pairs(r, 3, mut=mut)
    i = int(np.flatnonzero(r.index == tt[10])[0])
    return bool(abs(y[10] - r.iloc[i + 3]) < 1e-15)


def fx_b(rule="W-SUN"):
    """b. 週切點 W-SUN：週收盤＝週日日 K 收盤（UTC）；週一切點的反例要變紅。"""
    d = _syn(); r = weekly(d, rule)
    t = r.index[200]; ok = pd.Timestamp(t).weekday() == 6
    p = d.set_index("date")["close"]; prev = (pd.Timestamp(t) - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    return bool(ok and abs(r.loc[t] - math.log(p[t] / p[prev])) < 1e-15)


def fx_c(mut=None):
    """c. 樣本外首週＝2018-06-03（第一個 r_t 的週日）；反例把論文窗也納入。"""
    x, y, tt = pairs(weekly(_syn()), 1, mut=mut)
    return bool(tt[0] == "2018-06-03")


def fx_d(mut=None):
    """d. 五分位界線只用 t 以前：把樣本外窗之後才出現的極端值改掉，界線不能變。"""
    d = _syn(); r = weekly(d); r2 = r.copy(); r2.iloc[-60:] = r2.iloc[-60:] * 25
    _, q1 = quintile_desc(r, mut); _, q2 = quintile_desc(r2, mut)
    a = {t: c for t, _, c in q1}; b = {t: c for t, _, c in q2}
    t0 = sorted(a)[100]
    return bool(np.allclose(a[t0], b[t0], rtol=0, atol=0))


def run_fixtures():
    res = []
    for name, fx, mut, why in (("a r_{t+k} 單週", fx_a, "cum", "用 t+1～t+k 累積"), ("b 週切點 W-SUN", fx_b, "W-MON", "週一切點"),
                               ("c 樣本外首週 2018-06-03", fx_c, "nowin", "含論文窗"), ("d 五分位界線只用 t 以前", fx_d, "full", "全期分位")):
        g = fx() if name[0] != "b" else fx("W-SUN"); red = not (fx(mut))
        res.append({"案": name, "結果": "綠" if g else "紅", "反例": why, "反例結果": "紅（抓得到）" if red else "⛔ 仍綠"})
    return all(r["結果"] == "綠" and r["反例結果"].startswith("紅") for r in res), res


# ───────────────────────── 描述①：多開 0.2 倍 ─────────────────────────
def sig_dd(dates, r):
    """週日：r_t>0 ⇒ −1（開）、r_t≤0 或缺 ⇒ 0（關）；平日 −0.4（中性）。配 D＝0.5、X＝0.25。"""
    rr = r.to_dict(); out = np.full(len(dates), -0.4)
    for i, dt in enumerate(dates):
        if pd.Timestamp(dt).weekday() == 6:
            v = rr.get(dt, np.nan)
            out[i] = -1.0 if (np.isfinite(v) and v > 0) else 0.0
    return out


def seg_spot(sym, d0, d1):
    d = daily(sym); d = d[(d["date"] >= d0) & (d["date"] <= d1)].reset_index(drop=True); n = len(d)
    return {"sym": sym, "dates": d["date"].to_numpy(), "close": d["close"].to_numpy(float), "open": d["open"].to_numpy(float),
            "tlow": d["low"].to_numpy(float), "mlow": d["low"].to_numpy(float), "mclose": d["close"].to_numpy(float),
            "f0": np.zeros(n), "f1": np.zeros(n), "fsum": np.zeros(n)}


def desc_extra(sym, r):
    out = []
    main = C11.load_main(sym)
    p0 = main["dates"][0]
    segs = []
    if OOS0 < p0:
        segs.append(("現貨代理段（不計資金費）", seg_spot(sym, max(OOS0, daily(sym)["date"].iloc[0]), (pd.Timestamp(p0) - pd.Timedelta(days=1)).strftime("%Y-%m-%d"))))
    segs.append(("合約段（幣本位、標記價）", main))
    for name, d in segs:
        d = dict(d); d["dd"] = sig_dd(d["dates"], r)
        for m in C10.MMRS:
            p = C11.path(d, d["mlow"], 1.2, 0.5, 0.25, m, C10.COST_SIDE, want_eq=True)
            held = np.zeros(len(d["dates"]), bool)
            for sg in p["segs"]:
                a = int(np.flatnonzero(d["dates"] == sg["開倉日"])[0]); b = int(np.flatnonzero(d["dates"] == sg["平倉日"])[0]) if sg["平倉日"] else len(held)
                held[a:b] = True
            share = float(held.mean())
            Ec = 1 + 0.2 * share
            liq, eq, _, _ = C10.engine(d["close"], d["mlow"], d["mclose"], d["fsum"], C10.rebal_mask(d["dates"], "monthly"), np.array([0]),
                                       np.array([Ec - 1]), np.array([m]), np.array([C10.COST_SIDE]), want_eq=True)
            out.append({"coin": sym, "段": name, "起": d["dates"][0], "迄": d["dates"][-1], "MMR": m, "在場比例": share, "進出次數": len(p["segs"]),
                        "訊號臂期末幣數": p["coins"], "訊號臂強平日": d["dates"][p["liq"]] if p["liq"] >= 0 else "",
                        "固定臂E": Ec, "固定臂期末幣數": float(eq[0, -1]), "固定臂強平日": d["dates"][liq[0]] if liq[0] >= 0 else ""})
    return out


# ───────────────────────── --check 參考實作 ─────────────────────────
def ref_rho(d, k):
    """純迴圈：從日 K 逐日找週日收盤、算 r、配對、算相關。"""
    cl = dict(zip(d["date"], d["close"]))
    t = pd.Timestamp(OOS0); r = {}
    day = pd.Timestamp(d["date"].iloc[0])
    while day.weekday() != 6:
        day += pd.Timedelta(days=1)
    while day <= pd.Timestamp(OOS1):
        a, b = day.strftime("%Y-%m-%d"), (day - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        if a in cl and b in cl:
            r[a] = math.log(cl[a] / cl[b])
        day += pd.Timedelta(days=7)
    xs, ys = [], []
    for a, v in r.items():
        if a < OOS0:
            continue
        b = (pd.Timestamp(a) + pd.Timedelta(days=7 * k)).strftime("%Y-%m-%d")
        if b in r and b <= OOS1:
            xs.append(v); ys.append(r[b])
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((p - mx) * (q - my) for p, q in zip(xs, ys)); vx = sum((p - mx) ** 2 for p in xs); vy = sum((q - my) ** 2 for q in ys)
    return cov / math.sqrt(vx * vy), n


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return C12.pct(x, nd)


def build_html(meta, T, Q, Y, P4, X1, fx, chk):
    e = html.escape
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>週動能樣本外</title><style>{C12.CSS}</style></head><body><main>"]
    h.append("<h1>加密週報酬動能：論文發表後的樣本外重驗</h1>")
    h.append(f"<div class='sub'>PREREGC13 v2（N＝24）｜回測線｜Liu & Tsyvinski（2021, RFS）｜樣本外 {OOS0}～{OOS1}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             "<div class='small'>⚠ 價格看過、ρ 未算過。論文價格源 CoinDesk，本件用交易所現貨。⛔ 出口②也只代表「樣本外週報酬有正自相關」，不是操作建議；出口①只代表「樣本外測不出」。</div></div>")
    h.append("<div class='card'><b>怎麼測</b>：週＝週日 UTC 23:59:59 收盤（論文 Table 14 的切法）。r_t＝當週對數報酬；看 r_t 和第 k 週後<b>那一週</b>報酬 r_{t+k} 的相關係數 ρ_k（k＝1～4，論文的四個週距）。"
             "CI：配對 block bootstrap 2,000 次、信賴水準 1−0.05/24。下界 > 0 ⇒ 出口②（樣本外仍有動能）；上界 < 0 ⇒ 出口③（反轉）；含 0 ⇒ 出口①（測不出）。</div>")
    for grp, title in ((PAPER, "一、論文三幣（BTC、ETH、XRP）"), (EXT, "二、延伸三幣（BNB、SOL、DOGE；論文沒測）")):
        h.append(f"<h2>{title}</h2><div class='tw'><table><tr><th>幣（週數）</th><th>k</th><th>ρ_k［CI］</th><th>+1 sd ⇒ 第 k 週</th><th>出口</th></tr>")
        for s in grp:
            for k in KS:
                r = T[(T.coin == s) & (T.k == k)].iloc[0]
                cls = "pass" if r["出口"] == "出口②" else ("narrow" if r["出口"] == "出口③" else "")
                h.append(f"<tr><td>{s}（{int(r['配對數'])}）</td><td>{k}</td><td>{r['rho']:+.3f}［{r['CI下']:+.3f}～{r['CI上']:+.3f}］</td><td>{r['beta_sd'] * 100:+.2f}%</td><td class='{cls}'>{r['出口']}</td></tr>")
        h.append("</table></div>")
    h.append("<h2>三、描述（不判）</h2><h3>論文窗對帳（BTC 2011-01～2018-05）</h3><div class='small'>驗證本線實作，不入判定。論文：+1 sd ⇒ 第 1～4 週 +3.16／3.66／3.49／1.50%（t 3.73／4.52／4.26／1.72）。BTC 2011 年是 Mt.Gox（第三方鏡像）。</div>")
    h.append("<div class='tw'><table><tr><th>k</th><th>對數：+1 sd ⇒（t）</th><th>簡單報酬：+1 sd ⇒（t）</th><th>論文</th><th>ρ</th><th>配對數</th></tr>")
    for _, r in P4.iterrows():
        h.append(f"<tr><td>{r.k}</td><td>{r.log_beta_sd * 100:+.2f}%（{r.log_t:.2f}）</td><td>{r.simple_beta_sd * 100:+.2f}%（{r.simple_t:.2f}）</td><td>+{PAPER_BTC[r.k][0]:.2f}%（{PAPER_BTC[r.k][1]:.2f}）</td><td>{r.rho:+.3f}</td><td>{r.n}</td></tr>")
    h.append("</table></div>")
    h.append("<h3>論文五分位法（樣本外；界線只用 t 以前）</h3><div class='small'>r_t 落在自己歷史的第幾個五分位 ⇒ 下一週平均對數報酬（括號＝週數）。</div><div class='tw'><table><tr><th>幣</th>" + "".join(f"<th>Q{q + 1}</th>" for q in range(5)) + "</tr>")
    for s in COINS:
        g = Q[s]
        h.append(f"<tr><td>{s}</td>" + "".join(f"<td>{g[q][0] * 100:+.2f}%（{g[q][1]}）</td>" for q in range(5)) + "</tr>")
    h.append("</table></div>")
    h.append("<h3>逐年 ρ_1</h3><div class='tw'><table><tr><th>幣</th>" + "".join(f"<th>{y}</th>" for y in sorted(Y.columns)) + "</tr>")
    for s in COINS:
        h.append(f"<tr><td>{s}</td>" + "".join(f"<td>{Y.loc[s, y]:+.2f}</td>" if np.isfinite(Y.loc[s, y]) else "<td>—</td>" for y in sorted(Y.columns)) + "</tr>")
    h.append("</table></div>")
    h.append("<h3>「上週漲才多開 0.2 倍」vs「一直開同平均曝險」（只描述、⛔ 不是倍數建議）</h3><div class='small'>各段各自從 1 顆幣起算；m＝1% 的期末幣數，強平欄列出 0.5／1／2% 有強平的。現貨代理段不計資金費。</div>")
    h.append("<div class='tw'><table><tr><th>幣</th><th>段</th><th>在場比例</th><th>訊號臂期末幣數</th><th>固定臂（E）期末幣數</th><th>強平</th></tr>")
    for (s, seg), g in X1.groupby(["coin", "段"], sort=False):
        r = g[g.MMR == 0.01].iloc[0]
        lq = "；".join([f"m{m * 100:g}% 訊號臂 {a}" for m, a in zip(g.MMR, g["訊號臂強平日"]) if a] + [f"m{m * 100:g}% 固定臂 {b}" for m, b in zip(g.MMR, g["固定臂強平日"]) if b])
        h.append(f"<tr><td>{s}</td><td>{e(seg)}<br><span class='small'>{r['起']}～{r['迄']}</span></td><td>{pct(r['在場比例'])}</td><td>{r['訊號臂期末幣數']:.3f}</td><td>{r['固定臂期末幣數']:.3f}（E{r['固定臂E']:.3f}）</td><td>{e(lq) or '無'}</td></tr>")
    h.append("</table></div>")
    h.append("<h2>四、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>五、驗證</h2><div class='tw'><table><tr><th>fixture</th><th>結果</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td>{e(r['案'])}</td><td>{r['結果']}</td><td>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>參考實作重算 24 格 ρ：{chk.get('一致數', '—')}／{chk.get('抽樣數', '—')} 一致。</div>")
    h.append("<h2>六、讀的時候要注意</h2><ul><li>N＝24，可判出的最小相關約 0.15～0.17；論文效果若衰退一半，依構造測不出。</li><li>價格源與論文不同（交易所現貨 vs CoinDesk）。</li>"
             "<li>BTC 2017-08 以前（只用於論文窗對帳與五分位歷史）來自私有庫，結果檔只放統計量。</li><li>⛔ 不得寫成「上週漲就買」；⛔ 不提供倍數建議。</li></ul>")
    h.append("<h2>七、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in EXEC_SUPPLIED) + "</ul></main></body></html>")
    return "\n".join(h)


EXEC_SUPPLIED = [
    "W1 週日沒有日 K ⇒ 該週收盤缺，不拿週六補",
    "W2 配對 (r_t, r_{t+k}) 兩週都要在樣本外窗內",
    "W4 bootstrap 區塊長 L 用去均值乘積序列算 Politis–White",
    "W6① 兩段分開、各從 1 顆幣起算；訊號臂用 C11 引擎（週日收盤判、週一開盤執行），固定臂用 C10 引擎每月再平衡",
    "W6② 五分位歷史不足 52 週的起點不算",
    "W6④ 論文窗只對帳 BTC（ETH／XRP 論文數字未給，XRP 2015-02 前沒有美元價）",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['結果']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    D = {s: daily(s) for s in COINS}; R = {s: weekly(D[s]) for s in COINS}
    for s in COINS:
        x, y, tt = pairs(R[s], 1)
        print(f"[{s}] 日K {D[s]['date'].iloc[0]}～{D[s]['date'].iloc[-1]}｜樣本外 r_t 首週 {tt[0]}｜k1 配對 {len(x)}")
    if a.check:
        rows = []
        for s in COINS:
            for k in KS:
                x, y, _ = pairs(R[s], k); rho = float(np.corrcoef(x, y)[0, 1]); rr, n = ref_rho(D[s], k)
                rows.append({"coin": s, "k": k, "引擎": rho, "參考": rr, "n": [len(x), n], "一致": bool(abs(rho - rr) < 1e-12 and len(x) == n)})
        chk = {"讀法寫死": FROZEN, "fixture全過": ok, "fixture": fx, "抽樣數": len(rows), "一致數": int(sum(r["一致"] for r in rows)), "抽樣": rows}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"[check] 24 格 ρ 參考重算 {chk['一致數']}／{chk['抽樣數']} 一致")
        assert chk["一致數"] == chk["抽樣數"]
        return
    rows = []
    for s in COINS:
        for k in KS:
            x, y, tt = pairs(R[s], k)
            rho = float(np.corrcoef(x, y)[0, 1]); b, tv = ols(x, y); lo, hi, L = ci_corr(x, y)
            ex = "出口②" if lo > 0 else ("出口③" if hi < 0 else "出口①")
            rows.append({"coin": s, "組": "論文三幣" if s in PAPER else "延伸三幣", "k": k, "配對數": len(x), "首週": tt[0], "末週": tt[-1],
                         "rho": rho, "CI下": lo, "CI上": hi, "L": L, "beta": b, "beta_sd": b * float(np.std(x, ddof=1)), "OLS_t": tv, "出口": ex})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    Q = {s: quintile_desc(R[s])[0] for s in COINS}
    pd.DataFrame([{"coin": s, "Q": q + 1, "下週平均": Q[s][q][0], "週數": Q[s][q][1]} for s in COINS for q in range(5)]).to_csv(os.path.join(OUT, "quintile.csv"), index=False)
    yr = {}
    for s in COINS:
        x, y, tt = pairs(R[s], 1); df = pd.DataFrame({"x": x, "y": y, "yr": [t[:4] for t in tt]})
        yr[s] = {g: (float(np.corrcoef(v.x, v.y)[0, 1]) if len(v) > 10 else float("nan")) for g, v in df.groupby("yr")}
    Y = pd.DataFrame(yr).T; Y.to_csv(os.path.join(OUT, "yearly_rho1.csv"))
    p4 = []
    db = D["BTC"]; rl = R["BTC"]
    s_ = pd.Series(db["close"].to_numpy(float), index=pd.to_datetime(db["date"]))
    for k in KS:
        x, y, tt = pairs(rl, k, lo="2011-01-01", hi=PAPER1)
        xs, ys = np.expm1(x), np.expm1(y)
        bl, tl = ols(x, y); bs_, ts_ = ols(xs, ys)
        p4.append({"k": k, "n": len(x), "首週": tt[0], "末週": tt[-1], "rho": float(np.corrcoef(x, y)[0, 1]), "log_beta_sd": bl * float(np.std(x, ddof=1)), "log_t": tl,
                   "simple_beta_sd": bs_ * float(np.std(xs, ddof=1)), "simple_t": ts_})
    P4 = pd.DataFrame(p4); P4.to_csv(os.path.join(OUT, "paper_window_btc.csv"), index=False)
    X1 = pd.DataFrame([row for s in COINS for row in desc_extra(s, R[s])]); X1.to_csv(os.path.join(OUT, "extra_0p2.csv"), index=False)
    # 先驗與結論
    b1 = T[(T.coin == "BTC") & (T.k == 1)].iloc[0]
    n2 = int((T["出口"] == "出口②").sum()); n3 = int((T["出口"] == "出口③").sum())
    pri = [f"① BTC k＝1 出口①：ρ＝{b1.rho:+.3f}［{b1.CI下:+.3f}～{b1.CI上:+.3f}］⇒ {b1.出口} ⇒ " + ("中" if b1.出口 == "出口①" else "未中"),
           f"② 24 格中出口② ≤ 2 格：出口② {n2} 格 ⇒ " + ("中" if n2 <= 2 else "未中"),
           f"③ 沒有任何出口③：出口③ {n3} 格 ⇒ " + ("中" if n3 == 0 else "未中")]
    lines = []
    for grp, nm in ((PAPER, "論文三幣"), (EXT, "延伸三幣")):
        g = T[T.coin.isin(grp)]
        lines.append(f"<b>{nm}</b>：12 格中 出口② {int((g.出口 == '出口②').sum())}、出口③ {int((g.出口 == '出口③').sum())}、出口① {int((g.出口 == '出口①').sum())}；ρ 範圍 {g.rho.min():+.3f}～{g.rho.max():+.3f}。")
    lines.append(f"BTC k＝1 樣本外 ρ＝{b1.rho:+.3f}（+1 sd ⇒ 下週 {b1.beta_sd * 100:+.2f}%）；論文窗本線重算 +1 sd ⇒ {P4.iloc[0].log_beta_sd * 100:+.2f}%（論文 +3.16%）。")
    meta = {"登錄": "PREREGC13 週動能樣本外 v2 shadd495fd671327be0", "裁定": "seq296、seq298（N＝24）", "讀法寫死": FROZEN, "資料": f"公開 main {C10.SHA[:10]}＋BTC 2017-08 前私有庫",
            "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "結論行": lines, "先驗對答": pri, "fixture": fx, "執行者補": EXEC_SUPPLIED,
            "耗時秒": round(time.time() - t0, 1)}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "週動能樣本外.html"), "w", encoding="utf-8").write(build_html(meta, T, Q, Y, P4, X1, fx, chk))
    import re
    print(T[["coin", "k", "配對數", "rho", "CI下", "CI上", "beta_sd", "出口"]].round(4).to_string())
    print(P4.round(4).to_string())
    for x in lines + pri:
        print(re.sub(r"<[^>]+>", "", x))
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

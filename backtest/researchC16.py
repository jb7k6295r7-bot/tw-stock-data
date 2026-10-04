# -*- coding: utf-8 -*-
"""PREREGC16「BTC 恐懼貪婪指數——『極度恐懼時買』是否成立？」v1（sha 3f217df7c47ad189）——回測線執行端。裁定 seq299 §二：核准，N＝3，雙向判。

⭐ 讀法寫死：2026-10-04 23:35（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何相關係數之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法標【執行者補】。
   寫死前已看過的：資料檔頭尾幾列與 classification 各類天數（只為確認欄位；未碰任何報酬）。
⭐ Fear & Greed Index 資料來源：Alternative.me（條款：須明確標示來源）。⚠ 指數含價格成分（動能、波動度、成交量等；裁定 seq299）。

資料：私有 ~/us-stock-data data/crypto_private/fng/fng_btc_daily.csv（commit 8d1de6fd 落地；資料庫 1004-2247；date_utc,value,classification；
   2018-02-01～2026-10-04；缺 2018-04-14～16、2024-10-26 四天，API 本來就沒有，⛔ 不補）；BTC 現貨日 K：公開 main 1fb8815e81 data/crypto/BTC.csv
   ⛔ 私有資料不外流：結果檔只放統計量（相關、比例、平均、逐年分布摘要），⛔ 不放逐日指數列

⭐ 落地讀法
 G1 訊號 G_t＝UTC 日 t 的指數值（0～100，原樣、不平滑）；當日值只配「t 日收盤之後」的報酬（登錄 §二）
 G2 結果 R_t＝ln(C_{t+h}／C_t)，C＝BTC 現貨 UTC 日收盤；h ∈ {7、14、30}
 G3 起點：指數首日 2018-02-01 起每 h 天一個（日曆，不重疊），t＋h ≤ 2026-09-30；起點那天指數缺 ⇒ 該起點不算（⛔ 不補值）【執行者補】
 G4 判定量 ρ_h＝corr(G_t, R_t)
 G5 CI：同 C15——配對 stationary block bootstrap，區塊長＝max(Politis–White(去均值乘積), 1) 個起點（＝至少 h 天，符合 seq299「block ≥ H」），
    2,000 次、每格種子 20260923，信賴水準 1−0.05/3
 G6 出口（雙向）：② 上界 < 0（逆勢說法：越恐懼之後越好）｜③ 下界 > 0（順勢：越貪婪之後越好）｜① 含 0
 G7 描述（不判）：
    ① 逐年指數分布（平均、標準差、各分級天數比例）——檢查改算法跡象
    ② 「極度恐懼」日 vs「極度貪婪」日（API 自帶分級）：之後 h 天平均報酬、上漲比例、天數（每日都算、重疊，只描述）
    ③ C11 BTC：「只在極度恐懼日開」＝C11 的開倉條件再加「當天分級是 Extreme Fear」，平倉照 C11；指數缺的日子當作不是極度恐懼【執行者補：解讀成濾網（且）】；
       報期末幣數與強平（m 0.5／1／2%、標記價），與原 C11 並列
 G8 先驗對答：① 3 格全出口① ② h30 點估計為負
 G9 --check：fixture a 指數時點不早於 BTC 收盤（反例：用 t＋1 的值）、b 缺日不補（反例：前值補）；純迴圈參考實作重算 3 格 ρ 逐位比
⛔ 不寫「極度恐懼就買」；⛔ 任何倍數建議都不寫。
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
import researchC15 as C15

OUT = os.path.join(C10.REPO, "backtest", "resultsC16")
FNG = os.path.expanduser("~/us-stock-data/data/crypto_private/fng/fng_btc_daily.csv")
HS = (7, 14, 30)
T0, TEND = "2018-02-01", "2026-09-30"
N_CELLS = 3
SEED = 20260923
N_BOOT = 2000
SRC = "Fear & Greed Index 資料來源：Alternative.me"
FROZEN = "2026-10-04 23:35（台北）"


def load_fng():
    f = pd.read_csv(FNG, dtype={"date_utc": str})
    assert list(f.columns) == ["date_utc", "value", "classification"]
    assert not f["date_utc"].duplicated().any()
    return f.sort_values("date_utc").reset_index(drop=True)


def spot():
    d = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto", "BTC.csv"), dtype={"date": str}).drop_duplicates("date").sort_values("date")
    d = d[(d["date"] >= "2018-01-01") & (d["date"] <= TEND)].reset_index(drop=True)
    assert (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1 == len(d)
    return d


def align(f, days, mut=None):
    """G1：G[t]＝當天值；缺 ⇒ NaN。mut：next（用 t＋1 的值；反例）｜ffill（缺值用前值補；反例）。"""
    s = f.set_index("date_utc")["value"].astype(float).reindex(days)
    if mut == "next":
        s = s.shift(-1)
    if mut == "ffill":
        s = s.ffill()
    return s.to_numpy()


def starts(days, h):
    d = list(days); i0 = d.index(T0); out = []
    for i in range(i0, len(d) - h, h):
        if d[i + h] > TEND:
            break
        out.append(i)
    return np.array(out, int)


# ───────────────────────── fixture ─────────────────────────
def fx_a(mut=None):
    """a. 指數時點不早於 BTC 收盤：t 日起點配的必須是 t 日的值（不是 t＋1）。"""
    days = pd.date_range("2018-02-01", periods=40).strftime("%Y-%m-%d")
    f = pd.DataFrame({"date_utc": days, "value": np.arange(40) * 2 + 1, "classification": "Neutral"})
    g = align(f, days, mut)
    return bool(g[10] == 21)


def fx_b(mut=None):
    """b. 缺日不補：指數缺的那天 G＝NaN（起點不算），⛔ 不用前一天的值。"""
    days = pd.date_range("2018-02-01", periods=40).strftime("%Y-%m-%d")
    f = pd.DataFrame({"date_utc": days, "value": np.arange(40) + 1, "classification": "Neutral"}).drop(index=[12, 13])
    g = align(f, days, mut)
    return bool(np.isnan(g[12]) and np.isnan(g[13]) and g[14] == 15)


def run_fixtures():
    res = []
    for name, fx, mut, why in (("a 指數時點不早於 BTC 收盤", fx_a, "next", "用 t＋1 的值"), ("b 缺日不補", fx_b, "ffill", "前值補")):
        g = fx(); red = not fx(mut)
        res.append({"案": name, "結果": "綠" if g else "紅", "反例": why, "反例結果": "紅（抓得到）" if red else "⛔ 仍綠"})
    return all(r["結果"] == "綠" and r["反例結果"].startswith("紅") for r in res), res


def ref_rho(f, sp, h):
    val = dict(zip(f["date_utc"], f["value"])); cl = dict(zip(sp["date"], sp["close"])); days = list(sp["date"])
    xs, ys = [], []; i = days.index(T0)
    while i + h < len(days) and days[i + h] <= TEND:
        if days[i] in val:
            xs.append(float(val[days[i]])); ys.append(math.log(cl[days[i + h]] / cl[days[i]]))
        i += h
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)), n


# ───────────────────────── 描述③ ─────────────────────────
C11_NOTE = []


def c11_ef(f):
    d = C11.load_main("BTC"); dates = d["dates"]
    cls = f.set_index("date_utc")["classification"].reindex(dates)
    ef = (cls == "Extreme Fear").to_numpy()
    rows = []
    for E in C11.ES:
        for D in C11.DS:
            for X in C11.XS:
                d2 = dict(d); d2["dd"] = np.where(ef, d["dd"], np.maximum(d["dd"], -D + 1e-9))
                for m in C10.MMRS:
                    base = C11.path(d, d["mlow"], E, D, X, m, C10.COST_SIDE); filt = C11.path(d2, d2["mlow"], E, D, X, m, C10.COST_SIDE)
                    rows.append({"E": E, "D": D, "X": X, "MMR": m, "原C11期末幣數": base["coins"], "原C11進場": len(base["segs"]), "原C11強平": dates[base["liq"]] if base["liq"] >= 0 else "",
                                 "極度恐懼才開期末幣數": filt["coins"], "極度恐懼才開進場": len(filt["segs"]), "極度恐懼才開強平": dates[filt["liq"]] if filt["liq"] >= 0 else ""})
    note = []
    for D in C11.DS:
        m_ = d["dd"] <= -D
        sig = [s_["訊號日"] for s_ in C11.path(d, d["mlow"], 1.1, D, 0.3, 0.01, C10.COST_SIDE)["segs"]]
        allef = all(cls.reindex([x]).iloc[0] == "Extreme Fear" for x in sig)
        note.append(f"D{int(D * 100)}%：dd ≤ −D 的 {int(m_.sum())} 天中有 {int((m_ & ~ef).sum())} 天不是極度恐懼；原 C11 的開倉訊號日 {'、'.join(sig)}" + ("全是極度恐懼日" if allef else "不全是極度恐懼日"))
    C11_NOTE[:] = note
    return pd.DataFrame(rows), float(ef.mean())


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return C12.pct(x, nd)


def build_html(meta, T, YR, EXT, C11E, ef_share, fx, chk):
    e = html.escape
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BTC恐懼貪婪</title><style>{C12.CSS}</style></head><body><main>"]
    h.append("<h1>BTC 恐懼貪婪指數：「極度恐懼時買」成立嗎？</h1>")
    h.append(f"<div class='sub'>PREREGC16 v1（N＝3，雙向判）｜回測線｜<b>{SRC}</b>｜起點 {T0}～結果窗到 {TEND}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             f"<div class='small'>⚠ 指數含價格成分（動能、波動度、成交量等），跟價格本身不是獨立訊號。{SRC}。⛔ 不寫「極度恐懼就買」，也不提供任何倍數建議。</div></div>")
    h.append("<div class='card'><b>怎麼測</b>：每個起點 t 取當天的指數值（0＝極度恐懼、100＝極度貪婪），看它和 t 日收盤之後 h 天（7／14／30）BTC 現貨對數報酬的相關係數。"
             "起點每 h 天一個、不重疊；指數缺的 4 天（2018-04-14～16、2024-10-26）不補。CI：block bootstrap 2,000 次（區塊至少 h 天）、信賴水準 1−0.05/3。"
             "上界 < 0 ⇒ 出口②（越恐懼之後越好）；下界 > 0 ⇒ 出口③（越貪婪之後越好）；含 0 ⇒ 出口①。</div>")
    h.append("<h2>一、判定</h2><div class='tw'><table><tr><th>h</th><th>起點數</th><th>ρ［CI］</th><th>出口</th></tr>")
    for _, r in T.iterrows():
        h.append(f"<tr><td>{r.h}</td><td>{r.起點數}</td><td>{r.rho:+.3f}［{r.CI下:+.3f}～{r.CI上:+.3f}］</td><td>{r.出口}</td></tr>")
    h.append("</table></div>")
    h.append(f"<h2>二、描述（不判）</h2><h3>極度恐懼日 vs 極度貪婪日（API 自帶分級；每日都算、重疊）</h3><div class='small'>{SRC}。</div>")
    h.append("<div class='tw'><table><tr><th>分級</th><th>h</th><th>天數</th><th>之後平均報酬</th><th>上漲比例</th></tr>")
    for _, r in EXT.iterrows():
        h.append(f"<tr><td>{r.分級}</td><td>{r.h}</td><td>{r.天數}</td><td>{r.平均報酬 * 100:+.2f}%</td><td>{pct(r.上漲比例)}</td></tr>")
    h.append("</table></div>")
    h.append(f"<h3>逐年指數分布（檢查改算法跡象）</h3><div class='small'>{SRC}。只列摘要，不列逐日值。</div><div class='tw'><table><tr><th>年</th><th>天數</th><th>平均</th><th>標準差</th><th>極度恐懼</th><th>恐懼</th><th>中性</th><th>貪婪</th><th>極度貪婪</th></tr>")
    for _, r in YR.iterrows():
        h.append(f"<tr><td>{r.年}</td><td>{r.天數}</td><td>{r.平均:.1f}</td><td>{r.標準差:.1f}</td><td>{pct(r['Extreme Fear'])}</td><td>{pct(r['Fear'])}</td><td>{pct(r['Neutral'])}</td><td>{pct(r['Greed'])}</td><td>{pct(r['Extreme Greed'])}</td></tr>")
    h.append("</table></div>")
    g = C11E[C11E.MMR == 0.01]
    h.append(f"<h3>C11 的 BTC 小合約改成「只在極度恐懼日開」（只描述、⛔ 不是建議）</h3><div class='small'>C11 開倉條件再加「當天是極度恐懼」；平倉照 C11。極度恐懼日占 C11 主窗 {pct(ef_share)}。m＝1%、標記價；期末幣數相對 1 顆。</div>")
    h.append("<div class='small'>濾網有作用，但結果相同的原因：" + e("；".join(C11_NOTE)) + "。</div>")
    h.append("<div class='tw'><table><tr><th>E／D／X</th><th>原 C11</th><th>極度恐懼才開</th><th>進場段數（原→改）</th><th>強平</th></tr>")
    for _, r in g.iterrows():
        lq = (f"原 {r.原C11強平}" if r.原C11強平 else "") + (f" 改 {r.極度恐懼才開強平}" if r.極度恐懼才開強平 else "")
        h.append(f"<tr><td>{r.E:g}／{int(r.D * 100)}／{int(r.X * 100)}</td><td>{r.原C11期末幣數:.3f}</td><td>{r.極度恐懼才開期末幣數:.3f}</td><td>{r.原C11進場}→{r.極度恐懼才開進場}</td><td>{lq or '無'}</td></tr>")
    h.append("</table></div>")
    h.append("<h2>三、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>四、驗證</h2><div class='tw'><table><tr><th>fixture</th><th>結果</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td>{e(r['案'])}</td><td>{r['結果']}</td><td>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>參考實作重算：{e(str(chk.get('重算', '—')))}。</div>")
    h.append("<h2>五、讀的時候要注意</h2><ul><li>指數含價格成分；與 C13（週動能）、C7（波動率管理）的訊號有重疊。</li><li>無法驗證歷史值是否事後回填或改算法（調查成分已暫停）；資料於 2026-10-04 取得後凍結。</li>"
             f"<li>{SRC}（條款要求明確標示來源）。</li><li>⛔ 不寫「極度恐懼就買」；⛔ 不提供倍數建議。</li></ul>")
    h.append("<h2>六、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in EXEC_SUPPLIED) + "</ul></main></body></html>")
    return "\n".join(h)


EXEC_SUPPLIED = [
    "G3 起點那天指數缺 ⇒ 該起點不算（不補值）",
    "G5 區塊長以起點計、至少 1 個起點＝至少 h 天（同 C15）",
    "G7② 極度恐懼／極度貪婪日的之後報酬用每日（重疊）起點，只描述、不附 CI",
    "G7③ 「只在極度恐懼日開」解讀成 C11 開倉條件再加極度恐懼（且），平倉照 C11；指數缺的日子當作不是極度恐懼",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['結果']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    f = load_fng(); sp = spot(); days = sp["date"].to_numpy(); cl = sp["close"].to_numpy(float)
    G = align(f, days)
    miss = sorted(set(pd.date_range(f["date_utc"].iloc[0], f["date_utc"].iloc[-1]).strftime("%Y-%m-%d")) - set(f["date_utc"]))
    print(f"[資料] 指數 {f['date_utc'].iloc[0]}～{f['date_utc'].iloc[-1]} 共 {len(f)} 天｜缺 {miss}")
    if a.check:
        rows = []
        for h in HS:
            st = starts(days, h); x = G[st]; k = np.isfinite(x); y = np.log(cl[st + h] / cl[st])
            rho = float(np.corrcoef(x[k], y[k])[0, 1]); rr, n = ref_rho(f, sp, h)
            rows.append(f"h{h} {int(k.sum())} 起點 {'一致' if (abs(rho - rr) < 1e-12 and n == k.sum()) else '⛔不一致'}")
        chk = {"讀法寫死": FROZEN, "fixture全過": ok, "fixture": fx, "重算": "；".join(rows), "缺日": miss}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("[check]", chk["重算"])
        assert all("不一致" not in r for r in rows)
        return
    rows = []
    for h in HS:
        st = starts(days, h); x = G[st]; k = np.isfinite(x); skipped = [days[s] for s in st[~k]]
        st, x = st[k], x[k]; y = np.log(cl[st + h] / cl[st])
        rho = float(np.corrcoef(x, y)[0, 1]); lo, hi, L = C15.ci_corr(x, y)
        rows.append({"h": h, "起點數": len(st), "缺值略過的起點": "、".join(skipped), "首起點": days[st[0]], "末起點": days[st[-1]], "rho": rho, "CI下": lo, "CI上": hi,
                     "L_block起點": L, "L_block天": L * h, "出口": C15.exit_of(lo, hi)})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    cls = f.set_index("date_utc")["classification"].reindex(days).to_numpy()
    ext = []
    for nm in ("Extreme Fear", "Extreme Greed"):
        for h in HS:
            idx = np.array([i for i in range(len(days) - h) if cls[i] == nm and days[i] >= T0])
            r = np.log(cl[idx + h] / cl[idx])
            ext.append({"分級": nm, "h": h, "天數": len(idx), "平均報酬": float(r.mean()), "上漲比例": float((r > 0).mean())})
    EXT = pd.DataFrame(ext); EXT.to_csv(os.path.join(OUT, "extreme_days.csv"), index=False)
    f2 = f.copy(); f2["年"] = f2["date_utc"].str[:4]
    yr = []
    for y_, g_ in f2.groupby("年"):
        row = {"年": y_, "天數": len(g_), "平均": float(g_["value"].mean()), "標準差": float(g_["value"].std())}
        for c in ("Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"):
            row[c] = float((g_["classification"] == c).mean())
        yr.append(row)
    YR = pd.DataFrame(yr); YR.to_csv(os.path.join(OUT, "yearly_distribution.csv"), index=False)
    C11E, ef_share = c11_ef(f); C11E.to_csv(os.path.join(OUT, "c11_extreme_fear_btc.csv"), index=False)
    g = T.set_index("h"); n1 = int((T["出口"] == "出口①").sum())
    pri = [f"① 3 格全出口①：出口① {n1}／3 ⇒ " + ("中" if n1 == 3 else "未中"),
           f"② h30 點估計為負：ρ＝{g.loc[30, 'rho']:+.3f} ⇒ " + ("中" if g.loc[30, "rho"] < 0 else "未中")]
    lines = ["3 格：" + "、".join(f"h{r.h} ρ {r.rho:+.3f}（{r.出口}）" for r in T.itertuples()) + f"。指數含價格成分；{SRC}。"]
    meta = {"登錄": "PREREGC16 BTC 恐懼貪婪 v1 sha3f217df7c47ad189", "裁定": "seq299 §二（N＝3）", "讀法寫死": FROZEN, "資料來源": SRC,
            "資料": "私有 us-stock-data data/crypto_private/fng（commit 8d1de6fd，2026-10-04 22:32 取得凍結）＋公開 main " + C10.SHA[:10] + " BTC 現貨",
            "缺日": miss, "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "結論行": lines, "先驗對答": pri, "極度恐懼日比例_C11窗": ef_share,
            "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1)}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "BTC恐懼貪婪.html"), "w", encoding="utf-8").write(build_html(meta, T, YR, EXT, C11E, ef_share, fx, chk))
    print(T.round(4).to_string()); print(EXT.round(4).to_string()); print(YR.round(3).to_string())
    print(C11E[C11E.MMR == 0.01].round(3).to_string())
    for x in lines + pri:
        print(x)
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

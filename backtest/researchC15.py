# -*- coding: utf-8 -*-
"""PREREGC15「BTC 資金費率過熱 ⇒ 之後報酬偏低？」v1（sha d405609a02a09cc9）——回測線執行端。裁定 seq299 §二：核准，N＝3，雙向判。

⭐ 讀法寫死：2026-10-04 22:03（台北，腳本 TZ=Asia/Taipei date 取得）——⛔ 在算出任何相關係數之前寫在這裡；之後只准補「執行時發現」並標時間。
   登錄沒寫到、由回測線補的讀法標【執行者補】。方向取自外部文獻（Schmeling, Schrimpf & Todorov, BIS WP 1087）；論文用交割期貨溢價，本件用永續資金費率 ⇒ 只取方向。

資料：公開 main 1fb8815e81（唯讀副本 ~/c10data/<sha>；與當前 main 7c0dd23a94 的這三檔逐位相同）
   BTCUSDT 永續資金費率 data/crypto_funding/BTCUSDT.csv（calc_time 毫秒 UTC、funding_interval_hours 逐列、last_funding_rate 小數），
   逐月以 data/meta/crypto_funding_manifest.csv 驗（status＝ok 且列數相符，backtest/funding.py 同一支）；BTC 現貨日 K data/crypto/BTC.csv；
   描述③：幣本位 BTCUSD_PERP 資金費率 data/meta/crypto_cm_funding_rest/BTCUSD_PERP.csv（REST 完整版）

⭐ 落地讀法
 F1 訊號 F_t（登錄 §二）：結算時點（毫秒截到秒）落在（t−7 日 UTC 收盤，t 日 UTC 收盤〕的各筆費率逐筆加總 × 365／7
    ＝ UTC 日期 t−6～t 的全部結算（00:00 那筆屬於當天，是前一日收盤之後的事）；t＋1 日 00:00 那筆 ⛔ 不算（fixture a）
    逐列加、⛔ 不假設一天 3 筆（fixture b）；7 日內任何一天在清單裡不是 ok 月 ⇒ 該 t 不算
 F2 結果：R_t＝ln(C_{t+h}／C_t)，C＝BTC 現貨 UTC 日收盤；h ∈ {7、14、30}
 F3 起點（登錄 §二）：2020-01-08 起每 h 天一個（不重疊），t＋h ≤ 2026-08-31
 F4 判定量 ρ_h＝corr(F_t, R_t)（起點序列）
 F5 CI：配對 stationary block bootstrap（researchc1），區塊長＝max(Politis–White(去均值乘積), 1) 個起點；
    起點每 h 天一個 ⇒ 一個區塊至少 h 天 ⇒ 符合 seq299「block 長 ≥ H」【執行者補：以天數計，1 個起點＝h 天】
    2,000 次、每格種子 20260923；信賴水準 1−0.05/3（雙尾各 0.05/6）
 F6 出口（雙向）：② 上界 < 0（論文方向：費率高 ⇒ 之後差）｜③ 下界 > 0（反向：費率高 ⇒ 之後更好）｜① 含 0
 F7 描述（不判）：
    ① 費率三分位：界線＝t 以前（不含 t）全部日訊號 F 的 1／3、2／3 分位，歷史不足 90 天不分【執行者補：擴張窗、不看未來】；
       各分位的起點中，之後 h 天「最大跌幅」（t＋1～t＋h 日低最小值 ÷ C_t − 1）超過 10%、20% 的比例，與平均 R_t
    ② 起點在 2024-08-01 以後（論文沒看過）的 ρ_h
    ③ 幣本位 BTCUSD_PERP 費率同法重算（第一個 7 日完整的日子起、每 h 天一個）
    ④ C11 BTC：「費率在前 1／3（同 ① 的擴張窗界線）時不開、在場就關」對 C11 主臂 BTC 的影響：
       用 researchC11.path，把過熱日的訊號改成「平倉訊號、不開倉」，其餘照 C11；資金費率資料尾（2026-08-31）之後視為不過熱【執行者補】；
       報期末幣數與強平（m 0.5／1／2%、標記價），與原 C11 並列
    ⑤ 每日起點（重疊）版：區塊長 max(PW, h) 天的 block bootstrap，只描述【執行者補：對應 seq299「重疊 ⇒ block ≥ H」的另一種讀法】
 F8 先驗對答：① h7、h14 出口① ② h30 點估計為負但出口① ③ 無出口③
 F9 --check：fixture a（不含 t＋1 的 00:00；反例：含）、b（非 8 小時間隔逐筆加；反例：一天 3 筆）；純迴圈參考實作重算 3 格 ρ 逐位比
⛔ 出口②也不是「費率高就放空／賣幣」；⛔ 任何買賣、倍數建議都不寫。
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, html
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchc1 as C1
import funding as F
import researchC10 as C10
import researchC11 as C11
import researchC12 as C12

OUT = os.path.join(C10.REPO, "backtest", "resultsC15")
HS = (7, 14, 30)
T0, TEND = "2020-01-08", "2026-08-31"
POST = "2024-08-01"
N_CELLS = 3
SEED = 20260923
N_BOOT = 2000
FROZEN = "2026-10-04 22:03（台北）"


# ───────────────────────── 資料 ─────────────────────────
def load_funding_usdt():
    full = F.load_full("BTC", path=os.path.join(C10.ROOT, "data", "crypto_funding", "BTCUSDT.csv"))
    man = F.load_manifest(path=os.path.join(C10.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
    sec = full["calc_time"].to_numpy() // 1000
    full["date"] = pd.to_datetime(sec, unit="s", utc=True).strftime("%Y-%m-%d")
    okm = set()
    for (y, m) in sorted({(int(d[:4]), int(d[5:7])) for d in full["date"]}):
        try:
            F.month_of(full, "BTC", y, m, man); okm.add(f"{y:04d}-{m:02d}")
        except F.FundingAbsent:
            pass
    return full[["date", "last_funding_rate", "funding_interval_hours"]].rename(columns={"last_funding_rate": "rate"}), okm


def load_funding_cm():
    f = pd.read_csv(os.path.join(C10.ROOT, "data", "meta", "crypto_cm_funding_rest", "BTCUSD_PERP.csv"))
    f["sec"] = f["funding_time"] // 1000; f = f.drop_duplicates("sec")
    f["date"] = pd.to_datetime(f["sec"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    return f[["date", "funding_rate"]].rename(columns={"funding_rate": "rate"})


def spot():
    d = pd.read_csv(os.path.join(C10.ROOT, "data", "crypto", "BTC.csv"), dtype={"date": str}).drop_duplicates("date").sort_values("date")
    d = d[(d["date"] >= "2019-12-01") & (d["date"] <= "2026-09-30")].reset_index(drop=True)
    assert (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1 == len(d)
    return d


def signal(fr, days, okm=None, mut=None):
    """F1：F[t]＝Σ rate（UTC 日期 t−6～t）× 365/7。mut：next0（多含 t＋1 的 00:00；反例）｜three（每日改成 平均×3；反例）。
    fr 需含 date、rate；mut＝next0 需 fr 另有 tod0（是否 00:00）欄。"""
    g = fr.groupby("date")["rate"]
    s = g.sum() if mut != "three" else g.mean() * 3
    cnt = g.size()
    cal = pd.Index(days)
    daily = s.reindex(cal); have = cnt.reindex(cal).fillna(0) > 0
    if okm is not None:
        have &= pd.Series([d[:7] in okm for d in cal], index=cal)
    v = daily.where(have)
    F7 = v.rolling(7, min_periods=7).sum()
    if mut == "next0":
        nx = fr[fr["tod0"]].groupby("date")["rate"].sum().reindex(cal).shift(-1).fillna(0.0)
        F7 = F7 + nx
    return (F7 * 365.0 / 7.0)


def starts(days, h, t0=T0, tend=TEND):
    d = list(days); i0 = d.index(t0); out = []
    for i in range(i0, len(d) - h, h):
        if d[i + h] > tend:
            break
        out.append(i)
    return np.array(out, int)


def ci_corr(x, y, Lmin=1):
    z = (x - x.mean()) * (y - y.mean())
    L = max(C1.politis_white_block(z), Lmin); rng = np.random.default_rng(SEED)
    bs = np.empty(N_BOOT)
    for i in range(N_BOOT):
        j = C1.stationary_idx(len(x), L, rng); bs[i] = np.corrcoef(x[j], y[j])[0, 1]
    a = 0.05 / N_CELLS / 2
    return float(np.percentile(bs, 100 * a)), float(np.percentile(bs, 100 * (1 - a))), int(L)


def exit_of(lo, hi):
    return "出口②" if hi < 0 else ("出口③" if lo > 0 else "出口①")


# ───────────────────────── fixture ─────────────────────────
def _fr(rows):
    df = pd.DataFrame(rows, columns=["date", "tod_h", "rate"]); df["tod0"] = df["tod_h"] == 0; return df


def fx_a(mut=None):
    """a. F_t 只含 t 日收盤以前的結算：t＋1 日 00:00 那筆（很大）不能算進 F_t。"""
    days = pd.date_range("2021-01-01", periods=10).strftime("%Y-%m-%d")
    rows = [(d, hh, 0.0001) for d in days for hh in (0, 8, 16)]
    rows = [(d, hh, (0.05 if (d == days[8] and hh == 0) else r)) for d, hh, r in rows]
    f = signal(_fr(rows), days, mut=mut)
    return bool(abs(f.loc[days[7]] - 0.0001 * 21 * 365 / 7) < 1e-12)


def fx_b(mut=None):
    """b. 結算間隔非 8 小時（4 小時，一天 6 筆）要逐筆加：7 天 42 筆 × 0.0001。"""
    days = pd.date_range("2021-01-01", periods=10).strftime("%Y-%m-%d")
    rows = [(d, hh, 0.0001) for d in days for hh in (0, 4, 8, 12, 16, 20)]
    f = signal(_fr(rows), days, mut=mut)
    return bool(abs(f.loc[days[7]] - 0.0001 * 42 * 365 / 7) < 1e-12)


def run_fixtures():
    res = []
    for name, fx, mut, why in (("a 訊號只含 t 日收盤以前的結算", fx_a, "next0", "多含 t＋1 日 00:00"), ("b 非 8 小時間隔逐筆加", fx_b, "three", "假設一天 3 筆（平均×3）")):
        g = fx(); red = not fx(mut)
        res.append({"案": name, "結果": "綠" if g else "紅", "反例": why, "反例結果": "紅（抓得到）" if red else "⛔ 仍綠"})
    return all(r["結果"] == "綠" and r["反例結果"].startswith("紅") for r in res), res


def ref_rho(fr, okm, sp, h):
    """純迴圈參考實作。"""
    by = {}
    for d, r in zip(fr["date"], fr["rate"]):
        by.setdefault(d, []).append(r)
    cl = dict(zip(sp["date"], sp["close"])); days = list(sp["date"])
    xs, ys = [], []
    i = days.index(T0)
    while i + h < len(days) and days[i + h] <= TEND:
        win = days[i - 6:i + 1]
        if all(d in by and d[:7] in okm for d in win):
            fsum = 0.0
            for d in win:
                for r in by[d]:
                    fsum += r
            xs.append(fsum * 365 / 7); ys.append(math.log(cl[days[i + h]] / cl[days[i]]))
        i += h
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)), n


# ───────────────────────── 描述④：C11 BTC 加過熱濾網 ─────────────────────────
def hot_flag(Fd, days):
    """擴張窗三分位：t 以前（不含 t）日訊號的 2/3 分位；歷史 < 90 天不算過熱。"""
    v = Fd.reindex(days).to_numpy(float); out = np.zeros(len(days), bool); cut = np.full(len(days), np.nan)
    hist = []
    for i in range(len(days)):
        if len(hist) >= 90 and np.isfinite(v[i]):
            c = float(np.percentile(hist, 200 / 3)); cut[i] = c; out[i] = v[i] > c
        if np.isfinite(v[i]):
            hist.append(v[i])
    return out, cut


def c11_filter(Fd):
    d = C11.load_main("BTC"); dates = d["dates"]
    hot, _ = hot_flag(Fd, dates)
    rows = []
    for E in C11.ES:
        for D in C11.DS:
            for X in C11.XS:
                for m in C10.MMRS:
                    base = C11.path(d, d["mlow"], E, D, X, m, C10.COST_SIDE)
                    d2 = dict(d); d2["dd"] = np.where(hot, 0.0, d["dd"])
                    filt = C11.path(d2, d2["mlow"], E, D, X, m, C10.COST_SIDE)
                    rows.append({"E": E, "D": D, "X": X, "MMR": m, "原C11期末幣數": base["coins"], "原C11進場": len(base["segs"]), "原C11強平": dates[base["liq"]] if base["liq"] >= 0 else "",
                                 "加濾網期末幣數": filt["coins"], "加濾網進場": len(filt["segs"]), "加濾網強平": dates[filt["liq"]] if filt["liq"] >= 0 else ""})
    return pd.DataFrame(rows), float(hot.mean())


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return C12.pct(x, nd)


def build_html(meta, T, TER, POSTR, CM, OV, C11F, hot_share, fx, chk):
    e = html.escape
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BTC資金費率過熱</title><style>{C12.CSS}</style></head><body><main>"]
    h.append("<h1>BTC 資金費率過熱，之後報酬偏低嗎？</h1>")
    h.append(f"<div class='sub'>PREREGC15 v1（N＝3，雙向判）｜回測線｜方向取自 BIS WP 1087｜起點 {T0}～結果窗到 {TEND}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    h.append("<div class='lead'><b>結論</b><ul>" + "".join(f"<li>{x}</li>" for x in meta["結論行"]) + "</ul>"
             "<div class='small'>論文用交割期貨溢價、本件用 Binance USDT 永續資金費率（同一種「多方付空方的溢價」，不是同一工具），只取方向。⛔ 出口②也不是「費率高就放空／賣幣」；不提供任何買賣或倍數建議。</div></div>")
    h.append("<div class='card'><b>怎麼測</b>：每個起點 t 算近 7 天資金費逐筆加總的年化值 F_t（只含 t 日 UTC 收盤以前的結算），看它和之後 h 天（7／14／30）BTC 現貨對數報酬的相關係數。"
             "起點每 h 天一個、不重疊；CI 用 block bootstrap 2,000 次（一個區塊至少 h 天）、信賴水準 1−0.05/3。上界 < 0 ⇒ 出口②（論文方向）；下界 > 0 ⇒ 出口③（反向）；含 0 ⇒ 出口①。</div>")
    h.append("<h2>一、判定</h2><div class='tw'><table><tr><th>h</th><th>起點數</th><th>ρ［CI］</th><th>出口</th></tr>")
    for _, r in T.iterrows():
        cls = "pass" if r["出口"] != "出口①" else ""
        h.append(f"<tr><td>{r.h}</td><td>{r.起點數}</td><td>{r.rho:+.3f}［{r.CI下:+.3f}～{r.CI上:+.3f}］</td><td class='{cls}'>{r.出口}</td></tr>")
    h.append("</table></div>")
    h.append("<h2>二、描述（不判）</h2><h3>費率三分位：之後 h 天的最大跌幅</h3><div class='small'>三分位界線只用 t 以前的日訊號（擴張窗）。最大跌幅＝之後 h 天日低最低點相對起點收盤。</div>")
    h.append("<div class='tw'><table><tr><th>h</th><th>分位</th><th>起點數</th><th>跌超過 10%</th><th>跌超過 20%</th><th>平均報酬</th></tr>")
    for _, r in TER.iterrows():
        h.append(f"<tr><td>{r.h}</td><td>{r.分位}</td><td>{r.起點數}</td><td>{pct(r.跌超10)}</td><td>{pct(r.跌超20)}</td><td>{r.平均報酬 * 100:+.2f}%</td></tr>")
    h.append("</table></div>")
    h.append("<h3>其他版本（只描述）</h3><div class='tw'><table><tr><th>版本</th><th>h</th><th>起點數</th><th>ρ</th><th>CI</th></tr>")
    for nm, D_ in (("2024-08 以後（論文沒看過）", POSTR), ("幣本位 BTCUSD_PERP 費率", CM), ("每日起點（重疊）、區塊 ≥ h 天", OV)):
        for _, r in D_.iterrows():
            ci = f"［{r.CI下:+.3f}～{r.CI上:+.3f}］" if "CI下" in r and np.isfinite(r.CI下) else "—"
            h.append(f"<tr><td>{nm}</td><td>{r.h}</td><td>{r.起點數}</td><td>{r.rho:+.3f}</td><td>{ci}</td></tr>")
    h.append("</table></div>")
    g = C11F[C11F.MMR == 0.01]
    h.append(f"<h3>C11 的 BTC 小合約加「費率過熱不開／關掉」（只描述、⛔ 不是建議）</h3><div class='small'>過熱日（擴張窗前 1／3）占 C11 主窗 {pct(hot_share)}。m＝1%、標記價；期末幣數相對 1 顆。</div>")
    h.append("<div class='tw'><table><tr><th>E／D／X</th><th>原 C11</th><th>加濾網</th><th>進場段數（原→加）</th><th>強平</th></tr>")
    for _, r in g.iterrows():
        lq = (f"原 {r.原C11強平}" if r.原C11強平 else "") + (f" 加 {r.加濾網強平}" if r.加濾網強平 else "")
        h.append(f"<tr><td>{r.E:g}／{int(r.D * 100)}／{int(r.X * 100)}</td><td>{r.原C11期末幣數:.3f}</td><td>{r.加濾網期末幣數:.3f}</td><td>{r.原C11進場}→{r.加濾網進場}</td><td>{lq or '無'}</td></tr>")
    h.append("</table></div>")
    h.append("<h2>三、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    h.append("<h2>四、驗證</h2><div class='tw'><table><tr><th>fixture</th><th>結果</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td>{e(r['案'])}</td><td>{r['結果']}</td><td>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>參考實作重算：{e(str(chk.get('重算', '—')))}；資金費逐月清單：{e(str(chk.get('清單', '—')))}。</div>")
    h.append("<h2>五、讀的時候要注意</h2><ul><li>N＝3，可判出的最小相關約 0.13（h7）～0.27（h30）。</li><li>論文窗 2019-03～2024-07 與本件大部分重疊，只有 2024-08 以後是論文沒看過的（另報）。</li>"
             "<li>先驗污染：C2、C5 用過這份費率（知道 2020～21 高、2022 後低），但從未算過與之後報酬的關係。</li><li>⛔ 不提供任何買賣、倍數建議。</li></ul>")
    h.append("<h2>六、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in EXEC_SUPPLIED) + "</ul></main></body></html>")
    return "\n".join(h)


EXEC_SUPPLIED = [
    "F1 7 日內有任何一天所屬月份不在清單 ok ⇒ 該起點不算",
    "F5 起點每 h 天一個、區塊至少 1 個起點 ⇒ 區塊至少 h 天，符合 seq299「block 長 ≥ H」",
    "F7① 三分位界線用 t 以前全部日訊號（擴張窗），歷史不足 90 天不分",
    "F7④ C11 濾網：過熱日訊號改成「平倉、不開倉」；資金費率資料尾之後視為不過熱",
    "F7⑤ 另做每日起點（重疊）版、區塊 max(PW, h) 天，只描述",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] {r['結果']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    fr, okm = load_funding_usdt(); sp = spot(); days = sp["date"].to_numpy(); cl = sp["close"].to_numpy(float); lo_ = sp["low"].to_numpy(float)
    Fd = signal(fr, days, okm)
    missing = sorted({d[:7] for d in fr["date"]} - okm)
    print(f"[資料] 費率 {fr['date'].iloc[0]}～{fr['date'].iloc[-1]} 共 {len(fr)} 筆｜非 ok 月 {missing or '無'}｜間隔 {sorted(fr['funding_interval_hours'].unique())}")
    if a.check:
        rows = []
        for h in HS:
            st = starts(days, h); x = Fd.to_numpy()[st]; y = np.log(cl[st + h] / cl[st]); k = np.isfinite(x)
            rho = float(np.corrcoef(x[k], y[k])[0, 1]); rr, n = ref_rho(fr, okm, sp, h)
            rows.append(f"h{h} {int(k.sum())} 起點 {'一致' if (abs(rho - rr) < 1e-12 and n == k.sum()) else '⛔不一致'}")
        chk = {"讀法寫死": FROZEN, "fixture全過": ok, "fixture": fx, "重算": "；".join(rows), "清單": f"2020-01～2026-08 非 ok 月：{missing or '無'}"}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("[check]", chk["重算"], "｜", chk["清單"])
        assert all("不一致" not in r for r in rows)
        return
    rows, ter, post, ov = [], [], [], []
    hot, cut = hot_flag(Fd, days)
    Fv = Fd.to_numpy()
    for h in HS:
        st = starts(days, h); x = Fv[st]; y = np.log(cl[st + h] / cl[st]); k = np.isfinite(x); st, x, y = st[k], x[k], y[k]
        rho = float(np.corrcoef(x, y)[0, 1]); lo, hi, L = ci_corr(x, y)
        rows.append({"h": h, "起點數": len(st), "首起點": days[st[0]], "末起點": days[st[-1]], "rho": rho, "CI下": lo, "CI上": hi, "L_block起點": L, "L_block天": L * h, "出口": exit_of(lo, hi)})
        mdd = np.array([lo_[s + 1:s + h + 1].min() / cl[s] - 1 for s in st])
        # 三分位：用 t 以前的 1/3、2/3 界線
        lab = []
        for s in st:
            if not np.isfinite(cut[s]):
                lab.append("歷史不足"); continue
            histv = Fv[:s][np.isfinite(Fv[:s])]
            c1, c2 = np.percentile(histv, [100 / 3, 200 / 3])
            lab.append("前 1/3（高）" if Fv[s] > c2 else ("後 1/3（低）" if Fv[s] <= c1 else "中 1/3"))
        lab = np.array(lab)
        for q in ("前 1/3（高）", "中 1/3", "後 1/3（低）", "歷史不足"):
            m_ = lab == q
            if m_.any():
                ter.append({"h": h, "分位": q, "起點數": int(m_.sum()), "跌超10": float((mdd[m_] < -0.10).mean()), "跌超20": float((mdd[m_] < -0.20).mean()), "平均報酬": float(y[m_].mean())})
        pm = np.array([days[s] >= POST for s in st])
        post.append({"h": h, "起點數": int(pm.sum()), "rho": float(np.corrcoef(x[pm], y[pm])[0, 1]), "CI下": np.nan, "CI上": np.nan})
        # 每日起點（重疊）
        sd = np.arange(list(days).index(T0), len(days) - h); sd = sd[[days[s + h] <= TEND for s in sd]]
        xd = Fv[sd]; yd = np.log(cl[sd + h] / cl[sd]); kk = np.isfinite(xd)
        lo2, hi2, L2 = ci_corr(xd[kk], yd[kk], Lmin=h)
        ov.append({"h": h, "起點數": int(kk.sum()), "rho": float(np.corrcoef(xd[kk], yd[kk])[0, 1]), "CI下": lo2, "CI上": hi2, "L_block天": L2})
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    TER = pd.DataFrame(ter); TER.to_csv(os.path.join(OUT, "tercile.csv"), index=False)
    POSTR = pd.DataFrame(post); OV = pd.DataFrame(ov)
    # 幣本位費率
    fc = load_funding_cm(); Fc = signal(fc, days)
    cmr = []
    first = Fc.first_valid_index()
    for h in HS:
        st = starts(days, h, t0=first); x = Fc.to_numpy()[st]; y = np.log(cl[st + h] / cl[st]); k = np.isfinite(x)
        cmr.append({"h": h, "起點數": int(k.sum()), "rho": float(np.corrcoef(x[k], y[k])[0, 1]), "CI下": np.nan, "CI上": np.nan})
    CM = pd.DataFrame(cmr)
    pd.concat([POSTR.assign(版本="2024-08以後"), CM.assign(版本="幣本位費率"), OV.assign(版本="每日起點重疊")]).to_csv(os.path.join(OUT, "other_versions.csv"), index=False)
    C11F, hot_share = c11_filter(Fd); C11F.to_csv(os.path.join(OUT, "c11_filter_btc.csv"), index=False)
    pri = []
    g = T.set_index("h")
    pri.append(f"① h7、h14 出口①：h7 {g.loc[7, '出口']}、h14 {g.loc[14, '出口']} ⇒ " + ("中" if g.loc[7, "出口"] == "出口①" and g.loc[14, "出口"] == "出口①" else "未中"))
    pri.append(f"② h30 點估計為負但出口①：ρ＝{g.loc[30, 'rho']:+.3f}、{g.loc[30, '出口']} ⇒ " + ("中" if g.loc[30, "rho"] < 0 and g.loc[30, "出口"] == "出口①" else "未中"))
    n3 = int((T["出口"] == "出口③").sum())
    pri.append(f"③ 無出口③：出口③ {n3} 格 ⇒ " + ("中" if n3 == 0 else "未中"))
    lines = ["3 格：" + "、".join(f"h{r.h} ρ {r.rho:+.3f}（{r.出口}）" for r in T.itertuples()) + "。"]
    meta = {"登錄": "PREREGC15 BTC 資金費率過熱 v1 shad405609a02a09cc9", "裁定": "seq299 §二（N＝3）", "讀法寫死": FROZEN, "資料": f"公開 main {C10.SHA[:10]}",
            "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"), "結論行": lines, "先驗對答": pri, "過熱日比例_C11窗": hot_share,
            "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1)}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    cp = os.path.join(OUT, "check.json"); chk = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    open(os.path.join(OUT, "BTC資金費率過熱.html"), "w", encoding="utf-8").write(build_html(meta, T, TER, POSTR, CM, OV, C11F, hot_share, fx, chk))
    print(T.round(4).to_string()); print(TER.round(3).to_string()); print(POSTR.round(3).to_string()); print(CM.round(3).to_string()); print(OV.round(3).to_string())
    print(C11F[C11F.MMR == 0.01].round(3).to_string())
    for x in lines + pri:
        print(x)
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

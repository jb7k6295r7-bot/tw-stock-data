# -*- coding: utf-8 -*-
"""賣 0050／六四 v1 提領拿現金 對照 換高股息（裁定 seq391＋seq392＋seq393）。回測線，2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWithdraw
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchWithdraw_check.py

⛔ 定位：描述，不判、不計 N、不改六四 v1、不改任何規則。這是描述，不是買賣建議。
   前提（seq393）：每月一定要拿到同樣的現金；「不提領」不在候選裡、不列表。
═══ 設計（seq391／seq392 逐項）═══
 帳戶   A ＝ 100% 0050｜B ＝ 六四 v1（0050 60%＋00685L 40%，每年 1 月第一個交易日開盤調回，成本 0.385% × 調動，researchMix70 同值）
        00685L 上市（2017-03-30）前 ＝ 六四 v1 研究的合成兩倍序列：research64retest.synth(rate＝0) ＝ researchMix70 原式
        （0050 含息日報酬 ×2 每日重設、扣 0.3%／年；開盤 ＝ 前收 ×（1＋2×隔夜報酬））；上市日起用真的 00685L（2026-07-07 分割 1→24 照單位 ×24）
        ⚠ 逐字：「00685L 早年為合成序列（0050×2 合成、不扣資金成本）」
 資料   0050／00685L 未還原價與除息、分割：researchHighDiv.load／load_px／load_events（tw-stock-data origin/main＋早年 3edc0e2206）
 本金   以 50 萬元模擬（健保單筆 ≥2 萬門檻照 researchHighDiv 50 萬口徑），輸出一律換算「每 100 萬本金」
 目標   每月 3,404 元、4,649 元（每 100 萬本金；＝ seq386 高股息 70/30、0/100 淨 3.5% 版的每月中位現金）
 配息   0050 配息照領現：除息日稅後（researchHighDiv.tax_fn 合併計稅 淨 3.5%／淨 11.5%、8.5% 抵減每戶 8 萬上限）、
        健保 2.11%（單筆 ≥2 萬，50 萬本金口徑）後進現金（①② 為暫存、③④⑤ 為水庫），先付當月，不足才賣股
 發放   每月第一個交易日發當月現金；窗首日發第一個月（①② 直接從本金留下、③④⑤ 從水庫付）
 賣股   發放日開盤賣；從比重超標的那檔先賣（賣到回目標比重後，剩下照目標比重賣）；成本 手續費 0.1425%＋ETF 證交稅 0.1%；價差不課稅
        建倉 照 researchHighDiv／六四 v1：0.385% × 建倉金額
 提領法 ① 固定金額：每月目標現金（原值、不依 CPI 調）
        ② 固定比例：每年第一次發放日，年額 ＝ 前一交易日收盤帳戶市值（含暫存）× 起始比例（3,404×12／100 萬 ＝ 4.0848%；4,649 ⇒ 5.5788%），÷12 按月發；
           窗首年用本金
        ③④⑤ 現金水庫（Evensky）：窗首從本金撥 24 個月現金進水庫；每月從水庫付；條件成立的發放日開盤賣股把水庫補滿 24 個月
           ③ 只在賺錢年補：1 月發放日，帳戶（市值＋水庫）過去 12 個月時間加權報酬（領現加回）＞0（前一年最後交易日收盤 對 再前一年最後交易日收盤；
              不足 12 個月用窗首）
           ④ 0050 前一交易日（月底）收盤 ≥ 52 週（364 曆日，含當日）最高收盤 × 0.95（分割調整價、不含息）
           ⑤ 0050 前一交易日（月底）收盤 ＞ 200 日均線（分割調整價）
           水庫不夠付當月而條件不成立 ⇒ 被迫照① 只賣足當月（次數與年份必報）；配息超過上限不強制再投入
           水庫利率 0%，另報 1.5%（逐曆日複利，利息不課稅）
 期間   起點 2007-12-26（＝ 高股息全期）、2015-01-05、2021-12-01；終點 ＝ 資料最新日
 大盤回落 ＞20%：0050 含息還原（2004-02 起全歷史，researchHighDiv 早年＋main 除息事件建鏈）收盤對歷史最高回落 ＞20%（賣出日前一交易日收盤）
        ⚠ 不用加權指數：us-stock-data twse_taiex.csv 是價格指數（不含息），且 1990-02 高點到 2020 才再過 ⇒ 2007～2019 幾乎全期都算「回落 ＞20%」；
          加權指數回落只列在 conditions_monthly.csv 參考
═══ 指標 ═══
 期末總額 ＝ 期末市值＋水庫（或暫存）＋累計領現（每 100 萬本金）；換算年化 ＝ (期末總額／100 萬)^(1／年數) − 1（年數 ＝ 曆日／365.25；領現不生息；seq390 口徑）
 最大回落 ＝ 帳戶（市值＋水庫）路徑對高點的最大回落（窗首 ＝ 本金；與 researchHighDiv「帳戶市值回落」同口徑）
 最低市值剩本金幾成 ＝ min（市值＋水庫）÷ 本金
 最差年每月現金 ＝ 完整日曆年領現 ÷12（每 100 萬本金，元）
 賣在大跌期 ＝ 賣股事件（次數、金額）中落在大盤回落 ＞20% 的比例
 高股息並排 ＝ resultsHighDiv/grid_with_endcagr.csv（全期 50 萬 領現：70/30 對 3,404、0/100 對 4,649；30／50／100% 都列）；
        2015-01、2021-12 起點以 researchHighDiv.sim 同式重算（全期重算與 csv 核對）
輸出 backtest/resultsWithdraw/
"""
from __future__ import annotations

import glob
import io
import json
import os

import numpy as np
import pandas as pd

from . import researchHighDiv as RH
from . import researchMix70 as MX
from . import research64retest as R64

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsWithdraw")
V0 = 500_000.0
SCALE = 1_000_000.0 / V0
TARGETS = (3404.0, 4649.0)
SELLC = 0.001425 + 0.001
REBC = MX.COST
FEE685 = 0.003
LIST685 = "2017-03-30"
RES_M = 24
TAXV = {"淨3.5%": ("comb", 0.12), "淨11.5%": ("comb", 0.20)}
HD_TAXN = {"淨3.5%": "合併 淨3.5%（12%級）", "淨11.5%": "合併 淨11.5%（20%級）"}
METHODS = {1: "①固定金額", 2: "②固定比例", 3: "③賺錢年才補水庫", 4: "④近52週高才補", 5: "⑤站上200日線才補"}
ACCTS = {"A": (("0050",), (1.0,)), "B": (("0050", "00685L"), (0.6, 0.4))}
START_REQ = {"2007-12": "2007-12-26", "2015-01": "2015-01-01", "2021-12": "2021-12-01"}
TAIEX_GLOB = os.path.expanduser("~/msdata/us_macro/*/twse_taiex.csv")
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


# ───────────────────────── 資料 ─────────────────────────
def load_all():
    msha = RH.git("rev-parse", RH.MAIN_REF).strip()
    cal, pos, X = RH.load(msha)
    n = len(cal)
    x50 = X["0050"]
    # 0050 含息還原（收盤、開盤）：TR_t ＝ split_t ×（C_t＋d_t）／C_{t−1}
    Ac = np.empty(n); Ao = np.empty(n); Ac[0] = x50["C"][0]
    o0 = x50["O"][0]; Ao[0] = o0 if np.isfinite(o0) else Ac[0]
    for t in range(1, n):
        cp = x50["C"][t - 1]; s = x50["split"][t]; d = x50["div"][t]
        Ac[t] = Ac[t - 1] * s * (x50["C"][t] + d) / cp
        o = x50["O"][t]
        Ao[t] = Ac[t - 1] * s * (o + d) / cp if np.isfinite(o) else np.nan
    # 合成 00685L（research64retest.synth，rate＝0 ＝ researchMix70 原式），窗首日開盤用日內報酬反推
    Lo, Lc = R64.synth(Ao, Ac, 0, FEE685, 0.0)
    Lo[0] = Lc[0] / (1 + 2 * (Ac[0] / Ao[0] - 1))
    p85 = RH.load_px("00685L", msha).reindex(cal)
    a85 = pd.read_csv(io.StringIO(RH.git("show", f"{msha}:data/adj/00685L.csv")), dtype={"date": str})
    spl = np.ones(n); sp_rows = []
    for _, r in a85.iterrows():
        if r["kind"] != "分割":
            raise SystemExit(f"⛔ 00685L 未知事件 {r['kind']}")
        ratio = float(round(float(r["pre_close"]) / float(r["ref_price"])))
        spl[pos[r["date"]]] = ratio; sp_rows.append({"date": r["date"], "ratio": ratio})
    ts = pos[LIST685]
    assert np.isfinite(p85["close"].iloc[ts]) and not np.isfinite(p85["close"].iloc[ts - 1])
    k = (p85["close"].iloc[ts] / (Lc[ts] / Lc[ts - 1])) / Lc[ts - 1]
    C85 = np.r_[k * Lc[:ts], pd.Series(p85["close"].to_numpy(float)[ts:]).ffill().to_numpy()]
    O85 = np.r_[k * Lo[:ts], p85["open"].to_numpy(float)[ts:]]
    X["00685L"] = {"O": O85, "C": C85, "div": np.zeros(n), "split": spl, "splits": pd.DataFrame(sp_rows),
                   "synth_k": float(k), "Lo": Lo, "Lc": Lc}
    X["0050"]["Ac"] = Ac; X["0050"]["Ao"] = Ao
    # 條件指標（0050 全歷史、分割調整價）
    P = RH.load_px("0050", msha)["close"].dropna()
    adj = P.copy()
    for _, s in x50["splits"].iterrows():
        adj[adj.index < s["date"]] /= s["ratio"]
    di = pd.to_datetime(adj.index)
    hi52 = pd.Series(adj.to_numpy(), index=di).rolling("364D").max().to_numpy()
    sma200 = adj.rolling(200).mean().to_numpy()
    ind = pd.DataFrame({"adj": adj, "hi52": hi52, "sma200": sma200}, index=adj.index)
    ind["c4"] = ind["adj"] >= 0.95 * ind["hi52"]; ind["c5"] = ind["adj"] > ind["sma200"]
    ind = ind.reindex(cal); n_ffill = int(ind["adj"].isna().sum()); ind = ind.ffill()      # 0050 無收盤的日子沿用前一日指標
    assert not ind[["c4", "c5"]].isna().any().any(), "條件在日曆內有缺"
    c4 = ind["c4"].astype(bool); c5 = ind["c5"].astype(bool)
    # 大盤回落
    tf = sorted(glob.glob(TAIEX_GLOB))
    if not tf:
        raise SystemExit("⛔ 找不到 twse_taiex.csv")
    tx = pd.read_csv(tf[-1], dtype={"date": str}).set_index("date")["close"].astype(float)
    tdd = (tx / tx.cummax() - 1).reindex(cal)
    a = pd.Series(Ac, index=cal); add = (a / a.cummax() - 1)
    # 0050 還原在 2007-12-26 起才有 ⇒ 補用全歷史含息還原的高點：以 RH 早年事件建鏈（窗首前高點）
    full = RH.load_px("0050", msha)
    ev, sp = RH.load_events("0050", msha)
    fc = full["close"].ffill(); fac = [1.0]; dmap = dict(zip(ev["date"], ev["div"])); smap = dict(zip(sp["date"], sp["ratio"]))
    idx = list(fc.index)
    for i in range(1, len(idx)):
        d = idx[i]; fac.append(fac[-1] * smap.get(d, 1.0) * (fc.iloc[i] + dmap.get(d, 0.0)) / fc.iloc[i - 1])
    fa = pd.Series(fac, index=idx); fdd = (fa / fa.cummax() - 1).reindex(cal).ffill()
    nfb = int(tdd.isna().sum())
    # ⚠ 加權指數是價格指數（不含息），且 1990-02 高點 12,682 到 2020 才再過 ⇒ 2007～2019 幾乎天天「對歷史高點回落 ＞20%」，不適用；
    #   主口徑改用 0050 含息還原（2004-02 起全歷史）對歷史高點的回落；加權指數回落只列在 conditions_monthly.csv 參考
    assert not fdd.isna().any()
    regime = (fdd < -0.20).to_numpy()
    info = {"main": msha, "taiex_file": tf[-1], "taiex_last": str(tx.index.max()), "taiex_fallback_days": nfb,
            "fallback_in_dd": int(np.sum((tdd.isna()) & (fdd < -0.20))), "0050無收盤沿用前日指標日數": n_ffill, "synth_k": float(k), "00685L_splits": sp_rows,
            "0050_splits": x50["splits"].to_dict("records")}
    return cal, pos, X, c4.to_numpy(bool), c5.to_numpy(bool), regime.astype(bool), ind, info, tdd, fdd


# ───────────────────────── 模擬 ─────────────────────────
def sim(acct, tgt, method, tspec, rr, i0, i1, cal, X, c4, c5, regime, keep=False):
    assets, w = ACCTS[acct]; w = np.asarray(w, float); k = len(assets); n = i1 - i0 + 1
    M = tgt / SCALE; r0 = tgt * 12 / 1e6; resv = method >= 3
    new_year, ftax = RH.tax_fn(tspec)
    R = MX.reb_days(cal, i0, i1, "Y", 1) if k > 1 else np.zeros(n, bool)
    dts = pd.to_datetime(cal[i0:i1 + 1])
    st = {"u": np.zeros(k), "cost_sell": 0.0}
    V = np.empty(n); out = np.zeros(n); nav = np.empty(n); resA = np.empty(n)
    sales = []; divs = []; pays = []; rebs = []
    open_fb = 0
    depleted = None

    def px_open(t):
        nonlocal open_fb
        o = np.array([X[a]["O"][t] for a in assets])
        bad = ~np.isfinite(o)
        if bad.any():
            open_fb += 1
            o = np.where(bad, np.array([X[a]["C"][t - 1] for a in assets]), o)
        return o

    def sell(net, t, kind, cond):
        nonlocal depleted
        o = px_open(t); u = st["u"]; h = u * o; H = h.sum()
        G = net / (1 - SELLC)
        if G >= H - 1e-9:
            G = H; s = h.copy(); got = H * (1 - SELLC)
            if depleted is None:
                depleted = cal[t]
        else:
            Hn = H - G; d = h - w * Hn
            if np.all(d >= -1e-12):
                s = np.maximum(d, 0.0)
            else:
                s = np.zeros(k); s[int(np.argmax(h / H - w))] = G
            got = net
        st["u"] = u - s / o
        st["u"][np.abs(st["u"]) < 1e-12] = 0.0
        st["cost_sell"] += G * SELLC
        sales.append({"date": cal[t], "種類": kind, "條件": cond, "賣出總額": G, "成本": G * SELLC, "淨得": got,
                      **{f"賣{a}": s[q] for q, a in enumerate(assets)}, **{f"價{a}": o[q] for q, a in enumerate(assets)},
                      "權重前": (h / H).round(6).tolist() if H > 0 else None, "大盤回落>20%": bool(regime[t - 1]) if t > 0 else False})
        return got

    # 窗首：留第一個月現金（①②）或撥 24 個月水庫並付第一個月（③④⑤），其餘開盤建倉
    new_year()
    res = RES_M * M - M if resv else 0.0
    invest = V0 - M - res
    o = px_open(i0); cb = invest * REBC
    st["u"] = w * (invest - cb) / o
    out[0] = M; pays.append({"date": cal[i0], "發放": M, "條件": None})
    monthly2 = M
    year_last = {}  # 年 → 該年最後交易日的 nav
    for j in range(n):
        t = i0 + j
        if j > 0:
            if resv and rr > 0 and res > 0:
                res *= (1 + rr) ** ((dts[j] - dts[j - 1]).days / 365.0)
            if cal[t][:4] != cal[t - 1][:4]:
                year_last[cal[t - 1][:4]] = nav[j - 1]
                new_year()
            u = st["u"]
            for q, a in enumerate(assets):
                if u[q] > 0 and X[a]["split"][t] != 1.0:
                    u[q] *= X[a]["split"][t]
                d = X[a]["div"][t]
                if u[q] > 0 and d > 0:
                    g = u[q] * d; tx = ftax(g); nh = RH.NHI_RATE * g if g >= RH.NHI_MIN else 0.0
                    net = g - tx - nh; res += net
                    divs.append({"date": cal[t], "etf": a, "單位": u[q], "每單位配息": d, "給付": g, "稅": tx, "健保": nh, "淨": net})
            # 每月發放
            if cal[t][:7] != cal[t - 1][:7] and depleted is None:
                jan = cal[t][5:7] == "01"
                if method == 2 and jan:
                    monthly2 = r0 * V[j - 1] / 12
                need = monthly2 if method == 2 else M
                if method == 3:
                    if jan:
                        y2 = str(int(cal[t][:4]) - 2)
                        base = year_last.get(y2, 1.0)
                        cond = bool(nav[j - 1] / base - 1 > 0)
                    else:
                        cond = False
                elif method == 4:
                    cond = bool(c4[t - 1])
                elif method == 5:
                    cond = bool(c5[t - 1])
                else:
                    cond = None
                if method <= 2:
                    if res >= need - 1e-9:
                        res -= need
                    else:
                        got = sell(need - res, t, "每月", None); res = res + got - need
                else:
                    if cond:
                        top = need + RES_M * M - res
                        if top > 1e-9:
                            got = sell(top, t, "補水庫", True); res = res + got - need
                        else:
                            res -= need
                    elif res >= need - 1e-9:
                        res -= need
                    else:
                        got = sell(need - res, t, "被迫", False); res = res + got - need
                if depleted is not None:
                    need = need + min(res, 0.0); res = max(res, 0.0)
                res = max(res, 0.0) if abs(res) < 1e-6 else res
                out[j] += need; pays.append({"date": cal[t], "發放": need, "條件": cond})
            # 年度調回（B）
            if R[j] and st["u"].sum() > 0:
                o = px_open(t); h = st["u"] * o; H = h.sum()
                tr = 0.5 * np.abs(w * H - h).sum(); cc = tr * REBC
                st["u"] = w * (H - cc) / o
                rebs.append({"date": cal[t], "調動": tr, "成本": cc, "權重前": (h / H).round(6).tolist()})
        c = np.array([X[a]["C"][t] for a in assets])
        mv = float((st["u"] * c).sum())
        V[j] = mv + res; resA[j] = res
        nav[j] = (V[j] + out[j]) / V0 if j == 0 else nav[j - 1] * (V[j] + out[j]) / V[j - 1]
    r = dict(V=V, out=out, nav=nav, res=resA, sales=sales, divs=divs, pays=pays, rebs=rebs, depleted=depleted,
             cost_sell=st["cost_sell"], cost_build=cb, open_fb=open_fb, u_end=st["u"].copy())
    return r


def mdd_path(v):
    p = np.r_[1.0, v]; pk = np.maximum.accumulate(p); return float(((p - pk) / pk).min())


def summarize(r, cal, i0, i1):
    yrs = (pd.Timestamp(cal[i1]) - pd.Timestamp(cal[i0])).days / 365.25
    endt = (r["V"][-1] + r["out"].sum()) * SCALE
    days = cal[i0:i1 + 1]; ys = np.array([d[:4] for d in days])
    ycash = []
    for y in sorted(set(ys)):
        idx = np.flatnonzero(ys == y)
        full_start = idx[0] > 0 or days[0][5:] <= "01-08"
        ti = i0 + idx[-1]; nxt = ti + 1 < len(cal) and cal[ti + 1][:4] != y
        if full_start and nxt:
            ycash.append((y, r["out"][idx].sum() * SCALE / 12))
    sl = r["sales"]
    G = np.array([s["賣出總額"] for s in sl]) if sl else np.zeros(0)
    dd = np.array([s["大盤回落>20%"] for s in sl], bool) if sl else np.zeros(0, bool)
    forced = [s for s in sl if s["種類"] == "被迫"]
    worst = min(ycash, key=lambda x: x[1]) if ycash else ("", np.nan)
    return {"期末總額（每100萬）": endt, "換算年化": (endt / 1e6) ** (1 / yrs) - 1, "年數": yrs,
            "最大回落（市值＋水庫）": mdd_path(r["V"] / V0), "最低市值剩本金": float(np.min(r["V"]) / V0),
            "最低日": cal[i0 + int(np.argmin(r["V"]))], "期末市值＋水庫（每100萬）": r["V"][-1] * SCALE,
            "期末水庫（每100萬）": r["res"][-1] * SCALE, "累計領現（每100萬）": r["out"].sum() * SCALE,
            "提領到歸零": r["depleted"] or "否", "最差年每月現金": worst[1], "最差年": worst[0],
            "每月現金中位（完整年）": float(np.median([c for _, c in ycash])) if ycash else np.nan,
            "賣股次數": len(sl), "賣在大跌期次數比例": float(dd.mean()) if len(dd) else np.nan,
            "賣在大跌期金額比例": float(G[dd].sum() / G.sum()) if G.sum() > 0 else np.nan,
            "賣出總額（每100萬）": float(G.sum() * SCALE),
            "補水庫次數": sum(1 for s in sl if s["種類"] == "補水庫"), "被迫賣次數": len(forced),
            "被迫賣年份": ",".join(sorted({s["date"][:4] for s in forced})),
            "被迫賣在大跌期比例": float(np.mean([s["大盤回落>20%"] for s in forced])) if forced else np.nan,
            "賣股成本（每100萬）": r["cost_sell"] * SCALE, "建倉成本（每100萬）": r["cost_build"] * SCALE,
            "調回成本（每100萬）": sum(x["成本"] for x in r["rebs"]) * SCALE, "開盤缺價改用前收次數": r["open_fb"]}


def hd_rows(cal, pos, X, starts, i1, grid):
    rows = []
    for sn, d0 in starts.items():
        i0 = pos[d0]
        for tn, ts in TAXV.items():
            for a in (0.7, 0.5, 0.0):
                r = RH.sim(("0050", "0056"), (a, 1 - a), i0, i1, X, cal, V0, ts, "領現")
                yrs = (pd.Timestamp(cal[i1]) - pd.Timestamp(cal[i0])).days / 365.25
                endt = (r["V"][-1] + r["out"].sum()) * SCALE
                yr = RH.yearly(r, cal, i0, V0)
                cash = [y["稅後現金每100萬"] / 12 for y in yr]
                days = cal[i0:i1 + 1]; ys = np.array([d[:4] for d in days]); absc = []
                for y in [q["年"] for q in yr]:
                    absc.append(r["out"][ys == y].sum() * SCALE / 12)
                row = {"起點": sn, "稅版": tn, "方案": f"高股息 0050 {int(a*100)}／0056 {int(round((1-a)*100))}",
                       "期末總額（每100萬）": endt, "換算年化": (endt / 1e6) ** (1 / yrs) - 1,
                       "最大回落（帳戶市值）": RH.mdd(r["V"] / V0), "最低市值剩本金": float(np.min(r["V"]) / V0),
                       "累計領現（每100萬）": r["out"].sum() * SCALE,
                       "每月現金中位（每100萬年初市值）": float(np.median(cash)) if cash else np.nan,
                       "最差年每月現金（每100萬本金，元）": float(np.min(absc)) if absc else np.nan}
                if sn == "2007-12":
                    g = grid[(grid["窗"] == "全期") & (grid["本金"] == "50萬") & (grid["配息"] == "領現") &
                             (grid["稅版"] == HD_TAXN[tn]) & (grid["0050%"] == int(a * 100))].iloc[0]
                    row["csv期末總額"] = float(g["期末市值＋累計領現（每100萬）"]); row["csv換算年化"] = float(g["期末總額換算年化（領現不生息）"])
                    row["csv帳戶市值回落"] = float(g["帳戶市值回落"]); row["csv每月_中位"] = float(g["每月_中位"])
                    row["與csv一致"] = bool(abs(row["csv期末總額"] - endt) < 1e-3 and abs(row["csv帳戶市值回落"] - row["最大回落（帳戶市值）"]) < 1e-9)
                rows.append(row)
    return pd.DataFrame(rows)


def main():
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log"); open(LOGF, "w").close()
    log(f"===== researchWithdraw {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜裁定 seq391＋392＋393｜描述，不判、不計 N、不改六四 v1 =====")
    cal, pos, X, c4, c5, regime, ind, info, tdd, fdd = load_all()
    i1 = len(cal) - 1
    starts = {k: next(d for d in cal if d >= v) for k, v in START_REQ.items()}
    log(f"資料 main {info['main'][:10]}；日曆 {cal[0]}～{cal[-1]}（{len(cal)} 日）；起點 {starts}")
    log(f"00685L：{LIST685} 前為合成（research64retest.synth rate＝0，接合係數 k＝{info['synth_k']:.6g}）；分割 {info['00685L_splits']}；0050 分割 {info['0050_splits']}")
    log(f"大盤回落 >20%：0050 含息還原（2004-02 起）對歷史高點；加權指數（{info['taiex_file']}，至 {info['taiex_last']}）為價格指數且 1990 高點到 2020 才過，只列參考")
    rows = []; KEEP = {}
    for sn, d0 in starts.items():
        i0 = pos[d0]
        for acct in ACCTS:
            for tgt in TARGETS:
                for tn, ts in TAXV.items():
                    for m in METHODS:
                        for rr in ((0.0, 0.015) if m >= 3 else (0.0,)):
                            r = sim(acct, tgt, m, ts, rr, i0, i1, cal, X, c4, c5, regime)
                            s = summarize(r, cal, i0, i1)
                            rows.append({"起點": sn, "起": d0, "迄": cal[i1], "帳戶": acct, "每月目標": int(tgt), "稅版": tn,
                                         "方法": METHODS[m], "水庫利率": rr, **s})
                            if sn == "2007-12" and tn == "淨3.5%" and rr == 0.0:
                                KEEP[(acct, int(tgt), m)] = r
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "grid.csv"), index=False, encoding="utf-8-sig")
    grid = pd.read_csv(os.path.join(HERE, "resultsHighDiv", "grid_with_endcagr.csv"))
    hd = hd_rows(cal, pos, X, starts, i1, grid)
    hd.to_csv(os.path.join(OUT, "highdiv_side.csv"), index=False, encoding="utf-8-sig")
    log(f"[高股息全期重算 ＝ csv] {bool(hd['與csv一致'].dropna().all())}")
    # 抽樣明細
    for key, nm in (((("A", 3404, 1)), "A_3404_m1"), ((("B", 3404, 1)), "B_3404_m1"), ((("B", 3404, 4)), "B_3404_m4"), ((("A", 4649, 3)), "A_4649_m3")):
        r = KEEP[key]
        pd.DataFrame(r["sales"]).to_csv(os.path.join(OUT, f"sample_sales_full_3.5_{nm}.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(r["divs"]).to_csv(os.path.join(OUT, f"sample_divs_full_3.5_{nm}.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame(r["pays"]).to_csv(os.path.join(OUT, f"sample_pays_full_3.5_{nm}.csv"), index=False, encoding="utf-8-sig")
        pd.DataFrame({"date": cal[pos[starts['2007-12']]:], "V": r["V"], "res": r["res"], "out": r["out"]}).to_csv(
            os.path.join(OUT, f"sample_daily_full_3.5_{nm}.csv"), index=False, encoding="utf-8-sig")
        if r["rebs"]:
            pd.DataFrame(r["rebs"]).to_csv(os.path.join(OUT, f"sample_rebs_full_3.5_{nm}.csv"), index=False, encoding="utf-8-sig")
    # 條件月份
    ms = [t for t in range(1, len(cal)) if cal[t][:7] != cal[t - 1][:7]]
    cm = pd.DataFrame({"發放日": [cal[t] for t in ms], "月底": [cal[t - 1] for t in ms], "④近52週高": [bool(c4[t - 1]) for t in ms],
                       "⑤站上200日線": [bool(c5[t - 1]) for t in ms], "大盤回落>20%": [bool(regime[t - 1]) for t in ms],
                       "0050調整收盤": [ind["adj"].iloc[t - 1] for t in ms], "52週高": [ind["hi52"].iloc[t - 1] for t in ms],
                       "200日線": [ind["sma200"].iloc[t - 1] for t in ms], "加權回落": [tdd.iloc[t - 1] for t in ms], "0050還原回落": [fdd.iloc[t - 1] for t in ms]})
    cm.to_csv(os.path.join(OUT, "conditions_monthly.csv"), index=False, encoding="utf-8-sig")
    log(f"[條件月份比例] ④ {cm['④近52週高'].mean():.1%}｜⑤ {cm['⑤站上200日線'].mean():.1%}｜大盤回落>20% {cm['大盤回落>20%'].mean():.1%}（{len(cm)} 個月底）")
    meta = {"定位": "描述，不判、不計 N、不改六四 v1；這是描述，不是買賣建議", **info, "起點": starts, "迄": cal[i1],
            "本金模擬": V0, "目標每月（每100萬）": TARGETS, "賣股成本": SELLC, "建倉與調回成本": REBC, "00685L合成": "research64retest.synth(rate=0)＝researchMix70 原式；0050 含息日報酬×2、扣 0.3%/年",
            "水庫": {"上限月數": RES_M, "利率": [0.0, 0.015]}, "稅": list(TAXV), "健保": {"費率": RH.NHI_RATE, "單筆門檻": RH.NHI_MIN}}
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, default=str)
    # 精簡顯示
    for tn in TAXV:
        for sn in starts:
            log(f"\n── 起點 {sn}｜{tn}｜水庫利率 0% ──")
            for tgt in TARGETS:
                for acct in ACCTS:
                    x = df[(df["起點"] == sn) & (df["稅版"] == tn) & (df["每月目標"] == int(tgt)) & (df["帳戶"] == acct) & (df["水庫利率"] == 0.0)]
                    for _, z in x.iterrows():
                        log(f"  {int(tgt)} {acct} {z['方法']:<10} 總額 {z['期末總額（每100萬）']/1e4:7.1f} 萬｜年化 {z['換算年化']:6.2%}｜回落 {z['最大回落（市值＋水庫）']:7.2%}｜"
                            f"最低剩 {z['最低市值剩本金']:.2f}｜最差年月 {z['最差年每月現金']:,.0f}｜賣 {z['賣股次數']} 次 大跌期 {z['賣在大跌期金額比例']:.0%}（金額）｜"
                            f"被迫 {z['被迫賣次數']}（{z['被迫賣年份']}）｜歸零 {z['提領到歸零']}")
                hdx = hd[(hd["起點"] == sn) & (hd["稅版"] == tn)]
                for _, z in hdx.iterrows():
                    log(f"  {int(tgt)} 高股息 {z['方案']} 總額 {z['期末總額（每100萬）']/1e4:7.1f} 萬｜年化 {z['換算年化']:6.2%}｜回落 {z['最大回落（帳戶市值）']:7.2%}｜最低剩 {z['最低市值剩本金']:.2f}｜"
                        f"月中位 {z['每月現金中位（每100萬年初市值）']:,.0f}") if tgt == TARGETS[0] else None
    log("完成。")


if __name__ == "__main__":
    main()

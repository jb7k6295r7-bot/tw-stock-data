# -*- coding: utf-8 -*-
"""部分 0050 換高股息 ETF 的稅後現金流描述（裁定 seq386＋seq387 更正稅率段）。回測線，2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchHighDiv
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchHighDiv_check.py

⛔ 定位：描述，不判合格、不計 N、不改任何規則。這是描述，不是買賣建議。
═══ 設計（seq386／seq387 逐項）═══
 主臂   0050 ＋ 0056（上市首日 2007-12-26 起）；0050 佔 100／70／50／0%
 短窗臂 0050 ＋ 00878（上市首日 2020-07-20 起）同配比，只列 2020～今，⛔ 不與主臂並排比年化
 再平衡 每年 1 月第一個交易日開盤調回（researchMix70.reb_days rule="Y", month=1，六四 v1 同一支）；
        成本照六四 v1：ETF 0.385% × 調動金額（窗首建倉與每次調回都扣，researchMix70.sim 同式）
 配息   主：領現金、不再投入（現金不計利息）；對照：配息稅後於除息日收盤再投入同一檔（買進手續費 0.1425%）
        配息金額 ＝ 除息事件（早年 data/early/exright 的 value；2015 起 data/adj 的 pre_close − ref_price，與 value 同式）
        0050 2025-06-18 分割 1→4：持有單位 ×4（data/adj kind＝分割）
 價格   未還原：2015 起 tw-stock-data origin/main data/stocks；2007-12～2014 早年 3edc0e2206 data/early/daily
 稅     合併計稅：邊際 12%（淨 3.5%）、20%（淨 11.5%）兩版；8.5% 抵減每戶每年上限 8 萬，超過部分以全額邊際稅率計
        （逐筆：抵減 ＝ min(8.5%×股利, 8 萬 − 今年已抵)）；分開計稅 28% 一列；另跑「不扣稅與健保」一列當拆解基準
        ⚠ 現行稅制（2018 起的 8.5% 抵減）與健保參數套用全期（假設性），稅率參數是使用者自報、以財政部公告為準，級距變動要重算
 健保   二代健保補充保費 2.11%，單筆（單檔單次）給付 ≥ 2 萬才扣；本金 50 萬、250 萬各一版（以元計，決定單次是否達 2 萬）
 54C    資料庫沒有 ETF 配息組成（股利所得 vs 收益平準金／資本利得）⇒ 全額當股利所得（保守，稅與健保偏高）
 期間   全期 2007-12-26～最新；2007～2016（2007-12-26～2016-12-30）；2017～今（2017-01-03～最新）
═══ 指標 ═══
 稅後年化   時間加權：淨值[t] ＝ 淨值[t−1] ×（市值[t] ＋ 當日領出現金[t]）÷ 市值[t−1]；年化與回落用 researchLev2.perf（245 日／年）
 市值回落   領現版帳戶市值本身（不含已領現金）的最大回落（描述）
 每年現金   完整日曆年：當年稅後配息 ÷ 年初市值 × 100 萬（中位、最差年；÷12 ＝ 每月）；稅前股利同法（對照級距）
 對 0050    同窗、同本金、同稅版、同配息處理的 100% 0050；年化差 ＝ 年化相減；
            月分群 95% CI：月報酬差 d_m 的平均 ×12 ± 1.96 × sd(d_m)/√M × 12（假設月與月獨立）
 稅健保吃掉 年化（不扣稅健保）− 稅後年化（pp）；另報 每年（稅＋健保）÷ 年初市值 的平均（pp）
輸出 backtest/resultsHighDiv/
"""
from __future__ import annotations

import io
import json
import os
import subprocess

import numpy as np
import pandas as pd

from . import researchLev2 as L2
from . import researchMix70 as MX

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsHighDiv")
DB = os.path.expanduser("~/tw-stock-data")
MAIN_REF = "origin/main"
EARLY_SHA = "3edc0e2206"
MAIN_START = "2015-01-05"
COST = MX.COST                     # 0.385%（六四 v1）
BUYCOST = 0.001425                 # 再投入的買進手續費
NHI_RATE, NHI_MIN = 0.0211, 20000.0
CREDIT_RATE, CREDIT_CAP = 0.085, 80000.0
TAXES = {"不扣稅健保": None, "合併 淨3.5%（12%級）": ("comb", 0.12), "合併 淨11.5%（20%級）": ("comb", 0.20), "分開 28%": ("sep", 0.28)}
PRINCIPALS = {"50萬": 500_000.0, "250萬": 2_500_000.0}
ALLOCS = (1.0, 0.7, 0.5, 0.0)
MODES = ("領現", "再投入")
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


def git(*a, ok_fail=False):
    r = subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True)
    if r.returncode != 0:
        if ok_fail:
            return ""
        raise SystemExit(f"⛔ git {' '.join(a)}：{r.stderr}")
    return r.stdout


DCOLS = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
         "shares", "transactions", "price_basis", "last_price"]
ECOLS = ["date", "stock_id", "pre_close", "ref_price", "value", "kind", "open_base", "limit_up", "limit_down", "ex_div_ref"]


def load_px(sid, msha):
    m = pd.read_csv(io.StringIO(git("show", f"{msha}:data/stocks/{sid}.csv")), dtype=str)
    m = m[["date", "open", "close"]]
    e = git("grep", "-h", f"_{sid},", EARLY_SHA, "--", "data/early/daily/", ok_fail=True)
    if e:
        d = pd.read_csv(io.StringIO(e), header=None, names=DCOLS, dtype=str)
        d = d[(d["stock_id"] == sid) & (d["date"] < MAIN_START)][["date", "open", "close"]]
        m = pd.concat([d, m[m["date"] >= MAIN_START]])
    for k in ("open", "close"):
        m[k] = pd.to_numeric(m[k], errors="coerce")
    m.loc[(m["open"] <= 0) | (m["close"] <= 0), ["open", "close"]] = np.nan
    return m.sort_values("date").drop_duplicates("date").set_index("date")


def load_events(sid, msha):
    """回 (除息 DataFrame[date, div, src]、分割 DataFrame[date, ratio])。"""
    rows = []
    e = git("grep", "-h", f",{sid},", EARLY_SHA, "--", "data/early/exright/", ok_fail=True)
    if e:
        d = pd.read_csv(io.StringIO(e), header=None, names=ECOLS, dtype={"date": str, "stock_id": str})
        d = d[(d["stock_id"] == sid) & (d["date"] < MAIN_START)]
        assert set(d["kind"]) <= {"息"}, f"{sid} 早年有非息事件"
        for _, r in d.iterrows():
            v = float(r["value"]); dd = round(float(r["pre_close"]) - float(r["ref_price"]), 6)
            assert abs(v - dd) < 1e-6, (sid, r["date"], v, dd)
            rows.append({"date": r["date"], "div": v, "src": "early/exright value"})
    a = pd.read_csv(io.StringIO(git("show", f"{msha}:data/adj/{sid}.csv")), dtype={"date": str})
    sp = []
    for _, r in a.iterrows():
        if r["date"] < MAIN_START:
            continue
        if r["kind"] == "息":
            rows.append({"date": r["date"], "div": round(float(r["pre_close"]) - float(r["ref_price"]), 6), "src": "adj pre−ref"})
        elif r["kind"] == "分割":
            sp.append({"date": r["date"], "ratio": float(round(float(r["pre_close"]) / float(r["ref_price"])))})
        else:
            raise SystemExit(f"⛔ {sid} 未知事件 {r['kind']}")
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True), pd.DataFrame(sp, columns=["date", "ratio"])


def load(msha):
    cal_m = pd.read_csv(io.StringIO(git("show", f"{msha}:data/meta/calendar_twse.csv")), dtype=str)["date"].tolist()
    P = {s: load_px(s, msha) for s in ("0050", "0056", "00878")}
    early = [d for d in P["0050"].index if "2007-12-26" <= d < MAIN_START]
    cal = early + [d for d in cal_m if d >= MAIN_START]
    pos = {d: i for i, d in enumerate(cal)}
    for s, df in P.items():
        extra = sorted(set(df.index[df.index >= "2007-12-26"]) - set(cal))
        assert not extra, f"{s} 有日曆外日期 {extra[:5]}"
    X = {}
    for s, df in P.items():
        r = df.reindex(cal)
        ev, sp = load_events(s, msha)
        div = np.zeros(len(cal)); spl = np.ones(len(cal))
        for _, e in ev.iterrows():
            if e["date"] >= "2007-12-26":
                assert e["date"] in pos, f"{s} 除息日 {e['date']} 不在日曆"
                div[pos[e["date"]]] = e["div"]
        for _, e in sp.iterrows():
            spl[pos[e["date"]]] = e["ratio"]
        X[s] = {"O": r["open"].to_numpy(float), "C": r["close"].ffill().to_numpy(float), "div": div, "split": spl,
                "events": ev, "splits": sp, "first": str(df.index[df["close"].notna()].min())}
    return cal, pos, X


def tax_fn(spec):
    """回傳一個逐筆計稅的閉包工廠：new_year() 重置年度抵減額度；f(g) 回該筆稅額。"""
    st = {"used": 0.0}

    def new_year():
        st["used"] = 0.0

    def f(g):
        if spec is None:
            return 0.0
        kind, marg = spec
        if kind == "sep":
            return marg * g
        cr = min(CREDIT_RATE * g, max(CREDIT_CAP - st["used"], 0.0)); st["used"] += cr
        return marg * g - cr
    return new_year, f


def sim(assets, w, i0, i1, X, cal, V0, tspec, mode):
    """回傳逐日 dict：V（市值，元）、out（領出現金）、gross、tax、nhi、cost、nav（時間加權）。"""
    w = np.asarray(w, float); k = len(assets); n = i1 - i0 + 1
    R = MX.reb_days(cal, i0, i1, "Y", 1)
    new_year, ftax = tax_fn(tspec); nhi_on = tspec is not None
    u = np.zeros(k); idle = V0; pend = True
    V = np.empty(n); out = np.zeros(n); gross = np.zeros(n); tax = np.zeros(n); nhi = np.zeros(n); cost = np.zeros(n); nav = np.empty(n)
    trades = []; ev_log = []
    for j in range(n):
        t = i0 + j
        if j > 0 and cal[t][:4] != cal[t - 1][:4]:
            new_year()
        if j == 0:
            new_year()
        # 1) 公司行動（屬於前一日收盤的持有）
        for q, a in enumerate(assets):
            if u[q] > 0 and X[a]["split"][t] != 1.0:
                u[q] *= X[a]["split"][t]
            d = X[a]["div"][t]
            if u[q] > 0 and d > 0:
                g = u[q] * d; tx = ftax(g); nh = NHI_RATE * g if (nhi_on and g >= NHI_MIN) else 0.0
                net = g - tx - nh
                gross[j] += g; tax[j] += tx; nhi[j] += nh
                if mode == "領現":
                    out[j] += net
                else:
                    c = X[a]["C"][t]; cc = net * BUYCOST; u[q] += (net - cc) / c; cost[j] += cc
                ev_log.append({"date": cal[t], "etf": a, "單位": u[q], "每單位配息": d, "給付": g, "稅": tx, "健保": nh, "淨": net})
        # 2) 調回
        if j > 0 and R[j]:
            pend = True
        if pend:
            o = np.array([X[a]["O"][t] for a in assets])
            need = (u > 0) | (w > 0)
            if np.all(np.isfinite(o[need])):
                hold = np.where(u > 0, u * np.where(np.isfinite(o), o, 0), 0.0); Vt = hold.sum() + idle
                tr = 0.5 * (np.abs(w * Vt - hold).sum() + abs((1 - w.sum()) * Vt - idle))
                cc = tr * COST; V2 = Vt - cc
                with np.errstate(invalid="ignore", divide="ignore"):
                    u = np.where(w > 0, w * V2 / o, 0.0)
                idle = (1 - w.sum()) * V2; pend = False; cost[j] += cc
                trades.append({"date": cal[t], "調動": tr, "成本": cc, "前市值": Vt, "權重前": (hold / Vt).tolist()})
        c = np.array([X[a]["C"][t] for a in assets])
        V[j] = float(np.where(u > 0, u * c, 0.0).sum() + idle)
        nav[j] = (V[j] + out[j]) / V0 if j == 0 else nav[j - 1] * (V[j] + out[j]) / V[j - 1]
    return dict(V=V, out=out, gross=gross, tax=tax, nhi=nhi, cost=cost, nav=nav, trades=trades, ev=ev_log)


def mdd(path):
    p = np.r_[1.0, path]; pk = np.maximum.accumulate(p); return float(((p - pk) / pk).min())


def monthly(nav, cal, i0):
    ms = np.array([d[:7] for d in cal[i0:i0 + len(nav)]])
    ends = np.r_[np.flatnonzero(ms[1:] != ms[:-1]), len(nav) - 1]
    lv = np.r_[1.0, nav[ends]]
    return lv[1:] / lv[:-1] - 1, ms[ends]


def yearly(r, cal, i0, V0):
    days = cal[i0:i0 + len(r["V"])]; ys = np.array([d[:4] for d in days])
    rows = []
    for y in sorted(set(ys)):
        idx = np.flatnonzero(ys == y)
        full_start = idx[0] > 0 or days[0][5:] <= "01-08"          # 窗首在 1 月第一週也算完整
        ti = i0 + idx[-1]                                           # 該年在窗內最後一日；日曆下一日已是次年 ⇒ 該年已結束
        nxt_year = ti + 1 < len(cal) and cal[ti + 1][:4] != y
        if not (full_start and nxt_year):
            continue
        Vs = r["V"][idx[0] - 1] if idx[0] > 0 else V0
        g = r["gross"][idx].sum(); tx = r["tax"][idx].sum(); nh = r["nhi"][idx].sum()
        rows.append({"年": y, "年初市值": Vs, "股利每100萬": g / Vs * 1e6, "稅後現金每100萬": (g - tx - nh) / Vs * 1e6,
                     "稅健保佔年初市值": (tx + nh) / Vs, "稅": tx, "健保": nh, "股利元": g})
    return rows


def main():
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log"); open(LOGF, "w").close()
    msha = git("rev-parse", MAIN_REF).strip(); esha = git("rev-parse", EARLY_SHA).strip()
    log(f"===== researchHighDiv {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜裁定 seq386＋seq387｜描述，不判合格、不計 N =====")
    log(f"資料：tw-stock-data {MAIN_REF} {msha[:10]}（2015 起）＋早年 {esha[:10]}（2007-12～2014）")
    cal, pos, X = load(msha)
    last = cal[-1]
    WINS = {"全期": ("2007-12-26", last, "0056"), "2007～2016": ("2007-12-26", "2016-12-30", "0056"),
            "2017～今": ("2017-01-03", last, "0056"), "00878 短窗 2020～今": (X["00878"]["first"], last, "00878")}
    log(f"日曆 {cal[0]}～{last}（{len(cal)} 日）；首日 0056 {X['0056']['first']}、00878 {X['00878']['first']}")
    for s in X:
        ev = X[s]["events"]; ev = ev[ev["date"] >= "2007-12-26"]
        log(f"[除息] {s} {len(ev)} 筆：" + "，".join(f"{r.date}:{r.div:g}" for r in ev.itertuples()) +
            (f"｜分割 {X[s]['splits'].to_dict('records')}" if len(X[s]["splits"]) else ""))
    rows = []; RES = {}; yrows = []
    for wn, (d0, d1, hd) in WINS.items():
        i0, i1 = pos[d0], pos[d1]
        for pn, V0 in PRINCIPALS.items():
            for mode in MODES:
                base = {}
                for tn, ts in TAXES.items():
                    for a in ALLOCS:
                        r = sim(("0050", hd), (a, 1 - a), i0, i1, X, cal, V0, ts, mode)
                        RES[(wn, pn, mode, tn, a)] = r
                for tn, ts in TAXES.items():
                    rb = RES[(wn, pn, mode, tn, 1.0)]; mb, _ = monthly(rb["nav"], cal, i0)
                    cb, _ = L2.perf(rb["nav"])
                    for a in ALLOCS:
                        r = RES[(wn, pn, mode, tn, a)]; r0 = RES[(wn, pn, mode, "不扣稅健保", a)]
                        c, m = L2.perf(r["nav"]); c0, _ = L2.perf(r0["nav"])
                        mp, _ = monthly(r["nav"], cal, i0); dm = mp - mb; M = len(dm)
                        md = dm.mean() * 12; se = dm.std(ddof=1) / np.sqrt(M) * 12 if M > 1 else np.nan
                        yr = yearly(r, cal, i0, V0)
                        for y in yr:
                            yrows.append({"窗": wn, "本金": pn, "配息": mode, "稅版": tn, "0050%": int(a * 100), **y})
                        cash = np.array([y["稅後現金每100萬"] for y in yr]); divs = np.array([y["股利每100萬"] for y in yr])
                        drag = np.array([y["稅健保佔年初市值"] for y in yr])
                        ymin = yr[int(np.argmin(cash))]["年"] if len(yr) else ""
                        endw = (r["V"][-1] + r["out"].sum()) / V0 * 1e6
                        rows.append({"窗": wn, "高股息": hd, "本金": pn, "配息": mode, "稅版": tn, "0050%": int(a * 100), f"{hd}%": int(round((1 - a) * 100)),
                                     "起": d0, "迄": d1, "稅後年化": c, "最大回落": m, "年化÷|MDD|": L2.ratio(c, m), "帳戶市值回落": mdd(r["V"] / V0),
                                     "每100萬每年稅後現金_中位": float(np.median(cash)) if len(cash) else np.nan,
                                     "每100萬每年稅後現金_最差年": float(cash.min()) if len(cash) else np.nan, "最差年": ymin,
                                     "每月_中位": float(np.median(cash)) / 12 if len(cash) else np.nan,
                                     "每月_最差年": float(cash.min()) / 12 if len(cash) else np.nan,
                                     "每100萬每年股利_中位": float(np.median(divs)) if len(divs) else np.nan,
                                     "每100萬每年股利_最高": float(divs.max()) if len(divs) else np.nan,
                                     "對100%0050年化差": c - cb, "月差均值×12": md, "CI低": md - 1.96 * se, "CI高": md + 1.96 * se, "月數": M,
                                     "稅健保吃掉年化pp": c0 - c, "稅健保每年佔年初市值_平均": float(drag.mean()) if len(drag) else np.nan,
                                     "期末市值＋累計領現（每100萬）": endw, "完整年數": len(yr),
                                     "健保扣到的次數": int(sum(1 for e in r["ev"] if e["健保"] > 0)), "配息次數": len(r["ev"]),
                                     "調回次數": len(r["trades"]) - 1, "成本合計佔本金": r["cost"].sum() / V0})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "grid.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(yrows).to_csv(os.path.join(OUT, "yearly.csv"), index=False, encoding="utf-8-sig")
    # 抽樣：全期 50萬 領現 合併 3.5% 50/50 的逐筆配息與調回（給 _check 手算）
    r = RES[("全期", "50萬", "領現", "合併 淨3.5%（12%級）", 0.5)]
    pd.DataFrame(r["ev"]).to_csv(os.path.join(OUT, "sample_events_full_50w_cash_3.5_5050.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(r["trades"]).to_csv(os.path.join(OUT, "sample_trades_full_50w_cash_3.5_5050.csv"), index=False, encoding="utf-8-sig")
    meta = {"定位": "描述，不判合格、不計 N、不改規則；這是描述，不是買賣建議", "資料 main": msha, "資料 早年": esha, "日曆": [cal[0], last, len(cal)],
            "窗": {k: v[:2] for k, v in WINS.items()}, "成本": {"再平衡與建倉": COST, "再投入買進": BUYCOST},
            "稅": {"抵減率": CREDIT_RATE, "每戶上限": CREDIT_CAP, "版本": list(TAXES)}, "健保": {"費率": NHI_RATE, "單筆門檻": NHI_MIN},
            "54C": "資料庫無 ETF 配息組成 ⇒ 全額當股利所得（保守）",
            "除息": {s: X[s]["events"][X[s]["events"]["date"] >= "2007-12-26"].to_dict("records") for s in X},
            "分割": {s: X[s]["splits"].to_dict("records") for s in X}}
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, default=str)
    show = df[(df["配息"] == "領現") & (df["本金"] == "50萬") & (df["稅版"].isin(["合併 淨3.5%（12%級）", "合併 淨11.5%（20%級）"]))]
    for _, x in show.iterrows():
        log(f"[{x['窗']}｜{x['稅版']}｜0050 {x['0050%']}%] 年化 {x['稅後年化']:.2%}｜MDD {x['最大回落']:.2%}｜比 {x['年化÷|MDD|']:.2f}｜"
            f"現金中位 {x['每100萬每年稅後現金_中位']/1e4:.2f} 萬（月 {x['每月_中位']:,.0f}）最差 {x['每100萬每年稅後現金_最差年']/1e4:.2f} 萬（{x['最差年']}）｜"
            f"差 {x['對100%0050年化差']:+.2%} [{x['CI低']:+.2%},{x['CI高']:+.2%}]｜稅健保吃 {x['稅健保吃掉年化pp']:.2%}")
    log("完成。")


if __name__ == "__main__":
    main()

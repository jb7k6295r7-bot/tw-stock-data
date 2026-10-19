# -*- coding: utf-8 -*-
"""VIX 飆高後買進描述（使用者問「VIX 如果出現了（飆高），可不可以買？」）。回測線計算子代理。
⛔ 描述，不是買賣建議；⛔ 不計 N、不判合格、不是登錄件。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXbuy
    查核：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchVIXbuy_check

重用（import，不改）researchUSC13 的資料讀取（load_vix／load_us／load_tw）、段（segments，段止 ＝ VIX 收盤 ≤ 20）、
時差（buy_index：VIX 日期 d ⇒ 市場日期 ＞ d 的第一個有效開盤；台股 ＝ 台北 d＋1 含之後第一個 0050 K 棒日開盤）與 dd_recover。

定義（寫於 2026-10-20，台北）：
 B1 觸發 ＝ 每個門檻（30／40／50／75）各自的「段起日」（不在段內時 VIX 收盤 ≥ 門檻的第一天；段止 ＝ 之後第一個 VIX 收盤 ≤ 20）。
    美股段 1990-01-02～2026-09-30；台股段 2003-06-30 起（＝ C13-7）。
 B2 買進 ＝ buy_index 位置的【開盤】（^SP500TR 開 ＝ ^GSPC 開 × TR÷GSPC；0050 還原開）；成本不計。
 B3 持有期 h ＝ 3／6／12／36／60 個月（日曆）：出場 ＝ 日期 ≤ 買進日 ＋ h 個月 的最後一個交易日收盤；
    買進日 ＋ h 個月 ＞ 資料末日 ⇒ 該格「未滿期」不計。報酬 ＝ 出場收盤 ÷ 買價 − 1（含息還原）。
 B4 最深與回本：
    ① 段內（＝ C13-8 修訂版，dd_recover 原函式）：買進日起到「段止日之後第一個交易日」最低收盤 ÷ 買價 − 1（取 min 0）；
       回本 ＝ 該最低點之後第一個收盤 ≥ 買價的交易日距買進日交易日數。
    ② 1 年內：同式，窗 ＝ 買進日起到買進日 ＋ 12 個月的最後一個交易日；回本可在窗外。
 B5 隨機對照（同期間所有交易日）：美股 ＝ 1990-01-02 起每個有效開盤日、台股 ＝ 0050 序列每個有效開盤日，
    當天開盤買、同 B3 持有期 ⇒ 報酬分布（平均、中位、勝率 ＝ 報酬 ＞ 0 的比例）。
    百分位：(a) 觸發組平均在「隨機抽同樣檔數的日子取平均」10,000 次分布中的百分位（seed 20261020，不放回）；
           (b) 觸發組中位在單日分布中的百分位；(c) 觸發組每筆在單日分布百分位的平均。
    超額 ＝ 觸發組平均 − 全部日平均（＝ 閒錢在 VIX 飆高時一次投入，相對「那天剛好有錢投入的平均日」多賺的部分）。
 B6 「VIX ≥ 30 段內任一天買」：≥30 段的段起日（含）到段止日（不含）之間每個 VIX 日 ⇒ 同 B2 買進（同一買進日去重），同 B3 持有期；
    另列「任一個 VIX 收盤 ≥ 30 的日子」的同式結果。

⛔⛔ 私有資料：us-stock-data 私有 ⇒ resultsVIXbuy/ 只放彙總與事件層級（每段的觸發日、VIX、買進日、各持有期報酬、最深、回本日數）——
   比照 C13_segments.csv 的事件彙總先例；⛔ 不放逐日價格。隨機對照的逐日報酬只在記憶體。
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC13 as C

OUT = os.path.expanduser("~/tw-p17/backtest/resultsVIXbuy")
THRS = (30.0, 40.0, 50.0, 75.0)
HM = (3, 6, 12, 36, 60)
HN = {3: "3個月", 6: "6個月", 12: "1年", 36: "3年", 60: "5年"}
NBOOT = 10000
SEED = 20261020
DISC = "描述，不是買賣建議"


def jdump(obj, name):
    os.makedirs(OUT, exist_ok=True)

    def cv(o):
        if isinstance(o, dict):
            return {str(k): cv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [cv(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(cv(obj), open(os.path.join(OUT, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def exit_index(dates, hm):
    """每個位置 t ⇒ 日期 ≤ dates[t] ＋ hm 個月 的最後一個位置；超過資料末日 ⇒ −1。"""
    dt = pd.to_datetime(pd.Series(dates))
    tgt = (dt + pd.DateOffset(months=hm)).dt.strftime("%Y-%m-%d").to_numpy(str)
    e = np.searchsorted(dates, tgt, side="right") - 1
    e[tgt > dates[-1]] = -1
    return e


def all_day_returns(X):
    """每個有效開盤日 t 開盤買、持有 hm 個月的報酬（未滿期 NaN）。"""
    o, cf, ok = X["o"], X["cf"], X["ok"]
    R = {}
    for hm in HM:
        e = exit_index(X["dates"], hm)
        r = np.full(len(o), np.nan)
        m = ok & (e >= 0)
        r[m] = cf[e[m]] / o[m] - 1
        R[hm] = r
    return R


def stats(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "平均": None, "中位": None, "勝率": None, "最差": None, "最好": None}
    return {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x)), "勝率": float((x > 0).mean()),
            "最差": float(x.min()), "最好": float(x.max())}


def pct_rank(pool, v):
    """v 在 pool 中的百分位（≤ v 的比例，中間值取一半）。"""
    pool = np.asarray(pool, float)
    return float(((pool < v).sum() + 0.5 * (pool == v).sum()) / len(pool))


def boot_pct(pool, n, v, rng):
    pool = np.asarray(pool, float)
    idx = np.array([rng.choice(len(pool), n, replace=False) for _ in range(NBOOT)])
    means = pool[idx].mean(axis=1)
    return pct_rank(means, v), float(np.percentile(means, 5)), float(np.percentile(means, 95))


def window_dd(X, b, E):
    e = int(E[b])
    we = e if e >= 0 else len(X["dates"]) - 1
    dd, days, okr, tr = C.dd_recover(X["o"], X["cf"], b, we)
    return dd, (days if okr is not False else None), (e >= 0)


def run_market(X, vd, vv, lo, label, rng):
    nv = C.next_valid(X["ok"]); n = len(X["dates"])
    bidx = C.buy_index(vd, X["dates"], nv)
    AR = all_day_returns(X)
    E12 = exit_index(X["dates"], 12)
    # 隨機對照只取同期間：VIX 有資料以後（美股 1990-01-02；台股序列首日 2004-02-11 已晚於 2003-06-30）
    base_m = X["dates"] >= max(vd[0], lo or vd[0])
    ev_rows = []; summ = {}
    for thr in THRS:
        segs = C.segments(vd, vv, thr, lo)
        rows = []
        for g in segs:
            j = g["_j"]; b = int(bidx[j])
            r = {"市場": label, "門檻": thr, "段起日": g["段起日"], "段起VIX收盤": g["段起VIX收盤"], "段內最高VIX收盤": g["段內最高VIX收盤"],
                 "段止日（VIX≤20）": g["段止日（VIX≤20）"]}
            if b >= n:
                r["買進日"] = "無資料"; rows.append(r); continue
            r["買進日"] = X["dates"][b]; r["_b"] = b
            for hm in HM:
                r[f"報酬_{HN[hm]}"] = AR[hm][b]
                r[f"百分位_{HN[hm]}"] = pct_rank(AR[hm][base_m & np.isfinite(AR[hm])], AR[hm][b]) if np.isfinite(AR[hm][b]) else np.nan
            we = int(bidx[g["_je"]])
            dd, days, okr, tr = C.dd_recover(X["o"], X["cf"], b, we)
            r["段內最深"] = dd; r["段內最深_回本交易日"] = days if okr is not False else None
            r["段內最深_回本"] = "段內收盤從沒低於買價" if okr is None else ("是" if okr else "未回本")
            d1, rd1, full1 = window_dd(X, b, E12)
            r["1年內最深"] = d1; r["1年內最深_回本交易日"] = rd1; r["1年窗滿期"] = full1
            rows.append(r)
        ev_rows += rows
        S = {"段數": len(segs), "有市場資料的段數": sum(1 for r in rows if "_b" in r)}
        if thr >= 50:
            S["註"] = "樣本極少"
        for hm in HM:
            x = np.array([r[f"報酬_{HN[hm]}"] for r in rows if "_b" in r], float)
            pool = AR[hm][base_m & np.isfinite(AR[hm])]
            st = stats(x); bs = stats(pool)
            cell = {"觸發組": st, "全部日": bs}
            if st["n"] > 0:
                cell["超額平均（觸發−全部日）"] = st["平均"] - bs["平均"]
                cell["超額中位"] = st["中位"] - bs["中位"]
                bp, b5, b95 = boot_pct(pool, st["n"], st["平均"], rng) if st["n"] < len(pool) else (np.nan, np.nan, np.nan)
                cell["觸發組平均在隨機同檔數平均中的百分位"] = bp
                cell["隨機同檔數平均_5%～95%"] = [b5, b95]
                cell["觸發組中位在單日分布的百分位"] = pct_rank(pool, st["中位"])
                cell["觸發組每筆百分位的平均"] = float(np.nanmean([r[f"百分位_{HN[hm]}"] for r in rows if "_b" in r]))
            S[HN[hm]] = cell
        dds = [r["段內最深"] for r in rows if "_b" in r]
        rcs = [r["段內最深_回本交易日"] for r in rows if "_b" in r and r["段內最深_回本交易日"] is not None]
        d1s = [r["1年內最深"] for r in rows if "_b" in r]
        r1s = [r["1年內最深_回本交易日"] for r in rows if "_b" in r and r["1年內最深_回本交易日"] is not None]
        S["段內最深"] = {"中位": float(np.median(dds)) if dds else None, "最差": float(np.min(dds)) if dds else None}
        S["段內最深_回本交易日"] = {"中位": float(np.median(rcs)) if rcs else None, "最長": int(np.max(rcs)) if rcs else None,
                              "未回本段數": sum(1 for r in rows if r.get("段內最深_回本") == "未回本")}
        S["1年內最深"] = {"中位": float(np.median(d1s)) if d1s else None, "最差": float(np.min(d1s)) if d1s else None,
                       "1年窗未滿期段數": sum(1 for r in rows if "_b" in r and not r["1年窗滿期"])}
        S["1年內最深_回本交易日"] = {"中位": float(np.median(r1s)) if r1s else None, "最長": int(np.max(r1s)) if r1s else None,
                                "未回本段數": sum(1 for r in rows if "_b" in r and r["1年內最深_回本交易日"] is None)}
        summ[f"≥{thr:.0f}"] = S
    # B6 段內任一天、收盤 ≥30 任一天
    any_ = {}
    segs = C.segments(vd, vv, 30.0, lo)
    js_seg = sorted({j for g in segs for j in range(g["_j"], g["_je"])})
    js_cl = [j for j in range(len(vd)) if vv[j] >= 30.0 and (lo is None or vd[j] >= lo)]
    for nm, js in (("≥30段內任一天", js_seg), ("VIX收盤≥30任一天", js_cl)):
        bs_ = sorted({int(bidx[j]) for j in js if int(bidx[j]) < n})
        cell = {"買進日數（去重）": len(bs_)}
        for hm in HM:
            x = AR[hm][bs_]; pool = AR[hm][base_m & np.isfinite(AR[hm])]
            st = stats(x)
            cell[HN[hm]] = {**st, "超額平均（−全部日）": (st["平均"] - float(pool.mean())) if st["n"] else None}
        any_[nm] = cell
    summ["B6"] = any_
    summ["隨機對照母體"] = {"首日": str(X["dates"][base_m][0]), "末日（資料）": str(X["dates"][-1]),
                        **{f"{HN[hm]}_日數": int((base_m & np.isfinite(AR[hm])).sum()) for hm in HM}}
    return summ, ev_rows


def fmt(v, pct=True):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v * 100:+.1f}%" if pct else f"{v:.0f}"


def main():
    T0 = time.time()
    vd, vv, vinfo = C.load_vix()
    U = C.load_us(); T = C.load_tw()
    rng = np.random.default_rng(SEED)
    res = {"題": "VIX 收盤首次站上門檻（每段第一天）後隔一交易日開盤買，之後報酬如何（描述）", "聲明": DISC + "；⛔ 不計 N、不判合格",
           "定義": "B1～B6 見 researchVIXbuy.py docstring"}
    resU, evU = run_market(U, vd, vv, None, "美股（^SP500TR）", rng)
    resT, evT = run_market(T, vd, vv, C.TW_SEG0, "台股（0050）", rng)
    res["美股"] = resU; res["台股"] = resT
    ev = pd.DataFrame(evU + evT).drop(columns=["_b"], errors="ignore")
    ev.to_csv(os.path.join(OUT, "VIXbuy_events.csv"), index=False, encoding="utf-8", float_format="%.4f")
    # 精簡表
    lines = []
    for mk, R in (("美股 ^SP500TR", resU), ("台股 0050", resT)):
        lines.append(f"## {mk}（隨機對照母體 {R['隨機對照母體']['首日']} 起；{DISC}）")
        lines.append("門檻 | 段數 | " + " | ".join(HN[h] for h in HM) + " | 段內最深中位/最差 | 回本交易日中位/最長 | 1年內最深中位/最差 | 回本交易日中位/最長")
        for thr in THRS:
            S = R[f"≥{thr:.0f}"]
            cells = []
            for h in HM:
                c = S[HN[h]]
                if c["觸發組"]["n"] == 0:
                    cells.append("—"); continue
                cells.append(f"{fmt(c['觸發組']['平均'])} (n{c['觸發組']['n']}, 勝{c['觸發組']['勝率']:.0%}, 超額{fmt(c['超額平均（觸發−全部日）'])}, P{c['觸發組平均在隨機同檔數平均中的百分位'] * 100:.0f})")
            note = "（樣本極少）" if thr >= 50 else ""
            lines.append(f"≥{thr:.0f}{note} | {S['段數']} | " + " | ".join(cells) +
                         f" | {fmt(S['段內最深']['中位'])}/{fmt(S['段內最深']['最差'])} | {fmt(S['段內最深_回本交易日']['中位'], False)}/{fmt(S['段內最深_回本交易日']['最長'], False)}"
                         f" | {fmt(S['1年內最深']['中位'])}/{fmt(S['1年內最深']['最差'])} | {fmt(S['1年內最深_回本交易日']['中位'], False)}/{fmt(S['1年內最深_回本交易日']['最長'], False)}")
        base = R["≥30"]
        lines.append("全部日 | — | " + " | ".join(f"{fmt(base[HN[h]]['全部日']['平均'])} (勝{base[HN[h]]['全部日']['勝率']:.0%})" for h in HM) + " | — | — | — | —")
        for nm, c in R["B6"].items():
            lines.append(f"{nm} | 買進日{c['買進日數（去重）']} | " + " | ".join(
                f"{fmt(c[HN[h]]['平均'])} (n{c[HN[h]]['n']}, 超額{fmt(c[HN[h]]['超額平均（−全部日）'])})" for h in HM) + " | — | — | — | —")
        lines.append("")
    res["精簡表"] = lines
    res["資料"] = {"VIX": vinfo, "美股快照": C.A.data_commit(), "0050": T["info"]}
    res["算於"] = C.now_tpe(); res["秒"] = round(time.time() - T0)
    jdump(res, "VIXbuy.json")
    open(os.path.join(OUT, "VIXbuy_table.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    return res


if __name__ == "__main__":
    main()

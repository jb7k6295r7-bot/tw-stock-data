# -*- coding: utf-8 -*-
"""型態補條件 B 組 seq1 頻率表【對帳】——回測線計算子代理。⛔ 不讀、不算任何 T＋1 以後的價格或報酬；⛔ 不改既有檔。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatB_freq_check
輸出 backtest/resultsPatB/freq/check.json

 C1 原版 K25、K56 對 PREREG型態全量 頻率階段已提交事件檔（resultsPatAll/events_K25_多頭母子線、events_K56_多頭吞噬；同一快照 edc6f8002f）：
    窗 [2017-03-02, 2026-08-24 往前 20 個交易日]，兩邊都有的股票逐筆比 (T, first)；名單差（PatAll ＝ gate3 v1、無 260 根門檻）另報、不算差異。
    另報 PatAll freq.json 的原始／保留數與本支同窗數（母體、剔除規則不同 ⇒ 只描述）。
 C2 抽樣手算：B1、B2 各 20 筆＋原版未確認 K25、K56 各 10 筆（主全窗、早年各半；種子固定），從 D.load_stock 與原始 CSV 重讀，
    純量逐條手算 B̄、長黑、顏色、實體包含、B2 vs B1、r10＜0、第 3 根條件（⛔ 不呼叫 patterns_all）。
 C3 內部一致：事件檔重數 ＝ freq.json（原始、保留）；探索＋確認 原始 ＝ 主全窗 原始；B1（B2）每筆都對得到一筆「第 3 根確認」的原版事件
    （同 sid、同 first），且原版確認筆數 ＝ 確認版筆數（窗邊界差另報）。
"""
from __future__ import annotations
import gzip, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                  # noqa: E402
from backtest import rerun17 as RR              # noqa: E402
from backtest import researchAddOn as RA        # noqa: E402

OUT = "backtest/resultsPatB/freq"
PAT = {"K25": "backtest/resultsPatAll/events_K25_多頭母子線.csv.gz", "K56": "backtest/resultsPatAll/events_K56_多頭吞噬.csv.gz"}
DATA = {"主": RR.H2D, "早年": RA.EOTC}
SEG = {"主": "主全窗", "早年": "早年"}


def ev(wn, sg, cell):
    return pd.read_csv(os.path.join(OUT, f"events_{wn}_{sg}_{cell}.csv.gz"), dtype={"sid": str})


def c1():
    D.DATA = RR.H2D
    cal = D.load_calendar()
    w0 = pd.Timestamp("2017-03-02"); w1 = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    assert str(cal[w1].date()) == "2026-08-24"
    wend = cal[w1 - 20]
    PJ = json.load(open("backtest/resultsPatAll/freq.json", encoding="utf-8"))
    out = {"窗": [str(w0.date()), str(wend.date())]}
    import pickle
    sids_main = set(pickle.load(open(os.path.expanduser("~/rluwork/world_main.pkl"), "rb"))["sids"])
    for cell, p in PAT.items():
        P = pd.read_csv(p, dtype={"sid": str}); P["T"] = pd.to_datetime(P["T"])
        M = ev("主", "主全窗", cell); M["T"] = pd.to_datetime(M["T"]); M = M[(M["T"] >= w0) & (M["T"] <= wend)]
        sP, sM = set(P["sid"]), set(M["sid"])
        # 兩邊都有的股票：mine 的母體 ＝ 本支跑過的全部股票（含零事件者）⇒ 用 PatAll 有事件、且在本支母體內的股票
        common = (sP | sM) & sids_main
        kP = set(zip(P["sid"], P["T"], P["first"])); kM = set(zip(M["sid"], M["T"], M["first"]))
        kPc = {x for x in kP if x[0] in common}; kMc = {x for x in kM if x[0] in common}
        onlyP = sorted(kPc - kMc); onlyM = sorted(kMc - kPc)
        # 只在 PatAll 多的、是否全落在本支 load_bars<260 根被排除的股票
        onlyP_sids = sorted({x[0] for x in onlyP})
        stx = pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str); mk = dict(zip(stx["stock_id"], stx["market"]))
        short = set()
        for s in onlyP_sids:
            st_ = D.load_stock(s, mk.get(s, "twse"), cal)
            if st_ is None or int(st_.df["traded"].sum()) < 260:
                short.add(s)
        onlyP_real = [x for x in onlyP if x[0] not in short]
        out[cell] = {"PatAll窗內原始列數": len(P), "PatAll_freq.json原始_H20": PJ["變體"][cell]["H20"]["事件帳"]["原始"],
                     "PatAll_freq.json保留_H20": PJ["變體"][cell]["H20"]["事件帳"]["保留"],
                     "本支同窗原始列數": int(len(M)), "本支同窗保留_H20": int((M["狀態_H20"] == "保留").sum()),
                     "共同股票的列數_PatAll": len(kPc), "共同股票的列數_本支": len(kMc),
                     "只在PatAll(共同股票)": len(onlyP), "其中屬load_bars不足260根被本支排除的股票": sorted(short),
                     "其中屬load_bars不足260根的列數": len(onlyP) - len(onlyP_real),
                     "只在PatAll(扣260根門檻後)": len(onlyP_real), "只在本支(共同股票)": len(onlyM),
                     "只在本支列(前10)": [(a, str(b.date()), c) for a, b, c in onlyM[:10]],
                     "PatAll有事件但不在本支母體的股票數": len(sP - sids_main), "名單差事件列數": int(P["sid"].isin(sP - sids_main).sum()),
                     "逐筆一致": len(onlyP_real) == 0 and len(onlyM) == 0}
        onlyP = onlyP_real
        if onlyP:
            out[cell]["只在PatAll列(前10)"] = [(a, str(b.date()), c) for a, b, c in onlyP[:10]]
    return out


def load_raw_ohlc(sid, cal):
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for k in ("open", "high", "low", "close"):
        raw[k] = pd.to_numeric(raw[k], errors="coerce")
    raw.loc[(raw[["open", "high", "low", "close"]] <= 0).any(axis=1), ["open", "high", "low", "close"]] = np.nan
    return raw.reindex(cal)


def hand(wn, sid, Tdate, fdate, kind, market):
    """純量手算。kind ∈ B1、B2、K25u、K56u（u ＝ 原版但第 3 根不確認）。回 dict(各條, 全過)。"""
    D.DATA = DATA[wn]; cal = D.load_calendar()
    st = D.load_stock(sid, market, cal); df = st.df
    raw = load_raw_ohlc(sid, cal)
    bars = list(np.flatnonzero(np.isfinite(df["close"].to_numpy(float))))
    pos = {int(p): k for k, p in enumerate(bars)}
    jT = pos[int(cal.searchsorted(pd.Timestamp(Tdate)))]; j1 = pos[int(cal.searchsorted(pd.Timestamp(fdate)))]
    g = lambda col, j: float(df[col].iloc[bars[j]])
    gr = lambda col, j: float(raw[col].iloc[bars[j]])
    O = lambda j: g("open", j); H = lambda j: g("high", j); L = lambda j: g("low", j); C = lambda j: g("close", j)
    body = lambda j: abs(C(j) - O(j)); rng = lambda j: H(j) - L(j)
    top = lambda j: max(O(j), C(j)); bot = lambda j: min(O(j), C(j))
    j2 = j1 + 1; j3 = j1 + 2
    r = {}
    r["T與first相距"] = (jT - j1) == (2 if kind in ("B1", "B2") else 1)
    pre = list(range(j1 - 10, j1))
    fin = all(np.isfinite([g(k, j) for j in pre + [j1, j2] for k in ("open", "high", "low", "close")])) and \
        all(np.isfinite([gr(k, j) for j in pre + [j1, j2] for k in ("open", "high", "low", "close")]))
    r["前10根與兩根OHLC全非缺"] = bool(fin)
    Bm = sum(body(j) for j in pre) / 10.0; Rm = sum(rng(j) for j in pre) / 10.0
    r["B̄>0且R̄>0"] = Bm > 0 and Rm > 0
    r10 = C(j1 - 1) / C(j1 - 11) - 1.0
    r["r10<0(事前降)"] = r10 < 0
    r["第1根黑K"] = C(j1) < O(j1)
    r["第2根白K"] = C(j2) > O(j2)
    if kind in ("B1", "K25u"):
        r["第1根長(B1≥1.5B̄)"] = body(j1) >= 1.5 * Bm
        r["top2≤top1"] = top(j2) <= top(j1); r["bot2≥bot1"] = bot(j2) >= bot(j1); r["B2<B1"] = body(j2) < body(j1)
        third = (j3 < len(bars)) and (C(j3) > O(j3)) and np.isfinite(O(j3)) and np.isfinite(gr("open", j3)) and np.isfinite(gr("high", j3)) \
            and np.isfinite(gr("low", j3)) and np.isfinite(gr("close", j3)) and np.isfinite(H(j3)) and np.isfinite(L(j3)) and (C(j3) > C(j1))
    else:
        r["top2≥top1"] = top(j2) >= top(j1); r["bot2≤bot1"] = bot(j2) <= bot(j1); r["B2>B1"] = body(j2) > body(j1)
        third = (j3 < len(bars)) and (C(j3) > C(j2))
    if kind in ("B1", "B2"):
        r["第3根條件成立"] = bool(third)
    else:
        r["第3根條件不成立(未確認)"] = not bool(third)
    r = {k: bool(v) for k, v in r.items()}
    return {"wn": wn, "sid": sid, "T": Tdate, "first": fdate, "kind": kind, "r10": round(r10, 5), "條件": r, "全過": all(r.values())}


def c2():
    import pickle
    mk = {}
    for wn, part in (("主", "main"), ("早年", "early")):
        D.DATA = DATA[wn]
        stx = pd.read_csv(os.path.join(DATA[wn], "meta", "stocks.csv"), dtype=str)
        mk[wn] = dict(zip(stx["stock_id"], stx["market"]))
    rng = np.random.default_rng(20261017)
    plan = [("B1", "B1", None, 10), ("B2", "B2", None, 10), ("K25", "K25u", False, 5), ("K56", "K56u", False, 5)]
    res = []
    for wn in ("主", "早年"):
        for cell, kind, conf, n in plan:
            E = ev(wn, SEG[wn], cell)
            if conf is not None:
                E = E[E["第3根確認"] == conf]
            pick = E.iloc[rng.choice(len(E), size=min(n, len(E)), replace=False)]
            for _, x in pick.iterrows():
                res.append(hand(wn, x["sid"], x["T"], x["first"], kind, mk[wn].get(x["sid"], "twse")))
    return {"抽樣筆數": len(res), "全過筆數": sum(1 for r in res if r["全過"]), "不過": [r for r in res if not r["全過"]], "明細": res}


def c3():
    J = json.load(open(os.path.join(OUT, "freq.json"), encoding="utf-8"))
    out = {"重數不符": [], "段加總": {}, "確認版對原版": {}}
    for wn, segs in (("主", ("主全窗", "探索", "確認")), ("早年", ("早年",))):
        for sg in segs:
            for cell in ("B1", "B2", "K25", "K56"):
                E = ev(wn, sg, cell); q = J["世界"][wn]["段"][sg][cell]["H20"]
                if not (len(E) == q["原始"] and int((E["狀態_H20"] == "保留").sum()) == q["去重後n(保留)"]):
                    out["重數不符"].append((wn, sg, cell, len(E), q["原始"]))
        if wn == "主":
            for cell in ("B1", "B2", "K25", "K56"):
                a = len(ev("主", "探索", cell)) + len(ev("主", "確認", cell)); b = len(ev("主", "主全窗", cell))
                out["段加總"][cell] = {"探索+確認": a, "主全窗": b, "一致": a == b}
        for cell, base in (("B1", "K25"), ("B2", "K56")):
            sg = SEG[wn]
            Bv = ev(wn, sg, cell); Kv = ev(wn, sg, base)
            kc = Kv[Kv["第3根確認"]]
            kset = set(zip(kc["sid"], kc["first"]))
            miss = [(s, t, f) for s, t, f in zip(Bv["sid"], Bv["T"], Bv["first"]) if (s, f) not in kset]
            bset = set(zip(Bv["sid"], Bv["first"]))
            miss2 = [(s, t, f) for s, t, f in zip(kc["sid"], kc["T"], kc["first"]) if (s, f) not in bset]
            out["確認版對原版"][f"{wn}/{cell}"] = {"確認版原始": len(Bv), "原版第3根確認": len(kc),
                                             "確認版找不到原版(窗頭邊界)": len(miss), "原版確認找不到確認版(窗尾邊界)": len(miss2),
                                             "例": {"找不到原版": miss[:5], "找不到確認版": miss2[:5]}}
    out["全過"] = not out["重數不符"] and all(v["一致"] for v in out["段加總"].values())
    return out


def main():
    R = {"C1_對PatAll": c1(), "C2_抽樣手算": c2(), "C3_內部一致": c3()}
    R["總結"] = {"C1_K25逐筆一致": R["C1_對PatAll"]["K25"]["逐筆一致"], "C1_K56逐筆一致": R["C1_對PatAll"]["K56"]["逐筆一致"],
               "C2_手算": f"{R['C2_抽樣手算']['全過筆數']}／{R['C2_抽樣手算']['抽樣筆數']}", "C3_全過": R["C3_內部一致"]["全過"]}
    json.dump(R, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    show = {k: v for k, v in R.items() if k != "C2_抽樣手算"}
    show["C2"] = {k: v for k, v in R["C2_抽樣手算"].items() if k != "明細"}
    print(json.dumps(show, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

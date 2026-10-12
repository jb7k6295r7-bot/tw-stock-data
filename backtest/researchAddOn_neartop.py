# -*- coding: utf-8 -*-
"""加碼點是否近頂（描述、不計 N、不判定）。重用 researchAddOn 的世界檔、引擎檔、觸發清單、market()（壞根）。"""
import os, sys, json, pickle
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO
from backtest import universe_gate as UG

OUT = "backtest/resultsAddOn/near_top"
os.makedirs(OUT, exist_ok=True)
log = lambda m: print(m, flush=True)
UG.set_gate_v2(True)
TR = pd.read_csv("backtest/resultsAddOn/triggers.csv.gz", dtype={"sid": str})
ENG = pickle.load(open(os.path.join(AO.WORK, "engine_200.pkl"), "rb"))
WS = {wn: pickle.load(open(os.path.join(AO.WORK, f"world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
POST = 60

# 每條路徑的持股（含 ep）
PATH = {}
for key, E in ENG.items():
    PATH[key] = [(sid, int(tb), float(ep), ts) for sid, tb, amt, ep, ts, pxs in AO.holdings(E["au"])]

X = None
rows = []
for wn in ("主", "早年"):
    W = WS[wn]; n = len(W["cal"])
    uh = {}
    for (w_, sn, r), Hs in PATH.items():
        if w_ != wn:
            continue
        for sid, tb, ep, ts in Hs:
            uh[(sn, sid, tb)] = (ep, ts)
    hold_sids = sorted({k[1] for k in uh})
    M, HB, X, info = AO.market(wn, W, X, log, hold_sids)
    del M
    tw = TR[TR["世界"] == wn].set_index(["策略", "sid", "tb", "格"])
    x0, y0 = W["segp"]["主窗" if wn == "主" else "早年"]
    for (sn, sid, tb), (ep, ts) in uh.items():
        cl = np.asarray(W["closes"][sid], float); bar, bad = HB[sid]
        ok = bar[:len(cl)] & np.isfinite(cl) & (cl > 0)
        r0 = tw.loc[(sn, sid, tb, "A1")]
        xbar = int(r0["xbar"]); sf = bool(r0["停止交易強制"])
        kb = AO.first_true(bad, tb + 1, xbar)
        end = (kb - 1) if kb is not None else xbar
        idx = np.arange(tb, end + 1); idx = idx[ok[idx]]
        if not len(idx):
            continue
        Hmax = float(cl[idx].max())
        # 第 10～14 根（h ＝ pos − tb ＋ 1）
        p1014 = [tb + h - 1 for h in range(10, 15) if tb + h - 1 <= end and ok[tb + h - 1]]
        r1014 = float(np.mean(cl[p1014] / Hmax)) if p1014 else np.nan
        # 出場後 60 根
        post_new = np.nan; post_note = ""
        if ts is None or (isinstance(ts, float) and np.isnan(ts)):
            post_note = "資料尾仍持有"
        elif kb is not None:
            post_note = "持有期內有壞根（已截斷）"
        elif xbar + POST > n - 1:
            post_note = "出場後不滿60根"
        else:
            kb2 = AO.first_true(bad, xbar + 1, xbar + POST)
            hi = (kb2 - 1) if kb2 is not None else xbar + POST
            pi = np.arange(xbar + 1, hi + 1); pi = pi[ok[pi]] if len(pi) else pi
            if not len(pi):
                post_note = "出場後60根內無有效K棒"
            else:
                post_new = float(cl[pi].max() > Hmax)
                if kb2 is not None:
                    post_note = "出場後窗遇壞根截斷"
        base = {"世界": wn, "策略": sn, "sid": sid, "tb": tb, "窗內": bool(x0 <= tb <= y0), "ep": ep, "持有期最高收盤": Hmax,
                "持有期截斷於壞根": kb is not None, "停止交易強制": sf, "xbar": xbar, "第10至14根價÷最高": r1014,
                "出場後60根更高": post_new, "出場後註": post_note}
        for c in AO.CELLS:
            rr = tw.loc[(sn, sid, tb, c)]
            d = dict(base, 格=c, 結果=rr["結果"])
            if rr["結果"] == "加碼":
                t, ta, epa = int(rr["t"]), int(rr["ta"]), float(rr["ep_a"])
                pre = cl[tb:t + 1][ok[tb:t + 1]].max()
                post = cl[ta:end + 1][ok[ta:end + 1]]
                d.update({"h": int(rr["h"]), "t": t, "ta": ta, "加碼價": epa, "加碼價÷最高": epa / Hmax,
                          "加碼後創新高": bool(len(post) and post.max() > pre),
                          "已漲掉幾成": ((epa - ep) / (Hmax - ep)) if Hmax > ep else np.nan, "最高不高於買進": bool(Hmax <= ep)})
            rows.append(d)
DF = pd.DataFrame(rows)
DF.to_csv(os.path.join(OUT, "near_top_holdings.csv.gz"), index=False, float_format="%.10g")
log(f"[逐筆] {len(DF)} 列")


def qq(v):
    v = np.asarray(pd.Series(v).dropna(), float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "q25": float(np.quantile(v, .25)), "q75": float(np.quantile(v, .75))}


def stats(g):
    tr = g[g["結果"] == "加碼"]; nt = g[g["結果"] != "加碼"]
    s = {"持股筆": int(len(g)), "加碼筆": int(len(tr))}
    s["1 加碼價÷持有期最高"] = qq(tr["加碼價÷最高"])
    s["1 ≥0.9 比例"] = float((tr["加碼價÷最高"] >= 0.9).mean()) if len(tr) else np.nan
    s["1 ≥1（加碼價≥持有期最高收盤）比例"] = float((tr["加碼價÷最高"] >= 1.0).mean()) if len(tr) else np.nan
    s["1 加碼後創新高比例"] = float(tr["加碼後創新高"].astype(bool).mean()) if len(tr) else np.nan
    s["2 已漲掉幾成"] = qq(tr["已漲掉幾成"])
    s["2 最高≤買進價筆數"] = int(tr["最高不高於買進"].astype(bool).sum()) if len(tr) else 0
    s["3 沒觸發 第10至14根價÷最高"] = qq(nt["第10至14根價÷最高"])
    s["3 沒觸發 ≥0.9 比例"] = float((nt["第10至14根價÷最高"].dropna() >= 0.9).mean()) if nt["第10至14根價÷最高"].notna().any() else np.nan
    s["3 觸發 第10至14根價÷最高"] = qq(tr["第10至14根價÷最高"])
    s["3 全部 第10至14根價÷最高"] = qq(g["第10至14根價÷最高"])
    for nm, gg in (("觸發", tr), ("沒觸發", nt)):
        v = gg["出場後60根更高"].dropna()
        s[f"4 {nm} 出場後60根更高比例"] = float(v.mean()) if len(v) else np.nan
        s[f"4 {nm} 可算筆"] = int(len(v))
    return s


def flat(s, pre=""):
    o = {}
    for k, v in s.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                o[f"{k}·{k2}"] = v2
        else:
            o[k] = v
    return o


RES = {}; TAB = []
for wn in ("主", "早年"):
    D = DF[(DF["世界"] == wn) & DF["窗內"]]
    for sn in AO.STRATS:
        for c in AO.CELLS:
            G = D[(D["策略"] == sn) & (D["格"] == c)].set_index(["sid", "tb"])
            per = []
            for r in AO.seeds_of(sn):
                keys = [(sid, tb) for sid, tb, ep, ts in PATH[(wn, sn, r)]]
                keys = [k for k in keys if k in G.index]
                per.append(flat(stats(G.loc[keys].reset_index())))
            r0 = per[0]
            RES[f"{wn}·{sn}·{c}·r0"] = r0
            TAB.append(dict(世界=wn, 策略=sn, 格=c, 口徑="r0", **r0))
            if sn == "營飆":
                P = pd.DataFrame(per)
                med = {k: (float(P[k].median()) if pd.api.types.is_numeric_dtype(P[k]) else None) for k in P.columns}
                RES[f"{wn}·{sn}·{c}·200顆中位"] = med
                TAB.append(dict(世界=wn, 策略=sn, 格=c, 口徑="200顆中位", **med))
            # 唯一持股（不分顆）
            u = flat(stats(G.reset_index()))
            RES[f"{wn}·{sn}·{c}·唯一持股"] = u
TB = pd.DataFrame(TAB)
TB.to_csv(os.path.join(OUT, "near_top.csv"), index=False, float_format="%.4f", encoding="utf-8-sig")
meta = {"說明": "描述性統計、不計 N、不判定；重用 researchAddOn 世界檔、engine_200.pkl、triggers.csv.gz、market()（壞根）",
        "定義": {"持有期": "買進根 tb ～ 原規則出場根 xbar（引擎同一份還原收盤；持有期內遇壞根 ⇒ 截在壞根前一根）",
                 "加碼價": "ta 開盤（triggers ep_a）", "加碼後創新高": "ta～持有期末 最高收盤 ＞ tb～決策日 t 最高收盤",
                 "已漲掉幾成": "(加碼價−買進價)÷(持有期最高收盤−買進價)；最高≤買進價另計",
                 "第10至14根": "h＝10～14（買進根算第 1 根）各根收盤÷持有期最高的平均（每筆一個值）",
                 "出場後60根更高": "xbar＋1～xbar＋60 有效收盤最高 ＞ 持有期最高；資料尾仍持有、持有期截斷、不滿 60 根者不計（遇壞根截斷）",
                 "窗": "依買進根 tb 落在 主窗／早年 段", "營飆": "r0 ＝ 第 0 顆；200顆中位 ＝ 每顆路徑各算一次再取中位（各欄獨立取中位）"},
        "結果": RES}
json.dump(meta, open(os.path.join(OUT, "near_top.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
cols = ["世界", "策略", "格", "口徑", "加碼筆", "1 加碼價÷持有期最高·中位", "1 加碼價÷持有期最高·q25", "1 加碼價÷持有期最高·q75", "1 ≥0.9 比例",
        "1 ≥1（加碼價≥持有期最高收盤）比例", "1 加碼後創新高比例", "2 已漲掉幾成·中位", "2 已漲掉幾成·q25", "2 已漲掉幾成·q75", "2 最高≤買進價筆數",
        "3 沒觸發 第10至14根價÷最高·中位", "3 沒觸發 ≥0.9 比例", "3 觸發 第10至14根價÷最高·中位", "3 全部 第10至14根價÷最高·中位",
        "4 觸發 出場後60根更高比例", "4 觸發 可算筆", "4 沒觸發 出場後60根更高比例", "4 沒觸發 可算筆"]
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(TB[cols].T.to_string())
print("截斷：", DF.drop_duplicates(["世界", "策略", "sid", "tb"]).groupby(["世界", "策略"])[["持有期截斷於壞根"]].sum().to_dict())
print(DF.drop_duplicates(["世界", "策略", "sid", "tb"]).groupby(["世界", "策略"])["出場後註"].value_counts())

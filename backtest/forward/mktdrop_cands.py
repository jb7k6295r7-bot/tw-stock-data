# -*- coding: utf-8 -*-
"""PREREG大盤大跌後買什麼 seq1 前瞻第 0 筆（2026-10-15）候選名單——照 researchMktDrop_v1.basket() / researchMktDrop.stock_job 的 R1 母體定義，
改用公開庫 origin/main 最新資料（~/h2data/<sha>/data，run_daily_list.sh 的 archive）。只計算、只寫 backtest/forward/mktdrop/candidates_20261015.csv 與 scratchpad md。"""
import os, sys, json, math, time
from multiprocessing import Pool
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import patterns as P
from backtest import universe_gate as UG
from backtest import researchIndRev_prereg as PRE
from backtest import researchBARR as BARR
from backtest import researchExit5 as EX5
from backtest import holdings as HD

SHA = sys.argv[1]; T_DATE = pd.Timestamp(sys.argv[2]); OUTCSV = sys.argv[3]; OUTMD = sys.argv[4]
DATA = os.path.expanduser(f"~/h2data/{SHA}/data")
IND_EXCL = {"其他", "存託憑證", "ETF"}
UG.set_gate_v2(True)
D.DATA = DATA
cal = D.load_calendar(); n0 = len(cal)
assert cal[-1] == T_DATE, f"日曆尾 {cal[-1]} ≠ {T_DATE}"
TP = n0 - 1


def job(a):
    sid, mk = a
    D.DATA = DATA
    B = R.load_bars(sid, mk, cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if idx[-1] != TP:
        return sid, {"traded": False}
    c = np.asarray(B["c"], float); dn = np.asarray(B["dn"], bool); up = np.asarray(B["up"], bool)
    gate_b = np.asarray(P.Frame(df, set()).gate, bool)[idx]
    bad = np.asarray(np.asarray(B["next_bad"])[:nb] == np.arange(nb), bool)
    # seq335 壞根另源：researchBARR.bad_part ∪ adj 減資／面額（addon_daily._badjob 同式）
    bp_ = BARR.bad_part(sid, DATA, cal).copy()
    D.DATA = DATA
    adj = D.load_adj(sid)
    if adj is not None and len(adj) and "event" in adj:
        for d, e in zip(adj["date"], adj["event"].astype(str)):
            if e in ("reduce", "parvalue"):
                k = int(cal.searchsorted(d))
                if k < n0:
                    bp_[k] = True
    bad |= bp_[idx]
    K = nb - 1
    pv = bool(np.asarray(UG.pit_valid(sid, cal, DATA), bool)[TP])
    nobad = (K >= 20) and not bad[K - 20:K + 1].any()
    mem = bool(gate_b[K] and pv and nobad)
    ret1 = float(c[K] / c[K - 1] - 1.0)
    raw = pd.read_csv(os.path.join(DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date").set_index("date")["close"]
    rc = float(pd.to_numeric(raw.get(str(T_DATE.date())), errors="coerce"))
    return sid, {"traded": True, "mem": mem, "gate": bool(gate_b[K]), "pv": pv, "nobad": nobad, "ret": ret1, "dn": bool(dn[K]), "up": bool(up[K]), "rc": rc}


def main():
    T0 = time.time()
    stocks = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    nm_of = stocks.drop_duplicates("stock_id", keep="last").set_index("stock_id")["name"].to_dict()
    U = UG.gate3(stocks); U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
    jobs = list(zip(U["stock_id"], U["market"]))
    with Pool(4) as pool:
        res = dict(pool.map(job, jobs, chunksize=16))
    print(f"[載入] gate3(GATE_V2)∩四碼 {len(U)} 檔｜{time.time() - T0:.0f}s", flush=True)
    st = {"gate3∩四碼": len(U), "load_bars 可用（≥260 根）": sum(v is not None for v in res.values()),
          "當天有成交": sum(bool(v and v.get("traded")) for v in res.values())}
    mem = sorted(s for s, v in res.items() if v and v.get("traded") and v["mem"] and np.isfinite(v["ret"]))
    st["R1 母體（閘∧pit_valid∧前20根無壞根）"] = len(mem)
    st["剔除：成交閘不過"] = sum(1 for v in res.values() if v and v.get("traded") and not v["gate"])
    st["剔除：pit_valid 否"] = sum(1 for v in res.values() if v and v.get("traded") and v["gate"] and not v["pv"])
    st["剔除：前20根有壞根"] = sum(1 for v in res.values() if v and v.get("traded") and v["gate"] and v["pv"] and not v["nobad"])
    rets = np.array([res[s]["ret"] for s in mem])
    # C：最低 ceil(10%)，stable（列序＝代號排序，同 v1 assemble sorted(PK)）
    ns = int(np.ceil(0.10 * len(mem)))
    o = np.argsort(rets, kind="stable")
    Csel = [mem[i] for i in o[:ns]]
    # 產業（PIT pit 版＋營收彙總表後備）
    rev_, rly_, cat, mk, nf, nr = PRE.load_rev(DATA)
    PIT = PRE.PIT(DATA, cat)
    ind = {}; isrc = {}
    for s in mem:
        v, src = PIT._at(s, T_DATE, "pit")
        ind[s] = v; isrc[s] = src
    dfi = pd.DataFrame({"s": mem, "v": rets, "i": [ind[s] for s in mem]})
    order = {}
    for s in mem:            # 產業號 ＝ 依代號序第一次出現（同 assemble 的 setdefault）
        v = ind[s]
        if v is not None and v not in IND_EXCL:
            order.setdefault(v, len(order))
    dfo = dfi[dfi["i"].map(lambda x: x is not None and x not in IND_EXCL)].copy()
    dfo["ii"] = dfo["i"].map(order)
    g = dfo.groupby("ii")["v"].agg(["mean", "count"]); g = g[g["count"] >= 5].reset_index().sort_values(["mean", "ii"], kind="stable")
    inv = {v: k for k, v in order.items()}
    worst = [int(x) for x in g["ii"].iloc[:2]]
    Esel = dfo[dfo["ii"].isin(worst)].sort_values(["ii", "v"])["s"].tolist()
    gtab = g.assign(產業=g["ii"].map(inv)).head(6)
    # 營收：可得日 ≤ t 的最後一期（≤2025-12 次月 10 日後、≥2026-01 次月 15 日後第一個交易日）
    rev, rly, rinfo = EX5.load_revenue(DATA)
    AV = EX5.avail_pos(list(rev.index), cal)

    def lastrev(s):
        if s not in rev.columns:
            return None, np.nan
        rv = rev[s].to_numpy(float); rl = rly[s].to_numpy(float); per = list(rev.index)
        best = None
        for k, p in enumerate(per):
            if not np.isfinite(rv[k]) or AV[p] >= n0 or AV[p] > TP:
                continue
            if best is None or AV[p] >= AV[per[best]]:
                best = k
        if best is None:
            return None, np.nan
        yoy = rv[best] / rl[best] - 1.0 if (np.isfinite(rl[best]) and rl[best] > 0) else np.nan
        return per[best], yoy
    REV = {s: lastrev(s) for s in set(Csel) | set(Esel)}
    Cp = [s for s in Csel if np.isfinite(REV[s][1]) and REV[s][1] > 0]
    # ETF
    etf = {}
    for s in ("0050", "00631L"):
        stx = D.load_stock(s, "twse", cal); c = stx.df["close"].to_numpy(float)
        etf[s] = float(c[TP] / c[TP - 1] - 1.0) if np.isfinite(c[TP]) and np.isfinite(c[TP - 1]) else np.nan
    # 持股（營量／營飆）
    hold = []
    for c_, bd_, bp_, nt_, src in HD.read_csv():
        if src in ("營量", "營飆", "營飆營量"):
            per, yoy = lastrev(c_)
            r_ = res.get(c_)
            hold.append({"代號": c_, "名稱": nm_of.get(c_, ""), "來源": src, "買進日": bd_, "營收期別": per, "年增": yoy,
                         "當日報酬": (r_["ret"] if r_ and r_.get("traded") else np.nan), "是否跌停": (r_["dn"] if r_ and r_.get("traded") else None),
                         "在R1": c_ in set(mem)})
    # 輸出 CSV
    rows = []
    fmt = lambda x: "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else x
    rows.append({"候選": "A", "代號": "0050", "名稱": nm_of.get("0050", "元大台灣50"), "當日報酬": etf["0050"], "營收期別": "", "年增": "", "是否跌停": "", "產業": "", "備註": "照登錄：10/16 開盤買"})
    rows.append({"候選": "B", "代號": "00631L", "名稱": nm_of.get("00631L", ""), "當日報酬": etf["00631L"], "營收期別": "", "年增": "", "是否跌停": "", "產業": "", "備註": "照登錄：10/16 開盤買（正2 含槓桿效果）"})
    for cd, sel in (("C", Csel), ("C+", Cp)):
        for s in sel:
            per, y = REV[s]
            rows.append({"候選": cd, "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": res[s]["ret"], "營收期別": fmt(per), "年增": fmt(y),
                         "是否跌停": "是" if res[s]["dn"] else "否", "產業": fmt(ind[s]), "備註": ""})
    for s in Esel:
        per, y = REV[s]
        rows.append({"候選": "E", "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": res[s]["ret"], "營收期別": fmt(per), "年增": fmt(y),
                     "是否跌停": "是" if res[s]["dn"] else "否", "產業": ind[s], "備註": ""})
    rows.append({"候選": "F", "代號": "", "名稱": "", "當日報酬": "", "營收期別": "", "年增": "", "是否跌停": "", "產業": "",
                 "備註": "0 檔：營量 v1 正式訊號 10/15 已達成＝無（每日名單 daily_2026-10-15 第二節，main 4b26f6ad1e）⇒ 照登錄該事件 F 不進場"})
    for h in hold:
        rows.append({"候選": "持股（描述對照）", "代號": h["代號"], "名稱": h["名稱"], "當日報酬": fmt(h["當日報酬"]), "營收期別": fmt(h["營收期別"]), "年增": fmt(h["年增"]),
                     "是否跌停": ("" if h["是否跌停"] is None else ("是" if h["是否跌停"] else "否")), "產業": "",
                     "備註": f"來源 {h['來源']}；年增>0={'是' if np.isfinite(h['年增']) and h['年增'] > 0 else '否'}"})
    out = pd.DataFrame(rows)
    out.to_csv(OUTCSV, index=False, encoding="utf-8-sig", float_format="%.6f")
    J = {"sha": SHA, "資料日": str(T_DATE.date()), "統計": st, "C 檔數": len(Csel), "C 跌停數": int(sum(res[s]["dn"] for s in Csel)),
         "C+ 檔數": len(Cp), "C 年增缺": int(sum(not np.isfinite(REV[s][1]) for s in Csel)), "C 最淺跌幅": float(rets[o[ns - 1]]),
         "E 產業": [inv[w] for w in worst], "E 檔數": len(Esel), "E 各產業": {inv[w]: int((dfo["ii"] == w).sum()) for w in worst},
         "產業最差六": gtab[["產業", "mean", "count"]].to_dict("records"),
         "ETF": etf, "營收資訊": rinfo, "產業來源計數（母體）": pd.Series(isrc).value_counts().to_dict(),
         "營收期別分佈（C）": pd.Series([REV[s][0] for s in Csel]).value_counts().to_dict(),
         "持股": hold, "耗時秒": round(time.time() - T0)}
    print(json.dumps(J, ensure_ascii=False, indent=1, default=str))
    # md
    L = [f"# 大盤大跌 seq1 前瞻第 0 筆 2026-10-15 候選名單（描述、不入判）", "",
         f"- 資料：tw-stock-data origin/main {SHA[:10]}（資料日 {T_DATE.date()}）；母體 R1 ＝ gate3（GATE_V2 開）∩ 四碼普通股 ∧ Frame.gate（20 日都有成交 ∧ 前 20 日均量 ≥ 500 張）∧ pit_valid ∧ 前 20 根無壞根（seq335）＝ {len(mem)} 檔",
         f"- 加權 −3.41%（門檻 −2.92%）；收復目標 加權收盤 ≥ 48,625.83 ⇒ 隔天開盤賣；⛔ 不設天數",
         f"- 買進價：10/16 開盤（尚未發生；買到後再補 positions.csv；開盤漲停鎖死／沒成交 ⇒ 剔除）",
         f"- 營收：可得日 ≤ 10/15 的最後一期（2026 期次月 15 日之後才可得 ⇒ 9 月營收 10/16 起才算）；年增 ＝ 當月 ÷ 去年當月 − 1", "",
         f"## A 0050（當天 {etf['0050']:+.2%}）｜B 00631L（當天 {etf['00631L']:+.2%}）", "",
         f"## C 當天跌最多一成：{len(Csel)} 檔（其中收盤跌停 {J['C 跌停數']} 檔；最淺 {J['C 最淺跌幅']:+.2%}）", "",
         f"## C+ 其中最近一期營收年增 > 0：{len(Cp)} 檔", "", "| 代號 名稱 | 當天 | 跌停 | 營收期別 | 年增 |", "|---|---|---|---|---|"]
    for s in sorted(Cp, key=lambda x: res[x]["ret"]):
        L.append(f"| {s} {nm_of.get(s, '')} | {res[s]['ret']:+.2%} | {'是' if res[s]['dn'] else ''} | {REV[s][0]} | {REV[s][1]:+.1%} |")
    L += ["", f"## E 跌最多兩產業（成員 ≥5 檔的產業裡等權最差）：{'、'.join(inv[w] for w in worst)}，共 {len(Esel)} 檔", ""]
    for w in worst:
        mm = dfo[dfo["ii"] == w].sort_values("v")
        L.append(f"- {inv[w]}（{len(mm)} 檔、等權 {mm['v'].mean():+.2%}）：" + "、".join(f"{s} {nm_of.get(s, '')} {v:+.1%}" for s, v in zip(mm["s"], mm["v"])))
    L += ["", "## F 營量 v1 已達成：0 檔 ⇒ 該事件 F 不進場", "",
          "## 持股（營量／營飆）最近一期營收年增 > 0（描述對照）", ""]
    for h in hold:
        y = h["年增"]
        L.append(f"- {h['代號']} {h['名稱']}｜{h['來源']}｜{h['營收期別']} 年增 {y:+.1%}" if np.isfinite(y) else f"- {h['代號']} {h['名稱']}｜{h['來源']}｜年增缺")
    L += ["", "⛔ 不是買賣建議；第 0 筆只描述、不入判。"]
    open(OUTMD, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

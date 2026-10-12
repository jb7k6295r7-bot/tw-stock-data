# -*- coding: utf-8 -*-
"""漲多加碼：加碼那一份改用「真頂訊號」賣出，或到時間跟原持股一起賣（使用者 2026-10-12 逐字：「加碼那份改用真頂訊號賣出，或到時間一起賣出就這兩種!」）
——回測線計算子代理。⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議。
⚠ 本件是看過 researchAddOn 加碼結果（兩策略加碼版都沒變好）之後才加的出場 ⇒ 事後重切、只當參考（⛔ 不計 N、⛔ 不進採用）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_truetop
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_truetop_check

═══ 讀法（寫死 2026-10-12 20:15（台北），在算任何本件數字之前；看過的：researchAddOn 全文與其結果（判定、退化）、researchYL_truetopT 全文、處置表起訖）═══
 V0 原持股、加碼條件、加碼價、加碼金額、資金讀法 A／B／C、成本、壞根、段 ＝ researchAddOn 一字不動（直接 import 它的 holdings／market／main_exit／account／metrics／better／ratio，
    讀它留下的世界檔 ~/addonwork/world_主.pkl、引擎檔 engine_200.pkl、觸發清單 resultsAddOn/triggers.csv.gz）；只改「加碼那一份」的出場
 V1 臂 S ＝ researchAddOn 主臂（跟原持股同日同價賣）：本檔重算，閘 ＝ 與 resultsAddOn/seeds.csv.gz 主臂 A／B／C 年化、回落逐列差 ≤ 1e−12
 V2 臂 T：真頂訊號 ＝ researchYL_truetopT 的 T1（U2 起漲點 ＋ U3 W2a ∪ W2b），直接呼叫 TTT.surge_world 與 TTT.signals_row（⛔ 不另寫訊號邏輯、⛔ 不用 T2 分數、⛔ 不用 S8）
      起漲點照 U2 以原持股進場日 e ＝ tb 錨定（signals_row(S, SW, gi, m*, tb, hi)）；價格 ＝ 引擎還原收盤（世界 closes[:n0]）
      訊號只看 ta ≤ d ＜ hi，hi ＝ min(xbar, n0)（xbar ＝ researchAddOn 原持股出場根：正式第 60／120 根、停止交易 ＝ L、資料尾 ＝ 墊根）
      第一個訊號日 d ⇒ d 之後第一個「有效開盤」u（researchAddOn 同一份 K 棒 bar ∧ 開盤有值 ＞ 0，u ≤ n0−1）賣加碼那一份（價 ＝ 開盤還原價、記帳日 ＝ u）
      與主臂出場比時序取早：主臂刻度 ＝ 2 × 價所在根 ＋ 1（收盤；含壞根前一根收盤強制、停止交易 L 收盤），資料尾仍持有 ＝ ∞；開盤刻度 ＝ 2u（同根開盤早於收盤）
      2u ＜ 主臂刻度 ⇒ 提早賣；否則 ＝ 主臂（到時間一起賣／壞根強制）；成本照 researchAddOn（入帳 ＝ A × (賣價 ÷ 加碼價 − COST)）
      不在飆股母體（無處置／NEAR 資料，如 6854）⇒ 沒有訊號 ⇒ ＝ 主臂（照報筆數）
      閘：truetopT 的有效開盤（FX0.stock_arrays nxt）與本件有效開盤在所有提早賣的筆上一致（照報不同筆數）
 V3 判定（同裁定 seq342 口徑，⚠ 只當參考）：挑中格寫死 ＝ 營量 A2、營飆 A1（researchAddOn 挑中）；另報另一格（營飆 A2 探索段退化 ＜ 20 筆，照標）
      「T 變好」＝ 臂 T 年化 ＞ 原策略年化 且 臂 T 年化÷|回落| ≥ 原策略；探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24 兩段都要；讀法 A、B 各判（C 描述）
      營飆 ＝ 200 顆中位（年化中位、回落中位、比值 ＝ 年化中位 ÷ |回落中位|）；另報逐顆比例；另報 T vs S 同式
 V4 早年 2005-02～2014-12：處置表（飆股資料 MAIN meta/disposal.csv）起始日 ＜ 2005-02 才算；否則整段標「不可算（無處置資料）」、⛔ 不硬算
 V5 必報（主世界，營飆 ＝ 200 顆合併、另報唯一持股口徑；依加碼日 ta 分段 (x, y]）：提早賣比例（W2a／W2b 拆）、訊號距加碼日（d − ta，日曆交易日位置差）分佈、
      提早賣那幾筆 T 淨報酬 − S 淨報酬（中位、平均、T 較好比例；S 資料尾仍持有者不計）、加碼部位淨報酬分佈 S 與 T（中位、p10、p90、平均；只算 S 已出場的筆）
 輸出 backtest/resultsAddOn/truetop/：truetop.json、truetop_main.csv、trades_T.csv.gz（逐路徑逐筆）、run.log
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa: E402
from backtest import researchYL_truetopT as TTT               # noqa: E402
from backtest import researchYL_flowexit as FX0               # noqa: E402
from backtest import rerun17 as RR                            # noqa: E402
from backtest import universe_gate as UG                      # noqa: E402

TIME = "2026-10-12 20:15（台北）"
OUT = "backtest/resultsAddOn/truetop"
WN = "主"
PICK = {"營量": "A2", "營飆": "A1"}
SEGJ = ("探索", "確認", "主窗")
READS = ("A", "B", "C")
EARLY0 = "2005-02-01"
NOTE = ["⚠ 本件是看過加碼結果之後才加的出場（事後重切），只當參考、不計 N、不進採用",
        "加碼用的是另外的錢；⛔ 不代表該把原策略的錢集中到漲最多的那檔", "加碼版用的錢比原策略多"]


def q3(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p10": float(np.quantile(v, .1)), "p90": float(np.quantile(v, .9)), "平均": float(v.mean())}


def load_all(log):
    WS = {WN: pickle.load(open(os.path.join(AO.WORK, f"world_{WN}.pkl"), "rb"))}
    ENG = pickle.load(open(os.path.join(AO.WORK, f"engine_{AO.NSEED}.pkl"), "rb"))
    ENG = {k: v for k, v in ENG.items() if k[0] == WN}
    TR = pd.read_csv("backtest/resultsAddOn/triggers.csv.gz", dtype={"sid": str})
    TR = TR[TR["世界"] == WN].copy()
    log(f"[讀] 世界 {WN}｜引擎 {len(ENG)} 條｜觸發清單 {len(TR)} 列")
    return WS, ENG, TR


def build(log):
    T0 = time.time()
    WS, ENG, TR = load_all(log)
    W = WS[WN]; cal = W["cal"]; n0 = len(cal)
    RAW = {k: AO.holdings(E["au"]) for k, E in ENG.items()}
    uh = {}
    for (w_, sn, r), Hs in RAW.items():
        for sid, tb, amt, ep, ts, pxs in Hs:
            uh[(w_, sn, sid, tb)] = (ep, ts, pxs)
    TRi = TR.set_index(["策略", "sid", "tb", "格"])
    trig_hk = sorted({(WN, s, i, int(b)) for s, i, b in TR.loc[TR["結果"] == "加碼", ["策略", "sid", "tb"]].itertuples(index=False)})
    sids = sorted({hk[2] for hk in trig_hk})
    # truetopT 的股票陣列（照 truetopT：gate 不開時建）
    ctx = {"mk": W["uni"], "cal": cal, "closes": W["closes"], "opens": W["opens"]}
    SA = {s: FX0.stock_arrays(ctx, s, n0) for s in sids}
    # researchAddOn 的 K 棒、壞根（gate v2 開，同 researchAddOn）
    UG.set_gate_v2(True)
    M, HB, X, info = AO.market(WN, W, None, log, sorted({hk[2] for hk in uh}))
    del M
    HI = {}
    for hk, (ep, ts, pxs) in uh.items():
        sn, sid, tb = hk[1], hk[2], hk[3]
        r0 = TRi.loc[(sn, sid, tb, "A1")]
        HI[hk] = {"sid": sid, "tb": tb, "ep": ep, "ts": ts, "pxs": pxs, "xbar": int(r0["xbar"]), "sf": bool(r0["停止交易強制"]),
                  "cl": W["closes"][sid], "op": W["opens"][sid], "bar": HB[sid][0], "bad": HB[sid][1]}
    AO._G["HI"] = HI; AO._G["NCAL"] = {WN: n0}
    # 處置／NEAR（truetopT）
    SWD, gi, mstar, sinfo = TTT.surge_world(sids, cal, log)
    RR.use_snapshot()
    gates = {"世界收盤 vs truetopT 股票陣列 c 最大相對差": 0.0}
    for s in sids:
        c1 = np.asarray(W["closes"][s], float)[:n0]; c2 = SA[s]["c"]; ok = np.isfinite(c1) & np.isfinite(c2)
        if ok.any():
            gates["世界收盤 vs truetopT 股票陣列 c 最大相對差"] = max(gates["世界收盤 vs truetopT 股票陣列 c 最大相對差"], float(np.max(np.abs(c1[ok] / c2[ok] - 1))))
    # 每筆唯一持股 × 格 的 T 出場
    TX = {}; nxo_diff = 0; nos = 0
    for hk in trig_hk:
        sn, sid, tb = hk[1], hk[2], hk[3]; I = HI[hk]
        hi = min(I["xbar"], n0)
        SW = SWD.get(sid)
        nos += int(SW is None)
        tt, w2a, w2b, nh, t2 = TTT.signals_row(SA[sid], SW, gi, mstar, tb, hi)
        t1 = w2a | w2b
        for c in AO.CELLS:
            rr = TRi.loc[(sn, sid, tb, c)]
            if rr["結果"] != "加碼":
                continue
            ta, ep_a = int(rr["ta"]), float(rr["ep_a"])
            mx = AO.main_exit(hk, ta)                       # 主臂（臂 S）
            sd, px, pb, kind = mx
            mtick = np.inf if sd is None else 2 * pb + 1
            k = np.flatnonzero(t1[max(ta - tb, 0):]) if hi > ta else np.zeros(0, int)
            sig = (ta + int(k[0])) if len(k) else None
            src = None if sig is None else ("W2a" if w2a[sig - tb] else "W2b")
            u = None
            if sig is not None:
                bar, op = I["bar"], I["op"]
                for x in range(sig + 1, n0):
                    if bar[x] and np.isfinite(op[x]) and op[x] > 0:
                        u = x; break
                ut = TTT.TT.nxo_of(SA[sid], n0)(sig)
                nxo_diff += int(ut != u)
            if u is not None and 2 * u < mtick:
                tx = (u, float(I["op"][u]), u, "真頂訊號次一有效開盤"); early = True
            else:
                tx = mx; early = False
            TX[(hk, c)] = {"S": mx, "T": tx, "sig": sig, "src": src, "early": early, "ta": ta, "ep_a": ep_a, "t": int(rr["t"]), "h": int(rr["h"]),
                           "t起漲點": int(tt[sig - tb]) if sig is not None else None, "無飆股資料": SW is None}
    gates["提早賣筆：truetopT 有效開盤 ≠ 本件有效開盤（筆數，含未提早）"] = nxo_diff
    log(f"[T 出場] 唯一持股×格 {len(TX)}｜提早賣 {sum(v['early'] for v in TX.values())}｜無飆股資料持股 {nos}｜{time.time() - T0:.0f}s")
    return WS, ENG, RAW, HI, TX, gates, sinfo, info


def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    # 早年：處置表起始日
    from backtest import researchSurge5 as S5
    dsp = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    d0 = str(dsp["start_date"].min())
    early = {"處置表": os.path.join(S5.MAIN, "meta", "disposal.csv"), "處置表最早 start_date": d0, "處置表筆數": int(len(dsp)),
             "早年各年處置筆數": {k: int(v) for k, v in dsp["start_date"].astype(str).str[:4].value_counts().sort_index().items() if k <= "2014"}}
    early["早年可算"] = bool(d0 < EARLY0)
    early["結論"] = "可算" if early["早年可算"] else f"不可算（無處置資料）：處置表最早 {d0}，早年段 2005-02～2014-12 大部分期間沒有處置資料 ⇒ 真頂訊號無法判，⛔ 不硬算"
    log(f"[早年] {early}")
    WS, ENG, RAW, HI, TX, gates, sinfo, minfo = build(log)
    W = WS[WN]; cal = W["cal"]
    REF = pd.read_csv("backtest/resultsAddOn/seeds.csv.gz", float_precision="round_trip")
    REF = REF[(REF["世界"] == WN) & (REF["臂"] == "主臂")].set_index(["策略", "r", "格", "段"])
    rows = []; trows = []; dS = 0.0
    for key in sorted(ENG):
        _, sn, r = key; E = ENG[key]; eq = E["eq"]; first, end = E["first"], E["end"]
        HL = [((WN, sn, sid, tb), amt) for sid, tb, amt, ep, ts, pxs in RAW[key]]
        for c in AO.CELLS:
            acts = [(TX[(hk, c)]["t"], hk, amt) for hk, amt in HL if (hk, c) in TX]
            acts.sort(key=lambda z: (z[0], z[1][2]))
            POS = {}
            for arm in ("S", "T"):
                POS[arm] = []
                for t, hk, amt in acts:
                    v = TX[(hk, c)]; sd, px, pb, kind = v[arm]
                    POS[arm].append((v["ta"], amt, v["ep_a"], hk, sd, px, kind))
            for sg in SEGJ:
                x, y = W["segp"][sg]; a = max(x, first); yy = min(y, end - 1)
                c0, m0, _ = RR.win_metrics(eq, first, end, x, y)
                row = {"策略": sn, "r": r, "格": c, "段": sg, "原_年化": c0, "原_回落": m0}
                for arm in ("S", "T"):
                    navs, st = AO.account(eq, a, yy, POS[arm])
                    row[f"{arm}_加碼筆數"] = st["加碼筆數"]; row[f"{arm}_撥入總額÷段首權益"] = st["撥入總額÷段首權益"]; row[f"{arm}_MV÷W峰值"] = st["MV÷W峰值"]
                    for rd in READS:
                        cc, mm = AO.metrics(eq, first, end, x, y, a, navs[rd])
                        row[f"{arm}_{rd}_年化"] = cc; row[f"{arm}_{rd}_回落"] = mm
                row["T_提早賣筆數"] = int(sum(1 for t, hk, amt in acts if a < TX[(hk, c)]["ta"] <= yy and TX[(hk, c)]["early"]))
                ref = REF.loc[(sn, r, c, sg)]
                for rd in READS:
                    for k in ("年化", "回落"):
                        dS = max(dS, abs(row[f"S_{rd}_{k}"] - float(ref[f"{rd}_{k}"])))
                dS = max(dS, abs(c0 - float(ref["原_年化"])), abs(m0 - float(ref["原_回落"])))
                rows.append(row)
            for t, hk, amt in acts:
                v = TX[(hk, c)]; ta, ep_a = v["ta"], v["ep_a"]
                cl = HI[hk]["cl"]
                rS = (v["S"][1] / ep_a - 1.0 - AO.COST) if v["S"][0] is not None else np.nan
                rT = (v["T"][1] / ep_a - 1.0 - AO.COST) if v["T"][0] is not None else np.nan
                trows.append({"策略": sn, "r": r, "格": c, "sid": hk[2], "tb": hk[3], "t": t, "h": v["h"], "ta": ta, "加碼日": str(cal[ta].date()), "加碼價": ep_a, "金額": amt,
                              "訊號日": -1 if v["sig"] is None else v["sig"], "訊號來源": v["src"] or "", "訊號距加碼日": np.nan if v["sig"] is None else v["sig"] - ta,
                              "訊號起漲點": -1 if v["t起漲點"] is None else v["t起漲點"], "提早賣": v["early"], "無飆股資料": v["無飆股資料"],
                              "S_出場日": -1 if v["S"][0] is None else v["S"][0], "S_價": v["S"][1], "S_種類": v["S"][3],
                              "T_出場日": -1 if v["T"][0] is None else v["T"][0], "T_價": v["T"][1], "T_種類": v["T"][3], "S_淨報酬": rS, "T_淨報酬": rT})
    gates["臂 S vs resultsAddOn seeds 主臂（原、A/B/C 年化回落）最大差"] = dS
    log(f"[記帳] {len(rows)} 列｜臂 S 重現最大差 {dS:.3g}｜{time.time() - T0:.0f}s")
    if dS > 1e-12:
        raise SystemExit(f"⛔ 臂 S 重現閘不過 {dS}")
    SE = pd.DataFrame(rows); TD = pd.DataFrame(trows)
    SE.to_csv(os.path.join(OUT, "seeds_T.csv.gz"), index=False, float_format="%.17g")
    TD.to_csv(os.path.join(OUT, "trades_T.csv.gz"), index=False, float_format="%.17g")
    # ── 主表 ──
    MAIN = []
    for sn in AO.STRATS:
        for c in AO.CELLS:
            for sg in SEGJ:
                g = SE[(SE["策略"] == sn) & (SE["格"] == c) & (SE["段"] == sg)]
                co, mo = float(g["原_年化"].median()), float(g["原_回落"].median())
                for rd in READS:
                    sa, sm = float(g[f"S_{rd}_年化"].median()), float(g[f"S_{rd}_回落"].median())
                    ta_, tm = float(g[f"T_{rd}_年化"].median()), float(g[f"T_{rd}_回落"].median())
                    pTo = np.mean([AO.better(*z) for z in zip(g[f"T_{rd}_年化"], g[f"T_{rd}_回落"], g["原_年化"], g["原_回落"])])
                    pTS = np.mean([AO.better(*z) for z in zip(g[f"T_{rd}_年化"], g[f"T_{rd}_回落"], g[f"S_{rd}_年化"], g[f"S_{rd}_回落"])])
                    MAIN.append({"策略": sn, "格": c, "挑中格": c == PICK[sn], "段": sg, "讀法": rd, "顆數": len(g),
                                 "原_年化": co, "原_回落": mo, "原_比值": AO.ratio(co, mo),
                                 "S_年化": sa, "S_回落": sm, "S_比值": AO.ratio(sa, sm),
                                 "T_年化": ta_, "T_回落": tm, "T_比值": AO.ratio(ta_, tm),
                                 "T變好（vs原）": AO.better(ta_, tm, co, mo), "S變好（vs原）": AO.better(sa, sm, co, mo), "T變好（vs S）": AO.better(ta_, tm, sa, sm),
                                 "T−原 年化": ta_ - co, "T−S 年化": ta_ - sa, "T−原 回落": tm - mo, "T−S 回落": tm - sm,
                                 "逐顆 T變好vs原 比例": float(pTo), "逐顆 T變好vsS 比例": float(pTS),
                                 "T年化p10": float(g[f"T_{rd}_年化"].quantile(.1)), "T年化p90": float(g[f"T_{rd}_年化"].quantile(.9)),
                                 "逐顆 T−S 年化中位": float((g[f"T_{rd}_年化"] - g[f"S_{rd}_年化"]).median()),
                                 "加碼筆數中位": float(g["T_加碼筆數"].median()), "提早賣筆數中位": float(g["T_提早賣筆數"].median())})
    MT = pd.DataFrame(MAIN)
    MT.to_csv(os.path.join(OUT, "truetop_main.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    DG = json.load(open("backtest/resultsAddOn/degeneracy.json", encoding="utf-8"))
    VER = {}
    for sn in AO.STRATS:
        for c in AO.CELLS:
            for rd in ("A", "B"):
                row = lambda sg: MT[(MT["策略"] == sn) & (MT["格"] == c) & (MT["段"] == sg) & (MT["讀法"] == rd)].iloc[0]
                ex, cf = row("探索"), row("確認")
                d = DG["格"][f"{sn}·{c}"]
                insuff = bool(d["確認段樣本不足（＜ 20）"]); degen = bool(d["退化（探索 ＜ 20）"])
                okO = bool(ex["T變好（vs原）"]) and bool(cf["T變好（vs原）"]) and not insuff
                okS = bool(ex["T變好（vs S）"]) and bool(cf["T變好（vs S）"]) and not insuff
                VER[f"{sn}·{c}·{rd}"] = {"挑中格": c == PICK[sn], "探索退化": degen, "確認段樣本不足": insuff,
                                         "T vs 原：探索變好": bool(ex["T變好（vs原）"]), "T vs 原：確認變好": bool(cf["T變好（vs原）"]),
                                         "T vs 原 結論": ("變好（只當參考、事後重切）" if okO else ("確認段樣本不足、不判" if insuff and ex["T變好（vs原）"] else "沒有變好")),
                                         "T vs S：探索變好": bool(ex["T變好（vs S）"]), "T vs S：確認變好": bool(cf["T變好（vs S）"]),
                                         "T vs S 結論": ("變好（只當參考、事後重切）" if okS else ("確認段樣本不足、不判" if insuff and ex["T變好（vs S）"] else "沒有變好"))}
    log(f"[判定] {json.dumps({k: (v['T vs 原 結論'], v['T vs S 結論']) for k, v in VER.items()}, ensure_ascii=False)}")
    # ── 必報 ──
    REP = {}
    for sn in AO.STRATS:
        for c in AO.CELLS:
            for sg in SEGJ:
                x, y = W["segp"][sg]
                for basis in (("200顆合併", "唯一持股") if sn == "營飆" else ("r0",)):
                    t_ = TD[(TD["策略"] == sn) & (TD["格"] == c) & (TD["ta"] > x) & (TD["ta"] <= y)]
                    if basis == "唯一持股":
                        t_ = t_.drop_duplicates(["sid", "tb"])
                    e_ = t_[t_["提早賣"]]
                    cl_ = t_[t_["S_出場日"] >= 0]; ecl = e_[e_["S_出場日"] >= 0]
                    dd = (ecl["T_淨報酬"] - ecl["S_淨報酬"])
                    REP[f"{sn}·{c}·{sg}·{basis}"] = {
                        "加碼筆": int(len(t_)), "提早賣筆": int(len(e_)), "提早賣比例": float(len(e_) / len(t_)) if len(t_) else None,
                        "提早賣由 W2a（再次處置）": int((e_["訊號來源"] == "W2a").sum()), "提早賣由 W2b（處置出關）": int((e_["訊號來源"] == "W2b").sum()),
                        "有訊號但沒提早（訊號隔天開盤不早於主臂）": int(((t_["訊號日"] >= 0) & ~t_["提早賣"]).sum()),
                        "無飆股資料筆": int(t_["無飆股資料"].sum()),
                        "訊號距加碼日（交易日，提早賣筆）": q3(e_["訊號距加碼日"]),
                        "訊號距加碼日分組": {k: int(((e_["訊號距加碼日"] >= lo) & (e_["訊號距加碼日"] <= hi)).sum()) for k, (lo, hi) in
                                        {"0～4": (0, 4), "5～9": (5, 9), "10～19": (10, 19), "20～39": (20, 39), "40～59": (40, 59), "60+": (60, 9999)}.items()},
                        "提早賣：T淨 − S淨（S 已出場者）": {**q3(dd), "T 較好比例": float((dd > 0).mean()) if len(dd) else None},
                        "提早賣但 S 資料尾仍持有（不進差）": int(len(e_) - len(ecl)),
                        "加碼部位淨報酬 S（S 已出場）": q3(cl_["S_淨報酬"]), "加碼部位淨報酬 T（同一批）": q3(cl_["T_淨報酬"]),
                        "營飆說明": "200 顆合併 ＝ 同一筆在多顆出現就算多次；唯一持股 ＝ 去重" if sn == "營飆" else None}
    S = {"讀法寫死": TIME, "事後重切": NOTE, "使用者指示": "加碼那份改用真頂訊號賣出，或到時間一起賣出就這兩種!（2026-10-12）",
         "挑中格（寫死）": PICK, "閘": gates, "飆股資料": sinfo, "母體（researchAddOn.market）": minfo, "早年": early,
         "判定": VER, "主表": MT.to_dict("records"), "必報": REP,
         "臂": {"原": "原策略（營量 v1／營飆 v1 正式）", "S": "researchAddOn 主臂：加碼那份跟原持股同日同價賣", "T": "加碼那份：加碼日起第一個真頂訊號 T1 ⇒ 次一有效開盤賣；沒有 ⇒ 跟原持股一起賣"},
         "讀法": {"A": "累計撥入（時間加權）", "B": "峰值撥入（段首預留）", "C": "描述：撥入即用、出場退回"},
         "耗時秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "truetop.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


def main():
    os.makedirs(OUT, exist_ok=True)
    log = AO.log_to(os.path.join(OUT, "run.log"))
    log(f"[開跑] {AO.now_tpe()}（台北）")
    run(log)


if __name__ == "__main__":
    main()

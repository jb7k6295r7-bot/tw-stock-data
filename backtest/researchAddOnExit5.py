# -*- coding: utf-8 -*-
"""漲多加碼：只把「加碼那一份」的出場換成出場五法（使用者 2026-10-13 逐字：「我在算的是加碼的部分不是？原規則沒有動啊」）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。
⚠ 範圍更正：backtest/researchExit5.py（五法套原持股整筆）是理解錯；本件 ＝ 原持股完全照正式，只改加碼部位出場。加碼已看過結果（researchAddOn、truetop）⇒ 事後重切、最多暫定（N 待裁定）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnExit5 [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnExit5_check [--procs 3]

═══ 讀法（Y 標；寫死 TIME（台北），在算任何本件數字之前；看過的：researchAddOn／researchAddOn_truetop／researchAddOn_truetop_peak／researchExit5 全文與
    researchAddOn、truetop 判定（兩策略加碼版都沒變好；T vs S 營飆 A1 變好）、Exit5 判定（套原持股 10 判定 0 變好）、登錄 seq1 sha e59718354bec67e0 全文）═══
 Y0 原持股、加碼條件、加碼價、加碼金額、資金讀法 A／B／C、成本、壞根、段 ＝ researchAddOn 一字不動（import 它的 holdings／market／main_exit／thresholds／account／metrics／
    better／ratio／t2 等；讀它留下的 ~/addonwork/world_{主,早年}.pkl、engine_200.pkl、resultsAddOn/triggers.csv.gz）；只改「加碼那一份」的出場
 Y1 臂 S ＝ researchAddOn 主臂（同原持股同日同價賣）：本檔重算，閘 ＝ 與 resultsAddOn/seeds.csv.gz 主臂 原／A／B／C 年化回落逐列差 ≤ 1e−12
    臂 T ＝ researchAddOn_truetop 的臂 T（直接讀 resultsAddOn/truetop/seeds_T.csv.gz，⛔ 不重算）；早年 T 不可算（處置表 2010-12 起）
 Y2 五法訊號 ＝ 直接呼叫 researchExit5.row_variants（⛔ 不另寫訊號邏輯），代入加碼語境：
      e ＝ ta（加碼日，算第 1 根）、bp ＝ 加碼價 ep_a（ta 開盤還原價）、pos ＝ t（決策日 ＝ 加碼前一根，ATR 取 t 往前 20 根有效 K 棒）、L ＝ None；
      xf ＝ 臂 S 的價所在根 pb（正常 ＝ 原持股第 H 根；停止交易 ＝ L；壞根強制 ＝ 壞根前收盤根）、資料尾仍持有 ⇒ xf ＝ n0（X 上限 ＝ n0−1）；gf ＝ S 價 ÷ ep_a − 1
      ⇒ 判斷期 d ∈ [ta, xf−1]，動作 X ＝ d 之後第一個有效開盤且 X ≤ xf（xf 開盤早於 xf 收盤）；沒觸發或 X 不早於 S ⇒ 該部分照臂 S
      ⇒ row_variants 回傳的 parts：("open", X) 部分 ＝ 提早賣（記帳日 X、價 ＝ X 開盤還原價）；其餘部分 ＝ 臂 S 的 (sd, px)（記帳日、價一字不動）
      閘：row_variants 的壞根修正（fix）在本件不該發生（X ≤ xf ＜ 下一個壞根；S 已含壞根強制）⇒ bad 列數 ＝ 0 才放行
    法 1 M ＝ [ta, d] 有效 K 棒最高收盤（含加碼日）；E1a：收盤 ≤ M − 2×ATR、E1b：≤ M − 4×ATR；ATR NaN ⇒ 該筆該法不判（照報筆數）
    法 2 收盤 ＜ MA5，且 [ta, d] 有效 K 棒 ≥ 6（加碼後第 6 根起判）⇒ 整份加碼部位賣
    法 3 持有中（可得日 A ≥ ta）新公布月營收年增 ≤ 0 ⇒ 可得日後第一個有效開盤賣整份
    法 4（⚠ 加碼語境讀法）：「加碼部位持有報酬 g ＝ 收盤[d] ÷ 加碼價 − 1、h ＝ d − ta ＋ 1（ta 算第 1 根）、h ≥ 10、(ta, d] 無壞根、d 有效 K 棒、
      g ≥ q99(h, d)（R1 母體同 h 報酬第 99 百分位，researchAddOn.thresholds 原式）」⇒ 賣加碼部位的一半（＝ 登錄法 4 的式子把「買進」換成「加碼」，最接近登錄的寫法）
    法 5 d ≥ ta＋1、d 有效 K 棒且非壞根、單日還原報酬 r ≤ q2(d)（R1 母體當日第 2 百分位，researchExit5 同式）且 r ＜ 0 ⇒ 賣加碼部位一半
    描述臂（⛔ 不判）：D1_5／D1_10 收盤 ≤ (1−5%／10%) × M 整份；D4 加碼部位持有報酬 ≥ +100% 賣一半；D5 單日還原報酬 ＜ −5% 賣一半
    每筆每法只動作一次；賣一半後剩下那一半照臂 S
 Y3 錢：賣出（整份或一半）的錢 ＝ A × w × (賣價 ÷ 加碼價 − COST) 當天回加碼子帳戶 K（researchAddOn.account 原式；⛔ 不補別檔、⛔ 不回原策略）；
    一半先賣 ⇒ 兩塊各付自己的 COST（金額相同、只差時點）
 Y4 判定（seq342 口徑）：每法 × 每策略 × 讀法 A、B 各判（C 描述）：「該法加碼版」對「原策略」變好 ＝ 年化較高 且 年化÷|回落| ≥ 原策略；探索 2017-03-02～2021-12-30、
    確認 2022-01-03～2026-08-24 兩段都要；營飆 ＝ 200 顆中位（年化中位、回落中位、比值 ＝ 年化中位÷|回落中位|）；另報逐顆比例
    格：寫死 營量 A2、營飆 A1（researchAddOn 挑中格）為主；另一格（營量 A1、營飆 A2）描述（營飆 A2 探索加碼 ＜ 20 筆 ＝ 退化，照標）
    法 1：E1a、E1b 探索段挑比值較高者（非退化者先；同 ⇒ 年化高 ⇒ E1a），每讀法各自挑；判定 ＝ 挑中者兩段都變好
    另報 vs 臂 S、vs 臂 T（同式、同兩段）；確認段加碼筆數 ＜ 20（researchAddOn degeneracy）⇒「確認段樣本不足、不判」
    結論字樣：「變好（事後重切、最多暫定；N 待裁定）」／「沒有變好（探索段就沒變好）」／「沒有變好（確認段沒變好）」／「退化、不判」
    早年 2005-02～2014-12：五法、S 全部可算（價格、R1、營收、reduce_v2 壞根同 researchAddOn）⇒ 描述、⛔ 不判；T 不可算
 Y5 退化（seq325：先寫 degeneracy.json 附台北時間，再算任何報酬；⚠ 門檻為執行者所訂）：
    ① 繼承 researchAddOn U6：探索段加碼筆數（營飆 200 顆中位）＜ 20 ⇒ 該格退化；確認段 ＜ 20 ⇒ 確認段樣本不足
    ② 觸發太少：探索段該法提早動作筆數（中位）＜ 5 ⇒ 該法在該格對加碼部位幾乎沒作用（＝ 臂 S），退化
    ③ 觸發太快：探索段加碼部位按金額加權平均持有根數（中位）＜ 5 ⇒ 幾乎等於沒加碼，退化
 Y6 必報（依加碼日 ta 分段 (x, y]；營飆 ＝ 200 顆合併、另報唯一（世界, sid, tb, 格）去重）：
    各法觸發（提早動作）比例；提早動作筆 該法淨報酬 − 臂 S 淨報酬（S 資料尾仍持有者不計；中位、p10、p90、平均、較好比例）；
    加碼部位淨報酬分布（同一批：S 已出場者；S、T（主世界讀 truetop trades_T）、各法）；
    賣後 60 根新高（researchExit5.post60(pk, X, d, ta, n0)：[X, X＋59] 有效 K 棒最高收盤 ＞ [ta, d] 最高收盤；唯一觸發列）；臂 S 對照 post60(pk, pb＋1, pb, ta, n0)；
    賣出點距整段最高點（researchAddOn_truetop_peak.rowstats／describe；起漲點 t ＝ truetopT.anchor_pit(c, d, tb)（原持股進場日錨定，同 truetop）、
      敏感度 te ＝ anchor_pit(c, tb, tb)；賣價 ＝ X 開盤）；ATR 視窗跨壞根筆數（描述）
 輸出 backtest/resultsAddOn/exit5/：degeneracy.json（先寫）、AddOnExit5.json、AddOnExit5_main.csv、seeds.csv.gz、exits.csv.gz（唯一 加碼×格 的各臂出場）、
    paths.csv.gz（逐路徑加碼清單）、run.log
── 事後註（寫死之後、照實記；讀法沒改）──
 ① 00:48 第一次全跑時 TIME 字串誤植為「00:58」（晚於實際開跑）；更正為 00:48 後原樣重跑一次（計算 ⛔ 沒改；seeds／exits 與第一次逐位元比對，見 run.log）；
    第一次跑完後看過判定與必報，也跑過一次查核（00:53，通過）
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa: E402
from backtest import researchExit5 as EX5                     # noqa: E402
from backtest import rerun17 as RR                            # noqa: E402
from backtest import universe_gate as UG                      # noqa: E402

TIME = "2026-10-13 00:48（台北）"
OUT = "backtest/resultsAddOn/exit5"
PICK = {"營量": "A2", "營飆": "A1"}
JUDGED = ("E1a", "E1b", "E2", "E3", "E4", "E5")
DESC = ("D1_5", "D1_10", "D4", "D5")
EXARMS = JUDGED + DESC
ARMS = ("S",) + EXARMS
VNAME = {"S": "臂S 同原持股日賣", "T": "臂T 真頂訊號", "E1a": "法1 移動停利 2×ATR", "E1b": "法1 移動停利 4×ATR", "E2": "法2 跌破5日線",
         "E3": "法3 營收年增≤0", "E4": "法4 加碼部位漲到R1前1% 賣一半", "E5": "法5 單日跌落R1最低2% 賣一半",
         "D1_5": "描述 回落5%", "D1_10": "描述 回落10%", "D4": "描述 +100%賣一半", "D5": "描述 單日<−5%賣一半"}
HALF = EX5.HALF
METHODS = EX5.METHODS
READS = AO.READS
SEGS = AO.SEGS
DEG_ADD, DEG_TRIG, DEG_HOLD = 20, 5, 5.0
NOTE = ["⚠ 範圍更正後重算（使用者原意：只改加碼那一份）；加碼已看過結果 ⇒ 事後重切、最多暫定（N 待裁定）",
        "加碼用的是另外的錢；⛔ 不代表該把原策略的錢集中到漲最多的那檔", "加碼版用的錢比原策略多", "原持股照正式規則，只換加碼那一份的賣法"]
NOTE_EARLY = AO.NOTE_EARLY
_G: dict = {}


def q3(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p10（後10%）": float(np.quantile(v, .1)), "p90（前10%）": float(np.quantile(v, .9)), "平均": float(v.mean())}


# ═════════════ 每個世界：持股、母體、門檻、營收、加碼部位各臂出場 ═════════════
def build_world(wn, X, log, procs):
    T0 = time.time()
    W = pickle.load(open(os.path.join(AO.WORK, f"world_{wn}.pkl"), "rb")); cal = W["cal"]; n0 = len(cal); NP = W["NP"]
    ENG = pickle.load(open(os.path.join(AO.WORK, f"engine_{AO.NSEED}.pkl"), "rb"))
    ENG = {k: v for k, v in ENG.items() if k[0] == wn}
    TR = pd.read_csv("backtest/resultsAddOn/triggers.csv.gz", dtype={"sid": str}); TR = TR[TR["世界"] == wn].copy()
    RAW = {k: AO.holdings(E["au"]) for k, E in ENG.items()}
    uh = {}
    for (w_, sn, r), Hs in RAW.items():
        for sid, tb, amt, ep, ts, pxs in Hs:
            uh[(w_, sn, sid, tb)] = (ep, ts, pxs)
    TRi = TR.set_index(["策略", "sid", "tb", "格"])
    UG.set_gate_v2(True)
    M, HB, X, minfo = AO.market(wn, W, X, log, sorted({hk[2] for hk in uh}))
    HI = {}
    for hk, (ep, ts, pxs) in uh.items():
        sn, sid, tb = hk[1], hk[2], hk[3]
        r0 = TRi.loc[(sn, sid, tb, "A1")]
        HI[hk] = {"sid": sid, "tb": tb, "ep": ep, "ts": ts, "pxs": pxs, "xbar": int(r0["xbar"]), "sf": bool(r0["停止交易強制"]),
                  "cl": W["closes"][sid], "op": W["opens"][sid], "bar": HB[sid][0], "bad": HB[sid][1]}
    AO._G.setdefault("HI", {}).update(HI); AO._G.setdefault("NCAL", {})[wn] = n0
    TA = TR[TR["結果"] == "加碼"].copy()
    sids = sorted(set(TA["sid"]))
    # 逐股陣列（researchExit5.stock_pack，load_bars 有效 K 棒）
    EX5._G["data"] = W["data"]; EX5._G["cal"] = cal
    with Pool(procs) as pool:
        LBS = dict(pool.map(EX5.bars_job, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=4))
    miss = [s for s in sids if LBS.get(s) is None]
    if miss:
        raise SystemExit(f"⛔ load_bars 取不到 {miss[:5]}")
    PK = {}; md = 0.0
    for s in sids:
        PK[s] = EX5.stock_pack(W, s, LBS[s], HB, n0, NP)
        idx, h, l, cb = LBS[s]; ok = idx < n0
        cw = PK[s]["c"][idx[ok]]; m_ = np.isfinite(cw) & np.isfinite(cb[ok])
        if m_.any():
            md = max(md, float(np.max(np.abs(cb[ok][m_] / cw[m_] - 1.0))))
    gates = {f"{wn} load_bars 收盤 vs 世界收盤 最大相對差": md}
    if md > 1e-6:
        raise SystemExit(f"⛔ {wn} 收盤閘 {md}")
    # 門檻 q99(h, d)（researchAddOn.thresholds 原式）、q2(d)（researchExit5 run 內同式）
    HMAX = AO.HMIN; t_lo = 10 ** 9
    for z in TA.itertuples(index=False):
        hk = (wn, z.策略, z.sid, int(z.tb)); xb = HI[hk]["xbar"]
        HMAX = max(HMAX, min(xb, n0 - 1) - int(z.ta) + 2); t_lo = min(t_lo, int(z.ta) + AO.HMIN - 1)
    Q, NPOP = AO.thresholds(M, HMAX, t_lo, log, wn)
    C_, BAR, BAD, R1m = M["C"], M["BAR"], M["BAD"], M["R1"]
    with np.errstate(invalid="ignore", divide="ignore"):
        Rr = np.full(C_.shape, np.nan)
        m2 = R1m[:, 1:] & BAR[:, 1:] & np.isfinite(C_[:, :-1]) & ~BAD[:, 1:]
        Rr[:, 1:] = np.where(m2, C_[:, 1:] / C_[:, :-1] - 1.0, np.nan)
    cnt2 = np.isfinite(Rr).sum(0); Q2 = np.full(C_.shape[1], np.nan); ok2 = cnt2 >= EX5.MINPOP
    Q2[ok2] = np.nanpercentile(Rr[:, ok2], EX5.Q2PCT, axis=0)
    minfo["q2 可判日數"] = int(ok2.sum()); minfo["HMAX"] = int(HMAX)
    del M, Rr
    rev, rly, rinf = EX5.load_revenue(W["data"]); AV = EX5.avail_pos(list(rev.index), cal)
    REV = {s: EX5.rev_events(s, rev, rly, AV, n0) for s in sids}
    rinf["加碼股有營收"] = int(sum(1 for s in sids if s in rev.columns)); rinf["加碼股數"] = len(sids)
    ctxm = {"n0": n0, "cal": cal, "Q99": Q["A2"], "Q2": Q2, "REV": REV}
    # 每筆唯一 加碼×格
    TX = {}; nbad = 0; natr = 0; nta_nobar = 0; atr_badwin = 0
    for z in TA.itertuples(index=False):
        sn, sid, tb, c = z.策略, z.sid, int(z.tb), z.格
        hk = (wn, sn, sid, tb); I = HI[hk]; pk = PK[sid]
        ta, ep_a, t = int(z.ta), float(z.ep_a), int(z.t)
        mx = AO.main_exit(hk, ta); sd, px, pb, kind = mx
        if sd is None:
            xf = n0; gf = float(np.asarray(I["cl"], float)[n0 - 1]) / ep_a - 1.0
        else:
            xf = int(pb); gf = px / ep_a - 1.0
        V, info = EX5.row_variants(W, pk, sid, ta, xf, gf, ep_a, None, t, ctxm)
        natr += int(not np.isfinite(info["ATR"])); nta_nobar += int(not pk["bar"][ta])
        k_ = info["k"]
        if np.isfinite(info["ATR"]):
            lo = int(pk["idx"][k_ - 20])
            atr_badwin += int(np.asarray(I["bad"], bool)[lo + 1:t + 1].any())
        arms = {}
        for v in EXARMS:
            rec = V[v]; nbad += int(rec["bad"])
            parts = []
            for w, p in rec["parts"]:
                if p[0] == "open":
                    parts.append((float(w), int(p[1]), float(p[2]), "提早賣"))
                else:
                    parts.append((float(w), sd, px, kind))
            arms[v] = {"parts": parts, "trig": int(rec["trig"]), "d": -1 if rec["d"] is None else int(rec["d"]), "X": -1 if rec["X"] is None else int(rec["X"])}
        TX[(hk, c)] = {"S": mx, "arms": arms, "ta": ta, "ep_a": ep_a, "t": t, "h": int(z.h), "xf": xf, "ATR": float(info["ATR"])}
    gates.update({f"{wn} row_variants 壞根修正筆（應 0）": nbad, f"{wn} ATR NaN（加碼×格）": natr, f"{wn} 加碼日 ta 非 load_bars 有效 K 棒（加碼×格）": nta_nobar,
                  f"{wn} ATR 20 根視窗含壞根（加碼×格，描述）": atr_badwin})
    if nbad:
        raise SystemExit(f"⛔ {wn} row_variants 出現壞根修正 {nbad}")
    log(f"[{wn}] 加碼×格 {len(TX)}｜觸發 { {v: sum(x['arms'][v]['trig'] for x in TX.values()) for v in EXARMS} }｜{gates}｜{time.time() - T0:.0f}s")
    return {"W": W, "ENG": ENG, "RAW": RAW, "TX": TX, "PK": PK, "gates": gates, "minfo": minfo, "rinfo": rinf, "X": X}


def positions(TX, HL, c, arm):
    """路徑 HL ＝ [(hk, amt)] ⇒ 該臂加碼部位 [(ta, A, ep, hk, sd, px, kind)]。"""
    acts = sorted([(TX[(hk, c)]["t"], hk, amt) for hk, amt in HL if (hk, c) in TX], key=lambda z: (z[0], z[1][2]))
    P = []
    for t, hk, amt in acts:
        v = TX[(hk, c)]
        if arm == "S":
            sd, px, pb, kind = v["S"]; P.append((v["ta"], amt, v["ep_a"], hk, sd, px, kind))
        else:
            for w, sd, px, kind in v["arms"][arm]["parts"]:
                P.append((v["ta"], amt * w, v["ep_a"], hk, sd, px, kind))
    return P, acts


def path_job(key):
    wn, sn, r = key
    B = _G["B"][wn]; E = B["ENG"][key]; eq = E["eq"]; first, end = E["first"], E["end"]; W = B["W"]; TX = B["TX"]
    HL = [((wn, sn, sid, tb), amt) for sid, tb, amt, ep, ts, pxs in B["RAW"][key]]
    rows = []
    for c in AO.CELLS:
        POS = {}; ACTS = None
        for arm in ARMS:
            POS[arm], ACTS = positions(TX, HL, c, arm)
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]; a = max(x, first); yy = min(y, end - 1)
            c0, m0, _ = RR.win_metrics(eq, first, end, x, y)
            row = {"世界": wn, "策略": sn, "r": r, "格": c, "段": sg, "原_年化": c0, "原_回落": m0}
            inseg = [(t, hk, amt) for t, hk, amt in ACTS if a < TX[(hk, c)]["ta"] <= yy]
            row["加碼筆數"] = len(inseg)
            for arm in ARMS:
                navs, st = AO.account(eq, a, yy, POS[arm])
                if arm == "S":
                    row["撥入總額÷段首權益"] = st["撥入總額÷段首權益"]; row["MV÷W峰值"] = st["MV÷W峰值"]
                for rd in READS:
                    cc, mm = AO.metrics(eq, first, end, x, y, a, navs[rd])
                    row[f"{arm}_{rd}_年化"] = cc; row[f"{arm}_{rd}_回落"] = mm
                if arm != "S":
                    row[f"{arm}_提早動作筆數"] = int(sum(TX[(hk, c)]["arms"][arm]["trig"] for t, hk, amt in inseg))
                    hold = []
                    for t, hk, amt in inseg:
                        v = TX[(hk, c)]; n0 = len(W["cal"])
                        hold.append(sum(w * ((sd if sd is not None else n0 - 1) - v["ta"]) for w, sd, px, kind in v["arms"][arm]["parts"]))
                    row[f"{arm}_加碼部位平均持有根數"] = float(np.mean(hold)) if hold else np.nan
                else:
                    hold = [((TX[(hk, c)]["S"][0] if TX[(hk, c)]["S"][0] is not None else len(W["cal"]) - 1) - TX[(hk, c)]["ta"]) for t, hk, amt in inseg]
                    row["S_加碼部位平均持有根數"] = float(np.mean(hold)) if hold else np.nan
            rows.append(row)
    return rows


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    B = {}; X = None; gates = {}
    for wn in ("主", "早年"):
        B[wn] = build_world(wn, X, log, a.procs); X = B[wn]["X"]; gates.update(B[wn]["gates"])
    _G["B"] = B
    # ── 唯一出場表（不含報酬彙總）──
    ER = []
    for wn in ("主", "早年"):
        cal = B[wn]["W"]["cal"]; n0 = len(cal)
        for (hk, c), v in B[wn]["TX"].items():
            sd, px, pb, kind = v["S"]
            row = {"世界": wn, "策略": hk[1], "sid": hk[2], "tb": hk[3], "格": c, "t": v["t"], "h": v["h"], "ta": v["ta"], "加碼日": str(cal[v["ta"]].date()),
                   "加碼價": v["ep_a"], "ATR": v["ATR"], "xf": v["xf"], "S_出場日": -1 if sd is None else int(sd), "S_價": px, "S_價根": int(pb), "S_種類": kind}
            for arm in EXARMS:
                z = v["arms"][arm]; early = [p for p in z["parts"] if p[3] == "提早賣"]
                row.update({f"{arm}_trig": z["trig"], f"{arm}_d": z["d"], f"{arm}_X": z["X"], f"{arm}_w": early[0][0] if early else 0.0,
                            f"{arm}_px1": early[0][2] if early else np.nan})
            ER.append(row)
    ER = pd.DataFrame(ER).sort_values(["世界", "策略", "格", "sid", "tb"]).reset_index(drop=True)
    ER.to_csv(os.path.join(OUT, "exits.csv.gz"), index=False, float_format="%.17g")
    PR = []
    for wn in ("主", "早年"):
        for key, Hs in B[wn]["RAW"].items():
            for sid, tb, amt, ep, ts, pxs in Hs:
                for c in AO.CELLS:
                    if ((wn, key[1], sid, tb), c) in B[wn]["TX"]:
                        PR.append({"世界": wn, "策略": key[1], "r": key[2], "格": c, "sid": sid, "tb": tb, "金額": amt})
    pd.DataFrame(PR).to_csv(os.path.join(OUT, "paths.csv.gz"), index=False, float_format="%.17g")
    # ── 退化（Y5）：先算不含報酬的筆數與持有根數，寫 degeneracy.json ──
    DGA = json.load(open("backtest/resultsAddOn/degeneracy.json", encoding="utf-8"))
    keys = sorted(k for wn in B for k in B[wn]["ENG"])
    CNT = {}
    for key in keys:
        wn, sn, r = key; Bw = B[wn]; W = Bw["W"]; E = Bw["ENG"][key]; n0 = len(W["cal"])
        HL = [((wn, sn, sid, tb), amt) for sid, tb, amt, ep, ts, pxs in Bw["RAW"][key]]
        for c in AO.CELLS:
            _, acts = positions(Bw["TX"], HL, c, "S")
            for sg in SEGS[wn]:
                x, y = W["segp"][sg]; a_ = max(x, E["first"]); y_ = min(y, E["end"] - 1)
                ins = [hk for t, hk, amt in acts if a_ < Bw["TX"][(hk, c)]["ta"] <= y_]
                for arm in EXARMS:
                    ntr = sum(Bw["TX"][(hk, c)]["arms"][arm]["trig"] for hk in ins)
                    hold = [sum(w * ((sd if sd is not None else n0 - 1) - Bw["TX"][(hk, c)]["ta"]) for w, sd, px, kind in Bw["TX"][(hk, c)]["arms"][arm]["parts"]) for hk in ins]
                    CNT.setdefault((sn, c, arm, sg), []).append((len(ins), ntr, float(np.mean(hold)) if hold else np.nan))
    DG = {"寫入時間": AO.now_tpe() + "（台北）", "說明": "⭐ 本檔在算任何報酬之前寫入（Y5、裁定 seq325）；① 繼承 researchAddOn：探索段加碼筆數（中位）＜ 20 ⇒ 格退化，確認段 ＜ 20 ⇒ 樣本不足；"
          "② 探索段提早動作筆數（中位）＜ 5 ⇒ 該法退化（≈ 臂 S）；③ 探索段加碼部位按金額加權平均持有根數（中位）＜ 5 ⇒ 該法退化（≈ 沒加碼）；②③ 門檻為執行者所訂", "格": {}}
    for sn in AO.STRATS:
        for c in AO.CELLS:
            ga = DGA["格"][f"{sn}·{c}"]
            for arm in EXARMS:
                d = {}
                for sg in ("探索", "確認", "主窗", "早年"):
                    z = np.asarray(CNT[(sn, c, arm, sg)], float)
                    d[sg] = {"加碼筆數（中位）": float(np.median(z[:, 0])), "提早動作筆數（中位）": float(np.median(z[:, 1])),
                             "加碼部位平均持有根數（中位）": float(np.nanmedian(z[:, 2])) if np.isfinite(z[:, 2]).any() else None}
                e_ = d["探索"]
                d["①格退化（繼承）"] = bool(ga["退化（探索 ＜ 20）"]); d["確認段樣本不足（繼承）"] = bool(ga["確認段樣本不足（＜ 20）"])
                d["②觸發太少"] = bool(e_["提早動作筆數（中位）"] < DEG_TRIG)
                d["③觸發太快"] = bool(e_["加碼部位平均持有根數（中位）"] is not None and e_["加碼部位平均持有根數（中位）"] < DEG_HOLD)
                d["退化"] = bool(d["①格退化（繼承）"] or d["②觸發太少"] or d["③觸發太快"])
                DG["格"][f"{sn}·{c}·{arm}"] = d
    json.dump(DG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json：{ {k: (v['探索']['提早動作筆數（中位）'], v['探索']['加碼部位平均持有根數（中位）'], v['退化']) for k, v in DG['格'].items()} }")
    # ── 記帳 ──
    with Pool(a.procs) as pool:
        res = pool.map(path_job, keys, chunksize=2)
    SE = pd.DataFrame([r_ for rr in res for r_ in rr])
    # 閘：臂 S ＝ researchAddOn 主臂
    REF = pd.read_csv("backtest/resultsAddOn/seeds.csv.gz", float_precision="round_trip")
    REF = REF[REF["臂"] == "主臂"].set_index(["世界", "策略", "r", "格", "段"])
    dS = 0.0
    for z in SE.itertuples(index=False):
        ref = REF.loc[(z.世界, z.策略, z.r, z.格, z.段)]
        dS = max(dS, abs(z.原_年化 - float(ref["原_年化"])), abs(z.原_回落 - float(ref["原_回落"])))
        for rd in READS:
            dS = max(dS, abs(getattr(z, f"S_{rd}_年化") - float(ref[f"{rd}_年化"])), abs(getattr(z, f"S_{rd}_回落") - float(ref[f"{rd}_回落"])))
    gates["臂 S vs resultsAddOn seeds 主臂（原、A/B/C 年化回落）最大差"] = dS
    log(f"[記帳] {len(SE)} 列｜臂 S 重現最大差 {dS:.3g}｜{time.time() - T0:.0f}s")
    if dS > 1e-12:
        raise SystemExit(f"⛔ 臂 S 重現閘不過 {dS}")
    # 臂 T（truetop，主世界）併入
    TT = pd.read_csv("backtest/resultsAddOn/truetop/seeds_T.csv.gz", float_precision="round_trip")
    TT = TT[[c for c in TT.columns if c in ("策略", "r", "格", "段") or (c.startswith("T_") and c.split("_")[1] in READS)]]
    TT.insert(0, "世界", "主")
    SE = SE.merge(TT, on=["世界", "策略", "r", "格", "段"], how="left")
    gates["臂 T 併入：主世界缺列"] = int(SE[(SE["世界"] == "主")]["T_A_年化"].isna().sum())
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # ── 主表 ──
    MAIN = []
    for wn in ("主", "早年"):
        for sn in AO.STRATS:
            for c in AO.CELLS:
                for sg in SEGS[wn]:
                    g = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["格"] == c) & (SE["段"] == sg)].sort_values("r")
                    co, mo = float(g["原_年化"].median()), float(g["原_回落"].median())
                    for rd in READS:
                        armsT = ARMS + (("T",) if wn == "主" else ())
                        sa, sm = float(g[f"S_{rd}_年化"].median()), float(g[f"S_{rd}_回落"].median())
                        if wn == "主":
                            tA, tM = float(g[f"T_{rd}_年化"].median()), float(g[f"T_{rd}_回落"].median())
                        MAIN.append({"世界": wn, "策略": sn, "格": c, "挑中格": c == PICK[sn], "段": sg, "讀法": rd, "臂": "原", "臂名": "原策略", "顆數": len(g),
                                     "年化": co, "回落": mo, "比值": AO.ratio(co, mo), "加碼筆數中位": float(g["加碼筆數"].median())})
                        for arm in armsT:
                            ca, ma = float(g[f"{arm}_{rd}_年化"].median()), float(g[f"{arm}_{rd}_回落"].median())
                            pO = np.mean([AO.better(*z) for z in zip(g[f"{arm}_{rd}_年化"], g[f"{arm}_{rd}_回落"], g["原_年化"], g["原_回落"])])
                            rr = {"世界": wn, "策略": sn, "格": c, "挑中格": c == PICK[sn], "段": sg, "讀法": rd, "臂": arm, "臂名": VNAME[arm], "顆數": len(g),
                                  "年化": ca, "回落": ma, "比值": AO.ratio(ca, ma), "原_年化": co, "原_回落": mo, "原_比值": AO.ratio(co, mo),
                                  "變好vs原": AO.better(ca, ma, co, mo), "逐顆變好vs原比例": float(pO), "年化−原": ca - co, "回落−原": ma - mo,
                                  "年化p10": float(g[f"{arm}_{rd}_年化"].quantile(.1)), "年化p90": float(g[f"{arm}_{rd}_年化"].quantile(.9)),
                                  "加碼筆數中位": float(g["加碼筆數"].median())}
                            if arm != "S":
                                pS = np.mean([AO.better(*z) for z in zip(g[f"{arm}_{rd}_年化"], g[f"{arm}_{rd}_回落"], g[f"S_{rd}_年化"], g[f"S_{rd}_回落"])])
                                rr.update({"S_年化": sa, "S_回落": sm, "變好vsS": AO.better(ca, ma, sa, sm), "逐顆變好vsS比例": float(pS), "年化−S": ca - sa})
                            if arm in EXARMS:
                                rr["提早動作筆數中位"] = float(g[f"{arm}_提早動作筆數"].median())
                                if wn == "主":
                                    pT = np.mean([AO.better(*z) for z in zip(g[f"{arm}_{rd}_年化"], g[f"{arm}_{rd}_回落"], g[f"T_{rd}_年化"], g[f"T_{rd}_回落"])])
                                    rr.update({"T_年化": tA, "T_回落": tM, "變好vsT": AO.better(ca, ma, tA, tM), "逐顆變好vsT比例": float(pT), "年化−T": ca - tA})
                            MAIN.append(rr)
    MT = pd.DataFrame(MAIN)
    MT.to_csv(os.path.join(OUT, "AddOnExit5_main.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    # ── 判定（Y4）──
    row = lambda sn, c, sg, rd, arm: MT[(MT["世界"] == "主") & (MT["策略"] == sn) & (MT["格"] == c) & (MT["段"] == sg) & (MT["讀法"] == rd) & (MT["臂"] == arm)].iloc[0]
    VER = {}
    for sn in AO.STRATS:
        for c in AO.CELLS:
            for rd in ("A", "B"):
                for mth, cells in METHODS.items():
                    nd = [v for v in cells if not DG["格"][f"{sn}·{c}·{v}"]["退化"]]
                    pool_ = nd if nd else list(cells)
                    pick = sorted(pool_, key=lambda v: (-row(sn, c, "探索", rd, v)["比值"], -row(sn, c, "探索", rd, v)["年化"], list(cells).index(v)))[0]
                    ex, cf = row(sn, c, "探索", rd, pick), row(sn, c, "確認", rd, pick)
                    dg = DG["格"][f"{sn}·{c}·{pick}"]; insuff = dg["確認段樣本不足（繼承）"]
                    out = {"挑中格": c == PICK[sn], "法1挑中": pick if mth == "法1" else None, "臂": pick, "退化": dg["退化"], "確認段樣本不足": insuff}
                    for nm, key_ in (("原", "變好vs原"), ("S", "變好vsS"), ("T", "變好vsT")):
                        e1, c1 = bool(ex[key_]), bool(cf[key_])
                        out[f"vs{nm}：探索變好"] = e1; out[f"vs{nm}：確認變好"] = c1
                        out[f"vs{nm} 結論"] = ("退化、不判" if dg["退化"] else ("確認段樣本不足、不判" if insuff and e1 else
                                             ("變好（事後重切、最多暫定；N 待裁定）" if e1 and c1 else ("沒有變好（探索段就沒變好）" if not e1 else "沒有變好（確認段沒變好）"))))
                    for sg, r_ in (("探索", ex), ("確認", cf)):
                        out[sg] = {k: float(r_[k]) for k in ("原_年化", "原_回落", "原_比值", "年化", "回落", "比值", "S_年化", "S_回落", "T_年化", "T_回落", "逐顆變好vs原比例", "提早動作筆數中位")}
                    if mth == "法1":
                        out["探索段兩格比值"] = {v: float(row(sn, c, "探索", rd, v)["比值"]) for v in cells}
                    out["早年（描述）"] = {k: float(MT[(MT["世界"] == "早年") & (MT["策略"] == sn) & (MT["格"] == c) & (MT["讀法"] == rd) & (MT["臂"] == pick)].iloc[0][k])
                                         for k in ("原_年化", "原_回落", "原_比值", "年化", "回落", "比值", "S_年化", "S_回落")}
                    VER[f"{sn}·{c}·{rd}·{mth}"] = out
    log(f"[判定] {json.dumps({k: (v['臂'], v['vs原 結論'], v['vsS 結論'], v['vsT 結論']) for k, v in VER.items() if v['挑中格']}, ensure_ascii=False)}")
    # ── 必報（Y6）──
    REP = must_report(B, ER, log)
    S = {"讀法寫死": TIME, "使用者指示": "我在算的是加碼的部分不是？原規則沒有動啊（2026-10-13）", "結果句必附": NOTE, "早年必附": NOTE_EARLY,
         "登錄": "營量營飆出場五法 seq1 sha e59718354bec67e0（五法定義）；架構 ＝ researchAddOn／researchAddOn_truetop", "挑中格（寫死）": PICK,
         "閘": gates, "母體": {wn: B[wn]["minfo"] for wn in B}, "營收": {wn: B[wn]["rinfo"] for wn in B}, "退化": DG, "判定": VER,
         "主表": MT.to_dict("records"), "必報": REP,
         "讀法清單": {"A": "累計撥入（時間加權）", "B": "峰值撥入（段首預留）", "C": "描述：撥入即用、出場退回", "Y": "見 backtest/researchAddOnExit5.py 檔頭 Y0～Y6"},
         "臂": VNAME, "耗時秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "AddOnExit5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


def netret(parts, ep):
    if any(sd is None for w, sd, px, kind in parts):
        return np.nan
    return sum(w * px / ep for w, sd, px, kind in parts) - 1.0 - AO.COST


def must_report(B, ER, log):
    from backtest import researchYL_truetopT as TTT
    from backtest import researchAddOn_truetop_peak as PKF
    TD = pd.read_csv("backtest/resultsAddOn/truetop/trades_T.csv.gz", dtype={"sid": str})
    REP = {}
    for wn in ("主", "早年"):
        Bw = B[wn]; W = Bw["W"]; cal = W["cal"]; n0 = len(cal); TX = Bw["TX"]; PK = Bw["PK"]
        # 合併口徑：逐路徑展開
        PL = {}
        for key, Hs in Bw["RAW"].items():
            for sid, tb, amt, ep, ts, pxs in Hs:
                for c in AO.CELLS:
                    if ((wn, key[1], sid, tb), c) in TX:
                        PL.setdefault((key[1], c), []).append((wn, key[1], sid, tb))
        for sn in AO.STRATS:
            for c in AO.CELLS:
                for sg in SEGS[wn]:
                    x, y = W["segp"][sg]
                    for basis in (("200顆合併", "唯一") if sn == "營飆" else ("r0",)):
                        hks = [hk for hk in PL.get((sn, c), []) if x < TX[(hk, c)]["ta"] <= y]
                        if basis == "唯一":
                            hks = sorted(set(hks))
                        rep = {"加碼筆": len(hks)}
                        rS = {hk: netret([(1.0,) + tuple(TX[(hk, c)]["S"][i] for i in (0, 1)) + ("S",)], TX[(hk, c)]["ep_a"]) for hk in set(hks)}
                        Sdone = [hk for hk in hks if np.isfinite(rS[hk])]
                        rep["加碼部位淨報酬 S（S 已出場）"] = q3([rS[hk] for hk in Sdone])
                        if wn == "主":
                            td = TD[(TD["策略"] == sn) & (TD["格"] == c)].drop_duplicates(["sid", "tb"]).set_index(["sid", "tb"])["T_淨報酬"]
                            rep["加碼部位淨報酬 T（同一批）"] = q3([float(td.loc[(hk[2], hk[3])]) for hk in Sdone])
                        for arm in EXARMS:
                            rv = {hk: netret(TX[(hk, c)]["arms"][arm]["parts"], TX[(hk, c)]["ep_a"]) for hk in set(hks)}
                            tr = [hk for hk in hks if TX[(hk, c)]["arms"][arm]["trig"]]
                            dd = [rv[hk] - rS[hk] for hk in tr if np.isfinite(rS[hk]) and np.isfinite(rv[hk])]
                            o = {"提早動作筆": len(tr), "觸發比例": len(tr) / len(hks) if hks else None,
                                 "提早動作：該法淨 − S淨（S 已出場）": {**q3(dd), "該法較好比例": float(np.mean(np.asarray(dd) > 0)) if dd else None},
                                 "提早動作但 S 資料尾仍持有（不進差）": int(sum(1 for hk in tr if not np.isfinite(rS[hk]))),
                                 "加碼部位淨報酬（同一批：S 已出場）": q3([rv[hk] for hk in Sdone])}
                            if arm in ("E1a", "E1b"):
                                o["ATR NaN 筆"] = int(sum(1 for hk in hks if not np.isfinite(TX[(hk, c)]["ATR"])))
                            rep[arm] = o
                        REP[f"{wn}·{sn}·{c}·{sg}·{basis}"] = rep
                # 賣後 60 根新高、距整段最高點（唯一觸發列；主窗／早年）
                sgT = "主窗" if wn == "主" else "早年"; x, y = W["segp"][sgT]
                U = sorted({hk for hk in PL.get((sn, c), []) if x < TX[(hk, c)]["ta"] <= y})
                o = {}
                p60S = []
                for hk in U:
                    v = TX[(hk, c)]; sd, px, pb, kind = v["S"]
                    if sd is not None and pb < n0 - 1:
                        p60S.append(EX5.post60(PK[hk[2]], pb + 1, pb, v["ta"], n0))
                o["S 出場後60根又創新高（[pb＋1, pb＋60] 比 [ta, pb] 最高）"] = {"n": int(np.isfinite(p60S).sum()), "比例": float(np.nanmean(p60S)) if np.isfinite(p60S).any() else None}
                for arm in EXARMS:
                    p60 = []; prow = []
                    for hk in U:
                        v = TX[(hk, c)]; z = v["arms"][arm]
                        if not z["trig"]:
                            continue
                        d, X = z["d"], z["X"]; pk = PK[hk[2]]; cc = np.asarray(W["closes"][hk[2]], float)[:n0]
                        p60.append(EX5.post60(pk, X, d, v["ta"], n0))
                        t = TTT.anchor_pit(cc, d, hk[3]); te = TTT.anchor_pit(cc, hk[3], hk[3])
                        prow.append(PKF.rowstats(cc, t, te, d, float(pk["o"][X]), n0))
                    o[arm] = {"唯一觸發列": len(p60),
                              "賣出後60根又創新高": {"n": int(np.isfinite(p60).sum()), "比例": float(np.nanmean(p60)) if np.isfinite(p60).any() else None},
                              "賣出點距整段最高點": PKF.describe(pd.DataFrame(prow)) if prow else {"筆數": 0}}
                REP[f"{wn}·{sn}·{c}·{sgT}·新高與最高點（唯一）"] = o
    log("[必報] 完成")
    return REP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = AO.log_to(os.path.join(OUT, "run.log"))
    log(f"[開跑] {AO.now_tpe()}（台北）讀法寫死 {TIME}")
    run(a, log)


if __name__ == "__main__":
    main()

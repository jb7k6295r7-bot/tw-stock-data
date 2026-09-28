# -*- coding: utf-8 -*-
"""營量 提早一天：盤中確認才買（使用者指正後的做法；描述臂：不計 N、不改任何判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLearly_noon [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLearly_noon_check.py

使用者原話（逐字）：
  「如果前兩天準備好即將達成的個股，在達成前一天中午左右買進！（或許有可能是差一點點，然後算61天！？）」
  「通常可以預設最後一天的條件到達多少會達成啊，你怎麼會有這種困擾？」
  「成交量放大 3 倍，我看的到成交量啊！？」
⚠ 逐字標：B 臂「中午價以當日均價近似、判斷含輕微前視」；「中午成交量以全日×0.5 近似，含前視」。
⭐ 先驗提醒：本專案 回測 研究十二「早鳥不優於追高」。
═══ 規則（協調者轉述）＋ 本線讀法（S 標；看數字前寫死）═══
 名單（T−1 收盤後）：T−1 是 stock_features 合格根、AND 營收（讀 T−1 當下）成立
 A 開盤確認臂（沒有前視）：T−1 分數 ＝ 2、差的條件裡有價格條件（c1／c2／c4／c5 所需漲幅有限）
     T 開盤價 ≥ 最容易那條的門檻價 ⇒ 開盤價買；否則不買。c3（量）開盤看不到 ⇒ 不收
 B 中午確認臂（近似）：中午價 p ＝ 當日均價（成交額÷成交量、夾到當日區間；敏感度 (開＋收)÷2）；中午量 ＝ 全日成交額 × r（r ＝ 0.5；敏感度 0.4、0.6）
     價格條件確認 ＝ p ≥ 該條門檻價；c3 確認 ＝ r × 全日成交額 ≥ 3 × 前 20 日均額（成交量一路累加 ⇒ 中午已過 ⇒ 當天一定成立）
     T−1 分數 2：任一未達條件在中午確認（價格或 c3）⇒ 用 p 買
     T−1 分數 1、未達含 c3：c3 ＋ 至少一條價格條件都在中午確認 ⇒ 用 p 買
       S1 協調者寫「差兩條、其中一條是 c3（分數 2，差 c3 和一個價格條件）」——分數 2 只差一條；本線讀成「分數 1（差兩條才到 3）、其中一條是 c3」，
          分數 2 差 c3 的已含在上一行（只要 c3 確認就買）
     另列 B0（上一則指示的版本）：只有分數 2、只看價格（均價），不收 c3
 S2 門檻價 ＝ 收[T−1] ×（1＋該條所需隔日漲幅），所需漲幅同 researchYLearly S3（c2 ＝ 漲停價，換算成還原價）；c4 字面是「＞」，這裡用 ≥（差一個 tick 以內）
 S3 已經達成的條件假設 T 當天仍成立（只確認「差的那條」；使用者字面）；「T 收盤真的成立」另報 ⇒ 過價後收盤掉回去的比例 ＝ 1 − 成立比例
 S4 同檔去重 ＝ 營量 v1 的 20 根，作用在【有觸發買進的根】（名單每天重算、沒觸發不佔）
 S5 抱 61 根：第 T＋60 根收盤出（同 researchYLearly S5）；g ＝ 出場收盤 ÷ 進場價 − 1；名額 20、relvol（T−1）排序、stop_force 開；引擎一字不動
 並列：原版、上一版可執行 x5、完美預知（讀 resultsYLearly/table.csv，同一套引擎與閘）
 閘：原版 ＝ resultsT1fix c13 t1（主）／resultsYLexit3 營量v1 種子 0（主、早年）；原版換擴充字典 eq_sha 不變
輸出 backtest/resultsYLearly/noon/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import researchYLexit as YX
from backtest import researchYLexit3_b as YB
from backtest import researchYLearly as YE
from backtest import chart_svg as CS

OUT = "backtest/resultsYLearly/noon"
F_HTML = "營量盤中確認才買_20260928.html"
COST = R11.COST
RAWS = ["如果前兩天準備好即將達成的個股，在達成前一天中午左右買進！（或許有可能是差一點點，然後算61天！？）",
        "通常可以預設最後一天的條件到達多少會達成啊，你怎麼會有這種困擾？", "成交量放大 3 倍，我看的到成交量啊！？"]
TAG_B = "中午價以當日均價近似、判斷含輕微前視"
TAG_V = "中午成交量以全日×0.5 近似，含前視"
PRIOR = YE.PRIOR
PX = ("c1", "c2", "c4", "c5")
# 臂：(名稱, 種類, 價格代理, 量比例)
ARMS = [("A_開盤確認", "A", "open", None), ("B_中午確認", "B", "vw", 0.5), ("B_量0.4", "B", "vw", 0.4), ("B_量0.6", "B", "vw", 0.6),
        ("B_開收平均", "B", "oc", 0.5), ("B0_只看價", "B0", "vw", None)]
_G: dict = {}


def scan(args):
    sid, mk = args
    cal = _G["cal"]; n0 = len(cal); w0, w1 = _G["w0"], _G["w1"]
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        return None
    idx, o, c, h, l, amt, rc, df, up, dates = (B[k] for k in ("idx", "o", "c", "h", "l", "amt", "rc", "df", "up", "dates"))
    n = len(idx)
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = np.clip(np.where(vol > 0, amt / vol * c / rc, np.nan), l, h)
    oc = (o + c) / 2.0
    PXA = {"open": o, "vw": vw, "oc": oc}
    cond, score, eligible, nb_sig, _ = YE.feats(B)
    sp, hi = _G["PAN"].get(sid, (np.zeros(0, int), np.zeros(0, bool)))

    def andf(pos):
        j_ = int(np.searchsorted(sp, pos, side="right")) - 1
        return bool(j_ >= 0 and pos - sp[j_] <= YE.STALE and hi[j_])
    cf_ = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
    evd = _G["EVD"].get(sid, [])
    cand = []
    for j in np.flatnonzero(eligible[:n - 1] & ((score[:n - 1] == 2) | (score[:n - 1] == 1))):
        pj = int(idx[j])
        if not andf(pj):
            continue
        k = j + 1; T = int(idx[k])
        if not (w0 - 25 <= T <= w1 + 1):
            continue
        thr = {}
        if not cond[0, j]:
            thr["c1"] = (1 + YE.C1) * c[j - 19]
        if not cond[1, j] and int(up[j - 18:j + 1].sum()) == 2:
            lim = 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10
            thr["c2"] = c[j] * R11.limit_price(rc[j], True, lim) / rc[j]
        if not cond[3, j]:
            thr["c4"] = c[j - 98:j + 1].sum() / 99.0
        if not cond[4, j]:
            thr["c5"] = c[j - 248:j + 1].max()
        ap20 = float(np.mean(amt[k - 20:k]))
        c3_un = not bool(cond[2, j])
        e = k + 60; nbk = int(nb_sig[k]); xpos = -1; cx = np.nan
        if e < n and e < nbk:
            xpos = int(idx[e]); cx = c[e]
        elif e >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1:
            xpos = n0; cx = c[n - 1]
        r8 = False
        if xpos >= 0:
            for pe, pL in evd:
                if T <= pL and xpos >= pe:
                    xpos = pL; cx = cf_[pL]; r8 = True
        med = float(np.nanmedian(amt[j - 60:j])) if j >= 60 else np.nan
        rec = {"sid": sid, "j": int(j), "k": int(k), "T": T, "score_j": int(score[j]), "未達": "+".join(z for q, z in enumerate(YE.CN) if not cond[q, j]),
               **{f"thr_{z}": float(thr.get(z, np.nan)) for z in PX}, "最低門檻": float(min(thr.values())) if thr else np.nan,
               "最容易": (min(thr, key=lambda z: (thr[z], z)) if thr else ""), "收_Tm1": float(c[j]), "開_T": float(o[k]), "vw_T": float(vw[k]), "oc_T": float(oc[k]),
               "收_T": float(c[k]), "額_T": float(amt[k]), "均額20": ap20, "c3未達": c3_un,
               "relvol_j": float(amt[j]) / med if (j >= 60 and med > 0 and np.isfinite(amt[j])) else np.nan,
               "xpos": int(xpos), "出場收": float(cx), "R8截": r8, "T成立": bool(eligible[k] and score[k] >= 3 and andf(T)), "T分數": int(score[k])}
        for nm, kind, px, r in ARMS:
            p = float(PXA[px][k])
            pc = [z for z in thr if np.isfinite(p) and p >= thr[z] - 1e-9]
            if kind == "A":
                trig = score[j] == 2 and bool(thr) and np.isfinite(p) and p >= rec["最低門檻"] - 1e-9
                path = "價" if trig else ""
            elif kind == "B0":
                trig = score[j] == 2 and bool(pc); path = "價" if trig else ""
            else:
                c3ok = c3_un and r * amt[k] >= 3.0 * ap20
                if score[j] == 2:
                    trig = bool(pc) or c3ok
                    path = ("價＋量" if (pc and c3ok) else ("價" if pc else ("量" if c3ok else "")))
                else:
                    trig = c3_un and c3ok and bool(pc); path = "分數1：量＋價" if trig else ""
            rec[f"觸發_{nm}"] = bool(trig); rec[f"路徑_{nm}"] = path; rec[f"價_{nm}"] = p
            rec[f"g_{nm}"] = float(cx / p - 1.0) if (xpos >= 0 and np.isfinite(p) and p > 0) else np.nan
        cand.append(rec)
    for nm, *_ in ARMS:
        last = -10 ** 9
        for r in cand:
            ok = r[f"觸發_{nm}"] and r["j"] - last > YE.DD
            r[f"買_{nm}"] = bool(ok)
            if ok:
                last = r["j"]
    arr = None
    if cand:
        def mk_(a):
            z = np.full(n0, np.nan); z[idx] = a
            return z
        arr = {"open": mk_(o), "vw": mk_(vw), "oc": mk_(oc), "close32": pd.Series(df["close"].to_numpy()).ffill().to_numpy(np.float32),
               "valid": np.isfinite(df["close"].to_numpy(float))}
    return {"sid": sid, "rows": cand, "arr": arr}


def prep(wk, W, procs, panel_path, log, S):
    _G.clear(); _G.update(cal=W["cal"], w0=W["w0"], w1=W["w1"], PAN=YE.load_panel(panel_path), EVD=W["EVD"])
    t0 = time.time()
    with Pool(procs) as pool:
        res = [r for r in pool.imap_unordered(scan, YE.universe(), chunksize=8) if r is not None]
    ARR = {r["sid"]: r["arr"] for r in res if r["arr"] is not None}
    R = pd.DataFrame([x for r in res for x in r["rows"]]).sort_values(["T", "sid"]).reset_index(drop=True)
    log(f"[{wk}] 掃描 {len(res)} 檔｜名單列 {len(R):,}｜{time.time() - t0:.0f}s")
    NP = W["NP"]; w0, w1 = W["w0"], W["w1"]
    CL = dict(W["closes"]); new = []
    for s, a in ARR.items():
        if s not in CL:
            CL[s] = YE.pad(a["close32"], NP, "last"); new.append(s)
    SFx = {**W["SF"], **R11.stop_force_days({s: ARR[s]["valid"] for s in new}, w1)}
    OPD = {}
    for px in ("open", "vw", "oc"):
        d_ = dict(W["opens"])
        for s, a in ARR.items():
            if px == "open" and s in W["opens"]:
                continue                                           # 既有開盤字典原樣（⛔ 不換）
            d_[s] = YE.pad(a[px].astype(np.float32), NP, "nan")
        OPD[px] = d_
    AR = {"原版": (W["SIGH"][("營量", 60)], None, None, None), "原版_擴充字典": (W["SIGH"][("營量", 60)], CL, OPD["open"], SFx)}
    for nm, kind, px, r in ARMS:
        Q = R[R[f"買_{nm}"] & (R["T"] >= w0) & (R["T"] <= w1) & (R["xpos"] >= 0) & np.isfinite(R[f"g_{nm}"])]
        sg = pd.DataFrame({"sid": Q["sid"].to_numpy(), "k": Q["k"].to_numpy(int), "pos": Q["T"].to_numpy(int), "entry_pos": Q["T"].to_numpy(int),
                           "xpos_H60": Q["xpos"].to_numpy(np.int64), "g_H60": Q[f"g_{nm}"].to_numpy(float), "relvol": Q["relvol_j"].to_numpy(float)})
        AR[nm] = (sg, CL, OPD[px], SFx)
    # 開盤臂的進場價核對：引擎字典開盤（float32）vs 本支
    Q = R[R["買_A_開盤確認"]]
    S["資料"][f"{wk}｜A 臂：開盤 本支 vs 引擎字典（最大相對差）"] = float(np.nanmax(np.abs(np.array([OPD['open'][s][t] for s, t in zip(Q['sid'], Q['T'])], float) / Q["開_T"].to_numpy() - 1))) if len(Q) else 0.0
    S["資料"][f"{wk}｜補進收盤字典檔數"] = len(new)
    W["ARMS"] = AR; W["NR"] = R; W["ARR"] = ARR


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchYLearly_noon {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜盤中確認才買（描述臂） =====")
    S = {"身分": "描述臂、不計 N、不改任何判定", "使用者原話": RAWS, "逐字標": [TAG_B, TAG_V], "先驗提醒": PRIOR, "閘": {}, "資料": {}}
    Wm, We, ctx = YB.worlds(log)
    YE._W["主"] = Wm; YE._W["早年"] = We
    from backtest import researchV as V
    RR.use_snapshot()
    prep("主", Wm, a.procs, os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), log, S)
    D.DATA = V.body_paths("main")[0]
    prep("早年", We, a.procs, os.path.join(V.body_paths("main")[1], "panel_rev.csv.gz"), log, S)
    RR.use_snapshot()
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str})
    rf = ref[(ref["key"] == "c13") & (ref["var"] == "t1")].set_index("r")["eq_sha"]
    ref3 = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    ROWS = []; DIFF = {}; AUD = {}
    for wk, W in (("主", Wm), ("早年", We)):
        o, _ = YX._eng(W, "營量", W["SIGH"][("營量", 60)], "H60", 7000); W["V1EQ"] = np.asarray(o["equity"], float); sh = YX.sha(W["V1EQ"])
        S["閘"][f"{wk}｜原版 ＝ resultsYLexit3 營量v1 種子 0"] = bool(sh == ref3[(ref3["世界"] == wk) & (ref3["格"] == "營量v1") & (ref3["r"] == 0)]["eq_sha"].iloc[0])
        if wk == "主":
            S["閘"]["主｜原版 ＝ resultsT1fix c13 t1 種子 0"] = bool(sh == rf[0])
        names = list(W["ARMS"])
        with Pool(a.procs) as pool:
            res = pool.map(YE.run_arm, [(wk, nm) for nm in names])
        for nm, (row, diffs, aud_) in zip(names, res):
            ROWS.append(row); AUD[(wk, nm)] = aud_
            for sg, d in diffs.items():
                DIFF[(wk, nm, sg)] = d
        shas = {r["臂"]: r["eq_sha"] for r in ROWS if r["世界"] == wk}
        S["閘"][f"{wk}｜原版換擴充字典 eq_sha 不變"] = bool(shas["原版_擴充字典"] == sh and shas["原版"] == sh)
        log(f"[{wk}] 引擎完成｜{S['閘']}")
    SEED = pd.DataFrame(ROWS); SEED.to_csv(os.path.join(OUT, "arms.csv"), index=False, float_format="%.17g")
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    SEGW = (("探索", "主"), ("確認", "主"), ("早年", "早年"))
    TB = []
    for nm, *_ in ARMS:
        row = {"臂": nm}
        for sg, wk in SEGW:
            g = SEED[(SEED["世界"] == wk) & (SEED["臂"] == nm)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            m_, se_ = YX.cr0(DIFF[(wk, nm, sg)], months[sg])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_標籤": YX.label(cc, mm, Z[sg]), f"{sg}_差": m_ * 245,
                        f"{sg}_差lo": (m_ - 1.96 * se_) * 245, f"{sg}_差hi": (m_ + 1.96 * se_) * 245})
        for wk, W in (("主", Wm), ("早年", We)):
            R = W["NR"]; Q = R[R[f"買_{nm}"] & (R["T"] >= W["w0"]) & (R["T"] <= W["w1"])]
            ok = Q[(Q["xpos"] >= 0) & np.isfinite(Q[f"g_{nm}"])]
            yrs = (W["w1"] - W["w0"] + 1) / 245.0
            row[f"{wk}_觸發每年"] = len(Q) / yrs; row[f"{wk}_觸發筆數"] = int(len(Q))
            row[f"{wk}_T收盤成立"] = float(Q["T成立"].mean()) if len(Q) else np.nan
            row[f"{wk}_成立那批淨"] = float((ok[ok["T成立"]][f"g_{nm}"] - COST).mean()); row[f"{wk}_沒成立那批淨"] = float((ok[~ok["T成立"]][f"g_{nm}"] - COST).mean())
            row[f"{wk}_路徑"] = Q[f"路徑_{nm}"].value_counts().to_dict()
            TRd = YE.trades(AUD[(wk, nm)]); inf = {(s, int(t)): bool(f) for s, t, f in zip(ok["sid"], ok["T"], ok["T成立"])}
            cf = np.array([inf.get((r.sid, int(r.t_in))) for r in TRd.itertuples()], dtype=object)
            row[f"{wk}_組合成交"] = int(len(TRd)); row[f"{wk}_組合成立比例"] = float(np.mean(cf == True)) if len(TRd) else np.nan
            row[f"{wk}_組合平均淨"] = float(TRd["淨"].mean()) if len(TRd) else np.nan
        TB.append(row)
    TB = pd.DataFrame(TB); TB.to_csv(os.path.join(OUT, "table.csv"), index=False, float_format="%.9g")
    for wk, W in (("主", Wm), ("早年", We)):
        W["NR"].to_csv(os.path.join(OUT, f"rows_{wk}.csv.gz"), index=False, float_format="%.9g")
    OLD = pd.read_csv("backtest/resultsYLearly/table.csv").set_index("臂")
    S["表"] = TB.to_dict("records"); S["0050"] = Z
    log("[結果] " + "；".join(f"{r.臂} 確認 {r.確認_年化:+.2%}／{r.確認_回落:+.2%} {r.確認_標籤} 差 {r.確認_差:+.2%}｜成立 {r.主_T收盤成立:.0%}" for r in TB.itertuples()))
    # ── 例子（主、B_中午確認、確認段、組合實際成交）
    NM = "B_中午確認"; R = Wm["NR"]; Qb = R[R[f"買_{NM}"]]
    info = {(s, int(t)): r for s, t, r in zip(Qb["sid"], Qb["T"], Qb.to_dict("records"))}
    t0c, t1c = Wm["SEGP"]["確認"]
    TRd = YE.trades(AUD[("主", NM)]); TRd = TRd[(TRd["t_in"] > t0c) & (TRd["t_in"] <= t1c)].copy()
    TRd["info"] = [info.get((r.sid, int(r.t_in))) for r in TRd.itertuples()]; TRd = TRd[TRd["info"].notna()].copy()
    TRd["成立"] = [bool(i["T成立"]) for i in TRd["info"]]
    A_ = TRd[TRd["成立"]].sort_values(["淨", "t_in"]); B_ = TRd[~TRd["成立"]].sort_values(["淨", "t_in"])
    q = lambda g, f: g.index[min(int(f * (len(g) - 1) + 0.5), len(g) - 1)] if len(g) else None
    EX = [("中午確認、收盤真的成立（中位偏上）", q(A_, 0.67), len(A_)), ("中午確認、收盤真的成立（中位偏下）", q(A_, 0.33), len(A_)),
          ("中午確認、收盤掉回去沒成立（中位偏上）", q(B_, 0.67), len(B_)), ("中午確認、收盤掉回去沒成立（中位偏下）", q(B_, 0.33), len(B_))]
    uni = D.load_universe().set_index("stock_id")["name"]
    dt = lambda t: str(cal[int(t)].date()) if int(t) < len(cal) else "資料尾"
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}.ref td{color:#666}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量 盤中確認才買</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量 v1：前一天備好名單、盤中確認過了才買</h1>",
         "<p class='lead'>使用者原話：" + "<br>".join(f"「{html.escape(x)}」" for x in RAWS) + f"<br>⛔ 描述臂：不計 N、不改任何判定。⚠ 先驗提醒：{html.escape(PRIOR)}。</p>",
         "<p class='note'>名單：前一天收盤後，營收已成立、5 取 3 已有 2 條（或 1 條、另外差的兩條含量）。<br>"
         "<b>A 開盤確認</b>：開盤價已經 ≥ 差的那條所需價格才用開盤價買（沒有前視；量開盤看不到，不收）。<br>"
         f"<b>B 中午確認</b>：中午價 ≥ 所需價格、或中午累計量已 ≥ 3 倍 ⇒ 用中午價買。⚠ {TAG_B}；⚠ {TAG_V}。<br>"
         "都抱 61 天、名額 20、挑法照營量 v1、扣成本。「收盤真的成立」＝ 當天收盤 5 取 3 真的 ≥ 3 條。</p>"]
    H.append("<h2>對照表</h2><div class='wrap'><table><tr><th class='l'>臂</th><th>每年買進</th><th>收盤真的成立</th><th>探索</th><th>確認</th><th>標籤</th><th>早年</th><th>標籤</th><th>確認：對原版〔95% CI〕</th></tr>")
    lab = {"A_開盤確認": "A 開盤確認", "B_中午確認": "B 中午確認（均價、量×0.5）", "B_量0.4": "B 敏感度：量×0.4", "B_量0.6": "B 敏感度：量×0.6",
           "B_開收平均": "B 敏感度：(開＋收)÷2", "B0_只看價": "B0 只看價（不收量）"}
    for r in TB.to_dict("records"):
        c_ = "pick" if r["臂"] in ("A_開盤確認", "B_中午確認") else ""
        H.append(f"<tr class='{c_}'><td class='l'>{lab[r['臂']]}</td><td>{r['主_觸發每年']:.0f}</td><td>{r['主_T收盤成立']:.0%}</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td>"
                 f"<td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td><td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td>"
                 f"<td>{P(r['確認_差'])}〔{P(r['確認_差lo'])}, {P(r['確認_差hi'])}〕</td></tr>")
    for nm, lb in (("原版", "原版（營量 v1）"), ("可執行_x5", "上一版：前一天決定、不確認 x5"), ("完美預知", "完美預知（含前視、不可執行）")):
        g = OLD.loc[nm]
        dd = "—" if nm == "原版" else f"{P(g['確認_差'])}〔{P(g['確認_差lo'])}, {P(g['確認_差hi'])}〕"
        H.append(f"<tr class='ref'><td class='l'>{lb}</td><td>—</td><td>—</td><td>{P(g['探索_年化'])}／{P(g['探索_回落'])}</td><td>{P(g['確認_年化'])}／{P(g['確認_回落'])}</td>"
                 f"<td>{g['確認_標籤']}</td><td>{P(g['早年_年化'])}／{P(g['早年_回落'])}</td><td>{g['早年_標籤']}</td><td>{dd}</td></tr>")
    H.append("</table></div>")
    H.append(f"<p class='note'>年化／最大回落。每年買進、收盤真的成立 ＝ 主窗 2017–2026 名單觸發（訊號層、去重後）。0050 確認 {P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}、早年 {P(Z['早年']['cagr'])}。</p>")
    H.append("<h2>B 中午確認：確認段的例子（組合實際成交）</h2>" + CS.legend_html())
    for cat, i, n_ in EX:
        if i is None:
            H.append(f"<p class='note'>{cat}：沒有例子。</p>"); continue
        r = TRd.loc[i]; s = r["sid"]; inf_ = r["info"]; T = int(r["t_in"]); t_out = min(int(r["t_out"]), len(cal) - 1)
        df = D.load_stock(s, Wm["mk"].get(s, "twse"), cal).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        i0 = max(0, T - 40); i1 = min(len(cal) - 1, t_out + 8); sl = slice(i0, i1 + 1)
        pz = [z for z in PX if np.isfinite(inf_[f"thr_{z}"]) and inf_["vw_T"] >= inf_[f"thr_{z}"] - 1e-9]
        hl = [{"px": float(inf_[f"thr_{z}"]), "label": f"{YE.CNAME[z]} 門檻 {inf_[f'thr_{z}']:.2f}", "color": "#e65100"} for z in (pz or ([inf_["最容易"]] if inf_["最容易"] else []))]
        marks = [{"i": T - i0, "px": float(inf_["vw_T"]), "kind": "entry", "label": f"中午買 {inf_['vw_T']:.2f}"},
                 {"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"出 {cf[t_out]:.2f}"}]
        how = inf_[f"路徑_{NM}"]; vr = inf_["額_T"] * 0.5 / inf_["均額20"]
        ts = "真的成立" if inf_["T成立"] else "沒成立（T 分數 " + str(inf_["T分數"]) + "）"
        pzs = "、".join(YE.CNAME[z] for z in pz) or "無"
        sub = f"前一天 {inf_['score_j']} 分、差 {inf_['未達']}｜中午確認：{how}（中午價過門檻：{pzs}；中午量≈20 日均額 {vr:.1f} 倍）｜收盤{ts}｜這筆 {P(r['淨'])}"
        ma = {kk: CS.moving_avg(cf, kk)[sl] for kk in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(T - i0, t_out - i0), title=cat, show_title=False, hlines=hl)
        H.append(f"<details class='card' open><summary><b>{html.escape(cat)}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜中午買 {dt(T)}</summary>"
                 f"<div class='meta'>這一類在確認段 {n_} 筆｜{html.escape(sub)}</div>{svg}</details>")
    H.append(f"<p class='note'>⚠ {TAG_B}；⚠ {TAG_V}；價格為還原價。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    S["例子"] = [{"類": cat, "sid": (TRd.at[i, "sid"] if i is not None else None), "T": (dt(TRd.at[i, "t_in"]) if i is not None else None),
                "淨": (float(TRd.at[i, "淨"]) if i is not None else None), "類筆數": n_} for cat, i, n_ in EX]
    S["例子查核：組合進場價 ＝ 中午價（最大相對差）"] = float(max([abs(float(r.px_in) / float(r.info["vw_T"]) - 1) for r in TRd.itertuples()] + [0.0]))
    NL = chr(10)
    L = ["# 營量 提早一天：盤中確認才買（描述臂）" + NL, "使用者原話（逐字）：" + NL] + [f"- 「{x}」" for x in RAWS] + [
        NL + f"> ⛔ 描述臂：不計 N、不改任何判定。⚠ 先驗提醒：{PRIOR}。⚠ B 臂：{TAG_B}；{TAG_V}。本線讀法 S1～S5 見程式開頭（S1：「差兩條其中一條是 c3」讀成 T−1 分數 1）。" + NL,
        "| 臂 | 主 每年買進 | 主 收盤真的成立 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 探索 對原版〔CI〕 | 確認 對原版〔CI〕 | 早年 對原版〔CI〕 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        L.append(f"| {r['臂']} | {r['主_觸發每年']:.0f} | {r['主_T收盤成立']:.1%} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | "
                 f"{P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {P(r['探索_差'])}〔{P(r['探索_差lo'])}, {P(r['探索_差hi'])}〕 | {P(r['確認_差'])}〔{P(r['確認_差lo'])}, {P(r['確認_差hi'])}〕 | {P(r['早年_差'])}〔{P(r['早年_差lo'])}, {P(r['早年_差hi'])}〕 |")
    for nm in ("原版", "可執行_x5", "完美預知"):
        g = OLD.loc[nm]
        dd = lambda sg: "—" if nm == "原版" else f"{P(g[sg + '_差'])}〔{P(g[sg + '_差lo'])}, {P(g[sg + '_差hi'])}〕"
        L.append(f"| 並列：{nm}（resultsYLearly） | — | — | {P(g['探索_年化'])}／{P(g['探索_回落'])} | {P(g['確認_年化'])}／{P(g['確認_回落'])} | {g['確認_標籤']} | {P(g['早年_年化'])}／{P(g['早年_回落'])} | {g['早年_標籤']} | {dd('探索')} | {dd('確認')} | {dd('早年')} |")
    L.append(NL + "## 另報（訊號層＝去重後每筆各抱 61 天、扣成本；組合＝種子 0 實際成交）" + NL)
    L.append("| 臂 | 世界 | 觸發筆數 | 收盤成立 | 過價後收盤掉回去 | 成立那批淨 | 沒成立那批淨 | 觸發路徑 | 組合成交 | 組合成立比例 | 組合平均淨 |"); L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in TB.to_dict("records"):
        for wk in ("主", "早年"):
            L.append(f"| {r['臂']} | {wk} | {r[wk + '_觸發筆數']} | {r[wk + '_T收盤成立']:.1%} | {1 - r[wk + '_T收盤成立']:.1%} | {P(r[wk + '_成立那批淨'])} | {P(r[wk + '_沒成立那批淨'])} | "
                     f"{r[wk + '_路徑']} | {r[wk + '_組合成交']} | {r[wk + '_組合成立比例']:.1%} | {P(r[wk + '_組合平均淨'])} |")
    L.append(NL + f"閘：{S['閘']}｜資料：{S['資料']}｜例子：{S['例子']}｜例子查核：{S['例子查核：組合進場價 ＝ 中午價（最大相對差）']}｜網頁：{F_HTML}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(L) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda z: z.item() if hasattr(z, "item") else str(z))
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜閘 {S['閘']}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

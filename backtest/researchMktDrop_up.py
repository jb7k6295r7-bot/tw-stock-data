# -*- coding: utf-8 -*-
"""大盤大跌日「逆勢上漲」的股票（描述性初測、⛔ 不計 N、⛔ 不判定）——回測線計算子代理，2026-10-15。
使用者問：「逆勢漲的呢？」＝ 大跌日當天收盤逆勢上漲的股票。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（v1／初測程式只 import 重用）；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_up [--procs 4]

═══ 讀法（執行者補的都在這裡；寫死於第一次跑之前）═══
 U0 全部重用 researchMktDrop_v1（PREREG大盤大跌後買什麼 seq1）：事件 ＝ q2（擴張視窗最低 2%、2005-01-03 起算、去重 20 列）＋「同時只處理一個事件」鎖 ⇒ 同 28 個接受事件；
    世界、母體 R1（patterns.Frame.gate ∧ pit_valid ∧ 四碼普通股 ∧ 含已下市 ∧ 前 20 根無壞根；GATE_V2；缺口 ≥ 5 日即壞根；早年 reduce_v2＋R8）、
    主出場（加權收盤 ≥ 事件前一日收盤 ⇒ 隔天開盤賣；⛔ 不設天數）、成本（個股 0.585%、ETF 0.385%）、配對 0050（扣 ETF 成本）、
    ①（只在事件進場、平時現金）、②（平時 0050、事件換 20%）、隨機日 200 次（同年、非原始事件日、同主出場、同候選）、段、window_stats 口徑 —— 全部 import v1／初測函式，
    逐股快取讀 v1 的 ~/mktdropwork/v1/packs_*.pkl（只讀）
 U1 新候選（t 收盤決定、t＋1 開盤買、等權；母體 ＝ 與 C／D 同一個 R1 母體 ∧ 當天報酬有值；母體 ＜ 20 檔不排，同 C／D）：
    G1 當天報酬 ＞ 0（逆勢上漲，全部）；G2 當天報酬 ≥ +3%；G3 當天收盤漲停
    當天報酬 ＝ 還原收盤[k] ÷ 收盤[k−1] − 1（同 C／D）
    漲停 ＝ 既有判定 research11.limit_flags（未還原收盤 ＝ 漲停價；2015-06-01 前 7%、之後 10%；還原事件根與上市前 5 根不判）
    候選 ＜ 5 檔 ⇒ 標「候選不足」、照實報（1～4 檔照買照算；0 檔 ⇒ 該事件不進場）——同 v1 對 F 的處理
    買不到（隔天沒成交、開盤漲停鎖死、隔天是壞根）⇒ 剔除、比例照報（漲停股隔天常開盤鎖死 ⇒ G3 買不到比例另報）
 U2 並列 A（0050）、C（跌最多一成）、D（最抗跌一成）：同程式重算，並與 v1 main_table.csv 對帳（不一致 ⇒ 停）
 U3 只做 q2 × 主出場；隨機日種子 ＝ v1 同式 default_rng([v1.RSEED, 段號, 候選號, i])，A／C／D 用 v1 候選號（⇒ 可逐位元對帳），G1／G2／G3 用 6／7／8
 U4 實作：v1.day_stats 只 import 呼叫，執行期把 v1 模組的 CANDS／basket 換成本件清單（記憶體內、⛔ 不改 v1 檔）
輸出 backtest/resultsMktDrop/up/：MktDrop_up.json、main_table.csv、counts.csv、event_rows.csv、portfolio.csv、random.csv.gz、run.log；大檔 ~/mktdropwork/up/
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/up")
WORK = os.path.expanduser("~/mktdropwork/up")
V1WORK = os.path.expanduser("~/mktdropwork/v1")
V1MAIN = os.path.join(REPO, "backtest/resultsMktDrop/v1/main_table.csv")
TIME = "2026-10-15（台北；讀法寫死、第一次跑之前）"
CANDS_UP = ["A", "C", "D", "G1", "G2", "G3"]
CN_UP = {"A": "0050", "C": "當天跌最多一成（v1）", "D": "當天最抗跌一成（v1）",
         "G1": "當天收盤上漲（＞0）全部", "G2": "當天漲幅 ≥ +3%", "G3": "當天收盤漲停"}
RIDX = {"A": 0, "C": 2, "D": 3, "G1": 6, "G2": 7, "G3": 8}       # 隨機日種子的候選號（A／C／D ＝ v1 CANDS.index）
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "事件約每年 1 次，樣本很少（同 v1 的 28 個接受事件）",
         "收復才賣的勝率有一部分來自規則本身（等多久都等）",
         "候選 ＜ 5 檔標候選不足（1～4 檔照買照算；0 檔不進場）",
         "漲停股隔天常開盤鎖死買不到 ⇒ 實際買到的是「隔天沒鎖死」的那一部分（有選擇偏差），買不到比例照報",
         "早年（2006～2014）含減資假飆股約 0.3%（剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；2005-01～2007-06 只有上市",
         "成本：個股 0.585% 來回、ETF 0.385%；未含滑價"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def up_job(a):
    wn, sid = a
    from backtest import data as D
    from backtest import research11 as R
    W = _G[wn]; D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"])
    if B is None:
        return sid, None, None
    return sid, B["idx"].astype(np.int64), np.asarray(B["up"], bool)


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    from multiprocessing import Pool
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop as MD
    MD.SEGS = V1.SEGS_V1
    orig_basket = V1.basket

    def basket_up(M, t, cd):
        if cd in ("A", "C", "D"):
            return orig_basket(M, t, cd)
        m = M["MEM"][:, t] & np.isfinite(M["RET"][:, t])
        rows = np.flatnonzero(m)
        if len(rows) < 20:
            return np.array([], int), 0, None
        v = M["RET"][rows, t]
        if cd == "G1":
            sel = rows[v > 0]
        elif cd == "G2":
            sel = rows[v >= 0.03]
        else:
            sel = rows[M["UP"][rows, t]]
        return sel[M["BUY"][sel, t]], len(sel), None
    V1.CANDS = CANDS_UP; V1.basket = basket_up          # 只在記憶體內換（⛔ 不改 v1 檔）

    S = {"件": "大盤大跌日逆勢上漲（描述性初測、不計 N、不判定）", "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭 U0～U4",
         "必附": NOTES, "候選": CN_UP, "重用": "researchMktDrop_v1（PREREG大盤大跌後買什麼 seq1）", "閘": {}}
    IXmd = MD.load_index(log)
    sha = IXmd["sha"]; df = IXmd["df"]
    EV = V1.index_events(df)
    ft = np.flatnonzero(EV["FIRST"]["q2"])
    if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
        raise SystemExit("⛔ q2 收復列與初測 rec 不同")
    S["指數"] = {"origin/main sha": sha, "期間": f"{df['date'].iloc[0].date()}～{df['date'].iloc[-1].date()}",
                 "q2 接受事件（全部）": int(EV["ACC"]["q2"].sum())}
    ROWS = []; CELLS = []; PORT = []; RND = []; CNT = []
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W; _G[wn] = W
        cp = os.path.join(V1WORK, f"packs_{wn}.pkl")
        PK = pickle.load(open(cp, "rb")); log(f"[逐股 {wn}] 讀 v1 快取 {cp}")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        # 漲停矩陣
        up_p = os.path.join(WORK, f"up_{wn}.pkl")
        if os.path.exists(up_p):
            UPD = pickle.load(open(up_p, "rb")); log(f"[漲停 {wn}] 讀快取 {up_p}")
        else:
            t0 = time.time(); UPD = {}
            with Pool(a.procs) as pool:
                for j, (s, idx, up) in enumerate(pool.imap_unordered(up_job, [(wn, s) for s in M["sids"]], chunksize=8)):
                    if idx is not None:
                        UPD[s] = (idx, up)
                    if j % 500 == 0:
                        log(f"[漲停 {wn}] {j}/{len(M['sids'])}｜{time.time() - t0:.0f}s")
            pickle.dump(UPD, open(up_p, "wb"), protocol=5)
        n0 = W["n0"]; UP = np.zeros((M["S"], n0), bool); idx_bad = []
        for r, s in enumerate(M["sids"]):
            if s not in UPD:
                idx_bad.append(s); continue
            idx, up = UPD[s]
            if not np.array_equal(idx, PK[s]["idx"]):
                idx_bad.append(s); continue
            UP[r, idx] = up
        M["UP"] = UP
        S["閘"][wn] = {"漲停 idx 與快取不同或缺": idx_bad[:20], "檔數": len(idx_bad), "漲停股日": int(UP.sum()),
                      "母體內漲停股日": int((UP & M["MEM"]).sum())}
        if idx_bad:
            raise SystemExit(f"⛔ {wn} 漲停 idx 對不上：{idx_bad[:10]}")
        log(f"[漲停 {wn}] {S['閘'][wn]}")
        DAY, MEMB = V1.day_stats(W, M, log)
        cal = W["cal"]; BO, BC = W["BO"], W["BC"]
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        hold0050 = BC / BC[0]
        rawpos = {datepos[d] for d in df["date"][EV["RAW"]["q2"]] if d in datepos}
        evs = []
        for i in np.flatnonzero(EV["ACC"]["q2"]):
            p = datepos.get(df["date"].iloc[i])
            if p is not None and p + 1 < n0 and segof(p) is not None:
                evs.append((p, i))
        x = "主"
        for cd in CANDS_UP:
            cost = V1.COST_ETF if cd == "A" else V1.COST_STK
            Dx = DAY[cd]; Dd = Dx[x]; paths = {}
            for p, i in evs:
                m_ = M["MEM"][:, p] & np.isfinite(M["RET"][:, p])
                base = {"世界": wn, "段": segof(p), "候選": cd, "日期": str(cal[p].date()), "指數報酬": float(EV["r"][i]),
                        "母體檔數": int(m_.sum()), "母體上漲比例": float(np.mean(M["RET"][m_, p] > 0)) if m_.any() else np.nan,
                        "選出檔數": int(Dx["nsel"][p]), "買到檔數": int(Dx["n"][p]),
                        "候選不足（＜5）": bool(cd != "A" and Dx["nsel"][p] < 5)}
                if Dx["n"][p] == 0:
                    ROWS.append({**base, "進場": False}); continue
                e_, end_, V, ro = V1.bpath(W, M, MEMB[(cd, p)], p, x)
                paths[p] = (e_, end_, V, ro)
                Vpk = np.maximum.accumulate(np.r_[1.0, V])
                ROWS.append({**base, "進場": True, "報酬": float(Dd["net"][p]), "配對0050": float(Dd["b50"][p]),
                             "配對差": float(Dd["net"][p] - Dd["b50"][p]), "平均持有天數": float(Dd["hold"][p]),
                             "持有中最大回落": float(np.min(np.r_[1.0, V] / Vpk - 1)), "窗尾未出場比例": float(Dd["unex"][p]),
                             "賣完日": str(cal[end_].date())})
            for sg, (x0, y0) in W["segp"].items():
                es = [(p, i) for p, i in evs if x0 <= p <= y0]
                ec = [p for p, _ in es if Dx["n"][p] > 0]
                ns_all = np.array([Dx["nsel"][p] for p, _ in es]); nb_all = np.array([Dx["n"][p] for p, _ in es])
                CNT.append({"段": sg, "候選": cd, "事件數": len(es), "選出檔數_最少": int(ns_all.min()) if len(es) else None,
                            "選出檔數_中位": float(np.median(ns_all)) if len(es) else None, "選出檔數_平均": float(ns_all.mean()) if len(es) else None,
                            "選出檔數_最多": int(ns_all.max()) if len(es) else None,
                            "候選不足事件數（＜5，含 0）": int((ns_all < 5).sum()) if cd != "A" else 0, "0 檔事件數": int((ns_all == 0).sum()),
                            "買到檔數_平均": float(nb_all.mean()) if len(es) else None,
                            "買不到比例": float(1 - nb_all.sum() / ns_all.sum()) if ns_all.sum() else np.nan,
                            "逐事件選出檔數": " ".join(str(int(v)) for v in ns_all)})
                row = {"世界": wn, "段": sg, "候選": cd, "指數事件數（接受、段內）": len(es), "進場事件數": len(ec),
                       "候選不足事件數（＜5，含 0）": int((ns_all < 5).sum()) if cd != "A" else 0}
                if ec:
                    vals = np.array([Dd["net"][p] for p in ec]); b50 = np.array([Dd["b50"][p] for p in ec]); dif = vals - b50
                    ne, rho, prs = V1.eff_n(vals, [(paths[p][0], paths[p][1]) for p in ec])
                    row.update({"等效獨立事件數": ne, "平均報酬": float(vals.mean()), "中位報酬": float(np.median(vals)), "勝率": float(np.mean(vals > 0)),
                                "同期0050平均（配對、含成本）": float(b50.mean()), "配對差平均": float(dif.mean()), "配對差中位": float(np.median(dif)),
                                "X較好比例": float(np.mean(dif > 0)), "平均持有天數": float(np.mean([Dd["hold"][p] for p in ec])),
                                "平均籃子檔數": float(np.mean([Dx["n"][p] for p in ec]))})
                    yrs = pd.Series([cal[p].year for p in ec]).value_counts().to_dict()
                    pool_ = {y_: np.array([t for t in range(x0, min(y0, n0 - 2) + 1) if cal[t].year == y_ and t not in rawpos and Dx["n"][t] > 0], int) for y_ in yrs}
                    rm = []
                    for rep in range(V1.NRAND):
                        rng = np.random.default_rng([V1.RSEED, list(V1.SEGS_V1[wn]).index(sg) + (0 if wn == "早年" else 1), RIDX[cd], rep])
                        dl = [rng.choice(pool_[y_], size=min(c_, len(pool_[y_])), replace=False) for y_, c_ in sorted(yrs.items()) if len(pool_[y_])]
                        dr = np.concatenate(dl) if dl else np.array([], int)
                        rm.append(float(np.mean(Dd["net"][dr])) if len(dr) else np.nan)
                        RND.append({"段": sg, "候選": cd, "i": rep, "隨機平均": rm[-1]})
                    rm = np.array(rm)
                    row.update({"隨機平均": float(np.nanmean(rm)), "實際減隨機": float(vals.mean() - np.nanmean(rm)),
                                "p（隨機 ≥ 實際）": float(np.nanmean(rm >= vals.mean()))})
                CELLS.append(row)
            pl = [paths[p] for p in sorted(paths)]
            eq1, inm = V1.curve1(n0, pl, cost)
            if cd == "A":
                eq2, skp = hold0050.copy(), 0
            else:
                eq2, skp = V1.curve2(n0, pl, BO, BC, cost)
            for sg, (x0, y0) in W["segp"].items():
                h = V1.wstats(hold0050, x0, y0); s1 = V1.wstats(eq1, x0, y0); s2 = V1.wstats(eq2, x0, y0)
                PORT.append({"世界": wn, "段": sg, "候選": cd, "①只在事件進場_年化": s1["年化"], "①最大回落": s1["最大回落"], "①比值": s1["比值"],
                             "①在場日比例": float(inm[x0:y0 + 1].mean()), "②平時0050換20%_年化": s2["年化"], "②最大回落": s2["最大回落"], "②比值": s2["比值"],
                             "②略過重疊事件": skp, "一直抱0050_年化": h["年化"], "一直抱0050_最大回落": h["最大回落"], "一直抱0050_比值": h["比值"],
                             "②年化減0050": s2["年化"] - h["年化"], "②比值減0050": s2["比值"] - h["比值"]})
        log(f"[{wn}] 完｜{time.time() - T0:.0f}s")
        del M, DAY, MEMB, PK, UPD
    ER = pd.DataFrame(ROWS); CE = pd.DataFrame(CELLS); PO = pd.DataFrame(PORT); CT = pd.DataFrame(CNT)
    m = CE.merge(PO, on=["世界", "段", "候選"], how="left")
    m["_s"] = m["段"].map({"2006～2014": 0, "2015～2021": 1, "2022～": 2}); m["_c"] = m["候選"].map(CANDS_UP.index)
    m = m.sort_values(["_c", "_s"]).drop(columns=["_s", "_c"])
    # 對帳 v1（A／C／D）
    V1M = pd.read_csv(V1MAIN)
    chk = {}; worst = 0.0
    cols = ["平均報酬", "中位報酬", "勝率", "配對差平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落", "②平時0050換20%_年化", "②最大回落"]
    for cd in ("A", "C", "D"):
        for sg in ("2006～2014", "2015～2021", "2022～"):
            a_ = m[(m["候選"] == cd) & (m["段"] == sg)].iloc[0]; b_ = V1M[(V1M["候選"] == cd) & (V1M["段"] == sg)].iloc[0]
            d_ = {c: float(abs(a_[c] - b_[c])) for c in cols}
            worst = max(worst, max(d_.values())); chk[f"{cd} {sg}"] = max(d_.values())
    S["對帳 v1 main_table（A／C／D，最大絕對差；v1 csv 6 位有效數字）"] = {"逐格": chk, "最大": worst}
    log(f"[對帳 v1] 最大絕對差 {worst:.2e}")
    if worst > 5e-6:
        raise SystemExit(f"⛔ A／C／D 與 v1 對不上（{worst}）")
    keep = ["段", "候選", "指數事件數（接受、段內）", "進場事件數", "候選不足事件數（＜5，含 0）", "平均籃子檔數", "等效獨立事件數",
            "平均報酬", "中位報酬", "勝率", "同期0050平均（配對、含成本）", "配對差平均", "配對差中位", "X較好比例", "平均持有天數",
            "隨機平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落", "①比值", "①在場日比例",
            "②平時0050換20%_年化", "②最大回落", "②比值", "一直抱0050_年化", "一直抱0050_最大回落", "一直抱0050_比值", "②年化減0050", "②比值減0050"]
    MT = m[[c for c in keep if c in m.columns]]
    MT.to_csv(os.path.join(OUT, "main_table.csv"), index=False, float_format="%.6g", encoding="utf-8")
    CT.to_csv(os.path.join(OUT, "counts.csv"), index=False, float_format="%.6g", encoding="utf-8")
    ER.to_csv(os.path.join(OUT, "event_rows.csv"), index=False, float_format="%.10g", encoding="utf-8")
    PO.to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8")
    pd.DataFrame(RND).to_csv(os.path.join(OUT, "random.csv.gz"), index=False, float_format="%.6g")
    S["主表"] = MT.to_dict("records"); S["候選檔數分布"] = CT.to_dict("records")
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_up.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 250)
    log("[主表]\n" + MT[["段", "候選", "進場事件數", "候選不足事件數（＜5，含 0）", "平均籃子檔數", "平均報酬", "中位報酬", "勝率", "配對差平均",
                        "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落", "②平時0050換20%_年化", "②最大回落", "一直抱0050_年化", "一直抱0050_最大回落"]].to_string())
    log("[檔數分布]\n" + CT.to_string())
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    sys.path.insert(0, REPO)
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

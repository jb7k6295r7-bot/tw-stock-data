# -*- coding: utf-8 -*-
"""大盤大跌日加碼營量／營飆持股時「再配合營收條件」——描述性初測（⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）——回測線計算子代理，2026-10-16。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（researchMktDrop_yl／v1／初測／researchExit5 只 import 重用；引擎與逐股快取只讀）；用語「假訊號」。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_ylrev

═══ 讀法（寫死於第一次跑之前，2026-10-16 台北）═══
 R0 全部沿用 researchMktDrop_yl 的 Y0～Y4：同 28 個接受事件、同世界／母體、同主出場（收復即賣）、同成本、同配對 0050、同 ①、同隨機日 200 次、
    同營量 v1 r0／營飆 v1 200 顆持股（讀 ~/mktdropwork/yl/engine.pkl，只讀）、同營收矩陣（researchExit5.load_revenue／avail_pos／rev_events：
    ≤2025-12 期次月 10 日後、≥2026-01 期 15 日後第一個交易日；可得日 ≤ 事件日 t 的最後一期；⛔ 不設資料過舊上限）、同 impact 口徑（80% 原策略＋20% 閒錢、不再平衡）
    yl 模組只 import 用 hold_matrix／orig_curve／常數；yl.run 內的巢狀函式無法 import ⇒ 本檔照抄（邏輯不改），並以「H1～H3 重算 ＝ yl 輸出」對帳把關
 R1 新候選（持股過濾在「持有中、在世界」之後、買不到之前；候選檔數 ＝ 過濾後）：
    Hkr ＝ Hk 持股中「事件日當時最新一期月營收年增 ＞ 0」；Hkn ＝ 年增 ≤ 0（對照；年增缺 ⇒ 兩邊都不入選）；Hkh ＝ 最新一期創 24 月新高（不可判 ⇒ 不入選）
    k ＝ 1（營量 r0）、2（營飆第 r 顆，報 200 顆中位＋r0）、3（聯集）
    隨機日種子 ＝ v1 同式 default_rng([v1.RSEED, 段號, 候選號, i])；候選號 H1 11、H2 12、H3 13（同 yl）、H1r 14、H1n 15、H1h 16、H2r 17、H2n 18、H2h 19、H3r 20、H3n 21、H3h 22
 R2 不足：候選檔數 ＜ 3（含 0）標不足、照買照算；0 檔 ⇒ 不進場
 R3 持股營收占比：每事件 Hk 持股（在世界、買不到之前）中 年增 ＞0／≤0／缺、創 24 月新高 的占比；段內 ＝ 逐事件占比平均、另報合併占比（總檔次加總）
    H2／H3 ＝ 200 顆各自算再取中位
 R4 impact：同 yl Y4；加碼部位換成過濾後籃子，原策略不變（Hkr／Hkn／Hkh 的原策略 ＝ Hk 的原策略）
 R5 必附：見 NOTES
輸出 backtest/resultsMktDrop/ylrev/：MktDrop_ylrev.json、main_table.csv、impact.csv、holdshare.csv、event_rows.csv.gz、seeds.csv.gz、run.log
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
sys.path.insert(0, REPO)
from backtest import researchMktDrop_yl as YL  # noqa: E402

OUT = os.path.join(REPO, "backtest/resultsMktDrop/ylrev")
YLOUT = YL.OUT
TIME = "2026-10-16（台北；讀法寫死、第一次跑之前）"
NSEED = YL.NSEED
W_ADD = YL.W_ADD
MIN_N = 3
CANDS_S = ["A", "H1", "H1r", "H1n", "H1h"]
CANDS_R = ["H2", "H2r", "H2n", "H2h", "H3", "H3r", "H3n", "H3h"]
SUF = {"": "持有中全部", "r": "只加碼年增＞0", "n": "只加碼年增≤0（對照）", "h": "只加碼創24月新高"}
BASEN = {"H1": "營量 v1", "H2": "營飆 v1", "H3": "營量＋營飆聯集"}
CN = {"A": "0050"}
for _b in ("H1", "H2", "H3"):
    for _s in ("", "r", "n", "h"):
        CN[_b + _s] = f"{BASEN[_b]}・{SUF[_s]}"
RIDX = {"A": 0, "H1": 11, "H2": 12, "H3": 13, "H1r": 14, "H1n": 15, "H1h": 16, "H2r": 17, "H2n": 18, "H2h": 19, "H3r": 20, "H3n": 21, "H3h": 22}
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "⚠ 年增＞0／≤0／創 24 月新高 這三種過濾是看過 H1～H3 結果與 deep 拆解之後才加的條件 ⇒ 事後重切，任何「看起來較好」都只是待驗線索",
         "事件只有 28 次（早年 10、2015～2021 7、2022～ 11），同事件內檔次高度相關；過濾後每事件檔數更少（＜3 標不足）；收復才賣的勝率有一部分來自規則本身",
         "營量／營飆主世界引擎窗 2017-03-02～2026-08-24 ⇒ 2015-08-24 事件沒有 H 籃子；2026-08-25 之後也沒有；早年引擎窗 2005-02～2014-12",
         "營飆 v1 ＝ 抽籤 200 顆，表上報 200 顆中位（各統計各自取中位，不是同一顆）＋r0",
         "年增缺（新上市、資料缺）⇒ r 與 n 都不入選；創 24 月新高前 24 期不全 ⇒ 不入選",
         "對原策略的影響：加碼資金另撥（段起點 原策略 80%＋閒錢 20%，不再平衡）；與「閒錢不動」比",
         "早年（2006～2014）含減資假飆股約 0.3%（reduce_v2，剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市",
         "成本：個股 0.585% 來回、ETF 0.385%；未含滑價"]
SEGORD = {"2006～2014": 0, "2015～2021": 1, "2022～": 2}


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    ENG = pickle.load(open(YL.ENGPK, "rb"))
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop as MD
    from backtest import researchExit5 as EX5
    MD.SEGS = V1.SEGS_V1
    orig_basket = V1.basket

    def basket_rev(M, t, cd):
        if cd == "A":
            return orig_basket(M, t, cd)
        base, suf = cd[:2], cd[2:]
        sel = np.flatnonzero(M["HOLD_" + base][:, t])
        if suf == "r":
            with np.errstate(invalid="ignore"):
                sel = sel[M["YOY"][sel, t] > 0]
        elif suf == "n":
            with np.errstate(invalid="ignore"):
                sel = sel[M["YOY"][sel, t] <= 0]
        elif suf == "h":
            sel = sel[M["HI24"][sel, t]]
        return sel[M["BUY"][sel, t]], len(sel), None
    V1.basket = basket_rev; V1.EXITS = ["主"]          # 只在記憶體內換（⛔ 不改 v1 檔）

    S = {"件": "大盤大跌日加碼營量／營飆持股，配合營收條件（年增＞0／≤0／創 24 月新高）——描述性初測、不計 N、不判定", "讀法寫死": TIME, "開跑（台北）": YL.now_tpe(),
         "讀法": "見程式檔頭 R0～R5", "必附": NOTES, "候選": CN, "重用": "researchMktDrop_yl（引擎快取、hold_matrix、orig_curve）、researchMktDrop_v1、researchExit5",
         "閘": {"引擎": ENG["閘"]}}
    IXmd = MD.load_index(log)
    df = IXmd["df"]
    EV = V1.index_events(df)
    rev_e, rly_e, info_e = EX5.load_revenue(MD.DB.WORLDS["早年"]["data"])
    rev_m, rly_m, info_m = EX5.load_revenue(MD.DB.WORLDS["主"]["data"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    S["營收"] = {"早年": info_e, "主": info_m}
    DEEP = pd.read_csv(YL.DEEPC, dtype={"sid": str})
    ROWS = []; SEGR = []; IMP = []; SEEDR = []; SHR = []
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W
        PK = pickle.load(open(os.path.join(YL.V1WORK, f"packs_{wn}.pkl"), "rb")); log(f"[逐股 {wn}] 讀 v1 快取")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        cal = W["cal"]; n0 = W["n0"]; BC = W["BC"]
        rix = {s: r for r, s in enumerate(M["sids"])}
        AV = EX5.avail_pos(list(rev.index), cal)
        YOY = np.full((M["S"], n0), np.nan); HI24 = np.zeros((M["S"], n0), bool); ar = np.arange(n0)
        for r, s in enumerate(M["sids"]):
            ev = EX5.rev_events(s, rev, rly, AV, n0)
            if not ev:
                continue
            rA = np.array([e[0] for e in ev], np.int64)
            j = np.searchsorted(rA, ar, "right") - 1; ok = j >= 0; jj = np.maximum(j, 0)
            yv = np.array([e[1] for e in ev], float); hv = np.array([bool(e[2]) if e[2] is not None else False for e in ev])
            YOY[r, ok] = yv[jj[ok]]; HI24[r, ok] = hv[jj[ok]]
        M["YOY"] = YOY; M["HI24"] = HI24
        E = ENG[wn]; cal_e = E["cal"]; w0e, w1e = E["w0"], E["w1"]
        HY, missY = YL.hold_matrix([E["YL"][0][3]], cal_e, w1e, cal, rix, n0)
        M["HOLD_H1"] = HY
        S["閘"].setdefault(wn, {})["引擎窗"] = f"{cal_e[w0e].date()}～{cal_e[w1e].date()}"
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        rawpos = {datepos[d] for d in df["date"][EV["RAW"]["q2"]] if d in datepos}
        evs = []
        for i in np.flatnonzero(EV["ACC"]["q2"]):
            p = datepos.get(df["date"].iloc[i])
            if p is not None and p + 1 < n0 and segof(p) is not None:
                evs.append((p, i))
        # deep 閘（同 yl）
        dchk = 0; dn = 0
        for p, i in evs:
            dd = DEEP[DEEP["事件日"] == str(cal[p].date())]
            for s, yv, hv in zip(dd["sid"], dd["yoy"], dd["hi24"]):
                r = rix[s]; dn += 1; my = YOY[r, p]
                if np.isfinite(yv) != np.isfinite(my) or (np.isfinite(yv) and abs(my - yv) > 1e-5 * max(1, abs(yv))):
                    dchk += 1
                if (hv == 1.0) != bool(HI24[r, p]):
                    dchk += 1
        S["閘"][wn]["deep C 列年增／新高不同"] = {"列": dn, "不同": dchk}
        log(f"[閘 {wn}] deep 對帳 列 {dn} 不同 {dchk}")
        if dchk:
            raise SystemExit(f"⛔ {wn} 營收與 deep 對不上 {dchk}")
        hold0050 = BC / BC[0]

        def share_rows(base, Hm, tag=None):
            out = []
            for p, i in evs:
                sel = np.flatnonzero(Hm[:, p]); n = len(sel)
                y = YOY[sel, p]
                out.append({"世界": wn, "段": segof(p), "持股": base, "r": tag, "日期": str(cal[p].date()), "持股檔數": n,
                            "年增>0": int(np.sum(y > 0)), "年增<=0": int(np.sum(y <= 0)), "年增缺": int(np.sum(~np.isfinite(y))),
                            "創24月新高": int(HI24[sel, p].sum())})
            return out

        def eval_cd(cd, DAY, MEMB, tag=None):
            cost = V1.COST_ETF if cd == "A" else V1.COST_STK
            Dx = DAY[cd]; Dd = Dx["主"]; paths = {}; rows = []
            for p, i in evs:
                base = {"世界": wn, "段": segof(p), "候選": cd, "r": tag, "日期": str(cal[p].date()), "指數報酬": float(EV["r"][i]),
                        "選出檔數": int(Dx["nsel"][p]), "買到檔數": int(Dx["n"][p]), "不足（＜3）": bool(cd != "A" and Dx["nsel"][p] < MIN_N)}
                if Dx["n"][p] == 0:
                    rows.append({**base, "進場": False}); continue
                e_, end_, V, ro = V1.bpath(W, M, MEMB[(cd, p)], p, "主")
                paths[p] = (e_, end_, V, ro)
                rows.append({**base, "進場": True, "報酬": float(Dd["net"][p]), "配對0050": float(Dd["b50"][p]), "配對差": float(Dd["net"][p] - Dd["b50"][p]),
                             "平均持有天數": float(Dd["hold"][p]), "賣完日": str(cal[end_].date())})
            segs = []
            for sg, (x0, y0) in W["segp"].items():
                es = [(p, i) for p, i in evs if x0 <= p <= y0]
                ec = [p for p, _ in es if Dx["n"][p] > 0]
                ns_all = np.array([Dx["nsel"][p] for p, _ in es])
                row = {"世界": wn, "段": sg, "候選": cd, "r": tag, "指數事件數（接受、段內）": len(es), "進場事件數": len(ec),
                       "不足事件數（＜3，含 0）": int((ns_all < MIN_N).sum()) if cd != "A" else 0,
                       "候選不足事件數（＜5，含 0）": int((ns_all < 5).sum()) if cd != "A" else 0, "0 檔事件數": int((ns_all == 0).sum()),
                       "逐事件候選檔數": " ".join(str(int(v)) for v in ns_all),
                       "候選檔數中位（段內事件）": float(np.median(ns_all)) if len(es) else np.nan,
                       "每進場事件平均檔數（候選）": float(np.mean([Dx["nsel"][p] for p in ec])) if ec else np.nan}
                if ec:
                    vals = np.array([Dd["net"][p] for p in ec]); b50 = np.array([Dd["b50"][p] for p in ec]); dif = vals - b50
                    ne, rho, prs = V1.eff_n(vals, [(paths[p][0], paths[p][1]) for p in ec])
                    nb_ = np.array([Dx["n"][p] for p in ec]); nsl = np.array([Dx["nsel"][p] for p in ec])
                    row.update({"等效獨立事件數": ne, "平均報酬": float(vals.mean()), "中位報酬": float(np.median(vals)), "勝率": float(np.mean(vals > 0)),
                                "同期0050平均（配對、含成本）": float(b50.mean()), "配對差平均": float(dif.mean()), "配對差中位": float(np.median(dif)),
                                "X較好比例": float(np.mean(dif > 0)), "平均持有天數": float(np.mean([Dd["hold"][p] for p in ec])),
                                "平均籃子檔數（買到）": float(nb_.mean()), "買不到比例": float(1 - nb_.sum() / nsl.sum()) if nsl.sum() else np.nan})
                    yrs = pd.Series([cal[p].year for p in ec]).value_counts().to_dict()
                    pool_ = {y_: np.array([t for t in range(x0, min(y0, n0 - 2) + 1) if cal[t].year == y_ and t not in rawpos and Dx["n"][t] > 0], int) for y_ in yrs}
                    rm = []
                    for rep in range(V1.NRAND):
                        rng = np.random.default_rng([V1.RSEED, list(V1.SEGS_V1[wn]).index(sg) + (0 if wn == "早年" else 1), RIDX[cd], rep])
                        dl = [rng.choice(pool_[y_], size=min(c_, len(pool_[y_])), replace=False) for y_, c_ in sorted(yrs.items()) if len(pool_[y_])]
                        dr = np.concatenate(dl) if dl else np.array([], int)
                        rm.append(float(np.mean(Dd["net"][dr])) if len(dr) else np.nan)
                    rm = np.array(rm)
                    row.update({"隨機平均": float(np.nanmean(rm)), "實際減隨機": float(vals.mean() - np.nanmean(rm)), "p（隨機 ≥ 實際）": float(np.nanmean(rm >= vals.mean()))})
                segs.append(row)
            pl = [paths[p] for p in sorted(paths)]
            eq1, inm = V1.curve1(n0, pl, cost)
            for row in segs:
                x0, y0 = W["segp"][row["段"]]
                s1 = V1.wstats(eq1, x0, y0); h = V1.wstats(hold0050, x0, y0)
                row.update({"①只在事件進場_年化": s1["年化"], "①最大回落": s1["最大回落"], "①比值": s1["比值"], "①在場日比例": float(inm[x0:y0 + 1].mean()),
                            "一直抱0050_年化": h["年化"], "一直抱0050_最大回落": h["最大回落"]})
            return rows, segs, eq1

        def impact(cd, eq1, origs, tag=None):
            out = []
            fin = np.all([np.isfinite(o_) for _, o_ in origs], axis=0)
            for sg, (x0, y0) in W["segp"].items():
                ok = np.flatnonzero(fin[x0:y0 + 1])
                if not len(ok):
                    out.append({"世界": wn, "段": sg, "候選": cd, "r": tag, "窗": "引擎窗外"}); continue
                a0, b0 = x0 + int(ok[0]), x0 + int(ok[-1])
                og = sum(w_ * o_ / o_[a0] for w_, o_ in origs)
                sl = eq1 / eq1[a0]
                full = np.full(n0, np.nan); full[a0:b0 + 1] = og[a0:b0 + 1]
                idle = np.full(n0, np.nan); idle[a0:b0 + 1] = (1 - W_ADD) * og[a0:b0 + 1] + W_ADD
                addv = np.full(n0, np.nan); addv[a0:b0 + 1] = (1 - W_ADD) * og[a0:b0 + 1] + W_ADD * sl[a0:b0 + 1]
                slv = np.full(n0, np.nan); slv[a0:b0 + 1] = sl[a0:b0 + 1]
                so = V1.wstats(full, a0, b0); si = V1.wstats(idle, a0, b0); sa = V1.wstats(addv, a0, b0); ss = V1.wstats(slv, a0, b0)
                nev = sum(1 for p, _ in evs if a0 <= p <= b0)
                out.append({"世界": wn, "段": sg, "候選": cd, "r": tag, "窗": f"{cal[a0].date()}～{cal[b0].date()}", "窗內接受事件數": nev,
                            "原策略_年化": so["年化"], "原策略_最大回落": so["最大回落"],
                            "閒錢不動_年化": si["年化"], "閒錢不動_最大回落": si["最大回落"],
                            "大跌加碼_年化": sa["年化"], "大跌加碼_最大回落": sa["最大回落"],
                            "年化差（加碼−不動）": sa["年化"] - si["年化"], "回落差（加碼−不動）": sa["最大回落"] - si["最大回落"],
                            "回落差（加碼−原策略本身）": sa["最大回落"] - so["最大回落"],
                            "加碼部位自身累計損益（窗內）": float(sl[b0] - 1.0), "加碼部位對總資金貢獻": float(W_ADD * (sl[b0] - 1.0)),
                            "加碼部位_年化": ss["年化"], "加碼部位_最大回落": ss["最大回落"]})
            return out

        V1.CANDS = CANDS_S
        DAY, MEMB = V1.day_stats(W, M, log)
        EQ1 = {}
        for cd in CANDS_S:
            rows, segs, eq1 = eval_cd(cd, DAY, MEMB)
            ROWS += rows; SEGR += segs; EQ1[cd] = eq1
        SHR += share_rows("H1", HY)
        oY = YL.orig_curve(E["YL"][0][0], cal_e, w0e, w1e, cal)
        for cd in CANDS_S[1:]:
            IMP += impact(cd, EQ1[cd], [(1.0, oY)])
        V1.CANDS = CANDS_R
        for r in range(NSEED):
            HF, _ = YL.hold_matrix([E["YF"][r][3]], cal_e, w1e, cal, rix, n0)
            M["HOLD_H2"] = HF; M["HOLD_H3"] = HF | HY
            SHR += share_rows("H2", HF, r) + share_rows("H3", HF | HY, r)
            DAYr, MEMBr = V1.day_stats(W, M, (lambda m_: None))
            oF = YL.orig_curve(E["YF"][r][0], cal_e, w0e, w1e, cal)
            for cd in CANDS_R:
                rows, segs, eq1 = eval_cd(cd, DAYr, MEMBr, tag=r)
                ROWS += rows; SEEDR += segs
                IMP += impact(cd, eq1, [(1.0, oF)] if cd.startswith("H2") else [(0.5, oY), (0.5, oF)], tag=r)
            if r % 25 == 0:
                log(f"[{wn} 營飆種子] {r}/{NSEED}｜{time.time() - T0:.0f}s")
        log(f"[{wn}] 完｜{time.time() - T0:.0f}s")
        del M, DAY, MEMB, PK
    ER = pd.DataFrame(ROWS); SG = pd.DataFrame(SEGR); SR = pd.DataFrame(SEEDR); IM = pd.DataFrame(IMP); SH = pd.DataFrame(SHR)
    # 主表：H2*／H3* 200 顆中位＋r0
    num = [c for c in SR.columns if c not in ("世界", "段", "候選", "r", "逐事件候選檔數") and pd.api.types.is_numeric_dtype(SR[c])]
    med = SR.groupby(["世界", "段", "候選"])[num].median().reset_index(); med["r"] = "200 顆中位"
    r0 = SR[SR["r"] == 0].copy(); r0["r"] = "r0"
    ec = ER[ER["候選"].isin(CANDS_R)].groupby(["候選", "日期"])["選出檔數"].median()
    for d_ in (med, r0):
        d_["逐事件候選檔數"] = [" ".join(f"{ec[(c_, dt)]:g}" for dt in sorted(ER[(ER["候選"] == c_) & (ER["段"] == s_)]["日期"].unique()))
                         for c_, s_ in zip(d_["候選"], d_["段"])]
    SG["r"] = SG["r"].fillna("")
    MT = pd.concat([SG, med, r0], ignore_index=True)
    MT["_s"] = MT["段"].map(SEGORD); MT["_c"] = MT["候選"].map(list(CN).index); MT["_r"] = MT["r"].map(lambda x: 1 if x == "r0" else 0)
    MT = MT.sort_values(["_c", "_r", "_s"]).drop(columns=["_s", "_c", "_r"])
    MT.insert(2, "名稱", MT["候選"].map(CN))
    keep = ["段", "候選", "名稱", "r", "指數事件數（接受、段內）", "進場事件數", "不足事件數（＜3，含 0）", "候選不足事件數（＜5，含 0）", "0 檔事件數", "逐事件候選檔數",
            "候選檔數中位（段內事件）", "每進場事件平均檔數（候選）", "平均籃子檔數（買到）", "買不到比例", "等效獨立事件數", "平均報酬", "中位報酬", "勝率",
            "同期0050平均（配對、含成本）", "配對差平均", "配對差中位", "X較好比例", "平均持有天數", "隨機平均", "實際減隨機", "p（隨機 ≥ 實際）",
            "①只在事件進場_年化", "①最大回落", "①比值", "①在場日比例", "一直抱0050_年化", "一直抱0050_最大回落"]
    MT = MT[[c for c in keep if c in MT.columns]]
    # 影響表
    inum = [c for c in IM.columns if c not in ("世界", "段", "候選", "r", "窗") and pd.api.types.is_numeric_dtype(IM[c])]
    i1 = IM[IM["候選"].isin(CANDS_S)].copy(); i1["r"] = "r0（營量）"
    imed = IM[IM["候選"].isin(CANDS_R)].groupby(["世界", "段", "候選", "窗"])[inum].median().reset_index(); imed["r"] = "200 顆中位"
    ir0 = IM[IM["候選"].isin(CANDS_R) & (IM["r"] == 0)].copy(); ir0["r"] = "r0"
    IT = pd.concat([i1, imed, ir0], ignore_index=True)
    IT["_s"] = IT["段"].map(SEGORD); IT["_c"] = IT["候選"].map(list(CN).index)
    IT = IT.sort_values(["_c", "r", "_s"]).drop(columns=["_s", "_c"])
    IT = IT[["段", "候選", "r", "窗"] + [c for c in IT.columns if c not in ("世界", "段", "候選", "r", "窗")]]
    # 對帳 yl（H1／H2／H3，主表與影響表）
    YM = pd.read_csv(os.path.join(YLOUT, "main_table.csv")); YI = pd.read_csv(os.path.join(YLOUT, "impact.csv"))
    cols = ["進場事件數", "平均報酬", "中位報酬", "勝率", "配對差平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落"]
    icol = ["原策略_年化", "閒錢不動_年化", "大跌加碼_年化", "年化差（加碼−不動）", "回落差（加碼−不動）"]
    worst = 0.0; chk = {}
    for cd in ("H1", "H2", "H3"):
        for rr in (["", ] if cd == "H1" else ["200 顆中位", "r0"]):
            for sg in SEGORD:
                a_ = MT[(MT["候選"] == cd) & (MT["段"] == sg) & (MT["r"] == rr)].iloc[0]
                b_ = YM[(YM["候選"] == cd) & (YM["段"] == sg) & (YM["r"].fillna("") == rr)].iloc[0]
                d_ = max(float(abs(float(a_[c]) - float(b_[c]))) for c in cols)
                ri = "r0（營量）" if cd == "H1" else rr
                ai = IT[(IT["候選"] == cd) & (IT["段"] == sg) & (IT["r"] == ri)].iloc[0]
                bi = YI[(YI["候選"] == cd) & (YI["段"] == sg) & (YI["r"] == ri)].iloc[0]
                d_ = max(d_, max(float(abs(float(ai[c]) - float(bi[c]))) for c in icol))
                chk[f"{cd} {rr} {sg}"] = d_; worst = max(worst, d_)
    S["閘"]["對帳 yl（H1～H3 主表＋影響，最大絕對差；yl csv 為 6 位有效數字）"] = {"逐格": chk, "最大": worst}
    log(f"[對帳 yl] 最大絕對差 {worst:.2e}")
    if worst > 5e-6:
        raise SystemExit(f"⛔ H1～H3 與 yl 對不上（{worst}）")
    # 持股營收占比
    SH["年增>0占比"] = SH["年增>0"] / SH["持股檔數"].replace(0, np.nan)
    SH["年增<=0占比"] = SH["年增<=0"] / SH["持股檔數"].replace(0, np.nan)
    SH["年增缺占比"] = SH["年增缺"] / SH["持股檔數"].replace(0, np.nan)
    SH["創24月新高占比"] = SH["創24月新高"] / SH["持股檔數"].replace(0, np.nan)
    SH["r"] = SH["r"].fillna(-1).astype(int)

    def shagg(g):
        h = g[g["持股檔數"] > 0]
        tot = h["持股檔數"].sum()
        return pd.Series({"有持股事件數": len(h), "平均持股檔數": h["持股檔數"].mean(),
                          "年增>0占比（逐事件平均）": h["年增>0占比"].mean(), "年增<=0占比（逐事件平均）": h["年增<=0占比"].mean(),
                          "年增缺占比（逐事件平均）": h["年增缺占比"].mean(), "創24月新高占比（逐事件平均）": h["創24月新高占比"].mean(),
                          "年增>0占比（合併）": h["年增>0"].sum() / tot if tot else np.nan, "創24月新高占比（合併）": h["創24月新高"].sum() / tot if tot else np.nan,
                          "逐事件年增>0占比": " ".join(f"{v:.2f}" for v in h["年增>0占比"])})
    shs = SH.groupby(["段", "持股", "r"]).apply(shagg).reset_index()
    nm = [c for c in shs.columns if c not in ("段", "持股", "r", "逐事件年增>0占比")]
    s1 = shs[shs["持股"] == "H1"].copy(); s1["r"] = "r0（營量）"
    s2 = shs[shs["持股"] != "H1"].groupby(["段", "持股"])[nm].median().reset_index(); s2["r"] = "200 顆中位"
    s3 = shs[(shs["持股"] != "H1") & (shs["r"] == 0)].copy(); s3["r"] = "r0"
    HT = pd.concat([s1, s2, s3], ignore_index=True)
    HT["_s"] = HT["段"].map(SEGORD); HT = HT.sort_values(["持股", "r", "_s"]).drop(columns="_s")
    # 存檔
    MT.to_csv(os.path.join(OUT, "main_table.csv"), index=False, float_format="%.6g", encoding="utf-8")
    IT.to_csv(os.path.join(OUT, "impact.csv"), index=False, float_format="%.6g", encoding="utf-8")
    HT.to_csv(os.path.join(OUT, "holdshare.csv"), index=False, float_format="%.6g", encoding="utf-8")
    ER.to_csv(os.path.join(OUT, "event_rows.csv.gz"), index=False, float_format="%.8g")
    pd.concat([SR, IM[IM["候選"].isin(CANDS_R)]], keys=["事件與①", "對原策略影響"]).to_csv(os.path.join(OUT, "seeds.csv.gz"), float_format="%.8g")
    S["主表"] = MT.to_dict("records"); S["對原策略影響"] = IT.to_dict("records"); S["持股營收占比"] = HT.to_dict("records")
    S["結束（台北）"] = YL.now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_ylrev.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 300)
    log("[主表]\n" + MT[["段", "候選", "r", "進場事件數", "不足事件數（＜3，含 0）", "逐事件候選檔數", "平均報酬", "中位報酬", "勝率", "配對差平均",
                        "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落"]].to_string())
    log("[影響]\n" + IT[["段", "候選", "r", "窗", "窗內接受事件數", "閒錢不動_年化", "大跌加碼_年化", "年化差（加碼−不動）", "回落差（加碼−不動）",
                        "加碼部位自身累計損益（窗內）"]].to_string())
    log("[持股營收占比]\n" + HT[["段", "持股", "r", "有持股事件數", "平均持股檔數", "年增>0占比（逐事件平均）", "年增<=0占比（逐事件平均）", "年增缺占比（逐事件平均）",
                            "創24月新高占比（逐事件平均）", "年增>0占比（合併）"]].to_string())
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

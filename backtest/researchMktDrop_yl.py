# -*- coding: utf-8 -*-
"""大盤大跌日「用閒錢加碼手上的營量／營飆持股」與「跌最多一成裡只挑營收在成長的」——描述性初測（⛔ 不計 N、⛔ 不判定）——回測線計算子代理，2026-10-16。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（v1／初測／營收趨勢整合程式只 import 重用；逐股快取只讀）；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_yl [--procs 3]
    （第一步自動另開子程序跑營量／營飆正式引擎 ⇒ ~/mktdropwork/yl/engine.pkl；之後讀快取）

═══ 讀法（執行者補的都在這裡；寫死於第一次跑之前，2026-10-16 台北）═══
 Y0 全部重用 researchMktDrop_v1（PREREG大盤大跌後買什麼 seq1）：q2 事件＋「同時只處理一個事件」鎖 ⇒ 同 28 個接受事件（早年 10、2015～2021 7、2022～ 11）；
    世界、母體 R1、主出場（加權收盤 ≥ 事件前一日收盤 ⇒ 隔天開盤賣；⛔ 不設天數；壞根前收盤強制、下市最後收盤）、買不到剔除、成本（個股 0.585%、ETF 0.385%）、
    配對 0050（扣 ETF 成本）、①（只在事件進場、平時現金；連續曲線按段切；window_stats 口徑）、隨機日 200 次（同年、非原始事件日、同主出場、同候選；
    統計 ＝ 每筆平均淨報酬；p ＝ 隨機 ≥ 實際的比例）——v1.day_stats／bpath／curve1／wstats／eff_n 只 import 呼叫；執行期把 v1 模組的 CANDS／basket／EXITS
    換成本件清單（記憶體內、⛔ 不改 v1 檔；EXITS 只留「主」）；逐股快取讀 ~/mktdropwork/v1/packs_*.pkl（只讀）
 Y1 H 類（加碼手上持股）：營量 v1 ＝ researchYL_integrate 格 H60·S20·無·relvol r0（relvol 只排序、r1 逐位元同 r0）；營飆 v1 ＝ H120·S10·閘·抽籤 r0～199
    主世界 ＝ researchYL_integrate.main_world（researchT1fix.build_ctx(True)：edc6f 快照、AND T1、窗 2017-03-02～2026-08-24）；
    早年 ＝ researchYL_integrate.early_world（上市＋上櫃 W_B、窗 2005-02-01～2014-12-31）；引擎 ＝ researchYL_integrate.eng（同參數、audit 開）
    閘：每顆權益 sha ＝ resultsYL_integrate/seeds.csv.gz 同世界同格同 r 的 eq_sha（不同 ⇒ 停）
    「持有中」＝ 引擎 audit 配對（同 researchYL_blend.holdings_w：同日先賣後買、先進先出）⇒ 事件日 t 收盤仍持有 ＝ 買進日 ≤ t ＜ 賣出日（賣出日以收盤／開盤賣都算當天已不持有）；
       引擎窗尾（w1）之後不算持有（⇒ 2026-08-25 之後、2015-01～2017-03-01 主世界沒有 H 籃子）；以日期對到 MktDrop 世界日曆
    H1 ＝ 營量 v1 r0 持有中全部股等權；H2 ＝ 營飆 v1 第 r 顆持有中全部股等權（r ＝ 0～199，報 200 顆中位，另列 r0）；H3 ＝ 營量 r0 ∪ 營飆第 r 顆（同一檔只算一次）
    事件日 t 收盤決定、t＋1 開盤買、等權；買不到剔除（同 v1）；持股不在 MktDrop 世界股票清單 ⇒ 剔除、照報檔數；候選 ＜ 5 檔標「候選不足」、照買照算；0 檔 ⇒ 不進場
    加碼部位用 MktDrop 主出場（收復即賣），⛔ 與原策略自己的出場無關（原策略照舊）
 Y2 C 類：C ＝ v1 C（事件日 R1 母體報酬最低 ceil(10%) 檔，同 v1.basket 穩定排序）；
    C+ ＝ C 中「最近一期月營收年增 ＞ 0」；C++ ＝ C 中「最近一期月營收創 24 月新高」（候選檔數 ＝ 過濾後、買不到之前）
    營收 ＝ researchExit5.load_revenue（早年＋主世界 revenue_hist 合併、主世界優先，同 deep）／avail_pos（≤2025-12 期次月 10 日後、≥2026-01 期 15 日後第一個交易日）／
    rev_events：可得日 ≤ t 的最後一期；年增缺 ⇒ 不入選；24 月新高不可判（前 24 期不全）⇒ 不入選；⛔ 不設資料過舊上限（同 deep）
    閘：事件日 C 列的年增、24 月新高 ＝ deep c_rows.csv（6 位有效數字）
 Y3 並列 A（0050）、C：同程式重算並與 v1 main_table.csv 對帳（平均、中位、勝率、配對差、實際減隨機、p、① 年化、① 回落；差 ＞ 5e−6 ⇒ 停）
    隨機日種子 ＝ v1 同式 default_rng([v1.RSEED, 段號, 候選號, i])，A／C 用 v1 候選號 0／2，C+ 9、C++ 10、H1 11、H2 12、H3 13（H2／H3 每顆同一組種子、各自的有籃日池）
 Y4 對原策略的影響（H1～H3；加碼資金另撥）：段起點總資金 ＝ 原策略 80%＋閒錢 20%，⛔ 不再平衡；
    「閒錢不動」＝ 0.8 × 原策略 ＋ 0.2 現金；「大跌加碼」＝ 0.8 × 原策略 ＋ 0.2 × 加碼部位 ①曲線（平時現金、事件進場、收復即賣）
    原策略：H1 ＝ 營量 r0；H2 ＝ 營飆第 r 顆；H3 ＝ 營量 r0、營飆第 r 顆各半（段起點各 50%、不再平衡）
    原策略權益以日期對到 MktDrop 世界日曆（ffill，只在引擎窗內）；窗 ＝ 段 ∩ 引擎窗（2006～2014 全段；2015～2021 ⇒ 2017-03-02 起；2022～ ⇒ 到 2026-08-24）
    報 原策略本身、閒錢不動、大跌加碼 的年化／最大回落（window_stats），差（加碼 − 不動），加碼部位自身累計損益（①曲線同窗）
    ⚠ H 類的 ①（只在事件進場、平時現金）照 v1 用整段；組合影響用「段 ∩ 引擎窗」
 Y5 必附：見 NOTES
輸出 backtest/resultsMktDrop/yl/：MktDrop_yl.json、main_table.csv、impact.csv、event_rows.csv、seeds.csv.gz、random.csv.gz、run.log；大檔 ~/mktdropwork/yl/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/yl")
WORK = os.path.expanduser("~/mktdropwork/yl")
V1WORK = os.path.expanduser("~/mktdropwork/v1")
V1MAIN = os.path.join(REPO, "backtest/resultsMktDrop/v1/main_table.csv")
DEEPC = os.path.join(REPO, "backtest/resultsMktDrop/deep/c_rows.csv")
YISEEDS = os.path.join(REPO, "backtest/resultsYL_integrate/seeds.csv.gz")
ENGPK = os.path.join(WORK, "engine.pkl")
TIME = "2026-10-16（台北；讀法寫死、第一次跑之前）"
NSEED = 200
W_ADD = 0.20
CANDS_S = ["A", "C", "C+", "C++", "H1"]          # 固定（不隨種子）
CANDS_R = ["H2", "H3"]                           # 隨營飆種子
CN = {"A": "0050", "C": "當天跌最多一成（v1）", "C+": "C 中最近一期月營收年增 ＞ 0", "C++": "C 中最近一期月營收創 24 月新高",
      "H1": "營量 v1 持有中全部加碼", "H2": "營飆 v1 持有中全部加碼（200 顆中位）", "H3": "營量＋營飆持有中聯集加碼"}
RIDX = {"A": 0, "C": 2, "C+": 9, "C++": 10, "H1": 11, "H2": 12, "H3": 13}
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "⚠ C+、C++ 是看過 deep 拆解（營收年增 ≤0 三段略差、創新高略好）之後才選的切法 ⇒ 事後重切，任何「看起來較好」都只是待驗線索",
         "⚠ H1～H3 是新組合，但營量 v1／營飆 v1 的正式引擎結果本線都已看過",
         "事件只有 28 次（早年 10、2015～2021 7、2022～ 11），同事件內檔次高度相關；收復才賣的勝率有一部分來自規則本身（等多久都等）",
         "營量／營飆主世界引擎窗 2017-03-02～2026-08-24 ⇒ 2015-08-24 事件沒有 H 籃子（H 類 2015～2021 最多 6 事件）；早年引擎窗 2005-02～2014-12",
         "營量 v1 ＝ relvol r0（r1 逐位元同）；營飆 v1 ＝ 抽籤 200 顆，表上報 200 顆中位（各統計各自取中位，不是同一顆）＋r0",
         "對原策略的影響：加碼資金另撥（段起點 原策略 80%＋閒錢 20%，不再平衡）；與「閒錢不動」比",
         "早年（2006～2014）含減資假飆股約 0.3%（reduce_v2，剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市",
         "成本：個股 0.585% 來回、ETF 0.385%；未含滑價"]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 第一步：營量／營飆正式引擎（子程序）═════════════
def eng_job(args):
    from backtest import researchYL_integrate as YI
    wn, key, r = args
    W = YI._W[wn]
    o, au = YI.eng(W, key, r)
    eq = np.asarray(o["equity"], float)
    opn = {}; tr = []
    for a in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
        if a["side"] == "buy":
            opn.setdefault(a["sid"], []).append(int(a["t"]))
        else:
            tr.append((a["sid"], opn[a["sid"]].pop(0), int(a["t"])))
    for s, lst in opn.items():
        for t0 in lst:
            tr.append((s, t0, 10 ** 9))
    return wn, key, r, eq, int(o["first"]), int(o["end"]), tr, YI.sha(eq)


def engine_phase(procs):
    from multiprocessing import Pool
    from backtest import researchAddOn as RA
    from backtest import researchYL_integrate as YI
    os.makedirs(WORK, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "run.log"))
    log("[引擎] 開始（子程序）")
    Wm, gm = YI.main_world(log)
    We, ge = YI.early_world(log, procs)
    YI._W["主"], YI._W["早年"] = Wm, We
    jobs = [(wn, YI.YL, 0) for wn in ("主", "早年")] + [(wn, YI.YF, r) for wn in ("主", "早年") for r in range(NSEED)]
    with Pool(procs) as pool:
        res = pool.map(eng_job, jobs, chunksize=4)
    ref = pd.read_csv(YISEEDS, dtype={"eq_sha": str})
    ref = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    out = {"閘": {**gm, **ge}}
    bad = 0
    for wn, key, r, eq, f_, e_, tr, sh in res:
        if ref.get((wn, key, r)) != sh:
            bad += 1
        nm = "YL" if key == YI.YL else "YF"
        out.setdefault(wn, {}).setdefault(nm, {})[r] = (eq, f_, e_, tr)
    out["閘"]["權益 sha ≠ resultsYL_integrate seeds（顆數）"] = bad
    for wn, W in (("主", Wm), ("早年", We)):
        out[wn]["cal"] = W["cal"]; out[wn]["w0"] = int(W["w0"]); out[wn]["w1"] = int(W["w1"])
    log(f"[引擎] 閘 {out['閘']}")
    if bad:
        raise SystemExit(f"⛔ 引擎權益與 resultsYL_integrate 不同 {bad} 顆")
    pickle.dump(out, open(ENGPK, "wb"), protocol=5)
    log(f"[引擎] 存 {ENGPK}")


# ═════════════ 第二步 ═════════════
def hold_matrix(trades_list, cal_e, w1, cal, rix, n0):
    """trades（引擎日曆位置）⇒ MktDrop 世界 HOLD[S, n0]（t 收盤仍持有）；⇒ (HOLD, 不在世界的檔名集合)。"""
    S = len(rix); H = np.zeros((S, n0), bool); miss = set()
    cap = cal_e[min(w1, len(cal_e) - 1)]
    pend = int(cal.searchsorted(cap, "right"))
    for tr in trades_list:
        for s, tb, ts in tr:
            r = rix.get(s)
            if r is None:
                miss.add(s); continue
            p0 = int(cal.searchsorted(cal_e[tb]))
            p1 = int(cal.searchsorted(cal_e[ts])) if ts < len(cal_e) else n0
            p1 = min(p1, pend)
            if p1 > p0:
                H[r, p0:p1] = True
    return H, miss


def orig_curve(eq, cal_e, w0, w1, cal):
    """引擎權益 ⇒ MktDrop 世界日曆（引擎窗內 ffill，窗外 NaN）。"""
    n = min(len(eq), len(cal_e))
    s = pd.Series(eq[:n], index=cal_e[:n])
    s = s[(s.index >= cal_e[w0]) & (s.index <= cal_e[min(w1, n - 1)])]
    x = s.reindex(cal.union(s.index)).ffill().reindex(cal)
    m = (cal >= s.index[0]) & (cal <= s.index[-1])
    v = np.array(x.to_numpy(float), copy=True); v[~m] = np.nan
    return v


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    if not os.path.exists(ENGPK):
        log("[引擎] 快取不存在 ⇒ 子程序跑")
        env = dict(os.environ, PYTHONPATH=REPO)
        subprocess.run([sys.executable, "-m", "backtest.researchMktDrop_yl", "--engine", "--procs", str(a.procs)], cwd=REPO, env=env, check=True)
    ENG = pickle.load(open(ENGPK, "rb"))
    from backtest import researchMktDrop_v1 as V1
    from backtest import researchMktDrop as MD
    from backtest import researchExit5 as EX5
    MD.SEGS = V1.SEGS_V1
    orig_basket = V1.basket

    def basket_yl(M, t, cd):
        if cd == "A":
            return orig_basket(M, t, cd)
        if cd in ("C", "C+", "C++"):
            m = M["MEM"][:, t] & np.isfinite(M["RET"][:, t])
            rows = np.flatnonzero(m)
            if len(rows) < 20:
                return np.array([], int), 0, None
            v = M["RET"][rows, t]; ns = int(np.ceil(0.10 * len(rows)))
            sel = rows[np.argsort(v, kind="stable")[:ns]]
            if cd == "C+":
                with np.errstate(invalid="ignore"):
                    sel = sel[M["YOY"][sel, t] > 0]
            elif cd == "C++":
                sel = sel[M["HI24"][sel, t]]
            return sel[M["BUY"][sel, t]], len(sel), None
        Hm = M["HOLD_" + cd]
        sel = np.flatnonzero(Hm[:, t])
        return sel[M["BUY"][sel, t]], len(sel), None
    V1.basket = basket_yl; V1.EXITS = ["主"]          # 只在記憶體內換（⛔ 不改 v1 檔）

    S = {"件": "大盤大跌日加碼營量／營飆持股、跌最多一成只挑營收成長（描述性初測、不計 N、不判定）", "讀法寫死": TIME, "開跑（台北）": now_tpe(),
         "讀法": "見程式檔頭 Y0～Y5", "必附": NOTES, "候選": CN, "重用": "researchMktDrop_v1（PREREG大盤大跌後買什麼 seq1）、researchYL_integrate（營量 v1／營飆 v1 正式引擎）",
         "閘": {"引擎": ENG["閘"]}}
    IXmd = MD.load_index(log)
    df = IXmd["df"]
    EV = V1.index_events(df)
    ft = np.flatnonzero(EV["FIRST"]["q2"])
    if not np.array_equal(EV["rec"][ft], IXmd["rec"][ft]):
        raise SystemExit("⛔ q2 收復列與初測 rec 不同")
    S["指數"] = {"origin/main sha": IXmd["sha"], "q2 接受事件（全部）": int(EV["ACC"]["q2"].sum())}
    rev_e, rly_e, info_e = EX5.load_revenue(MD.DB.WORLDS["早年"]["data"])
    rev_m, rly_m, info_m = EX5.load_revenue(MD.DB.WORLDS["主"]["data"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    S["營收"] = {"早年": info_e, "主": info_m}
    DEEP = pd.read_csv(DEEPC, dtype={"sid": str})
    ROWS = []; SEGR = []; RND = []; IMP = []; SEEDR = []
    for wn in ("早年", "主"):
        W = MD.load_world(wn, IXmd, log); MD._G[wn] = W
        PK = pickle.load(open(os.path.join(V1WORK, f"packs_{wn}.pkl"), "rb")); log(f"[逐股 {wn}] 讀 v1 快取")
        EP = {s: MD.etf_pack(W, s) for s in MD.ETFS}
        M = MD.assemble(W, PK, EP, log)
        cal = W["cal"]; n0 = W["n0"]; BC = W["BC"]
        rix = {s: r for r, s in enumerate(M["sids"])}
        # 營收矩陣
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
        # 持有矩陣
        E = ENG[wn]; cal_e = E["cal"]; w0e, w1e = E["w0"], E["w1"]
        HY, missY = hold_matrix([E["YL"][0][3]], cal_e, w1e, cal, rix, n0)
        M["HOLD_H1"] = HY
        S["閘"].setdefault(wn, {})["營量持股不在世界（檔）"] = sorted(missY)
        S["閘"][wn]["引擎窗"] = f"{cal_e[w0e].date()}～{cal_e[w1e].date()}"
        datepos = {d: j for j, d in enumerate(cal)}
        segof = lambda p: next((sg for sg, (x0, y0) in W["segp"].items() if x0 <= p <= y0), None)   # noqa: E731
        rawpos = {datepos[d] for d in df["date"][EV["RAW"]["q2"]] if d in datepos}
        evs = []
        for i in np.flatnonzero(EV["ACC"]["q2"]):
            p = datepos.get(df["date"].iloc[i])
            if p is not None and p + 1 < n0 and segof(p) is not None:
                evs.append((p, i))
        # deep 閘：事件日 C 列年增、新高
        dchk = 0; dmax = 0.0; dn = 0
        for p, i in evs:
            ev_ = str(cal[p].date()); dd = DEEP[DEEP["事件日"] == ev_]
            for s, yv, hv in zip(dd["sid"], dd["yoy"], dd["hi24"]):
                r = rix[s]; dn += 1
                my = YOY[r, p]
                if np.isfinite(yv) != np.isfinite(my) or (np.isfinite(yv) and abs(my - yv) > 1e-5 * max(1, abs(yv))):
                    dchk += 1
                elif np.isfinite(yv):
                    dmax = max(dmax, abs(my - yv))
                if (hv == 1.0) != bool(HI24[r, p]):
                    dchk += 1
        S["閘"][wn]["deep C 列年增／新高不同"] = {"列": dn, "不同": dchk, "年增最大差": dmax}
        log(f"[閘 {wn}] deep 對帳 {S['閘'][wn]['deep C 列年增／新高不同']}｜營量持股不在世界 {len(missY)}")
        if dchk:
            raise SystemExit(f"⛔ {wn} 營收與 deep 對不上 {dchk}")
        hold0050 = BC / BC[0]

        def eval_cd(cd, DAY, MEMB, tag=None, keep_rows=True):
            cost = V1.COST_ETF if cd == "A" else V1.COST_STK
            Dx = DAY[cd]; Dd = Dx["主"]; paths = {}; rows = []
            for p, i in evs:
                base = {"世界": wn, "段": segof(p), "候選": cd, "r": tag, "日期": str(cal[p].date()), "指數報酬": float(EV["r"][i]),
                        "選出檔數": int(Dx["nsel"][p]), "買到檔數": int(Dx["n"][p]), "候選不足（＜5）": bool(cd != "A" and Dx["nsel"][p] < 5)}
                if Dx["n"][p] == 0:
                    rows.append({**base, "進場": False}); continue
                e_, end_, V, ro = V1.bpath(W, M, MEMB[(cd, p)], p, "主")
                paths[p] = (e_, end_, V, ro)
                Vpk = np.maximum.accumulate(np.r_[1.0, V])
                rows.append({**base, "進場": True, "報酬": float(Dd["net"][p]), "配對0050": float(Dd["b50"][p]), "配對差": float(Dd["net"][p] - Dd["b50"][p]),
                             "平均持有天數": float(Dd["hold"][p]), "持有中最大回落": float(np.min(np.r_[1.0, V] / Vpk - 1)),
                             "窗尾未出場比例": float(Dd["unex"][p]), "賣完日": str(cal[end_].date())})
            segs = []; rnd = []
            for sg, (x0, y0) in W["segp"].items():
                es = [(p, i) for p, i in evs if x0 <= p <= y0]
                ec = [p for p, _ in es if Dx["n"][p] > 0]
                ns_all = np.array([Dx["nsel"][p] for p, _ in es])
                row = {"世界": wn, "段": sg, "候選": cd, "r": tag, "指數事件數（接受、段內）": len(es), "進場事件數": len(ec),
                       "候選不足事件數（＜5，含 0）": int((ns_all < 5).sum()) if cd != "A" else 0, "0 檔事件數": int((ns_all == 0).sum()),
                       "逐事件候選檔數": " ".join(str(int(v)) for v in ns_all),
                       "候選檔數中位（段內事件）": float(np.median(ns_all)) if len(es) else np.nan}
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
                        if keep_rows:
                            rnd.append({"段": sg, "候選": cd, "i": rep, "隨機平均": rm[-1]})
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
            return rows, segs, rnd, eq1

        def impact(cd, eq1, origs, tag=None):
            """origs ＝ [(權重, MktDrop 日曆上的原策略權益)]（權重和 1，段起點各自歸一）。"""
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

        # 固定候選
        V1.CANDS = CANDS_S
        DAY, MEMB = V1.day_stats(W, M, log)
        EQ1 = {}
        for cd in CANDS_S:
            rows, segs, rnd, eq1 = eval_cd(cd, DAY, MEMB)
            ROWS += rows; SEGR += segs; RND += rnd; EQ1[cd] = eq1
        oY = orig_curve(E["YL"][0][0], cal_e, w0e, w1e, cal)
        IMP += impact("H1", EQ1["H1"], [(1.0, oY)])
        # 隨營飆種子
        V1.CANDS = CANDS_R
        missF = set()
        for r in range(NSEED):
            HF, mf = hold_matrix([E["YF"][r][3]], cal_e, w1e, cal, rix, n0); missF |= mf
            M["HOLD_H2"] = HF; M["HOLD_H3"] = HF | HY
            DAYr, MEMBr = V1.day_stats(W, M, (lambda m_: None))
            oF = orig_curve(E["YF"][r][0], cal_e, w0e, w1e, cal)
            for cd in CANDS_R:
                rows, segs, rnd, eq1 = eval_cd(cd, DAYr, MEMBr, tag=r, keep_rows=False)
                ROWS += rows; SEEDR += segs
                IMP += impact(cd, eq1, [(1.0, oF)] if cd == "H2" else [(0.5, oY), (0.5, oF)], tag=r)
            if r % 50 == 0:
                log(f"[{wn} 營飆種子] {r}/{NSEED}｜{time.time() - T0:.0f}s")
        S["閘"][wn]["營飆持股不在世界（檔，200 顆合計）"] = sorted(missF)
        log(f"[{wn}] 完｜{time.time() - T0:.0f}s")
        del M, DAY, MEMB, PK
    ER = pd.DataFrame(ROWS); SG = pd.DataFrame(SEGR); SR = pd.DataFrame(SEEDR); IM = pd.DataFrame(IMP)
    # 對帳 v1（A／C）
    V1M = pd.read_csv(V1MAIN)
    cols = ["平均報酬", "中位報酬", "勝率", "配對差平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落"]
    chk = {}; worst = 0.0
    for cd in ("A", "C"):
        for sg in ("2006～2014", "2015～2021", "2022～"):
            a_ = SG[(SG["候選"] == cd) & (SG["段"] == sg)].iloc[0]; b_ = V1M[(V1M["候選"] == cd) & (V1M["段"] == sg)].iloc[0]
            d_ = max(float(abs(a_[c] - b_[c])) for c in cols); chk[f"{cd} {sg}"] = d_; worst = max(worst, d_)
    S["閘"]["對帳 v1 main_table（A／C，最大絕對差）"] = {"逐格": chk, "最大": worst}
    log(f"[對帳 v1] 最大絕對差 {worst:.2e}")
    if worst > 5e-6:
        raise SystemExit(f"⛔ A／C 與 v1 對不上（{worst}）")
    # H2／H3：200 顆中位
    num = [c for c in SR.columns if c not in ("世界", "段", "候選", "r", "逐事件候選檔數") and pd.api.types.is_numeric_dtype(SR[c])]
    med = SR.groupby(["世界", "段", "候選"])[num].median().reset_index()
    med["r"] = "200 顆中位"
    r0 = SR[SR["r"] == 0].copy(); r0["r"] = "r0"
    # 逐事件候選檔數（200 顆中位）
    ec = ER[ER["候選"].isin(CANDS_R)].groupby(["候選", "日期"])["選出檔數"].median()
    for d_ in (med, r0):
        d_["逐事件候選檔數"] = [" ".join(f"{ec[(c_, dt)]:g}" for dt in sorted(ER[(ER["候選"] == c_) & (ER["段"] == s_)]["日期"].unique()))
                         for c_, s_ in zip(d_["候選"], d_["段"])]
    SG["r"] = SG["r"].fillna("")
    MT = pd.concat([SG, med, r0], ignore_index=True)
    MT["_s"] = MT["段"].map({"2006～2014": 0, "2015～2021": 1, "2022～": 2}); MT["_c"] = MT["候選"].map(list(CN).index)
    MT["_r"] = MT["r"].map(lambda x: 1 if x == "r0" else 0)
    MT = MT.sort_values(["_c", "_r", "_s"]).drop(columns=["_s", "_c", "_r"])
    MT.insert(2, "名稱", MT["候選"].map(CN))
    keep = ["段", "候選", "名稱", "r", "指數事件數（接受、段內）", "進場事件數", "候選不足事件數（＜5，含 0）", "0 檔事件數", "逐事件候選檔數", "候選檔數中位（段內事件）",
            "平均籃子檔數（買到）", "買不到比例", "等效獨立事件數", "平均報酬", "中位報酬", "勝率", "同期0050平均（配對、含成本）", "配對差平均", "配對差中位", "X較好比例",
            "平均持有天數", "隨機平均", "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落", "①比值", "①在場日比例", "一直抱0050_年化", "一直抱0050_最大回落"]
    MT = MT[[c for c in keep if c in MT.columns]]
    # 影響表
    inum = [c for c in IM.columns if c not in ("世界", "段", "候選", "r", "窗") and pd.api.types.is_numeric_dtype(IM[c])]
    i1 = IM[IM["候選"] == "H1"].copy(); i1["r"] = "r0（營量）"
    imed = IM[IM["候選"].isin(CANDS_R)].groupby(["世界", "段", "候選", "窗"])[inum].median().reset_index(); imed["r"] = "200 顆中位"
    ir0 = IM[IM["候選"].isin(CANDS_R) & (IM["r"] == 0)].copy(); ir0["r"] = "r0"
    IT = pd.concat([i1, imed, ir0], ignore_index=True)
    IT["_s"] = IT["段"].map({"2006～2014": 0, "2015～2021": 1, "2022～": 2}); IT["_c"] = IT["候選"].map(list(CN).index)
    IT = IT.sort_values(["_c", "r", "_s"]).drop(columns=["_s", "_c"])
    IT = IT[["段", "候選", "r", "窗"] + [c for c in IT.columns if c not in ("世界", "段", "候選", "r", "窗")]]
    # 存檔
    MT.to_csv(os.path.join(OUT, "main_table.csv"), index=False, float_format="%.6g", encoding="utf-8")
    IT.to_csv(os.path.join(OUT, "impact.csv"), index=False, float_format="%.6g", encoding="utf-8")
    ER.to_csv(os.path.join(OUT, "event_rows.csv.gz"), index=False, float_format="%.8g")
    pd.concat([SR, IM[IM["候選"].isin(CANDS_R)]], keys=["事件與①", "對原策略影響"]).to_csv(os.path.join(OUT, "seeds.csv.gz"), float_format="%.8g")
    pd.DataFrame(RND).to_csv(os.path.join(OUT, "random.csv.gz"), index=False, float_format="%.6g")
    S["主表"] = MT.to_dict("records"); S["對原策略影響"] = IT.to_dict("records")
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop_yl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
    log("[主表]\n" + MT[["段", "候選", "r", "進場事件數", "候選不足事件數（＜5，含 0）", "逐事件候選檔數", "平均報酬", "中位報酬", "勝率", "配對差平均",
                        "實際減隨機", "p（隨機 ≥ 實際）", "①只在事件進場_年化", "①最大回落"]].to_string())
    log("[影響]\n" + IT[["段", "候選", "r", "窗", "窗內接受事件數", "原策略_年化", "原策略_最大回落", "閒錢不動_年化", "閒錢不動_最大回落", "大跌加碼_年化", "大跌加碼_最大回落",
                        "年化差（加碼−不動）", "回落差（加碼−不動）", "加碼部位自身累計損益（窗內）"]].to_string())
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--engine", action="store_true", help="只跑營量／營飆引擎（子程序用）")
    a = ap.parse_args()
    sys.path.insert(0, REPO)
    os.makedirs(OUT, exist_ok=True)
    if a.engine:
        engine_phase(a.procs); return
    from backtest import researchAddOn as RA
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

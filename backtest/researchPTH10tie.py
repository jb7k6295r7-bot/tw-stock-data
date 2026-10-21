# -*- coding: utf-8 -*-
"""高10 同分三排序【正式跑】T1 F9／T2 營收年增／T3 低波動 對 200 組抽籤（台股策略線登錄 seq1 sha 0840ddaa3ddb1fa9；裁定 seq433、434、435 §四）——回測線計算子代理，2026-10-21。
⛔ 不改既有檔、只新增；⛔ 不寫第二份實作：researchPTHpf（build_world、metrics、pf_stats、常數）、researchPTHn（run_slot、trades_df、df_text）、
   researchPTH（stock_job）、researchPTH10seed（events_with、seed_of、SEED0、NSEED、seg_row、buyset、same_arr）、
   researchPTH10tie_freq（order_of、date_scores、vol_feats、f9_cols、ai1_table、ai1_patch）、researchMktDrop_fund／quality、researchExit5、
   benchmark_rejudge（read_series、on_cal、seg_pos、bstat）、researchAscTri（ratio、label）、researchIndMom_freq（reg_check）只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10tie --world 主|早年 [--procs 4]
    乾跑（fixture，⛔ 無任何真實報酬）：… -m backtest.researchPTH10tie --dry
    彙總（兩世界跑完後；只讀 main/ 內本件輸出）：… -m backtest.researchPTH10tie --summary
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10tie_check
輸出 backtest/resultsPTH10tie/main/：raw_<世界>.npz（各排序與 200 組權益）、seeds_<世界>.csv、cells_<世界>.csv、trades_<世界>_<排序>[s].csv.gz、
    keys_<世界>.csv.gz（各排序鍵）、result.json、table.csv、run.log

═══ 讀法（★＝執行者定；寫死於第一次正式執行前，2026-10-21 台北；登錄字面優先）═══
 R0 登錄 sha 先核（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼，researchIndMom_freq.reg_check）；不符 ⇒ 中止。策略鎖前後 --check 相符。
 R1 引擎 ＝ researchPTHn.run_slot(ev, W, 10, slip) 原樣（高10 seq4：跳月、PTH 由高往下、10 格、6 個月、空位 0050、500 張閘與缺口規則在事件檔內）。
    唯一更動 ＝ 同 PTH 內次序：o ＝ researchPTH10tie_freq.order_of(ev, 算不出旗標, 分數)（lexsort(rk, −分數, 算不出, −PTH, 進場日)）；
    ★ 交給引擎的方式 ＝ ev 複本的 rk 換成「o 中的位置」⇒ run_slot 的 lexsort(rk', −PTH, 進場日) ＝ o（每格逐位元斷言）；其餘欄 ⛔ 不動。
    分數 ＝ 頻率表同式重建（同分群、date_scores、vol_feats、f9_cols、AI1 覆寫）⇒ 必與 resultsPTH10tie/freq/members_<世界>.csv.gz 全文逐字相同，否則中止。
    排序鍵：T1 F9 高→低（＝ 三套名次相加小者先）、T2 營收年增 高→低、T3 60 日波動 低→高、MAX 20 日最大單日漲幅 低→高（描述臂）；算不出排最後；仍同分 ⇒ 原種子 rk。
 R2 段：探索 2017-03-02～2021-12-30（W.segp）；★ 確認（判定）＝ 2022-01-03～2026-08-24（排名表同窗，benchmark_rejudge.seg_pos）；另報 確認原窗 2022-01-03～資料尾 2026-09-24
    （W.segp）；早年 W.segp（2005～2014，只描述）。年化／回落 ＝ researchPTHpf.metrics（rerun17.win_metrics）；比值 ＝ AS.ratio。
 R3 200 組分布 ★ ＝ 本行程重跑 researchPTH10seed 種子 k＝1…200（events_with(seed_of(k)) ＋ run_slot）⇒ 權益與 resultsBenchRejudge/pth10seed_<世界>.npz 逐位元、
    探索／確認原窗 年化／回落／比值 ＝ resultsPTH10seed/seeds_<世界>.csv（%.10g 字面）⇒ 再切排名窗。
    百分位 ★ ＝ 200 組中「≤ 該排序值」的比例（另報「＜」）。
 R4 判定（登錄二）★：每格「探索 年化、探索 比值、確認 年化、確認 比值」四個百分位都 ≥ 0.97 ⇒「〔排序〕勝過抽籤」（暫定）；否則「跟抽籤分不出」。MAX、早年 ⛔ 不判。
 R5 並報：大盤報酬指數（origin/main data/history/market_tri.csv，benchmark_rejudge.bstat，世界日曆 ffill）與 0050（W.bench）同窗 年化／回落／比值與標籤（AS.label）；
    滑價版（每邊 +0.5%，slot_tr slip）；pf_stats（平均持股、換手、成本）；空位率 ＝ 1 − 平均持股 ÷ 10。
    持股重疊 ★ ＝ 段內買進（日, 代號）集合：|A∩B| ÷ |A|；對原種子一個值；對 200 組 ⇒ 中位、p5、p95；並列「200 組對原種子」的同式中位當抽籤基準線。
 R6 不前視：排序鍵只用 ≤ 形成月底的資料（頻率表 K1 已驗；本件 check 再驗 members 檔可得日欄）；進場在跳 1 個月後。
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import subprocess
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHn as PN                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchPTH10seed as PS                # noqa: E402
from backtest import researchPTH10tie_freq as TF            # noqa: E402
from backtest import researchMktDrop_fund as FU             # noqa: E402
from backtest import researchMktDrop_quality as QL          # noqa: E402
from backtest import researchExit5 as EX5                   # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import benchmark_rejudge as BR_               # noqa: E402
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

REG_SHA = "0840ddaa3ddb1fa9"
OUT = "backtest/resultsPTH10tie/main"
FREQ = TF.OUT
SEEDNPZ = "backtest/resultsBenchRejudge/pth10seed_{}.npz"
TRSRC = "git:origin/main:data/history/market_tri.csv"
N = 10
NSEED = PS.NSEED
ORDS = ["原", "T1", "T2", "T3", "MAX"]
JUDGED = ["T1", "T2", "T3"]
ORDNAME = {"原": "原種子抽籤 [20261023, j]", "T1": "T1 F9 分數（三套名次相加小者先＝F9 高→低）", "T2": "T2 營收年增 高→低", "T3": "T3 60 日波動 低→高",
           "MAX": "MAX 20 日最大單日漲幅 低→高（描述臂）"}
KEYCOL = {"T1": ("F9", False), "T2": ("rv_yoy", False), "T3": ("vol60", True), "MAX": ("max20", True)}
THR = 0.97
RANKWIN = ("2022-01-03", "2026-08-24")
KEEP_EXTRA = ["q", "形成月底", "進場日", "sid", "grp", "PTH", "F9ok", "has6", "has7", "hasQ", "F6", "F7", "Q", "F6_g6", "F7_g6", "Q_g6", "F9", "F9寬",
              "rv_yoy", "rev_avail_date", "vol60", "vol60_n", "max20", "max20_n", "q_nmiss", "fin_q", "fin_src", "q_finq", "q_finsrc", "q_divsrc", "f7_fin_q",
              "tdcc_date", "inU", "大母體檔數"]


def lock_check():
    p = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    out = (p.stdout + p.stderr).strip().splitlines()
    return bool(("相符" in "".join(out[-3:])) and p.returncode == 0), out[-3:]


# ═════════════ 排序 ⇒ 引擎 ═════════════
def ev_with_order(ev0, o):
    """R1：rk 換成 o 中的位置；斷言 run_slot 的 lexsort 重現 o。"""
    nev = len(ev0["e"])
    rk2 = np.empty(nev, float); rk2[o] = np.arange(nev, dtype=float)
    ev = dict(ev0); ev["rk"] = rk2
    if not np.array_equal(np.lexsort((ev["rk"], -ev["pth"], ev["e"])), o):
        raise SystemExit("⛔ rk 位置化後 lexsort ≠ 指定次序")
    return ev


def windows(W, wn):
    cal = W["cal"]
    if wn == "主":
        x, y = BR_.seg_pos(cal, *RANKWIN)
        return {"探索": W["segp"]["探索"], "確認": (x, y), "確認原窗": W["segp"]["確認"]}
    return {"早年": W["segp"]["早年"]}


def segm(W, eq, x, y):
    c, m, b = M.metrics(W, eq, x, y)
    return c, m, AS.ratio(c, m), b


def buys_in(ev, S, x, y):
    return {(int(t), str(ev["sid"][S["q"][q]])) for t, q, _ in S["buys"] if x <= t <= y}


def ovl(A, B):
    return len(A & B) / max(len(A), 1)


# ═════════════ 分數重建（＝ 頻率表 world() 的分數段，函式全 import）═════════════
def build_keys(W, ev, wn, procs, log, J):
    nev = len(ev["e"])
    grp = np.full(nev, -1, np.int64); gid = 0
    for e in np.unique(ev["e"]):
        idx = np.flatnonzero(ev["e"] == e)
        for v, c in Counter(ev["pth"][idx].tolist()).items():
            if c >= 2:
                mm = idx[ev["pth"][idx] == v]; grp[mm] = gid; gid += 1
    forms = sorted({ev["form"][q] for q in np.flatnonzero(grp >= 0)})
    t0 = time.time()
    FU._G["cal"] = {W["data"]: W["cal"]}
    allu = FU.universe_sids(W["data"], forms[0], forms[-1])
    memsids = sorted({str(ev["sid"][q]) for q in np.flatnonzero(grp >= 0)})
    sids_all = sorted(set(allu) | set(memsids))
    mkt = {s: W["mk"].get(s, allu.get(s, "twse")) for s in sids_all}
    BRx = FU.run_jobs([(W["data"], s, mkt[s], forms) for s in sids_all], procs, wn)
    log(f"[{wn}] uni_job {len(sids_all)} 檔 × {len(forms)} 排序日｜{time.time() - t0:.0f}s")
    FIN, _ = FU.load_fin(); QFIN, _ = QL.load_fin()
    am, _ = TF.ai1_table(FU.XD)
    n6, m6 = TF.ai1_patch(FIN, am); nq, mq = TF.ai1_patch(QFIN, am)
    J["AI1覆寫"][wn] = {"fund 季列": n6, "最大延後天": m6, "quality 季列": nq, "最大延後天(Q)": mq}
    TD, _ = FU.load_tdcc()
    DV, mkd, smk = QL.load_div()
    rev, rly, _ = EX5.load_revenue(W["data"])
    AV = EX5.avail_pos(list(rev.index), W["cal"]); AVA = np.array([AV[p] for p in rev.index], np.int64)
    X = {"W": W, "BR": BRx, "rev": rev, "rly": rly, "AV": AV, "AVA": AVA, "TD": TD, "DV": DV, "mkd": mkd, "smk": smk}
    parts = []; t0 = time.time()
    for f_ in forms:
        qs = np.flatnonzero((grp >= 0) & (ev["form"] == f_))
        sids = [str(ev["sid"][q]) for q in qs]
        if len(set(sids)) != len(sids):
            raise SystemExit(f"⛔ {f_} 同批同檔重複")
        d = TF.date_scores(X, pd.Timestamp(f_), sids, {s: int(grp[q]) for s, q in zip(sids, qs)}, FIN, QFIN)
        d["q"] = d["sid"].map(dict(zip(sids, qs.tolist())))
        p = int(W["cal"].searchsorted(pd.Timestamp(f_)))
        V = pd.DataFrame([TF.vol_feats(W, s, p) for s in d["sid"]], index=d.index)
        for c in V.columns:
            d[c] = V[c]
        parts.append(d)
    MB = TF.f9_cols(pd.concat(parts, ignore_index=True))
    MB["進場日"] = [W["dates"][ev["e"][q]] for q in MB["q"]]; MB["形成月底"] = [ev["form"][q] for q in MB["q"]]
    MB["PTH"] = [ev["pth"][q] for q in MB["q"]]
    MB["rev_avail_date"] = [W["dates"][p] if 0 <= p < W["n0"] else "" for p in MB["rev_avail_pos"]]
    log(f"[{wn}] 分數 {len(MB)} 列｜{time.time() - t0:.0f}s")
    keep = KEEP_EXTRA + list(TF.F6KEYS) + list(TF.F7KEYS) + list(TF.QKEYS)
    b = io.StringIO(); MB[keep].to_csv(b, index=False, float_format="%.10g"); txt = b.getvalue()
    with gzip.open(os.path.join(FREQ, f"members_{wn}.csv.gz"), "rt", encoding="utf-8") as fh:
        ref = fh.read()
    if txt != ref:
        raise SystemExit(f"⛔ {wn} 分數重建 ≠ 頻率表 members_{wn}.csv.gz")
    J["對帳"][f"{wn}|排序鍵重建 vs resultsPTH10tie/freq/members_{wn}.csv.gz"] = f"全文逐字相同（{len(MB)} 列、{gid} 組、{len(forms)} 排序日）"
    KEY = {"原": (np.zeros(nev, bool), np.zeros(nev))}
    qv = MB["q"].to_numpy(np.int64)
    for nm, (col, neg) in KEYCOL.items():
        v = np.full(nev, np.nan); v[qv] = MB[col].to_numpy(float) * (-1 if neg else 1)
        fl = ~np.isfinite(v); fl[grp < 0] = False; v[grp < 0] = 0.0
        KEY[nm] = (fl, np.where(np.isfinite(v), v, 0.0))
    KD = pd.DataFrame({"q": np.arange(nev), "sid": ev["sid"], "形成月底": ev["form"], "進場日": [W["dates"][e] for e in ev["e"]], "PTH": ev["pth"],
                       "grp": grp, "rk原": ev["rk"]})
    for nm in KEYCOL:
        KD[f"{nm}_算不出"] = KEY[nm][0]; KD[f"{nm}_鍵"] = KEY[nm][1]
    return KEY, KD, grp


# ═════════════ 世界 ═════════════
def world(wn, a, log):
    T0 = time.time()
    J = {"世界": wn, "開跑": M.now_tpe(), "對帳": {}, "AI1覆寫": {}}
    W = M.build_world(wn, log)
    WIN = windows(W, wn)
    J["窗"] = {k: f"{W['cal'][x].date()}～{W['cal'][y].date()}" for k, (x, y) in WIN.items()}
    RES = {}
    with Pool(a.procs) as pool:
        for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
            if r is not None:
                RES[sid] = r
    log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - T0:.0f}s")
    ev0, _ = PS.events_with(W, wn, RES, PS.SEED0)
    nev = len(ev0["e"])
    # ── 原種子重現（直接 ＋ 經 rk 位置化）
    Z = np.load(os.path.join(PN.OUT, f"eq_{wn}.npz"))
    SIM = {}
    for slip, tag in ((False, "N10"), (True, "N10s")):
        Sd = PN.run_slot(ev0, W, N, slip)
        o0 = TF.order_of(ev0, np.zeros(nev, bool), np.zeros(nev))
        Sr = PN.run_slot(ev_with_order(ev0, o0), W, N, slip)
        for S_, how in ((Sd, "直接"), (Sr, "rk 位置化")):
            for k_ in ("eq", "hv", "u", "pend", "nh"):
                if not np.array_equal(S_[k_], Z[f"{tag}_{k_}"]):
                    raise SystemExit(f"⛔ 原種子（{how}）{wn} {tag} {k_} ≠ resultsPTHn")
            with gzip.open(os.path.join(PN.OUT, f"trades_{wn}_{tag}.csv.gz"), "rt", encoding="utf-8") as fh:
                if PN.df_text(PN.trades_df(W, ev0, S_), "%.17g") != fh.read():
                    raise SystemExit(f"⛔ 原種子（{how}）{wn} {tag} 交易檔 ≠ resultsPTHn")
        J["對帳"][f"{wn}|原種子 {tag}（直接、rk 位置化兩路）eq/hv/u/pend/nh ＋ 交易檔全文 vs resultsPTHn"] = f"逐位元／逐字相同（{len(Sd['buys'])} 筆）"
        SIM[("原", slip)] = (ev0, Sd)
    # ── 200 組種子（分布）
    ZS = np.load(SEEDNPZ.format(wn))
    if list(ZS["dates"][[0, -1]]) != [str(W["cal"][0].date()), str(W["cal"][-1].date())] or not np.array_equal(ZS["eq"][0], Z["N10_eq"]):
        raise SystemExit("⛔ pth10seed npz 日曆或 k＝0 不符")
    sref = pd.read_csv(os.path.join(PS.OUT, f"seeds_{wn}.csv"), dtype=str, encoding="utf-8-sig").set_index("k")
    SEQ, SB, SROW = [], [], []; t0 = time.time(); bad = 0
    for k in range(1, NSEED + 1):
        evk, _ = PS.events_with(W, wn, RES, PS.seed_of(k))
        for key in PS.EVKEYS:
            if not PS.same_arr(evk[key], ev0[key]):
                raise SystemExit(f"⛔ k={k} 事件欄 {key} ≠ 原種子")
        S = PN.run_slot(evk, W, N, False)
        if not np.array_equal(S["eq"], ZS["eq"][k]):
            raise SystemExit(f"⛔ 種子 {k} 權益 ≠ {SEEDNPZ.format(wn)}")
        for sg in PS.SEGS[wn]:
            d, _ = PS.seg_row(W, S, sg)
            for col in ("年化", "回落", "比值"):
                if "%.10g" % d[f"{sg}_{col}"] != sref.loc[str(k), f"{sg}_{col}"]:
                    bad += 1
        SEQ.append(S["eq"]); SB.append({sg: buys_in(evk, S, x, y) for sg, (x, y) in WIN.items()})
        r = {"k": k}
        for sg, (x, y) in WIN.items():
            c, m, rt, _ = segm(W, S["eq"], x, y)
            r.update({f"{sg}_年化": c, f"{sg}_回落": m, f"{sg}_比值": rt})
        SROW.append(r)
        if k % 50 == 0:
            log(f"[{wn}] 種子 {k}/{NSEED}｜{time.time() - t0:.0f}s")
    if bad:
        raise SystemExit(f"⛔ 種子段統計 ≠ resultsPTH10seed/seeds_{wn}.csv（{bad} 格）")
    J["對帳"][f"{wn}|200 組種子權益 vs {SEEDNPZ.format(wn)}"] = "200 條逐位元相同"
    J["對帳"][f"{wn}|200 組 {'／'.join(PS.SEGS[wn])} 年化／回落／比值 vs resultsPTH10seed/seeds_{wn}.csv（%.10g）"] = "全部相同"
    SD = pd.DataFrame(SROW)
    del RES
    # ── 排序鍵
    KEY, KD, grp = build_keys(W, ev0, wn, a.procs, log, J)
    KD.to_csv(os.path.join(OUT, f"keys_{wn}.csv.gz"), index=False, float_format="%.10g", encoding="utf-8", compression="gzip")
    # ── 各排序真引擎
    for nm in ORDS[1:]:
        o = TF.order_of(ev0, *KEY[nm])
        evn = ev_with_order(ev0, o)
        for slip in (False, True):
            SIM[(nm, slip)] = (evn, PN.run_slot(evn, W, N, slip))
        log(f"[{wn}] {nm} 買進 {len(SIM[(nm, False)][1]['buys'])}／滑價 {len(SIM[(nm, True)][1]['buys'])}")
    for (nm, slip), (evn, S) in SIM.items():
        PN.trades_df(W, evn, S).to_csv(os.path.join(OUT, f"trades_{wn}_{nm}{'s' if slip else ''}.csv.gz"), index=False, float_format="%.17g",
                                       encoding="utf-8", compression="gzip")
    np.savez_compressed(os.path.join(OUT, f"raw_{wn}.npz"), seeds_eq=np.array(SEQ), dates=np.array([str(d.date()) for d in W["cal"]]),
                        **{f"{nm}{'s' if slip else ''}_{k_}": SIM[(nm, slip)][1][k_] for (nm, slip) in SIM for k_ in ("eq", "nh")})
    # ── 基準
    TR = BR_.read_series(TRSRC); trarr, nfill = BR_.on_cal(TR, W["cal"])
    J["大盤報酬指數"] = {"來源": TRSRC, "origin/main": BR_.git("rev-parse", "origin/main").strip(), "世界日曆 ffill 補值日": nfill}
    # ── 每格每段
    CELLS = []
    for nm in ORDS:
        for slip in (False, True):
            evn, S = SIM[(nm, slip)]
            typ_q = evn["typ"][S["q"]]
            for sg, (x, y) in WIN.items():
                c, m, rt, b = segm(W, S["eq"], x, y)
                bt = BR_.bstat(W["cal"], trarr, x, y)
                st = M.pf_stats(W, S, x, y, typ_q)
                r = {"世界": wn, "排序": nm, "滑價": slip, "段": sg, "窗": J["窗"][sg], "年化": c, "回落": m, "比值": rt,
                     "平均持股": st["平均持股(筆)"], "空位率": 1 - st["平均持股(筆)"] / N, "0050占淨值": st["0050占淨值"], "換手每年": st["換手每年"],
                     "成本合計每年(實付)": st["成本合計每年(實付)"], "買進筆": st["買進筆"], "平均持有天數": st["平均持有天數"],
                     "大盤年化": bt["cagr"] if bt else np.nan, "大盤回落": bt["mdd"] if bt else np.nan, "大盤比值": bt["ratio"] if bt else np.nan,
                     "對大盤": AS.label(c, m, bt) if bt else "—", "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]),
                     "對0050": AS.label(c, m, b)}
                if not slip:
                    for col, v in (("年化", c), ("比值", rt)):
                        dist = SD[f"{sg}_{col}"].to_numpy(float)
                        r[f"{col}_百分位(≤)"] = float((dist <= v).mean()); r[f"{col}_百分位(<)"] = float((dist < v).mean())
                    A = buys_in(evn, S, x, y)
                    r["重疊_對原種子"] = ovl(A, buys_in(ev0, SIM[("原", False)][1], x, y))
                    ov = np.array([ovl(A, sb[sg]) for sb in SB])
                    r["重疊_對200組_中位"] = float(np.median(ov)); r["重疊_對200組_p5"] = float(np.quantile(ov, .05)); r["重疊_對200組_p95"] = float(np.quantile(ov, .95))
                CELLS.append(r)
    # 200 組自身摘要（分布列）
    B0 = {sg: buys_in(ev0, SIM[("原", False)][1], x, y) for sg, (x, y) in WIN.items()}
    DIST = []
    for sg, (x, y) in WIN.items():
        o = {"世界": wn, "段": sg, "窗": J["窗"][sg]}
        for col in ("年化", "回落", "比值"):
            v = SD[f"{sg}_{col}"]
            o.update({f"{col}_中位": float(v.median()), f"{col}_p5": float(v.quantile(.05)), f"{col}_p95": float(v.quantile(.95)),
                      f"{col}_p97": float(v.quantile(.97)), f"{col}_最大": float(v.max()), f"{col}_第194名": float(np.sort(v.to_numpy())[193])})
        ovs = np.array([ovl(sb[sg], B0[sg]) for sb in SB])
        o["200組對原種子重疊_中位"] = float(np.median(ovs))
        DIST.append(o)
    SD.to_csv(os.path.join(OUT, f"seeds_{wn}.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    pd.DataFrame(CELLS).to_csv(os.path.join(OUT, f"cells_{wn}.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    pd.DataFrame(DIST).to_csv(os.path.join(OUT, f"dist_{wn}.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, f"world_{wn}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[{wn}] 完 {J['耗時秒']}s")


# ═════════════ 彙總（判定）═════════════
def verdict_of(C, nm):
    r = {sg: C[(C["排序"] == nm) & (~C["滑價"]) & (C["段"] == sg)].iloc[0] for sg in ("探索", "確認")}
    pc = {f"{sg}_{col}": float(r[sg][f"{col}_百分位(≤)"]) for sg in ("探索", "確認") for col in ("年化", "比值")}
    ok = all(v >= THR for v in pc.values())
    return ok, pc


def summary(log):
    C = pd.read_csv(os.path.join(OUT, "cells_主.csv"), encoding="utf-8-sig", float_precision="round_trip")
    E = pd.read_csv(os.path.join(OUT, "cells_早年.csv"), encoding="utf-8-sig", float_precision="round_trip")
    D = pd.concat([pd.read_csv(os.path.join(OUT, f"dist_{w}.csv"), encoding="utf-8-sig", float_precision="round_trip") for w in ("主", "早年")])
    WJ = {w: json.load(open(os.path.join(OUT, f"world_{w}.json"), encoding="utf-8")) for w in ("主", "早年")}
    VD = {}
    for nm in JUDGED:
        ok, pc = verdict_of(C, nm)
        VD[nm] = {"成立": ok, "四個百分位(≤)": pc,
                  "結果句": (f"高10 同分時改用〔{ORDNAME[nm]}〕挑，兩段都勝過 97% 的抽籤結果（暫定）" if ok else f"高10 同分時用〔{ORDNAME[nm]}〕挑，跟抽籤分不出")}
    n_ok = sum(v["成立"] for v in VD.values())
    cm = C[~C["滑價"]]
    pri = {"① 三格 0 格成立（約六成）": f"成立 {n_ok} 格 ⇒ {'中' if n_ok == 0 else '不中'}"}
    cc = cm[(cm["段"] == "確認") & cm["排序"].isin(JUDGED)].set_index("排序")
    ce = cm[(cm["段"] == "探索") & cm["排序"].isin(JUDGED)].set_index("排序")
    for sg, X_ in (("確認", cc), ("探索", ce)):
        pri[f"② T2 在三格中年化最高（約四成）｜{sg}"] = f"年化最高 ＝ {X_['年化'].idxmax()} ⇒ {'中' if X_['年化'].idxmax() == 'T2' else '不中'}"
        pri[f"③ T3 回落最淺、但年化最低（約五成）｜{sg}"] = (f"回落最淺 ＝ {X_['回落'].idxmax()}、年化最低 ＝ {X_['年化'].idxmin()} ⇒ "
                                                f"{'中' if (X_['回落'].idxmax() == 'T3' and X_['年化'].idxmin() == 'T3') else '不中'}")
    J = {"題": "高10 同分三排序 T1 F9／T2 營收年增／T3 低波動 對 200 組抽籤（組合層，N_組合 ＋3）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}（{IM.reg_check(REG_SHA)}）", "裁定": "seq433、434、435 §四",
         "判定": VD, "成立格數": n_ok, "先驗": pri, "對帳": {**WJ["主"]["對帳"], **WJ["早年"]["對帳"]}, "AI1覆寫": {**WJ["主"]["AI1覆寫"], **WJ["早年"]["AI1覆寫"]},
         "窗": {"主": WJ["主"]["窗"], "早年": WJ["早年"]["窗"]}, "大盤報酬指數": WJ["主"]["大盤報酬指數"],
         "必附": ["F9 分數本身是看過歷史才定（且在大跌情境高分組不比低分組好）", "高10 看過結果、最多暫定，只能靠前瞻確認", "同分時排序，不是整個選股改變",
                "早年 T1 依構造退化：F9 2005～2010 可算 0%、需抽月切點仍隨機 57% ⇒ 一半仍抽籤，只描述"],
         "完成": M.now_tpe()}
    json.dump(J, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.concat([C, E]).to_csv(os.path.join(OUT, "table.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    log("[判定] " + json.dumps(VD, ensure_ascii=False)); log("[先驗] " + json.dumps(pri, ensure_ascii=False))


# ═════════════ 乾跑 fixture（⛔ 無真實報酬）═════════════
def dry():
    print(TF.selftest())
    rng = np.random.default_rng(1)
    ev = {"e": np.repeat([3, 5, 9], 7), "pth": np.tile([1, 1, 1, 1, .95, .95, .9], 3).astype(float), "rk": rng.random(21)}
    fl = rng.random(21) < .2; sc = rng.integers(0, 3, 21).astype(float)
    for f_, s_ in ((fl, sc), (np.zeros(21, bool), np.zeros(21)), (np.ones(21, bool), sc)):
        o = TF.order_of(ev, f_, s_); ev2 = ev_with_order(ev, o)
        assert np.array_equal(np.lexsort((ev2["rk"], -ev2["pth"], ev2["e"])), o)
    o0 = TF.order_of(ev, np.zeros(21, bool), np.zeros(21)); assert np.array_equal(o0, np.lexsort((ev["rk"], -ev["pth"], ev["e"])))
    print("ev_with_order fixture：隨機鍵／全 0／全算不出 ⇒ lexsort(rk', −PTH, e) ＝ order_of；全 0 ＝ 原序 全過")
    # 判定 fixture（合成百分位）
    C = pd.DataFrame([{"排序": "T1", "滑價": False, "段": sg, "年化_百分位(≤)": a_, "比值_百分位(≤)": b_} for sg, a_, b_ in (("探索", .98, .975), ("確認", .97, .99))]
                     + [{"排序": "T2", "滑價": False, "段": sg, "年化_百分位(≤)": a_, "比值_百分位(≤)": b_} for sg, a_, b_ in (("探索", .99, .99), ("確認", .965, .99))])
    assert verdict_of(C, "T1")[0] and not verdict_of(C, "T2")[0]
    print("判定 fixture：四個 ≥ 0.97 ⇒ 成立；任一 ＜ 0.97 ⇒ 不成立 全過")
    d = np.arange(1, 201) / 200.0
    assert (d <= d[193]).mean() == 0.97 and (d <= d[192]).mean() < 0.97
    print("百分位 fixture：第 194 名 ＝ 0.97 全過")
    print("窗：排名窗", RANKWIN, "｜段來源 W.segp；TR", TRSRC, "｜REG", IM.reg_check(REG_SHA))
    print("KEYCOL", KEYCOL, "SEED0", PS.SEED0, "NSEED", NSEED)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--world", default=None)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    IM.reg_check(REG_SHA)                                      # R0：不符即 SystemExit
    if a.dry:
        dry(); print("策略鎖", lock_check()); return
    os.makedirs(OUT, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "run.log"))
    lk = lock_check(); log(f"[策略鎖 前] {lk}")
    if not lk[0]:
        raise SystemExit("⛔ 策略鎖不符")
    if a.summary:
        summary(log)
    else:
        world(a.world, a, log)
    lk = lock_check(); log(f"[策略鎖 後] {lk}")


if __name__ == "__main__":
    main()

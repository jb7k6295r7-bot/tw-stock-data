# -*- coding: utf-8 -*-
"""大盤大跌前瞻：事件日候選名單（A、B、C、C+、E、F）＋ F8 前 3 —— backtest/forward/mktdrop_cands.py（寫死 10/15）的通用化版（回測線程式子代理，2026-10-17）。
⛔ 只描述、不判；⛔ 不是買賣建議；用語「假訊號」。

    事件成立當天由 backtest.mktdrop_fwd daily 自動呼叫 make_candidates(事件日, sha, md=每日名單檔)；也可手動：
      cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.mktdrop_cands --date 2026-10-15 --sha <main sha> \
          --md backtest/resultsDaily/daily_2026-10-15.md [--fsha <財報籌碼 sha>] [--out CSV] [--nof8]

═══ 讀法（照 forward/mktdrop_cands.py 逐行搬，只把 10/15、sha、F 改成參數；第一次寫入之前寫死，2026-10-17 台北）═══
 資料：~/h2data/<sha>/data（run_daily_list.sh 的 archive）；⭐ 日曆尾必須 ＝ 事件日（事件日當晚跑；重產舊事件要用當時的 sha）
 母體 R1 ＝ gate3（GATE_V2 開）∩ 四碼普通股 ∧ Frame.gate ∧ pit_valid ∧ 前 20 根無壞根（seq335：research11 next_bad ∪ researchBARR.bad_part ∪ adj 減資／面額）
   ＝ researchMktDrop_v1.basket() / researchMktDrop.stock_job 的 R1 定義
 A 0050、B 00631L（當日報酬只描述）
 C ＝ R1 當天報酬最低 ceil(10%) 檔（stable、列序＝代號排序）
 C+ ＝ C 裡「可得日 ≤ 事件日的最後一期月營收」年增 ＞ 0（≤2025-12 期次月 10 日後、≥2026-01 期次月 15 日後第一個交易日；researchExit5.avail_pos）
 E ＝ 成員 ≥ 5 檔的產業（industry_pit pit 版＋營收彙總表後備；排「其他」「存託憑證」「ETF」與無產業）中等權報酬最差 2 個的 R1 股
 F ＝ 事件日營量 v1 正式訊號【已達成】＝ 每日名單 daily_<事件日>.md 第二節列的代號（⛔ 不含即將達成）；0 檔 ⇒ 一列「F 不進場」；1～4 檔 ⇒ 備註候選不足、照買照算
 持股（描述對照）＝ 持股.csv 營量／營飆／營飆營量（跑的當下那份）
 ⭐ F8top3（研究紀錄、未驗證、不入判；使用者 2026-10-17 要記前瞻）：C+ 內 F8 ＝ F6 名次百分位 ＋ F7 名次百分位 前 3 檔
   F6、F7 逐檔分數 ＝ researchMktDrop_fund.forward() 同式（重用 fund 的函式；財報、法人、融資、集保讀 ~/mktdropwork 下 --fsha 的 git archive，預設 ＝ sha）
   F8 ＝ researchMktDrop_f8.add_f8／order（F6、F7 先取 6 位有效數字＝同 f8 讀 features.csv；同分 ⇒ F7 高者 ⇒ 代號）
 輸出 candidates_<事件日>.csv（欄位同 10/15 版；F8top3 三列放在 F 列之後、持股列之前）
── 2026-10-17 改（使用者裁：檔數改 4，並採 F9；只加列、A～F／C+／持股列不動）──
 ⭐ F9top4（使用者採用、未驗證、不入判）：C+ 內 F9 ＝ F6 名次百分位 ＋ F7 名次百分位 ＋ Q 名次百分位（等權）前 4 檔（--f9n，預設 4）
   Q ＝ researchMktDrop_quality 的函式在事件日 PIT 算（重用 load_fin／fin_q／load_div／div_q／add_q，不另寫）：
     財報 ＝ --fsha archive 的 fin_hist／fs_xbrl，可得日 ＝ filing_dates.csv（t57sb01）該季最早上傳日 ＜ 事件日（無時戳 ⇒ 法定期限）；
     配息 ＝ 事件日 archive（--sha）data/adj 除息紀錄、除息日 ＜ 事件日；6 子項 C+ 內百分位等權、缺值 0 分
   Q 先取 6 位有效數字（同 f9 讀 quality/forward_*.csv）；F9 ＝ researchMktDrop_f9.add_f9／order（F9 四捨五入 1e-6；同分 ⇒ F7 高者 ⇒ 代號）
 ⭐ F8 檔數參數化（--f8n，預設改 4 ⇒ 候選欄「F8top4」；--f8n 3 可回 F8top3）
 列序：F 列之後 F9top<n> 先、F8top<n> 後，再接持股列；--nof8 ⇒ F8、F9 都不算（只 A～F）；--nof9 ⇒ 只不算 F9
 --feat CSV ⇒ 另寫 C+ 逐檔 F6／F7／Q（含 6 子項）／三個名次百分位／F8／F9（稽核用）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import research11 as R
from backtest import patterns as P
from backtest import universe_gate as UG
from backtest import researchIndRev_prereg as PRE
from backtest import researchBARR as BARR
from backtest import researchExit5 as EX5
from backtest import holdings as HD

REPO = os.path.expanduser("~/tw-p17")
IND_EXCL = {"其他", "存託憑證", "ETF"}
SEC2 = "## 二、營量 v1 已達成"
F8N = 4                            # 2026-10-17 使用者裁：檔數 4（--f8n 3 可回舊版 F8top3）
F9N = 4
F8TAG = "F8top3"                   # 舊名（10/15 正式紀錄用過）；新產一律 f8tag(n)


def f8tag(n):
    return f"F8top{int(n)}"


def f9tag(n):
    return f"F9top{int(n)}"
FUND_PATHS = ["data/meta/calendar_twse.csv", "data/meta/stocks.csv", "data/meta/filing_dates.csv", "data/meta/fs_xbrl",
              "data/mops/fin_hist", "data/stocks_inst", "data/stocks_margin", "data/tdcc", "data/tdcc_hist"]
COLS = ["候選", "代號", "名稱", "當日報酬", "營收期別", "年增", "是否跌停", "產業", "備註"]
_C: dict = {}                      # Pool（fork）用：DATA、cal、n0、TP


def ddir(sha):
    p = os.path.expanduser(f"~/h2data/{sha}/data")
    if not os.path.isdir(os.path.join(p, "stocks")):
        raise SystemExit(f"⛔ 沒有 archive：{p}（先跑 run_daily_list.sh 或 git archive）")
    return p


def fund_dir(fsha, log=print):
    """財報／法人／融資／集保（每日 archive 沒有）⇒ ~/mktdropwork/fund/<fsha10>/data（fund 研究那份）或 ~/mktdropwork/fwd/<fsha10>/data（沒有就 git archive）。"""
    for base in ("fund", "fwd"):
        p = os.path.expanduser(f"~/mktdropwork/{base}/{fsha[:10]}/data")
        if os.path.isdir(os.path.join(p, "mops", "fin_hist")) and os.path.isdir(os.path.join(p, "stocks_inst")):
            return p
    root = os.path.expanduser(f"~/mktdropwork/fwd/{fsha[:10]}")
    tmp = root + ".tmp"
    subprocess.run(["rm", "-rf", tmp], check=True)
    os.makedirs(tmp)
    t0 = time.time()
    ar = subprocess.Popen(["git", "-C", REPO, "archive", fsha] + FUND_PATHS, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", tmp], stdin=ar.stdout, check=True)
    if ar.wait() != 0:
        raise SystemExit(f"⛔ git archive {fsha} 失敗")
    os.replace(tmp, root)
    log(f"[財報籌碼 archive] {root}（{time.time() - t0:.0f}s）")
    return os.path.join(root, "data")


def f_from_md(md):
    """每日名單第二節（營量 v1 已達成）的代號；「- 無」⇒ []；找不到第二節 ⇒ 丟例外。"""
    L = open(md, encoding="utf-8").read().splitlines()
    k = [i for i, x in enumerate(L) if x.startswith(SEC2)]
    if len(k) != 1:
        raise SystemExit(f"⛔ {md} 找不到「{SEC2}」（{len(k)} 個）")
    out, none = [], False
    for x in L[k[0] + 1:]:
        if x.startswith("## "):
            break
        m = re.match(r"^- (\d{4,6}[A-Z]?) ", x)
        if m:
            out.append(m.group(1))
        elif x.strip() == "- 無":
            none = True
    if not out and not none:
        raise SystemExit(f"⛔ {md} 第二節沒有代號也沒有「- 無」，格式看不懂")
    return out


def next_td(cal, DATA):
    """事件日下一個【預計】交易日（備註「m/d 開盤買」用）：平日 − 休市表休市日 ＋ 休市表交易日（同 run_daily_list.sh --final 讀法）。"""
    hol, trade = set(), set()
    hs = os.path.join(DATA, "meta", "holiday_schedule.csv")
    if os.path.exists(hs):
        h = pd.read_csv(hs, dtype=str)
        h = h[h["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
        for d, nm, nt in zip(h["date"], h["name"].fillna(""), h["note"].fillna("") if "note" in h else [""] * len(h)):
            (trade if (any(k in nm for k in ("開始交易", "最後交易")) and "無交易" not in nt) else hol).add(d)
    d = cal[-1] + pd.Timedelta(days=1)
    while (d.weekday() >= 5 and d.strftime("%Y-%m-%d") not in trade) or d.strftime("%Y-%m-%d") in hol:
        d += pd.Timedelta(days=1)
    return d


def _job(a):
    """＝ forward/mktdrop_cands.py job（逐行同；全域改讀 _C）。"""
    sid, mk = a
    DATA, cal, n0, TP, T_DATE = _C["DATA"], _C["cal"], _C["n0"], _C["TP"], _C["T"]
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


# ═════════════ F8（重用 researchMktDrop_fund／_f8）═════════════
def f8_rank(t, DATA, XD, cal, cp, procs=4, log=print):
    """cp：C+ 名單 [(代號, 名稱, 當日報酬, 年增)]（依名單列序）⇒ DataFrame（F8 降冪；欄 F8名次、sid、名稱、F8、r6、r7、F6、F7、F7A～E、F1、F4、F5…）。
    ＝ researchMktDrop_fund.forward() 的逐檔分數（大母體 F7、C+ 內 F6）＋ researchMktDrop_f8 的 add_f8／order。"""
    from backtest import researchMktDrop_fund as FU
    from backtest import researchMktDrop_f8 as F8
    FU.XD = XD                                                      # fund 的財報／法人／融資／集保路徑（uni_job 在 fork 的子程序讀）
    FIN, finfo = FU.load_fin()
    TD, tdd = FU.load_tdcc()
    D.DATA = DATA
    n0 = len(cal); TP = int(cal.searchsorted(t)); assert TP < n0 and cal[TP] == t
    FU._G["cal"] = {DATA: cal}
    mk = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")["market"].to_dict()
    rev, rly, _ = EX5.load_revenue(DATA); AV = EX5.avail_pos(list(rev.index), cal); AVA = np.array([AV[p] for p in rev.index], np.int64)
    ds = str(t.date())
    us = FU.universe_sids(DATA, ds, ds)
    sids = sorted(set(us) | {x[0] for x in cp})
    BR = FU.run_jobs([(DATA, s, mk.get(s, "twse"), [ds]) for s in sids], procs, ds)
    rows = []
    for sid, nm, r1, yoy in cp:
        f = {"sid": sid, "名稱": nm, "事件日": ds, "ret1": float(r1), "rv_yoy": float(yoy)}
        E = [e for e in EX5.rev_events(sid, rev, rly, AV, n0) if e[0] <= TP]
        last3 = [e[1] for e in E[-3:]]
        f["rv_yoy3"] = float(np.mean(last3)) if len(last3) == 3 and np.isfinite(last3).all() else np.nan
        f["rv_hi24"] = (np.nan if (not E or E[-1][2] is None) else float(E[-1][2])); f["yoy_chk"] = E[-1][1] if E else np.nan
        f.update(FU.fin_feats(FIN.get(sid), t))
        b = BR[(sid, ds)]
        for k in ("tc_ma120", "ch_i1", "ch_i5", "ch_i20", "ch_t20", "ch_mu"):
            f[k] = b[k]
        f["tc_r60"] = b["chk_r60"]; f["tc_rs"] = b["chk_r20"]; f["tc_ma60"] = b["chk_ma60"]; f["tc_d52"] = b["chk_d52"]; f["tc_drop"] = -float(r1)
        f["ret1_chk"] = b["chk_ret1"]
        f["ch_big"], f["tdcc_date"] = FU.tdcc_chg(TD, sid, t, 4)
        rows.append(f)
    d = pd.DataFrame(rows)
    d = FU.add_scores(d, "事件日")
    cps = set(d["sid"]); rr = []
    for s in sids:
        b = BR.get((s, ds))
        inU = bool(s in us and b.get("valid") == 1.0 and np.isfinite(b.get("amt20", np.nan)) and b["amt20"] >= 5e7)
        if not inU and s not in cps:
            continue
        r = {"事件日": ds, "sid": s, "inU": inU, "inC": s in cps, "e1": b["e1"], "e2": b["e2"], "d1": b["d1"], "d2": b["d2"]}
        r.update(FU.rev7(s, rev, rly, AVA, TP)); r.update(FU.fin7(FIN.get(s), t)); r["d3"], _ = FU.tdcc_chg(TD, s, t, 1)
        rr.append(r)
    T = pd.DataFrame(rr); T = FU.f7_scores(T, T["inU"].to_numpy(bool))
    d = d.merge(T[T["inC"]][["sid", "inU"] + list(FU.F7SUB) + ["fin_ind", "f7_fin_q", "F7A", "F7B", "F7C", "F7D", "F7E", "F7"]], on="sid", how="left")
    info = {"財報": finfo, "集保週": f"{pd.Timestamp(tdd[0]).date()}～{pd.Timestamp(tdd[-1]).date()}", "大母體": int(T["inU"].sum()),
            "C+在大母體": int((T["inU"] & T["inC"]).sum()), "C+": len(cps),
            "年增對名單最大差": float(np.nanmax(np.abs(d["rv_yoy"] - d["yoy_chk"]))) if len(d) else None,
            "當日報酬對名單最大差": float(np.nanmax(np.abs(d["ret1"] - d["ret1_chk"]))) if len(d) else None,
            "F6缺": int(d["F6"].isna().sum()), "F7缺": int(d["F7"].isna().sum())}
    W = d.copy()
    for c in ("F6", "F7", "F7A"):                                   # 同 f8 讀 fund/forward_*_features.csv（float_format %.6g）
        W[c] = [float(f"{x:.6g}") if np.isfinite(x) else np.nan for x in W[c].to_numpy(float)]
    W = F8.add_f8(W, "事件日")
    o = F8.order(W, "F8").reset_index(drop=True)
    o["F8名次"] = np.arange(1, len(o) + 1)
    return o, info, d


# ═════════════ Q、F9（重用 researchMktDrop_quality／_f9）═════════════
def q_scores(t, DATA, XD, sids, log=print):
    """C+ 代號 ⇒ DataFrame（sid、6 子項、p_*、Q、q_nmiss…）＝ researchMktDrop_quality.forward() 同式，只是事件日 t、資料路徑參數化。
    財報 ＝ XD（fin_hist／fs_xbrl／filing_dates：t57sb01 上傳日 ＜ t）；配息 ＝ DATA/adj（除息日 ＜ t）、市場別 ＝ adj/_index.csv ∪ DATA/meta/stocks.csv。"""
    from backtest import researchMktDrop_fund as FU
    from backtest import researchMktDrop_quality as QL
    keep = (QL.XD, QL.ADJ, FU.FDATA)
    QL.XD = XD; QL.ADJ = os.path.join(DATA, "adj"); FU.FDATA = DATA       # quality 的模組路徑（load_fin 讀 QL.XD；load_div 讀 QL.ADJ、FU.FDATA/meta/stocks.csv）
    try:
        FIN, finfo = QL.load_fin()
        DV, mk, smk = QL.load_div()
    finally:
        QL.XD, QL.ADJ, FU.FDATA = keep
    W = pd.DataFrame({"sid": list(sids)}); W["事件日"] = str(t.date())
    FQ = pd.DataFrame([QL.fin_q(FIN.get(s), t) for s in W["sid"]], index=W.index)
    for c in FQ.columns:
        W[c] = FQ[c]
    dv = [QL.div_q(DV, mk, smk, s, t) for s in W["sid"]]
    W["q_div"] = [x[0] for x in dv]; W["q_divsrc"] = [x[1] for x in dv]
    W = QL.add_q(W, "事件日")
    info = {"財報季列": finfo.get("季列"), "財報季": W["q_finq"].value_counts().to_dict(), "配息來源": W["q_divsrc"].value_counts().to_dict(),
            "缺值比例": {s: round(float(W[s].isna().mean()), 3) for s in QL.SUBS}, "Q缺": int(W["Q"].isna().sum())}
    return W, info


def f9_rank(t, DATA, XD, o8, log=print):
    """o8 ＝ f8_rank 的輸出（F6、F7 已取 6 位有效數字）⇒ DataFrame（F9 降冪；欄 F9名次、sid、名稱、F9、r6、r7、rQ、Q、F6、F7、Q 子項…）。
    ＝ researchMktDrop_f9.forward()：Q 取 6 位有效數字（同讀 quality/forward_*.csv）後 add_f9／order。"""
    from backtest import researchMktDrop_quality as QL
    from backtest import researchMktDrop_f9 as F9
    QW, qinfo = q_scores(t, DATA, XD, o8["sid"].tolist(), log)
    W = o8[["sid", "名稱", "事件日", "F6", "F7"]].copy()
    W = W.merge(QW[["sid", "Q", "q_nmiss", "q_finq", "q_divsrc"] + QL.SUBS + ["p_" + s for s in QL.SUBS]], on="sid", how="left")
    if W["Q"].isna().any():
        raise SystemExit(f"⛔ Q 有缺：{W.loc[W['Q'].isna(), 'sid'].tolist()}")
    W["Q"] = [float(f"{x:.6g}") for x in W["Q"].to_numpy(float)]
    W = F9.add_f9(W, "事件日")
    o = F9.order(W, "F9").reset_index(drop=True)
    o["F9名次"] = np.arange(1, len(o) + 1)
    return o, qinfo


# ═════════════ 候選名單 ═════════════
def make_candidates(t_date, sha, md=None, f_codes=None, fsha=None, out=None, procs=4, f8=True, log=print, f8n=F8N, f9=True, f9n=F9N, feat_out=None):
    """事件日 t_date 的候選名單 ⇒ 寫 out（預設 researchMktDrop_v1.FWD/candidates_<日>.csv）；回摘要 dict。
    F：f_codes（代號 list）優先；否則讀 md（每日名單）第二節；兩者都沒有 ⇒ 丟例外。
    f8＝False ⇒ F8、F9 都不算；f8n／f9n ＝ 檔數（候選欄 F8top<n>／F9top<n>）；f9＝False ⇒ 只不算 F9；feat_out ⇒ 另寫 C+ 逐檔分數表。"""
    from backtest import researchMktDrop_v1 as RM
    T0 = time.time()
    T_DATE = pd.Timestamp(t_date)
    DATA = ddir(sha)
    if f_codes is None:
        if not md:
            raise SystemExit("⛔ F 要每日名單第二節（md）或 f_codes")
        f_codes = f_from_md(md)
    f_codes = list(dict.fromkeys(str(x) for x in f_codes))
    out = out or os.path.join(RM.FWD, f"candidates_{T_DATE.strftime('%Y%m%d')}.csv")
    g0 = UG.GATE_V2
    UG.set_gate_v2(True)
    try:
        D.DATA = DATA
        cal = D.load_calendar(); n0 = len(cal)
        if cal[-1] != T_DATE:
            raise SystemExit(f"⛔ 日曆尾 {cal[-1].date()} ≠ 事件日 {T_DATE.date()}（要用事件日當晚的 sha）")
        TP = n0 - 1
        _C.update({"DATA": DATA, "cal": cal, "n0": n0, "TP": TP, "T": T_DATE})
        nx = next_td(cal, DATA); md_ = f"{nx.month}/{nx.day}"
        stocks = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
        nm_of = stocks.drop_duplicates("stock_id", keep="last").set_index("stock_id")["name"].to_dict()
        U = UG.gate3(stocks); U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
        jobs = list(zip(U["stock_id"], U["market"]))
        with Pool(procs) as pool:
            res = dict(pool.map(_job, jobs, chunksize=16))
        log(f"[載入] gate3(GATE_V2)∩四碼 {len(U)} 檔｜{time.time() - T0:.0f}s")
        st = {"gate3∩四碼": len(U), "load_bars 可用（≥260 根）": sum(v is not None for v in res.values()),
              "當天有成交": sum(bool(v and v.get("traded")) for v in res.values())}
        mem = sorted(s for s, v in res.items() if v and v.get("traded") and v["mem"] and np.isfinite(v["ret"]))
        st["R1 母體（閘∧pit_valid∧前20根無壞根）"] = len(mem)
        st["剔除：成交閘不過"] = sum(1 for v in res.values() if v and v.get("traded") and not v["gate"])
        st["剔除：pit_valid 否"] = sum(1 for v in res.values() if v and v.get("traded") and v["gate"] and not v["pv"])
        st["剔除：前20根有壞根"] = sum(1 for v in res.values() if v and v.get("traded") and v["gate"] and v["pv"] and not v["nobad"])
        if len(mem) < 20:
            raise SystemExit(f"⛔ R1 母體 {len(mem)} 檔 ＜ 20（登錄：母體 ＜ 20 檔不排）")
        rets = np.array([res[s]["ret"] for s in mem])
        ns = int(np.ceil(0.10 * len(mem)))
        o = np.argsort(rets, kind="stable")
        Csel = [mem[i] for i in o[:ns]]
        rev_, rly_, cat, mk, nf, nr = PRE.load_rev(DATA)
        PIT = PRE.PIT(DATA, cat)
        ind = {}; isrc = {}
        for s in sorted(set(mem) | set(f_codes)):
            v, src = PIT._at(s, T_DATE, "pit")
            ind[s] = v; isrc[s] = src
        dfi = pd.DataFrame({"s": mem, "v": rets, "i": [ind[s] for s in mem]})
        order = {}
        for s in mem:
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
        REV = {s: lastrev(s) for s in set(Csel) | set(Esel) | set(f_codes)}
        Cp = [s for s in Csel if np.isfinite(REV[s][1]) and REV[s][1] > 0]
        etf = {}
        for s in ("0050", "00631L"):
            stx = D.load_stock(s, "twse", cal); c = stx.df["close"].to_numpy(float)
            etf[s] = float(c[TP] / c[TP - 1] - 1.0) if np.isfinite(c[TP]) and np.isfinite(c[TP - 1]) else np.nan
        hold = []
        for c_, bd_, bp_, nt_, src in HD.read_csv():
            if src in ("營量", "營飆", "營飆營量"):
                per, yoy = lastrev(c_)
                r_ = res.get(c_)
                hold.append({"代號": c_, "名稱": nm_of.get(c_, ""), "來源": src, "買進日": bd_, "營收期別": per, "年增": yoy,
                             "當日報酬": (r_["ret"] if r_ and r_.get("traded") else np.nan), "是否跌停": (r_["dn"] if r_ and r_.get("traded") else None),
                             "在R1": c_ in set(mem)})
    finally:
        UG.set_gate_v2(g0)
    # ── F8 前 n、F9 前 n（GATE_V2 照 fund 研究：關）──
    F8sel = []; f8info = None; F9sel = []; f9info = None
    tag8, tag9 = f8tag(f8n), f9tag(f9n)
    if f8 and Cp:
        XD = fund_dir(fsha or sha, log)
        oF8, f8info, _feat = f8_rank(T_DATE, DATA, XD, cal, [(s, nm_of.get(s, ""), res[s]["ret"], REV[s][1]) for s in Cp], procs=procs, log=log)
        F8sel = oF8.head(int(f8n)).to_dict("records")
        f8info["財報籌碼資料"] = XD
        f8info["前10"] = [{"名次": int(r["F8名次"]), "代號": r["sid"], "名稱": r["名稱"], "F8": round(float(r["F8"]), 3), "F6名次百分位": round(float(r["r6"]), 3),
                          "F7名次百分位": round(float(r["r7"]), 3), "F6": float(r["F6"]), "F7": float(r["F7"])} for r in oF8.head(10).to_dict("records")]
        if f9:
            oF9, qinfo = f9_rank(T_DATE, DATA, XD, oF8, log=log)
            F9sel = oF9.head(int(f9n)).to_dict("records")
            f9info = {"Q": qinfo, "財報資料": XD, "配息資料": os.path.join(DATA, "adj"),
                      "前10": [{"名次": int(r["F9名次"]), "代號": r["sid"], "名稱": r["名稱"], "F9": float(r["F9"]), "F6名次百分位": round(float(r["r6"]), 4),
                               "F7名次百分位": round(float(r["r7"]), 4), "Q名次百分位": round(float(r["rQ"]), 4), "Q": float(r["Q"]),
                               "F8名次": int(oF8.index[oF8["sid"] == r["sid"]][0]) + 1} for r in oF9.head(10).to_dict("records")]}
            if feat_out:
                r8 = dict(zip(oF8["sid"], oF8["F8名次"]))
                FT = oF9.assign(F8名次=oF9["sid"].map(r8))
                os.makedirs(os.path.dirname(os.path.abspath(feat_out)), exist_ok=True)
                FT.to_csv(feat_out, index=False, encoding="utf-8", float_format="%.10g")
    # ── 輸出 CSV（欄、列序、格式同 forward/mktdrop_cands.py；F8top3 放 F 列之後）──
    rows = []
    fmt = lambda x: "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else x
    rows.append({"候選": "A", "代號": "0050", "名稱": nm_of.get("0050", "元大台灣50"), "當日報酬": etf["0050"], "營收期別": "", "年增": "", "是否跌停": "", "產業": "", "備註": f"照登錄：{md_} 開盤買"})
    rows.append({"候選": "B", "代號": "00631L", "名稱": nm_of.get("00631L", ""), "當日報酬": etf["00631L"], "營收期別": "", "年增": "", "是否跌停": "", "產業": "", "備註": f"照登錄：{md_} 開盤買（正2 含槓桿效果）"})
    for cd, sel in (("C", Csel), ("C+", Cp)):
        for s in sel:
            per, y = REV[s]
            rows.append({"候選": cd, "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": res[s]["ret"], "營收期別": fmt(per), "年增": fmt(y),
                         "是否跌停": "是" if res[s]["dn"] else "否", "產業": fmt(ind[s]), "備註": ""})
    for s in Esel:
        per, y = REV[s]
        rows.append({"候選": "E", "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": res[s]["ret"], "營收期別": fmt(per), "年增": fmt(y),
                     "是否跌停": "是" if res[s]["dn"] else "否", "產業": ind[s], "備註": ""})
    src_f = f"每日名單 daily_{T_DATE.date()} 第二節，main {sha[:10]}"
    if not f_codes:
        rows.append({"候選": "F", "代號": "", "名稱": "", "當日報酬": "", "營收期別": "", "年增": "", "是否跌停": "", "產業": "",
                     "備註": f"0 檔：營量 v1 正式訊號 {T_DATE.month}/{T_DATE.day} 已達成＝無（{src_f}）⇒ 照登錄該事件 F 不進場"})
    for s in f_codes:
        per, y = REV[s]; r_ = res.get(s) or {}
        rows.append({"候選": "F", "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": (r_["ret"] if r_.get("traded") else ""), "營收期別": fmt(per), "年增": fmt(y),
                     "是否跌停": (("是" if r_["dn"] else "否") if r_.get("traded") else ""), "產業": fmt(ind.get(s)),
                     "備註": f"營量 v1 已達成（{src_f}）" + (f"；候選不足（{len(f_codes)} ＜ 5 檔，照登錄照買照算）" if len(f_codes) < 5 else "")})
    for j, r in enumerate(F9sel):
        s = r["sid"]; per, y = REV[s]
        rows.append({"候選": tag9, "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": res[s]["ret"], "營收期別": fmt(per), "年增": fmt(y),
                     "是否跌停": "是" if res[s]["dn"] else "否", "產業": fmt(ind[s]),
                     "備註": f"F9 第 {j + 1} 名（C+ {len(Cp)} 檔內 F6 名次百分位 {r['r6']:.1f} ＋ F7 名次百分位 {r['r7']:.1f} ＋ Q 名次百分位 {r['rQ']:.1f} ＝ {r['F9']:.1f}）；"
                             f"使用者採用、未驗證、不入判"})
    for j, r in enumerate(F8sel):
        s = r["sid"]; per, y = REV[s]
        rows.append({"候選": tag8, "代號": s, "名稱": nm_of.get(s, ""), "當日報酬": res[s]["ret"], "營收期別": fmt(per), "年增": fmt(y),
                     "是否跌停": "是" if res[s]["dn"] else "否", "產業": fmt(ind[s]),
                     "備註": f"F8 第 {j + 1} 名（C+ {len(Cp)} 檔內 F6 名次百分位 {r['r6']:.1f} ＋ F7 名次百分位 {r['r7']:.1f} ＝ {r['F8']:.1f}）；研究紀錄、未驗證、不入判"})
    for h in hold:
        rows.append({"候選": "持股（描述對照）", "代號": h["代號"], "名稱": h["名稱"], "當日報酬": fmt(h["當日報酬"]), "營收期別": fmt(h["營收期別"]), "年增": fmt(h["年增"]),
                     "是否跌停": ("" if h["是否跌停"] is None else ("是" if h["是否跌停"] else "否")), "產業": "",
                     "備註": f"來源 {h['來源']}；年增>0={'是' if np.isfinite(h['年增']) and h['年增'] > 0 else '否'}"})
    outdf = pd.DataFrame(rows, columns=COLS).astype(object)      # 一律 object ⇒ 浮點寫全精度（同 10/15 版；F 有檔時欄位不會變成 float 被 %.6f 截）
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + ".tmp"
    outdf.to_csv(tmp, index=False, encoding="utf-8-sig", float_format="%.6f")
    os.replace(tmp, out)
    J = {"sha": sha, "財報籌碼sha": (fsha or sha) if f8 else None, "資料日": str(T_DATE.date()), "輸出": out, "統計": st, "C 檔數": len(Csel),
         "C 跌停數": int(sum(res[s]["dn"] for s in Csel)), "C+ 檔數": len(Cp), "C 年增缺": int(sum(not np.isfinite(REV[s][1]) for s in Csel)),
         "C 最淺跌幅": float(rets[o[ns - 1]]), "E 產業": [inv[w] for w in worst], "E 檔數": len(Esel),
         "E 各產業": {inv[w]: int((dfo["ii"] == w).sum()) for w in worst}, "產業最差六": gtab[["產業", "mean", "count"]].to_dict("records"),
         "F": f_codes, "F 來源": (md or "f_codes"), "ETF": etf, "營收資訊": rinfo, "產業來源計數（母體）": pd.Series(isrc).value_counts().to_dict(),
         "F8候選欄": tag8 if F8sel else None, "F8前n": [r["sid"] for r in F8sel], "F8": f8info,
         "F9候選欄": tag9 if F9sel else None, "F9前n": [r["sid"] for r in F9sel], "F9": f9info, "持股列": len(hold), "耗時秒": round(time.time() - T0)}
    log(json.dumps(J, ensure_ascii=False, default=str))
    return J


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--sha", required=True); ap.add_argument("--md", default=None)
    ap.add_argument("--f", default=None, help="F 代號（逗號分隔；給了就不讀 md；空字串＝0 檔）")
    ap.add_argument("--fsha", default=None, help="財報／法人／融資／集保的 sha（預設 ＝ --sha）")
    ap.add_argument("--out", default=None); ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--nof8", action="store_true", help="F8、F9 都不算（只 A～F）"); ap.add_argument("--nof9", action="store_true", help="只不算 F9")
    ap.add_argument("--f8n", type=int, default=F8N, help=f"F8 檔數（預設 {F8N}；3 ＝ 舊版 F8top3）")
    ap.add_argument("--f9n", type=int, default=F9N, help=f"F9 檔數（預設 {F9N}）")
    ap.add_argument("--feat", default=None, help="另寫 C+ 逐檔 F6／F7／Q／F8／F9 分數表（稽核用）")
    a = ap.parse_args()
    fc = None if a.f is None else [x for x in a.f.split(",") if x.strip()]
    make_candidates(a.date, a.sha, md=a.md, f_codes=fc, fsha=a.fsha, out=a.out, procs=a.procs, f8=not a.nof8,
                    f8n=a.f8n, f9=not a.nof9, f9n=a.f9n, feat_out=a.feat)


if __name__ == "__main__":
    main()

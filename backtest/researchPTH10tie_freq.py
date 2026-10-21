# -*- coding: utf-8 -*-
"""高10 同分改排序 T1／T2／T3【頻率表・乾跑】（裁定 seq433、seq434；台股正式登錄未到，先依兩信字面做，登錄到後回測線再核對）——回測線計算子代理，2026-10-21。
⛔ 不算任何報酬（seq366：只准不含報酬欄的乾跑）：不讀、不存、不印任何進場後價格、R、組合淨值；輸出沒有任何報酬欄。
⛔ 不改既有檔、只新增；⛔ 不寫第二份實作：researchPTHpf（build_world、load_events、keep_order）、researchPTHn（set_ns、NS0）、researchPTH（stock_job）、
   researchPTH10seed（events_with、seed_of、tie_stats、same_arr、SEED0）、researchMktDrop_fund（uni_job／run_jobs、load_fin、fin_feats、
   fin7、rev7、load_tdcc、tdcc_chg、add_scores、f7_scores、universe_sids）、researchMktDrop_quality（load_fin、fin_q、load_div、div_q、add_q）、
   researchMktDrop_f9（add_f9）、researchExit5（load_revenue、avail_pos、rev_events）只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10tie_freq [--procs 4] [--dry]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10tie_freq_check
輸出 backtest/resultsPTH10tie/freq/：freq.json、freq.csv、avail.csv、avail_by_year.csv、missing_sub.csv、overlap.csv、spearman.csv、
    monthly_<世界>.csv、members_<世界>.csv.gz、run.log

═══ 讀法（★＝執行者定；〔 〕內為另一讀法；寫死於第一次正式執行前，2026-10-21 台北）═══
 B0 高10 其餘全照前瞻 seq4（＝ researchPTHn N10：跳月各批事件 resultsPTH/events/trades_<世界>_跳月、PTH 由高往下、10 格、6 個月、空位 0050）。
    唯一更動 ＝ 同 PTH（同一批、PTH 值完全相同）的先後：原 ＝ rk（default_rng([20261023, 形成月序 j])）；
    新 ＝ lexsort((rk, −分數, 算不出旗標, −PTH, 進場日))＝「同 PTH 內：算得出者依分數、算不出者排最後、仍同分才用原 rk」。
 B1 ★ 排序日 t ＝ 形成月底（seq4「每月底收盤後排 PTH」）；所有排序欄只用 ≤ t 可得的資料（財報 ＜ t、月營收可得位置 ≤ t、集保可用日 ≤ t、價量 ≤ t 收盤）。
 B2 ★ 同分群 ＝ 同一批（進場日）內 PTH 值完全相同、成員 ≥ 2 的每一組（多半是 PTH＝1 組）；名次在「全組成員」內算（不扣已持有；買進時才跳過已持有）。
 T1 F9 ＝ 大跌 4 檔 F9（mktdrop_cands.f8_rank／q_scores／f9_rank 同式）：
    F6 ＝ 22 子項（營收 3、獲利 4、未來性 3、籌碼 6、線型 6）百分位等權、缺值 0 分（FU.add_scores）；★ 百分位改在【同分群】內算（原：大跌日 C+ 內）。
       子項逐檔取法照 f8_rank 逐行：rv_yoy ＝ 可得位置 ≤ t 的最新一期年增（EX5.rev_events）、rv_yoy3、rv_hi24、FU.fin_feats、uni_job（tc_ma120、ch_*、chk_r60／r20／ma60／d52）、
       集保 4 週變化；★ tc_drop ＝ −（排序日 t 當天報酬）（原：大跌日跌幅；照字面搬，方向「跌越深分越高」沿用）。
    F7 ＝ 情報 F7 凍結規則：細項百分位在【大母體】算（t 有效收盤 ∧ 前 20 日均成交金額 ≥ 5,000 萬的四碼普通股；FU.f7_scores）——與原同。
    Q ＝ 6 子項百分位等權、缺值 0 分（QL.add_q）；★ 百分位改在【同分群】內算（原：C+ 內）。
    F6、F7、Q 先取 6 位有效數字（同 mktdrop_cands）；★ F9 可算 ⇔ F6、F7、Q 三套各至少有一個子項有值（原 F9 研究：Q 無早年財報 ⇒ 2006～2014「標缺」）；
    F9 ＝ 同分群內【可算者】的 F6、F7、Q 名次百分位相加（F9.add_f9，四捨五入 1e−6）；F9 同分 ⇒ 原 rk（★ 不用原 F9 的「F7 高者 ⇒ 代號」決勝，照 seq433「仍同分才隨機」）。
    另報 T1寬（描述）：沿用原程式「缺值 0 分／50 分」⇒ 每檔都算得出、全組成員一起排名次；看它與 T1 的重疊。
 T2 ★ 營收年增 ＝ 可得位置 ≤ t 的最新一期月營收年增（EX5.avail_pos：≤2025-12 期次月 10 日後、≥2026-01 期次月 15 日後第一個交易日；去年同月 ≤ 0 ⇒ 算不出）高→低。
    月營收來源 ＝ 世界資料夾（主 h2data edc6f8 2015-01 起；早年 earlydata eotc 2003-01 起）。
 T3 ★ 60 日波動 ＝ t 往回 60 個市場交易日（t−59～t）的日報酬（快取還原收盤 W["C"]；兩端都有成交、兩端都不是壞根才算）標準差（ddof＝1），有效 ≥ 40 個才算；低→高。
    MAX（描述）＝ t−19～t 的單日報酬最大值，有效 ≥ 15 個才算；低→高。
 C1 財報可用日：FU／QL.load_fin 原為「同期全部文件最早 uploaded_at」；★ 本件依全線 seq352 口徑覆寫為「同期有 AI1 ⇒ AI1 最早，否則全部最早」（只會變晚、不會變早；
    改到的季列數照報）；無時戳 ⇒ 沿用原程式法定期限（F6、Q）／B、C 給 50（F7）。配息 ＝ h2data 4b26f6 data/adj（QL 原設定；除息日 ＜ t）。
 C2 路徑：★ 只用【原種子已提交路徑】（resultsPTHn/trades_<世界>_N10 的 sid、買進日、賣出日三欄；⛔ 不讀報酬欄）＝ 每月補幾格、當時持有中哪些檔。
    ⚠ 換排序後的「自己路徑」⛔ 不算：試過零報酬世界（價格全 1、R 全 0）跑原引擎 ⇒ 主世界 223 筆 ≠ 原 221 筆（12 筆不同）——
       每月能補幾格取決於 0050 可撥金額，而那取決於持股漲跌 ⇒ 不跑真實報酬就無法得到各排序自己的路徑；本表因此全部以原路徑為條件。
    ⭐ 閘：由三欄重建的路徑 ⇒ PS.tie_stats ＝ resultsPTH10seed/ties_<世界>.csv 逐字；且每月實買 ＝ 可買者依原 rk 排序前 k（逐批斷言）。
 C3 段 ＝ 進場日落在 探索 [2017-03-02, 2021-12-30]、確認 [2022-01-03, 資料尾]、早年 [2005 首日, 2014-12-31]；主另報全窗（含 2016-03～2017-02 暖身批次）。
 C4 重疊（全部靜態、以原路徑為條件）：① 補格 ＝ 原路徑每月「可買者」（扣當時持有中、當天賣出者）依該排序取前 k 名（k ＝ 原路徑當月買進格數），
    兩排序之間 Σ∩÷Σk；對原抽籤另附 200 組種子（default_rng([20261021, k, j])）同式分布；② 前 10 名（不看持有）＝ 每批依該排序的前 10 名 Σ∩÷Σ10。
 C5 等價／退化檢查（seq377）：任兩排序（含原抽籤）補格重疊 ≥ 90% ⇒ 標「近乎等價」；需抽月邊界組可算比例 ＜ 50% ⇒ 標「可算比例低」；
    需抽月中切點兩側（第 k 名與第 k＋1 名）排序鍵仍相同 ≥ 50% ⇒ 標「仍靠抽籤」；開頭先報。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHn as PN                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchPTH10seed as PS                # noqa: E402

from backtest import researchMktDrop_fund as FU             # noqa: E402
from backtest import researchMktDrop_quality as QL          # noqa: E402
from backtest import researchMktDrop_f9 as F9               # noqa: E402
from backtest import researchExit5 as EX5                   # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10tie/freq"
SEEDDIR = PS.OUT
N = 10
NSEED = PS.NSEED
SEGS = {"主": ("探索", "確認", "主全窗"), "早年": ("早年",)}
ORD = ["原", "T1", "T2", "T3", "MAX", "T1寬"]
ORDNAME = {"原": "原種子抽籤 [20261023, j]", "T1": "T1 F9 高→低（同分群內名次）", "T2": "T2 營收年增 高→低", "T3": "T3 60 日波動 低→高",
           "MAX": "MAX 20 日最大單日漲幅 低→高（描述）", "T1寬": "T1寬 F9 缺值照原程式給分（描述）"}
VOLN, VOLMIN, MAXN, MAXMIN = 60, 40, 20, 15
EQV, LOWAV = 0.90, 0.50
F7KEYS = list(FU.F7SUB)
F6KEYS = list(FU.SC["F6"])
QKEYS = list(QL.SUBS)


def g6(x):
    return float(f"{x:.6g}") if np.isfinite(x) else np.nan


# ═════════════ 財報可用日 AI1 覆寫（C1）═════════════
def ai1_table(xd):
    fd = pd.read_csv(os.path.join(xd, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["qk"] = [FU.qkey(a, b) for a, b in zip(fd["year"], fd["season"])]
    allmin = fd.groupby(["stock_id", "qk"])["d"].min()
    ai1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "qk"])["d"].min()
    m = allmin.copy(); m.loc[ai1.index] = ai1
    return m, allmin


def ai1_patch(FIN, m):
    """FIN（FU／QL.load_fin 輸出）中 src＝t57sb01 的季，可用日改為 AI1 優先最早；回 (改到列數, 最大延後天數)。"""
    md = {k: np.datetime64(v, "ns") for k, v in m.items()}
    n = 0; mx = 0
    for s, g in FIN.items():
        av = g["avail"].copy()
        for i, (k, src) in enumerate(zip(g["qk"], g["src"])):
            if src == "t57sb01":
                v = md.get((s, int(k)))
                if v is not None and v != av[i]:
                    if v < av[i]:
                        raise SystemExit(f"⛔ AI1 覆寫變早 {s} {k}")
                    mx = max(mx, int((v - av[i]) / np.timedelta64(1, "D"))); av[i] = v; n += 1
        g["avail"] = av
    return n, mx


# ═════════════ 排序 ═════════════
def order_of(ev, flag, score):
    """⇒ 全部事件的順序：進場日、PTH 降冪、可算者先、分數降冪、原 rk。flag ＝ True 表算不出。"""
    sc = np.where(flag, 0.0, score)
    return np.lexsort((ev["rk"], -sc, flag.astype(np.int8), -ev["pth"], ev["e"]))


def path_from_trades(W, ev, wn):
    """原種子已提交路徑（C2）：resultsPTHn/trades_<世界>_N10 只讀 sid、形成月底、買進日、賣出日 ⇒ S（buys／sells 以 ev 索引；q、j 為恆等對照）。"""
    tf = pd.read_csv(os.path.join(PN.OUT, f"trades_{wn}_N10.csv.gz"), dtype=str, keep_default_na=False, usecols=["sid", "形成月底", "買進日", "賣出日"])
    key = {(str(s), str(f)): q for q, (s, f) in enumerate(zip(ev["sid"], ev["form"]))}
    dpos = {d: i for i, d in enumerate(W["dates"])}
    buys, sells = [], []
    for s, f, b, x in zip(tf["sid"], tf["形成月底"], tf["買進日"], tf["賣出日"]):
        q = key[(s, f)]
        if dpos[b] != int(ev["e"][q]):
            raise SystemExit(f"⛔ {wn} 交易檔買進日 ≠ 事件進場日 {s} {f}")
        buys.append((dpos[b], q, 0.0))
        if x != "":
            sells.append((dpos[x], q, 0.0, 0.0))
    buys.sort(); sells.sort()
    nev = len(ev["e"])
    return {"buys": buys, "sells": sells, "q": np.arange(nev), "j": ev["j"]}


def path_info(W, ev, S):
    """每批：可買候選（扣持有中、當天賣出）與實買 ev 索引。"""
    n0 = W["n0"]
    sl = {q: t for t, q, a_, b_ in S["sells"]}
    iv = [(int(S["j"][q]), int(t), int(sl.get(q, n0 + 1))) for t, q, _ in S["buys"]]
    bought = defaultdict(list)
    for t, q, _ in S["buys"]:
        bought[int(t)].append(int(S["q"][q]))
    out = {}
    for e in np.unique(ev["e"]):
        e = int(e)
        blk = {j for j, tb, ts in iv if tb < e and ts >= e}
        idx = np.flatnonzero(ev["e"] == e)
        ok = idx[[int(ev["j"][q]) not in blk for q in idx]]
        out[e] = (ok, sorted(bought.get(e, [])))
    return out


def cut_stats(ev, PI, pos, flag, score, strict=False):
    """各批（原路徑有買進）：可買者依該排序取前 k（k ＝ 原路徑實買數；strict ⇒ 斷言 ＝ 實買）；需抽 ＝ 第 k＋1 名與第 k 名同 PTH；
    仍隨機 ＝ 兩者同（旗標、分數）。"""
    rows = {}
    for e, (ok, bq) in PI.items():
        k = len(bq)
        r = {"買進格數": k, "需抽": False, "切點仍隨機": False, "切點兩側皆算不出": False, "入選算不出格數": 0, "邊界組可買": 0, "邊界組可算": 0}
        if k > 0:
            srt = ok[np.argsort(pos[ok], kind="stable")]
            if strict and sorted(srt[:k].tolist()) != bq:
                raise SystemExit(f"⛔ 原路徑實買 ≠ 可買者依原排序前 k（進場日位置 {e}）")
            v = ev["pth"][srt[k - 1]]
            G = srt[ev["pth"][srt] == v]
            r["邊界組可買"] = int(len(G)); r["邊界組可算"] = int((~flag[G]).sum())
            r["入選算不出格數"] = int(flag[srt[:k]].sum())
            if k < len(srt) and ev["pth"][srt[k]] == v:
                a_, b_ = srt[k - 1], srt[k]
                r["需抽"] = True
                r["切點仍隨機"] = bool(flag[a_] == flag[b_] and (flag[a_] or score[a_] == score[b_]))
                r["切點兩側皆算不出"] = bool(flag[a_] and flag[b_])
        rows[e] = r
    return rows


def topk_static(ev, PI, pos):
    """補格（靜態）：每批可買者依排序前 k（k ＝ PI 實買數）⇒ {e: set(ev 索引)}。"""
    out = {}
    for e, (ok, bq) in PI.items():
        if bq:
            out[e] = set(ok[np.argsort(pos[ok], kind="stable")][:len(bq)].tolist())
    return out


def top10_static(ev, pos):
    out = {}
    for e in np.unique(ev["e"]):
        idx = np.flatnonzero(ev["e"] == e)
        out[int(e)] = set(idx[np.argsort(pos[idx], kind="stable")][:N].tolist())
    return out


def seg_of(W, wn, e):
    out = []
    for sg in SEGS[wn]:
        if sg == "主全窗":
            out.append(sg); continue
        x, y = W["segp"][sg]
        if x <= e <= y:
            out.append(sg)
    return out


# ═════════════ 分數（T1 F9、T2、T3）═════════════
def vol_feats(W, s, p):
    i = W["ix"][s]; C = W["C"][i]; T_ = W["TRD"][i]; bad = W["BADPOS"].get(s, set())
    out = {}
    for nm, L, mn in (("vol60", VOLN, VOLMIN), ("max20", MAXN, MAXMIN)):
        r = []
        for d in range(p - L + 1, p + 1):
            if d - 1 < 0:
                continue
            if T_[d] and T_[d - 1] and d not in bad and (d - 1) not in bad and np.isfinite(C[d]) and np.isfinite(C[d - 1]) and C[d - 1] > 0:
                r.append(C[d] / C[d - 1] - 1.0)
        out[nm + "_n"] = len(r)
        if len(r) >= mn:
            out[nm] = float(np.std(r, ddof=1)) if nm == "vol60" else float(np.max(r))
        else:
            out[nm] = np.nan
    return out


def date_scores(X, t, mem, grp_of, FIN, QFIN):
    """X：情境（W、BR、rev、rly、AV、AVA、TD、DV、mkd、smk）；t：排序日；mem：同分群成員代號；grp_of：代號 ⇒ 組號。
    ⇒ 每檔一列：F6 子項與 F6、F7 細項與 F7、Q 子項與 Q（未取 6 位）、T2、稽核欄。＝ mktdrop_cands.f8_rank／q_scores 逐行（只把 C+ 換成同分群、多日共用逐股結果）。"""
    W = X["W"]; cal = W["cal"]; n0 = W["n0"]; data = W["data"]; BR = X["BR"]
    rev, rly, AV, AVA, TD = X["rev"], X["rly"], X["AV"], X["AVA"], X["TD"]
    TP = int(cal.searchsorted(t)); assert TP < n0 and cal[TP] == t
    ds = str(t.date())
    rows = []
    for sid in mem:
        b = BR[(sid, ds)]
        E = [e for e in EX5.rev_events(sid, rev, rly, AV, n0) if e[0] <= TP]
        r1 = b["chk_ret1"]; yoy = E[-1][1] if E else np.nan
        f = {"sid": sid, "grp": grp_of[sid], "事件日": ds, "ret1": float(r1), "rv_yoy": float(yoy)}
        last3 = [e[1] for e in E[-3:]]
        f["rv_yoy3"] = float(np.mean(last3)) if len(last3) == 3 and np.isfinite(last3).all() else np.nan
        f["rv_hi24"] = (np.nan if (not E or E[-1][2] is None) else float(E[-1][2])); f["yoy_chk"] = E[-1][1] if E else np.nan
        f["rev_avail_pos"] = int(E[-1][0]) if E else -1
        f.update(FU.fin_feats(FIN.get(sid), t))
        for k in ("tc_ma120", "ch_i1", "ch_i5", "ch_i20", "ch_t20", "ch_mu"):
            f[k] = b[k]
        f["tc_r60"] = b["chk_r60"]; f["tc_rs"] = b["chk_r20"]; f["tc_ma60"] = b["chk_ma60"]; f["tc_d52"] = b["chk_d52"]; f["tc_drop"] = -float(r1)
        f["ret1_chk"] = b["chk_ret1"]
        f["ch_big"], f["tdcc_date"] = FU.tdcc_chg(TD, sid, t, 4)
        rows.append(f)
    d = pd.DataFrame(rows)
    d = FU.add_scores(d, "grp")
    us = FU.universe_sids(data, ds, ds)
    cps = set(d["sid"]); rr = []
    for s in sorted(set(us) | cps):
        b = BR.get((s, ds))
        inU = bool(s in us and b.get("valid") == 1.0 and np.isfinite(b.get("amt20", np.nan)) and b["amt20"] >= 5e7)
        if not inU and s not in cps:
            continue
        r = {"事件日": ds, "sid": s, "inU": inU, "inC": s in cps, "e1": b["e1"], "e2": b["e2"], "d1": b["d1"], "d2": b["d2"]}
        r.update(FU.rev7(s, rev, rly, AVA, TP)); r.update(FU.fin7(FIN.get(s), t)); r["d3"], _ = FU.tdcc_chg(TD, s, t, 1)
        rr.append(r)
    T = pd.DataFrame(rr); T = FU.f7_scores(T, T["inU"].to_numpy(bool))
    d = d.merge(T[T["inC"]][["sid", "inU"] + F7KEYS + ["fin_ind", "f7_fin_q", "F7A", "F7B", "F7C", "F7D", "F7E", "F7"]], on="sid", how="left")
    d["大母體檔數"] = int(T["inU"].sum())
    # Q（＝ q_scores）
    Wq = pd.DataFrame({"sid": list(d["sid"])}); Wq["grp"] = d["grp"].to_numpy()
    FQ = pd.DataFrame([QL.fin_q(QFIN.get(s), t) for s in Wq["sid"]], index=Wq.index)
    for c in FQ.columns:
        Wq[c] = FQ[c]
    dv = [QL.div_q(X["DV"], X["mkd"], X["smk"], s, t) for s in Wq["sid"]]
    Wq["q_div"] = [x[0] for x in dv]; Wq["q_divsrc"] = [x[1] for x in dv]
    Wq = QL.add_q(Wq, "grp")
    d = d.merge(Wq[["sid", "Q", "q_nmiss", "q_finq", "q_finsrc", "q_divsrc"] + QKEYS], on="sid", how="left")
    return d


def f9_cols(D_):
    """D_：全部成員（已有 F6、F7、Q）⇒ 加 has6／has7／hasQ、F9ok、F9（嚴：可算者內）、F9寬（全員）。"""
    D_ = D_.copy()
    for c in ("F6", "F7", "Q"):
        D_[c + "_g6"] = [g6(x) for x in D_[c].to_numpy(float)]
    D_["has6"] = D_[F6KEYS].notna().any(axis=1)
    D_["has7"] = D_[F7KEYS].notna().any(axis=1)
    D_["hasQ"] = D_["q_nmiss"] < len(QKEYS)
    D_["F9ok"] = D_["has6"] & D_["has7"] & D_["hasQ"]
    base = D_[["q", "grp", "F6_g6", "F7_g6", "Q_g6"]].rename(columns={"F6_g6": "F6", "F7_g6": "F7", "Q_g6": "Q"})
    s1 = F9.add_f9(base[D_["F9ok"].to_numpy()].copy(), "grp")
    s2 = F9.add_f9(base.copy(), "grp")
    D_["F9"] = D_["q"].map(dict(zip(s1["q"], s1["F9"])))
    D_["F9寬"] = D_["q"].map(dict(zip(s2["q"], s2["F9"])))
    return D_


# ═════════════ 主流程 ═════════════
def world(wn, a, log, J):
    W = M.build_world(wn, log)
    t0 = time.time(); RES = {}
    with Pool(a.procs) as pool:
        for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
            if r is not None:
                RES[sid] = r
    log(f"[{wn}] 逐股（事件重建閘用）完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
    ev, info = PS.events_with(W, wn, RES, PS.SEED0)
    nev = len(ev["e"])
    for k_ in ("R", "px", "P"):                                       # ⛔ 不用任何價格／報酬欄
        ev[k_] = None
    # ── 原種子已提交路徑 ＋ 閘（C2）
    o0 = np.lexsort((ev["rk"], -ev["pth"], ev["e"]))
    if not np.array_equal(o0, order_of(ev, np.zeros(nev, bool), np.zeros(nev))):
        raise SystemExit("⛔ order_of(全 0) ≠ researchPTHn.run_slot 順序")
    S0 = path_from_trades(W, ev, wn)
    J["對帳"][f"{wn}|原路徑 ＝ resultsPTHn/trades_{wn}_N10（只讀 sid／形成月底／買進日／賣出日）"] = f"{len(S0['buys'])} 筆買進、{len(S0['sells'])} 筆賣出；買進日 ＝ 事件進場日"
    TS0 = PS.tie_stats(W, ev, S0, wn)
    txt = TS0.to_csv(index=False, float_format="%.10g")
    ref = open(os.path.join(SEEDDIR, f"ties_{wn}.csv"), encoding="utf-8-sig").read()
    if txt != ref:
        raise SystemExit(f"⛔ {wn} tie_stats 重建 ≠ resultsPTH10seed/ties_{wn}.csv")
    J["對帳"][f"{wn}|同分重建 PS.tie_stats vs resultsPTH10seed/ties_{wn}.csv"] = f"逐字相同（{len(TS0)} 批）"
    PI0 = path_info(W, ev, S0)
    pos0 = np.empty(nev, np.int64); pos0[o0] = np.arange(nev)
    cut_stats(ev, PI0, pos0, np.zeros(nev, bool), np.zeros(nev), strict=True)
    J["對帳"][f"{wn}|原路徑每月實買 ＝ 可買者依原 rk 排序前 k（逐批斷言）"] = "全過"
    # ── 200 組種子（參考分布；只換 rk、靜態）
    SEEDREF = []; t0 = time.time()
    for k in range(1, NSEED + 1):
        evk, _ = PS.events_with(W, wn, RES, PS.seed_of(k))
        for k_ in ("R", "px", "P"):
            evk[k_] = None
        for key in ("sid", "e", "pth", "j", "form"):
            if not PS.same_arr(evk[key], ev[key]):
                raise SystemExit(f"⛔ 種子 {k} 事件欄 {key} 不同")
        ok_ = np.lexsort((evk["rk"], -evk["pth"], evk["e"]))
        posk = np.empty(nev, np.int64); posk[ok_] = np.arange(nev)
        stk = topk_static(evk, PI0, posk)
        row = {"k": k}
        for sg in SEGS[wn]:
            es = [e for e in stk if sg in seg_of(W, wn, e)]
            row[f"{sg}|補格"] = sum(len(stk[e] & set(PI0[e][1])) for e in es) / max(sum(len(PI0[e][1]) for e in es), 1)
        SEEDREF.append(row)
        if k % 50 == 0:
            log(f"[{wn}] 種子 {k}/{NSEED}｜{time.time() - t0:.0f}s")
    del RES
    SR = pd.DataFrame(SEEDREF)
    # ── 同分群
    grp = np.full(nev, -1, np.int64); gid = 0; GR = []
    for e in np.unique(ev["e"]):
        idx = np.flatnonzero(ev["e"] == e)
        for v, c in Counter(ev["pth"][idx].tolist()).items():
            if c >= 2:
                mm = idx[ev["pth"][idx] == v]; grp[mm] = gid; GR.append((gid, int(e), float(v), int(c))); gid += 1
    log(f"[{wn}] 同分群 {gid} 組、成員 {int((grp >= 0).sum())}／事件 {nev}")
    # ── 分數資料
    forms = sorted({ev["form"][q] for q in np.flatnonzero(grp >= 0)})
    t0 = time.time()
    FU._G["cal"] = {W["data"]: W["cal"]}
    allu = FU.universe_sids(W["data"], forms[0], forms[-1])
    memsids = sorted({str(ev["sid"][q]) for q in np.flatnonzero(grp >= 0)})
    sids_all = sorted(set(allu) | set(memsids))
    mkt = {s: W["mk"].get(s, allu.get(s, "twse")) for s in sids_all}
    BR = FU.run_jobs([(W["data"], s, mkt[s], forms) for s in sids_all], a.procs, wn)
    log(f"[{wn}] uni_job {len(sids_all)} 檔 × {len(forms)} 排序日｜{time.time() - t0:.0f}s")
    FIN, finfo = FU.load_fin(); QFIN, qinfo = QL.load_fin()
    am, _ = ai1_table(FU.XD)
    n6, m6 = ai1_patch(FIN, am); nq, mq = ai1_patch(QFIN, am)
    J["AI1覆寫"][wn] = {"fund load_fin 改到季列": n6, "最大延後天": m6, "quality load_fin 改到季列": nq, "最大延後天(Q)": mq}
    TD, tdd = FU.load_tdcc()
    DV, mkd, smk = QL.load_div()
    rev, rly, rinfo = EX5.load_revenue(W["data"])
    AV = EX5.avail_pos(list(rev.index), W["cal"]); AVA = np.array([AV[p] for p in rev.index], np.int64)
    J["資料"][wn] = {"月營收": rinfo, "財報(fund)": {k: v for k, v in finfo.items() if k != "無時戳占比（依年）"}, "財報無時戳占比(fund,依年)": finfo["無時戳占比（依年）"],
                    "集保週": f"{pd.Timestamp(tdd[0]).date()}～{pd.Timestamp(tdd[-1]).date()}", "配息": QL.ADJ, "財報籌碼": FU.XD, "價量": W["data"]}
    X = {"W": W, "BR": BR, "rev": rev, "rly": rly, "AV": AV, "AVA": AVA, "TD": TD, "DV": DV, "mkd": mkd, "smk": smk}
    parts = []; t0 = time.time()
    for f_ in forms:
        qs = np.flatnonzero((grp >= 0) & (ev["form"] == f_))
        sids = [str(ev["sid"][q]) for q in qs]
        if len(set(sids)) != len(sids):
            raise SystemExit(f"⛔ {f_} 同批同檔重複")
        d = date_scores(X, pd.Timestamp(f_), sids, {s: int(grp[q]) for s, q in zip(sids, qs)}, FIN, QFIN)
        d["q"] = d["sid"].map(dict(zip(sids, qs.tolist())))
        p = int(W["cal"].searchsorted(pd.Timestamp(f_)))
        V = pd.DataFrame([vol_feats(W, s, p) for s in d["sid"]], index=d.index)
        for c in V.columns:
            d[c] = V[c]
        parts.append(d)
    MB = f9_cols(pd.concat(parts, ignore_index=True))
    MB["進場日"] = [W["dates"][ev["e"][q]] for q in MB["q"]]; MB["形成月底"] = [ev["form"][q] for q in MB["q"]]
    MB["PTH"] = [ev["pth"][q] for q in MB["q"]]
    MB["rev_avail_date"] = [W["dates"][p] if 0 <= p < W["n0"] else "" for p in MB["rev_avail_pos"]]
    log(f"[{wn}] 分數 {len(MB)} 列｜{time.time() - t0:.0f}s")
    # ── 各排序鍵
    KEY = {"原": (np.zeros(nev, bool), np.zeros(nev))}
    qv = MB["q"].to_numpy(np.int64)

    def arr(col, neg=False):
        v = np.full(nev, np.nan); v[qv] = MB[col].to_numpy(float) * (-1 if neg else 1)
        return v
    for nm, col, neg in (("T1", "F9", False), ("T2", "rv_yoy", False), ("T3", "vol60", True), ("MAX", "max20", True), ("T1寬", "F9寬", False)):
        v = arr(col, neg); fl = ~np.isfinite(v); fl[grp < 0] = False; v[grp < 0] = 0.0
        KEY[nm] = (fl, np.where(np.isfinite(v), v, 0.0))
    POS, CUT = {}, {}
    for nm in ORD:
        o_ = order_of(ev, *KEY[nm]); pos = np.empty(nev, np.int64); pos[o_] = np.arange(nev); POS[nm] = pos
        CUT[nm] = cut_stats(ev, PI0, pos, *KEY[nm], strict=(nm == "原"))
    # cut_stats 需抽 ＝ tie_stats 需抽（原路徑）
    tsd = dict(zip(TS0["進場日"], TS0["需抽"]))
    if any(bool(tsd[W["dates"][e]]) != r["需抽"] for e, r in CUT["原"].items()):
        raise SystemExit("⛔ cut_stats 需抽 ≠ tie_stats 需抽")
    J["對帳"][f"{wn}|cut_stats 需抽 ＝ tie_stats 需抽（原路徑）"] = "全批相同"
    # ── 每月表
    mon = []
    for e in sorted(PI0):
        tr0 = TS0[TS0["進場日"] == W["dates"][e]].iloc[0]
        qs = np.flatnonzero((ev["e"] == e) & (grp >= 0))
        r = {"世界": wn, "進場日": W["dates"][e], "形成月底": ev["form"][np.flatnonzero(ev["e"] == e)[0]], "段": "／".join(seg_of(W, wn, e)),
             "候選": int(tr0["候選"]), "PTH=1組": int(tr0["PTH=1組"]), "同分組數(≥2)": int(tr0["同分組數(≥2)"]), "同分群成員": int(len(qs))}
        mm = MB[MB["q"].isin(qs)]
        for c, cc in (("F9可算", "F9ok"), ("F6有值", "has6"), ("F7有值", "has7"), ("Q有值", "hasQ")):
            r[c] = int(mm[cc].sum())
        r["T2可算"] = int(np.isfinite(mm["rv_yoy"]).sum()); r["T3可算"] = int(np.isfinite(mm["vol60"]).sum()); r["MAX可算"] = int(np.isfinite(mm["max20"]).sum())
        for nm in ORD:
            c_ = CUT[nm][e]
            r[f"{nm}|買進格數"] = c_["買進格數"]; r[f"{nm}|需抽"] = c_["需抽"]; r[f"{nm}|邊界組可買"] = c_["邊界組可買"]
            r[f"{nm}|邊界組可算"] = c_["邊界組可算"]; r[f"{nm}|切點仍隨機"] = c_["切點仍隨機"]; r[f"{nm}|入選算不出格數"] = c_["入選算不出格數"]
        mon.append(r)
    MON = pd.DataFrame(mon)
    MON.to_csv(os.path.join(OUT, f"monthly_{wn}.csv"), index=False, encoding="utf-8-sig")
    keep = ["q", "形成月底", "進場日", "sid", "grp", "PTH", "F9ok", "has6", "has7", "hasQ", "F6", "F7", "Q", "F6_g6", "F7_g6", "Q_g6", "F9", "F9寬",
            "rv_yoy", "rev_avail_date", "vol60", "vol60_n", "max20", "max20_n", "q_nmiss", "fin_q", "fin_src", "q_finq", "q_finsrc", "q_divsrc", "f7_fin_q",
            "tdcc_date", "inU", "大母體檔數"] + F6KEYS + F7KEYS + QKEYS
    MB[keep].to_csv(os.path.join(OUT, f"members_{wn}.csv.gz"), index=False, float_format="%.10g", encoding="utf-8", compression="gzip")
    # ── 彙總
    FR, AVL, AVY, MIS, OVL, SPR = [], [], [], [], [], []
    for sg in SEGS[wn]:
        es = [e for e in sorted(PI0) if sg in seg_of(W, wn, e)]
        T = TS0[TS0["進場日"].isin([W["dates"][e] for e in es]) & (TS0["候選"] > 0)]
        Tb = T[T["買進格數"] > 0]; Td = Tb[Tb["需抽"]]
        Ms = MON[MON["進場日"].isin(T["進場日"])]
        fr = {"世界": wn, "段": sg, "批次(月)": len(T), "候選中位": float(T["候選"].median()), "PTH=1組大小平均": float(T["PTH=1組"].mean()),
              "PTH=1組大小中位": float(T["PTH=1組"].median()), "PTH=1組(可買)平均": float(T["PTH=1組(可買)"].mean()),
              "同分組數(≥2)平均": float(T["同分組數(≥2)"].mean()), "同分群成員平均": float(Ms["同分群成員"].mean()),
              "有買進的月": len(Tb), "每月補格數平均(全部月)": float(T["買進格數"].mean()), "每月補格數平均(有買進月)": float(Tb["買進格數"].mean()),
              "每月補格數分布": json.dumps({int(k): int(v) for k, v in sorted(Counter(T["買進格數"].astype(int)).items())}),
              "需抽月比例(有買進月)": float(Tb["需抽"].mean()), "需抽月比例(全部月)": float(Tb["需抽"].sum() / max(len(T), 1)),
              "需抽月：邊界組(可買)平均": float(Td["邊界組(可買)"].mean()), "需抽月：從邊界組抽的格數平均": float(Td["邊界組買進"].mean())}
        for nm in ORD[1:]:
            c = [CUT[nm][e] for e in es]
            cb = [x for x in c if x["買進格數"] > 0]; cd = [x for x in cb if x["需抽"]]
            fr[f"{nm}|需抽月中切點仍隨機比例"] = sum(x["切點仍隨機"] for x in cd) / max(len(cd), 1)
            fr[f"{nm}|需抽月中切點兩側皆算不出比例"] = sum(x["切點兩側皆算不出"] for x in cd) / max(len(cd), 1)
            fr[f"{nm}|入選格中算不出比例"] = sum(x["入選算不出格數"] for x in cb) / max(sum(x["買進格數"] for x in cb), 1)
        FR.append(fr)
        # 可算比例：A ＝ 全部同分群成員；B ＝ 原路徑需抽月的邊界組可買者
        qa = np.flatnonzero((grp >= 0) & np.isin(ev["e"], es))
        qb = []
        for e in es:
            ok, bq = PI0[e]
            if CUT["原"][e]["需抽"]:
                srt = ok[np.argsort(POS["原"][ok], kind="stable")]; v = ev["pth"][srt[len(bq) - 1]]
                qb += srt[ev["pth"][srt] == v].tolist()
        for lv, qq in (("A 全部同分群成員", qa), ("B 原路徑需抽月邊界組可買者", np.array(qb, np.int64))):
            mm = MB[MB["q"].isin(qq)]
            o = {"世界": wn, "段": sg, "層": lv, "檔次": len(mm)}
            for c, cc in (("F6有值(≥1子項)", "has6"), ("F7有值(≥1細項)", "has7"), ("Q有值(≥1子項)", "hasQ"), ("T1 F9可算", "F9ok")):
                o[c] = float(mm[cc].mean()) if len(mm) else np.nan
            o["F7 財報無時戳⇒B、C給50"] = float((mm["f7_fin_q"] == "無時戳⇒50").mean()) if len(mm) else np.nan
            o["Q 子項缺值數平均"] = float(mm["q_nmiss"].mean()) if len(mm) else np.nan
            o["F6 子項缺值數平均"] = float(mm[F6KEYS].isna().sum(axis=1).mean()) if len(mm) else np.nan
            o["T2 營收年增可算"] = float(np.isfinite(mm["rv_yoy"]).mean()) if len(mm) else np.nan
            o["T3 60日波動可算"] = float(np.isfinite(mm["vol60"]).mean()) if len(mm) else np.nan
            o["MAX 可算"] = float(np.isfinite(mm["max20"]).mean()) if len(mm) else np.nan
            AVL.append(o)
        mA = MB[MB["q"].isin(qa)]
        for fam, keys in (("F6", F6KEYS), ("F7", F7KEYS), ("Q", QKEYS)):
            for c in keys:
                MIS.append({"世界": wn, "段": sg, "套": fam, "子項": c, "名稱": FU.SUBNAME.get(c) or FU.F7SUB.get(c) or QL.SUBNAME.get(c),
                            "缺值率": float(mA[c].isna().mean()) if len(mA) else np.nan})
        # 重疊
        STK = {nm: topk_static(ev, PI0, POS[nm]) for nm in ORD}
        T10 = {nm: top10_static(ev, POS[nm]) for nm in ORD}
        esk = [e for e in es if PI0[e][1]]
        for x_ in ORD:
            for y_ in ORD:
                if x_ == y_:
                    continue
                o = {"世界": wn, "段": sg, "A": x_, "B": y_, "Σk": sum(len(PI0[e][1]) for e in esk),
                     "補格 Σ∩÷Σk": sum(len(STK[x_][e] & STK[y_][e]) for e in esk) / max(sum(len(PI0[e][1]) for e in esk), 1),
                     "前10名 Σ∩÷Σ10": sum(len(T10[x_][e] & T10[y_][e]) for e in es) / max(sum(len(T10[x_][e]) for e in es), 1)}
                if y_ == "原":
                    for col, sc in (("補格 Σ∩÷Σk", f"{sg}|補格"),):
                        v = SR[sc]
                        o[col.split(" ")[0] + "｜200組種子對原 中位"] = float(v.median())
                        o[col.split(" ")[0] + "｜200組 p5"] = float(v.quantile(.05)); o[col.split(" ")[0] + "｜200組 p95"] = float(v.quantile(.95))
                        o[col.split(" ")[0] + "｜在200組中百分位(≤)"] = float((v <= o[col]).mean())
                OVL.append(o)
        # 同分群內 Spearman（各組 ≥ 5 檔兩邊都有值）
        mS = mA.assign(nvol=-mA["vol60"], nmax=-mA["max20"])
        for a_, b_ in (("F9", "rv_yoy"), ("F9", "nvol"), ("rv_yoy", "nvol"), ("nvol", "nmax"), ("F9", "nmax"), ("rv_yoy", "nmax"), ("F9", "F9寬")):
            cs = []
            for _, g in mS.groupby("grp"):
                g = g[np.isfinite(g[a_]) & np.isfinite(g[b_])]
                if len(g) >= 5:
                    c = g[a_].rank().corr(g[b_].rank())
                    if np.isfinite(c):
                        cs.append(c)
            SPR.append({"世界": wn, "段": sg, "A": a_, "B": b_, "組數": len(cs), "Spearman 平均": float(np.mean(cs)) if cs else np.nan,
                        "中位": float(np.median(cs)) if cs else np.nan})
    MB["年"] = MB["形成月底"].str[:4]
    for y, g in MB.groupby("年"):
        AVY.append({"世界": wn, "排序年": y, "檔次": len(g), "F6有值": float(g["has6"].mean()), "F7有值": float(g["has7"].mean()), "Q有值": float(g["hasQ"].mean()),
                    "F9可算": float(g["F9ok"].mean()), "T2可算": float(np.isfinite(g["rv_yoy"]).mean()), "T3可算": float(np.isfinite(g["vol60"]).mean()),
                    "MAX可算": float(np.isfinite(g["max20"]).mean()), "Q子項缺值數平均": float(g["q_nmiss"].mean())})
    J["同分群"][wn] = {"組數": gid, "成員": int((grp >= 0).sum()), "事件": nev, "排序日": len(forms), "大母體檔數(排序日平均)": float(MB.groupby("形成月底")["大母體檔數"].first().mean())}
    del W, ev, BR, FIN, QFIN
    return FR, AVL, AVY, MIS, OVL, SPR


def flags(FR, AVL, OVL):
    out = []
    for o in OVL:
        for col in ("補格 Σ∩÷Σk",):
            if o["A"] < o["B"] or o["B"] == "原" or o["A"] == "原":
                if np.isfinite(o[col]) and o[col] >= EQV:
                    out.append(f"近乎等價：{o['世界']}/{o['段']} {o['A']} vs {o['B']} {col} ＝ {o[col]:.3f}")
    for o in AVL:
        if o["層"].startswith("B"):
            for c, nm in (("T1 F9可算", "T1"), ("T2 營收年增可算", "T2"), ("T3 60日波動可算", "T3"), ("MAX 可算", "MAX")):
                if np.isfinite(o[c]) and o[c] < LOWAV:
                    out.append(f"可算比例低：{o['世界']}/{o['段']} {nm} 需抽月邊界組可算 {o[c]:.3f}")
    for f in FR:
        for nm in ORD[1:]:
            v = f.get(f"{nm}|需抽月中切點仍隨機比例")
            if v is not None and v >= 0.5:
                out.append(f"仍靠抽籤：{f['世界']}/{f['段']} {nm} 需抽月中切點仍隨機 {v:.3f}")
    return sorted(set(out))


def selftest():
    """排序 fixture：同 PTH 內可算先、分數降冪、算不出排最後、同分用 rk；不同 PTH 不受影響；全 0 ＝ 原順序。"""
    ev = {"e": np.array([5, 5, 5, 5, 5, 5, 7, 7]), "pth": np.array([1, 1, 1, 1, .9, .9, 1, 1.]),
          "rk": np.array([.1, .2, .3, .4, .5, .6, .7, .8])}
    fl = np.array([False, True, False, False, False, False, False, False]); sc = np.array([1., 9., 3., 1., 0., 0., 2., 5.])
    o = order_of(ev, fl, sc)
    assert o.tolist() == [2, 0, 3, 1, 4, 5, 7, 6], o.tolist()
    o0 = order_of(ev, np.zeros(8, bool), np.zeros(8)); assert o0.tolist() == np.lexsort((ev["rk"], -ev["pth"], ev["e"])).tolist()
    o1 = order_of(ev, np.ones(8, bool), sc); assert o1.tolist() == o0.tolist()
    return "order_of fixture：可算先／分數降冪／算不出最後／同分 rk／不跨 PTH／全 0 ＝ 原序／全算不出 ＝ 原序 全過"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--dry", action="store_true", help="只做 fixture 與 import")
    ap.add_argument("--worlds", default="主,早年")
    a = ap.parse_args()
    print(selftest())
    if a.dry:
        print("SEED0", PS.SEED0, "N", N, "NS0", PN.NS0, "FU.XD", FU.XD, "QL.ADJ", QL.ADJ, "F6 子項", len(F6KEYS), "F7 細項", len(F7KEYS), "Q 子項", len(QKEYS))
        return
    os.makedirs(OUT, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "run.log"))
    T0 = time.time()
    J = {"題": "高10 同分改排序 T1（F9）／T2（營收年增）／T3（60 日波動）頻率表（乾跑、⛔ 不算任何報酬）", "依據": "裁定 seq433、seq434（台股正式登錄未到）",
         "開跑": M.now_tpe(), "fixture": selftest(), "排序": ORDNAME, "對帳": {}, "AI1覆寫": {}, "資料": {}, "同分群": {}}
    FR, AVL, AVY, MIS, OVL, SPR = [], [], [], [], [], []
    for wn in a.worlds.split(","):
        r = world(wn, a, log, J)
        for L_, x in zip((FR, AVL, AVY, MIS, OVL, SPR), r):
            L_ += x
    pd.DataFrame(FR).to_csv(os.path.join(OUT, "freq.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(AVL).to_csv(os.path.join(OUT, "avail.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(AVY).to_csv(os.path.join(OUT, "avail_by_year.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(MIS).to_csv(os.path.join(OUT, "missing_sub.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(OVL).to_csv(os.path.join(OUT, "overlap.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(SPR).to_csv(os.path.join(OUT, "spearman.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["先知道的事"] = flags(FR, AVL, OVL)
    J["頻率表"] = FR; J["可算比例"] = AVL; J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[先知道的事]\n" + "\n".join(J["先知道的事"]))
    log(f"[對帳] {json.dumps(J['對帳'], ensure_ascii=False)}")
    log(f"[完] {J['耗時秒']}s")


if __name__ == "__main__":
    main()

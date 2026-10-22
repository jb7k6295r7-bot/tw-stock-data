# -*- coding: utf-8 -*-
"""找下一個大漲股：訊號後 3 年內漲 3 倍命中率 seq1【正式跑】（台股策略線 登錄 sha 8455d7003a62a190；裁定 seq449 發號、seq450 §一：
S1 判定 1 格（N_單筆 ＋1、Bonferroni 1 格）、最多暫定、2005～2016 未看過期間描述欄並報、S1 與「G1 且甲」重疊約 90% 照報；
V 依構造不可判定（N_單筆 −1）⇒ 原 seq1 季判版只描述（命中率、對照、季分群 CI，標「描述，不判」）；
seq451：seq2（sha c46d0d9e72c23f67）不核、⛔ 不取代 seq1，只准加 V「每月判」描述欄（標「看過頻率表後加的描述，不判、不計 N」））——回測線計算子代理。
⛔ 不 commit、不改既有檔；researchTriple_freq（頻率表：make_events、load_cf、ttm、low1y、latest_q、pct_of、deadline、segof、in_rng、mnum_d、market_map）、
   researchRevTurn_freq（ensure_data、prices、rev_table、jia、yi、avail_pos、filing_pos、mnum）、researchShortageExit（seam_open、lastvalid_le、cl）、
   researchIndMom_freq（reg_check、entry_flag、load_pit）⛔ 只 import。

    cd ~/tw-p17
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple --sha <頻率表同一版> --step rebuild      # M1：頻率表逐列重建
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple --sha <同上> --step vstate       # V 季判／月判狀態（不碰進場後價格）
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple --sha <同上> --step main [--dry0]         # --dry0：結果全寫 0（seq366 乾跑）
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple_check [--dry0]
輸出 backtest/resultsTriple/main/（乾跑 ~/trpwork/dry0）：main.json、cells.csv、yearly.csv、industry.csv、recall.csv、ungated.csv、vm_freq.csv、
     events_R_S1.csv.gz、events_R_Vq.csv.gz、events_R_Vm.csv.gz、rebuild.json（複本）、run.log

═══ 讀法（M 標；頻率表讀法 T0～T10 原樣沿用；以下為正式跑新增；⛔ 在讀任何本件命中、報酬之前寫死於 2026-10-22（台北）；★＝執行者定）═══
 M1 事件、配對 ＝ 頻率表：先以 researchTriple_freq.main 原樣（同一 --sha）重建到 ~/trpwork/rebuild，events_S1、events_V、freq_段、v_coverage、
    v_coverage_年、recall_denom、equiv、desc_signals、yearly 與已 commit 的 resultsTriple/freq 逐字比；任一不同 ⇒ 中止、⛔ 不算命中。
 M2 結果變數（登錄 §四）：進場價 P0 ＝ e 還原開盤（主世界開盤乘接縫倍數，researchShortageExit.seam_open，＝ 營收轉強驗證 N2）。
    路徑 ＝ 還原收盤 [e, e＋H]（★ 含 e 當日收盤）的有效 K 棒；(e, e＋H] 有壞根 ⇒ 路徑截在第一個壞根前一根（之後不再看；seq335 硬斷點）；
    最後有效 K 棒 ＜ e＋H 且距資料尾 ≥ 5 日 ⇒ 下市，路徑止於末根、之後以末根收盤計（登錄 §二）。
    H3（命中）＝ 路徑(750) 最高收盤 ≥ 3 × P0；2 倍 ＝ 路徑(500) 最高收盤 ≥ 2 × P0；750 日後仍 3 倍 ＝ 終值(750) ≥ 3 × P0
    （終值 ＝ 路徑末端有效收盤）；腰斬 ＝ 路徑(750) 最低收盤 ≤ 0.5 × P0；3 年報酬 R3 ＝ 終值(750) ÷ P0 − 1 − 0.585%（登錄 §九）。
    seq373（同根兩出場價取較低）：本件只用收盤、沒有盤中出場價 ⇒ 不適用（照註）。
 M3 主格 ＝ 頻率表主格（配到 ∧ e 可進場 ∧ 750 日走得完）。每事件 X ＝ H3事件 − 對照 H3 平均（對照 1～3 檔、同一 e）；命中率不扣成本。
    事件等權；CI ＝ research11.cl_stats 月分群（S1、V 季判：可用日 A 的月；V 月判：判日 J 的月，★ J 月與進場月一一對應）；
    S1 Bonferroni 1 格 ⇒ 雙尾 95%（z ＝ 1.96）；V 兩版同式但只描述。倍數 ＝ 命中率(訊號) ÷ 命中率(對照)。
 M4 判定（只有 S1；登錄 §五、裁定 seq450）：段 探索 2007-01～2014-12｜確認 2015-01～2023-08（依 A）；任一段 n_eff ＜ 24 ⇒ 還沒測；
    兩段差 ＞ 0 ∧ 確認段 CI 下界 ＞ 0 ⇒「S1 之後 3 年內漲 3 倍的比例比同類高（暫定）」；兩段差 ＜ 0 ∧ 確認段 CI 上界 ＜ 0 ⇒「比同類低（暫定）」；
    其他 ⇒「跟同類分不出」。2005～2016（未看過期間）只描述、並報。
 M5 全母體同月命中率（描述）：同一 e、判日過閘（S1、V 季判：G[A−1]；V 月判：G[J]）且 e 可進場的全部面板股，H3 平均；
    報「事件加權」（每個主格事件取其 e 的全母體率，再平均）。無閘版：母體換成判日有有效 K 棒的面板股。
 M6 V 月判（seq451 描述欄；台股 seq2 §三字面）：判日 J ＝ 每月最後一個交易日（2013-05～2026-08）；收盤、市值、距一年低點、500 張閘用 J；
    財報 ＝ 上傳日 ＜ J 日期（⇔ 該季可判位置 ≤ J，seq352）的最新一季；★ 目標季 ＝ 法定期限 ＜ J 日期的最新一季，落後 ≥ 2 季不可算；
    四條件、門檻、FCF／OCF代、淨值、分位母體（J 過閘）全同季判版（researchTriple_freq 原函式）；e ＝ J＋1 開盤；同檔 36 個月內只取第一次（J 的月序）；
    對照 ＝ 同一 J、過閘、V 可判但為假、市值十分位同（J 過閘母體）、e 可進場；★ 候選 ≥ 3 抽 3、否則全取；np.random.default_rng(20261022) 另起一條，
    事件依（J, 代號）序。段依 J：探索 2013-05～2017-12｜確認 2018-01～2023-08。主格 ＝ 配到 ∧ e 可進場 ∧ e＋750 ≤ 資料尾。
    同一套函式先以季判日重算 ⇒ 過閘去重事件須與頻率表 events_V 完全相同（自我對帳），不同 ⇒ 中止。
 M7 召回率（描述；登錄 §六）：3 倍段 3,316（resultsBigRun/乙_段_x3）；起漲前 12 個月 ＝ A（或 J）∈ [起點 − 12 曆月, 起點]；
    分子 ＝ 窗內出現過該訊號「狀態」（★ 不論閘、不去重；S1 ＝ 甲∧乙、轉強 ＝ up、V ＝ 季判／月判 V 真）；分母 ＝ 頻率表同式「可判」段數。
    過閘版另報（分子分母都限判日過閘）。
 M8 描述：分年（A／J 年）、分產業（S1 兩段主格合計，industry_pit）、同產業同月 ≥ 3 檔 S1、上市／上櫃、無流動性閘版本（事件 ＝ 頻率表無閘口徑重建，
    件數須與 freq_段 無閘事件相同；只報命中率與無閘全母體同月率、不配對）、R3 平均與中位、命中者與未命中者 R3 中位。
 M9 先驗（登錄 §十，寫死不改）：① S1 兩段差皆 ＞ 0；② V（季判，原登錄）兩段差皆 ＞ 0；③ S1 兩段、V 季判兩段的訊號命中率皆 ＜ 10%；
    ④ 召回率（無閘）：3 倍段起漲前 12 個月內出現 S1 的 ＜ 30%。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import shutil
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTriple_freq as TP              # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402  seam_open、lastvalid_le、cl
from backtest import researchIndMom_freq as IMF             # noqa: E402

REG2_SHA = "c46d0d9e72c23f67"
OUT = "backtest/resultsTriple/main"
FREQ = TP.OUT
REB = os.path.join(TP.TW, "rebuild")
RBJ = os.path.join(TP.TW, "rebuild.json")
COST = 0.00585
FILES = ["events_S1.csv.gz", "events_V.csv.gz", "freq_段.csv", "v_coverage.csv", "v_coverage_年.csv", "recall_denom.csv", "equiv.csv", "desc_signals.csv", "yearly.csv"]
SENT_V = "V 是一季才判一次的訊號，樣本期太短、判不了，只描述。"
NOTES = ["S1 最多暫定：S1 是看過營收轉強驗證（2017～2025-08）甲且乙描述才選的，兩段與已看期間重疊；2005～2016（未看過期間）另列描述",
         "S1 與「G1 且甲」事件重疊約 90%（3,023／3,376），S1 幾乎就是「營收創 24 月新高且加速」",
         SENT_V,
         "V 月判欄是看過頻率表後加的描述（裁定 seq451），不判、不計 N",
         "750 日重疊、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」",
         "這是全市場事件統計，不是買進規則；⛔ 不改 4 檔小部位（登錄 §八）",
         "3 倍段是事後圈的 ⇒ 召回率只描述",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）；早年上櫃 2007-07 前無價"]
LOG = TP.LOG
log = TP.log


# ═════════════ M1 頻率表重建 ═════════════
def step_rebuild(sha, procs):
    if os.path.isdir(REB):
        shutil.rmtree(REB)
    TP.OUT = REB
    argv = sys.argv
    sys.argv = ["researchTriple_freq", "--procs", str(procs), "--sha", sha]
    try:
        TP.main()
    finally:
        sys.argv = argv
        TP.OUT = FREQ
    res = {}
    for f in FILES:
        a_ = pd.read_csv(os.path.join(REB, f), dtype=str, keep_default_na=False)
        b_ = pd.read_csv(os.path.join(FREQ, f), dtype=str, keep_default_na=False)
        res[f] = bool(a_.shape == b_.shape and (a_.columns == b_.columns).all() and a_.equals(b_))
    J = {"sha": sha, "相同": res, "全同": all(res.values()), "時間": str(pd.Timestamp.now(tz="Asia/Taipei"))}
    json.dump(J, open(RBJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[M1 重建] {J}")
    if not J["全同"]:
        raise SystemExit("⛔ 頻率表重建不同")


# ═════════════ M2 結果變數 ═════════════
def outcome(PX, O, i, e, zero):
    """回 dict：H3、H2、仍3倍、腰斬、R3、狀態。zero ⇒ 全寫 0（seq366 乾跑）。"""
    if zero:
        return {"H3": 0.0, "H2_500": 0.0, "仍3倍": 0.0, "腰斬": 0.0, "R3": 0.0, "狀態": "乾跑0"}
    C, BAD, LASTV, VP = PX["C"], PX["BAD"], PX["LASTV"], PX["VP"]
    CEND = len(PX["CAL"]) - 1
    P0 = O[i, e]
    nan = {"H3": np.nan, "H2_500": np.nan, "仍3倍": np.nan, "腰斬": np.nan, "R3": np.nan}
    if not (np.isfinite(P0) and P0 > 0):
        return {**nan, "狀態": "無進場價"}
    res = {}
    for H in (500, 750):
        x = e + H; st = "完整"
        bb = np.flatnonzero(BAD[i, e + 1:x + 1])
        if len(bb):
            x = e + int(bb[0]); st = "壞根截斷"
        lv = int(LASTV[i])
        if (CEND - lv) >= 5 and lv < x:
            x = lv; st = "下市末根"
        seg = C[i, e:x + 1]; v = seg[np.isfinite(seg)]
        xv = SM.lastvalid_le(VP, i, x)
        if not len(v) or xv < e:
            return {**nan, "狀態": "路徑無K棒"}
        res[H] = (float(v.max()), float(v.min()), float(C[i, xv]), st)
    mx, mn, fin, st = res[750]
    return {"H3": float(mx >= 3 * P0), "H2_500": float(res[500][0] >= 2 * P0), "仍3倍": float(fin >= 3 * P0), "腰斬": float(mn <= 0.5 * P0),
            "R3": fin / P0 - 1 - COST, "狀態": st}


# ═════════════ M6 V 狀態（季判／月判共用；researchTriple_freq 原函式）═════════════
def v_states(PX, FP, XB, G, VALID, pts):
    """pts：[(tq, p1, cut)] ⇒ {(i, p1): {...}}；tq ＝ 目標季、p1 ＝ 收盤／市值／閘的位置、cut ＝ 上傳日須 ＜ 此日期。"""
    CAL, SIDS = PX["CAL"], PX["SIDS"]
    VS = {}
    for tq, p1, cut in pts:
        U0 = np.flatnonzero(VALID[:, p1]); Ug = G[U0, p1]
        n = len(U0)
        cf = np.full(n, np.nan); bm = np.full(n, np.nan); mcv = np.full(n, np.nan); lw = np.full(n, np.nan); ocfo = np.full(n, np.nan)
        src = [""] * n
        for k, i in enumerate(U0):
            sid = SIDS[i]
            mc = PX["MC"][i, p1]
            if np.isfinite(mc) and mc > 0:
                mcv[k] = mc
            lw[k] = TP.low1y(PX, int(i), p1)
            kq = TP.latest_q(FP, sid, cut)
            if kq < 0 or tq - kq >= 2:
                continue
            df = XB.get(sid)
            if df is None or kq not in df.index:
                continue
            o = TP.ttm(df["operating_cash_flow_ytd"], kq); c_ = TP.ttm(df["capex_ytd"], kq); eq = df.loc[kq, "total_equity"]
            if np.isfinite(o) and np.isfinite(mcv[k]):
                ocfo[k] = o / mcv[k]
                if np.isfinite(c_):
                    cf[k] = (o + c_) / mcv[k]; src[k] = "FCF"
                else:
                    cf[k] = o / mcv[k]; src[k] = "OCF代"
            if np.isfinite(eq) and np.isfinite(mcv[k]):
                bm[k] = eq / mcv[k]
        for tag, um in (("g", Ug), ("ng", np.ones(n, bool))):
            pc = TP.pct_of(cf, um); pb = TP.pct_of(bm, um); pm = TP.pct_of(mcv, um)
            for k, i in enumerate(U0):
                if not um[k]:
                    continue
                jd = bool(np.isfinite(pc[k]) and np.isfinite(pb[k]) and np.isfinite(pm[k]) and np.isfinite(lw[k]))
                v = bool(jd and pc[k] > 0.7 and pb[k] > 0.7 and pm[k] <= 0.5 and lw[k] <= 0.20)
                d = VS.setdefault((int(i), p1), {"tq": tq, "src": src[k]})
                d[f"可判_{tag}"] = jd; d[f"V_{tag}"] = v
                if tag == "g":
                    d["dec"] = int(math.ceil(pm[k] * 10)) if np.isfinite(pm[k]) else -1
    return VS


# ═════════════ 小工具 ═════════════
def rate(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(x.mean()) if len(x) else np.nan


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def cell_row(sig, seg, ident, d, z=1.96):
    """d：主格事件列（含 H3事件、H3對照平均、X、月 …）。"""
    d = d.dropna(subset=["X"])
    s = SM.cl(d["X"].to_numpy(float), d["月"].to_numpy(), z=z) if len(d) else {"n": 0, "months": 0}
    he, hc = rate(d["H3事件"]), rate(d["H3對照平均"])
    hit = d[d["H3事件"] == 1.0]; mis = d[d["H3事件"] == 0.0]
    return {"訊號": sig, "段": seg, "身分": ident, "主格事件": int(s["n"]), "n_eff": int(s.get("months", 0)),
            "命中率_訊號": he, "命中率_對照": hc, "命中率_全母體同月": rate(d["H3全母體同月"]),
            "差(點)": s.get("mean"), "se": s.get("se"), "CI95下": s.get("lo_b"), "CI95上": s.get("hi_b"),
            "倍數(訊號÷對照)": (he / hc if hc and np.isfinite(hc) and hc > 0 else np.nan),
            "2倍500日_訊號": rate(d["H2_500事件"]), "2倍500日_對照": rate(d["H2_500對照平均"]),
            "750日後仍3倍_訊號": rate(d["仍3倍事件"]), "750日後仍3倍_對照": rate(d["仍3倍對照平均"]),
            "腰斬率_訊號": rate(d["腰斬事件"]), "腰斬率_對照": rate(d["腰斬對照平均"]),
            "R3平均_訊號": rate(d["R3事件"]), "R3中位_訊號": med(d["R3事件"]), "R3平均_對照": rate(d["R3對照平均"]), "R3中位_對照": med(d["R3對照平均"]),
            "R3中位_命中者": med(hit["R3事件"]), "R3中位_未命中者": med(mis["R3事件"]),
            "命中率_上市": rate(d.loc[d["市場"] == "twse", "H3事件"]), "命中率_上櫃": rate(d.loc[d["市場"] == "tpex", "H3事件"]),
            "上市件": int((d["市場"] == "twse").sum()), "上櫃件": int((d["市場"] == "tpex").sum())}


# ═════════════ 主程式 ═════════════
def step_main(a):
    t0 = time.time()
    out = os.path.join(TP.TW, "dry0") if a.dry0 else OUT
    os.makedirs(out, exist_ok=True)
    RB = json.load(open(RBJ, encoding="utf-8"))
    FJ = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    if not (RB["全同"] and RB["sha"] == a.sha == FJ["origin/main"]):
        raise SystemExit(f"⛔ 重建未全同或 sha 不符：{RB}｜頻率表 {FJ['origin/main']}")
    reg1 = IMF.reg_check(TP.REG_SHA); reg2 = IMF.reg_check(REG2_SHA)
    dirs = [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*")))
    ruls = {q: [os.path.basename(f) for d in dirs for f in glob.glob(os.path.join(d, "*.md")) if q in os.path.basename(f) and "裁定線-" in os.path.basename(f)]
            for q in ("seq449", "seq450", "seq451")}
    if not all(ruls.values()):
        raise SystemExit(f"⛔ 裁定信缺 {ruls}")
    log(f"[登錄] seq1 {reg1}｜seq2 {reg2}（只取 V 月判字面）｜裁定 {ruls}")
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]
    CEND = len(CAL) - 1
    O, nseam = SM.seam_open(PX)
    G = PX["G"]; VALID = np.isfinite(PX["C"])
    MKT = TP.market_map(DN)
    pit = IMF.load_pit(DN)
    log(f"[M2] 接縫倍數套到主世界開盤：{nseam} 檔｜{time.time() - t0:.0f}s")
    Z = a.dry0
    oc_memo = {}

    def oc(i, e):
        k = (i, e)
        if k not in oc_memo:
            oc_memo[k] = outcome(PX, O, i, e, Z)
        return oc_memo[k]
    ef_memo = {}

    def eok(i, e):
        k = (i, e)
        if k not in ef_memo:
            ef_memo[k] = IMF.entry_flag(PX, i, e - 1, e) == "保留"
        return ef_memo[k]
    un_memo = {}

    def univ(p1, e, gated):
        k = (p1, e, gated)
        if k not in un_memo:
            U = np.flatnonzero((G if gated else VALID)[:, p1])
            hs = [oc(int(j), e)["H3"] for j in U if eok(int(j), e)]
            un_memo[k] = (rate(hs), len(hs))
        return un_memo[k]
    stc = Counter()

    def ev_rows(E, sig, segcol, p1_of, mcol):
        rows = []
        for rd in E.to_dict("records"):
            if str(rd["主格"]) != "True":
                continue
            i = ix[rd["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(rd["e"])))
            p1 = p1_of(rd, e)
            r0 = oc(i, e); stc[f"{sig} 事件 {r0['狀態']}"] += 1
            cs = [oc(ix[s], e) for s in str(rd["對照"]).split()]
            for c in cs:
                stc[f"{sig} 對照 {c['狀態']}"] += 1
            row = {"sid": rd["sid"], "A": rd.get("A", ""), "e": rd["e"], "月": rd[mcol], "e月": f"{CAL[e].year}-{CAL[e].month:02d}", "年": int(rd["年"]),
                   "段": rd[segcol], "市場": rd.get("市場", ""), "產業": rd.get("產業", ""), "對照數": len(cs)}
            if sig == "S1":
                row["未看過期間"] = str(rd["未看過期間"]) == "True"; row["同產業同月S1事件數"] = int(rd["同產業同月S1事件數"]); row["期別"] = rd["期別"]
            for k_ in ("H3", "H2_500", "仍3倍", "腰斬", "R3"):
                row[f"{k_}事件"] = r0[k_]
                row[f"{k_}對照平均"] = rate([c[k_] for c in cs])
            row["X"] = row["H3事件"] - row["H3對照平均"] if np.isfinite(row["H3對照平均"]) else np.nan
            row["H3全母體同月"], row["全母體股數"] = univ(p1, e, True)
            rows.append(row)
        return pd.DataFrame(rows)

    # ── S1（頻率表事件與配對）
    E1 = pd.read_csv(os.path.join(FREQ, "events_S1.csv.gz"), dtype={"sid": str, "期別": str}, keep_default_na=False)
    R1 = ev_rows(E1, "S1", "段", lambda rd, e: e - 2, "月")
    log(f"[S1] 主格 {len(R1)}｜A 月≠e 月 {int((R1['月'] != R1['e月']).sum())}｜{time.time() - t0:.0f}s")
    # ── V 季判（頻率表事件與配對）
    E2 = pd.read_csv(os.path.join(FREQ, "events_V.csv.gz"), dtype={"sid": str}, keep_default_na=False)
    R2 = ev_rows(E2, "V季判", "段", lambda rd, e: e - 2, "月")
    log(f"[V 季判] 主格 {len(R2)}｜{time.time() - t0:.0f}s")
    # ── V 月判（M6）：狀態由 --step vstate 先算好（同一 sha）
    import pickle
    VZ = pickle.load(open(os.path.join(TP.TW, f"vs_{sha[:12]}.pkl"), "rb"))
    qpts, mpts, VSq, VSm = VZ["qpts"], VZ["mpts"], VZ["VSq"], VZ["VSm"]
    if (qpts, mpts) != build_pts(CAL):
        raise SystemExit("⛔ V 狀態快取判日不符")
    qc =[(SIDS[i], i, p1 + 1, TP.mnum_d(CAL[p1 + 1]), d["tq"]) for (i, p1), d in VSq.items() if d.get("V_g")]
    qk_, _ = TP.make_events(qc, CEND, lambda i, A_: bool(G[i, A_ - 1]))
    selfq = {(s, str(CAL[A_].date())) for s, _, A_, _, _ in qk_} == set(zip(E2["sid"], E2["A"]))
    log(f"[M6 自我對帳] 季判以共用函式重算 ⇒ 事件 {len(qk_)}｜與頻率表 events_V 相同 {selfq}")
    if not selfq:
        raise SystemExit("⛔ V 狀態函式重算季判 ≠ 頻率表")
    mc_ =[(SIDS[i], i, J, TP.mnum_d(CAL[J]), d["tq"]) for (i, J), d in VSm.items() if d.get("V_g")]
    MK, mrs = TP.make_events(mc_, CEND, lambda i, J: bool(G[i, J]))
    mpool = defaultdict(list)
    for (i, J), d in VSm.items():
        if G[i, J] and d.get("可判_g") and not d.get("V_g") and d.get("dec", -1) > 0 and eok(i, J + 1):
            mpool[(J, d["dec"])].append(SIDS[i])
    rngm = np.random.default_rng(TP.SEED)
    rows = []
    for sid, i, J, mk, tq in sorted(MK, key=lambda z: (z[2], z[0])):
        e = J + 1; d = VSm[(i, J)]
        okE = eok(i, e)
        cand = sorted(mpool.get((J, d["dec"]), [])) if d.get("dec", -1) > 0 else []
        pick = (sorted(rngm.choice(cand, 3, replace=False).tolist()) if len(cand) >= 3 else cand) if (okE and cand) else []
        ind, _ = pit.at(sid, CAL[J])
        rows.append({"sid": sid, "J": str(CAL[J].date()), "A": str(CAL[J].date()), "e": str(CAL[e].date()), "目標季": TP.LP.qlabel(tq), "現金流口徑": d["src"],
                     "段": TP.segof(CAL[J], TP.V_SEGS), "年": CAL[J].year, "月": f"{CAL[J].year}-{CAL[J].month:02d}", "市場": MKT.get(sid, ""), "產業": ind or "",
                     "市值十分位": d["dec"], "進場": "保留" if okE else "不可進場", "候選數": len(cand), "對照": " ".join(pick), "對照數": len(pick), "配到": bool(pick),
                     "H750走得完": bool(e + 750 <= CEND), "主格": bool(pick and e + 750 <= CEND)})
    E3 = pd.DataFrame(rows)
    VMF = []
    for nm, x_, y_ in TP.V_SEGS + [("段外", None, None)]:
        dd = E3[E3["段"] == nm]; mm = dd[dd["主格"]]
        VMF.append({"段": nm, "判日數": sum(1 for _, J, _ in mpts if TP.segof(CAL[J], TP.V_SEGS) == nm), "事件(過閘去重)": len(dd),
                    "e可進場": int((dd["進場"] == "保留").sum()), "配到": int(dd["配到"].sum()), "750走得完": int(dd["H750走得完"].sum()),
                    "主格": len(mm), "n_eff": int(mm["月"].nunique()), "FCF/OCF代": f"{int((dd['現金流口徑'] == 'FCF').sum())}/{int((dd['現金流口徑'] == 'OCF代').sum())}",
                    "候選數中位": float(dd["候選數"].median()) if len(dd) else np.nan})
    VMF = pd.DataFrame(VMF)
    log(f"[V 月判] 判日 {len(mpts)}（{CAL[mpts[0][1]].date()}～{CAL[mpts[-1][1]].date()}）｜狀態 {len(mc_)} ⇒ 事件 {len(MK)}｜剔除 {dict(mrs)}｜{VMF.to_dict('records')}｜{time.time() - t0:.0f}s")
    E3s = E3.astype({"主格": str})
    R3m = ev_rows(E3s, "V月判", "段", lambda rd, e: e - 1, "月")
    log(f"[V 月判] 主格 {len(R3m)}｜{time.time() - t0:.0f}s")

    # ── 格表（M3、M4）
    CE = []
    for sg in ("探索", "確認"):
        CE.append(cell_row("S1", sg, "判定", R1[R1["段"] == sg]))
    CE.append(cell_row("S1", "2005～2016(未看過,描述)", "描述", R1[R1["未看過期間"]]))
    for sg in ("探索", "確認"):
        CE.append(cell_row("V季判(原登錄)", sg, "描述，不判（依構造不可判定）", R2[R2["段"] == sg]))
    for sg in ("探索", "確認"):
        CE.append(cell_row("V月判(seq451)", sg, "看過頻率表後加的描述，不判、不計 N", R3m[R3m["段"] == sg]))
    for sg in ("探索", "確認"):
        dd = R1[(R1["段"] == sg) & (R1["同產業同月S1事件數"] >= 3)]
        CE.append(cell_row("S1 同產業同月≥3檔(描述)", sg, "描述", dd))
    CE = pd.DataFrame(CE)
    ex = CE[(CE["訊號"] == "S1") & (CE["段"] == "探索")].iloc[0]; cf = CE[(CE["訊號"] == "S1") & (CE["段"] == "確認")].iloc[0]
    if min(ex["n_eff"], cf["n_eff"]) < TP.NEFF_MIN:
        verdict = "還沒測（n_eff ＜ 24）"
    elif ex["差(點)"] > 0 and cf["差(點)"] > 0 and cf["CI95下"] > 0:
        verdict = "S1 之後 3 年內漲 3 倍的比例比同類高（暫定）"
    elif ex["差(點)"] < 0 and cf["差(點)"] < 0 and cf["CI95上"] < 0:
        verdict = "S1 之後 3 年內漲 3 倍的比例比同類低（暫定）"
    else:
        verdict = "跟同類分不出"
    log(f"[M4 判定] {verdict}")

    # ── 分年、產業
    YR = []
    for sig, R in (("S1", R1), ("V季判", R2), ("V月判", R3m)):
        for y, d in R.groupby("年"):
            YR.append({"訊號": sig, "年": int(y), "主格": len(d), "命中率_訊號": rate(d["H3事件"]), "命中率_對照": rate(d["H3對照平均"]),
                       "命中率_全母體同月": rate(d["H3全母體同月"]), "差": rate(d["X"]), "腰斬率_訊號": rate(d["腰斬事件"])})
    YR = pd.DataFrame(YR)
    IN = []
    d12 = R1[R1["段"].isin(["探索", "確認"])]
    for ind, d in d12.groupby("產業"):
        IN.append({"產業": ind, "主格(兩段)": len(d), "月數": int(d["月"].nunique()), "命中率_訊號": rate(d["H3事件"]), "命中率_對照": rate(d["H3對照平均"]), "差": rate(d["X"])})
    IN = pd.DataFrame(IN).sort_values("主格(兩段)", ascending=False)

    # ── 無流動性閘版本（M8）
    Zc = pickle_load_rv(MD, SIDS)
    RV = Zc["RV"]
    APOS = RT.avail_pos(CAL, sorted(RV["period"].unique()))
    RV["i"] = RV["sid"].map(ix).fillna(-1).astype(int); RV["A"] = RV["period"].map(APOS).astype(int)
    RV["S1"] = RT.jia(RV) & RT.yi(RV); RV["mk"] = [RT.mnum(p) for p in RV["period"]]
    s1c = [(s, int(i), int(A_), int(mk), P) for s, i, A_, mk, P in zip(RV.loc[RV["S1"], "sid"], RV.loc[RV["S1"], "i"], RV.loc[RV["S1"], "A"], RV.loc[RV["S1"], "mk"], RV.loc[RV["S1"], "period"])]
    vok = lambda i, A_: bool(i >= 0 and 1 <= A_ <= CEND and VALID[i, A_ - 1])  # noqa: E731
    K1n, _ = TP.make_events(s1c, CEND, vok)
    qcn = [(SIDS[i], i, p1 + 1, TP.mnum_d(CAL[p1 + 1]), d["tq"]) for (i, p1), d in VSq.items() if d.get("V_ng")]
    K2n, _ = TP.make_events(qcn, CEND, vok)
    mcn = [(SIDS[i], i, J, TP.mnum_d(CAL[J]), d["tq"]) for (i, J), d in VSm.items() if d.get("V_ng")]
    K3n, _ = TP.make_events(mcn, CEND, lambda i, J: bool(VALID[i, J]))
    FR = pd.read_csv(os.path.join(FREQ, "freq_段.csv"), encoding="utf-8-sig")
    UG = []
    for sig, K, segs, eoff, dfun in (("S1", K1n, TP.S1_SEGS, 1, lambda z: CAL[z[2]]), ("V季判", K2n, TP.V_SEGS, 1, lambda z: CAL[z[2]]),
                                     ("V月判", K3n, TP.V_SEGS, 1, lambda z: CAL[z[2]])):
        for nm, x_, y_ in segs:
            kk = [z for z in K if TP.segof(dfun(z), segs) == nm]
            hs = []; us = []
            for z in kk:
                i, A_ = z[1], z[2]; e = A_ + eoff
                if e + 750 > CEND or not eok(i, e):
                    continue
                p1 = (A_ - 1) if sig != "V月判" else A_
                hs.append(oc(i, e)["H3"]); us.append(univ(p1, e, False)[0])
            fr_n = FR[(FR["訊號"] == ("S1" if sig == "S1" else "V")) & (FR["段"] == nm)]["無閘事件(去重)"]
            UG.append({"訊號": sig, "段": nm, "無閘事件": len(kk), "頻率表無閘事件": (int(fr_n.iloc[0]) if (len(fr_n) and sig != "V月判") else None),
                       "可進場且750走得完": len(hs), "命中率_訊號(無閘)": rate(hs), "命中率_全母體同月(無閘)": rate(us)})
    UG = pd.DataFrame(UG)
    badug = [r for r in UG.to_dict("records") if pd.notna(r["頻率表無閘事件"]) and int(r["頻率表無閘事件"]) != r["無閘事件"]]
    if badug:
        raise SystemExit(f"⛔ 無閘事件數與頻率表不同 {badug}")

    # ── 召回率（M7）
    X3 = pd.read_csv(TP.X3_CSV, dtype={"代號": str}, usecols=["代號", "起點"]); X3["起點"] = pd.to_datetime(X3["起點"])
    RV["過閘"] = [bool(i >= 0 and 1 <= A_ <= CEND and G[i, A_ - 1]) for i, A_ in zip(RV["i"], RV["A"])]
    RV["up_"] = RV["up"].astype(bool)
    acc = RV["accel"].to_numpy(float); h24 = RV["hi24"].to_numpy(float)
    RV["S1可判"] = np.isfinite(acc) & np.isfinite(h24); RV["轉強可判"] = np.isfinite(acc) | np.isfinite(h24)
    byS = defaultdict(list)
    for r in RV[(RV["A"] >= 1) & (RV["A"] <= CEND)][["sid", "A", "S1", "up_", "S1可判", "轉強可判", "過閘"]].itertuples(index=False):
        byS[r.sid].append((CAL[r.A], r.S1, r.up_, r.S1可判, r.轉強可判, r.過閘))
    byQ = defaultdict(list); byM = defaultdict(list)
    for (i, p1), d in VSq.items():
        byQ[SIDS[i]].append((CAL[p1 + 1], d.get("V_ng", False), d.get("可判_ng", False), d.get("V_g", False), d.get("可判_g", False)))
    for (i, J), d in VSm.items():
        byM[SIDS[i]].append((CAL[J], d.get("V_ng", False), d.get("可判_ng", False), d.get("V_g", False), d.get("可判_g", False)))
    RCr = []
    for s, st in zip(X3["代號"], X3["起點"]):
        lo = st - pd.DateOffset(months=12)
        r = [x for x in byS.get(s, []) if lo <= x[0] <= st]
        q = [x for x in byQ.get(s, []) if lo <= x[0] <= st]
        m = [x for x in byM.get(s, []) if lo <= x[0] <= st]
        RCr.append({"起點": st,
                    "S1可判": any(x[3] for x in r), "S1出現": any(x[1] for x in r), "S1可判g": any(x[3] and x[5] for x in r), "S1出現g": any(x[1] and x[5] for x in r),
                    "轉強可判": any(x[4] for x in r), "轉強出現": any(x[2] for x in r), "轉強可判g": any(x[4] and x[5] for x in r), "轉強出現g": any(x[2] and x[5] for x in r),
                    "V季可判": any(x[2] for x in q), "V季出現": any(x[1] for x in q), "V季可判g": any(x[4] for x in q), "V季出現g": any(x[3] for x in q),
                    "V月可判": any(x[2] for x in m), "V月出現": any(x[1] for x in m), "V月可判g": any(x[4] for x in m), "V月出現g": any(x[3] for x in m)})
    RCr = pd.DataFrame(RCr)
    RC = []
    for lab, d in (("全部", RCr), ("起點 2006～2014", RCr[(RCr["起點"].dt.year >= 2006) & (RCr["起點"].dt.year <= 2014)]),
                   ("起點 2015 起", RCr[RCr["起點"].dt.year >= 2015]), ("起點 2014-04 起", RCr[RCr["起點"] >= pd.Timestamp("2014-04-01")])):
        for sg, kj, ko in (("S1", "S1可判", "S1出現"), ("轉強", "轉強可判", "轉強出現"), ("V季判", "V季可判", "V季出現"), ("V月判", "V月可判", "V月出現")):
            for gt in ("", "g"):
                den = d[d[kj + gt]]
                num = int((den[ko + gt]).sum()) if not Z else 0
                RC.append({"3倍段範圍": lab, "訊號": sg, "閘": ("過閘" if gt else "無閘"), "分母(可判段)": len(den), "分子(窗內出現)": num,
                           "召回率": (num / len(den) if len(den) else np.nan)})
    RC = pd.DataFrame(RC)
    # 頻率表分母對帳
    RD = pd.read_csv(os.path.join(FREQ, "recall_denom.csv"), encoding="utf-8-sig")
    r0 = RD[RD["3倍段範圍"] == "全部"].iloc[0]
    dchk = {"S1無閘": [int(RC[(RC["3倍段範圍"] == "全部") & (RC["訊號"] == "S1") & (RC["閘"] == "無閘")]["分母(可判段)"].iloc[0]), int(r0["S1可判(無閘)"])],
            "S1過閘": [int(RC[(RC["3倍段範圍"] == "全部") & (RC["訊號"] == "S1") & (RC["閘"] == "過閘")]["分母(可判段)"].iloc[0]), int(r0["S1可判(過閘)"])],
            "V季過閘": [int(RC[(RC["3倍段範圍"] == "全部") & (RC["訊號"] == "V季判") & (RC["閘"] == "過閘")]["分母(可判段)"].iloc[0]), int(r0["V可判(過閘)"])]}
    log(f"[M7] 召回分母對頻率表 {dchk}")

    # ── 先驗（M9）
    v_ex = CE[(CE["訊號"] == "V季判(原登錄)") & (CE["段"] == "探索")].iloc[0]; v_cf = CE[(CE["訊號"] == "V季判(原登錄)") & (CE["段"] == "確認")].iloc[0]
    rec = RC[(RC["3倍段範圍"] == "全部") & (RC["訊號"] == "S1") & (RC["閘"] == "無閘")].iloc[0]
    PRI = [{"先驗": "① S1 命中率比同類高（約六成）", "實際": f"差 探索 {ex['差(點)']:+.4f}、確認 {cf['差(點)']:+.4f}", "中": bool(ex["差(點)"] > 0 and cf["差(點)"] > 0)},
           {"先驗": "② V 命中率比同類高（約五成；季判原登錄、描述）", "實際": f"差 探索 {v_ex['差(點)']:+.4f}、確認 {v_cf['差(點)']:+.4f}", "中": bool(v_ex["差(點)"] > 0 and v_cf["差(點)"] > 0)},
           {"先驗": "③ 兩訊號絕對命中率都 ＜ 10%（約八成）", "實際": f"S1 {ex['命中率_訊號']:.4f}／{cf['命中率_訊號']:.4f}；V 季判 {v_ex['命中率_訊號']:.4f}／{v_cf['命中率_訊號']:.4f}",
            "中": bool(max(ex["命中率_訊號"], cf["命中率_訊號"], v_ex["命中率_訊號"], v_cf["命中率_訊號"]) < 0.10)},
           {"先驗": "④ 召回率：3 倍段起漲前 12 個月內出現 S1 的 ＜ 30%（約七成）", "實際": f"{rec['分子(窗內出現)']}／{rec['分母(可判段)']} ＝ {rec['召回率']:.4f}", "中": bool(rec["召回率"] < 0.30)}]
    sent = [f"S1（營收加速且首次創 24 月新高）之後 3 年內漲 3 倍：{verdict}；探索段 訊號 {ex['命中率_訊號'] * 100:.2f}%／對照 {ex['命中率_對照'] * 100:.2f}%（差 {ex['差(點)'] * 100:+.2f} 點，n_eff {ex['n_eff']}）、"
            f"確認段 訊號 {cf['命中率_訊號'] * 100:.2f}%／對照 {cf['命中率_對照'] * 100:.2f}%（差 {cf['差(點)'] * 100:+.2f} 點，CI95 [{cf['CI95下'] * 100:+.2f}, {cf['CI95上'] * 100:+.2f}]，n_eff {cf['n_eff']}）"] + NOTES
    # ── 輸出
    R1.to_csv(os.path.join(out, "events_R_S1.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    R2.to_csv(os.path.join(out, "events_R_Vq.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    R3m.to_csv(os.path.join(out, "events_R_Vm.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    E3.to_csv(os.path.join(out, "events_Vm.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CE.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    IN.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    RC.to_csv(os.path.join(out, "recall.csv"), index=False, encoding="utf-8-sig")
    UG.to_csv(os.path.join(out, "ungated.csv"), index=False, encoding="utf-8-sig")
    VMF.to_csv(os.path.join(out, "vm_freq.csv"), index=False, encoding="utf-8-sig")
    shutil.copy(RBJ, os.path.join(out, "rebuild.json"))
    MJ = {"性質": "3 年 3 倍命中率 seq1 正式跑（S1 判定 1 格；V 季判、月判只描述）" + ("【乾跑：結果全寫 0】" if Z else ""),
          "登錄": {"seq1": f"sha {TP.REG_SHA}（{reg1}）", "seq2(只取 V 月判字面、不取代 seq1)": f"sha {REG2_SHA}（{reg2}）"}, "裁定": ruls,
          "origin/main": sha, "頻率表重建": RB, "接縫開盤倍數檔數": nseam, "結果狀態": dict(stc), "V季判自我對帳": selfq, "召回分母對頻率表": dchk,
          "V月判": {"判日數": len(mpts), "頻率": VMF.to_dict("records")}, "判定": verdict, "格": CE.to_dict("records"), "先驗": PRI, "結果句": sent,
          "乾跑0": bool(Z), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


def build_pts(CAL):
    """季判點（頻率表 T4 同式）與月判點（M6）：[(目標季, p1, 上傳截止日)]。"""
    CEND = len(CAL) - 1
    qpts = []
    for qk in range(TP.LP.qkey(2013, 1), TP.LP.qkey(2026, 2) + 1):
        A_ = int(CAL.searchsorted(TP.deadline(qk), side="right"))
        if 1 <= A_ <= CEND:
            qpts.append((qk, A_ - 1, CAL[A_]))
    mpts = []
    tqs = list(range(TP.LP.qkey(2012, 4), TP.LP.qkey(2026, 2) + 1))
    for y in range(2013, 2027):
        for m in range(1, 13):
            if (y, m) < (2013, 5) or (y, m) > (2026, 8):
                continue
            nxt = pd.Timestamp(y + (m == 12), m % 12 + 1, 1)
            J = int(CAL.searchsorted(nxt, side="left")) - 1
            if J < 0 or CAL[J].year != y or CAL[J].month != m or J + 1 > CEND:
                continue
            tq = max(q for q in tqs if TP.deadline(q) < CAL[J])
            mpts.append((tq, J, CAL[J]))
    return qpts, mpts


def step_vstate(a):
    """V 季判、月判狀態（只算訊號狀態與分位，⛔ 不碰進場後價格）⇒ ~/trpwork/vs_<sha12>.pkl。"""
    import pickle
    t0 = time.time()
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL = PX["CAL"]; G = PX["G"]; VALID = np.isfinite(PX["C"])
    FP, _ = RT.filing_pos(DN, CAL)
    XB, _ = TP.load_cf(DN)
    qpts, mpts = build_pts(CAL)
    VSq = v_states(PX, FP, XB, G, VALID, qpts)
    log(f"[vstate] 季判 {len(qpts)} 點 ⇒ {len(VSq)}｜{time.time() - t0:.0f}s")
    VSm = v_states(PX, FP, XB, G, VALID, mpts)
    log(f"[vstate] 月判 {len(mpts)} 點 ⇒ {len(VSm)}｜{time.time() - t0:.0f}s")
    pickle.dump({"qpts": qpts, "mpts": mpts, "VSq": VSq, "VSm": VSm, "sha": sha}, open(os.path.join(TP.TW, f"vs_{sha[:12]}.pkl"), "wb"), protocol=5)


def pickle_load_rv(MD, SIDS):
    import pickle
    Zc = pickle.load(open(os.path.join(RT.WORK, f"rv_{TP.RV_TAG}_s{RT.SHIFT_Y}.pkl"), "rb"))
    if not (Zc["MD"] == MD and Zc["codes"] == list(SIDS)):
        raise SystemExit("⛔ 月營收快取與資料版本不符")
    return Zc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--sha", required=True)
    ap.add_argument("--step", choices=["rebuild", "vstate", "main"], required=True); ap.add_argument("--dry0", action="store_true")
    a = ap.parse_args()
    if a.step == "rebuild":
        step_rebuild(a.sha, a.procs)
    elif a.step == "vstate":
        step_vstate(a)
    else:
        step_main(a)


if __name__ == "__main__":
    main()

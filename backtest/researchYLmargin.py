# -*- coding: utf-8 -*-
"""PREREG營收創新高加毛利率 seq2（台股策略線登錄 sha 052eff086de99d59，2026-10-09 15:59；裁定 seq321 §四發號、N_組合 ＋1、定 Q1；
事後重切 ⇒ 最多暫定）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLmargin run [--procs 2] [--reps 200]
    ...                                                       -m backtest.researchYLmargin report     # 由 seeds_part.csv 重算彙總
    ...                                                       -m backtest.researchYLmargin page       # 網頁 backtest/營收創新高加毛利率.html
    抽樣查核（獨立寫法）：... -m backtest.researchYLmargin_check

⭐ 讀法寫死時間：2026-10-10 23:20（台北）；寫死前 ⛔ 沒算任何本件數字（只看過登錄全文 seq2、裁定 seq321、資料庫線 1009-1712、
   既有程式、fs_hist 欄位格式與 other 檔名單；營量 v1／營飆 v1 正式數字本來就看過 ⇒ 登錄已標事後重切）。

═══ 讀法（M 標；登錄沒寫清楚的執行者補讀法都在這裡）═══
 M1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ 052eff086de99d59 才跑（信箱檔只讀）
 M2 本體 ＝ researchT1fix.build_ctx(True)（T1 資料尾補回、edc6f 快照、主窗 2017-03-02～2026-08-24）；停止交易強制出場：開
      （SF ＝ research11.stop_force_days(valid_from_data(全部股票), 主窗尾)，同 researchT1fix）
    營飆 v1 ＝ listexit_lines.sim（H120、N10、default_rng(1000＋r)、t−1 大盤閘：0050 收盤 ＞ 200 日均線）200 顆
    營量 v1 ＝ research11.simulate_mtm(sig13, "H60", 20, default_rng(7000＋r), log=[], d_max=None, pick="relvol", queue_days=0)；
      relvol 排序不抽籤 ⇒ 只跑 r＝0（正式件同）
    閘 G0：0050 主窗錨逐位元｜G1：不加條件 ＝ resultsT1fix/seeds.csv.gz c1 t1（200 顆）、c13 t1 r0 的 cagr／mdd／vol repr、first／end／trades、eq_sha 逐位元
    ⭐ 出場照登錄（營飆 120 根、營量 60 根收盤 ＝ 原策略「持有一字不動」）⇒ seq308 條件出場主臂不適用（本件是原策略加一條進場條件）
 M3 毛利率（Q1）資料：data/mops/fs_hist/<yyyy>Q<q>_<格式>_<市場>.csv（工作樹，與 origin/main 同內容；檔內容 sha 記在 setup）
    ci 檔「營業收入」「營業毛利（毛損）」（千元、年初累計）；單季 ＝ 本期累計 − 同年前一季累計（Q1 不減；前一季不在 ci 或空值 ⇒ 單季缺）
    毛利率 ＝ 單季毛利 ÷ 單季營收；單季營收 ≤ 0 或缺 ⇒ 缺；⛔ 不用「…淨額」欄；⛔ 不用 fin_hist（主窗只需 2015Q1 起；fin_hist 只在 --check 當旁證）
    同一股同一期出現在兩個檔（換市場等）⇒ ci 優先、再依檔名排序取第一個（筆數照報）
 M4 可用日：季 q 的法定期限 Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31 ⇒ 可用日 ＝ 嚴格晚於期限日的第一個交易日（本件日曆）
    訊號根 k（AND 表 pos：k 收盤判、次一交易日開盤進）的日期 d ⇒「最近一個已可用季」q* ＝ 可用日 ≤ d 的最晚一季（只看日曆、⛔ 不看資料有沒有）；
    去年同季 ＝ q*−4；⛔ 不用實際上傳日；⛔ q* 缺時不往前找別季補（⇒ 缺值）
 M5 每筆訊號一個狀態：
    行業 ＝ 該股在 q* 那期所在檔的格式；q* 不在任何檔 ⇒ 用該股 fs_hist 最近一次出現（≤ q* 最晚；沒有就 ＞ q* 最早）的格式；從未出現 ⇒ 無
    格式 ∈ {basi, bd, fh, ins}（金融保險）⇒「不適用・金融」⇒ 照原策略（留）
    格式 ＝ other（異業：新纖、中纖、和泰車、三商等；只有收入／支出、沒有毛利欄）⇒「不適用・異業」⇒ 照原策略（留）
      （⚠ 補讀法：登錄只寫金融；異業同樣「沒有毛利 ⇒ 不適用」⇒ 比照，筆數照報）
    其餘：q* 不在 ci 或 q* 毛利率缺 ⇒「缺值・本季」；q*−4 毛利率缺 ⇒「缺值・去年同季」⇒ 都算不符（剔除），筆數照報
    毛利率[q*] ≥ 毛利率[q*−4] ⇒「符」（留）；否則「不符」（剔除）
 M6 加條件 ＝ 原策略窗內訊號表（營飆：已過大盤閘的 ctx["sig"]；營量：ctx["sig13"]）只留「符」與「不適用」列，順序不動、同一引擎、同種子；
    剔除後空位 ⇒ 引擎原規則等下一個新訊號（⛔ 不放寬補）
 M7 段：主窗 2017-03-02～2026-08-24｜探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24
    ＝ 同一條權益曲線切窗（rerun17.win_metrics；researchSlip 子段同式）；「資料尾」讀成主窗尾 2026-08-24（＝ 0050 錨、正式件同窗）
    早年段（2012-06～2014-12）：fs_hist 2015Q1 起 ⇒ 0 筆可判；fin_hist 2013Q1 起也要到 2014-05-16 才有第一個可比季（不到段長 1/4），
      且營飆 v1 沒有早年版面 ⇒「不可判定」（登錄 §二「不足 ⇒ 不可判定」），⛔ 不硬判
 M8 判（使用者判準，對 0050 同段）：年化中位 ＞ 0050 年化 且 比值（年化中位 ÷ |回落中位|）≥ 0050 比值 ⇒ 合格；只過第一條 ⇒ 另列；否則不合格
    策略標籤 ＝ 探索、確認兩段取較嚴（不合格 ＜ 另列 ＜ 合格）；事後重切 ⇒ 最多「暫定」
    「比原策略好」＝ 探索、確認兩段都「年化中位 ≥ 原策略 且 比值 ≥ 原策略」，且這四個比較至少一個嚴格較大（⚠ 補讀法：登錄沒寫怎麼比）
    出口（登錄 §二）：合格且比原策略好 ⇒「加毛利率條件後 <策略> 判過（暫定）」；否則 ⇒「加毛利率條件沒有改善 <策略>」；⛔ 不寫「毛利率沒用」
 M9 假訊號臂：同一個訊號根（pos）在原策略當日候選裡均勻隨機剔除「與本條件當日剔除數相同」的列（不分行業）；200 次；
    抽樣 default_rng([20261010, 族, i])（族 1 ＝ 營飆、13 ＝ 營量），pos 由小到大逐日 rng.choice(不放回)；引擎種子 營飆 1000＋i、營量 7000＋i
    p ＝ 假訊號 ≥ 本件（營飆用本件 200 顆中位）的比例；年化、比值各報、各段
 M10 現實版（登錄 §四 成本 0.585%＋現實版）：researchSlip「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」兩策略＋「現實版＋C5 低消 20 元」營量；
    接法照 researchT1fix.slip_setup（T1）；閘 G2：不加條件的現實版 ＝ resultsT1fix seeds slip1_real t1（200 顆）、slip13_real／slip13_c5 t1 r0 的 cagr／mdd repr、eq_sha
    判定以 0.585% 版為準（同營量／營飆正式判定口徑）；現實版同表並報標籤，兩版不同照實寫
 M11 必報（描述、不判）：
    剔除比例逐年（訊號根日期年份；各狀態筆數）
    被剔除 vs 留下的逐筆報酬：AND 表 g_H120（營飆）／g_H60（營量）＝ 固定出場毛報酬（未扣成本；T1 補回列算到最後收盤）；
      筆數、平均、中位、p10／p25／p75／p90、勝率、≥ +50% 比例
    持股與現金（引擎 audit 逐日重建：部位市值 ＝ 買進金額 × 收盤 ÷ 買價；持有區間 ＝ [買進日, 賣出日)；現金 ＝ 1 − 部位市值 ÷ 權益）：
      每顆各段平均持股、平均現金，取種子中位；退化 ＝ 探索或確認段 平均持股 ＜ 3 或 現金 ＞ 30%（照報）
    窗尾持有：r＝0，主窗尾 2026-08-24 收盤仍持有的檔
    等效獨立檔數（seq321 §五；台股策略線 1009-1542 ⑨ 的式子）：r＝0，每個換股日（當天有買進）收盤持股 N 檔，
      ρ ＝ 各檔前 60 個交易日收盤日報酬（ffill 收盤）兩兩相關的平均（共同有效報酬 ＜ 40 天或零變異的配對略過），N_eff ＝ N ÷ (1 ＋ (N−1)ρ)；各段平均
    0050 濾網角色：營飆 v1 的大盤閘是「擋長空頭、不是急跌保護」
 M12 相對門檻（seq321 §五）：本件不新增母體或漲幅門檻（毛利率只跟自己去年同季比）⇒ 不適用
輸出 backtest/resultsYLmargin/：signals.csv.gz（逐筆狀態）、seeds.csv.gz、cells.csv、summary.json、run.log（seeds_part.csv ＝ 續跑用）；
     網頁 backtest/營收創新高加毛利率.html
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import re
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import rerun17 as RR
from . import research11 as R
from . import researchT1fix as T

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "resultsYLmargin")
PAGE = os.path.join(HERE, "營收創新高加毛利率.html")
FS = os.path.join(ROOT, "data", "mops", "fs_hist")
REG = "/mnt/c/SynologyDrive/跨線信箱/登錄全文-營收創新高加毛利率不退步_營量營飆候選加季報毛利率條件_登錄_台股策略線_seq2_sha052eff086de99d59-5054B-20261009-1559.md"
REG_SHA = "052eff086de99d59"
SEGS = {"主窗": ("2017-03-02", "2026-08-24"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
JUDGE = ("探索", "確認")
FIN = ("basi", "bd", "fh", "ins")
DEAD = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}
FAKE_SEED = 20261010
FAM = {"fly": {"id": 1, "名": "營飆 v1", "g": "g_H120"}, "vol": {"id": 13, "名": "營量 v1", "g": "g_H60"}}
SLIP = {"slip_fly": (1, T.SLIP_REAL, "營飆 v1 現實版", "slip1_real", "fly"), "slip_vol": (13, T.SLIP_REAL, "營量 v1 現實版", "slip13_real", "vol"),
        "slipc5_vol": (13, T.SLIP_C5, "營量 v1 現實版＋C5 低消 20 元", "slip13_c5", "vol")}
KEEP = ("符", "不適用・金融", "不適用・異業")
STATUSES = ("符", "不符", "缺值・本季", "缺值・去年同季", "不適用・金融", "不適用・異業")
RP = dict(float_precision="round_trip")
COLS = (["key", "r"] + [f"{s}_{m}" for s in SEGS for m in ("cagr", "mdd", "vol")] + [f"{s}_{m}" for s in SEGS for m in ("nh", "cash")]
        + ["cash_min", "audit_anom", "n_sig", "cagr", "mdd", "vol", "first", "end", "trades", "eq_sha", "sf_n"])
_G: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def qname(qi):
    return f"{qi // 4}Q{qi % 4 + 1}"


# ═════════════ 毛利率 ═════════════
def load_fs():
    """⇒ (F：sid、qi、fmt、rev、gp 一期一列，GM：{(sid, qi): 單季毛利率}，資訊)。"""
    files = sorted(glob.glob(os.path.join(FS, "*.csv")))
    h = hashlib.sha256(); parts = []; bad_num = 0
    for f in files:
        b = os.path.basename(f)
        m = re.fullmatch(r"(\d{4})Q([1-4])_([a-z]+)_(twse|tpex)\.csv", b)
        if not m:
            continue
        h.update(b.encode()); h.update(open(f, "rb").read())
        y, q, fmt = int(m[1]), int(m[2]), m[3]
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        x = pd.DataFrame({"sid": df["stock_id"].str.strip(), "qi": y * 4 + q - 1, "fmt": fmt, "file": b})
        for col, k in (("營業收入", "rev"), ("營業毛利（毛損）", "gp")):
            if fmt == "ci" and col in df:
                raw = df[col].str.replace(",", "").str.strip()
                v = pd.to_numeric(raw, errors="coerce")
                bad_num += int(((raw != "") & v.isna()).sum())
                x[k] = v.to_numpy(float)
            else:
                x[k] = np.nan
        parts.append(x)
    F = pd.concat(parts, ignore_index=True)
    F["_o"] = (F["fmt"] != "ci").astype(int)
    F = F.sort_values(["sid", "qi", "_o", "file"], kind="mergesort")
    dup = int(F.duplicated(["sid", "qi"]).sum())
    F = F.drop_duplicates(["sid", "qi"], keep="first").drop(columns="_o").reset_index(drop=True)
    ci = F[F["fmt"] == "ci"][["sid", "qi", "rev", "gp"]]
    p = ci.copy(); p["qi"] = p["qi"] + 1
    M = ci.merge(p, on=["sid", "qi"], how="left", suffixes=("", "_p"))
    q1 = (M["qi"] % 4 == 0).to_numpy()
    rq = np.where(q1, M["rev"], M["rev"] - M["rev_p"]); gq = np.where(q1, M["gp"], M["gp"] - M["gp_p"])
    with np.errstate(invalid="ignore", divide="ignore"):
        gm = np.where(np.isfinite(rq) & (rq > 0) & np.isfinite(gq), gq / rq, np.nan)
    M["gm"] = gm
    GM = {(s, int(qi)): float(g) for s, qi, g in zip(M["sid"], M["qi"], M["gm"])}
    info = {"檔數": len(files), "內容sha": h.hexdigest()[:16], "同股同期重複列": dup, "非數字值": bad_num,
            "期別": [qname(int(F["qi"].min())), qname(int(F["qi"].max()))], "ci 股期": int(len(ci)), "ci 單季毛利率有值": int(np.isfinite(gm).sum())}
    return F, GM, info


def avail_dates(cal, qlo, qhi):
    out = {}
    for qi in range(qlo, qhi + 1):
        y, q = qi // 4, qi % 4 + 1
        dy, mo, dd = DEAD[q]
        j = int(cal.searchsorted(pd.Timestamp(y + dy, mo, dd), side="right"))
        out[qi] = cal[j] if j < len(cal) else None
    return out


def status_table(sig, cal, F, GM):
    """訊號表（index 保留）⇒ 每列 q*、格式、毛利率、狀態。"""
    AV = avail_dates(cal, 2013 * 4, 2027 * 4)
    qs_sorted = sorted(k for k, v in AV.items() if v is not None)
    av_arr = np.array([AV[k] for k in qs_sorted], dtype="datetime64[ns]")
    FMT = {(s, int(q)): f for s, q, f in zip(F["sid"], F["qi"], F["fmt"])}
    APP = {s: list(zip(g["qi"].astype(int), g["fmt"])) for s, g in F.groupby("sid")}
    rows = []
    for idx, sid, pos in zip(sig.index, sig["sid"].astype(str), sig["pos"].astype(int)):
        d = cal[pos]
        j = int(np.searchsorted(av_arr, np.datetime64(d), side="right")) - 1
        qs = qs_sorted[j]
        fmt = FMT.get((sid, qs))
        if fmt is None:
            ap = APP.get(sid, [])
            le = [f for q, f in ap if q <= qs]; gt = [f for q, f in ap if q > qs]
            fmt_n = le[-1] if le else (gt[0] if gt else None)
        else:
            fmt_n = fmt
        g0 = GM.get((sid, qs), np.nan); g4 = GM.get((sid, qs - 4), np.nan)
        if fmt_n in FIN:
            st = "不適用・金融"
        elif fmt_n == "other":
            st = "不適用・異業"
        elif fmt != "ci" or not np.isfinite(g0):
            st = "缺值・本季"
        elif not np.isfinite(g4):
            st = "缺值・去年同季"
        else:
            st = "符" if g0 >= g4 else "不符"
        rows.append({"idx": idx, "sid": sid, "pos": pos, "date": str(d.date()), "qstar": qname(qs), "avail": str(AV[qs].date()),
                     "fmt": fmt_n if fmt_n else "", "fmt_q": fmt if fmt else "", "gm_q": g0, "gm_q4": g4, "status": st})
    S = pd.DataFrame(rows).set_index("idx")
    S["keep"] = S["status"].isin(KEEP)
    return S


# ═════════════ 持股重建 ═════════════
def intervals(au, n):
    op, iv, anom = {}, [], 0
    for x in au:
        if x["side"] == "buy":
            if x["sid"] in op:
                anom += 1
            op[x["sid"]] = (int(x["t"]), float(x["amt"]) / float(x["px"]))
        elif x["side"] == "sell":
            if x["sid"] not in op:
                anom += 1; continue
            t0, sh = op.pop(x["sid"]); iv.append((x["sid"], t0, int(x["t"]), sh))
    for s, (t0, sh) in op.items():
        iv.append((s, t0, n, sh))
    return iv, anom


def hold_stats(iv, closes, eq, segpos):
    n = len(eq); nh = np.zeros(n); val = np.zeros(n)
    for s, t0, t1, sh in iv:
        t1 = min(t1, n); c = np.asarray(closes[s][t0:t1], float)
        nh[t0:t1] += 1; val[t0:t1] += sh * c
    with np.errstate(invalid="ignore", divide="ignore"):
        cash = 1.0 - val / eq
    out = {}
    for k, (a, b) in segpos.items():
        out[f"{k}_nh"] = float(nh[a:b + 1].mean()); out[f"{k}_cash"] = float(np.nanmean(cash[a:b + 1]))
    out["cash_min"] = float(np.nanmin(cash[segpos["主窗"][0]:segpos["主窗"][1] + 1]))
    return out


def eff_n(iv, closes, days):
    res = []
    for t in days:
        held = [s for s, t0, t1, sh in iv if t0 <= t < t1]
        N = len(held)
        if N == 0:
            continue
        if N == 1:
            res.append((t, 1, np.nan, 1.0)); continue
        Rm = []
        for s in held:
            c = np.asarray(closes[s][max(t - 60, 0):t + 1], float)
            Rm.append(c[1:] / c[:-1] - 1.0 if len(c) == 61 else np.full(60, np.nan))
        Rm = np.array(Rm); cs = []
        for i in range(N):
            for j in range(i + 1, N):
                mk = np.isfinite(Rm[i]) & np.isfinite(Rm[j])
                if mk.sum() < 40:
                    continue
                a, b = Rm[i][mk], Rm[j][mk]
                if a.std() == 0 or b.std() == 0:
                    continue
                cs.append(float(np.corrcoef(a, b)[0, 1]))
        rho = float(np.mean(cs)) if cs else np.nan
        res.append((t, N, rho, N / (1 + (N - 1) * rho) if np.isfinite(rho) else np.nan))
    return res


# ═════════════ 設定 ═════════════
def fake_plan(P):
    plan = []
    keep = P["keep"].to_numpy(); pos = P["pos"].to_numpy()
    for p in np.unique(pos):
        idx = np.flatnonzero(pos == p); nrm = int((~keep[idx]).sum())
        if nrm:
            plan.append((int(p), idx, nrm))
    return plan


def fake_sig(fam, i):
    P = _G["POOL"][fam]
    rng = np.random.default_rng([FAKE_SEED, FAM[fam]["id"], i])
    drop = np.zeros(len(P), bool)
    for p, idx, nrm in _G["PLAN"][fam]:
        drop[idx[rng.choice(len(idx), size=nrm, replace=False)]] = True
    return _G["BASE"][fam][~drop]


def setup(procs):
    t0 = time.time()
    b = open(REG, "rb").read()
    sha = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if sha != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {sha} ≠ {REG_SHA}")
    log(f"[M1 登錄 sha] {sha} ✔")
    ctx = T.build_ctx(True)
    cal = ctx["cal"]; ncal = len(cal); w0, w1 = ctx["w0"], ctx["w1"]
    bench = RR.load_bench(cal)
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    g0 = repr(bw["cagr"]) == repr(T.ANCHOR[0]) and repr(bw["mdd"]) == repr(T.ANCHOR[1])
    log(f"[G0 0050 錨] 逐位元 {g0}")
    if not g0:
        raise SystemExit("⛔ G0 不過")
    segpos = {}
    for k, (x, y) in SEGS.items():
        a, bb = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
        if str(cal[a].date()) != x or str(cal[bb].date()) != y:
            raise SystemExit(f"⛔ 段端點不對 {k}")
        segpos[k] = (a, bb)
    if segpos["主窗"] != (w0, w1):
        raise SystemExit("⛔ 主窗 ≠ ctx 窗")
    B50 = {k: RR.bench_row(cal, bench, a, bb + 1) for k, (a, bb) in segpos.items()}
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    F, GM, fsinfo = load_fs()
    log(f"[fs_hist] {json.dumps(fsinfo, ensure_ascii=False)}")
    sig_fly, sig_vol = ctx["sig"], ctx["sig13"]
    if not sig_fly.index.isin(sig_vol.index).all():
        raise SystemExit("⛔ 營飆訊號不是營量訊號的子集")
    ST = status_table(sig_vol, cal, F, GM)
    ST["in_vol"] = True; ST["in_fly"] = ST.index.isin(sig_fly.index)
    for c in ("entry_pos", "g_H60", "g_H120", "relvol"):
        ST[c] = sig_vol[c]
    POOL = {"vol": ST.loc[sig_vol.index], "fly": ST.loc[sig_fly.index]}
    BASE = {"vol": sig_vol, "fly": sig_fly}
    Q1 = {f: BASE[f][POOL[f]["keep"].to_numpy()] for f in FAM}
    PLAN = {f: fake_plan(POOL[f]) for f in FAM}
    for f in FAM:
        log(f"[{FAM[f]['名']}] 窗內訊號 {len(BASE[f])} ⇒ 加條件留 {len(Q1[f])}（剔 {len(BASE[f]) - len(Q1[f])}）｜"
            + "、".join(f"{s} {int((POOL[f]['status'] == s).sum())}" for s in STATUSES))
    # 現實版
    T._G.update(cal=cal, NPX=ncal + 1)
    slip_sids = sorted(set(sig_fly["sid"]) | set(sig_vol["sid"]))
    with Pool(procs) as pool:
        X_full = dict(pool.map(T._load_x, [(s, ctx["mk"].get(s, "twse")) for s in slip_sids], chunksize=8))
    SL = {"base": T.slip_setup(ctx, X_full, SF, procs), "q1": T.slip_setup(dict(ctx, sig=Q1["fly"], sig13=Q1["vol"]), X_full, SF, procs)}
    _G.update(ctx=ctx, cal=cal, ncal=ncal, w0=w0, w1=w1, SF=SF, segpos=segpos, POOL=POOL, BASE=BASE, Q1=Q1, PLAN=PLAN, SL=SL)
    info = {"日曆": ncal, "日曆起訖": [str(cal[0].date()), str(cal[-1].date())], "段": {k: [str(cal[a].date()), str(cal[bb].date()), bb - a + 1] for k, (a, bb) in segpos.items()},
            "0050": B50, "停止交易股": len(SF), "fs_hist": fsinfo, "現實版股數": len(slip_sids), "秒": round(time.time() - t0)}
    return info, ST


# ═════════════ 一顆 ═════════════
def seg_metrics(eq, first, end):
    out = {}
    for k, (a, b) in _G["segpos"].items():
        c, m, v = RR.win_metrics(eq, first, end, a, b)
        out[f"{k}_cagr"] = float(c); out[f"{k}_mdd"] = float(m); out[f"{k}_vol"] = float(v)
    return out


def _one(args):
    key, r = args
    fam_k, arm = key.split("|")
    ctx = _G["ctx"]; extra = None
    if fam_k in SLIP:
        from . import researchSlip as S
        cell, arm_nm, *_ = SLIP[fam_k]
        S._G.clear(); S._G.update(_G["SL"][arm])
        sig, op, cost, kw = S._G["INP"][(cell, arm_nm)]
        o = S.run_engine(cell, sig, op, cost, kw, r)
        eq = np.asarray(o["equity"], float)
        row = {"key": key, "r": r, **seg_metrics(eq, o["first"], o["end"])}
    else:
        sig = fake_sig(fam_k, r) if arm == "fake" else (_G["BASE"][fam_k] if arm == "base" else _G["Q1"][fam_k])
        au = []
        if fam_k == "fly":
            o = L.sim(dict(ctx, sig=sig), {"stop_force": _G["SF"]}, r, audit=au)
        else:
            o = R.simulate_mtm(sig, "H60", 20, np.random.default_rng(RR.P1_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                               pick="relvol", queue_days=0, return_equity=True, stop_force=_G["SF"], audit=au)
        eq = np.asarray(o["equity"], float)
        iv, anom = intervals(au, len(eq))
        row = {"key": key, "r": r, **seg_metrics(eq, o["first"], o["end"]), **hold_stats(iv, ctx["closes"], eq, _G["segpos"]), "audit_anom": anom,
               "n_sig": int(len(sig))}
        if r == 0 and arm != "fake":
            w0, w1 = _G["w0"], _G["w1"]
            days = sorted({int(x["t"]) for x in au if x["side"] == "buy" and w0 <= int(x["t"]) <= w1})
            en = eff_n(iv, ctx["closes"], days)
            cal = _G["cal"]
            extra = {"窗尾持有": sorted(s for s, t0, t1, sh in iv if t0 <= w1 < t1),
                     "effn": [(str(cal[t].date()), N, rho, ne) for t, N, rho, ne in en]}
    row.update({"cagr": row["主窗_cagr"], "mdd": row["主窗_mdd"], "vol": row["主窗_vol"], "first": int(o["first"]), "end": int(o["end"]),
                "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "sf_n": int(o.get("x_stop_force_n", -1))})
    return row, extra


def plan(reps):
    P = []
    for arm in ("base", "q1", "fake"):
        P.append((f"fly|{arm}", reps))
    P += [("vol|base", 1), ("vol|q1", 1), ("vol|fake", reps)]
    P += [("slip_fly|base", reps), ("slip_fly|q1", reps), ("slip_vol|base", 1), ("slip_vol|q1", 1), ("slipc5_vol|base", 1), ("slipc5_vol|q1", 1)]
    return P


def run(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("research11.py", "rerun17.py", "listexit_lines.py", "researchSlip.py", "researchT1fix.py", "researchYLmargin.py")}
    log(f"===== researchYLmargin run procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{T.TAG}｜{src} =====")
    info, ST = setup(a.procs)
    ST.to_csv(os.path.join(OUT, "signals.csv.gz"), index_label="and_idx")
    fp = os.path.join(OUT, "seeds_part.csv"); xp = os.path.join(OUT, "extras.json")
    done = pd.read_csv(fp, dtype={"eq_sha": str}, **RP) if os.path.exists(fp) else None
    have = set() if done is None else {k for k, g in done.groupby("key") if g["r"].nunique() >= dict(plan(a.reps))[k]}
    EX = json.load(open(xp, encoding="utf-8")) if os.path.exists(xp) else {}
    todo = [(k, n) for k, n in plan(a.reps) if k not in have]
    log(f"[計畫] {len(plan(a.reps))} 批，已落檔 {len(have)}、待跑 {len(todo)}")
    with Pool(a.procs) as pool:
        for k, n in todo:
            t0 = time.time()
            res = pool.map(_one, [(k, r) for r in range(n)], chunksize=4)
            df = pd.DataFrame([x for x, _ in res]).reindex(columns=COLS)       # ⭐ 固定欄序（現實版列沒有持股欄）⇒ 續寫不錯位
            for x, e in res:
                if e is not None:
                    EX[k] = e
            df.to_csv(fp, mode="a", header=not os.path.exists(fp), index=False)
            json.dump(EX, open(xp, "w", encoding="utf-8"), ensure_ascii=False, default=float)
            log(f"  [{k}] {n} 顆｜{time.time() - t0:.0f}s")
    json.dump({"setup": info, "程式": src, "reps": a.reps, "秒_run": round(time.time() - t00)},
              open(os.path.join(OUT, "setup.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(a)


# ═════════════ 彙總 ═════════════
ORD = {"不合格": 0, "另列": 1, "合格": 2}


def lab(c, m, b):
    c50, r50 = b["cagr"], b["cagr"] / abs(b["mdd"])
    return "合格" if (c > c50 and c / abs(m) >= r50) else ("另列" if c > c50 else "不合格")


def dist(g):
    g = np.asarray(g, float); g = g[np.isfinite(g)]
    if not len(g):
        return {"筆數": 0}
    q = np.percentile(g, [10, 25, 50, 75, 90])
    return {"筆數": int(len(g)), "平均": float(g.mean()), "中位": float(q[2]), "p10": float(q[0]), "p25": float(q[1]), "p75": float(q[3]), "p90": float(q[4]),
            "勝率": float((g > 0).mean()), "≥+50%": float((g >= 0.5).mean())}


def gates(SD):
    ref = pd.read_csv(os.path.join(HERE, "resultsT1fix", "seeds.csv.gz"), dtype={"eq_sha": str}, **RP)
    out = {}
    for k, rk, full in (("fly|base", "c1", True), ("vol|base", "c13", True), ("slip_fly|base", "slip1_real", False), ("slip_vol|base", "slip13_real", False),
                        ("slipc5_vol|base", "slip13_c5", False)):
        g = SD[SD["key"] == k].set_index("r").sort_index()
        rf = ref[(ref["key"] == rk) & (ref["var"] == "t1")].set_index("r").sort_index()
        bad = 0
        for r in g.index:
            ok = all(repr(float(g.at[r, c])) == repr(float(rf.at[r, c])) for c in (("cagr", "mdd", "vol") if full else ("cagr", "mdd"))) and \
                str(g.at[r, "eq_sha"]) == str(rf.at[r, "eq_sha"])
            if full:
                ok = ok and all(int(g.at[r, c]) == int(rf.at[r, c]) for c in ("first", "end", "trades"))
            bad += not ok
        out[k] = {"顆數": int(len(g)), "不同": int(bad), "對照": f"resultsT1fix/seeds.csv.gz｜{rk}｜t1"}
    return out


def report(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    SD = pd.read_csv(os.path.join(OUT, "seeds_part.csv"), dtype={"eq_sha": str}, **RP).drop_duplicates(["key", "r"], keep="last")
    SD = SD.sort_values(["key", "r"]).reset_index(drop=True)
    SD.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False)
    setup_info = json.load(open(os.path.join(OUT, "setup.json"), encoding="utf-8"))
    EX = json.load(open(os.path.join(OUT, "extras.json"), encoding="utf-8"))
    ST = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str}, **RP)
    B50 = setup_info["setup"]["0050"]
    G = gates(SD); gok = all(v["不同"] == 0 for v in G.values())
    log(f"[G1／G2 不加條件 ＝ 正式版] {json.dumps(G, ensure_ascii=False)}")
    # 格
    cells = []
    for k, g in SD.groupby("key", sort=False):
        fam_k, arm = k.split("|")
        for s in SEGS:
            c, m = float(g[f"{s}_cagr"].median()), float(g[f"{s}_mdd"].median())
            row = {"key": k, "段": s, "顆數": int(len(g)), "年化": c, "回落": m, "比值": c / abs(m), "標籤": lab(c, m, B50[s]),
                   "年化_p10": float(g[f"{s}_cagr"].quantile(0.1)), "年化_p90": float(g[f"{s}_cagr"].quantile(0.9)),
                   "0050年化": B50[s]["cagr"], "0050回落": B50[s]["mdd"], "0050比值": B50[s]["cagr"] / abs(B50[s]["mdd"])}
            if f"{s}_nh" in g:
                row.update({"平均持股": float(g[f"{s}_nh"].median()), "平均現金": float(g[f"{s}_cash"].median())})
            row["交易筆數中位"] = float(g["trades"].median())
            cells.append(row)
    TB = pd.DataFrame(cells)
    TB.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    C = {(r["key"], r["段"]): r for r in cells}
    verdict = {}
    for f, nm in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        q, b = (lambda s: C[(f"{f}|q1", s)]), (lambda s: C[(f"{f}|base", s)])
        seg_lab = {s: q(s)["標籤"] for s in SEGS}
        strict = min((seg_lab[s] for s in JUDGE), key=lambda x: ORD[x])
        cmp4 = [(q(s)["年化"], b(s)["年化"]) for s in JUDGE] + [(q(s)["比值"], b(s)["比值"]) for s in JUDGE]
        better = all(x >= y for x, y in cmp4) and any(x > y for x, y in cmp4)
        deg = {s: bool(q(s)["平均持股"] < 3 or q(s)["平均現金"] > 0.30) for s in JUDGE}
        ok = strict == "合格" and better
        v = {"段標籤": seg_lab, "兩段取較嚴": strict, "比原策略好": better, "退化": deg, "早年": "不可判定",
             "結論": (f"加毛利率條件後 {nm} 判過（暫定）" if ok else f"加毛利率條件沒有改善 {nm}"),
             "差": {s: {"年化pt": (q(s)["年化"] - b(s)["年化"]) * 100, "回落pt": (q(s)["回落"] - b(s)["回落"]) * 100, "比值": q(s)["比值"] - b(s)["比值"]} for s in SEGS}}
        # 假訊號
        fk = SD[SD["key"] == f"{f}|fake"]
        v["假訊號"] = {}
        for s in SEGS:
            fc = fk[f"{s}_cagr"].to_numpy(); fr = fc / np.abs(fk[f"{s}_mdd"].to_numpy())
            v["假訊號"][s] = {"次數": int(len(fk)), "年化中位": float(np.median(fc)), "回落中位": float(fk[f"{s}_mdd"].median()),
                            "比值中位": float(np.median(fc)) / abs(float(fk[f"{s}_mdd"].median())),
                            "p_年化": float((fc >= q(s)["年化"]).mean()), "p_比值": float((fr >= q(s)["比值"]).mean()),
                            "假訊號合格比例": float(np.mean([lab(c_, m_, B50[s]) == "合格" for c_, m_ in zip(fc, fk[f"{s}_mdd"])]))}
        if f == "fly":
            qq = SD[SD["key"] == "fly|q1"].set_index("r").sort_index(); bb = SD[SD["key"] == "fly|base"].set_index("r").sort_index().loc[qq.index]
            v["同顆配對"] = {s: {"年化與回落都較好": int(((qq[f"{s}_cagr"] > bb[f"{s}_cagr"]) & (qq[f"{s}_mdd"] > bb[f"{s}_mdd"])).sum()),
                                "年化與回落都較差": int(((qq[f"{s}_cagr"] < bb[f"{s}_cagr"]) & (qq[f"{s}_mdd"] < bb[f"{s}_mdd"])).sum()),
                                "年化較高": int((qq[f"{s}_cagr"] > bb[f"{s}_cagr"]).sum()), "顆數": int(len(qq))} for s in SEGS}
        # 現實版
        v["現實版"] = {}
        for sk, (cell, armn, snm, rk, ff) in SLIP.items():
            if ff != f:
                continue
            v["現實版"][snm] = {s: {"原策略": {k_: C[(f"{sk}|base", s)][k_] for k_ in ("年化", "回落", "比值", "標籤")},
                                   "加條件": {k_: C[(f"{sk}|q1", s)][k_] for k_ in ("年化", "回落", "比值", "標籤")}} for s in SEGS}
            v["現實版"][snm]["兩段取較嚴"] = min((C[(f"{sk}|q1", s)]["標籤"] for s in JUDGE), key=lambda x: ORD[x])
        # 剔除
        P = ST[ST["in_fly"]] if f == "fly" else ST[ST["in_vol"]]
        P = P.assign(年=P["date"].str[:4])
        yr = []
        for y_, g in P.groupby("年"):
            d = {"年": y_, "訊號": int(len(g)), **{s: int((g["status"] == s).sum()) for s in STATUSES}}
            d["剔除比例"] = float((~g["keep"]).mean()); yr.append(d)
        v["剔除"] = {"訊號": int(len(P)), "剔除": int((~P["keep"]).sum()), "剔除比例": float((~P["keep"]).mean()),
                    "各狀態": {s: int((P["status"] == s).sum()) for s in STATUSES}, "逐年": yr}
        gcol = FAM[f]["g"]
        v["逐筆報酬"] = {"口徑": f"{gcol}（固定出場毛報酬、未扣成本）", "留下": dist(P.loc[P["keep"], gcol]), "剔除": dist(P.loc[~P["keep"], gcol]),
                       "其中不符": dist(P.loc[P["status"] == "不符", gcol]), "其中缺值": dist(P.loc[P["status"].str.startswith("缺值"), gcol])}
        # 等效獨立、窗尾
        v["窗尾持有"] = {arm: EX.get(f"{f}|{arm}", {}).get("窗尾持有") for arm in ("base", "q1")}
        v["等效獨立檔數"] = {}
        for arm in ("base", "q1"):
            en = pd.DataFrame(EX.get(f"{f}|{arm}", {}).get("effn", []), columns=["date", "N", "rho", "neff"])
            v["等效獨立檔數"][arm] = {s: {"換股日": int(((en["date"] >= x) & (en["date"] <= y)).sum()),
                                     "平均N": float(en.loc[(en["date"] >= x) & (en["date"] <= y), "N"].mean()),
                                     "平均ρ": float(en.loc[(en["date"] >= x) & (en["date"] <= y), "rho"].mean()),
                                     "平均N_eff": float(en.loc[(en["date"] >= x) & (en["date"] <= y), "neff"].mean())} for s, (x, y) in SEGS.items()}
        v["audit 異常"] = int(SD[SD["key"].str.startswith(f + "|")]["audit_anom"].sum())
        v["最低現金"] = float(SD[SD["key"].str.startswith(f + "|")]["cash_min"].min())
        verdict[f] = v
        log(f"[{nm}] {v['結論']}｜段標籤 {seg_lab}｜比原策略好 {better}｜剔除 {v['剔除']['剔除']}/{v['剔除']['訊號']}")
    S = {"件": "PREREG營收創新高加毛利率 seq2（Q1）", "登錄sha": REG_SHA, "停止交易強制出場": "開", "閘": {"G0": True, "G1G2": G, "全過": gok},
         "setup": setup_info["setup"], "程式": setup_info["程式"], "reps": setup_info["reps"], "策略": verdict}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    if not gok:
        raise SystemExit("⛔ 閘門不過")


# ═════════════ 網頁 ═════════════
def page(a):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    TB = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
    C = {(r["key"], r["段"]): r for _, r in TB.iterrows()}
    p = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.1f}%"
    pp = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.1f}%"
    e = html.escape
    V = S["策略"]; B = S["setup"]["0050"]
    chk = {}
    cf = os.path.join(OUT, "check.json")
    if os.path.exists(cf):
        chk = json.load(open(cf, encoding="utf-8"))

    def cmp_table(f):
        rows = []
        for s in SEGS:
            b, q = C[(f"{f}|base", s)], C[(f"{f}|q1", s)]
            fk = V[f]["假訊號"][s]
            rows.append(f"<tr><th>{s}</th><td>{p(b['年化'])}／{p(b['回落'])}<br><span class=m>{b['標籤']}</span></td>"
                        f"<td><b>{p(q['年化'])}／{p(q['回落'])}</b><br><span class=m>{q['標籤']}</span></td>"
                        f"<td>{p(fk['年化中位'])}／{p(fk['回落中位'])}<br><span class=m>p 年化 {fk['p_年化']:.2f}・p 比值 {fk['p_比值']:.2f}</span></td>"
                        f"<td>{p(B[s]['cagr'])}／{p(B[s]['mdd'])}</td></tr>")
        return ("<table><thead><tr><th>段</th><th>原策略</th><th>加毛利率條件</th><th>假訊號臂（隨機剔同數量）</th><th>0050</th></tr></thead><tbody>"
                + "".join(rows) + "</tbody></table><p class=m>格內：年化中位／回落中位；標籤對 0050 同段。p ＝ 假訊號 200 次裡不輸本件的比例。</p>")

    def slip_table(f):
        out = []
        for snm, d in V[f]["現實版"].items():
            rs = "".join(f"<tr><th>{s}</th><td>{p(d[s]['原策略']['年化'])}／{p(d[s]['原策略']['回落'])}（{d[s]['原策略']['標籤']}）</td>"
                         f"<td>{p(d[s]['加條件']['年化'])}／{p(d[s]['加條件']['回落'])}（{d[s]['加條件']['標籤']}）</td></tr>" for s in SEGS)
            out.append(f"<h4>{e(snm)}</h4><table><thead><tr><th>段</th><th>原策略</th><th>加條件</th></tr></thead><tbody>{rs}</tbody></table>")
        return "".join(out)

    def rm_table(f):
        d = V[f]["剔除"]
        rs = "".join(f"<tr><td>{y['年']}</td><td>{y['訊號']}</td><td>{y['符']}</td><td>{y['不符']}</td><td>{y['缺值・本季'] + y['缺值・去年同季']}</td>"
                     f"<td>{y['不適用・金融'] + y['不適用・異業']}</td><td>{pp(y['剔除比例'])}</td></tr>" for y in d["逐年"])
        return ("<table><thead><tr><th>年</th><th>訊號</th><th>符（留）</th><th>不符（剔）</th><th>缺值（剔）</th><th>不適用（留）</th><th>剔除比例</th></tr></thead><tbody>"
                + rs + f"<tr class=tot><td>合計</td><td>{d['訊號']}</td><td>{d['各狀態']['符']}</td><td>{d['各狀態']['不符']}</td>"
                f"<td>{d['各狀態']['缺值・本季'] + d['各狀態']['缺值・去年同季']}</td><td>{d['各狀態']['不適用・金融'] + d['各狀態']['不適用・異業']}</td>"
                f"<td>{pp(d['剔除比例'])}</td></tr></tbody></table>"
                f"<p class=m>缺值細分：本季 {d['各狀態']['缺值・本季']}、去年同季 {d['各狀態']['缺值・去年同季']}；不適用細分：金融 {d['各狀態']['不適用・金融']}、異業 {d['各狀態']['不適用・異業']}。</p>")

    def ret_table(f):
        d = V[f]["逐筆報酬"]
        rs = "".join(f"<tr><th>{k}</th><td>{x['筆數']}</td><td>{p(x.get('平均'))}</td><td>{p(x.get('中位'))}</td><td>{p(x.get('p25'))}～{p(x.get('p75'))}</td>"
                     f"<td>{pp(x.get('勝率'))}</td><td>{pp(x.get('≥+50%'))}</td></tr>" for k, x in (("留下", d["留下"]), ("剔除", d["剔除"]), ("其中不符", d["其中不符"]), ("其中缺值", d["其中缺值"])))
        return (f"<table><thead><tr><th></th><th>筆數</th><th>平均</th><th>中位</th><th>四分位</th><th>賺錢比例</th><th>≥ +50%</th></tr></thead><tbody>{rs}</tbody></table>"
                f"<p class=m>口徑：{e(d['口徑'])}；描述，不判。</p>")

    def hold_table(f):
        rs = []
        for arm, nm in (("base", "原策略"), ("q1", "加條件")):
            en = V[f]["等效獨立檔數"][arm]
            rs.append(f"<tr><th>{nm}</th>" + "".join(
                f"<td>{C[(f'{f}|{arm}', s)]['平均持股']:.1f} 檔／現金 {pp(C[(f'{f}|{arm}', s)]['平均現金'])}<br><span class=m>等效獨立 {en[s]['平均N_eff']:.1f}（ρ {en[s]['平均ρ']:.2f}）</span></td>"
                for s in SEGS) + "</tr>")
        return ("<table><thead><tr><th></th>" + "".join(f"<th>{s}</th>" for s in SEGS) + "</tr></thead><tbody>" + "".join(rs) + "</tbody></table>"
                f"<p class=m>平均持股、現金取種子中位；等效獨立檔數 ＝ N ÷ (1＋(N−1)ρ)，ρ ＝ 換股日持股前 60 日報酬兩兩平均相關（r＝0）。"
                f"退化（平均持股 ＜ 3 或現金 ＞ 30%）：探索 {'是' if V[f]['退化']['探索'] else '否'}、確認 {'是' if V[f]['退化']['確認'] else '否'}。"
                f"窗尾（2026-08-24）仍持有：原策略 {len(V[f]['窗尾持有']['base'] or [])} 檔、加條件 {len(V[f]['窗尾持有']['q1'] or [])} 檔。</p>")

    secs = []
    for f, nm in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        v = V[f]
        pair = ""
        if f == "fly":
            pc = v["同顆配對"]["確認"]
            pair = f"<p class=m>同顆種子配對（確認段）：加條件年化較高 {pc['年化較高']}／{pc['顆數']} 顆；年化與回落都較好 {pc['年化與回落都較好']} 顆、都較差 {pc['年化與回落都較差']} 顆。</p>"
        secs.append(f"<section><h2>{nm}：{e(v['結論'])}</h2>"
                    f"<p>探索段 {v['段標籤']['探索']}、確認段 {v['段標籤']['確認']} ⇒ 兩段取較嚴「{v['兩段取較嚴']}」；比原策略好：{'是' if v['比原策略好'] else '否'}；早年 {v['早年']}。"
                    f"候選剔除 {v['剔除']['剔除']}／{v['剔除']['訊號']} 筆（{pp(v['剔除']['剔除比例'])}）。</p>"
                    + cmp_table(f) + pair + "<h3>現實版（並報）</h3>" + slip_table(f) + "<h3>剔除比例（逐年）</h3>" + rm_table(f)
                    + "<h3>被剔除 vs 留下的逐筆報酬</h3>" + ret_table(f) + "<h3>持股、現金、等效獨立檔數</h3>" + hold_table(f) + "</section>")
    vf, vv = V["fly"], V["vol"]
    head = (f"<p class=lead><b>結論：{e(vf['結論'])}；{e(vv['結論'])}。</b></p>"
            f"<ul><li>營飆 v1：加條件後確認段 {p(C[('fly|q1', '確認')]['年化'])}／{p(C[('fly|q1', '確認')]['回落'])}，原策略 {p(C[('fly|base', '確認')]['年化'])}／{p(C[('fly|base', '確認')]['回落'])}；"
            f"探索段 {p(C[('fly|q1', '探索')]['年化'])}／{p(C[('fly|q1', '探索')]['回落'])}（原 {p(C[('fly|base', '探索')]['年化'])}／{p(C[('fly|base', '探索')]['回落'])}）。</li>"
            f"<li>營量 v1：加條件後確認段 {p(C[('vol|q1', '確認')]['年化'])}／{p(C[('vol|q1', '確認')]['回落'])}，原策略 {p(C[('vol|base', '確認')]['年化'])}／{p(C[('vol|base', '確認')]['回落'])}；"
            f"探索段 {p(C[('vol|q1', '探索')]['年化'])}／{p(C[('vol|q1', '探索')]['回落'])}（原 {p(C[('vol|base', '探索')]['年化'])}／{p(C[('vol|base', '探索')]['回落'])}）。</li>"
            f"<li>條件是「最近一個已可用季的毛利率 ≥ 去年同季」（裁定 seq321 定 Q1）。營飆候選剔掉 {pp(vf['剔除']['剔除比例'])}、營量候選剔掉 {pp(vv['剔除']['剔除比例'])}。</li>"
            f"<li>⚠ 營量、營飆的結果事前看過 ⇒ 這是事後重切，就算合格也最多「暫定」。⛔ 不能讀成「毛利率沒用」——只測了這一個用法。⛔ 不是買賣建議。</li></ul>")
    gate = S["閘"]["G1G2"]
    notes = ("<section><h2>怎麼算的</h2><ul>"
             "<li>本體：營量 v1、營飆 v1 正式版（資料尾補回 T1、停止交易強制出場開、主窗 2017-03-02～2026-08-24）。出場照原策略（營飆 120 根、營量 60 根收盤）。</li>"
             "<li>毛利率：資料庫 fs_hist 綜合損益表（年初累計）相減成單季，單季毛利 ÷ 單季營收；可用日 ＝ 法定期限（5/15、8/14、11/14、隔年 3/31）之後第一個交易日。</li>"
             "<li>金融保險業與異業（沒有毛利欄）⇒ 不適用、照原策略留下；新上市或季報不足 ⇒ 缺值、算不符剔除。</li>"
             "<li>假訊號臂：同一天在原候選裡隨機剔掉一樣多檔（200 次），用來看「剔掉的是不是剛好那幾檔」有沒有差。</li>"
             "<li>判準：對 0050 同段，年化較高且年化÷回落不低於 0050 ⇒ 合格；探索、確認兩段取較嚴；早年段毛利資料不夠 ⇒ 不可判定。</li>"
             "<li>營飆 v1 的 0050 濾網（0050 在 200 日線上才進）是擋長空頭、不是急跌保護。</li>"
             f"<li>閘門：不加條件時與正式版逐位元相同 —— " + "、".join(f"{k} {v['顆數']} 顆不同 {v['不同']}" for k, v in gate.items()) + "。</li>"
             + (f"<li>獨立查核（--check）：{e(chk.get('結論', ''))}</li>" if chk else "")
             + f"<li>產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）；程式 backtest/researchYLmargin.py；結果 backtest/resultsYLmargin/。</li></ul></section>")
    css = """:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#1f5f8b;--card:#ffffff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;margin:0;padding:24px 16px;max-width:980px;margin:auto}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;border-bottom:2px solid var(--acc);padding-bottom:.2em;margin-top:2em}h3{font-size:1rem;margin-top:1.4em}h4{margin:.8em 0 .3em}
.lead{font-size:1.08rem}.m{color:var(--mut);font-size:.88rem}
table{border-collapse:collapse;width:100%;margin:.4em 0;font-size:.9rem;display:block;overflow-x:auto;background:var(--card)}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{text-align:left}thead th{background:var(--line)}tr.tot td{font-weight:600}"""
    doc = (f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>營收創新高加毛利率</title><style>{css}</style></head><body>"
           f"<h1>營收創新高加毛利率</h1><p class=m>PREREG營收創新高加毛利率 seq2（sha {S['登錄sha']}；裁定 seq321 §四、N_組合 ＋1、Q1）｜回測線｜停止交易強制出場：開</p>"
           + head + "".join(secs) + notes + "</body></html>")
    open(PAGE, "w", encoding="utf-8").write(doc)
    print("寫出", PAGE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "report", "page"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    {"run": run, "report": report, "page": page}[a.mode](a)

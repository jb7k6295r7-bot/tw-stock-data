# -*- coding: utf-8 -*-
"""台股策略線 seq521（裁定 seq399 §五）：十條供應鏈 169 檔【描述快照】——回測線計算子代理。
⛔ 純描述：名單是 2026-10-20 事後挑的，不能拿來回測過去；不計 N、不判、不算任何進場後報酬。
⛔ 不 commit、不改既有檔；research34／researchPTH_freq／research11／patterns／universe_gate／data ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLongPool [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/resultsLongPool/_check.py
輸出 backtest/resultsLongPool/：pool169_20261020.csv、missing.csv、README.md、run.log

資料：tw-stock-data origin/main（SHA 常數）唯讀 git archive：
  每日名單那份 ~/h2data/<sha>/data（stocks、adj、meta、mops/revenue_hist、stocks_per）；
  財報另 archive 到 ~/longpoolwork/<sha10>/data（meta/filing_dates.csv、meta/fs_xbrl、mops/fs_hist、mops/fin_hist）。

讀法（執行者定，README 同文）：
 一 月營收 ＝ research34.load_revenue（revenue_hist，千元）；年增 ＝ 當月營收 ÷ 去年當月營收 − 1（去年當月 ≤ 0 或缺 ⇒ 缺）；
    可用日 ＝ 2025-12 期以前次月 10 日之後、2026-01 期起次月 15 日之後（嚴格大於）；資料日 2026-10-20 ⇒ 2026-09 期可用。
    創 24 月新高 ＝ research34 rev_hi24 原式（當月 ≥ 前 24 個月最大值，且前 24 個月全部有值）。
    加速 ＝ 近 3 月年增平均 − 近 12 月年增平均（2026-07～09 vs 2025-10～2026-09；任一月缺 ⇒ 缺，⛔ 不補）。
 二 季報：存貨 ＝ fs_xbrl inventories（期末，元；cr 合併優先）；營業成本、營業收入、毛利 ＝ fs_hist 一般業 ci（年初累計，千元 ×1000；
    單季 ＝ 本期 − 前期，Q1 不減）；fs_hist 沒有該公司 ⇒ 退 fin_hist（rev_ytd − gp_ytd，元）並標來源。
    存貨週轉天數 ＝ 期末存貨 ÷ 單季營業成本 × 91.25；毛利率 ＝ 單季營業毛利（毛損）淨額（無 ⇒ 營業毛利（毛損））÷ 單季營業收入。
    可用日 ＝ filing_dates uploaded_at：同 (代號, 年, 季) 有 AI1 ⇒ AI1 最早一筆；沒有 AI1 ⇒ 全部文件最早一筆；只取可用日 ＜ 資料日的季。
 三 價格 ＝ data.load_stock 還原價（除權息、減資、面額變更；含息）；
    離 52 週高 ＝ 今日還原收盤 ÷（資料日往前 364 天內最高還原收盤）− 1；
    PTH ＝ researchPTH_freq P2～P4 口徑在最近一個完整月底（2026-09-30）重算全市場（母體 UG.gate3 GATE_V2 ∩ 四碼；
      閘 ＝ patterns.Frame.gate ∧ pit_valid；窗 ＝（2025-09-30, 2026-09-30］還原收盤；未滿 12 月、窗內壞根剔除；前 ⌈30%⌉、同值併入）；
      ⚠ 與 PTH 頻率表差一處：壞根只用 research11.load_bars next_bad（缺口≥5、價格斷點、幽靈還原），沒有併 ~/crashwork/bad_*.pkl（那份只到 2026-09-24 快照）。
    本益比 ＝ stocks_per per（官方，近四季 EPS）資料日當天；5 年百分位 ＝ 資料日往前 5 年（含）每日官方 per 有值日中 ≤ 今日值的比例；
      另附 EPS4Q ＝ fin_hist eps 年初累計差分成單季、可用日 ＜ 資料日的最近 4 季加總，與 自算本益比 ＝ 今日未還原收盤 ÷ EPS4Q（EPS4Q ≤ 0 ⇒ 缺）。
    近一年報酬 ＝ 今日還原收盤 ÷（資料日往前 365 天當天或之前最後一根）還原收盤 − 1；
    窗內壞根（research11.load_bars 口徑＝PTH 同：缺口≥5 交易日 seq335、價格斷點、幽靈還原；不足 260 根或 3718 接續 ⇒ 缺口≥5 ＋ data.breakpoints）
      ⇒ 照算、在 ret_1y_badbar／w52_badbar 列出壞根日期（⛔ 不剔、不補）。
    20 日均量 ＝ 資料日（含）往前 20 個交易日的成交股數平均 ÷ 1000（無成交日算 0）。
    名單 ＝ backtest/resultsDaily/daily_<資料日>.md 第一節（營飆 v1 已達成）、第二節（營量 v1 已達成）、第三節（營量 v1 即將達成）。
 四 3718 中光電投控（2026-09-03 掛牌）接 5371 中光電（最後交易 2026-08-21）：價格以 1:1 接（兩檔 shares 欄同為 390,981,110 ⇒ 推定 1:1，⛔ 未查轉換公告）；
    中間停 8 個交易日（缺口 ≥ 5 ⇒ 依 seq335 屬壞根，近一年報酬、52 週高照算但標旗）；季報用 5371（fs_xbrl、fin_hist、filing_dates 皆 5371）；
    月營收：我方 revenue_hist 全期 5371 0 列 ⇒ 接不上，照實只有 3718 的 2026-08、2026-09。
"""
from __future__ import annotations

import argparse
import glob
import math
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                      # noqa: E402
from backtest import research34 as R34              # noqa: E402  load_revenue（⛔ 只 import）
from backtest import research11 as R11              # noqa: E402  load_bars
from backtest import patterns as P                  # noqa: E402  Frame.gate
from backtest import universe_gate as UG            # noqa: E402
from backtest.addon_daily import okcode             # noqa: E402

UG.set_gate_v2(True)

SHA = "5cb00a60c1fcdc6f2a388a9fbcb50a8812e32584"
DB_REPO = os.path.expanduser("~/tw-stock-data")
H = os.path.expanduser(f"~/h2data/{SHA}/data")
FW = os.path.expanduser(f"~/longpoolwork/{SHA[:10]}")
FUND_PATHS = ["data/meta/filing_dates.csv", "data/meta/fs_xbrl", "data/mops/fs_hist", "data/mops/fin_hist"]
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
MAIL_KEY = "擴大seq520十條供應鏈169檔"
OUT = "backtest/resultsLongPool"
CSV_NAME = "pool169_20261020.csv"
SPLICE = {"3718": "5371"}
DAYS_Q = 91.25
LOG: list = []
_G: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


# ═════════════ 準備 ═════════════
def codes_from_mail():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if MAIL_KEY in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找到 {len(fs)} 封含「{MAIL_KEY}」")
    txt = open(fs[0], encoding="utf-8").read()
    blk = re.search(r"```\n(.*?)```", txt, re.S).group(1)
    codes = blk.splitlines()[0].split()
    if len(codes) != 169 or len(set(codes)) != 169 or not all(re.fullmatch(r"\d{4}", c) for c in codes):
        raise SystemExit(f"⛔ 代號清單 {len(codes)} 檔（唯一 {len(set(codes))}）≠ 169")
    return codes, os.path.basename(fs[0])


def ensure_fund():
    d = os.path.join(FW, "data")
    if all(os.path.exists(os.path.join(FW, p)) for p in FUND_PATHS):
        return d
    tmp = FW + ".tmp"
    subprocess.run(["rm", "-rf", tmp], check=True); os.makedirs(tmp)
    ar = subprocess.Popen(["git", "-C", DB_REPO, "archive", SHA] + FUND_PATHS, stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", tmp], stdin=ar.stdout, check=True)
    if ar.wait() != 0:
        raise SystemExit("⛔ git archive 失敗")
    subprocess.run(["rm", "-rf", FW], check=True); os.replace(tmp, FW)
    return d


# ═════════════ 一、月營收 ═════════════
def rev_avail(p):
    y, m = int(p[:4]), int(p[5:])
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return pd.Timestamp(y2, m2, 15 if p >= "2026-01" else 10)


def revenue_block(codes, asof):
    rev, rev_ly, ind = R34.load_revenue()
    periods = [p for p in rev.index if rev_avail(p) < asof]
    rev, rev_ly = rev.loc[periods], rev_ly.loc[periods]
    last = periods[-1]
    M13 = periods[-13:]
    log(f"[月營收] revenue_hist 期別 {periods[0]}～{last}（可用日 ＜ {asof.date()}）；近 13 月 {M13[0]}～{M13[-1]}")
    rows = {}; miss = []
    for sid in codes:
        r = {}
        if sid not in rev.columns:
            for p in M13:
                r[f"rev_{p}"] = r[f"yoy_{p}"] = r[f"hi24_{p}"] = np.nan
            r["rev_accel"] = np.nan; r["rev_first"] = ""
            rows[sid] = r; miss.append((sid, "月營收全部", "revenue_hist 無此代號")); continue
        rv, rl = rev[sid], rev_ly[sid]
        first = rv.first_valid_index(); r["rev_first"] = first
        yo = {}
        for p in M13:
            k = periods.index(p); v = rv.iloc[k]; ly = rl.iloc[k]
            r[f"rev_{p}"] = v
            yo[p] = v / ly - 1 if (np.isfinite(v) and np.isfinite(ly) and ly > 0) else np.nan
            r[f"yoy_{p}"] = yo[p]
            if np.isfinite(v):
                hist = rv.iloc[max(0, k - 24):k]
                r[f"hi24_{p}"] = bool(len(hist) == 24 and hist.notna().all() and v >= hist.max())
                if not (len(hist) == 24 and hist.notna().all()):
                    r[f"hi24_{p}"] = np.nan          # 前 24 月不全 ⇒ 不可判（研究三原式記 False；本表改記缺、另列 missing）
                    miss.append((sid, f"hi24_{p}", f"前 24 月不全（本代號首期 {first}）"))
            else:
                r[f"hi24_{p}"] = np.nan
                why = f"新上市／新登錄：本代號月營收首期 {first}" if (first is None or p < first) else "該月無資料"
                if sid in SPLICE:
                    why = (f"{sid} 月營收自 {first} 起；原 {SPLICE[sid]} 在我方 revenue_hist（2015-01～2026-09 全部檔）0 列 ⇒ 接不上（照實標，⛔ 不補）")
                miss.append((sid, f"rev_{p}", why))
            if np.isfinite(v) and not np.isfinite(yo[p]):
                miss.append((sid, f"yoy_{p}", "去年當月營收 ≤ 0 或缺" + (f"（新代號去年當月欄為 0；{SPLICE[sid]} 我方無月營收）" if sid in SPLICE else "")))
        y3 = [yo[p] for p in M13[-3:]]; y12 = [yo[p] for p in M13[-12:]]
        r["rev_accel"] = float(np.mean(y3) - np.mean(y12)) if all(np.isfinite(y3 + y12)) else np.nan
        if not np.isfinite(r["rev_accel"]):
            miss.append((sid, "rev_accel", f"近 12 月年增有缺 {sum(not np.isfinite(x) for x in y12)} 個月"))
        r["industry"] = ind.get(sid, "")
        rows[sid] = r
    return rows, M13, miss


# ═════════════ 二、季報 ═════════════
def qkey(y, q):
    return int(y) * 4 + int(q) - 1


def qlabel(k):
    return f"{k // 4}Q{k % 4 + 1}"


def load_filing(FD):
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce")
    fd = fd.dropna(subset=["d"])
    fd["qk"] = [qkey(a, b) for a, b in zip(fd["year"], fd["season"])]
    ai1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "qk"])["d"].min()
    anyd = fd.groupby(["stock_id", "qk"])["d"].min()
    out = anyd.to_dict(); src = {k: "最早文件" for k in out}
    for k, v in ai1.items():
        out[k] = v; src[k] = "AI1"
    return out, src


def load_fs(FD, ids, qk0, qk1):
    """fs_hist ci 損益（千元，年初累計）→ dict[sid] → DataFrame(index=qk)。各檔各讀自己的 header（陷阱 16）。"""
    want = ["營業收入", "營業成本", "營業毛利（毛損）淨額", "營業毛利（毛損）"]
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fs_hist", "*_ci_*.csv"))):
        per = os.path.basename(f)[:6]
        k = qkey(per[:4], per[5])
        if not (qk0 - 1 <= k <= qk1):
            continue
        x = pd.read_csv(f, dtype={"stock_id": str})
        x = x[x["stock_id"].isin(ids)]
        if x.empty:
            continue
        y = pd.DataFrame({"stock_id": x["stock_id"], "qk": k})
        for c in want:
            y[c] = pd.to_numeric(x[c], errors="coerce") * 1000 if c in x.columns else np.nan
        L.append(y)
    F = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last")
    return {s: g.set_index("qk").sort_index() for s, g in F.groupby("stock_id")}


def load_fin(FD, ids, qk0, qk1):
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv"))):
        per = os.path.basename(f)[:6]; k = qkey(per[:4], per[5])
        if not (qk0 - 4 <= k <= qk1):
            continue
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "period", "rev_ytd", "gp_ytd", "eps_ytd"])
        x = x[x["stock_id"].isin(ids)].copy(); x["qk"] = k
        L.append(x)
    F = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last")
    for c in ("rev_ytd", "gp_ytd", "eps_ytd"):
        F[c] = pd.to_numeric(F[c], errors="coerce")
    return {s: g.set_index("qk").sort_index() for s, g in F.groupby("stock_id")}


def load_xbrl(FD, ids, qk0, qk1):
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        yr = int(os.path.basename(f)[8:12])
        if yr < qk0 // 4 or yr > qk1 // 4:
            continue
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "inventories", "revenue_ytd"])
        x = x[x["stock_id"].isin(ids)].copy()
        x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        x["qk"] = [qkey(p[:4], p[-1]) for p in x["period"]]
        L.append(x)
    X = pd.concat(L)
    X["inventories"] = pd.to_numeric(X["inventories"], errors="coerce")
    return {s: g.set_index("qk").sort_index() for s, g in X.groupby("stock_id")}


def single(ytd: pd.Series, k):
    """年初累計 → 單季（Q1 不減）；缺前期 ⇒ NaN。"""
    v = ytd.get(k, np.nan)
    if k % 4 == 0:
        return v
    pv = ytd.get(k - 1, np.nan)
    return v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan


def fin_block(codes, asof, FD):
    fmin, fsrc = load_filing(FD)
    src_id = {s: SPLICE.get(s, s) for s in codes}
    ids = sorted(set(src_id.values()))
    # 每檔最近一季可用（可用日 ＜ 資料日）
    qk_last_all = max(k for (s, k), d in fmin.items() if s in ids and d < asof)
    QK = list(range(qk_last_all - 7, qk_last_all + 1))
    FS = load_fs(FD, ids, QK[0], QK[-1]); FN = load_fin(FD, ids, QK[0] - 3, QK[-1]); XB = load_xbrl(FD, ids, QK[0], QK[-1])
    log(f"[季報] 近 8 季 {qlabel(QK[0])}～{qlabel(QK[-1])}；fs_hist ci {len(FS)} 檔、fin_hist {len(FN)} 檔、fs_xbrl {len(XB)} 檔（來源代號 {len(ids)}）")
    rows = {}; miss = []
    for sid in codes:
        s = src_id[sid]; r = {}
        fs = FS.get(s); fn = FN.get(s); xb = XB.get(s)
        nots = 0
        r["fs_src"] = "fs_hist" if fs is not None else ("fin_hist" if fn is not None else "")
        for k in QK:
            q = qlabel(k)
            av = fmin.get((s, k)); r[f"fs_avail_{q}"] = av.strftime("%Y-%m-%d %H:%M:%S") + f"（{fsrc[(s, k)]}）" if av is not None else ""
            ok = av is not None and av < asof
            if av is None:
                nots += 1
            if fs is not None:
                rev_q = single(fs["營業收入"], k); cogs = single(fs["營業成本"], k)
                gpn = fs["營業毛利（毛損）淨額"] if fs["營業毛利（毛損）淨額"].notna().any() else fs["營業毛利（毛損）"]
                gp_q = single(gpn, k)
            elif fn is not None:
                rev_q = single(fn["rev_ytd"], k); gp_q = single(fn["gp_ytd"], k)
                cogs = rev_q - gp_q if (np.isfinite(rev_q) and np.isfinite(gp_q)) else np.nan
            else:
                rev_q = cogs = gp_q = np.nan
            inv = xb["inventories"].get(k, np.nan) if xb is not None else np.nan
            if not ok:
                inv = cogs = gp_q = rev_q = np.nan
            r[f"inv_{q}"] = inv
            r[f"cogs_{q}"] = cogs
            r[f"inv_days_{q}"] = inv / cogs * DAYS_Q if (np.isfinite(inv) and np.isfinite(cogs) and cogs > 0) else np.nan
            r[f"gm_{q}"] = gp_q / rev_q if (np.isfinite(gp_q) and np.isfinite(rev_q) and rev_q > 0) else np.nan
            if not np.isfinite(r[f"inv_days_{q}"]):
                if not ok and av is None:
                    why = "filing_dates（t57sb01）無該季上傳時戳 ⇒ 可用日不明、不給值（⛔ 不補）"
                elif not ok:
                    why = f"可用日 {av.date()} 未早於資料日"
                elif xb is None or k not in xb.index:
                    why = "fs_xbrl 無該季列"
                elif not np.isfinite(inv):
                    why = "fs_xbrl 該季無存貨科目（空白≠0）"
                elif not np.isfinite(cogs):
                    why = "營業成本缺（fs_hist／fin_hist 無該季或缺前期累計）"
                else:
                    why = f"營業成本 ≤ 0（{cogs:.0f}）"
                miss.append((sid, f"inv_days_{q}", why))
            if not np.isfinite(r[f"gm_{q}"]) and ok:
                miss.append((sid, f"gm_{q}", "營收／毛利缺（fs_hist／fin_hist 無該季或缺前期累計）"))
        r["fs_quarters_no_ts"] = nots
        # EPS4Q（fin_hist；可用日 ＜ 資料日的最近 4 季）
        e4 = np.nan; e4q = ""
        if fn is not None:
            okk = [k for k in fn.index if fmin.get((s, k)) is not None and fmin[(s, k)] < asof]
            if okk:
                kl = max(okk); eq = [single(fn["eps_ytd"], k) for k in range(kl - 3, kl + 1)]
                if all(np.isfinite(eq)):
                    e4 = float(sum(eq)); e4q = f"{qlabel(kl - 3)}～{qlabel(kl)}"
        r["eps4q"] = e4; r["eps4q_quarters"] = e4q
        if not np.isfinite(e4):
            miss.append((sid, "eps4q", "fin_hist 近 4 季 EPS 不全或無時戳"))
        if sid in SPLICE:
            r["fs_src"] += f"（接 {s}）"
        rows[sid] = r
    return rows, QK, miss


# ═════════════ 三、價格、PTH、本益比、名單 ═════════════
def pth_job(sid):
    cal = _G["cal"]; t = _G["t"]; s0 = _G["s0"]
    D.DATA = H
    B = R11.load_bars(sid, _G["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, "不足260根", np.nan
    idx = B["idx"].astype(np.int64); nb = len(idx)
    c = np.asarray(B["c"], float)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    f = P.Frame(B["df"], set())
    gate = bool(np.asarray(f.gate, bool)[t]) and bool(UG.pit_valid(sid, cal, H)[t])
    posk = np.full(len(cal), -1, np.int64); posk[idx] = np.arange(nb)
    if not gate or posk[t] < 0:
        return sid, "閘外(500張/pit)", np.nan
    kt = int(posk[t]); k12 = int(np.searchsorted(idx, s0, "right")) - 1
    if k12 < 0:
        return sid, "未滿12月", np.nan
    k0 = k12 + 1
    if bad[k0 + 1:kt + 1].any():
        return sid, "窗內壞根", np.nan
    return sid, "排序母體", float(c[kt] / c[k0:kt + 1].max())


def pth_market(cal, procs):
    s = pd.Series(np.arange(len(cal)), index=cal)
    g = s.groupby([cal.year, cal.month]).max()
    ME = list(g.to_numpy()); MK = list(g.index)
    if cal[-1] < cal[-1] + pd.offsets.BMonthEnd(0):           # 資料尾月不完整 ⇒ 不算（PTH P2）
        ME, MK = ME[:-1], MK[:-1]
    t, s0 = int(ME[-1]), int(ME[-13])
    st = pd.read_csv(os.path.join(H, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st); U = U[U["stock_id"].map(okcode)].reset_index(drop=True)
    _G.update(cal=cal, t=t, s0=s0, mk=dict(zip(U["stock_id"], U["market"])))
    with Pool(procs) as pool:
        res = pool.map(pth_job, list(U["stock_id"]), chunksize=20)
    df = pd.DataFrame(res, columns=["stock_id", "st", "pth"])
    v = df.loc[df["st"] == "排序母體", "pth"].to_numpy(float)
    n = len(v); k = int(math.ceil(0.3 * n)); cut = float(np.sort(v)[::-1][k - 1])
    df["top30"] = (df["st"] == "排序母體") & (df["pth"] >= cut)
    info = {"月底": str(cal[t].date()), "窗起（前 12 個月底）": str(cal[s0].date()), "母體": len(U), "排序母體 n": n, "k": k,
            "切點": round(cut, 6), "入選": int(df["top30"].sum()), "狀態": df["st"].value_counts().to_dict()}
    log(f"[PTH] {info}")
    return df.set_index("stock_id"), info, cut


def load_px(sid, market, cal):
    """還原價框；3718 接 5371（1:1）。回 (df, note)。"""
    st = D.load_stock(sid, market, cal)
    if sid not in SPLICE:
        return (st.df if st else None), ""
    old = D.load_stock(SPLICE[sid], "tpex", cal)
    df = st.df.copy()
    m = old.df["traded"] & ~df["traded"]
    for c in ["open", "high", "low", "close", "volume", "amount", "traded"]:
        df.loc[m, c] = old.df.loc[m, c]
    return df, f"接 {SPLICE[sid]}（1:1 推定）"


def per_series(sid):
    p = os.path.join(H, "stocks_per", f"{sid}.csv")
    if not os.path.exists(p):
        return None
    x = pd.read_csv(p, usecols=["date", "per"])
    x["date"] = pd.to_datetime(x["date"]); x["per"] = pd.to_numeric(x["per"], errors="coerce")
    return x.drop_duplicates("date").set_index("date")["per"].sort_index()


def daily_lists(asof):
    f = f"backtest/resultsDaily/daily_{asof.date()}.md"
    if not os.path.exists(f):
        raise SystemExit(f"⛔ 沒有 {f}")
    L = open(f, encoding="utf-8").read().splitlines()
    if not L[0].startswith(f"# 每日名單 {asof.date()}"):
        raise SystemExit(f"⛔ {f} 抬頭不是資料日")
    sec = {"一": "營飆v1已達成", "二": "營量v1已達成", "三": "營量v1即將達成"}
    out = {v: set() for v in sec.values()}; cur = None
    for x in L:
        if x.startswith("## "):
            cur = next((v for k, v in sec.items() if x.startswith(f"## {k}、")), None); continue
        if cur is None:
            continue
        m = re.match(r"^- (\d{4}) ", x) or re.match(r"^\| (\d{4}) ", x)
        if m:
            out[cur].add(m.group(1))
    return out, f


def price_block(codes, mk, asof, cal, pth, procs_unused=None):
    n = len(cal); lists, lf = daily_lists(asof)
    log(f"[名單] {lf}：" + "；".join(f"{k} {sorted(v)}" for k, v in lists.items()))
    rows = {}; miss = []
    for sid in codes:
        r = {}; market = mk[sid]
        if market == "emerging":
            for c in ("close_adj", "pct_from_52w_high", "pth_2026-09", "pth_top30", "per", "per_pct5y", "per_eps4q_own", "ret_1y"):
                r[c] = np.nan
                miss.append((sid, c, "興櫃：close 為均價、無開收盤（技術欄不適用）；stocks 只自 2026-09-03 起"))
        df, note = load_px(sid, market, cal)
        r["px_note"] = note
        if df is None:
            rows[sid] = r; continue
        c = df["close"].to_numpy(float); v = df["volume"].to_numpy(float)
        tr = np.flatnonzero(np.isfinite(c))
        vol20 = np.nan_to_num(v[n - 20:n], nan=0.0).mean() / 1000.0
        r["vol20_lots"] = vol20; r["vol20_ge500"] = bool(vol20 >= 500)
        r["traded_today"] = bool(np.isfinite(c[n - 1]))
        for k_, v_ in lists.items():
            r[k_] = sid in v_
        if market == "emerging":
            rows[sid] = r; continue
        last = tr[-1]; r["close_adj"] = c[last]; r["last_trade"] = str(cal[last].date())
        if last != n - 1:
            miss.append((sid, "close_adj", f"資料日無成交，用 {cal[last].date()}"))
        # 壞根（日曆位置）：research11.load_bars 口徑（缺口≥5／價格斷點／幽靈還原，同 PTH）；不足 260 根或 3718 接續 ⇒ 缺口≥5 ＋ data.breakpoints
        B = None if sid in SPLICE else R11.load_bars(sid, market, cal)
        if B is not None:
            ib = B["idx"].astype(np.int64); nb = len(ib)
            badpos = ib[np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)]
        else:
            ev = D.load_adj(sid)
            badpos = np.r_[tr[1:][np.diff(tr) - 1 >= 5],
                           [b["pos"] for b in D.breakpoints(df, set(ev["date"]) if ev is not None else set()) if D.applies(b)]].astype(np.int64)
        w0 = int(cal.searchsorted(asof - pd.Timedelta(days=364)))
        hi = np.nanmax(c[w0:n]); r["high_52w_adj"] = hi
        r["pct_from_52w_high"] = c[last] / hi - 1
        bw = sorted(set(int(p) for p in badpos if w0 < p <= last))
        r["w52_badbar"] = "、".join(str(cal[p].date()) for p in bw)
        first_tr = cal[tr[0]]
        r["listed_lt_52w"] = bool(first_tr > cal[w0])
        # 近一年報酬
        y0 = int(cal.searchsorted(asof - pd.Timedelta(days=365), side="right")) - 1
        ty = tr[tr <= y0]
        if len(ty) == 0:
            r["ret_1y"] = np.nan; miss.append((sid, "ret_1y", f"上市未滿一年（首根 {first_tr.date()}）"))
        else:
            k0 = ty[-1]; r["ret_1y"] = c[last] / c[k0] - 1; r["ret_1y_base_date"] = str(cal[k0].date())
            by = sorted(set(int(p) for p in badpos if k0 < p <= last))
            r["ret_1y_badbar"] = "、".join(str(cal[p].date()) for p in by)
        # PTH
        if sid in pth.index:
            r["pth_2026-09"] = pth.at[sid, "pth"]; r["pth_status"] = pth.at[sid, "st"]; r["pth_top30"] = bool(pth.at[sid, "top30"])
            if pth.at[sid, "st"] != "排序母體":
                r["pth_top30"] = np.nan
                why = f"PTH 口徑剔除：{pth.at[sid, 'st']}"
                if sid in SPLICE:
                    why += f"（{sid} 自身不足 260 根；接 {SPLICE[sid]} 後窗內有 8 個交易日停牌缺口，缺口 ≥ 5 ＝ 壞根 ⇒ 口徑上仍不排序）"
                miss.append((sid, "pth_top30", why))
        else:
            r["pth_2026-09"] = np.nan; r["pth_top30"] = np.nan; r["pth_status"] = "不在母體"
            miss.append((sid, "pth_top30", "不在 PTH 母體（UG.gate3 v2 ∩ 四碼）" + ("；3718 新代號未滿 12 月" if sid in SPLICE else "")))
        # 本益比（官方）
        ps = per_series(sid)
        if sid in SPLICE:
            po = per_series(SPLICE[sid])
            ps = po if ps is None else pd.concat([po, ps]).sort_index()
        if ps is None or asof not in ps.index or not np.isfinite(ps.get(asof, np.nan)) or ps.get(asof) <= 0:
            r["per"] = np.nan; r["per_pct5y"] = np.nan
            why = "stocks_per 無此代號" if (ps is None) else ("stocks_per 資料日無列" if asof not in ps.index else "官方 per 空白（多為近四季 EPS ≤ 0）")
            if sid in SPLICE:
                why += f"（3718 無 stocks_per 檔；{SPLICE[sid]} 只到 2026-08）"
            miss.append((sid, "per", why))
        else:
            today = float(ps.get(asof)); h5 = ps[(ps.index > asof - pd.DateOffset(years=5)) & (ps.index <= asof)]
            h5 = h5[np.isfinite(h5) & (h5 > 0)]
            r["per"] = today; r["per_pct5y"] = float((h5 <= today).mean()); r["per_5y_days"] = int(len(h5))
            r["per_5y_from"] = str(h5.index.min().date())
            if h5.index.min() > asof - pd.DateOffset(years=5) + pd.Timedelta(days=30):
                miss.append((sid, "per_pct5y", f"本益比序列不足 5 年（自 {h5.index.min().date()}，{len(h5)} 日）——百分位照算、只在可得期間"))
        rows[sid] = r
    return rows, miss, lists


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    t0 = time.time()
    codes, mail = codes_from_mail()
    log(f"[信] {mail}：{len(codes)} 檔")
    D.DATA = H
    tip = subprocess.run(["git", "-C", DB_REPO, "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    log(f"[資料] origin/main {tip[:10]}（本件用 {SHA[:10]}{'' if tip == SHA else '⚠ 與最新不同'}）；daily archive {H}")
    FD = ensure_fund(); log(f"[財報 archive] {FD}")
    cal = D.load_calendar(); asof = cal[-1]
    px2330 = pd.read_csv(os.path.join(H, "stocks", "2330.csv"), usecols=["date"])["date"].max()
    if str(asof.date()) != px2330:
        raise SystemExit(f"⛔ 日曆尾 {asof.date()} ≠ 2330 價格尾 {px2330}")
    log(f"[資料日] {asof.date()}")
    st = pd.read_csv(os.path.join(H, "meta", "stocks.csv"), dtype=str).set_index("stock_id")
    mk = st["market"].to_dict(); nm = st["name"].to_dict()
    R1, M13, m1 = revenue_block(codes, asof)
    R2, QK, m2 = fin_block(codes, asof, FD)
    pth, pinfo, cut = pth_market(cal, a.procs)
    R3, m3, lists = price_block(codes, mk, asof, cal, pth)
    rows = []
    for sid in codes:
        r = {"stock_id": sid, "name": nm[sid], "market": mk[sid], "industry": R1[sid].get("industry", ""),
             "ky": "KY" in nm[sid], "first_seen": st.at[sid, "first_seen"], "data_date": str(asof.date())}
        if sid in SPLICE:
            r["note"] = "3718 2026-09-03 掛牌；價格、季報、本益比接 5371（1:1 推定）；月營收 5371 我方 0 列 ⇒ 接不上"
        r.update(R1[sid]); r.update(R2[sid]); r.update(R3[sid])
        rows.append(r)
    df = pd.DataFrame(rows)
    # 欄序
    lead = ["stock_id", "name", "market", "industry", "ky", "first_seen", "data_date", "note"]
    revc = [f"{x}_{p}" for p in M13 for x in ("rev", "yoy", "hi24")] + ["rev_accel", "rev_first"]
    fsc = [f"{x}_{qlabel(k)}" for k in QK for x in ("inv_days", "gm", "inv", "cogs", "fs_avail")] + ["fs_src", "fs_quarters_no_ts", "eps4q", "eps4q_quarters"]
    pxc = ["close_adj", "last_trade", "traded_today", "high_52w_adj", "pct_from_52w_high", "w52_badbar", "listed_lt_52w", "pth_2026-09", "pth_status", "pth_top30",
           "per", "per_pct5y", "per_5y_days", "per_5y_from", "per_eps4q_own", "ret_1y", "ret_1y_base_date", "ret_1y_badbar",
           "vol20_lots", "vol20_ge500", "營飆v1已達成", "營量v1已達成", "營量v1即將達成", "px_note"]
    # 自算本益比 ＝ 今日未還原收盤 ÷ EPS4Q
    raw_close = {}
    for sid in codes:
        if mk[sid] == "emerging":
            continue
        x = pd.read_csv(os.path.join(H, "stocks", f"{sid}.csv"), usecols=["date", "close"]).dropna()
        raw_close[sid] = float(x["close"].iloc[-1])
    df["per_eps4q_own"] = [raw_close[s] / e if (s in raw_close and np.isfinite(e) and e > 0) else np.nan for s, e in zip(df["stock_id"], df["eps4q"])]
    for c in lead + revc + fsc + pxc:
        if c not in df.columns:
            df[c] = np.nan
    df = df[lead + revc + fsc + pxc]
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, CSV_NAME), index=False, encoding="utf-8-sig", float_format="%.6g")
    ms = pd.DataFrame(m1 + m2 + m3, columns=["stock_id", "field", "reason"])
    ms.insert(1, "name", ms["stock_id"].map(nm)); ms.insert(2, "market", ms["stock_id"].map(mk))
    ms = ms.drop_duplicates().sort_values(["stock_id", "field"]).reset_index(drop=True)
    ms.to_csv(os.path.join(OUT, "missing.csv"), index=False, encoding="utf-8-sig")
    log(f"[交件] {CSV_NAME} {df.shape}；missing.csv {len(ms)} 列（{ms['stock_id'].nunique()} 檔）")
    log(f"[摘要] 2026-09 創24月新高 {int((df['hi24_2026-09'] == True).sum())} 檔；PTH 前30% {int((df['pth_top30'] == True).sum())} 檔；"
        f"20日均量≥500 {int(df['vol20_ge500'].fillna(False).astype(bool).sum())} 檔；名單 " + "、".join(f"{k} {int(df[k].fillna(False).astype(bool).sum())}" for k in lists))
    bb = df[df["ret_1y_badbar"].fillna("") != ""]
    log(f"[壞根] 近一年窗內有壞根 {len(bb)} 檔：" + "；".join(f"{s} {b}" for s, b in zip(bb["stock_id"], bb["ret_1y_badbar"])))
    log(f"[耗時] {time.time() - t0:.0f}s")
    _G["pinfo"] = pinfo; _G["M13"] = M13; _G["QK"] = QK
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as fo:
        fo.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

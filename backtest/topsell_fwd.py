# -*- coding: utf-8 -*-
"""頂部樣子 前瞻紀錄（PREREG 大漲後頂部樣子當賣出訊號 seq1，sha e30036415fbbce81；裁定 seq443 §三：依構造不可判定、N_前段 −1、轉前瞻，
每月記 S 成立者與同月母體之後 12 個月表現，累積到兩段各 n_eff ≥ 30 再判）——回測線開發子代理，2026-10-22。
⛔ 不寫第二份：條件、報酬一律 topsell_cond（＝ 頻率表同式，topsell_fwd_check F1 逐列重現已凍結頻率表證明）；世界 ＝ pth10_daily._wjob2（RLU._wjob ＋
   RA.extra_stock）＋ researchIndMom_freq._panel_job（頻率表價格面板同一支）；版本與快照 ＝ bigrun_monthly（asof_commit、ensure_snapshot、ensure_fund、put_daily）；
   財報可用日 ＝ researchLongPool.load_filing（AI1 最早、否則最早文件）；產業 ＝ researchIndRev_prereg.PIT。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.topsell_fwd --sha <main sha> [--asof YYYY-MM-DD] [--md <每日名單 md>]
    選項：--fwd DIR（預設 backtest/forward/topsell）｜--nowrite｜--procs N（預設 3）｜--start YYYY-MM（測試用，預設 2026-09）｜--fund-at SHA（測試用：財報／集保固定版本）
    fixture：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.topsell_fwd_check

讀法（V 標；★＝執行者定，寫死於 2026-10-22）：
 V1 誰、何時：形成月 m 的月底 t ＝ researchPTH_freq.month_ends（該月最後交易日）；★ 判定夜 ＝ t 的下一交易日（＝ 每月第一個交易日晚上，run_daily_list 每晚呼叫、
    沒到就只看到期）。待判 ＝ m ≥ 起始月（2026-09）∧ t ＜ 資料日 ∧ state 沒有 m；漏跑的月份下一次一併補（照月序）。
    ⭐ 起始月 2026-09（月底 2026-09-30、進場 2026-10-01 開盤）於 2026-10-22 首次執行時補記（判定一律只用 ≤ t 的資料，見 V3）。
 V2 母體、訊號 ＝ 頻率表 T2、T3 原式（topsell_cond）；★ 去重的歷史：本檔 events.csv 已記的入判列 ＋ 起始月之前取已凍結頻率表 resultsTopSell/freq/events.csv.gz。
    產業中位成員 ＝ 該月底存活（最後有效 K 棒距月底 ≤ 20 交易日）∧ 市值 ＞ 0（快照 stocks 原始收盤×股數，向前延用）∧ PIT 產業不在排除類 ∧ ROE 有值。
    ★ V2′ 股票池 ＝ UG.gate3 ∩ 四碼 ∩「到判定夜為止有效 K 棒 ≥ 260 根」（load_bars 門檻以當晚計）。⚠ 已凍結頻率表的面板是以 2026-09-24 資料尾計 260 根
    （歷史上多收了之後才滿 260 根的新股，主要影響產業中位成員）⇒ 前瞻比頻率表更嚴、是當晚可知的版本；fixture F3 ③ 驗「晚判舊月 ＝ 當晚判」。
 V3 版本（不前視）：價格、本益比、產業 ＝ --sha 的唯讀快照（run_daily_list 同一份），日曆截到資料日；判定只取 ≤ t 的列（R36、距一年高點、500 張閘、月底 per）；
    財報、集保 ＝ main 在「判定夜 23:59（台北）」當時的版本（bigrun_monthly.asof_commit）；財報季 ＝ 上傳日 ＜ t 的最新季；集保 ＝ t 前一交易日或更早 14 交易日內最近一筆。
    e（t 下一交易日）旗標（壞根(t,e]、e 無成交、e 開盤鎖漲停）是實際進場狀況，照記。
 V4 凍結：events.csv 只追加；已寫的格 ⛔ 不重算、不改；到期欄只在「空白」時填一次（之後凍結）。每次寫回前核對舊的非空格逐字不變，否則中止不寫。
 V5 到期：12 個月 ＝ e＋12 個曆月（topsell_cond.window_end），資料日 ≥ 該日 ⇒ 填 R12、出場12、腰斬12、最大回落12；6 個月同式（描述）。
    同月入判 ∧ 可用（e 有成交、(t,e] 無壞根）列全部填好 ⇒ 填「同月對照R12平均」（S 不成立者 R12 平均）與 S 成立列 d12 ＝ R12 − 該平均（登錄 §四：對同月其他大漲股；
    成本兩邊各 0.585% 抵銷，R淨 ＝ R − 0.585% 另列）；6 個月同。判定（兩段各 n_eff ≥ 30）由回測線另做，本檔不判。
 V6 每日名單 ★：只在「判定夜」或「到期填報酬的那晚」於名單尾加一節「## 十三、頂部樣子前瞻（內部・不推 LINE）」一行狀態（⛔ 不帶【LINE】、不推）；
    其他夜晚移除本節（同資料日重產名單 ⇒ 依 state 補回，冪等）；失敗只記 log（run_daily_list 規則 15）。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO); sys.path.insert(0, os.path.join(REPO, "backtest"))
from backtest import topsell_cond as TC                     # noqa: E402  唯一條件／報酬來源
from backtest import bigrun_monthly as BM                   # noqa: E402  asof_commit、ensure_snapshot、ensure_fund、put_daily、git
from backtest import pth10_daily as PD                      # noqa: E402  universe、_wjob2、_LW（⛔ 只 import）
from backtest import researchIndMom_freq as IMF             # noqa: E402  _panel_job（頻率表價格面板同一支）
from backtest import researchRevLimitUp as RLU              # noqa: E402  _G
from backtest import researchPTH_freq as PF                 # noqa: E402  month_ends
from backtest import researchLongPool as LP                 # noqa: E402  load_filing、qkey
from backtest import researchIndRev_prereg as PRE           # noqa: E402  load_rev、PIT
from backtest import data as D                              # noqa: E402

FWD = os.path.join(REPO, "backtest", "forward", "topsell")
FREQ_EV = os.path.join(REPO, "backtest", "resultsTopSell", "freq", "events.csv.gz")
WORK = os.path.expanduser("~/tpswork")
START = "2026-09"
MIN_BARS = 260                                              # research11.load_bars 的門檻（< 260 根回 None）
SEC ="## 十三、頂部樣子前瞻"
TD_PATHS = ["data/tdcc_hist", "data/tdcc"]
JUDGE_COLS = ["形成月", "t", "sid", "名稱", "入判", "R36_36月完整無壞根", "產業", "產業ROE有值數", "產業ROE中位", "ROE", "本益比", "本益比5年月底位置",
              "近4季EPS", "財報季", "財報可用日", "集保12月變化", "T1a", "T1b", "T1", "T2", "T3", "S", "S12"]
ENTRY_COLS = ["e", "壞根(t,e]", "e無成交", "e開盤鎖漲停", "可用"]
META_COLS = ["判定夜", "資料日", "sha", "財報集保版本"]
FILL_COLS = ["到期日6", "R6", "出場6", "填於6", "同月對照R6平均", "d6",
             "到期日12", "R12", "出場12", "腰斬12", "最大回落12", "填於12", "同月對照R12平均", "d12"]
COLS = JUDGE_COLS + ENTRY_COLS + META_COLS + FILL_COLS
_W: dict = {}


def log(s):
    print(f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}", flush=True)


def ym(d):
    d = pd.Timestamp(d); return f"{d.year}-{d.month:02d}"


def ymi(s):
    return int(s[:4]) * 12 + int(s[5:7]) - 1


# ═════════════ 月份判斷（純函式，fixture F2）═════════════
def pending_months(cal, asof, done, start=START):
    """回 [(形成月, 月底位置, 判定夜位置)]：月底 t ＜ 資料日 ∧ 形成月 ≥ start ∧ 不在 done；照月序。cal 已截到資料日。"""
    ME, MK = PF.month_ends(cal)
    out = []
    for p, (y, m) in zip(ME, MK):
        key = f"{y}-{m:02d}"
        if key >= start and key not in done and cal[p] < asof and p + 1 < len(cal):
            out.append((key, int(p), int(p) + 1))
    return out


# ═════════════ 世界（逐股：pth10_daily._wjob2 ＋ researchIndMom_freq._panel_job）═════════════
def _job(a):
    sid, mk = a
    s, v, b = PD._wjob2((sid, mk))
    if v is None:
        return sid, None
    cal = PD._LW["cal"]; n0 = len(cal)
    key = "主"                                  # _panel_job 只在 wn＝"主" 時回市值（本子程序內覆寫，不影響他人）
    IMF._G[key] = {"data": PD._LW["data"], "cal": cal, "n0": n0, "ix": {sid: 0}, "mk": {sid: mk},
                   "BADPOS": {sid: set(int(x) for x in b)}, "PV": np.asarray(v["pv"], bool)[None, :]}
    _, r = IMF._panel_job((key, sid))
    if r is None:
        return sid, None
    C, BAD, G, MC = r
    per = np.full(n0, np.nan)
    f = os.path.join(PD._LW["data"], "stocks_per", f"{sid}.csv")
    if os.path.exists(f):
        z = pd.read_csv(f, dtype={"date": str}, usecols=["date", "per"]).drop_duplicates("date", keep="last")
        iz = cal.get_indexer(pd.to_datetime(z["date"])); ok = iz >= 0
        vv = pd.to_numeric(z["per"], errors="coerce").to_numpy(float)[ok]
        per[iz[ok]] = np.where(vv > 0, vv, np.nan)
    return sid, {"C": C, "BAD": BAD, "G": G, "MC": MC, "O": np.asarray(v["o"], float)[:n0], "TRD": np.asarray(v["trd"], bool)[:n0],
                 "UPL": np.asarray(v["upl"], bool)[:n0], "PER": per}


def build_world(DATA, cal, sids, procs):
    D.DATA = DATA
    mk, names = PD.universe(DATA)
    todo = sorted(mk) if sids is None else sorted(set(sids) & set(mk))
    RLU._G["cal"] = cal; PD._LW.update(data=DATA, cal=cal)
    res = {}
    if todo:
        with Pool(procs) as pool:
            for sid, r in pool.imap_unordered(_job, [(s, mk[s]) for s in todo], chunksize=8):
                if r is not None:
                    res[sid] = r
    return res, names


# ═════════════ 財報、集保 ═════════════
def load_fund(FD, sids):
    av, _ = LP.load_filing(FD)
    AV = {}
    for (s, q), d in av.items():
        AV.setdefault(s, []).append((pd.Timestamp(d).normalize(), int(q)))
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv"))):
        b = os.path.basename(f)[:6]
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd", "nip_ytd", "equity_parent"])
        x = x[x["stock_id"].isin(sids)].copy(); x["qk"] = LP.qkey(b[:4], b[5]); L.append(x)
    FN = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last")
    for c in ("eps_ytd", "nip_ytd", "equity_parent"):
        FN[c] = pd.to_numeric(FN[c], errors="coerce")
    FIN = {s: {c: g.set_index("qk")[c].to_dict() for c in ("eps_ytd", "nip_ytd", "equity_parent")} for s, g in FN.groupby("stock_id")}
    return AV, FIN


def sel_q(AV, sid, t):
    c = [(q, d) for d, q in AV.get(sid, []) if d < t]
    return max(c) if c else (-1, None)


def ensure_tdcc(commit):
    root = os.path.join(WORK, f"tdcc_{commit[:10]}")
    if not os.path.isdir(os.path.join(root, "data")):
        paths = [p for p in TD_PATHS if subprocess.run(["git", "-C", REPO, "cat-file", "-e", f"{commit}:{p}"]).returncode == 0]
        tmp = BM._archive(commit, paths, root)
        subprocess.run(["rm", "-rf", root], check=True); os.replace(tmp, root)
    return os.path.join(root, "data")


def load_tdcc(TDD, cal, sids):
    """{sid: 日曆長 pct 陣列}；資料日非交易日 ⇒ 記在其後第一個交易日（面板同）；同位置後者蓋前者。"""
    L = []
    for f in sorted(glob.glob(os.path.join(TDD, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "pct"]); x = x[x["level"] == 15]
        L.append(pd.DataFrame({"date": x["date"].astype(str), "stock_id": x["stock_id"].astype(str), "pct": x["pct"].astype(float)}))
    for f in sorted(glob.glob(os.path.join(TDD, "tdcc", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "level", "pct"]); x = x[x["level"] == 15]
        L.append(pd.DataFrame({"date": x["date"], "stock_id": x["stock_id"], "pct": pd.to_numeric(x["pct"], errors="coerce")}))
    T = pd.concat(L, ignore_index=True)
    T = T[T["stock_id"].isin(sids)].drop_duplicates(["stock_id", "date"], keep="last").sort_values(["stock_id", "date"])
    n0 = len(cal); out = {}
    for s, g in T.groupby("stock_id"):
        a = np.full(n0, np.nan); pi = cal.searchsorted(pd.to_datetime(g["date"])); ok = pi < n0
        a[pi[ok]] = g["pct"].to_numpy(float)[ok]
        out[s] = a
    return out


# ═════════════ 判一個月底（純函式，fixture F5 突變測試）═════════════
def judge_month(W, cal, ME, k, AV, FIN, TD, PIT, names, last_taken):
    """W ＝ {sid: 世界列}；ME ＝ 月底位置陣列；k ＝ 本月在 ME 的序；last_taken ＝ {sid: 最後入判形成月序(年×12＋月−1)}（會就地更新）。
    回 list[dict]（JUDGE_COLS ＋ ENTRY_COLS）。只讀 ≤ ME[k] 的價格與 ≤ t 的財報、≤ t−1 的集保；e 旗標為實際進場狀況。"""
    p = int(ME[k]); t = cal[p]; n0 = len(cal); mkey = ym(t); mi = ymi(mkey)
    pk = {j: int(ME[j]) for j in range(max(0, k - TC.PE_WIN + 1), k + 1)}
    p36 = int(ME[k - 36]) if k >= 36 else -1
    VP = {s: np.flatnonzero(np.isfinite(r["C"][:p + 1])) for s, r in W.items()}

    def alive_at(s, pp):
        vp = VP[s]; return len(vp) > 0 and TC.alive(vp, pp)
    # 產業中位（同月同產業、存活 ∧ 市值 ＞ 0、ROE 有值）
    roe = {}; ind = {}; qinfo = {}
    for s, r in W.items():
        if not alive_at(s, p) or not (np.isfinite(r["MC"][p]) and r["MC"][p] > 0):
            continue
        q, qd = sel_q(AV, s, t); qinfo[s] = (q, qd)
        f = FIN.get(s, {})
        roe[s] = TC.roe4(f.get("nip_ytd"), f.get("equity_parent"), q)
        i_, _ = PIT.at(s, t)
        ind[s] = i_ if (i_ is not None and i_ not in TC.EXCL_IND) else ""
    byind = {}
    for s, i_ in ind.items():
        if i_:
            byind.setdefault(i_, []).append(roe[s])
    MED = {i_: TC.ind_median(v) for i_, v in byind.items()}

    def td_level(s, kk):
        a = TD.get(s)
        if a is None or kk < 0 or not alive_at(s, int(ME[kk])):
            return np.nan
        j = TC.lastok(a, int(ME[kk]) - 1, TC.TD_LAG)
        return float(a[j]) if j >= 0 else np.nan
    rows = []
    for s, r in sorted(W.items()):
        if not (r["G"][p] and np.isfinite(r["C"][p])):
            continue
        vp = VP[s]; vc = r["C"][vp]; vb = r["BAD"][vp]
        hi = TC.hi1y(vp, vc, vb, p); rr, full36 = TC.r36(vp, vc, vb, p, p36)
        if not TC.in_pop(rr, hi):
            continue
        take = TC.dedupe_take(mi, last_taken.get(s, -999))
        if take:
            last_taken[s] = mi
        win = np.array([r["PER"][pp] if alive_at(s, pp) else np.nan for pp in pk.values()], float)
        pos = TC.pe_pos(win)
        q, qd = qinfo.get(s) or sel_q(AV, s, t)
        f = FIN.get(s, {})
        e4 = TC.eps4(f.get("eps_ytd"), q)
        ro = roe.get(s, np.nan); i_ = ind.get(s, "")
        med, nmem = MED.get(i_, (np.nan, 0)) if i_ else (np.nan, 0)
        td12 = td_level(s, k) - td_level(s, k - 12) if k >= 12 else np.nan
        sg = TC.signals(pos, e4, ro, med, td12)
        e = p + 1
        ef = TC.entry_flags(r["C"], r["BAD"], r["TRD"], r["UPL"], e, n0)
        rows.append({"形成月": mkey, "t": str(t.date()), "sid": s, "名稱": names.get(s, ""), "入判": take, "R36_36月完整無壞根": full36,
                     "產業": i_, "產業ROE有值數": nmem, "產業ROE中位": med, "ROE": ro, "本益比": r["PER"][p], "本益比5年月底位置": pos,
                     "近4季EPS": e4, "財報季": LP.qlabel(q) if q >= 0 else "", "財報可用日": str(qd.date()) if qd is not None else "",
                     "集保12月變化": td12, **sg, "e": str(cal[e].date()) if e < n0 else "", **ef,
                     "可用": bool(e < n0 and ef["e無成交"] is False and ef["壞根(t,e]"] is False)})
    return rows


# ═════════════ 紀錄檔（凍結）═════════════
def read_events(path):
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLS)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "True" if v else "False"
    if isinstance(v, (float, np.floating)):
        return "" if not np.isfinite(v) else repr(float(v))
    return str(v)


def write_events(path, old, new):
    """V4：舊列非空格逐字不變才寫回（暫存檔 ＋ os.replace）。"""
    if len(old):
        o0 = read_events(path)
        a = o0.reindex(columns=COLS).fillna(""); b = new.iloc[:len(o0)].reindex(columns=COLS).fillna("")
        changed = (a != "") & (a != b)
        if changed.to_numpy().any():
            raise SystemExit(f"⛔ 凍結違反：已寫格被改 {int(changed.to_numpy().sum())} 格（不寫回）")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new.reindex(columns=COLS).to_csv(path + ".tmp", index=False, encoding="utf-8")
    os.replace(path + ".tmp", path)


def history_taken(EVf, start):
    """去重歷史：起始月之前 ＝ 已凍結頻率表的入判列；起始月起 ＝ 本檔紀錄。"""
    last = {}
    F = pd.read_csv(FREQ_EV, dtype={"sid": str}, usecols=["sid", "月", "入判"])
    F = F[(F["入判"].astype(str) == "True") & (F["月"] < start)]
    for s, m in zip(F["sid"], F["月"]):
        last[s] = max(last.get(s, -999), ymi(m))
    if len(EVf):
        for s, m, f in zip(EVf["sid"], EVf["形成月"], EVf["入判"]):
            if f == "True":
                last[s] = max(last.get(s, -999), ymi(m))
    return last


# ═════════════ 到期填報酬 ═════════════
def fill_due(EVf, cal, DATA, procs, asof):
    """回 (EVf, 本晚填了幾格)。"""
    n0 = len(cal); filled = []
    need = {}
    for idx, r in EVf.iterrows():
        if r["可用"] != "True" or r["e"] == "":
            continue
        e = int(cal.get_loc(pd.Timestamp(r["e"])))
        for mth, sfx in ((6, "6"), (12, "12")):
            if r[f"R{sfx}"] == "" and r[f"出場{sfx}"] == "":
                x, xd, done = TC.window_end(cal, e, mth)
                if done:
                    need.setdefault(r["sid"], []).append((idx, e, x, xd, sfx))
    if not need:
        return EVf, []
    W, _ = build_world(DATA, cal, sorted(need), procs)
    for s, L in need.items():
        r = W.get(s)
        for idx, e, x, xd, sfx in L:
            EVf.at[idx, f"到期日{sfx}"] = str(xd.date()); EVf.at[idx, f"填於{sfx}"] = str(asof.date())
            if r is None:
                EVf.at[idx, f"出場{sfx}"] = "無價格"; filled.append((idx, sfx)); continue
            vp = np.flatnonzero(np.isfinite(r["C"])); w = TC.ret_window(vp, r["C"][vp], r["BAD"][vp], float(r["O"][e]), e, x, n0 - 1)
            if w is None:
                EVf.at[idx, f"出場{sfx}"] = "不可算"
            else:
                EVf.at[idx, f"R{sfx}"] = fmt(w["R"]); EVf.at[idx, f"出場{sfx}"] = w["出場"]
                if sfx == "12":
                    EVf.at[idx, "腰斬12"] = fmt(w["腰斬"]); EVf.at[idx, "最大回落12"] = fmt(w["最大回落"])
            filled.append((idx, sfx))
    # 同月對照（入判 ∧ 可用 全部填好才算；填一次）
    for m, g in EVf.groupby("形成月"):
        gg = g[(g["入判"] == "True") & (g["可用"] == "True")]
        for sfx in ("6", "12"):
            if not len(gg) or (gg[f"出場{sfx}"] == "").any() or (gg[f"同月對照R{sfx}平均"] != "").any():
                continue
            ns = gg[(gg["S"] == "False") & (gg[f"R{sfx}"] != "")]
            base = float(pd.to_numeric(ns[f"R{sfx}"]).mean()) if len(ns) else np.nan
            for idx in gg.index:
                EVf.at[idx, f"同月對照R{sfx}平均"] = fmt(base) if np.isfinite(base) else "無對照"
                if gg.at[idx, "S"] == "True" and gg.at[idx, f"R{sfx}"] != "" and np.isfinite(base):
                    EVf.at[idx, f"d{sfx}"] = fmt(float(gg.at[idx, f"R{sfx}"]) - base)
    return EVf, filled


# ═════════════ 主流程 ═════════════
def load_state(fwd):
    p = os.path.join(fwd, "state.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"起始月": START, "months": {}, "fills": {}}


def md_lines(st, asof):
    a = str(asof.date()); L = []
    for m, v in sorted(st["months"].items()):
        if v.get("資料日") == a:
            L.append(f"- 頂部樣子前瞻（內部・不推 LINE）：形成月 {m}（月底 {v['t']}）母體入判 {v['入判']} 檔、S 成立 {v['S成立']} 檔"
                     + (f"（{v['S成立代號']}）" if v.get("S成立代號") else "") + "；12 個月後記表現，累積兩段各 n_eff ≥ 30 再判")
    f = st.get("fills", {}).get(a)
    if f:
        L.append(f"- 頂部樣子前瞻（內部・不推 LINE）：到期填報酬 {f}")
    return L


def run(a):
    t0 = time.time()
    sha = BM.git("rev-parse", a.sha or "origin/main").strip()
    H = BM.ensure_snapshot(sha); D.DATA = H
    cal = D.load_calendar()
    asof = pd.Timestamp(a.asof) if a.asof else cal[-1]
    if asof not in cal:
        raise SystemExit(f"⛔ 資料日 {asof.date()} 不在 {sha[:10]} 的交易日曆（尾 {cal[-1].date()}）")
    cal = cal[cal <= asof]
    fwd = a.fwd; evp = os.path.join(fwd, "events.csv")
    st = load_state(fwd); EVf = read_events(evp); n_old = len(EVf)
    todo = pending_months(cal, asof, set(st["months"]), a.start)
    log(f"[版本] sha {sha[:10]}｜資料日 {asof.date()}｜紀錄 {n_old} 列｜待判形成月 {[x[0] for x in todo]}")
    if todo:

        W, names = build_world(H, cal, None, a.procs)
        log(f"[世界] {len(W)} 檔｜{time.time() - t0:.0f}s")
        ME, _ = PF.month_ends(cal); ME = np.asarray(ME, np.int64)
        _, _, cat, _, _, _ = PRE.load_rev(H); PIT = PRE.PIT(H, cat)
        last = history_taken(EVf, a.start)
        for key, p, pj in todo:
            jd = cal[pj]
            ac = a.fund_at or BM.asof_commit(sha, jd)[0]
            FD = BM.ensure_fund(ac, sha); TDD = ensure_tdcc(ac)
            AV, FIN = load_fund(FD, set(W)); TD = load_tdcc(TDD, cal, set(W))
            k = int(np.flatnonzero(ME == p)[0])
            # V2′ 母體當晚口徑：research11.load_bars「有效 K 棒 ≥ 260 根」以判定夜為止計（世界用資料日日曆建，補判舊月時不讓之後才滿 260 根的股進來）
            Wm = {s: r for s, r in W.items() if int(np.isfinite(r["C"][:pj + 1]).sum()) >= MIN_BARS}
            rows = judge_month(Wm, cal, ME, k, AV, FIN, TD, PIT, names, last)
            for r in rows:
                r.update({"判定夜": str(jd.date()), "資料日": str(asof.date()), "sha": sha[:12], "財報集保版本": ac[:12]})
            add = pd.DataFrame([{c: fmt(r.get(c)) for c in COLS} for r in rows], columns=COLS)
            EVf = pd.concat([EVf, add], ignore_index=True)
            sS = [f"{r['sid']} {r['名稱']}" for r in rows if r["入判"] and r["S"] is True]
            st["months"][key] = {"t": str(cal[p].date()), "判定夜": str(jd.date()), "資料日": str(asof.date()), "sha": sha[:12], "財報集保版本": ac[:12],
                                 "母體列": len(rows), "入判": int(sum(r["入判"] for r in rows)), "S成立": len(sS), "S成立代號": "、".join(sS)}
            log(f"[判定] 形成月 {key}（月底 {cal[p].date()}、判定夜 {jd.date()}、版本 {ac[:10]}）：母體 {len(rows)}、入判 {st['months'][key]['入判']}、S 成立 {len(sS)}")
    EVf, filled = fill_due(EVf, cal, H, a.procs, asof)
    if filled:
        st.setdefault("fills", {})[str(asof.date())] = f"{len(filled)} 格（R6／R12）"
    log(f"[到期] 本晚填 {len(filled)} 格")
    if not a.nowrite and (todo or filled):
        write_events(evp, EVf.iloc[:n_old] if n_old else EVf.iloc[:0], EVf)
        st["last"] = {"資料日": str(asof.date()), "sha": sha[:12], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
        os.makedirs(fwd, exist_ok=True)
        json.dump(st, open(os.path.join(fwd, "state.json.tmp"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(os.path.join(fwd, "state.json.tmp"), os.path.join(fwd, "state.json"))
        with open(os.path.join(fwd, "runlog.md"), "a", encoding="utf-8") as fo:
            fo.write(f"- {st['last']['時間']} 台北｜資料日 {asof.date()}｜sha {sha[:10]}｜新判 {[x[0] for x in todo]}｜到期填 {len(filled)} 格\n")
    if a.md:
        L = md_lines(st, asof)
        BM.put_daily(a.md, [[SEC + "（內部・不推 LINE）", "", *L]] if L else [], prefix=SEC)
        log(f"[名單] 第十三節：{'寫 ' + str(len(L)) + ' 行' if L else '無（已移除舊節）'}")
    print(f"頂部樣子前瞻：資料日 {asof.date()}｜新判 {[x[0] for x in todo]}｜到期填 {len(filled)} 格｜紀錄 {len(EVf)} 列｜{time.time() - t0:.0f}s")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha"); ap.add_argument("--asof"); ap.add_argument("--md"); ap.add_argument("--fwd", default=FWD)
    ap.add_argument("--nowrite", action="store_true"); ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--start", default=START); ap.add_argument("--fund-at", dest="fund_at")
    a = ap.parse_args()
    if a.fund_at:
        a.fund_at = BM.git("rev-parse", a.fund_at).strip()
    sys.exit(run(a))


if __name__ == "__main__":
    main()

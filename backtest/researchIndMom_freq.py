# -*- coding: utf-8 -*-
"""產業價格動能 seq1【頻率表・乾跑】（台股策略線 登錄 sha 1d295bb0edd70326，2026-10-20 23:33；裁定 seq407 第一題、seq408 發號 N_前段 ＋1
（市值加權＝原文為判定格，等權並報）；Moskowitz & Grinblatt 1999：過去 6 個月最強 3 產業、抱 6 個月）——回測線計算子代理。
⛔ 只數入選、事件個數、剔除計數、n_eff、重疊比例；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有期結果（月報酬相關留正式跑）。
   用到的價格只有 ≤ 形成月底 t 的還原收盤（6／1 個月形成期報酬，只用來排名、⛔ 不存）與 t 的市值；進場日 e 只用「有沒有成交、開盤是否有效、
   是否開盤鎖漲停」旗標（快取 trd／o／upl）。
⛔ 不 commit、不改既有程式與結果夾；researchAscTri_freq／researchPTH_freq／researchIndRev_prereg／research11／patterns ⛔ 只 import。
本檔另提供共用面板 build_panel（財報品質、現增可轉債兩支頻率表 import 重用）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndMom_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndMom_freq_check
輸出 backtest/resultsIndMom/freq/：freq.json、freq.csv、monthly.csv、industry_months.csv.gz、industry_counts.csv、equiv.csv、run.log

═══ 讀法（I 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 I1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（PTH 頻率表同）：主 ＝ rerun17 快照 H2D（2015-01-05～2026-09-24）；
    早年 ＝ ~/earlydata/eotc_f65bb03e11（2004-02-11～2014-12-31，上市＋上櫃）；股票 ＝ UG.gate3(GATE_V2) ∩ 四碼普通股、含已下市；
    research11.load_bars ＜ 260 根不進。壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl
    ∪ 早年 reduce_v2（researchAddOn.early_extra_bad，seq341 §六／seq335 新件早年用 reduce_v2）。
 I2 月底 ＝ researchPTH_freq.month_ends 原樣（每個完整曆月最後交易日；資料尾不完整月不算）。排序日 t ＝ 月底。
    排序母體（股）＝ patterns.Frame.gate[t]（含 t 的 20 交易日都有成交 ∧ t−20～t−1 日均量 ≥ 500 張 ＝ 登錄「500 張閘在排序日判」）∧ UG.pit_valid[t]
      ∧ t 有有效 K 棒 ∧ 形成期報酬可算 ∧ 市值權重可算 ∧ 產業別可判。
 I3 形成期報酬（L ＝ 6，描述版 L ＝ 1）：r ＝ c[t] ÷ c[a] − 1，a ＝ 第 j−L 個月底當天或之前最後一根有效 K 棒（還原收盤）；
    ★ a 不存在 ⇒ 剔除「未滿 L 月」；(a, t] 之間任一根壞 K 棒 ⇒ 剔除「窗內壞根」（PTH 頻率表 P8 同式）。
 I4 產業別 ＝ researchIndRev_prereg.PIT（industry_pit 主表；沒有該檔 ⇒ 月營收彙總表當時類別 fallback，PREREG產業營收加速 P1 原樣）在 t 的類別；
    資料 ＝ tw-stock-data 最新 origin/main（git archive 到 ~/b2fwork/main_<sha12>，唯讀）。
    ★ 排除「其他」「綜合」「存託憑證」「ETF」與無類別（不是單一產業）；〔另一讀法：「其他」也當一個產業〕。⭐ 金融保險【納入】（原文含金融業）。
    ★ 上市、上櫃同名一類（PIT 原樣）。
 I5 產業報酬：市值加權（判定格）＝ Σ w·r ÷ Σ w，★ w ＝ 形成期起點 a 那天的市值（原始收盤 × 股數，該日以前最後一筆；主 H2D stocks，
    早年 eotc daily_all.pkl，PREREG產業營收加速 P0 同源）≈ 形成期內買進持有的市值加權產業組合；等權（並報）＝ 成員 r 的平均。
    ★ w 不可算（≤ 0 或缺）⇒ 該股剔除「市值缺」（兩版同一批成員，可比）。
    產業成員 ≥ 5 檔才排名（登錄 §一）；名次 ＝ 報酬由高到低，★ 同值依產業名稱。入選 ＝ 前 3；最弱 3 ＝ 後 3（只描述）。
 I6 進場 ＝ 形成月 m 的下一個曆月第一個交易日 e 開盤（登錄 §一 不跳月）；e 超出日曆 ⇒ 不計「超出資料尾」。
    股票層進場剔除（每筆只記第一個原因；PTH 頻率表 P5 同序）：壞根(t,e] → e無成交 → e開盤鎖漲停；保留 ＝ 該產業實際買得到的股。
    ★ 入選產業不因股票層剔除而改；剔除不遞補。
 I7 事件（登錄 §二）＝ 每月入選的 3 個產業各算一筆（同產業連月入選各算）；★ 事件依【進場日 e】歸段：探索 [2017-03-02, 2021-12-30]｜
    確認 [2022-01-03, 資料尾]｜早年 [2005 第一個交易日, 2014-12-31]（描述）。
    ★「整筆落在資料內」＝ 第 m＋6 個月底在日曆內（6 個月持有走完；X 要到那時才算得出）⇒ 另報「6 個月走完」的事件數與 n_eff。
    n_eff ＝ min(事件數, 有事件的進場月數)；n_eff ＜ 30 ⇒ 標「依構造不可判定、不計 N」。另報（參考）不重疊 6 個月段數 ＝ 進場月數 ÷ 6。
 I8 重疊（登錄 §二 ⭐必答之「持股重疊比例」；月報酬相關留正式跑）：形成月底 t 相同的
      PTH 前 30% ＝ backtest/resultsPTH/freq/events_<世界>.csv.gz「入選」（researchPTH_freq 原輸出，⛔ 只讀）；
      個股 12−1 動能前 30% ★ ＝ 同一檔 mom12_1 有值者（PTH 排序母體內）由高到低 ⌈0.3n⌉、同值併入（PTH 頻率表 P4 同法）。
    報：入選產業成員（I2 母體、三產業合計）中屬於對方前 30% 的比例（檔數比、★ 市值加權比 ＝ t 市值），對照基準 ＝ 對方前 30% ÷ 對方母體；
        對方前 30% 中落在入選產業的比例。★ 只算 PTH 檔該月有資料的形成月。
 I9 seq377 乾跑等價檢查：(a) 市值加權 vs 等權入選產業重疊（每月 |A∩B|÷3、股票層 Jaccard）；(b) 6 個月 vs 1 個月形成；
    (c) 相鄰兩月入選產業重複率（＝ 登錄「入選產業的重複率」）。兩臂入選幾乎相同 ⇒ 近乎同一件、先報。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import math
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import researchPTH_freq as PF                 # noqa: E402  month_ends／entry_pos（⛔ 只 import）
from backtest import researchIndRev_prereg as PRE           # noqa: E402  PIT、load_rev（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate（500 張閘）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "1d295bb0edd70326"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsIndMom/freq"
WORK = os.path.expanduser("~/b2fwork")
PARTS_GIT = ["data/meta/industry_hist", "data/meta/industry.csv", "data/meta/stocks.csv", "data/mops/revenue_hist", "data/early/revenue",
             "data/meta/fs_xbrl", "data/meta/filing_dates.csv", "data/meta/seo_cb_events", "data/meta/delisted.csv"]
EOTC_DAILY = os.path.expanduser("~/earlydata/eotc_f65bb03e11/daily_all.pkl")
PTH_EV = "backtest/resultsPTH/freq/events_{}.csv.gz"
EXCL_IND = {"其他", "綜合", "存託憑證", "ETF", ""}
MINMEM = 5
TOPK = 3
NEFF_MIN = 30
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-01-01", "2014-12-31")}}
ARMS = {"市值加權6月(判定)": ("vw", 6), "等權6月(並報)": ("ew", 6), "市值加權1月(描述)": ("vw", 1)}
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check(sha):
    """信箱根目錄與 _封存-* 夾以 sha 找登錄全文，去 pw1 行重算 sha256 前 16 碼。"""
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md"))
          if f"sha{sha}" in os.path.basename(f)]
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到登錄全文 sha{sha}")
    for f in fs:
        b = open(f, "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != sha:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}（{f}）")
    return os.path.basename(fs[0])


def ensure_main():
    """最新 origin/main（呼叫前已 git fetch）⇒ git archive 需要的路徑到 ~/b2fwork/main_<sha12>（唯讀用）。"""
    sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.join(WORK, f"main_{sha[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS_GIT, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(sha)
    return sha, os.path.join(root, "data")


# ═════════════ 共用面板（每世界一次，快取 ~/b2fwork/panel_<世界>.pkl）═════════════
def _panel_job(a):
    wn, sid = a
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    c = np.asarray(B["c"], float)
    if not np.isfinite(c).all():
        raise SystemExit(f"⛔ {wn} {sid} 有效 K 棒收盤有缺值")
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    Cc = np.full(n0, np.nan); Cc[idx] = c
    Bc = np.zeros(n0, bool); Bc[idx] = bad
    G = np.asarray(P.Frame(df, set()).gate, bool) & np.asarray(W["PV"][i], bool)
    MC = None
    if wn == "主":
        raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close", "shares"])
        raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
        v = pd.to_numeric(raw["close"], errors="coerce") * pd.to_numeric(raw["shares"], errors="coerce")
        v = v.where(v > 0)
        MC = v.reindex(cal).ffill().to_numpy(float) if v.notna().any() else np.full(n0, np.nan)
    return sid, (Cc, Bc, G, MC)


def build_panel(wn, procs, logf=None):
    logf = logf or log
    cp = os.path.join(WORK, f"panel_{wn}.pkl")
    if os.path.exists(cp):
        Z = pickle.load(open(cp, "rb"))
        logf(f"[面板 {wn}] 讀快取 {cp}（{len(Z['sids'])} 檔）")
        return Z
    os.makedirs(WORK, exist_ok=True)
    t0 = time.time()
    W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
    _G[wn] = W
    res = {}
    with Pool(procs) as pool:
        for k_, (sid, r) in enumerate(pool.imap_unordered(_panel_job, [(wn, s) for s in W["sids"]], chunksize=8)):
            res[sid] = r
            if (k_ + 1) % 500 == 0:
                logf(f"  面板 {wn} … {k_ + 1}／{len(W['sids'])}｜{time.time() - t0:.0f}s")
    ok = [s for s in W["sids"] if res.get(s) is not None]
    C = np.stack([res[s][0] for s in ok]); BD = np.stack([res[s][1] for s in ok]); G = np.stack([res[s][2] for s in ok])
    if wn == "主":
        MC = np.stack([res[s][3] for s in ok])
    else:
        da = pd.read_pickle(EOTC_DAILY)
        da = da[da["stock_id"].isin(set(ok))][["date", "stock_id", "close", "shares"]].copy()
        da["v"] = pd.to_numeric(da["close"], errors="coerce") * pd.to_numeric(da["shares"], errors="coerce")
        da = da[da["v"] > 0].drop_duplicates(["stock_id", "date"], keep="last")
        da["date"] = pd.to_datetime(da["date"])
        pv = da.pivot(index="date", columns="stock_id", values="v").reindex(cal).ffill()
        MC = np.stack([pv[s].to_numpy(float) if s in pv.columns else np.full(n0, np.nan) for s in ok])
        del da, pv
    ii = [W["ix"][s] for s in ok]
    Z = {"wn": wn, "data": W["data"], "cal": cal, "n0": n0, "sids": ok, "mk": W["mk"], "C": C, "BAD": BD, "G": G, "MC": MC,
         "TRD": W["TRD"][ii], "O": W["O"][ii], "UPL": W["UPL"][ii], "n_short": len(W["sids"]) - len(ok),
         "gate_info": W["gate"], "bad_info": W["bad_info"]}
    pickle.dump(Z, open(cp, "wb"), protocol=5)
    logf(f"[面板 {wn}] {len(ok)} 檔（load_bars 不足 260 根 {Z['n_short']}）｜{time.time() - t0:.0f}s ⇒ {cp}")
    return Z


def panel_aux(Z):
    """衍生：每檔有效 K 棒位置、壞根累計（日曆位置）。"""
    if "VP" not in Z:
        Z["VP"] = [np.flatnonzero(np.isfinite(r)) for r in Z["C"]]
        Z["CB"] = np.cumsum(Z["BAD"], axis=1, dtype=np.int32)
    return Z


def lastvalid(Z, i, p):
    """第 i 檔在日曆位置 p 當天或之前最後一根有效 K 棒的日曆位置；沒有 ⇒ −1。"""
    vp = Z["VP"][i]
    k = int(np.searchsorted(vp, p, "right")) - 1
    return int(vp[k]) if k >= 0 else -1


def nbad(Z, i, a, b):
    """日曆位置 (a, b] 內壞 K 棒數。"""
    return int(Z["CB"][i, b] - Z["CB"][i, a]) if b > a else 0


def entry_flag(Z, i, t, e):
    """進場剔除（PTH 頻率表 P5 同序）：回 '保留'／'壞根(t,e]'／'e無成交'／'e開盤鎖漲停'。"""
    ke = lastvalid(Z, i, e)
    if ke > t and nbad(Z, i, t, ke) > 0:
        return "壞根(t,e]"
    if not (np.isfinite(Z["C"][i, e]) and Z["TRD"][i, e] and np.isfinite(Z["O"][i, e]) and Z["O"][i, e] > 0):
        return "e無成交"
    if Z["UPL"][i, e]:
        return "e開盤鎖漲停"
    return "保留"


def window_ret(Z, i, a_pos, t):
    """I3：回 (r, 狀態)。"""
    pa = lastvalid(Z, i, a_pos)
    if pa < 0:
        return np.nan, "未滿L月", -1
    if nbad(Z, i, pa, t) > 0:
        return np.nan, "窗內壞根", pa
    return Z["C"][i, t] / Z["C"][i, pa] - 1.0, "ok", pa


def qd(a):
    a = np.asarray([x for x in a if x is not None and np.isfinite(x)], float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "中位": round(float(np.median(a)), 4), "p25": round(float(np.percentile(a, 25)), 4),
            "p75": round(float(np.percentile(a, 75)), 4), "min": round(float(a.min()), 4), "max": round(float(a.max()), 4)}


def seg_bounds(cal, x, y):
    n0 = len(cal)
    p0 = int(cal.searchsorted(pd.Timestamp(x)))
    p1 = n0 - 1 if y is None else int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1
    return p0, p1


def load_pit(DATA):
    rev, rev_ly, cat, mk, nf, nr = PRE.load_rev(DATA)
    return PRE.PIT(DATA, cat)


# ═════════════ 每月排序 ═════════════
def month_table(Z, PIT, ME, j, L):
    """形成月 j、形成期 L ⇒ (成員 dict 產業→[(i, r, w)], 剔除 Counter, 母體 i 清單)。"""
    cal = Z["cal"]; t = int(ME[j]); a_pos = int(ME[j - L]); d = cal[t]
    mem = defaultdict(list); rej = Counter(); univ = []
    for i in np.flatnonzero(Z["G"][:, t] & np.isfinite(Z["C"][:, t])):
        r, st, pa = window_ret(Z, i, a_pos, t)
        if st != "ok":
            rej[st] += 1; continue
        w = Z["MC"][i, a_pos]
        if not (np.isfinite(w) and w > 0):
            rej["市值缺"] += 1; continue
        ind, src = PIT.at(Z["sids"][i], d)
        if ind is None or ind in EXCL_IND:
            rej[f"產業排除:{ind or '無類別'}"] += 1; continue
        mem[ind].append((int(i), float(r), float(w)))
        univ.append(int(i))
    return mem, rej, univ


def rank_inds(mem):
    """回 {vw: [(產業, 值)...由高到低], ew: [...]}（只含成員 ≥ 5）。"""
    out = {}
    rk = {k: v for k, v in mem.items() if len(v) >= MINMEM}
    vw = {k: sum(r * w for _, r, w in v) / sum(w for _, _, w in v) for k, v in rk.items()}
    ew = {k: float(np.mean([r for _, r, _ in v])) for k, v in rk.items()}
    out["vw"] = sorted(vw.items(), key=lambda z: (-z[1], z[0]))
    out["ew"] = sorted(ew.items(), key=lambda z: (-z[1], z[0]))
    return out


def load_pth_sets(wn):
    """I8：{形成月底: (PTH 前30% 集合, PTH 母體集合, 12−1 前30% 集合, 12−1 母體集合)}。"""
    ev = pd.read_csv(PTH_EV.format(wn), dtype={"sid": str}, usecols=["sid", "形成月底", "入選", "mom12_1"])
    out = {}
    for t, g in ev.groupby("形成月底"):
        pth_top = set(g.loc[g["入選"].astype(bool), "sid"]); pth_all = set(g["sid"])
        m = g[np.isfinite(g["mom12_1"].to_numpy(float))]
        n = len(m)
        if n:
            k = int(math.ceil(0.3 * n)); cut = np.sort(m["mom12_1"].to_numpy(float))[::-1][k - 1]
            mom_top = set(m.loc[m["mom12_1"].to_numpy(float) >= cut, "sid"])
        else:
            mom_top = set()
        out[t] = (pth_top, pth_all, mom_top, set(m["sid"]))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DATA = ensure_main()
    log(f"[資料] origin/main {sha[:10]} ⇒ {DATA}")
    PIT = load_pit(DATA)
    J = {"性質": "產業價格動能 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有期結果；形成期報酬只用於排名、不存）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq407 第一題、seq408 發號 N_前段 ＋1（市值加權判定、等權並報）；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N",
         "資料": {"origin/main": sha, "產業別": "industry_pit（PIT）＋月營收彙總表 fallback"}, "世界": {}}
    FREQ = []; MON = []; EQ = []; INDROWS = []; ICNT = []
    for wn in ("主", "早年"):
        Z = panel_aux(build_panel(wn, a.procs))
        cal = Z["cal"]; n0 = Z["n0"]
        ME, MK = PF.month_ends(cal); nm = len(ME)
        EP = PF.entry_pos(cal, MK, 1)
        PTHS = load_pth_sets(wn)
        log(f"[{wn}] 月底 {nm} 個：{cal[ME[0]].date()}～{cal[ME[-1]].date()}｜PTH 對照月 {len(PTHS)}")
        # 每月
        M = {}
        for j in range(6, nm):
            t = int(ME[j]); ts = str(cal[t].date())
            row = {"j": j, "t": ts}
            for L in (6, 1):
                mem, rej, univ = month_table(Z, PIT, ME, j, L)
                rk = rank_inds(mem)
                row[L] = {"mem": mem, "rej": rej, "univ": univ, "rk": rk}
            M[j] = row
        log(f"[{wn}] 每月排序完｜{time.time() - t0:.0f}s")
        Wj = {"資料": Z["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "股票檔數": len(Z["sids"]),
              "load_bars不足260根": Z["n_short"], "閘": Z["gate_info"], "壞根": Z["bad_info"], "月底": [str(cal[ME[0]].date()), str(cal[ME[-1]].date())],
              "第一個可排序月(6月)": str(cal[ME[6]].date()), "段": {}}

        def picks(j, arm, bottom=False):
            kind, L = ARMS[arm] if arm in ARMS else arm
            lst = M[j][L]["rk"][kind]
            return [k for k, _ in (lst[-TOPK:][::-1] if bottom else lst[:TOPK])]

        def stocks_of(j, L, inds):
            mem = M[j][L]["mem"]
            return [(i, w) for k in inds for (i, r, w) in mem.get(k, [])]

        # 每月表
        prev = None
        for j in range(6, nm):
            t = int(ME[j]); e = int(EP[j]); ts = M[j]["t"]
            m6 = M[j][6]; nrank = len(m6["rk"]["vw"])
            top = picks(j, "市值加權6月(判定)"); topE = picks(j, "等權6月(並報)"); top1 = picks(j, "市值加權1月(描述)")
            bot = picks(j, ("vw", 6), bottom=True)
            sv = stocks_of(j, 6, top)
            fl = Counter(entry_flag(Z, i, t, e) for i, _ in sv) if e >= 0 else Counter({"超出資料尾": len(sv)})
            row = {"世界": wn, "形成月底": ts, "進場日": str(cal[e].date()) if e >= 0 else "", "6月走完": bool(j + 6 < nm),
                   "排序母體檔數": len(m6["univ"]), "產業數(含<5)": len(m6["mem"]), "可排名產業數(≥5)": nrank,
                   "成員<5產業數": sum(1 for v in m6["mem"].values() if len(v) < MINMEM),
                   **{f"剔除_{k}": v for k, v in m6["rej"].items() if not k.startswith("產業來源")},
                   "市值加權前3": "｜".join(top), "前3成員數": "｜".join(str(len(m6["mem"][k])) for k in top), "前3股票數": len(sv),
                   **{f"進場_{k}": v for k, v in fl.items()},
                   "等權前3": "｜".join(topE), "1月前3": "｜".join(top1), "最弱3(描述)": "｜".join(bot),
                   "市值vs等權重疊產業": len(set(top) & set(topE)), "6月vs1月重疊產業": len(set(top) & set(top1)),
                   "與上月重複產業": len(set(top) & set(prev)) if prev is not None else None}
            # 等權 vs 市值 股票層
            sE = {i for i, _ in stocks_of(j, 6, topE)}; sV = {i for i, _ in sv}
            row["股票層Jaccard_市值vs等權"] = round(len(sV & sE) / len(sV | sE), 4) if (sV | sE) else None
            # I8 重疊
            if ts in PTHS:
                pth_top, pth_all, mom_top, mom_all = PTHS[ts]
                ids = [Z["sids"][i] for i, _ in sv]; mc_t = np.array([Z["MC"][i, t] for i, _ in sv], float)
                mc_t = np.where(np.isfinite(mc_t), mc_t, 0.0)
                for nmx, top_, all_ in (("PTH前30%", pth_top, pth_all), ("12-1前30%", mom_top, mom_all)):
                    inn = np.array([s in top_ for s in ids]); inall = np.array([s in all_ for s in ids])
                    row[f"重疊_{nmx}_檔數"] = int(inn.sum())
                    row[f"重疊_{nmx}_對方母體內檔數"] = int(inall.sum())
                    row[f"重疊_{nmx}_比例(÷入選產業股)"] = round(float(inn.mean()), 4) if len(ids) else None
                    row[f"重疊_{nmx}_市值加權比例"] = round(float(mc_t[inn].sum() / mc_t.sum()), 4) if mc_t.sum() > 0 else None
                    row[f"重疊_{nmx}_基準(對方前30%÷對方母體)"] = round(len(top_) / len(all_), 4) if all_ else None
                    univ_ids = {Z["sids"][i] for i in m6["univ"]}
                    row[f"重疊_{nmx}_對方前30%落在入選產業比例"] = round(len(top_ & set(ids)) / len(top_ & univ_ids), 4) if (top_ & univ_ids) else None
            MON.append(row)
            for k, (nmk, v) in enumerate(m6["rk"]["vw"]):
                INDROWS.append({"世界": wn, "形成月底": ts, "產業": nmk, "成員數": len(m6["mem"][nmk]), "市值加權名次": k + 1,
                                "等權名次": [x for x, _ in m6["rk"]["ew"]].index(nmk) + 1,
                                "1月名次": ([x for x, _ in M[j][1]["rk"]["vw"]].index(nmk) + 1) if nmk in dict(M[j][1]["rk"]["vw"]) else None,
                                "入選(市值6月)": nmk in top, "入選(等權6月)": nmk in topE, "入選(1月)": nmk in top1, "最弱3": nmk in bot})
            prev = top
        # 段
        for sg, (x, y) in SEGS[wn].items():
            p0, p1 = seg_bounds(cal, x, y)
            je = [j for j in range(6, nm) if EP[j] >= 0 and p0 <= EP[j] <= p1]
            segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}", "形成月數(進場日在段內)": len(je)}
            segj["每月可排名產業數"] = qd([len(M[j][6]["rk"]["vw"]) for j in je])
            segj["每月排序母體檔數"] = qd([len(M[j][6]["univ"]) for j in je])
            segj["可排名產業的成員數(股-月合併)"] = qd([len(v) for j in je for v in M[j][6]["mem"].values() if len(v) >= MINMEM])
            rejall = Counter()
            for j in je:
                rejall.update(M[j][6]["rej"])
            segj["形成月剔除合計(6月)"] = {k: v for k, v in rejall.items() if not k.startswith("產業來源")}
            src = Counter()
            for j in je:
                for k, v in M[j][6]["mem"].items():
                    for (i, _, _) in v:
                        src[PIT.at(Z["sids"][i], cal[int(ME[j])])[1]] += 1
            segj["產業別來源(股-月)"] = dict(src)
            for arm in list(ARMS) + ["最弱3(描述)"]:
                if arm == "最弱3(描述)":
                    pk = {j: picks(j, ("vw", 6), bottom=True) for j in je}; L = 6
                else:
                    pk = {j: picks(j, arm) for j in je}; L = ARMS[arm][1]
                nev = sum(len(v) for v in pk.values()); months = sum(1 for v in pk.values() if v)
                jdone = [j for j in je if j + 6 < nm]
                nev_d = sum(len(pk[j]) for j in jdone); months_d = sum(1 for j in jdone if pk[j])
                rep = [len(set(pk[j]) & set(pk[j - 1])) / TOPK for j in je if j - 1 in pk and pk[j - 1]]
                cnt = Counter(k for v in pk.values() for k in v)
                stk = [len(stocks_of(j, L, pk[j])) for j in je]
                fl = Counter()
                for j in je:
                    for i, _ in stocks_of(j, L, pk[j]):
                        fl[entry_flag(Z, i, int(ME[j]), int(EP[j]))] += 1
                ne = min(nev, months); ne_d = min(nev_d, months_d)
                jarm = {"事件數(產業-月)": nev, "有事件進場月": months, "n_eff": ne, "n_eff<30": bool(ne < NEFF_MIN),
                        "6月走完_事件數": nev_d, "6月走完_n_eff": ne_d, "6月走完_n_eff<30": bool(ne_d < NEFF_MIN),
                        "判斷": "依構造不可判定、不計 N" if ne_d < NEFF_MIN else "可判（n_eff ≥ 30）",
                        "不重疊6個月段數(參考)": round(months / 6, 1), "相鄰兩月重複率(平均)": round(float(np.mean(rep)), 4) if rep else None,
                        "相異入選產業數": len(cnt), "入選次數前10": dict(cnt.most_common(10)),
                        "每月入選產業股票數": qd(stk), "股票層進場": dict(fl),
                        "進場月範圍": [cal[EP[je[0]]].strftime("%Y-%m"), cal[EP[je[-1]]].strftime("%Y-%m")] if je else None}
                segj[arm] = jarm
                FREQ.append({"世界": wn, "段": sg, "臂": arm, "期間": segj["期間"], **{k: v for k, v in jarm.items() if not isinstance(v, (dict, list))},
                             "每月股票數中位": jarm["每月入選產業股票數"]["中位"] if jarm["每月入選產業股票數"] else None,
                             "每月股票數min": jarm["每月入選產業股票數"]["min"] if jarm["每月入選產業股票數"] else None,
                             "每月股票數max": jarm["每月入選產業股票數"]["max"] if jarm["每月入選產業股票數"] else None})
                for k, v in sorted(cnt.items(), key=lambda z: -z[1]):
                    ICNT.append({"世界": wn, "段": sg, "臂": arm, "產業": k, "入選月數": v})
            # 等價（seq377）
            rows_ = [r for r in MON if r["世界"] == wn and r["進場日"] and p0 <= int(cal.searchsorted(pd.Timestamp(r["進場日"]))) <= p1]
            eqj = {"市值vs等權_每月重疊產業÷3_平均": round(float(np.mean([r["市值vs等權重疊產業"] / 3 for r in rows_])), 4) if rows_ else None,
                   "市值vs等權_三產業全同月比例": round(float(np.mean([r["市值vs等權重疊產業"] == 3 for r in rows_])), 4) if rows_ else None,
                   "市值vs等權_股票層Jaccard中位": qd([r["股票層Jaccard_市值vs等權"] for r in rows_ if r["股票層Jaccard_市值vs等權"] is not None]),
                   "6月vs1月_每月重疊產業÷3_平均": round(float(np.mean([r["6月vs1月重疊產業"] / 3 for r in rows_])), 4) if rows_ else None}
            for nmx in ("PTH前30%", "12-1前30%"):
                rr = [r for r in rows_ if f"重疊_{nmx}_檔數" in r]
                if rr:
                    eqj[f"{nmx}_可比月數"] = len(rr)
                    eqj[f"{nmx}_入選產業股中屬對方前30%_合計比例"] = round(sum(r[f"重疊_{nmx}_檔數"] for r in rr) / max(1, sum(r["前3股票數"] for r in rr)), 4)
                    eqj[f"{nmx}_同上_只算對方母體內"] = round(sum(r[f"重疊_{nmx}_檔數"] for r in rr) / max(1, sum(r[f"重疊_{nmx}_對方母體內檔數"] for r in rr)), 4)
                    eqj[f"{nmx}_市值加權比例_月中位"] = qd([r[f"重疊_{nmx}_市值加權比例"] for r in rr if r[f"重疊_{nmx}_市值加權比例"] is not None])
                    eqj[f"{nmx}_基準_月中位"] = qd([r[f"重疊_{nmx}_基準(對方前30%÷對方母體)"] for r in rr])
                    eqj[f"{nmx}_對方前30%落在入選產業_月中位"] = qd([r[f"重疊_{nmx}_對方前30%落在入選產業比例"] for r in rr
                                                              if r[f"重疊_{nmx}_對方前30%落在入選產業比例"] is not None])
            segj["seq377等價與重疊"] = eqj
            EQ.append({"世界": wn, "段": sg, **{k: (v["中位"] if isinstance(v, dict) and "中位" in v else v) for k, v in eqj.items()}})
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] " + "｜".join(f"{arm} 事件 {segj[arm]['事件數(產業-月)']} n_eff {segj[arm]['n_eff']}（走完 {segj[arm]['6月走完_n_eff']}）"
                                           for arm in ARMS) + f"｜市值vs等權 {eqj['市值vs等權_每月重疊產業÷3_平均']}")
        J["世界"][wn] = Wj
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MON).to_csv(os.path.join(OUT, "monthly.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQ).to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ICNT).to_csv(os.path.join(OUT, "industry_counts.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "industry_months.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame(INDROWS).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""產業價格動能 seq1【事件層正式跑】（台股策略線 登錄 sha 1d295bb0edd70326，2026-10-20 23:33；裁定 seq407 第一題、seq408 發號 N_前段 ＋1、
seq412 §四 核准開正式跑；Moskowitz & Grinblatt 1999：過去 6 個月最強 3 產業、抱 6 個月）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsIndMom/freq 不動）；researchIndMom_freq（讀法 I1～I9 寫死、沿用；build_panel、month_table、rank_inds、
   entry_flag、window_ret、load_pit、load_pth_sets）、researchPTH_freq（month_ends、entry_pos）、research11（cl_stats、limit_price）、tradability（CUT）、
   researchAddOn（early_extra_bad）、researchTurtle（NOTE_EARLY）⛔ 只 import。
本檔另提供共用工具（財報品質、現增可轉債兩支正式跑 import 重用）：exright 版旗標 build_exr／make_x、向量化出場 exits_vec、持有路徑 path_val、
   統計 stats／block_ci、資料快照 pinned_data。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndMom [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndMom_check
輸出 backtest/resultsIndMom/（⛔ 不碰 freq/）：IndMom.json、IndMom_表.csv（判定表＋並報＋描述）、events_<世界>.csv.gz（逐筆產業-月：R產業、R市場、X）、
     fake_reps.csv、block_ci.csv、corr.csv（月報酬相關）、monthly_ret.csv.gz（月報酬序列）、recon_freq.csv（頻率表逐列重建）、
     exright_diff.csv（exright 版與頻率表口徑不同的列）、先驗.csv、run.log

═══ 讀法（I 標續編；頻率表 I1～I9 原樣沿用，以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 I10 資料快照：產業別等 ＝ 頻率表當時的 origin/main 1ab51f2820df（~/b2fwork/main_1ab51f2820df，唯讀；⛔ 不用之後更新的 main，以免與頻率表不同）；
     價格面板 ＝ 頻率表同一份快取 ~/b2fwork/panel_<世界>.pkl。exright 表 ＝ origin/main b5532121f8d8（三件共用一份）。
 I11 exright 版（裁定 seq412 §三：新件一律用 exright 的 open_base）：★ 上市 exright 表（universe/exright＋early/exright）有 open_base 的除權息日，
     ① 開盤鎖漲停 ＝ 原始開盤 ＝ limit_price(open_base, 漲, 7%／10%) ∧ 原始最低 ＝ 原始開盤（tradability／researchSlip 同式，只把參考價換成 open_base；
        舊口徑在除權息日一律不判）；② 幽靈還原壞根 ＝ 原始收盤 ÷ open_base 不在 [0.895, 1.105]（取代 load_bars 的 原始收盤 ÷ (前收 × adj 因子)）；
        舊口徑判為幽靈、新口徑不是 ⇒ 該根若沒有其他壞根原因（缺口 ≥ 5、applies 斷點、減資／面額、早年 reduce_v2）才拿掉。
     上櫃 otcexright 的 open_base 全空 ⇒ 上櫃維持舊口徑（★ 不改用 ref_price）。
     ⭐ 正式跑全程（形成期壞根、進場剔除、出場壞根）用 exright 版；另以舊口徑（＝頻率表）逐列重建頻率表當對帳（I12），兩版不同的列照報。
 I12 頻率表對帳：本檔用 I2～I7 同式（同一批 import 函式、舊口徑旗標）重建 freq/monthly.csv 的 形成月底、進場日、6月走完、排序母體檔數、可排名產業數、
     市值加權前3、前3成員數、前3股票數、進場剔除計數、等權前3、1月前3、最弱3，逐列比；任一不同 ⇒ 中止、⛔ 不算報酬。
 I13 持有（登錄 §一「持有 6 個月」；PTH R2 同式）：進場 e ＝ 形成月下一個曆月第一個交易日（I6）；出場 ＝ 第 j＋H 個月底（＝ e 所在曆月起第 H 個曆月最後交易日）收盤。
     H ＝ 6 判、1／12 描述（登錄 §四 天數軸）。逐股出場：（e, x 當天或之前最後一根］有壞 K 棒 ⇒ 第一個壞 K 棒前一根收盤強制；最後一根 ＜ x 且距資料尾 ≥ 5 日
     ⇒ 末根收盤（下市）；x 當天無成交 ⇒ 之前最後一根收盤；x 超出完整月 ⇒ 不可算（段只收「H 個月走完」）。R ＝ 出場還原收盤 ÷ e 還原開盤 − 1。
     ★ 不跨世界：早年事件 H 個月走不完（跨 2014→2015 接縫）⇒ 不收（＝頻率表「6月走完」口徑）。
 I14 產業報酬（登錄 §二）＝ 產業成員（I2 母體、該產業、e 進場「保留」、R 可算）的 R 以 ★ t 市值（排序日原始收盤 × 股數）加權；
     〔形成期用起點 a 的市值排名（I5），持有用 t 的市值＝買進時已知的最新市值〕。等權版（並報）＝ 等權排名、成員等權持有 ★。
     全市場 ＝ ★ 同月 I2 排序母體（6 個月形成；含成員 ＜ 5 檔的產業、不含 I4 排除類別）中 e 進場保留 ∧ R 可算者，t 市值加權；各臂共用同一條市場。
     X ＝ R產業 − R市場 − 0.585%（登錄「扣 0.585%」：市場是基準、不交易 ⇒ 只扣產業那一邊 ★）。
 I15 判定（登錄 §二）：判定格 ＝ 市值加權、6 個月形成、6 個月持有；段 ＝ 探索、確認各報（I7 依進場日歸段、只收 6 個月走完）；早年描述。
     X̄ 進場月分群 CI（research11.cl_stats 式）1.96；Bonferroni 族 N ＝ 1（本登錄 1 格）⇒ z ＝ 1.96；n_eff ＝ min(筆數, 進場月數) ＜ 30 ⇒ 依構造不可判定、
     30～99 ⇒「樣本中等」；② ＝ 下界 ＞ 0、③ ＝ 上界 ＜ 0、① ＝ 含 0。
     seq322（researchPTH R6 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄（毛，＝ X̄ ＋ 0.585%）− 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；
     ★ 本件 X 已扣成本 ⇒ 第四條即 X̄ ＞ 0（不重複扣）。
 I16 假訊號臂（登錄 §二「每月隨機 3 個產業，30 次」）：r ＝ 0…29；每個段內形成月 j，從該月可排名產業（成員 ≥ 5，依名稱排序）不放回抽 3 個；
     種子 default_rng([20261021＋r, 世界標(主 0／早年 1), j])；產業報酬、市場、X 同 I14；進場月分群 ⇒ 結果；x ＝ 30 次中落結果② 的次數。
 I17 描述（⛔ 不判、不計 N）：等權版、1 個月形成版、最弱 3 個產業、H1／H12；6 個月不重疊區塊重抽 CI（段內進場月由第一個事件月起每 6 個曆月一塊，
     有放回 10,000 次，種子 [20261022, 段序, 臂序]）；與判定 ①②③ 不同 ⇒「區塊 CI 較寬」。
 I18 ⭐ 必答（seq407）月報酬相關：★ 三條月報酬序列都用 Jegadeesh–Titman 重疊 6 份（每個形成月一份、e 開盤進、持有 6 個月、買進持有權重漂移、出場後凍結）：
     本件 ＝ 入選 3 產業全部保留成員以 t 市值加權（登錄 §三「每份 3 個產業市值加權」）；PTH 前 30% ＝ PTH 頻率表同形成月「入選」∩ 面板 ∩ e 保留，等權；
     個股 12−1 前 30% ＝ I8 同法，等權；★ 三者同一進場日（PTH 件本身跳 1 個月，這裡不跳，只比選股）。月 τ 報酬 ＝ 當月在持有中的各份月報酬等權平均；
     不扣成本。報 Pearson 相關（原始月報酬＝登錄字面、判「≥ 0.9 照寫只是個股動能換個包裝」）；另報扣全市場（I14 市場、同法）後的超額月報酬相關（描述）。
     持股重疊比例 ＝ 引頻率表 equiv.csv（⛔ 不重算）。
 I19 結果句必附：「產業別用當時的產業分類」「原文美股 20 產業、台股產業數不同」「單筆層通過 ≠ 組合會贏 0050」；早年另附 researchTurtle.NOTE_EARLY
     （reduce_v2 約 0.3%）。本件不用月營收 ⇒ 不附存活者句（產業別 fallback 用月營收彙總表類別，無類別的股-月照計數）。
     同根兩出場價取較低（seq373）：本件每筆只有一種出場價（固定持有期收盤／壞根前一根收盤／下市末根互斥）⇒ 不適用，照寫。固定持有期為登錄照文獻（seq308 照登錄）。
 I20 先驗（登錄 §六）判讀 ★：① 判定格 探索、確認 皆結果①；② 主全窗（2017-03～）原始月報酬與 PTH 前 30% 相關 ≥ 0.7；
     ③ 主全窗（探索＋確認合併）1 個月形成版 X̄ ＞ 6 個月版 X̄。各段另報。
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import os
import pickle
import subprocess
import sys
import tarfile
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchPTH_freq as PF                 # noqa: E402  month_ends／entry_pos
from backtest import research11 as R                        # noqa: E402  cl_stats、limit_price
from backtest import tradability as TR                      # noqa: E402  CUT
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY
from backtest import evaluate as EVAL                       # noqa: E402  COST
import backtest.data as D                                   # noqa: E402

REG_SHA = "1d295bb0edd70326"
PIN_SHA = "1ab51f2820df86eb41a17a1a403bf56eca4d9041"
EXR_SHA = "b5532121f8d8d18e52328cae2345cd56220289d0"
OUT = "backtest/resultsIndMom"
FREQ_DIR = "backtest/resultsIndMom/freq"
WORK = IM.WORK
COST = EVAL.COST
Z196 = 1.96
NEFF_MIN = 30
NFAKE = 30
BOOT = 10_000
HS = (1, 6, 12)
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-01-01", "2014-12-31")}}
ARMS = {"市值加權6月(判定)": ("vw", 6), "等權6月(並報)": ("ew", 6), "市值加權1月(描述)": ("vw", 1), "最弱3(描述)": ("vwb", 6)}
ARMTAG = {"市值加權6月(判定)": 0, "等權6月(並報)": 1, "市值加權1月(描述)": 2, "最弱3(描述)": 3}
WTAG = {"主": 0, "早年": 1}
SENT = ["產業別用當時的產業分類", "原文美股 20 產業、台股產業數不同", "單筆層通過 ≠ 組合會贏 0050"]
SENT_373 = "同根兩出場價取較低（seq373）：本件每筆只有一種出場價（固定持有期收盤／壞根前一根收盤／下市末根互斥）⇒ 不適用，照寫"
LOG = IM.LOG
log = IM.log


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 共用：資料快照 ═════════════
def pinned_data(sha):
    root = os.path.join(WORK, f"main_{sha[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        raise SystemExit(f"⛔ 找不到頻率表當時的資料快照 {root}")
    if open(os.path.join(root, ".done")).read().strip() != sha:
        raise SystemExit(f"⛔ 快照 {root} 的 sha 不符")
    return os.path.join(root, "data")


def load_exr_table(sha=EXR_SHA):
    """上市 exright（universe＋early）四碼、open_base 有值 ⇒ {sid: [(date, open_base)]}。上櫃 open_base 全空另計數。"""
    cp = os.path.join(WORK, f"exrtab_{sha[:12]}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    p = subprocess.run(["git", "archive", "--format=tar", sha, "data/universe/exright", "data/early/exright", "data/universe/otcexright"],
                       capture_output=True, check=True).stdout
    tf = tarfile.open(fileobj=io.BytesIO(p))
    fr = []
    for m in tf.getmembers():
        if m.name.endswith(".csv"):
            x = pd.read_csv(tf.extractfile(m), dtype=str)
            x["src"] = "otc" if "otcexright" in m.name else "twse"
            fr.append(x)
    X = pd.concat(fr, ignore_index=True)
    X["stock_id"] = X["stock_id"].astype(str).str.strip()
    X = X[X["stock_id"].str.fullmatch(r"\d{4}")].copy()
    X["ob"] = pd.to_numeric(X["open_base"].astype(str).str.replace(",", ""), errors="coerce")
    info = {"上市列(四碼)": int((X["src"] == "twse").sum()), "上櫃列(四碼)": int((X["src"] == "otc").sum()),
            "上市open_base有值": int(((X["src"] == "twse") & (X["ob"] > 0)).sum()), "上櫃open_base有值": int(((X["src"] == "otc") & (X["ob"] > 0)).sum())}
    T = X[(X["src"] == "twse") & (X["ob"] > 0)].drop_duplicates(["stock_id", "date"])
    tab = defaultdict(list)
    for s, d, ob in zip(T["stock_id"], T["date"], T["ob"]):
        tab[s].append((pd.Timestamp(d), float(ob)))
    out = {"tab": dict(tab), "info": info, "sha": sha}
    pickle.dump(out, open(cp, "wb"))
    return out


_E: dict = {}


def _exr_job(a):
    """一檔：回 (sid, [(p, upl_new, ph_old, ph_new, other)])。"""
    wn, sid, i = a
    G = _E[wn]; cal = G["cal"]; n0 = len(cal)
    D.DATA = G["data"]
    rows = G["tab"].get(sid, [])
    fp = os.path.join(G["data"], "stocks", f"{sid}.csv")
    if not rows or not os.path.exists(fp):
        return sid, []
    raw = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "open", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").reindex(cal)
    ro, rl, rc = (np.array(pd.to_numeric(raw[k], errors="coerce").to_numpy(float), copy=True) for k in ("open", "low", "close"))
    for x in (ro, rl, rc):
        x[~(x > 0)] = np.nan
    vp = G["VP"][i]
    adj = D.load_adj(sid)
    dates_v = cal[vp]
    out = []
    st = None; bps = None
    for d, ob in rows:
        p = int(cal.searchsorted(d))
        if p >= n0 or cal[p] != d:
            continue
        k = int(np.searchsorted(vp, p))
        if k >= len(vp) or vp[k] != p or k == 0:
            continue
        pp = int(vp[k - 1])
        lim = 0.07 if d < TR.CUT else 0.10
        upn = bool(np.isfinite(ro[p]) and abs(ro[p] - R.limit_price(ob, True, lim)) < 1e-6 and np.isfinite(rl[p]) and rl[p] == ro[p])
        pho = False
        if adj is not None and len(adj):
            for ad, f in zip(adj["date"], adj["factor"].astype(float)):
                if int(np.searchsorted(dates_v, ad)) == k and np.isfinite(rc[p]) and np.isfinite(rc[pp]) and f > 0:
                    r_ = rc[p] / (rc[pp] * f)
                    if r_ < 0.895 or r_ > 1.105:
                        pho = True
        phn = bool(np.isfinite(rc[p]) and not (0.895 <= rc[p] / ob <= 1.105))
        other = None
        if pho and not phn:
            other = []
            if p - pp - 1 >= 5:
                other.append("缺口≥5")
            if st is None:
                st = D.load_stock(sid, G["mk"].get(sid, "twse"), cal)
                bps = [b for b in D.breakpoints(st.df, st.event_dates) if D.applies(b)] if st is not None else []
            if any(int(b["pos"]) == p for b in bps):
                other.append("斷點")
            if adj is not None and len(adj) and "event" in adj:
                for ad, ev in zip(adj["date"], adj["event"].astype(str)):
                    if ev in ("reduce", "parvalue"):
                        q = int(cal.searchsorted(ad))
                        kq = int(np.searchsorted(vp, q))
                        if kq < len(vp) and vp[kq] == p:
                            other.append("減資面額")
            if any(int(np.searchsorted(vp, q)) == k for q in G["EX"].get(sid, ())):
                other.append("早年reduce_v2")
        out.append((p, upn, pho, phn, other))
    return sid, out


def build_exr(Z, procs=2, logf=None):
    """I11：回 {UPLX, BADX, info, diff}（日曆布林矩陣，同 Z 形狀）；快取 ~/b2fwork/exrx_<世界>_<exr sha12>.pkl。"""
    logf = logf or log
    wn = Z["wn"]
    cp = os.path.join(WORK, f"exrx_{wn}_{EXR_SHA[:12]}.pkl")
    if os.path.exists(cp):
        X = pickle.load(open(cp, "rb"))
        logf(f"[exright {wn}] 讀快取 {cp}｜{X['info']}")
        return X
    t0 = time.time()
    T = load_exr_table()
    Z = IM.panel_aux(Z)
    EX = {}
    if wn == "早年":
        from backtest import researchAddOn as RA
        Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
        EXr, _ = RA.early_extra_bad(Wa, lambda s: None)
        EX = {s: set(int(k) for k in v) for s, v in EXr.items()}
    _E[wn] = {"cal": Z["cal"], "data": Z["data"], "tab": T["tab"], "VP": Z["VP"], "mk": Z["mk"], "EX": EX}
    jobs = [(wn, s, i) for i, s in enumerate(Z["sids"]) if s in T["tab"]]
    res = {}
    with Pool(procs) as pool:
        for sid, r in pool.imap_unordered(_exr_job, jobs, chunksize=8):
            res[sid] = r
    UPLX = np.array(Z["UPL"], bool, copy=True); BADX = np.array(Z["BAD"], bool, copy=True)
    ix = {s: i for i, s in enumerate(Z["sids"])}
    diff = []; cnt = Counter()
    for sid, rows in res.items():
        i = ix[sid]
        for p, upn, pho, phn, other in rows:
            cnt["exright列(有K棒)"] += 1
            if bool(UPLX[i, p]) != upn:
                diff.append({"世界": wn, "sid": sid, "date": str(Z["cal"][p].date()), "項": "開盤鎖漲停", "舊": bool(UPLX[i, p]), "新": upn})
                cnt["開盤鎖漲停_變"] += 1
                UPLX[i, p] = upn
            if phn and not pho and not BADX[i, p]:
                BADX[i, p] = True; cnt["壞根_新增"] += 1
                diff.append({"世界": wn, "sid": sid, "date": str(Z["cal"][p].date()), "項": "幽靈壞根新增", "舊": False, "新": True})
            elif pho and not phn:
                if other:
                    cnt["壞根_舊幽靈但另有原因保留"] += 1
                elif BADX[i, p]:
                    BADX[i, p] = False; cnt["壞根_拿掉"] += 1
                    diff.append({"世界": wn, "sid": sid, "date": str(Z["cal"][p].date()), "項": "幽靈壞根拿掉", "舊": True, "新": False})
    info = {"exright表": T["info"], "計數": dict(cnt), "秒": round(time.time() - t0)}
    X = {"UPLX": UPLX, "BADX": BADX, "info": info, "diff": diff}
    pickle.dump(X, open(cp, "wb"), protocol=5)
    logf(f"[exright {wn}] {info}")
    return X


def make_x(Z, X):
    """exright 版面板（共用價格，只換 UPL、BAD 與衍生）。"""
    Zx = {k: v for k, v in Z.items() if k not in ("CB", "VP", "LV", "NXB", "LAST")}
    Zx["UPL"] = X["UPLX"]; Zx["BAD"] = X["BADX"]
    return aux2(IM.panel_aux(Zx))


def aux2(Z):
    """LV[i,p] ＝ p 當天或之前最後一根有效 K 棒位置（無 ⇒ −1）；NXB[i,p] ＝ ≥ p 的第一個壞根位置（無 ⇒ BIG）；LAST[i] ＝ 最後一根。"""
    if "LV" not in Z:
        S, n0 = Z["C"].shape
        ar = np.arange(n0, dtype=np.int32)
        v = np.isfinite(Z["C"])
        Z["LV"] = np.maximum.accumulate(np.where(v, ar, -1).astype(np.int32), axis=1)
        BIG = n0 + 10
        Z["NXB"] = np.minimum.accumulate(np.where(Z["BAD"], ar, BIG).astype(np.int32)[:, ::-1], axis=1)[:, ::-1]
        Z["LAST"] = Z["LV"][:, -1]
    return Z


TYPN = {1: "到期收盤", 2: "到期日無成交用前一根", 3: "壞根前一根強制", 4: "下市末根", 5: "超出資料尾不可算"}


def exits_vec(Z, ii, e, x):
    """I13：ii 股票索引陣列（e 已有效、保留）、e 進場日曆位置（純量或陣列）、x 目標出場日曆位置（可 ＞ n0−1）。
    回 (exitpos, R, typ)；typ 5 ⇒ R＝nan、exitpos＝n0−1（持有路徑用：未出場）。"""
    ii = np.asarray(ii, np.int64); n0 = Z["C"].shape[1]
    e = np.broadcast_to(np.asarray(e, np.int64), ii.shape); x = np.broadcast_to(np.asarray(x, np.int64), ii.shape)
    xe = np.minimum(x, n0 - 1)
    kx = Z["LV"][ii, xe].astype(np.int64)
    e1 = np.minimum(e + 1, n0 - 1)
    fb = np.where(e + 1 <= n0 - 1, Z["NXB"][ii, e1], n0 + 10).astype(np.int64)
    forced = fb <= kx
    L = Z["LAST"][ii].astype(np.int64)
    dl = ~forced & (L < x) & (n0 - 1 - L >= 5)
    beyond = ~forced & ~dl & (x > n0 - 1)
    exitpos = kx.copy()
    fpos = Z["LV"][ii, np.maximum(fb - 1, 0).clip(max=n0 - 1)].astype(np.int64)
    exitpos[forced] = fpos[forced]
    exitpos[dl] = L[dl]
    typ = np.where(forced, 3, np.where(dl, 4, np.where(beyond, 5, np.where(kx == xe, 1, 2)))).astype(np.int8)
    o = Z["O"][ii, e]
    Rv = Z["C"][ii, np.clip(exitpos, 0, n0 - 1)] / o - 1.0
    Rv = np.where(beyond, np.nan, Rv)
    exitpos = np.where(beyond, n0 - 1, exitpos)
    return exitpos, Rv, typ


def path_val(Z, ii, e, exitpos, taus):
    """持有路徑：各股在月底 τ（日曆位置陣列）的價值（相對 e 開盤 ＝ 1）；τ ≥ 出場 ⇒ 出場價凍結；回 shape (len(ii), len(taus))。"""
    ii = np.asarray(ii, np.int64); taus = np.asarray(taus, np.int64)
    pos = np.minimum(taus[None, :], np.asarray(exitpos, np.int64)[:, None])
    lv = Z["LV"][ii[:, None], pos]
    return Z["C"][ii[:, None], lv] / Z["O"][ii, np.asarray(e, np.int64) if np.ndim(e) else e][:, None]


# ═════════════ 共用：統計 ═════════════
def res_of(lo, hi, ne):
    if ne < NEFF_MIN:
        return "依構造不可判定"
    return "結果①" if lo <= 0 <= hi else ("結果②" if lo > 0 else "結果③")


def stats(x, key, zj=Z196, zb=None):
    """x 逐筆、key 分群；zj ＝ 判定 z；zb ＝ Bonferroni z（None ⇒ 同 zj）。"""
    x = np.asarray(x, float); key = np.asarray(key)
    ok = np.isfinite(x); x = x[ok]; key = key[ok]
    n = len(x)
    if n == 0:
        return {"n": 0, "n_eff": 0, "結果": "依構造不可判定"}
    cs = R.cl_stats(x, key)
    m, se, ng = cs["mean"], cs["se"], cs["months"]
    ne = int(min(n, ng)); zb = zj if zb is None else zb
    mm = pd.Series(x).groupby(key).mean()
    o = {"n": int(n), "群數": int(ng), "n_eff": ne, "X̄": m, "中位": float(np.median(x)), "X勝率": float((x > 0).mean()), "se": se,
         "lo": m - zj * se, "hi": m + zj * se, "結果": res_of(m - zj * se, m + zj * se, ne),
         "lo196": m - Z196 * se, "hi196": m + Z196 * se, "結果196": res_of(m - Z196 * se, m + Z196 * se, ne),
         "bonf_z": zb, "bonf_lo": m - zb * se, "bonf_hi": m + zb * se, "t": m / se if se > 0 else np.nan,
         "逐月平均之中位": float(mm.median()), "逐月中位與平均同號": bool(np.sign(mm.median()) == np.sign(m)),
         "樣本": "樣本中等" if 30 <= ne < 100 else ("一般" if ne >= 100 else "不足")}
    return o


def block_ci(x, mkey, B_months, seed, z=None):
    """I17：mkey ＝ 進場月 'YYYY-MM'；由第一個月起每 B_months 個曆月一塊；有放回重抽 BOOT 次；回 (lo, hi, 結果, 塊數)。"""
    x = np.asarray(x, float); ok = np.isfinite(x); x = x[ok]; mk = np.asarray(mkey)[ok]
    if len(x) == 0:
        return {"塊數": 0}
    mi = np.array([int(s[:4]) * 12 + int(s[5:7]) - 1 for s in mk])
    blk = (mi - mi.min()) // B_months
    S = pd.Series(x).groupby(blk).agg(["sum", "count"])
    sums, cnts = S["sum"].to_numpy(), S["count"].to_numpy(float)
    nb = len(S)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nb, size=(BOOT, nb))
    bm = sums[pick].sum(1) / cnts[pick].sum(1)
    lo, hi = float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))
    return {"塊數": int(nb), "lo": lo, "hi": hi, "結果": "結果①" if lo <= 0 <= hi else ("結果②" if lo > 0 else "結果③")}


def seq322(st, x_fake, cost_in_x=True):
    c = {"結果②": st.get("結果") == "結果②", "Bonferroni下界>0": bool(st.get("bonf_lo", -1) > 0), "假訊號x≤1": bool(x_fake is not None and x_fake <= 1),
         "X̄−成本>0": bool((st.get("X̄", -1) if cost_in_x else st.get("X̄", -1) - COST) > 0), "逐月中位與平均同號": bool(st.get("逐月中位與平均同號"))}
    return all(c.values()), c


# ═════════════ 本件 ═════════════
def mkey_of(cal, p):
    return cal[p].strftime("%Y-%m")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    DATA = pinned_data(PIN_SHA)
    log(f"[資料] 頻率表快照 {PIN_SHA[:12]} ⇒ {DATA}；exright 表 {EXR_SHA[:12]}")
    PIT = IM.load_pit(DATA)
    mon_freq = pd.read_csv(os.path.join(FREQ_DIR, "monthly.csv"), dtype=str, keep_default_na=False)
    J = {"性質": "產業價格動能 seq1 事件層正式跑", "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq407 第一題、seq408 發號 N_前段 ＋1、seq412 §四 開正式跑",
         "資料": {"產業別快照": PIN_SHA, "exright": EXR_SHA}, "世界": {}}
    EVROWS = []; TAB = []; FAKE = []; BLK = []; CORR = []; MRET = []; RECON = []; EXD = []; PRIOR = []
    statsJ = {}
    for wn in ("主", "早年"):
        Z = IM.build_panel(wn, a.procs)
        Zo = aux2(IM.panel_aux(Z))
        X = build_exr(Zo, a.procs)
        Zx = make_x(Zo, X)
        EXD += X["diff"]
        cal = Zo["cal"]; n0 = Zo["n0"]
        ME, MK = PF.month_ends(cal); nm = len(ME)
        EP = PF.entry_pos(cal, MK, 1)
        # ── 兩口徑每月排序
        M = {"o": {}, "x": {}}
        for ver, ZZ in (("o", Zo), ("x", Zx)):
            for j in range(6, nm):
                M[ver][j] = {L: dict(zip(("mem", "rej", "univ"), IM.month_table(ZZ, PIT, ME, j, L))) for L in (6, 1)}
                for L in (6, 1):
                    M[ver][j][L]["rk"] = IM.rank_inds(M[ver][j][L]["mem"])
        log(f"[{wn}] 兩口徑排序完｜{time.time() - t0:.0f}s")

        def picks(ver, j, arm):
            kind, L = ARMS[arm]
            if kind == "vwb":
                lst = M[ver][j][6]["rk"]["vw"]; return [k for k, _ in lst[-3:][::-1]], 6
            lst = M[ver][j][L]["rk"][kind]
            return [k for k, _ in lst[:3]], L

        # ── I12 頻率表逐列重建（舊口徑）
        fz = mon_freq[mon_freq["世界"] == wn].reset_index(drop=True)
        nbad = 0
        for r_, j in enumerate(range(6, nm)):
            t = int(ME[j]); e = int(EP[j]); m6 = M["o"][j][6]
            top, _ = picks("o", j, "市值加權6月(判定)"); topE, _ = picks("o", j, "等權6月(並報)"); top1, _ = picks("o", j, "市值加權1月(描述)")
            bot, _ = picks("o", j, "最弱3(描述)")
            sv = [i for k in top for (i, _, _) in m6["mem"].get(k, [])]
            fl = Counter(IM.entry_flag(Zo, i, t, e) for i in sv) if e >= 0 else Counter({"超出資料尾": len(sv)})
            mine = {"形成月底": str(cal[t].date()), "進場日": str(cal[e].date()) if e >= 0 else "", "6月走完": str(bool(j + 6 < nm)),
                    "排序母體檔數": str(len(m6["univ"])), "可排名產業數(≥5)": str(len(m6["rk"]["vw"])), "市值加權前3": "｜".join(top),
                    "前3成員數": "｜".join(str(len(m6["mem"][k])) for k in top), "前3股票數": str(len(sv)), "等權前3": "｜".join(topE),
                    "1月前3": "｜".join(top1), "最弱3(描述)": "｜".join(bot)}
            fr = fz.iloc[r_]
            bad_cols = [c for c, v in mine.items() if str(fr[c]) != v]
            fcnt = {c[3:]: int(float(fr[c])) for c in fz.columns if c.startswith("進場_") and str(fr[c]) not in ("", "nan")}
            if fcnt != {k: v for k, v in fl.items() if v}:
                bad_cols.append("進場剔除計數")
            RECON.append({"世界": wn, "形成月底": mine["形成月底"], "相同": not bad_cols, "不同欄": "｜".join(bad_cols)})
            nbad += bool(bad_cols)
        if len(fz) != nm - 6 or nbad:
            raise SystemExit(f"⛔ [{wn}] 頻率表逐列重建不同：{nbad} 列（頻率表 {len(fz)} 列、本檔 {nm - 6}）⇒ 中止、不算報酬")
        log(f"[{wn}] I12 頻率表逐列重建：{nm - 6} 列全同")
        # exright 版與舊口徑入選差異
        for j in range(6, nm):
            for arm in ARMS:
                po, _ = picks("o", j, arm); px, _ = picks("x", j, arm)
                if po != px:
                    EXD.append({"世界": wn, "sid": "", "date": str(cal[int(ME[j])].date()), "項": f"入選產業不同:{arm}", "舊": "｜".join(po), "新": "｜".join(px)})
        # ── 逐月：市場、產業事件
        MKT = {}; EVT = {}

        def hold(ii, j, H):
            e = int(EP[j]); x = int(ME[j + H]) if j + H < nm else n0 + 400
            return exits_vec(Zx, ii, e, x)

        def ind_ret(j, L, ind, H, ew=False):
            t = int(ME[j]); e = int(EP[j])
            mem = [i for (i, _, _) in M["x"][j][L]["mem"].get(ind, []) if IM.entry_flag(Zx, i, t, e) == "保留"]
            if not mem:
                return np.nan, 0, 0
            ex, Rv, typ = hold(np.array(mem), j, H)
            ok = np.isfinite(Rv)
            if not ok.any():
                return np.nan, len(mem), 0
            w = np.ones(ok.sum()) if ew else np.nan_to_num(Zx["MC"][np.array(mem)[ok], t])
            if w.sum() <= 0:
                return np.nan, len(mem), int(ok.sum())
            return float((w * Rv[ok]).sum() / w.sum()), len(mem), int(ok.sum())

        for j in range(6, nm):
            if EP[j] < 0:
                continue
            t = int(ME[j]); e = int(EP[j])
            uv = [i for i in M["x"][j][6]["univ"] if IM.entry_flag(Zx, i, t, e) == "保留"]
            for H in HS:
                if j + H >= nm:
                    continue
                ex, Rv, typ = hold(np.array(uv), j, H)
                ok = np.isfinite(Rv); w = np.nan_to_num(Zx["MC"][np.array(uv)[ok], t])
                MKT[(j, H)] = float((w * Rv[ok]).sum() / w.sum()) if w.sum() > 0 else np.nan
        log(f"[{wn}] 市場報酬完｜{time.time() - t0:.0f}s")
        segs = SEGS[wn]
        segp = {sg: IM.seg_bounds(cal, x_, y_) for sg, (x_, y_) in segs.items()}

        def seg_of(j):
            if EP[j] < 0:
                return None
            for sg, (p0, p1) in segp.items():
                if p0 <= EP[j] <= p1:
                    return sg
            return None

        for arm in ARMS:
            for H in HS:
                if arm != "市值加權6月(判定)" and H != 6:
                    continue
                for j in range(6, nm):
                    sg = seg_of(j)
                    if sg is None or j + H >= nm:
                        continue
                    inds, L = picks("x", j, arm)
                    for rank, ind in enumerate(inds):
                        Ri, nmem, nok = ind_ret(j, L, ind, H, ew=(ARMS[arm][0] == "ew"))
                        Xv = Ri - MKT[(j, H)] - COST
                        EVROWS.append({"世界": wn, "段": sg, "臂": arm, "H": H, "形成月底": str(cal[int(ME[j])].date()), "進場日": str(cal[int(EP[j])].date()),
                                       "進場月": mkey_of(cal, int(EP[j])), "名次": rank + 1, "產業": ind, "成員保留": nmem, "成員R可算": nok,
                                       "R產業": Ri, "R市場": MKT[(j, H)], "X": Xv})
        log(f"[{wn}] 事件完｜{time.time() - t0:.0f}s")
        # ── 假訊號臂（判定格 H6）
        for sg in segs:
            js = [j for j in range(6, nm) if seg_of(j) == sg and j + 6 < nm]
            for r in range(NFAKE):
                xs = []; ks = []
                for j in js:
                    names = sorted(k for k, _ in M["x"][j][6]["rk"]["vw"])
                    rng = np.random.default_rng([20261021 + r, WTAG[wn], j])
                    for ind in rng.choice(names, size=min(3, len(names)), replace=False):
                        Ri, _, _ = ind_ret(j, 6, str(ind), 6)
                        xs.append(Ri - MKT[(j, 6)] - COST); ks.append(mkey_of(cal, int(EP[j])))
                st = stats(xs, ks)
                FAKE.append({"世界": wn, "段": sg, "r": r, "n": st["n"], "n_eff": st["n_eff"], "X̄": st.get("X̄"), "lo": st.get("lo"), "hi": st.get("hi"),
                             "結果": st["結果"]})
        log(f"[{wn}] 假訊號臂完｜{time.time() - t0:.0f}s")
        # ── I18 月報酬相關
        PTHS = IM.load_pth_sets(wn)
        sid_ix = {s: i for i, s in enumerate(Zx["sids"])}
        series = defaultdict(lambda: defaultdict(list))   # name → τ月序 → [cohort 月報酬]
        for j in range(6, nm):
            if EP[j] < 0 or j + 1 >= nm:
                continue
            t = int(ME[j]); e = int(EP[j]); ts = str(cal[t].date())
            kmax = min(6, nm - 1 - j)
            taus = np.array([int(ME[j + k]) for k in range(1, kmax + 1)])
            x6 = int(ME[j + 6]) if j + 6 < nm else n0 + 400
            top, _ = picks("x", j, "市值加權6月(判定)")
            sets = {"本件(3產業市值加權)": ([i for k in top for (i, _, _) in M["x"][j][6]["mem"].get(k, [])], "mc"),
                    "全市場(市值加權)": (list(M["x"][j][6]["univ"]), "mc")}
            if ts in PTHS:
                pth_top, _, mom_top, _ = PTHS[ts]
                sets["PTH前30%(等權)"] = ([sid_ix[s] for s in pth_top if s in sid_ix], "ew")
                sets["12-1前30%(等權)"] = ([sid_ix[s] for s in mom_top if s in sid_ix], "ew")
            for nmx, (ii, wt) in sets.items():
                ii = np.array([i for i in ii if IM.entry_flag(Zx, i, t, e) == "保留"], np.int64)
                if len(ii) == 0:
                    continue
                ex, Rv, typ = exits_vec(Zx, ii, e, x6)
                V = path_val(Zx, ii, e, ex, taus)
                w = np.nan_to_num(Zx["MC"][ii, t]) if wt == "mc" else np.ones(len(ii))
                okv = np.isfinite(V).all(1) & (w > 0)
                if not okv.any():
                    continue
                Vp = (w[okv, None] * V[okv]).sum(0) / w[okv].sum()
                prev = np.r_[1.0, Vp[:-1]]
                for k in range(kmax):
                    series[nmx][j + 1 + k].append(Vp[k] / prev[k] - 1.0)
        MS = pd.DataFrame({nmx: {MK[q][0] * 100 + MK[q][1]: float(np.mean(v)) for q, v in d.items()} for nmx, d in series.items()}).sort_index()
        MS.index.name = "年月"
        for c in list(MS.columns):
            if c != "全市場(市值加權)":
                MS[c + "_超額"] = MS[c] - MS["全市場(市值加權)"]
        mr = MS.reset_index(); mr.insert(0, "世界", wn); MRET.append(mr)
        cwin = {"主": {"探索": (201703, 202112), "確認": (202201, 999999), "主全窗": (201703, 999999)}, "早年": {"早年": (200501, 201412)}}[wn]
        for sg, (y0, y1) in cwin.items():
            m_ = MS[(MS.index >= y0) & (MS.index <= y1)]
            row = {"世界": wn, "段": sg, "月數": int(len(m_))}
            for other in ("PTH前30%(等權)", "12-1前30%(等權)"):
                if other in m_:
                    q = m_[["本件(3產業市值加權)", other]].dropna(); row[f"r_原始_{other}"] = float(q.corr().iloc[0, 1]) if len(q) > 2 else None
                    q = m_[["本件(3產業市值加權)_超額", other + "_超額"]].dropna(); row[f"r_超額_{other}"] = float(q.corr().iloc[0, 1]) if len(q) > 2 else None
                    row[f"可比月數_{other}"] = int(len(q))
            q = m_[["本件(3產業市值加權)", "全市場(市值加權)"]].dropna(); row["r_原始_全市場(參考)"] = float(q.corr().iloc[0, 1]) if len(q) > 2 else None
            row["原始相關≥0.9(照寫只是個股動能換個包裝)"] = bool(any((row.get(f"r_原始_{o}") or 0) >= 0.9 for o in ("PTH前30%(等權)", "12-1前30%(等權)")))
            CORR.append(row)
        J["世界"][wn] = {"日曆": [str(cal[0].date()), str(cal[-1].date())], "月底數": nm, "exright": X["info"]}
    # ═════ 統計 ═════
    EV = pd.DataFrame(EVROWS)
    FK = pd.DataFrame(FAKE)
    eqf = pd.read_csv(os.path.join(FREQ_DIR, "equiv.csv"))
    for (wn, sg), g0 in EV.groupby(["世界", "段"], sort=False):
        for (arm, H), g in g0.groupby(["臂", "H"], sort=False):
            st = stats(g["X"], g["進場月"])
            cell = "判定" if (arm == "市值加權6月(判定)" and H == 6 and wn == "主") else "描述"
            row = {"世界": wn, "段": sg, "臂": arm, "H": H, "身分": cell, **{k: st.get(k) for k in ("n", "群數", "n_eff", "樣本", "X̄", "中位", "X勝率", "lo", "hi", "結果", "t",
                                                                                         "逐月平均之中位", "逐月中位與平均同號")},
                   "R產業̄": float(g["R產業"].mean()), "R市場̄": float(g["R市場"].mean())}
            if arm == "市值加權6月(判定)" and H == 6:
                fk = FK[(FK["世界"] == wn) & (FK["段"] == sg)]
                xf = int((fk["結果"] == "結果②").sum()); row["假訊號x(／30)"] = xf
                row["假訊號X̄中位"] = float(fk["X̄"].median()); row["假訊號X̄p95"] = float(fk["X̄"].quantile(0.95))
                ok322, c322 = seq322(st, xf)
                row["過seq322"] = ok322 if wn == "主" else "（早年描述、不判）"; row["seq322各條"] = json.dumps(c322, ensure_ascii=False)
            if H == 6:
                bk = block_ci(g["X"], g["進場月"], 6, [20261022, list(SEGS[wn]).index(sg) + (0 if wn == "主" else 5), ARMTAG[arm]])
                row["區塊CI"] = f"[{pct(bk.get('lo'))}, {pct(bk.get('hi'))}] {bk.get('結果')}"
                row["區塊CI較寬"] = bool(bk.get("結果") != st.get("結果")) if st.get("結果") != "依構造不可判定" else None
                BLK.append({"世界": wn, "段": sg, "臂": arm, **bk})
            TAB.append(row)
            statsJ[f"{wn}/{sg}/{arm}/H{H}"] = st
    TB = pd.DataFrame(TAB)
    CR = pd.DataFrame(CORR)
    # 結果句
    def word(r):
        return {"結果②": "多", "結果③": "少", "結果①": "分不出"}.get(r, "依構造不可判定")
    jd = TB[(TB["身分"] == "判定")].set_index("段")
    crm = CR[(CR["世界"] == "主") & (CR["段"] == "主全窗")].iloc[0]
    sent = (f"每月買過去 6 個月最強的 3 個產業、抱 6 個月：探索段比全市場{word(jd.loc['探索', '結果'])} {pct(jd.loc['探索', 'X̄'])}"
            f"（{jd.loc['探索', '樣本']}）、確認段{word(jd.loc['確認', '結果'])} {pct(jd.loc['確認', 'X̄'])}（{jd.loc['確認', '樣本']}）；"
            f"與個股 12−1 動能月報酬相關 r＝{crm['r_原始_12-1前30%(等權)']:.2f}、與 PTH 前 30% r＝{crm['r_原始_PTH前30%(等權)']:.2f}"
            f"（扣全市場後 r＝{crm['r_超額_12-1前30%(等權)']:.2f}／{crm['r_超額_PTH前30%(等權)']:.2f}）")
    wrap = any(crm[f"r_原始_{o}"] >= 0.9 for o in ("PTH前30%(等權)", "12-1前30%(等權)"))
    # 先驗
    p1 = bool((jd["結果"] == "結果①").all())
    p2 = bool(crm["r_原始_PTH前30%(等權)"] >= 0.7)
    mm = EV[(EV["世界"] == "主") & (EV["H"] == 6)]
    x6 = mm[mm["臂"] == "市值加權6月(判定)"]["X"].mean(); x1 = mm[mm["臂"] == "市值加權1月(描述)"]["X"].mean()
    p3 = bool(x1 > x6)
    PRIOR = [{"先驗": "① 事件層兩段皆 ①（約五成五）", "中": p1, "實際": "｜".join(f"{sg} {jd.loc[sg, '結果']}" for sg in jd.index)},
             {"先驗": "② 與 PTH 前 30% 月報酬相關 ≥ 0.7（約六成）", "中": p2,
              "實際": f"主全窗 r＝{crm['r_原始_PTH前30%(等權)']:.3f}；" + "｜".join(f"{r['段']} {r['r_原始_PTH前30%(等權)']:.3f}" for _, r in CR.iterrows() if r.get('r_原始_PTH前30%(等權)') is not None)},
             {"先驗": "③ 1 個月形成版 X 高於 6 個月版（約五成）", "中": p3, "實際": f"主全窗 1月 {pct(x1)} vs 6月 {pct(x6)}；"
              + "｜".join(f"{sg} 1月 {pct(mm[(mm['段'] == sg) & (mm['臂'] == '市值加權1月(描述)')]['X'].mean())} vs 6月 {pct(mm[(mm['段'] == sg) & (mm['臂'] == '市值加權6月(判定)')]['X'].mean())}" for sg in ("探索", "確認"))}]
    J.update({"判定": {sg: {k: (v if not isinstance(v, (np.floating, np.integer)) else v.item()) for k, v in jd.loc[sg].items()} for sg in jd.index},
              "結果句": sent, "只是個股動能換個包裝": bool(wrap), "必附": SENT + (["（早年）" + s for s in TU.NOTE_EARLY]), "seq373": SENT_373,
              "先驗": PRIOR, "先驗中": int(p1) + int(p2) + int(p3), "相關": CORR, "持股重疊(引頻率表)": eqf.to_dict("records"),
              "exright差異列數": len(EXD), "頻率表重建": {"列數": len(RECON), "全同": bool(all(r["相同"] for r in RECON))},
              "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")})
    TB.to_csv(os.path.join(OUT, "IndMom_表.csv"), index=False, encoding="utf-8-sig")
    for wn in ("主", "早年"):
        with gzip.open(os.path.join(OUT, f"events_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            EV[EV["世界"] == wn].to_csv(fh, index=False)
    FK.to_csv(os.path.join(OUT, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BLK).to_csv(os.path.join(OUT, "block_ci.csv"), index=False, encoding="utf-8-sig")
    CR.to_csv(os.path.join(OUT, "corr.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "monthly_ret.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.concat(MRET, ignore_index=True).to_csv(fh, index=False)
    pd.DataFrame(RECON).to_csv(os.path.join(OUT, "recon_freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EXD, columns=["世界", "sid", "date", "項", "舊", "新"]).to_csv(os.path.join(OUT, "exright_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PRIOR).to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "IndMom.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[判定] {sent}")
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

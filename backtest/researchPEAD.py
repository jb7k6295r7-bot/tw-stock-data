# -*- coding: utf-8 -*-
"""財報公告後漂移 PEAD seq1【事件層正式跑】（台股策略線 登錄 sha af545cdcfa5bf94f，2026-10-20 11:38；裁定 seq388 發號 N_前段 ＋1、
seq390 核准照登錄（上季切點）正式跑；Bernard & Thomas 1989：標準化盈餘意外 SUE 最高十分位，財報上傳後抱 60 個交易日）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchPEAD_freq（fin_hist／filing_dates 讀取、單季 EPS、閘；讀法 E1～E11 寫死、沿用）、researchPTH（fixed_exit）、
   researchUO（x_stats（族 N＝1）、agg_eval、diff_stats、Sampler）、researchAscTri_freq、research11、evaluate ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEAD [--procs 3]
    乾跑（⛔ 不算任何報酬；只驗事件重現）：... -m backtest.researchPEAD --dry
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEAD_check
輸出 backtest/resultsPEAD/（⛔ 不碰 freq/）：PEAD.json、PEAD_main.csv（判定表＋並報＋描述）、by_year.csv、fake_reps.csv、
    events/trades_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：上季切點 ＝ 判定格（登錄 §一 主）；同季切點 ＝ 並報（裁定 seq388／390）；描述（⛔ 不判、不計 N）：上季切點_20日、上季切點_120日（天數軸）、
    最低十分位（方向）、最高減最低、營收已先好／沒先好兩組（登錄 §四）、上傳當天到隔天反應；假訊號臂（同季隨機 10%、同可用日，30 次）。

═══ 讀法（F 標；頻率表 E1～E11 原樣沿用（資料、單季 EPS、SUE、可用日、十分位、進場剔除、段、營收分組、重疊），以下為正式跑新增；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 F1 事件 ＝ 用 researchPEAD_freq 的 load_eps、load_upload、stock_job（閘）原樣 ＋ 頻率表 main 的 SUE、切點、進場狀態算式（逐行照抄）重算 ⇒
    與已提交 backtest/resultsPEAD/freq/events.csv.gz 的 sid、季、SUE、e、上季切點_入選、同季切點_入選、最低十分位、st 逐列逐欄（字串）比，
    任一不同 ⇒ 中止、⛔ 不算報酬。事件 ＝ 該臂入選 ∧ st「保留」；進場 ＝ e（上傳日後第一個交易日）還原開盤。營收分組取自事件檔（頻率表 E8）。
 F2 出場（登錄 §一「60 個交易日收盤賣」）：★ 進場日 e 算第 1 個交易日，第 60 個交易日（日曆位置 e＋59）收盤賣〔另一讀法 e＋60〕
    （＝ 上傳日 u 之後第 60 個交易日；researchUO D3「T＋H」同式）。該日無成交 ⇒ 用當天或之前最後一根有效 K 棒收盤。
    ⛔ 不跨壞根（登錄 §三、seq335）：持有中遇壞 K 棒 ⇒ 前一根收盤強制；下市 ⇒ 末根收盤；超出資料尾 ⇒「資料尾未出場」，⛔ 不進 X
    （researchPTH R2 同一支 fixed_exit）。20／120 日描述同式。
 F3 R ＝ 出場價 ÷ e 還原開盤 − 1；淨 ＝ R − 0.585%；X ＝ R − 對照平均 R（兩邊同扣成本）。
 F4 對照（登錄 §二「同日同母體隨機 20 檔同持有」）：池 ＝ 同一 e：主世界股票 ∧ Frame.gate[e] ∧ pit_valid[e]（同頻率表 E6 閘）∧ e 有效 K 棒、有成交、開盤有效、
    非開盤鎖漲停 ∧ 同 H 的 R 可算（★ 不要求 SUE 可算〔另一讀法：限 SUE 可算公司〕）；★ 扣事件股自己與同一 e 同臂【原始】入選（任何狀態；researchUO E6 同）。
    不放回抽 20 檔（不足 ⇒ 全取、計數）；等權；⛔ 無持有限制（事件、對照都每筆獨立；同檔前後季持有重疊照報件數）。
    種子 default_rng([20261020, 格標, e, crc32(sid)])；格標 上季切點＝0、同季切點＝1、最低十分位＝9、上季切點_20日＝20、上季切點_120日＝120；假訊號 ＝ 1000＋r。
 F5 判定量 X̄；CI ＝ e 所在曆月分群（researchUO.x_stats）、1.96；n_eff ＝ min(可算筆數, 有事件曆月數)；n_eff ＜ 30 ⇒ 依構造不可判定、30～99 ⇒ 句首「樣本中等」；
    結果②／③／①（登錄 §二）。Bonferroni 族 N ＝ 1 ⇒ z ＝ 1.96。判定段：探索、確認【各自報】為準；主全窗參考；段前（2016）只描述；早年段不做（登錄）。
 F6 seq322（researchUO E9 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；只判定格各段各報。
    seq329 §二：族 N＝1 ⇒ 臨界 1.96，已含在結果② 內；|t| 照報。
 F7 假訊號臂（登錄 §二「同季隨機 10% 公司、同可用日，30 次」）：只做判定格；r ＝ 0…29；每段每季 q：池 ＝ 該季 SUE 可算 ∧ 有上傳時戳 ∧ st 保留
    ∧ R60 可算 ∧ e 在段內；★ 抽 ⌈0.1 × 池大小⌉ 家（不放回；default_rng([20261021＋r, qi, 段序號])），各用自己的 e；對照照 F4（扣自己與該 e 上季切點原始入選）；
    e 曆月分群 ⇒ 結果；x／30 ＝ 落結果② 的次數。
 F8 描述：最低十分位 ＝ 事件檔「最低十分位」（★ 頻率表 E5 實作用同季 10 百分位）∧ st 保留，60 日、對照同 F4（扣自己與同 e 最低十分位原始）；
    最高減最低 ＝ researchUO.diff_stats（上季切點 − 最低十分位，曆月分群線性化）；營收已先好／沒先好（＝有月 ≤ 0 ＋ 資料不全）＝ 判定格可算筆的子集，
    另報差（已先好 − 沒先好）；上傳當天到隔天反應 ＝ ffill 還原收盤(e) ÷ ffill 還原收盤(上傳日前一個交易日) − 1（★ 窗 ＝ 上傳日當天＋e；窗內有壞 K 棒 ⇒ 不算），
    減去同一批 20 檔對照同窗平均（對照窗內有壞 K 棒者不入平均）；⛔ 不判。
 F9 引自頻率表（⛔ 不重算）：每季入選比例範圍（上季切點）、EPS 缺（半年報公司 Q2／Q4）剔除數、與單季 EPS 季增重疊比例、門檻微前視、每季可算 SUE 公司數（先驗④）。
 F10 結果句必附：「SUE 十分位切點用上一季分布（本線定；每季實際入選 a%～b%）」「台股有月營收先揭露，漂移可能被提前吃掉」「早年段無上傳時戳不做」
     「半年報公司 Q2／Q4 單季 EPS 算不出而剔除」「與單季 EPS 季增重疊 a～b%（該件 seq329 不合格）」「單筆層通過 ≠ 組合會贏 0050」。
     本件出場為固定持有期（登錄照文獻、seq363；裁定 seq388 已核），無賣出訊號措辭；⛔ 不稱最高點、頂部（seq343）。
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import time
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPEAD_freq as PF                # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchPTH as PTH                     # noqa: E402  fixed_exit、trade_stats、block 以外不用
from backtest import researchUO as UO                       # noqa: E402  x_stats、agg_eval、diff_stats、Sampler
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
assert UO.N_FAM == 1 and UO.Z95 == 1.96 and UO.NCTRL == 20

REG_SHA = PF.REG_SHA
OUT = "backtest/resultsPEAD"
FREQ = PF.OUT
COST = E.COST
SEED_CTRL, SEED_FAKE = 20261020, 20261021
REPS = 30
GAP_END = 5
HS = (20, 60, 120)
TAG = {"上季切點": 0, "同季切點": 1, "最低十分位": 9, "上季切點_20日": 20, "上季切點_120日": 120}
SEGNUM = {"段前": 9, "探索": 0, "確認": 1, "主全窗": 2}
TYP = PTH.TYP
CELLS = {"上季切點": ("上季切點_入選", 60, "判定格"), "同季切點": ("同季切點_入選", 60, "並報（⛔ 不擇優）"),
         "上季切點_20日": ("上季切點_入選", 20, "描述（⛔ 不判、不計 N）"), "上季切點_120日": ("上季切點_入選", 120, "描述（⛔ 不判、不計 N）"),
         "最低十分位": ("最低十分位", 60, "描述（⛔ 不判、不計 N；方向）")}
NAME = {"上季切點": "SUE 最高十分位（上季切點）上傳後抱 60 日（判定格）", "同季切點": "SUE 最高十分位（同季切點）抱 60 日（並報）",
        "上季切點_20日": "上季切點、抱 20 日（描述）", "上季切點_120日": "上季切點、抱 120 日（描述）", "最低十分位": "SUE 最低十分位抱 60 日（描述、空方不可做）",
        "營收已先好": "判定格中該季三個月營收年增都 ＞ 0（描述）", "沒先好": "判定格中營收沒先好（描述）",
        "沒先好_有月≤0": "沒先好：三個月都已公布但有月 ≤ 0（描述）", "沒先好_資料不全": "沒先好：有月缺／未公布（描述）"}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


pct = PTH.pct


# ═════════════ 逐股 ═════════════
def stock_job(sid):
    s_, r = PF.stock_job(sid)                                 # 閘、壞根日、有效 K 棒（頻率表同一支）
    if r is None:
        return sid, None
    W = PF._G["主"]; cal = W["cal"]; n0 = W["n0"]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    idx = B["idx"].astype(np.int64); nb = len(idx)
    o = np.asarray(B["o"], float); c = np.asarray(B["c"], float)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    assert np.array_equal(np.flatnonzero(r["badpos"]), idx[bad])
    delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
    ke = np.arange(nb)
    with np.errstate(invalid="ignore"):
        okp = np.isfinite(o) & (o > 0)
    out = {"gate": r["gate"], "bar": r["bar"], "badpos": r["badpos"]}
    for H in HS:
        eb, px, typ = PTH.fixed_exit(ke, idx + H - 1, idx, c, bad, n0, delisted)
        Rr = np.full(n0, np.nan, np.float64); Ty = np.zeros(n0, np.int8); Sd = np.full(n0, -1, np.int32)
        with np.errstate(invalid="ignore", divide="ignore"):
            rr = px / o - 1.0
        rr[~okp] = np.nan
        Rr[idx] = rr; Ty[idx] = np.where(okp, typ, 0); Sd[idx] = np.where(eb >= 0, idx[np.maximum(eb, 0)], -1)
        out[f"R{H}"] = Rr; out[f"T{H}"] = Ty; out[f"S{H}"] = Sd
        if H == 60:
            Mt = np.full(n0, np.nan); Mt[idx] = np.where(typ == 5, c[nb - 1] / o - 1.0, np.nan); out["M60"] = Mt
    cf = np.full(n0, np.nan); cf[idx] = c
    out["cff"] = pd.Series(cf).ffill().to_numpy()
    return sid, out


# ═════════════ 事件重算（F1；頻率表 main 207～273 行逐行照抄）═════════════
def detect(W, res, ok):
    cal = W["cal"]; n0 = W["n0"]
    F, finfo = PF.load_eps(ok)
    UP, USRC, RS, uinfo = PF.load_upload()
    q0, q1 = int(F["qi"].min()), int(F["qi"].max()); nq = q1 - q0 + 1
    six = {s: k for k, s in enumerate(ok)}; S = len(ok)
    EPS = np.full((S, nq), np.nan); HAS = np.zeros((S, nq), bool)
    for s, qi, e in zip(F["stock_id"], F["qi"], F["eps"]):
        EPS[six[s], qi - q0] = e; HAS[six[s], qi - q0] = True
    D4 = np.full((S, nq), np.nan); D4[:, 4:] = EPS[:, 4:] - EPS[:, :-4]
    SUE = np.full((S, nq), np.nan)
    for j in range(nq):
        for i in np.flatnonzero(HAS[:, j]):
            if not np.isfinite(D4[i, j]):
                continue
            if j - PF.NPREV < 4:
                continue
            h = D4[i, j - PF.NPREV:j]
            if not np.isfinite(h).all():
                continue
            sd = float(np.std(h, ddof=1))
            if not sd > 0:
                continue
            SUE[i, j] = D4[i, j] / sd
    OKS = np.isfinite(SUE)
    UPD = np.full((S, nq), np.datetime64("NaT"), "datetime64[ns]"); EP = np.full((S, nq), -1, np.int64)
    for i, s in enumerate(ok):
        for j in range(nq):
            v = UP.get((s, q0 + j))
            if v is not None:
                UPD[i, j] = np.datetime64(v)
                if v.normalize() >= cal[0] - pd.Timedelta(days=7):
                    EP[i, j] = int(cal.searchsorted(v.normalize(), side="right"))
    HASTS = ~np.isnat(UPD)
    CUT = {"上季切點": np.full(nq, np.nan), "同季切點": np.full(nq, np.nan)}; CUTB = np.full(nq, np.nan)
    for j in range(nq):
        v = SUE[OKS[:, j], j]
        if len(v):
            CUT["同季切點"][j] = np.quantile(v, PF.TOPQ); CUTB[j] = np.quantile(v, PF.BOTQ)
        if j >= 1:
            v1 = SUE[OKS[:, j - 1], j - 1]
            if len(v1):
                CUT["上季切點"][j] = np.quantile(v1, PF.TOPQ)
    with np.errstate(invalid="ignore"):
        TOP = {arm: OKS & HASTS & (SUE >= CUT[arm][None, :]) for arm in PF.ARMS}
        BOT = OKS & HASTS & (SUE <= CUTB[None, :])
    TRD = W["TRD"]; O = W["O"]; UPL = W["UPL"]; ixw = W["ix"]

    def est(i, j):
        e = int(EP[i, j]); s = ok[i]
        if e < 0 or e >= n0:
            return PF.E_TAIL
        r = res[s]
        if not r["gate"][e]:
            return PF.E_GATE
        w = ixw[s]
        if not (r["bar"][e] and TRD[w][e] and np.isfinite(O[w][e]) and O[w][e] > 0):
            return PF.E_NOTRD
        if UPL[w][e]:
            return PF.E_UPL
        return PF.E_KEEP
    ST = np.full((S, nq), "", object)
    for i, j in zip(*np.nonzero(HASTS)):
        ST[i, j] = est(i, j)
    ANY = TOP["上季切點"] | TOP["同季切點"] | BOT
    rows = []
    for i, j in zip(*np.nonzero(ANY)):
        e = int(EP[i, j])
        rows.append({"sid": ok[i], "季": PF.qname(q0 + j), "SUE": SUE[i, j], "e": str(cal[e].date()) if 0 <= e < n0 else "",
                     "上季切點_入選": bool(TOP["上季切點"][i, j]), "同季切點_入選": bool(TOP["同季切點"][i, j]), "最低十分位": bool(BOT[i, j]), "st": ST[i, j]})
    buf = io.StringIO(); pd.DataFrame(rows).to_csv(buf, index=False); buf.seek(0)
    mine = pd.read_csv(buf, dtype=str, keep_default_na=False)
    return {"q0": q0, "nq": nq, "SUE": SUE, "OKS": OKS, "UPD": UPD, "EP": EP, "HASTS": HASTS, "TOP": TOP, "BOT": BOT, "ST": ST, "mine": mine,
            "finfo": finfo, "uinfo": uinfo}


def selftest():
    msgs = []
    x = np.random.default_rng(3).normal(0, 1, 400); k = np.random.default_rng(4).integers(0, 30, 400)
    d = UO.diff_stats(x, k, x, k)
    assert abs(d["差(D2−A)"]) < 1e-15 and d["se"] < 1e-15
    msgs.append("F1' 兩組相同 ⇒ 差 0、SE 0（diff_stats）")
    # 60 日出場：e 算第 1 天、e＋59 收盤（無壞根、全有成交）
    idx = np.arange(100); c = np.arange(100, 200, dtype=float); bad = np.zeros(100, bool)
    eb, px, ty = PTH.fixed_exit(np.array([10]), np.array([10 + 60 - 1]), idx, c, bad, 100, False)
    assert eb[0] == 69 and px[0] == c[69] and ty[0] == 1
    bad[30] = True
    eb, px, ty = PTH.fixed_exit(np.array([10]), np.array([69]), idx, c, bad, 100, False)
    assert eb[0] == 29 and ty[0] == 3
    msgs.append("F2' 60 日 ＝ e＋59 收盤；持有中壞根 ⇒ 前一根收盤強制（researchPTH.fixed_exit，F1 已對逐根迴圈）")
    for m in msgs:
        log("✅ " + m)
    return msgs


def sentence(cell, st, tail):
    nm = NAME.get(cell, cell)
    rs = st["結果"]
    if rs == "樣本不足以分辨":
        s = f"{nm}：樣本不足以分辨（n_eff＝{st.get('n_eff', 0)}）"
    else:
        pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(st["n_eff"]) if st.get("出口") == "出口②" else ""
        if rs == "結果①":
            s = "{}{}：比同時隨便買分不出（X̄ {}，95% CI {} ～ {}）".format(pre, nm, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
        else:
            x2 = st.get("假訊號_x2", 0) or 0
            warn = "⚠ 隨機挑公司也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
            s = "{}{}{}：比同時隨便買{} {}（95% CI {} ～ {}）".format(warn, pre, nm, "多" if rs == "結果②" else "少", pct(abs(st["X̄"]))[1:],
                                                             pct(st["lo"]), pct(st["hi"]))
    return s + "｜" + "；".join(tail)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(os.path.join(OUT, "events"), exist_ok=True)
    reg = PF.reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜本體開跑 {now_tpe()}")
    PF.ensure_archive()
    fx = selftest()
    W = AT.load_world("主"); cal = W["cal"]; n0 = W["n0"]
    PF._G["主"] = W
    res = {}
    with Pool(a.procs) as pool:
        for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, W["sids"], chunksize=8)):
            res[sid] = r
            if (k_ + 1) % 500 == 0:
                log(f"  … {k_ + 1}／{len(W['sids'])}｜{time.time() - t0:.0f}s")
    ok = sorted(s for s, r in res.items() if r is not None)
    log(f"[主] 逐股完 {len(ok)} 檔｜{time.time() - t0:.0f}s")
    Dt = detect(W, res, ok)
    ref = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype=str, keep_default_na=False)
    cols = list(Dt["mine"].columns)
    same = Dt["mine"].shape == ref[cols].shape and (Dt["mine"].values == ref[cols].values).all()
    if not same:
        raise SystemExit(f"⛔ 重算事件 ≠ 已提交頻率表事件檔（{Dt['mine'].shape} vs {ref.shape}）⇒ 中止（未算任何報酬）")
    log(f"[查核1] 重算事件與已提交頻率表事件檔逐列逐欄相同（{len(ref):,} 列；欄 {cols}）")
    fj = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    if a.dry:
        log("[乾跑] 完（未算任何報酬）")
        return
    S = len(ok); six = {s: k for k, s in enumerate(ok)}; q0 = Dt["q0"]; nq = Dt["nq"]
    EPm, ST, TOP, BOT, OKS, HASTS, UPD = Dt["EP"], Dt["ST"], Dt["TOP"], Dt["BOT"], Dt["OKS"], Dt["HASTS"], Dt["UPD"]
    # 矩陣（n0 × S）
    Rm = {H: np.full((n0, S), np.nan) for H in HS}; Tm = {H: np.zeros((n0, S), np.int8) for H in HS}; Sm = {H: np.full((n0, S), -1, np.int32) for H in HS}
    M60 = np.full((n0, S), np.nan); CFF = np.full((n0, S), np.nan); BADC = np.zeros((n0, S), bool); BASE = np.zeros((n0, S), bool)
    TRD = W["TRD"]; O = W["O"]; UPL = W["UPL"]
    for s in ok:
        i = six[s]; r = res[s]; w = W["ix"][s]
        for H in HS:
            Rm[H][:, i] = r[f"R{H}"]; Tm[H][:, i] = r[f"T{H}"]; Sm[H][:, i] = r[f"S{H}"]
        M60[:, i] = r["M60"]; CFF[:, i] = r["cff"]; BADC[:, i] = r["badpos"]
        with np.errstate(invalid="ignore"):
            BASE[:, i] = r["gate"] & r["bar"] & TRD[w][:n0] & np.isfinite(O[w][:n0]) & (np.nan_to_num(O[w][:n0]) > 0) & ~UPL[w][:n0]
    del res
    J = {"性質": "PEAD seq1 事件層正式跑（判定格 上季切點；探索判定、確認確認、主全窗參考、段前描述；早年不做）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq388 發號 N_前段 ＋1；seq390 核准照登錄（上季切點）開跑、同季並報",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE}, "Bonferroni": {"族N": UO.N_FAM, "z": UO.Z95}, "fixture": fx,
         "資料": {"main": PF.MAIN_SHA, "fin_hist": Dt["finfo"], "filing_dates": Dt["uinfo"], "主世界": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "股數": S},
         "讀法_頻率表": PF.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "時點": {"本體開跑": now_tpe(), "第一次讀報酬": now_tpe()}}
    log(f"[報酬] 第一次讀報酬 {J['時點']['第一次讀報酬']}")
    # 查核2：保留事件必有 R60 或資料尾
    keepm = TOP["上季切點"] & (ST == PF.E_KEEP)
    ii, jj = np.nonzero(keepm)
    miss = int((Tm[60][EPm[ii, jj], ii] == 0).sum())
    assert miss == 0, f"⛔ 保留事件 {miss} 筆無進場價"
    log("[查核2] 判定格保留事件全部有進場還原開盤、有出場種類")
    crc = {s: zlib.crc32(s.encode("utf-8")) for s in ok}
    dates = np.array([str(d.date()) for d in cal]); moni = np.asarray(cal.year * 12 + cal.month)
    rv = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str}, usecols=["sid", "季", "營收分組", "EPS季增(seq329式)", "上傳時戳"])
    RVG = {(s, q): g for s, q, g in zip(rv["sid"], rv["季"], rv["營收分組"])}
    UTS = {(s, q): t for s, q, t in zip(rv["sid"], rv["季"], rv["上傳時戳"])}
    # 原始入選（任何狀態）在 e 的矩陣
    def raw_at(mask):
        M = np.zeros((n0, S), bool)
        i_, j_ = np.nonzero(mask)
        e_ = EPm[i_, j_]; g = (e_ >= 0) & (e_ < n0)
        M[e_[g], i_[g]] = True
        return M
    RAW = {"上季切點_入選": raw_at(TOP["上季切點"]), "同季切點_入選": raw_at(TOP["同季切點"]), "最低十分位": raw_at(BOT)}
    POOL = {H: BASE & np.isfinite(Rm[H]) for H in HS}
    MASK = {"上季切點_入選": TOP["上季切點"], "同季切點_入選": TOP["同季切點"], "最低十分位": BOT}
    TR = {}
    for cname, (src, H, role) in CELLS.items():
        evm = MASK[src] & (ST == PF.E_KEEP)
        i_, j_ = np.nonzero(evm); e_ = EPm[i_, j_]
        o_ = np.lexsort((j_, i_, e_)); i_, j_, e_ = i_[o_], j_[o_], e_[o_]          # e、sid（ok 已排序）、季
        smp = UO.Sampler(POOL[H], RAW[src])
        Rr = Rm[H][e_, i_]; ty = Tm[H][e_, i_]; sd = Sm[H][e_, i_].astype(np.int64)
        cm = np.full(len(i_), np.nan); cn = np.zeros(len(i_), np.int64); cids = []; cidx = []
        for q in range(len(i_)):
            i, e = int(i_[q]), int(e_[q])
            cs = smp.draw(e, i, [SEED_CTRL, TAG[cname], e, crc[ok[i]]])
            cn[q] = len(cs); cidx.append(cs)
            if len(cs):
                cm[q] = float(Rm[H][e, cs].mean())
            cids.append(";".join(ok[x] for x in cs) if cname == "上季切點" else "")
        Xv = Rr - cm
        qn = [PF.qname(q0 + j) for j in j_]
        fr = pd.DataFrame({"sid": [ok[x] for x in i_], "季": qn, "SUE": Dt["SUE"][i_, j_], "上傳時戳": [UTS.get((ok[x], q), "") for x, q in zip(i_, qn)],
                           "進場日": dates[e_], "出場日": [dates[x] if x >= 0 else "" for x in sd], "出場種類": [TYP[int(x)] for x in ty],
                           "持有天數": np.where(sd >= 0, sd - e_, -1), "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": M60[e_, i_] if H == 60 else np.nan,
                           "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids,
                           "營收分組": [RVG.get((ok[x], q), "") for x, q in zip(i_, qn)]})
        TR[cname] = {"fr": fr, "i": i_, "j": j_, "e": e_, "mon": moni[e_], "X": Xv, "R": Rr, "ty": ty, "H": np.where(sd >= 0, sd - e_, -1), "cm": cm,
                     "cidx": cidx, "sd": sd}
        log(f"  {cname}：事件 {len(i_)}｜資料尾未出場 {int((ty == 5).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
    # 反應（描述）、持有重疊
    A0 = TR["上季切點"]
    CB = np.vstack([np.zeros((1, S), np.int32), np.cumsum(BADC, axis=0, dtype=np.int32)])     # CB[p] ＝ bad[0..p−1]
    react = np.full(len(A0["e"]), np.nan); creact = np.full(len(A0["e"]), np.nan)
    for q, (i, e, cs) in enumerate(zip(A0["i"], A0["e"], A0["cidx"])):
        u = pd.Timestamp(A0["fr"]["上傳時戳"].iloc[q]).normalize()
        pb = int(cal.searchsorted(u, side="left")) - 1
        if pb < 0:
            continue
        def rr_(k):
            if CB[e + 1, k] - CB[pb + 1, k] > 0 or not (np.isfinite(CFF[e, k]) and np.isfinite(CFF[pb, k])):
                return np.nan
            return CFF[e, k] / CFF[pb, k] - 1.0
        react[q] = rr_(int(i))
        v = [rr_(int(k)) for k in cs]; v = [x for x in v if np.isfinite(x)]
        creact[q] = float(np.mean(v)) if v else np.nan
    A0["fr"]["反應_上傳日前收到e收"] = react; A0["fr"]["反應_對照平均"] = creact; A0["react"] = react - creact
    ovl = 0
    last = {}
    for i, e, sd in sorted(zip(A0["i"], A0["e"], A0["sd"]), key=lambda z: (z[0], z[1])):
        if i in last and last[i] >= 0 and e <= last[i]:
            ovl += 1
        last[i] = sd
    # 營收分組子集
    grp = A0["fr"]["營收分組"].to_numpy()
    for gname, m in (("營收已先好", grp == "營收已先好"), ("沒先好", grp != "營收已先好"), ("沒先好_有月≤0", grp == "沒先好_有月≤0"),
                     ("沒先好_資料不全", grp == "沒先好_資料不全")):
        TR[gname] = {**{k: (v[m] if isinstance(v, np.ndarray) else v) for k, v in A0.items() if k not in ("fr", "cidx")}, "fr": A0["fr"][m]}
    for cname in CELLS:
        TR[cname]["fr"].to_csv(os.path.join(OUT, "events", f"trades_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
    MAIN = []; BY = []; FK = []; SEGJ = {}
    rngq = fj["上季切點_最高十分位占可算比例(每季)"]
    sel_rng = f"{rngq['最小'] * 100:.0f}%～{rngq['最大'] * 100:.0f}%"
    ovp = [fj["段"][sg]["上季切點"]["比例_與EPS季增重疊"] for sg in ("探索", "確認")]
    ov_rng = f"{min(ovp) * 100:.0f}～{max(ovp) * 100:.0f}%"
    neps = fj["剔除合計(全部季)"]["EPS缺"]
    TAIL = [f"SUE 十分位切點用上一季分布（本線定；每季實際入選 {sel_rng}）", "台股有月營收先揭露，漂移可能被提前吃掉", "早年段無上傳時戳不做",
            f"半年報公司 Q2／Q4 單季 EPS 算不出而剔除（EPS 缺共 {neps:,} 股季）", f"與單季 EPS 季增重疊 {ov_rng}（該件 seq329 不合格）", "單筆層通過 ≠ 組合會贏 0050"]
    for sg, (x_, y_) in PF.SEGS.items():
        p0 = int(cal.searchsorted(pd.Timestamp(x_)))
        p1 = n0 - 1 if y_ is None else int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1
        yrs = (cal[p1] - cal[p0]).days / 365.25
        segj = {"期間": f"{cal[p0].date()}～{cal[p1].date()}"}
        for cname, d_ in TR.items():
            inseg = (d_["e"] >= p0) & (d_["e"] <= p1)
            okx = inseg & np.isfinite(d_["X"])
            st = UO.x_stats(d_["X"][okx], d_["mon"][okx])
            st["t"] = float(st["X̄"] / st["se"]) if st.get("se") else None
            st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == 5)).sum()),
                       "無對照剔除": int((inseg & np.isfinite(d_["R"]) & ~np.isfinite(d_["X"])).sum()), "相異檔數": int(len(set(d_["i"][okx].tolist()))),
                       "有事件財報季": int(len(set(d_["j"][okx].tolist()))), "每年事件數": round(int(okx.sum()) / yrs, 1),
                       "R̄": float(d_["R"][okx].mean()) if okx.any() else None, "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None})
            st.update(PTH.trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
            yr = np.asarray(cal.year)[d_["e"][okx]]
            st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean())} for y in sorted(set(yr.tolist()))}
            for y, q in st["逐年"].items():
                BY.append({"段": sg, "格": cname, "年": y, **q})
            if cname == "上季切點" and okx.any():
                rr = d_["react"][okx]; m_ = np.isfinite(rr)
                st["反應(描述)"] = {"n": int(m_.sum()), "事件平均": float(np.nanmean(d_["fr"]["反應_上傳日前收到e收"].to_numpy()[okx])),
                                  "對照平均": float(np.nanmean(d_["fr"]["反應_對照平均"].to_numpy()[okx])),
                                  **({k: v for k, v in UO.x_stats(rr[m_], d_["mon"][okx][m_]).items() if k in ("X̄", "lo", "hi", "n_eff")} if m_.any() else {})}
                # 假訊號
                POOLq = POOL[60]
                smpf = UO.Sampler(POOLq, RAW["上季切點_入選"])
                m0 = int(moni[p0])
                acc = np.zeros((REPS, 200, 2))
                fq = []
                for j in range(nq):
                    cand = np.flatnonzero(OKS[:, j] & HASTS[:, j] & (ST[:, j] == PF.E_KEEP))
                    if len(cand) == 0:
                        continue
                    e_ = EPm[cand, j]
                    g = (e_ >= p0) & (e_ <= p1)
                    cand = cand[g]; e_ = e_[g]
                    g2 = np.isfinite(Rm[60][e_, cand])
                    cand = cand[g2]; e_ = e_[g2]
                    if len(cand):
                        fq.append((j, cand, e_))
                for r_ in range(REPS):
                    for j, cand, e_ in fq:
                        k = int(math.ceil(0.1 * len(cand)))
                        pk = np.sort(np.random.default_rng([SEED_FAKE + r_, q0 + j, SEGNUM[sg]]).choice(len(cand), size=k, replace=False))
                        for q in pk:
                            i, e = int(cand[q]), int(e_[q])
                            cs = smpf.draw(e, i, [SEED_CTRL, 1000 + r_, e, crc[ok[i]]])
                            if len(cs) == 0:
                                continue
                            cl = int(moni[e]) - m0
                            acc[r_, cl, 0] += 1.0; acc[r_, cl, 1] += Rm[60][e, i] - Rm[60][e, cs].mean()
                res_ = [UO.agg_eval(acc[r_]) for r_ in range(REPS)]
                st["假訊號_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                st["假訊號_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                st["假訊號_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                st["假訊號_每次筆數中位"] = float(np.median([q["n"] for q in res_ if q])) if any(res_) else None
                for r_, q in enumerate(res_):
                    FK.append({"段": sg, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st["假訊號_x2"] <= 1 and st.get("X̄−成本", -1) > 0
                                      and st.get("逐月中位與平均同號", False))
                st["seq322各條"] = {"結果②": st["結果"] == "結果②", "Bonferroni下界>0": bool(st.get("bonf_lo", -1) > 0),
                                  "假訊號x≤1": bool(st["假訊號_x2"] <= 1), "X̄−0.585%>0": bool(st.get("X̄−成本", -1) > 0),
                                  "逐月中位與平均同號": bool(st.get("逐月中位與平均同號", False)),
                                  "seq329§二 |t|≥1.96(族N=1)": bool(st.get("t") is not None and abs(st["t"]) >= 1.96)}
                st["同檔持有重疊件數(全期)"] = ovl
            def dst(c1, c2):
                a1, a2 = TR[c1], TR[c2]
                m1 = (a1["e"] >= p0) & (a1["e"] <= p1) & np.isfinite(a1["X"]); m2 = (a2["e"] >= p0) & (a2["e"] <= p1) & np.isfinite(a2["X"])
                return UO.diff_stats(a1["X"][m1], a1["mon"][m1], a2["X"][m2], a2["mon"][m2])
            if cname == "最低十分位":
                st["最高減最低(上季切點−最低)"] = dst("最低十分位", "上季切點")
            if cname == "營收已先好":
                st["已先好−沒先好"] = dst("沒先好", "營收已先好")
            if cname == "同季切點":
                st["同季−上季"] = dst("上季切點", "同季切點")
            role = CELLS[cname][2] if cname in CELLS else "描述（⛔ 不判、不計 N）"
            if cname == "上季切點":
                role = "判定格｜" + {"探索": "判定段", "確認": "確認段", "主全窗": "參考", "段前": "段前描述（n_eff 不足）"}[sg]
            st["身分"] = role
            st["句子"] = sentence(cname, st, TAIL if cname in ("上季切點", "同季切點") else ["描述（⛔ 不判）"])
            segj[cname] = st
            MAIN.append({"段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": segj["期間"],
                         **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")}, "句子": st["句子"]})
            log(f"  [{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                + (f"｜假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname == "上季切點" else "") + f"｜{time.time() - t0:.0f}s")
        SEGJ[sg] = segj
    J["段"] = SEGJ
    jd = {}
    for sg in ("探索", "確認", "主全窗", "段前"):
        for cname in ("上季切點", "同季切點"):
            st = SEGJ[sg][cname]
            jd[f"{sg}_{cname}"] = {k: st.get(k) for k in ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "t", "中位", "X̄−成本", "逐月平均之中位",
                                                       "假訊號_x2", "過seq322門檻", "勝率", "平均賺賠比", "R̄", "對照R̄", "資料尾未出場", "句子")}
    J["判定"] = jd
    J["引自頻率表"] = {"上季切點入選比例(每季)": rngq, "剔除合計(全部季)": fj["剔除合計(全部季)"], "每季SUE可算公司數": fj["每季SUE可算公司數"],
                   "與EPS季增重疊": {sg: fj["段"][sg]["上季切點"]["比例_與EPS季增重疊"] for sg in ("探索", "確認", "主全窗")},
                   "門檻微前視": {sg: {k: v for k, v in fj["段"][sg]["上季切點"].items() if k.startswith("門檻微前視")} for sg in ("探索", "確認", "主全窗")},
                   "seq377等價": {sg: fj["段"][sg]["seq377等價_上季vs同季切點"] for sg in ("探索", "確認")}}
    r1 = [SEGJ[sg]["上季切點"]["結果"] for sg in ("探索", "確認")]
    J["先驗"] = {"①兩段皆①或一段②": {"探索/確認": r1, "中": sorted(r1) in (["結果①", "結果①"], ["結果①", "結果②"])},
                "②最高減最低X>0": {sg: {"差": SEGJ[sg]["最低十分位"]["最高減最低(上季切點−最低)"].get("差(D2−A)"),
                                      "CI": [SEGJ[sg]["最低十分位"]["最高減最低(上季切點−最低)"].get("lo"), SEGJ[sg]["最低十分位"]["最高減最低(上季切點−最低)"].get("hi")],
                                      "中": bool((SEGJ[sg]["最低十分位"]["最高減最低(上季切點−最低)"].get("差(D2−A)") or -1) > 0)} for sg in ("探索", "確認", "主全窗")},
                "③營收已先好X低於沒先好": {sg: {"已先好X̄": SEGJ[sg]["營收已先好"].get("X̄"), "沒先好X̄": SEGJ[sg]["沒先好"].get("X̄"),
                                           "差CI": [SEGJ[sg]["營收已先好"]["已先好−沒先好"].get("lo"), SEGJ[sg]["營收已先好"]["已先好−沒先好"].get("hi")],
                                           "中": bool(SEGJ[sg]["營收已先好"].get("X̄", 0) < SEGJ[sg]["沒先好"].get("X̄", 0))} for sg in ("探索", "確認", "主全窗")},
                "④每季可算SUE≥1000": {"頻率表": fj["每季SUE可算公司數"], "中": fj["每季SUE可算公司數"]["最少"] >= 1000}}
    J["N"] = {"本件判定格": 1, "並報／描述": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(OUT, "PEAD_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(OUT, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "PEAD.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"[先驗] ①{J['先驗']['①兩段皆①或一段②']['中']} ②{ {k: v['中'] for k, v in J['先驗']['②最高減最低X>0'].items()} } "
        f"③{ {k: v['中'] for k, v in J['先驗']['③營收已先好X低於沒先好'].items()} } ④{J['先驗']['④每季可算SUE≥1000']['中']}")
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

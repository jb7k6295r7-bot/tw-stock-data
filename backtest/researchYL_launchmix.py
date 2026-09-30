# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 搭配「低檔發動」（使用者問：「用低檔發動搭配營量、營飆呢？」；參考，⛔ 不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_launchmix [--check | --page]

═══ 讀法（寫死於 2026-09-30 21:53（台北），在算任何數字之前）═══
 M1 本體與閘（同 researchYL_flowexit F1）：ctx ＝ researchT1fix.build_ctx(True)；營量 v1 ＝ simulate_mtm(sig13, "H60", 20, default_rng(7000), pick relvol, queue 0, log=[], stop_force)；
    營飆 v1 ＝ simulate_mtm(sig, "H120", 10, default_rng(1000＋r), stop_force)，r ＝ 0～199
    閘：A 的主窗年化、回落 ＝ resultsT1fix/seeds.csv.gz（c13｜t1｜r0；c1｜t1｜r0～199）repr 逐位元；
       F3 的排序管線在「低檔旗標全 0」時權益 ＝ A 逐位元（營量 r0、營飆 r0～4）⇒ 驗排序改法本身不改結果
 M2 低檔發動（照 researchSurge6_launch／launch10／launchcombo，飆股資料 s5work、stitch 價格、飆股日曆，依日期對到引擎日曆）：
    pos(d) ＝ (c[d] − 最低) ÷ (最高 − 最低)，含 d 的最近 250 根有效 K 棒還原收盤（不足 250 根或最高 ＝ 最低 ⇒ 沒值）
    母體日（剛從低檔發動）＝ 有效 K 棒 d：[d−59, d] 有效 K 棒內最低收盤那根 j（同價取最近）pos(j) ≤ 0.4 且 c[d] ÷ c[j] − 1 ∈ [5%, 30%]
    logit 分數 ＝ launchcombo/logit_coef.csv（探索段 2021–2023 訓練）× launchcombo 的 50 個條件 bits（~/s6work/launchcombo_bits.npy）；
    閘：本檔重算的母體日在 2021-01～2026-08 與 launchcombo rows_min 逐列相同；探索段母體日分數的 95 分位 ＝ logit.csv 探索 5% 門檻（差 ＜ 5e−4）
    ⚠ 模型用 2021–2023 的結果訓練 ⇒ 2021–2023 的分數是樣本內；2017–2020、2024–2026 是樣本外
 ① 過濾／排序（出場照正式 60／120 日；同一批候選訊號）：
    每列候選（e ＝ entry_pos）：本輪起漲點 L ＝ anchor_before（researchYL_flowexit F2：引擎收盤、資料到 e−1、回落 30% 重錨）
    低檔旗標 ＝ pos(L) ≤ x，x ∈ {0.2, 0.4（主）, 0.6}（pos 沒值 ⇒ 不是低檔）；L 分數 ＝ [L, e−1] 內母體日 logit 分數最大值（沒有母體日 ⇒ 沒值）
    F1 只買低檔｜F2 排除低檔（對照）｜F3 低檔優先（營量：鍵 ＝ 旗標 × 1e9 ＋ relvol；營飆：pick_tie＝"rng"，同一次抽籤排列後依旗標穩定排序）｜
    F4 分數優先（營量：有分數 ⇒ 1e9 ＋ 分數，沒分數 ⇒ relvol；營飆：鍵 ＝ 分數、沒值排最後、同分照抽籤）
    報：年化、回落（營飆 200 顆中位、p10～p90、對 A 同顆差中位、贏 A 顆數比例）；逐筆：A 的實際交易依旗標分群，每筆淨報酬（g − 0.585%）平均、中位、勝率
 ② 資金混合：
    低檔 logit 策略 ＝ 母體日 d 且分數 ≥ 探索段 95 分位門檻（固定，只用 2021–2023）⇒ d 的下一個引擎交易日開盤進（entry ∈ 主窗）；不去重（仍符合的日子都是候選，引擎擋已持有）
      價格 ＝ stitch（D.DATA ＝ S5.ST）載到引擎日曆；有效 K 棒 ＝ 飆股 bar.npy ∧ 收盤有限；停止交易 ⇒ stop_force；沒有壞根截（stitch 已處理斷點，照實記）
      出場 ＝ 飆股流程（researchYL_flowexit.flow_one／finalize 同一套：起漲點錨在進場前一天、W1 賣 3 成、剩 7 成 W2／回落 30%、W1 前 40 天沒新高賣全部；未完 ⇒ T1）
      組合：simulate_mtm 10 槽、pick ＝ 分數（高者先、不抽籤），held_map 合成序列（同 flowexit F5；3 成先賣的錢留在部位裡）
    合併：兩條權益曲線每日再平衡到固定比例（⚠ 近似：不計再平衡成本，兩邊各自照自己的槽位跑）：r ＝ (1−w) r_正式 ＋ w r_低檔，w ∈ {0, 20%, 40%}
      營飆 ⇒ 200 顆各自混合後報中位、p10～p90
 分期：全部 ＝ 主窗 2017-03-02～2026-08-24；2021-01～2023-12；2024-01～2026-08-24（同一條權益曲線切窗）
 挑版本：① 的 F 版本、② 的比例若要選「最好的」，只用 2021–2023 年化（營飆取中位）選，2024–2026 照報、⛔ 不依它重選
 M3 查核（--check）：① 抽 50 列營量／營飆候選，逐日迴圈重算 L、pos(L)、[L, e−1] 母體日與分數最大值；② 抽 30 筆低檔策略實際交易，
    逐日迴圈重算訊號日是母體日且分數 ≥ 門檻、流程出場日與價（同 flowexit check 的迴圈寫法）；③ 一個比例的混合權益逐日迴圈重算年化 ⇒ 0 不同才算過；並附 M1、M2 的閘
 M4 接手紀錄（2026-09-30 23:10（台北），接手的子代理補；⚠ 前一個子代理已照 M1～M3 跑完一次主程式（22:10），接手者看過那次的彙總數字後才寫本段）：
    逐行讀過 M1～M3 的程式，判定可用、⛔ 讀法 M1～M3 一字不改；只修三處後整批重跑：
    ⓐ pick_versions 的鍵「其 2024–2026 年化」① 與 ② 重複，② 蓋掉 ① ⇒ 改名分開（只影響 meta 與網頁的「挑版本」段）
    ⓑ 逐筆的 A 交易報酬套停止交易強制出場（xpos ＞ L＋1 ⇒ g ＝ c[L] ÷ 買價 − 1，同 flowexit），原本直接用正式 g
    ⓒ 結論句（原本「待填」）依數字自動組；挑版本的規則仍是 M2 寫死的「只看 2021–2023」
    查核 ② 的 W1／W2 沿用主程式同一個建構（flowexit.surge_signals），驗的是錨、狀態機與價，⛔ 不是 W1／W2 本身（W1／W2 已由 flowexit 的查核逐根驗過）
輸出 backtest/resultsYL_launchmix/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR
from backtest import researchYL_flowexit as FE

TIME = "2026-09-30 21:53（台北）"
OUT = "backtest/resultsYL_launchmix"
LCDIR = "backtest/resultsSurge6/launchcombo"
BITS = os.path.expanduser("~/s6work/launchcombo_bits.npy")
COST = R.COST
THRS = (0.2, 0.4, 0.6)
FV = ["A"] + [f"{f}≤{x}" for x in (0.4, 0.2, 0.6) for f in ("F1", "F2", "F3")] + ["F4"]
FNAME = {"A": "A 正式", "F1": "F1 只買低檔發動", "F2": "F2 排除低檔發動", "F3": "F3 低檔發動優先", "F4": "F4 logit 分數優先"}
SEGS = FE.SEGS
STR = FE.STR
NYF = 200
WTS = (0.0, 0.2, 0.4)


# ═════════════ 低檔發動母體與分數（飆股資料）═════════════
def launch_arrays(cal_e, log):
    """⇒ 引擎日曆上的 POS、POP、SCORE（S × n_e）、uni、閘資訊。⚠ 切 D.DATA，結束切回快照。"""
    from backtest import researchSurge5 as S5
    from backtest import researchSurge6_launchcombo as LC
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str)
    D.DATA = S5.ST; cal_s = D.load_calendar(); n = len(cal_s); S = len(uni)
    bar = np.load(os.path.join(S5.WORK, "bar.npy")); BIT = np.load(BITS, mmap_mode="r")
    CF = pd.read_csv(os.path.join(LCDIR, "logit_coef.csv")); names = [c[3] for c in LC.candidates()]
    gate = {"logit 係數名 ＝ launchcombo 50 個條件（順序）": CF["特徵"].tolist()[1:] == names}
    w0 = float(CF["係數"].iloc[0]); w = CF["係數"].to_numpy(float)[1:]; K = len(w)
    POS = np.full((S, n), np.nan, np.float32); POP = np.zeros((S, n), bool); SC = np.full((S, n), np.nan)
    for s in range(S):
        st = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal_s)
        if st is None:
            continue
        c0 = st.df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c0) & bar[s]); m = len(idx)
        if m < 30:
            continue
        cb = c0[idx]; Sr = pd.Series(cb)
        mx = Sr.rolling(250, min_periods=250).max().to_numpy(); mn = Sr.rolling(250, min_periods=250).min().to_numpy()
        with np.errstate(invalid="ignore", divide="ignore"):
            p_ = (cb - mn) / (mx - mn)
        p_[~(mx > mn)] = np.nan; POS[s, idx] = p_
        arr = np.r_[np.full(59, np.inf), cb]; win = np.lib.stride_tricks.sliding_window_view(arr, 60)[:, ::-1]
        j = np.arange(m) - np.argmin(win, axis=1)
        g = cb / cb[j] - 1
        with np.errstate(invalid="ignore"):
            pp = np.isfinite(p_[j]) & (p_[j] <= 0.4) & (g >= 0.05) & (g <= 0.30)
        dd = idx[pp]; POP[s, dd] = True
        if len(dd):
            bb = np.asarray(BIT[s, dd], np.uint64)
            X = ((bb[:, None] >> np.arange(K, dtype=np.uint64)[None, :]) & np.uint64(1)).astype(np.float64)
            SC[s, dd] = np.c_[np.ones(len(dd)), X] @ np.r_[w0, w]
        if s % 500 == 0:
            log(f"[低檔發動] {s}/{S}")
    # 閘：母體列 ＝ launchcombo rows_min（2021-01～2026-08）；探索段 95 分位 ＝ logit.csv
    mon = np.array([d.year * 12 + d.month - 1 for d in cal_s])
    seg = np.full(n, -1); seg[(mon >= 2021 * 12) & (mon <= 2023 * 12 + 11)] = 0; seg[(mon >= 2024 * 12) & (mon <= 2026 * 12 + 7)] = 1
    RM = np.load(os.path.join(LCDIR, "rows_min.npz"))
    ss, dd = np.nonzero(POP & (seg >= 0)[None, :])
    mine = set(zip(ss.tolist(), dd.tolist())); ref = set(zip(RM["s"].astype(int).tolist(), RM["d"].astype(int).tolist()))
    gate["母體日 ＝ launchcombo rows_min（不同列數）"] = len(mine ^ ref)
    ex = SC[POP & (seg == 0)[None, :]]; thr = float(np.quantile(ex, 0.95))
    LG = pd.read_csv(os.path.join(LCDIR, "logit.csv")); ref_thr = float(LG[(LG["段"] == "探索") & (LG["前"] == "5%") & (~LG["去重"])]["分數門檻"].iloc[0])
    gate["探索段 95 分位 ＝ logit.csv 探索 5% 門檻（差 ＜ 5e−4）"] = bool(abs(thr - ref_thr) < 5e-4)
    # 對到引擎日曆
    gi = cal_s.get_indexer(cal_e); ok = gi >= 0
    POSe = np.full((S, len(cal_e)), np.nan, np.float32); POPe = np.zeros((S, len(cal_e)), bool); SCe = np.full((S, len(cal_e)), np.nan)
    POSe[:, ok] = POS[:, gi[ok]]; POPe[:, ok] = POP[:, gi[ok]]; SCe[:, ok] = SC[:, gi[ok]]
    lo, hi = cal_e[0], cal_e[-1]; inr = (cal_s >= lo) & (cal_s <= hi)
    info = {"門檻（探索段 95 分位）": thr, "logit.csv 門檻": ref_thr, "引擎日曆對不到的天數": int((~ok).sum()),
            "飆股日曆在引擎期間內、引擎日曆沒有的天數": int(inr.sum() - ok.sum()), "飆股母體檔數": S,
            "barS": bar}
    RR.use_snapshot()
    log(f"[低檔發動] 完成｜門檻 {thr:.5f}（檔 {ref_thr}）｜閘 {gate}")
    return uni, POSe, POPe, SCe, thr, gate, info


# ═════════════ ① 候選訊號標記 ═════════════
def tag_signals(ctx, sig, uni, POSe, POPe, SCe, n0):
    s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    rows = []
    for sid, e in zip(sig["sid"], sig["entry_pos"].astype(int)):
        c = np.asarray(ctx["closes"][sid], float)[:n0]
        L, nre = FE.anchor_before(c, e)
        s = s2i.get(sid)
        if s is None:
            rows.append((L, np.nan, np.nan, 0)); continue
        pl = float(POSe[s, L]); pm = POPe[s, L:e]
        sm = float(np.nanmax(SCe[s, L:e][pm])) if pm.any() else np.nan
        rows.append((L, pl, sm, int(pm.sum())))
    out = sig.copy()
    out["L"] = [r[0] for r in rows]; out["posL"] = [r[1] for r in rows]; out["L分數"] = [r[2] for r in rows]; out["L母體日數"] = [r[3] for r in rows]
    for x in THRS:
        with np.errstate(invalid="ignore"):
            out[f"低≤{x}"] = (out["posL"] <= x).astype(int)
    return out


def variant_sig(strat, sigT, v):
    """⇒ (sig, kw 覆寫)。"""
    if v == "A":
        return sigT, {}
    if v == "F4":
        sc = sigT["L分數"].to_numpy(float)
        if strat == "營量 v1":
            return sigT.assign(pk=np.where(np.isfinite(sc), 1e9 + sc, sigT["relvol"].to_numpy(float))), {"pick": "pk"}
        return sigT.assign(pk=sc), {"pick": "pk", "pick_tie": "rng"}
    f, x = v.split("≤"); fl = sigT[f"低≤{x}"].to_numpy(int)
    if f == "F1":
        return sigT[fl == 1], {}
    if f == "F2":
        return sigT[fl == 0], {}
    if strat == "營量 v1":
        return sigT.assign(pk=fl * 1e9 + sigT["relvol"].to_numpy(float)), {"pick": "pk"}
    return sigT.assign(pk=fl.astype(float)), {"pick": "pk", "pick_tie": "rng"}


def run_engine(ctx, strat, sig, r, SF, kw=None, audit=True, **over):
    cf = STR[strat]; au = [] if audit else None
    base = dict(log=[], d_max=None, pick="relvol", queue_days=0) if strat == "營量 v1" else {}
    base.update(kw or {})
    seed = (RR.P1_SEED0 if strat == "營量 v1" else 1000) + r
    o = R.simulate_mtm(sig, cf["rule"], cf["N"], np.random.default_rng(seed), over.get("closes", ctx["closes"]), over.get("opens", ctx["opens"]), ctx["ncal"],
                       return_equity=True, stop_force=SF, audit=au, **base)
    return o, au


# ═════════════ ② 低檔 logit 策略 ═════════════
class LazySc(dict):
    """鍵 ＝ 「代號#進場位置」⇒ 用到才算合成收盤（同 flowexit.finalize 的式子）。"""

    def __init__(self, base, spec, NP):
        super().__init__(base); self.spec = spec; self.NP = NP; self.tt = np.arange(NP)

    def __missing__(self, k):
        parts, cc = self.spec[k]
        Sc = np.zeros(self.NP)
        for wi, p in zip((FE.W30, 1 - FE.W30), parts):
            Sc += wi * np.where(self.tt <= p[3], cc, p[2])
        self[k] = Sc
        return Sc


class LazyRef(dict):
    def __init__(self, base, hm):
        super().__init__(base); self.hm = hm

    def __missing__(self, k):
        return dict.__getitem__(self, self.hm[k])


def launch_strategy(ctx, uni, POPe, SCe, thr, info, log):
    from backtest import researchSurge5 as S5
    cal = ctx["cal"]; n0 = len(cal); NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    ss, dd = np.nonzero(POPe & (SCe >= thr))
    e_ = dd + 1; keep = (e_ >= w0) & (e_ <= w1) & (e_ <= n0 - 1)
    ss, dd, e_ = ss[keep], dd[keep], e_[keep]
    sids = sorted({uni.loc[s, "stock_id"] for s in set(ss.tolist())})
    D.DATA = S5.ST
    from backtest import researchSurge5 as S5b
    cal_s = D.load_calendar(); gi = cal_s.get_indexer(cal); barS = info["barS"]; s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    PX = {}
    for sid in sids:
        st = D.load_stock(sid, uni.loc[s2i[sid], "market"], cal)
        c0 = st.df["close"].to_numpy(float); o0 = st.df["open"].to_numpy(float)
        bs = np.zeros(n0, bool); bs[gi >= 0] = barS[s2i[sid], gi[gi >= 0]]
        bar = bs & np.isfinite(c0)
        c = pd.Series(c0).ffill().to_numpy()
        okop = bar & np.isfinite(o0) & (o0 > 0); nxt = np.full(n0 + 1, -1, np.int64)
        for p in range(n0 - 1, -1, -1):
            nxt[p] = p if okop[p] else nxt[p + 1]
        PX[sid] = {"c": c, "o": o0, "bar": bar, "cb": np.cumsum(bar), "nxt": nxt, "B": None, "c0": c0}
    RR.use_snapshot()
    SIGW, sinfo = FE.surge_signals(sids, cal, log)
    SF = R.stop_force_days({sid: np.isfinite(PX[sid]["c0"]) for sid in sids}, w1)
    rows = []; spec = {}; hm = {}
    for s, d, e in zip(ss.tolist(), dd.tolist(), e_.tolist()):
        sid = uni.loc[s, "stock_id"]; S_ = PX[sid]; c = S_["c"]
        if not np.isfinite(c[e]) or not np.isfinite(c[max(e - 1, 0)]):
            continue
        bp = float(S_["o"][e]) if np.isfinite(S_["o"][e]) and S_["o"][e] > 0 else float(c[e])
        W1, W2 = SIGW.get(sid, (np.zeros(n0, bool), np.zeros(n0, bool)))
        fr = FE.flow_one(S_, W1, W2, e, n0)
        parts = [FE.portion(k, x, S_, n0) for k, x in (fr["p30"], fr["p70"])]
        L = SF.get(sid)
        f = FE.finalize(parts, bp, e, S_, n0, None, L, NP); f.pop("Sc")
        key = f"{sid}#{e}"; hm[key] = sid; spec[key] = (parts, np.r_[c, c[-1]])
        rows.append({"sid": key, "usid": sid, "d": d, "entry_pos": e, "xpos_FL": f["xpos"], "g_FL": f["g"], "score": float(SCe[s, d]), "bp": bp,
                     "原因30": fr["原因30"], "原因70": fr["原因70"], "天": FE.W30 * f["天30"] + (1 - FE.W30) * f["天70"], "px30": f["px30"], "px70": f["px70"]})
    SG = pd.DataFrame(rows)
    closes = LazySc({sid: np.r_[PX[sid]["c"], PX[sid]["c"][-1]] for sid in sids}, spec, NP)
    opens = LazyRef({sid: np.r_[PX[sid]["o"], np.nan] for sid in sids}, hm)
    SFk = {k: SF[u] for k, u in hm.items() if u in SF}
    au = []
    o = R.simulate_mtm(SG, "FL", 10, np.random.default_rng(20260930), closes, opens, NP, return_equity=True, pick="score", audit=au, held_map=hm, stop_force=SFk)
    log(f"[低檔策略] 候選列 {len(SG):,}（{len(sids)} 檔）｜買進 {sum(a['side'] == 'buy' for a in au)}")
    return o, au, SG, {"候選列": int(len(SG)), "檔數": len(sids), "飆股訊號": {k: v for k, v in sinfo.items() if k != "不在飆股母體的檔"}}


def mix_eq(eA, oA, eL, oL, w):
    end = min(oA["end"], oL["end"]); n = len(eA)
    rA = np.zeros(n); rL = np.zeros(n)
    rA[1:end] = eA[1:end] / eA[:end - 1] - 1; rL[1:end] = eL[1:end] / eL[:end - 1] - 1
    eq = np.cumprod(1 + (1 - w) * rA + w * rL)
    return eq, min(oA["first"], oL["first"]), end


def metrics(eq, first, end, SEGP):
    out = {}
    for sg, (x, y) in SEGP.items():
        c_, m_, _ = RR.win_metrics(eq, first, end, x, y)
        out[f"{sg}_年化"] = float(c_); out[f"{sg}_回落"] = float(m_)
    return out


# ═════════════ 主程式 ═════════════
def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); w0, w1 = ctx["w0"], ctx["w1"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    SEGP = FE.seg_pos(cal, w0, w1)
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    uni, POSe, POPe, SCe, thr, gates, linfo = launch_arrays(cal, log)
    # ② 先跑低檔策略
    oL, auL, SGL, lmeta = launch_strategy(ctx, uni, POPe, SCe, thr, linfo, log)
    eL = np.asarray(oL["equity"], float)
    np.savez_compressed(os.path.join(OUT, "launch_equity.npz"), eq=eL, fe=np.array([oL["first"], oL["end"]]))
    SGL.to_csv(os.path.join(OUT, "launch_candidates.csv.gz"), index=False, float_format="%.10g")
    LROW = {"策略": "低檔 logit 策略（單獨）", **metrics(eL, oL["first"], oL["end"], SEGP), **FE.port_row(oL, auL, SEGP, w0, w1)[0]}
    buysL = pd.DataFrame([a for a in auL if a["side"] == "buy"])
    LT = SGL.set_index("sid").loc[buysL["sid"]].reset_index(); LT["報酬"] = FE.W30 * (LT["px30"] / LT["bp"] - 1) + (1 - FE.W30) * (LT["px70"] / LT["bp"] - 1) - COST
    LT["進場日"] = [str(cal[int(x)].date()) for x in LT["entry_pos"]]
    LT.to_csv(os.path.join(OUT, "launch_trades.csv.gz"), index=False, float_format="%.10g")
    log(f"[低檔策略] {LROW}｜{time.time() - T0:.0f}s")
    PR = []; MX = []; TG = {}; ATR = {}
    for strat, cf in STR.items():
        sigT = tag_signals(ctx, ctx[cf["sig"]], uni, POSe, POPe, SCe, n0)
        TG[strat] = sigT
        seeds = [0] if strat == "營量 v1" else list(range(NYF))
        buys = []
        for r in seeds:
            for v in FV:
                sg_, kw = variant_sig(strat, sigT, v)
                o, au = run_engine(ctx, strat, sg_, r, SF, kw)
                row, eq = FE.port_row(o, au, SEGP, w0, w1)
                PR.append({"策略": strat, "版本": v, "r": r, **row})
                if v == "A":
                    key = "c13" if strat == "營量 v1" else "c1"
                    rr = ref[(ref["key"] == key) & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0]
                    c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
                    gk = f"M1 {strat} A ＝ resultsT1fix（不同顆數）"; gates[gk] = gates.get(gk, 0) + int(not (repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"]))))
                    b = pd.DataFrame([a for a in au if a["side"] == "buy"])[["t", "sid"]]; b["r"] = r; buys.append(b)
                    if r < (1 if strat == "營量 v1" else 5):
                        z = sigT.assign(**{f"低≤{x}": 0 for x in THRS})
                        s0, kw0 = variant_sig(strat, z, "F3≤0.4")
                        o0, _ = run_engine(ctx, strat, s0, r, SF, kw0, audit=False)
                        gk = f"M1 {strat} F3 旗標全 0 ＝ A（不同顆數）"; gates[gk] = gates.get(gk, 0) + int(not np.array_equal(np.asarray(o0["equity"], float), eq))
                    for wv in WTS:
                        if wv == 0.0:
                            m = metrics(eq, o["first"], o["end"], SEGP)
                            eqm, fm, em = mix_eq(eq, o, eL, oL, 0.0)
                            mm = metrics(eqm, fm, em, SEGP)
                            gk = f"② {strat} 混合 w＝0 ≈ A（年化差 ＞ 1e−9 的格）"
                            gates[gk] = gates.get(gk, 0) + int(any(abs(mm[k] - m[k]) > 1e-9 for k in m))
                        else:
                            eqm, fm, em = mix_eq(eq, o, eL, oL, wv); m = metrics(eqm, fm, em, SEGP)
                        MX.append({"策略": strat, "比例": wv, "r": r, **m})
            if r % 25 == 0:
                log(f"[{strat}] r{r}｜{time.time() - T0:.0f}s")
        BY = pd.concat(buys, ignore_index=True); BY["sid"] = BY["sid"].astype(str); ATR[strat] = BY
    PR = pd.DataFrame(PR); PR.to_csv(os.path.join(OUT, "portfolio_seeds.csv.gz"), index=False, float_format="%.10g")
    MX = pd.DataFrame(MX); MX.to_csv(os.path.join(OUT, "mix_seeds.csv.gz"), index=False, float_format="%.10g")
    TGA = pd.concat([t.assign(策略=s) for s, t in TG.items()], ignore_index=True); TGA.to_csv(os.path.join(OUT, "signals_tag.csv.gz"), index=False, float_format="%.10g")
    # 逐筆：A 的交易依旗標
    P = []
    for strat, BY in ATR.items():
        T = TG[strat].set_index(["sid", "entry_pos"]); cf = STR[strat]
        m = T.loc[list(zip(BY["sid"], BY["t"].astype(int)))].reset_index(); m["r"] = BY["r"].to_numpy(); m["策略"] = strat
        g_ = m[f"g_{cf['rule']}"].to_numpy(float).copy(); xp_ = m[f"xpos_{cf['rule']}"].to_numpy(int)
        for i, (sd, ep) in enumerate(zip(m["sid"], m["entry_pos"].astype(int))):
            Ls = SF.get(sd)
            if Ls is not None and xp_[i] > Ls + 1:
                g_[i] = float(ctx["closes"][sd][Ls]) / FE.engine_ep(ctx, sd, ep) - 1.0
        m["停止交易"] = [int(SF.get(sd) is not None and xp_[i] > SF[sd] + 1) for i, sd in enumerate(m["sid"])]
        m["報酬"] = g_ - COST; m["進場日"] = [str(cal[int(x)].date()) for x in m["entry_pos"]]
        P.append(m)
    PT = pd.concat(P, ignore_index=True); PT.to_csv(os.path.join(OUT, "trades_A.csv.gz"), index=False, float_format="%.10g")
    SP = port_summary(PR); SP.to_csv(os.path.join(OUT, "summary_portfolio.csv"), index=False, float_format="%.6g")
    SM = mix_summary(MX, LROW); SM.to_csv(os.path.join(OUT, "summary_mix.csv"), index=False, float_format="%.6g")
    ST = trade_summary(PT, LT); ST.to_csv(os.path.join(OUT, "summary_per_trade.csv"), index=False, float_format="%.6g")
    PICK = pick_versions(SP, SM)
    META = {"讀法寫死": TIME, "閘": gates, "低檔發動": {k: v for k, v in linfo.items() if k != "barS"}, "低檔策略": lmeta, "低檔策略單獨": LROW,
            "SEGP": {k: [str(cal[a].date()), str(cal[b].date())] for k, (a, b) in SEGP.items()}, "只用 2021–2023 挑的版本": PICK,
            "候選列": {s: int(len(t)) for s, t in TG.items()}, "候選列低檔比例（≤0.4）": {s: float(t["低≤0.4"].mean()) for s, t in TG.items()},
            "候選列有 L 分數比例": {s: float(np.isfinite(t["L分數"]).mean()) for s, t in TG.items()}, "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(META, ensure_ascii=False, default=str)[:3000]}")
    if not all(v is True or v == 0 for v in gates.values()):
        raise SystemExit(f"⛔ 閘不過 {gates}")


def port_summary(PR):
    out = []
    for strat in STR:
        a = PR[(PR["策略"] == strat) & (PR["版本"] == "A")].sort_values("r")
        for v in FV:
            x = PR[(PR["策略"] == strat) & (PR["版本"] == v)].sort_values("r")
            for sg in SEGS:
                cg = x[f"{sg}_年化"].to_numpy(); md = x[f"{sg}_回落"].to_numpy(); dc = cg - a[f"{sg}_年化"].to_numpy(); dm = md - a[f"{sg}_回落"].to_numpy()
                out.append({"策略": strat, "版本": v, "段": sg, "顆數": len(x), "年化 中位": np.median(cg), "年化 p10": np.quantile(cg, .1), "年化 p90": np.quantile(cg, .9),
                            "回落 中位": np.median(md), "回落 p10": np.quantile(md, .1), "回落 p90": np.quantile(md, .9), "對A年化差 中位": np.median(dc), "對A回落差 中位": np.median(dm),
                            "年化贏A比例": float(np.mean(dc > 1e-12)) if v != "A" else np.nan, "買進筆 中位": float(x["買進筆"].median()), "平均持股 中位": float(x["平均持股"].median())})
    return pd.DataFrame(out)


def mix_summary(MX, LROW):
    out = []
    for strat in STR:
        a = MX[(MX["策略"] == strat) & (MX["比例"] == 0.0)].sort_values("r")
        for wv in WTS:
            x = MX[(MX["策略"] == strat) & (MX["比例"] == wv)].sort_values("r")
            for sg in SEGS:
                cg = x[f"{sg}_年化"].to_numpy(); md = x[f"{sg}_回落"].to_numpy(); dc = cg - a[f"{sg}_年化"].to_numpy()
                out.append({"策略": strat, "低檔比例": wv, "段": sg, "顆數": len(x), "年化 中位": np.median(cg), "年化 p10": np.quantile(cg, .1), "年化 p90": np.quantile(cg, .9),
                            "回落 中位": np.median(md), "回落 p10": np.quantile(md, .1), "回落 p90": np.quantile(md, .9), "對A年化差 中位": np.median(dc),
                            "年化贏A比例": float(np.mean(dc > 1e-12)) if wv else np.nan, "回落差 中位": np.median(md - a[f"{sg}_回落"].to_numpy())})
        for sg in SEGS:
            out.append({"策略": "低檔 logit 策略（單獨）", "低檔比例": 1.0, "段": sg, "顆數": 1, "年化 中位": LROW[f"{sg}_年化"], "回落 中位": LROW[f"{sg}_回落"]}) if strat == "營飆 v1" else None
    return pd.DataFrame(out)


def trade_summary(PT, LT):
    out = []
    for strat in STR:
        m0 = PT[PT["策略"] == strat]
        for sg, (a, b) in SEGS.items():
            m1 = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]
            for x in THRS:
                for gname, mm in (("低檔發動", m1[m1[f"低≤{x}"] == 1]), ("非低檔發動", m1[m1[f"低≤{x}"] == 0])):
                    r = mm["報酬"]
                    out.append({"策略": strat, "段": sg, "門檻": x, "分群": gname, "筆數": len(mm), "占": len(mm) / max(len(m1), 1), "平均": r.mean(), "中位": r.median(),
                                "勝率": (r > 0).mean() if len(r) else np.nan, "去重筆": int(mm[["sid", "entry_pos"]].drop_duplicates().shape[0])})
    for sg, (a, b) in SEGS.items():
        mm = LT[(LT["進場日"] >= a) & (LT["進場日"] <= b)]; r = mm["報酬"]
        out.append({"策略": "低檔 logit 策略", "段": sg, "門檻": np.nan, "分群": "全部", "筆數": len(mm), "占": 1.0, "平均": r.mean(), "中位": r.median(),
                    "勝率": (r > 0).mean() if len(r) else np.nan, "去重筆": len(mm), "平均持有天數": mm["天"].mean() if len(mm) else np.nan})
    return pd.DataFrame(out)


def pick_versions(SP, SM):
    out = {}
    for strat in STR:
        x = SP[(SP["策略"] == strat) & (SP["段"] == "2021-2023") & (SP["版本"] != "A")].sort_values("年化 中位", ascending=False).iloc[0]
        y = SP[(SP["策略"] == strat) & (SP["段"] == "2024-2026.08") & (SP["版本"] == x["版本"])].iloc[0]
        a = SP[(SP["策略"] == strat) & (SP["段"] == "2024-2026.08") & (SP["版本"] == "A")].iloc[0]
        z = SM[(SM["策略"] == strat) & (SM["段"] == "2021-2023")].sort_values("年化 中位", ascending=False).iloc[0]
        zz = SM[(SM["策略"] == strat) & (SM["段"] == "2024-2026.08") & (SM["低檔比例"] == z["低檔比例"])].iloc[0]
        out[strat] = {"① 2021–2023 最好的版本": x["版本"], "① 其 2021–2023 年化": float(x["年化 中位"]), "① 其 2024–2026 年化": float(y["年化 中位"]), "A 2024–2026 年化": float(a["年化 中位"]),
                      "A 2021–2023 年化": float(SP[(SP["策略"] == strat) & (SP["段"] == "2021-2023") & (SP["版本"] == "A")].iloc[0]["年化 中位"]),
                      "② 2021–2023 最好的比例": float(z["低檔比例"]), "② 其 2021–2023 年化": float(z["年化 中位"]), "② 其 2024–2026 年化": float(zz["年化 中位"])}
    return out


# ═════════════ 查核 ═════════════
def check(log):
    from backtest import researchT1fix as T1
    from backtest import researchSurge5 as S5
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); last = n0 - 1
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8")); thr = META["低檔發動"]["門檻（探索段 95 分位）"]
    TG = pd.read_csv(os.path.join(OUT, "signals_tag.csv.gz"), dtype={"sid": str})
    LT = pd.read_csv(os.path.join(OUT, "launch_trades.csv.gz"), dtype={"usid": str})
    CF = pd.read_csv(os.path.join(LCDIR, "logit_coef.csv")); wv = CF["係數"].to_numpy(float)
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    D.DATA = S5.ST; cal_s = D.load_calendar(); pos_s = {d: j for j, d in enumerate(cal_s)}
    bar_s = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r"); BIT = np.load(BITS, mmap_mode="r")
    cache = {}

    def lstock(sid):
        """逐根：pos、母體、分數（飆股日曆位置 ⇒ 值）"""
        if sid in cache:
            return cache[sid]
        s = s2i[sid]; c0 = D.load_stock(sid, uni.loc[s, "market"], cal_s).df["close"].to_numpy(float)
        idx = [d for d in range(len(cal_s)) if np.isfinite(c0[d]) and bar_s[s, d]]; cb = [c0[d] for d in idx]; m = len(idx)
        pos = {}; popd = {}
        for i in range(m):
            if i >= 249:
                w = cb[i - 249:i + 1]; lo, hi = min(w), max(w)
                pos[idx[i]] = (cb[i] - lo) / (hi - lo) if hi > lo else np.nan
            else:
                pos[idx[i]] = np.nan
        for i in range(m):
            a = max(0, i - 59); j = max(range(a, i + 1), key=lambda x: (-cb[x], x)); pj = pos[idx[j]]
            if np.isfinite(pj) and pj <= 0.4 and 0.05 <= cb[i] / cb[j] - 1 <= 0.30:
                bb = int(BIT[s, idx[i]]); popd[idx[i]] = wv[0] + sum(wv[1 + b] for b in range(len(wv) - 1) if (bb >> b) & 1)
        cache[sid] = (pos, popd)
        return cache[sid]
    errs = []; info = {}
    # ① 候選標記
    S1 = TG.sample(50, random_state=20260930); nd = 0
    for r in S1.itertuples():
        sid, e = r.sid, int(r.entry_pos); c = np.asarray(ctx["closes"][sid], float)[:n0]
        T = e - 1; lo = max(T - 249, 0); P0 = lo
        for d in range(lo, T + 1):
            if c[d] > c[P0]:
                P0 = d
        t = lo
        for d in range(lo, P0 + 1):
            if c[d] < c[t]:
                t = d
        for _ in range(50):
            rm = -np.inf; st_ = None
            for d in range(t, T + 1):
                rm = max(rm, c[d])
                if c[d] <= rm * 0.7:
                    st_ = d; break
            if st_ is None:
                break
            m_ = st_
            for d in range(st_, T + 1):
                if c[d] < c[m_]:
                    m_ = d
            t = m_
        if sid in s2i:
            pos, popd = lstock(sid)
            pl = pos.get(pos_s.get(cal[t]), np.nan)
            scs = [popd[pos_s[cal[d]]] for d in range(t, e) if pos_s.get(cal[d]) in popd]
            sm = max(scs) if scs else np.nan
        else:
            pl = sm = np.nan
        same = lambda a, b: (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) < 1e-6 * max(1, abs(a)))
        if t != int(r.L) or not same(float(pl), float(r.posL)) or not same(float(sm), float(r.L分數)):
            nd += 1; errs.append(f"① {sid} {e}: L {t}/{r.L} pos {pl}/{r.posL} 分數 {sm}/{r.L分數}")
    info["① 候選 50 列不同"] = nd
    # ② 低檔策略交易
    S2 = LT.sample(min(30, len(LT)), random_state=20260930); nd2 = 0
    from backtest import researchSurge5 as S5c
    for r in S2.itertuples():
        sid = r.usid; e = int(r.entry_pos); d = int(r.d); why = []
        pos, popd = lstock(sid); ds = pos_s.get(cal[d])
        if ds not in popd or not (popd[ds] >= thr) or abs(popd[ds] - float(r.score)) > 1e-6:
            why.append(f"訊號 {popd.get(ds)} / {r.score}")
        st = D.load_stock(sid, uni.loc[s2i[sid], "market"], cal).df
        c0 = st["close"].to_numpy(float); o = st["open"].to_numpy(float); c = pd.Series(c0).ffill().to_numpy()
        isb = np.array([np.isfinite(c0[x]) and pos_s.get(cal[x]) is not None and bool(bar_s[s2i[sid], pos_s[cal[x]]]) for x in range(n0)])
        bp = float(o[e]) if np.isfinite(o[e]) and o[e] > 0 else float(c[e])
        # 流程（逐日；W1／W2 用主程式同一個建構 ⇒ 這裡驗的是錨、狀態機與價）
        ex = FE_loop(c, o, isb, bp, e, last, sid, cal)
        if ex is None:
            why.append("流程無法重算")
        else:
            (x30, p30), (x70, p70) = ex
            if not (np.isclose(p30, float(r.px30), rtol=1e-9) and np.isclose(p70, float(r.px70), rtol=1e-9)):
                why.append(f"價 {p30:.4f}/{float(r.px30):.4f} {p70:.4f}/{float(r.px70):.4f}")
        if why:
            nd2 += 1; errs.append(f"② {sid} {e}：{'；'.join(why)}")
    info["② 低檔策略交易不同"] = nd2; info["② 抽樣筆數"] = int(len(S2))
    RR.use_snapshot()
    # ③ 混合（營量、w＝0.2）逐日迴圈
    MX = pd.read_csv(os.path.join(OUT, "mix_seeds.csv.gz")); info["③"] = "見 run 內 w＝0 閘；此處以 csv 內 w＝0.2 年化與 A、低檔兩條曲線逐日迴圈比"
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), ctx["w1"])
    o, _ = run_engine(ctx, "營量 v1", ctx["sig13"], 0, SF, audit=False)
    eA = np.asarray(o["equity"], float)
    eL = np.load(os.path.join(OUT, "launch_equity.npz"))["eq"]; fL, enL = [int(x) for x in np.load(os.path.join(OUT, "launch_equity.npz"))["fe"]]
    end = min(o["end"], enL); eq = [1.0]
    for t in range(1, len(eA)):
        ra = eA[t] / eA[t - 1] - 1 if t < end else 0.0; rl = eL[t] / eL[t - 1] - 1 if t < end else 0.0
        eq.append(eq[-1] * (1 + 0.8 * ra + 0.2 * rl))
    x, y = ctx["w0"], ctx["w1"]; c_, _, _ = RR.win_metrics(np.array(eq), min(o["first"], fL), end, x, y)
    ref = float(MX[(MX["策略"] == "營量 v1") & (MX["比例"] == 0.2)]["全部_年化"].iloc[0])
    info["③ 營量 w＝0.2 全部年化（迴圈／檔）"] = [float(c_), ref]
    if abs(c_ - ref) > 1e-9:
        errs.append("③ 混合不同")
    out = {"讀法寫死": TIME, "比對": info, "不同的筆": errs[:20], "M1／M2 閘（主程式）": META["閘"],
           "通過": not errs and all(v is True or v == 0 for v in META["閘"].values())}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {info}｜{errs[:3]}")


_SIGW = {}


def FE_loop(c, o, isb, bp, e, last, sid, cal):
    """流程逐日重算（同 flowexit check 的寫法）⇒ ((x30, px30), (x70, px70))。"""
    if sid not in _SIGW:
        _SIGW.update(FE.surge_signals([sid], cal, lambda m: None)[0])
        from backtest import researchSurge5 as S5
        D.DATA = S5.ST
    W1, W2 = _SIGW.get(sid, (np.zeros(len(cal), bool), np.zeros(len(cal), bool)))
    n0 = last + 1

    def nxo(d):
        x = d + 1
        while x <= last and not (isb[x] and np.isfinite(o[x]) and o[x] > 0):
            x += 1
        return x if x <= last else None
    T = e - 1; lo = max(T - 249, 0); P0 = lo
    for d in range(lo, T + 1):
        if c[d] > c[P0]:
            P0 = d
    t = lo
    for d in range(lo, P0 + 1):
        if c[d] < c[t]:
            t = d
    for _ in range(50):
        rm = -np.inf; st_ = None
        for d in range(t, T + 1):
            rm = max(rm, c[d])
            if c[d] <= rm * 0.7:
                st_ = d; break
        if st_ is None:
            break
        m_ = st_
        for d in range(st_, T + 1):
            if c[d] < c[m_]:
                m_ = d
        t = m_
    rm = -np.inf; stop = None
    for d in range(t, last + 1):
        rm = max(rm, c[d])
        if c[d] <= rm * 0.7:
            stop = d; break
    pk, pkd, tv, tvd, segst = c[t], t, np.inf, -1, t
    for d in range(t + 1, e + 1):
        if c[d] > pk:
            if pkd > t and tv <= pk * 0.8 * (1 + 1e-9):
                segst = tvd
            pk, pkd, tv, tvd = c[d], d, np.inf, -1
        elif c[d] < tv:
            tv, tvd = c[d], d
    pre1 = next((d for d in range(segst, e) if W1[d]), None) if (stop is None or stop > e) else None
    lastday = stop if stop is not None else last
    rmx = -np.inf; nb = 0; ev = None
    for d in range(t, lastday + 1):
        if c[d] > rmx:
            rmx = c[d]; nb = 0
        elif isb[d]:
            nb += 1
        if d < e:
            continue
        if nb >= 40:
            ev = ("n40", d); break
        if (d == e and pre1 is not None) or (W1[d] and (stop is None or d < stop)):
            ev = ("W1", d); break
    if ev is None and stop is not None:
        ev = ("stop", stop)
    end = lambda: (n0, float(c[last]))
    op = lambda x: (x, float(o[x])) if x is not None else end()
    if ev is None:
        return end(), end()
    if ev[0] in ("n40", "stop"):
        p = op(nxo(ev[1])); return p, p
    x1 = nxo(ev[1])
    if x1 is None:
        return end(), end()
    d1date = pre1 if (pre1 is not None and ev[1] == e) else ev[1]
    pre2 = next((d for d in range(max(segst, d1date + 1), e) if W2[d]), None) if d1date < e else None
    if pre2 is not None:
        return op(x1), op(x1)
    w2d = next((d for d in range(x1, lastday + 1) if W2[d] and (stop is None or d < stop)), None)
    x2 = nxo(w2d) if w2d is not None else (nxo(stop) if stop is not None else None)
    return op(x1), op(x2)


# ═════════════ 網頁 ═════════════
def page(log):
    SP = pd.read_csv(os.path.join(OUT, "summary_portfolio.csv")); SM = pd.read_csv(os.path.join(OUT, "summary_mix.csv")); ST = pd.read_csv(os.path.join(OUT, "summary_per_trade.csv"))
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}"
            ".pane{display:none}.pane.on{display:block}td.up{color:#b0261e;font-weight:600}td.dn{color:#1f6f3d;font-weight:600}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    vn = lambda v: FNAME[v.split("≤")[0]] + (f"（位置 ≤{v.split('≤')[1]}）" if "≤" in v else "")
    LR = META["低檔策略單獨"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>低檔發動搭配營量營飆</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營量、營飆搭配「低檔發動」，期望值會變高嗎？（2017-03～2026-08）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數。低檔發動的 logit 分數是用 2021–2023 的結果訓練的，2021–2023 那段是樣本內（會偏好看）；要挑版本也只用 2021–2023，2024–2026 照報。</p>",
         "<h2>先講結論</h2><div class='ok big'>__CONCL__</div>"]
    H.append(f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。低檔發動 ＝ 前 60 天內的最低點位在一年區間下方 40% 以內、今天比那個低點漲了 5%～30%。"
             "搭配一「過濾／排序」：看營量、營飆每筆的本輪起漲點（進場前一天就找好）當時是不是在一年區間的低檔；出場照正式 60／120 天。"
             "搭配二「資金混合」：另開一個低檔發動 logit 分數前 5% 的策略（10 槽、飆股流程出場），和正式策略按比例每天再平衡合併（近似，不計再平衡成本）。"
             + (f"查核：{'通過' if CK['通過'] else '有不同'}；A 與正式 T1 版逐位元相同。" if CK else "") + "</p>")
    # ① 表
    H.append("<h2>一、過濾／排序（出場照正式）</h2><div class='sel'>策略 <select id='s1' onchange='sw()'>" + "".join(f"<option>{s}</option>" for s in STR)
             + "</select>期間 <select id='s2' onchange='sw()'>" + "".join(f"<option>{k}</option>" for k in SEGS) + "</select></div>")
    for s in STR:
        yf = s == "營飆 v1"
        for sg in SEGS:
            H.append(f"<div class='pane' id='p1{s[:2]}_{sg}'><div class='wrap'><table><tr><th class='l'>版本</th><th>年化{'<br><small>中位（p10～p90）</small>' if yf else ''}</th>"
                     f"<th>最大回落</th><th>對 A<br><small>年化差</small></th>" + ("<th>年化贏 A<br><small>種子比例</small></th>" if yf else "") + "<th>買進筆</th></tr>")
            for v in FV:
                x = SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["版本"] == v)].iloc[0]
                cls = "" if v == "A" else (" class='up'" if x["對A年化差 中位"] > 0 else " class='dn'")
                H.append(f"<tr><td class='l'>{vn(v)}</td><td>{P1(x['年化 中位'])}" + (f"<br><small>{P1(x['年化 p10'])}～{P1(x['年化 p90'])}</small>" if yf else "")
                         + f"</td><td>{P1(x['回落 中位'])}</td><td{cls}>{'—' if v == 'A' else PT(x['對A年化差 中位'])}</td>"
                         + (f"<td>{'—' if v == 'A' else P_(x['年化贏A比例'])}</td>" if yf else "") + f"<td>{x['買進筆 中位']:.0f}</td></tr>")
            H.append("</table></div>")
            t = ST[(ST["策略"] == s) & (ST["段"] == sg) & (ST["門檻"] == 0.4)]
            if len(t):
                a, b = t[t["分群"] == "低檔發動"].iloc[0], t[t["分群"] == "非低檔發動"].iloc[0]
                H.append(f"<p class='note'>逐筆（A 的實際交易、扣成本；營飆為 200 顆合併）：起漲點在低檔（位置 ≤0.4）的占 {P_(a['占'])}，平均 {P1(a['平均'])}、中位 {P1(a['中位'])}、勝率 {P_(a['勝率'])}；"
                         f"其他 平均 {P1(b['平均'])}、中位 {P1(b['中位'])}、勝率 {P_(b['勝率'])}。</p>")
            H.append("</div>")
    # ② 表
    H.append("<h2>二、資金混合（正式 ＋ 低檔 logit 策略）</h2><div class='wrap'><table><tr><th class='l'>策略</th><th class='l'>期間</th><th>低檔比例</th><th>年化</th><th>最大回落</th><th>對只做正式<br><small>年化差</small></th></tr>")
    for s in list(STR) + ["低檔 logit 策略（單獨）"]:
        for sg in SEGS:
            for _, x in SM[(SM["策略"] == s) & (SM["段"] == sg)].iterrows():
                yf = s == "營飆 v1"
                H.append(f"<tr><td class='l'>{s if x['低檔比例'] in (0.0, 1.0) and sg == '全部' else ''}</td><td class='l'>{sg if x['低檔比例'] in (0.0, 1.0) else ''}</td><td>{P_(x['低檔比例'])}</td>"
                         f"<td>{P1(x['年化 中位'])}" + (f"<br><small>{P1(x['年化 p10'])}～{P1(x['年化 p90'])}</small>" if yf else "") + f"</td><td>{P1(x['回落 中位'])}</td>"
                         f"<td>{'—' if x['低檔比例'] in (0.0, 1.0) else PT(x['對A年化差 中位'])}</td></tr>")
    H.append("</table></div>")
    lt = ST[(ST["策略"] == "低檔 logit 策略") & (ST["段"] == "全部")].iloc[0]
    H.append(f"<p class='note'>低檔 logit 策略單獨：主窗買進 {LR['買進筆']} 筆，每筆平均 {P1(lt['平均'])}、中位 {P1(lt['中位'])}、勝率 {P_(lt['勝率'])}、平均持有 {lt['平均持有天數']:.0f} 個交易日；"
             f"平均持股 {LR['平均持股']:.1f} 檔（10 槽）。分數門檻 ＝ 2021–2023 低檔發動母體日分數的前 5%（{META['低檔發動']['門檻（探索段 95 分位）']:.3f}）。</p>")
    pk = META["只用 2021–2023 挑的版本"]
    H.append("<h2>只用 2021–2023 挑，2024–2026 怎樣</h2><ul class='note'>" + "".join(
        f"<li>{s}：過濾／排序在 2021–2023 最好的是「{vn(v['① 2021–2023 最好的版本'])}」（{P1(v['① 其 2021–2023 年化'])}，正式 {P1(v['A 2021–2023 年化'])}），"
        f"到 2024–2026 {P1(v['① 其 2024–2026 年化'])}（正式 {P1(v['A 2024–2026 年化'])}）；"
        f"混合比例在 2021–2023 最好的是 {P_(v['② 2021–2023 最好的比例'])}，到 2024–2026 {P1(v['② 其 2024–2026 年化'])}。</li>" for s, v in pk.items()) + "</ul>")
    H.append("<h2>名詞與做法</h2><ul class='note'><li>位置 ＝（收盤 − 一年最低）÷（一年最高 − 一年最低），一年 ＝ 最近 250 根 K 棒；≤0.4 ＝ 在一年區間下方 40%。另報 ≤0.2、≤0.6。</li>"
             "<li>起漲點 ＝ 進場前 250 天內最高收盤之前的最低收盤（同買賣流程），只用進場前一天以前的資料。</li>"
             "<li>F3、F4 只改「候選多於空槽時先買誰」，不改買不買；營量原本依 relvol 排、營飆原本抽籤。L 分數 ＝ 起漲點到進場前一天之間，低檔發動日的 logit 分數最大值。</li>"
             "<li>資金混合是近似：兩個策略各自照自己的槽位跑，合併時每天把資金比例拉回固定值（不計這個再平衡的成本）。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value.slice(0,2),b=document.getElementById('s2').value;"
             "document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p1'+a+'_'+b))}sw()</script></main></body></html>")
    open(os.path.join(OUT, "低檔發動搭配營量營飆.html"), "w", encoding="utf-8").write("\n".join(H).replace("__CONCL__", conclusion(SP, SM, ST, META)))
    log("[網頁] 完成")


def conclusion(SP, SM, ST, META):
    """依數字自動組（M4ⓒ）；挑版本只看 2021–2023。"""
    P1 = lambda v: f"{v * 100:+.1f}%"
    sp = lambda s, v, sg: SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["版本"] == v)].iloc[0]
    sm = lambda s, w, sg: SM[(SM["策略"] == s) & (SM["段"] == sg) & (SM["低檔比例"] == w)].iloc[0]
    vn = lambda v: FNAME[v.split("≤")[0]] + (f"（位置 ≤{v.split('≤')[1]}）" if "≤" in v else "")
    L = []
    for s in STR:
        yf = s == "營飆 v1"; pk = META["只用 2021–2023 挑的版本"][s]; b = pk["① 2021–2023 最好的版本"]
        b21, b24 = sp(s, b, "2021-2023"), sp(s, b, "2024-2026.08")
        t = ST[(ST["策略"] == s) & (ST["段"] == "全部") & (ST["門檻"] == 0.4)]
        lo, nl = t[t["分群"] == "低檔發動"].iloc[0], t[t["分群"] == "非低檔發動"].iloc[0]
        f1, f3, f4 = (sp(s, v, "全部") for v in ("F1≤0.4", "F3≤0.4", "F4"))
        a = sp(s, "A", "全部"); m2 = sm(s, 0.2, "全部"); m4 = sm(s, 0.4, "全部")
        L.append(f"<li><b>{s[:2]}</b>（正式全部期間 {P1(a['年化 中位'])}）："
                 f"只買低檔發動（≤0.4）{P1(f1['年化 中位'])}、低檔優先 {P1(f3['年化 中位'])}、logit 分數優先 {P1(f4['年化 中位'])}。"
                 f"只看 2021–2023 挑，最好的是「{vn(b)}」{P1(b21['年化 中位'])}（正式 {P1(pk['A 2021–2023 年化'])}"
                 + (f"，贏 A 的種子 {b21['年化贏A比例'] * 100:.0f}%" if yf else "") + f"），"
                 f"到 2024–2026.08 {P1(b24['年化 中位'])}（正式 {P1(pk['A 2024–2026 年化'])}）。"
                 f"資金混合 20%／40% 全部期間 {P1(m2['年化 中位'])}／{P1(m4['年化 中位'])}，回落 {P1(m2['回落 中位'])}／{P1(m4['回落 中位'])}（正式 {P1(a['回落 中位'])}）；"
                 f"2021–2023 最好的比例是 {pk['② 2021–2023 最好的比例'] * 100:.0f}%。"
                 f"逐筆：起漲點在低檔的交易平均 {P1(lo['平均'])}、勝率 {lo['勝率'] * 100:.0f}%，其他 {P1(nl['平均'])}、{nl['勝率'] * 100:.0f}%。</li>")
    lr = META["低檔策略單獨"]
    return ("<ul class='big'>" + "".join(L) + "</ul>"
            f"<p>低檔 logit 策略單獨做：全部期間年化 {P1(lr['全部_年化'])}、回落 {P1(lr['全部_回落'])}"
            + ("，比營量、營飆正式都低 ⇒ 混進去主要是拉低年化、換一點回落。</p>" if all(lr["全部_年化"] < sp(s, "A", "全部")["年化 中位"] for s in STR) else "。</p>"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(log)
        page(log)


if __name__ == "__main__":
    main()

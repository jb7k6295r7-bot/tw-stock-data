# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 只配合「真頂出場訊號」（使用者：「營量、營飆只配合真頂出場訊號就好，其他的流程不用！」；參考，⛔ 不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_truetop [--check | --page]

═══ 讀法（寫死於 2026-09-30 22:58（台北），在算任何數字之前）═══
 T1 本體與閘：整套沿用 backtest/researchYL_flowexit.py（commit dca601c329）的 F1 —— ctx ＝ researchT1fix.build_ctx(True)；
    營量 v1 ＝ H60、20 槽、relvol 挑（r0；另核 r1 ＝ r0）；營飆 v1 ＝ H120、10 槽、抽籤 r ＝ 0～199
    閘 ① A 年化、回落（主窗）與 resultsT1fix/seeds.csv.gz repr 逐位元相同；閘 ② A 走 held_map 合成序列 ＝ A（營量 r0、營飆 r0～4）；
    閘 ③ 營量 r0 的 A 買進列 ＝ resultsYLlist/audit_seed0.csv.gz
 T2 真頂訊號（d 收盤可判、d 之後第一個有效開盤賣；K 棒、價格、次一開盤全同 flowexit：引擎還原收盤 ffill、開盤、research11.load_bars 有效 K 棒）：
    W2 ＝ W2a ∪ W2b，照 surge_flow_daily.signals_for（＝ flowexit.surge_signals 的 W2，直接呼叫）：
      W2a 再次進入處置：處置起日、且前 60 個交易日內另有一次起日；W2b 處置出關：處置迄日的下一個交易日；兩者都要收盤 ≥ 含當天 20 根有效 K 棒最高收盤 × 0.9、有效 K 棒
    S8 利多收黑 x＝5%：照 researchSurge6_exitsig_desc.signals 的 S8，取「營收利多收黑≥5%」∪「季報利多收黑≥5%」兩版的聯集
      （營收：月營收可得日（S5.world REV_EFF，次月 10 日後第一個交易日）當天；季報：A2 可得日（S5.world FIN）當天；
       兩者都要 Q 表 yoy ＝ 5、收盤 ≤ 開盤 ×（1 − 5%）、有效 K 棒）；飆股日曆上算、依日期對到引擎日曆；不在飆股母體的檔 ⇒ 沒有訊號
    ⭐「只看進場日之後出現的」＝ 訊號日 d ≥ 進場日 e（e 開盤買進，e 收盤的訊號已在買進之後）；進場前的訊號一律不看
 T3 版本（同一批候選訊號；正式出場 ＝ 第 H 根收盤，照正式 sig 的 xpos／g，含 T1 補；一律整筆賣，⛔ 不分 3 成／7 成、⛔ 沒有 W1、⛔ 沒有 40 天規則）：
    A  正式
    E1 真頂訊號 ＝ W2；到期前第一個訊號日 d（e ≤ d ＜ 正式出場日 xf）⇒ d 之後第一個有效開盤賣全部；與正式收盤比，取較早者（同一天 ⇒ 開盤早於收盤）
    E2 同 E1，真頂訊號 ＝ W2 ∪ S8(5%)
    E3 真頂訊號 ＝ W2；到期前不提早賣。到期日 xf 收盤時：[e, xf] 沒出現過訊號，且 c[xf] ＞ 0.7 × max(c[e..xf])（當下還沒從進場後最高收盤回落 30%）
       ⇒ 續抱；之後（d ＞ xf）第一個「訊號日」或「c[d] ≤ 0.7 × max(c[e..d])」⇒ d 之後第一個有效開盤賣；否則照正式在 xf 收盤賣
       正式本身未完（xf ≥ 資料長度，T1 墊的那天）⇒ 不延長
    E4 E1 ＋ E3：到期前有訊號 ⇒ 照 E1 提早賣；否則照 E3 判斷是否延長
    都沒發生（延長到資料尾 2026-09-24 仍未賣）⇒ 照 T1：xpos ＝ 資料尾後墊的那天、以資料尾收盤計值
    壞根（同 flowexit：訊號根前 20 根起第一個 next_bad 壞根）：出場晚於壞根前一根收盤 ⇒ 改在壞根前一根收盤出；停止交易 ⇒ 引擎 stop_force 同一條（L＋1 以 L 收盤出）
 T4 組合層：同 flowexit F5，每列候選改自己的價格鍵「代號#進場位置」＋held_map；合成收盤 ＝ 出場前照收盤、出場後凍結在賣價；
    xpos ＝ 出場日、g ＝ 賣價 ÷ 買價 − 1（出場 ＝ 正式時直接用正式 g）；名額、排序、抽籤、成本、停止交易強制出場全照正式引擎
    營量 1 顆；營飆 200 顆 ⇒ 中位、p10～p90、同顆對 A 差的中位、「年化贏 A 的顆數比例」
    分期：同一條權益曲線切窗（全部 ＝ 主窗 2017-03-02～2026-08-24；2021-01～2023-12；2024-01～2026-08-24），RR.win_metrics
    ⭐ 挑版本只看 2021～2023；2024～2026.08 只當對照，⛔ 不用它挑
 T5 逐筆（參考；同一批進場 ＝ A 的實際交易：營量 r0；營飆 200 顆合併、同一筆出現幾次算幾次，另報去重）：
    報酬 ＝ 賣價 ÷ 買價 − 1 − 0.585%；持有天數 ＝ 有效 K 棒數（開盤賣 ⇒ 算到前一根；收盤賣 ⇒ 含當根）；每持有一天 ＝ 平均報酬 ÷ 平均持有天數；分期依進場日
    報：筆數、平均、中位、勝率（＞0）、平均持有天數、每天報酬、對 A 差
 T6 觸發比例（同 T5 的交易）：到期前出現訊號（⇒ E1／E2 提早賣）、E2 裡 S8 先到的比例；E3 延長比例、延長後以訊號／回落 30%／未完結束的比例；E4 同
 T7 查核（--check）：A 交易（營量＋營飆去重）抽 50 筆（random_state 20260930），逐日迴圈從頭重算 W2（處置表逐筆）、S8（飆股資料逐根；
    營收／季報可得日清單沿用 S5.world）、E1～E4 出場日與報酬、壞根、停止交易 ⇒ 0 不同才算過；並附 T1 的閘
輸出 backtest/resultsYL_truetop/
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
from backtest import researchYL_flowexit as FX0

TIME = "2026-09-30 22:58（台北）"
OUT = "backtest/resultsYL_truetop"
COST = R.COST
VARS = ("A", "E1", "E2", "E3", "E4")
VNAME = {"A": "A 正式", "E1": "E1 到期前見真頂就賣", "E2": "E2 同 E1＋利多收黑", "E3": "E3 到期沒見真頂就續抱", "E4": "E4 到期前後都看（E1＋E3）"}
STR = FX0.STR
SEGS = FX0.SEGS
NYF = 200
S8X = 0.05


# ═════════════ S8 利多收黑（照 exitsig_desc.signals）═════════════
def s8_signals(sids, cal_e, log):
    """⇒ {sid: (S8 聯集, 營收版, 季報版)}（引擎日曆長布林）、資訊、W（給查核用的可得日）。⚠ 會切 D.DATA，結束切回快照。"""
    from backtest import researchSurge5 as S5
    W, _ = S5.world(log)
    cal_s = W["cal"]; n = len(cal_s)
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    bar = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); FXQ = S5.FIX
    revd = np.unique(W["REV_EFF"][(W["REV_EFF"] >= 0) & (W["REV_EFF"] < n)]); rev_mask = np.zeros(n, bool); rev_mask[revd] = True
    gi = cal_s.get_indexer(cal_e); ok = gi >= 0
    out = {}; miss = []; cnt = {"營收": 0, "季報": 0}
    for sid in sorted(sids):
        if sid not in s2i:
            miss.append(sid); continue
        s = s2i[sid]; st = D.load_stock(sid, uni.loc[s, "market"], cal_s)
        if st is None:
            miss.append(sid); continue
        df = st.df; c = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
        bs = np.asarray(bar[s], bool); idx = np.flatnonzero(np.isfinite(c) & bs)
        C = pd.Series(c).ffill().to_numpy(); O = np.full(n, np.nan); O[idx] = o[idx]
        Cr = np.where(bs, C, np.nan)
        with np.errstate(invalid="ignore"):
            down = Cr <= O * (1 - S8X)
        qy = np.asarray(Qm[FXQ["yoy"], s]) == 5
        a2 = np.zeros(n, bool)
        for x in W["FIN"].get(sid, []):
            if 0 <= x[0] < n:
                a2[x[0]] = True
        sr = rev_mask & qy & down & bs; sq = a2 & qy & down & bs
        E = [np.zeros(len(cal_e), bool) for _ in range(3)]
        for k, v in enumerate((sr | sq, sr, sq)):
            E[k][ok] = v[gi[ok]]
        cnt["營收"] += int(E[1].sum()); cnt["季報"] += int(E[2].sum())
        out[sid] = tuple(E)
    info = {"S8 不在飆股母體的檔": miss, "S8 訊號日數（引擎日曆、這批檔）": cnt, "引擎日曆對不到的天數": int((~ok).sum())}
    RR.use_snapshot()
    log(f"[S8] {len(out)} 檔｜{info}")
    return out, info


# ═════════════ 逐筆 ═════════════
def nxo_of(S, n0):
    nxt = S["nxt"]; last = n0 - 1
    return lambda d: (int(nxt[d + 1]) if d + 1 <= last and nxt[d + 1] >= 0 else None)


def exits_one(S, TTa, TTb, e, xf, n0):
    """⇒ {v: ('close'|'open'|'end', day)}、細節。TTa ＝ W2、TTb ＝ W2 ∪ S8。"""
    c = S["c"]; last = n0 - 1; nxo = nxo_of(S, n0)
    tk = lambda p: 2 * p[1] + (1 if p[0] == "close" else 0) if p[0] != "end" else 2 * n0
    pf = ("close", xf) if xf < n0 else ("end", None)
    hi = min(xf, n0)                                              # 到期前 ＝ [e, xf)
    op = lambda d: ("open", nxo(d)) if nxo(d) is not None else ("end", None)

    def early(TT):
        ds = e + np.flatnonzero(TT[e:hi])
        if not len(ds):
            return pf, None
        p = op(int(ds[0]))
        return (p, int(ds[0])) if tk(p) < tk(pf) else (pf, int(ds[0]))
    p1, d1 = early(TTa); p2, d2 = early(TTb)
    rec = {"前訊號日": -1 if d1 is None else d1, "前訊號日2": -1 if d2 is None else d2, "E1早賣": int(p1 != pf), "E2早賣": int(p2 != pf),
           "E2由S8": int(p2 != pf and (d1 is None or d2 < d1))}
    # E3 延長
    ext = 0; why3 = ""; p3 = pf; d3 = -1
    if xf < n0:
        seen = bool(TTa[e:xf + 1].any()); mx = float(np.max(c[e:xf + 1]))
        if seen:
            why3 = "到期前已見訊號"
        elif not c[xf] > 0.7 * mx:
            why3 = "到期時已回落30%"
        else:
            ext = 1
            rm = np.maximum.accumulate(c[e:last + 1])[xf - e + 1:]
            seg = c[xf + 1:last + 1]
            dd = xf + 1 + np.flatnonzero(seg <= 0.7 * rm)
            tt = xf + 1 + np.flatnonzero(TTa[xf + 1:last + 1])
            a_ = int(dd[0]) if len(dd) else None; b_ = int(tt[0]) if len(tt) else None
            if a_ is None and b_ is None:
                p3 = ("end", None); why3 = "延長未完"
            else:
                if b_ is not None and (a_ is None or b_ <= a_):
                    d3 = b_; why3 = "延長後見訊號"
                else:
                    d3 = a_; why3 = "延長後回落30%"
                p3 = op(d3)
    else:
        why3 = "正式未完"
    rec.update({"E3延長": ext, "E3原因": why3, "E3出場訊號日": d3})
    P = {"A": pf, "E1": p1, "E2": p2, "E3": p3, "E4": p1 if p1 != pf else p3}
    return P, rec


def finalize1(p, pf, bp, gf, e, S, n0, dbad, L, NP):
    """單一整筆出場 ⇒ xpos、g、天、合成收盤（壞根截、停止交易同 flowexit.finalize）。"""
    c = S["c"]; cc = np.r_[c, c[-1]] if NP > n0 else c
    if p == pf:
        if p[0] == "close":
            q = (2 * p[1] + 1, p[1], bp * (1 + gf), p[1])
        else:
            q = (2 * n0, n0, bp * (1 + gf), n0 - 1)
        formal = True
    elif p[0] == "open":
        q = (2 * p[1], p[1], float(S["o"][p[1]]), p[1] - 1); formal = False
    else:
        q = (2 * n0, n0, float(c[n0 - 1]), n0 - 1); formal = False
    nbad = 0
    if dbad is not None and q[0] > 2 * dbad + 1:
        q = (2 * dbad + 1, dbad, float(c[dbad]), dbad); nbad = 1; formal = False
    g = gf if formal else q[2] / bp - 1.0
    xpos = q[1]; sf = 0; dlast = q[3]
    if L is not None and xpos > L + 1:
        xpos = L + 1; g = float(c[L]) / bp - 1.0; sf = 1; dlast = L
    tt = np.arange(NP); Sc = np.where(tt <= q[3], cc[:NP], q[2])
    day = int(S["cb"][min(dlast, n0 - 1)] - (S["cb"][e - 1] if e > 0 else 0))
    return {"xpos": int(xpos), "g": float(g), "天": day, "壞根截": nbad, "停止交易": sf, "Sc": Sc}


def build_variants(ctx, sig, rule, SIGW, S8W, SA, SF, n0, NP):
    rows = []; SCS = {v: {} for v in VARS}
    Z = np.zeros(n0, bool)
    for r in sig.itertuples(index=False):
        sid = r.sid; e = int(r.entry_pos); xf = int(getattr(r, f"xpos_{rule}")); gf = float(getattr(r, f"g_{rule}"))
        if xf < 0:
            continue
        S = SA[sid]; bp = FX0.engine_ep(ctx, sid, e)
        W2 = SIGW.get(sid, (Z, Z))[1][:n0]; S8 = S8W.get(sid, (Z, Z, Z))[0][:n0]
        P, rec = exits_one(S, W2, W2 | S8, e, xf, n0)
        B = S["B"]; dbad = None
        if B is not None:
            idx = B["idx"]; kb = int(np.searchsorted(idx, e)) - 1; nbk = int(B["next_bad"][max(0, kb - 20)])
            if nbk < len(idx):
                dbad = int(idx[nbk - 1])
        L = SF.get(sid)
        key = f"{sid}#{e}"
        base = {"sid": sid, "e": e, "key": key, "bp": bp, "xf": xf, "gf": gf, "dbad": -1 if dbad is None else dbad, "L": -1 if L is None else L, **rec}
        for v in VARS:
            if v == "A":
                Sc = np.asarray(ctx["closes"][sid], float)[:NP].copy()
                xa, ga, sf = xf, gf, 0
                if L is not None and xf > L + 1:
                    xa, ga, sf = L + 1, float(ctx["closes"][sid][L]) / bp - 1.0, 1
                d_ = int(S["cb"][L if sf else min(xf, n0 - 1)] - (S["cb"][e - 1] if e > 0 else 0))
                f = {"xpos": xa, "g": ga, "天": d_, "壞根截": 0, "停止交易": sf, "Sc": Sc}
            else:
                f = finalize1(P[v], P["A"], bp, gf, e, S, n0, dbad, L, NP)
            SCS[v][key] = f.pop("Sc")
            base.update({f"{v}_{k}": val for k, val in f.items()})
            base[f"{v}_出場"] = f"{P[v][0]}{'' if P[v][1] is None else P[v][1]}"
        rows.append(base)
    return pd.DataFrame(rows), SCS


# ═════════════ 主程式 ═════════════
def run(log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    SEGP = FX0.seg_pos(cal, w0, w1)
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", float_precision="round_trip")
    gates = {}
    sids = sorted(set(ctx["sig13"]["sid"]) | set(ctx["sig"]["sid"]))
    SA = {s: FX0.stock_arrays(ctx, s, n0) for s in sids}
    log(f"[價格] {len(SA)} 檔")
    SIGW, sinfo = FX0.surge_signals(sids, cal, log)
    S8W, s8info = s8_signals(sids, cal, log)
    TRS = {}; PR = []; ATR = {}
    for strat, cf in STR.items():
        sig = ctx[cf["sig"]]; rule = cf["rule"]
        TR, SCS = build_variants(ctx, sig, rule, SIGW, S8W, SA, SF, n0, NP)
        TR.insert(0, "策略", strat); TRS[strat] = TR
        gates[f"{strat} 候選列（代號, 進場位置）不重複"] = bool(not TR.duplicated(["sid", "e"]).any())
        log(f"[{strat}] 候選 {len(TR)} 列｜{time.time() - T0:.0f}s")
        seeds = [0, 1] if strat == "營量 v1" else list(range(NYF))
        keyed = {v: FX0.keyed_inputs(ctx, sig, rule, TR, v, SCS, SF) for v in VARS}
        buys = []
        for r in seeds:
            o, au = FX0.run_engine(ctx, strat, sig, rule, cf["N"], r, SF)
            row, eq = FX0.port_row(o, au, SEGP, w0, w1)
            key = "c13" if strat == "營量 v1" else "c1"
            rr = ref[(ref["key"] == key) & (ref["var"] == "t1") & (ref["r"] == r)].iloc[0]
            c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
            ok = repr(float(c_)) == repr(float(rr["cagr"])) and repr(float(m_)) == repr(float(rr["mdd"]))
            gates.setdefault(f"① {strat} A ＝ resultsT1fix（不同顆數）", 0); gates[f"① {strat} A ＝ resultsT1fix（不同顆數）"] += int(not ok)
            PR.append({"策略": strat, "出場": "A", "r": r, **row})
            b = pd.DataFrame([a for a in au if a["side"] == "buy"])[["t", "sid", "px"]]; b["r"] = r; buys.append(b)
            if r < (1 if strat == "營量 v1" else 5):
                s2, cl, op, SFk, hm = keyed["A"]
                o2, _ = FX0.run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm, audit=False)
                gates.setdefault(f"② {strat} A 走 held_map ＝ A（不同顆數）", 0)
                gates[f"② {strat} A 走 held_map ＝ A（不同顆數）"] += int(not np.array_equal(np.asarray(o2["equity"], float), eq))
            for v in VARS[1:]:
                s2, cl, op, SFk, hm = keyed[v]
                o2, au2 = FX0.run_engine(ctx, strat, s2, rule, cf["N"], r, SFk, cl, op, hm)
                row2, _ = FX0.port_row(o2, au2, SEGP, w0, w1)
                PR.append({"策略": strat, "出場": v, "r": r, **row2})
            if r % 50 == 0:
                log(f"[{strat}] r{r}｜{time.time() - T0:.0f}s")
        BY = pd.concat(buys, ignore_index=True); BY["sid"] = BY["sid"].astype(str)
        if strat == "營量 v1":
            f0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}); f0 = f0[f0["side"] == "buy"][["t", "sid"]].reset_index(drop=True)
            y0 = BY[BY["r"] == 0].reset_index(drop=True); y1 = BY[BY["r"] == 1].reset_index(drop=True)
            gates["③ 營量 r0 A 買進列 ＝ audit_seed0"] = bool(len(f0) == len(y0) and (f0["t"].to_numpy() == y0["t"].to_numpy()).all() and (f0["sid"].to_numpy() == y0["sid"].to_numpy()).all())
            gates["營量 r1 A 買進列 ＝ r0（不抽籤）"] = bool(len(y1) == len(y0) and (y1["t"].to_numpy() == y0["t"].to_numpy()).all() and (y1["sid"].to_numpy() == y0["sid"].to_numpy()).all())
            BY = y0.assign(r=0)
        ATR[strat] = BY
        del keyed, SCS
    PR = pd.DataFrame(PR); PR.to_csv(os.path.join(OUT, "portfolio_seeds.csv.gz"), index=False, float_format="%.10g")
    for v in VARS:
        x = PR[(PR["策略"] == "營量 v1") & (PR["出場"] == v)]
        gates[f"營量 {v} r1 ＝ r0（年化回落）"] = bool(len(x) == 2 and all(x[f"{sg}_{k}"].nunique() == 1 for sg in SEGS for k in ("年化", "回落")))
    TRA = pd.concat(TRS.values(), ignore_index=True)
    TRA.to_csv(os.path.join(OUT, "signals_truetop.csv.gz"), index=False, float_format="%.10g")
    P = []
    for strat, BY in ATR.items():
        T = TRS[strat].set_index(["sid", "e"])
        m = T.loc[list(zip(BY["sid"], BY["t"].astype(int)))].reset_index()
        m["r"] = BY["r"].to_numpy(); m["進場日"] = [str(cal[int(x)].date()) for x in m["e"]]
        gates[f"{strat} A 交易進場價 ＝ 引擎（不同筆數）"] = int((~np.isclose(m["bp"].to_numpy(float), BY["px"].to_numpy(float), rtol=1e-9)).sum())
        P.append(m)
    PT = pd.concat(P, ignore_index=True)
    for v in VARS:
        PT[f"{v}_報酬"] = PT[f"{v}_g"] - COST
    PT.to_csv(os.path.join(OUT, "trades_A_entries.csv.gz"), index=False, float_format="%.10g")
    gates["A 逐筆 g ＝ 正式 g（停止交易外，不同筆數）"] = int((PT.loc[PT["A_停止交易"] == 0, "A_g"] != PT.loc[PT["A_停止交易"] == 0, "gf"]).sum())
    ST = per_trade_summary(PT, n0); ST.to_csv(os.path.join(OUT, "summary_per_trade.csv"), index=False, float_format="%.6g")
    TG = trigger_summary(PT); TG.to_csv(os.path.join(OUT, "summary_trigger.csv"), index=False, float_format="%.6g")
    SP = port_summary(PR); SP.to_csv(os.path.join(OUT, "summary_portfolio.csv"), index=False, float_format="%.6g")
    META = {"讀法寫死": TIME, "閘": gates, "飆股訊號": sinfo, "S8": s8info, "SEGP": {k: [str(cal[a].date()), str(cal[b].date())] for k, (a, b) in SEGP.items()},
            "候選列": {s: int(len(TRS[s])) for s in TRS}, "A 交易筆": {s: int(len(ATR[s])) for s in ATR},
            "營飆 A 去重筆": int(ATR["營飆 v1"][["sid", "t"]].drop_duplicates().shape[0]),
            "壞根截（候選列）": {s: {v: int(TRS[s][f"{v}_壞根截"].sum()) for v in VARS[1:]} for s in TRS}, "日曆尾": str(cal[-1].date()), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(META, ensure_ascii=False, default=str)}")
    if not all(v is True or v == 0 for v in gates.values()):
        raise SystemExit(f"⛔ 閘不過 {gates}")


def per_trade_summary(PT, n0):
    out = []
    for strat in STR:
        for dd in ((False, True) if strat == "營飆 v1" else (False,)):
            m0 = PT[PT["策略"] == strat]
            if dd:
                m0 = m0.drop_duplicates(["sid", "e"])
            for sg, (a, b) in SEGS.items():
                m = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]
                if not len(m):
                    continue
                for v in VARS:
                    x = m[f"{v}_報酬"]; d = m[f"{v}_天"]
                    out.append({"策略": strat, "口徑": "去重" if dd else ("200 顆合併" if strat == "營飆 v1" else "r0"), "段": sg, "出場": v, "筆數": len(m),
                                "平均": x.mean(), "中位": x.median(), "勝率": (x > 0).mean(), "p10": x.quantile(.1), "p90": x.quantile(.9),
                                "平均持有天數": d.mean(), "每天報酬": x.mean() / d.mean(), "對A差平均": (x - m["A_報酬"]).mean(),
                                "比A好比例": (x > m["A_報酬"] + 1e-12).mean(), "比A差比例": (x < m["A_報酬"] - 1e-12).mean(), "未完": (m[f"{v}_xpos"] >= n0).mean()})
    return pd.DataFrame(out)


def trigger_summary(PT):
    out = []
    for strat in STR:
        m0 = PT[PT["策略"] == strat]
        for sg, (a, b) in SEGS.items():
            m = m0[(m0["進場日"] >= a) & (m0["進場日"] <= b)]
            if not len(m):
                continue
            r = {"策略": strat, "段": sg, "筆數": len(m),
                 "到期前見W2（E1提早賣）": m["E1早賣"].mean(), "到期前見W2或S8（E2提早賣）": m["E2早賣"].mean(), "E2 由 S8 先觸發": m["E2由S8"].mean(),
                 "E3 延長": m["E3延長"].mean()}
            for k in ("到期前已見訊號", "到期時已回落30%", "延長後見訊號", "延長後回落30%", "延長未完", "正式未完"):
                r[f"E3｜{k}"] = (m["E3原因"] == k).mean()
            e4ext = (m["E1早賣"] == 0) & (m["E3延長"] == 1)
            r["E4 到期前見訊號提早賣"] = m["E1早賣"].mean(); r["E4 延長"] = e4ext.mean()
            r["E4 延長後見訊號"] = (e4ext & (m["E3原因"] == "延長後見訊號")).mean(); r["E4 延長後回落30%"] = (e4ext & (m["E3原因"] == "延長後回落30%")).mean()
            r["E3 平均持有天數"] = m["E3_天"].mean(); r["E3 延長筆 平均多抱天數"] = (m.loc[m["E3延長"] == 1, "E3_天"] - m.loc[m["E3延長"] == 1, "A_天"]).mean()
            out.append(r)
    return pd.DataFrame(out)


def port_summary(PR):
    out = []
    for strat in STR:
        a = PR[(PR["策略"] == strat) & (PR["出場"] == "A")].sort_values("r")
        for v in VARS:
            x = PR[(PR["策略"] == strat) & (PR["出場"] == v)].sort_values("r")
            aa = a
            if strat == "營量 v1":
                x = x[x["r"] == 0]; aa = a[a["r"] == 0]
            for sg in SEGS:
                cg = x[f"{sg}_年化"].to_numpy(); md = x[f"{sg}_回落"].to_numpy()
                dc = cg - aa[f"{sg}_年化"].to_numpy(); dm = md - aa[f"{sg}_回落"].to_numpy()
                out.append({"策略": strat, "出場": v, "段": sg, "顆數": len(x), "年化 中位": np.median(cg), "年化 p10": np.quantile(cg, .1), "年化 p90": np.quantile(cg, .9),
                            "回落 中位": np.median(md), "回落 p10": np.quantile(md, .1), "回落 p90": np.quantile(md, .9),
                            "對A年化差 中位": np.median(dc), "對A回落差 中位": np.median(dm), "年化贏A比例": float(np.mean(dc > 1e-12)) if v != "A" else np.nan,
                            "回落比A淺比例": float(np.mean(dm > 1e-12)) if v != "A" else np.nan,
                            "買進筆 中位": float(x["買進筆"].median()), "平均持股 中位": float(x["平均持股"].median()), "平均持有日 中位": float(x["平均持有日"].median())})
    return pd.DataFrame(out)


# ═════════════ 查核 ═════════════
def check(log):
    from backtest import researchT1fix as T1
    from backtest import researchSurge5 as S5
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; n0 = len(cal); last = n0 - 1; NP = ctx["ncal"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), ctx["w1"])
    PT = pd.read_csv(os.path.join(OUT, "trades_A_entries.csv.gz"), dtype={"sid": str})
    SMP = PT.drop_duplicates(["策略", "sid", "e"]).sample(50, random_state=20260930)
    W, _ = S5.world(log)
    cal_s = W["cal"]; pos_s = {d: j for j, d in enumerate(cal_s)}
    rev_days = set(int(x) for x in W["REV_EFF"] if 0 <= x < len(cal_s))
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    bar_s = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r"); Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); FXQ = S5.FIX
    dsp = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    SIGC = {}
    for sid in sorted(set(SMP["sid"])):
        W2 = np.zeros(n0, bool); S8 = np.zeros(n0, bool)
        if sid in s2i:
            s = s2i[sid]; df = D.load_stock(sid, uni.loc[s, "market"], cal_s).df
            c0 = df["close"].to_numpy(float); o0 = df["open"].to_numpy(float)
            bars = [d for d in range(len(cal_s)) if np.isfinite(c0[d]) and bar_s[s, d]]; bpos = {d: j for j, d in enumerate(bars)}
            yoy = np.asarray(Qm[FXQ["yoy"], s]); a2 = set(int(x[0]) for x in W["FIN"].get(sid, []))
            g = dsp[dsp["stock_id"] == sid]
            starts = [int(cal_s.searchsorted(pd.Timestamp(x))) for x in g["start_date"]]
            ends = [int(cal_s.searchsorted(pd.Timestamp(y), side="right")) - 1 for y in g["end_date"]]
            for te in range(n0):
                d = pos_s.get(cal[te])
                if d is None or d not in bpos:
                    continue
                j = bpos[d]
                near = j >= 19 and c0[d] >= 0.9 * max(c0[bars[j - 19:j + 1]])
                re60 = d in starts and any(0 < d - x <= 60 for x in starts if x != d)
                ex_ = any(d == b + 1 for b in ends)
                W2[te] = near and (re60 or ex_)
                S8[te] = (d in rev_days or d in a2) and yoy[d] == 5 and np.isfinite(o0[d]) and c0[d] <= o0[d] * (1 - S8X)
        SIGC[sid] = (W2, S8)
    RR.use_snapshot()
    errs = []; nd = 0; cnt = {"E1早賣": 0, "E2早賣": 0, "E3延長": 0}
    for r in SMP.itertuples():
        sid, e, xf, gf = r.sid, int(r.e), int(r.xf), float(r.gf); why = []
        B = R.load_bars(sid, ctx["mk"].get(sid, "twse"), cal)
        c = np.asarray(ctx["closes"][sid], float)[:n0]; o = np.asarray(ctx["opens"][sid], float)[:n0]
        isb = np.zeros(n0, bool); isb[B["idx"][B["idx"] < n0]] = True
        W2, S8 = SIGC[sid]
        bp = float(o[e]) if np.isfinite(o[e]) and o[e] > 0 else float(c[e])

        def nxo(d):
            x = d + 1
            while x <= last and not (isb[x] and np.isfinite(o[x]) and o[x] > 0):
                x += 1
            return x if x <= last else None

        # 逐日：E1／E2（到期前）
        def early(use8):
            for d in range(e, min(xf, n0)):
                if W2[d] or (use8 and S8[d]):
                    x = nxo(d)
                    if x is None:
                        return None
                    return ("open", x) if (xf >= n0 or x <= xf) else None
            return None

        def ext():
            if xf >= n0:
                return None
            mx = -np.inf; seen = False
            for d in range(e, xf + 1):
                mx = max(mx, c[d]); seen = seen or bool(W2[d])
            if seen or c[xf] <= 0.7 * mx:
                return None
            for d in range(xf + 1, last + 1):
                mx = max(mx, c[d])
                if W2[d] or c[d] <= 0.7 * mx:
                    x = nxo(d)
                    return ("open", x) if x is not None else ("end", None)
            return ("end", None)
        p1, p2, p3 = early(False), early(True), ext()
        cnt["E1早賣"] += int(p1 is not None); cnt["E2早賣"] += int(p2 is not None); cnt["E3延長"] += int(p3 is not None)
        idx = B["idx"]; kb = int(np.searchsorted(idx, e)) - 1; nbk = int(B["next_bad"][max(0, kb - 20)]); dbad = int(idx[nbk - 1]) if nbk < len(idx) else None
        L = SF.get(sid)
        for v, p in (("E1", p1), ("E2", p2), ("E3", p3), ("E4", p1 if p1 is not None else p3)):
            if p is None:                                      # 照正式
                xp, g, lastheld = xf, gf, min(xf, n0 - 1)
                if dbad is not None and xf > dbad:
                    xp, g, lastheld = dbad, c[dbad] / bp - 1, dbad
            elif p[0] == "open":
                xp, g, lastheld = p[1], o[p[1]] / bp - 1, p[1] - 1
                if dbad is not None and 2 * p[1] > 2 * dbad + 1:
                    xp, g, lastheld = dbad, c[dbad] / bp - 1, dbad
            else:
                xp, g, lastheld = n0, c[last] / bp - 1, last
                if dbad is not None:
                    xp, g, lastheld = dbad, c[dbad] / bp - 1, dbad
            if L is not None and xp > L + 1:
                xp, g = L + 1, c[L] / bp - 1
            if xp != int(getattr(r, f"{v}_xpos")) or not np.isclose(g, float(getattr(r, f"{v}_g")), rtol=1e-9, atol=1e-12):
                why.append(f"{v}: xpos {xp}/{getattr(r, f'{v}_xpos')} g {g:.6f}/{float(getattr(r, f'{v}_g')):.6f}")
        if why:
            nd += 1; errs.append(f"{r.策略} {sid} {e}：{'；'.join(why)}")
    meta = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    out = {"讀法寫死": TIME, "抽樣": "A 交易（營量＋營飆去重）抽 50 筆（random_state 20260930）", "不同": nd, "事件（抽樣）": cnt, "不同的筆": errs[:20],
           "T1 閘（主程式）": meta["閘"], "通過": nd == 0 and all(v is True or v == 0 for v in meta["閘"].values())}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 不同 {nd}｜{cnt}｜{errs[:3]}")


# ═════════════ 網頁 ═════════════
def page(log):
    ST = pd.read_csv(os.path.join(OUT, "summary_per_trade.csv")); SP = pd.read_csv(os.path.join(OUT, "summary_portfolio.csv"))
    TG = pd.read_csv(os.path.join(OUT, "summary_trigger.csv")); META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}"
            ".pane{display:none}.pane.on{display:block}td.up{color:#b0261e;font-weight:600}td.dn{color:#1f6f3d;font-weight:600}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    P_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    D_ = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.0f}"
    B2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f}%"
    st = lambda s, sg, v: ST[(ST["策略"] == s) & (ST["段"] == sg) & (ST["出場"] == v) & (ST["口徑"] != "去重")].iloc[0]
    sp = lambda s, sg, v: SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["出場"] == v)].iloc[0]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量營飆配真頂訊號</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營量、營飆只配合「真頂出場訊號」（2017-03～2026-08）</h1>",
         "<p class='warn'>⚠ 只當參考，沒有計入檢定數。挑版本只看 2021～2023；2024～2026.08 只是對照。</p>"]
    H.append("<div class='ok big'>__CONCL__</div>")
    H.append(f"<p class='lead'>讀法寫死 {html.escape(META['讀法寫死'])}。真頂訊號：<b>W2</b>＝再次進入處置或處置出關，且收盤在 20 日最高收盤 9 成以上；"
             "<b>利多收黑</b>＝營收或財報利多（年增最高兩成）公布當天收黑 5% 以上（只在 E2）。訊號當天收盤看到、隔天開盤整筆賣；只看進場當天以後的訊號。"
             "組合層照正式引擎重新模擬（同槽數、排序／抽籤、成本、停止交易強制出場）。"
             + (f"查核：抽 50 筆逐日重算，{CK['不同']} 筆不同；A 與正式 T1 版逐位元相同。" if CK else "") + "</p>")
    H.append("<h2>一、組合層</h2><div class='sel'>策略 <select id='s1' onchange='sw()'>" + "".join(f"<option>{s}</option>" for s in STR) + "</select></div>")
    for s in STR:
        yf = s == "營飆 v1"
        H.append(f"<div class='pane' id='p1{s[:2]}'><div class='wrap'><table><tr><th class='l'>期間</th><th class='l'>出場</th><th>年化{'<br><small>中位（p10～p90）</small>' if yf else ''}</th>"
                 f"<th>最大回落{'<br><small>中位（p10～p90）</small>' if yf else ''}</th><th>對 A<br><small>年化差</small></th>"
                 + ("<th>年化贏 A<br><small>種子比例</small></th>" if yf else "") + "<th>買進筆</th><th>平均持有<br><small>交易日</small></th></tr>")
        for sg in SEGS:
            for v in VARS:
                x = sp(s, sg, v)
                cls = "" if v == "A" else (" class='up'" if x["對A年化差 中位"] > 0 else " class='dn'")
                H.append(f"<tr><td class='l'>{sg if v == 'A' else ''}</td><td class='l'>{VNAME[v]}</td>"
                         f"<td>{P1(x['年化 中位'])}" + (f"<br><small>{P1(x['年化 p10'])}～{P1(x['年化 p90'])}</small>" if yf else "") + "</td>"
                         f"<td>{P1(x['回落 中位'])}" + (f"<br><small>{P1(x['回落 p10'])}～{P1(x['回落 p90'])}</small>" if yf else "") + "</td>"
                         f"<td{cls}>{'—' if v == 'A' else PT(x['對A年化差 中位'])}</td>"
                         + (f"<td>{'—' if v == 'A' else P_(x['年化贏A比例'])}</td>" if yf else "")
                         + f"<td>{D_(x['買進筆 中位'])}</td><td>{D_(x['平均持有日 中位'])}</td></tr>")
        H.append("</table></div><p class='note'>買進筆、平均持有只算主窗。" + ("營飆抽籤 200 顆種子；對 A 差是同一顆種子相減取中位。" if yf else "營量依 relvol 排序、不抽籤。") + "</p></div>")
    H.append("<h2>二、逐筆（同一批進場：A 實際買進的交易）</h2><div class='sel'>策略 <select id='s2' onchange='sw()'>"
             + "".join(f"<option>{s}</option>" for s in STR) + "</select>期間 <select id='s3' onchange='sw()'>" + "".join(f"<option>{k}</option>" for k in SEGS) + "</select></div>")
    for s in STR:
        for sg in SEGS:
            H.append(f"<div class='pane' id='p2{s[:2]}_{sg}'><div class='wrap'><table><tr><th class='l'>出場</th><th>筆數</th><th>平均<br><small>扣成本</small></th><th>中位</th><th>勝率</th>"
                     "<th>平均持有<br><small>交易日</small></th><th>每持有一天</th><th>對 A 差<br><small>平均</small></th><th>比 A 好／差</th></tr>")
            for v in VARS:
                x = st(s, sg, v)
                H.append(f"<tr><td class='l'>{VNAME[v]}</td><td>{int(x['筆數']):,}</td><td>{B2(x['平均'])}</td><td>{B2(x['中位'])}</td><td>{P_(x['勝率'])}</td>"
                         f"<td>{D_(x['平均持有天數'])}</td><td>{B2(x['每天報酬'])}</td><td>{'—' if v == 'A' else PT(x['對A差平均'])}</td>"
                         f"<td>{'—' if v == 'A' else P_(x['比A好比例']) + '／' + P_(x['比A差比例'])}</td></tr>")
            H.append("</table></div>")
            t = TG[(TG["策略"] == s) & (TG["段"] == sg)]
            if len(t):
                t = t.iloc[0]
                H.append(f"<p class='note'>觸發：到期前出現 W2 {P_(t['到期前見W2（E1提早賣）'])}（加利多收黑 {P_(t['到期前見W2或S8（E2提早賣）'])}）；"
                         f"到期時續抱（E3）{P_(t['E3 延長'])}，其中之後見 W2 結束 {P_(t['E3｜延長後見訊號'])}、回落 30% 結束 {P_(t['E3｜延長後回落30%'])}、到資料尾還沒賣 {P_(t['E3｜延長未完'])}（占全部筆數）；"
                         f"續抱的筆平均多抱 {D_(t['E3 延長筆 平均多抱天數'])} 個交易日。</p>")
            H.append("</div>")
    H.append("<h2>名詞與做法</h2><ul class='note'>"
             "<li>A 正式：營量第 60 個交易日收盤賣（20 槽、依 relvol 挑）；營飆第 120 個交易日收盤賣（10 槽、抽籤）。</li>"
             "<li>E1：到期前出現 W2 ⇒ 隔天開盤全部賣；沒出現就照正式到期賣。E2：E1 再加利多收黑。</li>"
             "<li>E3：到期前不看訊號；到期當天若進場以來沒出現過 W2、而且收盤還在進場後最高收盤 7 成以上 ⇒ 續抱，直到出現 W2 或從最高回落 30%（隔天開盤賣）。E4：E1＋E3。</li>"
             "<li>資料最後一天（2026-09-24）還沒賣的，以那天收盤計值。每筆扣來回成本 0.585%。</li>"
             "<li>和上一份（配飆股流程）不同：這裡不分批、沒有 W1 賣 3 成，也沒有 40 天沒新高。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value.slice(0,2),b=document.getElementById('s2').value.slice(0,2),c=document.getElementById('s3').value;"
             "document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p1'+a||x.id=='p2'+b+'_'+c))}sw()</script></main></body></html>")
    txt = "\n".join(H).replace("__CONCL__", conclusion(ST, SP, TG))
    open(os.path.join(OUT, "營量營飆配真頂訊號.html"), "w", encoding="utf-8").write(txt)
    log("[網頁] 完成")


def conclusion(ST, SP, TG):
    """依數字自動組；挑版本只看 2021～2023（讀法 T4）。"""
    P1 = lambda v: f"{v * 100:+.1f}%"
    sp = lambda s, v, sg: SP[(SP["策略"] == s) & (SP["段"] == sg) & (SP["出場"] == v)].iloc[0]
    L = []
    for s in STR:
        yf = s == "營飆 v1"
        best = max(VARS[1:], key=lambda v: sp(s, v, "2021-2023")["年化 中位"])
        a21, b21 = sp(s, "A", "2021-2023"), sp(s, best, "2021-2023"); a24, b24 = sp(s, "A", "2024-2026.08"), sp(s, best, "2024-2026.08")
        aal, bal = sp(s, "A", "全部"), sp(s, best, "全部")
        win = b21["對A年化差 中位"] > 0
        L.append(f"<li><b>{s[:2]}</b>：2021～2023 最好的是 <b>{VNAME[best]}</b>，年化 {P1(b21['年化 中位'])}（正式 {P1(a21['年化 中位'])}，"
                 f"{'多' if win else '少'} {abs(b21['對A年化差 中位']) * 100:.1f} 點"
                 + (f"，贏 A 的種子 {b21['年化贏A比例'] * 100:.0f}%" if yf else "") + "）；"
                 f"拿到 2024～2026.08 對照：{P1(b24['年化 中位'])} vs 正式 {P1(a24['年化 中位'])}"
                 + (f"（贏 A 的種子 {b24['年化贏A比例'] * 100:.0f}%）" if yf else "") + "；"
                 f"全部期間 {P1(bal['年化 中位'])}／回落 {P1(bal['回落 中位'])}，正式 {P1(aal['年化 中位'])}／{P1(aal['回落 中位'])}。</li>")
    return "<b>先講結論</b><ul class='big'>" + "".join(L) + "</ul>"


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

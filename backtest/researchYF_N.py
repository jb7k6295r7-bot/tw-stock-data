# -*- coding: utf-8 -*-
"""營飆 v1 持股上限 N ＝ 10／15／20（裁定 seq376；使用者問「營飆20檔是會變成怎樣？」）——回測線計算子代理。
⭐ 描述、⛔ 不計 N、⛔ 不改營飆 v1 正式規則（N10）。⛔ 不改任何既有 .py／結果夾；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYF_N [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYF_N_check [--procs 3]

═══ 讀法（寫於 2026-10-18 16:11（台北），在算任何本件數字之前；⚠ 本線看過：營飆 v1 各段、resultsYL_integrate 36 格（含 H120·S15／S20·閘·抽籤 的
    探索／確認／早年年化與回落）、resultsN17/nslots（舊 regime_t1 世界的 N10／20／30 主窗））═══
 Y1 規則一字不動、只換 N：營飆 v1 ＝ researchYL_integrate.eng 的「H120·S{N}·閘·抽籤」分支原式
    ＝ research11.simulate_mtm(SIG[閘], "H120", N, default_rng(rerun17.P10_SEED0＋r), closes, opens, NP, return_equity=True, stop_force=SF)
    （＝ forward_yl.STRATS["營飆v1"]：H120、gate True、pick None 抽籤）；N ∈ {10, 15, 20}；每檔 slot ＝ 前一日權益 ÷ N；r ＝ 0～199
    本檔另傳 log=[]、audit=[]（只記錄、數值路徑不變 ⇒ 閘 G2 逐位元驗）
    世界 ＝ researchYL_integrate.main_world（＝ researchT1fix.build_ctx(True)：AND T1、停止交易強制出場開）與 early_world（上市＋上櫃 eotc_f65bb03e11、R8 截斷）
 Y2 段（＝ 營飆 v1 原報告／整合件 I3 段界）：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（主窗一條權益切段讀）；早年 2005-02-01～2014-12-31（早年世界）
    另附主窗 2017-03-02～2026-08-24（描述）
 Y3 每顆種子、每段：
    年化、最大回落 ＝ rerun17.win_metrics；比值 ＝ 年化中位 ÷ |回落中位|（200 顆中位，同整合件）；對 0050 ＝ researchYL_integrate.label（合格／另列／不合格）＋ 0050 同段數字
    平均實際持股 ＝ audit 逐日（買 +1、賣 −1 累加）段內平均（＝ 整合件 stats 同式）；現金比例 ＝ 1 − 段內平均(持股市值 ÷ 權益)（同式）
    抽籤落選 ＝ 引擎 log 原因 "a"（當天有空槽但候選多於空槽、抽輸；含現金用盡）之 t ∈ 段 的筆數；
      另報 槽滿未進 ＝ 當天開盤前（排程出場後）持股 ＝ N、候選（當天訊號且未持有）全部沒進的筆數（引擎在槽滿時不抽、不記 log ⇒ 本檔由 audit 區間重建）
    等效獨立檔數 ＝ researchDumb／researchYLmargin.eff_n 同定義：段內每個有買進的日子 t，收盤持股 N_t 檔（買進日 ≤ t ＜ 賣出日）、
      ρ ＝ 各檔前 60 個交易日收盤日報酬兩兩相關平均（共同 ＜ 40 天或零變異略過），N_t ÷ (1＋(N_t−1)ρ)，段內平均（本檔用矩陣式算兩兩相關；查核檔用原迴圈式對）
    右尾：段內買進（audit 買進日 ∈ 段）的每筆交易 貢獻 ＝ 買進金額 ×（毛報酬 − COST）÷ 買進前一日權益（＝ 該筆對組合的報酬貢獻，以進場時權益計）；
      毛報酬 ＝ 賣出價 ÷ 買進價 − 1（audit 同一檔先買後賣配對）；前 10% ＝ 貢獻最大的 ⌈0.1 × 筆數⌉ 筆
      ⇒ 占比 ＝ 前 10% 貢獻和 ÷ 全部貢獻和（全部 ≤ 0 ⇒ NaN；虧損筆多時可 ＞ 100%）；另報 占正貢獻 ＝ 前 10% 貢獻和 ÷ 正貢獻筆的貢獻和（≤ 100%）；另報前 10% 貢獻和（權益倍數）與前 10% 交易的淨報酬中位
    200 顆中位為主，另報 p10／p90；另報同顆種子 年化、回落 兩項皆好／皆差於 N10 的顆數（描述）
 Y4 閘（不過即停）：G1 N10 主窗 ＝ resultsT1fix seeds c1 t1 r0～199（營飆 v1 定版；eq_sha、年化、回落 repr）；
    G2 N10／15／20 兩世界 ＝ resultsYL_integrate/seeds.csv.gz 同格同 r（eq_sha、各段 年化／回落／持股／現金 repr）；G3 0050 各段 ＝ 整合件 summary.json
 必附：「看過結果的參數變體，只描述，不當改規則的依據」；早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3；
    另註「使用者實際營飆持 15 份（10 格＋超額 5），15 檔版可對照他現在的實際狀態」
輸出 backtest/resultsYF_N/：seeds.csv.gz、cells.csv、summary.json、run.log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

TIME = "2026-10-18 16:11（台北）"
OUT = "backtest/resultsYF_N"
NS = (10, 15, 20)
NSEED = 200
if os.environ.get("YFN_QUICK"):                              # 煙霧測試（不是交件）
    NSEED, OUT = 2, "/tmp/yfn_quick"
COST = R.COST
WORD = "看過結果的參數變體，只描述，不當改規則的依據"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；本件早年照營飆 v1 早年既有版面（上市＋上櫃 eotc_f65bb03e11、R8 截斷）", IG.NOTE3]
NOTE_15 = "使用者實際營飆持 15 份（10 格＋超額 5），15 檔版可對照他現在的實際狀態"
SEGORD = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
_W: dict = {}


def key_of(N):
    return IG.ck(120, N, True, "抽籤")


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


# ═════════════ 引擎（Y1）═════════════
def engine(W, N, r, log=None, audit=None):
    return R.simulate_mtm(W["SIG"][True], "H120", N, np.random.default_rng(RR.P10_SEED0 + r), W["closes"], W["opens"], W["NP"],
                          return_equity=True, stop_force=W["SF"], audit=audit, log=log)


def trades_of(au, NP):
    """audit ⇒ [(sid, tb, ts, amt, px_in, px_out, eq_prev)]；同一檔先買後賣配對；資料尾未賣 ⇒ ts＝NP、px_out＝NaN。"""
    op, T = {}, []
    for a in au:
        if a["side"] == "buy":
            if a["sid"] in op:
                raise SystemExit(f"⛔ {a['sid']} 重複買進")
            op[a["sid"]] = (a["t"], a["amt"], a["px"], a["equity_prev"])
        else:
            tb, amt, px, ep_ = op.pop(a["sid"])
            T.append((a["sid"], tb, a["t"], amt, px, a["px"], ep_))
    for s, (tb, amt, px, ep_) in op.items():
        T.append((s, tb, NP, amt, px, np.nan, ep_))
    return T


def corr_mean(Rm):
    """Rm（N×60，NaN ＝ 缺）⇒ 兩兩相關平均（共同 ≥ 40 天、兩邊變異 ＞ 0 才算）；同 eff_n 迴圈式的矩陣版。"""
    M = np.isfinite(Rm).astype(float); X = np.where(M > 0, Rm, 0.0)
    n = M @ M.T; Sx = X @ M.T; Sxx = (X * X) @ M.T; Sxy = X @ X.T
    with np.errstate(invalid="ignore", divide="ignore"):
        vi = Sxx - Sx ** 2 / n; vj = vi.T
        cov = Sxy - Sx * Sx.T / n
        c = cov / np.sqrt(vi * vj)
    iu = np.triu_indices(len(Rm), 1)
    ok = (n[iu] >= 40) & (vi[iu] > 1e-18) & (vj[iu] > 1e-18)
    v = c[iu][ok]
    return float(v.mean()) if len(v) else np.nan


def eff_n(closes, iv, days):
    res = []
    for t in days:
        held = [s for s, t0, t1 in iv if t0 <= t < t1]
        Nt = len(held)
        if Nt == 0:
            continue
        if Nt == 1:
            res.append((t, 1, np.nan, 1.0)); continue
        Rm = []
        for s in held:
            cc = np.asarray(closes[s][max(t - 60, 0):t + 1], float)
            Rm.append(cc[1:] / cc[:-1] - 1.0 if len(cc) == 61 else np.full(60, np.nan))
        rho = corr_mean(np.array(Rm))
        res.append((t, Nt, rho, Nt / (1 + (Nt - 1) * rho) if np.isfinite(rho) else np.nan))
    return res


def seg_stats(W, N, o, au, lg):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float); NP = W["NP"]
    cnt = np.zeros(len(eq) + 1)
    for a in au:
        cnt[a["t"]] += 1 if a["side"] == "buy" else -1
    hold = np.cumsum(cnt)[:len(eq)]
    TR = trades_of(au, NP)
    iv = [(s, tb, ts) for s, tb, ts, *_ in TR]
    la = np.array([z["t"] for z in lg if z["reason"] == "a"], int)
    row = {}
    for sg, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1])); row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
        row[f"{sg}_抽籤落選"] = int(((la >= x) & (la <= y)).sum())
        # 槽滿未進：開盤前（排程出場後）持有 ＝ tb ＜ t ＜ ts
        full_miss = 0
        for t, sids in W["DAYSIG"].items():
            if not (x <= t <= y):
                continue
            hp = {s for s, tb, ts in iv if tb < t < ts}
            if len(hp) >= N:
                full_miss += sum(1 for s in sids if s not in hp)
        row[f"{sg}_槽滿未進"] = int(full_miss)
        days = sorted({tb for s, tb, ts in iv if x <= tb <= y})
        en = eff_n(W["closes"], iv, days)
        row[f"{sg}_等效獨立"] = float(np.nanmean([z[3] for z in en])) if en else np.nan
        row[f"{sg}_平均ρ"] = float(np.nanmean([z[2] for z in en])) if en else np.nan
        # 右尾
        cs, nets = [], []
        for s, tb, ts, amt, pin, pout, ep_ in TR:
            if not (x <= tb <= y):
                continue
            if not np.isfinite(pout):
                pout = float(W["closes"][s][min(o["end"], NP) - 1])
            g = pout / pin - 1.0
            cs.append(amt * (g - COST) / ep_); nets.append(g - COST)
        cs = np.array(cs); nets = np.array(nets)
        n_ = len(cs); k = int(math.ceil(0.1 * n_)) if n_ else 0
        row[f"{sg}_交易數"] = n_
        if n_:
            od = np.argsort(-cs, kind="stable")[:k]
            tot = float(cs.sum()); top = float(cs[od].sum())
            row[f"{sg}_前10%占比"] = top / tot if tot > 0 else np.nan
            pos_ = float(cs[cs > 0].sum())
            row[f"{sg}_前10%占正貢獻"] = top / pos_ if pos_ > 0 else np.nan
            row[f"{sg}_前10%貢獻和"] = top; row[f"{sg}_全部貢獻和"] = tot
            row[f"{sg}_前10%淨報酬中位"] = float(np.median(nets[od]))
        else:
            row.update({f"{sg}_前10%占比": np.nan, f"{sg}_前10%占正貢獻": np.nan, f"{sg}_前10%貢獻和": np.nan, f"{sg}_全部貢獻和": np.nan, f"{sg}_前10%淨報酬中位": np.nan})
    return row, eq


def job(args):
    wn, N, r = args
    W = _W[wn]
    lg, au = [], []
    o = engine(W, N, r, log=lg, audit=au)
    row, eq = seg_stats(W, N, o, au, lg)
    row.update({"世界": wn, "N": N, "格": key_of(N), "r": r, "eq_sha": sha(eq), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])})
    return row


def day_sig(W):
    s = W["SIG"][True]
    d = s.dropna(subset=["sid", "entry_pos", "xpos_H120", "g_H120"])
    d = d[d["xpos_H120"] >= 0]
    return {int(k): list(g["sid"]) for k, g in d.groupby("entry_pos")}


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}｜N {NS}｜種子 {NSEED}")
    Wm, gm = IG.main_world(log)
    We, ge = IG.early_world(log, a.procs)
    for W in (Wm, We):
        W["DAYSIG"] = day_sig(W)
    _W["主"], _W["早年"] = Wm, We
    S = {"讀法寫死": TIME, "裁定": "seq376（描述、不計 N、不改營飆 v1 正式規則）", "必附": WORD, "早年註": NOTE_EARLY, "15檔註": NOTE_15,
         "世界閘": {**gm, **ge}}
    jobs = [(wn, N, r) for wn in ("主", "早年") for N in NS for r in range(NSEED)]
    T0 = time.time()
    with Pool(a.procs) as pool:
        ROWS = pool.map(job, jobs, chunksize=4)
    SE = pd.DataFrame(ROWS)
    log(f"[引擎] {len(SE)} 次｜{time.time() - T0:.0f}s")
    # ── 閘 ──
    gate = {}
    ref1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    r1 = ref1[(ref1["key"] == "c1") & (ref1["var"] == "t1")].set_index("r")
    m1 = SE[(SE["世界"] == "主") & (SE["N"] == 10)].set_index("r")
    gate["G1 N10 主窗 ＝ T1fix c1 t1（不同顆數）"] = int(sum(m1.loc[r, "eq_sha"] != r1.loc[r, "eq_sha"] or repr(float(m1.loc[r, "主窗_年化"])) != repr(float(r1.loc[r, "cagr"]))
                                                   or repr(float(m1.loc[r, "主窗_回落"])) != repr(float(r1.loc[r, "mdd"])) for r in m1.index))
    refI = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    for wn in ("主", "早年"):
        for N in NS:
            a_ = SE[(SE["世界"] == wn) & (SE["N"] == N)].set_index("r")
            b_ = refI[(refI["世界"] == wn) & (refI["格"] == key_of(N))].set_index("r")
            bad = 0
            for r in a_.index:
                if a_.loc[r, "eq_sha"] != b_.loc[r, "eq_sha"]:
                    bad += 1; continue
                for sg in SEGORD[wn]:
                    for k in ("年化", "回落", "持股", "現金"):
                        if repr(float(a_.loc[r, f"{sg}_{k}"])) != repr(float(b_.loc[r, f"{sg}_{k}"])):
                            bad += 1; break
            gate[f"G2 {wn} N{N} ＝ 整合件 {key_of(N)}（不同顆數／{len(a_)}）"] = bad
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    gate["G3 0050 各段 ＝ 整合件（不同段數）"] = int(sum(repr(float(_W[wn]["b50"][sg][k])) != repr(float(sm[wn][sg][k]))
                                                for wn in ("主", "早年") for sg in SEGORD[wn] for k in ("cagr", "mdd")))
    S["閘"] = gate
    log(f"[閘] {gate}")
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    if any(v != 0 for v in gate.values()):
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit("⛔ 閘不過")
    # ── 彙總 ──
    MET = ["年化", "回落", "持股", "現金", "抽籤落選", "槽滿未進", "等效獨立", "平均ρ", "交易數", "前10%占比", "前10%占正貢獻", "前10%貢獻和", "全部貢獻和", "前10%淨報酬中位"]
    C = []
    for wn in ("主", "早年"):
        W = _W[wn]
        for sg in SEGORD[wn]:
            x, y = W["segp"][sg]; b = W["b50"][sg]
            base = SE[(SE["世界"] == wn) & (SE["N"] == 10)].set_index("r")
            for N in NS:
                g = SE[(SE["世界"] == wn) & (SE["N"] == N)].set_index("r")
                c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                row = {"世界": wn, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "N": N, "顆數": len(g),
                       "比值": c_ / abs(m_), "對0050": IG.label(c_, m_, b), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])}
                for k in MET:
                    v = g[f"{sg}_{k}"].astype(float)
                    row[f"{k}_中位"] = float(v.median()); row[f"{k}_p10"] = float(v.quantile(.1)); row[f"{k}_p90"] = float(v.quantile(.9))
                row["前10%占比_NaN顆數"] = int(g[f"{sg}_前10%占比"].isna().sum())
                if N != 10:
                    row["同顆_兩項皆好於N10"] = int(((g[f"{sg}_年化"] > base[f"{sg}_年化"]) & (g[f"{sg}_回落"] > base[f"{sg}_回落"])).sum())
                    row["同顆_兩項皆差於N10"] = int(((g[f"{sg}_年化"] < base[f"{sg}_年化"]) & (g[f"{sg}_回落"] < base[f"{sg}_回落"])).sum())
                C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S["表"] = C.to_dict("records")
    S["完成（台北）"] = now_tpe()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    show = ["世界", "段", "N", "年化_中位", "年化_p10", "年化_p90", "回落_中位", "比值", "對0050", "持股_中位", "現金_中位", "抽籤落選_中位", "槽滿未進_中位",
            "等效獨立_中位", "前10%占比_中位", "前10%占正貢獻_中位", "前10%貢獻和_中位", "全部貢獻和_中位"]
    log("\n" + C[show].to_string(index=False))
    log(f"[完] {now_tpe()}（台北）")


if __name__ == "__main__":
    main()

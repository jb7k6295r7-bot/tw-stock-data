# -*- coding: utf-8 -*-
"""PREREG營飆排名（台股策略線登錄 seq1 sha 6a1a8643d7e61b4a；裁定線 seq199 發號＋附則）：營飆 v1 候選多於空槽時「照排名取前」vs 抽籤。
回測線，2026-09-26。⭐ 本檔目前只有 pre 段 ＝ §一 退化檢查（⛔ 不看報酬：只數買進清單、日數、同分；⛔ 不印年化、回落）。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfRank pre [--procs 2] [--reps 200]

底：listexit_lines.setup_t1()（rerun17 快照 edc6f800、AND 訊號、t−1 大盤閘、主窗）；simulate_mtm(sig, "H120", 10, default_rng(1000＋r), …)
排名鍵（只用訊號日 k ＝ entry_pos 前一根有效 K 棒收盤前已知的資料；大者先）：
  K0 假訊號：代號最後一碼
  K1 五特徵命中數 ＝ S 表 score（research11.stock_features：c1 20 日漲 ≥ 30%、c2 20 根內漲停 ≥ 3、c3 成交額 ÷ 前 20 根均 ≥ 3、
     c4 收盤 ＞ MA100、c5 收盤 ≥ 250 根最高；全在有效 K 棒上）；本檔另用 c1～c5 加總對 score 驗
  K2 營收創高幅度 ＝ 訊號所用那一期營收 ÷ 前 24 期最高 − 1；「訊號所用那一期」＝ research13.and_flags 取的那一列
     （panel_rev.csv.gz 裡 signal_pos ≤ 訊號日的最新一列、距離 ≤ 45）；營收 ＝ research34.load_revenue（快照 mops/revenue_hist）；
     「前 24 期」＝ research34 rev_hi24 的 hist ＝ 該期之前 24 期（不含該期）
  K3 成交額倍數 ＝ 訊號日成交金額 ÷ 前 20 根有效 K 棒平均成交金額（＝ research11 amt_ratio；S 表 liq 是分母）
     ⚠ ≠ PREREGV #13 的 relvol（÷ 前 60 根中位數）；登錄字面公式是 20 根平均 ⇒ 用字面
  K4 20 日漲幅 ＝ c[k] ÷ c[k−20] − 1（還原收盤、有效 K 棒；＝ research11 ret20）；本檔另對 c1（≥ 0.30）驗
排名版的挑法（診斷用，⛔ 不改引擎）：引擎只在一處用 rng（order ＝ rng.permutation(len(cand))）⇒ 傳入一個 rng 包裝：
  照樣呼叫同顆種子的 permutation（⭐ 抽的次數與抽籤版逐日相同 ⇒「同顆種子 rng 接著抽」），再依鍵遞減穩定排序 ⇒ 同分者的先後 ＝ 那次抽籤
  （包裝從呼叫端的 cand 讀候選列；⚠ 讀呼叫端區域變數只為診斷，正式判定前要把同一個規則寫進引擎 pick 參數，見 PRE_REPORT §四）
輸出 backtest/resultsYfRank/：pre_keys.csv、pre_seeds.csv、pre_summary.json、pre_run.log、PRE_REPORT.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import research11 as R11

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYfRank")
KEYS = ["K0", "K1", "K2", "K3", "K4"]
KNAME = {"K0": "K0 代號尾數（假訊號）", "K1": "K1 飆股特徵命中數", "K2": "K2 營收創高幅度", "K3": "K3 成交額倍數（÷前 20 根均）", "K4": "K4 20 日漲幅"}
_G: dict = {}


# ─────────────────────────── 排名鍵
def build_keys(ctx, log):
    from . import research34 as R34
    sig = ctx["sig"].copy(); cal = ctx["cal"]; mk = ctx["mk"]
    sdir = os.path.join(ctx["RR"].OUT, "sig_edc6f")
    S = pd.read_csv(os.path.join(sdir, "signals_S.csv.gz"), dtype={"sid": str}, usecols=["sid", "k", "pos", "score", "c1", "c2", "c3", "c4", "c5", "liq"])
    sig = sig.merge(S, on=["sid", "k", "pos"], how="left", validate="1:1")
    chk = {"S 表對不到的訊號列": int(sig["score"].isna().sum())}
    sig["K0"] = sig["sid"].str[-1].astype(int)
    sig["K1"] = sig["score"].astype(float)
    chk["K1＝c1～c5 加總 不符"] = int((sig[["c1", "c2", "c3", "c4", "c5"]].astype(int).sum(axis=1) != sig["score"]).sum())
    k3 = []; k4 = []; liq2 = []
    for sid, g in sig.groupby("sid", sort=False):
        B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
        idx, c, amt = B["idx"], B["c"], B["amt"]
        for i, k, pos in zip(g.index, g["k"].astype(int), g["pos"].astype(int)):
            assert int(idx[k]) == pos
            den = float(np.mean(amt[k - 20:k]))
            k3.append((i, float(amt[k]) / den if den > 0 else np.nan)); liq2.append((i, den))
            k4.append((i, float(c[k] / c[k - 20] - 1.0)))
    sig["K3"] = pd.Series(dict(k3)); sig["K4"] = pd.Series(dict(k4)); sig["_liq2"] = pd.Series(dict(liq2))
    chk["K3 分母 ≠ S 表 liq（相對差 ＞ 1e−9）"] = int((np.abs(sig["_liq2"] / sig["liq"] - 1) > 1e-9).sum())
    chk["K3 ≥ 3 ⇔ c3 不符"] = int(((sig["K3"] >= 3.0) != sig["c3"].astype(bool)).sum())
    chk["K4 ≥ 0.30 ⇔ c1 不符"] = int(((sig["K4"] >= 0.30) != sig["c1"].astype(bool)).sum())
    # K2：and_flags 那一列 ⇒ 該期營收 ÷ 前 24 期最高 − 1
    pnl = pd.read_csv(os.path.join(sdir, "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos", "rev_hi24"])
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    by = {s: g.sort_values("signal_pos") for s, g in pnl.groupby("stock_id")}
    rev, _, _ = R34.load_revenue()
    periods = list(rev.index)
    k2 = []; per_used = []; bad_align = 0
    for i, sid, pos in zip(sig.index, sig["sid"], sig["pos"].astype(int)):
        g = by.get(sid)
        sp = g["signal_pos"].to_numpy(); j = int(np.searchsorted(sp, pos, side="right")) - 1
        if j < 0 or pos - sp[j] > 45 or not bool(g["rev_hi24"].iloc[j]):
            bad_align += 1; k2.append((i, np.nan)); per_used.append((i, None)); continue
        p = g["period"].iloc[j]; kk = periods.index(p)
        rv = rev[sid]; r0 = float(rv.iloc[kk]); hist = rv.iloc[kk - 24:kk].astype(float)
        k2.append((i, r0 / float(hist.max()) - 1.0 if len(hist) == 24 and hist.notna().all() and hist.max() > 0 else np.nan))
        per_used.append((i, p))
    sig["K2"] = pd.Series(dict(k2)); sig["K2_period"] = pd.Series(dict(per_used))
    chk["K2 對不到 and_flags 那一列"] = bad_align
    chk["K2 ＜ 0（與 rev_hi24 矛盾）"] = int((sig["K2"] < 0).sum())
    for k in KEYS:
        chk[f"{k} NaN"] = int(sig[k].isna().sum())
    log(f"[鍵] 訊號列 {len(sig):,}｜驗 {chk}")
    return sig, chk


# ─────────────────────────── rng 包裝（診斷用）
class RecRng:
    """抽籤版：照回同顆種子的 permutation，另記當天候選（sid, entry_pos）與名額。"""

    def __init__(self, seed):
        self.g = np.random.default_rng(seed); self.days = []

    def permutation(self, n):
        f = sys._getframe(1).f_locals
        perm = self.g.permutation(n)
        self.days.append((int(f["t"]), list(zip(f["cand"]["sid"], f["cand"]["entry_pos"].astype(int))), int(f["avail"]), perm))
        return perm


class RankRng(RecRng):
    """排名版：同一次 permutation（抽的次數與抽籤版逐日相同），再依鍵遞減穩定排序 ⇒ 同分者照抽籤先後。"""

    def __init__(self, seed, key):
        super().__init__(seed); self.key = key

    def permutation(self, n):
        f = sys._getframe(1).f_locals
        perm = self.g.permutation(n)
        cand = list(zip(f["cand"]["sid"], f["cand"]["entry_pos"].astype(int)))
        kv = np.array([self.key[c] for c in cand], float)
        kv = np.where(np.isnan(kv), -np.inf, kv)
        order = perm[np.argsort(-kv[perm], kind="stable")]
        self.days.append((int(f["t"]), cand, int(f["avail"]), order))
        return order


def _buys(au):
    return [(int(a["t"]), a["sid"]) for a in au if a["side"] == "buy"]


def _one(r):
    G = _G; ctx = G["ctx"]; N = 10
    seed = 1000 + r
    out = {"r": r}
    rg = RecRng(seed); au = []
    o = R11.simulate_mtm(ctx["sig"], "H120", N, rg, ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, audit=au)
    out["eq_sha"] = hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()[:16]
    del o
    BL = _buys(au); out["buys"] = len(BL)
    # 日數：audit 重建每個有訊號日的 持有／候選／空槽（⭐ 含槽滿、區塊沒進的日子）
    ent = G["ent"]; by_t = {}
    for a in au:
        by_t.setdefault(int(a["t"]), []).append(a)
    held = set(); d_sig = d_over = d_full = d_act = 0; elim_lot = elim_full = 0
    for t in sorted(set(by_t) | set(ent)):
        for a in by_t.get(t, []):
            if a["side"] == "sell":
                held.discard(a["sid"])
        if t in ent:
            cand = [s for s in ent[t] if s not in held]; free = N - len(held)
            d_sig += 1
            if len(cand) > free:
                d_over += 1
                if free <= 0:
                    d_full += 1; elim_full += len(cand)
                else:
                    d_act += 1; elim_lot += len(cand) - free
        for a in by_t.get(t, []):
            if a["side"] == "buy":
                held.add(a["sid"])
    out.update({"days_sig": d_sig, "days_over": d_over, "days_over_frac": d_over / d_sig, "days_full": d_full, "days_act": d_act,
                "days_act_frac": d_act / d_sig, "elim_by_lottery": elim_lot, "elim_by_full": elim_full})
    # 各鍵：同分、切點同分、抽籤路徑上的直接差、整條路徑的總差、第一次分歧
    KV = G["KV"]
    for k in KEYS:
        kv = KV[k]
        n_c = n_tie = n_cut = n_cut_tie = direct = 0
        for t, cand, avail, perm in rg.days:
            n = len(cand)
            if n <= avail:
                continue                                        # 候選 ≤ 空槽 ⇒ 排名不起作用
            v = np.array([kv[c] for c in cand], float)
            u, cnt = np.unique(v, return_counts=True)
            n_c += n; n_tie += int(cnt[cnt > 1].sum())
            srt = np.sort(v)[::-1]
            n_cut += 1; n_cut_tie += int(srt[avail - 1] == srt[avail])
            lot = {cand[i] for i in perm[:avail]}
            vv = np.where(np.isnan(v), -np.inf, v)
            rk = {cand[i] for i in perm[np.argsort(-vv[perm], kind="stable")][:avail]}
            direct += len(lot - rk)
        rr = RankRng(seed, kv); au2 = []
        o2 = R11.simulate_mtm(ctx["sig"], "H120", N, rr, ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, audit=au2)
        del o2
        BR = _buys(au2)
        sL, sR = set(BL), set(BR)
        fd = next((i for i, (x, y) in enumerate(zip(sorted(BL), sorted(BR))) if x != y), min(len(BL), len(BR)))
        mL = [kv[(s, t)] for t, s in BL]; mR = [kv[(s, t)] for t, s in BR]
        out.update({f"{k}_tie_frac": n_tie / n_c if n_c else np.nan, f"{k}_cut_tie_frac": n_cut_tie / n_cut if n_cut else np.nan,
                    f"{k}_direct_diff": direct, f"{k}_direct_frac": direct / len(BL),
                    f"{k}_path_diff": len(sL - sR), f"{k}_path_frac": len(sL - sR) / len(BL), f"{k}_buys": len(BR),
                    f"{k}_first_div_idx": fd, f"{k}_first_div_frac": fd / len(BL),
                    f"{k}_first_div_t": int(sorted(BL)[fd][0]) if fd < len(BL) else -1,
                    f"{k}_mean_key_lottery": float(np.nanmean(mL)), f"{k}_mean_key_ranked": float(np.nanmean(mR))})
    return out


def pre(a):
    global OUT
    OUT = a.out
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "pre_run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    t00 = time.time()
    log(f"===== researchYfRank pre procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）⛔ 不看報酬 =====")
    ctx = L.setup_t1(log)
    sig, chk = build_keys(ctx, log)
    sig.drop(columns=["_liq2"]).to_csv(os.path.join(OUT, "pre_keys.csv"), index=False)
    ent = {}
    for s, e in zip(sig["sid"], sig["entry_pos"].astype(int)):
        ent.setdefault(e, []).append(s)
    KV = {k: {(s, int(e)): float(v) for s, e, v in zip(sig["sid"], sig["entry_pos"], sig[k])} for k in KEYS}
    _G.update(ctx=ctx, ent=ent, KV=KV)
    ref = pd.read_csv(os.path.join(ctx["RR"].OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str})
    ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].set_index("r")
    with Pool(a.procs) as pool:
        rows = pool.map(_one, range(a.reps), chunksize=4)
    D = pd.DataFrame(rows).set_index("r").sort_index()
    gate = bool((D["eq_sha"] == ref.loc[D.index, "eq_sha"]).all())
    log(f"[閘] 抽籤版（記錄用 rng 包裝）{a.reps} 顆 eq_sha ＝ regime_t1 t1 #1：{gate}")
    D.to_csv(os.path.join(OUT, "pre_seeds.csv"))
    q = lambda s: {"中位": float(s.median()), "p10": float(s.quantile(.1)), "p90": float(s.quantile(.9)), "最小": float(s.min()), "最大": float(s.max())}  # noqa: E731
    S = {"登錄": "PREREG營飆排名 seq1 sha 6a1a8643d7e61b4a（§一 退化檢查；裁定 seq199 附則）", "⛔": "本段不含任何報酬、年化、回落", "閘_抽籤版重現": gate,
         "鍵的驗算": chk, "種子數": int(len(D)),
         "①日數": {"有訊號日": q(D["days_sig"]), "候選＞空槽日": q(D["days_over"]), "候選＞空槽日占有訊號日": q(D["days_over_frac"]),
                 "其中槽滿（空槽 0，排名不起作用）": q(D["days_full"]), "其中有作用（0＜空槽＜候選）": q(D["days_act"]),
                 "有作用日占有訊號日": q(D["days_act_frac"]), "被抽籤淘汰的候選筆數": q(D["elim_by_lottery"]), "槽滿淘汰的候選筆數": q(D["elim_by_full"])},
         "抽籤版買進筆數": q(D["buys"]), "各鍵": {}}
    for k in KEYS:
        S["各鍵"][KNAME[k]] = {"同分占比（候選＞空槽日的候選中與別檔同分）": q(D[f"{k}_tie_frac"]), "切點同分占比（有作用日）": q(D[f"{k}_cut_tie_frac"]),
                             "直接差（抽籤路徑上逐日改用排名、換掉的買進筆數）": q(D[f"{k}_direct_diff"]), "直接差占全部買進": q(D[f"{k}_direct_frac"]),
                             "整條路徑總差（排名版跑到底，抽籤版買進不在排名版的筆數）": q(D[f"{k}_path_diff"]), "總差占全部買進": q(D[f"{k}_path_frac"]),
                             "第一次分歧前的買進筆數": q(D[f"{k}_first_div_idx"]), "第一次分歧前占全部買進": q(D[f"{k}_first_div_frac"]),
                             "買到的鍵值平均：抽籤／排名（描述）": [float(D[f"{k}_mean_key_lottery"].median()), float(D[f"{k}_mean_key_ranked"].median())]}
    S["秒"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(OUT, "pre_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(json.dumps({k: v for k, v in S.items() if k != "各鍵"}, ensure_ascii=False))
    for k, v in S["各鍵"].items():
        log(f"  {k}：同分 {v['同分占比（候選＞空槽日的候選中與別檔同分）']['中位']:.3f}｜切點同分 {v['切點同分占比（有作用日）']['中位']:.3f}｜"
            f"直接差 {v['直接差（抽籤路徑上逐日改用排名、換掉的買進筆數）']['中位']:.0f}（{v['直接差占全部買進']['中位']:.3f}）｜"
            f"總差 {v['整條路徑總差（排名版跑到底，抽籤版買進不在排名版的筆數）']['中位']:.0f}（{v['總差占全部買進']['中位']:.3f}）｜"
            f"分歧前 {v['第一次分歧前的買進筆數']['中位']:.0f}")
    log(f"[完成] {time.time() - t00:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pre"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    pre(a)

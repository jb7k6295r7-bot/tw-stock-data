"""PREREGP2 落地版：類股集中度上限的成本（主要測量＝最大回落）。判準 backtest/PREREGP2.md（策略線 seq=3，sha bef83cb7ba0b78e4）。

    python3 -m backtest.researchp2 [--reps 200] [--procs 4] [--placebo-perms 20] [--placebo-seeds 30] [--out DIR]

引擎 ＝ research11.simulate_mtm（PREREGP2 加 cap_fn；預設 None 與原版逐位元相同，resultsp1/regress R1 逐種子驗）。
訊號 ＝ PREREGP1 的 AND 集合（results13b/and_signals.csv.gz，H60／H120 出場與 P1 同一份）；pick＝None（隨機，P1 的 null 規則）。
產業別 ＝ data/mops/revenue_hist 的「產業別」欄逐期面板；日 t 用【t 的月份往前兩個月】那一期（沒有就往前 ffill）；不在面板 ⇒「KY／無產業別」單獨一組。
對照：甲＝子類股 ≤2 ＋ 母類股 ≤2、乙＝無上限、丙＝只有母類股 ≤2。格＝3 × N∈{5,8,10} × H∈{60,120}＝18；判定只用 H120、N8 的三個配對。
最大回落 ＝ 日頻權益 dd = eq/cummax(eq) − 1 取 min（每個種子一條曲線，cummax 從模擬第一天起）；年化 ＝ 各種子 CAGR；
點估計 ＝ 200 種子【配對差】（同種子 乙−甲）的中位；CI ＝ 對種子 bootstrap 中位（1,000 次）；假訊號組 ＝ 把「sid→產業別」的對應在 AND 的 sid 間隨機重排再跑甲／丙。
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp2")
SEED0 = 12000                      # 種子 12000+r（r<200）；假訊號組重排 13000+k；bootstrap 12500；⛔ 與 P1（1000／3000／7000）、P3（9000／10000）、P1b（20260915+…）不重疊
USED_RANGES = [(1000, 1200), (3000, 3200), (7000, 7200), (9000, 9200), (10000, 10200), (20260915, 20261115), (20261915, 20262115)]
NS = [5, 8, 10]
HOLDS = ["H60", "H120"]
CONTROLS = ["甲", "乙", "丙"]
JUDGE_N, JUDGE_H = 8, "H120"
PAIRS = [("乙", "甲"), ("乙", "丙"), ("丙", "甲")]    # (拿掉上限那一邊, 有上限那一邊)：差 ＝ 前 − 後
MIN_MONTHS = 24
OVERLAP_MAX = 0.90
MDD_MIN_DIFF = 0.03                # 3pp（二之二①）
COST_ANCHOR = 0.00585              # H2 半寬與改善門檻（二之二②）
MAX_SUB, MAX_PAR = 2, 2
KY_LABEL = "KY／無產業別"
ELEC = {"半導體業", "電腦及週邊設備業", "光電業", "通信網路業", "電子零組件業", "電子通路業", "資訊服務業", "其他電子業"}
CHEMBIO = {"化學工業", "生技醫療業"}
LAG_MONTHS = 2                     # 量測日前兩個月可得的最近一期
RELVOL_WIN = 60                    # 本輪額外特徵（P1 的 relvol）最長回看窗；AND 本身的閘門在研究十三


def parent_of(label: str) -> str:
    if label == KY_LABEL:
        return KY_LABEL
    if label in ELEC:
        return "電子"
    if label in CHEMBIO:
        return "化學生技醫療"
    return label


# ───────────── 產業別逐期面板 → 逐日標籤 ─────────────
def load_industry_panel() -> pd.DataFrame:
    fs = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "產業別"]) for f in fs])
    df = df.dropna(subset=["產業別"]).drop_duplicates(["stock_id", "period"], keep="last")
    return df.pivot(index="period", columns="stock_id", values="產業別").sort_index()


def target_periods(cal: pd.DatetimeIndex, lag: int = LAG_MONTHS) -> list[str]:
    """日 t ⇒ 要用的期別字串（t 的月份往前 lag 個月）。"""
    out = []
    for d in cal:
        y, m = d.year, d.month - lag
        while m <= 0:
            y -= 1; m += 12
        out.append(f"{y:04d}-{m:02d}")
    return out


def daily_labels(ind: pd.DataFrame, cal: pd.DatetimeIndex, sids) -> tuple[dict, dict, list]:
    """回 (sub[sid] → 每日子類股代碼 int 陣列, par[sid] → 每日母類股代碼, vocab)；代碼 0 ＝ KY／無產業別。"""
    periods = list(ind.index); tp = target_periods(cal)
    pidx = np.searchsorted(np.array(periods), np.array(tp), side="right") - 1      # 最近一期 ≤ 目標期（-1 ＝ 沒有）
    vocab = [KY_LABEL]; code = {KY_LABEL: 0}
    sub, par = {}, {}
    for sid in sids:
        if sid in ind.columns:
            col = ind[sid].ffill().to_numpy(object)
            lab = np.array([col[i] if i >= 0 and isinstance(col[i], str) else KY_LABEL for i in pidx], dtype=object)
        else:
            lab = np.full(len(cal), KY_LABEL, dtype=object)
        s = np.empty(len(cal), dtype=np.int32); p = np.empty(len(cal), dtype=np.int32)
        for i, L in enumerate(lab):
            if L not in code:
                code[L] = len(vocab); vocab.append(L)
            s[i] = code[L]
            P_ = parent_of(L)
            if P_ not in code:
                code[P_] = len(vocab); vocab.append(P_)
            p[i] = code[P_]
        sub[sid] = s; par[sid] = p
    return sub, par, vocab


def make_cap(mode: str, sub: dict, par: dict):
    """cap_fn(sid, t, holding) → 是否可進。甲：子 ≤2 ∧ 母 ≤2；丙：母 ≤2；乙：None。"""
    if mode == "乙":
        return None

    def cap(sid, t, holding):
        ps = par[sid][t]; np_ = sum(1 for h in holding if par[h][t] == ps)
        if np_ >= MAX_PAR:
            return False
        if mode == "丙":
            return True
        ss = sub[sid][t]; ns = sum(1 for h in holding if sub[h][t] == ss)
        return ns < MAX_SUB
    return cap


# ───────────── 模擬 ─────────────
_G: dict = {}


def _init(sig, closes, opens, ncal, sub, par, rand_sigs):
    _G.update(sig=sig, closes=closes, opens=opens, ncal=ncal, sub=sub, par=par, rand=rand_sigs)


def holdings_by_day(log, ncal):
    H = [set() for _ in range(ncal)]
    for r in log:
        if r["reason"] == "in":
            for d in range(int(r["t"]), min(int(r["exit_pos"]), ncal)):
                H[d].add(r["sid"])
    return H


def overlap_jaccard(logA, logB, ncal) -> float:
    A, B = holdings_by_day(logA, ncal), holdings_by_day(logB, ncal)
    vals = []
    for a, b in zip(A, B):
        if a or b:
            vals.append(len(a & b) / len(a | b))
    return float(np.mean(vals)) if vals else np.nan


def _mdd(eq: np.ndarray, first: int, end: int) -> float:
    seg = eq[first:end]; peak = np.maximum.accumulate(seg)
    return float(((seg - peak) / peak).min())


def sim_one(args):
    """一個 (對照, N, rule, seed[, labels 覆蓋])。回 cagr／mdd／slot／m／cap 擋掉數／log。"""
    control, N, rule, seed, sub, par, sig_key = args
    sub = sub if sub is not None else _G["sub"]; par = par if par is not None else _G["par"]
    sig = _G["sig"] if sig_key is None else _G["rand"][sig_key]
    cap = make_cap(control, sub, par)
    lg = []
    s = R.simulate_mtm(sig, rule, N, np.random.default_rng(seed), _G["closes"], _G["opens"], _G["ncal"], return_equity=True, log=lg, cap_fn=cap)
    n_cap = sum(1 for r in lg if r["reason"] == "cap"); n_in = sum(1 for r in lg if r["reason"] == "in")
    return {"control": control, "N": N, "rule": rule, "seed": seed, "cagr": s["cagr"], "mdd": s["mdd"], "slot": s["slot_use"], "m": s["m"],
            "n_cap": n_cap, "n_in": n_in, "first": s["first"], "end": s["end"], "log": lg}


def boot_median_ci(x: np.ndarray, n_boot: int = 1000, seed: int = 12500) -> tuple[float, float, float]:
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed); meds = np.array([np.median(rng.choice(x, len(x), replace=True)) for _ in range(n_boot)])
    return float(np.median(x)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def judge(pair_row: dict, hw_mdd: float, hw_cagr: float, overlap: float, n_months: int) -> dict:
    """依 PREREGP2 §二：ⓐ 有效月 <24 ⇒ 還沒測；ⓑ 重疊 >90% ⇒ 不判定；H1（回落）／H2（年化）各自判。差 ＝ 拿掉上限 − 有上限。"""
    out = {}
    if n_months < MIN_MONTHS:
        out["H1"] = out["H2"] = "還沒測（有效月 < 24）"; return out
    if np.isfinite(overlap) and overlap > OVERLAP_MAX:
        out["H1"] = out["H2"] = f"不判定（重疊度 {overlap * 100:.1f}% > 90%：這條規則在本母體上幾乎不咬）"; return out
    d, lo, hi = pair_row["d_mdd"], pair_row["d_mdd_lo"], pair_row["d_mdd_hi"]
    # H1：拿掉之後回落變深 ≥ 3pp（差為負且 ≤ −0.03）且 CI 不含 0
    if np.isfinite(hw_mdd) and hw_mdd > MDD_MIN_DIFF:
        out["H1"] = f"未判定（假訊號組半寬 {hw_mdd * 100:.2f}pp > 3pp：尺太粗）"
    elif d <= -MDD_MIN_DIFF and hi < 0:
        out["H1"] = "H1 成立：測得出（拿掉上限回落變深 ≥ 3pp）"
    else:
        out["H1"] = "H1 否證：回落變深 < 3pp 或 CI 含 0"
    c, clo, chi = pair_row["d_cagr"], pair_row["d_cagr_lo"], pair_row["d_cagr_hi"]
    if np.isfinite(hw_cagr) and hw_cagr > COST_ANCHOR:
        out["H2"] = f"未判定（年化差假訊號組半寬 {hw_cagr * 100:.2f}% > 0.585%）"
    elif c > COST_ANCHOR and clo > 0:
        out["H2"] = "H2 否證：拿掉上限年化顯著變好（> 0.585% 且 CI 不含 0）"
    else:
        out["H2"] = "H2 成立：年化不顯著變好（成本低）"
    return out


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    except Exception:
        return "?"


def write_csv(df, path, stamp, commit, note=""):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# commit={commit} run={stamp} (Asia/Taipei) prereg=backtest/PREREGP2.md(sha bef83cb7ba0b78e4) seed0={SEED0} {note}\n")
        df.to_csv(fh, index=False)


def build_random_signals(AND: pd.DataFrame, closes: dict, opens: dict, pool_sids: list, rng) -> pd.DataFrame:
    """必報③ 同 N 隨機選股：同一批進場日與持有長度，sid 換成候選池裡的隨機一檔（進場日開盤與出場日收盤都要有價）。"""
    rows = []
    pool = np.array(pool_sids)
    for r in AND.itertuples():
        e = int(r.entry_pos)
        for _ in range(20):
            sid = pool[rng.integers(len(pool))]
            ok = True; rec = {"sid": sid, "entry_pos": e, "month": r.month}
            for H in HOLDS:
                x = int(getattr(r, f"xpos_{H}"))
                if x < 0 or x >= len(closes[sid]):
                    ok = False; break
                ep = float(opens[sid][e]); cx = float(closes[sid][x])
                if not (np.isfinite(ep) and ep > 0 and np.isfinite(cx) and cx > 0):
                    ok = False; break
                rec[f"xpos_{H}"] = x; rec[f"g_{H}"] = cx / ep - 1.0
            if ok:
                rows.append(rec); break
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=200); ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--placebo-perms", type=int, default=20); ap.add_argument("--placebo-seeds", type=int, default=30)
    ap.add_argument("--out", default=RESULTS)
    a = ap.parse_args()
    for lo, hi in USED_RANGES:
        assert not (lo <= SEED0 < hi or lo <= SEED0 + a.reps - 1 < hi or lo <= 13000 < hi), "種子區間與既有研究重疊"
    os.makedirs(a.out, exist_ok=True); t0 = time.time()
    stamp = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"); commit = _commit()
    log = lambda s: print(s, file=sys.stderr, flush=True)
    cal = D.load_calendar(); ncal = len(cal); uni_df = D.load_universe(); uni = uni_df.set_index("stock_id")["market"]
    AND = pd.read_csv(os.path.join(HERE, "results13b", "and_signals.csv.gz"), dtype={"sid": str})
    S = pd.read_csv(os.path.join(HERE, "results11", "signals.csv.gz"), dtype={"sid": str})
    closes, opens = P1.load_prices(set(AND["sid"]) | set(S["sid"]), cal, uni)
    AND = AND[AND["sid"].isin(closes)].reset_index(drop=True)
    ind = load_industry_panel()
    sub, par, vocab = daily_labels(ind, cal, sorted(set(AND["sid"])))
    # 閘門三件（〈八十二〉）：本輪額外特徵最長回看窗 ＝ relvol 60；AND 訊號自身的閘門在研究十三（k 最小值印出）
    kmin = int(AND["k"].min()); gate_drop = int((AND["k"] < RELVOL_WIN).sum())
    AND = AND[AND["k"] >= RELVOL_WIN].reset_index(drop=True)
    gh_p = os.path.join(a.out, "gate_history.csv"); existed = os.path.exists(gh_p)     # ⚠ 要在 open("a") 之前判，否則 open 已把檔建出來、表頭永遠寫不進去
    prev = pd.read_csv(gh_p, comment="#").iloc[-1].to_dict() if existed and len(pd.read_csv(gh_p, comment="#")) else None
    with open(gh_p, "a", encoding="utf-8") as fh:
        if not existed:
            fh.write("# 閘門逐輪計數（〈八十二〉③）：每跑一輪追加一列；⛔ 不可整份覆蓋\nstamp,commit,n_signals,gate_window,gate_dropped\n")
        fh.write(f"{stamp},{commit},{len(AND)},{RELVOL_WIN},{gate_drop}\n")
    gate_note = f"閘門：有效 K 棒 ≥ {RELVOL_WIN}（本輪特徵集最長回看窗＝relvol 60；AND 自身在研究十三已閘，k 最小 {kmin}）⇒ 擋掉 {gate_drop} 筆" + ("（本窗內觸發 0 次）" if gate_drop == 0 else "") + (f"；上一輪擋 {int(prev['gate_dropped'])} 筆（差 {gate_drop - int(prev['gate_dropped']):+d}）" if prev else "（第一輪）")
    # KY／無產業別佔比（必報⑤）
    sid_lab = {sid: vocab[sub[sid][int(e)]] for sid, e in zip(AND["sid"], AND["entry_pos"])}
    ky_share = float(np.mean([sid_lab[s] == KY_LABEL for s in AND["sid"]]))
    lab_counts = pd.Series(list(sid_lab.values())).value_counts()
    # 隨機選股（必報③）
    rng = np.random.default_rng(SEED0 + 999)
    pool_sids = sorted(closes.keys())
    rand_sigs = {"rand": build_random_signals(AND, closes, opens, pool_sids, rng)}
    log(f"AND {len(AND):,} 筆／{AND['sid'].nunique()} 檔；月 {AND['month'].min()}～{AND['month'].max()}；產業別面板 {ind.shape}；標籤 {len(vocab)} 種；KY／無產業別 {ky_share * 100:.1f}%；隨機集 {len(rand_sigs['rand']):,} 筆  {time.time() - t0:.0f}s")
    n_months = int(AND["month"].nunique())
    # 第一段：18 格 × reps 種子
    tasks = [(c, N, H, SEED0 + r, None, None, None) for c in CONTROLS for N in NS for H in HOLDS for r in range(a.reps)]
    tasks += [("乙", N, H, SEED0 + r, None, None, "rand") for N in NS for H in HOLDS for r in range(a.reps)]
    pool = Pool(a.procs, initializer=_init, initargs=(AND, closes, opens, ncal, sub, par, rand_sigs))
    res = pool.map(sim_one, tasks, chunksize=8)
    log(f"第一段 {len(res)} 次模擬 {time.time() - t0:.0f}s")
    # 整理：seeds.csv（不含 log）
    seeds = pd.DataFrame([{k: v for k, v in r.items() if k != "log"} | {"set": "rand" if i >= len(tasks) - len(NS) * len(HOLDS) * a.reps else "AND"} for i, r in enumerate(res)])
    write_csv(seeds, os.path.join(a.out, "seeds.csv"), stamp, commit)
    logs = {(r["control"], r["N"], r["rule"], r["seed"]): r["log"] for i, r in enumerate(res) if i < len(tasks) - len(NS) * len(HOLDS) * a.reps}
    # 格摘要、配對差、重疊度、觸發率、放棄組
    cells = []; pairs = []; trig_rows = []; drop_rows = []
    A = seeds[seeds["set"] == "AND"]
    for N in NS:
        for H in HOLDS:
            g = {c: A[(A.control == c) & (A.N == N) & (A.rule == H)].set_index("seed").sort_index() for c in CONTROLS}
            rnd = seeds[(seeds["set"] == "rand") & (seeds.N == N) & (seeds.rule == H)]
            for c in CONTROLS:
                d = g[c]
                cells.append({"control": c, "N": N, "H": H, "mdd_med": d["mdd"].median(), "mdd_p10": d["mdd"].quantile(0.1), "mdd_p90": d["mdd"].quantile(0.9),
                              "cagr_med": d["cagr"].median(), "cagr_p10": d["cagr"].quantile(0.1), "cagr_p90": d["cagr"].quantile(0.9), "slot_med": d["slot"].median(),
                              "m_med": d["m"].median(), "n_cap_med": d["n_cap"].median(), "n_in_med": d["n_in"].median(),
                              "rand_mdd_med": rnd["mdd"].median(), "rand_cagr_med": rnd["cagr"].median()})
            # 重疊度（甲 vs 乙、丙 vs 乙，同種子）
            ov = {}
            for c in ("甲", "丙"):
                ov[c] = np.array([overlap_jaccard(logs[(c, N, H, s)], logs[("乙", N, H, s)], ncal) for s in g["乙"].index])
            for hi_, lo_ in PAIRS:
                dm = (g[hi_]["mdd"] - g[lo_]["mdd"]).to_numpy(); dc = (g[hi_]["cagr"] - g[lo_]["cagr"]).to_numpy()
                m0, mlo, mhi = boot_median_ci(dm); c0, clo, chi = boot_median_ci(dc)
                ovv = ov["甲"] if "甲" in (hi_, lo_) else ov["丙"]
                pairs.append({"N": N, "H": H, "pair": f"{hi_}−{lo_}", "d_mdd": m0, "d_mdd_lo": mlo, "d_mdd_hi": mhi, "d_cagr": c0, "d_cagr_lo": clo, "d_cagr_hi": chi,
                              "overlap_med": float(np.nanmedian(ovv)), "n_seeds": int(len(dm))})
            # 觸發率與放棄組（甲、丙：用中位種子的 log）
            for c in ("甲", "丙"):
                d = g[c]; med_seed = int(d.index[int(np.argsort(d["mdd"].to_numpy())[len(d) // 2])])
                L = pd.DataFrame(logs[(c, N, H, med_seed)])
                if len(L):
                    per_m = L.groupby("month").apply(lambda x: pd.Series({"cap": int((x.reason == "cap").sum()), "all": int(len(x))}))
                    trig_rows.append({"control": c, "N": N, "H": H, "med_seed": med_seed, "cap_total": int((L.reason == "cap").sum()), "signals_total": int(len(L)),
                                      "trigger_rate": float((L.reason == "cap").mean()), "months_with_cap": int((per_m["cap"] > 0).sum()), "cap_per_month_med": float(per_m["cap"].median())})
                    gcol = f"g_{H}"
                    capd = L[L.reason == "cap"]; ind_ = L[L.reason == "in"]
                    drop_rows.append({"control": c, "N": N, "H": H, "n_cap": int(len(capd)), "cap_mean": float(capd[gcol].mean()) if len(capd) else np.nan,
                                      "cap_median": float(capd[gcol].median()) if len(capd) else np.nan, "n_in": int(len(ind_)), "in_mean": float(ind_[gcol].mean()) if len(ind_) else np.nan})
    cells = pd.DataFrame(cells); pairs = pd.DataFrame(pairs); trig = pd.DataFrame(trig_rows); dropped = pd.DataFrame(drop_rows)
    # 第二段：假訊號組（判定格 H120／N8）：sid→產業別 對應在 AND 的 sid 間重排，跑 甲／丙 對 乙（同種子）
    sids = sorted(set(AND["sid"])); hw_rows = []
    ptasks = []
    for k in range(a.placebo_perms):
        prng = np.random.default_rng(13000 + k); perm = prng.permutation(len(sids))
        sub_k = {sids[i]: sub[sids[perm[i]]] for i in range(len(sids))}; par_k = {sids[i]: par[sids[perm[i]]] for i in range(len(sids))}
        for c in ("甲", "丙"):
            for r in range(a.placebo_seeds):
                ptasks.append((c, JUDGE_N, JUDGE_H, SEED0 + r, sub_k, par_k, None))
    pres = pool.map(sim_one, ptasks, chunksize=4) if ptasks else []
    pool.close(); pool.join()
    log(f"第二段 假訊號組 {len(pres)} 次模擬 {time.time() - t0:.0f}s")
    yi = A[(A.control == "乙") & (A.N == JUDGE_N) & (A.rule == JUDGE_H)].set_index("seed")
    bing_real = A[(A.control == "丙") & (A.N == JUDGE_N) & (A.rule == JUDGE_H)].set_index("seed")
    if pres:
        P_ = pd.DataFrame([{k: v for k, v in r.items() if k != "log"} | {"perm": i // (2 * a.placebo_seeds)} for i, r in enumerate(pres)])
        for hi_, lo_ in PAIRS:
            meds_m, meds_c = [], []
            for k, gk in P_.groupby("perm"):
                def _side(name):
                    if name == "乙":
                        return yi.loc[gk["seed"].unique()]
                    return gk[gk.control == name].set_index("seed")
                x, y = _side(hi_), _side(lo_)
                common = x.index.intersection(y.index)
                meds_m.append(float(np.median((x.loc[common, "mdd"] - y.loc[common, "mdd"]).to_numpy())))
                meds_c.append(float(np.median((x.loc[common, "cagr"] - y.loc[common, "cagr"]).to_numpy())))
            hw_rows.append({"pair": f"{hi_}−{lo_}", "N": JUDGE_N, "H": JUDGE_H, "perms": a.placebo_perms, "seeds_per_perm": a.placebo_seeds,
                            "hw_mdd": (np.percentile(meds_m, 97.5) - np.percentile(meds_m, 2.5)) / 2, "hw_cagr": (np.percentile(meds_c, 97.5) - np.percentile(meds_c, 2.5)) / 2,
                            "band_mdd_lo": np.percentile(meds_m, 2.5), "band_mdd_hi": np.percentile(meds_m, 97.5)})
    hw = pd.DataFrame(hw_rows)
    # 判定
    jrows = []
    for r in pairs[(pairs.N == JUDGE_N) & (pairs.H == JUDGE_H)].itertuples():
        h = hw[hw.pair == r.pair].iloc[0] if len(hw) and (hw.pair == r.pair).any() else None
        jd = judge(r._asdict(), h["hw_mdd"] if h is not None else np.nan, h["hw_cagr"] if h is not None else np.nan, r.overlap_med, n_months)
        jrows.append({"pair": r.pair, "N": JUDGE_N, "H": JUDGE_H, "d_mdd_pp": r.d_mdd * 100, "ci": f"{r.d_mdd_lo * 100:+.2f}～{r.d_mdd_hi * 100:+.2f}", "d_cagr_pp": r.d_cagr * 100,
                      "hw_mdd_pp": (h["hw_mdd"] * 100 if h is not None else np.nan), "hw_cagr_pp": (h["hw_cagr"] * 100 if h is not None else np.nan), "overlap": r.overlap_med, **jd})
    J = pd.DataFrame(jrows)
    for df, name in ((cells, "cells.csv"), (pairs, "pairs.csv"), (trig, "trigger.csv"), (dropped, "dropped_cap.csv"), (hw, "placebo_halfwidth.csv"), (J, "judgement.csv")):
        write_csv(df, os.path.join(a.out, name), stamp, commit)
    # summary.md
    L = ["# PREREGP2 類股集中度上限的成本——細表", "", f"產出：{stamp}（台北）、commit {commit}；判準 `backtest/PREREGP2.md`（seq=3，sha bef83cb7ba0b78e4）；種子 {SEED0}+r（r<{a.reps}）、假訊號組重排 13000+k、bootstrap 12500；引擎 research11.simulate_mtm（cap_fn）；環境 pandas {pd.__version__}／numpy {np.__version__}。", "",
         "> ⛔ **結論第一段（依 §五①④）**：本件母體為【倖存者】（停止交易的公司在月營收面板 0 檔，資料庫線 2330）、缺口為下市公司與 KY；期間沿用 P1（AND 訊號 " + f"{AND['month'].min()}～{AND['month'].max()}" + "）⇒ 不含 2008／2000，而類股集中度的風險正是在系統性下跌時最大。", "",
         f"- {gate_note}", f"- AND {len(AND):,} 筆／{AND['sid'].nunique()} 檔、有效月 {n_months}；KY／無產業別 佔訊號 {ky_share * 100:.1f}%（必報⑤）；標籤前五：{', '.join(f'{k} {v}' for k, v in lab_counts.head(5).items())}",
         f"- 產業別＝量測日月份往前 {LAG_MONTHS} 個月那一期（ffill）；母類股映射：電子 8 業、化學生技醫療 2 業、KY 單獨、其餘各自一組（「金融保險業」「金融業」「其他」各自一組，待策略線答）。", "",
         "## 一、判定格（H120、N8；差＝拿掉上限 − 有上限；MDD 差為負＝拿掉之後回落更深）", "",
         "| 配對 | Δ最大回落中位 | 95% CI（種子 bootstrap） | Δ年化中位 | 假訊號組半寬 MDD／年化 | 重疊度 | H1 | H2 |", "|---|---:|---|---:|---|---:|---|---|"]
    for r in J.itertuples():
        L.append(f"| {r.pair} | {r.d_mdd_pp:+.2f}pp | {r.ci} | {r.d_cagr_pp:+.2f}pp | {r.hw_mdd_pp:.2f}／{r.hw_cagr_pp:.2f} | {r.overlap * 100:.1f}% | {r.H1} | {r.H2} |")
    L += ["", "## 二、18 格（200 種子中位；rand＝同 N 隨機選股，必報③）", "", "| 對照 | N | H | 最大回落中位（p10～p90） | 年化中位（p10～p90） | 槽位使用率 | 平均持倉 m | cap 擋掉／進場（中位） | 隨機選股 回落／年化 |", "|---|---:|---|---|---|---:|---:|---|---|"]
    for r in cells.itertuples():
        L.append(f"| {r.control} | {r.N} | {r.H} | {r.mdd_med * 100:.1f}%（{r.mdd_p10 * 100:.1f}～{r.mdd_p90 * 100:.1f}） | {r.cagr_med * 100:+.1f}%（{r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f}） | {r.slot_med * 100:.0f}% | {r.m_med:.0f} | {r.n_cap_med:.0f}／{r.n_in_med:.0f} | {r.rand_mdd_med * 100:.1f}%／{r.rand_cagr_med * 100:+.1f}% |")
    L += ["", "## 三、配對差（全部 18 格 × 3 配對；重疊度＝甲或丙對乙的 Jaccard 逐日平均，中位）", "", "| N | H | 配對 | ΔMDD 中位 | CI | Δ年化 | 重疊度 |", "|---:|---|---|---:|---|---:|---:|"]
    for r in pairs.itertuples():
        L.append(f"| {r.N} | {r.H} | {r.pair} | {r.d_mdd * 100:+.2f}pp | {r.d_mdd_lo * 100:+.2f}～{r.d_mdd_hi * 100:+.2f} | {r.d_cagr * 100:+.2f}pp | {r.overlap_med * 100:.1f}% |")
    L += ["", "## 四、觸發率（必報①）與放棄組（必報②，被 cap 擋掉者的後續毛報酬 vs 進場者；中位種子）", "", "| 對照 | N | H | cap 擋掉 | 訊號總數 | 觸發率 | 有 cap 的月數 | 放棄組 n／平均／中位 | 進場 n／平均 |", "|---|---:|---|---:|---:|---:|---:|---|---|"]
    for r, dr in zip(trig.itertuples(), dropped.itertuples()):
        L.append(f"| {r.control} | {r.N} | {r.H} | {r.cap_total} | {r.signals_total} | {r.trigger_rate * 100:.1f}% | {r.months_with_cap} | {dr.n_cap}／{dr.cap_mean * 100:+.1f}%／{dr.cap_median * 100:+.1f}% | {dr.n_in}／{dr.in_mean * 100:+.1f}% |")
    L += ["", "其餘：`seeds.csv`（逐種子）、`pairs.csv`、`trigger.csv`、`dropped_cap.csv`、`placebo_halfwidth.csv`、`judgement.csv`、`gate_history.csv`。⛔ 沒有任何「贏過 0050」的比較；隨機選股基準＝同進場日、同持有長度、sid 換成候選池（AND∪S 曾出現過的 {len(pool_sids)} 檔）隨機一檔，出場不套研究十三壞根規則（近似）。"]
    with open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
    log(f"完成 {time.time() - t0:.0f}s → {a.out}")


if __name__ == "__main__":
    main()

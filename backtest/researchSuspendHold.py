# -*- coding: utf-8 -*-
"""營量 v1／營飆 v1（策略鎖內）只讀盤點三：持有期內「停牌 ≥5 日後恢復」⇒ 訊號表整筆不進場 vs 照 seq255 強制出場——裁定 seq418 §三；回測線計算子代理。
⭐ 只讀盤點、描述、⛔ 不改標籤、⛔ 不計 N。⛔ 不改任何鎖內檔／既有檔（鎖內函式只呼叫）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSuspendHold [--procs 3]

═══ 讀法（寫於 2026-10-21（台北），在算任何本件數字之前；⚠ 本線看過：盤點一 resultsDelistHold 的分類筆數（停牌≥5日後恢復 營量 15、營飆 32 列，
    交件時誤寫成「共 42 筆」，本件以程式重數為準）；本件新數字一個都沒看過）═══
 定版路徑 ＝ researchYL_integrate.main_world／early_world ＋ IG.eng（營量 H60·S20·無·relvol r0；營飆 H120·S10·閘·抽籤 r0～199），同盤點一
 對象列（同盤點一分類「壞根（資料續存）」且壞根類型「停牌≥5日後恢復」）：窗內 AND 列、xpos_H＜0、exit_pos(k+1,H) ＜ n（出場根有資料）、
   k−20 起第一個壞根 j0 的前一段停牌 ≥5 個交易日（idx[j0] − idx[j0−1] − 1 ≥ 5）；營量看 H60、營飆看 H120 且閘開（t−1）
 讀法甲（主；seq255 原文「停止交易／下市 ⇒ 最後有效收盤後第一個交易日、以最後收盤強制出場、扣成本」，恢復交易後不再追回）：
   L ＝ idx[j0−1]（停牌前最後一根有效收盤）；若 j0 − 1 ≥ k＋1（進場後才停牌）⇒ xpos ＝ L＋1、g ＝ closes[L] ÷ opens[進場] − 1
   （＝ simulate_mtm stop_force 那一行的同式：第 L＋1 天以 L 收盤出場、照一般出場入帳扣成本；用 W 的 closes／opens 陣列）
   若 j0 ＝ k＋1（停牌在訊號日與進場日之間、進場日就是復牌日）⇒ 持有期間沒有停牌 ⇒ 甲與乙同式（見乙），另列筆數
 讀法乙（並列描述：恢復後照原 H 持有到期）：只忽略「停牌 ≥5 日」那一類壞根（其他壞根：幽靈除權、斷點照舊 ⇒ 仍不進）；
   出場 ＝ fixed_exit(o, c, k, H, nb′)，nb′ ＝ k−20 起第一個「非停牌類」壞根；同一根同時是停牌又是其他壞根 ⇒ 算停牌類（照記）；
   出場根超過資料 ⇒ 照 T1 資料尾補（最後一根 ＝ 日曆尾才補，否則仍不進）；H 是持有的有效 K 棒數（停牌日不算）
   早年世界再照原路徑套 R8 減資截斷（exits_for 的 EVD 同式；乾跑後補：早年定版對有出場的列本來就套 R8，乙要同路徑）
   ⚠ 乙跨過停牌那一段的還原價（多為減資換股停牌）⇒ 報酬受斷點還原品質影響，只當描述；甲只用停牌前價格
 只改上述列的 xpos／g；其餘列、種子、引擎參數一律不動；先跑不改任何東西的重現版 ⇒ eq_sha 與各段年化回落 ＝ resultsYL_integrate（閘 R），
   主世界另對 T1fix c13／c1（閘 T）
 報：明細（代號、名稱、訊號日、進場日、停牌起訖、復牌日、停牌日數、甲出場日與淨報酬、乙出場日與淨報酬）；
   各段 年化、回落、比值（年化 ÷ |回落|）、對 0050 標籤（IG.label）；營飆 200 顆中位與同顆配對差中位；實際買進的補回列
輸出 backtest/resultsSuspendHold/：rows.csv、seeds.csv.gz、cells.csv、summary.json、REPORT.md、run.log
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

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR                           # noqa: E402

RR.use_snapshot()
from backtest import data as D                               # noqa: E402
from backtest import research11 as R                         # noqa: E402
from backtest import researchYL_integrate as IG              # noqa: E402

TIME = "2026-10-21（台北）"
OUT = "backtest/resultsSuspendHold"
NSEED = 200
if os.environ.get("SSH_QUICK"):
    NSEED, OUT = 3, "/tmp/ssh_quick"
COST = R.COST
SEQ255 = ("引擎缺口（停止交易後凍結價續抱）：核准進共用引擎閘門 ⇒ 停止交易／下市 ⇒ 最後有效收盤後第一個交易日、以最後收盤強制出場、扣成本。"
          "適用之後所有新跑件（裁定線 2026-09-27 20:50 §一 4）")
STRAT = {"營量": (IG.YL, 60, False), "營飆": (IG.YF, 120, True)}
VARS = (("O", "定版（重現）"), ("甲", "甲 seq255 停牌強制出場"), ("乙", "乙 復牌後照原 H 持有"))
WORD = "只讀盤點、描述、不改標籤、不計 N"
_W: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def sha16(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def seg_of(W, e):
    for sg, (x, y) in W["segp"].items():
        if sg != "主窗" and x <= e <= y:
            return sg
    return "窗外"


def early_evd(cal):
    """早年 R8 事件 {sid: [(pe, pL)]}（researchYL_integrate.early_world 同式）。"""
    from backtest import researchEarlyOTC_rerun as EO
    EV = EO.events("O", "W_B", IG.MSHA)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(cal)}
    EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    return EVD


def find_rows(W, names, log, evd=None):
    D.DATA = W["data"]
    cal = W["cal"]; ncal0 = len(cal); base = W["base"]; reg = W["reg"]
    rows = []; bars = {}; pc = {}
    for stg, (key, H, G) in STRAT.items():
        for i in base.index[base[f"xpos_H{H}"] < 0]:
            s = base.at[i, "sid"]; k = int(base.at[i, "k"]); e_ = int(base.at[i, "entry_pos"]); p_ = int(base.at[i, "pos"])
            if G and not bool(reg[e_ - 1]):
                continue
            if s not in bars:
                bars[s] = R.load_bars(s, W["uni"].get(s, "twse"), cal)
            B = bars[s]
            if B is None:
                continue
            idx, nb, o, c = B["idx"], B["next_bad"], B["o"], B["c"]; n = len(idx)
            if k >= n or int(idx[k]) != p_:
                continue
            ex = D.exit_pos(k + 1, H); j0 = int(nb[max(0, k - 20)])
            if not (ex < n and j0 <= n - 1 and j0 > 0):
                continue
            gp = int(idx[j0] - idx[j0 - 1] - 1)
            if gp < 5:
                continue
            bad = np.zeros(n, bool); bad[np.flatnonzero(nb[:n] == np.arange(n))] = True
            gapb = np.zeros(n, bool); gapb[1:] = (np.diff(idx) - 1) >= 5
            other = bad & ~gapb
            nb2 = np.full(n + 1, n + 10, int)
            for j in range(n - 1, -1, -1):
                nb2[j] = j if other[j] else nb2[j + 1]
            rec = {"世界": W["name"], "策略": stg, "H": H, "idx": int(i), "sid": s, "名稱": names.get(s, ""), "k": k, "entry_pos": e_,
                   "訊號日": str(cal[p_].date()), "進場日": str(cal[e_].date()), "段": seg_of(W, e_), "閘開": bool(reg[e_ - 1]),
                   "停牌前末根日": str(cal[int(idx[j0 - 1])].date()), "停牌起": str(cal[int(idx[j0 - 1]) + 1].date()), "停牌迄": str(cal[int(idx[j0]) - 1].date()),
                   "復牌日": str(cal[int(idx[j0])].date()), "停牌交易日數": gp, "停牌在進場前": bool(j0 == k + 1),
                   "持有第幾根停牌": int(j0 - 1 - k), "持有期內停牌段數": int(gapb[k + 1:ex + 1].sum())}
            # 乙
            nb2k = int(nb2[max(0, k - 20)])
            r = R.fixed_exit(o, c, k, H, nb2k)
            if r:
                xb, gb = int(idx[r[0]]), float(r[1]); how = "照原 H"
            elif ex >= n and nb2k > n - 1 and int(idx[n - 1]) == ncal0 - 1:
                xb, gb = ncal0, float(c[n - 1] / o[k + 1] - 1.0); how = "T1 資料尾"
            else:
                xb, gb = -1, np.nan; how = "仍不進（其他壞根）"
            if evd and s in evd and xb >= 0:                       # 早年 R8 減資截斷（researchYL_integrate.exits_for 同式）
                if s not in pc:
                    st = D.load_stock(s, "twse", cal); pc[s] = (st.df["open"].to_numpy(float), st.df["close"].to_numpy(float))
                of_, cf_ = pc[s]
                for pe, pL in evd[s]:
                    if xb >= 0 and e_ <= pL and xb >= pe:
                        xb = pL; gb = float(cf_[pL] / of_[e_] - 1.0); how = "R8 減資截斷"
            rec.update({"乙_xpos": xb, "乙_g": gb, "乙_方式": how, "乙_出場日": (str(cal[xb].date()) if 0 <= xb < ncal0 else ("資料尾" if xb == ncal0 else "—"))})
            # 甲
            if j0 - 1 >= k + 1:
                L = int(idx[j0 - 1])
                ga = float(W["closes"][s][L]) / float(W["opens"][s][e_]) - 1.0
                rec.update({"甲_xpos": L + 1, "甲_g": ga, "甲_方式": "停牌強制出場", "甲_出場日": str(cal[L + 1].date()),
                            "甲_g_bars": float(c[j0 - 1] / o[k + 1] - 1.0)})
            else:
                rec.update({"甲_xpos": xb, "甲_g": gb, "甲_方式": "停牌在進場前⇒同乙", "甲_出場日": rec["乙_出場日"], "甲_g_bars": np.nan})
            rec["甲_淨"] = rec["甲_g"] - COST; rec["乙_淨"] = rec["乙_g"] - COST
            rows.append(rec)
    df = pd.DataFrame(rows)
    log(f"[對象 {W['name']}] {len(df)} 列｜" + json.dumps({f"{a}|{b}": int(v) for (a, b), v in df.groupby(["策略", "段"]).size().items()} if len(df) else {}, ensure_ascii=False))
    return df


def make_var(W, df, v):
    bv = W["base"].copy(); keys = {60: set(), 120: set()}
    if len(df):
        for _, r in df[df["世界"] == W["name"]].iterrows():
            H = int(r["H"]); x = int(r[f"{v}_xpos"])
            if x < 0:
                continue
            bv.at[int(r["idx"]), f"xpos_H{H}"] = x; bv.at[int(r["idx"]), f"g_H{H}"] = float(r[f"{v}_g"])
            keys[H].add((r["sid"], int(r["entry_pos"])))
    Wv = dict(W); Wv["base"] = bv
    Wv["SIG"] = {G: (bv[W["reg"][bv["entry_pos"].to_numpy() - 1]] if G else bv) for G in IG.GS}
    Wv["RESC"] = keys
    return Wv


def run_seed(args):
    wk, stg, r = args
    W = _W[wk]; key, H, G = STRAT[stg]
    o, au = IG.eng(W, key, r)
    eq = np.asarray(o["equity"], float)
    row = {"世界鍵": wk, "策略": stg, "r": r, "eq_sha": sha16(eq), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])}
    for sg, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    KEYS = W.get("RESC", {}).get(H, set()); nb_, nets, op = 0, [], {}
    for a in au:
        if a["side"] == "buy":
            op[a["sid"]] = (a["t"], a["px"])
        else:
            tb, pb = op.pop(a["sid"])
            if (a["sid"], tb) in KEYS:
                nb_ += 1; nets.append(a["px"] / pb - 1.0 - COST)
    nb_ += sum(1 for s, (tb, pb) in op.items() if (s, tb) in KEYS)
    row["補回買進"] = nb_; row["補回淨報酬和"] = float(np.sum(nets)) if nets else 0.0; row["補回勝"] = int(np.sum(np.array(nets) > 0)) if nets else 0
    return row


def sims(wk, procs):
    jobs = [(wk, "營量", 0)] + [(wk, "營飆", r) for r in range(NSEED)]
    with Pool(procs) as p:
        return p.map(run_seed, jobs, chunksize=4)


def sgn(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}｜快照 {RR.SHA[:10]}")
    S_ = {"讀法寫死": TIME, "性質": WORD, "seq255原文": SEQ255, "快照": RR.SHA, "閘": {}}
    Wm, gm = IG.main_world(log)
    names = pd.read_csv(os.path.join(Wm["data"], "meta", "stocks.csv"), dtype=str).set_index("stock_id")["name"].to_dict()
    We, ge = IG.early_world(log, a.procs)
    try:
        names = {**pd.read_csv(os.path.join(We["data"], "meta", "stocks.csv"), dtype=str).set_index("stock_id")["name"].to_dict(), **names}
    except Exception:
        pass
    S_["世界閘"] = {"主": gm, "早年": ge}
    WS = {"主": Wm, "早年": We}
    D.DATA = We["data"]
    df = pd.concat([find_rows(Wm, names, log), find_rows(We, names, log, evd=early_evd(We["cal"]))], ignore_index=True)
    df.to_csv(os.path.join(OUT, "rows.csv"), index=False, encoding="utf-8-sig")
    for wn, W in WS.items():
        _W[wn] = W
        for v in ("甲", "乙"):
            _W[f"{wn}_{v}"] = make_var(W, df, v)
    ROWS = []
    for wk in ("主", "主_甲", "主_乙", "早年", "早年_甲", "早年_乙"):
        ROWS += sims(wk, a.procs)
        log(f"[模擬 {wk}] 完成")
    SE = pd.DataFrame(ROWS)
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # 對帳
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    for wn in WS:
        for stg, (key, H, G) in STRAT.items():
            mine = SE[(SE["世界鍵"] == wn) & (SE["策略"] == stg)].set_index("r"); rr = ref[(ref["世界"] == wn) & (ref["格"] == key)].set_index("r")
            bad = 0
            for r in mine.index:
                if r not in rr.index or mine.at[r, "eq_sha"] != rr.at[r, "eq_sha"]:
                    bad += 1; continue
                for sg in WS[wn]["segp"]:
                    for k_ in ("年化", "回落"):
                        bad += int(repr(float(mine.at[r, f"{sg}_{k_}"])) != repr(float(rr.at[r, f"{sg}_{k_}"])))
            S_["閘"][f"R{wn}_{stg} 重現 ＝ resultsYL_integrate（不同項數，{len(mine)} 顆）"] = int(bad)
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    yl0 = SE[(SE["世界鍵"] == "主") & (SE["策略"] == "營量")].iloc[0]
    S_["閘"]["T1 營量 主 ＝ T1fix c13 t1 r0"] = int(yl0["eq_sha"] != c13["eq_sha"] or repr(float(yl0["主窗_年化"])) != repr(float(c13["cagr"])))
    r1 = t1[(t1["key"] == "c1") & (t1["var"] == "t1")].set_index("r"); m1 = SE[(SE["世界鍵"] == "主") & (SE["策略"] == "營飆")].set_index("r")
    S_["閘"]["T2 營飆 主 ＝ T1fix c1 t1（不同顆數）"] = int(sum(m1.at[r, "eq_sha"] != r1.at[r, "eq_sha"] for r in m1.index))
    S_["閘"]["T3 定版跑中買到對象列（理應 0）"] = int(SE[SE["世界鍵"].isin(list(WS))]["補回買進"].sum())
    log(f"[閘] {S_['閘']}")
    # 彙總
    C = []
    for wn, W in WS.items():
        for stg in STRAT:
            g0 = SE[(SE["世界鍵"] == wn) & (SE["策略"] == stg)].set_index("r")
            for v, lab in VARS:
                g = SE[(SE["世界鍵"] == (wn if v == "O" else f"{wn}_{v}")) & (SE["策略"] == stg)].set_index("r")
                for sg in W["segp"]:
                    b = W["b50"][sg]; c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                    c0, m0 = float(g0[f"{sg}_年化"].median()), float(g0[f"{sg}_回落"].median())
                    C.append({"世界": wn, "策略": stg, "段": sg, "變體": lab, "顆數": len(g), "年化": c_, "回落": m_, "比值": c_ / abs(m_), "對0050": IG.label(c_, m_, b),
                              "Δ年化": c_ - c0, "Δ回落": m_ - m0, "Δ比值": c_ / abs(m_) - c0 / abs(m0), "標籤變": IG.label(c_, m_, b) != IG.label(c0, m0, b),
                              "配對差年化_中位": float((g[f"{sg}_年化"] - g0.loc[g.index, f"{sg}_年化"]).median()),
                              "年化有變顆數": int((g[f"{sg}_年化"] != g0.loc[g.index, f"{sg}_年化"]).sum()),
                              "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"]), "補回買進_平均": float(g["補回買進"].mean())})
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S_["表"] = C.to_dict("records")
    TR = {}
    for wk in ("主_甲", "主_乙", "早年_甲", "早年_乙"):
        for stg in STRAT:
            g = SE[(SE["世界鍵"] == wk) & (SE["策略"] == stg)]; nb_ = g["補回買進"].sum()
            TR[f"{wk}|{stg}"] = {"每條補回買進（平均）": float(g["補回買進"].mean()), "顆數有買到": int((g["補回買進"] > 0).sum()),
                                 "淨報酬平均（已出場）": float(g["補回淨報酬和"].sum() / nb_) if nb_ else np.nan, "勝率": float(g["補回勝"].sum() / nb_) if nb_ else np.nan}
    S_["補回交易"] = TR
    S_["對象筆數"] = {f"{a}|{b}|{c}": int(v) for (a, b, c), v in df.groupby(["世界", "策略", "段"]).size().items()} if len(df) else {}
    S_["完成（台北）"] = now_tpe()
    json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(S_, C, df)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    log("\n" + C[C["段"] != "主窗"][["世界", "策略", "段", "變體", "年化", "回落", "比值", "對0050", "Δ年化", "Δ回落", "Δ比值", "配對差年化_中位", "年化有變顆數", "補回買進_平均"]].to_string(index=False))
    bad = [k for k, v in S_["閘"].items() if v != 0]
    if bad:
        log(f"⛔ 閘不過 {bad}"); raise SystemExit(1)
    log(f"[完] {now_tpe()}（台北）")


def report(S, C, df):
    L = ["# 只讀盤點三：持有期內停牌 ≥5 日後恢復（營量 v1、營飆 v1）", "", f"產出 {S['完成（台北）']}（台北）。回測線計算子代理。⭐ {WORD}。⛔ 鎖內檔一字未改。", "",
         f"seq255 原文：{S['seq255原文']}", "", "## ① 明細（營量 H60；營飆 H120 且閘開；淨報酬已扣 0.585%）", "",
         "| 世界 | 策略 | 段 | 代號 | 名稱 | 訊號日 | 進場日 | 停牌起～迄 | 復牌日 | 停牌交易日 | 甲 出場日 | 甲 淨報酬 | 乙 出場日 | 乙 淨報酬 | 備註 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in df.sort_values(["世界", "策略", "進場日"]).iterrows():
        L.append(f"| {r['世界']} | {r['策略']} | {r['段']} | {r['sid']} | {r['名稱']} | {r['訊號日']} | {r['進場日']} | {r['停牌起']}～{r['停牌迄']} | {r['復牌日']} | {r['停牌交易日數']} | "
                 f"{r['甲_出場日']} | {sgn(r['甲_淨'])} | {r['乙_出場日']} | {sgn(r['乙_淨'])} | {r['甲_方式']}；乙 {r['乙_方式']} |")
    L += ["", "## ② 組合層（營飆 200 顆中位；比值 ＝ 年化 ÷ |回落|；Δ 對定版）", "",
          "| 世界 | 策略 | 段 | 變體 | 年化 | 回落 | 比值 | 對 0050 | Δ年化 | Δ回落 | Δ比值 | 配對差中位 | 年化有變顆數 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in C[C["段"] != "主窗"].iterrows():
        L.append(f"| {r['世界']} | {r['策略']} | {r['段']} | {r['變體']} | {sgn(r['年化'])} | {sgn(r['回落'])} | {r['比值']:.3f} | {r['對0050']}{'（變）' if r['標籤變'] else ''} | "
                 f"{sgn(r['Δ年化'], 2)} | {sgn(r['Δ回落'], 2)} | {r['Δ比值']:+.3f} | {sgn(r['配對差年化_中位'], 2)} | {r['年化有變顆數']}／{r['顆數']} |")
    L += ["", "## ③ 補回列實際買進", "", "```", json.dumps(S["補回交易"], ensure_ascii=False, indent=1, default=float), "```", "",
          "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "", f"⭐ {WORD}。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

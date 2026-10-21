# -*- coding: utf-8 -*-
"""營量 v1／營飆 v1（策略鎖內）只讀盤點一：「持有期內下市 ⇒ 整筆不進場」vs 裁定 seq255「停止交易強制出場」——裁定 seq412 §二；回測線計算子代理。
⭐ 只讀盤點、描述、⛔ 不改標籤、⛔ 不計 N。⛔ 不改任何鎖內檔／既有檔（全部在本檔內處理，鎖內函式只呼叫不改）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDelistHold [--procs 3]

═══ 讀法（寫於 2026-10-21（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1、營飆 v1 定版各段年化／回落（resultsYL_integrate、resultsDelistRev）；本件新數字一個都沒看過）═══
 seq255 原文（裁定線 2026-09-27 20:50 §一 4）：「引擎缺口（停止交易後凍結價續抱）：核准進共用引擎閘門 ⇒ 停止交易／下市 ⇒ 最後有效收盤後第一個交易日、
   以最後收盤強制出場、扣成本。適用之後所有新跑件」；落地 ＝ research11.simulate_mtm(stop_force＝{sid: L})，L ＝ 最後一根有效收盤（stop_force_days）
 定版路徑 ＝ researchYL_integrate.main_world／early_world ＋ IG.eng（營量 H60·S20·無·relvol r0；營飆 H120·S10·閘·抽籤 r0～199），兩者都已帶 stop_force＝W["SF"]
   ⇒ 但 AND 表 xpos＜0 的列在 simulate_mtm 開頭就被丟掉（d[xpos ≥ 0]），stop_force 只作用在「已持有」部位 ⇒ 持有期內下市的訊號整筆不進場
 段 ＝ 主世界 探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（另附主窗）；早年世界 2005-02-01～2014-12-31（上市＋上櫃 W_B 版面）
 xpos＜0 原因分類（每列、每個 H；R.load_bars 有效 K 棒；k ＝ 訊號根；n ＝ 有效根數；nb ＝ k−20 起第一個壞根）：
   ・壞根（資料續存）：exit_pos(k+1,H) ＜ n（出場根還有資料，但出場前有壞根）⇒ 不是下市，⛔ 不在本件
   ・持有期內下市（純）：exit_pos ≥ n、k−20 之後無壞根、最後一根不在日曆尾 ⇒ ⭐ 本件主體
   ・持有期內壞根＋下市：exit_pos ≥ n、但 (k, n−1] 內有壞根 ⇒ 另列筆數與明細，⛔ 不進假設版（壞根規則 seq335 照舊判壞）
   ・壞根（資料到日曆尾）：exit_pos ≥ n、有壞根、最後一根 ＝ 日曆尾 ⇒ 不是下市（2026-10-21 跑後補分這一類：首跑把它併在「資料尾」，筆數與結論不變）
   ・資料尾：最後一根 ＝ 日曆尾且無壞根（T1 已補，理應 0 筆）；其他：讀不到 K 棒／k↔pos 不符
   另報壞根類型：壞根前停牌 ≥5 日 ⇒「停牌≥5日後恢復」；否則該根是 adj 事件根 ⇒「除權息日（幽靈判定）」；否則「斷點（面額／減資等）」
 假設版（seq255 照字面）：只改「持有期內下市（純）」列 ⇒ 讓它進訊號表：
   xpos ＝ L＋2（佔位，＞ L＋1 ⇒ 引擎在第 L＋1 天由 stop_force 以 closes[L] ÷ 進場開盤 − 1 出場並扣成本）、g ＝ 同值（佔位）；
   L 必須 ＝ W["SF"][sid]（stop_force_days 的 L）；不符或不在 SF（L ≥ 窗尾）⇒ 直接 xpos ＝ L＋1、g ＝ closes[L]／opens[進場] − 1（機械上同式），另報筆數
   其餘列、種子、引擎參數一律不動
 對帳（必過才算假設版）：不改任何東西的重現版 ⇒ 兩世界 營量 r0、營飆 r0～199 的 eq_sha／各段年化回落 repr ＝ resultsYL_integrate/seeds.csv.gz；
   主世界 營量 r0 ＝ resultsT1fix c13 t1 r0；營飆 ＝ T1fix c1 t1（主窗）
 報：各段筆數明細（代號、名稱、訊號日、進場日、末根日、閘）；假設版 vs 定版：年化、回落、比值（年化 ÷ |回落|）、對 0050 標籤（IG.label）；
   營飆 200 顆中位〔p10～p90〕與同顆配對差中位；實際買進的補回列筆數、淨報酬、stop_force 筆數
輸出 backtest/resultsDelistHold/：rows.csv（xpos＜0 全分類）、delist_rows.csv、seeds.csv.gz、cells.csv、summary.json、REPORT.md、run.log
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
OUT = "backtest/resultsDelistHold"
NSEED = 200
if os.environ.get("DLH_QUICK"):
    NSEED, OUT = 3, "/tmp/dlh_quick"
COST = R.COST
SEQ255 = ("引擎缺口（停止交易後凍結價續抱）：核准進共用引擎閘門 ⇒ 停止交易／下市 ⇒ 最後有效收盤後第一個交易日、以最後收盤強制出場、扣成本。"
          "適用之後所有新跑件（裁定線 2026-09-27 20:50 §一 4）")
STRAT = {"營量": (IG.YL, 60, False), "營飆": (IG.YF, 120, True)}
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


# ═════════════ 分類 ═════════════
def classify(W, names, log):
    D.DATA = W["data"]
    cal = W["cal"]; ncal0 = len(cal); base = W["base"]; reg = W["reg"]
    rows = []; bars = {}
    for H in (60, 120):
        for i in base.index[base[f"xpos_H{H}"] < 0]:
            s = base.at[i, "sid"]; k = int(base.at[i, "k"]); e_ = int(base.at[i, "entry_pos"]); p_ = int(base.at[i, "pos"])
            if s not in bars:
                B = R.load_bars(s, W["uni"].get(s, "twse"), cal)
                bars[s] = None if B is None else (B["idx"], B["next_bad"], B["o"], B["c"], B["ev_bar"])
            rec = {"世界": W["name"], "H": H, "idx": int(i), "sid": s, "名稱": names.get(s, ""), "k": k, "pos": p_, "entry_pos": e_,
                   "訊號日": str(cal[p_].date()), "進場日": str(cal[e_].date()), "段": seg_of(W, e_), "閘開": bool(reg[e_ - 1])}
            b = bars[s]
            if b is None:
                rec["原因"] = "其他：讀不到K棒"; rows.append(rec); continue
            idx, nb, o, c, evb = b; n = len(idx)
            if k >= n or int(idx[k]) != p_:
                rec["原因"] = "其他：k↔pos不符"; rows.append(rec); continue
            ex = D.exit_pos(k + 1, H); nbk = int(nb[max(0, k - 20)]); L = int(idx[n - 1])
            rec.update({"末根pos": L, "末根日": str(cal[L].date()), "持有根數到末根": int(n - 1 - k), "壞根pos": (int(idx[nbk]) if nbk <= n - 1 else -1)})
            if nbk <= n - 1:
                gp = int(idx[nbk] - idx[nbk - 1] - 1) if nbk > 0 else 0
                rec["壞根日"] = str(cal[int(idx[nbk])].date()); rec["壞根前停牌日數"] = gp
                rec["壞根類型"] = "停牌≥5日後恢復" if gp >= 5 else ("除權息日（幽靈判定）" if bool(evb[nbk]) else "斷點（面額／減資等）")
            if ex < n:
                rec["原因"] = "壞根（資料續存）"
            elif nbk <= n - 1:
                rec["原因"] = "壞根（資料到日曆尾）" if L >= ncal0 - 1 else "持有期內壞根＋下市"
            elif L >= ncal0 - 1:
                rec["原因"] = "資料尾"
            else:
                rec["原因"] = "持有期內下市（純）"
                rec["g_bars"] = float(c[n - 1] / o[k + 1] - 1.0)
            rows.append(rec)
    df = pd.DataFrame(rows)
    log(f"[分類 {W['name']}] xpos＜0 {len(df)} 列｜" + json.dumps({f"H{a}|{b}": int(v) for (a, b), v in df.groupby(["H", "原因"]).size().items()} if len(df) else {}, ensure_ascii=False, default=str))
    return df


def make_variant(W, cls, H, log):
    """回 (base_v, 補回鍵 {(sid, entry_pos)}, 明細)。只改 H 欄、只改「持有期內下市（純）」列。"""
    bv = W["base"].copy(); keys = set(); det = []
    sub = cls[(cls["H"] == H) & (cls["原因"] == "持有期內下市（純）")] if len(cls) else cls
    for _, r in sub.iterrows():
        i, s, L, e_ = int(r["idx"]), r["sid"], int(r["末根pos"]), int(r["entry_pos"])
        cl = float(W["closes"][s][L]); op = float(W["opens"][s][e_])
        g = cl / op - 1.0
        sfL = W["SF"].get(s)
        mode = "stop_force" if sfL == L else "直接 L＋1"
        bv.at[i, f"xpos_H{H}"] = (L + 2) if mode == "stop_force" else (L + 1)
        bv.at[i, f"g_H{H}"] = g
        keys.add((s, e_))
        det.append({"世界": W["name"], "H": H, "sid": s, "entry_pos": e_, "L": L, "SF_L": (-1 if sfL is None else int(sfL)), "方式": mode,
                    "g_seq255": g, "g_bars": r.get("g_bars", np.nan), "淨報酬": g - COST})
    return bv, keys, pd.DataFrame(det)


# ═════════════ 模擬 ═════════════
def run_seed(args):
    wk, stg, r = args
    W = _W[wk]; key, H, G = STRAT[stg]
    o, au = IG.eng(W, key, r)
    eq = np.asarray(o["equity"], float)
    row = {"世界鍵": wk, "策略": stg, "r": r, "eq_sha": sha16(eq), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"]),
           "stop_force_n": int(o.get("x_stop_force_n", -1))}
    for sg, (x, y) in W["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    KEYS = W.get("RESC", {}).get(H, set())
    nb_, nets = 0, []
    op = {}
    for a in au:
        if a["side"] == "buy":
            op[a["sid"]] = (a["t"], a["px"])
        else:
            tb, pb = op.pop(a["sid"])
            if (a["sid"], tb) in KEYS:
                nb_ += 1; nets.append(a["px"] / pb - 1.0 - COST)
    for s, (tb, pb) in op.items():
        if (s, tb) in KEYS:
            nb_ += 1
    row["補回買進"] = nb_; row["補回淨報酬和"] = float(np.sum(nets)) if nets else 0.0; row["補回勝"] = int(np.sum(np.array(nets) > 0)) if nets else 0
    return row


def sims(wk, procs):
    jobs = [(wk, "營量", 0)] + [(wk, "營飆", r) for r in range(NSEED)]
    with Pool(procs) as p:
        return p.map(run_seed, jobs, chunksize=4)


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
        names_e = pd.read_csv(os.path.join(We["data"], "meta", "stocks.csv"), dtype=str).set_index("stock_id")["name"].to_dict()
    except Exception:
        names_e = {}
    names_all = {**names_e, **names}
    S_["世界閘"] = {"主": gm, "早年": ge}
    WS = {"主": Wm, "早年": We}
    CLS = {}
    for wn, W in WS.items():
        CLS[wn] = classify(W, names_all, log)
    cls_all = pd.concat(CLS.values(), ignore_index=True)
    cls_all.to_csv(os.path.join(OUT, "rows.csv"), index=False, encoding="utf-8-sig")
    # 變體世界
    DET = []
    for wn, W in list(WS.items()):
        Wv = dict(W); RESC = {}
        bv = W["base"]
        for stg, (key, H, G) in STRAT.items():
            bH, keys, det = make_variant(dict(W, base=bv), CLS[wn], H, log)
            bv = bH; RESC[H] = keys
            if len(det):
                DET.append(det)
        Wv["base"] = bv
        Wv["SIG"] = {G: (bv[W["reg"][bv["entry_pos"].to_numpy() - 1]] if G else bv) for G in IG.GS}
        Wv["RESC"] = RESC
        W["RESC"] = RESC          # 定版也數「同一批鍵」買進數（理應 0）
        _W[wn] = W; _W[wn + "_v"] = Wv
    det_all = pd.concat(DET, ignore_index=True) if DET else pd.DataFrame()
    det_all.to_csv(os.path.join(OUT, "delist_rows.csv"), index=False, encoding="utf-8-sig")
    log(f"[補回列] {len(det_all)}｜方式 {det_all['方式'].value_counts().to_dict() if len(det_all) else {}}")
    ROWS = []; T0 = time.time()
    for wk in ("主", "主_v", "早年", "早年_v"):
        D.DATA = _W[wk]["data"]
        ROWS += sims(wk, a.procs)
        log(f"[模擬 {wk}] 完成｜{time.time() - T0:.0f}s")
    SE = pd.DataFrame(ROWS)
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # ── 對帳 ──
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    for wn in ("主", "早年"):
        for stg, (key, H, G) in STRAT.items():
            mine = SE[(SE["世界鍵"] == wn) & (SE["策略"] == stg)].set_index("r")
            rr = ref[(ref["世界"] == wn) & (ref["格"] == key)].set_index("r")
            bad = 0
            for r in mine.index:
                if r not in rr.index:
                    bad += 1; continue
                if mine.at[r, "eq_sha"] != rr.at[r, "eq_sha"]:
                    bad += 1; continue
                for sg in _W[wn]["segp"]:
                    for k_ in ("年化", "回落"):
                        if repr(float(mine.at[r, f"{sg}_{k_}"])) != repr(float(rr.at[r, f"{sg}_{k_}"])):
                            bad += 1
            S_["閘"][f"R{wn}_{stg} 重現 ＝ resultsYL_integrate（不同項數，{len(mine)} 顆）"] = int(bad)
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    yl0 = SE[(SE["世界鍵"] == "主") & (SE["策略"] == "營量")].iloc[0]
    S_["閘"]["T1 營量 主 ＝ T1fix c13 t1 r0（eq_sha、主窗年化回落 repr）"] = int(yl0["eq_sha"] != c13["eq_sha"] or repr(float(yl0["主窗_年化"])) != repr(float(c13["cagr"]))
                                                                     or repr(float(yl0["主窗_回落"])) != repr(float(c13["mdd"])))
    r1 = t1[(t1["key"] == "c1") & (t1["var"] == "t1")].set_index("r")
    m1 = SE[(SE["世界鍵"] == "主") & (SE["策略"] == "營飆")].set_index("r")
    S_["閘"]["T2 營飆 主 ＝ T1fix c1 t1（不同顆數）"] = int(sum(m1.at[r, "eq_sha"] != r1.at[r, "eq_sha"] for r in m1.index))
    S_["閘"]["T3 定版跑中買到補回鍵（理應 0）"] = int(SE[SE["世界鍵"].isin(["主", "早年"])]["補回買進"].sum())
    log(f"[閘] {S_['閘']}")
    bad = [k for k, v in S_["閘"].items() if v != 0]
    # ── 彙總 ──
    C = []
    for wn in ("主", "早年"):
        W = _W[wn]
        for stg in STRAT:
            g0 = SE[(SE["世界鍵"] == wn) & (SE["策略"] == stg)].set_index("r")
            g1 = SE[(SE["世界鍵"] == wn + "_v") & (SE["策略"] == stg)].set_index("r")
            for sg in W["segp"]:
                b = W["b50"][sg]
                for vn, g in (("定版（重現）", g0), ("seq255 強制出場", g1)):
                    c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                    C.append({"世界": wn, "策略": stg, "段": sg, "變體": vn, "顆數": len(g), "年化": c_, "回落": m_, "比值": c_ / abs(m_),
                              "對0050": IG.label(c_, m_, b), "年化_p10": float(g[f"{sg}_年化"].quantile(.1)), "年化_p90": float(g[f"{sg}_年化"].quantile(.9)),
                              "配對差年化_中位": float((g[f"{sg}_年化"] - g0.loc[g.index, f"{sg}_年化"]).median()),
                              "配對差回落_中位": float((g[f"{sg}_回落"] - g0.loc[g.index, f"{sg}_回落"]).median()),
                              "顆數_年化有變": int((g[f"{sg}_年化"] != g0.loc[g.index, f"{sg}_年化"]).sum()),
                              "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"]),
                              "補回買進_平均": float(g["補回買進"].mean()), "stop_force_平均": float(g["stop_force_n"].mean())})
    C = pd.DataFrame(C)
    base_ = C[C["變體"] == "定版（重現）"].set_index(["世界", "策略", "段"])
    for k in ("年化", "回落", "比值"):
        C[f"Δ{k}"] = [r[k] - base_.loc[(r["世界"], r["策略"], r["段"]), k] for _, r in C.iterrows()]
    C["標籤變"] = [r["對0050"] != base_.loc[(r["世界"], r["策略"], r["段"]), "對0050"] for _, r in C.iterrows()]
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S_["表"] = C.to_dict("records")
    # 筆數表
    CNT = {}
    for wn in ("主", "早年"):
        d = CLS[wn]
        for stg, (key, H, G) in STRAT.items():
            x = d[d["H"] == H] if len(d) else d
            if G and len(x):
                x = x[x["閘開"]]
            for sg in list(_W[wn]["segp"]):
                if sg == "主窗":
                    continue
                y = x[x["段"] == sg] if len(x) else x
                CNT[f"{wn}|{stg}|{sg}"] = y["原因"].value_counts().to_dict() if len(y) else {}
    S_["筆數（xpos＜0，營飆只算閘開）"] = CNT
    TR = {}
    for wk in ("主_v", "早年_v"):
        for stg in STRAT:
            g = SE[(SE["世界鍵"] == wk) & (SE["策略"] == stg)]
            nb_ = g["補回買進"].sum()
            TR[f"{wk}|{stg}"] = {"每條補回買進（平均）": float(g["補回買進"].mean()), "顆數有買到": int((g["補回買進"] > 0).sum()),
                                 "淨報酬平均（合併所有顆、已出場）": float(g["補回淨報酬和"].sum() / nb_) if nb_ else np.nan,
                                 "勝率": float(g["補回勝"].sum() / nb_) if nb_ else np.nan,
                                 "stop_force 平均（變體）": float(g["stop_force_n"].mean()),
                                 "stop_force 平均（定版）": float(SE[(SE["世界鍵"] == wk[:-2]) & (SE["策略"] == stg)]["stop_force_n"].mean())}
    S_["補回交易"] = TR
    S_["完成（台北）"] = now_tpe()
    json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(S_, C, cls_all, det_all)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    log("\n" + C[["世界", "策略", "段", "變體", "年化", "回落", "比值", "對0050", "Δ年化", "Δ回落", "配對差年化_中位", "顆數_年化有變", "補回買進_平均"]].to_string(index=False))
    if bad:
        log(f"⛔ 閘不過 {bad}（假設版數字不可用）")
        raise SystemExit(1)
    log(f"[完] {now_tpe()}（台北）")


def sgn(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


def report(S, C, cls, det):
    L = ["# 只讀盤點一：持有期內下市「整筆不進場」vs seq255 停止交易強制出場（營量 v1、營飆 v1）", "",
         f"產出 {S['完成（台北）']}（台北）。回測線計算子代理。⭐ {WORD}。⛔ 鎖內檔一字未改。", "",
         f"seq255 原文：{S['seq255原文']}", "",
         "## ① 因持有期內下市而沒進場的訊號（xpos＜0 分類；營飆只計閘開）", "", "| 世界｜策略｜段 | 分類筆數 |", "|---|---|"]
    for k, v in S["筆數（xpos＜0，營飆只算閘開）"].items():
        L.append(f"| {k} | {json.dumps(v, ensure_ascii=False) if v else '0'} |")
    L += ["", "### 明細（持有期內下市／壞根＋下市）", "", "| 世界 | H | 代號 | 名稱 | 訊號日 | 進場日 | 末根日 | 段 | 閘開 | 分類 | seq255 淨報酬 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    if len(cls):
        dd = cls[cls["原因"].isin(["持有期內下市（純）", "持有期內壞根＋下市"])]
        dk = {(r["世界"], r["H"], r["sid"], r["entry_pos"]): r["淨報酬"] for _, r in det.iterrows()} if len(det) else {}
        for _, r in dd.sort_values(["世界", "H", "進場日"]).iterrows():
            nr = dk.get((r["世界"], r["H"], r["sid"], r["entry_pos"]))
            L.append(f"| {r['世界']} | {r['H']} | {r['sid']} | {r['名稱']} | {r['訊號日']} | {r['進場日']} | {r.get('末根日', '')} | {r['段']} | {'是' if r['閘開'] else '否'} | {r['原因']} | {sgn(nr) if nr is not None else '—'} |")
    if len(cls) and "壞根類型" in cls:
        L += ["", "### 參考：xpos＜0 但不是下市的列（壞根類型；營飆只計閘開）", "", "| 世界 | 策略 | 段 | 壞根類型 | 筆數 |", "|---|---|---|---|---|"]
        for stg, (key, H, G) in STRAT.items():
            x = cls[(cls["H"] == H) & cls["壞根類型"].notna()]
            if G:
                x = x[x["閘開"]]
            for (w_, sg, ty), v in x.groupby(["世界", "段", "壞根類型"]).size().items():
                L.append(f"| {w_} | {stg} | {sg} | {ty} | {int(v)} |")
    L += ["", "## ② 組合層：定版 vs seq255 強制出場（營飆 200 顆中位；比值 ＝ 年化 ÷ |回落|）", "",
          "| 世界 | 策略 | 段 | 變體 | 年化 | 回落 | 比值 | 對 0050 | Δ年化 | Δ回落 | 配對差中位 | 年化有變顆數 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in C[C["段"] != "主窗"].iterrows():
        L.append(f"| {r['世界']} | {r['策略']} | {r['段']} | {r['變體']} | {sgn(r['年化'])} | {sgn(r['回落'])} | {r['比值']:.3f} | {r['對0050']} | {sgn(r['Δ年化'], 2)} | {sgn(r['Δ回落'], 2)} | "
                 f"{sgn(r['配對差年化_中位'], 2)} | {r['顆數_年化有變']}／{r['顆數']} |")
    L += ["", "## ③ 補回列的實際買進", "", "```", json.dumps(S["補回交易"], ensure_ascii=False, indent=1, default=float), "```", "",
          "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "", f"⭐ {WORD}。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

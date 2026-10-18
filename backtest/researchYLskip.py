# -*- coding: utf-8 -*-
"""營量 v1：買到／同日排名落選／已滿被略過 三類訊號比較（使用者看完 seq378 營飆結果後問「同問那營量呢？」）
——回測線計算子代理。⭐ 描述、⛔ 不計 N、⛔ 不改規則；⛔ 不改任何既有 .py／結果夾（researchYFskip.py 只 import 重用）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLskip [--procs 3]
    查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLskip_check

═══ 讀法（寫於 2026-10-18（台北），在算任何本件數字之前；⚠ 本線看過：營飆 seq378 全部結果（resultsYFskip cells／diffs）、營量 v1 各段年化／回落、
    resultsYLvsYF；⛔ 沒看過任何營量「被略過訊號」的逐筆報酬或特徵）═══
 方法 ＝ researchYFskip 檔頭 S1～S8 原樣，只換策略參數（⭐ 直接 import 該檔的 price_feats、bench50、wmed、wmean、boot_diffs、DIFF_MET）：
 L1 引擎：營量 v1 ＝ researchYL_integrate.eng(W, YL, r) 原式 ＝ research11.simulate_mtm(SIG[無閘], "H60", 20, default_rng(P1_SEED0＋r), …, d_max=None,
    pick="relvol", queue_days=0, stop_force=SF)；另傳自己的 log=[]、audit=[]（integrate 原式本來就傳 log=[]，只記錄、數值路徑不變）
    營量不抽籤（pick＝relvol、pick_tie＝None ⇒ rng 不被使用）⇒ 分類只用 r＝0；另跑 r＝1～199 驗 eq_sha 與逐筆分類 200 顆逐位元相同（閘 L1b）
 L2 訊號母體 ＝ 該世界 SIG[無閘] 去掉 sid／entry_pos／xpos_H60／g_H60 缺值與 xpos＜0（＝ 引擎看得到的列）
      A 入選 ＝ log "in"
      B 同日排名落選 ＝ log "a"（當天開盤前有空槽、候選多於空槽，relvol 排名在後沒買到；⚠ 與營飆「抽籤落選」性質不同：這裡是依 relvol 挑掉的；
        也含「現金用盡」，另計筆數）
      C 已滿被略過 ＝ 沒 log、當天開盤前（排程出場後）持有 ＝ 20 檔、且該 sid 未持有（由 audit 重建 tb ＜ t ＜ ts）
      D 已持有同檔 ＝ log "c" ＋ 槽滿日 sid 已持有 ⇒ 另列
 L3 段 ＝ 營飆 v1 原報告段界：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（主世界）；早年 2005-02-01～2014-12-31（早年世界）
 L4 特徵 ＝ YFskip S4 原樣（前 20／60 日漲幅、距 52 週高、同週訊號數、距本波首訊號、本波此前訊號數）；
    ⚠ 波／同週以「營量的訊號母體」（無大盤閘）算 ＝ YFskip 定義「該世界訊號母體所有訊號日」套在營量引擎看得到的列上
 L5 報酬 ＝ YFskip S5 原樣、抱 60 個交易日（營量 H60）：毛 ＝ g_H60；停止交易強制出場同引擎；淨 ＝ 毛 − 0.585%；0050 同期淨扣 0.385%；
    資料尾未滿 60 根照引擎以最後收盤計（「未滿60」）
 L6 彙總 ＝ YFskip S6 原樣（營量只一條 ⇒ p_c ∈ {0,1}，加權統計 ＝ 一般統計；月分群 bootstrap 2000 次、rng 378；種子中位對照法不適用、不報）
    S8 描述格照抄：距52週高_平均、在52週高占比；另列「確認·滿60」＝ 確認段剔除未滿 60 根的訊號
 L7 閘：G1 營量 主 ＝ resultsT1fix c13 t1 r0（eq_sha、年化、回落 repr）；G2 兩世界 ＝ resultsYL_integrate/seeds 同格 r0；
    L1b 200 顆 eq_sha、分類逐位元相同；K3 無法解釋＝0、重複＝0；K4 0050 ＝ bench；K5 A 每筆淨 ＝ audit（≤1e−12）、A 筆數 ＝ trades
 L8 營飆對照：讀 resultsYFskip/cells.csv、diffs.csv 並列（vsYF.csv）
 必附：「看過結果的描述，不當改規則依據」；早年附 reduce_v2 約 0.3% 註與 NOTE3
輸出 backtest/resultsYLskip/：signals.csv.gz、classes.npz、seed_check.csv.gz、cells.csv、diffs.csv、vsYF.csv、summary.json、run.log
"""
from __future__ import annotations

import argparse
import json
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
from backtest import researchYF_N as YN                     # noqa: E402
from backtest import researchYFskip as YFS                  # noqa: E402  ⭐ 只 import 重用、⛔ 不改

TIME = "2026-10-18（台北）"
OUT = "backtest/resultsYLskip"
H = 60
RULE = f"H{H}"
N = 20
NSEED = 200
BOOT_SEED = 378
COST = R.COST
COST_ETF = YFS.COST_ETF
if os.environ.get("YLS_QUICK"):                              # 煙霧測試（不是交件）
    NSEED, OUT = 3, "/tmp/yls_quick"
    YFS.NB = 50
WORD = YFS.WORD
NOTE_EARLY = YFS.NOTE_EARLY
SEGS = YFS.SEGS
CLS = YFS.CLS
CNAME = {"A": "A 入選", "B": "B 同日排名落選", "C": "C 已滿被略過", "D": "D 已持有同檔"}
FEAT = YFS.FEAT
NFULL = f"未滿{H}"
_W: dict = {}
sha, now_tpe, log_to, wmed, wmean = YFS.sha, YFS.now_tpe, YFS.log_to, YFS.wmed, YFS.wmean


def build_sig(W, wn, log):
    """＝ YFskip.build_sig，只換 SIG[無閘]、H60（另帶 relvol 欄供查核）。"""
    s = W["SIG"][False]
    d = s.dropna(subset=["sid", "entry_pos", f"xpos_{RULE}", f"g_{RULE}"])
    d = d[d[f"xpos_{RULE}"] >= 0].reset_index(drop=True)
    cal = W["cal"]; n0 = len(cal); cl, op, SF = W["closes"], W["opens"], W["SF"]
    e = d["entry_pos"].to_numpy(int); x = d[f"xpos_{RULE}"].to_numpy(int); g = d[f"g_{RULE}"].to_numpy(float)
    sid = d["sid"].astype(str).to_numpy()
    if pd.Series(list(zip(sid, e))).duplicated().any():
        raise SystemExit(f"⛔ {wn} (sid, entry_pos) 重複")
    bo, bc = YFS.bench50(cal)
    ref = RR._G["bench"] if wn == "主" else RR.load_bench(cal)
    k4 = int(not (len(ref) == len(bc) and np.array_equal(np.asarray(ref, float), bc, equal_nan=True)))
    rows = []; cache = {}
    rv = d["relvol"].to_numpy(float)
    for i in range(len(d)):
        s_, e_, x_, g_ = sid[i], int(e[i]), int(x[i]), float(g[i])
        ep = float(op[s_][e_])
        if not (np.isfinite(ep) and ep > 0):
            ep = float(cl[s_][e_])
        L = SF.get(s_); forced = 0
        if L is not None and e_ <= L and x_ > L + 1:
            gg = float(cl[s_][L]) / ep - 1.0; pdx = L; forced = 1
        else:
            gg = g_; pdx = min(x_, n0 - 1)
        net = gg - COST
        b_in = bo[e_] if (np.isfinite(bo[e_]) and bo[e_] > 0) else bc[e_]
        b_net = bc[pdx] / b_in - 1.0 - COST_ETF
        if s_ not in cache:
            cache[s_] = R.load_bars(s_, W["uni"].get(s_, "twse"), cal)
        r20, r60, d52, wl, st = YFS.price_feats(cache[s_], int(d["k"].iloc[i]), e_)
        rows.append({"sid": s_, "entry_pos": e_, "xpos": x_, "訊號日": e_ - 1, "k": int(d["k"].iloc[i]), "relvol": rv[i], "毛": gg, "淨": net, "0050淨": b_net,
                     "超額": net - b_net, "強制出場": forced, NFULL: int(x_ >= n0), "前20日漲幅": r20, "前60日漲幅": r60, "距52週高": d52, "52週窗長": wl,
                     "價格狀態": st})
    T = pd.DataFrame(rows)
    T["日期"] = cal[T["訊號日"].to_numpy()]
    T["月"] = T["日期"].dt.to_period("M").astype(str)
    wk = (T["日期"] - pd.to_timedelta(T["日期"].dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    T["週"] = wk; T["同週訊號數"] = T.groupby("週")["sid"].transform("size").astype(int)
    days = np.sort(T["訊號日"].unique())
    wid = np.concatenate([[0], np.cumsum(np.diff(days) > YFS.WAVE_GAP)])
    start = {}
    for dd, w_ in zip(days, wid):
        start.setdefault(w_, dd)
    dmap = dict(zip(days, wid))
    T["波"] = T["訊號日"].map(dmap).astype(int)
    T["距本波首訊號"] = (T["訊號日"] - T["波"].map(start)).astype(int)
    cnt_day = T.groupby("訊號日").size()
    cum = {}
    for w_, grp in pd.Series(cnt_day.index, index=cnt_day.index).groupby(cnt_day.index.map(dmap)):
        acc = 0
        for dd in grp.values:
            cum[dd] = acc; acc += int(cnt_day[dd])
    T["本波此前訊號數"] = T["訊號日"].map(cum).astype(int)
    T["本波訊號數"] = T.groupby("波")["sid"].transform("size").astype(int)
    T["段"] = ""
    for sg in SEGS[wn]:
        a, b = W["segp"][sg]
        T.loc[(T["entry_pos"] >= a) & (T["entry_pos"] <= b), "段"] = sg
    T["世界"] = wn
    log(f"[{wn} 訊號表] {len(T)} 筆｜波 {T['波'].nunique()}｜價格狀態 {T['價格狀態'].value_counts().to_dict()}｜強制出場 {int(T['強制出場'].sum())}｜"
        f"{NFULL} {int(T[NFULL].sum())}｜段 {T['段'].value_counts().to_dict()}｜K4 {k4}")
    return T, k4


def engine(W, r, log=None, audit=None):
    """＝ researchYL_integrate.eng(W, YL, r) 的 relvol 分支原式（只把 log=[] 換成呼叫端的 list）。"""
    Hk, S, G, P = IG.KEY[IG.YL]
    assert (Hk, S, G, P) == (H, N, False, "relvol"), IG.KEY[IG.YL]
    return R.simulate_mtm(W["SIG"][G], f"H{Hk}", S, np.random.default_rng(RR.P1_SEED0 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                          log=[] if log is None else log, d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=audit)


def classify(W, T, r):
    """＝ YFskip.classify，只換引擎與 N。"""
    NP = W["NP"]
    lg, au = [], []
    o = engine(W, r, log=lg, audit=au)
    ID = {(s_, int(e_)): i for i, (s_, e_) in enumerate(zip(T["sid"], T["entry_pos"]))}
    cls = np.full(len(T), -1, np.int8); dup = 0
    for z in lg:
        i = ID[(str(z["sid"]), int(z["entry_pos"]))]
        c = {"in": 0, "a": 1, "c": 3}.get(z["reason"])
        if c is None:
            raise SystemExit(f"⛔ 未預期的 log 原因 {z['reason']}")
        if cls[i] != -1:
            dup += 1
        cls[i] = c
    TR = YN.trades_of(au, NP)
    iv = [(s_, tb, ts) for s_, tb, ts, *_ in TR]
    unexp = 0; dfull = 0; cash_b = 0
    E = T["entry_pos"].to_numpy(int); SID = T["sid"].to_numpy()
    for t in np.unique(E):
        ii = np.flatnonzero(E == t)
        hp = {s_ for s_, tb, ts in iv if tb < t < ts}
        for i in ii:
            if cls[i] != -1:
                continue
            if len(hp) >= N:
                if SID[i] in hp:
                    cls[i] = 3; dfull += 1
                else:
                    cls[i] = 2
            else:
                unexp += 1
        nb_ = int((cls[ii] == 1).sum())
        if nb_:
            n_in = int((cls[ii] == 0).sum())
            if n_in < min(N - len(hp), n_in + nb_):
                cash_b += nb_
    net = T["淨"].to_numpy(float); k5 = 0.0; k5_bad = 0; nA_tr = 0
    for s_, tb, ts, amt, pin, pout, ep_ in TR:
        i = ID[(s_, int(tb))]; nA_tr += 1
        if cls[i] != 0:
            k5_bad += 1; continue
        if np.isfinite(pout):
            k5 = max(k5, abs((pout / pin - 1.0 - COST) - net[i]))
        else:
            k5_bad += 1
    row = {"r": r, "eq_sha": sha(o["equity"]), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"]), "A_audit筆": nA_tr, "重複": dup,
           "無法解釋": unexp, "D滿": dfull, "B現金用盡": cash_b, "K5最大差": k5, "K5不符": k5_bad}
    for sg in SEGS[W["name"]]:
        m = (T["段"] == sg).to_numpy()
        for j, c in enumerate(CLS):
            row[f"{sg}_{c}"] = int(((cls == j) & m).sum())
    return row, cls, o


def job(args):
    wn, r = args
    W = _W[wn]
    row, cls, _ = classify(W, W["T"], r)
    row["世界"] = wn
    return row, cls


def vs_yf(C, DF):
    """營飆（resultsYFskip）與營量並列。"""
    yc = pd.read_csv("backtest/resultsYFskip/cells.csv", encoding="utf-8-sig")
    yd = pd.read_csv("backtest/resultsYFskip/diffs.csv", encoding="utf-8-sig")
    segmap = {"探索": ("探索", "探索"), "確認": ("確認", "確認"), "確認·滿": ("確認·滿120", "確認·滿60"), "早年": ("早年", "早年")}
    rows = []
    for lab, (sf, sl) in segmap.items():
        for c in ("A", "B", "C", "D"):
            f = yc[(yc["段"] == sf) & (yc["類"].str[0] == c)].iloc[0]; l_ = C[(C["段"] == sl) & (C["類"].str[0] == c)].iloc[0]
            rows.append({"段": lab, "類": c, "營飆類名": f["類"], "營量類名": l_["類"],
                         "營飆_占比": f["占比"], "營量_占比": l_["占比"], "營飆_前20中位": f["前20日漲幅_中位"], "營量_前20中位": l_["前20日漲幅_中位"],
                         "營飆_前60中位": f["前60日漲幅_中位"], "營量_前60中位": l_["前60日漲幅_中位"],
                         "營飆_距首訊號中位": f["距本波首訊號_中位"], "營量_距首訊號中位": l_["距本波首訊號_中位"],
                         "營飆_淨中位(H120)": f["淨_中位"], "營量_淨中位(H60)": l_["淨_中位"], "營飆_淨平均(H120)": f["淨_平均"], "營量_淨平均(H60)": l_["淨_平均"],
                         "營飆_勝率": f["勝率"], "營量_勝率": l_["勝率"], "營飆_超額平均": f["超額_平均"], "營量_超額平均": l_["超額_平均"]})
    V = pd.DataFrame(rows)
    drows = []
    for lab, (sf, sl) in segmap.items():
        for cmp_ in ("B−A", "C−A"):
            for met in ("淨_平均", "淨_中位", "超額_平均", "前60日漲幅_中位", "距本波首訊號_中位"):
                f = yd[(yd["段"] == sf) & (yd["比較"] == cmp_) & (yd["指標"] == met)].iloc[0]
                l_ = DF[(DF["段"] == sl) & (DF["比較"] == cmp_) & (DF["指標"] == met)].iloc[0]
                drows.append({"段": lab, "比較": cmp_, "指標": met, "營飆_差": f["差"], "營飆_CI下": f["CI下"], "營飆_CI上": f["CI上"],
                              "營量_差": l_["差"], "營量_CI下": l_["CI下"], "營量_CI上": l_["CI上"]})
    return V, pd.DataFrame(drows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}｜營量 v1 {IG.YL}｜驗種子 {NSEED}｜bootstrap {YFS.NB}")
    gate = {}
    Wm, gm = IG.main_world(log)
    Wm["T"], gate["K4 主 0050 ≠ bench"] = build_sig(Wm, "主", log)       # ⚠ 在 early_world 改 D.DATA 之前
    We, ge = IG.early_world(log, a.procs)
    We["T"], gate["K4 早年 0050 ≠ bench"] = build_sig(We, "早年", log)
    _W["主"], _W["早年"] = Wm, We
    # ── r＝0：分類＋權益閘 ──
    R0 = {}
    for wn, W in _W.items():
        row, cls, o = classify(W, W["T"], 0)
        R0[wn] = (row, cls, o)
        log(f"[{wn} r0] eq_sha {row['eq_sha']}｜trades {row['trades']}｜{ {k: v for k, v in row.items() if '_' in k and k[0] in '探確早'} }")
    YLrow = {}
    for wn, W in _W.items():
        o = R0[wn][2]; eq = np.asarray(o["equity"], float)
        rr = {"eq_sha": sha(eq)}
        for sg in W["segp"]:
            x, y = W["segp"][sg]
            c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
            rr[f"{sg}_年化"] = float(c_); rr[f"{sg}_回落"] = float(m_)
        YLrow[wn] = rr
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    gate["G1 營量 主 ＝ T1fix c13 t1 r0"] = int(YLrow["主"]["eq_sha"] != c13["eq_sha"] or repr(YLrow["主"]["主窗_年化"]) != repr(float(c13["cagr"]))
                                           or repr(YLrow["主"]["主窗_回落"]) != repr(float(c13["mdd"])))
    refI = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    for wn in ("主", "早年"):
        b_ = refI[(refI["世界"] == wn) & (refI["格"] == IG.YL) & (refI["r"] == 0)].iloc[0]
        gate[f"G2 營量 {wn} ＝ 整合件 {IG.YL} r0"] = int(YLrow[wn]["eq_sha"] != b_["eq_sha"] or any(
            repr(YLrow[wn][f"{sg}_{k}"]) != repr(float(b_[f"{sg}_{k}"])) for sg in _W[wn]["segp"] for k in ("年化", "回落")))
    # ── r＝1～NSEED−1：驗 200 顆逐位元相同 ──
    jobs = [(wn, r) for wn in ("主", "早年") for r in range(1, NSEED)]
    T0 = time.time()
    with Pool(a.procs) as pool:
        RES = pool.map(job, jobs, chunksize=4)
    log(f"[驗種子] {len(RES)} 次｜{time.time() - T0:.0f}s")
    SC = pd.DataFrame([dict(R0[wn][0], 世界=wn) for wn in ("主", "早年")] + [z[0] for z in RES])
    for wn in ("主", "早年"):
        ref_sha = R0[wn][0]["eq_sha"]; ref_cls = R0[wn][1]
        sub = [(row, cls) for (row, cls), (w_, _) in zip(RES, jobs) if w_ == wn]
        gate[f"L1b {wn} eq_sha 與 r0 不同顆數（／{len(sub) + 1}）"] = int(sum(row["eq_sha"] != ref_sha for row, _ in sub))
        gate[f"L1b {wn} 分類與 r0 不同顆數（／{len(sub) + 1}）"] = int(sum(not np.array_equal(cls, ref_cls) for _, cls in sub))
        r0 = R0[wn][0]
        gate[f"K3 {wn} 無法解釋＋重複"] = int(SC[SC["世界"] == wn]["無法解釋"].sum() + SC[SC["世界"] == wn]["重複"].sum())
        gate[f"K5 {wn} A 淨報酬 ≠ audit（不符筆）"] = int(r0["K5不符"]) + int(r0["K5最大差"] > 1e-12)
        gate[f"K5 {wn} A 淨報酬最大差"] = float(r0["K5最大差"])
        gate[f"K5 {wn} A 筆 ≠ trades"] = int(r0["A_audit筆"] != r0["trades"])
    log(f"[閘] {gate}")
    SC.to_csv(os.path.join(OUT, "seed_check.csv.gz"), index=False)
    CM = {wn: R0[wn][1] for wn in ("主", "早年")}
    np.savez_compressed(os.path.join(OUT, "classes.npz"), **CM)
    S = {"讀法寫死": TIME, "性質": "描述、不計 N、不改規則（同 seq378 方法套營量 v1）", "必附": WORD, "早年註": NOTE_EARLY, "世界閘": {**gm, **ge}, "閘": gate,
         "營量r0": YLrow, "B 性質": "營量 B ＝ 同日 relvol 排名落選（依 relvol 挑掉的），與營飆 B 抽籤落選（隨機）性質不同"}
    hard = [k for k, v in gate.items() if "最大差" not in k and v != 0]
    if hard:
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {hard}")
    # ── 訊號表＋p ──
    TT = []
    for wn in ("主", "早年"):
        T = _W[wn]["T"].copy()
        T["類"] = np.array(CLS)[CM[wn]]
        for j, c in enumerate(CLS):
            T[f"p_{c}"] = (CM[wn] == j).astype(float)
        TT.append(T)
    TT = pd.concat(TT, ignore_index=True)
    TT.drop(columns=["日期"]).to_csv(os.path.join(OUT, "signals.csv.gz"), index=False, float_format="%.12g")
    # ── 彙總（YFskip S6 原樣；p ∈ {0,1}）──
    rng = np.random.default_rng(BOOT_SEED)
    C, DF = [], []
    for wn in ("主", "早年"):
        Tw = _W[wn]["T"]
        segl = [(sg, (Tw["段"] == sg).to_numpy()) for sg in SEGS[wn]]
        if wn == "主":
            segl.append((f"確認·滿{H}", ((Tw["段"] == "確認") & (Tw[NFULL] == 0)).to_numpy()))
        for sg, msk in segl:
            mi = np.flatnonzero(msk)
            Ts = TT[TT["世界"] == wn].reset_index(drop=True).iloc[mi].reset_index(drop=True)
            P = Ts[[f"p_{c}" for c in CLS]].to_numpy(float); n = len(Ts)
            net = Ts["淨"].to_numpy(float); exc = Ts["超額"].to_numpy(float)
            for j, c in enumerate(CLS):
                w = P[:, j]
                row = {"世界": wn, "段": sg, "類": CNAME[c], "段內訊號": n, "占比": float(w.mean()), "筆數": int(w.sum()),
                       "淨_中位": wmed(net, w), "淨_平均": wmean(net, w), "勝率": wmean((net > 0).astype(float), w),
                       "超額_中位": wmed(exc, w), "超額_平均": wmean(exc, w), "超額勝率": wmean((exc > 0).astype(float), w),
                       f"{NFULL}占": wmean(Ts[NFULL].to_numpy(float), w), "強制出場占": wmean(Ts["強制出場"].to_numpy(float), w)}
                for f in FEAT:
                    row[f"{f}_中位"] = wmed(Ts[f].to_numpy(float), w)
                row["距52週高_平均"] = wmean(Ts["距52週高"].to_numpy(float), w)
                row["在52週高占比"] = wmean((Ts["距52週高"].to_numpy(float) >= 0).astype(float), w)
                row["前60日_NaN占"] = wmean(np.isnan(Ts["前60日漲幅"].to_numpy(float)).astype(float), w)
                row["52週短窗占"] = wmean((Ts["52週窗長"].to_numpy(float) < 245).astype(float), w)
                row["relvol_中位"] = wmed(Ts["relvol"].to_numpy(float), w)
                C.append(row)
            if (P.sum(axis=0) == 0).any():
                log(f"⚠ {wn} {sg} 有空類 {dict(zip(CLS, P.sum(axis=0)))}")
            bd, M = YFS.boot_diffs(Ts, P, rng)
            for (col, how, cmp_), (pt, lo, hi, nb) in bd.items():
                DF.append({"世界": wn, "段": sg, "比較": cmp_, "指標": f"{col}_{'平均' if how == 'mean' else '中位'}", "差": pt, "CI下": lo, "CI上": hi,
                           "月群數": M, "有效抽數": nb})
    C = pd.DataFrame(C); DF = pd.DataFrame(DF)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    DF.to_csv(os.path.join(OUT, "diffs.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    V, VD = vs_yf(C, DF)
    V.to_csv(os.path.join(OUT, "vsYF.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    VD.to_csv(os.path.join(OUT, "vsYF_diffs.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S["表"] = C.to_dict("records"); S["差"] = DF.to_dict("records"); S["對照營飆"] = V.to_dict("records"); S["對照營飆差"] = VD.to_dict("records")
    S["B現金用盡"] = {wn: int(R0[wn][0]["B現金用盡"]) for wn in ("主", "早年")}
    S["D滿"] = {wn: int(R0[wn][0]["D滿"]) for wn in ("主", "早年")}
    S["完成（台北）"] = now_tpe()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    show = ["世界", "段", "類", "占比", "筆數", "前20日漲幅_中位", "前60日漲幅_中位", "距52週高_平均", "在52週高占比", "同週訊號數_中位", "距本波首訊號_中位",
            "relvol_中位", "淨_中位", "淨_平均", "勝率", "超額_中位", "超額_平均", f"{NFULL}占"]
    log("\n" + C[show].to_string(index=False))
    log("\n" + DF.to_string(index=False))
    log("\n" + VD.to_string(index=False))
    log(f"[完] {now_tpe()}（台北）")


if __name__ == "__main__":
    main()

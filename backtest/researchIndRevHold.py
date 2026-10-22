# -*- coding: utf-8 -*-
"""PREREG「產業營收加速改長抱」seq2【正式跑】（台股策略線登錄 seq2 sha 800ad3a4bcacd7da；裁定 seq452 §二 發號、seq453 核 seq2（36 格挑 1、N_組合 ＋1）、
seq455 §一 核開正式跑）——回測線計算子代理。⚠ 看過前件描述才改長抱 ⇒ 結論最多「暫定」。⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevHold --step prep_v2|dry|run|rand [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevHold_check

═══ 讀法（寫死於 2026-10-23 00:05（台北），在算任何報酬之前；★ ＝ 執行者補；〔 〕＝ 另一讀法）═══
 G0 沿用頻率表（researchIndRevHold_freq ＝ FQ，commit 453d368ed7，⛔ 不改）：讀法 F0～F10 全部照舊（A 表、批日 ＝ 可用日次一交易日、A ＞ 0 前 K、S1／S3、
    份數 round(H/21)、各產業 ＝ 批 ÷ K、出場 FQ.lot_exit（停止交易、硬斷點 seq335、到期順延）、主帳 2015-08 起（seq455 §一 1 核）、資料尾 2026-08-24）
    ⭐ 乾跑（價格全 1、成本 0）時本檔的帳與 FQ.sim_cell 逐日持股數完全相同、現金相同（--step dry 驗；早年用 eotc 旗標驗）
 G1 價格（seq455 §一 3）：主 ＝ ctx P（H2D edc6f8002f 還原價）；⭐ 早年A ＝ reduce_v2（~/earlydata/950ad26e12/reduce_v2，只上市；早年 W1 本來就只有上市）
    的 SC.load_px 還原價與旗標（TR.one、exright 修正、load_bars 壞根，皆在 reduce_v2 上重算）；挑選（成員、市值、A）仍是頻率表的 eotc 版面
    ⚠ reduce_v2 沒有的成員 ⇒ 不買（計數「無旗標」）；早年數字附「早年含減資假飆股約 0.3%」（seq341）
 G2 金額（★ 登錄「分成 H/21 份、每月新批用一份、到期回收再用」）：新批 ＝ min(前一日權益 ÷ n_H, 可用現金)；
    可用現金 ＝ 未被「尚未回收的批」占用的錢（批的份額連同其未投入、提前出場的現金，到該批全部賣完才回收）
    買價 ＝ 批日還原開盤；持有期間市值 ＝ 單位 × 還原收盤（ffill）；出場價 ＝ 出場日還原收盤（停止交易 ＝ 最後收盤 ffill）
    成本（組合層慣例，同前件 PRE／researchScore）：每筆賣出扣「進場金額 × 0.585%」（來回）；資料尾仍持有不扣
 G3 段與判準（登錄 §三、seq455 §一 2）：探索 2017-03-02～2021-12-30（挑）｜確認 2022-01-03～2026-08-24（判）｜早年A 2012-06-01～2014-12-30｜
    早年B 2015-08-03～2016-12-30（早年兩段分開報）；年化、MDD ＝ SC.seg_metrics（R13.window_stats，245 日／年）
    基準 ＝ 大盤報酬指數（origin/main data/history/market_tri.csv，同 A 表 sha；收盤 ffill 到各版面日曆）；標籤 ＝ SC.label（合格：年化 ＞ 大盤 且 比值 ≥ 大盤；另列：只贏年化）
    0050（RR.load_bench；早年用 reduce_v2 的 0050）只當排名表一列
    退化（事前排除，seq455：照評估窗）：探索段平均持股 ＜ 5 檔或平均現金 ＞ 30%（本檔正式帳的值；乾跑值另列）
    挑格：非退化中探索段「合格」者取比值最高；都沒有 ⇒ 非退化中比值最高；平手 ⇒ 年化高、A、K、H、S 順
    早年「依構造不可判定」（seq455 §一 2）：★ 該段平均現金 ＞ 30%，或 該段內一批都走不完（段內 mat ≤ 段尾的批 ＝ 0）
       〔另一讀法「任一批走不完」對任何有限段都成立、無鑑別力，不用〕
    判定 ＝ 確認段標籤與「可判的早年段」標籤取較嚴；早年都不可判 ⇒ 結果句寫「早年不可判、只看確認段」；合格 ⇒「暫定合格」、另列 ⇒「另列（最多暫定）」
 G4 對照（描述、不計 N）
    主對照 ＝ 前件挑中格 A2｜K1｜S1｜季｜E0：PRE.sim_ind 在本件設定（GATE_V2、15 日規則、本次 A 表；早年 reduce_v2）同窗重跑（主窗 2017-03-02～2026-08-24、
      早年 2012-06-01～2014-12-30；早年B 前件沒有）＋ 前件原數字（resultsIndRev/prereg/meta.json）並列
    隨機 1,000 次（FQ F9 框架）：rng ＝ default_rng([20261022, r])、每批從可排名產業（挑中格的 A）permutation 取 n_b（＝ 挑中格當批產業數）；
      挑股、金額、持有、出場、成本同挑中格 ⇒ 報 p ＝ 隨機 ≥ 挑中格的比例（年化、比值）與分散度（平均持股比）
    全產業等權（FQ F10）：每批全部可排名產業（A1 集合）、產業 ÷ 產業數；S、H 同挑中格
 G5 必報：挑中產業清單與次數；各批 H 天報酬（批最終價值 ÷ 份額 − 1，含批內現金、成本；只收走完的批）平均與中位；
    ★「產業 3 年漲幅超過大盤兩倍」：挑中格每批 × 挑中產業，產業指數（PRE.ind_index：主 W1、早年 liq∧bars 成員等權；早年 reduce_v2 只有上市）
       r_產業 ＝ I[b＋749] ÷ I[b−1] − 1、r_大盤 同窗（報酬指數）；碰到 ＝ r_產業 ＞ 2 × r_大盤 且 r_產業 ＞ 0（只收 b＋749 ≤ 資料尾）〔另：(1＋r_產業) ＞ 2 ×(1＋r_大盤)〕
    吃到起漲到頂幾成（PRE P13 同式）：Is ＝ I[b−1]、低 ＝ min(I[b−250..b−1])、頂 ＝ max(I[b..b+499])；吃到 ＝ ln(I[min(mat,尾)] ÷ Is) ÷ ln(頂 ÷ 低)
       〔另：頂取 max(I[b..mat])〕；各年報酬；現金比例；換手（年買進金額 ÷ 平均權益）與成本／年；確認段 H750 走完批數與獨立期數；每月重複同產業比例
    現實版（挑中格；researchSlip 定義落到批帳，★）：C1 每邊 ＋0.3%｜C2 資金 50 萬：Q ＝ 50 萬 × 該筆金額 ÷ 前一日權益，買價 ×(1＋σ20√(Q÷ADV20))；
      到期賣出 Q_賣 ＝ Q × 出場價 ÷ 買價（★ 批帳逐批算、賣出日權益未定）、賣價 ×(1−min(i,0.99))｜C4 買與到期賣用 (開＋高＋低＋收)÷4（硬斷點、停止交易仍收盤）｜
      ＋C5 低消 20 元：每邊另加 max(20 ÷ 每筆金額 − 0.1425%, 0)
    先驗 ①～⑤（登錄 §六）照實對；族群版：查無族群表，不做（seq455 §一 5；⛔ 不用 BigRun2 分群）
輸出 backtest/resultsIndRevHold/main/：cells.csv、chosen_batches.csv、industry_counts.csv、years.csv、random.csv.gz、controls.json、c_desc.csv、variants.csv、
     eq.npz、meta.json、dry.json、run.log
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import researchScore as SC                    # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchIndRevLag_prereg as LAGP       # noqa: E402
from backtest import researchIndRevHold_freq as FQ          # noqa: E402
from backtest import researchIndMom as IMo                  # noqa: E402
from backtest import tradability as TR                      # noqa: E402

TIME = "2026-10-23 00:05（台北）"
OUT = "backtest/resultsIndRevHold/main"
WORK = FQ.WORK
V2 = os.path.expanduser("~/earlydata/950ad26e12/reduce_v2/data")
AS, KS, HS, SS = FQ.AS, FQ.KS, FQ.HS, FQ.SS
COST = PRE.COST
SEED = FQ.SEED
CAP = 500_000
RANKL = {"合格": 2, "另列": 1, "不合格": 0}
PRE_CH = {"A": "A2", "K": 1, "S": "S1", "R": "季", "E": "E0"}
W: dict = {}
G: dict = {}
LOGF = None


def log(x):
    x = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def sha_main():
    return json.load(open(os.path.join(FQ.OUT, "A_meta.json"), encoding="utf-8"))["main"]


# ═════════════ 早年 reduce_v2（G1） ═════════════
def step_prep_v2(a):
    C = LAGP.part_ctx("early", a)
    FL0 = pickle.load(open(os.path.join(WORK, "flags_early.pkl"), "rb"))
    D.DATA = V2; cal = D.load_calendar()
    if not (len(cal) == len(C["cal"]) and bool((cal == C["cal"]).all())):
        raise SystemExit("⛔ reduce_v2 日曆 ≠ eotc 日曆")
    st = pd.read_csv(os.path.join(V2, "meta", "stocks.csv"), dtype=str)
    have = set(st["stock_id"])
    sids = sorted(s for s in FL0 if s in have)
    SC._G.update(cal=cal)
    with Pool(a.procs) as pool:
        P = dict(pool.map(SC.load_px, [(s, "twse") for s in sids], chunksize=8))
    P = {s: v for s, v in P.items() if v is not None}
    FQ._F.update(cal=cal, data=V2, tab=IMo.load_exr_table()["tab"])
    with Pool(a.procs) as pool:
        FL = dict(pool.map(FQ._flag_job, [(s, "twse") for s in sorted(P)], chunksize=8))
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=off)
    bench = RR.load_bench(cal)
    info = {"eotc 旗標檔數": len(FL0), "reduce_v2 有": len(sids), "載入": len(P), "缺": sorted(set(FL0) - set(P))[:30], "缺數": len(set(FL0) - set(P)),
            "load_bars None": sum(1 for v in FL.values() if v["src"] != "load_bars")}
    pickle.dump({"P": P, "FL": FL, "dl": dl, "bench": bench, "info": info}, open(os.path.join(WORK, "v2_early.pkl"), "wb"), protocol=5)
    log(f"[reduce_v2] {info}")


# ═════════════ 世界 ═════════════
def tri_on(cal, sha):
    p = subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout
    t = pd.read_csv(io.BytesIO(p)); t["date"] = pd.to_datetime(t["date"])
    s = t.drop_duplicates("date").set_index("date")["close"].astype(float)
    return s.reindex(s.index.union(cal)).ffill().reindex(cal).to_numpy(float)


def prep(world, a, v2=True):
    Wd = FQ.prep_world(world, a)
    C = Wd["C"]
    if world == "early" and v2:
        X = pickle.load(open(os.path.join(WORK, "v2_early.pkl"), "rb"))
        Wd["FL"] = X["FL"]; Wd["PX"] = X["P"]; Wd["bench0050"] = X["bench"]; Wd["dl2"] = X["dl"]
        Wd["SF"] = R.stop_force_days({s: v["valid"] for s, v in X["P"].items()}, Wd["T"])
        Wd["okopen"] = {s: (np.isfinite(v["o"]) & (v["o"] > 0)) for s, v in X["P"].items()}
        Wd["sidx"] = {s: k for k, s in enumerate(sorted(set(Wd["FL"]) | set(Wd["sidx"])))}
        Wd["ver"] = "reduce_v2"
    else:
        Wd["PX"] = C["P"]; Wd["bench0050"] = C["bench"]; Wd["dl2"] = C["dl"]; Wd["ver"] = "eotc" if world == "early" else "H2D"
    Wd["TRI"] = tri_on(Wd["cal"], G["sha"])
    W[world] = Wd
    return Wd


# ═════════════ 批帳（G2） ═════════════
def sim_book(Wd, BL, picks, K, S, H, dry=False, divK=None, real=None):
    cal = Wd["cal"]; T = Wd["T"]; n = len(cal); nsl = FQ.NSL[H]; PX = Wd["PX"]; sidx = Wd["sidx"]
    pacc = np.zeros(n); inv = np.zeros(n); buyd = np.zeros(n); costd = np.zeros(n)
    dl_ = np.zeros(n + 2)
    Ls, La, Le = [], [], []
    bt = []   # dict(rel, A, pf)
    cnt = Counter(); binfo = []
    rx = real or {}
    for j, (b, M) in enumerate(BL):
        eqb = 1.0 + pacc[b - 1]
        occ = sum(x["A"] for x in bt if x["rel"] >= b)
        back = sum(x["pf"] for x in bt if x["rel"] < b)
        Aj = min(eqb / nsl, max(1.0 - occ + back, 0.0))
        if Aj < eqb / nsl - 1e-12:
            cnt["份數被現金卡住"] += 1
        mem = Wd["MEM"][b][0]
        inds = picks[j]; dk = (divK[j] if divK is not None else K)
        mat = b + H - 1; release = mat if mat <= T else FQ.INF
        pf = 0.0; nb = 0
        for i in inds:
            lst = mem.get(i, [])
            lst = lst[:20] if S == "S1" else lst
            if not lst:
                cnt["產業0檔"] += 1; continue
            per = Aj / dk / len(lst)
            for s in lst:
                e, why = FQ.lot_exit(Wd, s, b, mat)
                cnt[why] += 1
                if e is None:
                    continue
                nb += 1
                end = min(e, T + 1)
                if dry:
                    u = per; cp = np.ones(end - b); cr = 0.0; pe = 1.0
                else:
                    x = PX[s]; ib = 0.0; Q = None
                    bp = x["o"][b]
                    xs = rx["X"].get(s) if rx else None
                    if rx and xs is None:
                        cnt["現實版無衝擊資料"] += 1
                    if xs is not None:
                        if rx.get("c4") and np.isfinite(xs["avg"][b]):
                            bp = xs["avg"][b]
                        Q = rx["cap"] * per / eqb
                        if np.isfinite(xs["adv20"][b]) and xs["adv20"][b] > 0 and np.isfinite(xs["sig20"][b]):
                            ib = xs["sig20"][b] * math.sqrt(Q / xs["adv20"][b])
                        bp = bp * (1 + ib)
                    u = per / bp; cp = x["c"][b:end]
                    cr = COST
                    if rx:
                        Qc = rx["cap"] * per / eqb
                        cr += 2 * rx.get("s", 0.0) + (2 * max(rx["m5"] / Qc - 0.001425, 0.0) if (rx.get("m5") and Qc > 0) else 0.0)
                    pe = np.nan
                    if e <= T:
                        pe = x["c"][e]
                        if xs is not None and why in ("到期", "到期順延"):
                            if rx.get("c4") and np.isfinite(xs["avg"][e]):
                                pe = xs["avg"][e]
                            Qs = Q * pe / bp
                            isl = xs["sig20"][e] * math.sqrt(Qs / xs["adv20"][e]) if (np.isfinite(xs["adv20"][e]) and xs["adv20"][e] > 0 and np.isfinite(xs["sig20"][e])) else 0.0
                            pe = pe * (1 - min(isl, 0.99))
                    if not np.all(np.isfinite(cp)) or (e <= T and not np.isfinite(pe)):
                        cnt["價格缺"] += 1
                        cp = np.nan_to_num(cp, nan=bp); pe = pe if np.isfinite(pe) else bp
                inv[b:end] += u * cp
                pacc[b:end] += u * cp - per
                buyd[b] += per
                if e <= T:
                    pr = u * pe - per * cr
                    pacc[e:] += pr - per; pf += pr - per; costd[e] += per * cr
                    if e > mat:
                        release = max(release, e) if release != FQ.INF else release
                else:
                    release = FQ.INF
                Ls.append(sidx[s]); La.append(b); Le.append(end)
        bt.append({"rel": release, "A": Aj, "pf": pf})
        binfo.append({"j": j, "b": b, "M": M, "產業": "｜".join(inds), "n_ind": len(inds), "Aj": Aj, "買檔數": nb, "mat": mat,
                      "完": int(release != FQ.INF), "批報酬": (pf / Aj if (release != FQ.INF and Aj > 0) else np.nan)})
    eq = 1.0 + pacc
    La = np.asarray(La, int); Le = np.asarray(Le, int); Ls = np.asarray(Ls, int)
    np.add.at(dl_, La, 1); np.add.at(dl_, Le, -1)
    M2 = np.zeros((len(sidx), n + 2), np.int32)
    np.add.at(M2, (Ls, La), 1); np.add.at(M2, (Ls, Le), -1)
    distinct = (np.cumsum(M2, axis=1)[:, :n] > 0).sum(0)
    cash = 1.0 - inv / eq
    return {"eq": eq, "cash": cash, "distinct": distinct, "lots": np.cumsum(dl_)[:n], "buyd": buyd, "costd": costd, "cnt": cnt, "binfo": binfo}


def seg_metrics(Wd, eq, a_, z_):
    z_ = min(z_, Wd["T"])
    return SC.seg_metrics(eq, a_, z_)


def cell_stats(Wd, res, a_, z_, H, BL):
    z_ = min(z_, Wd["T"])
    c, m, r = SC.seg_metrics(res["eq"], a_, z_)
    meq = float(res["eq"][a_:z_ + 1].mean()); yrs = (z_ + 1 - a_) / 245
    bi = [x for x in res["binfo"] if a_ <= x["b"] <= z_]
    br = [x["批報酬"] for x in bi if np.isfinite(x["批報酬"])]
    return {"年化": c, "回落": m, "比值": r, "平均持股": float(res["distinct"][a_:z_ + 1].mean()), "平均現金": float(np.nanmean(res["cash"][a_:z_ + 1])),
            "每年換手": float(res["buyd"][a_:z_ + 1].sum()) / meq / yrs, "成本／年": float(res["costd"][a_:z_ + 1].sum()) / meq / yrs,
            "批數": len(bi), "段內走完批數": int(sum(1 for x in bi if x["mat"] <= z_)), "走完批數（資料尾）": len(br),
            "批報酬平均": float(np.mean(br)) if br else np.nan, "批報酬中位": float(np.median(br)) if br else np.nan}


def segp(Wd):
    return FQ.segp(Wd)


def bench_rows(Wd):
    out = {}
    for sg, (a_, z_) in segp(Wd).items():
        out[sg] = {"大盤": SC.seg_metrics(Wd["TRI"], a_, min(z_, Wd["T"])), "0050": SC.seg_metrics(Wd["bench0050"], a_, min(z_, Wd["T"]))}
    return out


def _cell_job(args):
    world, A, K, S, H, dry = args
    Wd = W[world]; BL = Wd["BL"]["主讀法"]; picks = Wd["PK"]["主讀法"][(A, K)]
    res = sim_book(Wd, BL, picks, K, S, H, dry=dry)
    rows = []
    B = Wd["BR"]
    for sg, (a_, z_) in segp(Wd).items():
        st = cell_stats(Wd, res, a_, z_, H, BL)
        c0, m0, r0 = B[sg]["大盤"]
        lab = SC.label(st["年化"], st["回落"], c0, m0) if (np.isfinite(st["年化"]) and np.isfinite(st["回落"]) and st["回落"] < 0) else "—"
        rows.append({"世界": world, "段": sg, "A": A, "K": K, "S": S, "H": H, **st, "大盤年化": c0, "大盤回落": m0, "大盤比值": r0, "標籤": lab})
    return rows, dict(res["cnt"]), (res["distinct"].astype(np.int16), res["cash"].astype(np.float64), res["eq"].astype(np.float64))


# ═════════════ 乾跑對頻率表（G0） ═════════════
def step_dry(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    G["sha"] = sha_main()
    LAGP.setup(a, G["sha"]); FQ.install_A(G["sha"])
    fz = np.load(os.path.join(FQ.OUT, "daily.npz"))
    out = {}
    for world, v2 in (("main", False), ("early", False), ("early", True)):
        Wd = prep(world, a, v2=v2); Wd["BR"] = bench_rows(Wd)
        jobs = [(world, A, K, S, H, True) for A in AS for K in KS for S in SS for H in HS]
        with Pool(a.procs) as pool:
            res = pool.map(_cell_job, jobs, chunksize=1)
        dd = []; cd = []; eqd = []
        for jb, (_, cn, (dist, cash, eq)) in zip(jobs, res):
            ref = fz[f"{world}__主讀法__{jb[1]}__{jb[2]}__{jb[3]}__{jb[4]}"]
            t0 = Wd["BL"]["主讀法"][0][0]; T = Wd["T"]
            dd.append(int(np.sum(ref[0][t0:T + 1].astype(int) != dist[t0:T + 1].astype(int))))
            cd.append(float(np.max(np.abs(ref[1][t0:T + 1].astype(float) - cash[t0:T + 1]))))
            eqd.append(float(np.max(np.abs(eq - 1.0))))
        key = f"{world}|{Wd['ver']}"
        out[key] = {"格數": len(jobs), "持股數不同日數（合計）": int(sum(dd)), "有不同的格": int(sum(1 for x in dd if x)), "現金最大差": max(cd), "權益偏離1最大": max(eqd)}
        log(f"[乾跑 {key}] {out[key]}")
        W.pop(world)
    out["判讀"] = "主段、早年 eotc 版：應 0 不同（＝ 頻率表）；早年 reduce_v2 版：差異來自旗標與成員換版面（照報）"
    json.dump(out, open(os.path.join(OUT, "dry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ═════════════ 正式跑 ═════════════
def pick_cell(TM):
    ex = TM[TM["段"] == "探索"].copy()
    ex["退化"] = (ex["平均持股"] < 5) | (ex["平均現金"] > 0.30)
    cand = ex[~ex["退化"]].copy()
    pool_ = cand[cand["標籤"] == "合格"] if (cand["標籤"] == "合格").any() else cand
    oi = lambda col, seq: pool_[col].map({v: i for i, v in enumerate(seq)})
    pool_ = pool_.assign(_a=oi("A", AS), _k=oi("K", KS), _h=oi("H", HS), _s=oi("S", SS))
    best = pool_.sort_values(["比值", "年化", "_a", "_k", "_h", "_s"], ascending=[False, False, True, True, True, True]).iloc[0]
    return {"A": best["A"], "K": int(best["K"]), "S": best["S"], "H": int(best["H"])}, ex


def judge(TM, ch):
    sel = TM[(TM["A"] == ch["A"]) & (TM["K"] == ch["K"]) & (TM["S"] == ch["S"]) & (TM["H"] == ch["H"])].set_index("段")
    labs = {}
    for sg in ("確認", "早年A", "早年B"):
        r = sel.loc[sg]
        nj = (r["平均現金"] > 0.30) or (r["段內走完批數"] == 0)
        labs[sg] = {"標籤": r["標籤"], "依構造不可判定": bool(nj) if sg != "確認" else False, "平均現金": r["平均現金"], "段內走完批數": int(r["段內走完批數"])}
    use = [labs["確認"]["標籤"]] + [labs[s]["標籤"] for s in ("早年A", "早年B") if not labs[s]["依構造不可判定"]]
    fin_ = min(use, key=lambda z: RANKL.get(z, -1))
    word = {"合格": "暫定合格", "另列": "另列（最多暫定）", "不合格": "不合格"}.get(fin_, fin_)
    only = all(labs[s]["依構造不可判定"] for s in ("早年A", "早年B"))
    return labs, word, only


def ind_desc(Wd, I, res, ch):
    """G5：吃到幾成、3 年 2 倍。"""
    rows = []; n = len(Wd["cal"]); T = Wd["T"]; tri = Wd["TRI"]
    for x in res["binfo"]:
        b = x["b"]; mat = x["mat"]
        for i in [z for z in x["產業"].split("｜") if z]:
            v = I.get(i)
            r = {"世界": Wd["name"], "批日": str(Wd["cal"][b].date()), "產業": i}
            if v is None or not np.isfinite(v[b - 1]):
                r["缺"] = 1; rows.append(r); continue
            Is = v[b - 1]; low = np.nanmin(v[max(0, b - 250):b]); post = v[b:min(n, b + 500)]; top = np.nanmax(post) if np.isfinite(post).any() else np.nan
            den = math.log(top / low) if (np.isfinite(top) and top > low) else np.nan
            ee = min(mat, T); Ie = v[ee]
            top2 = np.nanmax(v[b:ee + 1])
            den2 = math.log(top2 / low) if (np.isfinite(top2) and top2 > low) else np.nan
            r.update({"缺": 0, "未滿500日": int(b + 500 > T + 1), "持有到尾": int(mat > T),
                      "吃到幾成": math.log(Ie / Is) / den if (np.isfinite(den) and np.isfinite(Ie)) else np.nan,
                      "吃到幾成_頂取持有窗": math.log(Ie / Is) / den2 if (np.isfinite(den2) and np.isfinite(Ie)) else np.nan})
            if b + 749 <= T and np.isfinite(v[b + 749]):
                ri = v[b + 749] / Is - 1; rm = tri[b + 749] / tri[b - 1] - 1
                r.update({"3年產業": ri, "3年大盤": rm, "碰到2倍": int(ri > 2 * rm and ri > 0), "碰到2倍_另": int((1 + ri) > 2 * (1 + rm))})
            rows.append(r)
    return rows


def realX(Wd, sids):
    from backtest import researchSlip as SL
    D.DATA = V2 if (Wd["name"] == "early" and Wd["ver"] == "reduce_v2") else Wd["C"]["data"]
    X = {}
    for s in sids:
        X[s] = SL.stock_extra(s, "twse" if Wd["ver"] == "reduce_v2" else Wd["C"]["mk"].get(s, "twse"), Wd["cal"], len(Wd["cal"]))
    return X


def step_run(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    T00 = time.time()
    REGI = FQ.reg_check()
    G["sha"] = sha_main()
    LAGP.setup(a, G["sha"]); FQ.install_A(G["sha"])
    log(f"===== researchIndRevHold run｜讀法寫死 {TIME}｜main {G['sha'][:10]}｜登錄 seq2 {REGI['seq2']['相符']} =====")
    META = {"讀法寫死": TIME, "main": G["sha"], "登錄": REGI, "成本": COST}
    rows, cnts, EQ = [], {}, {}
    for world in ("main", "early"):
        Wd = prep(world, a); Wd["BR"] = bench_rows(Wd)
        META.setdefault("基準", {})[world] = {sg: {"大盤": v["大盤"], "0050": v["0050"]} for sg, v in Wd["BR"].items()}
        jobs = [(world, A, K, S, H, False) for A in AS for K in KS for S in SS for H in HS]
        t0 = time.time()
        with Pool(a.procs) as pool:
            res = pool.map(_cell_job, jobs, chunksize=1)
        for jb, (rr, cn, dd) in zip(jobs, res):
            rows += rr; cnts["|".join(map(str, jb[:5]))] = cn; EQ["|".join(map(str, jb[:5]))] = dd[2]
        log(f"[{world}] 36 格 {time.time() - t0:.0f}s｜基準 {json.dumps(META['基準'][world], ensure_ascii=False, default=float)}")
        W.pop(world)
    # 0050 錨（主窗）
    TM = pd.DataFrame(rows)
    TM.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")
    ch, EX = pick_cell(TM)
    labs, word, only = judge(TM, ch)
    ck = f"{ch['A']}|K{ch['K']}|{ch['S']}|H{ch['H']}"
    META["挑格"] = {"退化格數（探索）": int(EX["退化"].sum()), "探索合格格數": int((EX["標籤"] == "合格").sum()), "探索另列格數": int((EX["標籤"] == "另列").sum()),
                  "挑中": ck, "挑中參數": ch, "各段": labs, "判定": word, "早年不可判只看確認段": only,
                  "確認段合格格數": int(((TM["段"] == "確認") & (TM["標籤"] == "合格")).sum()),
                  "確認段另列格數": int(((TM["段"] == "確認") & (TM["標籤"] == "另列")).sum())}
    log(f"[挑格] {json.dumps(META['挑格'], ensure_ascii=False, default=float)}")
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # ── 挑中格細項、對照、丙
    CTRL = {}; BAT = []; YR = []; CDESC = []; VAR = []; IC = []; EQS = {}
    for world in ("main", "early"):
        Wd = prep(world, a); Wd["BR"] = bench_rows(Wd); Wd["name"] = world
        BL = Wd["BL"]["主讀法"]; picks = Wd["PK"]["主讀法"][(ch["A"], ch["K"])]
        res = sim_book(Wd, BL, picks, ch["K"], ch["S"], ch["H"])
        assert np.array_equal(res["eq"], EQ[f"{world}|{ch['A']}|{ch['K']}|{ch['S']}|{ch['H']}"])
        EQS[world] = res["eq"]
        for x in res["binfo"]:
            BAT.append({"世界": world, "批日": str(Wd["cal"][x["b"]].date()), "營收月": x["M"], "產業": x["產業"], "份額": x["Aj"], "買檔數": x["買檔數"],
                        "到期": str(Wd["cal"][x["mat"]].date()) if x["mat"] < len(Wd["cal"]) else "曆外", "走完": x["完"], "批報酬": x["批報酬"],
                        "段": next((sg for sg, (a_, z_) in segp(Wd).items() if a_ <= x["b"] <= z_), "")})
        # 每月重複同產業
        sp = segp(Wd)
        for sg, (a_, z_) in sp.items():
            js = [j for j, (b, _) in enumerate(BL) if a_ <= b <= z_]
            seq = [picks[j] for j in js]
            rep = [len(set(seq[k]) & set(seq[k - 1])) / len(seq[k]) for k in range(1, len(seq)) if seq[k]]
            cc = Counter(i for p in seq for i in p)
            for i, v in cc.most_common():
                IC.append({"世界": world, "段": sg, "產業": i, "批次數": v})
            CTRL.setdefault("重複率", {})[sg] = float(np.mean(rep)) if rep else np.nan
        cal = Wd["cal"]; t0 = BL[0][0]; T = Wd["T"]
        yr = PRE.year_rets(res["eq"], cal, t0, T); yb = PRE.year_rets(Wd["TRI"] / Wd["TRI"][t0], cal, t0, T); y5 = PRE.year_rets(Wd["bench0050"] / Wd["bench0050"][t0], cal, t0, T)
        for y in yr:
            YR.append({"世界": world, "年": y, "挑中格": yr[y], "大盤報酬指數": yb[y], "0050": y5[y], "註": "首年自開帳日起" if y == str(cal[t0].year) else ""})
        # 主對照：前件挑中格在本件設定重跑
        C = Wd["C"] if world == "main" else dict(Wd["C"], P=Wd["PX"], dl=Wd["dl2"], SF={}, reb={}, pk={}, nomc=Counter())
        if world == "early":
            PRE.attach_months(C)
        win = PRE.MAIN_W if world == "main" else PRE.EARLY_A
        p0, p1 = SC.pos_of(cal, win[0]), SC.pos_of(cal, win[1])
        rp = PRE.sim_ind(C, p0, p1, dict(PRE_CH, ver="pit", order="top", elig="W1"))
        for sg, (a_, z_) in sp.items():
            if a_ >= p0 and z_ <= p1 + 1:
                CTRL.setdefault("前件挑中格_本件設定重跑", {})[sg] = dict(zip(("年化", "回落", "比值"), SC.seg_metrics(rp["eq"], a_, min(z_, p1))))
        # 全產業等權
        allp = [PRE.ranked("pit", "A1", M, "names") for b, M in BL]
        ra = sim_book(Wd, BL, allp, None, ch["S"], ch["H"], divK=[max(len(p), 1) for p in allp])
        for sg, (a_, z_) in sp.items():
            CTRL.setdefault("全產業等權", {})[sg] = cell_stats(Wd, ra, a_, z_, ch["H"], BL)
            CTRL.setdefault("挑中格", {})[sg] = cell_stats(Wd, res, a_, z_, ch["H"], BL)
            CTRL.setdefault("基準", {})[sg] = {"大盤": Wd["BR"][sg]["大盤"], "0050": Wd["BR"][sg]["0050"]}
        # 丙
        I = PRE.ind_index(dict(Wd["C"], P=Wd["PX"]), "W1" if world == "main" else "X")
        CDESC += ind_desc(Wd, I, res, ch)
        # 現實版
        need = sorted({s for j, (b, _) in enumerate(BL) for i in picks[j] for s in (Wd["MEM"][b][0].get(i, [])[:20] if ch["S"] == "S1" else Wd["MEM"][b][0].get(i, []))
                       if s in Wd["PX"]})
        X = realX(Wd, need)
        for nm, rx in (("現實版（C1 0.3%＋C2 50 萬＋C4）", dict(s=0.003, cap=CAP, c4=True)), ("現實版＋C5 低消 20 元", dict(s=0.003, cap=CAP, c4=True, m5=20))):
            rr = sim_book(Wd, BL, picks, ch["K"], ch["S"], ch["H"], real=dict(rx, X=X))
            for sg, (a_, z_) in sp.items():
                st = cell_stats(Wd, rr, a_, z_, ch["H"], BL)
                VAR.append({"版本": nm, "世界": world, "段": sg, **st, "標籤": SC.label(st["年化"], st["回落"], *Wd["BR"][sg]["大盤"][:2]) if st["回落"] < 0 else "—"})
        W.pop(world)
    pm = json.load(open(os.path.join(PRE.OUT, "meta.json"), encoding="utf-8"))
    CTRL["前件挑中格_原數字"] = {"探索": pm["挑格"]["探索"], "確認": pm["挑格"]["確認"], "早年A（前件早年，只上市 3edc0e2206）": pm["挑格"]["早年"]}
    pd.DataFrame(BAT).to_csv(os.path.join(OUT, "chosen_batches.csv"), index=False, float_format="%.8g")
    pd.DataFrame(IC).to_csv(os.path.join(OUT, "industry_counts.csv"), index=False)
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "years.csv"), index=False, float_format="%.8g")
    CD = pd.DataFrame(CDESC); CD.to_csv(os.path.join(OUT, "c_desc.csv"), index=False, float_format="%.8g")
    pd.DataFrame(VAR).to_csv(os.path.join(OUT, "variants.csv"), index=False, float_format="%.10g")
    np.savez_compressed(os.path.join(OUT, "eq.npz"), main=EQS["main"], early=EQS["early"])
    BD = pd.DataFrame(BAT); ok = CD[CD.get("缺", 0) == 0] if len(CD) else CD
    DES = {}
    for w_, g in BD.groupby("世界"):
        for sg, gg in g.groupby("段"):
            x = gg["批報酬"].dropna()
            DES[f"批報酬|{w_}|{sg}"] = {"走完批數": int(len(x)), "平均": float(x.mean()) if len(x) else None, "中位": float(x.median()) if len(x) else None}
    if len(ok):
        ok = ok.assign(段=[next((sg for sg, (x0, x1) in FQ.SEGS[w_].items() if x0 <= d <= x1), "") for w_, d in zip(ok["世界"], ok["批日"])])
        for (w_, sg), g in ok.groupby(["世界", "段"]):
            g3 = g.dropna(subset=["碰到2倍"]) if "碰到2倍" in g else g.iloc[:0]
            DES[f"丙|{w_}|{sg}"] = {"批×產業": int(len(g)), "吃到幾成中位": float(g["吃到幾成"].median()), "吃到幾成中位_頂取持有窗": float(g["吃到幾成_頂取持有窗"].median()),
                                   "吃到幾成中位（剔持有到尾）": float(g.loc[g["持有到尾"] == 0, "吃到幾成"].median()) if (g["持有到尾"] == 0).any() else None,
                                   "3年可算": int(len(g3)), "碰到2倍比例": float(g3["碰到2倍"].mean()) if len(g3) else None,
                                   "碰到2倍比例_另": float(g3["碰到2倍_另"].mean()) if len(g3) else None}
    CTRL["描述"] = DES
    # 先驗 ⑤（S3 vs S1）
    p5 = {}
    for sg in ("探索", "確認"):
        x = TM[TM["段"] == sg].pivot_table(index=["A", "K", "H"], columns="S", values="年化")
        d = (x["S3"] - x["S1"]).abs()
        p5[sg] = {"18 組 |S3−S1| ＜ 3 點比例": float((d < 0.03).mean()), "中位差": float((x["S3"] - x["S1"]).median()), "最大絕對差": float(d.max())}
    CTRL["先驗5"] = p5
    META["對照"] = CTRL; META["計數"] = cnts; META["耗時秒"] = round(time.time() - T00)
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    json.dump(CTRL, open(os.path.join(OUT, "controls.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T00:.0f}s")


# ═════════════ 隨機 1,000 次（G4） ═════════════
def _rand_job(args):
    world, r0, r1 = args
    Wd = W[world]; ch = G["ch"]; BL = Wd["BL"]["主讀法"]; mine = Wd["PK"]["主讀法"][(ch["A"], ch["K"])]
    names = Wd["NAMES"]; out = []
    for r in range(r0, r1):
        rng = np.random.default_rng([SEED, r])
        ps = []
        for j, (b, M) in enumerate(BL):
            nm = names[j]; nb = len(mine[j])
            ps.append([nm[k] for k in rng.permutation(len(nm))][:nb] if nm else [])
        res = sim_book(Wd, BL, ps, ch["K"], ch["S"], ch["H"])
        row = {"世界": world, "r": r}
        for sg, (a_, z_) in segp(Wd).items():
            c, m, rt = SC.seg_metrics(res["eq"], a_, min(z_, Wd["T"]))
            row.update({f"{sg}_年化": c, f"{sg}_回落": m, f"{sg}_比值": rt, f"{sg}_平均持股": float(res["distinct"][a_:min(z_, Wd['T']) + 1].mean()),
                        f"{sg}_平均現金": float(np.nanmean(res["cash"][a_:min(z_, Wd['T']) + 1]))})
        out.append(row)
    return out


def step_rand(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    G["sha"] = sha_main()
    LAGP.setup(a, G["sha"]); FQ.install_A(G["sha"])
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    G["ch"] = META["挑格"]["挑中參數"]
    rows = []
    for world in ("main", "early"):
        Wd = prep(world, a)
        Wd["NAMES"] = [PRE.ranked("pit", G["ch"]["A"], M, "names") for b, M in Wd["BL"]["主讀法"]]
        t0 = time.time()
        jobs = [(world, r0, min(r0 + 50, a.reps)) for r0 in range(0, a.reps, 50)]
        with Pool(a.procs) as pool:
            for rr in pool.imap_unordered(_rand_job, jobs):
                rows += rr
        log(f"[隨機 {world}] {a.reps} 次｜{time.time() - t0:.0f}s")
        W.pop(world)
    RD = pd.DataFrame(rows).sort_values(["世界", "r"])
    RD.to_csv(os.path.join(OUT, "random.csv.gz"), index=False, float_format="%.8g", compression={"method": "gzip", "mtime": 0})
    TM = pd.read_csv(os.path.join(OUT, "cells.csv"))
    ch = G["ch"]
    sel = TM[(TM["A"] == ch["A"]) & (TM["K"] == ch["K"]) & (TM["S"] == ch["S"]) & (TM["H"] == ch["H"])].set_index("段")
    RS = {}
    for world, g in RD.groupby("世界"):
        for sg in FQ.SEGS[world]:
            x = g[f"{sg}_年化"].to_numpy(float); rr_ = g[f"{sg}_比值"].to_numpy(float)
            me = sel.loc[sg]
            RS[sg] = {"次數": int(len(g)), "隨機年化中位": float(np.nanmedian(x)), "p10": float(np.nanquantile(x, .1)), "p90": float(np.nanquantile(x, .9)),
                      "隨機回落中位": float(np.nanmedian(g[f"{sg}_回落"])), "p_年化（隨機≥挑中）": float(np.nanmean(x >= me["年化"])),
                      "p_比值（隨機≥挑中）": float(np.nanmean(rr_ >= me["比值"])), "隨機贏大盤比例": float(np.nanmean(x > me["大盤年化"])),
                      "隨機合格比例": float(np.nanmean((x > me["大盤年化"]) & (rr_ >= me["大盤比值"]))),
                      "隨機平均持股中位": float(np.nanmedian(g[f"{sg}_平均持股"])), "挑中平均持股": float(me["平均持股"]),
                      "持股倍數（隨機÷挑中）": float(np.nanmedian(g[f"{sg}_平均持股"]) / me["平均持股"]),
                      "隨機平均現金中位": float(np.nanmedian(g[f"{sg}_平均現金"])), "挑中平均現金": float(me["平均現金"])}
    META["隨機"] = RS
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[隨機] {json.dumps(RS, ensure_ascii=False, default=float)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=["prep_v2", "dry", "run", "rand"])
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--sha", default=None)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    {"prep_v2": step_prep_v2, "dry": step_dry, "run": step_run, "rand": step_rand}[a.step](a)


if __name__ == "__main__":
    main()

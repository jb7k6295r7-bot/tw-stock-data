# -*- coding: utf-8 -*-
"""額外策略「營量 v1、營飆 v1：名單出現族群營收轉強就買、滿了就換掉持股裡最差那檔」【頻率表・乾跑】——回測線計算子代理，2026-11-11。
登錄：台股策略線 seq1（sha 369b04d9e487d4ce，6189 B）〈營量營飆族群轉強出現就換掉持股最差那檔_額外策略_組合層登錄〉
發號：裁定線 seq504 §二（N_組合 ＋2；最多「合格（暫定）」；8 岔路照登錄；退化線：換掉 ＜ 10% 或買進重疊 ≥ 90% ⇒ 先回信、等同原版；
      〈四十九〉用「有換股的不同月數」＜ 24 ⇒ 還沒測（依構造）；換錯的代價必報（正式跑）；先交頻率表，⛔ 不附報酬）

⛔ 乾跑：不讀、不算、不印任何報酬。原版路徑 ＝ researchGroupRevUp_freq.cell_sig／run_engine（dry：毛報酬全 0、價格全 1）⇒ 買進、持有是純構造量。
⛔ 族群旗標不另寫：直接讀 researchGroupRevUp_freq --groups industry 產出的 ~/grpwork/groups_<世界>_industry.pkl 的 grp 欄
   （主段＝產業分群檔、早年＝自建 v2；commit 8f826608e5／e134c45efb）；世界 ＝ ~/grpwork/world_<世界>.pkl（同上）。
⛔ 不改策略鎖內任何檔（research11、rerun17、data… 只 import）；跑完 strategy_lock --check。
⛔ 不改 researchGroupRevUp_freq.py（只 import 其函式）⇒ 舊輸出逐位元不變。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSwapWorst_freq [--procs 3]
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchSwapWorst_freq

═══ 讀法（寫死於 2026-11-11（台北），在算任何本件數字之前；★ ＝ 登錄沒寫清楚、執行者定）═══
 W0 登錄驗證：信箱登錄全文去掉末行 pw1 戳記後 sha256 前 16 碼 ＝ 369b04d9e487d4ce、整檔 6189 B；信箱有裁定 seq504 件；不符即停
 W1 原版 ＝ researchGroupRevUp_freq 的「原版」（營量 r0 一條；營飆種子 r ＝ 0～199，報中位〔p10～p90〕與 r0）；
    閘 G1：本檔重跑的原版買進 ＝ ~/grpwork/sim_<世界>_industry.pkl 的原版買進（逐種子逐筆）
 W2 觸發（登錄 §二）：引擎第 t 日（＝ 觸發日 t−1 的隔天、進場日）開盤時——
    候選 ＝ 引擎看得到的列（cell_sig：營飆含 0050 閘、xpos 有值）中 entry_pos ＝ t 者
    ★ 「不在持股中」＝ 排程出場（與停止交易強制出場）在 t 結清後仍持有者以外（＝ 引擎 held 口徑；持有區間 [買進日, 賣出日)，a ＜ t ＜ b 才算持有）
    觸發股 ＝ 候選中 grp＝1、不在持股中、而且原版第 t 日沒買到它
    ★ 引擎先把空槽補滿（逐日買進數 ＝ min(未持有候選, 空槽)，閘 G3 驗）⇒ 原版沒買到的未持有候選一定是「買完已滿槽」
      ⇒ 「有空位 ⇒ 買」＝ 原版本來就買的族群轉強候選（報筆數，＝ 原版行為）；觸發股全部屬「沒空位 ⇒ 換」（另報買完仍有空槽的觸發筆數，應 ＝ 0）
 W3 被換候選池（★）＝ 觸發日 t−1 收盤持有、且第 t 日沒有依原版出場者 ＝ #{a ＜ t ＜ b}
    「本來隔天就要依原版出場的持股」＝ #{a ＜ t，b ＝ t}（含停止交易強制出場在 t 者）⇒ 排除、照原版補（報次數）
    ★ 當天（第 t 日開盤）原版剛買進的不在池內（觸發日收盤時尚未持有，登錄的「買進日開盤起到觸發日收盤」無定義）
 W4 換股數（第 t 日）＝ min(觸發股數, 池大小)；觸發股 ＞ 池 ⇒ 多出的觸發股不買（報筆數）
    ⛔ 換掉哪一檔要價格（買進以來還原報酬最差）⇒ 本頻率表不決定、不算之後持股路徑
 W5 ★★ 第一層近似：以原版持股路徑為準估觸發與換股次數。真路徑上每次換股都會改變之後的持股、空槽日與觸發
    ⇒ 本表的換股次數、月數、重疊度都是「原版路徑上」的近似，正式跑才是真路徑。近似的範圍（報）：
      ・換進那檔佔槽到 t＋H，被換那檔原本 b 就空出 ⇒ 該槽之後每一次換手日都後移 (t＋H) − b ∈ [H − max(b−t), H − min(b−t)] 日（≥ 1）
        ⇒ 該槽之後的買進日與原版不同；報池內「距原版到期日數 b−t」分布（池全體，⛔ 不是被換那檔）
      ・買進重疊 近似 A（上限）＝ 原版買進 ÷ (原版買進 ＋ 換股數)（原版買進全保留、換進的另加）；
        近似 B ＝ max(0, (原版買進 − 換股數) ÷ 原版買進)（每次換股只擠掉後續一筆原版買進、不連鎖；換股多於原版買進 ⇒ 截 0）；真值可能低於 B（連鎖後移），⛔ 乾跑定不出下限
 W6 頻率表（每 世界 × 策略 × 段 × 種子；段以第 t 日（買進日）歸段：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、早年 2005-02-01～2014-12-31 只描述）
    ① 原版買進、觸發日數、觸發股數、換股數、換股 ÷ 原版買進（對 10%）、有換股的不同月數（對 24）、每年換股數
    ② 滿槽觸發（＝ 觸發股數）vs 有空槽直接買（原版本來就買的族群轉強候選）；同日觸發股數分布；池大小分布；觸發股 ＞ 池的筆數
    ③ 排除「隔天本來就要出場」：觸發日中有排除的日數、排除持股筆數
    ④ 池全體的「已持有天數 t−a」「距原版到期 b−t」分布（被換那檔要價格 ⇒ 正式跑）；平均持股（近似 ＝ 原版）、年換手近似 ＝ (原版買進＋換股)÷N÷年
    ⑤ seq377 等價檢查：有候選日中有觸發的比例；族群旗標在候選中的比例（≥95% 恆真／≤5% 恆假）；換股數 ＝ 0 ⇒ 恆等於原版
 必附：「額外策略、與正式營量營飆分開；正式規則不動」「看過族群轉強 seq2 結果與原版拆兩批才提」；早年附 reduce_v2 約 0.3% 註
輸出 backtest/resultsSwapWorst/freq/：cells.csv、yearly.csv、monthly_r0.csv、trigger_days_r0.csv、summary.json、結果.md
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
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
from backtest import researchGroupRevUp_freq as M           # noqa: E402  族群旗標、引擎呼叫（⛔ 不另寫）

TIME = "2026-11-11（台北）"
OUT = "backtest/resultsSwapWorst/freq"
MAILBOX = M.MAILBOX
REG_SHA, REG_BYTES = "369b04d9e487d4ce", 6189
RULING = "*seq504*"
NSEED = int(os.environ.get("SW_NSEED", "200"))
STRATS = M.STRATS
SEGN = M.SEGN


def log(x):
    print(f"[{time.strftime('%H:%M:%S')}] {x}", flush=True)


# ═════════════ W0 ═════════════
def check_reg():
    fs = glob.glob(os.path.join(MAILBOX, "**", f"*sha{REG_SHA}*"), recursive=True)
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到 sha{REG_SHA} 登錄全文")
    b = open(fs[0], "rb").read()
    i = b.rfind(b"<!-- pw1")
    h = hashlib.sha256(b[:i]).hexdigest()[:16]
    if not (h == REG_SHA and len(b) == REG_BYTES):
        raise SystemExit(f"⛔ 登錄 sha／大小不符：{h}／{len(b)} B")
    rl = glob.glob(os.path.join(MAILBOX, "**", RULING), recursive=True)
    if not rl:
        raise SystemExit("⛔ 信箱找不到裁定 seq504 件")
    return {"檔": os.path.basename(fs[0]), "sha16": h, "bytes": len(b), "裁定": os.path.basename(rl[0])}


# ═════════════ W2～W4：逐日觸發（純構造、無價格）═════════════
def trigger_days(sig, buys, iv, N):
    """回 {t: dict}：每個有候選的進場日 t。sig 需 sid、entry_pos、grp；iv ＝ intervals(buys, sells)（sid, a, b）。"""
    byt = defaultdict(dict)
    for t, s, f in zip(sig["entry_pos"].to_numpy(int), sig["sid"].astype(str).to_numpy(), sig["grp"].to_numpy(bool)):
        byt[int(t)][s] = bool(byt[int(t)].get(s, False) or f)
    bought = defaultdict(set)
    for t, s in buys:
        bought[int(t)].add(s)
    bys = defaultdict(list)
    for s, a, b in iv:
        bys[s].append((a, b))
    A = np.array([a for _, a, _ in iv], int); Bv = np.array([b for _, _, b in iv], int)
    out = {}
    for t in sorted(byt):
        cands = byt[t]
        held = {s for s in cands if any(a < t < b for a, b in bys.get(s, ()))}
        nonheld = [s for s in cands if s not in held]
        bt = bought.get(t, set())
        trig = sorted(s for s in nonheld if cands[s] and s not in bt)
        direct = sorted(s for s in nonheld if cands[s] and s in bt)
        inpool = (A < t) & (Bv > t)
        excl = (A < t) & (Bv == t)
        pool = int(inpool.sum())
        nb = len(bt)
        out[t] = {"nc": len(cands), "nc_grp": int(sum(cands.values())), "nonheld": len(nonheld), "nb": nb, "direct": direct,
                  "trig": trig, "pool": pool, "excl": int(excl.sum()), "free_after": N - pool - nb,
                  "swaps": min(len(trig), pool), "g3_bad": int(nb != max(0, min(len(nonheld), N - pool))),
                  "pool_age": (t - A[inpool]).astype(int), "pool_rem": (Bv[inpool] - t).astype(int)}
    return out


def seg_stats(td, buys, cal, x, y, N, H):
    """段 [x, y]（以第 t 日歸段）的頻率量。"""
    days = {t: d for t, d in td.items() if x <= t <= y}
    nbuy = sum(1 for t, _ in buys if x <= t <= y)
    trig_days = [t for t, d in days.items() if d["trig"]]
    sw_days = [t for t in trig_days if days[t]["swaps"] > 0]
    ntrig = sum(len(days[t]["trig"]) for t in trig_days)
    nsw = sum(days[t]["swaps"] for t in trig_days)
    ndirect = sum(len(d["direct"]) for d in days.values())
    months_sw = sorted({cal[t].strftime("%Y-%m") for t in sw_days})
    months_all = sorted({cal[t].strftime("%Y-%m") for t in range(x, y + 1)})
    pools = np.array([days[t]["pool"] for t in trig_days], int)
    per_day = Counter(min(len(days[t]["trig"]), 4) for t in trig_days)
    ages = np.concatenate([days[t]["pool_age"] for t in trig_days]) if trig_days else np.array([], int)
    rems = np.concatenate([days[t]["pool_rem"] for t in trig_days]) if trig_days else np.array([], int)
    pmin_rem = np.array([days[t]["pool_rem"].min() for t in trig_days if days[t]["pool"] > 0], int)
    pmax_rem = np.array([days[t]["pool_rem"].max() for t in trig_days if days[t]["pool"] > 0], int)
    yrs = (y - x + 1) / 245.0
    cand_rows = sum(d["nc"] for d in days.values()); cand_grp = sum(d["nc_grp"] for d in days.values())
    cdays = [t for t, d in days.items() if d["nonheld"] > 0]

    def qd(a):
        a = np.asarray(a, float)
        return {"中位": float(np.median(a)), "p10": float(np.percentile(a, 10)), "p90": float(np.percentile(a, 90)),
                "最小": float(a.min()), "最大": float(a.max())} if len(a) else None

    yearly = Counter(cal[t].year for t in trig_days for _ in range(days[t]["swaps"]))
    return {
        "原版買進": nbuy, "觸發日數": len(trig_days), "有換股日數": len(sw_days), "觸發股數": ntrig, "換股數": nsw,
        "換股÷原版買進": (nsw / nbuy) if nbuy else None,
        "有換股的不同月數": len(months_sw), "段月數": len(months_all), "有換股月份": months_sw,
        "滿槽觸發": ntrig, "觸發但買完仍有空槽": int(sum(1 for t in trig_days if days[t]["free_after"] > 0)),
        "有空槽直接買（族群轉強、原版行為）": ndirect,
        "觸發股多於池而未買": int(sum(len(days[t]["trig"]) - days[t]["swaps"] for t in trig_days)),
        "同日觸發股數分布": {("4+" if k == 4 else str(k)): int(v) for k, v in sorted(per_day.items())},
        "池大小": qd(pools), "池大小分布": {str(k): int(v) for k, v in sorted(Counter(pools.tolist()).items())},
        "池為0的觸發日": int((pools == 0).sum()),
        "排除隔天出場_日數": int(sum(1 for t in trig_days if days[t]["excl"] > 0)),
        "排除隔天出場_持股筆數": int(sum(days[t]["excl"] for t in trig_days)),
        "池全體_已持有天數": qd(ages), "池全體_距原版到期": qd(rems),
        "池內最近到期_距到期": qd(pmin_rem), "池內最晚到期_距到期": qd(pmax_rem),
        "槽後移日數範圍": ({"最小(H−max)": float(H - np.median(pmax_rem)), "最大(H−min)": float(H - np.median(pmin_rem)), "註": "以觸發日中位數"} if len(pmin_rem) else None),
        "買進重疊_近似A上限": (nbuy / (nbuy + nsw)) if nbuy else None,
        "買進重疊_近似B": (max(0.0, (nbuy - nsw) / nbuy)) if nbuy else None,
        "年換手近似": ((nbuy + nsw) / N / yrs) if yrs > 0 else None,
        "原版年換手": (nbuy / N / yrs) if yrs > 0 else None,
        "有候選日": len(cdays), "有觸發日÷有候選日": (len(trig_days) / len(cdays)) if cdays else None,
        "候選列": cand_rows, "候選族群轉強比例": (cand_grp / cand_rows) if cand_rows else None,
        "G3不符日": int(sum(d["g3_bad"] for d in days.values())),
        "每年換股": {str(k): int(v) for k, v in sorted(yearly.items())},
    }


_W: dict = {}


def job(args):
    wn, st, r = args
    P = _W["P"]; S = _W["S"]; NP = P["NP"]; SF = P["SF"]; N = STRATS[st]["N"]; H = STRATS[st]["H"]
    sig = M.cell_sig(S, st, "原版")
    buys, sells = M.run_engine(sig, st, "原版", r, _W["ones"], NP, SF)
    g1 = (buys == _W["simbuys"].get((st, r)))
    iv = M.intervals(buys, sells, NP)
    td = trigger_days(sig, buys, iv, N)
    res = {"st": st, "r": r, "G1": bool(g1), "seg": {}}
    for sg, (x, y) in P["segp"].items():
        if sg not in SEGN[wn]:
            continue
        res["seg"][sg] = seg_stats(td, buys, P["cal"], x, y, N, H)
    if r == 0:
        cal = P["cal"]; rv = dict(zip(sig["sid"].astype(str) + "@" + sig["entry_pos"].astype(str), sig["relvol"])) if st == "營量" else {}
        rows = []
        for t, d in sorted(td.items()):
            if not d["trig"]:
                continue
            tr = d["trig"]
            if st == "營量":
                tr = sorted(tr, key=lambda s: -(rv.get(f"{s}@{t}") if np.isfinite(rv.get(f"{s}@{t}", np.nan)) else -1e18))
            sg = next((k for k, (x, y) in P["segp"].items() if k in SEGN[wn] and x <= t <= y), "段外")
            rows.append({"世界": wn, "策略": st, "種子": r, "段": sg, "觸發日": cal[t - 1].strftime("%Y-%m-%d") if t > 0 else "",
                         "換股日(第t日)": cal[t].strftime("%Y-%m-%d"), "候選數": d["nc"], "未持有候選": d["nonheld"], "原版當日買進": d["nb"],
                         "族群轉強直接買": len(d["direct"]), "觸發股數": len(tr), "觸發股": " ".join(tr), "被換候選池": d["pool"],
                         "排除隔天出場": d["excl"], "換股數": d["swaps"], "買完空槽": d["free_after"],
                         "池最近到期距日": int(d["pool_rem"].min()) if d["pool"] else None,
                         "池最晚到期距日": int(d["pool_rem"].max()) if d["pool"] else None})
        res["rows"] = rows
        mon = defaultdict(lambda: [0, 0, 0])
        for t, d in td.items():
            m = cal[t].strftime("%Y-%m")
            mon[m][0] += len(d["trig"]); mon[m][1] += d["swaps"]
        for t, _ in buys:
            mon[cal[t].strftime("%Y-%m")][2] += 1
        res["monthly"] = [{"世界": wn, "策略": st, "月": m, "觸發股數": v[0], "換股數": v[1], "原版買進": v[2]} for m, v in sorted(mon.items())]
    return res


def run_world(wn, procs):
    P = pickle.load(open(os.path.join(M.WORK, f"world_{wn}.pkl"), "rb"))
    Gp = pickle.load(open(os.path.join(M.WORK, f"groups_{wn}_industry.pkl"), "rb"))
    SIM = pickle.load(open(os.path.join(M.WORK, f"sim_{wn}_industry.pkl"), "rb"))
    _W["P"] = P; _W["S"] = Gp["S"]
    _W["ones"] = {s: np.ones(P["NP"]) for s in P["sids"]}
    _W["simbuys"] = {(x["st"], x["r"]): x["ver"]["原版"]["buys"] for x in SIM}
    jobs = [(wn, "營量", 0)] + [(wn, "營飆", r) for r in range(NSEED)]
    t0 = time.time(); out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            out.append(res)
            if (i + 1) % 50 == 0:
                log(f"  {wn} {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    out.sort(key=lambda z: (z["st"], z["r"]))
    log(f"[{wn}] {len(out)} 件 {time.time() - t0:.0f}s")
    return P, out


NUMK = ["原版買進", "觸發日數", "有換股日數", "觸發股數", "換股數", "換股÷原版買進", "有換股的不同月數", "段月數", "滿槽觸發", "觸發但買完仍有空槽",
        "有空槽直接買（族群轉強、原版行為）", "觸發股多於池而未買", "池為0的觸發日", "排除隔天出場_日數", "排除隔天出場_持股筆數",
        "買進重疊_近似A上限", "買進重疊_近似B", "年換手近似", "原版年換手", "有觸發日÷有候選日", "候選族群轉強比例", "G3不符日"]


def qq(xs):
    a = np.asarray([v for v in xs if v is not None], float)
    if not len(a):
        return {"中位": None, "p10": None, "p90": None}
    return {"中位": float(np.median(a)), "p10": float(np.percentile(a, 10)), "p90": float(np.percentile(a, 90))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    reg = check_reg()
    log(f"登錄 {reg}")
    os.makedirs(OUT, exist_ok=True)
    summ = {"時間": TIME, "登錄": reg, "乾跑": "⛔ 無任何報酬；價格全 1、毛報酬全 0", "種子數": NSEED, "格": {}, "閘": {}}
    cells, yearly, monthly, rows = [], [], [], []
    for wn in ("main", "early"):
        P, out = run_world(wn, a.procs)
        summ["閘"][f"G1 原版買進＝sim_{wn}_industry（逐種子）"] = f"{sum(z['G1'] for z in out)}/{len(out)}"
        for st in STRATS:
            rs = [z for z in out if z["st"] == st]
            r0 = next(z for z in rs if z["r"] == 0)
            rows += r0["rows"]; monthly += r0["monthly"]
            for sg in SEGN[wn]:
                key = f"{wn}|{st}|{sg}"
                c = {"r0": {k: v for k, v in r0["seg"][sg].items() if k != "有換股月份"}, "有換股月份_r0": r0["seg"][sg]["有換股月份"]}
                if st == "營飆":
                    c["種子"] = {k: qq([z["seg"][sg][k] for z in rs]) for k in NUMK}
                    m24 = [z["seg"][sg]["有換股的不同月數"] for z in rs]
                    c["有換股月數<24的種子比例"] = float(np.mean([m < 24 for m in m24]))
                    c["換股<10%的種子比例"] = float(np.mean([(z["seg"][sg]["換股÷原版買進"] or 0) < 0.10 for z in rs]))
                    c["近似A重疊≥90%的種子比例"] = float(np.mean([(z["seg"][sg]["買進重疊_近似A上限"] or 0) >= 0.90 for z in rs]))
                    ally = Counter()
                    for z in rs:
                        ally.update({k: v for k, v in z["seg"][sg]["每年換股"].items()})
                    for yv, n in sorted(ally.items()):
                        yearly.append({"世界": wn, "策略": st, "段": sg, "年": yv, "換股_r0": r0["seg"][sg]["每年換股"].get(yv, 0),
                                       "換股_種子中位": float(np.median([z["seg"][sg]["每年換股"].get(yv, 0) for z in rs]))})
                else:
                    for yv, n in sorted(r0["seg"][sg]["每年換股"].items()):
                        yearly.append({"世界": wn, "策略": st, "段": sg, "年": yv, "換股_r0": n, "換股_種子中位": n})
                summ["格"][key] = c
                row = {"世界": wn, "策略": st, "段": sg}
                for k in NUMK:
                    row[f"{k}_r0"] = r0["seg"][sg][k]
                    if st == "營飆":
                        row[f"{k}_中位"] = c["種子"][k]["中位"]; row[f"{k}_p10"] = c["種子"][k]["p10"]; row[f"{k}_p90"] = c["種子"][k]["p90"]
                cells.append(row)
                summ["閘"][f"G3 {key}"] = int(sum(z["seg"][sg]["G3不符日"] for z in rs))
    pd.DataFrame(cells).to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(yearly).to_csv(os.path.join(OUT, "yearly.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(monthly).to_csv(os.path.join(OUT, "monthly_r0.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "trigger_days_r0.csv"), index=False, encoding="utf-8-sig")
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    summ["閘"]["G5 策略鎖"] = (lk.stdout + lk.stderr).strip()
    json.dump(summ, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    write_md(summ)
    log("完成")


def _p(x, d=1):
    return "—" if x is None else f"{100 * x:.{d}f}%"


def write_md(summ):
    G = summ["格"]
    L = [f"# 換掉最差那檔・額外策略 seq1 頻率表（乾跑，⛔ 無報酬）— {TIME}", "",
         "額外策略、與正式營量營飆分開；正式規則不動。看過族群轉強 seq2 結果與原版拆兩批才提。", "",
         f"登錄 sha {summ['登錄']['sha16']}（{summ['登錄']['bytes']} B）相符；發號 裁定 seq504 §二。", "",
         "⚠ **第一層近似**：以原版持股路徑為準估觸發與換股次數（換掉哪檔要價格 ⇒ 不決定、不算之後路徑）。正式跑才是真路徑。", "",
         "## 一、三條線（第一層近似）", "",
         "| 格 | 原版買進 | 換股數 | 換股÷原版買進（10% 線） | 買進重疊 近似A上限／B（90% 線） | 有換股的不同月數（24 線） |",
         "|---|---|---|---|---|---|"]
    for key, c in G.items():
        wn, st, sg = key.split("|")
        r0 = c["r0"]
        if st == "營飆":
            s = c["種子"]
            L.append(f"| {st}・{sg} | {s['原版買進']['中位']:.0f} | {s['換股數']['中位']:.0f}〔{s['換股數']['p10']:.0f}～{s['換股數']['p90']:.0f}〕 | "
                     f"{_p(s['換股÷原版買進']['中位'])}〔{_p(s['換股÷原版買進']['p10'])}～{_p(s['換股÷原版買進']['p90'])}〕 | "
                     f"{_p(s['買進重疊_近似A上限']['中位'])}／{_p(s['買進重疊_近似B']['中位'])} | "
                     f"{s['有換股的不同月數']['中位']:.0f}〔{s['有換股的不同月數']['p10']:.0f}～{s['有換股的不同月數']['p90']:.0f}〕／{r0['段月數']}（＜24 的種子 {_p(c['有換股月數<24的種子比例'], 0)}） |")
        else:
            L.append(f"| {st}・{sg} | {r0['原版買進']} | {r0['換股數']} | {_p(r0['換股÷原版買進'])} | {_p(r0['買進重疊_近似A上限'])}／{_p(r0['買進重疊_近似B'])} | "
                     f"{r0['有換股的不同月數']}／{r0['段月數']} |")
    L += ["", "營飆：200 顆種子中位〔p10～p90〕；營量：r0（成交金額相對放大排序，無抽籤）。早年只描述。", "",
          "## 二、觸發細項（r0；營飆另附種子中位）", "",
          "| 格 | 觸發日 | 觸發股 | 滿槽觸發／有空槽直接買 | 觸發但買完仍有空槽 | 同日觸發股數 1/2/3/4+ | 池大小 中位〔p10～p90〕 | 觸發股多於池未買 | 排除隔天出場（日／筆） | 有觸發日÷有候選日 | 候選族群轉強比例 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, c in G.items():
        wn, st, sg = key.split("|"); r0 = c["r0"]; pd_ = r0["同日觸發股數分布"]; pl = r0["池大小"] or {}
        L.append(f"| {st}・{sg} r0 | {r0['觸發日數']} | {r0['觸發股數']} | {r0['滿槽觸發']}／{r0['有空槽直接買（族群轉強、原版行為）']} | {r0['觸發但買完仍有空槽']} | "
                 f"{pd_.get('1', 0)}/{pd_.get('2', 0)}/{pd_.get('3', 0)}/{pd_.get('4+', 0)} | "
                 f"{pl.get('中位', '—')}〔{pl.get('p10', '—')}～{pl.get('p90', '—')}〕 | {r0['觸發股多於池而未買']} | {r0['排除隔天出場_日數']}／{r0['排除隔天出場_持股筆數']} | "
                 f"{_p(r0['有觸發日÷有候選日'])} | {_p(r0['候選族群轉強比例'])} |")
        if st == "營飆":
            s = c["種子"]
            L.append(f"| {st}・{sg} 種子中位 | {s['觸發日數']['中位']:.0f} | {s['觸發股數']['中位']:.0f} | {s['滿槽觸發']['中位']:.0f}／{s['有空槽直接買（族群轉強、原版行為）']['中位']:.0f} | "
                     f"{s['觸發但買完仍有空槽']['中位']:.0f} | — | — | {s['觸發股多於池而未買']['中位']:.0f} | {s['排除隔天出場_日數']['中位']:.0f}／{s['排除隔天出場_持股筆數']['中位']:.0f} | "
                     f"{_p(s['有觸發日÷有候選日']['中位'])} | {_p(s['候選族群轉強比例']['中位'])} |")
    L += ["", "## 三、近似的範圍（池全體，⛔ 不是被換那檔；被換那檔要價格 ⇒ 正式跑）", "",
          "| 格（r0） | 池全體已持有天數 中位〔p10～p90〕 | 池全體距原版到期 中位〔p10～p90〕 | 每次換股該槽後移（日，觸發日中位） | 年換手 原版→近似 |", "|---|---|---|---|---|"]
    for key, c in G.items():
        wn, st, sg = key.split("|"); r0 = c["r0"]
        ag, rm, sh = r0["池全體_已持有天數"], r0["池全體_距原版到期"], r0["槽後移日數範圍"]
        f3 = (lambda z: "—" if not z else f"{z['中位']:.0f}〔{z['p10']:.0f}～{z['p90']:.0f}〕")
        shs = "—" if not sh else "{:.0f}～{:.0f}".format(sh["最小(H−max)"], sh["最大(H−min)"])
        L.append(f"| {st}・{sg} | {f3(ag)} | {f3(rm)} | {shs} | {r0['原版年換手']:.1f}→{r0['年換手近似']:.1f} |")
    L += ["", "讀法：換進那檔佔槽到 t＋H，被換那檔原本在 b 空出 ⇒ 該槽之後每一次換手日都後移 (t＋H)−b 日（≥1），之後該槽的買進日與原版不同。",
          "⇒ 買進重疊近似 A（原版買進全保留、換進另加）是上限；近似 B（每次換股只擠掉一筆後續原版買進）不含連鎖後移；真值可能更低，乾跑定不出下限。",
          "⇒ 換股次數、有換股月數在真路徑上也會變（持股換了、空槽日變了），但觸發只看「名單上族群轉強且未持有、買完已滿槽」，滿槽日的比例在真路徑上與原版同量級（換股是一換一，不改持股數）。", "",
          "## 四、seq377 等價檢查", ""]
    for key, c in G.items():
        wn, st, sg = key.split("|"); r0 = c["r0"]
        eq = "恆等於原版（換股 0）" if r0["換股數"] == 0 else ("觸發幾乎恆空（有觸發日 ＜ 5%）" if (r0["有觸發日÷有候選日"] or 0) < 0.05 else "不等價")
        fl = r0["候選族群轉強比例"] or 0
        fl_s = "恆真" if fl >= 0.95 else ("恆假" if fl <= 0.05 else "非恆真恆假")
        L.append(f"- {st}・{sg}（r0）：{eq}；族群旗標在候選中 {_p(fl)} ⇒ {fl_s}")
    L += ["", "## 五、閘", ""] + [f"- {k}：{v}" for k, v in summ["閘"].items()]
    L += ["", "## 六、★ 執行者定（登錄沒寫清楚）", "",
          "- ★1 頻率表是第一層近似（原版持股路徑）；換掉哪檔、之後路徑 ⇒ 正式跑。",
          "- ★2 觸發只看引擎看得到的候選列（營飆含 0050 閘、xpos 有值）；「不在持股中」＝ 第 t 日排程出場與停止交易強制出場結清後的引擎持有口徑。",
          "- ★3 引擎先補滿空槽 ⇒ 觸發股全部屬「沒空位 ⇒ 換」；「有空位 ⇒ 買」＝ 原版本來就買的族群轉強候選（另報）。",
          "- ★4 被換候選池 ＝ 觸發日收盤持有、第 t 日不依原版出場者；第 t 日開盤原版剛買的不在池內；「隔天本來就要出場」含停止交易強制出場。",
          "- ★5 換股數 ＝ min(觸發股數, 池)；段以第 t 日（換股／買進日）歸段；有換股月以第 t 日所在月計。",
          "- ★6 族群旗標沿用 researchGroupRevUp_freq --groups industry 的 grp（主段產業檔、2016 無分群 ⇒ 0；早年自建 v2 只描述）。",
          "- ★7 買進重疊兩個近似（A 上限、B）；登錄的「換掉的買進占原版買進」頻率表讀成「換股數 ÷ 原版買進」（第一層近似下原版買進全保留、⇒ 原版被換掉 ＝ 0 無資訊）。", "",
          "早年：只描述；含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市", "",
          "描述，不是買賣建議"]
    open(os.path.join(OUT, "結果.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

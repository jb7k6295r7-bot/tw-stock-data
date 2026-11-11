# -*- coding: utf-8 -*-
"""額外策略「營量 v1、營飆 v1：名單出現族群營收轉強就買、滿了就換掉持股裡最差那檔」【正式跑】——回測線計算子代理，2026-11-11。
登錄：台股策略線 seq1（sha 369b04d9e487d4ce，6189 B）〈營量營飆族群轉強出現就換掉持股最差那檔_額外策略_組合層登錄〉
發號：裁定線 seq504 §二（N_組合 ＋2；最多「合格（暫定）」）；頻率表 commit 0276ed83f8；裁定線 seq505 §二 核可正式跑（閘 --formal --ruling seq505）
⛔ 不改策略鎖內任何檔、⛔ 不改既有 research*.py（只 import）；開跑前、跑完各驗一次 strategy_lock。
⛔ 原版路徑一律呼叫既有 researchGroupRevUp_freq.cell_sig／run_engine（真價格、full）；族群旗標 ＝ ~/grpwork/groups_<世界>_industry.pkl 的 grp
   （researchGroupRevUp.attach_g 接真實 g、cand_gate 對 freq_industry 逐年筆數；世界 ＝ researchAddOn.worlds 快取）。
⭐ 換股要真路徑：既有引擎沒有「賣一檔換一檔」⇒ 本檔 sim_swap 是 research11.simulate_mtm 在本件用到的那條路徑
   （營量 pick＝relvol、營飆抽籤、stop_force；真實成本版另含 tradable／delist）的逐日迴圈，只在其後加「換股」一步。
   閘 G：swap=False ⇒ 與 run_engine（真實成本版：與 simulate_mtm 同參數）逐筆買賣、權益與 hold_val 逐位元相同（營量 r0、營飆每一顆種子、兩個世界）
   ⇒ 證明它不是另一套口徑；換股為 0 的日子走的是同一條算式。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSwapWorst --formal --ruling seq505 [--procs 3]
    （⛔ 缺 --formal、缺 --ruling、裁定號不是 seq505 ⇒ 拒跑；登錄 sha／大小不符、信箱找不到 seq504／seq505 裁定 ⇒ 拒跑）
    試跑：SW_NSEED=5 …（輸出改到 /tmp/sw_try5，⛔ 不是交件）
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchSwapWorst
輸出 backtest/resultsSwapWorst/formal/：result.json、結果.md、cells.csv、freq.csv、swaps_r0.csv、seeds.csv.gz、real.csv、run.log

═══ 讀法（⛔ 在算任何本件報酬之前寫死於 2026-11-11 13:55（台北）；頻率表 W0～W6 照用、裁定 seq505 核；★ ＝ 登錄沒寫清、執行者定）═══
 寫死前看過：登錄 seq1 全文、裁定 seq504／505、頻率表 resultsSwapWorst/freq（⛔ 無報酬）、researchGroupRevUp 正式跑程式與結果（族群轉強 seq2）；
   ⚠ 回測線看過營量 v1、營飆 v1 全部正式結果、族群轉強 seq2 正式結果與原版拆兩批 ⇒ 判語最多「合格（暫定）」；⛔ 沒看過本件任何報酬。
 S0 閘：--formal --ruling seq505；登錄 sha（researchSwapWorst_freq.check_reg：sha16＋6189 B＋信箱 seq504）；信箱 glob *seq505*；策略鎖前後；
    researchGroupRevUp.dry_repro（freq 乾跑重現）、attach_g、cand_gate；原版 eq_sha ＝ resultsYL_integrate/seeds.csv.gz（＝ 正式營量 v1／營飆 v1）；
    閘 G（上面）；閘 L：正確版「池內那檔在換股時已不在持股」次數 ＝ 0
 S1 每日順序（W2～W4 照頻率表；第 t 日 ＝ 觸發日 t−1 的隔天）：
    ① 停止交易強制出場標記（照引擎）② 被換候選池快照 ③ 排程出場（照引擎）④ 原版正常買進（照引擎；營量 relvol、營飆同顆種子抽籤）⑤ 換股
    ★ 池 ＝ 觸發日 t−1 收盤持有、排程出場日 ＞ t（含停止交易強制出場在 t 者一律排除）、買進日 ＜ t 者（第 t 日剛買的不在池）
    ★ 最差 ＝ 收盤[t−1] ÷ 進場價 − 1（進場價 ＝ 引擎進場價：買進日還原開盤，無效改收盤；真實成本版 ＝ 均價）；同分 ⇒ 買進日較早者；再同 ⇒ 持股列序
    ★ 觸發 ＝ 第 t 日候選（引擎看得到的列：cell_sig 的 xpos 有值、營飆含 0050 閘）中 grp＝1、④ 之後仍未持有者（同檔多列只算一次）
    ★ ④ 之後仍有空槽（現金不足、真實成本版漲停買不到）⇒ 照原版不換（報筆數；頻率表 W2 預期 0）
    ★ 觸發股排序：營量 ＝ relvol 遞減（NaN 最後、同分照候選列序 ＝ 引擎 pick 同式）；
      營飆 ＝ 抽籤：另一條同種子衍生的抽籤流 default_rng([1000＋r, 505])（⛔ 不動原版抽籤流 ⇒ 換股為 0 時與原版逐位元相同）
    ★ 依序：第 1 檔觸發換池中最差、第 2 檔換次差…；池用完 ⇒ 剩下的觸發不買（報筆數）
    ★ 換出 ＝ 第 t 日開盤賣（還原開盤；無效改當日收盤）；毛報酬 ＝ 賣價 ÷ 進場價 − 1；入帳 ＝ 金額 ×（1 ＋ 毛 − 成本）（引擎出場同式）
    ★ 換進 ＝ 第 t 日開盤買，金額 ＝ min(權益[t−1] ÷ N, 現金)（＝ 引擎新部位同式；現金含剛賣得的）；出場 ＝ 該列原排程（營量第 60 日、營飆第 120 日收盤）、毛報酬 ＝ 該列 g
    ★ 成本 ＝ 引擎慣例：每一塊買進的錢在賣出時付一次來回 0.585%（＝ 買、賣各一半，只是記帳時點在賣出）；資料尾仍持有不扣
    ★ 不設最短持有：剛買（t−1 買進）的也在池內；換進的照同條可再被換
    真實成本版 ★ ＝ researchYLSell5.slip_setup ＋ researchSlip.arm_inputs「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」同輸入（主世界）：
      原版 ＝ researchYLSell5.slip_run（引擎）；本版 ＝ sim_swap 帶 tradable／delist／stop_force、成本 ＝ arm 成本；
      換出賣價 ＝ 均價（C4）、衝擊 ＝ C2 同式（arm_inputs 對出場日 t 的式；閘：本檔式對每列排程出場重算 ＝ arm_inputs 的 g 逐位元）；
      換出那天開盤跌停或停牌 ⇒ 不在池；換進那檔開盤漲停或停牌 ⇒ 該觸發不買（換出也不做），報筆數
 S2 段（以第 t 日歸段）＝ 世界 segp：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、早年 2005-02-01～2014-12-31（只描述）
    年化、回落 ＝ rerun17.win_metrics；營飆 ＝ 200 顆中位（比值 ＝ 年化中位 ÷ |回落中位|），另報 p10～p90 與 r0；營量 ＝ r0 一條
 S3 判定（登錄 §三、裁定 seq505 §二；只主世界兩格）：大盤 ＝ 臺灣加權報酬指數（benchmark_rejudge.read_series，同 researchGroupRevUp）；
    標籤 ＝ researchAscTri.label；順序：
      ① 退化（等同原版）★：探索或確認任一段 換股數 ÷ 原版買進 ＜ 10% 或 買進重疊（÷ 本版買進）≥ 90% ⇒「等同原版」（⛔ 不判、不進排名）
      ② 〈四十九〉：任一段「有換股的不同月數」＜ 24 ⇒「還沒測（依構造）」（營飆依種子中位、r0 並報）
      ③ 兩段都「合格」⇒「合格（暫定）」；兩段年化都贏大盤（合格或另列）⇒「另列」；其餘 ⇒「不合格」
    真實成本版：同 ①② 的構造量（正式真路徑）＋ 真實成本的標籤重判，報「改判／不改判」
 S4 頻率表項目在真路徑上重報（每段）：每年換股、換股 ÷ 原版買進、有換股月數、被換那檔持有天數（t − 買進日）中位／p10／p90、
    被換時距原版到期（排程出場日 − t）、同一檔被換出後又買回（★ 兩種：原到期日前買回；之後任何時候買回）、平均持股、年換手
    （筆數 ＝ 買進筆 ÷ N ÷ 年；金額 ＝ 買進金額 ÷ 平均權益 ÷ 年，年 ＝ 交易日 ÷ 245）、對原版：買進重疊（÷ 本版、÷ 原版）、
    金額權重逐日持股重疊（researchGroupRevUp.amt_overlap）、日報酬相關
 S5 換錯的代價 ★：每一次換股，被換那檔「若照原版抱到期」＝ 收盤[原到期日] ÷ 第 t 日換出賣價 − 1；換進那檔同期 ＝ 收盤[同一個原到期日] ÷ 換進價 − 1
    （還原價、毛、不扣成本；收盤已 ffill ⇒ 期間停止交易者 ＝ 最後收盤）；每筆差 ＝ 換進 − 換出，報平均、中位、正的比例（營飆 ＝ 每顆的值取中位，另報 r0）
    另一欄（描述）：換進那檔抱到它自己的到期
 S6 描述（⛔ 不判）：「買進滿 20 個交易日才可被換」★ ＝ 池另加 t − 買進日 ≥ 20
 S7 與原版並列只描述；方向為負寫「測不出／分不出」類措辭；必附：「額外策略、與正式營量營飆分開；正式規則不動」
    「看過族群轉強 seq2 結果與原版拆兩批才提」；早年附 reduce_v2 約 0.3% 註；結尾「描述，不是買賣建議」
"""
from __future__ import annotations

import argparse
import glob
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
from backtest import researchGroupRevUp_freq as M           # noqa: E402  cell_sig、run_engine、intervals、held_count（⛔ 不另寫）
from backtest import researchGroupRevUp as GR               # noqa: E402  attach_g、cand_gate、dry_repro、pos_book、amt_overlap、mci、lock_check
from backtest import researchSwapWorst_freq as SWF          # noqa: E402  check_reg（登錄 sha＋seq504）
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as AO                    # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import benchmark_rejudge as BR                # noqa: E402
from backtest import researchPTH_freq as PFQ                # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

TIME = "2026-11-11 13:55（台北）"
RULING = "seq505"
OUT = "backtest/resultsSwapWorst/formal"
NSEED = int(os.environ.get("SW_NSEED", "200"))
if NSEED != 200:                                            # 試跑（不是交件）
    OUT = f"/tmp/sw_try{NSEED}"
WNM = {"main": "主", "early": "早年"}
JSEG = ("探索", "確認")
VERS = ("原版", "換股版", "滿20日版")
MIN_HOLD = 20
NEFF_MIN = 24
DEG_SW, DEG_OV = 0.10, 0.90
COST = 0.00585
SW_SALT = 505
SENT = ["額外策略、與正式營量營飆分開；正式規則不動", "看過族群轉強 seq2 結果與原版拆兩批才提"]
_F: dict = {}


def log(x):
    GR.log(x)


# ═════════════ S0 閘 ═════════════
def parse_gate(argv):
    ap = argparse.ArgumentParser(description="換掉最差那檔 正式跑（閘 --formal --ruling seq505）")
    ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None)
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args(argv)
    why = None if a.formal else "缺 --formal"
    why = why or (None if a.ruling else "缺 --ruling")
    why = why or (None if a.ruling == RULING else f"裁定號 {a.ruling!r} ≠ {RULING}")
    if why:
        raise SystemExit(f"⛔ 拒跑：{why}（要 --formal --ruling {RULING}）")
    return a


def mailbox_gate():
    reg = SWF.check_reg()
    fs = sorted(glob.glob(os.path.join(SWF.MAILBOX, "**", f"*{RULING}*"), recursive=True))
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RULING}")
    reg["裁定505"] = os.path.basename(fs[0])
    return reg


# ═════════════ 換股真路徑（S1）═════════════
def day_rows(sig, rule):
    """引擎取列同條件：sid、entry_pos、xpos、g 都有值且 xpos ≥ 0（simulate_mtm 開頭）；另帶 relvol、grp。回 列陣列 ＋ {t: [列號…]}（保候選列序）。"""
    xc, gc = f"xpos_{rule}", f"g_{rule}"
    d = sig.dropna(subset=["sid", "entry_pos", xc, gc])
    d = d[d[xc] >= 0]
    by = defaultdict(list)
    for i, t in enumerate(d["entry_pos"].to_numpy(int)):
        by[int(t)].append(i)
    rv = d["relvol"].to_numpy(float) if "relvol" in d.columns else np.full(len(d), np.nan)
    gp = d["grp"].to_numpy(bool) if "grp" in d.columns else np.zeros(len(d), bool)
    return {"sid": [str(s) for s in d["sid"]], "ex": d[xc].to_numpy(float).astype(int), "g": d[gc].to_numpy(float),
            "rv": rv, "grp": gp, "ent": d["entry_pos"].to_numpy(int)}, by


def open_px(opens, closes, sid, t):
    o = float(opens[sid][t])
    return o if (np.isfinite(o) and o > 0) else float(closes[sid][t])


def can_trade(tradable, opens, sid, t, side):
    tb = tradable[sid]; o = float(opens[sid][t])
    lim = tb["up_o"][t] if side == "buy" else tb["dn_o"][t]
    return bool(tb["trd"][t]) and not bool(lim) and bool(np.isfinite(o)) and o > 0


def rank_desc(keys):
    k = np.asarray(keys, float)
    return np.argsort(-np.where(np.isnan(k), -np.inf, k), kind="stable")


def swap_pool(open_pos, ent, t, min_hold, closes, opens, tradable, cnt):
    """被換候選池（第 t 日開盤前快照）：[(買進以來報酬, 買進日, 列序, sid)]，最差在前。"""
    pool = []
    for k, (ex, sid, amt, gross, ep) in enumerate(open_pos):
        a_ = ent[sid]
        if not (ex > t and a_ < t and t - a_ >= min_hold):   # _MUT_EXCL
            continue
        c = float(closes[sid][t - 1])
        if not np.isfinite(c):
            cnt["池_收盤缺"] += 1; continue
        if tradable is not None and not can_trade(tradable, opens, sid, t, "sell"):
            cnt["池_不可賣"] += 1; continue
        pool.append((c / ep - 1.0, a_, k, sid))
    pool.sort(key=lambda z: (z[0], z[1], z[2]))   # _MUT_WORST
    return pool


def sim_swap(sig, st, r, closes, opens, NP, SF, swap=True, min_hold=0, N=None, cost=None, tradable=None, delist=None, sale_gross=None):
    """research11.simulate_mtm 本件路徑（營量 pick＝relvol、營飆抽籤；stop_force；可選 tradable／delist）＋ 換股。swap=False ⇒ 與引擎逐位元相同（閘 G）。"""
    sp = M.STRATS[st]
    N = sp["N"] if N is None else N
    cost = R.COST if cost is None else cost
    Dr, by = day_rows(sig, f"H{sp['H']}")
    sid_, ex_, g_, rv_, grp_ = Dr["sid"], Dr["ex"], Dr["g"], Dr["rv"], Dr["grp"]
    rng = np.random.default_rng(sp["seed0"] + r)
    rng_sw = np.random.default_rng([sp["seed0"] + r, SW_SALT])
    first, last = int(min(by)), int(ex_.max())
    equity = np.ones(NP); hold_val = np.zeros(NP); cash = 1.0
    open_pos = []; held = set(); ent = {}
    audit, swaps, tlog = [], [], []
    cnt = Counter()
    t_end = min(NP, last + 2); t_done = t_end - 1
    for t in range(first, NP if tradable is not None else t_end):
        if tradable is not None and t >= t_end and not open_pos:
            break
        sf_now = ()
        if SF is not None and open_pos:
            sf_now = set()
            for k, (ex, sid, amt, gross, ep) in enumerate(open_pos):
                L = SF.get(sid)
                if L is not None and t == L + 1 and ex > t:
                    open_pos[k] = (t, sid, amt, float(closes[sid][L]) / ep - 1.0, ep); sf_now.add(sid)
        pool = swap_pool(open_pos, ent, t, min_hold, closes, opens, tradable, cnt) if (swap and t > first) else []
        still = []
        for ex, sid, amt, gross, ep in open_pos:
            if ex <= t and tradable is not None and sid not in sf_now and (t > ex or not tradable[sid]["trd"][t] or tradable[sid]["dn_c"][t]):
                tb = tradable[sid]; o_t = float(opens[sid][t]); dl = None
                if delist is not None and (not tb["trd"][t]) and sid in delist and t > delist[sid]["last"]:
                    dl = delist[sid]["status"]
                if not (dl is not None and dl.startswith("delisted")):
                    if t == ex or not tb["trd"][t] or tb["dn_o"][t] or not np.isfinite(o_t) or o_t <= 0:
                        still.append((ex, sid, amt, gross, ep)); continue
                    gross = o_t / ep - 1.0
            if ex <= t:
                audit.append({"t": t, "sid": sid, "side": "sell", "amt": float(amt * (1 + gross)), "px": float(ep * (1 + gross))})
                cash += amt * (1 + gross - cost)
                held.discard(sid); ent.pop(sid, None)
            else:
                still.append((ex, sid, amt, gross, ep))
        open_pos = still
        idx = by.get(t)
        if idx is not None and len(open_pos) < N:
            cand = [i for i in idx if sid_[i] not in held]
            if cand:
                order = rng.permutation(len(cand)) if st == "營飆" else rank_desc(rv_[cand])
                slot = equity[t - 1] / N
                for j in order[:N - len(open_pos)]:
                    i = cand[j]; sid = sid_[i]
                    if tradable is not None and not can_trade(tradable, opens, sid, t, "buy"):
                        continue
                    amt = min(slot, cash)
                    if amt <= 1e-9:
                        break
                    cash -= amt
                    ep = open_px(opens, closes, sid, t)
                    open_pos.append((int(ex_[i]), sid, amt, float(g_[i]), ep)); held.add(sid); ent[sid] = t
                    audit.append({"t": t, "sid": sid, "side": "buy", "amt": float(amt), "px": ep})
        if swap and idx is not None:
            trig, seen = [], set()
            for i in idx:
                if grp_[i] and sid_[i] not in held and sid_[i] not in seen:
                    trig.append(i); seen.add(sid_[i])
            if trig:
                rec = {"t": t, "觸發": len(trig), "池": len(pool), "換": 0, "有空槽未換": 0, "池不足未換": 0, "換進不可成交": 0, "池內已出場": 0}
                if len(open_pos) < N:
                    rec["有空槽未換"] = len(trig)
                else:
                    if st == "營飆":
                        trig = [trig[j] for j in rng_sw.permutation(len(trig))]
                    else:
                        trig = [trig[j] for j in rank_desc(rv_[trig])]
                    pi = 0
                    for i in trig:
                        if pi >= len(pool):
                            rec["池不足未換"] += 1; continue
                        s_in = sid_[i]
                        if tradable is not None and not can_trade(tradable, opens, s_in, t, "buy"):
                            rec["換進不可成交"] += 1; continue
                        ret0, a_o, _, s_out = pool[pi]; pi += 1
                        k = next((k for k, p in enumerate(open_pos) if p[1] == s_out), None)
                        if k is None:
                            rec["池內已出場"] += 1; continue
                        ex_o, _, amt_o, _, ep_o = open_pos.pop(k)
                        px = open_px(opens, closes, s_out, t)
                        gr = px / ep_o - 1.0 if sale_gross is None else sale_gross(s_out, a_o, t, ep_o, px)
                        audit.append({"t": t, "sid": s_out, "side": "sell", "amt": float(amt_o * (1 + gr)), "px": float(ep_o * (1 + gr)), "kind": "swap"})
                        cash += amt_o * (1 + gr - cost)
                        held.discard(s_out); ent.pop(s_out, None)
                        amt = min(equity[t - 1] / N, cash)
                        cash -= amt
                        ep = open_px(opens, closes, s_in, t)
                        open_pos.append((int(ex_[i]), s_in, amt, float(g_[i]), ep)); held.add(s_in); ent[s_in] = t
                        audit.append({"t": t, "sid": s_in, "side": "buy", "amt": float(amt), "px": ep, "kind": "swap"})
                        swaps.append({"t": t, "out": s_out, "a_out": int(a_o), "b_out": int(ex_o), "ret_out": float(ret0), "gross_sale": float(gr),
                                      "px_out": float(px), "ep_out": float(ep_o), "in": s_in, "b_in": int(ex_[i]), "ep_in": float(ep)})
                        rec["換"] += 1
                tlog.append(rec)
        hv = sum(amt * float(closes[sid][t]) / ep for _, sid, amt, _, ep in open_pos)
        equity[t] = cash + hv
        hold_val[t] = hv
        t_done = t
    end = min(NP, last + 2)
    if tradable is not None:
        end = max(end, t_done + 1)
    equity[:first] = 1.0; equity[end:] = equity[end - 1]
    buys = [(int(a["t"]), str(a["sid"])) for a in audit if a["side"] == "buy"]
    sells = [(int(a["t"]), str(a["sid"])) for a in audit if a["side"] != "buy"]
    return {"equity": equity, "hold_val": hold_val, "first": first, "end": end, "audit": audit, "buys": buys, "sells": sells,
            "swaps": swaps, "tlog": tlog, "cnt": dict(cnt)}


def slip_sale_gross(X, Q):
    """真實成本版換出毛報酬：researchSlip.arm_inputs 的 C4（均價比）＋ C2（進場、出場衝擊）同式，出場日換成 t。"""
    def imp(sid, p):
        a = X[sid]["adv20"][p]
        return X[sid]["sig20"][p] * np.sqrt(Q / a) if (np.isfinite(a) and a > 0) else 0.0

    def f(sid, e, t, ep, px):
        av = X[sid]["avg"]
        g = av[t] / av[e] - 1.0 if (np.isfinite(av[e]) and av[e] > 0 and np.isfinite(av[t])) else px / ep - 1.0
        ie = np.nan_to_num(imp(sid, e)); ix = np.nan_to_num(imp(sid, t))
        return float((1 + g) * (1 - np.minimum(ix, 0.99)) / (1 + ie) - 1.0)
    return f


def same_path(b0, s0, eq0, hv0, f0, e0, au0, z):
    au_e = [(int(a["t"]), str(a["sid"]), a["side"], float(a["amt"]), float(a["px"])) for a in au0]
    au_m = [(int(a["t"]), str(a["sid"]), a["side"], float(a["amt"]), float(a["px"])) for a in z["audit"]]
    return {"買賣逐筆": bool(b0 == z["buys"] and s0 == z["sells"] and au_e == au_m),
            "權益逐位元": bool(np.array_equal(np.asarray(eq0, float), z["equity"])),
            "hold_val逐位元": hv0 is None or bool(np.array_equal(np.asarray(hv0, float), z["hold_val"])),
            "first_end": bool(int(f0) == z["first"] and int(e0) == z["end"])}


# ═════════════ 逐顆統計 ═════════════
def vstats(V, x, y, cal, pts, N):
    eq = V["eq"]; hv = V["hv"]
    c, m, _ = RR.win_metrics(eq, V["first"], V["end"], x, y)
    yrs = (y - x + 1) / 245.0
    bs = [a for a in V["au"] if a["side"] == "buy" and x <= int(a["t"]) <= y]
    hc = M.held_count(M.intervals(V["buys"], V["sells"], len(eq)), len(eq))
    return {"年化": float(c), "回落": float(m), "月報酬": eq[pts[1:]] / eq[pts[:-1]] - 1.0, "買進": len(bs),
            "筆換手每年": len(bs) / N / yrs, "金額換手每年": float(sum(float(a["amt"]) for a in bs) / np.mean(eq[x:y + 1]) / yrs),
            "平均持股": float(np.mean(hc[x:y + 1])), "現金比例": float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))}


def q3(v):
    v = np.asarray([z for z in v if z is not None and np.isfinite(z)], float)
    if not len(v):
        return {"中位": None, "p10": None, "p90": None, "n": 0}
    return {"中位": float(np.median(v)), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90)), "n": int(len(v))}


def freq_true(z, b0, x, y, cal, closes):
    """S4、S5：真路徑頻率量與換錯的代價（段 [x, y]，以第 t 日歸段）。"""
    sw = [e for e in z["swaps"] if x <= e["t"] <= y]
    tl = [e for e in z["tlog"] if x <= e["t"] <= y]
    nb0 = sum(1 for t, _ in b0 if x <= t <= y)
    rebuy = defaultdict(list)
    for t, s in z["buys"]:
        rebuy[s].append(t)
    rb_b = sum(1 for e in sw if any(e["t"] < t2 < e["b_out"] for t2 in rebuy[e["out"]]))
    rb_any = sum(1 for e in sw if any(t2 > e["t"] for t2 in rebuy[e["out"]]))
    hold = [e["t"] - e["a_out"] for e in sw]; rem = [e["b_out"] - e["t"] for e in sw]
    r_out = np.array([float(closes[e["out"]][e["b_out"]]) / e["px_out"] - 1.0 for e in sw])
    r_in = np.array([float(closes[e["in"]][e["b_out"]]) / e["ep_in"] - 1.0 for e in sw])
    r_in_own = np.array([float(closes[e["in"]][e["b_in"]]) / e["ep_in"] - 1.0 for e in sw])
    d = r_in - r_out
    return {"換股數": len(sw), "原版買進": nb0, "換股÷原版買進": (len(sw) / nb0) if nb0 else None,
            "有換股的不同月數": len({cal[e["t"]].strftime("%Y-%m") for e in sw}),
            "每年換股": {str(k): int(v) for k, v in sorted(Counter(cal[e["t"]].year for e in sw).items())},
            "觸發日": len(tl), "觸發股": int(sum(e["觸發"] for e in tl)), "有空槽未換": int(sum(e["有空槽未換"] for e in tl)),
            "池不足未換": int(sum(e["池不足未換"] for e in tl)), "換進不可成交": int(sum(e["換進不可成交"] for e in tl)),
            "池內已出場": int(sum(e["池內已出場"] for e in tl)),
            "被換持有天數": q3(hold), "距原版到期": q3(rem), "被換持有天數_平均": float(np.mean(hold)) if hold else None,
            "換出後原到期前買回": rb_b, "換出後任何時候買回": rb_any,
            "代價_筆": len(sw), "代價_差平均": float(d.mean()) if len(d) else None, "代價_差中位": float(np.median(d)) if len(d) else None,
            "代價_差為正比例": float((d > 0).mean()) if len(d) else None,
            "代價_換出若抱到期平均": float(r_out.mean()) if len(d) else None, "代價_換進同期平均": float(r_in.mean()) if len(d) else None,
            "代價_換進抱到自己到期平均": float(r_in_own.mean()) if len(d) else None,
            "代價_自己到期差平均": float((r_in_own - r_out).mean()) if len(d) else None}


def pair_stats(A, B, x, y, NP):
    ka = {k for k in A["bkey"] if x <= k[0] <= y}; kb = {k for k in B["bkey"] if x <= k[0] <= y}
    ov = GR.amt_overlap(A["V"], A["eq"], B["V"], B["eq"], NP)
    ra = A["eq"][x + 1:y + 1] / A["eq"][x:y] - 1.0; rb = B["eq"][x + 1:y + 1] / B["eq"][x:y] - 1.0
    cc = float(np.corrcoef(ra, rb)[0, 1]) if (np.std(ra) > 0 and np.std(rb) > 0) else float("nan")
    return {"買進重疊÷本版": len(ka & kb) / len(ka) if ka else None, "買進重疊÷原版": len(ka & kb) / len(kb) if kb else None,
            "金額持股重疊_平均": float(np.mean(ov[x:y + 1])), "日報酬相關": cc}


def job(args):
    wn, st, r = args
    F = _F[wn]; S = F["S"]; NP = F["NP"]; cal = F["cal"]; segs = F["segp"]; cl, op, SF = F["closes"], F["opens"], F["SF"]
    N = M.STRATS[st]["N"]
    sig = M.cell_sig(S, st, "原版", dry=False)
    b0, s0, o0, au0 = M.run_engine(sig, st, "原版", r, cl, NP, SF, opens=op, full=True)
    off = sim_swap(sig, st, r, cl, op, NP, SF, swap=False)
    gate = same_path(b0, s0, o0["equity"], o0["hold_val"], o0["first"], o0["end"], au0, off)
    on = sim_swap(sig, st, r, cl, op, NP, SF, swap=True)
    on20 = sim_swap(sig, st, r, cl, op, NP, SF, swap=True, min_hold=MIN_HOLD)
    V = {"原版": {"eq": np.asarray(o0["equity"], float), "hv": np.asarray(o0["hold_val"], float), "first": int(o0["first"]), "end": int(o0["end"]),
                 "buys": b0, "sells": s0, "au": au0}}
    for v, z in (("換股版", on), ("滿20日版", on20)):
        V[v] = {"eq": z["equity"], "hv": z["hold_val"], "first": z["first"], "end": z["end"], "buys": z["buys"], "sells": z["sells"], "au": z["audit"]}
    for v in VERS:
        V[v]["bkey"] = set(V[v]["buys"]); V[v]["V"] = GR.pos_values(GR.pos_book(V[v]["au"]), cl, NP)
    out = {"wn": wn, "st": st, "r": r, "G": gate, "eq_sha": IG.sha(V["原版"]["eq"]),
           "L": int(sum(e["池內已出場"] for e in on["tlog"]) + sum(e["池內已出場"] for e in on20["tlog"])), "ver": {}, "freq": {}, "freq20": {}, "pair": {}, "pair20": {}}
    for v in VERS:
        out["ver"][v] = {sg: vstats(V[v], x, y, cal, F["pts"][sg], N) for sg, (x, y) in segs.items()}
    for sg, (x, y) in segs.items():
        out["freq"][sg] = freq_true(on, b0, x, y, cal, cl)
        out["freq20"][sg] = freq_true(on20, b0, x, y, cal, cl)
        out["pair"][sg] = pair_stats(V["換股版"], V["原版"], x, y, NP)
        out["pair20"][sg] = pair_stats(V["滿20日版"], V["原版"], x, y, NP)
    if r == 0:
        rows = []
        for e in on["swaps"]:
            sg = next((k for k in segs if k != "主窗" and segs[k][0] <= e["t"] <= segs[k][1]), "段外")
            ro = float(cl[e["out"]][e["b_out"]]) / e["px_out"] - 1.0; ri = float(cl[e["in"]][e["b_out"]]) / e["ep_in"] - 1.0
            rows.append({"世界": wn, "策略": st, "種子": r, "段": sg, "換股日": cal[e["t"]].strftime("%Y-%m-%d"), "換出": e["out"],
                         "換出買進日": cal[e["a_out"]].strftime("%Y-%m-%d"), "換出原到期日": cal[min(e["b_out"], len(cal) - 1)].strftime("%Y-%m-%d"),
                         "持有天數": e["t"] - e["a_out"], "距原版到期": e["b_out"] - e["t"], "換出時報酬(觸發日收盤)": e["ret_out"],
                         "換出賣價毛報酬": e["gross_sale"], "換進": e["in"], "換進到期日": cal[min(e["b_in"], len(cal) - 1)].strftime("%Y-%m-%d"),
                         "換出若抱到期(同期)": ro, "換進同期": ri, "差(換進−換出)": ri - ro})
        out["rows"] = rows
    return out


def job_real(args):
    st, r = args
    Z = _F["real"][st]; W = _F["realW"]
    sg_, op, cost, kw, fsg = Z["sig"], Z["op"], Z["cost"], Z["kw"], Z["sale"]
    NP = W["NP"]; cl = W["closes"]; sp = M.STRATS[st]
    c0 = R.COST
    R.COST = cost
    try:
        if st == "營量":
            o = R.simulate_mtm(sg_, f"H{sp['H']}", sp["N"], np.random.default_rng(sp["seed0"] + r), cl, op, NP, log=[], d_max=None, pick="relvol",
                               queue_days=0, return_equity=True, **kw)
        else:
            o = R.simulate_mtm(sg_, f"H{sp['H']}", sp["N"], np.random.default_rng(sp["seed0"] + r), cl, op, NP, return_equity=True, **kw)
    finally:
        R.COST = c0
    a = dict(SF=kw.get("stop_force"), cost=cost, tradable=kw.get("tradable"), delist=kw.get("delist"), sale_gross=fsg)
    off = sim_swap(sg_, st, r, cl, op, NP, a["SF"], swap=False, cost=cost, tradable=a["tradable"], delist=a["delist"], sale_gross=fsg)
    on = sim_swap(sg_, st, r, cl, op, NP, a["SF"], swap=True, cost=cost, tradable=a["tradable"], delist=a["delist"], sale_gross=fsg)
    eq0 = np.asarray(o["equity"], float)
    met = lambda eq, f_, e_: {sg: tuple(map(float, RR.win_metrics(eq, f_, e_, x, y)[:2])) for sg, (x, y) in W["segp"].items()}   # noqa: E731
    res = {"st": st, "r": r, "G_eq": bool(np.array_equal(eq0, off["equity"]) and int(o["first"]) == off["first"] and int(o["end"]) == off["end"]),
           "met0": met(eq0, int(o["first"]), int(o["end"])), "met": met(on["equity"], on["first"], on["end"]),
           "L": int(sum(e["池內已出場"] for e in on["tlog"])), "seg": {}}
    for sg, (x, y) in W["segp"].items():
        sw = [e for e in on["swaps"] if x <= e["t"] <= y]
        tl = [e for e in on["tlog"] if x <= e["t"] <= y]
        res["seg"][sg] = {"換股數": len(sw), "有換股的不同月數": len({W["cal"][e["t"]].strftime("%Y-%m") for e in sw}),
                          "換進不可成交": int(sum(e["換進不可成交"] for e in tl)), "池不足未換": int(sum(e["池不足未換"] for e in tl))}
    return res


# ═════════════ 彙總 ═════════════
def verdict(cells_sw, fq, pr):
    """S3：cells_sw[段] 有 對大盤；fq[段] 有 換股÷原版買進、有換股的不同月數；pr[段] 有 買進重疊÷本版。"""
    deg = any((fq[sg]["換股÷原版買進"] or 0) < DEG_SW or (pr[sg]["買進重疊÷本版"] or 0) >= DEG_OV for sg in JSEG)
    if deg:
        return "等同原版"
    if min(fq[sg]["有換股的不同月數"] for sg in JSEG) < NEFF_MIN:
        return "還沒測（依構造）"
    labs = [cells_sw[sg]["對大盤"] for sg in JSEG]
    if all(x == "合格" for x in labs):
        return "合格（暫定）"
    if all(x in ("合格", "另列") for x in labs):
        return "另列"
    return "不合格"


def med_key(rs, path, k):
    vals = []
    for z in rs:
        v = z
        for p in path:
            v = v[p]
        vals.append(v[k])
    return q3([x for x in vals if x is not None])


FQK = ["換股數", "原版買進", "換股÷原版買進", "有換股的不同月數", "觸發日", "觸發股", "有空槽未換", "池不足未換", "池內已出場",
       "換出後原到期前買回", "換出後任何時候買回", "被換持有天數_平均", "代價_筆", "代價_差平均", "代價_差中位", "代價_差為正比例",
       "代價_換出若抱到期平均", "代價_換進同期平均", "代價_換進抱到自己到期平均", "代價_自己到期差平均"]
PRK = ["買進重疊÷本版", "買進重疊÷原版", "金額持股重疊_平均", "日報酬相關"]
VK = ["買進", "筆換手每年", "金額換手每年", "平均持股", "現金比例"]


def aggregate(wn, RES, W):
    F = _F[wn]; cal = W["cal"]; segs = W["segp"]; tri = F["tri"]
    CELL, FREQ, SEEDS = [], [], []
    for st in M.STRATS:
        rs = sorted([z for z in RES if z["wn"] == wn and z["st"] == st], key=lambda z: z["r"])
        r0 = rs[0]
        for v in VERS:
            for sg, (x, y) in segs.items():
                cs = [z["ver"][v][sg]["年化"] for z in rs]; ms = [z["ver"][v][sg]["回落"] for z in rs]
                for z in rs:
                    SEEDS.append({"世界": wn, "策略": st, "版": v, "段": sg, "r": z["r"], "年化": z["ver"][v][sg]["年化"], "回落": z["ver"][v][sg]["回落"],
                                  **({"換股數": z["freq" if v == "換股版" else "freq20"][sg]["換股數"]} if v != "原版" else {})})
                c, m = float(np.median(cs)), float(np.median(ms))
                bt = BR.bstat(cal, tri, x, y)
                b50 = RR.bench_row(cal, np.asarray(W["bench"], float), x, y + 1)
                pts = F["pts"][sg]
                tm = tri[pts[1:]] / tri[pts[:-1]] - 1.0
                ce = GR.mci(np.mean([z["ver"][v][sg]["月報酬"] for z in rs], axis=0) - tm)
                row = {"世界": wn, "策略": st, "版": v, "段": sg, "段起": str(cal[x].date()), "段尾": str(cal[y].date()), "種子數": len(rs),
                       "年化": c, "回落": m, "比值": AS.ratio(c, m), "年化_p10": q3(cs)["p10"], "年化_p90": q3(cs)["p90"],
                       "回落_p10": q3(ms)["p10"], "回落_p90": q3(ms)["p90"], "年化_r0": cs[0], "回落_r0": ms[0],
                       "大盤年化": bt["cagr"] if bt else None, "大盤回落": bt["mdd"] if bt else None, "大盤比值": bt["ratio"] if bt else None,
                       "對大盤差": (c - bt["cagr"]) if bt else None, "對大盤": AS.label(c, m, bt) if bt else "—",
                       "對大盤_r0": AS.label(cs[0], ms[0], bt) if bt else "—",
                       "逐顆合格比例": float(np.mean([AS.label(a_, b_, bt) == "合格" for a_, b_ in zip(cs, ms)])) if bt else None,
                       "0050年化": b50["cagr"], "0050回落": b50["mdd"],
                       "月超額平均": ce["平均"], "月超額CI下": ce["CI95"][0], "月超額CI上": ce["CI95"][1], "月數": ce["月數"]}
                for k in VK:
                    row[k] = float(np.median([z["ver"][v][sg][k] for z in rs]))
                CELL.append(row)
            for sg in segs:
                if v == "原版":
                    continue
                fk, pk = ("freq", "pair") if v == "換股版" else ("freq20", "pair20")
                row = {"世界": wn, "策略": st, "版": v, "段": sg}
                for k in FQK:
                    qq = med_key(rs, (fk, sg), k)
                    row[k + "_中位"] = qq["中位"]; row[k + "_p10"] = qq["p10"]; row[k + "_p90"] = qq["p90"]; row[k + "_r0"] = r0[fk][sg][k]
                for k in PRK:
                    qq = med_key(rs, (pk, sg), k)
                    row[k + "_中位"] = qq["中位"]; row[k + "_r0"] = r0[pk][sg][k]
                for k in ("被換持有天數", "距原版到期"):
                    for s_ in ("中位", "p10", "p90"):
                        row[f"{k}_{s_}_r0"] = r0[fk][sg][k][s_]
                        row[f"{k}_{s_}_種子中位"] = q3([z[fk][sg][k][s_] for z in rs])["中位"]
                yrs = Counter()
                for z in rs:
                    yrs.update(z[fk][sg]["每年換股"].keys())
                row["每年換股_r0"] = json.dumps(r0[fk][sg]["每年換股"], ensure_ascii=False)
                row["每年換股_種子中位"] = json.dumps({y_: float(np.median([z[fk][sg]["每年換股"].get(y_, 0) for z in rs])) for y_ in sorted(yrs)}, ensure_ascii=False)
                FREQ.append(row)
    return CELL, FREQ, SEEDS


def pick(rows, **kw):
    return next(x for x in rows if all(x[k] == v for k, v in kw.items()))


def judge(CELL, FREQ):
    out = {}
    for st in M.STRATS:
        cs = {sg: pick(CELL, 世界="main", 策略=st, 版="換股版", 段=sg) for sg in JSEG}
        fr = {sg: pick(FREQ, 世界="main", 策略=st, 版="換股版", 段=sg) for sg in JSEG}
        fq = {sg: {"換股÷原版買進": fr[sg]["換股÷原版買進_中位"], "有換股的不同月數": fr[sg]["有換股的不同月數_中位"]} for sg in JSEG}
        fq0 = {sg: {"換股÷原版買進": fr[sg]["換股÷原版買進_r0"], "有換股的不同月數": fr[sg]["有換股的不同月數_r0"]} for sg in JSEG}
        pr = {sg: {"買進重疊÷本版": fr[sg]["買進重疊÷本版_中位"]} for sg in JSEG}
        out[st] = {"判語": verdict(cs, fq, pr), "r0構造": verdict({sg: {"對大盤": cs[sg]["對大盤_r0"]} for sg in JSEG}, fq0,
                                                              {sg: {"買進重疊÷本版": fr[sg]["買進重疊÷本版_r0"]} for sg in JSEG})}
    return out


def real_part(WS, procs):
    from backtest import researchYLSell5 as YS
    from backtest import researchSlip as SL
    W = WS["主"]; S = _F["main"]["S"]
    YS._G["COST0"] = R.COST
    SLm, X = YS.slip_setup(W, procs, log)
    spec = dict(SL.ARMS)[YS.SLIP_ARM]
    REF, gate_g = {}, {}
    _F["real"] = {}; _F["realW"] = W
    for st in M.STRATS:
        sig = M.cell_sig(S, st, "原版", dry=False)
        seeds = list(range(1 if st == "營量" else NSEED))
        REF[st] = YS.slip_run(SLm, X, W, st, sig, False, seeds)
        cell = f"YLS5_{st}"
        sg_, op, cost, kw = SL.arm_inputs(cell, spec, sig, X, W["closes"], W["opens"])
        f = slip_sale_gross(X, spec["cap"] / SL.CELLS[cell]["N"])
        sid = sig["sid"].astype(str).to_numpy(); e = sig["entry_pos"].to_numpy(int); xx = sig[f"xpos_H{M.STRATS[st]['H']}"].to_numpy(int)
        ok_av = np.array([np.isfinite(X[s]["avg"][a]) and X[s]["avg"][a] > 0 and np.isfinite(X[s]["avg"][b]) for s, a, b in zip(sid, e, xx)])
        mine = np.array([f(s, a, b, 1.0, 1.0) if k else np.nan for s, a, b, k in zip(sid, e, xx, ok_av)])
        ref = sg_[f"g_H{M.STRATS[st]['H']}"].to_numpy(float)
        gate_g[st] = {"列": int(len(sid)), "均價有效列": int(ok_av.sum()), "換出式重算＝arm_inputs（逐位元）": int(np.sum(mine[ok_av] == ref[ok_av]))}
        _F["real"][st] = {"sig": sg_, "op": op, "cost": cost, "kw": kw, "sale": f}
        log(f"[現實版] {st} 原版 slip_run {len(seeds)} 顆｜成本 {cost:.5f}｜{gate_g[st]}")
    if abs(R.COST - YS._G["COST0"]) > 1e-15:
        raise SystemExit("⛔ 現實版跑完引擎成本沒還原")
    jobs = [("營量", 0)] + [("營飆", r) for r in range(NSEED)]
    with Pool(procs) as pool:
        RS = pool.map(job_real, jobs, chunksize=4)
    bad_met = sum(int(z["met0"] != REF[z["st"]][z["r"]]["met"]) for z in RS)
    gate = {"換出式": gate_g, "引擎直呼 vs slip_run 指標不同（條）": bad_met,
            "sim_swap 關換股 vs 引擎 權益逐位元": f"{sum(z['G_eq'] for z in RS)}/{len(RS)}", "池內已出場": int(sum(z["L"] for z in RS))}
    log(f"[現實版閘] {gate}")
    if bad_met or not all(z["G_eq"] for z in RS) or gate["池內已出場"]:
        raise SystemExit(f"⛔ 現實版閘不過 {gate}")
    if any(z["換出式重算＝arm_inputs（逐位元）"] != z["均價有效列"] for z in gate_g.values()):
        raise SystemExit(f"⛔ 換出衝擊式與 arm_inputs 不同 {gate_g}")
    return RS, gate, YS.SLIP_ARM


def real_table(RS, W, tri, J):
    rows = []
    out = {}
    for st in M.STRATS:
        rs = [z for z in RS if z["st"] == st]
        labs = {}
        for v, key in (("原版", "met0"), ("換股版", "met")):
            for sg, (x, y) in W["segp"].items():
                cs = [z[key][sg][0] for z in rs]; ms = [z[key][sg][1] for z in rs]
                c, m = float(np.median(cs)), float(np.median(ms))
                bt = BR.bstat(W["cal"], tri, x, y)
                lab = AS.label(c, m, bt) if bt else "—"
                rr = {"策略": st, "版": v, "段": sg, "年化": c, "回落": m, "比值": AS.ratio(c, m), "大盤年化": bt["cagr"] if bt else None,
                      "大盤比值": bt["ratio"] if bt else None, "對大盤": lab}
                if v == "換股版":
                    rr["換股數_中位"] = float(np.median([z["seg"][sg]["換股數"] for z in rs]))
                    rr["換進不可成交_中位"] = float(np.median([z["seg"][sg]["換進不可成交"] for z in rs]))
                    rr["有換股月數_中位"] = float(np.median([z["seg"][sg]["有換股的不同月數"] for z in rs]))
                    labs[sg] = lab
                rows.append(rr)
        base = J[st]["判語"]
        if base in ("等同原版", "還沒測（依構造）"):
            rv = base
        elif all(labs[sg] == "合格" for sg in JSEG):
            rv = "合格（暫定）"
        elif all(labs[sg] in ("合格", "另列") for sg in JSEG):
            rv = "另列"
        else:
            rv = "不合格"
        out[st] = {"判語": rv, "改判": rv != base, "標籤": labs}
    return rows, out


# ═════════════ 主流程 ═════════════
def run(a):
    T0 = time.time()
    A = {"讀法寫死": TIME, "開跑": GR.now_tpe() + "（台北）", "種子": NSEED}
    A["登錄"] = mailbox_gate(); log(f"[登錄] {A['登錄']}")
    A["策略鎖"] = [GR.lock_check("開跑前")]
    if abs(R.COST - COST) > 1e-15:
        raise SystemExit(f"⛔ 引擎成本 {R.COST} ≠ 0.585%")
    WS = AO.worlds(log, a.procs)
    tri_s = BR.read_series(GR.TRI_SRC)
    tri_sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    gates = {}
    for wn in ("main", "early"):
        W = WS[WNM[wn]]
        Gp = pickle.load(open(os.path.join(M.WORK, f"groups_{wn}_industry.pkl"), "rb"))
        P, dr = GR.dry_repro(wn, Gp["S"])
        if dr["不同"]:
            raise SystemExit(f"⛔ {wn} 乾跑重現不符 {dr}")
        if not (len(P["cal"]) == len(W["cal"]) and (P["cal"] == W["cal"]).all() and P["NP"] == W["NP"] and P["SF"] == W["SF"]):
            raise SystemExit(f"⛔ {wn} freq 世界與 AddOn 世界不同")
        S, ag = GR.attach_g(Gp["S"], W)
        cg = GR.cand_gate(S, wn, W["cal"])
        if cg["不符"]:
            raise SystemExit(f"⛔ {wn} 候選逐年不符 freq_industry {cg}")
        ME, _ = PFQ.month_ends(W["cal"])
        tri = np.r_[tri_s.reindex(W["cal"]).ffill().to_numpy(float), [np.nan] * (W["NP"] - len(W["cal"]))]
        _F[wn] = {"S": S, "NP": W["NP"], "cal": W["cal"], "segp": W["segp"], "closes": W["closes"], "opens": W["opens"], "SF": W["SF"],
                  "pts": {sg: GR.seg_points(ME, x, y) for sg, (x, y) in W["segp"].items()}, "tri": tri}
        gates[f"{wn} 乾跑重現"] = dr; gates[f"{wn} 訊號表接 g"] = ag; gates[f"{wn} 候選逐年族群轉強 ＝ freq_industry"] = cg
        log(f"[{wn}] 閘 {dr}｜{ag}｜{cg}")
    jobs = [(wn, "營量", 0) for wn in ("main", "early")] + [(wn, "營飆", r) for wn in ("main", "early") for r in range(NSEED)]
    RES = []
    with Pool(a.procs) as pool:
        for i, z in enumerate(pool.imap_unordered(job, jobs, chunksize=2)):
            RES.append(z)
            if (i + 1) % 40 == 0:
                log(f"  真路徑 {i + 1}/{len(jobs)} {time.time() - T0:.0f}s")
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    nb = sum(int(z["eq_sha"] != REF.get((WNM[z["wn"]], IG.YL if z["st"] == "營量" else IG.YF, z["r"]))) for z in RES)
    gG = {f"{wn}·{st}": {k: f"{sum(z['G'][k] for z in RES if z['wn'] == wn and z['st'] == st)}/{sum(1 for z in RES if z['wn'] == wn and z['st'] == st)}"
                         for k in RES[0]["G"]} for wn in ("main", "early") for st in M.STRATS}
    gates["原版 eq_sha ≠ resultsYL_integrate（條數）"] = nb
    gates["閘G 關換股 ＝ 原版 run_engine"] = gG
    gates["閘L 池內已出場（應 0）"] = int(sum(z["L"] for z in RES))
    log(f"[閘] 原版 eq_sha 不同 {nb}／{len(RES)}｜G {gG}｜L {gates['閘L 池內已出場（應 0）']}")
    if nb:
        raise SystemExit("⛔ 原版權益與正式營量 v1／營飆 v1 不同")
    if not all(all(z["G"].values()) for z in RES):
        raise SystemExit("⛔ 閘 G 不過：關掉換股不等於原版")
    if gates["閘L 池內已出場（應 0）"]:
        raise SystemExit("⛔ 閘 L 不過")
    CELL, FREQ, SEEDS = [], [], []
    for wn in ("main", "early"):
        c_, f_, s_ = aggregate(wn, RES, WS[WNM[wn]])
        CELL += c_; FREQ += f_; SEEDS += s_
    J = judge(CELL, FREQ)
    RS, rgate, arm = real_part(WS, a.procs)
    RROWS, RJ = real_table(RS, WS["主"], _F["main"]["tri"], J)
    gates["現實版"] = rgate
    ROWS = [x for z in RES if z["r"] == 0 for x in z.get("rows", [])]
    A.update({"閘": gates, "大盤報酬指數": f"{GR.TRI_SRC}（origin/main {tri_sha}）", "判語": J, "現實版": {"臂": arm, "判": RJ}})
    A["策略鎖"].append(GR.lock_check("跑完"))
    A["耗時秒"] = round(time.time() - T0)
    write_all(A, CELL, FREQ, SEEDS, ROWS, RROWS)
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


# ═════════════ 輸出 ═════════════
pc = GR.pc


def f2(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x:.{d}f}"


def write_all(A, CELL, FREQ, SEEDS, ROWS, RROWS):
    os.makedirs(OUT, exist_ok=True)
    C = pd.DataFrame(CELL); Fq = pd.DataFrame(FREQ)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    Fq.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    pd.DataFrame(ROWS).to_csv(os.path.join(OUT, "swaps_r0.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    pd.DataFrame(RROWS).to_csv(os.path.join(OUT, "real.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    pd.DataFrame(SEEDS).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.8g")

    def c(wn, st, v, sg):
        return pick(CELL, 世界=wn, 策略=st, 版=v, 段=sg)

    def fr(wn, st, sg, v="換股版"):
        return pick(FREQ, 世界=wn, 策略=st, 版=v, 段=sg)

    def rl(st, v, sg):
        return pick(RROWS, 策略=st, 版=v, 段=sg)

    J = A["判語"]; RJ = A["現實版"]["判"]
    sent = []
    for st in M.STRATS:
        segs_ = []
        for sg in JSEG:
            z = c("main", st, "換股版", sg); f = fr("main", st, sg)
            segs_.append(f"{sg} 年化 {pc(z['年化'])}、回落 {pc(z['回落'])}（比值 {f2(z['比值'])}）對大盤 {pc(z['大盤年化'])}／比值 {f2(z['大盤比值'])}"
                         f"（{z['對大盤']}）；有換股月數 {f['有換股的不同月數_中位']:.0f}（r0 {f['有換股的不同月數_r0']}）、換股÷原版 {pc(f['換股÷原版買進_中位'], 0)}、"
                         f"買進重疊 {pc(f['買進重疊÷本版_中位'], 0)}")
        o_ = {sg: c("main", st, "原版", sg) for sg in JSEG}; n_ = {sg: c("main", st, "換股版", sg) for sg in JSEG}
        sent.append(f"{st}：{J[st]['判語']}（{'；'.join(segs_)}）。年換手（金額）原版 {o_['探索']['金額換手每年']:.1f}／{o_['確認']['金額換手每年']:.1f} → 本版 "
                    f"{n_['探索']['金額換手每年']:.1f}／{n_['確認']['金額換手每年']:.1f}（探索／確認）；真實成本版 {RJ[st]['判語']}（{'改判' if RJ[st]['改判'] else '不改判'}）")
    sent += SENT
    A["結果句"] = sent
    json.dump(A, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    L = ["# 換掉最差那檔（營量、營飆族群轉強出現就換）額外策略　正式跑", "",
         f"登錄 台股 seq1 sha {A['登錄']['sha16']}（{A['登錄']['bytes']} B，相符）｜發號 裁定 seq504 §二｜正式跑核可 裁定 seq505 §二（閘 `--formal --ruling seq505`）｜"
         f"讀法寫死 {TIME}｜開跑 {A['開跑']}｜回測線計算子代理", "",
         "｜".join(SENT), "",
         "## 〇、先講結論", ""]
    for st in M.STRATS:
        L.append(f"- **{st}：{J[st]['判語']}**　真實成本版：{RJ[st]['判語']}（{'改判' if RJ[st]['改判'] else '不改判'}）")
    L += ["", "（營飆 ＝ 200 顆種子中位；營量 ＝ r0 一條；判語順序：等同原版 → 有換股月數 ＜ 24 → 對大盤兩段標籤；已看過相關結果 ⇒ 合格最多暫定）", "",
          "## 一、兩格主表（主段，各自對大盤報酬指數）", "",
          "| 格 | 段 | 年化 | 最大回落 | 年化÷\\|回落\\| | 大盤 年化／回落／比值 | 對大盤差 | 標籤 | 月超額平均〔95% CI〕 | 有換股月數 中位（r0） | 換股÷原版 | 買進重疊÷本版 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for st in M.STRATS:
        for sg in JSEG:
            z = c("main", st, "換股版", sg); f = fr("main", st, sg)
            yr = pc(z["年化"]) + (f"〔{pc(z['年化_p10'])}～{pc(z['年化_p90'])}〕" if st == "營飆" else "")
            L.append(f"| {st} | {sg} | {yr} | {pc(z['回落'])} | {f2(z['比值'])} | {pc(z['大盤年化'])}／{pc(z['大盤回落'])}／{f2(z['大盤比值'])} | "
                     f"{pc(z['對大盤差'], sign=True)} | {z['對大盤']} | {pc(z['月超額平均'], 2, True)}〔{pc(z['月超額CI下'], 2, True)}～{pc(z['月超額CI上'], 2, True)}〕 | "
                     f"{f['有換股的不同月數_中位']:.0f}（{f['有換股的不同月數_r0']}） | {pc(f['換股÷原版買進_中位'], 0)} | {pc(f['買進重疊÷本版_中位'], 0)} |")
    L += ["", "- 〈四十九〉以正式跑真路徑為準（裁定 seq505 §二①）；營飆判語依種子中位，r0 構造量並列："
          + "；".join(f"{st} r0 依構造 ⇒ {J[st]['r0構造']}" for st in M.STRATS),
          "- 月超額 CI：每月一群、描述用、⛔ 不進判語；持有 60／120 日 ⇒ 月與月不獨立、CI 偏窄。", "",
          "## 二、真實成本版（" + A["現實版"]["臂"] + "；主世界）", "",
          "| 格 | 段 | 原版 年化／回落 | 本版 年化／回落／比值 | 大盤 年化／比值 | 本版標籤 | 本版換股數（中位） | 換進漲停買不到（中位） |", "|---|---|---|---|---|---|---|---|"]
    for st in M.STRATS:
        for sg in JSEG:
            o_, n_ = rl(st, "原版", sg), rl(st, "換股版", sg)
            L.append(f"| {st} | {sg} | {pc(o_['年化'])}／{pc(o_['回落'])} | {pc(n_['年化'])}／{pc(n_['回落'])}／{f2(n_['比值'])} | {pc(n_['大盤年化'])}／{f2(n_['大盤比值'])} | "
                     f"{n_['對大盤']} | {n_['換股數_中位']:.0f} | {n_['換進不可成交_中位']:.0f} |")
    L += ["", "年換手（買進金額 ÷ 平均權益 ÷ 年；括號 ＝ 買進筆 ÷ N ÷ 年）：", ""]
    for st in M.STRATS:
        L.append(f"- {st}：" + "；".join(f"{sg} 原版 {c('main', st, '原版', sg)['金額換手每年']:.1f}（{c('main', st, '原版', sg)['筆換手每年']:.1f}）→ 本版 "
                                         f"{c('main', st, '換股版', sg)['金額換手每年']:.1f}（{c('main', st, '換股版', sg)['筆換手每年']:.1f}）" for sg in JSEG))
    L += ["", "## 三、換錯的代價（每次換股：換進那檔 − 被換那檔「若照原版抱到期」；同一段期間 ＝ 換股日開盤到被換那檔原到期日收盤；還原、毛、未扣成本）", "",
          "| 格 | 段 | 筆（中位） | 每筆差 平均 | 每筆差 中位 | 差為正的比例 | 被換那檔若抱到期 平均 | 換進同期 平均 | 〔另〕換進抱到自己到期 − 被換抱到期 平均 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for wn in ("main", "early"):
        for st in M.STRATS:
            for sg in (JSEG if wn == "main" else ("早年",)):
                f = fr(wn, st, sg)
                L.append(f"| {st}{'（早年）' if wn == 'early' else ''} | {sg} | {f['代價_筆_中位']:.0f} | {pc(f['代價_差平均_中位'], 2, True)}（r0 {pc(f['代價_差平均_r0'], 2, True)}） | "
                         f"{pc(f['代價_差中位_中位'], 2, True)}（r0 {pc(f['代價_差中位_r0'], 2, True)}） | {pc(f['代價_差為正比例_中位'], 0)} | "
                         f"{pc(f['代價_換出若抱到期平均_中位'], 2, True)} | {pc(f['代價_換進同期平均_中位'], 2, True)} | {pc(f['代價_自己到期差平均_中位'], 2, True)} |")
    L += ["", "營飆：每顆種子各自的平均／中位，再取 200 顆中位（括號 r0）。每次換股另多付一次來回 0.585%（上表未扣）。", "",
          "## 四、頻率表項目（真路徑重報；營飆 ＝ 種子中位，括號 r0）", "",
          "| 格 | 段 | 原版買進 | 換股數 | 換股÷原版 | 有換股月數 | 被換那檔持有天數 中位〔p10～p90〕 | 距原版到期 中位〔p10～p90〕 | 換出後原到期前買回／之後任何時候買回 | 平均持股 原→本 | 觸發股／池不足未換／有空槽未換 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for wn in ("main", "early"):
        for st in M.STRATS:
            for sg in (JSEG if wn == "main" else ("早年",)):
                f = fr(wn, st, sg); o_, n_ = c(wn, st, "原版", sg), c(wn, st, "換股版", sg)
                L.append(f"| {st}{'（早年）' if wn == 'early' else ''} | {sg} | {f['原版買進_中位']:.0f} | {f['換股數_中位']:.0f}（{f['換股數_r0']}） | {pc(f['換股÷原版買進_中位'], 0)} | "
                         f"{f['有換股的不同月數_中位']:.0f}（{f['有換股的不同月數_r0']}） | "
                         f"{f2(f['被換持有天數_中位_種子中位'], 0)}〔{f2(f['被換持有天數_p10_種子中位'], 0)}～{f2(f['被換持有天數_p90_種子中位'], 0)}〕 | "
                         f"{f2(f['距原版到期_中位_種子中位'], 0)}〔{f2(f['距原版到期_p10_種子中位'], 0)}～{f2(f['距原版到期_p90_種子中位'], 0)}〕 | "
                         f"{f['換出後原到期前買回_中位']:.0f}／{f['換出後任何時候買回_中位']:.0f} | {o_['平均持股']:.1f}→{n_['平均持股']:.1f} | "
                         f"{f['觸發股_中位']:.0f}／{f['池不足未換_中位']:.0f}／{f['有空槽未換_中位']:.0f} |")
    L += ["", "| 格 | 段 | 買進重疊 ÷本版／÷原版 | 金額權重逐日持股重疊 | 日報酬相關 | 每年換股（r0） |", "|---|---|---|---|---|---|"]
    for wn in ("main", "early"):
        for st in M.STRATS:
            for sg in (JSEG if wn == "main" else ("早年",)):
                f = fr(wn, st, sg)
                L.append(f"| {st}{'（早年）' if wn == 'early' else ''} | {sg} | {pc(f['買進重疊÷本版_中位'], 0)}／{pc(f['買進重疊÷原版_中位'], 0)} | "
                         f"{pc(f['金額持股重疊_平均_中位'], 0)} | {f2(f['日報酬相關_中位'])} | {f['每年換股_r0']} |")
    conc = []
    for st in M.STRATS:
        for sg in JSEG:
            yy = json.loads(fr("main", st, sg)["每年換股_r0"])
            if yy:
                ky = max(yy, key=yy.get)
                conc.append(f"{st} {sg} {ky} 年占 {pc(yy[ky] / sum(yy.values()), 0)}")
    L += ["", "- ⚠ 換股集中（r0，描述）：" + "；".join(conc) + "（族群轉強旗標集中在少數年份；有換股月數過 24 但多數換股落在一年內）。"]
    L += ["", "## 五、與原版並列（只描述，⛔ 不據此改正式規則）", "",
          "| 策略 | 段 | 原版 年化／回落／比值（標籤） | 本版 年化／回落／比值（標籤） | 滿 20 日才可換 年化／回落／比值（標籤，描述） | 現金比例 原／本 |", "|---|---|---|---|---|---|"]
    for wn in ("main", "early"):
        for st in M.STRATS:
            for sg in (JSEG if wn == "main" else ("早年",)):
                o_, n_, t_ = c(wn, st, "原版", sg), c(wn, st, "換股版", sg), c(wn, st, "滿20日版", sg)
                L.append(f"| {st}{'（早年）' if wn == 'early' else ''} | {sg} | {pc(o_['年化'])}／{pc(o_['回落'])}／{f2(o_['比值'])}（{o_['對大盤']}） | "
                         f"{pc(n_['年化'])}／{pc(n_['回落'])}／{f2(n_['比值'])}（{n_['對大盤']}） | {pc(t_['年化'])}／{pc(t_['回落'])}／{f2(t_['比值'])}（{t_['對大盤']}） | "
                         f"{pc(o_['現金比例'])}／{pc(n_['現金比例'])} |")
    L += ["", "- 滿 20 日版（描述）換股數：" + "；".join(f"{st} {sg} {fr('main', st, sg, '滿20日版')['換股數_中位']:.0f}（換股÷原版 "
                                                     f"{pc(fr('main', st, sg, '滿20日版')['換股÷原版買進_中位'], 0)}）" for st in M.STRATS for sg in JSEG),
          "- 本版與原版的差（年化、回落）只描述；登錄先驗 ② 是「分不出」，⛔ 不寫優劣。", "",
          "## 六、早年 2005～2014（只描述）", "",
          "早年：只描述（旗標＝自建 v2）；含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市。"
          "數字見上面各表「（早年）」列。", "",
          "## 七、閘", "", f"- {json.dumps(A['閘'], ensure_ascii=False, default=str)}", f"- 策略鎖：{A['策略鎖']}", "",
          "## 八、★ 執行者定（登錄沒寫清楚）", "",
          "- ★1 被換候選池 ＝ 觸發日收盤持有、排程出場日在第 t 日之後、買進日在第 t 日之前；停止交易強制出場在 t 者排除。",
          "- ★2 最差 ＝ 觸發日收盤 ÷ 引擎進場價 − 1；同分換較早買進的，再同照持股列序。",
          "- ★3 營飆觸發股排序 ＝ 另一條同種子衍生抽籤流（不動原版抽籤流，⇒ 換股為 0 時與原版逐位元相同）；營量 ＝ relvol 遞減。",
          "- ★4 換出 ＝ 第 t 日開盤賣（無效改收盤）；換進金額 ＝ min(前一日權益 ÷ N, 現金)；成本照引擎慣例在賣出時一次扣來回 0.585%。",
          "- ★5 原版正常買進後仍有空槽（現金不足、真實成本版漲停）⇒ 不換（照原版）。",
          "- ★6 退化判準任一段成立即「等同原版」；〈四十九〉營飆依種子中位。",
          "- ★7 換錯的代價 ＝ 同期（換股日開盤 → 被換那檔原到期日收盤）、毛報酬；另一欄換進抱到自己到期。",
          "- ★8 換出後又買回：原到期日前（t ＜ 買回日 ＜ 原到期日）與之後任何時候兩種。",
          "- ★9 真實成本版：換出賣價 ＝ 均價、衝擊照 C2 同式；換出那天跌停／停牌不在池；換進那天漲停／停牌該觸發不買。", "",
          "## 九、結果句（必附）", ""] + [f"- {s}" for s in A["結果句"]] + ["", "描述，不是買賣建議"]
    open(os.path.join(OUT, "結果.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main(argv=None):
    a = parse_gate(sys.argv[1:] if argv is None else argv)
    os.makedirs(OUT, exist_ok=True)
    GR.LOGF = os.path.join(OUT, "run.log")
    log(f"[開跑] {GR.now_tpe()}（台北）NSEED {NSEED}｜輸出 {OUT}")
    run(a)


if __name__ == "__main__":
    main()

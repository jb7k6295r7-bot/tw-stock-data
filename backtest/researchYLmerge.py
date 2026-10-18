# -*- coding: utf-8 -*-
"""營量 v1 與 營飆 v1「融合成一個」的描述性測試（使用者：「可以融合成一個就好？」→「你試試看怎麼結合」）——回測線計算子代理。
⭐ 描述、⛔ 不計 N、事後設計；⛔ 不改營量 v1／營飆 v1 任何規則；⛔ 不改任何既有 .py／結果夾；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLmerge [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLmerge_check [--procs 3]

═══ 讀法（寫死於 2026-10-18（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1、營飆 v1 各段年化／回落、resultsYLvsYF 全表
    （持股重疊、閘、各半①②）、resultsYL_integrate 36 格挑格結果（挑中 ＝ 營量 v1；⚠ M1～M5 都是該 36 格中的格，整合件已算過、本線看過其排序前 5）⇒
    融合變體是看過兩策略結果後才設計的，只描述）═══
 V1 變體（寫死，⛔ 不再加）；引擎 ＝ researchYL_integrate.eng（＝ research11.simulate_mtm 原式，只換 H／S／閘／挑法）：
    營量v1 ＝ H60·S20·無·relvol（對照）        營飆v1 ＝ H120·S10·閘·抽籤（對照；200 顆）
    M1 ＝ H60·S20·閘·relvol（營量 v1 ＋ t−1 大盤閘）   M2 ＝ H120·S20·無·relvol（營量 v1 改 H120）
    M3 ＝ H120·S20·閘·relvol（營量 v1 ＋ 閘 ＋ H120）  M4 ＝ H120·S10·閘·relvol（營飆 v1 改 relvol 挑、不抽籤）
    M5 ＝ H90·S15·閘·relvol（一本帳折衷）
    relvol 版：r ＝ 0～199 全跑、驗權益逐位元相同後報 r0 單值
 V2 對照組合（兩策略各一本帳、資金各半）：
    各半·年調 ＝ researchp17.compose(營飆窗內權益, 營量窗內權益, w＝0.5, 每年第一個交易日調回（窗首不算）, 換手 × 0.585%)（＝ researchYfSlots2／YfMix13 AB50）
      窗 ＝ 各世界的 [w0, w1]（主窗 2017-03-02～2026-08-24；早年 2005-02-01～2014-12-31）一條，段用 rerun17.win_metrics 切讀
    各半·日調 ＝ researchYL_integrate.blend_eq(w＝0.5)（每日再平衡、⚠ 不扣再平衡成本；＝ resultsYLvsYF 半半①）
    0050 ＝ 整合件 b50
 V3 段 ＝ 營飆 v1 原報告：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、早年 2005-02-01～2014-12-31（主窗只供對帳）
 V4 各段報：年化、最大回落（rerun17.win_metrics）、比值 ＝ 年化 ÷ |回落|、對 0050 ＝ researchYL_integrate.label（合格／另列／不合格）；
    平均持股、現金比例、換手（每年買進金額 ÷ 段內平均權益）、成本 ＝ 換手 × 0.585%（單一本帳 ＝ researchYL_integrate.stats 原式）
    組合：持股 ＝ 兩本帳持股聯集的檔數（同檔只算一次）；現金 ＝ Σ_腿 腿占比 × 腿現金比例；
          換手 ＝ （Σ 腿買進金額 × 腿占比換算 ＋ 再平衡移動金額）÷ 段內平均組合值 ÷ 年數（年調的再平衡金額 ＝ compose 的 turn；
          日調 ＝ 每日 |目標 − 現值|，⚠ 日調的年化沒有扣這部分成本）
    抽籤（營飆 v1、兩個各半）報 200 顆中位與 p10／p90；比值、標籤用中位
 V5 與營量 v1 的持股重疊（逐日平均，＝ researchYLvsYF.book／seg_overlap 口徑）：
    ⓐ 變體持股中也在營量持股的比例（檔數）；ⓑ 營量持股中也在變體的比例（檔數）；ⓒ 金額重疊 ＝ Σ_檔 min(變體權重, 營量權重)
 V6 閘（不過即停）：G1 營量 主 ＝ resultsT1fix c13 t1 r0；G2 營量＋M1～M5 兩世界 ＝ 整合件 seeds r0（eq_sha、全欄 repr）；G3 relvol 200 顆逐位元相同；
    G4 營飆 主 ＝ T1fix c1 t1 r0～199；G5 營飆 兩世界 ＝ 整合件 seeds 全欄 repr；
    G6 各半·年調：resultsYfMix13 AB50 早於 T1fix（兩腿 ＝ T1fix 'off' 版）⇒ 以 off 版兩腿走本檔同一條 compose 路徑 ＝ AB50 主窗（cagr、mdd、end_value、cost_sum repr）
       ＋ off 兩腿 eq_sha ＝ resultsT1fix off；本件數字用 T1fix 正式兩腿（t1 版）⇒ 與 AB50 不同屬 T1 補尾（2026-10-18 煙霧測試時發現、寫入此處；未改變任何變體）；
    G7 各半·日調 ＝ resultsYLvsYF seeds 半半①（repr）；G8 0050 ＝ 整合件 summary；G9 營飆對營量重疊 ⓐⓑⓒ ＝ resultsYLvsYF seeds（repr）
 必附：「融合變體是看過兩策略結果後才設計的，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證」；
       早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3
輸出 backtest/resultsYLmerge/：seeds.csv.gz、cells.csv、summary.json、REPORT.md、run.log
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
from backtest import research13 as R13                      # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchp17 as P17                     # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchYLvsYF as YV                   # noqa: E402

TIME = "2026-10-18（台北）"
OUT = "backtest/resultsYLmerge"
NSEED = 200
if os.environ.get("YLM_QUICK"):                              # 煙霧測試（不是交件）
    NSEED, OUT = 3, "/tmp/ylm_quick"
COST = R.COST
MCOST = 0.00585                                             # compose 換手成本（＝ researchYfSlots2.COST）
# ═══ 變體（寫死於看任何本件報酬之前；⛔ 不再加）═══
VAR = {"營量v1": IG.YL,
       "M1": IG.ck(60, 20, True, "relvol"),
       "M2": IG.ck(120, 20, False, "relvol"),
       "M3": IG.ck(120, 20, True, "relvol"),
       "M4": IG.ck(120, 10, True, "relvol"),
       "M5": IG.ck(90, 15, True, "relvol"),
       "營飆v1": IG.YF}
DESC = {"營量v1": "營量 v1（N20、relvol、H60、無閘）", "M1": "營量 v1 ＋ 大盤閘", "M2": "營量 v1 改 H120", "M3": "營量 v1 ＋ 閘 ＋ H120",
        "M4": "營飆 v1 改 relvol 挑（N10、閘、H120）", "M5": "一本帳 N15、relvol、閘、H90", "營飆v1": "營飆 v1（N10、抽籤、H120、閘）",
        "各半·年調": "兩者各半（每年第一個交易日調回、換手×0.585%）", "各半·日調": "兩者各半（每日再平衡、未扣再平衡成本）", "0050": "0050"}
RELV = [k for k, v in VAR.items() if IG.KEY[v][3] == "relvol"]
ROWS_ORDER = ["營量v1", "營飆v1", "各半·年調", "各半·日調", "M1", "M2", "M3", "M4", "M5", "0050"]
SEGS = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
REPSEG = (("主", "探索"), ("主", "確認"), ("早年", "早年"))
WORD = "描述、不計 N、事後設計"
MUST = "融合變體是看過兩策略結果後才設計的，只描述，不當改規則的依據；要採用須另行登錄、以前瞻驗證"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；早年照營飆 v1 早年既有版面（上市＋上櫃 eotc_f65bb03e11、R8 截斷）", IG.NOTE3]
_W: dict = {}


def leg(W, o, au):
    """單一本帳 ⇒ dict：eq、hv、buy[t]（當日買進金額）、book（researchYLvsYF.book）。"""
    eq = np.asarray(o["equity"], float); n = len(eq)
    buy = np.zeros(n)
    for a in au:
        if a["side"] == "buy":
            buy[a["t"]] += a["amt"]
    return {"o": o, "eq": eq, "hv": np.asarray(o["hold_val"], float), "buy": buy, "book": YV.book(W, o, au)}


def ov_with_yl(W, B):
    """單一本帳 B（book）對營量 ⇒ 各段 ⓐⓑⓒ。"""
    Y = W["YLB"]
    inter, ovA = YV.overlap_series(B, Y)
    out = {}
    for sg in SEGS[W["name"]]:
        x, y = W["segp"][sg]
        a, b, am, _, _ = YV.seg_overlap(B, Y, inter, ovA, x, y)
        out[f"{sg}_重疊a"], out[f"{sg}_重疊b"], out[f"{sg}_重疊c"] = a, b, am
    return out


def single_row(W, o, au):
    row, eq = IG.stats(W, o, au, None)
    L = leg(W, o, au)
    row.update(ov_with_yl(W, L["book"]))
    for sg in SEGS[W["name"]]:
        row[f"{sg}_成本每年"] = row[f"{sg}_換手每年"] * COST
    return row, L


def legs2(E, B, w, rebal):
    """compose 同一順序另回每日（調回後）兩腿值（＝ researchYfSlots2.legs2 同式；呼叫端斷言 V 與 compose 逐位元相同）。"""
    n = len(E); re_ = np.r_[1.0, E[1:] / E[:-1]]; rb_ = np.r_[1.0, B[1:] / B[:-1]]
    V = np.empty(n); VE = np.empty(n); VB = np.empty(n)
    ve, vb = w, 1.0 - w; V[0] = 1.0; VE[0] = ve; VB[0] = vb
    for t in range(1, n):
        ve *= re_[t]; vb *= rb_[t]; v = ve + vb
        if rebal[t]:
            tgt = w * v; c = abs(tgt - ve) * MCOST; v -= c; ve, vb = w * v, (1.0 - w) * v
        V[t] = v; VE[t] = ve; VB[t] = vb
    return V, VE, VB


def combo_stats(W, V, first, end, VF, VY, VFp, VYp, LF, LY, reb_turn):
    """組合（全長序列，窗外 NaN）⇒ 各段 年化、回落、持股（聯集）、現金、換手、成本、對營量重疊。
    VF、VY ＝ 每日收盤（調回後）兩腿在組合中的值（與 V 同單位）；VFp、VYp ＝ 第 t 天開盤前（前一日收盤）兩腿值；reb_turn[t] ＝ 第 t 天再平衡移動金額（V 單位）。"""
    n = len(V)
    eF, eY = LF["eq"], LY["eq"]
    sF = VF / V; sY = VY / V
    # 持股聯集、組合權重
    HF, HY = LF["book"][3], LY["book"][3]
    uni = np.zeros(n); inter = np.zeros(n); ovc = np.zeros(n)
    for s in set(HF) | set(HY):
        hf, wf = HF.get(s, (np.zeros(n, bool), np.zeros(n)))
        hy, wy = HY.get(s, (np.zeros(n, bool), np.zeros(n)))
        uni += (hf | hy); inter += hy                       # 聯集 ∩ 營量 ＝ 營量
        wc = np.nan_to_num(sF * wf + sY * wy)
        ovc += np.minimum(wc, wy)
    cnY = LY["book"][2]
    cash = sF * (1.0 - LF["hv"] / eF) + sY * (1.0 - LY["hv"] / eY)
    # 組合買進金額（V 單位）＝ 腿買進金額 × 前一日腿值 ÷ 前一日腿權益
    bF = np.zeros(n); bY = np.zeros(n)
    bF[1:] = LF["buy"][1:] * VFp[1:] / eF[:-1]; bY[1:] = LY["buy"][1:] * VYp[1:] / eY[:-1]
    row = {}
    for sg in SEGS[W["name"]]:
        x, y = W["segp"][sg]
        c_, m_, _ = RR.win_metrics(V, first, end, x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_持股"] = float(np.mean(uni[x:y + 1])); row[f"{sg}_現金"] = float(np.mean(cash[x:y + 1]))
        yrs = (y - x + 1) / 245.0; mv = float(np.mean(V[x:y + 1]))
        legt = float((bF[x:y + 1].sum() + bY[x:y + 1].sum()) / mv / yrs); rt = float(reb_turn[x:y + 1].sum() / mv / yrs)
        row[f"{sg}_換手每年"] = legt + rt; row[f"{sg}_再平衡換手每年"] = rt; row[f"{sg}_成本每年"] = (legt + rt) * COST
        u = uni[x:y + 1]; it = inter[x:y + 1]
        row[f"{sg}_重疊a"] = float(np.mean(it[u > 0] / u[u > 0])) if (u > 0).any() else np.nan
        cy = cnY[x:y + 1]
        row[f"{sg}_重疊b"] = float(np.mean(cy[cy > 0] / cy[cy > 0])) if (cy > 0).any() else np.nan   # 營量持股全在聯集裡 ⇒ 1
        row[f"{sg}_重疊c"] = float(np.mean(ovc[x:y + 1]))
    return row


# ═════════════ 工作 ═════════════
def job_relv(args):
    """relvol 變體：r＝0 全統計；r≥1 只取 eq_sha（驗 200 顆相同）。"""
    wn, name, r = args
    W = _W[wn]
    if r > 0:
        o, _ = IG.eng(W, VAR[name], r, audit=False)
        return {"世界": wn, "變體": name, "r": r, "eq_sha": YV.sha(o["equity"])}
    o, au = IG.eng(W, VAR[name], r)
    row, _ = single_row(W, o, au)
    row.update({"世界": wn, "變體": name, "r": r, "eq_sha": YV.sha(o["equity"]), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])})
    return row


def job_yf(args):
    """營飆 v1 種子 r ⇒ 營飆單列、各半·年調列、各半·日調列。"""
    wn, r = args
    W = _W[wn]; LY = W["YLL"]
    o, au = IG.eng(W, IG.YF, r)
    rowF, LF = single_row(W, o, au)
    rowF.update({"世界": wn, "變體": "營飆v1", "r": r, "eq_sha": YV.sha(o["equity"]), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])})
    eF, eY = LF["eq"], LY["eq"]; n = len(eF)
    w0, w1 = W["w0"], W["w1"]
    # ── 各半·年調（compose，窗 [w0, w1]）──
    EA, EB = eF[w0:w1 + 1], eY[w0:w1 + 1]
    Vw, turn, cst = P17.compose(EA, EB, np.full(len(EA), 0.5), W["REBAL"], cost=MCOST)
    V2, VE, VB = legs2(EA, EB, 0.5, W["REBAL"])
    if not np.array_equal(Vw, V2):
        raise SystemExit("⛔ legs2 與 compose 不逐位元相同")
    V = np.full(n, np.nan); VF = np.full(n, np.nan); VY = np.full(n, np.nan); RT = np.zeros(n)
    V[w0:w1 + 1] = Vw; VF[w0:w1 + 1] = VE; VY[w0:w1 + 1] = VB; RT[w0:w1 + 1] = turn
    VFp = np.r_[np.nan, VF[:-1]]; VYp = np.r_[np.nan, VY[:-1]]
    VFp[w0] = VF[w0] * eF[w0 - 1] / eF[w0]; VYp[w0] = VY[w0] * eY[w0 - 1] / eY[w0]   # 窗首：腿值以腿報酬倒推回前一日
    rowA = combo_stats(W, V, w0, w1 + 1, VF, VY, VFp, VYp, LF, LY, RT)
    c0, m0 = R13.window_stats(Vw, 0, len(Vw), 0, len(Vw))
    rowA.update({"世界": wn, "變體": "各半·年調", "r": r, "窗_cagr": float(c0), "窗_mdd": float(m0), "窗_end_value": 1_000_000 * Vw[-1] / Vw[0],
                 "窗_cost_sum": float(cst.sum())})
    # ── 各半·日調（blend_eq）──
    eB, fB, nB = IG.blend_eq(eF, o["first"], o["end"], eY, LY["o"]["first"], LY["o"]["end"], w=0.5)
    rF = np.zeros(n); rY = np.zeros(n)
    rF[1:nB] = eF[1:nB] / eF[:nB - 1] - 1; rY[1:nB] = eY[1:nB] / eY[:nB - 1] - 1
    half = 0.5 * eB
    rtd = np.zeros(n); rtd[1:] = 0.25 * np.abs(rF[1:] - rY[1:]) * eB[:-1]   # 調回前兩腿 0.5(1＋r) ⇒ |目標 − 現值| ＝ ¼|rF − rY| × 前一日組合值
    hp = np.r_[np.nan, half[:-1]]
    rowD = combo_stats(W, eB, fB, nB, half, half, hp, hp, LF, LY, rtd)
    rowD.update({"世界": wn, "變體": "各半·日調", "r": r})
    return [rowF, rowA, rowD]


def prep(W, log):
    o, au = IG.eng(W, IG.YL, 0)
    W["YLB"] = YV.book(W, o, au)
    W["YLL"] = leg(W, o, au)
    cal = W["cal"]; w0, w1 = W["w0"], W["w1"]
    W["REBAL"] = np.r_[False, pd.DatetimeIndex(cal[w0 + 1:w1 + 1]).year != pd.DatetimeIndex(cal[w0:w1]).year]
    log(f"[{W['name']}] 營量 eq_sha {YV.sha(o['equity'])}｜窗 {cal[w0].date()}～{cal[w1].date()}｜年調日 {int(W['REBAL'].sum())}")


def gate_compose_old(YFr, log):
    """G6：resultsYfMix13 AB50 是 T1fix 之前（T1 關、強制出場關 ＝ T1fix 'off' 版）的兩腿合成 ⇒ 用 off 版兩腿走本檔同一條 compose 路徑，
    須逐位元重現 AB50 主窗 cagr／mdd／end_value／cost_sum（200 顆）；另驗 off 兩腿 eq_sha ＝ resultsT1fix off。
    ⚠ 在所有 Pool 工作之後才呼叫（build_ctx(False) 會改 rerun17._G）。
    ⇒ 本件各半·年調 用的是 T1fix 正式兩腿（t1 版），數字與 AB50 不同是兩腿 T1 補尾所致，compose 路徑本身已由此閘驗過。"""
    from backtest import listexit_lines as L
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(False)
    w0, w1 = ctx["w0"], ctx["w1"]
    cal = ctx["cal"]
    rebal = np.r_[False, pd.DatetimeIndex(cal[w0 + 1:w1 + 1]).year != pd.DatetimeIndex(cal[w0:w1]).year]
    oB = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(7000), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True,
                        log=[], d_max=None, pick="relvol", queue_days=0)
    eB = np.asarray(oB["equity"], float)
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    off = t1[t1["var"] == "off"]
    o13 = off[(off["key"] == "c13") & (off["r"] == 0)]
    o1 = off[off["key"] == "c1"].set_index("r")
    mix = pd.read_csv("backtest/resultsYfMix13/mix_seeds.csv.gz", float_precision="round_trip")
    mix = mix[(mix["scope"] == "主窗") & (mix["mix"] == "AB50")].set_index("r")
    badsha = int(len(o13) and YV.sha(eB) != o13.iloc[0]["eq_sha"])
    bad = 0; badT = 0
    A_ = YFr[(YFr["變體"] == "各半·年調") & (YFr["世界"] == "主")].set_index("r")
    for r in range(NSEED):
        oA = L.sim(ctx, {}, r); eA = np.asarray(oA["equity"], float)
        if r in o1.index:
            badsha += int(YV.sha(eA) != o1.loc[r, "eq_sha"])
        V, _, cst = P17.compose(eA[w0:w1 + 1], eB[w0:w1 + 1], np.full(w1 - w0 + 1, 0.5), rebal, cost=MCOST)
        c, m = R13.window_stats(V, 0, len(V), 0, len(V))
        got = {"cagr": float(c), "mdd": float(m), "end_value": 1_000_000 * V[-1] / V[0], "cost_sum": float(cst.sum())}
        bad += sum(repr(float(got[k])) != repr(float(mix.loc[r, k])) for k in got)
        badT += int(repr(float(got["cagr"])) != repr(float(A_.loc[r, "窗_cagr"])))
    info = {"off 兩腿 eq_sha 對 resultsT1fix off": f"不同 {badsha}（c13 r0 ＋ c1 {len(o1)} 顆中的前 {NSEED}）",
            "T1fix 正式兩腿 vs off 兩腿 的各半·年調主窗年化 不同顆數": f"{badT}／{NSEED}（預期多數不同：T1 補尾）"}
    log(f"[G6] AB50 不同項數 {bad}｜{info}")
    return {"G6 各半·年調 compose 路徑：off 版兩腿 ＝ YfMix13 AB50 主窗（不同項數）": int(bad),
            "G6b off 版兩腿 eq_sha ＝ resultsT1fix off（不同數）": int(badsha)}, info


def q(v):
    v = pd.Series(v).astype(float)
    return float(v.median()), float(v.quantile(.1)), float(v.quantile(.9))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = YV.log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {YV.now_tpe()}（台北）｜讀法寫死 {TIME}｜變體 {VAR}｜種子 {NSEED}")
    Wm, gm = IG.main_world(log)
    We, ge = IG.early_world(log, a.procs)
    for W in (Wm, We):
        prep(W, log)
    _W["主"], _W["早年"] = Wm, We
    S = {"讀法寫死": TIME, "性質": WORD, "必附": MUST, "早年註": NOTE_EARLY, "變體": VAR, "世界閘": {**gm, **ge}}
    T0 = time.time()
    with Pool(a.procs) as pool:
        RV = pool.map(job_relv, [(wn, k, r) for wn in ("主", "早年") for k in RELV for r in range(NSEED)], chunksize=8)
        YF = pool.map(job_yf, [(wn, r) for wn in ("主", "早年") for r in range(NSEED)], chunksize=4)
    RV = pd.DataFrame(RV); YFr = pd.DataFrame([x for y in YF for x in y])
    log(f"[跑完] relvol {len(RV)}｜營飆＋各半 {len(YFr)}｜{time.time() - T0:.0f}s")
    SE = pd.concat([RV[RV["r"] == 0], YFr], ignore_index=True)
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    RV[["世界", "變體", "r", "eq_sha"]].to_csv(os.path.join(OUT, "relvol_sha.csv.gz"), index=False)
    # ═══ 閘 ═══
    gate = {}
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    y0 = SE[(SE["世界"] == "主") & (SE["變體"] == "營量v1")].iloc[0]
    gate["G1 營量 主 ＝ T1fix c13 t1 r0"] = int(y0["eq_sha"] != c13["eq_sha"] or repr(float(y0["主窗_年化"])) != repr(float(c13["cagr"]))
                                           or repr(float(y0["主窗_回落"])) != repr(float(c13["mdd"])))
    refI = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    icol = [c for c in refI.columns if c.split("_")[-1] in ("年化", "回落", "持股", "現金", "買進每年", "換手每年")]
    for wn in ("主", "早年"):
        bad = 0
        for k in RELV:
            m_ = SE[(SE["世界"] == wn) & (SE["變體"] == k)].iloc[0]
            for rr in (0, 1):
                b_ = refI[(refI["世界"] == wn) & (refI["格"] == VAR[k]) & (refI["r"] == rr)].iloc[0]
                bad += int(m_["eq_sha"] != b_["eq_sha"])
                bad += sum(repr(float(m_[c])) != repr(float(b_[c])) for c in icol if pd.notna(b_[c]) or (c in m_ and pd.notna(m_[c])))
        gate[f"G2 營量＋M1～M5 {wn} ＝ 整合件 r0／r1（不同項數）"] = int(bad)
    gate["G3 relvol 各變體 200 顆權益逐位元相同（不同的變體×世界數）"] = int(sum(g["eq_sha"].nunique() != 1 for _, g in RV.groupby(["世界", "變體"]))
                                                         + int(any(len(g) != NSEED for _, g in RV.groupby(["世界", "變體"]))))
    F = YFr[YFr["變體"] == "營飆v1"]
    r1 = t1[(t1["key"] == "c1") & (t1["var"] == "t1")].set_index("r")
    m1 = F[F["世界"] == "主"].set_index("r")
    gate["G4 營飆 主 ＝ T1fix c1 t1（不同顆數）"] = int(sum(m1.loc[r, "eq_sha"] != r1.loc[r, "eq_sha"] or repr(float(m1.loc[r, "主窗_年化"])) != repr(float(r1.loc[r, "cagr"]))
                                                 or repr(float(m1.loc[r, "主窗_回落"])) != repr(float(r1.loc[r, "mdd"])) for r in m1.index))
    for wn in ("主", "早年"):
        a_ = F[F["世界"] == wn].set_index("r"); b_ = refI[(refI["世界"] == wn) & (refI["格"] == IG.YF)].set_index("r")
        gate[f"G5 營飆 {wn} ＝ 整合件（不同顆數／{len(a_)}）"] = int(sum(
            a_.loc[r, "eq_sha"] != b_.loc[r, "eq_sha"] or any(repr(float(a_.loc[r, c])) != repr(float(b_.loc[r, c])) for c in icol if pd.notna(b_.loc[r, c]))
            for r in a_.index))
    g6, info6 = gate_compose_old(YFr, log)
    gate.update(g6); S["G6說明"] = info6
    vs = pd.read_csv("backtest/resultsYLvsYF/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    bad7 = bad9 = 0
    for wn in ("主", "早年"):
        Dd = YFr[(YFr["變體"] == "各半·日調") & (YFr["世界"] == wn)].set_index("r"); Ff = F[F["世界"] == wn].set_index("r")
        v_ = vs[vs["世界"] == wn].set_index("r")
        for r in Dd.index:
            for sg in SEGS[wn]:
                bad7 += repr(float(Dd.loc[r, f"{sg}_年化"])) != repr(float(v_.loc[r, f"{sg}_半半①年化"]))
                bad7 += repr(float(Dd.loc[r, f"{sg}_回落"])) != repr(float(v_.loc[r, f"{sg}_半半①回落"]))
                for k, kk in (("重疊a", "F中也在Y"), ("重疊b", "Y中也在F"), ("重疊c", "金額重疊")):
                    bad9 += repr(float(Ff.loc[r, f"{sg}_{k}"])) != repr(float(v_.loc[r, f"{sg}_{kk}"]))
    gate["G7 各半·日調 ＝ resultsYLvsYF 半半①（不同項數）"] = int(bad7)
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    gate["G8 0050 各段 ＝ 整合件（不同項數）"] = int(sum(repr(float(_W[wn]["b50"][sg][k])) != repr(float(sm[wn][sg][k]))
                                              for wn in ("主", "早年") for sg in SEGS[wn] for k in ("cagr", "mdd")))
    gate["G9 營飆對營量重疊 ⓐⓑⓒ ＝ resultsYLvsYF（不同項數）"] = int(bad9)
    S["閘"] = gate
    log(f"[閘] {gate}")
    bad = [k for k, v in gate.items() if v != 0]
    if bad and NSEED == 200:
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {bad}")
    # ═══ 彙總 ═══
    KS = ("年化", "回落", "持股", "現金", "換手每年", "成本每年", "重疊a", "重疊b", "重疊c")
    C = []
    for wn in ("主", "早年"):
        W = _W[wn]
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]; b = W["b50"][sg]
            for nm in ROWS_ORDER:
                row = {"世界": wn, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "變體": nm, "說明": DESC[nm]}
                if nm == "0050":
                    row.update({"顆數": 1, "年化": b["cagr"], "回落": b["mdd"]})
                else:
                    g = SE[(SE["世界"] == wn) & (SE["變體"] == nm)]
                    row["顆數"] = len(g)
                    for k in KS + (("再平衡換手每年",) if nm.startswith("各半") else ()):
                        m_, p10, p90 = q(g[f"{sg}_{k}"])
                        row[k] = m_
                        if len(g) > 1 and k in ("年化", "回落"):
                            row[f"{k}_p10"], row[f"{k}_p90"] = p10, p90
                row["比值"] = row["年化"] / abs(row["回落"])
                row["對0050"] = IG.label(row["年化"], row["回落"], b) if nm != "0050" else "—"
                C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S["表"] = C.to_dict("records"); S["0050"] = {wn: _W[wn]["b50"] for wn in _W}
    S["完成（台北）"] = YV.now_tpe()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(S, C)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    log("\n" + C[C["段"] != "主窗"][["段", "變體", "年化", "回落", "比值", "對0050", "持股", "現金", "換手每年", "重疊a", "重疊c"]].to_string(index=False))
    log(f"[完] {YV.now_tpe()}（台北）")


def pct(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.{d}f}%"


def sg_(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


def report(S, C):
    L = ["# 營量 v1 × 營飆 v1 融合：描述性測試", "", f"產出 {S['完成（台北）']}（台北）。回測線計算子代理。⭐ {WORD}。", "",
         f"> ⚠ {MUST}。", "",
         "> M1～M5 都是整合件（resultsYL_integrate）36 格中的格，整合件已算過、挑中的是營量 v1；本件逐位元重現並補上持股、現金、換手、與營量重疊。", "",
         "## 變體（看報酬前寫死）", "", "| 代號 | 內容 | 引擎格 |", "|---|---|---|"]
    L += [f"| {k} | {DESC[k]} | {v} |" for k, v in VAR.items()]
    L += ["| 各半·年調 | " + DESC["各半·年調"] + " | researchp17.compose w＝0.5 |", "| 各半·日調 | " + DESC["各半·日調"] + " | researchYL_integrate.blend_eq w＝0.5 |", ""]
    for wn, sg in REPSEG:
        g = C[(C["世界"] == wn) & (C["段"] == sg)]
        L += [f"## {sg}（{g.iloc[0]['窗']}）", "",
              "| 變體 | 年化 | 回落 | 比值 | 對 0050 | 平均持股 | 現金 | 換手／年 | 成本／年 | 與營量重疊 檔數ⓐ／金額ⓒ |", "|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in g.iterrows():
            rng = (f"（{sg_(r['年化_p10'])}～{sg_(r['年化_p90'])}）" if "年化_p10" in r and pd.notna(r.get("年化_p10")) else "")
            rngm = (f"（{sg_(r['回落_p10'])}～{sg_(r['回落_p90'])}）" if "回落_p10" in r and pd.notna(r.get("回落_p10")) else "")
            if r["變體"] == "0050":
                L.append(f"| 0050 | {sg_(r['年化'])} | {sg_(r['回落'])} | {r['比值']:.2f} | — | — | — | — | — | — |")
                continue
            L.append(f"| {r['變體']} | {sg_(r['年化'])}{rng} | {sg_(r['回落'])}{rngm} | {r['比值']:.2f} | {r['對0050']} | {r['持股']:.1f} | {pct(r['現金'])} | "
                     f"{r['換手每年']:.2f} | {pct(r['成本每年'], 2)} | {pct(r['重疊a'], 0)}／{pct(r['重疊c'], 0)} |")
        L.append("")
    L += ["註：", "- 抽籤的列（營飆 v1、兩個各半）＝ 200 顆中位，括號 p10～p90；比值、對 0050 用中位。relvol 列（營量 v1、M1～M5）200 顆權益逐位元相同 ⇒ 單值。",
          "- 對 0050：合格 ＝ 年化 ＞ 0050 且 比值 ≥ 0050；另列 ＝ 只贏年化；不合格 ＝ 年化沒贏（researchYL_integrate.label）。",
          "- 換手 ＝ 每年買進金額 ÷ 段內平均權益；成本 ＝ 換手 × 0.585%（已在權益裡扣過，此處只描述）。各半的平均持股 ＝ 兩本帳聯集（同檔算一次）；"
          "各半·日調的年化沒有扣每日再平衡成本（再平衡換手另列在 cells.csv）。",
          "- 與營量重疊：ⓐ 變體持股中也在營量持股的比例（逐日平均）；ⓒ 金額重疊 ＝ Σ min(變體權重, 營量權重)（逐日平均）；ⓑ 見 cells.csv。", "",
          "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "",
          f"早年註：{'；'.join(S['早年註'])}", "", f"> ⚠ {MUST}。", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

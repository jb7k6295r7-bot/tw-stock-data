# -*- coding: utf-8 -*-
"""PREREG海龜系統2組合層 seq1【正式跑】（台股策略線 登錄 sha 6fdcea50f3a9e53d，2026-10-18 10:40；裁定 seq368 准進組合層、seq369 發號；
N_組合 ＋1）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；researchTurtle（S2 偵測、N、2N 停損、通道出場、盤中觸價成交）、researchTurtle_freq、
researchAscTri（世界、判準 label／ratio）、rerun17（win_metrics、bench_row）⛔ 只 import。用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtleS2PF [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtleS2PF_check
輸出 backtest/resultsTurtleS2PF/：degeneracy.json（先寫）、TurtleS2PF.json、TurtleS2PF_main.csv、events_<世界>.csv.gz（S2 候選事件）、
    trades_<世界>_<臂>.csv.gz（組合實際成交）、eq_<世界>.npz（逐日權益、持股市值、0050 單位市值、待買回現金、持股數）、
    random_<世界>.csv.gz、burden_<世界>.csv.gz（每日掛單候選數）、run.log

⭐ 讀法寫死：2026-10-18 11:20～11:50（台北）之間寫檔；寫死前 ⛔ 沒看過任何海龜組合層數字（看過的只有事件層結果與頻率表）。

═══ 讀法（K 標；登錄沒寫清楚、執行者補的都在這裡；★＝執行者定，〔 〕內為另一讀法）═══
 K0 事件與出場 ⛔ 不另寫：逐股呼叫 researchTurtle.stock_job 原樣（＝ 事件層 seq2 正式跑同一支：S2 偵測、剔除、N（Wilder 20、段內起算）、
    停損 ＝ 買價 − 2N[k−1]、通道 ＝ 前 20 根最低、盤中觸價價 min(開, 線)、同根取低、鎖死跌停順延、壞根／下市／資料尾、進場當根不判出場）。
    候選事件 ＝ 該支 EVR["S2m"]（S2 保留事件中 N 有值、T 開盤有效者，⭐ 不套事件層的「持有中不重複」鏈——組合層另依自己的持股判）。
    查核：① S2、D4_S2 偵測 ＝ 已提交 resultsTurtle/freq/events_<世界>.csv.gz（鍵欄逐列）；② 事件層已提交 trades_<世界>_{S2,S2_當根停損,D4_S2}
    每一列的 買價、停損價、出場日、出場種類、R 與本支逐筆相同；任一不同 ⇒ 中止、⛔ 不算組合。
 K1 組合（登錄 §一；比照 researchAscTri A2 ＝ research11.simulate_mtm 規則）：10 槽；新部位 ＝ min(前一日收盤淨值 ÷ 10, 可撥款)
    ★「每檔買進時投入當時淨值 1/10」取【前一日收盤淨值】（＝ 引擎、上升三角組合層慣例）〔另一讀法：T 開盤時淨值〕；
    同日候選多於空位 ⇒ default_rng(1000)、每天 rng.permutation（候選依代號排序；引擎同一套抽法）；同一檔持有中不重複進場；
    ★ 同日先出後進（出場釋出的槽當天可給別檔）；★ 當天賣出的那一檔當天不再買（＝ 事件層 G7「T ＞ S」）〔另一讀法：可當天再買〕。
    ⛔ 不加碼；停損價買進後固定。
 K2 0050（登錄 §一 本線定；⭐ 與引擎不同 ⇒ 本支自寫組合迴圈，K9 驗「引擎模式」與 simulate_mtm 逐日相同）：
    窗首（日曆第 0 日收盤）淨值 1 全抱 0050（⛔ 不扣建倉成本，引擎慣例）；訊號日 T 以【T 日 0050 還原開盤】賣出撥款：
    要撥 amt ⇒ 賣 amt ÷ (1 − 0.2425%) 的 0050（賣：手續費 0.1425% ＋ 證交稅 0.1%）；個股賣出拿回的錢當天留現金（報酬 0），
    【隔天 0050 還原開盤】買回、付 0.1425%。★ 0050 成本照登錄字面不對稱（買 0.1425%、賣 0.2425%；上升三角組合層因引擎限制取對稱 0.1925%，本支自寫迴圈 ⇒ 照字面）。
    可撥款只算 0050（當天個股賣出的現金要隔天才回 0050，⛔ 不拿來撥當天的新部位）。0050 開盤缺值的日子 ⇒ 用前一日還原收盤（計數照報）。
    0050 不每日再平衡（閒置資金整包抱 0050，引擎 bench 慣例）。
 K3 個股成交：買價 P ＝ max(T 開盤, 前 55 日最高)（還原）；市值 ＝ amt × 收盤 ÷ P（停牌日 ffill 收盤）；賣出 ⇒ 入帳 amt × (1 ＋ R − 0.585%)
    （引擎成本口徑：0.585% 在賣出時對【買進金額】一次扣）。資料尾未出場 ⇒ 持有到資料尾、按收盤計值（⛔ 不賣、不扣賣出成本）。
    壞根前強制、下市末根 ⇒ 該根收盤賣（事件層 G5 原樣）、記在該根日曆日。
 K4 滑價版（登錄 §二）：個股買價 × 1.005、每筆賣價 × 0.995（含強制、末根）；R_滑 ＝ 賣價×0.995 ÷ (P×1.005) − 1；市值以 P×1.005 計；
    0050 不加滑價；其餘全同主判（同一組事件、同一顆抽籤種子）。資料尾未出場的帳面 ⇒ 收盤 ÷ (P×1.005)（尚未賣，⛔ 不扣賣出滑價）。
 K5 段（AscTri A6 ＝ researchAscTri_freq.SEGS）：探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾 2026-09-24｜早年 2005 首個交易日～2014-12-31；
    一個世界跑一次（主 2015-01-05 起、早年 2004-02-11 起），各段取權益曲線窗：年化、回落 ＝ rerun17.win_metrics；0050 ＝ rerun17.bench_row（同窗還原收盤）；
    判準 ＝ researchAscTri.label（使用者判準：合格 ＝ 年化 ＞ 0050 且 年化÷|回落| ≥ 0050；另列 ＝ 只贏年化；其餘不合格）。
 K6 整件（登錄 §二）：探索、確認主判都合格 且 兩段滑價版都不是「不合格」⇒ 合格（早年主判不合格 ⇒ 最多暫定）；
    主判兩段合格但任一段滑價版不合格 ⇒「紙上合格、實務不可用」；
    ★ 其餘（登錄沒寫）照上升三角組合層 A6：兩段主判都「合格或另列」⇒ 另列；否則不合格。
    退化（seq325）：探索段平均持股 ＜ 3 ⇒ 標退化、不判；⭐ 空位抱 0050 ⇒「現金 ＞ 30%」一條不用（seq360 §一）；先寫 degeneracy.json 再讀報酬。
 K7 隨機進場（登錄 §二 ②；比照 AscTri A9）：主判實際買進的每一天 t 買了 k 檔 ⇒ 從 t 當天同母體（Frame.gate ∧ pit_valid ∧ 有成交 ∧ 非壞根 ∧
    T 開盤有效 ∧ 非開盤鎖漲停 ∧ N[k−1] 有值 ∧ 出場可算或資料尾持有中 ＝ 事件層 G8 對照池，⛔ 不看是否突破、⛔ 不扣事件股——AscTri A9 同）
    不重複抽 k 檔（母體依代號排序；default_rng([20261017, 世界, i])）；★ 隨機股以 T【開盤】買（無通道價可觸，＝ 事件層 G8 對照式），
    出場同規則（各自 20 日低點、各自 2N（＝ 開盤 − 2N[k−1]）、T＋1 起判；＝ researchTurtle C_S2m 原樣）；同一個組合迴圈、同 0050 規則、
    同抽籤種子 1000；200 次；p ＝ 隨機 年化÷|回落| ≥ 主判 的比例（另報 年化 ≥ 主判）；各段各報。
 K8 描述（⛔ 不判、不計 N）：
    D4 ＝ 事件層 D4_S2 原樣（收盤 ＞ 前 55 日最高 ⇒ T＋1 開盤買；收盤 ＜ 前 20 日最低或收盤 ≤ 停損 ⇒ 隔天開盤賣；EVR["D4S2"]）；
       0050 在【買進日（T＋1）】開盤撥款（★）。
    D6 ＝ 事件層「S2_當根停損」原樣（EVR["S2a"]：進場當根最低 ≤ 停損 ⇒ 當根以停損價賣）；★ 當根就賣的部位：進場、出場同一天，
       槽當天釋出但當天不再補（當天新部位已在出場前排定）。
    D7 ＝ 同主判進場、固定抱 60 個交易日：★ 賣在日曆位置 ≥ T＋60 的第一根有效 K 棒收盤（事件層「固定抱 60」用 T＋60 ffill 收盤，
       組合層要真的賣得出 ⇒ 取那天或之後第一個有成交日）；途中遇壞根 ⇒ 壞根前一根收盤；之後無成交 ⇒ 下市末根／資料尾照 K3。
    D8 ＝ 主判但空位留現金（無 0050、無 0050 成本；個股賣出的錢隔天才可再用，與主判同步）。
 K9 引擎模式驗證：本支迴圈切到「引擎模式」（0050 以收盤價進出、對稱 0.1925%、賣出當天即買回 0050、不擋當天再買）⇒ 合成 fixture 與
    主世界主判實際事件都與 research11.simulate_mtm（cash_mode="bench"）逐日權益相對差 ≤ 1e−9（正規化到第一筆進場前一日）。
 K10 必報（AscTri A8 同式）：換手 ＝ 段內買進金額 ÷ 段內平均淨值 ÷ 年（年 ＝ 交易日 ÷ 245）；成本／年 ＝ 換手 × 0.585%（另報實付個股成本、
    實付 0050 成本、合計）；平均持股 ＝ 段內逐日收盤持股檔數平均（買進日算、賣出日不算）；空位率 ＝ 1 − 平均持股 ÷ 10（另報有空位日比例）；
    0050 占淨值 ＝ 0050 市值 ÷ 淨值 段內平均（另報待買回現金占比）；平均持有天數 ＝ 賣出日 − 買進日（日曆位置；資料尾未出場不計）；
    勝率 ＝ R − 0.585% ＞ 0 比例、平均賺賠比 ＝ 賺筆平均 ÷ |賠筆平均|（資料尾未出場不計、另報筆數）；出場種類占比（分母含資料尾未出場）；
    停損後 20 日內又創新高 ＝ 事件層 rehigh 旗標（2N 停損出場後 20 根有效 K 棒內又出現 S2 原始偵測）。逐筆統計依【買進日】歸段。
 K11 操作負擔（登錄 §四）：★ 第 t 天要掛觸價買單的候選 ＝ 前一根有效 K 棒 k（日曆 t−1，即 t 前一日有成交）收盤 ≥ 0.97 × 觸價線
    （觸價線 ＝ 第 k−54～k 根最高價之最大值 ＝ t 當天的「前 55 日最高」；前 55 根彼此相連）∧ t−1 在母體（Frame.gate ∧ pit_valid）。
    報每日檔數的平均、中位、p90、最多；另報「扣掉 t−1 收盤已持有」的版本。
 K12 結果句必附（登錄 §四）：★1 原意「優勢大部分在突破當天盤中到收盤那一段；改成收盤判、隔天開盤買就消失或縮小；當根也判停損時事件層只剩 +0.33%（測不出）」、
    ★2「盤中觸價；主判未計滑價，另報每邊 +0.5%」、「需每天對候選股掛觸價買單」；早年附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTurtle as RTT                  # noqa: E402  事件、出場（⛔ 只 import）
from backtest import researchTurtle_freq as RT              # noqa: E402  偵測、段（⛔ 只 import）
from backtest import researchAscTri as AS                   # noqa: E402  load_world、label、ratio（⛔ 只 import）
from backtest import researchUO_freq as RU                  # noqa: E402  load_sig（RT.stock_job 需要）
from backtest import research11 as R                        # noqa: E402  load_bars、simulate_mtm（K9）
from backtest import rerun17 as RR                          # noqa: E402  win_metrics、bench_row
from backtest import data as D                              # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402  log_to
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-18 11:20～11:50（台北）"
REG_SHA = "6fdcea50f3a9e53d"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsTurtleS2PF"
TFREQ = "backtest/resultsTurtle/freq"
TEV = "backtest/resultsTurtle/events"
NS = 10
SEED_ENG = 1000
RSEED = 20261017
NRAND = 200
WID = {"主": 0, "早年": 1}
COST = R.COST
BC_BUY = 0.001425
BC_SELL = 0.001425 + 0.001
BC_SYM = (0.001425 * 2 + 0.001) / 2
SLIP = 0.005
DEG_HOLD = 3.0
NEAR = 0.97
H55 = 55
HOLD7 = 60
TYPN = {1: "通道出場訊號(跌破20日低點)", 2: "2N停損", 3: "壞根前一根收盤強制", 4: "末根收盤(下市/之後無成交)", 5: "資料尾未出場", 6: "第60日收盤(D7)"}
ARMS = {"M": {"名": "主判：盤中觸價買、20 日低點／2N 停損、空位抱 0050", "src": "S2m", "mode": "main", "slip": False, "judge": True},
        "Mslip": {"名": "主判＋滑價每邊 0.5%（可執行性條款）", "src": "S2m", "mode": "main", "slip": True, "judge": True},
        "D4": {"名": "D4：收盤判、隔天開盤買賣（描述）", "src": "D4S2", "mode": "main", "slip": False, "judge": False},
        "D6": {"名": "D6：進場當根也判停損（描述）", "src": "S2a", "mode": "main", "slip": False, "judge": False},
        "D7": {"名": "D7：同進場、固定抱 60 個交易日（描述，⛔ 不當出場比較基準）", "src": "D7", "mode": "main", "slip": False, "judge": False},
        "D8": {"名": "D8：主判但空位留現金（描述）", "src": "S2m", "mode": "cash", "slip": False, "judge": False}}
SENT = ["優勢大部分在突破當天盤中到收盤那一段；改成收盤判、隔天開盤買就消失或縮小；當根也判停損時事件層只剩 +0.33%（測不出）",
        "盤中觸價；主判未計滑價，另報每邊 +0.5%",
        "需每天對候選股掛觸價買單"]
NOTE_EARLY = AS.NOTE_EARLY
_G: dict = {}
LOG = None


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ 組合迴圈（K1～K3、K9）═════════════
def simulate(tr, n0, CM, Bc, Bo, mode, block_same=True, seed=SEED_ENG, record=True, fund_pend=False):
    """tr：dict of arrays（依 (ent, 代號) 排序）：j（股欄）、ent（進場日曆位置）、ext（出場日曆位置，−1 ＝ 資料尾不出）、ep（市值基準價）、g（R）。
    mode：main（K2：0050 開盤進出、隔天買回）／cash（D8）／engine（K9：0050 收盤進出、對稱成本、當天買回）。
    fund_pend：⛔ 預設 False（＝ 正式跑 K2）；True ＝ 補充描述「另一讀法 K2′」：當天個股賣出的現金先拿來撥當天新部位，不足才賣 0050（只 main／cash）。"""
    j_, ent, ext, ep, g = tr["j"], tr["ent"], tr["ext"], tr["ep"], tr["g"]
    m = len(ent)
    by = {}
    for q in range(m):
        by.setdefault(int(ent[q]), []).append(q)
    rng = np.random.default_rng(seed)
    eq = np.zeros(n0); hv_a = np.zeros(n0); u_a = np.zeros(n0); p_a = np.zeros(n0); nh = np.zeros(n0, np.int16)
    if mode == "cash":
        units = 0.0; cash = 1.0
    else:
        units = 1.0 / Bc[0]; cash = 0.0
    pend = 0.0
    openp = []; held = set()
    buys = []; sells = []; etf = []
    for t in range(n0):
        if pend > 0.0:
            if mode == "main":
                cst = pend * BC_BUY
                units += (pend - cst) / Bo[t]
                if record:
                    etf.append((t, 1, pend, cst))
            else:
                cash += pend
            pend = 0.0
        sold = set(); still = []
        for q, amt in openp:
            if 0 <= ext[q] <= t:
                proc = amt * (1 + g[q] - COST)
                if mode == "engine":
                    units += amt * (1 + g[q] - COST) * (1 - BC_SYM) / Bc[t]
                else:
                    pend += proc
                held.discard(j_[q]); sold.add(j_[q])
                if record:
                    sells.append((t, q, amt, proc))
            else:
                still.append((q, amt))
        openp = still
        L = by.get(t)
        today = []
        if L is not None and len(openp) < NS:
            cand = [q for q in L if j_[q] not in held and not (block_same and j_[q] in sold)]
            if cand:
                order = rng.permutation(len(cand))
                slot = (eq[t - 1] if t > 0 else 1.0) / NS
                for i in order[:NS - len(openp)]:
                    q = cand[i]
                    if mode == "main":
                        avail = units * Bo[t] * (1 - BC_SELL)
                    elif mode == "engine":
                        avail = units * Bc[t] * (1 - BC_SYM)
                    else:
                        avail = cash
                    if fund_pend and mode != "engine":
                        avail = avail + pend
                    amt = min(slot, avail)
                    if amt <= 1e-9:
                        break
                    rest = amt
                    if fund_pend and mode != "engine":
                        use_p = min(amt, pend); pend -= use_p; rest = amt - use_p
                    if mode == "main":
                        if rest > 0.0:
                            gro = rest / (1 - BC_SELL)
                            units -= rest / ((1 - BC_SELL) * Bo[t])
                            if record:
                                etf.append((t, -1, gro, gro * BC_SELL))
                    elif mode == "engine":
                        units -= amt / ((1 - BC_SYM) * Bc[t])
                    else:
                        cash -= rest
                    openp.append((q, amt)); held.add(j_[q]); today.append(q)
                    if record:
                        buys.append((t, q, amt))
        if today and mode != "engine":                     # 進場當根就賣（D6、下一根壞根）；引擎模式照引擎留到隔天（K9）
            still = []
            for q, amt in openp:
                if ext[q] == t and ent[q] == t:
                    proc = amt * (1 + g[q] - COST)
                    pend += proc
                    held.discard(j_[q])
                    if record:
                        sells.append((t, q, amt, proc))
                else:
                    still.append((q, amt))
            openp = still
        hv = 0.0
        for q, amt in openp:
            hv += amt * CM[j_[q], t] / ep[q]
        if mode == "engine":
            eq[t] = units * Bc[t] + hv
        else:
            eq[t] = units * Bc[t] + cash + pend + hv
        hv_a[t] = hv; u_a[t] = units * Bc[t] if mode != "cash" else cash; p_a[t] = pend; nh[t] = len(openp)
    if not np.all(np.isfinite(eq)):
        raise SystemExit(f"⛔ 權益出現非有限值（首個 {np.flatnonzero(~np.isfinite(eq))[:3]}）")
    return {"eq": eq, "hv": hv_a, "u": u_a, "pend": p_a, "nh": nh, "buys": buys, "sells": sells, "etf": etf,
            "open_end": [q for q, _ in openp]}


# ═════════════ fixture ═════════════
def selftest(log):
    msgs = []
    rng = np.random.default_rng(11)
    worst = 0.0
    for rep in range(25):
        ncal = 260; S = 25
        C = 20 * np.exp(np.cumsum(rng.normal(0, 0.02, (S, ncal)), axis=1))
        O = C * np.exp(rng.normal(0, 0.01, (S, ncal)))
        bench = 50 * np.exp(np.cumsum(rng.normal(0, 0.01, ncal)))
        rows = []
        seen = set()
        for _ in range(int(rng.integers(30, 140))):
            s = int(rng.integers(0, S)); e = int(rng.integers(3, ncal - 50)); x = e + int(rng.integers(1, 45))
            if (s, e) in seen:
                continue
            seen.add((s, e))
            rows.append((f"{1000 + s}", s, e, x, float(C[s, x] / O[s, e] - 1.0 + rng.normal(0, 0.01))))
        rows.sort(key=lambda r: (r[2], r[0]))
        sig = pd.DataFrame({"sid": [r[0] for r in rows], "entry_pos": [r[2] for r in rows], "xpos_D": [r[3] for r in rows], "g_D": [r[4] for r in rows]})
        closes = {f"{1000 + s}": C[s] for s in range(S)}; opens = {f"{1000 + s}": O[s] for s in range(S)}
        o = R.simulate_mtm(sig, "D", NS, np.random.default_rng(SEED_ENG), closes, opens, ncal, return_equity=True, cash_mode="bench", bench=bench, bench_cost=BC_SYM)
        tr = {"j": np.array([r[1] for r in rows]), "ent": np.array([r[2] for r in rows]), "ext": np.array([r[3] for r in rows]),
              "ep": np.array([O[r[1], r[2]] for r in rows]), "g": np.array([r[4] for r in rows])}
        me = simulate(tr, ncal, C, bench, bench, "engine", block_same=False, record=False)["eq"]
        f, e_ = int(o["first"]), int(o["end"])
        a = me[f - 1:e_] / me[f - 1]; b = np.asarray(o["equity"])[f - 1:e_]
        d = float(np.max(np.abs(a / b - 1.0))); worst = max(worst, d)
        assert d < 1e-9, (rep, d)
    msgs.append(f"F1 引擎模式 ＝ research11.simulate_mtm(cash_mode='bench')（合成 25 組，逐日權益最大相對差 {worst:.1e}）")
    # F2 主模式手算：1 檔、0050 開盤撥款、隔天開盤買回
    C = np.array([[10.0, 11.0, 12.0, 12.5, 13.0]]); Bc = np.array([100.0, 101.0, 102.0, 103.0, 104.0]); Bo = np.array([99.0, 100.5, 101.5, 102.5, 103.5])
    tr = {"j": np.array([0]), "ent": np.array([1]), "ext": np.array([3]), "ep": np.array([10.5]), "g": np.array([12.6 / 10.5 - 1])}
    r = simulate(tr, 5, C, Bc, Bo, "main")
    u0 = 1 / 100.0; amt = 0.1 * (u0 * Bc[0]); u1 = u0 - amt / ((1 - BC_SELL) * Bo[1])
    e1 = u1 * Bc[1] + amt * 11 / 10.5; e2 = u1 * Bc[2] + amt * 12 / 10.5
    proc = amt * (1 + 12.6 / 10.5 - 1 - COST); e3 = u1 * Bc[3] + proc
    u4 = u1 + proc * (1 - BC_BUY) / Bo[4]; e4 = u4 * Bc[4]
    assert np.allclose(r["eq"], [1.0, e1, e2, e3, e4], rtol=0, atol=1e-15), (r["eq"], [1.0, e1, e2, e3, e4])
    msgs.append("F2 主模式手算（T 開盤賣 0050 撥款 0.2425%、P 買、收盤計值、賣出當天留現金、隔天開盤買回 0050 0.1425%）逐位元相同")
    # F3 D6 同根進出、當天賣出不再買
    tr = {"j": np.array([0, 0]), "ent": np.array([1, 3]), "ext": np.array([1, 4]), "ep": np.array([10.5, 12.0]), "g": np.array([-0.05, 0.02])}
    r = simulate(tr, 5, C, Bc, Bo, "main")
    assert [b[0] for b in r["buys"]] == [1, 3] and [s[0] for s in r["sells"]] == [1, 4] and r["nh"].tolist() == [0, 0, 0, 1, 0]
    tr = {"j": np.array([0, 0]), "ent": np.array([1, 3]), "ext": np.array([3, 4]), "ep": np.array([10.5, 12.0]), "g": np.array([0.1, 0.02])}
    r = simulate(tr, 5, C, Bc, Bo, "main")
    assert [b[0] for b in r["buys"]] == [1] and r["nh"].tolist() == [0, 1, 1, 0, 0]
    msgs.append("F3 D6 進場當根出場、當天賣出的那檔當天不再買（K1、K8）")
    # F4 滑價式
    P, px = 10.0, 12.0
    assert abs((px * (1 - SLIP)) / (P * (1 + SLIP)) - 1 - (11.94 / 10.05 - 1)) < 1e-15
    msgs.append("F4 滑價 R ＝ 賣價×0.995 ÷ (買價×1.005) − 1")
    for m_ in msgs:
        log("✅ " + m_)
    return msgs


# ═════════════ 逐股 ═════════════
def d7_exit(idx, c, bad, n0, k, T):
    nb = len(idx)
    q = int(np.searchsorted(idx, T + HOLD7, "left"))
    bb = np.flatnonzero(bad[k + 1:]) + k + 1
    b = int(bb[0]) if len(bb) else nb
    if b < nb and b <= q:
        return int(idx[b - 1]), float(c[b - 1]), 3
    if q >= nb:
        if (n0 - 1 - idx[-1]) >= RTT.GAP_END:
            return int(idx[nb - 1]), float(c[nb - 1]), 4
        return -1, np.nan, 5
    return int(idx[q]), float(c[q]), 6


EVF = ("T", "k", "P", "stop", "sell", "typ", "R", "rehigh", "pm", "Nprev")


def pack(d_):
    Ts = sorted(d_)
    return {f: np.array([d_[t][f] if f != "T" else t for t in Ts]) for f in EVF} if Ts else {f: np.zeros(0) for f in EVF}


def stock_job(a):
    wn, sid = a
    sid_, out = RTT.stock_job((wn, sid, False))           # ⭐ 事件層同一支
    if out is None:
        return sid, None
    W = RT._G[wn]; cal = W["cal"]; n0 = W["n0"]
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    idx = B["idx"].astype(np.int64); nb = len(idx)
    h, c = np.asarray(B["h"], float), np.asarray(B["c"], float)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    E = out["EVR"]
    res = {"ev": {"S1": [], "D4_S1": [], "S2": out["ev"]["S2"], "D4_S2": out["ev"]["D4_S2"]}, "nex": out["nex"]}
    for key in ("S2m", "S2a", "D4S2"):
        res[key] = pack(E[key])
    # D7
    d7 = {}
    for T, rec in E["S2m"].items():
        x, px, ty = d7_exit(idx, c, bad, n0, rec["k"], int(T))
        d7[int(T)] = {"sell": x, "px": px, "typ": ty}
    res["D7"] = d7
    # 隨機池（K7）＝ 事件層 G8 對照池 ∧ 出場可算或資料尾
    Rr, Ty, Hh = out["C_S2m"]
    pool = out["entS"] & out["pop"] & (np.isfinite(Rr) | (Ty == 5))
    pp = np.flatnonzero(pool)
    res["pool"] = (pp.astype(np.int32), Rr[pp], Ty[pp], Hh[pp])
    # 操作負擔（K11）
    lvl = pd.Series(h).rolling(H55, min_periods=H55).max().to_numpy()
    CB = np.r_[0, np.cumsum(bad)]
    kk = np.arange(nb)
    lo = np.clip(kk - H55 + 2, 0, nb)                      # [k−53, k] 無壞 K 棒 ⇒ 第 k−54～k 根相連
    clean = (kk >= H55 - 1) & ((CB[kk + 1] - CB[lo]) == 0)
    with np.errstate(invalid="ignore"):
        near = clean & np.isfinite(lvl) & (c >= NEAR * lvl) & out["pop"][idx]
    td = idx[near] + 1
    res["near"] = td[td < n0].astype(np.int32)
    return sid, res


# ═════════════ 統計 ═════════════
def seg_stats(W, S, TR, arm):
    eq, hv, u, pend, nh = S["eq"], S["hv"], S["u"], S["pend"], S["nh"]
    out = {}
    buys = S["buys"]; sells = {q: (t, amt, proc) for t, q, amt, proc in S["sells"]}
    etf = S["etf"]
    for sg, (x, y) in W["segp"].items():
        yrs = (y - x + 1) / 245.0
        meq = float(np.mean(eq[x:y + 1]))
        bs = [(t, q, amt) for t, q, amt in buys if x <= t <= y]
        sc = sum(amt * COST for t, q, amt, proc in S["sells"] if x <= t <= y)
        ec = sum(cst for t, sd, gro, cst in etf if x <= t <= y)
        hd = [sells[q][0] - t for t, q, amt in bs if q in sells]
        d = {"平均持股": float(np.mean(nh[x:y + 1])), "空位率": float(1 - np.mean(nh[x:y + 1]) / NS),
             "有空位日比例": float(np.mean(nh[x:y + 1] < NS)), "個股占淨值": float(np.mean(hv[x:y + 1] / eq[x:y + 1])),
             "0050占淨值": float(np.mean(u[x:y + 1] / eq[x:y + 1])) if ARMS[arm]["mode"] != "cash" else 0.0,
             "現金占淨值(含待買回)": float(np.mean((pend[x:y + 1] + (u[x:y + 1] if ARMS[arm]["mode"] == "cash" else 0)) / eq[x:y + 1])),
             "買進筆": len(bs), "買進每年": len(bs) / yrs, "換手每年": float(sum(a_ for _, _, a_ in bs) / meq / yrs),
             "平均持有天數": float(np.mean(hd)) if hd else np.nan, "持有天數中位": float(np.median(hd)) if hd else np.nan}
        d["成本每年(換手×0.585%)"] = d["換手每年"] * COST
        d["個股成本每年(實付)"] = float(sc / meq / yrs)
        d["0050成本每年(實付)"] = float(ec / meq / yrs)
        d["成本合計每年"] = d["個股成本每年(實付)"] + d["0050成本每年(實付)"]
        # 逐筆
        qs = [q for _, q, _ in bs]
        typ = np.array([TR["typ"][q] for q in qs], int) if qs else np.zeros(0, int)
        rn = np.array([TR["g"][q] - COST for q in qs], float) if qs else np.zeros(0)
        fin = typ != 5
        v = rn[fin]; w_ = v[v > 0]; l_ = v[v <= 0]
        d.update({"勝率": float((v > 0).mean()) if len(v) else np.nan,
                  "平均賺": float(w_.mean()) if len(w_) else np.nan, "平均賠": float(l_.mean()) if len(l_) else np.nan,
                  "平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
                  "逐筆淨報酬平均": float(v.mean()) if len(v) else np.nan, "資料尾未出場筆": int((~fin).sum())})
        for k_, nm in TYPN.items():
            d[f"出場占比_{nm}"] = float((typ == k_).mean()) if len(typ) else np.nan
        st = typ == 2
        d["停損後20日內又創新高比例"] = float(np.mean([TR["rehigh"][q] for q, s_ in zip(qs, st) if s_])) if st.any() and "rehigh" in TR else np.nan
        out[sg] = d
    return out


def metrics(W, eq, x, y):
    c_, m_, _ = RR.win_metrics(eq, 0, W["n0"], x, y)
    return float(c_), float(m_)


def verdict(L):
    le, lc, se, sc, lo = L["主判探索"], L["主判確認"], L["滑價探索"], L["滑價確認"], L["主判早年"]
    if le == "合格" and lc == "合格":
        if se != "不合格" and sc != "不合格":
            v = "暫定（早年不合格 ⇒ 最多暫定）" if lo == "不合格" else "合格"
        else:
            v = "紙上合格、實務不可用（主判兩段合格，但滑價版有不合格段）"
    elif le in ("合格", "另列") and lc in ("合格", "另列"):
        v = "另列（★ 登錄沒寫，照上升三角組合層 A6）" + ("（早年不合格）" if lo == "不合格" else "")
    else:
        v = "不合格"
    return v


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 隨機（K7）═════════════
def rand_rows(G, wn, i):
    RP = G["RP"]; st = RP["start"]
    rng = np.random.default_rng([RSEED, WID[wn], i])
    sel = []
    for t, k in G["DAYS"]:
        a_, b_ = int(st[t]), int(st[t + 1]); n = b_ - a_
        if n <= 0:
            continue
        sel.append(a_ + rng.choice(n, size=min(k, n), replace=False))
    sel = np.concatenate(sel) if sel else np.zeros(0, np.int64)
    sel = sel[np.lexsort((RP["rank"][sel], RP["t"][sel]))]
    tr = {"j": RP["j"][sel], "ent": RP["t"][sel], "ext": RP["ext"][sel], "ep": RP["ep"][sel], "g": RP["g"][sel]}
    return tr, len(sel)


def rand_job(a):
    wn, i = a
    G = _G[wn]
    tr, nrow = rand_rows(G, wn, i)
    S = simulate(tr, G["n0"], G["CM"], G["Bc"], G["Bo"], "main", record=True)
    row = {"世界": wn, "i": i, "列": nrow, "買進筆": len(S["buys"])}
    for sg, (x, y) in G["segp"].items():
        c_, m_, _ = RR.win_metrics(S["eq"], 0, G["n0"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    return row


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    if abs(COST - 0.00585) > 1e-15:
        raise SystemExit(f"⛔ R.COST {COST} ≠ 0.585%")
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}｜讀法寫死 {TIME}｜開跑 {now_tpe()}")
    J = {"讀法寫死": TIME, "登錄": f"PREREG海龜系統2組合層 seq1 sha {REG_SHA}（裁定 seq368 准、seq369 發號；N_組合 ＋1）", "登錄檔": regf,
         "結果句必附": SENT, "早年標註": NOTE_EARLY, "臂": {k: v["名"] for k, v in ARMS.items()},
         "成本": {"個股來回": COST, "0050買": BC_BUY, "0050賣": BC_SELL, "滑價每邊": SLIP}, "閘": {}, "時點": {"開跑": now_tpe()}}
    J["fixture"] = selftest(log)
    WS = {}; TRS = {}; SIMS = {}; RAWS = {}
    for wn in ("主", "早年"):
        W = AS.load_world(wn, log); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in RT.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["SIGPOS"], W["SIGPOS_YF"], _, _ = RU.load_sig(wn, cal)
        D.DATA = W["data"]
        bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float)
        nbo = np.flatnonzero(~(np.isfinite(bo) & (bo > 0)))
        Bc = np.asarray(W["bench"], float)
        Bo = bo.copy()
        for t in nbo:
            Bo[t] = Bc[t - 1] if t > 0 else Bc[0]
        W["Bc"] = Bc; W["Bo"] = Bo
        J["閘"][wn] = {"0050開盤缺值日(用前一日收盤)": [str(cal[t].date()) for t in nbo]}
        RT._G[wn] = W; WS[wn] = W
        log(f"[{wn}] 0050 開盤缺值 {len(nbo)} 日 {J['閘'][wn]['0050開盤缺值日(用前一日收盤)']}")
        t0 = time.time(); res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in W["sids"]], chunksize=8)):
                if r is not None:
                    res[sid] = r
                if (k_ + 1) % 400 == 0:
                    log(f"  [{wn}] 逐股 {k_ + 1}／{len(W['sids'])}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(res)} 檔｜{time.time() - t0:.0f}s")
        # ── K0 查核①：偵測 ＝ 頻率表事件檔（S2、D4_S2）
        mine = RTT.freq_frame([r["ev"] for r in res.values()], cal)
        ref = pd.read_csv(os.path.join(TFREQ, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)
        ref = ref[ref["格"].isin(["S2", "D4_S2"])].reset_index(drop=True)
        kc = ["格", "sid", "T", "k", "N", "前N日最高", "st"]
        same = mine.shape[0] == ref.shape[0] and (mine[kc].values == ref[kc].values).all()
        if not same:
            raise SystemExit(f"⛔ {wn} S2／D4_S2 偵測 ≠ 頻率表（{mine.shape} vs {ref.shape}）")
        J["閘"][wn]["偵測＝頻率表(S2,D4_S2 列數)"] = int(len(ref))
        log(f"[查核①] {wn} S2／D4_S2 偵測與頻率表逐列相同（{len(ref):,} 列）")
        # ── K0 查核②：事件層已提交逐筆
        dates = np.array([str(d.date()) for d in cal]); dpos = {d: i for i, d in enumerate(dates)}
        for cell, key in (("S2", "S2m"), ("S2_當根停損", "S2a"), ("D4_S2", "D4S2")):
            fr = pd.read_csv(os.path.join(TEV, f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str}, keep_default_na=False)
            nd = Counter(); nrow = 0
            for sid, Td, P_, st_, sd_, ty_, R_ in zip(fr["sid"], fr["T"], fr["買價"], fr["停損價"], fr["出場日"], fr["出場種類"], fr["R"]):
                ev = res[sid][key]; T = dpos[Td]
                q = int(np.searchsorted(ev["T"], T))
                if q >= len(ev["T"]) or ev["T"][q] != T:
                    nd["缺事件"] += 1; continue
                nrow += 1
                if abs(float(P_) / ev["P"][q] - 1) > 1e-12:
                    nd["買價"] += 1
                if abs(float(st_) - ev["stop"][q]) > 1e-9 * abs(ev["stop"][q]):
                    nd["停損價"] += 1
                s_ = dates[ev["sell"][q]] if ev["sell"][q] >= 0 else ""
                if s_ != sd_:
                    nd["出場日"] += 1
                if RTT.TYP[int(ev["typ"][q])] != ty_:
                    nd["出場種類"] += 1
                rr = float(R_) if R_ != "" else np.nan
                if not ((np.isnan(rr) and np.isnan(ev["R"][q])) or abs(rr - ev["R"][q]) <= 1e-12):
                    nd["R"] += 1
            J["閘"][wn][f"事件層逐筆對 {cell}"] = {"列": nrow, "不同": dict(nd)}
            log(f"[查核②] {wn} {cell}：{nrow:,} 列｜不同 {dict(nd)}")
            if nd:
                raise SystemExit(f"⛔ {wn} {cell} 與事件層已提交逐筆不同 {dict(nd)}")
        # ── 候選事件表
        S_ = W["sids"]; ix = W["ix"]
        CM = pd.DataFrame(np.asarray(W["C"], float)).ffill(axis=1).to_numpy(float)   # 停牌、資料尾 ffill（窗內本來就無缺）
        TR = {}
        for arm, cfg in ARMS.items():
            rows = []
            for sid, r in res.items():
                j = ix[sid]
                if cfg["src"] == "D7":
                    ev = r["S2m"]
                    for q in range(len(ev["T"])):
                        T = int(ev["T"][q]); d_ = r["D7"][T]; P_ = float(ev["P"][q])
                        g_ = d_["px"] / P_ - 1.0 if d_["sell"] >= 0 else np.nan
                        rows.append((j, T, T, d_["sell"], P_, g_, d_["typ"], False, P_ * (1 + g_) if d_["sell"] >= 0 else np.nan))
                    continue
                ev = r[cfg["src"]]
                for q in range(len(ev["T"])):
                    T = int(ev["T"][q]); P_ = float(ev["P"][q]); g_ = float(ev["R"][q]); ty = int(ev["typ"][q])
                    ent = T + 1 if cfg["src"] == "D4S2" else T
                    px = P_ * (1 + g_) if ty != 5 else np.nan
                    if cfg["slip"]:
                        epx = P_ * (1 + SLIP); gx = px * (1 - SLIP) / epx - 1.0 if ty != 5 else np.nan
                    else:
                        epx = P_; gx = g_
                    rows.append((j, T, ent, int(ev["sell"][q]) if ty != 5 else -1, epx, gx, ty, bool(ev["rehigh"][q]), px))
            rows.sort(key=lambda z: (z[2], S_[z[0]]))
            TR[arm] = {"j": np.array([z[0] for z in rows], np.int64), "T": np.array([z[1] for z in rows], np.int64),
                       "ent": np.array([z[2] for z in rows], np.int64), "ext": np.array([z[3] for z in rows], np.int64),
                       "ep": np.array([z[4] for z in rows], float), "g": np.array([z[5] for z in rows], float),
                       "typ": np.array([z[6] for z in rows], np.int8), "rehigh": np.array([z[7] for z in rows], bool),
                       "px": np.array([z[8] for z in rows], float)}
            bad_ = (TR[arm]["ext"] >= 0) & (TR[arm]["ext"] < TR[arm]["ent"])
            if bad_.any() or (np.isnan(TR[arm]["g"]) & (TR[arm]["ext"] >= 0)).any():
                raise SystemExit(f"⛔ {wn} {arm} 出場早於進場或 R 缺值（{int(bad_.sum())}）")
        J["閘"][wn]["候選事件數"] = {arm: int(len(v["ent"])) for arm, v in TR.items()}
        # 存 S2 候選事件（對帳用）
        Tm = TR["M"]
        ev_df = pd.DataFrame({"sid": [S_[j] for j in Tm["j"]], "T": dates[Tm["T"]], "買價": Tm["ep"], "出場日": [dates[x] if x >= 0 else "" for x in Tm["ext"]],
                              "出場種類": [TYPN[int(x)] for x in Tm["typ"]], "R": Tm["g"], "賣價": Tm["px"], "停損後20日內再突破": Tm["rehigh"]})
        with gzip.open(os.path.join(OUT, f"events_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            ev_df.to_csv(fh, index=False, float_format="%.17g")
        # 隨機池（陣列、依 (日, 代號) 排序）、操作負擔原料
        rank = np.empty(len(S_), np.int64); rank[np.argsort(np.array(S_))] = np.arange(len(S_))
        pt, pj, pe, px_, pg = [], [], [], [], []
        NEARM = np.zeros((n0, len(S_)), bool)
        for sid, r in res.items():
            j = ix[sid]; pp, Rr, Ty, Hh = r["pool"]
            pp = pp.astype(np.int64)
            pt.append(pp); pj.append(np.full(len(pp), j, np.int64)); pe.append(np.asarray(W["O"][j], float)[pp])
            px_.append(np.where(Ty != 5, pp + Hh.astype(np.int64), -1)); pg.append(np.where(Ty != 5, Rr, np.nan))
            NEARM[r["near"], j] = True
        pt, pj, pe, px_, pg = (np.concatenate(x) for x in (pt, pj, pe, px_, pg))
        od = np.lexsort((rank[pj], pt))
        RPa = {"t": pt[od], "j": pj[od], "ep": pe[od], "ext": px_[od], "g": pg[od]}
        RPa["rank"] = rank[RPa["j"]]
        RPa["start"] = np.searchsorted(RPa["t"], np.arange(n0 + 1), "left")
        if not (np.isfinite(RPa["ep"]).all() and (RPa["ep"] > 0).all()):
            raise SystemExit(f"⛔ {wn} 隨機池開盤缺值")
        RAWS[wn] = {"RP": RPa, "NEAR": NEARM}
        J["閘"][wn]["隨機池列數"] = int(len(pt))
        W["CM"] = CM
        TRS[wn] = TR
        del res
        # ── 組合（⛔ 先不讀任何報酬）
        SIMS[wn] = {}
        for arm, cfg in ARMS.items():
            SIMS[wn][arm] = simulate(TR[arm], n0, CM, Bc, Bo, cfg["mode"])
            log(f"[組合 {wn}] {arm} 買進 {len(SIMS[wn][arm]['buys'])} 筆（⛔ 尚未讀報酬）｜{time.time() - T0:.0f}s")
        # ── K9 引擎模式（主世界、主判事件）
        if wn == "主":
            tm = TR["M"]
            Cf = {}; Of = {}
            used = sorted(set(tm["j"].tolist()))
            for j in used:
                s = S_[j]; Cf[s] = np.r_[CM[j], CM[j][-1]]; Of[s] = np.r_[W["O"][j], np.nan].copy()
            for q in range(len(tm["ent"])):
                Of[S_[tm["j"][q]]][tm["ent"][q]] = tm["ep"][q]
            xp = np.where(tm["ext"] >= 0, tm["ext"], n0)
            gg = np.where(tm["ext"] >= 0, tm["g"], np.array([CM[j, n0 - 1] for j in tm["j"]]) / tm["ep"] - 1.0)
            sig = pd.DataFrame({"sid": [S_[j] for j in tm["j"]], "entry_pos": tm["ent"], "xpos_D": xp, "g_D": gg})
            o = R.simulate_mtm(sig, "D", NS, np.random.default_rng(SEED_ENG), Cf, Of, n0 + 1, return_equity=True, cash_mode="bench",
                               bench=W["benchP"], bench_cost=BC_SYM)
            me = simulate(tm, n0, CM, Bc, Bo, "engine", block_same=False, record=False)["eq"]
            f_ = int(o["first"])
            dmax = float(np.max(np.abs((me[f_ - 1:n0] / me[f_ - 1]) / np.asarray(o["equity"])[f_ - 1:n0] - 1.0)))
            J["閘"][wn]["K9 引擎模式 vs simulate_mtm 最大相對差"] = dmax
            log(f"[K9] 主世界主判事件：本支引擎模式 vs research11.simulate_mtm 逐日權益最大相對差 {dmax:.2e}")
            if dmax > 1e-9:
                raise SystemExit(f"⛔ K9 引擎模式不符 {dmax}")
    # ── 退化（先寫）
    DEG = {"規則": "seq325：探索段平均持股 ＜ 3 ⇒ 退化、不判；空位抱 0050 ⇒「現金 ＞ 30%」不適用（seq360 §一）", "格": {}}
    for wn, W in WS.items():
        for arm in ARMS:
            nh = SIMS[wn][arm]["nh"]
            for sg, (x, y) in W["segp"].items():
                DEG["格"][f"{wn}|{arm}|{sg}"] = {"平均持股": float(np.mean(nh[x:y + 1])), "退化": bool(np.mean(nh[x:y + 1]) < DEG_HOLD)}
    DEG["主判探索段退化"] = DEG["格"]["主|M|探索"]["退化"]
    DEG["寫入時間（台北）"] = now_tpe()
    json.dump(DEG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json（{DEG['寫入時間（台北）']}）｜主判探索 {DEG['格']['主|M|探索']}")
    J["退化"] = DEG
    J["時點"]["第一次讀報酬"] = now_tpe()
    # ── 報酬
    TAB = []; LAB = {}
    for wn, W in WS.items():
        cal = W["cal"]
        for arm, cfg in ARMS.items():
            S = SIMS[wn][arm]
            ps = seg_stats(W, S, TRS[wn][arm], arm)
            for sg, (x, y) in W["segp"].items():
                c_, m_ = metrics(W, S["eq"], x, y); b = RR.bench_row(cal, W["bench"], x, y + 1)
                lab = AS.label(c_, m_, b)
                LAB[(wn, arm, sg)] = lab
                TAB.append({"世界": wn, "臂": arm, "臂名": cfg["名"], "身分": ("判定" if cfg["judge"] and wn == "主" else ("早年（最多暫定用）" if cfg["judge"] else "描述（⛔ 不判）")),
                            "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_, "比值": AS.ratio(c_, m_),
                            "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]), "標籤": lab, **ps[sg]})
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "TurtleS2PF_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["主表"] = TAB
    log("[主表]\n" + TB[["世界", "臂", "段", "年化", "回落", "比值", "0050年化", "0050回落", "0050比值", "標籤", "平均持股", "換手每年", "成本合計每年", "買進筆"]].to_string())
    L = {"主判探索": LAB[("主", "M", "探索")], "主判確認": LAB[("主", "M", "確認")], "滑價探索": LAB[("主", "Mslip", "探索")],
         "滑價確認": LAB[("主", "Mslip", "確認")], "主判早年": LAB[("早年", "M", "早年")], "滑價早年(描述)": LAB[("早年", "Mslip", "早年")]}
    v = verdict(L)
    if DEG["主判探索段退化"]:
        v = f"退化、照 seq325 不判（標籤照報：{v}）"
    J["判語"] = {**L, "整件": v}
    J["描述標籤"] = {f"{wn}|{arm}|{sg}": LAB[(wn, arm, sg)] for (wn, arm, sg) in LAB if not ARMS[arm]["judge"]}
    log(f"[判語] {J['判語']}")
    # ── 存檔
    for wn, W in WS.items():
        cal = W["cal"]; dates = np.array([str(d.date()) for d in cal]); S_ = W["sids"]
        np.savez_compressed(os.path.join(OUT, f"eq_{wn}.npz"), Bc=W["Bc"], Bo=W["Bo"],
                            **{f"{arm}_{k}": SIMS[wn][arm][k] for arm in ARMS for k in ("eq", "hv", "u", "pend", "nh")})
        for arm in ARMS:
            S = SIMS[wn][arm]; T_ = TRS[wn][arm]
            sl = {q: (t, proc) for t, q, amt, proc in S["sells"]}
            df = pd.DataFrame({"sid": [S_[T_["j"][q]] for _, q, _ in S["buys"]], "T": [dates[T_["T"][q]] for _, q, _ in S["buys"]],
                               "買進日": [dates[t] for t, _, _ in S["buys"]], "買進日pos": [t for t, _, _ in S["buys"]],
                               "金額": [amt for _, _, amt in S["buys"]], "市值基準價": [T_["ep"][q] for _, q, _ in S["buys"]],
                               "R": [T_["g"][q] for _, q, _ in S["buys"]], "出場種類": [TYPN[int(T_["typ"][q])] for _, q, _ in S["buys"]],
                               "排程出場pos": [int(T_["ext"][q]) for _, q, _ in S["buys"]],
                               "賣出日": [dates[sl[q][0]] if q in sl else "" for _, q, _ in S["buys"]],
                               "入帳": [sl[q][1] if q in sl else np.nan for _, q, _ in S["buys"]],
                               "停損後20日內再突破": [bool(T_["rehigh"][q]) for _, q, _ in S["buys"]]})
            with gzip.open(os.path.join(OUT, f"trades_{wn}_{arm}.csv.gz"), "wt", encoding="utf-8") as fh:
                df.to_csv(fh, index=False, float_format="%.17g")
    # ── 操作負擔（K11）
    BUR = {}
    for wn, W in WS.items():
        NEARM = RAWS[wn]["NEAR"]; n0 = W["n0"]
        HELD = np.zeros_like(NEARM)
        S = SIMS[wn]["M"]; T_ = TRS[wn]["M"]
        sl = {q: t for t, q, amt, proc in S["sells"]}
        for t, q, amt in S["buys"]:
            e = sl.get(q, n0)
            HELD[t:e, T_["j"][q]] = True
        cnt = NEARM.sum(axis=1)
        heldprev = np.zeros_like(NEARM); heldprev[1:] = HELD[:-1]
        cntx = (NEARM & ~heldprev).sum(axis=1)
        pd.DataFrame({"日": [str(d.date()) for d in W["cal"]], "候選檔數": cnt, "扣已持有": cntx}).to_csv(
            os.path.join(OUT, f"burden_{wn}.csv.gz"), index=False, compression="gzip")
        for sg, (x, y) in W["segp"].items():
            z = cnt[x:y + 1]; zx = cntx[x:y + 1]
            BUR[f"{wn}|{sg}"] = {"平均": float(z.mean()), "中位": float(np.median(z)), "p90": float(np.percentile(z, 90)), "最多": int(z.max()),
                                 "最多日": str(W["cal"][x + int(np.argmax(z))].date()), "最少": int(z.min()),
                                 "扣已持有_平均": float(zx.mean()), "扣已持有_最多": int(zx.max())}
        log(f"[操作負擔 {wn}] {json.dumps({k: v for k, v in BUR.items() if k.startswith(wn)}, ensure_ascii=False)}")
    J["操作負擔"] = BUR
    # ── 隨機（K7）
    J["隨機進場"] = {}
    for wn, W in WS.items():
        S = SIMS[wn]["M"]
        byday = Counter(t for t, q, amt in S["buys"])
        _G[wn] = {"DAYS": sorted(byday.items()), "RP": RAWS[wn]["RP"], "sids": W["sids"], "n0": W["n0"], "CM": W["CM"],
                  "Bc": W["Bc"], "Bo": W["Bo"], "segp": W["segp"]}
        st_ = RAWS[wn]["RP"]["start"]
        empty = sum(1 for t, _ in _G[wn]["DAYS"] if st_[t + 1] == st_[t])
        with Pool(a.procs) as pool:
            RES = pool.map(rand_job, [(wn, i) for i in range(NRAND)], chunksize=4)
        RDF = pd.DataFrame(RES)
        RDF.to_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), index=False, float_format="%.10g")
        o = {}
        for sg in W["segp"]:
            z = TB[(TB["世界"] == wn) & (TB["臂"] == "M") & (TB["段"] == sg)].iloc[0]
            rr = RDF[f"{sg}_年化"] / RDF[f"{sg}_回落"].abs()
            o[sg] = {"主判 年化": float(z["年化"]), "主判 比值": float(z["比值"]), "隨機 年化中位": float(RDF[f"{sg}_年化"].median()),
                     "隨機 回落中位": float(RDF[f"{sg}_回落"].median()), "隨機 比值中位": float(rr.median()),
                     "p（隨機比值 ≥ 主判）": float((rr >= z["比值"]).mean()), "p（隨機年化 ≥ 主判）": float((RDF[f"{sg}_年化"] >= z["年化"]).mean()),
                     "隨機 買進筆中位": float(RDF["買進筆"].median()), "次數": int(len(RDF)), "母體空日": empty}
        J["隨機進場"][wn] = o
        log(f"[隨機 {wn}] {json.dumps(o, ensure_ascii=False)}")
    # ── 先驗
    J["先驗對照"] = {
        "① 主判探索、確認至少一段不合格（約六成）": {"探索": L["主判探索"], "確認": L["主判確認"], "成立": bool(L["主判探索"] == "不合格" or L["主判確認"] == "不合格")},
        "② 滑價版兩段都不合格（約六成五）": {"探索": L["滑價探索"], "確認": L["滑價確認"], "成立": bool(L["滑價探索"] == "不合格" and L["滑價確認"] == "不合格")},
        "③ D4 兩段都不合格（約七成五）": {"探索": LAB[("主", "D4", "探索")], "確認": LAB[("主", "D4", "確認")],
                                   "成立": bool(LAB[("主", "D4", "探索")] == "不合格" and LAB[("主", "D4", "確認")] == "不合格")}}
    log(f"[先驗] {json.dumps(J['先驗對照'], ensure_ascii=False)}")
    # ── 結果句
    sents = {}
    for wn, sgs in (("主", ("探索", "確認")), ("早年", ("早年",))):
        for sg in sgs:
            z = TB[(TB["世界"] == wn) & (TB["臂"] == "M") & (TB["段"] == sg)].iloc[0]
            zs = TB[(TB["世界"] == wn) & (TB["臂"] == "Mslip") & (TB["段"] == sg)].iloc[0]
            s = (f"海龜系統 2 組合層（10 檔、空位抱 0050）{sg}段：年化 {pct(z['年化'])}、最大回落 {pct(z['回落'])}（0050 {pct(z['0050年化'])}、{pct(z['0050回落'])}）⇒ {z['標籤']}；"
                 f"滑價每邊 +0.5% 版：年化 {pct(zs['年化'])}、回落 {pct(zs['回落'])} ⇒ {zs['標籤']}｜" + "；".join(SENT + (NOTE_EARLY if wn == "早年" else [])))
            sents[f"{wn}|{sg}"] = s
    J["結果句"] = sents
    J["N"] = {"本件": "N_組合 ＋1（判定 1 件；滑價版為可執行性條款、D4／D6／D7／D8 描述不計）"}
    J["耗時秒"] = round(time.time() - T0); J["時點"]["完成"] = now_tpe()
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    json.dump(J, open(os.path.join(OUT, "TurtleS2PF.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


# ═════════════ 補充描述（⛔ 不判；正式跑後、看過主表後才加，見 S 標）═════════════
SUPP_DOC = """S 標（2026-10-18 11:40 後追加；⛔ 看過正式跑主表之後才寫 ⇒ 全部只描述、不改判語）：
 S1 發現：正式跑主判買進中約一半金額 ＜ 前日淨值÷10（主世界 1367 筆中 721 筆 ＜ 0.99 槽、174 筆 ＜ 0.5 槽），主因之一是 K2「當天個股賣出的現金要隔天才回 0050、
    不能撥當天新部位」⇒ 同日先出後進時新部位只拿得到剩下的 0050；且一旦撥款用盡（金額 ≤ 1e−9 停止）兩臂的抽籤路徑就分岔
    ⇒ 滑價版與主判買到不同股票（確認段滑價版反而年化較高即此原因）。
 S2 另一讀法 K2′（描述）：當天賣出的現金先撥當天新部位、不足才賣 0050（＝ 登錄「每檔買進時投入當時淨值 1/10」字面較貼近的另一讀法）；主判、滑價各跑一次（種子 1000）。
 S3 抽籤種子敏感度（描述）：K2 與 K2′ 各以種子 1～100 重跑主判與滑價（同種子成對），報各段 年化、比值 的分位數與「合格」比例、滑價−主判 成對差。
 S4 對帳：K2、種子 1000 重跑 ⇒ 與正式跑 eq npz 逐位元相同（同一支 simulate、同一批事件，事件從 events_<世界>.csv.gz 讀回）。"""
SEEDS = list(range(1, 101))


def supp_job(a):
    wn, arm, fp, seed = a
    G = _G[wn]; S = simulate(G["TR"][arm], G["n0"], G["CM"], G["Bc"], G["Bo"], "main", seed=seed, record=True, fund_pend=fp)
    row = {"世界": wn, "臂": arm, "讀法": "K2′" if fp else "K2", "種子": seed, "買進筆": len(S["buys"])}
    eq = S["eq"]
    under = [amt / (eq[t - 1] / NS) for t, q, amt in S["buys"]]
    row["金額＜0.5槽筆數"] = int(sum(u < 0.5 for u in under))
    for sg, (x, y) in G["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, 0, G["n0"], x, y)
        b = G["bench"][sg]
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_); row[f"{sg}_標籤"] = AS.label(c_, m_, b)
        row[f"{sg}_平均持股"] = float(np.mean(S["nh"][x:y + 1]))
    if seed == SEED_ENG:
        row["_eq"] = eq
    return row


def supp(a, log):
    T0 = time.time(); J = {"說明": SUPP_DOC, "時點": now_tpe()}
    ROWS = []
    for wn in ("主", "早年"):
        W = AS.load_world(wn, log); cal = W["cal"]; n0 = W["n0"]
        D.DATA = W["data"]
        bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float)
        Bc = np.asarray(W["bench"], float); Bo = bo.copy()
        for t in np.flatnonzero(~(np.isfinite(bo) & (bo > 0))):
            Bo[t] = Bc[t - 1] if t > 0 else Bc[0]
        CM = pd.DataFrame(np.asarray(W["C"], float)).ffill(axis=1).to_numpy(float)
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)   # 全讀字串、用 Python float() 精確還原
        dpos = {str(d.date()): q for q, d in enumerate(cal)}
        j = np.array([W["ix"][s] for s in ev["sid"]]); T = np.array([dpos[d] for d in ev["T"]])
        ext = np.array([dpos[d] if d else -1 for d in ev["出場日"]]); P_ = np.array([float(x) for x in ev["買價"]])
        R_ = np.array([float(x) if x else np.nan for x in ev["R"]]); px = np.array([float(x) if x else np.nan for x in ev["賣價"]])
        TR = {"M": {"j": j, "ent": T, "ext": ext, "ep": P_, "g": R_},
              "Mslip": {"j": j, "ent": T, "ext": ext, "ep": P_ * (1 + SLIP), "g": px * (1 - SLIP) / (P_ * (1 + SLIP)) - 1.0}}
        bench = {sg: RR.bench_row(cal, W["bench"], x, y + 1) for sg, (x, y) in W["segp"].items()}
        _G[wn] = {"TR": TR, "n0": n0, "CM": CM, "Bc": Bc, "Bo": Bo, "segp": W["segp"], "bench": bench}
        jobs = [(wn, arm, fp, sd) for arm in ("M", "Mslip") for fp in (False, True) for sd in [SEED_ENG] + SEEDS]
        with Pool(a.procs) as pool:
            res = pool.map(supp_job, jobs, chunksize=4)
        Z = np.load(os.path.join(OUT, f"eq_{wn}.npz"))
        for r in res:
            if r["種子"] == SEED_ENG and r["讀法"] == "K2":
                d = float(np.max(np.abs(r["_eq"] - Z[f"{r['臂']}_eq"])))
                J[f"S4 {wn} {r['臂']} K2 種子1000 重跑 vs 正式跑 最大差"] = d
                log(f"[S4] {wn} {r['臂']}：重跑 vs 正式跑 eq 最大差 {d:.1e}")
                if d != 0.0:
                    raise SystemExit("⛔ S4 重跑不逐位元相同")
            r.pop("_eq", None)
        ROWS += res
        log(f"[補充 {wn}] {len(res)} 次｜{time.time() - T0:.0f}s")
    df = pd.DataFrame(ROWS)
    df.to_csv(os.path.join(OUT, "supp_seeds.csv.gz"), index=False, float_format="%.10g", compression="gzip")
    S2 = {}; S3 = {}
    for wn, sgs in (("主", ("探索", "確認")), ("早年", ("早年",))):
        for rd in ("K2", "K2′"):
            for arm in ("M", "Mslip"):
                z = df[(df["世界"] == wn) & (df["讀法"] == rd) & (df["臂"] == arm)]
                z0 = z[z["種子"] == SEED_ENG].iloc[0]; zs = z[z["種子"] != SEED_ENG]
                for sg in sgs:
                    rr = zs[f"{sg}_年化"] / zs[f"{sg}_回落"].abs()
                    S2[f"{wn}|{rd}|{arm}|{sg}（種子1000）"] = {"年化": float(z0[f"{sg}_年化"]), "回落": float(z0[f"{sg}_回落"]), "標籤": z0[f"{sg}_標籤"],
                                                         "平均持股": float(z0[f"{sg}_平均持股"]), "買進筆(全世界)": int(z0["買進筆"]),
                                                         "金額＜0.5槽筆數(全世界)": int(z0["金額＜0.5槽筆數"])}
                    S3[f"{wn}|{rd}|{arm}|{sg}（種子1～100）"] = {
                        "年化 p10／中位／p90": [float(np.percentile(zs[f"{sg}_年化"], q)) for q in (10, 50, 90)],
                        "比值 中位": float(rr.median()), "合格比例": float((zs[f"{sg}_標籤"] == "合格").mean()),
                        "另列比例": float((zs[f"{sg}_標籤"] == "另列").mean()), "不合格比例": float((zs[f"{sg}_標籤"] == "不合格").mean())}
                if arm == "Mslip":
                    zm = df[(df["世界"] == wn) & (df["讀法"] == rd) & (df["臂"] == "M") & (df["種子"] != SEED_ENG)].set_index("種子")
                    zz = zs.set_index("種子")
                    for sg in sgs:
                        dd = zz[f"{sg}_年化"] - zm[f"{sg}_年化"]
                        S3[f"{wn}|{rd}|滑價−主判 成對差|{sg}"] = {"年化差 中位": float(dd.median()), "年化差 p10／p90": [float(dd.quantile(.1)), float(dd.quantile(.9))],
                                                           "滑價較高的種子比例": float((dd > 0).mean())}
    J["S2 另一讀法 K2′（種子1000）與 K2 對照"] = S2; J["S3 抽籤種子敏感度"] = S3
    J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "TurtleS2PF_supp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[補充] " + json.dumps({k: (v["標籤"], round(v["年化"], 4)) for k, v in S2.items()}, ensure_ascii=False))
    log("[補充 種子] " + json.dumps(S3, ensure_ascii=False, default=float))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--supp", action="store_true", help="補充描述（S 標，⛔ 不判）：另一讀法 K2′、抽籤種子敏感度；需先有正式跑結果")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.supp:
        log = RA.log_to(os.path.join(OUT, "supp.log")); supp(a, log); return
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

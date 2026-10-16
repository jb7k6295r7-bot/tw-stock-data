# -*- coding: utf-8 -*-
"""PREREG看空型態出場 seq1（台股策略線登錄 sha d8681fd9d1e3bf72，2026-10-17 01:40；裁定 seq356、seq357、seq358 發號 N_組合 ＋1）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBearExit [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBearExit_check [--procs 3]

⭐ 讀法寫死：TIME（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本件數字
   看過的：登錄全文 seq1、裁定 seq356／357／358；既有程式 patterns_all（偵測器）、researchPatAll／researchPatAll_freq（呼叫法）、exit_signal（MA20 連 3 日）、
   researchExit5（重播管線）、researchAddOn（世界、壞根、t2_first）；⚠ 回測線看過營量 v1／營飆 v1 各段年化與回落、出場五法與跌破 MA20 類舊結果、
   型態全量單筆層結果（S09、S27 H20 反方向）；⛔ 沒看過本件任何輸出

═══ 讀法（Y 標；登錄沒寫清楚、執行者補的都在這裡）═══
 Y0 判定（登錄 §三，事前寫死）：營量、營飆各自判 X0 對原策略（A）；段 ＝ 探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24；
    段「有效」⇔ X0 年化 ≥ A 年化 且 X0 年化÷|回落| ≥ A 的同比（「不降」＝ ≥；營飆 ＝ 200 顆中位：年化中位、回落中位、比值 ＝ 年化中位÷|回落中位|，同 researchExit5）；
    兩段有效 ⇒「有效」；一段 ⇒「方向不一致」；兩段都不是 ⇒「無效」。
    先後：① 持股觸發次數 ＜ 30 ⇒「樣本不足、測不出」（⛔ 不硬判）② 退化（Y8）⇒「退化、不判」（seq325；另附登錄字面結果供參）③ 其餘照上。
    持股觸發次數 ＝ X0 回測實際買進（買進日在主窗）的持股中、真的被看空型態提早賣掉（Y3 觸發、⛔ 不含壞根強制）的筆數，兩型態合計；
    營飆 ＝ 200 顆各自筆數的中位（一個組合實際碰到的次數；去重數另報）；營飆 r0（種子 1000）同式並報、逐顆「兩段都有效」比例並報。
 Y1 世界、引擎（⛔ 不改）：同 researchExit5 X1——~/addonwork/world_{主,早年}.pkl；營量 v1 ＝ SIG[無閘]、H60、20 槽、relvol（7000＋0）；
    營飆 v1 ＝ SIG[閘]、H120、10 槽、抽籤 default_rng(1000＋r)，r＝0～199；停止交易強制出場開；改出場一律走 held_map（價格鍵「代號#進場位置」、
    合成收盤、xpos ＝ 最後一個部分出場那天、g ＝ Σ 權重×出場價÷進場價 −1）；整筆賣 ⇒ xpos ＝ 賣出那天開盤 ⇒ 名額當天就照原規則補候選。
    閘①：IG.eng 直接跑的權益 sha ＝ resultsYL_integrate/seeds.csv.gz；閘②：A 走 held_map 的權益與 IG.eng 逐位元相同。
 Y2 型態（登錄 §一、seq357 §一）：⭐ 逐字用 patterns_all.py（PREREG型態全量 seq3 sha b7b4a05af0341797 的偵測器，⛔ 不改、不重調）：
    S09 下降三角_向下 ＝ PA.detect_lines、S27 V型反轉 ＝ PA.detect_v；輸入 ＝ researchPatAll_freq.one_stock 同一套：data.load_stock 還原 OHLCV、
    有效 K 棒 ＝ 還原收盤非缺值、r60 ＝ PA._rN(c, 60)；同一 T 多筆 ⇒ 照 PA.detect_all 去重（sorted set、留第一筆）；位置換回交易日曆（＝ detect_calendar）。
    ⛔ 只呼叫這兩個變體需要的兩支子函式（其餘 94 變體不影響這兩個的輸出）；閘：主世界（同快照 edc6f）候選股窗內事件（T ∈ [2017-03-02, 窗尾−20]）
    與已提交的 resultsPatAll/events_S09／S27 逐筆 (sid, T, first) 比，不同 ⇒ 中止。原始偵測（⛔ 不套型態全量的 20 日合併、剔除——那是單筆層用的）。
    訊號日 ＝ T（突破確認那根收盤）。早年世界同一支偵測器、早年資料。
 Y3 時序（同 researchExit5 X2）：判斷日 d ∈ [e, X上限−1]（e ＝ 買進日；正常列 X上限 ＝ 正式出場根 xf；資料尾補回列 ＝ 資料尾；停止交易 L ⇒ min(·, L)）；
    d 當天有 S09 或 S27 事件 ⇒ 動作 X ＝ d 之後第一根「有效 K 棒（load_bars traded）且開盤有限 ＞ 0」的開盤；第一個成立日沒有可賣開盤（X 不存在或 ＞ X上限）
    ⇒ 該筆不賣（照正式）；每筆只動作一次（之後再出現型態不再動作）。
 Y4 壞根（seq335，同 researchExit5 X3）：主世界 bad_main.pkl；早年 bad_early.pkl ∪ R8 恢復日 ∪ reduce_v2（上市、上櫃偵測、未解釋 22 筆）——AO.market；
    任何部分的出場日 ≥ 進場後第一個壞根 kb ⇒ 改成 kb 前最後一根有效 K 棒收盤強制賣（筆數照報）。
 Y5 格：X0 兩型態任一整筆賣；X1 只 S09；X2 只 S27；X3 X0 觸發時賣一半（另一半照原規則，賣掉一半價值凍結在賣價、名額到剩下一半出清才釋出——同 researchExit5 賣一半）；
    X4 X0 觸發時整筆賣、⭐ 賣得的錢留現金到「下次換股」＝ 該筆原排程出場日（H60／H120 的 xf）才釋出名額（＝ 價值凍結在賣價、xpos ＝ xf；
    權重 0 的原出場那一塊只用來佔名額）；X5 參考臂 ＝ exit_signal.raw_signals(rule＝"d3")["乙"]（PREREG出場訊號 描述臂 a「連 3 日收在線下」：
    收盤跌破 MA20 那根 t、t＋1、t＋2 收盤都 ＜ 各自 MA20 ⇒ 訊號日 t＋2；有效 K 棒 ＜ 80 根不產生，同該件 MIN_BARS）整筆賣。
 Y6 隨機日賣（必報；描述 p）：主世界；每一次 k（k＝0～199）：原策略 A 同一顆（營量 r0；營飆 ⓐ 配對：第 k 次用種子 k、ⓑ r0：全部用種子 1000）
    在主窗買進的持股，依買進年 y 分組；n_y ＝ 該組中 X0 會觸發（rows X0_trig＝1）的筆數；從該組不放回抽 n_y 筆、每筆在
    「判斷日 [e, X上限−1] 中有效 K 棒且之後有可賣開盤（≤ X上限）」的日子均勻抽一天 d ⇒ X ＝ 次一有效開盤整筆賣（壞根照 Y4）、空格照原規則補；
    種子 default_rng([20261017, 世界, 策略, 模式, k])。統計量 Δ ＝ 臂 − A（同種子）的 年化、比值；營量 p ＝ #{Δ隨機 ≥ ΔX0}/200；
    營飆 ⓐ p ＝ #{Δ隨機_k ≥ median_k ΔX0_k}/200、ⓑ p ＝ #{Δ隨機_k ≥ ΔX0_r0}/200。p 小 ⇒ 型態賣點比隨機日賣好。早年 ⛔ 不跑（描述段）。
 Y7 賣錯率（必報）：唯一觸發列（該窗買進、X0／X1／X2／X5 各自；營飆 200 顆去重）：賣後 H〈n〉（n＝20、60；X＋n−1 根交易日曆收盤，ffill）＞ 賣價（X 開盤）
    ⇒「再漲」；[X, X＋n−1] 有效 K 棒最高收盤 ＞ [e, d] 有效 K 棒最高收盤 ⇒「再創新高」（同 researchExit5 post60，壞根截斷）；窗不滿 ⇒ 不計、
    「再漲」遇壞根 ⇒ 不計；另報隨機日賣（Y6 營量 200 次＋營飆 ⓐ 合併、去重）與原出場（(xf, xf＋n] 比持有期最高）對照。
    賣出點位置：同 researchAddOn_truetop_peak（t ＝ truetopT.anchor_pit(c, d, e)、P ＝ 起漲點起到第一次從高點回落 30% 為止最高收盤）；
    ⭐ 措辭照 seq343：本件賣出訊號屬「真頂訊號（多半在最高點之前）」式，⛔ 不稱最高點、頂部；只報 d−P 分佈與 d 在 P 之前比例。
 Y8 退化（seq325：先寫 degeneracy.json 附台北時間，再算任何報酬）：同 researchExit5 X8——探索段（營飆 200 顆中位）平均持股 ＜ 3 或 現金比例 ＞ 30% ⇒ 退化；
    現金比例 ＝ 1 − 段內平均（持股市值 − 凍結的錢）÷ 權益（X3 的一半、X4 的整筆凍結都算現金）；原策略同段已達同一條 ⇒ 該條不適用。
 Y9 大盤版（描述）：M1 加權指數（主）——⚠ 庫裡加權指數只有收盤與成交量（~/us-stock-data twse_taiex.csv；tw-stock-data history/market_index.csv 只有收盤），
    ⛔ 沒有高低價 ⇒ S09（要擺動高低點）逐字算不出：M1 ＝ 只用 S27（收盤＋volume_shares 成交股數，逐字）；另列「M1替代」＝ S09 以收盤代高低（⛔ 非逐字，只描述）∪ S27；
    M2 ＝ 0050 本身（還原 OHLCV、逐字兩型態）。規則：持有 0050 時型態事件 T ⇒ 0050 次一有效開盤全賣（成本 0.1425%＋0.1%）；空手時每天收盤看
    訊號序列收盤 ≥ 「突破前收盤」（＝ T 前一根有效 K 棒收盤）⇒ 次一有效開盤買回（0.1425%）；空手期間新事件不理、ref 不更新。
    另一讀法（S27 的「突破前收盤」低於 T 收盤、幾乎隔天就買回）：ref ＝ T 收盤 ⇒ 並列描述。對照 ＝ 一直抱 0050（還原收盤、不含成本，同 0050 判準）。
 Y10 必報組合欄（登錄 §四）：年化、最大回落、比值、換手（每年買進金額÷段內平均權益）、成本／年（換手×0.585%）、平均持股、現金比例；
    停用條件（seq341，⛔ 不改門檻）同時運作的級別變化 ＝ researchAddOn.t2_first（月底 D；營量 −34.4%／−27.5%，營飆 −56.1%／−44.9%）原 vs 臂。
 Y11 觸發逐年 ＝ 依訊號日 d 的曆年（唯一觸發列）；型態別：只 S09、只 S27、同日兩者。
 結果句必附：SENT；早年附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋上櫃版面註。
輸出 backtest/resultsBearExit/：degeneracy.json（先寫）、BearExit.json、BearExit_main.csv、BearExit_market.csv、seeds.csv.gz、rand.csv.gz、
     rows_{世界}_{策略}.csv.gz、events_{世界}.csv.gz、run.log；大檔 ~/bearexitwork/
── 事後註（跑完後補的註解；計算一字未改）──
 ① TIME 字串「02:20」是寫檔時預填的估計值；實際寫死在 02:05 煙霧測試開跑之前（BearExit.json「讀法寫死」欄照原字串，以本註為準）。
 ② 02:05 跑過一次 3 顆煙霧測試（BX_QUICK，輸出 /tmp/bx_quick，數字不是本件結果；⚠ 營量只有 r0 一條 ⇒ 煙霧測試已含營量完整數字，照記）；
    煙霧測試之後本檔 ⛔ 沒有改任何計算，02:12 正式開跑；查核檔在煙霧後修了自己的一處（S09 兩點同價時 np.polyfit 的 1e−16 雜訊 ⇒ 改中心化正規方程）。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as AO                    # noqa: E402
from backtest import researchExit5 as EX5                   # noqa: E402  只用純函式（stock_pack、first_sale、finalize、tk、keyed、bars_job）
from backtest import patterns_all as PA                     # noqa: E402  ⛔ 只 import
from backtest import exit_signal as XS                      # noqa: E402  ⛔ 只 import

TIME = "2026-10-17 02:20（台北）"
REG_SHA = "d8681fd9d1e3bf72"
PAT_SHA = "b7b4a05af0341797"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsBearExit"
WORK = os.path.expanduser("~/bearexitwork")
NSEED, NRAND = 200, 200
if os.environ.get("BX_QUICK"):                                   # 煙霧測試（不是交件）
    NSEED, NRAND, OUT, WORK = 3, 3, "/tmp/bx_quick", "/tmp/bx_quick/work"
COST = R.COST
STR = EX5.STR
VARS = ("A", "X0", "X1", "X2", "X3", "X4", "X5")
ARMS = VARS[1:]
VNAME = {"A": "原策略", "X0": "主判 兩型態任一 整筆賣、補候選", "X1": "只下降三角向下", "X2": "只V型反轉", "X3": "賣一半",
         "X4": "整筆賣、留現金到原出場日（不補）", "X5": "參考臂 跌破MA20連3日"}
FRZ = {"X3": 0.5, "X4": 1.0}
SEGS = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
T2 = EX5.T2
DEG_HOLD, DEG_CASH = 3.0, 0.30
MINTRIG = 30
RSEED = 20261017
WID = {"主": 0, "早年": 1}
SID_ = {"營量": 0, "營飆": 1}
C50_SELL, C50_BUY = 0.001425 + 0.001, 0.001425
TAIEX = os.path.expanduser("~/us-stock-data/data/macro/twse_taiex.csv")
PATDIR = "backtest/resultsPatAll"
PATF = {"S09": "events_S09_下降三角_向下.csv.gz", "S27": "events_S27_V型反轉.csv.gz"}
SENT = ["營量、營飆已看過結果（出場五法、跌破 MA20 類提早賣）；本件出場規則是新的、沒看過輸出", "買進照正式規則，只換賣法；停用條件照舊、⛔ 不改門檻"]
NOTE_EARLY = EX5.NOTE_EARLY
WORDING = "賣出點措辭照 seq343：看空型態訊號屬「真頂訊號（多半在最高點之前）」式；⛔ 不稱最高點、頂部"
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f) and os.path.basename(f).startswith("登錄全文")]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    if PAT_SHA not in open("backtest/researchPatAll.py", encoding="utf-8").read():
        raise SystemExit(f"⛔ researchPatAll.py 沒有型態全量 seq3 sha {PAT_SHA}")
    return os.path.basename(fs[0])


def seeds_of(sn):
    return [0] if sn == "營量" else list(range(NSEED))


# ═════════════ 型態偵測（Y2；⛔ 只呼叫 patterns_all）═════════════
def detect(h, l, c, v):
    """日曆陣列 ⇒ {"S09": (T, first), "S27": (T, first), "MA": T}（日曆位置）。"""
    c = np.asarray(c, float)
    bars = np.flatnonzero(np.isfinite(c))
    out = {}
    if len(bars) == 0:
        z = np.zeros(0, np.int64)
        return {"S09": (z, z), "S27": (z, z), "MA": z}
    hb, lb, cb, vb = (np.asarray(x, float)[bars] for x in (h, l, c, v))
    r60 = PA._rN(cb, PA.R60)
    S = {}
    S.update(PA.detect_lines(hb, lb, cb, r60))
    S.update(PA.detect_v(cb, vb))
    for vid in ("S09", "S27"):
        ev, seen = [], set()
        for e in sorted(set(S[vid])):                       # PA.detect_all 同式去重
            if e[0] not in seen:
                seen.add(e[0]); ev.append(e)
        T = np.array([x[0] for x in ev], dtype=np.int64); f = np.array([x[1] for x in ev], dtype=np.int64)
        out[vid] = (bars[T] if len(T) else T, bars[f] if len(f) else f)
    sg = XS.raw_signals(cb, lb, rule="d3")["乙"]
    ii = np.flatnonzero(sg); ii = ii[ii + 1 >= XS.MIN_BARS]
    out["MA"] = bars[ii] if len(ii) else ii.astype(np.int64)
    return out


def det_job(a):
    sid, mk = a
    D.DATA = _G["data"]
    st = D.load_stock(sid, mk, _G["cal"])
    if st is None:
        return sid, None, np.nan
    df = st.df
    h, l, c, v = (df[k].to_numpy(float) for k in ("high", "low", "close", "volume"))
    cw = np.asarray(_G["closes"][sid], float)[:len(c)]
    ok = np.isfinite(c) & np.isfinite(cw)
    md = float(np.max(np.abs(c[ok] / cw[ok] - 1.0))) if ok.any() else 0.0
    return sid, detect(h, l, c, v), md


def patall_gate(DET, cal, w0, w1, log):
    """主世界：候選股窗內事件 vs 已提交 resultsPatAll 事件檔（逐筆 sid、T、first）。宇宙 ＝ 96 個事件檔出現過的 sid（gate3）。"""
    uni = set()
    for f in glob.glob(os.path.join(PATDIR, "events_*.csv.gz")):
        uni |= set(pd.read_csv(f, dtype={"sid": str}, usecols=["sid"])["sid"])
    out = {"型態全量事件檔宇宙檔數": len(uni), "候選股在宇宙內": int(sum(s in uni for s in DET)), "候選股不在宇宙內": sorted(s for s in DET if s not in uni)}
    for vid, fn in PATF.items():
        E = pd.read_csv(os.path.join(PATDIR, fn), dtype={"sid": str, "T": str, "first": str})
        E = E[E["sid"].isin(DET)]
        ref = set(zip(E["sid"], E["T"], E["first"]))
        mine = set()
        for s, d in DET.items():
            if s not in uni:
                continue
            T, f = d[vid]
            m = (T >= w0) & (T <= w1 - 20)
            mine |= {(s, str(cal[t].date()), str(cal[ff].date())) for t, ff in zip(T[m], f[m])}
        out[vid] = {"事件檔筆數（候選股）": len(ref), "本支筆數": len(mine), "只在事件檔": len(ref - mine), "只在本支": len(mine - ref)}
    log(f"[型態全量事件檔閘] {out}")
    if any(out[v]["只在事件檔"] or out[v]["只在本支"] for v in PATF):
        raise SystemExit("⛔ 偵測與型態全量事件檔不同")
    return out


# ═════════════ 逐列出場 ═════════════
def row_variants(pk, DV, e, xf, gf, bp, L, n0):
    c = pk["c"]; o = pk["o"]; bar = pk["bar"]
    Xcap = xf if xf < n0 else n0 - 1
    if L is not None:
        Xcap = min(Xcap, L)
    pf = ("close", xf, bp * (1 + gf), xf) if xf < n0 else ("end", n0, bp * (1 + gf), n0 - 1)
    kb = int(pk["nbad"][e + 1]) if e + 1 < len(pk["nbad"]) else -1
    pbad = None
    if kb >= 0:
        vb = np.flatnonzero(bar[e:min(kb, n0)])
        db = e + int(vb[-1]) if len(vb) else e
        pbad = ("close", db, float(c[db]), db)

    def fix(p):
        if pbad is None:
            return p, 0
        day = p[1] if p[0] != "end" else n0
        if day >= kb:
            return pbad, 1
        return p, 0
    hi = min(Xcap - 1, n0 - 1)
    dStd = np.arange(e, hi + 1) if hi >= e else np.zeros(0, np.int64)

    def mask(pos):
        m = np.zeros(n0, bool); pos = np.asarray(pos, np.int64); pos = pos[(pos >= 0) & (pos < n0)]; m[pos] = True
        return m
    m9, m27, mMA = mask(DV["S09"][0]), mask(DV["S27"][0]), mask(DV["MA"])

    def sale(cond, mode="whole"):
        cand = dStd[cond[dStd]] if len(dStd) else dStd
        d, X = EX5.first_sale(cand, pk, Xcap)
        if X is not None:
            p = ("open", X, float(o[X]), X - 1)
            if mode == "whole":
                return [(1.0, p)], d, X
            if mode == "keep":
                return [(1.0, p), (0.0, pf)], d, X
            return [(0.5, p), (0.5, pf)], d, X
        return ([(0.5, pf), (0.5, pf)] if mode == "half" else [(1.0, pf)]), d, None
    any_ = m9 | m27
    parts = {"A": ([(1.0, pf)], None, None), "X0": sale(any_), "X1": sale(m9), "X2": sale(m27), "X3": sale(any_, "half"),
             "X4": sale(any_, "keep"), "X5": sale(mMA)}
    out = {}
    for v, (pl, d, X) in parts.items():
        fx = [(w, fix(p)) for w, p in pl]
        bd = int(any(f[1] for _, f in fx)); pl2 = [(w, f[0]) for w, f in fx]
        trig = int(X is not None and any(p[0] == "open" and p[1] == X for _, p in pl2))
        out[v] = {"parts": pl2, "d": d, "X": X if trig else None, "trig": trig, "bad": bd}
    d0 = out["X0"]["d"]
    typ = "" if d0 is None else ("兩者" if (m9[d0] and m27[d0]) else ("S09" if m9[d0] else "S27"))
    # 隨機日賣可抽日（Y6）
    if len(dStd):
        nx = pk["nxt"][dStd + 1]
        el = dStd[bar[dStd] & (nx >= 0) & (nx <= Xcap)]
    else:
        el = dStd
    return out, {"Xcap": Xcap, "kb": kb, "typ": typ, "elig": el, "pf": pf, "fix": fix}


def build_rows(wn, sn, W, PK, DET, n0, log):
    S = STR[sn]; H = S["H"]; sig = W["SIG"][S["G"]]
    sig = sig[sig[f"xpos_H{H}"] >= 0]
    NP = W["NP"]
    rows = []; SC = {v: {} for v in VARS}; ELIG = {}
    for r in sig.itertuples(index=False):
        sid = r.sid; e = int(r.entry_pos); xf = int(getattr(r, f"xpos_H{H}")); gf = float(getattr(r, f"g_H{H}"))
        pk = PK[sid]
        bp = float(W["opens"][sid][e])
        if not np.isfinite(bp) or bp <= 0:
            bp = float(W["closes"][sid][e])
        L = W["SF"].get(sid)
        V, info = row_variants(pk, DET[sid], e, xf, gf, bp, L, n0)
        key = f"{sid}#{e}"
        ELIG[key] = info["elig"]
        base = {"key": key, "sid": sid, "e": e, "xf": xf, "gf": gf, "bp": bp, "L": -1 if L is None else L, "kb": info["kb"], "Xcap": info["Xcap"],
                "買進年": int(W["cal"][e].year), "X0_type": info["typ"], "可抽日數": int(len(info["elig"]))}
        orig = W["closes"][sid]
        for v in VARS:
            rec = V[v]
            if v == "A":
                xa, ga, sfa = xf, gf, 0
                if L is not None and xf > L + 1:
                    xa, ga, sfa = L + 1, float(orig[L]) / bp - 1.0, 1
                base.update({"A_xpos": xf, "A_g": gf, "A_xe": xa, "A_ge": ga, "A_sf": sfa, "A_bad": rec["bad"]})
                SC[v][key] = orig
                continue
            if (not rec["trig"]) and (not rec["bad"]):
                xp, g, sf, xe, ge = xf, gf, base["A_sf"], base["A_xe"], base["A_ge"]; SC[v][key] = orig
            else:
                xp, g, Sc, sf, xe, ge = EX5.finalize(rec, pk, bp, n0, NP, L, orig)
                SC[v][key] = Sc
            p1 = rec["parts"][0][1]
            base.update({f"{v}_xpos": xp, f"{v}_g": g, f"{v}_xe": xe, f"{v}_ge": ge, f"{v}_sf": sf, f"{v}_trig": rec["trig"], f"{v}_bad": rec["bad"],
                         f"{v}_d": -1 if rec["d"] is None else int(rec["d"]), f"{v}_X": -1 if rec["X"] is None else int(rec["X"]),
                         f"{v}_px1": float(p1[2]) if rec["trig"] else np.nan})
        rows.append(base)
    T = pd.DataFrame(rows)
    T.insert(0, "策略", sn); T.insert(0, "世界", wn)
    trg = {v: int(T[v + "_trig"].sum()) for v in ARMS}
    log(f"[逐列 {wn}·{sn}] {len(T)} 列｜觸發 {trg}｜X0 型態 {T.loc[T['X0_trig'] == 1, 'X0_type'].value_counts().to_dict()}｜壞根強制 "
        f"{ {v: int(T[v + '_bad'].sum()) for v in ARMS} }")
    return T, SC, ELIG


# ═════════════ 引擎 ═════════════
def run_engine(C, r):
    S = STR[C["sn"]]; au = []
    if C["sn"] == "營量":
        o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P1_SEED0 + r), C["cl"], C["op"], C["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=C["SF"], audit=au, held_map=C["hm"])
    else:
        o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P10_SEED0 + r), C["cl"], C["op"], C["NP"], return_equity=True,
                           stop_force=C["SF"], audit=au, held_map=C["hm"])
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    A = [(int(a["t"]), a["side"], a["sid"], float(a["amt"]), float(a["px"])) for a in au]
    return eq, hv, A, int(o["first"]), int(o["end"])


def job_run(r):
    C = _G["CUR"]
    eq, hv, A, f_, e_ = run_engine(C, r)
    return r, eq, f_, e_, pre_stats(C, eq, hv, A), A


def job_ig(a):
    wn, sn, r = a
    o, _ = IG.eng(_G["WS"][wn], STR[sn]["key"], r, audit=False)
    return wn, sn, r, np.asarray(o["equity"], float)


def pre_stats(C, eq, hv, A):
    """⛔ 不含任何報酬：持股數、現金（凍結算現金）、換手、持有天數、買進鍵。"""
    n = len(eq); cnt = np.zeros(n + 1); frz = np.zeros(n)
    RI = C["RI"]; w = FRZ.get(C["v"], 0.0)
    buys = {}
    for t, side, k, amt, px in A:
        cnt[t] += 1 if side == "buy" else -1
        if side == "buy":
            buys[k] = [t, amt, px, None]
        elif k in buys:
            buys[k][3] = t
    if w > 0:
        for k, (t, amt, px, ts) in buys.items():
            ri = RI.get(k)
            if ri is not None and ri["trig"] and ri["X"] >= 0:
                a_ = ri["X"]; b_ = ts if ts is not None else n
                if b_ > a_:
                    frz[a_:b_] += amt * w * ri["px1"] / px
    hold = np.cumsum(cnt)[:n]
    out = {}
    for sg, (x, y) in C["segp"].items():
        yrs = (y - x + 1) / 245.0
        bs = [(k, b) for k, b in buys.items() if x <= b[0] <= y]
        hd = [b[3] - b[0] for k, b in bs if b[3] is not None]
        out[sg] = {"持股": float(np.mean(hold[x:y + 1])), "現金": float(1.0 - np.mean((hv[x:y + 1] - frz[x:y + 1]) / eq[x:y + 1])),
                   "買進筆": len(bs), "換手每年": float(sum(b[1] for _, b in bs) / np.mean(eq[x:y + 1]) / yrs),
                   "持有天數": float(np.mean(hd)) if hd else np.nan, "買進鍵": [k for k, _ in bs]}
    return out


def base_inputs(W, sn):
    S = STR[sn]; H = S["H"]; sig = W["SIG"][S["G"]]
    s2 = sig[sig[f"xpos_H{H}"] >= 0].copy()
    k = [f"{s}#{e}" for s, e in zip(s2["sid"], s2["entry_pos"].astype(int))]
    hm = dict(zip(k, s2["sid"]))
    s2["sid"] = k
    cl = {**W["closes"], **{kk: W["closes"][hm[kk]] for kk in k}}
    op = {**W["opens"], **{kk: W["opens"][hm[kk]] for kk in k}}
    SFk = {**W["SF"], **{kk: W["SF"][hm[kk]] for kk in k if hm[kk] in W["SF"]}}
    return s2, cl, op, SFk, hm


def rand_job(k):
    B = _G["RB"]; sel = _G["RSEL"][k]
    H = STR[B["sn"]]["H"]
    s2 = B["sig"].copy()
    ix = {kk: i for i, kk in enumerate(s2["sid"])}
    xp = s2[f"xpos_H{H}"].to_numpy(np.int64).copy(); g = s2[f"g_H{H}"].to_numpy(float).copy()
    cl = dict(B["cl"])
    for key, (xpos, gg, Sc) in sel["ov"].items():
        i = ix[key]; xp[i] = xpos; g[i] = gg; cl[key] = Sc
    s2[f"xpos_H{H}"] = xp; s2[f"g_H{H}"] = g
    C = {"sn": B["sn"], "sig": s2, "cl": cl, "op": B["op"], "SF": B["SF"], "hm": B["hm"], "NP": B["NP"], "RI": {}, "v": "RND", "segp": B["segp"]}
    eq, hv, A, f_, e_ = run_engine(C, sel["seed"])
    pre = pre_stats(C, eq, hv, A)
    met = {}
    for sg, (x, y) in B["segp"].items():
        c_, m_, _ = RR.win_metrics(eq, f_, e_, x, y)
        met[sg] = (c_, m_, pre[sg]["持股"], pre[sg]["現金"])
    return k, met, IG.sha(eq)


# ═════════════ 彙總工具 ═════════════
def q3(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p10（後10%）": float(np.quantile(v, .1)), "p90（前10%）": float(np.quantile(v, .9)), "平均": float(v.mean())}


def ratio(c, m):
    return c / abs(m) if (m is not None and np.isfinite(m) and m != 0 and np.isfinite(c)) else np.nan


def notworse(ca, ma, co, mo):
    return bool(ca >= co and ratio(ca, ma) >= ratio(co, mo))


def post_stats(pk, X, d, e, n0, H):
    """⇒ (再漲, 再創新高)：Y7。"""
    c = pk["c"]; bar = pk["bar"]; o = pk["o"]
    if X is None or X < 0 or X + H - 1 > n0 - 1:
        return np.nan, np.nan
    kb = pk["nbad"][X + 1] if X + 1 < len(pk["nbad"]) else -1
    clean = kb < 0 or kb > X + H - 1
    rise = float(c[X + H - 1] > o[X]) if clean else np.nan
    hi = X + H - 1 if clean else kb - 1
    pi = np.arange(X, hi + 1); pi = pi[bar[pi]]
    hb = np.arange(e, d + 1); hb = hb[bar[hb]]
    if not len(pi) or not len(hb):
        return rise, np.nan
    return rise, float(c[pi].max() > c[hb].max())


def post_orig(pk, xf, e, n0, H):
    """原出場對照：(xf, xf＋H] 有效 K 棒最高收盤 ＞ [e, xf] 有效 K 棒最高收盤。"""
    c = pk["c"]; bar = pk["bar"]
    if xf + H > n0 - 1:
        return np.nan
    kb = pk["nbad"][xf + 1] if xf + 1 < len(pk["nbad"]) else -1
    hi = xf + H if (kb < 0 or kb > xf + H) else kb - 1
    pi = np.arange(xf + 1, hi + 1); pi = pi[bar[pi]]
    hb = np.arange(e, xf + 1); hb = hb[bar[hb]]
    if not len(pi) or not len(hb):
        return np.nan
    return float(c[pi].max() > c[hb].max())


def misrate(items, PK, n0):
    """items：[(sid, e, d, X)] ⇒ 賣錯率。"""
    out = {}
    for H in (20, 60):
        rs, nh = [], []
        for sid, e, d, X in items:
            a, b = post_stats(PK[sid], X, d, e, n0, H); rs.append(a); nh.append(b)
        rs = np.asarray(rs, float); nh = np.asarray(nh, float)
        out[f"賣後{H}日再漲"] = {"n": int(np.isfinite(rs).sum()), "比例": float(np.nanmean(rs)) if np.isfinite(rs).any() else None}
        out[f"賣後{H}日再創新高"] = {"n": int(np.isfinite(nh).sum()), "比例": float(np.nanmean(nh)) if np.isfinite(nh).any() else None}
    return out


# ═════════════ 大盤版（Y9）═════════════
def nxt_open(okop, n0):
    nx = np.full(n0 + 2, -1, np.int64)
    for p in range(n0 - 1, -1, -1):
        nx[p] = p if okop[p] else nx[p + 1]
    return nx


def msim(evT, refs, sigc, sigok, o50, c50f, nx50, t0, n0):
    """⇒ eq、空手旗標、賣出列。evT：事件 T（日曆位置，排序）；refs：對應買回門檻。"""
    eq = np.full(n0, np.nan); cashf = np.zeros(n0, bool)
    ev = {int(t): float(r) for t, r in zip(evT, refs)}
    inn = True; sh = 1.0 / c50f[t0]; cash = 0.0; ps = pb = None; ref = None; sold = None; trades = []
    for t in range(t0, n0):
        if ps is not None and t == ps:
            cash = sh * o50[t] * (1 - C50_SELL); sh = 0.0; inn = False; ps = None; sold = t; trades[-1]["X"] = t
        elif pb is not None and t == pb:
            sh = cash * (1 - C50_BUY) / o50[t]; cash = 0.0; inn = True; pb = None; trades[-1]["Y"] = t
        eq[t] = sh * c50f[t] + cash; cashf[t] = not inn
        if inn and ps is None and t > t0 and t in ev:
            x = int(nx50[t + 1]) if t + 1 < n0 else -1
            if x >= 0:
                ps = x; ref = ev[t]; trades.append({"T": t, "ref": ref, "X": None, "Y": None})
        elif (not inn) and pb is None and sold is not None and t >= sold and sigok[t] and np.isfinite(ref) and sigc[t] >= ref:
            x = int(nx50[t + 1]) if t + 1 < n0 else -1
            if x >= 0:
                pb = x
    return eq, cashf, trades


def market_arms(WS, log):
    tx = pd.read_csv(TAIEX, dtype={"date": str})
    tx["date"] = pd.to_datetime(tx["date"]); tx = tx.drop_duplicates("date").set_index("date").sort_index()
    RES = {}; ROWS = []
    for wn, W in WS.items():
        cal = W["cal"]; n0 = len(cal)
        D.DATA = W["data"]
        st = D.load_stock("0050", "twse", cal); df = st.df
        o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
        b = np.asarray(W["bench"], float)[:n0]; ok = np.isfinite(c)
        g50 = float(np.max(np.abs(c[ok] / b[ok] - 1.0)))
        if g50 > 1e-9:
            raise SystemExit(f"⛔ {wn} 0050 收盤 vs 世界 bench {g50}")
        c50f = pd.Series(c).ffill().to_numpy(float)
        okop = np.isfinite(c) & np.isfinite(o) & (o > 0)
        nx50 = nxt_open(okop, n0)
        t0 = int(np.flatnonzero(ok)[0])
        txa = tx.reindex(cal)
        tc = txa["close"].to_numpy(float); tv = txa["volume_shares"].to_numpy(float)
        tok = np.isfinite(tc)
        # 偵測
        d50 = detect(h, l, c, v)
        tb = np.flatnonzero(tok); r60 = PA._rN(tc[tb], PA.R60)
        tS27 = PA.detect_v(tc[tb], tv[tb])["S27"]
        tS09 = PA.detect_lines(tc[tb], tc[tb], tc[tb], r60)["S09"]

        def dedup(lst, bars):
            ev, seen = [], set()
            for e in sorted(set(lst)):
                if e[0] not in seen:
                    seen.add(e[0]); ev.append(e)
            return np.array([bars[x[0]] for x in ev], np.int64)
        TX27 = dedup(tS27, tb); TX09 = dedup(tS09, tb)
        b50 = np.flatnonzero(ok)

        def prevclose(sc, sok, T):
            bb = np.flatnonzero(sok); k = np.searchsorted(bb, T) - 1
            return np.where(k >= 0, sc[bb[np.maximum(k, 0)]], np.nan)
        SPEC = {"M1 加權（只V型；下降三角缺高低價）": (TX27, np.zeros(0, np.int64), tc, tok),
                "M1替代 加權（下降三角以收盤代高低，⛔非逐字）": (TX27, TX09, tc, tok),
                "M2 0050本身": (d50["S27"][0], d50["S09"][0], c, ok)}
        segp = W["segp"]
        eqb = c50f / c50f[t0]
        base = {sg: RR.win_metrics(eqb, t0, n0, x, y)[:2] for sg, (x, y) in segp.items()}
        RES[wn] = {"一直抱0050（還原、不含成本）": {sg: {"年化": base[sg][0], "回落": base[sg][1], "比值": ratio(*base[sg])} for sg in segp},
                   "0050收盤 vs 世界bench 最大相對差": g50, "t0": str(cal[t0].date())}
        for nm, (E27, E09, sc, sok) in SPEC.items():
            allT = np.unique(np.r_[E27, E09]).astype(np.int64)
            for rd, lab in (("前收", ""), ("T收", "｜另一讀法 ref＝T收盤")):
                if rd == "T收" and not len(E27):
                    continue
                refs = []
                for T in allT:
                    pc = float(prevclose(sc, sok, np.array([T]))[0])
                    refs.append(float(sc[T]) if (rd == "T收" and T in set(E27.tolist())) else pc)
                eq, cashf, trades = msim(allT, refs, sc, sok, o, c50f, nx50, t0, n0)
                arm = nm + lab
                blk = {}
                for sg, (x, y) in segp.items():
                    c_, m_, _ = RR.win_metrics(eq, t0, n0, x, y)
                    nsell = sum(1 for tr in trades if tr["X"] is not None and x <= tr["X"] <= y)
                    blk[sg] = {"年化": c_, "回落": m_, "比值": ratio(c_, m_), "年化差（−抱0050）": c_ - base[sg][0], "回落差": m_ - base[sg][1],
                               "空手比例": float(cashf[x:y + 1].mean()), "賣出次數": nsell,
                               "事件數 V型": int(((E27 >= x) & (E27 <= y)).sum()), "事件數 下降三角": int(((E09 >= x) & (E09 <= y)).sum()),
                               "空手天數中位": float(np.median([(tr["Y"] if tr["Y"] is not None else n0) - tr["X"] for tr in trades
                                                         if tr["X"] is not None and x <= tr["X"] <= y])) if nsell else None}
                    ROWS.append({"世界": wn, "臂": arm, "段": sg, **{k: v for k, v in blk[sg].items()},
                                 "抱0050_年化": base[sg][0], "抱0050_回落": base[sg][1], "抱0050_比值": ratio(*base[sg])})
                RES[wn][arm] = {"段": blk, "賣出列": [{"T": str(cal[tr["T"]].date()), "賣": str(cal[tr["X"]].date()) if tr["X"] is not None else None,
                                                    "買回": str(cal[tr["Y"]].date()) if tr["Y"] is not None else None, "ref": tr["ref"]} for tr in trades],
                                "eq": eq}
        log(f"[大盤版 {wn}] " + "｜".join(f"{k}: " + "、".join(f"{sg} {v['段'][sg]['年化']:+.4f}/{v['段'][sg]['回落']:+.4f}（抱 {base[sg][0]:+.4f}/{base[sg][1]:+.4f}）"
                                                                for sg in segp) for k, v in RES[wn].items() if isinstance(v, dict) and "段" in v))
    return RES, pd.DataFrame(ROWS)


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}｜型態全量 seq3 sha {PAT_SHA} ✓")
    WS = AO.worlds(log, a.procs)
    gates = {}
    for wn, W in WS.items():
        gates.update(W["gate"])
    _G["WS"] = WS
    jobs = [(wn, sn, r) for wn in ("主", "早年") for sn in STR for r in seeds_of(sn)]
    with Pool(a.procs) as pool:
        res = pool.map(job_ig, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    IGEQ = {(wn, sn, r): eq for wn, sn, r, eq in res}
    gates["① IG.eng eq_sha ≠ resultsYL_integrate（條數）"] = int(sum(IG.sha(eq) != REF[(wn, STR[sn]["key"], r)] for (wn, sn, r), eq in IGEQ.items()))
    log(f"[閘①] {gates['① IG.eng eq_sha ≠ resultsYL_integrate（條數）']}")
    UG.set_gate_v2(True)
    # ── 逐股：壞根、K 棒、型態 ──
    ROWS = {}; SCS = {}; ELIGS = {}; X = None; MINFO = {}; PKS = {}; DETS = {}
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n0 = len(cal); NP = W["NP"]
        sids = sorted(set(W["SIG"][False]["sid"]) | set(W["SIG"][True]["sid"]))
        M, HB, X, info = AO.market(wn, W, X, log, sids)
        del M
        MINFO[wn] = info
        EX5._G["data"] = W["data"]; EX5._G["cal"] = cal
        _G["data"] = W["data"]; _G["cal"] = cal; _G["closes"] = W["closes"]
        with Pool(a.procs) as pool:
            LBS = dict(pool.map(EX5.bars_job, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=8))
            DR = pool.map(det_job, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=8)
        miss = [s for s in sids if LBS.get(s) is None]
        DET = {s: d for s, d, _ in DR if d is not None}
        miss2 = [s for s in sids if s not in DET]
        if miss or miss2:
            raise SystemExit(f"⛔ load_bars／load_stock 取不到 {miss[:5]} {miss2[:5]}")
        mdd = max(md for _, _, md in DR)
        gates[f"{wn} 型態用 load_stock 收盤 vs 世界收盤 最大相對差"] = mdd
        if mdd > 1e-6:
            raise SystemExit(f"⛔ {wn} 型態收盤閘 {mdd}")
        PK = {}; md = 0.0
        for s in sids:
            PK[s] = EX5.stock_pack(W, s, LBS[s], HB, n0, NP)
            idx, h_, l_, cb = LBS[s]; ok = idx < n0
            cw = PK[s]["c"][idx[ok]]; m_ = np.isfinite(cw) & np.isfinite(cb[ok])
            if m_.any():
                md = max(md, float(np.max(np.abs(cb[ok][m_] / cw[m_] - 1.0))))
        gates[f"{wn} load_bars 收盤 vs 世界收盤 最大相對差"] = md
        if md > 1e-6:
            raise SystemExit(f"⛔ {wn} 收盤閘 {md}")
        if wn == "主":
            gates["主 型態全量事件檔閘"] = patall_gate(DET, cal, W["w0"], W["w1"], log)
        EVR = []
        for s in sids:
            for vid in ("S09", "S27"):
                for t, f in zip(*DET[s][vid]):
                    EVR.append((s, vid, str(cal[t].date()), str(cal[f].date())))
            for t in DET[s]["MA"]:
                EVR.append((s, "MA20連3日", str(cal[t].date()), ""))
        pd.DataFrame(EVR, columns=["sid", "型態", "T", "first"]).to_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), index=False)
        for sn in STR:
            T, SC, EL = build_rows(wn, sn, W, PK, DET, n0, log)
            ROWS[(wn, sn)] = T; SCS[(wn, sn)] = SC; ELIGS[(wn, sn)] = EL
            T.to_csv(os.path.join(OUT, f"rows_{wn}_{sn}.csv.gz"), index=False, float_format="%.17g")
        PKS[wn] = PK; DETS[wn] = DET
    pickle.dump({k: {s: {kk: vv for kk, vv in d.items()} for s, d in v.items()} for k, v in DETS.items()}, open(os.path.join(WORK, "det.pkl"), "wb"), protocol=5)
    for (wn, sn), T in ROWS.items():
        gates[f"{wn}·{sn} 候選列正式出場跨壞根（A_bad）"] = int(T["A_bad"].sum())
        gates[f"{wn}·{sn} 壞根強制列（各臂合計）"] = int(sum(T[f"{v}_bad"].sum() for v in ARMS))
    # ── 組合層 ──
    RUN = {}
    for wn in ("主", "早年"):
        W = WS[wn]
        for sn in STR:
            T = ROWS[(wn, sn)]
            for v in VARS:
                s2, cl, op, SFk, hm, RI = EX5.keyed(W, sn, T, v, SCS[(wn, sn)])
                _G["CUR"] = {"sn": sn, "sig": s2, "cl": cl, "op": op, "SF": SFk, "hm": hm, "NP": W["NP"], "RI": RI, "v": v, "segp": W["segp"]}
                with Pool(a.procs) as pool:
                    rr = pool.map(job_run, seeds_of(sn), chunksize=4)
                for r, eq, f_, e_, pre, A in rr:
                    RUN[(wn, sn, v, r)] = {"eq": eq, "first": f_, "end": e_, "pre": pre, "au": A}
                log(f"[引擎 {wn}·{sn}·{v}] {len(rr)} 條｜{time.time() - T0:.0f}s")
    g2 = g1 = 0
    for (wn, sn, v, r), Rn in RUN.items():
        if v == "A":
            g2 += int(not np.array_equal(Rn["eq"], IGEQ[(wn, sn, r)]))
            g1 += int(IG.sha(Rn["eq"]) != REF[(wn, STR[sn]["key"], r)])
    gates["② A 走 held_map ≠ IG.eng（條數）"] = g2; gates["① A 走 held_map eq_sha ≠ resultsYL_integrate（條數）"] = g1
    log(f"[閘②] {g2}｜[閘①held_map] {g1}")
    if g1 or g2 or gates["① IG.eng eq_sha ≠ resultsYL_integrate（條數）"]:
        raise SystemExit("⛔ 原策略閘不過")
    pickle.dump({k: (v["eq"], v["first"], v["end"]) for k, v in RUN.items()}, open(os.path.join(WORK, "eq.pkl"), "wb"), protocol=5)
    # ── 退化（Y8）：先寫 degeneracy.json（不含任何報酬）──
    DG = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在算任何報酬之前寫入（Y8、裁定 seq325）；退化 ＝ 探索段（營飆 200 顆中位）平均持股 ＜ 3 或 現金比例 ＞ 30%"
          "（X3 一半、X4 整筆凍結都算現金）；原策略同段已達同一條 ⇒ 該條不適用", "格": {}}
    for sn in STR:
        for v in VARS:
            d = {}
            for wn in ("主", "早年"):
                for sg in SEGS[wn]:
                    hs = [RUN[(wn, sn, v, r)]["pre"][sg]["持股"] for r in seeds_of(sn)]
                    cs = [RUN[(wn, sn, v, r)]["pre"][sg]["現金"] for r in seeds_of(sn)]
                    d[sg] = {"平均持股（中位）": float(np.median(hs)), "現金比例（中位）": float(np.median(cs))}
            DG["格"][f"{sn}·{v}"] = d
        o = DG["格"][f"{sn}·A"]["探索"]
        for v in VARS:
            e_ = DG["格"][f"{sn}·{v}"]["探索"]
            rule_h = o["平均持股（中位）"] >= DEG_HOLD; rule_c = o["現金比例（中位）"] <= DEG_CASH
            dg = (rule_h and e_["平均持股（中位）"] < DEG_HOLD) or (rule_c and e_["現金比例（中位）"] > DEG_CASH)
            DG["格"][f"{sn}·{v}"]["退化"] = bool(dg) if v != "A" else False
            DG["格"][f"{sn}·{v}"]["適用條"] = {"持股＜3": rule_h, "現金＞30%": rule_c}
    json.dump(DG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json：{ {k: (round(v['探索']['平均持股（中位）'], 2), round(v['探索']['現金比例（中位）'], 3), v['退化']) for k, v in DG['格'].items()} }")
    # ── 報酬 ──
    from backtest import researchStopRule as SR
    ME = {wn: SR.month_ends(W["cal"], W["w0"], W["w1"]) for wn, W in WS.items()}
    SE = []; T2R = []
    for (wn, sn, v, r), Rn in RUN.items():
        W = WS[wn]; eq = Rn["eq"]; f_, e_ = Rn["first"], Rn["end"]
        row = {"世界": wn, "策略": sn, "臂": v, "r": r, "eq_sha": IG.sha(eq)}
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            c_, m_, _ = RR.win_metrics(eq, f_, e_, x, y)
            p = Rn["pre"][sg]
            row.update({f"{sg}_年化": c_, f"{sg}_回落": m_, f"{sg}_持股": p["持股"], f"{sg}_現金": p["現金"], f"{sg}_買進筆": p["買進筆"],
                        f"{sg}_換手每年": p["換手每年"], f"{sg}_成本每年": p["換手每年"] * COST, f"{sg}_持有天數": p["持有天數"]})
            if v != "A":
                Tk = ROWS[(wn, sn)].set_index("key")
                ks = p["買進鍵"]
                row[f"{sg}_觸發筆"] = int(Tk.loc[ks, f"{v}_trig"].sum()) if ks else 0
        SE.append(row)
        sgT = "主窗" if wn == "主" else "早年"; x, y = W["segp"][sgT]
        a_ = max(x, f_); yy = min(y, e_ - 1)
        MEs = [m for m in ME[wn] if a_ <= m <= yy]
        t2 = {"世界": wn, "策略": sn, "臂": v, "r": r}
        t2.update(AO.t2_first(W["cal"], eq[a_:yy + 1], a_, yy, MEs, T2[sn]))
        T2R.append(t2)
    SE = pd.DataFrame(SE); T2R = pd.DataFrame(T2R)
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    MAIN = []
    for sn in STR:
        for wn in ("主", "早年"):
            for sg in SEGS[wn]:
                base = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == "A")].sort_values("r")
                co, mo = float(base[f"{sg}_年化"].median()), float(base[f"{sg}_回落"].median())
                for v in VARS:
                    g = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == v)].sort_values("r")
                    ca, ma = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                    per = [notworse(*z) for z in zip(g[f"{sg}_年化"], g[f"{sg}_回落"], base[f"{sg}_年化"], base[f"{sg}_回落"])]
                    r0 = g[g["r"] == 0].iloc[0]; b0 = base[base["r"] == 0].iloc[0]
                    MAIN.append({"策略": sn, "臂": v, "臂名": VNAME[v], "段": sg, "顆數": len(g), "原_年化": co, "原_回落": mo, "原_比值": ratio(co, mo),
                                 "臂_年化": ca, "臂_回落": ma, "臂_比值": ratio(ca, ma), "年化差": ca - co, "回落差（臂−原）": ma - mo,
                                 "不降（年化與比值）": notworse(ca, ma, co, mo) if v != "A" else None,
                                 "逐顆不降比例": float(np.mean(per)) if v != "A" else None,
                                 "r0_原_年化": float(b0[f"{sg}_年化"]), "r0_原_回落": float(b0[f"{sg}_回落"]), "r0_臂_年化": float(r0[f"{sg}_年化"]),
                                 "r0_臂_回落": float(r0[f"{sg}_回落"]),
                                 "r0_不降": notworse(float(r0[f"{sg}_年化"]), float(r0[f"{sg}_回落"]), float(b0[f"{sg}_年化"]), float(b0[f"{sg}_回落"])) if v != "A" else None,
                                 "臂_年化p10": float(g[f"{sg}_年化"].quantile(.1)), "臂_年化p90": float(g[f"{sg}_年化"].quantile(.9)),
                                 "持股中位": float(g[f"{sg}_持股"].median()), "現金中位": float(g[f"{sg}_現金"].median()),
                                 "換手每年中位": float(g[f"{sg}_換手每年"].median()), "成本每年中位": float(g[f"{sg}_成本每年"].median()),
                                 "持有天數中位": float(g[f"{sg}_持有天數"].median()), "買進筆中位": float(g[f"{sg}_買進筆"].median()),
                                 "觸發筆中位": float(g[f"{sg}_觸發筆"].median()) if v != "A" else None,
                                 "退化": DG["格"][f"{sn}·{v}"]["退化"]})
    MT = pd.DataFrame(MAIN); MT.to_csv(os.path.join(OUT, "BearExit_main.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    row = lambda sn, v, sg: MT[(MT["策略"] == sn) & (MT["臂"] == v) & (MT["段"] == sg)].iloc[0]
    # ── 判定（Y0）──
    VER = {}
    for sn in STR:
        ex, cf = row(sn, "X0", "探索"), row(sn, "X0", "確認")
        okx, okc = bool(ex["不降（年化與比值）"]), bool(cf["不降（年化與比值）"])
        lit = "有效" if (okx and okc) else ("方向不一致" if okx != okc else "無效")
        g = SE[(SE["世界"] == "主") & (SE["策略"] == sn) & (SE["臂"] == "X0")]
        ntr = g["主窗_觸發筆"].to_numpy(float)
        ntr_med = float(np.median(ntr))
        dg = DG["格"][f"{sn}·X0"]["退化"]
        concl = "樣本不足、測不出" if ntr_med < MINTRIG else ("退化、不判" if dg else lit)
        r0x, r0c = bool(ex["r0_不降"]), bool(cf["r0_不降"])
        lit0 = "有效" if (r0x and r0c) else ("方向不一致" if r0x != r0c else "無效")
        b = SE[(SE["世界"] == "主") & (SE["策略"] == sn) & (SE["臂"] == "A")].sort_values("r"); gg = g.sort_values("r")
        both = [notworse(a1, m1, a0, m0) and notworse(a2, m2, a3, m3) for a1, m1, a0, m0, a2, m2, a3, m3 in
                zip(gg["探索_年化"], gg["探索_回落"], b["探索_年化"], b["探索_回落"], gg["確認_年化"], gg["確認_回落"], b["確認_年化"], b["確認_回落"])]
        VER[sn] = {"結論": concl, "登錄字面結果（不看觸發數與退化）": lit, "探索段不降": okx, "確認段不降": okc, "退化": dg,
                   "主窗持股觸發次數（營飆＝200顆中位）": ntr_med, "觸發次數 ≥ 30": ntr_med >= MINTRIG,
                   **{sg: {k: float(r_[k]) for k in ("原_年化", "原_回落", "原_比值", "臂_年化", "臂_回落", "臂_比值", "逐顆不降比例")}
                      for sg, r_ in (("探索", ex), ("確認", cf))},
                   "r0（種子1000）登錄字面結果": lit0 if sn == "營飆" else None,
                   "逐顆兩段都不降比例": float(np.mean(both)),
                   "早年（描述）": {k: float(row(sn, "X0", "早年")[k]) for k in ("原_年化", "原_回落", "原_比值", "臂_年化", "臂_回落", "臂_比值")}}
    log(f"[判定] {json.dumps({k: (v['結論'], v['登錄字面結果（不看觸發數與退化）'], v['主窗持股觸發次數（營飆＝200顆中位）']) for k, v in VER.items()}, ensure_ascii=False)}")
    # ── 隨機日賣（Y6；主世界）──
    RND = rand_arm(WS["主"], ROWS, ELIGS, PKS["主"], RUN, SE, a, log)
    # ── 必報 ──
    REP = must_report(WS, ROWS, RUN, T2R, PKS, RND, log)
    MK, MKT = market_arms(WS, log)
    MKT.to_csv(os.path.join(OUT, "BearExit_market.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    for wn in MK:
        for k in list(MK[wn]):
            if isinstance(MK[wn][k], dict) and "eq" in MK[wn][k]:
                MK[wn][k]["eq_sha"] = IG.sha(np.nan_to_num(MK[wn][k].pop("eq")))
    # ── 先驗 ──
    PRI = {"① 營量、營飆至少一個判「無效」或「方向不一致」（約七成）": {"營量": VER["營量"]["結論"], "營飆": VER["營飆"]["結論"],
                                                         "成立": any(VER[s]["結論"] in ("無效", "方向不一致") for s in STR)},
           "② 持股觸發次數（兩型態合計、主窗）≥ 30（約六成）": {s: VER[s]["主窗持股觸發次數（營飆＝200顆中位）"] for s in STR} |
           {"兩策略都成立": all(VER[s]["觸發次數 ≥ 30"] for s in STR)},
           "③ 賣後 60 日再創新高比例 ≥ 40%（約六成）": {s: REP[f"{s}·X0·主"]["賣錯率（唯一觸發列）"]["賣後60日再創新高"]["比例"] for s in STR}}
    PRI["③ 賣後 60 日再創新高比例 ≥ 40%（約六成）"]["兩策略都成立"] = all((PRI["③ 賣後 60 日再創新高比例 ≥ 40%（約六成）"][s] or 0) >= 0.40 for s in STR)
    S = {"讀法寫死": TIME, "登錄": f"看空型態出場 seq1 sha {REG_SHA}（裁定 seq356／357／358 發號 N_組合＋1）", "登錄檔": regf, "型態定義": f"型態全量 seq3 sha {PAT_SHA}：patterns_all S09、S27",
         "結果句必附": SENT, "早年必附": NOTE_EARLY, "措辭": WORDING, "閘": gates, "母體": MINFO, "退化": DG, "判定": VER, "隨機日賣": RND["摘要"],
         "先驗": PRI, "主表": MT.to_dict("records"), "必報": REP, "大盤版": MK, "上線條件": "判「有效」前 ⛔ 不推 LINE、⛔ 不進每日名單（登錄 §五）",
         "讀法清單": "見 backtest/researchBearExit.py 檔頭 Y0～Y11", "耗時秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "BearExit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else (o.tolist() if isinstance(o, np.ndarray) else str(o)))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


def rand_arm(W, ROWS, ELIGS, PK, RUN, SE, a, log):
    wn = "主"; n0 = len(W["cal"]); NP = W["NP"]; x0, y0 = W["segp"]["主窗"]
    RSEL_ALL = {}; RES = []; SALES = []
    for sn in STR:
        T = ROWS[(wn, sn)].set_index("key"); EL = ELIGS[(wn, sn)]
        s2, cl, op, SFk, hm = base_inputs(W, sn)
        _G["RB"] = {"sn": sn, "sig": s2, "cl": cl, "op": op, "SF": SFk, "hm": hm, "NP": NP, "segp": W["segp"]}
        modes = [("r0", 0)] if sn == "營量" else [("配對", None), ("r0", 0)]
        for mode, fixed in modes:
            RSEL = {}
            for k in range(NRAND):
                seed = fixed if fixed is not None else k
                rng = np.random.default_rng([RSEED, WID[wn], SID_[sn], 0 if mode == "r0" else 1, k])
                keys = RUN[(wn, sn, "A", seed)]["pre"]["主窗"]["買進鍵"]
                tv = T.loc[keys]
                ov = {}; skip = 0; nsel = 0
                for y in sorted(tv["買進年"].unique()):
                    grp = sorted(tv.index[tv["買進年"] == y])
                    ny = int(tv.loc[grp, "X0_trig"].sum())
                    if ny == 0:
                        continue
                    pick = rng.choice(len(grp), ny, replace=False)
                    for j in sorted(pick):
                        key = grp[j]; el = EL[key]
                        if not len(el):
                            skip += 1; continue
                        d = int(el[rng.integers(len(el))])
                        rw = T.loc[key]; sid = rw["sid"]; pk = PK[sid]; e = int(rw["e"]); xf = int(rw["xf"]); bp = float(rw["bp"])
                        L = None if int(rw["L"]) < 0 else int(rw["L"])
                        Xs = int(pk["nxt"][d + 1])
                        p = ("open", Xs, float(pk["o"][Xs]), Xs - 1)
                        kb = int(rw["kb"])
                        if kb >= 0 and Xs >= kb:
                            vb = np.flatnonzero(pk["bar"][e:min(kb, n0)]); db = e + int(vb[-1]) if len(vb) else e
                            p = ("close", db, float(pk["c"][db]), db)
                        rec = {"parts": [(1.0, p)]}
                        xp, g, Sc, sf, xe, ge = EX5.finalize(rec, pk, bp, n0, NP, L, W["closes"][sid])
                        ov[key] = (xp, g, Sc); nsel += 1
                        if p[0] == "open":
                            SALES.append((sn, mode, k, key, sid, e, d, Xs))
                RSEL[k] = {"seed": seed, "ov": ov, "skip": skip, "n": nsel}
            _G["RSEL"] = RSEL
            with Pool(a.procs) as pool:
                rr = pool.map(rand_job, list(range(NRAND)), chunksize=4)
            for k, met, sh in rr:
                rw_ = {"策略": sn, "模式": mode, "k": k, "seed": RSEL[k]["seed"], "抽中筆": RSEL[k]["n"], "無可抽日": RSEL[k]["skip"], "eq_sha": sh}
                for sg, (c_, m_, h_, ca_) in met.items():
                    rw_.update({f"{sg}_年化": c_, f"{sg}_回落": m_, f"{sg}_持股": h_, f"{sg}_現金": ca_})
                RES.append(rw_)
            RSEL_ALL[(sn, mode)] = {k: {"seed": v["seed"], "sel": {kk: (int(vv[0]), float(vv[1])) for kk, vv in v["ov"].items()}} for k, v in RSEL.items()}
            log(f"[隨機日賣 {sn}·{mode}] {len(rr)} 次｜抽中筆中位 {np.median([v['n'] for v in RSEL.values()])}")
    RD = pd.DataFrame(RES); RD.to_csv(os.path.join(OUT, "rand.csv.gz"), index=False, float_format="%.17g")
    pickle.dump({"sel": RSEL_ALL, "sales": SALES}, open(os.path.join(WORK, "rand.pkl"), "wb"), protocol=5)
    # p 值
    SUM = {}
    for sn in STR:
        A_ = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == "A")].set_index("r")
        X_ = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == "X0")].set_index("r")
        X5_ = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == "X5")].set_index("r")
        for mode in (["r0"] if sn == "營量" else ["配對", "r0"]):
            g = RD[(RD["策略"] == sn) & (RD["模式"] == mode)].sort_values("k")
            blk = {"次數": int(len(g)), "抽中筆中位": float(g["抽中筆"].median()), "無可抽日筆（合計）": int(g["無可抽日"].sum())}
            for sg in SEGS[wn]:
                dr_c = g[f"{sg}_年化"].to_numpy() - A_.loc[g["seed"], f"{sg}_年化"].to_numpy()
                rr_ = np.array([ratio(c, m) for c, m in zip(g[f"{sg}_年化"], g[f"{sg}_回落"])])
                ra_ = np.array([ratio(c, m) for c, m in zip(A_.loc[g["seed"], f"{sg}_年化"], A_.loc[g["seed"], f"{sg}_回落"])])
                dr_r = rr_ - ra_
                if mode == "r0":
                    xc = float(X_.loc[0, f"{sg}_年化"] - A_.loc[0, f"{sg}_年化"])
                    xr = float(ratio(X_.loc[0, f"{sg}_年化"], X_.loc[0, f"{sg}_回落"]) - ratio(A_.loc[0, f"{sg}_年化"], A_.loc[0, f"{sg}_回落"]))
                    x5c = float(X5_.loc[0, f"{sg}_年化"] - A_.loc[0, f"{sg}_年化"])
                else:
                    xc = float(np.median(X_[f"{sg}_年化"] - A_[f"{sg}_年化"]))
                    xr = float(np.median([ratio(c, m) - ratio(c0, m0) for c, m, c0, m0 in zip(X_[f"{sg}_年化"], X_[f"{sg}_回落"], A_[f"{sg}_年化"], A_[f"{sg}_回落"])]))
                    x5c = float(np.median(X5_[f"{sg}_年化"] - A_[f"{sg}_年化"]))
                blk[sg] = {"X0 年化差（−A）": xc, "X0 比值差": xr, "X5 年化差（並列）": x5c,
                           "隨機 年化差 中位": float(np.median(dr_c)), "隨機 年化差 p10/p90": [float(np.quantile(dr_c, .1)), float(np.quantile(dr_c, .9))],
                           "隨機 比值差 中位": float(np.nanmedian(dr_r)),
                           "p 年化（隨機 ≥ X0）": float(np.mean(dr_c >= xc)), "p 比值（隨機 ≥ X0）": float(np.mean(dr_r >= xr)),
                           "隨機 現金中位": float(g[f"{sg}_現金"].median())}
            SUM[f"{sn}·{mode}"] = blk
    log(f"[隨機日賣 p] { {k: {sg: (round(v[sg]['p 年化（隨機 ≥ X0）'], 3), round(v[sg]['p 比值（隨機 ≥ X0）'], 3)) for sg in SEGS['主']} for k, v in SUM.items()} }")
    return {"摘要": SUM, "SALES": SALES}


def must_report(WS, ROWS, RUN, T2R, PKS, RND, log):
    from backtest import researchYL_truetopT as TTT
    from backtest import researchAddOn_truetop_peak as PKF
    REP = {}
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n0 = len(cal); PK = PKS[wn]
        sgT = "主窗" if wn == "主" else "早年"
        for sn in STR:
            T = ROWS[(wn, sn)].set_index("key")
            for v in ("X0", "X1", "X2", "X3", "X4", "X5"):
                per = []; held = set(); typ = {"S09": [], "S27": [], "兩者": []}
                for r in seeds_of(sn):
                    keys = RUN[(wn, sn, v, r)]["pre"][sgT]["買進鍵"]
                    tv = T.loc[keys]; m = tv[tv[f"{v}_trig"] == 1]
                    per.append(len(m)); held |= set(m.index)
                    if v == "X0":
                        for tp in typ:
                            typ[tp].append(int((m["X0_type"] == tp).sum()))
                U = T.loc[sorted(held)] if held else T.iloc[0:0]
                yrs = {}
                for d in U[f"{v}_d"]:
                    yy = int(cal[int(d)].year); yrs[yy] = yrs.get(yy, 0) + 1
                rep = {"持股觸發次數（每顆；營飆200顆中位）": float(np.median(per)), "每顆範圍": [int(np.min(per)), int(np.max(per))],
                       "唯一觸發列": int(len(U)), "唯一觸發列逐年（訊號日曆年）": {str(k): v_ for k, v_ in sorted(yrs.items())},
                       "提早賣筆 報酬差（臂ge−原ge，唯一列）": q3((U[f"{v}_ge"] - U["A_ge"]).to_numpy(float)) if len(U) else {"n": 0}}
                if v == "X0":
                    rep["型態別（每顆中位）"] = {tp: float(np.median(x)) for tp, x in typ.items()}
                    rep["型態別（唯一列）"] = U["X0_type"].value_counts().to_dict()
                    yt = {}
                    for d, tp in zip(U["X0_d"], U["X0_type"]):
                        yy = str(cal[int(d)].year); yt.setdefault(yy, {}); yt[yy][tp] = yt[yy].get(tp, 0) + 1
                    rep["型態別逐年（唯一列）"] = dict(sorted(yt.items()))
                if v in ("X0", "X1", "X2", "X5"):
                    items = [(rw["sid"], int(rw["e"]), int(rw[f"{v}_d"]), int(rw[f"{v}_X"])) for _, rw in U.iterrows() if int(rw[f"{v}_X"]) >= 0]
                    rep["賣錯率（唯一觸發列）"] = misrate(items, PK, n0)
                    if v == "X0":
                        prow = []
                        for sid, e, d, X in items:
                            c = np.asarray(W["closes"][sid], float)[:n0]
                            t = TTT.anchor_pit(c, d, e); te = TTT.anchor_pit(c, e, e)
                            prow.append(PKF.rowstats(c, t, te, d, float(PK[sid]["o"][X]), n0))
                        rep["賣出點相對整段漲勢最高收盤日P（seq343 措辭）"] = {"措辭": WORDING, **(PKF.describe(pd.DataFrame(prow)) if prow else {"筆數": 0})}
                REP[f"{sn}·{v}·{wn}"] = rep
            # 原策略持股中「會觸發」的比例、原出場後再創新高
            held = set()
            for r in seeds_of(sn):
                held |= set(RUN[(wn, sn, "A", r)]["pre"][sgT]["買進鍵"])
            U = T.loc[sorted(held)]
            po = {H: [post_orig(PK[rw["sid"]], int(rw["A_xe"]), int(rw["e"]), n0, H) for _, rw in U.iterrows() if int(rw["A_xe"]) < n0 - 1] for H in (20, 60)}
            REP[f"{sn}·A·{wn}"] = {"原策略唯一持股": int(len(U)), "其中 X0 會觸發": int(U["X0_trig"].sum()), "比例": float(U["X0_trig"].mean()),
                                   **{f"原出場後{H}日再創新高（比持有期最高）": {"n": int(np.isfinite(po[H]).sum()), "比例": float(np.nanmean(po[H])) if np.isfinite(po[H]).any() else None}
                                      for H in (20, 60)}}
    # 隨機日賣的賣錯率（主世界、營量 200 次＋營飆配對 200 次；(key, d) 去重）
    W = WS["主"]; n0 = len(W["cal"]); PK = PKS["主"]
    for sn in STR:
        S_ = {(key, d): (sid, e, d, X) for s_, mode, k, key, sid, e, d, X in RND["SALES"] if s_ == sn and mode == ("r0" if sn == "營量" else "配對")}
        REP[f"{sn}·隨機日賣·主"] = {"唯一賣出 (列,日)": len(S_), "賣錯率": misrate(list(S_.values()), PK, n0)}
    # T2
    T2S = {}
    for sn in STR:
        for wn in ("主", "早年"):
            o_ = T2R[(T2R["策略"] == sn) & (T2R["世界"] == wn) & (T2R["臂"] == "A")].sort_values("r")
            for v in ARMS:
                g = T2R[(T2R["策略"] == sn) & (T2R["世界"] == wn) & (T2R["臂"] == v)].sort_values("r")
                d = {}
                for nm in ("停用", "警戒"):
                    cls = []
                    for x1, x2 in zip(o_[f"第一次{nm}月底"], g[f"第一次{nm}月底"]):
                        if not isinstance(x1, str):
                            cls.append("新增" if isinstance(x2, str) else "都沒有")
                        elif not isinstance(x2, str):
                            cls.append("消失")
                        else:
                            cls.append("提早" if x2 < x1 else ("一樣" if x2 == x1 else "延後"))
                    d[nm] = pd.Series(cls).value_counts().to_dict()
                    d[f"{nm} 月底數中位（原→臂）"] = [float(o_[f"{nm}月底數"].median()), float(g[f"{nm}月底數"].median())]
                    if sn == "營量":
                        d[f"{nm} 第一次月底（原→臂）"] = [o_[f"第一次{nm}月底"].iloc[0], g[f"第一次{nm}月底"].iloc[0]]
                d["月底最深D中位（原→臂）"] = [float(o_["月底最深D"].median()), float(g["月底最深D"].median())]
                T2S[f"{sn}·{v}·{wn}"] = d
    REP["停用條件同時運作（T2）"] = T2S
    log("[必報] 完成")
    return REP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = AO.log_to(os.path.join(OUT, "run.log"))
    log(f"[開跑] {now_tpe()}（台北）NSEED {NSEED} NRAND {NRAND}")
    run(a, log)


if __name__ == "__main__":
    main()

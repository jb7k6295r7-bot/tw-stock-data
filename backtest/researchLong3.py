# -*- coding: utf-8 -*-
"""長線怎麼操作三問 seq1【正式跑】（台股策略線 登錄 sha fe24579779402ee8，2026-10-20 19:58；§四b 附件 sha 1ac2310c08e8b759，20:08；
裁定 seq400 發號（N_前段 ＋4：甲 S1、S3 的 H250 ＋2、乙 ＋2；丙不計）、seq403 核 §四b、seq406 §四 核准開正式跑）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsLong3/freq 不動）；researchLong3_freq（reg_check、load_rev_pit、topk_sel、greedy_segments；讀法 L1～L9 寫死、沿用）、
   researchAscTri_freq（load_world）、research11（load_bars、cl_stats）、patterns（Frame.gate）、researchAddOn（early_extra_bad）、researchTurtle（NOTE_EARLY）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3 --procs 2
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_check
輸出 backtest/resultsLong3/（⛔ 不碰 freq/）：long3.json、甲_表.csv、甲_下市補.csv、甲_組合描述.csv、乙_表.csv、乙_年.csv、丙_表.csv、先驗.csv、
     events_甲.csv.gz（逐筆 R、對照、X、對 0050）、events_乙.csv.gz、events_丙.csv.gz、run.log

═══ 讀法（L 標續編；頻率表 L1～L9 原樣沿用，以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 L10 事件重用（seq406「事件直接重用」）：S1 ＝ freq/events_S1 的 st＝保留；S2 ＝ PTH 頻率表 入選∧跳月_st＝保留；S3 ＝ freq/events_S3；M ＝ freq/events_M。
     ⭐ 對照重建：本檔用頻率表 L3 同式重建 S1 全部列（含剔除原因）與 S3，與已提交檔逐列比，任一不同 ⇒ 中止、⛔ 不算報酬。
 L11 價格：每檔兩世界有效 K 棒接成一條（L1）；★ 跨接縫的價格比照 L1 字面「早年段還原比 × 接縫【原始】收盤比 × 主段還原比」，原始收盤 ＝ load_bars 的 rc
     （⚠ 頻率表 r_between 實作取 df["close"]，那是還原收盤、不是原始收盤 ⇒ 乙 2015～2017 形成年 R36 與 L1 不符；本檔照 L1 字面重算贏輸名單，差異照報，
     ⛔ 不回頭改頻率表）。實作：主段價格乘常數 M ＝ c[j−1]·rc[j] ÷ (rc[j−1]·c[j])（j ＝ 主世界第一根）⇒ 任意兩根之比即上式。
 L12 甲 報酬：R ＝ 出場價 ÷ e 的還原開盤 − 1；出場（同 PTH R2、L5）：x ＝ e＋H−1 收盤；（ke, x 當天或之前最後一根］有壞根 ⇒ 第一個壞根前一根收盤強制；
     最後一根 ＜ x 且距資料尾 ≥ 5 交易日 ⇒ 末根收盤（下市）；早年獨有、活到 2014 年底前 5 日內、x 跨接縫 ⇒「接縫不明」★ 不算 R、⛔ 不進對照池（筆數照報）；
     x ＞ 資料尾 ⇒ 不可用（段界本來就排除）。淨 ＝ R − 0.585%。
 L13 甲 對照（登錄 §二「同日同母體隨機 20 檔同持有平均（扣 0.585%）」；成本兩邊相同 ⇒ X ＝ R − 對照平均 R）：
     ★ S1 池 ＝ 同一進場日 e、同 L2／L3 進場條件（sp 在 500 張閘內 ∧ (sp,e] 無壞根 ∧ e 有成交、開盤有效 ∧ 非開盤鎖漲停）的全部四碼普通股（不看營收）∧ 同 H 的 R 可算；
       S2、S3、M 池 ＝ 同一形成月 PTH 排序母體中 跳月_st＝保留 ∧ R 可算（同 PTH R4）。只扣事件股自己（同 PTH R4 ★）。
     不放回抽 20 檔（不足 ⇒ 全取）；種子 default_rng([20261021, 集合標, H, e, crc32(sid)])；集合標 S1＝1、S2＝2、S3＝3、M＝4、S1 下市補＝11、S3 下市補＝13。
     另報對 0050：R − R0050（0050 同 e 開盤 → x 收盤，跨接縫同 L11）；淨對淨 ★（0050 來回 0.385%＝手續費 0.285%＋ETF 證交稅 0.1%）。
 L14 甲 判定（登錄 §二）：H250 S1、S3 的 探索／確認 各判；X̄ 進場月分群 CI（research11.cl_stats）；★ z ＝ Bonferroni 2 格（Φ⁻¹(1−0.05/4)＝2.2414，本登錄甲 2 判定格）為判定，
     1.96 並報（兩者不同 ⇒ 照寫）；n_eff ＝ min(筆數, 進場月數) ＜ 30 ⇒ 依構造不可判定、30～99 ⇒「樣本中等」；② ＝ 下界 ＞ 0、③ ＝ 上界 ＜ 0、① ＝ 含 0。
     「兩段一致」＝ 兩段同為②或同為③。★ seq322（假訊號臂）登錄未列 ⇒ 本件不判 seq322（照寫）。S2 H250 只描述（seq400，結果句照引 52 週新高件 1833「抱 12 個月 ①」）。
     H 長度不重疊區塊 CI（描述）：進場月由第一個有事件月起每 B 個曆月一塊（B ＝ H120:6、H250:12、H750:36、H1250:60）★，有放回重抽 10,000 次，種子 [20261022, 集合標, H, 段序]；
     與月分群結果不同 ⇒「區塊 CI 較寬」。H750／H1250 一律「樣本極少、只看方向」。
 L15 甲 組合層描述（登錄 §二）：★ 每個進場日一批（cohort），批內等權；月底記值（出場後凍結成現金）；組合月報酬 ＝ 當月有持有的各批月報酬等權平均（Jegadeesh–Titman 重疊式）；
     進場扣 0.585%；超出資料尾的批截到資料尾；無批的月份報酬 0。對 0050（月底還原收盤、跨接縫同 L11）同月份。窗：早年 2005-01～2014-12、主 2017-03～2026-09（描述）。
 L16 乙：贏輸名單照 L7 重算（R36 用 L11）；持有報酬 ＝ e（Y＋1 年第一個交易日）開盤 → Y＋1／Y＋2／Y＋3 年 12 月最後交易日收盤，出場規則同 L12；
     市場 ＝ 同形成年母體中進場「保留」者等權 ★；贏家／輸家 ＝ 名單中「保留」者；產業層 ＝ 贏家／輸家 3 個產業的「保留」成員（★ 成員等權）。
     量 ＝ 組平均 − 市場平均；CI ＝ 形成年分群（逐股 R − 當年市場平均，research11.cl_stats，1.96）。
     ★ 方向判（只判方向、⛔ 不給合格）：主看 36 個月；〔落後／領先〕＝ CI 不含 0 的那一側，否則「分不出」；
       〔一致〕＝ 6 個不重疊形成年（2007、2010、2013、2016、2019、2022）中 ≥ 4 個與全期平均同號，否則〔不一致〕。結果句一律「樣本極少」。
 L17 丙（描述，F1～F7）：觸發日 ＝ freq/events_丙 的 F*_首次（⛔ 不重算）；賣 ＝ 觸發日之後第一根有效 K 棒開盤（＝ 隔天開盤，停牌順延）；賣出那根必須 ≤ 抱 3 年的出場根，否則視同沒賣。
     抱 3 年 ＝ L12 的 H750 出場；純單筆：賣掉後到原出場日記 0 ⇒ d ＝ 賣價 ÷ 進場開盤 − 抱 3 年出場價 ÷ 進場開盤（成本兩邊各一次來回，抵銷）。
     主樣本 ＝ 窗完整（x ≤ 資料尾）∧ 非接縫不明 ★；另報對抱 1 年：d1 ＝ 同一賣法（3 年窗）− 抱 250 日（L12 H250）〔另一讀法 d1′：賣法只在 1 年窗內作用、未觸發則抱滿 250 日，再減抱 250 日〕。
     必報：觸發率、賣出到出場的天數、賣出點離之後最高收盤（(賣出後到原出場日最高收盤 ÷ 賣價 − 1)，真頂措辭 seq343）、
     ★ 賣後 250 日又創新高 ＝ 賣出後 250 個交易日內（遇壞根止）有收盤 ＞ 進場以來到賣出前一根的最高收盤、
     放棄組 ＝ 被賣的若抱滿 3 年（抱 3 年出場價 ÷ 賣價 − 1）、最大回落 ＝ 持有路徑（進場開盤 1、各根收盤、賣出那根開盤）的最大回落，對抱 3 年同式；成對差照報。
     CI ＝ 進場月分群 1.96（描述）。
 L18 下市營收補（seq406 §三、描述）：data/meta/revenue_delisted（origin/main，72 家）只補 revenue_hist 沒有的「股-期」格，⛔ 不覆蓋原值；
     用 L3 同式重建 S1、S3（S2 不變）⇒ 甲 H120／H250／H750 同表再算一次，與原口徑並列（⛔ 不改判定）。
 L19 結果句必附：「2015 後營收母體無下市股（存活者偏差，偏樂觀）」「單筆層通過 ≠ 組合會贏 0050」「⛔ 不是抱多久最好的證據」「長抱遇減資、下市的比例 x%」；
     早年附 researchTurtle.NOTE_EARLY（reduce_v2 約 0.3%）；丙附「利多反應完是使用者的判斷，本件只是把它寫成數字，不代表抓得到真頂（真頂訊號（多半在最高點之前））」
     「數字門檻（第 90 百分位、前 5%、5 日）為台股策略線定」；同根兩出場價取較低（seq373）：本件每一筆只有一種出場價（固定持有期收盤、壞根前一根收盤、
     觸發後隔天開盤三者互斥），照寫不適用。
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import os
import subprocess
import sys
import time
import zlib
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLong3_freq as LF               # noqa: E402  reg_check、load_rev_pit、topk_sel、greedy_segments（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world
from backtest import research11 as R                        # noqa: E402  load_bars、cl_stats
from backtest import patterns as P                          # noqa: E402  Frame.gate
from backtest import researchAddOn as RA                    # noqa: E402  early_extra_bad、WORK
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY
from backtest import evaluate as EVAL                       # noqa: E402  COST
import backtest.data as D                                   # noqa: E402

OUT = "backtest/resultsLong3"
FREQ = LF.OUT
PTHEV = LF.PTHEV
COST = EVAL.COST
COST50 = 0.001425 * 2 + 0.001
NCTRL = 20
SEED_CTRL, SEED_BLOCK = 20261021, 20261022
BOOT = 10_000
Z196 = 1.96
ZB2 = NormalDist().inv_cdf(1 - 0.05 / 4)
HS = (120, 250, 750, 1250)
BM = {120: 6, 250: 12, 750: 36, 1250: 60}
SETTAG = {"S1": 1, "S2": 2, "S3": 3, "M": 4, "S1_下市補": 11, "S3_下市補": 13}
TYPN = {1: "到期收盤", 2: "到期日無成交用前一根", 3: "壞根前一根強制", 4: "下市末根", 5: "超出資料尾", 6: "接縫不明", 7: "合併序列無進場K棒"}
NEFF_MIN = 30
FS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
FNAME = {"F1": "近4季營收年增＜0", "F2": "單季毛利率連2季年減", "F3": "月營收年增連3月＜0", "F4": "本益比≥自身5年第90百分位",
         "F5": "200日乖離全市場前5%", "F6": "營收創高但5日不漲（利多反應完）", "F7": "F6且(F4或F5)（使用者版）"}
SENT_COMMON = ["2015 後營收母體無下市股（存活者偏差，偏樂觀）", "單筆層通過 ≠ 組合會贏 0050", "⛔ 不是抱多久最好的證據"]
SENT_C = ["利多反應完是使用者的判斷，本件只是把它寫成數字，不代表抓得到真頂（真頂訊號（多半在最高點之前））",
          "數字門檻（第 90 百分位、前 5%、5 日）為台股策略線定"]
SENT_373 = "同根兩出場價取較低（seq373）：本件每筆只有一種出場價（固定持有期收盤／壞根前一根收盤／觸發後隔天開盤互斥）⇒ 不適用，照寫"
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


def fmtp(x, d=1):
    return "—" if x is None or not np.isfinite(x) else "{:.{}f}%".format(x * 100, d)


# ═════════════ 逐股（各世界）═════════════
def stock_job(a):
    wn, sid = a
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return wn, sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    c = np.asarray(B["c"], float); o = np.asarray(B["o"], float); rc = np.asarray(B["rc"], float)
    if not np.isfinite(c).all():
        raise SystemExit(f"⛔ {wn} {sid} 有效 K 棒收盤有缺值")
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    f = P.Frame(df, set())
    has = np.zeros(n0, bool); has[idx] = True
    gate = np.asarray(f.gate, bool) & np.asarray(W["PV"][i], bool) & has
    return wn, sid, {"idx": idx.astype(np.int32), "bad": bad, "c": c, "o": o, "rc": rc, "gate": np.packbits(gate)}


# ═════════════ 小工具 ═════════════
def nxt_bad(bad):
    nb = len(bad); BIG = nb + 10
    out = np.full(nb + 2, BIG, np.int64)
    p = np.where(np.asarray(bad, bool), np.arange(nb), BIG)
    if nb:
        out[:nb] = np.minimum.accumulate(p[::-1])[::-1]
    return out


def exits_vec(S, e, x, CEND, NE):
    """L12：e、x 為日曆位置陣列 ⇒ (ke, kexit, typ)。typ 見 TYPN。"""
    e = np.asarray(e, np.int64); x = np.asarray(x, np.int64)
    pos = S["pos"]; nb = len(pos)
    ke = np.searchsorted(pos, e, "left")
    if not ((ke < nb).all() and (pos[np.minimum(ke, nb - 1)] == e).all()):
        raise SystemExit(f"⛔ 進場日沒有有效 K 棒 {S.get('sid')}")
    typ = np.zeros(len(e), np.int8); kexit = np.full(len(e), -1, np.int64)
    beyond = x > CEND
    kx = np.searchsorted(pos, np.minimum(x, CEND), "right") - 1
    kb = S["nxb"][ke + 1]
    forced = ~beyond & (kb <= kx)
    typ[forced] = 3; kexit[forced] = kb[forced] - 1
    L = int(pos[-1])
    rest = ~beyond & ~forced
    short = rest & (L < x)
    if short.any():
        seam = short & (not S["main"]) & (L >= NE - 5) & (x >= NE)
        dl = short & ~seam & (CEND - L >= 5)
        o2 = short & ~seam & ~dl
        typ[seam] = 6
        typ[dl] = 4; kexit[dl] = nb - 1
        typ[o2] = 2; kexit[o2] = kx[o2]
    full = rest & ~short
    if full.any():
        typ[full] = np.where(pos[kx[full]] == x[full], 1, 2); kexit[full] = kx[full]
    typ[beyond] = 5
    return ke, kexit, typ


def res_of(m, se, ne, z):
    if ne < NEFF_MIN:
        return "依構造不可判定"
    lo, hi = m - z * se, m + z * se
    return "結果①" if lo <= 0 <= hi else ("結果②" if lo > 0 else "結果③")


def stats(x, key, z=Z196):
    x = np.asarray(x, float); key = np.asarray(key)
    ok = np.isfinite(x); x = x[ok]; key = key[ok]
    n = len(x)
    if n == 0:
        return {"n": 0, "n_eff": 0}
    cs = R.cl_stats(x, key)
    m, se, ng = cs["mean"], cs["se"], cs["months"]
    ne = int(min(n, ng))
    mm = pd.Series(x).groupby(key).mean()
    return {"n": int(n), "平均": float(m), "中位": float(np.median(x)), "勝率": float((x > 0).mean()), "se": float(se), "群數": int(ng), "n_eff": ne,
            "lo": float(m - z * se), "hi": float(m + z * se), "z": float(z), "結果": res_of(m, se, ne, z),
            "lo196": float(m - Z196 * se), "hi196": float(m + Z196 * se), "結果196": res_of(m, se, ne, Z196),
            "t": float(m / se) if se > 0 else None, "逐群平均之中位": float(mm.median())}


def block_ci(x, mon, bm, seed, B=BOOT):
    x = np.asarray(x, float); mon = np.asarray(mon, np.int64)
    ok = np.isfinite(x); x = x[ok]; mon = mon[ok]
    if len(x) == 0:
        return None
    blk = (mon - mon.min()) // bm
    nbk = int(blk.max()) + 1
    Sx = np.bincount(blk, weights=x, minlength=nbk); N = np.bincount(blk, minlength=nbk).astype(float)
    keep = N > 0; Sx = Sx[keep]; N = N[keep]; nbk = len(N)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nbk, size=(B, nbk))
    m = Sx[pick].sum(1) / np.maximum(N[pick].sum(1), 1e-300)
    lo, hi = float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
    return {"塊數": int(nbk), "lo": lo, "hi": hi, "結果": "結果①" if lo <= 0 <= hi else ("結果②" if lo > 0 else "結果③")}


def mdd_path(path):
    path = np.asarray(path, float)
    if len(path) == 0:
        return np.nan
    return float((path / np.maximum.accumulate(path) - 1.0).min())


def ann_stats(r):
    r = np.asarray(r, float)
    if len(r) == 0:
        return None, None
    eq = np.r_[1.0, np.cumprod(1 + r)]
    cagr = float(eq[-1] ** (12.0 / len(r)) - 1.0)
    return cagr, mdd_path(eq)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    regs = LF.reg_check()
    log(f"[登錄] {regs}（sha 已驗）")
    J = {"性質": "長線怎麼操作三問 seq1 正式跑", "登錄": regs,
         "裁定": "seq400 發號（N_前段 ＋4：甲 S1、S3 的 H250 ＋2、乙 ＋2；丙不計）；seq403 核 §四b F4～F7；seq406 §四 核准正式跑、§三 必附存活者偏差句",
         "z_判定": ZB2, "z_並報": Z196}
    # ── 世界
    WS = {wn: AT.load_world(wn) for wn in ("早年", "主")}
    We, Wm = WS["早年"], WS["主"]
    ne, nm_ = We["n0"], Wm["n0"]
    CAL = We["cal"].append(Wm["cal"]); NC = len(CAL); CEND = NC - 1
    OFF = {"早年": 0, "主": ne}
    CP = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(CAL)}
    cpos = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts)))
    cpos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    MON = np.array([d.year * 12 + d.month - 1 for d in CAL], np.int64)
    log(f"[合併日曆] {CAL[0].date()}～{CAL[-1].date()}｜{NC} 日")
    # ── 逐股
    _G.update(WS)
    jobs = [(wn, s) for wn in ("早年", "主") for s in WS[wn]["sids"]]
    RES = {"早年": {}, "主": {}}
    with Pool(a.procs) as pool:
        for k_, (wn, sid, r) in enumerate(pool.imap_unordered(stock_job, jobs, chunksize=8)):
            RES[wn][sid] = r
            if (k_ + 1) % 1000 == 0:
                log(f"  逐股 {k_ + 1}／{len(jobs)}｜{time.time() - t0:.0f}s")
    log(f"[逐股完] {time.time() - t0:.0f}s")
    SS = {}
    main_sids = {s for s, r in RES["主"].items() if r is not None}
    seam_info = {"兩世界都有": 0, "接縫原始收盤缺⇒接縫當壞根": 0}
    for s in sorted(set(RES["早年"]) | set(RES["主"])):
        parts = [(wn, RES[wn].get(s)) for wn in ("早年", "主") if RES[wn].get(s) is not None]
        if not parts:
            continue
        pos = np.concatenate([r["idx"].astype(np.int64) + OFF[wn] for wn, r in parts])
        bad = np.concatenate([r["bad"] for wn, r in parts]).copy()
        c = np.concatenate([r["c"] for wn, r in parts]); o = np.concatenate([r["o"] for wn, r in parts])
        rc = np.concatenate([r["rc"] for wn, r in parts])
        wid = np.concatenate([np.full(len(r["idx"]), 0 if wn == "早年" else 1, np.int8) for wn, r in parts])
        cc = c.copy(); oo = o.copy()
        if (wid == 0).any() and (wid == 1).any():
            seam_info["兩世界都有"] += 1
            j = int(np.argmax(wid == 1)); bad[j] = False
            Mf = c[j - 1] * rc[j] / (rc[j - 1] * c[j]) if (np.isfinite(rc[j]) and np.isfinite(rc[j - 1]) and rc[j - 1] > 0) else np.nan
            if np.isfinite(Mf) and Mf > 0:
                cc[wid == 1] *= Mf; oo[wid == 1] *= Mf
            else:
                bad[j] = True; seam_info["接縫原始收盤缺⇒接縫當壞根"] += 1
        SS[s] = {"sid": s, "pos": pos, "bad": bad, "CB": np.r_[0, np.cumsum(bad)], "nxb": nxt_bad(bad), "c": c, "cc": cc, "oo": oo, "wid": wid,
                 "main": s in main_sids, "last": int(pos[-1])}
    log(f"[合併] 代號 {len(SS)}｜{seam_info}")
    J["接縫"] = seam_info
    # 0050
    B50 = {}
    for wn in ("早年", "主"):
        D.DATA = WS[wn]["data"]
        B = R.load_bars("0050", "twse", WS[wn]["cal"])
        B50[wn] = B
    idx50 = np.concatenate([B50["早年"]["idx"].astype(np.int64), B50["主"]["idx"].astype(np.int64) + ne])
    c50 = np.concatenate([B50["早年"]["c"], B50["主"]["c"]]).astype(float); o50 = np.concatenate([B50["早年"]["o"], B50["主"]["o"]]).astype(float)
    rc50 = np.concatenate([B50["早年"]["rc"], B50["主"]["rc"]]).astype(float)
    j50 = len(B50["早年"]["idx"])
    M50 = c50[j50 - 1] * rc50[j50] / (rc50[j50 - 1] * c50[j50])
    c50[j50:] *= M50; o50[j50:] *= M50
    dr = c50[1:] / c50[:-1] - 1
    log(f"[0050] 有效 K 棒 {len(idx50)}／日曆 {NC}｜接縫 M {M50:.4f}｜還原日報酬 最大 {dr.max():+.3f} 最小 {dr.min():+.3f}")
    J["0050"] = {"有效K棒": int(len(idx50)), "日曆": NC, "接縫M": float(M50), "日報酬最大": float(dr.max()), "日報酬最小": float(dr.min())}
    if abs(dr).max() > 0.2:
        raise SystemExit("⛔ 0050 還原序列有 > 20% 單日跳動")

    def r50(e, x):
        ke = int(np.searchsorted(idx50, e, "left")); kx = int(np.searchsorted(idx50, min(x, CEND), "right")) - 1
        if ke >= len(idx50) or kx < ke:
            return np.nan
        return c50[kx] / o50[ke] - 1.0

    # ═════════ 對照重建：S1（L3 同式）、S3 ═════════
    rev, ly, IND = LF.load_rev_pit([We["data"], Wm["data"]])
    PER = list(rev.index); KP = {p: k for k, p in enumerate(PER)}
    AV = np.full(len(PER), -1, np.int64)
    for k, p in enumerate(PER):
        y, m = int(p[:4]), int(p[5:])
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(y2, m2, 15 if p >= "2026-01" else 10)
        e = int(CAL.searchsorted(cut, side="right"))
        if 1 <= e <= CEND:
            AV[k] = e

    def hi_mat(rv_df):
        RV = rv_df.to_numpy(float)
        HI = np.full(RV.shape, -1, np.int8)
        for k in range(24, len(PER)):
            h = RV[k - 24:k]; full = np.isfinite(h).all(axis=0)
            mx = np.where(full, np.nanmax(np.where(np.isfinite(h), h, -np.inf), axis=0), np.nan)
            r0 = RV[k]; okk = full & np.isfinite(r0)
            HI[k, okk] = (r0[okk] >= mx[okk]).astype(np.int8)
        return HI, list(rv_df.columns)

    def build_s1(HI, RSID):
        RIX = {s: j for j, s in enumerate(RSID)}
        rows = []
        for wn in ("早年", "主"):
            W = WS[wn]; off = OFF[wn]; n0 = W["n0"]
            for s, r in RES[wn].items():
                if r is None or s not in RIX:
                    continue
                j = RIX[s]; gate = np.unpackbits(r["gate"])[:n0].astype(bool)
                i = W["ix"][s]; idx = r["idx"].astype(np.int64); CBw = np.r_[0, np.cumsum(r["bad"])]
                for k in np.flatnonzero(HI[:, j] == 1):
                    e = int(AV[k])
                    if e < 0 or not (off <= e < off + n0):
                        continue
                    ew = e - off; sp = e - 1
                    rec = {"sid": s, "期別": PER[k], "世界": wn, "e": e, "sp": sp}
                    if not (off <= sp < off + n0):
                        rec["st"] = LF.ST_SPX
                    else:
                        spw = sp - off
                        if not gate[spw]:
                            rec["st"] = LF.ST_GATE
                        else:
                            ksp = int(np.searchsorted(idx, spw, "right")) - 1
                            kee = int(np.searchsorted(idx, ew, "right")) - 1
                            if kee > ksp and CBw[kee + 1] - CBw[ksp + 1] > 0:
                                rec["st"] = LF.ST_BAD
                            elif not (W["TRD"][i, ew] and np.isfinite(W["O"][i, ew]) and W["O"][i, ew] > 0):
                                rec["st"] = LF.ST_NOTRD
                            elif W["UPL"][i, ew]:
                                rec["st"] = LF.ST_UPL
                            else:
                                rec["st"] = LF.ST_KEEP
                    rows.append(rec)
        S1 = pd.DataFrame(rows)
        S1["進場日"] = [str(CAL[e].date()) for e in S1["e"]]; S1["sp日"] = [str(CAL[p].date()) for p in S1["sp"]]
        return S1

    HI0, RSID0 = hi_mat(rev)
    S1all = build_s1(HI0, RSID0)
    ref = pd.read_csv(os.path.join(FREQ, "events_S1.csv.gz"), dtype={"sid": str, "期別": str})
    key = ["世界", "sid", "期別"]
    a_ = S1all.sort_values(key).reset_index(drop=True)[list(ref.columns)]
    b_ = ref.sort_values(key).reset_index(drop=True)
    same_s1 = len(a_) == len(b_) and bool((a_.astype(str).to_numpy() == b_.astype(str).to_numpy()).all())
    log(f"[對照重建 S1] 本檔 {len(a_)} 列｜已提交 {len(b_)} 列｜逐列相同 {same_s1}")
    if not same_s1:
        raise SystemExit("⛔ S1 重建 ≠ 已提交 events_S1 ⇒ 中止（未算任何報酬）")
    EVp = []
    for wn in ("早年", "主"):
        x = pd.read_csv(PTHEV.format(wn), dtype={"sid": str}); x["世界"] = wn; EVp.append(x)
    EVp = pd.concat(EVp, ignore_index=True)
    EVp["e"] = EVp["跳月_進場日"].map(lambda d: CP.get(d, -1) if isinstance(d, str) else -1)
    EVp["期別"] = EVp["形成月底"].str[:7]
    S2 = EVp[EVp["入選"] & (EVp["跳月_st"] == "保留")].copy()

    def build_s3(HI, RSID):
        RIX = {s: j for j, s in enumerate(RSID)}
        h = [int(HI[KP[p], RIX[s]]) if (p in KP and s in RIX) else -1 for s, p in zip(S2["sid"], S2["期別"])]
        return S2[np.array(h) == 1].copy()

    S3 = build_s3(HI0, RSID0)
    ref3 = pd.read_csv(os.path.join(FREQ, "events_S3.csv.gz"), dtype={"sid": str, "期別": str})
    a3 = S3.assign(進場日=[str(CAL[e].date()) for e in S3["e"]])[list(ref3.columns)].sort_values(["世界", "sid", "形成月底"]).reset_index(drop=True)
    b3 = ref3.sort_values(["世界", "sid", "形成月底"]).reset_index(drop=True)
    same_s3 = len(a3) == len(b3) and bool((a3.astype(str).to_numpy() == b3.astype(str).to_numpy()).all())
    log(f"[對照重建 S3] 本檔 {len(a3)}｜已提交 {len(b3)}｜逐列相同 {same_s3}")
    if not same_s3:
        raise SystemExit("⛔ S3 重建 ≠ 已提交 events_S3 ⇒ 中止")
    MM = pd.read_csv(os.path.join(FREQ, "events_M.csv.gz"), dtype={"sid": str})
    MM["e"] = MM["跳月_進場日"].map(lambda d: CP.get(d, -1) if isinstance(d, str) else -1)
    J["對照重建"] = {"S1逐列相同": same_s1, "S1列數": int(len(a_)), "S3逐列相同": same_s3, "S3列數": int(len(a3)), "S2": int(len(S2)), "M": int(len(MM))}
    # ── 下市營收補（L18）
    git_head = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    blob = subprocess.run(["git", "show", "origin/main:data/meta/revenue_delisted/revenue_delisted.csv"], capture_output=True, check=True).stdout
    import hashlib
    DLV = pd.read_csv(io.BytesIO(blob), dtype={"stock_id": str, "period": str})
    rev2 = rev.copy(); n_add = 0; n_conf = 0; n_out = 0
    for s, p, v in zip(DLV["stock_id"], DLV["period"], DLV["revenue_k"]):
        if p not in KP:
            n_out += 1; continue
        if s not in rev2.columns:
            rev2[s] = np.nan
        cur = rev2.at[p, s]
        if np.isfinite(cur):
            n_conf += int(abs(cur - float(v)) > 1.0)
            continue
        rev2.at[p, s] = float(v); n_add += 1
    HI2, RSID2 = hi_mat(rev2)
    S1all2 = build_s1(HI2, RSID2)
    S1k2 = S1all2[S1all2["st"] == LF.ST_KEEP].copy()
    S3_2 = build_s3(HI2, RSID2)
    J["下市補"] = {"來源": "origin/main data/meta/revenue_delisted/revenue_delisted.csv", "origin_main": git_head,
                 "檔 sha256": hashlib.sha256(blob).hexdigest()[:16], "列": int(len(DLV)), "家": int(DLV["stock_id"].nunique()),
                 "補入股期格": n_add, "原已有值(不覆蓋)且差>1千元": n_conf, "期別在面板外": n_out,
                 "S1保留_原": int((S1all["st"] == LF.ST_KEEP).sum()), "S1保留_補後": int(len(S1k2)), "S3_原": int(len(S3)), "S3_補後": int(len(S3_2)),
                 "補後新增S1事件代號數": int(S1k2.loc[~S1k2.set_index(["sid", "期別"]).index.isin(S1all[S1all["st"] == LF.ST_KEEP].set_index(["sid", "期別"]).index), "sid"].nunique())}
    log(f"[下市補] {J['下市補']}")
    S1k = S1all[S1all["st"] == LF.ST_KEEP].copy()
    # ═════════ 甲：R、對照 ═════════
    SETS = {"S1": S1k[["sid", "e"]].assign(g=S1k["e"].astype(str)), "S2": S2[["sid", "e"]].assign(g=S2["世界"] + S2["形成月底"]),
            "S3": S3[["sid", "e"]].assign(g=S3["世界"] + S3["形成月底"]), "M": MM[["sid", "e"]].assign(g=MM["世界"] + MM["形成月底"]),
            "S1_下市補": S1k2[["sid", "e"]].assign(g=S1k2["e"].astype(str)), "S3_下市補": S3_2[["sid", "e"]].assign(g=S3_2["世界"] + S3_2["形成月底"])}
    for nm, T in SETS.items():
        bad_ = int((~T["sid"].isin(SS)).sum()) + int((T["e"] < 0).sum())
        if bad_:
            raise SystemExit(f"⛔ {nm} 有 {bad_} 筆沒有 K 棒或進場日")
    # S1 池（同 e、同進場條件）
    GU = {}
    for wn in ("早年", "主"):
        for s, r in RES[wn].items():
            if r is not None:
                GU[(wn, s)] = (np.unpackbits(r["gate"])[:WS[wn]["n0"]].astype(bool), r["idx"].astype(np.int64), np.r_[0, np.cumsum(r["bad"])])
    PO1 = {}
    for e in sorted(set(S1k["e"]) | set(S1k2["e"])):
        wn = "早年" if e < ne else "主"; W = WS[wn]; off = OFF[wn]; ew = e - off; sp = e - 1
        if not (off <= sp):
            raise SystemExit("⛔ S1 保留事件 sp 跨世界")
        spw = sp - off; mem = []
        for s, r in RES[wn].items():
            if r is None:
                continue
            g, idx, CBw = GU[(wn, s)]
            if not g[spw]:
                continue
            ksp = int(np.searchsorted(idx, spw, "right")) - 1; kee = int(np.searchsorted(idx, ew, "right")) - 1
            if kee > ksp and CBw[kee + 1] - CBw[ksp + 1] > 0:
                continue
            i = W["ix"][s]
            if not (W["TRD"][i, ew] and np.isfinite(W["O"][i, ew]) and W["O"][i, ew] > 0) or W["UPL"][i, ew]:
                continue
            mem.append(s)
        PO1[str(e)] = (sorted(mem), e)
    log(f"[S1 池] 進場日 {len(PO1)}｜每日池大小中位 {np.median([len(v[0]) for v in PO1.values()]):.0f}｜{time.time() - t0:.0f}s")
    # S1 事件必在自己的池內（同條件）
    for s, e in zip(S1k["sid"], S1k["e"]):
        if s not in set(PO1[str(e)][0]):
            raise SystemExit(f"⛔ S1 事件 {s} {e} 不在同日池內")
    POP = {}
    pk = EVp[EVp["跳月_st"] == "保留"]
    for (w_, m_), g in pk.groupby(["世界", "形成月底"]):
        if g["e"].nunique() != 1 or int(g["e"].iloc[0]) < 0:
            raise SystemExit(f"⛔ PTH 池 {w_}{m_} 進場日不唯一")
        POP[w_ + m_] = (sorted(g["sid"].tolist()), int(g["e"].iloc[0]))
    # 需要的 (sid, e) ⇒ 各 H 的 R
    need = {}
    for nm, T in SETS.items():
        for s, e in zip(T["sid"], T["e"]):
            need.setdefault(s, set()).add(int(e))
    for g, (mem, e) in PO1.items():
        for s in mem:
            need.setdefault(s, set()).add(int(e))
    for g, (mem, e) in POP.items():
        for s in mem:
            need.setdefault(s, set()).add(int(e))
    RT = {}   # (sid, e, H) ⇒ (R, typ, 出場日曆位置)
    nmiss_bar = 0
    for s, es in need.items():
        if s not in SS:
            nmiss_bar += len(es); continue
        S = SS[s]; ea = np.array(sorted(es), np.int64)
        okb = np.isin(ea, S["pos"])
        nmiss_bar += int((~okb).sum()); ea = ea[okb]
        for H in HS:
            ke, kx, ty = exits_vec(S, ea, ea + H - 1, CEND, ne)
            Rv = np.where(np.isin(ty, (1, 2, 3, 4)), S["cc"][np.maximum(kx, 0)] / S["oo"][ke] - 1.0, np.nan)
            xp = np.where(kx >= 0, S["pos"][np.maximum(kx, 0)], -1)
            for e, rv, t_, xx in zip(ea, Rv, ty, xp):
                RT[(s, int(e), H)] = (float(rv), int(t_), int(xx))
    log(f"[甲 R] (sid,e,H) {len(RT):,}｜池內無進場 K 棒 {nmiss_bar}｜{time.time() - t0:.0f}s")
    # 減資（同頻率表 L5）
    RED = {}
    for s in SS:
        p_ = os.path.join(Wm["data"], "adj", f"{s}.csv")
        if os.path.exists(p_):
            x = pd.read_csv(p_, usecols=["date", "event"])
            for d in x.loc[x["event"] == "reduce", "date"]:
                if d in CP:
                    RED.setdefault(s, []).append(CP[d])
    import pickle
    Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
    EXB, _ = RA.early_extra_bad(Wa, lambda *x: None)
    for s, ks in EXB.items():
        for k in ks:
            RED.setdefault(s, []).append(int(k))
    RED = {s: np.array(sorted(set(v)), np.int64) for s, v in RED.items()}
    r50c = {}
    PR_ = {}   # (池鍵, H) ⇒ (sids 陣列（R 可算、已排序）, R 陣列, {sid: 位置})
    for src in (PO1, POP):
        for g, (mem, e) in src.items():
            for H in HS:
                ok = [m for m in mem if np.isfinite(RT.get((m, e, H), (np.nan,))[0])]
                PR_[(g, H)] = (np.array(ok, dtype=object), np.array([RT[(m, e, H)][0] for m in ok], float), {m: q for q, m in enumerate(ok)})
    log(f"[池 R] {len(PR_):,} 組｜{time.time() - t0:.0f}s")
    ROWS = []
    for nm, T in SETS.items():
        tag = SETTAG[nm]
        for s, e, g in zip(T["sid"], T["e"], T["g"]):
            e = int(e)
            for H in HS:
                rv, ty, xp = RT.get((s, e, H), (np.nan, -1, -1))
                x = e + H - 1
                if ty == 5:
                    continue
                psid, pR, pix = PR_[(g, H)]
                q0 = pix.get(s, -1)
                npool = len(psid) - (1 if q0 >= 0 else 0)
                rng = np.random.default_rng([SEED_CTRL, tag, H, e, zlib.crc32(s.encode())])
                if npool > 0:
                    ch = np.sort(rng.choice(npool, size=min(NCTRL, npool), replace=False))
                    if q0 >= 0:
                        ch = np.where(ch >= q0, ch + 1, ch)
                    pick = list(psid[ch]); cm = float(pR[ch].mean())
                else:
                    pick = []; cm = np.nan
                pool = range(npool)
                if (e, H) not in r50c:
                    r50c[(e, H)] = r50(e, x)
                rd = RED.get(s)
                red = bool(rd is not None and ((rd > e) & (rd <= x)).any())
                ROWS.append({"集合": nm, "sid": s, "e": e, "進場日": str(CAL[e].date()), "H": H, "x": x, "typ": ty, "出場": TYPN.get(ty, ""),
                             "出場日": str(CAL[xp].date()) if xp >= 0 else "", "R": rv, "池大小": len(pool), "對照數": len(pick), "對照R平均": cm,
                             "X": rv - cm if np.isfinite(rv) else np.nan, "R0050": r50c[(e, H)],
                             "對0050(淨對淨)": (rv - COST) - (r50c[(e, H)] - COST50) if np.isfinite(rv) else np.nan,
                             "窗內有減資": red, "對照": "|".join(pick)})
    EA = pd.DataFrame(ROWS)
    EA["進場月"] = EA["進場日"].str[:7]
    log(f"[甲 逐筆] {len(EA):,} 列｜{time.time() - t0:.0f}s")
    # ── 甲 段與統計
    p170302, p201231, p211230, p220103 = cpos("2017-03-02"), cpos_le("2020-12-31"), cpos_le("2021-12-30"), cpos("2022-01-03")
    p05, p141231, p211231 = cpos("2005-01-01"), cpos_le("2014-12-31"), cpos_le("2021-12-31")
    SEGDEF = {}
    for H in (120, 250):
        SEGDEF[(H, "探索")] = (p170302, p201231 if H == 250 else p211230, p211230)
        SEGDEF[(H, "確認")] = (p220103, CEND, CEND)
        SEGDEF[(H, "早年(描述)")] = (p05, p141231, CEND)
    for H in (750, 1250):
        SEGDEF[(H, "長窗2005～2021")] = (p05, p211231, CEND)
        SEGDEF[(H, "長窗_2005～2014")] = (p05, p141231, CEND)
        SEGDEF[(H, "長窗_2015～2021")] = (p141231 + 1, p211231, CEND)
    SEGNUM = {sg: i for i, sg in enumerate(sorted({k[1] for k in SEGDEF}))}
    TA = []
    for nm in SETS:
        for (H, sg), (a0, a1, xb) in SEGDEF.items():
            sub = EA[(EA["集合"] == nm) & (EA["H"] == H) & (EA["e"] >= a0) & (EA["e"] <= a1) & (EA["x"] <= xb)]
            seam = int((sub["typ"] == 6).sum())
            v = sub[np.isfinite(sub["R"]) & np.isfinite(sub["X"])]
            st = stats(v["X"].to_numpy(), v["進場月"].to_numpy(), ZB2 if (nm in ("S1", "S3") and H == 250 and sg in ("探索", "確認")) else Z196)
            mon = v["進場日"].map(lambda d: int(d[:4]) * 12 + int(d[5:7]) - 1).to_numpy()
            bk = block_ci(v["X"].to_numpy(), mon, BM[H], [SEED_BLOCK, SETTAG[nm], H, SEGNUM[sg]]) if len(v) else None
            d50 = v["對0050(淨對淨)"].to_numpy(float)
            role = ("判定格（seq400）" if (nm in ("S1", "S3") and H == 250 and sg in ("探索", "確認"))
                    else ("只描述（seq400：52 週新高件 1833 已看過抱 12 個月）" if (nm == "S2" and H == 250 and sg in ("探索", "確認"))
                          else ("下市營收補（描述，seq406）" if "下市補" in nm else "描述")))
            row = {"集合": nm, "H": H, "段": sg, "身分": role, "進場界": f"{CAL[a0].date()}～{CAL[a1].date()}", "x上限": str(CAL[min(xb, CEND)].date()),
                   "接縫不明(剔除)": seam, **{f"X_{k}": v_ for k, v_ in st.items()},
                   "區塊CI塊數": bk["塊數"] if bk else None, "區塊lo": bk["lo"] if bk else None, "區塊hi": bk["hi"] if bk else None,
                   "區塊結果": bk["結果"] if bk else None,
                   "區塊CI較寬": bool(bk and st.get("n_eff", 0) >= NEFF_MIN and bk["結果"] != st.get("結果")),
                   "R淨平均": float((v["R"] - COST).mean()) if len(v) else None, "R淨中位": float((v["R"] - COST).median()) if len(v) else None,
                   "R勝率(淨>0)": float(((v["R"] - COST) > 0).mean()) if len(v) else None, "對照R平均": float(v["對照R平均"].mean()) if len(v) else None,
                   "對0050平均": float(np.nanmean(d50)) if len(v) else None, "對0050中位": float(np.nanmedian(d50)) if len(v) else None,
                   "贏0050比例": float(np.nanmean(d50 > 0)) if len(v) else None,
                   "遇壞根比例": float((v["typ"] == 3).mean()) if len(v) else None, "遇下市比例": float((v["typ"] == 4).mean()) if len(v) else None,
                   "窗內有減資比例": float(v["窗內有減資"].mean()) if len(v) else None, "對照數<20": int((v["對照數"] < NCTRL).sum()),
                   "池大小中位": float(v["池大小"].median()) if len(v) else None, "不重疊段數": LF.greedy_segments(v["e"].tolist(), H) if len(v) else 0}
            TA.append(row)
    TA = pd.DataFrame(TA)
    log("[甲 判定格] " + "｜".join(f"{r['集合']} H{r['H']} {r['段']} n={r['X_n']} X̄={pct(r.get('X_平均'))} {r.get('X_結果')}"
                                    for _, r in TA[TA["身分"].str.startswith("判定格")].iterrows()))
    # 結果句（甲）
    def jrow(nm, H, sg):
        r = TA[(TA["集合"] == nm) & (TA["H"] == H) & (TA["段"] == sg)]
        return r.iloc[0] if len(r) else None
    SENT = {}
    early_note = TU.NOTE_EARLY
    for nm, lab in (("S1", "營收創新高"), ("S3", "營收創新高且接近一年高點"), ("S2", "接近一年高點"), ("S1_下市補", "營收創新高（加入下市營收 72 家，描述）"),
                    ("S3_下市補", "兩者都有（加入下市營收 72 家，描述）")):
        r1, r2 = jrow(nm, 250, "探索"), jrow(nm, 250, "確認")
        rs = [r1["X_結果"], r2["X_結果"]]
        def word(r):
            res = r["X_結果"]
            return {"結果②": f"多 {pct(r['X_平均'])}", "結果③": f"少 {pct(r['X_平均'])}"}.get(res, f"分不出（X̄ {pct(r['X_平均'])}）")
        cons = "一致" if (rs[0] == rs[1] and rs[0] in ("結果②", "結果③")) else "不一致"
        l7, l12 = jrow(nm, 750, "長窗2005～2021"), jrow(nm, 1250, "長窗2005～2021")
        dir_ = lambda r: ("仍正" if r["X_平均"] > 0 else "轉負") if (r is not None and r["X_n"]) else "—"
        midw = "；樣本中等（n_eff 30～99）" if any(30 <= (r["X_n_eff"] or 0) < 100 for r in (r1, r2)) else ""
        base = (f"{lab}的股票抱 1 年，比同時隨便買：探索 {word(r1)}、確認 {word(r2)}（兩段{cons}）{midw}；"
                f"抱 3 年方向{dir_(l7)}（X̄ {pct(l7['X_平均'])}）、抱 5 年方向{dir_(l12)}（X̄ {pct(l12['X_平均'])}），樣本極少")
        if nm == "S2":
            base = ("接近一年高點（PTH 前 30%）抱 1 年：⛔ 只描述，照引 52 週新高件（回測 1833）「抱 12 個月 ①」——探索 +1.04%、確認 +2.37%，兩段皆分不出；"
                    f"本件 H250 交易日版描述 探索 {word(r1)}、確認 {word(r2)}；抱 3 年方向{dir_(l7)}、5 年方向{dir_(l12)}，樣本極少")
        rr = [jrow(nm, H, "長窗2005～2021") for H in (750, 1250)]
        tail = list(SENT_COMMON) + [f"長抱遇減資、下市的比例：H750 減資 {fmtp(rr[0]['窗內有減資比例'])}、下市 {fmtp(rr[0]['遇下市比例'])}；"
                                     f"H1250 減資 {fmtp(rr[1]['窗內有減資比例'])}、下市 {fmtp(rr[1]['遇下市比例'])}（2015 後營收母體無下市股 ⇒ 下市比例偏低）"] + early_note
        if r1["X_結果"] != r1["X_結果196"] or r2["X_結果"] != r2["X_結果196"]:
            tail.append(f"判定用 Bonferroni 2 格（z＝{ZB2:.3f}）；1.96 時 探索 {r1['X_結果196']}、確認 {r2['X_結果196']}")
        if bool(r1["區塊CI較寬"]) or bool(r2["區塊CI較寬"]):
            tail.append("區塊 CI 較寬、結論不穩")
        SENT[f"甲_{nm}"] = base + "｜" + "；".join(tail)
    J["甲句"] = SENT
    for k, v in SENT.items():
        log(f"[句] {k}：{v}")
    # ── 甲 組合層描述（L15）
    ME = np.array([j for j in range(NC - 1) if CAL[j].month != CAL[j + 1].month] + [CEND], np.int64)
    MEK = {int(MON[j]): k for k, j in enumerate(ME)}
    me50 = c50[np.searchsorted(idx50, ME, "right") - 1]
    r50m = me50[1:] / me50[:-1] - 1.0
    PF = []
    for nm in ("S1", "S2", "S3"):
        T = SETS[nm]
        for H in (250, 750, 1250):
            cohorts = {}
            for s, e in zip(T["sid"], T["e"]):
                e = int(e)
                if e < p05:
                    continue
                S = SS[s]
                ke, kx, ty = exits_vec(S, np.array([e]), np.array([min(e + H - 1, CEND)]), CEND, ne)
                if ty[0] not in (1, 2, 3, 4):
                    continue
                cohorts.setdefault(e, []).append((s, int(ke[0]), int(kx[0])))
            NMM = len(ME); acc = np.zeros(NMM); cnt = np.zeros(NMM)
            for e, lst in cohorts.items():
                k0 = MEK[int(MON[e])]
                endp = max(SS[s]["pos"][kx] for s, ke, kx in lst)
                k1 = MEK[int(MON[endp])]
                vals = np.zeros((len(lst), k1 - k0 + 1))
                for q, (s, ke, kx) in enumerate(lst):
                    S = SS[s]
                    kk = np.searchsorted(S["pos"], ME[k0:k1 + 1], "right") - 1
                    kk = np.minimum(kk, kx)
                    vals[q] = S["cc"][kk] / S["oo"][ke] * (1 - COST)
                Cv = vals.mean(0)
                rr_ = Cv / np.r_[1.0, Cv[:-1]] - 1.0
                acc[k0:k1 + 1] += rr_; cnt[k0:k1 + 1] += 1
            pr = np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0)
            for wl, (m0, m1) in {"早年 2005-01～2014-12": ("2005-01", "2014-12"), "主 2017-03～2026-09": ("2017-03", "2026-09")}.items():
                ks = [k for k in range(1, len(ME)) if m0 <= CAL[ME[k]].strftime("%Y-%m") <= m1]
                pc, pm = ann_stats(pr[ks]); bc, bm_ = ann_stats(r50m[np.array(ks) - 1])
                PF.append({"集合": nm, "H": H, "窗": wl, "月數": len(ks), "無持有月": int((cnt[ks] == 0).sum()), "批數中位": float(np.median(cnt[ks])),
                           "組合年化": pc, "組合最大回落(月)": pm, "0050年化": bc, "0050最大回落(月)": bm_,
                           "年化÷|回落|": pc / abs(pm) if pm else None, "0050年化÷|回落|": bc / abs(bm_) if bm_ else None, "性質": "描述（⛔ 不判、不計 N）"})
    PF = pd.DataFrame(PF)
    log(f"[甲 組合描述] 完成｜{time.time() - t0:.0f}s")
    # ═════════ 乙 ═════════
    MEY = {}
    for Y in range(2004, 2027):
        p_ = cpos_le(f"{Y}-12-31")
        if p_ >= 0 and CAL[p_].year == Y and CAL[p_].month == 12:
            MEY[Y] = p_
    IND_BY = {s: (g["period"].to_numpy(), g["產業別"].fillna("").to_numpy()) for s, g in IND.sort_values("period").groupby("stock_id")}

    def ind_of(s, Y):
        g = IND_BY.get(s)
        if g is None:
            return ""
        ps, vs = g
        k = int(np.searchsorted(ps, f"{Y}-12", "right")) - 1
        return vs[k] if k >= 0 else ""

    gate_c = {(wn, s): np.unpackbits(r["gate"])[:WS[wn]["n0"]].astype(bool) for wn in ("早年", "主") for s, r in RES[wn].items() if r is not None}
    UNIV0 = pd.read_csv(os.path.join(FREQ, "long_univ.csv.gz"), dtype={"sid": str})
    BR = []; BY = []; diff_flags = 0; diff_years = {}
    for Y in range(2007, 2023):
        t = MEY[Y]; t0_ = MEY[Y - 3]; wn = "早年" if t < ne else "主"; off = OFF[wn]
        e = t + 1
        uni = []
        for s in SS:
            g = gate_c.get((wn, s))
            if g is None or not g[t - off]:
                continue
            S = SS[s]; pos = S["pos"]
            kt = int(np.searchsorted(pos, t, "right")) - 1; k0 = int(np.searchsorted(pos, t0_, "right")) - 1
            if kt < 0 or pos[kt] != t or k0 < 0:
                continue
            if S["CB"][kt + 1] - S["CB"][k0 + 1] > 0:
                continue
            uni.append((s, S["cc"][kt] / S["cc"][k0] - 1.0))
        sids = [u[0] for u in uni]; R36 = np.array([u[1] for u in uni], float)
        win = LF.topk_sel(R36, LF.DEC, True); los = LF.topk_sel(R36, LF.DEC, False)
        ref_ = UNIV0[UNIV0["形成年"] == Y].set_index("sid")
        if set(ref_.index) != set(sids):
            raise SystemExit(f"⛔ 乙 {Y} 母體 ≠ 頻率表")
        dW = int((ref_.loc[sids, "贏家"].to_numpy() != win).sum()); dL = int((ref_.loc[sids, "輸家"].to_numpy() != los).sum())
        diff_flags += dW + dL; diff_years[Y] = {"贏家旗標不同": dW, "輸家旗標不同": dL}
        ew_wn = "早年" if e < ne else "主"; We_ = WS[ew_wn]; offe = OFF[ew_wn]
        ent = {}
        for s in sids:
            S = SS[s]; pos = S["pos"]
            kt = int(np.searchsorted(pos, t, "right")) - 1; ke = int(np.searchsorted(pos, e, "right")) - 1
            if ke > kt and S["CB"][ke + 1] - S["CB"][kt + 1] > 0:
                ent[s] = "壞根(t,e]"; continue
            if s not in We_["ix"]:
                ent[s] = "e無成交"; continue
            i = We_["ix"][s]; ew = e - offe
            if not (We_["TRD"][i, ew] and np.isfinite(We_["O"][i, ew]) and We_["O"][i, ew] > 0):
                ent[s] = "e無成交"
            elif We_["UPL"][i, ew]:
                ent[s] = "e開盤鎖漲停"
            else:
                ent[s] = "保留"
        if any(ent[s] != ref_.at[s, "進場"] for s in sids):
            raise SystemExit(f"⛔ 乙 {Y} 進場狀態 ≠ 頻率表")
        inds = [ind_of(s, Y) for s in sids]
        df_ = pd.DataFrame({"sid": sids, "R": R36, "ind": inds})
        g = df_[df_["ind"] != ""].groupby("ind")["R"].agg(["mean", "size"])
        g5 = g[g["size"] >= 5].sort_values("mean", ascending=False)
        top3 = list(g5.index[:3]); bot3 = list(g5.index[::-1][:3])
        keep = [s for s in sids if ent[s] == "保留"]
        for mo in (12, 24, 36):
            xp = MEY[Y + mo // 12]
            for s in keep:
                S = SS[s]
                if not (S["pos"] == e).any():
                    ty = np.array([7]); rv = np.nan          # ★ 世界矩陣有成交、但合併序列沒有該根（該世界 load_bars ＜260 根）⇒ 剔除、照報
                else:
                    ke, kx, ty = exits_vec(S, np.array([e]), np.array([xp]), CEND, ne)
                    rv = float(S["cc"][kx[0]] / S["oo"][ke[0]] - 1.0) if ty[0] in (1, 2, 3, 4) else np.nan
                k_ = sids.index(s)
                BR.append({"形成年": Y, "sid": s, "月": mo, "R": rv, "typ": int(ty[0]), "贏家": bool(win[k_]), "輸家": bool(los[k_]),
                           "產業": inds[k_], "贏家產業": inds[k_] in top3, "輸家產業": inds[k_] in bot3, "R36形成": float(R36[k_])})
        BY.append({"形成年": Y, "母體": len(sids), "保留": len(keep), "贏家產業": "、".join(top3), "輸家產業": "、".join(bot3)})
    BR = pd.DataFrame(BR)
    J["乙_名單與頻率表差異(L11 接縫原始收盤)"] = {"旗標不同合計": diff_flags, "逐年": {str(k): v for k, v in diff_years.items() if v["贏家旗標不同"] or v["輸家旗標不同"]}}
    log(f"[乙 名單] 與頻率表旗標不同 {diff_flags}｜{J['乙_名單與頻率表差異(L11 接縫原始收盤)']['逐年']}")
    NONOV = [2007, 2010, 2013, 2016, 2019, 2022]
    BT = []; BYR = []
    for mo in (12, 24, 36):
        sub = BR[(BR["月"] == mo) & np.isfinite(BR["R"])]
        mk = sub.groupby("形成年")["R"].mean()
        for grp, col in (("個股贏家", "贏家"), ("個股輸家", "輸家"), ("產業贏家", "贏家產業"), ("產業輸家", "輸家產業")):
            v = sub[sub[col]]
            x = v["R"].to_numpy() - mk.loc[v["形成年"]].to_numpy()
            st = stats(x, v["形成年"].to_numpy(), Z196)
            ym = pd.Series(x).groupby(v["形成年"].to_numpy()).mean()
            for Y_, val in ym.items():
                BYR.append({"月": mo, "組": grp, "形成年": int(Y_), "組−市場": float(val), "筆數": int((v["形成年"] == Y_).sum())})
            ymean = float(ym.mean()) if len(ym) else np.nan
            nonov = [float(ym.get(Y_, np.nan)) for Y_ in NONOV]
            same = sum(1 for z in nonov if np.isfinite(z) and np.sign(z) == np.sign(ymean))
            side = "分不出" if st["lo196"] <= 0 <= st["hi196"] else ("落後" if st["平均"] < 0 else "領先")
            BT.append({"月": mo, "組": grp, "量": "組−市場（等權）", "筆數": st["n"], "形成年數": st["群數"], "逐股平均": st["平均"], "形成年等權平均": ymean,
                       "lo": st["lo196"], "hi": st["hi196"], "方向": side, "不重疊6段同號數": same, "一致": "一致" if same >= 4 else "不一致",
                       "遇下市": int((v["typ"] == 4).sum()), "遇壞根": int((v["typ"] == 3).sum()), "接縫不明剔除": int(((BR["月"] == mo) & BR[col] & (BR["typ"] == 6)).sum()),
                       "無進場K棒剔除": int(((BR["月"] == mo) & BR[col] & (BR["typ"] == 7)).sum()),
                       "判定": ("方向判（36 月；只判方向、⛔ 不給合格）" if (mo == 36 and grp in ("個股贏家", "產業贏家")) else "描述")})
        # 贏 − 輸（形成年）
        for a_g, b_g, nm_ in (("贏家", "輸家", "個股贏−輸"), ("贏家產業", "輸家產業", "產業贏−輸")):
            wy = sub[sub[a_g]].groupby("形成年")["R"].mean(); ly_ = sub[sub[b_g]].groupby("形成年")["R"].mean()
            dd = (wy - ly_).dropna()
            BT.append({"月": mo, "組": nm_, "量": "贏組平均−輸組平均（形成年）", "形成年數": int(len(dd)), "形成年等權平均": float(dd.mean()),
                       "lo": float(dd.mean() - 1.96 * dd.std(ddof=1) / np.sqrt(len(dd))), "hi": float(dd.mean() + 1.96 * dd.std(ddof=1) / np.sqrt(len(dd))),
                       "不重疊6段同號數": int(sum(1 for Y_ in NONOV if Y_ in dd.index and np.sign(dd[Y_]) == np.sign(dd.mean()))), "判定": "描述"})
    BT = pd.DataFrame(BT)
    SB = {}
    for grp, lab in (("個股贏家", "股票"), ("產業贏家", "產業")):
        r = BT[(BT["月"] == 36) & (BT["組"] == grp)].iloc[0]
        SB[grp] = (f"過去 3 年漲最多的{lab}，之後 3 年比市場{r['方向']} {pct(r['形成年等權平均'])}（形成年等權；逐股 {pct(r['逐股平均'])}，CI {pct(r['lo'])}～{pct(r['hi'])}），"
                   f"方向{r['一致']}（不重疊 6 段 {int(r['不重疊6段同號數'])} 段同號）；樣本極少、只看方向｜" + "；".join(SENT_COMMON[:2] + [SENT_COMMON[2]]) + "；" + "；".join(early_note))
    J["乙句"] = SB
    for k, v in SB.items():
        log(f"[句] 乙 {k}：{v}")
    # ═════════ 丙 ═════════
    EC = pd.read_csv(os.path.join(FREQ, "events_丙.csv.gz"), dtype={"sid": str, "期別": str})
    if len(EC) != len(S1k):
        raise SystemExit("⛔ events_丙 筆數 ≠ S1 保留")
    CR = []
    for _, rw in EC.iterrows():
        s = rw["sid"]; e = int(rw["e"]); S = SS[s]; pos = S["pos"]
        ke, kx, ty = exits_vec(S, np.array([e, e]), np.array([e + 749, e + 249]), CEND, ne)
        ke = int(ke[0]); kx3, ty3 = int(kx[0]), int(ty[0]); kx1, ty1 = int(kx[1]), int(ty[1])
        base3 = S["cc"][kx3] / S["oo"][ke] - 1.0 if ty3 in (1, 2, 3, 4) else np.nan
        base1 = S["cc"][kx1] / S["oo"][ke] - 1.0 if ty1 in (1, 2, 3, 4) else np.nan
        mddb = mdd_path(np.r_[1.0, S["cc"][ke:kx3 + 1] / S["oo"][ke]]) if np.isfinite(base3) else np.nan
        rec = {"sid": s, "期別": rw["期別"], "e": e, "進場日": rw["進場日"], "窗完整": bool(rw["窗完整"]), "typ3": ty3, "typ1": ty1,
               "抱3年R": base3, "抱1年R": base1, "抱3年MDD": mddb, "抱3年出場日": str(CAL[pos[kx3]].date()) if kx3 >= 0 else ""}
        for F in FS:
            dstr = rw[f"{F}_首次"]
            sold = False; sv = np.nan; ks = -1
            if isinstance(dstr, str) and dstr and np.isfinite(base3):
                d = CP[dstr]
                ks = int(np.searchsorted(pos, d, "right"))
                if ks <= kx3 and ks < len(pos):
                    sold = True; sv = S["oo"][ks] / S["oo"][ke] - 1.0
            rec[f"{F}_賣"] = sold
            if sold:
                rec[f"{F}_賣日"] = str(CAL[pos[ks]].date()); rec[f"{F}_賣出天數"] = int(pos[ks] - e)
                rec[f"{F}_R"] = sv; rec[f"{F}_d"] = sv - base3
                rec[f"{F}_d1"] = (sv - base1) if np.isfinite(base1) else np.nan
                rec[f"{F}_d1alt"] = ((sv if ks <= kx1 else base1) - base1) if np.isfinite(base1) else np.nan
                mx_after = float(S["cc"][ks:kx3 + 1].max()) if ks <= kx3 else np.nan
                rec[f"{F}_之後最高÷賣價−1"] = mx_after / S["oo"][ks] - 1.0
                pre_hi = float(S["cc"][ke:ks].max())
                lim = min(pos[ks] + 249, CEND); kl = int(np.searchsorted(pos, lim, "right")) - 1
                kb = int(S["nxb"][ks + 1]) if ks + 1 < len(S["nxb"]) else 10 ** 9
                kl = min(kl, kb - 1)
                rec[f"{F}_賣後250日又創新高"] = bool(kl >= ks and (S["cc"][ks:kl + 1] > pre_hi).any())
                rec[f"{F}_放棄組"] = S["cc"][kx3] / S["oo"][ks] - 1.0
                rec[f"{F}_MDD"] = mdd_path(np.r_[1.0, S["cc"][ke:ks] / S["oo"][ke], S["oo"][ks] / S["oo"][ke]])
            else:
                rec[f"{F}_R"] = base3; rec[f"{F}_d"] = 0.0 if np.isfinite(base3) else np.nan
                rec[f"{F}_d1"] = (base3 - base1) if (np.isfinite(base1) and np.isfinite(base3)) else np.nan
                rec[f"{F}_d1alt"] = 0.0 if np.isfinite(base1) else np.nan
                rec[f"{F}_MDD"] = mddb
        CR.append(rec)
    CR = pd.DataFrame(CR)
    CR["進場月"] = CR["進場日"].str[:7]
    CSEG = {"全部窗完整": (0, CEND), "早年進場(～2014)": (0, p141231), "2015～進場": (p141231 + 1, CEND), "探索進場(2017-03～2021-12)": (p170302, p211230)}
    TC = []
    for sg, (a0, a1) in CSEG.items():
        sub = CR[(CR["e"] >= a0) & (CR["e"] <= a1) & CR["窗完整"] & np.isfinite(CR["抱3年R"])]
        nseam = int(((CR["e"] >= a0) & (CR["e"] <= a1) & CR["窗完整"] & (CR["typ3"] == 6)).sum())
        for F in FS:
            sold = sub[sub[f"{F}_賣"]]
            st = stats(sub[f"{F}_d"].to_numpy(), sub["進場月"].to_numpy())
            st1 = stats(sub[f"{F}_d1"].to_numpy(), sub["進場月"].to_numpy())
            st1a = stats(sub[f"{F}_d1alt"].to_numpy(), sub["進場月"].to_numpy())
            stv = stats(sold[f"{F}_d"].to_numpy(), sold["進場月"].to_numpy()) if len(sold) else {"n": 0}
            TC.append({"進場段": sg, "法": F, "說明": FNAME[F], "事件(窗完整)": int(len(sub)), "接縫不明剔除": nseam, "觸發賣出": int(len(sold)),
                       "觸發率": float(len(sold) / len(sub)) if len(sub) else None,
                       "d平均(加賣法−抱3年)": st.get("平均"), "d中位": st.get("中位"), "d_lo": st.get("lo196"), "d_hi": st.get("hi196"), "d結果(描述)": st.get("結果196"),
                       "d_n_eff": st.get("n_eff"),
                       "被賣者d平均": stv.get("平均"), "被賣者d中位": stv.get("中位"),
                       "d1平均(對抱1年)": st1.get("平均"), "d1_lo": st1.get("lo196"), "d1_hi": st1.get("hi196"),
                       "d1′平均(1年窗另一讀法)": st1a.get("平均"), "d1′_lo": st1a.get("lo196"), "d1′_hi": st1a.get("hi196"),
                       "賣出天數中位": float(sold[f"{F}_賣出天數"].median()) if len(sold) else None,
                       "之後最高÷賣價−1 中位": float(sold[f"{F}_之後最高÷賣價−1"].median()) if len(sold) else None,
                       "賣在之後最高之上比例": float((sold[f"{F}_之後最高÷賣價−1"] <= 0).mean()) if len(sold) else None,
                       "賣後250日又創新高比例": float(sold[f"{F}_賣後250日又創新高"].mean()) if len(sold) else None,
                       "放棄組平均": float(sold[f"{F}_放棄組"].mean()) if len(sold) else None, "放棄組中位": float(sold[f"{F}_放棄組"].median()) if len(sold) else None,
                       "MDD中位(加賣法)": float(sub[f"{F}_MDD"].median()), "MDD中位(抱3年)": float(sub["抱3年MDD"].median()),
                       "MDD成對差平均(加賣法−抱3年)": float((sub[f"{F}_MDD"] - sub["抱3年MDD"]).mean()),
                       "抱3年R淨平均": float((sub["抱3年R"] - COST).mean()), "抱3年遇下市": int((sub["typ3"] == 4).sum()), "抱3年遇壞根": int((sub["typ3"] == 3).sum()),
                       "性質": "描述（不計 N）"})
    TC = pd.DataFrame(TC)
    SC = {}
    for F in FS:
        r = TC[(TC["進場段"] == "全部窗完整") & (TC["法"] == F)].iloc[0]
        w = {"結果②": "多", "結果③": "少"}.get(r["d結果(描述)"], "分不出")
        SC[F] = (f"長線抱著時，用 {F}（{FNAME[F]}）賣比抱 3 年{w} {pct(r['d平均(加賣法−抱3年)'])}（描述；CI {pct(r['d_lo'])}～{pct(r['d_hi'])}；觸發率 {fmtp(r['觸發率'])}；"
                 f"對抱 1 年 {pct(r['d1平均(對抱1年)'])}）｜" + "；".join((SENT_C if F in ("F4", "F5", "F6", "F7") else []) + SENT_COMMON + early_note + [SENT_373]))
    J["丙句"] = SC
    for k, v in SC.items():
        log(f"[句] 丙 {k}：{v}")
    # ═════════ 先驗 ═════════
    def g_(nm, H, sg, col):
        r = jrow(nm, H, sg)
        return None if r is None else r[col]
    PR = []
    a1 = [g_("S1", 250, s_, "X_結果") for s_ in ("探索", "確認")]
    PR.append({"先驗": "① 甲 S1 抱 1 年兩段皆②（約四成五）", "結果": "、".join(a1), "中": all(x == "結果②" for x in a1)})
    s2d = [g_("S2", H, "長窗2005～2021", "X_平均") for H in (750, 1250)]; md = [g_("M", H, "長窗2005～2021", "X_平均") for H in (750, 1250)]
    PR.append({"先驗": "② 甲 S2 3、5 年方向 ＞0，M 3、5 年方向 ＜0（約五成）", "結果": f"S2 {pct(s2d[0])}／{pct(s2d[1])}；M {pct(md[0])}／{pct(md[1])}",
               "中": all(x > 0 for x in s2d) and all(x < 0 for x in md)})
    m5 = {nm: g_(nm, 1250, "長窗2005～2021", "對0050中位") for nm in ("S1", "S2", "S3")}
    PR.append({"先驗": "③ 甲 抱 5 年對 0050 的單筆中位 ＜0（約六成五）", "結果": "；".join(f"{k} {pct(v)}" for k, v in m5.items()), "中": all(v < 0 for v in m5.values())})
    bw = BT[(BT["月"] == 36) & (BT["組"] == "個股贏家")].iloc[0]; bi = BT[(BT["月"] == 36) & (BT["組"] == "產業贏家")].iloc[0]
    PR.append({"先驗": "④ 乙 個股贏家之後 3 年落後市場（約六成）；產業贏家之後 3 年落後（約五成五）",
               "結果": f"個股 {bw['方向']} {pct(bw['形成年等權平均'])}（{bw['一致']}）；產業 {bi['方向']} {pct(bi['形成年等權平均'])}（{bi['一致']}）",
               "中": f"個股 {'中' if bw['方向'] == '落後' else '不中'}；產業 {'中' if bi['方向'] == '落後' else '不中'}"})
    c3 = TC[(TC["進場段"] == "全部窗完整") & TC["法"].isin(["F1", "F2", "F3"])]
    PR.append({"先驗": "⑤ 丙 三種賣法（F1～F3）都不比抱 3 年好（約六成）★「不比較好」＝ 非（d ＞0 且 CI 不含 0）",
               "結果": "；".join(f"{r['法']} {pct(r['d平均(加賣法−抱3年)'])}（{r['d結果(描述)']}）" for _, r in c3.iterrows()),
               "中": bool(all(r["d結果(描述)"] != "結果②" for _, r in c3.iterrows()))})
    f7 = TC[(TC["進場段"] == "全部窗完整") & (TC["法"] == "F7")].iloc[0]
    PR.append({"先驗": "⑥ F7 不比抱 3 年好，但最大回落較淺（約五成五）；F7 觸發率 ＜15%（約六成）",
               "結果": f"d {pct(f7['d平均(加賣法−抱3年)'])}（{f7['d結果(描述)']}）；MDD 成對差 {pct(f7['MDD成對差平均(加賣法−抱3年)'])}；觸發率 {fmtp(f7['觸發率'])}",
               "中": f"前半 {'中' if (f7['d結果(描述)'] != '結果②' and f7['MDD成對差平均(加賣法−抱3年)'] > 0) else '不中'}；觸發率 {'中' if f7['觸發率'] < 0.15 else '不中'}"})
    PR = pd.DataFrame(PR)
    for _, r in PR.iterrows():
        log(f"[先驗] {r['先驗']}｜{r['結果']}｜{r['中']}")
    # ═════════ 輸出 ═════════
    J["甲表摘要"] = TA[TA["身分"].str.startswith("判定格")][["集合", "H", "段", "X_n", "X_n_eff", "X_平均", "X_lo", "X_hi", "X_結果", "X_結果196", "區塊結果"]].to_dict("records")
    J["必附"] = SENT_COMMON + early_note + SENT_C + [SENT_373]
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    TA.to_csv(os.path.join(OUT, "甲_表.csv"), index=False, encoding="utf-8-sig")
    TA[TA["集合"].isin(["S1", "S1_下市補", "S3", "S3_下市補"]) & TA["H"].isin([120, 250, 750])].to_csv(os.path.join(OUT, "甲_下市補.csv"), index=False, encoding="utf-8-sig")
    PF.to_csv(os.path.join(OUT, "甲_組合描述.csv"), index=False, encoding="utf-8-sig")
    BT.to_csv(os.path.join(OUT, "乙_表.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BYR).merge(pd.DataFrame(BY), on="形成年", how="left").to_csv(os.path.join(OUT, "乙_年.csv"), index=False, encoding="utf-8-sig")
    TC.to_csv(os.path.join(OUT, "丙_表.csv"), index=False, encoding="utf-8-sig")
    PR.to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    EA.to_csv(os.path.join(OUT, "events_甲.csv.gz"), index=False, compression="gzip")
    BR.to_csv(os.path.join(OUT, "events_乙.csv.gz"), index=False, compression="gzip")
    CR.to_csv(os.path.join(OUT, "events_丙.csv.gz"), index=False, compression="gzip")
    json.dump(J, open(os.path.join(OUT, "long3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

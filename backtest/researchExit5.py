# -*- coding: utf-8 -*-
"""PREREG營量營飆出場五法 seq1（台股策略線登錄 sha e59718354bec67e0，2026-10-12 22:04；裁定 seq343 發號 N_組合 ＋5、事後重切、最多暫定）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit5 [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit5_check [--procs 3]

⭐ 讀法寫死：TIME（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本件數字
   看過的：登錄全文 seq1、裁定 seq343（經回測線轉述：主臂、不設上限只描述、相對門檻判定、判定照 seq342）、既有程式 researchAddOn／researchYL_flowexit／
   researchYL_truetopT／researchAddOn_truetop_peak／researchAddOn_neartop／researchYL_integrate／research11.simulate_mtm／research34（營收）；
   ⚠ 回測線看過營量 v1／營飆 v1 各段年化與回落、舊出場研究；⛔ 沒看過本件五法任何輸出

═══ 讀法（X 標；登錄沒寫清楚、執行者補的都在這裡）═══
 X0 判定（seq342 口徑、裁定 seq343）：每法 × 每策略各自：「改出場版」對「原策略」變好 ＝ 年化較高 且 年化÷|回落| ≥ 原策略；探索 2017-03-02～2021-12-30、
    確認 2022-01-03～2026-08-24 兩段都要；營飆 ＝ 200 顆中位（年化中位、回落中位、比值 ＝ 年化中位 ÷ |回落中位|，同 researchAddOn），另報逐顆變好顆數比例（描述）
    法 1：E1a（2×ATR）、E1b（4×ATR）探索段挑比值較高者（非退化格先；同 ⇒ 年化高 ⇒ E1a），判定 ＝ 挑中格探索、確認兩段都變好；早年 2005-02～2014-12 只描述
    結果 ＝「變好（暫定）」或「沒有變好（探索段就沒變好／確認段沒變好）」；退化格（X8）⇒「退化、不判」
 X1 原策略、世界、引擎（⛔ 不改）：世界 ＝ researchAddOn 的快取 ~/addonwork/world_{主,早年}.pkl（＝ researchYL_integrate.main_world／early_world）
    營量 v1 ＝ SIG[無閘]、H60、20 槽、relvol（default_rng(7000＋0)，log=[]、d_max None、queue 0）；營飆 v1 ＝ SIG[閘]、H120、10 槽、抽籤 default_rng(1000＋r)，r ＝ 0～199
    停止交易強制出場開（W["SF"]）；改出場一律走引擎 held_map（researchYL_flowexit／truetopT 同一條管線）：每列候選訊號（formal xpos ≥ 0）用自己的價格鍵「代號#進場位置」，
    合成收盤 ＝ 還在抱的部分 × 當日收盤 ＋ 已賣部分 × 賣價；xpos ＝ 最後一個部分出場那天；g ＝ Σ 權重 × 出場價 ÷ 進場價 − 1；名額、排序、抽籤、成本、停止交易全照正式引擎
    ⭐ 整筆賣：xpos ＝ 賣出那天 ⇒ 引擎在那天開盤前結清、名額當天就可以給當天（含）以後的候選（＝ 原引擎「排程出場 → 新部位」同日順序；不是縮放近似）
    ⭐ 賣一半（法 4、法 5、描述臂）：賣掉的一半價值凍結在賣價（報酬 0、⛔ 不拿去買別檔）、名額到剩下一半出清那天才釋出、成本在最後出清時一次扣整筆來回
      （每一塊買進的錢付一次 COST，金額相同、只差扣的時點）＝ 登錄「那一半現金留著，等該持股剩下部分出清時一起併回、照原規則補候選」
    閘 ① 原策略（A 走 held_map、合成收盤 ＝ 原收盤）權益 sha ＝ resultsYL_integrate/seeds.csv.gz（同世界、同格、同 r）；閘 ② ＝ IG.eng 直接跑的權益逐位元相同
 X2 時序（登錄 §一）：訊號判斷用收盤（訊號日 d），動作 ＝ d 之後第一根「有效 K 棒且開盤有限 ＞ 0」的開盤（X）；有效 K 棒 ＝ research11.load_bars 的 traded；
    價格 ＝ 世界 closes／opens（引擎同一份還原價，ffill）；判斷期 d ∈ [e, X上限 − 1]，X ≤ X上限 才賣：正常列 X上限 ＝ 正式出場根 xf（xf 開盤早於 xf 收盤）；
    資料尾補回列（xf ＝ 資料尾後墊根）X上限 ＝ 資料尾；有停止交易 L ⇒ X上限 ＝ min(·, L)；第一個成立的訊號日沒有可賣開盤（X 不存在或 ＞ X上限）⇒ 該法對該筆不賣（照正式）
    每筆每法只動作一次（法 4、法 5 賣一半後剩下照主臂；描述臂「MA5 先半再清」除外，見 X7）
 X3 壞根（seq335 全線，同 researchAddOn U4 的集合）：主世界 ＝ ~/crashwork/bad_main.pkl（load_bars 壞根 ∪ adj 減資／面額）；早年 ＝ bad_early.pkl ∪ R8 事件恢復日 ∪ reduce_v2
    （上市偵測、上櫃偵測、未解釋 22 筆）——直接呼叫 researchAddOn.market 取得；任何部分的出場日 ≥ 進場後第一個壞根 kb ⇒ 改成 kb 前最後一根有效 K 棒收盤強制賣
    （正式出場本身也照這條；正式訊號建構已保證窗內沒有 load_bars 壞根 ⇒ 只有 adj／reduce_v2 另加的才可能碰到，筆數照報；沒觸發的列若因此與原策略不同，筆數照報）
 X4 法 1 移動停利：M_d ＝ [e, d] 有效 K 棒最高收盤（含買進日 e）；ATR ＝ 訊號根（e 前一根有效 K 棒，SIG pos）往前 20 根有效 K 棒的真實區間平均
    （TR_j ＝ max(高_j, 收_{j−1}) − min(低_j, 收_{j−1})，load_bars 還原高低收；⚠ 用簡單平均、不用 Wilder 遞迴：20 根全落在正式訊號「k−20 起無壞根」的範圍內）
    E1a：收盤 ≤ M − 2×ATR；E1b：收盤 ≤ M − 4×ATR；ATR 不可得（NaN）⇒ 該列不判（筆數照報）
 X5 法 2：MA5 ＝ 含 d 的最近 5 根有效 K 棒收盤平均；d 是有效 K 棒且 [e, d] 有效 K 棒數 ≥ 6（前 5 根不判）且 收盤 ＜ MA5
 X6 法 3：月營收 ＝ D.DATA/mops/revenue_hist（本庫彙總表；research34.load_revenue 同式：當月營收、去年當月營收，同代號同期別留最後一列）；主世界 ＝ edc6f 快照、
    早年 ＝ eotc_f65bb03e11 版面（2003-01～2014-12，早年日曆止於 2014-12-31 ⇒ 夠用）
    年增 ＝ 當月 ÷ 去年當月 − 1（去年當月 ＞ 0 才可判）；可得日 A(p) ＝ 期別 p 次月 10 日（p ≤ 2025-12）／15 日（p ≥ 2026-01）之後第一個交易日（research34.rebalance_dates 的 e 同式，side=right）
    持有中新公布 ＝ A(p) ≥ e；訊號日 d ＝ A(p)（可得日收盤知道）⇒ X ＝ A 之後第一個有效開盤（＝ 登錄「可得日隔天開盤賣」）；依 A 先後第一個年增 ≤ 0 的期別觸發
 X7 法 4：同 researchAddOn A2（h ＝ d − e ＋ 1 日曆位置、h ≥ 10、(e, d] 無壞根、d 有效 K 棒、q99(h, d) 由 researchAddOn.market／thresholds 同一份 R1 與門檻、母體 ≥ 20）
    g ＝ 收盤[d] ÷ 進場價 − 1 ≥ q99 ⇒ X 賣一半；⚠ 動作日照 X2 統一規則（第一個成立日之後第一個有效開盤），⛔ 不用 AddOn「t＋1 沒開盤就改天再判」
    法 5：d ≥ e＋1、d 有效 K 棒且非壞根；r ＝ 收盤[d] ÷ 收盤[d−1] − 1（日曆前一根、ffill 收盤；同母體 h＝1 口徑）；q2(d) ＝ 當天 R1 母體（有 K 棒、C[d−1] 有值、d 非壞根）
    同式報酬的第 2 百分位（np.nanpercentile 線性；母體 ＜ 20 不判）；r ≤ q2 且 r ＜ 0 ⇒ X 賣一半
    描述臂（⛔ 不判、不計 N）：D1_5／D1_10 收盤 ≤ (1 − 5%／10%) × M_d 整筆；D2 MA5 第一次跌破（X5）賣一半、之後「再跌破」（前一根有效 K 棒收盤 ≥ 其 MA5、這根 ＜ MA5 的新一次跌破）
    出清、沒有再跌破剩下照主臂；D3 新公布月營收「不再創 24 個月新高」（research34 rev_hi24：當月 ≥ 前 24 期最高、24 期齊全才可判；可判且不是新高）整筆；
    D4 持有報酬 ≥ +100% 賣一半；D5 單日還原報酬 ＜ −5% 賣一半（d ≥ e＋1）；N1a／N1b／N2／N3 ＝ E1a／E1b／E2／E3 不設最長天數（只靠條件賣；沒觸發 ⇒ 抱到資料尾、
    照 T1 以資料尾收盤計值；壞根、停止交易照 X3、引擎）
 X8 退化（seq325：先寫 degeneracy.json 附台北時間，再算任何報酬）：每格探索段（營飆 200 顆中位）平均持股 ＜ 3 或 現金比例 ＞ 30% ⇒ 退化；
    現金比例 ＝ 1 − 段內平均（持股市值 − 已賣一半凍結的錢）÷ 權益（凍結的一半算現金）；原策略同段已達同一條 ⇒ 該條對該策略不適用（照報原策略數值），只看另一條
 X9 必報（登錄 §四）：
    ① 觸發比例（占持股，逐年）：改出場版實際買進的每一筆（依買進年；營飆 200 顆合計）中「該法真的提早動作（賣出早於正式、⛔ 不含壞根強制）」的比例
    ② 提早賣那幾筆 改出場 − 原出場 報酬差（各自含停止交易調整的實際 g；中位、前 10%（p90）、後 10%（p10）；營飆 200 顆合併、另報去重）
    ③ 賣出點距整段最高點：同 researchAddOn_truetop_peak（t ＝ 訊號日起漲點 truetopT.anchor_pit(c, d, e)、P ＝ 起漲點起到第一次從高點回落 30% 為止最高收盤；重用 peak／rowstats／describe）
      ⇒ 主窗、唯一列（去重）；賣價 ＝ X 開盤
    ④ 賣出後 60 個交易日內又創新高：[X, X＋59] 有效 K 棒最高收盤 ＞ [e, d] 最高收盤（窗不滿 60 根不計、遇壞根截斷照 neartop）；另報原出場（(xf, xf＋60]、比持有期最高）對照
    ⑤ 平均持有天數變化（賣出日 − 買進日，日曆位置；賣一半另報按股數加權）；⑥ 換手（每年買進金額 ÷ 段內平均權益）與成本（換手 × 0.585%）
    ⑦ 組合層最大回落變化；⑧ T2：researchAddOn.t2_first（月底 D ＝ NAV ÷ 段首起最高 − 1；營量 −34.4%／−27.5%，營飆 −56.1%／−44.9%）原 vs 改出場；營飆逐顆分類
 結果句必附：「營量、營飆已看過結果，本件最多暫定」「買進照正式規則，只換賣法」；早年附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註
輸出 backtest/resultsExit5/：degeneracy.json（先寫）、Exit5.json、Exit5_main.csv、seeds.csv.gz、rows_{世界}_{策略}.csv.gz（逐列出場）、run.log；大檔 ~/exit5work/
── 事後註（寫死之後、照實記；讀法沒改）──
 ① 22:2x 跑過一次 3 顆煙霧測試（EX5_QUICK，輸出 /tmp/exit5_quick，數字不是本件結果；⚠ 營量只有 r0 一條 ⇒ 煙霧測試已含營量完整數字，照記）；
    之前只修語法（f-string）；煙霧測試之後本檔 ⛔ 沒有改任何計算；查核檔修了自己的兩個錯（np.bool_ 判 is False、D2 條件對照表）
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

TIME = "2026-10-12 22:19（台北）"
REG_SHA = "e59718354bec67e0"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsExit5"
WORK = os.path.expanduser("~/exit5work")
NSEED = 200
if os.environ.get("EX5_QUICK"):                                  # 煙霧測試（不是交件）
    NSEED, OUT, WORK = 3, "/tmp/exit5_quick", "/tmp/exit5_quick/work"
COST = R.COST
STR = {"營量": {"H": 60, "N": 20, "G": False, "key": IG.YL}, "營飆": {"H": 120, "N": 10, "G": True, "key": IG.YF}}
JUDGED = ("E1a", "E1b", "E2", "E3", "E4", "E5")
DESC = ("D1_5", "D1_10", "D2", "D3", "D4", "D5", "N1a", "N1b", "N2", "N3")
VARS = ("A",) + JUDGED + DESC
VNAME = {"A": "原策略", "E1a": "法1 移動停利 2×ATR", "E1b": "法1 移動停利 4×ATR", "E2": "法2 跌破5日線", "E3": "法3 營收年增≤0",
         "E4": "法4 漲多(R1 q99)賣一半", "E5": "法5 單日大跌(R1 最低2%)賣一半",
         "D1_5": "描述 回落5%", "D1_10": "描述 回落10%", "D2": "描述 MA5先半再清", "D3": "描述 營收不再創24月新高", "D4": "描述 +100%賣一半",
         "D5": "描述 單日<−5%賣一半", "N1a": "描述 E1a不設最長天數", "N1b": "描述 E1b不設最長天數", "N2": "描述 E2不設最長天數", "N3": "描述 E3不設最長天數"}
HALF = {"E4", "E5", "D2", "D4", "D5"}
METHODS = {"法1": ("E1a", "E1b"), "法2": ("E2",), "法3": ("E3",), "法4": ("E4",), "法5": ("E5",)}
SEGS = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
T2 = {"營量": (-0.344, -0.275), "營飆": (-0.561, -0.449)}
DEG_HOLD, DEG_CASH = 3.0, 0.30
Q2PCT, MINPOP = 2.0, 20
SENT = ["營量、營飆已看過結果，本件最多暫定", "買進照正式規則，只換賣法"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）", "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
_G: dict = {}


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


def seeds_of(sn):
    return [0] if sn == "營量" else list(range(NSEED))


# ═════════════ 價格與逐股陣列 ═════════════
def bars_job(a):
    sid, mk = a
    D.DATA = _G["data"]
    B = R.load_bars(sid, mk, _G["cal"])
    if B is None:
        return sid, None
    return sid, (B["idx"], B["h"], B["l"], B["c"])


def stock_pack(W, sid, LB, HB, n0, NP):
    c = np.asarray(W["closes"][sid], float)[:n0]; o = np.asarray(W["opens"][sid], float)[:n0]
    idx = LB[0]; idx = idx[idx < n0]
    bar = np.zeros(n0, bool); bar[idx] = True
    okop = bar & np.isfinite(o) & (o > 0)
    nxt = np.full(n0 + 2, -1, np.int64)
    for p in range(n0 - 1, -1, -1):
        nxt[p] = p if okop[p] else nxt[p + 1]
    bad = np.asarray(HB[sid][1], bool)[:NP].copy()
    nbad = np.full(NP + 1, -1, np.int64)
    for p in range(NP - 1, -1, -1):
        nbad[p] = p if bad[p] else nbad[p + 1]
    # MA5（有效 K 棒序列）
    cb = c[idx]; ma5 = np.full(n0, np.nan)
    if len(idx) >= 5:
        m = pd.Series(cb).rolling(5, min_periods=5).mean().to_numpy(); ma5[idx] = m
    prevbar = np.full(n0, -1, np.int64); prevbar[idx[1:]] = idx[:-1]
    cumbar = np.cumsum(bar)
    r1 = np.full(n0, np.nan); r1[1:] = c[1:] / c[:-1] - 1.0
    return {"c": c, "o": o, "bar": bar, "nxt": nxt, "bad": bad, "nbad": nbad, "ma5": ma5, "prevbar": prevbar, "cumbar": cumbar, "r1": r1, "idx": idx,
            "lb": LB}


def atr20(pk, pos):
    idx, h, l, c = pk["lb"]
    k = int(np.searchsorted(idx, pos))
    if k >= len(idx) or idx[k] != pos or k < 20:
        return np.nan, k
    tr = [max(h[j], c[j - 1]) - min(l[j], c[j - 1]) for j in range(k - 19, k + 1)]
    return float(np.mean(tr)), k


# ═════════════ 營收 ═════════════
def load_revenue(data):
    fs = sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df["rev_ly"] = pd.to_numeric(df["去年當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    rly = df.pivot(index="period", columns="stock_id", values="rev_ly").sort_index()
    return rev, rly, {"檔案數": len(fs), "期別": [str(rev.index[0]), str(rev.index[-1])], "列": int(len(df))}


def avail_pos(periods, cal):
    out = {}
    for p in periods:
        y, m = int(p[:4]), int(p[5:])
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        day = 10 if p <= "2025-12" else 15
        e = int(cal.searchsorted(pd.Timestamp(year=y2, month=m2, day=day), side="right"))
        out[p] = e
    return out


def rev_events(sid, rev, rly, AV, n0):
    """⇒ 依可得日排序 [(A, yoy, hi24)]；yoy／hi24 不可判 ⇒ NaN／None。"""
    if sid not in rev.columns:
        return []
    rv = rev[sid].to_numpy(float); rl = rly[sid].to_numpy(float); per = list(rev.index)
    ev = []
    for k, p in enumerate(per):
        if not np.isfinite(rv[k]):
            continue
        A = AV[p]
        if A >= n0:
            continue
        yoy = rv[k] / rl[k] - 1.0 if (np.isfinite(rl[k]) and rl[k] > 0) else np.nan
        hist = rv[max(0, k - 24):k]
        hi = bool(rv[k] >= hist.max()) if (len(hist) == 24 and np.isfinite(hist).all()) else None
        ev.append((A, yoy, hi))
    ev.sort(key=lambda z: z[0])
    return ev


# ═════════════ 逐列出場 ═════════════
def tk(p, n0):
    k, d = p[0], p[1]
    return 2 * d if k == "open" else (2 * d + 1 if k == "close" else 2 * n0)


def first_sale(cond_days, pk, Xcap):
    """cond_days：依序的候選訊號日（已過濾）⇒ (d, X) 或 (d, None)（第一個成立日沒有可賣開盤）或 (None, None)。"""
    for d in cond_days:
        X = int(pk["nxt"][d + 1]) if d + 1 < len(pk["nxt"]) else -1
        if X < 0 or X > Xcap:
            return int(d), None
        return int(d), X
    return None, None


def row_variants(W, pk, sid, e, xf, gf, bp, L, pos, ctxm):
    """⇒ {v: rec}、info。rec ＝ parts[(w, (kind, day, px, dlast))]、trig、d、X、bad。"""
    n0 = ctxm["n0"]; c = pk["c"]; bar = pk["bar"]
    # X 上限（X2）
    if xf < n0:
        Xcap = xf
    else:
        Xcap = n0 - 1
    if L is not None:
        Xcap = min(Xcap, L)
    XcapN = n0 - 1 if L is None else min(n0 - 1, L)
    pf = ("close", xf, bp * (1 + gf), xf) if xf < n0 else ("end", n0, bp * (1 + gf), n0 - 1)
    pend = ("end", n0, float(c[n0 - 1]), n0 - 1)
    # 壞根（X3）
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
    # 判斷日（X2）
    def days(lo, hi):
        hi = min(hi, n0 - 1)
        if hi < lo:
            return np.zeros(0, np.int64)
        return np.arange(lo, hi + 1)
    dStd = days(e, Xcap - 1); dN = days(e, XcapN - 1)
    # 共用序列
    cc = c.copy()
    Mrun = np.full(n0, np.nan)
    seg = np.where(bar[e:], c[e:], -np.inf); Mrun[e:] = np.maximum.accumulate(seg)
    atr, kk = atr20(pk, pos)
    out = {}; info = {"ATR": atr, "k": kk, "kb": kb, "Xcap": Xcap}

    def whole(cond, dd, Xc, base):
        cand = dd[cond[dd]] if len(dd) else dd
        d, X = first_sale(cand, pk, Xc)
        if X is not None:
            p = ("open", X, float(pk["o"][X]), X - 1)
            if tk(p, n0) < tk(base, n0):
                return [(1.0, p)], d, X
        return [(1.0, base)], d, None

    def half(cond, dd, base):
        cand = dd[cond[dd]] if len(dd) else dd
        d, X = first_sale(cand, pk, Xcap)
        if X is not None:
            p = ("open", X, float(pk["o"][X]), X - 1)
            if tk(p, n0) < tk(base, n0):
                return [(0.5, p), (0.5, base)], d, X
        return [(0.5, base), (0.5, base)], d, None

    with np.errstate(invalid="ignore"):
        trailA = bar & (cc <= Mrun - 2 * atr) if np.isfinite(atr) else np.zeros(n0, bool)
        trailB = bar & (cc <= Mrun - 4 * atr) if np.isfinite(atr) else np.zeros(n0, bool)
        tr5 = bar & (cc <= 0.95 * Mrun); tr10 = bar & (cc <= 0.90 * Mrun)
        below = bar & (cc < pk["ma5"])
        nb_ok = np.zeros(n0, bool)
        cnt = pk["cumbar"] - (pk["cumbar"][e - 1] if e > 0 else 0)
        nb_ok[e:] = cnt[e:] >= 6
        ma5c = below & nb_ok
        g = cc / bp - 1.0
        dbl = bar & (g >= 1.0)
        r1 = pk["r1"]
        drop5 = bar & ~pk["bad"][:n0] & (r1 < -0.05)
    drop5[:e + 1] = False
    # 法 3 營收
    REV = ctxm["REV"].get(sid, [])
    def revcond(kind, Xc):
        dd = []
        for A, yoy, hi in REV:
            if A < e or A > Xc - 1:
                continue
            if kind == "yoy" and np.isfinite(yoy) and yoy <= 0:
                dd.append(A)
            elif kind == "hi" and hi is False:
                dd.append(A)
        return dd
    # 法 4／5 門檻
    Q = ctxm["Q99"]; Q2 = ctxm["Q2"]; nQ = Q.shape[1]
    c4 = np.zeros(n0, bool); c5 = np.zeros(n0, bool)
    if len(dStd):
        T = dStd[dStd >= e + 9]
        if len(T):
            h = T - e + 1
            nbd = np.array([pk["nbad"][e + 1] if e + 1 < len(pk["nbad"]) else -1] * len(T))
            okb = (nbd < 0) | (nbd > T)
            q = np.full(len(T), np.nan); inT = (T < nQ) & (h < Q.shape[0])
            q[inT] = Q[h[inT], T[inT]]
            hit = bar[T] & okb & np.isfinite(q) & (g[T] >= q)
            c4[T[hit]] = True
        T = dStd[dStd >= e + 1]
        if len(T):
            q2 = Q2[T]
            hit = bar[T] & ~pk["bad"][T] & np.isfinite(q2) & np.isfinite(r1[T]) & (r1[T] <= q2) & (r1[T] < 0)
            c5[T[hit]] = True
            info["q2_ok"] = int(np.isfinite(q2).sum())
    # 組合
    parts = {"A": ([(1.0, pf)], None, None)}
    parts["E1a"] = whole(trailA, dStd, Xcap, pf); parts["E1b"] = whole(trailB, dStd, Xcap, pf)
    parts["E2"] = whole(ma5c, dStd, Xcap, pf)
    ev = revcond("yoy", Xcap); d3, X3 = first_sale(ev, pk, Xcap)
    parts["E3"] = ([(1.0, ("open", X3, float(pk["o"][X3]), X3 - 1))], d3, X3) if (X3 is not None and tk(("open", X3), n0) < tk(pf, n0)) else ([(1.0, pf)], d3, None)
    parts["E4"] = half(c4, dStd, pf); parts["E5"] = half(c5, dStd, pf)
    parts["D1_5"] = whole(tr5, dStd, Xcap, pf); parts["D1_10"] = whole(tr10, dStd, Xcap, pf)
    # D2：第一次跌破賣一半、新一次跌破出清
    pp, d1, X1 = half(ma5c, dStd, pf)
    if X1 is not None:
        pv = pk["prevbar"]
        fresh = below.copy(); fresh[:d1 + 1] = False
        ok = np.zeros(n0, bool); ii = np.flatnonzero(fresh)
        for j in ii:
            q_ = pv[j]
            ok[j] = q_ >= 0 and not below[q_]
        cand = dStd[ok[dStd]] if len(dStd) else dStd
        d2, X2 = first_sale(cand, pk, Xcap)
        if X2 is not None:
            p2 = ("open", X2, float(pk["o"][X2]), X2 - 1)
            if tk(p2, n0) < tk(pf, n0):
                pp = [pp[0], (0.5, p2)]
    parts["D2"] = (pp, d1, X1)
    ev = revcond("hi", Xcap); d3h, X3h = first_sale(ev, pk, Xcap)
    parts["D3"] = ([(1.0, ("open", X3h, float(pk["o"][X3h]), X3h - 1))], d3h, X3h) if (X3h is not None and tk(("open", X3h), n0) < tk(pf, n0)) else ([(1.0, pf)], d3h, None)
    parts["D4"] = half(dbl, dStd, pf); parts["D5"] = half(drop5, dStd, pf)
    parts["N1a"] = whole(trailA, dN, XcapN, pend); parts["N1b"] = whole(trailB, dN, XcapN, pend)
    parts["N2"] = whole(ma5c, dN, XcapN, pend)
    evN = revcond("yoy", XcapN); dN3, XN3 = first_sale(evN, pk, XcapN)
    parts["N3"] = ([(1.0, ("open", XN3, float(pk["o"][XN3]), XN3 - 1))], dN3, XN3) if XN3 is not None else ([(1.0, pend)], dN3, None)
    for v, (pl, d, X) in parts.items():
        fx = [(w, fix(p)) for w, p in pl]
        bd = int(any(f[1] for _, f in fx)); pl2 = [(w, f[0]) for w, f in fx]
        trig = int(X is not None and any(p[0] == "open" and p[1] == X for _, p in pl2))
        out[v] = {"parts": pl2, "d": d, "X": X if trig else None, "trig": trig, "bad": bd}
    return out, info


def finalize(rec, pk, bp, n0, NP, L, orig_arr):
    """⇒ xpos、g（含停止交易）、Sc（合成收盤，與原陣列相同時回傳原陣列）、天數（按股數加權、最後出清）。"""
    pl = rec["parts"]
    c = pk["c"]
    fin = max(pl, key=lambda wp: tk(wp[1], n0))[1]
    xpos = fin[1]
    g = sum(w * p[2] for w, p in pl) / bp - 1.0
    tt = np.arange(NP); cc = np.r_[c, np.full(NP - n0, c[n0 - 1])] if NP > n0 else c
    Sc = np.zeros(NP)
    for w, p in pl:
        Sc += w * np.where(tt <= p[3], cc[:NP], p[2])
    xe, ge, sf = xpos, g, 0                                   # 經濟口徑（含停止交易：引擎在 L＋1 以合成收盤[L] 強制）
    if L is not None and xpos > L + 1:
        xe = L + 1; ge = float(Sc[L]) / bp - 1.0; sf = 1
    return int(xpos), float(g), Sc, sf, int(xe), float(ge)


def build_rows(wn, sn, W, PK, ctxm, log):
    S = STR[sn]; H = S["H"]; sig = W["SIG"][S["G"]]
    sig = sig[sig[f"xpos_H{H}"] >= 0]
    n0 = ctxm["n0"]; NP = W["NP"]
    rows = []; SC = {v: {} for v in VARS}; gate = {"ATR NaN 列": 0, "k ≠ SIG k 列": 0, "load_bars 收盤 vs 世界收盤 最大相對差": 0.0}
    for r in sig.itertuples(index=False):
        sid = r.sid; e = int(r.entry_pos); xf = int(getattr(r, f"xpos_H{H}")); gf = float(getattr(r, f"g_H{H}")); pos = int(r.pos)
        pk = PK[sid]
        bp = float(W["opens"][sid][e])
        if not np.isfinite(bp) or bp <= 0:
            bp = float(W["closes"][sid][e])
        L = W["SF"].get(sid)
        V, info = row_variants(W, pk, sid, e, xf, gf, bp, L, pos, ctxm)
        gate["ATR NaN 列"] += int(not np.isfinite(info["ATR"])); gate["k ≠ SIG k 列"] += int(info["k"] != int(r.k))
        key = f"{sid}#{e}"
        base = {"key": key, "sid": sid, "e": e, "xf": xf, "gf": gf, "bp": bp, "L": -1 if L is None else L, "ATR": info["ATR"], "kb": info["kb"], "Xcap": info["Xcap"],
                "買進年": int(ctxm["cal"][e].year)}
        orig = W["closes"][sid]
        for v in VARS:
            rec = V[v]
            if v == "A":                                      # 原策略 ＝ 正式（⛔ 不套壞根，A_bad 只記）；引擎輸入 ＝ 正式 xpos／g，停止交易由引擎做
                xa, ga, sfa = xf, gf, 0
                if L is not None and xf > L + 1:
                    xa, ga, sfa = L + 1, float(orig[L]) / bp - 1.0, 1
                base.update({"A_xpos": xf, "A_g": gf, "A_xe": xa, "A_ge": ga, "A_sf": sfa, "A_bad": rec["bad"]})
                SC[v][key] = orig
                continue
            unchanged = (not rec["trig"]) and (not rec["bad"]) and v[0] != "N"
            if unchanged:
                xp, g, sf, xe, ge = xf, gf, base["A_sf"], base["A_xe"], base["A_ge"]; SC[v][key] = orig
            else:
                xp, g, Sc, sf, xe, ge = finalize(rec, pk, bp, n0, NP, L, orig)
                SC[v][key] = Sc
            p1 = rec["parts"][0][1]
            base.update({f"{v}_xpos": xp, f"{v}_g": g, f"{v}_xe": xe, f"{v}_ge": ge, f"{v}_sf": sf, f"{v}_trig": rec["trig"], f"{v}_bad": rec["bad"],
                         f"{v}_d": -1 if rec["d"] is None else int(rec["d"]), f"{v}_X": -1 if rec["X"] is None else int(rec["X"]),
                         f"{v}_px1": float(p1[2]) if rec["trig"] else np.nan,
                         f"{v}_X2": int(rec["parts"][1][1][1]) if (v == "D2" and len(rec["parts"]) > 1 and rec["parts"][1][1][0] == "open") else -1})
        rows.append(base)
    T = pd.DataFrame(rows)
    T.insert(0, "策略", sn); T.insert(0, "世界", wn)
    trg = {v: int(T[v + "_trig"].sum()) for v in VARS if v != "A"}
    log(f"[逐列 {wn}·{sn}] {len(T)} 列｜{gate}｜觸發 {trg}")
    return T, SC, gate


# ═════════════ 引擎 ═════════════
def job_run(r):
    C = _G["CUR"]; S = STR[C["sn"]]
    au = []
    if C["sn"] == "營量":
        o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P1_SEED0 + r), C["cl"], C["op"], C["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=C["SF"], audit=au, held_map=C["hm"])
    else:
        o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P10_SEED0 + r), C["cl"], C["op"], C["NP"], return_equity=True,
                           stop_force=C["SF"], audit=au, held_map=C["hm"])
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    A = [(int(a["t"]), a["side"], a["sid"], float(a["amt"]), float(a["px"])) for a in au]
    pre = pre_stats(C, eq, hv, A, int(o["first"]), int(o["end"]))
    return r, eq, int(o["first"]), int(o["end"]), pre, A


def job_ig(a):
    wn, sn, r = a
    o, _ = IG.eng(_G["WS"][wn], STR[sn]["key"], r, audit=False)
    return wn, sn, r, np.asarray(o["equity"], float)


def pre_stats(C, eq, hv, A, first, end):
    """⛔ 不含任何報酬：持股數、現金（凍結的一半算現金）、換手、持有天數、買進列（給觸發比例）。"""
    n = len(eq); cnt = np.zeros(n + 1); frz = np.zeros(n)
    RI = C["RI"]; v = C["v"]
    buys = {}
    for t, side, k, amt, px in A:
        cnt[t] += 1 if side == "buy" else -1
        if side == "buy":
            buys[k] = [t, amt, px, None]
        else:
            if k in buys:
                buys[k][3] = t
    for k, (t, amt, px, ts) in buys.items():
        ri = RI.get(k)
        if ri is not None and v in HALF and ri["trig"] and ri["X"] >= 0:
            a_ = ri["X"]; b_ = ts if ts is not None else n
            if b_ > a_:
                frz[a_:b_] += amt * 0.5 * ri["px1"] / px
    hold = np.cumsum(cnt)[:n]
    out = {}
    for sg, (x, y) in C["segp"].items():
        yrs = (y - x + 1) / 245.0
        bs = [(k, b) for k, b in buys.items() if x <= b[0] <= y]
        hd = [b[3] - b[0] for k, b in bs if b[3] is not None]
        hdw = []
        for k, b in bs:
            if b[3] is None:
                continue
            ri = RI.get(k)
            if ri is not None and v in HALF and ri["trig"] and ri["X"] >= 0 and ri["X"] < b[3]:
                hdw.append(0.5 * (ri["X"] - b[0]) + 0.5 * (b[3] - b[0]))
            else:
                hdw.append(b[3] - b[0])
        out[sg] = {"持股": float(np.mean(hold[x:y + 1])), "現金": float(1.0 - np.mean((hv[x:y + 1] - frz[x:y + 1]) / eq[x:y + 1])),
                   "買進筆": len(bs), "換手每年": float(sum(b[1] for _, b in bs) / np.mean(eq[x:y + 1]) / yrs),
                   "持有天數": float(np.mean(hd)) if hd else np.nan, "持有天數按股數": float(np.mean(hdw)) if hdw else np.nan,
                   "買進鍵": [k for k, _ in bs]}
    return out


def keyed(W, sn, T, v, SC):
    S = STR[sn]; H = S["H"]; sig = W["SIG"][S["G"]]
    s2 = sig[sig[f"xpos_H{H}"] >= 0].copy()
    k = [f"{s}#{e}" for s, e in zip(s2["sid"], s2["entry_pos"].astype(int))]
    Ti = T.set_index("key").loc[k]
    hm = dict(zip(k, s2["sid"]))
    s2[f"xpos_H{H}"] = Ti[f"{v}_xpos"].to_numpy(np.int64); s2[f"g_H{H}"] = Ti[f"{v}_g"].to_numpy(float)
    s2["sid"] = k
    cl = {**W["closes"], **{kk: SC[v][kk] for kk in k}}
    op = {**W["opens"], **{kk: W["opens"][hm[kk]] for kk in k}}
    SFk = {**W["SF"], **{kk: W["SF"][hm[kk]] for kk in k if hm[kk] in W["SF"]}}
    RI = {}
    if v != "A":
        for kk, tr, X, px1 in zip(Ti.index, Ti[f"{v}_trig"], Ti[f"{v}_X"], Ti[f"{v}_px1"]):
            RI[kk] = {"trig": int(tr), "X": int(X), "px1": float(px1)}
    return s2, cl, op, SFk, hm, RI


# ═════════════ 彙總工具 ═════════════
def q3(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p10（後10%）": float(np.quantile(v, .1)), "p90（前10%）": float(np.quantile(v, .9)), "平均": float(v.mean())}


def ratio(c, m):
    return c / abs(m) if (m is not None and np.isfinite(m) and m != 0 and np.isfinite(c)) else np.nan


def better(ca, ma, co, mo):
    return bool(ca > co and ratio(ca, ma) >= ratio(co, mo))


def post60(pk, X, d, e, n0):
    if X is None or X < 0 or X + 59 > n0 - 1:
        return np.nan
    bar = pk["bar"]; c = pk["c"]
    kb = pk["nbad"][X + 1] if X + 1 < len(pk["nbad"]) else -1
    hi = X + 59 if (kb < 0 or kb > X + 59) else kb - 1
    pi = np.arange(X, hi + 1); pi = pi[bar[pi]]
    if not len(pi):
        return np.nan
    hb = np.arange(e, d + 1); hb = hb[bar[hb]]
    return float(c[pi].max() > c[hb].max())


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}")
    WS = AO.worlds(log, a.procs)
    gates = {}
    for wn, W in WS.items():
        gates.update(W["gate"])
    # 閘 ①②：IG.eng 直接跑（⛔ 不寫 ~/addonwork）
    _G["WS"] = WS
    jobs = [(wn, sn, r) for wn in ("主", "早年") for sn in STR for r in seeds_of(sn)]
    with Pool(a.procs) as pool:
        res = pool.map(job_ig, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    IGEQ = {(wn, sn, r): eq for wn, sn, r, eq in res}
    gates["① IG.eng eq_sha ≠ resultsYL_integrate（條數）"] = int(sum(IG.sha(eq) != REF[(wn, STR[sn]["key"], r)] for (wn, sn, r), eq in IGEQ.items()))
    log(f"[閘①] {gates['① IG.eng eq_sha ≠ resultsYL_integrate（條數）']}")
    UG.set_gate_v2(True)                                                  # seq296；本件新建的只有 R1 母體（快取為 GATE_V2 開建）
    # ── 逐股、母體、門檻、營收 ──
    ROWS = {}; SCS = {}; X = None; MINFO = {}; RINFO = {}
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n0 = len(cal); NP = W["NP"]
        sids = sorted(set(W["SIG"][False]["sid"]) | set(W["SIG"][True]["sid"]))
        M, HB, X, info = AO.market(wn, W, X, log, sids)
        MINFO[wn] = info
        _G["data"] = W["data"]; _G["cal"] = cal
        with Pool(a.procs) as pool:
            LBS = dict(pool.map(bars_job, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=8))
        miss = [s for s in sids if LBS.get(s) is None]
        if miss:
            raise SystemExit(f"⛔ load_bars 取不到 {miss[:5]}")
        PK = {}; md = 0.0
        for s in sids:
            PK[s] = stock_pack(W, s, LBS[s], HB, n0, NP)
            idx, h, l, cb = LBS[s]; ok = idx < n0
            cw = PK[s]["c"][idx[ok]]; m_ = np.isfinite(cw) & np.isfinite(cb[ok])
            if m_.any():
                md = max(md, float(np.max(np.abs(cb[ok][m_] / cw[m_] - 1.0))))
        gates[f"{wn} load_bars 收盤 vs 世界收盤 最大相對差"] = md
        if md > 1e-6:
            raise SystemExit(f"⛔ {wn} 收盤閘 {md}")
        # 門檻：q99(h, t)（researchAddOn.thresholds 原式）、q2(t)
        HMAX = 0; t_lo = 10 ** 9
        for sn in STR:
            H = STR[sn]["H"]; sg_ = W["SIG"][STR[sn]["G"]]; sg_ = sg_[sg_[f"xpos_H{H}"] >= 0]
            xm = np.minimum(sg_[f"xpos_H{H}"].to_numpy(int), n0 - 1)
            HMAX = max(HMAX, int((xm - sg_["entry_pos"].to_numpy(int)).max()) + 1)
            t_lo = min(t_lo, int(sg_["entry_pos"].min()) + AO.HMIN - 1)
        Q, NPOP = AO.thresholds(M, HMAX, t_lo, log, wn)
        C_, BAR, BAD, R1m = M["C"], M["BAR"], M["BAD"], M["R1"]
        with np.errstate(invalid="ignore", divide="ignore"):
            Rr = np.full(C_.shape, np.nan)
            m2 = R1m[:, 1:] & BAR[:, 1:] & np.isfinite(C_[:, :-1]) & ~BAD[:, 1:]
            Rr[:, 1:] = np.where(m2, C_[:, 1:] / C_[:, :-1] - 1.0, np.nan)
        cnt2 = np.isfinite(Rr).sum(0); Q2 = np.full(C_.shape[1], np.nan); ok2 = cnt2 >= MINPOP
        Q2[ok2] = np.nanpercentile(Rr[:, ok2], Q2PCT, axis=0)
        MINFO[wn]["q2 可判日數"] = int(ok2.sum()); MINFO[wn]["HMAX"] = HMAX
        del M, Rr
        rev, rly, rinf = load_revenue(W["data"]); AV = avail_pos(list(rev.index), cal)
        REV = {s: rev_events(s, rev, rly, AV, n0) for s in sids}
        RINFO[wn] = {**rinf, "持股候選股有營收": int(sum(1 for s in sids if s in rev.columns)), "候選股數": len(sids)}
        log(f"[營收 {wn}] {RINFO[wn]}")
        ctxm = {"n0": n0, "cal": cal, "Q99": Q["A2"], "Q2": Q2, "REV": REV}
        for sn in STR:
            T, SC, gt = build_rows(wn, sn, W, PK, ctxm, log)
            gates.update({f"{wn}·{sn} {k}": v for k, v in gt.items()})
            ROWS[(wn, sn)] = T; SCS[(wn, sn)] = SC
            T.to_csv(os.path.join(OUT, f"rows_{wn}_{sn}.csv.gz"), index=False, float_format="%.17g")
        _G[("PK", wn)] = PK
        del Q, NPOP
    pickle.dump(ROWS, open(os.path.join(WORK, "rows.pkl"), "wb"), protocol=5)
    # 原策略持有期跨壞根（候選列）
    for (wn, sn), T in ROWS.items():
        gates[f"{wn}·{sn} 候選列正式出場跨壞根（A_bad）"] = int(T["A_bad"].sum())
        for v in VARS[1:]:
            gates.setdefault(f"{wn}·{sn} 壞根強制列（各臂合計）", 0); gates[f"{wn}·{sn} 壞根強制列（各臂合計）"] += int(T[f"{v}_bad"].sum())
    # ── 組合層 ──
    RUN = {}
    for wn in ("主", "早年"):
        W = WS[wn]
        for sn in STR:
            T = ROWS[(wn, sn)]
            for v in VARS:
                s2, cl, op, SFk, hm, RI = keyed(W, sn, T, v, SCS[(wn, sn)])
                _G["CUR"] = {"sn": sn, "sig": s2, "cl": cl, "op": op, "SF": SFk, "hm": hm, "NP": W["NP"], "RI": RI, "v": v, "segp": W["segp"]}
                with Pool(a.procs) as pool:
                    rr = pool.map(job_run, seeds_of(sn), chunksize=4)
                for r, eq, f_, e_, pre, A in rr:
                    RUN[(wn, sn, v, r)] = {"eq": eq, "first": f_, "end": e_, "pre": pre, "au": A}
                log(f"[引擎 {wn}·{sn}·{v}] {len(rr)} 條｜{time.time() - T0:.0f}s")
            del SCS[(wn, sn)]
    # 閘 ①②（A 走 held_map）
    g2 = 0; g1 = 0
    for (wn, sn, v, r), Rn in RUN.items():
        if v == "A":
            g2 += int(not np.array_equal(Rn["eq"], IGEQ[(wn, sn, r)]))
            g1 += int(IG.sha(Rn["eq"]) != REF[(wn, STR[sn]["key"], r)])
    gates["② A 走 held_map ≠ IG.eng（條數）"] = g2; gates["① A 走 held_map eq_sha ≠ resultsYL_integrate（條數）"] = g1
    log(f"[閘②] {g2}｜[閘①held_map] {g1}")
    if g1 or g2 or gates["① IG.eng eq_sha ≠ resultsYL_integrate（條數）"]:
        raise SystemExit("⛔ 原策略閘不過")
    pickle.dump({k: (v["eq"], v["first"], v["end"]) for k, v in RUN.items()}, open(os.path.join(WORK, "eq.pkl"), "wb"), protocol=5)
    pickle.dump({k: v["au"] for k, v in RUN.items()}, open(os.path.join(WORK, "audit.pkl"), "wb"), protocol=5)
    # ── 退化（X8）：先寫 degeneracy.json（不含任何報酬）──
    DG = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在算任何報酬之前寫入（X8、裁定 seq325）；退化 ＝ 探索段（營飆 200 顆中位）平均持股 ＜ 3 或 現金比例 ＞ 30%"
          "（凍結的一半算現金）；原策略同段已達同一條 ⇒ 該條不適用", "格": {}}
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
        row = {"世界": wn, "策略": sn, "臂": v, "r": r}
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            c_, m_, _ = RR.win_metrics(eq, f_, e_, x, y)
            p = Rn["pre"][sg]
            row.update({f"{sg}_年化": c_, f"{sg}_回落": m_, f"{sg}_持股": p["持股"], f"{sg}_現金": p["現金"], f"{sg}_買進筆": p["買進筆"],
                        f"{sg}_換手每年": p["換手每年"], f"{sg}_成本每年": p["換手每年"] * COST, f"{sg}_持有天數": p["持有天數"], f"{sg}_持有天數按股數": p["持有天數按股數"]})
        SE.append(row)
        sgT = "主窗" if wn == "主" else "早年"; x, y = W["segp"][sgT]
        a_ = max(x, f_); yy = min(y, e_ - 1)
        MEs = [m for m in ME[wn] if a_ <= m <= yy]
        t2 = {"世界": wn, "策略": sn, "臂": v, "r": r}
        t2.update(AO.t2_first(W["cal"], eq[a_:yy + 1], a_, yy, MEs, T2[sn]))
        T2R.append(t2)
    SE = pd.DataFrame(SE); T2R = pd.DataFrame(T2R)
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # 主表
    MAIN = []
    for sn in STR:
        for wn in ("主", "早年"):
            for sg in SEGS[wn]:
                base = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == "A")].sort_values("r")
                co, mo = float(base[f"{sg}_年化"].median()), float(base[f"{sg}_回落"].median())
                for v in VARS:
                    g = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["臂"] == v)].sort_values("r")
                    ca, ma = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                    per = [better(*z) for z in zip(g[f"{sg}_年化"], g[f"{sg}_回落"], base[f"{sg}_年化"], base[f"{sg}_回落"])]
                    MAIN.append({"策略": sn, "臂": v, "臂名": VNAME[v], "段": sg, "顆數": len(g), "原_年化": co, "原_回落": mo, "原_比值": ratio(co, mo),
                                 "臂_年化": ca, "臂_回落": ma, "臂_比值": ratio(ca, ma), "年化差": ca - co, "回落差（臂−原）": ma - mo,
                                 "變好": better(ca, ma, co, mo) if v != "A" else None,
                                 "逐顆變好比例": float(np.mean(per)) if v != "A" else None,
                                 "逐顆年化贏比例": float(np.mean(g[f"{sg}_年化"].to_numpy() > base[f"{sg}_年化"].to_numpy() + 1e-12)) if v != "A" else None,
                                 "臂_年化p10": float(g[f"{sg}_年化"].quantile(.1)), "臂_年化p90": float(g[f"{sg}_年化"].quantile(.9)),
                                 "臂_回落p10": float(g[f"{sg}_回落"].quantile(.1)), "臂_回落p90": float(g[f"{sg}_回落"].quantile(.9)),
                                 "持股中位": float(g[f"{sg}_持股"].median()), "現金中位": float(g[f"{sg}_現金"].median()),
                                 "換手每年中位": float(g[f"{sg}_換手每年"].median()), "成本每年中位": float(g[f"{sg}_成本每年"].median()),
                                 "持有天數中位": float(g[f"{sg}_持有天數"].median()), "持有天數按股數中位": float(g[f"{sg}_持有天數按股數"].median()),
                                 "買進筆中位": float(g[f"{sg}_買進筆"].median())})
    MT = pd.DataFrame(MAIN); MT.to_csv(os.path.join(OUT, "Exit5_main.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    row = lambda sn, v, sg: MT[(MT["策略"] == sn) & (MT["臂"] == v) & (MT["段"] == sg)].iloc[0]
    # 判定
    VER = {}
    for sn in STR:
        for mth, cells in METHODS.items():
            nd = [c for c in cells if not DG["格"][f"{sn}·{c}"]["退化"]]
            alld = not nd; pool_ = list(cells) if alld else nd
            pick = sorted(pool_, key=lambda c: (-(row(sn, c, "探索")["臂_比值"]), -(row(sn, c, "探索")["臂_年化"]), list(cells).index(c)))[0]
            ex, cf = row(sn, pick, "探索"), row(sn, pick, "確認")
            dg = DG["格"][f"{sn}·{pick}"]["退化"]
            ok = bool(ex["變好"]) and bool(cf["變好"]) and not dg
            VER[f"{sn}·{mth}"] = {"挑中格": pick, "全退化": alld and len(cells) > 1, "退化": dg, "探索段變好": bool(ex["變好"]), "確認段變好": bool(cf["變好"]),
                                  "結論": ("退化、不判" if dg else ("變好（暫定）" if ok else ("沒有變好（探索段就沒變好）" if not ex["變好"] else "沒有變好（確認段沒變好）"))),
                                  **{f"{sg}": {k: float(r_[k]) for k in ("原_年化", "原_回落", "原_比值", "臂_年化", "臂_回落", "臂_比值", "逐顆變好比例")}
                                     for sg, r_ in (("探索", ex), ("確認", cf))},
                                  "早年（描述）": {k: float(row(sn, pick, "早年")[k]) for k in ("原_年化", "原_回落", "原_比值", "臂_年化", "臂_回落", "臂_比值")}}
            if mth == "法1":
                VER[f"{sn}·{mth}"]["探索段兩格比值"] = {c: float(row(sn, c, "探索")["臂_比值"]) for c in cells}
    log(f"[判定] {json.dumps({k: (v['挑中格'], v['結論']) for k, v in VER.items()}, ensure_ascii=False)}")
    # ── 必報 ──
    REP = must_report(WS, ROWS, RUN, SE, T2R, log)
    nbetter = sum(1 for v in VER.values() if v["結論"].startswith("變好"))
    trig = {sn: {v: REP[f"{sn}·{v}·主"]["觸發比例合計"] for v in JUDGED} for sn in STR}
    turn = {sn: {v: float(row(sn, v, "主窗")["換手每年中位"]) for v in JUDGED} for sn in STR}
    PRI = {"① 10 個判定變好 ≤ 1（約七成）": {"變好個數": nbetter, "成立": nbetter <= 1},
           "② 法2 觸發最多、換手最高，兩策略都變差（約七成）": {
               sn: {"法2 觸發比例": trig[sn]["E2"], "觸發最多": trig[sn]["E2"] >= max(trig[sn].values()), "法2 換手": turn[sn]["E2"],
                    "換手最高": turn[sn]["E2"] >= max(turn[sn].values()), "判定沒有變好": not VER[f"{sn}·法2"]["結論"].startswith("變好"),
                    "探索、確認 年化與比值都低於原策略": all(row(sn, "E2", sg)["臂_年化"] < row(sn, "E2", sg)["原_年化"] and row(sn, "E2", sg)["臂_比值"] < row(sn, "E2", sg)["原_比值"]
                                                    for sg in ("探索", "確認"))} for sn in STR},
           "③ 法3 觸發占持股 ＜ 15%（約六成）": {sn: {"觸發比例（主窗）": trig[sn]["E3"], "成立": trig[sn]["E3"] < 0.15} for sn in STR}}
    S = {"讀法寫死": TIME, "登錄": f"營量營飆出場五法 seq1 sha {REG_SHA}（裁定 seq343 發號 N_組合＋5）", "登錄檔": regf,
         "結果句必附": SENT, "早年必附": NOTE_EARLY, "閘": gates, "母體": MINFO, "營收": RINFO, "退化": DG, "判定": VER, "先驗": PRI,
         "主表": MT.to_dict("records"), "必報": REP,
         "讀法清單": "見 backtest/researchExit5.py 檔頭 X0～X9", "耗時秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "Exit5.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


def must_report(WS, ROWS, RUN, SE, T2R, log):
    from backtest import researchYL_truetopT as TTT
    from backtest import researchAddOn_truetop_peak as PKF
    REP = {}
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n0 = len(cal); PK = _G[("PK", wn)]
        sgT = "主窗" if wn == "主" else "早年"
        for sn in STR:
            T = ROWS[(wn, sn)].set_index("key")
            for v in VARS[1:]:
                yr = {}; diffs = []; held = set(); nb = 0
                for r in seeds_of(sn):
                    keys = RUN[(wn, sn, v, r)]["pre"][sgT]["買進鍵"]; nb += len(keys)
                    tv = T.loc[keys]
                    for Y, tr in zip(tv["買進年"], tv[f"{v}_trig"]):
                        z = yr.setdefault(int(Y), [0, 0]); z[0] += 1; z[1] += int(tr)
                    m = tv[tv[f"{v}_trig"] == 1]
                    diffs += list((m[f"{v}_ge"] - m["A_ge"]).to_numpy(float)); held |= set(m.index)
                tot = [sum(z[0] for z in yr.values()), sum(z[1] for z in yr.values())]
                U = T.loc[sorted(held)] if held else T.iloc[0:0]
                dd = (U[f"{v}_ge"] - U["A_ge"]).to_numpy(float)
                rep = {"觸發比例逐年（依買進年；營飆 200 顆合計）": {str(Y): {"持股筆": z[0], "觸發筆": z[1], "占比": z[1] / z[0] if z[0] else None} for Y, z in sorted(yr.items())},
                       "觸發比例合計": tot[1] / tot[0] if tot[0] else None,
                       "提早賣筆 報酬差（改出場−原出場，合併）": q3(diffs), "報酬差 ＞ 0 比例（合併）": float(np.mean(np.asarray(diffs) > 0)) if diffs else None,
                       "提早賣筆 報酬差（去重）": q3(dd), "唯一觸發列": int(len(U))}
                # ③ 距整段最高點、④ 賣後 60 根新高
                prow = []; p60 = []; p60o = []
                for k, rw in U.iterrows():
                    pk = PK[rw["sid"]]; c = np.asarray(W["closes"][rw["sid"]], float)[:n0]
                    d = int(rw[f"{v}_d"]); X = int(rw[f"{v}_X"]); e = int(rw["e"])
                    if d < 0 or X < 0:
                        continue
                    t = TTT.anchor_pit(c, d, e); te = TTT.anchor_pit(c, e, e)
                    prow.append(PKF.rowstats(c, t, te, d, float(pk["o"][X]), n0))
                    p60.append(post60(pk, X, d, e, n0))
                if prow:
                    DFp = pd.DataFrame(prow); REPk = PKF.describe(DFp)
                else:
                    REPk = {"筆數": 0}
                rep["賣出點距整段最高點（唯一觸發列）"] = REPk
                rep["賣出後60根又創新高比例（唯一觸發列）"] = {"n": int(np.isfinite(p60).sum()), "比例": float(np.nanmean(p60)) if np.isfinite(p60).any() else None}
                REP[f"{sn}·{v}·{wn}"] = rep
            # 原出場對照（A 的唯一持股）
            held = set()
            for r in seeds_of(sn):
                held |= set(RUN[(wn, sn, "A", r)]["pre"][sgT]["買進鍵"])
            p60o = []
            for k in sorted(held):
                rw = T.loc[k]; pk = PK[rw["sid"]]; xf = int(rw["A_xe"])
                if xf >= n0 - 1:
                    continue
                p60o.append(post60(pk, xf + 1, xf, int(rw["e"]), n0))
            REP[f"{sn}·A·{wn}"] = {"原出場後60根又創新高比例（(xf, xf＋60] 比持有期最高；唯一持股）": {"n": int(np.isfinite(p60o).sum()),
                                                                                              "比例": float(np.nanmean(p60o)) if np.isfinite(p60o).any() else None}}
    # 觸發比例合計鍵名統一（主）
    for k in list(REP):
        if k.endswith("·主") or k.endswith("·早年"):
            pass
    # T2
    T2S = {}
    for sn in STR:
        for wn in ("主", "早年"):
            o_ = T2R[(T2R["策略"] == sn) & (T2R["世界"] == wn) & (T2R["臂"] == "A")].sort_values("r")
            for v in VARS[1:]:
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
    REP["T2"] = T2S
    for sn in STR:
        for v in VARS[1:]:
            REP[f"{sn}·{v}·主"]["觸發比例合計"] = REP[f"{sn}·{v}·主"]["觸發比例合計"]
    log(f"[必報] 完成")
    return REP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = AO.log_to(os.path.join(OUT, "run.log"))
    log(f"[開跑] {now_tpe()}（台北）NSEED {NSEED}")
    run(a, log)


if __name__ == "__main__":
    main()

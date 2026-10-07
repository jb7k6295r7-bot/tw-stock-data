# -*- coding: utf-8 -*-
"""連續虧損（F4）飆股什麼時候抓得到——到頂點幾天、中間幾根漲停、差別訊號出現時已漲幾 %、漲幾 % 後變飆股的機率（描述；使用者直接問；參考、⛔ 不計 N、不需登錄）。回測線（子代理執行）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMineF4when            # 本體＋網頁
    ...                                                                   -m backtest.researchMineF4when page       # 只重做網頁
    抽樣查核：... -m backtest.researchMineF4when --check（⛔ 不呼叫本檔本體、researchMine、researchMineF4、researchMineF4why 的函式；從原始 CSV 自算）

⭐ 讀法寫死時間：2026-10-07 11:45（台北）；寫死前 ⛔ 沒看任何本件數字（只知道派工單轉述：F4 飆股起漲到頂點窗長中位 130 個交易日，p10～p90 40～229；
   以及「連續虧損飆股為什麼漲」的結論：差別出在起漲到頂點這段的營收創 24 月新高、轉盈、題材、處置等）。
   使用者原話：「如果每天關注這些股票你要漲到幾%才抓的出來？或是漲幾趴可以算是飆股可以買進？中間會有很多漲停嗎？你的一般到頂點會是幾天？」
   使用者固定規矩：描述性統計（參考、不計 N）；飆股 ＝ seq6 網格 250 格（H 10～250 × g 50%～1000%），每個數字取全網格各格中位（附 p10～p90）；
   ⛔ 不寫「N 天漲一倍」；⛔ 不給買賣建議；用語「假訊號」。

═══ 讀法（W 標）═══
 W1 事件（同 researchMineF4 Z2／researchMineF4why Y1，逐筆相同）：s5 events 全部 250 格、t＋H ≤ 2026-08-31（U4b）、m ＝ 嚴格 ＜ t 的最後月底判定日；
    「F4 飆股」＝ m 時 F4；參照「不帶 F4 的飆股」＝ known 且 m 時非 F4；頂點 P ＝ s5 的 P（(t, t＋H] 內最高收盤、同價取最早）；
    段依 t 的月份（2017-03～2021-12、2022-01～2026-08、合併）；版本：全部上市櫃（主）、W1 母體內（EL[m]）。
    ⭐ 閘門：F4 飆股集合 ＝ ~/minework/F4/events.npz；自載還原收盤（接合版面、停牌沿用前一收盤）重算每個事件的 P 與 M（＝ t→P 漲幅）＝ s5 events
 W2 到頂點幾天：t→P 的 s5 日曆交易日數 P−t（含停牌日）與 t→P 漲幅 c[P]÷c[t]−1；每格算 p10／p25／中位／p75／p90，再取網格中位。
    ⚠ 構造使然：起漲日 ＝「H 日內會漲到 g 的第一天」⇒ P−t 天生 ≤ H 且貼近 H（researchSurge5 S18）；另報「不設 H 的頂點」P*（s5 ps_d、ps_g：
    從 P 起跟著創新高、直到第一次從最高回落 30% 之前的最高點；到資料尾沒回落 ⇒ 未完，比例照報）與依 H 分的天數（參考）
    ⭐ 閘門：F4 合併全部「各格 P−t 中位的網格中位、p10、p90」＝ researchMineF4why summary.json（130、40、229）
 W3 中間有多少漲停：漲停 ＝ researchMineF4why 的 lu.npy（researchSurge5 同法；該件已閘門 lu_20 逐一相同；本件呼叫其 build_arrays 時再過一次閘門）；
    窗 ＝ [t, P]（含起漲日，同 researchMineF4why「起漲到頂點」）；漲停天數分 0、1～2、3～5、6～10、＞10；中位、平均；
    最長連續漲停 ＝ 窗內「有效 K 棒序列上連續漲停」最長幾根（停牌日跳過不斷，窗外的不算）；漲停占比 ＝ 漲停天數 ÷ 窗內有效 K 棒數
    ⭐ 閘門：漲停 ≥ 1／≥ 3／≥ 5 天的逐格比例與件數 ＝ researchMineF4why cells.csv.gz（lu1／lu3／lu5、run 窗；各段各版）
 W4 差別訊號第一次出現時已漲幾 %：訊號 e ＝ 窗 [t, P] 內該訊號的第一個生效交易日（生效日規則全同 researchMineF4why Y3～Y8；直接用其 build_arrays 的事件陣列）：
      月營收創 24 月新高（rv_h24；可用日 ＝ 次月 10 日〔2026-01 期起 15 日〕之後第一個交易日，法定期限代理）｜季報由虧轉盈（eq_turn1 ∨ eq_turn4；A2 可用日）｜
      業績明顯變好（嚴；同 Y3）｜私募（主旨含「私募」）｜接單／題材類（classify 6、11、2）｜第一次注意股｜第一次處置（start_date）｜
      族群一起漲（同一格的 s5 事件中，同產業〔現值、後見〕、不同股票、起漲日 t' 在 [t−20, P] 者最早的一個，e ＝ max(t, t')）｜第一次漲停（參考）
    已漲 ＝ c[e]÷c[t]−1（還原、停牌沿用）；已走完幾成 ＝ (c[e]−c[t])÷(c[P]−c[t])；還剩幾成 ＝ 1 − 已走完；還剩漲幅 ＝ c[P]÷c[e]−1；e−t 交易日數
    出現比例 ＝ 窗內有出現 ÷ 全部事件；其餘只在有出現的事件裡算；另報「起漲前 60 日 [t−60, t−1] 就已出現過」的比例（參考）
    ⭐ 閘門：rv_h24、業績明顯變好（嚴）、私募、題材類、注意股、處置「窗內有出現」的逐格比例與件數 ＝ researchMineF4why cells.csv.gz（run 窗；各段各版）
 W5 漲幾 % 後變飆股的機率（條件機率；描述）：
    比率 r[d] ＝ s5 F.npy 的 dlo_60 ＝ c[d] ÷（含 d 在內最近 60 根有效 K 棒的最低收盤）− 1（回看窗內有壞根 ⇒ 無值；researchSurge5 S3、S9）；
    觸發 ＝ 每檔、每個 x ∈ {10,15,20,30,40,50,70,100%}：依有效 K 棒順序，r[d] ≥ x 的日子取第一個，之後 60 根有效 K 棒內不再取（第 61 根起再找下一個）；
      去重只看股價，不看旗；全歷史一起掃（2017-03 以前的觸發只影響去重）；觸發日 d 依月份分段，且 d 時 known（m(d) 判定日存在、股票在旗表內）
    分組：F4 ＝ m(d) 時 F4（主）｜不帶 F4 ＝ known 且 m(d) 時非 F4（對照）；W1 版另加 EL[m(d)]
    之後變飆股 ＝ 每格 (H, g)：定義域 hdef[d] ≥ H 且 d＋H ≤ 2026-08-31；(d, d＋H] 最高收盤 ≥ c[d] ×（1＋g）×（1−1e−9）（同 s5 標籤）；比例 ＝ 定義域內的平均，取網格中位
    之後還能再漲 ＝ (d, d＋H] 最高收盤 ÷ c[d] − 1（定義域內中位；另報變飆股者的中位）；
    能吃到全程幾成（只算變飆股者）＝（頂點收盤 − c[d]）÷（頂點收盤 − 60 根低點收盤），低點收盤 ＝ c[d] ÷（1＋r[d]），頂點 ＝ (d, d＋H] 最高收盤
    還沒變飆股就先跌 15% ＝ (d, d＋H] 內第一次收盤 ≤ c[d]×0.85 早於第一次收盤 ≥ c[d]×(1＋g)（或沒漲到）；格中位
    一年內曾跌 15%（不分格）＝ (d, d＋250] 內任一收盤 ≤ c[d]×0.85；定義域 hdef[d] ≥ 250 且 d＋250 ≤ 2026-08-31
    每天平均幾檔 ＝ 段內觸發數 ÷ 段內 s5 日曆交易日數（不論標籤定義域）
    基準列「不看漲幅（帶 F4 的每一個有 K 棒的股-日）」：同分組、同定義域的變飆股比例與一年內曾跌 15%；倍數 ＝ 同格 觸發列比例 ÷ 基準比例 的網格中位
    ⭐ 閘門：所有 U4b 的 s5 事件 (s, t) 在本件標籤矩陣上 ＝ 1；觸發列逐筆算的標籤 ＝ 標籤矩陣同一格
 W6 彙總：每格 × 段 × 版本 × 分組；網格彙總 ＝ 有 ≥ 1 筆（條件統計：有 ≥ 1 筆符合條件）的格的中位，附 p10～p90。
 W7 只描述：⛔ 不判定、⛔ 不計 N；W4 用到起漲後才知道的事（e 在窗內、窗延伸到頂點），W5 的「變飆股」也是事後標籤——都 ⛔ 不能拿來當事前訊號或買點；
    ⛔ 不寫「N 天漲一倍」、⛔ 不給買賣建議
 W8 --check（獨立寫法）：
    ① 抽 2 格（合併段、全部版、F4 飆股 ≥ 30；default_rng(20261009)）：自己從 events.npz／日曆／flags_main.npz 分 F4 與不帶 F4、自己載還原收盤（data.load_stock 是輸入）、
       自寫 tick 表算漲停、自己讀 fin_hist＋filing_dates、revenue_hist、news（classify 原始碼字串 exec）、attention、disposal、industry
       ⇒ W2～W4 的全部格統計比 cells.csv.gz（件數相同、數值相對 1e-9）
    ② 抽 200 檔（default_rng(20261010)）：自己從還原收盤算 60 根最低（壞根位置由 hdef 反推）⇒ 觸發逐筆比本體 trig.npz；同 2 格逐筆重算標籤、漲幅、先跌 15%、一年跌 15%、吃到幾成
    ③ 同 2 格用 pandas 另一套寫法從 trig.npz 重算 W5 全部格統計比 cells.csv.gz；基準列用每檔 sliding window 自算比 cells.csv.gz
輸出 backtest/resultsMine/F4when/（cells.csv.gz、grid.csv、free.csv、byH.csv、summary.json、check.json、run.log、連續虧損飆股什麼時候抓得到.html）；逐筆 ~/minework/F4when/
"""
from __future__ import annotations

import argparse
import bisect
import glob
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import researchMine as RM
from backtest import researchMineF4 as M4

TAGT = "2026-10-07 11:45（台北）"
S5W = RM.S5W
CUT = RM.CUT
WORK = os.path.join(RM.WORK, "F4when")
OUT = os.path.join(RM.OUT, "F4when")
M4W = os.path.join(RM.WORK, "F4")
WHYW = os.path.join(RM.WORK, "F4why")
WHYO = os.path.join(RM.OUT, "F4why")
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
SEGS, SEGNAME, VERS = M4.SEGS, M4.SEGNAME, M4.VERS
HS5, GS5, NC5 = RM.HS5, RM.GS5, RM.NC5
XS = (0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.70, 1.00)
XK = [f"x{int(round(x * 100))}" for x in XS]
NLOW, DEDUP, WPRE, WGRP, BIG = 60, 60, 60, 20, 32000
SIG = [("rv_h24", "月營收創 24 個月新高", ["rv_h24"]),
       ("turn", "季報由虧轉盈（比前一季或比去年同季）", ["eq_turn1", "eq_turn4"]),
       ("A_str", "業績明顯變好（嚴：由虧轉盈、月營收年增 ＞ 50%、或創 24 個月新高）", ["eq_turn1", "eq_turn4", "rv_y50", "rv_h24"]),
       ("kw_pp", "私募公告（主旨含「私募」）", ["kw_pp"]),
       ("C_any", "接單／題材類公告（得標接單合約、法說會、澄清媒體報導）", ["n6", "n11", "n2"]),
       ("att", "第一次被列注意股", ["att"]),
       ("disp", "第一次被處置", ["disp"]),
       ("grp", "族群一起漲（同產業另一檔也起漲；產業現值、後見）", None),
       ("lu", "第一次漲停（參考）", None)]
GATE_WHY = {"rv_h24": "rv_h24", "A_str": "A_str", "kw_pp": "kw_pp", "C_any": "C_any", "att": "att1", "disp": "disp1"}
QS = {"q10": 0.1, "q25": 0.25, "med": 0.5, "q75": 0.75, "q90": 0.9}


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 還原收盤（接合版面）═════════════
_CG: dict = {}


def _c_init(cal):
    D.DATA = ST; _CG["cal"] = cal


def _c_one(a):
    si, sid, mk = a
    st = D.load_stock(sid, mk, _CG["cal"])
    if st is None:
        return si, None
    return si, st.df["close"].to_numpy(float)


def load_closes(uni, cal5, procs, log):
    p = os.path.join(WORK, "cff.npy")
    if os.path.exists(p):
        return np.load(p)
    CF = np.full((len(uni), len(cal5)), np.nan)
    with Pool(procs, initializer=_c_init, initargs=(cal5,)) as pool:
        for si, c in pool.imap_unordered(_c_one, [(i, x, m) for i, (x, m) in enumerate(zip(uni["stock_id"], uni["market"]))], chunksize=16):
            if c is not None:
                CF[si] = pd.Series(c).ffill().to_numpy()
    np.save(p, CF)
    log(f"[收盤] {len(uni)} 檔 × {len(cal5)} 日（接合版面還原、停牌沿用）")
    return CF


# ═════════════ 彙總工具 ═════════════
def cell_stats(df, specs, tag, out):
    """df：每列一筆（含 cell、各值欄）；specs：(鍵, 值欄, 統計, 條件欄或 None)。out 追加 (tag..., 鍵, 統計, cell, n, 值)。"""
    for key, col, stat, cond in specs:
        x = df if cond is None else df[df[cond]]
        if not len(x):
            continue
        g = x.groupby("cell")[col]
        n = g.size()
        if stat == "mean":
            v = g.mean()
        else:
            v = g.quantile(QS[stat])
        for c, nn in n.items():
            out.append((*tag, key, stat, int(c), int(nn), float(v.loc[c])))


def grid_of(CL):
    rows = []
    for k, x in CL.groupby(["部分", "分組", "段", "版本", "鍵", "統計"], sort=False):
        v = x["值"].to_numpy(float); v = v[np.isfinite(v)]
        rows.append((*k, len(v), float(np.median(v)) if len(v) else np.nan, float(np.quantile(v, 0.1)) if len(v) else np.nan,
                     float(np.quantile(v, 0.9)) if len(v) else np.nan, int(x["n"].sum())))
    return pd.DataFrame(rows, columns=["部分", "分組", "段", "版本", "鍵", "統計", "格數", "網格中位", "p10", "p90", "筆數各格加總"])


def next_occ(has):
    """has (S, nd) bool ⇒ NX[s, k] ＝ ≥ k 的第一個 True 位置（無 ⇒ BIG）。"""
    nd = has.shape[1]
    idx = np.where(has, np.arange(nd, dtype=np.int32)[None, :], BIG).astype(np.int32)
    return np.minimum.accumulate(idx[:, ::-1], axis=1)[:, ::-1].astype(np.int16)


def first_in(NX, off, s, a, b):
    nd = NX.shape[1]
    a2 = a - off; b2 = b - off
    nx = NX[s, np.clip(a2, 0, nd - 1)].astype(np.int64)
    ok = (a2 >= 0) & (a2 <= b2) & (a2 < nd) & (nx <= b2)
    return np.where(ok, nx + off, -1)


# ═════════════ 本體 ═════════════
def body(a):
    from backtest import researchMineF4why as W
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchMineF4when {now_tpe()}（台北）｜讀法寫死 {TAGT} =====")
    G = M4.load_base(log)
    FL, sids, cal, mepos, cal5, uni = G["FL"], G["sids"], G["cal"], G["mepos"], G["cal5"], G["uni"]
    cell, d, s = G["cell"], G["d"], G["s"]
    icut = G["icut"]; N5 = len(cal5); S5 = len(uni)
    bar5 = np.asarray(G["bar5"]); hdef = np.asarray(G["hdef"])
    E = np.load(os.path.join(S5W, "events.npz"))
    Hc_all = np.array(HS5)[E["cell"].astype(int) // len(GS5)]
    ok = E["d"].astype(int) + Hc_all <= icut
    P = E["P"][ok].astype(int); Mv = E["M"][ok].astype(float)
    psd = E["ps_d"][ok].astype(int); psg = E["ps_g"][ok].astype(float); pso = E["ps_open"][ok].astype(int)
    assert np.array_equal(E["cell"][ok].astype(int), cell) and np.array_equal(E["d"][ok].astype(int), d)
    Hc = np.array(HS5)[cell // len(GS5)]
    # F4／非 F4（同 researchMineF4why）
    a0, b0 = SEGS["合併"]
    tdates = cal5[d]; mon_t = np.array([str(x)[:7] for x in tdates])
    insg = (mon_t >= a0) & (mon_t <= b0)
    me_dates = cal[mepos].values
    k_ = np.searchsorted(me_dates, tdates.values, side="left") - 1
    usid = uni["stock_id"].to_numpy()[s]
    ix = {x: j for j, x in enumerate(sids)}
    jcol5 = np.array([ix.get(x, -1) for x in uni["stock_id"]])
    jcol = jcol5[s]
    known = insg & (jcol >= 0) & (k_ >= 0)
    f4ev = np.zeros(len(d), bool); f4ev[known] = FL["F4"][k_[known], jcol[known]]
    elev = np.zeros(len(d), bool); elev[known] = FL["EL"][k_[known], jcol[known]]
    evF = np.flatnonzero(known & f4ev); evN = np.flatnonzero(known & ~f4ev)
    ref = np.load(os.path.join(M4W, "events.npz"))
    assert np.array_equal(ref["ev"], evF), "⛔ F4 飆股與 researchMineF4 不同"
    log(f"[事件] F4 飆股 {len(evF):,}（＝ researchMineF4 events.npz）｜不帶 F4 飆股 {len(evN):,}")
    # ── 收盤＋閘門（P、M）
    CF = load_closes(uni, cal5, a.procs, log)
    badP = 0; badM = 0
    for H in HS5:
        q = np.flatnonzero(Hc == H)
        for i0 in range(0, len(q), 20000):
            qq = q[i0:i0 + 20000]
            win = CF[s[qq][:, None], d[qq][:, None] + np.arange(1, H + 1)[None, :]]
            Pm = d[qq] + 1 + np.argmax(win, axis=1)
            badP += int((Pm != P[qq]).sum())
            mm = CF[s[qq], P[qq]] / CF[s[qq], d[qq]] - 1
            badM += int((np.abs(mm - Mv[qq]) > 1e-5 * np.maximum(1, np.abs(Mv[qq]))).sum())
    log(f"[閘門 P／M] 自載收盤重算 vs s5 events：P 不同 {badP}、M 不同 {badM}（共 {len(d):,}）")
    if badP or badM:
        raise SystemExit("⛔ 收盤與 s5 不同")
    gain = CF[s, P] / CF[s, d] - 1
    # ── 事件陣列（researchMineF4why；含漲停閘門）
    AR, info = W.build_arrays(G, log, a.procs)
    off, nd = AR["off"], AR["nd"]
    NX = {}
    for k, nm, tys in SIG:
        if tys is None:
            continue
        has = np.zeros((S5, nd), bool)
        for ty in tys:
            has |= np.diff(AR["C"][ty], axis=1) > 0
        NX[k] = next_occ(has)
    ind5 = AR["ind5"]
    del AR
    LU = np.load(os.path.join(WHYW, "lu.npy"))
    NX["lu"] = next_occ(LU[:, off:])
    ordm = np.cumsum(bar5, axis=1, dtype=np.int32)
    lucum = np.zeros((S5, N5 + 1), np.int32); np.cumsum(LU, axis=1, out=lucum[:, 1:])
    RUN = np.zeros((S5, N5), np.int16)
    for si in range(S5):
        ixb = np.flatnonzero(bar5[si])
        if not len(ixb):
            continue
        l = LU[si, ixb]; r = np.zeros(len(ixb), np.int16); c_ = 0
        for k in range(len(ixb)):
            c_ = c_ + 1 if l[k] else 0; r[k] = c_
        RUN[si, ixb] = r
    # ── 每事件（F4 ∪ 不帶 F4）
    EV = np.concatenate([evF, evN]); isF = np.r_[np.ones(len(evF), bool), np.zeros(len(evN), bool)]
    es, et, eP, ec = s[EV], d[EV], P[EV], cell[EV]
    assert bar5[es, et].all() and bar5[es, eP].all()
    out = {"cell": ec, "isF": isF, "el": elev[EV], "mon": mon_t[EV], "days": eP - et, "gain": gain[EV], "psd": psd[EV], "psg": psg[EV], "pso": pso[EV].astype(float)}
    nlu = lucum[es, eP + 1] - lucum[es, et]
    nbars = ordm[es, eP] - ordm[es, et] + 1
    stk = np.zeros(len(EV), int)
    for i in range(len(EV)):
        rr = RUN[es[i], et[i]:eP[i] + 1].astype(int); oo = ordm[es[i], et[i]:eP[i] + 1] - ordm[es[i], et[i]] + 1
        stk[i] = int(np.max(np.minimum(rr, oo)))
    out.update({"lu_n": nlu.astype(float), "lu_ratio": nlu / nbars, "lu_streak": stk.astype(float), "nbars": nbars})
    # 族群：同格事件、同產業、不同股、t' ∈ [t−20, P]
    egrp = np.full(len(EV), -1)
    for c in range(NC5):
        mc = cell == c
        qi = np.flatnonzero(ec == c)
        if not mc.any() or not len(qi):
            continue
        cs_, cd_ = s[mc], d[mc]; ig = ind5[cs_]; okc = ig >= 0
        key = ig[okc].astype(np.int64) * 100000 + cd_[okc]; o_ = np.argsort(key, kind="stable")
        key = key[o_]; ks = cs_[okc][o_]; kd = cd_[okc][o_]
        for i in qi:
            g_ = ind5[es[i]]
            if g_ < 0:
                continue
            j = int(np.searchsorted(key, g_ * 100000 + et[i] - WGRP, "left")); hi_ = g_ * 100000 + eP[i]
            while j < len(key) and key[j] <= hi_:
                if ks[j] != es[i]:
                    egrp[i] = max(int(kd[j]), int(et[i])); break
                j += 1
    for k, nm, tys in SIG:
        e = egrp if k == "grp" else first_in(NX[k], off, es, et, eP)
        if k == "grp":
            pre = np.zeros(len(EV), bool)                                    # 族群窗本身含起漲前 20 日 ⇒ 不另報起漲前
        else:
            pre = first_in(NX[k], off, es, et - WPRE, et - 1) >= 0
        h = e >= 0; ee = np.where(h, e, et)
        ce = CF[es, ee]; c0 = CF[es, et]; cp = CF[es, eP]
        out[f"{k}|has"] = h; out[f"{k}|pre"] = pre
        out[f"{k}|gain"] = np.where(h, ce / c0 - 1, np.nan)
        out[f"{k}|done"] = np.where(h, (ce - c0) / (cp - c0), np.nan)
        out[f"{k}|up"] = np.where(h, cp / ce - 1, np.nan)
        out[f"{k}|lag"] = np.where(h, ee - et, np.nan).astype(float)
        out[f"{k}|e"] = e
    DF = pd.DataFrame({k: v for k, v in out.items()})
    np.savez_compressed(os.path.join(WORK, "events.npz"), EV=EV, **{k.replace("|", "__"): np.asarray(v) for k, v in out.items()})
    log(f"[事件端] {len(EV):,} 列完成")
    # 規格
    sp = []
    for k in ("days", "gain", "psd", "psg"):
        sp += [(k, k, st_, None) for st_ in QS]
    sp += [("pso", "pso", "mean", None)]
    DF["lu_0"] = DF["lu_n"] == 0; DF["lu_1_2"] = DF["lu_n"].between(1, 2); DF["lu_3_5"] = DF["lu_n"].between(3, 5)
    DF["lu_6_10"] = DF["lu_n"].between(6, 10); DF["lu_gt10"] = DF["lu_n"] > 10
    DF["lu_ge1"] = DF["lu_n"] >= 1; DF["lu_ge3"] = DF["lu_n"] >= 3; DF["lu_ge5"] = DF["lu_n"] >= 5
    DF["stk_ge2"] = DF["lu_streak"] >= 2; DF["stk_ge3"] = DF["lu_streak"] >= 3; DF["stk_ge5"] = DF["lu_streak"] >= 5
    for k in ("lu_0", "lu_1_2", "lu_3_5", "lu_6_10", "lu_gt10", "lu_ge1", "lu_ge3", "lu_ge5", "stk_ge2", "stk_ge3", "stk_ge5"):
        DF[k] = DF[k].astype(float); sp.append((k, k, "mean", None))
    for k in ("lu_n", "lu_streak", "lu_ratio"):
        sp += [(k, k, st_, None) for st_ in ("med", "q75", "q90")] + [(k, k, "mean", None)]
    sp3 = []
    for k, _, _ in SIG:
        DF[f"{k}|hasf"] = DF[f"{k}|has"].astype(float); DF[f"{k}|pref"] = DF[f"{k}|pre"].astype(float)
        sp3 += [(f"{k}|has", f"{k}|hasf", "mean", None), (f"{k}|pre", f"{k}|pref", "mean", None)]
        sp3 += [(f"{k}|gain", f"{k}|gain", st_, f"{k}|has") for st_ in ("q25", "med", "q75")]
        sp3 += [(f"{k}|done", f"{k}|done", "med", f"{k}|has"), (f"{k}|up", f"{k}|up", "med", f"{k}|has"), (f"{k}|lag", f"{k}|lag", "med", f"{k}|has")]
    rows = []
    for seg, (sa, sb) in SEGS.items():
        for ver in VERS:
            for grp, gm in (("F4", DF["isF"]), ("不帶F4", ~DF["isF"])):
                m = gm & (DF["mon"] >= sa) & (DF["mon"] <= sb) & (DF["el"] if ver != "全部" else True)
                x = DF[m]
                cell_stats(x, [z for z in sp if z[0] in ("days", "gain", "psd", "psg", "pso")], ("1 到頂點", grp, seg, ver), rows)
                cell_stats(x, [z for z in sp if z[0] not in ("days", "gain", "psd", "psg", "pso")], ("2 漲停", grp, seg, ver), rows)
                cell_stats(x, sp3, ("3 訊號", grp, seg, ver), rows)
        log(f"[彙總 1～3] {seg}")
    # 依 H（參考）
    byH = []
    for grp, gm in (("F4", DF["isF"]), ("不帶F4", ~DF["isF"])):
        x = DF[gm]
        for c, y in x.groupby("cell"):
            byH.append((grp, int(HS5[c // len(GS5)]), float(GS5[c % len(GS5)]), len(y), float(y["days"].median()), float(y["psd"].median()), float(y["gain"].median())))
    BH = pd.DataFrame(byH, columns=["分組", "H", "g", "件數", "P−t 中位", "P*−t 中位", "t→P 漲幅中位"])
    BH = BH.groupby(["分組", "H"]).agg(格數=("g", "size"), 件數=("件數", "sum"), 天數中位=("P−t 中位", "median"), 不設H天數中位=("P*−t 中位", "median"),
                                      漲幅中位=("t→P 漲幅中位", "median")).reset_index()
    BH.to_csv(os.path.join(OUT, "byH.csv"), index=False, float_format="%.6g")
    del DF
    # ═════ W5 ═════
    rows4, free = part4(G, CF, bar5, hdef, jcol5, FL, cal, mepos, cal5, icut, cell, d, s, log)
    CL = pd.DataFrame(rows + rows4, columns=["部分", "分組", "段", "版本", "鍵", "統計", "cell", "n", "值"])
    CL.insert(7, "格", [RM.cell_name(c) for c in CL["cell"]])
    CL.to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.10g")
    GR = grid_of(CL)
    # 倍數（觸發比例 ÷ 基準比例，逐格）
    lifts = []
    for (grp, seg, ver), x in CL[(CL["部分"] == "4 漲幾%") & (CL["統計"] == "mean") & CL["鍵"].str.endswith("|rate")].groupby(["分組", "段", "版本"]):
        b = x[x["鍵"] == "base|rate"].set_index("cell")["值"]
        for xk in XK:
            y = x[x["鍵"] == f"{xk}|rate"].set_index("cell")["值"]
            cc = y.index.intersection(b.index)
            rr = (y.loc[cc] / b.loc[cc]).replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
            lifts.append(("4 漲幾%", grp, seg, ver, f"{xk}|lift", "ratio", len(rr), float(np.median(rr)) if len(rr) else np.nan,
                          float(np.quantile(rr, 0.1)) if len(rr) else np.nan, float(np.quantile(rr, 0.9)) if len(rr) else np.nan, 0))
    GR = pd.concat([GR, pd.DataFrame(lifts, columns=GR.columns)], ignore_index=True)
    GR.to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.10g")
    FR = pd.DataFrame(free)
    FR.to_csv(os.path.join(OUT, "free.csv"), index=False, float_format="%.10g")
    # ── 閘門（和 researchMineF4why 對）
    WS = json.load(open(os.path.join(WHYO, "summary.json"), encoding="utf-8"))
    WC = pd.read_csv(os.path.join(WHYO, "cells.csv.gz"))
    WC = WC[(WC["窗"] == "run") & (WC["F4飆股數"] >= 1)].set_index(["段", "版本", "情況", "cell"])
    MYC = CL[CL["分組"] == "F4"].set_index(["部分", "段", "版本", "鍵", "統計", "cell"])
    g_ = GR.set_index(["部分", "分組", "段", "版本", "鍵", "統計"])
    dmed = g_.loc[("1 到頂點", "F4", "合併", "全部", "days", "med")]
    gate = {"P−t 中位網格（中位、p10、p90）": [dmed["網格中位"], dmed["p10"], dmed["p90"]],
            "researchMineF4why": [WS["起漲到頂點交易日數（各格中位的網格中位，合併全部）"], WS["p10"], WS["p90"]]}
    bad = int(not np.allclose(gate["P−t 中位網格（中位、p10、p90）"], gate["researchMineF4why"], rtol=1e-9))
    for seg in SEGS:
        for ver in VERS:
            for k, wk in list(GATE_WHY.items()) + [("lu_ge1", "lu1"), ("lu_ge3", "lu3"), ("lu_ge5", "lu5")]:
                pt = ("3 訊號", seg, ver, f"{k}|has", "mean") if not k.startswith("lu_") else ("2 漲停", seg, ver, k, "mean")
                mine = MYC.loc[pt]; th = WC.loc[(seg, ver, wk)]                     # 逐格（cells.csv.gz 10 位有效數字）
                cc = th.index
                if not mine.index.equals(cc) and set(mine.index) != set(cc):
                    bad += 1; log(f"⛔ 閘門格集合不同 {pt}"); continue
                mine = mine.loc[cc]
                nb_ = int((mine["n"].to_numpy() != th["F4飆股數"].to_numpy()).sum() + (~np.isclose(mine["值"].to_numpy(), th["涵蓋率"].to_numpy(), rtol=1e-9, atol=1e-12)).sum())
                if nb_:
                    bad += 1; log(f"⛔ 閘門不同 {pt}：{nb_} 格")
    gate["和 researchMineF4why 不同"] = bad
    log(f"[閘門 F4why] 不同 {bad}")
    if bad:
        raise SystemExit("⛔ 與 researchMineF4why 不同")
    cnts = {}
    for seg, (sa, sb) in SEGS.items():
        for ver in VERS:
            for grp, ev_ in (("F4", evF), ("不帶F4", evN)):
                mm = (mon_t[ev_] >= sa) & (mon_t[ev_] <= sb) & (elev[ev_] if ver != "全部" else True)
                cnts[f"{grp}｜{seg}｜{ver}"] = {"事件（各格加總）": int(mm.sum()), "不同 (股, 起漲日)": len(set(zip(usid[ev_][mm].tolist(), d[ev_][mm].tolist()))),
                                                "不同股票": len(set(usid[ev_][mm].tolist()))}
    SM = {"讀法寫死": TAGT, "執行": now_tpe() + "（台北）", "閘門": {"P 不同": badP, "M 不同": badM, **gate, "漲停 lu_20": info["漲停閘門"]},
          "件數": cnts, "資料": {"旗": "~/minework/flags_main.npz", "s5": "~/s5work", "收盤": "stitch_950ad26e12_b53f5540a8（data.load_stock）",
                               "訊號": "researchMineF4why.build_arrays", "漲停": "~/minework/F4why/lu.npy"}}
    json.dump(SM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("===== 本體完成 =====")
    page()


def part4(G, CF, bar5, hdef, jcol5, FL, cal, mepos, cal5, icut, cell, d, s, log):
    S5, N5 = CF.shape
    bjs = json.load(open(os.path.join(S5W, "build.json"), encoding="utf-8")); FX = {c: i for i, c in enumerate(bjs["特徵欄"])}
    Fm = np.load(os.path.join(S5W, "F.npy"), mmap_mode="r")
    R = np.asarray(Fm[FX["dlo_60"]])                                            # (S5, N5) float32
    ordm = np.cumsum(bar5, axis=1, dtype=np.int32)
    mon5 = np.array([str(x)[:7] for x in cal5])
    a0, b0 = SEGS["合併"]
    # m(d)、known、F4、EL（股-日）
    kd = np.searchsorted(cal[mepos].values, cal5.values, side="left") - 1         # 每個 s5 日 → 嚴格之前最後判定日
    cols = np.flatnonzero((mon5 >= a0) & (mon5 <= b0))
    c0_, c1_ = int(cols[0]), int(cols[-1]) + 1
    assert (kd[c0_:c1_] >= 0).all()
    jj = np.where(jcol5 >= 0, jcol5, 0)
    F4M = FL["F4"][kd[c0_:c1_]][:, jj].T & (jcol5 >= 0)[:, None]
    ELM = FL["EL"][kd[c0_:c1_]][:, jj].T & (jcol5 >= 0)[:, None]
    KNM = np.repeat((jcol5 >= 0)[:, None], c1_ - c0_, axis=1)
    # ── 觸發
    TR = {"s": [], "d": [], "xi": []}
    for xi, x in enumerate(XS):
        for si in range(S5):
            ixb = np.flatnonzero(bar5[si])
            if not len(ixb):
                continue
            r = R[si, ixb]
            with np.errstate(invalid="ignore"):
                cand = np.flatnonzero(r >= x)
            last = -10 ** 9; o_ = ordm[si, ixb]
            for k in cand:
                if o_[k] - last > DEDUP:
                    TR["s"].append(si); TR["d"].append(int(ixb[k])); TR["xi"].append(xi); last = o_[k]
        log(f"[觸發] x {x:.0%}｜累計 {len(TR['d']):,}")
    ts, td, txi = (np.array(TR[k], dtype=np.int64) for k in ("s", "d", "xi"))
    keep = (td >= c0_) & (td < c1_) & (jcol5[ts] >= 0)
    ts, td, txi = ts[keep], td[keep], txi[keep]
    tf4 = F4M[ts, td - c0_]; tel = ELM[ts, td - c0_]; tmon = mon5[td]
    rr = R[ts, td].astype(float)
    # 逐筆前瞻
    n = len(td); HA = np.array(HS5)
    MHH = np.full((n, len(HS5)), np.nan); UPG = np.full((n, len(GS5)), 999, np.int16); DN = np.full(n, 999, np.int16)
    offs = np.arange(1, 251)
    for i0 in range(0, n, 20000):
        q = slice(i0, min(n, i0 + 20000))
        ii = np.minimum(td[q][:, None] + offs[None, :], N5 - 1)
        seg = CF[ts[q][:, None], ii]; c0 = CF[ts[q], td[q]][:, None]
        cm = np.maximum.accumulate(seg, axis=1)
        MHH[q] = cm[:, HA - 1] / c0 - 1
        for gi, g in enumerate(GS5):
            hit = seg >= c0 * (1 + g) * (1 - 1e-9)
            UPG[q, gi] = np.where(hit.any(1), np.argmax(hit, axis=1) + 1, 999)
        hit = seg <= c0 * 0.85 * (1 + 1e-9)
        DN[q] = np.where(hit.any(1), np.argmax(hit, axis=1) + 1, 999)
    thd = hdef[ts, td].astype(int)
    np.savez_compressed(os.path.join(WORK, "trig.npz"), s=ts, d=td, xi=txi, f4=tf4, el=tel, r=rr, MHH=MHH, UPG=UPG, DN=DN, hdef=thd)
    log(f"[觸發] 段內、known：{n:,}（F4 {int(tf4.sum()):,}）")
    # ── 標籤矩陣（基準＋閘門）
    nd_seg = {seg: int(((mon5 >= sa) & (mon5 <= sb)).sum()) for seg, (sa, sb) in SEGS.items()}
    segc = {seg: (mon5[c0_:c1_] >= sa) & (mon5[c0_:c1_] <= sb) for seg, (sa, sb) in SEGS.items()}
    barS = bar5[:, c0_:c1_]; hdS = hdef[:, c0_:c1_]; cS = CF[:, c0_:c1_]
    posS = np.arange(c0_, c1_)
    grpM = {"F4": F4M & barS, "不帶F4": KNM & ~F4M & barS}
    masks = {}
    for grp, gm in grpM.items():
        for ver in VERS:
            vm = gm & (ELM if ver != "全部" else True)
            for seg in SEGS:
                masks[(grp, seg, ver)] = vm & segc[seg][None, :]
    rows = []; free = []
    ev_ok = d + np.array(HS5)[cell // len(GS5)] <= icut
    gate_ev = 0; gate_tr = 0
    rev = CF[:, ::-1]
    for hi, H in enumerate(HS5):
        rmx = pd.DataFrame(rev.T).rolling(H, min_periods=1).max().to_numpy().T[:, ::-1]   # rmx[p] ＝ max(cff[p..p+H−1])
        fm = np.concatenate([rmx[:, 1:], np.full((S5, 1), np.nan)], axis=1)              # (p, p+H]
        defH = barS & (hdS >= H) & (posS + H <= icut)[None, :]
        fmS = fm[:, c0_:c1_]
        for gi, g in enumerate(GS5):
            c = hi * len(GS5) + gi
            with np.errstate(invalid="ignore"):
                lab = fm >= CF * (1 + g) * (1 - 1e-9)
            qe = np.flatnonzero((cell == c) & ev_ok)
            gate_ev += int((~lab[s[qe], d[qe]]).sum())
            # 觸發列一致
            dfr = (thd >= H) & (td + H <= icut)
            gate_tr += int(((UPG[:, gi] <= H) != lab[ts, td])[dfr].sum())
            labS = lab[:, c0_:c1_]
            for (grp, seg, ver), mk in masks.items():
                dm = mk & defH
                nn = int(dm.sum())
                if nn:
                    rows.append(("4 漲幾%", grp, seg, ver, "base|rate", "mean", c, nn, float((labS & dm).sum() / nn)))
        if hi % 5 == 0:
            log(f"[標籤矩陣] H {H}｜事件不符 {gate_ev}｜觸發列不符 {gate_tr}")
    log(f"[閘門 標籤] s5 事件在標籤矩陣上 ≠ 1：{gate_ev}｜觸發列逐筆 vs 矩陣：{gate_tr}")
    if gate_ev or gate_tr:
        raise SystemExit("⛔ 標籤閘門")
    # 一年內曾跌 15%（基準）
    rmn = pd.DataFrame(rev.T).rolling(250, min_periods=1).min().to_numpy().T[:, ::-1]
    fmin = np.concatenate([rmn[:, 1:], np.full((S5, 1), np.nan)], axis=1)[:, c0_:c1_]
    with np.errstate(invalid="ignore"):
        dd1 = fmin <= cS * 0.85 * (1 + 1e-9)
    def250 = barS & (hdS >= 250) & (posS + 250 <= icut)[None, :]
    for (grp, seg, ver), mk in masks.items():
        dm = mk & def250
        free.append({"分組": grp, "段": seg, "版本": ver, "x": "base", "觸發數": int(mk.sum()), "每天平均": float(mk.sum() / nd_seg[seg]),
                     "一年跌15%定義域": int(dm.sum()), "一年內曾跌15%": float((dd1 & dm).sum() / max(int(dm.sum()), 1)) if dm.sum() else np.nan})
    # ── 觸發列每格統計
    df = pd.DataFrame({"f4": tf4, "el": tel, "mon": tmon, "xi": txi})
    for seg, (sa, sb) in SEGS.items():
        for ver in VERS:
            for grp in ("F4", "不帶F4"):
                gm = (tf4 if grp == "F4" else ~tf4) & (tmon >= sa) & (tmon <= sb) & (tel if ver != "全部" else True)
                for xi, xk in enumerate(XK):
                    m = gm & (txi == xi)
                    q = np.flatnonzero(m)
                    d250 = (thd[q] >= 250) & (td[q] + 250 <= icut)
                    free.append({"分組": grp, "段": seg, "版本": ver, "x": xk, "觸發數": int(len(q)), "每天平均": float(len(q) / nd_seg[seg]),
                                 "一年跌15%定義域": int(d250.sum()), "一年內曾跌15%": float((DN[q][d250] <= 250).mean()) if d250.any() else np.nan})
                    for hi, H in enumerate(HS5):
                        dfr = (thd[q] >= H) & (td[q] + H <= icut)
                        qq = q[dfr]
                        if not len(qq):
                            continue
                        mh = MHH[qq, hi]; r_ = rr[qq]
                        for gi, g in enumerate(GS5):
                            c = hi * len(GS5) + gi
                            lab = UPG[qq, gi] <= H
                            dnf = (DN[qq] <= H) & (DN[qq] < UPG[qq, gi])
                            tag = ("4 漲幾%", grp, seg, ver)
                            rows.append((*tag, f"{xk}|rate", "mean", c, len(qq), float(lab.mean())))
                            rows.append((*tag, f"{xk}|mh", "med", c, len(qq), float(np.quantile(mh, 0.5))))
                            rows.append((*tag, f"{xk}|dnfirst", "mean", c, len(qq), float(dnf.mean())))
                            if lab.any():
                                ms = mh[lab]; cap = ms / (1 + ms - 1 / (1 + r_[lab]))
                                rows.append((*tag, f"{xk}|mh_s", "med", c, int(lab.sum()), float(np.quantile(ms, 0.5))))
                                rows.append((*tag, f"{xk}|cap", "med", c, int(lab.sum()), float(np.quantile(cap, 0.5))))
            log(f"[彙總 4] {seg}｜{ver}")
    return rows, free


# ═════════════ 網頁 ═════════════
def pc(x, d=0, sign=False):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(x):
        return "—"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def fx(x, d=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x:,.{d}f}"


def page():
    from backtest.researchMine_page import CSS
    GR = pd.read_csv(os.path.join(OUT, "grid.csv")); FR = pd.read_csv(os.path.join(OUT, "free.csv")); BH = pd.read_csv(os.path.join(OUT, "byH.csv"))
    SM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    g = GR.set_index(["部分", "分組", "段", "版本", "鍵", "統計"])
    fr = FR.set_index(["分組", "段", "版本", "x"])

    def V(part, key, stat, grp="F4", seg="合併", ver="全部", col="網格中位"):
        try:
            return g.loc[(part, grp, seg, ver, key, stat)][col]
        except KeyError:
            return np.nan

    def F(x, col, grp="F4", seg="合併", ver="全部"):
        try:
            return fr.loc[(grp, seg, ver, x)][col]
        except KeyError:
            return np.nan
    P1, P2, P3, P4 = "1 到頂點", "2 漲停", "3 訊號", "4 漲幾%"
    css = CSS.replace("max-width:820px", "max-width:980px") + "<style>td small{color:var(--note)}.k{font-size:.8em;color:var(--note)}</style>"
    cF = SM["件數"]["F4｜合併｜全部"]; cN = SM["件數"]["不帶F4｜合併｜全部"]
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>連續虧損飆股什麼時候抓得到</title>", css, "</head><body>",
         "<h1>連續虧損（F4）的飆股：要漲到幾 % 才抓得出來？中間幾根漲停？一般幾天到頂？</h1>",
         "<p class='note'>使用者原話：「如果每天關注這些股票你要漲到幾%才抓的出來？或是漲幾趴可以算是飆股可以買進？中間會有很多漲停嗎？你的一般到頂點會是幾天？」｜"
         f"接續「連續虧損飆股為什麼漲」｜只描述（參考、不計檢定數、不需登錄）｜回測線執行，讀法寫死 {html.escape(TAGT)}。"
         "這是歷史統計，不是對任何一檔的預測或買賣建議。</p>"]
    # ── 結論
    d50 = V(P1, "days", "med"); d25 = V(P1, "days", "q25"); d75 = V(P1, "days", "q75")
    s50 = V(P1, "psd", "med"); g50 = V(P1, "gain", "med")
    bh0 = BH[BH["分組"] == "F4"].set_index("H")
    CLs = pd.read_csv(os.path.join(OUT, "cells.csv.gz"))
    CLs = CLs[(CLs["部分"] == P4) & (CLs["段"] == "合併") & (CLs["版本"] == "全部")].set_index(["分組", "鍵", "格"])
    EXC = ["H60_g50%", "H120_g50%", "H120_g100%", "H250_g100%", "H250_g200%"]

    def CV(grp, key, cn):
        try:
            return CLs.loc[(grp, key, cn)]["值"]
        except KeyError:
            return np.nan
    H.append("<div class='box'><b>結論（2017-03～2026-08，全部上市櫃；每個數字 ＝ 250 種飆股定義各算一次取中位）</b><ul>")
    H.append(f"<li>對象：起漲前一個月底帶 F4 連續虧損的飆股，{cF['不同股票']} 檔、{cF['不同 (股, 起漲日)']:,} 個起漲點；參照 ＝ 同期不帶 F4 的飆股（{cN['不同股票']} 檔）。</li>")
    H.append(f"<li><b>一般幾天到頂點</b>：起漲日到頂點中位 <b>{fx(d50)}</b> 個交易日（一半落在 {fx(d25)}～{fx(d75)}）；這段漲幅中位 <b>{pc(g50)}</b>。"
             f"⚠ 這個天數被飆股定義的「H 天內」綁住（H 越長天數越長）；不設天數上限、跟著創新高到第一次回落 30% 為止的頂點，中位 <b>{fx(s50)}</b> 個交易日"
             f"（不帶 F4 的飆股：{fx(V(P1, 'days', 'med', '不帶F4'))}、不設上限 {fx(V(P1, 'psd', 'med', '不帶F4'))}）。"
             "依定義的 H 看：" + "、".join(f"H{h_} 天的定義 → {fx(bh0.loc[h_, '天數中位'])} 天（不設上限 {fx(bh0.loc[h_, '不設H天數中位'])}）" for h_ in (20, 60, 120, 250) if h_ in bh0.index)
             + "——頂點幾乎都落在 H 的最後幾天，代表這個問題的答案主要由「你把飆股定義成幾天內漲多少」決定，資料本身說不出一個固定天數。</li>")
    H.append(f"<li><b>中間漲停多不多</b>：起漲到頂點這段，漲停天數中位 <b>{fx(V(P2, 'lu_n', 'med'))}</b> 天、平均 {fx(V(P2, 'lu_n', 'mean'), 1)} 天；"
             f"0 天 {pc(V(P2, 'lu_0', 'mean'))}、1～2 天 {pc(V(P2, 'lu_1_2', 'mean'))}、3～5 天 {pc(V(P2, 'lu_3_5', 'mean'))}、6～10 天 {pc(V(P2, 'lu_6_10', 'mean'))}、超過 10 天 {pc(V(P2, 'lu_gt10', 'mean'))}；"
             f"最長連續漲停中位 {fx(V(P2, 'lu_streak', 'med'))} 根（連 3 根以上 {pc(V(P2, 'stk_ge3', 'mean'))}）；漲停日占這段 K 棒的中位 {pc(V(P2, 'lu_ratio', 'med'), 1)}"
             f"（不帶 F4 的飆股：漲停中位 {fx(V(P2, 'lu_n', 'med', '不帶F4'))} 天、0 天 {pc(V(P2, 'lu_0', 'mean', '不帶F4'))}）。</li>")
    sg = [(k, nm) for k, nm, _ in SIG if k != "lu"]
    sg_txt = "；".join(f"{nm.split('（')[0]} 出現 {pc(V(P3, f'{k}|has', 'mean'))}、出現時已漲 <b>{pc(V(P3, f'{k}|gain', 'med'))}</b>、還剩 {pc(1 - V(P3, f'{k}|done', 'med'))} 的路"
                     for k, nm in sg)
    H.append(f"<li><b>差別訊號出現時已經漲了多少</b>（起漲到頂點這段第一次出現；只算有出現的）：{sg_txt}。</li>")
    best = None
    for xk in XK:
        r_ = V(P4, f"{xk}|rate", "mean")
        if best is None or (np.isfinite(r_) and r_ > best[1]):
            best = (xk, r_)
    rb = V(P4, "base|rate", "mean")
    tr = "；".join(f"從 60 日低點漲 {xk[1:]}%：之後變飆股 {pc(V(P4, f'{xk}|rate', 'mean'), 1)}、之後最高還能漲 {pc(V(P4, f'{xk}|mh', 'med'))}、"
                   f"變飆股的能吃到全程 {pc(V(P4, f'{xk}|cap', 'med'))}" for xk in ("x10", "x30", "x50", "x100"))
    H.append(f"<li><b>漲幾 % 之後變飆股的機率</b>（帶 F4 的股票，從 60 日低點起漲到 x 的那天起算）：不看漲幅的任何一天 {pc(rb, 1)}；{tr}。"
             f"比例最高的是 {best[0][1:]}%（{pc(best[1], 1)}）。"
             + f"每天平均：帶 F4 的股票約 {fx(F('base', '每天平均'))} 檔，其中當天第一次漲到 10% 的約 {fx(F('x10', '每天平均'), 1)} 檔、到 50% 的約 {fx(F('x50', '每天平均'), 1)} 檔。"
             "⚠ 這是事後標籤的歷史比例，不是買點；一年內曾跌 15% 的比例也隨 x 變高（見第四節）。</li>")
    H.append("<li>⚠ 起漲日、頂點、「變飆股」全部是事後才知道的；訊號出現時已漲幾 % 是拿真飆股回頭量的，沒變飆股的股票同樣會出現這些訊號（見「連續虧損飆股為什麼漲」的對照組）。</li>")
    H.append("</ul></div>")
    # ── 一
    H.append("<h2>一、起漲到頂點要幾天、漲多少（全部上市櫃、2017-03～2026-08）</h2>")
    H.append("<p class='note'>條件：飆股 250 種定義（H 天內漲 g 以上）；起漲日 t ＝ 第一個「H 天內會漲到 g」的日子；頂點 P ＝ t 之後 H 天內最高收盤那天；"
             "天數 ＝ 交易日（含停牌日）；「不設上限頂點」＝ 從 P 起跟著創新高、到第一次從最高回落 30% 前的最高點。每格先算分位數，再取 250 格中位。</p>")
    hd = ["項目", "p10", "p25", "中位", "p75", "p90", "不帶 F4 中位"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    for k, nm, f_ in (("days", "起漲到頂點（交易日）", lambda v: fx(v)), ("gain", "起漲到頂點漲幅", lambda v: pc(v)),
                      ("psd", "起漲到不設上限頂點（交易日）", lambda v: fx(v)), ("psg", "起漲到不設上限頂點漲幅", lambda v: pc(v))):
        H.append(f"<tr><td class=l>{nm}</td>" + "".join(f"<td>{f_(V(P1, k, st_))}</td>" for st_ in ("q10", "q25")) + f"<td><b>{f_(V(P1, k, 'med'))}</b></td>"
                 + "".join(f"<td>{f_(V(P1, k, st_))}</td>" for st_ in ("q75", "q90")) + f"<td>{f_(V(P1, k, 'med', '不帶F4'))}</td></tr>")
    H.append("</table></div>")
    H.append(f"<p class='note'>不設上限頂點到資料尾（2026-09-24）還沒回落 30%（未完）的比例：{pc(V(P1, 'pso', 'mean'), 1)}（只能算到資料尾）。"
             "「中位」那欄的 250 格分佈 p10～p90：起漲到頂點 " + f"{fx(V(P1, 'days', 'med', col='p10'))}～{fx(V(P1, 'days', 'med', col='p90'))} 天。</p>")
    bh = BH[BH["分組"] == "F4"].set_index("H"); bn = BH[BH["分組"] == "不帶F4"].set_index("H")
    H.append("<p class='note'>依 H 分（參考；同一個 H 的 10 個 g 各格中位再取中位）：" + "；".join(
        f"H{h_} 天 → {fx(bh.loc[h_, '天數中位'])} 天（不設上限 {fx(bh.loc[h_, '不設H天數中位'])}）" for h_ in (20, 60, 120, 180, 250) if h_ in bh.index) + "。</p>")
    # ── 二
    H.append("<h2>二、起漲到頂點中間有多少漲停</h2>")
    H.append("<p class='note'>條件：窗 ＝ 起漲日到頂點（含兩端）；漲停用未還原收盤、10%（2015-06 以前 7%）、還原事件日與上市前 5 根不判；連續漲停看有效 K 棒（停牌日跳過不斷）。</p>")
    hd = ["項目", "F4 飆股", "<small>250 格 p10～p90</small>", "不帶 F4 的飆股"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    for k, st_, nm, f_ in (("lu_0", "mean", "漲停 0 天", pc), ("lu_1_2", "mean", "漲停 1～2 天", pc), ("lu_3_5", "mean", "漲停 3～5 天", pc),
                           ("lu_6_10", "mean", "漲停 6～10 天", pc), ("lu_gt10", "mean", "漲停超過 10 天", pc),
                           ("lu_n", "med", "漲停天數中位", fx), ("lu_n", "mean", "漲停天數平均", lambda v: fx(v, 1)), ("lu_n", "q90", "漲停天數 p90", fx),
                           ("lu_streak", "med", "最長連續漲停（根）中位", fx), ("stk_ge2", "mean", "最長連續漲停 ≥ 2 根", pc), ("stk_ge3", "mean", "最長連續漲停 ≥ 3 根", pc),
                           ("stk_ge5", "mean", "最長連續漲停 ≥ 5 根", pc), ("lu_ratio", "med", "漲停日占這段 K 棒（中位）", lambda v: pc(v, 1)),
                           ("lu_ratio", "mean", "漲停日占這段 K 棒（平均）", lambda v: pc(v, 1))):
        H.append(f"<tr><td class=l>{nm}</td><td><b>{f_(V(P2, k, st_))}</b></td><td><small>{f_(V(P2, k, st_, col='p10'))}～{f_(V(P2, k, st_, col='p90'))}</small></td>"
                 f"<td>{f_(V(P2, k, st_, '不帶F4'))}</td></tr>")
    H.append("</table></div>")
    # ── 三
    H.append("<h2>三、差別訊號第一次出現時，股價已經從起漲點漲了多少</h2>")
    H.append("<p class='note'>條件：只看起漲日到頂點這段（含兩端）第一次出現；「已漲」＝ 出現那天收盤 ÷ 起漲日收盤 − 1；「還剩幾成」＝ 1 −（出現時已漲的價差 ÷ 起漲到頂點的價差）；"
             "「還剩漲幅」＝ 頂點收盤 ÷ 出現那天收盤 − 1；生效日：重大訊息 13:30 後算隔天、季報用上傳時戳隔天、月營收用次月 10 日（2026 起 15 日）後第一個交易日（法定期限代理，很多公司更早公布）。"
             "出現比例以全部 F4 飆股為分母，其餘欄只算有出現的。</p>")
    hd = ["訊號", "窗內出現", "起漲前 60 日已出現", "出現時已漲（中位）", "<small>p25～p75</small>", "已走完幾成", "還剩幾成", "還剩漲幅（中位）", "起漲後第幾天（中位）",
          "不帶 F4：出現／已漲"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    for k, nm, _ in SIG:
        H.append(f"<tr><td class=l>{html.escape(nm)}</td><td>{pc(V(P3, f'{k}|has', 'mean'))}</td><td>{pc(V(P3, f'{k}|pre', 'mean')) if k != 'grp' else '—'}</td>"
                 f"<td><b>{pc(V(P3, f'{k}|gain', 'med'))}</b></td><td><small>{pc(V(P3, f'{k}|gain', 'q25'))}～{pc(V(P3, f'{k}|gain', 'q75'))}</small></td>"
                 f"<td>{pc(V(P3, f'{k}|done', 'med'))}</td><td><b>{pc(1 - V(P3, f'{k}|done', 'med'))}</b></td><td>{pc(V(P3, f'{k}|up', 'med'))}</td>"
                 f"<td>{fx(V(P3, f'{k}|lag', 'med'))}</td><td>{pc(V(P3, f'{k}|has', 'mean', '不帶F4'))}／{pc(V(P3, f'{k}|gain', 'med', '不帶F4'))}</td></tr>")
    H.append("</table></div>")
    H.append("<p class='note'>「已走完幾成」與「還剩幾成」各是 250 格中位，所以兩欄相加剛好 100%（同一格內 1 − 中位 ＝ 中位的反面）。族群一起漲的「起漲前」不另報（它的窗本來就含起漲前 20 日；"
             "起漲前就有別檔起漲的，出現日算起漲日、已漲 0%）。⚠ 別檔的「起漲日」本身也是事後才知道的。</p>")
    # ── 四
    H.append("<h2>四、漲幾 % 之後變飆股的機率（帶 F4 的股票，每天看）</h2>")
    H.append("<p class='note'>條件：每檔每天算「收盤 ÷ 最近 60 根 K 棒（含當天）最低收盤 − 1」；第一次達到 x 的那天記一次，之後 60 根內不重複記；當天起漲前一個月底帶 F4（不帶 F4 的另列）。"
             "「變飆股」＝ 從那天起 H 天內最高收盤 ≥ 那天收盤 ×（1＋g），250 格各算再取中位；「還能漲」＝ 那天之後 H 天內最高收盤 ÷ 那天收盤 − 1；"
             "「能吃到全程幾成」＝（頂點 − 那天）÷（頂點 − 60 日低點），只算變飆股的；「還沒變飆股先跌 15%」＝ H 天內先跌到那天收盤 ×0.85、才（或沒）漲到門檻；"
             "「一年內曾跌 15%」＝ 之後 250 個交易日內任一天收盤 ≤ 那天 ×0.85（不分格）。</p>")
    hd = ["從 60 日低點已漲", "每天平均幾檔", "之後變飆股", "<small>250 格 p10～p90</small>", "÷ 不看漲幅", "之後還能漲（中位）", "變飆股的還能漲", "變飆股的吃到全程",
          "還沒變飆股先跌 15%", "一年內曾跌 15%", "不帶 F4：變飆股／還能漲"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    H.append(f"<tr class='y'><td class=l>不看漲幅（帶 F4 的每一天）</td><td>{fx(F('base', '每天平均'), 0)}</td><td>{pc(V(P4, 'base|rate', 'mean'), 1)}</td>"
             f"<td><small>{pc(V(P4, 'base|rate', 'mean', col='p10'), 1)}～{pc(V(P4, 'base|rate', 'mean', col='p90'), 1)}</small></td><td>1.00</td><td>—</td><td>—</td><td>—</td><td>—</td>"
             f"<td>{pc(F('base', '一年內曾跌15%'))}</td><td>{pc(V(P4, 'base|rate', 'mean', '不帶F4'), 1)}／—</td></tr>")
    for xk in XK:
        H.append(f"<tr><td class=l>{xk[1:]}%</td><td>{fx(F(xk, '每天平均'), 1)}</td><td><b>{pc(V(P4, f'{xk}|rate', 'mean'), 1)}</b></td>"
                 f"<td><small>{pc(V(P4, f'{xk}|rate', 'mean', col='p10'), 1)}～{pc(V(P4, f'{xk}|rate', 'mean', col='p90'), 1)}</small></td>"
                 f"<td>{fx(V(P4, f'{xk}|lift', 'ratio'), 2)}</td><td>{pc(V(P4, f'{xk}|mh', 'med'))}</td><td>{pc(V(P4, f'{xk}|mh_s', 'med'))}</td>"
                 f"<td><b>{pc(V(P4, f'{xk}|cap', 'med'))}</b></td><td>{pc(V(P4, f'{xk}|dnfirst', 'mean'))}</td><td>{pc(F(xk, '一年內曾跌15%'))}</td>"
                 f"<td>{pc(V(P4, f'{xk}|rate', 'mean', '不帶F4'), 1)}／{pc(V(P4, f'{xk}|mh', 'med', '不帶F4'))}</td></tr>")
    H.append("</table></div>")
    H.append("<p class='note'>⚠ 飆股定義照使用者規矩用 seq6 網格、取各格中位；中位會被網格裡很嚴的格拉低，所以「之後變飆股」的絕對比例看起來很小，請看相對倍數與隨 x 的變化。各格數字在 cells.csv.gz。</p>")
    H.append("<p class='note'>讀法：同一列越往右越是代價——x 越高，「之後變飆股」的比例可能越高，但能吃到的全程比例越少。"
             "「每天平均幾檔」＝ 段內觸發數 ÷ 段內交易日數。「÷ 不看漲幅」＝ 同一格觸發列比例 ÷ 帶 F4 每一天的比例，取 250 格中位。⚠「變飆股」是事後標籤；這張表 ⛔ 不是買點。</p>")
    # ── 五：兩段
    H.append("<h2>五、兩段比較（全部上市櫃、F4）</h2>")
    hd = ["項目", "2017-03～2021", "2022～2026-08", "合併"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    items = [(P1, "days", "med", "起漲到頂點天數中位", fx), (P1, "psd", "med", "不設上限頂點天數中位", fx), (P1, "gain", "med", "起漲到頂點漲幅中位", pc),
             (P2, "lu_n", "med", "漲停天數中位", fx), (P2, "lu_0", "mean", "漲停 0 天", pc), (P2, "lu_gt10", "mean", "漲停超過 10 天", pc), (P2, "lu_streak", "med", "最長連續漲停中位", fx)]
    items += [(P3, f"{k}|gain", "med", f"{nm.split('（')[0]}：出現時已漲", pc) for k, nm, _ in SIG]
    items += [(P3, f"{k}|has", "mean", f"{nm.split('（')[0]}：窗內出現", pc) for k, nm, _ in SIG]
    items += [(P4, "base|rate", "mean", "不看漲幅：之後變飆股", lambda v: pc(v, 1))]
    items += [(P4, f"{xk}|rate", "mean", f"已漲 {xk[1:]}%：之後變飆股", lambda v: pc(v, 1)) for xk in XK]
    items += [(P4, f"{xk}|cap", "med", f"已漲 {xk[1:]}%：變飆股的吃到全程", pc) for xk in XK]
    for part, k, st_, nm, f_ in items:
        H.append(f"<tr><td class=l>{html.escape(nm)}</td>" + "".join(f"<td>{f_(V(part, k, st_, seg=sg_))}</td>" for sg_ in ("探索", "確認", "合併")) + "</tr>")
    H.append("</table></div>")
    H.append("<p class='note'>每天平均幾檔（F4）：" + "；".join(f"{xk[1:]}% {fx(F(xk, '每天平均', seg='探索'), 1)} → {fx(F(xk, '每天平均', seg='確認'), 1)}" for xk in XK)
             + f"；帶 F4 的股票每天 {fx(F('base', '每天平均', seg='探索'))} → {fx(F('base', '每天平均', seg='確認'))} 檔。</p>")
    # ── 六：W1
    cW = SM["件數"]["F4｜合併｜W1 母體內"]
    H.append(f"<h2>六、只看 W1 母體內（營量／營飆能買的股票）</h2><p class='note'>起漲前一個月底在 W1 母體內的 F4 飆股：{cW['不同股票']} 檔、{cW['不同 (股, 起漲日)']:,} 個起漲點；"
             "第四部分的觸發日也只取當時在 W1 母體內的。</p>")
    hd = ["項目", "W1 母體內", "全部上市櫃"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    for part, k, st_, nm, f_ in items:
        H.append(f"<tr><td class=l>{html.escape(nm)}</td><td>{f_(V(part, k, st_, ver='W1 母體內'))}</td><td>{f_(V(part, k, st_))}</td></tr>")
    H.append("</table></div>")
    H.append("<p class='note'>W1 每天平均幾檔（F4）：" + "；".join(f"{xk[1:]}% {fx(F(xk, '每天平均', ver='W1 母體內'), 1)}" for xk in XK)
             + f"；W1 內帶 F4 的股票每天 {fx(F('base', '每天平均', ver='W1 母體內'))} 檔。完整表見 grid.csv、free.csv。</p>")
    # ── 七：讀法
    H.append("<h2>七、怎麼算的、限制</h2><ul class='note'>"
             "<li>飆股 ＝ 飆股回推網格的 250 種定義（H ＝ 10～250 天 × g ＝ 50%～1000%），s5 全日曆名單、上市櫃普通股（含已下市），起漲日加 H 在 2026-08-31 以前；"
             "每個數字是 250 格各算一次的中位（只算有資料的格）。同一檔在不同格會重複出現。</li>"
             "<li>F4 連續虧損 ＝ 起漲日（第四部分：觸發日）前最後一個月底，最近 4 季 EPS 合計虧且最近一季虧，或最近 8 季有 6 季以上虧（當時已公布的財報）；事件與「連續虧損股的飆股特徵」「連續虧損飆股為什麼漲」逐筆相同。</li>"
             "<li>價格用還原收盤（停牌日沿用前一收盤）；漲停用未還原收盤判。</li>"
             "<li>⚠ 起漲日的定義是「H 天內會漲到 g 的第一天」，所以起漲到頂點的天數天生貼近 H；不設上限頂點的天數比較接近「這波漲多久」。</li>"
             "<li>⚠ 第三部分的訊號是在真飆股的上漲過程中回頭量的；同樣的訊號在沒變飆股的股票也常出現，出現了 ≠ 會變飆股。</li>"
             "<li>⚠ 第四部分的「變飆股」是事後標籤，觸發本身也沒有扣成本、沒有考慮漲停買不到；只描述歷史比例，⛔ 不是買點、不是策略。</li>"
             "<li>只描述：不計檢定數、不判定；⛔ 不給買賣建議。</li></ul>")
    gt = SM["閘門"]
    H.append(f"<p class='note'>閘門：自載收盤重算 s5 頂點 P 與漲幅 M 不同 {gt['P 不同']}／{gt['M 不同']}；起漲到頂點天數網格中位與「連續虧損飆股為什麼漲」相同"
             f"（{fx(gt['P−t 中位網格（中位、p10、p90）'][0])}、{fx(gt['P−t 中位網格（中位、p10、p90）'][1])}、{fx(gt['P−t 中位網格（中位、p10、p90）'][2])}）；"
             f"六個訊號的窗內出現比例、漲停 ≥ 1／3／5 天與該件逐段逐版相同（不同 {gt['和 researchMineF4why 不同']}）。</p>")
    if CK:
        H.append(f"<p class='note'>抽樣查核（獨立寫法重算 2 格的第一～四部分、200 檔的觸發逐筆）：{'0 不同，過' if CK.get('過') else '有不同，見 check.json'}。</p>")
    H.append("<p class='note'>檔案：backtest/resultsMine/F4when/（cells.csv.gz 每格、grid.csv 網格中位、free.csv 不分格、byH.csv 依 H）。</p>")
    H.append("</body></html>")
    open(os.path.join(OUT, "連續虧損飆股什麼時候抓得到.html"), "w", encoding="utf-8").write("\n".join(H))


# ═════════════ 查核（獨立寫法）═════════════
def check():
    """⛔ 不呼叫本檔本體、researchMine、researchMineF4、researchMineF4why 的函式；只讀原始 CSV、s5 原表、flags_main.npz、本體輸出；還原收盤用 data.load_stock（輸入）。"""
    T0 = time.time()
    hs = tuple(range(10, 251, 10)); gs = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
    cname = lambda c: f"H{hs[c // 10]}_g{int(round(gs[c % 10] * 100))}%"
    res = {"時間": now_tpe() + "（台北）", "種子": [20261009, 20261010]}
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz"))
    CLa = CL[(CL["段"] == "合併") & (CL["版本"] == "全部")]
    REF = {(r.部分, r.分組, r.鍵, r.統計, int(r.cell)): (int(r.n), float(r.值)) for r in CLa.itertuples()}
    mainp = os.path.expanduser("~/h2data/mine_796d94c9dafd/data"); s5w = os.path.expanduser("~/s5work")
    zz = np.load(os.path.expanduser("~/minework/flags_main.npz")); z = {k: zz[k] for k in ("sids", "me", "F4", "EL")}
    sids = [str(x) for x in z["sids"]]; jx = {x: j for j, x in enumerate(sids)}; me = pd.to_datetime(pd.Series(z["me"])).values
    calm = pd.to_datetime(pd.read_csv(os.path.join(mainp, "meta", "calendar_twse.csv"))["date"]).sort_values().reset_index(drop=True)
    c1 = pd.read_csv(os.path.expanduser("~/earlydata/3edc0e2206/main/data/meta/calendar_twse.csv"))["date"]
    c2 = pd.read_csv(os.path.join(mainp, "meta", "calendar_twse.csv"))["date"]
    cal5 = pd.DatetimeIndex(pd.to_datetime(pd.concat([c1, c2[c2 <= "2026-09-24"]], ignore_index=True)))
    N5 = len(cal5); assert N5 == 5571
    c5s = [str(x.date()) for x in cal5]; d5 = {t: i for i, t in enumerate(c5s)}
    uni = pd.read_csv(os.path.join(s5w, "uni.csv"), dtype=str)
    U = uni["stock_id"].tolist(); MK = uni["market"].tolist(); ux = {x: i for i, x in enumerate(U)}
    E = np.load(os.path.join(s5w, "events.npz"))
    Ec, Ed, Es, EP = (E[k].astype(int) for k in ("cell", "d", "s", "P"))
    Epd, Epg, Epo = E["ps_d"].astype(int), E["ps_g"].astype(float), E["ps_open"].astype(int)
    icut = d5["2026-08-31"]
    okE = Ed + np.array(hs)[Ec // 10] <= icut
    bar5 = np.load(os.path.join(s5w, "bar.npy")); hdef = np.load(os.path.join(s5w, "hdef.npy"))
    rng = np.random.default_rng(20261009)
    cand = sorted({c for (p_, g_, k_, st_, c), (n_, v_) in REF.items() if p_ == "1 到頂點" and g_ == "F4" and k_ == "days" and st_ == "med" and n_ >= 30})
    pick = [int(x) for x in rng.choice(cand, 2, replace=False)]
    res["抽到的格"] = [cname(c) for c in pick]

    def mon_of(p):
        return c5s[p][:7]

    def f4_at(x, p):                                                          # (known, F4, EL) at 嚴格之前最後判定日
        if x not in jx:
            return False, False, False
        im = int(np.searchsorted(me, np.datetime64(cal5[p]), side="left")) - 1
        if im < 0:
            return False, False, False
        return True, bool(z["F4"][im, jx[x]]), bool(z["EL"][im, jx[x]])
    groups = {}
    for c in pick:
        F4l, NFl = [], []
        for i in np.flatnonzero((Ec == c) & okE):
            if not ("2017-03" <= mon_of(Ed[i]) <= "2026-08"):
                continue
            kn, f4, _ = f4_at(U[Es[i]], Ed[i])
            if kn:
                (F4l if f4 else NFl).append(i)
        groups[c] = (F4l, NFl)
    need = set()
    for c in pick:
        for L_ in groups[c]:
            need |= {int(Es[i]) for i in L_}
    needx = {U[i] for i in need}
    D.DATA = ST
    CFd = {}

    def closes(si):
        if si not in CFd:
            st = D.load_stock(U[si], MK[si], cal5)
            CFd[si] = None if st is None else st.df["close"].ffill().to_numpy(float)
        return CFd[si]
    # ── 訊號事件日（自己讀）
    EVD = {}

    def put(si, ty, dd):
        if 0 <= dd < N5:
            EVD.setdefault((si, ty), []).append(dd)
    calv = calm.values
    fh = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "eps_q", "eps_ytd"]) for f in sorted(glob.glob(os.path.join(mainp, "mops", "fin_hist", "*.csv")))])
    fh = fh.drop_duplicates(["stock_id", "period"], keep="last")
    fd = pd.read_csv(os.path.join(mainp, "meta", "filing_dates.csv"), dtype=str)
    fd["dd"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce"); fd = fd.dropna(subset=["dd"])
    up = fd.groupby(["stock_id", "year", "season"])["dd"].min()
    up.index = [(a_, int(b_), int(c_)) for a_, b_, c_ in up.index]; up = up.to_dict()
    for x, gg in fh.groupby("stock_id"):
        if x not in needx:
            continue
        si = ux[x]
        ytd = {pd.Period(p, "Q"): v for p, v in zip(gg["period"], pd.to_numeric(gg["eps_ytd"], errors="coerce"))}
        qq = {pd.Period(p, "Q"): v for p, v in zip(gg["period"], pd.to_numeric(gg["eps_q"], errors="coerce"))}
        ee = {}
        for P_, v in ytd.items():
            e = v if P_.quarter == 1 else (v - ytd[P_ - 1] if (P_ - 1) in ytd and np.isfinite(v) and np.isfinite(ytd[P_ - 1]) else np.nan)
            if not np.isfinite(e) and np.isfinite(qq.get(P_, np.nan)):
                e = qq[P_]
            ee[P_] = e
        for P_, e0 in ee.items():
            ts = up.get((x, P_.year, P_.quarter))
            if ts is not None:
                k = int(np.searchsorted(calv, np.datetime64(ts), side="right"))
            else:
                dl = pd.Timestamp(P_.year + 1, 3, 31) if P_.quarter == 4 else pd.Timestamp(P_.year, *{1: (5, 15), 2: (8, 14), 3: (11, 14)}[P_.quarter])
                k = int(np.searchsorted(calv, np.datetime64(dl), side="right")) + 5
            if k >= len(calm):
                continue
            ds = str(calm.iloc[k].date())
            if ds not in d5:
                continue
            dd = d5[ds]; e1 = ee.get(P_ - 1, np.nan); e4 = ee.get(P_ - 4, np.nan)
            if e1 < 0 < e0: put(si, "eq_turn1", dd)
            if e4 < 0 < e0: put(si, "eq_turn4", dd)
    revd = os.path.expanduser("~/h2data/indrev_796d94c9dafd/data/mops/revenue_hist")
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in sorted(glob.glob(os.path.join(revd, "*.csv")))])
    rv["stock_id"] = rv["stock_id"].str.strip(); rv = rv.drop_duplicates(["stock_id", "period"], keep="last")
    for x, gg in rv.groupby("stock_id"):
        if x not in needx:
            continue
        si = ux[x]
        R_ = dict(zip(gg["period"], pd.to_numeric(gg["當月營收"], errors="coerce")))
        val = lambda P_: R_.get(str(P_), np.nan)
        for p, v in R_.items():
            if not np.isfinite(v):
                continue
            P_ = pd.Period(p, "M"); Q_ = P_ + 1
            cut = pd.Timestamp(Q_.year, Q_.month, 10 if p <= "2025-12" else 15)
            k = int(np.searchsorted(calv, np.datetime64(cut), side="right"))
            if k >= len(calm):
                continue
            ds = str(calm.iloc[k].date())
            if ds not in d5:
                continue
            dd = d5[ds]
            g12 = val(P_ - 12); y = v / g12 - 1 if (np.isfinite(g12) and g12 > 0) else np.nan
            pv = [val(P_ - k_) for k_ in range(1, 25)]; pv = [w_ for w_ in pv if np.isfinite(w_)]
            if y > 0.5: put(si, "rv_y50", dd)
            if len(pv) >= 18 and v >= max(pv): put(si, "rv_h24", dd)
    src = open("backtest/researchNewsCat.py", encoding="utf-8").read()
    i0 = src.index("SEQ2_SRC = '''") + len("SEQ2_SRC = '''"); i1 = src.index("'''", i0)
    ns: dict = {}; exec(src[i0:i1], ns); clf = ns["classify"]
    nd_ = os.path.expanduser("~/msdata/8425186bd20cdef4d39ac039ad2a6eda0903a8bb/data/mops/news")
    seen = set(); c5set = set(c5s)
    for y in range(2016, 2027):
        Nn = pd.read_csv(os.path.join(nd_, f"{y}.csv"), dtype=str, keep_default_na=False)
        for dt, tm, x, mk, se, sj in zip(Nn["date"], Nn["time"], Nn["stock_id"], Nn["market"], Nn["serial"], Nn["subject"]):
            kk = (dt, tm, x, se)
            if kk in seen:
                continue
            seen.add(kk)
            x = x.strip()
            if mk not in ("sii", "otc") or x not in needx:
                continue
            k = bisect.bisect_left(c5s, dt)
            if dt in c5set and tm[:5] > "13:30":
                k += 1
            if k >= N5:
                continue
            si = ux[x]; cc = clf(sj)
            if cc in (6, 11, 2):
                put(si, "C", k)
            if "私募" in sj:
                put(si, "kw_pp", k)
    at = pd.read_csv(os.path.join(mainp, "meta", "attention.csv"), dtype=str, usecols=["stock_id", "date"]).dropna()
    for x, dt in set(zip(at["stock_id"].str.strip(), at["date"])):
        if x in needx:
            put(ux[x], "att", bisect.bisect_left(c5s, dt))
    dp = pd.read_csv(os.path.join(mainp, "meta", "disposal.csv"), dtype=str, usecols=["stock_id", "start_date"]).dropna()
    for x, dt in set(zip(dp["stock_id"].str.strip(), dp["start_date"])):
        if x in needx:
            put(ux[x], "disp", bisect.bisect_left(c5s, dt))

    def tick(p):
        return 0.01 if p < 10 else 0.05 if p < 50 else 0.1 if p < 100 else 0.5 if p < 500 else 1.0 if p < 1000 else 5.0
    for si in sorted(need):
        x = U[si]; pth = os.path.join(ST, "stocks", x + ".csv")
        if not os.path.exists(pth):
            continue
        raw = pd.read_csv(pth, dtype=str, usecols=["date", "close"]).drop_duplicates("date")
        rc = dict(zip(raw["date"], pd.to_numeric(raw["close"], errors="coerce")))
        bars = np.flatnonzero(bar5[si])
        if len(bars) < 2:
            continue
        evd = set(); bds = [c5s[b] for b in bars]
        pa = os.path.join(ST, "adj", x + ".csv")
        if os.path.exists(pa):
            for dt in pd.read_csv(pa, dtype=str)["date"]:
                k = bisect.bisect_left(bds, str(dt)[:10])
                if k < len(bars):
                    evd.add(k)
        first5 = c5s[bars[0]] > "2015-01-12"
        for k in range(1, len(bars)):
            if k in evd or (first5 and k < 5):
                continue
            a_ = rc.get(c5s[bars[k - 1]], np.nan); b_ = rc.get(c5s[bars[k]], np.nan)
            if not (np.isfinite(a_) and np.isfinite(b_) and a_ > 0 and b_ > 0):
                continue
            lim = 0.07 if c5s[bars[k]] < "2015-06-01" else 0.10
            rw = a_ * (1 + lim); tk = tick(rw); lp = np.floor(rw / tk + 1e-9) * tk
            if abs(b_ - lp) < 1e-6:
                put(si, "lu", int(bars[k]))
    for k in EVD:
        EVD[k].sort()
    TYS = {"rv_h24": ["rv_h24"], "turn": ["eq_turn1", "eq_turn4"], "A_str": ["eq_turn1", "eq_turn4", "rv_y50", "rv_h24"], "kw_pp": ["kw_pp"], "C_any": ["C"],
           "att": ["att"], "disp": ["disp"], "lu": ["lu"]}

    def first(si, tys, a_, b_):
        best = None
        for ty in tys:
            L_ = EVD.get((si, ty))
            if not L_ or a_ > b_:
                continue
            i = bisect.bisect_left(L_, a_)
            if i < len(L_) and L_[i] <= b_:
                best = L_[i] if best is None else min(best, L_[i])
        return best
    ind = pd.read_csv(os.path.join(mainp, "meta", "industry.csv"), dtype=str)
    IND = {a_.strip(): (b_.strip() if isinstance(b_, str) else "") for a_, b_ in zip(ind["stock_id"], ind["industry_name"])}
    errs = []

    def cmp(key, n_, v_):
        r = REF.get(key)
        if r is None:
            errs.append(f"缺 {key}"); return 1
        if r[0] != n_ or not np.isclose(v_, r[1], rtol=1e-9, atol=1e-12, equal_nan=True):
            errs.append(f"{key}：查核 {n_}／{v_}，本體 {r[0]}／{r[1]}"); return 1
        return 0
    qmap = {"q10": 0.1, "q25": 0.25, "med": 0.5, "q75": 0.75, "q90": 0.9}
    out1 = []
    for c in pick:
        ii = np.flatnonzero((Ec == c) & okE); o_ = np.argsort(Ed[ii], kind="stable")
        cd, cs_ = Ed[ii][o_].tolist(), Es[ii][o_].tolist()
        one = {}
        for gname, lst in (("F4", groups[c][0]), ("不帶F4", groups[c][1])):
            R1 = {k: [] for k in ("days", "gain", "psd", "psg", "pso", "lu_n", "lu_streak", "lu_ratio")}
            R3 = {}
            for i in lst:
                si, t, P_ = int(Es[i]), int(Ed[i]), int(EP[i]); cf = closes(si)
                R1["days"].append(P_ - t); R1["gain"].append(cf[P_] / cf[t] - 1); R1["psd"].append(int(Epd[i])); R1["psg"].append(float(Epg[i])); R1["pso"].append(float(Epo[i]))
                lus = set(EVD.get((si, "lu"), [])); nb = 0; nl = 0; run = 0; best = 0
                for p in range(t, P_ + 1):
                    if not bar5[si, p]:
                        continue
                    nb += 1
                    if p in lus:
                        nl += 1; run += 1; best = max(best, run)
                    else:
                        run = 0
                R1["lu_n"].append(nl); R1["lu_streak"].append(best); R1["lu_ratio"].append(nl / nb)
                for k, _, _ in SIG:
                    if k == "grp":
                        e = None; ig = IND.get(U[si], "")
                        if ig:
                            for j in range(bisect.bisect_left(cd, t - 20), bisect.bisect_right(cd, P_)):
                                if cs_[j] != si and IND.get(U[cs_[j]], "") == ig:
                                    e = max(cd[j], t); break
                        pre = False
                    else:
                        e = first(si, TYS[k], t, P_); pre = first(si, TYS[k], t - 60, t - 1) is not None
                    rr = R3.setdefault(k, {"has": [], "pre": [], "gain": [], "done": [], "up": [], "lag": []})
                    rr["has"].append(e is not None); rr["pre"].append(pre)
                    if e is not None:
                        rr["gain"].append(cf[e] / cf[t] - 1); rr["done"].append((cf[e] - cf[t]) / (cf[P_] - cf[t])); rr["up"].append(cf[P_] / cf[e] - 1); rr["lag"].append(e - t)
            nb_ = 0; n = len(lst)
            for k in ("days", "gain", "psd", "psg"):
                for st_, q in qmap.items():
                    nb_ += cmp(("1 到頂點", gname, k, st_, c), n, float(np.quantile(np.array(R1[k], float), q)))
            nb_ += cmp(("1 到頂點", gname, "pso", "mean", c), n, float(np.mean(R1["pso"])))
            ln = np.array(R1["lu_n"]); sk = np.array(R1["lu_streak"])
            for k, v in (("lu_0", ln == 0), ("lu_1_2", (ln >= 1) & (ln <= 2)), ("lu_3_5", (ln >= 3) & (ln <= 5)), ("lu_6_10", (ln >= 6) & (ln <= 10)), ("lu_gt10", ln > 10),
                         ("lu_ge1", ln >= 1), ("lu_ge3", ln >= 3), ("lu_ge5", ln >= 5), ("stk_ge2", sk >= 2), ("stk_ge3", sk >= 3), ("stk_ge5", sk >= 5)):
                nb_ += cmp(("2 漲停", gname, k, "mean", c), n, float(v.mean()))
            for k in ("lu_n", "lu_streak", "lu_ratio"):
                a_ = np.array(R1[k], float)
                for st_ in ("med", "q75", "q90"):
                    nb_ += cmp(("2 漲停", gname, k, st_, c), n, float(np.quantile(a_, qmap[st_])))
                nb_ += cmp(("2 漲停", gname, k, "mean", c), n, float(a_.mean()))
            for k, rr in R3.items():
                nb_ += cmp(("3 訊號", gname, f"{k}|has", "mean", c), n, float(np.mean(rr["has"])))
                nb_ += cmp(("3 訊號", gname, f"{k}|pre", "mean", c), n, float(np.mean(rr["pre"])))
                nh = len(rr["gain"])
                if nh:
                    for st_ in ("q25", "med", "q75"):
                        nb_ += cmp(("3 訊號", gname, f"{k}|gain", st_, c), nh, float(np.quantile(rr["gain"], qmap[st_])))
                    for kk in ("done", "up", "lag"):
                        nb_ += cmp(("3 訊號", gname, f"{k}|{kk}", "med", c), nh, float(np.quantile(np.array(rr[kk], float), 0.5)))
            one[gname] = {"件數": n, "不同": nb_}
        out1.append({"格": cname(c), **one})
    res["① 1～3 部分 2 格"] = out1
    # ── ② 觸發逐筆（200 檔）
    _t = np.load(os.path.join(WORK, "trig.npz")); TRz = {k: _t[k] for k in _t.files}
    ts, td, txi, tf4, tel = (TRz[k] for k in ("s", "d", "xi", "f4", "el"))
    a0 = c5s.index(next(x for x in c5s if x >= "2017-03-01")); b0 = max(i for i, x in enumerate(c5s) if x <= "2026-08-31")
    rng2 = np.random.default_rng(20261010)
    samp = sorted(int(x) for x in rng2.choice(len(U), 200, replace=False))
    nb2 = 0; ntr = 0; nrow = 0
    tidx = {}
    for i, (a_, b_, x_) in enumerate(zip(ts.tolist(), td.tolist(), txi.tolist())):
        tidx.setdefault(a_, {})[(b_, x_)] = i
    for si in samp:
        cf = closes(si)
        bars = np.flatnonzero(bar5[si])
        mine = {}
        if cf is not None and len(bars):
            badset = set()
            for p in bars:
                capv = min(250, N5 - 1 - p)
                if hdef[si, p] < capv:
                    badset.add(int(p + hdef[si, p] + 1))
            cb = np.array([cf[p] for p in bars])
            isbad = np.array([int(p) in badset for p in bars])
            r = np.full(len(bars), np.nan, np.float32)
            for k in range(59, len(bars)):
                if isbad[max(0, k - 60):k + 1].any():
                    continue
                r[k] = np.float32(cb[k] / cb[k - 59:k + 1].min() - 1)
            for xi, x in enumerate(XS):
                last = -10 ** 9
                for k in range(len(bars)):
                    if np.isfinite(r[k]) and r[k] >= x and k - last > 60:
                        last = k
                        p = int(bars[k])
                        if a0 <= p <= b0 and U[si] in jx:
                            mine[(p, xi)] = float(r[k])
        body_ = tidx.get(si, {})
        if set(mine) != set(body_):
            nb2 += 1; errs.append(f"觸發不同 {U[si]}：查核 {len(mine)} 本體 {len(body_)}；差 {sorted(set(mine) ^ set(body_))[:5]}")
            continue
        ntr += len(mine)
        for (p, xi), rv_ in mine.items():
            i = body_[(p, xi)]; nrow += 1
            kn, f4, el = f4_at(U[si], p)
            if (f4, el) != (bool(tf4[i]), bool(tel[i])) or not np.isclose(rv_, TRz["r"][i], rtol=0, atol=0):
                nb2 += 1; errs.append(f"觸發屬性不同 {U[si]} {c5s[p]} x{xi}")
            c0 = cf[p]
            d250 = hdef[si, p] >= 250 and p + 250 <= icut
            if d250:
                dd1 = bool((cf[p + 1:p + 251] <= c0 * 0.85 * (1 + 1e-9)).any())
                if dd1 != bool(TRz["DN"][i] <= 250):
                    nb2 += 1; errs.append(f"一年跌15% 不同 {U[si]} {c5s[p]}")
            for c in pick:
                H, g = hs[c // 10], gs[c % 10]
                if not (hdef[si, p] >= H and p + H <= icut):
                    continue
                w = cf[p + 1:p + H + 1]
                lab = bool(w.max() >= c0 * (1 + g) * (1 - 1e-9)); mh = w.max() / c0 - 1
                upk = next((j + 1 for j, v in enumerate(w) if v >= c0 * (1 + g) * (1 - 1e-9)), 999)
                dnk = next((j + 1 for j, v in enumerate(w) if v <= c0 * 0.85 * (1 + 1e-9)), 999)
                dnf = dnk <= H and dnk < upk
                bl = bool(TRz["UPG"][i, c % 10] <= H); bmh = float(TRz["MHH"][i, c // 10])
                bdn = bool((TRz["DN"][i] <= H) and (TRz["DN"][i] < TRz["UPG"][i, c % 10]))
                if lab != bl or not np.isclose(mh, bmh, rtol=1e-12) or dnf != bdn:
                    nb2 += 1; errs.append(f"觸發標籤不同 {U[si]} {c5s[p]} x{xi} {cname(c)}")
    res["② 觸發逐筆 200 檔"] = {"檔": len(samp), "觸發": ntr, "逐筆列": nrow, "不同": nb2}
    # ── ③ 第四部分格統計（pandas 另一套）＋基準列（每檔 sliding window）
    df = pd.DataFrame({"f4": tf4, "el": tel, "xi": txi, "d": td, "hd": TRz["hdef"], "r": TRz["r"]})
    mon = np.array([c5s[p][:7] for p in td]); df = df[(mon >= "2017-03") & (mon <= "2026-08")]
    nb3 = 0
    ndays = sum(1 for x in c5s if "2017-03" <= x[:7] <= "2026-08")
    FR = pd.read_csv(os.path.join(OUT, "free.csv")).set_index(["分組", "段", "版本", "x"])
    for gname, gm in (("F4", df["f4"]), ("不帶F4", ~df["f4"])):
        for xi, xk in enumerate(XK):
            sub = df[gm & (df["xi"] == xi)]
            ok250 = (sub["hd"] >= 250) & (sub["d"] + 250 <= icut)
            dd1 = (TRz["DN"][sub.index[ok250]] <= 250)
            fr = FR.loc[(gname, "合併", "全部", xk)]
            if int(fr["觸發數"]) != len(sub) or not np.isclose(fr["每天平均"], len(sub) / ndays, rtol=1e-9) or \
                    int(fr["一年跌15%定義域"]) != len(dd1) or (len(dd1) and not np.isclose(fr["一年內曾跌15%"], dd1.mean(), rtol=1e-9)):
                nb3 += 1; errs.append(f"free 不同 {gname} {xk}：查核 {len(sub)}、{len(sub) / ndays}、{len(dd1)}、{dd1.mean() if len(dd1) else None}；本體 {fr.to_dict()}")
            for c in pick:
                H, hi, gi = hs[c // 10], c // 10, c % 10
                q = sub[(sub["hd"] >= H) & (sub["d"] + H <= icut)]
                if not len(q):
                    continue
                ix_ = q.index.to_numpy()
                lab = pd.Series(TRz["UPG"][ix_, gi] <= H); mh = pd.Series(TRz["MHH"][ix_, hi])
                dnf = pd.Series((TRz["DN"][ix_] <= H) & (TRz["DN"][ix_] < TRz["UPG"][ix_, gi]))
                nb3 += cmp(("4 漲幾%", gname, f"{xk}|rate", "mean", c), len(q), float(lab.mean()))
                nb3 += cmp(("4 漲幾%", gname, f"{xk}|mh", "med", c), len(q), float(mh.median()))
                nb3 += cmp(("4 漲幾%", gname, f"{xk}|dnfirst", "mean", c), len(q), float(dnf.mean()))
                if lab.any():
                    ms = mh[lab.to_numpy()]; rr_ = pd.Series(q["r"].to_numpy()[lab.to_numpy()].astype(float), index=ms.index)
                    low = 1 / (1 + rr_)
                    capv = ms / (1 + ms - low)
                    nb3 += cmp(("4 漲幾%", gname, f"{xk}|mh_s", "med", c), int(lab.sum()), float(ms.median()))
                    nb3 += cmp(("4 漲幾%", gname, f"{xk}|cap", "med", c), int(lab.sum()), float(capv.median()))
    # 基準列
    from numpy.lib.stride_tricks import sliding_window_view as swv
    base = {(gname, c): [0, 0] for gname in ("F4", "不帶F4") for c in pick}
    mpos = np.searchsorted(me, cal5.values, side="left") - 1
    for si in range(len(U)):
        x = U[si]
        if x not in jx:
            continue
        cf = closes(si)
        if cf is None:
            continue
        f4row = z["F4"][:, jx[x]]
        for c in pick:
            H, g = hs[c // 10], gs[c % 10]
            fmx = np.full(N5, np.nan)
            if N5 - 1 - H >= 0:
                fmx[:N5 - H] = np.nanmax(swv(cf[1:], H), axis=1)[:N5 - H] if np.isfinite(cf).any() else np.nan
            for p in np.flatnonzero(bar5[si, a0:b0 + 1]) + a0:
                if not (hdef[si, p] >= H and p + H <= icut) or mpos[p] < 0:
                    continue
                gname = "F4" if f4row[mpos[p]] else "不帶F4"
                b = base[(gname, c)]; b[0] += 1
                b[1] += int(fmx[p] >= cf[p] * (1 + g) * (1 - 1e-9))
        if si % 400 == 0:
            print(f"[基準] {si}/{len(U)}", flush=True)
    for (gname, c), (n_, k_) in base.items():
        nb3 += cmp(("4 漲幾%", gname, "base|rate", "mean", c), n_, k_ / n_ if n_ else np.nan)
    res["③ 第四部分 2 格＋free＋基準"] = {"不同": nb3}
    res["錯誤（前 30）"] = errs[:30]; res["合計不同"] = len(errs); res["過"] = len(errs) == 0; res["秒"] = round(time.time() - T0)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    if a.check:
        return check()
    if a.stage == "body":
        body(a)
    else:
        page()


if __name__ == "__main__":
    main()

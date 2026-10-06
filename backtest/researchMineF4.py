# -*- coding: utf-8 -*-
"""連續虧損（F4）股的飆股特徵——PREREG地雷股濾網 seq3 丙的往下拆（描述；使用者直接問；參考、⛔ 不計 N、不需登錄）。回測線（子代理執行）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 MINE_REUSE=1 ~/tw-p16/.venv/bin/python -m backtest.researchMineF4           # 本體＋網頁
    ...                                                                                -m backtest.researchMineF4 page      # 只重做網頁
    抽樣查核：... -m backtest.researchMineF4 --check（⛔ 不呼叫本檔本體與 researchMine 的函式；從原始 CSV／s5 原表自算）

⭐ 讀法寫死時間：2026-10-07 06:40（台北）；寫死前 ⛔ 沒看任何本件數字（只知道派工單轉述的丙結果：G1 48%、F4 38%）。
   使用者原話：「順著F4繼續往下」——連續虧損的股票裡，後來變飆股的那些，起漲前有什麼共同情況、跟沒變飆股的 F4 股差在哪。
   使用者固定規矩：問「特徵」＝ 描述性統計，先答涵蓋率（依比例高到低全部列），倍數放後面補充；⛔ 不轉成「能不能預測」；⛔ 不自己挑前 N 個；
   飆股 ＝ seq6 網格（H×g 250 格），每個數字取全網格各格的中位（附 p10～p90）；⛔ 不寫「N 天漲一倍」。

═══ 讀法（Z 標）═══
 Z1 資料：沿用 researchMine 的 ~/minework/flags_main.npz（逐月底判定日 F1～F5、G、EL ＝ W1 母體）、主快照 796d94c9da 的 fin_hist／filing_dates
    （EPS；researchMine.load_fin 同一支）、s5 名單 ~/s5work（events、hdef、bar、Q）；月營收 ＝ 同一 commit 796d94c9da 的 mops/revenue_hist
    （~/h2data/indrev_796d94c9dafd；期別用每列 period 欄）；產業別 ＝ 主快照 meta/industry.csv 的 industry_name（現值套回 ⇒ 標「後見」）
 Z2 事件（同 researchMine 丙）：s5 events 全部 250 格、t＋H ≤ 2026-08-31（U4b）、s5 全日曆鏈；m ＝ 嚴格 ＜ t 的最後一個月底判定日；
    「F4 飆股」＝ m 時 F4（F4a ∨ F4b）；段依 t 的月份：探索 2017-03～2021-12、確認 2022-01～2026-08、合併 2017-03～2026-08
    版本：全部上市櫃（主；s5 名單不套 W1）、W1 母體內（EL[m]）
    ⭐ 閘門：事件 cell、d、s 與 bing_events.npz 逐筆相同；「事件中帶 F4 的比例」網格中位要重現 bing_grid.csv（探索＋確認，全部／W1 兩版）
 Z3 對照「沒變飆股的 F4 股-月」（每格各算）：s5 名單內股-月 (股, m)、m 時 F4、m 當天有 K 棒、定義域 hdef[m＋1] ≥ H 且 m＋1＋H ≤ 2026-08-31
    （＝ researchMine「帶旗股票之後變飆股的機率」同一定義域），去掉 (m, m_next] 內有該格起漲日者；段依 m＋1（次月）的月份；W1 版另加 EL[m]
 Z4 時點：1～5、7 類一律看 m（起漲前一個判定日 ＝ F4 旗本身那一天；所有資料 point-in-time 到 m 收盤）；
    6 類（14 個起漲特徵）看起漲日 t（使用者說的「起漲點訊號」＝ researchSurge6_overlap.FEATS，s5 Q 碼相等 ＝ 有）；
    對照股-月的 6 類 ＝ (m, m_next] 內有 K 棒各日的平均（＝ 這段期間任一天拿來當起漲日時的平均）；該段沒有任何 K 棒 ⇒ 該列 6 類不進分母
 Z5 EPS（2 類）：單季 EPS、可用日（A2 式）、「最近一季」＝ m 時已可用期別的最新者（researchMine X5 同式；researchMine.load_fin）；
    e0 ＝ 最近一季、e1 ＝ 前一季、e4 ＝ 去年同季；比前一季好 ＝ e0 ＞ e1；比去年同季好 ＝ e0 ＞ e4；已轉正 ＝ e0 ＞ 0；已轉正但 4 季合計仍虧 ＝ e0 ＞ 0 且 Σe0..3 ＜ 0；
    近 4 季比再前 4 季好 ＝ Σe0..3 ＞ Σe4..7；連續虧損季數 ＝ 從 e0 往回連續 ＜ 0 的季數（最多看 12 季；缺值中斷）分 0、1、2、3、4～7、≥8
    任一比較用到的季缺值 ⇒ 該項算「沒有」（缺值率另報在 rows 統計）
    ⭐ 閘門：用這裡的 e 重算 F4a、F4b，須與 flags_main.npz 全部格逐一相同
 Z6 月營收（3 類）：可用日 ＝ 期別 ≤ 2025-12：次月 10 日之後第一個交易日；2026-01 期起：次月 15 日之後第一個交易日；可用 ⇔ 可用日 ≤ m；
    取 m 時可用的最新一個「有值」期別 j；年增 ＝ V[j]÷V[j−12]−1（V[j−12] ＞ 0 才算）；＞ 0、＞ 20%；
    創 12／24 月新高 ＝ V[j] ≥ 前 12／24 個月（不含當月）最大值，前面那段至少 9／18 個月有值（項目 rev_hi24_flags 的「不含當期、≥18 期有效」讀法；⛔ 不加容差）；
    連續年增月數（到 j 為止往回連續年增 ＞ 0，缺值中斷）分 0、1～2、3～5、6～11、≥12；算不出年增 ⇒「月營收無資料或算不出年增」
 Z7 價位與規模（4 類）：股價 ＜ 面額 ＝ F2(p＝1)、＜ 半個面額 ＝ F2(p＝0.5)（researchMine 旗）；
    距 250 日低點、市值、20 日平均成交金額 ＝ s5 Q（dlo_250、mcap、amt_20）在 m 的全市場五等分（當天有 K 棒的 s5 名單、同值同組；1 ＝ 最小
    〔最貼近低點／市值最小／成交最少〕）；Q＝0 ⇒ 無資料。⭐「日均成交量」用成交金額（張數跨股不可比），照標
 Z8 其他旗（5 類）：F1(50%)、F1(70%)、F3(淨值 ＜ 面額/2)、F3(淨值 ＜ 0)、F5a、F5b、F5、「F4 之外至少再帶一旗」（＝ G2）
 Z9 起漲特徵（6 類）：14 個各自、同時有幾個（0～4、5 以上；沒有值算沒有，同 overlap V4）
 Z10 產業（7 類）：industry_name 現值（後見）；查不到 ⇒「（查無產業別）」；全部列
 Z11 彙總：每格 c × 段 × 版本：涵蓋率 ＝ F4 飆股中有此情況的比例（分母 ＝ 全部 F4 飆股；缺值算沒有）；對照比例 ＝ Z3 股-月中有此情況的比例；
     倍數 ＝ 涵蓋率 ÷ 對照比例（對照 0 ⇒ 不算）；網格彙總 ＝ 有 ≥ 1 個 F4 飆股的格的中位（p10～p90），對照比例與倍數取同一批格的中位；另報 ≥ 30 事件的格
     「一般 F4 股也差不多」＝ 倍數中位在 0.8～1.25（只加註，⛔ 不篩選；全部項目照列）
 Z12 只描述：⛔ 不判定、⛔ 不計 N、⛔ 不轉成「能不能事先預測」、⛔ 不寫「N 天漲一倍」、⛔ 不給買賣建議
 Z13 --check（獨立寫法）：抽 2 格（合併段、全部版、事件 ≥ 30）從 events.npz／日曆自找 F4 飆股、從 fin_hist／filing_dates／revenue_hist CSV 與 s5 Q 自算每列情況
     ⇒ 重算涵蓋率比 cells.csv.gz；另抽 300 個 F4 股-月逐項比 rows；對照比例用 rows 以另一套寫法（pandas）重算比 cells.csv.gz；
     容差：布林逐一相同、比例相對 1e-9；researchMine 的 flags（F1、F2、F3、F5、EL）是輸入，直接讀 npz
輸出 backtest/resultsMine/F4/（cells.csv.gz、grid.csv、summary.json、check.json、run.log、連續虧損股的飆股特徵.html）；逐列 ~/minework/F4/
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import researchMine as RM

TAGT = "2026-10-07 06:40（台北）"
MAIN = RM.MAIN
S5W = RM.S5W
WORK = os.path.join(RM.WORK, "F4")
OUT = os.path.join(RM.OUT, "F4")
REVD = os.path.expanduser("~/h2data/indrev_796d94c9dafd/data/mops/revenue_hist")
CUT = RM.CUT
SEGS = {"探索": ("2017-03", "2021-12"), "確認": ("2022-01", "2026-08"), "合併": ("2017-03", "2026-08")}
SEGNAME = {"探索": "2017-03～2021", "確認": "2022～2026-08", "合併": "2017-03～2026-08"}
VERS = ("全部", "W1 母體內")
HS5, GS5, NC5 = RM.HS5, RM.GS5, RM.NC5
# 14 個起漲特徵（＝ researchSurge6_overlap.FEATS；名稱、欄、碼照抄，閘門比對）
FEATS = [("距5日最低｜Q1", "dlo_5", 1), ("距10日最低｜Q1", "dlo_10", 1), ("收盤÷MA5−1｜Q1", "ma_5", 1), ("5日報酬｜Q1", "r_5", 1),
         ("60日平均周轉率｜Q5", "turn_60", 5), ("120日報酬｜Q5", "r_120", 5), ("融資使用率｜Q5", "musage", 5),
         ("原：股價級距｜＜20 元", "d_px", 1), ("原：均線多頭排列5>20>60>100｜是", "d_bull", 2), ("原：注意股60日次數級距｜≥3 次", "d_att60", 3),
         ("原R2營收年增≥50%｜是", "d_R2a", 2), ("原：EPS轉正｜是", "d_eps", 2), ("原：營收創24月新高｜是", "d_revhi", 2), ("原：20日漲停天數級距｜≥3 次", "d_lu20", 4)]
FEAT_PLAIN = ["離 5 日最低點最近的 20%", "離 10 日最低點最近的 20%", "收盤低於 5 日均線最多的 20%", "5 日報酬最差的 20%", "60 日平均周轉率最高的 20%",
              "120 日報酬最好的 20%", "融資使用率最高的 20%", "股價 ＜ 20 元", "均線多頭排列（5＞20＞60＞100 日）", "60 日內被列注意股 ≥ 3 次",
              "月營收年增 ≥ 50%（起漲日當時）", "EPS 轉正（起漲日當時最近一季由虧轉盈）", "月營收創 24 個月新高（起漲日當時、項目原讀法）", "20 日內漲停 ≥ 3 次"]
QX = [("dlo_250", "dlo", "離 250 日最低點", ("最近的 20%", "次近的 20%", "中間 20%", "次遠的 20%", "最遠的 20%")),
      ("mcap", "mcap", "市值", ("最小的 20%", "次小的 20%", "中間 20%", "次大的 20%", "最大的 20%")),
      ("amt_20", "amt", "20 日平均成交金額", ("最少的 20%", "次少的 20%", "中間 20%", "次多的 20%", "最多的 20%"))]
CAT = {1: "1 F4 的種類", 2: "2 虧損在改善嗎（最近一季財報）", 3: "3 月營收", 4: "4 價位與規模", 5: "5 同時帶的其他旗", 6: "6 起漲特徵（起漲日當天）", 7: "7 產業（現值，後見）"}


def keys_spec(inds):
    K = [("f4a_only", 1, "只有「近 4 季合計虧、最近一季也虧」那一種"), ("f4b_only", 1, "只有「近 8 季有 6 季以上虧」那一種"), ("f4ab", 1, "兩種都有"),
         ("F4a", 1, "近 4 季合計虧、最近一季也虧（含兩種都有）"), ("F4b", 1, "近 8 季有 6 季以上虧（含兩種都有）"),
         ("e_qoq", 2, "最近一季 EPS 比前一季好"), ("e_yoy", 2, "最近一季 EPS 比去年同季好"), ("e_pos", 2, "最近一季已經轉成賺錢"),
         ("e_pos4", 2, "最近一季已賺錢、但近 4 季合計仍虧"), ("e_4v4", 2, "近 4 季合計比再前 4 季好（虧損縮小）"),
         ("lq0", 2, "連續虧損 0 季（最近一季沒虧）"), ("lq1", 2, "連續虧損 1 季"), ("lq2", 2, "連續虧損 2 季"), ("lq3", 2, "連續虧損 3 季"),
         ("lq4", 2, "連續虧損 4～7 季"), ("lq8", 2, "連續虧損 8 季以上"),
         ("rv_y0", 3, "月營收年增 ＞ 0"), ("rv_y20", 3, "月營收年增 ＞ 20%"), ("rv_h12", 3, "月營收創 12 個月新高"), ("rv_h24", 3, "月營收創 24 個月新高"),
         ("rs0", 3, "連續年增 0 個月（最新一個月沒有年增）"), ("rs1", 3, "連續年增 1～2 個月"), ("rs3", 3, "連續年增 3～5 個月"), ("rs6", 3, "連續年增 6～11 個月"),
         ("rs12", 3, "連續年增 12 個月以上"), ("rv_na", 3, "月營收無資料或算不出年增"),
         ("F2_1", 4, "股價低於面額"), ("F2_05", 4, "股價低於半個面額")]
    for _, k, nm, labs in QX:
        K += [(f"{k}{q}", 4, f"{nm}：全市場{labs[q - 1]}") for q in range(1, 6)] + [(f"{k}0", 4, f"{nm}：無資料（月底沒有交易，例如停牌中{'；或上市未滿 250 天' if k == 'dlo' else ''}）")]
    K += [("F1_50", 5, "F1 長期下探（一年跌 50% 以上且在年線下）"), ("F1_70", 5, "F1 長期下探（一年跌 70% 以上）"), ("F3_half", 5, "F3 淨值低於面額一半"),
          ("F3_neg", 5, "F3 淨值為負"), ("F5a", 5, "F5 全額交割／變更交易／管理股票"), ("F5b", 5, "F5 懲罰型停資停券"), ("F5", 5, "F5 官方警示（任一）"),
          ("G2", 5, "F4 之外至少再帶一個旗（F1／F2／F3／F5）")]
    K += [(f"ft{i}", 6, FEAT_PLAIN[i]) for i in range(len(FEATS))]
    K += [(f"fc{c}", 6, f"14 個起漲特徵同時有 {c} 個" if c < 5 else "14 個起漲特徵同時有 5 個以上") for c in range(6)]
    K += [(f"ind_{x}", 7, x) for x in inds]
    return K


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 基底：旗、日曆、s5 ═════════════
def load_base(log):
    z = np.load(os.path.join(RM.WORK, "flags_main.npz"))
    FL = {k: z[k] for k in z.files if k not in ("me", "sids")}
    sids = [str(x) for x in z["sids"]]
    D.DATA = MAIN; cal = D.load_calendar()
    mepos = cal.get_indexer(pd.DatetimeIndex(z["me"]))
    assert (mepos >= 0).all() and np.array_equal(mepos, RM.month_ends(cal, False)), "⛔ 判定日對不上"
    cal5 = RM.s5_calendar()
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)
    hdef = np.load(os.path.join(S5W, "hdef.npy"), mmap_mode="r"); bar5 = np.load(os.path.join(S5W, "bar.npy"), mmap_mode="r")
    assert len(cal5) == hdef.shape[1] == 5571 and len(uni) == hdef.shape[0]
    icut = int(cal5.get_loc(pd.Timestamp(CUT)))
    E = np.load(os.path.join(S5W, "events.npz"))
    cell = E["cell"].astype(int); d = E["d"].astype(int); s = E["s"].astype(int)
    Hc = np.array(HS5)[cell // len(GS5)]
    ok = d + Hc <= icut
    cell, d, s = cell[ok], d[ok], s[ok]
    B = np.load(os.path.join(RM.WORK, "bing_events.npz"))
    assert np.array_equal(B["cell"], cell) and np.array_equal(B["d"], d) and np.array_equal(B["s"], s), "⛔ 事件與 bing_events.npz 不同"
    me5 = cal5.get_indexer(cal[mepos])                                   # 2026-09-24 以後 ⇒ −1
    log(f"[基底] 判定日 {len(mepos)}（{cal[mepos[0]].date()}～{cal[mepos[-1]].date()}）｜主世界 {len(sids)} 檔｜s5 名單 {len(uni)} 檔｜事件（U4b 後）{len(d):,}（＝ bing_events.npz）")
    return {"FL": FL, "sids": sids, "cal": cal, "mepos": mepos, "cal5": cal5, "uni": uni, "hdef": hdef, "bar5": bar5, "icut": icut,
            "cell": cell, "d": d, "s": s, "me5": me5, "bing": B}


# ═════════════ EPS ═════════════
def eps_matrix(F_s, mepos, nq=12):
    nm = len(mepos); E = np.full((nm, nq), np.nan)
    if F_s is None or not len(F_s):
        return E
    o = (F_s["y"] * 4 + F_s["q"] - 1).to_numpy(); ap = F_s["ap"].to_numpy(); ep = F_s["eps"].to_numpy(float)
    srt = np.argsort(ap, kind="stable"); ap_s = ap[srt]; runmax = np.maximum.accumulate(o[srt])
    k = np.searchsorted(ap_s, mepos, side="right") - 1
    val = {oo: v for oo, v in zip(o, ep)}
    for i in np.flatnonzero(k >= 0):
        top = int(runmax[k[i]])
        E[i] = [val.get(top - j, np.nan) for j in range(nq)]
    return E


def eps_feats(E):
    e = E; f8 = np.isfinite(e[:, :8]).all(1); f4 = np.isfinite(e[:, :4]).all(1)
    with np.errstate(invalid="ignore"):
        s4 = e[:, :4].sum(1); s8b = e[:, 4:8].sum(1)
        out = {"F4a_re": f4 & (s4 < 0) & (e[:, 0] < 0), "F4b_re": f8 & ((e[:, :8] < 0).sum(1) >= 6),
               "e_qoq": e[:, 0] > e[:, 1], "e_yoy": e[:, 0] > e[:, 4], "e_pos": e[:, 0] > 0, "e_pos4": f4 & (e[:, 0] > 0) & (s4 < 0),
               "e_4v4": f8 & (s4 > s8b)}
    run = np.zeros(len(e), int); alive = np.ones(len(e), bool)
    for j in range(e.shape[1]):
        with np.errstate(invalid="ignore"):
            alive &= e[:, j] < 0
        run += alive
    out["lqn"] = run
    return out


# ═════════════ 月營收 ═════════════
def load_rev(cal, log):
    fs = sorted(glob.glob(os.path.join(REVD, "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs], ignore_index=True)
    df["stock_id"] = df["stock_id"].str.strip(); df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    per = pd.period_range(df["period"].min(), df["period"].max(), freq="M").astype(str)
    V = df.pivot(index="period", columns="stock_id", values="rev").reindex(per)
    eff = []
    for p in per:
        y, mo = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if mo == 12 else (y, mo + 1)
        eff.append(int(cal.searchsorted(pd.Timestamp(y2, m2, 10 if p <= "2025-12" else 15), side="right")))
    log(f"[月營收] {len(fs)} 檔案、{len(df):,} 列、期別 {per[0]}～{per[-1]}（revenue_hist @796d94c9da）")
    return V, np.array(eff)


def rev_series(v):
    n = len(v)
    with np.errstate(invalid="ignore", divide="ignore"):
        prev = np.r_[np.full(12, np.nan), v[:-12]]
        yoy = np.where(prev > 0, v / prev - 1, np.nan)
    hi = {}
    for L, mn in ((12, 9), (24, 18)):
        sh = pd.Series(v).shift(1)
        mx = sh.rolling(L, min_periods=mn).max().to_numpy()
        hi[L] = np.isfinite(v) & np.isfinite(mx) & (v >= mx)
    stk = np.zeros(n, int); r = 0
    for j in range(n):
        r = r + 1 if (np.isfinite(yoy[j]) and yoy[j] > 0) else 0; stk[j] = r
    lastf = np.full(n, -1); cur = -1
    for j in range(n):
        if np.isfinite(v[j]):
            cur = j
        lastf[j] = cur
    return yoy, hi[12], hi[24], stk, lastf


# ═════════════ 本體 ═════════════
def body(a):
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchMineF4 {now_tpe()}（台北）｜讀法寫死 {TAGT} =====")
    G = load_base(log)
    FL, sids, cal, mepos, cal5, uni = G["FL"], G["sids"], G["cal"], G["mepos"], G["cal5"], G["uni"]
    nm, S = FL["F4"].shape
    s5ix = {x: i for i, x in enumerate(uni["stock_id"])}
    col5 = np.array([s5ix.get(x, -1) for x in sids])
    mon_m1 = np.array([str(cal[p + 1])[:7] if p + 1 < len(cal) else "9999-99" for p in mepos])      # m＋1 的月份
    # ── EPS（全部格；閘門：重算 F4a／F4b）
    _, F = RM.load_fin(cal, log)
    FS = {x: g for x, g in F.groupby("stock_id")}
    EPS = np.full((nm, S, 12), np.nan); bad = 0
    for j, x in enumerate(sids):
        EPS[:, j] = eps_matrix(FS.get(x), mepos)
    EF = eps_feats(EPS.reshape(nm * S, 12))
    EF = {k: v.reshape(nm, S) for k, v in EF.items()}
    bad = int((EF["F4a_re"] != FL["F4a"]).sum() + (EF["F4b_re"] != FL["F4b"]).sum())
    log(f"[EPS 閘門] 重算 F4a／F4b vs flags_main.npz：不同 {bad}（共 {nm * S:,} 格 ×2）")
    if bad:
        raise SystemExit("⛔ F4 重算不同")
    # ── 列：F4 股-月，m＋1 月份在合併段內、s5 名單有此股
    a0, b0 = SEGS["合併"]
    mi = np.flatnonzero((mon_m1 >= a0) & (mon_m1 <= b0))
    R_i, R_j = np.nonzero(FL["F4"][mi][:, :] & (col5 >= 0)[None, :])
    R_i = mi[R_i]
    nr = len(R_i)
    RI = np.full((nm, S), -1); RI[R_i, R_j] = np.arange(nr)
    rs5 = col5[R_j]; rm5 = G["me5"][R_i]; rm5n = G["me5"][np.minimum(R_i + 1, nm - 1)]
    assert (rm5 >= 0).all() and (rm5n > rm5).all()
    log(f"[列] F4 股-月 {nr:,}（m＋1 在 {a0}～{b0}、s5 名單內）｜檔數 {len(set(R_j.tolist()))}")
    # ── 情況
    ind = pd.read_csv(os.path.join(MAIN, "meta", "industry.csv"), dtype=str)
    imap = dict(zip(ind["stock_id"].str.strip(), ind["industry_name"].fillna("").str.strip()))
    rind = np.array([imap.get(sids[j], "") or "（查無產業別）" for j in R_j])
    inds = sorted(set(rind.tolist()))
    KS = keys_spec(inds); KI = {k: i for i, (k, _, _) in enumerate(KS)}; K = len(KS)
    X = np.zeros((nr, K), np.float64); VD = np.ones((nr, K), np.float64)

    def put(k, v):
        X[:, KI[k]] = np.asarray(v, np.float64)
    f4a, f4b = FL["F4a"][R_i, R_j], FL["F4b"][R_i, R_j]
    put("f4a_only", f4a & ~f4b); put("f4b_only", f4b & ~f4a); put("f4ab", f4a & f4b); put("F4a", f4a); put("F4b", f4b)
    for k in ("e_qoq", "e_yoy", "e_pos", "e_pos4", "e_4v4"):
        put(k, EF[k][R_i, R_j])
    lq = EF["lqn"][R_i, R_j]
    put("lq0", lq == 0); put("lq1", lq == 1); put("lq2", lq == 2); put("lq3", lq == 3); put("lq4", (lq >= 4) & (lq <= 7)); put("lq8", lq >= 8)
    # 月營收
    V, eff = load_rev(cal, log)
    rp = np.searchsorted(eff, mepos[R_i], side="right") - 1               # eff 單調（期別遞增）
    assert np.all(np.diff(eff) >= 0)
    yoy_r = np.full(nr, np.nan); h12 = np.zeros(nr, bool); h24 = np.zeros(nr, bool); stk_r = np.zeros(nr, int)
    cache = {}
    for r in range(nr):
        x = sids[R_j[r]]
        if x not in V.columns or rp[r] < 0:
            continue
        if x not in cache:
            cache[x] = rev_series(V[x].to_numpy(float))
        yoy, a12, a24, stk, lastf = cache[x]
        jj = lastf[rp[r]]
        if jj < 0:
            continue
        yoy_r[r] = yoy[jj]; h12[r] = a12[jj]; h24[r] = a24[jj]; stk_r[r] = stk[jj]
    fy = np.isfinite(yoy_r)
    with np.errstate(invalid="ignore"):
        put("rv_y0", fy & (yoy_r > 0)); put("rv_y20", fy & (yoy_r > 0.2))
    put("rv_h12", h12); put("rv_h24", h24)
    put("rs0", fy & (stk_r == 0)); put("rs1", fy & (stk_r >= 1) & (stk_r <= 2)); put("rs3", fy & (stk_r >= 3) & (stk_r <= 5))
    put("rs6", fy & (stk_r >= 6) & (stk_r <= 11)); put("rs12", fy & (stk_r >= 12)); put("rv_na", ~fy)
    # 旗
    for k in ("F2_1", "F2_05", "F1_50", "F1_70", "F3_half", "F3_neg", "F5a", "F5b", "F5", "G2"):
        put(k, FL[k][R_i, R_j])
    # Q（s5）
    bjs = json.load(open(os.path.join(S5W, "build.json"), encoding="utf-8"))
    FX = {c: i for i, c in enumerate(bjs["特徵欄"])}
    Qm = np.load(os.path.join(S5W, "Q.npy"), mmap_mode="r")
    for col, k, _, _ in QX:
        q = np.asarray(Qm[FX[col]])[rs5, rm5]
        for v in range(6):
            put(f"{k}{v}", q == v)
    fs_ = pd.read_csv("backtest/resultsSurge6/feat_summary.csv")
    for nm_, col, code in FEATS:
        r_ = fs_[fs_["特徵"] == nm_]
        assert len(r_) == 1 and r_.iloc[0]["欄"] == col and int(r_.iloc[0]["碼"]) == code, nm_
    QF = np.stack([np.asarray(Qm[FX[col]]) for _, col, _ in FEATS])          # (14, S5, n5) int8
    code = np.array([c for _, _, c in FEATS], np.int8)
    # 對照列的起漲特徵：(m, m_next] 內有 K 棒各日平均
    bar5 = np.asarray(G["bar5"])
    lens = rm5n - rm5
    rr = np.repeat(np.arange(nr), lens); dd = np.concatenate([np.arange(a_ + 1, b_ + 1) for a_, b_ in zip(rm5, rm5n)]); ss = rs5[rr]
    hb = bar5[ss, dd]
    rr, dd, ss = rr[hb], dd[hb], ss[hb]
    nb = np.bincount(rr, minlength=nr).astype(float)
    hit = QF[:, ss, dd] == code[:, None]                                     # (14, N)
    cnt = hit.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        for i in range(len(FEATS)):
            put(f"ft{i}", np.where(nb > 0, np.bincount(rr, weights=hit[i], minlength=nr) / np.maximum(nb, 1), 0))
        for c in range(6):
            put(f"fc{c}", np.where(nb > 0, np.bincount(rr, weights=(np.minimum(cnt, 5) == c), minlength=nr) / np.maximum(nb, 1), 0))
    for k in [f"ft{i}" for i in range(len(FEATS))] + [f"fc{c}" for c in range(6)]:
        VD[:, KI[k]] = (nb > 0)
    for x in inds:
        put(f"ind_{x}", rind == x)
    np.savez_compressed(os.path.join(WORK, "rows.npz"), R_i=R_i, R_j=R_j, rs5=rs5, rm5=rm5, rm5n=rm5n, X=X, VD=VD, keys=np.array([k for k, _, _ in KS]),
                        nbar=nb, yoy=yoy_r, lqn=lq)
    log(f"[列] 情況 {K} 項｜(m, m_next] 沒有 K 棒的列 {int((nb == 0).sum())}｜月營收算不出年增 {float((~fy).mean()):.1%}")
    # ── 事件
    cell, d, s = G["cell"], G["d"], G["s"]
    tdates = cal5[d]; mon_t = np.array([str(x)[:7] for x in tdates])
    insg = (mon_t >= a0) & (mon_t <= b0)
    medates = cal[mepos]
    k_ = np.searchsorted(medates.values, tdates.values, side="left") - 1     # 嚴格 ＜ t
    usid = uni["stock_id"].to_numpy()[s]
    ix = {x: j for j, x in enumerate(sids)}
    jcol = np.array([ix.get(x, -1) for x in usid])
    known = insg & (jcol >= 0) & (k_ >= 0)
    # 閘門：事件中帶 F4 的比例（探索＋確認）重現 bing_grid
    BG = pd.read_csv(os.path.join(RM.OUT, "bing_grid.csv"))
    f4ev = np.zeros(len(d), bool); f4ev[known] = FL["F4"][k_[known], jcol[known]]
    elev = np.zeros(len(d), bool); elev[known] = FL["EL"][k_[known], jcol[known]]
    assert np.array_equal(known, G["bing"]["known"] & insg) and np.array_equal(f4ev[known], G["bing"]["F4"][known])
    rep = {}
    for ver, msk in (("全部", known), ("W1 母體內", known & elev)):
        v = [f4ev[msk & (cell == c)].mean() for c in range(NC5) if (msk & (cell == c)).any()]
        ref = float(BG[(BG["段"] == "探索＋確認") & (BG["版本"] == ver) & (BG["旗"] == "F4")]["網格中位"].iloc[0])
        rep[ver] = {"本件重算": float(np.median(v)), "bing_grid.csv": ref}
        if not np.isclose(np.median(v), ref, rtol=1e-12, atol=0):
            raise SystemExit(f"⛔ F4 比例重現不過 {ver}：{rep}")
    log(f"[事件 閘門] 事件中帶 F4 比例（網格中位）重現 bing_grid：{rep}")
    ev = np.flatnonzero(known & f4ev)
    erow = RI[k_[ev], jcol[ev]]
    assert (erow >= 0).all(), "⛔ 有 F4 飆股找不到對應 F4 股-月列"
    XE = X[erow].copy()
    qe = QF[:, s[ev], d[ev]] == code[:, None]
    for i in range(len(FEATS)):
        XE[:, KI[f"ft{i}"]] = qe[i]
    ce = np.minimum(qe.sum(0), 5)
    for c in range(6):
        XE[:, KI[f"fc{c}"]] = ce == c
    e_cell = cell[ev]; e_mon = mon_t[ev]; e_el = elev[ev]; e_sid = usid[ev]; e_d = d[ev]
    np.savez_compressed(os.path.join(WORK, "events.npz"), ev=ev, erow=erow, cell=e_cell, d=e_d, s=s[ev], el=e_el, XE=XE)
    log(f"[事件] F4 飆股（合併段、各格加總）{len(ev):,}｜不同 (股, 起漲日) {len(set(zip(e_sid.tolist(), e_d.tolist()))):,}｜不同股票 {len(set(e_sid.tolist()))}")
    # ── 對照的定義域與「該格有起漲」
    hd1 = np.asarray(G["hdef"])[rs5, np.minimum(rm5 + 1, G["hdef"].shape[1] - 1)]
    barm = bar5[rs5, rm5]
    keyall = s.astype(np.int64) * 10000 + d
    lo = rs5.astype(np.int64) * 10000 + rm5 + 1; hi_ = rs5.astype(np.int64) * 10000 + rm5n
    HAS = np.zeros((NC5, nr), bool)
    for c in range(NC5):
        kc = np.sort(keyall[cell == c])
        if len(kc):
            p = np.searchsorted(kc, lo, side="left")
            HAS[c] = (p < len(kc)) & (kc[np.minimum(p, len(kc) - 1)] <= hi_)
    r_mon = mon_m1[R_i]; r_el = FL["EL"][R_i, R_j]
    rows = []
    for seg, (a_, b_) in SEGS.items():
        rseg = (r_mon >= a_) & (r_mon <= b_)
        eseg = (e_mon >= a_) & (e_mon <= b_)
        for ver in VERS:
            rb = rseg & barm & (r_el if ver != "全部" else True)
            eb = eseg & (e_el if ver != "全部" else True)
            M = np.zeros((NC5, nr), np.float64)
            for c in range(NC5):
                H = int(HS5[c // len(GS5)])
                M[c] = rb & (hd1 >= H) & (rm5 + 1 + H <= G["icut"]) & ~HAS[c]
            sm = M @ (X * VD); cn = M @ VD                                        # (250, K)
            g = pd.DataFrame(XE[eb]).groupby(e_cell[eb]).agg(["sum", "count"])
            esum = np.zeros((NC5, K)); ecnt = np.zeros(NC5)
            if len(g):
                cc = g.index.to_numpy()
                esum[cc] = g.xs("sum", axis=1, level=1).to_numpy(); ecnt[cc] = g.xs("count", axis=1, level=1).to_numpy()[:, 0]
            with np.errstate(invalid="ignore", divide="ignore"):
                es = esum / ecnt[:, None]; cs = sm / cn
            for c in range(NC5):
                for kk in range(K):
                    rows.append((seg, ver, RM.cell_name(c), c, int(HS5[c // len(GS5)]), float(GS5[c % len(GS5)]), KS[kk][0], int(ecnt[c]),
                                 es[c, kk] if ecnt[c] else np.nan, float(cn[c, kk]), cs[c, kk] if cn[c, kk] else np.nan))
        log(f"[彙總] {seg} 完成")
    CL = pd.DataFrame(rows, columns=["段", "版本", "格", "cell", "H", "g", "情況", "F4飆股數", "涵蓋率", "對照股月數", "對照比例"])
    with np.errstate(invalid="ignore", divide="ignore"):
        CL["倍數"] = np.where(CL["對照比例"] > 0, CL["涵蓋率"] / CL["對照比例"], np.nan)
    CL.to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.10g")
    lab = {k: (CAT[c], l) for k, c, l in KS}
    grid = []
    for (seg, ver, kk), x in CL.groupby(["段", "版本", "情況"], sort=False):
        x1 = x[x["F4飆股數"] >= 1]; x30 = x[x["F4飆股數"] >= 30]
        rt = x1["倍數"].dropna()
        grid.append({"段": seg, "版本": ver, "情況": kk, "類": lab[kk][0], "說明": lab[kk][1], "格數(≥1)": len(x1),
                     "涵蓋率中位": x1["涵蓋率"].median(), "p10": x1["涵蓋率"].quantile(0.1), "p90": x1["涵蓋率"].quantile(0.9),
                     "對照比例中位": x1["對照比例"].median(), "倍數中位": rt.median() if len(rt) else np.nan,
                     "倍數 p10": rt.quantile(0.1) if len(rt) else np.nan, "倍數 p90": rt.quantile(0.9) if len(rt) else np.nan,
                     "格數(≥30)": len(x30), "涵蓋率中位(≥30)": x30["涵蓋率"].median() if len(x30) else np.nan,
                     "倍數中位(≥30)": x30["倍數"].dropna().median() if len(x30) else np.nan,
                     "F4飆股數 各格加總": int(x["F4飆股數"].sum())})
    GR = pd.DataFrame(grid)
    GR["一般F4股也差不多"] = GR["倍數中位"].between(0.8, 1.25)
    GR.to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    cnts = {}
    for seg, (a_, b_) in SEGS.items():
        eseg = (e_mon >= a_) & (e_mon <= b_)
        for ver in VERS:
            eb = eseg & (e_el if ver != "全部" else True)
            cnts[f"{seg}｜{ver}"] = {"F4飆股（各格加總）": int(eb.sum()), "不同 (股, 起漲日)": len(set(zip(e_sid[eb].tolist(), e_d[eb].tolist()))),
                                    "不同股票": len(set(e_sid[eb].tolist())), "有 ≥1 F4 飆股的格": int(len(set(e_cell[eb].tolist()))),
                                    "有 ≥30 F4 飆股的格": int((np.bincount(e_cell[eb], minlength=NC5) >= 30).sum())}
    SM = {"讀法寫死": TAGT, "執行": now_tpe() + "（台北）", "資料": {"旗": "~/minework/flags_main.npz（researchMine seq3）", "主快照": RM.MAIN_SHA,
                                                             "月營收": "revenue_hist @796d94c9da", "s5": "~/s5work（950ad26e12＋b53f5540a8）"},
          "閘門": {"事件＝bing_events.npz": True, "EPS 重算 F4a／F4b 不同": bad, "事件中帶F4比例 重現 bing_grid": rep},
          "F4股月列": int(nr), "對照列 (m,m_next] 無K棒": int((nb == 0).sum()), "月營收算不出年增（列比例）": float((~fy).mean()),
          "件數": cnts, "情況數": K, "產業數": len(inds)}
    json.dump(SM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("===== 本體完成 =====")
    page()


# ═════════════ 網頁 ═════════════
def pc(x, d=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:.{d}f}%"


def rt(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x:.2f}"


NOCMP = {"dlo0", "mcap0", "amt0"}                                   # 對照定義要求月底有 K 棒 ⇒ 「月底沒交易」這格倍數不可比


def note(r):
    if r["情況"] in NOCMP:
        return "對照要求月底有交易 ⇒ 倍數不可比"
    return "一般 F4 股也差不多" if r["一般F4股也差不多"] else ""


def page():
    from backtest.researchMine_page import CSS
    GR = pd.read_csv(os.path.join(OUT, "grid.csv")); SM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    g = GR.set_index(["段", "版本", "情況"])
    A = GR[(GR["段"] == "合併") & (GR["版本"] == "全部")].copy()
    nI = A[A["類"] == CAT[7]]; A = A[A["類"] != CAT[7]]
    A = A.sort_values(["涵蓋率中位", "p90"], ascending=False)
    nI = nI.sort_values("涵蓋率中位", ascending=False)
    c_all = SM["件數"]["合併｜全部"]; c_w1 = SM["件數"]["合併｜W1 母體內"]
    css = CSS.replace("max-width:820px", "max-width:900px") + "<style>td small{color:var(--note)}.k{font-size:.8em;color:var(--note)}</style>"
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>連續虧損股的飆股特徵</title>", css, "</head><body>",
         "<h1>連續虧損（F4）的股票裡，後來變飆股的那些，起漲前有什麼共同情況？</h1>",
         f"<p class='note'>使用者原話：「順著F4繼續往下」｜接續 PREREG地雷股濾網 seq3 的丙（起漲前一個判定日帶 F4 連續虧損的飆股約占 38%）｜"
         f"只描述（參考、不計檢定數、不需登錄）｜回測線執行，讀法寫死 {html.escape(TAGT)}。這是歷史統計，不是對任何一檔的預測或買賣建議。</p>"]

    # ── 結論
    hi = A[A["涵蓋率中位"] >= 0.5]
    H.append("<div class='box'><b>結論（2017-03～2026-08，全部上市櫃）</b><ul>")
    H.append(f"<li>起漲前一個月底帶 F4 連續虧損的飆股：{c_all['不同股票']} 檔股票、{c_all['不同 (股, 起漲日)']:,} 個起漲點（各格加總 {c_all['F4飆股（各格加總）']:,} 筆）。"
             "下面每個比例都是 250 種飆股定義各算一次、取中位數。</li>")
    if len(hi):
        items = "；".join(f"{html.escape(r['說明'])} <b>{pc(r['涵蓋率中位'])}</b>" + ("（一般 F4 股也差不多）" if r["一般F4股也差不多"] else
                         f"（沒變飆股的 F4 股 {pc(r['對照比例中位'])}）") for _, r in hi.iterrows())
        H.append(f"<li><b>一半以上的 F4 飆股都有的情況</b>（依比例高到低）：{items}。</li>")
    A["可比"] = ~A["情況"].isin(NOCMP)
    up = A[A["可比"] & (A["倍數中位"] >= 1.5)].sort_values("倍數中位", ascending=False)
    dn = A[A["可比"] & (A["倍數中位"] <= 1 / 1.5)].sort_values("倍數中位")
    if len(up):
        H.append("<li><b>補充：比沒變飆股的 F4 股明顯常見的</b>（倍數 ≥ 1.5；括號 ＝ 涵蓋率、倍數）：" + "；".join(
            f"{html.escape(r['說明'])}（{pc(r['涵蓋率中位'])}、{rt(r['倍數中位'])} 倍）" for _, r in up.iterrows()) + "。</li>")
    if len(dn):
        H.append("<li><b>補充：比沒變飆股的 F4 股明顯少見的</b>（倍數 ≤ 0.67）：" + "；".join(
            f"{html.escape(r['說明'])}（{pc(r['涵蓋率中位'])}、{rt(r['倍數中位'])} 倍）" for _, r in dn.iterrows()) + "。</li>")
    H.append("<li>⚠ 起漲日落在短期低點附近（離 5／10 日最低點近、5 日報酬差）有一部分是「起漲日」的定義使然（起漲日 ＝ 之後會漲上去的第一天），"
             "所有飆股都有這個傾向，不是 F4 股特有。</li>")
    sd = []
    for _, r in A.iterrows():
        e1 = g.loc[("探索", "全部", r["情況"]), "涵蓋率中位"]; e2 = g.loc[("確認", "全部", r["情況"]), "涵蓋率中位"]
        if np.isfinite(e1) and np.isfinite(e2) and abs(e2 - e1) >= 0.10:
            sd.append((e2 - e1, r["說明"], e1, e2))
    if sd:
        sd.sort()
        H.append("<li><b>兩段差 10 個百分點以上的</b>（2017-03～2021 → 2022～2026-08）：" + "；".join(
            f"{html.escape(nm_)} {pc(a_)} → {pc(b_)}" for _, nm_, a_, b_ in sd) + "。</li>")
    W1 = GR[(GR["段"] == "合併") & (GR["版本"] == "W1 母體內") & (GR["類"] != CAT[7])].sort_values(["涵蓋率中位", "p90"], ascending=False)
    hw = W1[W1["涵蓋率中位"] >= 0.5]
    if len(hw):
        H.append(f"<li><b>只看 W1 母體內（營量／營飆能買的，{c_w1['不同股票']} 檔、{c_w1['不同 (股, 起漲日)']:,} 個起漲點）</b>，一半以上有的情況：" + "；".join(
            f"{html.escape(r['說明'])} <b>{pc(r['涵蓋率中位'])}</b>（對照 {pc(r['對照比例中位'])}）" for _, r in hw.iterrows()) + "。</li>")
    H.append("<li>「倍數」只是補充：涵蓋率 ÷ 同期沒變飆股的 F4 股-月有這個情況的比例。倍數在 0.8～1.25 的項目標「一般 F4 股也差不多」——"
             "這種情況是連續虧損股本來就常有的，不是飆股才有。全部項目都列在下面的表，沒有挑。</li>")
    H.append("</ul></div>")
    # ── 主表
    H.append("<h2>一、全部情況（依涵蓋率高到低；全部上市櫃、2017-03～2026-08）</h2>")
    H.append("<p class='note'>涵蓋率 ＝ 變飆股的 F4 股裡有這個情況的比例（250 格中位；小字 p10～p90）。對照 ＝ 同期「沒變飆股的 F4 股-月」有這個情況的比例。"
             "1～5、7 類看起漲前一個月底（F4 旗那一天，只用當時已公布的資料）；6 類看起漲日當天（對照 ＝ 那個月每個交易日的平均）。</p>")
    hd = ["情況", "類", "涵蓋率", "沒變飆股的 F4 股-月", "倍數", "註"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i < 2 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    for _, r in A.iterrows():
        H.append(f"<tr><td class=l>{html.escape(r['說明'])}</td><td class='l k'>{html.escape(r['類'][2:])}</td>"
                 f"<td><b>{pc(r['涵蓋率中位'])}</b> <small>{pc(r['p10'])}～{pc(r['p90'])}</small></td><td>{pc(r['對照比例中位'])}</td>"
                 f"<td>{rt(r['倍數中位']) if r['可比'] else '—'}</td><td class=l>{note(r)}</td></tr>")
    H.append("</table></div>")
    H.append("<p class='note'>分段的項目（例：連續虧損幾季、市值五等分）各段加起來是 100%，所以會分散在表的不同位置（逐格數字見 cells.csv.gz、彙總見 grid.csv）。"
             "五等分 ＝ 當天全市場（有交易的上市櫃普通股）排序切五份。「日均成交量」用成交金額（張數跨股不能比）。</p>")
    # ── 分類分佈（自然順序）
    H.append("<h2>二、兩段比較（全部上市櫃）</h2><p class='note'>同一張表、依合併段涵蓋率排序；差 ＝ 2022～2026-08 減 2017-03～2021（百分點）。</p>")
    hd = ["情況", "2017-03～2021", "2022～2026-08", "差", "合併"]
    H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
    for _, r in A.iterrows():
        e1 = g.loc[("探索", "全部", r["情況"]), "涵蓋率中位"]; e2 = g.loc[("確認", "全部", r["情況"]), "涵蓋率中位"]
        dfx = (e2 - e1) * 100 if np.isfinite(e1) and np.isfinite(e2) else np.nan
        H.append(f"<tr><td class=l>{html.escape(r['說明'])}</td><td>{pc(e1)}</td><td>{pc(e2)}</td><td>{'—' if not np.isfinite(dfx) else f'{dfx:+.0f}'}</td><td>{pc(r['涵蓋率中位'])}</td></tr>")
    H.append("</table></div>")
    c1 = SM["件數"]["探索｜全部"]; c2 = SM["件數"]["確認｜全部"]
    H.append(f"<p class='note'>F4 飆股：2017-03～2021 {c1['不同股票']} 檔／{c1['不同 (股, 起漲日)']:,} 個起漲點；2022～2026-08 {c2['不同股票']} 檔／{c2['不同 (股, 起漲日)']:,} 個起漲點。</p>")
    # ── 產業
    H.append("<h2>三、產業（現值套回，後見）</h2>")
    H.append("<div class='wrap'><table><tr><th class=l>產業</th><th>涵蓋率</th><th>沒變飆股的 F4 股-月</th><th>倍數</th><th class=l>註</th></tr>")
    for _, r in nI.iterrows():
        if not (r["涵蓋率中位"] > 0 or r["p90"] > 0 or r["對照比例中位"] > 0):
            continue
        H.append(f"<tr><td class=l>{html.escape(r['說明'])}</td><td><b>{pc(r['涵蓋率中位'], 1)}</b> <small>{pc(r['p10'], 1)}～{pc(r['p90'], 1)}</small></td>"
                 f"<td>{pc(r['對照比例中位'], 1)}</td><td>{rt(r['倍數中位'])}</td><td class=l>{'一般 F4 股也差不多' if r['一般F4股也差不多'] else ''}</td></tr>")
    H.append("</table></div><p class='note'>產業別是今天的分類套回過去（公司可能改過產業），標「後見」。涵蓋率與對照都是 0 的產業不列（見 grid.csv）。</p>")
    # ── W1
    W = GR[(GR["段"] == "合併") & (GR["版本"] == "W1 母體內") & (GR["類"] != CAT[7])].sort_values(["涵蓋率中位", "p90"], ascending=False)
    H.append(f"<h2>四、只看 W1 母體內（營量／營飆能買的股票）</h2><p class='note'>起漲前一個月底在 W1 母體內的 F4 飆股：{c_w1['不同股票']} 檔、{c_w1['不同 (股, 起漲日)']:,} 個起漲點；"
             f"有 ≥ 1 筆的格 {c_w1['有 ≥1 F4 飆股的格']} 格。對照也只取 W1 母體內的 F4 股-月。</p>")
    H.append("<div class='wrap'><table><tr><th class=l>情況</th><th>涵蓋率</th><th>沒變飆股的 F4 股-月</th><th>倍數</th><th>全部上市櫃版涵蓋率</th></tr>")
    for _, r in W.iterrows():
        H.append(f"<tr><td class=l>{html.escape(r['說明'])}</td><td><b>{pc(r['涵蓋率中位'])}</b> <small>{pc(r['p10'])}～{pc(r['p90'])}</small></td>"
                 f"<td>{pc(r['對照比例中位'])}</td><td>{'—' if r['情況'] in NOCMP else rt(r['倍數中位'])}</td><td>{pc(g.loc[('合併', '全部', r['情況']), '涵蓋率中位'])}</td></tr>")
    H.append("</table></div>")
    # ── 讀法
    H.append("<h2>五、怎麼算的</h2><ul class='note'>"
             "<li>飆股 ＝ 飆股回推 seq6 網格的 250 種定義（不同持有天數上限 × 不同漲幅門檻），s5 全日曆名單，起漲日加上持有天數上限要在 2026-08-31 以前；每個數字是 250 格各算一次的中位（只算有 F4 飆股的格），小字 p10～p90。</li>"
             "<li>F4 連續虧損 ＝ 起漲日之前最後一個月底，最近 4 季 EPS 合計虧且最近一季虧，或最近 8 季有 6 季以上虧（財報用當時已公布的）。</li>"
             "<li>沒變飆股的 F4 股-月 ＝ 同期其他帶 F4 的股票-月份中，接下來一個月沒有在該格起漲的（定義域同地雷股濾網丙）。</li>"
             "<li>月營收公布日：2025-12 以前算次月 10 日之後第一個交易日，2026-01 期起算次月 15 日之後。季報公布日同地雷股濾網（有上傳時戳用時戳，否則法定期限＋5 個交易日）。</li>"
             "<li>同一檔股票在不同飆股定義（格）下會重複出現；每格各自算比例再取中位，所以一檔不會被算成很多票。</li>"
             "<li>全部項目照列，沒有挑前幾名；倍數只是補充，不是「能不能事先抓到」的檢定。結論框裡的「一半以上」「倍數 ≥ 1.5」「兩段差 10 點以上」只是摘要的取法，完整數字都在表裡。</li></ul>")
    if CK:
        H.append(f"<p class='note'>抽樣查核（獨立寫法重算）：{'0 不同，過' if CK.get('過') else '有不同，見 check.json'}。</p>")
    H.append(f"<p class='note'>閘門：事件與地雷股濾網丙逐筆相同；事件中帶 F4 的比例重現丙（全部 {pc(SM['閘門']['事件中帶F4比例 重現 bing_grid']['全部']['本件重算'], 1)}、"
             f"W1 {pc(SM['閘門']['事件中帶F4比例 重現 bing_grid']['W1 母體內']['本件重算'], 1)}）；EPS 重算的 F4 與地雷股濾網逐格相同。檔案：backtest/resultsMine/F4/。</p>")
    H.append("</body></html>")
    open(os.path.join(OUT, "連續虧損股的飆股特徵.html"), "w", encoding="utf-8").write("\n".join(H))


# ═════════════ 查核（獨立寫法）═════════════
def check():
    """⛔ 不呼叫本檔 body 的函式與 researchMine 的函式；只讀原始 CSV、s5 原表、本體輸出。"""
    rng = np.random.default_rng(20261008)
    cname = lambda c: f"H{HS5[c // len(GS5)]}_g{int(round(GS5[c % len(GS5)] * 100))}%"
    res = {"時間": now_tpe() + "（台北）", "種子": 20261008}
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz"))
    RW = np.load(os.path.join(WORK, "rows.npz"), allow_pickle=False)
    keys = [str(k) for k in RW["keys"]]; KI = {k: i for i, k in enumerate(keys)}
    z = np.load(os.path.expanduser("~/minework/flags_main.npz"))
    sids = [str(x) for x in z["sids"]]; me = pd.to_datetime(pd.Series(z["me"]))
    # 日曆（自己讀）
    calm = pd.to_datetime(pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"]).sort_values().reset_index(drop=True)
    c1 = pd.read_csv(os.path.expanduser("~/earlydata/3edc0e2206/main/data/meta/calendar_twse.csv"))["date"]
    c2 = pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"]
    cal5 = pd.to_datetime(pd.concat([c1, c2[c2 <= "2026-09-24"]], ignore_index=True)).reset_index(drop=True)
    assert len(cal5) == 5571
    d5 = {t: i for i, t in enumerate(cal5)}
    # 自己算月底：每個曆月最後一個交易日（最後一個月未完不算）
    mlast = calm.groupby(calm.dt.to_period("M")).max().iloc[:-1].reset_index(drop=True)
    assert (mlast.values == me.values).all()
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)["stock_id"].tolist()
    # ── EPS（自己寫）
    fh = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "eps_q", "eps_ytd"]) for f in sorted(glob.glob(os.path.join(MAIN, "mops", "fin_hist", "*.csv")))])
    fh = fh.drop_duplicates(["stock_id", "period"], keep="last")
    fd = pd.read_csv(os.path.join(MAIN, "meta", "filing_dates.csv"), dtype=str)
    fd["dd"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce"); fd = fd.dropna(subset=["dd"])
    up = fd.groupby(["stock_id", "year", "season"])["dd"].min()
    up.index = [(a, int(b), int(c)) for a, b, c in up.index]; up = up.to_dict()
    EPSQ = {}
    for x, gg in fh.groupby("stock_id"):
        ytd = {pd.Period(p, "Q"): float(v) for p, v in zip(gg["period"], pd.to_numeric(gg["eps_ytd"], errors="coerce"))}
        qq = {pd.Period(p, "Q"): v for p, v in zip(gg["period"], pd.to_numeric(gg["eps_q"], errors="coerce"))}
        out = {}
        for P_, v in ytd.items():
            if P_.quarter == 1:
                e = v
            else:
                pv = ytd.get(P_ - 1, np.nan)
                e = v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan
            if not np.isfinite(e) and np.isfinite(qq.get(P_, np.nan)):
                e = qq[P_]
            ts = up.get((x, P_.year, P_.quarter))
            if ts is not None:
                av = calm[calm > ts].iloc[0] if (calm > ts).any() else None
            else:
                dl = pd.Timestamp(P_.year + 1, 3, 31) if P_.quarter == 4 else pd.Timestamp(P_.year, *{1: (5, 15), 2: (8, 14), 3: (11, 14)}[P_.quarter])
                k = int((calm <= dl).sum()) + 5
                av = calm.iloc[k] if k < len(calm) else None
            out[P_] = (e, av)
        EPSQ[x] = out

    def eps_at(x, mdate):
        o = EPSQ.get(x)
        if not o:
            return None
        avail = [P_ for P_, (e, av) in o.items() if av is not None and av <= mdate]
        if not avail:
            return None
        top = max(avail)
        return [o[top - j][0] if (top - j) in o else np.nan for j in range(12)]
    # ── 月營收（自己寫）
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in sorted(glob.glob(os.path.join(REVD, "*.csv")))])
    rv["stock_id"] = rv["stock_id"].str.strip(); rv = rv.drop_duplicates(["stock_id", "period"], keep="last")
    REV = {x: dict(zip(gg["period"], pd.to_numeric(gg["當月營收"], errors="coerce"))) for x, gg in rv.groupby("stock_id")}

    def pub(p):
        P_ = pd.Period(p, "M") + 1
        cut = pd.Timestamp(P_.year, P_.month, 10 if p <= "2025-12" else 15)
        return calm[calm > cut].iloc[0] if (calm > cut).any() else pd.Timestamp("2100-01-01")

    pubc = {}

    def rev_at(x, mdate):
        R_ = REV.get(x, {})
        ps = sorted(p for p, v in R_.items() if np.isfinite(v))
        ok = [p for p in ps if pubc.setdefault(p, pub(p)) <= mdate]
        if not ok:
            return None
        p = ok[-1]; P_ = pd.Period(p, "M"); v = R_[p]
        g12 = R_.get(str(P_ - 12), np.nan)
        y = v / g12 - 1 if np.isfinite(g12) and g12 > 0 else np.nan
        hs = {}
        for L, mn in ((12, 9), (24, 18)):
            prev = [R_.get(str(P_ - k), np.nan) for k in range(1, L + 1)]; prev = [w for w in prev if np.isfinite(w)]
            hs[L] = len(prev) >= mn and v >= max(prev)
        st = 0; Q_ = P_
        while True:
            a_ = R_.get(str(Q_), np.nan); b_ = R_.get(str(Q_ - 12), np.nan)
            if np.isfinite(a_) and np.isfinite(b_) and b_ > 0 and a_ / b_ - 1 > 0:
                st += 1; Q_ = Q_ - 1
            else:
                break
        return y, hs[12], hs[24], st
    bj = json.load(open(os.path.join(S5W, "build.json"), encoding="utf-8")); FX = {c: i for i, c in enumerate(bj["特徵欄"])}
    Qm = np.load(os.path.join(S5W, "Q.npy"), mmap_mode="r"); bar5 = np.load(os.path.join(S5W, "bar.npy"), mmap_mode="r")
    ind = pd.read_csv(os.path.join(MAIN, "meta", "industry.csv"), dtype=str)
    IND = dict(zip(ind["stock_id"].str.strip(), ind["industry_name"].fillna("").str.strip()))
    flagk = ("F2_1", "F2_05", "F1_50", "F1_70", "F3_half", "F3_neg", "F5a", "F5b", "F5", "G2")

    def feats_row(x, i_me, s5i, mdate):
        """一個 (股, 判定日) 的 1～5、7 類情況（dict）；None ⇒ 不是 F4。"""
        e = eps_at(x, mdate)
        if e is None:
            return None
        e = np.array(e, float)
        a = bool(np.isfinite(e[:4]).all() and e[:4].sum() < 0 and e[0] < 0)
        b = bool(np.isfinite(e[:8]).all() and (e[:8] < 0).sum() >= 6)
        if not (a or b):
            return None
        o = {"f4a_only": a and not b, "f4b_only": b and not a, "f4ab": a and b, "F4a": a, "F4b": b}
        o["e_qoq"] = bool(e[0] > e[1]); o["e_yoy"] = bool(e[0] > e[4]); o["e_pos"] = bool(e[0] > 0)
        o["e_pos4"] = bool(np.isfinite(e[:4]).all() and e[0] > 0 and e[:4].sum() < 0)
        o["e_4v4"] = bool(np.isfinite(e[:8]).all() and e[:4].sum() > e[4:8].sum())
        n = 0
        for v in e:
            if np.isfinite(v) and v < 0:
                n += 1
            else:
                break
        for k, (lo_, hi2) in {"lq0": (0, 0), "lq1": (1, 1), "lq2": (2, 2), "lq3": (3, 3), "lq4": (4, 7), "lq8": (8, 99)}.items():
            o[k] = lo_ <= n <= hi2
        r = rev_at(x, mdate)
        y = r[0] if r else np.nan; fy = bool(np.isfinite(y))
        o["rv_y0"] = fy and y > 0; o["rv_y20"] = fy and y > 0.2
        o["rv_h12"] = bool(r[1]) if r else False; o["rv_h24"] = bool(r[2]) if r else False
        st = r[3] if r else 0
        for k, (lo_, hi2) in {"rs0": (0, 0), "rs1": (1, 2), "rs3": (3, 5), "rs6": (6, 11), "rs12": (12, 999)}.items():
            o[k] = fy and lo_ <= st <= hi2
        o["rv_na"] = not fy
        j = sids.index(x)
        for k in flagk:
            o[k] = bool(z[k][i_me, j])
        m5 = d5[mdate]
        for col, k, _, _ in QX:
            q = int(Qm[FX[col], s5i, m5])
            for v in range(6):
                o[f"{k}{v}"] = q == v
        nmx = IND.get(x, "") or "（查無產業別）"
        for kk in keys:
            if kk.startswith("ind_"):
                o[kk] = kk[4:] == nmx
        return o

    def feats_day(s5i, dd):
        hits = [int(Qm[FX[col], s5i, dd]) == code for _, col, code in FEATS]
        o = {f"ft{i}": h for i, h in enumerate(hits)}
        c = min(sum(hits), 5)
        for k in range(6):
            o[f"fc{k}"] = c == k
        return o
    errs = []
    # ① 抽 2 格：事件端涵蓋率
    cand = CL[(CL["段"] == "合併") & (CL["版本"] == "全部") & (CL["情況"] == "F4a")]
    cand = cand[cand["F4飆股數"] >= 30]["cell"].to_numpy()
    pick = rng.choice(cand, 2, replace=False)
    E = np.load(os.path.join(S5W, "events.npz"))
    icut = d5[pd.Timestamp(CUT)]
    cellres = []
    for c in pick:
        H = HS5[int(c) // 10]
        m_ = (E["cell"] == c) & (E["d"] + H <= icut)
        rows = []
        for s5i, dd in zip(E["s"][m_].astype(int), E["d"][m_].astype(int)):
            t = cal5[dd]
            if not ("2017-03" <= str(t)[:7] <= "2026-08"):
                continue
            x = uni[s5i]
            if x not in sids:
                continue
            i_me = int((me < t).sum()) - 1
            o = feats_row(x, i_me, s5i, me.iloc[i_me])
            if o is None:
                continue
            o.update(feats_day(s5i, dd)); rows.append(o)
        df = pd.DataFrame(rows)
        ref = CL[(CL["段"] == "合併") & (CL["版本"] == "全部") & (CL["cell"] == c)].set_index("情況")
        nd = 0
        for kk in keys:
            mine = float(df[kk].mean()) if len(df) else np.nan
            if int(ref.loc[kk, "F4飆股數"]) != len(df) or not np.isclose(mine, ref.loc[kk, "涵蓋率"], rtol=1e-9, atol=1e-12):
                nd += 1; errs.append(f"格 {cname(int(c))} {kk}：查核 {len(df)}／{mine}，本體 {int(ref.loc[kk, 'F4飆股數'])}／{ref.loc[kk, '涵蓋率']}")
        cellres.append({"格": cname(int(c)), "F4飆股": len(df), "情況數": len(keys), "不同": nd})
    res["① 事件端涵蓋率（2 格全部情況）"] = cellres
    # ② 抽 300 個 F4 股-月逐項比
    nr = len(RW["R_i"]); pk = rng.choice(nr, 300, replace=False); nd = 0
    X = RW["X"]
    for r in pk:
        i_me, j = int(RW["R_i"][r]), int(RW["R_j"][r]); x = sids[j]; s5i = uni.index(x)
        o = feats_row(x, i_me, s5i, me.iloc[i_me])
        if o is None:
            nd += 1; errs.append(f"列 {x} {me.iloc[i_me].date()}：查核不是 F4"); continue
        m5 = d5[me.iloc[i_me]]; m5n = d5[me.iloc[i_me + 1]]
        days = [dd for dd in range(m5 + 1, m5n + 1) if bool(bar5[s5i, dd])]
        if days:
            fd_ = pd.DataFrame([feats_day(s5i, dd) for dd in days]).mean()
            o.update(fd_.to_dict())
        else:
            o.update({f"ft{i}": 0.0 for i in range(len(FEATS))}); o.update({f"fc{k}": 0.0 for k in range(6)})
        for kk in keys:
            if not np.isclose(float(o[kk]), float(X[r, KI[kk]]), rtol=1e-9, atol=1e-12):
                nd += 1; errs.append(f"列 {x} {me.iloc[i_me].date()} {kk}：查核 {o[kk]} 本體 {X[r, KI[kk]]}")
    res["② F4 股-月逐項（300 列 × 全部情況）"] = {"列": 300, "情況數": len(keys), "不同": nd}
    # ③ 對照比例：用 rows 以 pandas 重算 2 格
    hdef = np.load(os.path.join(S5W, "hdef.npy"), mmap_mode="r")
    df = pd.DataFrame({"s5": RW["rs5"], "m5": RW["rm5"], "m5n": RW["rm5n"], "i": RW["R_i"], "j": RW["R_j"]})
    df["mon"] = [str(cal5[v + 1])[:7] for v in df["m5"]]
    df["bar"] = [bool(bar5[a_, b_]) for a_, b_ in zip(df["s5"], df["m5"])]
    df["hd1"] = [int(hdef[a_, b_ + 1]) for a_, b_ in zip(df["s5"], df["m5"])]
    VD = RW["VD"]; nd3 = []
    for c in pick:
        H = HS5[int(c) // 10]
        m_ = E["cell"] == c
        evs = set(zip(E["s"][m_].astype(int).tolist(), E["d"][m_].astype(int).tolist()))
        bys = {}
        for a_, b_ in evs:
            bys.setdefault(a_, []).append(b_)
        has = np.array([any(m5 < q <= m5n for q in bys.get(s5_, [])) for s5_, m5, m5n in zip(df["s5"], df["m5"], df["m5n"])])
        dom = (df["mon"] >= "2017-03") & (df["mon"] <= "2026-08") & df["bar"] & (df["hd1"] >= H) & (df["m5"] + 1 + H <= icut) & ~has
        ref = CL[(CL["段"] == "合併") & (CL["版本"] == "全部") & (CL["cell"] == c)].set_index("情況")
        k_bad = 0
        for kk in keys:
            v = VD[dom.to_numpy(), KI[kk]] > 0
            mine = float(X[dom.to_numpy(), KI[kk]][v].mean())
            if not np.isclose(mine, ref.loc[kk, "對照比例"], rtol=1e-9, atol=1e-12) or int(round(ref.loc[kk, "對照股月數"])) != int(v.sum()):
                k_bad += 1; errs.append(f"對照 {cname(int(c))} {kk}：查核 {int(v.sum())}／{mine} 本體 {ref.loc[kk, '對照股月數']}／{ref.loc[kk, '對照比例']}")
        nd3.append({"格": cname(int(c)), "對照股-月": int(dom.sum()), "不同": k_bad})
    res["③ 對照比例（2 格全部情況）"] = nd3
    res["錯誤（前 30）"] = errs[:30]
    res["合計不同"] = len(errs); res["過"] = len(errs) == 0
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        return check()
    if a.stage == "body":
        body(a)
    else:
        page()


if __name__ == "__main__":
    main()

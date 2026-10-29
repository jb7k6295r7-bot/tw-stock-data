# -*- coding: utf-8 -*-
"""葛蘭碧原版（200 日線＋前低停損）seq2 追加拆件（§九）【頻率表＋全部描述欄乾跑／正式程式】——回測線計算子代理。

登錄：登錄全文-葛蘭碧原版200日線加前低停損與乖離太遠會不會回來_單筆層登錄_台股策略線_seq2_sha194c5d8d0cdcd663-8715B-20261029-1941.md
      （整檔 8715 B；整檔 sha256 eb0ea825… ≠ ⇒ 照 pw1 慣例去末行戳記重算 ＝ 194c5d8d0cdcd663…，相符；回測線計算子代理 2026-10-29 19:48 已驗）
核可：裁定 seq487 §二（拆件全部只描述、⛔ 不計 N、⛔ 不改 seq1 判語；先交頻率表（⛔ 不附報酬），核後再跑；買 2 的 B 組優先）；
      seq487 當時的固定句「拆件是看過 seq1 結果後追加的，只描述」已由裁定 seq490 更正（見沿革）。
沿革：2026-10-30 02:35（台北）照裁定 seq490（更正 seq487 §二、seq488：拆件改認「事前定好的拆法」）、seq492（核台股登錄 seq3
      sha 1fc4dda730b513ac、9973 B，只改 §九 標籤）改標籤：固定句換成 PHRASE；不產生新判定、不加 N 的理由改為「04:24 只定了拆什麼、
      沒定怎樣算通過」（⛔ 不是因為看過結果）；補確認段 Bonferroni 18 格 CI（3 買點 × A1～A3、B1～B3，雙尾 1−0.05/18 ＝ 99.72%），
      與 99% CI 並列；★S4、★S6、★S8、★S9 註一行。⛔ 數字不變、不重跑：--relabel 只讀 formal/ 既有輸出（main_excess.csv.gz、
      desc.csv、formal.json）改標籤、加 CI 欄，並自驗既有數字逐位元相同（commit b5bc39f2cd）。
§一～§八 與 seq1 一字不改 ⇒ 母體、成本、對照、段、去重、硬斷點、CI 方法全照 seq1 程式 backtest/researchGranville.py（commit 48c8bcb982）。
⛔ 本檔只 import researchGranville（seg_features、shift、runlen、dedup、segof、mkey、exit_sim、exit_price、match_day、deciles、cluster_boot、
   merged_hl、dry_status），⛔ 不改它（seq1 輸出逐位元不變）；拆件版本的進場條件在本檔另算，A0 每檔每根都與 G.seg_features 逐位比對，不符即停。
⛔ 乾跑（--dry）：只數事件、配對、n_eff、出場原因（次數）、持有天數分布、與 A0 的重疊；⛔ 不讀、不算、不存任何報酬／超額／勝率（seq366／458／459）；
   描述欄的報酬一律填 0 當佔位，輸出只寫 filled／EMPTY 與件數。
⛔ 不 commit。

用法（cd ~/tw-p17）：
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville2 --dry [--procs 3] [--limit N（煙霧測，輸出 ~/grvwork/dry2）]
        ⇒ backtest/resultsGranville2/freq/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville2 --formal --ruling seq487
        ⇒ 正式跑（⛔ 兩個旗標都要給、ruling 必須是 seq487，否則拒跑；裁定 seq488 §二 已核可正式跑）→ backtest/resultsGranville2/formal/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville2 --relabel --ruling seq490
        ⇒ 只改標籤＋補 Bonferroni 18 格 CI（裁定 seq490／seq492；⛔ 不重跑、數字不變；讀寫 backtest/resultsGranville2/formal/）
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville2_check

══════════ 登錄 §九（照抄）══════════
 A 組（只拆進場；出場一律 seq1 主臂：停損或賣 5 先到、上限 250 日）：
   A0 原版｜A1 拿掉 MA200 方向條件｜A2 拿掉前置位置條件（買 1：前 60 日至少 40 日在線下；買 2：跌破前 20 日都在線上、k ≤ 10；
   買 3：前 20 日都在線上）｜A3 只剩觸發
 B 組（只拆出場；進場一律 seq1 原版）：B0 原版｜B1 只停損（不用賣 5，上限 250 日）｜B2 只賣 5（不用停損，上限 250 日）｜B3 都不用，固定抱 250 日
 每版必報：事件數、n_eff、停損與賣 5 先到比例、持有中位、超額平均與中位、去掉最大 1 筆；結果句必附固定句（seq3 §九 ＝ PHRASE）。
 seq3 §九 增：多重比較 確認段 3 買點 × 6 新版（A1～A3、B1～B3）＝ 18 格 ⇒ 另報 Bonferroni 18 格 CI（99.72%），與 99% CI 並列，⛔ 不只列 99%。

══════════ ★ 執行者讀法（⛔ 在跑任何本檔程式之前寫死於 2026-10-29 19:52（台北，WSL TZ=Asia/Taipei date）；〔 〕內為另一讀法；皆取保守）══════════
 寫死前看過：登錄 seq2 全文、裁定 seq487、seq1 程式與自測（researchGranville.py／_check.py）、seq1 頻率表事件檔欄名；
   ⚠ 裁定 seq487 §一 轉述了 seq1 買 2 的兩個數字（確認段 CI 下緣、固定抱 60 日超額）——本子代理讀到了，⛔ 本檔不算、不印任何報酬。
 ★S1 seq1 的 ★1～★19 全部沿用（同一資料版 9b0e98、同一價格面板與高低價快取 ~/grvwork/hl_*.pkl、同一閘、去重、配對、出場、走得完、段與月分群）。
 ★S2 各版的「方向條件」：買 1 ＝「MA200 上揚或走平」（＝ 非下彎）；買 2、買 3 ＝「MA200 上揚」（只在 t 判，同 seq1 ★6）。拿掉 ＝ 不看方向（上揚、走平、下彎都可）。
 ★S3 各版的「前置位置條件」照登錄 §九 括號：買 1 ＝ t−60～t−1 至少 40 日收盤 < MA200；買 2 ＝ 跌破前 20 日（b−20～b−1）都在線上 且 1 ≤ k ≤ 10；
     買 3 ＝ t−20～t−1 都在線上。
 ★S4 「觸發」：買 1 ＝ t−1 收盤 ≤ MA200 且 t 收盤 > MA200；買 3 ＝ t 最低 ≤ MA200×1.02 且收盤 > MA200；
     買 2 ＝ 跌破後第一次站回 ＝ t−1 起往回連續 k ≥ 1 根線下（≤）、t 線上，且 ★ 跌破那根 b 的前一根 b−1 是線上（有 MA200 且收盤 > MA200）
     ＝ 真的「由上往下跌破」才算〔另一讀法：線下段從 MA200 剛可算的第一根開始也算跌破〕。A2／A3 的 k 不設上限。
 ★S5 停損價 S 不屬進場條件 ⇒ 各版照 seq1 定義（買 1 ＝ t−60～t−1 最低收盤；買 2 ＝ 跌破期間 b～t−1 最低收盤（k 不限時照算）；買 3 ＝ t 最低）。
 ★S6 可判（回看窗）各版一律沿用 A0 的可判條件（J1：t−60～t−1 都有 MA200 且 t−20 有 MA200；J2：t−30 有 MA200；J3：t−20 有 MA200；皆同段不跨壞根）
     ⇒ 各版分母（可判股日）相同、A0 原始訊號 ⊆ A1、A2 ⊆ A3〔另一讀法：拿掉條件後只要求剩下條件所需的窗，會在每段前 20～60 根多出少量訊號〕。
 ★S7 去重（60 日內只取第一次）、閘 G[t] 都在各版自己的原始訊號上做 ⇒ 拿掉條件後新增的早到訊號可能把 A0 的事件擠掉（照報「A0 有、本版沒有」件數）。
 ★S8 對照「當天沒有該買點訊號」＝ 當天沒有【本版】原始訊號〔另一讀法：沒有 seq1 原版訊號〕；每版各起一條 rng（種子 20261028），事件依 (t, 代號) 序抽
     （＝ seq1 同式）。B 組進場 ＝ A0 ⇒ 事件、對照與 A0（＝ seq1）完全相同，只換出場。
 ★S9 B 組出場：B1 ＝ 只看「收盤 < S」；B2 ＝ 只看賣 5（收盤 < MA200 且 MA200 下彎）；觸發 ⇒ 次日開盤賣、上限 250 日收盤、賣出根恰為上限根 ⇒ 開盤與收盤取較低
     （seq373）、壞根前強制出、下市末根 ＝ seq1 ★8 同式（以 seq1 exit_sim 實作：不用的臂把停損價設 −∞／賣 5 狀態設全否）。
     B3 ＝ 不看任何觸發，e＋250 合併日曆位置當天或之前最後一根有效收盤〔另一讀法：e＋249〕；遇壞根、下市同 ★8。
 ★S10 走得完：各版一律 e＋250 ≤ 資料尾（同 seq1 ★9，與實際出場無關）。主格 ＝ 配到 ∧ 可進場 ∧ 走得完。n_eff ＝ 該段主格訊號月數；< 24 照〈四十九〉加註「只描述、樣本不足」。
 ★S11 描述欄（§九 每版必報；乾跑 0 佔位）：每格 × 版 × 段：超額（訊號−對照，兩邊各扣 0.585%）平均、中位、去掉最大 1 筆；月分群 bootstrap 99% CI
     （「CI 方法全照 seq1」⇒ 99%、10,000 次、種子 20261028）〔另一讀法：只描述用 95%〕；停損先到（含同日）比例、賣 5 先到比例、持有中位（次數，非報酬）。
     ⛔ 不報勝率（§九 沒列）。
     〔seq490 增〕Bonferroni 18 格 CI：同一 G.cluster_boot（10,000 次、種子 20261028、月分群），alpha ＝ 0.05/18（雙尾 99.72%）；
     確認段 A1～A3、B1～B3 為 18 格本體；A0／B0 與探索段也照算，只當參考／描述。
 ★S12 與 A0 的重疊（每格、A1～A3）：原始訊號數與「A0 原始 ⊆ 本版原始」驗證；事件集（同檔同訊號日）交集、本版新增、A0 有本版沒有；主格同。
 ★S13 seq1 重現：A0 與 B0 的事件檔（代號、日期、段、市場、進場、走得完、配對、對照、主格、市值十分位、產業、出場日、出場方式、出場原因、旗標、持有天數、
     對照出場狀態）必須與 backtest/resultsGranville/freq/events_買k.csv.gz 逐字相同，不符即停（--limit 煙霧測不比）。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchGranville as G                 # noqa: E402  seq1（⛔ 只 import、不改）
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchTriple_freq as TP              # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402

REG_SHA = "194c5d8d0cdcd663"
REG_BYTES = 8715
RULING = "seq487"
OUT = "backtest/resultsGranville2"
SEQ1_FREQ = os.path.join(G.OUT, "freq")
WORK = G.WORK
BUY = G.BUY
SEGS = G.SEGS
AV = ["A0", "A1", "A2", "A3"]
BV = ["B0", "B1", "B2", "B3"]
VERS = AV + BV
ENTRY = {**{v: v for v in AV}, **{v: "A0" for v in BV}}
ARM = {"A0": "SX", "A1": "SX", "A2": "SX", "A3": "SX", "B0": "SX", "B1": "S", "B2": "X", "B3": ""}
VNAME = {"A0": "原版", "A1": "拿掉 MA200 方向條件", "A2": "拿掉前置位置條件", "A3": "只剩觸發",
         "B0": "原版出場（停損或賣5，上限250日）", "B1": "只停損（上限250日）", "B2": "只賣5（上限250日）", "B3": "都不用，固定抱250日"}
PHRASE_SEQ487 = "拆件是看過 seq1 結果後追加的，只描述"            # ⛔ 已由裁定 seq490 更正；只留給自測確認「不再出現」與歷史乾跑檔（freq/）
PHRASE = "拆法在看任何報酬前、照使用者要求定好（10/29 04:24）。用途是看效果來自哪一部分。"   # 裁定 seq490 §一、登錄 seq3 §九
# 裁定 seq490／seq492：標籤更正（登錄 seq3）
REG3_SHA = "1fc4dda730b513ac"
REG3_BYTES = 9973
RELABEL_RULING = "seq490"
RELABEL_RULINGS = ("seq490", "seq492")
BASE_COMMIT = "b5bc39f2cd"
BONF_K = 18
BONF_ALPHA = 0.05 / BONF_K
BONF_LAB = "Bonferroni 18 格 99.72% CI"
BONF_CELLS = [(c, v) for c in ("買1", "買2", "買3") for v in ("A1", "A2", "A3", "B1", "B2", "B3")]
NO_VERDICT_LINE = ("拆件不產生新的判定、不加 N：04:24 的拆法只定了拆什麼、沒定怎樣算數（⛔ 理由不是看過結果；裁定 seq490）；"
                   "某版要變成可照做的規則，照 seq363 另開登錄驗證")
STAR_LINE = "★S4、★S6、★S8、★S9 於 10/29 19:52 寫進程式：只是怎麼數的細節，拆法沒動；不重跑（裁定 seq490）"
BONF_LINE = ("多重比較：確認段 3 買點 × 6 個新版本（A1～A3、B1～B3）＝ 18 格 ⇒ 另報 Bonferroni 18 格 CI（雙尾 1−0.05/18 ＝ 99.72%，"
             "與 99% CI 同一月分群 bootstrap、10,000 次、種子 20261028），和 99% CI 並列；A0／B0、探索段照算只當參考／描述")
RELABEL_NOTE = ("沿革：裁定 seq490（更正 seq487 §二、seq488：拆件改認事前定好的拆法）、seq492（核登錄 seq3 sha 1fc4dda730b513ac）"
                "⇒ 只改標籤、補 Bonferroni 18 格 CI；數字與 commit b5bc39f2cd 逐位元相同、未重跑")
# 裁定 seq487／seq488 §二 要求結果句照記（正式輸出才用）
SEEN_LINE = "子代理讀 seq487 時看到 seq1 買 2 的兩個報酬數字；拆法 10/29 04:24 已定，本件只描述"
A3_LINE = "買 1 A3 與買 2 A3 幾乎是同一觸發（都是前一根收盤在 MA200 之下、當根站回），兩者不要當成兩個獨立證據"
FORMAL_RULING_NOTE = "正式跑核可：裁定 seq488 §二（帶 --formal --ruling seq487；★S4、★S6、★S8、★S9 核）"
NOTES = ["乾跑：未讀、未算、未存任何報酬、超額、勝率（seq366／458／459）；描述欄報酬以 0 佔位，只報 filled／EMPTY",
         PHRASE + "不新增判定格、不計 N（理由：04:24 只定了拆什麼、沒定怎樣算數；⛔ 不是因為看過結果）、不改 seq1 判語（登錄 seq3 §九、裁定 seq490）",
         "B 組進場 ＝ A0 ＝ seq1 原版（事件、對照逐字相同，見 repro_seq1.csv），只換出場",
         "A 組各版的去重、閘、對照排除都以本版自己的原始訊號做（★S7、★S8）",
         "n_eff < 24 的版×段照〈四十九〉加註：只描述、樣本不足"]
LOG: list = []
HOLD_BINS = [0, 1, 2, 3, 5, 10, 20, 60, 120, 250, 10 ** 6]


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


G.log = log
RT.log = log


# ═════════════ 登錄與裁定 ═════════════
def reg_verify():
    dirs = [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*")))      # seq2 登錄全文 10/30 已移入 _封存-*（同 IMF.reg_check）
    fs = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if not fs:
        raise SystemExit("⛔ 信箱找不到 seq2 登錄全文")
    b = open(fs[0], "rb").read()
    name = IMF.reg_check(REG_SHA)                                       # 去 pw1 行重算，不符即 SystemExit
    if len(b) != REG_BYTES:
        raise SystemExit(f"⛔ 登錄大小 {len(b)} ≠ {REG_BYTES}")
    rul = [f for f in glob.glob(os.path.join(IMF.MAILBOX, "*.md")) if RULING in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RULING}")
    import hashlib
    whole = hashlib.sha256(b).hexdigest()[:16]
    return {"登錄": name, "bytes": len(b), "整檔sha前16": whole, "整檔相符": whole == REG_SHA, "pw1去戳記相符": True,
            "裁定": os.path.basename(rul[0])}


# ═════════════ 進場版本（單一無壞根段；自測直接呼叫）═════════════
def seg_variants(c, h, l, check=True):
    """回 (V, S, F)：V[(格, 版)] ＝ 各版原始訊號（bool）；S[格] ＝ 停損價（各版同定義）；F ＝ G.seg_features 原輸出（含 X5、MA）。
    A0 與 seq1 G.seg_features 逐位比對（check=True 不符即 raise）。"""
    F = G.seg_features(c, h, l)
    m = len(c); fin = np.isfinite
    MA = F["MA"]
    MA20 = G.shift(MA, G.SLOPE, np.nan)
    mok = fin(MA); slok = mok & fin(MA20)
    up = slok & (MA > MA20)
    down = slok & (MA < MA20)
    above = mok & (c > MA); under = mok & (c <= MA); below = mok & (c < MA)
    V = {}
    # 買1（★S2～S4）
    lt = np.where(mok, below.astype(float), np.nan)
    cnt60 = pd.Series(lt).shift(1).rolling(60, min_periods=60).sum().to_numpy(float)
    J1 = F["J1"]
    dir1 = ~down
    pos1 = fin(cnt60) & (np.nan_to_num(cnt60, nan=-1.0) >= 40)
    trig1 = G.shift(under, 1, False) & above
    V[("買1", "A0")] = J1 & dir1 & pos1 & trig1
    V[("買1", "A1")] = J1 & pos1 & trig1
    V[("買1", "A2")] = J1 & dir1 & trig1
    V[("買1", "A3")] = J1 & trig1
    # 買2
    ra = G.runlen(above); ru = G.runlen(under)
    r = G.shift(ru, 1, 0)
    bpos = np.arange(m) - r
    ra_bm1 = np.where(bpos >= 1, ra[np.clip(bpos - 1, 0, m - 1)], 0)
    trig2 = above & (r >= 1) & (ra_bm1 >= 1)
    pos2 = (r <= 10) & (ra_bm1 >= 20)
    J2 = F["J2"]
    V[("買2", "A0")] = J2 & up & pos2 & trig2
    V[("買2", "A1")] = J2 & pos2 & trig2
    V[("買2", "A2")] = J2 & up & trig2
    V[("買2", "A3")] = J2 & trig2
    S2 = np.full(m, np.nan)
    for k in np.flatnonzero(V[("買2", "A3")]):
        S2[k] = float(np.min(c[bpos[k]:k]))
    # 買3
    trig3 = above & fin(l) & (np.nan_to_num(l, nan=np.inf) <= MA * 1.02)
    pos3 = G.shift(ra, 1, 0) >= 20
    J3 = F["J3"]
    V[("買3", "A0")] = J3 & up & pos3 & trig3
    V[("買3", "A1")] = J3 & pos3 & trig3
    V[("買3", "A2")] = J3 & up & trig3
    V[("買3", "A3")] = J3 & trig3
    S3 = np.where(V[("買3", "A3")], l, np.nan)
    S = {"買1": F["S1"], "買2": S2, "買3": S3}
    if check:
        for cell, bk, sk in (("買1", "B1", "S1"), ("買2", "B2", "S2"), ("買3", "B3", "S3")):
            if not np.array_equal(V[(cell, "A0")], F[bk]):
                raise SystemExit(f"⛔ {cell} A0 ≠ seq1 seg_features")
            q = np.flatnonzero(F[bk])
            if not np.array_equal(S[cell][q], F[sk][q]):
                raise SystemExit(f"⛔ {cell} A0 停損價 ≠ seq1")
    return V, S, F


def stock_variants(c, h, l, bad, check=True):
    """有效 K 棒序列 ⇒ 依壞根切段（G.stock_features 同式）逐段 seg_variants 再接回。回 (V, S, X5, MA)。"""
    n = len(c)
    starts = sorted(set([0] + [int(k) for k in np.flatnonzero(bad) if k > 0]))
    ends = starts[1:] + [n]
    V = None; S = None
    X5 = np.zeros(n, bool); MA = np.full(n, np.nan)
    for a, b in zip(starts, ends):
        v, s, F = seg_variants(c[a:b], h[a:b], l[a:b], check=check)
        if V is None:
            V = {k: np.zeros(n, bool) for k in v}; S = {k: np.full(n, np.nan) for k in s}
        for k in v:
            V[k][a:b] = v[k]
        for k in s:
            S[k][a:b] = s[k]
        X5[a:b] = F["X5"]; MA[a:b] = F["MA"]
    return V, S, X5, MA


# ═════════════ 出場版本（★S9；自測直接呼叫）═════════════
def exit_v(c, o, x5, bad, e, S, cap, cend, lastv, arm):
    """arm：'SX' ＝ seq1 主臂｜'S' 只停損｜'X' 只賣5｜'' 固定抱到上限。以 seq1 exit_sim 實作（不用的臂：停損價 −∞、賣5 全否）。"""
    S_ = S if "S" in arm else -np.inf
    x5_ = x5 if "X" in arm else np.zeros(len(c), bool)
    X = G.exit_sim(c, o, x5_, bad, e, S_, cap, cend, lastv)
    if arm == "" and X["reason"] == "上限250日":
        X = {**X, "reason": "固定250日"}
    return X


def ret_one(C, O, BAD, LASTV, CEND, i, cj, e, x, kind, cost):
    """（正式跑用）訊號筆與對照的報酬（各扣成本）⇒ (訊號, 對照平均)。對照同進同出（seq1 ★15，G.exit_price）。"""
    vals = []
    for j in [i] + list(cj):
        p, _ = G.exit_price(C[j], O[j], BAD[j], e, x, kind, CEND, int(LASTV[j]))
        vals.append(p / O[j, e] - 1.0 - cost if np.isfinite(p) and O[j, e] > 0 else np.nan)
    cv = np.array(vals[1:], float)
    return vals[0], (float(np.nanmean(cv)) if np.isfinite(cv).any() else np.nan)


def desc3(x):
    """§九 每版必報：平均、中位、去掉最大 1 筆（⛔ 不含勝率）。"""
    x = np.asarray(x, float); xs = x[np.isfinite(x)]
    return {"n": int(len(xs)), "mean": float(xs.mean()) if len(xs) else np.nan, "median": float(np.median(xs)) if len(xs) else np.nan,
            "mean_ex_max1": float(np.sort(xs)[:-1].mean()) if len(xs) >= 2 else np.nan}


def bonf_ci(x, months):
    """裁定 seq490：Bonferroni 18 格 CI ＝ seq1 G.cluster_boot（同 NBOOT、SEED、月分群），只換 alpha ＝ 0.05/18（雙尾 99.72%）。"""
    return G.cluster_boot(x, months, alpha=BONF_ALPHA)


def bonf_scope(cell, ver, seg):
    """Bonferroni 18 格的範圍標記：確認段 A1～A3、B1～B3 ＝ 18 格本體；其餘只當參考／描述。"""
    if seg != "確認":
        return "探索段只描述"
    if ver in ("A0", "B0"):
        return "A0／B0 不在 18 格內，只參考"
    return "確認段 18 格之一"


def _ci_text(v, seg, ver):
    sc = bonf_scope("", ver, seg)
    tag = "" if sc == "確認段 18 格之一" else f"（{sc}）"
    return (f"月分群 99% CI [{_p(v.get('lo'))}, {_p(v.get('hi'))}]、{BONF_LAB}{tag} [{_p(v.get('loB'))}, {_p(v.get('hiB'))}]；"
            f"另一讀法 95% CI [{_p(v.get('lo95'))}, {_p(v.get('hi95'))}]")


def _p(x, signed=True):
    if x is None or not np.isfinite(x):
        return "—"
    return f"{x * 100:+.2f}%" if signed else f"{x * 100:.1f}%"


def result_sentence(cell, ver, rows, dry):
    """rows：{段: {n, months, mean, median, mean_ex_max1, lo, hi, 停損先到, 賣5先到, 持有中位}}。乾跑 ⇒ 報酬欄寫「（乾跑不填）」。"""
    P = [f"{cell}｜{ver} {VNAME[ver]}（只描述，不判定、不計 N）"]
    for nm, _, _ in SEGS:
        v = rows.get(nm, {})
        ret = ("超額（訊號−對照，兩邊各扣 0.585%）（乾跑不填）" if dry else
               f"超額（訊號−對照，兩邊各扣 0.585%）平均 {_p(v.get('mean'))}、中位 {_p(v.get('median'))}、去掉最大 1 筆 {_p(v.get('mean_ex_max1'))}"
               f"（{_ci_text(v, nm, ver)}）")
        neff = v.get("months", 0)
        P.append(f"{nm}段 主格 {v.get('n', 0)} 件、n_eff {neff} 月{'（< 24，只描述、樣本不足）' if neff < G.NEFF_MIN else ''}、{ret}、"
                 f"停損先到（含同日）{_p(v.get('停損先到'), False)}、賣 5 先到 {_p(v.get('賣5先到'), False)}、持有中位 {v.get('持有中位', float('nan')):.0f} 日")
    if not dry and ver == "A3" and cell in ("買1", "買2"):
        P.append(A3_LINE)
    s = "；".join(P) + "；" + PHRASE
    guard(s)
    return s


VERDICT_WORDS = ("通過", "測不出", "還沒測", "測到", "顯著", "有效", "成立")


def guard(s):
    """結果句判定措辭擋門（seq1 BANNED＋通過／測不出／還沒測…）；PHRASE_SEQ487 也不可再出現（seq490）。"""
    for w in G.BANNED + VERDICT_WORDS:
        if w in s:
            raise ValueError(f"結果句含不該出現的判定措辭 {w}")
    if PHRASE_SEQ487 in s:
        raise ValueError("結果句仍含 seq487 舊固定句（已由 seq490 更正）")


# ═════════════ 主程式 ═════════════
def run(dry, procs, limit=None):
    t0 = time.time()
    od = (os.path.join(WORK, "dry2") if limit else os.path.join(OUT, "freq")) if dry else os.path.join(OUT, "formal")
    os.makedirs(od, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    REG = reg_verify(); log(f"[登錄] {REG}")
    sha, DN, MD = RT.ensure_data(G.DATA_SHA); log(f"[資料] {sha}｜{DN}")
    PX = RT.prices(sha, DN, procs)
    CAL, SIDS = PX["CAL"], PX["SIDS"]
    N, NC = len(SIDS), len(CAL); CEND = NC - 1
    C, BAD, Gt, MC, VP, LASTV = PX["C"], PX["BAD"], PX["G"], PX["MC"], PX["VP"], PX["LASTV"]
    O, nseam = SM.seam_open(PX)
    PX["O"] = O
    Hs, Ls, hlinfo = G.merged_hl(PX, procs)
    VALID = np.isfinite(C)
    log(f"[高低] {hlinfo}｜開盤接縫 {nseam}｜{time.time() - t0:.0f}s")
    SUB = np.ones(N, bool)
    if limit:
        rr = np.random.default_rng(G.SEED); pick = set(rr.choice(N, limit, replace=False).tolist())
        SUB = np.array([k in pick for k in range(N)])
    # ── 特徵（各版）⇒ 日曆陣列；A0 逐檔對 seq1
    RAW = {(cell, v): np.zeros((N, NC), bool) for cell in BUY for v in AV}
    X5 = np.zeros((N, NC), bool)
    STOP = {cell: {} for cell in BUY}
    for i in range(N):
        if not SUB[i]:
            continue
        vp = VP[i]
        if len(vp) < G.MAW:
            continue
        V, S, x5, _ = stock_variants(C[i, vp], Hs[i, vp], Ls[i, vp], BAD[i, vp])
        for k in V:
            RAW[k][i, vp] = V[k]
        X5[i, vp] = x5
        for cell in BUY:
            for q in np.flatnonzero(V[(cell, "A3")] | V[(cell, "A2")] | V[(cell, "A1")] | V[(cell, "A0")]):
                STOP[cell][(i, int(vp[q]))] = float(S[cell][q])
    log(f"[特徵] A0 逐檔與 seq1 seg_features 相同｜{time.time() - t0:.0f}s")
    # ── 事件（A 組各版；B 組 ＝ A0）
    eflag_memo = {}

    def eflag(i, t):
        k = (i, t)
        if k not in eflag_memo:
            eflag_memo[k] = IMF.entry_flag(PX, i, t, t + 1) if t + 1 <= CEND else "e超出資料尾"
        return eflag_memo[k]
    MKT = TP.market_map(DN)
    EV = {}; EVR = {}
    for cell in BUY:
        for v in AV:
            ii, tt = np.nonzero(RAW[(cell, v)] & SUB[:, None])
            rs = Counter({"原始訊號": int(len(ii))})
            byi = defaultdict(list)
            for i, t in zip(ii.tolist(), tt.tolist()):
                if not Gt[i, t]:
                    rs["閘外G[t]"] += 1; continue
                byi[i].append(t)
            rows = []
            for i in sorted(byi):
                kept, nd = G.dedup(byi[i]); rs["60日內非第一次"] += nd
                for t in kept:
                    d = CAL[t]
                    rows.append({"i": i, "sid": SIDS[i], "t": t, "date": str(d.date()), "段": G.segof(d), "月": G.mkey(d), "年": d.year,
                                 "市場": MKT.get(SIDS[i], "?"), "進場": eflag(i, t)})
            E = pd.DataFrame(rows, columns=["i", "sid", "t", "date", "段", "月", "年", "市場", "進場"])
            E = E.sort_values(["t", "sid"]).reset_index(drop=True)
            E["e"] = E["t"] + 1
            for H in (G.CAP, G.HFIX):
                E[f"走得完{H}"] = (E["e"] + H) <= CEND
            E["走得完"] = E[f"走得完{G.CAP}"]
            rs["事件"] = int(len(E))
            EV[(cell, v)] = E; EVR[f"{cell}|{v}"] = dict(rs)
            log(f"[事件 {cell} {v}] {dict(rs)}")
    # ── r60 向量化（G.run 同式）
    LVP = np.full((N, NC), -1, np.int32)
    for i in range(N):
        a = np.full(NC, -1, np.int64); a[VP[i]] = VP[i]; LVP[i] = np.maximum.accumulate(a)
    AR = np.arange(N); CB = PX["CB"]

    def r60_vec(t):
        p0 = t - 60
        if p0 < 0:
            return np.full(N, np.nan)
        a = LVP[:, p0].astype(np.int64)
        ok = VALID[:, t] & (a >= 0)
        a2 = np.where(ok, a, 0)
        ok &= (CB[:, t] - CB[AR, a2]) == 0
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(ok, C[:, t] / C[AR, a2] - 1.0, np.nan)
    pit = IMF.load_pit(DN)

    def ind_at(j, t):
        v, _ = pit.at(SIDS[j], CAL[t]); return v or ""
    GS = Gt & SUB[:, None]
    UCACHE = {}

    def uday(t):
        if t not in UCACHE:
            U = np.flatnonzero(GS[:, t] & VALID[:, t]) if not limit else np.flatnonzero(Gt[:, t] & VALID[:, t])
            mc = MC[U, t].astype(float); mc[~(mc > 0)] = np.nan
            r6 = r60_vec(t)[U]
            pm = G.deciles(mc); pr = G.deciles(r6)
            dec = np.where(np.isfinite(pm), np.ceil(pm * 10), -1).astype(int)
            ter = np.where(np.isfinite(pr), np.ceil(pr * 3), -1).astype(int)
            UCACHE[t] = (U, dec, ter)
        return UCACHE[t]
    # ── 配對（A 組各版，排除本版原始訊號 ★S8）
    MREASON = {}
    for cell in BUY:
        for v in AV:
            E = EV[(cell, v)]; rng = np.random.default_rng(G.SEED); EX = RAW[(cell, v)]
            res = {}; binfo = {}
            if len(E):
                need = E[(E["進場"] == "保留") & E["走得完"]]
                for t, g in need.groupby("t", sort=True):
                    t = int(t)
                    U, dec, ter = uday(t)
                    out = G.match_day(rng, sorted(g["i"].astype(int).tolist(), key=lambda z: SIDS[z]), U, dec, ter,
                                      lambda j, t=t: bool(EX[j, t]), lambda j, t=t: ind_at(j, t), lambda j, t=t: eflag(j, t) == "保留")
                    for i, vv in out.items():
                        res[(i, t)] = vv
                    posU = {int(j): k for k, j in enumerate(U)}
                    for i in g["i"].astype(int).tolist():
                        k = posU.get(int(i))
                        binfo[(int(i), t)] = (int(dec[k]) if k is not None else -1, ind_at(int(i), t))
            if len(E):
                E["市值十分位"] = [binfo.get((int(i), int(t)), (np.nan, ""))[0] for i, t in zip(E["i"], E["t"])]
                E["產業"] = [binfo.get((int(i), int(t)), (np.nan, ""))[1] for i, t in zip(E["i"], E["t"])]
            E["配對"] = [res.get((int(i), int(t)), ("未配(剔除或走不完)", []))[0] for i, t in zip(E["i"], E["t"])] if len(E) else []
            E["對照"] = [";".join(SIDS[j] for j in res.get((int(i), int(t)), ("", []))[1]) for i, t in zip(E["i"], E["t"])] if len(E) else []
            E["對照數"] = [len(res.get((int(i), int(t)), ("", []))[1]) for i, t in zip(E["i"], E["t"])] if len(E) else []
            E["主格"] = (E["配對"] == "配到") & (E["進場"] == "保留") & E["走得完"] if len(E) else []
            MREASON[f"{cell}|{v}"] = dict(Counter(E["配對"])) if len(E) else {}
            log(f"[配對 {cell} {v}] {MREASON[f'{cell}|{v}']}｜{time.time() - t0:.0f}s")
    # ── 出場（各版；B 組 ＝ A0 事件換出場臂）
    EVX = {}
    for cell in BUY:
        for v in VERS:
            E = EV[(cell, ENTRY[v])].copy()
            xs, kinds, reas, fl, hold, cst = [], [], [], [], [], []
            for r in E.itertuples(index=False):
                if not (r.進場 == "保留" and r.走得完):
                    xs.append(-1); kinds.append(""); reas.append(""); fl.append(""); hold.append(-1); cst.append(""); continue
                i, e = int(r.i), int(r.e)
                S = STOP[cell][(i, int(r.t))]
                X = exit_v(C[i], O[i], X5[i], BAD[i], e, S, e + G.CAP, CEND, int(LASTV[i]), ARM[v])
                xs.append(X["x"]); kinds.append(X["kind"]); reas.append(X["reason"]); fl.append("|".join(X["flags"])); hold.append(X["x"] - e)
                cs = []
                for sj in (r.對照.split(";") if r.對照 else []):
                    j = PX["ix"][sj]
                    if len(np.flatnonzero(BAD[j, e + 1:X["x"] + 1])):
                        cs.append("壞根")
                    elif X["kind"] in ("open", "minoc") and not (VALID[j, X["x"]] and np.isfinite(O[j, X["x"]])):
                        cs.append("出場日無成交")
                    elif X["kind"] == "close" and not VALID[j, X["x"]]:
                        cs.append("出場日無收盤")
                    else:
                        cs.append("ok")
                cst.append(";".join(cs))
            E["出場位"] = xs; E["出場方式"] = kinds; E["出場原因"] = reas; E["旗標"] = fl; E["持有天數"] = hold; E["對照出場狀態"] = cst
            E["出場日"] = [str(CAL[x].date()) if x >= 0 else "" for x in xs]
            EVX[(cell, v)] = E
        log(f"[出場 {cell}] {time.time() - t0:.0f}s")
    # ── 報酬（正式）或 0 佔位（乾跑）⇒ 描述欄
    DESC = {}; SENT_ROWS = {}
    for cell in BUY:
        for v in VERS:
            E = EVX[(cell, v)]
            M = E[E["主格"]]
            XS = []
            for r in M.itertuples(index=False):
                if dry:
                    XS.append(0.0); continue
                cj = [PX["ix"][s] for s in (r.對照.split(";") if r.對照 else [])]
                a, b = ret_one(C, O, BAD, LASTV, CEND, int(r.i), cj, int(r.e), int(r.出場位), r.出場方式, G.COST)
                XS.append(a - b if np.isfinite(a) and np.isfinite(b) else np.nan)
            M = M.assign(X=XS)
            EVX[(cell, v, "M")] = M
            rows = {}
            for nm, _, _ in SEGS:
                q = M[M["段"] == nm]
                d3 = desc3(q["X"]); cb = G.cluster_boot(q["X"].to_numpy(float), q["月"].to_numpy())
                cb95 = G.cluster_boot(q["X"].to_numpy(float), q["月"].to_numpy(), alpha=0.05)   # ★S11 另一讀法（只描述用 95%）
                cbB = bonf_ci(q["X"].to_numpy(float), q["月"].to_numpy())                       # seq490：Bonferroni 18 格
                stp = float(q["出場原因"].str.startswith(("停損先到", "同日兩者")).mean()) if len(q) else np.nan
                s5 = float(q["出場原因"].str.startswith("賣5先到").mean()) if len(q) else np.nan
                hm = float(np.median(q["持有天數"].to_numpy(float))) if len(q) else np.nan
                key = f"{cell}{v}"
                DESC[("拆件描述", key, f"{nm}｜超額(訊號−對照)")] = d3
                DESC[("拆件描述", key, f"{nm}｜超額 月分群99%CI")] = {"n": cb["n"], "mean": cb["mean"], "lo": cb["lo"], "hi": cb["hi"],
                                                                 "lo_bonf18": cbB["lo"], "hi_bonf18": cbB["hi"], "bonf18_scope": bonf_scope(cell, v, nm)}
                DESC[("拆件描述", key, f"{nm}｜超額 月分群95%CI(另一讀法)")] = {"n": cb95["n"], "mean": cb95["mean"], "lo": cb95["lo"], "hi": cb95["hi"]}
                DESC[("拆件描述", key, f"{nm}｜停損先到(含同日)比例")] = {"n": int(len(q)), "share": stp}
                DESC[("拆件描述", key, f"{nm}｜賣5先到比例")] = {"n": int(len(q)), "share": s5}
                DESC[("拆件描述", key, f"{nm}｜持有中位")] = {"n": int(len(q)), "value": hm}
                rows[nm] = {"n": int(len(q)), "months": int(q["月"].nunique()), **{k: d3[k] for k in ("mean", "median", "mean_ex_max1")},
                            "lo": cb["lo"], "hi": cb["hi"], "lo95": cb95["lo"], "hi95": cb95["hi"], "loB": cbB["lo"], "hiB": cbB["hi"],
                            "停損先到": stp, "賣5先到": s5, "持有中位": hm}
            SENT_ROWS[(cell, v)] = rows
    return dict(od=od, REG=REG, sha=sha, PX=PX, RAW=RAW, EV=EV, EVX=EVX, EVR=EVR, MREASON=MREASON, DESC=DESC, SENT_ROWS=SENT_ROWS,
                hlinfo=hlinfo, CAL=CAL, CEND=CEND, t0=t0, SUB=SUB, limit=limit)


# ═════════════ 輸出 ═════════════
KEEP = ["sid", "date", "段", "市場", "進場", "走得完", "配對", "對照數", "對照", "主格", "市值十分位", "產業", "走得完250", "走得完60",
        "出場日", "出場方式", "出場原因", "旗標", "持有天數", "對照出場狀態"]


def events_csv(E):
    """事件檔（seq1 events_買k 同欄同序；⛔ 無報酬）⇒ CSV 文字。"""
    return E[KEEP].to_csv(index=False)


def _read_str(src):
    return pd.read_csv(src, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def repro_seq1(EVX):
    """★S13：A0、B0 事件檔 vs seq1 freq events_買k.csv.gz 逐字。"""
    rows = []
    for cell in BUY:
        ref = _read_str(os.path.join(SEQ1_FREQ, f"events_{cell}.csv.gz"))
        for v in ("A0", "B0"):
            mine = _read_str(io.StringIO(events_csv(EVX[(cell, v)])))
            same_cols = list(ref.columns) == list(mine.columns)
            eq = same_cols and ref.shape == mine.shape and bool((ref.values == mine.values).all())
            ndiff = int((ref.values != mine.values).any(axis=1).sum()) if (same_cols and ref.shape == mine.shape) else -1
            rows.append({"格": cell, "版": v, "seq1事件": len(ref), "本版事件": len(mine), "欄相同": same_cols, "逐字相同": eq, "不同列": ndiff,
                         "主格": int((mine["主格"] == "True").sum())})
    return rows


def overlap_A0(A):
    """★S12：A1～A3 vs A0（原始訊號、事件、主格；只件數）。"""
    out = []
    SUB = A["SUB"]
    for cell in BUY:
        r0 = A["RAW"][(cell, "A0")] & SUB[:, None]
        E0 = A["EV"][(cell, "A0")]
        s0 = set(zip(E0["sid"], E0["date"])); m0 = set(zip(E0.loc[E0["主格"], "sid"], E0.loc[E0["主格"], "date"]))
        for v in AV[1:]:
            rv = A["RAW"][(cell, v)] & SUB[:, None]
            Ev = A["EV"][(cell, v)]
            sv = set(zip(Ev["sid"], Ev["date"])); mv = set(zip(Ev.loc[Ev["主格"], "sid"], Ev.loc[Ev["主格"], "date"]))
            out.append({"格": cell, "版": v, "拿掉": VNAME[v],
                        "A0原始訊號": int(r0.sum()), "本版原始訊號": int(rv.sum()), "A0原始不在本版(應為0)": int((r0 & ~rv).sum()),
                        "本版原始新增": int((rv & ~r0).sum()),
                        "A0事件": len(s0), "本版事件": len(sv), "事件交集": len(s0 & sv), "事件本版新增": len(sv - s0), "事件A0有本版沒有(去重擠掉)": len(s0 - sv),
                        "本版事件中A0比例": (len(s0 & sv) / len(sv)) if sv else None,
                        "A0主格": len(m0), "本版主格": len(mv), "主格交集": len(m0 & mv), "主格本版新增": len(mv - m0), "主格A0有本版沒有": len(m0 - mv)})
    return out


def freq_tables(A):
    rows, reas, holds = [], [], []
    for cell in BUY:
        for v in VERS:
            E = A["EVX"][(cell, v)]
            for nm, _, _ in SEGS + [("段外", "", "")]:
                q = E[E["段"] == nm] if len(E) else E
                row = {"格": cell, "版": v, "組": v[0], "版說明": VNAME[v], "段": nm, "事件(過閘去重)": int(len(q))}
                if not len(q):
                    rows.append(row); continue
                ent = q["進場"] == "保留"; wk = q["走得完"]; base = q[ent & wk]
                main = q[q["主格"]]
                months = int(main["月"].nunique())
                row.update({"進場剔除": dict(Counter(q.loc[~ent, "進場"])), "可進場": int(ent.sum()), "可進場且走得完": int(len(base)),
                            "配到": int((base["配對"] == "配到").sum()), "配對成功率": float((base["配對"] == "配到").mean()) if len(base) else None,
                            "配不到原因": dict(Counter(base.loc[base["配對"] != "配到", "配對"])),
                            "主格事件": int(len(main)), "主格訊號月數(n_eff)": months,
                            "n_eff註": ("" if months >= G.NEFF_MIN or nm == "段外" else "n_eff < 24（〈四十九〉只描述、樣本不足）"),
                            "首個事件日": q["date"].min(), "末個事件日": q["date"].max()})
                n = len(main)
                f = (lambda pre: float(main["出場原因"].str.startswith(pre).mean()) if n else None)
                row.update({"停損先到(含同日)比例": f(("停損先到", "同日兩者")), "停損先到(不含同日)比例": f("停損先到"), "同日兩者比例": f("同日兩者"),
                            "賣5先到比例": f("賣5先到"), "上限250日比例": float((main["出場原因"] == "上限250日").mean()) if n else None,
                            "固定250日比例": float((main["出場原因"] == "固定250日").mean()) if n else None,
                            "壞根前強制出比例": f("壞根前強制出"), "下市末根比例": f("下市末根"),
                            "旗標": dict(Counter(x for s in main["旗標"] for x in s.split("|") if x)),
                            "對照出場狀態": dict(Counter(x for s in main["對照出場狀態"] for x in s.split(";") if x))})
                for k_, v_ in Counter(main["出場原因"]).items():
                    reas.append({"格": cell, "版": v, "段": nm, "出場原因": k_, "件數": int(v_), "比例": v_ / n if n else None})
                hd = main["持有天數"].to_numpy(float)
                if len(hd):
                    row["持有中位"] = float(np.median(hd))
                    hc = np.histogram(hd, bins=HOLD_BINS)[0]
                    holds.append({"格": cell, "版": v, "段": nm, "n": int(len(hd)), "平均": float(hd.mean()), "中位": float(np.median(hd)),
                                  "p10": float(np.percentile(hd, 10)), "p25": float(np.percentile(hd, 25)), "p75": float(np.percentile(hd, 75)),
                                  "p90": float(np.percentile(hd, 90)), "max": float(hd.max()),
                                  **{f"[{HOLD_BINS[k]},{HOLD_BINS[k + 1]})": int(hc[k]) for k in range(len(hc))}})
                rows.append(row)
    return rows, reas, holds


def _js(o):
    if isinstance(o, (np.integer, np.floating, np.bool_)):
        return o.item()
    return str(o)


def write_out(A, formal=False):
    od = A["od"]; EVX = A["EVX"]
    rows, reas, holds = freq_tables(A)
    pd.DataFrame(rows).to_csv(os.path.join(od, "freq_versions.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(reas).to_csv(os.path.join(od, "exit_reasons.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(holds).to_csv(os.path.join(od, "hold_dist.csv"), index=False, encoding="utf-8-sig")
    OV = overlap_A0(A)
    pd.DataFrame(OV).to_csv(os.path.join(od, "overlap_vs_A0.csv"), index=False, encoding="utf-8-sig")
    for cell in BUY:
        for v in VERS:
            with open(os.path.join(od, f"events_{cell}_{v}.csv.gz"), "wb") as fh:
                import gzip
                fh.write(gzip.compress(("﻿" + events_csv(EVX[(cell, v)])).encode("utf-8"), mtime=0))
    RP = []
    if not A["limit"]:
        RP = repro_seq1(EVX)
        pd.DataFrame(RP).to_csv(os.path.join(od, "repro_seq1.csv"), index=False, encoding="utf-8-sig")
        if not all(r["逐字相同"] for r in RP):
            raise SystemExit(f"⛔ A0／B0 未重現 seq1 事件檔：{RP}")
        log(f"[seq1 重現] A0、B0 × 3 格 逐字相同")
    sents = {f"{c}|{v}": result_sentence(c, v, A["SENT_ROWS"][(c, v)], dry=not formal) for c in BUY for v in VERS}
    head = head_lines() if formal else []
    open(os.path.join(od, "result_sentences.txt" if formal else "result_sentence_template.txt"), "w", encoding="utf-8").write(
        "\n\n".join(head + list(sents.values())) + "\n")
    neff = {f"{c}|{v}": {nm: int(EVX[(c, v)][(EVX[(c, v)]["段"] == nm) & EVX[(c, v)]["主格"]]["月"].nunique()) for nm, _, _ in SEGS}
            for c in BUY for v in VERS}
    J = {"登錄": A["REG"], "核可": RULING, "資料": A["sha"], "高低價": A["hlinfo"], "日曆": f"{A['CAL'][0].date()}～{A['CAL'][-1].date()}（{len(A['CAL'])}）",
         "事件剔除": A["EVR"], "配對原因": A["MREASON"], "n_eff": neff, "n_eff<24": [k for k, x in neff.items() if min(x.values()) < G.NEFF_MIN],
         "seq1重現": RP, "與A0重疊": OV, "NOTES": NOTES if not formal else NOTES[1:], "完成": str(pd.Timestamp.now(tz="Asia/Taipei")),
         "耗時秒": int(time.time() - A["t0"])}
    if formal:
        drows = [{"section": s, "cell": c, "stat": st, **{k: v[k] for k in DESC_COLS[3:] if k in v}}
                 for (s, c, st), v in A["DESC"].items()]
        pd.DataFrame(drows, columns=DESC_COLS).to_csv(os.path.join(od, "desc.csv"), index=False, encoding="utf-8-sig")
        mx = []
        for c in BUY:
            for v in VERS:
                M = EVX[(c, v, "M")]
                mx.append(pd.DataFrame({"格": c, "版": v, "sid": M["sid"], "date": M["date"], "段": M["段"], "月": M["月"],
                                        "出場原因": M["出場原因"], "持有天數": M["持有天數"], "超額": M["X"]}))
        import gzip
        with open(os.path.join(od, "main_excess.csv.gz"), "wb") as fh:
            fh.write(gzip.compress(("﻿" + pd.concat(mx).to_csv(index=False)).encode("utf-8"), mtime=0))
        # 買1 A3 vs 買2 A3 重疊（原始訊號、主格；只件數）
        SUB = A["SUB"]
        r1 = A["RAW"][("買1", "A3")] & SUB[:, None]; r2 = A["RAW"][("買2", "A3")] & SUB[:, None]
        m1 = EVX[("買1", "A3", "M")]; m2 = EVX[("買2", "A3", "M")]
        k1 = set(zip(m1["sid"], m1["date"])); k2 = set(zip(m2["sid"], m2["date"]))
        J["買1A3與買2A3重疊"] = {"買1A3原始": int(r1.sum()), "買2A3原始": int(r2.sum()), "原始交集": int((r1 & r2).sum()),
                            "買1A3主格": len(k1), "買2A3主格": len(k2), "主格交集(同檔同日)": len(k1 & k2), "說明": A3_LINE}
        J["核可正式跑"] = FORMAL_RULING_NOTE
        J["照記"] = [SEEN_LINE, A3_LINE]
        J["結果句"] = sents
        J.update(relabel_fields(bonf_table(A["SENT_ROWS"])))
        json.dump(J, open(os.path.join(od, "formal.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_js)
    else:
        ds = G.dry_status(A["DESC"]); ds.to_csv(os.path.join(od, "desc_dryrun_status.csv"), index=False, encoding="utf-8-sig")
        J["描述欄乾跑"] = {"欄數": int(len(ds)), "EMPTY": int((ds["status"] == "EMPTY").sum()) if len(ds) else 0,
                       "EMPTY清單": [f"{a}|{b}" for a, b in zip(ds.loc[ds["status"] == "EMPTY", "cell"], ds.loc[ds["status"] == "EMPTY", "stat"])] if len(ds) else []}
        json.dump(J, open(os.path.join(od, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_js)
    open(os.path.join(od, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] ⇒ {od}｜{J.get('描述欄乾跑', {}).get('欄數')} 欄、EMPTY {J.get('描述欄乾跑', {}).get('EMPTY')}")


# ═════════════ 裁定 seq490／seq492：標籤更正＋Bonferroni 18 格 CI（⛔ 不重跑、數字不變）═════════════
DESC_COLS = ["section", "cell", "stat", "n", "mean", "median", "mean_ex_max1", "lo", "hi", "share", "value",
             "lo_bonf18", "hi_bonf18", "bonf18_scope"]          # 前 11 欄 ＝ b5bc39f2cd 版 desc.csv，新欄只接在後面
FORMAL_FILES = ("formal.json", "desc.csv", "result_sentences.txt", "main_excess.csv.gz")


def head_lines():
    """result_sentences.txt 開頭照記（每行都附固定句）；★ 註一行（seq490）。"""
    out = [f"{x}；{PHRASE}" for x in (SEEN_LINE, A3_LINE, STAR_LINE, NO_VERDICT_LINE, BONF_LINE)]
    for s in out:
        guard(s)
    return out


def reg3_verify():
    """登錄 seq3（9973 B；pw1 去戳記 sha256 前 16 ＝ 1fc4dda730b513ac）＋裁定 seq490、seq492 在信箱。"""
    name = IMF.reg_check(REG3_SHA)
    b = open(os.path.join(IMF.MAILBOX, name), "rb").read()
    if len(b) != REG3_BYTES:
        raise SystemExit(f"⛔ 登錄 seq3 大小 {len(b)} ≠ {REG3_BYTES}")
    rul = {}
    for r in RELABEL_RULINGS:
        fs = [os.path.basename(f) for f in glob.glob(os.path.join(IMF.MAILBOX, "*.md")) if r in os.path.basename(f) and "裁定線" in os.path.basename(f)]
        if not fs:
            raise SystemExit(f"⛔ 信箱找不到裁定 {r}")
        rul[r] = fs[0]
    return {"登錄seq3": name, "bytes": len(b), "pw1去戳記sha前16": REG3_SHA, "相符": True, "裁定": rul}


def bonf_table(SENT_ROWS):
    """每格 × 版 × 段：99% 與 Bonferroni 18 格 CI 並列（⛔ 不只列 99%）。"""
    T = {}
    for (c, v), rows in SENT_ROWS.items():
        T[f"{c}|{v}"] = {}
        for nm, _, _ in SEGS:
            r = rows[nm]
            T[f"{c}|{v}"][nm] = {"範圍": bonf_scope(c, v, nm), "主格": r["n"], "n_eff": r["months"], "超額平均": r["mean"],
                                 "99%CI": [r["lo"], r["hi"]], "Bonferroni18格99.72%CI": [r["loB"], r["hiB"]],
                                 "99%下緣>0": bool(r["lo"] > 0), "99.72%下緣>0": bool(r["loB"] > 0),
                                 "99%上緣<0": bool(r["hi"] < 0), "99.72%上緣<0": bool(r["hiB"] < 0)}
    return T


def relabel_fields(bt, reg3=None):
    return {"沿革": RELABEL_NOTE, "標籤裁定": list(RELABEL_RULINGS), "登錄seq3": reg3 if reg3 is not None else reg3_verify(),
            "固定句": PHRASE, "固定句(seq487舊，已更正)": PHRASE_SEQ487, "判定與N": NO_VERDICT_LINE, "★註": STAR_LINE, "多重比較": BONF_LINE,
            "Bonferroni18格CI": {"方法": "seq1 G.cluster_boot 月分群 bootstrap（同 99% CI），只換 alpha", "alpha": BONF_ALPHA,
                                 "信賴水準": 1 - BONF_ALPHA, "nboot": G.NBOOT, "seed": G.SEED,
                                 "18格(確認段)": [f"{c}|{v}" for c, v in BONF_CELLS], "表": bt}}


def _git_show(path):
    import subprocess
    return subprocess.run(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=os.path.expanduser("~/tw-p17"), capture_output=True, check=True).stdout


def _fx(s):
    return float(s) if s != "" else np.nan


def _same(a, b):
    return (np.isnan(a) and np.isnan(b)) or a == b


def _r(x):
    return repr(float(x)) if np.isfinite(x) else ""


def relabel():
    """⛔ 不重跑：以 b5bc39f2cd 的 formal/ 輸出為準（git show），只改標籤、補 Bonferroni 18 格 CI；既有數字逐位元自驗，不符即停。"""
    import re
    od = os.path.join(OUT, "formal")
    reg3 = reg3_verify(); log(f"[登錄 seq3] {reg3}")
    base = {f: _git_show(f"{od}/{f}") for f in FORMAL_FILES}
    J = json.loads(base["formal.json"].decode("utf-8"))
    D = pd.read_csv(io.BytesIO(base["desc.csv"]), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    MX = pd.read_csv(io.BytesIO(base["main_excess.csv.gz"]), compression="gzip", dtype={"sid": str, "月": "int64"}, encoding="utf-8-sig",
                     keep_default_na=False, na_values=[""], float_precision="round_trip")
    if list(D.columns) != DESC_COLS[:11]:
        raise SystemExit(f"⛔ 基準 desc.csv 欄位不符 {list(D.columns)}")
    Dk = {(r.cell, r.stat): r for r in D.itertuples(index=False)}
    SENT_ROWS = {}; nchk = 0
    for c in BUY:
        for v in VERS:
            M = MX[(MX["格"] == c) & (MX["版"] == v)]
            rows = {}
            for nm, _, _ in SEGS:
                q = M[M["段"] == nm]
                x = q["超額"].to_numpy(float); mo = q["月"].to_numpy()
                d3 = desc3(x); cb = G.cluster_boot(x, mo); cb95 = G.cluster_boot(x, mo, alpha=0.05); cbB = bonf_ci(x, mo)
                key = f"{c}{v}"
                r0 = Dk[(key, f"{nm}｜超額(訊號−對照)")]; r1 = Dk[(key, f"{nm}｜超額 月分群99%CI")]
                r2 = Dk[(key, f"{nm}｜超額 月分群95%CI(另一讀法)")]
                rs = Dk[(key, f"{nm}｜停損先到(含同日)比例")]; r5 = Dk[(key, f"{nm}｜賣5先到比例")]; rh = Dk[(key, f"{nm}｜持有中位")]
                pairs = [(d3["n"], int(r0.n)), (d3["mean"], _fx(r0.mean)), (d3["median"], _fx(r0.median)), (d3["mean_ex_max1"], _fx(r0.mean_ex_max1)),
                         (cb["n"], int(r1.n)), (cb["mean"], _fx(r1.mean)), (cb["lo"], _fx(r1.lo)), (cb["hi"], _fx(r1.hi)),
                         (cb95["lo"], _fx(r2.lo)), (cb95["hi"], _fx(r2.hi)), (len(q), int(rs.n)),
                         (int(q["月"].nunique()), int(J["n_eff"][f"{c}|{v}"][nm]))]
                bad = [k for k, (a, b) in enumerate(pairs) if not _same(float(a), float(b))]
                if bad:
                    raise SystemExit(f"⛔ {c} {v} {nm} 由 main_excess 重算 ≠ 基準 desc.csv（第 {bad} 項）：數字不能變，停")
                nchk += len(pairs)
                rows[nm] = {"n": len(q), "months": int(q["月"].nunique()), **{k: d3[k] for k in ("mean", "median", "mean_ex_max1")},
                            "lo": cb["lo"], "hi": cb["hi"], "lo95": cb95["lo"], "hi95": cb95["hi"], "loB": cbB["lo"], "hiB": cbB["hi"],
                            "停損先到": _fx(rs.share), "賣5先到": _fx(r5.share), "持有中位": _fx(rh.value)}
            SENT_ROWS[(c, v)] = rows
    log(f"[自驗] main_excess 重算 平均／中位／去最大／99% CI／95% CI／件數／n_eff ＝ 基準 desc.csv、formal.json：{nchk} 項逐位元相同")
    # 結果句：去掉新 CI 片段、換回舊固定句 ⇒ 必須逐字等於基準結果句
    sents = {f"{c}|{v}": result_sentence(c, v, SENT_ROWS[(c, v)], dry=False) for c in BUY for v in VERS}
    strip = re.compile("、" + re.escape(BONF_LAB) + r"(（[^）]*）)? \[[^\]]*\]")
    for k, s in sents.items():
        back = strip.sub("", s).replace("；" + PHRASE, "；" + PHRASE_SEQ487 + "。")
        if back != J["結果句"][k]:
            raise SystemExit(f"⛔ {k} 結果句除標籤與新 CI 外與基準不同，停")
    log("[自驗] 24 句結果句：去掉 Bonferroni 片段、換回舊固定句 ⇒ 與基準逐字相同")
    # desc.csv：舊 11 欄原字串不動，新 3 欄只填在 99%CI 列
    D2 = D.copy()
    lo, hi, sc = [], [], []
    for r in D.itertuples(index=False):
        if r.stat.endswith("｜超額 月分群99%CI"):
            c, v, nm = r.cell[:2], r.cell[2:], r.stat.split("｜")[0]
            rr = SENT_ROWS[(c, v)][nm]
            lo.append(_r(rr["loB"])); hi.append(_r(rr["hiB"])); sc.append(bonf_scope(c, v, nm))
        else:
            lo.append(""); hi.append(""); sc.append("")
    D2["lo_bonf18"] = lo; D2["hi_bonf18"] = hi; D2["bonf18_scope"] = sc
    D2.to_csv(os.path.join(od, "desc.csv"), index=False, encoding="utf-8-sig")
    # formal.json：NOTES 舊固定句那條換新、結果句換新，其餘鍵值原樣；加沿革與 CI 表
    J["NOTES"] = [NOTES[1] if PHRASE_SEQ487 in x else x for x in J["NOTES"]]
    J["結果句"] = sents
    J.update(relabel_fields(bonf_table(SENT_ROWS), reg3))
    J["標籤更正完成"] = str(pd.Timestamp.now(tz="Asia/Taipei"))
    json.dump(J, open(os.path.join(od, "formal.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_js)
    open(os.path.join(od, "result_sentences.txt"), "w", encoding="utf-8").write("\n\n".join(head_lines() + list(sents.values())) + "\n")
    for c, v in BONF_CELLS + [(c, v) for c in BUY for v in ("A0", "B0")]:
        r = SENT_ROWS[(c, v)]["確認"]
        log(f"[確認段 {c} {v}] 平均 {_p(r['mean'])}｜99% [{_p(r['lo'])}, {_p(r['hi'])}]｜99.72% [{_p(r['loB'])}, {_p(r['hiB'])}]"
            f"｜{bonf_scope(c, v, '確認')}")
    log(f"[完成] 標籤更正 ⇒ {od}（events、main_excess、run.log 等未動）")


def gate(argv):
    """→ ('dry', procs, limit) | ('formal', procs, None) | ('relabel',) | ('refuse', 訊息)。
    正式跑只認 --formal --ruling seq487；標籤更正只認 --relabel --ruling seq490（不帶其他旗標）。"""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--formal", action="store_true")
    ap.add_argument("--relabel", action="store_true")
    ap.add_argument("--ruling", default=None); ap.add_argument("--procs", type=int, default=None); ap.add_argument("--limit", type=int, default=None)
    try:
        a, rest = ap.parse_known_args(argv)
    except SystemExit:
        return ("refuse", "⛔ 參數錯；拒跑")
    if rest:
        return ("refuse", f"⛔ 不認得的參數 {rest}；拒跑")
    if a.relabel:
        if a.formal or a.dry or a.limit or a.procs is not None:
            return ("refuse", "⛔ --relabel 不可與 --formal／--dry／--limit／--procs 同給；拒跑")
        if a.ruling != RELABEL_RULING:
            return ("refuse", f"⛔ 標籤更正須 --relabel --ruling {RELABEL_RULING}；拒跑")
        return ("relabel",)
    a.procs = 3 if a.procs is None else a.procs
    if a.formal and a.dry:
        return ("refuse", "⛔ --formal 與 --dry 不可同時給；拒跑")
    if a.formal:
        if a.ruling != RULING:
            return ("refuse", f"⛔ 正式跑須 --formal --ruling {RULING}（裁定 seq487 §二：先交頻率表、核後再跑）；拒跑")
        if a.limit:
            return ("refuse", "⛔ 正式跑不可 --limit；拒跑")
        return ("formal", a.procs, None)
    if a.dry:
        if a.ruling:
            return ("refuse", "⛔ --dry 不收 --ruling；拒跑")
        return ("dry", a.procs, a.limit)
    return ("refuse", f"用法：--dry ｜ --formal --ruling {RULING} ｜ --relabel --ruling {RELABEL_RULING}；拒跑")


def main():
    m = gate(sys.argv[1:])
    if m[0] == "refuse":
        sys.exit(m[1])
    if m[0] == "relabel":
        relabel(); return
    A = run(dry=(m[0] == "dry"), procs=m[1], limit=m[2])
    write_out(A, formal=(m[0] == "formal"))


if __name__ == "__main__":
    main()

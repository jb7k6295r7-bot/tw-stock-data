# -*- coding: utf-8 -*-
"""USREG-A3 g1 組（事件層四件）：A3-1 月線 3 日站回（H1 分類器讀法）、A3-2 144／200MA 雙翻揚（H2）、A3-4 上升趨勢線跌破（個股層）、
A3-8 週線訊號單測（S1～S4 × k{4,8,12,26} 週；只做甲件）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_g1 --run [--procs 2] [--limit 60] [--only A3-1,A3-2]
    ...                                                                                         --check

判準：美股登錄 USREG-A3A4 seq1（0dc16d3267725d7c）＋seq2（bc0927fed5996fd4）；裁定 seq318（發號）、seq319（Q1 早年段、Q3 週線 k 週各自判）、seq316（兩母體）。
開跑前清單（⛔ 照它、不改）：backtest/researchUSA34_prep.py（px_one 的 A3-1／A3-2／A3-4／A3-8 偵測段、keep_first、roll_mean）、PREP_REPORT.md P1～P20。
共用底座：backtest/researchUSA3_core.py（C1～C10）。台股原登錄與原程式：
  A3-1 PREREGH1 seq2（a2d23aa8f7dc400c）＋ backtest/researchH1.py（Q1～Q8）
  A3-2 PREREGH2 seq2（239b4fac2cd6b856）＋ backtest/researchH2.py（R1～R10）
  A3-4 上升趨勢線跌破 個股層 seq1（ffac12dee65c6bf1）＋ backtest/researchUT.py（V1～V10）、trendline_ut.py、researchRev.up_line_events
  A3-8 週線兩件 seq1（3c7ad365dc7a2f33）甲件 ＋ backtest/researchWeekly.py（W1～W3、S1～S4、A1～A11）；乙件（營量週收盤出場）不搬

⛔⛔ 私有資料：resultsUSA34/A3/ 只放彙總；逐筆事件寫 ~/us_work/a3/g1/（repo 外）並列 sha。

═══ g1 補讀法（執行者寫死於 2026-10-07 12:10（台北）；寫死前 ⛔ 沒看任何 A3 報酬）═══
 共同
 G1 窗 ＝ 2016-01-04～2026-09-30（C1）。A3-1／A3-2／A3-4 原登錄沒有探索／確認兩段 ⇒ 全窗判；A3-8 原登錄有探索／確認／早年三段 ⇒
    確認段判（seq319 Q1：原文「確認＋早年同向」只看確認段；甲件 16 格各自判、不挑格 ⇒ 探索段只描述），結果句標「缺早年段」。
 G2 三欄 ＝ 事件日當天歸屬（只 S&P 400 ＝ m400、只 S&P 500 ＝ 其餘、合併 ＝ 全部；C3）；合併窗、剔除、狀態在聯集實體上算一次，三欄只是切開來看（A2 A1）。
    基準／對照池一律取【合併】母體（PREP_REPORT §二：gate3 → 合併母體）；三欄各下一次原登錄的結果字樣，標籤照 C4。
 G3 成交：T＋1（或原文的進場日）沒有有效 K 棒或開盤 ≤0 ⇒ 不成交剔除（P4，取代「開盤漲停／停牌」）；硬斷點 ＝ 轉接層 hard_break＋缺 K 棒（MB.Stk.brk，P5）。
 G4 成本：美股 0.05% 來回（seq242）；A3-1／A3-2／A3-4 的判定量是兩組差或超額，成本相消；A3-8 成本帶用 0.05%（原 0.585% 是台股成本）。
 G5 原登錄沒有組合層、沒有條件出場臂 ⇒ 卡片「條件出場必報」＝ null；固定 {20,60,120,240} 日組合層描述不做（事件件，C6 的組合層描述不適用）。
 G6 |ret|＞50% 敏感度（C8）：事件（或訊號持有期）的斷點範圍碰到 S&P 400 未確認列 ⇒ 剔除；基準同時改成「跨到未確認列的股票不進」版。
 A3-1（H1）
 H1a 事件偵測照 prep px_one「A3-1」段逐字（i ≥ 25、上揚 k＝5、首次跌破；T ∈ [窗首, 窗尾 −（3＋H）]；T 當天在母體）；狀態順序 ＝ 合併（被保留事件 t0 的 (t0, t0＋3＋H]）
     ⇒ 事前斷點 [t0−24, t0] ⇒ 無法分組（t0＋1～t0＋3 任一天無有效 K 棒）⇒ 未來窗斷點 [t0＋1, t0＋3＋H]（逐組）⇒ t0＋4 不成交（逐組）⇒ 保留；被剔除者不開合併窗（H1 Q3）。
 H1b 判定量照原文：R ＝ 收盤(t0＋23)（ffill：下市者最後成交價）÷ 開盤(t0＋4) − 1；X ＝ R − 同段合併母體等權
     （USX.ew_close：d＝t0＋4 在合併母體∧有效∧開盤＞0、(d, d＋19] 無 hard_break 的股票 收盤(≤d＋19)÷開盤(d) − 1，H1 Q4 同式）。
     D ＝ X 對「站回」虛擬變數迴歸係數（＝ 兩組平均差）、SE 以 t0 曆月分群 CR0；非重疊 SE 以窗首切的 20 日區段分群；
     n_eff ＝ min（未站回組事件數，有未站回事件的 20 日區段數）；＜30 或未站回 ＜30 ⇒ 出口①；30～99 出口②；≥100 出口③。通過 ＝ 結果②（D＞0）。
 H1c 描述：H＝60／120／240（P0＝開盤(t0＋4)、終點收盤(t0＋3＋H)、合併窗與未來窗同延長、區段長 H；H1 Q6 推廣）、描述臂 a（從 t0 起算）、g（原始報酬）、
     ④ 分組窗機械差、站回率、⑧ 未來窗排除逐組比例（＞2 倍加警語）。描述臂 b（k）、c（期限 2／5 天）、e（進場讀法）、f（SMA10／60）本批不重跑（A2 A6 先例）。
 H1d 假訊號臂：t0 曆月內打亂站回標籤 30 次（種子 20260925＋r），每欄各自打亂；x ≥ 5 ⇒ 句前警語、⛔ 不改判定。
 A3-2（H2）
 H2a 訊號照 prep px_one「A3-2」段（i ≥ 205、MA144／MA200 上揚 k＝5、首次站上 max）；資格（t 日可知）＝ 有效 K 棒∧在合併母體∧該股有效 K 棒數 ≥200∧
     日曆 [t−199, t] 無硬斷點∧vol60 可算（H2 R4 前半；⚠ prep 用「往前第 199 根有效 K 棒」當斷點起點，本件照原文用日曆 t−199，差異只在缺 K 棒處）。
 H2b 狀態（H2 R5）：t 不在母體 ⇒ 不是事件；(t0, t0＋20] ⇒ 合併掉；資格不符 ⇒ 剔除；未來窗 [t＋1, t＋20] 斷點 ⇒ 剔除；t＋1 不成交 ⇒ 剔除；被剔除者不開合併窗。
 H2c hit ＝ max(還原高 t＋1…t＋20) ≥ 1.3 × 開盤(t＋1)（相對容差 1e-12，H2 ge13）；對照 ＝ t 日合併母體資格股、t 日無原始訊號、同 vol60 五分位（資格母體內 rank(first) 切 5）、
     抽 10 檔不放回（種子 20260925，事件依 (t, 代號) 排序後依序抽；池依代號排序）；對照不成交／未來窗斷點 ⇒ 該抽剔除、⛔ 不補抽。
     d_e ＝ hit − 對照 hit 平均；D 月分群 CI；n_eff ＝ min(事件數, 有事件的 20 日區段數)；訊號或對照達成筆數 ＜30 ⇒ 出口①。通過 ＝ 結果②。
 H2d 假訊號臂：每事件從自己的對照池另抽 1 檔（排除已抽到的對照）當訊號、重抽 10 檔對照（種子 20260925＋r），30 次；假訊號依抽中股當天屬哪個指數歸欄。
 H2e 描述：H＝60／120／240（各自偵測合併、對照、區段長 H）、d 原說法字面（×1.3 × min(MA)）、e 只對日期不對波動、g 20 日報酬差、② 白拿段 r、⑧ 排除比例；f 滾動續抱不重跑。
 A3-4（上升趨勢線跌破）
 UTa 18 格偵測 ＝ trendline_ut.detect_calendar（甲乙丙 × R{3,5,10} × {1%穿越, 3日3%}；丙三個 R 相同）；主格（甲 R5 1%）另與 prep 的 researchRev.up_line_events 逐筆核對（不同數照報）。
 UTb 狀態（UT V2 ＋ USM R1）：T ∈ [窗首, 窗尾−21]、T 當天在母體且有效（否則不是事件、不開合併窗）；合併 20 日 ⇒ 硬斷點 [最早取點, T＋21] ⇒ T＋1 不成交 ⇒ 保留；被剔除者不開合併窗。
     ⚠ prep 用 keep_first(H＝20)；本件照原登錄（UT V2／USM R3）斷點到 T＋21（出場價在 T＋21）。
 UTc 量：g ＝ px(T＋21)÷開盤(T＋1) − 1；X ＝ g − EW_20(T＋1)（core.ew_bench 合併，MB.ew_us 原式；成本相消）；researchM.summ／verdict；區段上限 ⌈(窗尾−21−窗首＋1)/20⌉。
 UTd ⭐ 本件是賣出訊號讀法：原登錄「顯著為負才算跌破後真的會跌」⇒ 本件的「通過」＝ 結果③（測得出（−））；C4 標籤照此：合併與只 S&P 400 都結果③ ⇒ 合格；只合併 ⇒ 事後擴母體；否則不合格。
 UTe 描述：其餘 17 格（只報數、⛔ 不判）、60／120／240 日（A2 A3：T＋1＋H ≤ 窗尾、斷點延伸到 T＋1＋H、區段長 H）、控制組（主格；同 T、合併母體、近 60 根有效 K 棒報酬＞0、
     當日無原始主格跌破、T＋1 可成交、[T, T＋21] 無斷點、非事件股；d ＝ 事件毛報酬 − 控制等權）、放棄組（主格事件依確認根乙 R5 選取結果分組）。
 UTf 假訊號臂（UT V8／USM B4）：每檔抽數 ＝ 該檔主格保留真事件數；可抽日 ＝ T ∈ [窗首, 窗尾−21]、當天在母體且有效、排除「存在真事件 T_r ∈ [t−20, t]」；
     不放回、不合併；斷點 [t, t＋21] → T＋1 不成交 剔除；種子 default_rng([20260925＋r, crc32(代號)])；依抽中日當天屬哪個指數歸欄；主格結果③ 且假訊號（−）≥2／30 ⇒ 警語。
 A3-8（週線）
 WKa 週 K ＝ researchWeekly.weekly_bars（日曆週、週一起算）；訊號 ＝ researchWeekly.signals；照 prep px_one「A3-8」段：週序位置 ≥35（P14 暖機）、
     hard_break 所在週與前後各 1 週不產生訊號、同檔同訊號 8 週內只算第一次（不在窗或不在母體的不開合併窗）、訊號日 ＝ 該週最後一根有效 K 棒、在窗內且在母體。
 WKb R_k ＝ 收盤 ffill(第 w＋k 週最後一個交易日) ÷ 開盤(第 w＋1 週第一個交易日) − 1；剔除：出場日 ＞ 窗尾（P14「k 週後仍在窗內」取出場日字面）、
     進場日無有效 K 棒或開盤 ≤0、[訊號週第一天, 出場日] 有硬斷點（MB.Stk.brk；下市後以最後收盤計）。
 WKc 母體股週 ＝ 該股該週有週 K 且該週最後一根有效 K 棒那天在合併母體；基準① ＝ 同週母體其他股 R_k 等權；基準②（主）＝ 同週母體依前 4 週報酬
     （收盤 ffill[週末日] ÷ 4 週前 − 1）分十分位（avgdown.deciles）、同十分位其他股等權；同週有效股 ＜20 ⇒ 該週不算（researchWeekly A5 同）。
 WKd 段 ＝ 訊號週的日曆週末日：≤ 2021-12-31 探索、2022-01-03～2026-09-30 確認；曆月分群用同一日；n_eff ＝ min(筆數, 段內 k 週區段數)；
     ＜30 出口①（依構造不可判定）、30～99 ②、≥100 ③；Bonferroni α ＝ 0.05／k（k ＝ 該段、該欄基準② 可判定格數）；
     成本帶：Bonferroni CI 下緣 − 0.05% ＞ 0 ⇒ 測得出（＋）；上緣 ＋ 0.05% ＜ 0 ⇒ 測得出（−）；否則測不出。
 WKe 假訊號：同股、同段、基準② 可算的隨機週 30 次（均勻、可重複；rng default_rng([20260928, 訊號序, k, 段序, 欄序])），合併 30 次同一套判 ⇒「過」＝ 測得出（＋）。
 WKf 每格每欄「通過」＝ 確認段基準② 測得出（＋）且確認段假訊號臂不過（原「早年同向」拿掉，seq319 Q1）；格標籤：合併確認段出口① ⇒ 不可判定（依構造）；
     合併與只 S&P 400 都通過 ⇒ 合格；只合併通過 ⇒ 事後擴母體；否則不合格。N ＝ 16（seq319 Q3、清單）。
     ⚠ 清單的「n_eff（月）」是全窗曆月數上限；原程式 researchWeekly A6 用「段內 k 週區段數」⇒ 本件照原程式（k12、k26 在確認段依構造最多 21、10 個區段 ⇒ 出口①）。
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_core as K          # ⚠ 先 import core（內含 A2.install 順序）
from backtest import researchUSA34_prep as P          # 只用 keep_first 以外的小工具：roll_mean（偵測段逐字照搬）
from backtest import researchWeekly as RW
from backtest import trendline_ut as UTL
from backtest import researchUSX as USX
from backtest import researchUSM_body as MB
from backtest import avgdown as AV
from backtest import research11 as R11
import researchRev as RV
import researchM as TWM

READ_TS = "2026-10-07 12:10（台北）"
GW = os.path.join(K.WORK, "g1")
OUT = K.OUT
SEED, REPS, M_CTRL = 20260925, 30, 10
HD = (60, 120, 240)
COLS = K.COLS
TWREG = {
    "A3-1": "登錄全文-PREREGH1_月線3日站回_台股策略線_seq2_shaa2d23aa8f7dc400c-13738B-20260925-0121.md（a2d23aa8f7dc400c）",
    "A3-2": "登錄全文-PREREGH2_144與200MA雙翻揚_台股策略線_seq2_sha239b4fac2cd6b856-15401B-20260925-0117.md（239b4fac2cd6b856）",
    "A3-4": "登錄全文-上升趨勢線跌破_個股層_登錄_台股策略線_seq1_shaffac12dee65c6bf1-2944B-20260927-1238.md（ffac12dee65c6bf1）",
    "A3-8": "登錄全文-週線兩件_週線訊號單測與營量週收盤出場_登錄_台股策略線_seq1_sha3c7ad365dc7a2f33-5007B-20260928-2230.md（3c7ad365dc7a2f33；只甲件）",
}
_W: dict = {}


# ═════════════ 共用 ═════════════
def setup(lim=None):
    meta, ST = K.load_cache(lim)
    cal = meta["cal"]; w0, w1, sp, c0 = meta["w0"], meta["w1"], meta["sp"], meta["c0"]
    sids = sorted(ST)
    SK = {s: K.stk(ST[s], w0, w1) for s in sids}
    _W.update(ST=ST, SK=SK, cal=cal, w0=w0, w1=w1, sp=sp, c0=c0, n=len(cal), sids=sids, meta=meta)
    return meta, ST, SK, sids


def pmap(fn, items, procs):
    if procs <= 1:
        return [fn(x) for x in items]
    with Pool(procs) as pool:
        return list(pool.imap(fn, items, chunksize=8))


def mats(sids):
    ST = _W["ST"]
    O = np.column_stack([ST[s]["O"] for s in sids])
    V = np.column_stack([ST[s]["valid"] for s in sids])
    okO = V & (np.nan_to_num(O) > 0)
    CFF = np.column_stack([ST[s]["closes"] for s in sids])
    MEM = np.column_stack([ST[s]["member"] for s in sids])
    PB = np.column_stack([ST[s]["pb"] for s in sids])
    F50 = np.column_stack([ST[s]["f50"] for s in sids])
    return {"O": O, "okO": okO, "CFF": CFF, "MEM": MEM, "CSPB": np.cumsum(PB.astype(np.int64), axis=0),
            "CSF": np.cumsum((PB | F50).astype(np.int64), axis=0)}


def mon_of(T):
    cal = _W["cal"]
    return np.array([str(cal[int(t)])[:7] for t in T])


def gm(idx, g):
    return K.gmask(idx, g)


def f6(x):
    return None if x is None or not np.isfinite(x) else round(float(x), 6)


def pctf(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


def ppf(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}pp".format(x * 100, d)


def write_work(name, df):
    os.makedirs(GW, exist_ok=True)
    p = os.path.join(GW, name)
    df.to_csv(p, index=False, compression="gzip", float_format="%.12g")
    return {"檔": "~/us_work/a3/g1/" + name, "sha256": K.sha256f(p), "列數": int(len(df))}


def creg(y, g, cl):
    """y ＝ α ＋ β g；β 與分群 SE（CR0；H1 cluster_reg 同式）。"""
    X = np.column_stack([np.ones(len(y)), g.astype(float)])
    XtX_inv = np.linalg.inv(X.T @ X); b = XtX_inv @ X.T @ y; u = y - X @ b
    meat = np.zeros((2, 2))
    for c_ in np.unique(cl):
        m_ = cl == c_; s_ = X[m_].T @ u[m_]; meat += np.outer(s_, s_)
    V = XtX_inv @ meat @ XtX_inv
    return float(b[1]), float(np.sqrt(V[1, 1]))


def cut(s, keys=("n", "平均", "中位", "lo", "hi", "n_eff", "區段數", "曆月數", "出口", "結果")):
    return {k: (f6(s[k]) if isinstance(s.get(k), (float, np.floating)) else s.get(k)) for k in keys if k in s}


# ═════════════════════════ A3-1 H1 ═════════════════════════
def h1_events(d, S, w0, w1, Hh, dl=3):
    C, bars, valid, member, m4, f50 = d["C"], d["bars"], d["valid"], d["member"], d["m4"], d["f50"]
    n = len(C); end = dl + Hh
    cb = C[bars]; sma = P.roll_mean(cb, 20)
    smac = np.full(n, np.nan); smac[bars] = sma
    acc = Counter(); rows = []; kept = -10 ** 9
    for i in range(25, len(bars)):
        if not (sma[i] > sma[i - 5] and cb[i] < sma[i] and cb[i - 1] >= sma[i - 1]):
            continue
        T = int(bars[i])
        if not (w0 <= T <= w1 - end):
            continue
        if not (member[T] and valid[T]):
            continue
        gi = "400" if m4[T] else "500"
        acc[(gi, "原始")] += 1
        if T <= kept + end:
            acc[(gi, "合併掉")] += 1; continue
        if S.brk(T - 24, T):
            acc[(gi, "剔除_事前硬斷點")] += 1; continue
        if not valid[T + 1:T + dl + 1].all():
            acc[(gi, "無法分組")] += 1; continue
        back = [s_ for s_ in range(1, dl + 1) if C[T + s_] >= smac[T + s_]]
        g = "站回" if back else "未站回"
        e = T + dl + 1
        if S.brk(T + 1, T + end):
            acc[(gi, g + "_未來窗斷點")] += 1; continue
        if not S.okO[e]:
            acc[(gi, g + "_不成交")] += 1; continue
        cE = d["closes"][T + end]
        rows.append((T, gi, int(bool(back)), back[0] if back else 0, e, cE / d["O"][e] - 1.0, cE / C[T] - 1.0,
                     C[T + dl] / C[T] - 1.0, bool(f50[T - 24:T + end + 1].any())))
        kept = T
        acc[(gi, "保留_" + g)] += 1
    return rows, acc


def w_h1(s):
    d = _W["ST"][s]; S = _W["SK"][s]
    return s, {Hh: h1_events(d, S, _W["w0"], _W["w1"], Hh) for Hh in (20,) + HD}


def h1_judge(E, Hh, col="X"):
    w0 = _W["w0"]
    if len(E) == 0 or E["站回"].nunique() < 2:
        return {"n": int(len(E)), "出口": "出口①", "結果": "—（出口①：樣本不足以分辨）"}
    y = E[col].to_numpy(float); g = E["站回"].to_numpy()
    mon = mon_of(E["T"]); blk = ((E["T"] - w0) // Hh).to_numpy()
    b, se = creg(y, g, mon); _, se2 = creg(y, g, blk)
    nb = E[E["站回"] == 0]; n0 = len(nb); nblk0 = int(((nb["T"] - w0) // Hh).nunique())
    n_eff = min(n0, nblk0)
    out = {"n": int(len(E)), "D": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "se_月": se, "曆月數": int(len(np.unique(mon))),
           "lo_非重疊": b - 1.96 * se2, "hi_非重疊": b + 1.96 * se2, "n_站回": int(g.sum()), "n_未站回": int(n0),
           "未站回區段數": nblk0, "n_eff": int(n_eff), "n_eff_尺度": "未站回事件數" if n0 <= nblk0 else "有未站回事件的區段數",
           "平均X_站回": float(E.loc[E["站回"] == 1, col].mean()), "平均X_未站回": float(nb[col].mean())}
    if n0 < 30:
        out["出口"] = "出口①"; out["結果"] = "結果④（未站回組 < 30 ⇒ 閘退化，併入出口①：樣本不足以分辨）"
    elif n_eff < 30:
        out["出口"] = "出口①"; out["結果"] = "—（出口①：樣本不足以分辨）"
    else:
        out["出口"] = "出口②" if n_eff < 100 else "出口③"
        out["結果"] = "結果①（測不出）" if out["lo"] <= 0 <= out["hi"] else ("結果②（測得出（＋））" if b > 0 else "結果③（測得出（−））")
    return {k: (f6(v) if isinstance(v, float) else v) for k, v in out.items()}


def shuffle_within(lab, keys, rng):
    lab = lab.copy()
    for _, idx in pd.Series(np.arange(len(keys))).groupby(keys).indices.items():
        lab[idx] = rng.permutation(lab[idx])
    return lab


def run_h1(procs, sids, M):
    t0 = time.time(); cal, w0, w1 = _W["cal"], _W["w0"], _W["w1"]
    res = pmap(w_h1, sids, procs)
    EWc = {Hh: USX.ew_close(M["O"], M["okO"] & M["MEM"], M["CFF"], M["CSPB"], Hh) for Hh in (20,) + HD}
    EWa = USX.ew_close(M["O"], M["okO"] & M["MEM"], M["CFF"], M["CSF"], 20)
    E = {}; ACC = {}
    for Hh in (20,) + HD:
        rows = []; acc = Counter()
        for s, out in res:
            rr, a = out[Hh]; acc.update(a)
            for r in rr:
                rows.append((s,) + r)
        df = pd.DataFrame(rows, columns=["sid", "T", "idx", "站回", "s_first", "e", "R", "a_R_t0", "mech", "f50"])
        df["X"] = df["R"] - EWc[Hh][df["e"].to_numpy(int)] if len(df) else []
        if Hh == 20 and len(df):
            df["X_alt"] = df["R"] - EWa[df["e"].to_numpy(int)]
        E[Hh] = df.sort_values(["T", "sid"]).reset_index(drop=True); ACC[Hh] = acc
    print("[A3-1] 事件 {}｜{:.0f}s".format({h: len(E[h]) for h in E}, time.time() - t0), flush=True)
    e20 = E[20]
    cols = {}
    for g in COLS:
        e = e20[gm(e20["idx"], g)]
        acc = Counter()
        for (gi, k), v in ACC[20].items():
            if g == "合併" or gi == ("400" if g == "只400" else "500"):
                acc[k] += v
        js = h1_judge(e, 20)
        # 假訊號臂
        fk = []
        if len(e) and e["站回"].nunique() == 2:
            mon = mon_of(e["T"])
            for r in range(1, REPS + 1):
                lab = shuffle_within(e["站回"].to_numpy(), mon, np.random.default_rng(SEED + r))
                j = h1_judge(e.assign(站回=lab), 20)
                fk.append(bool(j.get("lo") is not None and not (j["lo"] <= 0 <= j["hi"])))
        nfk = int(sum(fk))
        ex = {}
        for gg in ("站回", "未站回"):
            num = acc[gg + "_未來窗斷點"] + acc[gg + "_不成交"]
            den = num + acc["保留_" + gg]
            ex[gg] = {"斷點": acc[gg + "_未來窗斷點"], "t0+4不成交": acc[gg + "_不成交"], "分母": den, "比例": f6(num / den) if den else None}
        a_, b_ = (ex["站回"]["比例"] or 0), (ex["未站回"]["比例"] or 0)
        two = bool(max(a_, b_) > 2 * min(a_, b_)) if min(a_, b_) > 0 else bool(max(a_, b_) > 0)
        rate = float(e["站回"].mean()) if len(e) else np.nan
        mech = e.groupby("站回")["mech"].mean() if len(e) else pd.Series(dtype=float)
        ef = e[~e["f50"]] if len(e) else e
        jf = h1_judge(ef.assign(X=ef["X_alt"]) if len(ef) else ef, 20)
        desc = {"a_從t0起算（原始）": h1_judge(e, 20, col="a_R_t0"), "g_原始報酬": h1_judge(e, 20, col="R")}
        for Hh in HD:
            eH = E[Hh][gm(E[Hh]["idx"], g)]
            desc["H{}".format(Hh)] = h1_judge(eH, Hh)
        cols[g] = {"判定": js, "事件帳": dict(acc), "保留": int(len(e)), "相異檔數": int(e["sid"].nunique()) if len(e) else 0,
                   "站回率": f6(rate), "s1／s2／s3": [int((e["s_first"] == k).sum()) for k in (1, 2, 3)] if len(e) else [0, 0, 0],
                   "措辭前提（站回率≥80%）": bool(rate >= 0.8) if np.isfinite(rate) else False,
                   "④分組窗機械差": {"站回": f6(mech.get(1, np.nan)), "未站回": f6(mech.get(0, np.nan)),
                                 "差": f6(mech.get(1, np.nan) - mech.get(0, np.nan))},
                   "⑤逐年": {gg: e[e["站回"] == v]["T"].map(lambda t: cal[t].year).value_counts().sort_index().to_dict() for gg, v in (("站回", 1), ("未站回", 0))} if len(e) else {},
                   "⑥假訊號臂": {"判過": nfk, "次數": len(fk)}, "⑧未來窗排除": {**ex, "相差逾兩倍": two, "無法分組": acc["無法分組"]},
                   "敏感度_ret50": {"剔除事件": int(e["f50"].sum()) if len(e) else 0, **{k: jf.get(k) for k in ("n", "D", "lo", "hi", "n_eff", "結果")}},
                   "描述": desc}
    wk = write_work("A3-1_events_H20.csv.gz", e20.drop(columns=["f50"]))
    wk2 = {Hh: write_work("A3-1_events_H{}.csv.gz".format(Hh), E[Hh].drop(columns=["f50"])) for Hh in HD}
    # 卡片
    rc, r4 = cols["合併"]["判定"]["結果"], cols["只400"]["判定"]["結果"]
    lab = K.label_ev(rc, r4)

    def line(g):
        c = cols[g]; j = c["判定"]
        warn = []
        if c["⑥假訊號臂"]["判過"] >= 5:
            warn.append("⚠ 同設計假訊號臂判過 {}／30，CI 可能偏窄".format(c["⑥假訊號臂"]["判過"]))
        if c["⑧未來窗排除"]["相差逾兩倍"]:
            warn.append("⚠ 因分組後 20 日內停牌／硬斷點而排除的比例，站回組 {}、未站回組 {}，相差逾兩倍".format(
                pctf(c["⑧未來窗排除"]["站回"]["比例"]), pctf(c["⑧未來窗排除"]["未站回"]["比例"])))
        mid = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(j.get("n_eff")) if j.get("出口") == "出口②" else ""
        return "{}{}D {}（月分群 95% CI {}～{}，n_eff {}；站回 {}／未站回 {}；站回率 {}）{} {}".format(
            "".join(w + "；" for w in warn), mid, ppf(j.get("D")), ppf(j.get("lo")), ppf(j.get("hi")), j.get("n_eff"),
            j.get("n_站回"), j.get("n_未站回"), pctf(c["站回率"], 1), j.get("出口"), j.get("結果"))
    prem = "未站回組是一個較小的子群，它表現較差可能只是它本來就跌得較兇；" if cols["合併"]["措辭前提（站回率≥80%）"] else ""
    jc = cols["合併"]["判定"]
    if K.passed(rc):
        core = "在 H＝20、k＝5、3 天期限、分組確定後起算這一格上，站回組分組後 20 日超額比未站回組高 {}（月分群 95% CI {}～{}，n_eff＝{}）。單筆層描述；⛔ 不是進場訊號、⛔ 不推論組合層。".format(
            ppf(jc.get("D")), ppf(jc.get("lo")), ppf(jc.get("hi")), jc.get("n_eff"))
    elif str(rc).startswith("結果①"):
        core = "在 H＝20、k＝5、3 天期限、分組確定後起算這一格上，測不出兩組差（合併 CI {}～{} 含 0）。⛔ 不表示『3 天站回』沒有意義，只表示這一格分辨不出。".format(
            ppf(jc.get("lo")), ppf(jc.get("hi")))
    else:
        core = "在 H＝20、k＝5、3 天期限、分組確定後起算這一格上，合併 {}（D {}，CI {}～{}）。".format(rc, ppf(jc.get("D")), ppf(jc.get("lo")), ppf(jc.get("hi")))
    sent = "{}：{}{}只 S&P 400：{}。{}；{}。".format(lab, prem, core, r4, K.IDEA, K.SURV)
    sens = "剔除 |ret|＞50% 未確認列碰到的事件 {} 筆後：合併 {}、只 S&P 400 {}（判語{}）".format(
        cols["合併"]["敏感度_ret50"]["剔除事件"], cols["合併"]["敏感度_ret50"]["結果"], cols["只400"]["敏感度_ret50"]["結果"],
        "不變" if (K.label_ev(cols["合併"]["敏感度_ret50"]["結果"], cols["只400"]["敏感度_ret50"]["結果"]) == lab) else "改變")
    da = cols["合併"]["描述"]["a_從t0起算（原始）"]
    prior = "台股原押：判定欄測不出或很小（約七成五）⇒ 美股合併 {}（{}）；另押描述欄 a（從 t0 起算）比判定欄明顯偏向站回組 ⇒ a 欄 D {} 對判定欄 {}（{}）。".format(
        rc, "押中" if (str(rc).startswith("結果①") or (jc.get("D") is not None and abs(jc["D"]) < 0.005)) else "沒押中",
        ppf(da.get("D")), ppf(jc.get("D")), "押中" if (da.get("D") is not None and jc.get("D") is not None and da["D"] > jc["D"]) else "沒押中")
    card = {"件": "A3-1", "名稱": "月線 3 日站回（H1，分類器讀法）", "台股原登錄": TWREG["A3-1"], "出場型": "③ 事件（判定 H20＝原文；60／120／240 描述）",
            "N": 1, "標籤": lab, "判定格": "SMA20 上揚 k＝5、首次跌破、3 天期限、分組確定後起算 H＝20 的兩組差 D",
            "三欄": {"合併": line("合併"), "只400": line("只400"), "只500": "（描述、⛔ 不判）" + line("只500")},
            "條件出場必報": None, "結果句": sent, "敏感度_ret50": sens,
            "偏離": ["判定量的基準 gate3 母體等權 → 合併母體等權（同段，USX.ew_close）；T+1 開盤漲停剔除拿掉（P4）",
                   "描述臂 b（k 1／10）、c（期限 2／5 天）、e（進場讀法）、f（SMA10／60）本批不重跑（A2 A6 先例）；H 描述擴到 60／120／240"],
            "補讀法": ["G1～G6、H1a～H1d（docstring，寫死於 {}）".format(READ_TS)], "先驗紀錄": prior}
    J = {"卡片": card, "依據": K.REG, "讀法寫死": READ_TS, "資料commit": _W["meta"].get("data_commit"), "三欄": cols,
         "逐筆中間檔": {"H20": wk, **{"H%d" % h: v for h, v in wk2.items()}}, "存活者偏差": K.SURV}
    return J


# ═════════════════════════ A3-2 H2 ═════════════════════════
def w_h2(s):
    d = _W["ST"][s]; S = _W["SK"][s]; n = _W["n"]
    bars, C, valid, member = d["bars"], d["C"], d["valid"], d["member"]
    cb = C[bars]; nb = len(bars)
    sig = np.zeros(n, bool); mn = np.full(n, np.nan); lit = np.zeros(n, bool)
    if nb >= 206:
        ma144 = P.roll_mean(cb, 144); ma200 = P.roll_mean(cb, 200)
        with np.errstate(invalid="ignore"):
            u1 = np.zeros(nb, bool); u2 = np.zeros(nb, bool)
            u1[5:] = ma144[5:] > ma144[:-5]; u2[5:] = ma200[5:] > ma200[:-5]
            mx = np.fmax(ma144, ma200); mx[np.isnan(ma144) | np.isnan(ma200)] = np.nan
            s_ = np.zeros(nb, bool)
            s_[1:] = u1[1:] & u2[1:] & (cb[1:] >= mx[1:]) & (cb[:-1] < mx[:-1])
        s_ &= np.isfinite(mx); s_[1:] &= np.isfinite(mx[:-1]); s_[:205] = False
        sig[bars] = s_
        m_ = np.fmin(ma144, ma200); m_[np.isnan(ma144) | np.isnan(ma200)] = np.nan
        mn[bars] = m_
    rb = np.full(n, np.nan)
    if nb > 1:
        rb[bars[1:]] = cb[1:] / cb[:-1] - 1.0
    vol = pd.Series(rb).rolling(60, min_periods=2).std(ddof=1).to_numpy()
    nbc = np.cumsum(valid)
    t = np.arange(n); a = t - 199
    pad = lambda cs: np.r_[0, cs]
    cp, cm = pad(S.cs_pb), pad(S.cs_ms)
    lo = np.maximum(a, 0)
    past = ((cp[t + 1] - cp[lo]) > 0) | ((cm[t + 1] - cm[lo]) > 0)
    elig = valid & member & (nbc >= 200) & ~past & np.isfinite(vol) & (a >= 0)
    return s, sig, elig, vol, mn


def ge13(mx, base):
    return int(np.isfinite(mx) and mx >= 1.3 * base * (1 - 1e-12))


class H2Ctx:
    def __init__(self, sids, SIG, ELIG, VOL, MN):
        self.sids = sids; self.SIG, self.ELIG, self.VOL, self.MN = SIG, ELIG, VOL, MN
        self.si = {s: i for i, s in enumerate(sids)}; self._day = {}; self._oc = {}

    def outcome(self, j, t, H):
        k = (j, t, H)
        if k in self._oc:
            return self._oc[k]
        s = self.sids[j]; d = _W["ST"][s]; S = _W["SK"][s]
        if t + H >= _W["n"] or S.brk(t + 1, t + H):
            r = "brk"
        elif not S.okO[t + 1]:
            r = "halt"
        else:
            P0 = float(d["O"][t + 1]); hh = d["H"][t + 1:t + H + 1]
            mx = float(np.nanmax(hh)) if np.isfinite(hh).any() else np.nan
            mn = float(self.MN[t, j]); cH = float(d["closes"][t + H])
            r = {"P0": P0, "hit": ge13(mx, P0), "g": cH / P0 - 1.0, "hit_lit": ge13(mx, mn) if np.isfinite(mn) else np.nan,
                 "r": P0 / mn if np.isfinite(mn) else np.nan, "f50": bool(d["f50"][max(t - 199, 0):t + H + 1].any())}
        self._oc[k] = r
        return r

    def day(self, t):
        if t not in self._day:
            idx = np.flatnonzero(self.ELIG[t]); vv = self.VOL[t, idx].astype(float)
            q = pd.qcut(pd.Series(vv).rank(method="first"), 5, labels=False).to_numpy() if len(vv) >= 5 else np.zeros(len(vv), int)
            self._day[t] = (idx, q, self.SIG[t, idx])
        return self._day[t]


def h2_build(C: H2Ctx, H):
    w0, w1 = _W["w0"], _W["w1"]; ST = _W["ST"]
    acc = Counter(); ev = []
    for j, s in enumerate(C.sids):
        d = ST[s]
        ts = np.flatnonzero(C.SIG[w0:w1 - H + 1, j]) + w0
        t0 = -10 ** 9
        for t in ts:
            t = int(t)
            if not (d["member"][t] and d["valid"][t]):
                continue
            gi = "400" if d["m4"][t] else "500"
            acc[(gi, "原始觸發")] += 1
            if t0 < t <= t0 + 20:
                acc[(gi, "合併掉")] += 1; continue
            if not C.ELIG[t, j]:
                acc[(gi, "樣本不足或過去斷點")] += 1; continue
            o = C.outcome(j, t, H)
            if o == "brk":
                acc[(gi, "未來窗斷點")] += 1; continue
            if o == "halt":
                acc[(gi, "不成交")] += 1; continue
            ev.append({"j": j, "sid": s, "t": t, "idx": gi, **o}); t0 = t
    ev.sort(key=lambda e: (e["t"], e["sid"]))
    return ev, acc


def h2_controls(C: H2Ctx, ev, H, seed, by_vol=True, m=M_CTRL):
    rng = np.random.default_rng(seed)
    acc = Counter(); out = []
    for e in ev:
        idx, q, sg = C.day(e["t"])
        ii = np.flatnonzero(idx == e["j"])
        if len(ii) == 0:
            out.append((e, [], np.zeros(0, int), np.zeros(0, int))); continue
        i = int(ii[0])
        msk = ~sg
        if by_vol:
            msk &= q == q[i]
        pool = idx[msk]; pool = pool[pool != e["j"]]
        if len(pool) < m:
            acc["池不足10"] += 1
        pick = rng.choice(pool, size=min(m, len(pool)), replace=False) if len(pool) else np.zeros(0, int)
        res = []
        for jj in pick:
            acc["對照抽樣數"] += 1
            o = C.outcome(int(jj), e["t"], H)
            if o == "brk":
                acc["對照_未來窗斷點"] += 1; continue
            if o == "halt":
                acc["對照_不成交"] += 1; continue
            res.append(o)
        if not res:
            acc["無對照成交而剔除"] += 1
        out.append((e, res, pool, pick))
    return out, acc


def h2_rows(pairs, key="hit", drop_f50=False):
    rows = []
    for e, res, _, _ in pairs:
        if drop_f50:
            if e.get("f50"):
                continue
            res = [r for r in res if not r.get("f50")]
        if not res:
            continue
        ce = np.array([r[key] for r in res], float)
        if key == "hit_lit" and (not np.isfinite(e[key]) or not np.isfinite(ce).any()):
            continue
        rows.append({"t": e["t"], "sid": e["sid"], "idx": e["idx"], "sig": float(e[key]), "ctl": float(np.nanmean(ce)),
                     "ctl_hits": int(np.nansum(ce)) if key != "g" else 0, "n_ctl": int(np.isfinite(ce).sum())})
    X = pd.DataFrame(rows, columns=["t", "sid", "idx", "sig", "ctl", "ctl_hits", "n_ctl"])
    X["d"] = X["sig"] - X["ctl"]
    return X


def h2_judge(X, H, key="hit"):
    w0 = _W["w0"]
    if len(X) == 0:
        return {"n": 0, "出口": "出口①", "結果": "—（無事件）"}
    cs = R11.cl_stats(X["d"].to_numpy(float), mon_of(X["t"]))
    blk = (X["t"] - w0) // H
    bm = X.groupby(blk)["d"].mean()
    se_b = float(bm.std(ddof=1) / np.sqrt(len(bm))) if len(bm) > 1 else np.nan
    n_ev, n_blk = len(X), int(blk.nunique()); n_eff = min(n_ev, n_blk)
    out = {"n": n_ev, "D": cs["mean"], "lo": cs["lo"], "hi": cs["hi"], "se_月": cs["se"], "曆月數": cs["months"],
           "lo_非重疊": cs["mean"] - 1.96 * se_b, "hi_非重疊": cs["mean"] + 1.96 * se_b, "區段數": n_blk, "n_eff": n_eff}
    if key in ("hit", "hit_lit"):
        sh, ch = int(X["sig"].sum()), int(X["ctl_hits"].sum())
        out.update({"訊號達成": sh, "訊號分母": n_ev, "對照達成": ch, "對照分母": int(X["n_ctl"].sum()),
                    "訊號達成率": float(X["sig"].mean()), "對照達成率": float((X["ctl"] * X["n_ctl"]).sum() / X["n_ctl"].sum())})
        if n_eff < 30 or sh < 30 or ch < 30:
            out["出口"] = "出口①"; out["結果"] = "—（出口①：樣本不足以分辨）" if ch >= 30 else "結果④（對照組達成筆數 < 30 ⇒ 閘退化，併入出口①）"
        else:
            out["出口"] = "出口②" if n_eff < 100 else "出口③"
            out["結果"] = "結果①（測不出）" if cs["lo"] <= 0 <= cs["hi"] else ("結果②（測得出（＋））" if cs["mean"] > 0 else "結果③（測得出（−））")
    else:
        out.update({"訊號平均": float(X["sig"].mean()), "對照平均": float(X["ctl"].mean())})
    return {k: (f6(v) if isinstance(v, (float, np.floating)) else v) for k, v in out.items()}


def h2_fake(C, pairs, H, r):
    rng = np.random.default_rng(SEED + r)
    fev = []
    for e, res, pool, pick in pairs:
        cand = pool[~np.isin(pool, pick)]
        if len(cand) == 0:
            continue
        f = int(rng.choice(cand))
        o = C.outcome(f, e["t"], H)
        if isinstance(o, dict):
            s = C.sids[f]
            fev.append({"j": f, "sid": s, "t": e["t"], "idx": "400" if _W["ST"][s]["m4"][e["t"]] else "500", **o})
    fev.sort(key=lambda x: (x["t"], x["sid"]))
    fp, _ = h2_controls(C, fev, H, SEED + r)
    return h2_rows(fp)


def qst(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return {"中位": f6(np.median(x)), "p10": f6(np.percentile(x, 10)), "p90": f6(np.percentile(x, 90))} if len(x) else {}


def run_h2(procs, sids):
    t0 = time.time(); cal = _W["cal"]
    res = pmap(w_h2, sids, procs)
    SIG = np.column_stack([r[1] for r in res]); ELIG = np.column_stack([r[2] for r in res])
    VOL = np.column_stack([r[3] for r in res]); MN = np.column_stack([r[4] for r in res])
    C = H2Ctx(sids, SIG, ELIG, VOL, MN)
    ev, acc = h2_build(C, 20)
    pairs, cacc = h2_controls(C, ev, 20, SEED)
    X = h2_rows(pairs)
    print("[A3-2] 保留事件 {}｜可判 {}｜{:.0f}s".format(len(ev), len(X), time.time() - t0), flush=True)
    # 假訊號臂（30 次）
    FK = []
    for r in range(1, REPS + 1):
        FK.append(h2_fake(C, pairs, 20, r))
    print("[A3-2] 假訊號臂完成｜{:.0f}s".format(time.time() - t0), flush=True)
    # 描述
    D_H = {}
    for H in HD:
        e2, a2 = h2_build(C, H); p2, _ = h2_controls(C, e2, H, SEED); D_H[H] = (h2_rows(p2), len(e2))
    Xlit = h2_rows(pairs, "hit_lit"); Xg = h2_rows(pairs, "g")
    pe, _ = h2_controls(C, ev, 20, SEED, by_vol=False); Xe = h2_rows(pe)
    Xf = h2_rows(pairs, drop_f50=True)
    print("[A3-2] 描述完成｜{:.0f}s".format(time.time() - t0), flush=True)
    cols = {}
    for g in COLS:
        xg = X[gm(X["idx"], g)]; js = h2_judge(xg, 20)
        evg = [e for e in ev if g == "合併" or e["idx"] == ("400" if g == "只400" else "500")]
        a = Counter()
        for (gi, k), v in acc.items():
            if g == "合併" or gi == ("400" if g == "只400" else "500"):
                a[k] += v
        nfk = 0
        for fx in FK:
            j = h2_judge(fx[gm(fx["idx"], g)], 20)
            if j.get("lo") is not None and j["n"] > 0 and not (j["lo"] <= 0 <= j["hi"]):
                nfk += 1
        den_s = a["未來窗斷點"] + a["不成交"] + len(evg)
        ps = (a["未來窗斷點"] + a["不成交"]) / max(1, den_s)
        pg = [p for p in pairs if g == "合併" or p[0]["idx"] == ("400" if g == "只400" else "500")]
        nc = sum(len(p[3]) for p in pg); nbad = nc - sum(len(p[1]) for p in pg)
        pc = nbad / max(1, nc)
        two = bool(max(ps, pc) > 2 * min(ps, pc)) if min(ps, pc) > 0 else bool(max(ps, pc) > 0)
        nct = [len(p[1]) for p in pg]
        cols[g] = {"判定": js, "事件帳": {**dict(a), "保留事件": len(evg), "相異檔數": len({e["sid"] for e in evg})},
                   "②白拿段": {"r": qst([e["r"] for e in evg]), "1.3/r−1": qst([1.3 / e["r"] - 1 for e in evg if np.isfinite(e["r"])])},
                   "④對照": {"成交對照 < 10 的事件": int(sum(1 for x in nct if x < 10)), "無對照成交而剔除": int(sum(1 for x in nct if x == 0)),
                            "每事件成交對照數中位": f6(np.median(nct)) if nct else None},
                   "⑤假訊號臂": {"判過": nfk, "次數": REPS},
                   "⑦逐年": pd.Series([cal[e["t"]].year for e in evg]).value_counts().sort_index().to_dict() if evg else {},
                   "⑧未來窗排除": {"訊號比例": f6(ps), "對照比例": f6(pc), "相差逾兩倍": two},
                   "敏感度_ret50": {"剔除事件": int(sum(1 for e in evg if e["f50"])), **{k: v for k, v in h2_judge(Xf[gm(Xf["idx"], g)], 20).items() if k in ("n", "D", "lo", "hi", "n_eff", "結果")}},
                   "描述": {"d_原說法字面": h2_judge(Xlit[gm(Xlit["idx"], g)], 20, "hit_lit"),
                          "e_只對日期": h2_judge(Xe[gm(Xe["idx"], g)], 20),
                          "g_20日報酬差": h2_judge(Xg[gm(Xg["idx"], g)], 20, "g"),
                          **{"H{}".format(H): h2_judge(D_H[H][0][gm(D_H[H][0]["idx"], g)], H) for H in HD}}}
    cols["合併"]["④對照"]["帳"] = dict(cacc)
    wk = write_work("A3-2_events_H20.csv.gz", pd.DataFrame([{"sid": e["sid"], "t": e["t"], "idx": e["idx"], "P0": e["P0"], "hit": e["hit"], "g": e["g"],
                                                             "r": e["r"], "picks": ";".join(sids[int(j)] for j in pk),
                                                             "ctl_hit": float(np.mean([x["hit"] for x in rs])) if rs else np.nan, "n_ctl": len(rs)}
                                                            for e, rs, _, pk in pairs]))
    rc, r4 = cols["合併"]["判定"]["結果"], cols["只400"]["判定"]["結果"]
    lab = K.label_ev(rc, r4)

    def line(g):
        c = cols[g]; j = c["判定"]; warn = []
        if c["⑤假訊號臂"]["判過"] >= 5:
            warn.append("⚠ 同設計假訊號臂判過 {}／30，CI 可能偏窄".format(c["⑤假訊號臂"]["判過"]))
        if c["⑧未來窗排除"]["相差逾兩倍"]:
            warn.append("⚠ 因未來 20 日內停牌／硬斷點而排除的比例，訊號組 {}、對照組 {}，相差逾兩倍".format(pctf(c["⑧未來窗排除"]["訊號比例"]), pctf(c["⑧未來窗排除"]["對照比例"])))
        mid = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(j.get("n_eff")) if j.get("出口") == "出口②" else ""
        return "{}{}D {}（訊號達成率 {}、對照 {}；月分群 95% CI {}～{}，n_eff {}，事件 {}）{} {}".format(
            "".join(w + "；" for w in warn), mid, ppf(j.get("D")), pctf(j.get("訊號達成率"), 1), pctf(j.get("對照達成率"), 1),
            ppf(j.get("lo")), ppf(j.get("hi")), j.get("n_eff"), j.get("n"), j.get("出口"), j.get("結果"))
    jc = cols["合併"]["判定"]
    if K.passed(rc):
        core = "在 H＝20、k＝5、同日同波動五分位對照這一格上，雙翻揚首次站上後 20 個交易日內觸及進場價 ×1.3 的比例，比對照高 {}（月分群 95% CI {}～{}，n_eff＝{}）。單筆層描述；⛔ 不是策略、⛔ 不推論組合層。".format(
            ppf(jc.get("D")), ppf(jc.get("lo")), ppf(jc.get("hi")), jc.get("n_eff"))
    elif str(rc).startswith("結果①"):
        core = "在 H＝20、k＝5、同日同波動五分位對照這一格上，測不出差異（合併 CI {}～{} 含 0）。⛔ 不表示宣稱為假，只表示在這一格上分辨不出。".format(ppf(jc.get("lo")), ppf(jc.get("hi")))
    elif str(jc.get("出口")) == "出口①":
        core = "在 H＝20、k＝5、同日同波動五分位對照這一格上，樣本不足以分辨（n_eff＝{}／達成筆數 {}、{}）。".format(jc.get("n_eff"), jc.get("訊號達成"), jc.get("對照達成"))
    else:
        core = "在 H＝20、k＝5、同日同波動五分位對照這一格上，合併 {}（D {}，CI {}～{}）。".format(rc, ppf(jc.get("D")), ppf(jc.get("lo")), ppf(jc.get("hi")))
    sent = "{}：{}只 S&P 400：{}。{}；{}。".format(lab, core, r4, K.IDEA, K.SURV)
    sens = "剔除 |ret|＞50% 未確認列碰到的事件 {} 筆（對照同剔）後：合併 {}、只 S&P 400 {}（判語{}）".format(
        cols["合併"]["敏感度_ret50"]["剔除事件"], cols["合併"]["敏感度_ret50"]["結果"], cols["只400"]["敏感度_ret50"]["結果"],
        "不變" if K.label_ev(cols["合併"]["敏感度_ret50"]["結果"], cols["只400"]["敏感度_ret50"]["結果"]) == lab else "改變")
    prior = "台股原押：判定格落在測不出或很小（約七成）⇒ 美股合併 {}（D {}）⇒ {}。".format(
        rc, ppf(jc.get("D")), "押中" if (str(rc).startswith("結果①") or (jc.get("D") is not None and abs(jc["D"]) < 0.01)) else "沒押中")
    card = {"件": "A3-2", "名稱": "144／200MA 雙翻揚 20 日內觸及 ×1.3（H2）", "台股原登錄": TWREG["A3-2"], "出場型": "③ 事件（判定 H20＝原文；60／120／240 描述）",
            "N": 1, "標籤": lab, "判定格": "MA144／200 上揚 k＝5、首次站上、H＝20、同日同 vol60 五分位對照的達成率差 D",
            "三欄": {"合併": line("合併"), "只400": line("只400"), "只500": "（描述、⛔ 不判）" + line("只500")},
            "條件出場必報": None, "結果句": sent, "敏感度_ret50": sens,
            "偏離": ["對照池 gate3 同日同 vol60 五分位 → 合併母體同日同 vol60 五分位；上市／上櫃組成 → S&P 500／400（三欄）；T+1 開盤漲停不成交拿掉（P4）",
                   "過去窗斷點起點照原文日曆 t−199（prep 用往前第 199 根有效 K 棒）",
                   "描述臂 a（k 1／10）、b（120／240 均線）、f（滾動續抱）本批不重跑（A2 A6 先例）；H 描述擴到 60／120／240"],
            "補讀法": ["G1～G6、H2a～H2e（docstring，寫死於 {}）".format(READ_TS)], "先驗紀錄": prior}
    return {"卡片": card, "依據": K.REG, "讀法寫死": READ_TS, "資料commit": _W["meta"].get("data_commit"), "三欄": cols,
            "逐筆中間檔": {"H20": wk}, "存活者偏差": K.SURV}


# ═════════════════════════ A3-4 上升趨勢線跌破 ═════════════════════════
UT_M, UT_R, UT_RU = ("甲", "乙", "丙"), (3, 5, 10), ("pct1", "d3p3")
UT_NM = {"pct1": "1%穿越", "d3p3": "3日3%"}
UT_CELLS = [(m, R, ru) for m in UT_M for R in UT_R for ru in UT_RU]
UT_MAIN = ("甲", 5, "pct1")
UT_HOLD, UT_MERGE = 21, 20


def ut_name(c):
    return "{}_R{}_{}".format(c[0], c[1], UT_NM[c[2]])


def ut_status(evs, d, S, w0, wE):
    acc = Counter(); keep = []; tk = -10 ** 9
    for T, first, conf in sorted(evs):
        if not (w0 <= T <= wE):
            continue
        if not (d["member"][T] and d["valid"][T]):
            continue
        gi = "400" if d["m4"][T] else "500"
        acc[(gi, "原始")] += 1
        if tk < T <= tk + UT_MERGE:
            acc[(gi, "合併掉")] += 1; continue
        if S.brk(first, T + UT_HOLD):
            acc[(gi, "剔除_硬斷點")] += 1; continue
        if not S.okO[T + 1]:
            acc[(gi, "剔除_T+1不成交")] += 1; continue
        acc[(gi, "保留")] += 1; keep.append((T, first, conf, gi)); tk = T
    return keep, acc


def w_ut(s):
    d = _W["ST"][s]; S = _W["SK"][s]; w0, w1 = _W["w0"], _W["w1"]; wE = w1 - UT_HOLD; n = _W["n"]
    O, L, C = d["O"], d["L"], d["C"]
    out = {}; raw_main = np.zeros(0, int); why = {}; mism = 0
    for m, R, ru in UT_CELLS:
        if m == "丙" and R != 5:
            continue
        r = UTL.detect_calendar(O, L, C, m, R, ru)
        evs = [(int(e["T"]), int(e["first"]), int(e.get("conf", -1)) if e.get("conf") is not None else -1) for e in r["events"]]
        out[(m, R, ru)] = ut_status(evs, d, S, w0, wE)
        if (m, R, ru) == UT_MAIN:
            raw_main = np.array([e[0] for e in evs], int)
            b = d["bars"]
            ul = RV.up_line_events(O[b], L[b], C[b])
            mism = int(sorted((int(b[a]), int(b[f])) for a, f in ul) != sorted((e[0], e[1]) for e in evs))
        if (m, R, ru) == ("乙", 5, "pct1"):
            why = r["why_at"]
    for R in (3, 10):
        for ru in UT_RU:
            out[("丙", R, ru)] = out[("丙", 5, ru)]
    cb = C[d["bars"]]; r60 = np.full(n, np.nan)
    if len(cb) > 60:
        r60[d["bars"][60:]] = cb[60:] / cb[:-60] - 1.0
    return s, out, raw_main, why, mism, r60


def run_ut(procs, sids):
    t0 = time.time(); cal, w0, w1 = _W["cal"], _W["w0"], _W["w1"]; wE = w1 - UT_HOLD; n = _W["n"]; ST, SK = _W["ST"], _W["SK"]
    res = pmap(w_ut, sids, procs)
    EW = K.ew_bench(ST, sids, (20,) + HD, ("合併",))
    EWa = K.ew_bench(ST, sids, (20,), ("合併",), f50_break=True)[("合併", 20)]
    cap = -(-(wE - w0 + 1) // 20)
    mism = sum(r[4] for r in res)
    print("[A3-4] 偵測完成｜主格與 up_line_events 不同檔數 {}｜{:.0f}s".format(mism, time.time() - t0), flush=True)
    E = {}; ACC = {}
    for cell in UT_CELLS:
        rows = []; acc = Counter()
        for s, out, *_ in res:
            kp, a = out[cell]; acc.update(a)
            d = ST[s]; S = SK[s]
            for T, first, conf, gi in kp:
                g = S.px[T + UT_HOLD] / d["O"][T + 1] - 1.0
                rows.append((s, T, first, conf, gi, g, g - EW[("合併", 20)][T + 1], g - EWa[T + 1],
                             bool(d["f50"][first:T + UT_HOLD + 1].any())))
        E[cell] = pd.DataFrame(rows, columns=["sid", "T", "first", "conf", "idx", "g", "X", "X_alt", "f50"]); ACC[cell] = acc
    em = E[UT_MAIN]
    print("[A3-4] 主格保留 {}｜{:.0f}s".format(len(em), time.time() - t0), flush=True)
    # 控制組（主格）
    sidx = {s: i for i, s in enumerate(sids)}
    R60 = np.column_stack([r[5] for r in res])
    VM = np.column_stack([ST[s]["valid"] & ST[s]["member"] for s in sids])
    OK1 = np.zeros_like(VM); OK1[:-1] = np.column_stack([SK[s].okO[1:] for s in sids])
    HB = np.zeros_like(VM)
    Tr = np.arange(1, n - UT_HOLD)
    for i, s in enumerate(sids):
        S = SK[s]
        cp = np.r_[0, S.cs_pb]; cm = np.r_[0, S.cs_ms]
        HB[Tr, i] = ((cp[Tr + UT_HOLD + 1] - cp[Tr]) > 0) | ((cm[Tr + UT_HOLD + 1] - cm[Tr]) > 0)
    PXm = np.column_stack([SK[s].px for s in sids]); Om = np.column_stack([np.where(SK[s].okO, ST[s]["O"], np.nan) for s in sids])
    G20 = np.full(PXm.shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        G20[:n - UT_HOLD] = PXm[UT_HOLD:] / Om[1:n - UT_HOLD + 1] - 1.0
    RAW = np.zeros(VM.shape, bool)
    for s, out, raw, *_ in res:
        RAW[raw, sidx[s]] = True
    crow = []
    with np.errstate(invalid="ignore"):
        for T, grp in em.groupby("T"):
            el = VM[T] & (R60[T] > 0) & OK1[T] & ~HB[T] & ~RAW[T] & np.isfinite(G20[T])
            for ev in grp.itertuples():
                cm_ = el.copy(); cm_[sidx[ev.sid]] = False
                if cm_.any():
                    crow.append((T, ev.idx, ev.g - float(G20[T, cm_].mean()), int(cm_.sum())))
    CT = pd.DataFrame(crow, columns=["T", "idx", "d", "nc"])
    del G20, PXm, Om, HB, RAW, VM, OK1
    # 放棄組
    why = {s: w for s, _, _, w, *_ in res}
    em = em.assign(乙選取=[why[s].get(int(cf), "（該根無乙選取）") for s, cf in zip(em["sid"], em["conf"])])
    # 假訊號臂
    realT = {s: np.sort(g["T"].to_numpy()) for s, g in em.groupby("sid")}
    cand = {}
    for s in realT:
        d = ST[s]; b = d["bars"]; b = b[(b >= w0) & (b <= wE)]; b = b[d["member"][b]]
        rt = realT[s]; k_ = np.searchsorted(rt, b, side="right")
        prev = np.where(k_ > 0, rt[np.maximum(k_ - 1, 0)], -10 ** 9)
        cand[s] = b[~((k_ > 0) & (b - prev <= 20))]
    FK = []
    for r in range(REPS):
        xs = []
        for s in sorted(realT):
            d = ST[s]; S = SK[s]
            rng = np.random.default_rng([SEED + r, zlib.crc32(s.encode())])
            k = min(len(realT[s]), len(cand[s]))
            for T in (np.sort(rng.choice(cand[s], size=k, replace=False)) if k else []):
                T = int(T)
                if S.brk(T, T + UT_HOLD) or not S.okO[T + 1]:
                    continue
                xs.append((T, "400" if d["m4"][T] else "500", S.px[T + UT_HOLD] / d["O"][T + 1] - 1.0 - EW[("合併", 20)][T + 1]))
        FK.append(pd.DataFrame(xs, columns=["T", "idx", "X"]))
    print("[A3-4] 控制組、假訊號臂完成｜{:.0f}s".format(time.time() - t0), flush=True)

    def sm(x, T, blk=20, cp_=None):
        return K.ev_summ(np.asarray(x, float), np.asarray(T, int), cal, w0, wE if blk == 20 else w1, blk=blk, cap=cp_ if cp_ else cap)

    cols = {}
    for g in COLS:
        e = em[gm(em["idx"], g)]
        s_ = sm(e["X"], e["T"])
        a = Counter()
        for (gi, k), v in ACC[UT_MAIN].items():
            if g == "合併" or gi == ("400" if g == "只400" else "500"):
                a[k] += v
        sR = sm(e["g"] - K.COST, e["T"]) if len(e) else {"n": 0}
        fk = {"判過": 0, "其中(+)": 0, "其中(−)": 0}
        for f in FK:
            fg = f[gm(f["idx"], g)]
            sf = sm(fg["X"], fg["T"])
            if sf.get("n", 0) and not (sf["lo"] <= 0 <= sf["hi"]):
                fk["判過"] += 1; fk["其中(+)" if sf["平均"] > 0 else "其中(−)"] += 1
        ef = e[~e["f50"]]
        sf = sm(ef["X_alt"], ef["T"])
        desc = {}
        for H in HD:
            xs, Ts = [], []
            for ev in e.itertuples():
                T = int(ev.T)
                if T + 1 + H > w1 or SK[ev.sid].brk(int(ev.first), T + 1 + H):
                    continue
                xs.append(SK[ev.sid].px[T + 1 + H] / ST[ev.sid]["O"][T + 1] - 1.0 - EW[("合併", H)][T + 1]); Ts.append(T)
            desc["H{}".format(H)] = cut(K.ev_summ(np.asarray(xs, float), np.asarray(Ts, int), cal, w0, w1, blk=H, cap=(w1 - w0 + 1) // H))
        ct = CT[gm(CT["idx"], g)]
        desc["控制組_同T近60日上漲不看趨勢線"] = {**cut(sm(ct["d"], ct["T"]), ("n", "平均", "lo", "hi", "n_eff")),
                                          "每事件控制數中位": f6(ct["nc"].median()) if len(ct) else None}
        if g == "合併":
            desc["放棄組_依乙R5選取"] = {w: cut(sm(gg["X"], gg["T"]), ("n", "平均", "lo", "hi")) for w, gg in e.groupby("乙選取")}
            desc["其餘17格（只報數）"] = {}
            for cell in UT_CELLS:
                if cell == UT_MAIN:
                    continue
                ec = E[cell]
                desc["其餘17格（只報數）"][ut_name(cell)] = {**cut(sm(ec["X"], ec["T"]), ("n", "平均", "lo", "hi", "n_eff")),
                                                       "只400": cut(sm(ec[gm(ec["idx"], "只400")]["X"], ec[gm(ec["idx"], "只400")]["T"]), ("n", "平均", "lo", "hi", "n_eff")),
                                                       "丙三個R相同": cell[0] == "丙"}
        cols[g] = {"判定": {**cut(s_), "R_e平均": f6(sR.get("平均"))}, "事件帳": dict(a), "相異檔數": int(e["sid"].nunique()),
                   "逐年": {str(y): {k: f6(v) if isinstance(v, float) else v for k, v in cut(sm(gg["X"], gg["T"]), ("n", "平均", "lo", "hi")).items()}
                          for y, gg in e.groupby(e["T"].map(lambda t: cal[t].year))},
                   "假訊號臂": fk, "敏感度_ret50": {"剔除事件": int(e["f50"].sum()), **cut(sf, ("n", "平均", "lo", "hi", "n_eff", "結果"))}, "描述": desc}
    wk = write_work("A3-4_events_main.csv.gz", em.drop(columns=["f50"]))
    rc, r4 = cols["合併"]["判定"]["結果"], cols["只400"]["判定"]["結果"]
    neg = lambda r: isinstance(r, str) and r.startswith("結果③")
    lab = "合格" if (neg(rc) and neg(r4)) else ("事後擴母體" if neg(rc) else "不合格")

    def verdict_sent(c):
        j = c["判定"]; r = j.get("結果", "")
        if str(r).startswith("結果③"):
            return "上升趨勢線跌破後，平均比同月其他股票差 {:.2f}%".format(-j["平均"] * 100)
        if str(r).startswith("結果②"):
            return "跌破上升趨勢線，看不出之後比較會跌（反而測得出（＋））⇒ 不構成賣出理由"
        return "跌破上升趨勢線，看不出之後比較會跌 ⇒ 不構成賣出理由"

    def line(g):
        c = cols[g]; j = c["判定"]; warn = ""
        if str(j.get("結果", "")).startswith("結果③") and c["假訊號臂"]["其中(−)"] >= 2:
            warn = "⚠ 隨機日也有 {}／30 測得出（−）；".format(c["假訊號臂"]["其中(−)"])
        mid = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(j.get("n_eff")) if j.get("出口") == "出口②" else ""
        return "{}{}X 平均 {}（月分群 95% CI {}～{}，n_eff {}，事件 {}）{} {}｜{}".format(warn, mid, pctf(j.get("平均")), pctf(j.get("lo")), pctf(j.get("hi")),
                                                                         j.get("n_eff"), j.get("n"), j.get("出口"), j.get("結果"), verdict_sent(c))
    ctl = cols["合併"]["描述"]["控制組_同T近60日上漲不看趨勢線"]
    sent = "{}：主格（甲 兩點法 × R＝5 × 1% 穿越）合併 {}；只 S&P 400 {}。⭐ 本件是賣出訊號讀法，「過」＝ 顯著為負（結果③）。控制組（同 T 近 60 日上漲、不看趨勢線）差 {}（描述）。{}；{}。".format(
        lab, line("合併"), cols["只400"]["判定"].get("結果"), pctf(ctl.get("平均")), K.IDEA, K.SURV)
    sens = "剔除 |ret|＞50% 未確認列碰到的事件 {} 筆後：合併 {}、只 S&P 400 {}".format(cols["合併"]["敏感度_ret50"]["剔除事件"], cols["合併"]["敏感度_ret50"].get("結果"),
                                                                    cols["只400"]["敏感度_ret50"].get("結果"))
    jc = cols["合併"]["判定"]
    ok_prior = (not neg(rc)) or (ctl.get("lo") is not None and ctl["lo"] <= 0 <= ctl["hi"])
    prior = "台股原押：主格分不出或負但與同月弱勢分不開（約七成）⇒ 美股合併 {}、控制組差 {}（CI {}～{}）⇒ {}。".format(
        rc, pctf(ctl.get("平均")), pctf(ctl.get("lo")), pctf(ctl.get("hi")), "押中" if ok_prior else "沒押中")
    card = {"件": "A3-4", "名稱": "上升趨勢線跌破（個股層）", "台股原登錄": TWREG["A3-4"], "出場型": "③ 事件（主格 20 日判；60／120／240 描述）",
            "N": 1, "標籤": lab, "判定格": "甲 兩點法 × R＝5 × 1% 穿越（20 日超額 X，顯著為負才算「跌破後真的會跌」）",
            "三欄": {"合併": line("合併"), "只400": line("只400"), "只500": "（描述、⛔ 不判）" + line("只500")},
            "條件出場必報": None, "結果句": sent, "敏感度_ret50": sens,
            "偏離": ["同月全母體 → 合併母體等權（EW_20(T+1)，MB.ew_us）；上市／上櫃 → S&P 500／400（三欄）；T+1 開盤漲停剔除拿掉（P4）",
                   "斷點範圍照原登錄到 T+21（prep keep_first 用 T+20）",
                   "主格與 prep 的 researchRev.up_line_events 逐檔核對：不同 {} 檔（照報）".format(mism),
                   "通過＝結果③（賣出讀法，UTd）；60／120／240 描述"],
            "補讀法": ["G1～G6、UTa～UTf（docstring，寫死於 {}）".format(READ_TS)], "先驗紀錄": prior}
    return {"卡片": card, "依據": K.REG, "讀法寫死": READ_TS, "資料commit": _W["meta"].get("data_commit"), "三欄": cols,
            "主格偵測核對_up_line_events不同檔數": mism, "區段上限": cap, "逐筆中間檔": {"主格": wk}, "存活者偏差": K.SURV}


# ═════════════════════════ A3-8 週線 ═════════════════════════
KS, SIGS = RW.KS, RW.SIGS
SEGS = ("探索", "確認")
COST_B = K.COST


def w_wk(s):
    d = _W["ST"][s]; S = _W["SK"][s]
    wk, wf, wl = _W["wk"], _W["wf"], _W["wl"]; nw = len(wf); w0, w1 = _W["w0"], _W["w1"]
    O, H, L, C, V, valid, member = d["O"], d["H"], d["L"], d["C"], d["V"], d["valid"], d["member"]
    wks, WO, WH, WL, WC, WV = RW.weekly_bars(valid, O, H, L, C, np.nan_to_num(V), wk)
    has = np.zeros(nw, bool); memw = np.zeros(nw, bool); sigs = {s_: [] for s_ in SIGS}
    Rk = {k: np.full(nw, np.nan) for k in KS}; r4 = np.full(nw, np.nan)
    nanlow = 0
    if len(wks) == 0:
        return s, has, memw, Rk, r4, sigs, nanlow
    ix = np.flatnonzero(valid); w_ = wk[ix]; stt = np.r_[0, np.flatnonzero(np.diff(w_)) + 1]; en = np.r_[stt[1:], len(ix)] - 1
    wlast = ix[en]
    has[wks] = True; memw[wks] = member[wlast]
    nanlow = int(np.isnan(WL).sum())
    if len(wks) > 40:
        sig = RW.signals(WO, WH, WL, WC, WV)
        badw = np.zeros(int(wk.max()) + 3, bool); badw[wk[d["pb"]]] = True
        near = badw[wks] | badw[np.maximum(wks - 1, 0)] | badw[wks + 1]
        for s_ in SIGS:
            last = -10 ** 9
            for i in np.flatnonzero(sig[s_]):
                if i < 35 or near[i]:
                    continue
                if wks[i] - last <= 8:
                    continue
                dd = int(wlast[i])
                if not (w0 <= dd <= w1) or not (member[dd] and valid[dd]):
                    continue
                last = wks[i]
                sigs[s_].append((dd, int(wks[i])))
    cff = d["closes"]
    for k in KS:
        for w in np.flatnonzero(has):
            if w + k >= nw:
                continue
            e = wf[w + 1]; x = wl[w + k]
            if x > w1 or not S.okO[e] or S.brk(wf[w], x):
                continue
            Rk[k][w] = cff[x] / O[e] - 1.0
    ce = cff[wl]
    with np.errstate(invalid="ignore", divide="ignore"):
        r4[4:] = ce[4:] / ce[:-4] - 1.0
    r4[~has] = np.nan
    return s, has, memw, Rk, r4, sigs, nanlow


def cstats(x, mon, z):
    cs = R11.cl_stats(np.asarray(x, float), np.asarray(mon))
    if cs["n"] == 0:
        return {"n": 0}
    return {"n": cs["n"], "D": cs["mean"], "se": cs["se"], "lo": cs["mean"] - z * cs["se"], "hi": cs["mean"] + z * cs["se"],
            "lo95": cs["lo"], "hi95": cs["hi"], "曆月": cs["months"]}


def band(lo, hi):
    return "測得出（＋）" if lo - COST_B > 0 else ("測得出（−）" if hi + COST_B < 0 else "測不出")


def exit_of(neff):
    return "出口①" if neff < 30 else ("出口②" if neff < 100 else "出口③")


def run_wk(procs, sids):
    t0 = time.time(); cal, w0, w1, sp, c0 = _W["cal"], _W["w0"], _W["w1"], _W["sp"], _W["c0"]
    wk, wf, wl = RW.weeks_of(cal); nw = len(wf)
    _W.update(wk=wk, wf=wf, wl=wl)
    res = pmap(w_wk, sids, procs)
    HAS = np.array([r[1] for r in res]); MEMW = np.array([r[2] for r in res]); R4 = np.array([r[4] for r in res]).astype(float)
    POOL = HAS & MEMW
    nanlow = sum(r[6] for r in res)
    segw = np.array([("探索" if (w0 <= wl[w] <= sp) else ("確認" if (c0 <= wl[w] <= w1) else "")) for w in range(nw)])
    month = np.array([str(cal[x])[:7] for x in wl])
    X1, X2, RK = {}, {}, {}
    for k in KS:
        Rm = np.array([r[3][k] for r in res]).astype(float); RK[k] = Rm
        x1 = np.full(Rm.shape, np.nan); x2 = np.full(Rm.shape, np.nan)
        for w in range(nw):
            ok = POOL[:, w] & np.isfinite(Rm[:, w]); ii = np.flatnonzero(ok)
            if len(ii) < 20:
                continue
            y = Rm[ii, w]; x1[ii, w] = y - (y.sum() - y) / (len(ii) - 1)
            ok2 = ok & np.isfinite(R4[:, w]); j2 = np.flatnonzero(ok2)
            if len(j2) < 20:
                continue
            dcl = AV.deciles(np.where(ok2, R4[:, w], np.nan)); dd = dcl[j2]; y2 = Rm[j2, w]
            smm = np.bincount(dd, weights=y2, minlength=10); ct = np.bincount(dd, minlength=10); co = ct[dd] - 1
            x2[j2, w] = np.where(co > 0, y2 - (smm[dd] - y2) / np.maximum(co, 1), np.nan)
        X1[k] = x1; X2[k] = x2
    rows = []
    for i, r in enumerate(res):
        s = r[0]; d = _W["ST"][s]
        for sg in SIGS:
            for dd, w in r[5][sg]:
                rr = {"sid": s, "i": i, "訊號": sg, "d": dd, "w": w, "段": segw[w], "月": month[w], "idx": "400" if d["m4"][dd] else "500"}
                for k in KS:
                    rr["R%d" % k] = RK[k][i, w]; rr["X1_%d" % k] = X1[k][i, w]; rr["X2_%d" % k] = X2[k][i, w]
                rows.append(rr)
    SG = pd.DataFrame(rows)
    print("[A3-8] 訊號 {}｜週 K 低為 NaN 的週 {}｜{:.0f}s".format(len(SG), nanlow, time.time() - t0), flush=True)
    seg_w0 = {sg_: int(np.flatnonzero(segw == sg_)[0]) for sg_ in SEGS}
    seg_ws = {sg_: np.flatnonzero(segw == sg_) for sg_ in SEGS}
    # 格表
    cells = []
    for col in COLS:
        for seg in SEGS:
            for sg in SIGS:
                g = SG[(SG["訊號"] == sg) & (SG["段"] == seg) & gm(SG["idx"], col)] if len(SG) else SG
                for k in KS:
                    gg = g[np.isfinite(g["X2_%d" % k])] if len(g) else g
                    blocks = len(set(((gg["w"].to_numpy() - seg_w0[seg]) // k).tolist())) if len(gg) else 0
                    neff = int(min(len(gg), blocks))
                    cells.append({"欄": col, "段": seg, "訊號": sg, "k": k, "段內訊號": int(len(g)), "n": int(len(gg)), "n_eff": neff, "出口": exit_of(neff)})
    CC = pd.DataFrame(cells)
    kseg = CC[CC["出口"] != "出口①"].groupby(["欄", "段"]).size().to_dict()
    out = {}
    for ci, r in CC.iterrows():
        col, seg, sg, k = r["欄"], r["段"], r["訊號"], r["k"]
        kk = max(kseg.get((col, seg), 1), 1)
        z = NormalDist().inv_cdf(1 - 0.025 / kk)
        g = SG[(SG["訊號"] == sg) & (SG["段"] == seg) & gm(SG["idx"], col)] if len(SG) else SG
        g2 = g[np.isfinite(g["X2_%d" % k])] if len(g) else g
        cell = {"n": int(r["n"]), "n_eff": int(r["n_eff"]), "出口": r["出口"], "Bonferroni_k": int(kk), "z": f6(z)}
        if len(g2) >= 2:
            c2 = cstats(g2["X2_%d" % k], g2["月"], z)
            g1 = g[np.isfinite(g["X1_%d" % k])]; c1 = cstats(g1["X1_%d" % k], g1["月"], z)
            cell.update({"②D": f6(c2["D"]), "②lo": f6(c2["lo"]), "②hi": f6(c2["hi"]), "②lo95": f6(c2["lo95"]), "②hi95": f6(c2["hi95"]),
                         "②毛R": f6(g2["R%d" % k].mean()), "①D": f6(c1.get("D", np.nan)), "①n": c1.get("n", 0),
                         "②結果": band(c2["lo"], c2["hi"]) if r["出口"] != "出口①" else "出口①（不可判定）",
                         "①結果": (band(c1["lo"], c1["hi"]) if (r["出口"] != "出口①" and c1.get("n", 0) > 1) else "—")})
            # 假訊號
            rng = np.random.default_rng([20260928, SIGS.index(sg), k, SEGS.index(seg), COLS.index(col)])
            ii = g2["i"].to_numpy()
            pools = {}
            for i in np.unique(ii):
                pools[i] = seg_ws[seg][np.isfinite(X2[k][i, seg_ws[seg]])]
            sizes = np.array([len(pools[i]) for i in ii])
            okp = sizes > 0
            fx, fm, means = [], [], []
            for rep in range(REPS):
                pick = (rng.random(len(ii)) * np.maximum(sizes, 1)).astype(int)
                wsel = np.array([pools[i][p] if len(pools[i]) else -1 for i, p in zip(ii, pick)])
                xs = np.array([X2[k][i, w_] for i, w_ in zip(ii[okp], wsel[okp])])
                means.append(float(xs.mean()) if len(xs) else np.nan); fx.append(xs); fm.extend(month[wsel[okp]])
            cf = cstats(np.concatenate(fx), np.array(fm), z)
            cell.update({"假D": f6(cf.get("D", np.nan)), "假結果": band(cf["lo"], cf["hi"]) if cf.get("n", 0) else "—",
                         "假p": f6(float(np.nanmean(np.array(means) >= c2["D"])))})
        else:
            cell.update({"②結果": "出口①（不可判定）" if r["出口"] == "出口①" else "—", "假結果": "—"})
        cell["通過"] = bool(cell.get("②結果") == "測得出（＋）" and cell.get("假結果") != "測得出（＋）")
        out[(col, seg, sg, k)] = cell
    # 穩（相鄰 k）
    for (col, seg, sg, k), c in out.items():
        res_ = str(c.get("②結果", ""))
        if not res_.startswith("測得出"):
            continue
        j = KS.index(k); nb = [KS[x] for x in (j - 1, j + 1) if 0 <= x < len(KS)]
        same = [str(out[(col, seg, sg, q)].get("②結果")) == res_ for q in nb]
        c["穩"] = "穩" if all(same) else ("方向一致，但只有 {} 週過門檻".format(k) if not any(same) else "部分相鄰過")
    # 格標籤（確認段）
    glab = {}; tri = {}
    for sg in SIGS:
        for k in KS:
            cc, c4, c5 = out[("合併", "確認", sg, k)], out[("只400", "確認", sg, k)], out[("只500", "確認", sg, k)]
            name = "{}_k{}".format(sg, k)
            if cc["出口"] == "出口①":
                lab = "不可判定（確認段合併 n_eff＝{}＜30，依構造）".format(cc["n_eff"])
            elif cc["通過"] and c4["通過"]:
                lab = "合格"
            elif cc["通過"]:
                lab = "事後擴母體" + ("（只 S&P 400 確認段 n_eff＜30，依構造最多事後擴母體）" if c4["出口"] == "出口①" else "")
            else:
                lab = "不合格"
            glab[name] = lab

            def one(c):
                if c.get("②D") is None:
                    return "{}（n {}、n_eff {}）".format(c.get("②結果"), c["n"], c["n_eff"])
                return "D {}（Bonferroni CI {}～{}；n {}、n_eff {}）{}｜{}｜假訊號 {}".format(
                    pctf(c["②D"]), pctf(c["②lo"]), pctf(c["②hi"]), c["n"], c["n_eff"], c["出口"], c["②結果"], c.get("假結果"))
            tri[name] = {"合併": one(cc), "只400": one(c4), "只500": "（描述）" + one(c5)}
    cnt = Counter(v.split("（")[0] for v in glab.values())
    order = ["合格", "事後擴母體", "不合格", "不可判定"]
    best = next((o for o in order[:2] if cnt.get(o)), None)
    item_lab = (best + "（{}）".format("、".join(k for k, v in glab.items() if v.startswith(best)))) if best else (
        "不合格" if cnt.get("不合格") else "不可判定（全部格依構造）")
    summary = "16 格：" + "、".join("{} {}".format(o, cnt.get(o, 0)) for o in order)
    # ret50 敏感度：訊號持有期 [第 w 週首日, 出場日] 碰到未確認列 ⇒ 剔除，重判確認段
    f50c = {}
    for k in KS:
        flag = []
        for rr in SG.itertuples():
            d = _W["ST"][rr.sid]; x = wl[min(rr.w + k, nw - 1)]
            flag.append(bool(d["f50"][wf[rr.w]:x + 1].any()))
        f50c[k] = np.array(flag, bool)
    sens = {}
    for sg in SIGS:
        for k in KS:
            rr = {}
            for col in ("合併", "只400"):
                msk = (SG["訊號"] == sg).to_numpy() & (SG["段"] == "確認").to_numpy() & gm(SG["idx"], col) & ~f50c[k] & np.isfinite(SG["X2_%d" % k].to_numpy())
                g2 = SG[msk]; c = out[(col, "確認", sg, k)]
                if len(g2) >= 2 and c["出口"] != "出口①":
                    c2 = cstats(g2["X2_%d" % k], g2["月"], c["z"]); rr[col] = band(c2["lo"], c2["hi"])
                else:
                    rr[col] = c.get("②結果")
            sens["{}_k{}".format(sg, k)] = rr
    nchg = 0
    for sg in SIGS:
        for k in KS:
            a_ = sens["{}_k{}".format(sg, k)]["合併"] == "測得出（＋）"
            b_ = out[("合併", "確認", sg, k)].get("②結果") == "測得出（＋）"
            nchg += int(a_ != b_)
    wkf = write_work("A3-8_signals.csv.gz", SG)
    cells_json = {"{}|{}|{}_k{}".format(c, s_, g, k): v for (c, s_, g, k), v in out.items()}
    passed_names = [k for k, v in glab.items() if v.startswith("合格") or v.startswith("事後擴母體")]
    nusable = sum(1 for v in glab.values() if v.startswith("合格"))
    s4 = glab.get("S4_k26")
    prior = ("台股原押：① 甲 16 格「可用」0 格（約六成五）⇒ 美股合格 {} 格 ⇒ {}；最接近的是 S4 26 週（約四成）⇒ 美股 S4_k26 {}；"
             "② S1～S3 在基準②下多數測不出（約七成）⇒ 美股確認段合併 S1～S3 可判定格中測不出 {}／{} ⇒ {}。").format(
        nusable, "押中" if nusable == 0 else "沒押中", s4,
        sum(1 for sg in ("S1", "S2", "S3") for k in KS if out[("合併", "確認", sg, k)].get("②結果") == "測不出"),
        sum(1 for sg in ("S1", "S2", "S3") for k in KS if out[("合併", "確認", sg, k)]["出口"] != "出口①"),
        "押中" if sum(1 for sg in ("S1", "S2", "S3") for k in KS if out[("合併", "確認", sg, k)].get("②結果") == "測不出") * 2 >
        sum(1 for sg in ("S1", "S2", "S3") for k in KS if out[("合併", "確認", sg, k)]["出口"] != "出口①") else "沒押中")
    sent = ("{}：{}。確認段（2022-01～2026-09）基準②（前 4 週報酬同十分位）扣成本帶 0.05%、Bonferroni；過的格：{}。"
            "k12、k26 在確認段只有約 21、10 個不重疊區段 ⇒ 依構造不可判定。{}；{}；{}。").format(
        item_lab, summary, "、".join(passed_names) if passed_names else "無", K.IDEA, K.NO_EARLY, K.SURV)
    card = {"件": "A3-8", "名稱": "週線訊號單測（S1～S4 × k{4,8,12,26} 週）", "台股原登錄": TWREG["A3-8"],
            "出場型": "③ 事件＋（原文 k 週持有＝格、各自判，seq319 Q3）", "N": 16, "標籤": item_lab, "格標籤": glab,
            "判定格": "16 格各自判（確認段、基準②、成本帶、Bonferroni、假訊號臂不過）", "三欄": {
                "合併": "；".join("{} {}".format(k, v["合併"]) for k, v in tri.items()),
                "只400": "；".join("{} {}".format(k, v["只400"]) for k, v in tri.items()),
                "只500": "（描述、⛔ 不判）" + "；".join("{} {}".format(k, v["只500"]) for k, v in tri.items())},
            "條件出場必報": None, "結果句": sent,
            "敏感度_ret50": "剔除持有期碰到 |ret|＞50% 未確認列的訊號後，確認段合併「測得出（＋）」與否改變的格數 {}／16".format(nchg),
            "偏離": ["基準① eligible 等權 → 合併母體等權；基準② 前 4 週報酬十分位 → 合併母體；週內硬斷點 → 轉接層 hard_break＋缺 K 棒",
                   "早年段拿掉（seq319 Q1：只看確認段；可用條件的「早年同向」拿掉）；乙件（營量週收盤出場）不搬",
                   "暖機照 prep P14（週 K 位置 ≥35；原程式 A1 為 52）；成本帶 0.585% → 0.05%（美股成本）",
                   "n_eff 照原程式 A6（段內 k 週區段數），不用清單的全窗曆月上限 ⇒ k12、k26 確認段依構造出口①（N 仍 16，照清單與 seq319 Q3）",
                   "Bonferroni k 與假訊號種子按欄各自算（三欄各下一次原規則）"],
            "補讀法": ["G1～G6、WKa～WKf（docstring，寫死於 {}）".format(READ_TS)], "先驗紀錄": prior}
    return {"卡片": card, "依據": K.REG, "讀法寫死": READ_TS, "資料commit": _W["meta"].get("data_commit"),
            "格": cells_json, "三欄_確認段": tri, "敏感度_ret50_確認段": sens, "週K低為NaN的週數": nanlow,
            "逐筆中間檔": {"訊號": wkf}, "存活者偏差": K.SURV}


# ═════════════════════════ run ═════════════════════════
def run(procs=2, lim=None, only=None):
    t0 = time.time()
    meta, ST, SK, sids = setup(lim)
    print("[g1] 快取 {} 檔｜窗 {}～{}｜{:.0f}s".format(len(sids), meta["cal"][meta["w0"]].date(), meta["cal"][meta["w1"]].date(), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True); os.makedirs(GW, exist_ok=True)
    only = only or ["A3-1", "A3-2", "A3-4", "A3-8"]
    sfx = "" if lim is None else "_lim%d" % lim
    done = {}
    if "A3-1" in only:
        M = mats(sids); J = run_h1(procs, sids, M); del M
        K.jdump(J, os.path.join(OUT if lim is None else GW, "A3-1%s.json" % sfx)); done["A3-1"] = J["卡片"]["標籤"]
    if "A3-2" in only:
        J = run_h2(procs, sids); K.jdump(J, os.path.join(OUT if lim is None else GW, "A3-2%s.json" % sfx)); done["A3-2"] = J["卡片"]["標籤"]
    if "A3-4" in only:
        J = run_ut(procs, sids); K.jdump(J, os.path.join(OUT if lim is None else GW, "A3-4%s.json" % sfx)); done["A3-4"] = J["卡片"]["標籤"]
    if "A3-8" in only:
        J = run_wk(procs, sids); K.jdump(J, os.path.join(OUT if lim is None else GW, "A3-8%s.json" % sfx)); done["A3-8"] = J["卡片"]["標籤"]
    print("[g1] 完成 {}｜{:.0f}s".format(done, time.time() - t0), flush=True)
    return done


# ═════════════════════════ check（⭐ 獨立寫法：不呼叫上面任何算事件、報酬、基準、統計的函式）═════════════════════════
def _ck_last_close(c, j):
    while j >= 0 and not np.isfinite(c[j]):
        j -= 1
    return c[j] if j >= 0 else np.nan


def _ck_brk(d, a, b):
    """[a, b] 內有 hard_break，或（該股第一～最後一根有效 K 棒之間）有沒有有效 K 棒的日子。"""
    a = max(a, 0); b = min(b, len(d["valid"]) - 1)
    vb = np.flatnonzero(d["valid"]); f, l = vb[0], vb[-1]
    for t in range(a, b + 1):
        if d["pb"][t]:
            return True
        if f <= t <= l and not d["valid"][t]:
            return True
    return False


def _ck_okO(d, t):
    return bool(d["valid"][t] and np.isfinite(d["O"][t]) and d["O"][t] > 0)


def _ck_D(x, mon):
    """平均與曆月分群 SE（獨立寫）。"""
    x = np.asarray(x, float); m = np.asarray(mon)
    mu = x.mean(); s = {}
    for v, k in zip(x - mu, m):
        s[k] = s.get(k, 0.0) + v
    se = np.sqrt(sum(v * v for v in s.values())) / len(x)
    return mu, se


def check(lim=None):
    meta, ST = K.load_cache(lim)
    cal = meta["cal"]; w0, w1 = meta["w0"], meta["w1"]; n = len(cal)
    sids = sorted(ST)
    src = OUT if lim is None else GW
    sfx = "" if lim is None else "_lim%d" % lim
    rng = np.random.default_rng(777)
    out = []
    TOL = 1e-8
    # ── A3-1 ──
    try:
        J = json.load(open(os.path.join(src, "A3-1%s.json" % sfx), encoding="utf-8"))
        E = pd.read_csv(os.path.join(GW, "A3-1_events_H20.csv.gz"))
        smp = E.iloc[rng.choice(len(E), size=min(150, len(E)), replace=False)]
        bad = 0; notes = []
        for r in smp.itertuples():
            d = ST[r.sid]; c = d["C"]; T = int(r.T); vb = np.flatnonzero(d["valid"]); p = int(np.searchsorted(vb, T))
            sma = lambda q: float(np.mean(c[vb[q - 19:q + 1]]))
            ev_ok = sma(p) > sma(p - 5) and c[T] < sma(p) and c[vb[p - 1]] >= sma(p - 1)
            grp = int(any(c[T + s_] >= sma(int(np.searchsorted(vb, T + s_))) for s_ in (1, 2, 3)))
            e = T + 4
            R = _ck_last_close(c, T + 23) / d["O"][e] - 1
            tot = 0.0; k_ = 0
            for s2 in sids:
                d2 = ST[s2]
                if not (d2["member"][e] and _ck_okO(d2, e)) or d2["pb"][e + 1:e + 20].any():
                    continue
                tot += _ck_last_close(d2["C"], e + 19) / d2["O"][e] - 1; k_ += 1
            X = R - tot / k_
            if not (ev_ok and grp == r.站回 and abs(R - r.R) < TOL and abs(X - r.X) < TOL):
                bad += 1; notes.append((r.sid, T))
        e_ = E
        Dm = e_[e_["站回"] == 1]["X"].mean() - e_[e_["站回"] == 0]["X"].mean()
        Dj = J["三欄"]["合併"]["判定"].get("D")
        bad += int(Dj is None or abs(Dm - Dj) > 1e-6)
        out.append({"件": "A3-1", "抽樣": int(len(smp)) + 1, "不同": int(bad),
                    "說明": "抽 {} 筆事件獨立重算 SMA20 事件條件、站回分組、R、合併母體收盤基準（逐檔迴圈）與 X；另以兩組平均差重算合併 D（{} vs json {}）；不同：{}".format(
                        len(smp), round(Dm, 8), Dj, notes[:5])})
    except Exception as ex:                                  # noqa
        out.append({"件": "A3-1", "錯誤": repr(ex)})
    # ── A3-2 ──
    try:
        J = json.load(open(os.path.join(src, "A3-2%s.json" % sfx), encoding="utf-8"))
        E = pd.read_csv(os.path.join(GW, "A3-2_events_H20.csv.gz"), keep_default_na=False, na_values=[""])
        smp = E.iloc[rng.choice(len(E), size=min(100, len(E)), replace=False)]
        bad = 0; notes = []

        def outc(d, t):
            if _ck_brk(d, t + 1, t + 20) or not _ck_okO(d, t + 1):
                return None
            hh = d["H"][t + 1:t + 21]
            return int(np.nanmax(hh) >= 1.3 * d["O"][t + 1] * (1 - 1e-12))
        for r in smp.itertuples():
            d = ST[r.sid]; c = d["C"]; t = int(r.t); vb = np.flatnonzero(d["valid"]); p = int(np.searchsorted(vb, t))
            ma = lambda L, q: float(np.mean(c[vb[q - L + 1:q + 1]]))
            mx0 = max(ma(144, p), ma(200, p)); mx1 = max(ma(144, p - 1), ma(200, p - 1))
            sig = ma(144, p) > ma(144, p - 5) and ma(200, p) > ma(200, p - 5) and c[t] >= mx0 and c[vb[p - 1]] < mx1
            h = outc(d, t)
            ch = [outc(ST[s2], t) for s2 in str(r.picks).split(";") if s2 and s2 != "nan"]
            ch = [x for x in ch if x is not None]
            cm = float(np.mean(ch)) if ch else np.nan
            same_c = (len(ch) == r.n_ctl) and ((not ch and not np.isfinite(r.ctl_hit)) or abs(cm - r.ctl_hit) < TOL)
            if not (sig and h == r.hit and same_c):
                bad += 1; notes.append((r.sid, t))
        ok = E[E["n_ctl"] > 0]
        Dm = float((ok["hit"] - ok["ctl_hit"]).mean()); Dj = J["三欄"]["合併"]["判定"].get("D")
        bad += int(Dj is None or abs(Dm - Dj) > 1e-6)
        out.append({"件": "A3-2", "抽樣": int(len(smp)) + 1, "不同": int(bad),
                    "說明": "抽 {} 筆事件獨立重算 MA144／200 雙翻揚首次站上條件、hit（×1.3）、所抽 10 檔對照各自的成交與 hit；另以逐筆平均重算合併 D（{} vs json {}）；不同：{}".format(
                        len(smp), round(Dm, 8), Dj, notes[:5])})
    except Exception as ex:                                  # noqa
        out.append({"件": "A3-2", "錯誤": repr(ex)})
    # ── A3-4 ──
    try:
        J = json.load(open(os.path.join(src, "A3-4%s.json" % sfx), encoding="utf-8"))
        E = pd.read_csv(os.path.join(GW, "A3-4_events_main.csv.gz"))
        smp = E.iloc[rng.choice(len(E), size=min(150, len(E)), replace=False)]
        bad = 0; notes = []

        def pxj(d, j):
            return d["O"][j] if _ck_okO(d, j) else _ck_last_close(d["C"], j)
        for r in smp.itertuples():
            d = ST[r.sid]; T = int(r.T); c = d["C"]; l = d["L"]; vb = np.flatnonzero(d["valid"])
            bT = int(np.searchsorted(vb, T)); b1 = int(np.searchsorted(vb, int(r.first))); bc = int(np.searchsorted(vb, int(r.conf))); b2 = bc - 5
            lb = l[vb]; cbb = c[vb]
            piv = all(lb[b1] < lb[b1 + q] and lb[b1] < lb[b1 - q] for q in range(1, 6)) and all(lb[b2] < lb[b2 + q] and lb[b2] < lb[b2 - q] for q in range(1, 6))
            slope = (lb[b2] - lb[b1]) / (b2 - b1)
            line = lambda b: lb[b1] + slope * (b - b1)
            brk_ok = piv and slope > 0 and cbb[bT] < 0.99 * line(bT) and cbb[bT - 1] >= 0.99 * line(bT - 1)
            g = pxj(d, T + 21) / d["O"][T + 1] - 1
            tot = 0.0; k_ = 0; dd = T + 1
            for s2 in sids:
                d2 = ST[s2]
                if not (d2["member"][dd] and _ck_okO(d2, dd)) or d2["pb"][dd + 1:dd + 21].any():
                    continue
                tot += pxj(d2, dd + 20) / d2["O"][dd] - 1; k_ += 1
            X = g - tot / k_
            if not (brk_ok and abs(g - r.g) < TOL and abs(X - r.X) < TOL):
                bad += 1; notes.append((r.sid, T, bool(brk_ok)))
        mu, se = _ck_D(E["X"], [str(cal[t])[:7] for t in E["T"]])
        Jm = J["三欄"]["合併"]["判定"]
        bad += int(abs(mu - Jm["平均"]) > 1e-6 or abs((mu - 1.96 * se) - Jm["lo"]) > 1e-6)
        out.append({"件": "A3-4", "抽樣": int(len(smp)) + 1, "不同": int(bad),
                    "說明": "抽 {} 筆主格事件獨立重算樞紐低點（R＝5 嚴格）、兩點線 1% 穿越、g、合併母體開盤基準（逐檔迴圈）與 X；另獨立重算合併平均與月分群 CI 下緣（{} vs json {}）；不同：{}".format(
                        len(smp), round(mu, 8), Jm["平均"], notes[:5])})
    except Exception as ex:                                  # noqa
        out.append({"件": "A3-4", "錯誤": repr(ex)})
    # ── A3-8 ──
    try:
        J = json.load(open(os.path.join(src, "A3-8%s.json" % sfx), encoding="utf-8"))
        E = pd.read_csv(os.path.join(GW, "A3-8_signals.csv.gz"))
        monday = (cal - pd.to_timedelta(cal.weekday, unit="D")).normalize()
        wid = pd.factorize(monday)[0]; nwk = wid.max() + 1
        first = np.full(nwk, -1); lastd = np.full(nwk, -1)
        for i_, w_ in enumerate(wid):
            if first[w_] < 0:
                first[w_] = i_
            lastd[w_] = i_

        def Rk(d, w, k):
            vw = np.flatnonzero(d["valid"][first[w]:lastd[w] + 1])
            if len(vw) == 0 or w + k >= nwk:
                return np.nan
            e, x = first[w + 1], lastd[w + k]
            if x > w1 or not _ck_okO(d, e) or _ck_brk(d, first[w], x):
                return np.nan
            return _ck_last_close(d["C"], x) / d["O"][e] - 1

        def inpool(d, w):
            vw = np.flatnonzero(d["valid"][first[w]:lastd[w] + 1])
            return len(vw) > 0 and bool(d["member"][first[w] + vw[-1]])
        smp = E.iloc[rng.choice(len(E), size=min(40, len(E)), replace=False)]
        bad = 0; notes = []; ncmp = 0
        for r in smp.itertuples():
            k = int(rng.choice(KS)); w = int(r.w)
            vals = []
            for s2 in sids:
                d2 = ST[s2]
                if not inpool(d2, w):
                    continue
                rr = Rk(d2, w, k)
                if not np.isfinite(rr):
                    continue
                c2 = d2["C"]
                a_, b_ = _ck_last_close(c2, lastd[w]), (_ck_last_close(c2, lastd[w - 4]) if w >= 4 else np.nan)
                vals.append((s2, rr, a_ / b_ - 1 if (np.isfinite(a_) and np.isfinite(b_)) else np.nan))
            V = pd.DataFrame(vals, columns=["s", "R", "r4"]).astype({"R": float, "r4": float})
            mine = V[V["s"] == r.sid]
            Rm = float(mine["R"].iloc[0]) if len(mine) else np.nan
            x1 = (Rm - (V["R"].sum() - Rm) / (len(V) - 1)) if (len(mine) and len(V) >= 20) else np.nan
            V2 = V[np.isfinite(V["r4"])].reset_index(drop=True)
            x2 = np.nan
            if len(mine) and len(V2) >= 20 and np.isfinite(mine["r4"].iloc[0]):
                order = sorted(range(len(V2)), key=lambda q: (V2["r4"][q], sids.index(V2["s"][q])))
                dec = {V2["s"][q]: (rank * 10) // len(V2) for rank, q in enumerate(order)}
                same = [q for q in range(len(V2)) if dec[V2["s"][q]] == dec[r.sid] and V2["s"][q] != r.sid]
                x2 = Rm - float(np.mean([V2["R"][q] for q in same])) if same else np.nan
            want = (getattr(r, "R%d" % k), getattr(r, "X1_%d" % k), getattr(r, "X2_%d" % k))
            got = (Rm, x1, x2)
            ncmp += 1
            if not all((np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) < TOL) for a, b in zip(want, got)):
                bad += 1; notes.append((r.sid, w, k))
        # 一格 D 與 n（合併、確認、S2、k4）
        g = E[(E["訊號"] == "S2") & (E["段"] == "確認") & np.isfinite(E["X2_4"])]
        mu, se = _ck_D(g["X2_4"], g["月"])
        c = J["格"]["合併|確認|S2_k4"]
        bad += int(c.get("②D") is None or abs(mu - c["②D"]) > 1e-6 or len(g) != c["n"])
        out.append({"件": "A3-8", "抽樣": ncmp + 1, "不同": int(bad),
                    "說明": "抽 {} 個訊號（各隨機一個 k）獨立重算週 K 分週、R_k、同週合併母體等權（基準①）與前 4 週十分位（基準②，自寫排序）；另獨立重算 合併｜確認｜S2_k4 的 n 與 D（{} vs json {}）；不同：{}".format(
                        ncmp, round(mu, 8), c.get("②D"), notes[:5])})
    except Exception as ex:                                  # noqa
        out.append({"件": "A3-8", "錯誤": repr(ex)})
    return out


if __name__ == "__main__":
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    if "--run" in sys.argv:
        run(procs, lim, only)
    if "--check" in sys.argv:
        print(json.dumps(check(lim), ensure_ascii=False, indent=1, default=str))

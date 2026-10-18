# -*- coding: utf-8 -*-
"""布林通道 Method I（擠壓後突破）、Method II（%b 配 MFI 順勢）seq1【事件層正式跑】（台股策略線 單筆層登錄 sha d5ac888e15ab1418，
2026-10-18 11:08；裁定 seq371 §一、seq372 發號；N_前段 ＋2）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchBB_freq（事件偵測、布林、剔除）、researchWR_freq（base、段）、researchUO（Sampler、verdict、
   agg_eval、diff_stats、_nxt）、researchTurtle（x_stats：Bonferroni 族 N＝2 同式、NOTE_EARLY）、researchAscTri_freq、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBB [--procs 2]
    乾跑（⛔ 不算任何出場、報酬；只驗事件重現與對照池）：... -m backtest.researchBB --dry [--limit 200]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBB_check
輸出 backtest/resultsBB/（⛔ 不碰 freq/）：BB.json、BB_main.csv（判定表＋分報）、BB_desc.csv（固定天數描述）、by_year.csv、fake_reps.csv、
    events/trades_<世界>_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：M1、M2 ＝ 判定格（登錄 §二）；M1_收盤判 ＝ 裁定 seq372「收盤判版並報」（＝登錄 §三 描述「M1 收盤判隔天開盤出場版」）；
    另一讀法（只報）：M1_當日下軌（H3）；描述（⛔ 不判、不計 N）：M3（Method III）、M1／M2 固定抱 20／60 日、假訊號臂（30 次隨機日當 T）。
    （M2 的出場本來就是收盤判、隔天開盤 ⇒「M2 收盤判版」≡ M2 判定格，不另列。）

═══ 讀法（H 標；頻率表 B1～B9 原樣沿用（世界、母體、壞根、布林、MFI、擠壓、偵測、剔除、段），以下為正式跑新增；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 H1 事件 ＝ 逐股呼叫 researchBB_freq.stock_job 原樣；⭐ 依頻率表寫法排成表、與已提交的 resultsBB/freq/events_<世界>.csv.gz 逐列逐欄比
    （M1、M2、M3），任一不同 ⇒ 中止、⛔ 不算報酬。進場候選 ＝ 狀態「保留」者；進場 ＝ T＋1 開盤（還原開盤 o[k＋1]）。
    ★ 另需 T 當根 20 根布林窗有值（M1、M2、M3 依構造必有）與還原開盤有值且 ＞ 0，否則剔除「指標或開盤缺值」並計數。
 H2 SAR（登錄 §一、§二；Wilder 多方規則，只做多、碰到即出場、不反手）：
    起點 SAR[s] ＝ 進場前 20 個有效 K 棒的最低價 ＝ min(l[s−20..s−1]) ＝ min(l[k−19..k])（⭐ 本線定；s ＝ 進場根 ＝ k＋1；布林窗有值 ⇒ 這 20 根必相連）。
    ★ EP 起始 ＝ 進場當根最高 h[s]、AF 起始 0.02（進場當根不加速）；之後每根 j（j ≥ s＋1）未出場時：h[j] ＞ EP ⇒ EP ＝ h[j]、AF ＝ min(AF＋0.02, 0.20)
    （AF ＝ 0.02 × 次數，避免累加誤差）；明日 SAR[j＋1] ＝ min(SAR[j] ＋ AF ×（EP − SAR[j]）, l[j], l[j−1])
    （★「SAR 不得高於今昨兩根最低」為 Wilder 原規則，照用；上限 0.20 為常見轉述值，seq371 照用）。SAR[j] 只用 ≤ j−1 的資料 ⇒ 盤前已知。
 H3 M1 出場（登錄 §二，盤中觸價，判定格）：持有中第 j 根（★ j ≥ s，含進場當根：開盤買在當日一切成交之前，當日最低必在買進之後）
    SAR 觸價：l[j] ≤ SAR[j]；碰下軌：l[j] ≤ 下軌。★ 下軌用【前一根收盤算出的下軌】lo[j−1]（盤前已知；當根下軌含當日收盤、盤中不可知）
    〔另一讀法 M1_當日下軌：用 lo[j]，只報〕。出場價 ＝ min(開盤, 觸到的價位)。
    ★ 同一根兩者都觸：開盤在兩價位之上時，價格由開盤一路到最低必先經過較高的價位 ⇒「先到者」＝ 較高者，出場價 ＝ min(開, 較高價位)，
    種類記較高者（相等記 SAR）；另計「同根皆觸」筆數。開盤缺值 ⇒ 用觸價價位並計數。開盤 ≤ 價位 ⇒ 開盤賣（含進場當根 ⇒ R ＝ 0，計「進場當根出場」）。
 H4 M1_收盤判（seq372 並報）：同一批進場、同 SAR 路徑；第 j 根（j ≥ s）收盤 ≤ SAR[j] 或 收盤 ≤ 當根下軌 lo[j] ⇒ 第 j＋1 根開盤賣
    （★ 與 H3 的「≤」對稱；收盤已知 ⇒ 用當根下軌）。種類：兩者皆成立記較高價位者（相等記 SAR）。
    「盤中觸價對收盤判的差」＝ X̄(M1) − X̄(M1_收盤判)，SE ＝ 曆月分群線性化（researchUO.diff_stats；兩組持有限制各自套、筆數可不同）。
 H5 M2 出場（登錄 §二，⭐ 本線定）：第 j 根（j ≥ s，含進場當天收盤）收盤 ＜ 中軌[j]（嚴格）⇒ 第 j＋1 根開盤賣。⛔ 不對稱補 0.2／20。
 H6 跌停鎖死順延（登錄 §二）：盤中觸價的觸發根、或收盤判的賣出根是開盤鎖死跌停（W.DNL）⇒ 順延到其後第一根非鎖死有效 K 棒開盤賣
    （開盤缺 ⇒ 收盤）；途中遇壞 K 棒 ⇒ 壞 K 棒前一根收盤強制；順延到資料外 ⇒ 照 H7。種類不變、另記「順延」（researchTurtle G4 同）。
 H7 壞根、下市、資料尾（researchUO E3／researchTurtle G5 同）：持有中下一根是壞 K 棒 ⇒ 以其前一根還原收盤強制出場（收盤判訊號在第 j 根、
    第 j＋1 根就是壞 K 棒 ⇒ 第 j 根收盤強制）；之後再無成交且最後一根距資料尾 ≥ 5 交易日 ⇒ 最後一根收盤出場（末根＝下市／長期停牌）；
    否則「資料尾未出場」：照實報件數與帳面報酬，⛔ 不進 X。
 H8 R ＝ 出場價 ÷ 買價 − 1；淨報酬 ＝ R − 0.585%；X ＝ R − 對照平均 R（兩邊同扣成本）。持有天數 ＝ 出場日 − 進場日（交易日曆位置差）。
 H9 持有中不重複進場（登錄 §二）：同檔保留事件依 T 排序；前筆賣出日 S（日曆位置）；★ 新事件需 T ≥ S（T＋1 開盤買在賣出日之後，researchUO E5 同）
    〔另一讀法 T ＞ S〕；前筆資料尾未出場 ⇒ 之後全部略過。整個世界時序上套；各格（含收盤判、另一讀法、M3）各自用自己的出場日套。
    M1 偵測為「擠壓後 20 根內每根收盤在上軌之上」（B4）⇒ 持有中的偵測被略過；出場後窗內再站上上軌可再進場（登錄沒寫「第一天」）。
 H10 對照（登錄 §三）：同一天 T、同母體隨機 20 檔、同進場時點（T＋1 開盤）、同出場規則（各用自己的通道、SAR、中軌）。
    池 ＝ Frame.gate[T] ∧ pit_valid[T] ∧ T 非壞 K 棒 ∧ T＋1 可買（下一根 ＝ 日曆 T＋1、非壞、有成交、開盤有值 ＞ 0、非開盤鎖漲停 ＝ B1 同旗標）
    ∧ T 當根布林窗有值（★ 出場要用自己的軌道與 SAR 起點）∧ R 可算。★ 扣掉事件股自己與 T 當天同格【原始】偵測到的股票（任何狀態；
    researchUO E6、researchTurtle G8 同）；不放回抽 20 檔（不足 ⇒ 全取、計數）；等權平均；⛔ 對照不套持有限制。
    種子 default_rng([20261018, 格標, T, crc32(sid)])；格標 M1＝1、M2＝2、M3＝3、M1_收盤判＝11、M1_當日下軌＝12、固定抱 ＝ 格×100＋H。
 H11 判定量 X̄；CI ＝ T 所在曆月分群（research11.cl_stats）、1.96；n_eff ＝ min(可算筆數, 有事件曆月數)；n_eff ＜ 30 ⇒ 依構造不可判定、
    30～99 ⇒ 句首「樣本中等」；結果② ＝ CI 不含 0 且 X̄ ＞ 0、③ ＝ X̄ ＜ 0 且 CI 不含 0、① ＝ 含 0。
    判定段：探索、確認【各自報】為準；主全窗參考；早年 2005～2014 描述（附 reduce_v2 約 0.3% 註）。Bonferroni 族 N＝2（z ＝ 2.2414）。
 H12 seq322（researchTurtle G10 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；各段各報。
 H13 假訊號臂（researchTurtle G11／researchUO E10 同式）：r ＝ 0…29；每檔每段 n ＝ 該檔該格可算筆數；可抽日 ＝ 該檔在段內且在 H10 對照池；
    排除「存在該檔同格保留事件 T_r ∈ [T−20, T]」的日子；不放回抽 n 天；假事件 R ＝ 對照式 R（T＋1 開盤進場、同出場）；對照照 H10；
    種子 default_rng([20261019＋r, crc32(sid), 段序號])，假事件的對照 [20261018, 5000＋100×格號＋r, T, crc32(sid)]；x／30 ＝ 落結果② 的次數。⛔ 不套持有限制。
 H14 描述：M3 ＝ 頻率表 M3 事件（B8 操作化）；★ 出場用 M1 的規則（SAR 起點前 20 日最低＋碰前一根下軌、盤中觸價；原作 Method III 無出場）
    〔另一讀法：用 M2 的跌破中軌——不做〕。固定抱 H（20／60；登錄 §三 描述）＝ 判定格同一批進場，R_H ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1；
    (T＋1, T＋H] 有壞 K 棒或 T＋H 落在 ≥ 5 日缺口 ⇒ 不可算（researchUO D3 同式）；對照同法抽 20 檔。⛔ 只描述，不當出場比較基準（seq308）。
 H15 必報：每年事件數（可算筆 ÷ 段長；另附頻率表上限）、平均／中位／p90 持有天數、出場種類占比（分母 ＝ 可算筆，另報含資料尾）、
    勝率（淨報酬 ＞ 0）、平均賺賠比（賺錢筆平均淨報酬 ÷ |賠錢筆平均淨報酬|）、假訊號 x／30、seq322。
    措辭照 seq343：「SAR 出場訊號」「碰下軌出場訊號」「跌破中軌出場訊號」；⛔ 不稱最高點、頂部。
 H16 結果句必附（登錄 §四）：「M1 擠壓後 20 日內、SAR 起點用前 20 日最低、M2 收盤跌破中軌出場，三處由本線定」「SAR 上限 0.20 為常見轉述值」
    「原作為網頁轉錄版」「單筆層通過 ≠ 組合會贏 0050」；M1 另附「盤中觸價對收盤判的差」（seq372，比照海龜 ★1）；早年另附 reduce_v2 與上櫃版面註。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchBB_freq as BB                  # noqa: E402  事件偵測、布林（⛔ 只 import）
from backtest import researchWR_freq as WF                  # noqa: E402  base、SEGS、reg_check（⛔ 只 import）
from backtest import researchUO as UO                       # noqa: E402  Sampler、verdict、agg_eval、diff_stats、_nxt（⛔ 只 import）
from backtest import researchTurtle as TU                   # noqa: E402  x_stats（族 N＝2）、NOTE_EARLY（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import research11 as R                        # noqa: E402  cl_stats
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = BB.REG_SHA
OUT = "backtest/resultsBB"
FREQ = BB.OUT
AF0 = 0.02
AF_N = 10                    # AF 上限 0.20 ＝ 0.02 × 10
SAR_LB = 20
SEED_CTRL, SEED_FAKE = 20261018, 20261019
REPS, EXCL = 30, 20
HD = (20, 60)
N_FAM = 2
ZB = TU.ZB
assert TU.N_FAM == N_FAM
COST = E.COST
GAP_END = 5
TYP = {1: "SAR出場訊號", 2: "碰下軌出場訊號", 3: "跌破中軌出場訊號", 4: "壞根前一根收盤強制", 5: "末根收盤(下市/之後無成交)", 6: "資料尾未出場"}
TAIL = 6
# 格 ⇒ (出場模式鍵, 事件來源格)
CELLDEF = {"M1": ("Mi", "M1"), "M2": ("Mm", "M2"), "M1_收盤判": ("Mc", "M1"), "M1_當日下軌": ("Mb", "M1"), "M3": ("Mi", "M3")}
MODES = {"Mi": "i", "Mb": "i", "Mc": "c", "Mm": "m"}
MODE_EV = {"Mi": ("M1", "M3"), "Mb": ("M1",), "Mc": ("M1",), "Mm": ("M2",)}
TAG = {"M1": 1, "M2": 2, "M3": 3, "M1_收盤判": 11, "M1_當日下軌": 12, "M1_H20": 120, "M1_H60": 160, "M2_H20": 220, "M2_H60": 260}
CELLNUM = {"M1": 1, "M2": 2}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
JUDGE = ("M1", "M2")
NAME = {"M1": "布林 Method I（擠壓後 20 日內收盤站上上軌、隔天開盤買；SAR 或碰下軌先到者盤中觸價出場）",
        "M2": "布林 Method II（%b＞0.8 且 MFI(10)＞80、隔天開盤買；收盤跌破中軌隔天開盤出場）",
        "M1_收盤判": "M1 收盤判版（收盤 ≤ SAR 或 ≤ 下軌、隔天開盤出場；seq372 並報）",
        "M1_當日下軌": "另一讀法：M1 碰下軌用當根下軌（只報）",
        "M3": "M3 Method III（W 底＋%b＋MFI 確認；本線操作化；出場同 M1）（描述）"}
SENT_SELF = "M1 擠壓後 20 日內、SAR 起點用前 20 日最低、M2 收盤跌破中軌出場，三處由本線定"
SENT_SAR = "SAR 上限 0.20 為常見轉述值"
SENT_SRC = "原作為網頁轉錄版"
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = TU.NOTE_EARLY
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ H2～H7 出場（向量化；fixture 對逐根迴圈）═════════════
def sim(o, h, l, c, bad, dnlb, idx, n0, S, SAR0, LV, mode):
    """S ＝ 進場根（開盤買）、SAR0 ＝ 各自 SAR 起點、LV ＝ 出場用軌道（逐根陣列）。
    mode 'i'：盤中觸價（l[j] ≤ SAR[j] 或 l[j] ≤ LV[j]）⇒ 當根 min(開, 先到價位)；
    mode 'c'：收盤判（c[j] ≤ SAR[j] 或 c[j] ≤ LV[j]）⇒ 下一根開盤；mode 'm'：收盤判（c[j] ＜ LV[j]）⇒ 下一根開盤（無 SAR）。
    回 dict(eb 出場根, px, typ, post 順延, both 同根皆觸, obad 開盤缺用替代)。"""
    nb = len(c); BIG = nb + 10; m = len(S)
    S = np.asarray(S, np.int64)
    eb = np.full(m, -1, np.int64); px = np.full(m, np.nan); typ = np.zeros(m, np.int8)
    post = np.zeros(m, bool); both = np.zeros(m, bool); obad = np.zeros(m, bool)
    out = {"eb": eb, "px": px, "typ": typ, "post": post, "both": both, "obad": obad}
    if m == 0:
        return out
    dnlb = np.asarray(dnlb, bool); bad = np.asarray(bad, bool)
    nok = UO._nxt(~dnlb, nb, BIG); nbd = UO._nxt(bad, nb, BIG)
    delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
    sar = np.asarray(SAR0, float).copy(); ep = h[S].astype(float).copy(); naf = np.ones(m, np.int64)

    def fin_end(q):
        if delisted:
            eb[q] = nb - 1; px[q] = c[nb - 1]; typ[q] = 5
        else:
            typ[q] = TAIL

    def defer(q, x0, ty):
        y = nok[x0]; b = nbd[x0]
        post[q] = True
        f1 = (b <= y) & (b < nb)
        eb[q[f1]] = b[f1] - 1; px[q[f1]] = c[b[f1] - 1]; typ[q[f1]] = 4
        f2 = ~f1 & (y >= nb)
        if f2.any():
            fin_end(q[f2])
        f3 = ~f1 & ~f2
        yy = y[f3]; oy = o[yy]; ok = np.isfinite(oy) & (oy > 0)
        eb[q[f3]] = yy; px[q[f3]] = np.where(ok, oy, c[yy]); typ[q[f3]] = ty[f3]; obad[q[f3]] = ~ok

    act = np.arange(m); d = 0
    while len(act):
        j = S[act] + d
        f = j >= nb
        if f.any():
            fin_end(act[f]); act = act[~f]; j = j[~f]
            if not len(act):
                break
        if d >= 1:
            fb = bad[j]
            if fb.any():
                q = act[fb]; eb[q] = j[fb] - 1; px[q] = c[j[fb] - 1]; typ[q] = 4
                act = act[~fb]; j = j[~fb]
                if not len(act):
                    break
        lv = LV[j]
        if not np.isfinite(lv).all():
            raise RuntimeError(f"⛔ 持有中軌道值缺（mode {mode}；不應發生：進場時 20 根相連、持有中不跨壞根）")
        if mode == "i":
            sv = sar[act]
            ts = l[j] <= sv; tb = l[j] <= lv; trig = ts | tb
            if trig.any():
                q = act[trig]; jj = j[trig]; a_s = ts[trig]; a_b = tb[trig]; s_ = sv[trig]; b_ = lv[trig]
                bt = a_s & a_b
                lvl = np.where(bt, np.maximum(s_, b_), np.where(a_s, s_, b_))
                ty = np.where(bt, np.where(s_ >= b_, 1, 2), np.where(a_s, 1, 2)).astype(np.int8)
                both[q] = bt
                dl = dnlb[jj]
                if dl.any():
                    defer(q[dl], jj[dl] + 1, ty[dl])
                nd = ~dl
                if nd.any():
                    qn = q[nd]; jn = jj[nd]; oj = o[jn]; ok = np.isfinite(oj) & (oj > 0)
                    eb[qn] = jn; px[qn] = np.where(ok, np.minimum(oj, lvl[nd]), lvl[nd]); typ[qn] = ty[nd]; obad[qn] = ~ok
        else:
            if mode == "c":
                sv = sar[act]
                ts = c[j] <= sv; tb = c[j] <= lv; trig = ts | tb; bt = ts & tb
                ty = np.where(bt, np.where(sv >= lv, 1, 2), np.where(ts, 1, 2)).astype(np.int8)
            else:
                trig = c[j] < lv; bt = np.zeros(len(j), bool); ty = np.full(len(j), 3, np.int8)
            if trig.any():
                q = act[trig]; jj = j[trig]; tyq = ty[trig]; both[q] = bt[trig]
                x = jj + 1
                la = x >= nb
                if la.any():
                    ql = q[la]
                    if delisted:
                        eb[ql] = jj[la]; px[ql] = c[jj[la]]; typ[ql] = 5
                    else:
                        typ[ql] = TAIL
                g = ~la
                xg = x[g]; qg = q[g]; jg = jj[g]; tg = tyq[g]
                fb2 = bad[xg]
                eb[qg[fb2]] = jg[fb2]; px[qg[fb2]] = c[jg[fb2]]; typ[qg[fb2]] = 4
                dl = dnlb[xg] & ~fb2
                if dl.any():
                    defer(qg[dl], xg[dl], tg[dl])
                nn = ~fb2 & ~dl
                xo = xg[nn]; ox = o[xo]; ok = np.isfinite(ox) & (ox > 0)
                eb[qg[nn]] = xo; px[qg[nn]] = np.where(ok, ox, c[xo]); typ[qg[nn]] = tg[nn]; obad[qg[nn]] = ~ok
        keep = ~trig
        act = act[keep]; j = j[keep]
        if mode != "m" and len(act):
            if d >= 1:
                nh = h[j] > ep[act]
                ep[act] = np.where(nh, h[j], ep[act])
                naf[act] = np.where(nh, np.minimum(naf[act] + 1, AF_N), naf[act])
            sv = sar[act]
            nv = sv + (AF0 * naf[act]) * (ep[act] - sv)
            sar[act] = np.minimum(nv, np.minimum(l[j], l[j - 1]))
        d += 1
    return out


def sim_ref(o, h, l, c, bad, dnlb, idx, n0, s, sar0, LV, mode):
    """逐根迴圈版（fixture 用）：回 (eb, px, typ, post, both)。"""
    nb = len(c); delisted = (n0 - 1 - idx[-1]) >= GAP_END

    def endp():
        return (nb - 1, c[nb - 1], 5) if delisted else (-1, np.nan, TAIL)

    def defer(x0, ty):
        y = x0
        while y < nb:
            if bad[y]:
                return y - 1, c[y - 1], 4
            if not dnlb[y]:
                return y, (o[y] if (np.isfinite(o[y]) and o[y] > 0) else c[y]), ty
            y += 1
        return endp()
    sar = sar0; ep = h[s]; naf = 1; j = s; d = 0
    while True:
        if j >= nb:
            e = endp(); return e[0], e[1], e[2], False, False
        if d >= 1 and bad[j]:
            return j - 1, c[j - 1], 4, False, False
        if mode == "i":
            ts = l[j] <= sar; tb = l[j] <= LV[j]
            if ts or tb:
                bt = bool(ts and tb)
                lvl = max(sar, LV[j]) if bt else (sar if ts else LV[j])
                ty = (1 if sar >= LV[j] else 2) if bt else (1 if ts else 2)
                if dnlb[j]:
                    e = defer(j + 1, ty); return e[0], e[1], e[2], True, bt
                ok = np.isfinite(o[j]) and o[j] > 0
                return j, (min(o[j], lvl) if ok else lvl), ty, False, bt
        else:
            if mode == "c":
                ts = c[j] <= sar; tb = c[j] <= LV[j]; trig = ts or tb; bt = bool(ts and tb)
                ty = (1 if sar >= LV[j] else 2) if bt else (1 if ts else 2)
            else:
                trig = c[j] < LV[j]; bt = False; ty = 3
            if trig:
                if j + 1 >= nb:
                    return (j, c[j], 5, False, bt) if delisted else (-1, np.nan, TAIL, False, bt)
                if bad[j + 1]:
                    return j, c[j], 4, False, bt
                if dnlb[j + 1]:
                    e = defer(j + 1, ty); return e[0], e[1], e[2], True, bt
                return j + 1, (o[j + 1] if (np.isfinite(o[j + 1]) and o[j + 1] > 0) else c[j + 1]), ty, False, bt
        if mode != "m":
            if d >= 1 and h[j] > ep:
                ep = h[j]; naf = min(naf + 1, AF_N)
            sar = min(sar + (AF0 * naf) * (ep - sar), min(l[j], l[j - 1]))
        j += 1; d += 1


def sar_path(h, l, s, sar0, upto):
    """SAR[s..upto] 逐根（對帳／fixture 用；不判出場）。"""
    out = [sar0]; sar = sar0; ep = h[s]; naf = 1
    for j in range(s, upto):
        if j > s and h[j] > ep:
            ep = h[j]; naf = min(naf + 1, AF_N)
        sar = min(sar + (AF0 * naf) * (ep - sar), min(l[j], l[j - 1]))
        out.append(sar)
    return out


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(11)
    nchk = 0
    for rep in range(300):
        nb = int(rng.integers(40, 200)); n0 = nb + int(rng.integers(0, 12))
        c = 50 * np.exp(np.cumsum(rng.normal(0.002, 0.03, nb)))
        h = c * (1 + rng.uniform(0, 0.04, nb)); l = c * (1 - rng.uniform(0, 0.04, nb))
        o = l + (h - l) * rng.uniform(0, 1, nb)
        o[rng.random(nb) < 0.03] = np.nan
        bad = rng.random(nb) < 0.02; bad[0] = True
        dnlb = rng.random(nb) < 0.06
        idx = np.sort(rng.choice(np.arange(n0), nb, replace=False))
        mid, up, lo, bw, pb = BB.boll(c, bad)
        LBp = np.r_[np.nan, lo[:-1]]
        L20 = BB._win(l, SAR_LB, np.min)
        # 進場根 s：第 k＝s−1 根布林窗有值、s 非壞
        cand = np.array([k + 1 for k in range(nb - 1) if np.isfinite(up[k]) and not bad[k + 1]], np.int64)
        if not len(cand):
            continue
        # 窗內不全相連 ⇒ 布林缺值會在持有中出現：fixture 把「持有中會遇到的缺值」交給壞根（bad 即斷開，與實際相同）
        sar0 = L20[cand - 1] * rng.uniform(0.9, 1.0, len(cand))
        for key, mode, LV in (("Mi", "i", LBp), ("Mb", "i", lo), ("Mc", "c", lo), ("Mm", "m", mid)):
            r = sim(o, h, l, c, bad, dnlb, idx, n0, cand, sar0, LV, mode)
            for q, s in enumerate(cand):
                e2 = sim_ref(o, h, l, c, bad, dnlb, idx, n0, int(s), float(sar0[q]), LV, mode)
                assert (r["eb"][q], r["typ"][q], r["post"][q], r["both"][q]) == (e2[0], e2[2], e2[3], e2[4]), (rep, key, s, r["eb"][q], r["typ"][q], e2)
                assert (np.isnan(r["px"][q]) and np.isnan(e2[1])) or abs(r["px"][q] - e2[1]) < 1e-12
                nchk += 1
    msgs.append(f"F1 向量化出場（盤中觸價前一根下軌／當根下軌、收盤判 SAR＋下軌、跌破中軌；SAR 遞迴、鎖死跌停順延、壞根、缺開盤、下市／資料尾）＝ 逐根迴圈（{nchk} 筆）")
    # F2 SAR 手算小例：起點 9、h＝[10,11,12,11.5,13]、l 高（不觸）⇒ 逐根
    h = np.array([10, 10, 11, 12, 11.5, 13, 13, 13], float); l = np.array([9.5, 9.6, 10.5, 11, 11, 12, 12.5, 12.6], float)
    p = sar_path(h, l, 1, 9.0, 6)
    exp = [9.0]; sv = 9.0
    sv = min(sv + 0.02 * (10 - sv), 9.6, 9.5); exp.append(sv)            # j＝1（進場根）：EP＝10、AF 0.02
    sv = min(sv + 0.04 * (11 - sv), 10.5, 9.6); exp.append(sv)           # j＝2：新高 11 ⇒ AF 0.04
    sv = min(sv + 0.06 * (12 - sv), 11, 10.5); exp.append(sv)            # j＝3：新高 12 ⇒ 0.06
    sv = min(sv + 0.06 * (12 - sv), 11, 11); exp.append(sv)              # j＝4：無新高
    sv = min(sv + 0.08 * (13 - sv), 12, 11); exp.append(sv)              # j＝5：新高 13 ⇒ 0.08
    assert np.allclose(p, exp, atol=1e-12, rtol=0), (p, exp)
    msgs.append("F2 SAR 手算小例（EP 起始＝進場根最高、新高才加速、今昨兩低上限）相符")
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((300, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = UO.agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F3 假訊號分群彙總式 ＝ research11.cl_stats")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid, dry = a
    sid_, res = BB.stock_job((wn, sid))                     # ⭐ 頻率表同一支：事件、剔除狀態
    if res is None:
        return sid, None
    X = WF.base(wn, sid)
    W = X["W"]; n0 = X["n0"]; i = W["ix"][sid]
    o, h, l, c, bad, idx, nb, df = X["o"], X["h"], X["l"], X["c"], X["bad"], X["idx"], X["nb"], X["df"]
    mid, up, lo, bw, pb = BB.boll(c, bad)
    gate = X["gate"]; PV = np.asarray(X["PV"][:n0], bool); TRD = X["TRD"]; O = X["O"]; UPL = X["UPL"]
    dnlb = np.asarray(W["DNL"][i][idx], bool)
    pop = gate & PV
    kk = np.arange(nb - 1); s = kk + 1; T = idx[kk]; e = T + 1
    e_ = np.minimum(e, n0 - 1)
    with np.errstate(invalid="ignore"):
        ok = pop[T] & ~bad[kk] & (idx[s] == e) & ~bad[s] & (e < n0)
        ok &= TRD[e_] & np.isfinite(O[e_]) & (np.nan_to_num(O[e_]) > 0) & ~UPL[e_] & np.isfinite(o[s]) & (o[s] > 0) & np.isfinite(up[kk])
    ent = np.zeros(n0, bool); ent[T[ok]] = True
    ev = res["ev"]
    okk = np.zeros(nb, bool); okk[kk[ok]] = True
    nex = {cell: int(sum(1 for x in ev[cell] if x["st"] == "保留" and not okk[x["k"]])) for cell in ("M1", "M2", "M3")}
    out = {"ent": ent, "pop": pop, "ev": ev, "nex": nex, "nb": nb}
    if dry:
        return sid, out
    L20 = BB._win(l, SAR_LB, np.min)
    LBp = np.r_[np.nan, lo[:-1]]
    LVS = {"Mi": LBp, "Mb": lo, "Mc": lo, "Mm": mid}
    sk = kk[ok]; S = sk + 1; Tq = idx[sk]; Pq = o[S]; sar0 = L20[sk]
    if not np.isfinite(sar0).all():
        raise RuntimeError(f"⛔ {sid} SAR 起點缺值")
    kept = {cell: {int(x["T"]) for x in ev[cell] if x["st"] == "保留"} for cell in ("M1", "M2", "M3")}
    EVR = {}
    for key, mode in MODES.items():
        r = sim(o, h, l, c, bad, dnlb, idx, n0, S, sar0, LVS[key], mode)
        okr = r["eb"] >= 0
        Rr = np.full(n0, np.nan); Ty = np.zeros(n0, np.int8); Hh = np.full(n0, -1, np.int16)
        with np.errstate(invalid="ignore", divide="ignore"):
            rr = r["px"] / Pq - 1.0
        Rr[Tq[okr]] = rr[okr]; Ty[Tq] = r["typ"]
        Hh[Tq[okr]] = (idx[r["eb"][okr]] - idx[S[okr]]).astype(np.int16)
        out[f"C_{key}"] = (Rr, Ty, Hh)
        out[f"Cn_{key}"] = {"順延": int(r["post"].sum()), "同根皆觸": int(r["both"].sum()), "開盤缺用替代": int(r["obad"].sum())}
        want = set().union(*[kept[cl] for cl in MODE_EV[key]])
        d_ = {}
        for q in np.flatnonzero(np.isin(Tq, np.fromiter(want, np.int64, len(want)))) if want else []:
            e_b = int(r["eb"][q]); ty = int(r["typ"][q])
            d_[int(Tq[q])] = {"k": int(sk[q]), "P": float(Pq[q]), "sar0": float(sar0[q]), "eb": e_b, "typ": ty,
                              "R": float(rr[q]) if e_b >= 0 else np.nan, "sell": int(idx[e_b]) if e_b >= 0 else -1,
                              "hold": int(idx[e_b] - idx[S[q]]) if e_b >= 0 else -1,
                              "mtm": float(c[nb - 1] / Pq[q] - 1.0) if ty == TAIL else np.nan,
                              "post": bool(r["post"][q]), "both": bool(r["both"][q]), "obad": bool(r["obad"][q]),
                              "same": bool(e_b == int(S[q])), "px": float(r["px"][q])}
        EVR[key] = d_
    out["EVR"] = EVR
    # 固定抱 H（researchUO D3 同式；T＋1 開盤進場）
    cf = df["close"].to_numpy(float); of = df["open"].to_numpy(float)
    cff = pd.Series(cf).ffill().to_numpy()
    badcal = np.zeros(n0, bool); badcal[idx[bad]] = True
    csb = np.cumsum(badcal).astype(np.int64)
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okh = (kH >= 0) & (kH < nb - 1)
    pp = np.arange(n0)[okh]; kq = kH[okh]
    gap[pp] = (idx[kq + 1] - idx[kq] - 1 >= 5) & (pp - idx[kq] >= 5)
    for H in HD:
        g = np.full(n0, np.nan)
        t = np.arange(n0 - H)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[t] = cff[t + H] / of[t + 1] - 1.0
        brk = np.ones(n0, bool)
        brk[t] = (csb[t + H] - csb[t + 1] > 0) | gap[t + H]
        g[brk] = np.nan
        g[~ent] = np.nan
        out[f"G{H}"] = g
    return sid, out


# ═════════════ 統計 ═════════════
def trade_stats(Rn, hold, typ):
    Rn = np.asarray(Rn, float)
    o = {}
    if len(Rn):
        w = Rn[Rn > 0]; l_ = Rn[Rn <= 0]
        o.update({"淨報酬平均": float(Rn.mean()), "淨報酬中位": float(np.median(Rn)), "勝率": float((Rn > 0).mean()),
                  "平均賺": float(w.mean()) if len(w) else None, "平均賠": float(l_.mean()) if len(l_) else None,
                  "平均賺賠比": float(w.mean() / abs(l_.mean())) if len(w) and len(l_) and l_.mean() != 0 else None,
                  "平均持有天數": float(np.mean(hold)), "持有天數中位": float(np.median(hold)), "持有天數p90": float(np.percentile(hold, 90))})
        cnt = Counter(np.asarray(typ).tolist())
        for k_, nm in TYP.items():
            if k_ == TAIL:
                continue
            o[f"出場占比_{nm}"] = float(cnt.get(k_, 0) / len(Rn))
    return o


def sentence(cell, st, early=False, extra=None):
    tail = ([extra] if extra else []) + [SENT_SELF, SENT_SAR, SENT_SRC, SENT_ALL] + (NOTE_EARLY if early else [])
    rs = st["結果"]
    nm = NAME.get(cell, cell)
    if rs == "樣本不足以分辨":
        return f"{nm}：樣本不足以分辨（n_eff＝{st.get('n_eff', 0)}）｜" + "；".join(tail)
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(st["n_eff"]) if st.get("出口") == "出口②" else ""
    if rs == "結果①":
        s = "{}{}比同一天同母體隨機買、照同樣規則賣：測不出（X̄ {}，95% CI {} ～ {}）".format(pre, nm, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
    else:
        x2 = st.get("假訊號_x2", 0) or 0
        warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
        verb = "多賺" if rs == "結果②" else "少賺"
        s = "{}{}{}比同一天同母體隨機買、照同樣規則賣，每筆{} {}".format(warn, pre, nm, verb, pct(abs(st["X̄"]))[1:])
        s += "（95% CI {} ～ {}）".format(pct(st["lo"]), pct(st["hi"]))
    return s + "｜" + "；".join(tail)


def freq_frame(EVS, cal, n0):
    """researchWR_freq.run_freq 的事件檔寫法原樣（M1、M2、M3），寫成 CSV 再讀回字串。"""
    allrows = []
    for cell in ("M1", "M2", "M3"):
        rows = sorted([e for ev in EVS for e in ev.get(cell, [])], key=lambda x: (x["T"], x["sid"]))
        if not rows:
            continue
        dfo = pd.DataFrame(rows)
        for col in ("T", "c日", "進場日位置"):
            if col in dfo:
                dfo[col] = [str(cal[x].date()) if 0 <= x < n0 else "" for x in dfo[col]]
        dfo.insert(0, "格", cell)
        allrows.append(dfo)
    buf = io.StringIO()
    pd.concat(allrows, ignore_index=True).to_csv(buf, index=False)
    buf.seek(0)
    return pd.read_csv(buf, dtype=str, keep_default_na=False)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="乾跑：只驗事件重現、對照池；⛔ 不算任何出場與報酬")
    a = ap.parse_args()
    if a.limit and not a.dry:
        raise SystemExit("⛔ 不准含報酬的小樣本試跑；--limit 只能配 --dry")
    t0 = time.time()
    out = OUT
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = WF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑' if a.dry else '本體'}開跑 {now_tpe()}")
    fx = selftest()
    J = {"性質": "布林 Method I／II seq1 事件層正式跑（單筆層；判定格 M1、M2；探索、確認各自報、主全窗參考、早年描述）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq371 §一、seq372 發號；N_前段 ＋2；盤中觸價為判定格、收盤判版並報",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE}, "Bonferroni": {"族N": N_FAM, "z": ZB},
         "SAR": {"AF起": AF0, "加速": AF0, "上限": AF0 * AF_N, "起點": "進場前 20 根最低價"},
         "fixture": fx, "讀法_頻率表": BB.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DESC = []; BY = []; FK = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in WF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        WF._G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        S = len(W["sids"]); ix = W["ix"]
        ENT = np.zeros((n0, S), bool); POP = np.zeros((n0, S), bool)
        CK = list(MODES)
        CR = {k: np.full((n0, S), np.nan) for k in CK}
        CT = {k: np.zeros((n0, S), np.int8) for k in CK}
        CH = {k: np.full((n0, S), -1, np.int16) for k in CK}
        G = {H: np.full((n0, S), np.nan) for H in HD}
        CN = {k: Counter() for k in CK}
        EVS = {}; EVR = {}; NEX = Counter()
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s_, a.dry) for s_ in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    ENT[:, j] = r["ent"]; POP[:, j] = r["pop"]
                    EVS[sid] = r["ev"]; NEX.update(r["nex"])
                    if not a.dry:
                        for kk in CK:
                            CR[kk][:, j], CT[kk][:, j], CH[kk][:, j] = r[f"C_{kk}"]
                            CN[kk].update(r[f"Cn_{kk}"])
                        for H in HD:
                            G[H][:, j] = r[f"G{H}"]
                        EVR[sid] = r["EVR"]
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(EVS)} 檔｜{time.time() - t0:.0f}s")
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        for s_, ev in EVS.items():
            for cell in ("M1", "M2", "M3"):
                for e in ev[cell]:
                    assert e["sid"] == s_
        mine = freq_frame(list(EVS.values()), cal, n0)
        ref = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)
        if a.limit:
            ref = ref[ref["sid"].isin(set(sids))].reset_index(drop=True)
        same = list(ref.columns) == list(mine.columns) and ref.shape == mine.shape and (ref.values == mine.values).all()
        if not same:
            raise SystemExit(f"⛔ {wn} 重新偵測 ≠ 已提交頻率表事件檔（{mine.shape} vs {ref.shape}）⇒ 中止（未讀任何報酬）")
        log(f"[查核1] {wn}：重新偵測與已提交頻率表事件檔逐列逐欄相同（{len(ref):,} 列）")
        # ── 查核 2：保留事件都在母體
        bad_st = Counter()
        for s_, ev in EVS.items():
            j = ix[s_]
            for cell in ("M1", "M2", "M3"):
                for e in ev[cell]:
                    if e["st"] == "保留" and not POP[e["T"], j]:
                        bad_st[cell] += 1
        assert not bad_st, f"⛔ 保留事件但不在母體：{bad_st}"
        log(f"[查核2] 保留事件全在母體；指標或開盤缺值剔除（全世界時序、不分段）：{dict(NEX)}")
        RAW = {}
        for fam in ("M1", "M2", "M3"):
            Mx = np.zeros((n0, S), bool)
            for s_, ev in EVS.items():
                for e in ev[fam]:
                    Mx[e["T"], ix[s_]] = True
            RAW[fam] = Mx
        BASE = POP & ENT
        moni = np.asarray(cal.year * 12 + cal.month); years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(EVS),
              "段": {sg: f"{cal[p].date()}～{cal[q].date()}" for sg, (p, q) in win.items()}, "指標或開盤缺值剔除(全時序)": dict(NEX), "格": {}}
        if a.dry:
            for sg, (p0, p1) in win.items():
                pb_ = BASE[p0:p1 + 1].sum(axis=1)
                kept = {c_: sum(1 for ev in EVS.values() for e in ev[c_] if e["st"] == "保留" and p0 <= e["T"] <= p1) for c_ in ("M1", "M2", "M3")}
                log(f"[乾跑 {wn}/{sg}] 對照基池每日中位 {int(np.median(pb_[pb_ > 0]))}｜保留事件 {kept}")
            J["世界"][wn] = Wj
            continue
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        POOL = {k: BASE & np.isfinite(CR[k]) for k in CK}
        log(f"[對照池] 第一次讀報酬 {J['時點']['第一次讀報酬']}｜Mi 每日對照池中位 {int(np.median(POOL['Mi'].sum(axis=1)[POOL['Mi'].sum(axis=1) > 0]))} 檔｜{time.time() - t0:.0f}s")
        crc = {s_: zlib.crc32(s_.encode("utf-8")) for s_ in W["sids"]}
        TR = {}
        for cname, (ck, src) in CELLDEF.items():
            smp = UO.Sampler(POOL[ck], RAW[src])
            rows = []; skip = Counter()
            for s_, ev in EVS.items():
                j = ix[s_]; last_sell = -10 ** 9; open_end = False
                er = EVR[s_][ck]
                for e in sorted([x for x in ev[src] if x["st"] == "保留"], key=lambda x: x["T"]):
                    T = e["T"]
                    rec = er.get(T)
                    if rec is None:
                        skip["指標或開盤缺值"] += 1; continue
                    if open_end:
                        skip["前筆資料尾未出場"] += 1; continue
                    if T < last_sell:
                        skip["持有中略過"] += 1; continue
                    rows.append((j, T, e, rec))
                    if rec["typ"] == TAIL:
                        open_end = True
                    else:
                        last_sell = rec["sell"]
            rows.sort(key=lambda z: (z[1], W["sids"][z[0]]))
            n = len(rows)
            ii = np.array([z[0] for z in rows], np.int64); TT = np.array([z[1] for z in rows], np.int64)
            Rr = np.array([z[3]["R"] for z in rows], float); ty = np.array([z[3]["typ"] for z in rows], np.int8)
            Hk = np.array([z[3]["hold"] for z in rows], np.int64)
            cm = np.full(n, np.nan); cn = np.zeros(n, np.int64); cids = []; cty = []; chd = []
            for q, (j, T, e, rec) in enumerate(rows):
                sid = W["sids"][j]
                cs = smp.draw(T, j, [SEED_CTRL, TAG[cname], T, crc[sid]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(CR[ck][T, cs].mean()); cty.append(CT[ck][T, cs]); chd.append(CH[ck][T, cs])
                cids.append(";".join(W["sids"][x] for x in cs))
            Xv = Rr - cm
            fr = pd.DataFrame({"sid": [W["sids"][x] for x in ii], "market": [W["mk"].get(W["sids"][x], "twse") for x in ii],
                               "T": dates[TT] if n else [], "進場日": dates[np.minimum(TT + 1, n0 - 1)] if n else [],
                               "買價": [z[3]["P"] for z in rows], "SAR起點(前20日最低)": [z[3]["sar0"] for z in rows],
                               "出場價": [z[3]["px"] for z in rows],
                               "出場日": [dates[z[3]["sell"]] if z[3]["sell"] >= 0 else "" for z in rows], "出場種類": [TYP[int(x)] for x in ty],
                               "持有天數": Hk, "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": [z[3]["mtm"] for z in rows],
                               "順延(鎖死跌停)": [z[3]["post"] for z in rows], "同根皆觸": [z[3]["both"] for z in rows],
                               "開盤缺用替代": [z[3]["obad"] for z in rows], "進場當根出場": [z[3]["same"] for z in rows],
                               "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids})
            if src == "M1":
                fr["擠壓距T"] = [z[2]["擠壓距T"] for z in rows]; fr["前一根也是事件"] = [z[2]["前一根也是事件"] for z in rows]
            elif src == "M2":
                fr["%b"] = [z[2]["%b"] for z in rows]; fr["MFI"] = [z[2]["MFI"] for z in rows]
            TR[cname] = {"fr": fr, "i": ii, "T": TT, "X": Xv, "R": Rr, "ty": ty, "H": Hk, "cm": cm, "skip": dict(skip),
                         "cty": np.concatenate(cty) if cty else np.zeros(0), "chd": np.concatenate(chd) if chd else np.zeros(0), "ck": ck, "src": src}
            log(f"  [{wn}] {cname}：進場 {n} 筆（{dict(skip)}）｜資料尾未出場 {int((ty == TAIL).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
        # 固定抱 H：判定格同一批進場（描述）
        for cname in JUDGE:
            A0 = TR[cname]
            smpH = {H: UO.Sampler(BASE & np.isfinite(G[H]), RAW[A0["src"]]) for H in HD}
            for H in HD:
                g = np.array([G[H][int(T), int(j)] for j, T in zip(A0["i"], A0["T"])], float)
                cm = np.full(len(g), np.nan); cn = np.zeros(len(g), np.int64)
                for q, (j, T) in enumerate(zip(A0["i"], A0["T"])):
                    cs = smpH[H].draw(int(T), int(j), [SEED_CTRL, TAG[f"{cname}_H{H}"], int(T), crc[W["sids"][j]]])
                    cn[q] = len(cs)
                    if len(cs):
                        cm[q] = float(G[H][T, cs].mean())
                A0["fr"][f"固定抱{H}_R"] = g; A0["fr"][f"固定抱{H}_對照"] = cm; A0["fr"][f"固定抱{H}_X"] = g - cm; A0["fr"][f"固定抱{H}_對照數"] = cn
                A0[f"X{H}"] = g - cm; A0[f"G{H}"] = g
        for cname, d_ in TR.items():
            d_["fr"].to_csv(os.path.join(out, "events", f"trades_{wn}_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
        keptS = {cname: {ix[s_]: np.array(sorted(e["T"] for e in ev[cname] if e["st"] == "保留"), np.int64) for s_, ev in EVS.items()} for cname in JUDGE}
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {}
            for cname, d_ in TR.items():
                inseg = (d_["T"] >= p0) & (d_["T"] <= p1)
                okx = inseg & np.isfinite(d_["X"])
                st = TU.x_stats(d_["X"][okx], moni[d_["T"][okx]])
                fin = inseg & np.isfinite(d_["R"])
                ty_all = d_["ty"][inseg]
                st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == TAIL)).sum()),
                           "資料尾未出場_帳面R平均": float(np.nanmean(d_["fr"]["帳面R(資料尾)"].to_numpy(float)[inseg & (d_["ty"] == TAIL)])) if (inseg & (d_["ty"] == TAIL)).any() else None,
                           "無對照剔除": int((fin & ~np.isfinite(d_["X"])).sum()), "相異檔數": int(len(set(d_["i"][okx].tolist()))),
                           "每年事件數": round(int(okx.sum()) / yrs, 2), "R̄": float(d_["R"][okx].mean()) if okx.any() else None,
                           "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None,
                           "對照淨報酬平均": float(d_["cm"][okx].mean() - COST) if okx.any() else None})
                for k_, nm in TYP.items():
                    st[f"出場占比含資料尾_{nm}"] = float((ty_all == k_).mean()) if len(ty_all) else None
                st.update(trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
                frs = d_["fr"]
                if okx.any():
                    for col, nm in (("順延(鎖死跌停)", "順延筆數"), ("同根皆觸", "同根皆觸筆數"), ("開盤缺用替代", "開盤缺用替代筆數"), ("進場當根出場", "進場當根出場筆數")):
                        st[nm] = int(frs[col].to_numpy(bool)[okx].sum())
                yr = years[d_["T"][okx]]
                st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean()),
                                      "持有均": float(d_["H"][okx][yr == y].mean()),
                                      "勝率": float(((d_["R"][okx][yr == y] - COST) > 0).mean())} for y in sorted(set(yr.tolist()))}
                for y, q in st["逐年"].items():
                    BY.append({"世界": wn, "段": sg, "格": cname, "年": y, **q})
                if cname in JUDGE:
                    for H in HD:
                        xh = d_[f"X{H}"]; okh = inseg & np.isfinite(xh)
                        q = TU.x_stats(xh[okh], moni[d_["T"][okh]])
                        q.update({"R̄": float(d_[f"G{H}"][okh].mean()) if okh.any() else None})
                        DESC.append({"世界": wn, "段": sg, "格": f"{cname}_固定抱{H}日", "說明": f"同 {cname} 進場、固定抱 {H} 日（描述，⛔ 不當出場比較基準）",
                                     **{k: v for k, v in q.items() if not isinstance(v, dict)}, "身分": "描述（⛔ 不判）"})
                        st[f"固定抱{H}"] = q
                    # 假訊號臂
                    ck = d_["ck"]
                    acc = np.zeros((REPS, 300, 2)); cntf = np.zeros((REPS, 3), np.int64)
                    mo0 = moni[p0]
                    isel = d_["i"][okx]
                    nper = Counter(isel.tolist())
                    candc = {}
                    for jj in nper:
                        cand = np.flatnonzero(POOL[ck][p0:p1 + 1, jj]).astype(np.int64) + p0
                        Tk = keptS[cname].get(jj, np.zeros(0, np.int64))
                        if len(Tk) and len(cand):
                            kq = np.searchsorted(Tk, cand, side="right") - 1
                            prv = np.where(kq >= 0, Tk[np.clip(kq, 0, len(Tk) - 1)], -10 ** 9)
                            cand = cand[~((kq >= 0) & (cand - prv <= EXCL))]
                        candc[jj] = cand
                    smpf = UO.Sampler(POOL[ck], RAW[d_["src"]])
                    for r_ in range(REPS):
                        for jj, nn in nper.items():
                            cand = candc[jj]; mq = min(nn, len(cand)); cntf[r_, 2] += nn - mq
                            if mq == 0:
                                continue
                            sid = W["sids"][jj]
                            rng = np.random.default_rng([SEED_FAKE + r_, crc[sid], SEGNUM[sg]])
                            pick = np.sort(rng.choice(cand, size=mq, replace=False))
                            for T in pick:
                                T = int(T)
                                cs = smpf.draw(T, jj, [SEED_CTRL, 5000 + 100 * CELLNUM[cname] + r_, T, crc[sid]])
                                cntf[r_, 0] += 1
                                if len(cs) == 0:
                                    cntf[r_, 1] += 1; continue
                                xv = CR[ck][T, jj] - CR[ck][T, cs].mean()
                                cl = moni[T] - mo0
                                acc[r_, cl, 0] += 1.0; acc[r_, cl, 1] += xv
                    res_ = [UO.agg_eval(acc[r_]) for r_ in range(REPS)]
                    st["假訊號_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                    st["假訊號_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                    st["假訊號_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                    c2 = cntf.sum(axis=0)
                    st["假訊號_帳"] = {"抽出": int(c2[0]), "無對照": int(c2[1]), "可抽日不足": int(c2[2])}
                    for r_, q in enumerate(res_):
                        FK.append({"世界": wn, "段": sg, "格": cname, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st["假訊號_x2"] <= 1 and st.get("X̄−成本", -1) > 0
                                          and st.get("逐月中位與平均同號", False))
                segj[cname] = st
            # 盤中觸價對收盤判的差（seq372）、另一讀法差
            A_ = TR["M1"]; okA = (A_["T"] >= p0) & (A_["T"] <= p1) & np.isfinite(A_["X"])
            for other, key in (("M1_收盤判", "盤中−收盤判"), ("M1_當日下軌", "前一根下軌−當日下軌")):
                B_ = TR[other]; okB = (B_["T"] >= p0) & (B_["T"] <= p1) & np.isfinite(B_["X"])
                dd = UO.diff_stats(B_["X"][okB], moni[B_["T"][okB]], A_["X"][okA], moni[A_["T"][okA]])
                dd["R̄差"] = float(A_["R"][okA].mean() - B_["R"][okB].mean()) if okA.any() and okB.any() else None
                segj["M1"][key] = dd
            dic = segj["M1"]["盤中−收盤判"]; stc = segj["M1_收盤判"]
            extra_m1 = ("盤中觸價對收盤判的差：X̄ 差 {}（95% CI {} ～ {}）；收盤判版 {}（X̄ {}，CI {} ～ {}）".format(
                pct(dic.get("差(D2−A)")), pct(dic.get("lo")), pct(dic.get("hi")), stc["結果"], pct(stc.get("X̄")), pct(stc.get("lo")), pct(stc.get("hi"))))
            for cname, st in segj.items():
                if cname in JUDGE:
                    role = "判定格｜" + {"探索": "判定段（各自報）", "確認": "判定段（各自報）", "主全窗": "參考", "早年": "早年描述"}[sg]
                elif cname == "M1_收盤判":
                    role = "收盤判版並報（seq372；描述、⛔ 不計 N）"
                elif cname == "M1_當日下軌":
                    role = "另一讀法（只報）"
                else:
                    role = "描述（⛔ 不判、不計 N）"
                st["身分"] = role
                st["句子"] = sentence(cname, st, early=(wn == "早年"), extra=(extra_m1 if cname == "M1" else None))
                MAIN.append({"世界": wn, "段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": f"{cal[p0].date()}～{cal[p1].date()}",
                             **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")},
                             **({"盤中−收盤判_差": st["盤中−收盤判"].get("差(D2−A)"), "盤中−收盤判_lo": st["盤中−收盤判"].get("lo"),
                                 "盤中−收盤判_hi": st["盤中−收盤判"].get("hi")} if cname == "M1" else {}), "句子": st["句子"]})
                log(f"  [{wn}/{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                    + (f" 假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname in JUDGE else "")
                    + (f" 盤中−收盤判 {pct(st['盤中−收盤判'].get('差(D2−A)'))}（{pct(st['盤中−收盤判'].get('lo'))}～{pct(st['盤中−收盤判'].get('hi'))}）" if cname == "M1" else "")
                    + f"｜{time.time() - t0:.0f}s")
            Wj["格"][sg] = segj
        Wj["對照側"] = {c_: {"筆數": int(len(TR[c_]["cty"])), **{f"占比_{TYP[k]}": float((TR[c_]["cty"] == k).mean()) if len(TR[c_]["cty"]) else None for k in TYP},
                             "平均持有": float(TR[c_]["chd"][TR[c_]["chd"] >= 0].mean()) if (TR[c_]["chd"] >= 0).any() else None}
                        for c_ in CELLDEF}
        Wj["對照全體計數"] = {k: dict(v) for k, v in CN.items()}
        Wj["持有限制略過"] = {c_: d_["skip"] for c_, d_ in TR.items()}
        J["世界"][wn] = Wj
        del ENT, POP, CR, CT, CH, G, RAW, BASE, POOL, TR, EVR
    if a.dry:
        log(f"[乾跑完] ⛔ 未算任何出場與報酬｜{time.time() - t0:.0f}s")
        open(os.path.join(out, "dry.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        return
    # ── 判定表與先驗
    jd = {}
    keys = ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "bonf_lo", "中位", "X̄−成本", "逐月平均之中位", "假訊號_x2", "過seq322門檻",
            "勝率", "平均賺賠比", "平均持有天數", "持有天數中位", "每年事件數", "句子")
    for cell in JUDGE + ("M1_收盤判",):
        for sg in ("探索", "確認", "主全窗"):
            st = J["世界"]["主"]["格"][sg][cell]
            jd[f"{cell}｜{sg}"] = {k: st.get(k) for k in keys}
        st = J["世界"]["早年"]["格"]["早年"][cell]
        jd[f"{cell}｜早年"] = {k: st.get(k) for k in keys}
    J["判定"] = jd
    pri = {}
    for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for sg in sgs:
            G_ = J["世界"][w]["格"][sg]
            y1 = G_["M1"].get("每年事件數") or 0; y2 = G_["M2"].get("每年事件數") or 0
            pri[sg] = {"①M1落結果①": {"M1": G_["M1"]["結果"], "中": G_["M1"]["結果"] == "結果①"},
                       "②M2落結果①或③": {"M2": G_["M2"]["結果"], "中": G_["M2"]["結果"] in ("結果①", "結果③")},
                       "③M1每年事件數<M2的三分之一": {"M1": y1, "M2": y2, "M1÷M2": (y1 / y2 if y2 else None), "中": bool(y2 and y1 < y2 / 3)}}
    J["先驗"] = pri
    J["N"] = {"本件判定格": 2, "描述格／另一讀法／收盤判版": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "BB_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "BB_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out, "BB.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v.get(kk) for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log("[先驗] " + json.dumps({sg: {k: v['中'] for k, v in d.items()} for sg, d in pri.items()}, ensure_ascii=False))
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

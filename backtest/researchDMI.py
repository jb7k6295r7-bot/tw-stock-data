# -*- coding: utf-8 -*-
"""DMI 交叉＋極點進場＋SAR 出場 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 7329d0b51c85b40c，2026-10-18 11:08；
裁定 seq371 §二、seq372 發號；N_前段 ＋1）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchDMI_freq（DI／ADXR、交叉、事件偵測、剔除；讀法 M1～M9 寫死、沿用）、researchBB（Parabolic SAR 出場
   sim／sim_ref／sar_path、_win、trade_stats）、researchWR_freq（base、段、clean_window、reg_check）、researchUO（Sampler、x_stats（族 N＝1）、
   agg_eval、diff_stats）、researchTurtle（NOTE_EARLY）、researchAscTri_freq、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDMI [--procs 2]
    乾跑（⛔ 不算任何出場、報酬；只驗事件重現與對照池）：... -m backtest.researchDMI --dry [--limit 200]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDMI_check
輸出 backtest/resultsDMI/（⛔ 不碰 freq/）：DMI.json、DMI_main.csv（判定表＋分報）、by_year.csv、fake_reps.csv、
    events/trades_<世界>_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：E ＝ 判定格（登錄 §一）；D2_收盤 ＝ 收盤判版（登錄 §二 D2；裁定 seq372「收盤判版並報」；⛔ 不判、不計 N）；
    D1_ADXR ＝ 描述（登錄 §二 D1：E 且 ADXR(14)[T−1]＞25；⛔ 不判）；另一讀法（只報）：E_當根判SAR（進場當根也判 SAR）；
    假訊號臂（30 次隨機日當 T，只做 E）。⛔ 無固定天數（登錄 §一；seq308）。

═══ 讀法（Q 標；頻率表 M1～M9 原樣沿用（世界、母體、壞根、DI／ADXR、交叉、觸發、作廢、剔除、段），以下為正式跑新增；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 Q1 事件 ＝ 逐股呼叫 researchDMI_freq.stock_job 原樣；⭐ 依頻率表寫法排成表、與已提交的 resultsDMI/freq/events_<世界>.csv.gz 逐列逐欄比
    （E、D2_收盤），任一不同 ⇒ 中止、⛔ 不算報酬。進場候選 ＝ 狀態「保留」者；D1_ADXR ＝ 頻率表 D1（E ∧ ADXR(14)[T−1]＞25）。
    ★ 另需 SAR 起點的 20 根有值且相連：進場根 s 與其前 20 根 [s−20, s] 之間無壞 K 棒（WF.clean_window(bad, 21)[s]）、還原開盤有值 ＞ 0；
    否則剔除「SAR起點或開盤缺值」並計數（頻率表沒有這一關；DI 段齡 14 起就可能交叉，段首新股會碰到）〔另一讀法：段內不足 20 根取現有最低——不採〕。
 Q2 成交（登錄 §一）：E 進場根 s ＝ T（觸價當日），買價 P ＝ max(o[T], c 日最高)（還原價；頻率表 M5 已保證 h[T] ＞ c 日最高 ⇒ o[T] ≤ P ≤ h[T]）。
    D2：s ＝ T＋1，P ＝ o[T＋1]。開盤鎖漲停買不到 ＝ 頻率表 M6／M7 已剔。
 Q3 SAR ＝ researchBB H2 原式（⛔ 不另寫）：SAR[s] ＝ 進場前 20 根最低 ＝ min(l[s−20..s−1])（⭐ 本線定；與 researchBB 起點規則同式，以參數 SAR0 傳入）；
    EP 起始 ＝ h[s]、AF 0.02（進場當根不加速）；之後 h[j] ＞ EP ⇒ EP ＝ h[j]、AF ＝ min(0.02 × 次數, 0.20)；明日 SAR ＝ min(今 SAR ＋ AF×(EP − 今 SAR), 今低, 昨低)
    （「不得高於今昨兩根最低」＝ Wilder 原規則；上限 0.20 為常見轉述值，seq371 照用）。SAR[j] 只用 ≤ j−1 的資料。
 Q4 出場程式 ＝ researchBB.sim 原始碼以 inspect 取出、只改兩處（SIM_PATCH，逐字列在 JSON）、exec 成 sim_dmi（同 researchDMI_freq M2 對 adx_wilder 的作法；
    ⛔ 不複製一份）：① 盤中觸價模式 'i'：觸發條件加「d ≥ 1」＝ 進場當根不判出場（登錄 §一「同海龜主讀法」）；
    ② 收盤判模式 'c'：「收盤 ≤ SAR」改「收盤 ＜ SAR」（登錄 §二 D2 逐字「收盤 ＜ SAR」）。
    軌道參數 LV 傳常數 −1e300（永不觸發；DMI 只有 SAR）。其餘（SAR 遞迴、鎖死跌停順延、壞根前一根收盤強制、下市末根、資料尾）＝ researchBB H6、H7 原樣。
    fixture：sim_dmi ＝ 同法 patch 的 researchBB.sim_ref 逐根迴圈；未在進場當根觸發者 sim_dmi('i') ＝ researchBB.sim 原樣逐位同；SAR 手算用 researchBB.sar_path。
 Q5 E 出場（盤中觸價，判定格）：第 j 根（j ≥ s＋1）最低 ≤ SAR[j] ⇒ 當根以 min(開, SAR[j]) 賣（開盤缺 ⇒ SAR 價並計數）。
    E_當根判SAR（另一讀法，只報；海龜 ★2 同型）＝ researchBB.sim 原樣（j ≥ s）：進場當根最低 ≤ SAR0 ⇒ 當根以 min(開, SAR0) 賣
    （★ 日 K 看不出最低在買進前或後，此讀法假設在買進後；事件買價 ≥ 開盤）。
 Q6 D2 出場（收盤判）：第 j 根（★ j ≥ s，含進場當天收盤——開盤買在收盤之前；同海龜 D4、布林 H4）收盤 ＜ SAR[j] ⇒ 第 j＋1 根開盤賣。
 Q7 鎖死跌停順延、壞根、下市、資料尾 ＝ researchBB H6、H7（＝ 海龜 G4、G5）原樣：持有中下一根是壞 K 棒 ⇒ 前一根還原收盤強制；之後再無成交且最後一根
    距資料尾 ≥ 5 交易日 ⇒ 末根收盤（下市）；否則「資料尾未出場」照實報件數與帳面報酬，⛔ 不進 X。
 Q8 R ＝ 出場價 ÷ P − 1；淨 ＝ R − 0.585%；X ＝ R − 對照平均 R（兩邊同扣成本）。持有天數 ＝ 出場日 − 進場日（日曆位置差；E 進場日 ＝ T、D2 ＝ T＋1）。
 Q9 持有中不重複進場（登錄 §一）：同檔保留事件依 T 排序，前筆賣出日 S；★ E 系（E、D1、E_當根判）新事件需 T ＞ S（當日觸價買 ⇒ 賣出當日不再買；
    海龜 G7 同）〔另一讀法 T ≥ S〕；D2 需 T ≥ S（T＋1 開盤買在賣出日之後）。前筆資料尾未出場 ⇒ 之後全略。整個世界時序上套；各格用自己的出場日
    各自套（D1 先濾再套）。
 Q10 對照（登錄 §二「全同海龜 seq2」⇒ 海龜 G8）：同一天 T、同母體隨機 20 檔、同出場規則（各自 SAR 起點、各自 SAR）：
    E 系 ⇒ 對照以 T 當日開盤 o[T] 進場、出場從 T＋1 起判（E_當根判：含 T）。⚠ 時點不對稱：事件在盤中觸價成交（價 ≥ 開盤、且已知當天突破）、
      對照在開盤成交（不知道當天走勢）；池 ＝ gate[T] ∧ pit_valid[T] ∧ T 非壞 ∧ T 開盤有值 ＞ 0 ∧ 非開盤鎖漲停 ∧ Q1 的 21 根相連 ∧ R 可算。
    D2 ⇒ 對照以 T＋1 開盤進場（同 D2 事件，時點對稱）；池 ＝ 母體 ∧ T＋1 可買（頻率表同旗標）∧ 21 根相連 ∧ R 可算。
    ★ 扣事件股自己與 T 當天同格【原始】偵測到的股票（任何狀態；D1、E_當根判扣 E 的原始偵測；researchUO E6、海龜 G8 同）；不放回抽 20（不足全取、計數）；
    等權；⛔ 對照不套持有限制。種子 default_rng([20261018, 格標, T, crc32(sid)])；格標 E＝1、E_當根判SAR＝11、D1_ADXR＝31、D2_收盤＝41。
 Q11 判定量 X̄；CI ＝ T 所在曆月分群（research11.cl_stats）、1.96；n_eff ＝ min(可算筆數, 有事件曆月數)；n_eff ＜ 30 ⇒ 依構造不可判定、
    30～99 ⇒ 句首「樣本中等」；結果② ＝ CI 不含 0 且 X̄ ＞ 0、③ ＝ X̄ ＜ 0 且 CI 不含 0、① ＝ 含 0。判定段：探索、確認【各自報】為準；主全窗參考；
    早年 2005～2014 描述（附 reduce_v2 約 0.3% 註）。★ Bonferroni 族 N＝1（本件判定格只有 E，N_前段 ＋1）⇒ z ＝ 1.96（researchUO.x_stats 同式）。
 Q12 seq322（海龜 G10 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；各段各報（只 E）。
 Q13 假訊號臂（海龜 G11 同式）：只做 E；r ＝ 0…29；每檔每段 n ＝ 該檔 E 可算筆數；可抽日 ＝ 該檔在段內且在 E 對照池；排除「存在該檔 E 保留事件
    T_r ∈ [T−20, T]」；不放回抽 n 天；假事件 R ＝ 對照式 R（T 開盤進場、同出場）；對照照 Q10；種子 default_rng([20261019＋r, crc32(sid), 段序號])，
    假事件的對照 [20261018, 5100＋r, T, crc32(sid)]；x／30 ＝ 落結果② 的次數。⛔ 不套持有限制。
 Q14 盤中觸價對收盤判的差（seq372，比照海龜 ★1）＝ X̄(E) − X̄(D2)，SE ＝ 曆月分群線性化（researchUO.diff_stats；兩組各自持有限制、筆數可不同）；
    另報 X̄(E) − X̄(E_當根判)。★ 描述「T 當日段」：事件 c[T] ÷ P − 1 對同一批對照 c[T] ÷ o[T] − 1 的差（X_當日），顯示 X 有多少落在進場當天
    盤中到收盤那段（海龜 ★1 的形狀）；⛔ 只描述。
 Q15 必報：交叉數、進場率（段內交叉中 20 根內有觸發的比例 ＝ 頻率表口徑；另報 實際進場 E ÷ 交叉）、每年事件數（可算筆 ÷ 段長；另附頻率表上限）、
    n_eff、平均／中位／p90 持有天數、出場種類占比（分母 ＝ 可算筆，另報含資料尾）、勝率（淨報酬 ＞ 0）、平均賺賠比（賺錢筆平均淨報酬 ÷ |賠錢筆平均|）、
    假訊號 x／30、seq322。措辭照 seq343：「SAR 出場訊號」；⛔ 不稱最高點、頂部。
 Q16 結果句必附（登錄 §三）：「交叉後 20 日內、SAR 起點用前 20 日最低，兩處由本線定」「SAR 上限 0.20 與 ADXR 25 為二手轉述」「盤中觸價口徑，另報收盤判版」
    「單筆層通過 ≠ 組合會贏 0050」；E 另附「盤中觸價對收盤判的差」（seq372）與對照口徑一句；早年另附 reduce_v2 與上櫃版面註。
 Q17 先驗（登錄 §三，寫下不改）：① E 探索、確認至少一段落結果②；② D2 探索、確認兩段都落結果①；③ 進場率（頻率表口徑）落 50～70%（各段各報）。
"""
from __future__ import annotations

import argparse
import inspect
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
from backtest import researchDMI_freq as DF                 # noqa: E402  事件偵測、DI／ADXR（⛔ 只 import）
from backtest import researchBB as BB                       # noqa: E402  SAR 出場 sim／sim_ref／sar_path、_win（⛔ 只 import）
from backtest import researchBB_freq as BBF                 # noqa: E402  _win
from backtest import researchWR_freq as WF                  # noqa: E402  base、SEGS、reg_check、clean_window（⛔ 只 import）
from backtest import researchUO as UO                       # noqa: E402  Sampler、x_stats、agg_eval、diff_stats（⛔ 只 import）
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import research11 as R                        # noqa: E402  cl_stats
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = DF.REG_SHA
OUT = "backtest/resultsDMI"
FREQ = DF.OUT
SAR_LB = BB.SAR_LB            # 20（⭐ 本線定，與布林同）
assert SAR_LB == 20 and BB.AF0 == 0.02 and abs(BB.AF0 * BB.AF_N - 0.20) < 1e-15
NO_BAND = -1e300
SEED_CTRL, SEED_FAKE = 20261018, 20261019
REPS, EXCL = 30, 20
N_FAM = 1
assert UO.N_FAM == N_FAM and UO.NCTRL == 20
COST = E.COST
TAIL = BB.TAIL
TYP = {1: "SAR出場訊號", 4: "壞根前一根收盤強制", 5: "末根收盤(下市/之後無成交)", 6: "資料尾未出場"}
assert all(BB.TYP[k] == v for k, v in TYP.items())
# 格 ⇒ (出場鍵, 事件來源格, 原始偵測族, 型)
CELLDEF = {"E": ("Ei", "E", "E", "S"), "E_當根判SAR": ("Ea", "E", "E", "S"),
           "D1_ADXR": ("Ei", "D1_ADXR", "E", "S"), "D2_收盤": ("Dc", "D2_收盤", "D2_收盤", "D")}
TAG = {"E": 1, "E_當根判SAR": 11, "D1_ADXR": 31, "D2_收盤": 41}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
JUDGE = ("E",)
NAME = {"E": "DMI＋SAR（+DI 上穿 −DI 後 20 日內盤中突破交叉日最高買、SAR 翻轉盤中觸價賣）",
        "D2_收盤": "D2 收盤判版（收盤＞交叉日最高隔天開盤買、收盤＜SAR 隔天開盤賣；seq372 並報）",
        "D1_ADXR": "D1 描述：E 且 ADXR(14)＞25",
        "E_當根判SAR": "另一讀法：進場當根也判 SAR（只報）"}
SENT_SELF = "交叉後 20 日內、SAR 起點用前 20 日最低，兩處由本線定"
SENT_SEC = "SAR 上限 0.20 與 ADXR 25 為二手轉述"
SENT_INTRA = "盤中觸價口徑，另報收盤判版"
SENT_CTRL = "對照口徑：E 事件在 T 盤中觸價買（價 ≥ 開盤、已知當天突破），對照在 T 開盤買，進場時點不對稱；收盤判版事件與對照都在 T＋1 開盤買"
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = TU.NOTE_EARLY
LOG: list = []

# ═════════════ Q4 sim_dmi：由 researchBB.sim／sim_ref 原始碼只改兩處 ═════════════
SIM_PATCH = [
    ("def sim(", "def sim_dmi("),
    ("ts = l[j] <= sv; tb = l[j] <= lv; trig = ts | tb", "ts = (l[j] <= sv) & (d >= 1); tb = (l[j] <= lv) & (d >= 1); trig = ts | tb"),
    ("ts = c[j] <= sv; tb = c[j] <= lv; trig = ts | tb; bt = ts & tb", "ts = c[j] < sv; tb = c[j] < lv; trig = ts | tb; bt = ts & tb"),
]
REF_PATCH = [
    ("def sim_ref(", "def sim_ref_dmi("),
    ("ts = l[j] <= sar; tb = l[j] <= LV[j]", "ts = d >= 1 and l[j] <= sar; tb = d >= 1 and l[j] <= LV[j]"),
    ("ts = c[j] <= sar; tb = c[j] <= LV[j]; trig = ts or tb", "ts = c[j] < sar; tb = c[j] < LV[j]; trig = ts or tb"),
]


def _patch(fn, patches, name):
    src = inspect.getsource(fn)
    for a, b in patches:
        if src.count(a) != 1:
            raise SystemExit(f"⛔ researchBB.{fn.__name__} 原始碼找不到唯一一處「{a}」⇒ 不 patch")
        src = src.replace(a, b)
    ns = dict(BB.__dict__)
    exec(compile(src, f"<{name} from researchBB.{fn.__name__}>", "exec"), ns)
    return ns[name], src


sim_dmi, SIM_SRC = _patch(BB.sim, SIM_PATCH, "sim_dmi")
sim_ref_dmi, REF_SRC = _patch(BB.sim_ref, REF_PATCH, "sim_ref_dmi")


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(12)
    nchk = 0; nsame = 0; ndiff0 = 0
    for rep in range(300):
        nb = int(rng.integers(40, 200)); n0 = nb + int(rng.integers(0, 12))
        c = 50 * np.exp(np.cumsum(rng.normal(0.001, 0.03, nb)))
        h = c * (1 + rng.uniform(0, 0.04, nb)); l = c * (1 - rng.uniform(0, 0.04, nb))
        o = l + (h - l) * rng.uniform(0, 1, nb)
        c = np.where(rng.random(nb) < 0.08, l, c)        # 收盤＝最低的根（收盤判等號情形）
        o[rng.random(nb) < 0.03] = np.nan
        bad = rng.random(nb) < 0.02; bad[0] = True
        dnlb = rng.random(nb) < 0.06
        idx = np.sort(rng.choice(np.arange(n0), nb, replace=False))
        ok21 = WF.clean_window(bad, SAR_LB + 1)
        L20 = BBF._win(l, SAR_LB, np.min)
        cand = np.flatnonzero(ok21).astype(np.int64)
        if not len(cand):
            continue
        sar0 = L20[cand - 1]
        NOB = np.full(nb, NO_BAND); BAND = c * rng.uniform(0.85, 0.97, nb)
        for mode, LV in (("i", NOB), ("c", NOB), ("i", BAND), ("c", BAND)):
            r = sim_dmi(o, h, l, c, bad, dnlb, idx, n0, cand, sar0, LV, mode)
            for q, s in enumerate(cand):
                e2 = sim_ref_dmi(o, h, l, c, bad, dnlb, idx, n0, int(s), float(sar0[q]), LV, mode)
                assert (r["eb"][q], r["typ"][q], r["post"][q], r["both"][q]) == (e2[0], e2[2], e2[3], e2[4]), (rep, mode, s, r["eb"][q], r["typ"][q], e2)
                assert (np.isnan(r["px"][q]) and np.isnan(e2[1])) or abs(r["px"][q] - e2[1]) < 1e-12
                assert not (mode == "i" and r["typ"][q] == 1 and r["eb"][q] == s)
                nchk += 1
        # F1b：進場當根未觸發者 sim_dmi('i') ＝ researchBB.sim 原樣
        rb = BB.sim(o, h, l, c, bad, dnlb, idx, n0, cand, sar0, NOB, "i")
        rd = sim_dmi(o, h, l, c, bad, dnlb, idx, n0, cand, sar0, NOB, "i")
        f0 = l[cand] <= sar0                      # researchBB.sim 在進場當根觸發者
        ndiff0 += int(f0.sum())
        for k_ in ("eb", "typ", "post", "both", "obad"):
            assert np.array_equal(rb[k_][~f0], rd[k_][~f0]), k_
        assert np.array_equal(rb["px"][~f0], rd["px"][~f0], equal_nan=True)
        nsame += int((~f0).sum())
    msgs.append(f"F1 sim_dmi（向量化，盤中觸價當根不判／收盤判嚴格 ＜；有軌道與無軌道）＝ 同法 patch 的 researchBB.sim_ref 逐根迴圈（{nchk} 筆）")
    msgs.append(f"F1b 進場當根未觸發者 sim_dmi('i') ＝ researchBB.sim 原樣逐位同（{nsame} 筆；當根觸發而分岔 {ndiff0} 筆）")
    # F2 手算：進場當根最低 ＜ SAR0 ⇒ researchBB.sim 當根出、sim_dmi 不出；之後依 researchBB.sar_path
    n = 30
    l = np.full(n, 10.0); l[5] = 9.0; h = l + 1.0; o = l + 0.5; c = l + 0.6
    s = 21; l[s] = 8.5; h[s] = 12.0; o[s] = 9.5; c[s] = 11.0
    h[22] = 11.0; o[22] = 10.5; c[22] = 10.6
    l[23] = 8.4; o[23] = 8.9; h[23] = 9.5; c[23] = 9.0
    bad = np.zeros(n, bool); bad[0] = True; dn = np.zeros(n, bool); idx = np.arange(n)
    sar0 = float(BBF._win(l, SAR_LB, np.min)[s - 1]); assert sar0 == 9.0
    p = BB.sar_path(h, l, s, sar0, 24)
    exp = [9.0, min(9.0 + 0.02 * (12 - 9.0), 8.5, 10.0)]
    exp.append(min(exp[-1] + 0.02 * (12 - exp[-1]), 10.0, 8.5))
    assert np.allclose(p[:3], exp, atol=1e-12, rtol=0) and exp[1] == 8.5 and exp[2] == 8.5
    NOB = np.full(n, NO_BAND)
    rb = BB.sim(o, h, l, c, bad, dn, idx, n + 10, np.array([s]), np.array([sar0]), NOB, "i")
    rd = sim_dmi(o, h, l, c, bad, dn, idx, n + 10, np.array([s]), np.array([sar0]), NOB, "i")
    assert (rb["eb"][0], rb["px"][0], rb["typ"][0]) == (21, 9.0, 1), rb
    assert (rd["eb"][0], rd["px"][0], rd["typ"][0]) == (23, 8.5, 1), rd
    # 收盤判嚴格：c[s] ＝ SAR0 ⇒ researchBB('c' ≤) 出、sim_dmi（＜）不出；c[22] ＜ SAR[22] ⇒ 23 開盤
    l2 = np.full(n, 10.0); l2[5] = 9.0; h2 = l2 + 1.0; o2 = l2 + 0.5; c2 = l2 + 0.6
    l2[s] = 9.0; h2[s] = 10.0; o2[s] = 9.5; c2[s] = 9.0
    l2[22] = 8.8; c2[22] = 8.9; o2[22] = 9.2; h2[22] = 9.4; o2[23] = 8.7; l2[23] = 8.5
    rb = BB.sim(o2, h2, l2, c2, bad, dn, idx, n + 10, np.array([s]), np.array([9.0]), NOB, "c")
    rd = sim_dmi(o2, h2, l2, c2, bad, dn, idx, n + 10, np.array([s]), np.array([9.0]), NOB, "c")
    p2 = BB.sar_path(h2, l2, s, 9.0, 23)
    assert p2[1] == 9.0 and c2[22] < p2[1]
    assert (rb["eb"][0], rb["px"][0]) == (22, o2[22]), rb
    assert (rd["eb"][0], rd["px"][0]) == (23, o2[23]), rd
    msgs.append("F2 手算小例：進場當根最低 ≤ SAR0 ⇒ researchBB.sim 當根出、sim_dmi 續抱至第 23 根以 SAR 8.5 出（SAR 路徑 ＝ researchBB.sar_path）；"
                "收盤＝SAR ⇒ 收盤判嚴格 ＜ 不出、次根收盤 ＜ SAR 隔天開盤出")
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
    sid_, res = DF.stock_job((wn, sid))                     # ⭐ 頻率表同一支：事件、剔除狀態、交叉
    if res is None:
        return sid, None
    X = WF.base(wn, sid)
    W = X["W"]; n0 = X["n0"]; i = W["ix"][sid]
    o, h, l, c, bad, idx, nb = X["o"], X["h"], X["l"], X["c"], X["bad"], X["idx"], X["nb"]
    gate = X["gate"]; PV = np.asarray(X["PV"][:n0], bool); TRD = X["TRD"]; O = X["O"]; UPL = X["UPL"]
    dnlb = np.asarray(W["DNL"][i][idx], bool)
    pop = gate & PV
    ok21 = WF.clean_window(bad, SAR_LB + 1)
    kk = np.arange(nb); T = idx
    with np.errstate(invalid="ignore"):
        okS = pop[T] & ~bad & np.isfinite(O[T]) & (np.nan_to_num(O[T]) > 0) & ~UPL[T] & np.isfinite(o) & (o > 0) & ok21
        okD = np.zeros(nb, bool)
        q = kk[:-1]; s1 = q + 1; e1 = T[q] + 1
        okD[q] = pop[T[q]] & ~bad[q] & (idx[s1] == e1) & ~bad[s1] & (e1 < n0)
        e_ = np.minimum(e1, n0 - 1)
        okD[q] &= TRD[e_] & np.isfinite(O[e_]) & (np.nan_to_num(O[e_]) > 0) & ~UPL[e_] & np.isfinite(o[s1]) & (o[s1] > 0) & ok21[s1]
    entS = np.zeros(n0, bool); entS[T[okS]] = True
    entD = np.zeros(n0, bool); entD[T[okD]] = True
    ev = res["ev"]
    nex = {}
    for cell in ("E", "D1_ADXR", "D2_收盤"):
        msk = okD if cell == "D2_收盤" else okS
        nex[cell] = int(sum(1 for e in ev[cell] if e["st"] == "保留" and not msk[e["k"]]))
    out = {"entS": entS, "entD": entD, "pop": pop, "ev": ev, "nex": nex, "nb": nb}
    if dry:
        return sid, out
    L20 = BBF._win(l, SAR_LB, np.min)
    NOB = np.full(nb, NO_BAND)
    sS = kk[okS]; sD = kk[okD] + 1
    s0S = L20[sS - 1]; s0D = L20[sD - 1]
    if not (np.isfinite(s0S).all() and np.isfinite(s0D).all()):
        raise RuntimeError(f"⛔ {sid} SAR 起點缺值（不應發生：21 根相連）")
    C = {"Ei": (T[sS], sS, s0S, sim_dmi(o, h, l, c, bad, dnlb, idx, n0, sS, s0S, NOB, "i")),
         "Ea": (T[sS], sS, s0S, BB.sim(o, h, l, c, bad, dnlb, idx, n0, sS, s0S, NOB, "i")),
         "Dc": (T[sD - 1], sD, s0D, sim_dmi(o, h, l, c, bad, dnlb, idx, n0, sD, s0D, NOB, "c"))}
    for key, (Tq, sq, s0, r) in C.items():
        Rr = np.full(n0, np.nan); Ty = np.zeros(n0, np.int8); Hh = np.full(n0, -1, np.int16)
        ok = r["eb"] >= 0
        Rr[Tq[ok]] = r["px"][ok] / o[sq[ok]] - 1.0
        Ty[Tq] = r["typ"]
        Hh[Tq[ok]] = (idx[r["eb"][ok]] - idx[sq[ok]]).astype(np.int16)
        out[f"C_{key}"] = (Rr, Ty, Hh)
        out[f"Cn_{key}"] = {"順延": int(r["post"].sum()), "開盤缺用替代": int(r["obad"].sum()), "進場當根出場": int((r["eb"] == sq).sum())}
    R1 = np.full(n0, np.nan); R1[T[sS]] = c[sS] / o[sS] - 1.0          # Q14 描述：對照 T 開盤 → T 收盤
    out["R1"] = R1
    # 事件式
    EVR = {}
    for key, (Tq, sq, s0, r) in C.items():
        pos = {int(s_): q_ for q_, s_ in enumerate(sq)}
        cells = ("D2_收盤",) if key == "Dc" else ("E",)
        d_ = {}
        for cell in cells:
            for e in ev[cell]:
                if e["st"] != "保留":
                    continue
                t = int(e["k"]); s = t + 1 if key == "Dc" else t
                q_ = pos.get(s)
                if q_ is None:
                    continue
                P = float(o[s]) if key == "Dc" else float(max(o[t], e["c日最高"]))
                if key != "Dc" and not (o[t] <= P <= h[t] and h[t] > e["c日最高"]):
                    raise RuntimeError(f"⛔ {sid} T={t} 觸價買價不在當日區間")
                e_b = int(r["eb"][q_]); ty = int(r["typ"][q_]); Tk = int(idx[t])
                assert Tk not in d_
                d_[Tk] = {"k": t, "s": s, "P": P, "o": float(o[s]), "sar0": float(s0[q_]), "eb": e_b, "typ": ty,
                          "R": float(r["px"][q_] / P - 1.0) if e_b >= 0 else np.nan, "sell": int(idx[e_b]) if e_b >= 0 else -1,
                          "hold": int(idx[e_b] - idx[s]) if e_b >= 0 else -1,
                          "mtm": float(c[nb - 1] / P - 1.0) if ty == TAIL else np.nan,
                          "post": bool(r["post"][q_]), "obad": bool(r["obad"][q_]), "same": bool(e_b == s), "px": float(r["px"][q_]),
                          "R1": float(c[t] / P - 1.0) if key != "Dc" else np.nan}
        EVR[key] = d_
    out["EVR"] = EVR
    return sid, out


# ═════════════ 統計 ═════════════
def trade_stats(Rn, hold, typ):
    st = BB.trade_stats(Rn, hold, typ)                    # researchBB 原式；DMI 只有 SAR 出場 ⇒ 去掉軌道兩種
    return {k: v for k, v in st.items() if not (k.startswith("出場占比_") and k[5:] not in TYP.values())}


def sentence(cell, st, early=False, extra=None):
    tail = ([extra] if extra else []) + [SENT_SELF, SENT_SEC, SENT_INTRA] + ([SENT_CTRL] if cell in ("E", "E_當根判SAR", "D1_ADXR") else []) \
        + [SENT_ALL] + (NOTE_EARLY if early else [])
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
    """researchWR_freq.run_freq 的事件檔寫法原樣（ev_cells ＝ E、D2_收盤），寫成 CSV 再讀回字串。"""
    allrows = []
    for cell in ("E", "D2_收盤"):
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
    FJ = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    J = {"性質": "DMI 交叉＋極點進場＋SAR 出場 seq1 事件層正式跑（單筆層；判定格 E；探索、確認各自報、主全窗參考、早年描述）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq371 §二、seq372 發號；N_前段 ＋1；盤中觸價為判定格、收盤判版並報",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE}, "Bonferroni": {"族N": N_FAM, "z": UO.Z95},
         "SAR": {"AF起": BB.AF0, "加速": BB.AF0, "上限": BB.AF0 * BB.AF_N, "起點": "進場前 20 根最低價（⭐ 本線定）", "實作": "researchBB.sim（inspect＋SIM_PATCH 兩處）"},
         "SIM_PATCH": SIM_PATCH, "REF_PATCH": REF_PATCH,
         "fixture": fx, "讀法_頻率表": DF.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; BY = []; FK = []
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
        ENTS = np.zeros((n0, S), bool); ENTD = np.zeros((n0, S), bool); POP = np.zeros((n0, S), bool)
        CK = ("Ei", "Ea", "Dc")
        CR = {k: np.full((n0, S), np.nan) for k in CK}
        CT = {k: np.zeros((n0, S), np.int8) for k in CK}
        CH = {k: np.full((n0, S), -1, np.int16) for k in CK}
        CR1 = np.full((n0, S), np.nan)
        CN = {k: Counter() for k in CK}
        EVS = {}; EVR = {}; NEX = Counter()
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s_, a.dry) for s_ in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    ENTS[:, j] = r["entS"]; ENTD[:, j] = r["entD"]; POP[:, j] = r["pop"]
                    EVS[sid] = r["ev"]; NEX.update(r["nex"])
                    if not a.dry:
                        for kk in CK:
                            CR[kk][:, j], CT[kk][:, j], CH[kk][:, j] = r[f"C_{kk}"]
                            CN[kk].update(r[f"Cn_{kk}"])
                        CR1[:, j] = r["R1"]
                        EVR[sid] = r["EVR"]
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(EVS)} 檔｜{time.time() - t0:.0f}s")
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        for s_, ev in EVS.items():
            for cell in ("E", "D2_收盤", "D1_ADXR"):
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
            for cell in ("E", "D2_收盤"):
                for e in ev[cell]:
                    if e["st"] == "保留" and not POP[e["T"], j]:
                        bad_st[cell] += 1
        assert not bad_st, f"⛔ 保留事件但不在母體：{bad_st}"
        log(f"[查核2] 保留事件全在母體；SAR起點或開盤缺值剔除（全世界時序、不分段）：{dict(NEX)}")
        RAW = {}
        for fam in ("E", "D2_收盤"):
            Mx = np.zeros((n0, S), bool)
            for s_, ev in EVS.items():
                for e in ev[fam]:
                    Mx[e["T"], ix[s_]] = True
            RAW[fam] = Mx
        BASES = POP & ENTS; BASED = POP & ENTD
        moni = np.asarray(cal.year * 12 + cal.month); years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(EVS),
              "段": {sg: f"{cal[p].date()}～{cal[q].date()}" for sg, (p, q) in win.items()}, "SAR起點或開盤缺值剔除(全時序)": dict(NEX), "格": {}}
        # 交叉數、進場率（頻率表口徑；不需報酬）
        XR = {}
        for sg, (p0, p1) in win.items():
            Xs = [e for ev in EVS.values() for e in ev["_交叉"] if p0 <= e["T"] <= p1]
            nE = sum(1 for e in Xs if e["E觸發"]); nD = sum(1 for e in Xs if e["D2觸發"])
            fx_ = FJ["世界"][wn]["段"][sg].get("附加", {})
            XR[sg] = {"交叉數(c在段內)": len(Xs), "E有觸發交叉": nE, "E進場率(偵測÷交叉)": nE / len(Xs) if Xs else None,
                      "D2有觸發交叉": nD, "D2進場率(偵測÷交叉)": nD / len(Xs) if Xs else None,
                      "與頻率表相同": bool(fx_.get("交叉數(c在段內)") == len(Xs) and fx_.get("E有觸發交叉") == nE and fx_.get("D2有觸發交叉") == nD)}
            if not a.limit:
                assert XR[sg]["與頻率表相同"], (wn, sg, XR[sg], fx_)
        Wj["交叉與進場率"] = XR
        if a.dry:
            for sg, (p0, p1) in win.items():
                pb_ = BASES[p0:p1 + 1].sum(axis=1); pd_ = BASED[p0:p1 + 1].sum(axis=1)
                kept = {c_: sum(1 for ev in EVS.values() for e in ev[c_] if e["st"] == "保留" and p0 <= e["T"] <= p1) for c_ in ("E", "D1_ADXR", "D2_收盤")}
                log(f"[乾跑 {wn}/{sg}] E 系對照基池每日中位 {int(np.median(pb_[pb_ > 0])) if (pb_ > 0).any() else 0}｜D2 {int(np.median(pd_[pd_ > 0])) if (pd_ > 0).any() else 0}"
                    f"｜保留事件 {kept}｜交叉 {XR[sg]['交叉數(c在段內)']} 進場率 {XR[sg]['E進場率(偵測÷交叉)']}")
            J["世界"][wn] = Wj
            continue
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        POOL = {"Ei": BASES & np.isfinite(CR["Ei"]), "Ea": BASES & np.isfinite(CR["Ea"]), "Dc": BASED & np.isfinite(CR["Dc"])}
        pm = POOL["Ei"].sum(axis=1)
        log(f"[對照池] 第一次讀報酬 {J['時點']['第一次讀報酬']}｜Ei 每日對照池中位 {int(np.median(pm[pm > 0]))} 檔｜{time.time() - t0:.0f}s")
        crc = {s_: zlib.crc32(s_.encode("utf-8")) for s_ in W["sids"]}
        TR = {}
        for cname, (ck, src, fam, typ_) in CELLDEF.items():
            smp = UO.Sampler(POOL[ck], RAW[fam])
            rows = []; skip = Counter()
            for s_, ev in EVS.items():
                j = ix[s_]; last_sell = -10 ** 9; open_end = False
                er = EVR[s_][ck]
                for e in sorted([x for x in ev[src] if x["st"] == "保留"], key=lambda x: x["T"]):
                    T = e["T"]
                    rec = er.get(T)
                    if rec is None:
                        skip["SAR起點或開盤缺值"] += 1; continue
                    if open_end:
                        skip["前筆資料尾未出場"] += 1; continue
                    if (typ_ == "S" and T <= last_sell) or (typ_ == "D" and T < last_sell):
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
            cm = np.full(n, np.nan); cn = np.zeros(n, np.int64); cm1 = np.full(n, np.nan); cids = []; cty = []; chd = []
            for q, (j, T, e, rec) in enumerate(rows):
                sid = W["sids"][j]
                cs = smp.draw(T, j, [SEED_CTRL, TAG[cname], T, crc[sid]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(CR[ck][T, cs].mean()); cty.append(CT[ck][T, cs]); chd.append(CH[ck][T, cs])
                    if typ_ == "S":
                        cm1[q] = float(CR1[T, cs].mean())
                cids.append(";".join(W["sids"][x] for x in cs))
            Xv = Rr - cm
            R1e = np.array([z[3]["R1"] for z in rows], float)
            fr = pd.DataFrame({"sid": [W["sids"][x] for x in ii], "market": [W["mk"].get(W["sids"][x], "twse") for x in ii],
                               "T": dates[TT] if n else [], "進場日": (dates[TT] if typ_ == "S" else dates[np.minimum(TT + 1, n0 - 1)]) if n else [],
                               "c日": [dates[z[2]["c日"]] for z in rows], "距交叉": [z[2]["距交叉"] for z in rows],
                               "c日最高": [z[2]["c日最高"] for z in rows], "進場根開盤": [z[3]["o"] for z in rows],
                               "買價": [z[3]["P"] for z in rows], "SAR起點(前20日最低)": [z[3]["sar0"] for z in rows],
                               "出場價": [z[3]["px"] for z in rows],
                               "出場日": [dates[z[3]["sell"]] if z[3]["sell"] >= 0 else "" for z in rows], "出場種類": [BB.TYP[int(x)] for x in ty],
                               "持有天數": Hk, "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": [z[3]["mtm"] for z in rows],
                               "順延(鎖死跌停)": [z[3]["post"] for z in rows], "開盤缺用替代": [z[3]["obad"] for z in rows],
                               "進場當根出場": [z[3]["same"] for z in rows],
                               "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids,
                               "ADXR[T-1]": [z[2]["ADXR[T-1]"] for z in rows]})
            if typ_ == "S":
                fr["R當日(買價→T收)"] = R1e; fr["對照當日R(開→T收)"] = cm1; fr["X當日"] = R1e - cm1
            TR[cname] = {"fr": fr, "i": ii, "T": TT, "X": Xv, "R": Rr, "ty": ty, "H": Hk, "cm": cm, "X1": R1e - cm1, "skip": dict(skip),
                         "cty": np.concatenate(cty) if cty else np.zeros(0), "chd": np.concatenate(chd) if chd else np.zeros(0), "ck": ck, "src": src}
            log(f"  [{wn}] {cname}：進場 {n} 筆（{dict(skip)}）｜資料尾未出場 {int((ty == TAIL).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
        for cname, d_ in TR.items():
            d_["fr"].to_csv(os.path.join(out, "events", f"trades_{wn}_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
        keptS = {ix[s_]: np.array(sorted(e["T"] for e in ev["E"] if e["st"] == "保留"), np.int64) for s_, ev in EVS.items()}
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {}
            for cname, d_ in TR.items():
                inseg = (d_["T"] >= p0) & (d_["T"] <= p1)
                okx = inseg & np.isfinite(d_["X"])
                st = UO.x_stats(d_["X"][okx], moni[d_["T"][okx]])
                fin = inseg & np.isfinite(d_["R"])
                ty_all = d_["ty"][inseg]
                fq = FJ["世界"][wn]["段"][sg].get(d_["src"], {})
                st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == TAIL)).sum()),
                           "資料尾未出場_帳面R平均": float(np.nanmean(d_["fr"]["帳面R(資料尾)"].to_numpy(float)[inseg & (d_["ty"] == TAIL)])) if (inseg & (d_["ty"] == TAIL)).any() else None,
                           "無對照剔除": int((fin & ~np.isfinite(d_["X"])).sum()), "相異檔數": int(len(set(d_["i"][okx].tolist()))),
                           "每年事件數": round(int(okx.sum()) / yrs, 2), "頻率表上限每年事件數": fq.get("每年事件數"),
                           "R̄": float(d_["R"][okx].mean()) if okx.any() else None,
                           "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None,
                           "對照淨報酬平均": float(d_["cm"][okx].mean() - COST) if okx.any() else None})
                for k_, nm in TYP.items():
                    st[f"出場占比含資料尾_{nm}"] = float((ty_all == k_).mean()) if len(ty_all) else None
                st.update(trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
                frs = d_["fr"]
                if okx.any():
                    for col, nm in (("順延(鎖死跌停)", "順延筆數"), ("開盤缺用替代", "開盤缺用替代筆數"), ("進場當根出場", "進場當根出場筆數")):
                        st[nm] = int(frs[col].to_numpy(bool)[okx].sum())
                if cname in ("E", "E_當根判SAR", "D1_ADXR"):
                    ok1 = okx & np.isfinite(d_["X1"])
                    q1 = UO.x_stats(d_["X1"][ok1], moni[d_["T"][ok1]])
                    st["T當日段"] = {k: q1.get(k) for k in ("n", "X̄", "lo", "hi", "結果")}
                if cname == "E":
                    st["實際進場÷交叉"] = int(okx.sum()) / XR[sg]["交叉數(c在段內)"] if XR[sg]["交叉數(c在段內)"] else None
                yr = years[d_["T"][okx]]
                st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean()),
                                      "持有均": float(d_["H"][okx][yr == y].mean()),
                                      "勝率": float(((d_["R"][okx][yr == y] - COST) > 0).mean())} for y in sorted(set(yr.tolist()))}
                for y, q in st["逐年"].items():
                    BY.append({"世界": wn, "段": sg, "格": cname, "年": y, **q})
                if cname in JUDGE:
                    ck = d_["ck"]
                    acc = np.zeros((REPS, 300, 2)); cntf = np.zeros((REPS, 3), np.int64)
                    mo0 = moni[p0]
                    isel = d_["i"][okx]
                    nper = Counter(isel.tolist())
                    candc = {}
                    for jj in nper:
                        cand = np.flatnonzero(POOL[ck][p0:p1 + 1, jj]).astype(np.int64) + p0
                        Tk = keptS.get(jj, np.zeros(0, np.int64))
                        if len(Tk) and len(cand):
                            kq = np.searchsorted(Tk, cand, side="right") - 1
                            prv = np.where(kq >= 0, Tk[np.clip(kq, 0, len(Tk) - 1)], -10 ** 9)
                            cand = cand[~((kq >= 0) & (cand - prv <= EXCL))]
                        candc[jj] = cand
                    smpf = UO.Sampler(POOL[ck], RAW["E"])
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
                                cs = smpf.draw(T, jj, [SEED_CTRL, 5100 + r_, T, crc[sid]])
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
            # 盤中觸價對收盤判的差（seq372）、當根判差
            A_ = TR["E"]; okA = (A_["T"] >= p0) & (A_["T"] <= p1) & np.isfinite(A_["X"])
            for other, key in (("D2_收盤", "盤中−收盤判"), ("E_當根判SAR", "當根不判−當根判")):
                B_ = TR[other]; okB = (B_["T"] >= p0) & (B_["T"] <= p1) & np.isfinite(B_["X"])
                dd = UO.diff_stats(B_["X"][okB], moni[B_["T"][okB]], A_["X"][okA], moni[A_["T"][okA]])
                dd["R̄差"] = float(A_["R"][okA].mean() - B_["R"][okB].mean()) if okA.any() and okB.any() else None
                segj["E"][key] = dd
            dic = segj["E"]["盤中−收盤判"]; stc = segj["D2_收盤"]; t1 = segj["E"]["T當日段"]
            extra_e = ("盤中觸價對收盤判的差：X̄ 差 {}（95% CI {} ～ {}）；收盤判版 {}（X̄ {}，CI {} ～ {}）；T 當日段（買價→T 收盤 對 對照開盤→T 收盤）X̄ {}".format(
                pct(dic.get("差(D2−A)")), pct(dic.get("lo")), pct(dic.get("hi")), stc["結果"], pct(stc.get("X̄")), pct(stc.get("lo")), pct(stc.get("hi")),
                pct(t1.get("X̄"))))
            for cname, st in segj.items():
                if cname in JUDGE:
                    role = "判定格｜" + {"探索": "判定段（各自報）", "確認": "判定段（各自報）", "主全窗": "參考", "早年": "早年描述"}[sg]
                elif cname == "D2_收盤":
                    role = "收盤判版並報（seq372；描述、⛔ 不計 N）"
                elif cname == "E_當根判SAR":
                    role = "另一讀法（只報）"
                else:
                    role = "描述（⛔ 不判、不計 N）"
                st["身分"] = role
                st["句子"] = sentence(cname, st, early=(wn == "早年"), extra=(extra_e if cname == "E" else None))
                MAIN.append({"世界": wn, "段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": f"{cal[p0].date()}～{cal[p1].date()}",
                             **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")},
                             **({"盤中−收盤判_差": st["盤中−收盤判"].get("差(D2−A)"), "盤中−收盤判_lo": st["盤中−收盤判"].get("lo"),
                                 "盤中−收盤判_hi": st["盤中−收盤判"].get("hi"), "T當日段_X̄": st["T當日段"].get("X̄")} if cname == "E" else {}),
                             "句子": st["句子"]})
                log(f"  [{wn}/{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                    + (f" 假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname in JUDGE else "")
                    + (f" 盤中−收盤判 {pct(st['盤中−收盤判'].get('差(D2−A)'))}（{pct(st['盤中−收盤判'].get('lo'))}～{pct(st['盤中−收盤判'].get('hi'))}）"
                       f" 當日段 {pct(st['T當日段'].get('X̄'))}" if cname == "E" else "")
                    + f"｜{time.time() - t0:.0f}s")
            Wj["格"][sg] = segj
        Wj["對照側"] = {c_: {"筆數": int(len(TR[c_]["cty"])), **{f"占比_{TYP[k]}": float((TR[c_]["cty"] == k).mean()) if len(TR[c_]["cty"]) else None for k in TYP},
                             "平均持有": float(TR[c_]["chd"][TR[c_]["chd"] >= 0].mean()) if (TR[c_]["chd"] >= 0).any() else None}
                        for c_ in CELLDEF}
        Wj["對照全體計數"] = {k: dict(v) for k, v in CN.items()}
        Wj["持有限制略過"] = {c_: d_["skip"] for c_, d_ in TR.items()}
        J["世界"][wn] = Wj
        del ENTS, ENTD, POP, CR, CT, CH, CR1, RAW, BASES, BASED, POOL, TR, EVR
    if a.dry:
        log(f"[乾跑完] ⛔ 未算任何出場與報酬｜{time.time() - t0:.0f}s")
        open(os.path.join(out, "dry.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        return
    # ── 判定表與先驗
    jd = {}
    keys = ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "bonf_lo", "中位", "X̄−成本", "逐月平均之中位", "假訊號_x2", "過seq322門檻",
            "勝率", "平均賺賠比", "平均持有天數", "持有天數中位", "持有天數p90", "每年事件數", "頻率表上限每年事件數", "出場占比_SAR出場訊號", "句子")
    for cell in ("E", "D2_收盤", "D1_ADXR", "E_當根判SAR"):
        for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
            for sg in sgs:
                st = J["世界"][w]["格"][sg][cell]
                jd[f"{cell}｜{sg}"] = {k: st.get(k) for k in keys}
    J["判定"] = jd
    pri = {}
    for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for sg in sgs:
            G_ = J["世界"][w]["格"][sg]; xr = J["世界"][w]["交叉與進場率"][sg]
            pri[sg] = {"③進場率50～70%": {"進場率": xr["E進場率(偵測÷交叉)"], "中": bool(0.5 <= xr["E進場率(偵測÷交叉)"] <= 0.7)},
                       "E結果": G_["E"]["結果"], "D2結果": G_["D2_收盤"]["結果"]}
    ex, cf = J["世界"]["主"]["格"]["探索"], J["世界"]["主"]["格"]["確認"]
    pri["①E兩段至少一段落結果②"] = {"探索": ex["E"]["結果"], "確認": cf["E"]["結果"], "中": ex["E"]["結果"] == "結果②" or cf["E"]["結果"] == "結果②"}
    pri["②D2兩段都落結果①"] = {"探索": ex["D2_收盤"]["結果"], "確認": cf["D2_收盤"]["結果"], "中": ex["D2_收盤"]["結果"] == "結果①" and cf["D2_收盤"]["結果"] == "結果①"}
    J["先驗"] = pri
    J["N"] = {"本件判定格": 1, "描述格／另一讀法／收盤判版": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "DMI_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out, "DMI.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v.get(kk) for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log("[先驗] " + json.dumps(pri, ensure_ascii=False, default=float))
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

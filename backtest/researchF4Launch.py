# -*- coding: utf-8 -*-
"""PREREG連續虧損起漲 seq1（台股策略線登錄 sha 207e7f0db9763c36，2026-10-07 14:23；裁定 seq320 發號 N_組合 ＋1、16 格整套一判、事後重切 ⇒ 最多暫定）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchF4Launch prep [--procs 2]          # 世界、F4、訊號、逐筆出場（大檔 ~/f4lwork）
    ...                                                      -m backtest.researchF4Launch run [--procs 2] [--reps 100]   # 組合層（16 格 × 臂 × 種子）＋假訊號臂＋逐筆
    ...                                                      -m backtest.researchF4Launch page                          # 網頁
    抽樣查核：... -m backtest.researchF4Launch_check（獨立寫法；E1 逐日直接呼叫 surge_flow_daily.replay）

⭐ 讀法寫死時間：2026-10-07 15:40（台北）；寫死前 ⛔ 沒算任何本件數字（只看過登錄全文、裁定 seq317／seq320、既有程式與資料格式）。

═══ 讀法（L 標；登錄沒寫清楚的執行者補讀法都在這裡）═══
 L1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ 207e7f0db9763c36 才跑
 L2 世界（＝ 飆股回推 seq5／seq6、起漲特徵描述同一份）：接合版面 stitch_950ad26e12_b53f5540a8（日曆 2004-02-11～2026-09-24）、s5 名單 2,203 檔
    （上市櫃普通股含已下市、不含 DR、創新板含 -KY創）；K 棒 ＝ s5 bar；價格 ＝ data.load_stock（還原、收盤 ffill）
    GATE_V2 開（UG.set_gate_v2(True)）：訊號日 d 須 UG.pit_valid（data ＝ s5 main archive b53f5540a8）
 L3 ② 起漲特徵：researchSurge6_overlap.FEATS 14 個（s5 Q 表碼相等 ＝ 有；沒值 ＝ 沒有）；k ＝ d 收盤同時符合的個數
    月營收：Q 表建表時一律「次月 10 日之後」可用；GATE_V2 規則「2026-01 期起次月 15 日」⇒ 2026 年各月「10 日後第一個交易日 e10 ～ 15 日後第一個交易日 e15」
    之間（[e10, e15)）的 d_R2a、d_revhi 改用 e10 之前最後一根 K 棒的碼（＝ 該期還不能用時的狀態；改動的股-日數照報）
 L4 ① F4（裁定 seq320 第 1 條）：researchMine X5 的式子（單季 EPS ＝ eps_ytd 本期 − 前期、Q1 不減、空值用 eps_q；F4a 近 4 季都有值、合計 ＜ 0 且最近一季 ＜ 0｜
    F4b 近 8 季都有值、≥ 6 季 ＜ 0）；月底判定（主快照 796d94c9da 日曆各月最後交易日，2015-01～2026-09）；
    公布日 ＝ filing_dates 該季最早上傳時戳 ⇒ 次一交易日起可用；沒有時戳（2016～2018 全部、其他零星）⇒ 法定期限後第 5 個交易日（researchMine 同式；偏晚、不會早用）
    ⭐ 第一次公布值：fin_hist 是 2026-10 回填的版本；該季後來重編過（filing_dates doc_type 含「重編」）⇒ 檔內數字可能是重編後的、資料庫沒有第一次公布值
      ⇒ 該季 eps_ytd、eps_q 當空值（用到它的判定 ⇒ 判不出 ⇒ 不帶 F4）
    閘：不遮重編季時重建的 F4、F4_ok ＝ ~/minework/flags_main.npz 逐格相同；遮了以後與 flags_main 的差異（股-月數）照報
    股-日 d 的 F4 ＝ 嚴格早於 d 的最後一個月底判定日的 F4（登錄「當天之前最後一個月底」）；判不出或不在旗表 ⇒ 不帶 F4
 L5 ③ 已起漲（＝ researchMineF4when W5 觸發，逐字）：r[d] ＝ s5 F 表 dlo_60（c[d] ÷ 含 d 最近 60 根有效 K 棒最低收盤 − 1）；每檔、每個 x：依有效 K 棒順序，
    r ≥ x 的日子取第一個，之後 60 根有效 K 棒內不再取（第 61 根起再找）；全歷史一起掃（只看股價、不看旗）
    ⭐「這一段第一次達到」＝ 觸發日本身；觸發日當天 ①② 不成立 ⇒ 這一段沒有訊號（同一段之後的日子不補）
    閘：主窗內、旗表內的觸發 ＝ ~/minework/F4when/trig.npz（x ∈ 10、20、30、50%）逐筆相同
 L6 訊號 ＝ 觸發日 d ∧ k(d) ≥ K ∧ 帶 F4 ∧ pit_valid(d) ⇒ 進場日 e ＝ d＋1（日曆次一交易日）開盤買；「同一檔 60 個交易日內只算第一次」由觸發去重自動滿足（程式另驗）
    組合層：e ∈ 主窗 [2017-03-02, 2026-08-24]（rerun17 win 讀法、0050 錨同窗）；探索 ＝ 2017-03-02～2021-12-30、確認 ＝ 2022-01-03～2026-08-24（同一條權益曲線切窗；researchSlip 同法）
    ⭐「資料尾」讀成主窗尾 2026-08-24（營飆／營量、0050 錨同窗）；價格與出場判斷仍用到 2026-09-24（只影響窗外）
    W1 版：另要 EL[m(d)]（flags_main 的 W1 eligible）
 L7 E1（裁定 seq320 第 2 條；surge_flow_daily 現行 replay、去掉買回）：逐日 T ＝ e, e＋1, …，只用 T 收盤以前的資料
    起漲點 t(T) ＝ replay 錨（researchYL_truetopT.anchor_pit 同式：anchor_of(c, T)；e ＜ t ⇒ anchor_of(c, e)；t 起回落 30% 早於 e ⇒ 改錨到結束日～e 最低收盤日，最多 50 次）
    ⭐ 新上市未滿 250 根：anchor_of 原式遇到上市前空值會把空值日當最高點 ⇒ 本件回看窗下界限在第一根有效收盤（窗內全有值時與原式逐字相同）
    在 t(T) 下照 replay：W1 ＝ 收盤創 20 日新高 ∧ 10 日注意 Q5 ∧（5 日漲停 Q5 ∨ 5 日報酬 Q5）∧ 60 日無處置 ∧ K 棒；W2 ＝（再次處置：起日且前 60 個交易日內另有起日｜
    出關：迄日下一交易日）∧ 收盤 ≥ 含當天 20 根最高收盤 × 0.9 ∧ K 棒（＝ signals_for；Q／F ＝ s5 表、處置表 ＝ s5 main archive）：
      W1 前連 40 根沒創新高（t 起最後新高日之後 K 棒數 ≥ 40、且那天 ≥ e）⇒ 全賣｜W1（本段買進前已出現 ⇒ 當作 e）⇒ 賣 3 成｜之後 W2（買進前本段已有 ⇒ 與 3 成同一天）⇒ 賣剩 7 成｜
      任何時候收盤 ≤ t 起最高收盤 × 0.7 ⇒ 賣剩下全部；⛔ 不買回
    執行：replay(T) 認定「到 T 為止該賣到 f 成」而已下單 ＜ f ⇒ 差額在 T 之後第一個有效開盤賣（T 當天出現 ⇒ 次一開盤；錨移動讓 replay 回頭認定更早就該賣 ⇒ 也是次一開盤，
      原因註「錨移」）；錨移動讓認定的成數變小 ⇒ 不買回
    實作：t 固定時 replay 的每個判斷只用到該事件日以前的資料 ⇒ 每個 t 用全資料算一次「事件日 → 累計成數」時間表，T 那天取事件日 ≤ T 的最大成數；
      --check 逐日直接呼叫 surge_flow_daily.replay 比對
 L8 E2：持有期間（進場日收盤起）最高收盤回落 30%（收盤 ≤ 最高 × 0.7）⇒ 次一有效開盤全賣
 L9 共同：有效開盤 ＝ K 棒且還原開盤有限 ＞ 0；進場價 ＝ e 開盤（無效 ⇒ 引擎退路 e 收盤）；
    壞根（researchSurge5 S3：幽靈還原事件、價格斷點）在 e 之後出現 ⇒ 還沒賣的部分改在壞根前一根收盤出（筆數照報）；
    資料尾（2026-09-24）還沒賣 ⇒ 未完：照 T1 墊一根（以最後收盤計值、不賣不扣成本）；停止交易 ⇒ 引擎 stop_force（最後一根有效收盤 L ＜ 主窗尾 ⇒ L＋1 以 L 收盤出）
    兩個子部位（E1 3 成／7 成；E2 兩部位同日）＝ researchYL_flowexit F5 同法：合成收盤 ＝ Σ 權重 ×（還在抱 ⇒ 當日收盤；已賣 ⇒ 賣價）；xpos ＝ 最後一個子部位出場日；
    g ＝ 加權賣價 ÷ 進場價 − 1；先賣的錢留在部位裡（報酬 0）、名額到最後才釋出；成本在最後出場一次扣整筆來回
 L10 組合：research11.simulate_mtm，10 槽等權（slot ＝ 前一日權益 ÷ 10）、候選多於空位 ⇒ rng.permutation 抽籤（default_rng(20261007 ＋ r)），已過進場日不補（queue_days 0）、
    賣出款回現金給下一個新訊號；同一檔已持有 ⇒ 不再進（每筆訊號自己的合成價格鍵、cap_fn 擋同代號）；停止交易強制出場開；成本 0.585%／來回（引擎出場一次扣）
    每格報年化、回落的種子中位（比值 ＝ 年化中位 ÷ |回落中位|，researchT1fix 同式）、p10～p90
    0050 ＝ 引擎快照（rerun17 H2D）0050 還原收盤，依日期對到本件日曆；RR.bench_row 同窗；閘：主窗 0050 ＝ rerun17 錨（0.24020209886370614、−0.3395700527611012）
 L11 退化（事前排除）：探索段種子中位「平均持股 ＜ 3 檔」或「平均現金 ＞ 30%」（現金 ＝ 1 − 持股市值 ÷ 權益，逐日平均）⇒ 該格不參加挑選（照報）
 L12 挑格：探索段（0.585% 版、主母體、帶 F4）非退化格中，合格（年化 ＞ 0050 且 年化÷|MDD| ≥ 0050）者取比值最大；沒有合格 ⇒ 取比值最大的非退化格（照報它在探索段不合格）
    判定：挑中格在確認段的標籤（合格／另列＝只贏報酬／不合格）；早年段（2012-06～2014-12）：F4 季報 2013Q1 起、月底旗 2015-01 起 ⇒ 0 個月可判 ⇒「不可判定」
    （裁定 seq320 第 3 條；FEATS 早年 3 個沒資料也照報），⛔ 不硬判；兩段取較嚴 ⇒ 早年不可判定時只剩確認段、照寫；事後重切 ⇒ 兩段都合格也最多「暫定」
    現實版同表並報標籤（主要參考）；兩版標籤不同 ⇒ 照實寫
 L13 現實版（＝ researchSlip「現實版」臂逐字，營飆 v1 那組參數 N＝10）：C1 每邊 ＋0.3%（引擎成本 0.585%＋0.6%）；C2 平方根衝擊 單邊 ＝ σ20 × √(5 萬 ÷ ADV20)
    （50 萬 ÷ 10 檔；σ20、ADV20 截至前一根），進場一次、每個子部位出場各一次：g′ ＝ Σ w ×賣價 ×(1 − i出) ÷ (進場價 ×(1 ＋ i進)) − 1；
    C3 一字漲停買不到（名額持現金、不遞補）、一字跌停賣不掉（延到第一個賣得掉的開盤；每個子部位各自延）；C4 進出價 ＝ 當日 (開＋高＋低＋收)÷4（還原）；
    C5 低消 20 元：A ＝ 2.5 萬 ⇒ 20 ÷ 25,000 ＝ 0.08% ＜ 0.1425% ⇒ 公式加 0（照報）
    researchSlip.stock_extra 原函式取均價、σ20、ADV20、一字漲跌停旗；引擎 tradable（擋一字漲停買進；本件出場日已先避開一字跌停）＋ delist（下市了結）
 L14 對照：① 不帶 F4（同 k、x、E；訊號日 F4 判為否或判不出）｜② 假訊號臂（挑中格）：每筆訊號換成「同一檔、同一段（探索／確認）內隨機一根 K 棒」為訊號日 d′（進場 d′＋1），
    持有天數從挑中格訊號（已完成者）的「進場 → 最後出場」日曆位置差等機率抽，到期日（含）以後第一個有效開盤全賣；第 r 抽配組合種子 r；抽樣 default_rng(20261008 ＋ r)
    ③ 營飆 v1、營量 v1：引 resultsT1fix（t1 版主窗；現實版 slip1_real、slip13_real）｜④ 0050 同窗｜另列（描述）：不看 F4（帶與不帶合起來）
 L15 必報（逐筆 ＝ 挑中格各種子實際成交的筆，出現幾次算幾次；另報訊號層）：
    一年內先跌 15% ＝ 進場後 250 個交易日內收盤先碰到 ≤ 進場價 × 0.85（早於 ≥ × 1.15；只算觀察窗滿 250 的筆）
    吃到「起漲→頂」幾成（裁定 seq317：離頂多近）＝（加權賣價 − 起漲點收盤）÷（真頂收盤 − 起漲點收盤）；起漲點 ＝ 進場日的 replay 錨（point-in-time）、
      真頂 ＝ truetopT U8（從起漲點起最高收盤，到進場後第一次從 [起漲點, 當日] 最高回落 30% 為止）；未完的筆不算；另報買價基準（賣價 − 進場價）÷（真頂 − 進場價）（真頂高於進場價 5% 以上的筆）
    窗尾仍持有 ＝ 主窗尾 2026-08-24 收盤還在抱的檔數（種子中位）；持有天數 ＝ 進場到最後出場的有效 K 棒數；出場原因；各年報酬（同一條權益、各曆年）；
    平均每天訊號數 ＝ 段內訊號數 ÷ 段內交易日；漲停買不到 ＝ 現實版引擎 tr_limit_up；下市 ＝ 進場後停止交易（stop_force）的筆數與報酬
 L16 本件沒有用到飆股網格的句子（引描述時一律網格中位）；⛔ 不寫「N 天漲一倍」；用語「假訊號」；⛔ 不給買賣建議
輸出 backtest/resultsF4Launch/；大檔 ~/f4lwork/
"""
from __future__ import annotations

import argparse
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
from backtest import universe_gate as UG
from backtest import research11 as R
from backtest import research13 as R13
from backtest import rerun17 as RR
from backtest import researchMine as RM
from backtest import researchSurge5 as S5
from backtest import researchSurge6_overlap as O
from backtest import researchSlip as SL
from backtest import tradability as TR
from backtest.researchYL_truetopT import true_top
from backtest.surge_flow_daily import cuts_rec

UG.set_gate_v2(True)

TIME = "2026-10-07 15:40（台北）"
REG_SHA = "207e7f0db9763c36"
REGF = "登錄全文-連續虧損股起漲進場_F4加起漲特徵加從低點已漲x_登錄_台股策略線_seq1_sha207e7f0db9763c36-5266B-20261007-1423.md"
OUT = os.path.expanduser("~/tw-p17/backtest/resultsF4Launch")
WORK = os.path.expanduser("~/f4lwork")
ST = O.ST
S5W = O.WORK5
KS = (5, 10)
XS = (0.10, 0.20, 0.30, 0.50)
ES = ("E1", "E2")
CELLS = [(k, x, E) for k in KS for x in XS for E in ES]
NLOW, DEDUP = 60, 60
W0, W1 = RR.W0, RR.W1
XE, CS = "2021-12-30", "2022-01-03"
EARLY = ("2012-06-01", "2014-12-31")
SEED0, FSEED0 = 20261007, 20261008
COST_B = R.COST
SLIP_S = 0.003
CAP_Q = 500_000 / 10
C5_M, C5_A = 20, 25_000
COST_R = COST_B + 2 * SLIP_S + 2 * max(C5_M / C5_A - 0.001425, 0.0)
W30 = 0.3
REV_COLS = ("d_R2a", "d_revhi")
ANCHOR_0050 = (0.24020209886370614, -0.3395700527611012)
SEGN = {"探索": "探索 2017-03-02～2021-12-30", "確認": "確認 2022-01-03～2026-08-24", "主窗": "主窗 2017-03-02～2026-08-24"}
_G: dict = {}


def cname(k, x, E):
    return f"k{k}_x{int(round(x * 100))}_{E}"


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def sha_gate():
    p = os.path.join(RM.MAILBOX, REGF)
    h = RM.reg_sha(p)
    if h != REG_SHA:
        sys.exit(f"⛔ 登錄全文 sha {h} ≠ {REG_SHA}")
    return h


# ═════════════ F4（point-in-time 第一次公布值）═════════════
def single_eps(F, restated):
    """researchMine.load_fin 的單季 EPS 式（逐字），先把重編季的 eps_ytd、eps_q 當空值。"""
    F = F.copy()
    if restated:
        m = np.array([(s, int(y), int(q)) in restated for s, y, q in zip(F["stock_id"], F["y"], F["q"])])
        F.loc[m, ["eps_ytd", "eps_q"]] = np.nan
    K = {(s, y, q): v for s, y, q, v in zip(F["stock_id"], F["y"], F["q"], F["eps_ytd"])}
    single = []
    for s, y, q, v, vq in zip(F["stock_id"], F["y"], F["q"], F["eps_ytd"], F["eps_q"]):
        if q == 1:
            e = v
        else:
            pv = K.get((s, y, q - 1), np.nan)
            e = v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan
        if not np.isfinite(e) and np.isfinite(vq):
            e = vq
        single.append(e)
    F["eps"] = single
    return F


def restated_set():
    fd = pd.read_csv(os.path.join(RM.MAIN, "meta", "filing_dates.csv"), dtype=str)
    r = fd[fd["doc_type"].astype(str).str.contains("重編")]
    return {(s, int(y), int(q)) for s, y, q in zip(r["stock_id"], r["year"], r["season"])}


def f4_pit(log):
    z = np.load(os.path.join(RM.WORK, "flags_main.npz"))
    D.DATA = RM.MAIN; calm = D.load_calendar()
    me = pd.to_datetime(z["me"]); mepos = calm.get_indexer(me)
    assert (mepos >= 0).all(), "⛔ flags_main 月底日對不到主快照日曆"
    _, F = RM.load_fin(calm, log)
    RS = restated_set()
    out = {}
    for tag, rs in (("unmasked", set()), ("pit", RS)):
        F2 = single_eps(F, rs)
        FS = {s: g for s, g in F2.groupby("stock_id")}
        sids = z["sids"].tolist(); nm = len(me)
        A = np.zeros((nm, len(sids)), bool); OK = np.zeros((nm, len(sids)), bool)
        for j, s in enumerate(sids):
            o = RM.fin_flags_stock(s, None, FS.get(s), mepos, np.zeros(nm))
            A[:, j] = o["F4a"] | o["F4b"]; OK[:, j] = o["F4_ok"]
        out[tag] = (A, OK)
    A0, OK0 = out["unmasked"]
    gate = {"F4 不同格（不遮重編 vs flags_main）": int((A0 != z["F4"]).sum()), "F4_ok 不同格": int((OK0 != z["F4_ok"]).sum())}
    A1, OK1 = out["pit"]
    inm = z["EL"]
    rsq = {(s, y, q) for s, y, q in RS}
    diff = {"重編季數（filing_dates）": len(rsq), "重編季在 fin_hist 有列": int(sum((s, y, q) in rsq for s, y, q in zip(F["stock_id"], F["y"], F["q"]))),
            "F4 由有變無（股-月）": int((A0 & ~A1).sum()), "F4 由無變有（股-月）": int((~A0 & A1).sum()),
            "可判 → 判不出（股-月）": int((OK0 & ~OK1).sum()), "全部股-月": int(A0.size), "flags_main 帶 F4（股-月）": int(A0.sum()),
            "W1 母體內 F4 由有變無": int((A0 & ~A1 & inm).sum())}
    log(f"[F4] 閘 {gate}｜重編遮罩差異 {diff}")
    if any(v != 0 for v in gate.values()):
        raise SystemExit(f"⛔ F4 重建閘不過 {gate}")
    return {"me": me, "sids": z["sids"].tolist(), "F4": A1, "OK": OK1, "EL": z["EL"], "gate": gate, "diff": diff}


def to_days(FL, uni, cal):
    """股-日：嚴格早於 d 的最後一個月底判定日的 F4、F4_ok、EL。"""
    n = len(cal); S = len(uni)
    mpos = cal.get_indexer(FL["me"]); keep = mpos >= 0
    assert (FL["me"][~keep] > cal[-1]).all()
    mpos = mpos[keep]
    six = {s: i for i, s in enumerate(FL["sids"])}
    col = np.array([six.get(s, -1) for s in uni["stock_id"]]); has = col >= 0
    jm = np.searchsorted(mpos, np.arange(n), side="left") - 1
    out = {}
    for k in ("F4", "OK", "EL"):
        src = FL[k][keep]; A = np.zeros((S, n), bool)
        for j in np.unique(jm[jm >= 0]):
            tt = np.flatnonzero(jm == j); v = np.zeros(S, bool); v[has] = src[j, col[has]]
            A[:, tt[0]:tt[-1] + 1] = v[:, None]
        out[k] = A
    return out, int((~has).sum())


# ═════════════ 特徵、觸發 ═════════════
def rev_fix(q, bar, cal, log):
    """L3：2026 期起營收次月 15 日可用 ⇒ [e10, e15) 的營收兩欄改用 e10 前最後一根 K 棒的碼。"""
    n = len(cal); info = []
    S = bar.shape[0]
    for m in range(1, 13):
        y2, m2 = (2026, m + 1) if m < 12 else (2027, 1)
        e10 = int(cal.searchsorted(pd.Timestamp(y2, m2, 10), side="right")); e15 = int(cal.searchsorted(pd.Timestamp(y2, m2, 15), side="right"))
        if e10 >= n:
            break
        e15 = min(e15, n)
        cb = np.cumsum(bar[:, :e10], axis=1)
        lastb = np.where(cb[:, -1] > 0, e10 - 1 - np.argmax(bar[:, :e10][:, ::-1], axis=1), -1)
        ch = {}
        for col in REV_COLS:
            old = q[col][:, e10:e15].copy()
            src = np.where(lastb >= 0, q[col][np.arange(S), np.maximum(lastb, 0)], 0).astype(old.dtype)
            new = np.where(bar[:, e10:e15], src[:, None], old)
            ch[col] = int(((new != old) & bar[:, e10:e15]).sum())
            q[col][:, e10:e15] = new
        info.append({"期": f"2026-{m:02d}", "e10": str(cal[e10].date()), "e15前一日": str(cal[e15 - 1].date()), **{f"{c} 改動股-日": v for c, v in ch.items()}})
    log(f"[營收 15 日] {info}")
    return info


def triggers(bar, dlo):
    """L5：researchMineF4when 觸發（逐字）⇒ (s, d, xi)。"""
    S = bar.shape[0]; TRs, TRd, TRx = [], [], []
    for xi, x in enumerate(XS):
        for si in range(S):
            ixb = np.flatnonzero(bar[si])
            if not len(ixb):
                continue
            r = dlo[si, ixb]
            with np.errstate(invalid="ignore"):
                cand = np.flatnonzero(r >= x)
            last = -10 ** 9
            for k in cand:
                o_ = k + 1
                if o_ - last > DEDUP:
                    TRs.append(si); TRd.append(int(ixb[k])); TRx.append(xi); last = o_
    return np.array(TRs, np.int64), np.array(TRd, np.int64), np.array(TRx, np.int64)


# ═════════════ 每檔流程（E1 replay 逐日模擬、E2）═════════════
class Flow:
    def __init__(self, c, okop, bar, w1, w2, last):
        self.c = c; self.okop = okop; self.bar = bar; self.cb = np.cumsum(bar); self.w1 = w1; self.w2 = w2; self.last = last
        self.okidx = np.flatnonzero(okop[:last + 1])
        fv = np.flatnonzero(np.isfinite(c)); self.f0 = int(fv[0]) if len(fv) else 0
        self._st = {}

    def nxo(self, d):
        j = int(np.searchsorted(self.okidx, d + 1))
        return int(self.okidx[j]) if j < len(self.okidx) else None

    def anchor_of(self, T):
        lo = max(T - 249, self.f0); P0 = lo + int(np.argmax(self.c[lo:T + 1]))
        return lo + int(np.argmin(self.c[lo:P0 + 1]))

    def st_full(self, t):
        v = self._st.get(t, -2)
        if v == -2:
            seg = self.c[t:self.last + 1]; rm = np.maximum.accumulate(seg); w = np.flatnonzero(seg <= rm * 0.7)
            v = t + int(w[0]) if len(w) else None
            self._st[t] = v
        return v

    def anchor_pit(self, T, e):
        t = self.anchor_of(T)
        if e < t:
            t = self.anchor_of(e)
        for _ in range(50):
            st = self.st_full(t)
            if st is None or st >= e:
                break
            t = st + int(np.argmin(self.c[st:e + 1]))
        return t

    def timeline(self, t, e):
        """錨 t、買進日 e：replay（去買回）的「事件日、累計成數、3 成原因、7 成原因」。"""
        c = self.c; last = self.last
        stop = self.st_full(t)
        lastday = stop if stop is not None else last
        CU = cuts_rec(c[t:e + 1])
        segst = max([t + b for a, b, r in CU if t + r <= e], default=t)
        pre = segst + np.flatnonzero(self.w1[segst:e]) if (stop is None or stop > e) else np.array([], int)
        if len(pre):
            d1, d1date = e, int(pre[0])
        else:
            cand = e + np.flatnonzero(self.w1[e:lastday + 1])
            if stop is not None:
                cand = cand[cand < stop]
            d1 = int(cand[0]) if len(cand) else None; d1date = d1
        sg = c[t:lastday + 1]; r_ = np.maximum.accumulate(sg)
        isnh = np.r_[True, sg[1:] > r_[:-1]]; lastnh = t + np.maximum.accumulate(np.where(isnh, np.arange(len(sg)), 0))
        nbar = self.cb[t:lastday + 1] - self.cb[lastnh]; hh = t + np.flatnonzero(nbar >= 40); hh = hh[hh >= e]
        n40 = int(hh[0]) if len(hh) else None
        if n40 is not None and (d1 is None or n40 <= d1):
            return [(n40, 1.0, "40天沒新高", "40天沒新高")]
        if d1 is None:
            return [(stop, 1.0, "回落30%", "回落30%")] if stop is not None else []
        r30 = "W1（買進前）" if d1date < e else "W1"
        if d1date < e:
            lo2 = max(segst, d1date + 1)
            if self.w2[lo2:e].any():
                return [(e, 1.0, r30, "W2（買進前）")]
        out = [(d1, 0.3, r30, None)]
        ex1 = self.nxo(d1)
        if ex1 is None:
            return out
        w2c = ex1 + np.flatnonzero(self.w2[ex1:lastday + 1]) if ex1 <= lastday else np.array([], int)
        w2d = int(w2c[0]) if len(w2c) else None
        if w2d is None or (stop is not None and w2d >= stop):
            if stop is not None:
                out.append((stop, 1.0, None, "回落30%"))
            return out
        out.append((w2d, 1.0, None, "W2"))
        return out

    def e1_orders(self, e):
        """逐日 T：replay(T) 的累計成數 ⇒ 下單（T, 舊成數, 新成數, 3 成原因, 7 成原因, 錨移）。"""
        cache = {}; ordered = 0.0; orders = []; T = e
        while T <= self.last and ordered < 1 - 1e-12:
            t = self.anchor_pit(T, e)
            tl = cache.get(t)
            if tl is None:
                tl = cache[t] = self.timeline(t, e)
            tgt = max([f for d, f, _, _ in tl if d <= T], default=0.0)
            if tgt > ordered + 1e-12:
                d30 = next(((d, a, b) for d, f, a, b in tl if d <= T and f >= 0.3 - 1e-12), None)
                d70 = next(((d, a, b) for d, f, a, b in tl if d <= T and f >= 1 - 1e-12), None)
                r30 = (d30[1] or d30[2]) if d30 else None; r70 = d70[2] if d70 else None
                first_d = min(d for d, f, _, _ in tl if d <= T and f > ordered + 1e-12)
                orders.append((T, ordered, tgt, r30, r70, first_d < T))
                ordered = tgt
            T += 1
        return orders, len(cache)

    def e2_orders(self, e):
        seg = self.c[e:self.last + 1]; rm = np.maximum.accumulate(seg); w = np.flatnonzero(seg <= rm * 0.7)
        if not len(w):
            return []
        return [(e + int(w[0]), 0.0, 1.0, "回落30%", "回落30%", False)]


def exec_day(X, T, real):
    """T 收盤決定 ⇒ 次一可成交開盤（base：有效開盤；real：再避開停牌與一字跌停）。"""
    idx = X["ok_r"] if real else X["ok_b"]
    j = int(np.searchsorted(idx, T + 1))
    return int(idx[j]) if j < len(idx) else None


def portions(X, orders, e, real, bad_after):
    """下單 ⇒ 兩個子部位 [p30, p70]，每個 (tk, xpos, px, dlast, kind, reason, retro)。"""
    n = X["n"]; c = X["c"]; px_of = X["avg"] if real else X["o"]
    parts = {}
    for T, f0, f1, r30, r70, retro in orders:
        x = exec_day(X, T, real)
        who = []
        if f0 < 0.3 - 1e-12:
            who.append(("p30", r30))
        if f1 >= 1 - 1e-12:
            who.append(("p70", r70))
        for k_, r_ in who:
            if x is None:
                parts[k_] = (2 * n, n, float(c[n - 1]), n - 1, "end", "未完", retro)
            else:
                parts[k_] = (2 * x, x, float(px_of[x]), x - 1, "open", r_, retro)
    for k_ in ("p30", "p70"):
        if k_ not in parts:
            parts[k_] = (2 * n, n, float(c[n - 1]), n - 1, "end", "未完", False)
    if bad_after is not None:
        pb = bad_after
        for k_ in ("p30", "p70"):
            p = parts[k_]
            if p[0] > 2 * pb + 1:
                pxb = float(c[pb]) if (not real or not np.isfinite(X["avg"][pb])) else float(X["avg"][pb])
                parts[k_] = (2 * pb + 1, pb, pxb, pb, "close", "壞根", False)
    return [parts["p30"], parts["p70"]]


def finalize(parts, bp, X, e, real, i_in):
    w = (W30, 1 - W30)
    fin = max(parts, key=lambda p: p[0])
    if real:
        num = 0.0
        for wi, p in zip(w, parts):
            io = 0.0
            if p[4] != "end":
                io = X["imp"][p[1]] if np.isfinite(X["imp"][p[1]]) else 0.0
            num += wi * p[2] * (1 - min(io, 0.99))
        g = num / (bp * (1 + i_in)) - 1.0
    else:
        g = (w[0] * parts[0][2] + w[1] * parts[1][2]) / bp - 1.0
    hold = int(X["cb"][min(fin[3], X["n"] - 1)] - (X["cb"][e - 1] if e > 0 else 0))
    return {"xpos": int(fin[1]), "g": float(g), "hold": hold, "end": int(any(p[4] == "end" for p in parts)), "bad": int(any(p[4] == "close" for p in parts)),
            "x30": int(parts[0][1]), "px30": parts[0][2], "dl30": int(parts[0][3]), "r30": parts[0][5], "rt30": int(parts[0][6]),
            "x70": int(parts[1][1]), "px70": parts[1][2], "dl70": int(parts[1][3]), "r70": parts[1][5], "rt70": int(parts[1][6])}


def stock_arrays(s):
    """一檔的全日曆陣列（價格、可成交、W1／W2、壞根、衝擊）。"""
    G = _G; cal = G["cal"]; n = len(cal)
    sid = G["uni"].loc[s, "stock_id"]; mk = G["uni"].loc[s, "market"]
    D.DATA = ST
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None
    df = st.df
    c0 = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
    bar = np.isfinite(c0)
    c = pd.Series(c0).ffill().to_numpy()
    XE_ = SL.stock_extra(sid, mk, cal, n + 1)
    okop = bar & np.isfinite(o) & (o > 0)
    trd = XE_["trd"][:n]; dnl = XE_["dn_o"][:n]; upl = XE_["up_o"][:n]
    avg = XE_["avg"][:n]
    ok_r = okop & trd & ~dnl & np.isfinite(avg) & (avg > 0)
    # W1／W2（surge_flow_daily.signals_for 同式）
    idx = np.flatnonzero(bar); cb_ = c[idx]
    HI20 = np.zeros(n, bool); NEAR = np.zeros(n, bool)
    if len(idx):
        mx20 = pd.Series(cb_).rolling(20, min_periods=20).max().to_numpy(); pmx = np.r_[np.nan, mx20[:-1]]
        HI20[idx] = cb_ > pmx; NEAR[idx] = cb_ >= 0.9 * mx20
    w1 = HI20 & G["W1B"][s] & bar
    iv = G["DISP"].get(sid, []); st_ = sorted(a for a, b in iv)
    START = np.zeros(n, bool); EXIT = np.zeros(n, bool); RE60 = np.zeros(n, bool)
    for a, b in iv:
        if 0 <= a < n:
            START[a] = True
            if any(0 < a - x <= 60 for x in st_ if x != a):
                RE60[a] = True
        if 0 <= b + 1 < n:
            EXIT[b + 1] = True
    w2 = (RE60 & NEAR & bar) | (EXIT & NEAR & bar)
    # 壞根（researchSurge5 S3）
    m = len(idx); dates = cal[idx]
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); rcf = np.array(pd.to_numeric(raw["close"].reindex(cal), errors="coerce"), dtype=float); rcf[~(rcf > 0)] = np.nan
    rc = rcf[idx]; bad_k = np.zeros(m, bool)
    adj = D.load_adj(sid)
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= m:
                continue
            if k > 0 and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad_k[k] = True
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < m:
                bad_k[k] = True
    badd = idx[bad_k]
    imp = XE_["sig20"][:n] * np.sqrt(CAP_Q / XE_["adv20"][:n])
    imp = np.where(np.isfinite(imp), imp, np.nan)
    return {"sid": sid, "n": n, "c": c, "o": o, "avg": avg, "bar": bar, "okop": okop, "trd": trd, "upl": upl, "dnl": dnl,
            "ok_b": np.flatnonzero(okop), "ok_r": np.flatnonzero(ok_r), "cb": np.cumsum(bar), "w1": w1, "w2": w2, "bad": badd, "imp": imp,
            "sig20": XE_["sig20"][:n], "adv20": XE_["adv20"][:n], "nbar_mis": int((bar != G["bar"][s]).sum())}


def signal_rows(X, s, es):
    n = X["n"]; c = X["c"]
    FLW = Flow(c, X["okop"], X["bar"], X["w1"], X["w2"], n - 1)
    rows = []
    for e in es:
        bpb = float(X["o"][e]) if (np.isfinite(X["o"][e]) and X["o"][e] > 0) else float(c[e])
        bpr = float(X["avg"][e]) if (np.isfinite(X["avg"][e]) and X["avg"][e] > 0) else np.nan
        bb = X["bad"][X["bad"] > e]
        bad_after = None
        if len(bb):
            pbs = np.flatnonzero(X["bar"][:int(bb[0])]); pbs = pbs[pbs >= e]
            bad_after = int(pbs[-1]) if len(pbs) else e
        i_in = X["imp"][e] if np.isfinite(X["imp"][e]) else 0.0
        row = {"s": s, "e": int(e), "bp_b": bpb, "bp_r": bpr, "upl_e": bool(X["upl"][e]), "trd_e": bool(X["trd"][e]), "i_in": float(i_in),
               "bad_after": -1 if bad_after is None else bad_after}
        o1, nanc = FLW.e1_orders(e); o2 = FLW.e2_orders(e)
        row["E1_錨數"] = nanc
        for E, od in (("E1", o1), ("E2", o2)):
            for v, real in (("b", False), ("r", True)):
                bp = bpb if not real else bpr
                if not np.isfinite(bp):          # 現實版：進場日沒有均價（停牌等）⇒ 引擎買不到；放一列不會用到的出場讓引擎記 halt_in、⛔ 不遞補
                    row.update({f"{E}{v}_xpos": int(e) + 1, f"{E}{v}_g": 0.0, f"{E}{v}_hold": 0, f"{E}{v}_end": 0, f"{E}{v}_bad": 0,
                                f"{E}{v}_x30": int(e) + 1, f"{E}{v}_px30": float(c[e]), f"{E}{v}_dl30": int(e), f"{E}{v}_r30": "進場日無均價",
                                f"{E}{v}_rt30": 0, f"{E}{v}_x70": int(e) + 1, f"{E}{v}_px70": float(c[e]), f"{E}{v}_dl70": int(e),
                                f"{E}{v}_r70": "進場日無均價", f"{E}{v}_rt70": 0})
                    continue
                p = portions(X, od, e, real, bad_after)
                f = finalize(p, bp, X, e, real, i_in)
                row.update({f"{E}{v}_{k}": val for k, val in f.items()})
        # 必報：先跌 15%、起漲→頂
        if e + 250 <= n - 1:
            W = c[e + 1:e + 251]
            up = np.flatnonzero(W >= bpb * 1.15); dn = np.flatnonzero(W <= bpb * 0.85)
            row["up15"] = int(up[0]) + 1 if len(up) else 999; row["dn15"] = int(dn[0]) + 1 if len(dn) else 999; row["full250"] = 1
        else:
            row["up15"] = row["dn15"] = 999; row["full250"] = 0
        t0 = FLW.anchor_pit(e, e)
        Ps, Pend, done = true_top(c, t0, e, n)
        row.update({"t0": t0, "c_t0": float(c[t0]), "Ps": int(Ps), "c_Ps": float(c[Ps]), "P_done": int(done)})
        rows.append(row)
    return rows


def stock_job(s):
    X = stock_arrays(s)
    if X is None:
        return s, None, []
    rows = signal_rows(X, s, _G["ES_BY"].get(s, []))
    keep = {k: X[k] for k in ("c", "o", "avg", "bar", "okop", "trd", "upl", "dnl", "imp", "cb")}
    keep["bad"] = X["bad"]; keep["nbar_mis"] = X["nbar_mis"]; keep["ok_b"] = X["ok_b"]; keep["ok_r"] = X["ok_r"]
    return s, keep, rows


# ═════════════ prep ═════════════
def prep(a):
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run_prep.log"))
    log(f"===== researchF4Launch prep {now_tpe()}（台北）｜讀法寫死 {TIME} =====")
    log(f"[sha] {sha_gate()}")
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)
    D.DATA = ST; cal = D.load_calendar(); n = len(cal); S = len(uni)
    bar = np.load(os.path.join(S5W, "bar.npy"))
    fcol = json.load(open(os.path.join(S5W, "build.json"), encoding="utf-8"))["特徵欄"]; FX = {c: i for i, c in enumerate(fcol)}
    Qm = np.load(os.path.join(S5W, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(S5W, "F.npy"), mmap_mode="r")
    q = {col: np.array(Qm[FX[col]]) for _, col, _ in O.FEATS}
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == RR.WIN_DAYS, "⛔ 主窗與 rerun17 不同"
    # 覆蓋（早年／探索／確認）
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    segd = {"早年": (cal >= pd.Timestamp(EARLY[0])) & (cal <= pd.Timestamp(EARLY[1])),
            "探索": (cal >= pd.Timestamp(W0)) & (cal <= pd.Timestamp(XE)), "確認": (cal >= pd.Timestamp(CS)) & (cal <= pd.Timestamp(W1))}
    COV = {}
    for sg, m_ in segd.items():
        rows_ = bar & m_[None, :]
        COV[sg] = {"有K棒股-日": int(rows_.sum()), "有K棒檔數": int(rows_.any(1).sum()),
                   **{f"有值：{nm}": float((q[col][rows_] > 0).mean()) for nm, col, _ in O.FEATS}}
    rinfo = rev_fix(q, bar, cal, log)
    kk = np.zeros((S, n), np.int8)
    for nm, col, code in O.FEATS:
        kk += (q[col] == code)
    for sg, m_ in segd.items():
        rows_ = bar & m_[None, :]
        COV[sg]["k≥5 股-日比例"] = float((kk[rows_] >= 5).mean()); COV[sg]["k≥10 股-日比例"] = float((kk[rows_] >= 10).mean())
        COV[sg]["k 可達上限（有值特徵數中位）"] = float(np.median(sum((q[col][rows_] > 0).astype(np.int8) for _, col, _ in O.FEATS)))
    del q
    log(f"[覆蓋] {json.dumps(COV, ensure_ascii=False)}")
    W1B = (np.asarray(Qm[FX["att_10"]]) == 5) & ((np.asarray(Qm[FX["lu_5"]]) == 5) | (np.asarray(Qm[FX["r_5"]]) == 5)) & (np.asarray(Fm[FX["disp_60"]]) == 0) & bar
    dlo = np.asarray(Fm[FX["dlo_60"]])
    # F4
    FL = f4_pit(log)
    DY, nomiss = to_days(FL, uni, cal)
    D.DATA = ST
    for sg, m_ in segd.items():
        rows_ = bar & m_[None, :]
        COV[sg]["F4 可判（股-日）"] = float(DY["OK"][rows_].mean()); COV[sg]["帶 F4（股-日）"] = float(DY["F4"][rows_].mean())
    # 觸發
    ts, td, txi = triggers(bar, dlo)
    log(f"[觸發] 全歷史 {len(td):,}（{ {f'x{int(x*100)}': int((txi == i).sum()) for i, x in enumerate(XS)} }）")
    # 閘：F4when trig.npz
    zt = np.load(os.path.join(RM.WORK, "F4when", "trig.npz"))
    six = {s: i for i, s in enumerate(FL["sids"])}; known = np.array([s in six for s in uni["stock_id"]])
    mon5 = np.array([str(x)[:7] for x in cal])
    inwin = (mon5[td] >= "2017-03") & (mon5[td] <= "2026-08") & known[ts]
    MAPX = {0: 0, 1: 2, 2: 3, 3: 5}
    mine = set(zip(ts[inwin].tolist(), td[inwin].tolist(), [MAPX[i] for i in txi[inwin].tolist()]))
    ref = set((int(s), int(d), int(x)) for s, d, x in zip(zt["s"], zt["d"], zt["xi"]) if int(x) in MAPX.values())
    gate_tr = {"本件觸發（主窗月份、旗表內）": len(mine), "F4when trig": len(ref), "只在本件": len(mine - ref), "只在 F4when": len(ref - mine)}
    log(f"[閘 觸發] {gate_tr}")
    if gate_tr["只在本件"] or gate_tr["只在 F4when"]:
        raise SystemExit(f"⛔ 觸發閘不過 {gate_tr}")
    # 訊號表（全部觸發，帶欄位）
    e_ = td + 1; ok_e = e_ <= n - 1
    ts, td, txi, e_ = ts[ok_e], td[ok_e], txi[ok_e], e_[ok_e]
    PIT = {}
    for s in np.unique(ts):
        PIT[s] = UG.pit_valid(uni.loc[s, "stock_id"], cal, data=S5.MAIN)
    SG = pd.DataFrame({"s": ts, "sid": uni["stock_id"].to_numpy()[ts], "d": td, "e": e_, "xi": txi, "x": np.array(XS)[txi],
                       "k": kk[ts, td].astype(int), "f4": DY["F4"][ts, td], "f4ok": DY["OK"][ts, td], "el": DY["EL"][ts, td],
                       "pit": np.array([PIT[s][d] for s, d in zip(ts, td)]), "bar_d": bar[ts, td]})
    SG["日期"] = [str(cal[d].date()) for d in SG["d"]]
    SG["段"] = np.where((SG["e"] >= w0) & (SG["e"] <= int(cal.searchsorted(pd.Timestamp(XE)))), "探索",
                        np.where((SG["e"] >= int(cal.searchsorted(pd.Timestamp(CS)))) & (SG["e"] <= w1), "確認",
                                 np.where((cal[SG["d"]] >= pd.Timestamp(EARLY[0])) & (cal[SG["d"]] <= pd.Timestamp(EARLY[1])), "早年", "")))
    assert SG["bar_d"].all()
    # 60 根去重自驗
    dd_ok = True
    for (s, xi), g in SG.groupby(["s", "xi"]):
        ob = np.cumsum(bar[s])[g["d"].to_numpy()]
        dd_ok &= bool((np.diff(ob) > DEDUP).all())
    log(f"[訊號] 觸發列 {len(SG):,}｜同檔同 x 相鄰觸發都 ＞ 60 根：{dd_ok}")
    SG.to_pickle(os.path.join(WORK, "signals_all.pkl"))
    # 逐筆出場：主窗內、k ≥ 5、pit 的 (s, e)
    need = SG[(SG["段"].isin(["探索", "確認"])) & (SG["k"] >= min(KS)) & SG["pit"]]
    ES_BY = {int(s): sorted(set(g["e"].astype(int))) for s, g in need.groupby("s")}
    log(f"[出場] 要算的 (股, 進場日) {sum(len(v) for v in ES_BY.values()):,}｜股 {len(ES_BY)}")
    _, DISP = S5.SF.att_disp(S5.MAIN, cal)
    D.DATA = ST
    _G.update(cal=cal, uni=uni, bar=bar, W1B=W1B, DISP=DISP, ES_BY=ES_BY)
    sids_sig = sorted(ES_BY)
    J = {s: j for j, s in enumerate(sids_sig)}
    np.save(os.path.join(WORK, "arr_sids.npy"), np.array(sids_sig))
    MM = {k: np.lib.format.open_memmap(os.path.join(WORK, f"arr_{k}.npy"), mode="w+", dtype=dt, shape=(len(sids_sig), n))
          for k, dt in (("c", np.float64), ("o", np.float64), ("avg", np.float64), ("imp", np.float64), ("bar", bool), ("okop", bool),
                        ("trd", bool), ("upl", bool), ("dnl", bool))}
    BAD = {}; rows = []; mis = 0
    t0 = time.time()
    with Pool(a.procs) as pool:
        for i, (s, keep, rr) in enumerate(pool.imap_unordered(stock_job, sids_sig, chunksize=4)):
            if keep is None:
                log(f"[出場] ⚠ {uni.loc[s, 'stock_id']} 讀不到價格"); continue
            j = J[s]
            for k in MM:
                MM[k][j] = keep[k]
            BAD[s] = keep["bad"]; mis += keep["nbar_mis"]; rows += rr
            if i % 200 == 0:
                log(f"[出場] {i}/{len(sids_sig)}｜{time.time() - t0:.0f}s")
    for k in MM:
        MM[k].flush()
    EX = pd.DataFrame(rows)
    EX.to_pickle(os.path.join(WORK, "exits.pkl"))
    json.dump({str(k): v.tolist() for k, v in BAD.items()}, open(os.path.join(WORK, "bad.json"), "w"))
    META = {"讀法寫死": TIME, "prep": now_tpe(), "sha": REG_SHA, "日曆": [str(cal[0].date()), str(cal[-1].date()), n], "主窗": [W0, W1, w0, w1],
            "營收15日": rinfo, "覆蓋": COV, "F4 閘": FL["gate"], "F4 重編遮罩差異": FL["diff"], "flags 名冊沒有的檔": nomiss, "觸發閘": gate_tr,
            "60根去重自驗": bool(dd_ok), "K棒（load_stock vs s5 bar）不同格": int(mis), "出場列": int(len(EX)),
            "E1 錨移下單筆（b）": int(((EX.get("E1b_rt30", 0) == 1) | (EX.get("E1b_rt70", 0) == 1)).sum()) if len(EX) else 0}
    json.dump(META, open(os.path.join(WORK, "prep_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] prep {json.dumps({k: META[k] for k in ('出場列', 'K棒（load_stock vs s5 bar）不同格', 'E1 錨移下單筆（b）')}, ensure_ascii=False)}")


# ═════════════ run：組合層 ═════════════
class Syn:
    """合成收盤：Σ 權重 ×（t ≤ dlast ⇒ 當日收盤；否則賣價）。"""
    __slots__ = ("c", "p")

    def __init__(self, c, p):
        self.c = c; self.p = p

    def __getitem__(self, t):
        v = 0.0
        for w, dl, px in self.p:
            v += w * (self.c[t] if t <= dl else px)
        return v


def load_run():
    cal_n = json.load(open(os.path.join(WORK, "prep_meta.json"), encoding="utf-8"))["日曆"][2]
    sids_sig = np.load(os.path.join(WORK, "arr_sids.npy")).tolist()
    A = {k: np.load(os.path.join(WORK, f"arr_{k}.npy"), mmap_mode="r") for k in ("c", "o", "avg", "imp", "bar", "okop", "trd", "upl", "dnl")}
    return cal_n, sids_sig, A


def build_inputs(log):
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)
    D.DATA = ST; cal = D.load_calendar(); n = len(cal); NP = n + 1
    _, sids_sig, A = load_run()
    J = {s: j for j, s in enumerate(sids_sig)}
    SG = pd.read_pickle(os.path.join(WORK, "signals_all.pkl")); EX = pd.read_pickle(os.path.join(WORK, "exits.pkl"))
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    xe = int(cal.searchsorted(pd.Timestamp(XE))); cs = int(cal.searchsorted(pd.Timestamp(CS)))
    # 價格（墊一根）
    C = {}; Ob = {}; Or = {}; TRD = {}; UPL = {}
    for s in sids_sig:
        j = J[s]; c = np.asarray(A["c"][j]); C[s] = np.r_[c, c[-1]]
        Ob[s] = np.r_[np.asarray(A["o"][j]), np.nan]; Or[s] = np.r_[np.asarray(A["avg"][j]), np.nan]
        TRD[s] = np.r_[np.asarray(A["trd"][j]), False]; UPL[s] = np.r_[np.asarray(A["upl"][j]), False]
    valid = {s: np.asarray(A["bar"][J[s]]) for s in sids_sig}
    SF = R.stop_force_days(valid, w1)
    D.DATA = ST
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status({s: {"trd": valid[s]} for s in sids_sig}, cal, official=off)
    # 0050
    D.DATA = RR.H2D; calE = D.load_calendar(); bE = RR.load_bench(calE)
    bench = pd.Series(bE, index=calE).reindex(cal).ffill().to_numpy(float)
    D.DATA = ST
    Z = {}
    for nm, (a_, b_) in {"主窗": (w0, w1), "探索": (w0, xe), "確認": (cs, w1)}.items():
        assert pd.Series(bE, index=calE).reindex(cal[a_:b_ + 1]).notna().all()
        Z[nm] = RR.bench_row(cal, bench, a_, b_ + 1)
    gate0 = (repr(Z["主窗"]["cagr"]) == repr(ANCHOR_0050[0]), repr(Z["主窗"]["mdd"]) == repr(ANCHOR_0050[1]))
    log(f"[0050] {Z}｜錨逐位元 {gate0}")
    if not all(gate0):
        raise SystemExit("⛔ 0050 錨不對")
    # 年度 0050
    yrs = sorted(set(cal[w0:w1 + 1].year))
    ZY = {}
    for y in yrs:
        a_ = max(w0 - 1, int(cal.searchsorted(pd.Timestamp(y, 1, 1))) - 1); b_ = min(w1, int(cal.searchsorted(pd.Timestamp(y + 1, 1, 1))) - 1)
        ZY[y] = float(bench[b_] / bench[a_] - 1)
    return {"uni": uni, "cal": cal, "n": n, "NP": NP, "C": C, "Ob": Ob, "Or": Or, "TRD": TRD, "UPL": UPL, "SF": SF, "dl": dl, "bench": bench, "Z": Z, "ZY": ZY,
            "w0": w0, "w1": w1, "xe": xe, "cs": cs, "SG": SG, "EX": EX, "A": A, "J": J}


def arm_signals(I, k, x, grp, pop):
    SG = I["SG"]
    m = (SG["x"] == x) & (SG["k"] >= k) & SG["pit"] & SG["段"].isin(["探索", "確認"])
    if grp == "F4":
        m &= SG["f4"]
    elif grp == "NF4":
        m &= ~SG["f4"]
    if pop == "W1":
        m &= SG["el"]
    return SG[m]


def arm_frame(I, sg, E, v):
    """訊號 ⇒ 引擎 sig、closes、opens 等（每筆一個合成價格鍵 sid#e）。"""
    EX = I["EX"].set_index(["s", "e"])
    ex = EX.loc[list(zip(sg["s"].astype(int), sg["e"].astype(int)))]
    ok = ex[f"{E}{v}_xpos"].notna().to_numpy()
    sg = sg[ok]; ex = ex[ok]
    keys = [f"{sid}#{e}" for sid, e in zip(sg["sid"], sg["e"])]
    sig = pd.DataFrame({"sid": keys, "entry_pos": sg["e"].astype(int).to_numpy(), "xpos_F": ex[f"{E}{v}_xpos"].astype(int).to_numpy(),
                        "g_F": ex[f"{E}{v}_g"].astype(float).to_numpy()})
    C, Op = I["C"], (I["Ob"] if v == "b" else I["Or"])
    ss = sg["s"].astype(int).to_numpy()
    closes = {}; opens = {}; SFk = {}; trad = {}; dlk = {}; under = {}
    for key, s, dl3, px3, dl7, px7 in zip(keys, ss, ex[f"{E}{v}_dl30"].astype(int), ex[f"{E}{v}_px30"].astype(float),
                                           ex[f"{E}{v}_dl70"].astype(int), ex[f"{E}{v}_px70"].astype(float)):
        closes[key] = Syn(C[s], ((W30, dl3, px3), (1 - W30, dl7, px7)))
        opens[key] = Op[s]; under[key] = s
        if s in I["SF"]:
            SFk[key] = I["SF"][s]
        if v == "r":
            trad[key] = {"trd": I["TRD"][s], "up_o": I["UPL"][s], "dn_o": I["ZB"], "dn_c": I["ZB"]}
            if s in I["dl"]:
                dlk[key] = I["dl"][s]
    return sig, closes, opens, SFk, trad, dlk, under, ex.reset_index()


def cap_same(sid_i, t, hold):
    u = sid_i.split("#", 1)[0]
    return all(h.split("#", 1)[0] != u for h in hold)


def sim_one(sig, closes, opens, SFk, trad, dlk, v, r, NP, seed0=SEED0):
    au = []
    kw = {"tradable": trad, "delist": dlk} if v == "r" else {}
    R.COST = COST_R if v == "r" else COST_B
    try:
        o = R.simulate_mtm(sig, "F", 10, np.random.default_rng(seed0 + r), closes, opens, NP, return_equity=True, audit=au,
                           stop_force=SFk, cap_fn=cap_same, **kw)
    finally:
        R.COST = COST_B
    return o, au


def metrics(I, o, au):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    w0, w1, xe, cs = I["w0"], I["w1"], I["xe"], I["cs"]
    out = {}
    cnt = np.zeros(len(eq) + 1); opn = {}
    for a_ in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
        cnt[a_["t"]] += 1 if a_["side"] == "buy" else -1
    hc = np.cumsum(cnt)[:len(eq)]
    with np.errstate(invalid="ignore", divide="ignore"):
        cash = 1 - hv / eq
    for nm, (a_, b_) in {"主窗": (w0, w1), "探索": (w0, xe), "確認": (cs, w1)}.items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], a_, b_)
        out[f"{nm}_年化"] = float(c_); out[f"{nm}_回落"] = float(m_)
        lo = max(a_, o["first"])
        out[f"{nm}_平均持股"] = float(np.mean(hc[lo:b_ + 1])) if b_ >= lo else np.nan
        out[f"{nm}_平均現金"] = float(np.nanmean(cash[lo:b_ + 1])) if b_ >= lo else np.nan
    buys = [a_ for a_ in au if a_["side"] == "buy"]; sells = {}
    for a_ in au:
        if a_["side"] == "sell":
            sells[a_["sid"]] = a_
    out["買進筆"] = int(sum(1 for a_ in buys if w0 <= a_["t"] <= w1))
    out["窗尾持有"] = int(sum(1 for a_ in buys if a_["t"] <= w1 and (a_["sid"] not in sells or sells[a_["sid"]]["t"] > w1)))
    out["漲停買不到"] = int(o.get("tr_limit_up", 0)); out["停牌買不到"] = int(o.get("tr_halt_in", 0)); out["停止交易強制出場"] = int(o.get("x_stop_force_n", 0))
    cal = I["cal"]
    for y in sorted(set(cal[w0:w1 + 1].year)):
        a_ = max(w0 - 1, int(cal.searchsorted(pd.Timestamp(y, 1, 1))) - 1); b_ = min(w1, int(cal.searchsorted(pd.Timestamp(y + 1, 1, 1))) - 1)
        out[f"年{y}"] = float(eq[b_] / eq[a_] - 1)
    TRD = [(a_["t"], a_["sid"], a_["px"], sells[a_["sid"]]["t"] if a_["sid"] in sells else -1, sells[a_["sid"]]["px"] if a_["sid"] in sells else np.nan) for a_ in buys]
    return out, TRD


def _armjob(arm):
    G = _G; I = G["I"]
    pop, grp, cell, v = arm
    k, x, E = next((k, x, E) for k, x, E in CELLS if cname(k, x, E) == cell)
    sg = arm_signals(I, k, x, grp, pop)
    sig, closes, opens, SFk, trad, dlk = arm_frame(I, sg, E, v)[:6]
    res = []
    for r in range(G["REPS"]):
        o, au = sim_one(sig, closes, opens, SFk, trad, dlk, v, r, I["NP"])
        m, TRD = metrics(I, o, au)
        res.append((r, m, TRD if G["KEEP"].get(arm) else None))
    return arm, res, len(sig)


def label(c, m, z):
    ratio = c / abs(m) if (np.isfinite(c) and np.isfinite(m) and m < 0) else np.nan
    zr = z["cagr"] / abs(z["mdd"])
    if not np.isfinite(c):
        return "—", ratio
    return ("合格" if (c > z["cagr"] and ratio >= zr) else ("另列" if c > z["cagr"] else "不合格")), ratio


def summarize(PR, I):
    rows = []
    for arm, g in PR.groupby("arm"):
        pop, grp, cell, v = arm
        row = {"母體": pop, "群": grp, "格": cell, "版本": v, "種子": len(g)}
        for sg in ("探索", "確認", "主窗"):
            c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
            lab, rt = label(c_, m_, I["Z"][sg])
            row.update({f"{sg}_年化": c_, f"{sg}_年化p10": float(g[f"{sg}_年化"].quantile(.1)), f"{sg}_年化p90": float(g[f"{sg}_年化"].quantile(.9)),
                        f"{sg}_回落": m_, f"{sg}_比值": rt, f"{sg}_標籤": lab,
                        f"{sg}_平均持股": float(g[f"{sg}_平均持股"].median()), f"{sg}_平均現金": float(g[f"{sg}_平均現金"].median())})
        row["探索_退化"] = bool(row["探索_平均持股"] < 3 or row["探索_平均現金"] > 0.30)
        row["確認_退化"] = bool(row["確認_平均持股"] < 3 or row["確認_平均現金"] > 0.30)
        for k in ("買進筆", "窗尾持有", "漲停買不到", "停牌買不到", "停止交易強制出場"):
            row[k] = float(g[k].median())
        for c in [c for c in g.columns if c.startswith("年")]:
            row[c] = float(g[c].median())
        rows.append(row)
    return pd.DataFrame(rows)


def fake_signals(I, sgc, exc, r, E):
    """L14 ②：同一檔、同一段內隨機一根 K 棒；持有天數從挑中格抽。"""
    rng = np.random.default_rng(FSEED0 + r)
    A, J = I["A"], I["J"]; n = I["n"]
    w0, w1, xe, cs = I["w0"], I["w1"], I["xe"], I["cs"]
    hd = (exc[f"{E}b_xpos"] - exc["e"])[exc[f"{E}b_end"] == 0].to_numpy(int)
    rows = []
    for s, e, sg in zip(sgc["s"].astype(int), sgc["e"].astype(int), sgc["段"]):
        lo, hi = (w0, xe) if sg == "探索" else (cs, w1)
        bars = np.flatnonzero(np.asarray(A["bar"][J[s]][lo - 1:hi])) + lo - 1          # d′ 使 d′＋1 ∈ [lo, hi]
        if not len(bars):
            continue
        d2 = int(rng.choice(bars)); e2 = d2 + 1; k = int(rng.choice(hd)); xt = e2 + k
        rows.append((s, e2, xt))
    return rows


def fake_frame(I, rows, v, tag):
    A, J, C = I["A"], I["J"], I["C"]; n = I["n"]
    keys = []; ent = []; xp = []; gg = []; closes = {}; opens = {}; SFk = {}; trad = {}; dlk = {}; info = []
    for i, (s, e, xt) in enumerate(rows):
        j = J[s]
        if v == "b":
            ok = np.asarray(A["okop"][j]); px = np.asarray(A["o"][j])
            bp = float(px[e]) if (np.isfinite(px[e]) and px[e] > 0) else float(C[s][e])
        else:
            ok = np.asarray(A["okop"][j]) & np.asarray(A["trd"][j]) & ~np.asarray(A["dnl"][j]); px = np.asarray(A["avg"][j]); ok &= np.isfinite(px) & (px > 0)
            bp = float(px[e]) if (np.isfinite(px[e]) and px[e] > 0) else np.nan
            if not np.isfinite(bp):
                continue
        cand = np.flatnonzero(ok[xt:]) + xt if xt < n else np.array([], int)
        if len(cand):
            x = int(cand[0]); p = float(px[x]); dl_ = x - 1
            if v == "r":
                imp = np.asarray(A["imp"][j]); ii = imp[e] if np.isfinite(imp[e]) else 0.0; io = imp[x] if np.isfinite(imp[x]) else 0.0
                g = p * (1 - min(io, 0.99)) / (bp * (1 + ii)) - 1
            else:
                g = p / bp - 1
        else:
            x = n; p = float(C[s][n - 1]); dl_ = n - 1; g = p / bp - 1
        key = f"{I['uni'].loc[s, 'stock_id']}#{e}#{tag}{i}"
        keys.append(key); ent.append(e); xp.append(x); gg.append(g)
        closes[key] = Syn(C[s], ((1.0, dl_, p),)); opens[key] = (I["Ob"] if v == "b" else I["Or"])[s]
        if s in I["SF"]:
            SFk[key] = I["SF"][s]
        if v == "r":
            trad[key] = {"trd": I["TRD"][s], "up_o": I["UPL"][s], "dn_o": I["ZB"], "dn_c": I["ZB"]}
            if s in I["dl"]:
                dlk[key] = I["dl"][s]
    sig = pd.DataFrame({"sid": keys, "entry_pos": ent, "xpos_F": xp, "g_F": gg})
    return sig, closes, opens, SFk, trad, dlk


def run(a):
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchF4Launch run {now_tpe()}（台北）｜讀法寫死 {TIME}｜reps {a.reps} =====")
    sha_gate()
    I = build_inputs(log); I["ZB"] = np.zeros(I["NP"], bool)
    _G["I"] = I
    KEEP = {}
    plan = [("all", "F4", "b"), ("all", "F4", "r"), ("all", "NF4", "b"), ("all", "NF4", "r"), ("all", "ALL", "b"), ("W1", "F4", "b"), ("W1", "F4", "r"), ("W1", "NF4", "b")]
    if a.only:
        plan = [p for p in plan if f"{p[0]}_{p[1]}_{p[2]}" in a.only.split(",")]
    arms = []
    for pop, grp, v in plan:
        for k, x, E in CELLS:
            if a.cells and cname(k, x, E) not in a.cells.split(","):
                continue
            arm = (pop, grp, cname(k, x, E), v); arms.append(arm)
            KEEP[arm] = (pop == "all" and grp in ("F4", "NF4"))
    _G.update(KEEP=KEEP, REPS=a.reps)
    PR = []; TRADES = {}
    t0 = time.time()
    with Pool(a.procs) as pool:
        for i, (arm, res, nsig) in enumerate(pool.imap_unordered(_armjob, arms, chunksize=1)):
            for r, m, trd in res:
                PR.append({"arm": arm, "r": r, "訊號列": nsig, **m})
                if trd is not None:
                    TRADES[(arm, r)] = trd
            log(f"[組合] {i + 1}/{len(arms)} {arm} 訊號 {nsig}｜{time.time() - t0:.0f}s")
    PRd = pd.DataFrame(PR)
    SM = summarize(PRd, I)
    # 挑格
    base = SM[(SM["母體"] == "all") & (SM["群"] == "F4") & (SM["版本"] == "b")].copy()
    cand = base[~base["探索_退化"]]
    q_ = cand[cand["探索_標籤"] == "合格"]
    pickrow = (q_ if len(q_) else cand).sort_values("探索_比值", ascending=False).head(1)
    chosen = pickrow["格"].iloc[0] if len(pickrow) else None
    log(f"[挑格] 非退化 {len(cand)}／16、探索合格 {len(q_)} ⇒ {chosen}")
    # 假訊號臂
    FK = []
    if chosen:
        k, x, E = next((k, x, E) for k, x, E in CELLS if cname(k, x, E) == chosen)
        sgc = arm_signals(I, k, x, "F4", "all")
        exc = I["EX"].set_index(["s", "e"]).loc[list(zip(sgc["s"].astype(int), sgc["e"].astype(int)))].reset_index()
        FARM = {}
        for r in range(a.reps):
            rows = fake_signals(I, sgc, exc, r, E)
            for v in ("b", "r"):
                FARM[(r, v)] = fake_frame(I, rows, v, "f")
        _G["FARM"] = FARM
        with Pool(a.procs) as pool:
            for r, v, m in pool.imap_unordered(_fjob, [(r, v) for r in range(a.reps) for v in ("b", "r")], chunksize=2):
                FK.append({"arm": ("all", "FAKE", chosen, v), "r": r, **m})
        SMF = summarize(pd.DataFrame(FK), I)
        SM = pd.concat([SM, SMF], ignore_index=True)
    PRd = pd.concat([PRd, pd.DataFrame(FK)], ignore_index=True) if FK else PRd
    PRd["arm"] = PRd["arm"].map(lambda z: "|".join(z))
    PRd.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    SM.to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    # 逐筆（挑中格、帶 F4 對照不帶 F4）
    import pickle
    pickle.dump(TRADES, open(os.path.join(WORK, "trades.pkl"), "wb"))
    PT = trade_stats(I, TRADES, chosen, log) if chosen else {}
    SIGS = signal_stats(I, log)
    META = {"讀法寫死": TIME, "run": now_tpe(), "reps": a.reps, "0050": I["Z"], "0050 年度": I["ZY"], "挑中格": chosen,
            "探索合格格數": int(len(q_)), "非退化格數": int(len(cand)), "成本": {"b": COST_B, "r": COST_R}, "耗時秒": round(time.time() - t0)}
    json.dump(META, open(os.path.join(OUT, "meta_run.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(PT, open(os.path.join(OUT, "trades_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    SIGS.to_csv(os.path.join(OUT, "signals_summary.csv"), index=False, float_format="%.6g")
    log(f"[完] run｜挑中 {chosen}")


def _fjob(args):
    r, v = args
    sig, closes, opens, SFk, trad, dlk = _G["FARM"][(r, v)]
    o, au = sim_one(sig, closes, opens, SFk, trad, dlk, v, r, _G["I"]["NP"])
    m, _ = metrics(_G["I"], o, au)
    return r, v, m


# ═════════════ 逐筆與訊號層統計 ═════════════
def _q(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p25": float(np.percentile(x, 25)),
            "p75": float(np.percentile(x, 75)), "p90": float(np.percentile(x, 90))}


def per_trade_table(I, TRADES, arm, E, v):
    EXi = I["EX"].set_index(["s", "e"])
    sid2s = {sid: s for s, sid in enumerate(I["uni"]["stock_id"])}
    rows = []
    for (a_, r), trd in TRADES.items():
        if a_ != arm:
            continue
        for tb, key, pxb, tsell, pxs in trd:
            sid, e = key.split("#")[:2]; s = sid2s[sid]; e = int(e)
            rows.append((r, s, e, tb, pxb, tsell, pxs))
    if not rows:
        return pd.DataFrame()
    T = pd.DataFrame(rows, columns=["r", "s", "e", "tb", "pxb", "tsell", "pxs"])
    ex = EXi.loc[list(zip(T["s"], T["e"]))].reset_index(drop=True)
    T = pd.concat([T, ex], axis=1)
    T["實現報酬"] = T["pxs"] / T["pxb"] - 1 - (COST_R if v == "r" else COST_B)
    T["停止交易"] = T["s"].map(lambda s: s in I["SF"]) & (T["tsell"] >= 0) & (T["tsell"] < T[f"{E}{v}_xpos"])
    T["段"] = np.where(T["e"] <= I["xe"], "探索", "確認")
    return T


def trade_stats(I, TRADES, chosen, log):
    out = {}
    k, x, E = next((k, x, E) for k, x, E in CELLS if cname(k, x, E) == chosen)
    for grp in ("F4", "NF4"):
        for v in ("b", "r"):
            arm = ("all", grp, chosen, v)
            T = per_trade_table(I, TRADES, arm, E, v)
            if not len(T):
                continue
            T.to_pickle(os.path.join(WORK, f"trades_{grp}_{v}.pkl"))
            res = {}
            for sg in ("探索", "確認", "主窗"):
                t = T if sg == "主窗" else T[T["段"] == sg]
                fin = t[t[f"{E}{v}_end"] == 0]
                full = t[t["full250"] == 1]
                spx = W30 * fin[f"{E}{v}_px30"] + (1 - W30) * fin[f"{E}{v}_px70"]
                den = fin["c_Ps"] - fin["c_t0"]
                eat = np.where(den > 0, (spx - fin["c_t0"]) / den, np.nan)
                bpc = fin["bp_b" if v == "b" else "bp_r"]
                den2 = fin["c_Ps"] - bpc
                eat2 = np.where(den2 >= 0.05 * bpc, (spx - bpc) / den2, np.nan)
                rs30 = t[f"{E}{v}_r30"].value_counts().to_dict(); rs70 = t[f"{E}{v}_r70"].value_counts().to_dict()
                res[sg] = {"筆（各種子合計）": int(len(t)), "每顆種子平均筆": float(len(t) / max(t["r"].nunique(), 1)),
                           "實現報酬": _q(t["實現報酬"]), "勝率": float((t["實現報酬"] > 0).mean()),
                           "一年內先跌15%": float(((full["dn15"] < full["up15"])).mean()) if len(full) else np.nan,
                           "一年內先漲15%": float(((full["up15"] < full["dn15"])).mean()) if len(full) else np.nan, "觀察窗滿250筆": int(len(full)),
                           "吃到起漲→頂幾成": _q(eat), "吃到（買價基準）": _q(eat2), "未完筆": int((t[f"{E}{v}_end"] == 1).sum()),
                           "持有天數": _q(t[f"{E}{v}_hold"]), "出場原因3成": {str(k_): int(v_) for k_, v_ in rs30.items()},
                           "出場原因7成": {str(k_): int(v_) for k_, v_ in rs70.items()}, "壞根截": int(t[f"{E}{v}_bad"].sum()),
                           "錨移下單": int(((t.get(f"{E}{v}_rt30", 0) == 1) | (t.get(f"{E}{v}_rt70", 0) == 1)).sum()) if E == "E1" else 0,
                           "停止交易（下市等）筆": int(t["停止交易"].sum()), "停止交易筆實現報酬": _q(t.loc[t["停止交易"], "實現報酬"]),
                           "進場日一字漲停（訊號層）": int(t["upl_e"].sum())}
            out[f"{grp}|{v}"] = res
            log(f"[逐筆] {grp} {v} 主窗 {res['主窗']['筆（各種子合計）']} 筆")
    return out


def signal_stats(I, log):
    """訊號層（每格、群、母體）：每天訊號數、先跌 15%、吃到幾成（E1／E2，base）、平均持有。"""
    cal = I["cal"]; rows = []
    nday = {"探索": int(I["xe"] - I["w0"] + 1), "確認": int(I["w1"] - I["cs"] + 1)}
    EXi = I["EX"].set_index(["s", "e"])
    for pop in ("all", "W1"):
        for grp in ("F4", "NF4", "ALL"):
            for k, x, E in CELLS:
                sg = arm_signals(I, k, x, grp, pop)
                if not len(sg):
                    continue
                ex = EXi.loc[list(zip(sg["s"].astype(int), sg["e"].astype(int)))].reset_index(drop=True)
                ex["段"] = sg["段"].to_numpy()
                for seg in ("探索", "確認"):
                    t = ex[ex["段"] == seg]
                    fin = t[t[f"{E}b_end"] == 0]; full = t[t["full250"] == 1]
                    spx = W30 * fin[f"{E}b_px30"] + (1 - W30) * fin[f"{E}b_px70"]; den = fin["c_Ps"] - fin["c_t0"]
                    eat = np.where(den > 0, (spx - fin["c_t0"]) / den, np.nan)
                    rows.append({"母體": pop, "群": grp, "格": cname(k, x, E), "段": seg, "訊號數": int(len(t)), "每天訊號": len(t) / nday[seg],
                                 "一年內先跌15%": float((full["dn15"] < full["up15"]).mean()) if len(full) else np.nan,
                                 "吃到起漲→頂中位": float(np.nanmedian(eat)) if np.isfinite(eat).any() else np.nan,
                                 "持有天數中位": float(t[f"{E}b_hold"].median()) if len(t) else np.nan,
                                 "逐筆報酬平均（未扣成本、訊號層）": float(t[f"{E}b_g"].mean()) if len(t) else np.nan,
                                 "未完": int((t[f"{E}b_end"] == 1).sum()), "進場日一字漲停": int(t["upl_e"].sum())})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="prep")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--only", default=""); ap.add_argument("--cells", default="")
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a)
    elif a.cmd == "run":
        run(a)
    elif a.cmd == "page":
        from backtest import researchF4Launch_page as PG
        PG.page()


if __name__ == "__main__":
    main()

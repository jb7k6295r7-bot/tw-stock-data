# -*- coding: utf-8 -*-
"""PREREG營量營飆漲多加碼大盤濾網 seq2（台股策略線 sha ac703a66dbd7ffcc，2026-10-13 22:26；裁定 seq345 核准、N 不變）——定版：
歷史段重算（描述、最多暫定）＋前瞻樣本門檻（寫死）＋挑選偏誤＋隨機擋＋成交滑價＋年代交互作用＋前瞻記帳函式——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議；⭐ 判定只看前瞻（裁定 seq344／345），本檔歷史數字全是描述。

    定版重算：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnMkt_v2 [--procs 3]
    前瞻記帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnMkt_v2 --forward [--sha <main sha>] [--asof YYYY-MM-DD] [--path <csv>]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnMkt_v2_check

⭐ 讀法寫死 2026-10-14 00:20（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何「營量 A2＋營飆 A1」口徑的數字
   （看過的：登錄全文 seq1／seq2、台股 2226、裁定 seq344／345、回測 1847／1901／1910／2009／2012／2122 與其程式、mkt／ext 初測輸出〔400 筆口徑〕）

═══ 讀法（V 標；登錄沒寫清楚、執行者補的都在這裡）═══
 V0 登錄 sha 驗證（AO.reg_check 同式：去掉 pw1 行後 sha256 前 16 碼）＝ ac703a66dbd7ffcc
 V1 加權指數 ＝ 公開庫 tw-stock-data main（執行時 origin/main，git show 釘 sha，記在 json）data/history/market_index.csv 的 close；⛔ 不讀私有庫
    大盤旗標(t) ＝ 指數自己的日序列上「t 收盤 ＞ 含 t 最近 20 筆收盤平均」（不足 20 筆 ⇒ 缺）；事件日 ＝ 世界日曆 cal[t]；事件日在指數裡缺 ⇒ 停
    閘：與初測 ext_rows 的 G3a_多頭（私有庫算的）在同一筆事件上逐筆相同（只比對布林、不讀私有庫）
 V2 觸發 ＝ researchAddOn U2／U3／U4 逐式重算（AO.market／thresholds／hold_info；世界、引擎讀 ~/addonwork 快取，引擎 eq_sha 對 resultsYL_integrate）；
    閘：重算的 觸發表（3,614 列）與 resultsAddOn/triggers.csv.gz 逐列相同
    ⭐ 登錄 §一 格寫死：營量 A2（q99）、營飆 A1（q95）——⚠ 初測 400 筆（ext／mkt）是「同一筆持股 A1、A2 都有取 A1」⇒ 營量多用了 A1；本件只用登錄格；
       初測口徑另列「對照」（描述，不是本件數字）
    唯一事件 ＝ 世界×策略×sid×tb（營飆 200 顆去重）；段（依 ta）：探索 (523, 1711]、確認 (1711, 2835]、主窗 (523, 2835]（同 feat）；早年 (249, 2711]
    金額（逐筆診斷用）＝ 持有該筆的路徑 audit 金額平均（同 ext：起始權益 ＝ 1 的單位；營飆 ＝ 持有該筆的種子平均）
 V3 成交（登錄 §一）：ta ＝ t＋1 開盤；鎖漲停 ＝ ta 原始 最高 ＝ 最低 且 原始開盤 ≥ 漲停價 − 1e−6；
      漲停價 ＝ research11.limit_price(參考價, 漲, 限幅)，限幅 ＝ 7%（ta ＜ 2015-06-01）／10%；參考價 ＝ 原始收盤[t] × 還原因子[t] ÷ 還原因子[ta]（因子 ＝ 世界還原收盤 ÷ 原始收盤；ta 是除權息日時把參考價換到除權後）
      另列「一字且開盤 ≥ 參考價 ×(1＋限幅−1%)」（容許除權息參考價取整差）與兩者不一致筆數；鎖漲停 ⇒ 濾網版、無條件版都不加（記「未成交」）
    跳空 ＝ 還原開盤[ta] ÷ 還原收盤[t] − 1；「開盤漲停（含未鎖）」＝ 原始開盤 ≥ 漲停價 − 1e−6
 V4 出場（登錄 §二）＝ AO.main_exit（原持股同日同價；(ta, xbar] 有壞根 ⇒ 壞根前收盤強制）；每筆淨報酬 r ＝ 賣價×(1−s) ÷ (加碼價×(1＋s)) − 1 − 0.585%，s ∈ {0, 0.5%, 1%}（每邊）
    資料尾仍持有（無出場）⇒ 逐筆統計不算（照報筆數）；記帳以段尾收盤計值
 V5 加碼子帳戶（主判單位，登錄 §三）：每條路徑（營量 r＝0；營飆 r＝0～199）、每段；只收 ta ∈ (max(段首, first), min(段尾, end−1)] 且可成交（非鎖漲停）
      無條件版 ＝ 全部可成交觸發；濾網版 ＝ 其中大盤旗標成立者
    帳：加碼在開盤先用子帳戶現金 K（前面出場收回的錢），不足才撥入 F；出場收回 A ×(賣價÷加碼價 − 0.585%) 入 K（同 AO.account）；
      撥入峰值 I ＝ ΣF（段首就預留，閒置現金報酬 0）；NAV_t ＝ (I − 累計 F_t) ＋ K_t ＋ 在外市值 MV_t（還原收盤 ÷ 加碼價 × A）
    報：淨損益 ＝ NAV_段尾 − I（起始權益 ＝ 1 的單位）；年化 ＝ (NAV_尾 ÷ I)^(245 ÷ (段長−1)) − 1；最大回落 ＝ NAV 的最大回落；
      資金使用率 ＝ 段內逐日 MV ÷ NAV 的平均（另報峰值）；I；筆數
    營飆 ＝ 200 顆中位（另報 p10／p90 與「濾網版淨損益 ＞ 無條件版」的顆數比例）；合計 ＝ 營量 r0 ＋ 營飆第 r 顆兩個子帳戶相加（200 組中位；兩策略起始權益都是 1）
    滑價每邊 0.5%、1%：加碼價 ×(1＋s)、賣價 ×(1−s) 重算子帳戶（主判）與逐筆差
 V6 組合三版（必報、⛔ 不判）：原策略、原＋無條件、原＋濾網；AO.account 讀法 A（累計撥入）、B（峰值撥入）＋ AO.metrics（年化、最大回落 ＝ rerun17.win_metrics）；營飆 200 顆中位；比值 ＝ 年化中位 ÷ |回落中位|
 V7 逐筆診斷（⛔ 不單獨判）：唯一事件、可成交、已出場；留下 − 被擋 的平均差（③）、中位差、賺錢比例、賠 ＞15% 比例；
      ① ＝ −Σ_被擋 金額 × r（＝ 唯一事件口徑的「濾網版 − 無條件版」淨損益）；CI ＝ 按加碼月（世界|年月）群集 bootstrap 5000 次（兩組共用月集合重抽）
      去右尾：依 r 去掉最高 1%、5%（段內、向上取整筆數）後的 ③ 與 ①；逐年（依 ta 年）；營量／營飆分開；上市／上櫃分開
 V8 原持股同期（必報「是不是原策略本來就在大盤弱時差」）：所有唯一原持股（兩策略、不分是否觸發）在每個 t ∈ [tb＋9, xbar−1]：t 有 K 棒、(tb, t＋1] 無壞根、
      t＋1 有有效開盤、原持股有出場 ⇒ r(t) ＝ 原持股賣價 ÷ 開盤[t＋1] − 1 − 0.585%（「那天隨便加一份」）；依 t 的大盤旗標分兩組；
      報 持有日加權 與 每檔先平均 兩種；差 CI ＝ 按 t＋1 月群集；段依 t＋1
 V9 隨機擋（必報、前瞻判定 c 的歷史版）：每段、唯一可成交已出場事件，隨機擋掉與真實同數量的事件 1,000 次（default_rng(SEED＋1)）；
      報真實 ③、① 的排名 ＝ 隨機值 ≥ 真實值的比例（＜ 5% ＝ 排在前 5%）
 V10 挑選過程重跑（描述、⛔ 不判）：族 ＝ 加權 MA5／10／20／40／60／120／200 站上（7）、MA20 斜率正（MA20_t ＞ MA20_{t−5}）、
      站上×斜率 四格（4）、站上或斜率正、連續站上 ≥ 5 日、剛站上（1～5 日）、已站上多日（≥ 6 日）、廣度（R1／全檔 × 收盤 ＞ 自身 MA20／MA60 比例 ＞ 50%）（4）＝ 20 個
      （廣度同 researchAddOn_mkt M2③）；另列「＋0050 MA 七個」＝ 27 個（描述）
      平移 k ＝ 21～250 交易日：每個成員用 t−k 的旗標（指數成員在指數日序列上平移、廣度／0050 在世界日曆上平移），算主窗 ③（兩組各 ≥ 5 筆才算），取族內最大；
      真實 MA20 ③（不平移）在 230 個「挑出來的最好」中的百分位 ＝ 比它小的比例；＜ 95% ⇒ 結果句加「歷史結果不足以排除挑選巧合」；同法報 ①
      另列：初測 400 筆口徑（MA20 實際被挑出的那批）同法重跑（描述）
 V11 年代交互作用：③_早年 − ③_主窗 與 ①（÷ 段內可成交金額合計，正規化）的差；CI ＝ 兩年代各自按月群集獨立重抽 5000 次相減
 V12 前瞻門檻 ②（檢定力）：母體 ＝ 主窗（2017～）唯一可成交已出場事件，依 r 去掉最高 5%（向上取整）；
      S1（主）＝ 去右尾後的差就是真效果；S2（敏感度）＝ 被擋組平移成差恰為 +10 點；S1 差 ≤ 0 ⇒ 改用 S2 當主
      模擬：按月區塊拔靴（有事件的月等機率、放回）一直抽到累計觸發 ≥ N；檢定 ＝ 群集穩健 z（群集 ＝ 抽到的月塊）＞ 1.645（單尾 5%，登錄 ②）；
      N ＝ 40～1000 每 20；每格 2,000 次（default_rng(SEED＋2)）；N* ＝ 最小的 N 使檢定力 ≥ 80% 且其後各格都 ≥ 80%；B* ＝ N* 時被擋筆數中位（向上取整）
      門檻（寫死）＝ 觸發 ≥ max(80, N*)、被擋 ≥ max(20, B*)；另報 N* 時 兩尾 95%（z ＞ 1.96）檢定力、三條（a 子帳戶淨損益較高、b、c 隨機擋 200 次排前 5%）同時成立的機率
      年數 ＝ 依主窗每條路徑的觸發頻率（營量 r0 ＋ 營飆 200 顆中位；含鎖漲停）推到第一個「12 月最後交易日」檢查點；另列唯一事件頻率
 V13 櫃買指數版：公開庫 main 沒有櫃買指數 ⇒ 資料未到位、不描述（⛔ 不讀私有庫）
 V14 前瞻記帳（forward_update）：見函式說明；欄位 ＝ FWD_COLS；起點 FWD_START
輸出 backtest/resultsAddOn/mkt_v2/：mkt_v2.json、events.csv、paths.csv.gz、years.csv、family_shift.csv、power.csv、forward_template.csv、run.log
── 事後註（寫死之後、照實記）──
 ① 00:22 第一次全跑後查前瞻函式時發現：引擎對「世界日曆尾還沒到出場日」的持股，在墊根位置（日曆之後一格）以最後收盤了結，
    AO.main_exit 照樣回傳成「同原持股」出場 ⇒ 這是資料尾計值、不是真出場。照 V4 原意（資料尾仍持有 ⇒ 逐筆統計不算）改為：
    出場根 ≥ 世界日曆長度 ⇒ 標「資料尾計值」、逐筆 r 記缺（另存 r0_含資料尾）；子帳戶記帳不受影響（這些出場根都在段尾之後，本來就以段尾收盤計值）。
    影響：主窗 2 筆（營飆 8042、5328，2026-06 加碼）、早年 1 筆（營飆 3285，2014-09）；重跑後交件數字 ＝ 這一版
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import math
import os
import pickle
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa: E402
from backtest import research11 as R11                        # noqa: E402

REPO = os.path.expanduser("~/tw-p17")
REG_SHA = "ac703a66dbd7ffcc"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsAddOn/mkt_v2"
TIME = "2026-10-14 00:20（台北）"
SEED = 20261014
NB = 5000
NRAND = 1000
SLIPS = (0.0, 0.005, 0.01)
CELL = {"營量": "A2", "營飆": "A1"}
HOLD = {"營量": 60, "營飆": 120}
MA_N = 20
LENS = (5, 10, 20, 40, 60, 120, 200)
LAGS = tuple(range(21, 251))
YEAR = 245
COST = AO.COST
LU_CUT = pd.Timestamp("2015-06-01")
SEGU = {"探索": (523, 1711), "確認": (1711, 2835), "主窗": (523, 2835), "早年": (249, 2711)}   # 唯一事件段（ta ∈ (x, y]），同 feat
SEGW = {"探索": "主", "確認": "主", "主窗": "主", "早年": "早年"}
SEGN = ("探索", "確認", "主窗", "早年")
NGRID = tuple(range(40, 1001, 20))
NSIM = 2000
FWD_START = "2026-10-14"                                      # 定版日（前瞻只記 t ≥ 此日的第一次觸發）
SENT = ["營量、營飆已看過結果，本件最多暫定；以前瞻為準", "從約 50 個比較中挑出", "2005～2014 不成立是反證，未解釋前 ⛔ 不可稱有效",
        "2017 以後有效、2005～2014 無效", "效果主要是避開大盤弱勢時加碼", "金額上的改善尚不顯著",
        "加碼用的是另外的錢；⛔ 不代表該把原策略的錢集中到漲最多的那檔"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）"]
SENT_SEL = "歷史結果不足以排除挑選巧合"


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def jdef(v):
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if hasattr(v, "item"):
        return v.item()
    return str(v)


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ 指數（公開庫）═════════════
def main_sha(ref="origin/main"):
    return subprocess.run(["git", "-C", REPO, "rev-parse", ref], capture_output=True, text=True, check=True).stdout.strip()


def load_index(sha):
    txt = subprocess.run(["git", "-C", REPO, "show", f"{sha}:data/history/market_index.csv"], capture_output=True, text=True, check=True).stdout
    df = pd.read_csv(io.StringIO(txt))
    s = pd.Series(pd.to_numeric(df["close"], errors="coerce").to_numpy(float), index=pd.to_datetime(df["date"])).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s = s[s > 0]
    return s, hashlib.sha256(txt.encode()).hexdigest()[:16]


def index_flags(tx):
    """指數日序列上的各成員旗標（float：1／0／nan）。"""
    c = tx.to_numpy(float); n = len(c)
    F = {}
    MA = {L: pd.Series(c).rolling(L, min_periods=L).mean().to_numpy() for L in LENS}
    for L in LENS:
        F[f"TX_MA{L}"] = np.where(np.isfinite(MA[L]), (c > MA[L]).astype(float), np.nan)
    m20 = MA[20]; m20s = np.r_[np.full(5, np.nan), m20[:-5]]
    sl = np.where(np.isfinite(m20) & np.isfinite(m20s), (m20 > m20s).astype(float), np.nan)
    st = F["TX_MA20"]
    F["TX_斜率正"] = sl
    ok = np.isfinite(st) & np.isfinite(sl)
    for nm, f in (("Q_站上斜率正", lambda a, b: a & b), ("Q_站上斜率非正", lambda a, b: a & ~b), ("Q_未站上斜率正", lambda a, b: ~a & b),
                  ("Q_未站上斜率非正", lambda a, b: ~a & ~b), ("TX_站上或斜率正", lambda a, b: a | b)):
        v = f(np.nan_to_num(st).astype(bool), np.nan_to_num(sl).astype(bool)).astype(float)
        F[nm] = np.where(ok, v, np.nan)
    a = np.nan_to_num(st).astype(bool); k = np.zeros(n, int)
    for i in range(n):
        k[i] = (k[i - 1] + 1 if i else 1) if a[i] else 0
    okk = np.isfinite(st)
    F["TX_連5"] = np.where(okk, (k >= 5).astype(float), np.nan)
    F["TX_剛站上"] = np.where(okk, ((k >= 1) & (k <= 5)).astype(float), np.nan)
    F["TX_已站上多日"] = np.where(okk, (k >= 6).astype(float), np.nan)
    return F


# ═════════════ 世界、觸發（AO 逐式）═════════════
def build(log, procs):
    WS = AO.worlds(log, procs)
    gates = {}
    for wn, W in WS.items():
        gates.update({f"{wn}·{k}": v for k, v in W["gate"].items()})
    ENG = pickle.load(open(os.path.join(AO.WORK, f"engine_{AO.NSEED}.pkl"), "rb"))
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    bad = sum(int(AO.IG.sha(E["eq"]) != REF[(wn, AO.STRATS[sn], r)]) for (wn, sn, r), E in ENG.items())
    gates["引擎 eq_sha ≠ resultsYL_integrate（條數）"] = bad; gates["引擎條數"] = len(ENG)
    log(f"[引擎] 讀快取 {len(ENG)} 條｜eq_sha 不同 {bad}")
    if bad or len(ENG) != 402:
        raise SystemExit("⛔ 引擎閘不過")
    from backtest import universe_gate as UG
    UG.set_gate_v2(True)
    RAWH = {key: AO.holdings(E["au"]) for key, E in ENG.items()}
    XPOS = {}
    for wn, W in WS.items():
        base = W["SIG"][False]
        XPOS[wn] = {H: {(s, int(e)): int(x) for s, e, x in zip(base["sid"], base["entry_pos"], base[f"xpos_H{H}"])} for H in (60, 120)}
    AO._G["XPOS"] = XPOS
    HI = {}; X = None; MW = {}; MINFO = {}
    for wn in ("主", "早年"):
        W = WS[wn]; uh = {}
        for (w_, sn, r), Hs in RAWH.items():
            if w_ != wn:
                continue
            for sid, tb, amt, ep, ts, pxs in Hs:
                hk = (wn, sn, sid, tb)
                if hk in uh and uh[hk] != (ep, ts, pxs):
                    raise SystemExit(f"⛔ 同一筆持股在不同種子出場不同 {hk}")
                uh[hk] = (ep, ts, pxs)
        hold_sids = sorted({hk[2] for hk in uh})
        M, HB, X, info = AO.market(wn, W, X, log, hold_sids)
        MINFO[wn] = info; MW[wn] = M
        HMAX = max(max(min(AO._xb(W, hk, v), len(W["cal"])) - hk[3] for hk, v in uh.items()), AO.HMIN)
        t_lo = min(hk[3] for hk in uh) + AO.HMIN - 1
        Q, NPOP = AO.thresholds(M, HMAX, t_lo, log, wn)
        for hk, (ep, ts, pxs) in uh.items():
            HI[hk] = AO.hold_info(wn, hk[1], W, HB, hk[2], hk[3], ep, ts, pxs, Q)
        log(f"[{wn}] 唯一持股 {len(uh)}")
    AO._G["HI"] = HI; AO._G["NCAL"] = {wn: len(W["cal"]) for wn, W in WS.items()}
    PATHH = {key: [((key[0], key[1], sid, tb), amt) for sid, tb, amt, ep, ts, pxs in Hs] for key, Hs in RAWH.items()}
    # 閘：觸發表 vs resultsAddOn/triggers.csv.gz
    TR = []
    for hk, I in HI.items():
        for c in AO.CELLS:
            tr, why = I["trig"][c]
            TR.append({"世界": hk[0], "策略": hk[1], "sid": hk[2], "tb": hk[3], "格": c, "結果": why, "xbar": I["xbar"],
                       **({k: tr[k] for k in ("t", "h", "g", "q", "ta", "ep_a")} if tr else {})})
    TR = pd.DataFrame(TR)
    old = pd.read_csv("backtest/resultsAddOn/triggers.csv.gz", dtype={"sid": str})
    key = ["世界", "策略", "sid", "tb", "格"]
    m = TR.merge(old, on=key, how="outer", suffixes=("", "_o"), indicator=True)
    g = {"觸發表列數 新／舊": [int(len(TR)), int(len(old))], "只在一邊的列": int((m["_merge"] != "both").sum()),
         "結果不同": int((m["結果"] != m["結果_o"]).sum())}
    for c in ("t", "h", "ta", "xbar"):
        a_, b_ = m[c].to_numpy(float), m[c + "_o"].to_numpy(float)
        g[f"{c} 不同"] = int(((np.isfinite(a_) != np.isfinite(b_)) | (np.isfinite(a_) & np.isfinite(b_) & (a_ != b_))).sum())
    for c in ("g", "q", "ep_a"):
        a_, b_ = m[c].to_numpy(float), m[c + "_o"].to_numpy(float)
        ok = np.isfinite(a_) & np.isfinite(b_)
        g[f"{c} 最大相對差"] = float(np.max(np.abs(a_[ok] / b_[ok] - 1.0))) if ok.any() else 0.0
    gates["觸發重算 vs triggers.csv.gz"] = g
    log(f"[閘 觸發] {g}")
    if g["只在一邊的列"] or g["結果不同"] or any(g[f"{c} 不同"] for c in ("t", "h", "ta", "xbar")) or max(g[f"{c} 最大相對差"] for c in ("g", "q", "ep_a")) > 1e-9:
        raise SystemExit("⛔ 觸發重算閘不過")
    return WS, ENG, HI, PATHH, MW, MINFO, gates


def load_raw(data, sid, cal):
    p = os.path.join(data, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    bad = (raw[["open", "high", "low", "close"]] <= 0).any(axis=1)
    raw.loc[bad, ["open", "high", "low", "close"]] = np.nan
    return raw.reindex(cal)


def lock_info(ro, rh, rl, rc, cadj, t, ta, day):
    """⇒ (鎖漲停, 開盤漲停, 一字且≥參考×(1＋限幅−1%), 參考價來源)；ro／rh／rl／rc 原始、cadj 還原收盤（同日曆）。"""
    lim = 0.07 if day < LU_CUT else 0.10
    f_t = cadj[t] / rc[t] if (np.isfinite(rc[t]) and rc[t] > 0) else np.nan
    f_a = cadj[ta] / rc[ta] if (np.isfinite(rc[ta]) and rc[ta] > 0) else np.nan
    if not np.isfinite(f_t):
        return False, False, False, "t 無原始收盤"
    ref = rc[t] * (f_t / f_a) if np.isfinite(f_a) else rc[t]
    lup = R11.limit_price(float(ref), True, lim)
    o, h, l = ro[ta], rh[ta], rl[ta]
    if not (np.isfinite(o) and np.isfinite(h) and np.isfinite(l)):
        return False, False, False, "ta 原始價缺"
    one = abs(h - l) < 1e-9
    up_o = o >= lup - 1e-6
    alt = one and (o / ref - 1.0 >= lim - 0.01)
    return bool(one and up_o), bool(up_o), bool(alt), ("除權息換算" if (np.isfinite(f_a) and abs(f_a / f_t - 1) > 1e-6) else "前收")


def events(WS, HI, PATHH, tx, TXF, log):
    """登錄格的唯一事件。"""
    amts = {}
    for key, HL in PATHH.items():
        for hk, amt in HL:
            amts.setdefault(hk, []).append(amt)
    txpos = {d: i for i, d in enumerate(tx.index)}
    RAW = {}; rows = []
    for hk, I in HI.items():
        wn, sn, sid, tb = hk
        tr, why = I["trig"][CELL[sn]]
        if tr is None:
            continue
        W = WS[wn]; cal = W["cal"]; n = len(cal)
        t, ta = tr["t"], tr["ta"]
        sg = [s for s in ("探索", "確認", "早年") if SEGW[s] == wn and SEGU[s][0] < ta <= SEGU[s][1]]
        d = cal[t]
        if d not in txpos:
            raise SystemExit(f"⛔ 事件日 {d.date()} 指數缺")
        p = txpos[d]
        flag = TXF["TX_MA20"][p]
        if not np.isfinite(flag):
            raise SystemExit(f"⛔ 事件日 {d.date()} MA20 缺")
        if (wn, sid) not in RAW:
            RAW[(wn, sid)] = load_raw(W["data"], sid, cal)
        rw = RAW[(wn, sid)]
        cl = np.asarray(W["closes"][sid][:n], float); op = np.asarray(W["opens"][sid][:n], float)
        ro, rh, rl, rc = (rw[c].to_numpy(float) for c in ("open", "high", "low", "close"))
        lk, upo, alt, refsrc = lock_info(ro, rh, rl, rc, cl, t, ta, cal[ta])
        sd, px, xb, kind = AO.main_exit(hk, ta)
        ep = tr["ep_a"]
        o = {"世界": wn, "策略": sn, "sid": sid, "tb": tb, "格": CELL[sn], "t": t, "ta": ta, "h": tr["h"], "g": tr["g"], "q": tr["q"],
             "日期t": str(d.date()), "加碼日": str(cal[ta].date()), "段": sg[0] if sg else "段外", "加碼月": str(cal[ta])[:7],
             "clu": f"{wn}|{str(cal[ta])[:7]}", "年": int(cal[ta].year), "市場": W["uni"].get(sid, "twse"),
             "大盤旗標": bool(flag), "指數位置": p, "鎖漲停": lk, "開盤漲停": upo, "一字近漲停": alt, "參考價": refsrc,
             "跳空": float(op[ta] / cl[t] - 1.0), "加碼價": ep, "出場根": sd, "出場價": px, "出場種類": kind,
             "金額": float(np.mean(amts.get(hk, [np.nan]))), "種子數": len(amts.get(hk, []))}
        o["資料尾計值"] = bool(px is None or sd >= n)                    # 引擎在墊根（世界日曆之後）以最後收盤了結 ＝ 未真正出場
        o["r0_含資料尾"] = (px / ep - 1.0 - COST) if px is not None else np.nan
        for s in SLIPS:
            o[f"r{int(s * 1000)}"] = (px * (1 - s) / (ep * (1 + s)) - 1.0 - COST) if (px is not None and not o["資料尾計值"]) else np.nan
        rows.append(o)
    E = pd.DataFrame(rows)
    E["可成交"] = ~E["鎖漲停"]
    E["已出場"] = E["r0"].notna()
    log(f"[事件] 登錄格唯一事件 {len(E)}｜段 {E['段'].value_counts().to_dict()}｜鎖漲停 {int(E['鎖漲停'].sum())}")
    return E


# ═════════════ 子帳戶 ═════════════
def subacct(x, y, pos, HI):
    """pos：[(ta, A, ep, hk, sd, px)]（ta ∈ (a, y] 已篩）。⇒ dict（NAV 長 y−x+1）。"""
    L = y - x + 1
    MV = np.zeros(L); ADD = np.zeros(L); PROC = np.zeros(L)
    for (ta, A, ep, hk, sd, px) in pos:
        cl = HI[hk]["cl"]
        e2 = min(sd if sd is not None else y + 1, y + 1)
        if e2 > ta:
            MV[ta - x:e2 - x] += A * np.asarray(cl[ta:e2], float) / ep
        ADD[ta - x] += A
        if sd is not None and sd <= y:
            PROC[sd - x] += A * (px / ep - COST)
    K = 0.0; F = np.zeros(L); Kc = np.zeros(L)
    for i in range(L):
        if ADD[i] > 0:
            u = min(K, ADD[i]); K -= u; F[i] = ADD[i] - u
        if PROC[i] != 0.0:
            K += PROC[i]
        Kc[i] = K
    I = float(F.sum())
    NAV = (I - np.cumsum(F)) + Kc + MV
    o = {"n": len(pos), "I": I, "NAV": NAV}
    if I <= 0:
        o.update(淨損益=0.0, 年化=np.nan, 回落=np.nan, 使用率=np.nan, 使用率峰值=np.nan)
        return o
    o["淨損益"] = float(NAV[-1] - I)
    o["年化"] = float((NAV[-1] / I) ** (YEAR / (L - 1)) - 1.0)
    pk = np.maximum.accumulate(NAV); o["回落"] = float((NAV / pk - 1.0).min())
    u = MV / NAV; o["使用率"] = float(u.mean()); o["使用率峰值"] = float(u.max())
    return o


def nav_stats(NAV, I, L):
    if I <= 0:
        return {"淨損益": 0.0, "年化": np.nan, "回落": np.nan}
    pk = np.maximum.accumulate(NAV)
    return {"淨損益": float(NAV[-1] - I), "年化": float((NAV[-1] / I) ** (YEAR / (L - 1)) - 1.0), "回落": float((NAV / pk - 1.0).min())}


def paths(WS, ENG, HI, PATHH, EV, log):
    """每條路徑 × 段 × 滑價：子帳戶兩版；滑價 0 另算組合三版。"""
    rows = []; NAVS = {}
    evd = {(r["世界"], r["策略"], r["sid"], r["tb"]): r for r in EV.to_dict("records")}
    for key in sorted(ENG):
        wn, sn, r = key
        E = ENG[key]; eq = E["eq"]; first, end = E["first"], E["end"]; W = WS[wn]
        for sg in AO.SEGS[wn]:
            x, y = W["segp"][sg]
            a = max(x, first); yy = min(y, end - 1)
            sel = []
            for hk, amt in PATHH[key]:
                ev = evd.get(hk)
                if ev is None or not (a < ev["ta"] <= yy):
                    continue
                sel.append((ev, hk, amt))
            ntrig = len(sel); nlock = sum(int(ev["鎖漲停"]) for ev, _, _ in sel)
            fills = [(ev, hk, amt) for ev, hk, amt in sel if not ev["鎖漲停"]]

            def mkpos(ev, hk, amt, s):
                px = ev["出場價"]; has = px is not None and np.isfinite(px)
                return (int(ev["ta"]), float(amt), float(ev["加碼價"]) * (1 + s), hk,
                        (int(ev["出場根"]) if has else None), (float(px) * (1 - s) if has else None))
            for s in SLIPS:
                U = [mkpos(ev, hk, amt, s) for ev, hk, amt in fills]
                Fv = [mkpos(ev, hk, amt, s) for ev, hk, amt in fills if ev["大盤旗標"]]
                su = subacct(x, y, U, HI); sf = subacct(x, y, Fv, HI)
                row = {"世界": wn, "策略": sn, "r": r, "段": sg, "滑價": s, "觸發": ntrig, "鎖漲停": nlock,
                       "無條件_筆": su["n"], "濾網_筆": sf["n"], "被擋_筆": su["n"] - sf["n"]}
                for nm, z in (("無條件", su), ("濾網", sf)):
                    for k_ in ("I", "淨損益", "年化", "回落", "使用率", "使用率峰值"):
                        row[f"{nm}_{k_}"] = z[k_]
                row["濾網減無條件_淨損益"] = sf["淨損益"] - su["淨損益"]
                NAVS[(key, sg, s)] = (su["NAV"], su["I"], sf["NAV"], sf["I"])
                if s == 0.0:
                    c0, m0, _ = AO.RR.win_metrics(eq, first, end, x, y)
                    row["原_年化"], row["原_回落"] = c0, m0
                    for nm, P in (("無條件", U), ("濾網", Fv)):
                        pos = [(ta, A, ep, hk, sd, px, "") for ta, A, ep, hk, sd, px in P]
                        navs, st = AO.account(eq, a, yy, pos)
                        for rd in ("A", "B"):
                            cc, mm = AO.metrics(eq, first, end, x, y, a, navs[rd])
                            row[f"組合{nm}_{rd}_年化"], row[f"組合{nm}_{rd}_回落"] = cc, mm
                rows.append(row)
    log(f"[路徑] {len(rows)} 列")
    return pd.DataFrame(rows), NAVS


def ratio(c, m):
    return c / abs(m) if (m is not None and np.isfinite(m) and m != 0 and np.isfinite(c)) else np.nan


def summarize_paths(P, NAVS, WS):
    S = {}
    for sg in SEGN:
        wn = SEGW[sg]
        for s in SLIPS:
            z = {}
            for sn in ("營量", "營飆"):
                g = P[(P["世界"] == wn) & (P["策略"] == sn) & (P["段"] == sg) & (P["滑價"] == s)]
                d = {"路徑數": int(len(g))}
                for c in ("觸發", "鎖漲停", "無條件_筆", "濾網_筆", "被擋_筆"):
                    d[c + "（中位）"] = float(g[c].median())
                for nm in ("無條件", "濾網"):
                    for k_ in ("I", "淨損益", "年化", "回落", "使用率", "使用率峰值"):
                        d[f"{nm}_{k_}"] = float(g[f"{nm}_{k_}"].median())
                    d[f"{nm}_年化÷|回落|"] = ratio(d[f"{nm}_年化"], d[f"{nm}_回落"])
                d["濾網減無條件_淨損益（中位）"] = float(g["濾網減無條件_淨損益"].median())
                if len(g) > 1:
                    d["濾網減無條件_淨損益 p10／p90"] = [float(g["濾網減無條件_淨損益"].quantile(.1)), float(g["濾網減無條件_淨損益"].quantile(.9))]
                    d["濾網淨損益 ＞ 無條件 的顆數比例"] = float((g["濾網減無條件_淨損益"] > 0).mean())
                if s == 0.0:
                    co, mo = float(g["原_年化"].median()), float(g["原_回落"].median())
                    comb = {"不加碼": {"年化": co, "回落": mo, "年化÷|回落|": ratio(co, mo)}}
                    for nm in ("無條件", "濾網"):
                        for rd in ("A", "B"):
                            ca, ma = float(g[f"組合{nm}_{rd}_年化"].median()), float(g[f"組合{nm}_{rd}_回落"].median())
                            comb[f"{nm}加碼·讀法{rd}"] = {"年化": ca, "回落": ma, "年化÷|回落|": ratio(ca, ma)}
                    d["組合三版（營飆 200 顆中位）"] = comb
                z[sn] = d
            # 合計：營量 r0 ＋ 營飆 r
            x, y = WS[wn]["segp"][sg]; L = y - x + 1
            ky = (wn, "營量", 0)
            if (ky, sg, s) in NAVS:
                uY, iuY, fY, ifY = NAVS[(ky, sg, s)]
                res = []
                for r in range(AO.NSEED):
                    k2 = ((wn, "營飆", r), sg, s)
                    if k2 not in NAVS:
                        continue
                    uF, iuF, fF, ifF = NAVS[k2]
                    a_ = nav_stats(uY + uF, iuY + iuF, L); b_ = nav_stats(fY + fF, ifY + ifF, L)
                    res.append((a_["淨損益"], b_["淨損益"], a_["年化"], b_["年化"], a_["回落"], b_["回落"], iuY + iuF, ifY + ifF))
                R_ = np.array(res, float)
                z["合計（營量＋營飆第 r 顆，200 組）"] = {
                    "無條件_淨損益": float(np.median(R_[:, 0])), "濾網_淨損益": float(np.median(R_[:, 1])),
                    "濾網減無條件_淨損益（中位）": float(np.median(R_[:, 1] - R_[:, 0])),
                    "濾網減無條件 p10／p90": [float(np.quantile(R_[:, 1] - R_[:, 0], .1)), float(np.quantile(R_[:, 1] - R_[:, 0], .9))],
                    "濾網淨損益 ＞ 無條件 的組數比例": float(np.mean(R_[:, 1] > R_[:, 0])),
                    "無條件_年化": float(np.nanmedian(R_[:, 2])), "濾網_年化": float(np.nanmedian(R_[:, 3])),
                    "無條件_回落": float(np.nanmedian(R_[:, 4])), "濾網_回落": float(np.nanmedian(R_[:, 5])),
                    "無條件_I": float(np.median(R_[:, 6])), "濾網_I": float(np.median(R_[:, 7]))}
            S[f"{sg}·滑價{s * 100:.1f}%"] = z
    return S


# ═════════════ 統計工具 ═════════════
def boot_diff(r, keep, clu, rng, nb=NB):
    """留下平均 − 被擋平均；按群集（兩組共用群集）重抽 ⇒ (值, 樣本陣列)。"""
    r = np.asarray(r, float); k = np.asarray(keep, bool)
    u, inv = np.unique(np.asarray(clu), return_inverse=True); G = len(u)
    sk = np.bincount(inv, r * k, G); nk = np.bincount(inv, k.astype(float), G)
    sb = np.bincount(inv, r * ~k, G); nb_ = np.bincount(inv, (~k).astype(float), G)
    v = float(r[k].mean() - r[~k].mean()) if k.any() and (~k).any() else np.nan
    out = np.full(nb, np.nan)
    for i0 in range(0, nb, 1000):
        ix = rng.integers(G, size=(min(1000, nb - i0), G))
        NK = nk[ix].sum(1); NBb = nb_[ix].sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[i0:i0 + len(ix)] = sk[ix].sum(1) / NK - sb[ix].sum(1) / NBb
    return v, out[np.isfinite(out)]


def boot_sum(x, clu, rng, nb=NB):
    x = np.asarray(x, float)
    u, inv = np.unique(np.asarray(clu), return_inverse=True); G = len(u)
    s = np.bincount(inv, x, G)
    out = np.empty(nb)
    for i0 in range(0, nb, 1000):
        ix = rng.integers(G, size=(min(1000, nb - i0), G))
        out[i0:i0 + len(ix)] = s[ix].sum(1)
    return float(x.sum()), out


def ci(b):
    return [float(np.quantile(b, .025)), float(np.quantile(b, .975))] if len(b) else [None, None]


def diag(s, rng, rc="r0"):
    """逐筆診斷（s ＝ 可成交、已出場的唯一事件）。"""
    r = s[rc].to_numpy(float); k = s["大盤旗標"].to_numpy(bool); amt = s["金額"].to_numpy(float); c = s["clu"].to_numpy()
    o = {"筆": int(len(s)), "留下": int(k.sum()), "被擋": int((~k).sum()), "被擋比例": float((~k).mean()) if len(k) else None}
    for nm, m in (("留下", k), ("被擋", ~k)):
        if m.any():
            o[f"{nm}_平均"] = float(r[m].mean()); o[f"{nm}_中位"] = float(np.median(r[m]))
            o[f"{nm}_賺錢比例"] = float((r[m] > 0).mean()); o[f"{nm}_賠超過15比例"] = float((r[m] < -0.15).mean())
    if k.sum() >= 2 and (~k).sum() >= 2:
        v, b = boot_diff(r, k, c, rng)
        o["③留下減被擋"] = v; o["③CI"] = ci(b); o["③ bootstrap ≤0 比例"] = float((b <= 0).mean())
        o["中位差"] = float(np.median(r[k]) - np.median(r[~k]))
    v1, b1 = boot_sum(-(amt * r) * (~k), c, rng)
    o["①濾網減無條件淨損益"] = v1; o["①CI"] = ci(b1)
    o["無條件淨損益（Σ金額×r）"] = float(np.sum(amt * r)); o["濾網淨損益"] = float(np.sum(amt * r * k))
    o["不同股票 留下／被擋"] = [int(s.loc[k, "sid"].nunique()), int(s.loc[~k, "sid"].nunique())]
    o["群集月數"] = int(len(np.unique(c)))
    return o


def trims(s, rng):
    z = {}
    for q_ in (0.01, 0.05):
        m = int(math.ceil(q_ * len(s)))
        t_ = s.drop(s["r0"].sort_values(ascending=False).index[:m])
        d = diag(t_, rng)
        z[f"去最賺 {int(q_ * 100)}%（{m} 筆）"] = {k: d.get(k) for k in ("③留下減被擋", "③CI", "①濾網減無條件淨損益", "①CI", "中位差", "留下_平均", "被擋_平均")}
        z[f"去最賺 {int(q_ * 100)}%（{m} 筆）"]["被去掉的筆中留下的筆數"] = int(s.loc[s["r0"].sort_values(ascending=False).index[:m], "大盤旗標"].sum())
    return z


def seg_ev(EV, sg, full=False):
    if sg == "主窗":
        s = EV[EV["段"].isin(("探索", "確認"))]
    else:
        s = EV[EV["段"] == sg]
    return s if full else s[s["可成交"] & s["已出場"]]


# ═════════════ 原持股同期（V8）═════════════
def orig_sameperiod(WS, HI, tx, TXF, rng):
    txpos = {d: i for i, d in enumerate(tx.index)}
    rows = []
    for hk, I in HI.items():
        wn, sn, sid, tb = hk
        if I["ts"] is None or I["orig_cross_bad"]:
            continue
        T = I["T"]
        if not len(T):
            continue
        cal = WS[wn]["cal"]; bar, bad, op = I["bar"], I["bad"], I["op"]
        badc = np.cumsum(bad[tb + 1:I["xbar"] + 1])
        for k, t in enumerate(T):
            if not bar[t] or badc[t - tb] > 0:
                continue
            o_ = float(op[t + 1])
            if not (np.isfinite(o_) and o_ > 0):
                continue
            p = txpos.get(cal[t])
            if p is None or not np.isfinite(TXF["TX_MA20"][p]):
                continue
            rows.append((wn, sn, sid, tb, t + 1, I["pxs"] / o_ - 1.0 - COST, bool(TXF["TX_MA20"][p]), f"{wn}|{str(cal[t + 1])[:7]}"))
    D_ = pd.DataFrame(rows, columns=["世界", "策略", "sid", "tb", "ta", "r", "旗標", "clu"])
    out = {}
    for sg in SEGN:
        x, y = SEGU[sg]; wn = SEGW[sg]
        s = D_[(D_["世界"] == wn) & (D_["ta"] > x) & (D_["ta"] <= y)]
        if not len(s):
            continue
        k = s["旗標"].to_numpy(bool); r = s["r"].to_numpy(float)
        v, b = boot_diff(r, k, s["clu"].to_numpy(), rng)
        hs = s.groupby(["策略", "sid", "tb", "旗標"])["r"].mean().unstack()
        z = {"持有日數": int(len(s)), "旗標成立日比例": float(k.mean()), "成立_平均": float(r[k].mean()), "不成立_平均": float(r[~k].mean()),
             "成立_賺錢比例": float((r[k] > 0).mean()), "不成立_賺錢比例": float((r[~k] > 0).mean()),
             "差（持有日加權）": v, "差CI（按月）": ci(b),
             "每檔先平均：成立平均／不成立平均／兩者皆有的檔數": [float(hs[True].mean()) if True in hs else None, float(hs[False].mean()) if False in hs else None,
                                              int(hs.dropna().shape[0]) if hs.shape[1] == 2 else 0]}
        for sn in ("營量", "營飆"):
            q = s[s["策略"] == sn]; kk = q["旗標"].to_numpy(bool); rr = q["r"].to_numpy(float)
            if kk.any() and (~kk).any():
                z[f"{sn} 成立／不成立 平均"] = [float(rr[kk].mean()), float(rr[~kk].mean())]
        out[sg] = z
    return out


# ═════════════ 隨機擋（V9）═════════════
def random_block(s, rng, nrand=NRAND):
    r = s["r0"].to_numpy(float); k = s["大盤旗標"].to_numpy(bool); amt = s["金額"].to_numpy(float)
    n = len(r); m = int((~k).sum())
    real3 = float(r[k].mean() - r[~k].mean()); real1 = float(-(amt * r)[~k].sum())
    v3 = np.empty(nrand); v1 = np.empty(nrand)
    for i in range(nrand):
        bl = np.zeros(n, bool); bl[rng.choice(n, m, replace=False)] = True
        v3[i] = r[~bl].mean() - r[bl].mean(); v1[i] = -(amt * r)[bl].sum()
    return {"筆": n, "被擋": m, "真③": real3, "隨機③ 中位／p95": [float(np.median(v3)), float(np.quantile(v3, .95))],
            "③ 隨機 ≥ 真實 的比例": float((v3 >= real3).mean()), "③ 排在前 5%": bool((v3 >= real3).mean() < 0.05),
            "真①": real1, "隨機① 中位／p95": [float(np.median(v1)), float(np.quantile(v1, .95))],
            "① 隨機 ≥ 真實 的比例": float((v1 >= real1).mean()), "① 排在前 5%": bool((v1 >= real1).mean() < 0.05)}


# ═════════════ 挑選過程重跑（V10）═════════════
def breadth_series(MW, WS):
    """世界日曆上：廣度成員旗標（float），同 researchAddOn_mkt M2③。"""
    B = {}
    for wn in ("主", "早年"):
        M = MW[wn]; C, BAR, BAD, R1m = M["C"], M["BAR"], M["BAD"], M["R1"]; S, n = M["S"], M["n"]
        CB = np.zeros((S, n + 1), np.int32); CB[:, 1:] = np.cumsum(BAD, axis=1)
        okc = BAR & np.isfinite(C)
        OKC = np.zeros((S, n + 1), np.int32); OKC[:, 1:] = np.cumsum(okc, axis=1)
        CS = np.zeros((S, n + 1)); CS[:, 1:] = np.cumsum(np.where(okc, C, 0.0), axis=1)
        for L in (20, 60):
            out = {pn: np.full(n, np.nan) for pn in ("R1", "全檔")}
            for t in range(L, n):
                el = ((OKC[:, t + 1] - OKC[:, t - L + 1]) == L) & ((CB[:, t + 1] - CB[:, t - L + 2]) == 0)
                ma = (CS[:, t + 1] - CS[:, t - L + 1]) / L
                up = el & (C[:, t] > ma)
                for pn, pm in (("R1", R1m[:, t] & el), ("全檔", BAR[:, t] & el)):
                    nn = int(pm.sum())
                    if nn:
                        out[pn][t] = float((up & pm).sum() / nn > 0.5)
            for pn in out:
                B[(wn, f"BR_{pn}_MA{L}")] = out[pn]
    return B


def e50_series(WS):
    E = {}
    for wn, W in WS.items():
        b = np.asarray(W["bench"], float); n = len(W["cal"]); b = b[:n]
        for L in LENS:
            v = np.full(n, np.nan)
            for t in range(L - 1, n):
                w = b[t - L + 1:t + 1]
                if np.isfinite(w).all():
                    v[t] = float(b[t] > w.mean())
            E[(wn, f"E50_MA{L}")] = v
    return E


def stat3(r, f):
    ok = np.isfinite(f)
    k = f[ok] > 0.5; rr = r[ok]
    if k.sum() < 5 or (~k).sum() < 5:
        return np.nan
    return float(rr[k].mean() - rr[~k].mean())


def stat1(r, amt, f):
    ok = np.isfinite(f)
    k = f[ok] > 0.5
    if k.sum() < 5 or (~k).sum() < 5:
        return np.nan
    return float(-(amt[ok] * r[ok])[~k].sum())


def family_shift(s, TXF, BR, E50, log, tag):
    """s：事件（需 r、金額、指數位置、世界、t）。⇒ 每個 lag 的族內最佳、真實位置。"""
    r = s["r"].to_numpy(float); amt = s["金額"].to_numpy(float); p = s["指數位置"].to_numpy(int)
    wn = s["世界"].to_numpy(); t = s["t"].to_numpy(int)
    txm = [k for k in TXF]
    brm = sorted({k for (_, k) in BR}); e5m = sorted({k for (_, k) in E50})

    def flags(mem, lag):
        if mem in TXF:
            q = p - lag
            return np.where(q >= 0, TXF[mem][np.clip(q, 0, None)], np.nan)
        src = BR if mem in brm else E50
        out = np.empty(len(t))
        for i in range(len(t)):
            a = src[(wn[i], mem)]; q = t[i] - lag
            out[i] = a[q] if q >= 0 else np.nan
        return out
    fam20 = txm + brm; fam27 = fam20 + e5m
    real = {m: (stat3(r, flags(m, 0)), stat1(r, amt, flags(m, 0))) for m in fam27}
    rows = []
    for lag in LAGS:
        v = {m: (stat3(r, flags(m, lag)), stat1(r, amt, flags(m, lag))) for m in fam27}
        rows.append({"lag": lag, "族20 最佳③": np.nanmax([v[m][0] for m in fam20]), "族20 最佳①": np.nanmax([v[m][1] for m in fam20]),
                     "族27 最佳③": np.nanmax([v[m][0] for m in fam27]), "族27 最佳①": np.nanmax([v[m][1] for m in fam27]),
                     "MA20③": v["TX_MA20"][0], "MA20①": v["TX_MA20"][1],
                     "族20 最佳③ 是誰": fam20[int(np.nanargmax([v[m][0] for m in fam20]))]})
    Fd = pd.DataFrame(rows); Fd.insert(0, "樣本", tag)
    o = {"成員數": [len(fam20), len(fam27)], "真 MA20 ③": real["TX_MA20"][0], "真 MA20 ①": real["TX_MA20"][1],
         "族20 真（不平移）最佳③ 與成員": [float(np.nanmax([real[m][0] for m in fam20])), fam20[int(np.nanargmax([real[m][0] for m in fam20]))]],
         "族內各成員真③": {m: real[m][0] for m in fam27}}
    for fam in ("族20", "族27"):
        for st, key in (("③", "MA20③"), ("①", "MA20①")):
            col = Fd[f"{fam} 最佳{st}"].to_numpy(float); col = col[np.isfinite(col)]
            rv = real["TX_MA20"][0 if st == "③" else 1]
            pct = float((col < rv).mean()) if len(col) else None
            o[f"{fam}·{st}：真 MA20 在平移最佳分布的百分位"] = pct
            o[f"{fam}·{st}：平移最佳 中位／p95"] = [float(np.median(col)), float(np.quantile(col, .95))] if len(col) else None
            o[f"{fam}·{st}：未達 95% ⇒ 加結果句"] = (pct is not None and pct < 0.95)
        # 平移的單一 MA20（不挑，同 mkt M5）
    col = Fd["MA20③"].to_numpy(float); col = col[np.isfinite(col)]
    o["單一 MA20（不挑）③：真值 ≥ 平移值比例"] = float((real["TX_MA20"][0] >= col).mean())
    log(f"[挑選 {tag}] 族20③ 百分位 {o['族20·③：真 MA20 在平移最佳分布的百分位']}｜族20① {o['族20·①：真 MA20 在平移最佳分布的百分位']}")
    return o, Fd


# ═════════════ 檢定力（V12）═════════════
def power(s, amt_col, rng, mode, ngrid=NGRID, nsim=NSIM, joint_at=None, log=print):
    d = s.sort_values("r0", ascending=False)
    m = int(math.ceil(0.05 * len(d)))
    d = d.iloc[m:]
    r = d["r0"].to_numpy(float).copy(); k = d["大盤旗標"].to_numpy(bool); amt = d[amt_col].to_numpy(float)
    eff0 = float(r[k].mean() - r[~k].mean())
    if mode == "S2":
        r[~k] -= (0.10 - eff0)
    eff = float(r[k].mean() - r[~k].mean())
    u, inv = np.unique(d["clu"].to_numpy(), return_inverse=True); G = len(u)
    groups = [np.flatnonzero(inv == g) for g in range(G)]; sizes = np.array([len(g) for g in groups])
    mean_sz = sizes.mean()
    res = []

    def one(N, want_joint):
        L_ = int(N / mean_sz * 2) + 30
        seq = rng.integers(G, size=L_)
        cs = np.cumsum(sizes[seq])
        while cs[-1] < N:
            seq = np.r_[seq, rng.integers(G, size=L_)]; cs = np.cumsum(sizes[seq])
        j = int(np.searchsorted(cs, N)); seq = seq[:j + 1]
        idx = np.concatenate([groups[g] for g in seq]); cid = np.repeat(np.arange(len(seq)), sizes[seq])
        rr = r[idx]; kk = k[idx]; nk = kk.sum(); nb_ = (~kk).sum()
        if nk < 2 or nb_ < 2:
            return 0.0, nb_, False, False, False
        mk = rr[kk].mean(); mb = rr[~kk].mean(); dif = mk - mb
        psi = np.where(kk, (rr - mk) / nk, -(rr - mb) / nb_)
        Sg = np.bincount(cid, psi); Gc = len(Sg)
        var = Sg @ Sg * Gc / max(Gc - 1, 1)
        z = dif / math.sqrt(var) if var > 0 else 0.0
        ja = jc = False
        if want_joint:
            ja = bool(-(amt[idx] * rr)[~kk].sum() > 0)
            n_ = len(rr); cnt = 0
            for _ in range(200):
                bl = np.zeros(n_, bool); bl[rng.choice(n_, nb_, replace=False)] = True
                cnt += (rr[~bl].mean() - rr[bl].mean()) >= dif
            jc = cnt / 200 < 0.05
        return z, nb_, ja, jc, True
    for N in ngrid:
        Z = np.empty(nsim); NBk = np.empty(nsim)
        for i in range(nsim):
            z, nb_, *_ = one(N, False); Z[i] = z; NBk[i] = nb_
        res.append({"情境": mode, "N觸發": N, "檢定力（單尾5%）": float((Z > 1.645).mean()), "檢定力（兩尾95%）": float((Z > 1.96).mean()),
                    "被擋筆數中位": float(np.median(NBk)), "被擋筆數 p10": float(np.quantile(NBk, .1))})
    Pw = pd.DataFrame(res)
    ok = Pw["檢定力（單尾5%）"].to_numpy() >= 0.80
    Nstar = None
    for i in range(len(ok)):
        if ok[i:].all():
            Nstar = int(Pw["N觸發"].iloc[i]); break
    o = {"情境": mode, "母體筆數（去右尾後）": int(len(d)), "去掉筆數": m, "原始去右尾差": eff0, "模擬用真效果": eff, "月塊數": int(G),
         "N*": Nstar, "B*": (int(math.ceil(float(Pw.loc[Pw["N觸發"] == Nstar, "被擋筆數中位"].iloc[0]))) if Nstar else None)}
    Nj = joint_at or Nstar
    if Nj:
        J = [one(Nj, True) for _ in range(nsim)]
        zz = np.array([j[0] for j in J]); ja = np.array([j[2] for j in J]); jc = np.array([j[3] for j in J])
        o[f"N＝{Nj} 時：b（兩尾95%）檢定力"] = float((zz > 1.96).mean())
        o[f"N＝{Nj} 時：a∧b∧c 同時成立機率"] = float(((zz > 1.96) & ja & jc).mean())
        o[f"N＝{Nj} 時：a 成立機率"] = float(ja.mean()); o[f"N＝{Nj} 時：c 成立機率"] = float(jc.mean())
    log(f"[檢定力 {mode}] 真效果 {eff:+.4f}｜N* {Nstar}｜B* {o['B*']}")
    return o, Pw


def years_needed(N, B, rate_t, rate_b, start=FWD_START):
    """⇒ 第一個 12 月最後交易日檢查點（年份）使預期累計 觸發 ≥ N 且 被擋 ≥ B。"""
    st = pd.Timestamp(start)
    yrs = max(N / rate_t, B / rate_b)
    for Y in range(st.year, st.year + 60):
        el = (pd.Timestamp(f"{Y}-12-31") - st).days / 365.25
        if el >= yrs:
            return {"所需年數（期望值）": float(yrs), "第一個可判的年底檢查點": f"{Y}-12 最後交易日"}
    return {"所需年數（期望值）": float(yrs), "第一個可判的年底檢查點": None}


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}")
    sha = main_sha(); tx, txsha = load_index(sha)
    log(f"[指數] 公開庫 main {sha}｜market_index.csv 內容 sha {txsha}｜{tx.index[0].date()}～{tx.index[-1].date()} {len(tx)} 筆")
    TXF = index_flags(tx)
    WS, ENG, HI, PATHH, MW, MINFO, gates = build(log, a.procs)
    EV = events(WS, HI, PATHH, tx, TXF, log)
    # 閘：與初測 ext（私有庫指數算的 G3a、A_ret）逐筆比對（只比布林與報酬）
    ext = pd.read_csv("backtest/resultsAddOn/ext/ext_rows.csv.gz", dtype={"sid": str}, usecols=["世界", "策略", "sid", "tb", "格", "t", "ta", "A_ret", "G3a_多頭", "金額"])
    mm = EV.merge(ext, on=["世界", "策略", "sid", "tb", "t", "ta"], how="inner", suffixes=("", "_ext"))
    g = {"同一筆（世界×策略×sid×tb×t）筆數": int(len(mm)), "大盤旗標 vs G3a_多頭 不同": int((mm["大盤旗標"] != mm["G3a_多頭"].astype(bool)).sum()),
         "r0 vs A_ret 最大差": float(np.nanmax(np.abs(mm["r0"] - mm["A_ret"]))) if len(mm) else None,
         "金額 vs ext 金額 最大相對差": float(np.nanmax(np.abs(mm["金額"] / mm["金額_ext"] - 1))) if len(mm) else None}
    gates["登錄格事件 vs 初測 ext"] = g; log(f"[閘 ext] {g}")
    if g["大盤旗標 vs G3a_多頭 不同"] or (g["r0 vs A_ret 最大差"] or 0) > 1e-9:
        raise SystemExit("⛔ ext 閘不過")
    rng = np.random.default_rng(SEED)
    J = {"時間": now_tpe() + "（台北）", "讀法寫死": TIME, "登錄": f"PREREG營量營飆漲多加碼大盤濾網 seq2 sha {REG_SHA}（裁定 seq345 核准；N 不變）", "登錄檔": regf,
         "性質": "歷史段＝描述、最多暫定；⭐ 判定只看前瞻（裁定 seq344／345）",
         "讀法": __doc__.split("═══ 讀法（V 標")[1].split("輸出")[0].strip(),
         "指數": {"來源": "公開庫 tw-stock-data main data/history/market_index.csv（git show）", "main sha": sha, "檔內容 sha16": txsha,
                "起訖": [str(tx.index[0].date()), str(tx.index[-1].date())], "筆數": int(len(tx))},
         "閘": gates, "母體": MINFO, "結果句必附": SENT, "早年必附": NOTE_EARLY}
    # ── 1. 主判：子帳戶（路徑）
    P, NAVS = paths(WS, ENG, HI, PATHH, EV, log)
    P.to_csv(os.path.join(OUT, "paths.csv.gz"), index=False, float_format="%.10g")
    J["主判（加碼子帳戶，濾網版 vs 無條件版）"] = summarize_paths(P, NAVS, WS)
    # ── 2. 成交
    fill = {}
    for sg in SEGN:
        s = seg_ev(EV, sg, full=True)
        z = {"觸發": int(len(s)), "鎖漲停（買不到）": int(s["鎖漲停"].sum()), "鎖漲停比例": float(s["鎖漲停"].mean()) if len(s) else None,
             "開盤漲停（含未鎖）比例": float(s["開盤漲停"].mean()) if len(s) else None,
             "一字近漲停（容許取整）筆數": int(s["一字近漲停"].sum()), "鎖漲停 與 一字近漲停 不一致筆數": int((s["鎖漲停"] != s["一字近漲停"]).sum()),
             "鎖漲停 按大盤旗標（成立／不成立）": [int((s["鎖漲停"] & s["大盤旗標"]).sum()), int((s["鎖漲停"] & ~s["大盤旗標"]).sum())],
             "參考價除權息換算筆數": int((s["參考價"] == "除權息換算").sum()),
             "跳空分布（全部）": {q: float(s["跳空"].quantile(v)) for q, v in (("p5", .05), ("p25", .25), ("中位", .5), ("p75", .75), ("p95", .95))},
             "跳空平均": float(s["跳空"].mean()), "跳空 ≥ +3% 比例": float((s["跳空"] >= 0.03).mean()), "跳空 ≤ −3% 比例": float((s["跳空"] <= -0.03).mean())}
        for nm, m in (("留下", s["大盤旗標"]), ("被擋", ~s["大盤旗標"])):
            q = s.loc[m, "跳空"]
            z[f"跳空中位（{nm}）"] = float(q.median()) if len(q) else None
        z["資料尾仍持有（逐筆不算）"] = int((~s["已出場"]).sum())
        fill[sg] = z
    J["成交（t＋1 開盤、鎖漲停、跳空）"] = fill
    # ── 逐筆診斷（含滑價）
    DG = {}
    for sg in SEGN:
        s = seg_ev(EV, sg)
        z = {"滑價0": diag(s, rng)}
        for sl in SLIPS[1:]:
            d = diag(s, rng, f"r{int(sl * 1000)}")
            z[f"滑價每邊{sl * 100:.1f}%"] = {k: d.get(k) for k in ("③留下減被擋", "③CI", "①濾網減無條件淨損益", "①CI", "留下_平均", "被擋_平均")}
        z["去右尾"] = trims(s, rng)
        for sn in ("營量", "營飆"):
            q = s[s["策略"] == sn]
            if len(q) >= 4:
                z[f"{sn}"] = diag(q, rng)
        for mk in ("twse", "tpex"):
            q = s[s["市場"] == mk]
            if len(q) >= 4 and q["大盤旗標"].any() and (~q["大盤旗標"]).any():
                d = diag(q, rng); z[f"市場 {mk}"] = {k: d.get(k) for k in ("筆", "留下", "被擋", "留下_平均", "被擋_平均", "③留下減被擋", "③CI")}
        DG[sg] = z
    J["逐筆診斷（唯一事件，⛔ 不單獨判）"] = DG
    # 逐年
    YR = []
    for (y_, sg_), q in EV[EV["段"] != "段外"].groupby(["年", "段"]):
        qq = q[q["可成交"] & q["已出場"]]; k = qq["大盤旗標"]
        YR.append({"年": y_, "段": sg_, "觸發": int(len(q)), "鎖漲停": int(q["鎖漲停"].sum()), "被擋比例": float((~q["大盤旗標"]).mean()),
                   "可算筆": int(len(qq)), "留下筆": int(k.sum()), "被擋筆": int((~k).sum()),
                   "留下平均": float(qq.loc[k, "r0"].mean()) if k.any() else None, "被擋平均": float(qq.loc[~k, "r0"].mean()) if (~k).any() else None,
                   "留下中位": float(qq.loc[k, "r0"].median()) if k.any() else None, "被擋中位": float(qq.loc[~k, "r0"].median()) if (~k).any() else None,
                   "差": float(qq.loc[k, "r0"].mean() - qq.loc[~k, "r0"].mean()) if (k.any() and (~k).any()) else None,
                   "①": float(-(qq["金額"] * qq["r0"])[~k].sum())})
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "years.csv"), index=False, float_format="%.6g")
    J["逐年"] = YR
    # ── V8 原持股同期
    J["原持股同期（大盤成立 vs 不成立）"] = orig_sameperiod(WS, HI, tx, TXF, rng)
    log("[V8] 完成")
    # ── V9 隨機擋
    rng9 = np.random.default_rng(SEED + 1)
    J["隨機擋同比例 1,000 次"] = {sg: random_block(seg_ev(EV, sg), rng9) for sg in SEGN}
    # ── V11 年代交互作用
    rngI = np.random.default_rng(SEED + 3)
    sE, sM = seg_ev(EV, "早年"), seg_ev(EV, "主窗")
    vE, bE = boot_diff(sE["r0"], sE["大盤旗標"], sE["clu"], rngI); vM, bM = boot_diff(sM["r0"], sM["大盤旗標"], sM["clu"], rngI)
    nn = min(len(bE), len(bM))
    n1E = float(-(sE["金額"] * sE["r0"])[~sE["大盤旗標"]].sum() / sE["金額"].sum()); n1M = float(-(sM["金額"] * sM["r0"])[~sM["大盤旗標"]].sum() / sM["金額"].sum())
    _, b1E = boot_sum(-(sE["金額"] * sE["r0"]) * (~sE["大盤旗標"]) / sE["金額"].sum(), sE["clu"], rngI)
    _, b1M = boot_sum(-(sM["金額"] * sM["r0"]) * (~sM["大盤旗標"]) / sM["金額"].sum(), sM["clu"], rngI)
    J["年代交互作用（早年 − 主窗）"] = {"③ 早年／主窗": [vE, vM], "③ 差的差": vE - vM, "③ 差的差 CI": ci(bE[:nn] - bM[:nn]),
                                 "③ 差的差 bootstrap ≥0 比例": float(((bE[:nn] - bM[:nn]) >= 0).mean()),
                                 "①÷可成交金額 早年／主窗": [n1E, n1M], "① 正規化 差的差": n1E - n1M, "① 正規化 差的差 CI": ci(b1E - b1M)}
    # ── V10 挑選過程
    log("[V10] 廣度序列…")
    BR = breadth_series(MW, WS); E50 = e50_series(WS)
    sMm = sM.assign(r=sM["r0"])
    o1, F1 = family_shift(sMm, TXF, BR, E50, log, "登錄格 主窗")
    oth = {}
    for sg in ("探索", "確認", "早年"):
        ss = seg_ev(EV, sg).assign(r=lambda z: z["r0"])
        oth[sg], _ = family_shift(ss, TXF, BR, E50, log, f"登錄格 {sg}")
    # 初測 400 筆口徑
    ext2 = pd.read_csv("backtest/resultsAddOn/ext/ext_rows.csv.gz", dtype={"sid": str}, usecols=["世界", "策略", "sid", "tb", "t", "段", "A_ret", "金額"])
    ext2 = ext2[ext2["段"].isin(("探索", "確認"))].copy()
    txpos = {d: i for i, d in enumerate(tx.index)}
    ext2["指數位置"] = [txpos[WS[w]["cal"][int(t)]] for w, t in zip(ext2["世界"], ext2["t"])]
    ext2["r"] = ext2["A_ret"]
    o2, F2 = family_shift(ext2, TXF, BR, E50, log, "初測400 主窗")
    pd.concat([F1, F2]).to_csv(os.path.join(OUT, "family_shift.csv"), index=False, float_format="%.6g")
    J["挑選過程重跑（時間平移 k＝21～250）"] = {"登錄格 主窗（主）": o1, "登錄格 各段（描述）": {k: {kk: v for kk, v in z.items() if kk != "族內各成員真③"} for k, z in oth.items()},
                                     "初測 400 筆 主窗（MA20 實際被挑出的那批，描述）": o2}
    # ── V12 檢定力
    rngP = np.random.default_rng(SEED + 2)
    o_s1, P1 = power(sM, "金額", rngP, "S1", log=log)
    o_s2, P2 = power(sM, "金額", rngP, "S2", log=log)
    main_o = o_s1 if (o_s1["原始去右尾差"] > 0 and o_s1["N*"]) else o_s2
    pd.concat([P1, P2]).to_csv(os.path.join(OUT, "power.csv"), index=False, float_format="%.6g")
    Nth = max(80, main_o["N*"] or 10 ** 9); Bth = max(20, main_o["B*"] or 10 ** 9)
    # 頻率（每條路徑，主窗；含鎖漲停）
    pm = P[(P["段"] == "主窗") & (P["滑價"] == 0.0)]
    x, y = WS["主"]["segp"]["主窗"]; yrs = (y - x) / YEAR
    yl = pm[pm["策略"] == "營量"].iloc[0]; yf = pm[pm["策略"] == "營飆"]
    rate_t = (float(yl["觸發"]) + float(yf["觸發"].median())) / yrs
    rate_b = (float(yl["被擋_筆"]) + float(yf["被擋_筆"].median())) / yrs
    sMf = seg_ev(EV, "主窗", full=True)
    rate_tu = len(sMf) / yrs; rate_bu = float((~sMf["大盤旗標"]).sum()) / yrs
    J["前瞻門檻（寫死）"] = {"規則": "觸發 ≥ max(80, N*)、被擋 ≥ max(20, B*)；N*／B* 取 S1（S1 去右尾差 ≤ 0 或算不出 ⇒ S2）",
                         "採用情境": main_o["情境"], "觸發門檻": int(Nth), "被擋門檻": int(Bth),
                         "S1": o_s1, "S2（敏感度：真效果恰 +10 點）": o_s2,
                         "歷史頻率（主窗 2017-03～2026-08，每條路徑：營量＋營飆中位顆，含鎖漲停）": {"觸發／年": rate_t, "被擋／年": rate_b,
                                                                              **years_needed(Nth, Bth, rate_t, rate_b)},
                         "歷史頻率（唯一事件，營飆 200 顆去重；偏多）": {"觸發／年": rate_tu, "被擋／年": rate_bu, **years_needed(Nth, Bth, rate_tu, rate_bu)},
                         "檢查時點": "只在每年 12 月最後一個交易日收盤後看一次；門檻第一次到的那個年底判一次，之後不重判"}
    log(f"[門檻] 觸發 ≥ {Nth}、被擋 ≥ {Bth}｜{J['前瞻門檻（寫死）']['歷史頻率（主窗 2017-03～2026-08，每條路徑：營量＋營飆中位顆，含鎖漲停）']}")
    # ── 歷史版三條（描述）
    hz = {}
    for sg in SEGN:
        s = seg_ev(EV, sg); d = DG[sg]["滑價0"]; rb = J["隨機擋同比例 1,000 次"][sg]
        zz = J["主判（加碼子帳戶，濾網版 vs 無條件版）"][f"{sg}·滑價0.0%"].get("合計（營量＋營飆第 r 顆，200 組）", {})
        a_ = zz.get("濾網減無條件_淨損益（中位）", np.nan) > 0
        b_ = (d.get("③留下減被擋") or 0) > 0 and d.get("③CI", [None])[0] is not None and d["③CI"][0] > 0
        c_ = rb["③ 排在前 5%"]
        hz[sg] = {"a 子帳戶淨損益 濾網＞無條件（合計中位）": bool(a_), "b ③＞0 且 CI 不含 0": bool(b_), "c 隨機擋排前 5%": bool(c_),
                  "三條皆成立（僅描述）": bool(a_ and b_ and c_)}
    J["歷史段套前瞻三條（描述、⛔ 不判）"] = hz
    J["櫃買指數版"] = "公開庫 main 沒有櫃買指數 ⇒ 資料未到位、不描述（⛔ 不讀私有庫）"
    # 初測口徑對照（③，公開庫指數；描述）
    ext3 = pd.read_csv("backtest/resultsAddOn/ext/ext_rows.csv.gz", dtype={"sid": str}, usecols=["世界", "段", "A_ret", "金額", "clu", "t", "sid"])
    ext3["大盤旗標"] = [bool(TXF["TX_MA20"][txpos[WS[w]["cal"][int(t)]]]) for w, t in zip(ext3["世界"], ext3["t"])]
    ext3["r0"] = ext3["A_ret"]
    cmp_ = {}
    for sg in SEGN:
        s = ext3[ext3["段"].isin(("探索", "確認"))] if sg == "主窗" else ext3[ext3["段"] == sg]
        d = diag(s, rng); cmp_[sg] = {k: d.get(k) for k in ("筆", "留下", "被擋", "③留下減被擋", "③CI", "①濾網減無條件淨損益", "①CI")}
    J["對照：初測 400 筆口徑（營量多用 A1；無成交規則；描述）"] = cmp_
    # 結果句
    sel_pct = o1["族20·③：真 MA20 在平移最佳分布的百分位"]
    J["結果句（本件附）"] = SENT + ([SENT_SEL] if (sel_pct is not None and sel_pct < 0.95) else [])
    # ── 存
    keep = ["世界", "策略", "sid", "tb", "格", "t", "ta", "h", "g", "q", "日期t", "加碼日", "段", "加碼月", "年", "市場", "大盤旗標", "鎖漲停", "開盤漲停",
            "一字近漲停", "參考價", "跳空", "加碼價", "出場根", "出場價", "出場種類", "資料尾計值", "r0_含資料尾", "金額", "種子數"] + [f"r{int(s * 1000)}" for s in SLIPS]
    EV[keep].sort_values(["世界", "ta", "策略", "sid"]).to_csv(os.path.join(OUT, "events.csv"), index=False, float_format="%.10g")
    pd.DataFrame(columns=FWD_COLS).to_csv(os.path.join(OUT, "forward_template.csv"), index=False)
    J["前瞻紀錄欄位"] = FWD_COLS; J["前瞻起點"] = FWD_START
    J["事後註"] = __doc__.split("── 事後註（寫死之後、照實記）──")[1].strip()
    J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "mkt_v2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=jdef)
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


# ═════════════ 前瞻記帳（V14）═════════════
FWD_COLS = ["觸發日", "代號", "策略", "進場日", "h", "g", "門檻", "大盤旗標", "是否加", "加碼日", "加碼價", "鎖漲停", "跳空",
            "出場日", "出場價", "出場種類", "報酬_假如有加", "金額_份", "子帳戶損益_濾網版", "子帳戶損益_無條件版", "狀態",
            "持股來源", "記錄時間", "資料sha", "指數sha"]
FWD_PATH = os.path.join(REPO, "backtest", "forward", "addon_mkt_forward.csv")
FROZEN = ("已出場", "不計（加碼日壞根）")


def holdings_default():
    """持股.csv（backtest.holdings，只讀）中來源含營量／營飆者；營飆營量 ⇒ 兩策略各一列。金額以「份」記（1 份 ＝ 該策略那部分的原買進金額）。"""
    from backtest import holdings as HD
    rows = HD.read_csv(); ED = HD.entry_dates(); out = []
    for c_, bd_, bp_, _, src in rows:
        if src not in ("營量", "營飆", "營飆營量") or bd_ is None:
            continue
        ed_ = ED.get(c_) or bd_
        for sn in ("營量", "營飆"):
            if sn in src and not any(o["代號"] == c_ and o["策略"] == sn for o in out):
                out.append({"代號": c_, "策略": sn, "進場日": ed_, "金額_份": 1.0, "持股來源": f"持股.csv:{src}"})
    return out


def forward_update(sha=None, data=None, asof=None, holdings=None, path=None, procs=2, log=print, start=FWD_START):
    """前瞻紀錄逐日追加（每日名單或月底呼叫皆可；重跑同一資料日結果相同）。⇒ 更新後的 DataFrame。
    規則（登錄 seq2 §一、§二、§四；逐式同 addon_daily／researchAddOn U2～U4）：
      持股 ＝ holdings（list of dict：代號、策略、進場日、金額_份、持股來源），預設 holdings_default()；判定只用規則模擬（t＋1 開盤、原持股同日收盤），⛔ 不用使用者實際成交
      每筆持股每策略只認第一次觸發（h ≥ 10 ∧ g ≥ q(h,t)；營量 q99、營飆 q95；R1 母體 ＝ addon_daily 同式）；第一次觸發在 start 之前 ⇒ 不記（狀態檔記「定版前已觸發」）
      大盤旗標 ＝ 公開庫 main（sha）market_index.csv：t 收盤 ＞ 含 t 20 筆平均；讀不到 ⇒ 列「待指數」、下次重算
      t ＝ 資料日 ⇒ 列「待成交」（下次重算）；t＋1 是壞根 ⇒「不計（加碼日壞根）」；t＋1 沒有有效開盤 ⇒ 不算觸發、往後再判（同 U2）
      成交：t＋1 開盤；鎖漲停（原始 最高＝最低 且 開盤 ≥ 漲停價）⇒ 買不到；是否加 ∈ 加／被擋／未成交（鎖漲停）／被擋（假如有加也鎖漲停）
      出場：xbar ＝ D.exit_pos(進場, 60／120)；(t＋1, xbar] 有壞根 ⇒ 壞根前最後有效收盤；否則 xbar 收盤（還原、ffill）
      報酬_假如有加 ＝ 還原賣價 ÷ 還原加碼價 − 1 − 0.585%（出場時以當下還原序列算、之後凍結）；加碼價、出場價記原始價
      子帳戶損益_無條件版 ＝ 金額 × 報酬（鎖漲停 ⇒ 0）；子帳戶損益_濾網版 ＝ 只有「加」才有，其餘 0
      已凍結（狀態 ∈ FROZEN）的列 ⛔ 不重算；「持有中」只補出場欄；其餘重算
    """
    from backtest import addon_daily as AD
    from backtest import data as D
    from backtest import universe_gate as UG
    from multiprocessing import Pool
    path = path or FWD_PATH
    sha = main_sha(sha or "origin/main")
    DATA = data or os.path.expanduser(f"~/h2data/{sha}/data")
    if not os.path.isdir(DATA):
        raise SystemExit(f"⛔ 找不到資料快照 {DATA}（每日名單 run_daily_list.sh 會先 git archive）")
    D.DATA = DATA
    cal = D.load_calendar()
    if asof is not None:
        cal = cal[cal <= pd.Timestamp(asof)]
    n = len(cal); T = n - 1; s0 = int(cal.searchsorted(pd.Timestamp(start)))
    try:
        tx, txsha = load_index(sha)
    except Exception:
        tx, txsha = pd.Series(dtype=float), ""
    txc = tx.to_numpy(float); txi = {d: i for i, d in enumerate(tx.index)}

    def mk(t):
        i = txi.get(cal[t])
        if i is None or i < MA_N - 1:
            return None
        return bool(txc[i] > txc[i - MA_N + 1:i + 1].mean())
    H = holdings if holdings is not None else holdings_default()
    old = pd.read_csv(path, dtype=str, keep_default_na=False) if os.path.exists(path) else pd.DataFrame(columns=FWD_COLS)
    stp = path + ".state.json"
    state = json.load(open(stp, encoding="utf-8")) if os.path.exists(stp) else {}
    OLD = {(r["策略"], r["代號"], r["進場日"]): r for r in old.to_dict("records")}
    stocks = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    mk_of = stocks.drop_duplicates("stock_id", keep="last").set_index("stock_id")["market"].to_dict()
    todo = []                                                      # 需要掃觸發的持股
    for h in H:
        e = int(cal.searchsorted(pd.Timestamp(h["進場日"])))
        if e > T:
            continue
        key = (h["策略"], h["代號"], str(cal[e].date()))
        r = OLD.get(key)
        if r is not None and r["狀態"] in FROZEN + ("持有中",):
            continue
        if "|".join(key) in state:
            continue
        xb = D.exit_pos(e, HOLD[h["策略"]])
        if xb - 1 < s0:                                            # 判斷窗整段在起點之前
            continue
        todo.append(dict(h, e=e, xb=xb, key=key))
    TR = {}                                                         # key ⇒ (t, h, g, q) 或 ("加碼日壞根", t)
    if todo:
        lo = max(min(z["e"] for z in todo) - 1, 0)
        days = sorted({d for z in todo for d in range(z["e"] + AO.HMIN - 1, min(z["xb"] - 1, T) + 1)})
        prev = UG.GATE_V2; UG.set_gate_v2(True)
        try:
            U = UG.gate3(stocks); U = U[U["stock_id"].map(AD.okcode)].reset_index(drop=True)
            extra = [(c_, mk_of.get(c_, "twse")) for c_ in sorted({z["代號"] for z in todo}) if c_ not in set(U["stock_id"])]
            AD._G.update(DATA=DATA, cal=cal, lo=lo)
            with Pool(procs) as pool:
                res = dict(pool.map(AD._job, list(zip(U["stock_id"], U["market"])) + extra, chunksize=16))
        finally:
            UG.set_gate_v2(prev)
        usids = [s for s in U["stock_id"] if res.get(s) is not None]
        C = np.vstack([res[s]["c"] for s in usids]); BAR = np.vstack([res[s]["bar"] for s in usids])
        A20 = np.vstack([res[s]["a20"] for s in usids]); PV = np.vstack([res[s]["pv"] for s in usids])
        MKT = BAR & PV & np.isfinite(A20)
        R1 = {}
        for d in days:
            ii = np.flatnonzero(MKT[:, d - lo])
            R1[d] = ii[np.argsort(-A20[ii, d - lo], kind="stable")[:int(np.ceil(AD.X_R1 * len(ii)))]] if len(ii) else ii
        need_bad = sorted({usids[i] for d in days for i in R1[d]} | {z["代號"] for z in todo})
        with Pool(procs) as pool:
            BADD = dict(pool.map(AD._badjob, need_bad, chunksize=8))
        BADM = {s: np.cumsum(np.r_[0, BADD[s]]) for s in BADD}
        QC = {}

        def q_of(pct, h_, t):
            k = t - lo; k0 = k - h_
            if (pct, h_, t) not in QC:
                v = []
                if k0 >= 0:
                    for i in R1[t]:
                        s = usids[i]
                        if BAR[i, k] and np.isfinite(C[i, k0]) and BADM[s][k + 1] - BADM[s][k0 + 1] == 0:
                            v.append(C[i, k] / C[i, k0] - 1.0)
                v = np.asarray(v, float); v = v[np.isfinite(v)]
                QC[(pct, h_, t)] = float(np.percentile(v, pct)) if len(v) >= AD.MINPOP else np.nan
            return QC[(pct, h_, t)]
        ix = {s: i for i, s in enumerate(usids)}
        for z in todo:
            sid, sn, e, xb = z["代號"], z["策略"], z["e"], z["xb"]
            rr = res.get(sid)
            if rr is None:
                continue
            cc = rr["c"]; bb = rr["bar"]; oo = rr["o"]
            ep = oo[e - lo]
            if not np.isfinite(ep):
                continue
            cb = BADM.get(sid)
            for t in range(e + AO.HMIN - 1, min(xb - 1, T) + 1):
                k = t - lo
                if cb is not None and cb[k + 1] - cb[e - lo + 1] > 0:
                    TR[z["key"]] = ("壞根", t); break
                if not bb[k]:
                    continue
                q = q_of(AD.PCT[sn], t - e + 1, t)
                if not np.isfinite(q):
                    continue
                g = cc[k] / ep - 1.0
                if g >= q:
                    if t < T:
                        if cb is not None and cb[k + 2] - cb[k + 1] > 0:
                            TR[z["key"]] = ("加碼日壞根", t, t - e + 1, g, q); break
                        if not np.isfinite(oo[k + 1]):
                            continue
                    TR[z["key"]] = ("觸發", t, t - e + 1, g, q); break
            else:
                if T >= xb - 1:
                    TR[z["key"]] = ("窗結束未觸發", None)
    # 價格（單檔）
    PX = {}

    def px_of(sid):
        if sid not in PX:
            st = D.load_stock(sid, mk_of.get(sid, "twse"), cal)
            raw = load_raw(DATA, sid, cal)
            from backtest import researchBARR as BARR
            bad = BARR.bad_part(sid, DATA, cal).copy()
            adj = D.load_adj(sid)
            if adj is not None and len(adj) and "event" in adj:
                for d_, ev_ in zip(adj["date"], adj["event"].astype(str)):
                    if ev_ in ("reduce", "parvalue"):
                        k = int(cal.searchsorted(d_))
                        if k < n:
                            bad[k] = True
            c0 = st.df["close"].to_numpy(float)
            PX[sid] = {"c": pd.Series(c0).ffill().to_numpy(float), "bar": np.isfinite(c0), "o": st.df["open"].to_numpy(float),
                       "ro": raw["open"].to_numpy(float), "rh": raw["high"].to_numpy(float), "rl": raw["low"].to_numpy(float), "rc": raw["close"].to_numpy(float),
                       "bad": np.asarray(bad[:n], bool)}
        return PX[sid]
    stamp = now_tpe()
    out = {k: dict(v) for k, v in OLD.items()}

    def fill_exit(row, sid, sn, e, ta):
        P_ = px_of(sid); xb = D.exit_pos(e, HOLD[sn])
        bads = np.flatnonzero(P_["bad"][ta + 1:min(xb, T) + 1]) + ta + 1
        if len(bads):
            kb = int(bads[0]); vb = np.flatnonzero(P_["bar"][ta:kb]); x = int(vb[-1]) + ta if len(vb) else ta; kind = "壞根前收盤強制"
        elif T >= xb:
            x = xb; kind = "同原持股" if P_["bar"][xb] else "同原持股（當天無成交、用前收）"
        else:
            return row
        r = P_["c"][x] / P_["o"][ta] - 1.0 - COST
        A = float(row["金額_份"] or 1.0)
        row.update({"出場日": str(cal[x].date()), "出場價": f"{P_['rc'][x]:.4f}" if np.isfinite(P_["rc"][x]) else "", "出場種類": kind,
                    "報酬_假如有加": f"{r:.6f}", "狀態": "已出場",
                    "子帳戶損益_無條件版": f"{(A * r if row['鎖漲停'] != 'True' else 0.0):.6f}",
                    "子帳戶損益_濾網版": f"{(A * r if row['是否加'] == '加' else 0.0):.6f}", "記錄時間": stamp})
        return row
    for h in H:
        e = int(cal.searchsorted(pd.Timestamp(h["進場日"])))
        if e > T:
            continue
        key = (h["策略"], h["代號"], str(cal[e].date()))
        r = out.get(key)
        if r is not None and r["狀態"] == "持有中":
            ta = int(cal.searchsorted(pd.Timestamp(r["加碼日"])))
            out[key] = fill_exit(r, h["代號"], h["策略"], e, ta); continue
        if r is not None and r["狀態"] in FROZEN:
            continue
        tr = TR.get(key)
        if tr is None:
            out.pop(key, None); continue
        if tr[0] in ("壞根", "窗結束未觸發"):
            state["|".join(key)] = tr[0]; out.pop(key, None); continue
        t = tr[1]
        if t < s0:
            state["|".join(key)] = f"定版前已觸發 {cal[t].date()}"; out.pop(key, None); continue
        base = {c: "" for c in FWD_COLS}
        base.update({"觸發日": str(cal[t].date()), "代號": h["代號"], "策略": h["策略"], "進場日": key[2], "h": str(tr[2]), "g": f"{tr[3]:.6f}",
                     "門檻": f"{tr[4]:.6f}", "金額_份": str(h.get("金額_份", 1.0)), "持股來源": h.get("持股來源", ""), "記錄時間": stamp,
                     "資料sha": sha, "指數sha": txsha})
        if tr[0] == "加碼日壞根":
            base.update({"是否加": "不加（加碼日壞根）", "狀態": "不計（加碼日壞根）"}); out[key] = base; continue
        f = mk(t)
        base["大盤旗標"] = "" if f is None else str(f)
        if f is None:
            base["狀態"] = "待指數"; out[key] = base; continue
        if t == T:
            base.update({"是否加": "待隔日開盤" + ("（大盤成立）" if f else "（大盤不成立 ⇒ 被擋）"), "狀態": "待成交"}); out[key] = base; continue
        ta = t + 1; P_ = px_of(h["代號"])
        lk, upo, alt, _ = lock_info(P_["ro"], P_["rh"], P_["rl"], P_["rc"], P_["c"], t, ta, cal[ta])
        add = ("加" if not lk else "未成交（鎖漲停）") if f else ("被擋" if not lk else "被擋（假如有加也鎖漲停）")
        base.update({"是否加": add, "加碼日": str(cal[ta].date()), "加碼價": f"{P_['ro'][ta]:.4f}", "鎖漲停": str(bool(lk)),
                     "跳空": f"{P_['o'][ta] / P_['c'][t] - 1.0:.6f}", "狀態": "持有中"})
        out[key] = fill_exit(base, h["代號"], h["策略"], e, ta)
    df = pd.DataFrame(list(out.values()), columns=FWD_COLS).sort_values(["觸發日", "策略", "代號"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"; df.to_csv(tmp, index=False); os.replace(tmp, path)
    json.dump(state, open(stp + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(stp + ".tmp", stp)
    log(f"[前瞻] {cal[T].date()}｜持股 {len(H)}｜紀錄 {len(df)} 列（{df['狀態'].value_counts().to_dict() if len(df) else {}}）⇒ {path}")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--forward", action="store_true")
    ap.add_argument("--sha", default=None); ap.add_argument("--asof", default=None); ap.add_argument("--path", default=None)
    a = ap.parse_args()
    if a.forward:
        forward_update(a.sha, asof=a.asof, path=a.path, procs=a.procs)
        return
    os.makedirs(OUT, exist_ok=True)
    log = AO.log_to(os.path.join(OUT, "run.log"))
    log(f"[開跑] {now_tpe()}（台北）")
    run(a, log)


if __name__ == "__main__":
    main()

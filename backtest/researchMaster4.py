# -*- coding: utf-8 -*-
"""PREREG大師三套 seq4 本體【仿 App 麥克墨菲／麥克喜偉／詹姆士歐沙那希 條件；10 檔；抱 20／60／120 天】——回測線落地（A0 定案版）。

登錄：台股策略線 PREREG大師三套 seq4（sha 48365ba96fb2b1a9，2026-09-27 17:09）；裁定 seq210 §五（發號、附則①②③）、seq214 §二（資料閘三處讀法）、
      seq231 §三（A0／L1（另報 L2）／P1）、seq241（H 軸 {20,60,120}）、seq242（沿用的預設、合格／另列固定跟進出場敏感度）、
      seq245（N_組合 ＋9、fin_hist、A2 暫定 A0 定案）、seq275（等 A0 2019～2026 全補齊才跑）；資料庫 2026-10-04 10:23（A0 全部完成）。
名稱一律「仿 App〔大師〕條件」；⚠ 算法照本線定義，不保證與 App 相同（附則①）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMaster4 [--procs 4] [--seeds 200] [--fake 1000]
    抽樣查核：同一支加 --check（⛔ 查核段不呼叫本體的條件、可用日、組合函式，自己從原始 CSV 重算）

⭐ 讀法寫死時間：2026-10-04 11:30（台北）；寫死前 ⛔ 沒看任何本件報酬（pre 版 2026-09-27 只看過可算比例與候選數，見 resultsMaster/PRE_GATE.md）。
⚠ 沿革（照實記）：
  11:31～11:34 以 2 顆種子試跑（只為測程式與耗時）；log 尾端誤顯示了歐沙那希 3 列（2 顆、起點 2018-04-02 版）的年化／回落 ⇒ 本線看過這 3 個數字。
  11:36 改一處讀法：起點。原因是【資料閘】不是報酬：試跑顯示 fin_hist（2013Q1 起）讓 5 年條件在 2018-04-02 就可算 ≥ 90%，
    但 2018-04～2019-05 每一列的「最新一季」都沒有 t57sb01 時戳、全靠法定期限補位（＝ seq231 明文禁止的 A1，有前視），
    且裁定 0026 §二① 寫明起點「以 t57sb01 可用日為準」⇒ 加一條：起點還須「分母內最新一季有 A0 時戳的比例首次 ≥ 90%」（執行者補）；
    原公式起點（2018-04-02）與裁定 0026 估的 2020-04-01 兩個起點都照跑、列為描述（起點敏感度）。之後 ⛔ 不再改。

═══ 資料（釘版）═══
  財報：tw-stock-data main 1fb8815e81 的 data/mops/fin_hist（XBRL 季快照，含已下市；seq4 §九①，取代 fs_hist／bs_hist）
        ⇒ 與 a2dadbca4a（品質件用的那版）逐檔相同（diff 0）；研發：同 commit data/mops/rd_hist（XBRL feed，§九①「研發仍用 XBRL feed」）
  可用日：同 commit data/meta/filing_dates.csv（t57sb01；2019～2026 全部問完，資料庫 10-04 10:23）
  本益比：同 commit data/universe/per（上市）＋ otcper（上櫃）＝ P1（seq231）；取量測日 t−1 那一天的檔
  價格、日曆、名冊（first_seen）：edc6f8002f 快照（researchH2，同 W1）；git archive 到 ~/msdata/<sha>（唯讀）
  母體與量測日：W1 eligible（liq_ok ∧ bars_ok ∧ inst_ok），面板 resultsp9_engine/panel_ext.csv.gz（W1 同一組量測日、延伸到 2026-08）

═══ 條件（登錄 §一 逐字機器化；⛔ 不掃門檻）═══
  單季 ＝ 累計相減（Q1 ＝ 累計；Q4 ＝ 全年 − Q3 累計）；資產負債表取期末；同 (stock_id, period) 重複取最後一列（品質件同）
  年 ROE ＝ 全年母公司淨利 ÷ 年底母公司權益｜年 ROA ＝ 全年母公司淨利 ÷ 年底總資產｜年負債比 ＝ 年底總負債 ÷ 年底總資產
  年營收成長 ＝ 全年營收 ÷ 前一年 − 1｜年 EPS 增率 ＝ 全年 EPS ÷ 前一年 − 1（前一年 ≤ 0 ⇒ 不符）
  母公司淨利／權益空白 ⇒ 本期淨利（ni_ytd）／權益總計（equity_total）（seq214 ②；逐值替代）
  M1 近 12 個已可用單季（單季營業利益 ÷ 單季營收）平均 ＞ 10%｜M2 年 ROE 近 5 個已可用年報平均 ＞ 8%｜M3 年營收成長近 3 年平均 ＞ 10%
  M4 近 4 季研發 ÷ 同期營收 ＞ 5%（rd_hist；近 4 季 ＝ 本季累計 ＋ 上年全年 − 上年同季累計，Q4 用全年；研發空白／XBRL 沒這家 ⇒ 不符）
  X1 ＝ M2｜X2 年負債比 5 年平均 ＜ 30%｜X3 本益比 ＜ 15｜X4 ＝ M3
  O1 年 ROA 5 年平均 ＞ 8%｜O2 ＝ M2｜O3 年 EPS 增率 3 年平均 ＞ 30%｜O4 本益比 ＜ 15
  本益比空白（虧損）⇒ 不符；當天檔裡沒有這檔 ⇒ 判不出（不可算、也不符）

═══ 可用日（⭐ A0 定案；seq231 §三、seq245 §三）═══
  登錄 §一 原文：「可用日：t57sb01 該檔該期『上傳日期』的下一個交易日（同 G seq4 §三；缺時戳 ⇒ 法定期限下一交易日，計數必報）」
  資料庫 10-04 ①：同一季多個檔（合併、個體、英文、更正…）⇒ 取該季【最早】上傳時戳（⛔ 不取最晚）；② 是電子檔上傳時戳、不是法定公告日
  資料庫信引「裁定 seq263」定盤中／盤後口徑：⚠ 本線查 seq263（2026-09-28 09:05）內文是營量名單插隊、沒有 A0 時點規則；
    A0 的定義出處實為 seq231 §三（A0）＋ seq245 §三（A2 暫定、A0 定案）＋ 登錄 §一（上傳日期的下一個交易日）⇒ 照登錄字面：
  ⭐ 盤中、盤後上傳一律算【上傳日期的下一個交易日】起可用（不看時刻；比「盤後才算隔天」保守，不會前視）
  量測日 T 可用 ⇔ 可用日 ≤ T（登錄「每個量測日只用當天已可用的最新各期」；T＋1 開盤進場）
  缺時戳（主要在 2019～2020 的 Q1／Q3，資料庫 ③）⇒ 登錄原文：法定期限（Q1 5/15、Q2 8/14、Q3 11/14、年報 次年 3/31）的下一個交易日；計數必報
    ⚠ seq231「⛔ 不用 A1」指整條規則改用法定期限；此處只是登錄原文的缺時戳補位 ⇒ 照登錄，另報缺時戳補位的家數與它們進候選的筆數（執行者補：報法）
  2019 年以前的季：資料庫只補 2019 起（使用者 09-29）⇒ 2015～2018 只有舊母體一部分時戳 ⇒ 其餘同上缺時戳規則；
    窗起點之後這些季只當「歷史年報／季」用（早已過期），不影響「最新可用一季」的判定（執行者補：說明；起點規則見下）

═══ 本線讀法（pre 已交、裁定 seq231 核定者照用；其餘標「執行者補」）═══
  L1 上市滿 N 年 ＝ first_seen ≤ T − N 年；first_seen ＝ 快照起點 2015-01-05 視為早於快照（seq231 L1）；另報 L2（不看上市年數）
  「可算」＝ 依規則判得出來；研發空白、本益比空白、前一年 EPS ≤ 0、分母 ≤ 0 ＝ 依定義不符（判得出來）；近 12 季須連續（pre 已交）
  可算比例分母 ＝ eligible ∧ 上市滿 5 年（三套都含 5 年條件；seq214 ①）；候選 ＝ 四條都符合 ∧ 上市滿 5 年
  最新可用年報 Y ＝ 可用日 ≤ T 的最大 Q4（執行者補：pre 用 L 推 Y，A0 下改直接查，兩者在正常申報順序下相同）
  起點 ＝ max(2017-03-02, 三套可算比例都首次 ≥ 90% 的量測日, 分母內最新一季有 A0 時戳的比例首次 ≥ 90% 的量測日【11:36 加，執行者補】)；
    0050 用同一起點重算（附則②）；窗 ＜ 5 年 ⇒ 結果句前加「樣本只有 x 年」

═══ 組合（登錄 §二 寫死）═══
  research11.simulate_mtm；n_slots＝10、pick=None（候選多於空槽抽籤）、cash_mode="zero"；T＋1 開盤買、第 H 根收盤賣（進場那根算第 1 根），H ∈ {20,60,120}
  成本 0.585%；200 顆種子 1000＋r；tradable（開盤漲停買不到、跌停賣不掉）＋ delist on ＋ 停止交易強制出場（stop_force，seq255）
  窗：起點量測日 ～ 2026-08-24（主窗尾）；最後一個量測日 ＜ 窗尾；第 H 根超出日曆尾 ⇒ 出場日截到日曆最後一天（T1 讀法：窗內逐日市值不受影響）
  指標：年化／回落 ＝ research13.window_stats（245 日）；200 顆取年化中位、回落中位；比值 ＝ 年化中位 ÷ |回落中位|
═══ 判定（§四；9 格）═══
  年化中位 ＞ 0050 同窗 且 比值 ≥ 0050 比值 ⇒ 合格；只過第一條 ⇒ 另列；否則不合格
  假訊號 S0（⛔ 不判）：每套 × H，每個量測日從同母體（W1 eligible；執行者補：不另加上市滿 5 年）隨機抽「與當日該套候選同數量」的股票當候選；
    1,000 顆（抽樣 default_rng([20261004, 套序, H, r])、引擎 default_rng([20261005, 套序, H, r])）⇒ 報合格比例 p；p ≥ 5% ⇒ 該套句前加「⚠ 隨機也有 x 合格」
  某套候選數中位 ＜ 10 的量測日占 ＞ 三成 ⇒ 句前加「常常湊不滿 10 檔」（執行者補：以「候選 ＜ 10 的量測日比例 ＞ 30%」判）
═══ 描述（⛔ 不判、不計 N）═══
  ⓐ 每套拿掉一條（各 4 臂 × H 三值，200 顆）｜ⓑ 每套與營飆 v1 混 50／50（resultsYfMix13 eq_main.npz 的 yf 200 顆逐顆配對；每年第一個交易日調回、
     移動金額 × 0.585%）：年化、回落、日報酬相關、同時持有檔數（營飆 positions.csv.gz cell 1 同種子）｜ⓒ 逐年 100 萬期末（年初第一個交易日放 100 萬、200 顆中位）；三套候選重疊
  L2（另報）｜現實版（researchSlip 定義：C1 每邊 ＋0.3%＋C2 50 萬平方根衝擊＋C4 均價；C3 不另加——本引擎 tradable 已是開盤漲停買不到）
  月分群（執行者補）：每格取 200 顆裡年化排第 100 的那顆，逐月報酬 − 0050 逐月報酬，以月為群的平均與 95% t 區間
  合格／另列 ⇒ 固定跟進出場敏感度（seq242 ②）：停損 −10／−20%（stop fix）、停利 +30／+50% 賣半（trim_rule gain）、檔數 5／20；
     ⚠ 2ATR 停損、時停 R0-40 引擎沒有對應開關 ⇒ 本輪不做、照實寫（執行者補）
輸出 backtest/resultsMaster4/
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                # ⭐ D.DATA ⇒ edc6f8002f 快照；chdir ⇒ repo
D, TR, R = H2.D, H2.TR, H2.R
from backtest import research13 as R13
from backtest import p4_features as P4F

OUT = "backtest/resultsMaster4"
MS_SHA = "1fb8815e81aa53edf91aacb8ebb4125c716ead3f"
FD = os.path.expanduser(f"~/msdata/{MS_SHA}/data")
PANEL = "backtest/resultsp9_engine/panel_ext.csv.gz"
W0_MAIN, W1_MAIN = "2017-03-02", "2026-08-24"
SNAP_FLOOR = pd.Timestamp("2015-01-05")
COV_TH = 0.90
COST = 0.00585
HS = (20, 60, 120)
NSLOT = 10
ANCHOR = (0.24020209886370614, -0.3395700527611012)
TAGT = "2026-10-04 11:30（台北）；起點規則 11:36 補（資料閘原因，見沿革）"
CONDS = ("M1", "M2", "M3", "M4", "X2", "O1", "O3", "PE")
SETS = {"M": ("M1", "M2", "M3", "M4"), "X": ("M2", "X2", "PE", "M3"), "O": ("O1", "M2", "O3", "PE")}
SET_NAME = {"M": "仿 App 麥克墨菲條件", "X": "仿 App 麥克喜偉條件", "O": "仿 App 詹姆士歐沙那希條件"}
CNAME = {"M1": "近12季營益率＞10%", "M2": "ROE 5年均＞8%", "M3": "營收成長3年均＞10%", "M4": "研發÷營收＞5%", "X2": "負債比5年均＜30%",
         "O1": "ROA 5年均＞8%", "O3": "EPS增率3年均＞30%", "PE": "本益比＜15"}
_G: dict = {}


def deadline(y, q):
    return pd.Timestamp(f"{y + 1}-03-31") if q == 4 else pd.Timestamp(f"{y}-{('05-15', '08-14', '11-14')[q - 1]}")


# ═════════════ 財報與可用日 ═════════════
def load_fin(log):
    cols = ["stock_id", "period", "rev_ytd", "opi_ytd", "ni_ytd", "nip_ytd", "eps_ytd", "assets", "liabilities", "equity_parent", "equity_total"]
    fs = sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv")))
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=cols) for f in fs], ignore_index=True)
    dup = int(F.duplicated(["stock_id", "period"]).sum())
    F = F.drop_duplicates(["stock_id", "period"], keep="last")
    F["p"] = F["period"].str[:4].astype(int) * 4 + F["period"].str[-1].astype(int) - 1
    for c in cols[2:]:
        F[c] = pd.to_numeric(F[c], errors="coerce")
    F["ni"] = np.where(np.isfinite(F["nip_ytd"]), F["nip_ytd"], F["ni_ytd"])
    F["eq"] = np.where(np.isfinite(F["equity_parent"]), F["equity_parent"], F["equity_total"])
    fb_ni = int((~np.isfinite(F["nip_ytd"]) & np.isfinite(F["ni_ytd"])).sum()); fb_eq = int((~np.isfinite(F["equity_parent"]) & np.isfinite(F["equity_total"])).sum())
    Q = {}
    for s, g in F.groupby("stock_id", sort=False):
        Q[s] = {int(p): (rv, oi, ni, eps, ta, tl, eq) for p, rv, oi, ni, eps, ta, tl, eq in
                zip(g["p"], g["rev_ytd"], g["opi_ytd"], g["ni"], g["eps_ytd"], g["assets"], g["liabilities"], g["eq"])}
    rs = sorted(glob.glob(os.path.join(FD, "mops", "rd_hist", "*.csv")))
    Rd = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "rd_ytd", "rev_ytd"]) for f in rs], ignore_index=True)
    dupr = int(Rd.duplicated(["stock_id", "period"]).sum())
    Rd = Rd.drop_duplicates(["stock_id", "period"], keep="last")
    Rd["p"] = Rd["period"].str[:4].astype(int) * 4 + Rd["period"].str[-1].astype(int) - 1
    for c in ("rd_ytd", "rev_ytd"):
        Rd[c] = pd.to_numeric(Rd[c], errors="coerce")
    RD = {s: {int(p): (a, b) for p, a, b in zip(g["p"], g["rd_ytd"], g["rev_ytd"])} for s, g in Rd.groupby("stock_id", sort=False)}
    log(f"[財報] fin_hist {len(fs)} 季檔 {len(F):,} 列（重複 {dup}）｜{len(Q):,} 家｜母公司淨利改本期淨利 {fb_ni:,}、權益改權益總計 {fb_eq:,}｜rd_hist {len(Rd):,} 列（重複 {dupr}）")
    return Q, RD, {"fin_dup": dup, "rd_dup": dupr, "ni_fallback": fb_ni, "eq_fallback": fb_eq, "fin_rows": int(len(F))}


def load_avail(Q, cal, log):
    """(sid, p) ⇒ 可用日位置、來源（ts／dl）。A0：最早上傳時戳的日期之後第一個交易日；缺 ⇒ 法定期限之後第一個交易日。"""
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fd["ts"] = pd.to_datetime(fd["uploaded_at"], errors="coerce")
    first = fd.dropna(subset=["ts"]).groupby(["stock_id", "year", "season"])["ts"].min()
    TS = {(s, int(y) * 4 + int(q) - 1): t for (s, y, q), t in first.items()}
    AV = {}; SRC = {}
    for s, d in Q.items():
        for p in d:
            y, q0 = divmod(p, 4)
            t = TS.get((s, p))
            if t is not None:
                AV[(s, p)] = int(cal.searchsorted(pd.Timestamp(t.date()), side="right")); SRC[(s, p)] = "ts"
            else:
                AV[(s, p)] = int(cal.searchsorted(deadline(y, q0 + 1), side="right")); SRC[(s, p)] = "dl"
    c19 = Counter((SRC[k], k[1] // 4 >= 2019) for k in SRC)
    log(f"[可用日 A0] filing_dates {len(fd):,} 列｜季有時戳 {len(TS):,}｜財報季 2019 起：時戳 {c19[('ts', True)]:,}、缺時戳補法定期限 {c19[('dl', True)]:,}｜2019 前：時戳 {c19[('ts', False)]:,}、補 {c19[('dl', False)]:,}")
    return AV, SRC, {"filing_rows": int(len(fd)), "quarters_with_ts": len(TS), "fin_q_2019on_ts": c19[("ts", True)], "fin_q_2019on_dl": c19[("dl", True)],
                     "fin_q_pre2019_ts": c19[("ts", False)], "fin_q_pre2019_dl": c19[("dl", False)]}


class Fin:
    def __init__(self, Q, RD, AV, SRC):
        self.Q, self.RD, self.SRC = Q, RD, SRC
        self.ord = {}
        for s, d in Q.items():
            ps = sorted(d, key=lambda p: (AV[(s, p)], p))
            self.ord[s] = ([AV[(s, p)] for p in ps], ps)
        self.cache = {}

    def latest(self, s, t):
        """可用日 ≤ t 的最新一季 L、最新年報 Y（年）。"""
        o = self.ord.get(s)
        if o is None:
            return None, None
        av, ps = o
        k = int(np.searchsorted(av, t, side="right"))
        if k == 0:
            return None, None
        ok = ps[:k]
        L = max(ok); q4 = [p for p in ok if p % 4 == 3]
        return L, (max(q4) // 4 if q4 else None)

    def v(self, s, p, i):
        r = self.Q[s].get(p)
        if r is None:
            return np.nan
        x = r[i]
        return float(x) if np.isfinite(x) else np.nan

    def single(self, s, p, i):
        a = self.v(s, p, i)
        return a if p % 4 == 0 else a - self.v(s, p - 1, i)

    def conds(self, s, L, Y):
        key = (s, L, Y)
        if key in self.cache:
            return self.cache[key]
        out = {}; d = self.Q[s]
        # M1
        ps = list(range(L - 11, L + 1))
        if all(p in d for p in ps) and all((p - 1) in d for p in ps if p % 4 != 0):
            rv = [self.single(s, p, 0) for p in ps]; oi = [self.single(s, p, 1) for p in ps]
            if all(np.isfinite(x) for x in rv + oi):
                mg = [o / r if r > 0 else np.nan for o, r in zip(oi, rv)]
                out["M1"] = (True, bool(all(np.isfinite(mg)) and np.mean(mg) > 0.10))
            else:
                out["M1"] = (False, False)
        else:
            out["M1"] = (False, False)
        if Y is None:
            for c in ("M2", "O1", "X2", "M3", "O3"):
                out[c] = (False, False)
        else:
            ys = range(Y - 4, Y + 1)
            ni = [self.v(s, y * 4 + 3, 2) for y in ys]; eq = [self.v(s, y * 4 + 3, 6) for y in ys]
            ta = [self.v(s, y * 4 + 3, 4) for y in ys]; tl = [self.v(s, y * 4 + 3, 5) for y in ys]

            def avg_rule(num, den, th, gt=True):
                if not all(np.isfinite(x) for x in num + den):
                    return (False, False)
                v_ = [n / e if e > 0 else np.nan for n, e in zip(num, den)]
                if not all(np.isfinite(v_)):
                    return (True, False)
                m = float(np.mean(v_))
                return (True, bool(m > th if gt else m < th))
            out["M2"] = avg_rule(ni, eq, 0.08); out["O1"] = avg_rule(ni, ta, 0.08); out["X2"] = avg_rule(tl, ta, 0.30, gt=False)
            ys4 = range(Y - 3, Y + 1)
            for c, i, th in (("M3", 0, 0.10), ("O3", 3, 0.30)):
                x = [self.v(s, y * 4 + 3, i) for y in ys4]
                if all(np.isfinite(z) for z in x):
                    g = [x[k] / x[k - 1] - 1 if x[k - 1] > 0 else np.nan for k in range(1, 4)]
                    out[c] = (True, bool(all(np.isfinite(g)) and np.mean(g) > th))
                else:
                    out[c] = (False, False)
        # M4（rd_hist）
        rd = self.RD.get(s); y, q0 = divmod(L, 4)
        need = [L] if q0 == 3 else [L, (y - 1) * 4 + 3, (y - 1) * 4 + q0]; sg = [1.0] if q0 == 3 else [1.0, 1.0, -1.0]
        if rd is None or any(k not in rd for k in need):
            st = "no_row"; out["M4"] = (True, False)
        else:
            a = [float(rd[k][0]) for k in need]; b = [float(rd[k][1]) for k in need]
            if not all(np.isfinite(x) for x in a):
                st = "rd_blank"; out["M4"] = (True, False)
            elif not all(np.isfinite(x) for x in b):
                st = "rev_missing"; out["M4"] = (False, False)
            else:
                num = sum(u * x for u, x in zip(sg, a)); den = sum(u * x for u, x in zip(sg, b))
                st = "ok"; out["M4"] = (True, bool(den > 0 and num / den > 0.05))
        out["_rd"] = st
        self.cache[key] = out
        return out


def load_pe(date, cache):
    if date in cache:
        return cache[date]
    d = {}
    for sub, mk in (("per", "twse"), ("otcper", "tpex")):
        p = os.path.join(FD, "universe", sub, f"{date}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p, dtype={"stock_id": str}, usecols=["stock_id", "per"])
            for s, v in zip(df["stock_id"].astype(str).str.strip(), pd.to_numeric(df["per"], errors="coerce")):
                d.setdefault(s, float(v))
    cache[date] = d
    return d


# ═════════════ 資料閘＋候選 ═════════════
def build_rows(log):
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    fseen = pd.to_datetime(stocks.set_index("stock_id")["first_seen"]).to_dict()
    mk = stocks.set_index("stock_id")["market"].to_dict()
    pan = P4F.read_panel(PANEL)
    pan = pan[(pan["measure_date"] >= pd.Timestamp("2017-01-01")) & pan["eligible"].astype(bool)]
    pos = {d: i for i, d in enumerate(cal)}
    pan = pan[pan["measure_date"].isin(pos)]
    Q, RD, fstat = load_fin(log)
    AV, SRC, astat = load_avail(Q, cal, log)
    F = Fin(Q, RD, AV, SRC)
    cache = {}; rows = []
    for T, g in pan.groupby("measure_date", sort=True):
        t = pos[T]
        pe = load_pe(str(cal[t - 1].date()), cache)
        for s in g["stock_id"].astype(str):
            fs_ = fseen.get(s, pd.NaT)
            age5 = bool(pd.notna(fs_) and (fs_ <= SNAP_FLOOR or fs_ <= T - pd.DateOffset(years=5)))
            L, Y = F.latest(s, t)
            if L is None:
                c = {k: (False, False) for k in ("M1", "M2", "M3", "M4", "X2", "O1", "O3")}; rdst = "no_fin"; lsrc = ""
            else:
                c = F.conds(s, L, Y); rdst = c["_rd"]; lsrc = SRC[(s, L)]
            v = pe.get(s, None)
            c = dict(c); c["PE"] = (False, False) if v is None else (True, bool(np.isfinite(v) and 0 < v < 15))
            row = {"T": T, "t": t, "sid": s, "market": mk.get(s, "twse"), "age5": age5, "L": L, "Y": Y, "Lsrc": lsrc, "rd": rdst}
            for k in CONDS:
                row[f"{k}_d"], row[f"{k}_o"] = c[k]
            rows.append(row)
    E = pd.DataFrame(rows)
    log(f"[逐列] eligible 股-月 {len(E):,}｜量測日 {E['T'].nunique()}（{E['T'].min().date()}～{E['T'].max().date()}）")
    return cal, E, {**fstat, **astat}


def flags(E, s, drop=None, age=True):
    cs = [c for c in SETS[s] if c != drop]
    d = np.ones(len(E), bool); o = np.ones(len(E), bool)
    for c in cs:
        d &= E[f"{c}_d"].to_numpy(bool); o &= E[f"{c}_o"].to_numpy(bool)
    if age:
        o &= E["age5"].to_numpy(bool)
    return d, o


def gate(E, log):
    per = []
    for T, g in E.groupby("T", sort=True):
        den = g["age5"].to_numpy(bool)
        r = {"T": str(T.date()), "eligible": len(g), "denom_5y": int(den.sum()), "excl_lt5y": int((~den).sum())}
        for s in SETS:
            d, o = flags(g, s)
            r[f"cov_{s}"] = float(d[den].mean()) if den.any() else np.nan
            r[f"cand_{s}"] = int(o.sum())
            r[f"cand_{s}_L2"] = int(flags(g, s, age=False)[1].sum())
        g5 = g[den]
        r["rd_blank_5y"] = int((g5["rd"] == "rd_blank").sum()); r["rd_norow_5y"] = int((g5["rd"] == "no_row").sum())
        m123 = g5["M1_o"] & g5["M2_o"] & g5["M3_o"]
        r["M123_only_rd_block"] = int((m123 & ~g5["M4_o"]).sum())
        r["Lsrc_dl_rows"] = int((g["Lsrc"] == "dl").sum())
        r["ts_share_5y"] = float((g5["Lsrc"] == "ts").mean()) if len(g5) else np.nan
        for s in SETS:
            o = flags(g, s)[1]
            r[f"cand_{s}_Lsrc_dl"] = int((o & (g["Lsrc"] == "dl").to_numpy()).sum())
        per.append(r)
    P = pd.DataFrame(per)
    ok = (P[[f"cov_{s}" for s in SETS]] >= COV_TH).all(axis=1)
    first = P.loc[ok, "T"].iloc[0] if ok.any() else None
    okts = P["ts_share_5y"] >= COV_TH
    first_ts = P.loc[okts, "T"].iloc[0] if okts.any() else None
    start = max(W0_MAIN, first, first_ts) if (first and first_ts) else None
    later_below = P.loc[(P["T"] >= (start or "9999")) & ~(ok & okts), "T"].tolist()
    log(f"[閘] 三套可算比例首次都 ≥ 90%：{first}｜最新一季有 A0 時戳的比例首次 ≥ 90%：{first_ts} ⇒ 起點 {start}｜之後跌破 {later_below}")
    return P, start, later_below, first, first_ts


# ═════════════ 價格與引擎 ═════════════
def _init(cal):
    _G["cal"] = cal


def load_px(args):
    s, mk = args
    cal = _G["cal"]
    st = D.load_stock(s, mk, cal)
    if st is None:
        return s, None
    c = st.df["close"].to_numpy(float)
    tb = TR.one(s, cal)
    return s, {"c": pd.Series(c).ffill().to_numpy(float), "o": st.df["open"].to_numpy(float), "valid": np.isfinite(c),
               "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "dn_c": tb["dn_c"]}


def make_sig(cand, H, closes, opens, n, w1):
    """cand ＝ {t（量測日位置）: [sid…]} ⇒ simulate_mtm 訊號表。"""
    rows = []
    for t, ss in cand.items():
        e = t + 1
        if e > w1:
            continue
        x = min(e + H - 1, n - 1)
        for s in ss:
            o_ = opens[s][e]; c_ = closes[s][x]
            if np.isfinite(o_) and o_ > 0 and np.isfinite(c_):
                rows.append((s, e, x, c_ / o_ - 1.0))
    df = pd.DataFrame(rows, columns=["sid", "entry_pos", f"xpos_H{H}", f"g_H{H}"])
    return df.sort_values(["entry_pos", "sid"]).reset_index(drop=True)


def run_eng(sig, H, rng, N=NSLOT, cost=COST, opens=None, audit=None, **kw):
    G = _G
    R.COST = cost
    try:
        return R.simulate_mtm(sig, f"H{H}", N, rng, G["closes"], opens if opens is not None else G["opens"], G["n"], return_equity=True, pick=None,
                              d_max=None, queue_days=0, cash_mode="zero", tradable=G["trad"], delist=G["dl"], stop_force=G["SF"], audit=audit, **kw)
    finally:
        R.COST = COST


def wstat(eq):
    c, m = R13.window_stats(np.asarray(eq, float), 0, _G["n"], _G["w0"], _G["w1"] + 1)
    return float(c), float(m)


def label(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


def _job_seed(args):
    key, H, r = args
    sig, kw, cost, ops = _G["SIGS"][(key, H)]
    o = run_eng(sig, H, np.random.default_rng(1000 + r), cost=cost, opens=ops, **kw)
    c, m = wstat(o["equity"])
    return key, H, r, c, m, (np.asarray(o["equity"], np.float32) if _G.get("keep_eq") and key in _G["keep_eq"] else None), o.get("slot_use")


def _job_fake(args):
    si, s, H, r = args
    G = _G
    rng = np.random.default_rng([20261004, si, H, r])
    cand = {}
    for t, k in G["KCNT"][s].items():
        pool = G["ELIG"][t]
        cand[t] = list(rng.choice(pool, size=min(k, len(pool)), replace=False)) if k > 0 else []
    sig = make_sig(cand, H, G["closes"], G["opens"], G["n"], G["w1"])
    o = run_eng(sig, H, np.random.default_rng([20261005, si, H, r]))
    c, m = wstat(o["equity"])
    return s, H, r, c, m


def _job_alt(args):
    al, s, H, r = args
    G = _G
    o = run_eng(G["ALTSIG"][(al, s, H)], H, np.random.default_rng(1000 + r))
    wa = int(G["cal"].searchsorted(pd.Timestamp(al)))
    c, m = R13.window_stats(np.asarray(o["equity"], float), 0, G["n"], wa, G["w1"] + 1)
    return al, s, H, r, float(c), float(m)


def monthly_ci(eq, bench, cal, w0, w1):
    idx = pd.DatetimeIndex(cal[w0:w1 + 1])
    a = pd.Series(np.asarray(eq[w0:w1 + 1], float), idx).resample("ME").last()
    b = pd.Series(np.asarray(bench[w0:w1 + 1], float), idx).resample("ME").last()
    a0 = pd.concat([pd.Series([eq[w0]], [idx[0] - pd.Timedelta(days=1)]), a]); b0 = pd.concat([pd.Series([bench[w0]], [idx[0] - pd.Timedelta(days=1)]), b])
    x = (a0.pct_change() - b0.pct_change()).dropna().to_numpy()
    m, sd, k = float(np.mean(x)), float(np.std(x, ddof=1)), len(x)
    from math import sqrt
    tq = 1.96 if k > 60 else {12: 2.20, 24: 2.07, 36: 2.03, 48: 2.01, 60: 2.00}.get(min((12, 24, 36, 48, 60), key=lambda z: abs(z - k)), 2.0)
    return {"月數": k, "月超額平均": m, "lo": m - tq * sd / sqrt(k), "hi": m + tq * sd / sqrt(k)}


def yearly_1m(eq, cal, w0, w1):
    out = {}
    yrs = sorted(set(cal[w0:w1 + 1].year))
    for y in yrs:
        ix = [i for i in range(w0, w1 + 1) if cal[i].year == y]
        a, b = ix[0], ix[-1]
        base = eq[a - 1] if a - 1 >= w0 else eq[w0]
        out[int(y)] = float(1e6 * eq[b] / base)
    return out


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--seeds", type=int, default=200); ap.add_argument("--fake", type=int, default=1000)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        return check()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchMaster4（PREREG大師三套 seq4，A0 定案）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TAGT} =====")
    S = {"登錄": "PREREG大師三套 seq4 sha 48365ba96fb2b1a9；裁定 seq210、214、231、241、242、245、275", "讀法寫死": TAGT,
         "資料": {"財報與可用日與本益比": f"main {MS_SHA}（~/msdata，唯讀）", "價格": f"edc6f8002f（{H2.H2D}）", "面板": PANEL}}
    cal, E, st = build_rows(log)
    S["資料閘"] = st
    E.to_csv(os.path.join(OUT, "rows.csv.gz"), index=False)
    P, start, below, first_cov, first_ts = gate(E, log)
    P.to_csv(os.path.join(OUT, "gate_by_month.csv"), index=False)
    n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(start))); w1 = int(cal.searchsorted(pd.Timestamp(W1_MAIN), side="right") - 1)
    yrs = (w1 - w0 + 1) / 245
    S["起點"] = {"三套可算比例首次都 ≥ 90%": first_cov, "最新一季有 A0 時戳比例首次 ≥ 90%（執行者補）": first_ts, "起點": start,
               "之後跌破 90% 的量測日": below, "窗": [str(cal[w0].date()), str(cal[w1].date())], "窗年數": yrs}
    ALT = sorted({first_cov, "2020-04-01"} - {start})
    Pw = P[P["T"] >= start]
    S["候選數分佈（窗內量測日）"] = {s: {"中位": float(Pw[f"cand_{s}"].median()), "p10": float(Pw[f"cand_{s}"].quantile(.1)), "p90": float(Pw[f"cand_{s}"].quantile(.9)),
                                   "候選＜10 的量測日比例": float((Pw[f"cand_{s}"] < 10).mean()), "候選＝0 的量測日": int((Pw[f"cand_{s}"] == 0).sum()),
                                   "可算比例最低": float(Pw[f"cov_{s}"].min()), "L2 候選中位": float(Pw[f"cand_{s}_L2"].median()),
                                   "候選中最新一季是缺時戳補位的筆數": int(Pw[f"cand_{s}_Lsrc_dl"].sum())} for s in SETS}
    S["每月被擋（窗內中位）"] = {"上市不滿 5 年": float(Pw["excl_lt5y"].median()), "研發空白": float(Pw["rd_blank_5y"].median()),
                          "XBRL 沒這家": float(Pw["rd_norow_5y"].median()), "M1～M3 都符合只卡研發": float(Pw["M123_only_rd_block"].median()),
                          "最新一季是缺時戳補位的 eligible 列（合計）": int(Pw["Lsrc_dl_rows"].sum())}
    log(f"[候選] {json.dumps(S['候選數分佈（窗內量測日）'], ensure_ascii=False)}")
    # ── 價格
    Ew = E[E["T"] >= pd.Timestamp(start)]
    Eall = E[E["T"] >= pd.Timestamp(min([start] + ALT))]
    sids = sorted(set(Eall["sid"]))
    mkd = dict(zip(Eall["sid"], Eall["market"]))
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        PX = dict(pool.map(load_px, [(s, mkd[s]) for s in sids], chunksize=16))
    PX = {s: v for s, v in PX.items() if v is not None}
    closes = {s: v["c"] for s, v in PX.items()}; opens = {s: v["o"] for s, v in PX.items()}
    trad = {s: {k: v[k] for k in ("trd", "up_o", "dn_o", "dn_c")} for s, v in PX.items()}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in PX.items()}, cal, official=TR.load_official())
    SF = R.stop_force_days({s: v["valid"] for s, v in PX.items()}, w1)
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    _G.update(cal=cal, n=n, w0=w0, w1=w1, closes=closes, opens=opens, trad=trad, dl=dl, SF=SF)
    m0a = int(cal.searchsorted(pd.Timestamp(W0_MAIN)))
    ca, ma = R13.window_stats(bench, 0, n, m0a, w1 + 1)
    S["閘"] = {"0050 主窗錨逐位元": repr(float(ca)) == repr(ANCHOR[0]) and repr(float(ma)) == repr(ANCHOR[1])}
    if not S["閘"]["0050 主窗錨逐位元"]:
        raise SystemExit("⛔ 0050 錨")
    c0, m0 = R13.window_stats(bench, 0, n, w0, w1 + 1); c0, m0 = float(c0), float(m0)
    S["0050同窗"] = {"年化": c0, "回落": m0, "比值": c0 / abs(m0)}
    log(f"[0050 同窗 {cal[w0].date()}～{cal[w1].date()}] {c0:+.2%}／{m0:+.2%}（{c0 / abs(m0):.3f}）｜停止交易 {len(SF)}")
    # ── 候選表
    CAND = {}
    for key, s, drop, age in [(s, s, None, True) for s in SETS] + [(f"{s}-{c}", s, c, True) for s in SETS for c in SETS[s]] + [(f"{s}_L2", s, None, False) for s in SETS]:
        d, o = flags(Ew, s, drop=drop, age=age)
        sub = Ew[o]
        CAND[key] = {int(t): sorted(g["sid"]) for t, g in sub.groupby("t")}
        for t in Ew["t"].unique():
            CAND[key].setdefault(int(t), [])
    # ── 主 9 格＋描述臂（200 顆）
    sigs = {}
    for key in CAND:
        for H in HS:
            sigs[(key, H)] = (make_sig(CAND[key], H, closes, opens, n, w1), {}, COST, None)
    # 現實版（researchSlip 定義）
    from backtest import researchSlip as SL
    X = {}
    for s in sids:
        X[s] = SL.stock_extra(s, mkd[s], cal, n) if s in PX else None
    for s_ in SETS:
        for H in HS:
            sg = sigs[(s_, H)][0].copy()
            e_ = sg["entry_pos"].to_numpy(int); x_ = sg[f"xpos_H{H}"].to_numpy(int); g_ = sg[f"g_H{H}"].to_numpy(float).copy()
            g_ = np.array([X[s]["avg"][xx] / X[s]["avg"][ee] - 1.0 if (np.isfinite(X[s]["avg"][ee]) and X[s]["avg"][ee] > 0 and np.isfinite(X[s]["avg"][xx])) else gg
                           for s, ee, xx, gg in zip(sg["sid"], e_, x_, g_)])
            Qc = 500_000 / NSLOT
            ie = np.nan_to_num(np.array([X[s]["sig20"][ee] * math.sqrt(Qc / X[s]["adv20"][ee]) if (np.isfinite(X[s]["adv20"][ee]) and X[s]["adv20"][ee] > 0) else 0.0 for s, ee in zip(sg["sid"], e_)]))
            ix = np.nan_to_num(np.array([X[s]["sig20"][xx] * math.sqrt(Qc / X[s]["adv20"][xx]) if (np.isfinite(X[s]["adv20"][xx]) and X[s]["adv20"][xx] > 0) else 0.0 for s, xx in zip(sg["sid"], x_)]))
            sg[f"g_H{H}"] = (1 + g_) * (1 - np.minimum(ix, 0.99)) / (1 + ie) - 1.0
            ops = {s: (X[s]["avg"] if X.get(s) is not None else opens[s]) for s in opens}
            sigs[(f"{s_}_real", H)] = (sg, {}, COST + 2 * 0.003, ops)
    _G["SIGS"] = sigs; _G["keep_eq"] = set(SETS)
    jobs = [(k, H, r) for (k, H) in sigs for r in range(a.seeds)]
    tt = time.time()
    with Pool(a.procs, initializer=_G.update, initargs=({},)) as pool:
        res = pool.map(_job_seed, jobs, chunksize=25)
    log(f"[引擎] {len(jobs):,} 次｜{time.time() - tt:.0f}s")
    SEEDS = pd.DataFrame([(k, H, r, c, m, su) for k, H, r, c, m, _, su in res], columns=["arm", "H", "r", "cagr", "mdd", "slot_use"])
    SEEDS.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    EQS = {(k, H, r): e for k, H, r, c, m, e, _ in res if e is not None}
    # ── 判定 9 格
    cells = []
    for s in SETS:
        for H in HS:
            x = SEEDS[(SEEDS["arm"] == s) & (SEEDS["H"] == H)]
            cm, mm = float(x["cagr"].median()), float(x["mdd"].median())
            cells.append({"套": s, "名": SET_NAME[s], "H": H, "年化中位": cm, "回落中位": mm, "比值": cm / abs(mm), "標籤": label(cm, mm, c0, m0),
                          "年化 p10": float(x["cagr"].quantile(.1)), "年化 p90": float(x["cagr"].quantile(.9)), "槽位使用率中位": float(x["slot_use"].median()),
                          "200顆中合格比例": float(np.mean([label(c, m, c0, m0) == "合格" for c, m in zip(x["cagr"], x["mdd"])]))})
    C = pd.DataFrame(cells); C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    log("\n" + C[["名", "H", "年化中位", "回落中位", "比值", "標籤"]].to_string(index=False))
    # ── 假訊號 S0
    ELIG = {int(t): sorted(g["sid"]) for t, g in Ew.groupby("t")}
    KCNT = {s: {t: len(v) for t, v in CAND[s].items()} for s in SETS}
    _G.update(ELIG=ELIG, KCNT=KCNT)
    fj = [(si, s, H, r) for si, s in enumerate(SETS) for H in HS for r in range(a.fake)]
    tt = time.time()
    with Pool(a.procs, initializer=_G.update, initargs=({},)) as pool:
        fr = pool.map(_job_fake, fj, chunksize=25)
    FK = pd.DataFrame(fr, columns=["set", "H", "r", "cagr", "mdd"]); FK["label"] = [label(c, m, c0, m0) for c, m in zip(FK["cagr"], FK["mdd"])]
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
    log(f"[假訊號] {len(fj):,} 次｜{time.time() - tt:.0f}s")
    for c in cells:
        f = FK[(FK["set"] == c["套"]) & (FK["H"] == c["H"])]
        c["假訊號合格比例 p"] = float((f["label"] == "合格").mean()); c["假訊號年化中位"] = float(f["cagr"].median())
        c["假訊號年化 ≥ 本格的比例"] = float((f["cagr"] >= c["年化中位"]).mean())
    C = pd.DataFrame(cells); C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    S["判定9格"] = cells
    # ── 描述臂
    def armstat(k, H):
        x = SEEDS[(SEEDS["arm"] == k) & (SEEDS["H"] == H)]
        cm, mm = float(x["cagr"].median()), float(x["mdd"].median())
        return {"年化中位": cm, "回落中位": mm, "標籤": label(cm, mm, c0, m0)}
    S["描述_拿掉一條"] = {f"{s}-{c}（拿掉 {CNAME[c]}）": {f"H{H}": armstat(f"{s}-{c}", H) for H in HS} for s in SETS for c in SETS[s]}
    S["描述_L2不看上市年數"] = {s: {f"H{H}": armstat(f"{s}_L2", H) for H in HS} for s in SETS}
    S["描述_現實版"] = {s: {f"H{H}": armstat(f"{s}_real", H) for H in HS} for s in SETS}
    # 月分群、逐年 100 萬
    mci = {}; y1m = {}
    for s in SETS:
        for H in HS:
            x = SEEDS[(SEEDS["arm"] == s) & (SEEDS["H"] == H)].sort_values("cagr")
            rmed = int(x.iloc[len(x) // 2 - 1]["r"]) if len(x) % 2 == 0 else int(x.iloc[len(x) // 2]["r"])
            eq = EQS[(s, H, rmed)].astype(float)
            mci[f"{s}_H{H}"] = {"種子": rmed, **monthly_ci(eq, bench, cal, w0, w1)}
            ys = [yearly_1m(EQS[(s, H, r)].astype(float), cal, w0, w1) for r in range(a.seeds)]
            y1m[f"{s}_H{H}"] = {y: float(np.median([d[y] for d in ys])) for y in ys[0]}
    y1m["0050"] = yearly_1m(bench, cal, w0, w1)
    S["描述_月分群（年化第100顆）"] = mci; S["描述_逐年100萬期末（200顆中位）"] = y1m
    # 候選重疊
    ov = {}
    ks = list(SETS)
    for i, p_ in enumerate(ks):
        for q_ in ks[i + 1:]:
            js = []
            for t in CAND[p_]:
                A_, B_ = set(CAND[p_][t]), set(CAND[q_][t])
                if A_ | B_:
                    js.append(len(A_ & B_) / len(A_ | B_))
            ov[f"{p_}×{q_}"] = float(np.mean(js))
    S["描述_三套候選重疊（Jaccard，量測日平均）"] = ov
    # 混營飆 v1
    z = np.load("backtest/resultsYfMix13/eq_main.npz"); zw0, zw1 = int(z["w0"]), int(z["w1"])
    pos1 = pd.read_csv("backtest/resultsYfMix13/positions.csv.gz", dtype={"sid": str}); pos1 = pos1[pos1["cell"] == 1]
    mix = {}
    for s in SETS:
        for H in HS:
            outs = []
            for r in range(a.seeds):
                ea = EQS[(s, H, r)].astype(float)
                yfr = np.ones(n); yfr[zw0:zw1 + 1] = z["yf"][r]; yfr[zw1 + 1:] = z["yf"][r][-1]
                ra = ea[w0 + 1:w1 + 1] / ea[w0:w1] - 1; rb = yfr[w0 + 1:w1 + 1] / yfr[w0:w1] - 1
                va, vb = 0.5, 0.5; eqm = [1.0]
                for i, t in enumerate(range(w0 + 1, w1 + 1)):
                    va *= 1 + ra[i]; vb *= 1 + rb[i]
                    if cal[t].year != cal[t - 1].year:
                        tot = va + vb; mv = abs(va - tot / 2); tot -= mv * COST; va = vb = tot / 2
                    eqm.append(va + vb)
                em = np.ones(n); em[w0:w1 + 1] = eqm; em[w1 + 1:] = eqm[-1]
                cm_, mm_ = wstat(em)
                outs.append((cm_, mm_, float(np.corrcoef(ra, rb)[0, 1])))
            o_ = np.array(outs)
            mix[f"{s}_H{H}"] = {"混合年化中位": float(np.median(o_[:, 0])), "混合回落中位": float(np.median(o_[:, 1])), "日報酬相關中位": float(np.median(o_[:, 2])),
                                "標籤": label(float(np.median(o_[:, 0])), float(np.median(o_[:, 1])), c0, m0)}
    yfw = [wstat(np.r_[np.ones(zw0), z["yf"][r], np.full(n - zw1 - 1, z["yf"][r][-1])]) for r in range(a.seeds)]
    S["描述_混營飆v1 50／50"] = {"營飆v1同窗": {"年化中位": float(np.median([x[0] for x in yfw])), "回落中位": float(np.median([x[1] for x in yfw]))}, **mix}
    # 同時持有檔數（種子 0，套 H 主格對營飆種子 0）
    hold_ov = {}
    p1 = pos1[pos1["r"] == 0]; H1 = [set() for _ in range(n)]
    for sd_, tb_, ts_ in zip(p1["sid"], p1["t_buy"], p1["t_sell"]):
        for t in range(max(tb_, w0), min((n if ts_ < 0 else ts_), w1 + 1)):
            H1[t].add(sd_)
    for s in SETS:
        for H in HS:
            aud = []
            run_eng(sigs[(s, H)][0], H, np.random.default_rng(1000), audit=aud)
            hs = [set() for _ in range(n)]; cur = {}
            for ev in sorted(aud, key=lambda d: (d["t"], 0 if d["side"] == "sell" else 1)):
                if ev["side"] == "buy":
                    cur[ev["sid"]] = ev["t"]
                else:
                    tb_ = cur.pop(ev["sid"], None)
                    if tb_ is not None:
                        for t in range(tb_, ev["t"]):
                            hs[t].add(ev["sid"])
            for sd_, tb_ in cur.items():
                for t in range(tb_, w1 + 1):
                    hs[t].add(sd_)
            both = [len(hs[t] & H1[t]) for t in range(w0, w1 + 1)]
            hold_ov[f"{s}_H{H}"] = {"同時持有檔數平均": float(np.mean(both)), "有同時持有的日子比例": float(np.mean([b > 0 for b in both]))}
    S["描述_與營飆v1同時持有（種子0）"] = hold_ov
    # ── 起點敏感度（描述）：可算比例公式起點（最新一季多靠法定期限補位）、裁定 0026 估的 2020-04
    altsig = {}
    for al in ALT:
        Ea = E[E["T"] >= pd.Timestamp(al)]
        for s in SETS:
            o = flags(Ea, s)[1]
            cand = {int(t): sorted(g["sid"]) for t, g in Ea[o].groupby("t")}
            for H in HS:
                altsig[(al, s, H)] = make_sig(cand, H, closes, opens, n, w1)
    _G.update(ALTSIG=altsig)
    with Pool(a.procs, initializer=_G.update, initargs=({},)) as pool:
        ar = pool.map(_job_alt, [(al, s, H, r) for al in ALT for s in SETS for H in HS for r in range(a.seeds)], chunksize=25)
    AR = pd.DataFrame(ar, columns=["alt", "set", "H", "r", "cagr", "mdd"])
    altd = {}
    for al in ALT:
        wa = int(cal.searchsorted(pd.Timestamp(al)))
        ca_, ma_ = R13.window_stats(bench, 0, n, wa, w1 + 1); ca_, ma_ = float(ca_), float(ma_)
        dd = {"0050同窗": {"年化": ca_, "回落": ma_, "比值": ca_ / abs(ma_)}}
        for s in SETS:
            for H in HS:
                x = AR[(AR["alt"] == al) & (AR["set"] == s) & (AR["H"] == H)]
                cm_, mm_ = float(x["cagr"].median()), float(x["mdd"].median())
                dd[f"{s}_H{H}"] = {"年化中位": cm_, "回落中位": mm_, "標籤": label(cm_, mm_, ca_, ma_)}
        altd[al] = dd
    S["描述_起點敏感度"] = altd
    # ── 合格／另列 ⇒ 固定跟進出場敏感度（seq242 ②）
    sens = {}
    for c in cells:
        if c["標籤"] in ("合格", "另列"):
            k, H = c["套"], c["H"]; sg = sigs[(k, H)][0]
            vs = {"停損 −10%": dict(stop=("fix", 0.10)), "停損 −20%": dict(stop=("fix", 0.20)),
                  "停利 +30% 賣半": dict(trim_rule={"kind": "gain", "x": 0.30, "frac": 0.5}), "停利 +50% 賣半": dict(trim_rule={"kind": "gain", "x": 0.50, "frac": 0.5}),
                  "檔數 5": dict(N=5), "檔數 20": dict(N=20)}
            d_ = {}
            for vn, kw in vs.items():
                cs_, ms_ = [], []
                for r in range(a.seeds):
                    o = run_eng(sg, H, np.random.default_rng(1000 + r), **kw); cc, mm = wstat(o["equity"]); cs_.append(cc); ms_.append(mm)
                cm_, mm_ = float(np.median(cs_)), float(np.median(ms_))
                d_[vn] = {"年化中位": cm_, "回落中位": mm_, "標籤": label(cm_, mm_, c0, m0)}
            d_["2ATR 停損、時停 R0-40"] = "引擎無對應開關，本輪未做（執行者補）"
            sens[f"{k}_H{H}"] = d_
    S["出場敏感度（seq242 ②，描述）"] = sens if sens else "9 格皆不合格 ⇒ 不跟進（seq242 ② 只在合格／另列時跑）"
    S["先驗（登錄 §七、§九③）"] = {"3 套都不是合格": all(c["標籤"] != "合格" for c in cells), "喜偉常常湊不滿 10 檔": S["候選數分佈（窗內量測日）"]["X"]["候選＜10 的量測日比例"] > 0.3,
                              "H 三值中年化最高的是 120": {s: max(HS, key=lambda H: [c for c in cells if c["套"] == s and c["H"] == H][0]["年化中位"]) for s in SETS}}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


# ═════════════ 抽樣查核（⛔ 不呼叫上面的 Fin／load_avail／make_sig／gate；自己從原始 CSV 重算）═════════════
def check():
    out = {"時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    E = pd.read_csv(os.path.join(OUT, "rows.csv.gz"), dtype={"sid": str}, parse_dates=["T"])
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    cal = D.load_calendar(); n = len(cal)
    rng = np.random.default_rng(7)
    # ① 可用日：抽 300 個 (sid, 年, 季) 直接讀 filing_dates 原檔
    fd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype=str)
    fin = {}
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv"))):
        df = pd.read_csv(f, dtype=str)
        for r in df.itertuples(index=False):
            fin[(r.stock_id, r.period)] = r._asdict()
    smp = E[E["L"].notna()].sample(400, random_state=11)
    bad_av = []

    fdg = {k: g for k, g in fd.groupby("stock_id")}
    calv = cal.values
    finq = {}
    for (s_, p_) in fin:
        finq.setdefault(s_, set()).add(int(p_[:4]) * 4 + int(p_[-1]) - 1)

    def avail_pos(sid, y, q):
        g0 = fdg.get(sid)
        rows = g0[(g0["year"] == str(y)) & (g0["season"] == str(q))] if g0 is not None else fd.iloc[0:0]
        if len(rows):
            d0 = min(pd.Timestamp(x) for x in rows["uploaded_at"]).normalize()
            return int(np.searchsorted(calv, np.datetime64(d0), side="right"))
        dd = pd.Timestamp(f"{y + 1}-03-31") if q == 4 else pd.Timestamp(f"{y}-{('05-15', '08-14', '11-14')[q - 1]}")
        return int(np.searchsorted(calv, np.datetime64(dd), side="right"))
    # ② 逐列條件重算
    def num(x):
        try:
            v = float(x)
            return v if np.isfinite(v) else np.nan
        except (TypeError, ValueError):
            return np.nan

    def get(sid, y, q, col):
        r = fin.get((sid, f"{y}Q{q}"))
        return np.nan if r is None else num(r[col])

    def ni(sid, y, q):
        a_ = get(sid, y, q, "nip_ytd")
        return a_ if np.isfinite(a_) else get(sid, y, q, "ni_ytd")

    def eqv(sid, y, q):
        a_ = get(sid, y, q, "equity_parent")
        return a_ if np.isfinite(a_) else get(sid, y, q, "equity_total")
    rdd = {}
    for f in sorted(glob.glob(os.path.join(FD, "mops", "rd_hist", "*.csv"))):
        df = pd.read_csv(f, dtype=str)
        for r in df.itertuples(index=False):
            rdd[(r.stock_id, r.period)] = (num(r.rd_ytd), num(r.rev_ytd))
    bad = []
    for r in smp.itertuples(index=False):
        sid, t = r.sid, int(r.t)
        # 最新可用一季：掃該檔所有季
        qs = sorted(finq.get(sid, set()))
        okq = [p for p in qs if avail_pos(sid, p // 4, p % 4 + 1) <= t]
        L = max(okq) if okq else None; q4 = [p for p in okq if p % 4 == 3]; Y = max(q4) // 4 if q4 else None
        if L != (int(r.L) if pd.notna(r.L) else None) or Y != (int(r.Y) if pd.notna(r.Y) else None):
            bad_av.append((sid, str(r.T.date()), L, r.L, Y, r.Y)); continue
        mine = {}
        # M1
        ps = list(range(L - 11, L + 1))

        def sq(p, col):
            y_, q_ = divmod(p, 4)
            a_ = get(sid, y_, q_ + 1, col)
            if q_ == 0:
                return a_
            return a_ - get(sid, y_, q_, col)
        have = all((sid, f"{p // 4}Q{p % 4 + 1}") in fin for p in ps) and all((sid, f"{(p - 1) // 4}Q{(p - 1) % 4 + 1}") in fin for p in ps if p % 4)
        if have:
            rv = [sq(p, "rev_ytd") for p in ps]; oi = [sq(p, "opi_ytd") for p in ps]
            if all(np.isfinite(rv + oi)):
                mg = [o / v if v > 0 else np.nan for o, v in zip(oi, rv)]
                mine["M1"] = (True, bool(np.all(np.isfinite(mg)) and np.mean(mg) > 0.1))
            else:
                mine["M1"] = (False, False)
        else:
            mine["M1"] = (False, False)
        if Y is None:
            for c in ("M2", "O1", "X2", "M3", "O3"):
                mine[c] = (False, False)
        else:
            def avg5(fn, fd_, th, gt):
                a_ = [fn(sid, y, 4) for y in range(Y - 4, Y + 1)]; b_ = [fd_(sid, y, 4) for y in range(Y - 4, Y + 1)]
                if not all(np.isfinite(a_ + b_)):
                    return (False, False)
                v_ = [x / z if z > 0 else np.nan for x, z in zip(a_, b_)]
                if not all(np.isfinite(v_)):
                    return (True, False)
                return (True, bool(np.mean(v_) > th) if gt else bool(np.mean(v_) < th))
            mine["M2"] = avg5(ni, eqv, 0.08, True)
            mine["O1"] = avg5(ni, lambda s_, y, q: get(s_, y, q, "assets"), 0.08, True)
            mine["X2"] = avg5(lambda s_, y, q: get(s_, y, q, "liabilities"), lambda s_, y, q: get(s_, y, q, "assets"), 0.30, False)
            for c, col, th in (("M3", "rev_ytd", 0.1), ("O3", "eps_ytd", 0.3)):
                x = [get(sid, y, 4, col) for y in range(Y - 3, Y + 1)]
                if all(np.isfinite(x)):
                    g = [x[k] / x[k - 1] - 1 if x[k - 1] > 0 else np.nan for k in (1, 2, 3)]
                    mine[c] = (True, bool(np.all(np.isfinite(g)) and np.mean(g) > th))
                else:
                    mine[c] = (False, False)
        y_, q_ = divmod(L, 4)
        keys = [f"{y_}Q4"] if q_ == 3 else [f"{y_}Q{q_ + 1}", f"{y_ - 1}Q4", f"{y_ - 1}Q{q_ + 1}"]
        sg = [1] if q_ == 3 else [1, 1, -1]
        if any((sid, k) not in rdd for k in keys):
            mine["M4"] = (True, False)
        else:
            a_ = [rdd[(sid, k)][0] for k in keys]; b_ = [rdd[(sid, k)][1] for k in keys]
            if not all(np.isfinite(a_)):
                mine["M4"] = (True, False)
            elif not all(np.isfinite(b_)):
                mine["M4"] = (False, False)
            else:
                nn = sum(u * x for u, x in zip(sg, a_)); dd = sum(u * x for u, x in zip(sg, b_))
                mine["M4"] = (True, bool(dd > 0 and nn / dd > 0.05))
        pv = None
        for sub in ("per", "otcper"):
            p_ = os.path.join(FD, "universe", sub, f"{cal[t - 1].date()}.csv")
            if os.path.exists(p_) and pv is None:
                df = pd.read_csv(p_, dtype=str)
                hit = df[df["stock_id"].str.strip() == sid]
                if len(hit):
                    pv = num(hit.iloc[0]["per"])
        mine["PE"] = (False, False) if pv is None else (True, bool(np.isfinite(pv) and 0 < pv < 15))
        for c in CONDS:
            if (bool(getattr(r, f"{c}_d")), bool(getattr(r, f"{c}_o"))) != mine[c]:
                bad.append((sid, str(r.T.date()), c, mine[c]))
    out["① 可用日與最新一季（抽 400 列）"] = {"不同": len(bad_av), "例": bad_av[:5]}
    out["② 八條件逐列重算（同 400 列）"] = {"不同": len(bad), "例": bad[:5]}
    # ③ 組合：每套 H60 種子 0 用 audit 自己重算逐日權益（只用原始價格＋成交紀錄）
    import importlib
    M = importlib.import_module("backtest.researchMaster4")
    w0 = int(cal.searchsorted(pd.Timestamp(S["起點"]["窗"][0]))); w1 = int(cal.searchsorted(pd.Timestamp(S["起點"]["窗"][1])))
    res3 = {}
    for s in SETS:
        d, o = M.flags(E[E["T"] >= pd.Timestamp(S["起點"]["窗"][0])], s)
        sub = E[E["T"] >= pd.Timestamp(S["起點"]["窗"][0])][o]
        cand = {int(t): sorted(g["sid"]) for t, g in sub.groupby("t")}
        sids = sorted({x for v in cand.values() for x in v})
        stk = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"]
        PX = {}
        for x in sids:
            st = D.load_stock(x, stk.get(x, "twse"), cal)
            PX[x] = (pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(), st.df["open"].to_numpy(float), np.isfinite(st.df["close"].to_numpy(float)))
        closes = {x: v[0] for x, v in PX.items()}; opens = {x: v[1] for x, v in PX.items()}
        trad = {x: TR.one(x, cal) for x in sids}
        dl = TR.delist_status({x: {"trd": trad[x]["trd"]} for x in sids}, cal, official=TR.load_official())
        SF = R.stop_force_days({x: v[2] for x, v in PX.items()}, w1)
        rows = []
        for t, ss in cand.items():
            e = t + 1
            if e > w1:
                continue
            x_ = min(e + 59, n - 1)
            for x in ss:
                if np.isfinite(opens[x][e]) and opens[x][e] > 0 and np.isfinite(closes[x][x_]):
                    rows.append((x, e, x_, closes[x][x_] / opens[x][e] - 1))
        sig = pd.DataFrame(rows, columns=["sid", "entry_pos", "xpos_H60", "g_H60"]).sort_values(["entry_pos", "sid"]).reset_index(drop=True)
        aud = []
        R.COST = COST
        o = R.simulate_mtm(sig, "H60", NSLOT, np.random.default_rng(1000), closes, opens, n, return_equity=True, pick=None, d_max=None, queue_days=0,
                           cash_mode="zero", tradable={x: {k: trad[x][k] for k in ("trd", "up_o", "dn_o", "dn_c")} for x in sids}, delist=dl, stop_force=SF, audit=aud)
        eq = np.asarray(o["equity"], float)
        # 自算：現金＋持股市值
        cash = 1.0; pos = {}; my = np.full(n, np.nan); ev = {}
        for a_ in aud:
            ev.setdefault(a_["t"], []).append(a_)
        bad_px = 0
        for t in range(n):
            for a_ in ev.get(t, []):
                if a_["side"] == "sell":
                    amt, ep = pos.pop(a_["sid"])
                    cash += a_["amt"] - a_["cost"]
                else:
                    if a_["px"] != opens[a_["sid"]][t]:
                        bad_px += 1
                    pos[a_["sid"]] = (a_["amt"], a_["px"]); cash -= a_["amt"]
            my[t] = cash + sum(amt * closes[x][t] / ep for x, (amt, ep) in pos.items())
        lo = int(o["first"]); hi = int(min(o["end"], w1 + 1))
        dmax = float(np.nanmax(np.abs(my[lo:hi] - eq[lo:hi])))
        s200 = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"))
        rec = s200[(s200["arm"] == s) & (s200["H"] == 60) & (s200["r"] == 0)].iloc[0]
        c_, m_ = R13.window_stats(eq, 0, n, w0, w1 + 1)
        res3[s] = {"成交筆數": len(aud), "買價≠當日開盤": bad_px, "自算權益最大差": dmax, "與 seeds.csv 種子0 年化差": abs(float(c_) - rec["cagr"])}
    out["③ 組合逐筆（H60 種子 0）"] = res3
    ok = (len(bad_av) == 0 and len(bad) == 0 and all(v["買價≠當日開盤"] == 0 and v["自算權益最大差"] < 1e-9 and v["與 seeds.csv 種子0 年化差"] < 1e-12 for v in res3.values()))
    out["結論"] = "✅ 全過（0 不同）" if ok else "⛔ 有不同"
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

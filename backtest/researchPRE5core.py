# -*- coding: utf-8 -*-
"""seq323／seq324 四件新登錄（個股趨勢全多、好營收股價已認同、財報前季營收前段、單季EPS季增）＋口徑件的【共用核心】——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議。

⭐ 讀法寫死時間：2026-10-10 23:37（台北）；寫死前 ⛔ 沒算任何本批數字（只看過登錄全文 seq3／seq2、裁定 seq323／seq324、情報 #10／#14／#15／#17／#21／#24 全文、
   既有程式與資料格式）。四件各自的讀法在各自檔頭（T／V／P／E 標），這裡是共同讀法（C 標）。

═══ 共同讀法（C 標；登錄沒寫清楚、執行者補的都在這裡）═══
 C1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ 登錄報頭 sha 才跑（信箱只讀）
 C2 版面：主段 ＝ rerun17 快照 H2D（edc6f8002f；日曆 2015-01-05～2026-09-24）；早年段 ＝ ~/earlydata/eotc_f65bb03e11/otc/data（上市＋上櫃；
    日曆 2004-02-11～2014-12-31；⚠ 上櫃日 K 2007-07 起 ⇒ 2005～2007-06 早年母體實際只有上市，照報）
    股票 ＝ UG.gate3（GATE_V2 開：UG.set_gate_v2(True)）∩ 四碼、首碼 1～9、非 91xx（PRE.okcode）；⭐ 含已下市；價格 ＝ D.load_stock（還原），收盤 ffill
 C3 母體（決策日 d ＝ 進場日 e 的前一個交易日，用 d 收盤以前的資料）：d 有 K 棒 ∧ UG.pit_valid(d) ∧ amt20(d) ≥ 5,000 萬
    amt20 ＝ 含 d 的最近 20 根有效 K 棒原始成交金額（元）平均（不足 20 根 ⇒ 不在母體）
    排除金融與生技（好營收股價已認同、財報前季營收前段）：產業 ＝ PRE.PIT（industry_pit，pit 版）在 d 的類別；「金融保險」、「生技醫療業」剔
      （早年合併類「化學生技醫療」分不開 ⇒ 不剔，筆數照報）；⚠ 產業分類層 ＝ 上市櫃官方產業別（單層；industry_pit）
    R1 排名版（描述；台股 1009-1542 §三 R1）：d 當天「四碼普通股 ∧ 有 K 棒 ∧ pit_valid（∧ 同件的產業排除）」依 amt20 由大到小前 X%；
      X ＝ 2016-01-04（2016-01 第一個交易日）5,000 萬母體檔數 ÷ 同日上述全市場檔數（固定；早年段沿用同一個 X）
 C4 進場：e 開盤（還原）；base 版 e 沒有有效開盤 ⇒ 該筆不進（筆數照報）；同一檔已持有 ⇒ 不重買（引擎 held）
 C5 出場：「開盤賣」型 ⇒ 排定日 x 起第一個有效開盤；「收盤賣」型 ⇒ 排定日 y 的收盤（y 沒有 K 棒 ⇒ ffill 收盤，筆數照報）
    到資料尾還沒出場 ⇒ 未完：xpos ＝ 墊檔日（日曆位置 n，價格墊一根）、以最後收盤計值、不賣（只影響窗外；窗尾持有照報）
 C6 引擎 research11.simulate_mtm（rule "F"：sig 欄 xpos_F、g_F）：10 槽、slot ＝ 前一日權益 ÷ 10；抽籤 ＝ rng.permutation（default_rng(SEED0＋r)，SEED0 ＝ 20261010）；
    「大者先」＝ 引擎 pick 欄遞減（不抽籤 ⇒ 200 顆相同 ⇒ 只跑 r＝0）；停止交易強制出場：開（stop_force ＝ stop_force_days(K 棒, 窗尾)）；
    成本 0.585%／來回（引擎出場一次扣）
    現實版（researchSlip「現實版」逐字，N＝10）：C1 每邊 ＋0.3%（引擎成本 0.585%＋0.6%）；C2 單邊衝擊 σ20 × √(5 萬 ÷ ADV20)（σ20、ADV20 截至前一根；
      50 萬 ÷ 10 檔）；C3 一字漲停買不到（名額持現金、不遞補）、一字跌停賣不掉（延到第一個賣得掉的日子）、停牌買不到；C4 進出價 ＝ 當日 (開＋高＋低＋收)÷4；
      C5 低消 20 元：A ＝ 2.5 萬 ⇒ 20 ÷ 25,000 ＝ 0.08% ＜ 0.1425% ⇒ 加 0（照報）；引擎 tradable（停牌、一字漲停）＋ delist（下市了結）
 C7 段：主窗 2017-03-02～2026-08-24（rerun17 win 讀法：進場日在窗內、窗首全現金）；探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24
    ＝ 同一條權益曲線切窗（rerun17.win_metrics；researchSlip 同法）；「資料尾」讀成主窗尾 2026-08-24（＝ 0050 錨、營量／營飆正式件同窗）；出場判斷用到 2026-09-24
    早年段（可判的件）：2005-02-01～2014-12-30（early 版面；MA240 暖機與 EARLY_X 同起點）；營收件另依覆蓋率（C14）縮
 C8 0050 ＝ RR.load_bench（各版面自己的 0050 還原收盤）同窗 RR.bench_row；主窗閘 ＝ rerun17 錨逐位元
    判準（使用者判準，對 0050 同窗）：合格 ＝ 年化中位 ＞ 0050 且 年化中位 ÷ |回落中位| ≥ 0050；另列 ＝ 只過年化；其餘不合格
 C9 退化（登錄必報「平均持股 ＜ 3 或現金 ＞ 30% ⇒ 退化，照報」）：⭐ 先算、先寫 degeneracy.json（附台北時間）再算任何報酬
    平均持股 ＝ 引擎 audit 逐日重建的持股檔數（段內逐日平均）；現金比例 ＝ 1 − 持股市值 ÷ 權益（段內逐日平均）；各取種子中位
    另報每個換股日候選數、訊號數逐年；挑格時探索段退化的格排除（登錄規則照報；⚠ 補讀法：全部格都退化 ⇒ 在全部格裡照同規則挑、標「全退化」）
 C10 挑格：探索段（0.585% 版）非退化格中，合格者取比值最大；沒有合格 ⇒ 取比值最大（照報它在探索段不合格）；平手 ⇒ 年化高、格序
     判定 ＝ 挑中格在確認段（與早年段，可判時）的標籤，兩段取較嚴；事後重切 ⇒ 兩段都合格也最多「暫定」、只進前瞻紀錄
     現實版同表並報標籤；兩版不同 ⇒ 照實寫
 C11 假訊號臂（挑中格）：每個進場日 e 的訊號列數 k_e 不變 ⇒ 改成「e 的決策日母體（同件的母體條件）裡隨機 k_e 檔」，持有天數從挑中格訊號（已完成者）的
     「進場 → 出場」日曆位置差等機率抽，到期日起第一個有效開盤賣；選法同挑中格（抽籤／大者先 ⇒ 假訊號列的鍵隨機）；第 r 抽配組合種子 r；
     抽樣 default_rng([20261011, r])；200 抽；p ＝ 假訊號年化 ≥ 挑中格年化中位 的比例
 C12 描述（⛔ 不判、不計 N；挑中格同進場）：固定持有 {20, 60, 120} 根（進場那根算第 1 根，第 H 根收盤出）；0050 在 200 日線上才買（決策日 d：0050 還原收盤 ＞ 含 d 的
     200 日均線）；R1 排名版（C3）；以上各 50 顆（種子 SEED0＋0～49）取中位
 C13 必報：等效獨立檔數（seq321 §五；1009-1542 ⑨ 的式子）：r＝0，每個換股日（當天有買進）收盤持股 N 檔，ρ ＝ 各檔前 60 個交易日收盤日報酬兩兩相關平均
       （共同有效報酬 ＜ 40 天或零變異的配對略過），N_eff ＝ N ÷ (1＋(N−1)ρ)；產業分類層 ＝ 上市櫃官方產業別單層（industry_pit），最大產業占幾檔、＞ 3 檔換股日占比
     持有天數分佈（進場到出場的交易日數，實際成交的筆，種子合計）、各出場原因次數（每顆平均）、窗尾仍持有（主窗尾仍抱的檔數，種子中位；持有天數）、
     一年內先跌 15%（進場後 250 個交易日內收盤先碰 ≤ 進場價 × 0.85，早於 ≥ × 1.15；只算觀察窗滿 250 的筆）、各年報酬（同一條權益、各曆年，種子中位）、最大產業
     ⚠ 0050 濾網的角色（seq321 §五）：「擋長空頭、不是急跌保護」
 C14 月營收：tw-stock-data origin/main（執行時 sha；PRE.ensure_data 的 git archive）data/early/revenue（2003～2014，上市＋上櫃＝自家彙總表）＋ data/mops/revenue_hist；
     欄「當月營收」「去年當月營收」「上月比較增減(%)」「去年同月增減(%)」；同 (代號, 期別) 重複 ⇒ 取最後一列（同 PRE.load_rev）
     可用日 ＝ research34.rebalance_dates（M ≤ 2025-12：M＋1 月 10 日之後第一個交易日；M ≥ 2026-01：15 日之後；嚴格大於）
     早年覆蓋：PRE.coverage（2005～2014 每月「當月與去年當月皆 ＞ 0 ÷ 當月有日 K」，上市）；年平均 ＜ 90% ⇒ 該年不可判定 ⇒ 早年判定窗從「其後各年都 ≥ 90%」的第一年起
     IFRS 窗（2013 期別：年增是 IFRS 對舊制）照舊標：早年段 2013 期別訊號占比照報，不剔
 C15 營量 v1、營飆 v1 對照：researchT1fix.build_ctx(True) 同一條路徑重跑（營飆 200 顆、營量 r＝0；stop_force 開），同窗三段；閘 ＝ resultsT1fix c1／c13 t1 逐位元
輸出：各件 backtest/results<件名>/；大檔 ~/pre5work/
"""
from __future__ import annotations

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
from backtest import universe_gate as UG                    # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import researchSlip as SL                     # noqa: E402
from backtest import tradability as TR                      # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402

UG.set_gate_v2(True)

TIME_CORE = "2026-10-10 23:37（台北）"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
WORK = os.path.expanduser("~/pre5work")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
SEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "主窗": ("2017-03-02", "2026-08-24")}
EARLY = ("2005-02-01", "2014-12-30")
SEED0 = 20261010
FSEED = 20261011
COST_B = R.COST
SLIP_S = 0.003
CAP_Q = 500_000 / 10
C5_M, C5_A = 20, 25_000
COST_R = COST_B + 2 * SLIP_S + 2 * max(C5_M / C5_A - 0.001425, 0.0)
LIQ = 5e7
ANCHOR = (0.24020209886370614, -0.3395700527611012)
EXCL_FB = {"金融保險", "生技醫療業"}
R1_DAY = "2016-01-04"
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def reg_check(sha):
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{sha}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{sha}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != sha:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}")
    return os.path.basename(fs[0])


def okcode(s):
    return PRE.okcode(s)


# ═════════════ 版面 ═════════════
def _wjob(args):
    sid, mk = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c0 = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
    bar = np.isfinite(c0)
    if bar.sum() < 2:
        return sid, None
    c = pd.Series(c0).ffill().to_numpy(float)
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)
    idx = np.flatnonzero(bar)
    a20 = np.full(n, np.nan)
    a20[idx] = pd.Series(amt[idx]).rolling(20, min_periods=20).mean().to_numpy()
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"])
    rc = pd.to_numeric(raw["close"], errors="coerce").reindex(cal).to_numpy(float)
    X = SL.stock_extra(sid, mk, cal, n)
    pv = UG.pit_valid(sid, cal, D.DATA)
    imp = X["sig20"] * np.sqrt(CAP_Q / X["adv20"])
    return sid, {"c": c, "o": np.where(np.isfinite(o) & (o > 0), o, np.nan), "bar": bar, "a20": a20, "rc": rc, "pv": np.asarray(pv, bool),
                 "avg": X["avg"], "imp": np.where(np.isfinite(imp), imp, np.nan), "trd": X["trd"], "upl": X["up_o"], "dnl": X["dn_o"], "dnc": X["dn_c"]}


class World:
    """一個版面（main／early）的全部逐日陣列。"""

    def __init__(self, part, procs, log):
        os.makedirs(WORK, exist_ok=True)
        self.part = part
        self.data = RR.H2D if part == "main" else EOTC
        D.DATA = self.data
        cal = D.load_calendar(); n = len(cal)
        cp = os.path.join(WORK, f"world_{part}.pkl")
        if os.path.exists(cp):
            Z = pickle.load(open(cp, "rb"))
            log(f"[版面 {part}] 讀快取 {cp}")
        else:
            st = pd.read_csv(os.path.join(self.data, "meta", "stocks.csv"), dtype=str)
            U = UG.gate3(st)
            U = U[U["stock_id"].map(okcode)].reset_index(drop=True)
            _G["cal"] = cal
            t0 = time.time(); res = {}
            with Pool(procs) as pool:
                for i, (sid, v) in enumerate(pool.imap_unordered(_wjob, list(zip(U["stock_id"], U["market"])), chunksize=8)):
                    if v is not None:
                        res[sid] = v
                    if i % 400 == 0:
                        log(f"[版面 {part}] {i}/{len(U)}｜{time.time() - t0:.0f}s")
            sids = sorted(res)
            Z = {"sids": sids, "mk": U.set_index("stock_id")["market"].to_dict(), "n_gate3": int(len(U))}
            for k in ("c", "o", "bar", "a20", "rc", "pv", "avg", "imp", "trd", "upl", "dnl", "dnc"):
                Z[k] = np.vstack([res[s][k] for s in sids])
            pickle.dump(Z, open(cp, "wb"), protocol=5)
            log(f"[版面 {part}] {len(sids)} 檔（gate3∩四碼 {len(U)}）｜{time.time() - t0:.0f}s")
        self.cal = cal; self.n = n
        self.sids = Z["sids"]; self.mk = Z["mk"]; self.ix = {s: i for i, s in enumerate(self.sids)}
        for k in ("c", "o", "bar", "a20", "rc", "pv", "avg", "imp", "trd", "upl", "dnl", "dnc"):
            setattr(self, k.upper(), Z[k])
        self.n_gate3 = Z["n_gate3"]
        self.bench = RR.load_bench(cal)
        self.S = len(self.sids)
        self.mon = np.array([d.year * 100 + d.month for d in cal])
        self.UNI = self.BAR & self.PV & (np.nan_to_num(self.A20, nan=0.0) >= LIQ)
        self.MKT = self.BAR & self.PV & np.isfinite(self.A20)
        # 價格墊一根（未完 ⇒ 墊檔日）
        self.CP = np.hstack([self.C, self.C[:, -1:]])
        self.OP = np.hstack([self.O, np.full((self.S, 1), np.nan)])
        self.AVP = np.hstack([self.AVG, np.full((self.S, 1), np.nan)])
        self.TRP = np.hstack([self.TRD, np.zeros((self.S, 1), bool)])
        self.UPP = np.hstack([self.UPL, np.zeros((self.S, 1), bool)])
        self.okb = [np.flatnonzero(self.BAR[i] & np.isfinite(self.O[i])) for i in range(self.S)]
        self.okr = [np.flatnonzero(self.TRD[i] & ~self.DNL[i] & np.isfinite(self.AVG[i]) & (self.AVG[i] > 0)) for i in range(self.S)]
        self.cbar = np.cumsum(self.BAR, axis=1)
        try:
            off = TR.load_official()
        except Exception:
            off = {}
        self.dl = TR.delist_status({s: {"trd": self.TRD[i]} for i, s in enumerate(self.sids)}, cal, official=off)
        self.ind_cache = {}

    def pos(self, d):
        return int(self.cal.searchsorted(pd.Timestamp(d)))

    def segpos(self, a, b):
        x, y = self.pos(a), int(self.cal.searchsorted(pd.Timestamp(b), side="right")) - 1
        return x, y

    def month_first_days(self, lo=None, hi=None):
        m = self.mon; f = np.r_[True, m[1:] != m[:-1]]
        p = np.flatnonzero(f)
        if lo is not None:
            p = p[p >= lo]
        if hi is not None:
            p = p[p <= hi]
        return p

    def ma_up(self, L):
        """有效 K 棒序列上：收盤 ＞ MA_L 且 MA_L ＞ 5 根前的 MA_L ⇒ 日曆長布林（沒 K 棒的日子 False）。"""
        out = np.zeros((self.S, self.n), bool)
        for i in range(self.S):
            idx = np.flatnonzero(self.BAR[i])
            if len(idx) < L + 5:
                continue
            cb = self.C[i, idx]
            ma = pd.Series(cb).rolling(L, min_periods=L).mean().to_numpy()
            ma5 = np.r_[np.full(5, np.nan), ma[:-5]]
            with np.errstate(invalid="ignore"):
                out[i, idx] = (cb > ma) & (ma > ma5)
        return out

    # ── 出場價 ──
    def exit_open(self, i, x, real):
        """x 起第一個可賣開盤 ⇒ (xpos, px)；沒有 ⇒ None（未完）。"""
        arr = self.okr[i] if real else self.okb[i]
        j = int(np.searchsorted(arr, x))
        if j >= len(arr):
            return None
        xp = int(arr[j])
        return xp, float(self.AVG[i, xp] if real else self.O[i, xp])

    def exit_close(self, i, y, real):
        """y 收盤賣 ⇒ (xpos＝y＋1, px)；real：y 起第一個可賣日（停牌、收盤一字跌停 ⇒ 延）均價。"""
        if y >= self.n:
            return None
        if not real:
            return y + 1, float(self.C[i, y])
        ok = self.TRD[i] & ~self.DNC[i] & np.isfinite(self.AVG[i]) & (self.AVG[i] > 0)
        w = np.flatnonzero(ok[y:])
        if not len(w):
            return None
        yy = y + int(w[0])
        return yy + 1, float(self.AVG[i, yy])


# ═════════════ 產業 ═════════════
_REV: dict = {}


def tw_data(log):
    if "DATA" not in _REV:
        sha, DATA = PRE.ensure_data()
        _REV.update(sha=sha, DATA=DATA)
        log(f"[tw-stock-data] origin/main {sha[:10]} ⇒ {DATA}")
    return _REV["sha"], _REV["DATA"]


def load_rev(log):
    """月營收（C14）⇒ rev、rev_ly、mom、yoy（period × 代號）。"""
    if "rev" in _REV:
        return _REV
    sha, DATA = tw_data(log)
    fs = PRE.rev_files(DATA)
    use = ["stock_id", "period", "market", "產業別", "當月營收", "去年當月營收", "上月比較增減(%)", "去年同月增減(%)"]
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=lambda c: c in use) for f in fs], ignore_index=True)
    for c, k in (("當月營收", "rev"), ("去年當月營收", "rev_ly"), ("上月比較增減(%)", "mom"), ("去年同月增減(%)", "yoy")):
        df[k] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce") if c in df else np.nan
    df["產業別"] = df["產業別"].fillna("")
    df["_old"] = df["產業別"].isin(PRE.OLDNAMES)
    cat = df.sort_values(["stock_id", "period", "_old"], kind="stable").drop_duplicates(["stock_id", "period"], keep="first")[["stock_id", "period", "market", "產業別"]]
    val = df.drop_duplicates(["stock_id", "period"], keep="last")
    pers = sorted(val["period"].unique()); full = [pers[0]]
    while full[-1] < pers[-1]:
        full.append(PRE.mshift(full[-1], 1))
    P = {k: val.pivot(index="period", columns="stock_id", values=k).reindex(full).sort_index() for k in ("rev", "rev_ly", "mom", "yoy")}
    _REV.update(P); _REV["cat"] = cat; _REV["nfiles"] = len(fs); _REV["nrows"] = int(len(df))
    _REV["PIT"] = PRE.PIT(DATA, cat)
    log(f"[月營收] {len(fs)} 檔、{len(df):,} 列；期別 {full[0]}～{full[-1]}；代號 {P['rev'].shape[1]}")
    return _REV


def avail_map(W, periods):
    """period ⇒ 可用日日曆位置（C14；本版面日曆）。"""
    rd = {**R34.rebalance_dates([M for M in periods if M <= "2025-12"], W.cal, 10), **R34.rebalance_dates([M for M in periods if M >= "2026-01"], W.cal, 15)}
    return {M: e for M, (_, e) in rd.items()}


def industry(W, i, d, log=print):
    """產業（PIT 版）於日曆位置 d。"""
    key = (i, d)
    if key not in W.ind_cache:
        P = load_rev(log)["PIT"]
        W.ind_cache[key] = P._at(W.sids[i], W.cal[d], "pit")[0]
    return W.ind_cache[key]


def fb_mask(W, d, log=print):
    """d 當天要剔的金融、生技（S 長布林）＋ 計數。"""
    m = np.zeros(W.S, bool); old = 0
    for i in np.flatnonzero(W.MKT[:, d]):
        ind = industry(W, i, d, log)
        if ind in EXCL_FB:
            m[i] = True
        elif ind == "化學生技醫療":
            old += 1
    return m, old


def r1_x(W, excl_fb=False, log=print):
    d = W.pos(R1_DAY)
    mk = W.MKT[:, d].copy(); u = W.UNI[:, d].copy()
    if excl_fb:
        fb, _ = fb_mask(W, d, log); mk &= ~fb; u &= ~fb
    return float(u.sum() / mk.sum()), int(u.sum()), int(mk.sum())


def r1_uni(W, d, X, extra=None):
    m = W.MKT[:, d].copy()
    if extra is not None:
        m &= extra
    idx = np.flatnonzero(m)
    k = int(np.ceil(X * len(idx)))
    order = idx[np.argsort(-W.A20[idx, d], kind="stable")]
    out = np.zeros(W.S, bool); out[order[:k]] = True
    return out


# ═════════════ 訊號列 ⇒ 引擎輸入 ═════════════
def finalize_rows(W, rows, real):
    """rows：DataFrame 欄 s、e、xk（"open"／"close"）、x（開盤賣排定日或收盤賣日）、why、key（選填）
    ⇒ 引擎 sig（sid、entry_pos、xpos_F、g_F、pick）＋ 每列 hold/未完/理由。"""
    out = []
    for r in rows.itertuples(index=False):
        i, e = int(r.s), int(r.e)
        if real:
            ep = W.AVG[i, e]
            if not (np.isfinite(ep) and ep > 0):
                ep = np.nan
        else:
            ep = W.O[i, e]
        if not np.isfinite(ep):
            if real:
                out.append((i, e, e + 1, 0.0, "進場日無均價", 0, np.nan, getattr(r, "key", np.nan))); continue   # 引擎 halt_in 擋（trd 假）或用不到
            continue
        res = None
        if r.x is not None and r.x >= 0 and r.x < W.n:
            res = W.exit_open(i, int(r.x), real) if r.xk == "open" else W.exit_close(i, int(r.x), real)
        if res is None:
            xp, px, why, end = W.n, float(W.C[i, -1]), "未完", 1
        else:
            xp, px = res; why, end = r.why, 0
        if real:
            ii = W.IMP[i, e] if np.isfinite(W.IMP[i, e]) else 0.0
            io = (W.IMP[i, xp - 1 if r.xk == "close" else xp] if xp < W.n else np.nan) if not end else 0.0
            io = io if np.isfinite(io) else 0.0
            g = px * (1 - min(io, 0.99)) / (ep * (1 + ii)) - 1.0
        else:
            g = px / ep - 1.0
        out.append((i, e, int(xp), float(g), why, end, float(ep), getattr(r, "key", np.nan)))
    F = pd.DataFrame(out, columns=["s", "e", "xpos", "g", "why", "end", "ep", "key"])
    F["sid"] = [W.sids[i] for i in F["s"]]
    return F


def engine_sig(F):
    return pd.DataFrame({"sid": F["sid"].to_numpy(), "entry_pos": F["e"].to_numpy(int), "xpos_F": F["xpos"].to_numpy(int),
                         "g_F": F["g"].to_numpy(float), "pk": F["key"].to_numpy(float)})


def sim(W, F, real, r, pick, upto, cash_bench=False, seed0=SEED0):
    """一顆。pick＝True ⇒ pk 遞減（不抽籤）。"""
    sig = engine_sig(F)
    sids = sorted(set(sig["sid"]))
    closes = {s: W.CP[W.ix[s]] for s in sids}
    opens = {s: (W.AVP if real else W.OP)[W.ix[s]] for s in sids}
    SF = {s: L for s, L in _sf(W, upto).items() if s in closes}
    kw = {}
    if real:
        z = np.zeros(W.n + 1, bool)
        kw["tradable"] = {s: {"trd": W.TRP[W.ix[s]], "up_o": W.UPP[W.ix[s]], "dn_o": z, "dn_c": z} for s in sids}
        kw["delist"] = {s: W.dl[s] for s in sids if s in W.dl}
    if cash_bench:
        b = np.r_[W.bench, W.bench[-1]]
        kw.update(cash_mode="bench", bench=b, bench_cost=COST_B / 2)
    au = []
    R.COST = COST_R if real else COST_B
    try:
        o = R.simulate_mtm(sig, "F", 10, np.random.default_rng(seed0 + r), closes, opens, W.n + 1, return_equity=True, audit=au,
                           pick="pk" if pick else None, stop_force=SF, **kw)
    finally:
        R.COST = COST_B
    return o, au


def _sf(W, upto):
    k = ("sf", upto)
    if k not in W.ind_cache:
        W.ind_cache[k] = R.stop_force_days({s: W.BAR[i] for i, s in enumerate(W.sids)}, upto)
    return W.ind_cache[k]


def holdings(au, n):
    """audit ⇒ [(sid, t_buy, t_sell, amt, px)]（未賣 ⇒ t_sell＝n）。"""
    op, iv = {}, []
    for x in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
        if x["side"] == "buy":
            op[x["sid"]] = (int(x["t"]), float(x["amt"]), float(x["px"]))
        elif x["side"] == "sell" and x["sid"] in op:
            t0, a, p = op.pop(x["sid"]); iv.append((x["sid"], t0, int(x["t"]), a, p))
    for s, (t0, a, p) in op.items():
        iv.append((s, t0, n, a, p))
    return iv


def seg_hold(W, o, au, segp):
    """段內平均持股（逐日檔數）與平均現金（1 − 持股市值 ÷ 權益）。"""
    n = W.n + 1
    nh = np.zeros(n)
    for s, t0, t1, a, p in holdings(au, n):
        nh[t0:t1] += 1
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        cash = 1 - hv / eq
    out = {}
    for k, (a, b) in segp.items():
        out[f"{k}_平均持股"] = float(nh[a:b + 1].mean()); out[f"{k}_平均現金"] = float(np.nanmean(cash[a:b + 1]))
    return out


def seg_ret(W, o, segp):
    eq = np.asarray(o["equity"], float); out = {}
    for k, (a, b) in segp.items():
        c, m, v = RR.win_metrics(eq, o["first"], o["end"], a, b)
        out[f"{k}_年化"] = c; out[f"{k}_回落"] = m
    return out


def years_ret(W, o, a0, b0):
    eq = np.asarray(o["equity"], float); cal = W.cal; out = {}
    for y in sorted(set(cal[a0:b0 + 1].year)):
        a = max(a0 - 1, int(cal.searchsorted(pd.Timestamp(y, 1, 1))) - 1); b = min(b0, int(cal.searchsorted(pd.Timestamp(y + 1, 1, 1))) - 1)
        out[str(y)] = float(eq[b] / eq[a] - 1)
    return out


def bench_years(W, a0, b0):
    cal = W.cal; out = {}
    for y in sorted(set(cal[a0:b0 + 1].year)):
        a = max(a0 - 1, int(cal.searchsorted(pd.Timestamp(y, 1, 1))) - 1); b = min(b0, int(cal.searchsorted(pd.Timestamp(y + 1, 1, 1))) - 1)
        out[str(y)] = float(W.bench[b] / W.bench[a] - 1)
    return out


def label(c, m, z):
    if not (np.isfinite(c) and np.isfinite(m)):
        return "—", np.nan
    ratio = c / abs(m) if m < 0 else np.inf
    zr = z["cagr"] / abs(z["mdd"])
    return ("合格" if (c > z["cagr"] and ratio >= zr) else ("另列" if c > z["cagr"] else "不合格")), ratio


STRICT = {"合格": 2, "另列": 1, "不合格": 0}


def stricter(*labs):
    labs = [l for l in labs if l in STRICT]
    return min(labs, key=lambda l: STRICT[l]) if labs else "—"


def eff_n(W, iv, days):
    res = []
    for t in days:
        held = [s for s, t0, t1, a, p in iv if t0 <= t < t1]
        N = len(held)
        if N == 0:
            continue
        if N == 1:
            res.append((t, 1, np.nan, 1.0, held)); continue
        Rm = []
        for s in held:
            c = W.CP[W.ix[s], max(t - 60, 0):t + 1]
            Rm.append(c[1:] / c[:-1] - 1.0 if len(c) == 61 else np.full(60, np.nan))
        Rm = np.array(Rm); cs = []
        for i in range(N):
            for j in range(i + 1, N):
                mk = np.isfinite(Rm[i]) & np.isfinite(Rm[j])
                if mk.sum() < 40:
                    continue
                a, b = Rm[i][mk], Rm[j][mk]
                if a.std() == 0 or b.std() == 0:
                    continue
                cs.append(float(np.corrcoef(a, b)[0, 1]))
        rho = float(np.mean(cs)) if cs else np.nan
        res.append((t, N, rho, N / (1 + (N - 1) * rho) if np.isfinite(rho) else np.nan, held))
    return res


def q_(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p25": float(np.percentile(x, 25)),
            "p75": float(np.percentile(x, 75)), "p90": float(np.percentile(x, 90))}


def dn15(W, i, e, ep):
    """一年內先跌 15%：(先跌, 觀察窗滿)。"""
    if e + 250 > W.n - 1:
        return None
    w = W.C[i, e + 1:e + 251]
    up = np.flatnonzero(w >= ep * 1.15); dn = np.flatnonzero(w <= ep * 0.85)
    u = up[0] if len(up) else 999; d = dn[0] if len(dn) else 999
    return bool(d < u)


# ═════════════ 一件的通用流程 ═════════════
class Study:
    """子類別要給：NAME、OUT、cells（list 名）、PICK（格 ⇒ bool）、build(W, uni_fn) ⇒ {格: rows}、uni_fn(W, d) ⇒ S 長布林（母體）。"""

    def __init__(self, a, log):
        self.a = a; self.log = log
        self.reps = a.reps

    # ── 段位置 ──
    def segp(self, W):
        if W.part == "main":
            return {k: W.segpos(*v) for k, v in SEGS.items()}
        return {"早年": W.segpos(*self.early_win)}

    def window(self, W):
        sp = self.segp(W)
        return (sp["主窗"] if W.part == "main" else sp["早年"])

    def bench_z(self, W):
        return {k: RR.bench_row(W.cal, W.bench, a, b + 1) for k, (a, b) in self.segp(W).items()}

    def in_win(self, W, rows):
        a, b = self.window(W)
        return rows[(rows["e"] >= a) & (rows["e"] <= b)].reset_index(drop=True)

    # ── 跑格 ──
    def run_arms(self, W, arms, procs):
        """arms：[(名, F 表, real, pick, reps, cash_bench)] ⇒ {名: [每顆 dict（含 equity 統計與 au 摘要）]}"""
        _G["W"] = W; _G["ARMS"] = {nm: (F, real, pick, cb) for nm, F, real, pick, reps, cb in arms}
        _G["upto"] = self.window(W)[1]; _G["segp"] = self.segp(W)
        jobs = [(nm, r) for nm, F, real, pick, reps, cb in arms for r in range(1 if pick else reps)]
        out = {}
        t0 = time.time()
        with Pool(procs) as pool:
            for i, (nm, r, m) in enumerate(pool.imap_unordered(_armjob, jobs, chunksize=2)):
                out.setdefault(nm, []).append(m)
                if i % 200 == 0:
                    self.log(f"[引擎] {i + 1}/{len(jobs)}｜{time.time() - t0:.0f}s")
        for nm in out:
            out[nm].sort(key=lambda z: z["r"])
        return out


def _armjob(args):
    nm, r = args
    W = _G["W"]; F, real, pick, cb = _G["ARMS"][nm]
    o, au = sim(W, F, real, r, pick, _G["upto"], cash_bench=cb)
    m = {"r": r}
    m["hold"] = seg_hold(W, o, au, _G["segp"])
    m["eq"] = np.asarray(o["equity"], np.float64)
    m["first"], m["end"] = int(o["first"]), int(o["end"])
    m["iv"] = holdings(au, W.n + 1)
    m["sf_n"] = int(o.get("x_stop_force_n", 0)); m["lu"] = int(o.get("tr_limit_up", 0)); m["halt_in"] = int(o.get("tr_halt_in", 0))
    m["dl_settled"] = int(o.get("tr_delist_settled", 0))
    return nm, r, m


# ═════════════ 通用流程 ═════════════
def med(ms, k):
    v = np.array([m[k] for m in ms], float)
    return float(np.nanmedian(v)) if len(v) else np.nan


def summarize(W, ms, Z, segs):
    row = {"種子": len(ms)}
    for sg in segs:
        r_ = [seg_ret(W, {"equity": m["eq"], "first": m["first"], "end": m["end"]}, {sg: segs[sg]}) for m in ms]
        cs = np.array([x[f"{sg}_年化"] for x in r_], float); ds = np.array([x[f"{sg}_回落"] for x in r_], float)
        c, d = float(np.nanmedian(cs)), float(np.nanmedian(ds))
        lab, rt = label(c, d, Z[sg])
        row.update({f"{sg}_年化": c, f"{sg}_回落": d, f"{sg}_比值": rt, f"{sg}_標籤": lab,
                    f"{sg}_年化p10": float(np.nanpercentile(cs, 10)), f"{sg}_年化p90": float(np.nanpercentile(cs, 90))})
        row[f"_{sg}_all"] = cs
    return row


def hold_only(ms, segs):
    out = {}
    for sg in segs:
        out[f"{sg}_平均持股"] = med([m["hold"] for m in ms], f"{sg}_平均持股")
        out[f"{sg}_平均現金"] = med([m["hold"] for m in ms], f"{sg}_平均現金")
    return out


def degen(h, sg):
    return bool(h[f"{sg}_平均持股"] < 3 or h[f"{sg}_平均現金"] > 0.30)


def fake_rows(W, F, U, r, pick):
    """C11：同進場日同筆數、隨機股、持有天數抽自挑中格。"""
    rng = np.random.default_rng([FSEED, r])
    hd = (F["xpos"] - F["e"])[F["end"] == 0].to_numpy(int)
    rows = []
    for e, g in F.groupby("e"):
        pool = np.flatnonzero(U[:, e - 1] & np.isfinite(W.O[:, e]))
        if not len(pool) or not len(hd):
            continue
        ss = rng.choice(pool, size=min(len(g), len(pool)), replace=False)
        for s in ss:
            h = int(rng.choice(hd))
            rows.append((int(s), int(e), "open", int(e + h), "假訊號到期", float(rng.random()) if pick else np.nan))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def fixed_rows(W, F, H):
    rows = []
    for s, e, k in zip(F["s"], F["e"], F["key"]):
        idx = np.flatnonzero(W.BAR[s, e:]) + e
        y = int(idx[H - 1]) if len(idx) >= H else -1
        rows.append((int(s), int(e), "close", y, f"固定{H}根", k))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def ma200_keep(W, F):
    ma = pd.Series(W.bench).rolling(200, min_periods=200).mean().to_numpy()
    d = F["e"].to_numpy(int) - 1
    with np.errstate(invalid="ignore"):
        return W.bench[d] > ma[d]


def trade_stats(W, ms, F, w1):
    """C13 逐筆必報（實際成交的筆，種子合計）。"""
    key = {(sid, int(e)): i for i, (sid, e) in enumerate(zip(F["sid"], F["e"]))}
    hold, why, dn, tail, tailh = [], {}, [], [], []
    nb = 0
    for m in ms:
        tl = 0
        for sid, t0, t1, a, p in m["iv"]:
            i = key.get((sid, t0))
            if i is None or t0 > w1:
                continue
            nb += 1
            row = F.iloc[i]
            if t1 > w1:
                tl += 1; tailh.append(w1 - t0 + 1)
                continue
            hold.append(t1 - t0)
            w = row["why"] if t1 == int(row["xpos"]) else "停止交易強制出場／延後"
            why[w] = why.get(w, 0) + 1
            x = dn15(W, int(row["s"]), t0, float(row["ep"]))
            if x is not None:
                dn.append(x)
        tail.append(tl)
    R_ = max(len(ms), 1)
    return {"每顆平均買進筆（窗內）": nb / R_, "持有天數（交易日，已出場）": q_(hold), "出場原因（每顆平均）": {k: v / R_ for k, v in sorted(why.items(), key=lambda z: -z[1])},
            "窗尾仍持有（檔，種子中位）": float(np.median(tail)) if tail else np.nan, "窗尾仍持有已持有天數": q_(tailh),
            "一年內先跌15%比例": float(np.mean(dn)) if dn else np.nan, "觀察窗滿250筆": len(dn)}


def neff_stats(W, m0, segs, log):
    iv = m0["iv"]
    days = sorted({t0 for s, t0, t1, a, p in iv})
    res = eff_n(W, iv, days)
    out = {}
    for sg, (a, b) in segs.items():
        rr = [x for x in res if a <= x[0] <= b]
        if not rr:
            continue
        mx = []
        for t, N, rho, ne, held in rr:
            cnt = {}
            for s in held:
                ind = industry(W, W.ix[s], t, log) or "無類別"
                cnt[ind] = cnt.get(ind, 0) + 1
            mx.append(max(cnt.values()))
        out[sg] = {"換股日": len(rr), "平均持股": float(np.mean([x[1] for x in rr])), "平均ρ": float(np.nanmean([x[2] for x in rr])),
                   "平均N_eff": float(np.nanmean([x[3] for x in rr])), "N_eff中位": float(np.nanmedian([x[3] for x in rr])),
                   "最大產業檔數中位": float(np.median(mx)), "最大產業檔數最大": int(max(mx)), "最大產業＞3檔的換股日占比": float(np.mean(np.array(mx) > 3)),
                   "產業分類層": "上市櫃官方產業別（單層，industry_pit pit 版）"}
    return out


def overlap_daily(ivA, ivB, a, b):
    """A 持股中同日也在 B 持股的比例（逐日，A 有持股的日子平均）。"""
    n = b + 1
    HA = {}; HB = {}
    for s, t0, t1, *_ in ivA:
        for t in range(max(t0, a), min(t1, n)):
            HA.setdefault(t, set()).add(s.split("#")[0])
    for s, t0, t1, *_ in ivB:
        for t in range(max(t0, a), min(t1, n)):
            HB.setdefault(t, set()).add(s.split("#")[0])
    v = [len(HA[t] & HB.get(t, set())) / len(HA[t]) for t in HA if HA[t]]
    return float(np.mean(v)) if v else np.nan


# ═════════════ 營量 v1／營飆 v1 對照（C15）═════════════
def yl_ref(log, procs=2, reps=200, and_path=None, tag="base"):
    """營飆 v1（reps 顆）、營量 v1（r＝0）同窗三段。and_path＝None ⇒ 正式 AND。"""
    cp = os.path.join(WORK, f"yl_{tag}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    os.makedirs(WORK, exist_ok=True)
    RR.use_snapshot()
    cal = D.load_calendar()
    RR.setup_and(cal, and_path or os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log, t1=True)
    G = RR._G; AND = G["AND"]; reg = G["regime"]; e = AND["entry_pos"].to_numpy()
    inwin = (e >= G["w0"]) & (e <= G["w1"])
    mk = D.load_universe().set_index("stock_id")["market"]
    ctx = {"cal": cal, "sig": AND[reg[e - 1] & inwin], "sig13": AND[inwin], "closes": G["closes"], "opens": G["opens"], "ncal": G["ncal"],
           "w0": G["w0"], "w1": G["w1"], "mk": mk}
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    _G["YL"] = (ctx, SF)
    segp = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in SEGS.items()}
    _G["YLseg"] = segp
    jobs = [("fly", r) for r in range(reps)] + [("vol", 0)]
    rows = []
    with Pool(procs) as pool:
        for x in pool.imap_unordered(_yljob, jobs, chunksize=4):
            rows.append(x)
    bench = RR.load_bench(cal)
    Z = {k: RR.bench_row(cal, bench, a, b + 1) for k, (a, b) in segp.items()}
    out = {"rows": rows, "Z": Z, "n_fly": int(len(ctx["sig"])), "n_vol": int(len(ctx["sig13"])),
           "sig_fly": ctx["sig"][["sid", "k", "pos", "entry_pos"]].copy(), "sig_vol": ctx["sig13"][["sid", "k", "pos", "entry_pos"]].copy(),
           "t1_cnt": G.get("t1_cnt")}
    pickle.dump(out, open(cp, "wb"), protocol=5)
    return out


def _yljob(args):
    fam, r = args
    from backtest import listexit_lines as L
    ctx, SF = _G["YL"]
    au = []
    if fam == "fly":
        o = L.sim(ctx, {"stop_force": SF}, r, audit=au)
    else:
        o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"],
                           log=[], d_max=None, pick="relvol", queue_days=0, return_equity=True, stop_force=SF, audit=au)
    eq = np.asarray(o["equity"], float)
    m = {"fam": fam, "r": r, "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])}
    c, mm, v = RR.win_metrics(eq, o["first"], o["end"], ctx["w0"], ctx["w1"])
    m.update(cagr=c, mdd=mm, vol=v)
    for k, (a, b) in _G["YLseg"].items():
        c, mm, _ = RR.win_metrics(eq, o["first"], o["end"], a, b)
        m[f"{k}_年化"] = c; m[f"{k}_回落"] = mm
    n = len(eq); nh = np.zeros(n); iv = holdings(au, n)
    for s, t0, t1, a_, p in iv:
        nh[t0:t1] += 1
    hv = np.asarray(o["hold_val"], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        cash = 1 - hv / eq
    for k, (a, b) in _G["YLseg"].items():
        m[f"{k}_平均持股"] = float(nh[a:b + 1].mean()); m[f"{k}_平均現金"] = float(np.nanmean(cash[a:b + 1]))
    if r == 0:
        m["iv"] = iv
    return m


def yl_table(Y):
    out = {}
    for fam, nm in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        g = [x for x in Y["rows"] if x["fam"] == fam]
        row = {"種子": len(g)}
        for sg in SEGS:
            c = float(np.median([x[f"{sg}_年化"] for x in g])); d = float(np.median([x[f"{sg}_回落"] for x in g]))
            lab, rt = label(c, d, Y["Z"][sg])
            row.update({f"{sg}_年化": c, f"{sg}_回落": d, f"{sg}_比值": rt, f"{sg}_標籤": lab,
                        f"{sg}_平均持股": float(np.median([x[f"{sg}_平均持股"] for x in g])), f"{sg}_平均現金": float(np.median([x[f"{sg}_平均現金"] for x in g]))})
        out[nm] = row
    return out


def yl_gate(Y):
    ref = pd.read_csv(os.path.join(os.path.expanduser("~/tw-p17/backtest"), "resultsT1fix", "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    bad = 0; n = 0
    for x in Y["rows"]:
        key = "c1" if x["fam"] == "fly" else "c13"
        q = ref[(ref["key"] == key) & (ref["var"] == "t1") & (ref["r"] == x["r"])]
        if not len(q):
            continue
        q = q.iloc[0]; n += 1
        ok = repr(float(q["cagr"])) == repr(float(x["cagr"])) and repr(float(q["mdd"])) == repr(float(x["mdd"])) and str(q["eq_sha"]) == x["eq_sha"] \
            and int(q["trades"]) == x["trades"]
        bad += not ok
    return {"比對顆數": n, "不同": bad, "對照": "resultsT1fix/seeds.csv.gz c1／c13 t1"}


# ═════════════ 一件的主流程 ═════════════
def pct(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def run_study(ST, a):
    """ST：件定義物件（見各件檔）。全部流程：sha → 版面 → 訊號 → 退化（先寫）→ 報酬 → 挑格 → 早年 → 對照與描述 → 必報 → 存檔。"""
    if getattr(a, "smoke", False):                       # 冒煙：只用 1/7 的股票、輸出到工作夾（數字不是本件結果）
        ST.OUT = os.path.join(WORK, f"smoke_{ST.KEY}")
        _u = ST.universe
        ST.universe = lambda W, log: _u(W, log) & (np.arange(W.S) % 7 == 0)[:, None]
    OUT = ST.OUT; os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== {ST.NAME} run {now_tpe()}（台北）｜讀法寫死 {ST.TIME}｜核心 {TIME_CORE}｜reps {a.reps} =====")
    regf = reg_check(ST.REG_SHA); log(f"[sha] {ST.REG_SHA} ✔ {regf}")
    t00 = time.time()
    WM = World("main", a.procs, log)
    seg = {k: WM.segpos(*v) for k, v in SEGS.items()}
    assert seg["主窗"] == (WM.pos("2017-03-02"), WM.pos("2026-08-24"))
    Z = {k: RR.bench_row(WM.cal, WM.bench, x, y + 1) for k, (x, y) in seg.items()}
    g0 = (repr(Z["主窗"]["cagr"]) == repr(ANCHOR[0]), repr(Z["主窗"]["mdd"]) == repr(ANCHOR[1]))
    log(f"[0050] {Z}｜主窗錨逐位元 {g0}")
    if not all(g0):
        raise SystemExit("⛔ 0050 錨不對")
    w0, w1 = seg["主窗"]
    U = ST.universe(WM, log)
    ROWS = ST.build(WM, U, log)
    META = {"件": ST.NAME, "登錄": regf, "sha": ST.REG_SHA, "讀法寫死": ST.TIME, "核心讀法寫死": TIME_CORE, "run": now_tpe(), "reps": a.reps,
            "版面": {"main": [str(WM.cal[0].date()), str(WM.cal[-1].date()), WM.n, WM.S, WM.n_gate3]}, "0050": Z}
    META.update(ST.meta_extra)
    FB, FR = {}, {}
    for c in ST.cells:
        rw = ROWS[c]; rw = rw[(rw["e"] >= w0) & (rw["e"] <= w1)].reset_index(drop=True)
        FB[c] = finalize_rows(WM, rw, False); FR[c] = finalize_rows(WM, rw, True)
        log(f"[訊號] {c}：窗內 {len(rw)} 列 ⇒ base 可進 {len(FB[c])}（e 無有效開盤剔 {len(rw) - len(FB[c])}）、未完 {int(FB[c]['end'].sum())}")
    # ── 退化檢查（先寫）──
    cand = {}
    for c in ST.cells:
        F = FB[c]; g = F.groupby("e").size()
        yrs = pd.Series([WM.cal[e].year for e in F["e"]]).value_counts().sort_index()
        cand[c] = {"換股日數": int(len(g)), "每換股日候選數": q_(g.to_numpy()), "候選 0 的換股日": int(sum(1 for e in ST.rebal_days(WM) if w0 <= e <= w1 and e not in g.index)),
                   "訊號數逐年": {str(k): int(v) for k, v in yrs.items()}}
    arms = []
    for c in ST.cells:
        arms.append((f"{c}|b", FB[c], False, ST.PICK[c], a.reps, False))
        arms.append((f"{c}|r", FR[c], True, ST.PICK[c], a.reps, False))
    RES = run_arms_generic(WM, arms, seg, w1, a.procs, log)
    DG = {}
    for nm, ms in RES.items():
        h = hold_only(ms, seg); DG[nm] = {**h, "探索_退化": degen(h, "探索"), "確認_退化": degen(h, "確認"), "主窗_退化": degen(h, "主窗"), "種子": len(ms)}
    DJ = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在算任何報酬之前寫入（C9）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（種子中位）",
          "候選與訊號": cand, "持股與現金": DG}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索持股 {v['探索_平均持股']:.2f}／現金 {v['探索_平均現金']:.1%}{'（退化）' if v['探索_退化'] else ''}" for k, v in DG.items()))
    # ── 報酬 ──
    GRID = []
    for nm, ms in RES.items():
        c, v = nm.split("|")
        row = {"格": c, "版本": v, **summarize(WM, ms, Z, seg), **DG[nm]}
        GRID.append(row)
    GR = pd.DataFrame(GRID)
    base = GR[GR["版本"] == "b"].copy()
    base["_ord"] = [ST.cells.index(c) for c in base["格"]]
    nd = base[~base["探索_退化"]]
    all_deg = len(nd) == 0
    pool_ = nd if not all_deg else base
    q = pool_[pool_["探索_標籤"] == "合格"]
    pick = (q if len(q) else pool_).sort_values(["探索_比值", "探索_年化", "_ord"], ascending=[False, False, True]).iloc[0]
    chosen = pick["格"]
    log(f"[挑格] 非退化 {len(nd)}／{len(base)}、探索合格 {len(q)} ⇒ {chosen}{'（⚠ 全退化）' if all_deg else ''}")
    CH = {v: GR[(GR["格"] == chosen) & (GR["版本"] == v)].iloc[0].to_dict() for v in ("b", "r")}
    # ── 早年 ──
    EARLYR = None
    if ST.early_ok:
        WE = World("early", a.procs, log)
        ew = ST.early_window(WE, log)
        META["版面"]["early"] = [str(WE.cal[0].date()), str(WE.cal[-1].date()), WE.n, WE.S, WE.n_gate3]
        if ew is not None:
            es = {"早年": WE.segpos(*ew)}
            ZE = {"早年": RR.bench_row(WE.cal, WE.bench, es["早年"][0], es["早年"][1] + 1)}
            UE = ST.universe(WE, log); RE = ST.build(WE, UE, log)
            ea, eb = es["早年"]
            earms = []
            FE = {}
            for c in ST.cells:
                rw = RE[c]; rw = rw[(rw["e"] >= ea) & (rw["e"] <= eb)].reset_index(drop=True)
                FE[c] = finalize_rows(WE, rw, False)
                earms.append((f"{c}|b", FE[c], False, ST.PICK[c], a.reps, False))
            FER = finalize_rows(WE, RE[chosen][(RE[chosen]["e"] >= ea) & (RE[chosen]["e"] <= eb)].reset_index(drop=True), True)
            earms.append((f"{chosen}|r", FER, True, ST.PICK[chosen], a.reps, False))
            RE_ = run_arms_generic(WE, earms, es, eb, a.procs, log)
            EG = {}
            for nm, ms in RE_.items():
                h = hold_only(ms, es)
                EG[nm] = {**{k: v for k, v in summarize(WE, ms, ZE, es).items() if not k.startswith("_")}, **h, "早年_退化": degen(h, "早年")}
            msE = RE_[f"{chosen}|b"]
            EARLYR = {"窗": ew, "0050": ZE["早年"], "格": EG, "訊號": {c: int(len(FE[c])) for c in ST.cells},
                      "2013 期別訊號占比（IFRS 窗）": ST.ifrs_share(WE, FE[chosen]) if hasattr(ST, "ifrs_share") else None,
                      "各年（策略種子中位）": {k: float(np.median([years_ret(WE, {"equity": m["eq"]}, ea, eb)[k] for m in msE])) for k in years_ret(WE, {"equity": msE[0]["eq"]}, ea, eb)},
                      "各年0050": bench_years(WE, ea, eb), "逐筆": trade_stats(WE, msE, FE[chosen], eb), "覆蓋": getattr(ST, "early_cov", None)}
            DJ["早年"] = {nm: {k: v for k, v in x.items() if k.endswith(("持股", "現金", "退化"))} for nm, x in EG.items()}
            json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
            log(f"[早年] {ew}：" + "；".join(f"{k} {pct(v['早年_年化'])}／{pct(v['早年_回落'])} {v['早年_標籤']}" for k, v in EG.items()))
        else:
            EARLYR = {"窗": None, "原因": ST.early_note}
    # ── 判定 ──
    lab_c = CH["b"]["確認_標籤"]; lab_cr = CH["r"]["確認_標籤"]
    if EARLYR and EARLYR.get("窗"):
        lab_e = EARLYR["格"][f"{chosen}|b"]["早年_標籤"]; lab_er = EARLYR["格"].get(f"{chosen}|r", {}).get("早年_標籤", "—")
        fin_b = stricter(lab_c, lab_e); fin_r = stricter(lab_cr, lab_er)
    else:
        lab_e = lab_er = "不可判定"; fin_b, fin_r = lab_c, lab_cr
    tag = lambda L_: ("暫定（事後重切；只進前瞻紀錄）" if L_ == "合格" else L_)
    VERD = {"挑中格": chosen, "全退化": all_deg, "確認": lab_c, "早年": lab_e, "判定": tag(fin_b), "現實版確認": lab_cr, "現實版早年": lab_er, "現實版判定": tag(fin_r)}
    if all_deg:                                          # 裁定 seq325：退化格照登錄排除 ⇒ 全退化 ⇒ 沒有可判的格
        VERD.update({"判定": "全部格退化（照登錄排除）⇒ 沒有可判的格；下列「挑中格」數字只作描述（同挑法在全部格裡挑）",
                     "現實版判定": "同左（全退化）"})
    log(f"[判定] {VERD}")
    # ── 對照與描述 ──
    Fc = FB[chosen]; pk = ST.PICK[chosen]
    darms = []
    for H in (20, 60, 120):
        darms.append((f"固定{H}", finalize_rows(WM, fixed_rows(WM, Fc, H), False), False, pk, 50, False))
    keep = ma200_keep(WM, Fc)
    darms.append(("0050在200日線上才買", Fc[keep].reset_index(drop=True), False, pk, 50, False))
    X, nu, nm_ = r1_x(WM, ST.excl_fb, log)
    UR1 = np.zeros_like(U)
    for d in ST.dec_days(WM):
        UR1[:, d] = r1_uni(WM, d, X, ST.extra_mask(WM, d, log) if hasattr(ST, "extra_mask") else None)
    RR1 = ST.build(WM, UR1, log)[chosen]
    RR1 = RR1[(RR1["e"] >= w0) & (RR1["e"] <= w1)].reset_index(drop=True)
    darms.append(("R1排名版", finalize_rows(WM, RR1, False), False, pk, 50, False))
    for nm, rows in ST.extra_desc(WM, U, chosen, log).items():
        rows = rows[(rows["e"] >= w0) & (rows["e"] <= w1)].reset_index(drop=True)
        darms.append((nm, finalize_rows(WM, rows, False), False, pk, 50, "持0050" in nm))
    for i in range(a.fake):
        darms.append((f"假訊號#{i}", finalize_rows(WM, fake_rows(WM, Fc, U, i, pk), False), False, pk, 1, False))
    DRES = run_arms_generic(WM, darms, seg, w1, a.procs, log, fake_seed=True)
    DESC = {}
    for nm, ms in DRES.items():
        if nm.startswith("假訊號#"):
            continue
        DESC[nm] = {**summarize(WM, ms, Z, seg), **hold_only(ms, seg)}
    FK = [summarize(WM, ms, Z, seg) for nm, ms in DRES.items() if nm.startswith("假訊號#")]
    FAKE = {}
    for sg in SEGS:
        v = np.array([x[f"{sg}_年化"] for x in FK], float); d_ = np.array([x[f"{sg}_回落"] for x in FK], float)
        FAKE[sg] = {"抽數": len(v), "年化中位": float(np.nanmedian(v)), "年化p10": float(np.nanpercentile(v, 10)), "年化p90": float(np.nanpercentile(v, 90)),
                    "回落中位": float(np.nanmedian(d_)), "p（假訊號年化 ≥ 挑中格）": float(np.mean(v >= CH["b"][f"{sg}_年化"]))}
    # ── 必報 ──
    msC = RES[f"{chosen}|b"]
    TS = {"b": trade_stats(WM, msC, Fc, w1), "r": trade_stats(WM, RES[f"{chosen}|r"], FR[chosen], w1)}
    NE = neff_stats(WM, msC[0], seg, log)
    YR = {k: float(np.median([years_ret(WM, {"equity": m["eq"]}, w0, w1)[k] for m in msC])) for k in years_ret(WM, {"equity": msC[0]["eq"]}, w0, w1)}
    YR50 = bench_years(WM, w0, w1)
    Y = yl_ref(log, a.procs)
    YT = yl_table(Y)
    YG = yl_gate(Y)
    ovl = {}
    yvol = [x for x in Y["rows"] if x["fam"] == "vol"][0]["iv"]
    yfly = [x for x in Y["rows"] if x["fam"] == "fly" and x["r"] == 0][0]["iv"]
    for sg, (x_, y_) in seg.items():
        ovl[sg] = {"與營量 v1 持股重疊率": overlap_daily(msC[0]["iv"], yvol, x_, y_), "與營飆 v1 持股重疊率": overlap_daily(msC[0]["iv"], yfly, x_, y_)}
    EXTRA = ST.extra_stats(WM, U, FB, RES, chosen, seg, log) if hasattr(ST, "extra_stats") else {}
    SUM = {"meta": META, "判定": VERD, "挑中格": {v: {k: x for k, x in CH[v].items() if not k.startswith("_")} for v in CH}, "退化": DJ,
           "格": [{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID], "早年": EARLYR,
           "假訊號": FAKE, "描述": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in DESC.items()},
           "R1": {"X": X, "2016-01-04 5,000萬母體": nu, "同日全市場": nm_},
           "逐筆": TS, "等效獨立": NE, "各年": {"策略": YR, "0050": YR50}, "營量營飆": YT, "營量營飆閘": YG, "重疊": ovl, "件專屬": EXTRA,
           "耗時秒": round(time.time() - t00)}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
    pd.DataFrame([{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID]).to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    seeds = []
    for nm, ms in list(RES.items()) + list(DRES.items()):
        for m in ms:
            r_ = seg_ret(WM, {"equity": m["eq"], "first": m["first"], "end": m["end"]}, seg)
            seeds.append({"arm": nm, "r": m["r"], **r_, **m["hold"], "sha": hashlib.sha256(m["eq"].tobytes()).hexdigest()[:16]})
    pd.DataFrame(seeds).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    pickle.dump({"FB": FB, "FR": FR, "chosen": chosen, "eq0": msC[0]["eq"], "iv0": msC[0]["iv"]}, open(os.path.join(WORK, f"{ST.KEY}_run.pkl"), "wb"))
    log(f"[完] {ST.NAME}｜{VERD}｜{time.time() - t00:.0f}s")
    return SUM


def run_arms_generic(W, arms, segp, upto, procs, log, fake_seed=False):
    _G["W"] = W; _G["ARMS"] = {nm: (F, real, pick, cb) for nm, F, real, pick, reps, cb in arms}
    _G["upto"] = upto; _G["segp"] = segp
    jobs = []
    for nm, F, real, pick, reps, cb in arms:
        if fake_seed and nm.startswith("假訊號#"):
            jobs.append((nm, int(nm.split("#")[1])))
        else:
            jobs += [(nm, r) for r in range(1 if pick else reps)]
    out = {}
    t0 = time.time()
    with Pool(procs) as pool:
        for i, (nm, r, m) in enumerate(pool.imap_unordered(_armjob, jobs, chunksize=2)):
            out.setdefault(nm, []).append(m)
            if i % 100 == 0:
                log(f"[引擎] {i + 1}/{len(jobs)}｜{time.time() - t0:.0f}s")
    for nm in out:
        out[nm].sort(key=lambda z: z["r"])
    log(f"[引擎] 完 {len(jobs)} 顆｜{time.time() - t0:.0f}s")
    return out

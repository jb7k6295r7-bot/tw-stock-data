# -*- coding: utf-8 -*-
"""PREREG好營收再加漲停 seq2（台股策略線登錄 sha 8ac33880a1527851，2026-10-10 23:38；裁定 seq326 §二發號、N_組合 ＋1（E1／E2 兩格挑 1）；
事後重切 ⇒ 最多暫定）——回測線計算子代理。⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevLimitUp run [--procs 2] [--reps 200] [--fake 200] [--smoke]
    ...                                                      -m backtest.researchRevLimitUp page          # 網頁 backtest/好營收再加漲停.html
    抽樣查核（獨立寫法）：... -m backtest.researchRevLimitUp_check

⭐ 讀法寫死時間：見 TIME（台北）；寫死前 ⛔ 沒算任何本件數字（只看過登錄全文 seq2、裁定 seq326、情報 #26 全文（事件層數字本來就看過 ⇒ 登錄已標事後重切）、
   既有程式（researchPRE5core 快照、researchF4Launch、researchYLmargin）與資料格式）。

═══ 讀法（M 標；登錄沒寫清楚、執行者補的都在這裡）═══
 M1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ 8ac33880a1527851 才跑（信箱只讀）
 M2 版面（＝ researchPRE5core C2 同一組）：主段 ＝ rerun17 快照 H2D（edc6f8002f；日曆 2015-01-05～2026-09-24）；早年 ＝ ~/earlydata/eotc_f65bb03e11/otc/data
    （上市＋上櫃；日曆 2004-02-11～2014-12-31；⚠ 上櫃日 K 2007-07 起）；股票 ＝ UG.gate3（GATE_V2 開）∩ 四碼、首碼 1～9、非 91xx；⭐ 含已下市
    價格 ＝ D.load_stock（還原），收盤 ffill；月營收、產業、交易所除權息表 ＝ tw-stock-data origin/main（執行時 sha）git archive 到 ~/rluwork（唯讀）
 M3 母體（決策日 d ＝ 漲停那天，用 d 收盤以前的資料）：d 有 K 棒 ∧ UG.pit_valid(d) ∧ amt20(d) ≥ 5,000 萬（含 d 的最近 20 根有效 K 棒原始成交金額平均；
    不足 20 根 ⇒ 不在母體；登錄「前 20 日」讀成含 d，同 researchPRE5core C3）∧ 產業不是「金融保險」「生技醫療業」（industry_pit 的 pit 版在 d；
    早年合併類「化學生技醫療」分不開 ⇒ 不剔，筆數照報）
    R1 排名版（描述，seq323 例外下 R1 只照報）：d 當天「四碼 ∧ 有 K 棒 ∧ pit_valid ∧ 非金融生技」依 amt20 由大到小前 X%；X ＝ 2016-01-04 上述 5,000 萬母體檔數 ÷ 同日全市場檔數
 M4 好營收：期別 M 的當月營收 ＞ 前 23 期（M−23～M−1）有值者的最大值；⭐ 補讀法（照 p4_features.rev_hi24_flags 的缺值三分法，窗改 23）：
    M 沒值 ⇒ 不明（不算）；該股首期到 M 不足 23 期（且首期不是面板第一期）⇒ 不成立；前 23 期有值 ＜ 18 期 ⇒ 不明（不算）
 M5 可用日 t0 ＝ research34.rebalance_dates（M ≤ 2025-12：M＋1 月 10 日之後第一個交易日；M ≥ 2026-01：15 日之後；嚴格大於）；
    觀察窗 ＝ 日曆位置 t0, t0＋1, …, t0＋19（20 個交易日）；窗內每天 d：d 有 K 棒 ∧ 母體 ∧ 漲停 ⇒ 第一個這樣的 d 就是該股該營收月的訊號（之後不再取）
    進場 e ＝ d＋1（日曆次一交易日）開盤；e 超出日曆 ⇒ 不進
 M6 漲停（裁定 seq326 §二）：
    官方 ＝ tw-stock-data data/universe/exright（2015 起）＋ data/early/exright（2003～2014）的 limit_up（上市除權息事件日才有；上櫃表沒有這欄）：
      d 有一列 ∧ limit_up 是數字且不是哨兵（≥ 9999 ⇒ 無漲跌幅限制 ⇒ 官方不適用、走備援，筆數照報）⇒ 漲停 ＝ 原始收盤 ≥ limit_up − 1e−6
    備援 ＝ 還原收盤日報酬（對前一根有效 K 棒）≥ +9.5%（d ＜ 2015-06-01 ⇒ ≥ +6.5%）
    ⇒ 有官方就以官方為準，沒有就用備援；兩者在「官方可判」的日子不一致的筆數照報（窗內母體股-日、訊號兩層）
 M7 出場（seq308 §四：條件出場、⛔ 不設最長天數）：
    E1：e 之後每個 t0(M′)（M′ ＞ M、t0(M′) ＞ e）：該股 M′ 的好營收旗標（M4）不是「成立」（不成立、不明、沒值都算）⇒ t0(M′) 起第一個可成交開盤賣
       （⭐ 補讀法：t0(M′) ≤ e 的那幾期（月營收窗 20 天可能跨過下一期可用日）不檢查，因為買進當下那期已公布、登錄的進場條件沒看它）
    E2：e 起（含 e 收盤）持有期最高收盤 × 0.8 ≥ 當日收盤 ⇒ 次一交易日起第一個可成交開盤賣
    資料尾還沒出場 ⇒ 未完（墊檔日、以最後收盤計值、不賣；只影響窗外，窗尾持有照報）；停止交易 ⇒ 引擎 stop_force
 M8 引擎 research11.simulate_mtm（rule "F"）：10 槽、slot ＝ 前一日權益 ÷ 10、候選多於空位 ⇒ rng.permutation（default_rng(20261010＋r)）、
    同一檔已持有 ⇒ 不再進、⛔ 不遞補；停止交易強制出場：開；成本 0.585%／來回（引擎出場一次扣）；200 顆種子報中位
    現實版（researchSlip「現實版」逐字、N＝10，＝ researchPRE5core C6）：C1 每邊 ＋0.3%；C2 單邊衝擊 σ20 × √(5 萬 ÷ ADV20)；C3 一字漲停買不到（名額持現金、不遞補）、
      停牌買不到、一字跌停賣不掉（延到第一個賣得掉的開盤）；C4 進出價 ＝ (開＋高＋低＋收)÷4；C5 低消 20 元加 0（照報）；引擎 tradable＋delist
    ⭐ 主要參考 ＝ 現實版（登錄 §三、裁定 seq326 §二）；0.585% 版同表並報
 M9 段：主窗 2017-03-02～2026-08-24（rerun17 win 讀法：進場日在窗內、窗首全現金）；探索 2017-03-02～2021-12-30；確認 2022-01-03～2026-08-24
    ＝ 同一條權益曲線切窗；「資料尾」讀成主窗尾 2026-08-24（0050 錨同窗）；出場判斷用到 2026-09-24
    早年 2005～2014（early 版面；月營收覆蓋：PRE.coverage 每年各市場平均 ＜ 90% 的年份不可判定 ⇒ 早年判定窗從「其後各年都 ≥ 90%」的第一年起；
    IFRS（2013）只照報占比、不剔；漲停門檻 2015-06 前 6.5%）
    ⚠ 覆蓋率依 researchPRE5core C14 原文「上市」判（上櫃照報）；這一句是 1/7 子樣本冒煙（輸出在 ~/rluwork/smoke，數字不是本件結果）看到上櫃 2013～2014
      覆蓋 88～89% 時補寫的（原稿誤寫成各市場都要 ≥ 90%），在任何正式數字之前
 M10 退化（裁定 seq325；登錄必報）：⭐ 先算持股與現金、先寫 degeneracy.json（附台北時間）再彙總任何報酬；平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）
     ⇒ 該格照登錄排除並列出；挑格只在探索段非退化格中挑（全退化 ⇒ 照 researchPRE5core C9 在全部格裡挑、標「全退化」）
 M11 挑格（0.585% 版）：探索段非退化格中合格者取比值最大；沒有合格 ⇒ 取比值最大（照報它在探索段不合格）；平手 ⇒ 年化高、格序（E1、E2）
     判定（使用者判準，對 0050 同段）：合格 ＝ 年化中位 ＞ 0050 且 年化中位 ÷ |回落中位| ≥ 0050；另列 ＝ 只過年化；其餘不合格
     挑中格在確認段與早年段（可判時）的標籤兩段取較嚴；事後重切 ⇒ 兩段都合格也最多「暫定」、只進前瞻紀錄；現實版同表並報標籤
 M12 假訊號臂（挑中格；researchPRE5core C11）：每個進場日 e 的訊號數不變 ⇒ 改成 e−1 母體裡隨機同數量的股（e 要有有效開盤），持有天數從挑中格（已完成）
     的「進場 → 出場」日曆位置差等機率抽，到期日起第一個有效開盤賣；抽樣 default_rng([20261011, r])；200 抽、第 r 抽配組合種子 r；p ＝ 假訊號年化 ≥ 挑中格年化中位 的比例
 M13 描述（⛔ 不判、不計 N；挑中格同進場、各 50 顆）：固定持有 {20, 60, 120} 根（第 H 根收盤出）；R1 排名版；0050 在 200 日線上才買（決策日 d：0050 還原收盤 ＞ 含 d 的 200 日均線）
     ⚠ 0050 濾網的角色（seq321 §五）：「擋長空頭、不是急跌保護」
 M14 必報：等效獨立檔數（r＝0，換股日持股 N、ρ ＝ 前 60 日收盤日報酬兩兩相關平均、N_eff ＝ N ÷ (1＋(N−1)ρ)）；最大產業占幾檔（industry_pit 單層）；
     現金比例；持有天數分佈；各出場原因次數；窗尾仍持有；一年內先跌 15%（250 日內收盤先碰 ≤ 進場價 × 0.85，早於 ≥ × 1.15）；
     漲停隔天買不到（一價到底）：訊號層 e 開盤鎖漲停的筆數＋現實版引擎 tr_limit_up（種子中位）；滑價：隔天開盤跳空（o[e] ÷ c[d] − 1）、均價對開盤、C2 衝擊、現實版比 0.585% 版少幾點
     與營飆 v1、營量 v1 持股重疊率（逐日、r＝0；先驗 ②）；E1 年化 vs E2（先驗 ③）；各年報酬
 M15 營飆 v1、營量 v1 對照：段數字直接引 backtest/resultsYLmargin/cells.csv 的 fly|base、vol|base、slip_fly|base、slip_vol|base（同窗三段、T1、stop_force 開；
     該檔已有閘：不加條件 ＝ resultsT1fix 逐位元）；持股重疊用 researchT1fix.build_ctx(True) 重跑 r＝0（閘：eq_sha ＝ resultsT1fix c1／c13 t1 r0）
     好營收股價已認同（#17）：本件跑時尚未跑完 ⇒ 不列（照報）
 M16 結果句必附（登錄 §三）：「多重檢定邊緣（事件層 t ≈ 3.2 ＜ 3.33）」；「抽籤型、多數個股會跌（事件層個股中位 −1.05%）⇒ 要分散買才吃得到平均」
輸出 backtest/resultsRevLimitUp/：degeneracy.json（先寫）、summary.json、grid.csv、seeds.csv.gz、signals.csv.gz、run.log；網頁 backtest/好營收再加漲停.html；大檔 ~/rluwork/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import pickle
import subprocess
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

TIME = "2026-10-11 00:09（台北）"
REG_SHA = "8ac33880a1527851"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsRevLimitUp")
PAGE = os.path.join(HERE, "好營收再加漲停.html")
WORK = os.path.expanduser("~/rluwork")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
PARTS = ["data/meta/industry_hist", "data/meta/industry.csv", "data/meta/stocks.csv", "data/mops/revenue_hist", "data/early/revenue",
         "data/universe/exright", "data/early/exright"]
SEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "主窗": ("2017-03-02", "2026-08-24")}
EARLY = ("2005-01-03", "2014-12-30")
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
WIN = 20
REVW, REVMIN = 23, 18
LU_NEW, LU_OLD, LU_CUT = 0.095, 0.065, pd.Timestamp("2015-06-01")
E2_DD = 0.20
CELLS = ["E1", "E2"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ tw-stock-data（月營收、產業、除權息表）═════════════
def tw_data(log):
    if "DATA" in _G:
        return _G["sha"], _G["DATA"]
    sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.join(WORK, f"tw_{sha[:12]}")
    if not os.path.exists(os.path.join(root, "DONE")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, "DONE"), "w").write(sha)
    _G.update(sha=sha, DATA=os.path.join(root, "data"))
    log(f"[tw-stock-data] origin/main {sha[:10]} ⇒ {_G['DATA']}")
    return _G["sha"], _G["DATA"]


def load_rev(log):
    if "rev" in _G:
        return _G
    sha, DATA = tw_data(log)
    rv, rly, cat, mk, nf, nr = PRE.load_rev(DATA)
    _G.update(rev=rv, rev_ly=rly, cat=cat, PIT=PRE.PIT(DATA, cat), rev_nfiles=nf, rev_nrows=nr)
    _G["HI"] = hi23(rv)
    log(f"[月營收] {nf} 檔、{nr:,} 列；期別 {rv.index[0]}～{rv.index[-1]}；代號 {rv.shape[1]}")
    return _G


def hi23(rev):
    """M4：period × sid ⇒ 1.0 成立／0.0 不成立／NaN 不明。"""
    vals = rev.to_numpy(float); P, S = vals.shape
    out = np.full((P, S), np.nan)
    for j in range(S):
        v = vals[:, j]; rep = np.flatnonzero(np.isfinite(v))
        if not len(rep):
            continue
        fk = int(rep[0])
        for k in rep:
            if fk > 0 and k - fk < REVW:
                out[k, j] = 0.0; continue
            if k < REVW:
                continue
            h = v[k - REVW:k]; h = h[np.isfinite(h)]
            if len(h) < REVMIN:
                continue
            out[k, j] = 1.0 if v[k] > h.max() else 0.0
    return pd.DataFrame(out, index=rev.index, columns=rev.columns)


def load_exright(log):
    """M6：{(sid, 'YYYY-MM-DD'): limit_up(float，哨兵 ⇒ inf)}（上市）。"""
    if "EXR" in _G:
        return _G["EXR"]
    _, DATA = tw_data(log)
    fs = sorted(glob.glob(os.path.join(DATA, "universe", "exright", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "early", "exright", "*.csv")))
    out = {}; nsent = 0; nrow = 0
    for f in fs:
        x = pd.read_csv(f, dtype=str)
        if "limit_up" not in x:
            continue
        for s, d, lu in zip(x["stock_id"].str.strip(), x["date"].str.strip(), x["limit_up"]):
            v = pd.to_numeric(str(lu).replace(",", ""), errors="coerce")
            if not np.isfinite(v):
                continue
            nrow += 1
            if v >= 9999:
                v = np.inf; nsent += 1
            out[(s, d)] = float(v)
    _G["EXR"] = out
    _G["EXR_info"] = {"檔": len(fs), "列（limit_up 有值）": nrow, "哨兵（無漲跌幅限制）": nsent}
    log(f"[除權息表] {_G['EXR_info']}")
    return out


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
    ret = np.full(n, np.nan)
    ret[idx[1:]] = c0[idx[1:]] / c0[idx[:-1]] - 1.0
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close", "market"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"])
    rc = pd.to_numeric(raw["close"], errors="coerce").reindex(cal).to_numpy(float)
    mkt = raw["market"].reindex(cal).ffill().fillna("").to_numpy()
    X = SL.stock_extra(sid, mk, cal, n)
    pv = UG.pit_valid(sid, cal, D.DATA)
    imp = X["sig20"] * np.sqrt(CAP_Q / X["adv20"])
    return sid, {"c": c, "o": np.where(np.isfinite(o) & (o > 0), o, np.nan), "bar": bar, "a20": a20, "rc": rc, "ret": ret, "pv": np.asarray(pv, bool),
                 "tw": np.array([m == "twse" for m in mkt]), "avg": X["avg"], "imp": np.where(np.isfinite(imp), imp, np.nan), "trd": X["trd"],
                 "upl": X["up_o"], "dnl": X["dn_o"], "dnc": X["dn_c"]}


KEYS = ("c", "o", "bar", "a20", "rc", "ret", "pv", "tw", "avg", "imp", "trd", "upl", "dnl", "dnc")


class World:
    def __init__(self, part, procs, log):
        os.makedirs(WORK, exist_ok=True)
        self.part = part
        self.data = RR.H2D if part == "main" else EOTC
        D.DATA = self.data
        cal = D.load_calendar(); n = len(cal)
        cp = os.path.join(WORK, f"world_{part}.pkl")
        if os.path.exists(cp):
            Z = pickle.load(open(cp, "rb")); log(f"[版面 {part}] 讀快取")
        else:
            st = pd.read_csv(os.path.join(self.data, "meta", "stocks.csv"), dtype=str)
            U = UG.gate3(st)
            U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
            _G["cal"] = cal; t0 = time.time(); res = {}
            with Pool(procs) as pool:
                for i, (sid, v) in enumerate(pool.imap_unordered(_wjob, list(zip(U["stock_id"], U["market"])), chunksize=8)):
                    if v is not None:
                        res[sid] = v
                    if i % 400 == 0:
                        log(f"[版面 {part}] {i}/{len(U)}｜{time.time() - t0:.0f}s")
            sids = sorted(res)
            Z = {"sids": sids, "n_gate3": int(len(U))}
            for k in KEYS:
                Z[k] = np.vstack([res[s][k] for s in sids])
            pickle.dump(Z, open(cp, "wb"), protocol=5)
            log(f"[版面 {part}] {len(sids)} 檔（gate3∩四碼 {len(U)}）｜{time.time() - t0:.0f}s")
        self.cal = cal; self.n = n; self.sids = Z["sids"]; self.ix = {s: i for i, s in enumerate(self.sids)}; self.S = len(self.sids)
        for k in KEYS:
            setattr(self, k.upper(), Z[k])
        self.n_gate3 = Z["n_gate3"]
        self.bench = RR.load_bench(cal)
        self.MKT = self.BAR & self.PV & np.isfinite(self.A20)
        self.CP = np.hstack([self.C, self.C[:, -1:]])
        self.OP = np.hstack([self.O, np.full((self.S, 1), np.nan)])
        self.AVP = np.hstack([self.AVG, np.full((self.S, 1), np.nan)])
        self.TRP = np.hstack([self.TRD, np.zeros((self.S, 1), bool)])
        self.UPP = np.hstack([self.UPL, np.zeros((self.S, 1), bool)])
        self.okb = [np.flatnonzero(self.BAR[i] & np.isfinite(self.O[i])) for i in range(self.S)]
        self.okr = [np.flatnonzero(self.TRD[i] & ~self.DNL[i] & np.isfinite(self.AVG[i]) & (self.AVG[i] > 0)) for i in range(self.S)]
        try:
            off = TR.load_official()
        except Exception:
            off = {}
        self.dl = TR.delist_status({s: {"trd": self.TRD[i]} for i, s in enumerate(self.sids)}, cal, official=off)
        self.cache = {}

    def pos(self, d):
        return int(self.cal.searchsorted(pd.Timestamp(d)))

    def segpos(self, a, b):
        return self.pos(a), int(self.cal.searchsorted(pd.Timestamp(b), side="right")) - 1

    def exit_open(self, i, x, real):
        arr = self.okr[i] if real else self.okb[i]
        j = int(np.searchsorted(arr, x))
        if j >= len(arr):
            return None
        xp = int(arr[j])
        return xp, float(self.AVG[i, xp] if real else self.O[i, xp])

    def exit_close(self, i, y, real):
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


def industry_at(W, i, d, log=print):
    k = ("ind", i, d)
    if k not in W.cache:
        W.cache[k] = load_rev(log)["PIT"]._at(W.sids[i], W.cal[d], "pit")[0]
    return W.cache[k]


def fb_matrix(W, log):
    """M3：金融／生技（S×n）與舊合併類（化學生技醫療）旗標；產業逐月月初判一次、月內沿用（industry_pit 段落換類以日為單位，月內換類照月初）。"""
    cp = os.path.join(WORK, f"fb_{W.part}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    P = load_rev(log)["PIT"]
    mon = np.array([d.year * 100 + d.month for d in W.cal]); first = np.flatnonzero(np.r_[True, mon[1:] != mon[:-1]])
    FB = np.zeros((W.S, W.n), bool); OLD = np.zeros((W.S, W.n), bool)
    for i, s in enumerate(W.sids):
        for a, b in zip(first, list(first[1:]) + [W.n]):
            ind = P._at(s, W.cal[a], "pit")[0]
            if ind in EXCL_FB:
                FB[i, a:b] = True
            elif ind == "化學生技醫療":
                OLD[i, a:b] = True
    pickle.dump((FB, OLD), open(cp, "wb"), protocol=5)
    return FB, OLD


# ═════════════ 訊號 ═════════════
def lu_matrix(W, log):
    """M6：(LU 最終, 官方可判, 官方判, 備援判)。"""
    EXR = load_exright(log)
    thr = np.where(W.cal < LU_CUT, LU_OLD, LU_NEW)
    with np.errstate(invalid="ignore"):
        FBK = (W.RET >= thr[None, :] - 1e-12) & W.BAR
    OFFA = np.zeros_like(FBK); OFF = np.zeros_like(FBK); SENT = 0
    dstr = np.array([str(d.date()) for d in W.cal]); dix = {d: k for k, d in enumerate(dstr)}
    for (s, d), lu in EXR.items():
        i = W.ix.get(s); k = dix.get(d)
        if i is None or k is None or not W.BAR[i, k]:
            continue
        if not np.isfinite(lu):
            SENT += 1; continue
        if not W.TW[i, k]:
            continue
        OFFA[i, k] = True; OFF[i, k] = bool(W.RC[i, k] >= lu - 1e-6)
    LU = np.where(OFFA, OFF, FBK)
    return LU, OFFA, OFF, FBK, SENT


def build_signals(W, U, log, tag=""):
    """M4～M6：⇒ 訊號列 DataFrame（s、d、e、M、t0、官方可判、官方、備援）＋ 計數。"""
    G = load_rev(log); HI = G["HI"]
    periods = list(HI.index)
    rd = {**R34.rebalance_dates([M for M in periods if M <= "2025-12"], W.cal, 10), **R34.rebalance_dates([M for M in periods if M >= "2026-01"], W.cal, 15)}
    T0 = {M: e for M, (_, e) in rd.items()}
    key = ("lu",)
    if key not in W.cache:
        W.cache[key] = lu_matrix(W, log)
    LU, OFFA, OFF, FBK, SENT = W.cache[key]
    cols = {s: j for j, s in enumerate(HI.columns)}
    hcol = np.array([cols.get(s, -1) for s in W.sids]); has = hcol >= 0
    HV = HI.to_numpy(float)
    rows = []
    stat = {"窗內母體股-日": 0, "其中漲停（最終）": 0, "官方可判股-日": 0, "官方判漲停": 0, "備援判漲停（官方可判日）": 0, "官方與備援不一致": 0,
            "官方是、備援否": 0, "官方否、備援是": 0, "好營收（股-期）": 0}
    for M in periods:
        t0 = T0.get(M)
        if t0 is None:
            continue
        k = periods.index(M)
        good = np.zeros(W.S, bool); good[has] = HV[k, hcol[has]] == 1.0
        if not good.any():
            continue
        a, b = t0, min(t0 + WIN, W.n - 1)          # d ≤ n−2（e ＝ d＋1 要在日曆內）
        if a >= b:
            continue
        stat["好營收（股-期）"] += int(good.sum())
        m = U[:, a:b] & good[:, None]
        lu = LU[:, a:b] & m
        stat["窗內母體股-日"] += int(m.sum()); stat["其中漲停（最終）"] += int(lu.sum())
        oa = OFFA[:, a:b] & m
        stat["官方可判股-日"] += int(oa.sum()); stat["官方判漲停"] += int((OFF[:, a:b] & oa).sum())
        stat["備援判漲停（官方可判日）"] += int((FBK[:, a:b] & oa).sum())
        stat["官方是、備援否"] += int((OFF[:, a:b] & ~FBK[:, a:b] & oa).sum()); stat["官方否、備援是"] += int((~OFF[:, a:b] & FBK[:, a:b] & oa).sum())
        for i in np.flatnonzero(lu.any(axis=1)):
            j = int(np.argmax(lu[i])); d = a + j
            rows.append((int(i), d, d + 1, M, t0, bool(OFFA[i, d]), bool(OFF[i, d]), bool(FBK[i, d])))
    stat["官方與備援不一致"] = stat["官方是、備援否"] + stat["官方否、備援是"]
    stat["除權息表哨兵（無漲跌幅限制，走備援）股-日（全表）"] = SENT
    F = pd.DataFrame(rows, columns=["s", "d", "e", "M", "t0", "官方可判", "官方", "備援"])
    F = F.sort_values(["e", "s"]).reset_index(drop=True)
    return F, stat, T0


def exit_rows(W, F, T0, cell):
    """M7 ⇒ rows（s、e、xk、x、why、key）。"""
    HI = _G["HI"]; periods = list(HI.index); cols = {s: j for j, s in enumerate(HI.columns)}; HV = HI.to_numpy(float)
    pidx = {M: k for k, M in enumerate(periods)}
    t0s = sorted((t, M) for M, t in T0.items())
    out = []
    for s, e, M in zip(F["s"], F["e"], F["M"]):
        s, e = int(s), int(e)
        x, why = -1, "未完"
        if cell == "E1":
            j = cols.get(W.sids[s], -1)
            for t, M2 in t0s:
                if M2 <= M or t <= e:
                    continue
                f = HV[pidx[M2], j] if j >= 0 else np.nan
                if f != 1.0:
                    x = t; why = "營收不再創新高" if f == 0.0 else "營收不明／沒值"
                    break
        else:
            c = W.C[s, e:]; rm = np.maximum.accumulate(c)
            w = np.flatnonzero(c <= rm * (1 - E2_DD) + 1e-12)
            if len(w):
                x = e + int(w[0]) + 1; why = "回落20%"
                if x >= W.n:
                    x, why = -1, "未完"
        out.append((s, e, "open", x, why, np.nan))
    return pd.DataFrame(out, columns=["s", "e", "xk", "x", "why", "key"])


def finalize_rows(W, rows, real):
    out = []
    for r in rows.itertuples(index=False):
        i, e = int(r.s), int(r.e)
        ep = W.AVG[i, e] if real else W.O[i, e]
        if real and not (np.isfinite(ep) and ep > 0):
            out.append((i, e, e + 1, 0.0, "進場日無均價", 0, np.nan)); continue
        if not np.isfinite(ep):
            continue
        res = None
        if r.x is not None and 0 <= r.x < W.n:
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
        out.append((i, e, int(xp), float(g), why, end, float(ep)))
    F = pd.DataFrame(out, columns=["s", "e", "xpos", "g", "why", "end", "ep"])
    F["sid"] = [W.sids[i] for i in F["s"]]
    return F


# ═════════════ 引擎 ═════════════
def _sf(W, upto):
    k = ("sf", upto)
    if k not in W.cache:
        W.cache[k] = R.stop_force_days({s: W.BAR[i] for i, s in enumerate(W.sids)}, upto)
    return W.cache[k]


def sim(W, F, real, r, upto, seed0=SEED0):
    sig = pd.DataFrame({"sid": F["sid"].to_numpy(), "entry_pos": F["e"].to_numpy(int), "xpos_F": F["xpos"].to_numpy(int), "g_F": F["g"].to_numpy(float)})
    sids = sorted(set(sig["sid"]))
    closes = {s: W.CP[W.ix[s]] for s in sids}
    opens = {s: (W.AVP if real else W.OP)[W.ix[s]] for s in sids}
    SF = {s: L for s, L in _sf(W, upto).items() if s in closes}
    kw = {}
    if real:
        z = np.zeros(W.n + 1, bool)
        kw["tradable"] = {s: {"trd": W.TRP[W.ix[s]], "up_o": W.UPP[W.ix[s]], "dn_o": z, "dn_c": z} for s in sids}
        kw["delist"] = {s: W.dl[s] for s in sids if s in W.dl}
    au = []
    R.COST = COST_R if real else COST_B
    try:
        o = R.simulate_mtm(sig, "F", 10, np.random.default_rng(seed0 + r), closes, opens, W.n + 1, return_equity=True, audit=au, stop_force=SF, **kw)
    finally:
        R.COST = COST_B
    return o, au


def holdings(au, n):
    op, iv = {}, []
    for x in sorted(au, key=lambda z: (z["t"], z["side"] != "sell")):
        if x["side"] == "buy":
            op[x["sid"]] = (int(x["t"]), float(x["amt"]), float(x["px"]))
        elif x["side"] == "sell" and x["sid"] in op:
            t0, a, p = op.pop(x["sid"]); iv.append((x["sid"], t0, int(x["t"]), a, p))
    for s, (t0, a, p) in op.items():
        iv.append((s, t0, n, a, p))
    return iv


def _armjob(args):
    nm, r = args
    W = _G["W"]; F, real = _G["ARMS"][nm]
    o, au = sim(W, F, real, r, _G["upto"])
    n = W.n + 1; nh = np.zeros(n); iv = holdings(au, n)
    for s, t0, t1, a, p in iv:
        nh[t0:t1] += 1
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        cash = 1 - hv / eq
    hold = {}
    for k, (a, b) in _G["segp"].items():
        hold[f"{k}_平均持股"] = float(nh[a:b + 1].mean()); hold[f"{k}_平均現金"] = float(np.nanmean(cash[a:b + 1]))
    m = {"r": r, "hold": hold, "eq": eq, "first": int(o["first"]), "end": int(o["end"]), "iv": iv, "sf_n": int(o.get("x_stop_force_n", 0)),
         "lu": int(o.get("tr_limit_up", 0)), "halt_in": int(o.get("tr_halt_in", 0)), "trades": int(o.get("trades", 0))}
    return nm, r, m


def run_arms(W, arms, segp, upto, procs, log):
    """arms：[(名, F, real, reps 或 ('fake', r))]"""
    _G["W"] = W; _G["ARMS"] = {nm: (F, real) for nm, F, real, _ in arms}; _G["upto"] = upto; _G["segp"] = segp
    jobs = []
    for nm, F, real, reps in arms:
        jobs += [(nm, reps[1])] if isinstance(reps, tuple) else [(nm, r) for r in range(reps)]
    out = {}; t0 = time.time()
    with Pool(procs) as pool:
        for i, (nm, r, m) in enumerate(pool.imap_unordered(_armjob, jobs, chunksize=2)):
            out.setdefault(nm, []).append(m)
            if i % 100 == 0:
                log(f"[引擎] {i + 1}/{len(jobs)}｜{time.time() - t0:.0f}s")
    for nm in out:
        out[nm].sort(key=lambda z: z["r"])
    log(f"[引擎] 完 {len(jobs)} 顆｜{time.time() - t0:.0f}s")
    return out


# ═════════════ 彙總工具 ═════════════
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


def seg_ret(m, segs):
    out = {}
    for k, (a, b) in segs.items():
        c, d, _ = RR.win_metrics(m["eq"], m["first"], m["end"], a, b)
        out[f"{k}_年化"] = float(c); out[f"{k}_回落"] = float(d)
    return out


def summarize(ms, Z, segs):
    row = {"種子": len(ms)}
    R_ = [seg_ret(m, segs) for m in ms]
    for sg in segs:
        cs = np.array([x[f"{sg}_年化"] for x in R_]); ds = np.array([x[f"{sg}_回落"] for x in R_])
        c, d = float(np.nanmedian(cs)), float(np.nanmedian(ds))
        lab, rt = label(c, d, Z[sg])
        row.update({f"{sg}_年化": c, f"{sg}_回落": d, f"{sg}_比值": rt, f"{sg}_標籤": lab, f"{sg}_年化p10": float(np.nanpercentile(cs, 10)),
                    f"{sg}_年化p90": float(np.nanpercentile(cs, 90)), f"_{sg}_all": cs})
    return row


def hold_only(ms, segs):
    out = {}
    for sg in segs:
        out[f"{sg}_平均持股"] = float(np.median([m["hold"][f"{sg}_平均持股"] for m in ms]))
        out[f"{sg}_平均現金"] = float(np.median([m["hold"][f"{sg}_平均現金"] for m in ms]))
    return out


def degen(h, sg):
    return bool(h[f"{sg}_平均持股"] < 3 or h[f"{sg}_平均現金"] > 0.30)


def q_(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "平均": float(x.mean()), "中位": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p25": float(np.percentile(x, 25)),
            "p75": float(np.percentile(x, 75)), "p90": float(np.percentile(x, 90))}


def years_ret(eq, cal, a0, b0, bench=False):
    out = {}
    for y in sorted(set(cal[a0:b0 + 1].year)):
        a = max(a0 - 1, int(cal.searchsorted(pd.Timestamp(y, 1, 1))) - 1); b = min(b0, int(cal.searchsorted(pd.Timestamp(y + 1, 1, 1))) - 1)
        out[str(y)] = float(eq[b] / eq[a] - 1)
    return out


def trade_stats(W, ms, F, w1):
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
                tl += 1; tailh.append(w1 - t0 + 1); continue
            hold.append(t1 - t0)
            w = row["why"] if t1 == int(row["xpos"]) else "停止交易強制出場／延後"
            why[w] = why.get(w, 0) + 1
            s = int(row["s"]); ep = float(row["ep"])
            if t0 + 250 <= W.n - 1:
                cc = W.C[s, t0 + 1:t0 + 251]
                up = np.flatnonzero(cc >= ep * 1.15); dw = np.flatnonzero(cc <= ep * 0.85)
                dn.append((dw[0] if len(dw) else 999) < (up[0] if len(up) else 999))
        tail.append(tl)
    R_ = max(len(ms), 1)
    return {"每顆平均買進筆（窗內）": nb / R_, "持有天數（交易日，已出場，種子合計）": q_(hold),
            "出場原因（每顆平均）": {k: v / R_ for k, v in sorted(why.items(), key=lambda z: -z[1])},
            "窗尾仍持有（檔，種子中位）": float(np.median(tail)) if tail else np.nan, "窗尾仍持有已持有天數": q_(tailh),
            "一年內先跌15%比例": float(np.mean(dn)) if dn else np.nan, "觀察窗滿250筆": len(dn)}


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


def neff_stats(W, m0, segs, log):
    iv = m0["iv"]; days = sorted({t0 for s, t0, t1, a, p in iv})
    res = eff_n(W, iv, days); out = {}
    for sg, (a, b) in segs.items():
        rr = [x for x in res if a <= x[0] <= b]
        if not rr:
            continue
        mx = []
        for t, N, rho, ne, held in rr:
            cnt = {}
            for s in held:
                ind = industry_at(W, W.ix[s], t, log) or "無類別"
                cnt[ind] = cnt.get(ind, 0) + 1
            mx.append(max(cnt.values()))
        out[sg] = {"換股日": len(rr), "平均持股": float(np.mean([x[1] for x in rr])), "平均ρ": float(np.nanmean([x[2] for x in rr])),
                   "平均N_eff": float(np.nanmean([x[3] for x in rr])), "N_eff中位": float(np.nanmedian([x[3] for x in rr])),
                   "最大產業檔數中位": float(np.median(mx)), "最大產業檔數最大": int(max(mx)), "最大產業＞3檔的換股日占比": float(np.mean(np.array(mx) > 3)),
                   "產業分類層": "上市櫃官方產業別（單層，industry_pit pit 版）"}
    return out


def overlap_daily(ivA, ivB, a, b):
    n = b + 1; HA = {}; HB = {}
    for s, t0, t1, *_ in ivA:
        for t in range(max(t0, a), min(t1, n)):
            HA.setdefault(t, set()).add(s)
    for s, t0, t1, *_ in ivB:
        for t in range(max(t0, a), min(t1, n)):
            HB.setdefault(t, set()).add(s)
    v = [len(HA[t] & HB.get(t, set())) / len(HA[t]) for t in HA if HA[t]]
    return float(np.mean(v)) if v else np.nan


def fake_rows(W, F, U, r):
    rng = np.random.default_rng([FSEED, r])
    hd = (F["xpos"] - F["e"])[F["end"] == 0].to_numpy(int)
    rows = []
    for e, g in F.groupby("e"):
        pool = np.flatnonzero(U[:, e - 1] & np.isfinite(W.O[:, e]))
        if not len(pool) or not len(hd):
            continue
        for s in rng.choice(pool, size=min(len(g), len(pool)), replace=False):
            rows.append((int(s), int(e), "open", int(e + int(rng.choice(hd))), "假訊號到期", np.nan))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def fixed_rows(W, F, H):
    rows = []
    for s, e in zip(F["s"], F["e"]):
        idx = np.flatnonzero(W.BAR[s, e:]) + e
        rows.append((int(s), int(e), "close", int(idx[H - 1]) if len(idx) >= H else -1, f"固定{H}根", np.nan))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def universe(W, log, r1=False):
    FB, OLD = fb_matrix(W, log)
    base = W.MKT & ~FB
    if not r1:
        return base & (np.nan_to_num(W.A20, nan=0.0) >= LIQ), OLD
    d = W.pos(R1_DAY) if W.part == "main" else None
    X = _G["R1X"]
    U = np.zeros_like(base)
    for k in range(W.n):
        ix = np.flatnonzero(base[:, k])
        if not len(ix):
            continue
        U[ix[np.argsort(-W.A20[ix, k], kind="stable")[:int(np.ceil(X * len(ix)))]], k] = True
    return U, OLD


def r1_x(W, log):
    FB, _ = fb_matrix(W, log)
    d = W.pos(R1_DAY); assert str(W.cal[d].date()) == R1_DAY
    mk = W.MKT[:, d] & ~FB[:, d]; u = mk & (W.A20[:, d] >= LIQ)
    return float(u.sum() / mk.sum()), int(u.sum()), int(mk.sum())


# ═════════════ 營飆 v1／營量 v1（M15）═════════════
def yl_ref(log):
    cp = os.path.join(WORK, "yl_r0.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    from backtest import researchT1fix as T
    from backtest import listexit_lines as L
    ctx = T.build_ctx(True)
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), ctx["w1"])
    out = {"cal": [str(ctx["cal"][0].date()), str(ctx["cal"][-1].date()), len(ctx["cal"])]}
    for fam in ("fly", "vol"):
        au = []
        if fam == "fly":
            o = L.sim(ctx, {"stop_force": SF}, 0, audit=au)
        else:
            o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                               pick="relvol", queue_days=0, return_equity=True, stop_force=SF, audit=au)
        eq = np.asarray(o["equity"], float)
        iv = holdings(au, len(eq))
        out[fam] = {"eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "trades": int(o["trades"]),
                    "iv": [(s, str(ctx["cal"][t0].date()), str(ctx["cal"][min(t1, len(ctx["cal"]) - 1)].date()) if t1 < len(ctx["cal"]) else "9999-12-31") for s, t0, t1, a, p in iv]}
    ref = pd.read_csv(os.path.join(HERE, "resultsT1fix", "seeds.csv.gz"), dtype={"eq_sha": str})
    gate = {}
    for fam, k in (("fly", "c1"), ("vol", "c13")):
        q = ref[(ref["key"] == k) & (ref["var"] == "t1") & (ref["r"] == 0)].iloc[0]
        gate[fam] = bool(str(q["eq_sha"]) == out[fam]["eq_sha"] and int(q["trades"]) == out[fam]["trades"])
    out["閘"] = gate
    pickle.dump(out, open(cp, "wb"), protocol=5)
    log(f"[營量營飆 r0] 閘（eq_sha、trades ＝ resultsT1fix t1 r0）{gate}")
    return out


def yl_cells():
    T_ = pd.read_csv(os.path.join(HERE, "resultsYLmargin", "cells.csv"), float_precision="round_trip")
    out = {}
    for k, nm in (("fly|base", "營飆 v1"), ("vol|base", "營量 v1"), ("slip_fly|base", "營飆 v1 現實版"), ("slip_vol|base", "營量 v1 現實版")):
        g = T_[T_["key"] == k].set_index("段")
        out[nm] = {s: {c: (float(g.at[s, c]) if c != "標籤" else str(g.at[s, c])) for c in ("年化", "回落", "比值", "標籤")} for s in g.index}
        out[nm]["種子"] = int(g["顆數"].iloc[0])
    return out


# ═════════════ 主流程 ═════════════
def run(a):
    global OUT, WORK
    if a.smoke:
        OUT = os.path.join(WORK, "smoke")
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchRevLimitUp run {now_tpe()}（台北）｜讀法寫死 {TIME}｜reps {a.reps} fake {a.fake} smoke {a.smoke} =====")
    regf = reg_check(); log(f"[sha] {REG_SHA} ✔ {regf}")
    t00 = time.time()
    load_rev(log); load_exright(log)
    WM = World("main", a.procs, log)
    seg = {k: WM.segpos(*v) for k, v in SEGS.items()}
    assert seg["主窗"] == (WM.pos("2017-03-02"), WM.pos("2026-08-24"))
    Z = {k: RR.bench_row(WM.cal, WM.bench, x, y + 1) for k, (x, y) in seg.items()}
    g0 = (repr(Z["主窗"]["cagr"]) == repr(ANCHOR[0]), repr(Z["主窗"]["mdd"]) == repr(ANCHOR[1]))
    log(f"[0050] 主窗錨逐位元 {g0}")
    if not all(g0):
        raise SystemExit("⛔ 0050 錨不對")
    w0, w1 = seg["主窗"]
    U, OLD = universe(WM, log)
    if a.smoke:
        U = U & (np.arange(WM.S) % 7 == 0)[:, None]
    SIG, LST, T0 = build_signals(WM, U, log)
    SIGw = SIG[(SIG["e"] >= w0) & (SIG["e"] <= w1)].reset_index(drop=True)
    log(f"[訊號] 全部 {len(SIG)}、主窗內 {len(SIGw)}｜{json.dumps(LST, ensure_ascii=False)}")
    FB_, FR_ = {}, {}
    for c in CELLS:
        rw = exit_rows(WM, SIGw, T0, c)
        FB_[c] = finalize_rows(WM, rw, False); FR_[c] = finalize_rows(WM, rw, True)
        log(f"[出場] {c}：base 可進 {len(FB_[c])}（e 無有效開盤剔 {len(rw) - len(FB_[c])}）、未完 {int(FB_[c]['end'].sum())}｜{FB_[c]['why'].value_counts().to_dict()}")
    # 訊號表存檔
    S_out = SIGw.copy(); S_out["sid"] = [WM.sids[i] for i in S_out["s"]]
    S_out["日期d"] = [str(WM.cal[d].date()) for d in S_out["d"]]; S_out["日期e"] = [str(WM.cal[e].date()) for e in S_out["e"]]
    S_out["t0日"] = [str(WM.cal[t].date()) for t in S_out["t0"]]
    S_out["跳空"] = [WM.O[s, e] / WM.C[s, d] - 1 for s, d, e in zip(S_out["s"], S_out["d"], S_out["e"])]
    S_out["e鎖漲停"] = [bool(WM.UPL[s, e]) for s, e in zip(S_out["s"], S_out["e"])]
    S_out["還原日報酬d"] = [WM.RET[s, d] for s, d in zip(S_out["s"], S_out["d"])]
    for c in CELLS:
        kk = {(int(s), int(e)): (x, g, w) for s, e, x, g, w in zip(FB_[c]["s"], FB_[c]["e"], FB_[c]["xpos"], FB_[c]["g"], FB_[c]["why"])}
        S_out[f"{c}_xpos"] = [kk.get((s, e), (np.nan, np.nan, ""))[0] for s, e in zip(S_out["s"], S_out["e"])]
        S_out[f"{c}_g"] = [kk.get((s, e), (np.nan, np.nan, ""))[1] for s, e in zip(S_out["s"], S_out["e"])]
        S_out[f"{c}_why"] = [kk.get((s, e), (np.nan, np.nan, ""))[2] for s, e in zip(S_out["s"], S_out["e"])]
    S_out.to_csv(os.path.join(OUT, "signals.csv.gz"), index=False, float_format="%.10g")
    # ── 主段臂 ──
    arms = []
    for c in CELLS:
        arms.append((f"{c}|b", FB_[c], False, a.reps)); arms.append((f"{c}|r", FR_[c], True, a.reps))
    RES = run_arms(WM, arms, seg, w1, a.procs, log)
    # ── 退化（先寫）──
    DG = {}
    for nm, ms in RES.items():
        h = hold_only(ms, seg)
        DG[nm] = {**h, "探索_退化": degen(h, "探索"), "確認_退化": degen(h, "確認"), "主窗_退化": degen(h, "主窗"), "種子": len(ms)}
    cand = {}
    for c in CELLS:
        g = FB_[c].groupby("e").size()
        cand[c] = {"有進場的日子": int(len(g)), "每個進場日訊號數": q_(g.to_numpy()),
                   "訊號數逐年（進場日）": {str(k): int(v) for k, v in pd.Series([WM.cal[e].year for e in FB_[c]["e"]]).value_counts().sort_index().items()}}
    DJ = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在彙總任何報酬之前寫入（M10、裁定 seq325）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）；退化格照登錄排除",
          "候選與訊號": cand, "持股與現金": DG,
          "排除的格": sorted({nm.split('|')[0] for nm, v in DG.items() if nm.endswith('|b') and v['探索_退化']})}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索 {v['探索_平均持股']:.2f} 檔／現金 {v['探索_平均現金']:.1%}、確認 {v['確認_平均持股']:.2f}／{v['確認_平均現金']:.1%}"
                                              f"{'（探索退化）' if v['探索_退化'] else ''}" for k, v in DG.items()))
    # ── 報酬、挑格 ──
    GRID = [{"格": nm.split("|")[0], "版本": nm.split("|")[1], **summarize(ms, Z, seg), **DG[nm]} for nm, ms in RES.items()]
    GR = pd.DataFrame(GRID)
    base = GR[GR["版本"] == "b"].copy(); base["_ord"] = [CELLS.index(c) for c in base["格"]]
    nd = base[~base["探索_退化"]]; all_deg = len(nd) == 0
    pool_ = nd if not all_deg else base
    qq = pool_[pool_["探索_標籤"] == "合格"]
    pick = (qq if len(qq) else pool_).sort_values(["探索_比值", "探索_年化", "_ord"], ascending=[False, False, True]).iloc[0]
    chosen = pick["格"]
    log(f"[挑格] 非退化 {len(nd)}／{len(base)}、探索合格 {len(qq)} ⇒ {chosen}{'（⚠ 全退化）' if all_deg else ''}")
    CH = {v: {k: x for k, x in GR[(GR["格"] == chosen) & (GR["版本"] == v)].iloc[0].to_dict().items() if not k.startswith("_")} for v in ("b", "r")}
    # ── 早年 ──
    EARLYR = early(a, chosen, log)
    lab_c, lab_cr = CH["b"]["確認_標籤"], CH["r"]["確認_標籤"]
    if EARLYR.get("窗"):
        lab_e = EARLYR["格"][f"{chosen}|b"]["早年_標籤"]; lab_er = EARLYR["格"][f"{chosen}|r"]["早年_標籤"]
    else:
        lab_e = lab_er = "不可判定"
    fin_b, fin_r = stricter(lab_c, lab_e) if lab_e != "不可判定" else lab_c, stricter(lab_cr, lab_er) if lab_er != "不可判定" else lab_cr
    tag = lambda L_: ("暫定（事後重切；只進前瞻紀錄）" if L_ == "合格" else L_)
    VERD = {"挑中格": chosen, "全退化": all_deg, "探索": CH["b"]["探索_標籤"], "確認": lab_c, "早年": lab_e, "判定": tag(fin_b),
            "現實版探索": CH["r"]["探索_標籤"], "現實版確認": lab_cr, "現實版早年": lab_er, "現實版判定（主要參考）": tag(fin_r)}
    log(f"[判定] {VERD}")
    # ── 對照與描述 ──
    Fc = FB_[chosen]
    darms = [(f"固定{H}", finalize_rows(WM, fixed_rows(WM, Fc, H), False), False, 50) for H in (20, 60, 120)]
    ma = pd.Series(WM.bench).rolling(200, min_periods=200).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        keep = WM.bench[Fc["e"].to_numpy(int) - 1] > ma[Fc["e"].to_numpy(int) - 1]
    darms.append(("0050在200日線上才買", Fc[keep].reset_index(drop=True), False, 50))
    X1, nu, nm_ = r1_x(WM, log); _G["R1X"] = X1
    UR1, _ = universe(WM, log, r1=True)
    if a.smoke:
        UR1 = UR1 & (np.arange(WM.S) % 7 == 0)[:, None]
    SR1, LR1, _ = build_signals(WM, UR1, log)
    SR1 = SR1[(SR1["e"] >= w0) & (SR1["e"] <= w1)].reset_index(drop=True)
    darms.append(("R1排名版", finalize_rows(WM, exit_rows(WM, SR1, T0, chosen), False), False, 50))
    for i in range(a.fake):
        darms.append((f"假訊號#{i}", finalize_rows(WM, fake_rows(WM, Fc, U, i), False), False, ("fake", i)))
    DRES = run_arms(WM, darms, seg, w1, a.procs, log)
    DESC = {nm: {**{k: v for k, v in summarize(ms, Z, seg).items() if not k.startswith("_")}, **hold_only(ms, seg)} for nm, ms in DRES.items() if not nm.startswith("假訊號#")}
    DESC["R1排名版"]["訊號（主窗）"] = int(len(SR1))
    FK = [summarize(ms, Z, seg) for nm, ms in DRES.items() if nm.startswith("假訊號#")]
    FAKE = {}
    for sg in SEGS:
        v = np.array([x[f"{sg}_年化"] for x in FK]); d_ = np.array([x[f"{sg}_回落"] for x in FK])
        FAKE[sg] = {"抽數": len(v), "年化中位": float(np.nanmedian(v)), "年化p10": float(np.nanpercentile(v, 10)), "年化p90": float(np.nanpercentile(v, 90)),
                    "回落中位": float(np.nanmedian(d_)), "p（假訊號年化 ≥ 挑中格）": float(np.mean(v >= CH["b"][f"{sg}_年化"])),
                    "假訊號合格比例": float(np.mean([label(c_, m_, Z[sg])[0] == "合格" for c_, m_ in zip(v, d_)]))}
    # ── 必報 ──
    msC = RES[f"{chosen}|b"]; msR = RES[f"{chosen}|r"]
    TS = {"b": trade_stats(WM, msC, Fc, w1), "r": trade_stats(WM, msR, FR_[chosen], w1)}
    TS_other = {c: trade_stats(WM, RES[f"{c}|b"], FB_[c], w1) for c in CELLS if c != chosen}
    NE = neff_stats(WM, msC[0], seg, log)
    YR = {k: float(np.median([years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msC])) for k in years_ret(msC[0]["eq"], WM.cal, w0, w1)}
    YRr = {k: float(np.median([years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msR])) for k in years_ret(msR[0]["eq"], WM.cal, w0, w1)}
    YR50 = years_ret(WM.bench, WM.cal, w0, w1)
    Y = yl_ref(log); YC = yl_cells()
    ovl = {}
    for fam, nmf in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        ivB = [(s, WM.pos(a_), WM.pos(b_) if b_ != "9999-12-31" else WM.n + 1) for s, a_, b_ in Y[fam]["iv"]]
        for sg, (x_, y_) in seg.items():
            ovl.setdefault(sg, {})[f"與{nmf}持股重疊率"] = overlap_daily(msC[0]["iv"], ivB, x_, y_)
            ovl[sg][f"與{nmf}持股重疊率（現實版 r0）"] = overlap_daily(msR[0]["iv"], ivB, x_, y_)
    # 滑價、漲停買不到
    Sw = S_out
    SLIP = {"訊號層（主窗內訊號）": {"隔天開盤跳空 o[e]÷c[d]−1": q_(Sw["跳空"]),
                                "均價對開盤 avg[e]÷o[e]−1": q_([WM.AVG[s, e] / WM.O[s, e] - 1 for s, e in zip(Sw["s"], Sw["e"])]),
                                "C2 進場衝擊（單邊）": q_([WM.IMP[s, e] for s, e in zip(Sw["s"], Sw["e"])]),
                                "e 開盤鎖漲停（一價到底）筆": int(Sw["e鎖漲停"].sum()), "訊號筆": int(len(Sw))},
            "引擎（現實版，種子中位）": {c: {"漲停買不到": float(np.median([m["lu"] for m in RES[f"{c}|r"]])),
                                         "停牌買不到": float(np.median([m["halt_in"] for m in RES[f"{c}|r"]]))} for c in CELLS},
            "現實版比 0.585% 版（年化點）": {c: {sg: (GR[(GR["格"] == c) & (GR["版本"] == "r")].iloc[0][f"{sg}_年化"] - GR[(GR["格"] == c) & (GR["版本"] == "b")].iloc[0][f"{sg}_年化"]) * 100
                                            for sg in SEGS} for c in CELLS}}
    LUJ = {"窗內母體股-日（主段、5,000 萬母體、好營收股）": LST,
           "訊號層（主窗內）": {"官方判定": int(Sw["官方可判"].sum()), "備援判定": int((~Sw["官方可判"]).sum()),
                            "官方可判訊號中備援也判漲停": int((Sw["官方可判"] & Sw["備援"]).sum()),
                            "不一致（官方是、備援否）": int((Sw["官方可判"] & Sw["官方"] & ~Sw["備援"]).sum())},
           "除權息表": _G["EXR_info"], "說明": "官方 ＝ 上市除權息事件日 exright.limit_up；上櫃沒有；TWT84U 尚未落地 ⇒ 其餘全走備援（還原收盤日報酬 ≥ 9.5%，2015-06 前 6.5%）"}
    SUM = {"meta": {"件": "PREREG好營收再加漲停 seq2", "登錄": regf, "sha": REG_SHA, "讀法寫死": TIME, "run": now_tpe() + "（台北）", "reps": a.reps, "fake": a.fake,
                    "smoke": bool(a.smoke), "版面": {"main": [str(WM.cal[0].date()), str(WM.cal[-1].date()), WM.n, WM.S, WM.n_gate3]},
                    "tw-stock-data": _G["sha"], "月營收": {"檔": _G["rev_nfiles"], "列": _G["rev_nrows"]}, "0050": Z,
                    "成本": {"0.585%版": COST_B, "現實版引擎成本": COST_R}, "化學生技醫療（未剔）股-日（主段母體）": int((OLD & U).sum())},
           "判定": VERD, "挑中格": CH, "退化": DJ, "格": [{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID], "早年": EARLYR,
           "假訊號": FAKE, "描述": DESC, "R1": {"X": X1, "2016-01-04 5,000萬母體（非金融生技）": nu, "同日全市場": nm_, "訊號計數": LR1},
           "逐筆": TS, "逐筆（另一格）": TS_other, "等效獨立": NE, "各年": {"策略": YR, "策略現實版": YRr, "0050": YR50},
           "營量營飆": YC, "營量營飆r0閘": Y["閘"], "重疊": ovl, "滑價與買不到": SLIP, "漲停判定": LUJ, "訊號計數": LST, "耗時秒": round(time.time() - t00)}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
    pd.DataFrame([{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID]).to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    seeds = []
    for nm, ms in list(RES.items()) + list(DRES.items()):
        for m in ms:
            seeds.append({"arm": nm, "r": m["r"], **seg_ret(m, seg), **m["hold"], "trades": m["trades"], "lu": m["lu"], "sha": hashlib.sha256(m["eq"].tobytes()).hexdigest()[:16]})
    pd.DataFrame(seeds).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    log(f"[完] {VERD}｜{time.time() - t00:.0f}s")


def early(a, chosen, log):
    """M9：早年段（early 版面）；先依月營收覆蓋決定判定窗。"""
    G = load_rev(log)
    try:
        T_, Yc = PRE.coverage(G["rev"], G["rev_ly"])
    except Exception as ex:
        return {"窗": None, "原因": f"覆蓋率算不出：{ex}"}
    ok = {}
    for y, g in Yc[Yc["市場"] == "twse"].groupby("年"):          # C14：覆蓋率以上市判（上櫃照報）
        ok[int(y)] = bool((g["覆蓋率"] >= 0.90).all())
    yrs = sorted(y for y in ok if 2005 <= y <= 2014)
    start = next((y for y in yrs if all(ok[z] for z in yrs if z >= y)), None)
    cov = {"各年各市場": Yc.to_dict("records"), "判定窗起年": start}
    if start is None:
        return {"窗": None, "原因": "早年各年月營收覆蓋都不到 90%", "覆蓋": cov}
    WE = World("early", a.procs, log)
    ew = (max(f"{start}-01-01", EARLY[0]), EARLY[1])
    ea, eb = WE.segpos(*ew)
    es = {"早年": (ea, eb)}
    ZE = {"早年": RR.bench_row(WE.cal, WE.bench, ea, eb + 1)}
    UE, OLDE = universe(WE, log)
    if a.smoke:
        UE = UE & (np.arange(WE.S) % 7 == 0)[:, None]
    SE, LSE, T0E = build_signals(WE, UE, log)
    SE = SE[(SE["e"] >= ea) & (SE["e"] <= eb)].reset_index(drop=True)
    arms = []; FE = {}
    for c in CELLS:
        rw = exit_rows(WE, SE, T0E, c)
        FE[c] = finalize_rows(WE, rw, False)
        arms.append((f"{c}|b", FE[c], False, a.reps))
        arms.append((f"{c}|r", finalize_rows(WE, rw, True), True, a.reps))
    RE_ = run_arms(WE, arms, es, eb, a.procs, log)
    HE = {nm: hold_only(ms, es) for nm, ms in RE_.items()}
    DJp = os.path.join(OUT, "degeneracy.json")                       # ⭐ 早年也先寫退化、再彙總報酬
    DJ = json.load(open(DJp, encoding="utf-8"))
    DJ["早年"] = {"寫入時間": now_tpe() + "（台北）", "窗": list(ew), **{nm: {**h, "早年_退化": degen(h, "早年")} for nm, h in HE.items()}}
    json.dump(DJ, open(DJp, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    EG = {}
    for nm, ms in RE_.items():
        EG[nm] = {**{k: v for k, v in summarize(ms, ZE, es).items() if not k.startswith("_")}, **HE[nm], "早年_退化": degen(HE[nm], "早年")}
    msE = RE_[f"{chosen}|b"]
    per = SE["M"]
    out = {"窗": list(ew), "0050": ZE["早年"], "格": EG, "訊號": int(len(SE)), "訊號計數": LSE,
           "IFRS：期別 2013 的訊號占比": float((per.str[:4] == "2013").mean()) if len(per) else np.nan,
           "IFRS：回看跨 2013-01（期別 2013-01～2014-11）占比": float(((per >= "2013-01") & (per <= "2014-11")).mean()) if len(per) else np.nan,
           "各年（策略種子中位）": {k: float(np.median([years_ret(m["eq"], WE.cal, ea, eb)[k] for m in msE])) for k in years_ret(msE[0]["eq"], WE.cal, ea, eb)},
           "各年0050": years_ret(WE.bench, WE.cal, ea, eb), "逐筆": trade_stats(WE, msE, FE[chosen], eb), "覆蓋": cov,
           "化學生技醫療（未剔）股-日": int((OLDE & UE).sum()), "版面": [str(WE.cal[0].date()), str(WE.cal[-1].date()), WE.n, WE.S]}
    log(f"[早年] {ew}：" + "；".join(f"{k} {v['早年_年化']:+.1%}／{v['早年_回落']:+.1%} {v['早年_標籤']}" for k, v in EG.items()))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "page"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    else:
        from backtest import researchRevLimitUp_page as PG
        PG.page()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG每年買去年漲最多 seq1（台股策略線 登錄 sha 175d13ec810ad683，2026-10-13 23:58；裁定 seq346、seq347、seq348 發號 N_組合 ＋1、6 格挑 1、
不算事後重切；結果一律「樣本不足，描述級」，判語最多「方向一致／不一致」，⛔ 不給合格）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopPrevTW [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopPrevTW_check [--procs 3]

⭐ 讀法寫死：2026-10-14 00:22（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本件數字
   看過的：登錄全文 seq1、裁定 seq341／346／347／348、既有程式 researchMomX／researchAddOn／researchYL_integrate／researchExit5／researchRevLimitUp／
   research11.simulate_mtm／research34／patterns.Frame；⚠ 回測線看過動能改良（M0～M4）與強勢類股的結果；⛔ 沒看過任何「年換一次、前一年漲幅第 1 名／前 10 名」輸出

═══ 讀法（Y 標；登錄沒寫清楚、執行者補的都在這裡）═══
 Y0 世界（⛔ 不另寫資料層，全部讀既有快取／既有函式）：
    主 ＝ rerun17 快照 H2D（edc6f8002f；日曆 2015-01-05～2026-09-24）；早年 ＝ ~/earlydata/eotc_f65bb03e11（上市＋上櫃，2004-02-11～2014-12-31）
    ＝ researchAddOn／researchExit5 的同一組版面；逐股矩陣 ＝ researchRevLimitUp.World 快取 ~/rluwork/world_{main,early}.pkl（UG.gate3 GATE_V2 開建、
    ∩ 四碼、首碼 1～9、非 91xx ⇒ 排 -DR、ETF、創新板；⭐ 含已下市；c ＝ D.load_stock 還原收盤 ffill、o ＝ 還原開盤、bar、pv ＝ UG.pit_valid、
    trd／upl（開盤漲停鎖死：開盤＝漲停價 ∧ 最低＝開盤）／dnl（開盤跌停鎖死）＝ researchSlip.stock_extra）；閘：本次 UG.gate3(GATE_V2)∩四碼 名單 vs 快取、
    pv 在每個決策日重算 vs 快取
    早年 reduce_v2（seq341 §六）讀法（同 researchAddOn U1／U4）：reduce_v2 版面只有上市本體（上櫃只收「之後轉上市」股的上市前列 ⇒ 拿來排名會有
    「事後轉上市」的前視）⇒ 主早年用上市＋上櫃版面，reduce_v2 的減資事件（上市官方＋上市偵測 2004～2010＋上櫃早年偵測＋未解釋跳動 22 筆）全部併入早年壞根
    （researchAddOn.early_extra_bad）；⭐ 另跑「早年v2」並列（描述）：~/earlydata/950ad26e12/reduce_v2 版面本身（還原鏈含減資），只取決策日當天是上市列的股
 Y1 年表：持有年 Y 的換股日 e(Y) ＝ Y 年第一個交易日；決策日 d(Y) ＝ e(Y) 前一個交易日（Y−1 年最後一個交易日）；d0(Y) ＝ Y−2 年最後一個交易日；
    nov(Y) ＝ Y−1 年 11 月最後一個交易日；x(Y) ＝ e(Y＋1)（最後一年 ＝ 資料尾墊根，照 T1：以資料尾收盤計值）
    主：持有年 2017～2026（2016 的形成期要 2014 年底價格，快照從 2015 起 ⇒ 不做）；早年：2006～2014（2004 年只有 02-11 起 ⇒ 2005 缺前一年整年價格 ⇒ 照登錄從 2006 起）
 Y2 排名母體（決策日 d 收盤可知）：快取股 ∧ pv[d] ∧ pv[d0] ∧ 營量閘 patterns.Frame.gate[d]（＝ 營量 G1 面板同一條：含 d 的 20 根全有成交 ∧
    前 20 日（d−20～d−1）均量 ≥ 500 張）∧ 形成期兩端 ffill 還原收盤有限 ＞ 0 ∧ 形成期 (d0, fe] 無壞根（fe ＝ d 整年／nov 扣一月）；早年v2 另加 d 當天是上市列
    形成期報酬 R ＝ c[fe] ÷ c[d0] − 1；名次 R 遞減、同值依代號
 Y3 T5／T6 營收：可得日 A(p) ＝ 期別 p 次月 10 日（p ≤ 2025-12）／15 日（p ≥ 2026-01）之後第一個交易日（researchExit5.avail_pos ＝ research34 同式）；
    A(p) ≤ e 的期別裡、該股最近一個有當月營收的期別 p*；年增 ＝ 當月 ÷ 去年當月 − 1（去年當月 ＞ 0 才可算；不可算 ⇒ 不過）；年增 ＞ 0 的才排名
    （＝ 登錄「不足就往下遞補」：先篩再取前 N）；p* 不是全市場最新可得期別的檔數照報
 Y4 換股簿（⭐ 正式引擎 research11.simulate_mtm，⛔ 不改）：N 槽（T1／T3／T5 ＝ 1、T2／T4／T6 ＝ 10）、pick＝形成期報酬（同日新部位依名次配錢）、
    新部位金額 ＝ min(前一日權益 ÷ N, 現金)（引擎同式）、成本 0.585% 出場一次扣（按買進金額）、stop_force ＝ 最後有效 K 棒 ＜ 資料尾的股（閘：應 0 次觸發）
    每一筆持股 ＝ 引擎的一列（sid、entry_pos、xpos、g）：出場日與出場價由本檔照登錄規則先算好：
    ① 續抱：仍在本年名單 ⇒ 同一列延長（不重複扣成本、買價不變）
    ② 換出：e(Y＋1) 起第一個「有成交 ∧ 開盤有效 ∧ 非開盤跌停鎖死」的開盤賣（延後賣出那幾天名額仍占用）；到資料尾賣不掉 ⇒ 墊根以資料尾收盤計值
    ③ 壞根：持有中 (e, x′] 有壞根 kb（x′ ＝ x 當天或之後第一根 K 棒，含「停牌跨過換股日」）⇒ kb 前最後一根有效 K 棒 vb 收盤強制賣（引擎記在 vb＋1）、現金到下次換股
    ④ 停止交易／下市：最後有效 K 棒 L（之後再也沒有成交）落在持有期 ⇒ L 收盤賣（記在 L＋1，＝ 引擎 stop_force 同式）
    ⑤ 買不到（e 當天無成交、開盤無效、開盤漲停鎖死）⇒ 該名額現金到下次換股，⛔ 不遞補（引擎同）；名額不足（延後賣出占位）⇒ 名次後面的不買
    閘：引擎買進筆數 ＝ 列數、log 沒有任何被拒（a／b／nocap）、stop_force 0 次
    ⭐ 權重函數（引擎 weight_fn；護欄要求跑前寫死逐字定義，見事後註 ①）：同一換股日要買的 k 檔，每檔目標金額 ＝ min(前一日權益 ÷ N, 當下現金 ÷ k)
      ⇒ 現金夠 ⇒ 每檔 1/N（多的現金閒置，含買不到的名額）；續抱檔漲很大、現金不夠 k 份 ⇒ 剩下現金 k 檔平分（全部買到，⛔ 不賣續抱檔去湊）
 Y5 段與指標：權益 ＝ 收盤市值；段 ＝ [d(起始年), d(結束年＋1)]（最後一段到資料尾）：探索 2016-12-30～2021-12-30（持有年 2017～2021）、
    確認 2021-12-30～2026-09-24（2022～資料尾）、早年 2005-12-30～2014-12-31（2006～2014）；年化、回落 ＝ rerun17.win_metrics；0050 ＝ 同窗 rerun17.bench_row（還原收盤）
    使用者判準：年化 ＞ 0050 ∧ 年化 ÷ |回落| ≥ 0050；回本年數 ＝ 段內最大回落谷底 → 回到谷底前高點的交易日數 ÷ 245（段內沒回本 ⇒「段內未回本」，另報全曲線）
 Y6 退化（seq325：先寫 degeneracy.json 附台北時間，再算任何報酬）：只用名單與可買性（不看報酬）：探索段「換股日持股數 ÷ N」平均 ＜ 0.5、或任一年
    排名母體（含營收篩）＜ N ⇒ 退化、不進挑格
 Y7 挑格（登錄 §三）：探索段非退化格中過使用者判準者取比值最高；都沒過取比值最高；同分 ⇒ 年化高 ⇒ 格號小
    判語（裁定 seq348）：⛔ 不給合格；確認段、早年段各報「年化贏／輸 0050」「比值贏／輸 0050」；方向一致 ＝ 該段這兩項的贏輸與探索段相同；另報照判準的落點（只描述）
 Y8 必報：每格每段 年化、回落、比值、回本年數；逐年持股代號、名稱、名次、形成期報酬、個股當年報酬、組合當年報酬、0050 當年報酬；
    拿掉最好一年 ＝ 段內逐日報酬剔除組合報酬最高那個持有年的日子後接起來算年化與回落（0050 同樣剔同一年並報）；
    拿掉貢獻最大那一檔 ＝ 段內持有過的每一檔各自當成「買不到（名額持現金）」重跑，段內年化掉最多的那一檔
    第 1 名那檔（T1／T3／T5）：換股日是否處置（meta/disposal.csv 普通股、區間含 e；另報 d）、換股日開盤是否漲停鎖死／開盤漲停；
      買不到 ⇒ 另報「改買第 2 名」臂（依名次往下取第一檔買得到的；⛔ 不判）
    描述（⛔ 不判）：固定 35% 停損（收盤 ≤ 買價 × 0.65 ⇒ 次一個可賣開盤賣、現金到隔年；續抱的買價 ＝ 原買價；附「原文九組中事後挑出」）；
      相對停損（收盤 ＜ 買價 × (1 − 2σ)，σ ＝ 買進那年的前一年有效 K 棒日報酬標準差 × √245；1 − 2σ ≤ 0 ⇒ 不觸發）；前 3 名等權（整年、扣一月、整年＋營收三種）
    早年（含主）逐年第 1 名逐檔核對減資假飆：形成期內 adj 事件（減資／面額）、reduce_v2 上市偵測／上櫃偵測／未解釋 22 筆、R8 事件、單根還原報酬超過漲跌幅 0.5 點以上
 結果句必附：「年換一次、每段只有 4～5 年，樣本不足」「台股追漲類（動能改良、強勢類股）多半不合格，本線已看過」「方向已見於美股與動能改良」
   早年另附：「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註
輸出 backtest/resultsTopPrevTW/：degeneracy.json（先寫）、TopPrevTW.json、cells.csv、yearly.csv、rank_top10.csv、run.log；大檔 ~/topprevwork/
── 事後註（寫死之後、照實記）──
 ① 00:29 第一次全跑：世界建好、degeneracy.json 已寫，跑到 主·T2 被引擎閘擋下（2025-01-02 續抱的 5314 占權益很大，賣出 9 檔的現金不夠 9 份 1/N，
    引擎原版 min(1/N, 現金) 第 6 檔起現金用盡沒買到 ⇒ 換股簿與引擎持股不一致）；⛔ 沒印出、沒看任何報酬數字。
    ⇒ 補上「權重函數」（Y4，用引擎既有 weight_fn 開關，⛔ 引擎沒改）後重跑；其餘讀法沒改
"""
from __future__ import annotations

import argparse
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
from backtest import research11 as R                        # noqa: E402
from backtest import research13 as R13                      # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import researchExit5 as X5                    # noqa: E402
from backtest import researchRevLimitUp as RLU              # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402

TIME = "2026-10-14 00:22（台北）"
REG_SHA = "175d13ec810ad683"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsTopPrevTW"
WORK = os.path.expanduser("~/topprevwork")
V2DATA = os.path.expanduser("~/earlydata/950ad26e12/reduce_v2/data")
COST = R.COST
ANN = 245
ANCHOR = (0.24020209886370614, -0.3395700527611012)
CELLS = {"T1": {"form": "整年", "N": 1, "rev": False}, "T2": {"form": "整年", "N": 10, "rev": False},
         "T3": {"form": "扣一月", "N": 1, "rev": False}, "T4": {"form": "扣一月", "N": 10, "rev": False},
         "T5": {"form": "整年", "N": 1, "rev": True}, "T6": {"form": "整年", "N": 10, "rev": True}}
TOP3 = {"整年前3": ("整年", False), "扣一月前3": ("扣一月", False), "整年營收前3": ("整年", True)}
WORLDS = {"主": {"data": RR.H2D, "part": "main", "y0": 2017, "y1": None},
          "早年": {"data": RA.EOTC, "part": "early", "y0": 2006, "y1": 2014},
          "早年v2": {"data": V2DATA, "part": None, "y0": 2006, "y1": 2014}}
SEGS = {"主": {"探索": (2017, 2021), "確認": (2022, None)}, "早年": {"早年": (2006, 2014)}, "早年v2": {"早年": (2006, 2014)}}
SENT = ["年換一次、每段只有 4～5 年，樣本不足（結果一律「樣本不足，描述級」）", "台股追漲類（動能改良、強勢類股）多半不合格，本線已看過",
        "方向已見於美股與動能改良"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市（早年主表 ＝ 上市＋上櫃版面）",
              "早年v2 ＝ reduce_v2 版面（只上市；還原鏈含減資）並列，描述"]
STOP_NOTE = "35% 是原文九組（10%～50%）中事後挑出的一組"
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


# ═════════════ 世界 ═════════════
def year_table(cal, y0, y1):
    yrs = np.asarray(cal.year); mon = np.asarray(cal.month); n = len(cal)
    first = {int(y): int(np.flatnonzero(yrs == y)[0]) for y in np.unique(yrs)}
    out = {}
    for Y in sorted(first):
        if Y < y0 or (y1 is not None and Y > y1) or (Y - 1) not in first:
            continue
        e = first[Y]; d = e - 1; d0 = first[Y - 1] - 1
        if d0 < 0 or cal[d0].year != Y - 2:
            continue
        nov = np.flatnonzero((yrs == Y - 1) & (mon == 11))
        out[Y] = {"e": e, "d": d, "d0": d0, "nov": int(nov[-1]), "x": first.get(Y + 1, n)}
    return out


def _job(a):
    """一檔：營量閘（patterns.Frame.gate）、量均、pv 重算（決策日位置）；full ⇒ 早年v2 的逐股陣列（RLU._wjob）與壞根（research11.load_bars）。"""
    data, sid, mk, dpos, full = a
    D.DATA = data
    cal = _G[("cal", data)]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    f = P.Frame(st.df, st.event_dates)
    out = {"g": np.asarray(f.gate, bool)[dpos], "v20": np.asarray(f.vol_ma20, float)[dpos],
           "pv": np.asarray(UG.pit_valid(sid, cal, data), bool)[dpos]}
    if full:
        RLU._G["cal"] = cal
        _, w = RLU._wjob((sid, mk))
        if w is None:
            return sid, None
        out["w"] = {k: w[k] for k in ("c", "o", "bar", "pv", "tw", "trd", "upl", "dnl", "ret")}
        B = R.load_bars(sid, mk, cal)
        if B is not None:
            nb = B["next_bad"]; nn = len(B["idx"])
            out["bad"] = B["idx"][[k for k in range(nn) if nb[k] == k]].astype(np.int64); out["bad_src"] = "load_bars"
        else:
            idx = np.flatnonzero(st.df["traded"].to_numpy(bool))
            gp = np.diff(idx) - 1
            out["bad"] = idx[1:][gp >= 5].astype(np.int64); out["bad_src"] = "缺口≥5（<260 根）"
    return sid, out


def build_world(wn, procs, log):
    cp = os.path.join(WORK, f"world_{wn}.pkl")
    if os.path.exists(cp):
        log(f"[世界 {wn}] 讀快取 {cp}")
        return pickle.load(open(cp, "rb"))
    cfg = WORLDS[wn]; data = cfg["data"]
    D.DATA = data
    cal = D.load_calendar(); n = len(cal)
    YT = year_table(cal, cfg["y0"], cfg["y1"])
    dpos = sorted({v["d"] for v in YT.values()})
    st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st)
    U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
    mk = dict(zip(U["stock_id"], U["market"])); names = dict(zip(st["stock_id"], st["name"]))
    gate = {}
    if cfg["part"] is not None:
        Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{cfg['part']}.pkl"), "rb"))
        if Z["c"].shape[1] != n:
            raise SystemExit(f"⛔ {wn} 快取日曆長 {Z['c'].shape[1]} ≠ {n}")
        sids = list(Z["sids"])
        gate["UG.gate3(GATE_V2)∩四碼 檔數"] = int(len(U)); gate["快取 n_gate3"] = int(Z["n_gate3"])
        gate["名單差（本次有、快取沒有）"] = sorted(set(U["stock_id"]) - set(sids))[:20]
        gate["名單差（快取有、本次沒有）"] = sorted(set(sids) - set(U["stock_id"]))[:20]
        full = False
    else:
        sids = sorted(U["stock_id"]); full = True
    _G[("cal", data)] = cal
    jobs = [(data, s, mk.get(s, "twse"), dpos, full) for s in sids]
    t0 = time.time(); res = {}
    with Pool(procs) as pool:
        for i, (s, v) in enumerate(pool.imap_unordered(_job, jobs, chunksize=8)):
            res[s] = v
            if i % 500 == 0:
                log(f"[世界 {wn}] 逐股 {i}/{len(jobs)}｜{time.time() - t0:.0f}s")
    if full:
        sids = sorted(s for s, v in res.items() if v is not None and "w" in v)
        Z = {k: np.vstack([res[s]["w"][k] for s in sids]) for k in ("c", "o", "bar", "pv", "tw", "trd", "upl", "dnl", "ret")}
        Z["sids"] = sids
    S = len(sids); ix = {s: i for i, s in enumerate(sids)}
    GV = np.zeros((S, len(dpos)), bool); V20 = np.full((S, len(dpos)), np.nan); PVc = np.ones((S, len(dpos)), bool)
    miss = []
    for s, i in ix.items():
        v = res.get(s)
        if v is None:
            miss.append(s); continue
        GV[i] = v["g"]; V20[i] = v["v20"]; PVc[i] = v["pv"]
    gate["逐股讀不到（營量閘當不過）"] = miss[:20]; gate["逐股讀不到 檔數"] = len(miss)
    gate["pv 決策日重算 ≠ 快取（股×日）"] = int((PVc != np.asarray(Z["pv"], bool)[:, dpos]).sum())
    # 壞根
    BAD = np.zeros((S, n), bool); bad_info = {}
    if cfg["part"] is not None:
        B = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{cfg['part']}.pkl"), "rb"))
        nocache = []
        for s, i in ix.items():
            if s in B:
                a, b = B[s]; BAD[i, a] = True; BAD[i, b] = True
            else:
                nocache.append(s)
        for s in nocache:
            bar, bad = RA.extra_stock(s, mk.get(s, "twse"), data, cal); BAD[ix[s]] |= np.asarray(bad, bool)[:n]
        bad_info["crashwork 沒有、現場補（BARR.bad_part∪adj 減資面額）"] = nocache[:20]; bad_info["現場補 檔數"] = len(nocache)
        bad_info["壞根股日（主來源）"] = int(BAD.sum())
        EV = None
        if wn == "早年":
            Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
            if not (len(Wa["cal"]) == n and (Wa["cal"] == cal).all()):
                raise SystemExit("⛔ 早年 addonwork 日曆 ≠ 版面日曆")
            EX, cnt = RA.early_extra_bad(Wa, log)
            n0 = int(BAD.sum())
            for s, ks in EX.items():
                if s in ix:
                    BAD[ix[s], sorted(ks)] = True
            bad_info["早年另加（reduce_v2＋R8）來源"] = cnt; bad_info["早年另加新增股日"] = int(BAD.sum()) - n0
            EV = Wa["EV"]
        bench = np.asarray(pickle.load(open(os.path.join(RA.WORK, f"world_{'主' if wn == '主' else '早年'}.pkl"), "rb"))["bench"], float)
    else:
        src = {}
        for s, i in ix.items():
            BAD[i, res[s]["bad"]] = True; src[res[s]["bad_src"]] = src.get(res[s]["bad_src"], 0) + 1
        bad_info["壞根來源（檔數）"] = src; bad_info["壞根股日"] = int(BAD.sum()); EV = None
        bench = RR.load_bench(cal)
    D.DATA = data
    bench_chk = np.asarray(RR.load_bench(cal), float)
    gate["0050 基準 ＝ 本版面 load_bench（最大相對差）"] = float(np.nanmax(np.abs(bench / bench_chk - 1.0)))
    rev, rly, rinfo = X5.load_revenue(data)
    AV = X5.avail_pos(list(rev.index), cal)
    disp = D.load_disposal_intervals()
    C = np.asarray(Z["c"], float); BAR = np.asarray(Z["bar"], bool)
    SF = {}
    for s, i in ix.items():
        b = np.flatnonzero(BAR[i])
        if len(b) and b[-1] < n - 1:
            SF[s] = int(b[-1])
    W = {"name": wn, "data": data, "cal": cal, "n": n, "YT": YT, "dpos": dpos, "sids": sids, "ix": ix, "mk": mk, "names": names,
         "C": C, "O": np.asarray(Z["o"], float), "BAR": BAR, "PV": np.asarray(Z["pv"], bool), "TW": np.asarray(Z["tw"], bool),
         "TRD": np.asarray(Z["trd"], bool)[:, :n], "UPL": np.asarray(Z["upl"], bool)[:, :n], "DNL": np.asarray(Z["dnl"], bool)[:, :n],
         "RET": np.asarray(Z["ret"], float), "BAD": BAD, "GV": GV, "V20": V20, "bench": bench, "rev": rev, "rly": rly, "rinfo": rinfo, "AV": AV,
         "disp": disp, "SF": SF, "EV": EV, "gate": gate, "bad_info": bad_info}
    pickle.dump(W, open(cp, "wb"), protocol=5)
    log(f"[世界 {wn}] {cal[0].date()}～{cal[-1].date()}｜股 {S}｜持有年 {min(YT)}～{max(YT)}｜閘 {gate}｜壞根 {bad_info}｜營收 {rinfo}")
    return W


def prep(W):
    """查詢用索引（每檔有效 K 棒、可賣開盤、壞根位置；壞根累計）。"""
    S, n = W["C"].shape
    W["CB"] = np.zeros((S, n + 1), np.int32); W["CB"][:, 1:] = np.cumsum(W["BAD"], axis=1)
    W["barpos"] = [np.flatnonzero(W["BAR"][i]) for i in range(S)]
    W["sellpos"] = [np.flatnonzero(W["TRD"][i] & np.isfinite(W["O"][i]) & (W["O"][i] > 0) & ~W["DNL"][i]) for i in range(S)]
    W["badpos"] = [np.flatnonzero(W["BAD"][i]) for i in range(S)]
    W["dcol"] = {d: j for j, d in enumerate(W["dpos"])}
    W["SFi"] = {W["ix"][s]: L for s, L in W["SF"].items()}
    W["rank_cache"] = {}
    return W


# ═════════════ 排名 ═════════════
def yoy_year(W, Y):
    """Y3：每檔在 e(Y) 可得的最近一期營收年增、期別。"""
    e = W["YT"][Y]["e"]
    av = [p for p in W["rev"].index if W["AV"][p] <= e]
    sub = W["rev"].loc[av]; subl = W["rly"].loc[av]
    latest = av[-1] if av else None
    out = {}
    for s in W["sids"]:
        if s not in sub.columns:
            continue
        col = sub[s]; lv = col.last_valid_index()
        if lv is None:
            continue
        r0 = float(col.loc[lv]); ly = subl.at[lv, s]
        y = (r0 / ly - 1.0) if (np.isfinite(ly) and ly > 0) else np.nan
        out[s] = (y, lv)
    return out, latest


def ranked(W, Y, form, rev):
    key = (Y, form, rev)
    if key in W["rank_cache"]:
        return W["rank_cache"][key]
    yt = W["YT"][Y]; d, d0 = yt["d"], yt["d0"]; fe = d if form == "整年" else yt["nov"]
    C = W["C"]; j = W["dcol"][d]
    el = W["GV"][:, j] & W["PV"][:, d] & W["PV"][:, d0]
    if W["name"] == "早年v2":
        el &= W["TW"][:, d]
    ca, cb = C[:, d0], C[:, fe]
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = el & np.isfinite(ca) & np.isfinite(cb) & (ca > 0) & (cb > 0)
        nb = W["CB"][:, fe + 1] - W["CB"][:, d0 + 1]
        Rr = cb / ca - 1.0
    ok &= nb == 0
    n_pool0 = int(ok.sum())
    info = {"排名母體（價）": n_pool0, "營量閘過": int(el.sum()), "形成期有壞根剔除": int((el & np.isfinite(ca) & np.isfinite(cb) & (nb > 0)).sum())}
    yo = {}
    if rev:
        if ("yoy", Y) not in W["rank_cache"]:
            W["rank_cache"][("yoy", Y)] = yoy_year(W, Y)
        yo, latest = W["rank_cache"][("yoy", Y)]
        keep = np.zeros(len(ok), bool); stale = 0
        for s, i in W["ix"].items():
            if ok[i] and s in yo and np.isfinite(yo[s][0]) and yo[s][0] > 0:
                keep[i] = True; stale += int(yo[s][1] != latest)
        info.update({"營收篩後": int(keep.sum()), "全市場最新可得期別": latest, "營收篩後中用較舊期別": stale,
                     "營收不可算或無列（價母體內）": int(sum(1 for s, i in W["ix"].items() if ok[i] and (s not in yo or not np.isfinite(yo[s][0]))))})
        ok = keep
    ii = np.flatnonzero(ok)
    order = sorted(ii, key=lambda i: (-Rr[i], W["sids"][i]))
    L = [(int(i), float(Rr[i]), (yo.get(W["sids"][i], (np.nan, None)) if rev else (np.nan, None))) for i in order]
    W["rank_cache"][key] = (L, info)
    return L, info


# ═════════════ 換股簿 ═════════════
def first_after(arr, t):
    k = int(np.searchsorted(arr, t))
    return int(arr[k]) if k < len(arr) else None


def last_before(arr, t):
    k = int(np.searchsorted(arr, t)) - 1
    return int(arr[k]) if k >= 0 else None


def buyable(W, i, e):
    return bool(W["TRD"][i, e] and np.isfinite(W["O"][i, e]) and W["O"][i, e] > 0 and not W["UPL"][i, e])


def year_events(W, i, p, e, x, stop):
    """持有期 [e, x) 內的提前出場（壞根、停止交易、停損）⇒ (exit_pos, gross, 種類) 或 None。"""
    n = W["n"]; C = W["C"]; ep = p["ep"]; cands = []
    xb = x if x >= n else (first_after(W["barpos"][i], x) if first_after(W["barpos"][i], x) is not None else n - 1)
    hi = min(max(xb, x if x < n else n - 1), n - 1)
    k = first_after(W["badpos"][i], e + 1)
    if k is not None and k <= hi:
        vb = last_before(W["barpos"][i], k)
        if vb is not None and vb + 1 <= x:
            cands.append((vb + 1, float(C[i, vb] / ep - 1.0), "壞根前收盤強制"))
    L = W["SFi"].get(i)
    if L is not None and e <= L and L + 1 <= min(x, n - 1):
        cands.append((L + 1, float(C[i, L] / ep - 1.0), "停止交易／下市（最後收盤）"))
    if stop is not None:
        lv = p.get("level")
        if lv is not None and np.isfinite(lv) and lv > 0:
            lo = max(p["entry"], e); bp = W["barpos"][i]
            seg = bp[(bp >= lo) & (bp <= min(x, n) - 1)]
            cc = C[i, seg]
            hit = seg[(cc <= lv) if stop == "stop35" else (cc < lv)]
            if len(hit):
                t = first_after(W["sellpos"][i], int(hit[0]) + 1)
                if t is not None:
                    cands.append((t, float(W["O"][i, t] / ep - 1.0), "停損（次一可賣開盤）"))
    if not cands:
        return None
    return min(cands, key=lambda z: (z[0], 0 if z[2].startswith("壞根") else 1))


def sched_sale(W, i, p, x):
    n = W["n"]; ep = p["ep"]
    t = first_after(W["sellpos"][i], x)
    if t is not None and t <= n - 1:
        return (t, float(W["O"][i, t] / ep - 1.0), "換出（開盤）" if t == x else "換出（延後開盤）")
    L = W["SFi"].get(i)
    if L is not None and L >= x:
        return (L + 1, float(W["C"][i, L] / ep - 1.0), "停止交易／下市（最後收盤）")
    return (n, float(W["C"][i, n - 1] / ep - 1.0), "資料尾仍持有（賣不掉）")


def sigma_prev(W, i, Y):
    yt = W["YT"][Y]; r = W["RET"][i, yt["d0"] + 1:yt["d"] + 1]; r = r[np.isfinite(r)]
    return float(np.std(r, ddof=1) * np.sqrt(ANN)) if len(r) > 2 else np.nan


def book(W, form, rev, N, mode="base", stop=None, exclude=frozenset()):
    """⇒ rows（引擎列）、pos（持股明細）、yrinfo（逐年名單與可買性）。mode：base｜alt2（買不到就往下取下一名）。"""
    n = W["n"]; YT = W["YT"]; years = sorted(YT)
    openp = {}        # i ⇒ dict(entry, ep, level, Y0)
    closing = []      # (i, exit_pos) 已決定出場、還占名額
    rows = []; pos = []; yrinfo = {}

    def close(i, ex, why):
        p = openp.pop(i)
        pos.append({"i": i, "sid": W["sids"][i], "entry": p["entry"], "ep": p["ep"], "exit": ex[0], "gross": ex[1], "kind": ex[2], "Y0": p["Y0"], "why": why})
        rows.append({"sid": W["sids"][i], "entry_pos": p["entry"], "xpos_Y": ex[0], "g_Y": ex[1], "score": p["score"]})
        return ex[0]
    for Y in years:
        e, x = YT[Y]["e"], YT[Y]["x"]
        L, info = ranked(W, Y, form, rev)
        # 有效名單
        if mode == "alt2":
            take = []
            for (i, r_, yo) in L:
                if len(take) >= N:
                    break
                if i in exclude:
                    continue
                if i in openp or buyable(W, i, e):
                    take.append(i)
            sel = take
        else:
            sel = [i for (i, r_, yo) in L[:N]]
        selset = set(sel)
        # 換出
        for i in list(openp):
            if i not in selset:
                ex = sched_sale(W, i, openp[i], e)
                close(i, ex, "換出")
                if ex[0] > e:
                    closing.append((i, ex[0]))
        busy = sum(1 for (_, xp) in closing if xp > e)
        closing = [(i, xp) for (i, xp) in closing if xp > e]
        cont = [i for i in sel if i in openp]
        free = N - len(cont) - busy
        bought = []; miss = []
        for i in sel:
            if i in openp:
                continue
            why = None
            if i in exclude:
                why = "排除（拿掉該檔）"
            elif not buyable(W, i, e):
                why = "開盤漲停鎖死" if (W["TRD"][i, e] and W["UPL"][i, e]) else "換股日無成交／開盤無效"
            elif free <= 0:
                why = "名額被延後賣出占用"
            if why:
                miss.append((i, why)); continue
            ep = float(W["O"][i, e])
            p = {"entry": e, "ep": ep, "Y0": Y, "score": float(dict((a, b) for a, b, _ in L)[i])}
            if stop == "stop35":
                p["level"] = 0.65 * ep
            elif stop == "stoprel":
                sg = sigma_prev(W, i, Y); p["sigma"] = sg; p["level"] = ep * (1.0 - 2.0 * sg) if np.isfinite(sg) else np.nan
            openp[i] = p; bought.append(i); free -= 1
        held_after = len(openp)
        # 年內提前出場
        for i in list(openp):
            ev = year_events(W, i, openp[i], e, x, stop)
            if ev is not None:
                close(i, ev, "年內")
                if ev[0] > x:
                    closing.append((i, ev[0]))
        yrinfo[Y] = {"e": e, "sel": sel, "cont": cont, "bought": bought, "miss": miss, "busy": busy, "held_after": held_after, "info": info,
                     "top": L[:max(N, 10)]}
    for i in list(openp):
        close(i, (n, float(W["C"][i, n - 1] / openp[i]["ep"] - 1.0), "資料尾仍持有"), "資料尾")
    return rows, pos, yrinfo


def run_engine(W, rows, N):
    if not rows:
        eq = np.ones(W["n"] + 1)
        return {"eq": eq, "first": W["n"], "end": W["n"] + 1, "out": {"trades": 0}, "log": [], "audit": []}
    sig = pd.DataFrame(rows)
    sids = sorted(set(sig["sid"]))
    NP = W["n"] + 1
    closes = {s: np.r_[W["C"][W["ix"][s]], W["C"][W["ix"][s]][-1]] for s in sids}
    opens = {s: np.r_[W["O"][W["ix"][s]], np.nan] for s in sids}
    sf = {s: W["SF"][s] for s in sids if s in W["SF"]}
    lg = []; au = []

    def wfn(batch, t, eq_prev, cash):
        k = len(batch)
        return [min(eq_prev / N, cash / k)] * k
    o = R.simulate_mtm(sig, "Y", N, np.random.default_rng(0), closes, opens, NP, return_equity=True, log=lg, pick="score",
                       stop_force=sf, audit=au, weight_fn=wfn)
    bad = [r for r in lg if r.get("reason") != "in"]
    if o["trades"] != len(rows) or bad or o.get("x_stop_force_n", 0) != 0:
        raise SystemExit(f"⛔ 引擎閘：trades {o['trades']} ≠ 列 {len(rows)} 或被拒 {bad[:3]} 或 stop_force {o.get('x_stop_force_n')}")
    return {"eq": np.asarray(o["equity"], float), "first": int(o["first"]), "end": int(o["end"]), "out": o, "log": lg, "audit": au}


# ═════════════ 指標 ═════════════
def seg_pos(W, seg):
    y0, y1 = seg; YT = W["YT"]
    w0 = YT[y0]["d"]
    w1 = YT[y1 + 1]["d"] if (y1 is not None and (y1 + 1) in YT) else W["n"] - 1
    yrs = [Y for Y in sorted(YT) if Y >= y0 and (y1 is None or Y <= y1)]
    return w0, w1, yrs


def ratio(c, m):
    return float(c / abs(m)) if (np.isfinite(c) and np.isfinite(m) and m < 0) else float("nan")


def recover(seg_eq):
    seg = np.asarray(seg_eq, float); pk = np.maximum.accumulate(seg); dd = seg / pk - 1.0
    j = int(np.argmin(dd)); peak = pk[j]
    k = np.flatnonzero(seg[j:] >= peak)
    return j, (float(k[0] / ANN) if len(k) else None)


def year_ret(arr, W, yrs):
    YT = W["YT"]; out = {}
    for Y in yrs:
        a = YT[Y]["d"]; b = YT[Y + 1]["d"] if (Y + 1) in YT else W["n"] - 1
        out[Y] = float(arr[b] / arr[a] - 1.0)
    return out


def drop_year(arr, W, w0, w1, Ydrop):
    YT = W["YT"]; a = YT[Ydrop]["d"]; b = YT[Ydrop + 1]["d"] if (Ydrop + 1) in YT else W["n"] - 1
    r = arr[w0 + 1:w1 + 1] / arr[w0:w1] - 1.0
    t = np.arange(w0 + 1, w1 + 1)
    keep = ~((t > a) & (t <= b))
    cur = np.r_[1.0, np.cumprod(1.0 + r[keep])]
    yrs = (len(cur) - 1) / ANN
    c = float(cur[-1] ** (1 / yrs) - 1.0) if yrs > 0 else float("nan")
    m = float((cur / np.maximum.accumulate(cur) - 1.0).min())
    return c, m


def seg_stats(W, E, seg):
    w0, w1, yrs = seg_pos(W, seg)
    eq = E["eq"]
    c, m, _ = RR.win_metrics(eq, E["first"], E["end"], w0, w1)
    b = RR.bench_row(W["cal"], W["bench"], w0, w1 + 1)
    j, rec = recover(eq[w0:w1 + 1])
    jb, recb = recover(W["bench"][w0:w1 + 1])
    full_rec = None
    if rec is None:
        pk = np.max(eq[w0:w0 + j + 1]); k = np.flatnonzero(eq[w0 + j:W["n"]] >= pk)
        full_rec = float(k[0] / ANN) if len(k) else None
    yr = year_ret(eq, W, yrs); yb = year_ret(W["bench"], W, yrs)
    best = max(yr, key=lambda y: yr[y])
    c2, m2 = drop_year(eq, W, w0, w1, best); cb2, mb2 = drop_year(W["bench"], W, w0, w1, best)
    bestb = max(yb, key=lambda y: yb[y]); cb3, mb3 = drop_year(W["bench"], W, w0, w1, bestb)
    return {"窗": [str(W["cal"][w0].date()), str(W["cal"][w1].date())], "持有年": f"{yrs[0]}～{yrs[-1]}", "持有年數（日數÷245）": (w1 - w0) / ANN,
            "持有年數（曆年個數）": len(yrs),
            "年化": c, "回落": m, "比值": ratio(c, m), "回本年數": rec, "谷底日": str(W["cal"][w0 + j].date()),
            "段內未回本⇒全曲線回本年數": full_rec,
            "0050": {"年化": b["cagr"], "回落": b["mdd"], "比值": ratio(b["cagr"], b["mdd"]), "回本年數": recb},
            "逐年": {int(y): yr[y] for y in yrs}, "0050逐年": {int(y): yb[y] for y in yrs},
            "拿掉最好一年": {"年": int(best), "年化": c2, "回落": m2, "比值": ratio(c2, m2), "0050 同年剔除": {"年化": cb2, "回落": mb2, "比值": ratio(cb2, mb2)},
                        "0050 剔自己最好一年": {"年": int(bestb), "年化": cb3, "回落": mb3, "比值": ratio(cb3, mb3)}}}


def crit(c, m, b):
    return {"年化贏0050": bool(c > b["年化"]), "比值贏0050": bool(ratio(c, m) >= b["比值"])}


def placement(cr):
    return "照判準會落在『年化、比值都贏』" if (cr["年化贏0050"] and cr["比值贏0050"]) else ("只贏年化" if cr["年化贏0050"] else "年化沒贏")


# ═════════════ 全部格 ═════════════
def run_cell(W, form, rev, N, mode="base", stop=None, exclude=frozenset()):
    rows, pos, yi = book(W, form, rev, N, mode, stop, exclude)
    E = run_engine(W, rows, N)
    E.update(rows=rows, pos=pos, yi=yi)
    return E


def contrib(W, form, rev, N, seg, E0):
    w0, w1, yrs = seg_pos(W, seg)
    held = sorted({p["i"] for p in E0["pos"] if p["entry"] <= w1 and p["exit"] > w0})
    c0, m0, _ = RR.win_metrics(E0["eq"], E0["first"], E0["end"], w0, w1)
    best = None
    for i in held:
        E = run_cell(W, form, rev, N, exclude=frozenset([i]))
        c, m, _ = RR.win_metrics(E["eq"], E["first"], E["end"], w0, w1)
        if best is None or (c0 - c) > best[1]:
            best = (i, c0 - c, c, m)
    if best is None:
        return None
    return {"代號": W["sids"][best[0]], "名稱": W["names"].get(W["sids"][best[0]]), "拿掉後年化": best[2], "拿掉後回落": best[3], "拿掉後比值": ratio(best[2], best[3]),
            "年化少（點）": best[1] * 100, "段內持有過檔數": len(held)}


def fake_check(W, Y, i, form):
    """逐年第 1 名減資假飆核對（形成期 (d0, fe]）。"""
    yt = W["YT"][Y]; d0 = yt["d0"]; fe = yt["d"] if form == "整年" else yt["nov"]
    s = W["sids"][i]; cal = W["cal"]; lo, hi = cal[d0], cal[fe]
    D.DATA = W["data"]
    adj = D.load_adj(s); ev = []
    if adj is not None and len(adj):
        for d, k_, f_ in zip(adj["date"], adj.get("event", pd.Series([""] * len(adj))), adj["factor"]):
            if lo < d <= hi:
                ev.append(f"{d.date()} {k_} {float(f_):.4f}")
    hits = []
    for fn, dc in (("twse_reduce_detected_2004_2010.csv", "date"), ("otc_reduce_detected_2007_2012.csv", "resume_day"), ("twse_jump_unexplained_2004_2010.csv", "date")):
        t = pd.read_csv(os.path.join(RA.V2EXT, fn), dtype=str, keep_default_na=False)
        for d in t.loc[t["stock_id"].str.strip() == s, dc]:
            if d.strip() and lo < pd.Timestamp(d.strip()) <= hi:
                hits.append(f"{fn.split('_2')[0]} {d.strip()}")
    if W["EV"] is not None:
        for s_, e_ in zip(W["EV"]["stock_id"], W["EV"]["e"]):
            if s_ == s and e_ and lo < pd.Timestamp(e_) <= hi:
                hits.append(f"R8 {e_}")
    r = W["RET"][i, d0 + 1:fe + 1]; t = np.arange(d0 + 1, fe + 1)
    lim = np.where(cal[t] < pd.Timestamp("2015-06-01"), 0.07, 0.10)
    ab = np.isfinite(r) & (np.abs(r) > lim + 0.005)
    jumps = [f"{cal[t[k]].date()} {r[k]:+.3f}" for k in np.flatnonzero(ab)]
    sus = bool([e for e in ev if ("reduce" in e or "parvalue" in e)] or hits or jumps)
    return {"形成期 adj 事件": ev, "reduce_v2／R8 名單": hits, "單根超過漲跌幅": jumps[:10], "單根超過漲跌幅 根數": len(jumps),
            "判讀": "⚠ 疑似減資／斷點（要人工看）" if sus else "未見減資／斷點跡象"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    T0 = time.time()
    log(f"===== researchTopPrevTW（PREREG每年買去年漲最多 seq1）{now_tpe()}（台北）讀法寫死 {TIME} procs {a.procs} =====")
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}")
    UG.set_gate_v2(True)
    WS = {}
    for wn in WORLDS:
        WS[wn] = prep(build_world(wn, a.procs, log))
    gates = {wn: W["gate"] for wn, W in WS.items()}
    Wm = WS["主"]
    a0 = int(Wm["cal"].searchsorted(pd.Timestamp("2017-03-02"))); a1 = int(Wm["cal"].searchsorted(pd.Timestamp("2026-08-24")))
    c_, m_ = R13.window_stats(Wm["bench"], 0, Wm["n"], a0, a1 + 1)
    gates["0050 主窗錨逐位元（2017-03-02～2026-08-24）"] = repr(float(c_)) == repr(ANCHOR[0]) and repr(float(m_)) == repr(ANCHOR[1])
    log(f"[閘] 0050 錨 {gates['0050 主窗錨逐位元（2017-03-02～2026-08-24）']}")
    if not gates["0050 主窗錨逐位元（2017-03-02～2026-08-24）"]:
        raise SystemExit("⛔ 0050 錨不過")

    # ── 退化（Y6）：只用名單與可買性，先寫 ──
    DG = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在算任何報酬之前寫入（Y6、裁定 seq325）；只用名單與可買性：探索段換股日持股數 ÷ N 平均 ＜ 0.5、"
                                              "或任一年排名母體（含營收篩）＜ N ⇒ 退化、不進挑格", "格": {}}
    BK = {}
    for wn, W in WS.items():
        for k, cf in CELLS.items():
            rows, pos, yi = book(W, cf["form"], cf["rev"], cf["N"])
            BK[(wn, k)] = (rows, pos, yi)
            dd = {}
            for sg, seg in SEGS[wn].items():
                _, _, yrs = seg_pos(W, seg)
                hold = [yi[Y]["held_after"] / cf["N"] for Y in yrs]
                pool = [yi[Y]["info"]["營收篩後" if cf["rev"] else "排名母體（價）"] for Y in yrs]
                dd[sg] = {"換股日持股數÷N 平均": float(np.mean(hold)), "逐年": {int(Y): yi[Y]["held_after"] for Y in yrs},
                          "排名母體最少": int(min(pool)), "逐年排名母體": {int(Y): int(p) for Y, p in zip(yrs, pool)},
                          "買不到名額（逐年）": {int(Y): [(W["sids"][i], w) for i, w in yi[Y]["miss"]] for Y in yrs if yi[Y]["miss"]}}
            if wn == "主":
                dd["退化"] = bool(dd["探索"]["換股日持股數÷N 平均"] < 0.5 or dd["探索"]["排名母體最少"] < cf["N"])
            DG["格"][f"{wn}·{k}"] = dd
    json.dump(DG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[退化] 已寫 degeneracy.json：{ {k: v.get('退化') for k, v in DG['格'].items() if '退化' in v} }")

    # ── 6 格 × 世界 ──
    RES = {}; CROWS = []
    for wn, W in WS.items():
        for k, cf in CELLS.items():
            E = run_cell(W, cf["form"], cf["rev"], cf["N"])
            if E["rows"] != BK[(wn, k)][0]:
                raise SystemExit("⛔ 換股簿不可重現")
            RES[(wn, k, "主臂")] = E
            for sg, seg in SEGS[wn].items():
                st = seg_stats(W, E, seg)
                CROWS.append({"世界": wn, "格": k, "臂": "主臂", "段": sg, **{kk: st[kk] for kk in ("窗", "持有年", "年化", "回落", "比值", "回本年數")},
                              "0050年化": st["0050"]["年化"], "0050回落": st["0050"]["回落"], "0050比值": st["0050"]["比值"],
                              **crit(st["年化"], st["回落"], st["0050"]), "_st": st})
        log(f"[格] {wn} 6 格完成")
    CT = pd.DataFrame(CROWS)
    # ── 挑格（探索）──
    ex = CT[(CT["世界"] == "主") & (CT["段"] == "探索")].copy()
    ex["退化"] = [DG["格"][f"主·{k}"]["退化"] for k in ex["格"]]
    pool = ex[~ex["退化"]]
    pas = pool[pool["年化贏0050"] & pool["比值贏0050"]]
    pp = (pas if len(pas) else pool).assign(_k=lambda z: z["格"].str[1].astype(int))
    best = pp.sort_values(["比值", "年化", "_k"], ascending=[False, False, True]).iloc[0]
    PK = best["格"]
    log(f"[挑格] {PK}｜探索過判準格數 {len(pas)}｜探索 {best['年化']:+.2%}／{best['回落']:+.2%}（{best['比值']:.3f}）vs 0050 {best['0050年化']:+.2%}／{best['0050回落']:+.2%}")

    def row(wn, k, sg, arm="主臂"):
        return CT[(CT["世界"] == wn) & (CT["格"] == k) & (CT["段"] == sg) & (CT["臂"] == arm)].iloc[0]
    ex0 = row("主", PK, "探索")
    verdict = {}
    for wn, sg in (("主", "確認"), ("早年", "早年"), ("早年v2", "早年")):
        r_ = row(wn, PK, sg)
        same = (r_["年化贏0050"] == ex0["年化贏0050"]) and (r_["比值贏0050"] == ex0["比值贏0050"])
        verdict[f"{wn}·{sg}"] = {"年化": r_["年化"], "回落": r_["回落"], "比值": r_["比值"], "0050年化": r_["0050年化"], "0050回落": r_["0050回落"], "0050比值": r_["0050比值"],
                                 "年化贏0050": bool(r_["年化贏0050"]), "比值贏0050": bool(r_["比值贏0050"]),
                                 "與探索段方向": "方向一致" if same else "方向不一致", "落點（只描述，⛔ 不是標籤）": placement({"年化贏0050": r_["年化贏0050"], "比值贏0050": r_["比值贏0050"]}),
                                 "標註": "樣本不足，描述級"}
    log(f"[判語] {PK}：{ {k: (v['與探索段方向'], round(v['年化'], 4), round(v['0050年化'], 4)) for k, v in verdict.items()} }")

    # ── 描述臂 ──
    for wn, W in WS.items():
        for k, cf in CELLS.items():
            for stop in ("stop35", "stoprel"):
                E = run_cell(W, cf["form"], cf["rev"], cf["N"], stop=stop)
                RES[(wn, k, stop)] = E
                for sg, seg in SEGS[wn].items():
                    st = seg_stats(W, E, seg)
                    n_stop = sum(1 for p in E["pos"] if p["kind"].startswith("停損"))
                    CROWS.append({"世界": wn, "格": k, "臂": {"stop35": "描述·固定35%停損", "stoprel": "描述·相對停損(2σ)"}[stop], "段": sg,
                                  **{kk: st[kk] for kk in ("窗", "持有年", "年化", "回落", "比值", "回本年數")}, "0050年化": st["0050"]["年化"],
                                  "0050回落": st["0050"]["回落"], "0050比值": st["0050"]["比值"], **crit(st["年化"], st["回落"], st["0050"]), "停損次數（全世界）": n_stop, "_st": st})
            if cf["N"] == 1:
                E = run_cell(W, cf["form"], cf["rev"], 1, mode="alt2")
                RES[(wn, k, "alt2")] = E
                for sg, seg in SEGS[wn].items():
                    st = seg_stats(W, E, seg)
                    CROWS.append({"世界": wn, "格": k, "臂": "描述·第1名買不到改買下一名", "段": sg, **{kk: st[kk] for kk in ("窗", "持有年", "年化", "回落", "比值", "回本年數")},
                                  "0050年化": st["0050"]["年化"], "0050回落": st["0050"]["回落"], "0050比值": st["0050"]["比值"], **crit(st["年化"], st["回落"], st["0050"]),
                                  "與主臂相同": bool(np.array_equal(E["eq"], RES[(wn, k, "主臂")]["eq"])), "_st": st})
        for t3, (form, rev) in TOP3.items():
            E = run_cell(W, form, rev, 3)
            RES[(wn, t3, "top3")] = E
            for sg, seg in SEGS[wn].items():
                st = seg_stats(W, E, seg)
                CROWS.append({"世界": wn, "格": t3, "臂": "描述·前3名等權", "段": sg, **{kk: st[kk] for kk in ("窗", "持有年", "年化", "回落", "比值", "回本年數")},
                              "0050年化": st["0050"]["年化"], "0050回落": st["0050"]["回落"], "0050比值": st["0050"]["比值"], **crit(st["年化"], st["回落"], st["0050"]), "_st": st})
        log(f"[描述臂] {wn} 完成")
    CT = pd.DataFrame(CROWS)
    CT.drop(columns=["_st"]).to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")

    # ── 必報：拿掉貢獻最大那一檔（主臂，每格每段）──
    CONTRIB = {}
    for wn, W in WS.items():
        for k, cf in CELLS.items():
            for sg, seg in SEGS[wn].items():
                CONTRIB[f"{wn}·{k}·{sg}"] = contrib(W, cf["form"], cf["rev"], cf["N"], seg, RES[(wn, k, "主臂")])
        log(f"[拿掉一檔] {wn} 完成")

    # ── 逐年表 ──
    YR = []; RK = []; FIRST = {}
    for wn, W in WS.items():
        cal = W["cal"]; YT = W["YT"]
        for k, cf in CELLS.items():
            E = RES[(wn, k, "主臂")]; eq = E["eq"]
            yr_all = year_ret(eq, W, sorted(YT)); yb_all = year_ret(W["bench"], W, sorted(YT))
            for Y in sorted(YT):
                yi = E["yi"][Y]; e = YT[Y]["e"]; x = YT[Y]["x"]; dY = YT[Y]["d"]; dY1 = YT[Y + 1]["d"] if (Y + 1) in YT else W["n"] - 1
                rk = {i: (r + 1, rr, yo) for r, (i, rr, yo) in enumerate(yi["top"])}
                held = [p for p in E["pos"] if p["entry"] <= e < p["exit"] or (p["entry"] == e)]
                missd = dict(yi["miss"])
                for i in yi["sel"]:
                    s = W["sids"][i]
                    p = next((q for q in E["pos"] if q["i"] == i and q["entry"] <= e and q["exit"] > e), None)
                    if p is not None:
                        px0 = p["ep"] if p["entry"] == e else float(W["C"][i, dY])
                        if p["exit"] <= x:
                            px1 = p["ep"] * (1 + p["gross"]); xd = str(cal[min(p["exit"], W["n"] - 1)].date()) if p["exit"] < W["n"] else "資料尾"; kind = p["kind"]
                        else:
                            px1 = float(W["C"][i, dY1]); xd = "續抱"; kind = "續抱到下一年"
                        r_s = px1 / px0 - 1.0
                    else:
                        r_s = np.nan; xd = None; kind = missd.get(i, "")
                    r1 = rk.get(i, (None, np.nan, (np.nan, None)))
                    dmask = D.disposal_mask(s, cal, W["disp"], after_days=0)
                    YR.append({"世界": wn, "格": k, "持有年": Y, "換股日": str(cal[e].date()), "名次": r1[0], "代號": s, "名稱": W["names"].get(s),
                               "形成期報酬": r1[1], "營收年增": r1[2][0] if cf["rev"] else np.nan, "營收期別": r1[2][1] if cf["rev"] else None,
                               "狀態": "續抱" if i in yi["cont"] else ("買進" if i in yi["bought"] else f"買不到：{missd.get(i, '')}"),
                               "買價（還原）": p["ep"] if p is not None else np.nan, "出場": xd, "出場種類": kind, "個股當年報酬": r_s,
                               "換股日處置中": bool(dmask[e]), "決策日處置中": bool(dmask[YT[Y]["d"]]), "換股日開盤漲停鎖死": bool(W["UPL"][i, e]),
                               "換股日有成交": bool(W["TRD"][i, e]), "組合當年報酬": yr_all[Y], "0050當年報酬": yb_all[Y]})
                if not yi["sel"]:
                    YR.append({"世界": wn, "格": k, "持有年": Y, "換股日": str(cal[e].date()), "狀態": "名單空（全年現金）", "組合當年報酬": yr_all[Y], "0050當年報酬": yb_all[Y]})
                if cf["N"] == 1 and yi["top"]:
                    i = yi["top"][0][0]
                    FIRST[f"{wn}·{k}·{Y}"] = {"代號": W["sids"][i], "名稱": W["names"].get(W["sids"][i]), "形成期報酬": yi["top"][0][1],
                                             "換股日處置中": bool(D.disposal_mask(W["sids"][i], cal, W["disp"], after_days=0)[e]),
                                             "換股日開盤漲停鎖死": bool(W["UPL"][i, e]), "換股日有成交": bool(W["TRD"][i, e]), "買得到": buyable(W, i, e),
                                             "減資假飆核對": fake_check(W, Y, i, cf["form"])}
            if k in ("T1", "T3", "T5"):
                pass
        for form, rev in (("整年", False), ("扣一月", False), ("整年", True)):
            for Y in sorted(YT):
                L, info = ranked(W, Y, form, rev)
                for r, (i, rr, yo) in enumerate(L[:10]):
                    RK.append({"世界": wn, "形成期": form + ("＋營收年增>0" if rev else ""), "持有年": Y, "名次": r + 1, "代號": W["sids"][i], "名稱": W["names"].get(W["sids"][i]),
                               "形成期報酬": rr, "營收年增": yo[0], "營收期別": yo[1], "換股日買得到": buyable(W, i, YT[Y]["e"]), **{f"母體_{kk}": vv for kk, vv in info.items()}})
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "yearly.csv"), index=False, float_format="%.10g")
    pd.DataFrame(RK).to_csv(os.path.join(OUT, "rank_top10.csv"), index=False, float_format="%.10g")

    # ── 先驗（只描述）──
    def g(wn, k, sg, f="年化", arm="主臂"):
        return float(row(wn, k, sg, arm)[f])
    prior = {
        "① 第 1 名的格（T1、T3、T5）確認段都沒有同時贏 0050 年化與比值": all(not (row("主", k, "確認")["年化贏0050"] and row("主", k, "確認")["比值贏0050"]) for k in ("T1", "T3", "T5")),
        "② 前 10 名的回落比第 1 名淺（同形成期、三組×三段）": {f"{a_}vs{b_}·{wn}·{sg}": g(wn, b_, sg, "回落") > g(wn, a_, sg, "回落")
                                                for a_, b_ in (("T1", "T2"), ("T3", "T4"), ("T5", "T6")) for wn, sgs in SEGS.items() for sg in sgs},
        "③ 加營收的年化高於不加的同檔數格": {f"{a_}vs{b_}·{wn}·{sg}": g(wn, a_, sg) > g(wn, b_, sg) for a_, b_ in (("T5", "T1"), ("T6", "T2")) for wn, sgs in SEGS.items() for sg in sgs},
        "④ 挑中那格早年沒有同時贏 0050 年化與比值": {wn: not (row(wn, PK, "早年")["年化贏0050"] and row(wn, PK, "早年")["比值贏0050"]) for wn in ("早年", "早年v2")}}

    # ── 彙總 ──
    def cellsum(wn, k, arm="主臂"):
        out = {}
        for sg in SEGS[wn]:
            st = row(wn, k, sg, arm)["_st"]
            out[sg] = {kk: st[kk] for kk in ("窗", "持有年", "持有年數（日數÷245）", "持有年數（曆年個數）", "年化", "回落", "比值", "回本年數", "谷底日", "段內未回本⇒全曲線回本年數",
                                              "0050", "逐年", "0050逐年", "拿掉最好一年")}
            out[sg]["使用者判準兩項"] = crit(st["年化"], st["回落"], st["0050"])
            if arm == "主臂":
                out[sg]["拿掉貢獻最大那一檔"] = CONTRIB.get(f"{wn}·{k}·{sg}")
        return out
    S = {"登錄": f"PREREG每年買去年漲最多 seq1 sha {REG_SHA}（{regf}）；裁定 seq346／347／348（N_組合 ＋1，6 格挑 1，不算事後重切）",
         "讀法寫死": TIME, "產出時間": now_tpe() + "（台北）", "閘": gates, "壞根": {wn: W["bad_info"] for wn, W in WS.items()},
         "營收": {wn: W["rinfo"] for wn, W in WS.items()},
         "世界": {wn: {"日曆": [str(W["cal"][0].date()), str(W["cal"][-1].date())], "股數": len(W["sids"]), "持有年": [min(W["YT"]), max(W["YT"])],
                     "段": {sg: [str(W["cal"][seg_pos(W, seg)[0]].date()), str(W["cal"][seg_pos(W, seg)[1]].date())] for sg, seg in SEGS[wn].items()}} for wn, W in WS.items()},
         "格定義": CELLS, "退化": {k: DG["格"][f"主·{k}"]["退化"] for k in CELLS},
         "主表": {wn: {k: cellsum(wn, k) for k in CELLS} for wn in WS},
         "挑格": {"格": PK, "探索段過判準格數": int(len(pas)), "探索": {"年化": float(best["年化"]), "回落": float(best["回落"]), "比值": float(best["比值"]),
                                                         "0050": {"年化": float(best["0050年化"]), "回落": float(best["0050回落"]), "比值": float(best["0050比值"])}},
                "挑法": "探索段非退化格中過使用者判準者取比值最高；都沒過取比值最高" + ("（本次：有格過判準）" if len(pas) else "（本次：沒有格過判準 ⇒ 取比值最高）")},
         "判語（裁定 seq348：⛔ 不給合格；最多方向一致／不一致）": verdict,
         "第1名（T1／T3／T5 逐年）": FIRST,
         "描述臂": {wn: {f"{k}·{arm}": cellsum(wn, k, arm) for (w_, k, arm2) in RES if w_ == wn and arm2 != "主臂"
                       for arm in [{"stop35": "描述·固定35%停損", "stoprel": "描述·相對停損(2σ)", "alt2": "描述·第1名買不到改買下一名", "top3": "描述·前3名等權"}[arm2]]} for wn in WS},
         "先驗（只描述）": prior, "結果句必附": SENT, "早年附註": NOTE_EARLY, "停損附註": STOP_NOTE}
    json.dump(S, open(os.path.join(OUT, "TopPrevTW.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    # 查核用：主臂權益與列
    pickle.dump({f"{wn}·{k}": {"eq": RES[(wn, k, "主臂")]["eq"], "first": RES[(wn, k, "主臂")]["first"], "end": RES[(wn, k, "主臂")]["end"],
                               "rows": RES[(wn, k, "主臂")]["rows"], "sel": {Y: [W["sids"][i] for i in RES[(wn, k, "主臂")]["yi"][Y]["sel"]] for Y in W["YT"]}}
                 for wn, W in WS.items() for k in CELLS}, open(os.path.join(WORK, "main_arms.pkl"), "wb"), protocol=5)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 描述統計（台股 1009-1542 §三 ①～⑪、R1／R2、§四 1～5；台股 1009-1559 §三 營量排序占比；裁定 seq321 §四）——回測線子代理。

⛔ 全件是描述：一律不附報酬（不算年化、勝率、之後漲跌）、不計 N。唯一例外 R1／R2（台股信字面「結論方向是否一致」）：
   只報對 0050 標籤（合格／另列／不合格）是否與原版相同、母體檔數、訊號數；⛔ 不印、不存任何年化／回落數字。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLdesc run [--procs 3]
    重寫報告：... -m backtest.researchYLdesc report
    抽樣獨立重算：... -m backtest.researchYLdesc --check

═══ 讀法（⭐ 寫死於 2026-10-10 23:22（台北；原稿誤用 Git Bash 時區標成 15:22，23:25 更正、內容未改），在算任何本件數字之前）═══
 Y0 對象：營量 v1 ＝ researchT1fix #13 T1 版（rerun17 AND 表 edc6f 快照、T1 資料尾補回、主窗 2017-03-02～2026-08-24 進場、⛔ 無大盤閘、
       N20、H60、pick＝relvol、停止交易強制出場開）；營飆 v1 ＝ researchT1fix #1 T1 版（同 AND、t−1 大盤閘 0050 還原收盤 ＞ 200 日均、N10、H120、
       default_rng(1000＋r) 抽籤、r＝0～199）。「訊號」＝ 主窗內 AND 列（營量全部、營飆過閘者）；「買進」＝ 引擎 audit 的買進列
       （營量 r＝0 ＝ resultsYLlist/audit_seed0；營飆 200 顆）。閘：重跑 eq_sha ＝ resultsT1fix/seeds.csv.gz（c13／c1、t1）逐顆相同
 Y1 前瞻段：主窗之後、快照資料尾之前（進場 2026-08-25～2026-09-24；訊號表同一份、不截 w1，引擎同參數重跑）；
       ⚠ 2026-09-25 以後的每日名單不在本快照 ⇒ 不含（列為待決事項）
 Y2「訊號月」＝ research13.and_flags 取的那一列營收期別（panel_rev 裡 signal_pos ≤ 訊號日的最新一列、距離 ≤ 45、rev_hi24）
 ① 下個月營收 ≤ 訊號月營收 × 0.5（掉回一半以上）的占比；下個月缺值另計；對照 ＝ 同期營量母體（原版閘過的面板列）全部股-月
 ② 重大訊息（tw-stock-data main 8425186bd2 的 data/mops/news 2015～2026，~/msdata 已 archive）主旨照 researchNewsCat 的 seq2 分類
       （SEQ2_SRC 逐字取自該檔、exec）第 4 類「併購／合資」；訊號月前 6 個月（含訊號月）、後 6 個月、任一；
       後 6 個月超出新聞資料尾（2026-10）者另計「未滿」；⚠ 庫裡沒有「併表」專欄 ⇒ 以併購類代替（照實寫）
 ③ 景氣循環 ＝ 產業別 ∈ {塑膠工業, 鋼鐵工業, 航運業, 油電燃氣業, 化學工業, 橡膠工業}；產業別 ＝ 月營收彙總表「產業別」欄各檔最後一期值
       （research34.load_revenue 的 ind；證交所／櫃買產業類別單層、約 30 類；⚠ 該欄是現行分類回填、⛔ 不是當時分類）；逐年依訊號日年份
 ④ 各曆月訊號數（訊號日 pos 的月份）；另報每交易日訊號數（÷ 該月交易日數）
 ⑤ 工程／專案認列 ＝ 建材營造（建設）｜資訊服務業（系統整合）｜無塵室名單（本件自訂，⛔ 無官方分類）：2404 漢唐、6196 帆宣、6139 亞翔、
       5536 聖暉、6691 洋基工程、6613 朋億、6667 信紘科、3402 漢科
 ⑥ 訊號日當天橫斷面分位（0＝最小、1＝最大）：母體 ＝ 營量母體來源（load_universe ∩ gate3）當天在存續期內者；
       市值 ＝ 未還原收盤（無成交沿用前收）× stocks/<代號>.csv 的 shares 欄（向前沿用；⚠ 上市在界線日之後 shares 全空 ⇒ 沿用最後值，另報沿用天數）；
       成交金額 ＝ 前 20 個交易日平均成交金額（T−20～T−1、沒成交記 0；＝ patterns amount 口徑）
 ⑦ 每年母體檔數 ＝ 各換股日（research34.rebalance_dates pub_day＝10 的 signal_pos）過閘檔數的年平均與當年曾過閘的不同檔數；
       原版閘 ＝ research34 gate（full20 ∧ 存續 ∧ 非處置（含後 5 日）∧ 非斷點窗 ∧ 20 日均量 ≥ 500 張 ∧ 進場日開盤有值）；
       ⚠ 營量／營飆的正式流動性閘是「20 日均量 ≥ 500 張」（rerun17_build liq_mode＝shares），⛔ 不是 5,000 萬 ⇒ 另報固定 5,000 萬（A0）對照
 ⑧ 條件逐年觸發率 ＝ research11.stock_features 的 eligible 根（≥ 249 根、非 skip、MA100 與 amt_ratio 有值、訊號根與前 20 根無壞根）中
       c1 20 日漲 ≥ 30%、c2 20 根漲停 ≥ 3、c3 成交額 ÷ 前 20 均 ≥ 3、c4 收 ＞ MA100、c5 收 ≥ 250 根最高、5 取 3 的占比（⛔ 未去重）；
       rev_hi24 與流動性閘 ＝ 換股日面板列（原版閘過 ∧ 有營收）的占比；FEATS 14 特徵 ＝ researchSurge6_overlap.FEATS（~/s5work Q.npy；
       有 ＝ Q 碼相等，分母 ＝ 有 K 棒且該特徵有值的股-日；另報有值率）；2026 標「部分年、8/10 起處置新制」
       飆股基準率 ＝ seq6 網格（~/s6work events／hdef6，2021-01～2026-08）全母體、合格格（兩段事件 ≥ 30）各格「當年起漲事件數 ÷ 當年定義域股-日」取格中位；
       另報 seq5 全日曆鏈（~/s5work events／hdef，2005 起、2015 前只上市）同一批格的逐年版（⚠ 鏈不同、只當參考）；⛔ 不寫「N 天漲一倍」
 ⑨ 換股日 ＝ 有買進的日子；持股 ＝ 當天買進後的全部部位；兩兩相關 ＝ 前 60 個交易日（t−60～t−1）日報酬（引擎 closes，還原、ffill）的相關係數平均
       （該檔 60 日內有效報酬 ≥ 40 才算）；等效獨立檔數 ＝ N ÷ (1＋(N−1)ρ)；產業 ＝ ③ 的單層產業別；
       同產業上限 3 擠掉 ＝ 當天新買中超過上限的筆數（既有持股不動）；同池補 ＝ 當天其他未買候選中所屬產業仍有空間者可補的筆數；
       大盤敏感度 ＝ 持股等權日報酬對 0050 日報酬的斜率，分 0050 漲日、跌日各算（同 60 日窗；⛔ 是進場前的共動、不是之後的報酬）；
       逐年依換股日；營飆 200 顆各換股日併在一起取中位／占比
 ⑩ 營飆主窗訊號（過閘）進場日 e：0050 還原收盤[e−1] ÷ 200 日均[e−1] − 1 的分佈、|距離| ≤ 3% 占比；
       判定日 e−1 前後挪 k＝1～3 個交易日（e−1±1..k 任一天）大盤閘狀態不同的占比；⑩ 末：正式規則 0050 用的價（查程式）
 ⑪ 六種寫法（都用 e−1 以前的資料）：每日（現行）｜緩衝 ±2%（收 ＞ 均×1.02 才開、收 ＜ 均×0.98 才關，中間維持前一天）｜緩衝 ±3%｜
       連 3 天確認（連 3 天在線上才開、連 3 天在線下才關）｜月初看一次（e 所在月份第一個交易日的前一天的每日狀態，整月用）｜
       10 個月均線月底（前一個月底月收盤 ＞ 前 10 個月底月收盤平均）；對象 ＝ 全部 AND 列（2016-01 起；另報主窗）；
       八段大跌期間：各寫法允許的新進場訊號筆數＋營飆實際買進（200 顆中位）；AND 表 2016-01 才開始 ⇒ 更早的段標「訊號表沒有」
 R1／R2（台股 1542 §三，⛔ 寄出前已寫死）：只換流動性閘，其餘（存續、處置、斷點窗、營收、5 取 3、引擎）不動
       R1 ＝ 換股日 20 日均成交金額（⑥ 口徑）在當天存續母體中排名前 X%（同值依代號序），X ＝ 2016-01 第一個換股日（period 2015-12 的 signal_pos
       2016-01-08）原版閘過關檔數 ÷ 當天存續母體檔數（固定）；R2 ＝ 20 日均成交金額 ≥ 5,000 萬 × 大盤 20 日均成交金額[sp] ÷ 大盤 20 日均成交金額[sp0]；
       大盤 ＝ data/meta/market_turnover 上市 amount_ntd ＋ 上櫃 amount_k_ntd×1000（origin/main，⛔ 不用日檔加總），同 T−20～T−1；
       另報 A0 固定 5,000 萬；不加絕對下限
       流程：自建面板（research34.process_stock 同式，多記閘的各分量）⇒ 原版閘 ＝ panel_rev 逐列相同（閘 P）⇒ 各版面板 ⇒ research13.and_flags
       ⇒ researchp1.attach_features（relvol）⇒ 原版 AND ＝ sig_edc6f/and_signals.csv.gz 逐列相同（閘 A）⇒ rerun17.setup_and(t1=True)
       ⇒ 營飆 200 顆、營量 r＝0 ⇒ researchT1fix.label（對 0050）；原版標籤與 eq_sha ＝ resultsT1fix（閘 E）
 營量排序（台股 1559 §三；比照 PREREG營飆排名 §一）：主窗有訊號日、候選（當天訊號去掉已持有）＞ 空槽日（槽滿／有作用）、
       直接差（relvol 路徑上每個有作用日改成隨機取的期望換掉筆數 ＝ Σ 空槽×(1−空槽÷候選)）、
       整條路徑總差（抽籤版 pick＝None default_rng(7000＋r) 200 顆，relvol 版買進不在抽籤版的筆數 ÷ relvol 版買進）
 §四-1 FEATS 14 個逐一標是否用到處置／注意／固定金額／固定張數／固定價位／固定漲幅；§四-2 只列要改的地方與建議文字（⛔ 不改程式）；
 §四-3 本報告的制度斷點行（data/meta/tw_regime_log origin/main，生效日落在 2016-01-04～2026-09-24 者）＋ ⑦；
 §四-4 grep 正式策略與每日名單程式的固定比率／漲幅／金額張數（檔名＋行號 ⇒ fixed_rules.csv）；
 §四-5 個股年化波動 ＝ 有效 K 棒相鄰收盤報酬（還原、跳過 skip 根）標準差 × √245、當年 ≥ 100 個報酬；母體 ＝ 當年曾過原版閘者；各年中位
═══ 補記（看過第一輪輸出後，⛔ 不改上面任何定義，只改標示）═══
 ・AND 表實際進場從 2017-02-13 起（rev_hi24 要前 24 期，revenue_hist 2015-01 起）⇒ ⑪ 標「全部 AND（進場 2017-02 起）」、⑧ 2016 年營收與 AND 欄依構造為 0
 ・② 後 6 個月「窗已滿」改為訊號月＋6 ＜ 新聞最後一則的月份（嚴格小於；第一輪用 ≤，2026-10 只有 2 天新聞）
輸出 backtest/resultsYLdesc/：REPORT.md、營量營飆描述統計.html、summary.json、check.json、各項 csv；工作檔 ~/ydwork/（⛔ 不進 repo）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR  # noqa: E402

RR.use_snapshot()
from backtest import data as D  # noqa: E402
from backtest import listexit_lines as L  # noqa: E402
from backtest import patterns as PT  # noqa: E402
from backtest import research11 as R  # noqa: E402
from backtest import research13 as R13  # noqa: E402
from backtest import research34 as R34  # noqa: E402
from backtest import researchp1 as P1  # noqa: E402
from backtest import researchT1fix as T1  # noqa: E402
from backtest import universe_gate as UG  # noqa: E402

TIME = "2026-10-10 23:22（台北）"
OUT = "backtest/resultsYLdesc"
WORK = os.path.expanduser("~/ydwork")
NEWS = os.path.expanduser("~/msdata/8425186bd20cdef4d39ac039ad2a6eda0903a8bb/data/mops/news")
WORK5 = os.path.expanduser("~/s5work"); WORK6 = os.path.expanduser("~/s6work")
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
CYC = ["塑膠工業", "鋼鐵工業", "航運業", "油電燃氣業", "化學工業", "橡膠工業"]
CLEAN = {"2404": "漢唐", "6196": "帆宣", "6139": "亞翔", "5536": "聖暉", "6691": "洋基工程", "6613": "朋億", "6667": "信紘科", "3402": "漢科"}
PROJ_IND = {"建材營造": "建設", "資訊服務業": "系統整合"}
CRASH = [("2007-10～2008-11", "2007-10-01", "2008-11-30"), ("2015-04～2016-01", "2015-04-01", "2016-01-31"), ("2018", "2018-01-01", "2018-12-31"),
         ("2020-01～03", "2020-01-01", "2020-03-31"), ("2022", "2022-01-01", "2022-12-31"), ("2024-07～08", "2024-07-01", "2024-08-31"),
         ("2025-01～04", "2025-01-01", "2025-04-30"), ("2026-06～07", "2026-06-01", "2026-07-31")]
VARS = ["每日（現行）", "緩衝±2%", "緩衝±3%", "連3天確認", "月初看一次", "10個月均線月底"]
GATES = ["原版", "A0", "R1", "R2"]
GNAME = {"原版": "原版（20 日均量 ≥ 500 張）", "A0": "A0 固定 5,000 萬（對照）", "R1": "R1 排名版", "R2": "R2 連動版"}
_G: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def q5(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "p10": float(np.percentile(x, 10)), "p25": float(np.percentile(x, 25)), "中位": float(np.median(x)),
            "p75": float(np.percentile(x, 75)), "p90": float(np.percentile(x, 90))}


def per_add(p, k):
    y, m = int(p[:4]), int(p[5:]); m0 = y * 12 + m - 1 + k
    return f"{m0 // 12:04d}-{m0 % 12 + 1:02d}"


# ═════════════ 0 共用：日曆、AND（T1）、引擎 ctx ═════════════
def base_ctx():
    if "ctx" in _G:
        return _G["ctx"]
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; G = RR._G
    ctx["AND"] = G["AND"].copy(); ctx["regime"] = G["regime"].copy(); ctx["bench"] = G["bench"].copy()
    sids = sorted(ctx["closes"])
    ctx["SF"] = R.stop_force_days(R.valid_from_data(sids, ctx["mk"], cal), ctx["w1"])
    e = ctx["AND"]["entry_pos"].to_numpy()
    ctx["sig_yf_fwd"] = ctx["AND"][ctx["regime"][e - 1] & (e >= ctx["w0"])]
    ctx["sig_yl_fwd"] = ctx["AND"][e >= ctx["w0"]]
    _G["ctx"] = ctx
    return ctx


# ═════════════ 1 引擎（audit）═════════════
def _eng(args):
    kind, r = args
    ctx = _G["ctx"]; SF = ctx["SF"]; au = []
    fwd = kind.endswith("_fwd")
    if kind.startswith("yf"):
        sig = ctx["sig_yf_fwd"] if fwd else ctx["sig"]
        o = R.simulate_mtm(sig, "H120", 10, np.random.default_rng(1000 + r), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True,
                           audit=au, stop_force=SF)
    else:
        sig = ctx["sig_yl_fwd"] if fwd else ctx["sig13"]
        pick = None if kind.startswith("yllot") else "relvol"
        o = R.simulate_mtm(sig, "H60", 20, np.random.default_rng(7000 + r), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                           pick=pick, queue_days=0, return_equity=True, audit=au, stop_force=SF)
    eq = np.asarray(o["equity"], float)
    return {"kind": kind, "r": r, "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16],
            "au": [(int(a["t"]), a["sid"], a["side"]) for a in au]}


def run_engine(procs):
    ctx = base_ctx()
    jobs = [("yl", 0), ("yl_fwd", 0)] + [("yf", r) for r in range(200)] + [("yf_fwd", r) for r in range(200)] + [("yllot", r) for r in range(200)]
    with Pool(procs) as pool:
        res = pool.map(_eng, jobs, chunksize=4)
    ref = pd.read_csv(os.path.join("backtest/resultsT1fix/seeds.csv.gz"), dtype={"eq_sha": str})
    ref = ref[ref["var"] == "t1"]
    gate = {}
    for kind, key in (("yl", "c13"), ("yf", "c1")):
        mine = {x["r"]: x["eq_sha"] for x in res if x["kind"] == kind}
        rr = ref[ref["key"] == key].set_index("r")["eq_sha"]
        gate[f"{kind}＝resultsT1fix {key} t1"] = {"顆數": len(mine), "不同": int(sum(mine[r] != rr.loc[r] for r in mine))}
    a0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str})
    b0 = [(int(t), s) for t, s in zip(a0.loc[a0["side"] == "buy", "t"], a0.loc[a0["side"] == "buy", "sid"])]
    yl = next(x for x in res if x["kind"] == "yl")
    b1 = [(t, s) for t, s, sd in yl["au"] if sd == "buy"]
    gate["營量 r0 買進列＝resultsYLlist/audit_seed0"] = {"筆數": len(b1), "相同": b0 == b1}
    rows = [(x["kind"], x["r"], t, s, sd) for x in res for t, s, sd in x["au"]]
    AU = pd.DataFrame(rows, columns=["kind", "r", "t", "sid", "side"])
    AU.to_csv(os.path.join(WORK, "audits.csv.gz"), index=False)
    json.dump(gate, open(os.path.join(WORK, "gate_engine.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[閘 E 引擎] {json.dumps(gate, ensure_ascii=False)}")
    return AU, gate


# ═════════════ 2 面板（research34.process_stock 同式，多記閘分量）＋ 逐檔日曆陣列 ═════════════
def _pinit(cal, disp, rev, rdates, lo, hi):
    _G.update(cal=cal, disp=disp, rev=rev, rdates=rdates, lo=lo, hi=hi)


def pworker(args):
    sid, market, first_seen, last_seen = args
    cal, disp, rev, rdates, lo, hi = (_G[k] for k in ("cal", "disp", "rev", "rdates", "lo", "hi"))
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    f = PT.Frame(df, st.event_dates)
    in_life = (cal >= first_seen) & (cal <= last_seen)
    dmask = D.disposal_mask(sid, cal, disp)
    jw = D.breakpoint_window(D.breakpoints(df, st.event_dates), len(cal), R34.H_FORWARD, R34.L_LOOKBACK)
    base = f.full20 & in_life & ~dmask & ~jw
    amt = df["amount"].fillna(0.0)
    amt20 = amt.rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=lambda c: c in ("date", "close", "shares"))
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
    rc = pd.to_numeric(raw["close"], errors="coerce").reindex(cal)
    shs = pd.to_numeric(raw["shares"], errors="coerce").reindex(cal) if "shares" in raw else pd.Series(np.nan, index=cal)
    has_sh = shs.notna().to_numpy()
    last_sh = pd.Series(np.where(has_sh, np.arange(len(cal)), np.nan)).ffill().to_numpy()
    mcap = (rc.ffill() * shs.ffill()).to_numpy(float)
    sh_age = np.arange(len(cal)) - last_sh
    has_rev = sid in rev.columns
    rv = rev[sid] if has_rev else None
    periods = list(rev.index)
    rows = []
    for k, p in enumerate(periods):
        if p not in rdates:
            continue
        sp, ep = rdates[p]
        if not (lo <= sp <= hi) or ep >= len(cal):
            continue
        base_ok = bool(base[sp]) and not np.isnan(f.o[ep])
        hi24 = False; rv0 = np.nan
        if has_rev and not np.isnan(rv.iloc[k]):
            rv0 = float(rv.iloc[k]); hist = rv.iloc[max(0, k - 24):k]
            hi24 = bool(len(hist) == 24 and hist.notna().all() and rv0 >= hist.max())
        rows.append((sid, p, sp, ep, base_ok, bool(f.liquid[sp]), float(amt20[sp]), bool(in_life[sp]), hi24, rv0))
    return sid, rows, amt20.astype(np.float32), mcap.astype(np.float32), sh_age.astype(np.float32), in_life


def build_panel(procs):
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    PT.PARAMS["liq_mode"] = "shares"
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = R34.load_revenue()
    rdates = R34.rebalance_dates(list(rev.index), cal, 10)
    lo = int(cal.searchsorted(pd.Timestamp(R34.SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(R34.SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    rows = []; A20 = {}; MC = {}; SA = {}; LIFE = {}
    with Pool(procs, initializer=_pinit, initargs=(cal, disp, rev, rdates, lo, hi)) as pool:
        for i, r in enumerate(pool.imap_unordered(pworker, jobs, chunksize=8)):
            if r:
                sid, rr, a20, mc, sa, life = r
                rows += rr; A20[sid] = a20; MC[sid] = mc; SA[sid] = sa; LIFE[sid] = life
            if (i + 1) % 500 == 0:
                log(f"  面板 {i + 1}/{len(jobs)}")
    PN = pd.DataFrame(rows, columns=["stock_id", "period", "signal_pos", "entry_pos", "base_ok", "liq_sh", "amt20", "in_life", "rev_hi24", "rev"])
    PN = PN.sort_values(["stock_id", "signal_pos"]).reset_index(drop=True)
    PN.to_csv(os.path.join(WORK, "panel_all.csv.gz"), index=False)
    sids = sorted(A20)
    np.savez(os.path.join(WORK, "arrays.npz"), sids=np.array(sids), amt20=np.stack([A20[s] for s in sids]), mcap=np.stack([MC[s] for s in sids]),
             sh_age=np.stack([SA[s] for s in sids]), life=np.stack([LIFE[s] for s in sids]))
    # 閘 P：原版閘 ＝ panel_rev
    ref = pd.read_csv("backtest/resultsN17/sig_edc6f/panel_rev.csv.gz", dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos", "rev_hi24"])
    ref["rev_hi24"] = ref["rev_hi24"].fillna(False).astype(bool)
    mine = PN[PN["base_ok"] & PN["liq_sh"]][["stock_id", "period", "signal_pos", "rev_hi24"]]
    m = mine.merge(ref, on=["stock_id", "period"], how="outer", suffixes=("", "_r"), indicator=True)
    gp = {"自建原版列": int(len(mine)), "panel_rev 列": int(len(ref)), "只在自建": int((m["_merge"] == "left_only").sum()),
          "只在 panel_rev": int((m["_merge"] == "right_only").sum()),
          "signal_pos 不同": int((m["_merge"] == "both").sum() - ((m["signal_pos"] == m["signal_pos_r"]) & (m["_merge"] == "both")).sum()),
          "rev_hi24 不同": int(((m["rev_hi24"] != m["rev_hi24_r"]) & (m["_merge"] == "both")).sum())}
    gp["全過"] = gp["只在自建"] == 0 and gp["只在 panel_rev"] == 0 and gp["signal_pos 不同"] == 0 and gp["rev_hi24 不同"] == 0
    json.dump(gp, open(os.path.join(WORK, "gate_panel.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[閘 P 面板] {json.dumps(gp, ensure_ascii=False)}")
    if not gp["全過"]:
        raise SystemExit("⛔ 閘 P 不過")
    return PN


def market_turnover(cal):
    p = os.path.join(WORK, "mkt.csv")
    if not os.path.exists(p):
        sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
        import io
        tw = pd.read_csv(io.StringIO(subprocess.run(["git", "show", f"{sha}:data/meta/market_turnover/twse_market_turnover.csv"],
                                                    capture_output=True, text=True).stdout))
        tp = pd.read_csv(io.StringIO(subprocess.run(["git", "show", f"{sha}:data/meta/market_turnover/tpex_market_turnover.csv"],
                                                    capture_output=True, text=True).stdout))
        m = pd.DataFrame({"date": pd.to_datetime(tw["date"]), "twse": tw["amount_ntd"].astype(float)}).merge(
            pd.DataFrame({"date": pd.to_datetime(tp["date"]), "tpex": tp["amount_k_ntd"].astype(float) * 1000}), on="date", how="left")
        m["sha"] = sha
        m.to_csv(p, index=False)
    m = pd.read_csv(p, parse_dates=["date"])
    s = m.set_index("date").reindex(cal)
    tot = (s["twse"] + s["tpex"]).to_numpy(float)
    m20 = pd.Series(tot).rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
    return m20, str(m["sha"].iloc[0]), int(np.isnan(tot).sum())


def gate_variants(PN, cal):
    """回 {版: 布林 Series（對 PN 列）}、X、sp0、門檻資訊。"""
    A = np.load(os.path.join(WORK, "arrays.npz"))
    sids = list(A["sids"]); amt20 = A["amt20"]; life = A["life"]
    sp_all = sorted(PN["signal_pos"].unique())
    p0 = PN[PN["period"] == "2015-12"]["signal_pos"].unique()
    assert len(p0) == 1; sp0 = int(p0[0])
    out = {"原版": (PN["base_ok"] & PN["liq_sh"]).to_numpy(), "A0": (PN["base_ok"] & (PN["amt20"] >= 5e7)).to_numpy()}
    # R1：當天存續母體排名
    M = {}; RK = {}
    for sp in sp_all:
        alive = life[:, sp] & np.isfinite(amt20[:, sp])
        idx = np.flatnonzero(alive)
        v = amt20[idx, sp].astype(float)
        order = np.lexsort((np.array(sids)[idx], -v))          # 金額大者先、同值依代號
        rk = np.empty(len(idx), int); rk[order] = np.arange(len(idx))
        M[sp] = int(len(idx)); RK[sp] = {sids[i]: int(rk[j]) for j, i in enumerate(idx)}
    n0 = int(out["原版"][PN["signal_pos"].to_numpy() == sp0].sum())
    X = n0 / M[sp0]
    kcut = {sp: int(np.floor(X * M[sp] + 1e-9)) for sp in sp_all}
    r1 = np.array([bool(b) and (RK[sp].get(s, 10 ** 9) < kcut[sp]) for s, sp, b in zip(PN["stock_id"], PN["signal_pos"], PN["base_ok"])])
    out["R1"] = r1
    m20, msha, mnan = market_turnover(cal)
    thr = {sp: 5e7 * m20[sp] / m20[sp0] for sp in sp_all}
    out["R2"] = (PN["base_ok"].to_numpy() & (PN["amt20"].to_numpy() >= PN["signal_pos"].map(thr).to_numpy()))
    info = {"sp0": str(cal[sp0].date()), "sp0_原版過關": n0, "sp0_存續母體": M[sp0], "X": X, "R2_門檻_首末": [float(thr[sp_all[0]]), float(thr[sp_all[-1]])],
            "R2_門檻_逐年中位（億）": {}, "大盤成交金額 origin/main": msha, "大盤序列在日曆上缺值天數": mnan,
            "存續母體_首末": [M[sp_all[0]], M[sp_all[-1]]], "M": {str(cal[sp].date()): M[sp] for sp in sp_all}}
    yrs = pd.Series({sp: cal[sp].year for sp in sp_all})
    for y, g in yrs.groupby(yrs):
        info["R2_門檻_逐年中位（億）"][int(y)] = float(np.median([thr[sp] for sp in g.index]) / 1e8)
    return out, info


def build_and(PN, GV, procs, cal):
    mk = D.load_universe().set_index("stock_id")["market"]
    S = pd.read_csv("backtest/resultsN17/sig_edc6f/signals_S.csv.gz", dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    FL = {}
    for g, m in GV.items():
        pn = PN[m][["stock_id", "signal_pos", "rev_hi24"]].copy()
        FL[g], _ = R13.and_flags(S, pn)
    anyf = np.zeros(len(S), bool)
    for v in FL.values():
        anyf |= v
    AU = S[anyf].copy()
    missing, mism = P1.attach_features(AU, S, cal, mk, procs)
    out = {}
    for g in GATES:
        A = AU.loc[S.index[FL[g]]].reset_index(drop=True)
        p = os.path.join(WORK, f"and_{g}.csv.gz"); A.to_csv(p, index=False)
        out[g] = p
    ref = pd.read_csv("backtest/resultsN17/sig_edc6f/and_signals.csv.gz", dtype={"sid": str})
    mine = pd.read_csv(out["原版"], dtype={"sid": str})
    same = list(ref.columns) == list(mine.columns) and len(ref) == len(mine) and ref.astype(str).equals(mine.astype(str))
    ga = {"原版 AND 列": int(len(mine)), "sig_edc6f 列": int(len(ref)), "逐列逐欄相同（字串）": bool(same), "relvol 缺": int(AU["relvol"].isna().sum()),
          "attach 讀不到": len(missing), "k↔pos 不符": int(mism), "各版 AND 列": {g: int(FL[g].sum()) for g in GATES}}
    json.dump(ga, open(os.path.join(WORK, "gate_and.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[閘 A AND] {json.dumps(ga, ensure_ascii=False)}")
    if not same:
        raise SystemExit("⛔ 閘 A 不過")
    return out


def _veng(args):
    fam, r = args
    E = _G["E"]
    if fam == "yf":
        o = R.simulate_mtm(E["sig"], "H120", 10, np.random.default_rng(1000 + r), E["closes"], E["opens"], E["ncal"], return_equity=True, stop_force=E["SF"])
    else:
        o = R.simulate_mtm(E["sig13"], "H60", 20, np.random.default_rng(7000 + r), E["closes"], E["opens"], E["ncal"], log=[], d_max=None,
                           pick="relvol", queue_days=0, return_equity=True, stop_force=E["SF"])
    eq = np.asarray(o["equity"], float)
    c, m, _ = RR.win_metrics(eq, o["first"], o["end"], E["w0"], E["w1"])
    return fam, r, c, m, hashlib.sha256(eq.tobytes()).hexdigest()[:16]


def variant_labels(paths, procs, cal):
    """⛔ 只回標籤；年化／回落只在記憶體裡比門檻，不寫檔、不印。"""
    mk = D.load_universe().set_index("stock_id")["market"]
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}); ref = ref[ref["var"] == "t1"]
    res = {}
    for g in GATES:
        RR.setup_and(cal, paths[g], "branch", log, t1=True)
        G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
        inwin = (e >= G["w0"]) & (e <= G["w1"])
        sig = AND[G["regime"][e - 1] & inwin]; sig13 = AND[inwin]
        SF = R.stop_force_days(R.valid_from_data(sorted(G["closes"]), mk, cal), G["w1"])
        _G["E"] = dict(sig=sig, sig13=sig13, closes=G["closes"], opens=G["opens"], ncal=G["ncal"], w0=G["w0"], w1=G["w1"], SF=SF)
        with Pool(procs) as pool:
            out = pool.map(_veng, [("yf", r) for r in range(200)] + [("yl", 0)], chunksize=4)
        yf = [x for x in out if x[0] == "yf"]; yl = [x for x in out if x[0] == "yl"][0]
        lab_yf = T1.label(float(np.median([x[2] for x in yf])), float(np.median([x[3] for x in yf])))[0]
        lab_yl = T1.label(float(yl[2]), float(yl[3]))[0]
        row = {"營飆訊號": int(len(sig)), "營量訊號": int(len(sig13)), "營飆標籤": lab_yf, "營量標籤": lab_yl, "AND 檔數": int(AND["sid"].nunique())}
        if g == "原版":
            r1 = ref[ref["key"] == "c1"].set_index("r")["eq_sha"]; r13 = ref[ref["key"] == "c13"].set_index("r")["eq_sha"]
            row["閘E_營飆 eq_sha 不同"] = int(sum(x[4] != r1.loc[x[1]] for x in yf))
            row["閘E_營量 eq_sha 不同"] = int(yl[4] != r13.loc[0])
        res[g] = row
        log(f"[版 {g}] {json.dumps(row, ensure_ascii=False)}")
        del _G["E"]
    return res


# ═════════════ 3 逐檔 K 棒：⑧ 條件觸發率、§四-5 波動 ═════════════
def bworker(args):
    sid, market = args
    B = R.load_bars(sid, market, _G["cal"])
    if B is None:
        return None
    idx, dates, o, c, amt, up, skip, next_bad = (B[k] for k in ("idx", "dates", "o", "c", "amt", "up", "skip", "next_bad"))
    n = len(idx)
    ret20 = np.array(c / np.roll(c, 20) - 1, dtype=float); ret20[:20] = np.nan
    nup20 = pd.Series(up.astype(int)).rolling(20, min_periods=20).sum().to_numpy(float)
    amt_prev20 = np.array(R._roll_mean(np.roll(amt, 1), 20), dtype=float); amt_prev20[:21] = np.nan
    amt_ratio = amt / amt_prev20
    ma100 = R._roll_mean(c, 100); hi250 = R._roll_max(c, 250)
    nb_sig = np.array([next_bad[max(0, k - 20)] for k in range(n)])
    elig = (np.arange(n) >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(amt_ratio)
    elig &= nb_sig > np.arange(n)
    with np.errstate(invalid="ignore"):
        cs = np.c_[ret20 >= 0.30, nup20 >= 3, amt_ratio >= 3.0, c > ma100, c >= hi250]
    score = cs.sum(1)
    yr = dates.year.to_numpy()
    out = {"sid": sid, "cnt": {}, "vol": {}}
    for y in np.unique(yr[elig]):
        m = elig & (yr == y)
        out["cnt"][int(y)] = [int(m.sum())] + [int((cs[:, j] & m).sum()) for j in range(5)] + [int(((score >= 3) & m).sum())]
    # 波動：相鄰有效 K 棒報酬，該根與前一根皆非 skip、該根非壞根
    bad = np.zeros(n, bool); bad[np.flatnonzero(next_bad[:n] == np.arange(n))] = True
    r = c[1:] / c[:-1] - 1
    ok = ~skip[1:] & ~bad[1:] & np.isfinite(r)
    ry = yr[1:]
    for y in np.unique(ry[ok]):
        x = r[ok & (ry == y)]
        if len(x) >= 100:
            out["vol"][int(y)] = (float(np.std(x, ddof=1) * np.sqrt(245)), int(len(x)))
    return out


def build_bars(procs):
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    _G["cal"] = cal
    rows = []; vols = []
    with Pool(procs) as pool:
        for r in pool.imap_unordered(bworker, list(zip(uni["stock_id"], uni["market"])), chunksize=8):
            if r is None:
                continue
            for y, v in r["cnt"].items():
                rows.append([r["sid"], y] + v)
            for y, (v, nn) in r["vol"].items():
                vols.append((r["sid"], y, v, nn))
    C = pd.DataFrame(rows, columns=["sid", "year", "elig", "c1", "c2", "c3", "c4", "c5", "score3"])
    V = pd.DataFrame(vols, columns=["sid", "year", "vol", "n"])
    C.to_csv(os.path.join(WORK, "cond_counts.csv.gz"), index=False); V.to_csv(os.path.join(WORK, "vol.csv.gz"), index=False)
    return C, V


# ═════════════ 4 各項 ═════════════
def used_period(sig, panel_rev):
    by = {s: (g["signal_pos"].to_numpy(), g["period"].to_numpy(), g["rev_hi24"].to_numpy(bool)) for s, g in panel_rev.sort_values(["stock_id", "signal_pos"]).groupby("stock_id")}
    out = []
    for sid, pos in zip(sig["sid"], sig["pos"]):
        sp, per, hi = by[sid]
        j = int(np.searchsorted(sp, pos, side="right")) - 1
        assert j >= 0 and pos - sp[j] <= R13.STALE_MAX and hi[j]
        out.append(per[j])
    return out


def news_ma():
    src = open("backtest/researchNewsCat.py", encoding="utf-8").read()
    m = re.search(r"SEQ2_SRC = '''(.*?)'''", src, re.S)
    ns = {}; exec(compile(m.group(1), "seq2", "exec"), ns)
    fs = sorted(glob.glob(os.path.join(NEWS, "20[12][0-9].csv")))
    fs = [f for f in fs if int(os.path.basename(f)[:4]) >= 2015]
    N = pd.concat([pd.read_csv(f, dtype=str, usecols=["date", "stock_id", "subject"]) for f in fs])
    N = N.dropna(subset=["subject"])
    N["cat"] = [ns["classify"](s) for s in N["subject"]]
    M = N[N["cat"] == 4].copy(); M["ym"] = M["date"].str[:7]
    last = N["date"].max()
    return set(zip(M["stock_id"], M["ym"])), last, hashlib.sha256(m.group(1).encode()).hexdigest()[:16], len(N), len(M)


def ma_flags(pairs, maset, last_ym):
    out = []
    for sid, p in pairs:
        pre = any((sid, per_add(p, -k)) in maset for k in range(0, 7))
        post = any((sid, per_add(p, k)) in maset for k in range(1, 7))
        full = per_add(p, 6) < last_ym
        out.append((pre, post, full))
    return np.array(out, bool).reshape(-1, 3)


def holdings_from_audit(au):
    """au：(t, sid, side) 依引擎順序 ⇒ {t: (before_set, bought_list)}（只記有買進的日子；先處理當天賣出）。"""
    held = set(); out = {}
    by = {}
    for t, s, sd in au:
        by.setdefault(t, []).append((s, sd))
    for t in sorted(by):
        before = None; bought = []
        for s, sd in by[t]:
            if sd == "sell":
                held.discard(s)
        before = set(held)
        for s, sd in by[t]:
            if sd == "buy":
                bought.append(s); held.add(s)
        if bought:
            out[t] = (before, bought)
    return out


def conc_metrics(H, ent, ind, closes, bench, cal, N):
    rows = []
    for t, (before, bought) in sorted(H.items()):
        hold = sorted(before | set(bought))
        n = len(hold)
        lo = max(1, t - 60)
        Rm = np.array([closes[s][lo - 1:t] for s in hold], float)
        rr = Rm[:, 1:] / Rm[:, :-1] - 1
        okc = (np.isfinite(rr).sum(1) >= 40) & (np.nanstd(rr, axis=1) > 0)
        rho = np.nan
        if okc.sum() >= 2:
            x = rr[okc]
            df = pd.DataFrame(x.T)
            cm = df.corr(min_periods=40).to_numpy()
            iu = np.triu_indices(len(x), 1)
            rho = float(np.nanmean(cm[iu]))
        neff = n / (1 + (n - 1) * rho) if np.isfinite(rho) and (1 + (n - 1) * rho) > 0 else np.nan
        inds = pd.Series([ind.get(s, "未知") for s in hold]).value_counts()
        # 大盤敏感度
        b = bench[lo - 1:t]; rb = b[1:] / b[:-1] - 1
        bk = np.nanmean(np.where(np.isfinite(rr), rr, np.nan), axis=0)
        bu = bd = np.nan
        for sgn in (1, -1):
            mm = np.isfinite(bk) & np.isfinite(rb) & ((rb > 0) if sgn > 0 else (rb < 0))
            if mm.sum() >= 10 and np.var(rb[mm]) > 0:
                v = float(np.cov(bk[mm], rb[mm])[0, 1] / np.var(rb[mm], ddof=1))
                if sgn > 0:
                    bu = v
                else:
                    bd = v
        # 同產業上限 3
        cb = pd.Series([ind.get(s, "未知") for s in before]).value_counts().to_dict()
        cn = pd.Series([ind.get(s, "未知") for s in bought]).value_counts().to_dict()
        sq = {}
        for i, k in cn.items():
            ex = cb.get(i, 0) + k - 3
            if ex > 0:
                sq[i] = min(k, ex)
        qn = sum(sq.values())
        filled = 0
        if qn:
            pool_ = [s for s in ent.get(t, []) if s not in before and s not in bought]
            room = {}
            cnt_after = {i: cb.get(i, 0) + cn.get(i, 0) - sq.get(i, 0) for i in set(cb) | set(cn)}
            pc = pd.Series([ind.get(s, "未知") for s in pool_]).value_counts().to_dict() if pool_ else {}
            for i, k in pc.items():
                room[i] = min(k, max(0, 3 - cnt_after.get(i, 0)))
            filled = min(qn, sum(room.values()))
        rows.append({"t": t, "年": cal[t].year, "日": str(cal[t].date()), "持股數": n, "ρ": rho, "等效獨立檔數": neff, "最大產業檔數": int(inds.iloc[0]),
                     "最大產業": inds.index[0], "超過3檔": bool(inds.iloc[0] > 3), "擠掉筆數": qn, "同池可補": filled, "β漲日": bu, "β跌日": bd})
    return pd.DataFrame(rows)


def gate_states(bench, cal):
    ma = pd.Series(bench).rolling(200, min_periods=200).mean().to_numpy()
    n = len(bench); d = np.where(np.isfinite(ma), bench / ma - 1, np.nan)
    S = {}
    S["每日（現行）"] = bench > ma
    for nm, x in (("緩衝±2%", 0.02), ("緩衝±3%", 0.03)):
        s = np.zeros(n, bool); cur = None
        for t in range(n):
            if not np.isfinite(ma[t]):
                continue
            if cur is None:
                cur = bool(bench[t] > ma[t])
            elif bench[t] > ma[t] * (1 + x):
                cur = True
            elif bench[t] < ma[t] * (1 - x):
                cur = False
            s[t] = cur
        S[nm] = s
    s = np.zeros(n, bool); cur = None; up = dn = 0
    for t in range(n):
        if not np.isfinite(ma[t]):
            continue
        a = bench[t] > ma[t]
        up = up + 1 if a else 0; dn = dn + 1 if not a else 0
        if cur is None:
            cur = bool(a)
        elif up >= 3:
            cur = True
        elif dn >= 3:
            cur = False
        s[t] = cur
    S["連3天確認"] = s
    ym = cal.year * 12 + cal.month
    first = {}
    for t in range(n):
        first.setdefault(ym[t], t)
    daily = S["每日（現行）"]
    S["月初看一次"] = np.array([bool(daily[first[ym[t]] - 1]) if first[ym[t]] >= 1 else False for t in range(n)])   # ⚠ 用法：entry e 看 S[e]（已是 e 月初前一天）
    # 10 個月均線：月底收盤
    me = pd.Series(bench, index=cal).groupby(ym).last()
    ma10 = me.rolling(10, min_periods=10).mean()
    st10 = (me > ma10)
    prev = {ymv: (bool(st10.loc[ymv - 1]) if (ymv - 1) in st10.index and np.isfinite(ma10.loc[ymv - 1]) else False) for ymv in me.index}
    S["10個月均線月底"] = np.array([prev[ym[t]] for t in range(n)])
    return S, d, ma


def allowed(S, e):
    """各寫法對進場日 e 是否允許：每日／緩衝／連 3 天 ⇒ 狀態[e−1]；月初／10 月 ⇒ 依 e 所在月（陣列已內含前一期資訊）。"""
    out = {}
    for k, s in S.items():
        out[k] = s[e - 1] if k in ("每日（現行）", "緩衝±2%", "緩衝±3%", "連3天確認") else s[e]
    return out


# ═════════════ 主流程 ═════════════
def run(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(OUT, "run.log")
    t00 = time.time()
    log(f"===== researchYLdesc run procs={a.procs} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TIME}｜⛔ 不附報酬、不計 N =====")
    ctx = base_ctx(); cal = ctx["cal"]; n = len(cal)
    log(f"[ctx] 日曆 {n}（{cal[0].date()}～{cal[-1].date()}）｜主窗 {cal[ctx['w0']].date()}～{cal[ctx['w1']].date()}｜營量訊號 {len(ctx['sig13'])}｜營飆訊號 {len(ctx['sig'])}")
    if not os.path.exists(os.path.join(WORK, "audits.csv.gz")):
        run_engine(a.procs)
    if not os.path.exists(os.path.join(WORK, "panel_all.csv.gz")):
        build_panel(a.procs)
    if not os.path.exists(os.path.join(WORK, "cond_counts.csv.gz")):
        build_bars(a.procs)
    PN = pd.read_csv(os.path.join(WORK, "panel_all.csv.gz"), dtype={"stock_id": str, "period": str})
    GV, ginfo = gate_variants(PN, cal)
    vp = os.path.join(WORK, "variant_labels.json")
    if not os.path.exists(vp):
        paths = build_and(PN, GV, a.procs, cal)
        VL = variant_labels(paths, a.procs, cal)
        json.dump(VL, open(vp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log, t1=True)   # 還原原版 _G
    items(a, ctx, PN, GV, ginfo)
    log(f"[完成] {time.time() - t00:.0f}s")


def items(a, ctx, PN, GV, ginfo):
    cal = ctx["cal"]; n = len(cal); w0, w1 = ctx["w0"], ctx["w1"]
    S = {}
    YL, YF = ctx["sig13"].copy(), ctx["sig"].copy()
    AND = ctx["AND"]
    prev = pd.read_csv("backtest/resultsN17/sig_edc6f/panel_rev.csv.gz", dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "signal_pos", "rev_hi24"])
    prev["rev_hi24"] = prev["rev_hi24"].fillna(False).astype(bool)
    for X in (YL, YF):
        X["period"] = used_period(X, prev)
        X["年"] = [cal[p].year for p in X["pos"]]; X["月"] = [cal[p].month for p in X["pos"]]
    rev, rev_ly, ind_s = R34.load_revenue()
    ind = ind_s.to_dict()
    AU = pd.read_csv(os.path.join(WORK, "audits.csv.gz"), dtype={"sid": str})
    gates = {"E": json.load(open(os.path.join(WORK, "gate_engine.json"), encoding="utf-8")), "P": json.load(open(os.path.join(WORK, "gate_panel.json"), encoding="utf-8")),
             "A": json.load(open(os.path.join(WORK, "gate_and.json"), encoding="utf-8"))}
    VL = json.load(open(os.path.join(WORK, "variant_labels.json"), encoding="utf-8"))
    gates["E_版原版"] = {k: v for k, v in VL["原版"].items() if k.startswith("閘E")}
    S["閘"] = gates
    base_rows = PN[GV["原版"]].copy(); base_rows["年"] = [cal[p].year for p in base_rows["signal_pos"]]
    tables = {}

    # ① 一次性收入
    def drop_of(pairs):
        o = []
        for sid, p in pairs:
            p1 = per_add(p, 1)
            if sid not in rev.columns or p not in rev.index or p1 not in rev.index:
                o.append(np.nan); continue
            r0, r1 = rev.at[p, sid], rev.at[p1, sid]
            o.append(np.nan if not (np.isfinite(r0) and np.isfinite(r1)) else float(r1 <= 0.5 * r0))
        return np.array(o)
    one = {}
    rows1 = []
    for nm, X in (("營量", YL), ("營飆", YF)):
        dd = drop_of(zip(X["sid"], X["period"])); X["掉一半"] = dd
        one[nm] = {"訊號": int(len(X)), "下月有值": int(np.isfinite(dd).sum()), "掉回一半以上": int(np.nansum(dd)), "占比": float(np.nanmean(dd))}
        for y, g in X.groupby("年"):
            rows1.append({"策略": nm, "年": y, "訊號": len(g), "下月有值": int(g["掉一半"].notna().sum()), "掉一半": int(g["掉一半"].sum()), "占比": float(g["掉一半"].mean())})
    bb = base_rows[base_rows["rev"].notna()]
    db = drop_of(zip(bb["stock_id"], bb["period"]))
    one["對照：營量母體全部股-月"] = {"股-月": int(len(bb)), "下月有值": int(np.isfinite(db).sum()), "掉回一半以上": int(np.nansum(db)), "占比": float(np.nanmean(db))}
    bh = bb[bb["rev_hi24"]]; dh = drop_of(zip(bh["stock_id"], bh["period"]))
    one["對照：營量母體中營收創 24 月新高的股-月"] = {"股-月": int(len(bh)), "掉回一半以上": int(np.nansum(dh)), "占比": float(np.nanmean(dh))}
    S["①一次性收入"] = one; tables["q1_by_year"] = pd.DataFrame(rows1)
    log(f"[①] {json.dumps(one, ensure_ascii=False)}")

    # ② 併購
    maset, last_date, seq2sha, nnews, nma = news_ma()
    last_ym = last_date[:7]
    two = {"新聞": f"data/mops/news 2015～2026（main 8425186bd2；最後一則 {last_date}）共 {nnews:,} 則，併購／合資類 {nma:,} 則", "分類 seq2 原始碼 sha": seq2sha}
    rows2 = []
    for nm, X in (("營量", YL), ("營飆", YF)):
        F = ma_flags(zip(X["sid"], X["period"]), maset, last_ym)
        X["併前"], X["併後"], X["後滿"] = F[:, 0], F[:, 1], F[:, 2]
        full = F[:, 2]
        two[nm] = {"訊號": int(len(X)), "前6個月（含訊號月）有": int(F[:, 0].sum()), "前占比": float(F[:, 0].mean()),
                   "後6個月窗已滿的訊號": int(full.sum()), "後6個月有（窗已滿者）": int((F[:, 1] & full).sum()), "後占比": float(F[full, 1].mean()),
                   "前後任一（窗已滿者）占比": float((F[full, 0] | F[full, 1]).mean())}
        for y, g in X.groupby("年"):
            ff = g["後滿"].to_numpy()
            rows2.append({"策略": nm, "年": y, "訊號": len(g), "前占比": float(g["併前"].mean()), "後滿": int(ff.sum()),
                          "後占比": float(g.loc[ff, "併後"].mean()) if ff.any() else np.nan})
    Fb = ma_flags(zip(base_rows["stock_id"], base_rows["period"]), maset, last_ym)
    two["對照：營量母體全部股-月"] = {"股-月": int(len(Fb)), "前占比": float(Fb[:, 0].mean()), "後占比（窗已滿者）": float(Fb[Fb[:, 2], 1].mean())}
    S["②併購"] = two; tables["q2_by_year"] = pd.DataFrame(rows2)
    log(f"[②] {json.dumps(two, ensure_ascii=False)}")

    # ③ 景氣循環、⑤ 專案型
    def cls5(s):
        if s in CLEAN:
            return "無塵室（自訂名單）"
        i = ind.get(s, "")
        return f"{i}（{PROJ_IND[i]}）" if i in PROJ_IND else ""
    rows3 = []; rows5 = []
    for nm, X in (("營量", YL), ("營飆", YF)):
        X["產業"] = [ind.get(s, "未知") for s in X["sid"]]; X["循環"] = X["產業"].isin(CYC); X["專案"] = [cls5(s) for s in X["sid"]]
        for y, g in list(X.groupby("年")) + [("全期", X)]:
            rows3.append({"策略": nm, "年": y, "訊號": len(g), "景氣循環": int(g["循環"].sum()), "占比": float(g["循環"].mean()),
                          **{c: int((g["產業"] == c).sum()) for c in CYC}})
            rows5.append({"策略": nm, "年": y, "訊號": len(g), "專案型合計": int((g["專案"] != "").sum()), "占比": float((g["專案"] != "").mean()),
                          "建材營造": int((g["專案"] == "建材營造（建設）").sum()), "資訊服務業": int((g["專案"] == "資訊服務業（系統整合）").sum()),
                          "無塵室": int((g["專案"] == "無塵室（自訂名單）").sum())})
    base_rows["產業"] = [ind.get(s, "未知") for s in base_rows["stock_id"]]
    univ_cyc = base_rows.groupby("年").apply(lambda g: float(g["產業"].isin(CYC).mean()))
    univ_proj = base_rows.groupby("年").apply(lambda g: float(np.mean([cls5(s) != "" for s in g["stock_id"]])))
    T3 = pd.DataFrame(rows3); T3["母體占比（換股日過閘股-月）"] = T3["年"].map(univ_cyc.to_dict())
    T5 = pd.DataFrame(rows5); T5["母體占比（換股日過閘股-月）"] = T5["年"].map(univ_proj.to_dict())
    tables["q3_cyclical"] = T3; tables["q5_project"] = T5
    S["③景氣循環"] = {nm: {"全期占比": float(T3[(T3["策略"] == nm) & (T3["年"] == "全期")]["占比"].iloc[0]),
                         "逐年占比範圍": [float(T3[(T3["策略"] == nm) & (T3["年"] != "全期")]["占比"].min()), float(T3[(T3["策略"] == nm) & (T3["年"] != "全期")]["占比"].max())]}
                    for nm in ("營量", "營飆")}
    S["③景氣循環"]["母體占比範圍"] = [float(univ_cyc.min()), float(univ_cyc.max())]
    S["⑤專案型"] = {nm: {"全期占比": float(T5[(T5["策略"] == nm) & (T5["年"] == "全期")]["占比"].iloc[0])} for nm in ("營量", "營飆")}
    S["⑤專案型"]["母體占比範圍"] = [float(univ_proj.min()), float(univ_proj.max())]

    # ④ 月份
    td = pd.Series(1, index=cal[w0:w1 + 1]).groupby(cal[w0:w1 + 1].month).sum()
    rows4 = []
    for m in range(1, 13):
        rows4.append({"月": m, "主窗交易日": int(td.get(m, 0)), "營量訊號": int((YL["月"] == m).sum()), "營飆訊號": int((YF["月"] == m).sum()),
                      "營量每交易日": float((YL["月"] == m).sum() / td.get(m, np.nan)), "營飆每交易日": float((YF["月"] == m).sum() / td.get(m, np.nan))})
    T4 = pd.DataFrame(rows4); tables["q4_month"] = T4
    tables["q4_year_month_營量"] = pd.crosstab(YL["年"], YL["月"]); tables["q4_year_month_營飆"] = pd.crosstab(YF["年"], YF["月"])
    S["④月份"] = {"營量每交易日訊號_2月": float(T4.loc[T4["月"] == 2, "營量每交易日"].iloc[0]), "營量每交易日訊號_其他月中位": float(T4.loc[T4["月"] != 2, "營量每交易日"].median()),
                 "營量每交易日訊號_3月": float(T4.loc[T4["月"] == 3, "營量每交易日"].iloc[0])}

    # ⑥ 分位
    A = np.load(os.path.join(WORK, "arrays.npz"))
    sids = list(A["sids"]); si = {s: i for i, s in enumerate(sids)}
    amt20, mcap, life, sh_age = A["amt20"], A["mcap"], A["life"], A["sh_age"]
    rows6 = []
    for nm, X in (("營量", YL), ("營飆", YF)):
        pa = []; pm = []; ages = []
        for s, p in zip(X["sid"], X["pos"]):
            col_a = amt20[:, p]; col_m = mcap[:, p]; lf = life[:, p]
            va = lf & np.isfinite(col_a); vm = lf & np.isfinite(col_m) & (col_m > 0)
            i = si[s]
            pa.append(float((col_a[va] < col_a[i]).sum() + 0.5 * ((col_a[va] == col_a[i]).sum() - 1)) / max(va.sum() - 1, 1) if va[i] else np.nan)
            pm.append(float((col_m[vm] < col_m[i]).sum() + 0.5 * ((col_m[vm] == col_m[i]).sum() - 1)) / max(vm.sum() - 1, 1) if vm[i] else np.nan)
            ages.append(float(sh_age[i, p]))
        X["成交金額分位"] = pa; X["市值分位"] = pm; X["股數沿用天數"] = ages
        for col in ("市值分位", "成交金額分位"):
            v = X[col].to_numpy(float)
            rows6.append({"策略": nm, "量": col, **q5(v), **{f"十分位{k + 1}": int(((v >= k / 10) & (v < (k + 1) / 10 + (1e-12 if k == 9 else 0))).sum()) for k in range(10)}})
    T6 = pd.DataFrame(rows6); tables["q6_pctl"] = T6
    S["⑥分位"] = {f"{r['策略']}{r['量']}": {k: r[k] for k in ("n", "p10", "中位", "p90")} for _, r in T6.iterrows()}
    S["⑥分位"]["股數沿用超過 250 天的訊號占比"] = {nm: float((X["股數沿用天數"] > 250).mean()) for nm, X in (("營量", YL), ("營飆", YF))}

    # ⑦ 母體檔數
    rows7 = []
    PN["年"] = [cal[p].year for p in PN["signal_pos"]]
    for g in GATES:
        PN[f"g_{g}"] = GV[g]
    Mser = pd.Series({pd.Timestamp(k).year: v for k, v in ginfo["M"].items()})
    for y, gg in PN.groupby("年"):
        r = {"年": y, "換股日數": int(gg["signal_pos"].nunique())}
        for g in GATES:
            per_sp = gg.groupby("signal_pos")[f"g_{g}"].sum()
            r[f"{g}_每換股日平均"] = float(per_sp.mean()); r[f"{g}_當年曾過閘檔數"] = int(gg.loc[gg[f"g_{g}"], "stock_id"].nunique())
        msp = [v for k, v in ginfo["M"].items() if pd.Timestamp(k).year == y]
        r["存續母體平均"] = float(np.mean(msp))
        rows7.append(r)
    T7 = pd.DataFrame(rows7); tables["q7_universe"] = T7
    S["⑦母體"] = {"原版每換股日平均_首年末年": [float(T7["原版_每換股日平均"].iloc[0]), float(T7["原版_每換股日平均"].iloc[-1])]}

    # ⑧ 條件觸發率
    C = pd.read_csv(os.path.join(WORK, "cond_counts.csv.gz"), dtype={"sid": str})
    cg = C.groupby("year").sum(numeric_only=True)
    T8 = pd.DataFrame({"年": cg.index, "eligible 股-日": cg["elig"]})
    for c_, nm in (("c1", "c1 20日漲≥30%"), ("c2", "c2 20根漲停≥3"), ("c3", "c3 成交額≥前20均3倍"), ("c4", "c4 收>MA100"), ("c5", "c5 收≥250根最高"), ("score3", "5取3")):
        T8[nm] = (cg[c_] / cg["elig"]).to_numpy()
    T8 = T8.reset_index(drop=True)
    pr = PN[PN["base_ok"] & PN["rev"].notna()]
    hi_y = pr.groupby("年")["rev_hi24"].mean(); liq_y = PN[PN["base_ok"]].groupby("年")["liq_sh"].mean()
    T8["營收創24月新高（過其他閘、有營收的股-月）"] = T8["年"].map(hi_y.to_dict())
    T8["流動性閘500張（過其他閘的股-月）"] = T8["年"].map(liq_y.to_dict())
    and_y = pd.Series([cal[p].year for p in AND["pos"]]).value_counts()
    T8["AND 訊號÷eligible 股-日"] = T8["年"].map(and_y.to_dict()).fillna(0) / T8["eligible 股-日"]
    T8["標"] = np.where(T8["年"] == 2026, "部分年（至 2026-09-24）；8/10 起處置新制", "")
    tables["q8_cond"] = T8
    FT = feats_rates(); tables["q8_feats"] = FT
    SB, sbinfo = surge_base(); tables["q8_surge_base"] = SB
    S["⑧觸發率"] = {"5取3_範圍": [float(T8["5取3"].min()), float(T8["5取3"].max())], "2026_5取3": float(T8.loc[T8["年"] == 2026, "5取3"].iloc[0]),
                  "c1_2026": float(T8.loc[T8["年"] == 2026, "c1 20日漲≥30%"].iloc[0]), "c1_2016_2025_範圍": [float(T8.loc[T8["年"].between(2016, 2025), "c1 20日漲≥30%"].min()), float(T8.loc[T8["年"].between(2016, 2025), "c1 20日漲≥30%"].max())],
                  "飆股基準率": sbinfo}

    # ⑨ 集中度
    bench = ctx["bench"]; closes = ctx["closes"]
    rows9 = []
    for kind, nm, N in (("yl", "營量", 20), ("yf", "營飆", 10), ("yl_fwd", "營量", 20), ("yf_fwd", "營飆", 10)):
        sig = {"yl": YL, "yf": YF, "yl_fwd": ctx["sig_yl_fwd"], "yf_fwd": ctx["sig_yf_fwd"]}[kind]
        ent = {}
        for s, e in zip(sig["sid"], sig["entry_pos"]):
            ent.setdefault(int(e), []).append(s)
        sub = AU[AU["kind"] == kind]
        for r, g in sub.groupby("r"):
            H = holdings_from_audit(list(zip(g["t"], g["sid"], g["side"])))
            if kind.endswith("_fwd"):
                H = {t: v for t, v in H.items() if t > w1}
            else:
                H = {t: v for t, v in H.items() if w0 <= t <= w1}
            if not H:
                continue
            M9 = conc_metrics(H, ent, ind, closes, bench, cal, N)
            M9["策略"] = nm; M9["段"] = "前瞻段" if kind.endswith("_fwd") else "主窗"; M9["r"] = r
            rows9.append(M9)
    T9 = pd.concat(rows9, ignore_index=True)
    T9.to_csv(os.path.join(WORK, "q9_days.csv.gz"), index=False)
    agg = []
    for (nm, seg, y), g in list(T9.groupby(["策略", "段", "年"])) + [((nm, seg, "全期"), g) for (nm, seg), g in T9.groupby(["策略", "段"])]:
        agg.append({"策略": nm, "段": seg, "年": y, "換股日（營飆為 200 顆合計）": len(g), "持股數中位": float(g["持股數"].median()), "ρ中位": float(g["ρ"].median()),
                    "等效獨立檔數中位": float(g["等效獨立檔數"].median()), "最大產業檔數中位": float(g["最大產業檔數"].median()),
                    "超過3檔的換股日占比": float(g["超過3檔"].mean()), "上限3擠掉筆數": int(g["擠掉筆數"].sum()), "同池可補": int(g["同池可補"].sum()),
                    "可補比例": float(g["同池可補"].sum() / g["擠掉筆數"].sum()) if g["擠掉筆數"].sum() else np.nan,
                    "β漲日中位": float(g["β漲日"].median()), "β跌日中位": float(g["β跌日"].median())})
    T9a = pd.DataFrame(agg); tables["q9_concentration"] = T9a
    topind = T9[T9["段"] == "主窗"].groupby(["策略", "最大產業"]).size().sort_values(ascending=False)
    S["⑨集中度"] = {"產業分類": "證交所／櫃買產業類別單層（月營收彙總表產業別欄、各檔最後一期值；約 30 類；⚠ 現行分類回填）",
                  "全期": {f"{r['策略']}{r['段']}": {k: r[k] for k in ("持股數中位", "ρ中位", "等效獨立檔數中位", "最大產業檔數中位", "超過3檔的換股日占比", "上限3擠掉筆數", "可補比例", "β漲日中位", "β跌日中位")}
                         for _, r in T9a[T9a["年"] == "全期"].iterrows()},
                  "最常是最大產業": {f"{k[0]}｜{k[1]}": int(v) for k, v in topind.head(6).items()}}

    # ⑩ 0050 距離、⑪ 六寫法
    SS, dist, ma = gate_states(bench, cal)
    e_yf = YF["entry_pos"].to_numpy()
    dd = dist[e_yf - 1]
    daily = SS["每日（現行）"]
    flip = {}
    for k in (1, 2, 3):
        f_ = np.zeros(len(e_yf), bool)
        for dlt in list(range(-k, 0)) + list(range(1, k + 1)):
            j = e_yf - 1 + dlt
            f_ |= (j >= 0) & (j < n) & (daily[np.clip(j, 0, n - 1)] != daily[e_yf - 1])
        flip[f"挪±{k}天內翻轉占比"] = float(f_.mean())
    ud = np.unique(e_yf)
    S["⑩0050距離"] = {"營飆訊號": int(len(e_yf)), "不同進場日": int(len(ud)), "距離分佈": q5(dd), "|距離|≤3%占比": float((np.abs(dd) <= 0.03).mean()),
                     "|距離|≤3%占比（不同進場日）": float((np.abs(dist[ud - 1]) <= 0.03).mean()), **flip,
                     "正式規則 0050 價": "還原價：rerun17.load_bench ＝ data.load_stock('0050').df['close']（load_stock 乘 data/adj 還原因子）再 ffill；"
                                         "regime_mask ＝ 收盤 ＞ 200 根滾動均（research13.MA_REGIME＝200）；營飆用 reg[entry_pos−1]。每日名單同（list_prereg10.regime_arrays → RR.load_bench）"}
    tables["q10_dist"] = pd.DataFrame({"sid": YF["sid"].to_numpy(), "進場日": [str(cal[e].date()) for e in e_yf], "0050距200日線": dd})
    eA = AND["entry_pos"].to_numpy(); inwin = (eA >= w0) & (eA <= w1)
    al = allowed(SS, eA)
    rows11 = []
    for nm, msk in (("全部 AND（進場 2017-02 起）", np.ones(len(eA), bool)), ("主窗", inwin)):
        for v in VARS:
            rows11.append({"範圍": nm, "寫法": v, "AND 訊號": int(msk.sum()), "允許": int((al[v] & msk).sum()),
                           "與每日不同": int(((al[v] != al["每日（現行）"]) & msk).sum()),
                           "每日允許→此寫法擋": int((al["每日（現行）"] & ~al[v] & msk).sum()), "每日擋→此寫法允許": int((~al["每日（現行）"] & al[v] & msk).sum())})
    T11 = pd.DataFrame(rows11); tables["q11_variants"] = T11
    yfb = AU[(AU["kind"] == "yf") & (AU["side"] == "buy")]
    rows11b = []
    and_lo = cal[int(eA.min())]
    for nm, s0, s1 in CRASH:
        a_, b_ = int(cal.searchsorted(pd.Timestamp(s0))), int(cal.searchsorted(pd.Timestamp(s1), side="right")) - 1
        m = (eA >= a_) & (eA <= b_)
        cover = "訊號表沒有（AND 進場 2017-02-13 才開始）" if pd.Timestamp(s1) < and_lo else ("部分（AND 進場 2017-02 起）" if pd.Timestamp(s0) < and_lo else "")
        r = {"期間": nm, "涵蓋": cover, "AND 訊號": int(m.sum())}
        for v in VARS:
            r[v] = int((al[v] & m).sum())
        per = yfb[(yfb["t"] >= a_) & (yfb["t"] <= b_)].groupby("r").size().reindex(range(200), fill_value=0)
        r["營飆實際買進（200 顆中位）"] = float(per.median()); r["營飆實際買進（最小～最大）"] = f"{per.min()}～{per.max()}"
        r["主窗內"] = bool(a_ <= w1 and b_ >= w0)
        rows11b.append(r)
    T11b = pd.DataFrame(rows11b); tables["q11_crash"] = T11b
    S["⑪六寫法"] = {r["寫法"]: {"允許": r["允許"], "與每日不同": r["與每日不同"]} for _, r in T11[T11["範圍"] == "全部 AND（進場 2017-02 起）"].iterrows()}

    # R1／R2
    S["R1R2"] = {"門檻": {k: v for k, v in ginfo.items() if k != "M"}, "各版": VL,
                 "結論方向一致": {g: {"營飆": VL[g]["營飆標籤"] == VL["原版"]["營飆標籤"], "營量": VL[g]["營量標籤"] == VL["原版"]["營量標籤"]} for g in GATES if g != "原版"}}
    log(f"[R1R2] {json.dumps(S['R1R2']['結論方向一致'], ensure_ascii=False)}")

    # 營量排序
    S["營量排序"] = rank_desc(AU, YL, YF, w0, w1)

    # §四
    S["§四-1"] = feats_flags(); S["§四-5"] = vol_line(PN, GV, cal)
    tables["fixed_rules"] = fixed_rules_grep()
    S["§四-3"] = regime_line(cal, T7)
    for k, t in tables.items():
        t.to_csv(os.path.join(OUT, f"{k}.csv"), index=k.startswith("q4_year"), encoding="utf-8-sig")
    S["讀法寫死"] = TIME; S["產出"] = f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    write_report(S, tables)


def rank_desc(AU, YL, YF, w0, w1):
    ent = {}
    for s, e in zip(YL["sid"], YL["entry_pos"]):
        ent.setdefault(int(e), []).append(s)
    g = AU[(AU["kind"] == "yl") & (AU["r"] == 0)]
    by = {}
    for t, s, sd in zip(g["t"], g["sid"], g["side"]):
        by.setdefault(int(t), []).append((s, sd))
    held = set(); d_sig = d_over = d_full = d_act = 0; el_lot = el_full = 0; exp_diff = 0.0; buys = []
    N = 20
    for t in sorted(set(by) | set(ent)):
        for s, sd in by.get(t, []):
            if sd == "sell":
                held.discard(s)
        if t in ent:
            cand = [s for s in ent[t] if s not in held]; free = N - len(held)
            d_sig += 1
            if len(cand) > free:
                d_over += 1
                if free <= 0:
                    d_full += 1; el_full += len(cand)
                else:
                    d_act += 1; el_lot += len(cand) - free; exp_diff += free * (1 - free / len(cand))
        for s, sd in by.get(t, []):
            if sd == "buy":
                held.add(s); buys.append((t, s))
    B = set(buys)
    tot = []
    for r, gg in AU[(AU["kind"] == "yllot") & (AU["side"] == "buy")].groupby("r"):
        L_ = set(zip(gg["t"].astype(int), gg["sid"]))
        tot.append(len(B - L_) / len(B))
    return {"⛔": "只數日數與買進清單，不含任何報酬", "主窗有訊號日": d_sig, "候選＞空槽日": d_over, "候選＞空槽日占有訊號日": d_over / d_sig,
            "其中槽滿（排序不起作用）": d_full, "其中有作用（0＜空槽＜候選）": d_act, "有作用日占有訊號日": d_act / d_sig,
            "有作用日被排序淘汰的候選": el_lot, "槽滿淘汰的候選": el_full, "relvol 版買進": len(buys),
            "直接差（期望換掉筆數）": exp_diff, "直接差占買進": exp_diff / len(buys),
            "整條路徑總差占買進（抽籤 200 顆）": q5(tot)}


def feats_rates():
    import json as _j
    uni = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str)
    cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(ST, "meta", "calendar_twse.csv"))["date"])).sort_values()
    fcol = _j.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"]
    fcol = eval(fcol) if isinstance(fcol, str) else fcol
    FX = {c: i for i, c in enumerate(fcol)}
    from backtest import researchSurge6_overlap as OV
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    bar = np.load(os.path.join(WORK5, "bar.npy"))
    yr = cal.year.to_numpy()
    rows = []
    for nm, col, code in OV.FEATS:
        q = np.asarray(Qm[FX[col]])
        for y in range(2005, 2027):
            cm = yr == y
            b = bar[:, cm]; qq = q[:, cm]
            has = b & (qq > 0)
            rows.append({"特徵": nm, "年": y, "有K棒股-日": int(b.sum()), "有值率": float(has.sum() / max(b.sum(), 1)),
                         "觸發率（有值者）": float((has & (qq == code)).sum() / max(has.sum(), 1)), "標": "部分年；8/10 起處置新制" if y == 2026 else ""})
    return pd.DataFrame(rows)


def surge_base():
    from backtest import researchSurge6_overlap as OV
    cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(ST, "meta", "calendar_twse.csv"))["date"])).sort_values()
    yr = cal.year.to_numpy(); mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    bar = np.load(os.path.join(WORK5, "bar.npy"))
    E6 = dict(np.load(os.path.join(WORK6, "events.npz"))); h6 = np.load(os.path.join(WORK6, "hdef6.npy"))
    cnt = np.bincount(E6["cell"].astype(int), minlength=250)
    cells = [c for c in range(250) if cnt[c] >= OV.MINEV]
    inseg = (mon >= 2021 * 12) & (mon <= 2026 * 12 + 7)
    rows = []
    for src, E, hd, years, segm in (("seq6（2021-01～2026-08）", E6, h6, range(2021, 2027), inseg),
                                    ("seq5 全日曆鏈（參考）", dict(np.load(os.path.join(WORK5, "events.npz"))), np.load(os.path.join(WORK5, "hdef.npy")), range(2005, 2027), np.ones(len(cal), bool))):
        den = {}
        for H in sorted({OV.HS[c // 10] for c in cells}):
            m = bar & (hd >= H) & segm[None, :]
            col = m.sum(0)
            den[H] = {y: int(col[yr == y].sum()) for y in years}
        ec, ed = E["cell"].astype(int), E["d"].astype(int)
        ey = yr[ed]
        for y in years:
            rates = []
            for c in cells:
                H = OV.HS[c // 10]
                dn = den[H][y]
                if dn > 0:
                    rates.append(((ec == c) & (ey == y) & segm[ed]).sum() / dn)
            rows.append({"來源": src, "年": y, "格數": len(rates), "基準率格中位": float(np.median(rates)) if rates else np.nan,
                         "p10": float(np.percentile(rates, 10)) if rates else np.nan, "p90": float(np.percentile(rates, 90)) if rates else np.nan,
                         "標": "部分年（右截斷 2026-08-31）；8/10 起處置新制" if y == 2026 else ""})
    T = pd.DataFrame(rows)
    s6 = T[T["來源"].str.startswith("seq6")]
    return T, {"合格格數": len(cells), "seq6 逐年格中位": {int(r["年"]): float(r["基準率格中位"]) for _, r in s6.iterrows()}}


def feats_flags():
    F = [("距5日最低｜Q1", "相對（當日橫斷面五等分）", ""), ("距10日最低｜Q1", "相對", ""), ("收盤÷MA5−1｜Q1", "相對", ""), ("5日報酬｜Q1", "相對", ""),
         ("60日平均周轉率｜Q5", "相對；分母股數（stocks shares 欄，⚠ 上市界線日後空）", ""), ("120日報酬｜Q5", "相對", ""),
         ("融資使用率｜Q5", "相對（融資餘額÷融資限額）", ""), ("原：股價級距｜＜20 元", "固定價位（未還原收盤 ＜ 20 元）", "固定金額"),
         ("原：均線多頭排列5>20>60>100｜是", "無固定門檻", ""), ("原：注意股60日次數級距｜≥3 次", "用到注意股（固定次數 3）", "注意"),
         ("原R2營收年增≥50%｜是", "固定比率（年增 ≥ 50%）", "固定比率"), ("原：EPS轉正｜是", "正負號", ""), ("原：營收創24月新高｜是", "相對自己歷史", ""),
         ("原：20日漲停天數級距｜≥3 次", "漲停（2015-06-01 前 7%、之後 10%；research11.limit_flags）＋固定次數 3", "固定漲幅")]
    return [{"特徵": a, "說明": b, "用到": c or "無", "處置": "否", "注意": "是" if c == "注意" else "否",
             "固定金額或張數": "是（價位 20 元）" if c == "固定金額" else "否"} for a, b, c in F]


def vol_line(PN, GV, cal):
    V = pd.read_csv(os.path.join(WORK, "vol.csv.gz"), dtype={"sid": str})
    PN = PN.copy(); PN["年"] = [cal[p].year for p in PN["signal_pos"]]
    ok = PN[GV["原版"]].groupby("年")["stock_id"].apply(set).to_dict()
    med = {}; medall = {}
    for y, g in V.groupby("year"):
        medall[int(y)] = float(g["vol"].median())
        if y in ok:
            gg = g[g["sid"].isin(ok[y])]
            med[int(y)] = float(gg["vol"].median())
    past = [v for y, v in med.items() if 2016 <= y <= 2025]
    return {"母體（當年曾過原版閘者）各年中位": med, "全部上市櫃普通股各年中位": medall, "2026": med.get(2026), "2016～2025 範圍": [min(past), max(past)],
            "一行": f"今年個股年化波動中位 {med.get(2026, np.nan) * 100:.0f}%（至 2026-09-24）vs 回測 2016～2025 各年 {min(past) * 100:.0f}～{max(past) * 100:.0f}%"}


def regime_line(cal, T7):
    p = os.path.join(WORK, "regime_log.csv")
    if not os.path.exists(p):
        txt = subprocess.run(["git", "show", "origin/main:data/meta/tw_regime_log/tw_regime_log.csv"], capture_output=True, text=True).stdout
        open(p, "w", encoding="utf-8").write(txt)
    Rg = pd.read_csv(p, dtype=str)
    eff = pd.to_datetime(Rg["effective_date"].fillna(Rg["announce_date"]), errors="coerce")
    m = (eff >= pd.Timestamp("2016-01-04")) & (eff <= cal[-1])
    sel = Rg[m].assign(生效=eff[m].dt.date.astype(str))[["event_id", "生效", "category", "title", "verify_status"]]
    sel.to_csv(os.path.join(OUT, "regime_crossed.csv"), index=False, encoding="utf-8-sig")
    key = sel[sel["category"].isin(["稅費", "處置與警示", "漲跌幅", "零股", "其他", "當沖"])]
    u = T7.set_index("年")["原版_每換股日平均"]
    line = ("回測期 2016-01～2026-09 跨過：" + "；".join(f"{r['生效']} {r['title']}" for _, r in key.iterrows()) +
            f"｜母體（原版閘每換股日平均）{int(u.index[0])} 年 {u.iloc[0]:.0f} 檔 → {int(u.index[-1])} 年 {u.iloc[-1]:.0f} 檔")
    return {"斷點數（全部類別）": int(len(sel)), "一行": line}


FIX_FILES = ["daily_list.py", "list_yl13.py", "list_yl13_watch.py", "list_prereg10.py", "surge_flow_daily.py", "surge_feat_daily.py", "researchSurge6_overlap.py",
             "researchSurge5.py", "gate_b_status.py", "universe_gate.py", "research11.py", "research13.py", "research34.py", "patterns.py", "researchp1.py",
             "rerun17_build.py", "data.py"]
FIX_PAT = [("固定金額／張數", r"50_000_000|5e7|5,000 ?萬|5000 ?萬|500_000|500 ?張|千張|1000 ?張|1_000_000|liq_min"),
           ("固定漲幅／漲停", r"ret20 ?>= ?|>= ?0\.30|1\.30 ?\*|0\.07 if|0\.10\)|nup20 ?>= ?3|漲停.{0,8}(≥|>=) ?3|limit_price\(|0\.85|0\.7\b|× ?0\.7|回落 ?30%|20% 切段|x＝20%"),
           ("固定比率（PE／PBR／殖利率／年增）", r"\bper\b.{0,6}(<|>)|pbr.{0,6}(<|>)|yld.{0,6}(<|>)|yoy\[?\w*\]? ?>= ?|年增 ?≥|>= ?0\.5\)|>= ?1\.0\)"),
           ("固定倍數", r"amt_ratio ?>= ?|ar_ ?>= ?|>= ?C3|3 倍|C3 ?= ?|C1, C3"),
           ("處置／注意", r"disposal|處置|attention|注意")]


def fixed_rules_grep():
    rows = []
    for f in FIX_FILES:
        p = os.path.join("backtest", f)
        if not os.path.exists(p):
            continue
        for i, line in enumerate(open(p, encoding="utf-8"), 1):
            for nm, pat in FIX_PAT:
                if re.search(pat, line):
                    rows.append({"檔": f"backtest/{f}", "行": i, "類": nm, "內容": line.strip()[:200]})
    return pd.DataFrame(rows)


# ═════════════ 報告 ═════════════
def pc(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:.{d}f}%"


def fnum(v):
    if isinstance(v, (float, np.floating)):
        if not np.isfinite(v):
            return "—"
        return f"{int(v)}" if float(v).is_integer() else f"{v:.3f}"
    return str(v)


def md_table(df, cols=None, fmt=None):
    cols = cols or list(df.columns); fmt = fmt or {}
    L_ = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        L_.append("| " + " | ".join(fmt[c](r[c]) if c in fmt else fnum(r[c]) for c in cols) + " |")
    return L_


def write_report(S, T):
    o1, o2, r1 = S["①一次性收入"], S["②併購"], S["R1R2"]
    rk = S["營量排序"]; c9 = S["⑨集中度"]["全期"]
    VL = r1["各版"]
    r2y = {int(k): v for k, v in r1["門檻"]["R2_門檻_逐年中位（億）"].items()}
    head = [
        f"**1. 一次性營收**：營量訊號 {pc(o1['營量']['占比'])}、營飆 {pc(o1['營飆']['占比'])} 下個月營收掉回一半以上；營量母體全部股-月是 {pc(o1['對照：營量母體全部股-月']['占比'])}。",
        f"**2. 併購公告**：訊號月前 6 個月內有併購／合資重大訊息的，營量 {pc(o2['營量']['前占比'])}、營飆 {pc(o2['營飆']['前占比'])}（母體 {pc(o2['對照：營量母體全部股-月']['前占比'])}）。庫裡沒有「併表」專欄，用重大訊息分類代替。",
        f"**3. 景氣循環產業**：營量全期 {pc(S['③景氣循環']['營量']['全期占比'])}、營飆 {pc(S['③景氣循環']['營飆']['全期占比'])}；母體逐年 {pc(S['③景氣循環']['母體占比範圍'][0])}～{pc(S['③景氣循環']['母體占比範圍'][1])}。",
        f"**4. 營量排序**：主窗有訊號的 {rk['主窗有訊號日']} 天裡，候選多於空槽 {rk['候選＞空槽日']} 天（{pc(rk['候選＞空槽日占有訊號日'])}），其中真正由排序決定誰進的只有 {rk['其中有作用（0＜空槽＜候選）']} 天（{pc(rk['有作用日占有訊號日'])}）；"
        f"改成抽籤，買進清單不同 {pc(rk['整條路徑總差占買進（抽籤 200 顆）']['中位'])}（直接差 {pc(rk['直接差占買進'])}）。",
        f"**5. 集中度**：營量主窗持股等效獨立檔數中位 {c9['營量主窗']['等效獨立檔數中位']:.1f}（持股中位 {c9['營量主窗']['持股數中位']:.0f}）、營飆 {c9['營飆主窗']['等效獨立檔數中位']:.1f}（持股中位 {c9['營飆主窗']['持股數中位']:.0f}）；"
        f"同產業超過 3 檔的換股日：營量 {pc(c9['營量主窗']['超過3檔的換股日占比'])}、營飆 {pc(c9['營飆主窗']['超過3檔的換股日占比'])}。",
        f"**6. 母體相對化 R1／R2**：營飆 原版「{VL['原版']['營飆標籤']}」→ R1「{VL['R1']['營飆標籤']}」、R2「{VL['R2']['營飆標籤']}」；營量 原版「{VL['原版']['營量標籤']}」→ R1「{VL['R1']['營量標籤']}」、R2「{VL['R2']['營量標籤']}」"
        f"（⛔ 只報方向）。R2 門檻（逐年中位）從 2016 年 {r2y[min(r2y)]:.2f} 億升到 2026 年 {r2y[max(r2y)]:.2f} 億，營飆訊號剩原版的 {pc(VL['R2']['營飆訊號'] / VL['原版']['營飆訊號'], 0)}。",
        f"**7. 母體大小與濾網寫法**：原版閘每換股日平均 {S['⑦母體']['原版每換股日平均_首年末年'][0]:.0f} 檔（2016）→ {S['⑦母體']['原版每換股日平均_首年末年'][1]:.0f} 檔（2026）；"
        f"大盤濾網五種替代寫法與現行「每日」結果不同的訊號 {min(v['與每日不同'] for v in S['⑪六寫法'].values() if v['與每日不同'])}～{max(v['與每日不同'] for v in S['⑪六寫法'].values())} 筆（AND 共 {T['q11_variants']['AND 訊號'].iloc[0]:,} 筆）。",
        f"**8. 大盤閘貼線**：營飆進場日 0050 距 200 日線 ±3% 內 {pc(S['⑩0050距離']['|距離|≤3%占比'])}；判定日挪 ±1 天就翻的 {pc(S['⑩0050距離']['挪±1天內翻轉占比'])}、±3 天內 {pc(S['⑩0050距離']['挪±3天內翻轉占比'])}。正式規則用 0050 **還原價**。",
        f"**9. 今年波動**：{S['§四-5']['一行']}。"]
    Ls = ["# 營量 v1、營飆 v1 描述統計（⛔ 不附報酬、不計 N）", "",
          f"產出 {S['產出']}；讀法寫死 {S['讀法寫死']}。回測線子代理。依據：台股 1009-1542 §三、§四；台股 1009-1559 §三；裁定 seq321 §四。程式 `backtest/researchYLdesc.py`。", "",
          "## 結論先講", ""] + [f"- {h}" for h in head] + ["",
          "## 閘門", "",
          f"- 閘 E 引擎重跑 ＝ resultsT1fix：{json.dumps(S['閘']['E'], ensure_ascii=False)}",
          f"- 閘 P 自建面板（原版閘）＝ panel_rev：{json.dumps(S['閘']['P'], ensure_ascii=False)}",
          f"- 閘 A 自建原版 AND ＝ sig_edc6f/and_signals：{json.dumps({k: v for k, v in S['閘']['A'].items() if k != '各版 AND 列'}, ensure_ascii=False)}",
          f"- 閘 E（R1／R2 流程的原版）：{json.dumps(S['閘']['E_版原版'], ensure_ascii=False)}", ""]
    Ls += ["## ① 一次性收入（下個月營收 ≤ 訊號月 × 0.5）", ""] + [f"- {k}：{json.dumps(v, ensure_ascii=False)}" for k, v in o1.items()] + ["", "逐年見 q1_by_year.csv。", ""]
    Ls += ["## ② 併購／合資公告（訊號月前後 6 個月）", ""] + [f"- {k}：{json.dumps(v, ensure_ascii=False)}" for k, v in o2.items()] + ["", "逐年見 q2_by_year.csv。", ""]
    t3 = T["q3_cyclical"]
    Ls += ["## ③ 景氣循環產業占訊號比例（逐年）", ""] + md_table(t3, ["策略", "年", "訊號", "景氣循環", "占比", "母體占比（換股日過閘股-月）"], {"占比": pc, "母體占比（換股日過閘股-月）": pc}) + [""]
    Ls += ["## ④ 各月份訊號數（主窗）", ""] + md_table(T["q4_month"], fmt={"營量每交易日": lambda x: f"{x:.2f}", "營飆每交易日": lambda x: f"{x:.2f}"}) + ["", "年×月見 q4_year_month_*.csv。", ""]
    t5 = T["q5_project"]
    Ls += ["## ⑤ 工程／專案認列型產業", "", "定義：建材營造（建設）｜資訊服務業（系統整合）｜無塵室自訂名單 " + "、".join(f"{k} {v}" for k, v in CLEAN.items()) + "（⛔ 無官方分類）", ""] + \
        md_table(t5[t5["年"] == "全期"], ["策略", "訊號", "專案型合計", "占比", "建材營造", "資訊服務業", "無塵室", "母體占比（換股日過閘股-月）"], {"占比": pc, "母體占比（換股日過閘股-月）": lambda x: "—"}) + \
        [f"", f"母體占比逐年範圍 {pc(S['⑤專案型']['母體占比範圍'][0])}～{pc(S['⑤專案型']['母體占比範圍'][1])}；逐年見 q5_project.csv。", ""]
    t6 = T["q6_pctl"]
    Ls += ["## ⑥ 訊號的市值分位、成交金額分位（當天全母體，0＝最小 1＝最大）", ""] + md_table(t6, ["策略", "量", "n", "p10", "p25", "中位", "p75", "p90"]) + \
        ["", f"⚠ 市值用 stocks shares 欄向前沿用；股數沿用超過 250 天的訊號占比 {json.dumps(S['⑥分位']['股數沿用超過 250 天的訊號占比'], ensure_ascii=False)}；十分位個數見 q6_pctl.csv。", ""]
    t7 = T["q7_universe"]
    Ls += ["## ⑦ 每年母體檔數（換股日過閘檔數，年平均／當年曾過閘）", "", "⚠ 正式版的流動性閘是 **20 日均量 ≥ 500 張**（rerun17_build liq_mode＝shares），不是 5,000 萬；A0 是固定 5,000 萬對照。", ""] + \
        md_table(t7, ["年", "換股日數", "存續母體平均"] + [f"{g}_每換股日平均" for g in GATES] + [f"{g}_當年曾過閘檔數" for g in GATES], {c: (lambda x: f"{x:.0f}") for c in ["存續母體平均"] + [f"{g}_每換股日平均" for g in GATES]}) + [""]
    t8 = T["q8_cond"]
    Ls += ["## ⑧ 條件逐年觸發率", ""] + md_table(t8, list(t8.columns), {c: (lambda x: pc(x, 2)) for c in t8.columns if c not in ("年", "eligible 股-日", "標")}) + [""]
    ft = T["q8_feats"]
    pv = ft.pivot(index="年", columns="特徵", values="觸發率（有值者）")
    Ls += ["### FEATS 14 特徵逐年觸發率（有值者中）", "", "⚠ Q1／Q5 是當日橫斷面五等分 ⇒ 依構造約 20%（同值多時會偏離）；原門檻型才看得出漂移。有值率見 q8_feats.csv。", ""] + \
        md_table(pv.reset_index(), ["年"] + list(pv.columns), {c: (lambda x: pc(x, 1)) for c in pv.columns}) + [""]
    sb = T["q8_surge_base"]
    Ls += ["### 飆股基準率（seq6 網格、全母體、合格格中位）", "", f"合格格 {S['⑧觸發率']['飆股基準率']['合格格數']} 格（兩段事件 ≥ 30）。基準率 ＝ 當年起漲事件 ÷ 當年定義域股-日。⛔ 不寫「N 天漲一倍」。", ""] + \
        md_table(sb, ["來源", "年", "格數", "基準率格中位", "p10", "p90", "標"], {c: (lambda x: pc(x, 3)) for c in ("基準率格中位", "p10", "p90")}) + [""]
    t9 = T["q9_concentration"]
    Ls += ["## ⑨ 換股日持股集中度（產業：" + S["⑨集中度"]["產業分類"] + "）", "", "前瞻段 ＝ 主窗之後到快照資料尾（進場 2026-08-25～2026-09-24）；⚠ 2026-09-25 之後的每日名單不在本快照。β ＝ 進場前 60 日持股等權報酬對 0050 的斜率（漲日／跌日分算；⛔ 不是之後的報酬）。", ""] + \
        md_table(t9, list(t9.columns), {"超過3檔的換股日占比": pc, "可補比例": pc, "ρ中位": lambda x: f"{x:.3f}", "等效獨立檔數中位": lambda x: f"{x:.1f}",
                                        "β漲日中位": lambda x: f"{x:.2f}", "β跌日中位": lambda x: f"{x:.2f}"}) + \
        ["", "前瞻段換股日數：" + "、".join(f"{nm} {int(t9[(t9['策略'] == nm) & (t9['段'] == '前瞻段') & (t9['年'] == '全期')]['換股日（營飆為 200 顆合計）'].sum())}" for nm in ("營量", "營飆")) +
         "（營飆 200 顆在 2026-08-25～09-24 都沒有新買進 ⇒ 前瞻段無資料；真正的前瞻紀錄要等每日名單資料，見待決事項）",
         "", "最常是最大產業：" + json.dumps(S["⑨集中度"]["最常是最大產業"], ensure_ascii=False), ""]
    d10 = S["⑩0050距離"]
    Ls += ["## ⑩ 營飆進場日 0050 離 200 日線", "", f"- 訊號 {d10['營飆訊號']} 筆、{d10['不同進場日']} 個進場日；距離分佈 {json.dumps(d10['距離分佈'], ensure_ascii=False)}",
           f"- |距離| ≤ 3%：{pc(d10['|距離|≤3%占比'])}（按進場日 {pc(d10['|距離|≤3%占比（不同進場日）'])}）",
           f"- 判定日挪 ±1／±2／±3 天內閘狀態翻轉：{pc(d10['挪±1天內翻轉占比'])}／{pc(d10['挪±2天內翻轉占比'])}／{pc(d10['挪±3天內翻轉占比'])}",
           f"- 正式規則：{d10['正式規則 0050 價']}", ""]
    Ls += ["## ⑪ 大盤濾網六種寫法", ""] + md_table(T["q11_variants"]) + ["", "### 八段大跌期間的新進場", ""] + md_table(T["q11_crash"]) + [""]
    Ls += ["## R1／R2 母體相對化（⛔ 只報方向、母體檔數、訊號數）", "", f"- 門檻：{json.dumps(r1['門檻'], ensure_ascii=False)}", ""] + \
        ["| 版 | 營飆訊號 | 營量訊號 | AND 檔數 | 營飆標籤 | 營量標籤 | 與原版方向一致 |", "|---|---|---|---|---|---|---|"] + \
        [f"| {GNAME[g]} | {VL[g]['營飆訊號']} | {VL[g]['營量訊號']} | {VL[g]['AND 檔數']} | {VL[g]['營飆標籤']} | {VL[g]['營量標籤']} | "
         f"{'—' if g == '原版' else ('營飆' + ('是' if r1['結論方向一致'][g]['營飆'] else '否') + '、營量' + ('是' if r1['結論方向一致'][g]['營量'] else '否'))} |" for g in GATES] + \
        ["", "每年母體檔數見 ⑦（原版／A0／R1／R2 四欄）。", ""]
    Ls += ["## 營量排序（relvol）真正改變買進的占比（比照 PREREG營飆排名 §一）", ""] + [f"- {k}：{json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v}" for k, v in rk.items()] + [""]
    Ls += ["## §四 處置新制與制度斷點", "", "### 1. FEATS 14 個特徵用到什麼", ""] + md_table(pd.DataFrame(S["§四-1"])) + \
        ["", "⇒ 14 個都 **沒有用到處置**；用到注意股 1 個（注意≥3 次）；固定價位 1 個（股價 ＜ 20 元）；固定比率 1 個（營收年增 ≥ 50%）；漲停類 1 個（20 日漲停 ≥ 3，7%→10% 已分段）；其餘是當日橫斷面五等分（相對）。", "",
         "### 2. 每日名單第五節、真頂 T1：要改的地方（⛔ 本件未改程式，由回測線本 session 決定）", ""] + SEC42 + \
        ["", "### 3. 本報告的制度斷點行", "", S["§四-3"]["一行"], "", "（全部斷點見 regime_crossed.csv）", "",
         "### 4. 固定比率／漲幅／金額張數", "", "逐條檔名＋行號見 fixed_rules.csv（grep 結果，含 docstring 行）；要點：", ""] + SEC44 + \
        ["", "### 5. 今年個股波動 vs 回測各年", "", S["§四-5"]["一行"], "", f"各年中位（當年曾過原版閘者）：{json.dumps({k: round(v, 3) for k, v in S['§四-5']['母體（當年曾過原版閘者）各年中位'].items()}, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Ls) + "\n")
    write_html(S, T, head)


SEC42 = ["- `backtest/daily_list.py` 第 158 行第五節標題「五、買賣流程追蹤」與第 160 行流程字串：建議在「買賣流程追蹤」標題後加「（W1／W2 的處置條件：回測舊制 10／12 日、2026-08-10 起實際新制 5／7 日）」",
         "- `backtest/surge_flow_daily.py` docstring 第 15～16 行（W1「過去 60 日無處置」、W2「再次進入處置／處置出關」）：建議加註「處置期 2026-08-10 起由 10 日改 5 日 ⇒ 出關更快、『再次處置』間隔變短；回測（2021～2026-07）全是舊制」",
         "- `backtest/researchYL_truetopT.py` 第 16 行 U3「T1 真頂訊號（主版）＝ W2」（再次處置／處置出關，處置期由 10 日改 5 日直接改變 W2 出現的時點）：報表（resultsYL_truetopT/REPORT.md 與 HTML）結論句前加「舊制回測（處置 10／12 日）、新制實際（2026-08-10 起 5／7 日）」；"
         "`researchSurge6_topjudge.py`、`researchSurge6_topwarn.py`（頂部判定／警示）同樣加註",
         "- 前瞻紀錄（每日名單的實際紀錄）以 2026-08-10 分段：建議在 resultsYLwatch／每日名單 log 加欄「處置制度＝舊／新」（依訊號日 ≥ 2026-08-10）",
         "- 資料端提醒（資料庫 1712 ②）：跨 8/10 的 42 筆處置 end_date 仍是原公告 10／12 日，用到時要對證交所對照表"]
SEC44 = ["- **固定金額／張數**：營量／營飆母體 `patterns.py` liq_min_shares 500,000 股（＝500 張，`research34` gate、`list_yl13_watch` 同管線）；`patterns.py` liq_min_amount 5,000 萬（並列母體）；"
         "`gate_b_status.py` 門檻B amt20 ≥ 5,000 萬；`data.py` GAP_LIQ_SHARES 500 張（斷點判定的流動性前提）；每日名單第三、四節的「3 倍量門檻張數」是相對量換算、不是固定張數",
         "- **固定漲幅**：`research11.py`／`list_yl13_watch.py` c1 20 日漲 ≥ 30%（C1＝0.30、明天門檻 1.30×）、c2 20 根漲停 ≥ 3（漲停價 7%→10% 於 2015-06-01 分段）；"
         "`surge_flow_daily.py` 回落 30%（×0.7）、參考停損 ×0.85、20% 切段",
         "- **固定倍數**：c3 成交額 ≥ 前 20 日均 3 倍（相對自己，⛔ 不受當沖降稅影響，台股 1008 已實測）",
         "- **固定比率**：FEATS「營收年增 ≥ 50%」（researchSurge5 d_R2a）；營量／營飆正式規則本身沒有 PE／PBR／殖利率門檻",
         "- **處置／注意**：`research34` gate 排除處置期與出關後 5 日（`data.disposal_mask` after_days＝5）；`surge_flow_daily` W1／W2；FEATS 注意股 ≥ 3 次"]


def write_html(S, T, head):
    css = """:root{--bg:#fff;--fg:#1d2330;--mut:#5b6474;--line:#e3e6ec;--acc:#2f5fb3;--bad:#b3402f;--card:#f6f8fb}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#14171c;--fg:#e6e9ef;--mut:#9aa3b2;--line:#2b313b;--acc:#7aa2ec;--bad:#ec8a7a;--card:#1b2028}}
:root[data-theme=dark]{--bg:#14171c;--fg:#e6e9ef;--mut:#9aa3b2;--line:#2b313b;--acc:#7aa2ec;--bad:#ec8a7a;--card:#1b2028}
body{background:var(--bg);color:var(--fg);font-family:system-ui,'Noto Sans TC',sans-serif;line-height:1.6;margin:0;padding:0 16px}
main{max-width:1100px;margin:auto;padding:16px 0 48px}h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:2rem;border-bottom:1px solid var(--line)}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85rem;margin:.5rem 0}td,th{border:1px solid var(--line);padding:3px 7px;text-align:right;white-space:nowrap}
th{background:var(--card)}td.l,th.l{text-align:left}.card{background:var(--card);border-radius:8px;padding:10px 14px}.note{color:var(--mut);font-size:.85rem}.warn{color:var(--bad)}"""

    def tb(df, fmt=None):
        fmt = fmt or {}
        h = ["<div class='wrap'><table><tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns) + "</tr>"]
        for _, r in df.iterrows():
            cells = []
            for c in df.columns:
                v = r[c]
                s = fmt[c](v) if c in fmt else fnum(v)
                cells.append(f"<td{' class=l' if not isinstance(v, (int, float, np.integer, np.floating)) else ''}>{html.escape(s)}</td>")
            h.append("<tr>" + "".join(cells) + "</tr>")
        return "".join(h) + "</table></div>"
    md = lambda s: html.escape(s).replace("**", "")  # noqa: E731
    H = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>營量營飆描述統計</title><style>{css}</style></head><body><main>",
         "<h1>營量 v1、營飆 v1 描述統計</h1>",
         f"<p class='note'>產出 {S['產出']}（讀法寫死 {S['讀法寫死']}）｜回測線｜⛔ 全部是描述：不附任何報酬、不計 N。R1／R2 只報「標籤方向是否一致」。</p>",
         "<h2>結論先講</h2><div class='card'><ol>" + "".join(f"<li>{md(h)}</li>" for h in head) + "</ol></div>"]
    pcf = lambda x: pc(x)  # noqa: E731
    t3 = T["q3_cyclical"]
    H += ["<h2>① 一次性營收、② 併購公告</h2>", tb(T["q1_by_year"], {"占比": pcf}), tb(T["q2_by_year"], {"前占比": pcf, "後占比": pcf}),
          "<p class='note'>一次性 ＝ 下個月營收 ≤ 訊號月 × 0.5。併購 ＝ 重大訊息主旨分類「併購／合資」（庫裡沒有併表欄）；後 6 個月只算窗已滿的訊號。</p>",
          "<h2>③ 景氣循環產業（塑膠、鋼鐵、航運、油電燃氣、化學、橡膠）</h2>", tb(t3[["策略", "年", "訊號", "景氣循環", "占比", "母體占比（換股日過閘股-月）"]], {"占比": pcf, "母體占比（換股日過閘股-月）": pcf}),
          "<h2>④ 各月份訊號數</h2>", tb(T["q4_month"], {"營量每交易日": lambda x: f"{x:.2f}", "營飆每交易日": lambda x: f"{x:.2f}"}),
          "<h2>⑤ 工程／專案認列型</h2>", tb(T["q5_project"], {"占比": pcf, "母體占比（換股日過閘股-月）": pcf}),
          "<h2>⑥ 市值、成交金額分位</h2>", tb(T["q6_pctl"][["策略", "量", "n", "p10", "p25", "中位", "p75", "p90"]]),
          "<h2>⑦ 每年母體檔數</h2><p class='warn'>正式版流動性閘是「20 日均量 ≥ 500 張」，不是 5,000 萬；A0 為 5,000 萬對照。</p>", tb(T["q7_universe"], {c: (lambda x: f"{x:.0f}") for c in T["q7_universe"].columns if "平均" in c}),
          "<h2>⑧ 條件逐年觸發率</h2>", tb(T["q8_cond"], {c: (lambda x: pc(x, 2)) for c in T["q8_cond"].columns if c not in ("年", "eligible 股-日", "標")}),
          tb(T["q8_feats"].pivot(index="年", columns="特徵", values="觸發率（有值者）").reset_index(), {c: pcf for c in T["q8_feats"]["特徵"].unique()}),
          tb(T["q8_surge_base"], {c: (lambda x: pc(x, 3)) for c in ("基準率格中位", "p10", "p90")}),
          "<h2>⑨ 持股集中度</h2><p class='note'>產業：" + html.escape(S["⑨集中度"]["產業分類"]) + "。β 是進場前 60 日的共動，⛔ 不是之後的報酬。</p>",
          tb(T["q9_concentration"], {"超過3檔的換股日占比": pcf, "可補比例": pcf}),
          "<h2>⑩ 營飆進場日 0050 離 200 日線</h2><div class='card'>" + md(json.dumps({k: v for k, v in S["⑩0050距離"].items() if k != "距離分佈"}, ensure_ascii=False)) + "</div>",
          "<h2>⑪ 大盤濾網六種寫法</h2>", tb(T["q11_variants"]), tb(T["q11_crash"]),
          "<h2>R1／R2 母體相對化（只報方向）</h2>",
          tb(pd.DataFrame([{"版": GNAME[g], **{k: v for k, v in S["R1R2"]["各版"][g].items() if not k.startswith("閘")}} for g in GATES])),
          "<h2>營量排序真正改變買進的占比</h2><div class='card'>" + md(json.dumps(S["營量排序"], ensure_ascii=False)) + "</div>",
          "<h2>§四 處置新制與制度斷點</h2>", tb(pd.DataFrame(S["§四-1"])), "<ul>" + "".join(f"<li>{md(x)}</li>" for x in SEC42) + "</ul>",
          f"<p>{md(S['§四-3']['一行'])}</p>", "<ul>" + "".join(f"<li>{md(x)}</li>" for x in SEC44) + "</ul>", f"<p>{md(S['§四-5']['一行'])}</p>",
          "</main></body></html>"]
    open(os.path.join(OUT, "營量營飆描述統計.html"), "w", encoding="utf-8").write("\n".join(H))


def report(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    ctx = base_ctx()
    PN = pd.read_csv(os.path.join(WORK, "panel_all.csv.gz"), dtype={"stock_id": str, "period": str})
    GV, ginfo = gate_variants(PN, ctx["cal"])
    items(a, ctx, PN, GV, ginfo)


# ═════════════ 抽樣獨立重算（--check）═════════════
def check(a):
    """每項用 pandas 從原始檔重算（⛔ 不呼叫本檔的 items 函式），對 summary.json／各 csv。"""
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    H2 = RR.H2D
    out = {}
    cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(H2, "meta", "calendar_twse.csv"))["date"])).sort_values()
    A = pd.read_csv("backtest/resultsN17/sig_edc6f/and_signals.csv.gz", dtype={"sid": str})
    w0, w1 = int(cal.searchsorted(pd.Timestamp(RR.W0))), int(cal.searchsorted(pd.Timestamp(RR.W1)))
    YLc = A[(A["entry_pos"] >= w0) & (A["entry_pos"] <= w1)].copy()
    pr = pd.read_csv("backtest/resultsN17/sig_edc6f/panel_rev.csv.gz", dtype={"stock_id": str, "period": str})
    pr["rev_hi24"] = pr["rev_hi24"].fillna(False).astype(bool)
    # k1 ① 營量：merge_asof 找訊號月
    s = YLc[["sid", "pos"]].rename(columns={"sid": "stock_id"}).sort_values("pos")
    p = pr[["stock_id", "signal_pos", "period", "rev_hi24"]].sort_values("signal_pos")
    m = pd.merge_asof(s, p, left_on="pos", right_on="signal_pos", by="stock_id", direction="backward")
    revs = []
    for f in sorted(glob.glob(os.path.join(H2, "mops", "revenue_hist", "*.csv"))):
        revs.append(pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]))
    RV = pd.concat(revs).drop_duplicates(["stock_id", "period"], keep="last")
    RV["v"] = pd.to_numeric(RV["當月營收"], errors="coerce")
    rmap = dict(zip(zip(RV["stock_id"], RV["period"]), RV["v"]))
    nxt = lambda q: (pd.Period(q, "M") + 1).strftime("%Y-%m")  # noqa: E731
    d = [(rmap.get((r.stock_id, nxt(r.period)), np.nan) <= 0.5 * rmap.get((r.stock_id, r.period), np.nan))
         if np.isfinite(rmap.get((r.stock_id, nxt(r.period)), np.nan)) and np.isfinite(rmap.get((r.stock_id, r.period), np.nan)) else None for r in m.itertuples()]
    k1 = sum(1 for x in d if x)
    out["k1 ①營量 掉一半筆數"] = {"重算": k1, "summary": S["①一次性收入"]["營量"]["掉回一半以上"], "不同": int(k1 != S["①一次性收入"]["營量"]["掉回一半以上"])}
    # k2 ③ 營量 全期景氣循環筆數（產業別各檔最後一期，獨立讀）
    RI = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "產業別"]) for f in sorted(glob.glob(os.path.join(H2, "mops", "revenue_hist", "*.csv")))])
    RI = RI.drop_duplicates(["stock_id", "period"], keep="last").sort_values(["period"], kind="stable").groupby("stock_id")["產業別"].last()
    k2 = int(YLc["sid"].map(RI).isin(CYC).sum())
    t3 = pd.read_csv(os.path.join(OUT, "q3_cyclical.csv"))
    v2 = int(t3[(t3["策略"] == "營量") & (t3["年"] == "全期")]["景氣循環"].iloc[0])
    out["k2 ③營量 景氣循環筆數"] = {"重算": k2, "csv": v2, "不同": int(k2 != v2)}
    # k3 ⑦ 原版：每年每換股日平均 ＝ panel_rev 列數
    t7 = pd.read_csv(os.path.join(OUT, "q7_universe.csv"))
    pr["年"] = [cal[x].year for x in pr["signal_pos"]]
    g = pr.groupby(["年", "signal_pos"]).size().groupby("年").mean()
    bad = sum(abs(g.loc[int(r["年"])] - r["原版_每換股日平均"]) > 1e-9 for _, r in t7.iterrows())
    out["k3 ⑦原版每換股日平均（panel_rev）"] = {"年數": len(t7), "不同": int(bad)}
    # k4 營量排序：audit_seed0 ＋ AND 表（原始 T1 前 entry 不變）
    au = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str})
    ent = YLc.groupby("entry_pos")["sid"].apply(list).to_dict()
    held = set(); over = act = 0
    ev = au.groupby("t")
    for t in sorted(set(au["t"]) | set(ent)):
        if t in ev.groups:
            gg = ev.get_group(t)
            for sid in gg.loc[gg["side"] == "sell", "sid"]:
                held.discard(sid)
        if t in ent:
            c = [x for x in ent[t] if x not in held]; fr = 20 - len(held)
            over += len(c) > fr; act += (len(c) > fr) and fr > 0
        if t in ev.groups:
            gg = ev.get_group(t)
            held |= set(gg.loc[gg["side"] == "buy", "sid"])
    out["k4 營量 候選＞空槽日"] = {"重算": over, "summary": S["營量排序"]["候選＞空槽日"], "不同": int(over != S["營量排序"]["候選＞空槽日"])}
    out["k4b 營量 有作用日"] = {"重算": act, "summary": S["營量排序"]["其中有作用（0＜空槽＜候選）"], "不同": int(act != S["營量排序"]["其中有作用（0＜空槽＜候選）"])}
    # k5 ⑩ ±3%：0050 未還原 × adj 因子（獨立式）
    raw = pd.read_csv(os.path.join(H2, "stocks", "0050.csv"), dtype={"date": str}); raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.drop_duplicates("date").set_index("date")["close"].astype(float)
    adj = pd.read_csv(os.path.join(H2, "adj", "0050.csv"), dtype={"date": str}); adj["date"] = pd.to_datetime(adj["date"])
    fac = np.ones(len(raw))
    for dte, cf in zip(adj["date"], adj["factor"].astype(float)):
        fac[raw.index < dte] *= cf
    b = (raw * fac).reindex(cal).ffill().to_numpy()
    ma = pd.Series(b).rolling(200).mean().to_numpy()
    reg = b > ma
    e = YLc["entry_pos"].to_numpy(); yf = YLc[reg[e - 1]]
    dd = b[yf["entry_pos"].to_numpy() - 1] / ma[yf["entry_pos"].to_numpy() - 1] - 1
    k5 = float((np.abs(dd) <= 0.03).mean())
    out["k5 ⑩ |距離|≤3% 占比"] = {"重算": k5, "summary": S["⑩0050距離"]["|距離|≤3%占比"], "不同": int(abs(k5 - S["⑩0050距離"]["|距離|≤3%占比"]) > 1e-9),
                                "營飆訊號數": int(len(yf)), "summary 訊號數": S["⑩0050距離"]["營飆訊號"]}
    out["k5b 營飆訊號數"] = {"不同": int(len(yf) != S["⑩0050距離"]["營飆訊號"])}
    # k6 ⑪ 月初看一次（獨立迴圈）
    ym = pd.Series(cal.year * 12 + cal.month)
    firstpos = ym.groupby(ym).apply(lambda x: x.index[0]).to_dict()
    eA = A["entry_pos"].to_numpy()
    al = np.array([bool(reg[firstpos[ym[x]] - 1]) for x in eA])
    t11 = pd.read_csv(os.path.join(OUT, "q11_variants.csv"))
    v6 = int(t11[(t11["範圍"] == "全部 AND（進場 2017-02 起）") & (t11["寫法"] == "月初看一次")]["允許"].iloc[0])
    out["k6 ⑪月初看一次 允許"] = {"重算": int(al.sum()), "csv": v6, "不同": int(int(al.sum()) != v6)}
    v6d = int(t11[(t11["範圍"] == "全部 AND（進場 2017-02 起）") & (t11["寫法"] == "每日（現行）")]["允許"].iloc[0])
    out["k6b ⑪每日 允許"] = {"重算": int(reg[eA - 1].sum()), "csv": v6d, "不同": int(int(reg[eA - 1].sum()) != v6d)}
    # k7 R1 的 X：panel_rev 在 2016-01-08 的列數 ÷ 當天存續（stocks.csv first/last_seen ∩ gate3 ∩ 有日檔）
    sp0 = int(cal.searchsorted(pd.Timestamp("2016-01-08")))
    n0 = int((pr["signal_pos"] == sp0).sum())
    out["k7 R1 sp0 原版過關"] = {"重算": n0, "summary": S["R1R2"]["門檻"]["sp0_原版過關"], "不同": int(n0 != S["R1R2"]["門檻"]["sp0_原版過關"])}
    # k8 FEATS 一格：注意≥3 次 2020 年
    import json as _j
    fcol = _j.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"]; fcol = eval(fcol) if isinstance(fcol, str) else fcol
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); bar = np.load(os.path.join(WORK5, "bar.npy"))
    calS = pd.to_datetime(pd.read_csv(os.path.join(ST, "meta", "calendar_twse.csv"))["date"]).sort_values().reset_index(drop=True)
    cols = np.flatnonzero(calS.dt.year.to_numpy() == 2020)
    q = np.asarray(Qm[fcol.index("d_att60")])[:, cols]; bb = bar[:, cols]
    k8 = float(((q == 3) & bb).sum() / ((q > 0) & bb).sum())
    ft = pd.read_csv(os.path.join(OUT, "q8_feats.csv"))
    v8 = float(ft[(ft["特徵"] == "原：注意股60日次數級距｜≥3 次") & (ft["年"] == 2020)]["觸發率（有值者）"].iloc[0])
    out["k8 FEATS 注意≥3 次 2020"] = {"重算": k8, "csv": v8, "不同": int(abs(k8 - v8) > 1e-12)}
    tot = sum(v["不同"] for v in out.values())
    out["合計不同"] = tot
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", choices=["run", "report"], default="run")
    ap.add_argument("--procs", type=int, default=3); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        sys.exit(1 if check(a) else 0)
    run(a) if a.mode == "run" else report(a)

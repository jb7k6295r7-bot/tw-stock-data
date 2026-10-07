# -*- coding: utf-8 -*-
"""連續虧損（F4）飆股為什麼漲——起漲前後到頂點之間發生了什麼（描述；使用者直接問；參考、⛔ 不計 N、不需登錄）。回測線（子代理執行）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMineF4why            # 本體＋網頁
    ...                                                                   -m backtest.researchMineF4why page       # 只重做網頁
    抽樣查核：... -m backtest.researchMineF4why --check（⛔ 不呼叫本檔本體、researchMine、researchMineF4 的函式；從原始 CSV 自算）

⭐ 讀法寫死時間：2026-10-07 08:20（台北）；寫死前 ⛔ 沒看任何本件數字（只知道派工單轉述：起漲當下，變飆股的 F4 股和一般 F4 股在「虧損改善、營收成長」比例幾乎一樣）。
   使用者原話：「F4在變飆股的過程中，是因為業績有變好，轉型成功還是什麼原因開始漲的？」
   使用者固定規矩：描述性統計，先答涵蓋率（F4 飆股裡有幾成有這個情況；依比例高到低全部列），倍數放後面補充；⛔ 不轉成預測題；
   飆股 ＝ seq6 網格 250 格，每個數字取全網格各格中位（附 p10～p90）；⛔ 不寫「N 天漲一倍」；很多股票本來就有的情況註明「對照組也差不多」。

═══ 讀法（Y 標）═══
 Y1 事件（同 researchMineF4 Z2）：s5 events 全部 250 格、t＋H ≤ 2026-08-31（U4b）、m ＝ 嚴格 ＜ t 的最後月底判定日；「F4 飆股」＝ m 時 F4（F4a ∨ F4b）；
    頂點 P ＝ s5 events 的 P（(t, t＋H] 內最高收盤那天、同價取最早；researchSurge5 S7）；段依 t 的月份（探索 2017-03～2021-12、確認 2022-01～2026-08、合併）；
    版本：全部上市櫃（主）、W1 母體內（EL[m]）。⭐ 閘門：F4 飆股集合與 ~/minework/F4/events.npz 逐筆相同
 Y2 時間窗（s5 日曆的交易日位置）：起漲前 [t−60, t−1]｜起漲到頂點 [t, P]｜頂點後 [P＋1, P＋60]（參考；超過 s5 日曆末日 2026-09-24 的部分截掉，截掉比例照報）｜
    頂點前合併 [t−60, P]（「都沒變好」「什麼都沒有」「最先發生」用）。「窗內發生」＝ 該事件的生效交易日落在窗內（事後描述，窗可延伸到頂點）
 Y3 業績（1 類）：
    季報：researchMine.load_fin 的單季 EPS 與可用日 ap（上傳時戳的次一交易日；無時戳 ⇒ 法定期限＋5 個交易日）；某季在 ap 那天算「公布」；
      e0 ＝ 該季、e1 ＝ 前一季、e4 ＝ 去年同季（皆取資料中的值；缺值 ⇒ 該比較算沒有）；比前一季好 e0＞e1、比去年同季好 e0＞e4（皆含虧損縮小）、
      由虧轉盈 e1＜0＜e0（比前一季）或 e4＜0＜e0（比去年同季）、單季賺錢 e0＞0
    月營收：同 researchMineF4（revenue_hist @796d94c9da；researchMineF4.load_rev／rev_series）；生效日 ＝ 次月 10 日（2026-01 期起 15 日）之後第一個交易日
      （⚠ 法定期限代理，不是實際公布時戳）；該期有值才算公布；年增 ＞0／＞20%／＞50%、創 12／24 月新高（同 researchMineF4 Z6）、連續年增 ≥3／≥6 個月
    業績變好（寬）＝ EPS 比前一季好 ∨ 比去年同季好 ∨ 月營收年增 ＞ 0；業績明顯變好（嚴）＝ 由虧轉盈（任一）∨ 月營收年增 ＞ 50% ∨ 創 24 個月新高；
    「都沒變好」＝ 窗內寬（嚴）都沒有；另列重大訊息「自結財報／營收」類（有發就算、不論好壞）
 Y4 重大訊息：tw-stock-data main 8425186bd2 的 data/mops/news/2016～2026（同 researchNewsCat seq2 用的版本）；鍵 (date, time, stock_id, serial) 去重；market ∈ {sii, otc}；
    股票對 s5 名單（uni.csv stock_id）；生效交易日 ＝ 公告日是交易日且 time[:5] ≤ "13:30" ⇒ 當天，否則次一交易日（同 researchNewsCat）；
    分類 ＝ researchNewsCat.SEQ2_SRC 的 classify()（從原始碼字串用 ast 取出、一字未改；12 類，有出入以程式為準）
    補充關鍵字旗（⭐ 只描述；不論 classify 歸哪一類都看主旨原文，所以和分類會重疊）：
      董事改選／經營權 ＝ 含「經營權」「改選」「補選」或（「董事」且「選任」）｜私募 ＝「私募」｜公司更名 ＝「更名」「名稱變更」「變更公司名稱」｜
      營業項目 ＝「營業項目」｜轉型／新事業／跨足 ＝「轉型」「新事業」「跨足」｜入股／策略聯盟 ＝「入股」「策略聯盟」
 Y5 轉型／經營權（2 類，⚠ 全部是代理：公告有發不代表轉型成功，也不代表跟上漲有關）＝ classify 10 經理人異動、4 併購／合資、5 增資／發債、
    7 取得或處分資產、3 減資，加上 Y4 六個關鍵字旗；任一 ⇒「轉型／經營權類任一」
 Y6 訂單／題材（3 類）＝ classify 6 得標／接單／合約、11 法說會、2 澄清媒體報導；任一 ⇒「訂單／題材類任一」
 Y7 炒作／籌碼（4 類）：注意股 ＝ 主快照 796d94c9da meta/attention.csv 的不重複 (股, 日)（窗內 ≥1、≥3 次）；處置 ＝ meta/disposal.csv 的 start_date（次一交易日對齊）落在窗內（≥1 次）；
    漲停 ＝ researchSurge5 同法（接合版面 stitch_950ad26e12_b53f5540a8、未還原收盤、research11.limit_flags、還原事件日與上市前 5 根不判）的漲停日（≥1、≥3、≥5 天）；
      ⭐ 閘門：每檔有效 K 棒滾 20 根加總 ＝ s5 F.npy 的 lu_20（有值處逐一相同）
    融資 ＝ surge_b53f5540a8ad 的 stocks_margin m_balance（交易日往前沿用）；變化 ＝ 窗末÷窗首−1（起漲前 t−61→t−1、起漲到頂點 t−1→P、頂點後 P→P＋60、
      頂點前合併 t−61→P；窗首 ＞0 且兩端有值才算，否則算沒有）：增加 ＞0、≥ 50%；
    公司自己發的「注意交易資訊」公告（classify 1）另列；「炒作／籌碼類任一」＝ 注意 ∨ 處置 ∨ 漲停
 Y8 族群（5 類）：產業別 ＝ 主快照 meta/industry.csv industry_name（現值套回 ⇒ 標「後見」）；同一格的 s5 事件（U4b 後、不論旗）中，
    同產業、不同股票、起漲日在 [t−20, t＋20] 者 ≥ 1 ⇒ 有；查無產業別 ⇒ 沒有。只有一個窗（起漲日前後 20 個交易日）
 Y9 什麼都沒有（6 類）：1～3 類（業績變好寬、轉型類任一、題材類任一）都沒有；再拆「只有炒作／籌碼」與「1～4 都沒有」；四個窗各報
 Y10 最先發生（頂點前合併窗）：業績（寬；另報嚴版）、轉型、題材、注意／處置 四類各自窗內最早生效日；最早者唯一 ⇒ 該類；同日並列 ⇒「同一天兩類以上」；都沒有 ⇒「都沒有」
     ⚠ 漲停、融資不是公告 ⇒ 不排；族群不排
 Y11 對照一 ＝ 同網格、同段、同版本的「不帶 F4 的飆股」（known 且 m 時非 F4）；窗用它自己的 t、P
     對照二 ＝ researchMineF4 Z3 的「沒變飆股的 F4 股-月」（~/minework/F4/rows.npz；定義域逐格同 Z3）；假起漲日 ＝ (m, m_next] 內有 K 棒的交易日中隨機一天
       （numpy default_rng(20261007)，依 rows.npz 列序、只對有 K 棒的列各抽一次 integers(候選天數)）；該月沒有 K 棒 ⇒ 不進對照二（照報）；
       假頂點 ＝ 假起漲日＋L，L 從同一格 F4 飆股（合併段、全部版，依 events 順序）的 P−t 隨機抽（default_rng([20261007, 格])，對全部列抽 integers(池大小, size＝列數)）
       ⇒ 窗長分佈同 F4 飆股；超過 s5 日曆末日截到末日。⭐ 閘門：「無 K 棒」剔除前的定義域列數逐格 ＝ researchMineF4 cells.csv.gz 的對照股月數
 Y12 彙總：每格 × 段 × 版本：涵蓋率 ＝ F4 飆股中有此情況的比例；對照一／二比例同；倍數一 ＝ 涵蓋率÷對照一、倍數二 ＝ 涵蓋率÷對照二（分母 0 ⇒ 不算）；
     網格彙總 ＝ 有 ≥ 1 個 F4 飆股的格的中位（p10～p90），對照與倍數取同一批格的中位；
     註：倍數二在 0.8～1.25 ⇒「對照組也差不多」（沒變飆股的 F4 股也常有）；倍數一在 0.8～1.25 ⇒「不帶 F4 的飆股也差不多」（只加註，⛔ 不篩選；全部項目照列）
 Y13 只描述：⛔ 不判定、⛔ 不計 N、⛔ 不轉成「能不能事先預測」（窗延伸到頂點，本來就用到起漲後才知道的事）、⛔ 不寫「N 天漲一倍」、⛔ 不給買賣建議
 Y14 --check（獨立寫法）：抽 2 格（合併段、全部版、F4 飆股 ≥ 30；default_rng(20261008)）：自己從 events.npz／日曆／flags_main.npz 分出 F4 飆股與不帶 F4 飆股、
     自己讀 news、attention、disposal、margin、fin_hist＋filing_dates、revenue_hist、industry、未還原收盤（漲停自寫 tick 表）、自己重抽假起漲日與 L、自己算對照二定義域
     ⇒ 三組比例（全部情況 × 全部窗）比 cells.csv.gz；容差：件數相同、比例相對 1e-9；flags_main.npz、rows.npz、s5 events／hdef／bar 是輸入
輸出 backtest/resultsMine/F4why/（cells.csv.gz、grid.csv、summary.json、check.json、run.log、連續虧損飆股為什麼漲.html）；逐筆 ~/minework/F4why/
"""
from __future__ import annotations

import argparse
import ast
import bisect
import glob
import hashlib
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
from backtest import research11 as R11
from backtest import researchMine as RM
from backtest import researchMineF4 as M4

TAGT = "2026-10-07 08:20（台北）"
MAIN = RM.MAIN
S5W = RM.S5W
CUT = RM.CUT
WORK = os.path.join(RM.WORK, "F4why")
OUT = os.path.join(RM.OUT, "F4why")
M4W = os.path.join(RM.WORK, "F4")
M4O = os.path.join(RM.OUT, "F4")
NEWS_SHA = "8425186bd20cdef4d39ac039ad2a6eda0903a8bb"
ND = os.path.expanduser(f"~/msdata/{NEWS_SHA}/data/mops/news")
NEWS_YEARS = range(2016, 2027)
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
MGD = os.path.expanduser("~/h2data/surge_b53f5540a8ad/data/stocks_margin")
SEED = 20261007
WPRE, WPOST, WGRP = 60, 60, 20
OFFD = "2016-09-01"
BIG = 32000
SEGS, SEGNAME, VERS = M4.SEGS, M4.SEGNAME, M4.VERS
HS5, GS5, NC5 = RM.HS5, RM.GS5, RM.NC5
WINS = ("pre", "run", "post", "prepk")
WNAME = {"pre": "起漲前 60 日", "run": "起漲到頂點", "post": "頂點後 60 日（參考）", "prepk": "起漲前 60 日到頂點（合併）", "t20": "起漲日前後 20 日"}

KW = [("kw_board", "董事改選／經營權", lambda s: any(w in s for w in ("經營權", "改選", "補選")) or ("董事" in s and "選任" in s)),
      ("kw_pp", "私募", lambda s: "私募" in s),
      ("kw_rename", "公司更名", lambda s: any(w in s for w in ("更名", "名稱變更", "變更公司名稱"))),
      ("kw_biz", "營業項目", lambda s: "營業項目" in s),
      ("kw_trans", "轉型／新事業／跨足", lambda s: any(w in s for w in ("轉型", "新事業", "跨足"))),
      ("kw_ally", "入股／策略聯盟", lambda s: any(w in s for w in ("入股", "策略聯盟")))]
EPS_T = ["eq_any", "eq_qoq", "eq_yoy", "eq_turn1", "eq_turn4", "eq_pos"]
REV_T = ["rv_any", "rv_y0", "rv_y20", "rv_y50", "rv_h12", "rv_h24", "rv_s3", "rv_s6"]
NEWS_T = [f"n{k}" for k in range(1, 13)] + ["nw_any"] + [k for k, _, _ in KW]
MKT_T = ["att", "disp", "lu"]
TYPES = EPS_T + REV_T + NEWS_T + MKT_T
GRP = {"A": ["eq_qoq", "eq_yoy", "rv_y0"], "As": ["eq_turn1", "eq_turn4", "rv_y50", "rv_h24"],
       "B": ["n10", "n4", "n5", "n7", "n3"] + [k for k, _, _ in KW], "C": ["n6", "n11", "n2"], "Dn": ["att", "disp"]}
CAT = {1: "1 業績變好", 2: "2 轉型／經營權（代理）", 3: "3 訂單／題材", 4: "4 炒作／籌碼", 5: "5 族群一起漲", 6: "6 什麼都沒有", 7: "7 其他公告（參考）",
       8: "8 最先發生的是哪一類"}
ITEMS = [  # (鍵, 類, 白話)
    ("eq_qoq", 1, "公布的季報：單季 EPS 比前一季好（含虧損縮小）"), ("eq_yoy", 1, "公布的季報：單季 EPS 比去年同季好（含虧損縮小）"),
    ("eq_turn1", 1, "公布的季報：由虧轉盈（前一季虧、這一季賺）"), ("eq_turn4", 1, "公布的季報：由虧轉盈（去年同季虧、這一季賺）"),
    ("eq_pos", 1, "公布的季報：單季賺錢"), ("rv_y0", 1, "公布的月營收：年增 ＞ 0"), ("rv_y20", 1, "公布的月營收：年增 ＞ 20%"),
    ("rv_y50", 1, "公布的月營收：年增 ＞ 50%"), ("rv_h12", 1, "公布的月營收：創 12 個月新高"), ("rv_h24", 1, "公布的月營收：創 24 個月新高"),
    ("rv_s3", 1, "公布的月營收：連續年增 ≥ 3 個月"), ("rv_s6", 1, "公布的月營收：連續年增 ≥ 6 個月"),
    ("n9", 1, "重大訊息：自結財報／營收類（有發就算、不論好壞）"),
    ("A_any", 1, "業績有變好（寬：EPS 比前一季或去年同季好、或月營收年增 ＞ 0，任一）"),
    ("A_str", 1, "業績明顯變好（嚴：由虧轉盈、月營收年增 ＞ 50%、或創 24 個月新高，任一）"),
    ("A_none", 1, "業績都沒變好（寬的反面）"), ("A_nonestr", 1, "業績沒有明顯變好（嚴的反面）"),
    ("n10", 2, "重大訊息：經理人異動（董事長、總經理等）"), ("kw_board", 2, "主旨含：董事改選／經營權"), ("n4", 2, "重大訊息：併購／合資"),
    ("n5", 2, "重大訊息：增資／發債（含私募）"), ("kw_pp", 2, "主旨含：私募"), ("n7", 2, "重大訊息：取得或處分資產"), ("n3", 2, "重大訊息：減資"),
    ("kw_rename", 2, "主旨含：公司更名"), ("kw_biz", 2, "主旨含：營業項目"), ("kw_trans", 2, "主旨含：轉型／新事業／跨足"),
    ("kw_ally", 2, "主旨含：入股／策略聯盟"), ("B_any", 2, "轉型／經營權類任一（代理）"),
    ("n6", 3, "重大訊息：得標／接單／合約"), ("n11", 3, "重大訊息：法說會"), ("n2", 3, "重大訊息：澄清媒體報導"), ("C_any", 3, "訂單／題材類任一"),
    ("att1", 4, "被列注意股 ≥ 1 次"), ("att3", 4, "被列注意股 ≥ 3 次"), ("disp1", 4, "被處置 ≥ 1 次"), ("lu1", 4, "漲停 ≥ 1 天"), ("lu3", 4, "漲停 ≥ 3 天"),
    ("lu5", 4, "漲停 ≥ 5 天"), ("mg0", 4, "融資餘額增加"), ("mg50", 4, "融資餘額增加 ≥ 50%"), ("n1", 4, "公司發「注意交易資訊」公告"),
    ("D_any", 4, "炒作／籌碼類任一（注意股、處置、漲停）"),
    ("n8", 7, "重大訊息：股利"), ("n12", 7, "重大訊息：其他類"), ("nw_any", 7, "任何重大訊息"),
    ("none123", 6, "1～3 類都沒有（沒有業績變好、沒有轉型類、沒有訂單題材）"), ("only4", 6, "1～3 類都沒有、只有炒作／籌碼"),
    ("none1234", 6, "1～4 類都沒有（完全沒事）")]
FIRST = [("A", "業績變好"), ("B", "轉型／經營權"), ("C", "訂單／題材"), ("D", "注意股／處置"), ("tie", "同一天兩類以上"), ("none", "都沒有")]
FIRST_ITEMS = [(f"{v}_{k}", 8, f"最先發生（業績用{'寬' if v == 'fw' else '嚴'}版）：{nm}") for v in ("fw", "fs") for k, nm in FIRST]
COLS = [(k, w) for k, _, _ in ITEMS for w in WINS] + [("grp", "t20")] + [(k, "prepk") for k, _, _ in FIRST_ITEMS] + [("trunc", "post")]
LAB = {k: (c, l) for k, c, l in ITEMS + FIRST_ITEMS}
LAB["grp"] = (5, "同產業另有別檔在起漲日前後 20 日內也起漲（產業現值，後見）")
LAB["trunc"] = (7, "頂點後 60 日窗被資料尾截掉")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def seq2_classify():
    """從 researchNewsCat.py 原始碼取 SEQ2_SRC 字串（ast，不 import 該檔）。"""
    src = open("backtest/researchNewsCat.py", encoding="utf-8").read()
    code = None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t_, "id", None) == "SEQ2_SRC" for t_ in node.targets):
            code = ast.literal_eval(node.value)
    assert code, "⛔ 找不到 SEQ2_SRC"
    ns: dict = {}
    exec(compile(code, "附件-重大訊息分類_seq2", "exec"), ns)
    return ns["classify"], hashlib.sha256(code.encode("utf-8")).hexdigest()


# ═════════════ 漲停（接合版面；researchSurge5 同法）═════════════
_LG: dict = {}


def _lu_init():
    D.DATA = ST
    _LG["cal"] = D.load_calendar()


def _lu_one(a):
    si, sid, mk = a
    cal = _LG["cal"]; n = len(cal)
    out = np.zeros(n, bool)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return si, out
    cA = st.df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(cA)); m = len(idx)
    if m < 2:
        return si, out
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rcA = np.array(pd.to_numeric(raw["close"], errors="coerce"), dtype=float); rcA[~(rcA > 0)] = np.nan
    rc = rcA[idx]; dates = cal[idx]
    ev_bar = np.zeros(m, bool)
    adj = D.load_adj(sid)
    if adj is not None and len(adj):
        for d in adj["date"]:
            k = int(np.searchsorted(dates, d))
            if k < m:
                ev_bar[k] = True
    skip = ev_bar.copy()
    if dates[0] > pd.Timestamp("2015-01-12"):
        skip[:5] = True
    up, _ = R11.limit_flags(rc, dates, skip)
    out[idx[up]] = True
    return si, out


# ═════════════ 每日事件陣列 ═════════════
def build_arrays(G, log, procs=4):
    cal, cal5, uni = G["cal"], G["cal5"], G["uni"]
    N5 = len(cal5); off = int(cal5.searchsorted(pd.Timestamp(OFFD))); nd = N5 - off; S5 = len(uni)
    s5ix = {x: i for i, x in enumerate(uni["stock_id"])}
    pos5 = cal5.get_indexer(cal)                                            # 主日曆位置 → s5 位置（2026-09-24 後 −1）
    EV = {ty: ([], []) for ty in TYPES}

    def add(ty, s_, d_):
        s_ = np.asarray(s_, int); d_ = np.asarray(d_, int)
        k = (s_ >= 0) & (d_ >= 0) & (d_ < N5)
        EV[ty][0].append(s_[k]); EV[ty][1].append(d_[k])
    info = {}
    # 季報
    _, F = RM.load_fin(cal, log)
    F = F.copy(); F["s5"] = F["stock_id"].map(s5ix).fillna(-1).astype(int)
    val = {(s_, y, q): e for s_, y, q, e in zip(F["stock_id"], F["y"], F["q"], F["eps"])}
    ap = F["ap"].to_numpy(); okap = (ap >= 0) & (ap < len(cal))
    d5 = np.where(okap, pos5[np.clip(ap, 0, len(cal) - 1)], -1)
    e0 = F["eps"].to_numpy(float)
    e1 = np.array([val.get((s_, y, q - 1) if q > 1 else (s_, y - 1, 4), np.nan) for s_, y, q in zip(F["stock_id"], F["y"], F["q"])], float)
    e4 = np.array([val.get((s_, y - 1, q), np.nan) for s_, y, q in zip(F["stock_id"], F["y"], F["q"])], float)
    sF = F["s5"].to_numpy()
    with np.errstate(invalid="ignore"):
        conds = {"eq_any": np.ones(len(F), bool), "eq_qoq": e0 > e1, "eq_yoy": e0 > e4, "eq_turn1": (e1 < 0) & (e0 > 0), "eq_turn4": (e4 < 0) & (e0 > 0),
                 "eq_pos": e0 > 0}
    for ty, c_ in conds.items():
        add(ty, sF[c_], d5[c_])
    info["季報列"] = int(len(F)); info["季報 s5 內且可用日在 s5 日曆內"] = int(((sF >= 0) & (d5 >= 0)).sum())
    # 月營收
    V, eff = M4.load_rev(cal, log)
    rs, rd = {t_: [] for t_ in REV_T}, {t_: [] for t_ in REV_T}
    nrev = 0
    for x in V.columns:
        si = s5ix.get(x, -1)
        if si < 0:
            continue
        v = V[x].to_numpy(float)
        yoy, h12, h24, stk, _ = M4.rev_series(v)
        j = np.flatnonzero(np.isfinite(v) & (eff < len(cal)))
        dd = pos5[eff[j]]
        with np.errstate(invalid="ignore"):
            cc = {"rv_any": np.ones(len(j), bool), "rv_y0": yoy[j] > 0, "rv_y20": yoy[j] > 0.2, "rv_y50": yoy[j] > 0.5, "rv_h12": h12[j], "rv_h24": h24[j],
                  "rv_s3": stk[j] >= 3, "rv_s6": stk[j] >= 6}
        for ty, c_ in cc.items():
            rs[ty].append(np.full(int(c_.sum()), si)); rd[ty].append(dd[c_])
        nrev += len(j)
    for ty in REV_T:
        add(ty, np.concatenate(rs[ty]), np.concatenate(rd[ty]))
    info["月營收 期別列（s5 內、有值）"] = nrev
    # 重大訊息
    classify, csha = seq2_classify()
    N = pd.concat([pd.read_csv(os.path.join(ND, f"{y}.csv"), dtype=str, keep_default_na=False) for y in NEWS_YEARS], ignore_index=True)
    info["news 原始則數（2016～2026 檔）"] = int(len(N))
    N = N.drop_duplicates(["date", "time", "stock_id", "serial"])
    N = N[N["market"].isin(["sii", "otc"])].copy()
    N["s5"] = N["stock_id"].str.strip().map(s5ix).fillna(-1).astype(int)
    info["news sii／otc"] = int(len(N)); N = N[N["s5"] >= 0].copy(); info["news 在 s5 名單"] = int(len(N))
    cv = cal5.values; dts = pd.to_datetime(N["date"]).values
    p0 = np.searchsorted(cv, dts, side="left")
    istd = (p0 < N5) & (cv[np.minimum(p0, N5 - 1)] == dts)
    late = N["time"].str.slice(0, 5).to_numpy() > "13:30"
    e_ = np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))
    N["e"] = e_; N = N[N["e"] < N5]
    subj = N["subject"].tolist(); sN = N["s5"].to_numpy(); eN = N["e"].to_numpy()
    cat = np.array([classify(x) for x in subj])
    for k in range(1, 13):
        add(f"n{k}", sN[cat == k], eN[cat == k])
    add("nw_any", sN, eN)
    for k, _, f in KW:
        m_ = np.array([f(x) for x in subj], bool)
        add(k, sN[m_], eN[m_]); info[f"關鍵字 {k} 則數"] = int(m_.sum())
    info["news 生效日在 s5 日曆內"] = int(len(N)); info["classify 來源 sha256"] = csha
    info["news 各類則數"] = {int(k): int((cat == k).sum()) for k in range(1, 13)}
    # 注意、處置
    A = pd.read_csv(os.path.join(MAIN, "meta", "attention.csv"), dtype=str, usecols=["stock_id", "date"]).dropna()
    A["stock_id"] = A["stock_id"].str.strip(); A = A.drop_duplicates()
    A["s5"] = A["stock_id"].map(s5ix).fillna(-1).astype(int)
    add("att", A["s5"].to_numpy(), np.searchsorted(cv, pd.to_datetime(A["date"]).values, side="left"))
    Dp = pd.read_csv(os.path.join(MAIN, "meta", "disposal.csv"), dtype=str, usecols=["stock_id", "start_date"]).dropna()
    Dp["stock_id"] = Dp["stock_id"].str.strip(); Dp = Dp.drop_duplicates()
    Dp["s5"] = Dp["stock_id"].map(s5ix).fillna(-1).astype(int)
    add("disp", Dp["s5"].to_numpy(), np.searchsorted(cv, pd.to_datetime(Dp["start_date"]).values, side="left"))
    # 漲停
    lup = os.path.join(WORK, "lu.npy")
    if os.path.exists(lup):
        LU = np.load(lup)
    else:
        with Pool(procs, initializer=_lu_init) as pool:
            R = pool.map(_lu_one, [(i, x, m) for i, (x, m) in enumerate(zip(uni["stock_id"], uni["market"]))], chunksize=16)
        LU = np.zeros((S5, N5), bool)
        for si, o in R:
            assert len(o) == N5
            LU[si] = o
        np.save(lup, LU)
    # 閘門：lu_20
    bjs = json.load(open(os.path.join(S5W, "build.json"), encoding="utf-8")); FX = {c: i for i, c in enumerate(bjs["特徵欄"])}
    Fm = np.load(os.path.join(S5W, "F.npy"), mmap_mode="r")
    L20 = np.asarray(Fm[FX["lu_20"]]); bar5 = np.asarray(G["bar5"])
    bad = 0; tot = 0
    for si in range(S5):
        ix = np.flatnonzero(bar5[si])
        if len(ix) < 20:
            continue
        r20 = pd.Series(LU[si, ix].astype(float)).rolling(20, min_periods=20).sum().to_numpy()
        ref = L20[si, ix]; ok = np.isfinite(ref)
        tot += int(ok.sum()); bad += int((np.abs(r20[ok] - ref[ok]) > 1e-6).sum())
    log(f"[漲停 閘門] 滾 20 根 vs s5 lu_20：不同 {bad}／{tot:,}")
    if bad:
        raise SystemExit("⛔ 漲停重算不同")
    info["漲停閘門"] = {"不同": bad, "比對格": tot}
    si_, di_ = np.nonzero(LU); add("lu", si_, di_)
    # 累計
    C = {}
    for ty in TYPES:
        s_ = np.concatenate(EV[ty][0]) if EV[ty][0] else np.zeros(0, int); d_ = np.concatenate(EV[ty][1]) if EV[ty][1] else np.zeros(0, int)
        k = d_ >= off
        cnt = np.zeros((S5, nd), np.int32)
        np.add.at(cnt, (s_[k], d_[k] - off), 1)
        cum = np.zeros((S5, nd + 1), np.int32); np.cumsum(cnt, axis=1, out=cum[:, 1:])
        C[ty] = cum
        info.setdefault("各型事件數（2016-09 起）", {})[ty] = int(k.sum())
    NX = {}
    ar = np.arange(nd, dtype=np.int32)
    for g, tys in GRP.items():
        has = np.zeros((S5, nd), bool)
        for ty in tys:
            has |= np.diff(C[ty], axis=1) > 0
        idx = np.where(has, ar[None, :], BIG).astype(np.int32)
        NX[g] = np.minimum.accumulate(idx[:, ::-1], axis=1)[:, ::-1].astype(np.int16)
    # 融資
    MB = np.full((S5, nd), np.nan, np.float32); nmg = 0
    cal5s = pd.DatetimeIndex(cal5)
    for si, x in enumerate(uni["stock_id"]):
        p_ = os.path.join(MGD, x + ".csv")
        if not os.path.exists(p_):
            continue
        mg = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "m_balance"]).drop_duplicates("date", keep="last")
        mg.index = pd.to_datetime(mg["date"])
        v = pd.to_numeric(mg["m_balance"], errors="coerce").reindex(cal5s).ffill().to_numpy(float)
        MB[si] = v[off:]; nmg += 1
    info["融資檔數"] = nmg
    # 產業
    ind = pd.read_csv(os.path.join(MAIN, "meta", "industry.csv"), dtype=str)
    imap = dict(zip(ind["stock_id"].str.strip(), ind["industry_name"].fillna("").str.strip()))
    names = sorted({v for v in imap.values() if v})
    code = {v: i for i, v in enumerate(names)}
    ind5 = np.array([code.get(imap.get(x, ""), -1) for x in uni["stock_id"]], int)
    info["產業查無（s5 名單）"] = int((ind5 < 0).sum())
    log(f"[陣列] off {off}（{cal5[off].date()}）｜{len(TYPES)} 型｜{json.dumps({k: v for k, v in info.items() if not isinstance(v, dict)}, ensure_ascii=False)}")
    return {"C": C, "NX": NX, "MB": MB, "ind5": ind5, "off": off, "N5": N5, "nd": nd}, info


# ═════════════ 窗內查詢 ═════════════
def wbounds(w, t, P, N5):
    if w == "pre":
        return t - WPRE, t - 1
    if w == "run":
        return t, P
    if w == "post":
        return P + 1, np.minimum(P + WPOST, N5 - 1)
    return t - WPRE, P


def mbounds(w, t, P, N5):
    if w == "pre":
        return t - WPRE - 1, t - 1
    if w == "run":
        return t - 1, P
    if w == "post":
        return P, np.minimum(P + WPOST, N5 - 1)
    return t - WPRE - 1, P


def wcount(AR, ty, s, a, b):
    off, nd = AR["off"], AR["nd"]
    a2 = np.clip(a - off, 0, nd); b2 = np.clip(b - off + 1, 0, nd)
    v = AR["C"][ty][s, b2] - AR["C"][ty][s, a2]
    return np.where(b2 > a2, v, 0)


def wfirst(AR, g, s, a, b):
    off, nd = AR["off"], AR["nd"]
    a2 = a - off; b2 = b - off
    nx = AR["NX"][g][s, np.clip(a2, 0, nd - 1)].astype(np.int64)
    ok = (a2 >= 0) & (a2 <= b2) & (a2 < nd) & (nx <= b2)
    return np.where(ok, nx, BIG)


def eval_rows(AR, s, t, P):
    s = np.asarray(s, int); t = np.asarray(t, int); P = np.asarray(P, int)
    N5, off = AR["N5"], AR["off"]
    assert (t - WPRE - 1 >= off).all()
    out = {}
    for w in WINS:
        a, b = wbounds(w, t, P, N5)
        c = {ty: wcount(AR, ty, s, a, b) for ty in TYPES}
        H = {ty: v > 0 for ty, v in c.items()}
        anyof = lambda ks: np.logical_or.reduce([H[k] for k in ks])
        A = anyof(GRP["A"]); As = anyof(GRP["As"]); B = anyof(GRP["B"]); Cc = anyof(GRP["C"]); Dx = H["att"] | H["disp"] | H["lu"]
        ms, me_ = mbounds(w, t, P, N5)
        x0 = AR["MB"][s, np.clip(ms - off, 0, AR["nd"] - 1)].astype(float); x1 = AR["MB"][s, np.clip(me_ - off, 0, AR["nd"] - 1)].astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.where(np.isfinite(x0) & (x0 > 0) & np.isfinite(x1), x1 / np.where(x0 > 0, x0, 1) - 1, np.nan)
            mg0 = r > 0; mg50 = r >= 0.5
        v = {k: H[k] for k in ("eq_qoq", "eq_yoy", "eq_turn1", "eq_turn4", "eq_pos", "rv_y0", "rv_y20", "rv_y50", "rv_h12", "rv_h24", "rv_s3", "rv_s6", "n9",
                               "n10", "kw_board", "n4", "n5", "kw_pp", "n7", "n3", "kw_rename", "kw_biz", "kw_trans", "kw_ally", "n6", "n11", "n2", "n1",
                               "n8", "n12", "nw_any")}
        v.update({"A_any": A, "A_str": As, "A_none": ~A, "A_nonestr": ~As, "B_any": B, "C_any": Cc,
                  "att1": c["att"] >= 1, "att3": c["att"] >= 3, "disp1": c["disp"] >= 1, "lu1": c["lu"] >= 1, "lu3": c["lu"] >= 3, "lu5": c["lu"] >= 5,
                  "mg0": mg0, "mg50": mg50, "D_any": Dx, "none123": ~(A | B | Cc), "only4": ~(A | B | Cc) & Dx, "none1234": ~(A | B | Cc | Dx)})
        for k, x in v.items():
            out[(k, w)] = np.asarray(x, bool)
        if w == "prepk":
            for ver, ga in (("fw", "A"), ("fs", "As")):
                Fm = np.stack([wfirst(AR, ga, s, a, b), wfirst(AR, "B", s, a, b), wfirst(AR, "C", s, a, b), wfirst(AR, "Dn", s, a, b)])
                mn = Fm.min(0); nmin = (Fm == mn).sum(0); none = mn >= BIG
                for i, k in enumerate(("A", "B", "C", "D")):
                    out[(f"{ver}_{k}", "prepk")] = ~none & (nmin == 1) & (Fm[i] == mn)
                out[(f"{ver}_tie", "prepk")] = ~none & (nmin >= 2)
                out[(f"{ver}_none", "prepk")] = none
    out[("trunc", "post")] = P + WPOST > N5 - 1
    return out


def to_mat(out, n):
    X = np.zeros((n, len(COLS)), bool)
    for i, c in enumerate(COLS):
        if c in out:
            X[:, i] = out[c]
    return X


def grp_flags(ind5, ev_s, ev_d, qs, qt):
    ig = ind5[ev_s]; ok = ig >= 0
    k_ind = np.sort(ig[ok].astype(np.int64) * 100000 + ev_d[ok])
    k_s = np.sort(ev_s[ok].astype(np.int64) * 100000 + ev_d[ok])
    qi = ind5[qs].astype(np.int64); qs = qs.astype(np.int64); qt = qt.astype(np.int64)
    n_ind = np.searchsorted(k_ind, qi * 100000 + qt + WGRP, "right") - np.searchsorted(k_ind, qi * 100000 + qt - WGRP, "left")
    n_s = np.searchsorted(k_s, qs * 100000 + qt + WGRP, "right") - np.searchsorted(k_s, qs * 100000 + qt - WGRP, "left")
    return (qi >= 0) & (n_ind - n_s > 0)


# ═════════════ 本體 ═════════════
def body(a):
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchMineF4why {now_tpe()}（台北）｜讀法寫死 {TAGT} =====")
    G = M4.load_base(log)
    FL, sids, cal, mepos, cal5, uni = G["FL"], G["sids"], G["cal"], G["mepos"], G["cal5"], G["uni"]
    nm, S = FL["F4"].shape
    cell, d, s = G["cell"], G["d"], G["s"]
    E = np.load(os.path.join(S5W, "events.npz"))
    Hc = np.array(HS5)[E["cell"].astype(int) // len(GS5)]
    ok = E["d"].astype(int) + Hc <= G["icut"]
    P = E["P"][ok].astype(int)
    assert np.array_equal(E["cell"][ok].astype(int), cell) and np.array_equal(E["d"][ok].astype(int), d) and (P > d).all()
    # F4／非 F4（同 researchMineF4）
    a0, b0 = SEGS["合併"]
    tdates = cal5[d]; mon_t = np.array([str(x)[:7] for x in tdates])
    insg = (mon_t >= a0) & (mon_t <= b0)
    k_ = np.searchsorted(cal[mepos].values, tdates.values, side="left") - 1
    usid = uni["stock_id"].to_numpy()[s]
    ix = {x: j for j, x in enumerate(sids)}
    jcol = np.array([ix.get(x, -1) for x in usid])
    known = insg & (jcol >= 0) & (k_ >= 0)
    f4ev = np.zeros(len(d), bool); f4ev[known] = FL["F4"][k_[known], jcol[known]]
    elev = np.zeros(len(d), bool); elev[known] = FL["EL"][k_[known], jcol[known]]
    evF = np.flatnonzero(known & f4ev); evN = np.flatnonzero(known & ~f4ev)
    ref = np.load(os.path.join(M4W, "events.npz"))
    assert np.array_equal(ref["ev"], evF), "⛔ F4 飆股與 researchMineF4 不同"
    log(f"[事件] F4 飆股 {len(evF):,}（＝ researchMineF4 events.npz）｜不帶 F4 飆股 {len(evN):,}（合併段、各格加總）")
    AR, info = build_arrays(G, log, a.procs)
    # ── 事件端
    XF = to_mat(eval_rows(AR, s[evF], d[evF], P[evF]), len(evF))
    XN = np.zeros((len(evN), len(COLS)), bool)
    for i0 in range(0, len(evN), 100000):
        q = evN[i0:i0 + 100000]
        XN[i0:i0 + len(q)] = to_mat(eval_rows(AR, s[q], d[q], P[q]), len(q))
    gi = COLS.index(("grp", "t20"))
    for c in range(NC5):
        mc = cell == c
        if not mc.any():
            continue
        es, ed = s[mc], d[mc]
        qF = cell[evF] == c; qN = cell[evN] == c
        XF[qF, gi] = grp_flags(AR["ind5"], es, ed, s[evF][qF], d[evF][qF])
        XN[qN, gi] = grp_flags(AR["ind5"], es, ed, s[evN][qN], d[evN][qN])
    log(f"[事件端] 情況欄 {len(COLS)}｜F4 {XF.shape}｜不帶 F4 {XN.shape}")
    np.savez_compressed(os.path.join(WORK, "events.npz"), evF=evF, evN=evN, XF=XF, XN=XN, cols=np.array([f"{k}|{w}" for k, w in COLS]))
    # ── 對照二
    RW = np.load(os.path.join(M4W, "rows.npz"))
    R_i, R_j, rs5, rm5, rm5n = (RW[k].astype(int) for k in ("R_i", "R_j", "rs5", "rm5", "rm5n"))
    nr = len(R_i)
    bar5 = np.asarray(G["bar5"]); hdef = G["hdef"]
    rng = np.random.default_rng(SEED)
    pt = np.full(nr, -1)
    for r in range(nr):
        dd = np.arange(rm5[r] + 1, rm5n[r] + 1)
        dd = dd[bar5[rs5[r], dd]]
        if len(dd):
            pt[r] = int(dd[rng.integers(len(dd))])
    mon_m1 = np.array([str(cal[p + 1])[:7] if p + 1 < len(cal) else "9999-99" for p in mepos])
    r_mon = mon_m1[R_i]; r_el = FL["EL"][R_i, R_j]
    hd1 = np.asarray(hdef)[rs5, np.minimum(rm5 + 1, hdef.shape[1] - 1)]
    barm = bar5[rs5, rm5]
    keyall = s.astype(np.int64) * 10000 + d
    lo = rs5.astype(np.int64) * 10000 + rm5 + 1; hi_ = rs5.astype(np.int64) * 10000 + rm5n
    M4C = pd.read_csv(os.path.join(M4O, "cells.csv.gz"))
    M4C = M4C[M4C["情況"] == "F4a"].set_index(["段", "版本", "cell"])["對照股月數"]
    gate_bad = 0
    Lall = {}
    CTL = {}                                                                # (段, 版本) → (NC5, K) 的 sum、n
    for seg in SEGS:
        for ver in VERS:
            CTL[(seg, ver)] = (np.zeros((NC5, len(COLS))), np.zeros(NC5))
    poolF = P[evF] - d[evF]
    nctl_cells = 0
    for c in range(NC5):
        H = int(HS5[c // len(GS5)])
        kc = np.sort(keyall[cell == c])
        p = np.searchsorted(kc, lo, side="left")
        HAS = (p < len(kc)) & (kc[np.minimum(p, max(len(kc) - 1, 0))] <= hi_) if len(kc) else np.zeros(nr, bool)
        base = barm & (hd1 >= H) & (rm5 + 1 + H <= G["icut"]) & ~HAS
        for seg, (a_, b_) in SEGS.items():
            for ver in VERS:
                dm = base & (r_mon >= a_) & (r_mon <= b_) & (r_el if ver != "全部" else True)
                if int(dm.sum()) != int(round(M4C.loc[(seg, ver, c)])):
                    gate_bad += 1
        pool = poolF[cell[evF] == c]
        if not len(pool):
            continue
        nctl_cells += 1
        L = pool[np.random.default_rng([SEED, c]).integers(len(pool), size=nr)]
        Lall[c] = L.astype(np.int16)
        q = np.flatnonzero(base & (r_mon >= a0) & (r_mon <= b0) & (pt >= 0))
        if not len(q):
            continue
        tq = pt[q]; Pq = np.minimum(tq + L[q], AR["N5"] - 1)
        Xq = to_mat(eval_rows(AR, rs5[q], tq, Pq), len(q))
        Xq[:, gi] = grp_flags(AR["ind5"], s[cell == c], d[cell == c], rs5[q], tq)
        for seg, (a_, b_) in SEGS.items():
            for ver in VERS:
                mm = (r_mon[q] >= a_) & (r_mon[q] <= b_) & (r_el[q] if ver != "全部" else True)
                CTL[(seg, ver)][0][c] = Xq[mm].sum(0); CTL[(seg, ver)][1][c] = mm.sum()
        if c % 25 == 0:
            log(f"[對照二] 格 {c}｜列 {len(q):,}")
    log(f"[對照二 閘門] 定義域列數逐格 ＝ researchMineF4 對照股月數：不同 {gate_bad}（共 {NC5 * 6} 格段版）")
    if gate_bad:
        raise SystemExit("⛔ 對照二定義域不同")
    np.savez_compressed(os.path.join(WORK, "control.npz"), pt=pt, cells=np.array(sorted(Lall)), L=np.stack([Lall[c] for c in sorted(Lall)]))
    nobar = int((pt < 0).sum())
    # ── 彙總
    rows = []
    for seg, (a_, b_) in SEGS.items():
        eF = (mon_t[evF] >= a_) & (mon_t[evF] <= b_); eN = (mon_t[evN] >= a_) & (mon_t[evN] <= b_)
        for ver in VERS:
            mF = eF & (elev[evF] if ver != "全部" else True); mN = eN & (elev[evN] if ver != "全部" else True)
            nF = np.bincount(cell[evF][mF], minlength=NC5).astype(float); nN = np.bincount(cell[evN][mN], minlength=NC5).astype(float)
            sF = np.stack([np.bincount(cell[evF][mF], weights=XF[mF, i], minlength=NC5) for i in range(len(COLS))], 1)
            sN = np.stack([np.bincount(cell[evN][mN], weights=XN[mN, i], minlength=NC5) for i in range(len(COLS))], 1)
            sC, nC = CTL[(seg, ver)]
            with np.errstate(invalid="ignore", divide="ignore"):
                cF = sF / nF[:, None]; cN = sN / nN[:, None]; cC = sC / nC[:, None]
            for c in range(NC5):
                for i, (k, w) in enumerate(COLS):
                    rows.append((seg, ver, RM.cell_name(c), c, int(HS5[c // len(GS5)]), float(GS5[c % len(GS5)]), k, w, int(nF[c]),
                                 cF[c, i] if nF[c] else np.nan, int(nN[c]), cN[c, i] if nN[c] else np.nan, int(nC[c]), cC[c, i] if nC[c] else np.nan))
        log(f"[彙總] {seg} 完成")
    CL = pd.DataFrame(rows, columns=["段", "版本", "格", "cell", "H", "g", "情況", "窗", "F4飆股數", "涵蓋率", "對照一數", "對照一比例", "對照二數", "對照二比例"])
    with np.errstate(invalid="ignore", divide="ignore"):
        CL["倍數一"] = np.where(CL["對照一比例"] > 0, CL["涵蓋率"] / CL["對照一比例"], np.nan)
        CL["倍數二"] = np.where(CL["對照二比例"] > 0, CL["涵蓋率"] / CL["對照二比例"], np.nan)
    CL.to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.10g")
    grid = []
    for (seg, ver, k, w), x in CL.groupby(["段", "版本", "情況", "窗"], sort=False):
        x1 = x[x["F4飆股數"] >= 1]; r1 = x1["倍數一"].dropna(); r2 = x1["倍數二"].dropna()
        grid.append({"段": seg, "版本": ver, "情況": k, "窗": w, "窗名": WNAME[w], "類": CAT[LAB[k][0]], "說明": LAB[k][1], "格數": len(x1),
                     "涵蓋率中位": x1["涵蓋率"].median(), "p10": x1["涵蓋率"].quantile(0.1), "p90": x1["涵蓋率"].quantile(0.9),
                     "對照一中位": x1["對照一比例"].median(), "對照二中位": x1["對照二比例"].median(),
                     "倍數一中位": r1.median() if len(r1) else np.nan, "倍數二中位": r2.median() if len(r2) else np.nan,
                     "倍數二 p10": r2.quantile(0.1) if len(r2) else np.nan, "倍數二 p90": r2.quantile(0.9) if len(r2) else np.nan,
                     "F4飆股數 各格加總": int(x["F4飆股數"].sum())})
    GR = pd.DataFrame(grid)
    GR["對照組也差不多"] = GR["倍數二中位"].between(0.8, 1.25)
    GR["不帶F4飆股也差不多"] = GR["倍數一中位"].between(0.8, 1.25)
    GR.to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    # 件數與窗長
    cnts = {}
    for seg, (a_, b_) in SEGS.items():
        eF = (mon_t[evF] >= a_) & (mon_t[evF] <= b_)
        for ver in VERS:
            mF = eF & (elev[evF] if ver != "全部" else True)
            sid_ = usid[evF][mF]; dd_ = d[evF][mF]
            cnts[f"{seg}｜{ver}"] = {"F4飆股（各格加總）": int(mF.sum()), "不同 (股, 起漲日)": len(set(zip(sid_.tolist(), dd_.tolist()))),
                                    "不同股票": len(set(sid_.tolist())), "有 ≥1 F4 飆股的格": int(len(set(cell[evF][mF].tolist())))}
    dur = pd.Series(P[evF] - d[evF]).groupby(cell[evF]).median()
    SM = {"讀法寫死": TAGT, "執行": now_tpe() + "（台北）",
          "資料": {"旗": "~/minework/flags_main.npz", "主快照": RM.MAIN_SHA, "news": NEWS_SHA, "漲停": "stitch_950ad26e12_b53f5540a8", "融資": "surge_b53f5540a8ad",
                 "月營收": "revenue_hist @796d94c9da", "s5": "~/s5work"},
          "閘門": {"F4飆股＝researchMineF4": True, "對照二定義域 不同": gate_bad, "漲停 lu_20": info["漲停閘門"]},
          "資料計數": {k: v for k, v in info.items() if k != "漲停閘門"}, "件數": cnts,
          "對照二": {"rows.npz 列": int(nr), "(m, m_next] 無 K 棒（不進對照二）": nobar, "有 F4 飆股的格": nctl_cells},
          "起漲到頂點交易日數（各格中位的網格中位，合併全部）": float(dur.median()), "p10": float(dur.quantile(0.1)), "p90": float(dur.quantile(0.9))}
    json.dump(SM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("===== 本體完成 =====")
    page()


# ═════════════ 網頁 ═════════════
def pc(x, d=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:.{d}f}%"


def rt(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x:.2f}"


def note(r):
    o = []
    if r["對照組也差不多"]:
        o.append("對照組也差不多")
    if r["不帶F4飆股也差不多"]:
        o.append("不帶 F4 的飆股也差不多")
    return "；".join(o)


def page():
    from backtest.researchMine_page import CSS
    GR = pd.read_csv(os.path.join(OUT, "grid.csv")); SM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    g = GR.set_index(["段", "版本", "情況", "窗"])
    A = GR[(GR["段"] == "合併") & (GR["版本"] == "全部")]
    c_all = SM["件數"]["合併｜全部"]; c_w1 = SM["件數"]["合併｜W1 母體內"]

    def G_(k, w, seg="合併", ver="全部"):
        return g.loc[(seg, ver, k, w)]

    def cv(k, w, seg="合併", ver="全部", bold=True):
        r = G_(k, w, seg, ver)
        v = pc(r["涵蓋率中位"])
        return f"<b>{v}</b>" if bold else v
    css = CSS.replace("max-width:820px", "max-width:960px") + "<style>td small{color:var(--note)}.k{font-size:.8em;color:var(--note)}</style>"
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>連續虧損飆股為什麼漲</title>", css, "</head><body>",
         "<h1>連續虧損（F4）的股票變成飆股，起漲前後到頂點發生了什麼？</h1>",
         f"<p class='note'>使用者原話：「F4在變飆股的過程中，是因為業績有變好，轉型成功還是什麼原因開始漲的？」｜接續「連續虧損股的飆股特徵」（起漲當下的情況）｜"
         f"這次看起漲前 60 日、起漲到頂點、頂點後 60 日發生的事｜只描述（參考、不計檢定數、不需登錄）｜回測線執行，讀法寫死 {html.escape(TAGT)}。"
         "這是歷史統計，不是對任何一檔的預測或買賣建議。</p>"]
    # ── 結論
    H.append("<div class='box'><b>結論（2017-03～2026-08，全部上市櫃；每個比例 ＝ 250 種飆股定義各算一次取中位）</b><ul>")
    H.append(f"<li>對象：起漲前一個月底帶 F4 連續虧損的飆股，{c_all['不同股票']} 檔股票、{c_all['不同 (股, 起漲日)']:,} 個起漲點。"
             "對照一 ＝ 同期不帶 F4 的飆股；對照二 ＝ 同期帶 F4 但沒變飆股的股票（隨機挑一天當假起漲日、窗長跟 F4 飆股一樣）。</li>")
    # 白話總結（由數字組句，不寫死數字）
    band = lambda k, w: 0.8 <= float(G_(k, w)["倍數二中位"]) <= 1.25
    pre_same = [nm for k, nm in (("A_any", "業績變好（寬）"), ("A_str", "業績明顯變好（嚴）"), ("B_any", "轉型類公告"), ("C_any", "題材類公告")) if band(k, "pre")]
    lead = []
    if pre_same:
        lead.append(f"起漲前 60 日，{('、'.join(pre_same))}的比例跟同期沒變飆股的 F4 股差不多（倍數二 0.8～1.25）——起漲前看不出它們比較特別")
    lead.append(f"差別主要出在起漲之後到頂點這段：業績明顯變好（嚴） {cv('A_str', 'run')} 對 {pc(G_('A_str', 'run')['對照二中位'])}、"
                f"月營收創 24 個月新高 {cv('rv_h24', 'run')} 對 {pc(G_('rv_h24', 'run')['對照二中位'])}、季報由虧轉盈（比去年同季） {cv('eq_turn4', 'run')} 對 {pc(G_('eq_turn4', 'run')['對照二中位'])}"
                f"；轉型類公告 {cv('B_any', 'run')} 對 {pc(G_('B_any', 'run')['對照二中位'])}（其中主旨含私募 {cv('kw_pp', 'run', bold=False)} 對 {pc(G_('kw_pp', 'run')['對照二中位'])}）")
    lead.append(f"頂點前「業績、轉型、題材都沒有」的只有 {cv('none123', 'prepk')}——幾乎每一檔在漲的過程中都有業績變好或公告；但沒變飆股的 F4 股同樣長的期間也幾乎都有（{pc(G_('none123', 'prepk')['對照二中位'])} 沒有），所以「有」本身說明不了為什麼漲")
    H.append("<li><b>白話</b>：" + "。".join(lead) + "。</li>")
    summ = [("A_any", "業績有變好（寬）"), ("A_str", "業績明顯變好（嚴）"), ("B_any", "轉型／經營權類公告（代理）"), ("C_any", "訂單／題材類公告"),
            ("D_any", "炒作／籌碼（注意股、處置、漲停）")]
    for k, nm in summ:
        H.append(f"<li><b>{nm}</b>：起漲前 60 日 {cv(k, 'pre')}（對照二 {pc(G_(k, 'pre')['對照二中位'])}）→ 起漲到頂點 {cv(k, 'run')}"
                 f"（對照二 {pc(G_(k, 'run')['對照二中位'])}、對照一 {pc(G_(k, 'run')['對照一中位'])}）→ 頂點後 60 日 {cv(k, 'post', bold=False)}。</li>")
    r = G_("grp", "t20")
    H.append(f"<li><b>族群一起漲</b>（同產業別檔在起漲日前後 20 日內也起漲；產業現值，後見）：{cv('grp', 't20')}（對照一 {pc(r['對照一中位'])}、對照二 {pc(r['對照二中位'])}）。</li>")
    H.append(f"<li><b>頂點前（起漲前 60 日到頂點）什麼都沒有</b>：1～3 類（業績變好、轉型類、題材類）都沒有 {cv('none123', 'prepk')}"
             f"（其中只有炒作／籌碼 {cv('only4', 'prepk', bold=False)}、完全沒事 {cv('none1234', 'prepk', bold=False)}）；"
             f"頂點前公布的業績都沒變好（寬） {cv('A_none', 'prepk')}、沒有明顯變好（嚴） {cv('A_nonestr', 'prepk')}。</li>")
    fw = ", ".join(f"{nm} {cv(f'fw_{k}', 'prepk', bold=False)}" for k, nm in FIRST)
    H.append(f"<li><b>最先發生的是哪一類</b>（頂點前合併窗、依生效日；業績用寬版）：{fw}。</li>")
    # 補充：倍數
    run = A[(A["窗"] == "run") & A["類"].isin([CAT[i] for i in (1, 2, 3, 4, 7)])]
    up = run[run["倍數二中位"] >= 1.5].sort_values("倍數二中位", ascending=False)
    if len(up):
        H.append("<li><b>補充：起漲到頂點這段，比沒變飆股的 F4 股明顯常見的</b>（倍數二 ≥ 1.5；括號 ＝ 涵蓋率、倍數二）：" + "；".join(
            f"{html.escape(x['說明'])}（{pc(x['涵蓋率中位'])}、{rt(x['倍數二中位'])} 倍）" for _, x in up.iterrows()) + "。</li>")
    pre = A[(A["窗"] == "pre") & A["類"].isin([CAT[i] for i in (1, 2, 3, 4, 7)])]
    up2 = pre[pre["倍數二中位"] >= 1.5].sort_values("倍數二中位", ascending=False)
    if len(up2):
        H.append("<li><b>補充：起漲前 60 日，比沒變飆股的 F4 股明顯常見的</b>（倍數二 ≥ 1.5）：" + "；".join(
            f"{html.escape(x['說明'])}（{pc(x['涵蓋率中位'])}、{rt(x['倍數二中位'])} 倍）" for _, x in up2.iterrows()) + "。</li>")
    H.append("<li>⚠「轉型」只能用公告代理：有發經營權、併購、增資、更名之類的公告，不代表轉型成功，也不代表股價是因為它漲。"
             "「起漲到頂點」這段本身就是漲的期間，漲停、注意股、處置多半是上漲的結果而不是原因。</li>")
    H.append("<li>「倍數」只是補充，全部項目都列在下面的表，沒有挑；標「對照組也差不多」＝ 沒變飆股的 F4 股在同樣長的期間也差不多常有（倍數二 0.8～1.25）。</li>")
    H.append("</ul></div>")
    # ── 各窗主表
    nsec = ["一", "二", "三", "四"]
    for si, w in enumerate(WINS):
        T = A[(A["窗"] == w) & (A["類"] != CAT[8])].copy()
        if w == "run":
            T = pd.concat([T, A[A["窗"] == "t20"]])
        T = T.sort_values(["涵蓋率中位", "p90"], ascending=False)
        H.append(f"<h2>{nsec[si]}、{WNAME[w]}（依涵蓋率高到低；全部上市櫃、2017-03～2026-08）</h2>")
        if w == "post":
            H.append(f"<p class='note'>頂點後 60 日只給參考；頂點在資料尾附近的會被截掉（F4 飆股被截比例中位 {pc(G_('trunc', 'post')['涵蓋率中位'], 1)}）。</p>")
        if w == "run":
            H.append("<p class='note'>「族群一起漲」一列是起漲日前後 20 個交易日，不是起漲到頂點。</p>")
        hd = ["情況", "類", "涵蓋率", "對照一：不帶 F4 的飆股", "對照二：沒變飆股的 F4 股", "倍數一", "倍數二", "註"]
        H.append("<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i < 2 else ''}>{x}</th>" for i, x in enumerate(hd)) + "</tr>")
        for _, x in T.iterrows():
            if x["情況"] == "trunc":
                continue
            H.append(f"<tr><td class=l>{html.escape(x['說明'])}</td><td class='l k'>{html.escape(x['類'][2:])}</td>"
                     f"<td><b>{pc(x['涵蓋率中位'])}</b> <small>{pc(x['p10'])}～{pc(x['p90'])}</small></td><td>{pc(x['對照一中位'])}</td><td>{pc(x['對照二中位'])}</td>"
                     f"<td>{rt(x['倍數一中位'])}</td><td>{rt(x['倍數二中位'])}</td><td class=l>{note(x)}</td></tr>")
        H.append("</table></div>")
    # ── 最先發生
    H.append("<h2>五、最先發生的是哪一類（起漲前 60 日到頂點；依公告生效日）</h2>")
    H.append("<div class='wrap'><table><tr><th class=l>最先發生</th><th>業績用寬版</th><th>對照一</th><th>對照二</th><th>業績用嚴版</th><th>對照一</th><th>對照二</th></tr>")
    for k, nm in FIRST:
        a1 = G_(f"fw_{k}", "prepk"); a2 = G_(f"fs_{k}", "prepk")
        H.append(f"<tr><td class=l>{nm}</td><td><b>{pc(a1['涵蓋率中位'])}</b></td><td>{pc(a1['對照一中位'])}</td><td>{pc(a1['對照二中位'])}</td>"
                 f"<td><b>{pc(a2['涵蓋率中位'])}</b></td><td>{pc(a2['對照一中位'])}</td><td>{pc(a2['對照二中位'])}</td></tr>")
    H.append("</table></div><p class='note'>各列是各格中位，加起來不一定剛好 100%。月營收每月都會公布，所以寬版業績天生容易最早出現；嚴版只算由虧轉盈、年增 ＞ 50%、創 24 個月新高。"
             "漲停、融資不是公告，不排。</p>")
    # ── 兩段
    H.append("<h2>六、兩段比較（全部上市櫃；各原因「任一」與「什麼都沒有」）</h2>")
    keys = [("A_any", "業績有變好（寬）"), ("A_str", "業績明顯變好（嚴）"), ("B_any", "轉型／經營權類（代理）"), ("C_any", "訂單／題材類"), ("D_any", "炒作／籌碼類"),
            ("none123", "1～3 類都沒有")]
    H.append("<div class='wrap'><table><tr><th class=l>情況</th><th class=l>窗</th><th>2017-03～2021</th><th>2022～2026-08</th><th>差（點）</th><th>合併</th><th>合併 對照二</th></tr>")
    sd = []
    for k, nm in keys + [("grp", "族群一起漲")]:
        for w in (WINS if k != "grp" else ("t20",)):
            e1 = G_(k, w, "探索")["涵蓋率中位"]; e2 = G_(k, w, "確認")["涵蓋率中位"]
            dfx = (e2 - e1) * 100 if np.isfinite(e1) and np.isfinite(e2) else np.nan
            H.append(f"<tr><td class=l>{nm}</td><td class=l>{WNAME[w]}</td><td>{pc(e1)}</td><td>{pc(e2)}</td><td>{'—' if not np.isfinite(dfx) else f'{dfx:+.0f}'}</td>"
                     f"<td>{pc(G_(k, w)['涵蓋率中位'])}</td><td>{pc(G_(k, w)['對照二中位'])}</td></tr>")
    H.append("</table></div>")
    for w in WINS + ("t20",):
        T = A[(A["窗"] == w)]
        for _, x in T.iterrows():
            e1 = G_(x["情況"], w, "探索")["涵蓋率中位"]; e2 = G_(x["情況"], w, "確認")["涵蓋率中位"]
            if np.isfinite(e1) and np.isfinite(e2) and abs(e2 - e1) >= 0.10 and x["情況"] != "trunc":
                sd.append((e2 - e1, x["說明"], WNAME[w], e1, e2))
    if sd:
        sd.sort()
        H.append("<p class='note'>全部項目裡兩段差 10 個百分點以上的（2017-03～2021 → 2022～2026-08）：" + "；".join(
            f"{html.escape(nm_)}〔{wn}〕{pc(a_)} → {pc(b_)}" for _, nm_, wn, a_, b_ in sd) + "。</p>")
    c1 = SM["件數"]["探索｜全部"]; c2 = SM["件數"]["確認｜全部"]
    H.append(f"<p class='note'>F4 飆股：2017-03～2021 {c1['不同股票']} 檔／{c1['不同 (股, 起漲日)']:,} 個起漲點；2022～2026-08 {c2['不同股票']} 檔／{c2['不同 (股, 起漲日)']:,} 個起漲點。</p>")
    # ── W1
    H.append(f"<h2>七、只看 W1 母體內（營量／營飆能買的股票）</h2><p class='note'>起漲前一個月底在 W1 母體內的 F4 飆股：{c_w1['不同股票']} 檔、{c_w1['不同 (股, 起漲日)']:,} 個起漲點、"
             f"有 ≥ 1 筆的格 {c_w1['有 ≥1 F4 飆股的格']} 格；對照一、二也只取 W1 母體內。</p>")
    H.append("<div class='wrap'><table><tr><th class=l>情況</th><th class=l>窗</th><th>W1 涵蓋率</th><th>W1 對照一</th><th>W1 對照二</th><th>全部上市櫃版</th></tr>")
    for k, nm in keys + [("grp", "族群一起漲")] + [(f"fw_{k}", f"最先發生：{nm}") for k, nm in FIRST]:
        for w in ((WINS if k != "grp" else ("t20",)) if not k.startswith("fw_") else ("prepk",)):
            x = G_(k, w, ver="W1 母體內")
            H.append(f"<tr><td class=l>{nm}</td><td class=l>{WNAME[w]}</td><td><b>{pc(x['涵蓋率中位'])}</b> <small>{pc(x['p10'])}～{pc(x['p90'])}</small></td>"
                     f"<td>{pc(x['對照一中位'])}</td><td>{pc(x['對照二中位'])}</td><td>{pc(G_(k, w)['涵蓋率中位'])}</td></tr>")
    H.append("</table></div><p class='note'>W1 版各細項的完整表見 grid.csv（版本 ＝ W1 母體內）。</p>")
    # ── 讀法
    H.append("<h2>八、怎麼算的、限制</h2><ul class='note'>"
             "<li>飆股 ＝ 飆股回推 seq6 網格的 250 種定義（持有天數上限 × 漲幅門檻），s5 全日曆名單，起漲日加持有天數上限在 2026-08-31 以前；頂點 ＝ 該定義下起漲後最高收盤那天。"
             "每個數字是 250 格各算一次的中位（只算有 F4 飆股的格），小字 p10～p90。同一檔在不同格會重複出現，每格各算比例再取中位。</li>"
             "<li>F4 連續虧損 ＝ 起漲日前最後一個月底，最近 4 季 EPS 合計虧且最近一季虧，或最近 8 季有 6 季以上虧（當時已公布的財報）。事件、F4 判定與「連續虧損股的飆股特徵」逐筆相同。</li>"
             "<li>「窗內發生」看生效日：重大訊息 13:30 前公告算當天、否則算下一個交易日；季報用上傳時戳的下一個交易日（沒有時戳用法定期限＋5 個交易日）；"
             "月營收用次月 10 日（2026 年起 15 日）之後第一個交易日——⚠ 這是法定期限代理，很多公司會更早公布。</li>"
             "<li>⚠ 轉型只能代理：用重大訊息的分類（經理人異動、併購、增資、取得處分資產、減資）和主旨關鍵字（經營權、改選、補選、董事＋選任、私募、更名、營業項目、轉型、新事業、跨足、入股、策略聯盟）。"
             "有公告 ≠ 轉型成功；關鍵字也會抓到不相干的公告（例：例行的董事選任），所以一定要看對照組。</li>"
             "<li>對照二的假起漲日是同一個月隨機一天（種子寫死），假頂點 ＝ 假起漲日加上從同一格 F4 飆股抽出的「起漲到頂點」天數，所以窗長分佈一樣。</li>"
             "<li>族群用今天的產業分類套回過去（後見）；漲停、注意股、處置在「起漲到頂點」這段多半是上漲的結果。</li>"
             f"<li>起漲到頂點的窗長：各格中位的網格中位 {SM['起漲到頂點交易日數（各格中位的網格中位，合併全部）']:.0f} 個交易日（p10～p90 {SM['p10']:.0f}～{SM['p90']:.0f}）。</li>"
             "<li>只描述：窗延伸到頂點，用到起漲後才知道的事，⛔ 不能拿來當事前訊號；不計檢定數、不判定。</li></ul>")
    if CK:
        H.append(f"<p class='note'>抽樣查核（獨立寫法重算 2 格的三組比例）：{'0 不同，過' if CK.get('過') else '有不同，見 check.json'}。</p>")
    H.append(f"<p class='note'>閘門：F4 飆股與「連續虧損股的飆股特徵」逐筆相同；對照二定義域逐格同該件；漲停重算與 s5 lu_20 逐一相同。檔案：backtest/resultsMine/F4why/。</p>")
    H.append("</body></html>")
    open(os.path.join(OUT, "連續虧損飆股為什麼漲.html"), "w", encoding="utf-8").write("\n".join(H))


# ═════════════ 查核（獨立寫法）═════════════
def check():
    """⛔ 不呼叫本檔本體、researchMine、researchMineF4 的函式；只讀原始 CSV、s5 原表、flags_main.npz、rows.npz、本體輸出。"""
    T0 = time.time()
    rng = np.random.default_rng(20261008)
    hs = tuple(range(10, 251, 10)); gs = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
    cname = lambda c: f"H{hs[c // 10]}_g{int(round(gs[c % 10] * 100))}%"
    res = {"時間": now_tpe() + "（台北）", "種子": 20261008}
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz"))
    mainp = os.path.expanduser("~/h2data/mine_796d94c9dafd/data"); s5w = os.path.expanduser("~/s5work")
    z = np.load(os.path.expanduser("~/minework/flags_main.npz"))
    sids = [str(x) for x in z["sids"]]; jx = {x: j for j, x in enumerate(sids)}; me = pd.to_datetime(pd.Series(z["me"]))
    calm = pd.to_datetime(pd.read_csv(os.path.join(mainp, "meta", "calendar_twse.csv"))["date"]).sort_values().reset_index(drop=True)
    c1 = pd.read_csv(os.path.expanduser("~/earlydata/3edc0e2206/main/data/meta/calendar_twse.csv"))["date"]
    c2 = pd.read_csv(os.path.join(mainp, "meta", "calendar_twse.csv"))["date"]
    cal5 = pd.to_datetime(pd.concat([c1, c2[c2 <= "2026-09-24"]], ignore_index=True)).reset_index(drop=True)
    N5 = len(cal5); assert N5 == 5571
    c5s = [str(x.date()) for x in cal5]; d5 = {t: i for i, t in enumerate(c5s)}
    uni = pd.read_csv(os.path.join(s5w, "uni.csv"), dtype=str)
    U = uni["stock_id"].tolist(); ux = {x: i for i, x in enumerate(U)}
    E = np.load(os.path.join(s5w, "events.npz"))
    Ec, Ed, Es, EP = (E[k].astype(int) for k in ("cell", "d", "s", "P"))
    icut = d5["2026-08-31"]
    okE = Ed + np.array(hs)[Ec // 10] <= icut
    cand = CL[(CL["段"] == "合併") & (CL["版本"] == "全部") & (CL["情況"] == "A_any") & (CL["窗"] == "pre") & (CL["F4飆股數"] >= 30)]["cell"].to_numpy()
    pick = [int(x) for x in rng.choice(cand, 2, replace=False)]
    res["抽到的格"] = [cname(c) for c in pick]

    def day5(datestr):                                                        # 當天或之後第一個交易日
        return bisect.bisect_left(c5s, datestr)
    # ── 事件分組（自己做）
    groups = {}
    for c in pick:
        F4l, NFl = [], []
        for i in np.flatnonzero((Ec == c) & okE):
            t = cal5[Ed[i]]
            if not ("2017-03" <= str(t)[:7] <= "2026-08"):
                continue
            x = U[Es[i]]
            if x not in jx:
                continue
            im = int((me < t).sum()) - 1
            if im < 0:
                continue
            (F4l if bool(z["F4"][im, jx[x]]) else NFl).append((Es[i], Ed[i], EP[i]))
        groups[c] = (F4l, NFl)
    need = set()
    for c in pick:
        for L_ in groups[c]:
            need |= {a for a, _, _ in L_}
    RW = np.load(os.path.expanduser("~/minework/F4/rows.npz"))
    need |= set(RW["rs5"].astype(int).tolist())
    needx = {U[i] for i in need}
    # ── 每檔事件日清單（自己讀）
    EVD = {}                                                                 # (s5, 型) → 排序日清單

    def put(si, ty, dd):
        if 0 <= dd < N5:
            EVD.setdefault((si, ty), []).append(dd)
    # 季報
    fh = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "eps_q", "eps_ytd"]) for f in sorted(glob.glob(os.path.join(mainp, "mops", "fin_hist", "*.csv")))])
    fh = fh.drop_duplicates(["stock_id", "period"], keep="last")
    fd = pd.read_csv(os.path.join(mainp, "meta", "filing_dates.csv"), dtype=str)
    fd["dd"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce"); fd = fd.dropna(subset=["dd"])
    up = fd.groupby(["stock_id", "year", "season"])["dd"].min()
    up.index = [(a_, int(b_), int(c_)) for a_, b_, c_ in up.index]; up = up.to_dict()
    calv = calm.values
    for x, gg in fh.groupby("stock_id"):
        if x not in needx:
            continue
        si = ux[x]
        ytd = {pd.Period(p, "Q"): v for p, v in zip(gg["period"], pd.to_numeric(gg["eps_ytd"], errors="coerce"))}
        qq = {pd.Period(p, "Q"): v for p, v in zip(gg["period"], pd.to_numeric(gg["eps_q"], errors="coerce"))}
        ee = {}
        for P_, v in ytd.items():
            e = v if P_.quarter == 1 else (v - ytd[P_ - 1] if (P_ - 1) in ytd and np.isfinite(v) and np.isfinite(ytd[P_ - 1]) else np.nan)
            if not np.isfinite(e) and np.isfinite(qq.get(P_, np.nan)):
                e = qq[P_]
            ee[P_] = e
        for P_, e0 in ee.items():
            ts = up.get((x, P_.year, P_.quarter))
            if ts is not None:
                k = int(np.searchsorted(calv, np.datetime64(ts), side="right"))
            else:
                dl = pd.Timestamp(P_.year + 1, 3, 31) if P_.quarter == 4 else pd.Timestamp(P_.year, *{1: (5, 15), 2: (8, 14), 3: (11, 14)}[P_.quarter])
                k = int(np.searchsorted(calv, np.datetime64(dl), side="right")) + 5
            if k >= len(calm):
                continue
            ds = str(calm.iloc[k].date())
            if ds not in d5:
                continue
            dd = d5[ds]; e1 = ee.get(P_ - 1, np.nan); e4 = ee.get(P_ - 4, np.nan)
            put(si, "eq_any", dd)
            if e0 > e1: put(si, "eq_qoq", dd)
            if e0 > e4: put(si, "eq_yoy", dd)
            if e1 < 0 < e0: put(si, "eq_turn1", dd)
            if e4 < 0 < e0: put(si, "eq_turn4", dd)
            if e0 > 0: put(si, "eq_pos", dd)
    # 月營收
    revd = os.path.expanduser("~/h2data/indrev_796d94c9dafd/data/mops/revenue_hist")
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in sorted(glob.glob(os.path.join(revd, "*.csv")))])
    rv["stock_id"] = rv["stock_id"].str.strip(); rv = rv.drop_duplicates(["stock_id", "period"], keep="last")
    for x, gg in rv.groupby("stock_id"):
        if x not in needx:
            continue
        si = ux[x]
        R_ = dict(zip(gg["period"], pd.to_numeric(gg["當月營收"], errors="coerce")))
        val = lambda P_: R_.get(str(P_), np.nan)
        for p, v in R_.items():
            if not np.isfinite(v):
                continue
            P_ = pd.Period(p, "M"); Q_ = P_ + 1
            cut = pd.Timestamp(Q_.year, Q_.month, 10 if p <= "2025-12" else 15)
            k = int(np.searchsorted(calv, np.datetime64(cut), side="right"))
            if k >= len(calm):
                continue
            ds = str(calm.iloc[k].date())
            if ds not in d5:
                continue
            dd = d5[ds]
            g12 = val(P_ - 12); y = v / g12 - 1 if (np.isfinite(g12) and g12 > 0) else np.nan
            hh = {}
            for L_, mn in ((12, 9), (24, 18)):
                pv = [val(P_ - k_) for k_ in range(1, L_ + 1)]; pv = [w_ for w_ in pv if np.isfinite(w_)]
                hh[L_] = len(pv) >= mn and v >= max(pv)
            st = 0; Q2 = P_
            while True:
                a_, b_ = val(Q2), val(Q2 - 12)
                if np.isfinite(a_) and np.isfinite(b_) and b_ > 0 and a_ / b_ - 1 > 0:
                    st += 1; Q2 = Q2 - 1
                else:
                    break
            put(si, "rv_any", dd)
            if y > 0: put(si, "rv_y0", dd)
            if y > 0.2: put(si, "rv_y20", dd)
            if y > 0.5: put(si, "rv_y50", dd)
            if hh[12]: put(si, "rv_h12", dd)
            if hh[24]: put(si, "rv_h24", dd)
            if st >= 3: put(si, "rv_s3", dd)
            if st >= 6: put(si, "rv_s6", dd)
    # 重大訊息
    src = open("backtest/researchNewsCat.py", encoding="utf-8").read()
    i0 = src.index("SEQ2_SRC = '''") + len("SEQ2_SRC = '''"); i1 = src.index("'''", i0)
    ns: dict = {}; exec(src[i0:i1], ns); clf = ns["classify"]
    nd_ = os.path.expanduser("~/msdata/8425186bd20cdef4d39ac039ad2a6eda0903a8bb/data/mops/news")
    seen = set()
    kwf = {"kw_board": lambda s_: ("經營權" in s_) or ("改選" in s_) or ("補選" in s_) or ("董事" in s_ and "選任" in s_),
           "kw_pp": lambda s_: "私募" in s_, "kw_rename": lambda s_: ("更名" in s_) or ("名稱變更" in s_) or ("變更公司名稱" in s_),
           "kw_biz": lambda s_: "營業項目" in s_, "kw_trans": lambda s_: ("轉型" in s_) or ("新事業" in s_) or ("跨足" in s_),
           "kw_ally": lambda s_: ("入股" in s_) or ("策略聯盟" in s_)}
    c5set = set(c5s)
    for y in range(2016, 2027):
        Nn = pd.read_csv(os.path.join(nd_, f"{y}.csv"), dtype=str, keep_default_na=False)
        for dt, tm, x, mk, se, sj in zip(Nn["date"], Nn["time"], Nn["stock_id"], Nn["market"], Nn["serial"], Nn["subject"]):
            kk = (dt, tm, x, se)
            if kk in seen:
                continue
            seen.add(kk)
            x = x.strip()
            if mk not in ("sii", "otc") or x not in needx:
                continue
            k = day5(dt)
            if dt in c5set and tm[:5] > "13:30":
                k += 1
            if k >= N5:
                continue
            si = ux[x]
            put(si, f"n{clf(sj)}", k); put(si, "nw_any", k)
            for kn, f in kwf.items():
                if f(sj):
                    put(si, kn, k)
    # 注意、處置
    at = pd.read_csv(os.path.join(mainp, "meta", "attention.csv"), dtype=str, usecols=["stock_id", "date"]).dropna()
    for x, dt in set(zip(at["stock_id"].str.strip(), at["date"])):
        if x in needx:
            put(ux[x], "att", day5(dt))
    dp = pd.read_csv(os.path.join(mainp, "meta", "disposal.csv"), dtype=str, usecols=["stock_id", "start_date"]).dropna()
    for x, dt in set(zip(dp["stock_id"].str.strip(), dp["start_date"])):
        if x in needx:
            put(ux[x], "disp", day5(dt))
    # 漲停（自寫 tick）
    bar5 = np.load(os.path.join(s5w, "bar.npy"), mmap_mode="r")
    st_ = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")

    def tick(p):
        return 0.01 if p < 10 else 0.05 if p < 50 else 0.1 if p < 100 else 0.5 if p < 500 else 1.0 if p < 1000 else 5.0
    for si in sorted(need):
        x = U[si]; pth = os.path.join(st_, "stocks", x + ".csv")
        if not os.path.exists(pth):
            continue
        raw = pd.read_csv(pth, dtype=str, usecols=["date", "close"]).drop_duplicates("date")
        rc = dict(zip(raw["date"], pd.to_numeric(raw["close"], errors="coerce")))
        bars = np.flatnonzero(np.asarray(bar5[si]))
        if len(bars) < 2:
            continue
        evd = set()
        bds = [c5s[b] for b in bars]
        pa = os.path.join(st_, "adj", x + ".csv")
        if os.path.exists(pa):
            for dt in pd.read_csv(pa, dtype=str)["date"]:
                k = bisect.bisect_left(bds, str(dt)[:10])
                if k < len(bars):
                    evd.add(k)
        first5 = c5s[bars[0]] > "2015-01-12"
        for k in range(1, len(bars)):
            if k in evd or (first5 and k < 5):
                continue
            a_ = rc.get(c5s[bars[k - 1]], np.nan); b_ = rc.get(c5s[bars[k]], np.nan)
            if not (np.isfinite(a_) and np.isfinite(b_) and a_ > 0 and b_ > 0):
                continue
            lim = 0.07 if c5s[bars[k]] < "2015-06-01" else 0.10
            rw = a_ * (1 + lim); tk = tick(rw); lp = np.floor(rw / tk + 1e-9) * tk
            if abs(b_ - lp) < 1e-6:
                put(si, "lu", int(bars[k]))
    for k in EVD:
        EVD[k].sort()
    # 融資（自己沿用）
    MBd = {}
    mgd = os.path.expanduser("~/h2data/surge_b53f5540a8ad/data/stocks_margin")
    for si in need:
        pth = os.path.join(mgd, U[si] + ".csv")
        if not os.path.exists(pth):
            continue
        mg = pd.read_csv(pth, dtype=str, usecols=["date", "m_balance"])
        dd_ = {}
        for dt, v in zip(mg["date"], pd.to_numeric(mg["m_balance"], errors="coerce")):
            dd_[dt] = v                                                       # 同日多列取最後
        arr = np.full(N5, np.nan); cur = np.nan
        for i, ds in enumerate(c5s):
            if ds in dd_ and np.isfinite(dd_[ds]):
                cur = dd_[ds]
            arr[i] = cur
        MBd[si] = arr
    # 產業
    ind = pd.read_csv(os.path.join(mainp, "meta", "industry.csv"), dtype=str)
    IND = {a_.strip(): (b_.strip() if isinstance(b_, str) else "") for a_, b_ in zip(ind["stock_id"], ind["industry_name"])}

    def cnt(si, ty, a_, b_):
        L_ = EVD.get((si, ty))
        if not L_ or a_ > b_:
            return 0
        return bisect.bisect_right(L_, b_) - bisect.bisect_left(L_, a_)

    def first(si, tys, a_, b_):
        best = None
        for ty in tys:
            L_ = EVD.get((si, ty))
            if not L_ or a_ > b_:
                continue
            i = bisect.bisect_left(L_, a_)
            if i < len(L_) and L_[i] <= b_:
                best = L_[i] if best is None else min(best, L_[i])
        return best
    GA = ["eq_qoq", "eq_yoy", "rv_y0"]; GAs = ["eq_turn1", "eq_turn4", "rv_y50", "rv_h24"]
    GB = ["n10", "n4", "n5", "n7", "n3", "kw_board", "kw_pp", "kw_rename", "kw_biz", "kw_trans", "kw_ally"]; GC = ["n6", "n11", "n2"]

    def items(si, t, P):
        o = {}
        last = N5 - 1
        for w, (a_, b_), (m0, m1) in (("pre", (t - 60, t - 1), (t - 61, t - 1)), ("run", (t, P), (t - 1, P)),
                                       ("post", (P + 1, min(P + 60, last)), (P, min(P + 60, last))), ("prepk", (t - 60, P), (t - 61, P))):
            h = lambda ty: cnt(si, ty, a_, b_) > 0
            A_ = any(h(k) for k in GA); As_ = any(h(k) for k in GAs); B_ = any(h(k) for k in GB); C_ = any(h(k) for k in GC)
            na, nl = cnt(si, "att", a_, b_), cnt(si, "lu", a_, b_); dsp = cnt(si, "disp", a_, b_) > 0
            Dx = na > 0 or dsp or nl > 0
            mb = MBd.get(si)
            r = np.nan
            if mb is not None:
                x0, x1 = mb[m0], mb[m1]
                if np.isfinite(x0) and x0 > 0 and np.isfinite(x1):
                    r = x1 / x0 - 1
            for k in ("eq_qoq", "eq_yoy", "eq_turn1", "eq_turn4", "eq_pos", "rv_y0", "rv_y20", "rv_y50", "rv_h12", "rv_h24", "rv_s3", "rv_s6", "n9",
                      "n10", "kw_board", "n4", "n5", "kw_pp", "n7", "n3", "kw_rename", "kw_biz", "kw_trans", "kw_ally", "n6", "n11", "n2", "n1", "n8", "n12", "nw_any"):
                o[(k, w)] = h(k)
            o.update({("A_any", w): A_, ("A_str", w): As_, ("A_none", w): not A_, ("A_nonestr", w): not As_, ("B_any", w): B_, ("C_any", w): C_,
                      ("att1", w): na >= 1, ("att3", w): na >= 3, ("disp1", w): dsp, ("lu1", w): nl >= 1, ("lu3", w): nl >= 3, ("lu5", w): nl >= 5,
                      ("mg0", w): bool(r > 0), ("mg50", w): bool(r >= 0.5), ("D_any", w): Dx,
                      ("none123", w): not (A_ or B_ or C_), ("only4", w): (not (A_ or B_ or C_)) and Dx, ("none1234", w): not (A_ or B_ or C_ or Dx)})
            if w == "prepk":
                for ver, ga in (("fw", GA), ("fs", GAs)):
                    fs_ = [first(si, ga, a_, b_), first(si, GB, a_, b_), first(si, GC, a_, b_), first(si, ["att", "disp"], a_, b_)]
                    vv = [f for f in fs_ if f is not None]
                    for k in ("A", "B", "C", "D", "tie", "none"):
                        o[(f"{ver}_{k}", "prepk")] = False
                    if not vv:
                        o[(f"{ver}_none", "prepk")] = True
                    else:
                        mn = min(vv); who = [i for i, f in enumerate(fs_) if f == mn]
                        if len(who) >= 2:
                            o[(f"{ver}_tie", "prepk")] = True
                        else:
                            o[(f"{ver}_{'ABCD'[who[0]]}", "prepk")] = True
        o[("trunc", "post")] = P + 60 > last
        return o

    CEV = {}
    for c in pick:
        ii = np.flatnonzero((Ec == c) & okE)
        o_ = np.argsort(Ed[ii], kind="stable")
        CEV[c] = (Ed[ii][o_].tolist(), Es[ii][o_].tolist())

    def grp(c, si, t):
        ig = IND.get(U[si], "")
        if not ig:
            return False
        cd, cs = CEV[c]
        for i in range(bisect.bisect_left(cd, t - 20), bisect.bisect_right(cd, t + 20)):
            if cs[i] != si and IND.get(U[cs[i]], "") == ig:
                return True
        return False
    errs = []
    # ── 對照二：自己算定義域與假起漲日
    R_i, R_j, rs5, rm5, rm5n = (RW[k].astype(int) for k in ("R_i", "R_j", "rs5", "rm5", "rm5n"))
    nr = len(R_i)
    r2 = np.random.default_rng(20261007); pt = np.full(nr, -1)
    for r in range(nr):
        dd = [x for x in range(rm5[r] + 1, rm5n[r] + 1) if bool(bar5[rs5[r], x])]
        if dd:
            pt[r] = dd[int(r2.integers(len(dd)))]
    CT = np.load(os.path.join(WORK, "control.npz"))
    res["假起漲日與本體相同"] = bool(np.array_equal(pt, CT["pt"]))
    if not res["假起漲日與本體相同"]:
        errs.append("假起漲日不同")
    hdef = np.load(os.path.join(s5w, "hdef.npy"), mmap_mode="r")
    out = []
    for c in pick:
        H = hs[c // 10]
        F4l, NFl = groups[c]
        pool = [P_ - t for _, t, P_ in F4l]
        L = np.array(pool)[np.random.default_rng([20261007, c]).integers(len(pool), size=nr)]
        evs = {}
        for i in np.flatnonzero((Ec == c) & okE):
            evs.setdefault(int(Es[i]), []).append(int(Ed[i]))
        ctl = []
        for r in range(nr):
            mon = c5s[rm5[r] + 1][:7]
            if not ("2017-03" <= mon <= "2026-08") or not bool(bar5[rs5[r], rm5[r]]) or int(hdef[rs5[r], rm5[r] + 1]) < H or rm5[r] + 1 + H > icut:
                continue
            if any(rm5[r] < q <= rm5n[r] for q in evs.get(int(rs5[r]), [])):
                continue
            if pt[r] < 0:
                continue
            ctl.append((int(rs5[r]), int(pt[r]), min(int(pt[r]) + int(L[r]), N5 - 1)))
        ref = CL[(CL["段"] == "合併") & (CL["版本"] == "全部") & (CL["cell"] == c)].set_index(["情況", "窗"])
        one = {}
        for nm, lst, cN, cP in (("F4", F4l, "F4飆股數", "涵蓋率"), ("對照一", NFl, "對照一數", "對照一比例"), ("對照二", ctl, "對照二數", "對照二比例")):
            rows = []
            for si, t, P_ in lst:
                o = items(si, t, P_); o[("grp", "t20")] = grp(c, si, t); rows.append(o)
            df = pd.DataFrame(rows)
            nb = 0
            for (k, w) in COLS:
                mine = float(df[(k, w)].mean()) if len(df) else np.nan
                rv_ = ref.loc[(k, w)]
                if int(rv_[cN]) != len(df) or not np.isclose(mine, rv_[cP], rtol=1e-9, atol=1e-12):
                    nb += 1; errs.append(f"{cname(c)} {nm} {k}|{w}：查核 {len(df)}／{mine}，本體 {int(rv_[cN])}／{rv_[cP]}")
            one[nm] = {"件數": len(df), "情況×窗": len(COLS), "不同": nb}
        out.append({"格": cname(c), **one})
    res["2 格三組比例"] = out
    res["錯誤（前 30）"] = errs[:30]; res["合計不同"] = len(errs); res["過"] = len(errs) == 0; res["秒"] = round(time.time() - T0)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    if a.check:
        return check()
    if a.stage == "body":
        body(a)
    else:
        page()


if __name__ == "__main__":
    main()

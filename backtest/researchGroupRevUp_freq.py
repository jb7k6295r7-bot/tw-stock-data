# -*- coding: utf-8 -*-
"""額外策略「營量 v1、營飆 v1 加『同族群營收也一起轉強』（只買版、優先版）」【頻率表・重疊度・等價檢查・乾跑】——回測線計算子代理，2026-11-10。
登錄：台股策略線 seq2（sha e72a759aefc7bfdc，6686 B；取代 seq1 8c0f6b403ebae89d）〈營量營飆加族群營收也轉強_只買版與優先版_組合層登錄〉
發號：裁定線 seq501 §三（N_組合 ＋4；最多「合格（暫定）」；優先版對原版買進重疊 ≥ 90% ⇒ 頻率表照報後先回信、正式標「等同原版」；
      優先版換掉的買進 ＜ 10% ⇒ 先回信；族群分群檔請產業提供，取不到照定義重建並報一致率；先交頻率表（含重疊度三項，⛔ 不附報酬））
族群定義：產業分析線 seq111（20261110-2008 件；定義全文在產業〈事前登錄_族群營收轉強能否讓營收新高訊號更準_20261110〉，本機取不到）

⛔ 乾跑：不讀、不算、不印任何報酬。引擎 research11.simulate_mtm 以「價格全為 1、毛報酬全為 0」跑（權益只隨成本下滑）⇒ 買進、持股、空槽是純構造量；
   ⛔ 日報酬相關係數需要報酬 ⇒ 本階段只報「算得出」。⛔ 不改策略鎖內任何檔（research11、rerun17、data… 只 import）；跑完 strategy_lock --check。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGroupRevUp_freq --step world --world main|early [--procs 3]
    … --step groups --world main|early [--procs 3]｜--step sim --world main|early [--procs 3]｜--step report
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchGroupRevUp_freq

═══ 讀法（寫死於 2026-11-10（台北），在算任何本件數字之前；★ ＝ 登錄沒寫清楚、執行者定；〔 〕＝ 另一讀法並報）═══
 F0 登錄驗證：信箱登錄全文去掉末行 pw1 戳記後 sha256 前 16 碼 ＝ e72a759aefc7bfdc、整檔 6686 B 才跑（不符即停）
 F1 兩策略原版 ＝ researchYL_integrate.eng 原式（＝ researchYLvsYF V1）：
    營量 v1 ＝ simulate_mtm(SIG[無閘], "H60", 20, default_rng(7000＋0), log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)，r＝0 一條
    營飆 v1 ＝ simulate_mtm(SIG[閘], "H120", 10, default_rng(1000＋r), stop_force=SF)，r ＝ 0～199（報中位、p10、p90 與 r0）
    世界 ＝ researchYL_integrate.main_world（T1 edc6f 快照；探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24）、
           early_world（上市＋上櫃 eotc_f65bb03e11、R8 截斷；早年 2005-02-01～2014-12-31，只描述）
    ★ 確認段尾 ＝ 該世界資料尾 2026-08-24（登錄「～資料尾」；正式跑若換新快照另報）
 F2 只買版 ＝ 候選表只留「族群營收轉強」列，其餘引擎參數同原版（不足額 ⇒ 空槽持現金；營飆照抽籤 200 顆、同種子）
    優先版 ＝ 候選照原表；名額不足時族群轉強者先進：
      營飆 ★ ＝ pick="prio"（族群轉強 1／否 0）＋ pick_tie="rng"：引擎每天照抽籤版抽同一次 permutation，依 prio 遞減穩定排序 ⇒ 同組內照抽籤先後
            （引擎註明「鍵全相同 ⇒ 與抽籤版逐位元相同」；本檔閘 G2 驗）
      營量 ★ ＝ pick 鍵 ＝ prio×10¹⁵ ＋ relvol（relvol 缺 ⇒ −10¹⁴，＝ 原版「NaN 排最後、同分照候選列序」）；閘 G2：prio 全 0 ⇒ 與原版逐筆相同
 F3 族群（產業 seq111，⛔ 不改定義）：每年初用前 250 日標準化日報酬 Ward 分群，群數 ＝ 母體檔數 ÷ 10
    ★ 分群檔：信箱、產業研究用、WSL、暫存夾都找不到產業 seq111 分群檔或逐筆名單 ⇒ 照定義重建（本檔），一致率只能對 seq111 件內的彙總數字
      （個股訊號 4,930、族群轉強 1,030、訊號月 113）以本檔同法重建近似訊號比對 ⇒ 報「彙總一致」，⛔ 不是逐檔一致率
    ★ 年 Y 的分群：參考日 ＝ 該世界日曆中 Y 年第一個交易日 ref；回看 [ref−250, ref−1] 共 250 個交易日
    ★ 母體（seq111 件內口徑）：data.load_universe（上市＋上櫃普通股，含之後下市；興櫃排除）中，回看 250 日內有效 K 棒（收盤有值）≥ 200，
      且 [ref−60, ref−1] 日均成交金額（無成交日記 0）≥ 1,000 萬元
    ★ 日報酬 ＝ 還原收盤相鄰兩個交易日都有值才算；|日報酬| ＞ 50% 視為斷點、當缺；每檔對自己有值的日報酬減平均、除標準差（ddof 0）、缺值補 0
    ★ Ward ＝ 平方歐氏距離 Lance–Williams 遞迴（同 scipy method="ward" 的合併順序；環境無 scipy、自寫，自測對窮舉 ΔSSE 驗），合併到剩
      K ＝ floor(母體檔數 ÷ 10 ＋ 0.5) 群為止；同距離取索引最小者
    ★補 F3b（分群步驟跑出「2005 回看只有 228 日」後、任何頻率數字之前補）：早年日曆首年回看不足 250 日 ⇒ 用可得回看（第 2 根起），
      有效 K 棒門檻按比例 ceil(200 × 可得日數 ÷ 250)；其餘不變
    族群營收轉強（第 m 月）：同群 ≥ 3 家，而且 ≥ 1/3 的成員第 m 月營收創 24 個月新高
    ★ 分母 ＝ 該群全部成員（無第 m 月營收者算「沒創新高」）
    ★ 創 24 月新高 ＝ 營量 v1 面板同式（research34：當月 ≥ 前 24 個月最大、前 24 個月全有值）〔另一讀法：含當月共 24 個月，即前 23 個月全有值且當月 ≥ 其最大；
      候選旗標兩讀法並報一致率〕；營收 ＝ 該世界資料夾 mops/revenue_hist（最新版，更正期間有輕微前視，照全線註）
    ★ 候選的 m ＝ 該候選自己的營收期別：同 research13.and_flags，取該世界 panel_rev 中 signal_pos ≤ 訊號日 pos、距離 ≤ 45 的最新一列的 period
      ⇒ 族群旗標與營量、營飆用同一期、同一個可用日（m＋1 月 10 日之後；2026-01 期起 15 日規則照該世界原建置，不另改）
    ★ 候選套用的分群 ＝ 訊號日 pos 所在年份 Y 的分群；候選不在 Y 年母體 ⇒ 「族群未轉強」並計入「不在產業母體」比例
 F4 頻率表（每 世界 × 策略 × 版本；營飆每顆種子各算，報中位〔p10～p90〕與 r0；段 ＝ 探索、確認、早年；以買進日 t 歸段）
    ① 每月：原版候選數（引擎看得到的列，以進場日歸月）、其中族群轉強數、原版買進、只買版買進、優先版買進、只買版平均持股與空格比例
       ★ 空格比例 ＝ 1 − 段內逐日持有檔數平均 ÷ 槽數（乾跑等權槽；＝ 現金比例的構造版）
    ② 優先版「換掉的買進」＝ 原版買進 (t, 代號) 不在優先版買進中的筆數 ÷ 原版買進筆數（對 10% 門檻）；
       買進重疊 ① ＝ 兩版同日同檔買進筆數 ÷ 該版買進筆數（另報 ÷ 原版買進筆數）（對 90% 門檻）；只買版、只買×優先同法
    ③ 持股重疊 ② ★ 乾跑無價格 ⇒ 報「等權槽持股重疊」＝ 逐日 |兩版共同持有代號| ÷ 槽數（每檔權重 1/N；一邊空槽 ＝ 0），平均、中位、逐年；
       ⚠ 金額權重需要價格（市值漂移）⇒ 留正式跑；③ 日報酬相關 ⇒ 只報「算得出」（兩版權益逐日都有、段內可配對）
       持有 ＝ [買進日, 賣出日)（researchYL_blend.holdings_w 同口徑；未賣持有到權益尾）
    ④ 只買版：逐日持有檔數分布（0、1～¼N、…、N）、空倉日比例、★ 空倉月 ＝ 整個月每個交易日都 0 檔的月份數；平均持股 ＜ N÷2 的月份數
       ★ 有效月數 ＝ 段內「有 ≥ 1 筆買進」的不同月份數（登錄沒定群；照方法論月分群 CI 的 24 群下限比）
    ⑤ 優先版「名額不足的日子」★ ＝ 當天（排程出場後）未持有的候選數 ＞ 空槽數的日子 ÷ 有未持有候選的日子；另報其中有族群轉強候選的日子
    ⑥ 候選中族群轉強比例、不在產業母體比例（逐年）
 F5 等價檢查（seq377）：只買版、優先版的買進序列是否與原版逐筆相同；族群旗標在候選中是否幾乎恆真（≥ 95%）或恆假（≤ 5%）；
    只買版買進是否 ＝ 「原版買進 ∩ 族群轉強」這個簡單條件（Jaccard）
 F6 閘：G0 乾跑原版營量買進 (t, 代號) 對 resultsYLlist/audit_seed0.csv.gz（只讀 t、sid、side 欄；正式版逐筆）一致率（現金不足差異照實報）；
    G1 世界閘照 IG 原樣印；G2 prio 全 0 的優先版 ＝ 原版（營量 r0；營飆 r0～2）逐筆相同；G3 逐日買進數 ＝ min(未持有候選, 空槽)（重建 vs 引擎）；
    G4 自算 24 月新高 vs 面板 rev_hi24（面板列）一致率；G5 strategy_lock --check 相符
 必附：「額外策略、與正式營量營飆分開；正式規則不動」「想法來自產業 seq111，看過同期結果才提」「營量、營飆本身已看過結果」；
       早年附 reduce_v2 約 0.3% 註與上櫃早年註（researchYL_integrate.NOTE3）
輸出 backtest/resultsGroupRevUp/freq/：monthly.csv、cand_yearly.csv、cells.csv、overlap_yearly.csv、holddist.csv、groups_yearly.csv、summary.json、結果.md
（中間檔 ~/grpwork/，不進 repo）

═══ 增補 --groups industry（2026-11-11（台北）寫死，在算任何一致率與頻率數字之前；裁定 seq502 §二、產業 seq112 交件）═══
    … --step groups --world main|early --groups industry ｜ --step sim … --groups industry ｜ --step report --groups industry
    （--groups 預設 self ＝ 上面原版，輸出、中間檔名都不變；industry ⇒ 中間檔 *_industry.pkl、輸出 backtest/resultsGroupRevUp/freq_industry/）
 I0 產業檔 ＝ 信箱 _交付-族群分群檔與seq111逐筆名單_產業分析線-20261111-0024/（clusters_by_year、group_month_flags、signals_no_returns；
    讀入驗 clusters 8,824 列、in_seq111＝1 共 4,930 筆、其中族群轉強 1,030、營收月 113；不符即停）
 I1 主段（main 世界）候選旗標 ＝ 產業版：候選營收期別 m（同 F3 ★）→ 分群年 Y → 產業 clusters_by_year 該年該股群號（used＝1 才算）
    → group_month_flags (m, Y, 群) 的 group_revenue_up
    ★ 分群年 Y ＝ README 第 4 點「看訊號日」：m 的 seq111 訊號日（m＋1 月 11 日起第一個交易日）所在年 ＝ m＋1 月的年
      〔另一讀法：候選自己的訊號日 pos 所在年（舊自建口徑）；報兩讀法不同筆數與旗標一致率〕
    ★ 2016 無分群（README：年初前不滿 250 日）：README 沒說候選怎麼處理 ⇒ 分群年 2016 的候選旗標 ＝ 0、記「不在產業母體」，報受影響筆數（候選、段內買進）
    ★ 該股在 Y 年 used＝1 群、但 group_month_flags 查無 (m, Y, 群) 列 ⇒ 旗標 0，報筆數
 I2 早年（early 世界 2005～2014，產業無檔）＝ 自建 v2，照 README 口徑 10 條（只描述、標「自建」）：
    1 價格：stocks/ 只取 valid_bar＝1、close 非空（★ 且 ＞0）、market twse／tpex；代號四碼數字、meta kind＝stock（含下市）；還原 ＝ data.cum_factor_series 同式
    2 母體：Y 年第一個交易日 t0；[t0−250, t0−1] 有效 K 棒 ≥ 200；[t0−60, t0−1] amount 平均（只對有效日、無成交日不計）≥ 1e7
    3 分群：補值（ffill）後還原價取 ★ [t0−251, t0−1] 共 250 個日對數報酬，缺值補 0，★ 先補 0 再逐檔減平均除標準差（ddof 0；sd＝0 ⇒ 1），
      Ward（ward_cut，自測已對窮舉驗）切 K ＝ max(2, 檔數 // 10) 群；群 ＜ 4 檔整群不用
      ★ t0 前不滿 251 日：主世界照 README 不分群（2016）；早年 2005 沿用 F3b（裁定 seq502 §二「核」）：用可得回看、門檻按比例
    4 分群年看訊號日（同 I1 ★）；5 創新高 ＝ 含當月 24 個月都有值且當月 ≥ 其最大（＝ F3 另一讀法 hib）
    8 族群轉強 ＝ 群內（年初名單）當月有營收者 n_wr、其中創新高 n_nh；n_nh ≥ 3 且 n_nh ≥ n_wr ÷ 3
    ★ v2 的價格、營收 ＝ 該世界資料夾（主世界 edc6f 快照；產業用 tw-stock-data 11/10 main）⇒ 殘差列入差異來源
 I3 逐檔一致率（只在 main 世界算；⛔ 不改舊頻率表結果）：
    a 分群：自建（舊）／v2 對產業，逐年：共同成員數、ARI、Rand、同群配對（產業同群者自建也同群 ÷ 產業同群配對；反向同）
    b 族群旗標：營量、營飆候選（引擎看得到的列、進場日在主段 2017-03-02～2026-08-24）逐筆旗標，自建（舊）對產業：相同 ÷ 候選（對 95%），整體＋逐年；
      另報旗標真的 Jaccard（底率約兩成，相同率會被「兩邊都假」墊高）
    c 個股訊號：舊自建 seq111 近似重建（seq111_recon 同式逐列）對 signals_no_returns in_seq111＝1，同股同營收月：交集 ÷ 聯集（對 95%），另報 ÷ 產業、÷ 自建；
      比對範圍 ＝ in_seq111＝1 出現的營收月（兩邊都限）
      v2 的 c：強勢第 7 點加權指數 ＝ tw-stock-data origin/main data/history/market_index.csv（git show 只讀，快取到 ~/grpwork）
    d 差異來源（同一批候選，逐版對產業的 b）：S0 舊自建；S1 舊分群＋README 旗標規則（4、5、8＋＜4 不用）；S2 v2（分群也照 README）；
      S3 產業分群＋本機營收照 README 旗標規則（驗本機營收與規則實作）
 I4 頻率表 ＝ 上面 F4～F6 全部照舊，只換旗標（主段＝產業版、早年＝自建 v2）；cand_yearly 另一讀法欄 ＝ I1 分群年另一讀法

═══ 增補（2026-11-11，裁定 seq503 正式跑）：正式程式 researchGroupRevUp.py 重用本檔 cell_sig／make_sig（dry=False 保留真實毛報酬）、run_engine（真價格、full）、
    intervals；乾跑路徑預設值不變（make_sig dry=True、run_engine 收盤＝開盤＝ones）⇒ 頻率表逐位元不變（自測 T6 驗）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402

TIME = "2026-11-10（台北）"
OUT = "backtest/resultsGroupRevUp/freq"
WORK = os.path.expanduser("~/grpwork")
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
REG_SHA, REG_BYTES = "e72a759aefc7bfdc", 6686
NSEED = int(os.environ.get("GRU_NSEED", "200"))
STRATS = {"營量": dict(H=60, N=20, gate=False, seed0=RR.P1_SEED0),
          "營飆": dict(H=120, N=10, gate=True, seed0=RR.P10_SEED0)}
VERS = ("原版", "只買版", "優先版")
PAIRS = (("優先版", "原版"), ("只買版", "原版"), ("只買版", "優先版"))
SEGN = {"main": ("探索", "確認"), "early": ("早年",)}
YEARS = {"main": range(2017, 2027), "early": range(2005, 2015)}
PANEL = {"main": os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"),
         "early": os.path.expanduser("~/earlydata/eotc_f65bb03e11/sig_otc/panel_rev.csv.gz")}
STALE_MAX = 45
LOOK, MINBARS, AMTWIN, AMTMIN = 250, 200, 60, 1.0e7
JUMP = 0.5
BIGP, NANRV = 1.0e15, -1.0e14
LOGF = None
GROUPS = "self"                                             # --groups；industry ⇒ 主段產業分群檔、早年自建 v2
OUT_IND = "backtest/resultsGroupRevUp/freq_industry"
IND_DIR = os.path.join(MAILBOX, "_交付-族群分群檔與seq111逐筆名單_產業分析線-20261111-0024")
IND_CHECK = {"clusters 列": 8824, "in_seq111": 4930, "族群轉強": 1030, "營收月": 113}
MAIN_SEG0 = "2017-03-02"


def sfx():
    return "" if GROUPS == "self" else "_industry"


def out_dir():
    return os.environ.get("GRU_OUT") or (OUT if GROUPS == "self" else OUT_IND)


def log(x):
    s = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(s + "\n")


# ═════════════ F0 登錄 sha ═════════════
def check_reg():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "**", f"*sha{REG_SHA}*"), recursive=True)]
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到 sha{REG_SHA} 登錄全文")
    b = open(fs[0], "rb").read()
    i = b.rfind(b"<!-- pw1")
    h = hashlib.sha256(b[:i]).hexdigest()[:16]
    ok = (h == REG_SHA and len(b) == REG_BYTES)
    if not ok:
        raise SystemExit(f"⛔ 登錄 sha／大小不符：{h}／{len(b)} B")
    return {"檔": os.path.basename(fs[0]), "sha16": h, "bytes": len(b)}


# ═════════════ Ward（平方歐氏 Lance–Williams）═════════════
def ward_cut(X, K):
    """X：n×d；合併到剩 K 群；回 labels（0..K−1，依群內最小列號排序編號）。"""
    n = X.shape[0]
    if K >= n:
        return np.arange(n)
    sq = (X * X).sum(1)
    Dm = sq[:, None] + sq[None, :] - 2.0 * (X @ X.T)
    np.maximum(Dm, 0.0, out=Dm)
    np.fill_diagonal(Dm, np.inf)
    size = np.ones(n)
    alive = np.ones(n, bool)
    lab = np.arange(n)
    nc = n
    while nc > K:
        k = int(np.argmin(Dm)); i, j = divmod(k, n)
        if i > j:
            i, j = j, i
        ni, nj = size[i], size[j]; dij = Dm[i, j]
        nk = size
        new = ((ni + nk) * Dm[i] + (nj + nk) * Dm[j] - nk * dij) / (ni + nj + nk)
        new[~alive] = np.inf; new[i] = np.inf; new[j] = np.inf
        Dm[i, :] = new; Dm[:, i] = new; Dm[i, i] = np.inf
        Dm[j, :] = np.inf; Dm[:, j] = np.inf
        alive[j] = False; size[i] = ni + nj
        lab[lab == j] = i
        nc -= 1
    roots = sorted(set(lab.tolist()), key=lambda r: int(np.flatnonzero(lab == r).min()))
    m = {r: q for q, r in enumerate(roots)}
    return np.array([m[x] for x in lab])


def zrets(C):
    """C：n×(L＋1) 還原收盤；回 n×L 標準化日報酬（缺 ⇒ 0）。"""
    with np.errstate(invalid="ignore", divide="ignore"):
        r = C[:, 1:] / C[:, :-1] - 1.0
    r[~np.isfinite(r)] = np.nan
    r[np.abs(r) > JUMP] = np.nan
    mu = np.nanmean(r, 1, keepdims=True); sd = np.nanstd(r, 1, keepdims=True)
    sd[~(sd > 0)] = 1.0
    z = (r - mu) / sd
    z[np.isnan(z)] = 0.0
    return z


def hi24_tables(rev):
    """rev：period × sid（完整月序）；回 (hi24 主讀法, hi24b 另一讀法) 兩個 bool 表。"""
    p1 = rev.shift(1)
    m24 = p1.rolling(24, min_periods=24).max()
    m23 = p1.rolling(23, min_periods=23).max()
    hi = rev.notna() & (rev >= m24)
    hib = rev.notna() & (rev >= m23)
    return hi, hib


def group_up(members_hi, size):
    """members_hi：該群第 m 月創高的成員數；size：群大小。"""
    return (size >= 3) and (members_hi * 3 >= size)


# ═════════════ step world ═════════════
def step_world(wn, procs):
    from backtest import researchYL_integrate as IG
    if wn == "main":
        W, gate = IG.main_world(log)
    else:
        W, gate = IG.early_world(log, procs)
    base = W["base"]
    keep = [c for c in ("sid", "k", "pos", "entry_pos", "month", "xpos_H60", "xpos_H120", "relvol") if c in base.columns]
    S = base[keep].copy().reset_index(drop=True)
    S["sid"] = S["sid"].astype(str)
    S["gated"] = np.asarray(W["reg"], bool)[S["entry_pos"].to_numpy(int) - 1]
    assert int(S["gated"].sum()) == len(W["SIG"][True]), "閘列數不符"
    P = dict(cal=W["cal"], w0=W["w0"], w1=W["w1"], NP=int(W["NP"]), SF=W["SF"], segp=W["segp"], S=S, data=D.DATA,
             sids=sorted(set(S["sid"])), gate=gate)
    os.makedirs(WORK, exist_ok=True)
    pickle.dump(P, open(os.path.join(WORK, f"world_{wn}.pkl"), "wb"), protocol=5)
    log(f"[world {wn}] 訊號 {len(S)}｜閘內 {int(S['gated'].sum())}｜NP {P['NP']}｜data {D.DATA}｜閘 {gate}")


# ═════════════ step groups ═════════════
def _load_px(args):
    sid, mk = args
    st = D.load_stock(sid, mk, _G["cal"])
    if st is None:
        return sid, None, None
    return sid, st.df["close"].to_numpy(np.float64), st.df["amount"].to_numpy(np.float64)


_G: dict = {}


def load_revenue():
    fs = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    full = pd.period_range(rev.index.min(), rev.index.max(), freq="M").strftime("%Y-%m")
    return rev.reindex(full)


def cand_period(S, panel):
    """and_flags 同式：每列候選的營收期別（找不到 ⇒ None）。"""
    p = panel.sort_values(["stock_id", "signal_pos"])
    by = {sid: (g["signal_pos"].to_numpy(), g["period"].to_numpy(), g["rev_hi24"].to_numpy(bool)) for sid, g in p.groupby("stock_id")}
    out = []; nohi = 0
    for sid, pos in zip(S["sid"], S["pos"]):
        if sid not in by:
            out.append(None); continue
        sp, per, hi = by[sid]
        j = int(np.searchsorted(sp, pos, side="right")) - 1
        if j >= 0 and pos - sp[j] <= STALE_MAX:
            out.append(per[j]); nohi += int(not hi[j])
        else:
            out.append(None)
    return out, nohi


def step_groups(wn, procs):
    P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
    D.DATA = P["data"]
    cal = D.load_calendar()
    if not (len(cal) == len(P["cal"]) and (cal == P["cal"]).all()):
        raise SystemExit("⛔ 日曆與世界不同")
    uni = D.load_universe()
    _G["cal"] = cal
    jobs = [(s, m) for s, m in zip(uni["stock_id"], uni["market"])]
    CL, AM = {}, {}
    with Pool(procs, initializer=_G.update, initargs=({"cal": cal},)) as pool:
        for sid, c, a in pool.imap_unordered(_load_px, jobs, chunksize=16):
            if c is not None:
                CL[sid] = c; AM[sid] = a
    log(f"[groups {wn}] 價格 {len(CL)} 檔／普通股 {len(uni)}")
    rev = load_revenue()
    hi, hib = hi24_tables(rev)
    mk = uni.set_index("stock_id")["market"]
    # 分群
    G = {}; GY = []
    for Y in YEARS[wn]:
        ref = int(cal.searchsorted(pd.Timestamp(year=Y, month=1, day=1)))
        lo = ref - LOOK; minb = MINBARS
        if ref >= len(cal):
            log(f"  {Y}：超出日曆 ⇒ 跳過"); continue
        if lo - 1 < 0:                                  # ★補（F3b）：早年日曆首年不足 250 日 ⇒ 用可得回看、有效 K 棒門檻按比例
            lo = 1; minb = int(np.ceil(MINBARS * (ref - lo) / LOOK))
            log(f"  {Y}：回看只有 {ref - lo} 日 ⇒ 用可得回看、門檻 {minb} 根（★）")
        elig = []
        for sid in sorted(CL):
            c = CL[sid]; a = AM[sid]
            nv = int(np.isfinite(c[lo:ref]).sum())
            if nv < minb:
                continue
            am = np.nan_to_num(a[ref - AMTWIN:ref], nan=0.0).mean()
            if am < AMTMIN:
                continue
            elig.append(sid)
        n = len(elig); K = int(np.floor(n / 10 + 0.5))
        C = np.vstack([CL[s][lo - 1:ref] for s in elig])
        Z = zrets(C)
        t0 = time.time(); lab = ward_cut(Z, K)
        sizes = np.bincount(lab)
        G[Y] = {"ref": ref, "sids": elig, "lab": lab, "sizes": sizes}
        GY.append({"世界": wn, "年": Y, "參考日": str(cal[ref].date()), "母體": n, "上市": int(sum(mk.get(s) == "twse" for s in elig)),
                   "上櫃": int(sum(mk.get(s) == "tpex" for s in elig)), "群數": K, "≥3 家群數": int((sizes >= 3).sum()),
                   "≥3 家群涵蓋檔數": int(sizes[sizes >= 3].sum()), "最大群": int(sizes.max()), "群大小中位": float(np.median(sizes)), "秒": round(time.time() - t0, 1)})
        log(f"  {Y}：母體 {n}｜K {K}｜≥3 家群 {(sizes >= 3).sum()}｜{time.time() - t0:.1f}s")
    # 群 × 期 的族群轉強
    GU = {}
    hiv = {"主": hi, "另": hib}
    for Y, g in G.items():
        periods = [p for p in rev.index if f"{Y - 1}-01" <= p <= f"{Y}-12"]
        cols = [s for s in g["sids"]]
        for nm, T in hiv.items():
            M = T.reindex(index=periods, columns=cols).fillna(False).to_numpy(bool)    # 期 × 成員
            for c in range(len(g["sizes"])):
                idx = np.flatnonzero(g["lab"] == c)
                cnt = M[:, idx].sum(1)
                for pi, p in enumerate(periods):
                    GU[(nm, Y, c, p)] = group_up(int(cnt[pi]), int(g["sizes"][c]))
    # 候選旗標
    S = P["S"].copy()
    panel = pd.read_csv(PANEL[wn], dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "signal_pos", "rev_hi24"])
    panel["rev_hi24"] = panel["rev_hi24"].fillna(False).astype(bool)
    per, nohi = cand_period(S, panel)
    S["period"] = per
    S["year"] = [cal[int(p)].year for p in S["pos"]]
    lk = {Y: dict(zip(g["sids"], g["lab"])) for Y, g in G.items()}
    inu, f_main, f_alt = [], [], []
    for sid, Y, p in zip(S["sid"], S["year"], S["period"]):
        c = lk.get(Y, {}).get(sid)
        inu.append(c is not None)
        f_main.append(bool(c is not None and p is not None and GU.get(("主", Y, int(c), p), False)))
        f_alt.append(bool(c is not None and p is not None and GU.get(("另", Y, int(c), p), False)))
    S["in_univ"] = inu; S["grp"] = f_main; S["grp_alt"] = f_alt
    # G4：自算 24 月新高 vs 面板
    pr = panel[panel["period"].isin(hi.index)]
    pr = pr[pr["stock_id"].isin(hi.columns)]
    hv =np.array([bool(hi.at[p, s]) for p, s in zip(pr["period"], pr["stock_id"])])
    g4 = {"面板列": int(len(pr)), "一致": int((hv == pr["rev_hi24"].to_numpy(bool)).sum()),
          "面板真我假": int((~hv & pr["rev_hi24"].to_numpy(bool)).sum()), "面板假我真": int((hv & ~pr["rev_hi24"].to_numpy(bool)).sum()),
          "候選找不到期別": int(sum(p is None for p in per)), "候選期別列非創高（應 0）": int(nohi)}
    log(f"[G4 {wn}] {g4}")
    out = {"S": S, "GY": GY, "G4": g4, "G": {Y: {"sids": g["sids"], "lab": g["lab"].tolist()} for Y, g in G.items()}}
    if wn == "main":
        out["seq111"] = seq111_recon(cal, CL, G, GU, hi, hib)
        log(f"[seq111 近似重建] {out['seq111']}")
    pickle.dump(out, open(os.path.join(WORK, f"groups_{wn}.pkl"), "wb"), protocol=5)


def seq111_recon(cal, CL, G, GU, hi, hib):
    """seq111 件內口徑的個股訊號近似重建（彙總一致性）：訊號日 e ＝ m＋1 月 10 日之後第一個交易日；
    當月創 24 月新高 ＋ e 收盤 ＞ 60 日均 ＋ 近 20 日報酬 ＞ 加權指數（★ 庫無加權指數 ⇒ 0050 還原代）；母體 ＝ e 所在年分群母體。"""
    b = D.load_benchmark(cal)["close"].to_numpy(float)
    rows = []
    for Y, g in G.items():
        lab = dict(zip(g["sids"], g["lab"]))
        for p in hi.index:
            y, m = int(p[:4]), int(p[5:])
            y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            if y2 != Y:
                continue
            e = int(cal.searchsorted(pd.Timestamp(year=y2, month=m2, day=10), side="right"))
            if e >= len(cal) or e < 60:
                continue
            for sid in g["sids"]:
                if not bool(hi.at[p, sid]) if sid in hi.columns else True:
                    continue
                c = CL[sid]
                w = c[e - 59:e + 1]
                if not (np.isfinite(w).all() and np.isfinite(c[e - 20])):
                    continue
                if not (c[e] > w.mean()):
                    continue
                if not (c[e] / c[e - 20] - 1.0 > b[e] / b[e - 20] - 1.0):
                    continue
                cc = int(lab[sid])
                rows.append((p, sid, bool(GU.get(("主", Y, cc, p), False))))
    if not rows:
        return {}
    X = pd.DataFrame(rows, columns=["period", "sid", "grp"])
    X = X[X["period"] >= "2016-12"]
    bm = X.groupby("period")["grp"].agg(["sum", "count"])
    return {"個股訊號": int(len(X)), "族群轉強": int(X["grp"].sum()), "族群轉強占比": float(X["grp"].mean()),
            "訊號月": int(X["period"].nunique()), "兩邊都有的月": int(((bm["sum"] > 0) & (bm["sum"] < bm["count"])).sum()),
            "期別範圍": [str(X["period"].min()), str(X["period"].max())],
            "seq111 件內": {"個股訊號": 4930, "族群轉強": 1030, "族群轉強占比": 1030 / 4930, "訊號月": 113, "兩邊都有的月": 80}}


# ═════════════ --groups industry：產業檔、自建 v2、逐檔一致率（I0～I4）═════════════
TIME_IND = "2026-11-11（台北）"


def load_industry(d=None):
    d = d or IND_DIR
    cl = pd.read_csv(os.path.join(d, "clusters_by_year.csv"), dtype={"stock_id": str})
    gm = pd.read_csv(os.path.join(d, "group_month_flags.csv"), dtype={"revenue_month": str})
    sg = pd.read_csv(os.path.join(d, "signals_no_returns.csv"), dtype={"stock_id": str, "revenue_month": str})
    return cl, gm, sg


def check_industry(cl, gm, sg):
    s1 = sg[sg["in_seq111"] == 1]
    got = {"clusters 列": int(len(cl)), "in_seq111": int(len(s1)), "族群轉強": int(s1["group_revenue_up"].sum()),
           "營收月": int(s1["revenue_month"].nunique())}
    return got, got == IND_CHECK


def ind_tables(cl, gm):
    memb = defaultdict(dict)
    for Y, sid, g, u in zip(cl["year"], cl["stock_id"], cl["group"], cl["used"]):
        memb[int(Y)][sid] = (int(g), bool(int(u) == 1))
    up = {(m, int(Y), int(g)): bool(int(f) == 1) for m, Y, g, f in zip(gm["revenue_month"], gm["cluster_year"], gm["group"], gm["group_revenue_up"])}
    return dict(memb), up


def next_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return (y + 1, 1) if mo == 12 else (y, mo + 1)


def cyear(m):
    """README 第 4 點：營收月 m 的 seq111 訊號日（m＋1 月 11 日起第一個交易日）所在年 ＝ m＋1 月的年。"""
    return next_month(m)[0]


def apply_flags(S, memb, up, mode="sig"):
    """候選逐列族群旗標。memb {Y: {sid: (群, used)}}；up {(m, Y, 群): bool}。
    mode：sig ＝ 分群年看 m 的訊號日（★ I1）；pos ＝ 候選自己訊號日 pos 所在年（舊自建口徑）。回 (旗標, 在母體且群 used, 分群年, 查無數)。"""
    fl, inu, cys = [], [], []
    miss = 0
    for sid, p, ypos in zip(S["sid"], S["period"], S["year"]):
        if not isinstance(p, str):
            fl.append(False); inu.append(False); cys.append(-1); continue
        Y = cyear(p) if mode == "sig" else int(ypos)
        cys.append(Y)
        c = memb.get(Y, {}).get(sid)
        if c is None or not c[1]:
            fl.append(False); inu.append(False); continue
        inu.append(True)
        k = (p, Y, c[0])
        miss += int(k not in up)
        fl.append(bool(up.get(k, False)))
    return np.array(fl, bool), np.array(inu, bool), np.array(cys, int), miss


def readme_up(memb, rev, hib):
    """README 第 8 點：只算 used 群；分母 ＝ 年初名單中當月有營收者。回 up、stat {(m, Y, 群): (n_wr, n_nh)}。"""
    up, stat = {}, {}
    for Y, mm in memb.items():
        grp = defaultdict(list)
        for sid, (g, u) in mm.items():
            if u:
                grp[g].append(sid)
        months = [p for p in rev.index if cyear(p) == Y]
        if not months:
            continue
        for g, sids in grp.items():
            cols = [s for s in sids if s in rev.columns]
            nwr = rev.loc[months, cols].notna().sum(axis=1).to_numpy() if cols else np.zeros(len(months), int)
            nnh = hib.loc[months, cols].sum(axis=1).to_numpy() if cols else np.zeros(len(months), int)
            for p, a, b in zip(months, nwr, nnh):
                up[(p, Y, g)] = bool(b >= 3 and 3 * b >= a)
                stat[(p, Y, g)] = (int(a), int(b))
    return up, stat


def old_gu(G, hi):
    """舊自建 step_groups 同式重算 GU（主讀法）⇒ {(m, Y, 群): bool}。"""
    up = {}
    for Y, g in G.items():
        lab = np.asarray(g["lab"]); sizes = np.bincount(lab)
        periods = [p for p in hi.index if f"{Y - 1}-01" <= p <= f"{Y}-12"]
        M = hi.reindex(index=periods, columns=list(g["sids"])).fillna(False).to_numpy(bool)
        for c in range(len(sizes)):
            cnt = M[:, np.flatnonzero(lab == c)].sum(1)
            for pi, p in enumerate(periods):
                up[(p, Y, c)] = group_up(int(cnt[pi]), int(sizes[c]))
    return up


def _load_px_v2(sid):
    """README 第 1 點價格面板：valid_bar＝1、close 非空（★ ＞0）、market twse／tpex；還原 ＝ data.cum_factor_series 同式。"""
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return sid, None, None
    raw = pd.read_csv(p, dtype={"date": str, "market": str}, usecols=lambda c: c in ("date", "close", "amount", "market", "valid_bar"))
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce"); raw["amount"] = pd.to_numeric(raw["amount"], errors="coerce")
    ok = raw["close"].notna() & (raw["close"] > 0) & raw["market"].isin(["twse", "tpex"])
    if "valid_bar" in raw.columns:
        ok &= pd.to_numeric(raw["valid_bar"], errors="coerce") == 1
    raw = raw[ok].copy()
    if raw.empty:
        return sid, None, None
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.drop_duplicates("date").set_index("date").sort_index()
    F = D.cum_factor_series(raw.index, D.load_adj(sid))
    cal = _G["cal"]
    return sid, (raw["close"] * F).reindex(cal).to_numpy(np.float64), raw["amount"].reindex(cal).to_numpy(np.float64)


def v2_universe():
    mk = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    mk = mk[(mk["kind"] == "stock") & mk["stock_id"].str.fullmatch(r"\d{4}")]
    return sorted(set(mk["stock_id"]))


def build_v2(cal, PX, AM, years, f3b):
    """README 第 2、3 點：回 memb {Y: {sid: (群, used)}}、GY 列、註。"""
    FF = {}
    memb, GY, notes = {}, [], []
    for Y in years:
        ref = int(cal.searchsorted(pd.Timestamp(year=Y, month=1, day=1)))
        if ref >= len(cal):
            continue
        lo = ref - LOOK; minb = MINBARS
        if lo - 1 < 0:
            if not f3b:
                notes.append(f"{Y}：t0 前只有 {ref} 日（不滿 251）⇒ 不分群（README）"); continue
            lo = 1; minb = int(np.ceil(MINBARS * (ref - lo) / LOOK))
            notes.append(f"{Y}：回看只有 {ref - lo} 日 ⇒ F3b 用可得回看、門檻 {minb} 根（★ I2）")
        a0 = max(ref - AMTWIN, 0)
        elig = []
        for sid in sorted(PX):
            c = PX[sid]
            if int(np.isfinite(c[lo:ref]).sum()) < minb:
                continue
            a = AM[sid][a0:ref]; a = a[np.isfinite(a) & np.isfinite(c[a0:ref])]
            if not len(a) or a.mean() < AMTMIN:
                continue
            elig.append(sid)
        X = []
        for s in elig:
            if s not in FF:
                FF[s] = pd.Series(PX[s]).ffill().to_numpy()
            w = FF[s][lo - 1:ref]
            with np.errstate(invalid="ignore", divide="ignore"):
                r = np.diff(np.log(w))
            r[~np.isfinite(r)] = 0.0
            sd = r.std()
            X.append((r - r.mean()) / (sd if sd > 0 else 1.0))
        n = len(elig); K = max(2, n // 10)
        lab = ward_cut(np.vstack(X), K); sizes = np.bincount(lab)
        memb[Y] = {s: (int(l), bool(sizes[l] >= 4)) for s, l in zip(elig, lab)}
        GY.append({"年": Y, "參考日": str(cal[ref].date()), "母體": n, "群數": K, "用到的群（≥4）": int((sizes >= 4).sum()),
                   "用到的檔數": int(sizes[sizes >= 4].sum()), "最大群": int(sizes.max()), "群大小中位": float(np.median(sizes))})
    return memb, GY, notes, FF


def seq111_rows_self(cal, CL, G, GU, hi):
    """seq111_recon 同式，逐列回傳（period, sid, grp）。"""
    b = D.load_benchmark(cal)["close"].to_numpy(float)
    rows = []
    for Y, g in G.items():
        lab = dict(zip(g["sids"], g["lab"]))
        for p in hi.index:
            y2, m2 = next_month(p)
            if y2 != Y:
                continue
            e = int(cal.searchsorted(pd.Timestamp(year=y2, month=m2, day=10), side="right"))
            if e >= len(cal) or e < 60:
                continue
            for sid in g["sids"]:
                if not bool(hi.at[p, sid]) if sid in hi.columns else True:
                    continue
                c = CL[sid]
                w = c[e - 59:e + 1]
                if not (np.isfinite(w).all() and np.isfinite(c[e - 20])):
                    continue
                if not (c[e] > w.mean()):
                    continue
                if not (c[e] / c[e - 20] - 1.0 > b[e] / b[e - 20] - 1.0):
                    continue
                rows.append((p, sid, bool(GU.get((p, Y, int(lab[sid])), False))))
    X = pd.DataFrame(rows, columns=["period", "sid", "grp"])
    return X[X["period"] >= "2016-12"].reset_index(drop=True)


def market_index(cal):
    f = os.path.join(WORK, "market_index_origin_main.csv")
    if not os.path.exists(f):
        txt = subprocess.run(["git", "-C", os.path.expanduser("~/tw-stock-data"), "show", "origin/main:data/history/market_index.csv"],
                             capture_output=True, text=True, check=True).stdout
        open(f, "w", encoding="utf-8").write(txt)
    m = pd.read_csv(f, dtype={"date": str})
    s = pd.Series(pd.to_numeric(m["close"], errors="coerce").to_numpy(), index=pd.to_datetime(m["date"])).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(cal).ffill().to_numpy(float), int(s.reindex(cal).isna().sum())


def seq111_rows_v2(cal, PX, FF, memb, up, hib, idx):
    """README 第 4～8 點：個股訊號逐列（period, sid, grp）。"""
    rows = []
    MA = {}
    for Y, mm in memb.items():
        for p in [q for q in hib.index if cyear(q) == Y]:
            y2, m2 = next_month(p)
            t = int(cal.searchsorted(pd.Timestamp(year=y2, month=m2, day=11)))
            if t >= len(cal) or t < 20:
                continue
            hrow = hib.loc[p]
            for sid, (g, u) in mm.items():
                if not u or sid not in hib.columns or not bool(hrow[sid]):
                    continue
                c = PX[sid]
                if not (np.isfinite(c[t]) and np.isfinite(c[t - 20])):
                    continue
                if sid not in FF:
                    FF[sid] = pd.Series(c).ffill().to_numpy()
                if sid not in MA:
                    MA[sid] = pd.Series(FF[sid]).rolling(60, min_periods=50).mean().to_numpy()
                f = FF[sid]
                if not (f[t] > MA[sid][t]):
                    continue
                if not (f[t] / f[t - 20] - 1.0 > idx[t] / idx[t - 20] - 1.0):
                    continue
                rows.append((p, sid, bool(up.get((p, Y, g), False))))
    return pd.DataFrame(rows, columns=["period", "sid", "grp"])


def pair_stats(la, lb):
    """兩組標籤（同一批成員）：ARI、Rand、同群配對。"""
    def c2(x):
        return x * (x - 1) / 2.0
    n = len(la)
    ct = Counter(zip(la, lb)); sa = Counter(la); sb = Counter(lb)
    sij = sum(c2(v) for v in ct.values()); si = sum(c2(v) for v in sa.values()); sj = sum(c2(v) for v in sb.values()); tot = c2(n)
    exp = si * sj / tot if tot else 0.0; mx = (si + sj) / 2.0
    return {"ARI": (sij - exp) / (mx - exp) if mx != exp else 1.0, "Rand": (tot + 2 * sij - si - sj) / tot if tot else None,
            "同群配對_兩邊都同群": sij, "同群配對_A": si, "同群配對_B": sj}


def flag_agree(a, b):
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    n = len(a)
    return {"分母": int(n), "相同": int((a == b).sum()), "一致率": float((a == b).mean()) if n else None,
            "都真": int((a & b).sum()), "A真B假": int((a & ~b).sum()), "A假B真": int((~a & b).sum()),
            "真集合Jaccard": float((a & b).sum() / (a | b).sum()) if (a | b).any() else None,
            "A轉強比例": float(a.mean()) if n else None, "B轉強比例": float(b.mean()) if n else None}


def set_agree(A, B):
    A, B = set(A), set(B)
    i = len(A & B); u = len(A | B)
    return {"自建": len(A), "產業": len(B), "交集": i, "只自建": len(A - B), "只產業": len(B - A),
            "交集÷聯集": i / u if u else None, "交集÷產業": i / len(B) if B else None, "交集÷自建": i / len(A) if A else None}


def step_groups_industry(wn, procs):
    P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
    Gs = pickle.load(open(os.path.join(WORK, f"groups_{wn}.pkl"), "rb"))      # 舊自建（只讀，不改）
    D.DATA = P["data"]
    cal = D.load_calendar()
    if not (len(cal) == len(P["cal"]) and (cal == P["cal"]).all()):
        raise SystemExit("⛔ 日曆與世界不同")
    _G["cal"] = cal
    sids2 = v2_universe()
    PX, AM = {}, {}
    with Pool(procs, initializer=_G.update, initargs=({"cal": cal},)) as pool:
        for sid, c, a in pool.imap_unordered(_load_px_v2, sids2, chunksize=16):
            if c is not None and np.isfinite(c).any():
                PX[sid] = c; AM[sid] = a
    log(f"[groups-ind {wn}] v2 價格 {len(PX)} 檔／四碼普通股 {len(sids2)}")
    rev = load_revenue()
    hi, hib = hi24_tables(rev)
    memb2, GY2, notes2, FF = build_v2(cal, PX, AM, YEARS[wn] if wn == "early" else range(2016, 2027), f3b=(wn == "early"))
    for x in notes2:
        log("  " + x)
    up2, stat2 = readme_up(memb2, rev, hib)
    S = Gs["S"].copy()
    f2, inu2, cy2, miss2 = apply_flags(S, memb2, up2, "sig")
    f2p, _, _, _ = apply_flags(S, memb2, up2, "pos")
    S["grp_self"] = S["grp"].to_numpy(bool)
    S["grp_v2"] = f2
    out = {"G4": Gs["G4"], "seq111": None}
    if wn == "early":
        S["grp"] = f2; S["grp_alt"] = f2p; S["in_univ"] = inu2; S["cy"] = cy2
        out["來源"] = "自建 v2（README 口徑 10 條；2005 沿用 F3b）、只描述"
        out["star"] = {"查無 (m,Y,群) 列": miss2, "註": notes2}
        out["GY"] = [{"世界": wn, "來源": "自建 v2", **r} for r in GY2]
    else:
        cl, gm, sg = load_industry()
        got, okk = check_industry(cl, gm, sg)
        log(f"[I0 產業檔讀入] {got} {'相符' if okk else '⛔ 不符'}")
        if not okk:
            raise SystemExit("⛔ 產業檔筆數不符")
        badcy = int(sum(cyear(m) != int(y) for m, y in zip(gm["revenue_month"], gm["cluster_year"])))
        memi, upi = ind_tables(cl, gm)
        fi, inui, cyi, missi = apply_flags(S, memi, upi, "sig")
        fip, _, _, _ = apply_flags(S, memi, upi, "pos")
        S["grp"] = fi; S["grp_alt"] = fip; S["in_univ"] = inui; S["cy"] = cyi
        out["來源"] = "產業 seq112 分群檔（clusters_by_year＋group_month_flags）"
        # 舊自建分群
        memo = {int(Y): {s: (int(l), True) for s, l in zip(g["sids"], g["lab"])} for Y, g in Gs["G"].items()}
        memo4 = {}
        for Y, g in Gs["G"].items():
            sz = np.bincount(np.asarray(g["lab"]))
            memo4[int(Y)] = {s: (int(l), bool(sz[l] >= 4)) for s, l in zip(g["sids"], g["lab"])}
        Gold = {int(Y): {"sids": list(g["sids"]), "lab": list(g["lab"])} for Y, g in Gs["G"].items()}
        GU = old_gu(Gold, hi)
        f0, _, _, _ = apply_flags(S, memo, GU, "pos")
        g0chk = int((f0 != S["grp_self"].to_numpy(bool)).sum())
        up1, _ = readme_up(memo4, rev, hib)
        f1, _, _, _ = apply_flags(S, memo4, up1, "sig")
        up3, stat3 = readme_up(memi, rev, hib)
        f3, _, _, _ = apply_flags(S, memi, up3, "sig")
        # S3 對產業 group_month_flags 逐列
        gmk = list(zip(gm["revenue_month"], gm["cluster_year"].astype(int), gm["group"].astype(int)))
        gs3 = {"列": len(gmk), "本機有": sum(k in stat3 for k in gmk),
               "n_with_revenue 相同": int(sum(stat3.get(k, (-1, -1))[0] == int(a) for k, a in zip(gmk, gm["n_with_revenue"]))),
               "n_new_high 相同": int(sum(stat3.get(k, (-1, -1))[1] == int(a) for k, a in zip(gmk, gm["n_new_high"]))),
               "group_revenue_up 相同": int(sum(up3.get(k, None) == bool(int(a)) for k, a in zip(gmk, gm["group_revenue_up"])))}
        # 候選範圍：主段進場、引擎看得到的列
        w0, w1 = P["w0"], P["w1"]
        ep = S["entry_pos"].to_numpy(int)
        tab_b, tab_d, tab_a, tab_c = [], [], [], []
        summ_b = {}
        VERF = {"S0 舊自建": f0, "S1 舊分群＋README 旗標規則": f1, "S2 自建 v2": f2, "S3 產業分群＋本機營收 README 規則": f3}
        dsum = {k: {} for k in VERF}
        for st in STRATS:
            H = STRATS[st]["H"]
            m = ((S["gated"].to_numpy(bool) if STRATS[st]["gate"] else np.ones(len(S), bool)) & S[f"xpos_H{H}"].notna().to_numpy()
                 & (S[f"xpos_H{H}"].fillna(-1).to_numpy() >= 0) & (ep >= w0) & (ep <= w1))
            yy = np.array([cal[e].year for e in ep])
            r = flag_agree(S["grp_self"].to_numpy(bool)[m], fi[m])
            summ_b[st] = r
            tab_b.append({"策略": st, "年": "全段", **r})
            for Y in sorted(set(yy[m])):
                mm = m & (yy == Y)
                tab_b.append({"策略": st, "年": int(Y), **flag_agree(S["grp_self"].to_numpy(bool)[mm], fi[mm])})
            for k, f in VERF.items():
                rr = flag_agree(f[m], fi[m])
                dsum[k][st] = rr["一致率"]
                tab_d.append({"版": k, "策略": st, **rr})
            alt = flag_agree(fip[m], fi[m])
            tab_d.append({"版": "產業分群年另一讀法（候選 pos 年）", "策略": st, **alt})
            dsum.setdefault("產業分群年另一讀法（候選 pos 年）", {})[st] = alt["一致率"]
        # a 分群
        pool_a = {"舊自建": [0.0, 0.0, 0.0], "自建 v2": [0.0, 0.0, 0.0]}
        for Y in sorted(memi):
            for nm, mem in (("舊自建", memo), ("自建 v2", memb2)):
                A = mem.get(Y, {}); B = memi[Y]
                com = sorted(set(A) & set(B))
                row = {"版": nm, "年": Y, "自建母體": len(A), "產業母體": len(B), "共同成員": len(com)}
                if com:
                    ps = pair_stats([A[s][0] for s in com], [B[s][0] for s in com])
                    row.update({"ARI": ps["ARI"], "Rand": ps["Rand"],
                                "產業同群中自建也同群": ps["同群配對_兩邊都同群"] / ps["同群配對_B"] if ps["同群配對_B"] else None,
                                "自建同群中產業也同群": ps["同群配對_兩邊都同群"] / ps["同群配對_A"] if ps["同群配對_A"] else None,
                                "同群配對Jaccard": ps["同群配對_兩邊都同群"] / (ps["同群配對_A"] + ps["同群配對_B"] - ps["同群配對_兩邊都同群"])})
                    pool_a[nm][0] += ps["同群配對_兩邊都同群"]; pool_a[nm][1] += ps["同群配對_A"]; pool_a[nm][2] += ps["同群配對_B"]
                tab_a.append(row)
        pa = {nm: {"同群配對Jaccard（逐年合計）": v[0] / (v[1] + v[2] - v[0]), "產業同群中自建也同群": v[0] / v[2],
                   "ARI 逐年中位": float(np.median([r["ARI"] for r in tab_a if r["版"] == nm and "ARI" in r])),
                   "共同成員合計": int(sum(r["共同成員"] for r in tab_a if r["版"] == nm)),
                   "產業母體合計": int(sum(r["產業母體"] for r in tab_a if r["版"] == nm))} for nm, v in pool_a.items()}
        # c 個股訊號
        uni = D.load_universe()                                                     # 舊自建 c 用 data.load_stock 版價格（同 step_groups）
        CLs = {}
        with Pool(procs, initializer=_G.update, initargs=({"cal": cal},)) as pool:
            for sid, c, a in pool.imap_unordered(_load_px, list(zip(uni["stock_id"], uni["market"])), chunksize=16):
                if c is not None:
                    CLs[sid] = c
        Xs = seq111_rows_self(cal, CLs, Gold, GU, hi)
        agg = {"個股訊號": int(len(Xs)), "族群轉強": int(Xs["grp"].sum()), "訊號月": int(Xs["period"].nunique())}
        aggok = all(agg[k] == Gs["seq111"][k] for k in agg)
        log(f"[c] 舊自建逐列重建 {agg}；對舊彙總 {'相同' if aggok else '⛔ 不同'}")
        idx, idxna = market_index(cal)
        Xv = seq111_rows_v2(cal, PX, FF, memb2, up2, hib, idx)
        s1 = sg[sg["in_seq111"] == 1]
        months1 = set(s1["revenue_month"])
        Iset = set(zip(s1["revenue_month"], s1["stock_id"]))
        Iall = set(zip(sg["revenue_month"], sg["stock_id"]))
        for nm, X in (("舊自建", Xs), ("自建 v2", Xv)):
            Xm = X[X["period"].isin(months1)]
            r = set_agree(zip(Xm["period"], Xm["sid"]), Iset)
            mm_ = sorted(months1 & set(X["period"]))
            r2 = set_agree(zip(X["period"], X["sid"]), {k for k in Iall if k[0] in set(X["period"])})
            # 交集上的族群旗標
            ig = dict(zip(zip(s1["revenue_month"], s1["stock_id"]), s1["group_revenue_up"].astype(int) == 1))
            both = [(g, ig[(p, s)]) for p, s, g in zip(Xm["period"], Xm["sid"], Xm["grp"]) if (p, s) in ig]
            tab_c.append({"版": nm, "範圍": f"in_seq111＝1 的營收月（{len(mm_)}／{len(months1)} 月兩邊都有）", **r,
                          "交集上族群旗標一致率": float(np.mean([a == b for a, b in both])) if both else None,
                          "自建族群轉強占比": float(Xm["grp"].mean()) if len(Xm) else None})
            tab_c.append({"版": nm, "範圍": "全部 5,428 筆（in_seq111 0／1，限自建有的營收月）", **r2})
        ca = {r["版"]: r for r in tab_c if r["範圍"].startswith("in_seq111")}
        nbad = int(((cyi == 2016)).sum())
        star = {"分群年 2016 候選列（旗標 0）": nbad, "查無 group_month_flags 列（旗標 0）": missi,
                "產業 cluster_year ≠ m＋1 年（應 0）": badcy, "S0 重算對舊旗標不符（應 0）": g0chk,
                "舊自建逐列重建對舊彙總": "相同" if aggok else "不同", "加權指數在日曆上缺（補前值）": idxna, "v2 註": notes2}
        rows3 = [
            {"項": "a 分群（同群配對 Jaccard，2017～2026 逐年合計）", "分母": f"共同成員 {pa['舊自建']['共同成員合計']} 檔·年（產業母體 {pa['舊自建']['產業母體合計']}）",
             "一致率": pa["舊自建"]["同群配對Jaccard（逐年合計）"]},
            {"項": "a′ 分群（產業同群配對中自建也同群）", "分母": "產業同群配對（逐年合計）", "一致率": pa["舊自建"]["產業同群中自建也同群"]},
            {"項": "b 族群旗標｜營量候選（主段）", "分母": f"候選 {summ_b['營量']['分母']} 列", "一致率": summ_b["營量"]["一致率"]},
            {"項": "b 族群旗標｜營飆候選（主段）", "分母": f"候選 {summ_b['營飆']['分母']} 列", "一致率": summ_b["營飆"]["一致率"]},
            {"項": "c 個股訊號（同股同營收月，交集÷聯集）", "分母": f"聯集 {ca['舊自建']['自建'] + ca['舊自建']['產業'] - ca['舊自建']['交集']} 筆（產業 {ca['舊自建']['產業']}）",
             "一致率": ca["舊自建"]["交集÷聯集"]},
            {"項": "c′ 個股訊號（交集÷產業 4,930）", "分母": f"產業 {ca['舊自建']['產業']} 筆", "一致率": ca["舊自建"]["交集÷產業"]},
            {"項": "d：v2 的 b｜營量", "分母": f"候選 {summ_b['營量']['分母']} 列", "一致率": dsum["S2 自建 v2"]["營量"]},
            {"項": "d：v2 的 b｜營飆", "分母": f"候選 {summ_b['營飆']['分母']} 列", "一致率": dsum["S2 自建 v2"]["營飆"]},
            {"項": "d：v2 的 a（同群配對 Jaccard）", "分母": f"共同成員 {pa['自建 v2']['共同成員合計']}", "一致率": pa["自建 v2"]["同群配對Jaccard（逐年合計）"]},
            {"項": "d：v2 的 c（交集÷聯集）", "分母": f"產業 {ca['自建 v2']['產業']} 筆", "一致率": ca["自建 v2"]["交集÷聯集"]}]
        DESC = {"S0 舊自建": "原頻率表口徑", "S1 舊分群＋README 旗標規則": "只換 4、5、8 點＋＜4 檔不用",
                "S2 自建 v2": "分群也照 README（1～3 點）", "S3 產業分群＋本機營收 README 規則": "分群用產業的、旗標本機算（驗資料與實作）",
                "產業分群年另一讀法（候選 pos 年）": "★ I1 另一讀法"}
        out["agree"] = {"summary": {"產業檔讀入": {**got, "相符": okk}, "一致率三項": rows3,
                                    "差異來源": [{"版": k, "營量": v.get("營量"), "營飆": v.get("營飆"), "說明": DESC[k]} for k, v in dsum.items()],
                                    "a": pa, "b": summ_b, "c": ca, "S3 對 group_month_flags 逐列": gs3, "star": star},
                        "tables": {"agree_a_clusters": pd.DataFrame(tab_a), "agree_b_flags": pd.DataFrame(tab_b),
                                   "agree_c_signals": pd.DataFrame(tab_c), "agree_d_sources": pd.DataFrame(tab_d)}}
        out["star"] = star
        out["seq111"] = None
        gyi = []
        for Y, g in cl.groupby("year"):
            sz = g.groupby("group").size()
            gyi.append({"世界": wn, "來源": "產業", "年": int(Y), "參考日": str(g["first_trading_day"].iloc[0]), "母體": int(len(g)), "群數": int(len(sz)),
                        "用到的群（≥4）": int((sz >= 4).sum()), "用到的檔數": int(sz[sz >= 4].sum()), "最大群": int(sz.max()), "群大小中位": float(sz.median())})
        out["GY"] = gyi + [{"世界": wn, "來源": "自建 v2（對照）", **r} for r in GY2]
        log(f"[一致率] {json.dumps(rows3, ensure_ascii=False, default=str)}")
        log(f"[差異來源] {json.dumps(dsum, ensure_ascii=False)}")
        log(f"[S3 對 gm] {gs3}｜★ {star}")
    out["S"] = S
    pickle.dump(out, open(os.path.join(WORK, f"groups_{wn}_industry.pkl"), "wb"), protocol=5)
    log(f"[groups-ind {wn}] 完成｜族群轉強比例（全候選）{S['grp'].mean():.4f}")


# ═════════════ step sim（乾跑）═════════════
_W: dict = {}


def make_sig(S, st, ver, flag="grp", zero_prio=False, dry=True):
    """dry（預設，頻率表乾跑）⇒ 毛報酬全 0；dry=False（正式 researchGroupRevUp）⇒ 保留 S 的真實 g_H60／g_H120。"""
    s = S[S["gated"]] if STRATS[st]["gate"] else S
    s = s.copy()
    if dry:
        s["g_H60"] = 0.0; s["g_H120"] = 0.0
    if ver == "只買版":
        s = s[s[flag].to_numpy(bool)]
    elif ver == "優先版":
        pr = np.zeros(len(s)) if zero_prio else s[flag].to_numpy(bool).astype(float)
        if st == "營量":
            rv = s["relvol"].to_numpy(float)
            s["prio_rv"] = pr * BIGP + np.where(np.isfinite(rv), rv, NANRV)
        else:
            s["prio"] = pr
    return s


def cell_sig(S, st, ver, zero_prio=False, dry=True):
    """引擎看得到的列：make_sig ＋ xpos_H 有值且 ≥ 0（job、正式 researchGroupRevUp 共用）。"""
    sig = make_sig(S, st, ver, zero_prio=zero_prio, dry=dry)
    xc = f"xpos_H{STRATS[st]['H']}"
    return sig[sig[xc].notna() & (sig[xc] >= 0)]


def run_engine(sig, st, ver, r, ones, NP, SF, opens=None, full=False):
    """ones ＝ 收盤字典（乾跑全 1）；opens 預設同 ones。full ⇒ 另回引擎輸出 o 與 audit（正式 researchGroupRevUp 用）。"""
    H, N, seed0 = STRATS[st]["H"], STRATS[st]["N"], STRATS[st]["seed0"]
    au = []
    op = ones if opens is None else opens
    rng = np.random.default_rng(seed0 + r)
    if st == "營量":
        pk = "prio_rv" if ver == "優先版" else "relvol"
        o = R.simulate_mtm(sig, f"H{H}", N, rng, ones, op, NP, return_equity=True, log=[], d_max=None, pick=pk, queue_days=0,
                           stop_force=SF, audit=au)
    else:
        kw = dict(pick="prio", pick_tie="rng") if ver == "優先版" else {}
        o = R.simulate_mtm(sig, f"H{H}", N, rng, ones, op, NP, return_equity=True, stop_force=SF, audit=au, **kw)
    buys = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] == "buy"]
    sells = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] != "buy"]
    if full:
        return buys, sells, o, au
    return buys, sells


def intervals(buys, sells, NP):
    """(sid, tb, ts)；同檔不重複持有 ⇒ 依時間配對。"""
    sl = defaultdict(list)
    for t, s in sorted(sells):
        sl[s].append(t)
    out = []
    for t, s in sorted(buys):
        L = sl[s]
        j = next((i for i, x in enumerate(L) if x > t), None)
        ts = L.pop(j) if j is not None else NP
        out.append((s, t, ts))
    return out


def held_count(iv, NP):
    d = np.zeros(NP + 1)
    for _, a, b in iv:
        d[a] += 1; d[b] -= 1
    return np.cumsum(d)[:NP]


def overlap_count(iva, ivb, NP):
    by = defaultdict(list)
    for s, a, b in ivb:
        by[s].append((a, b))
    d = np.zeros(NP + 1)
    for s, a, b in iva:
        for a2, b2 in by.get(s, ()):
            lo, hi = max(a, a2), min(b, b2)
            if lo < hi:
                d[lo] += 1; d[hi] -= 1
    return np.cumsum(d)[:NP]


def shortage(sig, iv, N, NP):
    """逐日：未持有候選數、空槽數（排程出場後、買進前）。"""
    e = sig["entry_pos"].to_numpy(int); sids = sig["sid"].to_numpy(str); fl = sig["grp"].to_numpy(bool)
    byt = defaultdict(list)
    for t, s, f in zip(e, sids, fl):
        byt[int(t)].append((s, f))
    A = np.sort(np.array([a for _, a, _ in iv], int)); Bv = np.sort(np.array([b for _, _, b in iv], int))
    bys = defaultdict(list)
    for s, a, b in iv:
        bys[s].append((a, b))
    res = {}
    for t, L in byt.items():
        nheld = int(np.searchsorted(A, t, side="left")) - int(np.searchsorted(Bv, t, side="right"))   # #{a < t < b}
        nh = [(s, f) for s, f in L if not any(a < t < b for a, b in bys.get(s, ()))]
        res[t] = (len(nh), sum(f for _, f in nh), N - nheld)
    return res


def job(args):
    wn, st, r = args
    P = _W["P"]; S = _W["S"]; NP = P["NP"]; SF = P["SF"]; ones = _W["ones"]; N = STRATS[st]["N"]
    cal = P["cal"]
    res = {"st": st, "r": r, "ver": {}}
    IV = {}; B = {}
    for v in VERS:
        sig = cell_sig(S, st, v)
        buys, sells = run_engine(sig, st, v, r, ones, NP, SF)
        iv = intervals(buys, sells, NP)
        IV[v] = iv; B[v] = buys
        hc = held_count(iv, NP)
        sh = shortage(sig, iv, N, NP)
        # G3：逐日買進數 ＝ min(未持有候選, 空槽)
        bc = Counter(t for t, _ in buys)
        g3 = sum(1 for t, (nh, _, fr) in sh.items() if bc.get(t, 0) != max(0, min(nh, fr)))
        g3 += sum(1 for t in bc if t not in sh)
        res["ver"][v] = {"buys": buys, "hc": hc.astype(np.int16), "short": sh, "g3": g3, "ncand": len(sig)}
    for a, b in PAIRS:
        res[f"ov_{a}_{b}"] = overlap_count(IV[a], IV[b], NP).astype(np.int16)
    # G2：prio 全 0 ＝ 原版
    if (st == "營量" and r == 0) or (st == "營飆" and r < 3):
        sig = cell_sig(S, st, "優先版", zero_prio=True)
        bz, sz = run_engine(sig, st, "優先版", r, ones, NP, SF)
        res["G2"] = bool(bz == B["原版"])
    return res


def step_sim(wn, procs):
    P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
    Gp = pickle.load(open(os.path.join(WORK, f"groups_{wn}{sfx()}.pkl"), "rb"))
    _W["P"] = P; _W["S"] = Gp["S"]
    _W["ones"] = {s: np.ones(P["NP"]) for s in P["sids"]}
    jobs = [(wn, "營量", 0)] + [(wn, "營飆", r) for r in range(NSEED)]
    t0 = time.time(); out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            out.append(res)
            if (i + 1) % 20 == 0:
                log(f"  sim {wn} {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    out.sort(key=lambda x: (x["st"], x["r"]))
    pickle.dump(out, open(os.path.join(WORK, f"sim_{wn}{sfx()}.pkl"), "wb"), protocol=5)
    log(f"[sim {wn}{sfx()}] {len(out)} 件｜{time.time() - t0:.0f}s")


# ═════════════ step report ═════════════
def seg_bounds(P, wn):
    return {sg: P["segp"][sg] for sg in SEGN[wn]}


def q(xs):
    xs = np.asarray([x for x in xs if x is not None and np.isfinite(x)], float)
    if not len(xs):
        return {"中位": None, "p10": None, "p90": None}
    return {"中位": float(np.median(xs)), "p10": float(np.percentile(xs, 10)), "p90": float(np.percentile(xs, 90))}


def per_seed_cell(res, P, x, y, N):
    cal = P["cal"]
    d = {}
    bset = {v: {(t, s) for t, s in res["ver"][v]["buys"] if x <= t <= y} for v in VERS}
    for v in VERS:
        hc = res["ver"][v]["hc"][x:y + 1].astype(float)
        d[f"{v}_買進"] = len(bset[v])
        d[f"{v}_平均持股"] = float(hc.mean())
        d[f"{v}_空格比例"] = float(1 - hc.mean() / N)
        d[f"{v}_空倉日比例"] = float((hc == 0).mean())
        mon = pd.Series(hc, index=cal[x:y + 1].strftime("%Y-%m"))
        g = mon.groupby(level=0)
        d[f"{v}_空倉月"] = int((g.max() == 0).sum())
        d[f"{v}_半滿以下月"] = int((g.mean() < N / 2).sum())
        d[f"{v}_月數"] = int(g.ngroups)
        d[f"{v}_有效月數"] = int(len({cal[t].strftime('%Y-%m') for t, _ in bset[v]}))
        sh = {t: z for t, z in res["ver"][v]["short"].items() if x <= t <= y}
        dc = [t for t, (nh, ng, fr) in sh.items() if nh > 0]
        ds = [t for t in dc if sh[t][0] > sh[t][2]]
        d[f"{v}_有候選日"] = len(dc)
        d[f"{v}_名額不足日比例"] = (len(ds) / len(dc)) if dc else None
        d[f"{v}_名額不足且有族群轉強候選日比例"] = (sum(1 for t in ds if sh[t][1] > 0) / len(dc)) if dc else None
    for a, b in PAIRS:
        A, Bb = bset[a], bset[b]
        inter = len(A & Bb)
        d[f"{a}vs{b}_買進重疊÷{a}"] = inter / len(A) if A else None
        d[f"{a}vs{b}_買進重疊÷{b}"] = inter / len(Bb) if Bb else None
        d[f"{a}vs{b}_{b}被換掉"] = (len(Bb - A) / len(Bb)) if Bb else None
        ov = res[f"ov_{a}_{b}"][x:y + 1].astype(float) / N
        d[f"{a}vs{b}_等權持股重疊_平均"] = float(ov.mean())
        d[f"{a}vs{b}_等權持股重疊_中位"] = float(np.median(ov))
        d[f"{a}vs{b}_逐筆相同"] = bool(A == Bb)
    return d


def step_report():
    OUTD = out_dir()
    os.makedirs(OUTD, exist_ok=True)
    reg = check_reg()
    summ = {"時間": TIME, "登錄": reg, "發號": "裁定線 seq501 §三", "乾跑": "價格全 1、毛報酬 0；⛔ 無任何報酬數字", "世界": {}}
    if GROUPS == "industry":
        summ["時間"] = TIME_IND
        summ["分群"] = "主段 ＝ 產業 seq112 分群檔（clusters_by_year＋group_month_flags）；早年 ＝ 自建 v2（README 10 條、只描述）；裁定 seq502 §二"
    cells, monthly, candy, ovy, hdist, gyear = [], [], [], [], [], []
    md = []
    for wn in ("main", "early"):
        P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
        Gp = pickle.load(open(os.path.join(WORK, f"groups_{wn}{sfx()}.pkl"), "rb"))
        SIM = pickle.load(open(os.path.join(WORK, f"sim_{wn}{sfx()}.pkl"), "rb"))
        S = Gp["S"]; cal = P["cal"]
        gyear += Gp["GY"]
        W = {"G4": Gp["G4"], "IG閘": P["gate"], "seq111": Gp.get("seq111")}
        if GROUPS == "industry":
            W["旗標來源"] = Gp["來源"]
            W["★"] = Gp.get("star")
            if wn == "main":
                summ["一致率"] = Gp["agree"]["summary"]
                for nm, df in Gp["agree"]["tables"].items():
                    df.to_csv(os.path.join(OUTD, f"{nm}.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
        # 候選逐年
        for st in STRATS:
            s = S[S["gated"]] if STRATS[st]["gate"] else S
            H = STRATS[st]["H"]
            s = s[s[f"xpos_H{H}"].notna() & (s[f"xpos_H{H}"] >= 0)]
            yy = [cal[int(e)].year for e in s["entry_pos"]]
            for Y, g in s.groupby(yy):
                candy.append({"世界": wn, "策略": st, "年": Y, "候選": len(g), "族群轉強": int(g["grp"].sum()), "族群轉強比例": float(g["grp"].mean()),
                              "另一讀法族群轉強比例": float(g["grp_alt"].mean()), "不在產業母體比例": float((~g["in_univ"]).mean())})
                if GROUPS == "industry":
                    candy[-1].update({"舊自建族群轉強比例": float(g["grp_self"].mean()), "舊自建對本版旗標一致率": float((g["grp_self"] == g["grp"]).mean())})
            W[f"{st}_候選"] = {"候選": int(len(s)), "族群轉強比例": float(s["grp"].mean()), "不在產業母體比例": float((~s["in_univ"]).mean()),
                             "兩讀法旗標一致率": float((s["grp"] == s["grp_alt"]).mean()),
                             "seq377 恆真恆假": ("恆真" if s["grp"].mean() >= 0.95 else ("恆假" if s["grp"].mean() <= 0.05 else "否"))}
            if GROUPS == "industry":
                W[f"{st}_候選"].update({"舊自建族群轉強比例": float(s["grp_self"].mean()), "兩讀法旗標不同筆數": int((s["grp"] != s["grp_alt"]).sum())})
            # 每月表
            rs = [x for x in SIM if x["st"] == st]
            mo = pd.Series([cal[int(e)].strftime("%Y-%m") for e in s["entry_pos"]])
            cm = s.groupby(mo.to_numpy())["grp"].agg(["count", "sum"])
            months = sorted(set(cal[P["w0"]:P["w1"] + 1].strftime("%Y-%m")))
            N = STRATS[st]["N"]
            mpos = pd.Series(np.arange(len(cal)), index=cal.strftime("%Y-%m"))
            calm = np.asarray(cal.strftime("%Y-%m"))
            MC = {v: [Counter(calm[t] for t, _ in x["ver"][v]["buys"] if t < len(calm)) for x in rs] for v in VERS}
            for mth in months:
                ps = mpos.loc[[mth]].to_numpy() if mth in mpos.index else np.array([], int)
                ps = ps[(ps >= P["w0"]) & (ps <= P["w1"])]
                row = {"世界": wn, "策略": st, "月": mth, "原版候選": int(cm["count"].get(mth, 0)), "族群轉強候選": int(cm["sum"].get(mth, 0))}
                for v in VERS:
                    row[f"{v}買進"] = float(np.mean([c_.get(mth, 0) for c_ in MC[v]]))
                hv = [x["ver"]["只買版"]["hc"][ps].mean() for x in rs] if len(ps) else [np.nan]
                row["只買版平均持股"] = float(np.mean(hv)); row["只買版空格比例"] = float(1 - np.mean(hv) / N)
                monthly.append(row)
            # 段 cell
            for sg, (x, y) in seg_bounds(P, wn).items():
                per = [per_seed_cell(r_, P, x, y, N) for r_ in rs]
                keys = per[0].keys()
                row = {"世界": wn, "策略": st, "段": sg, "段起": str(cal[x].date()), "段尾": str(cal[y].date()), "種子數": len(per)}
                for k in keys:
                    vals = [p[k] for p in per]
                    if isinstance(vals[0], bool):
                        row[k] = f"{sum(vals)}/{len(vals)}"
                    elif st == "營量":
                        row[k] = vals[0]
                    else:
                        qq = q(vals); row[k] = qq["中位"]; row[k + "_p10"] = qq["p10"]; row[k + "_p90"] = qq["p90"]; row[k + "_r0"] = vals[0]
                cells.append(row)
                # 只買版持有檔數分布
                bins = [0, 1, N // 4 + 1, N // 2 + 1, 3 * N // 4 + 1, N, N + 1]
                labs = ["0", f"1～{N // 4}", f"{N // 4 + 1}～{N // 2}", f"{N // 2 + 1}～{3 * N // 4}", f"{3 * N // 4 + 1}～{N - 1}", f"{N}"]
                for v in VERS:
                    hcs = np.concatenate([r_["ver"][v]["hc"][x:y + 1] for r_ in rs])
                    h, _ = np.histogram(hcs, bins=bins)
                    hdist.append({"世界": wn, "策略": st, "段": sg, "版": v, **{f"持有{l}": float(c / len(hcs)) for l, c in zip(labs, h)}})
                # 只買 × 族群條件簡單集合（seq377）
                jac = []
                fl = dict(zip(zip(s["entry_pos"].astype(int), s["sid"]), s["grp"]))
                for r_ in rs:
                    A = {(t, s_) for t, s_ in r_["ver"]["只買版"]["buys"] if x <= t <= y}
                    Bb = {(t, s_) for t, s_ in r_["ver"]["原版"]["buys"] if x <= t <= y and fl.get((t, s_), False)}
                    jac.append(len(A & Bb) / len(A | Bb) if (A | Bb) else np.nan)
                row["只買版vs原版∩族群轉強_Jaccard"] = float(np.nanmedian(jac))
            # 逐年持股重疊
            yrs = cal.year.to_numpy()
            for Y in sorted(set(yrs[P["w0"]:P["w1"] + 1])):
                ps = np.flatnonzero((yrs == Y) & (np.arange(len(cal)) >= P["w0"]) & (np.arange(len(cal)) <= P["w1"]))
                row = {"世界": wn, "策略": st, "年": int(Y)}
                for a, b in PAIRS:
                    v_ = [x[f"ov_{a}_{b}"][ps].mean() / N for x in rs]
                    row[f"{a}vs{b}_等權持股重疊"] = float(np.median(v_))
                ovy.append(row)
            W[f"{st}_閘"] = {"G2 prio全0＝原版": [x.get("G2") for x in rs if "G2" in x],
                            "G3 逐日買進數不符（全部版本×種子合計）": int(sum(x["ver"][v]["g3"] for x in rs for v in VERS))}
            if GROUPS == "industry":
                m16 = (s["cy"] == 2016).to_numpy()
                key = set(zip(s["entry_pos"].to_numpy(int)[m16], s["sid"].to_numpy(str)[m16]))
                nb = [sum(1 for t, s_ in r_["ver"]["原版"]["buys"] if (t, s_) in key and P["w0"] <= t <= P["w1"]) for r_ in rs]
                W[f"{st}_分群年2016（★無分群⇒旗標0）"] = {"候選列": int(m16.sum()), "段內進場候選": int((m16 & (s["entry_pos"].to_numpy(int) >= P["w0"])).sum()),
                                                  "原版段內買進_中位": float(np.median(nb)), "原版段內買進_r0": int(nb[0])}
        # G0：乾跑原版營量 vs 正式 audit_seed0
        if wn == "main":
            F0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}, usecols=["t", "sid", "side"])
            fb = {(int(t), s) for t, s, sd in zip(F0["t"], F0["sid"], F0["side"]) if sd == "buy"}
            yl = [x for x in SIM if x["st"] == "營量"][0]
            db = set(yl["ver"]["原版"]["buys"])
            W["G0 乾跑原版營量 vs 正式 audit_seed0"] = {"正式買進": len(fb), "乾跑買進": len(db), "相同": len(fb & db),
                                                  "只在正式": len(fb - db), "只在乾跑": len(db - fb)}
        summ["世界"][wn] = W
    # G5 策略鎖
    pr = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    summ["G5 策略鎖"] = {"exit": pr.returncode, "out": (pr.stdout + pr.stderr).strip()[-500:]}
    summ["日報酬相關"] = "算得出（兩版權益逐日皆有、段內可配對；本階段乾跑不算，正式跑報）"
    summ["持股重疊口徑"] = "等權槽（每檔 1/N）；金額權重需價格，留正式跑"
    for nm, rows in (("cells", cells), ("monthly", monthly), ("cand_yearly", candy), ("overlap_yearly", ovy), ("holddist", hdist), ("groups_yearly", gyear)):
        pd.DataFrame(rows).to_csv(os.path.join(OUTD, f"{nm}.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    json.dump(summ, open(os.path.join(OUTD, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    write_md(summ, cells, candy, gyear, hdist, OUTD)
    log("[report] 完成")


def _f(x, pct=True, d=1):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{100 * x:.{d}f}%" if pct else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def md_industry_head(summ):
    A = summ["一致率"]
    L = ["主段旗標 ＝ 產業 seq112 分群檔（clusters_by_year＋group_month_flags）；早年 ＝ 自建 v2（README 口徑 10 條、只描述、標「自建」）；"
         "裁定 seq502：優先版兩格撤判（只描述、標「等同原版」、N_組合 ＋2）；只買版兩格照 seq2 判定", "",
         "## 逐檔一致率（自建舊版 對 產業；門檻 95%）", "",
         "| 項 | 分母 | 一致率 | 過 95%？ |", "|---|---|---|---|"]
    for r in A["一致率三項"]:
        L.append(f"| {r['項']} | {r['分母']} | {_f(r['一致率'])} | {'是' if r['一致率'] >= 0.95 else '否'} |")
    L += ["", "裁定 seq502：< 95% ⇒ 以產業版為準、自建版只描述（本表即產業版）。", "",
          "## 差異來源（同一批候選旗標，各版對產業的相同率；主段）", "", "| 版 | 營量 | 營飆 | 說明 |", "|---|---|---|---|"]
    for r in A["差異來源"]:
        L.append(f"| {r['版']} | {_f(r['營量'])} | {_f(r['營飆'])} | {r['說明']} |")
    L += ["", f"讀入驗證：{A['產業檔讀入']}", f"★ 條目：{A['star']}", ""]
    return L


def write_md(summ, cells, candy, gyear, hdist, OUTD=None):
    OUTD = OUTD or OUT
    L = ["# 營量／營飆加族群營收也轉強（只買版、優先版）頻率表（乾跑、⛔ 無報酬）", "",
         f"登錄 台股 seq2 sha {summ['登錄']['sha16']}（{summ['登錄']['bytes']} B，相符）｜發號 裁定 seq501 §三｜回測線計算子代理 {TIME}", "",
         "額外策略、與正式營量營飆分開；正式規則不動｜想法來自產業 seq111，看過同期結果才提｜營量、營飆本身已看過結果", "",
         "營飆數字 ＝ 200 顆種子中位〔p10～p90〕；營量 ＝ r0 一條。持股重疊 ＝ 等權槽（金額權重留正式跑）；日報酬相關：算得出、本階段不算。", ""]
    if GROUPS == "industry":
        L[0] = "# 營量／營飆加族群營收也轉強（只買版、優先版）頻率表【產業分群版】（乾跑、⛔ 無報酬）"
        L[2] = L[2].replace(TIME, TIME_IND) + "｜分群 裁定 seq502 §二、產業 seq112"
        L += md_industry_head(summ)
    for c in cells:
        st = c["策略"]; sp = st == "營飆"

        def g(k):
            v = c.get(k)
            s = _f(v)
            if sp and c.get(k + "_p10") is not None:
                s += f"〔{_f(c[k + '_p10'])}～{_f(c[k + '_p90'])}〕"
            return s
        tag = ""
        if GROUPS == "industry":
            tag = "【產業分群】" if c["世界"] == "main" else "【自建 v2、只描述】"
        L += [f"## {c['世界']}｜{st}｜{c['段']}（{c['段起']}～{c['段尾']}）{tag}", "",
              "| 項 | 原版 | 只買版 | 優先版 |", "|---|---|---|---|",
              f"| 買進筆數 | {_f(c['原版_買進'], False)} | {_f(c['只買版_買進'], False)} | {_f(c['優先版_買進'], False)} |",
              f"| 平均持股 | {_f(c['原版_平均持股'], False)} | {_f(c['只買版_平均持股'], False)} | {_f(c['優先版_平均持股'], False)} |",
              f"| 空格比例 | {g('原版_空格比例')} | {g('只買版_空格比例')} | {g('優先版_空格比例')} |",
              f"| 空倉月／月數 | {c['原版_空倉月']}/{c['原版_月數']} | {c['只買版_空倉月']}/{c['只買版_月數']} | {c['優先版_空倉月']}/{c['優先版_月數']} |",
              f"| 有效月數（對 24） | {c['原版_有效月數']} | {c['只買版_有效月數']} | {c['優先版_有效月數']} |",
              f"| 名額不足日比例 | {g('原版_名額不足日比例')} | {g('只買版_名額不足日比例')} | {g('優先版_名額不足日比例')} |", "",
              "| 配對 | 買進重疊÷前者 | 買進重疊÷後者 | 後者被換掉 | 等權持股重疊 平均 | 中位 | 逐筆相同 |", "|---|---|---|---|---|---|---|"]
        for a, b in PAIRS:
            k = f"{a}vs{b}"
            L.append(f"| {a} vs {b} | {g(k + '_買進重疊÷' + a)} | {g(k + '_買進重疊÷' + b)} | {g(k + '_' + b + '被換掉')} | "
                     f"{g(k + '_等權持股重疊_平均')} | {g(k + '_等權持股重疊_中位')} | {c[k + '_逐筆相同']} |")
        L += ["", f"只買版 vs「原版買進 ∩ 族群轉強」Jaccard：{_f(c.get('只買版vs原版∩族群轉強_Jaccard'))}", ""]
    L += ["## 候選與族群", ""]
    for wn, W in summ["世界"].items():
        for st in STRATS:
            cd = W[f"{st}_候選"]
            L.append(f"- {wn}｜{st}：候選 {cd['候選']}、族群轉強 {_f(cd['族群轉強比例'])}、不在產業母體 {_f(cd['不在產業母體比例'])}、"
                     f"兩讀法一致 {_f(cd['兩讀法旗標一致率'])}、恆真恆假：{cd['seq377 恆真恆假']}；閘 {W[f'{st}_閘']}")
        L.append(f"- {wn} G4（自算 24 月新高 vs 面板）：{W['G4']}")
        if GROUPS == "industry":
            L.append(f"- {wn} 旗標來源：{W['旗標來源']}；★ 筆數：{W.get('★')}")
            for st in STRATS:
                L.append(f"- {wn}｜{st}：舊自建族群轉強 {_f(W[f'{st}_候選']['舊自建族群轉強比例'])}；分群年兩讀法旗標不同 {W[f'{st}_候選']['兩讀法旗標不同筆數']} 筆；"
                         f"分群年 2016：{W[f'{st}_分群年2016（★無分群⇒旗標0）']}")
        elif W.get("seq111"):
            L.append(f"- seq111 彙總一致（近似重建，⛔ 非逐檔）：{W['seq111']}")
        if W.get("G0 乾跑原版營量 vs 正式 audit_seed0"):
            L.append(f"- G0：{W['G0 乾跑原版營量 vs 正式 audit_seed0']}")
    L += ["", f"G5 策略鎖：{summ['G5 策略鎖']}", "",
          "早年：只描述；含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市", "",
          "描述，不是買賣建議"]
    open(os.path.join(OUTD, "結果.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=["world", "groups", "sim", "report", "reg"])
    ap.add_argument("--world", choices=["main", "early"])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--groups", choices=["self", "industry"], default="self")
    a = ap.parse_args()
    global GROUPS
    GROUPS = a.groups
    os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(WORK, "run.log")
    log(f"===== {a.step} {a.world or ''}{'' if GROUPS == 'self' else ' --groups ' + GROUPS}｜登錄 {check_reg()}")
    if a.step == "world":
        step_world(a.world, a.procs)
    elif a.step == "groups":
        if GROUPS == "industry":
            step_groups_industry(a.world, a.procs)
        else:
            step_groups(a.world, a.procs)
    elif a.step == "sim":
        step_sim(a.world, a.procs)
    elif a.step == "report":
        step_report()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""PREREG最笨交易法 seq1（台股策略線 登錄 sha c675b705610a6eed，2026-10-14 20:58；裁定 seq350 §六、seq351 發號 N_組合 ＋1；
只判 F1、F2 對照並報、F3～F6 描述不計 N；不是事後重切）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDumb [--procs 4]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDumb_check [--procs 4]

⭐ 讀法寫死：2026-10-14 21:18～21:24 之間（台北，WSL TZ=Asia/Taipei date 21:18 之後寫檔、21:25 煙霧測試之前）；寫死前 ⛔ 沒算任何本件數字
   看過的：登錄全文 seq1、裁定 seq350、seq351、既有程式 researchExit5／researchAddOn／researchTopPrevTW／researchYL_integrate／researchYLmargin（等效獨立）／
   research11（load_bars、limit_flags、fixed_exit、simulate_mtm）／patterns.Frame；⚠ 回測線看過 §五 列的相鄰結果；⛔ 沒看過本組合任何輸出

═══ 讀法（Z 標；登錄沒寫清楚、執行者補的都在這裡）═══
 Z0 判定（登錄 §四）：F1 每段對 0050 同段：合格（年化 ＞ 0050 且 年化÷|回落| ≥ 0050）／另列（只贏年化）／不合格；整件：探索、確認都合格 ⇒ 合格（早年不合格 ⇒ 最多暫定）；
    兩段都「合格或另列」⇒ 另列；其餘 ⇒ 不合格。F2 同法標籤並報、⛔ 不換主判；F3～F6 只描述。退化（Z15）⇒「退化、照 seq325 不判」（標籤仍照報）
 Z1 世界（⛔ 不另寫資料層）：主 ＝ rerun17 快照 H2D（edc6f8002f；日曆 2015-01-05～2026-09-24）；早年 ＝ ~/earlydata/eotc_f65bb03e11（上市＋上櫃，2004-02-11～2014-12-31）
    ＝ researchAddOn／researchExit5／researchTopPrevTW 同一組版面；逐股矩陣 ＝ researchRevLimitUp.World 快取 ~/rluwork/world_{main,early}.pkl
    （UG.gate3 GATE_V2 開 ∩ 四碼、首碼 1～9、非 91xx ⇒ 排 -DR、ETF、創新板；含已下市；c ＝ 還原收盤 ffill、o、trd、upl（開盤漲停鎖死：開盤＝漲停價 ∧ 最低＝開盤）、
    dnl（開盤跌停鎖死）、pv ＝ UG.pit_valid）；閘：本次 UG.gate3(GATE_V2)∩四碼 名單 vs 快取、快取收盤／開盤 vs research11.load_bars（有效 K 棒，相對差 ≤ 1e−9）
    早年 reduce_v2（seq341 §六，同 researchAddOn U1／U4）：reduce_v2 版面只有上市本體 ⇒ 早年用上市＋上櫃版面，reduce_v2 的減資事件（上市官方＋上市偵測 2004～2010＋
    上櫃早年偵測＋未解釋跳動 22 筆）＋ R8 事件全部併入早年壞根（researchAddOn.early_extra_bad）
 Z2 有效 K 棒與漲停（登錄 §一 ①）：research11.load_bars（有成交的日子 ＝ 有效 K 棒；up ＝ research11.limit_flags：未還原收盤 ＝ 前一根有效 K 棒未還原收盤 ×(1＋上限)
    依升降單位往下取；上限 2015-06-01 前 7%、之後 10%；還原事件日、2015-01-12 後上市前 5 根不判）⇒ 既有漲停判定函式，⛔ 不另寫
    ① ＝ 日曆位置 [t−9, t] 內的有效 K 棒至少 1 根 up；排除 ＝ 同窗內有「連續 3 根有效 K 棒都 up」（三根都在窗內）
 Z3 壞根（seq335 全線：缺口 ≥ 5 日即壞根）：主 ＝ ~/crashwork/bad_main.pkl（load_bars 壞根 ∪ adj 減資／面額）∪ 本次 load_bars next_bad；快取沒有的股 ⇒ researchAddOn.extra_stock；
    早年另加 Z1 的 reduce_v2＋R8；壞根日曆位置 ⇒ 該日或之後第一根有效 K 棒 ＝ 壞 K 棒（價格在它之前斷開）
    訊號 t（K 棒 k）要 [k−20, k＋1] 沒有壞 K 棒（＝ 正式訊號「k−20 起無壞根」，含進場根）；MA20 要 (k−19, k] 沒有壞 K 棒
    持有中：進場根之後第一個壞 K 棒 kb ⇒ 任何在 kb（含）以後才會發生的賣出 ⇒ 改成 kb−1 那根收盤強制賣（引擎記在次一日曆日、用該收盤；與 stop_force 同式）
    月 MACD 不跨壞根：月收盤序列在壞 K 棒處重新起算（Z5）
 Z4 母體（登錄 §三）：快取股 ∧ pv[t] ∧ patterns.Frame.gate[t]（營量閘同一條：含 t 的 20 個交易日都有成交 ∧ t−20～t−1 日均量 ≥ 500 張 ＝「t 前一日 20 日均量」）；
    t 必為有效 K 棒
 Z5 ②（登錄 §一 ②）：月收盤 ＝ 該月最後一根有效 K 棒還原收盤；「最近一個已收完的月」M* ＝ t 若是日曆上該月最後一個交易日（t 收盤後該月已收完）⇒ 當月，否則上月；
    資料尾那天一律當「未收完」；MACD ＝ EMA12、EMA26（adjust=False、以段內第一個月收盤起算）、DIF ＝ EMA12 − EMA26、DEA ＝ DIF 的 EMA9；
    段 ＝ 兩個壞 K 棒之間（月份不連續也斷）；M* 要與 t 在同一段、且是段內第 35 個（含）以後的月收盤；多方 ＝ DIF ＞ DEA
    ⚠ 主世界資料 2015-01 起 ⇒ 最早 2017-11 才有 35 個月收盤 ⇒ 探索段 2017-03～2017-11 沒有任何訊號（照登錄字面，現金）；早年 2004-02 起 ⇒ 2006-12 前沒有訊號
      ⇒ 另報「MACD 可算起」窗（描述、⛔ 不判，Z16）
 Z6 ③（F1）：MA20 ＝ 含 t 的 20 根有效 K 棒還原收盤平均；附近 ＝ 最低 ≤ MA20×1.02 ∧ 收盤 ≥ MA20；紅K ＝ 收盤 ＞ 開盤（同日還原因子相同 ⇒ 與原始開收同號）；
    帶量 ＝ 原始成交股數[t] ＞ 1.5 × 前 20 根有效 K 棒（t−20～t−1）原始成交股數平均
 Z7 F2（相對版）：ATR20 ＝ t 往前 20 根真實區間的簡單平均（TR ＝ max(高, 前收) − min(低, 前收)，同 researchExit5.atr20）；附近 ＝ 最低 ≤ MA20 ＋ 0.5×ATR20 ∧ 收盤 ≥ MA20
    （只把 2% 換成相對門檻，「收盤 ≥ MA20」照 F1 留著）；帶量 ＝ 量[t] ≥ np.percentile(前 60 根量, 80)（線性），且 [k−60, k] 無壞 K 棒；分批 ＝ 報酬 ≥ 8×、13×（ATR20[t] ÷ 收盤[t]）
 Z8 進場（登錄 §一 ③、§三）：e ＝ t＋1（日曆）；e 要是該股的下一根有效 K 棒 ∧ trd ∧ 開盤有效 ∧ ⛔ 非開盤漲停鎖死（upl）⇒ 才是候選；買不到的照實記（比例必報）
    ⚠ 引擎 tradable 開關不能與 held_map 同開 ⇒ 買不到的訊號在進引擎前剔除 ⇒ 該日其他候選可以補上（⛔ 不是「名額持現金」），照記
    檔數與權重 ＝ 正式引擎 research11.simulate_mtm（⛔ 不改）：10 槽、新部位 min(前一日權益 ÷ 10, 現金)、候選多於空槽 ⇒ 抽籤 default_rng(1000)（＝ 營飆 v1 r0）、
    同一檔同時只持一筆（held_map：每筆訊號自己的價格鍵「代號#進場位置」、已持有以代號判）、賣後可再進（引擎同日先出後進）；sig 依 (entry_pos, 代號) 排序
 Z9 出場 ④（整筆）：持有第 1、2 個交易日 ＝ 進場根 ke、ke＋1；a ＝ 收盤[ke] ＜ MA20 或 收盤[ke＋1] ＜ MA20 ⇒ 次一根可賣開盤全賣；
    b ＝ 第一個 d ≥ ke＋2 使 d、d＋1、d＋2、d＋3 四根收盤都 ＜ MA20 ⇒ d＋3 收盤後判、次一根可賣開盤（＝ d＋4）賣剩下全部
    可賣開盤 ＝ 判斷根之後第一根「trd ∧ 開盤有效 ∧ 非開盤跌停鎖死（dnl）」的有效 K 棒（鎖跌停 ⇒ 順延）；
    賣不到就碰到壞根 ⇒ Z3 強制；股票之後再也沒成交（下市／停止交易）⇒ 最後一根收盤賣（記在次一日曆日，＝ stop_force 同式）；到資料尾仍持有 ⇒ 以資料尾收盤計值（T1 墊根）
 Z10 分批 ⑤：r_j ＝ 收盤[j] ÷ 買價 − 1（還原），j ≥ ke（進場當天收盤起）；第一個 r ≥ +30%（F2：8×ATR%）的收盤 ⇒ 次一根可賣開盤賣原始股數 1/3；≥ +50%（13×）⇒ 再賣 1/3；
    同一根收盤兩條都到 ⇒ 同一個開盤賣 2/3；每段一次；賣出時點要早於整筆出場（同一個開盤 ⇒ 併進整筆）
    賣掉的部分凍結在賣價（現金、報酬 0、⛔ 不拿去買別檔）、名額到全部出清才釋出、整筆來回成本 0.585% 在最後出清時按買進金額一次扣（＝ researchExit5 X1 同式）
 Z11 F3 ＝ F1 拿掉 ⑤；F4 ＝ F1 拿掉 ②；F5 ＝ F1 拿掉 ①；F6 ＝ F1 進場、第 60 根有效 K 棒收盤賣（research11.fixed_exit：進場根算第 1 根、xpos ＝ 出場根 ＝ 營量／營飆正式口徑），
    無分批；途中壞根、下市、資料尾照 Z9
 Z12 滑價（登錄 §三「另報」）：買價 ×1.005、每一筆賣價（含強制、資料尾計值）×0.995；其餘同；描述並報
 Z13 段（登錄 §三）：主窗一條權益；探索 2017-03-02～2021-12-30、確認 2022-01-03～資料尾 2026-09-24；早年 2005 第一個交易日～2014-12-31；
    年化、回落 ＝ rerun17.win_metrics；0050 ＝ 同窗 rerun17.bench_row（還原收盤，同版面）
 Z14 隨機進場（登錄 §四 ②）：F1 實際買進的每一個進場日 e（引擎 audit），買了 k 檔 ⇒ 從 t ＝ e−1 的同日母體（Z4 ∧ Z3 訊號窗 ∧ Z8 可買，⛔ 不看 ①②③）
    不重複抽 k 檔（default_rng([20261014, 世界, i])，母體依代號排序），出場照 F1（含分批），同引擎同參數（default_rng(1000)）；200 次；
    p ＝ 隨機版 年化÷|回落| ≥ F1 的比例（另報年化 ≥ F1 的比例）；各段各報
 Z15 退化（seq325：先寫 degeneracy.json 附台北時間，再算任何報酬）：探索段（早年另報）平均持股 ＜ 3 或 現金比例 ＞ 30%（分批凍結的錢算現金）⇒ 退化
    同檔先報 F2 ATR% 分布（登錄 §二：名單股 ＝ F1 訊號列與 F2 訊號列的 ATR20÷收盤 中位、四分位；只看分布）
 Z16 必報（登錄 §六）定義：換手 ＝ 段內買進金額 ÷ 段內平均權益 ÷ 年；成本／年 ＝ 換手 × 0.585%；平均持股 ＝ 逐日持股檔數平均；現金比例 ＝ 1 − 段內平均（持股市值 − 凍結）÷ 權益；
    平均持有天數 ＝ 最後出清日 − 買進日（日曆交易日位置；另報按股數加權）；
    等效獨立檔數 ＝ researchYLmargin.eff_n 同式：段內每個有買進的日子收盤持股 N 檔、ρ ＝ 各檔前 60 個交易日收盤日報酬兩兩相關平均（共同 ＜ 40 天或零變異略過），N ÷ (1＋(N−1)ρ)，段內平均；
    每年：訊號數（剔可買前）、候選數、筆數（依買進年）、勝率（g − 成本 ＞ 0）、平均賺賠比（賺的筆平均 ÷ |賠的筆平均|）；
    ⑤ 觸發比例 ＝ 實際交易中真的賣了第一段／第二段的比例；④a ＝ 實際交易中整筆出場是 a 的比例（第 1 天、第 2 天分報）；
    賣出點（只算規則賣出的整筆出場、開盤賣）：賣價 ÷ 賣出根起 60 根有效 K 棒最高收盤 − 1（窗不滿 60 根或遇壞根截斷不計）、
    賣後 60 根內最高收盤 ＞ 持有期（ke～判斷根）最高收盤的比例（researchExit5.post60 同口徑）⇒ 對使用者措辭照 seq343（⛔ 不稱最高點、頂部）；
    開盤鎖漲停買不到 ＝ 訊號（剔可買前）中 e 開盤漲停鎖死的比例（另報 e 沒成交）；觀察名單內處置股比例 ＝ 母體 ∧ ① 的股日中，t 在處置期間內（meta/disposal.csv 普通股）的比例
    （另報 F1 訊號、F1 實際買進）；窗尾仍持有（T1）筆數；描述窗「MACD 可算起」：段首改成全母體第一個 MACD 可算日（0050 同窗），⛔ 不判
 結果句必附：「原文沒給的『附近』『帶量』『MACD 參數』由本線定（2%、1.5 倍、12／26／9）」「與爆量突破、均線出場、分批停利等已測項重疊，見 §五」；
   早年另附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註
輸出 backtest/resultsDumb/：degeneracy.json（先寫）、Dumb.json、Dumb_main.csv、rows_{世界}_{格}.csv.gz、eq_{世界}.npz、random_{世界}.csv.gz、run.log；大檔 ~/dumbwork/
── 事後註（寫死之後、照實記；讀法沒改）──
 ① 21:25 跑過兩次煙霧測試（DUMB_QUICK：只取每 10 檔一檔、隨機 3 次，輸出 /tmp/dumb_quick；數字不是本件結果）；之間只修程式錯（rolling 陣列唯讀）、
    拿掉引擎 log 參數（營飆 v1 抽籤版本來就不傳）；煙霧測試之後 ⛔ 沒改任何計算
 ② 21:31 全跑交件（656 秒）。查核發現抽樣 ~1.7 萬列出場中 10 列與查核不同，全是「收盤 ＝ MA20」的浮點平手（rolling 平均與逐段平均差 1 ulp）；
    ⛔ 沒改主程式計算，照記（組合層權益查核用主程式的列重算，差 ≤ 4e−15）
 ③ 描述（跑完後另算、⛔ 不判、⛔ 沒改本檔計算）：F1 探索段退化是資料起點造成（2017-03～11 月 MACD 不可算 ⇒ 全現金）；
    「MACD 可算起」窗 2017-11-30～2021-12-30 平均持股 8.62、現金 22.9%（不退化）；早年 2006-12-29 起 8.32 檔、22.7%
 ④ 讀法寫死時間更正：寫檔時預填「21:40」是錯的（比實際跑還晚）；實際是 21:18～21:24 之間寫死、21:25 煙霧測試、21:31 全跑寫 degeneracy.json；
    已把 TIME 與 Dumb.json 的「讀法寫死」欄改成實際區間（只改時間字樣，⛔ 沒動任何數字）
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
from backtest import rerun17 as RR                          # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-14 21:18～21:24（台北）"
REG_SHA = "c675b705610a6eed"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsDumb"
WORK = os.path.expanduser("~/dumbwork")
NRAND = 200
if os.environ.get("DUMB_QUICK"):                                 # 煙霧測試（不是交件）
    NRAND, OUT, WORK = 3, "/tmp/dumb_quick", "/tmp/dumb_quick/work"
COST = R.COST
SLIP = 0.005
NS = 10
SEED_ENG = RR.P10_SEED0 + 0                                      # 1000 ＝ 營飆 v1 r0
RSEED = 20261014
WID = {"主": 0, "早年": 1}
WORLDS = {"主": {"data": RR.H2D, "part": "main"}, "早年": {"data": RA.EOTC, "part": "early"}}
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = ("F1", "F2", "F3", "F4", "F5", "F6")
EXIT_OF = {"F1": "M", "F2": "M2", "F3": "N", "F4": "M", "F5": "M", "F6": "H60"}
SIG_OF = {"F1": "F1", "F2": "F2", "F3": "F1", "F4": "F4", "F5": "F5", "F6": "F1"}
CNAME = {"F1": "原文固定數字（主判）", "F2": "相對版（對照）", "F3": "拿掉分批減碼", "F4": "拿掉月MACD", "F5": "拿掉漲停名單", "F6": "F1進場、固定抱60根"}
TH1 = (0.30, 0.50)
TH2 = (8.0, 13.0)
DEG_HOLD, DEG_CASH = 3.0, 0.30
SENT = ["原文沒給的『附近』『帶量』『MACD 參數』由本線定（2%、1.5 倍、12／26／9）", "與爆量突破、均線出場、分批停利等已測項重疊，見 §五"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
TRUETOP = "真頂訊號（多半在最高點之前）"
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


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
def load_world(wn, log):
    cfg = WORLDS[wn]; data = cfg["data"]; D.DATA = data
    cal = D.load_calendar(); n0 = len(cal)
    st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st); U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
    mk = dict(zip(U["stock_id"], U["market"]))
    Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{cfg['part']}.pkl"), "rb"))
    if Z["c"].shape[1] != n0:
        raise SystemExit(f"⛔ {wn} 快取日曆長 {Z['c'].shape[1]} ≠ {n0}")
    sids = list(Z["sids"]); ix = {s: i for i, s in enumerate(sids)}
    run_sids = sids[::10] if os.environ.get("DUMB_QUICK") else sids          # 煙霧測試只跑每 10 檔一檔（數字不是本件結果）
    gate = {"UG.gate3(GATE_V2)∩四碼 檔數": int(len(U)), "快取檔數": len(sids),
            "名單差（本次有、快取沒有）": sorted(set(U["stock_id"]) - set(sids))[:20],
            "名單差（快取有、本次沒有）": sorted(set(sids) - set(U["stock_id"]))[:20]}
    S = len(sids)
    BADPOS = {}; bad_info = {}
    B = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{cfg['part']}.pkl"), "rb"))
    nocache = []
    for s in sids:
        if s in B:
            a, b = B[s]; BADPOS[s] = set(int(x) for x in a) | set(int(x) for x in b)
        else:
            nocache.append(s)
            _, bad = RA.extra_stock(s, mk.get(s, "twse"), data, cal); BADPOS[s] = set(int(x) for x in np.flatnonzero(np.asarray(bad, bool)[:n0]))
    D.DATA = data
    bad_info["crashwork 沒有、現場補"] = nocache[:20]; bad_info["現場補 檔數"] = len(nocache)
    bad_info["壞根股日（主來源）"] = int(sum(len(v) for v in BADPOS.values()))
    if wn == "早年":
        Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
        if not (len(Wa["cal"]) == n0 and (Wa["cal"] == cal).all()):
            raise SystemExit("⛔ 早年 addonwork 日曆 ≠ 版面日曆")
        EX, cnt = RA.early_extra_bad(Wa, log)
        n_ = bad_info["壞根股日（主來源）"]
        for s, ks in EX.items():
            if s in BADPOS:
                BADPOS[s] |= set(int(k) for k in ks)
        bad_info["早年另加（reduce_v2＋R8）來源"] = cnt
        bad_info["早年另加新增股日"] = int(sum(len(v) for v in BADPOS.values())) - n_
    D.DATA = data
    bench = np.asarray(RR.load_bench(cal), float)
    bref = np.asarray(pickle.load(open(os.path.join(RA.WORK, f"world_{wn}.pkl"), "rb"))["bench"], float)
    gate["0050 ＝ addonwork 世界 bench（最大相對差）"] = float(np.nanmax(np.abs(bench[:len(bref)] / bref[:len(bench)] - 1.0)))
    disp = D.load_disposal_intervals()
    C = np.asarray(Z["c"], float); BAR = np.asarray(Z["bar"], bool)
    SF = {}
    for s, i in ix.items():
        b = np.flatnonzero(BAR[i])
        if len(b) and b[-1] < n0 - 1:
            SF[s] = int(b[-1])
    MID = (cal.year * 12 + cal.month).to_numpy()
    is_me = np.zeros(n0, bool); is_me[:-1] = MID[1:] != MID[:-1]                # 資料尾那天一律當未收完（Z5）
    W = {"name": wn, "data": data, "cal": cal, "n0": n0, "NP": n0 + 1, "sids": sids, "ix": ix, "mk": mk, "names": dict(zip(st["stock_id"], st["name"])),
         "C": C, "O": np.asarray(Z["o"], float), "BAR": BAR, "PV": np.asarray(Z["pv"], bool), "TRD": np.asarray(Z["trd"], bool)[:, :n0],
         "UPL": np.asarray(Z["upl"], bool)[:, :n0], "DNL": np.asarray(Z["dnl"], bool)[:, :n0], "BADPOS": BADPOS, "bench": bench, "disp": disp, "SF": SF,
         "MID": MID, "is_me": is_me, "gate": gate, "bad_info": bad_info, "run_sids": run_sids}
    segp = {}
    for sg, (a, b) in SEGS[wn].items():
        x = int(cal.searchsorted(pd.Timestamp(a)))
        y = n0 - 1 if b is None else int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
        segp[sg] = (x, y)
    W["segp"] = segp
    log(f"[世界 {wn}] {cal[0].date()}～{cal[-1].date()}｜股 {S}｜段 {{{', '.join(f'{k}: {cal[x].date()}～{cal[y].date()}' for k, (x, y) in segp.items())}}}｜閘 {gate}｜壞根 {bad_info}")
    return W


# ═════════════ 逐股特徵 ═════════════
def macd_flags(idx, c, CBk, MID, is_me):
    """⇒ 每根有效 K 棒的 (可算, 多方)。CBk[k] ＝ 到第 k 根（含）為止的壞 K 棒數（段號）。"""
    nb = len(idx)
    mon = MID[idx]
    last_in_m = np.r_[mon[1:] != mon[:-1], True]
    mb = np.flatnonzero(last_in_m)                       # 每月最後一根有效 K 棒
    rec_m = mon[mb]; rec_c = c[mb]; rec_seg = CBk[mb]
    nr = len(mb)
    dif = np.full(nr, np.nan); dea = np.full(nr, np.nan); pos = np.zeros(nr, int); run = np.zeros(nr, int)
    a12, a26, a9 = 2 / 13, 2 / 27, 2 / 10
    rid = 0
    for r in range(nr):
        if r == 0 or rec_seg[r] != rec_seg[r - 1] or rec_m[r] != rec_m[r - 1] + 1:
            rid += 1; e12 = e26 = rec_c[r]; d_ = 0.0; de = 0.0; p_ = 0
        else:
            e12 = a12 * rec_c[r] + (1 - a12) * e12; e26 = a26 * rec_c[r] + (1 - a26) * e26
            p_ += 1
        d_ = e12 - e26
        de = d_ if p_ == 0 else a9 * d_ + (1 - a9) * de
        dif[r] = d_; dea[r] = de; pos[r] = p_; run[r] = rid
    m2r = {int(m): r for r, m in enumerate(rec_m)}
    ok = np.zeros(nb, bool); bull = np.zeros(nb, bool)
    for k in range(nb):
        t = idx[k]
        ms = int(MID[t]) if is_me[t] else int(MID[t]) - 1
        r = m2r.get(ms)
        if r is None or mb[r] > k or rec_seg[r] != CBk[k] or pos[r] < 34:
            continue
        ok[k] = True; bull[k] = dif[r] > dea[r]
    return ok, bull


def stock_job(a):
    wn, sid = a
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    up = np.asarray(B["up"], bool)
    v = df["volume"].to_numpy(float)[idx]
    f = P.Frame(df, set())
    gate_b = np.asarray(f.gate, bool)[idx]
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]                          # CB[b+1] − CB[a] ＝ [a, b] 的壞 K 棒數

    def nbad(a_, b_):
        a_ = np.maximum(a_, 0); b_ = np.minimum(b_, nb - 1)
        return CB[b_ + 1] - CB[a_]
    K = np.arange(nb)
    ma20 = pd.Series(c).rolling(20, min_periods=20).mean().to_numpy().copy()
    ma20[(K < 19) | (nbad(K - 18, K) > 0)] = np.nan
    v20 = pd.Series(v).rolling(20, min_periods=20).mean().shift(1).to_numpy().copy()
    tr = np.full(nb, np.nan); tr[1:] = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy()
    atrp = atr / c
    v80 = np.full(nb, np.nan)
    if nb > 60:
        sw = np.lib.stride_tricks.sliding_window_view(v, 60)[:nb - 60]   # 視窗 [k−60, k−1]，k ＝ 60..nb−1
        v80[60:] = np.percentile(sw, 80, axis=1)
    valid = (K >= 20) & (K + 1 < nb)
    valid &= nbad(K - 20, K + 1) == 0
    v60ok = valid & (K >= 60) & (nbad(K - 60, K) == 0)
    # ① 漲停名單
    js = np.searchsorted(idx, idx - 9, "left")
    cu = np.r_[0, np.cumsum(up)]
    lu = (cu[K + 1] - cu[js]) > 0
    three = np.zeros(nb, bool); three[2:] = up[2:] & up[1:-1] & up[:-2]
    ct = np.r_[0, np.cumsum(three)]
    lo3 = np.minimum(js + 2, K + 1)
    run3 = (ct[K + 1] - ct[lo3]) > 0
    A1 = lu & ~run3
    # ② 月 MACD
    mok, mbull = macd_flags(idx, c, CB[1:], W["MID"], W["is_me"])
    A2 = mok & mbull
    # ③
    with np.errstate(invalid="ignore"):
        near1 = (l <= ma20 * 1.02) & (c >= ma20)
        near2 = (l <= ma20 + 0.5 * atr) & (c >= ma20)
        red = c > o
        vx1 = np.isfinite(v) & np.isfinite(v20) & (v > 1.5 * v20)
        vx2 = np.isfinite(v) & np.isfinite(v80) & (v >= v80)
    A3 = near1 & red & vx1
    A3r = near2 & red & vx2 & np.isfinite(atr)
    pv_b = W["PV"][i, idx]
    TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]
    e = idx + 1
    nxt_is_e = np.zeros(nb, bool); nxt_is_e[:-1] = idx[1:] == e[:-1]
    ec = np.minimum(e, n0 - 1)
    o_e = O[ec]
    traded_e = nxt_is_e & (e < n0) & TRD[ec] & np.isfinite(o_e) & (o_e > 0)
    upl_e = traded_e & UPL[ec]
    buy_ok = traded_e & ~UPL[ec]
    base = gate_b & pv_b & valid & np.isfinite(ma20)
    sig = {"F1": base & A1 & A2 & A3, "F2": base & v60ok & A1 & A2 & A3r, "F4": base & A1 & A3, "F5": base & A2 & A3}
    obs = gate_b & pv_b & A1
    dm = D.disposal_mask(sid, cal, W["disp"], after_days=0)[idx]
    sell_ok = TRD[idx] & np.isfinite(O[idx]) & (O[idx] > 0) & ~DNL[idx]
    nxs = np.full(nb + 1, nb, np.int64)
    for k in range(nb - 1, -1, -1):
        nxs[k] = k if sell_ok[k] else nxs[k + 1]
    below = np.isfinite(ma20) & (c < ma20)
    r4 = np.zeros(nb, bool)
    if nb >= 4:
        r4[:nb - 3] = below[:nb - 3] & below[1:nb - 2] & below[2:nb - 1] & below[3:]
    # 閘：快取價 vs load_bars
    cc = W["C"][i, idx]; oo = O[idx]
    okc = np.isfinite(cc) & np.isfinite(c); oko = np.isfinite(oo) & np.isfinite(o)
    dc = float(np.max(np.abs(cc[okc] / c[okc] - 1.0))) if okc.any() else 0.0
    do = float(np.max(np.abs(oo[oko] / o[oko] - 1.0))) if oko.any() else 0.0
    pk = {"idx": idx, "o": o, "c": c, "ma20": ma20, "below": below, "R4": np.flatnonzero(r4), "nxs": nxs, "badb": np.flatnonzero(bad),
          "atrp": atrp, "sig": sig, "buy_ok": buy_ok, "upl_e": upl_e, "traded_e": traded_e, "pool": base & buy_ok, "obs": obs, "disp": dm,
          "macd_ok": mok, "end_ok": bool(idx[-1] == n0 - 1), "gate": {"收盤差": dc, "開盤差": do}}
    return sid, pk


# ═════════════ 出場 ═════════════
def tk(kind, day):
    return 2 * day if kind == "open" else 2 * day + 1


def exit_path(pk, k, mode, bp, n0, th=None):
    """訊號根 k（進場根 ke ＝ k＋1）⇒ rec：parts [(w, px, dlast)]、xpos、g、fk（final 種類）、a、p1、p2、d、S、hmax。"""
    idx, o, c = pk["idx"], pk["o"], pk["c"]; nb = len(idx); ke = k + 1
    bb = pk["badb"]; j_ = int(np.searchsorted(bb, ke + 1)); kb = int(bb[j_]) if j_ < len(bb) else None
    lim = kb if kb is not None else nb
    nxs = pk["nxs"]

    def sale_at(d):
        j = int(nxs[d + 1]) if d + 1 <= nb else nb
        return j if j < lim else None

    def forced():
        if kb is not None:
            q = kb - 1
            return ("close", int(idx[q]), float(c[q]), int(idx[q]), int(idx[q]) + 1, "壞根前收盤強制", q)
        if pk["end_ok"]:
            return ("end", n0 - 1, float(c[nb - 1]), n0 - 1, n0, "資料尾仍持有", nb - 1)
        return ("close", int(idx[nb - 1]), float(c[nb - 1]), int(idx[nb - 1]), int(idx[nb - 1]) + 1, "下市／停止交易（最後收盤）", nb - 1)
    a = 0; d = None; S = None
    if mode == "H60":
        r = R.fixed_exit(o, c, k, 60, lim)
        if r:
            q = int(r[0]); fin = ("close", int(idx[q]), float(c[q]), int(idx[q]), int(idx[q]), "第60根收盤", q)
        else:
            fin = forced()
    else:
        below = pk["below"]
        if ke < lim and below[ke]:
            d, a = ke, 1
        elif ke + 1 < lim and below[ke + 1]:
            d, a = ke + 1, 2
        else:
            R4 = pk["R4"]; jj = int(np.searchsorted(R4, ke + 2))
            if jj < len(R4) and R4[jj] + 3 < lim:
                d = int(R4[jj]) + 3
        S = sale_at(d) if d is not None else None
        if S is not None:
            fin = ("open", int(idx[S]), float(o[S]), int(idx[S]) - 1, int(idx[S]), "a 第1天破MA20" if a == 1 else ("a 第2天破MA20" if a == 2 else "b 三日沒站回"), S)
        else:
            fin = forced()
    tfin = 2 * n0 if fin[0] == "end" else tk(fin[0], fin[1])
    parts = []; p1 = p2 = -1
    if th is not None and mode != "H60":
        seg = c[ke:lim] / bp - 1.0
        sold = 0.0; Ps = []
        for thv in th:
            hit = np.flatnonzero(seg >= thv)
            if not len(hit):
                Ps.append(-1); continue
            jb = ke + int(hit[0]); P_ = sale_at(jb)
            if P_ is None or tk("open", int(idx[P_])) >= tfin:
                Ps.append(-1); continue
            Ps.append(P_)
        p1, p2 = Ps
        for P_ in Ps:
            if P_ >= 0:
                parts.append((1 / 3, float(o[P_]), int(idx[P_]) - 1)); sold += 1 / 3
        parts.append((1.0 - sold, fin[2], fin[3]))
    else:
        parts.append((1.0, fin[2], fin[3]))
    g = sum(w * px for w, px, _ in parts) / bp - 1.0
    gs = sum(w * px * (1 - SLIP) for w, px, _ in parts) / (bp * (1 + SLIP)) - 1.0
    qd = fin[6]
    hmax = float(np.nanmax(c[ke:(d if d is not None else qd) + 1])) if (d if d is not None else qd) >= ke else float(c[ke])
    return {"parts": parts, "xpos": int(fin[4]), "g": float(g), "g_slip": float(gs), "fk": fin[5], "a": a, "p1": int(idx[p1]) if p1 >= 0 else -1,
            "p2": int(idx[p2]) if p2 >= 0 else -1, "d": int(idx[d]) if d is not None else -1, "S": int(S) if S is not None else -1, "hmax": hmax, "kb": -1 if kb is None else int(kb)}


def rows_job(a):
    wn, sid = a
    W = _G[wn]; pk = _G["PK"][wn][sid]; n0 = W["n0"]; i = W["ix"][sid]
    out = {cl: [] for cl in CELLS}
    idx = pk["idx"]; O = W["O"][i]
    for cl in CELLS:
        sg = SIG_OF[cl]; mode = EXIT_OF[cl]
        ks = np.flatnonzero(pk["sig"][sg] & pk["buy_ok"])
        for k in ks:
            e = int(idx[k]) + 1; bp = float(O[e])
            if mode == "M":
                rec = exit_path(pk, int(k), "M", bp, n0, TH1)
            elif mode == "M2":
                ap = float(pk["atrp"][k]); rec = exit_path(pk, int(k), "M", bp, n0, (TH2[0] * ap, TH2[1] * ap))
            elif mode == "N":
                rec = exit_path(pk, int(k), "M", bp, n0, None)
            else:
                rec = exit_path(pk, int(k), "H60", bp, n0, None)
            rec.update(sid=sid, k=int(k), t=int(idx[k]), entry_pos=e, bp=bp, atrp=float(pk["atrp"][k]))
            out[cl].append(rec)
    return sid, out


def rand_rows_job(a):
    wn, sid, ks = a
    W = _G[wn]; pk = _G["PK"][wn][sid]; n0 = W["n0"]; O = W["O"][W["ix"][sid]]
    res = {}
    for k in ks:
        e = int(pk["idx"][k]) + 1; bp = float(O[e])
        rec = exit_path(pk, int(k), "M", bp, n0, TH1)
        rec.update(sid=sid, k=int(k), t=int(pk["idx"][k]), entry_pos=e, bp=bp)
        res[int(k)] = rec
    return sid, res


# ═════════════ 引擎 ═════════════
def padc(W, sid):
    i = W["ix"][sid]; c = W["C"][i]
    return np.r_[c, c[-1]]


def eng_inputs(W, rows, slip=False):
    rows = sorted(rows, key=lambda r: (r["entry_pos"], r["sid"]))
    keys = [f"{r['sid']}#{r['entry_pos']}" for r in rows]
    sig = pd.DataFrame({"sid": keys, "entry_pos": [r["entry_pos"] for r in rows], "xpos_D": [r["xpos"] for r in rows],
                        "g_D": [r["g_slip"] if slip else r["g"] for r in rows]})
    CPc = {}; OPc = {}
    closes = {}; opens = {}; hm = {}; SFk = {}; info = {}
    NP = W["NP"]; tt = np.arange(NP)
    for key, r in zip(keys, rows):
        s = r["sid"]
        if s not in CPc:
            CPc[s] = padc(W, s); op = np.r_[W["O"][W["ix"][s]], np.nan]; OPc[s] = op * (1 + SLIP) if slip else op
        hm[key] = s; opens[key] = OPc[s]
        if s in W["SF"]:
            SFk[key] = W["SF"][s]
        if len(r["parts"]) > 1:
            cp = CPc[s]; Sc = np.zeros(NP)
            for w, px, dl in r["parts"]:
                Sc += w * np.where(tt <= dl, cp, px * (1 - SLIP) if slip else px)
            closes[key] = Sc
        else:
            closes[key] = CPc[s]
        info[key] = r
    return sig, closes, opens, hm, SFk, info


def run_eng(W, rows, slip=False):
    if not rows:
        return None
    sig, closes, opens, hm, SFk, info = eng_inputs(W, rows, slip)
    au = []
    o = R.simulate_mtm(sig, "D", NS, np.random.default_rng(SEED_ENG), closes, opens, W["NP"], return_equity=True,
                       stop_force=SFk, audit=au, held_map=hm)
    return {"eq": np.asarray(o["equity"], float), "hv": np.asarray(o["hold_val"], float), "first": int(o["first"]), "end": int(o["end"]),
            "trades": int(o["trades"]), "sf_n": int(o.get("x_stop_force_n", 0)), "audit": au, "info": info, "slip": slip}


def eng_job(a):
    wn, cl, slip = a
    return wn, cl, slip, run_eng(_G[wn], _G["ROWS"][wn][cl], slip)


def trades_of(E):
    """⇒ 每筆實際交易：key、買進日、amt、ep、賣出日、info。"""
    buys = {}; out = []
    for x in E["audit"]:
        if x["side"] == "buy":
            buys[x["sid"]] = (int(x["t"]), float(x["amt"]), float(x["px"]))
        else:
            b = buys.pop(x["sid"])
            out.append({"key": x["sid"], "tb": b[0], "amt": b[1], "ep": b[2], "ts": int(x["t"]), "r": E["info"][x["sid"]]})
    for k, b in buys.items():
        out.append({"key": k, "tb": b[0], "amt": b[1], "ep": b[2], "ts": None, "r": E["info"][k]})
    return out


def pre_stats(W, E):
    """⛔ 不含任何報酬：持股數、現金（凍結算現金）、換手、持有天數。"""
    eq, hv = E["eq"], E["hv"]; n = len(eq)
    TR = trades_of(E)
    cnt = np.zeros(n + 1); frz = np.zeros(n)
    for z in TR:
        cnt[z["tb"]] += 1
        ts = z["ts"] if z["ts"] is not None else n
        cnt[min(ts, n)] -= 1
        r = z["r"]
        if len(r["parts"]) > 1:
            for w, px, dl in r["parts"][:-1]:
                pxx = px * (1 - SLIP) if E["slip"] else px
                a_ = dl + 1
                if ts > a_:
                    frz[a_:ts] += z["amt"] * w * pxx / z["ep"]
    hold = np.cumsum(cnt)[:n]
    out = {}
    for sg, (x, y) in W["segp"].items():
        yrs = (y - x + 1) / 245.0
        bs = [z for z in TR if x <= z["tb"] <= y]
        hd = [z["ts"] - z["tb"] for z in bs if z["ts"] is not None]
        hdw = []
        for z in bs:
            if z["ts"] is None:
                continue
            r = z["r"]
            hdw.append(sum(w * ((dl + 1 if j < len(r["parts"]) - 1 else z["ts"]) - z["tb"]) for j, (w, px, dl) in enumerate(r["parts"])))
        out[sg] = {"平均持股": float(np.mean(hold[x:y + 1])), "現金比例": float(1.0 - np.mean((hv[x:y + 1] - frz[x:y + 1]) / eq[x:y + 1])),
                   "買進筆": len(bs), "買進每年": len(bs) / yrs, "換手每年": float(sum(z["amt"] for z in bs) / np.mean(eq[x:y + 1]) / yrs),
                   "平均持有天數": float(np.mean(hd)) if hd else float("nan"), "平均持有天數（按股數）": float(np.mean(hdw)) if hdw else float("nan")}
        out[sg]["成本每年"] = out[sg]["換手每年"] * COST
    return out, TR


def label(c, m, b):
    if not (np.isfinite(c) and np.isfinite(m)) or m == 0:
        return "—"
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def ratio(c, m):
    return float(c / abs(m)) if (np.isfinite(c) and np.isfinite(m) and m < 0) else float("nan")


def eff_n(W, TR, days):
    res = []
    iv = [(z["r"]["sid"], z["tb"], z["ts"] if z["ts"] is not None else W["NP"]) for z in TR]
    for t in days:
        held = [s for s, t0, t1 in iv if t0 <= t < t1]
        N = len(held)
        if N == 0:
            continue
        if N == 1:
            res.append((t, 1, np.nan, 1.0)); continue
        Rm = []
        for s in held:
            cc = np.asarray(W["C"][W["ix"][s]][max(t - 60, 0):t + 1], float)
            Rm.append(cc[1:] / cc[:-1] - 1.0 if len(cc) == 61 else np.full(60, np.nan))
        Rm = np.array(Rm); cs = []
        for a in range(N):
            for b in range(a + 1, N):
                mk = np.isfinite(Rm[a]) & np.isfinite(Rm[b])
                if mk.sum() < 40:
                    continue
                u, v = Rm[a][mk], Rm[b][mk]
                if u.std() == 0 or v.std() == 0:
                    continue
                cs.append(float(np.corrcoef(u, v)[0, 1]))
        rho = float(np.mean(cs)) if cs else np.nan
        res.append((t, N, rho, N / (1 + (N - 1) * rho) if np.isfinite(rho) else np.nan))
    return res


def seg_metrics(W, E, x, y):
    c, m, _ = RR.win_metrics(E["eq"], E["first"], E["end"], x, y)
    return float(c), float(m)


def post60(pk, S, d_bar_idx, ke, px):
    """規則賣出的整筆出場（開盤 S 根）⇒ (賣價距賣後 60 根最高收盤, 賣後又創新高)；窗不滿或遇壞根截斷 ⇒ NaN。"""
    nb = len(pk["idx"]); c = pk["c"]
    if S < 0 or S + 59 > nb - 1:
        return np.nan, np.nan
    bb = pk["badb"]; j_ = int(np.searchsorted(bb, S + 1)); kb = int(bb[j_]) if j_ < len(bb) else None
    hi = S + 59 if (kb is None or kb > S + 59) else kb - 1
    if hi < S:
        return np.nan, np.nan
    mx = float(np.max(c[S:hi + 1]))
    d = int(np.searchsorted(pk["idx"], d_bar_idx))
    hold_mx = float(np.max(c[ke:d + 1]))
    return px / mx - 1.0, float(mx > hold_mx)


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}")
    S = {"讀法寫死": TIME, "登錄": f"最笨交易法 seq1 sha {REG_SHA}（裁定 seq351 發號，N_組合 ＋1）", "登錄檔": regf, "結果句必附": SENT, "早年標註": NOTE_EARLY,
         "格": CNAME, "閘": {}}
    WS = {}; PKS = {}
    for wn in WORLDS:
        W = load_world(wn, log); WS[wn] = W; _G[wn] = W
        S["閘"][wn] = {"世界": W["gate"], "壞根": W["bad_info"]}
        cp = os.path.join(WORK, f"packs_{wn}.pkl")
        if os.path.exists(cp):
            PKS[wn] = pickle.load(open(cp, "rb")); log(f"[逐股 {wn}] 讀快取 {cp}")
        else:
            t0 = time.time(); res = {}
            with Pool(a.procs) as pool:
                for j, (s, pk) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in W["run_sids"]], chunksize=8)):
                    res[s] = pk
                    if j % 400 == 0:
                        log(f"[逐股 {wn}] {j}/{len(W['run_sids'])}｜{time.time() - t0:.0f}s")
            PKS[wn] = {s: v for s, v in res.items() if v is not None}
            pickle.dump(PKS[wn], open(cp, "wb"), protocol=5)
        pk_ = PKS[wn]
        S["閘"][wn]["load_bars 讀不到（<260 根）檔數"] = len(W["run_sids"]) - len(pk_)
        S["閘"][wn]["快取收盤 vs load_bars 最大相對差"] = max(v["gate"]["收盤差"] for v in pk_.values())
        S["閘"][wn]["快取開盤 vs load_bars 最大相對差"] = max(v["gate"]["開盤差"] for v in pk_.values())
        mf = [int(v["idx"][np.flatnonzero(v["macd_ok"])[0]]) for v in pk_.values() if v["macd_ok"].any()]
        W["macd_first"] = min(mf) if mf else None
        log(f"[逐股 {wn}] {len(pk_)} 檔｜MACD 最早可算日 {W['cal'][W['macd_first']].date()}｜閘 {S['閘'][wn]}")
    for wn in WS:
        g = S["閘"][wn]
        if g["快取收盤 vs load_bars 最大相對差"] > 1e-9 or g["快取開盤 vs load_bars 最大相對差"] > 1e-9:
            raise SystemExit(f"⛔ {wn} 價格閘不過 {g}")
    _G["PK"] = PKS
    # ── 逐列出場 ──
    ROWS = {}
    for wn, W in WS.items():
        ROWS[wn] = {cl: [] for cl in CELLS}
        with Pool(a.procs) as pool:
            for s, out in pool.imap_unordered(rows_job, [(wn, s) for s in sorted(PKS[wn])], chunksize=8):
                for cl in CELLS:
                    ROWS[wn][cl] += out[cl]
        log(f"[逐列 {wn}] " + "｜".join(f"{cl} {len(ROWS[wn][cl])}" for cl in CELLS))
    _G["ROWS"] = ROWS
    # ── 訊號統計（不含報酬）、ATR% 分布（F2 跑前先報）──
    SIGS = {}
    for wn, W in WS.items():
        cal = W["cal"]; SIGS[wn] = {}
        for sg_ in ("F1", "F2", "F4", "F5"):
            yr = {}; n_all = n_c = n_upl = n_notr = 0; n_d = 0
            for s, pk in PKS[wn].items():
                m = pk["sig"][sg_]
                if not m.any():
                    continue
                ks = np.flatnonzero(m)
                for y in cal[pk["idx"][ks]].year:
                    yr.setdefault(int(y), [0, 0]); yr[int(y)][0] += 1
                for y in cal[pk["idx"][np.flatnonzero(m & pk["buy_ok"])]].year:
                    yr[int(y)][1] += 1
                n_all += len(ks); n_c += int((m & pk["buy_ok"]).sum()); n_upl += int((m & pk["upl_e"]).sum())
                n_notr += int((m & ~pk["traded_e"]).sum()); n_d += int((m & pk["disp"]).sum())
            SIGS[wn][sg_] = {"訊號（剔可買前）": n_all, "候選（可買）": n_c, "開盤鎖漲停買不到": n_upl, "比例_鎖漲停": n_upl / n_all if n_all else np.nan,
                             "e 沒成交或開盤無效": n_notr, "比例_沒成交": n_notr / n_all if n_all else np.nan,
                             "訊號日處置中": n_d, "比例_處置": n_d / n_all if n_all else np.nan, "逐年[訊號,候選]": yr}
        ob = sum(int(pk["obs"].sum()) for pk in PKS[wn].values()); obd = sum(int((pk["obs"] & pk["disp"]).sum()) for pk in PKS[wn].values())
        SIGS[wn]["觀察名單（母體∧①）股日"] = ob; SIGS[wn]["觀察名單內處置股比例"] = obd / ob if ob else np.nan
        log(f"[訊號 {wn}] " + json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != '逐年[訊號,候選]'}) for k, v in SIGS[wn].items()}, ensure_ascii=False, default=str))
    ATR = {}
    for sg_ in ("F1", "F2"):
        v = np.array([r["atrp"] for r in ROWS["主"][sg_ if sg_ == "F2" else "F1"]], float)
        v = v[np.isfinite(v)]
        ATR[sg_] = {"n": int(len(v)), "中位": float(np.median(v)) if len(v) else np.nan, "p25": float(np.quantile(v, .25)) if len(v) else np.nan,
                    "p75": float(np.quantile(v, .75)) if len(v) else np.nan, "8×中位": float(8 * np.median(v)) if len(v) else np.nan,
                    "13×中位": float(13 * np.median(v)) if len(v) else np.nan}
    log(f"[F2 ATR%（主世界訊號列，只看分布）] {ATR}")
    # ── 引擎（12 條＋滑價 12 條）──
    jobs = [(wn, cl, sl) for wn in WS for cl in CELLS for sl in (False, True)]
    with Pool(min(a.procs, len(jobs))) as pool:
        RES = pool.map(eng_job, jobs, chunksize=1)
    ENG = {(wn, cl, sl): E for wn, cl, sl, E in RES}
    for (wn, cl, sl), E in ENG.items():
        S["閘"][wn][f"{cl}{'·滑價' if sl else ''} 引擎"] = {"買進筆": E["trades"], "stop_force 觸發": E["sf_n"]}
    # ── 退化（先寫）──
    DEG = {"寫入時間（台北）": None, "規則": "seq325：探索段平均持股 ＜ 3 或 現金比例 ＞ 30%（分批凍結的錢算現金）⇒ 退化；早年另報", "F2 ATR%（跑前先報）": ATR,
           "MACD 最早可算日": {wn: str(W["cal"][W["macd_first"]].date()) for wn, W in WS.items()}, "格": {}}
    PRE_ = {}
    for (wn, cl, sl), E in ENG.items():
        ps, TR = pre_stats(WS[wn], E); PRE_[(wn, cl, sl)] = (ps, TR)
        if sl:
            continue
        for sg, v in ps.items():
            DEG["格"][f"{wn}|{cl}|{sg}"] = {"平均持股": v["平均持股"], "現金比例": v["現金比例"], "買進筆": v["買進筆"],
                                         "退化": bool(v["平均持股"] < DEG_HOLD or v["現金比例"] > DEG_CASH)}
    DEG["F1 探索段退化"] = DEG["格"]["主|F1|探索"]["退化"]
    DEG["寫入時間（台北）"] = now_tpe()
    json.dump(DEG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[退化] 已寫 degeneracy.json（{DEG['寫入時間（台北）']}）｜F1 探索 {DEG['格']['主|F1|探索']}")
    S["退化"] = DEG
    # ── 報酬 ──
    TAB = []; EQS = {}
    for (wn, cl, sl), E in ENG.items():
        W = WS[wn]; ps, TR = PRE_[(wn, cl, sl)]
        if not sl:
            EQS[f"{wn}|{cl}"] = E["eq"]
        for sg, (x, y) in W["segp"].items():
            c_, m_ = seg_metrics(W, E, x, y); b = RR.bench_row(W["cal"], W["bench"], x, y + 1)
            row = {"世界": wn, "格": cl, "滑價": sl, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "年化": c_, "回落": m_, "比值": ratio(c_, m_),
                   "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": ratio(b["cagr"], b["mdd"]), "標籤": label(c_, m_, b), **ps[sg]}
            if not sl:
                days = sorted({z["tb"] for z in TR if x <= z["tb"] <= y})
                en = eff_n(W, TR, days)
                row["等效獨立檔數"] = float(np.nanmean([z[3] for z in en])) if en else np.nan
                row["平均ρ"] = float(np.nanmean([z[2] for z in en])) if en else np.nan
                row["買進日持股N平均"] = float(np.mean([z[1] for z in en])) if en else np.nan
            TAB.append(row)
        # 描述窗：MACD 可算起
        for sg, (x, y) in W["segp"].items():
            if W["macd_first"] is not None and W["macd_first"] > x and not sl:
                x2 = W["macd_first"]; c_, m_ = seg_metrics(W, E, x2, y); b = RR.bench_row(W["cal"], W["bench"], x2, y + 1)
                TAB.append({"世界": wn, "格": cl, "滑價": sl, "段": f"{sg}（MACD可算起·描述）", "窗": f"{W['cal'][x2].date()}～{W['cal'][y].date()}", "年化": c_, "回落": m_,
                            "比值": ratio(c_, m_), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": ratio(b["cagr"], b["mdd"]), "標籤": label(c_, m_, b)})
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "Dumb_main.csv"), index=False, float_format="%.6g")
    np.savez_compressed(os.path.join(OUT, "eq_主.npz"), **{k.split("|")[1]: v for k, v in EQS.items() if k.startswith("主|")})
    np.savez_compressed(os.path.join(OUT, "eq_早年.npz"), **{k.split("|")[1]: v for k, v in EQS.items() if k.startswith("早年|")})
    for wn in WS:
        for cl in CELLS:
            R_ = pd.DataFrame([{k: (json.dumps(v) if k == "parts" else v) for k, v in r.items()} for r in ROWS[wn][cl]])
            R_.to_csv(os.path.join(OUT, f"rows_{wn}_{cl}.csv.gz"), index=False, float_format="%.17g")
    log("[主表]\n" + TB[~TB["滑價"]][["世界", "格", "段", "年化", "回落", "比值", "0050年化", "0050回落", "標籤", "平均持股", "現金比例", "買進筆"]].to_string())
    # ── 判語 ──
    def lab(wn, cl, sg, sl=False):
        z = TB[(TB["世界"] == wn) & (TB["格"] == cl) & (TB["段"] == sg) & (TB["滑價"] == sl)]
        return z.iloc[0]["標籤"]

    def verdict(cl, sl=False):
        le, lc, lo = lab("主", cl, "探索", sl), lab("主", cl, "確認", sl), lab("早年", cl, "早年", sl)
        if le == "合格" and lc == "合格":
            v = "暫定（早年不合格 ⇒ 最多暫定）" if lo == "不合格" else "合格"
        elif le in ("合格", "另列") and lc in ("合格", "另列"):
            v = "另列" + ("（早年不合格）" if lo == "不合格" else "")
        else:
            v = "不合格"
        return {"探索": le, "確認": lc, "早年": lo, "整件": v}
    S["判語"] = {"F1": verdict("F1"), "F2（對照、不換主判）": verdict("F2"), "F1·滑價（描述）": verdict("F1", True)}
    if DEG["F1 探索段退化"]:
        S["判語"]["F1"]["整件"] = "退化、照 seq325 不判（標籤照報：" + S["判語"]["F1"]["整件"] + "）"
    log(f"[判語] {S['判語']}")
    # ── 必報 ──
    S["必報"] = must(WS, PKS, ENG, PRE_, SIGS, log)
    S["訊號統計"] = SIGS
    # ── 隨機進場 ──
    S["隨機進場"] = random_arm(WS, PKS, ENG, TB, a, log)
    # ── 先驗 ──
    def g_(wn, cl, sg, k="年化"):
        z = TB[(TB["世界"] == wn) & (TB["格"] == cl) & (TB["段"] == sg) & (~TB["滑價"])]
        return float(z.iloc[0][k])
    nF1 = SIGS["主"]["F1"]["訊號（剔可買前）"]; nF5 = SIGS["主"]["F5"]["訊號（剔可買前）"]
    S["先驗對照"] = {
        "① F1 確認段不合格（約七成）": {"結果": lab("主", "F1", "確認"), "成立": lab("主", "F1", "確認") == "不合格"},
        "② F6 年化高於 F1（約六成五）": {sg: {"F6": g_(wn, "F6", sg), "F1": g_(wn, "F1", sg), "成立": g_(wn, "F6", sg) > g_(wn, "F1", sg)}
                                     for wn, sg in (("主", "探索"), ("主", "確認"), ("早年", "早年"))},
        "③ F5 訊號數多 5 倍以上、年化低於 F1（約五成五）": {"訊號倍數（主）": nF5 / nF1 if nF1 else np.nan,
                                              "訊號倍數（早年）": SIGS["早年"]["F5"]["訊號（剔可買前）"] / SIGS["早年"]["F1"]["訊號（剔可買前）"] if SIGS["早年"]["F1"]["訊號（剔可買前）"] else np.nan,
                                              **{sg: {"F5": g_(wn, "F5", sg), "F1": g_(wn, "F1", sg), "年化低於": g_(wn, "F5", sg) < g_(wn, "F1", sg)}
                                                 for wn, sg in (("主", "探索"), ("主", "確認"), ("早年", "早年"))}},
        "④ F1 早年 2005～2014 不合格（約六成五）": {"結果": lab("早年", "F1", "早年"), "成立": lab("早年", "F1", "早年") == "不合格"}}
    log(f"[先驗] {json.dumps(S['先驗對照'], ensure_ascii=False, default=str)}")
    S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "Dumb.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {S['耗時秒']}s")
    bad = [f"{wn}:{k}" for wn in WS for k, v in S["閘"][wn].items() if isinstance(v, dict) and v.get("stop_force 觸發", 0)]
    if bad:
        raise SystemExit(f"⛔ stop_force 應 0：{bad}")


def must(WS, PKS, ENG, PRE_, SIGS, log):
    out = {}
    for wn, W in WS.items():
        cal = W["cal"]
        for cl in CELLS:
            E = ENG[(wn, cl, False)]; ps, TR = PRE_[(wn, cl, False)]
            yrs = {}
            for z in TR:
                y = int(cal[z["tb"]].year); net = z["r"]["g"] - COST
                yrs.setdefault(y, []).append(net)
            sig_y = SIGS[wn][SIG_OF[cl]]["逐年[訊號,候選]"]
            peryr = {}
            for y in sorted(set(sig_y) | set(yrs)):
                v = np.array(yrs.get(y, []), float); w_ = v[v > 0]; l_ = v[v <= 0]
                peryr[y] = {"訊號": sig_y.get(y, [0, 0])[0], "候選": sig_y.get(y, [0, 0])[1], "筆數": int(len(v)), "勝率": float((v > 0).mean()) if len(v) else np.nan,
                            "平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
                            "平均淨報酬": float(v.mean()) if len(v) else np.nan}
            n = len(TR)
            rr = [z["r"] for z in TR]
            seg = {}
            for sg, (x, y) in W["segp"].items():
                tz = [z for z in TR if x <= z["tb"] <= y]; rz = [z["r"] for z in tz]
                nn = len(rz)
                v = np.array([r["g"] - COST for r in rz], float); w_ = v[v > 0]; l_ = v[v <= 0]
                d = {"筆數": nn, "勝率": float((v > 0).mean()) if nn else np.nan,
                     "平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
                     "⑤ +30% 觸發比例": float(np.mean([r["p1"] >= 0 for r in rz])) if nn else np.nan,
                     "⑤ +50% 觸發比例": float(np.mean([r["p2"] >= 0 for r in rz])) if nn else np.nan,
                     "④a 第1天破MA20出場比例": float(np.mean([r["a"] == 1 for r in rz])) if nn else np.nan,
                     "④a 第2天破MA20出場比例": float(np.mean([r["a"] == 2 for r in rz])) if nn else np.nan,
                     "整筆出場種類": pd.Series([r["fk"] for r in rz]).value_counts().to_dict() if nn else {},
                     "窗尾仍持有（T1）": int(sum(r["fk"] == "資料尾仍持有" for r in rz))}
                d["④a 合計"] = d["④a 第1天破MA20出場比例"] + d["④a 第2天破MA20出場比例"] if nn else np.nan
                # 賣出點（規則賣出、開盤）
                dist = []; nh = []
                for r in rz:
                    if r["S"] < 0:
                        continue
                    pk = PKS[wn][r["sid"]]
                    a_, b_ = post60(pk, r["S"], r["d"], r["k"] + 1, r["parts"][-1][1])
                    if np.isfinite(a_):
                        dist.append(a_); nh.append(b_)
                d["賣出點：賣價距賣後60根最高收盤（中位）"] = float(np.median(dist)) if dist else np.nan
                d["賣出點：p25／p75"] = [float(np.quantile(dist, .25)), float(np.quantile(dist, .75))] if dist else []
                d["賣後60根又創新高比例"] = float(np.mean(nh)) if nh else np.nan
                d["賣出點可算筆數"] = len(dist)
                disp_n = sum(int(PKS[wn][r["sid"]]["disp"][r["k"]]) for r in rz)
                d["實際買進中訊號日處置中比例"] = disp_n / nn if nn else np.nan
                seg[sg] = d
            out[f"{wn}|{cl}"] = {"逐年": peryr, "各段": seg, "全部筆數": n}
        log(f"[必報 {wn}] F1 " + json.dumps(out[f'{wn}|F1']['各段'], ensure_ascii=False, default=str)[:900])
    return out


def rand_job(a):
    wn, i = a
    W = _G[wn]; RB = _G["RANDROWS"][wn]; DAYS = _G["RDAYS"][wn]; POOL = _G["RPOOL"][wn]
    rng = np.random.default_rng([RSEED, WID[wn], i])
    rows = []
    for e, k in DAYS:
        pool = POOL.get(e - 1, [])
        if not pool:
            continue
        pick = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
        for j in pick:
            s, kk = pool[j]
            rows.append(RB[s][kk])
    E = run_eng(W, rows)
    row = {"世界": wn, "i": i, "列": len(rows), "買進筆": E["trades"] if E else 0}
    for sg, (x, y) in W["segp"].items():
        c_, m_ = seg_metrics(W, E, x, y) if E else (np.nan, np.nan)
        row[f"{sg}_年化"] = c_; row[f"{sg}_回落"] = m_
    return row, ([(r["sid"], r["entry_pos"]) for r in rows] if i == 0 else None)


def random_arm(WS, PKS, ENG, TB, a, log):
    _G["RANDROWS"] = {}; _G["RDAYS"] = {}; _G["RPOOL"] = {}
    out = {}
    for wn, W in WS.items():
        E = ENG[(wn, "F1", False)]
        cnt = {}
        for x in E["audit"]:
            if x["side"] == "buy":
                cnt[int(x["t"])] = cnt.get(int(x["t"]), 0) + 1
        DAYS = sorted(cnt.items())
        need = {e - 1 for e, _ in DAYS}
        POOL = {}
        for s in sorted(PKS[wn]):
            pk = PKS[wn][s]
            ks = np.flatnonzero(pk["pool"])
            for k in ks:
                t = int(pk["idx"][k])
                if t in need:
                    POOL.setdefault(t, []).append((s, int(k)))
        for t in POOL:
            POOL[t].sort()
        # 預抽（同一顆 rng 規則）⇒ 需要的列
        req = {}
        for i in range(NRAND):
            rng = np.random.default_rng([RSEED, WID[wn], i])
            for e, k in DAYS:
                pool = POOL.get(e - 1, [])
                if not pool:
                    continue
                for j in rng.choice(len(pool), size=min(k, len(pool)), replace=False):
                    s, kk = pool[j]; req.setdefault(s, set()).add(kk)
        RB = {}
        _G["RANDROWS"][wn] = RB
        with Pool(a.procs) as pool:
            for s, res in pool.imap_unordered(rand_rows_job, [(wn, s, sorted(v)) for s, v in sorted(req.items())], chunksize=8):
                RB[s] = res
        _G["RDAYS"][wn] = DAYS; _G["RPOOL"][wn] = POOL
        log(f"[隨機 {wn}] 進場日 {len(DAYS)}｜F1 買進 {sum(cnt.values())}｜母體日中位 {np.median([len(v) for v in POOL.values()]):.0f}｜需算列 {sum(len(v) for v in req.values())}")
        with Pool(a.procs) as pool:
            RES = pool.map(rand_job, [(wn, i) for i in range(NRAND)], chunksize=4)
        RD = pd.DataFrame([r for r, _ in RES])
        RD.to_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), index=False, float_format="%.10g")
        o = {}
        for sg in W["segp"]:
            z = TB[(TB["世界"] == wn) & (TB["格"] == "F1") & (TB["段"] == sg) & (~TB["滑價"])].iloc[0]
            rr = RD[f"{sg}_年化"] / RD[f"{sg}_回落"].abs()
            o[sg] = {"F1 年化": float(z["年化"]), "F1 比值": float(z["比值"]), "隨機 年化中位": float(RD[f"{sg}_年化"].median()), "隨機 回落中位": float(RD[f"{sg}_回落"].median()),
                     "隨機 比值中位": float(rr.median()), "p（隨機比值 ≥ F1）": float((rr >= z["比值"]).mean()), "p（隨機年化 ≥ F1）": float((RD[f"{sg}_年化"] >= z["年化"]).mean()),
                     "隨機 買進筆中位": float(RD["買進筆"].median())}
        out[wn] = o
        log(f"[隨機 {wn}] {o}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()

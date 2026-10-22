# -*- coding: utf-8 -*-
"""52 週新高 10 檔（高10）每日／每月名單與前瞻紀錄——回測線開發子代理，2026-10-21。
依據：前瞻登錄 seq4（sha 4c17797e31363ed1；§一 規則＝PREREG接近52週新高組合層 eae8a7706bf45b1f §三 描述①）；裁定 seq414／415／416
（10 格補空位、每格 1/10、每月初從前前月底 PTH 由高往下補、抱 6 個月、空位 0050、與營量營飆分開；第一批 2026-11 第一個交易日開盤、用 2026-09 底排序；
 賣出＝進場月起第 6 個曆月最後交易日收盤；LINE 每格 2 萬、只在有買賣那天推、固定三句）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.pth10_daily --asof <資料日> --md backtest/resultsDaily/daily_<資料日>.md [--sha SHA]
    選項：--fwd DIR（狀態夾，預設 backtest/forward/pth10）｜--nowrite（不寫狀態夾）｜--preview-buy（乾跑用：把今晚當成下一批買進前一晚）｜--procs N
    對帳／fixture：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.pth10_daily_check

⛔ 不寫第二份實作（選股、進出、補空位全部呼叫歷史回測同一批函式）：
  排序（PTH、500 張閘、pit、未滿 12 月、窗內壞根、前 30% 同值併入）＝ researchPTH_freq.stock_job ＋ researchPTH_freq.select
  進場剔除（壞根(t,e]、e 無成交、e 開盤鎖漲停）＝ researchPTH_freq.stock_job 的 ENT；出場（第 6 個曆月最後交易日收盤、壞根前一根強制、下市末根）
    ＝ researchPTH.exit_positions ＋ researchPTH.stock_job；同 PTH 打破 ＝ researchPTHpf.load_events 同式 default_rng([SEED_TOP, 形成月序 j])
  10 格補空位（每格 前一日淨值 ÷ 10、空位 0050、同檔不重複、同日先出後進）＝ researchPTHpf.slot_tr ＋ slot_sim（＝ researchTurtleS2PF.simulate、不洗牌）
  逐股矩陣 ＝ researchRevLimitUp._wjob（~/rluwork 快取的同一支）；壞根 ＝ researchAddOn.extra_stock（＝ ~/crashwork bad 的同式：BARR.bad_part ∪ 減資／面額）；
  世界收尾 ＝ researchPTHpf.finish_world。本檔只做「用每日名單的唯讀快照重建同一個世界」與狀態檔、名單段落。

讀法（執行者補，寫死於 2026-10-21）：
 D1 資料 ＝ ~/h2data/<main sha>/data（run_daily_list.sh 的唯讀 archive；--sha 未給 ⇒ git rev-parse origin/main）；資料日 ≠ --asof ⇒ 中止。
 D2 月底：researchPTH_freq.month_ends；★ 資料日是該月最後一個交易日（休市表外推的下一交易日已跨月）而 month_ends 因「月底遇平日休市」判為不完整 ⇒ 補進該月
    （歷史回測日曆完整、只有資料尾受影響）。
 D3 排序快取 ranks/ranks_<形成月>.csv：形成月 ≥ 2026-09、月底已在日曆 ⇒ 全母體跑一次 researchPTH_freq.stock_job（約 3～5 分鐘，每月一次）。
    批次事件快取 events/events_<形成月>.csv：進場日 e 已在日曆 ⇒ 入選股跑 stock_job 取 e 的進場狀態（保留＝事件）。
 D4 每日模擬：視窗 ＝ 第一批進場日前一個交易日 t0（全抱 0050、淨值 1）～ 資料日；事件 ＝ 進場月 ≥ 2026-11 的各批；
    每批只取 (−PTH, 同值隨機) 前 20 名事件算出場（持股 ≤ 10 ⇒ 被跳過的 ≤ 10 ⇒ 實際補進的必在前 20 名；模擬後驗證、不在 ⇒ 中止）。
 D5 明天是月初買進日 ⇒ 多跑一個「合成的明天」（收盤與 0050 沿用資料日）：當批事件 ＝ 入選 ∧（資料日為止）無壞根；同值隨機以這組事件數計
    ⚠ 明天若有入選股開盤鎖漲停、沒成交或出壞根，事件數改變 ⇒ 同值（PTH＝1）的隨機順序會整組換，照規則紀錄可能與今晚名單不同（以隔天紀錄為準、段落註明）。
 D6 前瞻紀錄（只追加；已寫的列不重算）：positions.csv（照規則、還原價、金額佔權益）、positions_user.csv（LINE 名單每格 2 萬：股數 ＝ floor(20000 ÷ 參考價)、
    參考價 ＝ 資料日未還原收盤；買進 ＝ e 未還原開盤，e 無成交／開盤無效／開盤鎖漲停 ⇒ 買不到；賣出 ＝ 同批照規則的賣出日，沒有對應照規則列 ⇒ 排程賣出日未還原收盤）、
    equity.csv（照規則淨值）、runlog.md、state.json。
 D8 補位排序用的 PTH ＝ 歷史實際用的值（pth_keys：pandas 預設 csv 寫出再讀回；最後一位可差 1 ulp）：數學上相等的比值（如 15/16）全精度會差 1 ulp、
    歷史上合併成同值交給隨機（rk）⇒ 照歷史。用全精度時 115 批中有 27 批補位順序不同，用 pth_keys 後全同（③ 驗）。排序快取仍存全精度。
 D9 回測線裁定（2026-10-21，交件後）：LINE 的「續抱」「要賣」與空格數一律照 positions_user（LINE 名單、每格 2 萬那份），⛔ 不用照規則持股；
    明天要買 ＝ 當批待定事件照規則排序 (−PTH, 同值隨機) 由高往下、跳過 positions_user 已持有的代號、取 positions_user 的空格數（pick_user）；
    照規則紀錄照字面另記（positions.csv、equity.csv），只進前瞻與 md 說明行；兩邊分岔時 md 寫一行說明（不推）。
    positions_user 列被照規則提前出場（壞根／下市，跟同批照規則列的賣出日）⇒ 記出場那晚的 LINE 一併列出。
 D7 名單段落「## 十、52 週新高 10 檔（高10）」：平日一行持有狀態；明天月初買進（有要買的）或今天／明天有到期賣出 ⇒ 「- 【LINE】⭐」行
    （買、續抱、賣，固定附三句）；其他說明一律不帶【LINE】。先算完全部、最後才寫 md（暫存檔 ＋ os.replace，寫完比對其他段逐字不變）；失敗 ⇒ 非 0 結束、md 不動。
 D10 同分排序（使用者 10/21「暫時高10 配大跌 4 檔的分數規則給我！」；回測線交辦 2026-10-21）：設定檔鍵「高10_同分排序」＝ "F9" ⇒ 只有【LINE 名單／positions_user】
    的補格次序改用 researchPTH10tie T1（同 PTH 內：F9 可算者依 F9 高→低、算不出排最後、仍同分用原種子 rk）；缺鍵或其他值 ＝ "抽籤"（原樣）。
    ⛔ 照規則欄（positions.csv、equity.csv，前瞻 seq4）不變，仍是原種子抽籤；兩邊名單不同 ⇒ 沿用 D9 的 md 說明行（不推）。
    分數 ＝ researchPTH10tie_freq 同一批函式（date_scores、f9_cols、ai1_table／ai1_patch、order_of；⛔ 只 import）：排序日 ＝ 形成月底、只用當時可得資料；
    同分群 ＝ 當批待定事件內 PTH（pth_keys 值）完全相同、成員 ≥ 2（researchPTH10tie.build_keys 同式）；財報可用日 AI1 覆寫（seq352 口徑，同該件）。
    資料路徑（＝ mktdrop_cands 前瞻同讀法）：價量／月營收／配息 ＝ 唯讀快照 DATA；財報／法人／融資／集保 ＝ mktdrop_cands.fund_dir(main sha)。
    快取 f9/f9_<形成月>.csv（同分群成員相同才沿用）。F9 算不出（例外）⇒ 這晚 LINE 名單退回抽籤並在 md 寫 ⚠ 行（不中止名單）。
 D11 第三本「F9 照規則」（裁定 seq440 §二：照規則／使用者實際／F9 版三欄並記，2027-11 三欄並報）：positions_f9.csv、equity_f9.csv，與 positions.csv／equity.csv
    同式（同引擎 window_sim、每格前一日淨值 1/10、空位 0050、到期與壞根出場、只追加、已寫凍結），只把各批同 PTH 次序換成 F9
    （＝ researchPTH10tie T1：rk 換成 F9 次序中的位置，f9_rows；前 20 名改依 F9 次序）。已進場各批的同分群 ＝ 保留事件（快取 f9/f9_rule_<形成月>.csv）。
    次序在建世界之前算（F9 前 20 名要進世界）；F9 算不出 ⇒ 這晚第三本不更新（之後補，只追加）、md 寫 ⚠。不含明天的待定批（只記已發生）。
 D12（使用者 10/21「下面五句都不用寫」，情報 2102）：LINE 行只留名單內容（賣、買、續抱、備位），開頭「- 【LINE】⭐ 52 週新高 10 檔（高10）：」不變；
    同分句、F9 句、固定三句移到下一行「  - 註：…」（不帶【LINE】）。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
from backtest import researchPTHpf as M                     # noqa: E402  slot_tr、slot_sim、keep_order、finish_world、SEED_TOP、COST（⛔ 只 import）
from backtest import researchPTH as PTH                     # noqa: E402  exit_positions、stock_job、TYP
from backtest import researchPTH_freq as PT                 # noqa: E402  month_ends、entry_pos、stock_job、select、S_OK、E_*
from backtest import researchTurtleS2PF as TS               # noqa: E402  NS
from backtest import researchRevLimitUp as RLU              # noqa: E402  _wjob
from backtest import researchAddOn as RA                    # noqa: E402  extra_stock
from backtest import researchIndRev_prereg as PRE           # noqa: E402  okcode
from backtest import rerun17 as RR                          # noqa: E402  load_bench
from backtest import data as D                              # noqa: E402
from backtest import gate_b_status as GB                    # noqa: E402  future_trading_days
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

FWD = os.path.join(REPO, "backtest", "forward", "pth10")
WN = "pth10live"
L_SKIP, H_HOLD = 2, 6
NS = 10
K_PRE = 2 * NS
START_YM = 2026 * 12 + 10                                   # 第一批進場月 2026-11（年×12＋月−1）
# 每份金額＝使用者測試金額（裁定 seq422／423：不是規則、會再改）⇒ 可改設定值：backtest/forward/設定_每份金額.json（各策略一個鍵：營量／營飆／高10／大跌4檔；本檔讀「高10」）；
# 改金額只影響 LINE 股數換算與 positions_user，⛔ 不動照規則欄
SETTING = os.path.join(REPO, "backtest", "forward", "設定_每份金額.json")


def _load_amt(default=20000):
    try:
        with open(SETTING, encoding="utf-8") as fh:
            d_ = json.load(fh); v = int(d_.get("高10", d_.get("每份金額")))
        return v if v > 0 else default
    except (OSError, ValueError, KeyError, TypeError):
        return default


AMT = _load_amt()


def _load_push(default=False):
    """裁定 seq431：高10 是好運種子 ⇒ 前瞻與 LINE 交使用者決定；未決定前名單照出、LINE 不推（照規則欄照記）。
    設定檔鍵「高10_LINE推送」＝true 才推；缺鍵或讀不到一律不推。"""
    try:
        with open(SETTING, encoding="utf-8") as fh:
            return bool(json.load(fh).get("高10_LINE推送", default))
    except (OSError, ValueError, TypeError):
        return default


PUSH = _load_push()
TIES = ("抽籤", "F9")


def _load_tie(path=None, default="抽籤"):
    """D10：設定檔鍵「高10_同分排序」＝ "F9" ⇒ LINE 名單同分依大跌 4 檔 F9；缺鍵、讀不到或其他值 ⇒ "抽籤"。"""
    try:
        with open(path or SETTING, encoding="utf-8") as fh:
            v = json.load(fh).get("高10_同分排序", default)
    except (OSError, ValueError, TypeError, AttributeError):
        return default
    return "F9" if str(v).strip().upper() == "F9" else default


TIE = _load_tie()
LINE_TAG = "- 【LINE】⭐ " if PUSH else "- （LINE 暫停：高10 是否續推等使用者決定，裁定 seq431）"
TITLE = "## 十、52 週新高 10 檔（高10）"
def _wan(a):
    return f"{a / 10000:g} 萬" if a % 1000 == 0 else f"{a:,} 元"


# 裁定 seq420：每月約 30 檔剛好在一年最高點（PTH＝1），「最高 10 檔」實際是在這批裡隨機抽
NOTE_TIE = "每月約 30 檔剛好在一年最高點，「最高 10 檔」是在這批裡隨機抽（同回測做法）；前一晚名單與照規則紀錄可能差 1～2 檔"
# D10（同分排序 F9）：NOTE_TIE 的 F9 版、固定三句之前加的一句
NOTE_TIE_F9 = "每月約 30 檔剛好在一年最高點，同分依大跌 4 檔分數排序；分數也同時才抽籤"
F9_SENT = "同分時依大跌 4 檔分數挑（你 10/21 選；回測：跟抽籤分不出，最多暫定）"
SENT3 = ("看完歷史結果才挑出的版本，最高暫定；2027-11 才檢查", "2005～2014 年不合格（輸在 2008、2011、2014）；單筆約一半會賠，靠少數大賺", "描述，不是買賣建議")
POS_COLS = ["批次", "代號", "名稱", "PTH", "買進日", "買進還原開盤", "買進未還原開盤", "金額佔權益", "排程賣出日", "賣出日", "賣出未還原收盤",
            "出場種類", "R用", "淨報酬", "狀態", "main"]
USR_COLS = ["批次", "代號", "名稱", "名單日", "參考價", "股數", "買進日", "買進價", "狀態", "排程賣出日", "賣出日", "賣出價", "備註", "出場記於"]
EQ_COLS = ["日期", "淨值", "持股數", "0050占淨值", "0050還原收盤", "main"]
_LW: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def ym(d):
    return int(d.year) * 12 + int(d.month) - 1


def ymkey(d):
    return f"{int(d.year):04d}-{int(d.month):02d}"


def ds(d):
    return str(pd.Timestamp(d).date())


# ═════════════ 日曆 ═════════════
def ext_cal(cal, n=420):
    """資料日之後的預計交易日（gate_b_status.future_trading_days；未公告年度扣週末＋固定國定假日）。⇒ (cal_ext, 每個外推日的依據)。"""
    fut, basis = GB.future_trading_days(cal, n, fixed_holidays_uncovered=True)
    return cal.append(fut), list(basis)


def month_ends_live(cal, nxt):
    """D2：researchPTH_freq.month_ends；資料日是月底（下一交易日已跨月）但被判不完整 ⇒ 補進。"""
    ME, MK = PT.month_ends(cal)
    n0 = len(cal); last = cal[-1]
    if nxt is not None and ym(pd.Timestamp(nxt)) != ym(last) and (len(ME) == 0 or int(ME[-1]) != n0 - 1):
        ME = np.r_[np.asarray(ME, np.int64), n0 - 1]; MK = list(MK) + [(int(last.year), int(last.month))]
    return np.asarray(ME, np.int64), list(MK)


def sched_sell(entry, cal_ext):
    """進場月起第 6 個曆月的最後一個交易日（＝ researchPTH.exit_positions 同式；可延伸到外推日曆）。"""
    e = pd.Timestamp(entry); k = ym(e) + (H_HOLD - 1)
    m = (cal_ext.year == k // 12) & (cal_ext.month == k % 12 + 1)
    if not m.any() or ym(cal_ext[-1]) <= k:
        raise SystemExit(f"⛔ 外推日曆不夠長：{ds(e)} 的第 6 個曆月")
    return cal_ext[np.flatnonzero(m)[-1]]


def is_buy_night(asof, nxt):
    """明天（下一交易日）是月初買進日：跨月 ∧ 進場月 ≥ 2026-11。"""
    return ym(pd.Timestamp(nxt)) != ym(pd.Timestamp(asof)) and ym(pd.Timestamp(nxt)) >= START_YM


def sells_on(held, day):
    """held：[(sid, 名, 買進日, 排程賣出日, …)]；排程賣出日 ＝ day 的那些。"""
    return [(h[0], h[1]) for h in held if h[3] == day]


def user_view(usr, asof, nxt):
    """回測線裁定：LINE 的續抱、要賣、空格一律照 positions_user（LINE 名單、每格 2 萬）。
    ⇒ held[(代號,名,買進日,排程賣出日)]、sells_tmr（排程賣出日＝明天）、sold_today（今天記出場且賣出日＝今天）、sold_other（今天記出場、賣出日較早＝照規則提前出場）。"""
    U = usr.fillna("") if len(usr) else usr
    hold = U[U["狀態"] == "持有中"] if len(U) else U
    held = [(r["代號"], r["名稱"], r["買進日"], re.sub(r"（.*$", "", r["排程賣出日"])) for _, r in hold.iterrows()] if len(U) else []
    gone = U[(U["狀態"] == "已出場") & (U["出場記於"] == asof)] if len(U) else U
    return {"held": held, "sells_tmr": sells_on(held, nxt),
            "sold_today": [(r["代號"], r["名稱"]) for _, r in gone.iterrows() if r["賣出日"] == asof] if len(U) else [],
            "sold_other": [(r["代號"], r["名稱"], r["賣出日"]) for _, r in gone.iterrows() if r["賣出日"] != asof] if len(U) else []}


def pick_user(order, held_codes, nfree, nback=3):
    """選股照規則排序（(−PTH, 同值隨機)）由高往下、跳過使用者已持有的代號，取空格數；之後 nback 檔當備位。"""
    rest = [s for s in order if s not in held_codes]
    k = max(int(nfree), 0)
    return rest[:k], rest[k:k + nback]


def shares(price, amt=AMT):
    """LINE 每格 2 萬：floor(2 萬 ÷ 參考價)（零股照算、取整數股）。"""
    if price is None or not np.isfinite(price) or price <= 0:
        return 0
    return int(np.floor(amt / float(price) + 1e-9))


# ═════════════ 世界（用唯讀快照重建；元件全部呼叫既有函式）═════════════
def universe(DATA):
    st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st); U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
    return dict(zip(U["stock_id"], U["market"])), dict(zip(st["stock_id"], st["name"]))


def _wjob2(a):
    sid, mk = a
    _, v = RLU._wjob((sid, mk))
    if v is None:
        return sid, None, None
    _, bad = RA.extra_stock(sid, mk, _LW["data"], _LW["cal"])
    return sid, v, np.flatnonzero(np.asarray(bad, bool)[:len(_LW["cal"])]).astype(np.int64)


def live_world(DATA, log, sids=None, procs=3, nxt=None):
    """researchAscTri_freq.load_world ＋ researchAscTri.load_world ＋ researchPTHpf.build_world 的同一組欄位，資料改為 DATA。
    sids ＝ None ⇒ 全母體（UG.gate3 ∩ 四碼）；否則只建這些（仍須在母體內）。"""
    t0 = time.time()
    D.DATA = DATA
    cal = D.load_calendar(); n0 = len(cal)
    mk, names = universe(DATA)
    todo = sorted(mk) if sids is None else sorted(set(map(str, sids)) & set(mk))
    RLU._G["cal"] = cal; _LW.update(data=DATA, cal=cal)
    res, bad = {}, {}
    if todo:
        with Pool(procs) as pool:
            for sid, v, b in pool.imap_unordered(_wjob2, [(s, mk[s]) for s in todo], chunksize=8):
                if v is not None:
                    res[sid] = v; bad[sid] = set(int(x) for x in b)
    D.DATA = DATA
    ss = sorted(res)

    def stack(k, dt, cut=False):
        if not ss:
            return np.zeros((0, n0), dt)
        A = np.vstack([np.asarray(res[s][k]) for s in ss]).astype(dt)
        return A[:, :n0] if cut else A
    W = {"name": WN, "data": DATA, "cal": cal, "n0": n0, "sids": ss, "ix": {s: i for i, s in enumerate(ss)}, "mk": mk,
         "O": stack("o", float), "PV": stack("pv", bool), "TRD": stack("trd", bool, True), "UPL": stack("upl", bool, True),
         "DNL": stack("dnl", bool, True), "BADPOS": bad, "C": stack("c", float), "NP": n0 + 1, "names": names}
    bench = np.asarray(RR.load_bench(cal), float)
    if not (np.all(np.isfinite(bench)) and np.all(bench > 0)):
        raise SystemExit("⛔ 0050 序列有缺值")
    W["bench"] = bench
    ME, MK = month_ends_live(cal, nxt)
    W["ME"], W["MK"] = ME, MK
    W["EP"] = {L: PT.entry_pos(cal, MK, L) for L in (1, 2)}
    W["XP"] = PTH.exit_positions(W)
    PT._G[WN] = W
    M.finish_world(W)
    log(f"[世界] {ds(cal[0])}～{ds(cal[-1])}｜要 {len(todo)} 檔、建成 {len(ss)} 檔｜{time.time() - t0:.0f}s")
    return W


def _rank_job(a):
    """單股：researchRevLimitUp._wjob ＋ researchAddOn.extra_stock 組成單股世界 ⇒ researchPTH_freq.stock_job 原樣（排序、進場狀態）。
    只回小陣列（全母體跑時不搬整個矩陣）；有待定 EP ⇒ 同一單股世界再跑一次（EP 換成待定版）。"""
    sid, mk = a
    _, v = RLU._wjob((sid, mk))
    if v is None:
        return sid, None
    cal = _LW["cal"]; n0 = len(cal)
    _, bad = RA.extra_stock(sid, mk, _LW["data"], cal)
    w1 = {"cal": cal, "n0": n0, "ix": {sid: 0}, "data": _LW["data"], "mk": {sid: mk},
          "BADPOS": {sid: set(int(x) for x in np.flatnonzero(np.asarray(bad, bool)[:n0]))},
          "PV": np.asarray(v["pv"], bool)[None, :], "TRD": np.asarray(v["trd"], bool)[None, :n0], "O": np.asarray(v["o"], float)[None, :],
          "UPL": np.asarray(v["upl"], bool)[None, :n0], "ME": _LW["ME"], "EP": _LW["EP"]}
    key = f"{WN}_1"
    PT._G[key] = w1
    _, r = PT.stock_job((key, sid))
    if r is None:
        return sid, None
    out = {"ST": r["ST"], "PTH": r["PTH"], "ENT2": r["ENT"][L_SKIP]}
    if _LW.get("EPp") is not None:
        w1["EP"] = _LW["EPp"]
        out["ENT2p"] = PT.stock_job((key, sid))[1]["ENT"][L_SKIP]
    return sid, out


def rank_pass(DATA, cal, ME, MK, sids, procs, ep_pend=None):
    """sids（須在母體內）逐股跑 _rank_job。ep_pend ＝ {形成月序 j: 位置} ⇒ 另算「待定」進場狀態（ENT2p）。"""
    D.DATA = DATA
    mk, _ = universe(DATA)
    EP = {L: PT.entry_pos(cal, MK, L) for L in (1, 2)}
    EPp = None
    if ep_pend:
        EPp = {L: v.copy() for L, v in EP.items()}
        for j, p in ep_pend.items():
            EPp[L_SKIP][j] = p
    RLU._G["cal"] = cal; _LW.update(data=DATA, cal=cal, ME=np.asarray(ME, np.int64), EP=EP, EPp=EPp)
    todo = sorted(set(map(str, sids)) & set(mk))
    return pool_map(_rank_job, [(s, mk[s]) for s in todo], procs)


def pool_map(fn, args, procs):
    out = {}
    if not args:
        return out
    with Pool(procs) as pool:
        for sid, r in pool.imap_unordered(fn, args, chunksize=8):
            out[sid] = r
    return out


# ═════════════ 排序、批次事件 ═════════════
def rank_from(R, j):
    """researchPTH_freq.main 同式：排序母體 ＝ ST ＝ S_OK；前 30%（同值併入）＝ researchPTH_freq.select。⇒ DataFrame（代號序）、meta。"""
    ok = sorted(s for s, r in R.items() if r is not None)
    ST = np.array([R[s]["ST"][j] for s in ok], np.int8)
    PV = np.array([R[s]["PTH"][j] for s in ok], float)
    U = ST == PT.S_OK
    sel, n, k, cut = PT.select(PV, U, True)
    df = pd.DataFrame({"代號": np.array(ok, object)[U], "PTH": PV[U], "入選": np.asarray(sel, bool)[U].astype(int)})
    return df, {"排序母體": int(n), "k": int(k), "切點": float(cut) if np.isfinite(cut) else None, "入選": int(df["入選"].sum())}


def ranks_path(fwd, key):
    return os.path.join(fwd, "ranks", f"ranks_{key}.csv")


def events_path(fwd, key):
    return os.path.join(fwd, "events", f"events_{key}.csv")


def read_ranks(fwd, key):
    return pd.read_csv(ranks_path(fwd, key), dtype={"代號": str}, float_precision="round_trip")


def read_events(fwd, key):
    return pd.read_csv(events_path(fwd, key), dtype={"代號": str}, float_precision="round_trip")


def write_csv(df, path, cols=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    (df if cols is None else df[cols]).to_csv(tmp, index=False, float_format="%.17g", encoding="utf-8-sig")
    os.replace(tmp, path)


def pth_keys(v):
    """D8 排序用 PTH ＝ 歷史上實際用的值：頻率表 events csv 以 pandas 預設寫出、再以 pandas 預設剖析器讀回（researchPTH 讀頻率表、寫事件檔、
    researchPTHpf 讀事件檔都經這一步；最後一位可差 1 ulp，數學上相等的比值〔如 15/16〕因而合併成同值、交給同值隨機）。
    ③ 回放驗：用這個值補位順序與 researchPTHpf.load_events 115 批全同；用全精度 27 批不同、用 16 位有效數字 27 批、15 位 36 批不同。"""
    v = np.asarray(v, float)
    if len(v) == 0:
        return v.copy()
    b = io.StringIO()
    pd.DataFrame({"PTH": v}).to_csv(b, index=False); b.seek(0)
    return pd.read_csv(b)["PTH"].to_numpy(float)


def batch_order(sids, pth, j):
    """researchPTHpf.load_events 同式：當批事件依代號序配 default_rng([SEED_TOP, j]).random；排序 (−PTH, rk)。⇒ rk、名次序。"""
    rk = np.random.default_rng([M.SEED_TOP, int(j)]).random(len(sids))
    o_ = np.lexsort((rk, -pth_keys(pth)))
    return rk, o_


def assemble(W, rows, RES):
    """rows：list of dict(sid, j, e, pth, rk, pre, pend)；pre ＝ 前 20 名（算出場）；pend ＝ 明天合成日。⇒ researchPTHpf.load_events 同欄位 ev。
    出場（pre 且非 pend）：R、出場種類、出場日 ＝ researchPTH.stock_job[(2, 6)][j]；賣出位置 ＝ 到期（1、2）⇒ XP、強制／末根（3、4）⇒ 出場日、資料尾（5）⇒ −1。
    價格閘同 load_events：買價 ＝ O[e] 有效；已出場者 賣價 ＝ 買價×(1＋R) ＝ 賣出日收盤（ffill）（相對差 ≤ 1e−9）。"""
    n = len(rows); ix = W["ix"]; O = np.asarray(W["O"], float); CM = W["CM"]; n0 = W["n0"]
    ev = {k: np.zeros(n, np.int64) for k in ("j", "jm", "e", "X", "sd", "sale")}
    ev.update({"typ": np.zeros(n, np.int8), "R": np.full(n, np.nan), "P": np.full(n, np.nan), "px": np.full(n, np.nan),
               "pth": np.zeros(n), "rk": np.zeros(n), "sid": np.array([r["sid"] for r in rows], object),
               "pre": np.array([r["pre"] for r in rows], bool), "pend": np.array([r["pend"] for r in rows], bool)})
    pk = pth_keys([r["pth"] for r in rows])
    for q, r in enumerate(rows):
        i = ix.get(r["sid"]); j = int(r["j"]); e = int(r["e"])
        if i is None:
            if r["pre"]:
                raise SystemExit(f"⛔ 前 {K_PRE} 名 {r['sid']} 不在世界")
            i = -(q + 1)                                          # 前 20 名以外、不會被補進（window_sim 驗）：給不重複的假股欄
        ev["j"][q] = i; ev["jm"][q] = j; ev["e"][q] = e; ev["pth"][q] = pk[q]; ev["rk"][q] = r["rk"]
        ev["sale"][q] = -1; ev["sd"][q] = -1; ev["X"][q] = n0 + 1
        if r["pend"] and i >= 0:
            ev["P"][q] = CM[i, n0 - 1]                            # 合成的明天：只為讓模擬能計值（收盤沿用資料日），不入紀錄
        if r["pend"] or not r["pre"]:
            continue
        z = RES[r["sid"]][(L_SKIP, H_HOLD)]
        R_, ty, sd = float(z["R"][j]), int(z["T"][j]), int(z["S"][j])
        X = int(W["XP"][(L_SKIP, H_HOLD)][j])
        if int(W["EP"][L_SKIP][j]) != e:
            raise SystemExit(f"⛔ {r['sid']} 進場日 ≠ EP")
        P = O[i, e]
        if not (np.isfinite(P) and P > 0) or ty == 0:
            raise SystemExit(f"⛔ {r['sid']} 形成月 {j}：保留事件無進場價（買價 {P}、出場種類 {ty}）")
        sale = X if ty in (1, 2) else (sd if ty in (3, 4) else -1)
        if ty in (1, 2) and X > n0 - 1:
            raise SystemExit(f"⛔ {r['sid']} 到期越界")
        if ty == 5 and np.isfinite(R_):
            raise SystemExit(f"⛔ {r['sid']} 資料尾 R 有值")
        if sale >= 0:
            if abs(P * (1 + R_) / CM[i, sale] - 1.0) > 1e-9 or sale < e:
                raise SystemExit(f"⛔ {r['sid']} 賣價閘不過")
        ev["typ"][q] = ty; ev["R"][q] = R_; ev["sd"][q] = sd; ev["X"][q] = X; ev["sale"][q] = sale; ev["P"][q] = P; ev["px"][q] = P * (1 + R_)
    return ev


def window_sim(W, ev, t0, synth):
    """D4／D5：researchPTHpf.slot_tr ＋ slot_sim（不洗牌、(e, −PTH, rk) 排序 ＝ researchPTHn.run_slot）跑在 [t0, 資料日]（＋合成的明天）。
    ⇒ S（buys/sells 的 t 為視窗位置、q 為排序後位置；S["q"][q] ＝ ev 列）、視窗長、真實日數。"""
    n_real = W["n0"] - t0
    CM = W["CM"][:, t0:]; Bc = np.asarray(W["Bc"], float)[t0:]; Bo = np.asarray(W["Bo"], float)[t0:]
    if synth:
        CM = np.hstack([CM, CM[:, -1:]]); Bc = np.r_[Bc, Bc[-1]]; Bo = np.r_[Bo, Bc[-1]]
    n_win = len(Bc)
    e2 = ev["e"] - t0
    if (e2 < 1).any():
        raise SystemExit("⛔ 事件進場日不在視窗內（須晚於 t0）")
    sale2 = np.where(ev["sale"] >= 0, ev["sale"] - t0, -1)
    evw = dict(ev); evw["e"] = e2; evw["sale"] = sale2
    o_ = np.lexsort((evw["rk"], -evw["pth"], evw["e"]))
    S = M.slot_sim(M.slot_tr(evw, False, o_), {"n0": n_win, "CM": CM, "Bc": Bc, "Bo": Bo}, M.keep_order())
    bad = [int(S["q"][q]) for _, q, _ in S["buys"] if not ev["pre"][S["q"][q]]]
    if bad:
        raise SystemExit(f"⛔ 補進了前 {K_PRE} 名以外的事件（{bad[:5]}）⇒ D4 前提不成立")
    return S, n_win, n_real


def held_after(S, upto):
    """視窗位置 upto（含）收盤後仍持有的 ev 列（依買進序）。"""
    sold = {q for t, q, _, _ in S["sells"] if t <= upto}
    return [(t, q, amt) for t, q, amt in S["buys"] if t <= upto and q not in sold]


# ═════════════ D10 同分排序 F9（LINE 名單用；函式全部 import researchPTH10tie_freq）═════════════
def _tf():
    """researchPTH10tie_freq（import 時會 chdir 到 ~/tw-p17）⇒ 只在需要時才載入。"""
    from backtest import researchPTH10tie_freq as TF
    return TF


def tie_groups(pk):
    """同分群（researchPTH10tie.build_keys／頻率表 B2 同式）：同批內 PTH（pth_keys 值）完全相同、成員 ≥ 2 ⇒ 組號；其餘 −1。"""
    pk = np.asarray(pk, float)
    grp = np.full(len(pk), -1, np.int64); gid = 0
    for v, c in Counter(pk.tolist()).items():
        if c >= 2:
            grp[pk == v] = gid; gid += 1
    return grp


def f9_ctx(DATA, cal, forms, extra, procs, log=print, mk=None, XD=None, ADJ=None, FDATA=None):
    """researchPTH10tie.build_keys 的資料段（同一批 import 函式）：uni_job（排序日 forms）、財報（AI1 覆寫）、集保、配息、月營收。
    XD／ADJ／FDATA ＝ None ⇒ 沿用模組預設（歷史回放用）；前瞻 ＝ mktdrop_cands 同讀法（XD ＝ fund_dir、ADJ ＝ DATA/adj、FDATA ＝ DATA）。"""
    TF = _tf(); FU, QL, EX5 = TF.FU, TF.QL, TF.EX5
    if XD:
        FU.XD = XD; QL.XD = XD
    if ADJ:
        QL.ADJ = ADJ
    if FDATA:
        FU.FDATA = FDATA
    D.DATA = DATA
    FU._G["cal"] = {DATA: cal}
    allu = FU.universe_sids(DATA, forms[0], forms[-1])
    sids_all = sorted(set(allu) | set(map(str, extra)))
    mk = mk or {}
    mkt = {s: mk.get(s, allu.get(s, "twse")) for s in sids_all}
    t_ = time.time()
    BR = FU.run_jobs([(DATA, s, mkt[s], list(forms)) for s in sids_all], procs, "高10F9")
    FIN, _ = FU.load_fin(); QFIN, _ = QL.load_fin()
    am, _ = TF.ai1_table(FU.XD)
    n6, m6 = TF.ai1_patch(FIN, am); nq, mq = TF.ai1_patch(QFIN, am)
    TD, tdd = FU.load_tdcc()
    DV, mkd, smk = QL.load_div()
    rev, rly, _ = EX5.load_revenue(DATA)
    AV = EX5.avail_pos(list(rev.index), cal); AVA = np.array([AV[p] for p in rev.index], np.int64)
    X = {"W": {"cal": cal, "n0": len(cal), "data": DATA}, "BR": BR, "rev": rev, "rly": rly, "AV": AV, "AVA": AVA, "TD": TD, "DV": DV, "mkd": mkd, "smk": smk}
    info = {"財報籌碼": FU.XD, "配息": QL.ADJ, "價量營收": DATA, "AI1覆寫季列": [n6, nq], "集保末週": str(pd.Timestamp(tdd[-1]).date()),
            "uni_job": f"{len(sids_all)} 檔 × {len(forms)} 排序日｜{time.time() - t_:.0f}s"}
    log(f"[F9 資料] {info}")
    return X, FIN, QFIN, info


def f9_members(X, FIN, QFIN, form, sids, grp, q=None):
    """當批事件（sids、同分群 grp）⇒ 同分群成員的 F6／F7／Q／F9（researchPTH10tie_freq.date_scores ＋ f9_cols 原樣）；q ＝ 每檔列號（預設 0..n−1）。"""
    TF = _tf()
    q = list(range(len(sids))) if q is None else list(q)
    mem = [(str(s), int(g), int(k)) for s, g, k in zip(sids, grp, q) if g >= 0]
    if not mem:
        return pd.DataFrame({"q": pd.Series([], dtype=np.int64), "sid": pd.Series([], dtype=object), "grp": pd.Series([], dtype=np.int64),
                             "F9ok": pd.Series([], dtype=bool), "F9": pd.Series([], dtype=float)})
    d = TF.date_scores(X, pd.Timestamp(form), [s for s, _, _ in mem], {s: g for s, g, _ in mem}, FIN, QFIN)
    d["q"] = d["sid"].map({s: k for s, _, k in mem})
    return TF.f9_cols(d)


def tie_keys(grp, MB):
    """researchPTH10tie.build_keys 的 T1 鍵（同式）：v ＝ F9（高→低）；同分群成員 F9 非有限 ⇒ 算不出（排最後）；非成員 ⇒ 旗標 False、分數 0。"""
    grp = np.asarray(grp, np.int64); n = len(grp)
    v = np.full(n, np.nan)
    if len(MB):
        v[MB["q"].to_numpy(np.int64)] = MB["F9"].to_numpy(float)
    fl = ~np.isfinite(v); fl[grp < 0] = False; v[grp < 0] = 0.0
    return fl, np.where(np.isfinite(v), v, 0.0)


def user_order(rk, pth, flag=None, score=None):
    """使用者版（LINE 名單）補格次序：researchPTH10tie_freq.order_of（lexsort(rk, −分數, 算不出, −PTH)）。flag／score ＝ None ⇒ 抽籤（＝ batch_order 的次序）。"""
    pk = pth_keys(pth); n = len(pk)
    if flag is None:
        return np.lexsort((np.asarray(rk, float), -pk))
    return _tf().order_of({"e": np.zeros(n, np.int64), "pth": pk, "rk": np.asarray(rk, float)}, np.asarray(flag, bool), np.asarray(score, float))


def f9_path(fwd, key):
    return os.path.join(fwd, "f9", f"f9_{key}.csv")


def f9_orders(a, DATA, cal, sha, fwd, jobs, mk, st, log):
    """D10／D11：各批 ⇒ F9 次序。jobs ＝ {名: {"key": 快取名, "form": 排序日, "sids": 代號（代號序）, "pth": PTH, "rk": 原種子 rk}}。
    ⇒ {名: (次序 index 陣列, 說明)}。快取 f9/f9_<快取名>.csv：同分群成員（代號、PTH 鍵）相同才沿用；要新算的批一起跑一次 f9_ctx（排序日合併）。"""
    out, todo, prep = {}, [], {}
    for nm, jb in jobs.items():
        sids = list(map(str, jb["sids"])); pk = pth_keys(jb["pth"]); grp = tie_groups(pk)
        mem = sorted((s, f"{v:.17g}") for s, v, g in zip(sids, pk, grp) if g >= 0)
        cp = f9_path(fwd, jb["key"]); MB = None; src = "新算"
        if not mem:                                                 # 沒有同分群 ⇒ 次序 ＝ 抽籤次序（不必算分數）
            MB = f9_members(None, None, None, jb["form"], sids, grp); src = "無同分群"
        elif os.path.exists(cp):
            C = pd.read_csv(cp, dtype={"sid": str}, float_precision="round_trip")
            if sorted(zip(C["sid"], [f"{v:.17g}" for v in C["PTH"].to_numpy(float)])) == mem:
                ix = {s: k for k, s in enumerate(sids)}
                MB = pd.DataFrame({"q": [ix[s] for s in C["sid"]], "sid": C["sid"], "F9": C["F9"].to_numpy(float), "F9ok": C["F9ok"].astype(bool)})
                src = f"快取 {os.path.basename(cp)}"
        prep[nm] = [sids, pk, grp, mem, cp, MB, src]
        if MB is None:
            todo.append(nm)
    if todo:
        XD = getattr(a, "xd", None)
        if not XD:
            from backtest import mktdrop_cands as MC                 # 財報／法人／融資／集保（每日 archive 沒有）＝ 大跌 4 檔前瞻同一支
            XD = MC.fund_dir(sha, log)
        forms = sorted({jobs[nm]["form"] for nm in todo})
        X, FIN, QFIN, info = f9_ctx(DATA, cal, forms, sorted({s for nm in todo for s, _ in prep[nm][3]}), a.procs, log, mk=mk, XD=XD,
                                    ADJ=os.path.join(DATA, "adj"), FDATA=DATA)
        for nm in todo:
            sids, pk, grp, mem, cp, _, _ = prep[nm]
            MB = f9_members(X, FIN, QFIN, jobs[nm]["form"], sids, grp)
            prep[nm][5] = MB
            if not a.nowrite:
                o_ = MB[["sid", "grp", "F9ok", "F9", "F6_g6", "F7_g6", "Q_g6", "has6", "has7", "hasQ"]].copy()
                o_.insert(2, "PTH", [pk[k] for k in MB["q"]])
                write_csv(o_, cp)
                st.setdefault("F9", {})[jobs[nm]["key"]] = {"排序日": jobs[nm]["form"], "成員": len(o_), "算不出": int((~o_["F9ok"]).sum()),
                                                           "財報籌碼": info["財報籌碼"], "main": sha[:10], "算於": now_tpe()}
    for nm, (sids, pk, grp, mem, cp, MB, src) in prep.items():
        fl, sc = tie_keys(grp, MB)
        o = user_order(jobs[nm]["rk"], jobs[nm]["pth"], fl, sc)
        out[nm] = (o, {"同分群": len(set(grp[grp >= 0].tolist())), "成員": int((grp >= 0).sum()), "算不出": int(fl.sum()), "來源": src})
    return out


def f9_pend(a, DATA, cal, sha, fwd, form, key, pend_list, rk, mk, st, log):
    """D10：明天那批待定事件 ⇒ (使用者版次序（代號）, 說明)＝ f9_orders 單批。"""
    sids = [s for s, _ in pend_list]
    o, info = f9_orders(a, DATA, cal, sha, fwd, {"p": {"key": key, "form": form, "sids": sids, "pth": [p for _, p in pend_list], "rk": rk}}, mk, st, log)["p"]
    return [sids[k] for k in o], info


def f9_rows(rows, orders):
    """D11 F9 照規則：照規則事件列（pend 除外）⇒ 同批改 F9 次序：rk ＝ F9 次序中的位置（researchPTH10tie.ev_with_order 同法）、前 K_PRE 名算出場。
    orders ＝ {形成月序 j: 該批（代號序）的 F9 次序 index}。"""
    out, by = [], {}
    for r in rows:
        if not r["pend"]:
            by.setdefault(r["j"], []).append(r)
    for j, rs in by.items():
        o = np.asarray(orders[j], np.int64)
        if sorted(o.tolist()) != list(range(len(rs))):
            raise SystemExit(f"⛔ F9 次序與事件列數不符（批 {j}）")
        pos = np.empty(len(rs), np.int64); pos[o] = np.arange(len(rs))
        if not np.array_equal(np.lexsort((pos.astype(float), -pth_keys([r["pth"] for r in rs]))), o):
            raise SystemExit(f"⛔ F9 次序位置化後 lexsort ≠ 指定次序（批 {j}）")
        for q, r in enumerate(rs):
            out.append({**r, "rk": float(pos[q]), "pre": bool(pos[q] < K_PRE)})
    return out


def book_trades(S, ev, n_real):
    """window_sim 結果 ⇒ 資料日（含）以前的買進 [(t, ev 列, 金額)]、賣出 {ev 列: (t, 入帳)}。"""
    buys, sells = [], {}
    if S is not None:
        for t, q, amt in S["buys"]:
            if t < n_real:
                buys.append((t, int(S["q"][q]), amt))
        for t, q, amt, proc in S["sells"]:
            if t < n_real:
                sells[int(S["q"][q])] = (t, proc)
    return buys, sells


def book_rows(POS, S, ev, rbuys, rsells, t0, cal, cal_ext, MEd, names, DATA, sha, sdate, warn, tag="照規則紀錄"):
    """照規則式紀錄（positions.csv／positions_f9.csv 同式）：只追加、已寫凍結；出場只補空白欄。⇒ (POS, 新列數)。"""
    posk = {(r["批次"], r["代號"]): i for i, r in POS.iterrows()}
    new_rows = []
    eqv = S["eq"] if S is not None else None
    for t, k, amt in rbuys:
        s = ev["sid"][k]; j = int(ev["jm"][k]); key = (ds(MEd[j]), s)
        o_raw, c_raw = raw_px(DATA, s, cal)
        e_abs = t0 + t
        rec = {"批次": key[0], "代號": s, "名稱": names.get(s, ""), "PTH": fmt(float(ev["pth"][k]), 10), "買進日": ds(cal[e_abs]),
               "買進還原開盤": fmt(float(ev["P"][k]), 6), "買進未還原開盤": fmt(float(o_raw[e_abs]), 4),
               "金額佔權益": fmt(float(amt / eqv[t - 1]), 10), "排程賣出日": sdate(sched_sell(cal[e_abs], cal_ext)), "賣出日": "", "賣出未還原收盤": "",
               "出場種類": "", "R用": "", "淨報酬": "", "狀態": "持有中", "main": sha[:10]}
        if k in rsells:
            ts, proc = rsells[k]; xa = t0 + ts
            rec.update({"賣出日": ds(cal[xa]), "賣出未還原收盤": fmt(last_close(c_raw, xa)[0], 4), "出場種類": PTH.TYP[int(ev["typ"][k])],
                        "R用": fmt(float(ev["R"][k]), 10), "淨報酬": fmt(float(ev["R"][k]) - M.COST, 10), "狀態": "已出場"})
        if key in posk:
            i = posk[key]
            if POS.at[i, "買進日"] != rec["買進日"]:
                warn.append(f"{tag} {key} 買進日 {POS.at[i, '買進日']} ≠ 重算 {rec['買進日']}（照凍結）")
            if POS.at[i, "賣出日"] == "" and rec["賣出日"]:
                for c_ in ("賣出日", "賣出未還原收盤", "出場種類", "R用", "淨報酬", "狀態"):
                    POS.at[i, c_] = rec[c_]
        else:
            new_rows.append(rec)
    simk = {(ds(MEd[int(ev["jm"][k])]), ev["sid"][k]) for _, k, _ in rbuys}
    for key in posk:
        if key not in simk:
            warn.append(f"{tag}有 {key}、重算沒有（照凍結；請回測線查）")
    if new_rows:
        POS = pd.concat([POS, pd.DataFrame(new_rows, columns=POS_COLS)], ignore_index=True)
    return POS, len(new_rows)


def eq_append(eq_p, S, W, t0, n_real, cal_w, sha):
    """equity.csv／equity_f9.csv 同式：只追加沒有的日期。"""
    EQ = read_tab(eq_p, EQ_COLS)
    have = set(EQ["日期"].tolist())
    add = []
    for t in range(n_real):
        d = ds(cal_w[t])
        if d not in have:
            add.append({"日期": d, "淨值": fmt(float(S["eq"][t]), 12), "持股數": str(int(S["nh"][t])),
                        "0050占淨值": fmt(float(S["u"][t] / S["eq"][t]), 8), "0050還原收盤": fmt(float(W["Bc"][t0 + t]), 6), "main": sha[:10]})
    if add:
        write_csv(pd.concat([EQ, pd.DataFrame(add, columns=EQ_COLS)], ignore_index=True), eq_p, EQ_COLS)
    return len(add)


# ═════════════ 段落 ═════════════
def nm_(sid, name):
    return f"{sid} {name}".strip()


def note_sents(tie):
    """LINE 行下方「註」子行的句子：同分句（NOTE_TIE／F9 版）、F9 句（F9 模式）、固定三句。"""
    return [NOTE_TIE_F9, F9_SENT, *SENT3] if tie == "F9" else [NOTE_TIE, *SENT3]


def render(c):
    """c：asof、nxt、started、e0、form0、held[(sid,名,買進日,排程賣出日)]、buys[(sid,名,參考價,股數)]、nfree、backup[(sid,名)]、
    sells_tmr[(sid,名)]、sold_today[(sid,名)]、buy_night、batch、warn[str]、note[str]。⇒ 段落各行（標題起、空行收）。"""
    L = [TITLE, ""]
    asof, nxt = c["asof"], c["nxt"]
    buys = c.get("buys") or []; sells_tmr = c.get("sells_tmr") or []; sold_today = c.get("sold_today") or []
    held = c.get("held") or []
    sold_other = c.get("sold_other") or []
    tmr_sold = {s for s, _ in sells_tmr}
    line_on = bool(buys) or bool(sells_tmr) or bool(sold_today) or bool(sold_other)
    if line_on:
        parts = []
        if sold_other:
            parts.append(f"照規則已提前出場 {len(sold_other)} 檔（壞根或下市，照規則以出場日收盤計）：" + "、".join(f"{nm_(s, n)}（{d}）" for s, n, d in sold_other))
        if sold_today:
            parts.append(f"今天 {asof} 收盤已到期賣出 {len(sold_today)} 檔：" + "、".join(nm_(s, n) for s, n in sold_today))
        if sells_tmr:
            parts.append(f"明天 {nxt} 收盤賣 {len(sells_tmr)} 檔（收盤賣）：" + "、".join(nm_(s, n) for s, n in sells_tmr))
        if buys:
            b = f"明天 {nxt} 開盤買 {len(buys)} 檔（每檔約 {_wan(AMT)}）：" + "、".join(
                f"{nm_(s, n)}（參考價 {p:,.2f}｜{k} 股）" for s, n, p, k in buys)
            if c["nfree"] > len(buys):
                b += f"；空 {c['nfree'] - len(buys)} 格放 0050"
            parts.append(b)
        keep = [(s, n) for s, n, _, _ in held if s not in tmr_sold]
        parts.append(f"續抱 {len(keep)} 檔" + ("：" + "、".join(nm_(s, n) for s, n in keep) if keep else ""))
        f9 = c.get("tie", "抽籤") == "F9"                            # D10：同分排序 F9 ⇒ NOTE_TIE 換 F9 版、固定三句之前加 F9_SENT
        if c.get("backup"):
            parts.append(f"備位（明天有股票開盤鎖漲停或沒成交而買不到時，{'照同一排序' if f9 else '照規則'}往下遞補）：" + "、".join(nm_(s, n) for s, n in c["backup"]))
        # D12（使用者 10/21「下面五句都不用寫」，情報 2102）：LINE 行只留名單內容（賣、買、續抱、備位）；同分句、F9 句、固定三句移到下一行「  - 註：」（不帶【LINE】）
        L.append(LINE_TAG + "52 週新高 10 檔（高10）：" + "；".join(parts))
        L.append("  - 註：" + "｜".join(note_sents(c.get("tie", "抽籤"))))
        if buys and f9:
            L.append("  - 名單依今晚資料；同分（都在一年最高點）依大跌 4 檔分數排序（形成月底資料）、分數也同才照規則隨機；照規則紀錄仍是原規則隨機排序，"
                     "兩邊不同時另有說明行；明天若有候選股開盤鎖漲停或沒成交，照規則紀錄可能換成別檔（以隔天紀錄為準）")
        elif buys:
            L.append("  - 名單依今晚資料；同分（都在一年最高點）照規則隨機排序，明天若有候選股開盤鎖漲停或沒成交，照規則紀錄可能換成別檔（以隔天紀錄為準）")
    else:
        if not c["started"]:
            L.append(f"- 尚未開始：{c['e0']} 開盤買第一批（用 {c['form0']} 收盤排序）；目前 0／{NS} 格（全放 0050）")
        else:
            nh = len(held)
            s = f"- 持有 {nh}／{NS} 格（照 LINE 名單；其餘 0050）"
            if held:
                s += "：" + "、".join(nm_(sd, n) for sd, n, _, _ in held)
                nxt_sell = min(x for _, _, _, x in held)
                k = sum(1 for _, _, _, x in held if x == nxt_sell)
                s += f"｜下次到期 {nxt_sell} 收盤賣 {k} 檔"
            if nh < NS:
                s += f"｜空 {NS - nh} 格下個月初補"
            L.append(s)
    for w in c.get("note") or []:
        L.append(f"  - {w}")
    for w in c.get("warn") or []:
        L.append(f"  - ⚠ {w}")
    return L + [""]


def put(md, L):
    """名單檔：拿掉舊的第十節、接在檔尾；暫存檔 ＋ os.replace；寫完比對其他段逐字不變。"""
    s = open(md, encoding="utf-8").read()
    pat = r"\n" + re.escape(TITLE) + r".*?(?=\n## |\Z)"
    base = re.sub(pat, "", s, flags=re.S).rstrip("\n")
    new = base + "\n\n" + "\n".join(L).rstrip("\n") + "\n"
    tmp = md + ".pth10.tmp"
    open(tmp, "w", encoding="utf-8").write(new)
    chk = re.sub(pat, "", open(tmp, encoding="utf-8").read(), flags=re.S).rstrip("\n")
    if chk != base:
        os.remove(tmp)
        raise SystemExit("⛔ 寫入比對不符（其他段會變），未寫")
    os.replace(tmp, md)


# ═════════════ 狀態檔 ═════════════
def load_state(fwd):
    p = os.path.join(fwd, "state.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"排序": {}, "事件": {}, "名單": {}}


def read_tab(path, cols):
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def raw_px(DATA, sid, cal):
    df = pd.read_csv(os.path.join(DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "open", "close"]).drop_duplicates("date")
    df.index = pd.to_datetime(df["date"])
    o = pd.to_numeric(df["open"], errors="coerce").reindex(cal).to_numpy(float)
    c = pd.to_numeric(df["close"], errors="coerce").reindex(cal).to_numpy(float)
    return o, c


def last_close(c, t):
    k = np.flatnonzero(np.isfinite(c[:t + 1]) & (c[:t + 1] > 0))
    return (float(c[k[-1]]), int(k[-1])) if len(k) else (np.nan, -1)


def fmt(x, d=6):
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else (f"{x:.{d}f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x))


# ═════════════ 主流程 ═════════════
def run(a, log=print):
    T0 = time.time()
    fwd = a.fwd or FWD
    if getattr(a, "data", None):                                 # 測試用：直接指定快照資料夾（sha 欄記資料夾名）
        DATA = os.path.expanduser(a.data); sha = a.sha or os.path.basename(os.path.dirname(DATA.rstrip("/")))
    else:
        sha = a.sha or subprocess.run(["git", "-C", REPO, "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
        DATA = os.path.expanduser(f"~/h2data/{sha}/data")
    if not os.path.isdir(os.path.join(DATA, "stocks")):
        raise SystemExit(f"⛔ 找不到唯讀快照 {DATA}")
    D.DATA = DATA
    cal = D.load_calendar(); n0 = len(cal); asof = cal[-1]
    if a.asof and ds(asof) != a.asof:
        raise SystemExit(f"⛔ 快照資料日 {ds(asof)} ≠ --asof {a.asof}")
    cal_ext, basis = ext_cal(cal)
    fut = cal_ext[n0:]; nxt = nxt_real = fut[0]
    ext_note = {ds(d): b for d, b in zip(fut, basis)}

    def sdate(d):
        s = ds(d)
        return s + ("（外推）" if "只扣週末" in ext_note.get(s, "") else "")
    st = load_state(fwd)
    st.setdefault("排序", {}); st.setdefault("事件", {}); st.setdefault("名單", {})
    ME, MK = month_ends_live(cal, nxt)
    EP2 = PT.entry_pos(cal, MK, L_SKIP)
    MEd = [cal[p] for p in ME]
    jF0 = [j for j, d in enumerate(MEd) if ym(d) == START_YM - L_SKIP]
    if not jF0:
        raise SystemExit("⛔ 日曆裡沒有 2026-09 月底")
    jF0 = jF0[0]
    form0 = ds(MEd[jF0])
    js = list(range(jF0, len(ME)))                                # 形成月 ≥ 2026-09、月底已在日曆
    keys = {j: ymkey(MEd[j]) for j in js}
    # 明天是不是月初買進日
    buy_night = is_buy_night(asof, nxt)
    if a.preview_buy:
        buy_night = True
        ent_ym = ym(MEd[-1]) + L_SKIP
        nxt = [d for d in fut if ym(d) == ent_ym][0]
    j_p = None
    if buy_night:
        cand = [j for j in js if ym(MEd[j]) + L_SKIP == ym(nxt)]
        if not cand:
            raise SystemExit(f"⛔ 明天 {ds(nxt)} 的形成月月底不在日曆")
        j_p = cand[0]
        if not a.preview_buy and int(EP2[j_p]) >= 0:
            raise SystemExit("⛔ 明天的批次進場日已在日曆（日曆／休市表不一致）")
    # ── D3 排序快取
    miss = [j for j in js if not os.path.exists(ranks_path(fwd, keys[j]))]
    RNK = {}
    if miss:
        t_ = time.time()
        R = rank_pass(DATA, cal, ME, MK, universe(DATA)[0].keys(), a.procs)
        for j in miss:
            df, meta = rank_from(R, j)
            RNK[keys[j]] = (df, meta)
            if not a.nowrite:                                     # 快取（只依資料、可重算）先寫，後面失敗不必重跑全母體
                write_csv(df, ranks_path(fwd, keys[j]))
                st["排序"][keys[j]] = {**meta, "main": sha[:10], "算於": now_tpe()}
        log(f"[排序] 補 {[keys[j] for j in miss]}（全母體 {len(R)} 檔）｜{time.time() - t_:.0f}s")
        del R
    for j in js:
        if keys[j] not in RNK:
            RNK[keys[j]] = (read_ranks(fwd, keys[j]), st["排序"].get(keys[j]))
    actual = [j for j in js if int(EP2[j]) >= 0 and ym(cal[int(EP2[j])]) >= START_YM]
    need_ev = [j for j in actual if not os.path.exists(events_path(fwd, keys[j]))]
    EVC = {keys[j]: read_events(fwd, keys[j]) for j in actual if j not in need_ev}
    # 前 20 名（已有事件快取的批）
    PRE_S = set()
    for j in actual:
        if j in need_ev:
            continue
        E = EVC[keys[j]]; E = E[E["保留"] == 1].sort_values("代號")
        rk, o_ = batch_order(E["代號"].tolist(), E["PTH"].to_numpy(float), j)
        PRE_S |= set(E["代號"].to_numpy()[o_[:K_PRE]].tolist())
    sel_of = {j: RNK[keys[j]][0].loc[RNK[keys[j]][0]["入選"] == 1, "代號"].tolist() for j in js}
    # ── D3 批次事件（e 已在日曆）＋ D5 明天的待定事件（待定：壞根只看到資料日；stock_job 先判壞根(t,e]）
    ENTS = {}
    jev = need_ev + ([j_p] if j_p is not None else [])
    if jev:
        t_ = time.time()
        RE = rank_pass(DATA, cal, ME, MK, set(s for j in jev for s in sel_of[j]), a.procs, {j_p: n0 - 1} if j_p is not None else None)
        for j in jev:
            fld = "ENT2p" if j == j_p else "ENT2"
            ENTS[j] = [(s, int(RE[s][fld][j]) if RE.get(s) is not None else PT.E_NA) for s in sorted(sel_of[j])]
        log(f"[進場狀態] 批 {[keys[j] for j in jev]}｜{len(RE)} 檔｜{time.time() - t_:.0f}s")
    need_s = set(PRE_S)
    for j in need_ev:
        E_ = [s for s, x in ENTS[j] if x == PT.E_KEEP]
        rk, o_ = batch_order(E_, RNK[keys[j]][0].set_index("代號").loc[E_, "PTH"].to_numpy(float), j)
        need_s |= set(np.array(E_, object)[o_[:K_PRE]].tolist())
    pend_list = []
    if j_p is not None:
        dfp = RNK[keys[j_p]][0].set_index("代號")
        pend_list = [(s, float(dfp.loc[s, "PTH"])) for s, x in ENTS[j_p] if x not in (PT.E_BAD, PT.E_NA)]
        rk_p, o_p = batch_order([s for s, _ in pend_list], [p for _, p in pend_list], j_p)
        need_s |= {pend_list[k][0] for k in o_p[:K_PRE]}
    # ── D10／D11 F9 次序（世界之前算：F9 照規則的前 20 名要進世界）：已進場各批（保留事件）＋ 明天那批（使用者版、F9 模式）
    tie_mode = getattr(a, "tie", None) or TIE
    tie_used = tie_mode if tie_mode in TIES else "抽籤"
    f9warn, F9O, f9_ok, jobs = [], {}, False, {}
    for j in actual:
        if j in need_ev:
            E_ = [s for s, x in ENTS[j] if x == PT.E_KEEP]
            P_ = RNK[keys[j]][0].set_index("代號").loc[E_, "PTH"].to_numpy(float) if E_ else np.zeros(0)
        else:
            E = EVC[keys[j]]; E = E[E["保留"] == 1].sort_values("代號"); E_ = E["代號"].tolist(); P_ = E["PTH"].to_numpy(float)
        jobs[("r", j)] = {"key": "rule_" + keys[j], "form": ds(MEd[j]), "sids": E_, "pth": P_, "rk": batch_order(E_, P_, j)[0]}
    if j_p is not None and tie_used == "F9" and pend_list:
        jobs[("p", j_p)] = {"key": keys[j_p], "form": ds(MEd[j_p]), "sids": [s for s, _ in pend_list], "pth": [p for _, p in pend_list], "rk": rk_p}
    if jobs:
        try:
            F9O = f9_orders(a, DATA, cal, sha, fwd, jobs, universe(DATA)[0], st, log)
            f9_ok = True
        except (Exception, SystemExit) as ex:                       # noqa: BLE001  F9 失敗不擋名單：F9 照規則這晚不更新、LINE 名單退回抽籤，標 ⚠
            f9warn.append(f"F9 次序算不出（{type(ex).__name__}: {str(ex)[:200]}）⇒ 這晚 F9 照規則紀錄不更新（下次補）"
                          + ("；LINE 名單同分改用抽籤" if ("p", j_p) in jobs else ""))
            if ("p", j_p) in jobs:
                tie_used = "抽籤"
    for (kind, j), (o, _) in F9O.items():
        if kind == "r":
            need_s |= set(np.array(jobs[(kind, j)]["sids"], object)[o[:K_PRE]].tolist())
    plan = st["名單"]
    need_s |= {r[0] for p in plan.values() for r in p.get("rows", [])}
    usr = read_tab(os.path.join(fwd, "positions_user.csv"), USR_COLS)
    for c_ in USR_COLS:
        if c_ not in usr:
            usr[c_] = ""
    W = live_world(DATA, log, sorted(need_s), a.procs, nxt_real)
    if jev:
        for j in need_ev:
            df = RNK[keys[j]][0].set_index("代號")
            E = pd.DataFrame({"代號": [s for s, _ in ENTS[j]], "PTH": [float(df.loc[s, "PTH"]) for s, _ in ENTS[j]],
                              "進場日": ds(cal[int(EP2[j])]), "狀態": [PT.ENAME.get(x, "無資料") for _, x in ENTS[j]],
                              "保留": [int(x == PT.E_KEEP) for _, x in ENTS[j]]})
            EVC[keys[j]] = E
            if not a.nowrite:
                write_csv(E, events_path(fwd, keys[j]))
                st["事件"][keys[j]] = {"進場日": ds(cal[int(EP2[j])]), "入選": len(E), "保留": int(E["保留"].sum()), "main": sha[:10], "算於": now_tpe()}
    # ── 事件列
    rows = []
    for j in actual:
        E = EVC[keys[j]]; E = E[E["保留"] == 1].sort_values("代號").reset_index(drop=True)
        rk, o_ = batch_order(E["代號"].tolist(), E["PTH"].to_numpy(float), j)
        pre = np.zeros(len(E), bool); pre[o_[:K_PRE]] = True
        for q in range(len(E)):
            rows.append({"sid": E["代號"][q], "j": j, "e": int(EP2[j]), "pth": float(E["PTH"][q]), "rk": float(rk[q]), "pre": bool(pre[q]), "pend": False})
    pend_order = []
    if j_p is not None:
        pend_order = [pend_list[k][0] for k in o_p]
        prep = np.zeros(len(pend_list), bool); prep[o_p[:K_PRE]] = True
        for q, (s, p) in enumerate(pend_list):
            rows.append({"sid": s, "j": j_p, "e": n0, "pth": p, "rk": float(rk_p[q]), "pre": bool(prep[q]), "pend": True})
    f9_book = f9_ok and bool(actual)                                # D11：F9 照規則（第三本）＝ 照規則事件列、同批改 F9 次序（不含明天的待定批）
    rows_f9 = f9_rows(rows, {j: F9O[("r", j)][0] for j in actual}) if f9_book else []
    pre_s = sorted({r["sid"] for r in rows + rows_f9 if r["pre"] and not r["pend"]})
    RES = pool_map(PTH.stock_job, [(WN, s) for s in pre_s], a.procs)
    ev = assemble(W, rows, RES) if rows else None
    started = bool(actual)
    t0 = (int(EP2[jF0]) - 1) if started else n0 - 1
    S = None
    if ev is not None:
        S, n_win, n_real = window_sim(W, ev, t0, j_p is not None)
    else:
        n_real = n0 - t0
    S9 = ev9 = None
    if rows_f9:
        ev9 = assemble(W, rows_f9, RES)
        S9, _, nr9 = window_sim(W, ev9, t0, False)
        if nr9 != n_real:
            raise SystemExit("⛔ F9 照規則視窗長 ≠ 照規則")
    # ── 整理
    names = W["names"]
    cal_w = cal[t0:]

    def held_of(S_, ev_):
        return [(ev_["sid"][int(S_["q"][q])], names.get(ev_["sid"][int(S_["q"][q])], ""), ds(cal_w[t]), ds(sched_sell(cal_w[t], cal_ext)), int(S_["q"][q]))
                for t, q, amt in held_after(S_, n_real - 1)] if S_ is not None else []
    held = held_of(S, ev); held9 = held_of(S9, ev9)
    rule_buys, rule_sells = book_trades(S, ev, n_real)
    picks = [int(S["q"][q]) for t, q, amt in S["buys"] if t >= n_real] if S is not None else []
    rule_picks = [ev["sid"][k] for k in picks]
    # ── 前瞻紀錄（D6；D11 F9 照規則同式另一本）
    warn, note = list(f9warn), []
    pos_p = os.path.join(fwd, "positions.csv")
    POS, n_new = book_rows(read_tab(pos_p, POS_COLS), S, ev, rule_buys, rule_sells, t0, cal, cal_ext, MEd, names, DATA, sha, sdate, warn)
    pos9_p = os.path.join(fwd, "positions_f9.csv")
    POS9 = n_new9 = None
    if S9 is not None:
        b9, s9 = book_trades(S9, ev9, n_real)
        POS9, n_new9 = book_rows(read_tab(pos9_p, POS_COLS), S9, ev9, b9, s9, t0, cal, cal_ext, MEd, names, DATA, sha, sdate, warn, "F9 照規則紀錄")
    # 使用者實際（LINE 名單每格 2 萬）
    usr_new = []
    usrk = {(r["批次"], r["代號"]): i for i, r in usr.iterrows()}
    for e_s, p in list(plan.items()):
        e_t = pd.Timestamp(e_s)
        if e_t > asof:
            continue
        if e_t not in cal:
            warn.append(f"名單買進日 {e_s} 不是交易日（名單作廢）")
            del plan[e_s]; continue
        e_abs = int(cal.get_loc(e_t))
        for sid, nm, ref, sh in p["rows"]:
            if (p["批次"], sid) in usrk:
                continue
            o_raw, _ = raw_px(DATA, sid, cal)
            i = W["ix"].get(sid)
            ok = i is not None and bool(W["TRD"][i, e_abs]) and np.isfinite(W["O"][i, e_abs]) and W["O"][i, e_abs] > 0 and not bool(W["UPL"][i, e_abs])
            why = "" if ok else ("開盤鎖漲停" if (i is not None and bool(W["UPL"][i, e_abs])) else "沒成交或開盤無效")
            usr_new.append({"批次": p["批次"], "代號": sid, "名稱": nm, "名單日": p["名單日"], "參考價": fmt(float(ref), 4), "股數": str(sh),
                            "買進日": e_s if ok else "", "買進價": fmt(float(o_raw[e_abs]), 4) if ok else "", "狀態": "持有中" if ok else "買不到",
                            "排程賣出日": sdate(sched_sell(e_t, cal_ext)), "賣出日": "", "賣出價": "", "備註": why})
        rset = {(r["批次"], r["代號"]) for _, r in POS.iterrows() if r["買進日"] == e_s} | {(ds(MEd[int(ev["jm"][k])]), ev["sid"][k]) for t, k, _ in rule_buys if ds(cal[t0 + t]) == e_s}
        pset = {(p["批次"], r[0]) for r in p["rows"]}
        if rset != pset:
            note.append(f"{e_s} 照規則紀錄與名單不同：只在名單 {sorted(s for _, s in pset - rset)}、只在照規則 {sorted(s for _, s in rset - pset)}")
        st.setdefault("名單歷史", {})[e_s] = {**p, "照規則": sorted(s for _, s in rset), "記於": ds(asof)}
        del plan[e_s]
    if usr_new:
        usr = pd.concat([usr, pd.DataFrame(usr_new, columns=USR_COLS)], ignore_index=True).fillna("")
    for i, r in usr.iterrows():
        if r["狀態"] != "持有中":
            continue
        rr = POS[(POS["批次"] == r["批次"]) & (POS["代號"] == r["代號"])]
        xd = rr["賣出日"].iloc[0] if len(rr) and rr["賣出日"].iloc[0] else ""
        if not xd:
            sd_ = re.sub(r"（.*$", "", r["排程賣出日"])
            if pd.Timestamp(sd_) <= asof:
                xd = sd_
        if xd:
            _, c_raw = raw_px(DATA, r["代號"], cal)
            px, kk = last_close(c_raw, int(cal.searchsorted(pd.Timestamp(xd), "right")) - 1)
            usr.at[i, "賣出日"] = xd; usr.at[i, "賣出價"] = fmt(px, 4); usr.at[i, "狀態"] = "已出場"; usr.at[i, "出場記於"] = ds(asof)
            if kk >= 0 and ds(cal[kk]) != xd:
                usr.at[i, "備註"] = (r["備註"] + "；" if r["備註"] else "") + f"賣出日無成交，用 {ds(cal[kk])} 收盤"
    # ── LINE 的續抱、賣、空格一律照 positions_user（回測線裁定）；選股照規則順序由高往下、跳過使用者已持有
    uv = user_view(usr, ds(asof), ds(nxt))
    nfree = NS - len(uv["held"]) if buy_night else 0
    buys, backup = [], []
    user_ord, f9i = pend_order, None
    if j_p is not None and tie_used == "F9" and ("p", j_p) in F9O:  # D10：LINE 名單同分依 F9（照規則欄不動；次序在世界之前已算）
        o9, f9i = F9O[("p", j_p)]
        user_ord = [pend_list[k][0] for k in o9]
        note.append(f"同分排序 F9（設定「高10_同分排序」；排序日 {ds(MEd[j_p])}）：同分群 {f9i['同分群']} 組 {f9i['成員']} 檔、"
                    f"分數算不出 {f9i['算不出']} 檔排最後（{f9i['來源']}）；照規則紀錄仍用原規則隨機")
    if j_p is not None:
        pk, bk = pick_user(user_ord, {h[0] for h in uv["held"]}, nfree)
        for s in pk:
            _, c_ = raw_px(DATA, s, cal)
            ref, _ = last_close(c_, n0 - 1)
            buys.append((s, names.get(s, ""), ref, shares(ref)))
        backup = [(s, names.get(s, "")) for s in bk]
        if sorted(pk) != sorted(rule_picks):
            note.append(f"照規則紀錄明天會買 {sorted(rule_picks)}；LINE 名單（照你的持股與空格）{sorted(pk)}（只記、不推）")
    # 使用者持有 vs 照規則持有
    u_held = sorted(h[0] for h in uv["held"])
    r_held = sorted(h[0] for h in held)
    if started and u_held != r_held and len(usr):
        note.append(f"LINE 名單持有 {u_held} ≠ 照規則持有 {r_held}（LINE 的續抱、賣照 LINE 名單；照規則紀錄另記）")
    f_held = sorted(h[0] for h in held9)
    if S9 is not None and f_held != u_held and len(usr):
        note.append(f"F9 照規則持有 {f_held} ≠ LINE 名單持有 {u_held}（F9 照規則紀錄另記）")
    # 名單（明天要買）
    if j_p is not None and not a.preview_buy and PUSH:                   # seq431：LINE 暫停時不推 ⇒ 使用者不會買 ⇒ 不記 positions_user（照規則欄照記）
        plan[ds(nxt)] = {"批次": ds(MEd[j_p]), "名單日": ds(asof), "rows": [[s, n, float(p), int(k)] for s, n, p, k in buys], "main": sha[:10],
                         "同分排序": tie_used}
    # ── 段落
    ctx = {"asof": ds(asof), "nxt": ds(nxt), "started": started, "e0": ds(cal[int(EP2[jF0])]) if started else ds([d for d in cal_ext if ym(d) == START_YM][0]),
           "form0": form0, "held": uv["held"], "buys": buys, "nfree": nfree, "backup": backup,
           "sells_tmr": uv["sells_tmr"], "sold_today": uv["sold_today"], "sold_other": uv["sold_other"], "warn": warn, "note": note, "tie": tie_used}
    Lsec = render(ctx)
    # ── 寫檔（先狀態、後 md）
    if not a.nowrite:
        os.makedirs(fwd, exist_ok=True)
        write_csv(POS, pos_p, POS_COLS)
        if len(usr):
            write_csv(usr, os.path.join(fwd, "positions_user.csv"), USR_COLS)
        if S is not None and started:
            eq_append(os.path.join(fwd, "equity.csv"), S, W, t0, n_real, cal_w, sha)
        if S9 is not None and started:                              # D11 F9 照規則（第三本）：同式、只追加
            write_csv(POS9, pos9_p, POS_COLS)
            eq_append(os.path.join(fwd, "equity_f9.csv"), S9, W, t0, n_real, cal_w, sha)
        st.update({"資料日": ds(asof), "main": sha[:10], "明天": ds(nxt), "明天月初買進": bool(j_p is not None), "照規則持有": r_held,
                   "使用者持有": u_held, "F9照規則持有": f_held if S9 is not None else None, "更新": now_tpe()})
        tmp = os.path.join(fwd, "state.json.tmp")
        json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, os.path.join(fwd, "state.json"))
        with open(os.path.join(fwd, "runlog.md"), "a", encoding="utf-8") as fh:
            fh.write(f"- [{now_tpe()} 台北] 資料日 {ds(asof)}｜main {sha[:10]}｜照規則持有 {len(held)}｜新買 {n_new}｜F9 照規則持有 {len(held9) if S9 is not None else '—'}｜F9 新買 {n_new9 if S9 is not None else '—'}｜明天月初買進 {j_p is not None}"
                     f"（名單 {[b[0] for b in buys]}）｜同分 {tie_used}｜LINE {'有' if any('【LINE】' in x for x in Lsec) else '無'}"
                     + (f"｜⚠ {'；'.join(warn)}" if warn else "") + f"｜{time.time() - T0:.0f}s\n")
    if a.md:
        put(a.md, Lsec)
    print("\n".join(Lsec))
    log(f"- 高10：{Lsec[2].lstrip('- ')}｜{time.time() - T0:.0f}s")
    return Lsec, {"S": S, "ev": ev, "W": W, "held": held, "buys": buys, "t0": t0, "backup": backup, "tie": tie_used, "f9": f9i,
                  "rule_order": pend_order, "user_order": user_ord, "rule_picks": rule_picks, "S9": S9, "ev9": ev9, "held9": held9}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof"); ap.add_argument("--md"); ap.add_argument("--sha"); ap.add_argument("--fwd")
    ap.add_argument("--nowrite", action="store_true"); ap.add_argument("--preview-buy", action="store_true"); ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--data", help="測試用：直接指定快照 data 資料夾")
    ap.add_argument("--tie", choices=TIES, help="測試用：覆寫設定檔「高10_同分排序」")
    ap.add_argument("--xd", help="測試用：財報／法人／融資／集保資料夾（預設 mktdrop_cands.fund_dir(main sha)）")
    a = ap.parse_args()
    run(a)


if __name__ == "__main__":
    main()

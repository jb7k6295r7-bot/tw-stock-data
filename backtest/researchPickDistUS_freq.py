# -*- coding: utf-8 -*-
"""美股「產業線挑法」好壞比例分佈 seq2【頻率表・⛔ 不附報酬】（美股策略線 登錄 sha 3ce4e52205c08a14，2026-10-23 21:28；
裁定 seq464 核：描述、⛔ 不判、不計 N；三種分佈與台股 seq1 同口徑；同檔同組重複窗 36 個月；台股 seq1、美股 seq2 頻率表並交）——回測線計算子代理。
⛔ 只數事件、n_eff、重複窗、A／B／轉強成立率、走得完、斷點、下市、GICS；⛔ 不讀、不算、不存任何進場後報酬（seq366）。
⛔⛔ 私有資料：us-stock-data 是私有 repo ⇒ resultsPickDistUS/ 只放彙總與逐事件【代號、日期、布林】；⛔ 不放任何價格、報酬、財報原值；
   逐事件位置檔存 ~/pkdwork_us（repo 外）。
⛔ 不 commit、不改既有檔；researchUSC（rworld）、researchUSA4（load_fund、q_last、yoy_at、key_at、sector_at）、researchUSA2_data（no_ohlc_tickers、idx_member）、
   researchIndMom_freq（reg_check）、researchTriple_freq（make_events）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDistUS_freq [--out DIR]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDistUS_freq_check
輸出 backtest/resultsPickDistUS/freq/：freq.json、freq.csv、base.csv、yearly.csv、gics.csv、index.csv、equiv.csv、noprice.csv、
      events_甲.csv.gz、events_乙.csv.gz、events_丙.csv.gz、events_丁.csv.gz（代號、日期、布林；⛔ 無價格）、run.log

═══ 讀法（U 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-24（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 U0 資料 ★：A4 世界（~/us_work/a4/world.npz；us-stock-data 881c86a，聯集轉接層 researchUSA2_data；＝ C3、C3s、去年漲最多同一份；登錄 §四「S&P 400 整段缺價 48、
    S&P 500 18」即此版）〔另一讀法：最新 main 重建〕。日曆 2015-11-02～2026-10-06、K 棒 2015-12-01 起、資料尾 ＝ 最後一個有個股 K 棒的交易日（2026-10-05）。
    收盤、開盤 ＝ 轉接層還原價（含息與分割）。季營收 ＝ researchUSA4.load_fund（S&P 500＋400，first_filed 次一交易日為可用日、代號重用分段 key_at）。
    GICS ＝ sector_pit（Wikipedia 歷史版，非官方；researchUSA4.sector_at，判斷日當時）。
 U1 判斷日 d ＝ 每月最後一個交易日（世界日曆）；判斷窗 2018-12～2023-09（登錄 §二）；2023-10 起 ＝ 段外（只報件數）。單一段 ★（登錄沒分段）。
    母體 ＝ d 當天 S&P 500 或 S&P 400（point-in-time m5 ∨ m4）∧ d 有有效 K 棒 ★（無價者另列，U8）。進場 e ＝ d＋1 還原開盤；
    ★ 可進場 ＝ e 有有效 K 棒且開盤 ＞ 0 ∧ (d, e] 無斷點（美股無漲跌停閘）。
 U2 斷點（硬斷點）★ ＝ 轉接層 pb（來源接縫、同日拆股配息）∪ 連續 ≥ 5 個交易日無 K 棒後的第一根（只數第一根～最後一根之間；＝ 台股 seq335 同參數、
    美股登錄 seq2 §二④）。
 U3 A 有大漲前例：存在 d−750 ≤ i ＜ j ≤ d（日曆位置）使 收盤_j ÷ 收盤_i ≥ 3；★ (i, j] 有斷點 ⇒ 這一對不算；只看有效 K 棒（登錄 §一字面「判斷日前 750 個交易日內」，
    ⚠ 與台股版「任一 750 日窗」不同、照寫為限制）。★ A 可判 ＝ 第一根有效 K 棒 ≤ d − 750；不可判者照式算、⛔ 不剔除、件數照報。
    描述欄：A任一窗 ＝ 台股口徑（K 棒起點 2015-12 起任一 750 日窗），報一致率。
 U4 B 還沒漲過：c[d] ＜ 2 × min(收盤[d−499 … d]) ∧ c[d] ≤ 0.85 × max(收盤[d−499 … d])（★ 500 個日曆位置含判斷日，＝ 台股 P4）；
    ★ B 可判 ＝ 第一根有效 K 棒 ≤ d−499 且 (d−499, d] 無斷點；不可判 ⇒ B 為假。
 U5 季營收轉強（乙臂；美股小部位 seq2 甲或乙）：用可用日 ≤ d 的季報；★ 最新一季期末距 d ＞ 200 日 ⇒ 不可判（A4 q_last 同式）。
    甲 ＝ 最新一季年增（researchUSA4.yoy_at）− 近 4 季合計年增（含最新一季：連續 8 季〔A4 q_last k＝8，相鄰期末 60～120 日〕的後 4 季和 ÷ 前 4 季和 − 1）≥ 0.05
       （★ 近 4 季含最新一季，對應台股 rev_metrics yoy12 含本期；〔另一讀法：最新一季之前的 4 季〕）。
    乙 ＝ 首次創 8 季新高：hi8 ＝ 連續 8 季中最新一季 ＞ 前 7 季最高（★ 本線 A4／prep rev_hi8 口徑〔另一讀法：與前 8 季比〕）∧ 上一季的 hi8 不為真（連續 9 季；不可判 ⇒ 視為不為真，同台股乙）。
    轉強 ＝ 甲 ∨ 乙；甲、hi8 皆不可算 ⇒ 轉強不可判 ⇒ 為假（件數照報）。
 U6 臂：甲 A∧B｜乙 A∧B∧轉強｜丙（對照一）B∧¬A｜丁（對照二）全母體（d 當天母體且可進場）。
    甲乙丙：同檔同臂 36 個月內只取第一次（判斷日月序；researchTriple_freq.make_events 原式；取用不論可否進場；從 2018-12 起算）。丁 ★ 不去重（同台股 P6）。
 U7 走得完 ＝ e ＋ 750 ≤ 資料尾。主格 ＝ 可進場 ∧ 走得完。n_eff ＝ 主格判斷日月數（＜ 24 ⇒ 樣本不足）；獨立年數 ＝ 主格判斷日年數。
    斷點截斷 ＝ (e, e＋750] 有斷點；下市 ＝ 最後有效 K 棒 ＜ e＋750 且距資料尾 ≥ 5 日（處理留正式跑：截在斷點前一根／以最後收盤計＝現行下市結算）。
 U8 無價者（登錄 §四：另列件數與占比、⛔ 不補）：每個判斷日 d 在 S&P 500／400 名冊內、但 d 沒有有效 K 棒（含整段缺價、未進世界的 60 檔：A2.idx_member）的檔數與占名冊比例。
 U9 等價／退化（seq377）：甲÷丁、B 成立率與兩條各自、A 成立率、乙÷甲、轉強可判率、甲∩丙＝0、A 與 A任一窗一致率、丁去重版件數、S&P 500／400 分開。
 U10 必附：「C（主題燈）沒有回測，只測了『有大漲前例＋還沒漲過』」「事件重疊、CI 偏窄」「不是選股規則」「年代集中（判斷日 2018-12～2023-09，
    多與 2020～2021 大多頭、2023～2026 AI 行情重疊）」「A 只能回看判斷日前 750 日（價格 2015-12 起）」「S&P 400 整段缺價 48、S&P 500 18 不在母體 ⇒ 偏存活股、偏樂觀」。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K                       # noqa: E402  rworld（A4 世界；⛔ 只 import）
from backtest import researchUSA4 as A4                     # noqa: E402  load_fund、q_last、yoy_at、key_at、sector_at
from backtest import researchUSA2_data as A2                # noqa: E402  no_ohlc_tickers、idx_member、data_commit
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、MAILBOX
from backtest import researchTriple_freq as TP              # noqa: E402  make_events（DEDUP_M＝36）

REG_SHA = "3ce4e52205c08a14"
RUL = "seq464"
OUT = "backtest/resultsPickDistUS/freq"
TW = os.path.expanduser("~/pkdwork_us")
HJ = 750
WA = 750
WB = 500
NEFF_MIN = 24
D0, D1 = "2018-12-01", "2023-09-30"
ARMS = ["甲", "乙", "丙", "丁"]
ARM_LABEL = {"甲": "甲 A＋B", "乙": "乙 A＋B＋轉強", "丙": "對照一 B 且非 A", "丁": "對照二 全母體"}
NOTES = ["頻率表、未算任何報酬（seq366）",
         "C（主題燈）沒有回測，只測了『有大漲前例＋還沒漲過』",
         "事件重疊（750 日窗互相重疊）⇒ 月分群 CI 偏窄，只描述",
         "不是選股規則",
         "年代集中：判斷日只有 2018-12～2023-09，多與 2020～2021 大多頭、2023～2026 AI 行情重疊",
         "A 只能回看判斷日前 750 日（價格 2015-12 起），與台股版「任一 750 日窗」不同",
         "S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 偏向存活股、①②比例偏樂觀",
         "GICS 取 sector_pit（Wikipedia 歷史版，非官方）",
         "資料 ＝ us-stock-data 881c86a（A4 世界）；私有資料只出彙總與代號、日期、布林"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


# ═════════════ 世界、斷點（U0、U2）═════════════
def world():
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]
    C = W["C"]; V = W["valid"]; n, S = V.shape
    BAD = np.asarray(W["pb"], bool).copy()
    ngap = 0
    for j in range(S):
        vp = np.flatnonzero(V[:, j])
        if len(vp) < 2:
            continue
        g = np.flatnonzero(np.diff(vp) - 1 >= 5)
        if len(g):
            BAD[vp[g + 1], j] = True; ngap += len(g)
    CB = np.cumsum(BAD, axis=0, dtype=np.int32)
    nv = V.sum(axis=1); tail = int(np.flatnonzero(nv > 0)[-1])
    FV = np.where(V.any(axis=0), np.argmax(V, axis=0), 10 ** 9)
    LV = np.where(V.any(axis=0), n - 1 - np.argmax(V[::-1], axis=0), -1)
    return {"R": R, "W": W, "cal": cal, "C": C, "O": W["O"], "V": V, "BAD": BAD, "CB": CB, "tail": tail, "FV": FV, "LV": LV,
            "ngap": ngap, "npb": int(np.asarray(W["pb"]).sum()), "tick": list(W["tick"]), "ix": W["ix"]}


def month_ends(cal, tail):
    s = pd.Series(np.arange(len(cal)), index=cal)
    me = s.groupby([s.index.year, s.index.month]).last().to_numpy()
    return [int(p) for p in me if p <= tail and str(cal[p].date()) >= D0]


def segname(d):
    s = str(pd.Timestamp(d).date())
    return "判斷窗" if D0 <= s <= D1 else "段外"


# ═════════════ A、B（U3、U4）═════════════
def pair_hit(c, bd):
    """c：收盤序列（NaN＝無 K 棒）、bd：同長斷點旗標 ⇒ 是否存在 i＜j（同段）c_j ≥ 3 c_i。"""
    seg = np.cumsum(bd)
    ok_all = np.isfinite(c)
    for k in np.unique(seg[ok_all]):
        s = c[seg == k]
        lo = pd.Series(s).cummin().shift(1).to_numpy(float)
        ok = np.isfinite(s) & np.isfinite(lo) & (lo > 0)
        if (ok & (s >= 3.0 * np.where(ok, lo, np.inf))).any():
            return True
    return False


def a_recent(Wx, j, d):
    a = max(0, d - WA)
    return pair_hit(Wx["C"][a:d + 1, j].astype(float), Wx["BAD"][a:d + 1, j])


def a_any(Wx, j, d):
    return pair_hit(Wx["C"][:d + 1, j].astype(float), Wx["BAD"][:d + 1, j]) if d - Wx["FV"][j] > WA else a_recent(Wx, j, d)


def b_at(Wx, j, d):
    a = d - (WB - 1)
    if a < 0 or Wx["FV"][j] > a or Wx["CB"][d, j] - Wx["CB"][a, j] > 0 or not Wx["V"][d, j]:
        return False, False
    w = Wx["C"][a:d + 1, j]; c = Wx["C"][d, j]
    mn, mx = np.nanmin(w), np.nanmax(w)
    return True, bool(c < 2.0 * mn and c <= 0.85 * mx)


# ═════════════ 季營收轉強（U5）═════════════
def rev_up(F, key, d, edays):
    """→ (可判, 甲, 乙, 轉強)；只用 av ≤ d 的季報。"""
    if key is None or key not in F["revenue"]:
        return False, False, False, False
    yo = A4.yoy_at(F, "revenue", key, d, edays)
    q8 = A4.q_last(F, "revenue", key, d, 8, edays=edays)
    ttm = np.nan
    hi8 = np.nan
    if q8 is not None:
        v = q8[1]
        if v[:4].sum() > 0:
            ttm = v[4:].sum() / v[:4].sum() - 1
        hi8 = bool(v[-1] > v[:-1].max())
    q9 = A4.q_last(F, "revenue", key, d, 9, edays=edays)
    hp = (bool(q9[1][7] > q9[1][:7].max()) if q9 is not None else np.nan)
    jia = bool(np.isfinite(yo) and np.isfinite(ttm) and (yo - ttm) >= 0.05)
    yi = bool(hi8 is True and not (hp is True))
    can = bool((np.isfinite(yo) and np.isfinite(ttm)) or hi8 is not np.nan)
    return can, jia, yi, bool(jia or yi)


def build():
    t0 = time.time()
    Wx = world(); cal = Wx["cal"]; tail = Wx["tail"]; W = Wx["W"]; tick = Wx["tick"]
    log(f"[世界] {cal[0].date()}～{cal[-1].date()}｜資料尾 {cal[tail].date()}｜檔 {len(tick)}｜pb {Wx['npb']}｜缺口≥5 斷點 {Wx['ngap']}｜{time.time() - t0:.0f}s")
    F = A4.load_fund(cal); SEG = F["SEG"]; sec = Wx["R"]["sec"]
    log(f"[季營收] 鍵 {len(F['revenue'])}｜{time.time() - t0:.0f}s")
    MEs = month_ends(cal, tail)
    m5, m4 = np.asarray(W["m5"], bool), np.asarray(W["m4"], bool)
    rows = []
    for d in MEs:
        ed = int(cal[d].value // 86400_000_000_000)
        for j in np.flatnonzero((m5[d] | m4[d]) & Wx["V"][d]):
            j = int(j); t = tick[j]
            bj, b = b_at(Wx, j, d)
            ar = a_recent(Wx, j, d)
            key = A4.key_at(SEG, t, cal[d])
            can, jia, yi, up = rev_up(F, key, d, ed)
            gs, _ = A4.sector_at(sec, t, ed)
            rows.append((t, j, d, str(cal[d].date()), segname(cal[d]), "S&P500" if m5[d, j] else "S&P400", ar, bool(Wx["FV"][j] <= d - WA),
                         bj, b, can, jia, yi, up, gs or "無GICS", int(d - Wx["FV"][j])))
    B = pd.DataFrame(rows, columns=["ticker", "j", "d", "判斷日", "段", "指數", "A成立", "A可判", "B可判", "B", "轉強可判", "季甲", "季乙", "轉強", "GICS", "歷史天數"])
    B["mk"] = [cal[d].year * 12 + cal[d].month - 1 for d in B["d"]]
    log(f"[股月] {len(B)}｜判斷日 {len(MEs)}｜{time.time() - t0:.0f}s")
    B["A任一窗"] = [a_any(Wx, int(j), int(d)) for j, d in zip(B["j"], B["d"])]

    def eok(j, d):
        e = d + 1
        if e > tail:
            return "e超出資料尾"
        if Wx["CB"][e, j] - Wx["CB"][d, j] > 0:
            return "斷點(d,e]"
        o = Wx["O"][e, j]
        if not (Wx["V"][e, j] and np.isfinite(o) and o > 0):
            return "e無K棒"
        return "保留"
    masks = {"甲": B["A成立"] & B["B"], "乙": B["A成立"] & B["B"] & B["轉強"], "丙": B["B"] & ~B["A成立"]}
    EV = {}; RS = {}
    for arm, m in masks.items():
        d_ = B[m]
        cands = [(t, int(j), int(d), int(mk), dd) for t, j, d, mk, dd in zip(d_["ticker"], d_["j"], d_["d"], d_["mk"], d_["判斷日"])]
        kept, rs = TP.make_events(cands, tail, lambda i, A_: True)
        rs["訊號股月(去重前)"] = len(cands)
        EV[arm] = kept; RS[arm] = dict(rs)
    EV["丁"] = [(t, int(j), int(d), int(mk), dd) for t, j, d, mk, dd in zip(B["ticker"], B["j"], B["d"], B["mk"], B["判斷日"])]
    Bi = B.set_index(["ticker", "d"])

    def ev_table(K_):
        out = []
        for t, j, d, mk, dd in K_:
            e = d + 1; x = e + HJ; walk = bool(x <= tail)
            r = Bi.loc[(t, d)]
            out.append({"ticker": t, "j": j, "d": d, "判斷日": dd, "e": (str(cal[e].date()) if e <= tail else ""), "段": r["段"],
                        "年": cal[d].year, "月": f"{cal[d].year}-{cal[d].month:02d}", "指數": r["指數"], "GICS": r["GICS"],
                        "A成立": bool(r["A成立"]), "A可判": bool(r["A可判"]), "A任一窗": bool(r["A任一窗"]), "B": bool(r["B"]),
                        "轉強可判": bool(r["轉強可判"]), "季甲": bool(r["季甲"]), "季乙": bool(r["季乙"]), "轉強": bool(r["轉強"]),
                        "進場": eok(j, d), "H750走得完": walk,
                        "H750窗內遇斷點": (bool(Wx["CB"][x, j] - Wx["CB"][e, j] > 0) if walk else None),
                        "H750窗內遇下市": (bool(Wx["LV"][j] < x and tail - Wx["LV"][j] >= 5) if walk else None)})
        E = pd.DataFrame(out)
        if len(E):
            E["主格"] = (E["進場"] == "保留") & E["H750走得完"]
        return E
    E = {arm: ev_table(EV[arm]) for arm in ARMS}
    E["丁"] = E["丁"][E["丁"]["進場"] == "保留"].reset_index(drop=True)
    log("[事件] " + "｜".join(f"{a} {len(E[a])}" for a in ARMS) + f"｜{time.time() - t0:.0f}s")
    # 無價者（U8）
    noo = [t for t in A2.no_ohlc_tickers()]
    extra = {t: A2.idx_member(t, cal) for t in noo}
    NP = []
    for d in MEs:
        mem = m5[d] | m4[d]
        inw_np = int((mem & ~Wx["V"][d]).sum())
        out5 = sum(int(v[0][d]) for v in extra.values()); out4 = sum(int(v[1][d]) for v in extra.values())
        nmem = int(mem.sum()) + out5 + out4
        NP.append({"判斷日": str(cal[d].date()), "段": segname(cal[d]), "名冊檔數": nmem, "無價(世界內當天無K棒)": inw_np, "無價(整段缺價未進世界)": out5 + out4,
                   "其中S&P500": out5 + int((m5[d] & ~Wx["V"][d]).sum()), "其中S&P400": out4 + int((m4[d] & ~Wx["V"][d]).sum()),
                   "無價占比": (inw_np + out5 + out4) / nmem if nmem else np.nan})
    NP = pd.DataFrame(NP)
    return {"Wx": Wx, "F": F, "B": B, "E": E, "EV": EV, "RS": RS, "MEs": MEs, "NP": NP, "tail": tail}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    t0 = time.time()
    out = a.out; os.makedirs(out, exist_ok=True); os.makedirs(TW, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    rul = [f for d in [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if RUL in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RUL}")
    log(f"[裁定] {os.path.basename(rul[0])}")
    Z = build()
    B, E, cal, tail = Z["B"], Z["E"], Z["Wx"]["cal"], Z["tail"]
    FR = []
    for arm in ARMS:
        for nm in ("判斷窗", "段外"):
            d = E[arm][E[arm]["段"] == nm] if len(E[arm]) else E[arm]
            bm = B[B["段"] == nm]
            raw = (int(len(bm)) if arm == "丁" else int({"甲": bm["A成立"] & bm["B"], "乙": bm["A成立"] & bm["B"] & bm["轉強"], "丙": bm["B"] & ~bm["A成立"]}[arm].sum()))
            if not len(d):
                FR.append({"臂": ARM_LABEL[arm], "段": nm, "訊號股月(重複窗前)": raw, "事件(重複窗後)": 0, "n_eff": 0, "樣本不足(n_eff<24)": True}); continue
            m = d[d["主格"]]; ne = int(m["月"].nunique())
            FR.append({"臂": ARM_LABEL[arm], "段": nm, "訊號股月(重複窗前)": raw, "事件(重複窗後)": len(d), "S&P500": int((d["指數"] == "S&P500").sum()),
                       "S&P400": int((d["指數"] == "S&P400").sum()), "可進場": int((d["進場"] == "保留").sum()), "750走得完": int(d["H750走得完"].sum()),
                       "750走得完比例": float(d["H750走得完"].mean()), "主格事件": len(m), "n_eff": ne, "樣本不足(n_eff<24)": ne < NEFF_MIN,
                       "獨立年數(主格)": int(m["年"].nunique()), "主格斷點截斷": int((m["H750窗內遇斷點"] == True).sum()),  # noqa: E712
                       "主格下市": int((m["H750窗內遇下市"] == True).sum()),  # noqa: E712
                       "主格下市比例": (float((m["H750窗內遇下市"] == True).mean()) if len(m) else np.nan),  # noqa: E712
                       "A可判比例(主格)": (float(m["A可判"].mean()) if len(m) else np.nan), "轉強可判比例(主格)": (float(m["轉強可判"].mean()) if len(m) else np.nan),
                       "轉強比例(主格)": (float(m["轉強"].mean()) if len(m) else np.nan)})
    FR = pd.DataFrame(FR)
    for nm in ("判斷窗", "段外"):
        nj = int((E["甲"]["段"] == nm).sum()) if len(E["甲"]) else 0; ny = int((E["乙"]["段"] == nm).sum()) if len(E["乙"]) else 0
        FR.loc[(FR["臂"] == ARM_LABEL["乙"]) & (FR["段"] == nm), "乙佔甲(事件)"] = ny / nj if nj else np.nan
        dj = E["甲"][E["甲"]["段"] == nm] if len(E["甲"]) else E["甲"]
        FR.loc[(FR["臂"] == ARM_LABEL["甲"]) & (FR["段"] == nm), "轉強配到率(甲事件可判)"] = float(dj["轉強可判"].mean()) if len(dj) else np.nan
        FR.loc[(FR["臂"] == ARM_LABEL["甲"]) & (FR["段"] == nm), "轉強率(甲事件)"] = float(dj["轉強"].mean()) if len(dj) else np.nan
    BS = []
    for nm in ("判斷窗", "段外"):
        for ixn in ("合併", "S&P500", "S&P400"):
            bm = B[(B["段"] == nm) & ((B["指數"] == ixn) if ixn != "合併" else True)]
            if not len(bm):
                continue
            BS.append({"段": nm, "母體": ixn, "股月": len(bm), "判斷日": int(bm["d"].nunique()), "A可判比例": float(bm["A可判"].mean()),
                       "A成立率": float(bm["A成立"].mean()), "A任一窗成立率": float(bm["A任一窗"].mean()), "B可判比例": float(bm["B可判"].mean()),
                       "B成立率": float(bm["B"].mean()), "B成立率(B可判中)": (float(bm.loc[bm["B可判"], "B"].mean()) if bm["B可判"].any() else np.nan),
                       "轉強可判比例": float(bm["轉強可判"].mean()), "季甲率": float(bm["季甲"].mean()), "季乙率": float(bm["季乙"].mean()), "轉強率": float(bm["轉強"].mean()),
                       "A且B率": float((bm["A成立"] & bm["B"]).mean()), "B且非A率": float((bm["B"] & ~bm["A成立"]).mean()),
                       "A且B且轉強率": float((bm["A成立"] & bm["B"] & bm["轉強"]).mean())})
    BS = pd.DataFrame(BS)
    YR = []; GI = []; IX = []
    for arm in ARMS:
        d = E[arm]
        if not len(d):
            continue
        for y, x in d.groupby("年"):
            YR.append({"臂": ARM_LABEL[arm], "年(判斷日)": int(y), "事件": len(x), "可進場": int((x["進場"] == "保留").sum()), "主格": int(x["主格"].sum()),
                       "S&P500": int((x["指數"] == "S&P500").sum()), "S&P400": int((x["指數"] == "S&P400").sum())})
        m = d[d["主格"] & (d["段"] == "判斷窗")]
        for g_, x in m.groupby("GICS"):
            GI.append({"臂": ARM_LABEL[arm], "GICS sector": g_, "主格事件": len(x), "月數": int(x["月"].nunique())})
        for g_, x in m.groupby("指數"):
            IX.append({"臂": ARM_LABEL[arm], "指數": g_, "主格事件": len(x), "n_eff": int(x["月"].nunique())})
    YR, GI, IX = pd.DataFrame(YR), pd.DataFrame(GI), pd.DataFrame(IX)
    gb = B[B["段"] == "判斷窗"]
    EQ = [{"項": "A且B 股月 ÷ 全母體股月（判斷窗）", "值": round(float((gb["A成立"] & gb["B"]).mean()), 4), "註": "甲 ⊂ 丁"},
          {"項": "A 成立率", "值": round(float(gb["A成立"].mean()), 4), "註": ""},
          {"項": "B 成立率／B 可判中", "值": f"{gb['B'].mean():.4f}／{gb.loc[gb['B可判'], 'B'].mean():.4f}", "註": "是否幾乎總成立"}]
    c1 = []; c2 = []
    Wx = Z["Wx"]
    for j, d in zip(gb.loc[gb["B可判"], "j"], gb.loc[gb["B可判"], "d"]):
        w = Wx["C"][int(d) - WB + 1:int(d) + 1, int(j)]; c = Wx["C"][int(d), int(j)]
        c1.append(c < 2 * np.nanmin(w)); c2.append(c <= 0.85 * np.nanmax(w))
    c1 = np.array(c1, bool); c2 = np.array(c2, bool)
    EQ += [{"項": "B 條件一 c＜2×500日最低（B 可判中）", "值": round(float(c1.mean()), 4) if len(c1) else None, "註": ""},
           {"項": "B 條件二 c≤0.85×500日最高（B 可判中）", "值": round(float(c2.mean()), 4) if len(c2) else None, "註": ""},
           {"項": "B 兩條聯合（B 可判中）", "值": round(float((c1 & c2).mean()), 4) if len(c1) else None, "註": "≈ 某一條 ⇒ 另一條幾乎不擋"}]
    nj, ny = len(E["甲"]), len(E["乙"])
    EQ.append({"項": "乙 ÷ 甲（事件，全期）", "值": round(ny / nj, 4) if nj else None, "註": "乙臂轉強配到率"})
    EQ.append({"項": "甲事件轉強可判比例", "值": round(float(E["甲"]["轉強可判"].mean()), 4) if nj else None, "註": "不可判 ⇒ 轉強為假（多為銀行保險無營收科目、季缺）"})
    EQ.append({"項": "母體轉強：季甲率／季乙率／兩者皆", "值": f"{gb['季甲'].mean():.4f}／{gb['季乙'].mean():.4f}／{(gb['季甲'] & gb['季乙']).mean():.4f}", "註": ""})
    ja = set(zip(E["甲"]["ticker"], E["甲"]["d"])) if nj else set(); ca = set(zip(E["丙"]["ticker"], E["丙"]["d"])) if len(E["丙"]) else set()
    ya = set(zip(E["乙"]["ticker"], E["乙"]["d"])) if ny else set()
    EQ.append({"項": "甲 ∩ 丙（依構造應為 0）", "值": len(ja & ca), "註": ""})
    EQ.append({"項": "乙事件中同期也是甲事件的比例", "值": round(len(ya & ja) / ny, 4) if ny else None, "註": "各自 36 月去重"})
    EQ.append({"項": "A（近 750）與 A任一窗（台股口徑）一致率（判斷窗）", "值": round(float((gb["A成立"] == gb["A任一窗"]).mean()), 4),
               "註": f"任一窗成立而近750不成立 {int((gb['A任一窗'] & ~gb['A成立']).sum())}；反向違反 {int((gb['A成立'] & ~gb['A任一窗']).sum())}"})
    d4 = E["丁"]
    kept, _ = TP.make_events([(t, int(j), int(d), cal[int(d)].year * 12 + cal[int(d)].month - 1, dd) for t, j, d, dd in zip(d4["ticker"], d4["j"], d4["d"], d4["判斷日"])],
                             tail, lambda i, A_: True)
    EQ.append({"項": "丁 若同 36 月去重的件數（另一讀法）", "值": json.dumps(dict(Counter(segname(cal[z[2]]) for z in kept)), ensure_ascii=False), "註": "主讀法不去重"})
    EQ = pd.DataFrame(EQ)
    for arm in ARMS:
        E[arm].drop(columns=[c for c in ("j", "d") if c in E[arm].columns]).to_csv(os.path.join(out, f"events_{arm}.csv.gz"), index=False,
                                                                                 encoding="utf-8-sig", compression="gzip")
    FR.to_csv(os.path.join(out, "freq.csv"), index=False, encoding="utf-8-sig")
    BS.to_csv(os.path.join(out, "base.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    GI.to_csv(os.path.join(out, "gics.csv"), index=False, encoding="utf-8-sig")
    IX.to_csv(os.path.join(out, "index.csv"), index=False, encoding="utf-8-sig")
    EQ.to_csv(os.path.join(out, "equiv.csv"), index=False, encoding="utf-8-sig")
    Z["NP"].to_csv(os.path.join(out, "noprice.csv"), index=False, encoding="utf-8-sig")
    pk = os.path.join(TW, "events_us.pkl")
    pickle.dump({"E": E, "out": out}, open(pk, "wb"), protocol=5)
    npw = Z["NP"][Z["NP"]["段"] == "判斷窗"]
    J = {"性質": "美股產業線挑法好壞比例分佈 seq2 頻率表（⛔ 未算任何報酬）", "登錄": f"美股策略線 seq2 sha {REG_SHA}（{reg}）", "裁定": os.path.basename(rul[0]),
         "資料": f"us-stock-data {A2.data_commit()}（A4 世界）", "日曆": [str(cal[0].date()), str(cal[-1].date())], "資料尾": str(cal[tail].date()),
         "斷點": {"pb": Z["Wx"]["npb"], "缺口≥5": Z["Wx"]["ngap"]}, "判斷日數": len(Z["MEs"]),
         "判斷窗判斷日": [str(cal[d].date()) for d in Z["MEs"] if segname(cal[d]) == "判斷窗"],
         "重複窗剔除": Z["RS"], "段": FR.to_dict("records"), "母體": BS.to_dict("records"),
         "無價(判斷窗)": {"平均名冊": float(npw["名冊檔數"].mean()), "平均無價": float((npw["無價(世界內當天無K棒)"] + npw["無價(整段缺價未進世界)"]).mean()),
                       "平均無價占比": float(npw["無價占比"].mean())},
         "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1], "逐事件位置檔": pk, "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: (o.item() if hasattr(o, "item") else str(o)))
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""廣撒長抱 seq1【頻率表・乾跑】（台股策略線 組合層登錄 sha 4f73227473ff654a，2026-10-22 23:33；裁定 seq454 §一 發號：6 格挑 1、N_組合 ＋1、最多暫定；
主對照「純廣撒」與隨機 1,000 次；頻率表補三項：①每批平均／最多檔數、一份錢分到每檔的比例（太多就照實寫「實際照做不可行」）②G1 與 G2 每批重疊率
③每批與當月營量、營飆名單重疊率；顧廣平 (2010) 是否讀過原文照實寫）——回測線計算子代理。
⛔ 不算任何報酬：乾跑 ＝ 全部價格視為不變（R 全 0）⇒ 權益恆 1、持股檔數與現金比例是純構造量。
   用到的價格只有：進場日前一日原始收盤（只為「每檔買 1 張要多少錢」）、有沒有有效 K 棒、開盤鎖漲停、壞根位置、下市位置。
⛔ 不 commit、不改既有檔；researchTriple_freq（RV_TAG 快取、segof）、researchRevTurn_freq（ensure_data、prices、rev_table、jia、yi、avail_pos、mnum）＝
   G1、G2 訊號定義（⛔ 只 import、不寫第二份）；researchIndRev_prereg.elig_at ＋ researchIndRevLag_prereg 的 W1 面板快取（~/indrevlagwork/ctx_*.pkl）＝ W1 eligible；
   researchIndMom_freq（reg_check、entry_flag）⛔ 只 import。

    cd ~/tw-p17
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad_freq --sha <origin/main> --step prep [--procs 4]
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad_freq --sha <同上> --step freq
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad_freq_check
輸出 backtest/resultsBroad/freq/：cells.csv、batches.csv.gz、overlap.csv、random_frame.csv、meta.json、run.log

═══ 讀法（B 標；⛔ 在算任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 B0 資料：tw-stock-data origin/main（月營收、產業、exright；＝ 3 倍命中率同一版）；價格 ＝ researchRevTurn_freq.prices（rerun17 H2D edc6f ＋ 早年 eotc 合併日曆
    2004-02-11～2026-09-24；四碼普通股、含已下市；壞根 ＝ 缺口 ≥5 日（seq335）∪ 斷點 ∪ 幽靈還原 ∪ 早年 reduce_v2；開盤鎖漲停用 exright／otcexright open_base）。
    引擎閘 UG.set_gate_v2(True)（登錄 §五；W1 面板快取建時即 GATE_V2 ∩ gate3、pit_valid 剔）。
 B1 W1 eligible（登錄 §二）：researchIndRev_prereg.elig_at（批日同月最後一個量測日的 W1 名單）；量測面板 ＝ researchIndRevLag_prereg.part_ctx 快取：
    主 panel_ext 2015-08-03～2026-08-03（上市＋上櫃）、早年 eotc 版面 2012-06-01～2014-12-01（⚠ 上櫃無法人 ⇒ 早年 W1 實際只有上市，照實報）。
    ⚠ 2015-01～2015-07 兩個版面都沒有 W1 ⇒ 這 7 個月不成批（該份放現金，照報）；2026-09 起沒有量測日 ⇒ 最後一批 2026-08。
    另須在價格面板（四碼普通股 ≥260 根）內，不在 ⇒ 計「不在價格面板」、當買不到。
 B2 訊號（⛔ 不寫第二份）：G1 ＝ S1 ＝ 甲 ∧ 乙（＝ 3 倍命中率 T1；researchRevTurn_freq.jia／yi）；G2 ＝ 轉強起點 up ∧ ¬up_prev（＝ 營收轉強驗證 V2）。
    月營收 ＝ researchTriple_freq 的 rev_metrics 快取（rv_trp_s7.pkl，3 倍命中率頻率表同一份）。★ 不做 36 月去重（登錄「當月全部訊號股」）；
    ★ 不加 500 張閘（登錄母體只寫 W1 eligible）〔另一讀法：再加 500 張閘〕。
 B3 批：營收月 P 的可用日 A ＝ researchRevTurn_freq.avail_pos（次月 10 日後第一個交易日；2026-01 起 15 日）；批日 b ＝ A＋1 開盤買（登錄「可用日收盤判、次一交易日開盤買」）。
    批 ＝ 該月訊號 ∩ W1(b) ∩ 價格面板，全部等權；空批 ⇒ 該份放現金到到期。批日落在 2012-06-01～2026-08-31 且有 W1 者成批。
 B4 資金：份數 ★ n_H ＝ round(H ÷ 21) ＝ 12／24／36（登錄「H/21 份」非整數；＝ 產業長抱頻率表 F3）；每批金額 ＝ min(1 ÷ n_H, 批日開盤可用現金)；
    到期 mat ＝ b ＋ H − 1（b 算第 1 日）收盤賣；份額在全部成員賣完後回收，供 b ＞ 回收日的新批用。
 B5 持有與出場（R 全 0 帳）：買不到 ⇒ 該部分現金到該批到期 ＝ researchIndMom_freq.entry_flag(t＝b−1, e＝b) ≠ 保留（壞根、b 無成交、b 開盤鎖漲停）；
    提前出場 ⇒ 現金到該批到期：(b, min(mat, 資料尾)] 第一個壞根 ⇒ 壞根前最後有效 K 棒收盤賣（seq335）；最後有效 K 棒 ＜ min(mat, 資料尾) 且距資料尾 ≥ 5 日 ⇒
    末根收盤賣（停止交易／下市）。到期日無有效 K 棒 ⇒ ★ 順延到下一根有效收盤（計數）；mat ＞ 資料尾 ⇒ 持有到尾（走不完）。
    持股計數 ＝ 收盤後：一筆在 [b, 出場日 − 1] 算持有。
 B6 格 ＝ G {G1, G2} × H {250, 500, 750}；主對照「純廣撒」＝ 每批 W1(b) ∩ 價格面板全部等權（同 H、同帳）。一條連續帳 ★ 從 2012-06 第一批起到資料尾
    〔另一讀法：主帳 2015-08 起，只報其現金比例〕。
 B7 段（依批日 b；統計依日）：早年 2012-06-01～2016-12-31｜探索 2017-03-01～2021-12-31｜確認 2022-01-01～資料尾（2026-09-24）。
    n_eff ＝ 段內批數（月數）；另報獨立期數 ＝ 段內交易日 ÷ H；各 H 走得完批數（mat ≤ 資料尾）。
 B8 頻率表（每 格×段）：每批計畫檔數平均／中位／最多／最少、空批數、實買檔數平均、一份錢分到每檔的比例（＝ 1 ÷ n_H ÷ 檔數，總資金的比例；平均與最小）、
    ★「每檔至少買 1 張所需總資金」＝ n_H × 檔數 × 1,000 × 批日前一日原始收盤中位（另報用最高價）〔批中位〕、每日同時持有不同代號數（平均、最多）、
    平均現金比例（＋拆：未投入份額／份內現金＝空批、買不到、提前出場）、份數被現金卡住批數、換手（年買進金額 ÷ 平均投入）、買不到／壞根／下市／順延次數。
    ★「實際照做不可行」標記：同時持有不同代號平均 ＞ 100 或 每檔至少 1 張所需總資金中位 ＞ 1 億元（兩條任一，執行者定、照實標）。
 B9 退化（登錄 §二 事前排除：平均持股 ＜ 10 檔或現金 ＞ 30%；★ 以探索段判，三段都報）。
 B10 重疊（seq377）：① G1 與 G2 每批：|G1∩G2|÷|G1|、÷|G2|、Jaccard（批內，W1∩面板後）；段內平均與全期。
     ② 營量、營飆：營量 v1 ＝ resultsN17/sig_edc6f/and_signals.csv.gz（⛔ 只讀 sid、pos、entry_pos）；營飆 ＝ 進場前一日 0050 ＞ 200 日均（rerun17.regime_mask；
     ＝ 營收轉強驗證 V9 原式）；★ 當月 ＝ 訊號日與批日同一曆月；報 批中為當月名單的比例、名單中在批內的比例（比得到的月份）。
 B11 隨機 1,000 次框架（登錄 §四；⛔ 本階段不算報酬）：rng ＝ default_rng([20261022, r])；每批從 W1(b) ∩ 價格面板依代號排好後 permutation 取前 n_b（＝ 該格當批檔數），
     批依時間序；本階段報 1,000 次的「與訊號批同檔比例」，及前 100 次的構造量（同時持有、現金）分佈。
 B12 必附：顧廣平 (2010) 是登錄引的反轉依據，回測線未讀原文；結論最多暫定（看過命中率與轉強結果才提）。
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTriple_freq as TP              # noqa: E402  RV_TAG（月營收快取）
from backtest import researchRevTurn_freq as RT             # noqa: E402  甲乙、可用日、價格
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、entry_flag
from backtest import researchIndRev_prereg as PRE           # noqa: E402  elig_at
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
REG_SHA = "4f73227473ff654a"
RUL = "seq454"
OUT = "backtest/resultsBroad/freq"
WK = os.path.expanduser("~/brdwork")
CTX = os.path.expanduser("~/indrevlagwork")
GS = ("G1", "G2", "純廣撒")
HS = (250, 500, 750)
NSL = {H: int(round(H / 21)) for H in HS}
SEED = 20261022
NRAND = 1000
RSTRUCT = 100
B_FIRST, B_LAST = "2012-06-01", "2026-08-31"
SEGS = [("早年", "2012-06-01", "2016-12-31"), ("探索", "2017-03-01", "2021-12-31"), ("確認", "2022-01-01", "2099-12-31")]
AND_CSV = "backtest/resultsN17/sig_edc6f/and_signals.csv.gz"
INF = 10 ** 9
NOTES = ["頻率表、未算任何報酬（R 全 0 帳）", "顧廣平 (2010) 是登錄引的反轉依據，回測線未讀原文",
         "看過 3 倍命中率與營收轉強結果才提 ⇒ 結論最多暫定", "早年 W1 只有上市（eotc 版面上櫃無法人）；2015-01～07 沒有 W1 ⇒ 不成批",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


RT.log = log


def segof(d):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in SEGS:
        if a <= s <= b:
            return nm
    return "段外"


# ═════════════ prep：訊號、W1、批、每筆出場 ═════════════
def load_w1():
    out = {}
    for nm in ("early", "main"):
        C = pickle.load(open(os.path.join(CTX, f"ctx_{nm}.pkl"), "rb"))
        out[nm] = {"cal": C["cal"], "meas": C["meas"], "memW": C["memW"], "mk": C["mk"], "info": C["info"]}
    return out


def w1_at(W1, d):
    """批日 d ⇒ (W1 名單, 版面)；researchIndRev_prereg.elig_at 原式（同月最後量測日）。"""
    for nm in ("main", "early"):
        Cw = W1[nm]
        if Cw["cal"][0] <= d <= Cw["cal"][-1]:
            t = int(Cw["cal"].searchsorted(d))
            if t < len(Cw["cal"]) and Cw["cal"][t] == d:
                lst = PRE.elig_at(Cw, t, "W1")
                if lst:
                    return list(lst), nm
    return [], ""


def lot_exit(PX, i, b, mat, CEND):
    """⇒ (出場位置 或 None, 原因)。持有 [b, 出場−1]；出場 ＝ CEND＋1 ⇒ 持有到資料尾。"""
    fl = IMF.entry_flag(PX, i, b - 1, b)
    if fl != "保留":
        return None, "買不到:" + fl
    end = min(mat, CEND)
    BAD, VP, LASTV = PX["BAD"], PX["VP"], PX["LASTV"]
    cand = []
    bb = np.flatnonzero(BAD[i, b + 1:end + 1])
    if len(bb):
        kb = b + 1 + int(bb[0]); vp = VP[i]
        q = int(vp[int(np.searchsorted(vp, kb - 1, "right")) - 1])
        cand.append((q, "壞根賣"))
    lv = int(LASTV[i])
    if lv < end and CEND - lv >= 5:
        cand.append((lv, "停止交易／下市"))
    if cand:
        return min(cand)
    if mat > CEND:
        return CEND + 1, "走不完"
    vp = VP[i]; k = int(np.searchsorted(vp, mat, "left"))
    if k >= len(vp):
        return CEND + 1, "到期後無K棒至資料尾"
    q = int(vp[k])
    return q, ("到期" if q == mat else "到期順延")


def raw_close_at(PX, pairs):
    """{(i, p)} ⇒ 原始收盤（只為 1 張金額）。依世界讀 stocks/<sid>.csv 的 close。"""
    CAL, NE, SIDS = PX["CAL"], PX["NE"], PX["SIDS"]
    need = defaultdict(set)
    for i, p in pairs:
        need[(i, "early" if p < NE else "main")].add(p)
    out = {}
    for (i, w), ps in need.items():
        d = PX["early_data"] if w == "early" else PX["main_data"]
        f = os.path.join(d, "stocks", f"{SIDS[i]}.csv")
        if not os.path.exists(f):
            continue
        x = pd.read_csv(f, dtype={"date": str}, usecols=["date", "close"])
        x["date"] = pd.to_datetime(x["date"]); x = x.drop_duplicates("date").set_index("date")["close"]
        x = pd.to_numeric(x, errors="coerce")
        for p in ps:
            v = x.get(CAL[p], np.nan)
            out[(i, p)] = float(v) if np.isfinite(v) and v > 0 else np.nan
    return out


def step_prep(a):
    t0 = time.time()
    os.makedirs(WK, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]; CEND = len(CAL) - 1
    Zc = pickle.load(open(os.path.join(RT.WORK, f"rv_{TP.RV_TAG}_s{RT.SHIFT_Y}.pkl"), "rb"))
    if not (Zc["MD"] == MD and Zc["codes"] == list(SIDS)):
        raise SystemExit("⛔ 月營收快取與資料版本不符")
    RV = Zc["RV"]
    APOS = RT.avail_pos(CAL, sorted(RV["period"].unique()))
    RV = RV.assign(A=RV["period"].map(APOS).astype(int))
    RV["G1"] = RT.jia(RV) & RT.yi(RV)
    RV["G2"] = RV["up"].astype(bool) & ~RV["up_prev"].astype(bool)
    W1 = load_w1()
    log(f"[W1] 主 {W1['main']['info']}｜早年 {W1['early']['info']}")
    BT = []
    nomiss = Counter()
    for P in sorted(RV["period"].unique()):
        A_ = APOS[P]; b = A_ + 1
        if not (1 <= A_ and b <= CEND):
            continue
        d = CAL[b]
        if not (B_FIRST <= str(d.date()) <= B_LAST):
            continue
        w1, wn = w1_at(W1, d)
        sub = RV[RV["period"] == P]
        g1 = sorted(sub.loc[sub["G1"], "sid"]); g2 = sorted(sub.loc[sub["G2"], "sid"])
        w1p = [s for s in w1 if s in ix]
        nomiss["W1不在價格面板(檔次)"] += len(w1) - len(w1p)
        ws = set(w1p)
        BT.append({"P": P, "A": A_, "b": b, "d": str(d.date()), "版面": wn, "W1": w1p, "W1原數": len(w1),
                   "G1": [s for s in g1 if s in ws], "G2": [s for s in g2 if s in ws], "G1全": len(g1), "G2全": len(g2)})
    log(f"[批] {len(BT)}（{BT[0]['d']}～{BT[-1]['d']}）｜無 W1 批 {sum(1 for x in BT if not x['W1'])}｜{dict(nomiss)}｜{time.time() - t0:.0f}s")
    # 每筆出場（三個 H；只算 W1∩面板 內的股——訊號與純廣撒都是它的子集）
    LX = {}
    cnt = Counter()
    for x in BT:
        b = x["b"]
        for s in x["W1"]:
            i = ix[s]
            for H in HS:
                e, why = lot_exit(PX, i, b, b + H - 1, CEND)
                LX[(i, b, H)] = (e, why)
                cnt[(H, why.split(":")[0])] += 1
    log(f"[出場] {len(LX)} 筆｜{time.time() - t0:.0f}s")
    RC = raw_close_at(PX, {(ix[s], x["b"] - 1) for x in BT for s in x["W1"]})
    log(f"[原始收盤] {len(RC)}｜{time.time() - t0:.0f}s")
    pickle.dump({"sha": sha, "BT": BT, "LX": LX, "RC": RC, "CAL": CAL, "SIDS": SIDS, "CEND": CEND, "cnt": dict(cnt),
                 "W1info": {k: v["info"] for k, v in W1.items()}, "reg": reg}, open(os.path.join(WK, f"prep_{sha[:12]}.pkl"), "wb"), protocol=5)
    log(f"[prep 完成] {time.time() - t0:.0f}s")


# ═════════════ freq：R 全 0 帳 ═════════════
def sim(PR, members, H):
    """members[j] ＝ 第 j 批代號清單。⇒ 每日 inv、slot、不同代號數、批資訊、計數。"""
    BT, LX, CAL, CEND = PR["BT"], PR["LX"], PR["CAL"], PR["CEND"]
    ix = {s: k for k, s in enumerate(PR["SIDS"])}
    n = CEND + 1; nsl = NSL[H]; sl = 1.0 / nsl
    rel = []; cnt = Counter(); binfo = []
    dinv = np.zeros(n + 2); dslot = np.zeros(n + 2)
    Ls, La, Le, Lm = [], [], [], []
    buy_amt = np.zeros(n + 2)
    for j, x in enumerate(BT):
        b = x["b"]; mat = b + H - 1
        occ = sum(v for r, v in rel if r >= b)
        Aj = min(sl, max(1.0 - occ, 0.0))
        if Aj < sl - 1e-12:
            cnt["份數被現金卡住"] += 1
        lst = members[j]
        release = mat if mat <= CEND else INF
        nb = 0
        if not lst:
            cnt["空批"] += 1
        per = Aj / len(lst) if lst else 0.0
        for s in lst:
            i = ix[s]
            e, why = LX[(i, b, H)]
            cnt[why.split(":")[0] if e is None else why] += 1
            if e is None:
                continue
            nb += 1
            Ls.append(i); La.append(b); Le.append(e); Lm.append(per); buy_amt[b] += per
            if e > mat:
                release = INF if e > CEND else max(release, e)
        rel.append((release, Aj))
        r_end = min(release, CEND + 1) if release != INF else CEND + 1
        dslot[b] += Aj; dslot[r_end] -= Aj
        binfo.append({"j": j, "b": b, "Aj": Aj, "n_plan": len(lst), "n_buy": nb, "mat": mat, "完": int(mat <= CEND)})
    Ls = np.asarray(Ls, int); La = np.asarray(La, int); Le = np.asarray(Le, int); Lm = np.asarray(Lm, float)
    np.add.at(dinv, La, Lm); np.add.at(dinv, Le, -Lm)
    inv = np.cumsum(dinv)[:n]; slot = np.cumsum(dslot)[:n]
    # 不同代號數：每代號持有區間合併
    dd = np.zeros(n + 2)
    byS = defaultdict(list)
    for i, a_, e_ in zip(Ls, La, Le):
        byS[int(i)].append((int(a_), int(e_)))
    for i, iv in byS.items():
        iv.sort(); cs, ce = iv[0]
        for s_, e_ in iv[1:]:
            if s_ <= ce:
                ce = max(ce, e_)
            else:
                dd[cs] += 1; dd[ce] -= 1; cs, ce = s_, e_
        dd[cs] += 1; dd[ce] -= 1
    distinct = np.cumsum(dd)[:n]
    dl = np.zeros(n + 2); np.add.at(dl, La, 1); np.add.at(dl, Le, -1)
    lots = np.cumsum(dl)[:n]
    return {"inv": inv, "slot": slot, "distinct": distinct, "lots": lots, "cnt": cnt, "binfo": binfo, "buy": buy_amt[:n]}


def seg_rows(PR, res, members, G, H):
    CAL, CEND, BT, RC = PR["CAL"], PR["CEND"], PR["BT"], PR["RC"]
    ix = {s: k for k, s in enumerate(PR["SIDS"])}
    rows = []
    first_b = BT[0]["b"]
    for nm, x_, y_ in SEGS:
        a_ = max(int(CAL.searchsorted(pd.Timestamp(x_))), first_b); z_ = min(int(CAL.searchsorted(pd.Timestamp(y_), "right")) - 1, CEND)
        js = [j for j, x in enumerate(BT) if a_ <= x["b"] <= z_]
        bi = [res["binfo"][j] for j in js]
        npl = np.array([x["n_plan"] for x in bi], float)
        nonempty = npl[npl > 0]
        cash = 1.0 - res["inv"][a_:z_ + 1]; idle = 1.0 - res["slot"][a_:z_ + 1]; dist = res["distinct"][a_:z_ + 1]
        frac = [1.0 / NSL[H] / x["n_plan"] for x in bi if x["n_plan"] > 0]
        cap_med = []; cap_max = []
        for j in js:
            lst = members[j]
            if not lst:
                continue
            pr = np.array([RC.get((ix[s], BT[j]["b"] - 1), np.nan) for s in lst], float); pr = pr[np.isfinite(pr)]
            if len(pr):
                cap_med.append(NSL[H] * len(lst) * 1000 * float(np.median(pr))); cap_max.append(NSL[H] * len(lst) * 1000 * float(pr.max()))
        yrs = (z_ - a_ + 1) / 245.0
        inv_mean = float(res["inv"][a_:z_ + 1].mean())
        r = {"格": G, "H": H, "段": nm, "段區間": f"{CAL[a_].date()}～{CAL[z_].date()}", "批數=n_eff(月)": len(js), "獨立期數(段日÷H)": round((z_ - a_ + 1) / H, 2),
             "H走得完批數": int(sum(x["完"] for x in bi)), "空批數": int((npl == 0).sum()),
             "每批檔數平均": float(npl.mean()) if len(npl) else np.nan, "每批檔數中位": float(np.median(npl)) if len(npl) else np.nan,
             "每批檔數最多": int(npl.max()) if len(npl) else 0, "每批檔數最少(非空)": int(nonempty.min()) if len(nonempty) else 0,
             "每批實買平均": float(np.mean([x["n_buy"] for x in bi])) if bi else np.nan,
             "一份錢分到每檔(占總資金)平均": float(np.mean(frac)) if frac else np.nan, "一份錢分到每檔(占總資金)最小": float(np.min(frac)) if frac else np.nan,
             "每檔≥1張所需總資金中位(中位股價,元)": float(np.median(cap_med)) if cap_med else np.nan,
             "每檔≥1張所需總資金中位(最高股價,元)": float(np.median(cap_max)) if cap_max else np.nan,
             "同時持有不同代號平均": float(dist.mean()), "同時持有不同代號最多": int(dist.max()), "同時持有不同代號最少": int(dist.min()),
             "平均持有筆數": float(res["lots"][a_:z_ + 1].mean()),
             "平均現金比例": float(cash.mean()), "現金_未投入份額": float(idle.mean()), "現金_份內(空批、買不到、提前出場)": float((cash - idle).mean()),
             "現金最高": float(cash.max()), "年換手(買進÷平均投入)": (float(res["buy"][a_:z_ + 1].sum() / yrs / inv_mean) if inv_mean > 0 else np.nan)}
        r["退化(平均持股<10或現金>30%)"] = bool(r["同時持有不同代號平均"] < 10 or r["平均現金比例"] > 0.30)
        r["實際照做不可行★"] = bool(r["同時持有不同代號平均"] > 100 or (np.isfinite(r["每檔≥1張所需總資金中位(中位股價,元)"]) and r["每檔≥1張所需總資金中位(中位股價,元)"] > 1e8))
        rows.append(r)
    return rows


def step_freq(a):
    t0 = time.time()
    out = OUT
    os.makedirs(out, exist_ok=True)
    PR = pickle.load(open(os.path.join(WK, f"prep_{a.sha[:12]}.pkl"), "rb"))
    BT, CAL, CEND = PR["BT"], PR["CAL"], PR["CEND"]
    MEM = {"G1": [x["G1"] for x in BT], "G2": [x["G2"] for x in BT], "純廣撒": [x["W1"] for x in BT]}
    CE = []; CNT = {}
    RES = {}
    for G in GS:
        for H in HS:
            res = sim(PR, MEM[G], H)
            RES[(G, H)] = res
            CE += seg_rows(PR, res, MEM[G], G, H)
            CNT[f"{G} H{H}"] = dict(res["cnt"])
    CE = pd.DataFrame(CE)
    log(f"[格] {len(CE)} 列｜{time.time() - t0:.0f}s")
    # 段外批（2017-01～02）
    # ── 重疊 ① G1×G2
    BR = []
    for j, x in enumerate(BT):
        g1, g2 = set(x["G1"]), set(x["G2"])
        BR.append({"批日": x["d"], "營收月": x["P"], "段": segof(x["d"]), "版面": x["版面"], "W1": len(x["W1"]), "W1原數": x["W1原數"],
                   "G1": len(g1), "G2": len(g2), "G1全(未限W1)": x["G1全"], "G2全(未限W1)": x["G2全"], "G1∩G2": len(g1 & g2),
                   "G1中也在G2": (len(g1 & g2) / len(g1) if g1 else np.nan), "G2中也在G1": (len(g1 & g2) / len(g2) if g2 else np.nan),
                   "Jaccard": (len(g1 & g2) / len(g1 | g2) if (g1 | g2) else np.nan)})
    BR = pd.DataFrame(BR)
    # ── 重疊 ② 營量、營飆
    from backtest import rerun17 as RR
    import backtest.data as D
    D.DATA = RR.H2D
    mcal = D.load_calendar()
    reg = RR.regime_mask(RR.load_bench(mcal))
    AN = pd.read_csv(AND_CSV, dtype={"sid": str}, usecols=["sid", "pos", "entry_pos"])
    AN = AN[(AN["pos"] < len(mcal)) & (AN["entry_pos"] <= len(mcal))].copy()
    AN["m"] = [f"{d.year}-{d.month:02d}" for d in mcal[AN["pos"].to_numpy()]]
    AN["飆"] = reg[AN["entry_pos"].to_numpy() - 1]
    m0, m1 = AN["m"].min(), AN["m"].max()
    LQ = {lab: sub.groupby("m")["sid"].apply(set).to_dict() for lab, sub in (("營量", AN), ("營飆", AN[AN["飆"]]))}
    for lab in ("營量", "營飆"):
        for G in ("G1", "G2"):
            c1, c2 = [], []
            for j, x in enumerate(BT):
                m = x["d"][:7]
                if not (m0 <= m <= m1):
                    c1.append(np.nan); c2.append(np.nan); continue
                L = LQ[lab].get(m, set()); g = set(x[G])
                c1.append(len(g & L) / len(g) if g else np.nan); c2.append(len(g & L) / len(L) if L else np.nan)
            BR[f"{G}中為當月{lab}"] = c1; BR[f"當月{lab}中在{G}"] = c2
        BR[f"當月{lab}檔數"] = [len(LQ[lab].get(x["d"][:7], set())) if m0 <= x["d"][:7] <= m1 else np.nan for x in BT]
    OV = []
    for nm in [s[0] for s in SEGS] + ["全期"]:
        d = BR if nm == "全期" else BR[BR["段"] == nm]
        row = {"段": nm, "批數": len(d), "G1∩G2÷G1(批平均)": float(d["G1中也在G2"].mean()), "G1∩G2÷G2(批平均)": float(d["G2中也在G1"].mean()),
               "Jaccard(批平均)": float(d["Jaccard"].mean()),
               "G1∩G2÷G1(合計)": float(d["G1∩G2"].sum() / max(1, d["G1"].sum())), "G1∩G2÷G2(合計)": float(d["G1∩G2"].sum() / max(1, d["G2"].sum()))}
        for lab in ("營量", "營飆"):
            for G in ("G1", "G2"):
                row[f"{G}中為當月{lab}(批平均)"] = float(d[f"{G}中為當月{lab}"].mean()); row[f"當月{lab}中在{G}(批平均)"] = float(d[f"當月{lab}中在{G}"].mean())
            row[f"{lab}比得到批數"] = int(d[f"當月{lab}檔數"].notna().sum())
        OV.append(row)
    OV = pd.DataFrame(OV)
    log(f"[重疊] 營量月 {m0}～{m1}｜{time.time() - t0:.0f}s")
    # ── 隨機框架（B11）
    RF = []
    for G in ("G1", "G2"):
        same = []
        st = {H: [] for H in HS}
        for r in range(NRAND):
            rng = np.random.default_rng([SEED, r])
            draw = []
            for j, x in enumerate(BT):
                pool = sorted(x["W1"]); nb = len(x[G])
                pk = [pool[k] for k in rng.permutation(len(pool))[:nb]] if nb else []
                draw.append(pk)
            tot = sum(len(x[G]) for x in BT)
            same.append(sum(len(set(dw) & set(x[G])) for dw, x in zip(draw, BT)) / max(1, tot))
            if r < RSTRUCT:
                for H in HS:
                    res = sim(PR, draw, H)
                    a_ = int(CAL.searchsorted(pd.Timestamp("2017-03-01"))); z_ = int(CAL.searchsorted(pd.Timestamp("2021-12-31"), "right")) - 1
                    st[H].append((float(res["distinct"][a_:z_ + 1].mean()), float((1 - res["inv"][a_:z_ + 1]).mean())))
        for H in HS:
            v = np.array(st[H])
            RF.append({"格": G, "H": H, "隨機次數": NRAND, "與訊號批同檔比例 平均": float(np.mean(same)), "p5": float(np.percentile(same, 5)), "p95": float(np.percentile(same, 95)),
                       f"前{RSTRUCT}次 探索段同時持有平均 中位": float(np.median(v[:, 0])), "最小": float(v[:, 0].min()), "最大": float(v[:, 0].max()),
                       f"前{RSTRUCT}次 探索段現金 中位": float(np.median(v[:, 1])), "現金最大": float(v[:, 1].max())})
        log(f"[隨機] {G}｜{time.time() - t0:.0f}s")
    RF = pd.DataFrame(RF)
    # ── 輸出
    CE.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    BR.to_csv(os.path.join(out, "batches.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    OV.to_csv(os.path.join(out, "overlap.csv"), index=False, encoding="utf-8-sig")
    RF.to_csv(os.path.join(out, "random_frame.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "廣撒長抱 seq1 頻率表（⛔ 未算任何報酬；R 全 0 帳）", "登錄": f"台股策略線 seq1 sha {REG_SHA}（{PR['reg']}）", "裁定": RUL, "origin/main": PR["sha"],
         "W1 面板": PR["W1info"], "批數": len(BT), "首批／末批": [BT[0]["d"], BT[-1]["d"]], "份數": NSL, "出場計數(prep)": {f"H{k[0]} {k[1]}": v for k, v in PR["cnt"].items()},
         "帳計數": CNT, "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "a", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--sha", required=True)
    ap.add_argument("--step", choices=["prep", "freq"], required=True)
    a = ap.parse_args()
    if a.step == "prep":
        step_prep(a)
        os.makedirs(OUT, exist_ok=True)
        open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    else:
        step_freq(a)


if __name__ == "__main__":
    main()

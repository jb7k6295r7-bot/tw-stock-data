# -*- coding: utf-8 -*-
"""被公開收購／經營權變動／私募 事件層描述 seq2【報酬・描述，不計 N】（台股策略線 登錄 sha 41a4f93d8210932e；裁定 seq441 發號、seq443 §四 核 seq2、
seq448 §三 E2 主表 v1c、seq449 §四 核頻率表並開報酬）——回測線計算子代理。
⛔ 描述，不是選股規則；⛔ 不判、不計 N、不推 LINE。
⛔ 不 commit、不改既有檔；researchTakeover_freq（頻率表：讀法 U0～U8 寫死、沿用；事件、配對、窗狀態）、researchRevTurn_freq（ensure_data）、
   researchIndMom_freq（reg_check）、research11（cl_stats）、researchTurtle（NOTE_EARLY）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover [--dry（R 全寫 0，輸出 ~/tkowork/dry_main）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_check [--dry]
輸出 backtest/resultsTakeover/main/（⛔ 不碰 freq/）：main.json、表.csv（組×段×窗）、先驗.csv、追蹤.csv、減資接續.csv、events.csv.gz（逐筆 R、X）、recon.csv、run.log

═══ 讀法（U 標續編；頻率表 U0～U8 原樣沿用，以下為報酬新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 U9 事件與配對 ＝ 頻率表（resultsTakeover/freq/events.csv.gz，commit 0cefbbd654）：本檔以 researchTakeover_freq 同一批函式、同一 sha（freq.json 的 origin/main）
    逐列重建，全部欄位逐字相同才往下算；任一不同 ⇒ 中止、⛔ 不算報酬（recon.csv）。最新 origin/main 另記；事件表、價格、追蹤資料一律用頻率表那個 sha。
 U10 報酬（登錄 §三；收盤到收盤、還原收盤 ＝ 頻率表價格面板 C）：窗 [a,b] ⇒ R ＝ C[窗尾有效] ÷ C[基準有效] − 1，基準 ＝ day0＋a−1、窗尾 ＝ day0＋b
    （＝ 前 [−30,−1]：c[−1]/c[−31]；當 [0,+1]：c[+1]/c[−1]；後 [+2,+H]：c[+H]/c[+1]）；停牌日用前一根有效 K 棒（報酬記 0）。
    頻率表窗狀態「走得完」收；「下市長停截斷」⭐ 照登錄「下市前最後收盤出場」收（窗尾改最後有效 K 棒；筆數照報）；「窗內壞根」「起點無K棒」「超出資料尾」不收。
    X ＝ R事件 − R配對（登錄 §三）；配對公司同一窗、同一套規則；任一方不可算 ⇒ 該窗 X 不收（照報）。同根兩出場價取較低（seq373）：每窗只有一個出場價 ⇒ 不適用。
 U11 ⭐ E3 有減資 [+2,+250]（seq449 §四）：事件與其配對公司在此窗內的壞根，若能以減資恢復買賣參考價解釋 ⇒
    主口徑「參考價接續」：停牌前最後收盤 → 參考價 持有價值等價（報酬 0）、停牌期間報酬 0、復牌後由參考價接續：
      1＋R ＝ Π 段內 C 比 × Π_k（復牌原始收盤 rc[k] ÷ 參考價）；
    敏感度「減資前最後收盤截斷」：出場 ＝ 窗內第一個減資壞根前最後一根有效 K 棒；配對公司同一天出場（其自身減資照主口徑接續）。
    兩者都標「減資跨斷點」。窗內有非減資壞根、或參考價驗證不過 ⇒ 不收（原因照報）。⭐ 只套用於 E3 with_reduction＝1 的事件（★ E3 全體列裡這些事件也用此口徑）；
    其他組、其他窗照 U10（裁定字面）。
    參考價表 ★（同一 sha，官方優先）：上市官方 universe/reduce（2015 起）＋early/reduce（2011～2014）、上櫃官方 meta/otc_reduce_history＋universe/otcreduce、
    人工 meta/manual_reduce_twse／tpex、data/adj（event＝reduce）；偵測：meta/twse_reduce_early（2004～2010 推估）、meta/otc_reduce_early（2007-07～2012，
    ★ 只取 shares_down＝1 ∧ exright_in_gap＝0）。對應 ＝ 恢復買賣日 ∈ (前一根有效 K 棒日, 壞根日]；★ 驗證：|表前收 ÷ 原始收盤[前一根] − 1| ≤ 2%、
    復牌原始收盤 ÷ 參考價 ∈ [0.85, 1.15]；原始收盤 ＝ 該世界 stocks/<代號>.csv close。
 U12 統計（描述）：每組×段×窗報 R事件 平均、中位、勝率；X 平均、中位、勝率、公告月分群 CI（research11.cl_stats，1.96；key ＝ 公告日年月）；
    n_eff ＝ min(筆數, 公告月數)；＜ 30 照標「事件少」。段 ＝ 頻率表 U6（依公告日）：早年 2005～2016｜探索 2017-03～2021｜確認 2022～｜全期 2005～。
    CI 結果記 ①（含 0）／②（下界 ＞ 0）／③（上界 ＜ 0），⛔ 只是描述、不判。
 U13 組（seq449 §四）：E1 只報主臂（最早日）；E1 對照臂只寫一句「對照臂只多 14 筆、結論同／不同」（★ 同 ＝ 全期各窗 X̄ 同號且 CI 結果相同）；
    E1 成功、結果空白分報；E1 失敗（2 筆）、E2 小市值組 ⇒「事件太少」不描述；E2 v1b 只寫一句（同上判法）；E2 含重疊另報（登錄 §六）；
    市值 ≤10 億／＞10 億（登錄 §三）照報（E2 小市值除外）。
 U14 先驗（登錄 §五；★ 以 X 判讀，登錄 §三 的量是 X；全期 2005～；R事件 並列）：
    ① E1 前 [−30,−1] X̄ ＞ 0 ⇒ 中｜② E1 後 [+2,+250] X 的 CI 含 0 ⇒ 中｜③ E3 有減資 後 [+2,+250]（主口徑）X̄ ＜ 0 ⇒ 中（敏感度並報）｜
    ④ E2 小市值組 ⇒ 事件太少、不描述（seq449）。
 U15 事後追蹤（登錄 §四；事件與配對公司都報）：★ 公告後被列注意股、處置股 ＝ meta/attention.csv（date）、meta/disposal.csv（announce_date）
    落在 [day0, day0＋20]、[day0, day0＋60] 交易日（兩表 2011-01 起 ⇒ day0 ≥ 2011-01-03 才計）；後來減資 ＝ U11 參考價表任一來源的恢復買賣日落在
    (day0, day0＋250]；全額交割 ＝ universe/fulldelivery 日檔（2015-01-05 起）任一天在 [day0, day0＋250]。窗尾超出價格資料尾 ⇒ 不計（分母照報）。
 U16 必附：「描述，不是選股規則」「E2 為 v1c（人工抽查嚴格 72%／寬鬆 100%）」「E3 未分策略投資人（待 seq3）」「早年 reduce_v2 約 0.3% 註」
    「只看單筆、沒算賣掉的錢」「事件少」「被收購方報酬受收購價壓住」「台灣文獻只讀到摘要」。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import io
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTakeover_freq as TF            # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchTopSell_freq as TS             # noqa: E402  raw_close
from backtest import research11 as R11                      # noqa: E402  cl_stats
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY

REG_SHA = TF.REG_SHA
OUT = "backtest/resultsTakeover/main"
FREQ_DIR = TF.OUT
WORK = TF.WORK
WINS = TF.WINS
W250 = "後[+2,+250]"
SEGS = [s for s in TF.SEGS if s[0] != "全表"]
NEFF_MIN = 30
EXTRA = ["data/adj", "data/universe/reduce", "data/early/reduce", "data/universe/otcreduce", "data/meta/otc_reduce_history.csv",
         "data/meta/twse_reduce_early", "data/meta/otc_reduce_early", "data/meta/manual_reduce_twse", "data/meta/manual_reduce_tpex",
         "data/meta/attention.csv", "data/meta/disposal.csv", "data/universe/fulldelivery"]
SRC_PRI = {"上市官方": 0, "上櫃官方": 0, "人工": 0, "adj": 1, "上市早年偵測": 2, "上櫃早年偵測": 2}
PRE_TOL = 0.02
G_LO, G_HI = 0.85, 1.15
SENT = ["描述，不是選股規則", "E2 為 v1c（人工抽查嚴格 72%／寬鬆 100%）", "E3 未分策略投資人（待 seq3）", "只看單筆、沒算賣掉的錢",
        "事件少（E1、E2 各段 n_eff ＜ 30）", "被收購方報酬受收購價壓住", "台灣文獻只讀到摘要"] + TU.NOTE_EARLY
FEW = {"E1_fail": "事件太少（2 筆）", "E2(v1c主)_市值≤10億": "事件太少（12 筆）"}
REPORT = ["E1", "E1_success", "E1_空白", "E1_市值≤10億", "E1_市值＞10億", "E1對照(被收購方日)", "E2(v1c主)", "E2(v1c主)_市值＞10億", "E2含重疊(v1c)",
          "E2(v1b敏感度)", "E3", "E3_有減資", "E3_無減資", "E3_市值≤10億", "E3_市值＞10億", "E3_有減資_市值≤10億", "E3_有減資_市值＞10億"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def gsel(E, name):
    if name in TF.GROUPS:
        return TF.GROUPS[name](E)
    base, mg = name.rsplit("_市值", 1)
    s = TF.GROUPS[base](E)
    return s[(s["st"] == "保留") & (s["市值組"] == mg)]


# ═════════════ U9 頻率表逐列重建 ═════════════
def rebuild(sha, DN, PX, procs):
    """researchTakeover_freq.main 的事件、配對段落原樣（同一批函式），回 E（字串化，與 freq/events.csv.gz 同口徑）。"""
    CAL = PX["CAL"]
    ev = TF.load_table(sha); tail_ev = pd.Timestamp(ev["date"].max())
    b1, MB = TF.load_build(sha, "v1b", True)
    evb = pd.read_csv(b1, dtype=str, keep_default_na=False); e2b = evb[evb["class"] == "E2"].copy()
    st = pd.read_csv(os.path.join(DN, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); alive = set(st.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])

    def cd_of(df):
        m = defaultdict(list)
        for s, d in zip(df["stock_id"], df["date"]):
            m[s].append(np.datetime64(pd.Timestamp(d)))
        return {s: np.array(sorted(v)) for s, v in m.items()}
    cls_dates = {"E1": cd_of(ev[ev["class"] == "E1"]), "E2": cd_of(ev[ev["class"] == "E2"]), "E2b": cd_of(e2b), "E3": cd_of(ev[ev["class"] == "E3"])}
    base_cols = ["first12m", "outcome", "acq_date", "with_reduction", "reduction_type", "overlap_e1", "market", "time"]
    units = []

    def mk(r, cls, arm, p0, extra=None):
        u = {"類": cls, "臂": arm, "sid": r["stock_id"], "date": r["date"], "p0": p0, **{c: r[c] for c in base_cols}}
        if extra:
            u.update(extra)
        return u
    e1 = ev[(ev["class"] == "E1") & (ev["followup"] == "0")]
    AQ = TF.acq_times(sha, MB, e1)
    for _, r in e1.iterrows():
        pt = TF.day0_of(CAL, r["date"], r["time"])
        ad, at = AQ[(r["stock_id"], r["date"])]
        if r["acq_date"]:
            pa = TF.day0_of(CAL, r["acq_date"], at if ad == r["acq_date"] else "")
            pa_d = int(CAL.searchsorted(pd.Timestamp(r["acq_date"]), "left"))
        else:
            pa = pa_d = pt
        pe = min(pt, pa); pe_d = min(pt, pa_d)
        ex = {"最早日提前(交易日)": int(pt - pe), "acq_time": at if r["acq_date"] else "", "日期版day0差": int(pe - pe_d)}
        units.append(mk(r, "E1", "最早日", pe, ex)); units.append(mk(r, "E1", "被收購方日", pt, ex))
    for _, r in ev[ev["class"] == "E2"].iterrows():
        units.append(mk(r, "E2", "v1c", TF.day0_of(CAL, r["date"], r["time"])))
    for _, r in e2b.iterrows():
        units.append(mk(r, "E2b", "v1b", TF.day0_of(CAL, r["date"], r["time"])))
    for _, r in ev[(ev["class"] == "E3") & (ev["first12m"] == "1")].iterrows():
        units.append(mk(r, "E3", "全體", TF.day0_of(CAL, r["date"], r["time"])))
    rows = TF.process(units, PX, alive, cls_dates, tail_ev, {})
    E = pd.DataFrame(rows)
    buf = io.StringIO(); E.to_csv(buf, index=False); buf.seek(0)
    return pd.read_csv(buf, dtype=str, keep_default_na=False)


# ═════════════ U11 參考價表 ═════════════
def ensure_extra(sha):
    root = os.path.join(WORK, f"main_{sha[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + EXTRA, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(sha)
    return os.path.join(root, "data")


def red_table(D):
    fr = []

    def add(df, dcol, pcol, src):
        x = pd.DataFrame({"sid": df["stock_id"].astype(str).str.strip(), "date": pd.to_datetime(df[dcol], errors="coerce"),
                          "pre": pd.to_numeric(df[pcol].astype(str).str.replace(",", ""), errors="coerce"),
                          "ref": pd.to_numeric(df["ref_price"].astype(str).str.replace(",", ""), errors="coerce"), "src": src})
        fr.append(x)

    def cat(pat):
        fs = [f for f in sorted(glob.glob(pat)) if not os.path.basename(f).startswith("_")]
        return pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True) if fs else pd.DataFrame()
    for d in ("universe/reduce", "early/reduce"):
        x = cat(os.path.join(D, d, "*.csv"))
        if len(x):
            add(x, "date", "pre_close", "上市官方")
    x = cat(os.path.join(D, "universe/otcreduce", "*.csv"))
    if len(x):
        add(x, "date", "pre_close", "上櫃官方")
    add(pd.read_csv(os.path.join(D, "meta/otc_reduce_history.csv"), dtype=str), "date", "last_close", "上櫃官方")
    for d in ("manual_reduce_twse", "manual_reduce_tpex"):
        ln = open(os.path.join(D, "meta", d, "manual_reduce.csv"), encoding="utf-8").read().splitlines()
        hdr = ln[0].split(",")[:4]                                    # 原因、出處欄含未加引號的逗號 ⇒ 只取前 4 欄
        add(pd.DataFrame([l.split(",", 4)[:4] for l in ln[1:] if l.strip()], columns=hdr), "date", "pre_close", "人工")
    al = []
    for f in glob.glob(os.path.join(D, "adj", "*.csv")):
        b = os.path.basename(f)[:-4]
        if b.startswith("_"):
            continue
        a = pd.read_csv(f, dtype=str)
        a = a[a["event"] == "reduce"]
        if len(a):
            a = a.assign(stock_id=b); al.append(a)
    if al:
        add(pd.concat(al, ignore_index=True), "date", "pre_close", "adj")
    tw = pd.read_csv(os.path.join(D, "meta/twse_reduce_early/twse_reduce_detected_2004_2010.csv"), dtype=str)
    add(tw, "date", "pre_close", "上市早年偵測")
    oc = pd.read_csv(os.path.join(D, "meta/otc_reduce_early/otc_reduce_detected_2007_2012.csv"), dtype=str)
    oc = oc[(oc["shares_down"] == "1") & (oc["exright_in_gap"] == "0")]
    add(oc, "resume_day", "last_close", "上櫃早年偵測")
    T = pd.concat(fr, ignore_index=True).dropna(subset=["date", "ref"])
    T = T[(T["ref"] > 0) & T["sid"].str.fullmatch(r"\d{4}")]
    T["pri"] = T["src"].map(SRC_PRI)
    T = T.sort_values(["sid", "date", "pri"]).reset_index(drop=True)
    tab = defaultdict(list)
    for s, d, p, r, src, pr in zip(T["sid"], T["date"], T["pre"], T["ref"], T["src"], T["pri"]):
        tab[s].append((d, p, r, src, pr))
    return tab, dict(Counter(T["src"]))


class Red:
    def __init__(self, PX, tab):
        self.PX = PX; self.tab = tab; self.memo = {}; self.cnt = Counter()

    def raw(self, i, p):
        PX = self.PX
        data = PX["early_data"] if p < PX["NE"] else PX["main_data"]
        return TS.raw_close(data, PX["SIDS"][i], PX["CAL"][p])

    def look(self, i, k):
        """壞根 k（第 i 檔）⇒ (g, 來源) 或 (None, 原因)。"""
        key = (i, k)
        if key in self.memo:
            return self.memo[key]
        PX = self.PX; CAL = PX["CAL"]
        pv = int(PX["LV"][i, k - 1]) if k > 0 else -1
        out = (None, "前無有效K棒")
        if pv >= 0:
            c = [x for x in self.tab.get(PX["SIDS"][i], ()) if CAL[pv] < x[0] <= CAL[k]]
            if not c:
                out = (None, "查無減資參考價")
            else:
                c.sort(key=lambda x: (x[4], x[0]))
                d, pre, ref, src, _ = c[0]
                rp = self.raw(i, pv); rk = self.raw(i, k)
                if not (np.isfinite(rp) and np.isfinite(rk) and rp > 0 and rk > 0):
                    out = (None, "原始收盤缺")
                elif np.isfinite(pre) and abs(pre / rp - 1) > PRE_TOL:
                    out = (None, "前收對不上")
                elif not (G_LO <= rk / ref <= G_HI):
                    out = (None, "復牌價對不上參考價")
                else:
                    out = (rk / ref, src)
        self.memo[key] = out
        return out


def ret_std(PX, i, p0, a, b):
    st = TF.walk(PX, i, p0, a, b)
    if st not in ("走得完", "下市長停截斷"):
        return np.nan, st, -1
    base = p0 + a - 1; end = p0 + b
    bv = int(PX["LV"][i, base]); last = int(PX["LASTV"][i])
    ev = int(PX["LV"][i, min(end, last)]) if last > base else bv
    return PX["C"][i, ev] / PX["C"][i, bv] - 1.0, st, ev


def ret_red(PX, RD, i, p0, a, b, mode, exit_pos=None):
    """U11：mode ＝ 接續／截斷；exit_pos 給定 ⇒ 窗尾改為該日曆位置（配對公司跟事件同一天出場）。回 (R, 狀態, 出場位置, 截斷位置)。"""
    NC = len(PX["CAL"]); base = p0 + a - 1; end = p0 + b if exit_pos is None else exit_pos
    if p0 + b >= NC:
        return np.nan, "超出資料尾", -1, -1
    if base < 0 or PX["LV"][i, base] < 0:
        return np.nan, "起點無K棒", -1, -1
    bv = int(PX["LV"][i, base]); last = int(PX["LASTV"][i])
    if last <= base:
        return 0.0, "下市長停截斷", bv, -1
    hi = min(end, last)
    bads = [int(k) for k in np.flatnonzero(PX["BAD"][i, bv + 1:hi + 1]) + bv + 1]
    tag = "下市長停截斷" if last < end else "走得完"
    C = PX["C"]
    if not bads:
        ev = int(PX["LV"][i, hi])
        return C[i, ev] / C[i, bv] - 1.0, tag, ev, -1
    info = [RD.look(i, k) for k in bads]
    bad_reason = [r for g, r in info if g is None]
    if bad_reason:
        return np.nan, "窗內壞根(" + bad_reason[0] + ")", -1, -1
    if mode == "截斷":
        pv = int(PX["LV"][i, bads[0] - 1])
        return C[i, pv] / C[i, bv] - 1.0, "減資跨斷點(截斷)", pv, pv
    f = 1.0; cur = bv
    for k, (g, src) in zip(bads, info):
        pv = int(PX["LV"][i, k - 1])
        f *= C[i, pv] / C[i, cur] * g; cur = k
    ev = int(PX["LV"][i, hi])
    f *= C[i, ev] / C[i, cur]
    return f - 1.0, "減資跨斷點(接續)" + ("・截斷" if tag != "走得完" else ""), ev, -1


# ═════════════ 統計 ═════════════
def stat(x, mon):
    x = np.asarray(x, float); mon = np.asarray(mon); ok = np.isfinite(x)
    if ok.sum() == 0:
        return {"n": 0}
    s = R11.cl_stats(x[ok], mon[ok])
    s["n_eff"] = min(s["n"], s["months"]); s["n_eff<30"] = bool(s["n_eff"] < NEFF_MIN)
    s["CI結果"] = "①" if s["lo"] <= 0 <= s["hi"] else ("②" if s["lo"] > 0 else "③")
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(WORK, "dry_main") if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑：R 全寫 0' if a.dry else '正式跑'}")
    FJ = json.load(open(os.path.join(FREQ_DIR, "freq.json"), encoding="utf-8")); sha = FJ["origin/main"]
    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    latest = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    log(f"[資料] 頻率表 sha {sha}｜最新 origin/main {latest}｜{'相同' if latest == sha else '不同（本件照頻率表 sha）'}")
    sha_, DN, MD = RT.ensure_data(sha)
    PX = TF.price_panel(sha, DN, a.procs); CAL = PX["CAL"]; NC = len(CAL)
    log(f"[價格] {CAL[0].date()}～{CAL[-1].date()}｜{time.time() - t0:.0f}s")
    # U9
    E = rebuild(sha, DN, PX, a.procs)
    F = pd.read_csv(os.path.join(FREQ_DIR, "events.csv.gz"), dtype=str, keep_default_na=False)
    rec = {"列數": [len(E), len(F)], "欄相同": list(E.columns) == list(F.columns)}
    diff = []
    if rec["欄相同"] and len(E) == len(F):
        for c in F.columns:
            m = E[c].to_numpy() != F[c].to_numpy()
            if m.any():
                diff.append({"欄": c, "不同列數": int(m.sum()), "例": str(list(zip(F.loc[m, "sid"].head(3), E.loc[m, c].head(3), F.loc[m, c].head(3))))})
    rec["不同欄"] = diff
    pd.DataFrame(diff or [{"欄": "（全部相同）", "不同列數": 0}]).to_csv(os.path.join(out, "recon.csv"), index=False, encoding="utf-8-sig")
    log(f"[U9 重建] {rec}")
    if not (rec["欄相同"] and len(E) == len(F) and not diff):
        open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        raise SystemExit("⛔ 頻率表逐列重建不同 ⇒ 中止、不算報酬")
    E = F.copy()
    # U11 參考價表
    DX = ensure_extra(sha)
    tab, srcc = red_table(DX)
    RD = Red(PX, tab)
    log(f"[參考價表] 來源 {srcc}")
    ix = PX["ix"]
    # U10／U11 逐列
    recs = []
    for k, r in E.iterrows():
        row = {"_k": k}
        if r["st"] != "保留":
            recs.append(row); continue
        i = ix[r["sid"]]; p0 = int(CAL.searchsorted(pd.Timestamp(r["day0"])))
        j = ix[r["配對sid"]] if r["配對sid"] else None
        red = (r["類"] == "E3") and (r["with_reduction"] == "1")
        for w, (a_, b_) in WINS.items():
            if red and w == W250:
                Re, se, ee, cut = ret_red(PX, RD, i, p0, a_, b_, "接續")
                Rm, sm = (np.nan, "") if j is None else ret_red(PX, RD, j, p0, a_, b_, "接續")[:2]
                Rt, stt, _, cutp = ret_red(PX, RD, i, p0, a_, b_, "截斷")
                if j is not None and np.isfinite(Rt):
                    Rmt, smt = ret_red(PX, RD, j, p0, a_, b_, "接續", exit_pos=(cutp if cutp >= 0 else None))[:2]
                else:
                    Rmt, smt = np.nan, ""
                row.update({f"R截斷{w}": Rt, f"狀態截斷{w}": stt, f"配R截斷{w}": Rmt, f"配狀態截斷{w}": smt})
            else:
                Re, se, _ = ret_std(PX, i, p0, a_, b_)
                Rm, sm = (np.nan, "") if j is None else ret_std(PX, j, p0, a_, b_)[:2]
            row.update({f"R{w}": Re, f"狀態{w}": se, f"配R{w}": Rm, f"配狀態{w}": sm})
        recs.append(row)
    RR = pd.DataFrame(recs).set_index("_k")
    for c in RR.columns:
        if c.startswith("R") or c.startswith("配R"):
            RR[c] = pd.to_numeric(RR[c], errors="coerce")
            if a.dry:
                RR[c] = RR[c].where(RR[c].isna(), 0.0)
    E = E.join(RR)
    for w in WINS:
        E[f"X{w}"] = E[f"R{w}"] - E[f"配R{w}"]
    E[f"X截斷{W250}"] = E[f"R截斷{W250}"] - E[f"配R截斷{W250}"]
    E["date_dt"] = pd.to_datetime(E["date"]); E["公告月"] = E["date"].str[:7]
    log(f"[報酬] 逐列完成｜參考價查詢 {len(RD.memo)} 個壞根：{dict(Counter(v[1] for v in RD.memo.values()))}｜{time.time() - t0:.0f}s")
    # U15 追蹤
    att = pd.read_csv(os.path.join(DX, "meta", "attention.csv"), dtype=str); dis = pd.read_csv(os.path.join(DX, "meta", "disposal.csv"), dtype=str)
    fds = [f for f in sorted(glob.glob(os.path.join(DX, "universe", "fulldelivery", "*.csv"))) if not os.path.basename(f).startswith("_")]
    fd = pd.concat([pd.read_csv(f, dtype=str, usecols=["date", "stock_id"]) for f in fds], ignore_index=True)

    def dmap(df, dc):
        m = defaultdict(list)
        for s, d in zip(df["stock_id"].astype(str).str.strip(), pd.to_datetime(df[dc], errors="coerce")):
            if pd.notna(d):
                m[s].append(np.datetime64(d))
        return {s: np.array(sorted(v)) for s, v in m.items()}
    MA, MD_, MF = dmap(att, "date"), dmap(dis, "announce_date"), dmap(fd, "date")
    MR = {s: np.array(sorted({np.datetime64(x[0]) for x in v})) for s, v in tab.items()}
    A0, D0, F0 = np.datetime64(pd.Timestamp(att["date"].min())), np.datetime64(pd.Timestamp("2011-01-03")), np.datetime64(pd.Timestamp(fd["date"].min()))

    def hit(M, s, lo, hi, incl_lo=True):
        v = M.get(s)
        if v is None:
            return False
        k = np.searchsorted(v, lo, "left" if incl_lo else "right")
        return bool(k < len(v) and v[k] <= hi)
    fu = defaultdict(list)
    for _, r in E.iterrows():
        res = {}
        if r["st"] == "保留":
            p0 = int(CAL.searchsorted(pd.Timestamp(r["day0"]))); d0 = np.datetime64(CAL[p0])
            for who, s in (("", r["sid"]), ("配", r["配對sid"])):
                if not s:
                    continue
                for nm, M, H, start in (("注意", MA, 20, max(A0, D0)), ("注意", MA, 60, max(A0, D0)), ("處置", MD_, 20, D0), ("處置", MD_, 60, D0),
                                        ("後來減資", MR, 250, None), ("全額交割", MF, 250, F0)):
                    key = f"{who}{nm}{H}"
                    if p0 + H >= NC or (start is not None and d0 < start):
                        res[key] = ""; continue
                    hi = np.datetime64(CAL[p0 + H])
                    res[key] = str(hit(M, s, d0, hi, incl_lo=(nm != "後來減資")))
        for c in ("注意20", "注意60", "處置20", "處置60", "後來減資250", "全額交割250"):
            for who in ("", "配"):
                fu[f"{who}{c}"].append(res.get(f"{who}{c}", ""))
    for c, v in fu.items():
        E[c] = v
    # U12／U13 表
    TAB = []
    for sg, x, y in SEGS:
        x_, y_ = pd.Timestamp(x), pd.Timestamp(y)
        for g in REPORT + list(FEW):
            sub = gsel(E, g); sub = sub[(sub["date_dt"] >= x_) & (sub["date_dt"] <= y_) & (sub["st"] == "保留")]
            for w in list(WINS) + [f"截斷{W250}"]:
                if w.startswith("截斷") and not g.startswith("E3_有減資"):
                    continue
                rw = {"段": sg, "組": g, "窗": w if not w.startswith("截斷") else f"{W250}（減資前截斷，敏感度）"}
                if g in FEW:
                    rw["註"] = FEW[g]; TAB.append(rw); continue
                Rc, Xc = f"R{w}", f"X{w}"
                se = stat(sub[Rc], sub["公告月"]); sx = stat(sub[Xc], sub["公告月"])
                stc = f"狀態{w}"
                rw.update({"可接": len(sub), "R_n": se.get("n", 0), "R平均": se.get("mean"), "R中位": se.get("median"), "R勝率": se.get("win"),
                           "X_n": sx.get("n", 0), "X平均": sx.get("mean"), "X中位": sx.get("median"), "X勝率": sx.get("win"), "X_lo": sx.get("lo"),
                           "X_hi": sx.get("hi"), "X月數": sx.get("months"), "X_n_eff": sx.get("n_eff"), "n_eff<30": sx.get("n_eff<30"),
                           "CI結果(描述)": sx.get("CI結果"),
                           "下市長停截斷筆數": int(sub[stc].astype(str).str.contains("下市長停截斷|・截斷").sum()) if stc in sub else 0,
                           "減資跨斷點筆數": int(sub[stc].astype(str).str.startswith("減資跨斷點").sum()) if stc in sub else 0,
                           "不收_壞根": int(sub[stc].astype(str).str.startswith("窗內壞根").sum()) if stc in sub else 0,
                           "不收_超出資料尾": int((sub[stc] == "超出資料尾").sum()) if stc in sub else 0,
                           "配對不可算或配對R缺": int((sub[Rc].notna() & sub[Xc].isna()).sum())})
                TAB.append(rw)
    T = pd.DataFrame(TAB)
    # 一句話：E1 對照臂、E2 v1b
    def same_concl(g1, g2):
        q = T[(T["段"] == "全期(2005～)") & T["組"].isin([g1, g2]) & ~T["窗"].str.contains("截斷")]
        res = []
        for w, s in q.groupby("窗"):
            a1 = s[s["組"] == g1].iloc[0]; a2 = s[s["組"] == g2].iloc[0]
            res.append(bool(np.sign(a1["X平均"] or 0) == np.sign(a2["X平均"] or 0) and a1["CI結果(描述)"] == a2["CI結果(描述)"]))
        return all(res), res
    s1, l1 = same_concl("E1", "E1對照(被收購方日)"); s2, l2 = same_concl("E2(v1c主)", "E2(v1b敏感度)")
    ONE = {"E1對照": f"對照臂（被收購方日）與主臂只差 14 筆 day0，全期五窗 X̄ 同號且 CI 結果相同：{'結論同' if s1 else '結論不同'}（逐窗 {l1}）",
           "E2v1b": f"E2 v1b（多 4 筆）敏感度：全期五窗 X̄ 同號且 CI 結果相同：{'結論同' if s2 else '結論不同'}（逐窗 {l2}）"}
    # U14 先驗
    def cell(g, w):
        q = T[(T["段"] == "全期(2005～)") & (T["組"] == g) & (T["窗"] == w)]
        return q.iloc[0] if len(q) else None
    PRI = []
    c1 = cell("E1", "前[-30,-1]"); c2 = cell("E1", W250); c3 = cell("E3_有減資", W250); c3s = cell("E3_有減資", f"{W250}（減資前截斷，敏感度）")
    PRI.append({"先驗": "① E1 公告前 [−30,−1] 平均 > 0（約七成）", "X平均": c1["X平均"], "CI": [c1["X_lo"], c1["X_hi"]], "R平均": c1["R平均"],
                "結果": "中" if (c1["X平均"] or 0) > 0 else "不中"})
    PRI.append({"先驗": "② E1 公告後 [+2,+250] 與配對分不出（約六成）", "X平均": c2["X平均"], "CI": [c2["X_lo"], c2["X_hi"]], "R平均": c2["R平均"],
                "結果": "中" if c2["CI結果(描述)"] == "①" else "不中"})
    PRI.append({"先驗": "③ E3 有減資組 [+2,+250] 平均 < 0（約六成）｜主口徑參考價接續（減資跨斷點）", "X平均": c3["X平均"], "CI": [c3["X_lo"], c3["X_hi"]],
                "R平均": c3["R平均"], "結果": "中" if (c3["X平均"] or 0) < 0 else "不中",
                "敏感度(減資前截斷)": {"X平均": c3s["X平均"], "CI": [c3s["X_lo"], c3s["X_hi"]], "結果": "中" if (c3s["X平均"] or 0) < 0 else "不中"}})
    PRI.append({"先驗": "④ E2 小市值組 [+2,+250] 中位 < 0 但平均 > 0（約五成）", "結果": "不描述：事件太少（seq449 §四）"})
    # 追蹤表
    FU = []
    for g in REPORT + list(FEW):
        if g in FEW:
            FU.append({"組": g, "註": FEW[g]}); continue
        sub = gsel(E, g); sub = sub[(sub["st"] == "保留") & (sub["date_dt"] >= pd.Timestamp("2005-01-01"))]
        rw = {"組": g, "可接(2005～)": len(sub)}
        for c in ("注意20", "注意60", "處置20", "處置60", "後來減資250", "全額交割250"):
            for who in ("", "配"):
                v = sub[f"{who}{c}"]; den = int((v != "").sum()); num = int((v == "True").sum())
                rw[f"{who}{c}_分母"] = den; rw[f"{who}{c}_比例"] = round(num / den, 4) if den else None
        FU.append(rw)
    # 減資接續明細
    rd = E[(E["類"] == "E3") & (E["with_reduction"] == "1") & (E["st"] == "保留")]
    RDT = {"主口徑狀態": dict(Counter(rd[f"狀態{W250}"])), "配對主口徑狀態": dict(Counter(rd[f"配狀態{W250}"])),
           "截斷狀態": dict(Counter(rd[f"狀態截斷{W250}"])), "配對截斷狀態": dict(Counter(rd[f"配狀態截斷{W250}"])),
           "參考價查詢結果": dict(Counter(v[1] for v in RD.memo.values()))}
    J = {"性質": "公開收購／經營權／私募 seq2 事件層描述（不計 N、不判）" + ("【乾跑 R 全 0】" if a.dry else ""), "登錄": f"台股策略線 seq2 sha {REG_SHA}",
         "裁定": "seq441、seq443 §四、seq448 §三、seq449 §四", "頻率表sha": sha, "最新origin/main": latest, "重建": rec, "參考價表來源": srcc,
         "一句話": ONE, "先驗": PRI, "減資接續": RDT, "必附": SENT, "同根兩出場價": "每窗一個出場價 ⇒ seq373 不適用",
         "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
    T.to_csv(os.path.join(out, "表.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PRI).to_csv(os.path.join(out, "先驗.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FU).to_csv(os.path.join(out, "追蹤.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([{"項": k, "值": json.dumps(v, ensure_ascii=False)} for k, v in RDT.items()]).to_csv(os.path.join(out, "減資接續.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(out, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        E.drop(columns=["date_dt"]).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[減資接續] {RDT}")
    log(f"[一句話] {ONE}")
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

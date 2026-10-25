# -*- coding: utf-8 -*-
"""H1「營收見頂確認、先賣一半」seq1 頻率表（台股策略線登錄 seq1 sha 42d64aee7df4e61b；裁定 seq474 §六核：描述、不判、不計 N）——回測線計算子代理。
⛔ 本檔不算任何報酬（不讀價格值，只用交易日曆、成交旗標、壞根／下市位置）；⛔ 不 commit、不改既有檔。
檔名說明：backtest/researchH1.py、researchH1_check.py、resultsH1/ 早已存在（別件 PREREGH1，已 commit）⇒ ⛔ 不覆寫，本件改名 researchH1half*、結果夾 resultsH1half/。
引擎＝researchLampCensus（Engine、load_signals、codes_of、q_last_month；researchV41EV.tw_cap）只 import——★ 凍結在 commit 04d50972fe 版（git show 載入，不讀工作樹）；
月營收＝bigrun_monthly.load_rev_pit（rev_metrics 的資料來源；revpit 夾＝researchRevTurn_freq.ensure_data(PIN) 同一版）只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_freq
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_freq_check
輸出 backtest/resultsH1half/freq/：events.csv（每訊號×每檔一列）、freq.csv、freq.md、main.json、run.log

═══ 讀法（★＝執行者定；寫死於看任何數字之前）═══
 F0 樣本（普查）＝ researchLampCensus 同一套：清單 v3 44 列；甲＝版本 甲／兩版，乙＝乙／兩版；公司欄「無點名」不算（另報）；
    乙版「待定」本來不在清單乙版內（清單中「待定」字樣 0 列 ⇒ 照報 0）。規模下限＝燈 1 季最後一個交易日市值 ≥ 100 億（V.tw_cap 同函式），不足剔除、列名單。
    進場＝燈 1 季結束後第一個有成交日還原開盤（LC.Engine.entry 同函式）；主程式逐筆比對 resultsLampCensus/rows.csv（燈1、H＝末）進場日，⛔ 不同即停。
 F0′ 舊 31 段（只描述、另欄）＝ resultsV41EV/cases_input.csv 台股 31 案 × members.csv 代表股版、同業等權版入選成員（同 researchAddOnLamp2）；
    進場＝燈亮月次月第一個有成交日（同 Engine.entry）；⛔ 不套規模下限（兩版本來就沒有）；主程式比對 resultsAddOnLamp2/rows.csv 燈1 進場日。
 F1 ★ E（評估點）＝「進場月＋60 個月」那個月的第一個交易日（面板日曆）；該月 1 日晚於面板尾或該月在面板尾前沒有交易日 ⇒「未到」，H1 觀察到資料末日為止。
 F2 S_m（登錄 §二）＝ (第 m、m−1、m−2 月營收合計 ÷ 去年同 3 個月合計) − 1。
    ★ 營收＝load_rev_pit 的 rev（每日版優先、否則 revenue_hist，公告當時口徑）；★ 去年同月＝同一列的「去年當月營收」ly（＝ rev_metrics 年增的分母口徑）。
    3 個月中任一個月 rev 或 ly 缺 ⇒ S_m 空；ly 合計 ≤ 0 ⇒ S_m 空。（check 另報分母改用 m−12 期自身 rev 的敏感度。）
 F3 判斷日 J(m) ＝ m+1 月 13 日當天或之後第一個交易日（面板日曆；登錄 §二）。J(m) 落在面板尾之後 ⇒ m 月尚不可用。
    ⚠ 全線規則 2026-01 期起月營收次月 15 日後才可用：登錄寫 13 日 ⇒ 主欄照登錄；確認月 ≥ 2026-01 的件另欄標「15 日規則改日」與改後日期（描述）。
 F4 ★ 起算月 m0 ＝ J(m) 嚴格晚於進場日的最小 m（＝進場日之後第一個可用的月營收）。可用月 ＝ m0 起、J(m) 存在且 J(m) < E（未到 ⇒ ≤ 面板尾）的各月。
 F5 P ＝ 可用月 S 的累計最高（空值跳過、不更新）；觸發需 P > 0。
    ★ 確認（滑動窗）＝ 最早的 m 使：m−2、m−1、m 三個連續日曆月都在可用月內且 S 都有值、都 < P(m−3)（＝m0～m−3 的累計最高，⇒ P 所在月 ≤ m−3），
       P(m−3) > 0，且 S_m ≤ P(m−3)÷2 或 S_m ≤ 0。三個月中有空值 ⇒ 該窗不成立（不跳月）。每檔只觸發一次（取最早）。
 F6 賣出日 ＝ J(m確認) 當天或之後第一個「該檔有成交開盤」日（同進場的順延規則）；須嚴格早於 E 的日期、且不晚於面板尾，否則記「到 E／末日前未確認」。
    ★ 該檔在賣出日前已壞根截斷或下市（截斷位置照 LC.Engine.settle 同式：E 或末日前第一個壞根的前一根有效 K 棒；下市＝最後有效 K 棒距面板尾 ≥5 日）
       ⇒ 記「觸發但已先結算」（不算觸發；H1 等於全抱）。
 F7 時距 ＝ (賣出日 − 進場日) 日曆日 ÷ 30.4375（月）；另報確認月距 m0 的月數。
 F8 營收資料缺 ＝ 可用月中 S 空的月數 ＞ 0 的件數；整段可用月 S 全空 ＝「營收全缺」。
 F9 季分群 n_eff ＝ 燈 1 季（普查）的不同季數；舊 31 段以案（燈亮月）數報。訊號層觸發比例 ＝ 訊號內各檔觸發（1／0）等權平均的平均。
 F5′ 緊接版（描述欄，裁定 seq475 加）：確認窗只看 P 所在月之後緊接的 3 個月；主欄仍為滑動版（seq475 裁定採用）。
 F10 重疊 ＝ 同組內同一代號出現在 ≥2 個訊號（檔數）；其中持有窗（進場～E 或末日）互相重疊的代號數另報。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
import subprocess                                           # noqa: E402
import types                                                # noqa: E402
LC_REV = "04d50972fe"   # ★ researchLampCensus 凍結在已交版（commit 04d50972fe）：工作樹版 2026-10-25 18:21 起被別件改寫中（load_signals 介面已變），⛔ 不跟著變


def _frozen(name, path, rev):
    src = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True, check=True).stdout
    m = types.ModuleType(name); m.__file__ = f"{rev}:{path}"; sys.modules[name] = m
    exec(compile(src, f"{rev}:{path}", "exec"), m.__dict__)
    return m


LC = _frozen("researchLampCensus_at_04d50972fe", "backtest/researchLampCensus.py", LC_REV)
from backtest import researchV41EV as V                     # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import bigrun_monthly as BM                   # noqa: E402

OUT = "backtest/resultsH1half/freq"
CENSUS_ROWS = "backtest/resultsLampCensus/rows.csv"
CENSUS_CAPS = "backtest/resultsLampCensus/caps.csv"
ADDON_ROWS = "backtest/resultsAddOnLamp2/rows.csv"
V41 = "backtest/resultsV41EV"
REG = "/mnt/c/SynologyDrive/跨線信箱/登錄全文-H1營收見頂確認先賣一半_對v4點1全抱_近年燈號普查_單筆層描述登錄_台股策略線_seq1_sha42d64aee7df4e61b-5174B-20261025-1558.md"
REG_SHA16 = "42d64aee7df4e61b"
HM = 60
TYPES = ("缺貨", "新需求", "政策")
OLD_VARS = ("代表股版", "同業等權版")
LOG = []


def log(s):
    s = f"[{time.strftime('%H:%M:%S')}] {s}"; print(s, flush=True); LOG.append(s)


def reg_sha16():
    import hashlib
    b = open(REG, "rb").read().split(b"\n")
    body = b"\n".join(x for x in b if b"<!-- pw1" not in x)      # pw1 戳記行不入 sha（照登錄檔名 sha 驗）
    return hashlib.sha256(body).hexdigest()[:16]


# ═════════════ 月營收與 S ═════════════
def load_S():
    sha, DN, MD = RT.ensure_data(V.PIN)
    L, diag = BM.load_rev_pit(MD)
    L = L[L["stock_id"].astype(str).str.fullmatch(r"\d{4}")].copy()
    return L, diag, MD


def s_series(L, sid):
    """回 (S: Series[Period→float], rev 期別範圍)；S_m 照 F2。"""
    d = L[L["stock_id"] == sid]
    if d.empty:
        return pd.Series(dtype=float), None
    d = d.drop_duplicates("period", keep="last").set_index("period")
    pr = pd.period_range(d.index.min(), d.index.max(), freq="M")
    rev = d["rev"].reindex(pr.astype(str)).astype(float).values
    ly = d["ly"].reindex(pr.astype(str)).astype(float).values
    num = pd.Series(rev).rolling(3, min_periods=3).sum().values
    den = pd.Series(ly).rolling(3, min_periods=3).sum().values
    with np.errstate(invalid="ignore", divide="ignore"):
        S = np.where(np.isfinite(num) & np.isfinite(den) & (den > 0), num / np.where(den > 0, den, 1.0) - 1, np.nan)
    return pd.Series(S, index=pr), (str(pr[0]), str(pr[-1]))


# ═════════════ 日曆 ═════════════
class Cal:
    def __init__(self, EN):
        self.EN = EN; self.CAL = EN.CAL; self.CEND = EN.CEND

    def first_td_ge(self, ts):
        k = int(self.CAL.searchsorted(pd.Timestamp(ts)))
        return k if k <= self.CEND else None

    def J(self, m, day=13):
        """m 月營收的判斷日 index：m+1 月 day 日當天或之後第一個交易日；超過面板尾 ⇒ None。"""
        return self.first_td_ge((m + 1).to_timestamp() + pd.Timedelta(days=day - 1))

    def J15(self, m):
        """全線規則（2026-01 期起）：嚴格晚於 m+1 月 15 日的第一個交易日。"""
        return self.first_td_ge((m + 1).to_timestamp() + pd.Timedelta(days=15))

    def E(self, e):
        """F1：進場月＋60 個月的第一個交易日 index；未到 ⇒ None。"""
        ms = (self.CAL[e].to_period("M") + HM).to_timestamp()
        k = self.first_td_ge(ms)
        if k is None or self.CAL[k].to_period("M") != ms.to_period("M"):
            return None, ms
        return k, ms

    def next_open(self, i, k):
        EN = self.EN
        while k is not None and k <= self.CEND and not EN.opened(i, k):
            k += 1
        return k if (k is not None and k <= self.CEND) else None

    def trunc(self, i, e, x):
        """LC.Engine.settle 同式的截斷位置（不讀價格值）：回 (xe, 狀態)。"""
        EN = self.EN
        lastv = int(EN.LASTV[i]); delist = (self.CEND - lastv) >= 5
        bb = np.flatnonzero(EN.BAD[i, e + 1:x + 1])
        if len(bb):
            b = e + 1 + int(bb[0]); return EN.lastvalid_le(i, b - 1), f"壞根截斷 {self.CAL[b].date()}"
        if delist and lastv < x:
            return lastv, "下市結算"
        return EN.lastvalid_le(i, x), ""


# ═════════════ H1 觸發（F4～F7）═════════════
def h1_trigger(S, C: Cal, i, e):
    CAL = C.CAL
    Ek, Ems = C.E(e)
    lim = Ek if Ek is not None else C.CEND + 1            # 可用月須 J(m) < lim（index）
    em = CAL[e].to_period("M")
    m = em - 3
    while True:                                           # m0：J(m) 嚴格晚於進場日
        j = C.J(m)
        if j is None or j > e:
            break
        m += 1
    m0 = m
    months, svals, js = [], [], []
    while True:
        j = C.J(m)
        if j is None or j >= lim:
            break
        months.append(m); js.append(j)
        v = S.get(m, np.nan) if len(S) else np.nan
        svals.append(float(v) if v is not None and np.isfinite(v) else np.nan)
        m += 1
    sv = np.asarray(svals, float)
    out = {"m0": str(m0), "可用月數": len(months), "S空月數": int(np.isnan(sv).sum()) if len(sv) else 0,
           "未到": Ek is None, "E日": str(CAL[Ek].date()) if Ek is not None else f"未到（{Ems.date()}）"}
    x = Ek if Ek is not None else C.CEND
    xe, tst = C.trunc(i, e, x)
    out.update({"截斷": tst, "截斷日": str(CAL[xe].date()) if xe is not None and xe >= 0 else ""})
    runmax = np.full(len(sv), np.nan); pm = np.full(len(sv), -1)
    cur = np.nan; cm = -1
    for k, v in enumerate(sv):
        if np.isfinite(v) and (not np.isfinite(cur) or v > cur):
            cur, cm = v, k
        runmax[k] = cur; pm[k] = cm
    out.update({"P終": float(cur) if np.isfinite(cur) else np.nan, "P終月": str(months[cm]) if cm >= 0 else ""})
    conf = None
    for k in range(3, len(sv)):
        P = runmax[k - 3]
        if not (np.isfinite(P) and P > 0):
            continue
        w = sv[k - 2:k + 1]
        if not np.isfinite(w).all() or not (w < P).all():
            continue
        if w[2] <= P / 2 or w[2] <= 0:
            conf = (k, P, int(pm[k - 3])); break
    # 緊接版（描述欄，裁定 seq475）：確認窗須是 P 所在月之後緊接的 3 個月（pm[k−3] ＝ k−3）
    imm = False
    for k in range(3, len(sv)):
        P = runmax[k - 3]
        if not (np.isfinite(P) and P > 0) or int(pm[k - 3]) != k - 3:
            continue
        w = sv[k - 2:k + 1]
        if np.isfinite(w).all() and (w < P).all() and (w[2] <= P / 2 or w[2] <= 0):
            s2 = C.next_open(i, js[k])
            imm = bool(s2 is not None and s2 < lim and xe is not None and s2 <= xe); break
    out["緊接版觸發"] = imm
    if len(sv) == 0 or np.isnan(sv).all():
        out["結果"] = "營收全缺"; return out
    if conf is None:
        if not (np.isfinite(cur) and cur > 0):
            out["結果"] = "P≤0未觸發"
        else:
            out["結果"] = "到E未確認" if Ek is not None else "未到E、末日前未確認"
        return out
    k, P, kp = conf
    mc = months[k]; w = sv[k - 2:k + 1]
    s = C.next_open(i, js[k])
    out.update({"P": float(P), "P月": str(months[kp]), "確認月": str(mc), "S1": float(w[0]), "S2": float(w[1]), "S3": float(w[2]),
                "第3月≤0": bool(w[2] <= 0), "第3月≤P/2": bool(w[2] <= P / 2), "J日": str(CAL[js[k]].date()),
                "確認距m0月": int((mc - m0).n)})
    if mc >= pd.Period("2026-01", "M"):
        j15 = C.J15(mc)
        out["15日規則改日"] = str(CAL[j15].date()) if j15 is not None else "面板尾之後"
    if s is None or s >= lim:
        out["結果"] = "到E未確認" if Ek is not None else "未到E、末日前未確認"
        out["註"] = "確認月已出、但賣出日落在 E／面板尾之後"
        return out
    if xe is None or s > xe:
        out.update({"結果": "觸發但已先結算", "賣出日": str(CAL[s].date())}); return out
    out.update({"結果": "觸發", "賣出日": str(CAL[s].date()), "賣出順延日": int(s - js[k]), "賣出idx": int(s),
                "時距月": (CAL[s] - CAL[e]).days / 30.4375})
    return out


# ═════════════ 事件 ═════════════
def census_events(EN, C, L):
    S = LC.load_signals()
    if "待定" in "".join(S.astype(str).values.ravel()):
        raise SystemExit("⛔ 清單出現「待定」字樣，讀法 F0 需重訂")
    cache = {}; rows = []; Scache = {}
    for _, r in S.iterrows():
        base = {"樣本": "普查", "訊號": r["訊號編號"], "版本": r["版本"], "甲": bool(r["甲"]), "乙": bool(r["乙"]), "型": r["型"], "產業": r["產業"],
                "主題": r["主題"], "燈1季": r["燈1季"], "無點名": bool(r["無點名"])}
        if r["無點名"]:
            rows.append({**base, "代號": "", "名稱": "", "入選": False, "下限": "無點名"}); continue
        ym1 = LC.q_last_month(r["燈1季"])
        for sid, nm in LC.codes_of(r):
            v, d, cl, sh, note = V.tw_cap(EN.sha, sid, ym1, [], cache)
            flag = "查無、未剔除" if not np.isfinite(v) else ("過下限" if v >= LC.FLOOR else "市值不足、剔除")
            rec = {**base, "代號": sid, "名稱": nm, "下限": flag, "入選": flag != "市值不足、剔除", "市值(億)": v / 1e8 if np.isfinite(v) else np.nan}
            ent = EN.entry(sid, ym1)
            if ent[0] is None:
                rows.append({**rec, "入選": False, "結果": ent[1]}); continue
            i, e, dl = ent
            rec.update({"進場日": str(EN.CAL[e].date()), "進場順延日": int(dl), "_i": i, "_e": e})
            if sid not in Scache:
                Scache[sid] = s_series(L, sid)
            Sx, rng = Scache[sid]
            rec["營收期別"] = "" if rng is None else f"{rng[0]}～{rng[1]}"
            rows.append({**rec, **h1_trigger(Sx, C, i, e)})
    return pd.DataFrame(rows)


def old31_events(EN, C, L):
    CS = pd.read_csv(os.path.join(V41, "cases_input.csv"), dtype=str, keep_default_na=False)
    CS = CS[CS["市場"] == "TW"]
    if len(CS) != 31:
        raise SystemExit(f"⛔ 台股案數 {len(CS)} ≠ 31")
    MB = pd.read_csv(os.path.join(V41, "members.csv"), dtype={"代號": str})
    MB = MB[(MB["市場"] == "TW") & MB["版"].isin(OLD_VARS) & (MB["入選"].astype(str) == "True")]
    rows = []; Scache = {}
    for _, c in CS.iterrows():
        for var in OLD_VARS:
            for _, m in MB[(MB["id"] == c["id"]) & (MB["版"] == var)].iterrows():
                sid = str(m["代號"]).zfill(4)
                rec = {"樣本": "舊31段", "版": var, "訊號": c["id"], "結果類": c["結果"], "型": c["型"], "產業": c["產業"], "燈亮月": c["燈亮月"],
                       "代號": sid, "名稱": m["名稱"], "入選": True}
                ent = EN.entry(sid, c["燈亮月"])
                if ent[0] is None:
                    rows.append({**rec, "入選": False, "結果": ent[1]}); continue
                i, e, dl = ent
                rec.update({"進場日": str(EN.CAL[e].date()), "進場順延日": int(dl), "_i": i, "_e": e})
                if sid not in Scache:
                    Scache[sid] = s_series(L, sid)
                Sx, rng = Scache[sid]
                rec["營收期別"] = "" if rng is None else f"{rng[0]}～{rng[1]}"
                rows.append({**rec, **h1_trigger(Sx, C, i, e)})
    return pd.DataFrame(rows)


def verify_entries(EV, OD):
    cr = pd.read_csv(CENSUS_ROWS, dtype={"代號": str})
    cr = cr[(cr["段"] == "燈1") & (cr["H"].astype(str) == "末")][["訊號", "代號", "進場日", "入選"]].drop_duplicates(["訊號", "代號"])
    ev = EV[EV["代號"] != ""][["訊號", "代號", "進場日", "入選"]]
    mg = ev.merge(cr, on=["訊號", "代號"], how="outer", suffixes=("", "_LC"), indicator=True)
    bad = mg[(mg["_merge"] != "both") | (mg["進場日"].astype(str) != mg["進場日_LC"].astype(str)) | (mg["入選"].astype(bool) != mg["入選_LC"].astype(bool))]
    if len(bad):
        print(bad.to_string()); raise SystemExit(f"⛔ 普查進場日／入選與 resultsLampCensus 不同 {len(bad)} 筆")
    cp = pd.read_csv(CENSUS_CAPS, dtype={"代號": str})[["訊號", "代號", "判定"]]
    m2 = EV[EV["代號"] != ""][["訊號", "代號", "下限"]].merge(cp, on=["訊號", "代號"], how="outer")
    if (m2["下限"] != m2["判定"]).any():
        raise SystemExit("⛔ 規模下限判定與 resultsLampCensus/caps.csv 不同")
    ar = pd.read_csv(ADDON_ROWS, dtype={"代號": str})
    ar = ar[ar["段"] == "燈1"][["id", "代號", "進場日"]].drop_duplicates(["id", "代號"]).rename(columns={"id": "訊號"})
    od = OD[OD["入選"]][["訊號", "代號", "進場日"]].drop_duplicates(["訊號", "代號"])
    m3 = od.merge(ar, on=["訊號", "代號"], how="outer", suffixes=("", "_A"), indicator=True)
    b3 = m3[(m3["_merge"] != "both") | (m3["進場日"] != m3["進場日_A"])]
    if len(b3):
        print(b3.to_string()); raise SystemExit(f"⛔ 舊 31 段進場日與 resultsAddOnLamp2 不同 {len(b3)} 筆")
    return {"普查進場日逐筆相同": int(len(mg)), "規模判定相同": int(len(m2)), "舊31段進場日逐筆相同": int(len(m3))}


# ═════════════ 統計 ═════════════
def qs(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0, "中位": np.nan, "P25": np.nan, "P75": np.nan, "最小": np.nan, "最大": np.nan}
    return {"n": len(v), "中位": float(np.median(v)), "P25": float(np.percentile(v, 25)), "P75": float(np.percentile(v, 75)),
            "最小": float(v.min()), "最大": float(v.max())}


def block(sub, sigrows=None, qcol="燈1季"):
    """sub＝入選事件列（每檔一列）。"""
    n = len(sub); tr = sub[sub["結果"] == "觸發"]
    rec = {"可交檔次": n, "不同代號": int(sub["代號"].nunique()), "訊號數(進統計)": int(sub["訊號"].nunique()),
           "n_eff(群數)": int(sub[qcol].nunique()) if n else 0, "觸發": len(tr), "觸發比例": len(tr) / n if n else np.nan,
           "觸發者n_eff": int(tr[qcol].nunique()) if len(tr) else 0}
    for k in ("P≤0未觸發", "到E未確認", "未到E、末日前未確認", "觸發但已先結算", "營收全缺"):
        rec[k] = int((sub["結果"] == k).sum())
    rec["走不到確認比例"] = (n - len(tr)) / n if n else np.nan
    rec["緊接版觸發數"] = int(sub["緊接版觸發"].astype(bool).sum()) if n else 0
    rec["未到E件數"] = int(sub["未到"].astype(bool).sum())
    rec["營收有缺件數"] = int((sub["S空月數"].fillna(0) > 0).sum())
    if n:
        g = sub.assign(t=(sub["結果"] == "觸發").astype(float)).groupby("訊號")["t"].mean()
        rec["訊號層觸發比例"] = float(g.mean())
    else:
        rec["訊號層觸發比例"] = np.nan
    t = qs(tr["時距月"].tolist() if len(tr) else [])
    rec.update({f"時距月_{k}": v for k, v in t.items() if k != "n"})
    tm = tr["時距月"] if len(tr) else pd.Series(dtype=float)
    rec.update({"時距≤12月": int((tm <= 12).sum()), "時距12–24月": int(((tm > 12) & (tm <= 24)).sum()),
                "時距24–36月": int(((tm > 24) & (tm <= 36)).sum()), "時距>36月": int((tm > 36).sum())})
    p = qs(tr["P"].tolist() if len(tr) else [])
    rec.update({f"P_{k}": v for k, v in p.items() if k != "n"})
    pa = qs(sub["P終"].where(sub["P終"] > 0).tolist())
    rec["全部件P終>0中位"] = pa["中位"]
    rec["第3月≤0"] = int(tr["第3月≤0"].astype(bool).sum()) if len(tr) else 0
    rec["第3月≤P/2且>0"] = int((tr["第3月≤P/2"].astype(bool) & ~tr["第3月≤0"].astype(bool)).sum()) if len(tr) else 0
    rec["確認距m0月_中位"] = float(tr["確認距m0月"].median()) if len(tr) else np.nan
    rec["賣出15日規則改日件"] = int(tr["15日規則改日"].notna().sum()) if (len(tr) and "15日規則改日" in tr) else 0
    rec["賣出順延>0件"] = int((tr["賣出順延日"].fillna(0) > 0).sum()) if len(tr) else 0
    return rec


def overlap(sub):
    c = sub.groupby("代號")["訊號"].nunique()
    multi = c[c >= 2].index.tolist(); ov = []
    for sid in multi:
        d = sub[sub["代號"] == sid]
        iv = sorted((pd.Timestamp(a), pd.Timestamp(b if not str(b).startswith("未到") else "2099-12-31")) for a, b in zip(d["進場日"], d["E日"]))
        if any(iv[k + 1][0] < iv[k][1] for k in range(len(iv) - 1)):
            ov.append(sid)
    return len(multi), len(ov), "／".join(multi)


def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    s16 = reg_sha16()
    if s16 != REG_SHA16:
        raise SystemExit(f"⛔ 登錄 sha {s16} ≠ {REG_SHA16}")
    log(f"[登錄] sha16 {s16} 相符（不含 pw1 行）")
    EN = LC.Engine(); C = Cal(EN)
    log(f"[面板] sha {EN.sha[:12]}｜面板尾 {EN.CAL[EN.CEND].date()}")
    L, diag, MD = load_S()
    log(f"[營收] revpit {MD}｜{len(L)} 列｜revenue_hist {diag['revenue_hist 期別']}｜每日版 {len(diag['每日版期別'])} 期")
    EV = census_events(EN, C, L)
    OD = old31_events(EN, C, L)
    chk = verify_entries(EV, OD)
    log(f"[進場驗證] {chk}")
    keep = ["樣本", "訊號", "版本", "版", "甲", "乙", "型", "產業", "主題", "燈1季", "燈亮月", "結果類", "無點名", "代號", "名稱", "下限", "市值(億)", "入選",
            "進場日", "進場順延日", "E日", "未到", "截斷", "截斷日", "營收期別", "m0", "可用月數", "S空月數", "P終", "P終月", "結果", "P", "P月", "確認月",
            "S1", "S2", "S3", "第3月≤0", "第3月≤P/2", "J日", "確認距m0月", "賣出日", "賣出順延日", "時距月", "15日規則改日", "緊接版觸發", "註"]
    ALL = pd.concat([EV, OD], ignore_index=True)
    ALL.reindex(columns=keep).to_csv(os.path.join(OUT, "events.csv"), index=False, encoding="utf-8-sig")
    FQ = []
    S = LC.load_signals()
    for ver in ("甲", "乙"):
        sig = S[S[ver]]
        evv = EV[EV[ver]]
        inn = evv[evv["入選"] & evv["代號"].ne("")]
        for ty in ("全部",) + TYPES:
            sg_ = sig if ty == "全部" else sig[sig["型"] == ty]
            ev_ = evv if ty == "全部" else evv[evv["型"] == ty]
            sub = inn if ty == "全部" else inn[inn["型"] == ty]
            hc = sg_[~sg_["無點名"]]
            cut = ev_[ev_["下限"] == "市值不足、剔除"]
            allcut = [s for s in hc["訊號編號"] if not len(sub[sub["訊號"] == s])]
            m, ov, ml = overlap(sub)
            FQ.append({"樣本": "普查", "組": ver, "型": ty, "訊號列": len(sg_), "無點名": int(sg_["無點名"].sum()), "待定": 0,
                       "規模剔除檔次": len(cut), "規模全剔除訊號": "、".join(allcut), "燈1季數(全部訊號列)": int(sg_["燈1季"].nunique()),
                       **block(sub), "重疊代號(≥2訊號)": m, "其中持有窗重疊": ov, "重疊代號": ml})
    for var in OLD_VARS:
        od = OD[(OD["版"] == var) & OD["入選"]]
        for cls in ("全部", "大漲", "失敗"):
            for ty in ("全部",) + TYPES + ("谷底",):
                sub = od if cls == "全部" else od[od["結果類"] == cls]
                sub = sub if ty == "全部" else sub[sub["型"] == ty]
                if not len(sub) and ty != "全部":
                    continue
                m, ov, ml = overlap(sub)
                FQ.append({"樣本": "舊31段", "組": var, "型": ty, "結果類": cls, **block(sub, qcol="訊號"), "重疊代號(≥2訊號)": m, "其中持有窗重疊": ov,
                           "重疊代號": ml})
    FQ = pd.DataFrame(FQ); FQ.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    meta = {"登錄": os.path.basename(REG), "登錄sha16": s16, "面板sha": EN.sha, "面板尾": str(EN.CAL[EN.CEND].date()), "revpit": MD,
            "營收診斷": {k: (v if k != "每日版期別" else f"{v[0]}～{v[-1]}（{len(v)} 期）") for k, v in diag.items()}, "進場驗證": chk}
    write_md(FQ, EV, OD, meta)
    json.dump({**meta, "freq": FQ.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)},
              open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def pc(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"


def f1(v, pct=False):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v * 100:+.0f}%" if pct else f"{v:.1f}"


def write_md(FQ, EV, OD, meta):
    md = ["# H1「營收見頂確認、先賣一半」seq1 頻率表（⛔ 不含任何報酬）", "",
          f"- 登錄 sha {meta['登錄sha16']}；裁定 seq474 §六：描述、不判、不計 N。面板 sha {meta['面板sha'][:12]}（尾 {meta['面板尾']}）；月營收 load_rev_pit（公告當時口徑）。",
          "- 讀法見 main.json「讀法」（F0～F10，★＝執行者定、看數字前寫死）。普查燈 1 季 15 季 ⇒ n_eff ≤ 15 < 24，依構造還沒測。", "",
          "## 普查（主）", "",
          "| 組 | 型 | 訊號列 | 無點名 | 待定 | 規模剔除檔次 | 進統計訊號 | 可交檔次 | 燈1季 n_eff | 觸發（緊接版） | 觸發比例（檔次／訊號層） | 觸發者 n_eff | 未到 E | 營收有缺 | 重疊代號（持有窗重疊） |",
          "|" + "---|" * 15]
    for _, r in FQ[FQ["樣本"] == "普查"].iterrows():
        md.append(f"| {r['組']} | {r['型']} | {int(r['訊號列'])} | {int(r['無點名'])} | {int(r['待定'])} | {int(r['規模剔除檔次'])} | {r['訊號數(進統計)']} | {r['可交檔次']} | "
                  f"{r['n_eff(群數)']} | {r['觸發']}（{r['緊接版觸發數']}） | {pc(r['觸發比例'])}／{pc(r['訊號層觸發比例'])} | {r['觸發者n_eff']} | {r['未到E件數']} | {r['營收有缺件數']} | "
                  f"{r['重疊代號(≥2訊號)']}（{r['其中持有窗重疊']}） |")
    md += ["", "### 觸發時距、P、確認第 3 個月、走不到確認", "",
           "| 組 | 型 | 觸發 | 時距月 中位［P25～P75］ | ≤12／12–24／24–36／>36 月 | P 中位（觸發者） | 第3月 ≤0／≤P÷2且>0 | 走不到確認 | P≤0／到E未確認／未到E末日前未確認／已先結算／營收全缺 | 15 日規則改日 |",
           "|" + "---|" * 10]
    for _, r in FQ[FQ["樣本"] == "普查"].iterrows():
        md.append(f"| {r['組']} | {r['型']} | {r['觸發']} | {f1(r['時距月_中位'])}［{f1(r['時距月_P25'])}～{f1(r['時距月_P75'])}］ | "
                  f"{r['時距≤12月']}／{r['時距12–24月']}／{r['時距24–36月']}／{r['時距>36月']} | {f1(r['P_中位'], True)} | {r['第3月≤0']}／{r['第3月≤P/2且>0']} | "
                  f"{pc(r['走不到確認比例'])} | {r['P≤0未觸發']}／{r['到E未確認']}／{r['未到E、末日前未確認']}／{r['觸發但已先結算']}／{r['營收全缺']} | {r['賣出15日規則改日件']} |")
    md += ["", "## 舊 31 段（只描述；⚠ H1 是看過其中 3 個輸家後才挑的）", "",
           "| 版 | 結果類 | 型 | 案數 | 可交檔次 | 觸發（緊接版） | 觸發比例 | 時距月 中位 | P 中位 | 第3月 ≤0／≤P÷2且>0 | P≤0／到E未確認／未到／已先結算／營收全缺 |", "|" + "---|" * 11]
    for _, r in FQ[FQ["樣本"] == "舊31段"].iterrows():
        md.append(f"| {r['組']} | {r['結果類']} | {r['型']} | {r['訊號數(進統計)']} | {r['可交檔次']} | {r['觸發']}（{r['緊接版觸發數']}） | {pc(r['觸發比例'])} | {f1(r['時距月_中位'])} | "
                  f"{f1(r['P_中位'], True)} | {r['第3月≤0']}／{r['第3月≤P/2且>0']} | {r['P≤0未觸發']}／{r['到E未確認']}／{r['未到E、末日前未確認']}／{r['觸發但已先結算']}／{r['營收全缺']} |")
    ins = EV[EV["入選"] & EV["代號"].ne("")]
    md += ["", "## 名單與註記", "",
           "- 規模剔除：" + "；".join(f"{r.訊號} {r.名稱}（{r.市值:.0f} 億）" for r in EV[EV["下限"] == "市值不足、剔除"].rename(columns={"市值(億)": "市值"}).itertuples()),
           "- 無點名：" + "、".join(f"{r.訊號}（{r.版本}）" for r in EV[EV["無點名"]].itertuples()),
           f"- 進場驗證：{meta['進場驗證']}",
           "- 營收有缺：" + ("；".join(f"{r.訊號} {r.代號}（缺 {int(r.S空月數)}／{int(r.可用月數)} 月）" for r in pd.concat([ins, OD[OD['入選']]]).itertuples()
                                    if (r.S空月數 or 0) > 0) or "無"),
           "- 觸發但已先結算：" + ("；".join(f"{r.樣本} {r.訊號} {r.代號}（{r.截斷}）" for r in pd.concat([ins, OD[OD['入選']]]).itertuples()
                                       if r.結果 == "觸發但已先結算") or "無"),
           "- 截斷（壞根／下市，E 或末日前）：" + ("；".join(f"{r.樣本} {r.訊號} {r.代號}（{r.截斷}）" for r in pd.concat([ins, OD[OD['入選']]]).itertuples()
                                              if isinstance(r.截斷, str) and r.截斷) or "無"),
           "- ⛔ 兩版（H1、全抱）都沒套 v4.1 新聞出場 ①～⑤。本表不含任何報酬。"]
    open(os.path.join(OUT, "freq.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

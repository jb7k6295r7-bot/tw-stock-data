# -*- coding: utf-8 -*-
"""照「接近燈」買賣的描述表（台股策略線 20261023-0101 §二；描述、⛔ 不判定、不計 N、不改任何規則）——回測線計算子代理。
⚠ 燈號日期是看過大漲之後從新聞挑的、樣本都是贏家 ⇒ 只描述，⛔ 不能當規則證據、不改任何規則。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices）、researchShortageExit（seam_open）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampTrade [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampTrade_check
輸入：backtest/resultsLampTrade/lamps_input.csv（附件原檔複本，31 列）
輸出 backtest/resultsLampTrade/：table.csv（每檔×進場燈×出場欄）、summary.md、main.json、run.log

═══ 讀法（Q 標；★＝執行者定）═══
 Q1 價格 ＝ 本線共用合併面板（researchRevTurn_freq.prices 原式：早年 eotc 2004-02～2014-12 ＋ 主 rerun17 H2D 2015-01～2026-09-24，
    還原含息收盤 C、還原開盤 O；主世界開盤乘接縫倍數 ＝ researchShortageExit.seam_open 原式）；資料 sha ＝ PIN（同 rtfwork 快取）。
    壞根 BAD ＝ 面板原定義（缺口 ≥5 日 seq335 ∪ 價格斷點（減資、面額變更等）∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2 ∪ 接縫）。
 Q2 燈號日 ＝ 燈號月份的下一個月第一個交易日（合併日曆）；該日無成交（TRD 假、開盤無值）⇒ 順延到下一個有成交的開盤（順延日數照報）。
    進場價 P0 ＝ 進場日還原開盤；燈號出場（E1～E3）出場價 ＝ 出場日還原開盤（同法順延）。
 Q3 抱滿 H（250／625）★ ＝ 進場日算第 1 個交易日、第 H 個交易日（合併日曆位置 e＋H−1，同 researchLong3 抱 1 年 e＋249）的還原收盤；
    該位置無有效 K 棒 ⇒ 該位置當天或之前最後一根有效收盤。
 Q4 留空：燈號 NA ⇒「燈NA」；出場日 ≤ 進場日 ⇒「出場不晚於進場」；出場日（或 e＋H−1）超出資料尾 ⇒「未到」（★ 留空、不結算到資料尾）。
 Q5 跨壞根（(e, 出場日] 有壞根）★ ⇒ 結算在第一個壞根前一根有效 K 棒的還原收盤，格標「⚠壞根截斷」並報壞根日期與截斷日；
    下市（最後有效 K 棒 ＜ 出場位置、距資料尾 ≥ 5 日）⇒ 最後有效收盤結算、標「下市結算」。
 Q5′ 接續版（參考、另欄）：⚠ 格的每個壞根 b 若當天是 data/adj 的 reduce（減資退還股款）或 parvalue（面額變更）事件 ⇒
    pb→b 的倍數 ＝ 原始收盤[b] ÷ ref_price × pre_close ÷ 原始收盤[pb]（等同退還股款再投入），其他段照面板還原價；非這兩類 ⇒ 接續欄留空。
 Q6 R ＝ 出場價 ÷ P0 − 1 − 0.4425%（扣一次賣出成本：手續費 0.1425%＋證交稅 0.3%，本線慣例；不計滑價）。
 Q7 大盤 ＝ data/history/market_tri.csv（報酬指數，只有收盤）。★ 開盤進出 ⇒ 用進／出場日「前一交易日」收盤當基準（最接近開盤）；
    收盤出場（抱滿、截斷、下市）⇒ 用該日收盤；某日無值 ⇒ 該日或之前最後一個值。大盤不扣成本。超額 ＝ R − 大盤報酬。
 Q8 天花板（參考、不扣成本）：① 格內 ＝ 進場日到出場前（開盤出場 ⇒ 到出場前一日；收盤出場 ⇒ 含出場日）最高還原收盤 ÷ P0 − 1；
    ② 到資料尾 ＝ 進場日到資料尾（遇壞根 ⇒ 到第一個壞根前一根，標⚠）最高還原收盤 ÷ P0 − 1（每個進場燈一個值，該列各格同值）。
 Q9 1503、1513 高點月 NA ⇒ 2021-05～2024-12 區間最高還原收盤所在月補，標「回測補」。同一檔在兩段（2327、2492）分開列。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  ensure_data、prices
from backtest import researchShortageExit as SE             # noqa: E402  seam_open
from backtest import researchTopSell_freq as TS             # noqa: E402  raw_close

OUT = "backtest/resultsLampTrade"
INP = os.path.join(OUT, "lamps_input.csv")
PIN = "9b0e9882572c"                                         # rtfwork 已有快取的最新資料版
COST = 0.004425
HOLDS = (250, 625)
ENTRY = ["L1", "L2", "L3"]
EXITS = ["E1", "E2", "E3", "抱250", "抱625"]
WARN = "燈號日期是看過大漲之後從新聞挑的、樣本都是贏家 ⇒ 只描述，⛔ 不能當規則證據、不改任何規則"
LOG = RT.LOG
log = RT.log


def load_tri(sha):
    t = subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout
    T = pd.read_csv(io.BytesIO(t))
    T["date"] = pd.to_datetime(T["date"]); T = T.dropna().drop_duplicates("date").sort_values("date").set_index("date")["close"]
    return T


def tri_at(T, d):
    k = int(T.index.searchsorted(pd.Timestamp(d), "right")) - 1
    if k < 0:
        raise SystemExit(f"⛔ 大盤指數無 {d} 以前的值")
    return float(T.iloc[k]), (T.index[k] != pd.Timestamp(d))


def month_first(CAL, ym):
    """燈號月 ym ⇒ 下一個月第一個交易日的日曆位置（可能 ＝ len(CAL)）。"""
    p = pd.Period(ym, "M") + 1
    return int(CAL.searchsorted(p.to_timestamp()))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    sha, DN, MD = RT.ensure_data(PIN)
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix, C, BAD, VP, LASTV, TRD = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"], PX["TRD"]
    CEND = len(CAL) - 1
    O, nseam = SE.seam_open(PX)
    log(f"[Q1] sha {sha[:12]}｜日曆 {CAL[0].date()}～{CAL[CEND].date()}｜接縫開盤倍數 {nseam} 檔")
    T = load_tri(sha)
    log(f"[Q7] 大盤報酬指數 {T.index[0].date()}～{T.index[-1].date()}")
    LP = pd.read_csv(INP, dtype=str, keep_default_na=False)
    if len(LP) != 31:
        raise SystemExit(f"⛔ 附件列數 {len(LP)} ≠ 31")
    anomalies = []

    def opened(i, p):
        return bool(TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p]))

    def open_pos(i, ym):
        """回 (位置, 順延日數, 狀態)；狀態 ok／未到／無成交到尾。"""
        p0 = month_first(CAL, ym)
        if p0 > CEND:
            return -1, 0, "未到"
        p = p0
        while p <= CEND and not opened(i, p):
            p += 1
        if p > CEND:
            return -1, 0, "未到(順延到資料尾仍無成交)"
        return p, p - p0, "ok"

    def lastvalid_le(i, x):
        vp = VP[i]; k = int(np.searchsorted(vp, x, "right")) - 1
        return int(vp[k]) if k >= 0 else -1

    def settle(i, e, x, kind):
        """持有 e→x：kind＝open（x 開盤賣）／close（x 收盤）。回 dict。"""
        bb = np.flatnonzero(BAD[i, e + 1:x + 1])
        lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
        st = "完整"; bad_d = ""
        if len(bb):
            b = e + 1 + int(bb[0]); bad_d = str(CAL[b].date())
            xe = lastvalid_le(i, b - 1); kind = "close"; st = "⚠壞根截斷"
        elif delist and lastv < x:
            xe = lastv; kind = "close"; st = "下市結算"
        elif kind == "close":
            xe = lastvalid_le(i, x)
        else:
            xe = x
        px = O[i, xe] if kind == "open" else C[i, xe]
        hi_end = xe - 1 if kind == "open" else xe
        seg = C[i, e:hi_end + 1]; seg = seg[np.isfinite(seg)]
        tri_d = CAL[xe - 1] if kind == "open" else CAL[xe]
        return {"出場日": str(CAL[xe].date()), "出場價型": ("開盤" if kind == "open" else "收盤"), "狀態": st, "壞根日": bad_d,
                "px": float(px), "hi": float(seg.max()) if len(seg) else np.nan, "tri_d": tri_d}

    def ceil_tail(i, e):
        bb = np.flatnonzero(BAD[i, e + 1:CEND + 1])
        end = lastvalid_le(i, e + int(bb[0])) if len(bb) else int(LASTV[i])
        seg = C[i, e:end + 1]; seg = seg[np.isfinite(seg)]
        return float(seg.max()), ("⚠截到壞根前 " + str(CAL[end].date()) if len(bb) else ""), str(CAL[end].date())

    ADJ = {}

    def adj_events(sid):
        if sid not in ADJ:
            t = subprocess.run(["git", "show", f"{sha}:data/adj/{sid}.csv"], capture_output=True)
            if t.returncode != 0:
                ADJ[sid] = {}
            else:
                A = pd.read_csv(io.BytesIO(t.stdout), dtype=str)
                ADJ[sid] = {pd.Timestamp(r["date"]): r for _, r in A.iterrows() if r["event"] in ("reduce", "parvalue")}
        return ADJ[sid]

    def bridge_mult(i, sid, e, end):
        """Q5′ 接續版：(e, end] 內每個壞根 b 若當天是 data/adj 的減資（reduce）或面額變更（parvalue）事件 ⇒ 以
        原始收盤[b] ÷ ref_price × pre_close ÷ 原始收盤[pb] 接起 pb→b（pb ＝ b 前一根有效 K 棒）；任一壞根不是這兩類 ⇒ 回 None。
        回 K：長度 end−e+1 的倍數陣列，使 C[p]×K[p−e]／P0 為接續後的還原價比（同一段內 K 不變）。"""
        K = np.ones(end - e + 1); k = 1.0; info = []
        data = PX["main_data"] if e >= PX["NE"] else PX["early_data"]
        for b in (e + 1 + np.flatnonzero(BAD[i, e + 1:end + 1])):
            b = int(b); ev = adj_events(sid).get(CAL[b])
            pb = lastvalid_le(i, b - 1)
            if ev is None or pb < e or not np.isfinite(C[i, b]):
                return None, f"壞根 {CAL[b].date()} 非減資／面額變更事件"
            rb = TS.raw_close(PX["main_data"] if b >= PX["NE"] else PX["early_data"], sid, CAL[b])
            rp = TS.raw_close(PX["main_data"] if pb >= PX["NE"] else PX["early_data"], sid, CAL[pb])
            g = rb / float(ev["ref_price"]) * float(ev["pre_close"]) / rp
            if not np.isfinite(g) or g <= 0:
                return None, f"壞根 {CAL[b].date()} 接續倍數不可算"
            k = k * (C[i, pb] * g) / C[i, b]
            K[b - e:] = k
            info.append(f"{CAL[b].date()} {ev['event']}（pb {CAL[pb].date()}，pre_close {ev['pre_close']}／原始收 {rp:g}，ref {ev['ref_price']}，原始收 {rb:g}）")
        return K, "；".join(info)

    def settle_bridge(i, sid, e, x, kind, P0):
        """接續版結算：x 的開盤或收盤（收盤無效 ⇒ 前一根有效）；回 (R, 天花板, 註) 或 (nan, nan, 原因)。"""
        lastv = int(LASTV[i])
        if (CEND - lastv) >= 5 and lastv < x:
            x = lastv; kind = "close"
        K, note = bridge_mult(i, sid, e, x)
        if K is None:
            return np.nan, np.nan, note
        if kind == "open":
            px = O[i, x] * K[x - e]; hi_end = x - 1
        else:
            xe = lastvalid_le(i, x); px = C[i, xe] * K[xe - e]; hi_end = xe
        seg = C[i, e:hi_end + 1] * K[:hi_end - e + 1]; seg = seg[np.isfinite(seg)]
        return float(px / P0 - 1 - COST), float(seg.max() / P0 - 1), note

    rows = []
    hi_fill = {}
    for r in LP.itertuples(index=False):
        rd = r._asdict()
        sid = rd["代號"].strip(); seg_ = rd["段"]
        if sid not in ix:
            anomalies.append(f"{seg_} {sid} 面板查無"); continue
        i = ix[sid]
        hm = rd["高點月"]; hm_note = ""
        if hm == "NA" and sid in ("1503", "1513"):
            a_, b_ = int(CAL.searchsorted(pd.Timestamp("2021-05-01"))), int(CAL.searchsorted(pd.Timestamp("2025-01-01"))) - 1
            w = C[i, a_:b_ + 1]
            if np.any(BAD[i, a_ + 1:b_ + 1]):
                anomalies.append(f"{sid} 2021-05～2024-12 區間內有壞根（高點月補值照取最高還原收盤）")
            k = int(np.nanargmax(w)); hm = str(CAL[a_ + k].to_period("M")); hm_note = "回測補"
            hi_fill[sid] = {"高點月": hm, "最高還原收盤日": str(CAL[a_ + k].date()), "還原收盤": float(w[k])}
        for L in ENTRY:
            base = {"段": seg_, "型態": rd["型態"], "代號": sid, "高點月": hm, "高點月註": hm_note, "備註": rd["備註"], "進場燈": L, "燈號月": rd[L]}
            if rd[L] == "NA":
                for X in EXITS:
                    rows.append({**base, "出場欄": X, "出場燈號月": (rd[X] if X in rd else ""), "留空原因": "進場燈NA"})
                continue
            e, de, ste = open_pos(i, rd[L])
            if ste != "ok":
                for X in EXITS:
                    rows.append({**base, "出場欄": X, "出場燈號月": (rd[X] if X in rd else ""), "留空原因": f"進場{ste}"})
                continue
            if BAD[i, e] and e > 0:
                anomalies.append(f"{seg_} {sid} {L} 進場日 {CAL[e].date()} 本身是壞根（壞在進場前一根與進場日之間，不影響持有段）")
            P0 = float(O[i, e]); tri0, tri0f = tri_at(T, CAL[e - 1])
            if de > 5:
                v0 = VP[i][0] if len(VP[i]) else -1
                anomalies.append(f"{seg_} {sid} {L} 燈號 {rd[L]} ⇒ 進場順延 {de} 個交易日到 {CAL[e].date()}"
                                 + ("（＝ 面板該檔第一根有效 K 棒；之前查無價）" if v0 == e else ""))
            hit, hnote, hend = ceil_tail(i, e)
            eb = {**base, "進場日": str(CAL[e].date()), "進場順延日": de, "進場價(還原開盤)": P0, "進場開盤鎖漲停": bool(PX["UPL"][i, e]),
                  "天花板_到資料尾": hit / P0 - 1, "天花板_到資料尾註": hnote, "天花板_到資料尾止日": hend}
            if hnote:
                _, Hb, nb = settle_bridge(i, sid, e, int(LASTV[i]), "close", P0)
                eb["接續天花板_到資料尾"] = Hb
                if not np.isfinite(Hb):
                    eb["接續註"] = nb
            for X in EXITS:
                row = {**eb, "出場欄": X}
                if X.startswith("E"):
                    row["出場燈號月"] = rd[X]
                    if rd[X] == "NA":
                        row["留空原因"] = "出場燈NA"; rows.append(row); continue
                    x, dx, stx = open_pos(i, rd[X])
                    if stx != "ok":
                        row["留空原因"] = stx; rows.append(row); continue
                    if x <= e:
                        row["留空原因"] = "出場不晚於進場"; row["出場日(未用)"] = str(CAL[x].date()); rows.append(row); continue
                    row["出場順延日"] = dx
                    s = settle(i, e, x, "open")
                else:
                    H = int(X[1:]); row["出場燈號月"] = ""
                    x = e + H - 1
                    if x > CEND:
                        row["留空原因"] = "未到"; rows.append(row); continue
                    s = settle(i, e, x, "close")
                tri1, tri1f = tri_at(T, s["tri_d"])
                R = s["px"] / P0 - 1 - COST; M = tri1 / tri0 - 1
                row.update({"出場日": s["出場日"], "出場價型": s["出場價型"], "出場價(還原)": s["px"], "狀態": s["狀態"], "壞根日": s["壞根日"],
                            "持有交易日": int(CAL.searchsorted(pd.Timestamp(s["出場日"])) - e), "報酬R(扣0.4425%)": R, "大盤報酬": M, "超額": R - M,
                            "大盤基準日": f"{CAL[e - 1].date()}→{pd.Timestamp(s['tri_d']).date()}", "大盤取前值": bool(tri0f or tri1f),
                            "天花板_格內": s["hi"] / P0 - 1, "留空原因": ""})
                if s["狀態"] == "⚠壞根截斷":
                    xb = x
                    Rb, Hb, nb = settle_bridge(i, sid, e, xb, ("open" if X.startswith("E") else "close"), P0)
                    if np.isfinite(Rb):
                        lastv = int(LASTV[i]); xq = lastv if ((CEND - lastv) >= 5 and lastv < xb) else xb
                        tq = CAL[xq - 1] if (X.startswith("E") and xq == xb) else CAL[lastvalid_le(i, xq)]
                        Mb = tri_at(T, tq)[0] / tri0 - 1
                        row.update({"接續R(參考)": Rb, "接續大盤": Mb, "接續超額(參考)": Rb - Mb, "接續天花板_格內": Hb,
                                    "接續出場日": str(CAL[xq].date()) if X.startswith("E") and xq == xb else str(CAL[lastvalid_le(i, xq)].date())})
                    row["接續註"] = nb
                rows.append(row)
    TB = pd.DataFrame(rows)
    cols = ["段", "型態", "代號", "進場燈", "燈號月", "出場欄", "出場燈號月", "留空原因", "進場日", "進場順延日", "進場開盤鎖漲停", "出場日", "出場順延日", "出場價型",
            "持有交易日", "狀態", "壞根日", "進場價(還原開盤)", "出場價(還原)", "報酬R(扣0.4425%)", "大盤報酬", "超額", "大盤基準日", "大盤取前值",
            "天花板_格內", "天花板_到資料尾", "天花板_到資料尾註", "天花板_到資料尾止日", "接續R(參考)", "接續大盤", "接續超額(參考)", "接續天花板_格內",
            "接續出場日", "接續天花板_到資料尾", "接續註", "出場日(未用)", "高點月", "高點月註", "備註"]
    TB = TB.reindex(columns=cols)
    TB.to_csv(os.path.join(OUT, "table.csv"), index=False, encoding="utf-8-sig")
    # ── 摘要
    ok = TB[TB["留空原因"] == ""]
    blank = TB[TB["留空原因"] != ""]
    bc = blank["留空原因"].value_counts().to_dict()
    ST = []
    for L in ENTRY:
        for X in EXITS:
            d = ok[(ok["進場燈"] == L) & (ok["出場欄"] == X)]
            n = len(d)
            ST.append({"進場燈": L, "出場欄": X, "n": n, "⚠截斷": int((d["狀態"] == "⚠壞根截斷").sum()),
                       "R中位": d["報酬R(扣0.4425%)"].median() if n else np.nan, "R平均": d["報酬R(扣0.4425%)"].mean() if n else np.nan,
                       "大盤中位": d["大盤報酬"].median() if n else np.nan, "超額中位": d["超額"].median() if n else np.nan,
                       "超額平均": d["超額"].mean() if n else np.nan, "超額>0": int((d["超額"] > 0).sum()),
                       "天花板格內中位": d["天花板_格內"].median() if n else np.nan, "持有日中位": d["持有交易日"].median() if n else np.nan})
            rb = d["接續R(參考)"].where(d["狀態"] == "⚠壞根截斷", d["報酬R(扣0.4425%)"])
            xb = d["接續超額(參考)"].where(d["狀態"] == "⚠壞根截斷", d["超額"])
            ST[-1].update({"接續版R中位": rb.median() if n else np.nan, "接續版超額中位": xb.median() if n else np.nan,
                           "接續版超額平均": xb.mean() if n else np.nan, "接續版超額>0": int((xb > 0).sum())})
    ST = pd.DataFrame(ST)
    ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")

    def pc(v):
        return "—" if not np.isfinite(v) else f"{v * 100:+.0f}%"

    md = [f"# 照「接近燈」買賣描述表（台股策略線 20261023-0101 §二）", "", f"> ⚠ **{WARN}**", "",
          f"- 描述、⛔ 不判定、不計 N。資料 sha {sha[:12]}；價格面板 {CAL[0].date()}～{CAL[CEND].date()}（資料尾）；大盤報酬指數 data/history/market_tri.csv。",
          "- 進場＝燈號月下一個月第一個交易日還原開盤；E1～E3 出場同法（開盤）；抱 250／625 ＝ 進場日算第 1 日、第 H 個交易日還原收盤。無成交 ⇒ 順延到下一個有成交開盤。",
          f"- 報酬 R ＝ 還原含息、扣一次賣出成本 0.4425%（手續費 0.1425%＋證交稅 0.3%，本線慣例）；大盤不扣成本；超額 ＝ R − 大盤。大盤以進出場前一交易日收盤（開盤進出）或當日收盤（收盤出場）為基準。",
          "- 留空：燈 NA、出場不晚於進場、出場日超出資料尾（標「未到」，⛔ 不結算到資料尾）。跨壞根（缺口 ≥5 日、減資／面額變更等斷點，research11 規則）⇒ 結算在第一個壞根前一根收盤、標 ⚠壞根截斷。",
          "- 接續版（參考）：⚠ 格的壞根若是 data/adj 的減資（退還股款）或面額變更事件，以「原始收盤 ÷ 參考價」把壞根前後接起（等同把退還股款再投入），另給接續 R／超額；統計表右三欄為「⚠ 格換成接續值」的中位／平均。",
          "- 天花板（參考、不扣成本）：格內 ＝ 進場到出場前最高還原收盤；到資料尾 ＝ 進場到資料尾最高還原收盤。",
          "- 1503、1513 高點月以 2021-05～2024-12 區間最高還原收盤所在月補（回測補）。2327、2492 兩段分開列。", "",
          f"## 留空格：{len(blank)}／{len(TB)}", "", "｜".join(f"{k} {v}" for k, v in bc.items()), "",
          "## 各進場燈 × 出場欄（中位／平均；n＝可算格數）", "",
          "| 進場燈 | 出場欄 | n | R 中位 | R 平均 | 大盤中位 | 超額中位 | 超額平均 | 超額>0 | 天花板格內中位 | 持有日中位 | ⚠截斷 | 接續版 R 中位 | 接續版超額中位 | 接續版超額平均 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in ST.to_dict("records"):
        md.append(f"| {s['進場燈']} | {s['出場欄']} | {s['n']} | {pc(s['R中位'])} | {pc(s['R平均'])} | {pc(s['大盤中位'])} | {pc(s['超額中位'])} | {pc(s['超額平均'])} | "
                  f"{s['超額>0']}/{s['n']} | {pc(s['天花板格內中位'])} | {'—' if not np.isfinite(s['持有日中位']) else int(s['持有日中位'])} | {s['⚠截斷']} | {pc(s['接續版R中位'])} | {pc(s['接續版超額中位'])} | {pc(s['接續版超額平均'])} |")
    md += ["", "## 每段一行（各檔：L1／L2／L3 進場 → E1 出場的超額；→ 抱 250 的超額；L2 進場到資料尾天花板）", ""]
    for sg in LP["段"].drop_duplicates():
        parts = []
        for sid in LP[LP["段"] == sg]["代號"]:
            d = TB[(TB["段"] == sg) & (TB["代號"] == sid)]
            def cell(L, X):
                q = d[(d["進場燈"] == L) & (d["出場欄"] == X)]
                if not len(q):
                    return "?"
                q = q.iloc[0]
                return ("空" if q["留空原因"] else pc(q["超額"]) + ("⚠" if q["狀態"] == "⚠壞根截斷" else ""))
            l2 = d[(d["進場燈"] == "L2")]
            ct = pc(l2["天花板_到資料尾"].iloc[0]) if len(l2) and np.isfinite(l2["天花板_到資料尾"].iloc[0]) else "—"
            hm = d["高點月"].iloc[0] + ("（回測補）" if d["高點月註"].iloc[0] == "回測補" else "")
            parts.append(f"{sid}：→E1 {'/'.join(cell(L, 'E1') for L in ENTRY)}；→抱250 {'/'.join(cell(L, '抱250') for L in ENTRY)}；L2 天花板 {ct}；高點月 {hm}")
        md.append(f"- **{sg}**（{LP[LP['段'] == sg]['型態'].iloc[0]}）｜" + "｜".join(parts))
    md += ["", "（「空」＝該格留空；數字為超額 ＝ 個股 R − 大盤；⚠ ＝ 壞根截斷）", "", "## ⚠ 壞根截斷格（截斷值 → 接續值，參考）", ""]
    W_ = ok[ok["狀態"] == "⚠壞根截斷"]
    for (sg, sid, L), g in W_.groupby(["段", "代號", "進場燈"], sort=False):
        md.append(f"- {sg} {sid} {L}（壞根 {g['壞根日'].iloc[0]}，{g['接續註'].iloc[0] if isinstance(g['接續註'].iloc[0], str) else ''}）：" + "；".join(
            f"{r['出場欄']} R {pc(r['報酬R(扣0.4425%)'])}/超額 {pc(r['超額'])} → 接續 R {pc(r['接續R(參考)'])}/超額 {pc(r['接續超額(參考)'])}（{r['接續出場日']}）"
            for _, r in g.iterrows()))
    md += ["", "## 異常與註", ""]
    md += [f"- {x}" for x in anomalies] or ["- 無"]
    md += [f"- 高點月回測補：{json.dumps(hi_fill, ensure_ascii=False)}",
           f"- 開盤鎖漲停進場（照開盤價算、未順延）：{int(ok['進場開盤鎖漲停'].fillna(False).astype(bool).sum())} 格；進場或出場順延 ≥1 日：進場 {int((TB['進場順延日'].fillna(0) > 0).sum())} 格、出場 {int((TB['出場順延日'].fillna(0) > 0).sum())} 格",
           f"- 資料尾 {CAL[CEND].date()}（面板）；大盤指數到 {T.index[-1].date()}；到資料尾天花板不含 {CAL[CEND].date()} 之後。", "", f"> ⚠ **{WARN}**"]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    MJ = {"性質": "照接近燈買賣描述表（描述、不判定、不計 N）", "警語": WARN, "請求": "台股策略線 20261023-0101 §二", "sha": sha, "資料尾": str(CAL[CEND].date()),
          "接縫開盤倍數檔數": nseam, "格數": len(TB), "可算": len(ok), "留空": bc, "異常": anomalies, "高點月補": hi_fill,
          "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜格 {len(TB)}｜可算 {len(ok)}｜留空 {bc}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

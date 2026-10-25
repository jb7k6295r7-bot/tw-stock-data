# -*- coding: utf-8 -*-
"""近年燈號普查（產業分析線 seq41 §一、seq44；回測 1450 §一）：燈 1 後 12／24 月／到資料末日對大盤超額＋燈 2 加碼 2 份（seq41 §三）
——回測線計算子代理。描述、⛔ 不判定、不計 N、不改任何規則。
⛔ 不 commit、不改既有檔；researchV41EV（tw_engine、tw_cap、tri_at）、researchTopSell_freq（raw_close）只 import；結算、壞根截斷、接續照 researchV41EV.tw_rows 原式抄
   （差別只在：判決目標日可指定「進場＋H 月」「到資料末日」或「指定日」三種）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus_check
輸入：/mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v3_產業分析線-20261025-1610.csv（44 列＝44 個訊號列；複本存 resultsLampCensus/signals_input.csv）
輸出 backtest/resultsLampCensus/：rows.csv（每訊號×每檔×每段）、caps.csv、signals.csv（每訊號一列）、stats.csv、summary.md、main.json、run.log

═══ 讀法（★＝執行者定）═══
 L0 版本：欄「版本」＝甲 ⇒ 只在甲版；乙 ⇒ 只在乙版；兩版 ⇒ 兩版都算（同一列、數字相同）。公司1～3 寫「無點名」⇒ 不算、另報筆數。
    乙版「待定」（SM、國內水泥、PC）本來就不在清單乙版內 ⇒ 不算。
 L1 公司代號 ＝ 公司欄第一個空白前的 4 碼。一個訊號內各檔等權（訊號＝1 個樣本）；另附每檔各算版。
 L2 規模下限 ＝ 燈 1 季最後一個月、該檔最後一個有收盤日的 未還原收盤 × 當日發行股數（researchV41EV.tw_cap，≥2015 讀 data/stocks 的 close、shares）
    ＜ 新台幣 100 億 ⇒ 剔除、列名單；算不出 ⇒「查無、未剔除」。訊號內全部剔除 ⇒ 該訊號不進統計（列名單）。
 L3 進場 ＝ 燈 1 季結束後第一個交易日的還原開盤（無成交 ⇒ 順延到下一個有成交開盤）；甲乙同口徑。價格面板＝researchV41EV 同一面板（PIN 9b0e9882572c）。
 L4 結算：12 月、24 月 ＝ 進場日＋H 個日曆月當天或之前最後一個交易日還原收盤；目標日超出資料尾 ⇒「未到」、⛔ 不入該欄分母（件數照報）。
    到末日 ＝ 資料尾（面板尾）收盤。壞根 ⇒ 截斷在第一個壞根前一根（主欄）；減資／面額變更接續版另欄；下市 ⇒ 最後有效收盤。
 L5 R ＝ 結算價 ÷ 進場價 − 1 − 0.585%（來回）；大盤 ＝ data/history/market_tri.csv 進場前一交易日收盤 → 結算日收盤；超額（份）＝ R − 大盤。
 L6 命中率 ＝ 訊號（等權值）超額 ＞0、≥+1、≥+2 各占幾成；分母 ＝ 該欄有值（非未到）的訊號數。
 L7 加碼（seq41 §三）：燈 2 欄有季 ⇒ 燈 2 季結束後第一個交易日還原開盤，每檔加 2 份；只在加碼進場日晚於燈 1 進場日時加。
    加碼那 2 份本身 ★ 兩種結算：(a) 自己的 12／24 月（加碼進場＋H 月）與到末日；(b) 同結算日＝跟燈 1 那 1 份同一天結算（12／24 月版用燈 1 進場＋H 月；
    到末日兩者相同）；加碼進場不早於 (b) 的結算日 ⇒ 該段不加碼。報的是 2 份合計（＝每份超額 × 2）。
    整體兩版：甲＝只買 1 份（每訊號 1 份的超額）；乙＝有加碼（每訊號 1 份＋加碼 2 份的總損益，用 (b) 同結算日；沒有燈 2 的訊號乙＝甲）；
    報酬率版 ＝ 乙總損益 ÷ 投入份數（有加碼 3、無加碼 1）。主欄用到末日，另附 12／24 月。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchV41EV as V                    # noqa: E402
from backtest import researchTopSell_freq as TS             # noqa: E402

SRC = "/mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v3_產業分析線-20261025-1610.csv"
OUT = "backtest/resultsLampCensus"
COST = V.COST_TW
FLOOR = 1e10
HS = (12, 24, "末")
TYPES = ("缺貨", "新需求", "政策")
LIMIT = ("限制（產業 seq44 §三，結果句照寫）：只有 6 個產業（水泥、食品、塑膠、紡織、電機機械、電器電纜），電子類還沒做；一般搜尋偏向近年新文章、舊報導較難搜到"
         "（電器電纜 6 季只找得到華新自己的消息、水泥政策型 8 季沒有新出處）；蒐集員讀過歷史，挑消息時可能偏向後來有漲的（已用固定產業清單、只准用當時出處、"
         "判燈不看股價壓低，但無法完全消除）；「受害者不是受益者」（產業第 27 條）：公司自己工廠出事時不買那家、改買同主題其他已點名公司，沒有可替代就記無點名。"
         "——描述、⛔ 不判定、不計 N。")
log = V.log
LOG = V.LOG


def q_last_month(q):
    m = re.match(r"^(\d{4})Q([1-4])$", q.strip())
    return f"{m.group(1)}-{int(m.group(2)) * 3:02d}" if m else None


def codes_of(r):
    out = []
    for k in ("公司1", "公司2", "公司3"):
        s = r[k].strip()
        if s and s != "無點名":
            m = re.match(r"^(\d{4})", s)
            out.append((m.group(1) if m else None, s))
    return out


def load_signals():
    S = pd.read_csv(SRC, dtype=str, keep_default_na=False)
    S = S.rename(columns={"版本(甲/乙/兩版)": "版本"})
    if len(S) != 44:
        raise SystemExit(f"⛔ 清單列數 {len(S)} ≠ 44")
    S["甲"] = S["版本"].isin(["甲", "兩版"]); S["乙"] = S["版本"].isin(["乙", "兩版"])
    S["無點名"] = S["公司1"].str.strip() == "無點名"
    return S


class Engine:
    """researchV41EV.tw_rows 的結算／截斷／接續原式，改成可指定目標日。"""

    def __init__(self):
        self.eng = V.tw_engine()
        self.sha, self.PX, self.O, self.nseam, self.T, self.Z = self.eng
        PX = self.PX
        self.CAL, self.ix, self.C, self.BAD, self.VP, self.LASTV, self.TRD = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"], PX["TRD"]
        self.CEND = len(self.CAL) - 1
        self.ADJ = {}

    def lastvalid_le(self, i, x):
        vp = self.VP[i]; k = int(np.searchsorted(vp, x, "right")) - 1
        return int(vp[k]) if k >= 0 else -1

    def opened(self, i, p):
        return bool(self.TRD[i, p] and np.isfinite(self.O[i, p]) and self.O[i, p] > 0 and np.isfinite(self.C[i, p]))

    def adj_events(self, sid):
        if sid not in self.ADJ:
            t = V.tshow(self.sha, f"data/adj/{sid}.csv")
            import io
            self.ADJ[sid] = {} if t is None else {pd.Timestamp(r["date"]): r for _, r in pd.read_csv(io.BytesIO(t), dtype=str).iterrows()
                                                  if r["event"] in ("reduce", "parvalue")}
        return self.ADJ[sid]

    def bridge(self, i, sid, e, xe):
        PX, C, BAD, CAL = self.PX, self.C, self.BAD, self.CAL
        k = 1.0; info = []
        for b in (e + 1 + np.flatnonzero(BAD[i, e + 1:xe + 1])):
            b = int(b); ev = self.adj_events(sid).get(CAL[b]); pb = self.lastvalid_le(i, b - 1)
            if ev is None or pb < e or not np.isfinite(C[i, b]):
                return None, f"壞根 {CAL[b].date()} 非減資／面額變更事件"
            rb = TS.raw_close(PX["main_data"] if b >= PX["NE"] else PX["early_data"], sid, CAL[b])
            rp = TS.raw_close(PX["main_data"] if pb >= PX["NE"] else PX["early_data"], sid, CAL[pb])
            g = rb / float(ev["ref_price"]) * float(ev["pre_close"]) / rp
            if not np.isfinite(g) or g <= 0:
                return None, f"壞根 {CAL[b].date()} 接續倍數不可算"
            k = k * (C[i, pb] * g) / C[i, b]
            info.append(f"{CAL[b].date()} {ev['event']}")
        return k, "；".join(info)

    def entry(self, sid, ym):
        """ym 月之後第一個有成交開盤日。回 (i, e, 順延日) 或 (None, 原因, None)。"""
        if sid not in self.ix:
            return None, "資料不足(面板查無)", None
        i = self.ix[sid]
        p0 = int(self.CAL.searchsorted((pd.Period(ym, "M") + 1).to_timestamp()))
        e = p0
        while e <= self.CEND and not self.opened(i, e):
            e += 1
        if e > self.CEND:
            return None, "資料不足(進場後無成交)", None
        if int(self.LASTV[i]) < e:
            return None, "資料不足(進場後無有效K棒)", None
        return i, e, e - p0

    def settle(self, i, sid, e, tgt):
        """tgt＝Timestamp 或 None（到資料末日）。回 dict。"""
        CAL, C, BAD, CEND, T = self.CAL, self.C, self.BAD, self.CEND, self.T
        P0 = float(self.O[i, e]); tri0 = V.tri_at(T, CAL[e - 1])
        lastv = int(self.LASTV[i]); delist = (CEND - lastv) >= 5
        if tgt is None:
            notyet = False; x = CEND; st0 = "到末日"
        else:
            notyet = tgt > CAL[CEND]
            x = CEND if notyet else int(CAL.searchsorted(tgt, "right")) - 1
            st0 = "未到" if notyet else "完整"
        bb = np.flatnonzero(BAD[i, e + 1:x + 1]); bad_d = ""; st = st0
        if len(bb):
            b = e + 1 + int(bb[0]); bad_d = str(CAL[b].date()); xe = self.lastvalid_le(i, b - 1); st = "⚠壞根截斷" + ("＋未到" if notyet else "")
        elif delist and lastv < x:
            xe = lastv; st = "下市結算" + ("＋未到" if notyet else "")
        else:
            xe = self.lastvalid_le(i, x)
        R = float(C[i, xe] / P0 - 1 - COST); M = V.tri_at(T, CAL[xe]) / tri0 - 1
        row = {"進場日": str(CAL[e].date()), "目標日": "" if tgt is None else str(tgt.date()), "結算日": str(CAL[xe].date()), "狀態": st, "壞根日": bad_d,
               "未到": bool(notyet), "R": R, "大盤": M, "超額": R - M}
        if len(bb):
            xq = lastv if (delist and lastv < x) else self.lastvalid_le(i, x)
            k, note = self.bridge(i, sid, e, xq)
            row["接續註"] = note
            if k is not None:
                Rb = float(C[i, xq] * k / P0 - 1 - COST); Mb = V.tri_at(T, CAL[xq]) / tri0 - 1
                row.update({"接續R": Rb, "接續超額": Rb - Mb, "接續結算日": str(CAL[xq].date())})
        row["xb"] = row.get("接續超額", row["超額"]) if len(bb) and np.isfinite(row.get("接續超額", np.nan)) else row["超額"]
        return row


def hit_stats(vals):
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    n = len(v)
    if n == 0:
        return {"n": 0, ">0": np.nan, "≥+1": np.nan, "≥+2": np.nan, "平均": np.nan, "中位": np.nan, ">0件": 0, "≥+1件": 0, "≥+2件": 0}
    return {"n": n, ">0件": int((v > 0).sum()), "≥+1件": int((v >= 1).sum()), "≥+2件": int((v >= 2).sum()),
            ">0": float((v > 0).mean()), "≥+1": float((v >= 1).mean()), "≥+2": float((v >= 2).mean()), "平均": float(v.mean()), "中位": float(np.median(v))}


def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    shutil.copyfile(SRC, os.path.join(OUT, "signals_input.csv"))
    S = load_signals()
    EN = Engine(); sha = EN.sha
    global TRI
    TRI = EN.T
    meta = {"tw_sha": sha, "面板尾": str(EN.CAL[EN.CEND].date()),
            "大盤": f"data/history/market_tri.csv {EN.T.index[0].date()}～{EN.T.index[-1].date()}（{len(EN.T)} 日）"}
    cache = {}; CAPS = []; ROWS = []
    for _, r in S.iterrows():
        if r["無點名"]:
            continue
        ym1 = q_last_month(r["燈1季"]); ym2 = q_last_month(r["燈2季"]) if r["燈2季"].strip() else None
        for sid, nm in codes_of(r):
            v, d, cl, sh, note = V.tw_cap(sha, sid, ym1, [], cache)
            flag = "查無、未剔除" if not np.isfinite(v) else ("過下限" if v >= FLOOR else "市值不足、剔除")
            CAPS.append({"訊號": r["訊號編號"], "版本": r["版本"], "型": r["型"], "主題": r["主題"], "代號": sid, "名稱": nm, "燈1季": r["燈1季"], "月底日": d,
                         "未還原收盤": cl, "股數": sh, "市值(億)": v / 1e8 if np.isfinite(v) else np.nan, "判定": flag, "來源註": note})
            base = {"訊號": r["訊號編號"], "版本": r["版本"], "甲": r["甲"], "乙": r["乙"], "型": r["型"], "產業": r["產業"], "主題": r["主題"], "代號": sid, "名稱": nm,
                    "燈1季": r["燈1季"], "燈2季": r["燈2季"], "入選": flag != "市值不足、剔除", "下限": flag}
            ent = EN.entry(sid, ym1)
            if ent[0] is None:
                ROWS.append({**base, "段": "燈1", "H": "末", "狀態": ent[1]}); continue
            i, e, dl = ent
            for H in HS:
                tgt = None if H == "末" else EN.CAL[e] + pd.DateOffset(months=H)
                ROWS.append({**base, "段": "燈1", "H": H, "進場順延日": dl, **EN.settle(i, sid, e, tgt)})
            if ym2:
                e2r = EN.entry(sid, ym2)
                if e2r[0] is None:
                    ROWS.append({**base, "段": "加碼(a)", "H": "末", "狀態": e2r[1]}); continue
                _, e2, dl2 = e2r
                if e2 <= e:
                    ROWS.append({**base, "段": "加碼(a)", "H": "末", "狀態": "加碼日不晚於燈1進場、不加碼"}); continue
                for H in HS:
                    tgt = None if H == "末" else EN.CAL[e2] + pd.DateOffset(months=H)
                    ROWS.append({**base, "段": "加碼(a)", "H": H, "進場順延日": dl2, **EN.settle(i, sid, e2, tgt)})
                for H in (12, 24):
                    tgt = EN.CAL[e] + pd.DateOffset(months=H)       # 燈 1 那 1 份的判決目標日
                    if EN.CAL[e2] >= min(tgt, EN.CAL[EN.CEND] + pd.Timedelta(days=1)):
                        ROWS.append({**base, "段": "加碼(b)", "H": H, "進場日": str(EN.CAL[e2].date()), "狀態": "加碼日晚於燈1結算日、該段不加碼"}); continue
                    ROWS.append({**base, "段": "加碼(b)", "H": H, "進場順延日": dl2, **EN.settle(i, sid, e2, tgt)})
    log(f"[結算] {time.time() - t0:.0f}s")
    CP = pd.DataFrame(CAPS); CP.to_csv(os.path.join(OUT, "caps.csv"), index=False, encoding="utf-8-sig")
    RW = pd.DataFrame(ROWS); RW["H"] = RW["H"].astype(str)
    cols = ["訊號", "版本", "甲", "乙", "型", "產業", "主題", "代號", "名稱", "燈1季", "燈2季", "下限", "入選", "段", "H", "進場日", "進場順延日", "目標日", "結算日",
            "狀態", "壞根日", "未到", "R", "大盤", "超額", "接續R", "接續超額", "接續結算日", "接續註", "xb"]
    RW = RW.reindex(columns=cols); RW.to_csv(os.path.join(OUT, "rows.csv"), index=False, encoding="utf-8-sig")

    # ── 每訊號一列（入選檔、非未到、有值者等權）
    ok = RW[RW["入選"] & RW["R"].notna()].copy()
    SG = []
    for _, r in S.iterrows():
        rec = {"訊號": r["訊號編號"], "版本": r["版本"], "甲": r["甲"], "乙": r["乙"], "型": r["型"], "產業": r["產業"], "主題": r["主題"], "燈1季": r["燈1季"],
               "燈2季": r["燈2季"], "無點名": r["無點名"]}
        allc = [c for c, _ in codes_of(r)]
        cut = CP[(CP["訊號"] == r["訊號編號"]) & (CP["判定"] == "市值不足、剔除")]["代號"].tolist()
        rec["點名檔"] = "／".join(allc); rec["剔除檔"] = "／".join(cut)
        d = ok[ok["訊號"] == r["訊號編號"]]
        rec["入選檔"] = "／".join(d["代號"].drop_duplicates())
        rec["檔數"] = d["代號"].nunique()
        for H in map(str, HS):
            for seg, tag in (("燈1", ""), ("加碼(a)", "加碼a_"), ("加碼(b)", "加碼b_")):
                q = d[(d["段"] == seg) & (d["H"] == H)]
                qq = q[~q["未到"].astype(bool)]
                rec[f"{tag}{H}_未到"] = bool(len(q) and q["未到"].astype(bool).any())
                rec[f"{tag}{H}_超額"] = float(qq["超額"].mean()) if len(qq) and len(qq) == len(q) else np.nan
                rec[f"{tag}{H}_xb"] = float(qq["xb"].mean()) if len(qq) and len(qq) == len(q) else np.nan
                rec[f"{tag}{H}_截斷"] = bool(q["狀態"].fillna("").str.contains("壞根").any())
        rec["有加碼"] = bool(np.isfinite(rec["加碼a_末_超額"]))
        # 甲乙兩版整體（b 同結算日；末＝a）
        for H in map(str, HS):
            x1 = rec[f"{H}_超額"]; xb1 = rec[f"{H}_xb"]
            a = rec["加碼a_末_超額"] if H == "末" else rec[f"加碼b_{H}_超額"]
            ab = rec["加碼a_末_xb"] if H == "末" else rec[f"加碼b_{H}_xb"]
            add = np.isfinite(a)
            rec[f"甲_{H}"] = x1
            rec[f"乙_{H}"] = x1 + 2 * a if add else x1
            rec[f"乙率_{H}"] = (x1 + 2 * a) / 3 if add else x1
            rec[f"乙接續_{H}"] = xb1 + 2 * ab if add else xb1
            rec[f"加碼段_{H}"] = bool(add and np.isfinite(x1))
        SG.append(rec)
    SG = pd.DataFrame(SG); SG.to_csv(os.path.join(OUT, "signals.csv"), index=False, encoding="utf-8-sig")

    # ── 統計
    ST = []
    for ver in ("甲", "乙"):
        base = SG[SG[ver] & ~SG["無點名"] & (SG["檔數"] > 0)]
        for ty in ("全部",) + TYPES:
            b = base if ty == "全部" else base[base["型"] == ty]
            for H in map(str, HS):
                for unit in ("訊號", "每檔"):
                    for met in ("超額", "xb"):
                        if unit == "訊號":
                            vals = b[f"{H}_{met}"].tolist(); nyet = int(b[f"{H}_未到"].sum())
                        else:
                            e_ = ok[(ok["段"] == "燈1") & (ok["H"] == H) & ok["訊號"].isin(b["訊號"])]
                            vals = e_[~e_["未到"].astype(bool)][met].tolist(); nyet = int(e_["未到"].astype(bool).sum())
                        ST.append({"表": "命中率", "版": ver, "型": ty, "H": H, "單位": unit, "量": met, "訊號數": len(b), "未到": nyet, **hit_stats(vals)})
                # 加碼那 2 份本身（訊號單位；×2）
                for seg in ("加碼(a)", "加碼(b)"):
                    if seg == "加碼(b)" and H == "末":
                        continue
                    tag = "加碼a_" if seg == "加碼(a)" else "加碼b_"
                    have = b[b["燈2季"].str.strip() != ""]
                    vals = (2 * have[f"{tag}{H}_超額"]).tolist()
                    e_ = ok[(ok["段"] == seg) & (ok["H"] == H) & ok["訊號"].isin(b["訊號"])]
                    ST.append({"表": "加碼2份", "版": ver, "型": ty, "H": H, "單位": "訊號", "量": seg, "訊號數": len(have),
                               "未到": int(have[f"{tag}{H}_未到"].sum()), **hit_stats(vals)})
                    ST.append({"表": "加碼2份", "版": ver, "型": ty, "H": H, "單位": "每檔", "量": seg, "訊號數": len(have),
                               "未到": int(e_["未到"].astype(bool).sum()), **hit_stats((2 * e_[~e_["未到"].astype(bool)]["超額"]).tolist())})
                # 甲乙兩版整體
                for k, lab in (("甲", "甲只買1份"), ("乙", "乙有加碼(總損益)"), ("乙率", "乙有加碼(÷投入份數)"), ("乙接續", "乙有加碼(總損益，接續版)")):
                    vals = b[f"{k}_{H}"].tolist()
                    ST.append({"表": "甲乙", "版": ver, "型": ty, "H": H, "單位": "訊號", "量": lab, "訊號數": len(b), "未到": int(b[f"{H}_未到"].sum()),
                               "有加碼訊號": int(b[f"加碼段_{H}"].sum()), **hit_stats(vals)})
                    sub = b[b[f"加碼段_{H}"]]
                    ST.append({"表": "甲乙_有加碼者", "版": ver, "型": ty, "H": H, "單位": "訊號", "量": lab, "訊號數": len(sub), "未到": 0,
                               **hit_stats(sub[f"{k}_{H}"].tolist())})
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")
    write_md(S, SG, ST, CP, RW, meta)
    MJ = {"性質": "近年燈號普查＋燈 2 加碼（描述、不判定、不計 N）", "限制": LIMIT, "請求": "產業分析線 seq41 §一§三、seq44；回測 1450", **meta,
          "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")


def f2(v):
    return "—" if v is None or not np.isfinite(v) else f"{v:+.2f}"


def pc(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"


def sg(ST, **kw):
    d = ST
    for k, v in kw.items():
        d = d[d[k] == v]
    return d.iloc[0] if len(d) else None


TRI = None


def write_md(S, SG, ST, CP, RW, meta):
    Hlab = {"12": "12 月", "24": "24 月", "末": "到末日"}
    md = [LIMIT, "", "# 近年燈號普查：燈亮後對大盤超額與命中率＋燈 2 加碼 2 份（產業 seq41 §一§三、seq44）", "",
          "- 單位「份」＝每檔 1 份的損益倍數；超額＝R（還原含息、扣 0.585% 來回）− 大盤（market_tri 發行量加權股價報酬指數，含息）。",
          "- 進場＝燈 1 季結束後第一個交易日開盤（甲乙同口徑）；12／24 月＝進場＋H 個日曆月；到末日＝資料尾。未到 12／24 月 ⇒ 標「未到」、不入該欄分母（件數照報）。",
          "- 同一訊號內各檔等權＝1 個樣本；另附每檔各算版。主欄壞根截斷、接續版另附。規模下限＝燈 1 季最後一個交易日市值（未還原收盤 × 當日發行股數）≥ 100 億。",
          f"- 資料：台股面板 sha {meta['tw_sha'][:12]}（面板尾 {meta['面板尾']}）；大盤 {meta['大盤']}。", ""]
    # 件數
    md += ["## 件數", "", "| 版 | 訊號列 | 無點名（不算） | 有公司 | 規模全剔除 | 進統計 | 缺貨／新需求／政策 | 有燈 2 | 12 月未到 | 24 月未到 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        a = SG[SG[ver]]; nm = int(a["無點名"].sum()); hc = a[~a["無點名"]]; inn = hc[hc["檔數"] > 0]
        allcut = hc[hc["檔數"] == 0]
        md.append(f"| {ver} | {len(a)} | {nm} | {len(hc)} | {len(allcut)}（{'、'.join(allcut['訊號']) or '無'}） | {len(inn)} | "
                  f"{(inn['型'] == '缺貨').sum()}／{(inn['型'] == '新需求').sum()}／{(inn['型'] == '政策').sum()} | {(inn['燈2季'].str.strip() != '').sum()} | "
                  f"{int(inn['12_未到'].sum())} | {int(inn['24_未到'].sum())} |")
    md.append("")
    md.append("- 無點名訊號：" + "、".join(f"{r.訊號}（{r.版本}）" for r in SG[SG["無點名"]].itertuples()))
    cut = CP[CP["判定"] == "市值不足、剔除"]
    md.append(f"- 規模下限剔除 {len(cut)} 檔次：" + "；".join(f"{r['訊號']} {r['名稱']}（{r['燈1季']} 末 {r['市值(億)']:.0f} 億）" for _, r in cut.iterrows()))
    unk = CP[CP["判定"] == "查無、未剔除"]
    md.append(f"- 市值查無、未剔除：{len(unk)} 檔次" + ("：" + "；".join(f"{r.訊號} {r.名稱}（{r.來源註}）" for r in unk.itertuples()) if len(unk) else ""))
    nod = RW[(RW["段"] == "燈1") & RW["R"].isna()]
    md.append(f"- 價格資料不足：{len(nod)} 檔次" + ("：" + "；".join(f"{r.訊號} {r.代號}（{r.狀態}）" for r in nod.itertuples()) if len(nod) else ""))
    tr = RW[(RW["段"] == "燈1") & (RW["H"] == "末") & RW["狀態"].fillna("").str.contains("壞根|下市")]
    md.append(f"- 壞根截斷／下市（燈 1、到末日）：{len(tr)} 檔次" + ("：" + "；".join(f"{r.訊號} {r.代號} {r.狀態} {r.壞根日}（接續 {f2(r.接續超額)}；{r.接續註}）" for r in tr.itertuples()) if len(tr) else ""))
    dl = RW[(RW["進場順延日"].fillna(0) > 0)].drop_duplicates(["訊號", "代號", "段"])
    md.append("- 進場順延：" + ("；".join(f"{r.訊號} {r.代號} {r.段} 順延 {int(r.進場順延日)} 日" for r in dl.itertuples()) or "無"))
    md.append("")
    # 命中率
    md += ["## 命中率（訊號＝1 個樣本；超額＞0／≥+1 份／≥+2 份；平均／中位，份）", "",
           "| 版 | 型 | 段 | 有值訊號 | 未到 | ＞0 | ≥+1 | ≥+2 | 平均 | 中位 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        for ty in ("全部",) + TYPES:
            for H in ("12", "24", "末"):
                s = sg(ST, 表="命中率", 版=ver, 型=ty, H=H, 單位="訊號", 量="超額")
                md.append(f"| {ver} | {ty} | {Hlab[H]} | {s['n']} | {s['未到']} | {pc(s['>0'])}（{s['>0件']}） | {pc(s['≥+1'])}（{s['≥+1件']}） | {pc(s['≥+2'])}（{s['≥+2件']}） | {f2(s['平均'])} | {f2(s['中位'])} |")
    md += ["", "### 每檔各算版（同上，每檔次 1 個樣本）", "", "| 版 | 型 | 段 | 檔次 | 未到 | ＞0 | ≥+1 | ≥+2 | 平均 | 中位 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        for ty in ("全部",) + TYPES:
            for H in ("12", "24", "末"):
                s = sg(ST, 表="命中率", 版=ver, 型=ty, H=H, 單位="每檔", 量="超額")
                md.append(f"| {ver} | {ty} | {Hlab[H]} | {s['n']} | {s['未到']} | {pc(s['>0'])} | {pc(s['≥+1'])} | {pc(s['≥+2'])} | {f2(s['平均'])} | {f2(s['中位'])} |")
    md += ["", "### 接續版（壞根改用減資／面額變更接續值；訊號單位，只列全部）", "", "| 版 | 段 | ＞0 | ≥+1 | ≥+2 | 平均 | 中位 |", "|---|---|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        for H in ("12", "24", "末"):
            s = sg(ST, 表="命中率", 版=ver, 型="全部", H=H, 單位="訊號", 量="xb")
            md.append(f"| {ver} | {Hlab[H]} | {pc(s['>0'])} | {pc(s['≥+1'])} | {pc(s['≥+2'])} | {f2(s['平均'])} | {f2(s['中位'])} |")
    # 加碼
    md += ["", "## 加碼那 2 份本身的超額（2 份合計，份；訊號＝1 個樣本）", "",
           "- (a) 自己的 12／24 月＝加碼進場＋H 月；(b) 同結算日＝跟燈 1 那 1 份同一天結算；到末日兩者相同。只在燈 2 進場晚於燈 1 進場時加。", "",
           "| 版 | 型 | 段 | 有燈 2 訊號 | 有值 | 未到 | 平均 | 中位 | ＞0 |", "|---|---|---|---|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        for ty in ("全部",) + TYPES:
            for H, seg in (("末", "加碼(a)"), ("12", "加碼(a)"), ("24", "加碼(a)"), ("12", "加碼(b)"), ("24", "加碼(b)")):
                s = sg(ST, 表="加碼2份", 版=ver, 型=ty, H=H, 單位="訊號", 量=seg)
                if s is None or s["訊號數"] == 0:
                    continue
                lab = Hlab[H] + ("" if H == "末" else ("（自己）" if seg == "加碼(a)" else "（同結算日）"))
                md.append(f"| {ver} | {ty} | {lab} | {s['訊號數']} | {s['n']} | {s['未到']} | {f2(s['平均'])} | {f2(s['中位'])} | {pc(s['>0'])} |")
    md += ["", "## 甲（只買 1 份）vs 乙（有加碼）整體（份；訊號＝1 個樣本；沒有燈 2 的訊號乙＝甲）", "",
           "- 乙＝1 份＋加碼 2 份的總損益（同結算日）；報酬率版＝乙總損益 ÷ 投入份數（有加碼 3 份、無加碼 1 份）。", "",
           "| 版 | 型 | 段 | 有值訊號（其中有加碼） | 甲 平均／中位 | 乙總損益 平均／中位 | 乙÷份數 平均／中位 | 乙接續版 平均／中位 |", "|---|---|---|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        for ty in ("全部",) + TYPES:
            for H in ("末", "12", "24"):
                a = sg(ST, 表="甲乙", 版=ver, 型=ty, H=H, 量="甲只買1份"); b = sg(ST, 表="甲乙", 版=ver, 型=ty, H=H, 量="乙有加碼(總損益)")
                c = sg(ST, 表="甲乙", 版=ver, 型=ty, H=H, 量="乙有加碼(÷投入份數)"); d = sg(ST, 表="甲乙", 版=ver, 型=ty, H=H, 量="乙有加碼(總損益，接續版)")
                md.append(f"| {ver} | {ty} | {Hlab[H]} | {a['n']}（{int(b['有加碼訊號'])}） | {f2(a['平均'])}／{f2(a['中位'])} | {f2(b['平均'])}／{f2(b['中位'])} | "
                          f"{f2(c['平均'])}／{f2(c['中位'])} | {f2(d['平均'])}／{f2(d['中位'])} |")
    md += ["", "### 只看有加碼的訊號（到末日）", "", "| 版 | 有加碼訊號 | 甲 平均／中位 | 乙總損益 平均／中位 | 乙÷3 平均／中位 |", "|---|---|---|---|---|"]
    for ver in ("甲", "乙"):
        a = sg(ST, 表="甲乙_有加碼者", 版=ver, 型="全部", H="末", 量="甲只買1份"); b = sg(ST, 表="甲乙_有加碼者", 版=ver, 型="全部", H="末", 量="乙有加碼(總損益)")
        c = sg(ST, 表="甲乙_有加碼者", 版=ver, 型="全部", H="末", 量="乙有加碼(÷投入份數)")
        md.append(f"| {ver} | {a['n']} | {f2(a['平均'])}／{f2(a['中位'])} | {f2(b['平均'])}／{f2(b['中位'])} | {f2(c['平均'])}／{f2(c['中位'])} |")
    # 每訊號一列
    md += ["", "## 每訊號一列（訊號等權超額，份；括號＝接續版有差時）", "",
           "| 訊號 | 版本 | 型 | 主題 | 燈1季 | 入選檔 | 剔除 | 12 月 | 24 月 | 到末日 | 燈2季 | 加碼 2 份（末） | 乙總損益（末） |", "|" + "---|" * 13]
    for _, r in SG.iterrows():
        if r["無點名"]:
            continue

        def cell(H):
            x = r[f"{H}_超額"]; xb = r[f"{H}_xb"]
            if r[f"{H}_未到"]:
                return "未到"
            return f2(x) + (f"（{f2(xb)}）" if np.isfinite(x) and np.isfinite(xb) and abs(x - xb) > 1e-9 else "")
        a2 = r["加碼a_末_超額"]; yi = r["乙_末"]
        md.append(f"| {r['訊號']} | {r['版本']} | {r['型']} | {r['主題']} | {r['燈1季']} | {r['入選檔'] or '—'} | {r['剔除檔'] or '—'} | {cell('12')} | {cell('24')} | {cell('末')} | "
                  f"{r['燈2季'] or '—'} | {f2(2 * a2) if np.isfinite(a2) else '—'} | {f2(yi)} |")
    md += ["", "## 異常與註記", "",
           "- 清單 V23 備註寫「乙版燈1另列V24」，但清單內沒有 V24 列；乙版件數（32 訊號、28 有公司、缺貨 8）與產業 seq44 §一表一致 ⇒ 照清單算、未補 V24。",
           "- V40 公司欄為 1503 士電、但備註寫「無點名（待裁定：05S05 士電『重電受惠台商回流』段落）」⇒ 照公司欄算（不是「無點名」），請產業確認。",
           "- 「兩版」列甲乙兩版數字相同（同一列）。",
           f"- ⚠ 到末日欄受 2025Q4～2026 大盤急漲主導：market_tri 2025-09-30 → 2026-09-24 約 +{(V.tri_at(TRI, '2026-09-24') / V.tri_at(TRI, '2025-09-30') - 1) * 100:.0f}%"
           f"（2025-09-30 {V.tri_at(TRI, '2025-09-30'):.0f}、2026-06-30 {V.tri_at(TRI, '2026-06-30'):.0f}、面板尾 {V.tri_at(TRI, '2026-09-24'):.0f}；逐月平順、非跳點），"
           "6 個傳產產業同期多半沒跟上 ⇒ 到末日超額大多為負、加碼 2 份到末日全為負；12／24 月欄較不受此段影響。", "", LIMIT]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

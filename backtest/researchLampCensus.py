# -*- coding: utf-8 -*-
"""近年燈號普查（產業分析線 seq41 §一、seq44；回測 1450 §一；裁定 seq476 電子類、seq477（17:28 版）報法）：
燈 1 後 12／24 月／到資料末日對大盤超額＋燈 2 加碼 2 份（seq41 §三）——回測線計算子代理。描述、⛔ 不判定、不計 N、不改任何規則。
⛔ 不 commit、不改既有檔；researchV41EV（tw_engine、tw_cap、tri_at）、researchTopSell_freq（raw_close）只 import；結算、壞根截斷、接續照 researchV41EV.tw_rows 原式抄
   （差別只在：判決目標日可指定「進場＋H 月」「到資料末日」或「指定日」三種）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus [--src 清單1.csv 清單2.csv ...] [--dry --out 目錄]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus_check [--out 目錄]
    --dry：照算但輸出到 --out（預設 ~/rtfwork/lampcensus_dry，⛔ 不寫 repo），先跑通再出數。
輸入（預設）：/mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v3_產業分析線-20261025-1610.csv（44 列）；電子類清單（產業代碼 24～28）來時用 --src 一起給。
     複本存輸出夾 signals_input.csv（第 2 份起 signals_input_2.csv …）。
輸出：rows.csv（每訊號×每檔×每段）、caps.csv、signals.csv（每訊號一列）、stats.csv、summary.md、main.json、run.log

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
 L6 報法（seq477 17:28）：每個結果報 中位、最好（最大，附訊號）、最壞（最小，附訊號），另附 P25／P75（np.percentile 線性內插）；平均放後面；
    命中率（＞0、≥+1、≥+2 各占幾成）照附。分母 ＝ 該欄有值（非未到）的訊號數。
 L7 加碼（seq41 §三）：燈 2 欄有季 ⇒ 燈 2 季結束後第一個交易日還原開盤，每檔加 2 份；只在加碼進場日晚於燈 1 進場日時加。
    加碼那 2 份本身 ★ 兩種結算：(a) 自己的 12／24 月（加碼進場＋H 月）與到末日；(b) 同結算日＝跟燈 1 那 1 份同一天結算（12／24 月版用燈 1 進場＋H 月；
    到末日兩者相同）；加碼進場不早於 (b) 的結算日 ⇒ 該段不加碼。報的是 2 份合計（＝每份超額 × 2）。
    整體兩版：甲＝只買 1 份（每訊號 1 份的超額）；乙＝有加碼（每訊號 1 份＋加碼 2 份的總損益，用 (b) 同結算日；沒有燈 2 的訊號乙＝甲）；
    報酬率版 ＝ 乙總損益 ÷ 投入份數（有加碼 3、無加碼 1）。主欄用到末日，另附 12／24 月。
 L8 判燈寬嚴（seq477 17:28）：清單有欄名含「判定把握」（值 確定／兩可）⇒ 三個情境：照實＝清單照算；寬鬆＝兩可都算亮燈（＝全部列）；
    嚴格＝燈 1 兩可的訊號列不算，且燈 2 兩可（欄名含「燈2」且含「把握」）⇒ 不加碼（產業 seq47 §二「燈 1 或燈 2 任一兩可 ⇒ 不加碼」；寬鬆版照加）。
    逐份清單判欄：某份清單缺該欄 ⇒ 該份全當「確定」（照寫）；所有清單都沒有判定把握欄 ⇒ 只出照實、寬嚴標「待產業補欄」。
    寬鬆、嚴格兩版的中位並列成範圍，每格標「寬／嚴」（不寫成保守～樂觀）；結果句「範圍來自判燈寬嚴，不是統計誤差」。
    剔自評知道（seq476、產業 seq46 §二）：欄名含「判燈者自評」值為「知道」的訊號剔除（以照實為底、加碼照列）；缺此欄的清單照寫不剔。
 L9 類別（seq476）：產業代碼欄（欄名含「代碼」）24～28 或產業名前綴屬 半導體／電腦（及）週邊／光電／通信網路／電子零組件 ⇒ 電子；水泥、食品、塑膠、紡織、電機機械、電器電纜 ⇒ 傳產；
    其他 ⇒「其他」（照列、log 警示）。有兩類以上 ⇒ 各類分開報，再報合計；只有一類 ⇒ 只報該類。
    多份清單訊號編號重複 ⇒ 第 k 份（k≥2）的編號改成「F{k}:原編號」。
"""
from __future__ import annotations

import argparse
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

SRC = "/mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v4_加判定把握_產業分析線-20261025-1830.csv"
SRC_E = "/mnt/c/SynologyDrive/跨線信箱/附件-電子類燈號普查訊號清單v5_產業分析線-20261026-0130.csv"   # 產業 seq50：v5 取代 v4（E38 補回、E29 燈 2 改兩可）   # 產業 seq45：v4 取代 v3（加判定把握、兩可理由欄）
SRC_V3 = "/mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v3_產業分析線-20261025-1610.csv"
OUT = "backtest/resultsLampCensus"
DRY_OUT = os.path.expanduser("~/rtfwork/lampcensus_dry")
COST = V.COST_TW
FLOOR = 1e10
HS = (12, 24, "末")
TYPES = ("缺貨", "新需求", "政策")
ELEC = ("半導體", "電腦", "光電", "通信網路", "電子零組件")      # 前綴比對（「電腦及週邊」「電腦週邊」都算）
TRAD = ("水泥", "食品", "塑膠", "紡織", "電機機械", "電器電纜")
RANGE_NOTE = "範圍來自判燈寬嚴，不是統計誤差"
FINAL = ("普查是事件點名選股，不是框架第 5 條（主題營收占比前 3 名），不能當第 5 條的驗證。",                      # 裁定 seq478 §二（產業 seq50 §三）
         "燈號在 12、24 月沒有測出選股能力；大贏家多半在判燈者知道後來走勢的那批，無法歸因。")              # 裁定 seq478 §二 定版句
LIMIT = ("限制（產業 seq44 §三，結果句照寫）：只有 6 個產業（水泥、食品、塑膠、紡織、電機機械、電器電纜），電子類還沒做；一般搜尋偏向近年新文章、舊報導較難搜到"
         "（電器電纜 6 季只找得到華新自己的消息、水泥政策型 8 季沒有新出處）；蒐集員讀過歷史，挑消息時可能偏向後來有漲的（已用固定產業清單、只准用當時出處、"
         "判燈不看股價壓低，但無法完全消除）；「受害者不是受益者」（產業第 27 條）：公司自己工廠出事時不買那家、改買同主題其他已點名公司，沒有可替代就記無點名。"
         "——描述、⛔ 不判定、不計 N。")
LIMIT_E = ("電子類限制（裁定 seq476 §二、產業 seq46 §二，結果句照寫）：只用當時出處，但蒐集與判燈者讀過歷史；舊文較難搜到（2021H1 偏多）；"
           "電子類後見偏差比傳產大（AI 這波大家都知道誰漲），已加兩道防線（每季先列當季有 A／B 級事件的全部公司再判燈、判燈者自評是否知道後來走勢，另出剔除自評知道版），"
           "仍無法完全消除；範圍來自判燈寬嚴，不是統計誤差；到末日欄被大盤 +89%（2025-09-30→2026-09-24）主導。")
log = V.log
LOG = V.LOG


def q_last_month(q):
    m = re.match(r"^(\d{4})Q([1-4])$", q.strip())
    return f"{m.group(1)}-{int(m.group(2)) * 3:02d}" if m else None


def codes_of(r):
    out = []
    for k in ("公司1", "公司2", "公司3"):
        s = str(r.get(k, "")).strip()
        if s and s != "無點名":
            m = re.match(r"^(\d{4})", s)
            out.append((m.group(1) if m else None, s))
    return out


def cls_of(r, code_col):
    if code_col:
        m = re.match(r"^\s*(\d{1,2})", str(r[code_col]))
        if m:
            c = int(m.group(1))
            if 24 <= c <= 28:
                return "電子"
            if 1 <= c <= 6:
                return "傳產"
    ind = str(r["產業"]).strip()
    if any(ind.startswith(x) for x in ELEC):
        return "電子"
    if ind in TRAD:
        return "傳產"
    return "其他"


def load_signals(srcs):
    """回 (S, info)。S 欄：訊號（唯一鍵）、原編號、檔、版本、甲、乙、無點名、類、兩可、燈2兩可 ＋ 原欄。"""
    parts = []; info = {"來源": [], "有判定把握欄": False, "有燈2把握欄": False, "有自評欄": False}
    for k, f in enumerate(srcs, 1):
        D = pd.read_csv(f, dtype=str, keep_default_na=False)
        vcol = [c for c in D.columns if c.startswith("版本")][0]
        D = D.rename(columns={vcol: "版本"})
        sure = [c for c in D.columns if "把握" in c and "燈2" not in c]
        sure2 = [c for c in D.columns if "把握" in c and "燈2" in c]
        code_col = next((c for c in D.columns if "代碼" in c), None)
        D["檔"] = k; D["原編號"] = D["訊號編號"]
        D["兩可"] = D[sure[0]].str.strip().eq("兩可") if sure else False
        D["燈2兩可"] = D[sure2[0]].str.strip().eq("兩可") if sure2 else False
        selfc = [c for c in D.columns if "判燈者自評" in c]
        D["自評知道"] = D[selfc[0]].str.strip().eq("知道") if selfc else False
        D["類"] = [cls_of(r, code_col) for _, r in D.iterrows()]
        info["有判定把握欄"] |= bool(sure); info["有燈2把握欄"] |= bool(sure2); info["有自評欄"] |= bool(selfc)
        if sure:
            bad = D[~D[sure[0]].str.strip().isin(["確定", "兩可"])]
            if len(bad):
                log(f"⚠ {os.path.basename(f)} 判定把握欄有非「確定／兩可」值 {len(bad)} 列：{bad['訊號編號'].tolist()[:10]}（當確定）")
        info["來源"].append({"檔": f, "列數": len(D), "判定把握欄": sure[0] if sure else "缺", "燈2把握欄": sure2[0] if sure2 else "缺", "自評欄": selfc[0] if selfc else "缺（照寫不剔）", "代碼欄": code_col or "缺"})
        parts.append(D)
    seen = set()
    for D in parts:
        ids = D["原編號"].tolist(); k = int(D["檔"].iloc[0]) if len(D) else 1
        D["訊號"] = [i if (i not in seen or k == 1) else f"F{k}:{i}" for i in ids]
        seen |= set(D["訊號"])
    S = pd.concat(parts, ignore_index=True)
    if S["訊號"].duplicated().any():
        raise SystemExit(f"⛔ 訊號編號重複：{S[S['訊號'].duplicated()]['訊號'].tolist()}")
    if srcs == [SRC] and len(S) != 44:
        raise SystemExit(f"⛔ 預設清單列數 {len(S)} ≠ 44")
    S["甲"] = S["版本"].isin(["甲", "兩版"]); S["乙"] = S["版本"].isin(["乙", "兩版"])
    S["無點名"] = S["公司1"].str.strip() == "無點名"
    oth = S[S["類"] == "其他"]
    if len(oth):
        log(f"⚠ 類別判不出（列「其他」）{len(oth)} 列：{oth['訊號'].tolist()[:10]}")
    return S, info


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


def summ(vals, ids=None):
    """中位、最好（最大）、最壞（最小）、P25、P75、平均、命中率。ids 與 vals 對齊時附最好／最壞訊號。"""
    ids = list(ids) if ids is not None else [""] * len(vals)
    pr = [(float(x), i) for x, i in zip(vals, ids) if x is not None and np.isfinite(x)]
    n = len(pr)
    if n == 0:
        return {"n": 0, "中位": np.nan, "最好": np.nan, "最好訊號": "", "最壞": np.nan, "最壞訊號": "", "P25": np.nan, "P75": np.nan, "平均": np.nan,
                ">0": np.nan, "≥+1": np.nan, "≥+2": np.nan, ">0件": 0, "≥+1件": 0, "≥+2件": 0}
    v = np.array([x for x, _ in pr])
    hi = int(np.argmax(v)); lo = int(np.argmin(v))
    return {"n": n, "中位": float(np.median(v)), "最好": float(v[hi]), "最好訊號": pr[hi][1], "最壞": float(v[lo]), "最壞訊號": pr[lo][1],
            "P25": float(np.percentile(v, 25)), "P75": float(np.percentile(v, 75)), "平均": float(v.mean()),
            ">0": float((v > 0).mean()), "≥+1": float((v >= 1).mean()), "≥+2": float((v >= 2).mean()),
            ">0件": int((v > 0).sum()), "≥+1件": int((v >= 1).sum()), "≥+2件": int((v >= 2).sum())}


hit_stats = summ    # 舊名相容


def combo(SG, drop_addon):
    """甲乙兩版整體欄（b 同結算日；末＝a）。drop_addon：True 的列當作不加碼（嚴格版燈 2 兩可）。"""
    SG = SG.copy()
    for H in map(str, HS):
        x1 = SG[f"{H}_超額"]; xb1 = SG[f"{H}_xb"]
        a = (SG["加碼a_末_超額"] if H == "末" else SG[f"加碼b_{H}_超額"]).where(~drop_addon)
        ab = (SG["加碼a_末_xb"] if H == "末" else SG[f"加碼b_{H}_xb"]).where(~drop_addon)
        add = np.isfinite(a)
        SG[f"加碼用_{H}"] = a; SG[f"加碼用接續_{H}"] = ab
        SG[f"甲_{H}"] = x1
        SG[f"乙_{H}"] = np.where(add, x1 + 2 * a, x1)
        SG[f"乙率_{H}"] = np.where(add, (x1 + 2 * a) / 3, x1)
        SG[f"乙接續_{H}"] = np.where(add, xb1 + 2 * ab, xb1)
        SG[f"加碼段_{H}"] = add & np.isfinite(x1)
    return SG


def run(srcs, out, dry):
    t0 = time.time(); os.makedirs(out, exist_ok=True)
    S, info = load_signals(srcs)
    for k, f in enumerate(srcs, 1):
        shutil.copyfile(f, os.path.join(out, "signals_input.csv" if k == 1 else f"signals_input_{k}.csv"))
    EN = Engine(); sha = EN.sha
    global TRI
    TRI = EN.T
    meta = {"tw_sha": sha, "面板尾": str(EN.CAL[EN.CEND].date()), "dry": dry, "來源": info["來源"],
            "有判定把握欄": info["有判定把握欄"], "有燈2把握欄": info["有燈2把握欄"], "有自評欄": info["有自評欄"],
            "大盤": f"data/history/market_tri.csv {EN.T.index[0].date()}～{EN.T.index[-1].date()}（{len(EN.T)} 日）"}
    cache = {}; CAPS = []; ROWS = []
    for _, r in S.iterrows():
        if r["無點名"]:
            continue
        ym1 = q_last_month(r["燈1季"]); ym2 = q_last_month(r["燈2季"]) if r["燈2季"].strip() else None
        for sid, nm in codes_of(r):
            if sid is None:
                CAPS.append({"訊號": r["訊號"], "類": r["類"], "版本": r["版本"], "型": r["型"], "主題": r["主題"], "代號": "", "名稱": nm, "燈1季": r["燈1季"],
                             "判定": "代號讀不出", "來源註": ""}); continue
            v, d, cl, sh, note = V.tw_cap(sha, sid, ym1, [], cache)
            flag = "查無、未剔除" if not np.isfinite(v) else ("過下限" if v >= FLOOR else "市值不足、剔除")
            CAPS.append({"訊號": r["訊號"], "類": r["類"], "版本": r["版本"], "型": r["型"], "主題": r["主題"], "代號": sid, "名稱": nm, "燈1季": r["燈1季"], "月底日": d,
                         "未還原收盤": cl, "股數": sh, "市值(億)": v / 1e8 if np.isfinite(v) else np.nan, "判定": flag, "來源註": note})
            base = {"訊號": r["訊號"], "類": r["類"], "版本": r["版本"], "甲": r["甲"], "乙": r["乙"], "型": r["型"], "產業": r["產業"], "主題": r["主題"], "代號": sid,
                    "名稱": nm, "燈1季": r["燈1季"], "燈2季": r["燈2季"], "入選": flag != "市值不足、剔除", "下限": flag}
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
    CP = pd.DataFrame(CAPS); CP.to_csv(os.path.join(out, "caps.csv"), index=False, encoding="utf-8-sig")
    RW = pd.DataFrame(ROWS); RW["H"] = RW["H"].astype(str)
    cols = ["訊號", "類", "版本", "甲", "乙", "型", "產業", "主題", "代號", "名稱", "燈1季", "燈2季", "下限", "入選", "段", "H", "進場日", "進場順延日", "目標日", "結算日",
            "狀態", "壞根日", "未到", "R", "大盤", "超額", "接續R", "接續超額", "接續結算日", "接續註", "xb"]
    RW = RW.reindex(columns=cols); RW.to_csv(os.path.join(out, "rows.csv"), index=False, encoding="utf-8-sig")

    # ── 每訊號一列（入選檔、非未到、有值者等權）
    ok = RW[RW["入選"].fillna(False).astype(bool) & RW["R"].notna()].copy()
    SG = []
    for _, r in S.iterrows():
        rec = {"訊號": r["訊號"], "原編號": r["原編號"], "檔": r["檔"], "類": r["類"], "版本": r["版本"], "甲": r["甲"], "乙": r["乙"], "型": r["型"], "產業": r["產業"],
               "主題": r["主題"], "燈1季": r["燈1季"], "燈2季": r["燈2季"], "無點名": r["無點名"], "兩可": bool(r["兩可"]), "燈2兩可": bool(r["燈2兩可"]), "自評知道": bool(r["自評知道"])}
        allc = [c for c, _ in codes_of(r)]
        cut = CP[(CP["訊號"] == r["訊號"]) & (CP["判定"] == "市值不足、剔除")]["代號"].tolist() if len(CP) else []
        rec["點名檔"] = "／".join(c or "?" for c in allc); rec["剔除檔"] = "／".join(cut)
        d = ok[ok["訊號"] == r["訊號"]]
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
        SG.append(rec)
    SG = pd.DataFrame(SG)
    SG = combo(SG, pd.Series(False, index=SG.index))
    SG.to_csv(os.path.join(out, "signals.csv"), index=False, encoding="utf-8-sig")

    # ── 情境、類別
    scen = {"照實": (SG, pd.Series(False, index=SG.index))}
    if info["有判定把握欄"]:
        scen["寬鬆"] = (SG, pd.Series(False, index=SG.index))
        strict = SG[~SG["兩可"]]
        scen["嚴格"] = (strict, strict["燈2兩可"])      # 燈 1 兩可整列不算；燈 2 兩可 ⇒ 不加碼（產業 seq47 §二；缺燈2把握欄的清單＝確定）
    if info["有自評欄"]:
        nk = SG[~SG["自評知道"]]
        scen["剔自評知道"] = (nk, pd.Series(False, index=nk.index))   # 照實減掉判燈者自評「知道」的訊號；無此欄的清單照寫不剔
    classes = [c for c in ("傳產", "電子", "其他") if (SG["類"] == c).any()]
    groups = classes + (["合計"] if len(classes) > 1 else [])
    types = list(TYPES) + [t for t in SG["型"].drop_duplicates() if t not in TYPES]
    meta.update({"情境": list(scen), "類別": groups})
    ST = []
    for sc, (SGs, dropm) in scen.items():
        SGc = combo(SGs, dropm)
        for gp in groups:
            G = SGc if gp == "合計" else SGc[SGc["類"] == gp]
            for ver in ("甲", "乙"):
                base = G[G[ver] & ~G["無點名"] & (G["檔數"] > 0)]
                for ty in ["全部"] + types:
                    b = base if ty == "全部" else base[base["型"] == ty]
                    if ty != "全部" and not len(b):
                        continue
                    key = {"情境": sc, "類": gp, "版": ver, "型": ty}
                    for H in map(str, HS):
                        for unit in ("訊號", "每檔"):
                            for met in ("超額", "xb"):
                                if unit == "訊號":
                                    vals = b[f"{H}_{met}"].tolist(); ids = b["訊號"].tolist(); nyet = int(b[f"{H}_未到"].sum())
                                else:
                                    e_ = ok[(ok["段"] == "燈1") & (ok["H"] == H) & ok["訊號"].isin(b["訊號"])]
                                    e2_ = e_[~e_["未到"].astype(bool)]
                                    vals = e2_[met].tolist(); ids = (e2_["訊號"] + " " + e2_["代號"]).tolist(); nyet = int(e_["未到"].astype(bool).sum())
                                ST.append({**key, "表": "燈1", "H": H, "單位": unit, "量": met, "訊號數": len(b), "未到": nyet, **summ(vals, ids)})
                        # 加碼那 2 份本身（×2）
                        for seg in ("加碼(a)", "加碼(b)"):
                            if seg == "加碼(b)" and H == "末":
                                continue
                            tag = "加碼a_" if seg == "加碼(a)" else "加碼b_"
                            have = b[(b["燈2季"].str.strip() != "") & ~(dropm.reindex(b.index).fillna(False).astype(bool))]
                            ST.append({**key, "表": "加碼2份", "H": H, "單位": "訊號", "量": seg, "訊號數": len(have), "未到": int(have[f"{tag}{H}_未到"].sum()),
                                       **summ((2 * have[f"{tag}{H}_超額"]).tolist(), have["訊號"].tolist())})
                            e_ = ok[(ok["段"] == seg) & (ok["H"] == H) & ok["訊號"].isin(have["訊號"])]
                            e2_ = e_[~e_["未到"].astype(bool)]
                            ST.append({**key, "表": "加碼2份", "H": H, "單位": "每檔", "量": seg, "訊號數": len(have), "未到": int(e_["未到"].astype(bool).sum()),
                                       **summ((2 * e2_["超額"]).tolist(), (e2_["訊號"] + " " + e2_["代號"]).tolist())})
                        # 甲乙兩版整體
                        for k, lab in (("甲", "甲只買1份"), ("乙", "乙有加碼(總損益)"), ("乙率", "乙有加碼(÷投入份數)"), ("乙接續", "乙有加碼(總損益，接續版)")):
                            ST.append({**key, "表": "甲乙", "H": H, "單位": "訊號", "量": lab, "訊號數": len(b), "未到": int(b[f"{H}_未到"].sum()),
                                       "有加碼訊號": int(b[f"加碼段_{H}"].sum()), **summ(b[f"{k}_{H}"].tolist(), b["訊號"].tolist())})
                            sub = b[b[f"加碼段_{H}"].astype(bool)]
                            ST.append({**key, "表": "甲乙_有加碼者", "H": H, "單位": "訊號", "量": lab, "訊號數": len(sub), "未到": 0,
                                       **summ(sub[f"{k}_{H}"].tolist(), sub["訊號"].tolist())})
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(out, "stats.csv"), index=False, encoding="utf-8-sig")
    write_md(out, S, SG, ST, CP, RW, meta, groups)
    MJ = {"性質": "近年燈號普查＋燈 2 加碼（描述、不判定、不計 N）", "限制": LIMIT, "請求": "產業分析線 seq41 §一§三、seq44；回測 1450；裁定 seq476、seq477（17:28）", **meta,
          "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{'dry' if dry else '正式'}｜情境 {list(scen)}｜類 {groups}｜{time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", nargs="+", default=[SRC, SRC_E])
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or (DRY_OUT if a.dry else OUT)
    if a.dry and os.path.abspath(out) == os.path.abspath(OUT):
        raise SystemExit("⛔ --dry 不可寫正式輸出夾")
    run(a.src, out, a.dry)


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
HLAB = {"12": "12 月", "24": "24 月", "末": "到末日"}
HDR = "| 中位 | 最好 | 最壞 | P25 | P75 | 平均 | ＞0 | ≥+1 | ≥+2 |"


def cells(s, best=True):
    if s is None or s["n"] == 0:
        return "| 無樣本 " + "| — " * 8 + "|"
    bw = (f"| {f2(s['最好'])}（{s['最好訊號']}） | {f2(s['最壞'])}（{s['最壞訊號']}） " if best else f"| {f2(s['最好'])} | {f2(s['最壞'])} ")
    return (f"| **{f2(s['中位'])}** {bw}| {f2(s['P25'])} | {f2(s['P75'])} | {f2(s['平均'])} | {pc(s['>0'])}（{s['>0件']}） | "
            f"{pc(s['≥+1'])}（{s['≥+1件']}） | {pc(s['≥+2'])}（{s['≥+2件']}） |")


def write_md(out, S, SG, ST, CP, RW, meta, groups):
    has = meta["有判定把握欄"]; scen = meta["情境"]
    types = [t for t in ["全部"] + list(TYPES) + [t for t in SG["型"].drop_duplicates() if t not in TYPES]]
    md = [(LIMIT.replace("，電子類還沒做", "（此句指傳產部分）") + "　" + LIMIT_E if "電子" in groups else LIMIT), "",
          "# 近年燈號普查：燈亮後對大盤超額（中位、最好、最壞）＋燈 2 加碼 2 份（產業 seq41 §一§三、seq44；裁定 seq476、seq477）", "",
          *[f"> ⭐ {x}" for x in FINAL], "",
          f"- {'⚠ dry 試跑（不是正式數）' if meta['dry'] else '正式輸出'}；情境：{'、'.join(scen)}；類別：{'、'.join(groups)}。",
          "- 報法（seq477 17:28）：每格先報 **中位**、最好（最大，括號為訊號）、最壞（最小）；另附 P25／P75；平均放後面；命中率（＞0／≥+1／≥+2 份）照附。",
          "- 單位「份」＝每檔 1 份的損益倍數；超額＝R（還原含息、扣 0.585% 來回）− 大盤（market_tri 發行量加權股價報酬指數，含息）。",
          "- 進場＝燈 1 季結束後第一個交易日開盤（甲乙同口徑）；12／24 月＝進場＋H 個日曆月；到末日＝資料尾。未到 12／24 月 ⇒ 標「未到」、不入該欄分母（件數照報）。",
          "- 同一訊號內各檔等權＝1 個樣本；另附每檔各算版。主欄壞根截斷、接續版另附。規模下限＝燈 1 季最後一個交易日市值（未還原收盤 × 當日發行股數）≥ 100 億。",
          f"- 資料：台股面板 sha {meta['tw_sha'][:12]}（面板尾 {meta['面板尾']}）；大盤 {meta['大盤']}。",
          "- 清單：" + "；".join(f"{os.path.basename(x['檔'])}（{x['列數']} 列；判定把握欄 {x['判定把握欄']}；燈2把握欄 {x['燈2把握欄']}；代碼欄 {x['代碼欄']}）" for x in meta["來源"]), ""]
    # 判燈寬嚴範圍
    md += ["## 判燈寬嚴範圍（寬鬆版中位～嚴格版中位，份）", "", f"- {RANGE_NOTE}。寬鬆＝兩可都算亮燈（偏樂觀；清單本來就把兩可列為訊號 ⇒ 寬鬆＝照實）；嚴格＝兩可的訊號列都不算（原意偏保守）。括號標明哪個是寬、哪個是嚴：⚠ 本樣本 12／24 月多數格嚴格版中位反而較高（剔掉的兩可訊號多半表現較差），到末日則嚴格版較低或相同。"]
    if not has:
        md += ["- ⚠ **待產業補欄**：清單尚無「判定把握」欄（確定／兩可）⇒ 本次只出「照實」版；寬鬆、嚴格兩版待產業補欄後自動產出。", ""]
    else:
        md += ["", "| 類 | 版 | 型 | 量 | 12 月 | 24 月 | 到末日 |", "|---|---|---|---|---|---|---|"]
        for gp in groups:
            for ver in ("甲", "乙"):
                for ty in types:
                    for tb, met, lab in (("燈1", "超額", "燈 1 那 1 份"), ("加碼2份", "加碼(a)", "加碼 2 份（自己）"), ("甲乙", "乙有加碼(總損益)", "乙有加碼總損益")):
                        cs = []
                        for H in ("12", "24", "末"):
                            kw = dict(類=gp, 版=ver, 型=ty, 表=tb, H=H, 單位="訊號", 量=met)
                            a = sg(ST, 情境="寬鬆", **kw); b = sg(ST, 情境="嚴格", **kw); c_ = sg(ST, 情境="剔自評知道", **kw)
                            if a is None or not np.isfinite(a["中位"]):
                                cs.append("—"); continue
                            if b is None or not np.isfinite(b["中位"]):
                                cs.append(f"寬 {f2(a['中位'])}／嚴 無樣本" + (f"；剔自評知道 {f2(c_['中位'])}" if c_ is not None and np.isfinite(c_['中位']) else "")); continue
                            lo, hi = sorted([a["中位"], b["中位"]])
                            cs.append(f"{f2(lo)}～{f2(hi)}（寬 {f2(a['中位'])}／嚴 {f2(b['中位'])}" + (f"；剔自評知道 {f2(c_['中位'])}" if c_ is not None else "") + "）")
                        if any(c != "—" for c in cs):
                            md.append(f"| {gp} | {ver} | {ty} | {lab} | " + " | ".join(cs) + " |")
        md.append("")
    for sc in scen:
        md += [f"# 情境：{sc}" + {"照實": "（清單照算）", "寬鬆": "（兩可都算亮燈）", "嚴格": "（燈 1 兩可都不算；燈 2 兩可不加碼）",
                                  "剔自評知道": "（照實減掉判燈者自評「知道後來走勢」的訊號；無此欄的清單不剔）"}[sc], ""]
        for gp in groups:
            Gs = SG if gp == "合計" else SG[SG["類"] == gp]
            if sc == "剔自評知道":
                Gs = Gs[~Gs["自評知道"]]
            if sc == "嚴格":
                Gs = Gs[~Gs["兩可"]]
            md += [f"## {sc}｜{gp}", "", "### 件數", "", "| 版 | 訊號列 | 無點名（不算） | 有公司 | 規模全剔除 | 進統計 | 各型 | 有燈 2 | 12 月未到 | 24 月未到 |",
                   "|---|---|---|---|---|---|---|---|---|---|"]
            for ver in ("甲", "乙"):
                a = Gs[Gs[ver]]; nm = int(a["無點名"].sum()); hc = a[~a["無點名"]]; inn = hc[hc["檔數"] > 0]; allcut = hc[hc["檔數"] == 0]
                tys = "／".join(f"{t} {(inn['型'] == t).sum()}" for t in types[1:] if (inn["型"] == t).any())
                md.append(f"| {ver} | {len(a)} | {nm} | {len(hc)} | {len(allcut)}（{'、'.join(allcut['訊號']) or '無'}） | {len(inn)} | {tys} | "
                          f"{(inn['燈2季'].str.strip() != '').sum()} | {int(inn['12_未到'].sum())} | {int(inn['24_未到'].sum())} |")
            md += ["", "### 燈 1 那 1 份（訊號＝1 個樣本）", "", "| 版 | 型 | 段 | 有值（未到） " + HDR, "|" + "---|" * 13]
            for ver in ("甲", "乙"):
                for ty in types:
                    for H in ("12", "24", "末"):
                        s = sg(ST, 情境=sc, 類=gp, 表="燈1", 版=ver, 型=ty, H=H, 單位="訊號", 量="超額")
                        if s is not None:
                            md.append(f"| {ver} | {ty} | {HLAB[H]} | {s['n']}（{s['未到']}） {cells(s)}")
            md += ["", "### 加碼那 2 份本身（2 份合計；(a) 自己的 12／24 月、(b) 跟燈 1 同結算日；到末日兩者相同）", "", "| 版 | 型 | 段 | 有燈 2（有值） " + HDR, "|" + "---|" * 13]
            for ver in ("甲", "乙"):
                for ty in types:
                    for H, seg in (("末", "加碼(a)"), ("12", "加碼(a)"), ("24", "加碼(a)"), ("12", "加碼(b)"), ("24", "加碼(b)")):
                        s = sg(ST, 情境=sc, 類=gp, 表="加碼2份", 版=ver, 型=ty, H=H, 單位="訊號", 量=seg)
                        if s is None or s["訊號數"] == 0:
                            continue
                        lab = HLAB[H] + ("" if H == "末" else ("（自己）" if seg == "加碼(a)" else "（同結算日）"))
                        md.append(f"| {ver} | {ty} | {lab} | {s['訊號數']}（{s['n']}） {cells(s)}")
            md += ["", "### 甲（只買 1 份）vs 乙（有加碼；總損益＝1 份＋加碼 2 份同結算日；沒有燈 2 的訊號乙＝甲）", "",
                   "| 版 | 型 | 段 | 量 | 有值（有加碼） " + HDR, "|" + "---|" * 14]
            for ver in ("甲", "乙"):
                for ty in types:
                    for H in ("12", "24", "末"):
                        for lab, sh in (("甲只買1份", "甲"), ("乙有加碼(總損益)", "乙總損益"), ("乙有加碼(÷投入份數)", "乙÷份數")):
                            s = sg(ST, 情境=sc, 類=gp, 表="甲乙", 版=ver, 型=ty, H=H, 量=lab)
                            if s is not None:
                                md.append(f"| {ver} | {ty} | {HLAB[H]} | {sh} | {s['n']}（{int(s['有加碼訊號'])}） {cells(s)}")
            md += ["", "### 每檔各算版（燈 1 那 1 份，每檔次 1 個樣本；只列全部）", "", "| 版 | 段 | 檔次（未到） " + HDR, "|" + "---|" * 12]
            for ver in ("甲", "乙"):
                for H in ("12", "24", "末"):
                    s = sg(ST, 情境=sc, 類=gp, 表="燈1", 版=ver, 型="全部", H=H, 單位="每檔", 量="超額")
                    if s is not None:
                        md.append(f"| {ver} | {HLAB[H]} | {s['n']}（{s['未到']}） {cells(s)}")
            md += ["", "### 接續版（壞根改用減資／面額變更接續值；燈 1 那 1 份，訊號單位，只列全部）", "", "| 版 | 段 " + HDR, "|" + "---|" * 11]
            for ver in ("甲", "乙"):
                for H in ("12", "24", "末"):
                    s = sg(ST, 情境=sc, 類=gp, 表="燈1", 版=ver, 型="全部", H=H, 單位="訊號", 量="xb")
                    if s is not None:
                        md.append(f"| {ver} | {HLAB[H]} {cells(s, best=False)}")
            md.append("")
    # 名單
    md += ["## 名單與註記", ""]
    md.append("- 無點名訊號：" + ("、".join(f"{r['訊號']}（{r['版本']}）" for _, r in SG[SG["無點名"]].iterrows()) or "無"))
    cut = CP[CP["判定"] == "市值不足、剔除"] if len(CP) else CP
    md.append(f"- 規模下限剔除 {len(cut)} 檔次：" + "；".join(f"{r['訊號']} {r['名稱']}（{r['燈1季']} 末 {r['市值(億)']:.0f} 億）" for _, r in cut.iterrows()))
    unk = CP[CP["判定"].isin(["查無、未剔除", "代號讀不出"])] if len(CP) else CP
    md.append(f"- 市值查無／代號讀不出：{len(unk)} 檔次" + ("：" + "；".join(f"{r['訊號']} {r['名稱']}（{r['判定']}）" for _, r in unk.iterrows()) if len(unk) else ""))
    nod = RW[(RW["段"] == "燈1") & RW["R"].isna()]
    md.append(f"- 價格資料不足：{len(nod)} 檔次" + ("：" + "；".join(f"{r['訊號']} {r['代號']}（{r['狀態']}）" for _, r in nod.iterrows()) if len(nod) else ""))
    tr = RW[(RW["段"] == "燈1") & (RW["H"] == "末") & RW["狀態"].fillna("").str.contains("壞根|下市")]
    md.append(f"- 壞根截斷／下市（燈 1、到末日）：{len(tr)} 檔次" + ("：" + "；".join(f"{r['訊號']} {r['代號']} {r['狀態']} {r['壞根日']}" for _, r in tr.iterrows()) if len(tr) else ""))
    if has:
        md.append("- 兩可訊號：" + ("、".join(SG[SG["兩可"]]["訊號"]) or "無") + "；燈 2 兩可：" + ("、".join(SG[SG["燈2兩可"]]["訊號"]) or "無"))
    if meta.get("有自評欄"):
        md.append("- 判燈者自評知道後來走勢（剔自評知道版剔除）：" + ("、".join(SG[SG["自評知道"]]["訊號"]) or "無"))
    md.append("")
    md += ["## 每訊號一列（照實；訊號等權超額，份；括號＝接續版有差時）", "",
           "| 訊號 | 類 | 版本 | 型 | 主題 | 燈1季 | 入選檔 | 剔除 | 12 月 | 24 月 | 到末日 | 燈2季 | 加碼 2 份（末） | 乙總損益（末） |", "|" + "---|" * 14]
    for _, r in SG.iterrows():
        if r["無點名"]:
            continue

        def cell(H):
            x = r[f"{H}_超額"]; xb = r[f"{H}_xb"]
            if r[f"{H}_未到"]:
                return "未到"
            return f2(x) + (f"（{f2(xb)}）" if np.isfinite(x) and np.isfinite(xb) and abs(x - xb) > 1e-9 else "")
        a2 = r["加碼a_末_超額"]
        md.append(f"| {r['訊號']}{'（兩可）' if r['兩可'] else ''} | {r['類']} | {r['版本']} | {r['型']} | {r['主題']} | {r['燈1季']} | {r['入選檔'] or '—'} | {r['剔除檔'] or '—'} | "
                  f"{cell('12')} | {cell('24')} | {cell('末')} | {r['燈2季'] or '—'} | {f2(2 * a2) if np.isfinite(a2) else '—'} | {f2(r['乙_末'])} |")
    md += ["", "## 異常與註記", ""]
    if any(os.path.basename(x["檔"]) == os.path.basename(SRC_V3) for x in meta["來源"]):
        md += ["- 傳產清單 V23 備註寫「乙版燈1另列V24」，但清單內沒有 V24 列；乙版件數（32 訊號、28 有公司、缺貨 8）與產業 seq44 §一表一致 ⇒ 照清單算、未補 V24。",
               "- V40 公司欄為 1503 士電、但備註寫「無點名（待裁定：05S05 士電『重電受惠台商回流』段落）」⇒ 照公司欄算（不是「無點名」），請產業確認。"]
    if any(os.path.basename(x["檔"]) == os.path.basename(SRC) for x in meta["來源"]):
        md += ["- 傳產清單 v4（產業 seq45）取代 v3：只加「判定把握」「兩可理由」兩欄、改 V23／V40 備註（V40 士電依第 11 條補上、V23 的乙版 V24 依第 24 條刪除），"
               "其餘欄位逐格與 v3 相同 ⇒ 照實版數字應與 v3 相同（本次已逐格驗證，見 v3_compare.txt）。"]
    md += ["- 「兩版」列甲乙兩版數字相同（同一列）。",
           f"- ⚠ 到末日欄受 2025Q4～2026 大盤急漲主導：market_tri 2025-09-30 → 2026-09-24 約 +{(V.tri_at(TRI, '2026-09-24') / V.tri_at(TRI, '2025-09-30') - 1) * 100:.0f}%"
           f"（2025-09-30 {V.tri_at(TRI, '2025-09-30'):.0f}、2026-06-30 {V.tri_at(TRI, '2026-06-30'):.0f}、面板尾 {V.tri_at(TRI, '2026-09-24'):.0f}；逐月平順、非跳點），"
           "傳產同期多半沒跟上 ⇒ 傳產到末日超額大多為負、加碼 2 份到末日全為負；12／24 月欄較不受此段影響。", "",
           (LIMIT.replace("，電子類還沒做", "（此句指傳產部分）") + "　" + LIMIT_E if "電子" in groups else LIMIT)]
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

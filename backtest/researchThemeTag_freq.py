# -*- coding: utf-8 -*-
"""主題標籤能否替營量、營飆加分 seq1（台股策略線 0328，sha b2e6be286b41a9ad；裁定 seq478 §五 核）——【普查標籤頻率表】⛔ 不附任何報酬。
回測線計算子代理，2026-10-26 03:45（台北）起草。前瞻＋描述、⛔ 不判、⛔ 不計 N；三種標籤分開報、⛔ 不合併。
⛔ 不 commit、不改既有檔（策略鎖內營量／營飆程式一字不動、resultsYFallin 只讀）；⛔ 本檔不讀 amt_out／cost／價格（＝ 不碰任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchThemeTag_freq
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchThemeTag_freq_check

═══ 出處 ═══
 營量 v1、營飆 v1 逐筆進場 ＝ backtest/resultsYFallin/trades_W.csv.gz（＝ backtest/researchTurnover.py 同一出處）：世界「主」、帳 YL（營量 v1：無閘、H60、20 檔、relvol）、
    帳 v1（營飆 v1：t−1 大盤閘、H120、10 檔、抽籤 r0 ＝ rerun17.P10_SEED0 那一顆；E1 閘 eq_sha ＝ resultsYF_N）；日期 ＝ 同夾 daily_W.csv.gz 世界「主」t→日期（2015-01-05～2026-09-24；
    t＝2859 為世界尾平倉根、無日期）。
 普查標籤 ＝ /mnt/c/SynologyDrive/跨線信箱/附件-近年燈號普查訊號清單v4_加判定把握_產業分析線-20261025-1830.csv（傳產 44 列）
          ＋ 附件-電子類燈號普查訊號清單v5_產業分析線-20261026-0130.csv（電子 67 列）；複本存輸出夾。
 前瞻標籤 ＝ 附件-前沿研究前瞻紀錄第1期_產業分析線-20261026-0206.md（sha256 前 16 ＝ 30e87e3eb701136f，本檔重算核對；42 家）。

═══ 讀法（寫死於看任何本件數字之前；★＝執行者定〔另一讀法〕）═══
 Q1 母體 ＝ 帳 YL／v1 的每一筆 buy 列（規則欄、非使用者實際欄）；配對出場 ＝ 同代號、t 大於買進 t 的第一筆 sell 列。
    ★ 營飆 v1 有抽籤：用正式回測那一顆 r0（＝ researchTurnover 引用的帳 v1）〔另一讀法：200 顆全部進場、或抽籤前的全部訊號〕。
 Q2 期間 ＝ 進場日 2021-01-01～2026-10-31；世界資料尾 2026-09-24 ⇒ 實際最後進場在 9 月。
    持有狀態（只計件數、不看報酬）：完整 ＝ 出場 t ＝ 買進列 xpos（排程第 60／120 根）；提前 ＝ 出場 t ＜ xpos 且有日期（停止交易強制出場，屬規則出場）；
    未滿 ＝ 出場在世界尾平倉根（無日期）或 xpos 超過資料尾。★ 正式跑：完整＋提前入統計，未滿記「未到」、⛔ 不入分母（件數照報）〔另一讀法：未滿以資料尾收盤結算入列〕。
 Q3 普查標籤（登錄 §二②）：進場日前 8 季內，該股代號出現在燈 1 公司欄（公司1～3，取第一個空白前 4 碼；「無點名」不算）。⛔ 只對同代號，不擴到同主題其他股。
    ★「進場日前 8 季內」＝ 燈1出處日期 d1 滿足 進場日 − 24 個日曆月 ≤ d1 ＜ 進場日（嚴格早於進場日；進場在開盤，同日消息不算）
      〔另一讀法：以「燈1季」計，燈1季落在進場季之前的 8 個完整季度內〕。
    ★ 甲／乙／兩版：三種列全部取聯集（同一代號同一燈 1 只要出現一次即算）〔另一讀法：只取甲版＋兩版、或只取乙版＋兩版〕；甲、乙分版筆數另附一表只供參考、正式跑只用聯集。
    寬鬆 ＝ 判定把握「確定」＋「兩可」全部列；嚴格 ＝ 判定把握「確定」且「判燈者自評知道後來走勢」≠「知道」（「不知道」「不確定」都留）。
    ★ 傳產 v4 沒有「判燈者自評」欄 ⇒ 嚴格版只用「確定」、不剔（＝ researchLampCensus L8「缺此欄照寫不剔」）〔另一讀法：傳產全部當未知而剔除〕。
 Q4 主題組 ＝ 該版標籤為真；非主題組 ＝ 同策略同期其餘進場。一筆可同時對到多個訊號／主題：只算 1 筆，對到的訊號編號與主題全列。
 Q5 同月隨機（登錄 §一）：同策略、同進場月，從該月【全部】進場（含主題組自己）抽與主題組同數量 ★〔另一讀法：只從非主題組抽〕。
    可抽性 ＝ 每月 主題 k_m ≤ 全部 n_m 恆成立；報 k_m＝n_m（隨機組必等於主題組）的月數與其主題筆數、log10 Π C(n_m, k_m)（不同抽法總數）。
    ★ 頻率表的 k_m、n_m 用「完整＋提前」那批（＝ 正式跑真正入統計的那批）；全部進場（含未滿）另列。
 Q6 n_eff：月群 ＝ 主題組有筆的不同進場月數；主題群 ＝ 主題組對到的不同（產業, 主題）數；另報不同代號數。
    ≥30（登錄 §四描述句的筆數條件）＝ 主題組「完整＋提前」筆數 ≥ 30。
 Q7 前瞻標籤：只用進場日以前已凍結的那期；第 1 期 2026-10-26 凍結，前瞻自 2026-11 起 ⇒ 本次 0 個月（每月一行：主題組／全部，⛔ 不附報酬，到 2027-11-30 才算）。
    名單解析 ＝ 附件第二節表格「公司」欄的 4 碼代號，括號內「只當上游對照、不計分」的不算；去重後必須 ＝ 42。
 Q8 盲判標籤（§二③）：本 seq 不做，待 seq2。
輸出 backtest/resultsThemeTag/freq/：entries.csv（每筆進場的標籤，無報酬）、year.csv、month.csv、draw.csv、neff.csv、ver.csv、forward.csv、freq.json、summary.md、run.log、
     signals_input_v4.csv、signals_input_v5.csv
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
os.chdir(REPO)
B = "backtest"
YFA = os.path.join(B, "resultsYFallin")
OUT = os.path.join(B, "resultsThemeTag", "freq")
MB = "/mnt/c/SynologyDrive/跨線信箱"
SRC = {"v4": os.path.join(MB, "附件-近年燈號普查訊號清單v4_加判定把握_產業分析線-20261025-1830.csv"),
       "v5": os.path.join(MB, "附件-電子類燈號普查訊號清單v5_產業分析線-20261026-0130.csv")}
FWD1 = os.path.join(MB, "附件-前沿研究前瞻紀錄第1期_產業分析線-20261026-0206.md")
FWD1_SHA16, FWD1_N = "30e87e3eb701136f", 42
REG = "登錄全文-主題標籤能否替營量營飆加分_主題組對非主題組_前瞻紀錄加描述登錄_台股策略線_seq1_shab2e6be286b41a9ad-4727B-20261026-0328.md"
TIME = "2026-10-26 03:45（台北）"
STRAT = {"營量": "YL", "營飆": "v1"}
HOLD = {"營量": 60, "營飆": 120}
P0, P1 = "2021-01-01", "2026-10-31"
LOOKBACK_MONTHS = 24
COL_KNOW = "判燈者自評知道後來走勢"
LOG: list = []


def log(s=""):
    LOG.append(str(s)); print(s, flush=True)


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


# ═════════════ 進場 ═════════════
def load_calendar():
    d = pd.read_csv(os.path.join(YFA, "daily_W.csv.gz"), usecols=["世界", "帳", "t", "日期"])
    d = d[(d["世界"] == "主") & (d["帳"] == "YL")].sort_values("t")
    assert np.array_equal(d["t"].to_numpy(), np.arange(len(d)))
    return d["日期"].fillna("").astype(str).to_numpy()


def load_entries(cal):
    """每筆 buy 列 → (策略, 代號, 進場 t／日期, 出場 t／日期, xpos, 持有狀態)。⛔ 不讀 amt_out／cost／px。"""
    T = pd.read_csv(os.path.join(YFA, "trades_W.csv.gz"), usecols=["世界", "帳", "side", "t", "sid", "xpos"])
    T = T[T["世界"] == "主"]
    last = max(i for i, x in enumerate(cal) if x)
    rows = []
    for st, acct in STRAT.items():
        A = T[T["帳"] == acct]
        bu, se = A[A["side"] == "buy"], A[A["side"] == "sell"]
        assert len(bu) == len(se), (st, len(bu), len(se))
        sells = {s: np.sort(g["t"].to_numpy(int)) for s, g in se.groupby("sid")}
        used = set()
        for sid, t, xp in zip(bu["sid"].astype(int), bu["t"].astype(int), bu["xpos"].astype(float)):
            s = sells[sid]; k = int(np.searchsorted(s, t, side="right"))
            assert k < len(s), (st, sid, t)
            ts = int(s[k]); assert (sid, ts) not in used; used.add((sid, ts))
            xp = int(xp)
            if cal[ts] == "" or xp > last:
                stt = "未滿"
            elif ts == xp:
                stt = "完整"
            else:
                assert ts < xp, (st, sid, t, ts, xp)
                stt = "提前"
            rows.append({"策略": st, "代號": f"{sid:04d}", "進場t": t, "進場日": cal[t], "出場t": ts, "出場日": cal[ts], "xpos": xp,
                         "持有狀態": stt})
    E = pd.DataFrame(rows)
    assert (E["進場日"] != "").all()
    E = E[(E["進場日"] >= P0) & (E["進場日"] <= P1)].sort_values(["策略", "進場t", "代號"]).reset_index(drop=True)
    E["月"] = E["進場日"].str[:7]; E["年"] = E["進場日"].str[:4]
    return E, last


# ═════════════ 普查標籤 ═════════════
def load_census():
    sig = []
    for k, p in SRC.items():
        d = pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        has_know = COL_KNOW in d.columns
        for _, r in d.iterrows():
            know = r[COL_KNOW].strip() if has_know else ""
            sure = r["判定把握"].strip()
            assert sure in ("確定", "兩可"), (k, r["訊號編號"], sure)
            d1 = r["燈1出處日期"].strip(); assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", d1), (k, r["訊號編號"], d1)
            for c in ("公司1", "公司2", "公司3"):
                v = r[c].strip()
                if not v or v == "無點名":
                    continue
                m = re.match(r"^(\d{4})\s", v); assert m, (k, r["訊號編號"], c, v)
                sig.append({"清單": k, "訊號編號": r["訊號編號"], "版本": r["版本(甲/乙/兩版)"].strip(), "產業": r["產業"].strip(), "主題": r["主題"].strip(),
                            "燈1季": r["燈1季"].strip(), "燈1出處日期": d1, "代號": m.group(1), "判定把握": sure, "自評知道": know,
                            "寬": True, "嚴": (sure == "確定") and (know != "知道")})
    S = pd.DataFrame(sig)
    return S


def lo_bound(d):
    """進場日 − 24 個日曆月（月底對齊：2024-02-29 − 24 月 ＝ 2022-02-28）。"""
    p = pd.Timestamp(d)
    return (p - pd.DateOffset(months=LOOKBACK_MONTHS)).strftime("%Y-%m-%d")


def tag(E, S):
    byid = {c: g for c, g in S.groupby("代號")}
    out = {v: [] for v in ("寬", "嚴")}
    det = {v: [] for v in ("寬", "嚴")}
    for sid, d in zip(E["代號"], E["進場日"]):
        g = byid.get(sid)
        lo = lo_bound(d)
        for v in ("寬", "嚴"):
            if g is None:
                out[v].append(False); det[v].append(""); continue
            h = g[(g[v]) & (g["燈1出處日期"] >= lo) & (g["燈1出處日期"] < d)]
            out[v].append(len(h) > 0)
            det[v].append(";".join(sorted({f"{a}:{b}|{c}／{e}" for a, b, c, e in zip(h["清單"], h["訊號編號"], h["產業"], h["主題"])})))
    for v in ("寬", "嚴"):
        E[f"標籤_{v}"] = out[v]; E[f"對到_{v}"] = det[v]
    # 甲／乙分版（只供參考）
    for ver, keep in (("甲", ("甲", "兩版")), ("乙", ("乙", "兩版"))):
        Sv = S[S["版本"].isin(keep)]
        byv = {c: g for c, g in Sv.groupby("代號")}
        for v in ("寬", "嚴"):
            col = []
            for sid, d in zip(E["代號"], E["進場日"]):
                g = byv.get(sid)
                col.append(bool(g is not None and len(g[(g[v]) & (g["燈1出處日期"] >= lo_bound(d)) & (g["燈1出處日期"] < d)])))
            E[f"參考_{ver}版_{v}"] = col
    return E


# ═════════════ 前瞻名單 ═════════════
def forward_list():
    h = sha16(FWD1)
    txt = open(FWD1, encoding="utf-8").read()
    sec = txt.split("## 二、", 1)[1].split("## 三、", 1)[0]
    codes = set()
    for ln in sec.splitlines():
        if not ln.startswith("|") or ln.startswith("|---") or "| 組 |" in ln:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        comp = re.sub(r"（[^）]*）", "", cells[2])
        codes |= set(re.findall(r"(?<!\d)(\d{4})(?!\d)", comp))
    return h, sorted(codes)


# ═════════════ 表 ═════════════
def lcomb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    log(f"# 主題標籤 seq1 普查標籤頻率表（⛔ 不附報酬）｜{TIME}｜執行 {time.strftime('%Y-%m-%d %H:%M:%S')}（機器時鐘）")
    cal = load_calendar()
    E, last = load_entries(cal)
    log(f"[進場] trades_W 主世界 帳 YL／v1；世界日曆 {cal[0]}～{cal[last]}（t 0～{last}，t{last + 1}＝世界尾平倉根）；期間 {P0}～{P1}")
    S = load_census()
    for k, p in SRC.items():
        shutil.copyfile(p, os.path.join(OUT, f"signals_input_{k}.csv"))
    log(f"[普查] v4 sha16 {sha16(SRC['v4'])}、v5 sha16 {sha16(SRC['v5'])}；燈1公司列 {len(S)}（寬）／{int(S['嚴'].sum())}（嚴）；"
        f"不同代號 寬 {S['代號'].nunique()}、嚴 {S.loc[S['嚴'], '代號'].nunique()}；燈1出處日期 {S['燈1出處日期'].min()}～{S['燈1出處日期'].max()}")
    # 燈1出處日期 是否落在 燈1季內（只報件數）
    q = pd.PeriodIndex(pd.to_datetime(S["燈1出處日期"]), freq="Q").astype(str).str.replace("Q", "Q")
    off = int((q.to_numpy() != S["燈1季"].str.replace("Q", "Q").to_numpy()).sum())
    log(f"[普查] 燈1出處日期不在燈1季內的公司列 {off}（只報、照出處日期算）")
    E = tag(E, S)
    fh, fcodes = forward_list()
    log(f"[前瞻] 第1期 sha16 {fh}（應 {FWD1_SHA16}）；解析代號 {len(fcodes)}（應 {FWD1_N}）")
    assert fh == FWD1_SHA16 and len(fcodes) == FWD1_N
    E.to_csv(os.path.join(OUT, "entries.csv"), index=False, encoding="utf-8")

    J = {"時間": TIME, "登錄": REG, "裁定": "seq478 §五 核", "出處": "backtest/resultsYFallin/trades_W.csv.gz（主世界 帳 YL＝營量 v1、帳 v1＝營飆 v1 r0）＋daily_W.csv.gz 日期",
         "普查sha16": {k: sha16(p) for k, p in SRC.items()}, "前瞻第1期sha16": fh, "前瞻第1期代號數": len(fcodes), "策略": {}}
    yr_rows, mo_rows, dr_rows, ne_rows, ver_rows = [], [], [], [], []
    for st in STRAT:
        Es = E[E["策略"] == st]
        EI = Es[Es["持有狀態"] != "未滿"]
        J["策略"][st] = {"進場筆數": len(Es), "完整": int((Es["持有狀態"] == "完整").sum()), "提前": int((Es["持有狀態"] == "提前").sum()),
                        "未滿": int((Es["持有狀態"] == "未滿").sum()), "進場月數": int(Es["月"].nunique()), "持有": f"H{HOLD[st]}"}
        for v in ("寬", "嚴"):
            c = f"標籤_{v}"
            a_all, a_in = int(Es[c].sum()), int(EI[c].sum())
            J["策略"][st][v] = {"主題組_全部": a_all, "主題組_入統計": a_in, "非主題組_全部": len(Es) - a_all, "非主題組_入統計": len(EI) - a_in,
                               "主題比例_全部": a_all / len(Es) if len(Es) else None, "主題比例_入統計": a_in / len(EI) if len(EI) else None,
                               "達30筆": a_in >= 30}
            # 年
            for y, g in Es.groupby("年"):
                gi = g[g["持有狀態"] != "未滿"]
                yr_rows.append({"策略": st, "版": v, "年": y, "全部": len(g), "主題組": int(g[c].sum()), "非主題組": int((~g[c]).sum()),
                                "主題組月數": int(g.loc[g[c], "月"].nunique()), "非主題組月數": int(g.loc[~g[c], "月"].nunique()),
                                "入統計_主題組": int(gi[c].sum()), "入統計_非主題組": int((~gi[c]).sum()), "未滿": int((g["持有狀態"] == "未滿").sum())})
            # 月 ＋ 可抽性
            lc, deg, degk = 0.0, 0, 0
            for m, g in Es.groupby("月"):
                gi = g[g["持有狀態"] != "未滿"]
                n, k = len(gi), int(gi[c].sum())
                mo_rows.append({"策略": st, "版": v, "月": m, "全部": len(g), "主題組": int(g[c].sum()), "入統計_全部": n, "入統計_主題組": k,
                                "未滿": len(g) - n})
                if k > 0:
                    lc += lcomb(n, k) / math.log(10)
                    if k == n:
                        deg += 1; degk += k
            km = Es.loc[Es["持有狀態"] != "未滿"].groupby("月")[c].sum()
            dr_rows.append({"策略": st, "版": v, "主題組有筆月數": int((km > 0).sum()), "k＝n 月數（隨機組必＝主題組）": deg, "k＝n 月的主題筆數": degk,
                            "log10 不同抽法數": round(lc, 3), "可抽（k≤n 每月成立）": True,
                            "主題組有筆月的 k 中位": float(km[km > 0].median()) if (km > 0).any() else None,
                            "主題組有筆月的 n 中位": float(Es.loc[Es["持有狀態"] != "未滿"].groupby("月").size()[km > 0].median()) if (km > 0).any() else None})
            # n_eff
            th = EI[EI[c]]
            themes = set()
            for s in th[f"對到_{v}"]:
                for z in s.split(";"):
                    if z:
                        themes.add(z.split("|", 1)[1])
            ne_rows.append({"策略": st, "版": v, "主題組_入統計": len(th), "月群": int(th["月"].nunique()), "主題群（產業／主題）": len(themes),
                            "不同代號": int(th["代號"].nunique()), "非主題組月群": int(EI.loc[~EI[c], "月"].nunique()),
                            "全部進場月群": int(EI["月"].nunique()), "達30筆": len(th) >= 30,
                            "主題群清單": "；".join(sorted(themes))})
            J["策略"][st][v].update({"月群": int(th["月"].nunique()), "主題群": len(themes), "不同代號": int(th["代號"].nunique())})
            for ver in ("甲", "乙"):
                cc = f"參考_{ver}版_{v}"
                ver_rows.append({"策略": st, "版": v, "甲乙": ver, "主題組_全部": int(Es[cc].sum()), "主題組_入統計": int(EI[cc].sum())})
    YR, MO, DR, NE, VR = (pd.DataFrame(x) for x in (yr_rows, mo_rows, dr_rows, ne_rows, ver_rows))
    YR.to_csv(os.path.join(OUT, "year.csv"), index=False); MO.to_csv(os.path.join(OUT, "month.csv"), index=False)
    DR.to_csv(os.path.join(OUT, "draw.csv"), index=False); NE.to_csv(os.path.join(OUT, "neff.csv"), index=False)
    VR.to_csv(os.path.join(OUT, "ver.csv"), index=False)
    FW = pd.DataFrame(columns=["月", "策略", "前瞻期別", "主題組", "全部"])
    FW.to_csv(os.path.join(OUT, "forward.csv"), index=False)
    # 每月筆數分布（全部進場）
    md = {}
    for st in STRAT:
        g = MO[(MO["策略"] == st) & (MO["版"] == "寬")]
        md[st] = {"月數": len(g), "每月全部 最小": int(g["全部"].min()), "中位": float(g["全部"].median()), "最大": int(g["全部"].max())}
        for v in ("寬", "嚴"):
            gv = MO[(MO["策略"] == st) & (MO["版"] == v)]
            md[st][f"主題組 0 筆的月數_{v}"] = int((gv["主題組"] == 0).sum())
            md[st][f"每月主題組 最大_{v}"] = int(gv["主題組"].max())
    J["每月分布"] = md
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    write_md(J, YR, DR, NE, VR, md)
    log(f"[完成] {time.time() - t0:.1f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def pct(a, b):
    return f"{a / b * 100:.1f}%" if b else "—"


def write_md(J, YR, DR, NE, VR, md):
    L = [f"# 主題標籤能否替營量、營飆加分 seq1｜普查標籤頻率表（⛔ 不附任何報酬）",
         f"<p align=\"right\">{TIME}・回測線計算子代理</p>", "",
         "> 前瞻＋描述、⛔ 不判、⛔ 不計 N（裁定 seq478 §五）。本表只有筆數，⛔ 沒有任何報酬數字。三種標籤分開報，本表只含②普查標籤（①前瞻 0 個月、③盲判待 seq2）。", "",
         "## 一、總表（期間 2021-01～2026-09 進場；世界資料尾 2026-09-24）", "",
         "| 策略 | 版 | 進場筆數 | 主題組 | 比例 | 入統計（完整＋提前） | 其中主題組 | 比例 | 未滿 | 月群 n_eff | 主題群 n_eff | 不同代號 | 主題組 ≥30 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for st, s in J["策略"].items():
        nin = s["完整"] + s["提前"]
        for v in ("寬", "嚴"):
            x = s[v]
            L.append(f"| {st} | {'寬鬆' if v == '寬' else '嚴格'} | {s['進場筆數']} | {x['主題組_全部']} | {pct(x['主題組_全部'], s['進場筆數'])} | {nin} | "
                     f"{x['主題組_入統計']} | {pct(x['主題組_入統計'], nin)} | {s['未滿']} | {x['月群']} | {x['主題群']} | {x['不同代號']} | "
                     f"{'達到' if x['達30筆'] else '未達'} |")
    L += ["", "- 「入統計」＝ 持有滿規則天數（完整）或停止交易強制出場（提前）；「未滿」＝ 出場落在世界尾平倉根，正式跑記「未到」、不入分母（★Q2）。",
          "- 營飆＝正式回測抽籤 r0 那一顆（★Q1）。", "",
          "## 二、依年份（主題組／非主題組筆數、月數；全部進場）", "",
          "| 策略 | 版 | 年 | 全部 | 主題組 | 非主題組 | 主題組月數 | 非主題組月數 | 未滿 |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in YR.iterrows():
        L.append(f"| {r['策略']} | {'寬鬆' if r['版'] == '寬' else '嚴格'} | {r['年']} | {r['全部']} | {r['主題組']} | {r['非主題組']} | {r['主題組月數']} | {r['非主題組月數']} | {r['未滿']} |")
    L += ["", "## 三、每月筆數分布（全部進場；逐月見 month.csv）", "", "| 策略 | 進場月數 | 每月筆數 最小／中位／最大 | 主題組 0 筆的月數 寬／嚴 | 單月主題組最多 寬／嚴 |", "|---|---|---|---|---|"]
    for st, m in md.items():
        L.append(f"| {st} | {m['月數']} | {m['每月全部 最小']}／{m['中位']:g}／{m['最大']} | {m['主題組 0 筆的月數_寬']}／{m['主題組 0 筆的月數_嚴']} | "
                 f"{m['每月主題組 最大_寬']}／{m['每月主題組 最大_嚴']} |")
    L += ["", "## 四、同月隨機對照的可抽性（入統計那批）", "", "| 策略 | 版 | 主題組有筆月數 | k＝n 月數（隨機必＝主題） | 那些月的主題筆數 | log10 不同抽法數 | 有筆月 k 中位／n 中位 |", "|---|---|---|---|---|---|---|"]
    for _, r in DR.iterrows():
        kk = "—" if r["主題組有筆月的 k 中位"] is None or pd.isna(r["主題組有筆月的 k 中位"]) else f"{r['主題組有筆月的 k 中位']:g}／{r['主題組有筆月的 n 中位']:g}"
        L.append(f"| {r['策略']} | {'寬鬆' if r['版'] == '寬' else '嚴格'} | {r['主題組有筆月數']} | {r['k＝n 月數（隨機組必＝主題組）']} | {r['k＝n 月的主題筆數']} | {r['log10 不同抽法數']} | {kk} |")
    L += ["", "- 每月主題 k ≤ 全部 n 恆成立 ⇒ 同月同數量隨機一定抽得出；k＝n 的月份隨機組與主題組相同（該月不提供對照）。", "",
          "## 五、主題群（n_eff 另一單位）", ""]
    for _, r in NE.iterrows():
        L.append(f"- {r['策略']}・{'寬鬆' if r['版'] == '寬' else '嚴格'}（{r['主題群（產業／主題）']} 群）：{r['主題群清單'] or '—'}")
    L += ["", "## 六、甲／乙分版筆數（只供參考；正式跑只用聯集 ★Q3）", "", "| 策略 | 版 | 甲版（甲＋兩版） 全部／入統計 | 乙版（乙＋兩版） 全部／入統計 |", "|---|---|---|---|"]
    for (st, v), g in VR.groupby(["策略", "版"], sort=False):
        a = g[g["甲乙"] == "甲"].iloc[0]; b = g[g["甲乙"] == "乙"].iloc[0]
        L.append(f"| {st} | {'寬鬆' if v == '寬' else '嚴格'} | {a['主題組_全部']}／{a['主題組_入統計']} | {b['主題組_全部']}／{b['主題組_入統計']} |")
    L += ["", "## 七、前瞻標籤（①）", "",
          f"- 第 1 期 sha256 前 16 ＝ {J['前瞻第1期sha16']}（相符）、解析 {J['前瞻第1期代號數']} 家（相符）。前瞻自 2026-11 起，**目前 0 個月**；之後每月一行（主題組／全部），⛔ 不附報酬，2027-11-30 才描述。", "",
          "## 八、必附", "",
          "- ⚠ 普查只涵蓋 11 個產業（傳產 6、電子 5），蒐集時有事後偏差；營量、營飆這段歷史本線看過 ⇒ 只描述。",
          "- ⚠ 普查燈 1 出處日期最晚 2024-09；8 季回看 ⇒ 2025 起進場被標到的機會逐年縮小（看年份表）。",
          "- 營飆 2022 年 0 筆進場：r0 那一顆 2022 無買進日（resultsYFallin/years.csv 同；t−1 大盤閘），非本表漏列。",
          "- 寬嚴兩版照標，⛔ 不寫成「保守～樂觀」。",
          "- ★ 讀法（Q1～Q8）全文寫在 backtest/researchThemeTag_freq.py 檔頭，寫於看任何數字之前。"]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())

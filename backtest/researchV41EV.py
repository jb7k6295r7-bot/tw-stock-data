# -*- coding: utf-8 -*-
"""大漲主題框架 v4.1 新設定重算：期望值、兩平命中率、停用張數（產業分析線 seq30／seq34；描述、⛔ 不判定、不計 N）——回測線計算子代理。
⚠ 事後挑的贏家與失敗樣本 ⇒ 只描述，⛔ 不是期望值的證據。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices、log）、researchShortageExit（seam_open）、researchTopSell_freq（raw_close）
   ⛔ 只 import；結算與接續的寫法照 researchLampTrade（Q1、Q5、Q5′、Q7）原式抄。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchV41EV [--market TW|US|ALL]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchV41EV_check
輸入：backtest/resultsV41EV/cases_input.csv（附件「進場候選K1至K4_56案與K1」原檔複本，56 列）
      backtest/resultsV41EV/peers_input.csv（★ 選用：同主題營收占比前 3 名；欄 id,代號,名次,占比出處）——
      ⛔ 本次在本機找不到產業線 p3_contrarian/peers 檔 ⇒ 無此檔 ⇒ 每個主題只有代表股（燈 1 事件點名的公司），主題值＝代表股值。
輸出 backtest/resultsV41EV/：table.csv（每檔×判決月）、themes.csv（每主題一列）、summary.md、main.json、run.log

═══ 讀法（★＝執行者定）═══
 V1 台股價格 ＝ researchLampTrade Q1 同一面板（PIN 9b0e9882572c；還原含息收盤 C、還原開盤 O 含接縫倍數；壞根 BAD 同定義）。
 V2 進場 ＝ 燈亮月下一個月第一個交易日的還原開盤（無成交 ⇒ 順延到下一個有成交開盤，日數照報）。美股同（Yahoo 還原開盤
    ＝ open × adjclose ÷ close）。
 V3 判決日 ＝ 進場日 ＋ H 個日曆月（H＝60 主表、72 副欄；另附 24、36 月供對照舊值與停用 (b)）當天或之前最後一個交易日的還原收盤；
    該日超出資料尾 ⇒ 結算到資料尾最後有效收盤、標「未到判決日」（件數照報）。持有期間 ⛔ 不模擬 v4 出場 ①～⑤（新聞判斷）。
 V4 跨壞根 ⇒ 結算在第一個壞根前一根有效收盤、標「⚠壞根截斷」；接續版（減資／面額變更以原始價接起）另欄（照 LampTrade Q5′）。
    下市（最後有效 K 棒距資料尾 ≥5 日且早於判決位置）⇒ 最後有效收盤、標「下市結算」。美股：連續 ≥5 交易日無 K 棒 ⇒ 壞根（同 us_data GAP_BREAK_DAYS）。
 V5 R ＝ 判決價 ÷ 進場價 − 1 − 成本；台股 0.585% 來回（手續費 0.1425%×2＋證交稅 0.3%），美股 0.05%／邊（0.1% 來回）。單位「份」＝每檔 1 份的損益倍數。
 V6 大盤 ＝ 台股 data/history/market_tri.csv（報酬指數）；美股 ^SP500TR（us-stock-data data/macro/yahoo_SP500TR.csv adjclose）。
    基準 ＝ 進場日前一交易日收盤 → 判決（或截斷）日收盤；超額 ＝ R − 大盤。大盤不扣成本。
 V7 主題值 ★ ＝ 同主題各檔（最多 3 檔）R 等權平均（1 個主題＝1 個獨立樣本）；合計 ＝ 各檔 R 之和（份）。另附「每檔各算 1 張」版。
 V8 兩平 p* ＝ −L ÷ (W − L)（W＝贏家組平均或中位，L＝反例組同口徑；L ≥ 0 ⇒「反例為正、兩平不適用」）；
    停用張數 n ＝ ⌈ln 0.1 ÷ ln(1 − p*)⌉；反例 μ、s（樣本標準差 ddof=1）與門檻 μ − 1.28·s／√8（v4.1 第七節 (b)）。
 V9 美股：us-stock-data origin/main data/prices_yahoo/<T>.csv（⛔ 不輸出價格，只輸出 R、日期、名稱）；查無檔或燈亮早於資料起點
    （約 2015-12）⇒「資料不足」（件數照報、不進統計）。
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SE             # noqa: E402
from backtest import researchTopSell_freq as TS             # noqa: E402

OUT = "backtest/resultsV41EV"
INP = os.path.join(OUT, "cases_input.csv")
PEERS = os.path.join(OUT, "peers_input.csv")
PIN = "9b0e9882572c"
COST_TW = 0.00585
COST_US = 0.001
HS = (24, 36, 60, 72)
US_REPO = os.path.expanduser("~/us-stock-data")
WARN = "事後挑的贏家與失敗樣本 ⇒ 只描述，⛔ 不是期望值的證據"
LOG = RT.LOG
log = RT.log


def gshow(path, repo, ref="origin/main"):
    t = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


def code_of(row):
    s = row["公司"].strip()
    if row["市場"] == "TW":
        m = re.search(r"(\d{4})\s*$", s)
        return m.group(1) if m else None
    m = re.match(r"^([A-Z][A-Z.\-]*)（", s)
    return m.group(1) if m else None


def load_members(CS):
    """每個案例的成員：代表股（名次 0）＋ peers_input.csv（若有）。回 {id: [(代號, 角色), ...]}。"""
    mem = {r["id"]: [(code_of(r), "代表股")] for _, r in CS.iterrows()}
    src = "無 peers_input.csv ⇒ 只有代表股"
    if os.path.exists(PEERS):
        P = pd.read_csv(PEERS, dtype=str, keep_default_na=False)
        for _, p in P.iterrows():
            lst = mem[p["id"]]
            if p["代號"] not in [c for c, _ in lst] and len(lst) < 3:
                lst.append((p["代號"], f"同業{p.get('名次', '')}"))
        src = f"peers_input.csv {len(P)} 列"
    return mem, src


# ═════════════ 台股 ═════════════
def tw_engine():
    sha, DN, MD = RT.ensure_data(PIN)
    PX = RT.prices(sha, DN, 3)
    O, nseam = SE.seam_open(PX)
    t = subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout
    T = pd.read_csv(io.BytesIO(t)); T["date"] = pd.to_datetime(T["date"])
    T = T.dropna().drop_duplicates("date").sort_values("date").set_index("date")["close"]
    return sha, PX, O, nseam, T


def tri_at(T, d):
    k = int(T.index.searchsorted(pd.Timestamp(d), "right")) - 1
    return float(T.iloc[k])


def tw_rows(CS, mem, eng):
    sha, PX, O, nseam, T = eng
    CAL, ix, C, BAD, VP, LASTV, TRD = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"], PX["TRD"]
    CEND = len(CAL) - 1
    ADJ = {}

    def lastvalid_le(i, x):
        vp = VP[i]; k = int(np.searchsorted(vp, x, "right")) - 1
        return int(vp[k]) if k >= 0 else -1

    def opened(i, p):
        return bool(TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p]))

    def adj_events(sid):
        if sid not in ADJ:
            t = subprocess.run(["git", "show", f"{sha}:data/adj/{sid}.csv"], capture_output=True)
            ADJ[sid] = {} if t.returncode != 0 else {pd.Timestamp(r["date"]): r for _, r in pd.read_csv(io.BytesIO(t.stdout), dtype=str).iterrows()
                                                     if r["event"] in ("reduce", "parvalue")}
        return ADJ[sid]

    def bridge(i, sid, e, xe):
        """LampTrade Q5′ 原式：回 (接續倍數 at xe, 註) 或 (None, 原因)。"""
        k = 1.0; info = []
        for b in (e + 1 + np.flatnonzero(BAD[i, e + 1:xe + 1])):
            b = int(b); ev = adj_events(sid).get(CAL[b]); pb = lastvalid_le(i, b - 1)
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

    rows = []
    for _, r in CS[CS["市場"] == "TW"].iterrows():
        for sid, role in mem[r["id"]]:
            base = {"id": r["id"], "市場": "TW", "結果": r["結果"], "型": r["型"], "產業": r["產業"], "代表股": r["公司"], "代號": sid, "角色": role, "燈亮月": r["燈亮月"]}
            if sid not in ix:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": "資料不足(面板查無)"})
                continue
            i = ix[sid]
            p0 = int(CAL.searchsorted((pd.Period(r["燈亮月"], "M") + 1).to_timestamp()))
            e = p0
            while e <= CEND and not opened(i, e):
                e += 1
            if e > CEND:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": "資料不足(進場前無成交)"})
                continue
            P0 = float(O[i, e]); tri0 = tri_at(T, CAL[e - 1])
            lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
            for H in HS:
                tgt = CAL[e] + pd.DateOffset(months=H)
                notyet = tgt > CAL[CEND]
                x = CEND if notyet else int(CAL.searchsorted(tgt, "right")) - 1
                bb = np.flatnonzero(BAD[i, e + 1:x + 1])
                st = "未到判決日" if notyet else "完整"; bad_d = ""
                if len(bb):
                    b = e + 1 + int(bb[0]); bad_d = str(CAL[b].date()); xe = lastvalid_le(i, b - 1); st = "⚠壞根截斷" + ("＋未到判決日" if notyet else "")
                elif delist and lastv < x:
                    xe = lastv; st = "下市結算"
                else:
                    xe = lastvalid_le(i, x)
                R = float(C[i, xe] / P0 - 1 - COST_TW); M = tri_at(T, CAL[xe]) / tri0 - 1
                row = {**base, "H月": H, "進場日": str(CAL[e].date()), "進場順延日": e - p0, "判決目標日": str(tgt.date()), "結算日": str(CAL[xe].date()),
                       "狀態": st, "壞根日": bad_d, "R": R, "大盤": M, "超額": R - M}
                # 接續版（只對壞根截斷格）
                if len(bb):
                    xq = lastv if (delist and lastv < x) else lastvalid_le(i, x)
                    k, note = bridge(i, sid, e, xq)
                    row["接續註"] = note
                    if k is not None:
                        Rb = float(C[i, xq] * k / P0 - 1 - COST_TW); Mb = tri_at(T, CAL[xq]) / tri0 - 1
                        row.update({"接續R": Rb, "接續大盤": Mb, "接續超額": Rb - Mb, "接續結算日": str(CAL[xq].date())})
                rows.append(row)
    return rows


# ═════════════ 美股 ═════════════
def us_rows(CS, mem):
    sha = subprocess.run(["git", "-C", US_REPO, "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    G = pd.read_csv(io.BytesIO(gshow("data/macro/yahoo_SP500TR.csv", US_REPO)), dtype={"date": str})
    G["date"] = pd.to_datetime(G["date"]); G["adjclose"] = pd.to_numeric(G["adjclose"], errors="coerce")
    G = G[G["adjclose"] > 0].drop_duplicates("date").sort_values("date").set_index("date")["adjclose"]
    GS = pd.read_csv(io.BytesIO(gshow("data/macro/yahoo_GSPC.csv", US_REPO)), dtype={"date": str})
    UCAL = pd.DatetimeIndex(pd.to_datetime(GS["date"])).sort_values().unique()
    rows = []; info = {"us_sha": sha, "SP500TR": f"{G.index[0].date()}～{G.index[-1].date()}"}

    def tr_at(d):
        k = int(G.index.searchsorted(pd.Timestamp(d), "right")) - 1
        return float(G.iloc[k])

    for _, r in CS[CS["市場"] == "US"].iterrows():
        for tk, role in mem[r["id"]]:
            base = {"id": r["id"], "市場": "US", "結果": r["結果"], "型": r["型"], "產業": r["產業"], "代表股": r["公司"], "代號": tk or "", "角色": role, "燈亮月": r["燈亮月"]}
            raw = gshow(f"data/prices_yahoo/{tk}.csv", US_REPO) if tk else None
            if raw is None:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": "資料不足(私有庫查無此檔)"})
                continue
            P = pd.read_csv(io.BytesIO(raw), dtype={"date": str}); P["date"] = pd.to_datetime(P["date"])
            for c in ("open", "close", "adjclose"):
                P[c] = pd.to_numeric(P[c], errors="coerce")
            P = P[(P["close"] > 0) & (P["adjclose"] > 0) & (P["open"] > 0)].drop_duplicates("date").sort_values("date").reset_index(drop=True)
            ent = (pd.Period(r["燈亮月"], "M") + 1).to_timestamp()
            if ent < P["date"].iloc[0]:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": f"資料不足(燈亮早於資料起點 {P['date'].iloc[0].date()})"})
                continue
            cal = UCAL[(UCAL >= P["date"].iloc[0])]
            pos = {d: q for q, d in enumerate(cal)}
            Pp = P[P["date"].isin(pos)].copy(); Pp["q"] = Pp["date"].map(pos)
            q = Pp["q"].to_numpy(); gapbad = set(q[1:][np.diff(q) - 1 >= 5])   # 連續 ≥5 交易日無 K 棒 ⇒ 壞根
            e_i = int(Pp["date"].searchsorted(ent))
            e_row = Pp.iloc[e_i]; P0 = float(e_row["open"] * e_row["adjclose"] / e_row["close"])
            e_d = e_row["date"]; prev = cal[pos[e_d] - 1] if pos[e_d] > 0 else e_d
            tr0 = tr_at(prev); last_d = Pp["date"].iloc[-1]
            delist = (UCAL[-1] - last_d).days > 10
            for H in HS:
                tgt = e_d + pd.DateOffset(months=H)
                notyet = tgt > last_d and not delist
                sub = Pp[(Pp["date"] > e_d) & (Pp["date"] <= tgt)]
                st = "未到判決日" if notyet else "完整"; bad_d = ""
                bq = [qq for qq in sub["q"] if qq in gapbad]
                if bq:
                    bad_d = str(cal[bq[0]].date()); sub = sub[sub["q"] < bq[0]]; st = "⚠壞根截斷" + ("＋未到判決日" if notyet else "")
                elif delist and last_d < tgt:
                    st = "下市結算"
                xr = sub.iloc[-1] if len(sub) else e_row
                R = float(xr["adjclose"] / P0 - 1 - COST_US); M = tr_at(xr["date"]) / tr0 - 1
                rows.append({**base, "H月": H, "進場日": str(e_d.date()), "進場順延日": int(pos[e_d] - int(np.searchsorted(cal, ent))),
                             "判決目標日": str(tgt.date()), "結算日": str(xr["date"].date()), "狀態": st, "壞根日": bad_d, "R": R, "大盤": M, "超額": R - M})
    return rows, info


# ═════════════ 統計 ═════════════
def themes(TB):
    ok = TB[TB["R"].notna()]
    g = ok.groupby(["市場", "id", "H月"])
    TH = g.agg(結果=("結果", "first"), 型=("型", "first"), 產業=("產業", "first"), 代表股=("代表股", "first"), 燈亮月=("燈亮月", "first"),
               檔數=("代號", "size"), 各檔=("代號", lambda s: "／".join(s)), 等權R=("R", "mean"), 合計R=("R", "sum"), 等權大盤=("大盤", "mean"),
               等權超額=("超額", "mean"), 合計超額=("超額", "sum"),
               未到=("狀態", lambda s: int(s.str.contains("未到").any())), 截斷=("狀態", lambda s: int(s.str.contains("壞根").any()))).reset_index()
    rep = ok[ok["角色"] == "代表股"].set_index(["市場", "id", "H月"])
    TH["代表股R"] = TH.set_index(["市場", "id", "H月"]).index.map(rep["R"]).to_numpy()
    TH["代表股超額"] = TH.set_index(["市場", "id", "H月"]).index.map(rep["超額"]).to_numpy()
    # 接續版主題超額（壞根格換接續值）
    if "接續超額" in ok:
        xb = ok["接續超額"].where(ok["狀態"].str.contains("壞根") & ok["接續超額"].notna(), ok["超額"])
        TH["接續等權超額"] = TH.set_index(["市場", "id", "H月"]).index.map(ok.assign(xb=xb).groupby(["市場", "id", "H月"])["xb"].mean()).to_numpy()
    else:
        TH["接續等權超額"] = TH["等權超額"]
    return TH


def be(W, L):
    if not (np.isfinite(W) and np.isfinite(L)):
        return np.nan, np.nan, "不可算"
    if L >= 0:
        return np.nan, np.nan, "反例平均為正、兩平不適用" if L > 0 else "反例為 0、兩平不適用"
    if W <= 0:
        return np.nan, np.nan, "贏家不為正、無兩平"
    p = -L / (W - L)
    return p, math.ceil(math.log(0.1) / math.log(1 - p)), ""


def stats(TH, TB):
    out = []
    for mk in ("TW", "US"):
        for H in HS:
            for unit, D, col in (("主題", TH, None), ("每檔", TB[TB["R"].notna()], None)):
                d = D[(D["市場"] == mk) & (D["H月"] == H)]
                for met in ("超額", "R", "接續超額"):
                    if met == "接續超額" and unit != "主題":
                        continue
                    c = ({"超額": "等權超額", "R": "等權R", "接續超額": "接續等權超額"}[met] if unit == "主題" else met)
                    w = d[d["結果"] == "大漲"][c].astype(float); l = d[d["結果"] == "失敗"][c].astype(float)
                    rec = {"市場": mk, "H月": H, "樣本單位": unit, "量": met, "贏家n": len(w), "反例n": len(l),
                           "贏家平均": w.mean(), "贏家中位": w.median(), "反例平均": l.mean(), "反例中位": l.median(),
                           "反例μ": l.mean(), "反例s": l.std(ddof=1) if len(l) > 1 else np.nan}
                    rec["門檻μ−1.28s/√8"] = rec["反例μ"] - 1.28 * rec["反例s"] / math.sqrt(8) if np.isfinite(rec["反例s"]) else np.nan
                    for k in ("平均", "中位"):
                        p, n, why = be(rec[f"贏家{k}"], rec[f"反例{k}"])
                        rec[f"p*_{k}"] = p; rec[f"n_{k}"] = n; rec[f"註_{k}"] = why
                    if unit == "主題":
                        u = d[d["結果"] == "大漲"]; rec["贏家代表股平均"] = u["代表股R" if met == "R" else "代表股超額"].mean()
                        rec["贏家代表股中位"] = u["代表股R" if met == "R" else "代表股超額"].median()
                        rec["未到判決日主題數"] = int(d["未到"].sum()); rec["壞根截斷主題數"] = int(d["截斷"].sum())
                    out.append(rec)
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--market", default="ALL"); a = ap.parse_args()
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    CS = pd.read_csv(INP, dtype=str, keep_default_na=False)
    if len(CS) != 56:
        raise SystemExit(f"⛔ 附件列數 {len(CS)} ≠ 56")
    mem, src = load_members(CS)
    log(f"[成員] {src}")
    rows = []; meta = {"成員來源": src}
    if a.market in ("TW", "ALL"):
        eng = tw_engine(); meta["tw_sha"] = eng[0]; meta["tw資料尾"] = str(eng[1]["CAL"][-1].date()); meta["接縫開盤倍數檔數"] = eng[3]
        rows += tw_rows(CS, mem, eng); log(f"[台股] 完成 {time.time() - t0:.0f}s")
    if a.market in ("US", "ALL"):
        ur, ui = us_rows(CS, mem); rows += ur; meta.update(ui); log(f"[美股] 完成 {time.time() - t0:.0f}s")
    TB = pd.DataFrame(rows)
    cols = ["id", "市場", "結果", "型", "產業", "代表股", "代號", "角色", "燈亮月", "H月", "進場日", "進場順延日", "判決目標日", "結算日", "狀態", "壞根日",
            "R", "大盤", "超額", "接續R", "接續大盤", "接續超額", "接續結算日", "接續註"]
    TB = TB.reindex(columns=cols)
    TB.to_csv(os.path.join(OUT, "table.csv"), index=False, encoding="utf-8-sig")
    TH = themes(TB); TH.to_csv(os.path.join(OUT, "themes.csv"), index=False, encoding="utf-8-sig")
    ST = stats(TH, TB); ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")
    write_md(TB, TH, ST, meta)
    MJ = {"性質": "v4.1 新設定重算（描述、不判定、不計 N）", "警語": WARN, "請求": "產業分析線 seq30、seq34", **meta,
          "列數": len(TB), "可算列": int(TB["R"].notna().sum()), "狀態計數": {f"{k[0]}|{k[1]}|{k[2]}": int(v) for k, v in TB.groupby(["市場", "H月"])["狀態"].value_counts().items()},
          "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: str(o) if not isinstance(o, (np.floating, np.integer)) else (None if not np.isfinite(o) else float(o)))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")


def f2(v):
    return "—" if v is None or not np.isfinite(v) else f"{v:+.2f}"


def pc(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.1f}%"


def write_md(TB, TH, ST, meta):
    md = [f"{WARN}", "", "# 大漲主題框架 v4.1 新設定重算：期望值、兩平命中率、停用張數（產業分析線 seq30／seq34）", "",
          "- 描述、⛔ 不判定、不計 N、不改任何規則。單位「份」＝每檔 1 份的損益倍數（R＝判決還原價÷進場還原價−1，含息、扣成本：台股 0.585% 來回、美股 0.05%／邊）。",
          "- 進場＝燈亮月下一個月第一個交易日還原開盤；判決日＝進場日＋60 個月（主表）／72 個月（副欄）當天或之前最後一個交易日還原收盤；另附 24、36 月。"
          "資料不夠 ⇒ 結算到資料尾、標「未到判決日」。持有期間不模擬 v4 出場 ①～⑤。",
          "- 大盤：台股 data/history/market_tri.csv（報酬指數）、美股 ^SP500TR；進場前一交易日收盤→結算日收盤；超額＝R−大盤。",
          f"- ⛔ 成員：{meta['成員來源']}。產業線說的同業名單「p3_contrarian/peers」在本機（Temp 各 session scratchpad、投資\\產業研究用、Obsidian、WSL、Claude app 目錄、全部對話紀錄）都找不到 ⇒ "
          "**本版每個主題只有代表股（燈 1 事件點名的公司），主題值＝代表股值；「同主題前 3 名等權」還不能算**，待產業線轉檔（peers_input.csv）後重跑即補。",
          "- 口徑（回測線定）：**同一主題的 3 檔算 1 個獨立樣本**（主題內等權平均＝該主題的值）；另附「每檔各算 1 張」版（本版兩者相同）。",
          "- 兩平 p*＝−L÷(W−L)；停用張數 n＝⌈ln0.1÷ln(1−p*)⌉；反例 μ、s（ddof=1）、門檻 μ−1.28·s／√8。",
          f"- 資料：台股 sha {str(meta.get('tw_sha', ''))[:12]}（面板尾 {meta.get('tw資料尾', '')}）；美股 us-stock-data {str(meta.get('us_sha', ''))[:12]}（⛔ 本檔不放美股價格，只放 R、日期、名稱）。", ""]
    dl = TB[TB["進場順延日"].fillna(0) > 0].drop_duplicates("id")
    md.append("- 進場順延（燈亮次月首日無成交）：" + ("；".join(f"{r.id} {r.代號} 順延 {int(r.進場順延日)} 個交易日到 {r.進場日}" for r in dl.itertuples()) or "無"))
    nd = TB[TB["R"].isna()].drop_duplicates("id")
    md.append(f"- 資料不足（不進統計）：{len(nd)} 案——" + "；".join(f"{r.id} {r.代表股}（{r.結果}，{r.狀態}）" for r in nd.itertuples()))
    md.append("")
    for H in (60, 72, 36, 24):
        md += [f"## 彙總：{H} 個月（主題為單位；超額＝對大盤含息，括號為原始 R）", "",
               "| 市場 | 贏家 n | 贏家平均 | 贏家中位 | 反例 n | 反例平均 | 反例中位 | p* 平均口徑 | n 平均 | p* 中位口徑 | n 中位 | 反例 μ | s | 門檻 | 未到判決日主題 | 壞根截斷主題 |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for mk in ("TW", "US"):
            s = ST[(ST["市場"] == mk) & (ST["H月"] == H) & (ST["樣本單位"] == "主題") & (ST["量"] == "超額")]
            r_ = ST[(ST["市場"] == mk) & (ST["H月"] == H) & (ST["樣本單位"] == "主題") & (ST["量"] == "R")]
            if not len(s):
                continue
            s = s.iloc[0]; r_ = r_.iloc[0]
            pa = pc(s["p*_平均"]) if np.isfinite(s["p*_平均"]) else s["註_平均"]
            pm = pc(s["p*_中位"]) if np.isfinite(s["p*_中位"]) else s["註_中位"]
            md.append(f"| {mk} | {s['贏家n']} | {f2(s['贏家平均'])}（{f2(r_['贏家平均'])}） | {f2(s['贏家中位'])}（{f2(r_['贏家中位'])}） | {s['反例n']} | "
                      f"{f2(s['反例平均'])}（{f2(r_['反例平均'])}） | {f2(s['反例中位'])}（{f2(r_['反例中位'])}） | {pa} | {s['n_平均'] if np.isfinite(s['p*_平均']) else '—'} | "
                      f"{pm} | {s['n_中位'] if np.isfinite(s['p*_中位']) else '—'} | {f2(s['反例μ'])} | {f2(s['反例s'])} | {f2(s['門檻μ−1.28s/√8'])} | {s['未到判決日主題數']} | {s['壞根截斷主題數']} |")
        md.append("")
    if "接續等權超額" in TH:
        md += ["## 接續版（壞根截斷格改用減資／面額變更接續值；參考）", ""]
        for H in (60, 72, 24):
            for res in ("大漲", "失敗"):
                d = TH[(TH["市場"] == "TW") & (TH["H月"] == H) & (TH["結果"] == res)]["接續等權超額"].astype(float)
                md.append(f"- 台股 {H} 月 {res}：平均 {f2(d.mean())}、中位 {f2(d.median())}（n {d.notna().sum()}）")
            s = ST[(ST["市場"] == "TW") & (ST["H月"] == H) & (ST["樣本單位"] == "主題") & (ST["量"] == "接續超額")].iloc[0]
            md.append(f"- 台股 {H} 月接續版：p* 平均口徑 {pc(s['p*_平均'])}（n {s['n_平均']}）、中位口徑 {pc(s['p*_中位'])}（n {s['n_中位']}）；"
                      f"反例 μ {f2(s['反例μ'])}、s {f2(s['反例s'])}、門檻 {f2(s['門檻μ−1.28s/√8'])}")
        md.append("")
    md += ["## 每主題一列（60 月；括號 72 月）", "",
           "| id | 市場 | 結果 | 產業 | 代表股 | 燈亮月 | 代表股 R | 同主題各檔 R | 等權 R | 合計 R | 大盤同期 | 等權超額 | 狀態 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (mk, cid), g in TB.groupby(["市場", "id"], sort=False):
        a = g[g["H月"] == 60]; b = g[g["H月"] == 72]
        t60 = TH[(TH["id"] == cid) & (TH["H月"] == 60)]; t72 = TH[(TH["id"] == cid) & (TH["H月"] == 72)]
        if not len(t60):
            md.append(f"| {cid} | {mk} | {a['結果'].iloc[0]} | {a['產業'].iloc[0]} | {a['代表股'].iloc[0]} | {a['燈亮月'].iloc[0]} | — | — | — | — | — | — | {a['狀態'].iloc[0]} |")
            continue
        t60 = t60.iloc[0]; t72 = t72.iloc[0]
        each = "／".join(f"{r.代號} {f2(r.R)}" for r in a.itertuples())
        stt = "；".join(sorted(set(a["狀態"]) | set("72:" + x for x in b["狀態"] if x != "完整")))
        md.append(f"| {cid} | {mk} | {t60['結果']} | {t60['產業']} | {t60['代表股']} | {t60['燈亮月']} | {f2(t60['代表股R'])}（{f2(t72['代表股R'])}） | {each} | "
                  f"{f2(t60['等權R'])}（{f2(t72['等權R'])}） | {f2(t60['合計R'])}（{f2(t72['合計R'])}） | {f2(t60['等權大盤'])}（{f2(t72['等權大盤'])}） | "
                  f"{f2(t60['等權超額'])}（{f2(t72['等權超額'])}） | {stt} |")
    md += ["", f"{WARN}"]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

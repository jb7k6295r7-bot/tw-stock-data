# -*- coding: utf-8 -*-
"""H1「營收見頂確認、先賣一半」對 v4.1 全抱 seq1：全部描述欄（台股策略線登錄 seq1 sha 42d64aee7df4e61b；裁定 seq474 §六核、seq458 全部描述欄先乾跑）
——回測線計算子代理。描述、⛔ 不判定、不計 N。
⛔ 正式跑必須帶 --ruling seqNNN（沒帶拒跑）；--dry＝乾跑：價格、大盤全換成 1、成本 0 ⇒ 所有 R 恰為 0（seq366：⛔ 不准含報酬的試跑或子樣本）。
⛔ 不 commit、不改既有檔。檔名：backtest/researchH1.py 早已存在（別件 PREREGH1）⇒ 本件 researchH1half.py；事件與觸發 import researchH1half_freq（同一套）。

    乾跑：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half --dry
    正式：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half --ruling seqNNN
輸出：正式 backtest/resultsH1half/main/；乾跑 backtest/resultsH1half/dry/（rows.csv、signals.csv、stats.csv、summary.md、main.json、run.log）

═══ 讀法（★＝執行者定；事件、進場、E、觸發、賣出日照 researchH1half_freq F0～F10）═══
 M1 全抱 ＝ 進場（還原開盤）抱到 E 收盤；未到 E ⇒ 結算到資料末日、標「未到」。結算、壞根截斷、下市照 researchLampCensus.Engine.settle（主欄＝截斷；⛔ 本件不做接續版）。
    R ＝ 結算價 ÷ 進場價 − 1 − 0.585%；H ＝ 持有交易日（面板日曆 index 差）。
 M2 H1 ＝ 賣出那半：賣出日還原開盤 ÷ 進場價 − 1 − 0.585%，H＝賣出日 − 進場日；剩下那半 ＝ 全抱（同一筆 R、H）。未觸發（含「觸發但已先結算」）⇒ H1 ＝ 全抱。
 M3 年化(半) ＝ (1＋R)^(250 ÷ max(H, 60)) − 1；1＋R ≤ 0 ⇒ 年化記 −100%。H1 整筆年化 ＝ 兩半年化等權平均；d ＝ H1 整筆年化 − 全抱年化。
 M4 主報 ＝ 訊號層（同訊號內各檔 d 等權平均＝1 個樣本）d 的中位與平均；另附每檔各算。甲乙分開、缺貨／新需求／政策分開；觸發率；觸發者 d 中位。
    CI ＝ 按燈 1 季分群的群集重抽（2000 次、種子 20261025，百分位 2.5／97.5），只描述。
 M5 份口徑（描述一句）＝ 每檔對大盤含息超額：全抱 R−M；H1 ＝ ½(R賣−M賣) ＋ ½(R全−M全)（賣掉那半之後改抱大盤 ⇒ 之後超額記 0）；
    ★ M賣 ＝ market_tri 進場前一交易日收盤 → 賣出日前一交易日收盤（賣在開盤、指數只有收盤）。
 M6 賣掉那一半後 12 個月內又漲 ≥ 1 倍 ＝ 賣出日～賣出日＋12 個日曆月（截到截斷／結算日）內最高還原收盤 ÷ 賣出價 − 1 ≥ 1；12 月窗未滿另標。
    賣在確認日的價格距之前最高收盤 ＝ 賣出價 ÷ 進場日～賣出日前一日最高還原收盤 − 1。
 M7 採用門檻描述句（產業 seq41，改寫成描述）＝「普查樣本上 d 平均 ≥ 0 且 d 中位 > 0」成立與否（訊號層、甲乙各一句；⛔ 不並列成結論、不判定）。
 M9 主表另報 d 的 P25／P75、最好與最壞一筆（訊號）、緊接版觸發數（裁定 seq475、使用者 seq477）。
 M8 舊 31 段 ＝ 代表股版、同業等權版，同口徑只描述（案＝1 個樣本）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchH1half_freq as F               # noqa: E402
LC = F.LC                                                   # researchLampCensus 凍結版（commit 04d50972fe），與頻率表同一個模組物件
from backtest import researchV41EV as V                     # noqa: E402

BASE = "backtest/resultsH1half"
COST = V.COST_TW
TYPES = F.TYPES
LOG = []
NB = 2000
SEED = 20261025


def log(s):
    s = f"[{time.strftime('%H:%M:%S')}] {s}"; print(s, flush=True); LOG.append(s)


def ann(R, H):
    with np.errstate(divide="raise", invalid="raise", over="raise"):
        if not np.isfinite(R) or H is None:
            return np.nan
        if 1 + R <= 0:
            return -1.0
        return float((1 + R) ** (250.0 / max(int(H), 60)) - 1)


def make_dry(EN):
    """乾跑：價格、大盤全換成 1（保留缺值位置），成本 0，接續停用 ⇒ R 恰為 0。"""
    EN.C = np.where(np.isfinite(EN.C), 1.0, np.nan)
    EN.O = np.where(np.isfinite(EN.O), 1.0, np.nan)
    EN.T = pd.Series(1.0, index=EN.T.index)
    EN.bridge = lambda *a, **k: (None, "乾跑不接續")
    LC.COST = 0.0                       # Engine.settle 讀模組變數 COST（只改執行期，不改檔）
    global COST
    COST = 0.0


def run_event(EN, C, r):
    i, e = int(r["_i"]), int(r["_e"]); sid = r["代號"]; CAL = EN.CAL
    Ek, Ems = C.E(e)
    tgt = CAL[Ek] if Ek is not None else Ems
    st = EN.settle(i, sid, e, tgt)
    xe = int(CAL.searchsorted(pd.Timestamp(st["結算日"])))
    Rf, Mf = st["R"], st["大盤"]; Hf = xe - e
    af = ann(Rf, Hf)
    out = {"全抱R": Rf, "全抱大盤": Mf, "全抱H": Hf, "全抱結算日": st["結算日"], "全抱狀態": st["狀態"], "全抱年化": af, "觸發": r["結果"] == "觸發"}
    if out["觸發"]:
        s = int(r["賣出idx"]); P0 = float(EN.O[i, e])
        with np.errstate(divide="raise", invalid="raise"):
            Rs = float(EN.O[i, s] / P0 - 1 - COST)
            Ms = V.tri_at(EN.T, CAL[s - 1]) / V.tri_at(EN.T, CAL[e - 1]) - 1
        Hs = s - e; as_ = ann(Rs, Hs)
        out.update({"賣R": Rs, "賣大盤": Ms, "賣H": Hs, "賣年化": as_, "H1年化": (as_ + af) / 2})
        # M6
        end12 = int(CAL.searchsorted(CAL[s] + pd.DateOffset(months=12), "right")) - 1
        w_end = min(end12, xe)
        cw = EN.C[i, s:w_end + 1]; cw = cw[np.isfinite(cw)]
        with np.errstate(divide="raise", invalid="raise"):
            up = float(cw.max() / EN.O[i, s] - 1) if len(cw) else np.nan
            ph = EN.C[i, e:s]; ph = ph[np.isfinite(ph)]
            dist = float(EN.O[i, s] / ph.max() - 1) if len(ph) else np.nan
        out.update({"賣後12月最高漲幅": up, "賣後12月又漲≥1倍": bool(np.isfinite(up) and up >= 1.0),
                    "12月窗未滿": bool(CAL[s] + pd.DateOffset(months=12) > CAL[EN.CEND] or end12 > xe), "賣價距前高": dist})
    else:
        out.update({"H1年化": af})
    out["d"] = out["H1年化"] - af
    exf = Rf - Mf
    out["全抱份超額"] = exf
    out["H1份超額"] = 0.5 * (out["賣R"] - out["賣大盤"]) + 0.5 * exf if out["觸發"] else exf
    out["d份"] = out["H1份超額"] - exf
    return out


def summ(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0, "平均": np.nan, "中位": np.nan}
    return {"n": int(len(v)), "平均": float(v.mean()), "中位": float(np.median(v))}


def cluster_ci(df, col, gcol):
    """群集重抽：以 gcol 為群，重抽群、群內訊號全帶，算 col 平均。空 ⇒ NaN。"""
    d = df[[col, gcol]].dropna()
    if d.empty:
        return np.nan, np.nan
    groups = [g[col].values for _, g in d.groupby(gcol)]
    rng = np.random.default_rng(SEED); k = len(groups); mus = []
    for _ in range(NB):
        pick = rng.integers(0, k, k)
        x = np.concatenate([groups[j] for j in pick])
        mus.append(x.mean())
    return float(np.percentile(mus, 2.5)), float(np.percentile(mus, 97.5))


def group_stats(ev, sig, gcol):
    """ev＝每檔列；sig＝訊號層列（d、d份、觸發比例、gcol）。"""
    s1 = summ(sig["d"].tolist()); s2 = summ(ev["d"].tolist())
    dv = sig.dropna(subset=["d"]) if len(sig) else sig
    if len(dv):
        b = dv.loc[dv["d"].idxmax()]; w = dv.loc[dv["d"].idxmin()]
        q25, q75 = float(np.percentile(dv["d"], 25)), float(np.percentile(dv["d"], 75))
        best, worst, bid, wid = float(b["d"]), float(w["d"]), str(b.iloc[0]), str(w.iloc[0])
    else:
        q25 = q75 = best = worst = np.nan; bid = wid = ""
    tr = ev[ev["觸發"]]
    lo, hi = cluster_ci(sig, "d", gcol)
    rec = {"訊號n": s1["n"], "d平均(訊號)": s1["平均"], "d中位(訊號)": s1["中位"], "dP25(訊號)": q25, "dP75(訊號)": q75, "d最好(訊號)": best, "最好訊號": bid,
           "d最壞(訊號)": worst, "最壞訊號": wid, "dCI低": lo, "dCI高": hi, "群數": int(sig[gcol].nunique()) if len(sig) else 0,
           "檔次n": s2["n"], "d平均(每檔)": s2["平均"], "d中位(每檔)": s2["中位"],
           "觸發率(每檔)": float(ev["觸發"].mean()) if len(ev) else np.nan,
           "觸發數": int(ev["觸發"].sum()) if len(ev) else 0, "緊接版觸發數": int(ev["緊接版觸發"].astype(bool).sum()) if len(ev) else 0, "觸發者d中位(每檔)": summ(tr["d"].tolist())["中位"],
           "H1年化中位(訊號)": summ(sig["H1年化"].tolist())["中位"], "全抱年化中位(訊號)": summ(sig["全抱年化"].tolist())["中位"],
           "d份平均(訊號)": summ(sig["d份"].tolist())["平均"], "d份中位(訊號)": summ(sig["d份"].tolist())["中位"],
           "賣後12月又漲≥1倍": int(tr["賣後12月又漲≥1倍"].astype(bool).sum()) if len(tr) else 0,
           "其中12月窗未滿": int((tr["賣後12月又漲≥1倍"].astype(bool) & tr["12月窗未滿"].astype(bool)).sum()) if len(tr) else 0,
           "12月窗未滿件": int(tr["12月窗未滿"].astype(bool).sum()) if len(tr) else 0,
           "賣價距前高中位": summ(tr["賣價距前高"].tolist() if len(tr) else [])["中位"], "未到E件": int(ev["未到"].astype(bool).sum())}
    rec["門檻描述句成立"] = bool(np.isfinite(s1["平均"]) and np.isfinite(s1["中位"]) and s1["平均"] >= 0 and s1["中位"] > 0) if s1["n"] else None
    return rec


def sig_level(ev, key):
    if ev.empty:
        return pd.DataFrame(columns=[key, "d", "d份", "H1年化", "全抱年化", "觸發", "群"])
    g = ev.groupby(key)
    out = g.agg(d=("d", "mean"), d份=("d份", "mean"), H1年化=("H1年化", "mean"), 全抱年化=("全抱年化", "mean"), 觸發=("觸發", "mean"), 群=("群", "first"))
    return out.reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default="")
    a = ap.parse_args()
    if not a.dry and not re.fullmatch(r"seq\d+", a.ruling or ""):
        raise SystemExit("⛔ 正式跑必須帶 --ruling seqNNN（裁定核准號）；乾跑用 --dry")
    warnings.simplefilter("error", RuntimeWarning)          # 除以 0、空切片平均等一律報錯
    OUT = os.path.join(BASE, "dry" if a.dry else "main"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    s16 = F.reg_sha16()
    if s16 != F.REG_SHA16:
        raise SystemExit(f"⛔ 登錄 sha {s16} ≠ {F.REG_SHA16}")
    log(f"[模式] {'乾跑（R 全為 0）' if a.dry else '正式 ' + a.ruling}｜登錄 sha16 {s16}")
    EN = LC.Engine(); C = F.Cal(EN)
    if a.dry:
        make_dry(EN)
    L, diag, MD = F.load_S()
    EV = F.census_events(EN, C, L); OD = F.old31_events(EN, C, L)
    chk = F.verify_entries(EV, OD)
    log(f"[進場驗證] {chk}")
    ALL = pd.concat([EV, OD], ignore_index=True)
    ALL = ALL[ALL["入選"].astype(bool) & ALL["代號"].fillna("").ne("") & ALL["_i"].notna()].copy()
    res = [run_event(EN, C, r) for _, r in ALL.iterrows()]
    ALL = pd.concat([ALL.reset_index(drop=True), pd.DataFrame(res)], axis=1)
    ALL["群"] = np.where(ALL["樣本"] == "普查", ALL["燈1季"], ALL["訊號"])
    ALL.drop(columns=["_i", "_e"]).to_csv(os.path.join(OUT, "rows.csv"), index=False, encoding="utf-8-sig")
    ST = []; SG = []
    cen = ALL[ALL["樣本"] == "普查"]
    for ver in ("甲", "乙"):
        ev0 = cen[cen[ver].astype(bool)]
        for ty in ("全部",) + TYPES:
            ev = ev0 if ty == "全部" else ev0[ev0["型"] == ty]
            sg = sig_level(ev, "訊號")
            if ty == "全部":
                SG.append(sg.assign(組=ver))
            ST.append({"樣本": "普查", "組": ver, "型": ty, **group_stats(ev, sg, "群")})
    old = ALL[ALL["樣本"] == "舊31段"]
    for var in F.OLD_VARS:
        for cls in ("全部", "大漲", "失敗"):
            for ty in ("全部",) + TYPES + ("谷底",):
                ev = old[old["版"] == var]
                ev = ev if cls == "全部" else ev[ev["結果類"] == cls]
                ev = ev if ty == "全部" else ev[ev["型"] == ty]
                sg = sig_level(ev, "訊號")
                ST.append({"樣本": "舊31段", "組": var, "結果類": cls, "型": ty, **group_stats(ev, sg, "群")})
    # 空組自測（乾跑必過）：空表進統計不得報錯
    empty = ALL.iloc[0:0]
    ST_empty = group_stats(empty, sig_level(empty, "訊號"), "群")
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")
    pd.concat(SG).to_csv(os.path.join(OUT, "signals.csv"), index=False, encoding="utf-8-sig")
    checks = {}
    if a.dry:
        num = ["全抱R", "全抱大盤", "賣R", "賣大盤", "全抱年化", "賣年化", "H1年化", "d", "d份", "賣後12月最高漲幅", "賣價距前高"]
        nz = {c: int((ALL[c].dropna().abs() > 0).sum()) for c in num if c in ALL}
        nn = {c: int(ALL[c].isna().sum()) for c in ("全抱R", "全抱年化", "H1年化", "d", "d份")}
        nn_sell = int(ALL.loc[ALL["觸發"], ["賣R", "賣年化"]].isna().sum().sum())
        checks = {"非零值筆數(應全0)": nz, "必填欄缺值(應全0)": nn, "觸發者賣出欄缺值(應0)": nn_sell, "空組自測": "通過" if ST_empty["訊號n"] == 0 else "異常",
                  "統計列": len(ST), "事件列": len(ALL), "觸發": int(ALL["觸發"].sum())}
        ok = all(v == 0 for v in nz.values()) and all(v == 0 for v in nn.values()) and nn_sell == 0
        checks["DRY"] = "PASS" if ok else "FAIL"
        log(f"[乾跑檢查] {checks}")
    tri = EN.T; tail = EN.CAL[EN.CEND]
    mk = (V.tri_at(tri, tail) / V.tri_at(tri, "2025-09-30") - 1) if not a.dry else 0.0
    notes = ["滑動版觸發 100%（普查甲 39／39、乙 29／29）⇒ 本件比的是「先賣一半的時點」，不是「賣不賣」；緊接版觸發數另列（描述，裁定 seq475）。",
             "兩版（H1、全抱）都沒套 v4.1 新聞出場 ①～⑤。",
             "普查只有 6 個產業（水泥、食品、塑膠、紡織、電機機械、電器電纜），電子類還沒做。",
             "燈 1 季 2021Q1～2024Q3 共 15 季；季分群 n_eff 甲 14、乙 12 < 24 ⇒ 依構造還沒測、只描述、不計 N。",
             f"多數件未到 E、結算在資料末日；「到資料末日」被大盤 2025-09-30 → {tail.date()} 約 {mk * 100:+.0f}%（market_tri 含息）主導，6 個傳產業多半沒跟上。",
             "E ＝ 進場月＋60 個月那個月的第一個交易日（本件登錄字面，裁定 seq475；V41EV 為進場＋60 月當天或之前最後一個交易日，兩邊各自標註）。",
             "P 很小的件照字面、不另訂門檻（裁定 seq475）；壞根主欄截斷、未做接續版。"]
    write_md(OUT, ST, a, chk, checks, notes)
    json.dump({"模式": "乾跑" if a.dry else a.ruling, "登錄sha16": s16, "面板sha": EN.sha, "面板尾": str(EN.CAL[EN.CEND].date()), "進場驗證": chk, "乾跑檢查": checks,
               "必附": notes, "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)},
              open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def pp(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f}"


def write_md(OUT, ST, a, chk, checks, notes):
    head = "⚠ 乾跑：價格、大盤全為 1、成本 0 ⇒ 下列數字全為 0，只驗程式路徑。" if a.dry else f"正式（裁定 {a.ruling}）"
    md = [f"# H1 先賣一半 對 v4.1 全抱 seq1：全部描述欄（{head}）", "",
          "- 描述、⛔ 不判定、不計 N。d ＝ H1 整筆年化 − 全抱年化（百分點）；年化 ＝ (1＋R)^(250÷max(H,60))−1；主報訊號層中位（訊號＝1 個樣本，同訊號內各檔等權）。", "",
          "## 必附", ""] + [f"- {x}" for x in notes] + ["",
          "## 主表（每筆年化 d，百分點；訊號層）", "",
          "| 樣本 | 組 | 結果類 | 型 | 訊號 n（群） | d 中位 | 平均 | P25／P75 | 最好（訊號） | 最壞（訊號） | CI（群集重抽，只描述） | d 中位（每檔） | 觸發（緊接版） | 觸發者 d 中位 | H1／全抱 年化中位 | 門檻描述句 |",
          "|" + "---|" * 16]
    for _, r in ST.iterrows():
        cls = r.get("結果類", "") if isinstance(r.get("結果類", ""), str) else ""
        th = "—" if r["門檻描述句成立"] is None or (isinstance(r["門檻描述句成立"], float) and np.isnan(r["門檻描述句成立"])) else ("成立" if r["門檻描述句成立"] else "不成立")
        md.append(f"| {r['樣本']} | {r['組']} | {cls} | {r['型']} | {r['訊號n']}（{r['群數']}） | {pp(r['d中位(訊號)'])} | {pp(r['d平均(訊號)'])} | "
                  f"{pp(r['dP25(訊號)'])}／{pp(r['dP75(訊號)'])} | {pp(r['d最好(訊號)'])}（{r['最好訊號']}） | {pp(r['d最壞(訊號)'])}（{r['最壞訊號']}） | "
                  f"［{pp(r['dCI低'])}，{pp(r['dCI高'])}］ | {pp(r['d中位(每檔)'])} | {r['觸發數']}／{r['檔次n']}（{r['緊接版觸發數']}） | {pp(r['觸發者d中位(每檔)'])} | "
                  f"{pp(r['H1年化中位(訊號)'])}／{pp(r['全抱年化中位(訊號)'])} | {th} |")
    md += ["", "## 描述欄", "", "| 樣本 | 組 | 結果類 | 型 | 份口徑 d 中位／平均（份×100） | 賣後 12 月又漲 ≥1 倍（其中窗未滿） | 12 月窗未滿件 | 賣價距前高中位 | 未到 E 件 |", "|" + "---|" * 9]
    for _, r in ST.iterrows():
        cls = r.get("結果類", "") if isinstance(r.get("結果類", ""), str) else ""
        md.append(f"| {r['樣本']} | {r['組']} | {cls} | {r['型']} | {pp(r['d份中位(訊號)'])}／{pp(r['d份平均(訊號)'])} | {r['賣後12月又漲≥1倍']}（{r['其中12月窗未滿']}） | "
                  f"{r['12月窗未滿件']} | {pp(r['賣價距前高中位'])} | {r['未到E件']} |")
    md += ["", "- 結果句範本（⛔ 不寫 H1 較好／較差）：「在普查樣本上，H1 的每筆年化差中位為 X（描述，樣本只有 15 季）」。",
           "- 份口徑（描述一句、⛔ 不並列成第二個結論）：賣掉那半之後改抱大盤（之後超額記 0）。",
           "- 門檻描述句＝「普查樣本上 d 平均 ≥ 0 且 d 中位 > 0」（訊號層）；成立與否照寫、交使用者決定。",
           f"- 進場驗證：{chk}"]
    if checks:
        md.append(f"- 乾跑檢查：{checks}")
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""H1「營收見頂確認、先賣一半」對 v4.1 全抱 seq1：電子＋傳產普查（清單 v4）全部描述欄（同一登錄 sha 42d64aee7df4e61b；讀法照裁定 seq475）——回測線計算子代理。
描述、⛔ 不判定、不計 N。⛔ 正式跑必須帶 --ruling seqNNN；--dry＝價格、大盤全為 1、成本 0 ⇒ R 恰為 0。⛔ 不 commit、不改既有檔（傳產原結果 resultsH1half/main 不覆寫）。
事件、進場、情境＝researchH1half_e_freq（普查 8c4d0d9559 輸出、逐筆驗進場日）；結算、年化、d、份口徑、又漲 1 倍＝researchH1half.run_event／group_stats（同一套，M1～M9）。

    乾跑：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_e --dry
    正式：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_e --ruling seqNNN
輸出：正式 backtest/resultsH1half/main_e/；乾跑 backtest/resultsH1half/dry_e/

═══ 讀法 ═══
 照 researchH1half M1～M9 與 researchH1half_e_freq E0～E3。結算引擎＝普查 8c4d0d9559 版 Engine（同面板 PIN 9b0e9882572c）。
 情境：照實（＝寬鬆）、嚴格（燈 1 兩可剔除）、剔自評知道；類：電子、傳產、合計；甲乙；型。主報照實。
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
from backtest import researchH1half_e_freq as FE            # noqa: E402
from backtest import researchH1half_freq as F               # noqa: E402
from backtest import researchH1half as H                    # noqa: E402
from backtest import researchV41EV as V                     # noqa: E402

BASE = "backtest/resultsH1half"
LOG = []
SC_MAIN = ("照實", "嚴格", "剔自評知道")


def log(s):
    s = f"[{time.strftime('%H:%M:%S')}] {s}"; print(s, flush=True); LOG.append(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default="")
    a = ap.parse_args()
    if not a.dry and not re.fullmatch(r"seq\d+", a.ruling or ""):
        raise SystemExit("⛔ 正式跑必須帶 --ruling seqNNN（裁定核准號）；乾跑用 --dry")
    warnings.simplefilter("error", RuntimeWarning)
    OUT = os.path.join(BASE, "dry_e" if a.dry else "main_e"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    s16 = F.reg_sha16()
    if s16 != F.REG_SHA16:
        raise SystemExit(f"⛔ 登錄 sha {s16} ≠ {F.REG_SHA16}")
    log(f"[模式] {'乾跑（R 全為 0）' if a.dry else '正式 ' + a.ruling}｜登錄 sha16 {s16}｜普查 {FE.CREV}")
    EN = FE.LC8.Engine(); C = F.Cal(EN)
    if a.dry:
        H.make_dry(EN)
        FE.LC8.COST = 0.0                 # 8c4d 版 Engine.settle 讀自己模組的 COST（只改執行期）
    L, diag, MD = F.load_S()
    EV, S, info, chk = FE.build_events(EN, C, L)
    log(f"[進場驗證] {chk}")
    ALL = EV[EV["入選"].astype(bool) & EV["代號"].fillna("").ne("") & EV["_i"].notna()].copy().reset_index(drop=True)
    res = [H.run_event(EN, C, r) for _, r in ALL.iterrows()]
    ALL = pd.concat([ALL, pd.DataFrame(res)], axis=1)
    ALL["群"] = ALL["燈1季"]
    ALL.drop(columns=["_i", "_e"]).to_csv(os.path.join(OUT, "rows.csv"), index=False, encoding="utf-8-sig")
    types = [t for t in ("缺貨", "新需求", "政策") if t in set(S["型"])] + sorted(set(S["型"]) - {"缺貨", "新需求", "政策"})
    ST = []
    for sc in SC_MAIN:
        for cl in FE.CLASSES:
            for ver in ("甲", "乙"):
                ev0 = ALL[ALL[ver].astype(bool)]
                ev0 = ev0 if cl == "合計" else ev0[ev0["類"] == cl]
                ev0 = ev0[FE.scen_mask(ev0, sc)]
                for ty in ("全部",) + tuple(types):
                    ev = ev0 if ty == "全部" else ev0[ev0["型"] == ty]
                    if ty != "全部" and not len(ev):
                        continue
                    ST.append({"情境": sc, "類": cl, "組": ver, "型": ty, **H.group_stats(ev, H.sig_level(ev, "訊號"), "群")})
    empty = ALL.iloc[0:0]
    ST_empty = H.group_stats(empty, H.sig_level(empty, "訊號"), "群")
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")
    checks = {}
    if a.dry:
        num = ["全抱R", "全抱大盤", "賣R", "賣大盤", "全抱年化", "賣年化", "H1年化", "d", "d份", "賣後12月最高漲幅", "賣價距前高"]
        nz = {c: int((ALL[c].dropna().abs() > 0).sum()) for c in num if c in ALL}
        nn = {c: int(ALL[c].isna().sum()) for c in ("全抱R", "全抱年化", "H1年化", "d", "d份")}
        nn_sell = int(ALL.loc[ALL["觸發"], ["賣R", "賣年化"]].isna().sum().sum())
        checks = {"非零值筆數(應全0)": nz, "必填欄缺值(應全0)": nn, "觸發者賣出欄缺值(應0)": nn_sell, "空組自測": "通過" if ST_empty["訊號n"] == 0 else "異常",
                  "統計列": len(ST), "事件列": len(ALL), "觸發": int(ALL["觸發"].sum())}
        checks["DRY"] = "PASS" if (all(v == 0 for v in nz.values()) and all(v == 0 for v in nn.values()) and nn_sell == 0) else "FAIL"
        log(f"[乾跑檢查] {checks}")
    tail = EN.CAL[EN.CEND]
    mk = (V.tri_at(EN.T, tail) / V.tri_at(EN.T, "2025-09-30") - 1) if not a.dry else 0.0
    def trig(cl, ver):
        d = ALL[ALL[ver].astype(bool)]; d = d if cl == "合計" else d[d["類"] == cl]
        return f"{int(d['觸發'].sum())}／{len(d)}"
    self_e = S[S["類"] == "電子"]["自評知道"].mean()
    neff = {f"{cl}{ver}": int(ALL[ALL[ver].astype(bool) & ((ALL['類'] == cl) if cl != '合計' else True)]["燈1季"].nunique()) for cl in FE.CLASSES for ver in ("甲", "乙")}
    notes = [f"滑動版觸發：電子 甲 {trig('電子', '甲')}、乙 {trig('電子', '乙')}；傳產 甲 {trig('傳產', '甲')}、乙 {trig('傳產', '乙')}（傳產 100%、電子近九成）⇒ 本件比的主要是「先賣一半的時點」，不是「賣不賣」；緊接版觸發數另列（描述，裁定 seq475）。",
             "兩版（H1、全抱）都沒套 v4.1 新聞出場 ①～⑤。",
             "傳產只有 6 個產業（水泥、食品、塑膠、紡織、電機機械、電器電纜）；電子為產業代碼 24～28（產業 seq47 清單 v4）。",
             f"燈 1 季 2021Q1～2024Q3 共 15 季；季分群 n_eff {neff} 全部 < 24 ⇒ 依構造還沒測、只描述、不計 N。",
             f"多數件未到 E、結算在資料末日；「到資料末日」被大盤 2025-09-30 → {tail.date()} 約 {mk * 100:+.0f}%（market_tri 含息）主導。",
             f"電子類判燈者自評「知道後來走勢」{self_e * 100:.0f}%（{int(S[S['類'] == '電子']['自評知道'].sum())}／{int((S['類'] == '電子').sum())} 訊號列）⇒ 後見偏差風險大；另出剔自評知道版。",
             "寬鬆＝照實（清單本來就列入兩可）；嚴格＝燈 1 兩可剔除。三版差異來自判燈寬嚴與自評，不是統計誤差。",
             "E ＝ 進場月＋60 個月那個月的第一個交易日（登錄字面，裁定 seq475）；P 很小照字面不另訂門檻；壞根主欄截斷、未做接續版。",
             "5371 中光電三件（E23、E39、E70）本庫 2013-01～2026-07 無月營收 ⇒ 營收全缺、未觸發（H1＝全抱，d＝0 計入）。"]
    write_md(OUT, ST, a, chk, checks, notes)
    json.dump({"模式": "乾跑" if a.dry else a.ruling, "登錄sha16": s16, "普查版": FE.CREV, "面板sha": EN.sha, "面板尾": str(tail.date()), "進場驗證": chk,
               "乾跑檢查": checks, "必附": notes, "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)},
              open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


pp = H.pp


def th_of(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return "成立" if v else "不成立"


def write_md(OUT, ST, a, chk, checks, notes):
    head = "⚠ 乾跑：價格、大盤全為 1、成本 0 ⇒ 數字全為 0，只驗程式路徑。" if a.dry else f"正式（裁定 {a.ruling}）"
    md = [f"# H1 先賣一半 對 v4.1 全抱 seq1：電子＋傳產普查（{head}）", "",
          "- 描述、⛔ 不判定、不計 N。d ＝ H1 整筆年化 − 全抱年化（百分點）；年化 ＝ (1＋R)^(250÷max(H,60))−1；主報訊號層中位（訊號＝1 個樣本）。", "",
          "## 必附", ""] + [f"- {x}" for x in notes]
    cols = ("| 情境 | 類 | 組 | 型 | 訊號 n（群） | d 中位 | 最好（訊號） | 最壞（訊號） | P25／P75 | 平均 | CI（群集重抽） | 觸發（緊接版） | 觸發者 d 中位 | 又漲≥1倍（窗未滿） | 份口徑 d 中位 | 門檻描述句 |",
            "|" + "---|" * 16)

    def row(r):
        return (f"| {r['情境']} | {r['類']} | {r['組']} | {r['型']} | {r['訊號n']}（{r['群數']}） | {pp(r['d中位(訊號)'])} | {pp(r['d最好(訊號)'])}（{r['最好訊號']}） | "
                f"{pp(r['d最壞(訊號)'])}（{r['最壞訊號']}） | {pp(r['dP25(訊號)'])}／{pp(r['dP75(訊號)'])} | {pp(r['d平均(訊號)'])} | ［{pp(r['dCI低'])}，{pp(r['dCI高'])}］ | "
                f"{r['觸發數']}／{r['檔次n']}（{r['緊接版觸發數']}） | {pp(r['觸發者d中位(每檔)'])} | {r['賣後12月又漲≥1倍']}（{r['其中12月窗未滿']}） | {pp(r['d份中位(訊號)'])} | {th_of(r['門檻描述句成立'])} |")
    md += ["", "## 三版並列（全部型；寬鬆＝照實）", "", *cols]
    for cl in FE.CLASSES:
        for ver in ("甲", "乙"):
            for sc in SC_MAIN:
                d = ST[(ST["情境"] == sc) & (ST["類"] == cl) & (ST["組"] == ver) & (ST["型"] == "全部")]
                if len(d):
                    md.append(row(d.iloc[0]))
    for sc in SC_MAIN:
        md += ["", f"## 情境：{sc}（各型）", "", *cols]
        for _, r in ST[ST["情境"] == sc].iterrows():
            md.append(row(r))
    md += ["", "- 結果句範本（⛔ 不寫 H1 較好／較差）：「在普查樣本上，H1 的每筆年化差中位為 X（描述，樣本只有 15 季）」。",
           "- 份口徑（描述一句、⛔ 不並列成第二個結論）：賣掉那半之後改抱大盤（之後超額記 0）；份口徑受「到末日」大盤急漲影響大（見必附）。",
           "- 門檻描述句＝「d 平均 ≥ 0 且 d 中位 > 0」（訊號層）；成立與否照寫、交使用者決定。", f"- 進場驗證：{chk}"]
    if checks:
        md.append(f"- 乾跑檢查：{checks}")
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""長線三問 丙（F1～F7 賣法）加描述欄「每筆年化」——回測線計算子代理（描述、不計 N；判語一字不改）。
依據：裁定 seq460 §二（已定版件加一欄「每筆年化」，判語照原「記 0」，⛔ 不追溯改）、seq461；台股策略線 1843 §一（短持有寫死）。
⛔ 不改 researchLong3*.py 與 resultsLong3/ 既有檔；只新增本檔、researchLong3_ann_check.py、resultsLong3/ann/。

    乾跑：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_ann --dry --procs 3   （R 全 0 ⇒ ~/rtfwork/dry_l3_ann）
    正式：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_ann --procs 3         （⇒ resultsLong3/ann/）
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_ann_check [--dry]

═══ 讀法（N 標；寫於 2026-10-24（台北），⛔ 在看任何本件年化數字之前；★＝執行者定）═══
 N1 重建與錨點（同 researchLong3_alt A1）：呼叫 researchLong3.main()（OUT 轉 /tmp/l3ann_rebuild_*，⛔ 不碰 resultsLong3/），在它寫 long3.json 時取區域變數；
    重建的 丙_表.csv 與 events_丙.csv.gz（解壓後）須與已提交檔【逐位元組】相同 ⇒ 逐筆 R（抱3年R、各法 F_R、賣日、抱3年出場日）即與原正式跑相同，否則中止、⛔ 不算年化。
    資料版本 ＝ 原正式跑同一份（researchLong3 固定兩世界：主 H2D edc6f8002fed…、早年 eotc_f65bb03e11；逐位元組相同即證同版）。
 N2 年化 ＝ (1 ＋ R)^(250 ÷ max(H, 60)) − 1；★ R ＝ 原逐筆 R 扣一次來回成本 0.585%（researchLong3 L17「成本兩邊各一次來回」；年化下不再相消，故兩臂各扣）；
    H ＝ 持有交易日數（合併日曆位置差，進場日 e 算第 1 日）：被賣者 H ＝ 賣出天數 ＋ 1（賣日 − e ＋ 1）；抱 3 年 H ＝ 抱3年出場日位置 − e ＋ 1；★ 1 ＋ R ≤ 0 ⇒ −1。
    比法 ＝ 同一筆「賣法年化 − 抱 3 年年化」（評估點 ＝ 原登錄的抱 3 年出場，含壞根前一根、下市末根）；沒被賣 ⇒ 0。
 N3 樣本與段 ＝ 原丙表（全部窗完整／早年進場(～2014)／2015～進場／探索進場(2017-03～2021-12)；窗完整 ∧ 抱3年R 有值）。
    報：差的中位（主報）、平均、＞0 比例、被賣者中位；賣法臂與抱 3 年臂年化中位；持有 ＜ 60 日件數與比例（賣法臂，全部事件為分母）。
 N4 呈現：原丙句一字不改照引；新欄只寫一句「若照每筆年化比：…」附在後面，⛔ 不改判語、⛔ 不並列判定。
 N5 乾跑（--dry）：重建與錨點照做，之後 R 全換 0 ⇒ 年化、差全 0，跑通全部欄位；輸出 ~/rtfwork/dry_l3_ann（⛔ 不進 repo）。
"""
from __future__ import annotations

import argparse
import gzip
import json as _json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLong3 as L3                    # noqa: E402  main（丙）、FS、FNAME、COST

ORIG = "backtest/resultsLong3"
OUT0 = "backtest/resultsLong3/ann"
DRY_OUT = os.path.expanduser("~/rtfwork/dry_l3_ann")
HMIN = 60
COST = L3.COST
LOG: list = []
_CAP: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


class _JsonShim:
    """researchLong3.main() 寫 long3.json 時取它的區域變數（⛔ 不改 researchLong3 任何一行）。"""
    def dump(self, obj, fp, *a, **k):
        _CAP.update(sys._getframe(1).f_locals)
        return _json.dump(obj, fp, *a, **k)

    def __getattr__(self, n):
        return getattr(_json, n)


def ann(r, h):
    g = 1.0 + float(r)
    return -1.0 if g <= 0 else g ** (250.0 / max(int(h), HMIN)) - 1.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    out = DRY_OUT if a.dry else OUT0
    os.makedirs(out, exist_ok=True)
    log(f"[開始] {'乾跑（R 全 0）' if a.dry else '正式'}｜輸出 {out}")
    reb = f"/tmp/l3ann_rebuild_{'dry' if a.dry else 'real'}"
    os.makedirs(reb, exist_ok=True)
    L3.OUT = reb; L3.json = _JsonShim()
    argv0 = sys.argv; sys.argv = ["researchLong3", "--procs", str(a.procs)]
    try:
        L3.main()
    finally:
        sys.argv = argv0
    if "CR" not in _CAP:
        raise SystemExit("⛔ 沒取到 researchLong3.main() 的區域變數")
    same_tc = open(os.path.join(reb, "丙_表.csv"), "rb").read() == open(os.path.join(ORIG, "丙_表.csv"), "rb").read()
    same_ev = gzip.open(os.path.join(reb, "events_丙.csv.gz"), "rb").read() == gzip.open(os.path.join(ORIG, "events_丙.csv.gz"), "rb").read()
    log(f"[N1 錨點] 丙_表.csv 逐位元組相同 {same_tc}｜events_丙 解壓後逐位元組相同 {same_ev}｜{time.time() - t0:.0f}s")
    if not (same_tc and same_ev):
        raise SystemExit("⛔ 重建 ≠ 已提交丙 ⇒ 中止（未算年化）")
    L = _CAP
    CR, CAL, CSEG, CP, SC = L["CR"].copy(), L["CAL"], L["CSEG"], L["CP"], L["SC"]
    # ── N2 逐筆
    ROW = []
    for _, rw in CR.iterrows():
        e = int(rw["e"]); b3 = rw["抱3年R"]
        rec = {"sid": rw["sid"], "期別": rw["期別"], "e": e, "進場日": rw["進場日"], "進場月": rw["進場月"], "窗完整": bool(rw["窗完整"]), "typ3": int(rw["typ3"]),
               "抱3年出場日": rw["抱3年出場日"] if isinstance(rw["抱3年出場日"], str) else ""}
        if np.isfinite(b3):
            H3 = CP[rec["抱3年出場日"]] - e + 1
            R3 = 0.0 if a.dry else b3 - COST
            A3 = ann(R3, H3)
        else:
            H3, A3 = np.nan, np.nan
        rec["H_抱3年"] = H3; rec["年化_抱3年"] = A3
        for F in L3.FS:
            sold = bool(rw[f"{F}_賣"]); rec[f"{F}_賣"] = sold
            if not np.isfinite(b3):
                rec[f"H_{F}"] = np.nan; rec[f"年化_{F}"] = np.nan; rec[f"年化差_{F}"] = np.nan
                continue
            if sold:
                Hk = int(rw[f"{F}_賣出天數"]) + 1
                if CP[rw[f"{F}_賣日"]] - e + 1 != Hk:
                    raise SystemExit(f"⛔ 賣出天數與賣日不符 {rw['sid']} {F}")
                Ak = ann(0.0 if a.dry else rw[f"{F}_R"] - COST, Hk)
            else:
                Hk, Ak = H3, A3
            rec[f"H_{F}"] = Hk; rec[f"年化_{F}"] = Ak; rec[f"年化差_{F}"] = Ak - A3
        ROW.append(rec)
    EV = pd.DataFrame(ROW)
    # ── N3 表
    TCo = pd.read_csv(os.path.join(ORIG, "丙_表.csv"))
    TB = []
    for sg, (a0, a1) in CSEG.items():
        sub = EV[(EV["e"] >= a0) & (EV["e"] <= a1) & EV["窗完整"] & np.isfinite(EV["年化_抱3年"])]
        o = TCo[TCo["進場段"] == sg].set_index("法")
        for F in L3.FS:
            x_ = sub[f"年化差_{F}"].to_numpy(float); sold = sub[f"{F}_賣"].to_numpy(bool)
            TB.append({"進場段": sg, "法": F, "說明": L3.FNAME[F], "事件(窗完整)": int(len(sub)), "觸發賣出": int(sold.sum()),
                       "原表事件": int(o.at[F, "事件(窗完整)"]), "原表觸發賣出": int(o.at[F, "觸發賣出"]),
                       "年化差中位(賣法−抱3年)": float(np.median(x_)), "年化差平均": float(x_.mean()), "年化差>0比例": float((x_ > 0).mean()),
                       "被賣者年化差中位": (float(np.median(x_[sold])) if sold.any() else np.nan),
                       "賣法年化中位": float(sub[f"年化_{F}"].median()), "抱3年年化中位": float(sub["年化_抱3年"].median()),
                       "持有<60日件數(賣法臂)": int((sub[f"H_{F}"] < HMIN).sum()), "持有<60日比例(賣法臂,÷全部)": float((sub[f"H_{F}"] < HMIN).mean()),
                       "抱3年臂持有<60日件數": int((sub["H_抱3年"] < HMIN).sum()), "賣法臂H中位": float(sub[f"H_{F}"].median()),
                       "原表d平均(記0，判語照原)": o.at[F, "d平均(加賣法−抱3年)"], "原表d結果(描述)": o.at[F, "d結果(描述)"], "性質": "描述（不計 N）"})
    TB = pd.DataFrame(TB)
    cnt_ok = bool((TB["事件(窗完整)"] == TB["原表事件"]).all() and (TB["觸發賣出"] == TB["原表觸發賣出"]).all())
    log(f"[N3] 事件數、觸發數與原丙表相同 {cnt_ok}")
    if not cnt_ok:
        raise SystemExit("⛔ 件數與原丙表不同")
    # ── N4 句
    SENT = {}
    for F in L3.FS:
        r = TB[(TB["進場段"] == "全部窗完整") & (TB["法"] == F)].iloc[0]
        SENT[F] = (SC[F] + f"｜若照每筆年化比（賣法年化 − 抱 3 年年化，兩臂各扣來回 0.585%，描述、不判）：中位 {r['年化差中位(賣法−抱3年)'] * 100:+.2f} 點"
                   f"（平均 {r['年化差平均'] * 100:+.2f} 點、＞0 {r['年化差>0比例'] * 100:.0f}%；持有＜60 日 {r['持有<60日比例(賣法臂,÷全部)'] * 100:.1f}%）")
        log(f"[句] {F}：{SENT[F]}")
    DC = {}
    if a.dry:
        nc = [c for c in EV.columns if c.startswith(("年化_", "年化差_"))]
        ok = EV[EV["窗完整"] & np.isfinite(EV["年化_抱3年"])]
        DC = {"年化欄全0(窗完整)": bool(np.all(ok[nc].to_numpy(float) == 0)), "年化欄無空值(窗完整)": bool(not ok[nc].isna().any().any()),
              "表空值欄": {c: int(TB[c].isna().sum()) for c in TB.columns if TB[c].isna().any()}, "表列數": len(TB), "句數": len(SENT)}
        log(f"[N5 乾跑檢查] {DC}")
    TB.to_csv(os.path.join(out, "丙_ann_表.csv"), index=False, encoding="utf-8-sig")
    EV.to_csv(os.path.join(out, "events_丙_ann.csv.gz"), index=False, compression="gzip")
    J = {"性質": "長線三問 丙 加描述欄「每筆年化」（描述、不計 N；判語一字不改）" + ("【乾跑：R 全 0】" if a.dry else ""),
         "依據": "裁定 seq460 §二、seq461；台股策略線 1843 §一", "資料": "researchLong3 固定兩世界（主 ~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65、早年 ~/earlydata/eotc_f65bb03e11）",
         "錨點": {"丙_表逐位元組相同": same_tc, "events_丙逐位元組相同": same_ev, "件數與原丙表相同": cnt_ok}, "成本": COST,
         "丙句(原句一字不改＋若照每筆年化比)": SENT, "乾跑檢查": DC, "表": TB.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "秒": round(time.time() - t0)}
    _json.dump(J, open(os.path.join(out, "long3_ann.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

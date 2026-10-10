# -*- coding: utf-8 -*-
"""營量營飆單月營收改三個月合計 seq2（月營收口徑敏感度；台股策略線登錄 sha 2a5e76cb1251858f，2026-10-10 23:11；裁定 seq323 §二 核准、⛔ 不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL3m run [--procs 2] [--reps 200]
    ...                                                  -m backtest.researchYL3m page
    抽樣查核（獨立寫法）：... -m backtest.researchYL3m_check

⭐ 讀法寫死時間：2026-10-10 23:54（台北）；寫死前 ⛔ 沒算任何本件數字（營量 v1／營飆 v1 正式數字本來就看過；登錄已聲明）。

═══ 讀法（Y 標）═══
 Y1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ 2a5e76cb1251858f 才跑
 Y2 本體 ＝ 營量 v1、營飆 v1 正式版：researchT1fix.build_ctx(True) 同一條路徑（rerun17.setup_and t1＝True、edc6f 快照、主窗 2017-03-02～2026-08-24、
    營飆 ＝ listexit_lines.sim H120 N10 default_rng(1000＋r) t−1 大盤閘 200 顆；營量 ＝ simulate_mtm H60 N20 relvol 排序 r＝0；停止交易強制出場：開）
    ⭐ 只換 AND 表裡的月營收條件；其他一字不動（強勢股 5 取 3 ＝ resultsN17/sig_edc6f/signals_S.csv.gz 原檔、STALE_MAX、可用日 10 日、檔數、排序、持有、成本）
 Y3 月營收條件重建：營收面板列 ＝ resultsN17/sig_edc6f/panel_rev.csv.gz 原檔的 (股, 期, signal_pos)（gate 已過的列；⛔ 不重跑 gate）；
    營收 ＝ research34.load_revenue（edc6f 快照 mops/revenue_hist；位置 k ＝ 該期在營收表期別序列的位置，同 research34.process_stock）
    現行臂（單月）＝ research34 原式：當期營收有值 ∧ 前 24 期全部有值 ∧ 當期 ≥ 前 24 期最大值（⚠ 正式程式是「≥」；登錄寫「＞」⇒ 照正式程式，兩者差幾列照報）
    3M 臂 ＝ 當期與前 2 期三期都有值 ∧ 前 21 期（k−23～k−3）全部有值 ∧ 三期合計 ≥ 前 21 期內任何連續三期合計（19 個窗）的最大值
      （⚠ 補讀法：比較號與正式程式同為「≥」，只換單月 ⇒ 三個月合計；登錄寫「＞」，「＞／≥」不同的列數照報）
    AND ＝ research13.and_flags(S, 面板)（原函式；最新一期面板列距訊號日 ≤ 45 個交易日）；relvol、g_H20 ＝ researchp1.attach_features（原函式）
 Y4 閘（⛔ 不過就停）：G0 0050 主窗錨逐位元｜G1 現行臂重建的 rev_hi24 ＝ panel_rev 原欄逐列相同、AND 列（sid、k、pos）＝ and_signals.csv.gz 逐列相同、
    relvol／g_H20 逐位元相同｜G2 現行臂引擎 ＝ resultsT1fix/seeds.csv.gz c1／c13 t1 逐位元（cagr／mdd repr、eq_sha、trades）
 Y5 判（登錄 §二）：兩臂各自照使用者判準給標籤（探索、確認兩段取較嚴；同一條權益切窗，researchSlip 同法）；
    ① 兩策略標籤都相同 ⇒「把單月改成 3 個月合計，營量 v1、營飆 v1 標籤不變（單月口徑不是挑出來的運氣）」
    ② 任一不同 ⇒「月營收口徑會改變 <策略> 的標籤」⇒ 交裁定；⛔ 本線不自行改正式規則
    必報：兩臂訊號重疊率（窗內；營飆＝過大盤閘的訊號、營量＝全部窗內訊號；交集 ÷ 聯集，另報各自占比）、換了股票的筆數（只在一臂的列）
 Y6 退化檢查先寫：各臂各段平均持股、平均現金（引擎 audit 逐日重建；種子中位）、訊號數逐年 ⇒ degeneracy.json（附台北時間）之後才算報酬
 Y7 不計 N；⛔ 不改正式規則；成本只報 0.585% 版（登錄「成本一字不動」）
輸出 backtest/resultsYL3m/；網頁 backtest/營量營飆三個月合計_口徑.html
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchPRE5core as C   # noqa: E402
from backtest import rerun17 as RR           # noqa: E402
from backtest import data as D               # noqa: E402

REG_SHA = "2a5e76cb1251858f"
TIME = "2026-10-10 23:54（台北）"
OUT = os.path.expanduser("~/tw-p17/backtest/resultsYL3m")
PAGE = os.path.expanduser("~/tw-p17/backtest/營量營飆三個月合計_口徑.html")
SIG = os.path.join(RR.OUT, "sig_edc6f")
AND3 = os.path.join(C.WORK, "and3m_signals.csv.gz")


def flags(rv, ks):
    """rv：期 × 檔（numpy，同營收表期別序列）；ks：(列, k, 檔欄) ⇒ (單月 ≥, 單月 ＞, 3M ≥, 3M ＞)。"""
    out = []
    for k, j in ks:
        x = rv[:, j]
        one_ge = one_gt = th_ge = th_gt = False
        if np.isfinite(x[k]):
            h = x[max(0, k - 24):k]
            if len(h) == 24 and np.isfinite(h).all():
                one_ge = bool(x[k] >= h.max()); one_gt = bool(x[k] > h.max())
        if k >= 23:
            w = x[k - 23:k + 1]
            if np.isfinite(w).all():
                cur = w[-3:].sum()
                prev = w[:21]
                mx = max(prev[i:i + 3].sum() for i in range(19))
                th_ge = bool(cur >= mx); th_gt = bool(cur > mx)
        out.append((one_ge, one_gt, th_ge, th_gt))
    return np.array(out, bool)


def run(a):
    os.makedirs(OUT, exist_ok=True)
    log = C.log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchYL3m run {C.now_tpe()}（台北）｜讀法寫死 {TIME}｜reps {a.reps} =====")
    regf = C.reg_check(REG_SHA); log(f"[sha] {REG_SHA} ✔ {regf}")
    from backtest import research13 as R13
    from backtest import research34 as R34
    from backtest import researchp1 as P1
    RR.use_snapshot(); cal = D.load_calendar()
    rev, rev_ly, ind = R34.load_revenue()
    pnl = pd.read_csv(os.path.join(SIG, "panel_rev.csv.gz"), dtype={"stock_id": str})
    per = {p: i for i, p in enumerate(rev.index)}; col = {s: j for j, s in enumerate(rev.columns)}
    rv = rev.to_numpy(float)
    ks = []; miss = 0
    for s, p in zip(pnl["stock_id"], pnl["period"]):
        if s in col:
            ks.append((per[p], col[s]))
        else:
            ks.append((per[p], None)); miss += 1
    FL = np.zeros((len(ks), 4), bool)
    have = np.array([j is not None for k, j in ks])
    FL[have] = flags(rv, [x for x in ks if x[1] is not None])
    orig = pnl["rev_hi24"].fillna(False).astype(bool).to_numpy()
    g1a = int((FL[:, 0] != orig).sum())
    log(f"[G1a] 面板 {len(pnl):,} 列（營收表沒有該檔 {miss}）；現行臂重建 rev_hi24 與原欄不同 {g1a} 列｜單月「≥／＞」不同 {int((FL[:, 0] != FL[:, 1]).sum())}、3M「≥／＞」不同 {int((FL[:, 2] != FL[:, 3]).sum())}")
    S = pd.read_csv(os.path.join(SIG, "signals_S.csv.gz"), dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    A0 = pd.read_csv(os.path.join(SIG, "and_signals.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    p1 = pnl.copy(); p1["rev_hi24"] = FL[:, 0]
    f1, _ = R13.and_flags(S, p1)
    A1 = S[f1].copy()
    same_rows = A1[["sid", "k", "pos"]].reset_index(drop=True).equals(A0[["sid", "k", "pos"]].reset_index(drop=True))
    log(f"[G1b] 現行臂 AND {len(A1)} 列 vs 原檔 {len(A0)} 列｜(sid,k,pos) 逐列相同 {same_rows}")
    p3 = pnl.copy(); p3["rev_hi24"] = FL[:, 2]
    f3, _ = R13.and_flags(S, p3)
    A3 = S[f3].copy()
    mk = D.load_universe().set_index("stock_id")["market"]
    both = pd.concat([A1.assign(_arm=1), A3.assign(_arm=3)], ignore_index=True)
    Sx = S.copy()
    miss_, mism = P1.attach_features(both, Sx, cal, mk, a.procs)
    A1f = both[both["_arm"] == 1].drop(columns="_arm").reset_index(drop=True)
    A3f = both[both["_arm"] == 3].drop(columns="_arm").reset_index(drop=True)
    g1c = {c: bool(all(repr(float(x)) == repr(float(y)) for x, y in zip(A1f[c], A0[c]))) for c in ("relvol", "g_H20")}
    g1c["xpos_H20"] = bool((A1f["xpos_H20"].to_numpy(int) == A0["xpos_H20"].to_numpy(int)).all())
    log(f"[G1c] relvol／g_H20／xpos_H20 逐位元：{g1c}｜attach 缺 {len(miss_)}、k↔pos 不符 {mism}")
    if g1a or not same_rows or not all(g1c.values()):
        raise SystemExit("⛔ G1 不過（不改口徑時不逐位元相同）")
    A3f[list(A0.columns)].to_csv(AND3, index=False)
    pd.DataFrame({"stock_id": pnl["stock_id"], "period": pnl["period"], "signal_pos": pnl["signal_pos"], "one_ge": FL[:, 0], "three_ge": FL[:, 2]}).to_csv(
        os.path.join(C.WORK, "yl3m_panel_flags.csv.gz"), index=False)
    log(f"[3M 臂] AND {len(A3f)} 列 ⇒ {AND3}")
    # 引擎
    YB = C.yl_ref(log, a.procs, a.reps)
    G2 = C.yl_gate(YB)
    log(f"[G2] 現行臂引擎 vs resultsT1fix：{G2}")
    if G2["不同"]:
        raise SystemExit("⛔ G2 不過")
    Y3 = C.yl_ref(log, a.procs, a.reps, and_path=AND3, tag="3m")
    # 退化（先寫）
    DG = {}
    for arm, Y in (("現行臂（單月）", YB), ("3M 臂", Y3)):
        for fam, nm in (("fly", "營飆 v1"), ("vol", "營量 v1")):
            g = [x for x in Y["rows"] if x["fam"] == fam]
            DG[f"{nm}｜{arm}"] = {f"{sg}_{k}": float(np.median([x[f"{sg}_{k}"] for x in g])) for sg in C.SEGS for k in ("平均持股", "平均現金")}
            for sg in C.SEGS:
                h = DG[f"{nm}｜{arm}"]
                h[f"{sg}_退化"] = bool(h[f"{sg}_平均持股"] < 3 or h[f"{sg}_平均現金"] > 0.30)
    yrs = {}
    for arm, Y in (("現行臂（單月）", YB), ("3M 臂", Y3)):
        for fam, k in (("營飆 v1", "sig_fly"), ("營量 v1", "sig_vol")):
            yrs[f"{fam}｜{arm}"] = {str(y): int(v) for y, v in pd.Series([cal[e].year for e in Y[k]["entry_pos"]]).value_counts().sort_index().items()}
    json.dump({"寫入時間": C.now_tpe() + "（台北）", "說明": "⭐ 在算任何報酬之前寫入；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（種子中位）", "持股與現金": DG, "訊號數逐年（窗內）": yrs},
              open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json：{json.dumps({k: (round(v['主窗_平均持股'], 2), round(v['主窗_平均現金'], 3)) for k, v in DG.items()}, ensure_ascii=False)}")
    # 報酬與標籤
    TB = {"現行臂（單月）": C.yl_table(YB), "3M 臂": C.yl_table(Y3)}
    LAB = {}
    for arm, T in TB.items():
        for nm, r in T.items():
            LAB[(nm, arm)] = C.stricter(r["探索_標籤"], r["確認_標籤"])
    same = all(LAB[(nm, "現行臂（單月）")] == LAB[(nm, "3M 臂")] for nm in ("營飆 v1", "營量 v1"))
    if same:
        concl = "① 把單月改成 3 個月合計，營量 v1、營飆 v1 標籤不變（單月口徑不是挑出來的運氣）"
    else:
        diff = [nm for nm in ("營飆 v1", "營量 v1") if LAB[(nm, "現行臂（單月）")] != LAB[(nm, "3M 臂")]]
        concl = "② 月營收口徑會改變 " + "、".join(diff) + " 的標籤 ⇒ 交裁定；⛔ 本線不自行改正式規則"
    log(f"[判] {concl}｜{ {f'{k[0]}｜{k[1]}': v for k, v in LAB.items()} }")
    # 重疊
    OV = {}
    for fam, k in (("營飆 v1", "sig_fly"), ("營量 v1", "sig_vol")):
        a1 = set(map(tuple, YB[k][["sid", "k"]].astype(str).to_numpy())); a3 = set(map(tuple, Y3[k][["sid", "k"]].astype(str).to_numpy()))
        OV[fam] = {"現行臂列": len(a1), "3M 臂列": len(a3), "兩臂都有": len(a1 & a3), "只在現行臂（換掉）": len(a1 - a3), "只在 3M 臂（換進）": len(a3 - a1),
                   "重疊率（交集÷聯集）": len(a1 & a3) / max(len(a1 | a3), 1), "現行臂列在 3M 臂的比例": len(a1 & a3) / max(len(a1), 1)}
    log(f"[重疊] {json.dumps(OV, ensure_ascii=False)}")
    # 全表（含 AND 全表 2015～）
    ALLOV = {"AND 全表 現行臂": int(len(A1f)), "AND 全表 3M 臂": int(len(A3f)),
             "面板 rev_hi24 單月 True": int(FL[:, 0].sum()), "面板 3M True": int(FL[:, 2].sum()), "面板兩者皆 True": int((FL[:, 0] & FL[:, 2]).sum())}
    SUM = {"件": "營量營飆單月營收改三個月合計 seq2（口徑件、不計 N）", "登錄": regf, "sha": REG_SHA, "讀法寫死": TIME, "run": C.now_tpe(), "reps": a.reps,
           "閘": {"G1a 面板重建不同列": g1a, "G1b AND 列相同": same_rows, "G1c 特徵逐位元": g1c, "G2 引擎": G2,
                  "單月≥與＞不同列": int((FL[:, 0] != FL[:, 1]).sum()), "3M≥與＞不同列": int((FL[:, 2] != FL[:, 3]).sum())},
           "0050": YB["Z"], "表": TB, "標籤（兩段取較嚴）": {f"{k[0]}｜{k[1]}": v for k, v in LAB.items()}, "結論": concl, "重疊": OV, "全表": ALLOV,
           "退化": DG, "T1 補回": {"現行臂": YB.get("t1_cnt"), "3M 臂": Y3.get("t1_cnt")}}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    rows = []
    for arm, Y in (("現行臂（單月）", YB), ("3M 臂", Y3)):
        for x in Y["rows"]:
            rows.append({"臂": arm, **{k: v for k, v in x.items() if k != "iv"}})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    log(f"[完] {concl}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="run")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    elif a.cmd == "page":
        from backtest import researchPRE5page as PG
        PG.page_yl3m()


if __name__ == "__main__":
    main()

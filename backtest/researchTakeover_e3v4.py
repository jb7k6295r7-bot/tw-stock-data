# -*- coding: utf-8 -*-
"""被公開收購／經營權變動／私募 seq2【E3 修後重跑（E3 v4，裁定 seq457 §一）】——回測線計算子代理。
⛔ 描述，不是選股規則；⛔ 不判、不計 N、不推 LINE。⛔ 不 commit、不改既有檔：researchTakeover_freq（TF）、researchTakeover（TM）、researchRevTurn_freq（RT）
   ⛔ 只 import，執行期只換三個模組變數（下列 V1～V3），函式原樣。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_e3v4 freq        # 頻率表（無報酬）
                  PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_e3v4 main --dry  # 乾跑（R 全寫 0，輸出 ~/tko3work/dry_main）
                  PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_e3v4 main        # 正式跑
                  PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_e3v4 cmp         # 與 seq2 原結果逐數對照
輸出 backtest/resultsTakeover/e3v4_freq/、backtest/resultsTakeover/e3v4_main/（⛔ 不碰原 freq/、main/）

═══ 讀法（2026-10-23 台北，⛔ 在看任何 E3 v4 報酬之前寫死）═══
 V1 事件表 ＝ origin/main 99159a0de9 的 data/meta/takeover_events/takeover_events.csv（E3 v4：3,012 列 ＝ v3 3,021 剔 9 列；E1、E2 逐列不變）。
    TF.load_table 換成固定讀這個 sha；其餘（同類池排除、first12m、with_reduction）照表原樣。
 V2 價格、exright、stocks.csv、news（E1 收購方時戳）、v1b 重建、參考價表、追蹤資料 ＝ seq2 頻率表同一 sha（resultsTakeover/freq/freq.json 的
    origin/main 443ee8ce96）——RT.ensure_data 固定回這個 sha ⇒ 與 seq2 唯一差別是事件表。
 V3 輸出夾、乾跑夾改到上列新夾；TM 參考價表解壓夾 ~/tko3work。
 V4 cmp：E1、E2（含 v1b）全部列、全部欄（頻率表欄＋報酬欄）與 seq2 原 events.csv.gz 逐字相同；表.csv 中 E1／E2 組逐格相同；
    E3 組列新舊主數字差（可接、n_eff、X 平均、中位、勝率、CI）。
"""
from __future__ import annotations

import gzip
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTakeover_freq as TF            # noqa: E402
from backtest import researchTakeover as TM                 # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402

EV_SHA = "99159a0de9"
OLD_F, OLD_M = TF.OUT, TM.OUT
OUT_F = "backtest/resultsTakeover/e3v4_freq"
OUT_M = "backtest/resultsTakeover/e3v4_main"
WORK3 = os.path.expanduser("~/tko3work")
PRICE_SHA = json.load(open(os.path.join(OLD_F, "freq.json"), encoding="utf-8"))["origin/main"]

_load = TF.load_table
_ens = RT.ensure_data


def setup():
    import subprocess
    full = subprocess.run(["git", "rev-parse", EV_SHA], capture_output=True, text=True, check=True).stdout.strip()
    TF.load_table = lambda sha: _load(full)                             # V1
    RT.ensure_data = lambda sha=None: _ens(PRICE_SHA)                   # V2
    TF.OUT = OUT_F; TM.FREQ_DIR = OUT_F; TM.OUT = OUT_M; TM.WORK = WORK3  # V3
    os.makedirs(WORK3, exist_ok=True)
    return full


def cmp():
    rows = []
    for tag, od, nd in (("freq", OLD_F, OUT_F), ("main", OLD_M, OUT_M)):
        O = pd.read_csv(os.path.join(od, "events.csv.gz"), dtype=str, keep_default_na=False)
        N = pd.read_csv(os.path.join(nd, "events.csv.gz"), dtype=str, keep_default_na=False)
        for cls in ("E1", "E2", "E2b"):
            o = O[O["類"] == cls].reset_index(drop=True); n = N[N["類"] == cls].reset_index(drop=True)
            same = list(o.columns) == list(n.columns) and len(o) == len(n) and bool((o == n).all().all())
            rows.append({"項": f"{tag} events {cls} 逐列逐欄相同", "值": same, "註": f"列 {len(o)}→{len(n)}"})
        o3 = O[O["類"] == "E3"]; n3 = N[N["類"] == "E3"]
        ko = set(zip(o3["sid"], o3["date"])); kn = set(zip(n3["sid"], n3["date"]))
        rows.append({"項": f"{tag} events E3 列數", "值": f"{len(o3)}→{len(n3)}", "註": f"剔 {sorted(ko - kn)}；新增 {sorted(kn - ko)}"})
        if tag == "freq":
            m = o3.merge(n3, on=["sid", "date"], suffixes=("_o", "_n"))
            for c in ("st", "配對", "配對sid", "市值組"):
                rows.append({"項": f"freq E3 共同列 {c} 不同", "值": int((m[c + "_o"] != m[c + "_n"]).sum()), "註": f"共同 {len(m)} 列"})
            ok = o3[(o3["st"] == "保留")]; rm = ok[[k not in kn for k in zip(ok["sid"], ok["date"])]]
            rows.append({"項": "freq 被剔 E3 中可接價格", "值": len(rm), "註": str(list(zip(rm["sid"], rm["date"])))})
    TO = pd.read_csv(os.path.join(OLD_M, "表.csv"), encoding="utf-8-sig"); TN = pd.read_csv(os.path.join(OUT_M, "表.csv"), encoding="utf-8-sig")
    key = ["段", "組", "窗"]
    M = TO.merge(TN, on=key, how="outer", suffixes=("_o", "_n"), indicator=True)
    num = [c for c in TO.columns if c not in key]
    e12 = M[M["組"].str.startswith(("E1", "E2"))]
    diff = 0
    for c in num:
        a, b = e12[c + "_o"], e12[c + "_n"]
        diff += int((~((a == b) | (a.isna() & b.isna()))).sum())
    rows.append({"項": "表.csv E1／E2 組逐格相同", "值": diff == 0 and bool((e12["_merge"] == "both").all()), "註": f"格數 {len(e12)}×{len(num)}；不同 {diff}"})
    e3 = M[M["組"].str.startswith("E3")].copy()
    D = []
    for _, r in e3.iterrows():
        d = {"段": r["段"], "組": r["組"], "窗": r["窗"]}
        for c in ("可接", "X_n", "X_n_eff", "R平均", "X平均", "X中位", "X勝率", "X_lo", "X_hi", "CI結果(描述)"):
            d[f"{c}_seq2"] = r[c + "_o"]; d[f"{c}_v4"] = r[c + "_n"]
        D.append(d)
    D = pd.DataFrame(D)
    D["X平均差"] = D["X平均_v4"] - D["X平均_seq2"]
    D["CI結果同"] = D["CI結果(描述)_seq2"] == D["CI結果(描述)_v4"]
    D.to_csv(os.path.join(OUT_M, "對照seq2_E3.csv"), index=False, encoding="utf-8-sig")
    PO = pd.read_csv(os.path.join(OLD_M, "先驗.csv"), encoding="utf-8-sig"); PN = pd.read_csv(os.path.join(OUT_M, "先驗.csv"), encoding="utf-8-sig")
    for (_, a), (_, b) in zip(PO.iterrows(), PN.iterrows()):
        rows.append({"項": f"先驗 {str(a['先驗'])[:12]}", "值": f"{a.get('結果')}→{b.get('結果')}", "註": f"X平均 {a.get('X平均')}→{b.get('X平均')}"})
    full = D[(D["段"] == "全期(2005～)")]
    rows.append({"項": "E3 組全期各窗：X平均最大絕對差", "值": float(np.nanmax(np.abs(full["X平均差"]))) if len(full) else None,
                 "註": f"CI 結果改變的格 {int((~full['CI結果同']).sum())}／{len(full)}"})
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(OUT_M, "對照seq2.csv"), index=False, encoding="utf-8-sig")
    print(R.to_string())
    print(D[(D["段"] == "全期(2005～)") & D["組"].isin(["E3", "E3_有減資", "E3_無減資"])][
        ["組", "窗", "X_n_seq2", "X_n_v4", "X平均_seq2", "X平均_v4", "X中位_seq2", "X中位_v4", "X勝率_seq2", "X勝率_v4", "CI結果(描述)_seq2", "CI結果(描述)_v4"]].to_string())


def main():
    mode = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    full = setup()
    print(f"[E3 v4] 事件表 sha {full}｜價格等 sha {PRICE_SHA}", flush=True)
    if mode == "freq":
        TF.main()
    elif mode == "main":
        TM.main()
    elif mode == "cmp":
        cmp()
    else:
        raise SystemExit("mode ＝ freq｜main｜cmp")


if __name__ == "__main__":
    main()

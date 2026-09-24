# -*- coding: utf-8 -*-
"""研究十五 主格的 cond_exit 邊界例外次數（A2／A3）——r11_boundary.py 的同族延伸（⛔ 不改共用引擎、⛔ 不改交件）。

研究十五的 A2／A3 與研究十一一樣是【有狀態】的 ATR 追蹤停損 ⇒ ⛔ 不重放 cond，沿用 r11_boundary.classify（只看引擎回傳）。
驅動：研究十五的 worker 在子行程裡跑、每個變體對同一根 k 會各叫一次 ⇒
   ⭐ 在【fork 之前】把 research11.cond_exit 換成包裝 ⇒ 子行程繼承；每個 worker 回傳自己的逐呼叫紀錄
   ⇒ 用 (sid, k, 規則) 去重後，對到「主格」＝ variant main、B3、gate_ok & liq_ok、去重 20（research15.dedup，與交件同一支）
錨：主格列數 vs 交件 summary.md 的 n＝5,525（09-13 產出；快照不同 ⇒ 差多少據實報，⛔ 不硬對）
用法：python r15_boundary.py [--limit N] [--procs 4]
"""
from __future__ import annotations
import os
import sys
import time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import r11_boundary as B                      # fixture、classify、rule_of 同一份
from backtest import data as D
from backtest import research11 as R
from backtest import research15 as R15

REC = []


def wrap15(o, c, k, nb, cond):
    r = B._orig(o, c, k, nb, cond)
    lab, idx = B.classify(o, c, k, nb, r)
    REC.append((B._CTX["sid"], k, B.rule_of(cond), lab, idx))
    return r


def run_one(t):
    del REC[:]
    B._CTX["sid"] = t[0]
    out = R15.worker(t)
    return (None if out is None else out["rows"]), list(REC)


if __name__ == "__main__":
    B.fixture()                                   # ⭐ 先證明分類器會響
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 4
    cal = D.load_calendar(); uni = D.load_universe()
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"]
    uni = uni[~uni["stock_id"].map(ind).isin(R15.EXCL_IND)]          # 與 research15.main 同一道
    if lim:
        uni = uni.head(lim)
    disp = D.load_disposal_intervals(); att = D.load_attention_dates(); marg = R15.load_margin_o()
    R.cond_exit = wrap15                          # ⭐ fork 之前換 ⇒ 子行程繼承
    t0 = time.time(); rows = []; recs = []
    with Pool(procs, initializer=R15._init, initargs=(cal, disp, att, marg)) as pool:
        for i, (rw, rc) in enumerate(pool.imap_unordered(run_one, list(zip(uni["stock_id"], uni["market"])), chunksize=8)):
            if rw:
                rows.extend(rw)
            recs.extend(rc)
            if (i + 1) % 300 == 0:
                print("  {}/{}  {:.0f}s".format(i + 1, len(uni), time.time() - t0), file=sys.stderr, flush=True)
    R.cond_exit = B._orig
    df = pd.DataFrame(rows)
    df = df[df["kind"] != "ERROR"].copy()
    df["gate_all"] = df["gate_ok"] & df["liq_ok"]
    dd = R15.dedup(df)
    M = dd[(dd.variant == "main") & (dd.kind == "B3") & dd.gate_all]
    Rc = pd.DataFrame(recs, columns=["sid", "k", "rule", "lab", "idx"])
    others = Rc[~Rc["rule"].isin(["A2", "A3"])]
    assert others.empty, "⛔ 有辨識不出規則的呼叫：{}".format(others["rule"].value_counts().to_dict())
    # 同一 (sid,k,規則) 在不同變體被叫多次 ⇒ 結果必須一致，再去重
    chk = Rc.groupby(["sid", "k", "rule"])["lab"].nunique()
    assert (chk == 1).all(), "⛔ 同一根 k 同一規則在不同變體分類不同"
    Ru = Rc.drop_duplicates(["sid", "k", "rule"])
    J = M[["sid", "k", "month"]].merge(Ru, on=["sid", "k"], how="left")
    nnull = int(J["rule"].isna().sum())
    print("\n=== 快照：日曆 {} 根／尾 {}｜跑 {} 檔｜主格 B3 過閘門去重 {:,} 列（交件 09-13 為 5,525）｜{:.0f}s ===".format(
        len(cal), cal[-1].date(), len(uni), len(M), time.time() - t0))
    print("  主格列沒有任何 A2／A3 呼叫（atr[k] 為 NaN ⇒ 引擎不叫）：{} 列".format(nnull // 1 if nnull else 0))
    out = []
    for rl in ("A2", "A3"):
        s = J[J["rule"] == rl]["lab"].value_counts()
        tot = int(s.sum()); exc = int(s[[x for x in s.index if x.startswith("exc_")]].sum())
        amb = int(s[[x for x in s.index if x.startswith("ambig")]].sum()); none_ = int(s.get("none_窗不足", 0))
        out.append(dict(規則=rl, 主格呼叫=tot, 例外=exc, 無法區分=amb, 正常=int(s.get("normal_次日開盤", 0)),
                        抱到上限=int(s.get("cap_抱到上限", 0)), 窗不足=none_,
                        有效出場=tot - none_, 例外占有效出場=round(exc / max(1, tot - none_) * 100, 4)))
    T = pd.DataFrame(out)
    print(T.to_string(index=False))
    E = J[J["lab"].astype(str).str.startswith(("exc_", "ambig"))]
    if len(E):
        print("\n例外／無法區分逐類：")
        print(E.groupby(["rule", "lab"]).size().to_string())
    alls = Ru["lab"].value_counts()
    print("\n（參考）全部變體、全部種類去重後的呼叫分類：", alls.to_dict())
    if not lim:
        os.makedirs("backtest/results_step2", exist_ok=True)
        T.to_csv("backtest/results_step2/r15_boundary_tally.csv", index=False, encoding="utf-8")
        E.to_csv("backtest/results_step2/r15_boundary_cases.csv", index=False, encoding="utf-8")
        print("⇒ 落檔 backtest/results_step2/r15_boundary_tally.csv、r15_boundary_cases.csv")

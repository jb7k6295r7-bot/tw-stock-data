"""P5 用新尺（型態線 20260923-2053 裁：對齊窗 3 個交易日）重掃 —— 回測線執行端。

⛔⛔ 本支【不重跑其他八個型態】：型態線 §五 逐字「⛔ 沒有動 P3_false_breakout 的尺」，
    其餘型態這次也都沒有動 ⇒ ⭐ 只有 P5 的訊號集合會變。

⭐⭐ 不複製 run.py：本支把 run.py 其餘偵測器【就地換成空函式】，然後呼叫
   run.py 自己的 `process_stock` ⇒ 母體、gate、處置股遮罩、斷點剔除窗、
   evaluate_signal 全部走【同一條正典路徑】。
   ⇒ ⛔ 這是 2026-09-23「四點五」（重造市值實作）的教訓：⛔ 不維護第二份實作。

⛔⛔ 錨點的第一版【錯了】，這裡逐字交代（⚠ 不可以只留修好的版本）：
   本支原本把閘門設成「k=0 重掃 ＝ 已交件的 signals.csv.gz 的 P5 逐筆相同」。
   ⇒ 實跑 12,578 vs 12,581，⛔ 不過。
   ⇒ 查因：那份 signals.csv.gz 是在 ~/tw-stock-data（資料庫線的分支）上產生的，
     而本支跑在 ~/tw-p17 ⇒ ⭐⭐【兩棵樹的 data/ 是不同的快照】：
       ・日曆：2,852 vs 2,855（tw-p17 多 2026-09-16~18 三天；⭐ 前 2,852 筆完全相同 ⇒ 索引沒錯位）
       ・個股檔：逐一比 sha256 ⇒ ⛔ 不同（受影響個股 tw-p17 各多 5 行）
     ⇒ 差異分佈：只在交件檔 62 筆／只在本次 59 筆，⭐ 其中大量是【同一檔差 1 個位置】
   ⇒ ⭐⭐ 結論：那個閘門【在原理上不可能過】，⛔ 它量的是資料快照差，不是偵測器差。

⭐ 所以閘門改成【只量本支的改動】，⛔ 不再跨快照比：
   閘門A（硬）：同一棵樹、同一批資料，
                【原版 patterns.py 的 ma_cross_up】 vs 【本支 k=0】⇒ 必須逐筆且逐位元相同
                ⇒ 它證明「patterns.py 的這次修改，在 k=0 時什麼都沒動」
   對帳B（⛔ 不是閘門，只報）：本支 k=0 vs 已交件檔 ⇒ 報差異的【分佈】
   主結果    ：k=0 vs k=3，⭐ 兩邊【同一棵樹、同一批資料】⇒ 差的只有尺
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D          # noqa: E402
from backtest import patterns as P      # noqa: E402
from backtest import run as RUN         # noqa: E402

REF = os.path.expanduser("~/tw-stock-data/backtest/results/signals.csv.gz")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsp5win")

_EMPTY = ["P1", "P2", "P3", "P4"]
PRISTINE = "/tmp/patterns_pristine.py"          # git show a1757abb2:backtest/patterns.py


def _load_pristine():
    """把【修改前】的 patterns.py 載進來，只為了取它的 ma_cross_up。

    ⚠ 它只讀 f.p／f.ma5／f.ma10／f.ma20／f.gate／f.v／f.vol_ma20／f.c／f.n，
      而本支對 Frame 與 PARAMS 的數值【一個字都沒動】⇒ 餵本版的 Frame 給它是合法的。
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("patterns_pristine", PRISTINE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.ma_cross_up


def _neuter(k):
    """把 P5 以外的偵測器換成空函式 ⇒ ⭐ 只省時間，⛔ 不改 P5 那條路徑上的任何東西。

    k ＝ 整數 ⇒ 本版的 ma_cross_up(confirm_window=k)
    k ＝ "pristine" ⇒ ⭐ 修改【前】那一版的 ma_cross_up（閘門A 用）
    """
    for key in _EMPTY:
        P.DETECTORS[key] = lambda f, *_a, **_kw: []
    P.cup_handle = lambda *a, **kw: []          # P6 日線＋週線（run.py 直接呼叫它）
    RUN.P.cup_handle = P.cup_handle
    if k == "pristine":
        fn = _load_pristine()
        P.DETECTORS["P5"] = fn
    else:
        P.DETECTORS["P5"] = lambda f: P.ma_cross_up(f, confirm_window=int(k))
    RUN.P.DETECTORS = P.DETECTORS


def _initw(cal, bench, disp, attn, lo, hi, split, k):
    _neuter(k)
    RUN._init(cal, bench, disp, attn, lo, hi, split)


def scan(k, procs: int) -> pd.DataFrame:
    cal = D.load_calendar()
    uni = D.load_universe()
    bench_df = D.load_benchmark(cal)
    bench = {"o": bench_df["open"].to_numpy(float), "c": bench_df["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    attn = D.load_attention_dates()
    lo = int(cal.searchsorted(pd.Timestamp(RUN.SIG_START)))
    hi = int(cal.searchsorted(pd.Timestamp(RUN.SIG_END), side="right") - 1)
    split = int(cal.searchsorted(pd.Timestamp(RUN.SPLIT)))
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    t0 = time.time()
    with Pool(procs, initializer=_initw,
              initargs=(cal, bench, disp, attn, lo, hi, split, k)) as pool:
        res = [r for r in pool.imap_unordered(RUN.process_stock, jobs, chunksize=8) if r is not None]
    rows = [s for r in res for s in r["signals"] if s["pattern"] == "P5_ma_cross_up"]
    d = pd.DataFrame(rows)
    print("[k={}] {:,} 檔掃完，P5 {:,} 筆（{:.0f}s）".format(k, len(res), len(d), time.time() - t0))
    return d.sort_values(["stock_id", "signal_pos"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    # ── ⭐⭐ 閘門A（硬）：原版 ma_cross_up vs 本版 k=0，同一棵樹同一批資料 ──────
    pris = scan("pristine", a.procs)
    old = scan(0, a.procs)
    key = ["stock_id", "signal_pos", "entry_pos"]
    same_key = len(pris) == len(old) and pris[key].equals(old[key])
    num = [c for c in ("conv", "vol_x", "entry_price", "ret_hold_net")
           if c in old.columns and c in pris.columns]
    worst = {c: float(np.nanmax(np.abs(old[c].to_numpy(float) - pris[c].to_numpy(float))))
             for c in num} if same_key else {}
    print("[閘門A] 原版 {:,} 筆　本版k=0 {:,} 筆　鍵逐筆相同 {}"
          .format(len(pris), len(old), same_key))
    for c, v in worst.items():
        print("        {:<14} 最大絕對差 {:.3e}".format(c, v))
    if not same_key or any(v > 0 for v in worst.values()):
        old.to_csv(os.path.join(OUT, "p5_k0_MISMATCH.csv"), index=False)
        pris.to_csv(os.path.join(OUT, "p5_pristine_MISMATCH.csv"), index=False)
        raise SystemExit("⛔⛔ 閘門A 不過：本支對 patterns.py 的修改在 k=0 時改變了結果 "
                         "⇒ 停止，⛔ k=3 的數字一個都不可以引用")
    print("[閘門A] ✅ 原版與本版 k=0【逐筆且逐位元相同】")
    print("        ⇒ ⭐ 這次對 patterns.py 的修改，在舊尺底下【什麼都沒有動】")

    # ── 對帳B（⛔ 不是閘門）：本支 k=0 vs 已交件檔 ⇒ 只報差異的分佈 ────────────
    ref = pd.read_csv(REF, dtype={"stock_id": str})
    ref = ref[ref["pattern"] == "P5_ma_cross_up"].sort_values(
        ["stock_id", "signal_pos"]).reset_index(drop=True)
    ko = set(zip(old["stock_id"], old["signal_pos"]))
    kr = set(zip(ref["stock_id"], ref["signal_pos"]))
    only_r, only_o = sorted(kr - ko), sorted(ko - kr)
    # ⭐ 差的分佈：有多少是「同一檔、位置差 ≤2」的位移，而不是憑空多出／消失
    ro = {}
    for s, p_ in only_o:
        ro.setdefault(s, []).append(p_)
    shift = sum(1 for s, p_ in only_r if any(abs(q - p_) <= 2 for q in ro.get(s, [])))
    print()
    print("[對帳B] ⛔ 不是閘門：本支 k=0 vs 已交件 signals.csv.gz")
    print("        已交件 {:,} 筆／本支 k=0 {:,} 筆／共同 {:,} 筆"
          .format(len(ref), len(old), len(ko & kr)))
    print("        只在交件檔 {} 筆／只在本支 {} 筆；其中【同一檔位置差 ≤2】的位移 {} 筆"
          .format(len(only_r), len(only_o), shift))
    print("        ⇒ ⭐ 成因是【兩棵樹的 data/ 是不同快照】（日曆 2,852 vs 2,855、個股檔 sha 不同），")
    print("          ⛔ 不是偵測器差 —— 閘門A 已經把偵測器那一側釘死了。")
    print("        ⚠ 差的量級：{:.2%} of {:,} ⇒ ⛔ 下面的 k=0 vs k=3 全部在【同一快照】上算，"
          .format(len(only_r) / len(ref), len(ref)))
    print("          ⇒ ⭐ 所以倍數是乾淨的，⛔ 但【絕對筆數】不可與交件檔的 12,581 直接相減。")

    # ── 新尺 ────────────────────────────────────────────────────────────────
    new = scan(P.P5_CONFIRM_WINDOW, a.procs)
    old.to_csv(os.path.join(OUT, "p5_k0.csv.gz"), index=False)
    new.to_csv(os.path.join(OUT, "p5_k3.csv.gz"), index=False)

    print()
    print("=== ⭐ P5 訊號筆數：舊尺 vs 新尺 ===")
    print("  舊尺（同日）      {:,} 筆／{:,} 檔".format(len(old), old["stock_id"].nunique()))
    print("  新尺（±3 日）     {:,} 筆／{:,} 檔".format(len(new), new["stock_id"].nunique()))
    print("  ⇒ 倍數 {:.2f}x（＋{:,} 筆）".format(len(new) / len(old), len(new) - len(old)))
    print()
    g = new["confirm_gap"].astype(int)
    print("=== ⭐ 新增的那些是怎麼來的：confirm_gap ＝ 放量日 − 上穿日 ===")
    vc = g.value_counts().sort_index()
    for k_, v in vc.items():
        print("  gap {:+d}：{:>7,} 筆（{:.1%}）{}".format(
            int(k_), int(v), v / len(g), "  ← 舊尺抓得到的就是這一格" if k_ == 0 else ""))
    print()
    print("  ⚠ gap ＝ 0 的筆數 {:,}　vs 舊尺 {:,}".format(int((g == 0).sum()), len(old)))
    print("  ⇒ ⭐ 兩者應該【幾乎相同】：gap=0 就是「上穿與放量同日」那一格。")
    print("    ⛔ 若差很多 ⇒ 表示新尺把舊尺的某些訊號【移走或吃掉】了，要查。")

    # ⭐ 舊尺的訊號有沒有【全部】留在新尺裡（⛔ 放寬不應該弄丟東西）
    ok = old.merge(new[["stock_id", "signal_pos"]].assign(_in=1),
                   on=["stock_id", "signal_pos"], how="left")
    lost = int(ok["_in"].isna().sum())
    print()
    print("=== ⛔ 放寬之後【弄丟】的舊訊號：{:,} 筆 ===".format(lost))
    if lost:
        ok[ok["_in"].isna()].to_csv(os.path.join(OUT, "p5_lost.csv"), index=False)
        print("  ⚠ 名單已寫 p5_lost.csv ⇒ ⭐ 成因：新尺的事件日可能被推到【較晚】那一天，")
        print("    或同一個事件日被去重合併 ⇒ ⛔ 這不是 bug，但必須報出來。")
    print()
    print("[輸出] {}".format(OUT))


if __name__ == "__main__":
    main()

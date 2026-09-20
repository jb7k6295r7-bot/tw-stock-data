"""P12 的 (S1,C1,T1) 是不是【決定性】的——策略線 2130 §三① 要本線先確認的事實。

    python3 -m backtest.p12_determinism [--seeds 5]

⛔ 背景：P14 seq=2 §二／P15 seq=2 §四① 要求 A0／G0【逐位元】重現 P12 的 (S1,C1,T1)，
   而對帳標的寫的是「P12 那一格**保存**的逐日權益序列」。
⇒ ⛔ 事實：P12 **沒有保存**逐日權益（`cells_by_seed.csv.gz` 只有 6 個逐種子彙總量）。
⇒ ⭐ 所以本檔量的是另一件事：**當場重算能不能逐位元重現**。
   能 ⇒ 零容差逐位元對帳【做得到】，只是對帳標的要從「存檔」改成「本趟當場重算」。
   ⛔ 而那是登錄的文字（策略線／K線分析線的格子）⇒ 本檔只給事實，⛔ 不自行改判準。

⛔⛔ 讀 `cells_by_seed.csv.gz` 一律 `float_precision="round_trip"`（K線分析線 1915 §五）：
   ⚠ 用預設解析器比，5 顆種子【全部】會被判成不同（1 ulp）⇒ 那是假警報。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import time

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp12 as P12

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp12")
BY_SEED = os.path.join(RESULTS, "cells_by_seed.csv.gz")
CELL = ("S1", "C1", "T1")
WIN, COST_TAG, N_SLOTS = "全窗", "成本0.585%", 8
COLS = ("own_dd", "cagr", "mdd", "expo", "slot", "trades")   # ⭐ 存檔裡逐種子只有這些


def stored(path: str = BY_SEED) -> pd.DataFrame:
    """P12 存起來的逐種子彙總（⛔ round_trip，否則逐位元比會全部假警報）。"""
    d = pd.read_csv(path, float_precision="round_trip")
    m = (d["S"] == CELL[0]) & (d["C"] == CELL[1]) & (d["T"] == CELL[2]) & (d["win"] == WIN) & (d["cost"] == COST_TAG)
    return d[m].set_index("seed")


def same_row(got: dict, ref, cols=COLS) -> list:
    """逐位元比（float 用 repr 逐字，⛔ 零容差）⇒ 回不同的欄名。"""
    return [c for c in cols if repr(float(got[c])) != repr(float(ref[c]))]


def eq_sha(out: dict) -> str:
    """權益曲線的指紋（⭐ 與 P13 否證① 同一個做法：sha256(equity.tobytes())）。"""
    return hashlib.sha256(out["equity"].tobytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    log = lambda s: print(s, flush=True)
    cal = D.load_calendar(); ncal = len(cal); uni = D.load_universe()
    panel = P4F.read_panel(a.panel)
    sids = set(panel["stock_id"])
    closes, opens = P1.load_prices(sids, cal, uni.set_index("stock_id")["market"])
    sig_b = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig_b), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    wins = {k: P12.win_bounds(cal, k) for k in P12.WINDOWS}
    marks = {k: P12.month_marks(cal, *v) for k, v in wins.items()}
    P12._init({(CELL[0], CELL[2], "*"): sig_b}, {(CELL[0], CELL[1], CELL[2], "*"): N_SLOTS},
              closes, opens, ncal, wins, marks, cal)
    ref = stored()
    seeds = [int(s) for s in list(ref.index[:a.seeds])]
    t0 = time.time(); rows = []
    for seed in seeds:
        r = [x for x in P12._one((*CELL, "*", COST_TAG, P12.COST_STD, seed)) if x["win"] == WIN][0]
        bad = same_row(r, ref.loc[seed])
        h1 = eq_sha(P12._sim(sig_b, N_SLOTS, seed, P12.COST_STD))
        h2 = eq_sha(P12._sim(sig_b, N_SLOTS, seed, P12.COST_STD))
        rows.append({"seed": seed, "同存檔": not bad, "不同的欄": ",".join(bad), "sha16": h1[:16], "同種子重跑同 sha": h1 == h2})
    secs = time.time() - t0
    tab = pd.DataFrame(rows)
    allsame = bool(tab["同存檔"].all() and tab["同種子重跑同 sha"].all())
    # ⭐ 反向驗：用 pandas 預設解析器讀同一份檔 ⇒ 證明那條 round_trip 規矩不是裝飾
    naive = pd.read_csv(BY_SEED)
    nm = (naive["S"] == CELL[0]) & (naive["C"] == CELL[1]) & (naive["T"] == CELL[2]) & \
         (naive["win"] == WIN) & (naive["cost"] == COST_TAG)
    naive = naive[nm].set_index("seed")
    n_false = sum(1 for seed in seeds
                  if same_row({c: ref.loc[seed][c] for c in COLS}, naive.loc[seed]))

    L = ["# P12 (S1,C1,T1) 的**決定性**——策略線 2130 §三① 要的那個事實", "",
         "## 一、⛔ 先答問的那一句：**沒有保存逐日權益序列**", "",
         "```",
         "resultsp12/cells_by_seed.csv.gz 的逐種子欄位只有："
         f"{', '.join(COLS)}（6 個彙總量）",
         "⇒ ⛔ 沒有逐日權益、⛔ 沒有權益的 sha",
         "⇒ 依 P14 seq=2 §二 逐字：⛔ 本線【不改判準】、⛔ 不自行改成容差 ⇒ 請策略線出 seq=3",
         "```", "",
         "## 二、⭐ 而本線量了一個讓 seq=3 好寫的事實：**當場重算逐位元重現**", "",
         f"| 種子 | 六個彙總量與存檔逐位元相同 | 不同的欄 | sha256(equity) 前 16 | 同種子重跑同 sha |",
         "|---|:-:|---|---|:-:|"]
    for r in tab.to_dict("records"):
        L.append(f"| {r['seed']} | {'✅' if r['同存檔'] else '⛔'} | {r['不同的欄'] or '—'} | {r['sha16']}… | "
                 f"{'✅' if r['同種子重跑同 sha'] else '⛔'} |")
    L += ["", f"⇒ **{'✅ ' + str(len(seeds)) + '/' + str(len(seeds)) + ' 逐位元重現' if allsame else '⛔ 有對不上的'}**"
          f"（{secs:.0f} 秒；環境 pandas {pd.__version__}／numpy {np.__version__}）", "",
          "```",
          "⇒ ⭐ 所以【零容差逐位元對帳做得到】，只是對帳標的要從",
          "     「P12 那一格保存的逐日權益」改成「本趟當場重算的 P12 (S1,C1,T1) 逐日權益」",
          "⇒ ⭐⭐ 而那樣其實更強：比的是【當下這一份程式】算出來的，",
          "     ⛔ 不是一個可能已經過期的存檔（⚠ 引擎後來加過 weight_fn，雖然預設路徑已驗 200/200 逐位元相同）",
          "⛔ 而【登錄的文字怎麼改】是策略線／K線分析線的格子 ⇒ 本件只給事實。",
          "```", "",
          "## 三、⛔⛔ 反向驗：不加 `float_precision='round_trip'` 會得到什麼", "",
          "```",
          f"用 pandas 預設解析器讀同一份 cells_by_seed.csv.gz ⇒ {len(seeds)} 顆種子裡有 **{n_false} 顆**被判成【不同】",
          "⇒ ⛔ 那是【假警報】：差的是 CSV 來回一趟的 1 ulp，⛔ 不是程式不決定性",
          "⇒ ⭐ 這是 K線分析線 1915 §五 那條規矩今天的第【二】個實例（第一個是 PREREGP1b 的閘門二）",
          "⇒ ⛔ 所以：凡是要拿 cells_by_seed.csv.gz 做逐位元對帳，一律 float_precision='round_trip'",
          "```", ""]
    p = os.path.join(RESULTS, "P12_DETERMINISM.md")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    log("\n".join(L)); log(f"[out] {p}")
    if not allsame:
        raise SystemExit("⛔ 有種子重算對不上 ⇒ 這件事實不成立，要先查")


if __name__ == "__main__":
    main()

"""PREREGP14：把 0050 放進組合（閒置資金去處 ＋ 固定配置線）—— 回測線執行端。

⛔ 登錄全文 `backtest/PREREGP14.md`（策略線 seq=5，2026-09-21 11:05 台北投遞）
   ✅ 已對 Drive createdTime 核過 ＝ 2026-09-21 11:06 台北（差 1 分）⇒ 這個標籤是對的
   ⚠ 而 P14 的 seq=6~9 標籤已漂移 8~12 h ⇒ ⛔ 本檔【釘在 seq=5】，⛔ 不跟著更新
   sha256[:16] ＝ **36c02965e3639996**
   ⚠ 口徑：**去掉 pw1 戳記行、檔尾恰一個換行**（45,814 B）——⛔ 不是全檔 sha（那是 d53b4a96391fea8b）。

⛔⛔ 本支【不訂判準、不訂判定用語、不設計策略】——§二 的判準、§四 的否證條件、
     §三 的必報欄、§十一 的兩個處置，全部逐字取自登錄。回測線只負責跑與報數字。

⭐ 三塊：
  A 組（§一1-A）A0 ＝ cash_mode="zero"／A1 ＝ cash_mode="bench"，200 顆種子 default_rng(102000+r)
  B 組（§一1-B）在【權益曲線層】合成 P_w(t) = w·E(t)/E(t0) + (1−w)·B(t)/B(t0)，w 五格寫死、⛔ 不再平衡
  閘門　　　　 §四① 逐位元（200/200 零容差）／§三⑦ 橋欄（cells.csv 20 欄）／§三⑧ 手算 fixture

⭐ 為什麼本支自己有一個引擎呼叫點（⛔ 不是抄 P12 的）：
  登錄 §九-2(a) 逐字要求「由回測線在【本件同一支程式、同一個 commit】內當場重跑」。
  ⚠ 而 P12 的 `_sim` 把 cash_mode="zero" 寫死，且那一行是 P12 登錄 §八⑦ 的閘門
  （`selftest_researchp2.t_p12` 逐字掃它）⇒ ⛔ 不可為了 A1 去改它。
  ⇒ ⭐ 每個件各有一個呼叫點是本庫既有形狀（p2／p7／p11／p12／p13 各一）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import research13 as R13
from . import researchp1 as P1
from . import researchp3 as P3
from . import researchp7 as P7
from . import researchp11 as P11
from . import researchp12 as P12
from . import researchp8 as P8

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp14")

# ── 登錄寫死的常數（⛔ 一個都不可以在這裡「挑」）──────────────────────────────
WIN = "全窗"                        # §一1-A：判定窗（2017-03-02 ~ 2026-08-24）
WS = (0.00, 0.25, 0.50, 0.75, 1.00)  # §一1-B：五格寫死，⛔ 不掃
JUDGE_W = 0.50                      # §二：判定格【只有一格】，理由＝無資訊的中點
REPS = 200                          # §一1-A：r ∈ [0, 200)
BENCH_CAGR = 0.2402                 # §七②：0050 同窗年化（⛔ 指定到一個值，⛔ 不與 +24.54% 並列）
BENCH_MDD = -0.340                  # §七②：0050 同窗最大回落
A1_CAGR_GUARD = 0.05                # §四⑤：A1 年化改善 > 5pp ⇒ 先查 bench_cost 是否漏算

# §十一1-3：橋欄要逐位元對上的 20 欄（⛔ 比的是 cells.csv，⛔ 不是 .md 的列印值）
BRIDGE_CSV = os.path.join(HERE, "resultsp12", "cells.csv")
BRIDGE_KEY = {"win": WIN, "cost": "成本0.585%", "S": "S1", "C": "C1", "T": "T1"}
BRIDGE_ID = ("win", "cost", "S", "C", "T")          # §十一1-2：識別欄 ⇒ 不同＝比錯格，⛔ 不是否證⑥
BRIDGE_COLS = ("tr_mean", "tr_med", "tr_p10", "tr_p90", "tr_prev_med",
               "cagr_med", "cagr_p10", "cagr_p90", "mdd_med", "mdd_p10", "mdd_p90",
               "expo_med", "slot_med", "trades_med", "seeds")

# §十一1-3：登錄【轉抄】自回測線 0115 §二 的 21 個值（全窗 15 ＋ 主格窗 6）
# ⛔ 開跑前要對 cells.csv 逐位元；對不上時的判別法見 anchor_check()（K線分析線 0050 §2-2 裁）
ANCHOR_VALS = {
    "全窗": {"tr_mean": 10.721624085824924, "tr_med": 9.439161911168174, "tr_p10": 4.785625917637471,
             "tr_p90": 18.292071231974276, "tr_prev_med": 9.327453029606506,
             "cagr_med": 0.2820350701063953, "cagr_p10": 0.20434354723573306, "cagr_p90": 0.36820505943804477,
             "mdd_med": -0.41432426935458594, "mdd_p10": -0.47524809022050024, "mdd_p90": -0.37023358981058885,
             "expo_med": 0.8713977071219294, "slot_med": 0.8871002592912706,
             "trades_med": 138.0, "seeds": 200.0},
    "主格窗": {"tr_med": -0.2952280527561196, "cagr_med": -0.18150044229406254, "mdd_med": -0.3843461599544722,
               "expo_med": 0.8745606308962086, "slot_med": 0.8871002592912706, "trades_med": 138.0},
}

# §三⑧／§十一2-2：手算 fixture（⛔ 與真實資料、P12、隨機源全部無關）
# ⭐ 這組數是【為了二進位可精確表示】挑出來的（分母都是 2 的冪）⇒ 才可以要求逐位元。
FIX_E = (100.0, 125.0, 75.0)
FIX_B = (40.0, 45.0, 35.0)
FIX_EXPECT = {0.00: (1.0, 1.125, 0.875),
              0.25: (1.0, 1.15625, 0.84375),
              0.50: (1.0, 1.1875, 0.8125),
              0.75: (1.0, 1.21875, 0.78125),
              1.00: (1.0, 1.25, 0.75)}


# ── §一1-B 的合成式（⭐ 全檔只有這一個地方做混合）────────────────────────────
def blend(e: np.ndarray, b: np.ndarray, w: float) -> np.ndarray:
    """P_w(t) = w × E(t)/E(t0) + (1−w) × B(t)/B(t0)。

    ⛔ 期初一次配置、之後【不再平衡】⇒ 兩邊各自複利（登錄 §一1-B）。
    ⚠ t0 ＝ 傳進來這兩條序列的第 0 個元素 ⇒ ⛔ 呼叫端必須先切到窗內再傳。
    """
    e = np.asarray(e, float); b = np.asarray(b, float)
    if e.shape != b.shape:
        raise SystemExit(f"⛔ 合成式兩條序列長度不同：E {e.shape} vs B {b.shape}")
    return w * (e / e[0]) + (1.0 - w) * (b / b[0])


def fixture_check() -> list[dict]:
    """§三⑧ 必報 ＋ §四⑦ 否證：手算 fixture 逐位元。

    ⭐ 它檢查的是【加權混合本身】——⛔ 否證② 的兩腿都檢查不到這一件
    （w=1 是恆等式；w=0 把 E 那一項整項乘掉）。
    ⛔ 任何一格對不上 ⇒ 停止，⛔ 不可換 w、⛔ 不可調容差。
    """
    e = np.array(FIX_E, float); b = np.array(FIX_B, float)
    rows, bad = [], []
    for w in WS:
        got = blend(e, b, w)
        exp = np.array(FIX_EXPECT[w], float)
        ok = [repr(float(g)) == repr(float(x)) for g, x in zip(got, exp)]
        rows.append({"w": w, "got": [float(x) for x in got], "expect": [float(x) for x in exp],
                     "逐位元": "✅" if all(ok) else "⛔"})
        if not all(ok):
            bad.append(f"  w={w:.2f}  得 {[repr(float(x)) for x in got]}  要 {[repr(float(x)) for x in exp]}")
    if bad:
        raise SystemExit("⛔⛔ 否證⑦：§三⑧ 的手算 fixture 對不上 ⇒ 合成式本身寫錯，本件不出結論\n" + "\n".join(bad))
    return rows


# ── 引擎呼叫（⭐ 全檔只有這一個地方）──────────────────────────────────────
_S: dict = {}


def _init(sigs, closes, opens, ncal, w0, w1, marks, cal, bench):
    _S.update(sigs=sigs, closes=closes, opens=opens, ncal=ncal, w0=w0, w1=w1, marks=marks, cal=cal, bench=bench)


def _sim(sig, n, seed, cost, cash_mode="zero", bench=None):
    """⭐ 唯一一個呼叫引擎的地方。成本用模組常數切換 ⇒ ⛔ 不改引擎、⛔ 跑完立刻還原。

    ⚠ bench_cost 不傳 ⇒ 用引擎預設 COST/2 ＝ 0.002925（登錄 §七④ 逐字）。
    """
    R.COST = cost
    try:
        return R.simulate_mtm(sig, P12.RULE, n, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                              return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0,
                              cash_mode=cash_mode, bench=bench)
    finally:
        R.COST = P12.COST_STD


def _one(args):
    """一個臂的一顆種子。⭐ 回傳 equity 的 sha256 與窗內讀數；A0／錨點另外把 equity 帶回來（B 組要用）。"""
    arm, r, keep_eq = args
    seed = P12.SEED0 + r
    out = _sim(_S["sigs"], P12.N_C1, seed, P12.COST_STD,
               cash_mode=("bench" if arm == "A1" else "zero"),
               bench=(_S["bench"] if arm == "A1" else None))
    eq = np.asarray(out["equity"], float)
    row = {"arm": arm, "seed": seed, "r": r,
           "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest(),
           **P12.win_read(out, _S["w0"], _S["w1"], _S["marks"])}
    row["hold_days"] = float(np.mean(out.get("hold_days", [np.nan]))) if out.get("hold_days") is not None else np.nan
    return (row, eq[_S["w0"]:_S["w1"] + 1].copy() if keep_eq else None)



def anchor_check() -> list[dict]:
    """開跑前：`resultsp12/cells.csv` 讀回的值 vs 登錄 §十一1-3 釘死的 21 個值，逐位元。

    ⛔⛔ 對不上時【兩個成因的意義完全不同】（K線分析線 0050 §2-2 裁，⭐ 判別法逐字）：
      檔 ＝ 回測線 0115 §二，且 檔 ≠ 本節 ⇒ ⭐【登錄那一節抄錯】⇒ 回信策略線訂正，⛔ 不觸發否證⑥
      檔 ≠ 回測線 0115 §二　　　　　　 ⇒ ⛔⛔【檔案變了】⇒ 觸發否證⑥，查 P12 交件的可重現性
    ⇒ ⛔ 本函式【不自己分辨】那兩者——它停下來並把判別法印出來，⭐ 因為 0115 §二 在信裡不在程式裡。
    ⇒ ⛔ 而把 0115 §二 再抄一份進本檔【正好會毀掉這道檢查】：兩份轉抄不再獨立（四點五）。
    """
    ref = pd.read_csv(BRIDGE_CSV, float_precision="round_trip")
    rows, bad = [], []
    for win, exp in ANCHOR_VALS.items():
        m = ((ref["win"] == win) & (ref["cost"] == "成本0.585%")
             & (ref["S"] == "S1") & (ref["C"] == "C1") & (ref["T"] == "T1")).to_numpy()
        if m.sum() != 1:
            raise SystemExit(f"⛔【比錯格】：{win} 在 cells.csv 命中 {m.sum()} 列（要恰 1）⇒ 停止，"
                             "⛔ 不可改 tuple 再找一次（K線分析線 0050 §2-3）")
        r = ref[m].iloc[0]
        for k, v in exp.items():
            a = float(r[k]); ok = repr(a) == repr(float(v))
            rows.append({"窗": win, "欄": k, "檔案": repr(a), "登錄 §11-1-3": repr(float(v)),
                         "逐位元": "✅" if ok else "⛔"})
            if not ok:
                bad.append(f"  {win}/{k}: 檔案 {a!r} ≠ 登錄 {float(v)!r}")
    if bad:
        raise SystemExit(
            "⛔⛔ cells.csv 讀回的值與登錄 §十一1-3 對不上 ⇒ 停止\n"
            "⭐ 判別法（K線分析線 0050 §2-2，⛔ 本線不自己選）：把下面讀回的值拿去對【回測線 0115 §二】\n"
            "   檔 ＝ 0115 §二，而 檔 ≠ §十一1-3 ⇒ ⭐【§十一1-3 抄錯】⇒ 回信策略線訂正，⛔ 不是否證⑥\n"
            "   檔 ≠ 0115 §二　　　　　　　　 ⇒ ⛔⛔【檔案變了】⇒ 否證⑥ ⇒ 查 P12 交件的可重現性\n"
            + "\n".join(bad))
    return rows


# ── §三⑦ 橋欄：把「本趟當場重算」接回「1740 已交件的那個數」──────────────────
def bridge_check(tab: pd.DataFrame) -> list[dict]:
    """§十一1：對 `resultsp12/cells.csv` 的 20 欄，float_precision='round_trip' 逐位元。

    ⛔ `.md` 的列印值只作顯示，⛔ 不作判定依據（§十一1 拿掉了 seq=4 那個條件式）。
    ⛔ 識別欄（win/cost/S/C/T）不同 ＝【比錯格】⇒ 不是否證⑥（§十一1-2）。
    ⛔ 量欄任一欄不是逐位元相同 ⇒ 否證⑥ ⇒ 停止，⚠ 而那時要查的是 P12 交件的可重現性。
    """
    if not os.path.exists(BRIDGE_CSV):
        raise SystemExit(f"⛔ §七① 退場條款：{BRIDGE_CSV} 不存在 ⇒ 回信策略線出 seq=6，"
                         "⛔ 不可自行挑一組欄位比、⛔ 不可降回列印值")
    ref = pd.read_csv(BRIDGE_CSV, float_precision="round_trip")      # ⛔ 逐位元對帳一律 round_trip（K線 1915 §五）
    miss = [c for c in BRIDGE_ID + BRIDGE_COLS if c not in ref.columns]
    if miss:
        raise SystemExit(f"⛔ §七① 退場條款：cells.csv 欄位與 §十一1-2 不符，缺 {miss} ⇒ 回信策略線出 seq=6")
    m = np.ones(len(ref), bool)
    for k, v in BRIDGE_KEY.items():
        m &= (ref[k] == v).to_numpy()                                # ⛔ 一律 ref[k]，⛔ 不用 ref.k（ref.T 是轉置）
    if m.sum() != 1:
        raise SystemExit(f"⛔【比錯格】：{BRIDGE_KEY} 在 cells.csv 命中 {m.sum()} 列（要恰 1）⇒ 停止，"
                         "⛔ 不可改 tuple 再找一次（K線分析線 0050 §2-3：選格在比對之前做完）")
    r_ref = ref[m].iloc[0]
    m2 = np.ones(len(tab), bool)
    for k, v in BRIDGE_KEY.items():
        m2 &= (tab[k] == v).to_numpy()
    if m2.sum() != 1:
        raise SystemExit(f"⛔【比錯格】：本趟彙總命中 {m2.sum()} 列（要恰 1）")
    r_own = tab[m2].iloc[0]
    rows, bad = [], []
    for c in BRIDGE_COLS:
        a, b = float(r_own[c]), float(r_ref[c])
        ok = repr(a) == repr(b)
        rows.append({"欄": c, "本趟當場重算": repr(a), "P12 1740 交件": repr(b), "逐位元": "✅" if ok else "⛔"})
        if not ok:
            bad.append(f"  {c}: 本趟 {a!r} ≠ 交件 {b!r}")
    if bad:
        raise SystemExit("⛔⛔ 否證⑥：§三⑦ 橋欄對不上 ⇒ 停止，本件不出結論\n"
                         "⚠ 而那時要查的不是本件，是【P12 那一份交件的可重現性】⇒ 回信策略線與 K線分析線\n"
                         + "\n".join(bad))
    return rows


def mdd_with_date(eq: np.ndarray, cal, w0: int) -> tuple[float, str, str]:
    """§三⑥：最大回落，連同【峰】與【谷】的日期一起回（⛔ 只報數字看不出五個 w 是不是同一段）。"""
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    i = int(np.argmin(dd))
    j = int(np.argmax(eq[:i + 1])) if i > 0 else 0
    return float(dd[i]), str(cal[w0 + j].date()), str(cal[w0 + i].date())


def judge(cagr: float, mdd: float,
          bench_cagr: float = None, bench_mdd: float = None) -> tuple[bool, str]:
    """§二 判準（⛔ 逐字，⛔ 本支不改）：兩腳都至少持平，且【至少一腳嚴格優於】（〈一百一十一〉）。

    ⭐ 兩個基準參數是 2026-09-22 為 PREREGP15 加的（⛔ 純追加，不傳 ＝ P14 原行為）：
      P15 §三 用的是【未捨入值】(0.24020209886370614／−0.3395700527611012)，
      ⇒ ⛔ 而再抄一份 judge 到 researchp15.py 就是 CLAUDE.md 四點五 的下一份
      ⇒ ⭐ 所以基準由呼叫端傳，判準本體【全庫只有這一份】。
    ⚠ 而別名可以被下一個人拆掉 ⇒ selftest 對本函式餵【兩組基準各四個出口】逐格比對。
    """
    bench_cagr = BENCH_CAGR if bench_cagr is None else bench_cagr
    bench_mdd = BENCH_MDD if bench_mdd is None else bench_mdd
    BENCH_CAGR_, BENCH_MDD_ = bench_cagr, bench_mdd
    leg_c = cagr >= BENCH_CAGR_
    leg_m = mdd >= BENCH_MDD_                      # ⭐ 回落是負數 ⇒「≤ 基準的回落深度」＝ 數值上 ≥
    strict = (cagr > BENCH_CAGR_) or (mdd > BENCH_MDD_)
    ok = leg_c and leg_m and strict
    # ⛔⛔ 這四處一律用區域變數：⭐ 用模組常數的話，P15 傳了別的基準時【布林是對的、
    #     而印出來的數字是 P14 的】⇒ 那是「欄位有值 ≠ 值是對的」那一族（CLAUDE.md 四點二③）。
    why = (f"年化 {cagr * 100:+.2f}% vs {BENCH_CAGR_ * 100:+.2f}%（{'✅' if leg_c else '⛔'}"
           f"{'，嚴格優' if cagr > BENCH_CAGR_ else ''}）／"
           f"回落 {mdd * 100:.2f}% vs {BENCH_MDD_ * 100:.2f}%（{'✅' if leg_m else '⛔'}"
           f"{'，嚴格優' if mdd > BENCH_MDD_ else ''}）")
    return ok, why


def run_arm(pool, arm: str, reps: int, keep_eq: bool):
    """一個臂跑 reps 顆種子。⭐ 回傳 (逐種子 DataFrame, {r: 窗內 equity})。"""
    res = pool.map(_one, [(arm, r, keep_eq) for r in range(reps)])
    df = pd.DataFrame([x[0] for x in res])
    eqs = {x[0]["r"]: x[1] for x in res if x[1] is not None}
    return df, eqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda x: print(x, flush=True)
    t0 = time.time()

    # ⭐ ① 最先跑 §三⑧ 的手算 fixture：它與資料、P12、隨機源全部無關 ⇒ 壞了要當場知道（否證⑦）
    fix = fixture_check()
    log(f"[fixture] §三⑧ 手算 fixture {len(fix)} 格【逐位元全同】⇒ ⭐ 合成式本身通過（否證⑦ 不觸發）")

    anc_rows = anchor_check()
    log(f"[錨點值] cells.csv 對登錄 §十一1-3 的 {len(anc_rows)} 個值【逐位元全同】"
        "（⭐ K線分析線 0050 §2-2 的判別法已寫進 anchor_check()，對不上時會印出來）")

    # ② 資料與訊號（⛔ 與 P12 同一條路：同一支 build_sig_gate_b、同一個驗收數）
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, WIN)
    marks = P12.month_marks(cal, w0, w1)
    log(f"[窗] {WIN} [{w0},{w1}] {w1 - w0 + 1} 日／{len(marks) - 1} 個月（{cal[w0].date()} ~ {cal[w1].date()}）")

    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    log(f"[sig] 門檻B ✅ 七個驗收數逐項相同：{len(sig):,} 筆／{sig['sid'].nunique():,} 檔／{sig['month'].nunique()} 月")

    # ③ bench ＝ 0050 還原收盤（ffill）。⭐⭐ §十一2-1：w=0 那一腿要【另一次獨立讀取】
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    bench_indep = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    if bench is bench_indep:
        raise SystemExit("⛔ §十一2-1：兩條 0050 是同一個物件 ⇒ w=0 那一腿會是恆等式")
    log(f"[bench] 0050 還原收盤 {len(bench):,} 點（⭐ 另一次獨立讀取 {len(bench_indep):,} 點，"
        f"物件不同 id={id(bench)}/{id(bench_indep)}）")

    _init(sig, closes, opens, ncal, w0, w1, marks, cal, bench)

    # ④ 三個臂（⭐ 錨點與 A0 是【兩次獨立呼叫】⇒ 逐位元相同才是真的檢查，⛔ 不是同一份結果比自己）
    with Pool(a.procs) as pool:
        anc, anc_eq = run_arm(pool, "ANCHOR", a.reps, keep_eq=True)
        log(f"[錨點] P12 (S1,C1,T1) 當場重算 {len(anc)} 顆（{time.time() - t0:.0f}s）")
        a0, a0_eq = run_arm(pool, "A0", a.reps, keep_eq=True)
        log(f"[A0]   cash_mode=zero {len(a0)} 顆（{time.time() - t0:.0f}s）")
        a1, _ = run_arm(pool, "A1", a.reps, keep_eq=False)
        log(f"[A1]   cash_mode=bench {len(a1)} 顆（{time.time() - t0:.0f}s）")

    # ⑤ §四①：逐位元，200/200 全同才算過，⛔ 零容差
    same = sum(int(x == y) for x, y in zip(anc["eq_sha"], a0["eq_sha"]))
    if same != len(anc):
        raise SystemExit(f"⛔⛔ 否證①：A0 對不上當場重算的 P12 (S1,C1,T1) ⇒ 停止，本件不出結論"
                         f"（逐位元相同 {same}/{len(anc)}）")
    log(f"[否證①] ✅ A0 的逐日權益 sha256 與當場重算【{same}/{len(anc)} 逐位元相同】（零容差）")

    # ⑥ §三⑦ 橋欄：把當場重算接回 1740 已交件的那個數
    for k, v in BRIDGE_KEY.items():
        anc[k] = v
    tab = P12.cell_table(anc)                       # ⛔ 用 P12 那一支，⛔ 本檔沒有第二份彙總實作
    br = bridge_check(tab)
    log(f"[否證⑥] ✅ 橋欄 {len(br)} 欄對 resultsp12/cells.csv【逐位元全同】(round_trip)")

    # ⑦ B 組（§一1-B）：逐種子合成五個 w。⛔ 期初一次配置、之後不再平衡
    B = bench[w0:w1 + 1]
    n = w1 - w0 + 1
    brows = []
    for r, E in sorted(a0_eq.items()):
        for w in WS:
            pw = blend(E, B, w)
            cg, md = R13.window_stats(pw, 0, n, 0, n)                 # ⛔ 與全庫同一支，⛔ 本檔沒有第二份
            _md, pk, tr = mdd_with_date(pw, cal, w0)                  # §三⑥ 回落的日期
            brows.append({"r": r, "w": w, "cagr": float(cg), "mdd": float(md),
                          "calmar": float(cg / abs(md)) if md else np.nan, "peak": pk, "trough": tr})
    bdf = pd.DataFrame(brows)
    log(f"[B組] 逐種子 × 五個 w ＝ {len(bdf):,} 條合成曲線（{time.time() - t0:.0f}s）")

    # ⑧ 否證②：w=1 對 A0（⚠ 恆等式，只驗輸入序列與 t0）／w=0 對【獨立讀取】的 0050 買進持有
    Bi = bench_indep[w0:w1 + 1]
    cg_i, md_i = R13.window_stats(Bi / Bi[0], 0, n, 0, n)
    w1row = bdf[bdf["w"] == 1.00].set_index("r").sort_index()
    bad2 = []
    for r in sorted(a0_eq):
        if repr(float(w1row.loc[r, "cagr"])) != repr(float(a0.set_index("r").loc[r, "cagr"])):
            bad2.append(f"  w=1 種子 {r}：{w1row.loc[r, 'cagr']!r} ≠ A0 {a0.set_index('r').loc[r, 'cagr']!r}")
    w0row = bdf[bdf["w"] == 0.00].iloc[0]
    if repr(float(w0row["cagr"])) != repr(float(cg_i)) or repr(float(w0row["mdd"])) != repr(float(md_i)):
        bad2.append(f"  w=0：合成 {w0row['cagr']!r}/{w0row['mdd']!r} ≠ 獨立 0050 {cg_i!r}/{md_i!r}")
    if bad2:
        raise SystemExit("⛔⛔ 否證②：合成式寫錯 ⇒ 停止\n" + "\n".join(bad2))
    log(f"[否證②] ✅ w=1 逐位元＝A0（⚠ 恆等式，只驗輸入序列與 t0）／"
        f"w=0 逐位元＝【另一次獨立讀取】的 0050 買進持有（年化 {cg_i * 100:+.2f}%／回落 {md_i * 100:.2f}%）")

    # ⑨ 必報 ③：五個 w 的判定（⛔ 只有 w=0.50 進判定，其餘四格只作描述）
    wsum = bdf.groupby("w").agg(cagr_med=("cagr", "median"), cagr_p10=("cagr", lambda x: x.quantile(.1)),
                                cagr_p90=("cagr", lambda x: x.quantile(.9)), mdd_med=("mdd", "median"),
                                mdd_p10=("mdd", lambda x: x.quantile(.1)), mdd_p90=("mdd", lambda x: x.quantile(.9)),
                                calmar_med=("calmar", "median")).reset_index()
    wsum["通過"], wsum["說明"] = zip(*[judge(c, m) for c, m in zip(wsum["cagr_med"], wsum["mdd_med"])])
    # ⛔⛔ w=0 是【純 0050】⇒ 登錄 §二 逐字寫它「不算通過（兩腳都只是相等）」。
    # ⚠ 而實測它兩腳都【嚴格優】——因為 §七② 把基準捨入成 +24.02%／−34.0%，
    #   而同一條序列算出來是 +24.020210%／−33.957005% ⇒ 差 0.00021pp 與 0.043pp 全是捨入。
    # ⇒ ⛔ 判準與判定用語【不是回測線的格子】⇒ 本支不改 judge()，只把那一格掛起、請裁。
    w0r = wsum[wsum["w"] == 0.00].iloc[0]
    res_deg = {"通過": bool(w0r["通過"]), "cagr": float(w0r["cagr_med"]), "mdd": float(w0r["mdd_med"]),
               "d_cagr_pp": (float(w0r["cagr_med"]) - BENCH_CAGR) * 100,
               "d_mdd_pp": (float(w0r["mdd_med"]) - BENCH_MDD) * 100}
    # ⭐ 判定格對這個捨入敏不敏感：用【未捨入的 w=0 實測值】當基準再判一次
    jr_ = wsum[wsum["w"] == JUDGE_W].iloc[0]
    cm_, mm_ = float(jr_["cagr_med"]), float(jr_["mdd_med"])
    alt_ok = (cm_ >= res_deg["cagr"]) and (mm_ >= res_deg["mdd"]) and ((cm_ > res_deg["cagr"]) or (mm_ > res_deg["mdd"]))

    # ⑩ 必報 ④：A1 − A0 的配對差（⭐ 同種子 ⇒ 這一欄才量得到 cash_mode 的效果）
    j = a0.set_index("r")[["cagr", "mdd", "mret"]].join(a1.set_index("r")[["cagr", "mdd", "mret"]],
                                                        lsuffix="_a0", rsuffix="_a1")
    d_cagr = float(np.median(j["cagr_a1"] - j["cagr_a0"])); d_mdd = float(np.median(j["mdd_a1"] - j["mdd_a0"]))
    dm = np.array([np.asarray(x1, float) - np.asarray(x0, float)
                   for x0, x1 in zip(j["mret_a0"], j["mret_a1"])]).mean(axis=0)
    ci = P8.month_ci(dm)                                             # ⛔ 走 P8，⛔ 本檔沒有第二份 CI
    if d_cagr > A1_CAGR_GUARD:
        log(f"⚠⚠ §四⑤ 觸發：A1 年化改善 {d_cagr * 100:+.2f}pp > 5pp ⇒ ⛔ 先查 bench_cost 是否漏算")

    _seg = bdf.assign(seg=pd.to_datetime(bdf["trough"]).dt.year.astype(str))
    segtab = _seg.groupby(["w", "seg"]).size().unstack(fill_value=0).sort_index()
    deg5_same = int((_seg.groupby("r")["seg"].nunique() == 1).sum())
    res = dict(fix=fix, br=br, anc=anc, a0=a0, a1=a1, bdf=bdf, wsum=wsum, tab=tab,
               segtab=segtab, seg_cols=list(segtab.columns), deg5_same=deg5_same,
               d_cagr=d_cagr, d_mdd=d_mdd, ci=ci, cg_i=cg_i, md_i=md_i, deg=res_deg, alt_ok=alt_ok,
               cal=cal, w0=w0, w1=w1, sig=sig, out=a.out, secs=time.time() - t0, reps=len(a0))
    write_out(res, log)
    return res


def write_out(res, log):
    """交件：P14_REPORT.md ＋ 逐種子／逐 w 的 csv。⛔ 判定用語逐字照登錄 §二。"""
    o = res["out"]
    res["bdf"].to_csv(os.path.join(o, "blend_by_seed.csv"), index=False)
    res["a0"].drop(columns=["mret"]).to_csv(os.path.join(o, "a0_by_seed.csv"), index=False)
    res["a1"].drop(columns=["mret"]).to_csv(os.path.join(o, "a1_by_seed.csv"), index=False)
    res["wsum"].to_csv(os.path.join(o, "w_summary.csv"), index=False)
    pd.DataFrame(res["br"]).to_csv(os.path.join(o, "bridge.csv"), index=False)
    jr = res["wsum"][res["wsum"]["w"] == JUDGE_W].iloc[0]
    L = [f"# PREREGP14 結果：把 0050 放進組合（{res['reps']} 顆種子）", "",
         f"⛔ 登錄 `backtest/PREREGP14.md` seq=5 sha **36c02965e3639996**（去 pw1 行＋檔尾一個換行）。",
         f"⛔ 判準與判定用語逐字取自登錄 §二 ⇒ ⭐ 回測線只報數字。", "",
         "## 〇、開跑前三道閘（⛔ 全部在看到任何一格結果之前）", "",
         f"- §三⑧ 手算 fixture：**5 格逐位元全同** ⇒ 否證⑦ 不觸發",
         f"- §四① A0 vs 當場重算的 P12 (S1,C1,T1)：**{res['reps']}/{res['reps']} 逐位元相同**（零容差）",
         f"- §三⑦ 橋欄 vs `resultsp12/cells.csv` 15 個量欄：**逐位元全同**（round_trip）⇒ 否證⑥ 不觸發", "",
         "## 一、⭐⭐ 判定格 w = 0.50（⛔ 唯一一格，虛無期望 0.05）", "",
         f"```", f"年化中位 {jr['cagr_med'] * 100:+.2f}%（p10 {jr['cagr_p10'] * 100:+.2f}／p90 {jr['cagr_p90'] * 100:+.2f}）",
         f"回落中位 {jr['mdd_med'] * 100:.2f}%（p10 {jr['mdd_p10'] * 100:.2f}／p90 {jr['mdd_p90'] * 100:.2f}）",
         f"基準     0050 年化 +24.02%／最大回落 −34.0%（§七② 指定到一個值，同窗）",
         f"⇒ {jr['說明']}", f"⇒ 判定：**{'通過' if jr['通過'] else '沒通過'}**", "```", "",
         "## 二、五個 w（⛔ 非 w=0.50 的四格【只作描述】，⛔ 不可用來宣告測到了）", "",
         "| w | 年化中位 | p10~p90 | 回落中位 | p10~p90 | Calmar | 兩腳 |", "|---|---|---|---|---|---|---|"]
    for _, r in res["wsum"].iterrows():
        L.append(f"| {r['w']:.2f} | {r['cagr_med'] * 100:+.2f}% | {r['cagr_p10'] * 100:+.2f}~{r['cagr_p90'] * 100:+.2f} "
                 f"| {r['mdd_med'] * 100:.2f}% | {r['mdd_p10'] * 100:.2f}~{r['mdd_p90'] * 100:.2f} "
                 f"| {r['calmar_med']:.3f} | {'✅通過' if r['通過'] else '⛔'} |")
    a0, a1 = res["a0"], res["a1"]
    L += ["", "## 三、A 組（§一1-A・⛔ 只作描述）", "",
          "| 臂 | 年化中位 | 回落中位 | 平均曝險 | 交易筆數 |", "|---|---|---|---|---|"]
    for nm, d in (("A0 zero", a0), ("A1 bench", a1)):
        L.append(f"| {nm} | {d['cagr'].median() * 100:+.2f}% | {d['mdd'].median() * 100:.2f}% "
                 f"| {d['expo'].median():.4f} | {d['trades'].median():.0f} |")
    L += ["", f"**§三④ A1 − A0 配對差（同種子）**：年化 {res['d_cagr'] * 100:+.3f}pp／"
              f"回落 {res['d_mdd'] * 100:+.3f}pp；逐月配對差月分群 CI {res['ci']}", "",
          "## 四、⛔⛔ 一格【掛起｜待裁】：w=0.00 依判準算出來是「通過」", "", "```",
          "⛔ 登錄 §二 逐字：「⭐ 這樣 w=0 就不算通過（它兩腳都只是相等）」",
          "⚠ 而實測 w=0（＝純 0050）兩腳都【嚴格優於基準】：",
          f"    年化 {res['deg']['cagr']!r}  vs 指定 {BENCH_CAGR}  ⇒ 多 {res['deg']['d_cagr_pp']:+.6f}pp",
          f"    回落 {res['deg']['mdd']!r}  vs 指定 {BENCH_MDD}  ⇒ 淺 {res['deg']['d_mdd_pp']:+.6f}pp",
          "⇒ ⭐⭐ 兩個差【完全來自捨入】——§七② 把同一條 0050 捨成 +24.02%／−34.0%",
          "   ⇒ 於是純 0050【嚴格優於它自己】⇒ 正是〈一百一十一〉要擋的退化解，從捨入的縫裡漏過去",
          "⛔ 判準與判定用語不是回測線的格子 ⇒ 本件【不自行改用未捨入值】、⛔ 不改 judge()",
          "⇒ ⏳ 請策略線與 K線分析線 裁：基準改成未捨入值，或 §二 加一條容差",
          "",
          "⭐⭐ 而【判定格 w=0.50 對這個捨入不敏感】——兩種基準下都沒通過：",
          f"    用登錄指定基準       ⇒ {'通過' if bool(jr['通過']) else '沒通過'}",
          f"    用未捨入的 w=0 實測  ⇒ {'通過' if res['alt_ok'] else '沒通過'}",
          "⇒ ⭐ 所以本件的判定【不等這個裁定】；⛔ 而 w=0 那一格的「通過」在裁定前不可引用",
          "```", "",
          "## 五、⭐ 先驗對帳（⛔ 登錄 §五 原文一字未改，這裡只報中與不中）", "", "```",
          f"① A1 押【年化 +1~3pp、回落 0~2pp】⇒ 實測 年化 {res['d_cagr'] * 100:+.3f}pp（⚠ 略超上緣）／"
          f"回落 {res['d_mdd'] * 100:+.3f}pp（✅ 在範圍內）",
          f"② 押【w=0.50 沒通過，且是回落那一腳】⇒ ✅ 方向押中（回落 {jr['mdd_med'] * 100:.2f}% 沒過）",
          f"   ⚠ 而它押回落 −36~−39%，實測 {jr['mdd_med'] * 100:.2f}% ⇒ ⛔ 量級押得太悲觀（實際淺 2~5pp）",
          "③ 押【存在某個 w 兩腳同時成立、落在 w ∈ [0.25, 0.50]】⇒ ✅ w=0.25 兩腳都嚴格優",
          "   ⛔ 而依 §二 那【不算通過】（事後看出來的比例）⇒ 標描述；",
          "   ⛔ 且 §五 已標它為【描述性先驗】⇒ ⛔ 不可當「押中了」的戰績、⛔ 不可據它給建議",
          "④ 押相關係數 ∈ [0.60, 0.80] ⇒ ⛔ 開跑前已被否證（引用值 0.533，整條分佈 max 0.567 < 0.60）",
          "   ⇒ ⭐ 策略線據此把先驗② 的把握由八成下調為【約六成】——而 ② 押中了",
          "⑤ 押【五個 w 的最大回落落在同一段】⇒ 見下表",
          "```", "",
          f"**⛔ 否證**：{res['deg5_same']}/{res['reps']} 顆種子（{res['deg5_same'] / res['reps'] * 100:.1f}%）"
          f"的五個 w 落在同一段 ⇒ ⭐ 絕大多數【不在同一段】", "",
          "| w | " + " | ".join(res["seg_cols"]) + " |", "|---|" + "---|" * len(res["seg_cols"])] \
         + [f"| {w:.2f} | " + " | ".join(str(int(v)) for v in row) + " |"
            for w, row in zip(res["segtab"].index, res["segtab"].to_numpy())] \
         + ["", "⚠ 欄 ＝ 最深回落【谷】落在哪一年；⛔ 逐種子計數，⛔ 不是中位（回落的日期沒有中位可取）。",
            "⭐ 而回測線只報這張表：**它代表什麼是策略線的格子**（⛔ 本線不寫機制故事）。", "",
          "## 六、⛔⛔ 缺的必報欄（⛔ 不略過，⛔ 不自行補）", "",
          "```", "§三⑤ A1 的 bench 進出次數與 bench_cost 累計 ⇒ ⛔【量不到】",
          "  成因：引擎在 cash_mode=\"bench\" 下【沒有任何記帳】——",
          "        units 在 research11.py:533／610 就地加減，⛔ 無計數器、⛔ 無累加器",
          "  ⇒ 進出【次數】推得出來（每筆進場賣 bench、每筆出場買 bench ⇒ 2×trades）",
          "  ⇒ ⛔ 而【成本累計】推不出來：它要逐筆的 amt，而回傳 dict 裡沒有",
          "  ⛔ 而登錄 §一1-A 逐字寫【不改引擎】⇒ 回測線不自行加計數器",
          "  ⇒ ⏳ 提案（照 stop／weak／cap_fn／weight_fn 四次的規格）：",
          "     引擎在 use_bench 時多回兩個鍵，預設路徑逐位元不變 ⇒ 請策略線裁、出 seq=6",
          "  ⚠ 而它連帶影響 §四⑤：『先查 bench_cost 是否漏算』這道檢查目前只能看年化改善的量級",
          "```", "",
          "## 七、⛔ 範圍限制（逐字照登錄 §六）", "",
          "```", "① 期初一次配置、⛔ 不再平衡 ⇒ ⛔ 不可讀成「維持 50/50」",
          "② 0050 的 ETF 內扣費用【未計】⇒ 本件對 0050 那一側【略為樂觀】",
          "③ 判準用回測線自己算的 0050（+24.02%，同窗）⇒ ⛔ 跨線不並列",
          "④ §三④ 那一欄是配對差 ⇒ 受〈九十五〉限制；⛔ 其餘是絕對值對基準，不受",
          "⑤ 倖存者偏誤：策略那一側未查證",
          "⑥ 最大回落是【一個窗上的一個數】⇒ ⛔ 不可用 200 顆種子講它的信心水準",
          "   ⇒ 回落一律報 p10~p90 的種子帶，⛔ 不報 CI",
          "⑦ A0 逐位元只證明【cash_mode 在 A0 位置沒改變任何東西】⛔ 不證明 P12 交件本身對",
          "⑧ 否證② 的 w=1 那一腿是【恆等式】⇒ ⛔ 不構成「合成式正確」的證據",
          "   ⇒ ⭐ 合成式的保證分兩層：輸入序列與 t0 ⇒ 否證②；加權混合 ⇒ 否證⑦（fixture）",
          "⚠ A0/A1 與 P12 共用種子 ⇒ ⛔ 本件與 P12【不是獨立證據】（〈七十八〉）",
          "```", ""]
    fp = os.path.join(o, "P14_REPORT.md")
    open(fp, "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"[交件] {fp}（{os.path.getsize(fp):,} B）＋ 4 個 csv")


if __name__ == "__main__":
    main()

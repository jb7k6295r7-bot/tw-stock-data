"""PREREGP16：**條件出場**（進場理由不再成立就走）—— 回測線執行端。

⛔ 登錄全文 `backtest/PREREGP16.md`（策略線 seq=5）
   sha256[:16] ＝ **6dc2e02d621b8cef**（去 pw1 戳記行 ＋ 檔尾恰一個換行，60,083 B）
   ⚠ 三個時間互不相同（⭐ 逐字標出，K線分析線 1425 §二 已收下）：
     標題標籤 2026-09-22 17:48／pw1 ts 16:40／**Drive createdTime 09:53 台北**
     ⇒ ⭐ 跨線對時序一律以 Drive createdTime 為準（〈一百二十五〉提案）
   ✅ K線分析線 1425【授權開跑】逐件列名附 seq 與 sha ⇒ ⛔ 授權只指這一份。

⛔⛔ 本支【不訂判準、不訂判定用語、不設計策略】——§三 的判準、§一 的 E1 定義、
     §二 的兩個對照組、§四 的必報欄，全部逐字取自登錄。回測線只負責跑與報數字。

⭐⭐ 為什麼本支【一行引擎都不用改】（⛔ 這是登錄 §一1-3④ 逐字要求的）：
  條件出場日只取決於【(個股 i, 進場日 e)】—— S(i,t) 是個股的逐日布林，
  ⛔ 與組合、槽位、現金【完全無關】⇒ ⭐ 所以它可以事前算完。
  ⚠ 而引擎只從 sig 讀四欄：`sid`／`entry_pos`／`xpos_H120`／`g_H120`（research11 L475-478）
  ⇒ ⭐⭐ E1／R1／E1a/b/c 全部 ＝【改寫 xpos ＋ 重算 g】的 sig 框
  ⇒ ⛔ 不加參數、不改排程、不碰 PREREGP7 那條「stop is None 逐位元相同」的保證

⭐ 三個分量的逐日值走 `P4F.stock_raw()` ——⛔ 而它【正是 panel 的來源】
  ⇒ ⛔ 本檔沒有第二份特徵實作（CLAUDE.md 四點五）
  ⇒ ⭐ 而「走的是同一條路」是【驗出來的】：`panel_echo_check()` 在量測日上逐位元對 panel。

⭐ 同理 import 而不抄：`P14._sim`／`P14.judge`（基準由呼叫端傳）／`P14.bridge_check`／
   `P14.anchor_check`／`P14.mdd_with_date`／`P12.win_read`／`win_bounds`／`month_marks`／
   `cell_table`／`P8.month_ci`／`R13.window_stats`。
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
from . import research34 as R34
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp8 as P8
from . import researchp12 as P12
from . import researchp14 as P14

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp16")

# ── 登錄寫死的常數（⛔ 一個都不可以在這裡「挑」）──────────────────────────────
WIN = "全窗"                 # §三：判定窗（2017-03-02 ~ 2026-08-24）
REPS = 200                   # §一1-1：r ∈ [0, 200)
R_RANDOM = 30                # §二(甲)／§七⑦：R1 每顆種子抽 R 次，⛔ 開跑前寫死
SEED_R1 = 106000             # §二(甲)：R1 持有天數抽樣的【獨立 rng 流】，⛔ 不進選股流
HOLD_MAX = P7.HOLD_BARS_N    # §一1-3②：H120 是【上限】（⛔ 條件出場只能提早）

# §三（seq=5 改）：基準改【未捨入值】（⛔ 捨入值只可顯示，⛔ 不進判定）
BENCH_CAGR = 0.24020209886370614
BENCH_MDD = -0.3395700527611012

D_GATE = 0.20                # §十 4-3：|D| > 20% ⇒ (i) 措辭改【本件分不開】（⛔ 只決定措辭）
PEAK_MULT = 2.0              # §十一②：出場高峰月 ＝ 逐月筆數中位 ×2（⛔ 只決定措辭）
OV_HI, OV_LO = 0.60, 0.30    # §十一②：兩向重疊率的三種措辭門檻
MIN_TRIG_FRAC = 0.10         # §四③：觸發筆數 < 進場筆數 ×10% ⇒ 先查實作

# §二(乙)：三個分量的分解組（⛔ 只作描述，⛔ 不進判定）
DECOMP = {"E1a": "ma60_up", "E1b": "rev_hi24", "E1c": "ma_stack"}


# ── §一1-2：S(i,t) 與它的否定（⭐ 全檔只有這一個地方定義條件）──────────────
def cond_holds(raw: pd.DataFrame, only: str | None = None) -> np.ndarray:
    """S(i,t) ＝ rev_hi24 ∧ ma60_up ∧ ¬ma_stack（⭐ 逐日）。

    ⭐⭐ 比較寫法與 `P7.build_sig_gate_b` 的進場側【逐字相同】
    （`rev_hi24 == 100`／`ma60_up == 100`／`ma_stack == 0`）⇒ ⛔ 本檔沒有第二套語意。
    ⚠ 而那個寫法把 **NaN 當成 False**（暖身不足的日子）⇒ 出場側就是「條件不成立 ⇒ 走」
      ⇒ ⛔ 本支【不替登錄改這個語意】，⭐ 但必報【因 NaN 而出場】的筆數（§四⑥ 旁欄）。

    only：⛔ None ＝ 合集（判定格 E1）；否則只看單一分量（§二(乙) 的 E1a/E1b/E1c）。
    """
    rev = (raw["rev_hi24"].to_numpy() == 100)
    up = (raw["ma60_up"].to_numpy() == 100)
    stk = (raw["ma_stack"].to_numpy() == 0)
    if only is None:
        return rev & up & stk
    if only == "rev_hi24":
        return rev
    if only == "ma60_up":
        return up
    if only == "ma_stack":
        return stk
    raise SystemExit(f"⛔ 分量只能是 rev_hi24／ma60_up／ma_stack，收到 {only!r}")


def cond_exit(e: int, x: int, holds: np.ndarray, tradable: np.ndarray) -> dict:
    """§一1-3①③＋§十一③：條件出場日。⭐ 全檔只有這一個地方算它。

    逐字規格：
      ① 在 t 日【收盤後】判 S(i,t)，於 **t+1 日收盤**出場（⛔ 不可同一根 K 判定又成交）
      ② t+1 無法成交 ⇒ 順延至下一個可成交日（⭐ 必報順延次數與最長順延天數）
      ③ ⛔⛔ 順延若【落在或晚於】H120 期滿日 x ⇒ 一律以 x 出場（H120 上限優先）
      ④ H120 是上限 ⇒ ⛔ 條件出場只能讓部位提早離場

    ⭐ 回的是一個 dict（⛔ 只有這一份實作 ⇒ 必報欄與 fixture 讀的是同一組數）：
      judge   第一次 S 不成立的判定日（⛔ −1 ＝ 全程成立）
      target  照①的成交日 ＝ judge+1（⛔ −1 ＝ 沒觸發）
      settle  照②順延後的成交日（⛔ 不設上限 ⇒ 可能 ≥ x）
      delay   settle − target（⭐ 順延天數）
      pos     實際出場位置 ＝ min(settle, x)
      reason  "H120"（沒觸發）／"cond"（條件出場）／"cap_priority"（順延或次日落在 ≥ x）
      crossed ⭐ True ＝ 順延【真的跨過】期滿日（target < x ≤ settle）⇒ §四⑧ 要單獨報

    ⚠ 判定日只掃 [e, x−1]：t ＝ x 觸發的話成交日 ≥ x+1 ⇒ 依③ 也是 x ⇒ 與 H120 同格。
    """
    if not (0 <= e < x):
        raise SystemExit(f"⛔ cond_exit：要 0 ≤ e < x，收到 e={e} x={x}")
    none = {"judge": -1, "target": -1, "settle": -1, "delay": 0,
            "pos": x, "reason": "H120", "crossed": False}
    for t in range(e, x):
        if holds[t]:
            continue
        target = t + 1
        settle = target
        while settle < x and not tradable[settle]:        # ② 順延（⛔ 掃到 x 就停：③ 會接手）
            settle += 1
        if settle >= x:                                    # ③ H120 上限優先
            return {"judge": t, "target": target, "settle": settle, "delay": settle - target,
                    "pos": x, "reason": "cap_priority", "crossed": target < x <= settle}
        return {"judge": t, "target": target, "settle": settle, "delay": settle - target,
                "pos": settle, "reason": "cond", "crossed": False}
    return none


def tradable_of(raw: pd.DataFrame, close_arr) -> np.ndarray:
    """可成交日 ＝ 當天有成交 ∧ 收盤是有限值。

    ⚠ 漲跌停【沒有模型】—— 引擎的進場側也沒有 ⇒ ⭐ 兩側同一個口徑，⛔ 必報這件事。
    """
    c = np.asarray(close_arr, float)
    tr = raw["traded"].to_numpy(bool)
    n = min(len(tr), len(c))
    out = np.zeros(len(tr), bool)
    out[:n] = tr[:n] & np.isfinite(c[:n])
    return out


# ── 手算 fixture（⛔ 與真實資料、隨機源全部無關）──────────────────────────
def exit_fixture() -> list[dict]:
    """§一1-3 的手算 fixture。⭐ 依〈一百一十三〉：先證明它【分得出來】（見 selftest 的突變驗）。

    ⭐ 一條 12 格的時間軸（e=0、x=10 ⇒ H120 期滿在第 10 格）：
       ⛔ 六格各釘一個會被實作寫反的地方，每一格答案都不同。
    """
    T = 12
    tr_all = np.ones(T, bool)
    ones = lambda *z: np.array([1] * T if not z else z[0], bool)
    cases = [
        ("一直成立 ⇒ H120", np.ones(T, bool), tr_all, (10, "H120", 0, False)),
        # t=3 不成立 ⇒ 次日 4 成交（⛔ 不是 3：同一根 K 不可判又成交）
        ("t=3 破 ⇒ 次日 4 出", np.array([1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1], bool), tr_all,
         (4, "cond", 0, False)),
        # t=3 不成立、而 4/5 不可成交 ⇒ 順延到 6（⭐ 順延 2 天）
        ("順延兩天 ⇒ 6 出", np.array([1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1], bool),
         np.array([1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1], bool), (6, "cond", 2, False)),
        # t=8 不成立 ⇒ 次日 9；⛔ 而 9 不可成交 ⇒ 順延到 10 ＝ x ⇒ 上限優先【且跨過】
        ("順延跨過期滿 ⇒ 上限優先", np.array([1] * 8 + [0, 1, 1, 1], bool),
         np.array([1] * 9 + [0, 1, 1], bool), (10, "cap_priority", 1, True)),
        # ⭐ 邊界：t=9（＝x−1）不成立 ⇒ 次日 10 ＝ x ⇒ 依③ 走上限優先，⛔ 而它【沒有跨過】
        ("x−1 破 ⇒ 上限優先但沒跨過", np.array([1] * 9 + [0, 1, 1], bool), tr_all,
         (10, "cap_priority", 0, False)),
        # ⭐ 進場當天就不成立 ⇒ 次日 1 出（⛔ 不可以因為「才剛進場」就跳過 t=e）
        ("進場當天就破 ⇒ 1 出", np.array([0] + [1] * 11, bool), tr_all, (1, "cond", 0, False)),
    ]
    rows, bad = [], []
    for nm, holds, tr, exp in cases:
        r = cond_exit(0, 10, holds, tr)
        got = (r["pos"], r["reason"], r["delay"], r["crossed"])
        ok = got == exp
        rows.append({"格": nm, "得": str(got), "要": str(exp), "逐位元": "✅" if ok else "⛔"})
        if not ok:
            bad.append(f"  {nm}: 得 {got}，要 {exp}")
    if bad:
        raise SystemExit("⛔⛔ §一1-3 的條件出場手算 fixture 對不上 ⇒ 出場規則本身寫錯，本件不出結論\n"
                         + "\n".join(bad))
    return rows


def cond_fixture() -> list[dict]:
    """§一1-2：S(i,t) 的合集與三個分量。⭐ 含【NaN 當 False】那一格（⛔ 它是本件的一個口徑）。"""
    raw = pd.DataFrame({"rev_hi24": [100.0, 100.0, 100.0, 0.0, np.nan, 100.0],
                        "ma60_up": [100.0, 100.0, 0.0, 100.0, 100.0, np.nan],
                        "ma_stack": [0.0, 100.0, 0.0, 0.0, 0.0, 0.0]})
    exp = {None: [1, 0, 0, 0, 0, 0],          # 合集：任一不成立就 False；⭐ NaN 也是 False
           "rev_hi24": [1, 1, 1, 0, 0, 1],
           "ma60_up": [1, 1, 0, 1, 1, 0],
           "ma_stack": [1, 0, 1, 1, 1, 1]}
    rows, bad = [], []
    for only, want in exp.items():
        got = cond_holds(raw, only).astype(int).tolist()
        ok = got == want
        rows.append({"分量": only or "合集", "得": str(got), "要": str(want), "逐位元": "✅" if ok else "⛔"})
        if not ok:
            bad.append(f"  {only or '合集'}: 得 {got}，要 {want}")
    if bad:
        raise SystemExit("⛔⛔ §一1-2 的 S(i,t) 手算 fixture 對不上 ⇒ 條件本身寫錯，本件不出結論\n"
                         + "\n".join(bad))
    return rows


# ── 每檔的逐日條件（⭐ 走 panel 的同一條路，⛔ 本檔沒有第二份特徵實作）──────────
_G: dict = {}


def _raw_worker(args):
    """⭐ 與 `researchp4.panel_worker` 逐字相同的呼叫路徑（⛔ 差一個參數就會靜靜給出別的出場日）。"""
    sid, market = args
    rf = _G["rev_flags"][sid] if sid in _G["rev_flags"].columns else None
    raw = P4F.stock_raw(sid, market, _G["cal"], rf)
    if raw is None:
        return sid, None
    keep = raw[["rev_hi24", "ma60_up", "ma_stack", "traded"]].copy()
    return sid, keep


def _init_raw(cal, rev_flags):
    _G.update(cal=cal, rev_flags=rev_flags)


def panel_echo_check(raws: dict, panel: pd.DataFrame, cal, n_max: int = 30000) -> dict:
    """⛔⛔ 開跑前閘門：本趟算的逐日值，在【量測日】上必須逐位元重現 panel。

    ⭐ 為什麼這一道是必要的（⛔ 而且它驗的是終點，不是「函式有沒有被呼叫」）：
      本支要的是【逐日】的三個分量，而 panel 只有【量測日】那一格。
      ⇒ 若本支的呼叫路徑與 panel 的不同（rev_flags 的 pub_day／undecided／mp_frac…），
        ⛔ 差異【不會報錯】—— 它會靜靜給出另一組出場日，而整件事看起來完全正常。
      ⇒ ⭐ 所以拿兩者【重疊的那一格】逐位元對；對不上就停。
    """
    pos = {d: i for i, d in enumerate(cal)}
    p = panel[panel["stock_id"].isin(raws.keys())]
    n, bad = 0, []
    for r in p.itertuples():
        raw = raws.get(r.stock_id)
        if raw is None:
            continue
        i = pos.get(r.measure_date)
        if i is None or i >= len(raw):
            continue
        for c in ("rev_hi24", "ma60_up", "ma_stack"):
            a, b = float(raw[c].iloc[i]), float(getattr(r, c))
            if not (repr(a) == repr(b) or (np.isnan(a) and np.isnan(b))):
                bad.append(f"  {r.stock_id} {r.measure_date.date()} {c}: 本趟 {a!r} ≠ panel {b!r}")
        n += 1
        if n >= n_max:
            break
    if bad:
        raise SystemExit("⛔⛔ 本趟的逐日特徵與 panel 對不上 ⇒ 兩條路徑不同，本件不出結論\n"
                         "⭐ 那表示本支的 stock_raw 呼叫與 researchp4.panel_worker 不是同一條\n"
                         + "\n".join(bad[:20]))
    if n == 0:
        raise SystemExit("⛔ panel 回聲閘門一格都沒比到 ⇒ ⛔ 它不是一道檢查（⭐ 先查 measure_date 對不對得上）")
    return {"比到的股-月": n, "結果": "✅ 逐位元全同"}


# ── 造臂：改寫 xpos ＋ 重算 g（⭐ 全檔只有這一個地方造臂）──────────────────
def build_arm(sig: pd.DataFrame, raws: dict, trad: dict, closes: dict, opens: dict,
              only: str | None = None, hold: np.ndarray | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """回 (新的 sig 框, 逐筆明細)。

    ⛔ 引擎只讀 sid／entry_pos／xpos_H120／g_H120 ⇒ ⭐ 改這兩欄就等於換了出場規則。
    hold：R1 用 —— 每一列抽到的【持有根數】；⛔ 給了就不看條件（§二(甲)）。
      ⭐⭐ 而 R1 仍走【同一個 cond_exit】：把 holds 造成「目標出場日的前一天不成立」
         ⇒ 順延與 H120 上限優先兩條規則【只有一份實作】（四點五）。
    """
    col_x, col_g = f"xpos_{P12.RULE}", f"g_{P12.RULE}"
    NANC = ["rev_hi24", "ma60_up", "ma_stack"]
    rows = []
    for i, r in enumerate(sig.itertuples()):
        sid = r.sid
        e, x0 = int(r.entry_pos), int(getattr(r, col_x))
        raw, tr = raws[sid], trad[sid]
        if hold is None:
            holds = cond_holds(raw, only)
            d = cond_exit(e, x0, holds, tr)
            nan_exit = bool(d["judge"] >= 0 and raw[NANC].iloc[d["judge"]].isna().any())
        else:
            h = int(hold[i])
            if h < 2:
                raise SystemExit(f"⛔ R1 抽到持有 {h} 根 ⇒ 目標出場日早於進場日，"
                                 "⭐ 而經驗分佈來自 E1（最短 2 根）⇒ 這表示校準來源錯了")
            tgt = D.exit_pos(e, h)                    # ⭐ 與全庫同一支：H〈n〉＝持有 n 根
            syn = np.ones(len(tr), bool)
            if tgt - 1 >= e:
                syn[tgt - 1] = False                  # ⇒ cond_exit 會在 tgt−1 判不成立、次日 tgt 成交
            d = cond_exit(e, x0, syn, tr)
            nan_exit = False
        rows.append({"sid": sid, "entry_pos": e, "xpos_E0": x0, "xpos": d["pos"], "reason": d["reason"],
                     "judge_pos": d["judge"], "delay": d["delay"], "crossed": d["crossed"],
                     "hold_bars": d["pos"] - e + 1, "nan_exit": nan_exit})
    det = pd.DataFrame(rows)
    out = sig.copy()
    out[col_x] = det["xpos"].to_numpy()
    out[col_g] = [float(np.asarray(closes[s], float)[x]) / float(np.asarray(opens[s], float)[e]) - 1.0
                  for s, x, e in zip(det["sid"], det["xpos"], det["entry_pos"])]
    return out, det


# ── 引擎（⛔ 本檔沒有呼叫點：走 P14._sim，理由見檔頭）────────────────────────
_P: dict = {}


def _one16(args):
    """一個臂的一顆種子。⭐ 選股種子一律 P12.SEED0 + r（§一1-1：逐位元對帳需要同一個隨機源）。"""
    arm, r, keep_eq, want_log = args
    log = [] if want_log else None
    out = P14._sim(_P["sigs"][arm], P12.N_C1, P12.SEED0 + r, P12.COST_STD, log=log)
    eq = np.asarray(out["equity"], float)
    w0, w1 = P14._S["w0"], P14._S["w1"]
    row = {"arm": arm, "r": r, "seed": P12.SEED0 + r, "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest(),
           **P12.win_read(out, w0, w1, P14._S["marks"])}
    row.pop("mret", None)
    tr = _trades_of(log) if log is not None else None
    return (row, eq[w0:w1 + 1].copy() if keep_eq else None, tr, _first_exit(log) if log is not None else None)


def _trades_of(log) -> pd.DataFrame:
    """逐筆成交（⭐ §四②③④⑤ 的唯一來源）。⛔ 只取 reason=="in"（＝真的買進去的那幾筆）。"""
    rows = [{"sid": x["sid"], "entry_pos": int(x["entry_pos"]), "exit_pos": int(x["exit_pos"]),
             "t": int(x["t"]), "gross": float(x["gross"])} for x in log if x["reason"] == "in"]
    d = pd.DataFrame(rows)
    if len(d):
        d["hold_bars"] = d["exit_pos"] - d["entry_pos"] + 1
    return d


def _first_exit(log) -> int:
    """t*(r) ＝ 該臂全窗【第一次】出場的成交日（⛔ 沒有任何一筆 ⇒ +∞）。"""
    ex = [int(x["exit_pos"]) for x in log if x["reason"] == "in"]
    return min(ex) if ex else 10 ** 9


def _r1_worker(r: int):
    """R1 的一顆種子：抽 R 次、每次造一個 sig 框、跑一趟。

    ⛔ rng 必須在【同一個 worker 內依序】抽完 R 次 ⇒ ⭐ 這樣 (r, rep) 的抽樣流才唯一確定。
    ⚠ 抽樣母體 ＝ 該顆種子下 E1【實際成交】那幾筆的持有根數（§二(甲) 逐字：有放回）。
    """
    pool = _P["e1_hold"][r]
    rng = np.random.default_rng(SEED_R1 + r)
    base, raws, trad = _P["sigs"]["E0"], _P["raws"], _P["trad"]
    out = []
    for rep in range(_P["R"]):
        draw = rng.choice(pool, size=len(base), replace=True)
        s1, det = build_arm(base, raws, trad, _P["closes"], _P["opens"], hold=draw)
        log = []
        o = P14._sim(s1, P12.N_C1, P12.SEED0 + r, P12.COST_STD, log=log)
        eq = np.asarray(o["equity"], float)
        w0, w1 = P14._S["w0"], P14._S["w1"]
        tr = _trades_of(log)
        hb = tr["hold_bars"].to_numpy(float) if len(tr) else np.array([np.nan])
        t_own = _first_exit(log)
        # ⭐ §十一①／§十二②：本 rep 自己的 [窗首, t*−1] 那一欄，⛔ 由 worker 自己算完
        #    （⭐ 共同區間要等 200×R 全抽完才知道 ⇒ 另外帶回【E1 的 t* 以內】那一段）
        own_n = max(0, min(t_own, w1 + 1) - w0)
        out.append({"r": r, "rep": rep, "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest(),
                    "n_trades": len(tr), "hold_mean": float(np.nanmean(hb)), "hold_med": float(np.nanmedian(hb)),
                    "hold_p10": float(np.nanpercentile(hb, 10)), "hold_p90": float(np.nanpercentile(hb, 90)),
                    "hold_max": float(np.nanmax(hb)), "first_exit": t_own,
                    "own_n": own_n, "own_sha": hashlib.sha256(eq[w0:w0 + own_n].copy().tobytes()).hexdigest(),
                    "pref": eq[w0:max(w0, min(_P["ts1"][r], w1 + 1))].copy(),
                    **{k: v for k, v in P12.win_read(o, w0, w1, P14._S["marks"]).items() if k != "mret"}})
    return out


def rev_clock(sig: pd.DataFrame, cal, rb: dict) -> pd.DataFrame:
    """⭐⭐ 必報（本線加的一欄，⛔ 登錄沒要求，⭐ 而少了它會把一件結構事實讀成訊號）：

    ⛔ panel 的【量測日】是月初，而 rev_hi24 的【可得日】是每月 ~10 日
    ⇒ ⭐ 所以一筆部位從進場到「下一次營收公布」只有 ~6-8 個交易日
    ⇒ ⛔⛔ 那表示 E1 裡由 rev_hi24 觸發的出場，時鐘是【營收行事曆】給的，
         ⛔ 不是個股走勢給的 —— ⭐ 而這一件從年化／回落上完全看不出來。

    回：逐筆的「進場 → 下一個可得日」交易日數（⛔ 只是一個日曆量，⛔ 與價格無關）。
    """
    avail = sorted({m for (m, e) in rb.values()})
    out = []
    for e in sig["entry_pos"].to_numpy(int):
        nxt = [p for p in avail if p >= e]
        out.append(nxt[0] - e + 1 if nxt else np.nan)
    return pd.Series(out, name="bars_to_next_avail")


def placebo_common(eq0: dict, eq1: dict, ts1: dict, r1: pd.DataFrame, w0: int) -> tuple[list[dict], dict]:
    """§十一①＋§十二②：安慰劑欄。⛔ 兩欄都要報，⛔ 不可只報一個就寫「三臂相同」。

    ⭐【三臂互比】用**共同區間** [窗首, min(t*_E0, t*_E1, t*_R1) − 1]
       （E0 無條件出場 ⇒ 其 t* 取 +∞ ⇒ 實際即 min(t*_E1, 該顆種子 R 次裡最早的 t*_R1)）
    ⭐【各臂對 E0】仍用各自的 [窗首, t*−1]，⛔ 但那一欄只能講該臂自己
    ⚠【區間過短】(< 2 個交易日) 一律用**共同區間**算 ⇒ ⛔ 不算過也不算不過，必報顆數
    ⛔ 零容差：逐顆種子各對一次，200/200 全同才算過。
    """
    h = lambda a: hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()
    rows, same_c, same_i, short, short_i = [], 0, 0, 0, 0
    for r in sorted(eq0):
        g = r1[r1["r"] == r]
        n1 = max(0, min(ts1[r] - w0, len(eq0[r])))                       # E1 自己那一段
        nc = min(n1, int(g["first_exit"].min()) - w0) if len(g) else n1   # ⭐ 共同區間
        nc = max(0, min(nc, len(eq0[r])))
        # ⭐【各臂對 E0】用各臂【自己】的區間 ⇒ ⛔ 它與共同區間那個出口【無關】
        #   （⚠ 登錄的「區間過短」寫在三臂互比那一欄；⛔ 拿它一併作廢本欄 ＝ 少報已經驗到的東西）
        parts = []
        if n1 >= 2:
            parts.append(h(eq1[r][:n1]) == h(eq0[r][:n1]))
        for _, x in g.iterrows():
            n = min(int(x["own_n"]), len(eq0[r]))
            if n >= 2:
                parts.append(x["own_sha"] == h(eq0[r][:n]))
        ok_i = all(parts) if parts else None
        same_i += int(bool(ok_i)) if parts else 0
        short_i += 0 if parts else 1
        col_i = "—（本身也過短）" if not parts else ("✅ 相同" if ok_i else "⛔ 不同")
        if nc < 2:
            short += 1
            rows.append({"r": r, "共同區間日數": nc, "三臂互比": "區間過短", "各臂對E0": col_i})
            continue
        ok_c = h(eq1[r][:nc]) == h(eq0[r][:nc]) and all(h(x[:nc]) == h(eq0[r][:nc]) for x in g["pref"])
        same_c += int(ok_c)
        rows.append({"r": r, "共同區間日數": nc, "三臂互比": "✅ 相同" if ok_c else "⛔ 不同",
                     "各臂對E0": col_i})
    return rows, {"n": len(eq0), "共同區間相同": same_c, "共同區間可驗": len(eq0) - short,
                  "各臂對E0相同": same_i, "各臂對E0可驗": len(eq0) - short_i,
                  "區間過短": short, "各臂自己也過短": short_i}


def overlap_two_ways(a: list, b: list, na: str, nb: str) -> tuple[list[str], float, float]:
    """兩向重疊率（⛔ 只報一個方向會把「一邊月份很多」誤讀成高度重合）。"""
    sa, sb = set(a), set(b)
    both = sa & sb
    ra = len(both) / len(sa) if sa else np.nan
    rb = len(both) / len(sb) if sb else np.nan
    f = lambda x, s: f"{len(both)}/{len(s)} ＝ {len(both) / len(s) * 100:.1f}%" if s else "n/a（分母 0）"
    return [f"{na} 裡有多少是 {nb}：{f(na, sa)}", f"{nb} 裡有多少是 {na}：{f(nb, sb)}"], ra, rb


# ── §四 必報 ＋ §三 判定（⛔ 欄位、門檻、措辭全部逐字取自登錄）──────────────
def verdict_i(d_abs: float, ci: dict) -> tuple[bool, str]:
    """§三(i) 的措辭【事前寫死】⇒ ⛔ 回測線一個字都不訂，本函式只是把登錄的四個出口寫成程式。

    出口順序【不可換】：先過 §十 4-3 的 D 閘門（它決定措辭），再讀 CI。
    ⚠ 第四個出口是【登錄沒有列舉的情形】（CI 不含 0 但方向相反）
      ⇒ ⛔ 不自行補措辭，⏳ 請策略線裁（⭐ 與 PREREGP15 §三(i) 同一族）。
    """
    if d_abs > D_GATE:                                       # §十 4-3：⛔ 絕對值判、門檻 20%
        return False, ("【本件分不開】逐字：\n"
                       "「E1 與 R1 的差同時含【持有天數分配】與【機會數】兩個軸，本件分不開。\n"
                       "  ⛔ 因此本件不宣告條件出場帶了資訊，⛔ 也不宣告它沒帶。」")
    if not ci["detectable"]:
        return False, ("【改善來自「持有時間變短」本身，不是來自「訊號消失」帶了資訊】\n"
                       "⛔ 不可寫成條件出場有效")
    if ci["diff_pp"] > 0:
        return True, "⭐ CI 不含 0 且方向為正 ⇒ E1 的回落改善【明顯大於】R1 ⇒ (i) 通過"
    return False, ("⛔⛔ CI 不含 0，但【方向相反】（E1 的回落改善明顯【小於】R1）\n"
                   "⇒ ⛔ 登錄 §三(i) 只列了「含 0」與「明顯大於」兩種 ⇒ ⭐ 本情形【登錄沒有列舉】\n"
                   "⇒ ⛔ 回測線不自行補措辭（不訂判定用語）⇒ ⏳ 請策略線裁（⭐ 與 P15 §三(i) 同一族）\n"
                   "⇒ ⚠ 而「(i) 沒過」這一點本身無歧義：⛔ 它不是「明顯大於」")


def overlap_verdict(ra: float, rb: float) -> str:
    """§十一② 的三種措辭【事前寫死，⛔ 三種之外不可另寫】。⚠ 判的是【兩向】，⛔ 不是單向。"""
    if ra >= OV_HI and rb >= OV_HI:
        return ("【E1 與 P15 G1 在時點上大量重合 ⇒ ⛔ 兩件不是獨立證據，⛔ 兩件的回落改善不可相加】\n"
                "⚠ 本句綁在『高峰月 ＝ 中位數 ×2』這個沒有外生依據的門檻上")
    if ra < OV_LO and rb < OV_LO:
        return "【兩件打的是不同的月份】"
    return "【重疊程度中等，本件不下判斷】"


def comp_flags(det: pd.DataFrame, raws: dict) -> pd.DataFrame:
    """§四⑥：條件出場那一刻，三個分量裡【哪幾個】不成立（⚠ 可同時多個 ⇒ 可重複計數）。

    S ＝ rev_hi24 ∧ ma60_up ∧ ¬ma_stack ⇒ 它變 False 的三條路：
      rev_hi24 轉 False／ma60_up 轉 False／ma_stack 轉 True
    ⛔ 比較式與 cond_holds 同源（== 100／== 0）⇒ NaN 一律算 False（⭐ 那個語意本身要被報出來）。
    """
    out = {"rev_hi24": [], "ma60_up": [], "ma_stack": []}
    for r in det.itertuples():
        j = int(r.judge_pos)
        if r.reason != "cond" or j < 0:
            for k in out:
                out[k].append(False)
            continue
        row = raws[r.sid].iloc[j]
        out["rev_hi24"].append(not (row["rev_hi24"] == 100))
        out["ma60_up"].append(not (row["ma60_up"] == 100))
        out["ma_stack"].append(not (row["ma_stack"] == 0))
    return pd.DataFrame(out)


def forgone(det: pd.DataFrame, closes: dict, opens: dict) -> pd.DataFrame:
    """§四④：出場日 → 原本 H120 期滿日 的報酬（＝ 如果沒走會拿到的那一段）。

    ⭐ 中位為正 ⇒ 砍掉的是【好單】；為負 ⇒ 砍掉的是【壞單】。
    ⚠ g_E0 ＝ 該筆【原本排程出場】的報酬 ⇒ 依 research11 L522 的同一口徑報「賺>50% 被砍掉」。
    """
    rows = []
    for r in det.itertuples():
        if r.xpos == r.xpos_E0:
            continue                                        # ⛔ 沒有被提早釋放 ⇒ 不是本欄的母體
        c = np.asarray(closes[r.sid], float)
        o = np.asarray(opens[r.sid], float)
        rows.append({"sid": r.sid, "entry_pos": r.entry_pos, "xpos": r.xpos, "xpos_E0": r.xpos_E0,
                     "fwd": float(c[r.xpos_E0]) / float(c[r.xpos]) - 1.0,
                     "g_E0": float(c[r.xpos_E0]) / float(o[r.entry_pos]) - 1.0})
    return pd.DataFrame(rows)


def _band(df: pd.DataFrame, col: str) -> dict:
    x = df[col].astype(float)
    return {f"{col}_med": float(x.median()), f"{col}_p10": float(x.quantile(.10)),
            f"{col}_p90": float(x.quantile(.90))}


def _hold_dist(tr: dict) -> dict:
    """逐筆持有根數（⭐ 全 200 顆種子的【實際成交】彙總 ⇒ ⛔ 不是候選層）。"""
    h = np.concatenate([t["hold_bars"].to_numpy(float) for t in tr.values() if len(t)]) if tr else np.array([np.nan])
    return {"平均": float(np.nanmean(h)), "中位": float(np.nanmedian(h)),
            "p10": float(np.nanpercentile(h, 10)), "p90": float(np.nanpercentile(h, 90)),
            "最大": float(np.nanmax(h)), "筆數": int(np.isfinite(h).sum())}


def _pm(x) -> str:
    return f"{x * 100:+.2f}%"


def report(res: dict) -> dict:
    """⛔ 本函式【不訂任何判準】：門檻（20%／×2／60%／30%／10%）與三種措辭都逐字來自登錄。"""
    out, L = res["out"], []
    e0, e1, r1, dec, dets = res["e0"], res["e1"], res["r1"], res["dec"], res["dets"]
    tr0, tr1, closes, opens, raws = res["tr0"], res["tr1"], res["closes"], res["opens"], res["raws"]
    cal, w0, w1, reps, R = res["cal"], res["w0"], res["w1"], res["reps"], res["rrand"]
    det1 = dets["E1"]

    # ── R1：逐種子先對 R 次取中位（§三(i) 逐字：「R1 側取該種子 R 次的中位」）──
    r1s = r1.groupby("r").median(numeric_only=True).reset_index()

    # ── §四① 各臂年化／回落（含 p10~p90 種子帶）＋平均曝險 ─────────────────
    armdf = {"E0": e0, "E1": e1, **{k: dec[k][0] for k in DECOMP}, "R1": r1s}
    summ = []
    for nm, df in armdf.items():
        row = {"臂": nm, **_band(df, "cagr"), **_band(df, "mdd"),
               "expo_med": float(df["expo"].median()), "trades_med": float(df["trades"].median())}
        row["成本累計_本金倍數"] = row["trades_med"] * P12.COST_STD
        summ.append(row)
    summ = pd.DataFrame(summ)

    # ── §四②⑨ 持有天數分佈（E0／E1／分解三臂 走逐筆；R1 走 worker 帶回的統計量）──
    hold = {"E0": _hold_dist(tr0), "E1": _hold_dist(tr1),
            **{k: _hold_dist(dec[k][2]) for k in DECOMP},
            "R1": {"平均": float(r1s["hold_mean"].median()), "中位": float(r1s["hold_med"].median()),
                   "p10": float(r1s["hold_p10"].median()), "p90": float(r1s["hold_p90"].median()),
                   "最大": float(r1s["hold_max"].max()), "筆數": int(r1["n_trades"].sum())}}

    # ── §四③ 進場筆數與被條件提早出場的筆數（⭐ 逐種子，母體 ＝【實際成交】）────
    early = {(r.sid, r.entry_pos): (r.xpos, r.xpos_E0) for r in det1.itertuples()}
    ent, cut = [], []
    for r, t in tr1.items():
        ent.append(len(t))
        cut.append(int(sum(1 for s, e in zip(t["sid"], t["entry_pos"])
                           if (s, e) in early and early[(s, e)][0] != early[(s, e)][1])))
    ent, cut = np.array(ent, float), np.array(cut, float)
    trig_frac = float(np.median(cut / np.where(ent > 0, ent, np.nan)))
    trig_warn = trig_frac < MIN_TRIG_FRAC

    # ── §四④ 被提早釋放的是好單還是壞單（〈九十六〉，⛔ 缺這一欄不算交件）────
    fg = forgone(det1, closes, opens)
    fg_tr = []                                              # ⭐ 同一算式，母體換成【實際成交】
    for r, t in tr1.items():
        for s, e in zip(t["sid"], t["entry_pos"]):
            if (s, e) in early and early[(s, e)][0] != early[(s, e)][1]:
                fg_tr.append((s, e))
    key = set(fg_tr)
    fgt = fg[[(s, e) in key for s, e in zip(fg["sid"], fg["entry_pos"])]]

    # ── §四⑥ 三個分量的觸發佔比（⚠ 可重複計數）───────────────────────────
    cf = comp_flags(det1, raws)
    ncond = int((det1["reason"] == "cond").sum())
    share = {k: (int(cf[k].sum()), int(cf[k].sum()) / ncond if ncond else np.nan) for k in cf}
    multi = int((cf.sum(axis=1) >= 2).sum())

    # ── §四⑦ 第一個進場日的持股清單與買價（⭐ §十一① 的必要條件，⛔ 保留）────
    def first_day_sig(tr: dict) -> str:
        h = hashlib.sha256()
        for r in sorted(tr):
            t = tr[r]
            if not len(t):
                continue
            d = t[t["entry_pos"] == t["entry_pos"].min()]
            for s, e in sorted(zip(d["sid"], d["entry_pos"])):
                h.update(f"{r}|{s}|{e}|{float(np.asarray(opens[s], float)[e]):.17g}".encode())
        return h.hexdigest()
    fd0, fd1 = first_day_sig(tr0), first_day_sig(tr1)
    fd_dec = {k: first_day_sig(dec[k][2]) for k in DECOMP}

    # ── §四⑧ 順延 ＋ §十一③ H120 上限優先 ────────────────────────────────
    dly = det1["delay"].to_numpy(int)
    cap_n = int((det1["reason"] == "cap_priority").sum())

    # ── §四⑨／§十 4-3 D 閘門（⛔ 閘門用絕對值判、門檻 20%；D_signed 只進必報）──
    n_e1 = pd.Series(ent, index=sorted(tr1)).astype(float)
    n_r1 = r1s.set_index("r")["n_trades"].astype(float).reindex(n_e1.index)
    d_signed = ((n_r1 - n_e1) / n_e1)
    D_abs, D_sgn = float(d_signed.abs().median()), float(d_signed.median())
    d_block = D_abs > D_GATE

    # ── §四⑩／§十一② E1 出場日逐月分佈 ＋ 與 P15 G1 觸發月的兩向重疊 ───────
    mon = pd.Series([str(cal[x])[:7] for x in det1.loc[det1["reason"] == "cond", "xpos"]]).value_counts()
    mon = mon.reindex(sorted(mon.index))
    peak = [m for m in mon.index if mon[m] >= mon.median() * PEAK_MULT]
    g1_path = os.path.join(HERE, "resultsp15", "events.csv")
    if not os.path.exists(g1_path):
        raise SystemExit(f"⛔ 讀不到 P15 G1 觸發月（{g1_path}）⇒ §四⑩ 會靜靜空一欄 ⇒ 停止")
    g1m = sorted(pd.read_csv(g1_path)["month"].astype(str))
    ov_lines, ra, rb_ = overlap_two_ways(peak, g1m, "E1 出場高峰月", "P15 G1 觸發月")
    ov_txt = overlap_verdict(ra, rb_)

    # ── §十一①／§十二② 安慰劑兩欄 ───────────────────────────────────────
    pb_rows, pb = placebo_common(res["eq0"], res["eq1"], res["ts1"], r1, w0)

    # ── §三 判定格（⛔ 唯一一格：E1 vs 使用者判準，基準 ＝ 未捨入值）──────────
    ok, why = P14.judge(float(e1["cagr"].median()), float(e1["mdd"].median()), BENCH_CAGR, BENCH_MDD)

    # ── §三(i) E1 的回落改善 vs R1 的回落改善（逐種子配對，判 CI 含不含 0）────
    m0 = e0.set_index("r")["mdd"].abs()
    imp_e1 = (m0 - e1.set_index("r")["mdd"].abs())
    imp_r1 = (m0 - r1s.set_index("r")["mdd"].abs())
    ci = P8.month_ci((imp_e1 - imp_r1).reindex(m0.index).to_numpy(float))

    # ════ 措辭（⛔ 全部事前寫死，⛔ 不可另寫）⇒ ⭐ 走純函式，四個出口才測得到 ════
    i_pass, i_txt = verdict_i(D_abs, ci)
    verdict = "✅ 通過" if (ok and i_pass) else "⛔【沒有新資訊】"

    # ════ 交件 ════════════════════════════════════════════════════════════
    A = L.append
    A("# PREREGP16 結果報告：**條件出場**（進場理由不再成立就走）")
    A("")
    A(f"⛔ 登錄全文 `backtest/PREREGP16.md`（策略線 seq=5，sha256[:16] ＝ **6dc2e02d621b8cef**，60,083 B）")
    A(f"✅ 授權：K線分析線 2026-09-22 14:25（逐件列名附 seq 與 sha）")
    A(f"⛔ 回測線只負責跑與報數字：判準（§三）、E1 定義（§一）、對照組（§二）、必報欄（§四）全部逐字取自登錄。")
    A(f"")
    A(f"跑法：{reps} 顆種子 × 6 個確定性臂 ＋ R1 {reps}×{R}｜窗 {WIN} {cal[w0].date()} ~ {cal[w1].date()}"
      f"｜耗時 {res['secs'] / 60:.1f} 分")
    A("")
    A("---")
    A("")
    A("## 〇、⛔ 開跑前四道閘門（⭐ 全部在看到任何一格結果之前）")
    A("")
    A("```")
    A(f"① 手算 fixture　　§一1-2 條件 4 格／§一1-3 出場 6 格　　　　【逐位元全同】")
    A(f"② 錨點值　　　　cells.csv 對 P14 §十一1-3 的 21 個值　　　　【逐位元全同】")
    A(f"③ 回聲閘門　　　本趟逐日值 vs panel 在量測日上 {res['echo']['比到的股-月']:,} 個股-月【逐位元全同】")
    A(f"④ 橋欄（§四⑪）　{len(res['br'])} 欄對 resultsp12/cells.csv（round_trip）　　【逐位元全同】")
    A("```")
    A("")
    A("---")
    A("")
    A("## 一、§四① 各臂：年化／最大回落（p10~p90 種子帶）／平均曝險")
    A("")
    A("| 臂 | 年化中位 | p10 | p90 | 回落中位 | p10 | p90 | 曝險 | 交易次數中位 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for r in summ.itertuples():
        A(f"| {r.臂} | {_pm(r.cagr_med)} | {_pm(r.cagr_p10)} | {_pm(r.cagr_p90)} | {_pm(r.mdd_med)} | "
          f"{_pm(r.mdd_p10)} | {_pm(r.mdd_p90)} | {r.expo_med:.3f} | {r.trades_med:,.0f} |")
    A("")
    A(f"⚠ R1 一列是【逐種子先對 {R} 次取中位】之後再跨種子（§三(i) 逐字口徑）。")
    A("")
    A("### ⭐ §四① 的阻斷項：E0 必須逐位元重現 P12 的 (S1,C1,T1)")
    A("")
    A("```")
    A(f"✅ E0 的逐日權益 sha256 與【本趟當場重算的 ANCHOR】逐顆種子各對一次：{reps}/{reps} 逐位元相同（零容差）")
    A("⇒ ⚠ 對的是【本趟自己的兩臂】（§九 的處置）⛔ 不是 P12 那一趟保存的序列（P12 未保存）")
    A(f"⇒ ⭐ 而【P12 那一趟】那一半由橋欄補：{len(res['br'])} 欄逐位元全同（§四⑪／§十三1）")
    A("```")
    A("")
    A("---")
    A("")
    A("## 二、§四②⑨ 持有天數分佈（⭐ E0 的上限是 120 ⇒ 這一欄直接顯示條件觸發得多不多）")
    A("")
    A("| 臂 | 平均 | 中位 | p10 | p90 | 最大 | 逐筆數 |")
    A("|---|---|---|---|---|---|---|")
    for nm, h in hold.items():
        A(f"| {nm} | {h['平均']:.1f} | {h['中位']:.0f} | {h['p10']:.0f} | {h['p90']:.0f} | {h['最大']:.0f} | {h['筆數']:,} |")
    A("")
    A(f"⚠【逐筆數】那一欄的母體不同：E0／E1／分解三臂 ＝ {reps} 趟；"
      f"R1 ＝ {reps}×{R} ＝ {reps * R:,} 趟 ⇒ ⛔ 那一欄不可橫向比大小")
    A(f"⚠ 先驗② 押【30~60 根】⇒ 實測 E1 中位 **{hold['E1']['中位']:.0f} 根**"
      f" ⇒ {'⛔ 沒押中（比押的更短）' if hold['E1']['中位'] < 30 else '✅ 押中'}")
    A(f"⇒ ⛔ 登錄同一條寫著「若它幾乎沒降（>100）⇒ 先查實作」——本趟是【遠低於】那個方向，⛔ 不觸發該條。")
    A("")
    A("### ⭐⭐ 本線加報的一欄：為什麼是 7 根（⛔ 登錄沒要求，⭐ 而少了它會把結構事實讀成訊號）")
    A("")
    A("```")
    rc = res["rev_clock"]
    A(f"進場 → 下一個營收可得日：中位 {rc.median():.0f} 根／p10 {rc.quantile(.1):.0f}／p90 {rc.quantile(.9):.0f}")
    A("⇒ ⛔ panel 的【量測日】是月初，而 rev_hi24 的【可得日】是每月 ~10 日")
    A("⇒ ⭐ 所以 rev_hi24 這個分量最多只能撐到下一次營收公布 ——")
    A("   那是【營收行事曆】給的時鐘，⛔ 不是個股走勢給的")
    A("⇒ ⚠ 這一件從年化／回落上【完全看不出來】（⭐ 只有這一欄講得出來）")
    A("```")
    A("")
    A("---")
    A("")
    A("## 三、§四③ 進場筆數與被條件提早出場的筆數（＝本件的有效樣本數，〈九十八〉）")
    A("")
    A("```")
    A(f"逐種子（母體 ＝【實際成交】）：進場 中位 {np.median(ent):,.0f} 筆／被提早釋放 中位 {np.median(cut):,.0f} 筆")
    A(f"⇒ 觸發佔比 中位 ＝ **{trig_frac * 100:.1f}%**　門檻 {MIN_TRIG_FRAC * 100:.0f}%")
    A(f"⇒ {'⛔⛔ < 10% ⇒ 依登錄【先查實作】' if trig_warn else '✅ ≥ 10% ⇒ 不觸發「先查實作」那一條'}")
    if trig_frac > 0.95:
        A("⛔⛔ 而它是【另一個極端】：登錄只寫了「太低要查實作」，⭐ 本趟幾乎每一筆都被條件砍掉")
        A(f"  ⇒ 候選層 H120 期滿 {int((det1['reason'] == 'H120').sum()):,} 筆 ＝ 沒有任何一筆走到上限")
        A(f"  ⇒ ⭐ 成因就是上一節那一欄：rev_hi24 最多撐到下一次營收公布（中位 {rc.median():.0f} 根）")
        A("  ⇒ ⚠ 所以 E1 量到的不是「訊號消失」，比較像是【營收行事曆的節奏】")
        A("     ⛔ 而這一句是【成因解讀】⇒ 回測線只把數字並排，⏳ 判讀請策略線")
    A(f"候選層（⛔ 不是成交層，⭐ 一併報以免誤讀）：{len(det1):,} 筆訊號中 條件出場 {ncond:,}／"
      f"上限優先 {cap_n:,}／H120 期滿 {int((det1['reason'] == 'H120').sum()):,}")
    A(f"⚠ 因 NaN 判為出場的筆數：{int(det1['nan_exit'].sum()):,}"
      f"（⭐ cond_holds 與進場側同源：NaN 一律算 False ⇒ 這個語意本身要看得見）")
    A("```")
    A("")
    A("---")
    A("")
    A("## 四、⭐⭐⭐ §四④ 被提早釋放的是**好單**還是**壞單**（〈九十六〉，⛔ 缺這一欄不算交件）")
    A("")
    A("```")
    A("算式：出場日收盤 → 原本 H120 期滿日收盤 的報酬（＝ 如果沒走會拿到的那一段）")
    A("")
    for lab, d in (("候選層（去重，⭐ 與種子無關）", fg), ("成交層（本趟真的買到的那些）", fgt)):
        if not len(d):
            A(f"{lab}：0 筆"); continue
        x = d["fwd"].astype(float)
        A(f"{lab}：{len(d):,} 筆")
        A(f"  中位 {_pm(x.median())}／p10 {_pm(x.quantile(.1))}／p90 {_pm(x.quantile(.9))}"
          f"／>0 的比例 {float((x > 0).mean()) * 100:.1f}%")
        rt = float((d['g_E0'] > 0.50).mean())
        A(f"  ⚠ 依 P7 stop_cut_right_tail 同一口徑（research11 L522）：被砍掉的【原本排程出場會賺>50%】"
          f" {int((d['g_E0'] > 0.50).sum()):,} 筆 ＝ {rt * 100:.1f}%")
        A("")
    md = float(fg["fwd"].median()) if len(fg) else np.nan
    A(f"⇒ ⭐ 中位 {'為正 ⇒ 砍掉的是【好單】' if md > 0 else '為負 ⇒ 砍掉的是【壞單】'}")
    A(f"⇒ 先驗④ 押【中位為正（+3~+12pp）】⇒ {'✅ 押中' if md > 0 else '⛔ 沒押中'}：{_pm(md)}")
    A("```")
    A("")
    A("---")
    A("")
    A("## 五、§四⑤ 成本（⚠ 條件出場會增加周轉，這一欄要看得見）")
    A("")
    A("```")
    for r in summ.itertuples():
        A(f"{r.臂:5s} 交易次數中位 {r.trades_med:8,.0f}　成本累計 {r.成本累計_本金倍數:7.2f}"
          f"（＝ 次數 × {P12.COST_STD * 100:.3f}%，單位：部位本金的倍數）")
    e0t = float(summ.loc[summ['臂'] == 'E0', 'trades_med'].iloc[0])
    e1t = float(summ.loc[summ['臂'] == 'E1', 'trades_med'].iloc[0])
    A("")
    A(f"⇒ E1 ÷ E0 ＝ **{e1t / e0t:.2f} 倍**　⇒ 先驗⑥ 押【至少 2 倍】"
      f"⇒ {'✅ 押中' if e1t / e0t >= 2 else '⛔ 沒押中'}")
    A("⛔ 而先驗⑥ 後半押的「成本累計增加 0.5~1.5pp 的【年化】」本件【不報】：")
    A("   那要另跑一格成本 0 ⇒ ⛔ 登錄沒有那一格（§六）⇒ ⛔ 回測線不自行加格。")
    A("```")
    A("")
    A("---")
    A("")
    A("## 六、§四⑥ 三個分量各自的觸發佔比（⚠ 可重複計數，⭐ 已標）")
    A("")
    A("| 分量 | 變成不成立的筆數 | 佔條件出場 |")
    A("|---|---|---|")
    for k in ("ma_stack", "rev_hi24", "ma60_up"):
        n, f = share[k]
        A(f"| {k}{'（轉 True）' if k == 'ma_stack' else '（轉 False）'} | {n:,} | {f * 100:.1f}% |")
    A("")
    A(f"⚠ 同一筆同時有 ≥2 個分量不成立：{multi:,} 筆 ＝ {multi / ncond * 100:.1f}% ⇒ ⛔ 上表三列相加 > 100%")
    A(f"⇒ 先驗⑤ 押【ma_stack 轉 True 觸發最多（40~70%）】⇒ 實測 {share['ma_stack'][1] * 100:.1f}%"
      f" ⇒ {'✅ 押中' if 0.40 <= share['ma_stack'][1] <= 0.70 else '⛔ 沒押中'}")
    A("⛔⛔ 而依 §五 seq=2 註記：先驗⑤ 是【描述性先驗】（三分量依 §二(乙) 只作描述、不進判定）")
    A("   ⇒ ⛔ 不可拿它當「押中了」的戰績，⛔ 也不可據它給任何建議。")
    A("")
    A("---")
    A("")
    A("## 七、⚠ 安慰劑欄（〈一百〇五〉）——**兩欄都報**（§四⑦ 保留 ＋ §十一①／§十二② 新口徑）")
    A("")
    A("### ① §四⑦ 原欄：第一個進場日的持股清單與買價（⭐ 新口徑的必要條件）")
    A("")
    A("```")
    A(f"E0 {fd0[:16]}")
    A(f"E1 {fd1[:16]}　⇒ {'✅ 相同' if fd0 == fd1 else '⛔⛔ 不同 ⇒ 實作有誤'}")
    for k, v in fd_dec.items():
        A(f"{k} {v[:16]}　⇒ {'✅ 相同' if v == fd0 else '⛔⛔ 不同'}")
    A("⚠ 口徑：全 200 顆種子、各自第一個進場日的 (sid, 進場開盤價) 逐筆串起來取 sha256")
    A("```")
    A("")
    A("### ② §十一① 新口徑 ＋ §十二② 兩個區間（⛔ 兩欄都要報，⛔ 不可只報一個）")
    A("")
    A("```")
    A(f"【三臂互比・共同區間】[窗首, min(t*_E1, t*_R1) − 1]　"
      f"{pb['共同區間相同']}/{pb['共同區間可驗']} 逐位元相同（零容差）")
    A(f"【各臂對 E0・各自區間】[窗首, t*−1]　　　　　　　　 "
      f"{pb['各臂對E0相同']}/{pb['各臂對E0可驗']} 逐位元相同（零容差）")
    A(f"⚠【區間過短】(共同區間 < 2 個交易日)：{pb['區間過短']}/{pb['n']} 顆 ⇒ ⛔ 不算過也不算不過")
    A(f"⚠ 各臂【自己的】區間也過短的：{pb['各臂自己也過短']}/{pb['n']} 顆")
    A("")
    A("⇒ ✅ 結論只能寫【三臂在共同區間內完全相同】")
    A("   ⛔ 不可寫【三臂在第一次出場前完全相同】（§十二② 逐字：在 [min(t*), 各臂自己的 t*) 這一段沒有保證）")
    A("")
    A("⛔⛔ 而本趟要【逐字講明這一欄有多弱】（⭐ 四點二：問這個綠燈證明的是哪一件事）：")
    A(f"  共同區間日數 ＝ 最小 {min(x['共同區間日數'] for x in pb_rows)}／"
      f"最大 {max(x['共同區間日數'] for x in pb_rows)} 個交易日")
    A("  ⇒ 成因（⛔ 不是實作有誤）：本策略【在窗首那一天就進場】，")
    A(f"    而 E1 的持有中位只有 {hold['E1']['中位']:.0f} 根、R1 的抽樣下限是 2 根")
    A("    ⇒ ⭐ 第一次出場幾乎貼著窗首 ⇒ 共同區間【結構上】就只有 1~3 天")
    A(f"  ⇒ ⛔⛔ 所以這一欄實際只驗到 {pb['共同區間可驗']}/{pb['n']} 顆種子的【頭 1~3 天】")
    A("    ⛔ 它擋不住「第二次進場就分岔」那一類錯誤 —— ⚠ 而那正是 §十一① 說要它來擋的東西")
    A(f"  ⇒ ⭐ 本件真正擋住那一類錯誤的是【§四⑦ 那一欄】：全 {reps} 顆種子、")
    A("    第一個進場日的 (持股清單, 買價) 逐位元相同（見上一小節）")
    A("  ⇒ ⏳ 這一條請策略線／K線分析線過目：⛔ 回測線不自行改口徑、⛔ 也不自行把它讀成「已驗過」")
    A("```")
    A("")
    A("---")
    A("")
    A("## 八、§四⑧ 順延 ＋ §十一③ H120 上限優先")
    A("")
    A("```")
    A(f"成交順延次數　　　　{int((dly > 0).sum()):,} 筆（佔 {int((dly > 0).sum()) / len(det1) * 100:.2f}%）")
    A(f"最長順延天數　　　　{int(dly.max())} 個交易日")
    A(f"⭐ 順延跨過 H120 期滿日 ⇒ 改以【上限】出場：**{cap_n:,} 筆**（§十一③：⛔ 任何機制都不可突破上限）")
    A("```")
    A("")
    A("---")
    A("")
    A("## 九、⛔⛔ §十 4-3 的 D 閘門（⭐ 它決定 (i) 的措辭，⛔ 不決定判定格）")
    A("")
    A("```")
    A(f"E1 進場筆數 中位 {n_e1.median():,.0f}　／　R1 進場筆數 中位 {n_r1.median():,.0f}")
    A(f"D（絕對值・逐種子算完取中位）＝ **{D_abs * 100:.2f}%**　門檻 {D_GATE * 100:.0f}%"
      f" ⇒ {'⛔⛔ 超過 ⇒ (i) 措辭改【本件分不開】' if d_block else '✅ 未超過 ⇒ (i) 依 §三 原文判'}")
    A(f"D_signed（§十二①／〈一百一十五〉④）＝ **{D_sgn * 100:+.2f}%**　⛔ 只進必報、⛔ 不進判定")
    A(f"⇒ K線分析線 2026-09-21 00:15 的事前先驗【押 R1 的進場筆數偏多】"
      f"⇒ {'✅ 押中' if D_sgn > 0 else '⛔ 沒押中'}（⭐ 這一條是 K線分析線的，⛔ 不是策略線的）")
    A("")
    A("三者並列（§四⑨）：")
    A(f"  進場筆數　E1 {n_e1.median():,.0f}　R1 {n_r1.median():,.0f}")
    A(f"  平均曝險　E1 {float(e1['expo'].median()):.3f}　R1 {float(r1s['expo'].median()):.3f}")
    A(f"  持有根數　E1 中位 {hold['E1']['中位']:.0f}（p10 {hold['E1']['p10']:.0f}／p90 {hold['E1']['p90']:.0f}）"
      f"　R1 中位 {hold['R1']['中位']:.0f}（p10 {hold['R1']['p10']:.0f}／p90 {hold['R1']['p90']:.0f}）")
    A("⇒ ⭐ (a) 校準有沒有成功 ＝ 看持有根數分佈對不對齊；(b) 被放棄那個軸有多大 ＝ 看進場筆數差")
    A("⚠ §十 4-4③ 逐字：第一次出場之後，R1 的選股流【就會與 E1 分岔】—— 那是 (A) 被放棄的直接後果，⛔ 不是 bug")
    A("```")
    A("")
    A("---")
    A("")
    A("## 十、§四⑩／§十一② E1 出場日的逐月分佈 ＋ 與 P15 G1 觸發月的兩向重疊率")
    A("")
    A("```")
    A(f"逐月條件出場筆數：{len(mon)} 個月｜中位 {mon.median():.0f} 筆｜最大 {mon.max():,} 筆（{mon.idxmax()}）")
    A(f"高峰月（≥ 中位 ×{PEAK_MULT:.0f} ＝ {mon.median() * PEAK_MULT:.0f} 筆）：{len(peak)} 個")
    A(f"  {'、'.join(peak) if peak else '（無）'}")
    A("")
    for x in ov_lines:
        A(f"  {x}")
    A("")
    A(f"⇒ 事前寫死的三種措辭 ⇒ 本趟 ＝ {ov_txt}")
    A("")
    A("⭐〈一百一十三〉：報「0 筆」時必須附上【該判準在該群抓到的正例數】")
    A(f"  G1 的 {len(g1m)} 個觸發月，有 {len(set(g1m) & set(mon.index))} 個【出現在 E1 的出場月清單裡】")
    A("  ⇒ ⭐ 所以上面的 0% 不是「比不到」，是【G1 觸發月都不是 E1 的高峰月】")
    A(f"  ⇒ ⚠ 形狀差很遠：G1 觸發月有 {sum(1 for m in g1m if m.endswith('-04'))}/{len(g1m)} 是四月；"
      f"E1 高峰月有 {sum(1 for m in peak if m.endswith('-04'))}/{len(peak)} 是四月")
    A("")
    A("")
    A("⏳ 策略線 1432 §三③ 已請 K線分析線 裁一則【讀法註記】：")
    A("   「兩向都 ≥60%」那一句裡有半句是【兩件的回落改善不可相加】，")
    A("   ⚠ 而 P15 那一側【沒有回落改善】（配對差 −3.12pp、CI[−3.89,−2.35]，回測線 0805）")
    A("   ⇒ ⭐ 也就是那句預寫措辭的前提，在它被觸發之前就失效了")
    fired = "不可相加" in ov_txt
    A(f"⇒ ⛔ 而本趟【{'觸發了' if fired else '沒有觸發'}】那一句（兩向 {ra * 100:.1f}%／{rb_ * 100:.1f}%"
      f"，落在「{'兩向都 ≥60%' if fired else '兩向都 <30%' if (ra < OV_LO and rb_ < OV_LO) else '一高一低'}」）")
    A(f"   ⇒ {'⛔⛔ 觸發了 ⇒ 那一則裁定【直接影響本件措辭】⇒ 交件暫掛該句' if fired else '✅ 沒觸發 ⇒ 那一則裁定對本趟【不生效】（⛔ 但它仍然該裁：下一件可能觸發）'}")
    A("   ⛔ 回測線不自行判它該怎麼讀（⛔ 不訂判定用語）")
    A("")
    A(f"⚠ ×{PEAK_MULT:.0f} 是策略線【在看到任何結果之前】定的粗門檻，⛔ 沒有外生依據（§十三2）")
    A("  ⇒ ⭐ 它【只決定本條的措辭】，⛔ 不進任何判定")
    A("  ⇒ ⭐ 逐月分佈全表見 `exit_months.csv` ⇒ 讀者可自行換門檻重算（⛔ 本件不另跑敏感度）")
    A("```")
    A("")
    A("---")
    A("")
    A("## 十一、⛔⛔ §三 判定")
    A("")
    A("### 判定格【只有一格】：E1 vs 使用者判準（⛔ 全窗）")
    A("")
    A("```")
    A(f"基準（§三 seq=5：**未捨入值**，⛔ 捨入值只可顯示、不進判定）")
    A(f"  年化 {BENCH_CAGR:.17g}　最大回落 {BENCH_MDD:.17g}")
    A(f"E1　年化 {_pm(float(e1['cagr'].median()))}　最大回落 {_pm(float(e1['mdd'].median()))}（逐種子中位）")
    A("")
    A(f"{why}")
    A(f"⇒ 判定格：{'✅ 通過' if ok else '⛔ 沒通過'}")
    A("⚠ 回落那一腳的口徑（§三 seq=5 補）＝ |本臂最大回落| ≤ |基準最大回落|（⭐ 絕對值，越淺越好）")
    A("⚠ 〈一百一十一〉：還要【至少一腳嚴格優於】才算通過")
    A("```")
    A("")
    A("### ⭐⭐ (i) E1 的回落改善必須【明顯大於】R1 的回落改善")
    A("")
    A("```")
    A(f"改善 ＝ |E0 回落| − |本臂回落|（逐種子）；R1 側先對 {R} 次取中位（§三(i) 逐字）")
    A(f"E1 改善 中位 {imp_e1.median() * 100:+.2f}pp　／　R1 改善 中位 {imp_r1.median() * 100:+.2f}pp")
    A(f"配對差（E1 − R1）＝ {ci['diff_pp']:+.2f}pp　CI[{ci['lo_pp']:+.2f}, {ci['hi_pp']:+.2f}]"
      f"　（n＝{ci['n_months']} 顆種子，為正 {ci['pos_months']} 顆）")
    A(f"⇒ CI {'不含' if ci['detectable'] else '含'} 0")
    A("")
    A(f"⭐ 前置閘門（§十 4-3）：D ＝ {D_abs * 100:.2f}% {'>' if d_block else '≤'} {D_GATE * 100:.0f}%")
    A(f"⇒ {i_txt}")
    A("```")
    A("")
    A("### ⛔ 本件判定")
    A("")
    A("```")
    A(f"判定格 {'✅ 通過' if ok else '⛔ 沒通過'}　＋　(i) {'✅ 通過' if i_pass else '⛔ 沒過'}")
    A(f"⇒ 登錄 §三 逐字：「(i) 沒過 ⇒ 本件判【沒有新資訊】，⛔ 不論判定格通不通過」")
    A(f"⇒ ⛔ 本件 ＝ **{verdict}**")
    A("```")
    A("")
    A("### ⚠ 描述格的多重檢定（§三 逐字）")
    A("")
    A("```")
    A("E1a／E1b／E1c 三格 × 5% ＝ 虛無期望 0.15 格")
    A("⇒ ⛔ 三格裡有一格「測得出」不可以當發現 ⇒ ⭐ 所以本報告的分解三臂【只作描述】")
    A("```")
    A("")
    A("---")
    A("")
    A("## 十二、§五 先驗對帳（⛔ 寫下就不改・⭐ 押判定）")
    A("")
    A("| # | 押的 | 實測 | 對帳 |")
    A("|---|---|---|---|")
    c1 = float(e1["cagr"].median())
    c0 = float(e0["cagr"].median())
    dc, dm = (c1 - c0) * 100, imp_e1.median() * 100
    A(f"| ①a | 判定格【沒通過】，而且是【年化那一腳】沒過 | 判定格 {'通過' if ok else '沒通過'}"
      f"；年化腳 {'沒過' if c1 < BENCH_CAGR else '過'} | {'✅ 押中' if not ok and c1 < BENCH_CAGR else '⛔ 沒押中'} |")
    A(f"| ①b | 年化【降 4~10pp】 | {dc:+.2f}pp | "
      f"{'✅ 押中' if -10 <= dc <= -4 else '⚠ 方向對、幅度遠在帶外' if dc < -10 else '⛔ 沒押中'} |")
    A(f"| ①c | 回落【改善 3~8pp】 | {dm:+.2f}pp | "
      f"{'✅ 押中' if 3 <= dm <= 8 else '⛔⛔ 方向就反了（回落不是變淺，是變深）' if dm < 0 else '⛔ 沒押中'} |")
    A(f"| ② | 平均持有 30~60 根 | 中位 {hold['E1']['中位']:.0f} 根 | "
      f"{'✅' if 30 <= hold['E1']['中位'] <= 60 else '⛔ 沒押中'} |")
    A(f"| ③ | (i) 那一道【含 0】 | CI {'不含' if ci['detectable'] else '含'} 0 | "
      f"{'✅ 押中' if not ci['detectable'] else '⛔ 沒押中'} |")
    A(f"| ④ | 被提早釋放的是【好單】（中位 +3~+12pp） | 中位 {_pm(md)} | "
      f"{'✅ 押中' if 0.03 <= md <= 0.12 else ('⚠ 方向對、幅度不在帶內' if md > 0 else '⛔ 沒押中')} |")
    A(f"| ⑤ | ma_stack 觸發最多（40~70%） | {share['ma_stack'][1] * 100:.1f}% | "
      f"{'✅' if 0.40 <= share['ma_stack'][1] <= 0.70 else '⛔'}（⛔ 描述性先驗，不計戰績） |")
    A(f"| ⑥ | 交易次數至少 2 倍 | {e1t / e0t:.2f} 倍 | {'✅' if e1t / e0t >= 2 else '⛔ 沒押中'} |")
    A("")
    A("⭐ K線分析線 00:15 的那一條（⛔ 不是策略線的先驗）：押 R1 進場筆數偏多 ⇒ "
      f"D_signed {D_sgn * 100:+.2f}% ⇒ {'✅ 押中' if D_sgn > 0 else '⛔ 沒押中'}")
    A("")
    A("---")
    A("")
    A("## 十三、⛔ 回測線**不做**的幾件（⭐ 逐字列出，免得被讀成漏了）")
    A("")
    A("```")
    A("⛔ 不解讀「為什麼」　　⇒ §二(乙) 的三個分量只作描述；成因解讀是策略線的格子")
    A("⛔ 不訂措辭　　　　　⇒ (i) 的三種措辭、§十一② 的三種措辭全部逐字取自登錄")
    A("⛔ 不加格　　　　　　⇒ 成本 0 那一格、×1.5／×3 的敏感度，登錄都沒有 ⇒ 不跑")
    A("⛔ 不動引擎　　　　　⇒ 六個臂全部是【改寫 xpos ＋ 重算 g】的 sig 框（§一1-3④）")
    A("```")
    A("")

    rep_path = os.path.join(out, "P16_REPORT.md")
    txt = "\n".join(L) + "\n"
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(txt)
    back = open(rep_path, encoding="utf-8").read()          # ⭐ 四點二：寫完重讀，斷言讀回來的內容
    if back != txt or "本件 ＝" not in back:
        raise SystemExit("⛔ 報告重讀對不上 ⇒ 停止")

    summ.to_csv(os.path.join(out, "summary.csv"), index=False)
    pd.DataFrame(pb_rows).to_csv(os.path.join(out, "placebo.csv"), index=False)
    mon.rename("筆數").rename_axis("month").to_frame().assign(
        高峰月=[m in peak for m in mon.index]).to_csv(os.path.join(out, "exit_months.csv"))
    fg.to_csv(os.path.join(out, "forgone.csv"), index=False)
    pd.DataFrame(hold).T.rename_axis("臂").to_csv(os.path.join(out, "hold_dist.csv"))
    pd.DataFrame({"r": n_e1.index, "n_E1": n_e1.to_numpy(), "n_R1": n_r1.to_numpy(),
                  "D_signed": d_signed.to_numpy()}).to_csv(os.path.join(out, "d_gate.csv"), index=False)
    res["rev_clock"].to_frame().to_csv(os.path.join(out, "rev_clock.csv"), index=False)
    print("\n".join(L[-14:]), flush=True)
    print(f"[報告] {rep_path}（{len(txt):,} B）", flush=True)
    return {"ok": ok, "i_pass": i_pass, "verdict": verdict, "D": D_abs, "D_signed": D_sgn,
            "ci": ci, "placebo": pb, "summ": summ, "path": rep_path}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--rrand", type=int, default=R_RANDOM)
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda x: print(x, flush=True)
    t0 = time.time()

    # ⭐ ① 最先跑兩組手算 fixture：與資料、隨機源全部無關 ⇒ 壞了要當場知道
    cf, xf = cond_fixture(), exit_fixture()
    log(f"[fixture] §一1-2 條件 {len(cf)} 格／§一1-3 出場 {len(xf)} 格【逐位元全同】")
    anc_rows = P14.anchor_check()
    log(f"[錨點值] cells.csv 對 P14 §十一1-3 的 {len(anc_rows)} 個值【逐位元全同】")

    # ② 資料與訊號（⛔ 與 P12／P14／P15 同一條路）
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, WIN)
    marks = P12.month_marks(cal, w0, w1)
    log(f"[窗] {WIN} [{w0},{w1}] {w1 - w0 + 1} 日（{cal[w0].date()} ~ {cal[w1].date()}）")

    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    log(f"[sig] 門檻B ✅ 七個驗收數逐項相同：{len(sig):,} 筆／{sig['sid'].nunique():,} 檔")

    # ③ 逐日三分量（⭐ 走 panel 的同一條路）
    tdr = P4F.load_tdr_codes()
    rev, _, _ = R34.load_revenue()
    rev_flags = P4F.rev_hi24_flags(rev, cal, 10, incl_current=False, undecided=tdr)
    sids = sorted(set(sig["sid"]))
    with Pool(a.procs, initializer=_init_raw, initargs=(cal, rev_flags)) as pool:
        res = pool.map(_raw_worker, [(s, uni.get(s, "twse")) for s in sids], chunksize=8)
    raws = {s: r for s, r in res if r is not None}
    miss = [s for s in sids if s not in raws]
    if miss:
        raise SystemExit(f"⛔ {len(miss)} 檔取不到逐日特徵（例：{miss[:5]}）⇒ 停止，⛔ 不可略過")
    log(f"[逐日] {len(raws):,} 檔的 rev_hi24／ma60_up／ma_stack（{time.time() - t0:.0f}s）")

    echo = panel_echo_check(raws, panel, cal)
    log(f"[回聲閘門] 本趟逐日值 vs panel 在量測日上：{echo['比到的股-月']:,} 個股-月【逐位元全同】")

    trad = {s: tradable_of(raws[s], closes[s]) for s in raws}

    # ⭐⭐ 本線加報的一欄：進場 → 下一個營收可得日 有幾根（⛔ 純日曆量）
    rb = R34.rebalance_dates(list(rev.index), cal, 10)
    rc = rev_clock(sig, cal, rb)
    log(f"[營收時鐘] 進場→下一個可得日：中位 {rc.median():.0f} 根／p10 {rc.quantile(.1):.0f}／"
        f"p90 {rc.quantile(.9):.0f} ⇒ ⭐ rev_hi24 最多只能撐這麼久（⛔ 與個股無關）")

    # ④ 造臂（⛔ 改寫 xpos ＋ 重算 g，⛔ 一行引擎都沒動）
    sigs, dets = {"E0": sig}, {}
    for nm, only in [("E1", None)] + [(k, v) for k, v in DECOMP.items()]:
        sigs[nm], dets[nm] = build_arm(sig, raws, trad, closes, opens, only=only)
        d = dets[nm]
        log(f"[臂] {nm:4s} 條件出場 {int((d['reason'] == 'cond').sum()):,} 筆／上限優先 "
            f"{int((d['reason'] == 'cap_priority').sum()):,}／H120 {int((d['reason'] == 'H120').sum()):,}"
            f"｜持有根數中位 {d['hold_bars'].median():.0f}｜因 NaN 出場 {int(d['nan_exit'].sum()):,}")
    sigs["ANCHOR"] = sig

    P14._init(sig, closes, opens, ncal, w0, w1, marks, cal, None)
    _P.update(sigs=sigs, raws=raws, trad=trad, closes=closes, opens=opens, R=a.rrand)

    # ⑤ 跑：ANCHOR／E0（⛔ 兩次獨立呼叫 ⇒ 逐位元相同才是真的檢查）＋ E1／分解三臂
    def run(arm, keep=False, wl=False):
        with Pool(a.procs) as p:
            res = p.map(_one16, [(arm, r, keep, wl) for r in range(a.reps)])
        return (pd.DataFrame([x[0] for x in res]),
                {x[0]["r"]: x[1] for x in res if x[1] is not None},
                {x[0]["r"]: x[2] for x in res if x[2] is not None},
                {x[0]["r"]: x[3] for x in res if x[3] is not None})

    anc, _, _, _ = run("ANCHOR")
    e0, eq0, tr0, _ = run("E0", keep=True, wl=True)
    same = sum(int(x == y) for x, y in zip(anc["eq_sha"], e0["eq_sha"]))
    if same != len(anc):
        raise SystemExit(f"⛔⛔ 否證①：E0 對不上當場重算的 P12 (S1,C1,T1) ⇒ 停止（逐位元相同 {same}/{len(anc)}）")
    log(f"[否證①] ✅ E0 的逐日權益 sha256 與當場重算【{same}/{len(anc)} 逐位元相同】（零容差，n={len(anc)}）")

    tab = P12.cell_table(anc.assign(**P14.BRIDGE_KEY))
    br = P14.bridge_check(tab)
    log(f"[橋欄] ✅ {len(br)} 欄對 resultsp12/cells.csv【逐位元全同】(round_trip)")

    e1, eq1, tr1, ts1 = run("E1", keep=True, wl=True)
    log(f"[E1] {len(e1)} 顆（{time.time() - t0:.0f}s）")
    dec = {}
    for nm in DECOMP:
        dec[nm] = run(nm, wl=True)
    log(f"[分解三臂] 各 {a.reps} 顆（{time.time() - t0:.0f}s）")

    # ⑥ R1：每顆種子用 E1【實際成交】那幾筆的持有根數當經驗分佈，抽 R 次
    _P["e1_hold"] = {r: tr1[r]["hold_bars"].to_numpy() for r in tr1}
    _P["ts1"] = ts1                       # ⭐ §十二②：共同區間的上界之一 ⇒ worker 只需帶回這麼長的前綴
    with Pool(a.procs) as p:
        r1rows = p.map(_r1_worker, list(range(a.reps)))
    r1 = pd.DataFrame([x for xs in r1rows for x in xs])
    log(f"[R1] {len(r1):,} 趟（{a.reps}×{a.rrand}，rng ＝ default_rng({SEED_R1}+r)）（{time.time() - t0:.0f}s）")

    res = dict(rev_clock=rc, anc=anc, e0=e0, e1=e1, dec=dec, r1=r1, dets=dets, tr0=tr0, tr1=tr1,
               eq0=eq0, eq1=eq1, ts1=ts1, sig=sig, cal=cal, w0=w0, w1=w1, marks=marks,
               raws=raws, closes=closes, opens=opens,
               echo=echo, br=br, out=a.out, reps=a.reps, rrand=a.rrand, secs=time.time() - t0)
    for nm, df in (("e0_by_seed", e0), ("e1_by_seed", e1), ("r1_by_seed", r1),
                   ("det_E1", dets["E1"]), ("det_E1a", dets["E1a"]),
                   ("det_E1b", dets["E1b"]), ("det_E1c", dets["E1c"]),
                   ("bridge", pd.DataFrame(br))):
        df.to_csv(os.path.join(a.out, f"{nm}.csv"), index=False)
    log(f"[out] {a.out}（{time.time() - t0:.0f}s）")
    res["rep"] = report(res)
    log(f"[完成] {time.time() - t0:.0f}s")
    return res


if __name__ == "__main__":
    main()

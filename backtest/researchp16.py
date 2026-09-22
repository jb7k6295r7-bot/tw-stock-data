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
        out.append({"r": r, "rep": rep, "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest(),
                    "n_trades": len(tr), "hold_med": float(tr["hold_bars"].median()) if len(tr) else np.nan,
                    "first_exit": _first_exit(log),
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


def placebo_common(eqs: dict, t_star: dict, w0: int) -> tuple[list[dict], dict]:
    """§十一①＋§十二②：安慰劑欄。⛔ 兩欄都要報，⛔ 不可只報一個就寫「三臂相同」。

    ⭐【三臂互比】用**共同區間** [窗首, min(t*_E0, t*_E1, t*_R1) − 1]
       （E0 無條件出場 ⇒ 其 t* 取 +∞ ⇒ 實際即 min(t*_E1, t*_R1)）
    ⭐【各臂對 E0】仍用各自的 [窗首, t*−1]，⛔ 但那一欄只能講該臂自己
    ⚠【區間過短】(< 2 個交易日) 一律用**共同區間**算 ⇒ ⛔ 不算過也不算不過，必報顆數
    """
    rows, same_c, same_i, short = [], 0, 0, 0
    arms = [a for a in eqs if a != "E0"]
    for r in sorted(eqs["E0"]):
        nc = min(t_star[a][r] for a in t_star) - w0          # 共同區間長度（窗內索引）
        h = lambda a, n: hashlib.sha256(np.asarray(eqs[a][r][:n], float).tobytes()).hexdigest()
        if nc < 2:
            short += 1
            rows.append({"r": r, "共同區間日數": nc, "三臂互比": "區間過短", "各臂對E0": "—"})
            continue
        ok_c = all(h(a, nc) == h("E0", nc) for a in arms)
        same_c += int(ok_c)
        ok_i = all(h(a, max(0, t_star[a][r] - w0)) == h("E0", max(0, t_star[a][r] - w0))
                   for a in arms if t_star[a][r] - w0 >= 2)
        same_i += int(ok_i)
        rows.append({"r": r, "共同區間日數": nc, "三臂互比": "✅ 相同" if ok_c else "⛔ 不同",
                     "各臂對E0": "✅ 相同" if ok_i else "⛔ 不同"})
    n = len(eqs["E0"])
    return rows, {"n": n, "共同區間相同": same_c, "各臂對E0相同": same_i, "區間過短": short}


def overlap_two_ways(a: list, b: list, na: str, nb: str) -> tuple[list[str], float, float]:
    """兩向重疊率（⛔ 只報一個方向會把「一邊月份很多」誤讀成高度重合）。"""
    sa, sb = set(a), set(b)
    both = sa & sb
    ra = len(both) / len(sa) if sa else np.nan
    rb = len(both) / len(sb) if sb else np.nan
    f = lambda x, s: f"{len(both)}/{len(s)} ＝ {len(both) / len(s) * 100:.1f}%" if s else "n/a（分母 0）"
    return [f"{na} 裡有多少是 {nb}：{f(na, sa)}", f"{nb} 裡有多少是 {na}：{f(nb, sb)}"], ra, rb


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
    with Pool(a.procs) as p:
        r1rows = p.map(_r1_worker, list(range(a.reps)))
    r1 = pd.DataFrame([x for xs in r1rows for x in xs])
    log(f"[R1] {len(r1):,} 趟（{a.reps}×{a.rrand}，rng ＝ default_rng({SEED_R1}+r)）（{time.time() - t0:.0f}s）")

    res = dict(rev_clock=rc, anc=anc, e0=e0, e1=e1, dec=dec, r1=r1, dets=dets, tr0=tr0, tr1=tr1,
               eq0=eq0, eq1=eq1, ts1=ts1, sig=sig, cal=cal, w0=w0, w1=w1, marks=marks,
               echo=echo, br=br, out=a.out, reps=a.reps, rrand=a.rrand, secs=time.time() - t0)
    for nm, df in (("e0_by_seed", e0), ("e1_by_seed", e1), ("r1_by_seed", r1),
                   ("det_E1", dets["E1"]), ("det_E1a", dets["E1a"]),
                   ("det_E1b", dets["E1b"]), ("det_E1c", dets["E1c"]),
                   ("bridge", pd.DataFrame(br))):
        df.to_csv(os.path.join(a.out, f"{nm}.csv"), index=False)
    log(f"[out] {a.out}（{time.time() - t0:.0f}s）")
    return res


if __name__ == "__main__":
    main()

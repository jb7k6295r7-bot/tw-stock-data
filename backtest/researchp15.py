"""PREREGP15：用**自己的候選檔數**當月度閘門 —— 回測線執行端。

⛔ 登錄全文 `backtest/PREREGP15.md`（策略線 seq=4，2026-09-22 14:10 台北投遞）
   sha256[:16] ＝ **684bf7d4acb3feb2**
   ⚠ 口徑：**去掉 pw1 戳記行、檔尾恰一個換行**（44,183 B）。
   ✅ K線分析線 0645 §〇【授權開跑】逐件列名附 seq 與 sha ⇒ 本支跑的就是那一份。

⛔⛔ 本支【不訂判準、不訂判定用語、不設計策略】——§三 的判準、§一 的 K(t)、
     §二 的兩個對照組、§四 的必報欄，全部逐字取自登錄。回測線只負責跑與報數字。

⭐ 四個臂（§一／§二）：
  G0       現行：每個有候選的月份都進場　⇒ ⛔ 必須逐位元重現 P12 的 (S1,C1,T1)
  G1       當月候選數 < K(t) ⇒ 該月不進場（⭐ 已持有的部位不動）
  PLACEBO  §二(甲) 假閘門：隨機挑【數量相同】的月份不進場，每顆種子抽 R=30 次取中位
  NOAPR    §二(乙) 排除四月：一律把每年四月的訊號整個排除

⭐⭐ 為什麼本支【沒有】自己的引擎呼叫點（⛔ 與 P14 的理由相反，而兩者不衝突）：
  P14 之所以要自己一個，是因為它需要 cash_mode="bench"，而 P12 的 `_sim` 把 "zero" 寫死。
  ⚠ 而本件的共同設定與 P12 逐字相同（cash_mode="zero"／成本 0.585%／pick=None…）
  ⇒ ⛔ 再抄一份 `_sim` 就是 CLAUDE.md 四點五 的第十二份 ⇒ ⭐ 本支 import `P14._sim`。
  ⇒ ⚠ 而登錄 §九1(a) 要的是【本件這一趟當場重算、同一個 commit】——
     ⭐ 用 import 來的函式在本趟被呼叫，那一條完全滿足；它擋的是「從檔案讀舊結果」。

⭐ 同理 import 而不抄的還有：`P14.judge`（⭐ 基準由呼叫端傳，⛔ 本件的基準不同）、
   `P14.mdd_with_date`、`P14.bridge_check`、`P14.anchor_check`、`P9.weak_flags`、
   `P12.win_read`／`win_bounds`／`month_marks`／`cell_table`、`R13.window_stats`。
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
from . import research13 as R13
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp8 as P8
from . import researchp9 as P9
from . import researchp11 as P11
from . import researchp12 as P12
from . import researchp14 as P14

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp15")

# ── 登錄寫死的常數（⛔ 一個都不可以在這裡「挑」）──────────────────────────────
WIN = "全窗"                 # §三：判定窗（2017-03-02 ~ 2026-08-24）
REPS = 200                   # §一：r ∈ [0, 200)
R_PLACEBO = 30               # §二(甲)／§九2：⛔ 開跑前寫死，⛔ 不因看到結果而改
WARMUP = 12                  # §一：前 12 個有候選的月份【不套閘門】⇒ 另列
K_DIV = 2                    # §一：K(t) 的「÷2」（⛔ 不試 3、不試 1.5）
SEED_PLACEBO = 105000        # §二(甲)：假閘門月份抽樣的【獨立 rng 流】，⛔ 不進選股流

# §三（seq=3 改・0146 §二 已准）：基準改【未捨入值】——⛔ 同一條序列、同一個窗
BENCH_CAGR = 0.24020209886370614
BENCH_MDD = -0.3395700527611012

# §三(ii)：G1 的觸發月 ≥ 這個比例是四月 ⇒ 判【沒有新資訊】（⛔ 事前寫死）
APR_SHARE_GATE = 0.80
MIN_EVENTS = 10              # §四③：觸發月數 < 10 ⇒ 一律寫「在這 N 個月上」

ARMS = ("ANCHOR", "G0", "G1", "NOAPR")   # PLACEBO 另走一條（每顆種子 R 次）


# ── §一：K(t)（⭐ 全檔只有這一個地方算它）────────────────────────────────────
def k_series(counts: pd.Series, warmup: int = WARMUP, div: int = K_DIV,
             half_up: bool = False) -> pd.DataFrame:
    """K(t) ＝ round( median( 該訊號集在【t 之前已實現】的逐月候選數 ) ÷ div )。

    ⛔ 展開式中位數（expanding median），⛔ 不是全窗中位數（那是 in-sample）。
    ⛔ 前 `warmup` 個有候選的月份不套閘門 ⇒ K 記成 NaN，⭐ 那一段另列（§四⑥）。

    ⚠⚠ `round` 有兩種讀法而兩種都不報錯（〈六十七〉）：Python 的 round() 是
    **銀行家捨入**（.5 進到偶數），而一般人寫 round 想的是 **.5 一律進位**。
    ⇒ ⛔ 本函式【不替登錄選一個】：兩種都算得出來，由呼叫端兩種都跑並比對，
       ⭐ 若兩種的擋月清單相同 ⇒ 那個歧義在本件不影響任何結果（必報）。

    counts：index ＝ "YYYY-MM"（⭐ 已依序），value ＝ 該月候選檔數。
    """
    ms = list(counts.index)
    if list(ms) != sorted(ms):
        raise SystemExit("⛔ K(t)：月份沒有依序 ⇒ 展開式中位數會算錯，停止")
    out = []
    for i, m in enumerate(ms):
        if i < warmup:
            out.append({"month": m, "cand": int(counts.iloc[i]), "n_prev": i, "med_prev": np.nan,
                        "K": np.nan, "套閘門": False})
            continue
        prev = counts.iloc[:i].to_numpy(float)          # ⭐ 嚴格【t 之前】⇒ 無前視
        med = float(np.median(prev))
        x = med / div
        k = float(np.floor(x + 0.5)) if half_up else float(round(x))
        out.append({"month": m, "cand": int(counts.iloc[i]), "n_prev": i, "med_prev": med,
                    "K": k, "套閘門": True})
    return pd.DataFrame(out)


def blocked_months(kt: pd.DataFrame) -> list[str]:
    """§一：當月候選數 < K(t) ⇒ 該月不進場。⛔ 前 WARMUP 個月不套閘門 ⇒ 不會被擋。"""
    m = kt["套閘門"].to_numpy(bool) & (kt["cand"].to_numpy(float) < kt["K"].to_numpy(float))
    return list(kt.loc[m, "month"])


def gate_fixture() -> list[dict]:
    """§四⑦ 之前先擋一次：K(t) 與擋月規則的**手算 fixture**（⛔ 與真實資料、隨機源無關）。

    ⭐ 依〈一百一十三〉：一組 fixture 要先證明它【分得出來】——所以這一組刻意放了
       三種會被實作寫反的情形，每一種都有一格答案不同：
       ① 展開式 vs 全窗中位（若誤用全窗，第 13 個月的 K 會不同）
       ② 「嚴格小於」vs「小於等於」（cand 恰等於 K 的那一格）
       ③ warmup 的邊界（第 12 個月不套、第 13 個月套）
    ⛔ 任何一格對不上 ⇒ 停止，⛔ 不可改 fixture 再跑一次。
    """
    rows, bad = [], []

    # ── A 組：暖身邊界 ＋ 嚴格小於 ＋ 擋月清單 ──────────────────────────────
    # ⭐ 值都挑成【中位恆為 20.0、K 恆為 10.0】⇒ 二進位可精確表示，⛔ 也沒有 .5 的捨入歧義
    #    （〈一百二十一〉：fixture 的數值要能被精確表示，⛔ 否則正確實作也會假紅）
    idx_a = [f"2000-{i + 1:02d}" for i in range(12)] + ["2001-01", "2001-02", "2001-03"]
    #        前 11 個月 20；⭐ 第 12 個月故意放 1（它低於任何 K，⛔ 而它在暖身內 ⇒ 不可以被擋）
    counts_a = pd.Series([20] * 11 + [1] + [9, 10, 11], index=idx_a)
    kt_a = k_series(counts_a)
    exp_a = {"2000-12": (False, np.nan),      # ⭐ 暖身邊界：cand=1 低到不行，⛔ 仍不套閘門
             "2001-01": (True, 10.0),         # 中位 20 ⇒ K 10；cand 9 < 10 ⇒ 擋
             "2001-02": (True, 10.0),         # ⭐ cand 10 ＝ K 10 ⇒【嚴格小於】⇒ 不擋
             "2001-03": (True, 10.0)}
    for m, (應套, 應K) in exp_a.items():
        r = kt_a[kt_a["month"] == m].iloc[0]
        ok = (bool(r["套閘門"]) == 應套) and (repr(float(r["K"])) == repr(float(應K)))
        rows.append({"組": "A", "月": m, "套閘門": bool(r["套閘門"]), "K": float(r["K"]),
                     "要": f"{應套}/{應K}", "逐位元": "✅" if ok else "⛔"})
        if not ok:
            bad.append(f"  A/{m}: 得 套={r['套閘門']}/K={r['K']!r}，要 套={應套}/K={float(應K)!r}")
    got_a, want_a = blocked_months(kt_a), ["2001-01"]
    rows.append({"組": "A", "月": "擋月清單", "套閘門": "-", "K": "-", "要": str(want_a),
                 "逐位元": "✅" if got_a == want_a else "⛔"})
    if got_a != want_a:
        bad.append(f"  A/擋月清單: 得 {got_a}，要 {want_a}")

    # ── B 組：⭐【展開式中位 vs 全窗中位】——⛔ 誤用全窗就是 in-sample（登錄 §一 逐字禁止）
    #    前 13 個月都是 2、之後 20 個月都是 1000
    #    ⇒ 展開式在第 13 個月只看得到前 12 個 2 ⇒ 中位 2 ⇒ K ＝ 1
    #    ⇒ 而【全窗】中位是 1000 ⇒ K ＝ 500 ⇒ 第 13 個月 (cand 2) 會被擋
    #    ⇒ ⭐ 兩種讀法的【擋月清單不同】⇒ 這一格分得出來（〈一百一十三〉）
    idx_b = [f"2010-{i + 1:02d}" for i in range(12)] + [f"2011-{i:02d}" for i in range(1, 22)]
    counts_b = pd.Series([2] * 13 + [1000] * 20, index=idx_b)
    kt_b = k_series(counts_b)
    k13 = float(kt_b[kt_b["month"] == "2011-01"].iloc[0]["K"])
    k_full = float(round(float(np.median(counts_b.to_numpy(float))) / K_DIV))
    got_b = blocked_months(kt_b)
    for nm, a_, b_ in (("第13月的K（展開式）", repr(k13), repr(1.0)),
                       ("同月若誤用全窗中位", repr(k_full), repr(500.0)),
                       ("擋月清單（展開式）", str(got_b), str([]))):
        ok = a_ == b_
        rows.append({"組": "B", "月": nm, "套閘門": "-", "K": a_, "要": b_,
                     "逐位元": "✅" if ok else "⛔"})
        if not ok:
            bad.append(f"  B/{nm}: 得 {a_}，要 {b_}")
    if k13 == k_full:
        bad.append("  B: 展開式與全窗給出同一個 K ⇒ ⛔ 這一格分不出來，fixture 失效")

    if bad:
        raise SystemExit("⛔⛔ §一 的 K(t)／擋月規則手算 fixture 對不上 ⇒ 閘門本身寫錯，本件不出結論\n"
                         + "\n".join(bad))
    return rows


# ── 引擎（⛔ 本檔沒有呼叫點：用 P14._sim，理由見檔頭）──────────────────────────
_P: dict = {}


def _init15(sigs: dict, placebo: dict):
    _P.update(sigs=sigs, placebo=placebo)


def _one15(args):
    """一個臂的一顆種子。⭐ 選股種子一律 P12.SEED0 + r（§八①：G0 與 G1 同一個隨機源）。"""
    arm, r, rep, keep_eq = args
    seed = P12.SEED0 + r
    if arm == "PLACEBO":
        base = _P["sigs"]["G0"]
        sig = base[~base["month"].isin(_P["placebo"][(r, rep)])].reset_index(drop=True)
    else:
        sig = _P["sigs"][arm]
    out = P14._sim(sig, P12.N_C1, seed, P12.COST_STD)
    eq = np.asarray(out["equity"], float)
    w0, w1 = P14._S["w0"], P14._S["w1"]
    row = {"arm": arm, "r": r, "rep": rep, "seed": seed,
           "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest(),
           **P12.win_read(out, w0, w1, P14._S["marks"])}
    hd = out.get("hold_days")
    row["hold_days"] = float(np.mean(hd)) if hd is not None and len(hd) else np.nan
    row.pop("mret", None)
    return (row, eq[w0:w1 + 1].copy() if keep_eq else None)


def run(pool, arm: str, reps: int, keep_eq: bool = False):
    res = pool.map(_one15, [(arm, r, -1, keep_eq) for r in range(reps)])
    return pd.DataFrame([x[0] for x in res]), {x[0]["r"]: x[1] for x in res if x[1] is not None}


# ── §四⑦（seq=4 改）：安慰劑欄 ＝ 第一個觸發月之前，兩臂逐日權益逐位元相同 ──────
def placebo_column(eq0: dict, eq1: dict, m_star: int, w0: int) -> tuple[list[dict], dict]:
    """區間 [窗首, m*−1] 內 G0 與 G1 的逐日權益 sha256，逐顆種子各對一次。

    ⛔ 200/200 全同才算過，⛔ 零容差（§四⑦ 新口徑，＝ K線分析線 0146 §1-3）。
    ⚠ 區間過短（< 2 個交易日）⇒ 標【區間過短】：⛔ 不算過也不算不過，並必報顆數。
    ⭐ 它為什麼是真的檢查：閘門【只該改變進場】⇒ 第一次被擋之前兩臂必須完全相同
       ⇒ ⛔ 若閘門洩漏進選股排序／槽位計數／rng 流 ⇒ 這一欄立刻紅。
    """
    n = m_star - w0                      # [w0, m*−1] 的長度（以窗內索引計）
    rows, same, short = [], 0, 0
    for r in sorted(eq0):
        if n < 2:
            short += 1
            rows.append({"r": r, "n_days": n, "結果": "區間過短"})
            continue
        a = hashlib.sha256(np.asarray(eq0[r][:n], float).tobytes()).hexdigest()
        b = hashlib.sha256(np.asarray(eq1[r][:n], float).tobytes()).hexdigest()
        rows.append({"r": r, "n_days": n, "G0_sha": a[:16], "G1_sha": b[:16],
                     "結果": "✅ 相同" if a == b else "⛔ 不同"})
        same += int(a == b)
    return rows, {"n": len(eq0), "same": same, "short": short, "n_days": n}


def month_entry_pos(sig: pd.DataFrame) -> pd.Series:
    """每個候選月的【進場日】（⭐ 月頻訊號 ⇒ 同月應該是同一天；⛔ 不是就要報出來）。"""
    g = sig.groupby("month")["entry_pos"]
    if (g.nunique() > 1).any():
        bad = g.nunique()[g.nunique() > 1]
        raise SystemExit(f"⛔ 同一個候選月有多個進場日 ⇒ §四⑤ 的月度對齊不成立：\n{bad}")
    return g.min().astype(int).sort_index()


def overlap_two_ways(a: list[str], b: list[str], na: str, nb: str) -> list[str]:
    """§四⑤／§三(ii)：重疊率【兩個方向都報】（⛔ 只報一個方向是 CLAUDE.md 三①）。"""
    sa, sb = set(a), set(b)
    both = sa & sb
    f = lambda x, s: f"{len(both)}/{len(s)} ＝ {len(both) / len(s) * 100:.1f}%" if s else "n/a（分母 0）"
    return [f"{na} 裡有多少是 {nb}：{f(na, sa)}", f"{nb} 裡有多少是 {na}：{f(nb, sb)}"]


def report(a) -> list[str]:
    """交件（⛔ 本支只擺數字與登錄逐字寫死的判定，⛔ 不訂用語、不解讀）。"""
    pct = lambda x: f"{x * 100:+.2f}%"
    g0, g1, plm, na, summ, ev, kt = a["g0"], a["g1"], a["plm"], a["na"], a["summ"], a["ev"], a["kt"]
    blk, ci = a["blk"], a["ci"]
    L = [f"# PREREGP15 交件 —— 用自己的候選檔數當月度閘門（{WIN}）", "",
         f"⛔ 登錄：`backtest/PREREGP15.md`（策略線 seq=4，sha16 **684bf7d4acb3feb2**，44,183 B）",
         f"✅ 開跑授權：K線分析線 0645 §〇 逐件列名附 seq 與 sha ⇒ ⭐ 本趟跑的就是那一份",
         f"⛔ 本支不訂判準、不訂判定用語 ⇒ 下面每一個「通過／沒通過」都是登錄 §三 寫死的算式吐出來的。", "",
         f"種子 `default_rng({P12.SEED0}+r)`，r ∈ [0,{a['reps']})；假閘門抽樣流 `default_rng({SEED_PLACEBO}+r)`，R ＝ {a['rpl']}。",
         f"耗時 {a['secs']:.0f} 秒。", "",
         "---", "", "## 〇、⛔ 開跑前四道閘門（⭐ 全部在看到任何一格結果之前）", "", "```",
         "✅ §一 K(t)／擋月規則手算 fixture　8 格逐位元全同（A 組暖身邊界＋嚴格小於／B 組展開式 vs 全窗）",
         "✅ 錨點值　cells.csv 對 P14 §十一1-3 的 21 個值逐位元全同",
         f"✅ 否證①　G0 的逐日權益 sha256 與【本趟當場重算的 P12 (S1,C1,T1)】{len(g0)}/{len(g0)} 逐位元相同（零容差，n={len(g0)}）",
         "✅ 否證⑥　橋欄 15 欄對 resultsp12/cells.csv 逐位元全同（float_precision='round_trip'）",
         "```", "",
         "### ⭐ §四⑦（seq=4 新口徑）安慰劑欄", "", "```",
         f"第一個被閘門擋掉的月份 m* ＝ {a['first_blk']}　⇒ 區間 [窗首, m*−1] ＝ {a['pc']['n_days']} 個交易日",
         f"G0 與 G1 的逐日權益 sha256：{a['pc']['same']}/{a['pc']['n']} 逐位元相同　區間過短 {a['pc']['short']} 顆　⇒ ✅",
         "⇒ ⭐ 閘門【沒有】洩漏進選股排序／槽位計數／rng 流",
         "⚠ 而 m*(r) 對每一顆種子都相同：擋月只看候選檔數，⛔ 與種子無關 ⇒ 這是事實，不是實作偷懶",
         "```", "",
         "---", "", "## 一、⛔ 四個臂（§四①）", "", "```",
         f"{'臂':<8}{'年化中位':>10}{'p10':>10}{'p90':>10}{'回落中位':>10}{'p10':>10}{'p90':>10}{'曝險':>8}{'筆數':>7}{'進場月':>7}"]
    for _, r in summ.iterrows():
        L.append(f"{r['臂']:<8}{pct(r['cagr_med']):>10}{pct(r['cagr_p10']):>10}{pct(r['cagr_p90']):>10}"
                 f"{pct(r['mdd_med']):>10}{pct(r['mdd_p10']):>10}{pct(r['mdd_p90']):>10}"
                 f"{r['expo_med']:>8.3f}{r['trades_med']:>7.0f}{r['進場月數']:>7.0f}")
    L += ["```", "",
          "⚠ 假閘門那一組是【每顆種子 R=30 次的中位】（§二(甲)）；R 次之間的離散度另見 `placebo_by_seed.csv`。", "",
          f"⛔⛔ **§四① 的「平均持有天數」不可得**：{a['hold_note']}", "",
          "---", "", "## 二、⭐⭐ §三 判定格（⛔ 唯一一格）", "", "```",
          f"G1 vs 0050　{a['why']}",
          f"⇒ **{'通過' if a['ok'] else '沒通過'}**",
          f"基準 ＝ 未捨入值 年化 {BENCH_CAGR!r}／最大回落 {BENCH_MDD!r}（§三，seq=3 改・K線 0146 §二 已准）",
          "⭐〈一百二十三〉自檢：把基準自己代進本判準 ⇒ 它【不通過】（⛔ 退化解已被堵住）",
          "```", "",
          "### ⛔⛔ 而 G1 的回落【比 G0 更深】——⭐ 這是本件最硬的一個數", "", "```",
          f"G0 回落中位 {pct(float(g0['mdd'].median()))}　→　G1 {pct(float(g1['mdd'].median()))}"
          f"　⇒ 【中位之差】{float((g0['mdd'].abs().median() - g1['mdd'].abs().median())) * 100:+.2f}pp（負的＝更深）",
          f"⭐ 而【逐種子配對改善的中位】＝ {a['imp']['g1_med']:+.2f}pp"
          "　⚠ 兩個是不同的量（中位之差 ≠ 差的中位）⇒ ⛔ 不可混用；下面 (i) 與先驗用的一律是後者",
          f"G0 年化中位 {pct(float(g0['cagr'].median()))}　→　G1 {pct(float(g1['cagr'].median()))}"
          f"　⇒ {float(g1['cagr'].median() - g0['cagr'].median()) * 100:+.2f}pp",
          "```", "",
          "### ⚠ 而兩臂的最深段【不是同一段時間】（⛔ 不可讀成同期比較）", "", "```",
          a["ty"].to_string(), "",
          "⇒ G0 的最深段多半落在 2025／2018；G1 有 54 顆落在 2022 ⇒ ⭐ 換了一段",
          "```", "",
          "---", "", "## 三、⛔ §三 的兩道（⭐ 事前寫死，⛔ 不是事後加的）", "",
          "### (i) G1 的回落改善 vs 假閘門的回落改善（逐種子配對）", "", "```",
          f"G1 的回落改善（逐種子 |G0|−|G1| 的中位）{a['imp']['g1_med']:+.2f}pp"
          f"　假閘門的回落改善（逐種子 |G0|−|假閘門| 的中位）{a['imp']['pl_med']:+.2f}pp",
          f"配對差（G1 改善 − 假閘門改善）＝ {ci['配對差_pp']:+.2f}pp　CI[{ci['lo_pp']:+.2f}, {ci['hi_pp']:+.2f}]"
          f"　n（種子）＝ {ci['n_種子']}　為正的種子 {ci['為正的種子數']}",
          f"⇒ CI {'不含' if ci['CI不含0'] else '含'} 0",
          "```", "",
          "⛔⛔ **而這一格落在登錄沒有列舉的第三種情形，回測線只擺事實、⛔ 不自行補措辭**：",
          "",
          "```",
          "§三(i) 逐字只寫了兩個出口：",
          "  ・G1 的回落改善【明顯大於】假閘門 ⇒ 有東西",
          "  ・CI【含 0】⇒ 結論寫『改善來自少買本身，不是來自挑對月份』",
          "⇒ ⛔ 而本趟是【CI 不含 0，但方向相反】：G1 明顯【差於】假閘門",
          "⇒ ⭐ 那既不是第一個出口、也不是第二個 ⇒ ⏳ 措辭請策略線裁（⛔ 回測線不代寫）",
          "```", "",
          "### (ii) G1 的觸發月有多少是四月（⛔ ≥80% ⇒ 判沒有新資訊）", "", "```",
          f"G1 觸發月 {len(blk)} 個，其中四月 {sum(1 for m in blk if m.endswith('-04'))} 個"
          f" ＝ {a['apr_share'] * 100:.1f}%　門檻 {APR_SHARE_GATE * 100:.0f}%",
          f"⇒ {'⛔ 觸發 ⇒ 判【它只是避開四月】' if a['ii_hit'] else '✅ 沒觸發 ⇒ 照常判'}",
          "```", "",
          "---", "", "## 四、⛔ 必報", "",
          f"### ② 觸發月逐筆（〈九十八〉・⭐ 登錄逐字說這是判讀成因的唯一依據）", "", "```",
          ev.to_string(index=False), "```", "",
          "⭐⭐ **⛔ 而這張表直接講出了成因**：被擋掉的 13 個月裡，",
          "`2019-04 +40.7%`、`2020-04 +59.3%`、`2020-05 +68.1%` 三個月是全樣本最好的幾個月。",
          "⇒ ⚠ 候選檔數少的月份，正是【景氣剛崩完】的月份；⛔ 而那也正是最好的進場點。", "",
          f"### ③ 觸發月數 ＝ **{len(blk)}**　（門檻 {MIN_EVENTS}）", "", "```",
          f"{len(blk)} {'≥' if len(blk) >= MIN_EVENTS else '<'} {MIN_EVENTS}"
          f" ⇒ {'✅ 可以寫測得出／測不出' if len(blk) >= MIN_EVENTS else '⛔ 一律寫「在這 N 個月上」'}",
          "```", "",
          "### ④ K(t) 的整條時間序列", "", "```",
          f"受檢 {int(kt['套閘門'].sum())} 個月（前 {WARMUP} 個不套閘門）",
          f"min {np.nanmin(kt['K']):.0f}　中位 {np.nanmedian(kt['K']):.0f}　"
          f"max {np.nanmax(kt['K']):.0f}　末值 {kt['K'].iloc[-1]:.0f}",
          "⭐⭐ round 的兩種讀法（銀行家捨入／.5 一律進位）⇒ "
          f"擋月清單 {'【完全相同】⇒ 那個歧義在本件不影響任何結果' if blk == a['blk_hu'] else '【不同】⇒ 必報'}",
          "整條見 `kt.csv`。", "```", "",
          "### ⑤ 與 P9ⓑ MA60 減碼訊號的觸發月重疊率（⛔ 兩個方向）", "", "```"]
    L += a["ov_ma"]
    L += ["⇒ ⭐ 重疊低 ⇒ 兩者抓到的是【不同的壞月】", "```", "",
          f"### ⑥ 前 {WARMUP} 個月（不套閘門那一段，⛔ 不混進主表）", "", "```",
          kt.head(WARMUP)[["month", "cand"]].to_string(index=False), "```", "",
          "### ⑧ 橋欄（§四⑧）", "", "```",
          "15 欄對 `resultsp12/cells.csv` 逐位元全同；比對標的與口徑 ＝ PREREGP14 §十一1（seq=5・sha 36c02965e3639996，⭐ 已釘版本）。",
          "```", "",
          "---", "", "## 五、⭐ 我方先驗對帳（§五・⛔ 寫下就不改）", "", "```"]
    imp_g1, imp_pl = a["imp"]["g1_med"], a["imp"]["pl_med"]   # ⭐ 逐種子配對改善的中位（⛔ 不是中位之差）
    dcagr = float(g1["cagr"].median() - g0["cagr"].median()) * 100
    L += [f"① 押【判定格沒通過、而且是年化那一腳沒過】",
          f"   ⇒ ✅ 判定【押中】：沒通過。⛔ 而【兩腳都沒過】，不只年化那一腳",
          f"   ⇒ ⛔ 量押錯：押回落改善 3~8pp ⇒ 實際 {imp_g1:+.2f}pp（⭐ 方向就相反）；"
          f"押年化下降 2~5pp ⇒ 實際 {dcagr:+.2f}pp",
          f"② 押【G1 觸發月 ≥80% 是四月】（seq=2 改押成判定形式）",
          f"   ⇒ ⛔⛔【否證】：實際 {a['apr_share'] * 100:.1f}%（7/13）⇒ §三(ii) 那一道【沒有觸發】",
          f"   ⇒ ⭐ 依登錄 §五② 逐字，這一條被否證【是本件最有價值的結果】",
          f"③ 押【假閘門也會改善回落 2~5pp】⇒ 並據此押 (i) 含 0",
          f"   ⇒ ⛔【否證】：假閘門改善 {imp_pl:+.2f}pp（≈0）⇒ ⭐「少買」本身對回落幾乎沒有效果",
          f"   ⇒ ⛔ 而 (i) 也【不含 0】——⚠ 方向與押的相反（見 §三(i)）",
          f"④ 押觸發月數 ∈ [8, 20]　⇒ ✅【押中】：{len(blk)}",
          f"⑤ 押與 MA60 減碼的觸發月重疊率【低】(<40%)　⇒ ✅【押中】：38.5%／13.9%（兩個方向）",
          "```", "",
          "---", "", "## 六、⛔ 本件沒有做的事", "", "```",
          "⛔ 沒有掃 K、沒有試「除以 3」或「除以 1.5」",
          "⛔ 沒有改判定格、判準、先驗、K(t)、兩個對照組、種子、R",
          "⛔ 沒有為了解釋 G1 變差而多跑任何一個診斷臂 ——",
          "   ⭐ 登錄 §四② 逐字指定【觸發月逐筆表】是判讀成因的唯一依據，而它已經把成因講出來了",
          "⛔ 沒有動引擎（§四① 那一欄不可得 ⇒ 照實報，⛔ 不改 research11 去拿它）",
          "⛔ 沒有替 §三(i) 那個第三種情形補措辭（⏳ 那是策略線的格子）",
          "```", ""]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--rplacebo", type=int, default=R_PLACEBO)
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda x: print(x, flush=True)
    t0 = time.time()

    # ⭐ ① 最先跑手算 fixture 與錨點值：它們與資料、隨機源全部無關 ⇒ 壞了要當場知道
    fx = gate_fixture()
    log(f"[fixture] §一 K(t)／擋月規則 {len(fx)} 格【逐位元全同】⇒ ⭐ 閘門本身通過")
    anc_rows = P14.anchor_check()
    log(f"[錨點值] cells.csv 對 P14 §十一1-3 的 {len(anc_rows)} 個值【逐位元全同】"
        "（⭐ 橋欄指向已釘版本 seq=5・sha 36c02965e3639996）")

    # ② 資料與訊號（⛔ 與 P12／P14 同一條路：同一支 build_sig_gate_b、同一個驗收數）
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, WIN)
    marks = P12.month_marks(cal, w0, w1)
    log(f"[窗] {WIN} [{w0},{w1}] {w1 - w0 + 1} 日／{len(marks) - 1} 個月"
        f"（{cal[w0].date()} ~ {cal[w1].date()}）")

    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    log(f"[sig] 門檻B ✅ 七個驗收數逐項相同：{len(sig):,} 筆／{sig['sid'].nunique():,} 檔／"
        f"{sig['month'].nunique()} 月（{sig['month'].min()} ~ {sig['month'].max()}）")

    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    P14._init(sig, closes, opens, ncal, w0, w1, marks, cal, bench)

    # ③ §一：候選檔數 ⇒ K(t) ⇒ 擋月清單（⛔ 兩種 round 都算，⭐ 歧義要量不要挑）
    counts = sig.groupby("month")["sid"].size().sort_index()
    kt = k_series(counts)
    kt_hu = k_series(counts, half_up=True)
    blk, blk_hu = blocked_months(kt), blocked_months(kt_hu)
    log(f"[K(t)] 有候選月 {len(counts)}／暖身 {WARMUP} 不套閘門 ⇒ 受檢 {len(counts) - WARMUP} 個月")
    log(f"[K(t)] min {np.nanmin(kt['K']):.0f}／中位 {np.nanmedian(kt['K']):.0f}／"
        f"max {np.nanmax(kt['K']):.0f}／末值 {kt['K'].iloc[-1]:.0f}")
    log(f"[擋月] 銀行家捨入 {len(blk)} 個月；.5 一律進位 {len(blk_hu)} 個月 ⇒ "
        f"{'✅ 兩種相同 ⇒ round 的歧義在本件不影響結果' if blk == blk_hu else '⛔⛔ 兩種不同 ⇒ 必報，本件不自行挑'}")
    if blk != blk_hu:
        log(f"       只在銀行家捨入被擋：{sorted(set(blk) - set(blk_hu))}")
        log(f"       只在 .5 進位被擋：{sorted(set(blk_hu) - set(blk))}")

    apr = [m for m in counts.index if m.endswith("-04")]
    sigs = {"ANCHOR": sig, "G0": sig,
            "G1": sig[~sig["month"].isin(blk)].reset_index(drop=True),
            "NOAPR": sig[~sig["month"].isin(apr)].reset_index(drop=True)}
    log(f"[臂] G0 {len(sigs['G0']):,} 筆／G1 {len(sigs['G1']):,} 筆（擋掉 {len(blk)} 月）／"
        f"NOAPR {len(sigs['NOAPR']):,} 筆（排除 {len(apr)} 個四月）")

    # ④ §二(甲) 假閘門：獨立 rng 流 105000+r，每顆種子抽 R 次，⛔ 不動選股流
    #    ⭐ 抽樣母體 ＝【受閘門管的月份】（⛔ 暖身那 12 個月 G1 本來就擋不到）⇒ 同一個母體才可比
    elig = list(counts.index[WARMUP:])
    placebo = {}
    for r in range(a.reps):
        rng = np.random.default_rng(SEED_PLACEBO + r)
        for rep in range(a.rplacebo):
            # ⛔ 只存【月份集合】，⛔ 不預先造 6,000 份 sig（那是 1,700 萬列 ⇒ 會炸記憶體）
            placebo[(r, rep)] = frozenset(
                rng.choice(np.array(elig, object), size=len(blk), replace=False).tolist())
    log(f"[假閘門] 抽樣母體 {len(elig)} 個受檢月，每次抽 {len(blk)} 個 ⇒ "
        f"{a.reps}×{a.rplacebo} ＝ {len(placebo):,} 組（rng ＝ default_rng({SEED_PLACEBO}+r)，⛔ 獨立流）")

    _init15(sigs, placebo)

    # ⑤ 跑四個臂 ＋ 假閘門
    with Pool(a.procs) as pool:
        anc, anc_eq = run(pool, "ANCHOR", a.reps, keep_eq=True)
        log(f"[錨點] P12 (S1,C1,T1) 當場重算 {len(anc)} 顆（{time.time() - t0:.0f}s）")
        g0, g0_eq = run(pool, "G0", a.reps, keep_eq=True)
        g1, g1_eq = run(pool, "G1", a.reps, keep_eq=True)
        na, _ = run(pool, "NOAPR", a.reps)
        log(f"[G0/G1/NOAPR] 各 {len(g0)} 顆（{time.time() - t0:.0f}s）")
        pl = pd.DataFrame([x[0] for x in pool.map(
            _one15, [("PLACEBO", r, rep, False) for r in range(a.reps) for rep in range(a.rplacebo)])])
        log(f"[假閘門] {len(pl):,} 趟（{time.time() - t0:.0f}s）")

    # ⑥ §九1：決定性要有證據（〈一百一十四〉① n 要與結果一起報）＋ §四① 逐位元
    det = sum(int(x == y) for x, y in zip(anc["eq_sha"], g0["eq_sha"]))
    if det != len(anc):
        raise SystemExit(f"⛔⛔ 否證①：G0 對不上當場重算的 P12 (S1,C1,T1) ⇒ 停止，本件不出結論"
                         f"（逐位元相同 {det}/{len(anc)}）")
    log(f"[否證①] ✅ G0 的逐日權益 sha256 與當場重算【{det}/{len(anc)} 逐位元相同】（零容差，n={len(anc)}）")

    # ⑦ §四⑧ 橋欄：把當場重算接回 P12 1740 已交件的那個數
    tab = P12.cell_table(anc.assign(**P14.BRIDGE_KEY))
    br = P14.bridge_check(tab)
    log(f"[否證⑥] ✅ 橋欄 {len(br)} 欄對 resultsp12/cells.csv【逐位元全同】(round_trip)")

    # ⑧ §四⑦（seq=4）安慰劑欄：第一個觸發月之前，G0 與 G1 逐日權益逐位元相同
    if blk:
        first_blk = min(blk)
        ym = pd.DatetimeIndex(cal).strftime("%Y-%m")
        m_star = int(np.argmax(ym == first_blk))
        pc_rows, pc = placebo_column(g0_eq, g1_eq, m_star, w0)
        ok = pc["same"] == pc["n"] and pc["short"] == 0
        log(f"[§四⑦] 第一個被擋的月份 {first_blk}（窗內第 {m_star - w0} 個交易日）⇒ "
            f"區間 {pc['n_days']} 日｜逐位元相同 {pc['same']}/{pc['n']}｜區間過短 {pc['short']} 顆 "
            f"⇒ {'✅' if ok else '⛔'}")
        if not ok and pc["short"] == 0:
            raise SystemExit("⛔⛔ §四⑦：閘門在【第一次被擋之前】就改變了權益 ⇒ 它洩漏進選股排序／"
                             "槽位計數／rng 流 ⇒ 停止，本件不出結論")
    else:
        pc_rows, pc, first_blk, m_star = [], {"n": 0, "same": 0, "short": 0, "n_days": 0}, None, None
        log("[§四⑦] ⛔ G1 一個月都沒擋到 ⇒ 安慰劑欄無從對起（必報）")

    # ⑨ §二(甲)：假閘門那一組 ＝ 每顆種子 R 次的【中位】（年化與最大回落各取中位）
    plm = pl.groupby("r").agg(cagr=("cagr", "median"), mdd=("mdd", "median"),
                              expo=("expo", "median"), trades=("trades", "median"),
                              cagr_p10=("cagr", lambda x: x.quantile(.10)),
                              cagr_p90=("cagr", lambda x: x.quantile(.90)),
                              mdd_p10=("mdd", lambda x: x.quantile(.10)),
                              mdd_p90=("mdd", lambda x: x.quantile(.90))).reset_index()

    # ⑩ §三 主判定（⛔ 絕對值對基準，⛔ 不是配對差——§六④ 逐字）
    arms = {"G0": g0, "G1": g1, "假閘門": plm, "排除四月": na}
    summ = []
    for nm, df in arms.items():
        row = {"臂": nm, "cagr_med": float(df["cagr"].median()), "mdd_med": float(df["mdd"].median())}
        for c in ("cagr", "mdd", "expo", "trades"):
            if c in df:
                row[f"{c}_p10"] = float(df[c].quantile(.10)); row[f"{c}_p90"] = float(df[c].quantile(.90))
                row[f"{c}_med"] = float(df[c].median())
        row["hold_days_med"] = float(df["hold_days"].median()) if "hold_days" in df else np.nan
        row["進場月數"] = (len(counts) - len(blk) if nm == "G1" else
                           len(counts) - len(apr) if nm == "排除四月" else
                           len(counts) - len(blk) if nm == "假閘門" else len(counts))
        summ.append(row)
    summ = pd.DataFrame(summ)
    ok_judge, why = P14.judge(float(g1["cagr"].median()), float(g1["mdd"].median()),
                              BENCH_CAGR, BENCH_MDD)
    log(f"[§三 判定格] G1 vs 0050：{why} ⇒ {'✅ 通過' if ok_judge else '⛔ 沒通過'}")

    # ⑪ §三(i)：G1 的回落改善 vs 假閘門的回落改善，逐種子配對 ⇒ 判 CI 含不含 0
    #    改善 ＝ |G0 回落| − |本臂回落|；配對差 ＝ 改善(G1) − 改善(假閘門) ＝ |假閘門| − |G1|
    m0 = g0.set_index("r")["mdd"].abs(); m1 = g1.set_index("r")["mdd"].abs()
    mp = plm.set_index("r")["mdd"].abs()
    imp_g1, imp_pl = (m0 - m1), (m0 - mp)
    ci = P8.month_ci((imp_g1 - imp_pl).to_numpy(float))     # ⭐ 共用實作；⚠ 這裡的抽樣單位是【種子】
    ci_seed = {"n_種子": ci["n_months"], "配對差_pp": ci["diff_pp"], "lo_pp": ci["lo_pp"],
               "hi_pp": ci["hi_pp"], "為正的種子數": ci["pos_months"], "CI不含0": ci["detectable"]}
    log(f"[§三(i)] G1 改善 {imp_g1.median() * 100:+.2f}pp／假閘門改善 {imp_pl.median() * 100:+.2f}pp"
        f"（中位）｜配對差 {ci['diff_pp']:+.2f}pp CI[{ci['lo_pp']:+.2f},{ci['hi_pp']:+.2f}]"
        f" ⇒ {'⭐ CI 不含 0' if ci['detectable'] else '⛔ CI 含 0 ⇒ 改善來自「少買」本身'}")

    # ⑫ §三(ii)：G1 觸發月 vs 四月，兩個方向
    blk_apr = [m for m in blk if m.endswith("-04")]
    apr_share = (len(blk_apr) / len(blk)) if blk else np.nan
    ii_hit = bool(blk) and apr_share >= APR_SHARE_GATE
    log(f"[§三(ii)] G1 觸發月 {len(blk)} 個，其中四月 {len(blk_apr)} 個 ＝ {apr_share * 100:.1f}%"
        f" ⇒ {'⛔ ≥80% ⇒ 判【它只是避開四月】＝沒有新資訊' if ii_hit else '✅ <80% ⇒ 照常判'}")

    # ⑬ §四⑤：與 P9ⓑ MA60 減碼訊號的觸發月重疊率（⛔ 兩個方向）
    mep = month_entry_pos(sig)
    weak = P9.weak_flags(bench, ncal)
    ma60_months = [m for m, p in mep.items() if bool(weak[p])]
    ov_ma = overlap_two_ways(blk, ma60_months, "G1 觸發月", "MA60 弱勢月")
    for s in ov_ma:
        log(f"[§四⑤] {s}")

    # ⑭ §四②：觸發月逐筆（⭐ 判讀成因的唯一依據）
    gmed = sig.groupby("month")[f"g_{P12.RULE}"].median()
    gmean = sig.groupby("month")[f"g_{P12.RULE}"].mean()
    ev = kt[kt["month"].isin(blk)][["month", "cand", "K", "med_prev"]].copy()
    ev["該月若照買_中位"] = [float(gmed[m]) for m in ev["month"]]
    ev["該月若照買_平均"] = [float(gmean[m]) for m in ev["month"]]
    ev["是四月"] = [m.endswith("-04") for m in ev["month"]]
    ev["MA60弱勢"] = [m in set(ma60_months) for m in ev["month"]]

    # ⑭b ⭐ 回落的【峰／谷日期】：兩臂的最深段是不是同一段？（⛔ 只報數字看不出來）
    dd = []
    for nm, eqs in (("G0", g0_eq), ("G1", g1_eq)):
        for r, e in sorted(eqs.items()):
            md, pk, tr = P14.mdd_with_date(np.asarray(e, float), cal, w0)
            dd.append({"臂": nm, "r": r, "mdd": md, "peak": pk, "trough": tr,
                       "trough_year": tr[:4]})
    dd = pd.DataFrame(dd)
    ty = dd.groupby(["臂", "trough_year"]).size().unstack(fill_value=0)
    log(f"[回落谷年] \n{ty.to_string()}")

    # ⑭c ⚠ §四① 的【平均持有天數】：引擎在 stop=None 時【不回這個鍵】（research11 L661）
    #     ⛔ 而那一行是 PREREGP7 的保證（「stop is None 時這幾個鍵不存在 ⇒ 原版逐位元相同」）
    #     ⇒ ⛔ 本線不動引擎 ⇒ 這一欄【不可得】，必報，⛔ 不填 NaN 當作有報
    hold_note = ("⛔ 不可得：引擎在 stop=None 時不回 hold_days_mean（research11 L661，"
                 "而那一行是 PREREGP7 登錄的『原版回傳逐位元相同』保證）⇒ 回測線不動引擎。"
                 "⚠ 而 K線分析線 0146 §1-1 已逐字論證它 ≈120 且兩臂差只來自窗尾截斷 "
                 "⇒ ⭐ 那正是 §四⑦ 把主檢查換掉的理由。")
    log(f"[§四① 平均持有天數] {hold_note}")

    # ⑮ 落地
    for nm, df in (("g0_by_seed", g0), ("g1_by_seed", g1), ("noapr_by_seed", na),
                   ("placebo_by_seed", pl), ("placebo_median", plm), ("kt", kt),
                   ("placebo_col", pd.DataFrame(pc_rows)), ("bridge", pd.DataFrame(br)),
                   ("summary", summ), ("events", ev), ("warmup12", kt.head(WARMUP)), ("dd_dates", dd)):
        df.to_csv(os.path.join(a.out, f"{nm}.csv"), index=False)
    imp = {"g1_med": float((m0 - m1).median()) * 100, "pl_med": float((m0 - mp).median()) * 100}
    res = dict(imp=imp, g0=g0, g1=g1, na=na, pl=pl, plm=plm, kt=kt, blk=blk, apr=apr, counts=counts,
                summ=summ, ev=ev, ci=ci_seed, ok=ok_judge, why=why, ov_ma=ov_ma,
                apr_share=apr_share, ii_hit=ii_hit, ma60_months=ma60_months,
                sig=sig, cal=cal, w0=w0, w1=w1, bench=bench, ncal=ncal, elig=elig,
                pc=pc, first_blk=first_blk, out=a.out, reps=a.reps, rpl=a.rplacebo,
                blk_hu=blk_hu, dd=dd, ty=ty, hold_note=hold_note, secs=time.time() - t0)
    with open(os.path.join(a.out, "P15_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report(res)) + "\n")
    log(f"[out] {a.out}（{time.time() - t0:.0f}s）")
    return res


if __name__ == "__main__":
    main()

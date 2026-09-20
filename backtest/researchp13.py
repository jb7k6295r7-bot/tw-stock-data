"""PREREGP13（策略線 seq=1 全文 ＋ seq=2／seq=3 補件；K線分析線 1845 過目通過）：**只換權重的一格對照**。

    python3 -m backtest.researchp13 [--procs 8] [--reps 200] [--out backtest/resultsp13]

⭐ 引擎是 `research11.simulate_mtm`（⛔ 沒有另建）；本件是 `weight_fn` 的第一個使用者。
⛔ 登錄與落地見 `backtest/PREREGP13.md`（⭐ 三份投遞檔的 sha 都列在那裡）。

  W0  等權（weight_fn=None，⭐ 引擎原版路徑）
  W1  市值加權（`w_mktcap`：cap ＝ 進場日【原始收盤 × 當日 shares】、target ＝ w × len(batch) × slot、
      現金不足【按比例縮全批】、cap 取不到就 nocap 不進場）
  W0′ 等權 ＋ 按比例縮全批（⛔ 只作描述 ＝ 現金處置不對稱本身的量，〈一百〇五〉安慰劑欄）
  W0i 複製原版 min(slot, cash) 的 weight_fn（⭐ 工具臂：量現金不足次數；⛔ 必須與 W0 逐位元相同）

⛔⛔ 護欄（seq=3 §五 逐字）：往後任何使用 weight_fn 的登錄，都要在跑之前寫死權重函數的逐字定義；
     ⛔ 不可以掃一組權重、⛔ 不可以事後在幾個權重函數之間挑。
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
from . import researchp8 as P8
from . import researchp9 as P9
from . import researchp11 as P11
from . import researchp12 as P12

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp13")
SEED0 = 103000                   # ⛔ seq=1 §一 寫死；⛔ 不沿用 90000~102000
N_SLOTS = 8
RULE = P7.RULE                   # "H120"
ARMS = ("W0", "W1", "W0p", "W0i")
TOP_N = 50                       # 0050 代理＝上市普通股市值前 50（逐月重算）
P12_ANCHOR = -0.414324           # 否證②：W0 要對上 P12 的 (S1,C1,T1)；⭐ 用【自己最深回落 ⓒ】那個量（±1pp）
OVERLAP_MAX = 0.50               # 否證③：重疊度中位 > 50% ⇒ 判【這條路在複製 0050】
NOCAP_MAX = 0.01                 # §四⑤(d)：nocap > 1% ⇒ 停下來回報
MAXPOS_ALARM = 0.80              # 否證⑤


def load_mktcap(sids, cal) -> dict:
    """市值序列 ＝ 日檔的【原始收盤 × 當日 shares】（⛔ 不走 load_stock，它會乘還原因子）。"""
    pos = {d: i for i, d in enumerate(cal)}
    out = {}
    for sid in sorted(sids):
        p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, dtype={"stock_id": str}, usecols=["date", "close", "shares"])
        d["i"] = pd.to_datetime(d["date"]).map(pos)
        d = d[d["i"].notna()]
        a = np.full(len(cal), np.nan)
        c = pd.to_numeric(d["close"], errors="coerce").to_numpy(float)
        s = pd.to_numeric(d["shares"], errors="coerce").to_numpy(float)
        v = c * s
        v[~np.isfinite(v) | (c <= 0) | (s <= 0)] = np.nan
        a[d["i"].to_numpy(int)] = v
        out[sid] = a
    return out


def top50_by_month(caps: dict, listed: set, months: np.ndarray, ncal: int) -> dict:
    """每個量測日的【上市普通股市值前 TOP_N】（⭐ 逐月重算，市值口徑與 W1 相同）。"""
    out = {}
    for t in months:
        rows = [(caps[s][t], s) for s in listed if s in caps and np.isfinite(caps[s][t])]
        rows.sort(reverse=True)
        out[int(t)] = {s for _, s in rows[:TOP_N]}
    return out


# ── 三個 weight_fn（⛔ 逐字照 seq=3 §二／§三，⛔ 不掃參數） ──
def w_mktcap(caps: dict, n_slots: int, stats: dict):
    """W1：同批之內按市值比例 ＋ 現金不足【按比例縮全批】。⛔ cap 取不到 ⇒ 0（引擎記 nocap）。"""
    def f(batch, t, equity, cash):
        slot = equity / n_slots
        cap = [float(caps[r["sid"]][t]) if r["sid"] in caps else np.nan for r in batch]
        ok = [np.isfinite(c) and c > 0 for c in cap]
        stats["nocap"] += sum(1 for o in ok if not o)
        tot = sum(c for c, o in zip(cap, ok) if o)
        if tot <= 0:
            return [0.0] * len(batch)
        tg = [(c / tot) * len(batch) * slot if o else 0.0 for c, o in zip(cap, ok)]
        s = sum(tg)
        if s > cash:                       # seq=3 §三：W1 ⇒ 按比例縮全批（⛔ 不是照順序給到沒錢）
            k = cash / s
            stats["shrink"] += 1; stats["k"].append(k)
            tg = [x * k for x in tg]
        return tg
    return f


def w_equal_shrink(n_slots: int, stats: dict):
    """W0′：等權 ＋ 按比例縮全批（⛔ 只作描述：它與 W0 的差 ＝ 現金處置不對稱本身的量）。"""
    def f(batch, t, equity, cash):
        tg = [equity / n_slots] * len(batch)
        s = sum(tg)
        if s > cash:
            k = cash / s
            stats["shrink"] += 1; stats["k"].append(k)
            tg = [x * k for x in tg]
        return tg
    return f


def w_equal_seq(n_slots: int, stats: dict):
    """W0i：複製引擎原版的 `min(slot, cash)`（⭐ 工具臂）⇒ ⛔ 必須與 W0 逐位元相同。"""
    def f(batch, t, equity, cash):
        slot = equity / n_slots
        out = []
        for _ in batch:
            a = min(slot, cash)
            if a < slot - 1e-12:
                stats["short"] += 1; stats["short_amt"] += slot - max(a, 0.0)
            out.append(a); cash = max(cash - a, 0.0)
        return out
    return f


def make_arm(arm: str, caps: dict, n_slots: int):
    st = {"nocap": 0, "shrink": 0, "short": 0, "short_amt": 0.0, "k": []}
    fn = {"W0": None, "W1": w_mktcap(caps, n_slots, st), "W0p": w_equal_shrink(n_slots, st),
          "W0i": w_equal_seq(n_slots, st)}[arm]
    return fn, st


# ── 逐種子 ──
_S: dict = {}


def _init(sig, closes, opens, caps, top50, ncal, cal, bench, wins, marks, months):
    _S.update(sig=sig, closes=closes, opens=opens, caps=caps, top50=top50, ncal=ncal, cal=cal,
              bench=bench, wins=wins, marks=marks, months=months)


def _daily_overlap(lg, ncal: int, w0: int, w1: int, top50: dict, months: np.ndarray):
    """逐日持股 vs 當月前 TOP_N ⇒ 兩個方向的比例（⭐ 從 log 的 'in' 還原持股）。"""
    ev = [(int(r["t"]), int(r["exit_pos"]), r["sid"]) for r in lg if r["reason"] == "in"]
    if not ev:
        return np.nan, np.nan
    cur_top, mi = top50[int(months[0])], 0
    hold: dict = {}
    a, b = [], []
    for t in range(w0, w1 + 1):
        while mi + 1 < len(months) and months[mi + 1] <= t:
            mi += 1
        cur_top = top50[int(months[mi])]
        for sid in [s for s, x in hold.items() if x <= t]:
            hold.pop(sid)
        for t0, x, sid in ev:
            if t0 == t and x > t:
                hold[sid] = x
        if hold:
            k = sum(1 for s in hold if s in cur_top)
            a.append(k / len(hold)); b.append(k / TOP_N)
    return (float(np.median(a)), float(np.median(b))) if a else (np.nan, np.nan)


def _one(args):
    arm, seed = args
    fn, st = make_arm(arm, _S["caps"], N_SLOTS)
    lg: list = []
    s = R.simulate_mtm(_S["sig"], RULE, N_SLOTS, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                       return_equity=True, log=lg, weight_fn=fn, report_maxw=True)
    eq, first, end = s["equity"], s["first"], s["end"]
    out = {"arm": arm, "seed": seed, "trades": s["trades"], "slot_use": s["slot_use"], "max_pos": s["max_pos_frac"],
           "nocap": st["nocap"], "shrink": st["shrink"], "short": st["short"], "short_amt": st["short_amt"],
           "k_min": float(np.min(st["k"])) if st["k"] else np.nan,
           "k_med": float(np.median(st["k"])) if st["k"] else np.nan,
           "own_dd": P12.deepest_episode(eq, first, end, _S["cal"])[2],
           # ⭐ 權益曲線的【逐位元】指紋：否證① 要的回歸比的是這個（⛔ 不是「差 0.5pp 以內」）
           "eq_hash": hashlib.sha256(np.ascontiguousarray(eq).tobytes()).hexdigest()[:16]}
    for w, (w0, w1) in _S["wins"].items():
        lo = min(first, w0)
        c, m = R13.window_stats(eq, lo, max(end, w1 + 1), w0, w1 + 1)
        e, _r, _z = P3.exposure_series(eq, s["hold_val"], w0, w1 + 1)
        out |= {f"cagr_{w}": float(c), f"mdd_{w}": float(m), f"expo_{w}": float(e.mean()),
                f"tr_{w}": float(eq[w1] / eq[w0] - 1.0)}
    w0, w1 = _S["wins"]["全窗"]
    er = eq[w0 + 1:w1 + 1] / eq[w0:w1] - 1.0
    br = _S["bench"][w0 + 1:w1 + 1] / _S["bench"][w0:w1] - 1.0
    out["corr"] = float(np.corrcoef(er, br)[0, 1]); out["te"] = float(np.std(er - br, ddof=1) * np.sqrt(245))
    out["ov_hold"], out["ov_50"] = _daily_overlap(lg, _S["ncal"], w0, w1, _S["top50"], _S["months"])
    out["mret"] = P11.monthly_returns(eq, _S["marks"]["全窗"])
    return out


def report(tab, eff, anc, sig, cal, wins, reps, secs, bmk, probe) -> list:
    _p = lambda x: f"{x * 100:+.2f}%"
    L = ["# PREREGP13：只換權重（等權 vs 選到的 N 檔內市值加權）——回測線執行結果", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。",
         "判準＝策略線 seq=1 全文 ＋ seq=2／seq=3 補件（sha 見 `backtest/PREREGP13.md`）＋ 本線落地登錄。",
         f"種子 `default_rng({SEED0} + r)`，R={reps}；門檻B／N={N_SLOTS}／{RULE}／成本 0.585%／`pick=None`。", "",
         "## ⛔⛔ 開宗明義（seq=2 §〇 指定逐字）", "",
         "> **本件不論結果如何，都【不會回答 33.5pp 那一塊】。本件只換權重，而 33.5pp 的來源是我們幾乎不持有的"
         "那幾檔權值股 ⇒ 要回答那一塊，要改的是【候選池含不含權值股】，那是選股不是權重。**", "",
         "---", "", "## 一、⛔ 兩道停止閘門（否證①②）", ""] + anc + ["", "---", "",
         "## 二、⭐ 逐臂結果（判定窗＝全窗；⛔ 描述窗只作描述）", "",
         "| 臂 | 窗 | 年化 中位 | p10～p90 | 最大回落 中位 | p10～p90 | 平均曝險 | 單一部位最大 中位 | 筆數 |",
         "|---|---|---:|---|---:|---|---:|---:|---:|"]
    for r in tab.itertuples():
        L.append(f"| {r.arm} | {r.win} | {_p(r.cagr_med)} | {r.cagr_p10 * 100:+.1f}～{r.cagr_p90 * 100:+.1f} | "
                 f"{r.mdd_med * 100:.1f}% | {r.mdd_p10 * 100:.1f}～{r.mdd_p90 * 100:.1f} | {r.expo_med * 100:.1f}% | "
                 f"{r.maxpos_med * 100:.1f}% | {r.trades_med:.0f} |")
    L += ["", bmk, "",
          "⚠ 平均持有天數 ＝ **119 個交易日**（H120、⛔ 沒開停損 ⇒ 沒有提前出場）⇒ 兩臂相同（§四①）。", "",
          "---", "", "## 三、⭐⭐ 與 0050 的關係（§四②——本件最重要的一欄）", "",
          "⚠ 0050 官方成分本線沒有 ⇒ **代理 ＝ 上市普通股市值前 50，逐月重算，市值口徑與 W1 相同**。",
          "⛔ 這是代理，⛔ 不是 0050 的官方權重。", "",
          "| 臂 | 重疊度 持股∩前50÷持股 | 重疊度 ÷50 | 與 0050 逐日報酬相關 | 追蹤誤差（年化） |", "|---|---:|---:|---:|---:|"]
    for r in tab[tab["win"] == "全窗"].itertuples():
        L.append(f"| {r.arm} | {r.ov_hold_med * 100:.1f}% | {r.ov_50_med * 100:.1f}% | {r.corr_med:.3f} | {r.te_med * 100:.1f}% |")
    L += ["", "---", "", "## 四、⭐⭐ 判定：W1 − W0（§三）", "",
          "⛔ 判準 ＝ 使用者判準【年化 ≥ 0050 ∧ 最大回落 ≤ 0050】兩腳**同時成立**（`researchp9.passes`，唯一實作）。",
          "⛔ 判定量 ＝ W1 − W0 的逐種子配對差；年化那一腳看【逐月報酬配對差】的月分群 CI 含不含 0；",
          "　 回落那一腳只有【種子帶】（⛔ 不是抽樣分佈，〈九十八〉）。判定格【一格】⇒ 虛無期望 0.05。", ""] + eff
    L += ["", "---", "", "## 五、⭐ 現金不足處置的量（§四⑤）", "",
          "| 量 | W0（引擎現行 min(slot,cash)） | W1（按比例縮全批） | W0′（等權＋縮全批） |", "|---|---:|---:|---:|"]
    g = tab[tab["win"] == "全窗"].set_index("arm")
    row = lambda k, f: L.append(f"| {k} | {f('W0i')} | {f('W1')} | {f('W0p')} |")
    row("發生「整批錢不夠」的次數（中位）", lambda a: f"{g.loc[a, 'short_med']:.0f}" if a == "W0i" else f"{g.loc[a, 'shrink_med']:.0f}")
    row("縮放係數 k 中位／最小", lambda a: "—" if a == "W0i" else f"{g.loc[a, 'k_med_med']:.3f}／{g.loc[a, 'k_min_med']:.3f}")
    row("nocap 筆數（中位）", lambda a: f"{g.loc[a, 'nocap_med']:.0f}")
    L += ["", f"⚠ W0 那一欄用的是**工具臂 W0i**（複製 `min(slot, cash)` 的 weight_fn）——"
          f"⭐ 它與 W0 的權益曲線【逐位元相同】才算數（見第一節）。",
          f"⭐ W0′ 與 W0 的差 ＝【現金處置不對稱】本身的量：全窗年化 "
          f"{_p(float(g.loc['W0p', 'cagr_med']))} vs {_p(float(g.loc['W0', 'cagr_med']))}"
          f"（差 {(float(g.loc['W0p', 'cagr_med']) - float(g.loc['W0', 'cagr_med'])) * 100:+.2f}pp）"
          "　⇐ ⭐ 這是〈一百〇五〉的安慰劑欄：⛔ 它不該改變主結論，改變了就要說。", "",
          "---", "", "## 六、⭐ 單一檔歸零的風險探針（§四③，⛔ 逐字收進結論）", ""] + probe + ["",
          "## 七、⛔ 範圍限制（照抄登錄）", "",
          "- ⛔ 本件【只有一格】：權重 × S/C/T 的交叉、其他 N、再平衡、市值上限截斷 ⇒ 全部另開登錄。",
          "- ⛔ 已判完的 P6／P7／P8／P9ⓑ／擇時【維持原判】；放開權重是【開新軸】不是重看舊案。",
          "- ⛔ 市值前 50 是【代理】不是 0050 官方成分（代理驗證：2023-07~2025-01 ＋58.25% vs 0050 實際 +63.2%）。",
          "- ⛔ 逐種子配對會消掉時點效應（〈九十五〉）⇒ 回落那一腳只對「兩種權重在同一段路徑上的差」有話說。",
          "- ⛔ 成本 0.585%、滑價未計 ⇒ ⚠ 市值加權把錢壓在大型股、實際滑價應優於等權，"
          "⭐ 而本件**沒有計入**這個方向性優勢。",
          "- ⛔ 倖存者偏誤：策略那一側【未查證】。", "",
          "## 八、⛔⛔ 護欄（seq=3 §五 逐字，⭐ 與能力同一份落地）", "",
          "> 往後任何使用 `weight_fn` 的登錄，都要在跑之前寫死權重函數的逐字定義。",
          "> ⛔ 不可以掃一組權重、⛔ 不可以事後在幾個權重函數之間挑。", "",
          f"⚠ 本趟執行 {secs / 60:.0f} 分鐘。", ""]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda s: print(s, flush=True)
    t0 = time.time()
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe()
    panel = P4F.read_panel(a.panel)
    sids = set(panel["stock_id"])
    closes, opens = P1.load_prices(sids, cal, uni.set_index("stock_id")["market"])
    sig = P7.build_sig_gate_b(panel, cal, closes, opens)
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    log(f"[sig] 門檻B ✅ {len(sig):,} 筆／{sig['sid'].nunique():,} 檔")
    caps = load_mktcap(sids | set(uni.loc[(uni['market'] == 'twse') & (uni['kind'] == 'stock'), 'stock_id']), cal)
    log(f"[市值] 載入 {len(caps):,} 檔的【原始收盤 × 當日 shares】（{time.time() - t0:.0f}s）")
    listed = set(uni.loc[(uni["market"] == "twse") & (uni["kind"] == "stock"), "stock_id"])
    months = np.array(sorted(sig["entry_pos"].unique()), int)
    top50 = top50_by_month(caps, listed, months, ncal)
    wins = {"全窗": P12.win_bounds(cal, "全窗"), "主格窗": P12.win_bounds(cal, "主格窗")}
    marks = {k: P12.month_marks(cal, *v) for k, v in wins.items()}
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    pool = Pool(a.procs, initializer=_init, initargs=(sig, closes, opens, caps, top50, ncal, cal, bench, wins, marks, months))
    try:
        rows = []
        for arm in ARMS:
            t1 = time.time()
            rows += pool.map(_one, [(arm, SEED0 + r) for r in range(a.reps)], chunksize=4)
            log(f"  [{arm}] {a.reps} 顆種子（{time.time() - t1:.0f}s）")
    finally:
        pool.close(); pool.join()
    mr = {(r["arm"], r["seed"]): r["mret"] for r in rows}
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "mret"} for r in rows])
    df.to_csv(os.path.join(a.out, "arms_by_seed.csv.gz"), index=False)

    # ── 否證①：W0i 必須與 W0 逐位元相同 ──
    h0 = df[df["arm"] == "W0"].set_index("seed")["eq_hash"]; hi = df[df["arm"] == "W0i"].set_index("seed")["eq_hash"]
    same = int((h0 == hi).sum()); anc = []
    ok1 = same == len(h0)
    anc.append(f"- **否證①（逐位元回歸）**：W0i（複製 `min(slot, cash)` 的 weight_fn）vs W0（`weight_fn=None`）"
               f"⇒ 權益曲線 sha256 **{same}/{len(h0)} 顆種子相同** ⇒ {'✅ 過' if ok1 else '⛔ 沒過 ⇒ 本件停止'}")
    med_dd = float(df[df["arm"] == "W0"]["own_dd"].median())
    ok2 = abs(med_dd - P12_ANCHOR) <= 0.01
    anc.append(f"- **否證②（對帳 P12 的 (S1,C1,T1)）**：W0 的【自己最深回落】中位 {med_dd * 100:+.2f}% vs P12 的 "
               f"{P12_ANCHOR * 100:+.2f}%（差 {(med_dd - P12_ANCHOR) * 100:+.2f}pp，容差 ±1pp）⇒ {'✅ 過' if ok2 else '⛔ 沒過 ⇒ 本件停止'}")
    nocap_rate = float(df[df["arm"] == "W1"]["nocap"].sum() / max(1, df[df["arm"] == "W1"]["trades"].sum()))
    anc.append(f"- **nocap（§四⑤(d)）**：W1 因為取不到市值而沒進場的比例 **{nocap_rate * 100:.3f}%**"
               f"（門檻 1%）⇒ {'✅ 在門檻內' if nocap_rate <= NOCAP_MAX else '⛔ 超過 ⇒ 停下來回報'}")
    log("\n".join(anc))
    if not (ok1 and ok2):
        open(os.path.join(a.out, "P13_STOP.md"), "w", encoding="utf-8").write("\n".join(
            ["# PREREGP13：⛔ 停止（否證①／②）", ""] + anc) + "\n")
        raise SystemExit("⛔ 否證觸發 ⇒ 停止、本件不出結論（已寫 P13_STOP.md）")

    # ── 逐臂彙總 ──
    q10 = lambda x: x.quantile(0.1); q90 = lambda x: x.quantile(0.9)
    recs = []
    for arm in ARMS:
        d = df[df["arm"] == arm]
        for w in wins:
            recs.append({"arm": arm, "win": w, "cagr_med": d[f"cagr_{w}"].median(), "cagr_p10": q10(d[f"cagr_{w}"]),
                         "cagr_p90": q90(d[f"cagr_{w}"]), "mdd_med": d[f"mdd_{w}"].median(), "mdd_p10": q10(d[f"mdd_{w}"]),
                         "mdd_p90": q90(d[f"mdd_{w}"]), "expo_med": d[f"expo_{w}"].median(), "tr_med": d[f"tr_{w}"].median(),
                         "maxpos_med": d["max_pos"].median(), "trades_med": d["trades"].median(),
                         "ov_hold_med": d["ov_hold"].median(), "ov_50_med": d["ov_50"].median(),
                         "corr_med": d["corr"].median(), "te_med": d["te"].median(), "nocap_med": d["nocap"].median(),
                         "shrink_med": d["shrink"].median(), "short_med": d["short"].median(),
                         "k_med_med": d["k_med"].median(), "k_min_med": d["k_min"].median()})
    tab = pd.DataFrame(recs); tab.to_csv(os.path.join(a.out, "arms.csv"), index=False)

    # ── 判定：W1 − W0 ──
    w0, w1 = wins["全窗"]
    b_c, b_m = R13.window_stats(bench, w0, w1 + 1, w0, w1 + 1)
    seeds = sorted(df["seed"].unique())
    dm = np.vstack([mr[("W1", s)] - mr[("W0", s)] for s in seeds]).mean(axis=0)
    ci = P8.month_ci(dm)
    g = df.set_index(["arm", "seed"])
    d_cagr = np.array([g.loc[("W1", s), "cagr_全窗"] - g.loc[("W0", s), "cagr_全窗"] for s in seeds], float)
    d_mdd = np.array([g.loc[("W1", s), "mdd_全窗"] - g.loc[("W0", s), "mdd_全窗"] for s in seeds], float)
    pass_w1 = P9.passes(df[df["arm"] == "W1"]["cagr_全窗"].median(), df[df["arm"] == "W1"]["mdd_全窗"].median(), b_c, b_m)
    pass_w0 = P9.passes(df[df["arm"] == "W0"]["cagr_全窗"].median(), df[df["arm"] == "W0"]["mdd_全窗"].median(), b_c, b_m)
    ov = float(tab[(tab["arm"] == "W1") & (tab["win"] == "全窗")]["ov_hold_med"].iloc[0])
    eff = ["| 量 | W1 − W0（逐種子配對） | 95% CI／種子帶 | 判 |", "|---|---:|---|:--:|",
           f"| 逐月報酬配對差 | {ci['diff_pp']:+.3f}pp | {ci['lo_pp']:+.3f}～{ci['hi_pp']:+.3f}pp（{ci['n_months']} 個月） | "
           f"{'✅ 測得出' if ci['detectable'] else '⛔ 測不出'} |",
           f"| 全窗年化差 | {np.median(d_cagr) * 100:+.2f}pp | p10～p90 {np.quantile(d_cagr, 0.1) * 100:+.2f}～{np.quantile(d_cagr, 0.9) * 100:+.2f} | 描述 |",
           f"| 全窗最大回落差 | {np.median(d_mdd) * 100:+.2f}pp | p10～p90 {np.quantile(d_mdd, 0.1) * 100:+.2f}～{np.quantile(d_mdd, 0.9) * 100:+.2f} | 描述（⛔ 只有種子帶） |",
           "",
           f"⭐ **使用者判準（兩腳同時成立）**：0050 全窗年化 {b_c * 100:+.2f}%／最大回落 {b_m * 100:.1f}%",
           f"⇒ W1 年化 {df[df['arm'] == 'W1']['cagr_全窗'].median() * 100:+.2f}%／回落 {df[df['arm'] == 'W1']['mdd_全窗'].median() * 100:.1f}%"
           f" ⇒ **{'✅ 通過' if pass_w1 else '⛔ 沒通過'}**（W0 對照：{'✅ 通過' if pass_w0 else '⛔ 沒通過'}）",
           "",
           f"⛔ **否證③（重疊度）**：W1 的【持股∩前50÷持股】中位 **{ov * 100:.1f}%**（門檻 50%）⇒ "
           + ("⛔ **超過 ⇒ 結論必須寫【這條路在複製 0050】**" if ov > OVERLAP_MAX else "✅ 未超過 ⇒ ⭐ 先驗② 成立"),
           "",
           f"⛔ **否證⑤（集中度）**：W1 的單一部位最大佔比中位 "
           f"{float(tab[(tab['arm'] == 'W1') & (tab['win'] == '全窗')]['maxpos_med'].iloc[0]) * 100:.1f}%"
           + ("　⚠ 已超過 80% ⇒ 那已不是「加權」是「集中持股」" if float(tab[(tab['arm'] == 'W1') & (tab['win'] == '全窗')]['maxpos_med'].iloc[0]) > MAXPOS_ALARM else "")]
    pd.DataFrame([{"diff_pp": ci["diff_pp"], "lo_pp": ci["lo_pp"], "hi_pp": ci["hi_pp"], "n_months": ci["n_months"],
                   "detectable": ci["detectable"], "d_cagr_med": float(np.median(d_cagr)), "d_mdd_med": float(np.median(d_mdd)),
                   "pass_w1": bool(pass_w1), "pass_w0": bool(pass_w0), "overlap_w1": ov,
                   "bench_cagr": float(b_c), "bench_mdd": float(b_m)}]).to_csv(os.path.join(a.out, "judge.csv"), index=False)
    bmk = f"**0050（本線自己算的那一份）**：全窗年化 {b_c * 100:+.2f}%／最大回落 {b_m * 100:.1f}%。"
    probe = [l for l in open(os.path.join(HERE, "resultsp13", "P13_RISKPROBE.md"), encoding="utf-8").read().splitlines()
             if l.startswith("- ") and ("單日" in l or "累積" in l or "last_seen" in l or "沒有成交" in l)][:14]
    probe = ["⭐ 逐字引用 `resultsp13/P13_RISKPROBE.md`（回測線 1815 交件）：", ""] + probe + ["",
             "> **本件的回落判準沒有包含單一檔歸零的情境，因為窗內未發生。⛔ 這不是說它不會發生。**",
             "> **而那個 0 的前提是【台股單日跌幅上限 10%】⇒ 它等於『沒有一天跌超過跌停』，"
             "⛔ 不等於『沒有個股崩掉』——腰斬（≤ −50%）在持股裡發生過 5 次。**"]
    L = report(tab, eff, anc, sig, cal, wins, a.reps, time.time() - t0, bmk, probe)
    open(os.path.join(a.out, "P13_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"寫入 {os.path.join(a.out, 'P13_REPORT.md')}（總計 {time.time() - t0:.0f}s）")


if __name__ == "__main__":
    main()

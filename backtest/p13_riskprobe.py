"""K線分析線 1755 §四 指定的【兩個必報】——取消單一部位上限的代價，⭐ 量給它看。

    python3 -m backtest.p13_riskprobe [--out backtest/resultsp13]

⛔ 這不是登錄、⛔ 不是判定：它是 PREREGP13（策略線正在起草）**必報**的兩個描述量，
⭐ 本線先量出來，讓那份登錄在**寫的時候**就有這兩個數（⛔ 不是跑完才補）。

逐字（K線分析線 1755 §四）：
  「① 窗內本策略【實際持有過】的股票裡，有沒有出現過單日 ≤ −30%？幾次？
    ② 有沒有任何一檔在持有期間下市／停止交易？幾次？
   ⇒ ⛔ 若答案是「一次都沒有」⇒ 結論要逐字寫：
     『本件的回落判準【沒有包含單一檔歸零的情境】，因為窗內未發生。⛔ 這不是說它不會發生。』」

⭐ 兩個母體都報（⛔ 不是只報一個）：
  母體A【訊號超集】＝ 門檻B 全部 2,882 筆訊號的持有窗（任何種子的持股都是它的子集）
  母體B【實際持有】＝ 種子 SEED0 那一顆、N=8、H120 真的進場的部位（⭐ 這才是「實際持有過」逐字要的）
⚠ 而本檔**不**回答「這個風險有多大」——它只回答「窗內發生過幾次」（〈九十八〉：有效樣本數是事件數）。
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp12 as P12

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp13")
DROP_1D = -0.30                  # ⛔ 1755 §四① 寫死的門檻（⛔ 本線不改）
DROP_EXTRA = (-0.20, -0.10)      # ⭐ 另報兩個較鬆的，⛔ 只作描述（⚠ 理由見 main 的輸出：台股單日跌幅上限 10%）
CUM_LEVELS = (-0.30, -0.50)      # ⭐ 持有期間【累積】跌幅（⛔ 描述；單日門檻在台股幾乎打不到）
HALT_GAP = 5                     # 持有期間連續 ≥ 5 個交易日沒有成交 ⇒ 記一次「停止交易」


def crash_days(closes: np.ndarray, lo: int, hi: int, thr: float) -> list:
    """[lo, hi] 內【單日】報酬 ≤ thr 的日子（⭐ 用還原收盤，⛔ 除權息已還原 ⇒ 不會假跌）。"""
    out = []
    for t in range(max(lo, 1), hi + 1):
        a, b = float(closes[t - 1]), float(closes[t])
        if np.isfinite(a) and a > 0 and np.isfinite(b) and b / a - 1.0 <= thr:
            out.append(t)
    return out


def halt_case(opens: np.ndarray, lo: int, hi: int, last_pos: int, gap: int = HALT_GAP) -> dict:
    """持有期間有沒有【下市／停止交易】。

    ⭐ 兩條各自獨立、都報（⛔ 不是二選一）：
      delisted  universe 的 last_seen 落在持有期間【之內】⇒ 這檔在持有中消失
      halted    持有期間有連續 ≥ gap 個交易日**沒有開盤價**（＝那幾天沒有成交）
    ⚠ `opens` ⛔ 不可 ffill（P1.load_prices 的 opens 本來就沒有 ffill）⇒ NaN ＝ 當天沒成交。
    """
    run = best = 0
    for t in range(lo, hi + 1):
        run = run + 1 if not np.isfinite(float(opens[t])) else 0
        best = max(best, run)
    return {"delisted": bool(lo <= last_pos <= hi), "halted": bool(best >= gap), "max_gap": int(best)}


def scan(pos: pd.DataFrame, closes: dict, opens: dict, last_pos: dict) -> pd.DataFrame:
    """逐個部位掃一次 ⇒ 每個部位一列（⛔ 不彙總，彙總在 report 那一層做）。"""
    rows = []
    for r in pos.itertuples():
        sid, lo, hi = r.sid, int(r.entry_pos), int(r.exit_pos)
        cl, op = closes[sid], opens[sid]
        d = {"sid": sid, "entry_pos": lo, "exit_pos": hi,
             **{f"n1d_{int(abs(th) * 100)}": len(crash_days(cl, lo, hi, th)) for th in (DROP_1D, *DROP_EXTRA)}}
        seg = np.array([float(cl[t]) for t in range(lo, hi + 1)], float)
        base = float(cl[lo])
        d["cum_min"] = float(np.nanmin(seg) / base - 1.0) if np.isfinite(base) and base > 0 else np.nan
        d.update(halt_case(op, lo, hi, last_pos.get(sid, -1)))
        rows.append(d)
    return pd.DataFrame(rows)


def summarize(t: pd.DataFrame, label: str) -> list:
    n = len(t)
    L = [f"### {label}（{n:,} 個部位、{t['sid'].nunique():,} 檔）", ""]
    for th in (DROP_1D, *DROP_EXTRA):
        k = f"n1d_{int(abs(th) * 100)}"
        L.append(f"- 單日 ≤ {th * 100:.0f}%：**{int(t[k].sum())} 次**（{int((t[k] > 0).sum())} 個部位、"
                 f"{t.loc[t[k] > 0, 'sid'].nunique()} 檔）")
    for lv in CUM_LEVELS:
        L.append(f"- 持有期間**累積**最深 ≤ {lv * 100:.0f}%：**{int((t['cum_min'] <= lv).sum())} 個部位**"
                 f"（{t.loc[t['cum_min'] <= lv, 'sid'].nunique()} 檔）")
    L.append(f"- 持有期間 last_seen 落在窗內（下市／消失）：**{int(t['delisted'].sum())} 個部位**"
             f"（{t.loc[t['delisted'], 'sid'].nunique()} 檔）")
    L.append(f"- 持有期間連續 ≥ {HALT_GAP} 個交易日沒有成交（停止交易）：**{int(t['halted'].sum())} 個部位**"
             f"（{t.loc[t['halted'], 'sid'].nunique()} 檔；最長 {int(t['max_gap'].max())} 天）")
    L.append(f"- 持有期間最深累積跌幅的分佈：中位 {t['cum_min'].median() * 100:.1f}%／"
             f"p10 {t['cum_min'].quantile(0.1) * 100:.1f}%／最差 {t['cum_min'].min() * 100:.1f}%")
    return L + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=RESULTS); ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe()
    last_pos = {r.stock_id: int(cal.searchsorted(pd.Timestamp(r.last_seen))) for r in uni.itertuples()}
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni.set_index("stock_id")["market"])
    sig = P7.build_sig_gate_b(panel, cal, closes, opens)
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    w0, w1 = P12.win_bounds(cal, "全窗")
    supers = sig.rename(columns={f"xpos_{P12.RULE}": "exit_pos"})[["sid", "entry_pos", "exit_pos"]]
    supers = supers[(supers["exit_pos"] >= w0) & (supers["entry_pos"] <= w1)]
    lg: list = []
    R.simulate_mtm(sig, P12.RULE, P12.N_C1, np.random.default_rng(P12.SEED0), closes, opens, ncal, log=lg)
    held = pd.DataFrame([{"sid": r["sid"], "entry_pos": int(r["t"]), "exit_pos": int(r["exit_pos"])}
                         for r in lg if r["reason"] == "in"])
    tA, tB = scan(supers, closes, opens, last_pos), scan(held, closes, opens, last_pos)
    tA.to_csv(os.path.join(a.out, "riskprobe_signals.csv"), index=False)
    tB.to_csv(os.path.join(a.out, "riskprobe_held.csv"), index=False)
    L = ["# PREREGP13 的兩個必報（K線分析線 1755 §四）——⛔ 描述，⛔ 不是判定", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。"
         f"窗 ＝ 全窗 [{cal[w0].date()}, {cal[w1].date()}]；訊號 ＝ 門檻B（七個驗收數已對）；"
         f"實際持有 ＝ 種子 `default_rng({P12.SEED0})`、N={P12.N_C1}、H120 的那一顆。", "",
         "⛔ 本檔回答的是【窗內發生過幾次】，⛔ 不是【這個風險有多大】（〈九十八〉：有效樣本數是事件數）。", ""]
    L += summarize(tA, "母體A：門檻B 全部訊號的持有窗（⭐ 任何種子的持股都是它的子集）")
    L += summarize(tB, "母體B：⭐【實際持有過】——一顆種子真的進場的部位")
    L += ["---", "", "## ⚠ 一件必須跟著這兩個數字一起讀的事（⭐ 本線量的時候才看見）", "",
          f"**台股單日跌幅上限是 10%** ⇒ 「單日 ≤ {DROP_1D * 100:.0f}%」在還原價上**幾乎只可能出現在停牌復牌那一天**。",
          "⇒ ⛔ 所以那個門檻回 0 次，**不等於**「沒有個股崩掉」——它等於「沒有一天跌超過跌停」。",
          f"⇒ ⭐ 所以本檔另外報了【持有期間累積 ≤ −30%／−50%】與【連續 ≥ {HALT_GAP} 天沒成交】兩欄，",
          "　 ⛔ 它們是描述，⛔ 不是本線自己訂的判準 ⇒ ⏳ 要不要進 PREREGP13 的必報，是 K線分析線／策略線的格子。", ""]
    open(os.path.join(a.out, "P13_RISKPROBE.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

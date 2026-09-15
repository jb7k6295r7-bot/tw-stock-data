"""researchm1 層一自測——⛔ 只用合成序列（登錄未到，不碰真實指數）。
① 逐日狀態＝去抖後所屬段；② 右設限：最後一段不進任何格；③ 段分群 n 與 m1_states 的 n_by_state 相符；
④ 隨機漫步下狀態差的 CI 多數含 0（假陽性率）；⑤ 剔除 7～9 月真的沒有那三個月；⑥ 分段視窗互斥且併起來＝全期；⑦ n<24 一律「還沒測」。"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import m1_states as M  # noqa: E402
from backtest import researchm1 as R  # noqa: E402

FAIL = 0


def check(cond, msg):
    global FAIL
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAIL += 1


def synth(seed=0, n=6000, start="1990-01-04"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, n))), index=idx)


if __name__ == "__main__":
    c = synth()
    ds = R.day_states(c)
    print("[researchm1] 逐日狀態")
    d = ds["a"]; db = M.debounce(M.signals(c)["a"])
    check(len(d) == M.signals(c)["a"].dropna().shape[0] and d["seg_id"].max() == len(db) - 1, "逐日狀態列數＝訊號有值日數、seg_id 對得上段表")
    check((d[d["open"]]["seg_id"] == len(db) - 1).all() and d["open"].sum() == int(db.iloc[-1]["len"]), "最後一段 open＝該段長度")
    L1 = R.layer1(c)
    print("[researchm1] 段分群 n")
    t = M.n_table(c).set_index("signal")
    for key in M.SIGNALS:
        full = L1[(L1.signal == key) & (L1.window == "全期") & (L1.H == 20)]
        tot = int(full["n_seg"].sum()); exp = int(sum(t.loc[key, "n_by_state"].values()))
        check(tot == exp, f"{key} 全期 H20 各狀態段數合計 {tot}＝n_table 的 {exp}")
    print("[researchm1] 假陽性率（隨機漫步，多種子）")
    hits = 0; tot = 0
    for seed in range(6):
        Ls = R.layer1(synth(seed))
        m = Ls[(Ls.window == "全期") & (Ls.judge.str.startswith("測得出"))]
        ok = Ls[(Ls.window == "全期") & Ls.judge.isin(["測不出"]) | (Ls.window == "全期") & Ls.judge.str.startswith("測得出")]
        hits += len(m); tot += len(ok)
    rate = hits / max(tot, 1)
    check(rate < 0.20, f"隨機漫步下「測得出」占可判格 {rate * 100:.0f}%（< 20%；⚠ H 重疊讓 5% 名目率會偏高）")
    print("[researchm1] 敏感度與視窗")
    S = R.layer1(c, exclude_months=(7, 8, 9))
    md = R.month_distribution(c)
    check((S["n_days"].sum() < L1["n_days"].sum()) and (md["q3_share"] > 0).all(), "剔除 7～9 月列數變少、月份分佈 7～9 月占比 > 0")
    dec = L1[(L1.signal == "b") & (L1.H == 20) & L1.window.isin(["1990s", "2000s", "2010s"])]["n_days"].sum()
    full_b = L1[(L1.signal == "b") & (L1.H == 20) & (L1.window == "全期")]["n_days"].sum()
    check(dec == full_b, f"b 三個年代視窗日數合計 {dec}＝全期 {full_b}（合成序列 1990～2013）")
    small = R.layer1(c.iloc[:1500])
    under = small[(small["n_seg"] < R.N_MIN) | (small["rest_n_seg"] < R.N_MIN)]
    check(len(under) > 0 and under["judge"].str.startswith(("還沒測", "窗口長度不可比")).all(), f"n<24 的 {len(under)} 格沒有一格被判測得出／測不出")
    check(not L1[L1["judge"].str.startswith("測")].pipe(lambda z: ((z["n_seg"] < R.N_MIN) | (z["rest_n_seg"] < R.N_MIN)).any()), "判「測得出／測不出」的格 n 與 rest_n 都 ≥ 24")
    a90 = L1[(L1.signal == "a") & (L1.window == "1990s")]
    check(len(a90) > 0 and a90["judge"].str.startswith("窗口長度不可比").all(), "a 的 1990s 視窗結論欄＝窗口長度不可比")
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變：把 layer1 的 `d = d[~d["open"]]` 拿掉 ⇒ 第 3～7 條的段數會多 1、右設限條紅；把 N_MIN 改 5 ⇒ 「還沒測」那條紅

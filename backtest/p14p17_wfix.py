"""把 P14 w=0.50 與 P17 W_fix 之間的 0.96pp【拆開】—— 回測線執行端。

⏳ 回策略線 20260923-2220 §一 的是非題。
⛔ 本支【不重跑 P14】，⛔ 不改 researchp17.py，⛔ 不動任何已交件的輸出。

⚠⚠ 策略線 §一 事前寫死的 (Ⅰ) 是：「P14 不再平衡 ⇒ 那 0.96pp 就是【再平衡本身】的效果」。
⭐ 實作上答案確實是 (Ⅰ)（P14 blend 逐字寫「期初一次配置、之後不再平衡」），
⛔ 但 0.96pp 這個【量】混了兩件事，本支把它拆開：

    P14 w=0.50    不再平衡 ⇒ ⛔ 沒有換手 ⇒ ⛔ 沒有成本
    P17 W_fix     月度再平衡 ⇒ 換手付 0.585%
    ⇒ 0.96pp ＝（再平衡的毛效果）−（再平衡的成本）
    ⇒ ⭐ 成本只會往壞的方向走 ⇒ ⛔ 毛效果【比 0.96pp 大】，不是等於

本支多跑一格：**W_fix 在 cost=0 之下的回落**，讓三個數並列。
⛔ 它是【描述欄】，⛔ 不進任何判定（同 P17 §四⑤ 的地位）。
"""
from __future__ import annotations

import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D          # noqa: E402
from backtest import p4_features as P4F  # noqa: E402
from backtest import researchp1 as P1   # noqa: E402
from backtest import researchp7 as P7   # noqa: E402
from backtest import researchp12 as P12  # noqa: E402
from backtest import researchp17 as P17  # noqa: E402

HERE = os.path.expanduser("~/tw-p17/backtest")
SRC = os.path.join(HERE, "resultsp17")


def main():
    t0 = time.time()
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, P17.WIN)
    marks = P12.month_marks(cal, w0, w1)
    n = w1 - w0 + 1
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    if P7.accept_sig_b(sig) != P7.WANT_SIG_B:
        raise SystemExit("⛔ 門檻B sig 驗收數對不上 ⇒ 停跑")
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    B = bench[w0:w1 + 1]
    rb = P17.rebal_days(cal, w0, w1)
    rebal_mask = np.zeros(n, bool); rebal_mask[[int(t) for t in rb]] = True

    P17._init(sig, closes, opens, ncal, w0, w1, marks)
    with Pool(8, initializer=P17._init,
              initargs=(sig, closes, opens, ncal, w0, w1, marks)) as pool:
        res = pool.map(P17._one, [("WFIX", r) for r in range(P17.REPS)])
    eqs = {x[0]["r"]: x[1] for x in res}
    print("[策略側] {} 顆（{:.0f}s）".format(len(eqs), time.time() - t0))

    wfix = np.full(n, P17.W_FIX)
    rows = []
    for r in sorted(eqs):
        E = eqs[r]
        Vc, turn, cst = P17.compose(E, B, wfix, rebal_mask)                 # 含成本（＝ 已交件的 W_fix）
        V0, t0_, _ = P17.compose(E, B, wfix, rebal_mask, cost=0.0)          # ⭐ 成本 0
        Vb = P17.blend_like(E, B) if hasattr(P17, "blend_like") else None   # （沒有就不用）
        cg_c, md_c = P17._stats(Vc)
        cg_0, md_0 = P17._stats(V0)
        # ⭐ P14 的合成式：期初一次配置、之後不再平衡 ⇒ 逐字重寫一行（⛔ P14 在另一棵樹，不 import）
        Vn = P17.W_FIX * (E / E[0]) + (1.0 - P17.W_FIX) * (B / B[0])
        cg_n, md_n = P17._stats(Vn)
        rows.append({"r": r, "cagr_rebal_cost": cg_c, "mdd_rebal_cost": md_c,
                     "cagr_rebal_free": cg_0, "mdd_rebal_free": md_0,
                     "cagr_norebal": cg_n, "mdd_norebal": md_n,
                     "turn_sum": float(turn.sum()), "cost_sum": float(cst.sum())})
    d = pd.DataFrame(rows)

    # ⭐⭐ 錨點：含成本那一欄必須與【已交件的】 per_seed_arm.csv 的 W_fix 逐位元相同
    # ⚠⚠ 必須用 float_precision="round_trip" 讀 —— pandas 的【預設】解析會丟掉最後幾個位元
    #   ⇒ 用預設讀會得到 110/200「不同」，⛔ 那是【讀檔參數】的問題，不是數字的問題
    #   （researchp17.py 自己讀 cells.csv 時也是指定 round_trip）
    ref = pd.read_csv(os.path.join(SRC, "per_seed_arm.csv"), float_precision="round_trip")
    ref = ref[(ref["arm"] == "W_fix") & (ref["rep"] == -1)].set_index("r")
    bad = []
    for r in d["r"]:
        got = float(d.loc[d["r"] == r, "mdd_rebal_cost"].iloc[0])
        want = float(ref.loc[r, "mdd"])
        if repr(got) != repr(want):
            bad.append((r, got, want))
    print("[錨點] 含成本的 W_fix 對【已交件】per_seed_arm.csv：{}/{} 逐位元相同"
          .format(len(d) - len(bad), len(d)))
    if bad:
        for r, g_, w_ in bad[:5]:
            print("   r={} 得 {!r} 要 {!r}".format(r, g_, w_))
        raise SystemExit("⛔⛔ 錨點不過 ⇒ 停止，⛔ 下面的拆解不可引用")

    out = os.path.join(HERE, "resultsp17_bc")
    os.makedirs(out, exist_ok=True)
    d.to_csv(os.path.join(out, "p14p17_wfix.csv"), index=False)

    print()
    print("=== ⭐⭐ w ＝ 0.50 這一格的三種合成法（⛔ 全部同一批種子、同一條策略側）===")
    print()
    print("  {:<34}{:>12}{:>12}".format("合成法", "年化中位", "回落中位"))
    print("  " + "-" * 58)
    print("  {:<34}{:>11.2f}%{:>11.2f}%".format(
        "① 不再平衡（＝ P14 §一1-B blend）", d["cagr_norebal"].median() * 100,
        d["mdd_norebal"].median() * 100))
    print("  {:<34}{:>11.2f}%{:>11.2f}%".format(
        "② 月度再平衡・成本 0", d["cagr_rebal_free"].median() * 100,
        d["mdd_rebal_free"].median() * 100))
    print("  {:<34}{:>11.2f}%{:>11.2f}%".format(
        "③ 月度再平衡・成本 0.585%（＝ P17 W_fix）", d["cagr_rebal_cost"].median() * 100,
        d["mdd_rebal_cost"].median() * 100))
    print()
    g = (d["mdd_rebal_free"].median() - d["mdd_norebal"].median()) * 100
    c = (d["mdd_rebal_cost"].median() - d["mdd_rebal_free"].median()) * 100
    net = (d["mdd_rebal_cost"].median() - d["mdd_norebal"].median()) * 100
    print("  回落的拆解（正 ＝ 回落變淺 ＝ 比較好）：")
    print("    再平衡的【毛效果】 ② − ① ＝ {:+.2f}pp".format(g))
    print("    再平衡的【成本】   ③ − ② ＝ {:+.2f}pp".format(c))
    print("    ─────────────────────────────")
    print("    淨效果             ③ − ① ＝ {:+.2f}pp".format(net))
    print()
    print("  換手金額合計中位 {:.4f}／成本合計中位 {:.4f}"
          .format(d["turn_sum"].median(), d["cost_sum"].median()))
    print()
    print("  ⚠⚠ 本支的 ① 是【在本棵樹上用 P14 的合成式重算的】，⛔ 不是 P14 的交件值。")
    print("     ⇒ ⭐ 它與 P14 交件的 −34.16% 若有差，差的是【P14 與 P17 的其餘口徑】，")
    print("       ⛔ 不是再平衡 ⇒ 那個差要另外對帳，本支不代答。")
    print()
    print("[輸出] {}／p14p17_wfix.csv".format(out))


if __name__ == "__main__":
    main()

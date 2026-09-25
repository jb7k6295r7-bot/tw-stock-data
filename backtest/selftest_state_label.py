# -*- coding: utf-8 -*-
"""state_label 的 fixture（合成價格序列；⛔ 不讀任何資料）。全部 assert 過才印 ✅。

 ① 偏漲：上升鋸齒、收在上揚的 MA20 之上 ⇒ A ∧ 上升 ⇒ 偏漲
 ② 偏跌：①的鏡像 ⇒ D ∧ 下降 ⇒ 偏跌
 ③ 盤整：上升鋸齒、最後急跌到 MA20 下而 MA20 仍上揚 ⇒ C ∧ 上升 ⇒ 盤整（C…；高低點上升）
 ④ 兩高點相等 ⇒ 混合（低點墊高、A 結構也一樣是盤整）；兩低點相等同理
 ⑤ 確認價／破壞價取對的點（手造 30 根，手標擺動點）
 ⑥ 無前視：右邊只走完 4 根的擺動高點不可被用到，第 5 根走完那天才生效；asof 之後的資料改成任意值結果不變
 ⑦ 擺動點偵測與一份獨立寫法（不呼叫 stop_fractal）逐點相同（隨機序列 200 組）
 ⑧ 「先證明分得出來」：①②③ 三個標籤互不相同，且把 ① 的最後一根改到 MA 下方標籤會變（不是恆等輸出）
"""
from __future__ import annotations
import os, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from state_label import core, label_text  # noqa: E402


def tri(n, period, amp):
    i = np.arange(n); ph = (i % period) / period
    return amp * np.where(ph < 0.5, ph * 2, 2 - ph * 2)          # 0→amp→0 的三角波（嚴格單調段）


def hlc_from_close(c, w=0.3):
    return c + w, c - w, c


def run(c):
    h, l, cc = hlc_from_close(np.asarray(c, float))
    r = core(h, l, cc); r["gate_reason"] = ""; r["label"] = label_text(r); return r


def brute_swings(x, k):
    """獨立寫法：s 為擺動低點 ⟺ x[s] < min(左 k 根) 且 x[s] < min(右 k 根)（用 min，不用 np.all 比較）。"""
    out = []
    for s in range(len(x)):
        if s - k < 0 or s + k >= len(x):
            continue
        if x[s] < min(x[s - k:s]) and x[s] < min(x[s + 1:s + k + 1]):
            out.append(s)
    return out


def main():
    n = 150
    # ① 偏漲：趨勢 +0.3／根、三角波振幅 6、週期 20；在上升段結束前停（最後一根在上升段中）
    up = 50 + 0.3 * np.arange(n) + tri(n, 20, 6.0)
    c1 = up[:148]                                   # 148 % 20 ＝ 8 ⇒ 位在上升段（相位 0.4）
    r1 = run(c1)
    assert r1["ma_struct"] == "A" and r1["hl_struct"] == "上升" and r1["label"] == "偏漲", r1
    # ② 偏跌：鏡像
    r2 = run(200 - c1)
    assert r2["ma_struct"] == "D" and r2["hl_struct"] == "下降" and r2["label"] == "偏跌", r2
    # ③ 盤整：① 最後一根跌到 MA20 下（MA20 仍上揚）
    c3 = c1.copy(); c3[-1] = 93.0                  # 介於 c[t−20]＝92.3 與 MA20≈93.99 之間 ⇒ MA 仍上揚、價在 MA 下
    r3 = run(c3)
    assert r3["ma_struct"] == "C" and r3["hl_struct"] == "上升" and r3["label"].startswith("盤整（C："), r3
    assert "高低點上升" in r3["label"], r3["label"]
    # ⑧ 分得出來
    assert len({r1["label"], r2["label"], r3["label"]}) == 3
    # ④ 兩高點相等：無趨勢三角波（高點全相等），低點另外墊高
    flat = 50 + tri(n, 20, 6.0)
    ramp_lo = flat.copy()
    # 只抬低點：在每個谷底加一點點遞增量，高點不動
    troughs = [i for i in range(n) if i % 20 == 0]
    for j, t in enumerate(troughs):
        ramp_lo[t] -= 0.0 - 0.01 * j                  # 谷底逐次 +0.01 ⇒ HL
    r4 = run(ramp_lo[:148])
    assert r4["hi_cmp"] == "EH" and r4["lo_cmp"] == "HL" and r4["hl_struct"] == "混合", r4
    assert r4["label"].startswith("盤整"), r4["label"]
    # 兩低點相等（高點墊高）
    ramp_hi = flat.copy()
    for j, t in enumerate(i for i in range(n) if i % 20 == 10):
        ramp_hi[t] += 0.01 * j
    r4b = run(ramp_hi[:148])
    assert r4b["lo_cmp"] == "EL" and r4b["hi_cmp"] == "HH" and r4b["hl_struct"] == "混合", r4b
    # ⑤ 手造 30 根（直接給 high；low ＝ high − 1；close ＝ high − 0.5）
    H = np.array([10, 11, 12, 13, 14, 20, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 14, 22, 14, 13, 12, 11, 10, 11, 12, 13, 14, 15, 16, 25], float)
    L = H - 1; C = H - 0.5
    #  擺動高點：5（20）、17（22）；29（25）右邊沒有 5 根 ⇒ 未確認｜擺動低點：11（8）、22（9）
    r5 = core(H, L, C)
    assert r5["swing_hi_idx"] == [5, 17] and r5["swing_lo_idx"] == [11, 22], (r5["swing_hi_idx"], r5["swing_lo_idx"])
    assert r5["confirm_adj"] == 22.0 and r5["break_adj"] == 9.0, (r5["confirm_adj"], r5["break_adj"])
    assert r5["hl_struct"] == "上升" and r5["hi_cmp"] == "HH" and r5["lo_cmp"] == "HL"
    # ⑥ 無前視：截在 index 21（17 的右邊只有 18..21 四根）⇒ 最近已確認高點仍是 5（20）；截在 22 ⇒ 變 17（22）
    r6a = core(H[:22], L[:22], C[:22]); r6b = core(H[:23], L[:23], C[:23])
    assert r6a["confirm_idx"] == 5 and r6a["confirm_adj"] == 20.0, r6a
    assert r6b["confirm_idx"] == 17 and r6b["confirm_adj"] == 22.0, r6b
    # asof 之後的資料亂改，呼叫端截斷後結果逐欄相同
    Hx = H.copy(); Hx[23:] = 999.0; Lx = Hx - 1; Cx = Hx - 0.5
    r6c = core(Hx[:23], Lx[:23], Cx[:23])
    assert {k: v for k, v in r6c.items()} == {k: v for k, v in r6b.items()}
    # 破壞價同理：低點 22 在截到 index 26 時（右邊 23..26 四根）還不可用、27 才可用
    r6d = core(H[:27], L[:27], C[:27]); r6e = core(H[:28], L[:28], C[:28])
    assert r6d["break_idx"] == 11 and r6e["break_idx"] == 22, (r6d["break_idx"], r6e["break_idx"])
    # ⑦ 獨立寫法對照
    rng = np.random.default_rng(20260925)
    from backtest import stop_fractal as SF
    tot = 0
    for _ in range(200):
        x = np.round(np.cumsum(rng.normal(0, 1, 300)), 1)        # 取 1 位小數 ⇒ 會出現相等值，順便驗嚴格不等式
        a = np.flatnonzero(SF.swing_lows(x, 5)).tolist(); b = brute_swings(x.tolist(), 5)
        assert a == b, (a, b); tot += len(a)
        a2 = np.flatnonzero(SF.swing_lows(-x, 5)).tolist(); b2 = brute_swings((-x).tolist(), 5)
        assert a2 == b2; tot += len(a2)
    # ⑧ 恆等輸出檢查：① 最後一根壓到 MA 之下 ⇒ 標籤改變
    c8 = c1.copy(); c8[-1] = r1["ma20"] - 5
    assert run(c8)["label"] != r1["label"]
    print("✅ state_label fixture 全過：")
    for tag, r in (("①", r1), ("②", r2), ("③", r3), ("④高相等", r4), ("④低相等", r4b)):
        print("  {} {}｜結構 {}｜高低點 {} ({}/{})｜確認 {:.2f} 破壞 {:.2f}".format(tag, r["label"], r["ma_struct"], r["hl_struct"], r["hi_cmp"], r["lo_cmp"], r["confirm_adj"], r["break_adj"]))
    print("  ⑤ 手造：擺動高 {} 低 {}｜確認 {} 破壞 {}".format(r5["swing_hi_idx"], r5["swing_lo_idx"], r5["confirm_adj"], r5["break_adj"]))
    print("  ⑥ 無前視：截到第 21 根確認價 {}（17 號只走完 4 根不用）→ 第 22 根 {}；未來亂改結果相同；低點 22 在第 26 根不可用、27 可用".format(r6a["confirm_adj"], r6b["confirm_adj"]))
    print("  ⑦ 擺動點與獨立寫法 200×2 組逐點相同（共 {:,} 個點，含相等值）".format(tot))
    print("  ⑧ 三標籤互異；① 最後一根壓到 MA 下 ⇒ 標籤改變")


if __name__ == "__main__":
    main()

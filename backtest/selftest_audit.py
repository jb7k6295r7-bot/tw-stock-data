# -*- coding: utf-8 -*-
"""simulate_mtm 新參數 audit 的 fixture（⇐ 裁定線 1714 §三⑥：D4 起預設開，補目標權重／換手／逐次成本）。

⭐⭐ 本檔的重點不是「有沒有那三欄」，是**稽核紀錄與引擎的記帳對不對得上**：
   A1 買賣配對：每個 sid 的 buy 與 sell 一一對應
   A2 ⭐⭐ **成本可加總**：Σ audit.cost ＝ 引擎實際扣的成本（⛔ 用權益曲線反推，不是抄參數）
   A3 ⭐ **目標權重**：買進那筆的 target_w ＝ amt ÷ 前一日 equity（手算對照）
   A4 換手：買賣筆數 ＝ 2 × trades
   B1 ⭐ audit=None 時【一行新程式都不走】⇒ 回歸閘門另有（regress_tradability.py）
   ⛔ 每條都附會紅的反例。
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R
C = R.COST; N = 40
def arr(v): return np.full(N, float(v))
ok = 0

# 合成：A 在 10 進 15 出（100→110）；B 在 12 進 20 出（50→45）；n_slots=2 ⇒ 兩檔都買得到
# ⭐ A 在 **t=11** 就漲到 110（⛔ 不是 t=15）⇒ B 在 t=12 進場時 equity 已經 ≠ 1.0
#   ⇒ ⚠ 否則「分母用哪一天的 equity」在這個 fixture 上分不出來（第一、二版都敗在這裡）
clA = arr(100); clA[11:] = 110
clB = arr(50);  clB[20:] = 45
cl = {"A": clA, "B": clB}; op = {"A": arr(100), "B": arr(50)}
sig = pd.DataFrame([
    {"sid": "A", "entry_pos": 10, "xpos_T": 15, "g_T": 110/100 - 1},
    {"sid": "B", "entry_pos": 12, "xpos_T": 20, "g_T": 45/50 - 1},
])
aud = []
out = R.simulate_mtm(sig, "T", 2, np.random.default_rng(0), cl, op, N, return_equity=True, audit=aud)
d = pd.DataFrame(aud)
print("稽核紀錄 {} 筆：\n{}\n".format(len(d), d.to_string(index=False)))

# ── A1 買賣配對 ────────────────────────────────
pair = d.groupby(["sid", "side"]).size().unstack(fill_value=0)
assert (pair["buy"] == 1).all() and (pair["sell"] == 1).all(), pair
ok += 1; print("✅ A1 買賣配對：A、B 各 1 買 1 賣")

# ── A2 ⭐⭐ 成本可加總（⛔ 用權益曲線反推，不是抄參數）──
eq = out["equity"]; end = out["end"]
gross_sum = 0.0
for r in sig.itertuples():
    amt = float(d[(d.sid == r.sid) & (d.side == "buy")]["amt"].iloc[0])
    gross_sum += amt * getattr(r, "g_T")
final_gain = float(eq[end - 1] - 1.0)            # 引擎實際的總損益
cost_from_eq = gross_sum - final_gain            # ⇒ 引擎實際扣掉的成本
cost_audit = float(d["cost"].sum())
assert abs(cost_from_eq - cost_audit) < 1e-12, (cost_from_eq, cost_audit)
ok += 1; print("✅ A2 成本可加總：Σ audit.cost {:.10f} ＝ 權益曲線反推 {:.10f}".format(cost_audit, cost_from_eq))
# 反例：若把 buy 也記一次成本 ⇒ 會多一倍
assert abs((cost_audit * 2) - cost_from_eq) > 1e-6, "⛔ A2 反例分不出來"
print("   反例：買賣各記一次成本 ⇒ {:.6f} ≠ {:.6f} ⇒ 必紅".format(cost_audit * 2, cost_from_eq))

# ── A3 ⭐ 目標權重手算 ──────────────────────────
b = d[d.side == "buy"].set_index("sid")
for sid in ("A", "B"):
    t = int(b.loc[sid, "t"]); amt = float(b.loc[sid, "amt"])
    hand = amt / float(eq[t - 1])
    assert abs(b.loc[sid, "target_w"] - hand) < 1e-12, (sid, b.loc[sid, "target_w"], hand)
    assert abs(b.loc[sid, "equity_prev"] - eq[t - 1]) < 1e-12
ok += 1; print("✅ A3 目標權重：A {:.6f}／B {:.6f} ＝ amt ÷ 前一日 equity（手算相符）".format(
    b.loc["A", "target_w"], b.loc["B", "target_w"]))
# ⚠ 反例要挑一個【分母真的不同】的日子：A 進場當天現金換股票、equity 不變
#   ⇒ ⛔ 用當日 equity 當分母在 t=10 分不出來（第一版的反例就是敗在這裡）
#   ⇒ ⭐ 改用 B：它在 t=12 進場，而 A 已經在 t=10~12 漲過 ⇒ 前一日與更早的 equity 不同
tB = int(b.loc["B", "t"]); amtB = float(b.loc["B", "amt"])
wrong = amtB / float(eq[tB - 3])                 # ⛔ 用三天前的 equity（t=9，那時還是 1.0）
assert abs(wrong - b.loc["B", "target_w"]) > 1e-9, (wrong, b.loc["B", "target_w"])
print("   反例：B 的分母改用【三天前】equity ⇒ {:.6f} ≠ {:.6f} ⇒ 必紅".format(wrong, b.loc["B", "target_w"]))
# ⭐ 另一個反例：A 與 B 的 equity_prev 必須不同（⛔ 若程式寫死 1.0 就分不出來）
assert abs(float(b.loc["A", "equity_prev"]) - float(b.loc["B", "equity_prev"])) > 1e-9,     "⛔ 兩筆的 equity_prev 相同 ⇒ 可能是寫死 1.0"
print("   反例：equity_prev A {:.6f} vs B {:.6f} ⇒ ⭐ 確實逐日更新，⛔ 不是寫死 1.0".format(
    float(b.loc["A", "equity_prev"]), float(b.loc["B", "equity_prev"])))

# ── A4 換手筆數 ────────────────────────────────
assert len(d) == 2 * out["trades"], (len(d), out["trades"])
ok += 1; print("✅ A4 換手：稽核 {} 筆 ＝ 2 × trades({})".format(len(d), out["trades"]))

# ── B1 audit=None 不走新程式 ───────────────────
o2 = R.simulate_mtm(sig, "T", 2, np.random.default_rng(0), cl, op, N, return_equity=True)
assert np.array_equal(o2["equity"], eq), "⛔ audit 竟然改了權益曲線"
ok += 1; print("✅ B1 audit=None 與 audit=[] 的權益曲線逐位元相同（⭐ 回歸 18 組另由 regress_tradability.py 把關）")

print("\n⇒ {} 條全過，⭐ 且 A2／A3 的反例都證明分得出來".format(ok))

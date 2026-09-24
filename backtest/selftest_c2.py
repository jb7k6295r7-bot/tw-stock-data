# -*- coding: utf-8 -*-
"""PREREGC2 開跑前 fixture **三案例**（⇐ 裁定線 1942 §一，⛔ 從兩案改三案）。

甲 BTC 左截　　2019-12 absent ⇒ 從 2019-10-01 起跑必須【拒絕或切到 2020-01-01】，⛔ 不可當費率 0
乙 SOL 未上市　2020-08 absent ⇒ 2020-09-13 前必須【沒有部位】，⛔ 不是有部位但成本 0
丙 間隔換檔　　SOL 2022-11 ⇒ 必須讀到 **165 次結算、累計 −0.354915**
              ⚠ 反例：寫死「每 8 小時一次」⇒ 只剩 64 列、−0.063680 ⇒ **必紅**
⭐ 每案都附【改一格就紅】的反例（〈一百一十三〉：fixture 要先證明分得出來）
"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
import pandas as pd
from backtest import funding as F

ok = 0

# ── 甲 BTC 左截 ──────────────────────────────────────
try:
    F.load_month("BTC", 2019, 12)
    raise SystemExit("⛔ 甲：2019-12 不該讀得到")
except F.FundingAbsent:
    pass
d = F.load_month("BTC", 2020, 1)
first = d["ts"].min()
# ⚠ calc_time 帶毫秒尾數（實測 SOL 首筆是 …16:00:00.004）⇒ 比到【秒】
assert first.floor("s") == pd.Timestamp("2020-01-01 00:00:00", tz="UTC"), first
assert len(d) == 93, len(d)
# ⭐ 會紅的反例：把 absent 當成費率 0 ⇒ 窗首會被當成 2019-10-01
try:
    F.settlements("BTC", [(2019, 10), (2019, 11), (2019, 12), (2020, 1)])
    raise SystemExit("⛔ 甲反例：跨 absent 的窗不該接得起來（⇒ 那就是把缺資料當 0）")
except F.FundingAbsent as e:
    pass
ok += 1
print("✅ 甲 BTC 左截：2019-12 absent ⇒ 拋 FundingAbsent；2020-01 首筆 {} 共 {} 列".format(first, len(d)))
print("   反例：從 2019-10 起接 ⇒ ⛔ 拋 FundingAbsent（⭐ 不會靜默當費率 0）")

# ── 乙 SOL 未上市 ────────────────────────────────────
try:
    F.load_month("SOL", 2020, 8)
    raise SystemExit("⛔ 乙：2020-08 不該讀得到")
except F.FundingAbsent:
    pass
s = F.load_month("SOL", 2020, 9)
f0 = s["ts"].min()
assert f0.floor("s") == pd.Timestamp("2020-09-13 16:00:00", tz="UTC"), f0
assert len(s) == 52, len(s)
# ⭐ 會紅的反例：日期改早一天 ⇒ 2020-09-12 應該【沒有任何結算】
before = s[s["ts"] < pd.Timestamp("2020-09-13", tz="UTC")]
assert len(before) == 0, "⛔ 乙反例：上市日前不該有結算，卻有 {} 筆".format(len(before))
ok += 1
print("✅ 乙 SOL 未上市：2020-08 absent；2020-09 首筆 {}（共 {} 列）".format(f0, len(s)))
print("   反例：2020-09-13 之前的結算筆數 ＝ 0 ⇒ ⭐ 是【沒有部位】，⛔ 不是成本 0")

# ── 丙 間隔換檔（⭐ 裁定線 1942 新增的那一案）────────────
c = F.load_month("SOL", 2022, 11)
mix = F.interval_mix(c)
tot = F.cum_cost(c)
assert len(c) == 165, len(c)
assert abs(tot - (-0.354915)) < 5e-7, tot
assert mix == {8: 64, 4: 2, 2: 99}, mix
# ⭐ 會紅的反例①：寫死「每 8 小時一次」⇒ 只取 interval==8
wrong8 = float(c[c["funding_interval_hours"] == 8]["last_funding_rate"].sum())
assert abs(wrong8 - (-0.063680)) < 5e-7, wrong8
assert abs(wrong8 - tot) > 0.29, "⛔ 丙反例分不出來"
# ⭐ 會紅的反例②：假設 30 天 × 3 次／日 ＝ 90 次
assert len(c) != 90, "⛔ 丙反例②分不出來"
ok += 1
print("✅ 丙 間隔換檔：SOL 2022-11 讀到 **{} 次結算**、累計 **{:.6f}** ⇒ 與裁定線 1942 逐位相符".format(len(c), tot))
print("   interval 逐列統計 {} ⇒ ⭐ 是【三種】8／4／2，⛔ 不是兩種".format(mix))
print("   反例①：寫死每 8 小時 ⇒ 只剩 {} 列、{:.6f}（差 {:+.6f}）⇒ **必紅**".format(
    int((c['funding_interval_hours'] == 8).sum()), wrong8, wrong8 - tot))
print("   反例②：假設 30×3 ＝ 90 次 ⇒ 與實際 165 不符 ⇒ **必紅**")

print("\n⇒ {} 案全過，⭐ 且每案的反例都證明分得出來（〈一百一十三〉）".format(ok))

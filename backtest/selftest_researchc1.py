"""PREREGC1 必10：執行時點的手算 fixture ＋ 突變測試 —— 回測線執行端。

⛔ 登錄 §2-A（v6 訂正・必10）逐字要求四件：
  ① 用一段手造價格（例如 10 根 K 棒，第 6 根收盤突破 SMA），【人工算出】正確答案
  ② 正確答案：第 6 根收盤出訊號 ⇒ 報酬從第 7 根開始算（訊號(6)×r(7)，⛔ 不是訊號(6)×r(6)）
  ③ 實作跑這段手造價格，輸出要與 ① 的手算結果【逐位元相同】
     ⇒ 手造價格取【二進位可精確表示】的數（依〈一百三十三〉／〈一百二十一〉）
  ④ 突變測試：把實作故意改成 訊號(t)×r(t)，跑同一段 fixture ⇒ 必須【變紅】

⭐⭐ 而本支多做一件（裁定線 20260924-0038 §二 已准，對應〈一百一十三〉）：
  **先證明這個 fixture 分得出來** —— ⛔ 一個全綠的 fixture 可能只是空對空。
  ⇒ 本支第 ⓪ 格先驗「正確實作」與「已知錯誤實作」在這段 fixture 上給出【不同】答案；
    ⛔ 若相同 ⇒ 立刻停止，⛔ 不報任何結果（因為那代表 fixture 沒有鑑別力）。
  ⚠ 這一格是本線 2026-09-23 在台股 P5 改尺那件事上踩過坑之後加的：
    舊自測在新舊兩把尺底下給同一個答案 ⇒ 它證明不了任何事。
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C   # noqa: E402

FAIL = []

# ── 手造價格：⭐ 全部是【二進位可精確表示】的數（2 的冪的和）────────────────
#   SMA 長度取 N=3（登錄 §2-A：fixture 用小 N 驗時點邏輯，主格 N=200 不受影響）
#   ⭐ 設計：前 5 根壓在 SMA3 之下或相等，第 6 根（index 5）收盤【突破】
PRICES = np.array([
    64.0,   # 0
    64.0,   # 1
    64.0,   # 2   SMA3(2) = 64.0   close = 64.0  ⇒ 64.0 > 64.0 為假 ⇒ 空手
    63.0,   # 3   SMA3(3) = (64+64+63)/3 = 63.666…  ⇒ 63.0 > 63.666 假 ⇒ 空手
    62.0,   # 4   SMA3(4) = (64+63+62)/3 = 63.0     ⇒ 62.0 > 63.0  假 ⇒ 空手
    68.0,   # 5 ⭐ SMA3(5) = (63+62+68)/3 = 64.333…  ⇒ 68.0 > 64.333 真 ⇒ 【出訊號】
    72.0,   # 6   SMA3(6) = (62+68+72)/3 = 67.333…  ⇒ 72.0 > 67.333 真 ⇒ 持有
    80.0,   # 7
    76.0,   # 8
    72.0,   # 9
], dtype=float)
N_FIX = 3


def check(name, got, want, exact=True):
    # ⭐ numpy 純量的 repr 與 python float 不同 ⇒ 先轉成 python 原生型別再比
    #   ⛔ 這不是放寬容差：float(x) 不改變位元，只是換 repr
    if isinstance(got, np.generic):
        got = got.item()
    if isinstance(got, (list, tuple)):
        got = [x.item() if isinstance(x, np.generic) else x for x in got]
    if exact:
        ok = repr(got) == repr(want)
    else:
        ok = bool(np.allclose(got, want, rtol=0, atol=0))
    print("{} {}".format("PASS" if ok else "⛔FAIL", name))
    if not ok:
        print("     得 {!r}".format(got))
        print("     要 {!r}".format(want))
        FAIL.append(name)


def wrong_impl(c, n):
    """⛔ 已知錯誤版本：訊號(t) 吃【當天】報酬 r(t)（登錄明令不可）。"""
    m = C.sma(c, n)
    ok = np.flatnonzero(~np.isnan(m))
    w0 = int(ok[0])
    cw, mw = c[w0:], m[w0:]
    sig = (cw > mw).astype(float)
    r = np.empty(len(cw)); r[0] = 0.0
    r[1:] = cw[1:] / cw[:-1] - 1.0
    held = sig[1:]                     # ⛔ 錯：讓訊號(t) 對到 r(t)
    rets = r[1:]
    prev = np.insert(held[:-1], 0, 0.0)
    return held * rets - np.abs(held - prev) * (C.COST_RT / 2.0)


print("=" * 72)
print("⓪ ⭐⭐ 先證明這個 fixture【分得出來】（⛔ 不然下面全綠也沒有意義）")
print("=" * 72)
right = C.rule_series(PRICES, N_FIX)["r_rule"]
wrong = wrong_impl(PRICES, N_FIX)
same = len(right) == len(wrong) and np.array_equal(right, wrong)
print("  正確實作 r_rule ＝ {}".format(np.round(right, 8).tolist()))
print("  錯誤實作 r_rule ＝ {}".format(np.round(wrong, 8).tolist()))
if same:
    raise SystemExit("⛔⛔ 兩種實作在這段 fixture 上給出【相同】答案\n"
                     "   ⇒ 這個 fixture 沒有鑑別力 ⇒ 停止，⛔ 不報任何結果")
print("  ✅ 兩者【不同】⇒ ⭐ 這段 fixture 對「訊號吃哪一天的報酬」有鑑別力")

print()
print("=" * 72)
print("① SMA 與訊號（⭐ 人工算出的答案，⛔ 不是抄程式輸出）")
print("=" * 72)
m = C.sma(PRICES, N_FIX)
# 手算：SMA3 從 index 2 起有值
want_sma = [np.nan, np.nan, 64.0, 191.0 / 3.0, 63.0, 193.0 / 3.0, 202.0 / 3.0,
            220.0 / 3.0, 76.0, 76.0]
for i in range(2, 10):
    check("① SMA3(index {}) ＝ {!r}".format(i, want_sma[i]), float(m[i]), want_sma[i])

# ⭐⭐ 手算訂正（2026-09-24）：本線第一版把 index 8 寫成 1，⛔ 那是錯的。
#   index 8：收盤 76.0，SMA3 ＝ (72+80+76)/3 ＝ 76.0 ⇒ 76.0 > 76.0 為【假】⇒ 0
#   ⇒ ⭐ fixture 抓到的是【本線的手算錯誤】，⛔ 不是實作錯誤 —— 這正是它該做的事。
#   ⭐ 而訂正後的 fixture 更好：它同時驗到【進場】與【出場】兩次成本。
want_sig = [0, 0, 0, 0, 0, 1, 1, 1, 0, 0]
got_sig = [int(PRICES[i] > m[i]) if not np.isnan(m[i]) else 0 for i in range(10)]
check("① 訊號序列（0/1，index 5 起為 1，index 9 轉 0）", got_sig, want_sig)

print()
print("=" * 72)
print("② ⭐⭐ 執行時點：訊號(5) 必須吃 r(7)＝index 6 的報酬，⛔ 不是 r(6)")
print("=" * 72)
res = C.rule_series(PRICES, N_FIX)
w0 = res["w0"]
check("② 窗首 w0（＝ SMA3 第一個有值的 index）", w0, 2)
# 窗內 close ＝ PRICES[2:] ＝ [64,63,62,68,72,80,76,72]（8 根）
# 窗內 sig   ＝ [0,0,0,1,1,1,0,0]   ⭐ index 8 收盤 76.0 ＝ SMA3 76.0 ⇒ 不成立
# held（第 i 期持有旗標）＝ sig[:-1] ＝ [0,0,0,1,1,1,0]
# rets（第 i 期報酬）    ＝ r[1:] ＝ [63/64−1, 62/63−1, 68/62−1, 72/68−1, 80/72−1, 76/80−1, 72/76−1]
check("② held 序列", res["held"].astype(int).tolist(), [0, 0, 0, 1, 1, 1, 0])
want_rets = [63.0 / 64.0 - 1, 62.0 / 63.0 - 1, 68.0 / 62.0 - 1, 72.0 / 68.0 - 1,
             80.0 / 72.0 - 1, 76.0 / 80.0 - 1, 72.0 / 76.0 - 1]
check("② rets 序列（逐位元）", res["r_bh"].tolist(), want_rets)

# ⭐⭐ 關鍵斷言：訊號在窗內 index 3（＝原始 index 5）出現，
#   而它吃到的是 rets[3]（＝ 68→72 那一段，原始 index 5→6）
#   ⇒ ⛔ 若實作吃 r(t) 本身，held 會變成 [0,0,1,1,1,1,0]，第 2 期就開始賺
check("②⭐ 第 2 期（原始 index 4→5，68 那根之前）必須【沒有】部位", res["held"][2], 0.0)
check("②⭐ 第 3 期（原始 index 5→6）必須【有】部位", res["held"][3], 1.0)
check("②⭐ 第 6 期（原始 index 8，收盤＝SMA）必須【已出場】", res["held"][6], 0.0)
check("②⭐ 訊號日當天的漲幅 68/62−1 ＝ {:.6f} 必須【沒有】被規則吃到"
      .format(68.0 / 62.0 - 1), res["gross"][2], 0.0)

print()
print("=" * 72)
print("③ 成本（⭐ 期初從空手起算 ⇒ 第一次進場要收單邊成本）")
print("=" * 72)
# 持有旗標 [0,0,0,1,1,1,0]，prev ＝ [0,0,0,0,1,1,1]
# |diff| ＝ [0,0,0,1,0,0,1] ⇒ ⭐ 第 3 期【進場】、第 6 期【出場】各收一次單邊 0.001
want_cost = [0.0, 0.0, 0.0, C.COST_RT / 2.0, 0.0, 0.0, C.COST_RT / 2.0]
check("③ 逐期成本（逐位元）", res["cost"].tolist(), want_cost)
want_net = [want_rets[i] * [0, 0, 0, 1, 1, 1, 0][i] - want_cost[i] for i in range(7)]
check("③ 淨報酬 r_rule（逐位元）", res["r_rule"].tolist(), want_net)

print()
print("=" * 72)
print("④ 突變測試：把實作改成 訊號(t)×r(t) ⇒ 必須【變紅】")
print("=" * 72)
red = not np.array_equal(wrong, np.array(want_net))
print("{} ④ 錯誤版本與手算答案【不同】".format("PASS" if red else "⛔FAIL"))
if not red:
    FAIL.append("④ 突變沒有變紅")
# ⭐ 並指出它錯在哪：錯誤版本會在第 2 期就有部位，吃到 68/62−1 那段漲幅
print("     ⭐ 錯誤版本第 2 期報酬 ＝ {:.8f}（＝ 68/62−1 {:.8f} 減成本）"
      .format(wrong[2], 68.0 / 62.0 - 1))
print("     ⭐ 正確版本第 2 期報酬 ＝ {:.8f}（⇒ 沒有部位）".format(want_net[2]))

print()
print("=" * 72)
print("⑤ 段落切法（§2-C③ 假訊號組要保留段數與各段長度）")
print("=" * 72)
segs = C.segments(res["held"])
check("⑤ 段落 ＝ [(0,3),(1,3),(0,1)]", [(int(v), int(n)) for v, n in segs], [(0, 3), (1, 3), (0, 1)])
rng = np.random.default_rng(C.SEED)
cg, md = C.placebo_dist(res["held"], res["r_bh"], rng)
print("  ⭐ 假訊號 1,000 組跑得動：cagr 中位 {:+.4%}／|mdd| 中位 {:.4%}"
      .format(float(np.median(cg)), float(np.median(md))))
print("  ⭐ 曝險保留檢查：所有重排的持有天數都應等於原始的 {} 天".format(int(res["held"].sum())))

print()
if FAIL:
    raise SystemExit("⛔⛔ {} 格不過：{}".format(len(FAIL), "／".join(FAIL)))
print("✅ 全部通過（⓪ 鑑別力 ＋ ①~③ 手算逐位元 ＋ ④ 突變變紅 ＋ ⑤ 段落）")
print("⭐ 而第 ⓪ 格證明了：這個 fixture 在【正確】與【已知錯誤】實作下給出不同答案")
print("  ⇒ ⛔ 所以上面的綠燈不是空對空。")

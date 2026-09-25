# -*- coding: utf-8 -*-
"""PREREG限價 限價成交判定 fixture（limit_entry.py）。合成資料、手算答案；每條都附【突變版】要被抓到（〈一百一十三〉：先證明分得出來）。

F1  掛價：close ×（1−k%）照 tick 往下取整（含級距邊界、浮點陷阱 99.0／0.1）；tick 表與 research11._tick 相同
F2  成交：最低 ≤ P 即成交；開盤 ＞ P ⇒ 以 P 成交；開盤 ≤ P（開低）⇒ 以開盤成交；最低＝P 剛好成交
F3  漲停開盤：最低 ＞ P ⇒ 不成交；開盤漲停但盤中殺到 ≤ P ⇒ 以 P 成交（自然成立、不另判）
F4  停牌日：佔 5 日的一天、當天不成交，下一個有成交日照判
F5  5 日有效期邊界：第 5 日碰到 ⇒ 成交；第 6 日才碰到 ⇒ 放棄
F6  M0／M0'：開盤漲停 ⇒ M0 放棄、M0' 以開盤買到；停牌 ⇒ 兩者都放棄
F7  無前視突變：隨機改成交日【之後】的全部價格 200 次（另 50 次改未成交者 e+5 以後，共 250） ⇒ 成交日與成交價不變；沒成交者改 e+5 以後的價格 ⇒ 仍沒成交
F8  鑑別力：故意用【當天收盤】判成交（close ≤ P）的突變版 ⇒ 必須在 F2／F3 被抓到（結果不同）
F9  出場引擎：x 收盤跌停 ⇒ 延到下一個開盤非跌停日開盤；x 停牌 ⇒ 同；下市 ⇒ 最後成交收盤了結；ambig ⇒ 量不到
F10 報酬：沒成交＝0（進分母）；成交＝出場還原 ÷（成交未還原 × F）− 1 − 成本；除權息 F 生效
F11 0 報酬輸入 ⇒ D ＝ 0、CI ＝ [0, 0]；平價序列（不扣成本）⇒ 各臂報酬 0 ⇒ D ＝ 0
F12 月分群 SE 與 research11.cl_stats 同值；出口／結果分流
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import limit_entry as LE
from backtest import research11 as R11

N = 40
ok = []


def arrs(o=100.0, l=99.5, c=100.0):
    return np.full(N, o), np.full(N, l), np.full(N, c), np.ones(N, bool)


def close_fill(e, P, ro, rl, rc, trd, days=5):
    """⛔ 突變版：用當天收盤判成交（這是錯的；fixture 要抓到它）。"""
    for t in range(e, min(e + days, len(rl))):
        if trd[t] and rc[t] <= P:
            return t, float(min(ro[t], P))
    return None, None


def check(name, cond):
    assert cond, "⛔ " + name
    ok.append(name)


# ── F1 掛價與 tick ─────────────────────────────
for p in (5.0, 9.99, 10.0, 49.9, 50.0, 99.9, 100.0, 499.0, 500.0, 999.0, 1000.0, 2000.0):
    check(f"F1 tick 表同 research11 @{p}", LE.tick(p) == R11._tick(p))
cases = [(100.0, 1, 99.0), (100.0, 2, 98.0), (100.0, 3, 97.0),       # 99.0／0.1 浮點陷阱
         (50.5, 2, 49.45),                                           # 49.49 ⇒ tick 0.05 ⇒ 49.45
         (9.99, 3, 9.69),                                            # 9.6903 ⇒ 9.69
         (1005.0, 1, 994.0),                                         # 994.95 ⇒ tick 1 ⇒ 994
         (505.0, 1, 499.5),                                          # 499.95 ⇒ tick 0.5 ⇒ 499.5
         (10.1, 1, 9.99),                                            # 9.999 ⇒ tick 0.01 ⇒ 9.99
         (51.0, 2, 49.95),                                           # 49.98 ⇒ 49.95
         (1030.0, 3, 999.0),                                         # 999.1 ⇒ tick 1 ⇒ 999
         (1035.0, 3, 1000.0),                                        # 1003.95 ⇒ tick 5 ⇒ 1000
         (23.45, 1, 23.2),                                           # 23.2155 ⇒ tick 0.05 ⇒ 23.20
         (3.0, 1, 2.97), (7.0, 2, 6.86)]                              # 浮點 floor 會錯成 2.96／6.85（全表 32 例）
for c, k, want in cases:
    got = LE.limit_px(c, k)
    check(f"F1 limit_px({c},{k})={want}", abs(got - want) < 1e-9)
    # 突變：不取整（直接 close×(1−k%)）在非整 tick 的案例要不同
naive = lambda c, k: c * (1 - k / 100)
check("F1 鑑別：不取整版在 50.5×0.98 被抓到", abs(naive(50.5, 2) - 49.45) > 1e-6)
import math
bad_floor = lambda c, k: math.floor(c * (1 - k / 100) / LE.tick(c * (1 - k / 100))) * LE.tick(c * (1 - k / 100))
check("F1 鑑別：浮點 floor 版至少在一個案例被抓到", any(abs(bad_floor(c, k) - w) > 1e-6 for c, k, w in cases))

# ── F2 成交判定與成交價 ─────────────────────────
e, P = 10, 99.0
ro, rl, rc, trd = arrs(100.0, 99.5, 100.0)
check("F2 5 日最低都 ＞ P ⇒ 放棄", LE.fill_limit(e, P, ro, rl, trd) == (None, None))
ro2, rl2 = ro.copy(), rl.copy(); rl2[12] = 98.5                         # 第 3 日盤中碰到、開盤 100 ＞ P
check("F2 開盤 ＞ P、最低 ≤ P ⇒ 以 P 成交", LE.fill_limit(e, P, ro2, rl2, trd) == (12, 99.0))
ro3, rl3 = ro.copy(), rl.copy(); ro3[11] = 98.0; rl3[11] = 97.5          # 第 2 日開低
check("F2 開盤 ≤ P ⇒ 以開盤成交", LE.fill_limit(e, P, ro3, rl3, trd) == (11, 98.0))
rl4 = rl.copy(); rl4[10] = 99.0
check("F2 最低＝P 剛好成交", LE.fill_limit(e, P, ro, rl4, trd) == (10, 99.0))
# F8 鑑別：收盤判的突變版在「盤中碰到、收盤回到 P 之上」要不同
check("F8 鑑別：收盤判突變版在 F2 被抓到", close_fill(e, P, ro2, rl2, rc, trd) != LE.fill_limit(e, P, ro2, rl2, trd))

# ── F3 漲停開盤 ─────────────────────────────
ro5, rl5 = ro.copy(), rl.copy(); ro5[10] = 110.0; rl5[10] = 110.0         # 一價到底漲停
check("F3 漲停鎖死（最低 ＞ P）⇒ 當天不成交", LE.fill_limit(e, P, ro5, rl5, trd) == (None, None))
ro6, rl6, rc6 = ro.copy(), rl.copy(), rc.copy(); ro6[10] = 110.0; rl6[10] = 98.0; rc6[10] = 105.0   # 開漲停、盤中殺到 98、收 105
check("F3 開漲停但盤中 ≤ P ⇒ 以 P 成交", LE.fill_limit(e, P, ro6, rl6, trd) == (10, 99.0))
check("F8 鑑別：收盤判突變版在 F3 被抓到", close_fill(e, P, ro6, rl6, rc6, trd) != LE.fill_limit(e, P, ro6, rl6, trd))

# ── F4 停牌日 ─────────────────────────────
trd7 = trd.copy(); trd7[10] = False; rl7 = rl.copy(); rl7[10] = 90.0; rl7[11] = 98.0   # 停牌日的殘值不得被讀
check("F4 停牌日不成交、下一日照判", LE.fill_limit(e, P, ro, rl7, trd7) == (11, 99.0))
trd8 = trd.copy(); trd8[10:15] = False; rl8 = rl.copy(); rl8[15] = 90.0
check("F4 停牌佔 5 日 ⇒ 全停牌、第 6 日才碰到 ⇒ 放棄", LE.fill_limit(e, P, ro, rl8, trd8) == (None, None))
rl9 = rl.copy(); rl9[11] = np.nan
check("F4 最低缺值 ⇒ 當天不成交", LE.fill_limit(e, P, ro, rl9, trd) == (None, None))

# ── F5 5 日邊界 ─────────────────────────────
rlA = rl.copy(); rlA[14] = 98.0
check("F5 第 5 日（e+4）碰到 ⇒ 成交", LE.fill_limit(e, P, ro, rlA, trd) == (14, 99.0))
rlB = rl.copy(); rlB[15] = 98.0
check("F5 第 6 日（e+5）才碰到 ⇒ 放棄", LE.fill_limit(e, P, ro, rlB, trd) == (None, None))
check("F5 鑑別：有效期 6 日的突變版會成交（被抓到）", LE.fill_limit(e, P, ro, rlB, trd, days=6) == (15, 99.0))

# ── F6 M0／M0' ─────────────────────────────
up = np.zeros(N, bool); up[10] = True
check("F6 M0 開盤漲停 ⇒ 放棄", LE.fill_m0(10, ro5, trd, up) == ("limit_up", None))
check("F6 M0' 開盤漲停 ⇒ 以開盤買到", LE.fill_m0(10, ro5, trd, up, allow_limit_up=True) == ("ok", 110.0))
check("F6 停牌 ⇒ M0、M0' 都放棄", LE.fill_m0(10, ro, trd7, up) == ("halt_in", None) and LE.fill_m0(10, ro, trd7, up, True) == ("halt_in", None))
check("F6 正常 ⇒ 開盤買", LE.fill_m0(10, ro, trd, np.zeros(N, bool)) == ("ok", 100.0))

# ── F7 無前視突變 ─────────────────────────────
rng = np.random.default_rng(20260925)
base = [(ro2, rl2, 12), (ro3, rl3, 11), (ro6, rl6, 10), (ro, rlA, 14)]
nmut = 0
for roX, rlX, t in base:
    want = LE.fill_limit(e, P, roX, rlX, trd)
    for _ in range(50):
        a, b = roX.copy(), rlX.copy(); tr_ = trd.copy()
        a[t + 1:] = rng.uniform(50, 150, N - t - 1); b[t + 1:] = a[t + 1:] * rng.uniform(0.8, 1.0, N - t - 1)
        tr_[t + 1:] = rng.random(N - t - 1) > 0.3
        assert LE.fill_limit(e, P, a, b, tr_) == want; nmut += 1
for _ in range(50):                                     # 沒成交者：改 e+5 以後
    a, b = ro.copy(), rl.copy(); a[15:] = rng.uniform(50, 150, N - 15); b[15:] = 1.0
    assert LE.fill_limit(e, P, a, b, trd) == (None, None); nmut += 1
check(f"F7 無前視：{nmut} 次突變成交日與成交價皆不變", nmut == 250)
# F7 鑑別：一個「偷看 e+5 最低」的突變版要被抓到
peek = lambda e_, P_, ro_, rl_, trd_: LE.fill_limit(e_, P_, ro_, rl_, trd_, days=6)
a, b = ro.copy(), rl.copy(); b[15] = 1.0
check("F7 鑑別：偷看第 6 日的突變版被抓到", peek(e, P, a, b, trd) != LE.fill_limit(e, P, a, b, trd))

# ── F9 出場引擎 ─────────────────────────────
c_adj = np.full(N, 100.0); o_adj = np.full(N, 100.0); dn_c = np.zeros(N, bool); dn_o = np.zeros(N, bool)
H = 20; x = e + H - 1                                     # 29
check("F9 正常 ⇒ x 收盤出", LE.exit_engine(e, H, c_adj, o_adj, trd, dn_c, dn_o, N - 1, "live") == ("ok", x, 100.0))
dc = dn_c.copy(); dc[x] = True; oo = o_adj.copy(); oo[x + 1] = 95.0
check("F9 x 收盤跌停 ⇒ x+1 開盤出", LE.exit_engine(e, H, c_adj, oo, trd, dc, dn_o, N - 1, "live") == ("exit_delayed", x + 1, 95.0))
do = dn_o.copy(); do[x + 1] = True; oo2 = oo.copy(); oo2[x + 2] = 93.0
check("F9 x 收盤跌停、x+1 開盤也跌停 ⇒ x+2 開盤出", LE.exit_engine(e, H, c_adj, oo2, trd, dc, do, N - 1, "live") == ("exit_delayed", x + 2, 93.0))
tr2 = trd.copy(); tr2[x:] = False; cc = c_adj.copy(); cc[x - 1:] = 88.0     # ffill 後的收盤＝最後成交
check("F9 x 起不再成交、已下市 ⇒ 最後成交收盤了結", LE.exit_engine(e, H, cc, o_adj, tr2, dn_c, dn_o, x - 1, "delisted_official") == ("delist_settled", x + 1, 88.0))
check("F9 ambig ⇒ 量不到", LE.exit_engine(e, H, cc, o_adj, tr2, dn_c, dn_o, x - 1, "ambig")[0] == "delist_ambig")
tr3 = trd.copy(); tr3[x] = False
check("F9 x 停牌 ⇒ 下一日開盤出", LE.exit_engine(e, H, c_adj, oo, tr3, dn_c, dn_o, N - 1, "live") == ("exit_delayed", x + 1, 95.0))
check("F9 超出日曆 ⇒ beyond_cal", LE.exit_engine(30, H, c_adj, o_adj, trd, dn_c, dn_o, N - 1, "live")[0] == "beyond_cal")

# ── F10 報酬 ─────────────────────────────
C = LE.COST_RT
check("F10 沒成交 ⇒ 0", LE.arm_return(None, 1.0, 120.0) == 0.0)
check("F10 成交 99、出 110（F＝1）", abs(LE.arm_return(99.0, 1.0, 110.0) - (110 / 99 - 1 - C)) < 1e-15)
# 除權息：成交日 F＝0.95（之後有 5% 配息），出場還原價 ＝ 未還原 × 1 ⇒ 進場還原 99×0.95
check("F10 除權息 F 生效", abs(LE.arm_return(99.0, 0.95, 100.0) - (100 / (99 * 0.95) - 1 - C)) < 1e-15)
# 放棄進分母：兩筆訊號，L 只成交一筆
rL = [LE.arm_return(99.0, 1.0, 110.0), LE.arm_return(None, 1.0, 130.0)]
check("F10 放棄＝0 算進分母（E ＝ 成交那筆 ÷ 2）", abs(np.mean(rL) - (110 / 99 - 1 - C) / 2) < 1e-15)

# ── F11 0 報酬 ⇒ D ＝ 0 ─────────────────────────
z = np.zeros(300); g = np.repeat(np.arange(100), 3)
m_, se_, lo_, hi_, nm_ = LE.cluster_mean(z - z, g)
check("F11 0 報酬輸入 ⇒ D＝0、CI＝[0,0]", m_ == 0.0 and se_ == 0.0 and lo_ == 0.0 and hi_ == 0.0)
# 平價序列、不扣成本：M0 與 L1 都成交或放棄，報酬皆 0
flat_o, flat_l, flat_c, flat_t = np.full(N, 100.0), np.full(N, 100.0), np.full(N, 100.0), np.ones(N, bool)
PL = LE.limit_px(100.0, 1)
tL, fL = LE.fill_limit(10, PL, flat_o, flat_l, flat_t)
st0, f0 = LE.fill_m0(10, flat_o, flat_t, np.zeros(N, bool))
_, _, px = LE.exit_engine(10, 20, flat_c, flat_o, flat_t, np.zeros(N, bool), np.zeros(N, bool), N - 1, "live")
rM = LE.arm_return(f0, 1.0, px, cost=0.0); rLx = LE.arm_return(fL, 1.0, px, cost=0.0)
check("F11 平價不扣成本 ⇒ M0＝0、L1（放棄）＝0 ⇒ D＝0", rM == 0.0 and rLx == 0.0 and (rLx - rM) == 0.0)
check("F11 鑑別：非零輸入 ⇒ D ≠ 0", LE.cluster_mean(np.r_[np.ones(3), z[3:]], g)[0] != 0.0)

# ── F12 月分群 SE 與出口 ─────────────────────────
rng2 = np.random.default_rng(7); xx = rng2.normal(0.01, 0.1, 500); gg = rng2.integers(0, 109, 500)
m_, se_, lo_, hi_, nm_ = LE.cluster_mean(xx, gg); cs = R11.cl_stats(xx, gg)
check("F12 cluster_mean ＝ research11.cl_stats", abs(m_ - cs["mean"]) < 1e-15 and abs(se_ - cs["se"]) < 1e-15 and nm_ == cs["months"])
check("F12 出口③ 含 0 ⇒ 結果①", LE.verdict(0.01, -0.01, 0.03, 109, 2881) == ("出口③", "結果①（CI 含 0 ⇒ 分不出來／測不出）"))
check("F12 出口③ 負 ⇒ 結果③", LE.verdict(-0.02, -0.03, -0.01, 109, 2881)[1].startswith("結果③"))
check("F12 出口③ 正 ⇒ 結果②", LE.verdict(0.02, 0.01, 0.03, 109, 2881)[1].startswith("結果②"))
check("F12 n_eff 99 ⇒ 出口②", LE.verdict(0.02, 0.01, 0.03, 99, 2881)[0] == "出口②")
check("F12 n_eff 29 ⇒ 出口①", LE.verdict(0.02, 0.01, 0.03, 29, 2881)[0] == "出口①")

for i, nm in enumerate(ok, 1):
    print(f"✅ {i:02d} {nm}")
print(f"== selftest_limit_entry：{len(ok)}／{len(ok)} 過 ==")

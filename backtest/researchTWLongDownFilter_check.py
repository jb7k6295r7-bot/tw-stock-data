# -*- coding: utf-8 -*-
"""長期下跌濾網（產業 seq96／裁定 seq498）——最少 fixture 自測（⛔ 不算任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchTWLongDownFilter_check.py

A 趨勢真值表：收盤<均線 × 均線<20根前均線 四組合；相等（收盤＝均線、均線＝20 根前均線）⇒ 不算長期下跌（★4）。
B 暖身邊界：有效根 N+19 ⇒ 不判；N+20 ⇒ 可判（年線 240、半年線 120 各測）。
C 回看壞根（★5）：窗內壞根 ⇒ 不判；壞根恰在窗外（窗首根與前一根之間）⇒ 可判。
D 趨勢 PIT：截斷到評估根重算＝全量；評估根後資料竄改不影響。
E 新低（★10）：新低在 k−2 ⇒ 有；在 k−5 ⇒ 主讀法沒有、另一讀法有；平手算新低；64 根邊界。
F 放行（★9）：站回均線當根即放行；途中壞根 ⇒ 截尾。
G 財報 ★1：無上傳紀錄的期別在法定評估日前不可用、當天起可用；有紀錄 ⇒ 上傳日 < 評估日才可用。
H 財報 PIT：真實資料截斷到評估日（FairValue asof）重算＝全量（主讀法，數個月份）。
I 原版一致：原版 24 個評估日上，主讀法分組＝核對版 orig/detail.csv（市值 ≥300 億者；只讀非報酬欄）。
（2026-11-08 正式跑加）
J 正式跑閘門：--formal --ruling seq499 兩個都要，否則拒跑（含實際執行兩支正式檔不帶旗標）。
K 持有報酬 hold_ret：壞根不計、下市用最後一根、日曆不夠不算。
L bootstrap：97.5%、種子固定、群集抽樣。
M 判語只有「通過（暫定）」與「測不出」；兩版都過採半年線。
N 每月表：不判留在全部可買、主量只取剔除組 ≥3 檔的月份、中位數差。
"""
import os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import researchTWLongDownFilter_freq as M     # noqa: E402

FAILS, PASSES = [], []


def ok(cond, name):
    (PASSES if cond else FAILS).append(name); print(('PASS ' if cond else 'FAIL ') + name, flush=True)


def code(px, N, bad=None, k=None):
    px = np.asarray(px, float)
    bad = np.zeros(len(px), bool) if bad is None else bad
    k = len(px) - 1 if k is None else k
    return M.longdown_code(px, M.ma_arr(px, N), M.cumbad(bad), k, N)


# ═════════ A 真值表 ═════════
for N in (240, 120):
    n = N + 60
    # 1) 長期下跌：持續下跌（收盤<均線、均線下彎）
    ok(code(1000 - np.arange(n), N) == 1, f'A1[{N}] 持續下跌 ⇒ 長期下跌')
    # 2) 收盤>均線、均線上揚 ⇒ 不是
    ok(code(100 + np.arange(n), N) == 0, f'A2[{N}] 持續上漲 ⇒ 不是')
    # 3) 收盤<均線但均線上揚：長漲後最後一根急跌
    s = 100.0 + np.arange(n); s[-1] = 50.0
    ma = M.ma_arr(s, N)
    ok(s[-1] < ma[-1] and ma[-1] > ma[-1 - 20] and code(s, N) == 0, f'A3[{N}] 收盤<均線、均線上揚 ⇒ 不是')
    # 4) 收盤>均線但均線下彎：長跌後最後一根急拉
    s = 1000.0 - np.arange(n); s[-1] = s[-2] + N / 2 + 10     # 剛好站上均線、不足以把均線拉成上揚
    ma = M.ma_arr(s, N)
    ok(s[-1] > ma[-1] and ma[-1] < ma[-1 - 20] and code(s, N) == 0, f'A4[{N}] 收盤>均線、均線下彎 ⇒ 不是')
    # 5) 相等：常數序列（收盤＝均線、均線＝20 根前均線）
    ok(code(np.full(n, 100.0), N) == 0, f'A5[{N}] 收盤＝均線且均線持平 ⇒ 不是（嚴格 <）')
    # 6) 均線＝20 根前均線、收盤<均線：s[k]＝80 進窗、s[k−N]＝80 在 20 根前的窗內 ⇒ 兩窗總和相同（整數，精確相等）
    s = np.full(n, 100.0); kk = n - 1; s[kk] = 80.0; s[kk - N] = 80.0
    ma = M.ma_arr(s, N)
    ok(ma[kk] == ma[kk - 20] and s[kk] < ma[kk] and code(s, N) == 0, f'A6[{N}] 均線＝20 根前均線（收盤<均線）⇒ 不是')

# ═════════ B 暖身 ═════════
for N in (240, 120):
    ok(code(1000 - np.arange(N + 19), N) == M.SHORT, f'B1[{N}] 有效根 {N + 19} ⇒ 不判（K 棒不足）')
    ok(code(1000 - np.arange(N + 20), N) == 1, f'B2[{N}] 有效根 {N + 20} ⇒ 可判')

# ═════════ C 回看壞根 ═════════
for N in (240, 120):
    n = N + 100; px = 1000 - np.arange(n); k = n - 1; W = N + 20
    b = np.zeros(n, bool); b[k - W + 2] = True     # 窗內（窗首根之後一根與窗首根之間）
    ok(code(px, N, b) == M.BRK, f'C1[{N}] 回看窗內壞根 ⇒ 不判')
    b = np.zeros(n, bool); b[k - W + 1] = True     # 窗首根與前一根之間：窗外
    ok(code(px, N, b) == 1, f'C2[{N}] 壞根恰在窗外 ⇒ 可判')
    b = np.zeros(n, bool); b[k] = True
    ok(code(px, N, b) == M.BRK, f'C3[{N}] 壞根在評估根 ⇒ 不判')
    ok(M.longdown_code_nobrk(px.astype(float), M.ma_arr(px, N), k, N) == 1, f'C4[{N}] ★5 另一讀法照判')

# ═════════ D 趨勢 PIT ═════════
rng = np.random.default_rng(1)
px = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 1500)))
bad = rng.random(1500) < 0.002
nd = 0
for N in (240, 120):
    full_ma = M.ma_arr(px, N); cbf = M.cumbad(bad)
    for k in range(300, 1400, 37):
        a = M.longdown_code(px, full_ma, cbf, k, N)
        cut = px[:k + 1]; b = M.longdown_code(cut, M.ma_arr(cut, N), M.cumbad(bad[:k + 1]), k, N)
        alt = px.copy(); alt[k + 1:] *= 7; c = M.longdown_code(alt, M.ma_arr(alt, N), cbf, k, N)
        sc = px * 3.3; e = M.longdown_code(sc, M.ma_arr(sc, N), cbf, k, N)     # ★6 全段同乘常數
        nd += int(not (a == b == c == e))
ok(nd == 0, f'D1 趨勢截斷重算＝全量、未來竄改不影響、全段乘常數不影響（不同 {nd}）')
nl = M.newlow_flags(px); nlc = M.newlow_flags(px[:900])
ok((nl[:900] == nlc).all(), 'D2 新低旗標只用過去 60 根（截斷＝全量）')

# ═════════ E 新低 ═════════
base = np.full(200, 100.0); k = 199; cb0 = M.cumbad(np.zeros(200, bool))
s = base.copy(); s[k - 2] = 90.0
ok(M.newlow_code(M.newlow_flags(s), cb0, k, True) == 1, 'E1 新低在 k−2 ⇒ 有新低')
s = 100.0 + np.arange(200.0); s[k - 5] = 50.0
ok(M.newlow_code(M.newlow_flags(s), cb0, k, True) == 0 and M.newlow_code(M.newlow_flags(s), cb0, k, False) == 1,
   'E2 新低在 k−5 ⇒ 主讀法沒有、另一讀法（前 5 根不含評估日）有')
ok(M.newlow_code(M.newlow_flags(base), cb0, k, True) == 1, 'E3 平手（常數序列）算新低')
s = 100.0 + np.arange(64.0)
ok(M.newlow_code(M.newlow_flags(s), M.cumbad(np.zeros(64, bool)), 63, True) == 0, 'E4 64 根可判')
ok(M.newlow_code(M.newlow_flags(s[:63]), M.cumbad(np.zeros(63, bool)), 62, True) == M.SHORT, 'E5 63 根不判')


# ═════════ F 放行 ═════════
class FS_:
    def __init__(self, px, bad):
        self.px = np.asarray(px, float); self.bad = bad; self.cb = M.cumbad(bad); self._m = {}; self._nl = None
    def ma(self, N):
        if N not in self._m: self._m[N] = M.ma_arr(self.px, N)
        return self._m[N]
    @property
    def nl(self):
        if self._nl is None: self._nl = M.newlow_flags(self.px)
        return self._nl


N = 120
px = np.concatenate([1000 - np.arange(300.0), np.full(5, 690.0), [5000.0], np.full(50, 5000.0)])
k = 299; st = FS_(px, np.zeros(len(px), bool))
ok(code(px, N, k=k) == 1, 'F0 評估根長期下跌')
ri = M.release_info(st, k, N)
ok(ri['rel_main'] == 'released' and ri['rel_main_bars'] == 6, f'F1 站回均線當根放行（{ri}）')
b = np.zeros(len(px), bool); b[303] = True
ri = M.release_info(FS_(px, b), k, N)
ok(ri['rel_main'] == 'censored', 'F2 放行前遇壞根 ⇒ 截尾')
t, why = M.delayed_entry(FS_(1000 - np.arange(300.0), np.zeros(300, bool)), 250)
ok(t is None and why == 'never', 'F3 一路創新低 ⇒ 延後版找不到進場根')

# ═════════ J 正式跑閘門（裁定 seq499：--formal --ruling seq499 兩個都要）═════════
import researchTWLongDownFilter as FM     # noqa: E402
ok(isinstance(FM.gate([]), tuple), 'J1 無參數 ⇒ 拒跑')
ok(isinstance(FM.gate(['--formal']), tuple), 'J2 只給 --formal ⇒ 拒跑')
ok(isinstance(FM.gate(['--ruling', 'seq499']), tuple), 'J3 只給 --ruling seq499 ⇒ 拒跑')
ok(isinstance(FM.gate(['--formal', '--ruling', 'seq498']), tuple), 'J4 --ruling seq498（舊號）⇒ 拒跑')
ok(isinstance(FM.gate(['--formal', '--ruling', 'seq499', '--x']), tuple), 'J5 多餘參數 ⇒ 拒跑')
ok(FM.gate(['--formal', '--ruling', 'seq499']) == 'formal', 'J6 --formal --ruling seq499 ⇒ 准跑')
import subprocess  # noqa: E402
for fn in ('researchTWLongDownFilter.py', 'researchUSLongDownFilter.py'):
    pr = subprocess.run([sys.executable, os.path.join(HERE, fn)], capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=os.path.dirname(HERE)), timeout=120)
    ok(pr.returncode != 0 and '拒跑' in (pr.stderr + pr.stdout), f'J7 {fn} 不帶旗標實際執行 ⇒ 非零結束且拒跑')
import importlib  # noqa: E402
US = importlib.import_module('researchUSLongDownFilter')
ok(US.gate is FM.gate, 'J8 美股正式檔用同一個閘門函式')


# ═════════ K 持有報酬（hold_ret：壞根不計、下市用最後一根、日曆不夠不算）═════════
class KS_:
    def __init__(self, px, pos, bad):
        self.px = np.asarray(px, float); self.pos = np.asarray(pos); self.cb = M.cumbad(bad)


ks = KS_([10, 11, 12, 13, 14, 15], [0, 1, 2, 3, 4, 5], np.zeros(6, bool))
r, s_ = FM.hold_ret(ks, 1, 3, 100)
ok(abs(r - (14 / 11 - 1)) < 1e-12 and s_ == 'ok', 'K1 第 1 根進、+3 出 ⇒ 14/11−1')
ok(np.isnan(FM.hold_ret(ks, 1, 3, 4)[0]) and FM.hold_ret(ks, 1, 3, 4)[1] == 'cal', 'K2 出場日超出日曆 ⇒ 不算')
b = np.zeros(6, bool); b[3] = True
ok(FM.hold_ret(KS_(ks.px, ks.pos, b), 1, 3, 100)[1] == 'holdbad', 'K3 持有窗內壞根 ⇒ 不計')
b = np.zeros(6, bool); b[1] = True
ok(FM.hold_ret(KS_(ks.px, ks.pos, b), 1, 3, 100)[1] == 'ok', 'K4 壞根恰在進場根（窗外）⇒ 照算')
r, s_ = FM.hold_ret(ks, 3, 10, 100)
ok(abs(r - (15 / 13 - 1)) < 1e-12 and s_ == 'delisted', 'K5 出場前已下市 ⇒ 用最後一根')
ks2 = KS_([10, 20, 30], [0, 1, 5], np.zeros(3, bool))
ok(abs(FM.hold_ret(ks2, 0, 3, 100)[0] - 1.0) < 1e-12, 'K6 出場日無成交 ⇒ 用之前最後一根')

# ═════════ L bootstrap（97.5%、種子固定、群集）═════════
v = np.full(10, 0.02)
pt, lo, hi, nc = FM.boot_ci(v, range(10))
ok(abs(pt - 0.02) < 1e-15 and abs(lo - 0.02) < 1e-15 and abs(hi - 0.02) < 1e-15 and nc == 10, 'L1 常數 ⇒ CI 退化為該常數')
rng = np.random.default_rng(5); v = rng.normal(0.01, 0.05, 40)
a1 = FM.boot_ci(v, range(40)); a2 = FM.boot_ci(v, range(40))
ok(a1 == a2, 'L2 同種子重跑結果相同')
a95 = FM.boot_ci(v, range(40), level=0.95)
ok(a1[1] < a95[1] and a1[2] > a95[2], 'L3 97.5% CI 比 95% 寬')
ok(FM.CI_LEVEL == 0.975 and FM.NBOOT == 10000 and isinstance(FM.SEED, int), 'L4 97.5%、10,000 次、種子寫死')
yr = FM.boot_ci([1, 1, 3, 3], ['a', 'a', 'b', 'b'])
ok(yr[3] == 2 and abs(yr[0] - 2) < 1e-12, 'L5 群集：同群值一起抽')

# ═════════ M 判語（只有「通過（暫定）」與「測不出」；兩版都過採半年線）═════════
ok(FM.verdict(0.03, 0.01, 0.02, 0.04, 0.01) == '通過（暫定）', 'M1 全部條件成立 ⇒ 通過（暫定）')
ok(FM.verdict(0.03, -0.001, 0.02, 0.04, 0.01) == '測不出', 'M2 CI 下緣 ≤ 0 ⇒ 測不出')
ok(FM.verdict(0.03, 0.01, -0.02, 0.04, 0.01) == '測不出', 'M3 前段 ≤ 0 ⇒ 測不出')
ok(FM.verdict(0.03, 0.01, 0.02, -0.04, 0.01) == '測不出', 'M4 後段 ≤ 0 ⇒ 測不出')
ok(FM.verdict(0.03, 0.01, 0.02, 0.04, -0.01) == '測不出', 'M5 中位數差方向相反 ⇒ 測不出')
ok(FM.verdict(-0.05, -0.08, -0.02, -0.04, -0.01) == '測不出', 'M6 全負 ⇒ 仍寫測不出（不寫劣於）')
ok(FM.verdict(0.03, 0.01, np.nan, 0.04, 0.01) == '測不出', 'M7 有 NaN ⇒ 測不出')
P_, F_ = FM.VERDICT_PASS, FM.VERDICT_FAIL
ok(FM.adopt({'年線': P_, '半年線': P_}) == '半年線' and FM.adopt({'年線': P_, '半年線': F_}) == '年線'
   and FM.adopt({'年線': F_, '半年線': P_}) == '半年線' and FM.adopt({'年線': F_, '半年線': F_}) is None, 'M8 採用規則')

# ═════════ N 每月表與主量（不判留在全部可買、只取剔除組 ≥3 檔月份）═════════
rows = []


def addm(E, codes, rets):
    for i, (c_, r_) in enumerate(zip(codes, rets)):
        rows.append(dict(E=E, stock_id=f'S{i}', year=int(E[:4]), segment=FM.seg_of(E), ld=c_, R=r_))


addm('2021-03-01', [0, 0, 1, 1, 1, M.BRK], [0.10, 0.20, -0.1, -0.2, 0.0, 0.5])   # 剔除 3 檔
addm('2024-03-01', [0, 0, 1, 1], [0.10, 0.30, 0.0, 0.0])                          # 剔除 2 檔
addm('2024-04-01', [0, 1, 1, 1, 0], [0.10, -0.1, np.nan, 0.0, 0.3])               # 剔除 3 檔（一筆不可算）
NB = pd.DataFrame(rows)
NT = FM.month_table(NB, 'ld', 'R')
r0 = NT.set_index('E').loc['2021-03-01']
ok(abs(r0['diff'] - (0.15 - np.mean([0.10, 0.20, -0.1, -0.2, 0.0, 0.5]))) < 1e-12 and r0.n_skip == 1 and r0.n_all == 6,
   'N1 不判留在全部可買、不進濾網組')
ok(FM.main_months(NT) == {'2021-03-01', '2024-04-01'}, 'N2 主量只取剔除組 ≥3 檔的月份（檔數不看報酬可不可算）')
r2 = NT.set_index('E').loc['2024-04-01']
ok(abs(r2['diff'] - (0.2 - np.mean([0.10, -0.1, 0.0, 0.3]))) < 1e-12 and abs(r2['diff_med'] - (0.2 - 0.05)) < 1e-12,
   'N3 不可算筆不進平均；中位數差＝濾網中位 − 全部中位')
cc = FM.cell(NT, FM.main_months(NT))
ok(cc['n_front'] == 1 and cc['n_back'] == 1 and abs(cc['main'] - NT[NT.E.isin(FM.main_months(NT))]['diff'].mean()) < 1e-12,
   'N4 主量＝主量月份每月差平均；前後段分開')


# ═════════ G／H／I 真實資料 ═════════
from researchTWCheapTrend_fv import FairValue  # noqa: E402
SNAP = M.SNAP
full = M.FairValueMonthly(SNAP)
# G：挑一筆有上傳紀錄的 Q1，暫刪紀錄
key = next(kk for kk in full.UP if kk[2] == '1' and kk[1] == '2023' and (kk[0], '2023Q1') in full.FS)
u = full.UP.pop(key)
s_, y_, q_ = key[0], 2023, 1
g1 = (not full.available(s_, y_, q_, '2023-05-15')) and full.available(s_, y_, q_, '2023-05-16')
full.mode = 'orig'; g2 = full.available(s_, y_, q_, '2023-04-03'); full.mode = 'upload'
full.UP[key] = u
g3 = (full.available(s_, y_, q_, u[:10]) is False) and full.available(s_, y_, q_, (pd.Timestamp(u[:10]) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
ok(g1, 'G1 無上傳紀錄：法定評估日（5/16）前不可用、當天起可用')
ok(g2, 'G2 另一讀法（原版 available）：無紀錄即視為已公告')
ok(g3, 'G3 有紀錄：上傳當天不可用、次日可用（嚴格 <）')
ok(M.kind_upload('2023-05-02') == ('Q1', 2023) and M.kind_upload('2024-01-02') == ('Q4', 2024)
   and M.kind_statutory('2023-05-02') == ('Q4', 2023) and M.kind_statutory('2024-01-02') == ('Q3', 2023)
   and M.kind_statutory('2023-11-15') == ('Q3', 2023), 'G4 期別起點對應（主讀法／另一讀法）')

# H：PIT
pit_n = pit_bad = 0
for E in ('2020-07-01', '2022-12-01', '2024-06-03', '2025-10-01'):
    km, ey = M.kind_upload(E)
    smp = [s for s in full.PX if E in full.PX[s].index][:2000]
    cand = []
    for s in smp:
        r = full.fair_at(s, E, km, ey)
        if r is not None and r['pass_q'] == 1: cand.append(s)
        if len(cand) >= 40: break
    cut = M.FairValueMonthly(SNAP, asof=E, ids=cand)
    for s in cand:
        a = full.fair_at(s, E, km, ey); b = cut.fair_at(s, E, km, ey); pit_n += 1
        fa = (a['pass_q'], a['group_E'], round(a['fair'], 6) if pd.notna(a['fair']) else None)
        fb = (b['pass_q'], b['group_E'], round(b['fair'], 6) if pd.notna(b['fair']) else None)
        pit_bad += int(fa != fb)
ok(pit_n > 0 and pit_bad == 0, f'H1 財報 PIT：截斷到評估日重算＝全量（{pit_n} 筆，不同 {pit_bad}）')

# I：原版一致
det = pd.read_csv(os.path.join(HERE, 'twfv_recheck', 'orig', 'detail.csv'), dtype={'date': str, 'stock_id': str},
                  usecols=['date', 'stock_id', 'pass_q', 'group'])
det['group'] = det['group'].fillna('')
n = mism = mism_alt = 0
for E, kind, ey in full.eval_dates(2020, 2025):
    km, eym = M.kind_upload(E); ka, eya = M.kind_statutory(E)
    for r0 in det[det.date == E].itertuples(index=False):
        full.mode = 'upload'; a = full.fair_at(r0.stock_id, E, km, eym)
        full.mode = 'orig'; b = full.fair_at(r0.stock_id, E, ka, eya); full.mode = 'upload'
        n += 1
        mism += int(a is None or a['group_E'] != r0.group)
        mism_alt += int(b is None or b['group_E'] != r0.group)
ok(n > 0 and mism == 0, f'I1 原版 24 評估日：主讀法分組＝orig/detail.csv（{n} 筆，不同 {mism}）')
ok(n > 0 and mism_alt == 0, f'I2 原版 24 評估日：另一讀法分組＝orig/detail.csv（{n} 筆，不同 {mism_alt}）')

print(f'\n=== {len(PASSES)} PASS, {len(FAILS)} FAIL ===')
for f in FAILS: print('FAIL', f)
sys.exit(1 if FAILS else 0)

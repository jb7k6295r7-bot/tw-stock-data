# -*- coding: utf-8 -*-
"""便宜＋趨勢轉強 台股 seq1——自測（fixture＋PIT；⛔ 不算任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTWCheapTrend_check

A 趨勢四態（合成序列）：T0～T4 各一個 fixture、16 種布林組合真值表、互斥＋涵蓋、20 日斜率（只看第 20 根前）、
  嚴格 >（相等算線下／下彎）、暖身 269／270 根、與逐根暴力算一致、等價檢查「轉強 ⇔ 收盤 > MA60」。
B 壞根：缺 ≥5 日、跳空無事件、跳空有事件（不算）、回看窗邊界。
C PIT：評估日合理價只用評估日前可得資料（真實資料截斷到評估日重算＝全量；評估日後資料竄改不影響）；
  趨勢在判日只用判日（含）前資料（截斷重算＝全量）。
D 與回測核對版輸出一致：2020～2025 評估日、核對版 detail.csv 裡市值 ≥300 億者，pass_q／fair／分組逐筆相同（只讀非報酬欄）。
E 正式跑閘門：缺 --ruling seq482、錯號、與 --dry 併用 ⇒ 拒跑。
"""
import os, sys, subprocess
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import researchTWCheapTrend as M                     # noqa: E402
from researchTWCheapTrend_fv import FairValue        # noqa: E402

FAILS, PASSES = [], []
def ok(cond, name):
    (PASSES if cond else FAILS).append(name); print(('PASS ' if cond else 'FAIL ') + name)


def brute(c):
    """逐根照登錄文字算（不用 rolling）。"""
    n = len(c); out = np.full(n, -1)
    def ma(k, L): return np.mean(c[k - L + 1:k + 1]) if k - L + 1 >= 0 else np.nan
    for k in range(n):
        if k + 1 < 270: continue
        m60, m250 = ma(k, 60), ma(k, 250); m60p, m250p = ma(k - 20, 60), ma(k - 20, 250)
        a60, a250, u60, u250 = c[k] > m60, c[k] > m250, m60 > m60p, m250 > m250p
        if a60 and u60 and a250: s = 1
        elif (a60 and not u60) or (a60 and not a250): s = 2
        elif (not a60) and a250 and u250: s = 3
        elif (not a60) and (not a250) and (not u60) and (not u250): s = 4
        else: s = 0
        out[k] = s
    return out


def last_state(c): return int(M.trend_states(np.asarray(c, float))['state'][-1])


# ═════════ A ═════════
t = np.arange(400)
up = 100 * 1.002 ** t
down = 100 * 0.998 ** t
ok(last_state(up) == 1, 'A1 T1 多頭：穩定上漲 400 根 ⇒ T1')
ok(last_state(down) == 4, 'A2 T4 空頭：穩定下跌 400 根 ⇒ T4')
# T2：長跌後急拉（MA60 線上、MA250 線下）
s2 = np.concatenate([100 * 0.99 ** np.arange(350), 100 * 0.99 ** 349 * 1.02 ** np.arange(1, 31)])
tr = M.trend_states(s2); k = len(s2) - 1
ok(tr['state'][k] == 2 and s2[k] > tr['ma60'][k] and s2[k] < tr['ma250'][k] and tr['ma60'][k] > tr['ma60'][k - 20],'A3 T2 剛轉強：長跌後急拉 ⇒ T2（MA60 線上、MA250 線下）')
# T2 另一支：MA60 線上但下彎（且 MA250 線上）
s2b = np.concatenate([100 * 1.002 ** np.arange(300), 100 * 1.002 ** 299 * 0.995 ** np.arange(1, 61),
                      np.full(8, 100 * 1.002 ** 299 * 0.995 ** 60 * 1.25)])
tr = M.trend_states(s2b); k = len(s2b) - 1
ok(tr['state'][k] == 2 and tr['above60'][k] and tr['ma60'][k] <= tr['ma60'][k - 20] and s2b[k] > tr['ma250'][k],
   'A4 T2 剛轉強：MA60 線上但下彎（MA250 線上）⇒ T2')
# T3：長多後短回檔跌破 MA60、仍在上揚的 MA250 之上
s3 = np.concatenate([100 * 1.003 ** np.arange(380), 100 * 1.003 ** 379 * 0.99 ** np.arange(1, 13)])
tr = M.trend_states(s3); k = len(s3) - 1
ok(tr['state'][k] == 3, 'A5 T3 長多回檔 ⇒ T3')
# T0：MA60 線下、MA250 線下，但 MA60 上揚（反彈後再跌）
s0 = np.concatenate([100 * 0.995 ** np.arange(300), 100 * 0.995 ** 299 * 1.006 ** np.arange(1, 51)])
s0 = np.concatenate([s0, s0[-1] * 0.96 ** np.arange(1, 9)])
tr = M.trend_states(s0); k = len(s0) - 1
ok(tr['state'][k] == 0 and s0[k] < tr['ma60'][k] and s0[k] < tr['ma250'][k] and tr['ma60'][k] > tr['ma60'][k - 20],
   'A6 T0 其他：雙線下但 MA60 上揚 ⇒ T0')
# 真值表
truth = {}
for a60 in (0, 1):
    for u60 in (0, 1):
        for a250 in (0, 1):
            for u250 in (0, 1):
                if a60 and u60 and a250: e = 1
                elif a60: e = 2
                elif a250 and u250: e = 3
                elif (not a250) and (not u60) and (not u250): e = 4
                else: e = 0
                got = int(M.classify(np.array([bool(a60)]), np.array([bool(u60)]), np.array([bool(a250)]), np.array([bool(u250)]))[0])
                truth[(a60, u60, a250, u250)] = (e, got)
ok(all(e == g for e, g in truth.values()), 'A7 16 種布林組合真值表（依序判、互斥）')
# 隨機序列：與暴力算一致、互斥涵蓋、轉強⇔收盤>MA60
rng = np.random.default_rng(7); agree = True; equiv = True; cover = True
for i in range(30):
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 420)))
    trs = M.trend_states(c); st = trs['state']; b = brute(c)
    agree &= bool((st == b).all())
    j = st >= 0
    cover &= bool(np.isin(st[j], [0, 1, 2, 3, 4]).all())
    equiv &= bool((np.isin(st[j], [1, 2]) == (c[j] > trs['ma60'][j])).all())
ok(agree, 'A8 30 條隨機序列逐根＝暴力照字面算')
ok(cover, 'A9 每根恰一態（0～4），互斥涵蓋')
ok(equiv, 'A10 等價檢查（seq377）：轉強(T1∪T2) ⇔ 收盤 > MA60，逐根全等 ⇒ 主格退化為「收盤 vs MA60」')
# 20 日斜率：只動第 k−79 根（只影響 MA60(k−20)）
c = 100 * 1.002 ** np.arange(400); k = 399
base = M.trend_states(c)
c2 = c.copy(); c2[k - 79] = c[k - 79] * 5         # MA60(k−20) 拉高 ⇒ 下彎（MA250 仍在收盤下）
t2 = M.trend_states(c2)
c3 = c.copy(); c3[k - 80] = c[k - 80] * 5         # 只影響 MA60(k−21) 以前 ⇒ 不變
t3 = M.trend_states(c3)
ok(base['state'][k] == 1 and t2['state'][k] == 2 and t3['state'][k] == 1,
   'A11 20 日斜率：比的是恰好第 20 根前的 MA60（動 k−79 翻成 T2、動 k−80 不變）')
# 嚴格 >：常數序列 ⇒ 收盤＝均線＝線下、均線持平＝下彎 ⇒ T4
ok(last_state(np.full(300, 50.0)) == 4, 'A12 嚴格 >：收盤＝均線算線下、均線持平算下彎（常數序列 ⇒ T4）')
# 暖身
ok(last_state(up[:269]) == -1 and last_state(up[:270]) == 1, 'A13 暖身：269 根不可判、270 根（含判日）可判')

# ═════════ B ═════════
dates = np.array([f'2020-01-{d:02d}' for d in range(1, 11)])
pos = np.array([0, 1, 2, 8, 9, 10, 11, 12, 13, 14])          # 第 3 根前缺 5 日
rc = np.array([10, 10, 10, 10, 10, 20, 20, 20, 9, 9], float)  # 第 5 根 ×2（無事件）、第 8 根 ×0.45（有事件）
adj = pd.DataFrame(dict(date=['2020-01-09'], factor=[0.45]))
bad = M.bad_bars(dates, pos, rc, adj)
ok(bad[3] and bad[5] and not bad[8] and bad.sum() == 2, 'B1 壞根：缺≥5日、跳空無事件算；跳空有事件（且比值相符）不算')
pos4 = np.array([0, 1, 2, 7, 8, 9, 10, 11, 12, 13])          # 缺 4 日 ⇒ 不算
ok(not M.bad_bars(dates, pos4, np.full(10, 10.0), adj.iloc[:0])[3], 'B2 缺 4 日不算壞根')
adj_ph = pd.DataFrame(dict(date=['2020-01-05'], factor=[0.5]))  # 事件說減半、價格沒動 ⇒ 幽靈
ok(M.bad_bars(dates, pos, np.full(10, 10.0), adj_ph)[4], 'B3 幽靈事件（事件根比值偏離 ±10.5%）算壞根')

# ═════════ C、D 用真實快照 ═════════
SNAP = M.SNAP
assert open(os.path.join(SNAP, '.commit')).read().strip() == M.SNAP_COMMIT
det = pd.read_csv(os.path.join(HERE, 'twfv_recheck', 'orig', 'detail.csv'), dtype={'stock_id': str},
                  usecols=['date', 'stock_id', 'pass_q', 'fair', 'mult', 'group'])     # ⛔ 只讀非報酬欄
full = FairValue(SNAP)
evs = full.eval_dates(2020, 2025)
# D
mism = 0; n = 0
for E, kind, ey in evs:
    for r in det[det.date == E].itertuples():
        x = full.fair_at(r.stock_id, E, kind, ey); n += 1
        if x is None: mism += 1; continue
        same_q = int(x['pass_q']) == int(r.pass_q)
        same_f = (pd.isna(x['fair']) and pd.isna(r.fair)) or (pd.notna(x['fair']) and pd.notna(r.fair) and abs(x['fair'] - r.fair) <= 1e-6 * max(1, abs(r.fair)))
        same_g = (x['group_E'] or '') == (r.group if isinstance(r.group, str) else '')
        if not (same_q and same_f and same_g): mism += 1
ok(n > 0 and mism == 0, f'D1 合理價＝核對版 detail.csv（{n} 筆評估日×檔，不符 {mism}）')

# C1 截斷到評估日重算＝全量
pit_n = pit_bad = 0
for E, kind, ey in [e for e in full.eval_dates(2020, 2026) if e[0] in ('2020-04-01', '2022-08-15', '2024-11-15', '2026-05-18')]:
    smp = [s for s in det[det.date == E].stock_id.tolist()[:40]] or [s for s in list(full.PX)[:300]]
    if E == '2026-05-18':
        smp = [s for s in full.PX if full.fair_at(s, E, kind, ey) is not None and full.fair_at(s, E, kind, ey)['pass_q'] == 1][:40]
    cut = FairValue(SNAP, asof=E, ids=smp)
    for s in smp:
        a = full.fair_at(s, E, kind, ey); b = cut.fair_at(s, E, kind, ey); pit_n += 1
        fa = None if a is None else (a['pass_q'], round(a['fair'], 6) if pd.notna(a['fair']) else None)
        fb = None if b is None else (b['pass_q'], round(b['fair'], 6) if pd.notna(b['fair']) else None)
        if fa != fb: pit_bad += 1
ok(pit_n > 0 and pit_bad == 0, f'C1 PIT：資料截斷到評估日（財報上傳 ≥ 評估日者刪除、價格／本益比／還原事件只留 ≤ 評估日）重算＝全量（{pit_n} 筆，不同 {pit_bad}）')

# C2 評估日後資料竄改不影響（同一物件竄改）
E, kind, ey = [e for e in evs if e[0] == '2022-08-15'][0]
smp = [s for s in det[(det.date == E) & (det.pass_q == 1)].stock_id.tolist()]
before = {s: full.fair_at(s, E, kind, ey)['fair'] for s in smp}
for s in smp:
    p = full.load_per(s); p.loc[p.index > E, 'per'] *= 3; p.loc[p.index > E, 'yield_pct'] *= 3
    px = full.PX[s]; px.loc[px.index > E, 'close'] *= 5
for (s, y, q), u in list(full.UP.items()):
    if u[:10] >= E and (s, f'{y}Q{q}') in full.FS:
        ni, ep = full.FS[(s, f'{y}Q{q}')]; full.FS[(s, f'{y}Q{q}')] = (ni * 2, ep * 2)
after = {s: full.fair_at(s, E, kind, ey)['fair'] for s in smp}
ok(len(smp) > 0 and all((pd.isna(before[s]) and pd.isna(after[s])) or before[s] == after[s] for s in smp),
   f'C2 PIT：評估日後的本益比／殖利率／收盤／評估日（含）後才上傳的財報竄改，合理價不變（{len(smp)} 檔）')

# C3 趨勢 PIT：判日截斷重算＝全量（含還原事件截斷；均線比較對全域縮放不變）
del full
Js = ['2020-06-01', '2022-03-01', '2024-09-02']
smp = ['2330', '2317', '2454', '2603', '3008', '1101', '2882', '6505', '2412', '3034', '2379', '1301']
fullB = M.Bars(FairValue(SNAP, ids=smp))
tp_n = tp_bad = 0
for J in Js:
    cutB = M.Bars(FairValue(SNAP, asof=J, ids=smp))
    for s in smp:
        if s not in fullB.B or J not in fullB.B[s]['at']: continue
        ka = fullB.B[s]['at'][J]; kb = cutB.B[s]['at'][J]
        a = (int(fullB.B[s]['state'][ka]), fullB.lookback_bad(s, ka)); b = (int(cutB.B[s]['state'][kb]), cutB.lookback_bad(s, kb))
        tp_n += 1; tp_bad += int(a != b)
ok(tp_n > 0 and tp_bad == 0, f'C3 PIT：趨勢狀態與回看壞根在判日截斷重算＝全量（{tp_n} 筆，不同 {tp_bad}）')

# ═════════ E ═════════
py = sys.executable
env = dict(os.environ, PYTHONPATH=os.path.dirname(HERE))
def runc(args):
    p = subprocess.run([py, '-m', 'backtest.researchTWCheapTrend'] + args, cwd=os.path.dirname(HERE), env=env,
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout + p.stderr
rc1, o1 = runc(['--formal'])
rc2, o2 = runc(['--formal', '--ruling', 'seq481'])
rc3, o3 = runc(['--formal', '--ruling', 'seq482', '--dry'])
rc4, o4 = runc([])
ok(rc1 != 0 and '拒跑' in o1 and rc2 != 0 and '拒跑' in o2 and rc3 != 0 and rc4 != 0,
   'E1 正式跑閘門：缺 --ruling、錯號、與 --dry 併用、無旗標 ⇒ 全部拒跑')

print(f'\n合計 PASS {len(PASSES)}／{len(PASSES) + len(FAILS)}' + ('' if not FAILS else '；FAIL：' + '、'.join(FAILS)))
sys.exit(1 if FAILS else 0)

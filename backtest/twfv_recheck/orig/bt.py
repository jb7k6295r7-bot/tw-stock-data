# -*- coding: utf-8 -*-
"""合理價算法（台股機械版）回測 —— 照 PREREG.md 執行。
用法：python3 bt.py <tw-stock-data repo 根目錄>
輸出：同目錄 detail.csv、groups.csv、summary.json、breaks.csv
"""
import sys, os, glob, json, math, re
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from value import path, pv          # 與看板同一支公式（不改動）

REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'qbt_repo', 'repo')
D = os.path.join(REPO, 'data')
CAP_MIN = 300e8
H1, H3 = 250, 750
SEED, NBOOT = 20261026, 10000

# ---------- 日曆與評估日 ----------
cal = pd.read_csv(f'{D}/meta/calendar_twse.csv', dtype=str).date.dropna().sort_values().tolist()
cal_idx = {d: i for i, d in enumerate(cal)}
def first_td_on_or_after(s):
    for d in cal:
        if d >= s: return d
EVAL = []
for y in range(2020, 2026):
    for md, kind in (('04-01', 'Q4'), ('05-16', 'Q1'), ('08-15', 'Q2'), ('11-15', 'Q3')):
        EVAL.append((first_td_on_or_after(f'{y}-{md}'), kind, y))

def fwd(d, n):
    i = cal_idx[d] + n
    return cal[i] if i < len(cal) else None

# ---------- 名冊（累積，含已下市） ----------
roster = pd.read_csv(f'{D}/meta/stocks.csv', dtype=str)
ids = roster[roster.kind == 'stock'].stock_id.tolist()

# ---------- 價格與還原因子 ----------
def load_px(s):
    fp = f'{D}/stocks/{s}.csv'
    if not os.path.exists(fp): return None
    d = pd.read_csv(fp, dtype=str, usecols=lambda c: c in ('date', 'market', 'close', 'shares', 'valid_bar'))
    d['close'] = pd.to_numeric(d['close'], errors='coerce')
    d['shares'] = pd.to_numeric(d['shares'], errors='coerce')
    d = d[(d.valid_bar == '1') & (d.close > 0)].copy()
    return d.set_index('date')

def load_adj(s):
    fp = f'{D}/adj/{s}.csv'
    if not os.path.exists(fp): return pd.DataFrame(columns=['date', 'cum_factor'])
    a = pd.read_csv(fp, dtype=str)
    a['cum_factor'] = pd.to_numeric(a['cum_factor'], errors='coerce')
    return a.sort_values('date')[['date', 'cum_factor']]

def F_series(dates, adj):
    """F(d) = 第一個事件日 > d 的 cum_factor，無則 1（READ_CONTRACT 照抄語意）"""
    ev = adj.date.values; cf = adj.cum_factor.values
    pos = np.searchsorted(ev, np.asarray(dates), side='right')
    return np.array([cf[p] if p < len(ev) else 1.0 for p in pos])

PX, ADJ = {}, {}
for s in ids:
    p = load_px(s)
    if p is None or p.empty: continue
    PX[s] = p
    ADJ[s] = load_adj(s)
    p['adj'] = p.close.values * F_series(p.index.values, ADJ[s])

# ---------- 財報（年初累計） ----------
NI_RE = re.compile(r'^淨利（(淨)?損）歸屬於母公司業主$')
EQ_RE = re.compile(r'^歸屬於母公司業主(之)?權益(合計)?$')
FS, BS = {}, {}
for f in glob.glob(f'{D}/mops/fs_hist/*.csv'):
    d = pd.read_csv(f, dtype=str)
    ni = [c for c in d.columns if NI_RE.match(c)]; ep = [c for c in d.columns if c.startswith('基本每股盈餘')]
    assert len(ni) == 1 and len(ep) == 1, (f, ni, ep)
    for r in d[['stock_id', 'period', ni[0], ep[0]]].itertuples(index=False):
        FS[(r[0], r[1])] = (pd.to_numeric(r[2], errors='coerce'), pd.to_numeric(r[3], errors='coerce'))
for f in glob.glob(f'{D}/mops/bs_hist/*.csv'):
    d = pd.read_csv(f, dtype=str)
    eq = [c for c in d.columns if EQ_RE.match(c)]
    assert len(eq) == 1 and '股本' in d.columns, (f, eq)
    for r in d[['stock_id', 'period', eq[0], '股本']].itertuples(index=False):
        BS[(r[0], r[1])] = (pd.to_numeric(r[2], errors='coerce'), pd.to_numeric(r[3], errors='coerce'))

# 上傳時戳：同一 (代號, 年, 季) 非英文版財報的最早上傳
fd = pd.read_csv(f'{D}/meta/filing_dates.csv', dtype=str)
fd = fd[~fd.doc_type.str.contains('英文', na=False)]
UP = fd.groupby(['stock_id', 'year', 'season']).uploaded_at.min().to_dict()

def per_str(y, q): return f'{y}Q{q}'
def available(s, y, q, E):
    if (s, per_str(y, q)) not in FS: return False
    u = UP.get((s, str(y), str(q)))
    return (u is None) or (u[:10] < E)      # 無上傳紀錄 ⇒ 視為法定期限前已公告

def latest_period(s, E, kind, ey):
    y, q = (ey - 1, 4) if kind == 'Q4' else (ey, int(kind[1]))
    for _ in range(5):
        if available(s, y, q, E): return y, q
        y, q = (y - 1, 4) if q == 1 else (y, q - 1)
    return None

def ttm_eps(s, y, q):
    if q == 4: return FS[(s, per_str(y, 4))][1]
    a = FS.get((s, per_str(y, q))); b = FS.get((s, per_str(y - 1, 4))); c = FS.get((s, per_str(y - 1, q)))
    if a is None or b is None or c is None: return np.nan
    return a[1] + b[1] - c[1]

def quality(s, E, y, q):
    ya = y if q == 4 else y - 1
    if q != 4 and not available(s, ya, 4, E): return False, np.nan, 'annual_unavail'
    rows = []
    for yy in range(ya - 4, ya + 1):
        f = FS.get((s, per_str(yy, 4))); b = BS.get((s, per_str(yy, 4)))
        if f is None or b is None or any(pd.isna(v) for v in (f[0], f[1], b[0])): return False, np.nan, 'fs_missing'
        rows.append((f[0], f[1], b[0]))
    roe_ok = sum(1 for ni, ep, eq in rows if eq > 0 and ni / eq >= 0.15)
    noloss = all(ni >= 0 for ni, ep, eq in rows)
    e0, e4 = rows[0][1], rows[-1][1]
    g = (e4 / e0) ** 0.25 - 1 if (e0 > 0 and e4 > 0) else np.nan
    ok = roe_ok >= 4 and noloss and pd.notna(g) and g >= 0.12
    return ok, g, f'roe{roe_ok}/noloss{int(noloss)}/g{g:.3f}' if pd.notna(g) else f'roe{roe_ok}/noloss{int(noloss)}/g_na'

PER = {}
def load_per(s):
    if s in PER: return PER[s]
    fp = f'{D}/stocks_per/{s}.csv'
    p = pd.read_csv(fp, dtype=str) if os.path.exists(fp) else pd.DataFrame(columns=['date', 'per', 'yield_pct'])
    p['per'] = pd.to_numeric(p['per'], errors='coerce'); p['yield_pct'] = pd.to_numeric(p['yield_pct'], errors='coerce')
    PER[s] = p.sort_values('date').set_index('date'); return PER[s]

def shift_years(E, k):
    y = int(E[:4]) - k; return f'{y}{E[4:]}' if E[5:] != '02-29' else f'{y}-02-28'

def px_on_or_before(p, d):
    sub = p.loc[:d]
    return (sub.index[-1], sub.iloc[-1]) if len(sub) else (None, None)

def ret(s, E, n):
    X = fwd(E, n)
    if X is None: return np.nan, None
    p = PX[s]
    if E not in p.index: return np.nan, None
    xd, xr = px_on_or_before(p, X)           # 出場日沒成交或已下市 ⇒ 最後成交價
    return xr.adj / p.loc[E].adj - 1, xd

def breaks_in(s, a, b):
    """(a, b] 區間內的硬斷點：相鄰有效 K 比值 ≤0.55/≥1.8 或洞 ≥5 交易日，且區間內無還原事件"""
    p = PX[s].loc[a:b]; ev = ADJ[s].date.values; out = []
    ds = p.index.tolist(); cs = p.close.values
    for i in range(1, len(ds)):
        r = cs[i] / cs[i - 1]; hole = cal_idx.get(ds[i], 0) - cal_idx.get(ds[i - 1], 0) - 1
        if (r <= 0.55 or r >= 1.8 or hole >= 5):
            if not ((ev > ds[i - 1]) & (ev <= ds[i])).any():
                out.append((ds[i - 1], ds[i], round(r, 4), hole))
    return out

# ---------- 主迴圈 ----------
rows, brk = [], []
for E, kind, ey in EVAL:
    for s, p in PX.items():
        if E not in p.index: continue
        r = p.loc[E]
        if r.market not in ('twse', 'tpex'): continue
        lp = latest_period(s, E, kind, ey)
        sh, sh_src = r.shares, 'daily'
        if pd.isna(sh) or sh <= 0:
            sh, sh_src = np.nan, 'none'
            if lp and (s, per_str(*lp)) in BS and pd.notna(BS[(s, per_str(*lp))][1]):
                sh, sh_src = BS[(s, per_str(*lp))][1] * 1000 / 10, 'bs_capital/10'
        cap = r.close * sh if pd.notna(sh) else np.nan
        if not (cap >= CAP_MIN): continue
        rec = dict(date=E, stock_id=s, market=r.market, close=r.close, mcap_e8=round(cap / 1e8, 1), shares_src=sh_src,
                   period=per_str(*lp) if lp else None)
        ok, g, why = (False, np.nan, 'no_period') if lp is None else quality(s, E, *lp)
        rec.update(pass_q=int(ok), q_note=why, g_hist=g)
        mult, grp = np.nan, ''
        if ok:
            E0 = ttm_eps(s, *lp)
            pr = load_per(s); hist = pr.loc[shift_years(E, 10):E]; hist = hist[hist.index < E]
            hv = hist[hist.per > 0]
            if len(hv) == 0 or hv.index[0] > shift_years(E, 3):
                rec.update(q_note=why + '|pe_hist<3y'); ok = False; rec['pass_q'] = 0
            else:
                pe_med = float(hv.per.median()); pe_T = min(pe_med, 25.0)
                cur = pr.loc[:E].tail(1)
                yv = cur.yield_pct.iloc[0] if len(cur) else np.nan
                pv_ = cur.per.iloc[0] if len(cur) else np.nan
                if pd.isna(pv_) or pv_ <= 0:
                    pv_ = r.close / E0 if E0 > 0 else np.nan
                payout = 0.0 if pd.isna(yv) or pd.isna(pv_) else min(max(yv / 100 * pv_, 0.0), 1.0)
                gg = min(0.8 * g, 0.15)
                if pd.isna(E0):
                    rec.update(q_note=why + '|E0_na'); ok = False; rec['pass_q'] = 0; grp = ''
                elif E0 > 0:
                    divs, term = path(E0, gg, pe_T, payout); fair = pv(divs, term, 0.10)
                    mult = r.close / fair
                else:
                    fair = np.nan; mult = np.inf
                if not ok: fair = np.nan; mult = np.nan
                if ok: grp = '可買' if mult <= 1.0 else ('接近' if mult <= 1.15 else '偏貴')
                rec.update(E0=E0, g_used=gg, pe_med=pe_med, pe_T=pe_T, payout=payout, fair=fair)
        rec.update(mult=mult, group=grp)
        r1, x1 = ret(s, E, H1); r3, x3 = ret(s, E, H3)
        rec.update(ret_1y=r1, exit_1y=x1, ret_3y=r3, exit_3y=x3)
        if ok:
            X = fwd(E, H3) or cal[-1]
            for b in breaks_in(s, E, X):
                brk.append(dict(date=E, stock_id=s, prev=b[0], cur=b[1], ratio=b[2], hole=b[3]))
        rows.append(rec)

det = pd.DataFrame(rows)
bk = pd.DataFrame(brk, columns=['date', 'stock_id', 'prev', 'cur', 'ratio', 'hole'])
bk.to_csv(f'{HERE}/breaks.csv', index=False)
# 斷點落在持有窗內 ⇒ 該檔該窗「本方法不適用」，報酬設 NaN
det['brk_1y'] = 0; det['brk_3y'] = 0
for b in bk.itertuples():
    m = (det.date == b.date) & (det.stock_id == b.stock_id)
    for col, xcol in (('brk_1y', 'exit_1y'), ('brk_3y', 'exit_3y')):
        x = det.loc[m, xcol]
        if len(x) and pd.notna(x.iloc[0]) and b.cur <= x.iloc[0]: det.loc[m, col] = 1
det.loc[det.brk_1y == 1, 'ret_1y'] = np.nan
det.loc[det.brk_3y == 1, 'ret_3y'] = np.nan
det = det.sort_values(['date', 'stock_id'])
det.to_csv(f'{HERE}/detail.csv', index=False, encoding='utf-8-sig')

# ---------- 大盤：加權報酬指數 ----------
tri = pd.read_csv(f'{D}/history/market_tri.csv', dtype={'date': str}).set_index('date').close.astype(float)
def tri_ret(E, n):
    X = fwd(E, n)
    return np.nan if X is None or X not in tri.index else tri[X] / tri[E] - 1

# ---------- 每評估日各組 ----------
G = []
for E, kind, ey in EVAL:
    d = det[det.date == E]; q = d[d.pass_q == 1]
    g = dict(date=E, entry_year=ey, n_mcap=len(d), n_pass=len(q))
    for nm in ('可買', '接近', '偏貴'):
        x = q[q.group == nm]; g[f'n_{nm}'] = len(x)
        g[f'r1_{nm}'] = x.ret_1y.mean() if x.ret_1y.notna().any() else np.nan
        g[f'r3_{nm}'] = x.ret_3y.mean() if x.ret_3y.notna().any() else np.nan
        g[f'n1_{nm}'] = int(x.ret_1y.notna().sum())
    g['r1_全部'] = q.ret_1y.mean() if q.ret_1y.notna().any() else np.nan
    g['r3_全部'] = q.ret_3y.mean() if q.ret_3y.notna().any() else np.nan
    g['r1_大盤'] = tri_ret(E, H1); g['r3_大盤'] = tri_ret(E, H3)
    g['diff1'] = g['r1_可買'] - g['r1_偏貴']; g['diff3'] = g['r3_可買'] - g['r3_偏貴']
    G.append(g)
G = pd.DataFrame(G); G.to_csv(f'{HERE}/groups.csv', index=False, encoding='utf-8-sig')

def cluster_ci(df, col):
    v = df[['entry_year', col]].dropna()
    if v.empty: return np.nan, np.nan, np.nan
    yrs = sorted(v.entry_year.unique()); by = {y: v[v.entry_year == y][col].values for y in yrs}
    rng = np.random.default_rng(SEED); bs = []
    for _ in range(NBOOT):
        pick = rng.choice(yrs, size=len(yrs), replace=True)
        bs.append(np.concatenate([by[y] for y in pick]).mean())
    return v[col].mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)

pt, lo, hi = cluster_ci(G, 'diff1')
front = G[G.entry_year <= 2022].diff1.dropna(); back = G[G.entry_year >= 2023].diff1.dropna()

# ---------- 對大盤：重疊持有袖（每評估日一袖、持 250 日、袖內同權買進持有、空袖＝現金） ----------
def sleeve_curve(E, members):
    X = fwd(E, H1); days = cal[cal_idx[E]:cal_idx[X] + 1]
    if not members: return pd.Series(1.0, index=days)
    vals = []
    for s in members:
        a = PX[s].adj.reindex(days).ffill()             # 停牌／下市後沿用最後成交
        vals.append(a / a.iloc[0])
    return pd.concat(vals, axis=1).mean(axis=1)
usable = [(E, ey) for E, k, ey in EVAL if fwd(E, H1) is not None]
sl = {}
for E, ey in usable:
    m = det[(det.date == E) & (det.group == '可買') & (det.brk_1y == 0)].stock_id.tolist()
    sl[E] = sleeve_curve(E, m)
start, end = usable[0][0], fwd(usable[-1][0], H1)
days = cal[cal_idx[start]:cal_idx[end] + 1]
dr = []
for i in range(1, len(days)):
    t0, t1 = days[i - 1], days[i]; rs = []
    for E, c in sl.items():
        if t0 in c.index and t1 in c.index: rs.append(c[t1] / c[t0] - 1)
    dr.append(np.mean(rs) if rs else 0.0)
eq = pd.Series(np.cumprod([1.0] + [1 + x for x in dr]), index=days)
mk = tri.reindex(days); mk = mk / mk.iloc[0]
def ann(e): return e.iloc[-1] ** (250 / (len(e) - 1)) - 1
def mdd(e): return (e / e.cummax() - 1).min()
strat = dict(cagr=ann(eq), mdd=mdd(eq)); mkt = dict(cagr=ann(mk), mdd=mdd(mk))
strat['ratio'] = strat['cagr'] / abs(strat['mdd']); mkt['ratio'] = mkt['cagr'] / abs(mkt['mdd'])
pd.DataFrame({'strat': eq, 'mkt': mk}).to_csv(f'{HERE}/equity_1y_sleeves.csv')

# ---------- 判定 ----------
n_lt3_all = int((G.n_可買 < 3).sum()); n_all = len(G)
Gu = G[G.diff1.notna() | G.r1_大盤.notna()]
Gu = G[[fwd(E, H1) is not None for E in G.date]]
n_lt3_use = int((Gu.n_可買 < 3).sum()); n_use = len(Gu)
insuff = (n_lt3_all >= n_all / 2) or (n_lt3_use >= n_use / 2)
passed = (pt > 0) and (lo > 0) and (front.mean() > 0) and (back.mean() > 0)
verdict = '樣本不足' if insuff else ('通過' if passed else '測不出')
vs = dict(cagr_win=bool(strat['cagr'] > mkt['cagr']), ratio_win=bool(strat['ratio'] >= mkt['ratio']))

out = dict(point=pt, ci=[lo, hi], n_dates_diff=int(G.diff1.notna().sum()), years=sorted(G.dropna(subset=['diff1']).entry_year.unique().tolist()),
           front=front.mean(), n_front=len(front), back=back.mean(), n_back=len(back),
           n_lt3_all=n_lt3_all, n_all=n_all, n_lt3_use=n_lt3_use, n_use=n_use, insufficient=bool(insuff), verdict=verdict,
           strat=strat, mkt=mkt, vs=vs, window=[start, end],
           avg_n_buy=float(G.n_可買.mean()), avg_n_buy_use=float(Gu.n_可買.mean()),
           diff3_mean=float(G.diff3.mean()) if G.diff3.notna().any() else None, n_diff3=int(G.diff3.notna().sum()),
           n_breaks=len(bk), n_brk_1y=int(det.brk_1y.sum()), n_brk_3y=int(det.brk_3y.sum()),
           shares_fallback=int((det.shares_src != 'daily').sum()))
json.dump(out, open(f'{HERE}/summary.json', 'w'), ensure_ascii=False, indent=1, default=float)
pd.set_option('display.width', 250)
print(G[['date', 'n_mcap', 'n_pass', 'n_可買', 'n_接近', 'n_偏貴', 'r1_可買', 'r1_偏貴', 'diff1', 'r1_全部', 'r1_大盤', 'diff3']].round(3).to_string(index=False))
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))

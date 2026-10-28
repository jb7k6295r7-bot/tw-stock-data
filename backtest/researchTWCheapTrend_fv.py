# -*- coding: utf-8 -*-
"""便宜＋趨勢轉強 台股 seq1 的「便宜」：台股合理價機械版（回測核對版）的評估日合理價。

來源（⛔ 不改動原檔）：backtest/twfv_recheck/orig/bt.py、value.py
  sha256 bt.py    9ca7ecb53ee02d33fc9c6e15c0a11b9e7a20ed6ca32fb85dfdf5eec1bc16b019
  sha256 value.py cec20bf80c79bb35a488f6e7c1dcfb416733e6808503be37c95b51adcabd1535
  核對：回測核對相符（commit 77aafeb9bd，twfv_recheck/結論.md；產業附件原樣＋tw-stock-data 8e5d22e，五檔逐位元相同）。
value.py：直接 import path()、pv()（sys.dont_write_bytecode，不在 orig/ 寫 .pyc）。
bt.py：是頂層直接執行的腳本（import 會整份跑並覆寫 orig/ 的輸出），⇒ 只能【照抄】函式，抄錄行號如下：
  L20–24 日曆／first_td_on_or_after、L30–32 fwd、L41–59 load_px／load_adj／F_series、L70–84 FS／BS 讀入、
  L87–89 上傳時戳、L91–123 per_str／available／latest_period／ttm_eps／quality、L125–138 load_per／shift_years／px_on_or_before、
  L148–157 breaks_in（本件不用於判定，只供描述對照）、L164–203 主迴圈內的「單檔單評估日」合理價計算。
  抄錄時唯一的改動（都不改公式、不改門檻）：
   (a) 全域變數改成 FairValue 物件的屬性（資料根目錄由參數給）；
   (b) 評估日年份 2018～2026（bt.py 是 2020～2025；登錄 §三「2018-04 起」）；
   (c) 主迴圈的「評估日市值 ≥ 300 億」過濾拿掉——登錄 §一 的市值門檻在【判日】判，評估日對所有上市櫃普通股都算合理價；
       合理價本身與市值無關（bt.py 的 L166–203 公式一字不改）；
   (d) 加 asof 截斷（只給 PIT 自測用；正式與乾跑不帶 asof）。
"""
import os, sys, glob, re
import numpy as np, pandas as pd

sys.dont_write_bytecode = True
ORIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twfv_recheck', 'orig')
sys.path.insert(0, ORIG)
from value import path, pv          # 與看板同一支公式（不改動）
sys.path.remove(ORIG)

SHA_BT = '9ca7ecb53ee02d33fc9c6e15c0a11b9e7a20ed6ca32fb85dfdf5eec1bc16b019'
SHA_VALUE = 'cec20bf80c79bb35a488f6e7c1dcfb416733e6808503be37c95b51adcabd1535'
CAP_MIN = 300e8
EVAL_MD = (('04-01', 'Q4'), ('05-16', 'Q1'), ('08-15', 'Q2'), ('11-15', 'Q3'))
NI_RE = re.compile(r'^淨利（(淨)?損）歸屬於母公司業主$')
EQ_RE = re.compile(r'^歸屬於母公司業主(之)?權益(合計)?$')


def verify_orig():
    import hashlib
    out = {}
    for fn, want in (('bt.py', SHA_BT), ('value.py', SHA_VALUE)):
        h = hashlib.sha256(open(os.path.join(ORIG, fn), 'rb').read()).hexdigest()
        out[fn] = (h, h == want)
    return out


def per_str(y, q): return f'{y}Q{q}'                                   # bt.py L91


def shift_years(E, k):                                                    # bt.py L133–134
    y = int(E[:4]) - k; return f'{y}{E[4:]}' if E[5:] != '02-29' else f'{y}-02-28'


def F_series(dates, adj):                                                 # bt.py L55–59
    """F(d) = 第一個事件日 > d 的 cum_factor，無則 1（READ_CONTRACT 照抄語意）"""
    ev = adj.date.values; cf = adj.cum_factor.values
    pos = np.searchsorted(ev, np.asarray(dates), side='right')
    return np.array([cf[p] if p < len(ev) else 1.0 for p in pos])


class FairValue:
    def __init__(self, repo, asof=None, ids=None):
        """repo：tw-stock-data 快照根目錄（含 data/）。asof：只留 asof 之前可得的資料（PIT 自測用；None＝全部）。"""
        self.D = D = os.path.join(repo, 'data')
        self.asof = asof
        cal = pd.read_csv(f'{D}/meta/calendar_twse.csv', dtype=str).date.dropna().sort_values().tolist()   # bt.py L20
        if asof: cal = [d for d in cal if d <= asof]
        self.cal = cal; self.cal_idx = {d: i for i, d in enumerate(cal)}                                      # bt.py L21
        roster = pd.read_csv(f'{D}/meta/stocks.csv', dtype=str)                                               # bt.py L35–36
        self.ids = roster[roster.kind == 'stock'].stock_id.tolist() if ids is None else list(ids)
        self.PX, self.ADJ = {}, {}
        for s in self.ids:                                                                                    # bt.py L61–67
            p = self.load_px(s)
            if p is None or p.empty: continue
            self.PX[s] = p
            self.ADJ[s] = self.load_adj(s)
            p['adj'] = p.close.values * F_series(p.index.values, self.ADJ[s])
            if 'open' in p: p['adj_open'] = p.open.values * F_series(p.index.values, self.ADJ[s])
        # 財報（年初累計）bt.py L72–84
        self.FS, self.BS = {}, {}
        for f in glob.glob(f'{D}/mops/fs_hist/*.csv'):
            d = pd.read_csv(f, dtype=str)
            ni = [c for c in d.columns if NI_RE.match(c)]; ep = [c for c in d.columns if c.startswith('基本每股盈餘')]
            assert len(ni) == 1 and len(ep) == 1, (f, ni, ep)
            for r in d[['stock_id', 'period', ni[0], ep[0]]].itertuples(index=False):
                self.FS[(r[0], r[1])] = (pd.to_numeric(r[2], errors='coerce'), pd.to_numeric(r[3], errors='coerce'))
        for f in glob.glob(f'{D}/mops/bs_hist/*.csv'):
            d = pd.read_csv(f, dtype=str)
            eq = [c for c in d.columns if EQ_RE.match(c)]
            assert len(eq) == 1 and '股本' in d.columns, (f, eq)
            for r in d[['stock_id', 'period', eq[0], '股本']].itertuples(index=False):
                self.BS[(r[0], r[1])] = (pd.to_numeric(r[2], errors='coerce'), pd.to_numeric(r[3], errors='coerce'))
        # 上傳時戳 bt.py L87–89
        fd = pd.read_csv(f'{D}/meta/filing_dates.csv', dtype=str)
        fd = fd[~fd.doc_type.str.contains('英文', na=False)]
        self.UP = fd.groupby(['stock_id', 'year', 'season']).uploaded_at.min().to_dict()
        if asof:   # PIT 截斷：asof 當天及之後才上傳的財報不存在（含無時戳者不動——同 bt.py 視為已公告）
            for (s, y, q), u in list(self.UP.items()):
                if u[:10] >= asof:
                    self.FS.pop((s, per_str(y, q)), None); self.BS.pop((s, per_str(y, q)), None)
                    del self.UP[(s, y, q)]
        self.PER = {}

    # ---------- bt.py L22–24、L30–32 ----------
    def first_td_on_or_after(self, s):
        for d in self.cal:
            if d >= s: return d

    def fwd(self, d, n):
        i = self.cal_idx[d] + n
        return self.cal[i] if i < len(self.cal) else None

    def eval_dates(self, y0=2018, y1=2026):
        out = []
        for y in range(y0, y1 + 1):
            for md, kind in EVAL_MD:
                d = self.first_td_on_or_after(f'{y}-{md}')
                if d is not None: out.append((d, kind, y))
        return out

    # ---------- bt.py L41–53 ----------
    def load_px(self, s):
        fp = f'{self.D}/stocks/{s}.csv'
        if not os.path.exists(fp): return None
        d = pd.read_csv(fp, dtype=str, usecols=lambda c: c in ('date', 'market', 'open', 'close', 'shares', 'valid_bar'))
        d['close'] = pd.to_numeric(d['close'], errors='coerce')
        d['shares'] = pd.to_numeric(d['shares'], errors='coerce')
        if 'open' in d: d['open'] = pd.to_numeric(d['open'], errors='coerce')
        d = d[(d.valid_bar == '1') & (d.close > 0)].copy()
        if self.asof: d = d[d.date <= self.asof]
        return d.set_index('date')

    def load_adj(self, s):
        fp = f'{self.D}/adj/{s}.csv'
        if not os.path.exists(fp): return pd.DataFrame(columns=['date', 'cum_factor', 'factor', 'kind', 'event'])
        a = pd.read_csv(fp, dtype=str)
        a['cum_factor'] = pd.to_numeric(a['cum_factor'], errors='coerce')
        a['factor'] = pd.to_numeric(a.get('factor'), errors='coerce')
        if self.asof:   # asof 之後的事件不可知：只留 ≤ asof；cum_factor 除以「asof 後第一個事件」的 cum_factor（＝只剩 ≤ asof 的事件）
            a = a.sort_values('date')
            later = a[a.date > self.asof]
            a = a[a.date <= self.asof].copy()
            if len(later): a['cum_factor'] = a.cum_factor / later.cum_factor.iloc[0]
        return a.sort_values('date')[['date', 'cum_factor', 'factor'] + [c for c in ('kind', 'event') if c in a.columns]]

    # ---------- bt.py L92–123 ----------
    def available(self, s, y, q, E):
        if (s, per_str(y, q)) not in self.FS: return False
        u = self.UP.get((s, str(y), str(q)))
        return (u is None) or (u[:10] < E)      # 無上傳紀錄 ⇒ 視為法定期限前已公告

    def latest_period(self, s, E, kind, ey):
        y, q = (ey - 1, 4) if kind == 'Q4' else (ey, int(kind[1]))
        for _ in range(5):
            if self.available(s, y, q, E): return y, q
            y, q = (y - 1, 4) if q == 1 else (y, q - 1)
        return None

    def ttm_eps(self, s, y, q):
        FS = self.FS
        if q == 4: return FS[(s, per_str(y, 4))][1]
        a = FS.get((s, per_str(y, q))); b = FS.get((s, per_str(y - 1, 4))); c = FS.get((s, per_str(y - 1, q)))
        if a is None or b is None or c is None: return np.nan
        return a[1] + b[1] - c[1]

    def quality(self, s, E, y, q):
        FS, BS = self.FS, self.BS
        ya = y if q == 4 else y - 1
        if q != 4 and not self.available(s, ya, 4, E): return False, np.nan, 'annual_unavail'
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

    # ---------- bt.py L126–131 ----------
    def load_per(self, s):
        if s in self.PER: return self.PER[s]
        fp = f'{self.D}/stocks_per/{s}.csv'
        p = pd.read_csv(fp, dtype=str) if os.path.exists(fp) else pd.DataFrame(columns=['date', 'per', 'yield_pct'])
        p['per'] = pd.to_numeric(p['per'], errors='coerce'); p['yield_pct'] = pd.to_numeric(p['yield_pct'], errors='coerce')
        if self.asof: p = p[p.date <= self.asof]
        self.PER[s] = p.sort_values('date').set_index('date'); return self.PER[s]

    # ---------- bt.py L164–203（單檔單評估日；拿掉 L173 的市值過濾，見檔頭 (c)） ----------
    def fair_at(self, s, E, kind, ey):
        """回傳 dict 或 None（評估日無成交／非上市櫃 ⇒ None，同 bt.py L163、L165）。"""
        p = self.PX.get(s)
        if p is None or E not in p.index: return None
        r = p.loc[E]
        if r.market not in ('twse', 'tpex'): return None
        lp = self.latest_period(s, E, kind, ey)
        rec = dict(eval_date=E, stock_id=s, close_E=r.close, period=per_str(*lp) if lp else None, lp=lp)
        ok, g, why = (False, np.nan, 'no_period') if lp is None else self.quality(s, E, *lp)
        rec.update(pass_q=int(ok), q_note=why, g_hist=g)
        mult, grp, fair = np.nan, '', np.nan
        if ok:
            E0 = self.ttm_eps(s, *lp)
            pr = self.load_per(s); hist = pr.loc[shift_years(E, 10):E]; hist = hist[hist.index < E]
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
                rec.update(E0=E0, g_used=gg, pe_med=pe_med, pe_T=pe_T, payout=payout)
        rec.update(fair=fair, mult_E=mult, group_E=grp)
        return rec

    def shares_fallback(self, s, lp):
        """bt.py L167–171：日股數缺 ⇒ 用 lp 季的資產負債表股本 ÷ 10 元面額。"""
        if lp and (s, per_str(*lp)) in self.BS and pd.notna(self.BS[(s, per_str(*lp))][1]):
            return self.BS[(s, per_str(*lp))][1] * 1000 / 10
        return np.nan

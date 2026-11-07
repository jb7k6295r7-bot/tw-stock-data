# -*- coding: utf-8 -*-
"""台股合理價機械版「可買」裡剔除【長期下跌】（年線版／半年線版）——正式跑。

登錄：產業 seq96（pw1 2b9b3d9778382198，6675 B）＋補登錄 產業 seq101（pw1 1d4094ab4250c703，1478 B）；開跑兩份都驗 sha。
發號：裁定 seq498 §一（N_單筆 +2；97.5% CI＝Bonferroni 2 格；判語最多「通過（暫定）」；按年分群 CI 列主表同一列，
      年分群下緣 ≤ 0 ⇒ 結果句寫「按年分群看不出」；兩版都過採半年線版；放行／加碼對照只描述、不計 N；本件對回落沉默）。
補核：裁定 seq499（seq101 四點核；24 門檻看全期、不分段；前段方向僅供參考句；同族句；2022 集中句＋拿掉 2022 描述；
      ★1 主讀法核、另一讀法只描述）⇒ 正式跑閘門：`--formal --ruling seq499` 兩個旗標都要，否則拒跑。
頻率表：researchTWLongDownFilter_freq.py（commit 48631418d9）；分組、★1～★11 一字不改，直接呼叫其 build()（同一份實作）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchTWLongDownFilter.py --formal --ruling seq499

══════════ 主量與判定（seq96 §四＋seq101 ①②＋seq498／seq499，照抄）══════════
 1 年報酬＝評估日收盤進、日曆 +250 交易日收盤出，還原收盤（bt.py ret() 同義）；出場日無成交／已下市 ⇒ 用之前最後一根（執行選擇 13）；
   持有窗 (評估根, 出場根] 有壞根（seq335 research11 語意，freq ★8 同一旗標）⇒ 該筆報酬不計（執行選擇 14）。不扣成本（原版不扣）。
 每月差＝濾網組平均 − 全部可買平均（組內同權；不判者留在全部可買、不進濾網組）。
 主量＝【剔除組 ≥ 3 檔】月份（剔除組檔數照頻率表，不看報酬是否可算）的每月差之平均；全部月份版只描述；報零差值月數。
 主 CI＝按月分群 bootstrap 10,000 次、97.5%（百分位 1.25／98.75），種子 SEED 寫死於下。
 按年分群 CI＝同法以進場年為群（6 群），列主表同一列，標「群數不足（6 群），只描述」。
 通過（暫定）＝主 CI 下緣 > 0，且前段（2020-04～2022-12）、後段（2023-01～2025-10）點估計各 > 0，
   且每月中位數差（★F2）的平均方向與主量一致（> 0）。其餘一律「測不出」（負也寫測不出）。兩版都過 ⇒ 採半年線版。

══════════ ★F 執行者定（看任何報酬前寫死）══════════
 ★F1 「全部可買平均」只用 1 年報酬可算的筆（持有窗壞根者不計，同原版）；濾網組、剔除組同。某月濾網組無可算筆 ⇒ 該月差 NaN、不進平均。
 ★F2 每月中位數差＝該月 濾網組中位數 − 全部可買中位數；彙總＝主量月份的平均（與主量同聚合）。
     〔另一讀法只描述：主量月份「每月平均差」的跨月中位數。〕
 ★F3 前段／後段點估計＝該段主量月份的每月差平均（前段方向僅供參考，seq499）。
 ★F4 拿掉 2022＝主量月份中去掉進場年 2022 者，重算主量、97.5% 月分群 CI、前後段、中位數差（只描述）。
 ★F5 少數股主導：每次拿掉一檔（該檔所有月份），月份集合固定、重算主量；任一檔使主量變號或 |變動| ≥ 0.5×|主量| ⇒ 「少數股主導」，
     逐筆列出該檔；不論是否觸發，影響最大的前 3 檔都逐筆列出。
 ★F6 放行對照（seq96 §五，只描述）：被擋筆＝主讀法可買且長期下跌（全部 67 個月，不限剔除組 ≥ 3 檔月份）。
     放行根照頻率表 ★9（主規則＝站回同一條均線或均線轉平往上；季線＝收盤 > MA60；遇壞根截尾）。
     放行價比＝放行根還原收盤 ÷ 被擋根還原收盤；放行時仍可買＝放行日用 fair_at（★1 主讀法期別）分組＝可買。
     放行後持有＝放行根收盤進、日曆 +250 收盤出（同上報酬規則）；「同期全部可買」＝被擋那個評估月全部可買 1 年平均（逐筆對應後平均）。
     先站回季線＝被擋後 250 根內季線放行；沒站回＝250 根內沒有（含到快照尾未放行）；截尾者不列。比較的是被擋日進場的 1 年報酬。
 ★F7 加碼對照（只描述）：全部可買按頻率表 ★10 主讀法 nl 拆兩組；每月差＝組平均 − 全部可買平均（該組 ≥ 1 筆可算的月份平均）。
     延後版：頻率表 ★10 的延後進場根（delay_bars）收盤進、+250 收盤出；仍可買＝延後進場日 fair_at 分組＝可買。
 ★F8 3 年＝日曆 +750，同主量算法（剔除組 ≥ 3 檔且 +750 在日曆內的月份），只描述。
 ★F9 ★1 另一讀法（法定期限對應）：可買名單改用 buy_alt、其餘同主量，只描述。
"""
import os, sys, json, glob, hashlib, argparse
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import researchTWLongDownFilter_freq as M      # noqa: E402

RULING_FORMAL = 'seq499'
SEED, NBOOT = 20261108, 10000
CI_LEVEL = 0.975                       # N＝2（裁定 seq498）⇒ 97.5%
OUTF = os.path.join(HERE, 'resultsLongDownFilter', 'formal')
REG101_GLOB = '*seq96補登錄四點*seq101.md'
REG101_SHA16, REG101_BYTES = '1d4094ab4250c703', 1478
YEAR_X = 2022
DOM_FRAC = 0.5
FRONT_LABEL, BACK_LABEL = '前段', '後段'
VERDICT_PASS, VERDICT_FAIL = '通過（暫定）', '測不出'


# ═════════════ 閘門 ═════════════
def gate(argv):
    """→ 'formal' | ('refuse', 訊息)。只認 --formal --ruling seq499（裁定 seq499 准正式跑）。"""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--formal', action='store_true')
    ap.add_argument('--ruling', default=None)
    try:
        a, rest = ap.parse_known_args(argv)
    except SystemExit:
        return ('refuse', '⛔ 參數錯；拒跑')
    if rest:
        return ('refuse', '⛔ 不認得的參數 %s；拒跑' % rest)
    if not a.formal or a.ruling != RULING_FORMAL:
        return ('refuse', '⛔ 正式跑須 --formal --ruling %s 兩個旗標都給（裁定 seq499 准正式跑）；拒跑' % RULING_FORMAL)
    return 'formal'


def verify_seq101():
    fs = glob.glob(os.path.join(M.REG_DIR, REG101_GLOB))
    assert len(fs) == 1, fs
    b = open(fs[0], 'rb').read()
    lines = b.decode('utf-8').splitlines(keepends=True)
    h = hashlib.sha256(''.join(lines[:-1]).encode('utf-8')).hexdigest()
    assert len(b) == REG101_BYTES and h.startswith(REG101_SHA16), (len(b), h)
    return dict(bytes=len(b), pw1=h[:16])


# ═════════════ 報酬（台股） ═════════════
def hold_ret(st, k, H, ncal):
    """第 k 根收盤進、日曆位置 +H 收盤出 → (R, 狀態)。出場日無成交／已下市 ⇒ 之前最後一根；持有窗壞根 ⇒ NaN。"""
    i = int(st.pos[k])
    if i + H >= ncal:
        return np.nan, 'cal'
    kx = int(np.searchsorted(st.pos, i + H, side='right')) - 1
    if kx > k and M.bad_in(st.cb, k, kx):
        return np.nan, 'holdbad'
    stt = 'delisted' if (kx == len(st.px) - 1 and st.pos[kx] < i + H) else 'ok'
    return float(st.px[kx] / st.px[k] - 1), stt


# ═════════════ 統計（台美共用） ═════════════
def boot_ci(vals, clusters, level=CI_LEVEL, seed=SEED, nboot=NBOOT):
    """群集 bootstrap：每次有放回抽群、群內值全取、取平均。→ (點估計, 下緣, 上緣, 群數)。"""
    v = pd.DataFrame(dict(v=np.asarray(vals, float), c=list(clusters))).dropna()
    if v.empty:
        return np.nan, np.nan, np.nan, 0
    cls = sorted(v.c.unique())
    by = [v.v[v.c == c].values for c in cls]
    rng = np.random.default_rng(seed)
    bs = np.empty(nboot)
    for i in range(nboot):
        pick = rng.choice(len(cls), size=len(cls), replace=True)
        bs[i] = np.concatenate([by[j] for j in pick]).mean()
    a = (1 - level) / 2 * 100
    return float(v.v.mean()), float(np.percentile(bs, a)), float(np.percentile(bs, 100 - a)), len(cls)


def month_table(B, gcol, rcol):
    """B：可買列（欄 E、year、segment、gcol 長期下跌代碼、rcol 報酬）。→ 每月一列。"""
    out = []
    for E, d in B.groupby('E', sort=True):
        c = d[gcol]; r = d[rcol]
        a = r.dropna(); f = r[c == 0].dropna(); x = r[c == 1].dropna()
        row = dict(E=E, month=E[:7], year=int(d.year.iloc[0]), segment=d.segment.iloc[0],
                   n_all=len(d), n_filt=int((c == 0).sum()), n_excl=int((c == 1).sum()),
                   n_skip=int((~c.isin([0, 1])).sum()),
                   nr_all=len(a), nr_filt=len(f), nr_excl=len(x),
                   mean_all=a.mean() if len(a) else np.nan, mean_filt=f.mean() if len(f) else np.nan,
                   mean_excl=x.mean() if len(x) else np.nan,
                   med_all=a.median() if len(a) else np.nan, med_filt=f.median() if len(f) else np.nan,
                   med_excl=x.median() if len(x) else np.nan)
        row['diff'] = row['mean_filt'] - row['mean_all'] if len(f) and len(a) else np.nan
        row['diff_med'] = row['med_filt'] - row['med_all'] if len(f) and len(a) else np.nan
        out.append(row)
    return pd.DataFrame(out)


def verdict(pt, lo, front, back, med):
    """seq96 §四＋seq101 ②＋seq498：通過（暫定）或測不出（⛔ 沒有第三種字）。"""
    vals = np.array([pt, lo, front, back, med], float)
    ok = bool(np.isfinite(vals).all() and lo > 0 and front > 0 and back > 0 and pt > 0 and med > 0)
    return VERDICT_PASS if ok else VERDICT_FAIL


def adopt(v_by_version):
    """兩版都過 ⇒ 半年線版；一版過 ⇒ 那一版；都沒過 ⇒ None。"""
    p = [vn for vn, v in v_by_version.items() if v == VERDICT_PASS]
    if len(p) == 2:
        return '半年線'
    return p[0] if p else None


def cell(T, months=None, level=CI_LEVEL):
    """主量格：T＝month_table 輸出，months＝要用的 E 集合（None＝T 全部）。"""
    m = T if months is None else T[T.E.isin(months)]
    m = m[m['diff'].notna()]
    pt, lo, hi, nm = boot_ci(m['diff'], m.E, level)
    _, ylo, yhi, ny = boot_ci(m['diff'], m.year, level)
    fr = m[m.segment == FRONT_LABEL]['diff']; bk = m[m.segment == BACK_LABEL]['diff']
    med = m['diff_med'].mean() if len(m) else np.nan
    return dict(main=pt, ci=[lo, hi], n_months=int(nm), year_ci=[ylo, yhi], n_years=int(ny),
                front=float(fr.mean()) if len(fr) else np.nan, n_front=int(len(fr)),
                back=float(bk.mean()) if len(bk) else np.nan, n_back=int(len(bk)),
                med_diff=float(med) if pd.notna(med) else np.nan,
                med_diff_alt_cross_month_median=float(m['diff'].median()) if len(m) else np.nan,
                n_pos=int((m['diff'] > 0).sum()), n_neg=int((m['diff'] < 0).sum()),
                n_zero=int((m['diff'].abs() < 1e-12).sum()))


def main_months(T):
    return set(T.E[T.n_excl >= M.MIN_EXCL_MAIN])


def pooled(r):
    r = pd.Series(r, dtype=float).dropna()
    return dict(n=int(len(r)), mean=float(r.mean()) if len(r) else np.nan, median=float(r.median()) if len(r) else np.nan)


def loo_dominance(B, gcol, rcol, months, idcol):
    """★F5：拿掉一檔（所有月份）重算主量（月份集合固定）。→ (主量, 影響表 DataFrame, 是否主導)"""
    base = cell(month_table(B, gcol, rcol), months)['main']
    sub = B[B.E.isin(months)]
    rows = []
    for s in sorted(sub[idcol].unique()):
        T2 = month_table(sub[sub[idcol] != s], gcol, rcol)
        v = T2[T2.E.isin(months) & T2['diff'].notna()]['diff'].mean()
        rows.append(dict(id=s, main_wo=v, delta=v - base, n_rows=int((sub[idcol] == s).sum()),
                         n_excl=int(((sub[idcol] == s) & (sub[gcol] == 1)).sum())))
    D = pd.DataFrame(rows)
    D['absd'] = D.delta.abs()
    D = D.sort_values('absd', ascending=False).reset_index(drop=True)
    flip = (np.sign(D.main_wo) != np.sign(base)) | (D.absd >= DOM_FRAC * abs(base))
    D['dominant'] = flip
    return base, D, bool(flip.any())


def seg_of(E):
    return FRONT_LABEL if E[:7] <= M.FRONT_END else BACK_LABEL


# ═════════════ 台美共用的分版本計算（市場差異只在 adapter：取根、報酬、仍可買、日曆） ═════════════
class TWAdapter:
    """台股：根索引用 st.at[E 字串]；報酬 hold_ret；仍可買＝fair_at（★1 主讀法期別）。"""
    def __init__(self, fv, STK):
        self.fv, self.STK, self.ncal, self.ci = fv, STK, len(fv.cal), fv.cal_idx

    def k(self, s, E):
        return self.STK[s].at[E]

    def ret(self, s, k, H):
        return hold_ret(self.STK[s], k, H, self.ncal)

    def still(self, s, k):
        D = self.STK[s].dates[k]
        self.fv.mode = 'upload'
        km, ey = M.kind_upload(D)
        r = self.fv.fair_at(s, D, km, ey)
        return np.nan if r is None else int(r['group_E'] == '可買')

    def cal_ok(self, E, H):
        return self.ci[E] + H < self.ncal


def version_block(BM, BA, vn, ad):
    """單一版本（年線／半年線）的主格與全部描述。BM＝主讀法可買列（含 R1、R3），BA＝★1 另一讀法可買列（None＝不算）。"""
    g = f'ld_{vn}'
    T = month_table(BM, g, 'R1')
    mm = main_months(T)
    c = cell(T, mm)
    c['verdict'] = verdict(c['main'], c['ci'][0], c['front'], c['back'], c['med_diff'])
    c['year_ci_note'] = '群數不足（%d 群），只描述' % c['n_years']
    c['year_lo_le0'] = bool(not (c['year_ci'][0] > 0))
    c['n_front_months_ge3'] = int(sum(1 for e in mm if seg_of(e) == FRONT_LABEL))
    c['n_back_months_ge3'] = int(sum(1 for e in mm if seg_of(e) == BACK_LABEL))
    d = dict(主格=c)
    ca = cell(T, None)
    ca['零差值月數'] = int((T['diff'].abs() < 1e-12).sum())
    ca['零差值月數_其中剔除組0檔'] = int(((T['diff'].abs() < 1e-12) & (T.n_excl == 0)).sum())
    d['全部月份版（只描述）'] = ca
    d['主量月份零差值月數'] = int((T[T.E.isin(mm)]['diff'].abs() < 1e-12).sum())
    d['拿掉2022（只描述）'] = cell(T, {e for e in mm if int(e[:4]) != YEAR_X})
    ex = BM[BM[g] == 1]
    d['剔除組筆數_2022'] = [int((ex.year == YEAR_X).sum()), int(len(ex))]
    three = (('全部可買', None), ('濾網組', 0), ('剔除組', 1))
    d['三組1年（全部月份，逐筆合併）'] = {k2: pooled(BM.R1[BM[g] == cc] if cc is not None else BM.R1) for k2, cc in three}
    Bm = BM[BM.E.isin(mm)]
    d['三組1年（主量月份，逐筆合併）'] = {k2: pooled(Bm.R1[Bm[g] == cc] if cc is not None else Bm.R1) for k2, cc in three}
    Tm = T[T.E.isin(mm)]
    d['剔除組_每月平均之平均（主量月份）'] = float(Tm.mean_excl.mean())
    d['剔除組_每月中位之平均（主量月份）'] = float(Tm.med_excl.mean())
    d['剔除組減全部可買_每月平均差之平均（主量月份）'] = float((Tm.mean_excl - Tm.mean_all).mean())
    T3 = month_table(BM, g, 'R3')
    d['3年（只描述）'] = cell(T3, {e for e in main_months(T3) if ad.cal_ok(e, M.H3)})
    d['3年三組（逐筆合併）'] = {k2: pooled(BM.R3[BM[g] == cc] if cc is not None else BM.R3) for k2, cc in three}
    if BA is not None:
        TA = month_table(BA, g, 'R1')
        d['★1另一讀法（只描述）'] = cell(TA, main_months(TA))
    base, D, dom = loo_dominance(BM, g, 'R1', mm, 'stock_id')
    d['少數股主導'] = dict(觸發=dom, 準則='拿掉單一檔後主量變號或 |變動| ≥ 0.5×|主量|',
                      前5檔=[dict(stock_id=r.id, 拿掉後主量=r.main_wo, 變動=r.delta, 主量月份筆數=r.n_rows,
                                其中剔除=r.n_excl, 觸發=bool(r.dominant)) for r in D.head(5).itertuples()])
    lst = sorted(set(D.head(3).id) | set(D.id[D.dominant]))
    rows = BM[BM.E.isin(mm) & BM.stock_id.isin(lst)].merge(T[['E', 'mean_all']], on='E')
    d['逐筆列表'] = [dict(E=E, stock_id=s, 組='剔除' if c_ == 1 else ('濾網' if c_ == 0 else '不判'), R1=r1, 當月全部可買平均=ma)
                 for E, s, c_, r1, ma in sorted(zip(rows.E, rows.stock_id, rows[g], rows.R1, rows.mean_all),
                                                key=lambda z: (z[1], z[0]))]
    d['放行對照'] = release_block(BM, vn, T, ad)
    return d, T


def release_block(BM, vn, T, ad):
    """★F6。"""
    x = BM[BM[f'ld_{vn}'] == 1]
    allm = dict(zip(T.E, T.mean_all))
    res = {}
    for tag, scol, bcol in (('主規則（站回同一條均線或均線轉平往上）', f'rel_main_{vn}', f'rel_main_bars_{vn}'),
                            ('季線（收盤 > MA60）', f'rel_ma60_{vn}', f'rel_ma60_bars_{vn}')):
        recs = []
        for E, s, stt, bars, r1 in zip(x.E, x.stock_id, x[scol], x[bcol], x.R1):
            rec = dict(E=E, stock_id=s, status=stt, R_block=r1, all_mean=allm.get(E), bars=np.nan)
            if stt == 'released':
                k = ad.k(s, E); kr = k + int(bars); st = ad.STK[s]
                rec.update(bars=int(bars), ratio=float(st.px[kr] / st.px[k]), still_buy=ad.still(s, kr))
                rec['R_rel'], rec['R_rel_status'] = ad.ret(s, kr, M.H1)
            recs.append(rec)
        Q = pd.DataFrame(recs)
        for col in ('ratio', 'still_buy', 'R_rel'):
            if col not in Q: Q[col] = np.nan
        rel = Q[Q.status == 'released']
        both = rel[rel.R_rel.notna() & rel.R_block.notna()]
        sb = rel.still_buy.dropna()
        res[tag] = dict(被擋=int(len(Q)), 放行=int(len(rel)), 截尾=int((Q.status == 'censored').sum()),
                        到快照尾未放行=int((Q.status == 'never').sum()),
                        放行_250根內=int((rel.bars <= M.H1).sum()),
                        隔幾根_中位=float(rel.bars.median()) if len(rel) else np.nan,
                        放行價比_中位=float(rel.ratio.median()) if len(rel) else np.nan,
                        放行時仍可買比例=float(sb.mean()) if len(sb) else np.nan, 放行時可判可買筆數=int(len(sb)),
                        放行日進場_1年=pooled(rel.R_rel), 放行日進場_1年不可算=int(rel.R_rel.isna().sum()),
                        同批被擋日進場_1年=pooled(both.R_block), 同批放行日進場_1年=pooled(both.R_rel),
                        同期全部可買_1年平均=float(both.all_mean.mean()) if len(both) else np.nan,
                        放行日進場減同期全部可買=float((both.R_rel - both.all_mean).mean()) if len(both) else np.nan)
        if tag.startswith('季線'):
            yes = Q[(Q.status == 'released') & (Q.bars <= M.H1)].R_block
            no = Q[(Q.status == 'never') | ((Q.status == 'released') & (Q.bars > M.H1))].R_block
            py, pn = pooled(yes), pooled(no)
            res['先站回季線vs沒站回（被擋日進場1年）'] = dict(先站回=py, 沒站回=pn,
                                                   平均差=py['mean'] - pn['mean'] if py['n'] and pn['n'] else np.nan,
                                                   中位差=py['median'] - pn['median'] if py['n'] and pn['n'] else np.nan)
    res['讀法'] = '〈四十八〉：放行日晚於被擋日＝晚進場設計；本件只有 1 年一個持有期，分不出「買得便宜」與「挑到的走勢不同」。'
    return res


def addon_block(BM, ad, month_all_mean):
    """★F7。"""
    res, rows = {}, []
    for E, d in BM.groupby('E'):
        a = d.R1.dropna()
        r = dict(E=E, n_nl=int((d.nl == 1).sum()), n_no=int((d.nl == 0).sum()))
        for tag, cc in (('nl', 1), ('no', 0)):
            v = d.R1[d.nl == cc].dropna()
            r[f'diff_{tag}'] = v.mean() - a.mean() if len(v) and len(a) else np.nan
        rows.append(r)
    Mt = pd.DataFrame(rows)
    for tag, cc, nm in (('nl', 1, '有新低'), ('no', 0, '沒新低')):
        res[nm] = dict(逐筆=pooled(BM.R1[BM.nl == cc]), 每月差_組減全部可買_平均=float(Mt[f'diff_{tag}'].mean()),
                       每月差可算月數=int(Mt[f'diff_{tag}'].notna().sum()),
                       每月檔數_中位最少最大=M.mstat(Mt[f'n_{tag}']), 有1檔以上月數=int((Mt[f'n_{tag}'] >= 1).sum()))
    res['全部可買'] = dict(逐筆=pooled(BM.R1))
    x = BM[BM.nl == 1]
    recs = []
    for E, s, r1 in zip(x.E, x.stock_id, x.R1):
        k = ad.k(s, E); st = ad.STK[s]
        t, why = M.delayed_entry(st, k)
        if t is None:
            continue
        R_, _ = ad.ret(s, t, M.H1)
        recs.append(dict(bars=t - k, ratio=float(st.px[t] / st.px[k]), still=ad.still(s, t), R_del=R_, R_eval=r1,
                         all_mean=month_all_mean.get(E)))
    Q = pd.DataFrame(recs)
    both = Q[Q.R_del.notna() & Q.R_eval.notna()]
    res['延後版'] = dict(有新低=int(len(x)), 找到延後進場=int(len(Q)), 延後根數_中位=float(Q.bars.median()),
                       進場價比_中位=float(Q.ratio.median()), 進場時仍可買比例=float(pd.Series(Q.still).dropna().mean()),
                       延後進場_1年=pooled(Q.R_del), 同批評估日進場_1年=pooled(both.R_eval), 同批延後進場_1年=pooled(both.R_del),
                       同期全部可買_1年平均=float(both.all_mean.mean()) if len(both) else np.nan,
                       讀法='〈四十八〉晚進場設計；只有 1 年一個持有期，分不出買得便宜與挑到走勢不同。')
    return res


def run_versions(BM, BA, ad, with_verdict=True):
    """兩版＋加碼對照 → (版本 dict, 每月表 dict, 加碼 dict)。"""
    V, TT, mam = {}, {}, {}
    for vn, _ in M.VERS:
        V[vn], TT[vn] = version_block(BM, BA, vn, ad)
        if not with_verdict:
            V[vn]['主格'].pop('verdict')
        for E, v in zip(TT[vn].E, TT[vn].mean_all):
            mam.setdefault(E, v)
    return V, TT, addon_block(BM, ad, mam)


# ═════════════ 台股正式跑 ═════════════
def compute_tw():
    vreg, vo = M.preflight()
    v101 = verify_seq101()
    fv = M.FairValueMonthly(M.SNAP)
    cal = fv.cal
    R, months, n_univ, STK = M.build(fv)
    ad = TWAdapter(fv, STK)
    B = R[(R.buy == 1) | (R.buy_alt == 1)].copy().reset_index(drop=True)
    B['year'] = B.E.str[:4].astype(int); B['segment'] = B.E.map(seg_of)
    r1, s1, r3, s3 = [], [], [], []
    for E, s in zip(B.E.values, B.stock_id.values):
        k = ad.k(s, E)
        a, b = ad.ret(s, k, M.H1); r1.append(a); s1.append(b)
        a, b = ad.ret(s, k, M.H3); r3.append(a); s3.append(b)
    B['R1'], B['R1_status'], B['R3'], B['R3_status'] = r1, s1, r3, s3
    assert ((B.R1_status == 'holdbad') == (B.holdbad_1y == 1)).all(), '1y 壞根旗標與頻率表不一致'
    BM = B[B.buy == 1].copy()
    out = dict(header=dict(登錄='產業 seq96 pw1 %s（%d B）＋產業 seq101 pw1 %s（%d B）' % (
        vreg['pw1'], vreg['bytes'], v101['pw1'], v101['bytes']),
        發號='裁定 seq498 §一（N_單筆 +2；97.5% CI；判語最多「通過（暫定）」）', 正式跑='裁定 seq499（--formal --ruling seq499）',
        資料commit=M.SNAP_COMMIT, sha_orig={k: v[0] for k, v in vo.items()}, SEED=SEED, NBOOT=NBOOT, CI=CI_LEVEL,
        月數=len(months), 評估日=[months[0], months[-1]]))
    out['持有窗壞根不計筆數_1年'] = int((BM.R1_status == 'holdbad').sum())
    out['出場前下市_1年'] = int((BM.R1_status == 'delisted').sum())
    V, TT, addon = run_versions(BM, B[B.buy_alt == 1], ad)
    vd = {vn: V[vn]['主格']['verdict'] for vn, _ in M.VERS}
    out['判語'] = vd
    out['採用'] = adopt(vd)
    out['版本'] = V
    out['加碼對照'] = addon
    out['結果句'] = result_sentences(out)
    os.makedirs(OUTF, exist_ok=True)
    keep = ['E', 'stock_id', 'buy', 'buy_alt', 'ld_年線', 'ld_半年線', 'nl', 'R1', 'R1_status', 'R3', 'R3_status']
    B[keep].to_csv(os.path.join(OUTF, 'tw_rows.csv'), index=False, encoding='utf-8-sig')
    pd.concat([TT[vn].assign(版本=vn) for vn, _ in M.VERS]).to_csv(os.path.join(OUTF, 'tw_month_table.csv'),
                                                                 index=False, encoding='utf-8-sig')
    return out


def pp(x):
    """差值 → ±x.xxpp。"""
    return "—" if x is None or not np.isfinite(x) else "%+.2fpp" % (100 * x)


def pc(x):
    """報酬 → ±x.x%。"""
    return "—" if x is None or not np.isfinite(x) else "%+.1f%%" % (100 * x)


def fail_reasons(c):
    """測不出時列出沒過的條件（只陳述，不改判）。"""
    if c.get('verdict') != VERDICT_FAIL:
        return ''
    r = []
    if not (c['ci'][0] is not None and c['ci'][0] > 0): r.append('CI 下緣 ≤ 0')
    if not (c['front'] is not None and c['front'] > 0): r.append('前段 ≤ 0')
    if not (c['back'] is not None and c['back'] > 0): r.append('後段 ≤ 0')
    if not (c['med_diff'] is not None and c['med_diff'] > 0): r.append('中位數差方向不一致')
    return '（未過：%s）' % '、'.join(r) if r else ''


def result_sentences(out):
    V = out['版本']; S = []
    for vn, _ in M.VERS:
        c = V[vn]['主格']
        S.append('%s版：%s。主量 %s（97.5%% 月分群 CI %s～%s，%d 個月）；前段 %s、後段 %s；中位數差 %s%s。' % (
            vn, c['verdict'], pp(c['main']), pp(c['ci'][0]), pp(c['ci'][1]), c['n_months'], pp(c['front']), pp(c['back']),
            pp(c['med_diff']), fail_reasons(c)))
        if c['year_lo_le0']:
            S.append('%s版按年分群看不出（年分群 97.5%% CI %s～%s，6 群，只描述）。' % (vn, pp(c['year_ci'][0]), pp(c['year_ci'][1])))
    fy, fh = V['年線']['主格']['n_front_months_ge3'], V['半年線']['主格']['n_front_months_ge3']
    assert (fy, fh) == (15, 17), (fy, fh)
    S.append('前段剔除組 ≥3 檔只有 %d／%d 個月，前段方向僅供參考。' % (fy, fh))
    S.append('同族先前一件：便宜＋趨勢轉強（還沒測，seq486）。')
    a, b = V['年線']['剔除組筆數_2022'], V['半年線']['剔除組筆數_2022']
    S.append('剔除組集中在 2022（年線 %d／%d、半年線 %d／%d）；拿掉 2022 進場後（只描述）：年線 %s（%d 個月）、半年線 %s（%d 個月）。' % (
        a[0], a[1], b[0], b[1], pp(V['年線']['拿掉2022（只描述）']['main']), V['年線']['拿掉2022（只描述）']['n_months'],
        pp(V['半年線']['拿掉2022（只描述）']['main']), V['半年線']['拿掉2022（只描述）']['n_months']))
    S.append('採用範圍：只限台股長期投資股、評估日一次進場持有 1 年；⛔ 不套到看板第二、三批加碼；美股只描述，要用須另外登錄。')
    S.append('本件對回落沉默：逐月配對量不到資金曲線的回落，結果不得引用為「能降低回落」。')
    S.append('相鄰月份持有期重疊約 11/12 ⇒ 月分群 CI 偏窄，判語最多「通過（暫定）」（裁定 seq498）；3 年只描述。')
    ad = out['採用']
    S.append('採用：%s。' % ('%s版（兩版都過採半年線版）' % ad if ad else '無（兩版都沒有通過；看板不加濾網，只提供描述數字）'))
    return S


def _js(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, set): return sorted(o)
    return str(o)


def _clean(o):
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, float) and not np.isfinite(o): return None
    return o


# ═════════════ 結果.md ═════════════
def _p(x):
    return pp(np.nan if x is None else x)


def _c(x):
    return pc(np.nan if x is None else x)


def _pool(d):
    return '%s／%s（%d 筆）' % (_c(d['mean']), _c(d['median']), d['n']) if d else '—'


def _main_rows(V, with_verdict):
    L = ['| 版本 | 月數 | 主量（濾網−全部可買） | 97.5% 月分群 CI | 按年分群 97.5% CI（群數不足（6 群），只描述） | 前段（月數） | 後段（月數） | 中位數差 |'
         + (' 判語 |' if with_verdict else ''),
         '|---|---:|---:|---|---|---:|---:|---:|' + ('---|' if with_verdict else '')]
    for vn in ('年線', '半年線'):
        c = V[vn]['主格']
        L.append('| %s版 | %d | **%s** | %s～%s | %s～%s | %s（%d） | %s（%d） | %s |' % (
            vn, c['n_months'], _p(c['main']), _p(c['ci'][0]), _p(c['ci'][1]), _p(c['year_ci'][0]), _p(c['year_ci'][1]),
            _p(c['front']), c['n_front'], _p(c['back']), c['n_back'], _p(c['med_diff']))
            + (' **%s** |' % c['verdict'] if with_verdict else ''))
    return L


def _desc_rows(V):
    L = ['| 描述（只描述、不判） | 年線版 | 半年線版 |', '|---|---|---|']
    def row(name, f):
        L.append('| %s | %s | %s |' % (name, f(V['年線']), f(V['半年線'])))
    def cellfmt(c):
        return '%s（%s～%s，%d 月；前 %s／後 %s；中位差 %s）' % (_p(c['main']), _p(c['ci'][0]), _p(c['ci'][1]), c['n_months'],
                                                  _p(c['front']), _p(c['back']), _p(c['med_diff']))
    row('全部月份版主量（97.5% 月分群 CI）', lambda v: cellfmt(v['全部月份版（只描述）']))
    row('零差值月數：全部月份（其中剔除組 0 檔）／主量月份', lambda v: '%d（%d）／%d' % (
        v['全部月份版（只描述）']['零差值月數'], v['全部月份版（只描述）']['零差值月數_其中剔除組0檔'], v['主量月份零差值月數']))
    row('主量月份 正／負 月數', lambda v: '%d／%d' % (v['主格']['n_pos'], v['主格']['n_neg']))
    row('〔★F2 另一讀法〕每月平均差的跨月中位數', lambda v: _p(v['主格']['med_diff_alt_cross_month_median']))
    row('拿掉 2022 進場（主量月份去 2022）', lambda v: cellfmt(v['拿掉2022（只描述）']))
    row('剔除組筆數：2022／全部', lambda v: '%d／%d' % tuple(v['剔除組筆數_2022']))
    for g in ('全部可買', '濾網組', '剔除組'):
        row('1 年 平均／中位（全部月份逐筆）%s' % g, lambda v, g=g: _pool(v['三組1年（全部月份，逐筆合併）'][g]))
    for g in ('全部可買', '濾網組', '剔除組'):
        row('1 年 平均／中位（主量月份逐筆）%s' % g, lambda v, g=g: _pool(v['三組1年（主量月份，逐筆合併）'][g]))
    row('剔除組 每月平均之平均／每月中位之平均（主量月份）', lambda v: '%s／%s' % (
        _c(v['剔除組_每月平均之平均（主量月份）']), _c(v['剔除組_每月中位之平均（主量月份）'])))
    row('剔除組 − 全部可買 每月平均差（主量月份）', lambda v: _p(v['剔除組減全部可買_每月平均差之平均（主量月份）']))
    row('3 年主量（剔除組 ≥3 檔且 +750 在日曆內）', lambda v: cellfmt(v['3年（只描述）']))
    for g in ('全部可買', '濾網組', '剔除組'):
        row('3 年 平均／中位（逐筆）%s' % g, lambda v, g=g: _pool(v['3年三組（逐筆合併）'][g]))
    if '★1另一讀法（只描述）' in V['年線']:
        row('★1 另一讀法（法定期限對應）主量', lambda v: cellfmt(v['★1另一讀法（只描述）']))
    return L


def _release_rows(V):
    L = ['| 放行對照（只描述、不計 N） | 年線 主規則 | 年線 季線 | 半年線 主規則 | 半年線 季線 |', '|---|---|---|---|---|']
    keys = []
    for vn in ('年線', '半年線'):
        R = V[vn]['放行對照']
        ks = [k for k in R if k.startswith('主規則')] + [k for k in R if k.startswith('季線')]
        keys.append([R[k] for k in ks])
    def row(name, f):
        L.append('| %s | %s |' % (name, ' | '.join(f(x) for pair in keys for x in pair)))
    row('被擋／放行／截尾／未放行', lambda x: '%d／%d／%d／%d' % (x['被擋'], x['放行'], x['截尾'], x['到快照尾未放行']))
    row('250 根內放行', lambda x: str(x['放行_250根內']))
    row('被擋到放行隔幾根（中位）', lambda x: '%.0f' % x['隔幾根_中位'] if x['隔幾根_中位'] is not None else '—')
    row('放行價比（放行收盤÷被擋收盤，中位）', lambda x: '%.3f' % x['放行價比_中位'] if x['放行價比_中位'] is not None else '—')
    row('放行時仍是可買', lambda x: '%.0f%%（%d 筆可判）' % (100 * x['放行時仍可買比例'], x['放行時可判可買筆數'])
        if x['放行時仍可買比例'] is not None else '—')
    row('放行日進場 1 年 平均／中位', lambda x: _pool(x['放行日進場_1年']))
    row('同批：被擋日進場 1 年 平均／中位', lambda x: _pool(x['同批被擋日進場_1年']))
    row('同批：放行日進場 1 年 平均／中位', lambda x: _pool(x['同批放行日進場_1年']))
    row('同期全部可買 1 年平均（逐筆對應）', lambda x: _c(x['同期全部可買_1年平均']))
    row('放行日進場 − 同期全部可買', lambda x: _p(x['放行日進場減同期全部可買']))
    return L


def _no_cmp(q):
    if q['沒站回']['n'] and q['先站回']['n']:
        return ''
    return '（被擋者幾乎全在 250 根內站回季線，「到期末都沒站回」0 筆 ⇒ 這項比較不成立；⛔ 未在看報酬後改切點）'


def write_md(od):
    A = json.load(open(os.path.join(od, 'result.json'), encoding='utf-8'))
    U = None
    up = os.path.join(od, 'us_result.json')
    if os.path.exists(up):
        U = json.load(open(up, encoding='utf-8'))
    h = A['header']; V = A['版本']
    L = ['# 長期下跌濾網（年線版／半年線版）——正式跑', '',
         '- 登錄：%s｜%s｜%s' % (h['登錄'], h['發號'], h['正式跑']),
         '- 資料：tw-stock-data `%s`（快照 .commit 已驗）%s' % (h['資料commit'], '｜美股 us-stock-data `%s`' % U['header']['資料commit'] if U else ''),
         '- 程式：`backtest/researchTWLongDownFilter.py`（正式；分組直接呼叫頻率表 `researchTWLongDownFilter_freq.build()`，同一份實作）、'
         '`researchUSLongDownFilter.py`（美股只描述）；自測 `researchTWLongDownFilter_check.py`。',
         '- 1 年＝評估日收盤進、+250 交易日收盤出（還原收盤；持有窗壞根不計 %d 筆；出場前下市 %d 筆）；組內同權；不扣成本（同原版）。' % (
             A['持有窗壞根不計筆數_1年'], A['出場前下市_1年']),
         '- bootstrap：按月分群 %d 次、97.5%%（N＝2）、種子 %d（寫死在程式檔頭）。' % (h['NBOOT'], h['SEED']),
         '- ⚠ 相鄰月份持有 1 年、重疊約 11/12 ⇒ **月分群 CI 偏窄**；判語最多「通過（暫定）」（裁定 seq498）。', '',
         '## 判語（檢定 N_單筆 +2）', '',
         '- **年線版：%s**｜**半年線版：%s**｜採用：%s' % (A['判語']['年線'], A['判語']['半年線'],
                                               (A['採用'] + '版') if A['採用'] else '無'), '',
         '## 結果句（必寫）', '']
    L += ['%d. %s' % (i + 1, s) for i, s in enumerate(A['結果句'])]
    L += ['', '## 主表（1 年；只取剔除組 ≥3 檔的月份，seq101 ①）', '']
    L += _main_rows(V, True)
    L += ['', '- 通過（暫定）＝月分群 CI 下緣 > 0，且前段、後段點估計各 > 0，且中位數差方向與平均一致；其餘一律測不出（負也寫測不出）。',
          '- 中位數差＝每月「濾網組中位 − 全部可買中位」的平均（★F2）。', '',
          '## 描述表（只描述、不判）', '']
    L += _desc_rows(V)
    L += ['', '## 少數股主導（★F5：拿掉單一檔後主量變號或變動 ≥ 主量一半）', '']
    for vn in ('年線', '半年線'):
        d = V[vn]['少數股主導']
        L.append('**%s版**：%s。影響最大前 5 檔（拿掉後主量／變動）：%s' % (
            vn, '觸發，逐筆列於下' if d['觸發'] else '未觸發（前 3 檔仍逐筆列出）',
            '；'.join('%s %s／%s%s' % (r['stock_id'], _p(r['拿掉後主量']), _p(r['變動']), '★' if r['觸發'] else '')
                     for r in d['前5檔'])))
        L += ['', '| 月 | 代號 | 組 | 1 年報酬 | 當月全部可買平均 |', '|---|---|---|---:|---:|']
        L += ['| %s | %s | %s | %s | %s |' % (r['E'][:7], r['stock_id'], r['組'], _c(r['R1']), _c(r['當月全部可買平均']))
              for r in V[vn]['逐筆列表']]
        L.append('')
    L += ['## 放行對照（seq96 §五；只描述、不判定、不計 N）', '']
    L += _release_rows(V)
    for vn in ('年線', '半年線'):
        q = V[vn]['放行對照']['先站回季線vs沒站回（被擋日進場1年）']
        L.append('- %s版 先站回季線（250 根內）vs 沒站回：%s vs %s；平均差 %s、中位差 %s%s。' % (
            vn, _pool(q['先站回']), _pool(q['沒站回']), _p(q['平均差']), _p(q['中位差']), _no_cmp(q)))
    L += ['- ' + V['年線']['放行對照']['讀法'], '']
    ad = A['加碼對照']
    L += ['## 加碼對照：不再創新低（只描述、不判定、不計 N）', '',
          '| | 1 年 平均／中位（逐筆） | 每月差：組 − 全部可買（月數） | 每月檔數 中位（最少～最大） | ≥1 檔月數 |', '|---|---|---|---|---:|']
    for nm in ('有新低', '沒新低'):
        x = ad[nm]
        L.append('| %s | %s | %s（%d） | %g（%d～%d） | %d |' % (nm, _pool(x['逐筆']), _p(x['每月差_組減全部可買_平均']), x['每月差可算月數'],
                                                           *x['每月檔數_中位最少最大'], x['有1檔以上月數']))
    L.append('| 全部可買 | %s | | | |' % _pool(ad['全部可買']['逐筆']))
    y = ad['延後版']
    L += ['', '- 延後版（有新低者等連續 5 根沒有 60 日新低才進場）：有新低 %d 筆、找到延後進場 %d；延後根數中位 %.0f；進場價 ÷ 評估日收盤 中位 %.3f；'
          '進場時仍可買 %.0f%%；延後進場 1 年 %s；同批評估日進場 %s vs 延後進場 %s；同期全部可買 %s。' % (
              y['有新低'], y['找到延後進場'], y['延後根數_中位'], y['進場價比_中位'], 100 * y['進場時仍可買比例'],
              _pool(y['延後進場_1年']), _pool(y['同批評估日進場_1年']), _pool(y['同批延後進場_1年']), _c(y['同期全部可買_1年平均'])),
          '- ' + y['讀法'], '']
    if U:
        L += ['## 美股（同規則；只描述、不判定、不計 N；逐筆只在 `~/us_work/longdown/`）', '',
              '- 1 年報酬照美股機械版 seq63（`researchUSFairValue.Holder.daily`：評估日收盤後 250 個 S&P 交易日的 panel 日報酬連乘）。', '']
        L += _main_rows(U['版本'], False)
        L += ['']
        L += _desc_rows(U['版本'])
        L += ['']
        L += _release_rows(U['版本'])
        for vn in ('年線', '半年線'):
            q = U['版本'][vn]['放行對照']['先站回季線vs沒站回（被擋日進場1年）']
            L.append('- 美股%s版 先站回季線 vs 沒站回：%s vs %s；平均差 %s%s。' % (vn, _pool(q['先站回']), _pool(q['沒站回']), _p(q['平均差']), _no_cmp(q)))
            d = U['版本'][vn]['少數股主導']
            L.append('- 美股%s版 少數股主導：%s（逐檔只在私有工作區）。' % (vn, '觸發' if d['觸發'] else '未觸發'))
        ua = U['加碼對照']
        L.append('- 美股加碼對照：有新低 %s（每月差 %s）、沒新低 %s（每月差 %s）、全部可買 %s；延後版 %d 筆、延後進場 1 年 %s、同批評估日進場 %s。' % (
            _pool(ua['有新低']['逐筆']), _p(ua['有新低']['每月差_組減全部可買_平均']), _pool(ua['沒新低']['逐筆']),
            _p(ua['沒新低']['每月差_組減全部可買_平均']), _pool(ua['全部可買']['逐筆']), ua['延後版']['找到延後進場'],
            _pool(ua['延後版']['延後進場_1年']), _pool(ua['延後版']['同批評估日進場_1年'])))
        L.append('')
    T = pd.read_csv(os.path.join(od, 'tw_month_table.csv'), encoding='utf-8-sig')
    L += ['## 台股每月（剔除組檔數、每月差；★＝主量月份）', '',
          '| 月 | 全部可買 | 年線 剔除 | 年線 濾網−全部 | 半年線 剔除 | 半年線 濾網−全部 |', '|---|---:|---:|---:|---:|---:|']
    ty = T[T['版本'] == '年線'].set_index('E'); th = T[T['版本'] == '半年線'].set_index('E')
    for E in ty.index:
        a, b = ty.loc[E], th.loc[E]
        L.append('| %s | %d | %d | %s%s | %d | %s%s |' % (E[:7], a.n_all, a.n_excl, _p(a['diff']), '★' if a.n_excl >= 3 else '',
                                                    b.n_excl, _p(b['diff']), '★' if b.n_excl >= 3 else ''))
    L += ['', '描述，不是買賣建議', '']
    open(os.path.join(od, '結果.md'), 'w', encoding='utf-8').write('\n'.join(L))


def main_formal():
    out = compute_tw()
    os.makedirs(OUTF, exist_ok=True)
    json.dump(_clean(out), open(os.path.join(OUTF, 'result.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1,
              default=_js)
    write_md(OUTF)
    print(json.dumps(_clean(dict(判語=out['判語'], 採用=out['採用'], 結果句=out['結果句'])), ensure_ascii=False, indent=1,
                     default=_js))


if __name__ == '__main__':
    m = gate(sys.argv[1:])
    if isinstance(m, tuple):
        sys.exit(m[1])
    main_formal()

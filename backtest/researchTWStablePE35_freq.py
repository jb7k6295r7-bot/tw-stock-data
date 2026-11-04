# -*- coding: utf-8 -*-
"""台股合理價機械版——「穩定溢價本益比 35」變體：頻率表＋描述欄乾跑（⛔ 不算任何報酬）。

登錄：產業 seq82（pw1 sha f79e37d619c9fb0f）；發號：裁定 seq495 §一（N_單筆 +2：台股、美股各 1；判語照〈四十九〉）。
原版：台股合理價機械版（產業 10/26 登錄；回測核對版 backtest/twfv_recheck/orig/bt.py＋value.py，結論.md）。
資料：tw-stock-data commit 8e5d22eb306895d15bd93643284330983c57a823（原跑那一版；~/twdata/8e5d22e… 唯讀快照，.commit 開跑先驗）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchTWStablePE35_freq.py

程式重用（⛔ 不改原版檔、不寫第二份實作）：
  - 合理價、品質門檻、財報可用日、本益比中位數：backtest/researchTWCheapTrend_fv.py 的 FairValue.fair_at（bt.py 照抄版，
    sha 驗 bt.py／value.py）；公式 path()／pv() 直接 import 自 orig/value.py。
  - 母體的市值 ≥ 300 億過濾：bt.py L166–173（fair_at 拿掉了這段 ⇒ 本檔用 fv.shares_fallback 補回同一段，
    並以 orig/detail.csv 逐筆核對母體與分組）。
  - 變體只換 pe_T：用 fair_at 回傳的 E0、g_used、pe_med、payout 重算 path()／pv()；其餘一字不動。

══════════ 新登錄規則（seq82 §二逐字）══════════
 穩定溢價（評估日當天三條全過才算）：
  1. 最近 5 個完整財年，每年 ROE ≥ 20%。
  2. 5 年沒有虧損，而且沒有任何一年 EPS 比前一年跌超過 30%。
  3. 評估日前 5 年（最少 3 年）季末本益比的第 25 百分位 ≥ 30。
 變體估值：穩定溢價者 pe_T＝min(評估日前本益比中位數, 35)；其餘照原版 min(中位數, 25)。折現 10%、分組門檻不變。
 重新分類組：變體判「可買」、原版不是「可買」的（公司 × 評估日）。

══════════ ★ 執行者定（看任何數字前寫死；另一讀法寫在〔〕）══════════
 ★1 「最近 5 個完整財年」＝原版 quality() 的同一 5 年（lp 為 Q4 ⇒ 該年起往前 5 年；否則前一年起往前 5 年，且該年年報
     須已可用〔上傳時戳嚴格早於評估日，seq352〕）。ROE＝歸母淨利 ÷ 年底歸母權益（原版口徑）；權益 ≤ 0 ⇒ 該年不過。
     任一年財報缺 ⇒ 三條的 1、2 不可算 ⇒ 不算穩定溢價（照報筆數）。
 ★2 虧損＝年度歸母淨利 < 0（原版 noloss 口徑）。EPS＝年度基本每股盈餘（fs_hist Q4 累計；原版成長率同欄）。
     「任何一年比前一年跌超過 30%」只比 5 年窗內相鄰 4 對（EPS_t ÷ EPS_{t−1} − 1 < −30% ⇒ 不過）；前一年 EPS ≤ 0 ⇒ 該對不可比 ⇒ 不過。
     〔另一讀法：連窗首年也和前一年比（共 5 對）⇒ 描述欄 n_stable_alt5pairs 照報，不改判〕。
 ★3 季末本益比＝stocks_per 每個日曆季（1–3、4–6、7–9、10–12 月）最後一列的 per；只收 per > 0（原版中位數同口徑；
     虧損季無本益比 ⇒ 不收）。窗＝[評估日 − 5 年, 評估日)（原版中位數同樣嚴格早於評估日）；季末日須 < 評估日。
     「最少 3 年」＝窗內最早一個有效季末點 ≤ 評估日 − 3 年（原版中位數的 3 年檢查同寫法）；不滿 ⇒ 第 3 條不可算 ⇒ 不算穩定溢價。
     第 25 百分位用 numpy 線性內插（np.percentile 預設）。
 ★4 穩定溢價家數的分母＝原版母體（評估日上市櫃、市值 ≥ 300 億）；另報其中過品質門檻的家數（只有過門檻的才有分組）。
 ★5 進場年＝評估日所在年（原版 cluster_ci 同）；群數＝重新分類組出現的評估日之進場年個數。
 ★6 描述欄乾跑只驗「算得出」：1 年／3 年報酬可算＝出場日（+250／+750 交易日）在日曆內、且原版硬斷點旗標
     （orig/detail.csv 的 brk_1y／brk_3y，原跑同一資料）為 0；大盤可算＝出場日在 market_tri.csv 的日期內（只讀日期欄）。
     ⛔ 不讀任何價格報酬欄、不算任何報酬。
"""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from researchTWCheapTrend_fv import FairValue, verify_orig, per_str, shift_years, path, pv, CAP_MIN  # noqa: E402

SNAP_COMMIT = '8e5d22eb306895d15bd93643284330983c57a823'
SNAP = os.path.expanduser('~/twdata/' + SNAP_COMMIT)
ORIG_DETAIL = os.path.join(HERE, 'twfv_recheck', 'orig', 'detail.csv')
OUT = os.path.join(HERE, 'resultsStablePE35', 'freq')
REG = '產業 seq82 pw1 f79e37d619c9fb0f'
RULING = '裁定 seq495 §一'
H1, H3 = 250, 750
PE_CAP_BASE, PE_CAP_STABLE = 25.0, 35.0
ROE_STABLE, EPS_DROP_MAX, PE_P25_MIN = 0.20, -0.30, 30.0
PE_WIN_YEARS, PE_MIN_YEARS = 5, 3
DISC = 0.10                                   # 原版 bt.py：pv(divs, term, 0.10)
MIN_N, MIN_DATES, MIN_CLUSTERS = 20, 8, 24    # seq82 §三＋〈四十九〉


def group_of(mult):
    # 原版 bt.py L202 同門檻（可買 ≤ 1.00、接近 ≤ 1.15、偏貴 > 1.15；E0 ≤ 0 ⇒ mult＝inf ⇒ 偏貴）
    return '可買' if mult <= 1.0 else ('接近' if mult <= 1.15 else '偏貴')


# ═════════════ 穩定溢價三條 ═════════════
def five_years(fv, s, E, lp):
    """★1：→ (rows［(年, 淨利, EPS, 權益)×5，舊→新］, why)；不可算 ⇒ (None, why)。"""
    if lp is None:
        return None, 'no_period'
    y, q = lp
    ya = y if q == 4 else y - 1
    if q != 4 and not fv.available(s, ya, 4, E):
        return None, 'annual_unavail'
    rows = []
    for yy in range(ya - 4, ya + 1):
        f = fv.FS.get((s, per_str(yy, 4))); b = fv.BS.get((s, per_str(yy, 4)))
        if f is None or b is None or any(pd.isna(v) for v in (f[0], f[1], b[0])):
            return None, 'fs_missing'
        rows.append((yy, f[0], f[1], b[0]))
    return rows, 'ok'


def eps_prev_year(fv, s, yy):
    f = fv.FS.get((s, per_str(yy, 4)))
    return None if f is None or pd.isna(f[1]) else f[1]


def cond12(fv, s, E, lp):
    rows, why = five_years(fv, s, E, lp)
    if rows is None:
        return 'na', 'na', why, None
    c1 = 'pass' if all(eq > 0 and ni / eq >= ROE_STABLE for _, ni, ep, eq in rows) else 'fail'
    noloss = all(ni >= 0 for _, ni, ep, eq in rows)
    def drops_ok(pairs):
        for a, b in pairs:
            if a is None or b is None or a <= 0 or (b / a - 1) < EPS_DROP_MAX:
                return False
        return True
    eps = [ep for _, ni, ep, eq in rows]
    pairs4 = list(zip(eps[:-1], eps[1:]))
    c2 = 'pass' if (noloss and drops_ok(pairs4)) else 'fail'
    # 另一讀法（★2〔〕）：窗首年也和前一年比
    alt = noloss and drops_ok([(eps_prev_year(fv, s, rows[0][0] - 1), eps[0])] + pairs4)
    return c1, c2, why, bool(alt)


def cond3(fv, s, E):
    """★3：→ ('pass'/'fail'/'na', p25, 點數)。"""
    pr = fv.load_per(s)
    lo = shift_years(E, PE_WIN_YEARS)
    h = pr.loc[lo:E]
    h = h[h.index < E]
    if len(h) == 0:
        return 'na', None, 0
    qk = pd.PeriodIndex(pd.to_datetime(h.index), freq='Q')
    last = h.groupby(qk).tail(1)                       # 每季最後一列
    lq = pd.PeriodIndex(pd.to_datetime(last.index), freq='Q')
    # 季末日須 < 評估日（該季已走完）
    done = (lq.end_time.normalize() < pd.Timestamp(E))
    last = last[np.asarray(done)]
    v = last[last.per > 0]
    if len(v) == 0 or v.index[0] > shift_years(E, PE_MIN_YEARS):
        return 'na', None, int(len(v))
    p25 = float(np.percentile(v.per.values.astype(float), 25))
    return ('pass' if p25 >= PE_P25_MIN else 'fail'), p25, int(len(v))


# ═════════════ 主程式 ═════════════
def main():
    assert open(os.path.join(SNAP, '.commit')).read().strip() == SNAP_COMMIT, 'snapshot .commit mismatch'
    vo = verify_orig(); assert all(v[1] for v in vo.values()), vo
    fv = FairValue(SNAP)
    evals = fv.eval_dates(2020, 2025)                   # 原版 bt.py：2020～2025 各 4 個
    assert len(evals) == 24
    tri_dates = set(pd.read_csv(os.path.join(SNAP, 'data', 'history', 'market_tri.csv'), usecols=['date'], dtype=str).date)
    od = pd.read_csv(ORIG_DETAIL, usecols=['date', 'stock_id', 'pass_q', 'group', 'brk_1y', 'brk_3y'],
                     dtype={'date': str, 'stock_id': str, 'group': str})
    od['group'] = od['group'].fillna('')
    OD = {(d, s): (int(p), g, int(b1), int(b3)) for d, s, p, g, b1, b3 in od.itertuples(index=False)}

    recs = []
    for E, kind, ey in evals:
        for s in fv.PX:
            r = fv.fair_at(s, E, kind, ey)
            if r is None:
                continue
            # bt.py L166–173：市值 ≥ 300 億（日股數缺 ⇒ lp 季股本 ÷ 10）
            sh = fv.PX[s].loc[E].shares
            if pd.isna(sh) or sh <= 0:
                sh = fv.shares_fallback(s, r['lp'])
            cap = r['close_E'] * sh if pd.notna(sh) else np.nan
            if not (cap >= CAP_MIN):
                continue
            c1, c2, why12, alt = cond12(fv, s, E, r['lp'])
            c3, p25, npts = cond3(fv, s, E)
            stable = (c1 == 'pass' and c2 == 'pass' and c3 == 'pass')
            rec = dict(date=E, entry_year=ey, stock_id=s, pass_q=r['pass_q'], group_orig=r['group_E'],
                       c1=c1, c2=c2, c3=c3, why12=why12, pe_p25=p25, pe_q_pts=npts, stable=stable,
                       stable_alt5pairs=bool(c1 == 'pass' and c3 == 'pass' and alt is True), pe_med=r.get('pe_med'))
            # 變體（cap 35／25 各算一次；cap 25 ＝ 一致性檢查）
            for tag, cap_s in (('var', PE_CAP_STABLE), ('chk25', PE_CAP_BASE)):
                g = ''
                if r['pass_q'] == 1 and r['group_E'] != '':
                    if r['E0'] > 0:
                        peT = min(r['pe_med'], cap_s if stable else PE_CAP_BASE)
                        divs, term = path(r['E0'], r['g_used'], peT, r['payout'])
                        g = group_of(r['close_E'] / pv(divs, term, DISC))
                    else:
                        g = group_of(np.inf)
                rec['group_' + tag] = g
            o = OD.get((E, s))
            rec['in_orig_detail'] = o is not None
            rec['group_orig_file'] = o[1] if o else None
            rec['brk_1y'] = o[2] if o else None
            rec['brk_3y'] = o[3] if o else None
            x1, x3 = fv.fwd(E, H1), fv.fwd(E, H3)
            rec['ok_1y'] = bool(x1 is not None and o is not None and o[2] == 0)
            rec['ok_3y'] = bool(x3 is not None and o is not None and o[3] == 0)
            rec['mkt_1y'] = bool(x1 is not None and x1 in tri_dates and E in tri_dates)
            rec['mkt_3y'] = bool(x3 is not None and x3 in tri_dates and E in tri_dates)
            recs.append(rec)
    R = pd.DataFrame(recs)
    R['reclass'] = (R.group_var == '可買') & (R.group_orig != '可買')
    os.makedirs(OUT, exist_ok=True)

    # ── 一致性 ──
    keys_new = set(zip(R.date, R.stock_id)); keys_old = set(OD)
    chk = {
        '母體(評估日,檔)_本檔': len(keys_new), '母體_orig_detail': len(keys_old),
        '母體只在本檔': len(keys_new - keys_old), '母體只在orig': len(keys_old - keys_new),
        '原版分組_fair_at_vs_orig_detail_不一致': int((R.group_orig != R.group_orig_file.fillna('')).sum()),
        '變體上限改回25_vs_原版分組_不一致': int((R.group_chk25 != R.group_orig).sum()),
        '變體上限改回25_vs_orig_detail_不一致': int((R.group_chk25 != R.group_orig_file.fillna('')).sum()),
        '變體只改穩定溢價者_非穩定溢價卻改組': int(((R.group_var != R.group_orig) & ~R.stable).sum()),
        'sha_orig': {k: v[0] for k, v in vo.items()},
    }

    # ── 每評估日 ──
    rows = []
    for (E, ey), d in R.groupby(['date', 'entry_year'], sort=True):
        q = d[d.pass_q == 1]
        rc = d[d.reclass]
        ob = d[d.group_orig == '可買']
        r = dict(eval=E, entry_year=int(ey), 母體=len(d), 過品質門檻=len(q),
                 穩定溢價=int(d.stable.sum()), 穩定溢價_過品質門檻=int(q.stable.sum()),
                 條1_ROE20_過=int((d.c1 == 'pass').sum()), 條2_無虧損且EPS未跌30_過=int((d.c2 == 'pass').sum()),
                 條3_季末PE_p25ge30_過=int((d.c3 == 'pass').sum()),
                 條12_不可算=int((d.c1 == 'na').sum()), 條3_不可算=int((d.c3 == 'na').sum()),
                 穩定溢價_另一讀法5對=int(d.stable_alt5pairs.sum()))
        for g in ('可買', '接近', '偏貴'):
            r['原版_' + g] = int((d.group_orig == g).sum())
            r['變體_' + g] = int((d.group_var == g).sum())
        r['重新分類組'] = len(rc)
        r['重新分類組_原接近'] = int((rc.group_orig == '接近').sum())
        r['重新分類組_原偏貴'] = int((rc.group_orig == '偏貴').sum())
        # 描述欄乾跑（只數可算筆數）
        r['乾跑_重新分類_1年可算'] = int(rc.ok_1y.sum())
        r['乾跑_原版可買_1年可算'] = int(ob.ok_1y.sum())
        r['乾跑_主格差可算'] = bool(rc.ok_1y.sum() > 0 and ob.ok_1y.sum() > 0)
        for tag in ('orig', 'var'):
            b = d[(d['group_' + tag] == '可買') & d.ok_1y]; e = d[(d['group_' + tag] == '偏貴') & d.ok_1y]
            r[f'乾跑_{tag}_可買減偏貴_1年可算'] = bool(len(b) > 0 and len(e) > 0)
        r['乾跑_重新分類對大盤_1年可算'] = bool(rc.ok_1y.sum() > 0 and d.mkt_1y.iloc[0])
        r['乾跑_重新分類_3年可算'] = int(rc.ok_3y.sum())
        r['乾跑_主格差_3年可算'] = bool(rc.ok_3y.sum() > 0 and ob.ok_3y.sum() > 0)
        rows.append(r)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, 'tw_freq_by_eval.csv'), index=False, encoding='utf-8-sig')

    # 逐筆明細（台股公開資料；⛔ 無任何報酬欄）：只放穩定溢價或分組有變的列
    cols = ['date', 'entry_year', 'stock_id', 'pass_q', 'c1', 'c2', 'c3', 'why12', 'pe_p25', 'pe_q_pts', 'stable',
            'stable_alt5pairs', 'pe_med', 'group_orig', 'group_var', 'reclass', 'ok_1y', 'ok_3y']
    R.loc[R.stable | R.stable_alt5pairs | (R.group_var != R.group_orig), cols].to_csv(
        os.path.join(OUT, 'tw_stable_rows.csv'), index=False, encoding='utf-8-sig')

    # ── 合計與判語（依構造）──
    rc = R[R.reclass]
    dates_rc = sorted(rc.date.unique()); yrs_rc = sorted(rc.entry_year.unique().tolist())
    main_dates = T[T['乾跑_主格差可算']]
    yrs_main = sorted(main_dates.entry_year.unique().tolist())
    trig = {'重新分類組<20筆': bool(len(rc) < MIN_N), '出現評估日<8': bool(len(dates_rc) < MIN_DATES),
            '進場年群數<24': bool(len(yrs_rc) < MIN_CLUSTERS)}
    universe_dates = sorted({e[2] for e in evals})
    gaps = R.groupby('why12').size().to_dict()
    S = {
        '登錄': REG, '發號': RULING, '資料commit': SNAP_COMMIT,
        '評估日數': int(len(T)), '評估日': [T['eval'].iloc[0], T['eval'].iloc[-1]],
        '原版可能的進場年（評估日的年）': universe_dates, '原版可能的群數上限': len(universe_dates),
        '穩定溢價家數_每評估日_中位_最少_最大': [float(T['穩定溢價'].median()), int(T['穩定溢價'].min()), int(T['穩定溢價'].max())],
        '穩定溢價且過品質門檻_中位_最少_最大': [float(T['穩定溢價_過品質門檻'].median()), int(T['穩定溢價_過品質門檻'].min()),
                                   int(T['穩定溢價_過品質門檻'].max())],
        '穩定溢價_涉及檔數': int(R.loc[R.stable, 'stock_id'].nunique()),
        '三條各自通過_每評估日中位': {c: float(T[c].median()) for c in ('條1_ROE20_過', '條2_無虧損且EPS未跌30_過', '條3_季末PE_p25ge30_過')},
        '另一讀法（EPS 比 5 對）穩定溢價_中位_最大': [float(T['穩定溢價_另一讀法5對'].median()), int(T['穩定溢價_另一讀法5對'].max())],
        '原版可買_中位_最少_最大': [float(T['原版_可買'].median()), int(T['原版_可買'].min()), int(T['原版_可買'].max())],
        '變體可買_中位_最少_最大': [float(T['變體_可買'].median()), int(T['變體_可買'].min()), int(T['變體_可買'].max())],
        '重新分類組': {'總筆數': int(len(rc)), '出現評估日數': len(dates_rc), '出現評估日': dates_rc,
                   '進場年': yrs_rc, '群數': len(yrs_rc), '涉及檔數': int(rc.stock_id.nunique()),
                   '原組_接近': int((rc.group_orig == '接近').sum()), '原組_偏貴': int((rc.group_orig == '偏貴').sum())},
        '還沒測觸發（依構造）': trig, '判語（依構造，不看報酬）': '還沒測' if any(trig.values()) else '未觸發（須正式跑）',
        '一致性檢查': chk,
        '描述欄乾跑（⛔ 只報筆數／算不算得出，不含報酬）': {
            '主格：重新分類組 1 年可算筆數': int(rc.ok_1y.sum()), '主格：重新分類組 3 年可算筆數': int(rc.ok_3y.sum()),
            '主格差（重新分類−原版可買）1 年算得出的評估日數': int(len(main_dates)), '其進場年群數': len(yrs_main),
            '原版 可買−偏貴 1 年算得出的評估日數': int(T['乾跑_orig_可買減偏貴_1年可算'].sum()),
            '變體 可買−偏貴 1 年算得出的評估日數': int(T['乾跑_var_可買減偏貴_1年可算'].sum()),
            '重新分類組對大盤 1 年算得出的評估日數': int(T['乾跑_重新分類對大盤_1年可算'].sum()),
            '主格差 3 年算得出的評估日數': int(T['乾跑_主格差_3年可算'].sum()),
            '穩定溢價家數': '每評估日皆算得出（見 tw_freq_by_eval.csv）',
            '說明': '1 年／3 年可算＝出場日在日曆內且原版硬斷點旗標 0；大盤＝出場日在 market_tri.csv 日期內。⛔ 未讀價格報酬欄。'},
        '資料缺口': {
            '條1條2不可算_原因_(評估日,檔)': {k: int(v) for k, v in gaps.items() if k != 'ok'},
            '條1條2不可算_涉及檔數': int(R.loc[R.c1 == 'na', 'stock_id'].nunique()),
            '條1條2不可算且過品質門檻': int(((R.c1 == 'na') & (R.pass_q == 1)).sum()),
            '條3不可算_(評估日,檔)': int((R.c3 == 'na').sum()),
            '條3不可算_涉及檔數': int(R.loc[R.c3 == 'na', 'stock_id'].nunique()),
            '條3不可算且過品質門檻': int(((R.c3 == 'na') & (R.pass_q == 1)).sum()),
            '處理': '任一條不可算 ⇒ 不算穩定溢價（變體 pe_T 照原版 25）；過品質門檻者五年財報必齊，故條1條2不可算只出現在未過門檻者。'
                   'stocks_per 從 2015-01-05 起，2020-04 評估日的 5 年窗從 2015-04 起，窗內完整。'},
    }
    with open(os.path.join(OUT, 'tw_freq_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x))
    pd.set_option('display.width', 250)
    print(T[['eval', '母體', '過品質門檻', '穩定溢價', '穩定溢價_過品質門檻', '條1_ROE20_過', '條2_無虧損且EPS未跌30_過',
             '條3_季末PE_p25ge30_過', '原版_可買', '變體_可買', '重新分類組']].to_string(index=False))
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()

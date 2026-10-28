# -*- coding: utf-8 -*-
"""便宜＋趨勢轉強【台股機械版合理價「可買」裡，趨勢轉強的 vs 沒轉強的】單筆層——正式程式（含頻率表／全部描述欄乾跑）。

登錄：登錄全文-便宜加趨勢轉強_機械版合理價可買裡轉強對沒轉強_60日_單筆層登錄_台股策略線_seq1_shaef2f1c05fbcbf841-5541B-20261028-1452.md
      （pw1 sha ef2f1c05fbcbf841＝去掉末行 pw1 戳記後全文 sha256 前 16 碼；整檔 5541 B；兩者回測線 2026-10-28 已驗）
發號：裁定 seq482 §一（判定 1 格 ⇒ N_單筆 +1；最多暫定）。
沿革：裁定 seq483 §2-1／§2-2／§2-3／§2-4＋seq484 §三（2026-10-28）：台股選 (a) 照原文跑、主格不改；准正式跑，
      判語事先固定「還沒測（依構造）」，報酬只當描述（⛔ 不得寫成測不出或測到了）；正式跑閘門 seq482 → seq484。
      ★4、★5、★10 照主讀法，另一讀法只描述。登錄錯兩處照記：① 登錄寫「財報 2013 起」，實際 fs_hist 2015Q1 起；
      ② 主格只有固定 60 日出場、沒有條件出場主臂，偏離 seq308（裁定 seq483 §2-3）。看報酬前只看過頻率表。
便宜：台股合理價機械版【回測核對版】＝ backtest/twfv_recheck/orig/bt.py＋value.py（回測核對相符，commit 77aafeb9bd），
      抄錄／import 見 researchTWCheapTrend_fv.py 檔頭。
資料：tw-stock-data 8e5d22eb306895d15bd93643284330983c57a823 唯讀快照 ~/twdata/8e5d22eb…（＝合理價核對用的同一份；
      git archive，.commit 開跑先驗）。登錄未指定資料版本 ⇒ 用核對版同一份；需要的路徑（meta、stocks、adj、mops/fs_hist、
      mops/bs_hist、stocks_per、history/market_tri.csv；0050 在 stocks/）都在，不另開快照。

用法（cd ~/tw-p17）：
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTWCheapTrend --dry
        ⇒ 頻率表＋全部描述欄乾跑（R 全寫 0；⛔ 不讀出、不印任何報酬）→ backtest/resultsTWCheapTrend/freq/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTWCheapTrend --formal --ruling seq484
        ⇒ 正式跑（⛔ 必須兩個旗標都給，否則拒跑）→ backtest/resultsTWCheapTrend/formal/

══════════ 登錄寫死的（照抄，不改）══════════
 便宜 C：判日收盤 ÷ 合理價 ≤ 1.00；合理價只在四個評估日（4/1、5/16、8/15、11/15 起第一個交易日）更新，其間沿用。
 母體 U：上市＋上櫃普通股（含已下市）、判日市值 ≥ 300 億、過品質門檻且算得出合理價。
 趨勢：MA60、MA250（還原收盤）；線上＝收盤 > 均線；上揚＝均線 > 20 個交易日前的均線；
       T1 多頭＝MA60 線上且上揚且 MA250 線上｜T2＝MA60 線上且下彎，或 MA60 線上而 MA250 線下｜
       T3＝MA60 線下、MA250 線上且上揚｜T4＝MA60、MA250 都線下且兩條都下彎｜T0＝其他；依序判、互斥。
       轉強＝T1∪T2；沒轉強＝T3∪T4∪T0；判日前不足 270 個有效交易日 ⇒ 趨勢不可判、不進任何格（照報件數）。
 判日：每月第一個交易日，2018-04 起到最後一個 60 日走得完的判日；進場＝判日次一交易日還原開盤；
       出場＝進場後第 60 個交易日還原收盤；扣 0.585% 來回；超額＝每筆 − 同判日 U 同口徑平均。
 主格 G：同判日 C∧轉強 平均超額 − C∧沒轉強 平均超額，對全部判日平均；3 個月一群抽群 bootstrap 95%、10,000 次、種子 20261028；
       前段 2018-04～2022-03、後段 2022-04 起。通過（暫定）＝G>0、CI 下緣>0、前後段各 >0；其餘測不出（負也寫測不出）；
       還沒測＝任一段 3 個月群數 < 24，或某段一半以上判日 C∧轉強、C∧沒轉強任一 < 3 檔。

══════════ ★ 執行者定（另一讀法寫在〔〕；看任何數字前寫死，皆取保守）══════════
 ★1 財報起點：登錄寫「財報 2013 起」，但寫死的核對版程式讀 mops/fs_hist，快照（與 tw-stock-data HEAD）fs_hist 都從 2015Q1 起
     ⇒ 品質門檻要 5 個完整年度，最早能過門檻的評估日是 2020-04-01；2018-04～2020-03 的判日 U＝0。
     照登錄判日範圍（2018-04 起）照列，這些判日記「U＝0」，算進「某段一半以上判日任一臂 < 3 檔」的分母與分子。
     〔另一讀法：判日從第一個有合理價的評估日 2020-04 起算；兩讀法的群數、不足判日數並報〕。⛔ 不改用 fs_xbrl 補 2013–14（會改寫死的程式輸入）。
 ★2 評估日與判日同一天（如 4 月第一個交易日）⇒ 用當天評估日的合理價（評估日 ≤ 判日，含等號）。〔另一讀法：嚴格早於判日〕
 ★3 合理價在評估日【對全部上市櫃普通股】算（評估日當天有成交者，同 bt.py L163）；市值 ≥ 300 億在【判日】判
     （判日收盤 × 判日股數；股數缺照 bt.py 用沿用評估日那季的股本÷10）。判日無成交 ⇒ 不在該判日 U。
     評估日無成交 ⇒ 到下一個評估日前都無合理價。〔另一讀法：評估日也要市值 ≥ 300 億才算合理價〕
 ★4「算得出合理價」：近四季 EPS ≤ 0（bt.py 記 mult=inf、歸偏貴）⇒ 合理價算不出 ⇒ 不進 U。〔另一讀法：照 bt.py 進 U、算非便宜〕
 ★5 現價＝判日【原始】收盤（登錄字面）。評估日到判日間若有股數基礎事件（除權／減資／面額變更／分割），原始收盤與評估日 EPS
     基礎不同——照字面不調；受影響筆數與「改用評估日股數基礎」後 C 翻轉筆數照報。〔另一讀法：收盤 ÷ Π(該區間股數事件因子)〕
 ★6 普通股＝meta/stocks.csv kind==stock（4 碼，含已下市）；上市櫃＝判日那根 market ∈ {twse, tpex}。
 ★7 有效交易日＝valid_bar==1 且 close>0 的根（同 bt.py）；均線、20 日前、270 根都數【該檔自己的有效根】（不數市場日曆）。
     〔另一讀法：按市場日曆數〕。270 根含判日當根（MA250 在判日與 20 根前都要有值＝250+20）。〔另一讀法：判日之前 270 根、不含當根〕
 ★8 線上／上揚都用嚴格 >；相等算線下／下彎。
 ★9 硬斷點（全線規則 seq335：research11 缺口規則）：壞根＝與上一有效根之間缺 ≥ 5 個交易日（無流動性前提）、或相鄰收盤比
     ≤0.55／≥1.8 且區間內無還原事件、或還原事件當根的幽靈比（research11 L130–148 照抄語意）。
     回看窗（判日往回 270 根）內有壞根 ⇒ 趨勢不可判（與「不足 270 根」分開照報）；持有窗（進場根, 出場根] 有壞根 ⇒ 該筆報酬不可算。
     〔另一讀法：只管持有窗〕。早年 reduce_v2 只涉 2015 前資料，本件資料 2015 起，不適用。
 ★10 進場：判日次一個市場交易日當檔要有有效根，否則該筆不進場（照報）；出場日＝市場日曆上進場日後第 60 個交易日
     （日曆位置 +60）；出場日無成交或已下市 ⇒ 用出場日（含）之前最後一根還原收盤（同 bt.py ret()）。〔另一讀法：+59〕
     「60 日走得完」＝出場日在快照最後一個交易日之內。
 ★11 成本：報酬 − 0.585%（減法，字面「扣」）。〔另一讀法：(1+r)(1−0.585%)−1〕
 ★12 U 同口徑平均：U 內所有報酬可算的筆（含趨勢不可判者——U 由 §一定義，與趨勢無關）。〔另一讀法：U 只取趨勢可判者〕
     主格某判日任一臂 0 筆可算 ⇒ 該判日差值缺、不進 G 平均（照報日數）。
 ★13 3 個月群＝日曆季（1–3、4–6、7–9、10–12 月；2018-04 起正好對齊，前後段切點也落在季界）；群數＝該段有主格差值的群
     〔另一讀法：該段判日涵蓋的全部日曆季〕；兩種都報，觸發判斷取保守（任一 < 24 即觸發）。
     bootstrap：抽群（放回）、把抽中群的判日差值串起來取平均（同 bt.py cluster_ci 寫法），種子 20261028、10,000 次。
 ★14「某段一半以上判日任一臂 < 3 檔」：檔數＝報酬可算的筆數（正式）〔另一讀法：成員檔數，不管報酬可不可算〕；
     「一半以上」含剛好一半（≥ n/2）。分母＝該段全部判日（含 U＝0 的判日，見 ★1）。
 ★15 描述①「五個狀態各自」＝C∧T0～T4；另加 U∧T0～T4（只多報，不判）。「C∧T2 單獨 − C∧其他」的其他＝C 內趨勢可判且非 T2。
 ★16 描述②1 年：判日＝四個評估日（2018 起、250 日走得完者），進場判日次一交易日開盤、出場日曆位置 +250 的收盤，
     其餘同 60 日口徑。〔另一讀法：bt.py 的評估日收盤→+250 收盤〕
 ★17 描述③大盤報酬指數只有收盤 ⇒ 用判日收盤→出場日收盤〔另一讀法：進場日收盤起〕；0050 用同口徑（次日還原開盤→出場還原收盤，
     扣同成本）。
 ★18 描述⑤「去掉最大 1 筆的平均」：以筆（判日×檔）池化；分年＝判日所在年。主格本身是判日層平均。
 ★19 描述④多頭排列＝收盤 > MA20 > MA60（還原、嚴格）；重疊率＝兩者都成立 ÷ 轉強（及 ÷ 多頭排列、Jaccard）。

══════════ 乾跑先做的等價檢查（seq377）══════════
 T1∪T2 ＝ MA60 線上 ∧ [(上揚∧MA250 線上) ∨ ¬(上揚∧MA250 線上)] ＝【收盤 > MA60】。
 ⇒ 主格的「轉強」恆等於「收盤 > MA60」（MA250、兩條斜率對主格不起作用，只剩 270 根暖身與 ★9 回看壞根）；
   「沒轉強」恆等於「收盤 ≤ MA60」。check 腳本以隨機序列驗證；頻率表也逐筆驗證。⇒ 依 seq377 回報，正式跑等裁定。
"""
import os, sys, json, argparse, math
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from researchTWCheapTrend_fv import FairValue, verify_orig, F_series, CAP_MIN  # noqa: E402

SNAP = os.path.expanduser('~/twdata/8e5d22eb306895d15bd93643284330983c57a823')
SNAP_COMMIT = '8e5d22eb306895d15bd93643284330983c57a823'
OUT = os.path.join(HERE, 'resultsTWCheapTrend')
H60, H1Y = 60, 250
COST = 0.00585
SEED, NBOOT = 20261028, 10000
WARM = 270
J_START = '2018-04'
FRONT_END = '2022-03'      # 前段 ≤ 2022-03；後段 ≥ 2022-04
MIN_CLUSTERS, MIN_ARM = 24, 3
RULING = 'seq484'          # 正式跑閘門（沿革：seq482 → seq484）
FIXED_VERDICT = '還沒測（依構造）'   # 裁定 seq483 §2-2、seq484 §三：事先固定，不看數字
RESULT_SENTENCES = [
    '主格的『轉強』恆等於收盤 > MA60（seq377 等價，回測 1548）',
    '依構造還沒測：財報 2015Q1 起、最早 2020-04，兩段群數 < 24',
    '台美主格口徑不同（台股 T1∪T2、60 日；美股 T2、1 年）',
]
REG_ERRORS = [
    '登錄錯①：登錄寫「財報 2013 起」，實際 fs_hist 2015Q1 起（最早能過品質門檻的評估日 2020-04-01）',
    '登錄錯②：主格只有固定 60 日出場、沒有條件出場主臂，偏離 seq308（裁定 seq483 §2-3）',
]
NAMES = {1: 'T1', 2: 'T2', 3: 'T3', 4: 'T4', 0: 'T0', -1: '不可判'}


# ═════════════════ 趨勢（純函式；check 腳本直接測） ═════════════════
def classify(above60, up60, above250, up250):
    """登錄 §二，依序判、互斥。輸入布林陣列，回傳 0～4。"""
    above60, up60, above250, up250 = map(np.asarray, (above60, up60, above250, up250))
    st = np.zeros(above60.shape, int)                      # T0 其他
    t1 = above60 & up60 & above250
    t2 = (above60 & ~up60) | (above60 & ~above250)
    t3 = ~above60 & above250 & up250
    t4 = ~above60 & ~above250 & ~up60 & ~up250
    done = np.zeros(above60.shape, bool)
    for code, m in ((1, t1), (2, t2), (3, t3), (4, t4)):
        st[m & ~done] = code; done |= m
    return st


def trend_states(c):
    """c：還原收盤（該檔有效根序列）。回傳 dict：state（-1＝暖身不足）、ma20/60/250、above60 等。"""
    c = np.asarray(c, float); n = len(c); s = pd.Series(c)
    ma20 = s.rolling(20, min_periods=20).mean().to_numpy()
    ma60 = s.rolling(60, min_periods=60).mean().to_numpy()
    ma250 = s.rolling(250, min_periods=250).mean().to_numpy()
    lag = lambda a, k: np.concatenate([np.full(k, np.nan), a[:-k]]) if n > k else np.full(n, np.nan)
    with np.errstate(invalid='ignore'):
        above60 = c > ma60; above250 = c > ma250
        up60 = ma60 > lag(ma60, 20); up250 = ma250 > lag(ma250, 20)
    st = classify(above60, up60, above250, up250)
    warm = (np.arange(n) + 1) >= WARM
    st = np.where(warm, st, -1)
    with np.errstate(invalid='ignore'):
        bull = (c > ma20) & (ma20 > ma60)
    return dict(state=st, warm=warm, ma20=ma20, ma60=ma60, ma250=ma250, above60=above60, bull=bull)


def bad_bars(dates, pos, rc, adj):
    """★9：research11 load_bars L130–148 的壞根語意。dates：有效根日期（str，遞增）；pos：日曆位置；rc：原始收盤；
    adj：該檔還原事件（date、factor）。回傳布林陣列 bad[k]＝第 k 根與前一根之間不連續。"""
    n = len(dates); bad = np.zeros(n, bool)
    if n < 2: return bad
    dates = np.asarray(dates); pos = np.asarray(pos); rc = np.asarray(rc, float)
    gap = np.diff(pos) - 1
    bad[1:] |= gap >= 5
    ev = np.sort(np.asarray(adj.date.values, dtype=str)) if len(adj) else np.array([], dtype=str)
    ratio = rc[1:] / rc[:-1]
    jump = (ratio <= 0.55) | (ratio >= 1.8)
    for t in np.flatnonzero(jump) + 1:
        if not ((ev > dates[t - 1]) & (ev <= dates[t])).any(): bad[t] = True
    if len(adj):
        for d, f in zip(adj.date.values, adj.factor.values):
            k = int(np.searchsorted(dates, d))
            if k >= n or k == 0 or not (f > 0): continue
            r = rc[k] / (rc[k - 1] * f)
            if r < 0.895 or r > 1.105: bad[k] = True
    return bad


def share_basis_factor(adj, E, J):
    """★5：(E, J] 之間股數基礎事件（kind 含「權」、或 event ∈ reduce/parvalue/etfsplit）的因子連乘；無 ⇒ 1。"""
    if not len(adj): return 1.0, 0
    a = adj[(adj.date > E) & (adj.date <= J)]
    if not len(a): return 1.0, 0
    kind = a.get('kind', pd.Series('', index=a.index)).fillna('').astype(str)
    evt = a.get('event', pd.Series('', index=a.index)).fillna('').astype(str)
    m = kind.str.contains('權') | evt.isin(['reduce', 'parvalue', 'etfsplit'])
    f = a.factor[m]
    return (float(np.prod(f.values)) if len(f) else 1.0), int(m.sum())


# ═════════════════ 資料組裝 ═════════════════
class Bars:
    """每檔有效根序列＋趨勢＋壞根。"""
    def __init__(self, fv):
        self.fv = fv; self.B = {}
        for s, p in fv.PX.items():
            dates = p.index.values.astype(str)
            pos = np.array([fv.cal_idx.get(d, -1) for d in dates])
            keep = pos >= 0
            if not keep.all(): p = p[keep]; dates = dates[keep]; pos = pos[keep]
            tr = trend_states(p.adj.values)
            bad = bad_bars(dates, pos, p.close.values, fv.ADJ[s])
            cb = np.concatenate([[0], np.cumsum(bad)])
            self.B[s] = dict(dates=dates, pos=pos, at={d: i for i, d in enumerate(dates)}, close=p.close.values,
                             adj=p.adj.values, adj_open=p.adj_open.values if 'adj_open' in p else np.full(len(p), np.nan),
                             market=p.market.values, shares=p.shares.values, cumbad=cb, **tr)

    def bad_between(self, s, k0, k1):
        """壞根落在 (k0, k1]（根索引）"""
        b = self.B[s]['cumbad']; return (b[k1 + 1] - b[k0 + 1]) > 0

    def lookback_bad(self, s, k):
        """回看窗 270 根（k−269..k）內的不連續 ⇒ 壞根索引落在 [k−268, k]"""
        lo = max(k - WARM + 1, 0); return self.bad_between(s, lo, k)


def judgment_dates(cal, horizon):
    last = len(cal) - 1; out = []; seen = set()
    for i, d in enumerate(cal):
        ym = d[:7]
        if ym < J_START or ym in seen: continue
        seen.add(ym)
        if i + 1 + horizon <= last: out.append(d)
    return out


def cluster_of(d):
    return f'{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}'


def segment_of(d):
    return 'front' if d[:7] <= FRONT_END else 'back'


def build_panel(fv, bars, FAIR, eval_list, J_list, horizon, use_eval_as_J=False):
    """每判日 U 成員一列（只 U 候選：評估日過門檻者）；另回傳每判日 市值≥300億 的檔數。"""
    cal, ci = fv.cal, fv.cal_idx
    ev_dates = [e[0] for e in eval_list]
    rows, nmcap = [], {}
    for J in J_list:
        Es = [e for e in ev_dates if e <= J]                                    # ★2 含等號
        E = Es[-1] if Es else None
        iJ = ci[J]; entry_day = cal[iJ + 1]; exit_day = cal[iJ + 1 + horizon]
        nm = 0
        for s, b in bars.B.items():
            k = b['at'].get(J)
            if k is None or b['market'][k] not in ('twse', 'tpex'): continue
            rec = FAIR.get(E, {}).get(s) if E else None
            sh = b['shares'][k]
            if pd.isna(sh) or sh <= 0:
                sh = fv.shares_fallback(s, rec['lp']) if rec else np.nan
            cap = b['close'][k] * sh if pd.notna(sh) else np.nan
            if not (cap >= CAP_MIN): continue
            nm += 1
            if rec is None or rec['pass_q'] != 1: continue
            fair_ok = pd.notna(rec['fair'])
            r = dict(J=J, stock_id=s, E=E, mcap_e8=round(cap / 1e8, 1), close_J=b['close'][k], fair=rec['fair'],
                     fair_ok=int(fair_ok))
            r['mult_J'] = b['close'][k] / rec['fair'] if fair_ok else np.nan
            r['C'] = int(fair_ok and r['mult_J'] <= 1.0)
            f, nev = share_basis_factor(fv.ADJ[s], E, J)
            r['n_share_ev'] = nev
            r['C_alt5'] = int(fair_ok and (b['close'][k] / f) / rec['fair'] <= 1.0)
            kE = b['at'].get(E)
            r['bad_E_J'] = int(kE is not None and bars.bad_between(s, kE, k))
            # 趨勢
            st = int(b['state'][k]); r['n_bars'] = k + 1
            r['warm_ok'] = int(b['warm'][k]); r['lb_bad'] = int(bars.lookback_bad(s, k)) if r['warm_ok'] else 0
            r['state'] = st if (r['warm_ok'] and not r['lb_bad']) else -1
            r['judg'] = int(r['state'] >= 0)
            r['above60'] = int(bool(b['above60'][k])) if r['judg'] else -1
            r['bull'] = int(bool(b['bull'][k])) if r['judg'] else -1
            # 持有可算性（不算報酬）
            ke = b['at'].get(entry_day)
            r['entry_ok'] = int(ke is not None)
            kx = int(np.searchsorted(b['dates'], exit_day, side='right')) - 1
            r['exit_bar_date'] = b['dates'][kx] if (ke is not None and kx >= ke) else None
            r['delisted_before_exit'] = int(ke is not None and b['dates'][-1] < exit_day)
            r['hold_bad'] = int(ke is not None and kx > ke and bars.bad_between(s, ke, kx))
            r['ret_ok'] = int(r['entry_ok'] and r['exit_bar_date'] is not None and not r['hold_bad'] and r['fair_ok'])
            r['_ke'] = ke if ke is not None else -1; r['_kx'] = kx
            r['in_U'] = int(fair_ok)
            rows.append(r)
        nmcap[J] = nm
    P = pd.DataFrame(rows)
    return P, nmcap


def attach_returns(P, bars, dry, horizon_tag):
    """正式：60 日／1 年報酬（扣成本）。乾跑：R 全寫 0（seq366），⛔ 不讀價格算報酬。"""
    if dry:
        P['R'] = np.where(P.ret_ok == 1, 0.0, np.nan); return P
    R = []   # 註：itertuples 會把底線開頭欄（_ke、_kx）改名，故用 zip 逐欄取（2026-10-28 正式跑首跑 AttributeError 後修，邏輯不變）
    for ok_, sid, ke, kx in zip(P.ret_ok.values, P.stock_id.values, P['_ke'].values, P['_kx'].values):
        if not ok_: R.append(np.nan); continue
        b = bars.B[sid]
        R.append(b['adj'][int(kx)] / b['adj_open'][int(ke)] - 1 - COST)
    P['R'] = R; return P


def bench_returns(fv, J_list, horizon, dry):
    """描述③：大盤報酬指數（判日收盤→出場日收盤）、0050（次日還原開盤→出場還原收盤，扣成本）。乾跑只記可算與否。"""
    tri = pd.read_csv(f'{fv.D}/history/market_tri.csv', dtype={'date': str}).set_index('date').close.astype(float)
    p = fv.load_px('0050'); a = fv.load_adj('0050')
    p['adj'] = p.close.values * F_series(p.index.values, a); p['adj_open'] = p.open.values * F_series(p.index.values, a)
    out = {}
    for J in J_list:
        i = fv.cal_idx[J]; en = fv.cal[i + 1]; ex = fv.cal[i + 1 + horizon]
        tri_ok = J in tri.index and ex in tri.index
        e50_ok = en in p.index and len(p.loc[:ex]) > 0
        if dry:
            out[J] = dict(tri_ok=int(tri_ok), e50_ok=int(e50_ok), TRI=0.0 if tri_ok else np.nan, E50=0.0 if e50_ok else np.nan)
        else:
            out[J] = dict(tri_ok=int(tri_ok), e50_ok=int(e50_ok),
                          TRI=tri[ex] / tri[J] - 1 if tri_ok else np.nan,
                          E50=p.loc[:ex].adj.iloc[-1] / p.loc[en].adj_open - 1 - COST if e50_ok else np.nan)
    return out


# ═════════════════ 彙總（正式與乾跑共用同一段程式） ═════════════════
def arm_masks(P):
    j = P.judg == 1; C = P.C == 1; U = P.in_U == 1
    m = {'C∧轉強': U & C & j & P.state.isin([1, 2]),
         'C∧沒轉強': U & C & j & P.state.isin([0, 3, 4]),
         'C∧T4': U & C & j & (P.state == 4),
         '非C∧轉強': U & ~C & j & P.state.isin([1, 2]),
         'U全部': U,
         'C∧T2': U & C & j & (P.state == 2),
         'C∧非T2': U & C & j & P.state.isin([0, 1, 3, 4])}
    for k in (0, 1, 2, 3, 4):
        m[f'C∧T{k}'] = U & C & j & (P.state == k)
    for k in (0, 1, 2, 3, 4):
        m[f'U∧T{k}'] = U & j & (P.state == k)
    return m


def add_excess(P):
    ok = P.R.notna() & (P.in_U == 1)
    um = P[ok].groupby('J').R.mean()
    P['U_mean'] = P.J.map(um); P['X'] = P.R - P.U_mean
    return P


def date_diff(P, a, b, masks):
    g = []
    for J, d in P.groupby('J'):
        ma, mb = masks[a][d.index], masks[b][d.index]
        xa, xb = d.X[ma].dropna(), d.X[mb].dropna()
        g.append(dict(J=J, n_a=len(xa), n_b=len(xb), diff=(xa.mean() - xb.mean()) if len(xa) and len(xb) else np.nan))
    return pd.DataFrame(g)


def cluster_boot(df, col='diff'):
    v = df[['J', col]].dropna()
    if v.empty: return np.nan, np.nan, np.nan, 0
    v = v.assign(cl=v.J.map(cluster_of)); cls = sorted(v.cl.unique()); by = {c: v[v.cl == c][col].values for c in cls}
    rng = np.random.default_rng(SEED); bs = np.empty(NBOOT)
    for i in range(NBOOT):
        pick = rng.choice(len(cls), size=len(cls), replace=True)
        bs[i] = np.concatenate([by[cls[j]] for j in pick]).mean()
    return v[col].mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), len(cls)


def triggers(J_all, G, arm_n_a, arm_n_b):
    """還沒測觸發（只用筆數，乾跑可算）。arm_n_*：dict J→該臂筆數。"""
    out = {}
    for seg in ('front', 'back'):
        Js = [J for J in J_all if segment_of(J) == seg]
        cal_cl = sorted({cluster_of(J) for J in Js})
        gd = G[G.J.isin(Js) & G['diff'].notna()]
        data_cl = sorted({cluster_of(J) for J in gd.J})
        lt3 = [J for J in Js if arm_n_a.get(J, 0) < MIN_ARM or arm_n_b.get(J, 0) < MIN_ARM]
        out[seg] = dict(n_dates=len(Js), n_clusters_calendar=len(cal_cl), n_clusters_with_diff=len(data_cl),
                        n_dates_arm_lt3=len(lt3), half=len(Js) / 2,
                        trig_clusters=bool(min(len(cal_cl), len(data_cl)) < MIN_CLUSTERS),
                        trig_clusters_cal=bool(len(cal_cl) < MIN_CLUSTERS), trig_clusters_data=bool(len(data_cl) < MIN_CLUSTERS),
                        trig_lt3=bool(len(Js) > 0 and len(lt3) >= len(Js) / 2))
    out['還沒測'] = bool(any(out[s]['trig_clusters'] or out[s]['trig_lt3'] for s in ('front', 'back')))
    return out


def cell_stats(P, mask, col):
    """描述⑤：判日層平均、筆層平均／中位／去最大 1 筆平均、分年。"""
    d = P[mask & P[col].notna()]
    x = d[col].values
    st = dict(n_records=len(x), n_dates=int(d.J.nunique()),
              date_mean=float(d.groupby('J')[col].mean().mean()) if len(x) else np.nan,
              rec_mean=float(x.mean()) if len(x) else np.nan,
              rec_median=float(np.median(x)) if len(x) else np.nan,
              rec_mean_ex_max1=float(np.sort(x)[:-1].mean()) if len(x) >= 2 else np.nan)
    st['by_year'] = {y: dict(n=int(len(g)), mean=float(g[col].mean())) for y, g in d.groupby(d.J.str[:4])}
    return st


def describe(P, masks, bench, label):
    D = {}
    for cell in ('C∧轉強', 'C∧T4', '非C∧轉強', 'U全部', 'C∧T0', 'C∧T1', 'C∧T2', 'C∧T3', 'C∧T4', 'U∧T0', 'U∧T1', 'U∧T2',
                 'U∧T3', 'U∧T4', 'C∧沒轉強', 'C∧非T2'):
        D[f'{label}|{cell}|超額'] = cell_stats(P, masks[cell], 'X')
    D[f'{label}|U全部|報酬(非超額)'] = cell_stats(P, masks['U全部'], 'R')
    g = date_diff(P, 'C∧T2', 'C∧非T2', masks)
    pt, lo, hi, ncl = cluster_boot(g)
    D[f'{label}|C∧T2−C∧其他|判日差'] = dict(n_dates=int(g['diff'].notna().sum()), mean=pt, ci=[lo, hi], n_clusters=ncl)
    g2 = date_diff(P, 'C∧轉強', 'C∧沒轉強', masks)
    D[f'{label}|主格同式(C∧轉強−C∧沒轉強)|判日差'] = dict(n_dates=int(g2['diff'].notna().sum()), mean=float(g2['diff'].mean()))
    # ③ 對大盤
    m = masks['C∧轉強'] & P.R.notna()
    d = P[m].copy()
    d['TRI'] = d.J.map(lambda J: bench[J]['TRI']); d['E50'] = d.J.map(lambda J: bench[J]['E50'])
    for nm, col in (('大盤報酬指數', 'TRI'), ('0050', 'E50')):
        z = (d.R - d[col]).dropna()
        D[f'{label}|C∧轉強−{nm}|筆層'] = dict(n_records=len(z), mean=float(z.mean()) if len(z) else np.nan,
                                           median=float(z.median()) if len(z) else np.nan)
    return D


def nonreturn_desc(P):
    """描述④（不涉報酬，乾跑照實算）。"""
    U = (P.in_U == 1); j = P.judg == 1; C = P.C == 1
    q = P[U & j]
    turn = q.state.isin([1, 2]); bull = q.bull == 1
    out = dict(n_U_judg=len(q),
               overlap_bull_given_turn=float((turn & bull).sum() / turn.sum()) if turn.sum() else np.nan,
               overlap_turn_given_bull=float((turn & bull).sum() / bull.sum()) if bull.sum() else np.nan,
               jaccard_turn_bull=float((turn & bull).sum() / (turn | bull).sum()) if (turn | bull).sum() else np.nan,
               equiv_turn_eq_above60=float((turn == (q.above60 == 1)).mean()) if len(q) else np.nan)
    for nm, mm in (('U', U & j), ('C', U & C & j)):
        z = P[mm].state.value_counts()
        tot = int(mm.sum())
        out[f'share_T_in_{nm}'] = {f'T{k}': (float(z.get(k, 0)) / tot if tot else np.nan) for k in (1, 2, 3, 4, 0)}
        out[f'n_T_in_{nm}'] = {f'T{k}': int(z.get(k, 0)) for k in (1, 2, 3, 4, 0)}
    return out


# ═════════════════ 主程式 ═════════════════
def build_all(dry):
    assert open(os.path.join(SNAP, '.commit')).read().strip() == SNAP_COMMIT, 'snapshot .commit mismatch'
    vo = verify_orig(); assert all(v[1] for v in vo.values()), vo
    fv = FairValue(SNAP)
    bars = Bars(fv)
    evals = fv.eval_dates(2018, 2026)
    J60 = judgment_dates(fv.cal, H60)
    evals = [e for e in evals if e[0] <= J60[-1]]
    FAIR = {}
    for E, kind, ey in evals:
        FAIR[E] = {}
        for s in fv.PX:
            r = fv.fair_at(s, E, kind, ey)
            if r is not None and r['pass_q'] == 1: FAIR[E][s] = r
    P60, nm60 = build_panel(fv, bars, FAIR, evals, J60, H60)
    P60 = add_excess(attach_returns(P60, bars, dry, '60'))
    E1y = [e[0] for e in evals if fv.cal_idx[e[0]] + 1 + H1Y < len(fv.cal)]
    P1y, nm1y = build_panel(fv, bars, FAIR, evals, E1y, H1Y)
    P1y = add_excess(attach_returns(P1y, bars, dry, '1y'))
    b60 = bench_returns(fv, J60, H60, dry); b1y = bench_returns(fv, E1y, H1Y, dry)
    return dict(fv=fv, bars=bars, evals=evals, FAIR=FAIR, J60=J60, P60=P60, nm60=nm60, E1y=E1y, P1y=P1y, nm1y=nm1y,
                b60=b60, b1y=b1y, verify=vo)


def per_date_freq(P, J_list, nmcap, masks):
    rows = []
    for J in J_list:
        d = P[P.J == J]; idx = d.index
        r = dict(J=J, segment=segment_of(J), cluster=cluster_of(J), E=d.E.iloc[0] if len(d) else None,
                 n_mcap300=nmcap.get(J, 0), n_pass_q=len(d), n_U=int(d.in_U.sum()),
                 n_U_E0le0=int(((d.fair_ok == 0)).sum()),
                 n_C=int((d.C == 1).sum()),
                 n_U_unjudg_short=int(((d.in_U == 1) & (d.warm_ok == 0)).sum()),
                 n_U_unjudg_lbbad=int(((d.in_U == 1) & (d.warm_ok == 1) & (d.lb_bad == 1)).sum()),
                 n_C_unjudg=int(((d.C == 1) & (d.judg == 0)).sum()))
        for nm, m in masks.items():
            r[f'n_{nm}'] = int(m[idx].sum())
        for nm in ('C∧轉強', 'C∧沒轉強', 'U全部', 'C∧T2', 'C∧非T2', 'C∧T4', '非C∧轉強'):
            r[f'nret_{nm}'] = int((masks[nm][idx] & d.R.notna()).sum())
        r['n_U_no_entry'] = int(((d.in_U == 1) & (d.entry_ok == 0)).sum())
        r['n_U_hold_bad'] = int(((d.in_U == 1) & (d.hold_bad == 1)).sum())
        r['n_U_delisted_before_exit'] = int(((d.in_U == 1) & (d.delisted_before_exit == 1)).sum())
        r['n_U_share_ev_E_J'] = int(((d.in_U == 1) & (d.n_share_ev > 0)).sum())
        r['n_C_flip_alt5'] = int(((d.in_U == 1) & (d.C != d.C_alt5)).sum())
        r['n_U_bad_E_J'] = int(((d.in_U == 1) & (d.bad_E_J == 1)).sum())
        rows.append(r)
    return pd.DataFrame(rows)


def dry_status(D):
    """把描述欄的值換成『有沒有填』——⛔ 乾跑檔不寫任何報酬值（R≡0 下的值本來就是 0）。"""
    rows = []
    for key, v in D.items():
        sec, cell, stat = key.split('|')
        for f, val in v.items():
            if f in ('n_records', 'n_dates', 'n_clusters'):
                continue
            if f == 'by_year':
                for y, yy in val.items():
                    rows.append(dict(section=sec, cell=cell, stat=f'{stat}:by_year:{y}:mean', n=yy['n'],
                                     status='filled' if (yy['n'] > 0 and np.isfinite(yy['mean'])) else 'EMPTY'))
                continue
            vals = val if isinstance(val, list) else [val]
            ok = all(isinstance(x, (int, float)) and np.isfinite(x) for x in vals)
            rows.append(dict(section=sec, cell=cell, stat=f'{stat}:{f}', n=v.get('n_records', v.get('n_dates')),
                             status='filled' if ok else 'EMPTY'))
    return pd.DataFrame(rows)


def run(dry):
    A = build_all(dry)
    P60, P1y = A['P60'], A['P1y']
    m60, m1y = arm_masks(P60), arm_masks(P1y)
    G = date_diff(P60, 'C∧轉強', 'C∧沒轉強', m60)
    na = dict(zip(G.J, G.n_a)); nb = dict(zip(G.J, G.n_b))
    trig = triggers(A['J60'], G, na, nb)
    # ★14 另一讀法：成員檔數
    fa = {J: int(m60['C∧轉強'][P60.J == J].sum()) for J in A['J60']}
    fb = {J: int(m60['C∧沒轉強'][P60.J == J].sum()) for J in A['J60']}
    trig_member = triggers(A['J60'], G, fa, fb)
    # ★1 另一讀法：判日從 2020-04 起
    J_alt = [J for J in A['J60'] if J >= '2020-04']
    trig_alt1 = triggers(J_alt, G, na, nb)
    pt, lo, hi, ncl = cluster_boot(G)
    front = G[G.J.map(segment_of) == 'front']['diff'].dropna(); back = G[G.J.map(segment_of) == 'back']['diff'].dropna()
    D = describe(P60, m60, A['b60'], '①60日')
    D.update(describe(P1y, m1y, A['b1y'], '②1年'))
    NR = nonreturn_desc(P60); NR1y = nonreturn_desc(P1y)
    F60 = per_date_freq(P60, A['J60'], A['nm60'], m60); F1y = per_date_freq(P1y, A['E1y'], A['nm1y'], m1y)
    return A, dict(G=G, trig=trig, trig_member=trig_member, trig_alt1=trig_alt1, main=(pt, lo, hi, ncl),
                   front=front, back=back, D=D, NR=NR, NR1y=NR1y, F60=F60, F1y=F1y, m60=m60)


def header(A):
    vo = A['verify']
    return {
        '登錄': '便宜＋趨勢轉強 台股 seq1（pw1 sha ef2f1c05fbcbf841；整檔 5541 B）；發號 裁定 seq482 §一',
        '合理價程式': 'backtest/twfv_recheck/orig/bt.py＋value.py（產業附件原樣）；sha256 bt.py '
                 + vo['bt.py'][0][:16] + ('（相符）' if vo['bt.py'][1] else '（不符！）') + '、value.py ' + vo['value.py'][0][:16]
                 + ('（相符）' if vo['value.py'][1] else '（不符！）'),
        '回測核對結果': '回測核對相符（commit 77aafeb9bd；twfv_recheck/結論.md：產業程式原樣＋tw-stock-data 8e5d22e，五檔逐位元相同；'
                  '主格 −20.27pp 與 seq63 一致）⇒ 本件「便宜」即此版（抄錄函式見 researchTWCheapTrend_fv.py）',
        '資料快照': SNAP_COMMIT + '（~/twdata/8e5d22e…，git archive 唯讀；最後交易日 ' + A['fv'].cal[-1] + '）',
        '沿革': '裁定 seq483 §2／seq484 §三：選 (a) 照原文跑、主格不改；准正式跑（閘門 seq482 → seq484），'
              '判語事先固定「' + FIXED_VERDICT + '」，報酬只當描述',
    }


def _js(o):
    if isinstance(o, (np.integer, np.floating, np.bool_)): return o.item()
    return str(o)


def main_dry():
    A, S = run(dry=True)
    od = os.path.join(OUT, 'freq'); os.makedirs(od, exist_ok=True)
    S['F60'].to_csv(f'{od}/freq_by_date_60d.csv', index=False, encoding='utf-8-sig')
    S['F1y'].to_csv(f'{od}/freq_by_eval_1y.csv', index=False, encoding='utf-8-sig')
    keep = ['J', 'stock_id', 'E', 'mcap_e8', 'close_J', 'fair', 'mult_J', 'C', 'C_alt5', 'n_share_ev', 'bad_E_J', 'n_bars',
            'warm_ok', 'lb_bad', 'state', 'above60', 'bull', 'entry_ok', 'exit_bar_date', 'delisted_before_exit', 'hold_bad',
            'ret_ok', 'in_U']
    A['P60'][keep].to_csv(f'{od}/panel_60d_noreturn.csv', index=False, encoding='utf-8-sig')
    A['P1y'][keep].to_csv(f'{od}/panel_1y_noreturn.csv', index=False, encoding='utf-8-sig')
    ds = dry_status(S['D']); ds.to_csv(f'{od}/desc_dryrun_status.csv', index=False, encoding='utf-8-sig')
    F = S['F60']; F1 = S['F1y']
    def mm(F, col):
        v = F[col]; vu = F[F.n_U > 0][col]
        return dict(median=float(v.median()), min=int(v.min()), max=int(v.max()),
                    median_Ugt0=float(vu.median()) if len(vu) else None, min_Ugt0=int(vu.min()) if len(vu) else None)
    summ = dict(header=header(A),
                n_judgment_dates=len(A['J60']), first_J=A['J60'][0], last_J=A['J60'][-1],
                n_dates_U0=int((F.n_U == 0).sum()), first_J_with_U=F[F.n_U > 0].J.min(),
                eval_dates=[e[0] for e in A['evals']], n_eval_1y=len(A['E1y']),
                arms_60d={c: mm(F, c) for c in ('n_U', 'n_C', 'n_C∧轉強', 'n_C∧沒轉強', 'nret_C∧轉強', 'nret_C∧沒轉強',
                                                'n_C∧T2', 'n_C∧非T2', 'n_C∧T4', 'n_非C∧轉強', 'n_U_unjudg_short', 'n_U_unjudg_lbbad')},
                arms_1y={c: mm(F1, c) for c in ('n_U', 'n_C', 'n_C∧轉強', 'n_C∧沒轉強', 'nret_C∧轉強', 'nret_C∧沒轉強',
                                                'n_C∧T2', 'n_C∧非T2', 'n_C∧T4', 'n_非C∧轉強', 'nret_U全部')},
                totals_60d={c: int(F[c].sum()) for c in F.columns if c.startswith('n')},
                totals_1y={c: int(F1[c].sum()) for c in F1.columns if c.startswith('n')},
                main_cell_dates_with_diff=int(S['G']['diff'].notna().sum()), main_cell_bootstrap_clusters=S['main'][3],
                triggers_main=S['trig'], triggers_alt14_member=S['trig_member'], triggers_alt1_from_2020_04=S['trig_alt1'],
                nonreturn_desc_60d=S['NR'], nonreturn_desc_1y=S['NR1y'],
                desc_columns=int(len(ds)), desc_columns_empty=int((ds.status != 'filled').sum()),
                desc_empty_list=[f'{r.section}|{r.cell}|{r.stat}' for r in ds[ds.status != 'filled'].itertuples()])
    json.dump(summ, open(f'{od}/freq_summary.json', 'w'), ensure_ascii=False, indent=1, default=_js)
    print(json.dumps({k: summ[k] for k in ('n_judgment_dates', 'first_J', 'last_J', 'n_dates_U0', 'first_J_with_U',
                                           'triggers_main', 'desc_columns', 'desc_columns_empty')}, ensure_ascii=False, indent=1, default=str))


def main_formal():
    A, S = run(dry=False)
    od = os.path.join(OUT, 'formal'); os.makedirs(od, exist_ok=True)
    pt, lo, hi, ncl = S['main']
    verdict = formal_verdict()                      # ⛔ 不看數字：裁定 seq483 §2-2、seq484 §三
    out = dict(header=header(A), verdict=verdict,
               verdict_basis='裁定 seq483 §2-2、seq484 §三：依構造還沒測（〈四十九〉），判語事先固定；以下報酬全部只當描述，'
                             '⛔ 不得寫成測不出或測到了',
               result_sentences=RESULT_SENTENCES, registration_errors=REG_ERRORS,
               readings='★4、★5、★10 照主讀法；另一讀法只描述',
               desc_main_cell=dict(G=pt, ci=[lo, hi], n_clusters_bootstrap=ncl,
                                   front=float(S['front'].mean()), n_front_dates=len(S['front']),
                                   back=float(S['back'].mean()), n_back_dates=len(S['back'])),
               triggers=S['trig'], triggers_alt14_member=S['trig_member'], triggers_alt1_from_2020_04=S['trig_alt1'],
               desc=S['D'], nonreturn=S['NR'], nonreturn_1y=S['NR1y'])
    S['G'].to_csv(f'{od}/main_cell_by_date.csv', index=False, encoding='utf-8-sig')
    S['F60'].to_csv(f'{od}/freq_by_date_60d.csv', index=False, encoding='utf-8-sig')
    json.dump(out, open(f'{od}/summary.json', 'w'), ensure_ascii=False, indent=1, default=_js)
    print(json.dumps(dict(verdict=verdict, desc_G=pt, desc_ci=[lo, hi]), ensure_ascii=False, default=float))


def formal_verdict(*_ignored, **__ignored):
    """正式跑判語：事先固定，與任何數字無關（裁定 seq483 §2-2、seq484 §三）。"""
    return FIXED_VERDICT


def gate(argv):
    """→ 'dry' | 'formal' | ('refuse', 訊息)。正式跑只認 --formal --ruling seq484。"""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--formal', action='store_true')
    ap.add_argument('--ruling', default=None)
    try:
        a, rest = ap.parse_known_args(argv)
    except SystemExit:
        return ('refuse', '⛔ 參數錯；拒跑')
    if rest:
        return ('refuse', '⛔ 不認得的參數 %s；拒跑' % rest)
    if a.formal and a.dry:
        return ('refuse', '⛔ --formal 與 --dry 不可同時給；拒跑')
    if a.formal:
        if a.ruling != RULING:
            return ('refuse', '⛔ 正式跑須 --formal --ruling %s（裁定 seq483／seq484 准正式跑、判語固定）；拒跑' % RULING)
        return 'formal'
    if a.dry:
        return 'dry'
    return ('refuse', '用法：--dry ｜ --formal --ruling %s；拒跑' % RULING)


if __name__ == '__main__':
    m = gate(sys.argv[1:])
    if isinstance(m, tuple):
        sys.exit(m[1])
    if m == 'formal':
        main_formal()
    else:
        main_dry()

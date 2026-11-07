# -*- coding: utf-8 -*-
"""台股合理價機械版「可買」裡剔除【長期下跌】（年線版／半年線版）——頻率表＋描述欄乾跑（⛔ 不讀、不算、不印任何報酬）。

登錄：產業 seq96「不接長期下跌濾網_年線半年線兩版回測登錄」（pw1 sha 2b9b3d9778382198＝去掉末行 pw1 戳記後全文 sha256 前 16 碼；
      整檔 6675 B；以 21:18 最後一次原地訂正為準；開跑先驗）。
發號：裁定 seq498 §一：判定 2 格（台股年線版、半年線版）⇒ N_單筆 +2；97.5% CI（Bonferroni 2 格）；判語【最多「暫定」】；
      按年分群 CI 列主表同一列（年分群下緣 ≤ 0 ⇒ 結果句必寫「按年分群看不出」）；美股同規則只描述、不計 N。
      ⇒ 先交頻率表（⛔ 不附報酬）：每月三組檔數、濾網組與剔除組各自 ≥ 1 檔的月數、K 棒不足不判的筆數。
補登錄：產業 seq101（pw1 sha 1d4094ab4250c703，1478 B，寫在任何頻率表與報酬之前；2026-11-07 22:41）：
      ① 主量只算剔除組 ≥ 3 檔的月份（全部月份版照報、只描述；必報零差值月數）⇒ 頻率表加報兩版各自：剔除組 ≥ 3 檔的月數
        （全期／前段／後段，對 24）、這些月份的年分群數、剔除組 0 檔月數（另報其中不判也為 0＝濾網−對照恆為 0 的月數）、1～2 檔月數。
      ② 中位數差（報酬欄）⛔ 乾跑不算；③ N 揭露交裁定；④ 採用範圍（只台股長期投資股、不套加碼）不影響頻率表。
      〔沿革：本檔第一次乾跑（只有 seq96 欄位）在收到 seq101 前已跑完；加欄後整份重跑，既有欄位數字不變。〕
原版：台股合理價機械版（產業 10/26 登錄；回測核對版 backtest/twfv_recheck/orig/bt.py＋value.py，結論.md；執行選擇 1～18 照舊）。
資料：tw-stock-data commit 8e5d22eb306895d15bd93643284330983c57a823（原跑那一版；~/twdata/8e5d22e… 唯讀快照，.commit 開跑先驗）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchTWLongDownFilter_freq.py

程式重用（⛔ 不改原版檔、不寫第二份合理價實作）：
  - 合理價、品質門檻、E0、g、配息率、本益比中位數、分組：researchTWCheapTrend_fv.FairValue.fair_at（bt.py 照抄版，sha 驗）。
    本件只【覆寫 available()】（財報可用性，見 ★1），合理價公式一字不動。
  - 市值 ≥ 300 億：bt.py L166–173（同 researchTWStablePE35_freq.py：評估日原始收盤 × 當日股數，缺 ⇒ fv.shares_fallback）。
  - 硬斷點（全線規則 seq335：research11 缺口 ≥ 5 日即壞根＋無事件跳價＋幽靈比）：researchTWCheapTrend.bad_bars（照用）。

══════════ 登錄寫死的（seq96 §二～§四，照抄）══════════
 長期下跌：年線版＝評估日收盤 < MA240 且 MA240 < 20 個交易日前的 MA240；半年線版＝同上改 MA120。還原收盤。
           有效 K 棒不到「均線天數＋20」根 ⇒ 該檔當天不判、留在全部可買、不進濾網組。
 濾網組＝可買且不在長期下跌；對照組＝全部可買（同評估日同名單）；剔除組＝可買且在長期下跌。
 評估日＝每月第一個交易日，2020-04～2025-10（67 個月）；財報用評估日當天已上傳的最新一期（執行選擇 4 照用）。
 持有 250 個交易日，評估日收盤進、收盤出；3 年只描述。前段 2020-04～2022-12、後段 2023-01～2025-10。
 還沒測：濾網組 ≥ 1 檔的月份 < 24，或剔除組 ≥ 1 檔的月份 < 24。

══════════ ★ 執行者定（看任何數字前寫死；另一讀法寫在〔〕，兩讀法檔數並報）══════════
 ★1 財報期別（每月評估日）：主讀法＝「評估日當天已上傳的最新一期」字面：從評估日前最後一個已結束的季起往前找
     （1–3 月⇒前一年 Q4、4–6 月⇒Q1、7–9 月⇒Q2、10–12 月⇒Q3；最多往前 5 期，同 bt.py latest_period），
     該期有非英文版上傳時戳且最早上傳日 < 評估日 ⇒ 可用；【無上傳紀錄】者照執行選擇 4「視為期限內已公告」
     ＝ 評估日 ≥ 該期法定評估日（年報⇒次年 4/1、Q1⇒5/16、Q2⇒8/15、Q3⇒11/15）才可用（不讓無時戳者在季末後立刻可用）。
     品質門檻裡「該年年報須已可用」同一規則。在原版四個評估日上兩讀法逐筆相同（法定評估日都已過）。
     〔另一讀法：期別照法定評估日對應（評估日 ≥ 11/15⇒Q3、≥ 8/15⇒Q2、≥ 5/16⇒Q1、≥ 4/1⇒前一年 Q4、其餘⇒前一年 Q3），
      未上傳退回前一期、無紀錄視為已公告（原版 available() 原樣）＝ 季內提早上傳的不提前用。〕
 ★2 母體＝原版執行選擇 2、3：kind＝stock、評估日那根 market ∈ {twse, tpex} 且有有效 K 棒；評估日原始收盤 × 當日股數 ≥ 300 億
     （股數缺 ⇒ 該期股本 ÷ 10）。可買＝fair_at 的 group_E＝「可買」（倍數 ≤ 1.00；E0 ≤ 0 照原版歸偏貴、不進可買）。
 ★3 有效 K 棒＝valid_bar＝1 且 close > 0 的根（同 bt.py）；均線、「20 個交易日前」、「均線天數＋20」都數【該檔自己的有效根】
     （同 CheapTrend ★7）；根數含評估日當根（MA 在評估日與 20 根前都要算得出＝N＋20 根）。
 ★4 不等式照字面嚴格：收盤 < 均線、均線 < 20 根前均線；相等 ⇒ 不算長期下跌。
 ★5 硬斷點（seq335）：回看窗（評估日往回 N＋20 根）內有壞根（缺口 ≥ 5 個交易日／無還原事件的 ≤0.55、≥1.8 跳價／幽靈比）
     ⇒ 均線跨斷點、當天【不判】（與 K 棒不足同處理：留在全部可買、不進濾網組也不進剔除組），筆數與 K 棒不足分開報、另報合計。
     〔另一讀法：只管持有窗、回看窗壞根照判 ⇒ 該讀法下會改判的筆數照報〕。早年 reduce_v2 只涉 2015 前，本件不適用。
 ★6 還原收盤＝原始收盤 × data/adj 累積因子（bt.py F_series）；評估日後事件對整段乘同一常數，均線比較不受影響（PIT 自測驗）。
 ★7 進場年＝評估日所在年；年分群數＝該組有 ≥ 1 檔的月份之進場年個數（2020～2025 最多 6）。
 ★8 描述欄乾跑只驗「算得出」：1 年＝評估日市場日曆位置 +250 在快照日曆內；3 年＝+750；另報持有窗（評估根, 出場根] 有壞根的筆數
     （執行選擇 14，只用壞根旗標、⛔ 不讀報酬）。
 ★9 放行對照（只報筆數）：剔除組每筆往後逐根（該檔有效根）找第一根「不再是長期下跌」（＝收盤 ≥ 均線 或 均線 ≥ 20 根前均線，
     即站回均線或均線轉平往上）＝主規則放行；「收盤 > MA60」第一根＝季線放行。途中遇壞根 ⇒ 截尾（照報）。
     報：放行／未放行（到快照尾）／截尾筆數、250 根內放行筆數、季線放行早於／同日／晚於主規則的筆數。⛔ 不報放行價比、報酬。
 ★10 加碼對照（只報筆數）：全部可買每筆，「評估日前 5 個交易日內」＝評估日當根與前 4 根（該檔有效根）；
     「出現近 60 個交易日的最低收盤」＝某根還原收盤 ≤ 含該根往回 60 根的最低還原收盤（平手算新低）。需 64 根且窗內無壞根，否則不判。
     〔另一讀法：評估日前 5 根、不含評估日〕。延後版：有新低組往後找第一根 t > 評估根、使 t−4..t 都沒有 60 日新低 ⇒ 延後進場根；
     報找得到的筆數與其 +250 在日曆內的筆數（遇壞根截尾）。⛔ 不報進場價比、報酬。
 ★11 seq377 條件等價檢查：①年線版剔除名單 ≡ 半年線版？②長期下跌 ≡ 只看「收盤 < 均線」（斜率條件多餘）？③剔除組恆空／濾網組 ≡ 全部可買？
     逐筆數出並寫結果；若成立，依 seq377 先回信不正式跑。
"""
import os, sys, json, glob, hashlib
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from researchTWCheapTrend_fv import FairValue, verify_orig, per_str, CAP_MIN  # noqa: E402
from researchTWCheapTrend import bad_bars                                    # noqa: E402

SNAP_COMMIT = '8e5d22eb306895d15bd93643284330983c57a823'
SNAP = os.path.expanduser('~/twdata/' + SNAP_COMMIT)
OUT = os.path.join(HERE, 'resultsLongDownFilter', 'freq')
REG_DIR = os.environ.get('LDF_REG_DIR', '/mnt/c/SynologyDrive/跨線信箱')
REG_GLOB = '*不接長期下跌濾網_年線半年線兩版回測登錄seq96.md'
REG_SHA16, REG_BYTES = '2b9b3d9778382198', 6675
REG = '產業 seq96 pw1 2b9b3d9778382198'
RULING = '裁定 seq498 §一'
VERS = (('年線', 240), ('半年線', 120))
SLOPE = 20
MA_REL = 60
NL_WIN, NL_LOOK = 60, 5
H1, H3 = 250, 750
M_START, M_END, FRONT_END = '2020-04', '2025-10', '2022-12'
MIN_MONTHS = 24
MIN_EXCL_MAIN = 3          # 產業 seq101 ①：主量只算剔除組 ≥ 3 檔的月份
SHORT, BRK = -1, -2
# 法定評估日（執行選擇 4 的期別對應）：季 → (月日, 年偏移)
STAT_MD = {4: ('04-01', 1), 1: ('05-16', 0), 2: ('08-15', 0), 3: ('11-15', 0)}


# ═════════════ 登錄驗證 ═════════════
def verify_registration():
    fs = glob.glob(os.path.join(REG_DIR, REG_GLOB))
    assert len(fs) == 1, fs
    b = open(fs[0], 'rb').read()
    lines = b.decode('utf-8').splitlines(keepends=True)
    pw1 = hashlib.sha256(''.join(lines[:-1]).encode('utf-8')).hexdigest()
    assert len(b) == REG_BYTES and pw1.startswith(REG_SHA16), (len(b), pw1)
    return dict(bytes=len(b), pw1=pw1[:16])


# ═════════════ ★1 財報期別 ═════════════
class FairValueMonthly(FairValue):
    """只覆寫 available()（★1 主讀法）；mode='orig' ⇒ 原版 available() 原樣（另一讀法）。合理價公式不動。"""
    mode = 'upload'

    def available(self, s, y, q, E):
        if self.mode == 'orig':
            return super().available(s, y, q, E)
        if (s, per_str(y, q)) not in self.FS:
            return False
        u = self.UP.get((s, str(y), str(q)))
        if u is None:
            md, off = STAT_MD[q]
            return E >= f'{y + off}-{md}'
        return u[:10] < E


def kind_upload(E):
    """★1 主讀法：評估日前最後一個已結束的季 ⇒ (kind, ey)（latest_period 的起點）。"""
    y, m = int(E[:4]), int(E[5:7])
    return ('Q4', y) if m <= 3 else ('Q1', y) if m <= 6 else ('Q2', y) if m <= 9 else ('Q3', y)


def kind_statutory(E):
    """★1 另一讀法：法定評估日對應。"""
    y = int(E[:4])
    if E >= f'{y}-11-15': return 'Q3', y
    if E >= f'{y}-08-15': return 'Q2', y
    if E >= f'{y}-05-16': return 'Q1', y
    if E >= f'{y}-04-01': return 'Q4', y
    return 'Q3', y - 1


def month_dates(cal):
    out, seen = [], set()
    for d in cal:
        ym = d[:7]
        if M_START <= ym <= M_END and ym not in seen:
            seen.add(ym); out.append(d)
    return out


# ═════════════ 趨勢（純函式；check 腳本直接測）═════════════
def ma_arr(px, L):
    px = np.asarray(px, float); out = np.full(len(px), np.nan)
    if len(px) >= L:
        out[L - 1:] = np.lib.stride_tricks.sliding_window_view(px, L).mean(axis=1)
    return out


def lag(a, k):
    out = np.full(len(a), np.nan)
    if len(a) > k: out[k:] = a[:-k]
    return out


def cumbad(bad):
    return np.concatenate([[0], np.cumsum(np.asarray(bad, int))])


def bad_in(cb, k0, k1):
    """壞根落在 (k0, k1]。"""
    return (cb[k1 + 1] - cb[k0 + 1]) > 0


def longdown_code(px, ma, cb, k, N):
    """→ 1 長期下跌｜0 不是｜SHORT 有效根 < N+20｜BRK 回看窗有壞根（★3～★5）。只用 px[0..k]。"""
    W = N + SLOPE
    if k + 1 < W: return SHORT
    if bad_in(cb, k - W + 1, k): return BRK
    with np.errstate(invalid='ignore'):
        return int(bool(px[k] < ma[k] and ma[k] < ma[k - SLOPE]))


def longdown_code_nobrk(px, ma, k, N):
    """★5 另一讀法：回看窗壞根照判。"""
    if k + 1 < N + SLOPE: return SHORT
    return int(bool(px[k] < ma[k] and ma[k] < ma[k - SLOPE]))


def below_only(px, ma, k):
    return int(bool(px[k] < ma[k]))


def newlow_flags(px):
    """★10：nl[t]＝px[t] ≤ 含 t 往回 60 根最低（平手算）；前 59 根 NaN→False。"""
    px = np.asarray(px, float); n = len(px); nl = np.zeros(n, bool)
    if n >= NL_WIN:
        mn = np.lib.stride_tricks.sliding_window_view(px, NL_WIN).min(axis=1)
        nl[NL_WIN - 1:] = px[NL_WIN - 1:] <= mn
    return nl


def newlow_code(nl, cb, k, include_E=True):
    """→ 1 有新低｜0 沒有｜SHORT｜BRK。主讀法 k−4..k；另一讀法 k−5..k−1。"""
    hi = k if include_E else k - 1
    lo = hi - NL_LOOK + 1
    need_first = lo - NL_WIN + 1          # 最早一根新低判斷需要的第一根
    if need_first < 0: return SHORT
    if bad_in(cb, need_first, k): return BRK
    return int(bool(nl[lo:hi + 1].any()))


# ═════════════ 每檔資料 ═════════════
class Stock:
    def __init__(self, fv, s):
        p = fv.PX[s]
        dates = p.index.values.astype(str)
        pos = np.array([fv.cal_idx.get(d, -1) for d in dates]); keep = pos >= 0
        if not keep.all(): p = p[keep]; dates = dates[keep]; pos = pos[keep]
        self.dates, self.pos = dates, pos
        self.at = {d: i for i, d in enumerate(dates)}
        self.close, self.shares, self.market = p.close.values, p.shares.values, p.market.values
        self.px = p.adj.values.astype(float)
        self.bad = bad_bars(dates, pos, p.close.values, fv.ADJ[s])
        self.cb = cumbad(self.bad)
        self._ma = {}
        self._nl = None

    def ma(self, N):
        if N not in self._ma: self._ma[N] = ma_arr(self.px, N)
        return self._ma[N]

    @property
    def nl(self):
        if self._nl is None: self._nl = newlow_flags(self.px)
        return self._nl


def first_true_after(mask, k):
    idx = np.flatnonzero(mask[k + 1:])
    return int(idx[0]) + k + 1 if len(idx) else None


def release_info(st, k, N):
    """★9：→ dict（只有根索引距離與旗標；⛔ 無價格）。"""
    px, ma = st.px, st.ma(N); ma60 = st.ma(MA_REL)
    with np.errstate(invalid='ignore'):
        ld = (px < ma) & (ma < lag(ma, SLOPE))
        rel = ~ld & np.isfinite(ma)
        rel60 = (px > ma60) & np.isfinite(ma60)
    kb = first_true_after(st.bad, k)                       # 第一個壞根（截尾）
    kr = first_true_after(rel, k); kr60 = first_true_after(rel60, k)
    def status(kk):
        if kb is not None and (kk is None or kk >= kb): return 'censored', None
        if kk is None: return 'never', None
        return 'released', kk - k
    s1, d1 = status(kr); s2, d2 = status(kr60)
    return dict(rel_main=s1, rel_main_bars=d1, rel_ma60=s2, rel_ma60_bars=d2)


def delayed_entry(st, k):
    """★10 延後版：第一根 t > k 使 t−4..t 都沒有新低（遇壞根截尾）→ 根索引或 None、狀態。"""
    nl = st.nl; n = len(nl)
    kb = first_true_after(st.bad, k)
    for t in range(k + 1, n):
        if kb is not None and t >= kb: return None, 'censored'
        if not nl[max(t - NL_LOOK + 1, 0):t + 1].any(): return t, 'found'
    return None, 'never'


# ═════════════ 主程式 ═════════════
def preflight():
    """快照 .commit、登錄 sha、原版 sha 三項先驗 → (vreg, vo)。"""
    assert open(os.path.join(SNAP, '.commit')).read().strip() == SNAP_COMMIT, 'snapshot .commit mismatch'
    vreg = verify_registration()
    vo = verify_orig(); assert all(v[1] for v in vo.values()), vo
    return vreg, vo


def build(fv):
    """主迴圈（頻率表與正式跑共用同一份；正式跑 researchTWLongDownFilter.py 直接呼叫）→ R, months, n_univ, STK。
    〔2026-11-08 正式跑前把 main() 的迴圈原樣抽成本函式，邏輯一字未改；重跑頻率表輸出逐位元相同。〕"""
    cal, ci = fv.cal, fv.cal_idx
    months = month_dates(cal)
    assert len(months) == 67, len(months)
    STK = {}

    def stock(s):
        if s not in STK: STK[s] = Stock(fv, s)
        return STK[s]

    recs = []
    n_univ = {}
    for E in months:
        nu = 0
        km, eym = kind_upload(E); ka, eya = kind_statutory(E)
        for s, p in fv.PX.items():
            if E not in p.index: continue
            row = p.loc[E]
            if row.market not in ('twse', 'tpex'): continue
            sh = row.shares
            fv.mode = 'upload'
            rm = None
            if pd.isna(sh) or sh <= 0:
                rm = fv.fair_at(s, E, km, eym)
                sh = fv.shares_fallback(s, rm['lp']) if rm else np.nan
            cap = row.close * sh if pd.notna(sh) else np.nan
            if not (cap >= CAP_MIN): continue
            nu += 1
            if rm is None: rm = fv.fair_at(s, E, km, eym)
            fv.mode = 'orig'
            ra = fv.fair_at(s, E, ka, eya)
            fv.mode = 'upload'
            gm = rm['group_E'] if rm else ''; ga = ra['group_E'] if ra else ''
            if gm != '可買' and ga != '可買':
                recs.append(dict(E=E, stock_id=s, buy=0, buy_alt=0, pass_q=rm['pass_q'] if rm else 0,
                                 period=rm['period'] if rm else None, period_alt=ra['period'] if ra else None))
                continue
            st = stock(s); k = st.at[E]
            r = dict(E=E, stock_id=s, buy=int(gm == '可買'), buy_alt=int(ga == '可買'), pass_q=rm['pass_q'] if rm else 0,
                     period=rm['period'] if rm else None, period_alt=ra['period'] if ra else None, n_bars=k + 1)
            for vn, N in VERS:
                ma = st.ma(N)
                c = longdown_code(st.px, ma, st.cb, k, N)
                r[f'ld_{vn}'] = c
                r[f'ld_{vn}_nobrk'] = longdown_code_nobrk(st.px, ma, k, N)
                r[f'below_{vn}'] = below_only(st.px, ma, k) if c in (0, 1) else np.nan
                if c == 1:
                    for kk, vv in release_info(st, k, N).items(): r[f'{kk}_{vn}'] = vv
            r['nl'] = newlow_code(st.nl, st.cb, k, True)
            r['nl_alt'] = newlow_code(st.nl, st.cb, k, False)
            if r['nl'] == 1:
                t, why = delayed_entry(st, k)
                r['delay_status'] = why
                r['delay_bars'] = (t - k) if t is not None else np.nan
                r['delay_1y_cal'] = int(t is not None and st.pos[t] + H1 < len(cal))
            # ★8 算得出（只看日期／壞根旗標）
            iE = ci[E]
            for tag, H in (('1y', H1), ('3y', H3)):
                ok_date = iE + H < len(cal)
                r[f'cal_{tag}'] = int(ok_date)
                if ok_date:
                    ex = cal[iE + H]
                    kx = int(np.searchsorted(st.dates, ex, side='right')) - 1
                    r[f'holdbad_{tag}'] = int(kx > k and bad_in(st.cb, k, kx))
                    r[f'delisted_{tag}'] = int(st.dates[-1] < ex)
                else:
                    r[f'holdbad_{tag}'] = np.nan; r[f'delisted_{tag}'] = np.nan
            recs.append(r)
        n_univ[E] = nu
        print(E, nu, sum(1 for x in recs if x['E'] == E and x['buy'] == 1), flush=True)
    R = pd.DataFrame(recs)
    return R, months, n_univ, STK


def main():
    vreg, vo = preflight()
    fv = FairValueMonthly(SNAP)
    cal, ci = fv.cal, fv.cal_idx
    R, months, n_univ, STK = build(fv)
    os.makedirs(OUT, exist_ok=True)

    # ── 每月 × 兩版 ──
    rows = []
    for E in months:
        d = R[R.E == E]
        for vn, N in VERS:
            for rd, bcol in (('主', 'buy'), ('另', 'buy_alt')):
                b = d[d[bcol] == 1]
                c = b[f'ld_{vn}'] if len(b) else pd.Series(dtype=float)
                rows.append(dict(month=E[:7], eval=E, year=int(E[:4]), segment='前段' if E[:7] <= FRONT_END else '後段',
                                 版本=vn, 財報讀法=rd, 母體=n_univ[E],
                                 全部可買=len(b), 濾網組=int((c == 0).sum()), 剔除組=int((c == 1).sum()),
                                 K棒不足不判=int((c == SHORT).sum()), 回看壞根不判=int((c == BRK).sum()),
                                 不判合計=int(c.isin([SHORT, BRK]).sum()),
                                 一年出場在日曆內=int(ci[E] + H1 < len(cal)),
                                 三年出場在日曆內=int(ci[E] + H3 < len(cal)),
                                 可買_持有窗壞根_1年=int((b.holdbad_1y == 1).sum()) if len(b) else 0,
                                 加碼_有新低=int((b.nl == 1).sum()) if len(b) else 0,
                                 加碼_沒新低=int((b.nl == 0).sum()) if len(b) else 0,
                                 加碼_不判=int(b.nl.isin([SHORT, BRK]).sum()) if len(b) else 0))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, 'tw_freq_by_month.csv'), index=False, encoding='utf-8-sig')
    cols = [c for c in R.columns]
    R[(R.buy == 1) | (R.buy_alt == 1)][cols].to_csv(os.path.join(OUT, 'tw_buy_rows_noreturn.csv'), index=False,
                                                    encoding='utf-8-sig')

    S = summarize(R, T, months, cal, ci, n_univ)
    S.update({'登錄': REG, '登錄驗證': vreg, '發號': RULING, '資料commit': SNAP_COMMIT,
              'sha_orig': {k: v[0] for k, v in vo.items()}})
    with open(os.path.join(OUT, 'tw_freq_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x))
    pd.set_option('display.width', 250)
    print(T[T['財報讀法'] == '主'].pivot_table(index='month', columns='版本',
                                            values=['全部可買', '濾網組', '剔除組', '不判合計']).to_string())
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str))


def mstat(x):
    x = pd.Series(x)
    return [float(x.median()), int(x.min()), int(x.max())]


def seq101_block(t):
    """產業 seq101 ①：主量只算剔除組 ≥ 3 檔的月份。t＝單一版本的每月表（需 剔除組、濾網組、不判合計、segment、year）。"""
    g = t['剔除組']; m3 = g >= MIN_EXCL_MAIN
    return {
        '剔除組≥3檔月數': int(m3.sum()),
        '剔除組≥3檔月數_前段': int((m3 & (t.segment == '前段')).sum()),
        '剔除組≥3檔月數_後段': int((m3 & (t.segment == '後段')).sum()),
        '剔除組≥3檔月份_年分群數': int(t[m3].year.nunique()),
        '剔除組≥3檔月份_進場年': sorted(int(y) for y in t[m3].year.unique()),
        '剔除組≥3檔且濾網組≥1檔月數': int((m3 & (t['濾網組'] >= 1)).sum()),
        '剔除組0檔月數': int((g == 0).sum()),
        '其中不判也為0（濾網組−對照組恆為0）': int(((g == 0) & (t['不判合計'] == 0)).sum()),
        '剔除組1～2檔月數': int(g.between(1, 2).sum()),
        '剔除組≥3檔月數<24（主量門檻）': bool(m3.sum() < MIN_MONTHS),
        '剔除組≥3檔月數_前段<24': bool((m3 & (t.segment == '前段')).sum() < MIN_MONTHS),
        '剔除組≥3檔月數_後段<24': bool((m3 & (t.segment == '後段')).sum() < MIN_MONTHS),
    }


def summarize(R, T, months, cal, ci, n_univ):
    S = {'月數': len(months), '評估日': [months[0], months[-1]],
         '前段月數': sum(1 for m in months if m[:7] <= FRONT_END), '後段月數': sum(1 for m in months if m[:7] > FRONT_END),
         '母體（市值≥300億）每月_中位_最少_最大': mstat(list(n_univ.values()))}
    for rd in ('主', '另'):
        bcol = 'buy' if rd == '主' else 'buy_alt'
        out = {}
        for vn, N in VERS:
            t = T[(T['版本'] == vn) & (T['財報讀法'] == rd)]
            o = {}
            for g in ('全部可買', '濾網組', '剔除組', '不判合計'):
                o[f'{g}_每月_中位_最少_最大'] = mstat(t[g])
            for g in ('濾網組', '剔除組'):
                o[f'{g}_≥1檔月數'] = int((t[g] >= 1).sum())
                o[f'{g}_≥1檔月數_前段'] = int(((t[g] >= 1) & (t.segment == '前段')).sum())
                o[f'{g}_≥1檔月數_後段'] = int(((t[g] >= 1) & (t.segment == '後段')).sum())
                o[f'{g}_年分群數'] = int(t[t[g] >= 1].year.nunique())
                o[f'{g}_總筆數'] = int(t[g].sum())
            o['全部可買_≥1檔月數'] = int((t['全部可買'] >= 1).sum())
            o['K棒不足不判_總筆數'] = int(t['K棒不足不判'].sum())
            o['回看壞根不判_總筆數'] = int(t['回看壞根不判'].sum())
            o['不判合計_總筆數'] = int(t['不判合計'].sum())
            b = R[R[bcol] == 1]
            o['★5另一讀法_回看壞根照判會改判筆數'] = int(((b[f'ld_{vn}'] == BRK) & (b[f'ld_{vn}_nobrk'] >= 0)).sum())
            o['★5另一讀法_回看壞根照判且判長期下跌'] = int(((b[f'ld_{vn}'] == BRK) & (b[f'ld_{vn}_nobrk'] == 1)).sum())
            o['還沒測觸發'] = bool(o['濾網組_≥1檔月數'] < MIN_MONTHS or o['剔除組_≥1檔月數'] < MIN_MONTHS)
            o['seq101①_剔除組≥3檔月份（主量）'] = seq101_block(t)
            out[vn] = o
        S[f'財報{rd}讀法'] = out
    # ★1 兩讀法差
    S['★1兩讀法_可買(評估日,檔)不同筆數'] = int((R.buy != R.buy_alt).sum())
    S['★1兩讀法_可買總筆數'] = {'主': int(R.buy.sum()), '另': int(R.buy_alt.sum())}
    S['★1兩讀法_母體內期別不同筆數'] = int((R.period.fillna('') != R.period_alt.fillna('')).sum())

    B = R[R.buy == 1].copy()
    # ── seq377 等價檢查（主讀法）──
    eq = {}
    jy, jh = B['ld_年線'], B['ld_半年線']
    both = B[(jy >= 0) & (jh >= 0)]
    eq['兩版都可判筆數'] = len(both)
    eq['交叉表_年線x半年線'] = {f'年{a}_半{b}': int(((both.ld_年線 == a) & (both.ld_半年線 == b)).sum())
                          for a in (0, 1) for b in (0, 1)}
    sy = set(zip(B.E[jy == 1], B.stock_id[jy == 1])); sh = set(zip(B.E[jh == 1], B.stock_id[jh == 1]))
    eq['剔除名單_年線筆數'] = len(sy); eq['剔除名單_半年線筆數'] = len(sh)
    eq['剔除名單_交集'] = len(sy & sh); eq['剔除名單_Jaccard'] = (len(sy & sh) / len(sy | sh)) if (sy | sh) else None
    same_m = 0
    for E, d in B.groupby('E'):
        a = set(d.stock_id[d.ld_年線 == 1]); b = set(d.stock_id[d.ld_半年線 == 1])
        same_m += int(a == b)
    eq['兩版剔除名單完全相同的月數'] = same_m
    eq['年線版剔除名單≡半年線版'] = bool(sy == sh)
    for vn, N in VERS:
        j = B[B[f'ld_{vn}'] >= 0]
        nb = int((j[f'below_{vn}'] == 1).sum()); nld = int((j[f'ld_{vn}'] == 1).sum())
        eq[f'{vn}_可判筆數'] = len(j)
        eq[f'{vn}_收盤<均線筆數'] = nb
        eq[f'{vn}_長期下跌筆數'] = nld
        eq[f'{vn}_收盤<均線但均線未下彎（斜率條件擋下）筆數'] = nb - nld
        eq[f'{vn}_長期下跌≡收盤<均線'] = bool(nb == nld)
        t = T[(T['版本'] == vn) & (T['財報讀法'] == '主')]
        eq[f'{vn}_剔除組為0的月數'] = int((t['剔除組'] == 0).sum())
        eq[f'{vn}_濾網組≡全部可買的月數'] = int((t['濾網組'] == t['全部可買']).sum())
        eq[f'{vn}_濾網組≡全部可買減不判的月數'] = int((t['濾網組'] == t['全部可買'] - t['不判合計']).sum())
    S['seq377等價檢查'] = eq

    # ── 描述欄乾跑（⛔ 只有筆數）──
    D = {}
    m1 = [m for m in months if ci[m] + H1 < len(cal)]
    D['1年出場在日曆內的月數'] = len(m1)
    D['2025-10進場+250在快照日曆內'] = bool(ci[months[-1]] + H1 < len(cal))
    D['2025-10進場+250日期'] = cal[ci[months[-1]] + H1] if ci[months[-1]] + H1 < len(cal) else None
    D['快照日曆最後一日'] = cal[-1]
    D['3年出場在日曆內的月數'] = sum(1 for m in months if ci[m] + H3 < len(cal))
    D['3年_最後可算月'] = max([m for m in months if ci[m] + H3 < len(cal)], default=None)
    D['全部可買_1年可算筆數（日曆內）'] = int((B.cal_1y == 1).sum())
    D['全部可買_1年持有窗壞根筆數'] = int((B.holdbad_1y == 1).sum())
    D['全部可買_1年出場前已下市筆數（用最後一筆，執行選擇13）'] = int((B.delisted_1y == 1).sum())
    D['全部可買_3年可算筆數（日曆內）'] = int((B.cal_3y == 1).sum())
    D['全部可買_3年持有窗壞根筆數'] = int((B.holdbad_3y == 1).sum())
    for vn, N in VERS:
        for g, c in (('濾網組', 0), ('剔除組', 1)):
            x = B[B[f'ld_{vn}'] == c]
            D[f'{vn}_{g}_1年可算筆數'] = int(((x.cal_1y == 1) & (x.holdbad_1y != 1)).sum())
            D[f'{vn}_{g}_3年可算筆數'] = int(((x.cal_3y == 1) & (x.holdbad_3y != 1)).sum())
        x = B[B[f'ld_{vn}'] == 1]
        rm, r6 = x[f'rel_main_{vn}'], x[f'rel_ma60_{vn}']
        dm, d6 = x[f'rel_main_bars_{vn}'], x[f'rel_ma60_bars_{vn}']
        both = (rm == 'released') & (r6 == 'released')
        D[f'{vn}_放行對照'] = {
            '被擋筆數': len(x),
            '主規則_放行': int((rm == 'released').sum()), '主規則_到快照尾未放行': int((rm == 'never').sum()),
            '主規則_壞根截尾': int((rm == 'censored').sum()), '主規則_250根內放行': int(((rm == 'released') & (dm <= H1)).sum()),
            '季線_放行': int((r6 == 'released').sum()), '季線_到快照尾未放行': int((r6 == 'never').sum()),
            '季線_壞根截尾': int((r6 == 'censored').sum()), '季線_250根內放行': int(((r6 == 'released') & (d6 <= H1)).sum()),
            '兩者都放行': int(both.sum()), '季線早於主規則': int((both & (d6 < dm)).sum()),
            '同一根': int((both & (d6 == dm)).sum()), '季線晚於主規則': int((both & (d6 > dm)).sum()),
            '說明': '只報筆數；放行價比、放行時是否仍可買、報酬留正式跑（⛔ 乾跑不算）'}
    D['加碼對照'] = {
        '主讀法（含評估日 5 根）': {'有新低': int((B.nl == 1).sum()), '沒新低': int((B.nl == 0).sum()),
                            'K棒不足不判': int((B.nl == SHORT).sum()), '壞根不判': int((B.nl == BRK).sum()),
                            '有新低≥1檔月數': int(B[B.nl == 1].E.nunique()), '沒新低≥1檔月數': int(B[B.nl == 0].E.nunique())},
        '另一讀法（評估日前 5 根）': {'有新低': int((B.nl_alt == 1).sum()), '沒新低': int((B.nl_alt == 0).sum()),
                              '不判': int(B.nl_alt.isin([SHORT, BRK]).sum())},
        '延後版': {'有新低筆數': int((B.nl == 1).sum()),
                '找到延後進場根': int((B.get('delay_status') == 'found').sum()) if 'delay_status' in B else 0,
                '到快照尾未出現': int((B.get('delay_status') == 'never').sum()) if 'delay_status' in B else 0,
                '壞根截尾': int((B.get('delay_status') == 'censored').sum()) if 'delay_status' in B else 0,
                '延後進場+250在日曆內': int((B.get('delay_1y_cal') == 1).sum()) if 'delay_1y_cal' in B else 0},
        '說明': '只報筆數；進場價比、報酬留正式跑'}
    S['描述欄乾跑（⛔ 只報筆數／算不算得出，不含報酬）'] = D
    return S


if __name__ == '__main__':
    main()

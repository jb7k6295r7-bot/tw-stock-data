"""PREREGP4 v2 的特徵層——同一件事只有一份實作：researchp4（主格）與 forward_p4（前瞻檔）都 import 這裡。
判準 backtest/P4_v3_回溯分析.md（v3，策略線 09-15 08:18；中心 backtest/forward/p4_types/centers_v3.json，策略線 09-15 12:52 投遞、sha256 前 16＝23be85b004977222）。assign() 只收參數、不內建。

13 條特徵（順序固定）：
  同日橫截面百分位（0～100）：ret_120 ret_20 dist_hi120 dist_lo120 vol60 vr_20_120 amt20 turn20 fore20 trust20
  布林 ×100：ma_stack ma60_up rev_hi24
機器定義（v2 §4-3）：
  ret_120   close_t / close_{t-120} − 1（還原、ffill）      ret_20 同
  dist_hi120 close_t / max(close, 120 日, min_periods=60) − 1   dist_lo120 對 min
  vol60     日報酬 60 日標準差（min_periods=30）× sqrt(245)
  vr_20_120 amount 20 日均 / amount 120 日均           amt20 amount 20 日均（元）
  turn20    volume 20 日均 / 1000 / (shares_t / 1000)
  fore20    foreign 20 日累計 / (shares_t / 1000)       trust20 trust 同（⚠ 欄位＝data/stocks_inst 的日淨買超股數，待策略線確認）
  shares_t  data/stocks/<code>.csv 當日 shares，依交易日曆 reindex 後【只 ffill、⛔ 不 bfill】；NaN 或 ≤ 0 ⇒ 該三欄 NaN（補 50、計入放棄組）
  ma_stack  close > MA20 > MA60 > MA120                ma60_up MA60_t > MA60_{t−20}
  rev_hi24  另算一欄 rev_hi24_p4：當期月營收 ≥ 近 24 期最高 × 0.9999；近 24 期有效期數 < 18 ⇒ NaN（⛔ 不是 False）；
            可得性＝期別次月 10 日後第一個交易日（research34.rebalance_dates）；⛔ 不動研究三／十三的 rev_hi24
⭐ 母體閘門（v3 補件 §3-1）：量測日 bars ≥ MIN_BARS(120) 才合格，不足者整檔排除當月（放棄組⑧）、⛔ 不是補 50；所有回看窗 min_periods＝w（§3-2）。
缺值一律補 50；標準化 (x − mu) / sd；歸型取歐氏距離最近的中心。
量測日＝每月第一個交易日；進場＝次一交易日開盤還原價；出場＝H 個交易日後收盤（H = 20 / 60 / 120）。
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import data as D
from . import research34 as R34

HERE = os.path.dirname(os.path.abspath(__file__))
PCT_FEATURES = ["ret_120", "ret_20", "dist_hi120", "dist_lo120", "vol60", "vr_20_120", "amt20", "turn20", "fore20", "trust20"]
BOOL_FEATURES = ["ma_stack", "ma60_up", "rev_hi24"]
FEATURES = PCT_FEATURES + BOOL_FEATURES
FILL = 50.0
LIQ_MIN = 50_000_000     # 近 20 日均額 ≥ 5,000 萬（v2 §三）
HOLDS = (20, 60, 120)
REV_WIN, REV_MIN_VALID, REV_TOL = 24, 18, 0.9999
TDR_INDUSTRY_CODE = "91"            # 存託憑證（官方證券種類欄＝data/meta/industry.csv 的 industry_code，資料庫線 1930）
MIN_BARS = 120          # v3 補件 §3-1（策略線 09-15 18:27、K線分析 1855 合併）：量測日有價收盤根數 ≥ 120 才進母體；⛔ 120 從當期特徵集最長回看窗推出（ret_120／dist_hi120／dist_lo120／MA120），新增回看窗 > 120 的特徵時本常數要一起改
LOOKBACKS = {"ma20": 20, "ma60": 60, "ma120": 120, "ret_120": 120, "ret_20": 20, "hi_lo_120": 120, "vol60": 60, "amt20": 20, "amt120": 120, "vol20": 20, "inst20": 20}


def measurement_days(cal: pd.DatetimeIndex, start: str | None = None, end: str | None = None) -> np.ndarray:
    """每月第一個交易日的日曆位置。"""
    per = cal.to_period("M")
    first = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    if start:
        first = first[cal[first] >= pd.Timestamp(start)]
    if end:
        first = first[cal[first] <= pd.Timestamp(end)]
    return first


def load_shares(sid: str, cal: pd.DatetimeIndex) -> pd.Series:
    """當日 shares，reindex 到日曆後只 ffill；NaN／≤0 ⇒ NaN。"""
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return pd.Series(np.nan, index=cal)
    s = pd.read_csv(p, usecols=["date", "shares"], parse_dates=["date"]).drop_duplicates("date").set_index("date")["shares"]
    s = pd.to_numeric(s, errors="coerce").reindex(cal).ffill()
    return s.where(s > 0)


def load_inst(sid: str, cal: pd.DatetimeIndex) -> pd.DataFrame:
    """三大法人日淨買超股數（foreign／trust），reindex 到日曆；沒有檔 ⇒ 全 NaN。"""
    p = os.path.join(D.DATA, "stocks_inst", f"{sid}.csv")
    if not os.path.exists(p):
        return pd.DataFrame({"foreign": np.nan, "trust": np.nan}, index=cal)
    df = pd.read_csv(p, usecols=["date", "foreign", "trust"], parse_dates=["date"]).drop_duplicates("date").set_index("date")
    return df.apply(pd.to_numeric, errors="coerce").reindex(cal)


def load_tdr_codes(path: str | None = None) -> set[str]:
    """存託憑證（TDR）名單＝`data/meta/industry.csv` 的 `industry_code == 91`（資料庫線 1930：那就是官方的證券種類欄）。
    ⛔ 讀不到判準檔就**大聲失敗**，⛔ 不是靜靜回空集合（CLAUDE.md 四點六：讀不到的表現是空值、不是錯誤，所以要自己擋）。
    ⚠ 判準是「那一族**有沒有內容**」，⛔ 不是 `os.path.exists`——一個空殼檔會讓後者靜靜放行。"""
    p = path or os.path.join(D.DATA, "meta", "industry.csv")
    if not os.path.exists(p):
        raise SystemExit(f"⛔ 讀不到 {p}（分支上的 data/ 比 main 舊？先 git checkout origin/main -- data/meta/industry.csv）")
    df = pd.read_csv(p, dtype=str)
    ids = set(df.loc[df["industry_code"].astype(str).str.strip() == TDR_INDUSTRY_CODE, "stock_id"].astype(str))
    if not ids:
        raise SystemExit(f"⛔ {p} 裡 industry_code == {TDR_INDUSTRY_CODE}（存託憑證）一檔都沒有 ⇒ 判準檔是空殼或欄位換了，⛔ 不可以當成「沒有 TDR」往下跑")
    return ids


def rev_hi24_flags(rev: pd.DataFrame, cal: pd.DatetimeIndex, pub_day: int = 10, incl_current: bool = False,
                   undecided: set[str] | None = None) -> pd.DataFrame:
    """rev：period × stock_id 的月營收（research34.load_revenue）。回傳 cal × stock_id 的 0／100／NaN，
    每期在可得日（次月 pub_day 日後第一個交易日）生效、延續到下一期可得日前。
    incl_current：⛔ 正式值 False（「近 24 期」＝當期之前的 24 期，不含當期）；True 只給對帳敏感度用（視窗＝含當期的 24 期＝前 23 期＋當期，策略線 v5 的讀法，2026-09-15 23:5x 對帳查到）。

    ⭐⭐ 缺值分三種（K線分析線 0150 §1-2／〈八十五〉，登錄在 P4_v3 追加十八）——判準是【缺失是不是未來事件的函數】：

        ① 該檔自己的營收序列首期到 k **不足 24 期** ⇒ **0.0（False）＝依定義不成立**
           （⛔ 不是「缺值後補 False」：規則自己造出來的空缺要由規則自己講清楚，〈七十七〉第三種空缺）
           ⇒ 前瞻可辨識（上市日、期別數，量測當下就知道）
        ② 當期營收是 NaN（該期沒申報）⇒ **NaN 留著**
           ⇒ ⛔ 「這家公司後來會不會下市」是量測日不可能知道的事 ⇒ 排除它＝把倖存者偏誤做實
           ⚠ 而**實際長相**要看清楚：最後那一行 `ffill` 會把上一期的旗標往後帶
             ⇒ 序列中途才停止申報的，日面板上看到的是**上一期的值**，⛔ 不是 NaN；
             ⇒ ⭐ 日面板上真正是 NaN 的，是**在來源裡整檔不存在**（`first_k is None`）那一種
               ——而那正是倖存者的形狀（資料庫線 2350：來源端就沒有已下市公司的營收史）。
        ③ 有 ≥24 期歷史而近 24 期有效 < 18（來源覆蓋不完整）⇒ **NaN 留著、標不明**

    undecided：⛔ **不寫 False 也不補值**的那一族（本案＝存託憑證，`load_tdr_codes()`）。
    ⚠ 它**優先**於①——9103 看起來像「期數不足」，⛔ 而它其實是來源覆蓋不完整而原因不明（資料庫線 0410），裁定明文要單獨標。"""
    undecided = undecided or set()
    periods = list(rev.index)
    rd = R34.rebalance_dates(periods, cal, pub_day)
    flags = {}
    vals = rev.to_numpy(float)
    for j, sid in enumerate(rev.columns):
        col = np.full(len(periods), np.nan)
        rep = np.flatnonzero(~np.isnan(vals[:, j]))          # 該檔有申報的期別位置
        first_k = int(rep[0]) if len(rep) else None          # 首期；⛔ 沒有任何一期就不存在
        tdr = str(sid) in undecided
        for k in range(len(periods)):
            if np.isnan(vals[k, j]):
                continue                                      # ② 當期沒申報 ⇒ NaN 留著（前視：後來下不下市不是量測日知道的事）
            # ⚠ first_k == 0 ⇒ 分不出「新上市」與「營收面板從這裡才開始」⇒ ⛔ 不可以寫成 False，留 NaN（資料起點限制）
            short = first_k is not None and first_k > 0 and (k - first_k) < REV_WIN
            if short:
                # ① 自己的序列不足 24 期 ⇒ 依定義不成立（⛔ 不是缺值）；⚠ 而 undecided（TDR）那一族優先，⛔ 不寫 False
                if not tdr:
                    col[k] = 0.0
                continue
            hist = vals[k - REV_WIN + 1:k, j] if incl_current else vals[k - REV_WIN:k, j]   # incl_current：前 23 期（當期自己不進 max，否則永遠 True）
            valid = hist[~np.isnan(hist)]
            if len(valid) < REV_MIN_VALID:
                continue                                      # ③ 來源覆蓋不完整 ⇒ NaN、標不明
            col[k] = 100.0 if vals[k, j] >= valid.max() * REV_TOL else 0.0
        flags[sid] = col
    F = pd.DataFrame(flags, index=periods)
    # 攤到日曆：每期在 entry_pos 生效
    out = pd.DataFrame(np.nan, index=cal, columns=rev.columns)
    for p, (_, e) in rd.items():
        if p in F.index:
            out.iloc[e] = F.loc[p].to_numpy()
    return out.ffill()


def stock_raw(sid: str, market: str, cal: pd.DatetimeIndex, rev_flags: pd.Series | None = None, mp_frac: float = 1.0) -> pd.DataFrame | None:
    """一檔的逐日原始特徵（尚未百分位化）＋ 進出場價與流動性閘門 ＋ bars（有價收盤根數，自序列起累計）。全部只看 t 及之前。
    mp_frac：每個回看窗的 min_periods ＝ ceil(w × mp_frac)。⛔ 正式值一律 1.0（v3 補件 §3-2：min_periods＝w）；0.5 只給 §4-1 的常設斷言用
    （閘門 MIN_BARS 擋乾淨 ⇒ 合格列上 0.5 與 1.0 逐位元相同；不同就是閘門沒擋到那一欄的缺值）。"""
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    mp = lambda w: max(1, int(np.ceil(w * mp_frac)))
    c = df["close"].ffill()
    o = df["open"]
    vol = pd.to_numeric(df["volume"], errors="coerce"); amt = pd.to_numeric(df["amount"], errors="coerce")
    # 〈七十七〉（K線分析 2210 §二）：無成交日的 amount／volume 是【記錄形式的空缺】——日檔只收當天有成交的證券，真值＝0 ⇒ 還原為 0，⛔ 不是補值、不進放棄組。
    # 依據＝該日日檔存在（cal 就是 data/universe/daily/ 的檔名集合）且不含該檔；只在該檔首末成交日之間還原（上市前／下市後仍 NaN）。
    tr = df["traded"].to_numpy(bool)
    if tr.any():
        i0, i1 = int(np.argmax(tr)), len(tr) - 1 - int(np.argmax(tr[::-1]))
        inside = np.zeros(len(tr), bool); inside[i0:i1 + 1] = True
        fill0 = inside & ~tr
        vol = vol.where(~fill0, 0.0); amt = amt.where(~fill0, 0.0)
    shares = load_shares(sid, cal); inst = load_inst(sid, cal)
    ma20, ma60, ma120 = c.rolling(20, min_periods=mp(20)).mean(), c.rolling(60, min_periods=mp(60)).mean(), c.rolling(120, min_periods=mp(120)).mean()
    out = pd.DataFrame(index=cal)
    out["ret_120"] = c / c.shift(120) - 1
    out["ret_20"] = c / c.shift(20) - 1
    out["dist_hi120"] = c / c.rolling(120, min_periods=mp(120)).max() - 1
    out["dist_lo120"] = c / c.rolling(120, min_periods=mp(120)).min() - 1
    out["vol60"] = c.pct_change().rolling(60, min_periods=mp(60)).std() * np.sqrt(245)
    out["vr_20_120"] = amt.rolling(20, min_periods=mp(20)).mean() / amt.rolling(120, min_periods=mp(120)).mean()
    out["amt20"] = amt.rolling(20, min_periods=mp(20)).mean()
    k = shares / 1000.0
    out["turn20"] = vol.rolling(20, min_periods=mp(20)).mean() / 1000.0 / k
    out["fore20"] = inst["foreign"].rolling(20, min_periods=mp(20)).sum() / k
    out["trust20"] = inst["trust"].rolling(20, min_periods=mp(20)).sum() / k
    out["ma_stack"] = ((c > ma20) & (ma20 > ma60) & (ma60 > ma120)).astype(float) * 100
    out["ma60_up"] = (ma60 > ma60.shift(20)).astype(float) * 100
    out.loc[ma120.isna(), "ma_stack"] = np.nan; out.loc[ma60.shift(20).isna(), "ma60_up"] = np.nan
    out["rev_hi24"] = rev_flags.reindex(cal).to_numpy(float) if rev_flags is not None else np.nan
    out["shares_ok"] = shares.notna().astype(int)
    out["inst_nan20"] = inst["foreign"].isna().astype(int).rolling(20, min_periods=1).sum()   # 近 20 日法人缺值日數（只給放棄組⑩成因用，不是特徵）
    out["bars"] = df["traded"].astype(bool).cumsum().to_numpy()      # 有價收盤根數（ffill 前的原始有成交列，自序列起算累計）
    out["notraded_inside"] = (inside & ~tr).astype(int) if tr.any() else 0    # 該日是區間內部無成交日（amount 已還原 0）——只給放棄組／統計用
    out["close"] = c; out["open"] = o; out["traded"] = df["traded"].astype(bool)
    return out


def pct_strict_less(x: pd.Series) -> pd.Series:
    """v3 §4-2（策略線 0818 確認）：pct ＝ 嚴格小於 v 的個數 ÷ 該欄有限值的檔數 × 100
    ＝ np.searchsorted(sorted_x, v, side="left") / len(x) * 100。同值取最低名次；母體含自己；NaN／inf 不進分母、結果 NaN（之後補 50）。"""
    v = pd.to_numeric(x, errors="coerce").astype(float)
    ok = np.isfinite(v.to_numpy())
    out = pd.Series(np.nan, index=x.index, dtype=float)
    if ok.sum() == 0:
        return out
    xs = np.sort(v.to_numpy()[ok])
    out[ok] = np.searchsorted(xs, v.to_numpy()[ok], side="left") / len(xs) * 100.0
    return out


def cross_section(day: pd.DataFrame) -> pd.DataFrame:
    """同一量測日的合格母體（列＝stock_id）：百分位特徵 → 0～100（pct_strict_less：嚴格小於／有限值數、同值最低名次），布林照舊；缺值補 50。"""
    X = pd.DataFrame(index=day.index)
    for f in PCT_FEATURES:
        X[f] = pct_strict_less(day[f])
    for f in BOOL_FEATURES:
        X[f] = day[f]
    return X.fillna(FILL)


def assign(X: pd.DataFrame, centers: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """標準化後取歐氏距離最近的中心。centers：(4, 13) ⚠ 在【標準化空間】（KMeans 擬合的那個空間）；mu／sd：(13,) 是百分位／布林特徵的均值與標準差。⛔ 中心由登錄給，這裡不擬合。"""
    Z = (X[FEATURES].to_numpy(float) - np.asarray(mu, float)) / np.asarray(sd, float)
    C = np.asarray(centers, float)
    d = ((Z[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
    return d.argmin(axis=1)


def forward_returns(raw: pd.DataFrame, pos: int, holds=HOLDS) -> dict:
    """量測日 pos：次日開盤進、H 日後收盤出的毛報酬（開盤 NaN ⇒ NaN）。"""
    o = raw["open"].to_numpy(float); c = raw["close"].to_numpy(float); n = len(o)
    e = pos + 1
    out = {"entry_pos": e}
    if e >= n or np.isnan(o[e]):
        return {**out, **{f"ret_{H}": np.nan for H in holds}}
    for H in holds:
        x = e + H
        out[f"ret_{H}"] = (c[x] / o[e] - 1) if x < n else np.nan
    return out

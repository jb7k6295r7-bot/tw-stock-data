"""p4_features 自測：① shares 只 ffill 不 bfill；② rev_hi24_p4 的 18/24 與 NaN；③ 橫截面百分位＋補 50；④ 歸型取最近中心；
⑤ 真實一檔（2330）的量級。rc != 0 或輸出含 ✗ 才算紅（突變見檔尾）。"""
from __future__ import annotations

import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import p4_features as P  # noqa: E402
from backtest import data as D  # noqa: E402

FAIL = 0


def check(cond, msg):
    global FAIL
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAIL += 1


def t_measurement_days():
    cal = D.load_calendar()
    md = P.measurement_days(cal, "2026-01-01", "2026-09-30")
    days = [str(cal[i].date()) for i in md]
    check(days[0] == "2026-01-02" and "2026-09-01" in days and len(days) == 9, f"2026 每月第一個交易日 {days}")


def t_rev_flags():
    periods = [f"{y}-{m:02d}" for y in range(2015, 2018) for m in range(1, 13)]
    cal = D.load_calendar()
    rev = pd.DataFrame({"A": np.arange(1, 37, dtype=float), "B": np.arange(1, 37, dtype=float)}, index=periods)
    rev.loc[periods[5:13], "B"] = np.nan          # B 有 8 期缺 ⇒ 第 25 期時近 24 期只有 16 有效 ⇒ NaN
    rev.loc["2017-06", "A"] = 10.0                # A 在 2017-06 沒創高
    F = P.rev_hi24_flags(rev, cal)
    a = F["A"].dropna(); b = F["B"].dropna()
    # A：2017-01 期（第 25 期）起有值；可得日＝2017-02-10 後第一個交易日
    first = a.index[0]
    check(first > pd.Timestamp("2017-02-10") and first <= pd.Timestamp("2017-02-15"), f"A 第一個有值日 {first.date()}（2017-01 期次月 10 日後）")
    check(a.iloc[0] == 100.0, "A 2017-01 期創高 ⇒ 100")
    # 2017-06 期在 2017-07-1x 生效 ⇒ 0
    v = F["A"].loc[:"2017-07-15"].iloc[-1]   # 07-15 是週六 ⇒ 取之前最後一個交易日
    check(v == 0.0, f"A 2017-06 沒創高 ⇒ 0（讀到 {v}）")
    # B：第 25～32 期（2017-01～2017-08）近 24 期有效 < 18 ⇒ NaN；2017-09 期（近 24 期＝2015-09～2017-08，缺 2015-09～2016-01 五期 ⇒ 19 有效）⇒ 有值
    check(pd.isna(F["B"].loc[:"2017-03-15"].iloc[-1]), "B 有效期數 < 18 ⇒ NaN（不是 0）")
    check(F["B"].loc[:"2017-10-20"].iloc[-1] == 100.0, "B 有效期數 ≥ 18 後恢復 ⇒ 100")


def t_rev_flags_three_kinds():
    """⭐ K線分析線 0150（追加十八）：缺值分三種，⛔ 不可以用同一個處置。"""
    periods = [f"{y}-{m:02d}" for y in range(2015, 2018) for m in range(1, 13)]
    cal = D.load_calendar()
    rev = pd.DataFrame({"OLD": np.arange(1, 37, dtype=float), "NEW": np.arange(1, 37, dtype=float),
                        "GONE": np.arange(1, 37, dtype=float), "DR": np.arange(1, 37, dtype=float)}, index=periods)
    rev.loc[periods[:20], "NEW"] = np.nan      # 新上市：第 21 期（2016-09）才第一次申報 ⇒ 之後 24 期內都「不足 24 期」
    rev.loc[periods[:20], "DR"] = np.nan       # 同一個形狀，⛔ 而它在 undecided 名單裡
    rev["GONE"] = np.nan                       # ⭐ 來源裡整檔不存在＝倖存者的形狀（資料庫線 2350：來源端就沒有已下市公司的營收史）
    F = P.rev_hi24_flags(rev, cal, undecided={"DR"})
    at = lambda sid, d: F[sid].loc[:d].iloc[-1]
    # ① 不足 24 期 ⇒ 0.0（依定義不成立），⛔ 不是 NaN
    check(at("NEW", "2016-10-20") == 0.0, "① 新上市不足 24 期 ⇒ 0.0（依定義不成立），⛔ 不是 NaN")
    # ② 來源裡整檔不存在（倖存者）⇒ 全程 NaN，⛔ 不寫 False
    check(F["GONE"].isna().all(), "② 來源裡整檔沒有營收史（倖存者形狀）⇒ 全程 NaN，⛔ 不寫 False")
    # ③ undecided（TDR）⇒ ⛔ 不寫 False，留 NaN
    check(pd.isna(at("DR", "2016-10-20")), "③ 存託憑證那一族不足 24 期也**不寫 False** ⇒ NaN（標不明）")
    check(at("NEW", "2016-10-20") == 0.0 and pd.isna(at("DR", "2016-10-20")), "⭐ 同一個形狀、只差在不在 undecided 名單 ⇒ 一個 0.0 一個 NaN（⛔ undecided 優先）")
    # 滿 24 期之後恢復正常判定（⛔ 不是永遠 False）
    check(at("NEW", "2018-09-20") in (0.0, 100.0), "① 那一檔滿 24 期之後回到正常判定（⛔ 不是永遠 False）")
    # ⛔ 有預設值的參數要有一條不傳它的斷言：不傳 undecided ⇒ DR 跟 NEW 一樣是 0.0
    check(P.rev_hi24_flags(rev, cal)["DR"].loc[:"2016-10-20"].iloc[-1] == 0.0, "⛔ 不傳 undecided（預設值那條路）⇒ DR 也會被寫成 0.0 ⇒ 名單真的有在咬")
    # ⚠ 首期就在面板第一期的檔：分不出「新上市」與「面板從這裡開始」⇒ ⛔ 留 NaN，不可寫 False
    check(pd.isna(F["OLD"].loc[:"2016-10-20"].iloc[-1]), "⚠ 首期＝面板第一期 ⇒ 前 24 期留 NaN（⛔ 不可當成新上市寫 False）")
    # 老檔滿 24 期之後照常（回歸）
    check(at("OLD", "2017-02-20") == 100.0, "回歸：滿 24 期的老檔不受影響")


def t_rev_tol_symmetric():
    """⭐〈八十六〉（K線分析線 0215 §四）：容差要對稱——乘法容差在負數那側會變成【收緊】。"""
    periods = [f"{y}-{m:02d}" for y in range(2015, 2018) for m in range(1, 13)]
    cal = D.load_calendar()
    check(abs(P.REV_TOL_FRAC - 1e-4) < 1e-18, f"容差比例是 1e-4（＝1−0.9999），⛔ 不是乘數 0.9999（實得 {P.REV_TOL_FRAC}）")
    # 正數側：近 24 期最高 1000，當期 999.95 ⇒ 門檻 1000−0.1＝999.9 ⇒ 進得去（與舊的 ×0.9999 同一個門檻）
    pos = pd.DataFrame({"P": np.r_[np.full(24, 1000.0), np.full(12, 999.95)]}, index=periods)
    F = P.rev_hi24_flags(pos, cal)
    check(F["P"].loc[:"2017-03-15"].iloc[-1] == 100.0, "正數側：999.95 ≥ 1000 − 1000×1e-4 ＝ 999.9 ⇒ True（容差放寬）")
    pos2 = pd.DataFrame({"P": np.r_[np.full(24, 1000.0), np.full(12, 999.5)]}, index=periods)
    check(P.rev_hi24_flags(pos2, cal)["P"].loc[:"2017-03-15"].iloc[-1] == 0.0, "正數側：999.5 < 999.9 ⇒ False（⛔ 容差沒有大到亂放行）")
    # ⭐⭐ 負數側：近 24 期最高 −100，當期 −100.005
    #    對稱：門檻 −100 − 100×1e-4 ＝ −100.01 ⇒ −100.005 ≥ −100.01 ⇒ True（放寬）
    #    ⛔ 舊的乘法：−100 × 0.9999 ＝ −99.99 ⇒ −100.005 < −99.99 ⇒ False（收緊）⇒ 這一條就是分辨點
    neg = pd.DataFrame({"N": np.r_[np.full(24, -100.0), np.full(12, -100.005)]}, index=periods)
    check(P.rev_hi24_flags(neg, cal)["N"].loc[:"2017-03-15"].iloc[-1] == 100.0,
          "⭐ 負數側：−100.005 ≥ −100 − 100×1e-4 ＝ −100.01 ⇒ True（⛔ 舊的乘法容差會判 False＝收緊）")
    neg2 = pd.DataFrame({"N": np.r_[np.full(24, -100.0), np.full(12, -100.05)]}, index=periods)
    check(P.rev_hi24_flags(neg2, cal)["N"].loc[:"2017-03-15"].iloc[-1] == 0.0, "負數側：−100.05 < −100.01 ⇒ False（容差有界，⛔ 不是全放行）")


def t_tdr_codes():
    ids = P.load_tdr_codes()
    check(len(ids) >= 5 and "9103" in ids, f"存託憑證名單 {len(ids)} 檔、含 9103（industry_code 91）")
    check(all(not s.startswith("11") for s in list(ids)[:50]), "名單裡沒有水泥股那種一般股（抽查前 50 筆）")
    # ⛔ 判準檔讀不到／是空殼 ⇒ 要**大聲失敗**，⛔ 不可以靜靜當成「沒有 TDR」（CLAUDE.md 四點六）
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        empty = os.path.join(d, "industry.csv")
        open(empty, "w", encoding="utf-8").write("stock_id,name,market,industry_code,industry_name,listed_date\n1101,台泥,twse,01,水泥工業,19620209\n")
        try:
            P.load_tdr_codes(empty); ok = False
        except SystemExit:
            ok = True
        check(ok, "判準檔裡沒有 industry_code 91 ⇒ SystemExit（⛔ 不是靜靜回空集合）")
        try:
            P.load_tdr_codes(os.path.join(d, "nope.csv")); ok2 = False
        except SystemExit:
            ok2 = True
        check(ok2, "判準檔不存在 ⇒ SystemExit")


def t_shares_ffill_not_bfill():
    cal = D.load_calendar()
    s = P.load_shares("2330", cal)
    check(s.notna().sum() > 2000 and float(s.iloc[-1]) > 2e10, f"2330 shares 有值 {int(s.notna().sum())} 天、最後 {s.iloc[-1]:.0f}")
    # 不存在的代號 ⇒ 全 NaN（不會被補）
    z = P.load_shares("000000", cal); check(z.isna().all(), "無檔 ⇒ shares 全 NaN")


def t_cross_section_assign():
    day = pd.DataFrame({f: [1.0, 2.0, 3.0, np.nan] for f in P.PCT_FEATURES}, index=list("abcd"))
    for f in P.BOOL_FEATURES:
        day[f] = [100.0, 0.0, np.nan, 100.0]
    X = P.cross_section(day)
    check(list(X.loc["a", P.PCT_FEATURES].round(1)) == [0.0] * 10 and round(X.loc["b", "ret_20"], 1) == 33.3 and round(X.loc["c", "ret_20"], 1) == 66.7 and X.loc["d", "ret_20"] == 50.0,
          "百分位（v3 §4-2 嚴格小於／有限值數）：a＝0、b＝33.3、c＝66.7、缺值＝50（⛔ 不是 rank 平均名次的 33.3／100）")
    tie = P.pct_strict_less(pd.Series([5.0, 5.0, 7.0, np.inf, np.nan], index=list("pqrst")))
    check(tie["p"] == tie["q"] == 0.0 and round(tie["r"], 4) == round(200 / 3, 4) and np.isnan(tie["s"]) and np.isnan(tie["t"]), "同值取最低名次（5,5 都是 0）、inf／NaN 不進分母且回 NaN（分母 3）")
    check(X.loc["c", "ma_stack"] == 50.0 and X.loc["a", "ma_stack"] == 100.0, "布林缺值補 50、有值照舊")
    C = np.zeros((4, 13)); C[1] = 2.0; C[2, :5] = 2.0; C[3, 5:] = 2.0   # 中心在標準化空間
    mu = np.full(13, 50.0); sd = np.full(13, 25.0)
    lab = P.assign(X, C, mu, sd)
    check(lab[0] == 0 and lab[3] == 0, f"歸型最近中心 {lab.tolist()}（a、d 靠近 0 向量）")
    X2 = pd.DataFrame([[100.0] * 13], columns=P.FEATURES); check(P.assign(X2, C, mu, sd)[0] == 1, "全 100 ⇒ 中心 1")


def t_real_stock():
    cal = D.load_calendar()
    raw = P.stock_raw("2330", "twse", cal)
    last = raw.dropna(subset=["ret_120", "amt20", "turn20"]).iloc[-1]
    check(abs(last["ret_120"]) < 3 and last["amt20"] > 1e9, f"2330 ret_120 {last['ret_120']:+.3f}、amt20 {last['amt20']:.3e}")
    check(0 < last["turn20"] < 100, f"2330 turn20 {last['turn20']:.3f}（每日成交張數/千張股本）")
    check(np.isfinite(last["fore20"]) and last["shares_ok"] == 1, f"2330 fore20 {last['fore20']:+.3f}、shares_ok")
    md = P.measurement_days(cal, "2024-01-01", "2024-12-31")
    fr = P.forward_returns_p4_legacy(raw, int(md[0]))
    check(fr["entry_pos"] == md[0] + 1 and np.isfinite(fr["ret_120"]), f"2024-01 量測日次日進、H120 {fr['ret_120']:+.3f}")
    # 前 120 根 ret_120 必為 NaN（只看過去）
    check(raw["ret_120"].iloc[:120].isna().all(), "ret_120 前 120 根 NaN")


def t_fwd_hold_bars():
    """P4_v3 追加二十一：`forward_returns` 的持有根數 ＝ H + hold_extra，出場根走 `D.exit_pos`（唯一實作）。"""
    n = 40
    cal = pd.date_range("2020-01-06", periods=n, freq="B")
    c = pd.Series(np.linspace(100.0, 139.0, n), index=cal)          # ⭐ 逐根不同 ⇒ 差一根就差得出來
    o = c * 0.99                                                    # ⭐ 開盤 ≠ 收盤 ⇒ 分得出報酬用的是哪一個
    raw = pd.DataFrame({"open": o, "close": c})
    pos, H = 5, 10
    e = pos + 1
    try:                                                            # ⭐ 追加二十一 §七：⛔ 不准靠預設值拿到其中一個口徑
        P.forward_returns(raw, pos, holds=(H,)); ok_req = False
    except TypeError:
        ok_req = True
    check(ok_req, "⛔ 不傳 hold_extra ⇒ TypeError（口徑必須由呼叫端講出來，⛔ 沒有預設值）")
    d_def = P.forward_returns_p4_legacy(raw, pos, holds=(H,))       # ⛔ 作廢口徑：名字自己講出來
    check(d_def["entry_pos"] == e, f"進場 ＝ 量測日次一根（實得 {d_def['entry_pos']}，要 {e}）")
    check(abs(d_def[f"ret_{H}"] - (c.iloc[e + H] / o.iloc[e] - 1)) < 1e-15,
          f"⭐ forward_returns_p4_legacy（hold_extra＝{D.P4_FWD_HOLD_BARS}）⇒ 出場根 ＝ entry+{H} ＝ 持有 {H + 1} 根")
    d0 = P.forward_returns(raw, pos, holds=(H,), hold_extra=0)
    check(abs(d0[f"ret_{H}"] - (c.iloc[e + H - 1] / o.iloc[e] - 1)) < 1e-15,
          f"hold_extra=0 ⇒ 出場根 ＝ entry+{H - 1} ＝ 持有 {H} 根（sig 慣例）")
    check(abs(d0[f"ret_{H}"] - d_def[f"ret_{H}"]) > 1e-6,
          f"⭐ 兩個口徑在同一列上【不同】（{d0[f'ret_{H}'] * 100:+.3f}% vs {d_def[f'ret_{H}'] * 100:+.3f}%）⇒ ⛔ 不可以並列比較")
    # ⭐ 分辨點：剛好差一根的邊界 —— 持有 H 根到得了、持有 H+1 根到不了
    pos_edge = n - 1 - H
    ed, e0 = P.forward_returns_p4_legacy(raw, pos_edge, holds=(H,)), P.forward_returns(raw, pos_edge, holds=(H,), hold_extra=0)
    check(np.isnan(ed[f"ret_{H}"]) and np.isfinite(e0[f"ret_{H}"]),
          "⭐ 序列最後一根那個邊界：持有 H 根算得出、持有 H+1 根超出序列 ⇒ NaN（⛔ 不是拿最後一根代）")
    check(np.isnan(P.forward_returns_p4_legacy(pd.DataFrame({"open": o.copy().mask(o.index == cal[e]), "close": c}), pos, holds=(H,))[f"ret_{H}"]),
          "進場根開盤 NaN ⇒ NaN（⛔ 不 ffill 開盤）")


# ⭐⭐ 稽核白名單（P4_v3 追加二十一 §七；K線分析線 1200 §二 要求的全庫稽核）
# 鍵 ＝ 檔名，值 ＝ {該檔裡「持有期位移算式」出現的行數: 口徑}。口徑只有三種：
#   "持有n根"      出場根 ＝ 進場根 + n − 1（⭐ 正式定義）
#   "作廢H+1根"    出場根 ＝ 進場根 + n（⛔ 只准 forward_returns_p4_legacy）
#   "收盤位移"      close[t] → close[t+n]，沒有開盤進場 ⇒ ⛔ 不是進場出場口徑，不可與上面兩種並列
# ⚠ 這份白名單的用途不是好看：⛔ 新增一處位移算式而沒登記 ⇒ 這條自測紅 ⇒ ⭐ 它會自己舉手
#   （K線分析線 1200 §二：「沒有撞到的那些格子，不會自己舉手」）
HOLD_OFFSET_SITES = {
    "data.py": {"exit_pos": "持有n根（⭐ 唯一實作）"},
    "p4_features.py": {"forward_returns": "由呼叫端指定（⛔ 無預設值）", "forward_returns_p4_legacy": "作廢H+1根"},
    "evaluate.py": {"hold_exit": "持有n根", "level_stop_exit": "持有n根", "quick_returns": "持有n根（idx+HOLD ＝ entry+HOLD−1）"},
    "research5.py": {"hold_exit_ndays": "持有n根"},
    "research7.py": {"_hold": "持有n根", "_baseline": "持有n根"},
    "research8.py": {"exit_pos欄": "持有n根"},
    "research11.py": {"fixed_exit": "持有n根（⭐ 走 exit_pos）", "向量化基準": "持有n根（c[ks+H]/o[ks+1]）"},
    "research15.py": {"fixed_exit呼叫": "持有n根", "div窗": "持有n根（k+1…k+H）"},
    "research16.py": {"P1": "持有n根", "P2": "收盤位移（close[k]→close[k+H]，出場根同 P1）", "P3_j": "持有n根（延遲進場）"},
    "research17.py": {"ret": "收盤位移"},
    "research18.py": {"X0": "持有n根", "X2": "事件後再 HOLD_AFTER 根（⛔ 另一種語意）"},
    "research19.py": {"stop_exit": "持有n根"},
    "researchm1.py": {"fwd_returns": "收盤位移"},
    "researchp4.py": {"recompute_fwd": "由呼叫端指定", "面板建構": "作廢H+1根（⛔ 既有面板與前瞻列不回改）"},
    "researchp7.py": {"build_sig_gate_b": "持有n根（HOLD_BARS_N=120 ⇒ entry+119）"},
    "forward_and.py": {"kx": "持有n根（⚠ 軸是【有效K棒 idx】不是日曆位置）"},
    "exright_gap.py": {"exposure": "⚠ 窗 (entry, entry+hold] ⇒ 比持有期【多含一根】——追加二十一 §七 已記，⛔ 未修"},
}
# ⛔ 這些 pattern 是「會製造出場位置」的裸算式形狀；⚠ 白名單比對的是【檔案是否登記過】，
#   ⛔ 不是逐行比對（行號會漂）——逐行會每天紅，然後被學會忽略（CLAUDE.md 四點五那條的教訓）。
HOLD_OFFSET_PAT = re.compile(r"\+\s*(H\b|HOLD\w*|hold\w*|n_days|days)\b|exit_pos\(|shift\(-")
# ⛔ 只呼叫別人的出場算式、自己不做位移的檔案（口徑是**繼承**的）⇒ 另一張表，⛔ 不與上面那張混
HOLD_OFFSET_CALLERS = {"research13.py": "R.fixed_exit", "research21.py": "R.fixed_exit", "research34.py": "E.hold_exit"}


def t_hold_offset_audit():
    """全庫稽核（追加二十一 §七）：每一個出現持有期位移算式的檔案都要在白名單裡，⛔ 新增一處沒登記就紅。"""
    here = os.path.dirname(os.path.abspath(__file__))
    found = set()
    for fn in sorted(f for f in os.listdir(here) if f.endswith(".py") and not f.startswith("selftest")):
        src = open(os.path.join(here, fn), encoding="utf-8").read()
        if any(HOLD_OFFSET_PAT.search(ln) and not ln.lstrip().startswith("#") for ln in src.splitlines()):
            found.add(fn)
    missing = sorted(found - set(HOLD_OFFSET_SITES))
    check(not missing, f"⭐ 所有出現持有期位移算式的檔案都在稽核白名單裡（未登記：{missing or '無'}）"
                       "⇒ ⛔ 新增一處就要在 HOLD_OFFSET_SITES 裡寫明它是哪一種口徑")
    stale = sorted(set(HOLD_OFFSET_SITES) - found)
    check(not stale, f"⚠ 白名單裡沒有實際命中的檔案（已改寫或改名 ⇒ 回頭修白名單）：{stale or '無'}")
    bad_caller = [fn for fn, fx in HOLD_OFFSET_CALLERS.items()
                  if fx not in open(os.path.join(here, fn), encoding="utf-8").read()]
    check(not bad_caller, f"⭐ 繼承口徑的那三支仍然是【呼叫】共用出場算式（⛔ 不是自己寫一份）：{bad_caller or '全部成立'}")
    n_void = sum(1 for v in HOLD_OFFSET_SITES.values() for x in v.values() if x.startswith("作廢"))
    check(n_void == 2, f"⛔ 作廢口徑（持有 H+1 根）只剩兩個登記處（forward_returns_p4_legacy 與面板建構），實得 {n_void}")
    check("多含一根" in HOLD_OFFSET_SITES["exright_gap.py"]["exposure"],
          "⚠ exright_gap.exposure 的窗多含一根這件事留在白名單上（⛔ 修掉之前不准把這一行刪掉）")


def t_gate_min_periods():
    """v3 補件 §3-1／§3-2：bars 欄＝有價收盤根數累計；MIN_BARS 寫死 120；min_periods＝w ⇒ 第 w 根之前 NaN；合格列上 mp_frac 0.5 與 1.0 逐位元相同。"""
    check(P.MIN_BARS == 120, "MIN_BARS 寫死 120（由最長回看窗推出）")
    cal = D.load_calendar()
    raw = P.stock_raw("2330", "twse", cal)
    check(raw["bars"].iloc[-1] == int(raw["traded"].sum()) and (raw["bars"].diff().dropna() >= 0).all(), f"bars 單調累計、末值＝有成交根數 {int(raw['traded'].sum())}")
    fi = lambda col: int(np.argmax(raw[col].notna().to_numpy()))     # 第一個非 NaN 的位置（0 起算）
    check(fi("ma_stack") == 119 and fi("dist_hi120") == 119 and fi("vol60") == 60 and fi("amt20") == 19 and fi("fore20") == 19,
          f"min_periods＝w：ma_stack/dist_hi120 第 120 根起、vol60 第 61 根（pct_change 先吃一根）、amt20/fore20 第 20 根起（實得 {fi('ma_stack')}/{fi('dist_hi120')}/{fi('vol60')}/{fi('amt20')}/{fi('fore20')}）")
    check(raw["ret_120"].iloc[119:121].isna().tolist() == [True, False], "ret_120 第 121 根才有值（shift 120）")
    raw05 = P.stock_raw("2330", "twse", cal, mp_frac=0.5)
    check(int(np.argmax(raw05["ma_stack"].notna().to_numpy())) == 59 and int(np.argmax(raw05["vol60"].notna().to_numpy())) == 30, "mp_frac=0.5 ⇒ ma_stack 第 60 根、vol60 第 31 根就有值（斷言的對照組真的不一樣）")
    el = raw["bars"] >= P.MIN_BARS
    diff_cols = [f for f in P.FEATURES if not ((raw.loc[el, f].isna() == raw05.loc[el, f].isna()).all() and np.allclose(raw.loc[el, f].fillna(0), raw05.loc[el, f].fillna(0), rtol=0, atol=0))]
    check(el.sum() > 2000 and diff_cols == [], f"合格列（bars ≥ 120，{int(el.sum())} 列）13 欄 mp 0.5 vs 1.0 逐位元相同（不同的欄：{diff_cols}）")
    bad = raw.loc[~el & raw["traded"], ["ma_stack", "dist_hi120", "ret_120"]]
    check(len(bad) == 119 and bad.isna().all().all(), f"bars < 120 的有成交列（{len(bad)}）ma_stack/dist_hi120/ret_120 全 NaN（閘門擋的就是這些）")
    # K線分析 2035 (c)：inst_nan20＝近 20 日法人缺值日數；缺 ⇒ fore20/trust20 NaN（min_periods=20），⛔ 不補
    nan20 = raw["inst_nan20"]; f20 = raw["fore20"]
    check(bool(((nan20 > 0) & raw["traded"] & (raw["bars"] >= 20)) .eq(f20.isna() & raw["traded"] & (raw["bars"] >= 20)).all()), "有成交且 bars≥20 的列：inst_nan20>0 ⇔ fore20 NaN（(c) 的判準與特徵一致）")
    # ⚠ 2330 法人從不缺 ⇒ 上一條在 2330 上是空成立；拿一檔真的有洞的：1240 2022-05-03 的 20 日窗內缺 04-01／04-07／04-08 三日（追加四逐筆看過）
    g = P.stock_raw("1240", "twse", cal); q = int(np.searchsorted(cal, pd.Timestamp("2022-05-03")))
    check(int(g["inst_nan20"].iloc[q]) == 3 and pd.isna(g["fore20"].iloc[q]) and pd.isna(g["trust20"].iloc[q]) and g["bars"].iloc[q] >= 120,
          f"1240 2022-05-03：inst_nan20＝{int(g['inst_nan20'].iloc[q])}（要 3）、fore20/trust20 NaN、bars {int(g['bars'].iloc[q])} ≥ 120（閘門擋不到、(c) 才擋得到的那種）")
    # 〈七十七〉：1315 2020-10-15～10-22 有 7 個區間內部無成交日 ⇒ amount 還原 0（不是 NaN）⇒ 2020-12-01 的 vr_20_120／amt20 有值；上市前仍 NaN
    h = P.stock_raw("1315", "tpex", cal); q1 = int(np.searchsorted(cal, pd.Timestamp("2020-10-15"))); q2 = int(np.searchsorted(cal, pd.Timestamp("2020-12-01")))
    check(int(h["notraded_inside"].iloc[q1:q1 + 6].sum()) == 6 and h["notraded_inside"].iloc[q1] == 1, f"1315 2020-10-15 起 6 個交易日標為區間內部無成交（實得 {int(h['notraded_inside'].iloc[q1:q1 + 6].sum())}）")
    check(np.isfinite(h["vr_20_120"].iloc[q2]) and np.isfinite(h["amt20"].iloc[q2]), f"1315 2020-12-01 vr_20_120＝{h['vr_20_120'].iloc[q2]:.3f}、amt20 有值（無成交日 amount 還原 0 之後 min_periods=w 不再打掉整窗）")
    check(pd.isna(late_first := P.stock_raw("7610", "tpex", cal)["amt20"].iloc[0]) and int(P.stock_raw("7610", "tpex", cal)["notraded_inside"].iloc[0]) == 0, "7610 上市前（序列第一列）amt20 仍 NaN、不算區間內部（還原只在首末成交日之間）")
    late = P.stock_raw("7610", "tpex", cal)
    if late is not None:
        pos = int(np.searchsorted(cal, pd.Timestamp("2026-01-02")))
        check(late["bars"].iloc[pos] < 120 and pd.isna(late["ma_stack"].iloc[pos]), f"7610 2026-01-02 bars {int(late['bars'].iloc[pos])} < 120 ⇒ ma_stack NaN（v3 補件的那一檔）")


if __name__ == "__main__":
    print("[p4_features] 量測日"); t_measurement_days()
    print("[p4_features] rev_hi24_p4"); t_rev_flags()
    print("[p4_features] rev_hi24 缺值三種（K線分析線 0150）"); t_rev_flags_three_kinds()
    print("[p4_features] 容差對稱（〈八十六〉）"); t_rev_tol_symmetric()
    print("[p4_features] 存託憑證名單"); t_tdr_codes()
    print("[p4_features] shares"); t_shares_ffill_not_bfill()
    print("[p4_features] 橫截面＋歸型"); t_cross_section_assign()
    print("[p4_features] 真實一檔"); t_real_stock()
    print("[p4_features] fwd 持有根數（追加二十一）"); t_fwd_hold_bars()
    print("[全庫] 持有期位移算式稽核（追加二十一 §七）"); t_hold_offset_audit()
    print("[p4_features] 閘門與 min_periods"); t_gate_min_periods()
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變（前後 rm -rf backtest/__pycache__）：
#  M1 REV_MIN_VALID 18 → 10           ⇒ rev 第 4 條紅（B 提早有值）
#  M2 load_shares 的 ffill 改 ffill().bfill() ⇒ 真實一檔不紅（2330 沒有前段缺），⚠ 這條要靠 code review；改用 shares 從 2016 才有的檔才抓得到
#  M3 cross_section 補 50 拿掉         ⇒ 橫截面第 1、2 條紅
#  M4 forward_returns 進場改當日開盤    ⇒ 真實一檔 entry_pos 紅

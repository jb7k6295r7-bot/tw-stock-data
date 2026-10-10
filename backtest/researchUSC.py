# -*- coding: utf-8 -*-
"""USREG-C 批（美股自選研究；裁定 seq321 §三 發號）——回測線計算子代理：C8 → C7 → C3 → C4 → C5 → C6（資料齊的六件）。
（C11、C12、C9、C2 另一子代理做：researchUSC_late.py、resultsUSC/late/；⛔ 本檔不碰。）

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC --item c8|c7|c3|c4|c5|c6|all [--procs 3]
    獨立查核：... -m backtest.researchUSC_check      網頁：... -m backtest.researchUSC_page

各件程式：researchUSC_c8.py（波動目標穩健性）、_c7.py（進場方式）、_c3.py（經典動能）、_c4.py（剔除股反彈）、_c5.py（同月季節性）、_c6.py（現金獲利）。
各件的補讀法寫在各自檔頭（台北時間）；本檔 K 標 ＝ 全批共同讀法。

登錄（美股策略線 seq1，寄出 2026-10-09 15:37；sha ＝ 整檔 sha256 前 16 碼，美股線已核）：
  C8 ← B8 波動目標穩健性 a3bbe592df10f4ed｜C7 ← B7 進場方式 eec986526b9f41a5｜C3 ← B3 經典動能 a98a1275a19c69f7
  C4 ← B4 剔除股反彈 20479c52532466ba｜C5 ← B5 同月季節性 a23a0b616ed17a57｜C6 ← B6 現金獲利 1fb69a5dbca84de7
裁定 seq321 §三（2026-10-09 15:52）：N（美股帳）C7 12、C4 2、C5 2、C6 2、C3 1；C8 不計 N、不判合格（事後追加，只描述＋前瞻）。
  相鄰件分開計 N、結果句並引：C3↔A3-12、C6↔A4-1、C4↔A4-7（A4-7 已結案，⛔ 不取代、⛔ 不退 N）。
  判定母體：C3、C5、C6 美股原生新題 ⇒ 合併母體當判定（⛔ 不套 seq316）；只 S&P 500、只 S&P 400 照報，兩欄方向相反要寫。C4、C7、C8 照登錄。
  C8 早年合成照 seq309（扣 DTB3＋0.25% 融資成本與費用率）；QQQ 1999-03 前不可判定。Chen & Welch 先驗參考：收下（結果句可附）。
全線規則：seq308（條件出場主臂、⛔ 不設最長天數、窗尾仍持有與持有天數分佈必報；固定 {20,60,120,240} 只描述）；
  seq321 §五（相對門檻、等效獨立檔數、0050 濾網角色）——只用在新登錄、⛔ 不回溯；本批登錄寄出（10-09 15:37）早於 seq321（15:52）⇒ 照報、不改規則。

⛔⛔ 私有資料：us-stock-data 是私有 repo ⇒ resultsUSC/ 只放彙總（年化、回落、比值、件數、比例、判語、sha）；
   逐日價格、財報原值、逐筆成交、權益曲線一律寫 ~/us_work/c/（repo 外）並列 sha。

═══ C 批共同讀法（K 標；⭐ 寫死於 2026-10-10 23:21（台北），寫死前 ⛔ 沒看任何 C 批報酬）═══
 K1 資料：個股價量 ＝ A3／A4 同一份（~/us_work/a4/world.npz、~/us_work/a3/stocks.pkl；us-stock-data 881c86a，聯集轉接層 researchUSA2_data；
    原始收盤 RCu ＝ Yahoo close × 日後拆股比（A4 G10））；ETF／指數 ＝ USREG-A1 同一份（~/usdata/60d2f99，researchUSA1_data.load_market；截到 2026-09-30）；
    本批新資料（剔除分類 removals_analysis.csv、ETF 費用率 etf_expense_ratios.csv、季現金流 quarterly_cfo.csv、季總資產 quarterly_assets.csv）
    讀 ~/usdata/b33bde6（git archive b33bde68，唯讀）。
 K2 組合層判準（seq242、W1b）：^SP500TR 同窗：年化 ＞ 基準 且 年化÷|回落| ≥ 基準比值 ⇒ 合格；只前者 ⇒ 另列；否則不合格（researchUSW1b.label，ANN 252）。
    窗 ＝ [第一個可進場日的前一交易日收盤, 2026-09-30]（策略與基準同起點，策略 1.0 起算）；「第一個可進場日」各件照實報。
 K3 換股簿引擎（C3、C5、C6；researchUSA4.sim_book 同式重寫，加「進場名單／續抱名單」兩張表）：換股日 e ＝ 每月第一個交易日；訊號只用 e−1 收盤以前；
    e 開盤成交：先賣（持股不在續抱名單 ⇒ e 開盤賣；開盤無效 ⇒ 延到下一個有效開盤）、再買（進場名單依優先序、跳過已持有、空槽才買、
    金額 ＝ min(前一日權益 ÷ 8, 現金)、開盤無效 ⇒ 該檔不買）；不再平衡既有持股；成本 ＝ 賣出時扣「進場金額 × 0.05%」（A4 G6）；
    斷點（轉接層 hard_break）⇒ 以前一日收盤結清、下市 ⇒ 最後收盤結清（A4 G11、G12）。持股在換股日已不在該欄母體 ⇒ 不在排名 ⇒ 落選賣出（A4 G3 換股簿型）。
    閘：「續抱名單 ＝ 進場名單 ∪ 緩衝帶」且進場從未用到緩衝帶時，本引擎權益 ＝ researchUSA4.sim_book（sel ＝ 續抱名單依優先序）逐日相同（≤1e−12）。
 K4 條件出場必報（seq308）：持有天數分佈（平均、中位、p10、p90、最長；交易日）、窗尾仍持有（筆、檔）、離頂多近（出場價 ÷ 持有期最高收盤 − 1 的中位）；
    固定 {20,60,120,240} 日只描述（換股簿 ＝ researchUSA4.sim_book fixed_h：新進者抱滿 H 根收盤賣、空槽到下一個換股日補）。
 K5 三欄：C3、C5、C6 合併 ＝ 判定；只 S&P 500、只 S&P 400 ＝ 排名母體只取該指數（描述）；兩欄標籤方向相反（一欄合格／另列、另一欄不合格）⇒ 結果句寫明。
 K6 等效獨立檔數（seq321 §五，加報、⛔ 不進判定）：每個換股日的持股，用前 60 個交易日日報酬（同時有效者）算兩兩相關平均 ρ̄，
    N_eff ＝ n ÷ (1 ＋ (n−1) ρ̄)（n ＝ 當天持股數；ρ̄ ＜ 0 截為 0）；報全期平均與中位。
 K7 相對門檻（seq321 §五）：本批照登錄；C3／C5／C6 的進出門檻是排名（前 10％／20％）＝ 已是相對；C4「≥ 5 美元」、C7「跌 10％」、C8 σ* 是固定值 ⇒ 登錄已寫理由，照報。
 K8 種子：抽籤 default_rng(102000＋r)，r ＝ 0～199；假訊號／隨機臂 default_rng([20261010, 件號, 臂號, r])。
 K9 事件層統計：月分群（曆月）95％ CI；C5、C6「逐月 SE」＝ 月報酬差序列的 sd÷√月數。C4 照 researchM.summ／verdict（曆月群集、20 日區段 n_eff）。
 K10 存活者偏差（必寫）：S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 結果偏向存活股、偏樂觀。
 K11 Chen & Welch 2026（What Useful Alphas?）先驗參考：C3、C5、C6 結果句後附「Chen & Welch 2026：2005 年後大中型股選股效果修正後近 0」（可選，照附）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))

READ_TS = "2026-10-10 23:21（台北）"
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSC")
WORK = os.path.expanduser("~/us_work/c")
NEWROOT = os.path.expanduser("~/usdata/b33bde6")
NEW_COMMIT = "b33bde68145eea96c6c4882f71b2a5352ba5c36e"
REG = {"C8": ("B8 波動目標穩健性", "a3bbe592df10f4ed"), "C7": ("B7 進場方式", "eec986526b9f41a5"), "C3": ("B3 經典動能", "a98a1275a19c69f7"),
       "C4": ("B4 剔除股反彈", "20479c52532466ba"), "C5": ("B5 同月季節性", "a23a0b616ed17a57"), "C6": ("B6 現金獲利", "1fb69a5dbca84de7")}
RULING = "裁定 seq321 §三（2026-10-09 15:52）"
NCOUNT = {"C8": 0, "C7": 12, "C3": 1, "C4": 2, "C5": 2, "C6": 2}
SURV = "S&P 400 整段缺價 48 檔、S&P 500 18 檔不在母體 ⇒ 結果偏向存活股、偏樂觀"
CW = "Chen & Welch 2026：2005 年後大中型股選股效果修正後近 0"
COST = 0.0005
COST_SENS = (0.0002, 0.0010)
N_SLOTS = 8
SEED0, NSEED = 102000, 200
FIXH = (20, 60, 120, 240)


def p_new(*a):
    return os.path.join(NEWROOT, "data", *a)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def _jdef(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (pd.Timestamp,)):
        return str(x.date())
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (set, tuple)):
        return list(x)
    return str(x)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def jdump(obj, name):
    os.makedirs(OUT, exist_ok=True)
    p = name if os.path.isabs(name) else os.path.join(OUT, name)
    json.dump(_clean(obj), open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_jdef)
    return p


def sha256f(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def log(m, f=None):
    print(m, flush=True)
    if f:
        with open(os.path.join(WORK, f), "a", encoding="utf-8") as fh:
            fh.write(m + "\n")


# ═════════════ 判準、統計 ═════════════
def metrics(eq, a, b, ann=252):
    """[a, b] 段（a ＝ 起點那天收盤，權益在 a 為基準）⇒ 年化、回落、比值。"""
    seg = np.asarray(eq[a:b + 1], float)
    yrs = (len(seg) - 1) / ann
    c = float((seg[-1] / seg[0]) ** (1 / yrs) - 1) if yrs > 0 else np.nan
    pk = np.maximum.accumulate(seg); m = float(((seg - pk) / pk).min())
    return {"年化": c, "回落": m, "比值": c / abs(m) if m < 0 else np.nan}


def label(c, m, cb, mb):
    if not (np.isfinite(c) and np.isfinite(m)) or m >= 0:
        return "—"
    k1 = c > cb; k2 = (c / abs(m)) >= (cb / abs(mb))
    return "合格" if (k1 and k2) else ("另列" if k1 else "不合格")


def opposite(l5, l4):
    good = {"合格", "另列"}
    return (l5 in good and l4 == "不合格") or (l4 in good and l5 == "不合格")


def clus_mean(x, grp, z=1.959963984540054):
    """群集（grp）穩健平均 CI：se ＝ sqrt(Σ_g (Σ_i∈g (x_i − x̄))²) ÷ n。"""
    x = np.asarray(x, float); grp = np.asarray(grp)
    ok = np.isfinite(x); x = x[ok]; grp = grp[ok]
    n = len(x)
    if n == 0:
        return {"n": 0}
    mu = float(x.mean())
    s = pd.Series(x - mu).groupby(grp).sum().to_numpy()
    se = float(np.sqrt((s ** 2).sum()) / n)
    return {"n": int(n), "平均": mu, "se": se, "lo": mu - z * se, "hi": mu + z * se, "群數": int(len(s))}


def month_series_ci(d, z=1.959963984540054):
    """逐月序列 ⇒ 平均、sd÷√T CI（K9）。"""
    d = np.asarray(d, float); d = d[np.isfinite(d)]
    T = len(d)
    if T < 2:
        return {"月數": T}
    mu = float(d.mean()); se = float(d.std(ddof=1) / np.sqrt(T))
    return {"月數": T, "平均": mu, "se": se, "lo": mu - z * se, "hi": mu + z * se, "t": mu / se if se > 0 else np.nan,
            "正的月比例": float(np.mean(d > 0))}


# ═════════════ 換股簿引擎（K3）═════════════
def book(Wd, rebs, keep, buy, N, t0, t1, cost=COST, brk=None, trades_out=None, on_buy=None, keep_fn=None, buy_fn=None):
    """keep：{e: set(j)} 續抱名單；buy：{e: [j…]} 進場名單（優先序）。keep_fn／buy_fn（可選）⇒ 取代兩表（隨機臂用，收 (e, 持股 set)）。
    → {"eq", "npos", "cashf", "costd", "buyd", "cnt", "open", "holds"(每個換股日持股)}。"""
    O, CF, valid, last = Wd["O"], Wd["CF"], Wd["valid"], Wd["last"]
    brk = Wd["pb"] if brk is None else brk
    n = len(Wd["cal"])
    eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    npos = np.zeros(n, np.int16); cashf = np.zeros(n); costd = np.zeros(n); buyd = np.zeros(n)
    cnt = Counter(); rset = set(int(e) for e in rebs if t0 <= e <= t1)
    tr = [] if trades_out is not None else None
    holds = {}
    for t in range(t0, t1 + 1):
        for j in list(pos):
            u, amt, b, hi = pos[j]
            if t > b and brk[t, j]:
                px = CF[t - 1, j]; why = "斷點"
            elif t > last[j]:
                px = CF[last[j], j]; why = "下市"
            else:
                continue
            pos.pop(j); pend.discard(j)
            cash += u * px - amt * cost; costd[t] += amt * cost; cnt["sell_" + why] += 1
            if tr is not None:
                tr.append((j, b, t - 1, px / (amt / u) - 1, px / hi - 1 if hi > 0 else np.nan, why))
        isreb = t in rset
        if isreb:
            ks = keep_fn(t, set(pos)) if keep_fn is not None else keep.get(t, set())
            pend |= (set(pos) - set(ks))
            pend -= set(ks)
        for j in sorted(pend):
            if j not in pos:
                pend.discard(j); continue
            o_t = O[t, j]
            if valid[t, j] and np.isfinite(o_t) and o_t > 0:
                px = o_t
            else:
                cnt["sell_delayed"] += 1; continue
            u, amt, b, hi = pos.pop(j)
            cash += u * px - amt * cost; costd[t] += amt * cost; cnt["sell"] += 1; pend.discard(j)
            if tr is not None:
                tr.append((j, b, t, px / (amt / u) - 1, px / max(hi, px) - 1, "換股"))
        if isreb:
            bl = buy_fn(t, set(pos)) if buy_fn is not None else buy.get(t, [])
            free = N - len(pos)
            new = [j for j in bl if j not in pos][:max(free, 0)]          # sim_book 同式：取前 free 檔，開盤無效那檔不買、⛔ 不遞補
            for j in new:
                o_t = O[t, j]
                if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                    cnt["buy_halt"] += 1; continue
                amt = min(eq[t - 1] / N, cash)
                if amt <= 1e-12:
                    break
                cash -= amt; pos[j] = [amt / o_t, amt, t, o_t]; cnt["buy"] += 1; buyd[t] += amt
                if on_buy is not None:
                    on_buy(j, t)
            holds[t] = sorted(pos)
        hv = 0.0
        for j, p in pos.items():
            c = CF[t, j]; hv += p[0] * c
            if c > p[3]:
                p[3] = c
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    if tr is not None:
        trades_out.extend(tr)
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": dict(cnt),
            "open": [(j, p[2], p[3]) for j, p in pos.items()], "holds": holds}


def hold_stats(trades, b, nopen):
    """K4：trades ＝ [(j, 進場, 出場, 報酬, 離頂, 原因)]；nopen ＝ 窗尾仍持有檔數。"""
    done = [x for x in trades if x[2] <= b]
    hd = np.array([x[2] - x[1] for x in done], float)
    near = np.array([x[4] for x in done if np.isfinite(x[4])], float)
    out = {"出場筆數": int(len(done)), "窗尾仍持有（檔）": int(nopen)}
    if len(hd):
        out.update({"持有天數_平均": float(hd.mean()), "持有天數_中位": float(np.median(hd)), "持有天數_p10": float(np.percentile(hd, 10)),
                    "持有天數_p90": float(np.percentile(hd, 90)), "持有天數_最長": float(hd.max()),
                    "離頂多近_中位": float(np.median(near)) if len(near) else np.nan, "出場勝率": float(np.mean([x[3] > 0 for x in done])),
                    "出場原因": dict(Counter(x[5] for x in done))})
    return out


def book_summary(res, a, b, bm, trades=None):
    m = metrics(res["eq"], a, b)
    yrs = (b - a) / 252
    meq = float(res["eq"][a:b + 1].mean())
    m.update({"標籤": label(m["年化"], m["回落"], bm["年化"], bm["回落"]), "平均持股": float(res["npos"][a + 1:b + 1].mean()),
              "現金比例": float(np.nanmean(res["cashf"][a + 1:b + 1])), "每年換手": float(res["buyd"][a:b + 1].sum()) / meq / yrs,
              "成本／年": float(res["costd"][a:b + 1].sum()) / meq / yrs, "計數": res["cnt"]})
    if trades is not None:
        m.update(hold_stats(trades, b, len(res["open"])))
    return m


def n_eff(Wd, holds, look=60):
    """K6：每個換股日持股的前 look 日報酬相關 ⇒ N_eff。"""
    CF = Wd["CF"]; V = Wd["valid"]
    out = []
    for t, js in holds.items():
        if len(js) < 2 or t - look - 1 < 0:
            if len(js) == 1:
                out.append(1.0)
            continue
        P = CF[t - look - 1:t, js]; vv = V[t - look - 1:t, js]
        with np.errstate(invalid="ignore", divide="ignore"):
            R = P[1:] / P[:-1] - 1
        R = np.where(vv[1:] & vv[:-1], R, np.nan)
        df = pd.DataFrame(R)
        cm = df.corr(min_periods=20).to_numpy()
        iu = np.triu_indices(len(js), 1)
        rho = np.nanmean(cm[iu]) if np.isfinite(cm[iu]).any() else np.nan
        if not np.isfinite(rho):
            continue
        rho = max(rho, 0.0); k = len(js)
        out.append(k / (1 + (k - 1) * rho))
    out = np.array(out, float)
    return {"平均": float(out.mean()) if len(out) else np.nan, "中位": float(np.median(out)) if len(out) else np.nan, "換股日數": int(len(out))}


def year_window(eq, cal, a, b):
    """100 萬在 a 前一交易日收盤 ⇒ [a, b] 期末（萬）、年內最大回落。"""
    base = eq[a - 1]
    seg = np.r_[1.0, eq[a:b + 1] / base]
    pk = np.maximum.accumulate(seg)
    return {"期末（萬）": float(seg[-1] * 100), "年內最大回落": float(((seg - pk) / pk).min()), "谷底剩（萬）": float(seg.min() * 100)}


# ═════════════ 選股換股簿共用（C3、C5、C6；K3～K6）═════════════
_RW: dict = {}
_JOB: dict = {}


def rworld():
    """A4 世界（world.npz）＋月表＋基準＋GICS。"""
    if not _RW:
        from backtest import researchUSA4 as A4
        Wd = A4.load_world()
        cal = Wd["cal"]; n = len(cal)
        w1 = int(cal.searchsorted(pd.Timestamp("2026-09-30"))); assert cal[w1] == pd.Timestamp("2026-09-30")
        ym = np.asarray(cal.year * 12 + cal.month - 1)
        first, last = {}, {}
        for i, k in enumerate(ym):
            first.setdefault(int(k), i); last[int(k)] = i
        ms = np.array(sorted(v for v in first.values() if 0 < v <= w1))
        _RW.update(Wd=Wd, A4=A4, cal=cal, n=n, w1=w1, ym=ym, first=first, last=last, ms=ms, B=A4.bench_series(cal),
                   sec=A4.load_sectors(), cpb=np.cumsum(Wd["pb"], axis=0, dtype=np.int32),
                   memb={"合併": Wd["m5"] | Wd["m4"], "只500": Wd["m5"], "只400": Wd["m4"]})
    return _RW


def anchor_ok(p):
    W = _RW["Wd"]
    return W["valid"][max(p - 4, 0):p + 1].any(axis=0)


def period_ret(a, b):
    """a 收盤 → b 收盤（ffill）報酬；a 附近 5 根內要有有效 K 棒、(a, b] 不跨斷點，否則 NaN。"""
    W = _RW["Wd"]; cpb = _RW["cpb"]
    with np.errstate(invalid="ignore", divide="ignore"):
        r = W["CF"][b] / W["CF"][a] - 1
    ok = anchor_ok(a) & ((cpb[b] - cpb[a]) == 0) & np.isfinite(r)
    return np.where(ok, r, np.nan)


def rank_tables(scores, M_, ent=0.10, ext=0.20, excl=None):
    """scores：{e: 分數向量}；M_：(n,S) 成分旗標（取 e−1）；excl：{e: 排除旗標}。⇒ BUY {e: 前 ent 依分數遞減}、KEEP {e: 前 ext 集合}、ORD {e: 前 ext 依序}。"""
    BUY, KEEP, ORD = {}, {}, {}
    for e, sc in scores.items():
        ok = np.isfinite(sc) & M_[e - 1]
        if excl is not None and e in excl:
            ok &= ~excl[e]
        el = np.flatnonzero(ok)
        if not len(el):
            BUY[e], KEEP[e], ORD[e] = [], set(), []
            continue
        order = el[np.lexsort((el, -sc[el]))]
        k1 = int(np.ceil(ent * len(el))); k2 = int(np.ceil(ext * len(el)))
        BUY[e] = [int(x) for x in order[:k1]]; ORD[e] = [int(x) for x in order[:k2]]; KEEP[e] = set(ORD[e])
    return BUY, KEEP, ORD


def sector_conc(holds):
    W = _RW["Wd"]; A4 = _RW["A4"]; sec = _RW["sec"]; cal = _RW["cal"]
    nd, mx, miss, tot = [], [], 0, 0
    for t, js in holds.items():
        if not js:
            continue
        ed = int(np.datetime64(cal[t - 1], "D").astype(np.int64))
        ss = []
        for j in js:
            gs, _ = A4.sector_at(sec, str(W["tick"][j]), ed); tot += 1
            if gs:
                ss.append(gs)
            else:
                miss += 1
        if ss:
            c = Counter(ss); nd.append(len(c)); mx.append(max(c.values()) / len(js))
    return {"平均產業數": float(np.mean(nd)) if nd else np.nan, "最大產業占比平均": float(np.mean(mx)) if mx else np.nan,
            "產業缺值持股比例": miss / tot if tot else np.nan}


def win_ret(eq, cal, d0, d1):
    a = int(cal.searchsorted(pd.Timestamp(d0))); b = int(cal.searchsorted(pd.Timestamp(d1), side="right")) - 1
    return float(eq[b] / eq[a - 1] - 1)


def rank_main(KEEP, BUY, t0, t1, a, b, cost=COST, N=N_SLOTS, trades=True):
    R = rworld(); W = R["Wd"]
    tr = [] if trades else None
    res = book(W, sorted(KEEP), KEEP, BUY, N, t0, t1, cost=cost, trades_out=tr)
    bm = metrics(R["B"], a, b)
    s = book_summary(res, a, b, bm, trades=tr)
    return res, tr, s, bm


def _rand_worker(r):
    J = _JOB; R = _RW; W = R["Wd"]
    out = J["gen"](r)
    if len(out) == 2:
        res = book(W, sorted(out[0]), out[0], out[1], N_SLOTS, J["t0"], J["t1"])
    else:
        res = book(W, R["ms"], None, None, N_SLOTS, J["t0"], J["t1"], keep_fn=out[0], buy_fn=out[1], on_buy=out[2])
    m = metrics(res["eq"], J["a"], J["b"])
    yrs = (J["b"] - J["a"]) / 252
    return (r, m["年化"], m["回落"], float(res["buyd"][J["a"]:J["b"] + 1].sum() / res["eq"][J["a"]:J["b"] + 1].mean() / yrs))


def run_random(gen, t0, t1, a, b, nrep, procs):
    from multiprocessing import Pool
    rworld()
    _JOB.clear(); _JOB.update(gen=gen, t0=t0, t1=t1, a=a, b=b)
    with Pool(procs) as pool:
        out = pool.map(_rand_worker, range(nrep), chunksize=max(1, nrep // (procs * 8)))
    c = np.array([x[1] for x in out]); m = np.array([x[2] for x in out]); tv = np.array([x[3] for x in out])
    return c, m, tv


def rand_summary(c, m, tv, bm, real):
    return {"次數": int(len(c)), "年化中位": float(np.median(c)), "回落中位": float(np.median(m)), "每年換手中位": float(np.median(tv)),
            "p（隨機年化 ＞ ^SP500TR）": float(np.mean(c > bm["年化"])), "隨機年化 ≥ 主臂 的比例": float(np.mean(c >= real)),
            "逐次判語比例": {k: float(np.mean([label(x, y, bm["年化"], bm["回落"]) == k for x, y in zip(c, m)])) for k in ("合格", "另列", "不合格")}}


def event_layer(scores, M_, t_list, excl=None, top=0.10, z=1.959963984540054):
    """K9：每月（換股日 e）分數最高十分位等權次月報酬 − 母體等權次月報酬（母體 ＝ e−1 在該欄、有次月報酬、未排除）。
    次月報酬 ＝ e−1 收盤 → e 所在月最後一個交易日收盤（period_ret）。"""
    R = rworld(); ym = R["ym"]; last = R["last"]
    rows = []
    for e in t_list:
        sc = scores.get(e)
        if sc is None:
            continue
        b = last[int(ym[e])]
        if b > R["w1"]:
            continue
        r = period_ret(e - 1, b)
        uni = M_[e - 1] & np.isfinite(r)
        if excl is not None and e in excl:
            uni &= ~excl[e]
        el = np.flatnonzero(uni & np.isfinite(sc))
        if len(el) < 20:
            continue
        order = el[np.lexsort((el, -sc[el]))]; k = int(np.ceil(top * len(el)))
        mu = float(r[uni].mean())
        rows.append({"e": e, "top": float(r[order[:k]].mean()) - mu, "bot": float(r[order[-k:]].mean()) - mu, "n": len(el), "k": k})
    df = pd.DataFrame(rows)
    if not len(df):
        return {"月數": 0}, df
    s = month_series_ci(df["top"].to_numpy(), z)
    s["判語"] = ("測得出（＋）" if s["lo"] > 0 else ("測得出（−）" if s["hi"] < 0 else "測不出"))
    s["最低十分位"] = month_series_ci(df["bot"].to_numpy(), z)
    s["每月排名檔數中位"] = float(df["n"].median())
    s["第一個月"] = str(R["cal"][int(df["e"].iloc[0])].date())
    return s, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", default="all")
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=NSEED)
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    items = ["c8", "c7", "c3", "c4", "c5", "c6"] if a.item == "all" else a.item.split(",")
    for it in items:
        mod = __import__("backtest.researchUSC_%s" % it, fromlist=["run"])
        t0 = time.time()
        mod.run(a)
        log("[%s] 完成 %.0fs" % (it, time.time() - t0), "run.log")


if __name__ == "__main__":
    main()

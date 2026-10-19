# -*- coding: utf-8 -*-
"""USREG-C11L 股債金往前延伸 seq2（月頻定版）：50% SSO＋30% IEF＋20% 黃金，1990-01～2006-06（合成）。回測線，台北 2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC11L_m
    獨立查核：... -m backtest.researchUSC11L_m_check｜合成 fixture（不碰真實資料）：... -m backtest.researchUSC11L_m_check --fixture

登錄：信箱 登錄全文-USREG-C11L_股債金往前延伸_seq2_美股策略線（sha 5e82cecacf975d56，去 pw1 行整檔 sha256 前 16 碼；本檔無 pw1 行）。
      seq1（sha 6ebd33cbfbc8f510）⇒ 裁定 seq353 發號（美股 N_組合 ＋1，seq2 不另加）；seq361 §六 改月頻；seq381 §三 定版、回測即跑。
資料：資料庫 1017-0226（us-stock-data 070a4bcd7：fred_DGS7、worldbank_gold_monthly）；本檔讀快照 ~/usdata/4bdd82b（git archive 4bdd82b94，唯讀）。
⛔⛔ 私有資料：resultsUSC11L_m/ 只放彙總（年化、回落、比值、次數、相關係數、逐年差）；逐月序列、權益路徑一律只放 ~/us_work/c11l_m/（repo 外）。
⛔ 組合、窗、判準、先驗一字不動（seq2 只改資料頻率）。

══ 執行者補讀法（⭐ 台北 2026-10-20 寫死於看任何 C11L 數字之前；登錄沒寫清楚處）══
 M1 日曆 ＝ yahoo_GSPC 日期，截到 2026-09-30（與 C11 同）；月底 ＝ 日曆每月最後一個交易日。^SP500TR 收盤 ＝ adjclose；ETF 用 adjclose（含息、含分割）。
 M2 判定窗（月）＝ 1990-01～2006-06 共 198 個月報酬：窗止 2006-06-20 落在月中 ⇒ 取到該月月底（合成 SSO 照公式算到 06-30，仍全為合成）。
    ^SP500TR 與合成 SSO 沒有 1989 年資料 ⇒ 1990-01 由 1990-01-02 收盤起算（＝ 日頻窗首，A1 bench／synth 同樣以首日收盤為 1.0）；
    IEF 腿照 §七 公式用 1989-12 月底殖利率、黃金腿用 1989-12 月平均（兩腿有前月資料）。
 M3 SSO 腿 ＝ researchUSA1_data.synth（A1 seq3：2r − (DTB3_{t−1}＋0.25%)/252 − 0.89%/252，逐日）⇒ 月底值相除；⛔ 一行未改、只 import。
 M4 IEF 腿：y_d ＝ (DGS7＋DGS10)÷2÷100，只取兩者同日都有值的 FRED 日；月底 y ＝ 當月最後一個有值日；
    r_m ＝ y_{m−1}/12 − D_{m−1}Δy ＋ ½C_{m−1}Δy² − 0.15%/12；D、C ＝ 8.5 年、半年付息（17 期）、票面＝y_{m−1} 的平價債修正存續期間與凸性（解析式）。
 M5 黃金腿：worldbank_gold_monthly；r_m ＝ avg_m ÷ avg_{m−1} − 1 − 0.40%/12。
 M6 組合：窗首建倉（現金→三腿，換手 ½Σ|目標−現有|（含現金）× 0.05%，A1 engine 同式）；每年 12 月月底估值後歸位、成本扣在 1 月（＝ 再平衡月）；
    窗首那年不算再平衡（第一次在 1990-12 月底）。年化 ＝ 末值^(12 ÷ 月數) − 1；回落 ＝ 含 1.0 起點的月底路徑最大回落；
    判準 ＝ researchUSA1_data.label（年化 ＞ ^SP500TR 同窗嚴格 且 比值 ≥ 基準比值 ⇒ 合格；只前者 ⇒ 另列；否則不合格）。
 M7 100 萬最低剩 ＝ 100 × 路徑最小值；回本 ＝ 最大回落那段由高點到再創高點的月數 ÷ 12（段內沒回 ⇒ 往後在接續段找，仍沒回 ⇒ 未回本）。
 M8 2000～02 ＝ 2000-02 月底為 100 萬，2000-03～2002-10；1994 ＝ 1993-12 月底為 100 萬，1994-01～12：報 窗內最大回落、最低剩、窗末剩（跌幅）、回本月數。
    先驗「2000～02 回落比 ^SP500TR 淺」＝ 窗內最大回落 組合 ＞ 指數（較不負）；「1994 年組合為負」＝ 1994 窗末剩 ＜ 100 萬。
 M9 同曝險對照 ＝ 平均總股票曝險（月底 SSO 實際權重 × 2 的平均，判定窗 198 個月）÷ 2 放合成 SSO、其餘國庫券（月內 DTB3_{t−1}/252 逐日連乘）、每年歸位、同成本。
 M10 相關係數 ＝ 每曆年月報酬 Pearson：^SP500TR–合成 IEF、^SP500TR–黃金（Pink Sheet）、合成 IEF–黃金；另報全窗。
 M11 對帳（描述、⛔ 不調參）：IEF ＝ 合成月公式 vs 真實 IEF 月底（2002-08～2026-09，逐曆年連乘；首尾年為部分年，照算；整年版另報）；
     黃金 ＝ GLD 月底（2004-12～2025-12）vs Pink Sheet 月平均版（含 0.40% 費用）逐曆年；SSO（描述）＝ 合成 vs 真實 2006-07～2026-09。
     年差絕對值平均 ＞ 1 點 ⇒ 結果句加「合成誤差約 x 點」（IEF、黃金各自判）。
 M12 接續段（描述）：1990-01～2006-06 合成、2006-07 起真實 SSO／IEF／GLD 月底，連續每年歸位到 2026-09；
     C11 對照 ＝ 真實三腿月頻 2007-04～2026-09（C11 日頻窗 2007-04-10 起；以 2007-03 月底為起點）與 resultsUSC/late/C11_summary.json 並列。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSA1_data as A          # noqa: E402  synth／label／ratio／bench（只 import、不改）

DATA_COMMIT = "4bdd82b94df8b403e24ef075323a27cc2fd3df3b"
ROOT = os.environ.get("US_DATA_ROOT_C11LM", os.path.expanduser("~/usdata/4bdd82b"))
OUT = os.environ.get("C11LM_OUT", os.path.expanduser("~/tw-p17/backtest/resultsUSC11L_m"))
WORK = os.environ.get("C11LM_WORK", os.path.expanduser("~/us_work/c11l_m"))
C11_SUMMARY = os.path.expanduser("~/tw-p17/backtest/resultsUSC/late/C11_summary.json")
CAL_END = "2026-09-30"
COST = 0.0005
FEE_IEF = 0.0015
FEE_GOLD = 0.0040
W = np.array([0.5, 0.3, 0.2])
WIN = ("1990-01", "2006-06")
C11WIN = ("2007-04", "2026-09")
REAL0 = "2006-07"
CRISES = {"2000～02": ("2000-03", "2002-10"), "1994": ("1994-01", "1994-12")}
REG = {"seq2": "登錄全文-USREG-C11L_股債金往前延伸_seq2_美股策略線 sha 5e82cecacf975d56", "seq1": "sha 6ebd33cbfbc8f510",
       "裁定": "seq353（發號、N_組合 ＋1）、seq361 §六（改月頻）、seq381 §三（定版）"}
TAIL = "判定窗為月頻，最大回落比日頻淺；黃金為月平均價，波動被低估"
SYN = "1990～2006 為合成、非實際 ETF"
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


def p_(*a):
    return os.path.join(ROOT, "data", "macro", *a)


def assert_pinned():
    c = io.open(os.path.join(ROOT, ".commit"), encoding="utf-8").read().strip()
    if c != DATA_COMMIT and os.environ.get("C11LM_FIXTURE") != "1":
        raise RuntimeError(f"資料 commit {c} ≠ 寫死的 {DATA_COMMIT}")
    return c


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _jd(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def rnd(x, k=10):
    if isinstance(x, dict):
        return {a: rnd(b, k) for a, b in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(b, k) for b in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), k)
    return x


# ═════════════ 讀檔（照 researchUSC_late.yahoo／fred 讀法）═════════════
def yahoo(name):
    d = pd.read_csv(p_(f"yahoo_{name}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume", "adjclose"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def fred(name):
    d = pd.read_csv(p_(f"fred_{name}.csv"), dtype=str, keep_default_na=False)
    v = pd.to_numeric(d["value"].replace({"": None, ".": None}), errors="coerce")
    return pd.Series(v.to_numpy(float), index=d["date"].to_numpy(str))


def _on(s, cal):
    return np.array(s.reindex(cal).to_numpy(float), dtype=float, copy=True)


def mprev(m):
    y, k = int(m[:4]), int(m[5:7])
    return f"{y - 1}-12" if k == 1 else f"{y}-{k - 1:02d}"


def mrange(a, b):
    out = []; m = a
    while m <= b:
        out.append(m); y, k = int(m[:4]), int(m[5:7]); m = f"{y + 1}-01" if k == 12 else f"{y}-{k + 1:02d}"
    return out


def bond_dc(y, T=8.5, f=2):
    """平價債（票面 ＝ y、半年付息、到期 T 年）的修正存續期間、凸性（對年化殖利率 y，小數）。"""
    n = int(round(T * f)); k = np.arange(1, n + 1, dtype=float)
    cf = np.full(n, y / f); cf[-1] += 1.0
    v = 1.0 / (1.0 + y / f)
    P = float((cf * v ** k).sum())
    dP = float(-(cf * k / f * v ** (k + 1)).sum())
    d2P = float((cf * k * (k + 1) / f ** 2 * v ** (k + 2)).sum())
    return -dP / P, d2P / P


def load():
    c = assert_pinned()
    d = pd.read_csv(p_("yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"]
    cal = np.array(sorted(x for x in set(d) if x <= CAL_END)); n = len(cal)
    pos = {x: i for i, x in enumerate(cal)}
    ym = np.array([x[:7] for x in cal])
    me = {}
    for i in range(n):
        if i == n - 1 or ym[i] != ym[i + 1]:
            me[ym[i]] = i
    D = {"cal": cal, "pos": pos, "me": me, "commit": c, "audit": {}}
    tr = yahoo("SP500TR"); gs = yahoo("GSPC")
    c_tr = _on(tr["adjclose"], cal); c_gs = _on(gs["close"], cal)
    o_tr = _on(gs["open"], cal) * (c_tr / c_gs)
    D["TR"] = c_tr
    # DTB3（照 A1 D4）
    r = fred("DTB3"); r = r[r.index <= CAL_END]; lv = r.dropna()
    dt = pd.Series(lv.to_numpy(), index=lv.index).reindex(sorted(set(lv.index) | set(cal))).ffill().reindex(cal).to_numpy(float)
    g = np.zeros(n); g[1:] = dt[:-1] / 100.0 / A.ANN
    D["cash_g"] = g
    # 合成 SSO（M3）：A.synth 原式
    _, Lc = A.synth({"O": {"TR": o_tr}, "C": {"TR": c_tr}, "dtb3": dt}, "SSO", A.SPREAD)
    D["SSO_syn_d"] = Lc
    i_end = me[WIN[1]]
    D["audit"]["^SP500TR"] = {"首日": cal[int(np.flatnonzero(np.isfinite(c_tr))[0])], "判定窗內缺日": int((~np.isfinite(c_tr[:i_end + 1])).sum())}
    D["audit"]["合成SSO"] = {"判定窗內 NaN": int((~np.isfinite(Lc[:i_end + 1])).sum())}
    assert np.all(np.isfinite(Lc[:i_end + 1])), "合成 SSO 判定窗內有 NaN"
    D["audit"]["DTB3"] = {"日曆日無當日值（用前值）": int(sum(1 for x in cal if x not in set(lv.index)))}
    for k in ("SSO", "IEF", "GLD"):
        y = yahoo(k)
        cc = _on(y["adjclose"], cal); cc[~(cc > 0)] = np.nan
        D[k] = pd.Series(cc).ffill().to_numpy()
        f = int(np.flatnonzero(np.isfinite(cc))[0])
        D["audit"][k] = {"首日": cal[f], "首日後日曆內缺日（前值補）": int((~np.isfinite(cc[f:])).sum())}
    # 殖利率（M4）
    a7, a10 = fred("DGS7"), fred("DGS10")
    both = pd.concat([a7.rename("a"), a10.rename("b")], axis=1).dropna()
    both = both[both.index <= CAL_END]
    yd = (both["a"] + both["b"]) / 2.0 / 100.0
    ym_y = pd.Series(yd.index.str[:7], index=yd.index)
    ylast = yd.groupby(ym_y).last(); ydate = pd.Series(yd.index, index=yd.index).groupby(ym_y).last()
    D["y_m"] = ylast.to_dict(); D["y_date"] = ydate.to_dict(); D["y_d"] = yd
    # 月底有值日 ≠ 日曆月底 的月數（描述）
    nd = sum(1 for m, i in me.items() if m in D["y_date"] and D["y_date"][m] != cal[i] and "1989-12" <= m <= CAL_END[:7])
    D["audit"]["殖利率"] = {"DGS7 與 DGS10 同日有值的日數": int(len(yd)), "月底有值日不等於日曆月底的月數（1989-12 起）": nd}
    gd = pd.read_csv(p_("worldbank_gold_monthly.csv"), dtype={"month": str})
    D["gold_m"] = dict(zip(gd["month"], pd.to_numeric(gd["gold_usd_per_troy_oz"], errors="coerce")))
    D["audit"]["黃金月平均"] = {"首月": gd["month"].iloc[0], "末月": gd["month"].iloc[-1]}
    D["sha16"] = {k: sha16(p_(k)) for k in ("yahoo_GSPC.csv", "yahoo_SP500TR.csv", "yahoo_SSO.csv", "yahoo_IEF.csv", "yahoo_GLD.csv", "fred_DTB3.csv",
                                              "fred_DGS7.csv", "fred_DGS10.csv", "worldbank_gold_monthly.csv")}
    return D


# ═════════════ 月報酬（M2～M5）═════════════
def base_idx(D, m):
    """月 m 報酬的起點日位置：前月月底；1990-01（無前月資料）⇒ 日曆首日。"""
    pm = mprev(m)
    return D["me"][pm] if pm in D["me"] else 0


def m_ret_daily(D, arr, m):
    a, b = base_idx(D, m), D["me"][m]
    return arr[b] / arr[a] - 1.0


def m_cash(D, m):
    a, b = base_idx(D, m), D["me"][m]
    return float(np.prod(1.0 + D["cash_g"][a + 1:b + 1]) - 1.0)


def m_ief_syn(D, m):
    y0, y1 = D["y_m"][mprev(m)], D["y_m"][m]
    dur, cvx = bond_dc(y0); dy = y1 - y0
    return y0 / 12.0 - dur * dy + 0.5 * cvx * dy * dy - FEE_IEF / 12.0


def m_gold_pk(D, m):
    return D["gold_m"][m] / D["gold_m"][mprev(m)] - 1.0 - FEE_GOLD / 12.0


def legs(D, months, kind):
    """kind：syn（合成三腿）｜real（SSO、IEF、GLD 月底）｜splice（REAL0 前合成、之後真實）。⇒ (n,3)。"""
    R = np.empty((len(months), 3))
    for j, m in enumerate(months):
        real = kind == "real" or (kind == "splice" and m >= REAL0)
        if real:
            R[j] = [m_ret_daily(D, D["SSO"], m), m_ret_daily(D, D["IEF"], m), m_ret_daily(D, D["GLD"], m)]
        else:
            R[j] = [m_ret_daily(D, D["SSO_syn_d"], m), m_ief_syn(D, m), m_gold_pk(D, m)]
    assert np.all(np.isfinite(R)), kind
    return R


# ═════════════ 組合（M6）═════════════
def port(R, w, months, cashR=None, cost=COST):
    """R：(n,k) 月報酬；w：目標權重（現金 ＝ 1 − 和）；12 月月底估值後歸位、成本扣在次月。⇒ eq (n,)、月底實際權重 (n,k)、換手次數。"""
    n, k = R.shape; w = np.asarray(w, float)
    cashR = np.zeros(n) if cashR is None else cashR
    V = 1.0; tr = 0.5 * (w.sum() + abs((1 - w.sum()) - 1.0)); V2 = V - tr * cost
    hold = w * V2; cash = (1 - w.sum()) * V2
    eq = np.empty(n); aw = np.empty((n, k)); nreb = 0
    for j in range(n):
        hold = hold * (1.0 + R[j]); cash = cash * (1.0 + cashR[j])
        eq[j] = hold.sum() + cash; aw[j] = hold / eq[j]
        if months[j][5:7] == "12" and j < n - 1:
            V = eq[j]; tgt = w * V; tc = (1 - w.sum()) * V
            tr = 0.5 * (np.abs(tgt - hold).sum() + abs(tc - cash)); V2 = V - tr * cost
            hold = w * V2; cash = (1 - w.sum()) * V2; nreb += 1
    return eq, aw, nreb


def stats(eq, months, bench_eq=None):
    n = len(eq); p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p); dd = (p - pk) / pk
    c = float(eq[-1] ** (12.0 / n) - 1.0); m = float(dd.min())
    it = int(np.argmin(dd)); ip = int(np.argmax(p[:it + 1]))
    back = np.flatnonzero(p[it:] >= p[ip])
    lab = lambda i: mprev(months[0]) + "（起點）" if i == 0 else months[i - 1]
    s = {"起": months[0], "迄": months[-1], "月數": n, "年化": c, "回落": m, "比值": A.ratio(c, m), "100萬最低剩（萬）": float(p.min() * 100),
         "期末（萬）": float(eq[-1] * 100), "高點月": lab(ip), "谷底月": lab(it),
         "回本年數（高點→再創高）": (it + int(back[0]) - ip) / 12.0 if len(back) else "段內未回本", "_ip": ip, "_it": it}
    if bench_eq is not None:
        b = stats(bench_eq, months)
        s.update({"基準年化": b["年化"], "基準回落": b["回落"], "基準比值": b["比值"], "標籤": A.label(c, m, b["年化"], b["回落"])})
    return s


def recover_after(chain, ip, it):
    """判定窗內未回本 ⇒ 往後在接續段（chain，月 cm）找；ip、it 為判定窗內路徑位置（含起點）。"""
    p = np.r_[1.0, chain]
    k = np.flatnonzero(p[it:] >= p[ip])
    return (it + int(k[0]) - ip) / 12.0 if len(k) else "未回本（至 2026-09）"


def crisis(eq, months, a, b):
    i0 = months.index(a); i1 = months.index(b)
    base = eq[i0 - 1] if i0 > 0 else 1.0
    seg = np.r_[1.0, eq[i0:i1 + 1] / base]; pk = np.maximum.accumulate(seg)
    it = int(np.argmin(seg))
    full = np.r_[1.0, eq[i0:] / base]                      # 起點 → 接續段末
    k = np.flatnonzero(full[it:] >= 1.0 - 1e-12)
    return {"窗": f"{a}～{b}（{mprev(a)} 月底 ＝ 100 萬）", "窗內最大回落": float(((seg - pk) / pk).min()), "窗內最低剩（萬）": float(seg.min() * 100),
            "窗末剩（萬）": float(seg[-1] * 100), "窗末報酬": float(seg[-1] - 1.0), "谷底月": months[i0 + it - 1] if it > 0 else "起點",
            "回本月數（從窗首）": (it + int(k[0])) if len(k) else "未回本（至 2026-09）"}


def yearly(r, months):
    out = {}
    for x, m in zip(r, months):
        y = m[:4]; v = out.setdefault(y, [1.0, 0]); v[0] *= 1.0 + x; v[1] += 1
    return {y: (v[0] - 1.0, v[1]) for y, v in out.items()}


def recon(a, b, months, name_a, name_b):
    ya, yb = yearly(a, months), yearly(b, months)
    rows = [{"件": f"{name_a} − {name_b}", "年": y, "月數": ya[y][1], "年差（點）": (ya[y][0] - yb[y][0]) * 100} for y in ya]
    df = pd.DataFrame(rows)
    full = df[df["月數"] == 12]
    ra, rb = np.asarray(a), np.asarray(b)
    return df, {"月份": f"{months[0]}～{months[-1]}", "年數": len(df), "年差絕對值平均（點，含首尾部分年）": float(df["年差（點）"].abs().mean()),
                "年差絕對值平均（點，只整年）": float(full["年差（點）"].abs().mean()), "年差平均（點，含部分年）": float(df["年差（點）"].mean()),
                "最大年差絕對值（點）": float(df["年差（點）"].abs().max()), "月報酬相關": float(np.corrcoef(ra, rb)[0, 1]),
                f"{name_a} 月報酬標準差×√12": float(ra.std(ddof=1) * np.sqrt(12)), f"{name_b} 月報酬標準差×√12": float(rb.std(ddof=1) * np.sqrt(12)),
                "整段年化差（點）": float((np.prod(1 + ra) ** (12 / len(ra)) - np.prod(1 + rb) ** (12 / len(rb))) * 100)}


def ief_daily_syn(D, a, b):
    """§三 日公式（描述，用來看月公式 vs 日公式）：FRED 有值日上逐日，對到日曆月底。"""
    yd = D["y_d"]; idx = list(yd.index); v = yd.to_numpy()
    lv = np.ones(len(v))
    for t in range(1, len(v)):
        dur, cvx = bond_dc(v[t - 1]); dy = v[t] - v[t - 1]
        lv[t] = lv[t - 1] * (1.0 + v[t - 1] / 252.0 - dur * dy + 0.5 * cvx * dy * dy - FEE_IEF / 252.0)
    s = pd.Series(lv, index=idx)
    last = s.groupby(pd.Series(s.index.str[:7], index=s.index)).last()
    months = mrange(a, b)
    return np.array([last[m] / last[mprev(m)] - 1.0 for m in months]), months


def main():
    global LOGF
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(WORK, "run.log"); open(LOGF, "w").close()
    D = load(); cal = D["cal"]
    MJ = mrange(*WIN); n = len(MJ)
    log(f"[C11L-m] 資料 {D['commit'][:9]}｜判定窗 {MJ[0]}～{MJ[-1]}（{n} 個月）")
    # 判定格
    RJ = legs(D, MJ, "syn")
    eqJ, awJ, nrebJ = port(RJ, W, MJ)
    trJ = np.array([m_ret_daily(D, D["TR"], m) for m in MJ]); trJ_eq = np.cumprod(1 + trJ)
    sJ = stats(eqJ, MJ, trJ_eq); bJ = stats(trJ_eq, MJ)
    # 接續段（M12）
    MS = mrange(WIN[0], CAL_END[:7]); RS = legs(D, MS, "splice"); eqS, awS, _ = port(RS, W, MS)
    assert np.max(np.abs(eqS[:n] - eqJ)) == 0.0, "接續段前段應與判定格逐位元相同"
    trS = np.array([m_ret_daily(D, D["TR"], m) for m in MS]); trS_eq = np.cumprod(1 + trS)
    if sJ["回本年數（高點→再創高）"] == "段內未回本":
        sJ["回本年數（高點→再創高）"] = recover_after(eqS, sJ["_ip"], sJ["_it"])
        sJ["回本註"] = "判定窗內未回本 ⇒ 往後在接續段（2006-07 起真實三腿）找"
    if bJ["回本年數（高點→再創高）"] == "段內未回本":
        bJ["回本年數（高點→再創高）"] = recover_after(trS_eq, bJ["_ip"], bJ["_it"])
    expo = float(np.mean(awJ[:, 0] * 2))
    log(f"[C11L-m] 判定格 年化 {sJ['年化']:.4f} 回落 {sJ['回落']:.4f} 比值 {sJ['比值']:.4f} 標籤 {sJ['標籤']}｜^SP500TR {bJ['年化']:.4f}／{bJ['回落']:.4f}｜曝險 {expo:.3f}")
    # 危機（M8）：用接續段路徑（判定窗內逐位元相同；回本可往後找）
    cr = {}
    for k, (a, b) in CRISES.items():
        cr[k] = {"組合": crisis(eqS, MS, a, b), "^SP500TR": crisis(trS_eq, MS, a, b)}
    # 同曝險（M9）
    cashJ = np.array([m_cash(D, m) for m in MJ])
    eqE, awE, _ = port(RJ[:, :1], [expo / 2], MJ, cashR=cashJ)
    sE = stats(eqE, MJ, trJ_eq)
    eqE_S, _, _ = port(RS[:, :1], [expo / 2], MS, cashR=np.array([m_cash(D, m) for m in MS]))
    for k, (a, b) in CRISES.items():
        cr[k]["同曝險 SSO＋國庫券"] = crisis(eqE_S, MS, a, b)
    eqSSO = np.cumprod(1 + RJ[:, 0]); sSSO = stats(eqSSO, MJ, trJ_eq)
    for k, (a, b) in CRISES.items():
        cr[k]["一直抱合成 SSO"] = crisis(np.cumprod(1 + RS[:, 0]), MS, a, b)
    # 相關係數（M10）
    rows = []
    for y in sorted(set(m[:4] for m in MJ)):
        ix = [j for j, m in enumerate(MJ) if m[:4] == y]
        s, b_, g = trJ[ix], RJ[ix, 1], RJ[ix, 2]
        rows.append({"年": y, "月數": len(ix), "股–債": np.corrcoef(s, b_)[0, 1], "股–金": np.corrcoef(s, g)[0, 1], "債–金": np.corrcoef(b_, g)[0, 1]})
    corr = pd.DataFrame(rows)
    corr_all = {"股–債": float(np.corrcoef(trJ, RJ[:, 1])[0, 1]), "股–金": float(np.corrcoef(trJ, RJ[:, 2])[0, 1]), "債–金": float(np.corrcoef(RJ[:, 1], RJ[:, 2])[0, 1])}
    Sg = np.cov(RJ.T); sd = np.sqrt(np.diag(Sg)); neff = float((W @ sd) ** 2 / (W @ Sg @ W))
    # 對帳（M11）
    MI = mrange("2002-08", CAL_END[:7])
    ief_syn = np.array([m_ief_syn(D, m) for m in MI]); ief_real = np.array([m_ret_daily(D, D["IEF"], m) for m in MI])
    rcI, rsI = recon(ief_syn, ief_real, MI, "合成IEF（月公式）", "真實IEF")
    ief_dsyn, _ = ief_daily_syn(D, MI[0], MI[-1])
    _, rsId = recon(ief_dsyn, ief_real, MI, "合成IEF（§三日公式，描述）", "真實IEF")
    MG = mrange("2004-12", "2025-12")
    g_pk = np.array([m_gold_pk(D, m) for m in MG]); g_real = np.array([m_ret_daily(D, D["GLD"], m) for m in MG])
    rcG, rsG = recon(g_pk, g_real, MG, "黃金PinkSheet月平均版", "GLD月底")
    MSS = mrange(REAL0, CAL_END[:7])
    s_syn = np.array([m_ret_daily(D, D["SSO_syn_d"], m) for m in MSS]); s_real = np.array([m_ret_daily(D, D["SSO"], m) for m in MSS])
    rcS, rsS = recon(s_syn, s_real, MSS, "合成SSO", "真實SSO")
    recon_df = pd.concat([rcI, rcG, rcS], ignore_index=True)
    # 頻率影響（描述）：日頻 vs 月頻
    i0d, i1d = D["pos"]["1990-01-02"], D["pos"]["2006-06-20"]
    tr_d = A.bench(D["TR"], i0d, i1d); sso_d = A.bench(D["SSO_syn_d"], i0d, i1d)
    freq = {"^SP500TR 日頻 1990-01-02～2006-06-20": {"年化": tr_d[0], "回落": tr_d[1]}, "^SP500TR 月頻 判定窗": {"年化": bJ["年化"], "回落": bJ["回落"]},
            "合成 SSO 日頻 1990-01-02～2006-06-20": {"年化": sso_d[0], "回落": sso_d[1]}, "合成 SSO 月頻 判定窗": {"年化": sSSO["年化"], "回落": sSSO["回落"]},
            "黃金 月報酬年化波動：PinkSheet 月平均 vs GLD 月底（2004-12～2025-12）": [rsG["黃金PinkSheet月平均版 月報酬標準差×√12"], rsG["GLD月底 月報酬標準差×√12"]]}
    # C11 並列（M12）
    MC = mrange(*C11WIN); RC = legs(D, MC, "real"); eqC, awC, _ = port(RC, W, MC)
    trC = np.cumprod(1 + np.array([m_ret_daily(D, D["TR"], m) for m in MC]))
    sC = stats(eqC, MC, trC)
    MR = mrange(REAL0, CAL_END[:7]); RR = legs(D, MR, "real"); eqR, _, _ = port(RR, W, MR)
    sR = stats(eqR, MR, np.cumprod(1 + np.array([m_ret_daily(D, D["TR"], m) for m in MR])))
    c11 = json.load(open(C11_SUMMARY, encoding="utf-8"))
    c11d = {"窗": c11["窗"], "年化": c11["判定"]["年化"], "回落": c11["判定"]["回落"], "比值": c11["判定"]["比值"], "標籤": c11["標籤"],
            "基準年化": c11["基準"]["年化"], "基準回落": c11["基準"]["回落"], "基準比值": c11["基準"]["比值"]}
    sSplice = stats(eqS, MS, trS_eq)
    sSplice2000 = crisis(eqS, MS, "2000-03", "2002-10")
    # 先驗（⛔ 寫下不改）
    pri = {"合格（約五成五）": sJ["標籤"] == "合格",
           "2000～02 回落比 ^SP500TR 淺（約八成）": cr["2000～02"]["組合"]["窗內最大回落"] > cr["2000～02"]["^SP500TR"]["窗內最大回落"],
           "1994 年組合為負（約六成）": cr["1994"]["組合"]["窗末報酬"] < 0,
           "合成 IEF 對帳年差 ≤ 1 點（約七成）": rsI["年差絕對值平均（點，含首尾部分年）"] <= 1.0}
    # 結果句（查表）
    adds = []
    if rsI["年差絕對值平均（點，含首尾部分年）"] > 1.0:
        adds.append(f"合成誤差約 {rsI['年差絕對值平均（點，含首尾部分年）']:.1f} 點（IEF）")
    if rsG["年差絕對值平均（點，含首尾部分年）"] > 1.0:
        adds.append(f"合成誤差約 {rsG['年差絕對值平均（點，含首尾部分年）']:.1f} 點（黃金）")
    pc = lambda x: f"{x * 100:.1f}%"
    if sJ["標籤"] == "合格":
        sent = (f"一半正2、三成中期公債、兩成黃金：1990～2006（合成）年化 {pc(sJ['年化'])}（^SP500TR {pc(bJ['年化'])}）、回落 {pc(sJ['回落'])}；"
                f"加上 2006 年後的真實段，兩段都合格")
    else:
        sent = (f"一半正2、三成中期公債、兩成黃金：1990～2006（合成）{sJ['標籤']}——年化 {pc(sJ['年化'])}（^SP500TR {pc(bJ['年化'])}）、"
                f"回落 {pc(sJ['回落'])}（^SP500TR {pc(bJ['回落'])}）、比值 {sJ['比值']:.3f}（^SP500TR {bJ['比值']:.3f}）")
    sent += "｜" + SYN + "｜" + TAIL + ("｜" + "；".join(adds) if adds else "")
    for s in (sJ, bJ, sE, sSSO, sC, sR, sSplice):
        s.pop("_ip", None); s.pop("_it", None)
    S = {"件": "USREG-C11L 股債金往前延伸 seq2（月頻定版）", "登錄": REG, "N": "美股 N_組合 ＋1（seq353 已計；seq2 不另加）",
         "資料": {"us-stock-data commit": D["commit"], "快照": "~/usdata/4bdd82b（git archive，唯讀）", "檔案 sha256 前 16": D["sha16"], "截止": CAL_END},
         "判定窗": f"{MJ[0]}～{MJ[-1]}（{n} 個月；1990-01 股票腿由 1990-01-02 收盤起）", "判定格": "50% 合成 SSO＋30% 合成 IEF＋20% 黃金（Pink Sheet 月平均），每年 1 月歸位，成本 0.05%",
         "判定": sJ, "基準 ^SP500TR（月頻）": bJ, "標籤": sJ["標籤"], "結果句": sent, "先驗對照": pri,
         "必報": {"100萬最低剩（萬）": sJ["100萬最低剩（萬）"], "回本年數": sJ["回本年數（高點→再創高）"], "危機": cr,
                 "股債金相關（全窗月報酬）": corr_all, "同曝險對照": {"平均總股票曝險": expo, "SSO 權重": expo / 2, "結果": sE},
                 "一直抱合成 SSO（描述）": sSSO, "再平衡次數": nrebJ, "等效獨立部位數（月報酬，描述）": neff},
         "對帳": {"IEF（判準用）": rsI, "IEF 日公式（描述）": rsId, "黃金": rsG, "SSO（描述）": rsS},
         "頻率影響（描述）": freq,
         "C11 並列（描述）": {"C11 日頻（resultsUSC/late/C11_summary.json）": c11d, "真實三腿月頻 同窗 2007-04～2026-09": sC,
                          "真實三腿月頻 2006-07～2026-09": sR},
         "接續段 1990-01～2026-09（描述）": {"整段": sSplice, "2000-03～2002-10": sSplice2000},
         "資料帳": D["audit"], "讀法": "見 researchUSC11L_m.py 檔頭 M1～M12（台北 2026-10-20 寫死於看數字之前）",
         "秒": round(time.time() - t0)}
    json.dump(rnd(S), open(os.path.join(OUT, "C11L_m_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_jd)
    corr.to_csv(os.path.join(OUT, "C11L_m_corr_by_year.csv"), index=False, encoding="utf-8", float_format="%.6f")
    recon_df.to_csv(os.path.join(OUT, "C11L_m_recon_by_year.csv"), index=False, encoding="utf-8", float_format="%.6f")
    # 逐月序列只放 repo 外（給 check 用）
    np.savez(os.path.join(WORK, "series.npz"), MJ=np.array(MJ), RJ=RJ, eqJ=eqJ, trJ=trJ, MS=np.array(MS), RS=RS, eqS=eqS, MC=np.array(MC), eqC=eqC, RC=RC, trC=trC,
             MI=np.array(MI), ief_syn=ief_syn, MG=np.array(MG), g_pk=g_pk, eqE=eqE, cashJ=cashJ)
    log(f"[C11L-m] 先驗 {pri}")
    log(f"[C11L-m] 結果句：{sent}")
    log(f"[C11L-m] 完成 {S['秒']}s")
    return S


if __name__ == "__main__":
    main()

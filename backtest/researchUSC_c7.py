# -*- coding: utf-8 -*-
"""USREG-C7（← 草稿 B7，sha eec986526b9f41a5）進場方式：一筆錢買美股——一次買（L）、定期定額（D）、等跌再買（B）、均線擇時（T）。
裁定 seq321 §三：N（美股帳）12（L、B、T 對 D × ^SP500TR、QQQ、SSO、QLD）；判定照登錄。

═══ C7 補讀法（C7- 標；⭐ 寫死於 2026-10-10 23:26（台北），寫死前 ⛔ 沒看任何 C7 數字）═══
 C7-1 資料 ＝ USREG-A1 同一份（researchUSA1_data.load_market，~/usdata/60d2f99，截到 2026-09-30）：^SP500TR（開 ＝ ^GSPC 開 × 同日 TR÷GSPC，A1 D2）、
      QQQ 還原（1999-03-10 起）、SSO／QLD 還原（2006-06-21 起）；現金 ＝ DTB3（t 日現金報酬 ＝ DTB3_{t−1}÷100÷252，A1 D4）。
      SSO ＝ 合成（A1 seq3 公式：2×^SP500TR 日報酬 − (DTB3＋0.25%)/252 − 0.89%/252，開盤 A1 D5 式）接真實 SSO（真實首日起按收盤比例接，報酬不變）；
      QLD ＝ 只用真實（登錄只列合成 SSO）。⛔ 不用 ^NDX 價格指數代 QQQ。
 C7-2 起點：每個月第一個交易日（滾動，⛔ 不挑起點）；該標的要：起點開盤有效、起點前一日 200 日均線可算（T 法要用）、量測日 ≤ 2026-09-30。四法同一組起點。
 C7-3 四法（拿到 1.0 元，買進成本 0.05%／筆，未投入放國庫券、按日計息）：
      L ＝ 起點開盤全部買。
      D ＝ 起點月起連續 12 個月、每月第一個交易日開盤買「剩餘現金 ÷ 剩餘期數」（第 12 筆買完全部現金，含利息）。
      B ＝ 自起點收盤起，收盤 ＜ 0.9 ×「起點以來最高收盤」⇒ 次一交易日開盤全部買；到第 12 個月最後一個交易日都沒觸發 ⇒ 第 13 個月第一個交易日開盤全部買。
          描述：門檻 5%、20%；上限 24 個月（門檻 10%）。
      T ＝ 起點前一日收盤 ＞ 200 日線 ⇒ 起點開盤全買；否則等收盤 ＞ 200 日線 ⇒ 次一交易日開盤全買；上限同 B（12 個月）。200 日線 ＝ 有效 K 棒收盤 200 根平均。
      買進後一律抱到量測日（⛔ 不比出場）。
 C7-4 量測：期末 ＝ 起點月 ＋ h−1 個月的最後一個交易日收盤（持有＋現金）；h ＝ 36（主）；12、60、120（描述）。
      主量 x ＝ 某法期末財富 ÷ D 期末財富 − 1。
 C7-5 判定（每標的 × 每法對 D，一格）：中位 ＞ 0 且「贏 D 的比例」的 Bonferroni（0.05／12，z ≈ 2.87）年分群 CI 下緣 ＞ 50% ⇒「比定期定額好」；
      中位 ＜ 0 且 CI 上緣 ＜ 50% ⇒「比定期定額差」；其餘 ⇒「分不出」。年分群 ＝ 依起點年份（群集穩健 SE：sqrt(Σ_年 (勝_年 − p̂ n_年)²) ÷ n）。
 C7-6 必並列：最差 10% 起點（x 的 p10、x 最差十分之一的平均）、3 年內最大回落（各法中位、最差）、
      「最後悔」起點 2000-03、2007-10、2021-12（各法 x；標的沒有該起點 ⇒ 照寫無）。
 C7-7 必報：各法 3 年平均閒置現金比例、平均實際買進價 ÷ 起點開盤價 − 1（金額加權）、B「12 個月內真的等到跌 10%」比例、T「起點就在線上」比例與上限觸發比例；
      合成 SSO 與真實 SSO 重疊期（2006-06-21～2026-09-30）年化對帳；有效樣本 ≈ 起點年數（相鄰起點高度重疊），結果句寫明。
 C7-8 條件出場（seq308）：不適用——登錄只比進場、量測日固定；照寫。
 C7-9 先驗對錯（登錄 §六）：^SP500TR、QQQ：L 好（約八成）、B 差（約八成）、T 分不出或差（約六成五）；
      SSO、QLD：L 贏 D 的比例低於 ^SP500TR 版（約六成五）；「最差 10% 起點 L 遠比 D 慘」＝ 該正2 的 x_L p10 低於 ^SP500TR 的 x_L p10（約九成）。
"""
from __future__ import annotations

import time
from statistics import NormalDist

import numpy as np
import pandas as pd

from backtest import researchUSC as K
from backtest import researchUSA1_data as A

READ_TS = "2026-10-10 23:26（台北）"
COSTB = 0.0005
TGT = ("TR", "QQQ", "SSO", "QLD")
TNAME = {"TR": "^SP500TR", "QQQ": "QQQ", "SSO": "SSO", "QLD": "QLD"}
METH = ("L", "B", "T")
HS = (12, 36, 60, 120)
ZB = NormalDist().inv_cdf(1 - 0.025 / 12)
REGRET = ("2000-03", "2007-10", "2021-12")


def setup():
    A.assert_pinned()
    M = A.load_market()
    so, sc = A.synth(M, "SSO", A.SPREAD)                 # A1 seq3 公式（A1 FEE 0.89%）
    r0 = int(np.flatnonzero(np.isfinite(M["C"]["SSO"]))[0])
    f = sc[r0] / M["C"]["SSO"][r0]
    n = len(sc); idx = np.arange(n)
    M["O"]["SSO_SP"] = np.where(idx < r0, so, M["O"]["SSO"] * f)
    M["C"]["SSO_SP"] = np.where(idx < r0, sc, M["C"]["SSO"] * f)
    M["SYN_SSO"] = (so, sc); M["sso_r0"] = r0
    return M


def series(M, k):
    key = {"TR": "TR", "QQQ": "QQQ", "SSO": "SSO_SP", "QLD": "QLD"}[k]
    o = M["O"][key].astype(float); c = M["C"][key].astype(float)
    ok = np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0)
    cf = pd.Series(np.where(ok, c, np.nan)).ffill().to_numpy()
    ma = np.full(len(c), np.nan)
    b = np.flatnonzero(ok)
    if len(b) >= 200:
        cs = np.cumsum(c[b]); m_ = np.full(len(b), np.nan); m_[199:] = (cs[199:] - np.r_[0, cs[:-200]]) / 200
        ma[b] = m_
    ma = pd.Series(ma).ffill().to_numpy()
    return o, cf, ok, ma


def month_tables(cal):
    d = pd.to_datetime(pd.Series(cal))
    ym = (d.dt.year * 12 + d.dt.month - 1).to_numpy()
    first = {}; last = {}
    for i, k in enumerate(ym):
        first.setdefault(int(k), i); last[int(k)] = i
    return ym, first, last


def wealth(o, cf, CI, s, buys, end):
    """buys：[(日, 比例 ＝ 用當時現金的幾成)]（依日序）⇒ 期末財富、路徑（s～end）、閒置現金比例路徑、買進加權價。"""
    sh = 0.0; cash_at = 1.0; tc = s - 1                  # cash_at ＝ 在 tc 收盤時的現金
    V = np.empty(end - s + 1); cashp = np.empty(end - s + 1)
    bi = 0; spent = 0.0; px_w = 0.0
    for t in range(s, end + 1):
        while bi < len(buys) and buys[bi][0] == t:
            c_open = cash_at * CI[t - 1] / CI[tc]
            amt = c_open * buys[bi][1]
            sh += amt * (1 - COSTB) / o[t]; spent += amt; px_w += amt * o[t]
            cash_at = c_open - amt; tc = t - 1
            bi += 1
        cash_t = cash_at * CI[t] / CI[tc]
        V[t - s] = sh * cf[t] + cash_t; cashp[t - s] = cash_t / V[t - s] if V[t - s] > 0 else np.nan
    return V, cashp, (px_w / spent if spent > 0 else np.nan)


def plans(o, cf, ok, ma, s, ym, first, last, n, thr=0.10, cap=12):
    k = int(ym[s])
    out = {"L": [(s, 1.0)]}
    out["D"] = [(first[k + i], 1.0 / (12 - i)) for i in range(12) if (k + i) in first]
    if len(out["D"]) < 12:
        return None
    dd = []
    for t, fr in out["D"]:
        while t < n and not ok[t]:
            t += 1
        dd.append((t, fr))
    out["D"] = dd
    dl = last.get(k + cap - 1); fb = first.get(k + cap)
    if dl is None or fb is None:
        return None
    # B
    hi = -np.inf; bday = None; trig = False
    for t in range(s, dl + 1):
        if ok[t]:
            hi = max(hi, cf[t])
            if cf[t] < (1 - thr) * hi and t + 1 < n:
                bday = t + 1; trig = True; break
    if bday is None:
        bday = fb
    while bday < n and not ok[bday]:
        bday += 1
    out["B"] = [(bday, 1.0)]
    # T
    tday = None; imm = False
    if np.isfinite(ma[s - 1]) and cf[s - 1] > ma[s - 1]:
        tday = s; imm = True
    else:
        for t in range(s, dl + 1):
            if ok[t] and np.isfinite(ma[t]) and cf[t] > ma[t] and t + 1 < n:
                tday = t + 1; break
    capT = tday is None
    if tday is None:
        tday = fb
    while tday < n and not ok[tday]:
        tday += 1
    out["T"] = [(tday, 1.0)]
    out["_meta"] = {"B觸發": trig, "T起點在線上": imm, "T上限": capT}
    return out


def run(a):
    T0 = time.time()
    M = setup(); cal = M["cal"]; n = len(cal)
    CI = np.cumprod(1.0 + M["cash_g"])
    ym, first, last = month_tables(cal)
    endpos = M["pos"]["2026-09-30"]
    R = {}; DESC = {}; META = {}
    for k in TGT:
        o, cf, ok, ma = series(M, k)
        rows = []
        for mk in sorted(first):
            s = first[mk]
            if s < 1 or not ok[s] or not np.isfinite(ma[s - 1]):
                continue
            for hh in HS:
                e = last.get(mk + hh - 1)
                if e is None or e > endpos or (mk + hh) not in first:
                    continue
                rec = {"起點": str(cal[s])[:7], "年": int(str(cal[s])[:4]), "h": hh}
                for var, thr, cap in (("主", 0.10, 12), ("B5", 0.05, 12), ("B20", 0.20, 12), ("B10cap24", 0.10, 24)):
                    if var != "主" and hh != 36:
                        continue
                    pl = plans(o, cf, ok, ma, s, ym, first, last, n, thr, cap)
                    if pl is None:
                        rec = None; break
                    if var == "主":
                        for m_ in ("L", "D", "B", "T"):
                            if pl[m_][-1][0] > e:
                                rec = None; break
                            V, cp, pw = wealth(o, cf, CI, s, pl[m_], e)
                            path = np.r_[1.0, V]; pk = np.maximum.accumulate(path)
                            rec[f"W_{m_}"] = float(V[-1]); rec[f"MDD_{m_}"] = float(((path - pk) / pk).min())
                            rec[f"閒置_{m_}"] = float(np.nanmean(cp)); rec[f"買價_{m_}"] = pw / o[s] - 1
                        if rec is None:
                            break
                        rec.update({k2: v2 for k2, v2 in pl["_meta"].items()})
                    else:
                        if pl["B"][-1][0] > e:
                            rec[f"W_{var}"] = np.nan; continue
                        V, _, _ = wealth(o, cf, CI, s, pl["B"], e)
                        rec[f"W_{var}"] = float(V[-1])
                if rec is not None:
                    rows.append(rec)
        df = pd.DataFrame(rows)
        R[k] = df
    K.log("[C7] 起點表 %.0fs" % (time.time() - T0), "c7.log")
    # ── 判定與必報 ──
    OUTJ = {}; CELLS = []
    for k in TGT:
        df = R[k]; d36 = df[df["h"] == 36]
        info = {"起點數": int(len(d36)), "起點年數（≈ 有效樣本）": int(d36["年"].nunique()), "起點範圍": [d36["起點"].min(), d36["起點"].max()] if len(d36) else None}
        for m_ in METH:
            x = d36[f"W_{m_}"] / d36["W_D"] - 1
            win = (x > 0).astype(float)
            cw = K.clus_mean(win, d36["年"], ZB)
            med = float(x.median())
            lab = ("比定期定額好" if (med > 0 and cw["lo"] > 0.5) else ("比定期定額差" if (med < 0 and cw["hi"] < 0.5) else "分不出"))
            xs = np.sort(x.to_numpy()); nw = max(1, int(np.ceil(len(xs) * 0.1)))
            cell = {"標的": TNAME[k], "法": m_, "起點數": int(len(x)), "中位": med, "平均": float(x.mean()), "贏D比例": cw["平均"], "贏D_CI": [cw["lo"], cw["hi"]],
                    "年群數": cw["群數"], "判語": lab, "x_p10": float(np.percentile(xs, 10)), "最差十分之一平均": float(xs[:nw].mean()),
                    "MDD中位": float(d36[f"MDD_{m_}"].median()), "MDD最差": float(d36[f"MDD_{m_}"].min()),
                    "閒置現金平均": float(d36[f"閒置_{m_}"].mean()), "買價相對起點": float(d36[f"買價_{m_}"].mean()),
                    "最後悔": {r_: (float(x[d36["起點"] == r_].iloc[0]) if (d36["起點"] == r_).any() else "無") for r_ in REGRET}}
            for hh in (12, 60, 120):
                dh = df[df["h"] == hh]
                if len(dh):
                    xh = dh[f"W_{m_}"] / dh["W_D"] - 1
                    cell[f"描述_{hh}月"] = {"起點數": int(len(dh)), "中位": float(xh.median()), "贏D比例": float((xh > 0).mean())}
            if m_ == "B":
                for var in ("B5", "B20", "B10cap24"):
                    xv = d36[f"W_{var}"] / d36["W_D"] - 1
                    cell[f"描述_{var}"] = {"中位": float(xv.median()), "贏D比例": float((xv > 0).mean()), "起點數": int(xv.notna().sum())}
            CELLS.append(cell)
        info.update({"D_MDD中位": float(d36["MDD_D"].median()), "D_閒置現金平均": float(d36["閒置_D"].mean()), "D_買價相對起點": float(d36["買價_D"].mean()),
                     "B_12月內等到跌10%比例": float(d36["B觸發"].mean()), "T_起點就在線上比例": float(d36["T起點在線上"].mean()),
                     "T_上限觸發比例": float(d36["T上限"].mean()),
                     "最後悔_D期末（萬）": {r_: (float(d36.loc[d36["起點"] == r_, "W_D"].iloc[0] * 100) if (d36["起點"] == r_).any() else "無") for r_ in REGRET},
                     "最後悔_L期末（萬）": {r_: (float(d36.loc[d36["起點"] == r_, "W_L"].iloc[0] * 100) if (d36["起點"] == r_).any() else "無") for r_ in REGRET}})
        OUTJ[TNAME[k]] = info
    C = pd.DataFrame(CELLS)
    # 合成對帳
    r0 = M["sso_r0"]; so, sc = M["SYN_SSO"]
    cr, _ = A.bench(M["C"]["SSO"], r0, endpos); cs, _ = A.bench(sc, r0, endpos)
    rec = {"重疊期": [cal[r0], cal[endpos]], "真實SSO年化": cr, "合成SSO年化": cs, "合成−真實（點）": (cs - cr) * 100}
    # 先驗
    g = lambda t_, m_: C[(C["標的"] == t_) & (C["法"] == m_)].iloc[0]
    pri = []
    for t_ in ("^SP500TR", "QQQ"):
        pri.append({"先驗": f"{t_}：L 比 D 好（約八成）", "結果": g(t_, "L")["判語"], "對": g(t_, "L")["判語"] == "比定期定額好"})
        pri.append({"先驗": f"{t_}：B 比 D 差（約八成）", "結果": g(t_, "B")["判語"], "對": g(t_, "B")["判語"] == "比定期定額差"})
        pri.append({"先驗": f"{t_}：T 分不出或較差（約六成五）", "結果": g(t_, "T")["判語"], "對": g(t_, "T")["判語"] in ("分不出", "比定期定額差")})
    for t_ in ("SSO", "QLD"):
        pri.append({"先驗": f"{t_}：L 贏 D 比例低於 ^SP500TR 版（約六成五）", "結果": f"{g(t_, 'L')['贏D比例']:.0%} vs {g('^SP500TR', 'L')['贏D比例']:.0%}",
                    "對": bool(g(t_, "L")["贏D比例"] < g("^SP500TR", "L")["贏D比例"])})
        pri.append({"先驗": f"{t_}：最差 10% 起點 L 遠比 D 慘（x_L p10 低於 ^SP500TR，約九成）", "結果": f"{g(t_, 'L')['x_p10']:+.1%} vs {g('^SP500TR', 'L')['x_p10']:+.1%}",
                    "對": bool(g(t_, "L")["x_p10"] < g("^SP500TR", "L")["x_p10"])})
    # 結果句
    sents = []
    for t_ in ("^SP500TR", "QQQ", "SSO", "QLD"):
        L_, B_, T_ = g(t_, "L"), g(t_, "B"), g(t_, "T")
        sents.append(f"一筆錢買 {t_}（{OUTJ[t_]['起點數']} 個起點、約 {OUTJ[t_]['起點年數（≈ 有效樣本）']} 年獨立）：一次買在 {L_['贏D比例']:.0%} 的起點贏定期定額、"
                     f"3 年後中位多 {L_['中位']:+.1%}（{L_['判語']}）；等跌 10% 再買在 {1 - B_['贏D比例']:.0%} 的起點輸定期定額（{B_['判語']}）；"
                     f"均線擇時 {T_['判語']}（中位 {T_['中位']:+.1%}）")
    lev_dir = []
    for t_ in ("SSO", "QLD"):
        if (g(t_, "L")["判語"] != g("^SP500TR", "L")["判語"]):
            lev_dir.append(f"{t_} 的一次買判語（{g(t_, 'L')['判語']}）與大盤（{g('^SP500TR', 'L')['判語']}）不同")
    nlab = {lab: int((C["判語"] == lab).sum()) for lab in ("比定期定額好", "比定期定額差", "分不出")}
    card = {"件": "C7", "名稱": "進場方式（一次買／定期定額／等跌再買／均線擇時）", "登錄": f"USREG-B7 seq1 sha {K.REG['C7'][1]}（→ C7）", "裁定": K.RULING,
            "N": 12, "標籤": f"12 格：比定期定額好 {nlab['比定期定額好']}、差 {nlab['比定期定額差']}、分不出 {nlab['分不出']}", "三欄": "不適用（ETF／指數層）",
            "條件出場必報": "不適用：登錄只比進場、買進後抱到量測日（3 年）",
            "結果句": "；".join(sents) + "。" + ("⚠ 槓桿 ETF：" + "；".join(lev_dir) + "。" if lev_dir else "槓桿 ETF 判語方向與大盤相同。")
                      + " ⚠ 起點逐月滾動、相鄰起點高度重疊 ⇒ 有效樣本約等於年數；SSO 2006-06 前為合成、非實際 ETF。",
            "偏離": ["QLD 只用真實（2006-06 起；登錄只列合成 SSO）", "B／T 上限到期日讀成「第 12 個月最後一個交易日都沒觸發 ⇒ 第 13 個月第一個交易日開盤買」",
                     "四法共用起點：需 200 日線可算（T 法）⇒ 每個標的前 200 根 K 棒內的起點不用"],
            "補讀法": [f"C7-1～C7-9（researchUSC_c7.py docstring，{READ_TS} 寫死）", f"K1～K11（researchUSC.py，{K.READ_TS}）"],
            "相對門檻（seq321 §五）": "B 的 10% 是相對自身起點以來最高價；照登錄"}
    out = {"卡片": card, "逐格": CELLS, "標的資訊": OUTJ, "Bonferroni z": ZB, "合成對帳": rec, "先驗": pri, "資料": A.data_commit(), "算於": K.now_tpe(),
           "秒": round(time.time() - T0)}
    C.drop(columns=[c for c in C.columns if c.startswith("描述") or c == "最後悔"]).to_csv(K.os.path.join(K.OUT, "C7_cells.csv"), index=False, encoding="utf-8", float_format="%.6g")
    for k in TGT:
        R[k].to_pickle(K.os.path.join(K.WORK, f"c7_starts_{k}.pkl"))
    K.jdump(out, "C7.json")
    K.log("[C7] %s" % card["標籤"], "c7.log")
    return out

# -*- coding: utf-8 -*-
"""USREG-A1-3 驅動因素（移植台股 PREREGY seq4，sha ed234d8ebe997bce；單筆層事件研究；N_前段 ＋8；Bonferroni 0.05／8）。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA1 a3

登錄 USREG-A1 seq1 件三：門檻、20 日取第一筆、756 日滾動 5／95 百分位、量法、出口、假訊號臂 ⇒ 逐字沿用台股 PREREGY seq4 §十 讀法定案
  （C＝a 序列自己的觀測日、W＝a 756 含 t、Q＝a 線性內插、D＝a 從保留那筆起隔 ≥ 20、E＝a 事件日在窗內、H＝a s→s＋20 開盤、S＝a 區段由起算日從 w0 切、
   G＝a 全時間軸去重、X1＝並存〈< 10 直接出口①、< 30 出口①〉、P5b＝a #5 也去重）；⭐ 直接 import researchY 的 tail_flags／dedupe／build_native／run_axis／next_tw（同一件事只一份實作）。
  標的 SPY（還原開盤）；因素：#5 聯準會升／降（fomc_rate_changes.csv 的 statement_date ⇒ 次一交易日開盤）｜#6 美元 DTWEXBGS 20 日變化（%）｜
  #7 DGS10 20 日變化（bp）｜#8 VIXCLS 水準；各高端／低端（#5 升／降）⇒ 8 格。主窗 2007-04-02～2026-09-30；1993～2007 描述。

══ 執行者補讀法（⭐ 2026-10-07 台北 02:35 寫死於看任何 A1 數字之前）══
 Y1 #7、#8：FRED 美東 d 日值在 d 收盤後才有 ⇒ 起算日 ＝ d 之後第一個 NYSE 交易日開盤（台股 #7 #8「下一個交易日開盤」同義）。
 Y2 #6 DTWEXBGS：⚠ 聯準會 H.10 每週一（美東下午）公布前一週的每日值 ⇒ d 日值最早在「d 所在那週之後的週一」收盤後可知；
    主讀法 起算日 ＝ 該週一之後第一個 NYSE 交易日開盤（⛔ 不前視）；「d 的次一交易日」版只描述（會前視最多約一週）。
 Y3 #5：事件日 ＝ statement_date 之後第一個 NYSE 交易日（＝起算日；台股 body_events_5 同式，聲明 14:00 公布 ⇒ 次一交易日開盤）；
    升／降 ＝ increase_bp／decrease_bp 非空、非「...」、非「0」（台股同式）。
 Y4 報酬 R20(s) ＝ SPY 還原開盤 o[s＋20] ÷ o[s] − 1；對照 ＝ 主窗每一個 s ∈ [w0, w1−20] 的 R20 平均；事件需 s ≥ w0 且 s＋20 ≤ w1（窗尾不收，照報筆數）。
 Y5 早年描述段 1993-01-29（SPY 首日）～2007-03-30：同法、自己的對照（同段全日平均）、只報差與 95% CI（⛔ 不判）；DTWEXBGS 2006 起 ⇒ #6 早年段無資料。
 Y6 假訊號臂：同格同事件數 n、主窗 eligible 起算日不放回抽 n 天，種子 default_rng(20260925＋r)，r＝0…999 ⇒ 真平均在 1,000 個假平均的百分位（描述）。
"""
from __future__ import annotations

import json
import os
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

from backtest import researchUSA1_data as A
from backtest import researchY as Y

HOLD, HOLD_DESC = 20, 60
N_CELLS = 8
ALPHA = 0.05
Z_BONF = NormalDist().inv_cdf(1 - ALPHA / N_CELLS / 2)
Z95 = 1.96
SEED_FAKE, REPS_FAKE = 20260925, 1000
CELLS8 = [("#5", "調升"), ("#5", "調降"), ("#6", "低端"), ("#6", "高端"), ("#7", "低端"), ("#7", "高端"), ("#8", "低端"), ("#8", "高端")]
NAME = {"#5": "聯準會目標利率（FOMC 聲明）", "#6": "美元指數 DTWEXBGS 20 日變化", "#7": "美債 10 年 DGS10 20 日變化", "#8": "VIX 水準"}
EARLY0 = "1993-01-29"


def h10_start(dates, cal):
    """Y2：d ⇒ d 所在週之後的週一（d 週一 ⇒ +7 天）⇒ 之後第一個交易日（嚴格）。"""
    d = pd.to_datetime(pd.Series(dates))
    mon = d + pd.to_timedelta(7 - d.dt.weekday, unit="D")
    return Y.next_tw(cal, mon.dt.strftime("%Y-%m-%d").to_numpy(str), strict=True)


def events_continuous(M):
    cal = M["cal"]
    Y.cal_arr_g = cal
    rows = []
    for key, nm in (("#6", "DTWEXBGS"), ("#7", "DGS10"), ("#8", "VIXCLS")):
        raw = A.fred(nm).dropna()
        raw = raw[raw.index <= A.CAL_END]
        dN, vN, evN, spN = Y.build_native(key, raw, cal)
        variants = [("主", spN)] if key != "#6" else [("主", h10_start(dN, cal)), ("次一日（描述，前視）", spN)]
        for tag, sp in variants:
            r_, fj = Y.run_axis(key, "a", "-", dN, vN, np.arange(len(dN)), evN, sp)
            for r in r_:
                if r["W"] == "a" and r["Q"] == "a" and r["D"] == "a":
                    rows.append({"因素": key, "端": r["端"], "版": tag, "事件日": r["事件日"], "起算位置": int(r["起算位置"]), "第一個可判日": fj["Wa"]})
    return pd.DataFrame(rows)


def events_fed(M):
    cal = M["cal"]
    fr = pd.read_csv(A.p_("macro", "fomc_rate_changes.csv"), dtype=str, keep_default_na=False)
    fs = pd.read_csv(A.p_("macro", "fomc_statements.csv"), dtype=str, keep_default_na=False)

    def moved(col):
        v = fr[col].str.strip()
        return ~v.isin(["", "...", "0"])
    up, dn = moved("increase_bp").to_numpy(), moved("decrease_bp").to_numpy()
    assert not (up & dn).any()
    fr["方向"] = np.where(up, "調升", np.where(dn, "調降", ""))
    sd = fr["statement_date"].to_numpy(str)
    sp = Y.next_tw(cal, sd, strict=True)
    audit = {"列": int(len(fr)), "statement_date ⊆ fomc_statements": bool(set(sd) <= set(fs["statement_date"])), "方向空白": int((fr["方向"] == "").sum()),
             "升": int(up.sum()), "降": int(dn.sum()), "sha256": A.sha256f(A.p_("macro", "fomc_rate_changes.csv"))}
    rows = []
    for end in ("調升", "調降"):
        m = (fr["方向"] == end).to_numpy() & (sp >= 0)
        ss = sp[m]; sdd = sd[m]
        k = Y.dedupe(ss, "a")
        for i in k:
            rows.append({"因素": "#5", "端": end, "版": "主", "事件日": str(cal[ss[i]]), "起算位置": int(ss[i]), "聲明日": sdd[i], "第一個可判日": None})
        audit[f"{end} 去重前／後"] = [int(m.sum()), int(len(k))]
    return pd.DataFrame(rows), audit


def cl_se(x, groups):
    n = len(x); d = x - x.mean()
    s = pd.Series(d).groupby(np.asarray(groups)).sum().to_numpy()
    return float(np.sqrt((s ** 2).sum()) / n), int(len(s))


def run_a3(M, log):
    t0 = time.time()
    cal = M["cal"]; pos = M["pos"]
    w0, w1 = pos[A.EXP[0]], pos[A.CONF[1]]
    e0, e1 = pos[EARLY0], pos[A.EARLY_END]
    o = M["O"]["SPY"]; n = len(cal)

    def Rh(h):
        R = np.full(n, np.nan); R[:n - h] = o[h:] / o[:-h] - 1.0
        return R
    R20, R60 = Rh(HOLD), Rh(HOLD_DESC)
    elig = np.arange(w0, w1 - HOLD + 1); elig = elig[np.isfinite(R20[elig])]
    base20 = float(R20[elig].mean())
    el60 = np.arange(w0, w1 - HOLD_DESC + 1); el60 = el60[np.isfinite(R60[el60])]; base60 = float(R60[el60].mean())
    eel = np.arange(e0, e1 - HOLD + 1); eel = eel[np.isfinite(R20[eel])]; ebase = float(R20[eel].mean())
    evc = events_continuous(M)
    ev5, a5 = events_fed(M)
    ev = pd.concat([evc, ev5], ignore_index=True)
    first_judg = evc.groupby("因素")["第一個可判日"].first().to_dict()
    cells = []; priv = []
    for key, end in CELLS8:
        for ver in (["主"] + (["次一日（描述，前視）"] if key == "#6" else [])):
            g = ev[(ev["因素"] == key) & (ev["端"] == end) & (ev["版"] == ver)]
            gm = g[(g["事件日"] >= A.EXP[0]) & (g["事件日"] <= A.CONF[1])]
            s_all = gm["起算位置"].to_numpy(int)
            ok = (s_all >= w0) & (s_all + HOLD <= w1)
            okh = ok & np.isfinite(R20[np.clip(s_all, 0, n - 1)])
            s = s_all[okh]
            nn = int(len(s)); segs = len(set(((s - w0) // HOLD).tolist())); neff = min(nn, segs)
            r = {"因素": key, "名稱": NAME[key], "端": end, "版": ver, "判定格": ver == "主", "窗內事件": int(len(gm)), "窗尾無20日報酬（不收）": int((~ok).sum()),
                 "n": nn, "區段數": segs, "n_eff": neff, "第一個可判日": first_judg.get(key) if key != "#5" else "（離散事件）",
                 "每年事件": nn / ((w1 - w0 + 1) / A.ANN)}
            if nn < 10 or neff < 10:
                r.update({"出口": "出口①", "結果": "—", "候選": "都不是", "結果句": f"出口①：事件 {nn}、n_eff {neff}（< 10）⇒ 樣本不足以分辨；⛔ 報酬未算"})
            elif neff < 30:
                r.update({"出口": "出口①", "結果": "—", "候選": "都不是", "結果句": f"出口①：n_eff＝{neff}（< 30）⇒ 樣本不足以分辨；只報筆數，⛔ 報酬未算"})
            else:
                x = R20[s]; D_ = float(x.mean() - base20)
                se, nm = cl_se(x, np.array([cal[i][:7] for i in s]))
                lo_b, hi_b = D_ - Z_BONF * se, D_ + Z_BONF * se
                ex = "出口②" if neff < 100 else "出口③"
                res = "結果①" if lo_b <= 0 <= hi_b else ("結果②" if D_ > 0 else "結果③")
                cand = {"結果①": "都不是", "結果②": "加碼候選", "結果③": "減碼候選"}[res] if ver == "主" else "（描述）"
                fake = np.empty(REPS_FAKE)
                for rr in range(REPS_FAKE):
                    fake[rr] = R20[np.random.default_rng(SEED_FAKE + rr).choice(elig, nn, replace=False)].mean()
                s60 = s_all[(s_all >= w0) & (s_all + HOLD_DESC <= w1)]; s60 = s60[np.isfinite(R60[s60])]
                x60 = R60[s60]; se60, _ = cl_se(x60, (s60 - w0) // HOLD_DESC) if len(s60) > 1 else (np.nan, 0)
                sent = (f"{ex}、結果①：測不出（Bonferroni CI 含 0；⛔ 不是「沒效」）" if res == "結果①" else f"{ex}、{res}：測得出（{'＋' if D_ > 0 else '−'}）⇒ {cand}")
                if res == "結果①" and not (D_ - Z95 * se <= 0 <= D_ + Z95 * se):
                    sent += "；⚠ 95% CI 不含 0、但 Bonferroni（0.05／8）含 0 ⇒ ⛔ 不算候選、⛔ 不單獨引用"
                r.update({"事件平均R20": float(x.mean()), "對照": base20, "D": D_, "月分群SE": se, "月數": nm, "Bonf下": lo_b, "Bonf上": hi_b,
                          "95下": D_ - Z95 * se, "95上": D_ + Z95 * se, "R20＞對照比例": float((x > base20).mean()), "最差R20": float(x.min()),
                          "假訊號百分位": float((fake <= x.mean()).mean() * 100), "出口": ex, "結果": res, "候選": cand, "結果句": sent,
                          "描述60日_n": int(len(s60)), "描述60日_D": float(x60.mean() - base60) if len(s60) else np.nan,
                          "描述60日_95下": float(x60.mean() - base60 - Z95 * se60) if len(s60) > 1 else np.nan,
                          "描述60日_95上": float(x60.mean() - base60 + Z95 * se60) if len(s60) > 1 else np.nan})
            # 早年描述
            ge = g[(g["事件日"] >= EARLY0) & (g["事件日"] <= A.EARLY_END)]
            se_ = ge["起算位置"].to_numpy(int); se_ = se_[(se_ >= e0) & (se_ + HOLD <= e1)]; se_ = se_[np.isfinite(R20[se_])]
            r["早年_n"] = int(len(se_))
            if len(se_) >= 10:
                xe = R20[se_]; ses, _ = cl_se(xe, np.array([cal[i][:7] for i in se_]))
                r.update({"早年_D": float(xe.mean() - ebase), "早年_95下": float(xe.mean() - ebase - Z95 * ses), "早年_95上": float(xe.mean() - ebase + Z95 * ses)})
            for i in s:
                priv.append({"因素": key, "端": end, "版": ver, "起算日": cal[i], "R20": float(R20[i])})
            cells.append(r)
            log(f"  [A1-3 {key} {end} {ver}] n {nn}｜n_eff {neff}｜{r['出口']}｜{r['結果']}｜{r['候選']}")
    C = pd.DataFrame(cells)
    os.makedirs(A.OUT, exist_ok=True); os.makedirs(A.WORK, exist_ok=True)
    C.to_csv(os.path.join(A.OUT, "A3_cells.csv"), index=False, encoding="utf-8")
    pp = os.path.join(A.WORK, "a3_events.csv"); pd.DataFrame(priv).to_csv(pp, index=False)
    pe = os.path.join(A.WORK, "a3_events_all.csv"); ev.to_csv(pe, index=False)
    main = C[C["判定格"]]
    S = {"件": "USREG-A1-3 驅動因素", "登錄": "USREG-A1 seq1 件三（移植 PREREGY seq4 sha ed234d8ebe997bce）", "N": "N_前段 ＋8（美股帳）", "Bonferroni": {"α每格": ALPHA / N_CELLS, "z": Z_BONF},
         "主窗": [cal[w0], cal[w1]], "早年描述": [EARLY0, A.EARLY_END], "對照": {"主窗R20": base20, "主窗R60": base60, "早年R20": ebase, "主窗起算日數": int(len(elig))},
         "#5資料": a5, "候選": {"加碼候選": [f"{a} {b}" for a, b in main.loc[main["候選"] == "加碼候選", ["因素", "端"]].itertuples(index=False)],
                              "減碼候選": [f"{a} {b}" for a, b in main.loc[main["候選"] == "減碼候選", ["因素", "端"]].itertuples(index=False)]},
         "出口計數": main["出口"].value_counts().to_dict(), "結果計數": main["結果"].value_counts().to_dict(),
         "第一個可判日": first_judg, "私有檔sha（repo外 ~/us_work/usa1/）": {os.path.basename(p): A.sha256f(p) for p in (pp, pe)}, "秒": round(time.time() - t0)}
    json.dump(S, open(os.path.join(A.OUT, "A3_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[A1-3] 候選 {S['候選']}｜{S['秒']}s")
    return S, ev

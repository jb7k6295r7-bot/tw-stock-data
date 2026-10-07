# -*- coding: utf-8 -*-
"""USREG-A4-10 飆股回推比對【季財報特徵部分】——只做探索段挑特徵（裁定 seq319 Q16：挑定後就停、交裁定，⛔ 不開驗證段 2024～2026-09）。

台股原登錄：飆股回推比對 seq7（sha 15a22c6b6c2c36d0）§二（財報特徵）、§十（seq5 改寫）、§十一（seq6：2021～、g 網格 250 格）；
台股回測讀法：researchSurge6 U1～U4、researchSurge5 S1～S12（①②與挑選規則）；裁定 seq311／seq318（飆股＝美股母體 seq6 網格、取格中位，⛔ 不搬台股門檻）。
═══ 執行者補讀法（寫死於 2026-10-07 11:54（台北）；寫死前 ⛔ 沒算任何飆股標籤或提升倍數）═══
 S1 列 ＝ 觀察日 t × 股；母體 ＝ t 當天在 S&P 500 或 S&P 400 且有有效 K 棒（P2）；探索段 t ∈ 2021-01-04～2023-12-29；⛔ 不讀 t ≥ 2024-01 的列（驗證段不開）。
 S2 飆股網格（seq6）：H ∈ {10, 20, …, 250}（25）× g ∈ {50, 100, 150, 200, 250, 300, 400, 500, 700, 1000%}（10）＝ 250 格；
    起漲日 t：(t, t＋H] 內最高 ffill 還原收盤 ≥ t 收盤 ×（1＋g）（「至少漲 g」，1000% ＝ ≥ 10 倍）；
    定義域：(t, t＋H] 內無轉接層斷點、且 t＋H ≤ 該股最後一根有效 K 棒與 2026-09-30（右截斷）；不在定義域的列不進該格（分母、事件都不進）。
    事件鏈：同一檔同一格事件後 H 個交易日內不再算新事件（被跳過的日子仍在分母、標籤 0；台股 S5）；鏈自 2021-01-04 起算（U4）；
    鏈只在母體列上走（不在指數的日子不是列、不算事件也不開鏈；執行者補：美股母體有進出指數，台股沒有這個問題）。
 S3 特徵（t 當天可得：季財報可用日 av ≤ t；G9 分段鍵）：
    二元：F_hi8 創 8 季新高｜F_r1 營收轉折（最新季年增 ＞ 0 且前一季年增 ≤ 0；月版「近 3 月 vs 前 3 月」⇒ 季版）｜F_niturn 季淨利由負轉正（EPS 轉正的代理）｜F_opm 營益率比去年同季升
    五等分（每日橫斷面、平均名次分箱，同值同箱）：F_yoy 季營收年增｜F_qoq 季營收季增｜F_streak 連續年增季數｜F_dist8 距 8 季最高｜F_roe ROE（TTM）
    原門檻版只描述（⛔ 不參與挑選）：R2 季年增 ≥ 50%／≥ 100%；毛利率比上季升 ⇒ 拿掉（B1 沒有毛利，特徵不全）。
 S4 ① 提升倍數 ＝ 有特徵者飆股比例 ÷ 同格「該特徵有值」全體飆股比例；CI ＝ 有特徵者比例的曆月群集 CR0 ÷ 全體比例；② 涵蓋率 ＝ 該格飆股（特徵有值者）中有此特徵的比例。
 S5 挑選（seq6 §十一之二）：250 格中 ≥ 125 格「① 95% 下緣 ＞ 1 且 ② ≥ 5%」⇒ 進驗證段（⛔ 本件不跑驗證段，交裁定）；
    「取格中位」⇒ 每個特徵級距另報 250 格的 ① 與 ② 中位數（給使用者的第一個數）；該格事件 ＜ 30 ⇒ 標「樣本少」（只標，不影響挑選）。
 S6 ③ 可交易曲線、妖股、結束特徵：本步不做（seq319 Q16 只准探索段挑特徵）；N ＝ 驗證段實際驗的特徵數（待裁定）。
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

from backtest import researchUSA4 as C
from backtest import researchUSA4_items as IT

HS = tuple(range(10, 251, 10))
GS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
NC = len(HS) * len(GS)
BIN = ("F_hi8", "F_r1", "F_niturn", "F_opm")
QNT = ("F_yoy", "F_qoq", "F_streak", "F_dist8", "F_roe")
DESC = ("R2_50", "R2_100")
_G: dict = {}


def _init(d):
    _G.update(d)


def stock_job(j):
    X = _G["X"]; Wd = X["Wd"]; cal = X["cal"]; F = X["F"]
    cd = cal.values.astype("datetime64[D]").astype(np.int64)
    t_lo, t_hi, w1 = _G["t_lo"], _G["t_hi"], X["w1"]
    CF = Wd["CF"][:, j]; valid = Wd["valid"][:, j]; mem = Wd["mem"][:, j]; pb = Wd["pb"][:, j]
    last = int(Wd["last"][j]); tk = Wd["tick"][j]
    days = np.flatnonzero(mem[t_lo:t_hi + 1] & valid[t_lo:t_hi + 1]) + t_lo
    if not len(days):
        return None
    # 定義域 hdef[t] ＝ 下一個斷點前一天與最後有效 K 棒、窗尾的最小值 − t
    nb = np.flatnonzero(pb)
    hdef = np.zeros(len(days), np.int16)
    for i, t in enumerate(days):
        k = np.searchsorted(nb, t + 1)
        lim = min(last, w1)
        if k < len(nb):
            lim = min(lim, nb[k] - 1)
        hdef[i] = max(0, min(lim - t, 300))
    # 事件鏈（S2）：只在母體列上走；斷點使該列不在定義域 ⇒ 不算事件、不開鏈
    ev = {}
    lim_all = min(last, w1)
    for H in HS:
        fmax = pd.Series(CF).rolling(H, min_periods=H).max().shift(-H).to_numpy()
        fm = fmax[days] / CF[days]
        fm[days + H > lim_all] = np.nan
        for g in GS:
            hit = np.isfinite(fm) & (fm >= 1 + g - 1e-12) & (hdef >= H)
            nxt = -1; out = []
            for i in np.flatnonzero(hit):
                t = days[i]
                if t <= nxt:
                    continue
                out.append(i); nxt = t + H
            ev[(H, g)] = np.array(out, np.int32)
    # 特徵
    feats = np.full((len(days), len(BIN) + len(QNT) + len(DESC)), np.nan)
    for i, t in enumerate(days):
        k = C.key_at(F["SEG"], tk, cal[t])
        if k is None:
            continue
        ed = int(cd[t])
        y0 = C.yoy_at(F, "revenue", k, t, ed)
        y1 = C.yoy_at(F, "revenue", k, t, ed, back=1) if np.isfinite(y0) else np.nan
        q8 = C.q_last(F, "revenue", k, t, 8, edays=ed)
        hi8 = (float(q8[1][-1] > q8[1][:-1].max())) if q8 is not None else np.nan
        q2 = C.q_last(F, "revenue", k, t, 2, edays=ed)
        qoq = (q2[1][1] / q2[1][0] - 1) if (q2 is not None and q2[1][0] > 0) else np.nan
        ex = C.rev_extra(F, k, t, ed)
        qn = C.q_last(F, "net_income", k, t, 2, edays=ed)
        nit = float(qn[1][1] > 0 and qn[1][0] <= 0) if qn is not None else np.nan
        q4 = C.q_last(F, "net_income", k, t, 4, edays=ed)
        qe = C.q_last(F, "equity", k, t, 2, edays=ed)
        roe = (q4[1].sum() / qe[1].mean()) if (q4 is not None and qe is not None and qe[1].mean() > 0) else np.nan
        qo = C.q_last(F, "operating_income", k, t, 5, edays=ed); qr = C.q_last(F, "revenue", k, t, 5, edays=ed)
        opm = (float(qo[1][-1] / qr[1][-1] > qo[1][0] / qr[1][0])) if (qo is not None and qr is not None and qr[1][0] > 0 and qr[1][-1] > 0 and qo[0][-1] == qr[0][-1]) else np.nan
        r1 = float(y0 > 0 and y1 <= 0) if (np.isfinite(y0) and np.isfinite(y1)) else np.nan
        feats[i] = [hi8, r1, nit, opm, y0, qoq, ex["rev_streak"], ex["rev_dist8"], roe,
                    float(y0 >= 0.5) if np.isfinite(y0) else np.nan, float(y0 >= 1.0) if np.isfinite(y0) else np.nan]
    return {"j": j, "days": days, "hdef": hdef, "ev": ev, "feats": feats}


def qbin(v, day):
    """每日橫斷面五等分（平均名次分箱：⌊5×(名次−0.5)÷n⌋＋1，同值同箱）。"""
    out = np.zeros(len(v), np.int8)
    df = pd.DataFrame({"v": v, "d": day})
    ok = np.isfinite(v)
    d = df[ok]
    r = d.groupby("d")["v"].rank(method="average")
    n = d.groupby("d")["v"].transform("count")
    out[np.flatnonzero(ok)] = (np.floor(5 * (r - 0.5) / n) + 1).clip(1, 5).astype(np.int8).to_numpy()
    return out


def run(a):
    t0 = time.time()
    X = IT.context(bool(a.lim))
    cal = X["cal"]
    t_lo = int(cal.searchsorted(pd.Timestamp("2021-01-04"))); t_hi = int(cal.searchsorted(pd.Timestamp("2023-12-31"))) - 1
    assert str(cal[t_hi].date()) == "2023-12-29", cal[t_hi]
    S = X["Wd"]["C"].shape[1]
    with Pool(a.procs, initializer=_init, initargs=({"X": X, "t_lo": t_lo, "t_hi": t_hi},)) as pool:
        res = [r for r in pool.imap(stock_job, range(S), chunksize=8) if r is not None]
    IT.log("A4-10 逐檔完成 %d 檔 %.0fs" % (len(res), time.time() - t0))
    off = np.cumsum([0] + [len(r["days"]) for r in res])
    N = int(off[-1])
    day = np.concatenate([r["days"] for r in res]); hdef = np.concatenate([r["hdef"] for r in res])
    FE = np.concatenate([r["feats"] for r in res])
    mon = np.array([(cal[t].year * 12 + cal[t].month) for t in day]); mon = mon - mon.min()
    cols = list(BIN) + list(QNT) + list(DESC)
    code = {}
    for i, c in enumerate(cols):
        v = FE[:, i]
        if c in QNT:
            code[c] = qbin(v, day)                         # 0 ＝ 缺，1～5
        else:
            code[c] = np.where(np.isfinite(v), np.where(v > 0, 2, 1), 0).astype(np.int8)   # 0 缺、1 否、2 是
    levels = [(c, 2) for c in BIN] + [(c, q) for c in QNT for q in range(1, 6)] + [(c, 2) for c in DESC]
    out = {lv: {"lift": [], "lo": [], "cov": [], "pass": [], "n_ev": [], "prev": []} for lv in levels}
    cells = []
    nm = int(mon.max()) + 1
    for H in HS:
        dom = hdef >= H
        for g in GS:
            y = np.zeros(N, bool)
            for r, o in zip(res, off[:-1]):
                e = r["ev"][(H, g)]
                if len(e):
                    y[o + e] = True
            y &= dom
            cells.append({"H": H, "g": g, "事件": int(y.sum()), "定義域列": int(dom.sum()), "樣本少": bool(y.sum() < 30)})
            for c, lvv in levels:
                cc = code[c]
                dm = dom & (cc > 0)
                n0 = dm.sum(); y0 = (y & dm).sum()
                p0 = y0 / n0 if n0 else np.nan
                f = dm & (cc == lvv)
                nf = f.sum(); yf = (y & f).sum()
                if nf == 0 or not (p0 > 0):
                    for k_ in ("lift", "lo", "cov"):
                        out[(c, lvv)][k_].append(np.nan)
                    out[(c, lvv)]["pass"].append(False); out[(c, lvv)]["n_ev"].append(int(yf)); out[(c, lvv)]["prev"].append(nf / max(n0, 1))
                    continue
                pf = yf / nf
                dev = (y[f].astype(float) - pf)
                s = np.bincount(mon[f], weights=dev, minlength=nm)
                se = float(np.sqrt((s ** 2).sum()) / nf)
                lift = pf / p0; lo = (pf - 1.96 * se) / p0
                cov = yf / y0 if y0 else np.nan
                out[(c, lvv)]["lift"].append(lift); out[(c, lvv)]["lo"].append(lo); out[(c, lvv)]["cov"].append(cov)
                out[(c, lvv)]["pass"].append(bool(lo > 1 and cov >= 0.05)); out[(c, lvv)]["n_ev"].append(int(yf)); out[(c, lvv)]["prev"].append(nf / n0)
    rows = []
    for (c, lvv), d in out.items():
        npass = int(np.sum(d["pass"]))
        rows.append({"特徵": c, "級距": ("是" if lvv == 2 else "否") if (c in BIN or c in DESC) else "Q%d" % lvv,
                     "過的格數（/250）": npass, "進驗證段": bool(npass >= 125 and c not in DESC),
                     "①提升倍數_網格中位": float(np.nanmedian(d["lift"])) if np.isfinite(d["lift"]).any() else np.nan,
                     "①下緣_網格中位": float(np.nanmedian(d["lo"])) if np.isfinite(d["lo"]).any() else np.nan,
                     "②涵蓋率_網格中位": float(np.nanmedian(d["cov"])) if np.isfinite(d["cov"]).any() else np.nan,
                     "盛行率_網格中位": float(np.nanmedian(d["prev"])),
                     "主格H60g100%_提升倍數": d["lift"][HS.index(60) * len(GS) + GS.index(1.0)],
                     "描述或挑選": "原門檻版（只描述）" if c in DESC else "挑選"})
    T = pd.DataFrame(rows)
    os.makedirs(C.OUT, exist_ok=True)
    T.to_csv(os.path.join(C.OUT, "A4-10_探索段_特徵級距.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(cells).to_csv(os.path.join(C.OUT, "A4-10_探索段_網格事件數.csv"), index=False, encoding="utf-8-sig")
    sel = T[T["進驗證段"]][["特徵", "級距", "過的格數（/250）", "①提升倍數_網格中位", "②涵蓋率_網格中位"]].to_dict("records")
    cov = {c: float(np.mean(code[c] > 0)) for c in cols}
    R = {"件": "A4-10", "名稱": "飆股回推比對 季財報特徵部分（探索段挑特徵；⛔ 未開驗證段）", "N": "待裁定（＝ 驗證段實際驗的特徵數）",
         "探索段": [str(cal[t_lo].date()), str(cal[t_hi].date())], "股-日列數": N, "檔數": len(res),
         "網格": "H 10～250（25）× g 50%～≥1000%（10）＝ 250 格", "挑選規則": "≥125 格 ① 下緣 ＞1 且 ② ≥5%",
         "挑出的特徵級距（待裁定）": sel, "挑出數": len(sel), "特徵有值比例": cov,
         "網格事件數中位": float(np.median([c["事件"] for c in cells])), "樣本少格數（事件＜30）": int(sum(c["樣本少"] for c in cells)),
         "全表": T.to_dict("records"),
         "附註": [C.IDEA, "毛利率比上季升拿掉（B1 沒有毛利；特徵不全）", "飆股 ＝ 美股母體 seq6 網格（⛔ 不搬台股門檻）；給使用者的數用網格中位",
                 "挑定後就停：⛔ 未讀驗證段 2024-01～2026-09 的任何列", C.SURV]}
    R["耗時秒"] = round(time.time() - t0, 1); R["算於"] = C.now_tpe(); R["讀法寫死"] = C.READ_TS; R["台股原登錄"] = C.TW_REG["A4-10"]
    C.jdump(R, os.path.join(C.OUT, "A4-10.json"))
    IT.log("A4-10 完成：挑出 %d 個特徵級距 %.0fs" % (len(sel), time.time() - t0))

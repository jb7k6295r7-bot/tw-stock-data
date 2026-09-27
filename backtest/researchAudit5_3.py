# -*- coding: utf-8 -*-
"""稽核 §五（seq3 §五、§七之六；裁定 seq255、seq257 順 7）第 3 件：單筆層補視窗。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit5_3 Y|Rev|M|H1|H2|U|X [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit5_3_check.py Y|Rev|…

共同讀法（⭐ 看數字前寫定）：
  C1 每件補 5／10／60 日判定格；原件已有的天數沿用（⭐ 閘：本檔重算該天數 ＝ 原件數字，才准用同一套算新天數）
  C2 事件集合 ＝ 原件主格保留的事件（不因天數改變重新合併）；新天數只再套「窗尾 ＋ 該天數要有報酬」與（個股）延伸段硬斷點
  C3 扣成本版：個股 0.585%、ETF／大盤層 0.385%；只有「動手的一側」付成本（基準不付）⇒ 判定量往不利方向移一個成本，CI 同移
  C4 基準②：個股 ＝ 同日（進場前一日收盤）近 20 日報酬十分位的控制組；大盤層 ＝ 0050 近 20 日報酬（訊號日收盤）十分位同格的所有交易日
  C5 出口、結果、Bonferroni 照原件；天數增加 ⇒ Bonferroni 的格數 ×（天數數）（逐件寫明）
  C6 「穩」採 seq253 收緊讀法：相鄰天數本身也過顯著才寫「穩」，否則寫「方向一致，但只有 X 天過門檻」
  C7 單筆層：stop_force、t1_censor 不適用（沒有組合層權益）
輸出 backtest/resultsAudit5/3/<件>/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT0 = os.path.join(HERE, "resultsAudit5", "3")
HS = (5, 10, 20, 60)
C_STK, C_ETF = 0.00585, 0.00385
_G: dict = {}


def zb(k):
    return NormalDist().inv_cdf(1 - 0.05 / max(k, 1) / 2)


def cr0(x, g):
    x = np.asarray(x, float); g = np.asarray(g); n = len(x)
    m = float(x.mean()); d = x - m
    keys, inv = np.unique(g, return_inverse=True)
    s = np.zeros(len(keys)); np.add.at(s, inv, d)
    return m, float(np.sqrt((s ** 2).sum()) / n), len(keys)


def deciles(r):
    r = np.asarray(r, float); d = np.full(len(r), -1, int)
    ok = np.flatnonzero(np.isfinite(r)); n = len(ok)
    if n:
        order = ok[np.lexsort((ok, r[ok]))]
        d[order] = (np.arange(n) * 10) // n
    return d


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def stable_text(rows, key_pass, key_sign, fav):
    """seq253 收緊：每個通過的天數，相鄰天數本身也通過 ⇒「穩」；否則「方向一致，但只有 X 天過門檻」或「方向不一致」。rows：{H: row}。"""
    passed = [H for H in HS if H in rows and rows[H].get(key_pass)]
    if not passed:
        return "沒有天數通過"
    out = []
    for H in passed:
        i = HS.index(H); nb = [HS[j] for j in (i - 1, i + 1) if 0 <= j < len(HS) and HS[j] in rows]
        if all(rows[x].get(key_pass) for x in nb):
            out.append(f"{H} 天通過、相鄰（{'／'.join(map(str, nb))} 天）也通過 ⇒ 穩")
        elif all(np.isfinite(rows[x].get(key_sign, np.nan)) and fav(rows[x][key_sign]) for x in nb):
            out.append(f"{H} 天通過；相鄰（{'／'.join(map(str, nb))} 天）方向一致，但只有 {'／'.join(str(x) for x in passed)} 天過門檻")
        else:
            out.append(f"只在 {H} 天看得到（相鄰天數方向不一致）")
    return "；".join(out)


# ═════════════════════════════════════ Y：大盤驅動因素（PREREGY seq4；大盤層）
def run_Y(a):
    from . import researchY as Y
    OUT = os.path.join(OUT0, "Y"); os.makedirs(OUT, exist_ok=True)
    cal, pos, g = Y.tw_calendar()
    cal_arr = np.asarray(cal, dtype=str)
    w0, w1 = pos[Y.W0], pos[Y.W1]
    o50 = Y.open_adj("0050", cal)
    # 收盤（同 open_adj 的對法）
    from . import data as D
    from . import rerun17 as RR
    RR.use_snapshot(); calm = D.load_calendar(); st = D.load_stock("0050", "twse", calm)
    c_m = st.df["close"].to_numpy(float); pm = {str(d.date()): i for i, d in enumerate(calm)}
    c50 = np.full(len(cal), np.nan)
    for i, d in enumerate(cal):
        if d in pm:
            c50[i] = c_m[pm[d]]
    cff = pd.Series(c50).ffill().to_numpy()
    r20 = np.full(len(cal), np.nan)                               # 起算日 s 開盤前可知：c[s−1] ÷ c[s−21] − 1
    r20[21:] = cff[20:-1] / cff[:-21] - 1.0
    # 事件：用原件的產生器重建（researchY.body_events_continuous；#2 的來源是私有 us-stock-data ⇒ 逐列 ⛔ 不落檔）
    Y.cal_arr_g = cal_arr
    inst, _ = Y.load_instamt(cal); prev, _, _ = Y.load_marginmkt(cal); us, _, _, _ = Y.load_us()
    EV = Y.body_events_continuous(cal_arr, us, inst, prev)
    EV = EV[(EV["事件日"] >= Y.W0) & (EV["事件日"] <= Y.W1)].copy()
    EV["s"] = EV["起算位置"].astype(int)
    ref = pd.read_csv(os.path.join(HERE, "resultsY", "body_cells.csv"), float_precision="round_trip")
    judged = ref[ref["出口"] != "出口①"][["因素", "端"]].itertuples(index=False)
    judged = [tuple(x) for x in judged]
    K = Y.N_CELLS * len(HS); z = zb(K)
    rows = []; gate = {}
    for H in HS:
        RH = np.full(len(cal), np.nan); RH[:len(cal) - H] = o50[H:] / o50[:-H] - 1.0
        bd = np.arange(w0, w1 - H + 1); bd = bd[np.isfinite(RH[bd])]
        base1 = float(RH[bd].mean())
        dq = deciles(r20[bd]); ctrl = {q: float(RH[bd][dq == q].mean()) for q in range(10)}
        qmap = dict(zip(bd, dq))
        for k, e in judged:
            s = EV.loc[(EV["因素"] == k) & (EV["端"] == e), "s"].to_numpy(int)
            s = s[(s >= w0) & (s + H <= w1)]; s = s[np.isfinite(RH[s])]         # 原件同式（H20 主格、H60 描述都是這一條）
            x = RH[s]; n = len(s)
            seg = (s - w0) // H; neff = int(min(n, len(set(seg.tolist()))))
            grp = np.array([cal_arr[i][:7] for i in s]) if H <= 20 else seg
            row = {"因素": k, "端": e, "H": H, "n": n, "n_eff": neff, "cluster": "曆月" if H <= 20 else f"{H} 日區段"}
            for bn, xb in (("基準①", x - base1), ("基準②", x - np.array([ctrl.get(qmap.get(int(i), -1), np.nan) for i in s]))):
                okb = np.isfinite(xb); xb = xb[okb]
                m, se, _ = cr0(xb, np.asarray(grp)[okb])
                lo, hi = m - z * se, m + z * se
                ex = "出口①" if (n < 10 or neff < 30) else ("出口②" if neff < 100 else "出口③")
                res = "—" if ex == "出口①" else ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))
                sh = -C_ETF if m > 0 else C_ETF
                after = "—" if res in ("—", "結果①") else ("仍是候選" if ((res == "結果②" and lo + sh > 0) or (res == "結果③" and hi + sh < 0)) else "扣成本後不是")
                row.update({f"{bn}_D": m, f"{bn}_se": se, f"{bn}_lo": lo, f"{bn}_hi": hi, f"{bn}_出口": ex, f"{bn}_結果": res,
                            f"{bn}_扣0.385%_D": m + sh, f"{bn}_扣0.385%_lo": lo + sh, f"{bn}_扣0.385%_hi": hi + sh, f"{bn}_扣成本後": after, f"{bn}_缺": int((~okb).sum())})
            row["過"] = row["基準①_結果"] in ("結果②", "結果③")
            rows.append(row)
            if H == 20:
                q = ref[(ref["因素"] == k) & (ref["端"] == e)].iloc[0]
                gate[f"{k} {e} H20"] = [int(q["n"]) == n, abs(float(q["D"]) - row["基準①_D"]) < 1e-15]
            if H == 60:
                q = ref[(ref["因素"] == k) & (ref["端"] == e)].iloc[0]
                gate[f"{k} {e} H60"] = [int(q["描述 60 日 n"]) == n, abs(float(q["描述 60 日 D"]) - row["基準①_D"]) < 1e-15]
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    ok = all(all(v) for v in gate.values())
    S = {"件": "PREREGY 大盤驅動因素（seq4）", "判定格": [f"{k} {e}" for k, e in judged], "Bonferroni": {"格數": K, "z": z, "註": "16 格 × 4 個天數"},
         "閘_H20／H60＝原件（n、D）": gate, "閘過": ok,
         "其餘 12 格": "原件事件 ≤ 21（n_eff < 30）⇒ 任何天數都是出口①（天數只影響窗尾 1～2 筆），⛔ 不另算",
         "基準②": "0050 近 20 日報酬 c[s−1]÷c[s−21]−1 的十分位（窗內所有起算日）同格的 R_H 平均",
         "0050": {"資料": "edc6f 快照還原開盤／收盤對到 PREREGY 合併日曆"}}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 稽核 第 3 件之 Y：大盤驅動因素（PREREGY seq4；大盤層）補 5／10／60 日", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。成本 0.385%（大盤層）；Bonferroni 16 格 × 4 天數 ＝ {K}。", ""]
    npass = int((T["基準①_結果"].isin(["結果②", "結果③"])).sum()); npass2 = int((T["基準②_結果"].isin(["結果②", "結果③"])).sum())
    L.append(f"**結論：原件判得動的 4 格 × 4 個天數 ＝ 16 個判定格，基準① 測得出 {npass} 格、基準② 測得出 {npass2} 格；其餘 12 格事件太少，任何天數都是出口①。閘（H20、H60 ＝ 原件）：{'過' if ok else '不過'}。**")
    L += ["", "| 格 | H | n／n_eff | 基準① D〔Bonf CI〕 | 結果 | 扣 0.385% | 基準② D〔Bonf CI〕 | 結果 | 扣 0.385% |", "|---|---|---|---|---|---|---|---|---|"]
    for d in T.to_dict("records"):
        L.append(f"| {d['因素']} {d['端']} | {d['H']} | {d['n']}／{d['n_eff']} | {d['基準①_D'] * 100:+.2f}%〔{d['基準①_lo'] * 100:+.2f}, {d['基準①_hi'] * 100:+.2f}〕 | "
                 f"{d['基準①_出口']} {d['基準①_結果']} | {d['基準①_扣成本後']} | {d['基準②_D'] * 100:+.2f}%〔{d['基準②_lo'] * 100:+.2f}, {d['基準②_hi'] * 100:+.2f}〕 | "
                 f"{d['基準②_出口']} {d['基準②_結果']} | {d['基準②_扣成本後']} |")
    L += ["", "## 讀法", "",
          "- R_H(s) ＝ 0050 還原開盤 o[s＋H] ÷ o[s] − 1（原件 R20 同式）；基準① ＝ 窗內每個起算日 R_H 平均（原件母體基準）",
          "- 事件 ＝ 用原件產生器重建的窗內事件（researchY.body_events_continuous；#2 來源私有、⛔ 逐列不落檔），每個天數照原件同式：s ≥ w0、s＋H ≤ 窗尾、R_H 有值（0050 分割停牌那幾天無值 ⇒ 不收）",
          "- SE：H ≤ 20 用起算曆月分群（原件主格）；H60 用 60 日區段分群（原件 60 日描述）；n_eff ＝ min(n, H 日區段數)",
          "- 扣成本：候選方向往 0 移 0.385%（加碼候選 D − 0.385%、減碼候選 D ＋ 0.385%），CI 同移",
          f"- 閘：{json.dumps(gate, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


# ═════════════════════════════════════ Rev：反轉訊號 大盤層（PREREG反轉訊號 seq2；Rev_win 已補 5／10／20／60）
def run_Rev(a):
    sys.path.insert(0, HERE)
    import researchRev as RV
    OUT = os.path.join(OUT0, "Rev"); os.makedirs(OUT, exist_ok=True)
    Mm, Ms, info = RV.market_series()
    ev = RV.detect_series(Mm)
    dM = Mm["dates"]; lo, hi = int(np.searchsorted(dM, RV.W0)), int(np.searchsorted(dM, RV.W1))
    bars = np.flatnonzero(Mm["valid"])
    r20 = np.full(len(Mm["c"]), np.nan); cb = Mm["c"][bars]; r20[bars[20:]] = cb[20:] / cb[:-20] - 1.0
    W = pd.read_csv(os.path.join(HERE, "resultsRev", "win_cells.csv"), float_precision="round_trip")
    Wm = W[W["層"] == "大盤"]
    cells = []
    for H in HS:
        bd = RV.base_days(Mm, lo, hi, H)
        base = np.array([RV.fwd(Mm, d, H, hi) for d in bd]); bm = float(base.mean())
        dq = deciles(r20[bd]); ctrl = {q: float(base[dq == q].mean()) for q in range(10)}
        qmap = dict(zip(bd.tolist(), dq.tolist()))
        for code in RV.CODES:
            top = RV.SIDE[code] == "高"
            T = np.array([t for t, _ in ev[code]], int)
            m_ = (T >= lo) & (T <= hi - H); T = T[m_]
            keep = RV.merge20(T)
            E = []
            for t, k in zip(T, keep):
                if not k:
                    continue
                st = "保留" if np.isfinite(Mm["o"][t + 1]) else "剔除_停牌"
                C = RV.confirm_day(Mm["c"], Mm["valid"], Mm["h"][t], Mm["l"][t], t, top, hi)
                stc = "沒確認" if C < 0 else ("窗外" if C + H > hi else ("保留" if np.isfinite(Mm["o"][C + 1]) else "剔除_停牌"))
                E.append((t, C, st, stc))
            for ver in ("原版", "確認版"):
                b = np.array([t for t, C, st, stc in E if st == "保留"] if ver == "原版" else [C for t, C, st, stc in E if stc == "保留"], int)
                R = np.array([RV.fwd(Mm, d, H, hi) for d in b])
                # 基準② 的十分位：事件日 b 本身的 r20（b 不一定在 base_days 裡 ⇒ 依 base_days 的切點歸格）
                cuts = np.sort(r20[bd][np.isfinite(r20[bd])])
                qb = np.array([min(9, int(np.searchsorted(cuts, r20[d], side="right") * 10 // len(cuts))) if np.isfinite(r20[d]) else -1 for d in b], int)
                x2 = np.array([R[i] - ctrl[q] if q >= 0 else np.nan for i, q in enumerate(qb)])
                cells.append({"code": code, "名": RV.NAME[code], "邊": RV.SIDE[code], "版": ver, "H": H, "_X1": R - bm, "_X2": x2, "_g": (b - lo) // 20, "n": int(len(b))})
    for c in cells:
        c["n_eff"] = int(min(len(c["_X1"]), len(np.unique(c["_g"])))) if len(c["_X1"]) else 0
    k = sum(1 for c in cells if c["n_eff"] >= RV.NEFF_MIN); z = zb(k)
    rows = []; gate_bad = []
    for c in cells:
        top = c["邊"] == "高"
        row = {kk: v for kk, v in c.items() if not kk.startswith("_")}
        for bn, X in (("基準①", c["_X1"]), ("基準②", c["_X2"])):
            ok_ = np.isfinite(X); X = X[ok_]; g = c["_g"][ok_]
            if c["n_eff"] < RV.NEFF_MIN or len(X) == 0:
                row.update({f"{bn}_判定": "不可判定"}); continue
            m, se, ng = cr0(X, g); ne = int(min(len(X), ng))
            lo_, hi_ = m - z * se, m + z * se
            ex = "出口①" if ne < 30 else ("出口②" if ne < 100 else "出口③")
            rs = "—" if ex == "出口①" else ("結果①" if lo_ <= 0 <= hi_ else ("結果③" if m < 0 else "結果②"))
            ok = rs == ("結果③" if top else "結果②")
            sh = C_ETF if top else -C_ETF
            ok_n = ok and ((hi_ + sh) < 0 if top else (lo_ + sh) > 0)
            row.update({f"{bn}_mean": m, f"{bn}_lo": lo_, f"{bn}_hi": hi_, f"{bn}_n_eff": ne, f"{bn}_出口": ex, f"{bn}_結果": rs,
                        f"{bn}_判定": "通過" if ok else "不通過", f"{bn}_扣0.385%": ("仍過" if ok_n else ("不過" if ok else "—")), f"{bn}_缺": int((~ok_).sum())})
        q = Wm[(Wm["code"] == c["code"]) & (Wm["版"] == c["版"]) & (Wm["H"] == c["H"])].iloc[0]
        if int(q["事件"]) != int(np.isfinite(c["_X1"]).sum()) or (q["事件"] and not np.isclose(float(q["mean"]), float(np.mean(c["_X1"])), rtol=0, atol=1e-12)):
            gate_bad.append((c["code"], c["版"], c["H"]))
        rows.append(row)
    T = pd.DataFrame(rows)
    for bn in ("基準①", "基準②"):
        st = {}
        for (code, ver), g in T.groupby(["code", "版"]):
            rr = {int(r["H"]): {"p": r.get(f"{bn}_判定") == "通過", "m": r.get(f"{bn}_mean", np.nan)} for _, r in g.iterrows()}
            top = RV.SIDE[code] == "高"
            st[(code, ver)] = stable_text(rr, "p", "m", (lambda x: x < 0) if top else (lambda x: x > 0))
        T[f"{bn}_穩不穩"] = [st[(r.code, r.版)] for r in T.itertuples()]
    T.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    S = {"件": "PREREG反轉訊號 大盤層（seq2；Rev_win 補過 5／10／20／60）", "Bonferroni": {"k": k, "z": z, "k 的算法": "訊號 × 版本 × 視窗 可判定格（n_eff ≥ 10），同 Rev_win"},
         "閘_基準①＝win_cells 大盤（事件數、mean）": {"不一致": len(gate_bad), "例": gate_bad[:5]},
         "通過": {bn: T.loc[T[f"{bn}_判定"] == "通過", ["code", "版", "H"]].values.tolist() for bn in ("基準①", "基準②")},
         "基準②": "0050 近 20 日報酬（訊號日收盤；有效 K 棒 20 根）十分位（窗內 base_days 切點）同格的 R_H 平均",
         "成本": "大盤層 0.385%（Rev_win 原用 0.585%）"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    np1 = len(S["通過"]["基準①"]); np2 = len(S["通過"]["基準②"])
    L = ["# 稽核 第 3 件之 Rev：反轉訊號 大盤層（PREREG反轉訊號）扣 0.385%＋基準②", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。5／10／20／60 日已由 Rev_win（裁定 seq249）補過 ⇒ 沿用事件與基準①，本件只加 0.385% 與基準②。", "",
         f"**結論：大盤層 21 訊號 × 2 版 × 4 天數，基準① 通過 {np1} 格、基準② 通過 {np2} 格（Bonferroni k＝{k}）。閘（基準① ＝ Rev_win 大盤列）：{'過' if not gate_bad else '不過'}。**", "",
         "| 訊號 | 邊 | 版 | H | n／n_eff | 基準① X〔CI〕 | 判定 | 基準② X〔CI〕 | 判定 |", "|---|---|---|---|---|---|---|---|---|"]
    for d in T.to_dict("records"):
        if d.get("基準①_判定") == "不可判定":
            continue
        f = lambda bn: (f"{d[f'{bn}_mean'] * 100:+.2f}%〔{d[f'{bn}_lo'] * 100:+.2f}, {d[f'{bn}_hi'] * 100:+.2f}〕" if isinstance(d.get(f"{bn}_mean"), float) and np.isfinite(d.get(f"{bn}_mean")) else "—")
        L.append(f"| {d['名']} | {d['邊']} | {d['版']} | {d['H']} | {d['n']}／{d['n_eff']} | {f('基準①')} | {d['基準①_判定']} | {f('基準②')} | {d.get('基準②_判定', '—')} |")
    L += ["", "## 讀法", "", "- 事件、R_H、基準①、20 日區段分群、Bonferroni 的 k：照 researchRev_win 大盤層（逐格閘過才用）",
          "- 通過 ＝ 高點結果③、低點結果②；扣 0.385% ＝ 往不利方向移、CI 同移", "- 「穩」照 seq253 收緊讀法（cells.csv 的 穩不穩 欄）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if gate_bad:
        raise SystemExit("⛔ 閘不過")


# ═════════════════════════════════════ 個股層共用：價格矩陣（researchM.load_one 的價格段，逐字同式）
def _px_one(args):
    sid, market = args
    sys.path.insert(0, HERE)
    import researchH2 as H2
    import researchM_freq as RF
    D, TR = H2.D, H2.TR
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=_G["off"]).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RF._g5(valid, upto=ds["last"]) if delisted else RF._g5(valid)
    cff = pd.Series(c).ffill().to_numpy()
    okO = valid & np.isfinite(o) & (o > 0)
    px = np.where(okO, o, cff)
    cb = c[bars]; r20 = np.full(n, np.nan)
    if len(bars) > 20:
        r20[bars[20:]] = cb[20:] / cb[:-20] - 1.0
    run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        r_ = r_ + 1 if not valid[i] else 0; run[i] = r_
    return {"sid": sid, "market": market, "o": o, "c": c, "valid": valid, "px": px, "okO": okO, "trd": tb["trd"], "up_o": tb["up_o"],
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32), "r20": r20,
            "cff": cff, "cs_g5h1": np.cumsum(run >= 5).astype(np.int32)}


def load_matrix(a):
    from multiprocessing import Pool
    sys.path.insert(0, HERE)
    import researchH2 as H2
    D, TR, UG = H2.D, H2.TR, H2.UG
    cal = D.load_calendar()
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    _G.update(cal=cal, off=TR.load_official())
    with Pool(a.procs) as pool:
        res = pool.map(_px_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    sids = sorted(ST)
    M = {"cal": cal, "sids": sids, "sidx": {s: i for i, s in enumerate(sids)}, "ST": ST}
    for k in ("o", "px", "okO", "valid", "r20", "cs_pb", "cs_g5", "cff", "cs_g5h1"):
        M[k] = np.column_stack([ST[s][k] for s in sids])
    M["TRD1"] = np.column_stack([ST[s]["trd"] & np.isfinite(ST[s]["o"]) & ~ST[s]["up_o"] for s in sids])
    return M


def ctrl_matrices(M, H):
    """基準② 用（researchM 描述臂 d 的一般化，H＝持有根數）：G[T] ＝ px(T+1+H)／open(T+1) − 1；HB[T] ＝ [T, T+H+1] 價格斷點或 (T+3, T+H+1] 連續缺日。"""
    n = len(M["cal"]); Sn = len(M["sids"])
    G = np.full((n, Sn), np.nan)
    Od = np.where(M["okO"], M["o"], np.nan)
    G[:n - H - 1] = M["px"][H + 1:] / Od[1:n - H] - 1.0
    HB = np.zeros((n, Sn), bool)
    Tr = np.arange(n - H - 1); bb = Tr + H + 1
    pbc = M["cs_pb"][bb] - np.where(Tr[:, None] > 0, M["cs_pb"][np.maximum(Tr - 1, 0)], 0)
    g5c = M["cs_g5"][bb] - M["cs_g5"][np.minimum(Tr + 3, n - 1)]
    HB[:n - H - 1] = (pbc > 0) | (g5c > 0)
    return G, HB


def base2(M, G, HB, RAW, ev_sid, ev_T, ev_g):
    """每事件：同 T、近 20 日報酬十分位同格、T+1 可成交、窗內無硬斷點、該畫法 T 日無原始事件、非事件股 的控制組 G 平均 ⇒ d ＝ g − 控制。"""
    VAL, R20, TRD1 = M["valid"], M["r20"], M["TRD1"]; sidx = M["sidx"]; Sn = len(M["sids"])
    d = np.full(len(ev_T), np.nan); nctl = np.zeros(len(ev_T), int)
    order = np.argsort(ev_T, kind="stable")
    last = None
    for j in order:
        T = int(ev_T[j])
        if T != last:
            base = VAL[T] & np.isfinite(R20[T]); idx = np.flatnonzero(base)
            dec = np.full(Sn, -1)
            if len(idx) >= 10:
                dec[idx] = pd.qcut(pd.Series(R20[T, idx]).rank(method="first"), 10, labels=False).to_numpy()
            elig = base & TRD1[T + 1] & ~HB[T] & ~RAW[T] & np.isfinite(G[T]); last = T
        i = sidx[ev_sid[j]]
        if dec[i] < 0:
            continue
        cm = elig & (dec == dec[i]); cm[i] = False
        if cm.any():
            d[j] = ev_g[j] - float(G[T, cm].mean()); nctl[j] = int(cm.sum())
    return d, nctl


def verdict_shift(s, sh, summ_fn=None):
    """出口照原件；結果用往不利方向移後的 CI。"""
    if s["n"] < 30 or s["n_eff"] < 30:
        return "出口①", "—"
    ex = "出口②" if s["n_eff"] < 100 else "出口③"
    lo, hi, m = s["lo"] + sh, s["hi"] + sh, s["平均"] + sh
    return ex, ("結果①（測不出）" if lo <= 0 <= hi else ("結果②（測得出（＋））" if m > 0 else "結果③（測得出（−））"))


# ═════════════════════════════════════ M：PREREGM 下降趨勢線被收盤向上突破（三畫法）
def run_M(a):
    sys.path.insert(0, HERE)
    import researchH2 as H2
    import researchM as RM
    OUT = os.path.join(OUT0, "M"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    M = load_matrix(a); cal = M["cal"]; n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(RM.W0))); w1 = int(cal.searchsorted(pd.Timestamp(RM.W1)))
    EW = {H: RM.ew_open(M["o"], M["okO"], M["px"], H) for H in HS}              # EW_H(d) ＝ px(d+H)／open(d) − 1，d ＝ T+1（原件 EW[20][T+1]）
    SJ = json.load(open(os.path.join(HERE, "resultsM_body", "summary.json"), encoding="utf-8"))
    ref_main = SJ["判定三格"]; ref_c = SJ["§七描述臂"]["c_持有60日"]; ref_d = SJ["§七描述臂"]["d_控制組_同T同近20日報酬十分位"]
    rows = []; gate = {}
    CT = {H: ctrl_matrices(M, H) for H in HS}
    for m in RM.MAIN:
        E = pd.read_csv(os.path.join(HERE, "resultsM_body", f"events_X_{m}.csv"), dtype={"sid": str}, float_precision="round_trip")
        R0 = pd.read_csv(os.path.join(HERE, "resultsM", f"events_{m}.csv"), dtype={"sid": str})
        RAW = np.zeros((n, len(M["sids"])), bool)
        for s_, t_ in zip(R0["sid"], R0["T"]):
            if s_ in M["sidx"]:
                RAW[int(cal.searchsorted(pd.Timestamp(t_))), M["sidx"][s_]] = True
        for H in HS:
            e = E.copy()
            if H == 60:                                                     # 原件描述臂 c 同式
                keep = [(T + 61 <= w1) and not H2.brk(M["ST"][s_], int(f), T + 61) for s_, T, f in zip(e["sid"], e["T"], e["first"])]
                e = e[np.array(keep, bool)]
            si = e["sid"].map(M["sidx"]).to_numpy(int); T = e["T"].to_numpy(int)
            g = M["px"][T + 1 + H, si] / M["o"][T + 1, si] - 1.0
            X = g - EW[H][T + 1]
            blk = 20 if H == 20 else H; cap = RM.CAP if H == 20 else RM.WIN_DAYS // H
            s1 = RM.summ(X, T, cal, w0, blk=blk, cap=cap)
            G, HB = CT[H]
            d2, nctl = base2(M, G, HB, RAW, e["sid"].to_numpy(), T, g)
            ok2 = np.isfinite(d2)
            s2 = RM.summ(d2[ok2], T[ok2], cal, w0, blk=blk, cap=cap)
            row = {"畫法": m, "H": H, "n": s1["n"], "n_eff": s1["n_eff"]}
            for bn, s_ in (("基準①", s1), ("基準②", s2)):
                ex, rs = verdict_shift(s_, 0.0); exn, rsn = verdict_shift(s_, -C_STK)
                row.update({f"{bn}_平均": s_["平均"], f"{bn}_lo": s_["lo"], f"{bn}_hi": s_["hi"], f"{bn}_n": s_["n"], f"{bn}_n_eff": s_["n_eff"],
                            f"{bn}_出口": ex, f"{bn}_結果": rs, "扣0.585%_" + bn + "_結果": rsn})
            row["基準②_控制數中位"] = float(np.median(nctl[ok2])) if ok2.any() else np.nan
            rows.append(row)
            if H == 20:
                gate[f"{m} H20 基準① ＝ 判定格"] = s1["n"] == ref_main[m]["n"] and abs(s1["平均"] - ref_main[m]["平均"]) < 1e-12 and abs(s1["lo"] - ref_main[m]["lo"]) < 1e-12
                gate[f"{m} H20 基準② ＝ 描述臂 d"] = s2["n"] == ref_d[m]["n"] and abs(s2["平均"] - ref_d[m]["平均"]) < 1e-12
            if H == 60:
                gate[f"{m} H60 基準① ＝ 描述臂 c"] = s1["n"] == ref_c[m]["n"] and abs(s1["平均"] - ref_c[m]["平均"]) < 1e-12 and abs(s1["lo"] - ref_c[m]["lo"]) < 1e-12
        print(f"  [M {m}] {time.time() - t0:.0f}s", flush=True)
    T_ = pd.DataFrame(rows); T_.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    ok = all(gate.values())
    st = {}
    for m in RM.MAIN:
        for bn in ("基準①", "基準②"):
            rr = {int(r["H"]): {"p": str(r[f"{bn}_結果"]).startswith("結果②"), "m": r[f"{bn}_平均"]} for r in T_[T_["畫法"] == m].to_dict("records")}
            st[f"{m} {bn}（＋）"] = stable_text(rr, "p", "m", lambda x: x > 0)
    S = {"件": "PREREGM 趨勢線突破（seq1；三畫法）", "閘": gate, "閘過": ok, "穩（seq253 收緊；只看 ＋）": st,
         "讀法": "事件 ＝ resultsM_body/events_X_*.csv（原件保留事件）；H60 照原件描述臂 c 再排 T+61 超出窗尾與延伸段硬斷點；H＝20 的區段 20／上限 115（原件），其餘區段 ＝ H、上限 ⌊2313／H⌋；"
                 "基準② ＝ 原件描述臂 d（同 T、近 20 日報酬十分位）一般化到 H；扣成本 ＝ 判定量 − 0.585%（基準不付）"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 稽核 第 3 件之 M：PREREGM 趨勢線突破 補 5／10／60 日＋扣成本＋基準②", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。個股成本 0.585%。沿用：H20 判定格（基準①）、描述臂 d（H20 基準②）、描述臂 c（H60 基準①）——閘逐格對過才用。", ""]
    pos_ = T_[T_["基準①_結果"].str.startswith("結果②") | T_["基準②_結果"].str.startswith("結果②")]
    L.append(f"**結論：三畫法 × 4 天數，測得出（＋）的格：{('、'.join(f'{r.畫法}H{r.H}' for r in pos_.itertuples()) or '無')}；閘：{'過' if ok else '不過'}。**")
    L += ["", "| 畫法 | H | n／n_eff | 基準① X〔CI〕 | 結果 | 扣 0.585% | 基準② d〔CI〕 | 結果 | 扣 0.585% |", "|---|---|---|---|---|---|---|---|---|"]
    for d in T_.to_dict("records"):
        L.append(f"| {d['畫法']} | {d['H']} | {d['n']}／{d['n_eff']} | {d['基準①_平均'] * 100:+.2f}%〔{d['基準①_lo'] * 100:+.2f}, {d['基準①_hi'] * 100:+.2f}〕 | {d['基準①_出口']} {d['基準①_結果']} | "
                 f"{d['扣0.585%_基準①_結果']} | {d['基準②_平均'] * 100:+.2f}%〔{d['基準②_lo'] * 100:+.2f}, {d['基準②_hi'] * 100:+.2f}〕 | {d['基準②_出口']} {d['基準②_結果']} | {d['扣0.585%_基準②_結果']} |")
    L += ["", "## 讀法與閘", "", f"- {S['讀法']}", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", f"- 穩：{json.dumps(st, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


# ═════════════════════════════════════ H1：PREREGH1 月線 3 日站回（分類器讀法）
def ctrl_close(M, H, back=2, g5key="cs_g5h1"):
    """基準② 控制（收盤出場版）：Gc[T] ＝ cff(T+H)／open(T+1) − 1；HB[T] ＝ [T−back, T+H] 價格斷點或 (T−back+4 起) 連續 5 日缺（researchH2.brk 同式）。"""
    n = len(M["cal"]); Sn = len(M["sids"])
    Od = np.where(M["okO"], M["o"], np.nan)
    Gc = np.full((n, Sn), np.nan)
    Gc[:n - H] = M["cff"][H:] / Od[1:n - H + 1] - 1.0
    Tr = np.arange(back, n - H)
    a_ = Tr - back; b_ = Tr + H
    pbc = M["cs_pb"][b_] - np.where(a_[:, None] > 0, M["cs_pb"][np.maximum(a_ - 1, 0)], 0)
    g5a = a_ + 4
    g5c = np.where((b_ >= g5a)[:, None], M[g5key][b_] - M[g5key][np.maximum(g5a - 1, 0)], 0)
    HB = np.ones((n, Sn), bool)
    HB[back:n - H] = (pbc > 0) | (g5c > 0)
    return Gc, HB


def base2_at(M, Gc, HB, Tdec, sids_ev, g_ev):
    """每事件：決策日 Tdec 的近 20 日報酬十分位同格、Tdec+1 可成交、窗內無斷點、非本股 的控制組 Gc 平均 ⇒ d ＝ g − 控制。"""
    VAL, R20, TRD1 = M["valid"], M["r20"], M["TRD1"]; sidx = M["sidx"]; Sn = len(M["sids"])
    d = np.full(len(Tdec), np.nan)
    cache = {}
    for j, (T, s_, g) in enumerate(zip(Tdec, sids_ev, g_ev)):
        T = int(T)
        if T not in cache:
            base = VAL[T] & np.isfinite(R20[T]); idx = np.flatnonzero(base)
            dec = np.full(Sn, -1)
            if len(idx) >= 10:
                dec[idx] = pd.qcut(pd.Series(R20[T, idx]).rank(method="first"), 10, labels=False).to_numpy()
            cache = {T: (dec, base & TRD1[T + 1] & ~HB[T] & np.isfinite(Gc[T]))}
        dec, elig = cache[T]
        i = sidx.get(s_, -1)
        if i < 0 or dec[i] < 0:
            continue
        cm = elig & (dec == dec[i]); cm[i] = False
        if cm.any():
            d[j] = g - float(Gc[T, cm].mean())
    return d


def one_side(x, t, cal, w0, H, sh):
    """單組（站回組）平均與月分群 CI（research11.cl_stats 同式），sh ＝ 扣成本位移。"""
    x = np.asarray(x, float) + sh
    mon = np.array([str(cal[int(i)])[:7] for i in t])
    m, se, nm = cr0(x, mon)
    nblk = len(set(((np.asarray(t) - w0) // H).tolist())); neff = int(min(len(x), nblk))
    lo, hi = m - 1.96 * se, m + 1.96 * se
    ex = "出口①" if neff < 30 else ("出口②" if neff < 100 else "出口③")
    rs = "—" if ex == "出口①" else ("結果①（測不出）" if lo <= 0 <= hi else ("結果②（測得出（＋））" if m > 0 else "結果③（測得出（−））"))
    return {"平均": m, "lo": lo, "hi": hi, "n": len(x), "n_eff": neff, "出口": ex, "結果": rs}


def run_H1(a):
    from multiprocessing import Pool
    sys.path.insert(0, HERE)
    import researchH2 as H2
    import researchH1 as RH1
    OUT = os.path.join(OUT0, "H1"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    cal = H2.D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(RH1.W0))); w1 = int(cal.searchsorted(pd.Timestamp(RH1.W1)))
    U = H2.UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    with Pool(a.procs, initializer=RH1._init, initargs=(cal,)) as pool:
        res = pool.map(RH1.load_one, list(zip(U["stock_id"], U["market"])), chunksize=16)
    ST = {r["sid"]: r for r in res if r is not None}
    EW = {H: RH1.market_ew(ST, n, H) for H in HS}
    M = load_matrix(a)
    ref = json.load(open(os.path.join(HERE, "resultsH1", "summary.json"), encoding="utf-8"))
    rows = []; gate = {}
    for H in HS:
        E, acc = RH1.build(ST, cal, w0, w1, EW[H], Hh=H)
        j1 = RH1.judge(E, cal, w0, Hh=H)
        Gc, HB = ctrl_close(M, H)
        d = base2_at(M, Gc, HB, (E["t"] + 3).to_numpy(), E["sid"].to_numpy(), E["R"].to_numpy(float))
        E2 = E.assign(X=d)[np.isfinite(d)]
        j2 = RH1.judge(E2, cal, w0, Hh=H)
        up1 = E[E["站回"] == 1]; up2 = E2[E2["站回"] == 1]
        row = {"H": H, "保留": len(E), "站回": int(E["站回"].sum()), "未站回": int((E["站回"] == 0).sum())}
        for bn, j in (("基準①", j1), ("基準②", j2)):
            row.update({f"{bn}_D": j.get("D"), f"{bn}_lo": j.get("lo"), f"{bn}_hi": j.get("hi"), f"{bn}_n_eff": j.get("n_eff"), f"{bn}_出口": j.get("出口"), f"{bn}_結果": j.get("結果")})
        for bn, up in (("基準①", (up1["X"], up1["t"])), ("基準②", (up2["X"], up2["t"]))):
            r0 = one_side(up[0], up[1], cal, w0, H, 0.0); rn = one_side(up[0], up[1], cal, w0, H, -C_STK)
            row.update({f"站回組_{bn}_X": r0["平均"], f"站回組_{bn}_CI": f"{r0['lo'] * 100:+.2f}～{r0['hi'] * 100:+.2f}", f"站回組_{bn}_結果": r0["結果"],
                        f"站回組_{bn}_扣0.585%": rn["結果"], f"站回組_{bn}_扣0.585%_CI": f"{rn['lo'] * 100:+.2f}～{rn['hi'] * 100:+.2f}"})
        row["基準②_缺"] = int((~np.isfinite(d)).sum())
        rows.append(row)
        if H == 20:
            q = ref["③判定"]; gate["H20 ＝ 主格"] = abs(j1["D"] - q["D"]) < 1e-12 and abs(j1["lo"] - q["lo"]) < 1e-12 and len(E) == ref["①事件帳"]["保留事件"]
        if H == 60:
            q = ref["⑦描述臂"]["d_H60"]["判定形"]; gate["H60 ＝ 描述臂 d_H60"] = abs(j1["D"] - q["D"]) < 1e-12 and abs(j1["lo"] - q["lo"]) < 1e-12
        print(f"  [H1 H{H}] {time.time() - t0:.0f}s", flush=True)
    T_ = pd.DataFrame(rows); T_.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    ok = all(gate.values())
    st = {bn: stable_text({int(r["H"]): {"p": str(r[f"{bn}_結果"]).startswith("結果②"), "m": r[f"{bn}_D"]} for r in rows}, "p", "m", lambda x: x > 0)
          for bn in ("基準①", "基準②")}
    S = {"件": "PREREGH1 月線 3 日站回（seq2；分類器讀法）", "閘": gate, "閘過": ok, "穩（seq253 收緊）": st,
         "讀法": "判定量 D ＝ 站回組 − 未站回組（原件 build／judge，Hh＝H：合併窗與未來窗同延長、區段長 H）；D 是兩組事件相減、成本相消 ⇒ 扣成本版改報「站回組 X − 0.585%」（買站回組是否贏過基準）；"
                 "基準② ＝ 決策日 t0+3 收盤的近 20 日報酬十分位控制組，同一段 open(t0+4)→close(t0+3+H)",
         "事件帳": "各 H 見 cells.csv 保留／站回／未站回"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 稽核 第 3 件之 H1：PREREGH1 月線 3 日站回 補 5／10／60 日＋扣成本＋基準②", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。沿用：H20 主格、H60 描述臂 d（閘逐格對過）。", "",
         f"**結論：D（站回 − 未站回）基準① " + "、".join(f"H{r['H']} {r['基準①_結果'].split('（')[0]}" for r in rows) + "；基準② " + "、".join(f"H{r['H']} {str(r['基準②_結果']).split('（')[0]}" for r in rows)
         + f"；站回組扣 0.585% 後（基準①）" + "、".join(f"H{r['H']} {str(r['站回組_基準①_扣0.585%']).split('（')[0]}" for r in rows) + f"。閘：{'過' if ok else '不過'}。**", "",
         "| H | 保留（站回／未站回） | 基準① D〔CI〕 | 結果 | 基準② D〔CI〕 | 結果 | 站回組 X 扣 0.585%（①）〔CI〕 | 結果 |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['H']} | {r['保留']}（{r['站回']}／{r['未站回']}） | {r['基準①_D'] * 100:+.3f}〔{r['基準①_lo'] * 100:+.3f}, {r['基準①_hi'] * 100:+.3f}〕 | {r['基準①_出口']} {r['基準①_結果']} | "
                 f"{r['基準②_D'] * 100:+.3f}〔{r['基準②_lo'] * 100:+.3f}, {r['基準②_hi'] * 100:+.3f}〕 | {r['基準②_出口']} {r['基準②_結果']} | "
                 f"{(r['站回組_基準①_X'] - C_STK) * 100:+.3f}〔{r['站回組_基準①_扣0.585%_CI']}〕 | {r['站回組_基準①_扣0.585%']} |")
    L += ["", "## 讀法與閘", "", f"- {S['讀法']}", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", f"- 穩：{json.dumps(st, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


# ═════════════════════════════════════ H2：PREREGH2 144／200MA 雙翻揚，H 日內觸及 ×1.3
def run_H2(a):
    from multiprocessing import Pool
    sys.path.insert(0, HERE)
    import researchH2 as RH2
    OUT = os.path.join(OUT0, "H2"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    cal = RH2.D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(RH2.W0))); w1 = int(cal.searchsorted(pd.Timestamp(RH2.W1)))
    U = RH2.UG.gate3(pd.read_csv(os.path.join(RH2.H2D, "meta", "stocks.csv"), dtype=str))
    with Pool(a.procs, initializer=RH2._init, initargs=(cal,)) as pool:
        res = pool.map(RH2.load_one, list(zip(U["stock_id"], U["market"])), chunksize=16)
    ST = {r["sid"]: r for r in res if r is not None}
    C = RH2.Ctx(ST, cal, w0, w1)
    R20 = {}
    for s, S_ in ST.items():                                    # 近 20 日報酬（有效 K 棒 20 根）
        b = np.flatnonzero(S_["valid"]); r = np.full(n, np.nan)
        if len(b) > 20:
            r[b[20:]] = S_["c"][b[20:]] / S_["c"][b[:-20]] - 1.0
        R20[s] = r

    def draw_r20(ev, H, seed, m=RH2.M_CTRL):
        """基準②：同 t 資格母體（原件 R4 前半）中，近 20 日報酬十分位同格、t 日無原始訊號、非本股 ⇒ 抽 m 檔（其餘同原件 draw_controls）。"""
        rng = np.random.default_rng(seed); out = []
        for e in ev:
            ss, vv, q, sg = C.day(e["t"], "main")
            if e["sid"] not in ss:
                out.append((e, [], [], [])); continue
            i = ss.index(e["sid"])
            rr = np.array([R20[s][e["t"]] for s in ss])
            dq = deciles(rr)
            if dq[i] < 0:
                out.append((e, [], [], [])); continue
            pool_ = [ss[j] for j in np.flatnonzero((~sg) & (dq == dq[i])) if ss[j] != e["sid"]]
            pick = list(rng.choice(pool_, size=min(m, len(pool_)), replace=False)) if pool_ else []
            res_ = [o for o in (RH2.outcome(ST[s], e["t"], H) for s in pick) if isinstance(o, dict)]
            out.append((e, res_, pool_, pick))
        return out

    ref = json.load(open(os.path.join(HERE, "resultsH2", "summary.json"), encoding="utf-8"))
    ge13_orig = RH2.ge13
    rows = []; gate = {}
    for H in HS:
        row = {"H": H}
        for cv, fac in (("毛", 1.0), ("扣0.585%", 1.0 + C_STK)):
            RH2.ge13 = (lambda mx, base, f=fac: int(np.isfinite(mx) and mx >= 1.3 * f * base * (1 - 1e-12))) if fac != 1.0 else ge13_orig
            ev, acc = RH2.build_events(C, "main", H)
            p1, _ = RH2.draw_controls(C, ev, "main", H, RH2.SEED); j1, _ = RH2.judge(C, p1, H)
            p2 = draw_r20(ev, H, RH2.SEED); j2, _ = RH2.judge(C, p2, H)
            for bn, j in (("基準①", j1), ("基準②", j2)):
                row.update({f"{cv}_{bn}_D": j.get("D"), f"{cv}_{bn}_lo": j.get("lo"), f"{cv}_{bn}_hi": j.get("hi"), f"{cv}_{bn}_n": j.get("n"),
                            f"{cv}_{bn}_n_eff": j.get("n_eff"), f"{cv}_{bn}_出口": j.get("出口"), f"{cv}_{bn}_結果": j.get("結果"),
                            f"{cv}_{bn}_訊號達成率": j.get("訊號達成率"), f"{cv}_{bn}_對照達成率": j.get("對照達成率")})
            if cv == "毛":
                row["保留事件"] = len(ev)
                if H == 20:
                    q = ref["③判定"]; gate["H20 ＝ 主格"] = abs(j1["D"] - q["D"]) < 1e-12 and abs(j1["lo"] - q["lo"]) < 1e-12 and j1["n"] == q["n"]
                if H == 60:
                    q = ref["⑥描述臂"]["c_H60"]["判定形"]; gate["H60 ＝ 描述臂 c_H60"] = abs(j1["D"] - q["D"]) < 1e-12 and abs(j1["lo"] - q["lo"]) < 1e-12
        RH2.ge13 = ge13_orig
        rows.append(row)
        print(f"  [H2 H{H}] {time.time() - t0:.0f}s", flush=True)
    T_ = pd.DataFrame(rows); T_.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    ok = all(gate.values())
    st = {bn: stable_text({r["H"]: {"p": str(r[f"毛_{bn}_結果"]).startswith("結果②"), "m": r[f"毛_{bn}_D"]} for r in rows}, "p", "m", lambda x: x > 0)
          for bn in ("基準①", "基準②")}
    S = {"件": "PREREGH2 144／200MA 雙翻揚、H 日內觸及 ×1.3（seq2）", "閘": gate, "閘過": ok, "穩（seq253 收緊）": st,
         "讀法": "判定量 D ＝ 訊號觸及率 − 對照觸及率（原件 build_events／draw_controls／judge，H 換成 5／10／20／60：事件窗、合併、區段同原件以 H 參數化）；"
                 "扣成本版：判定量是觸及率（不是報酬）⇒ 改把觸及門檻抬高一個來回成本（×1.3 × 1.00585），兩邊同抬；"
                 "基準② ＝ 同 t 資格母體中近 20 日報酬十分位同格（取代原件的 vol60 五分位），其餘抽法、種子同原件"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 稽核 第 3 件之 H2：PREREGH2 144／200MA 雙翻揚 補 5／10／60 日＋扣成本＋基準②", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。沿用：H20 主格、H60 描述臂 c（閘逐格對過）。", "",
         "**結論：觸及率差 D（基準①）" + "、".join(f"H{r['H']} {str(r['毛_基準①_結果']).split('（')[0]}" for r in rows)
         + "；基準② " + "、".join(f"H{r['H']} {str(r['毛_基準②_結果']).split('（')[0]}" for r in rows) + f"。閘：{'過' if ok else '不過'}。**", "",
         "| H | 保留 | 基準① D〔CI〕 | 結果 | 門檻 +0.585% | 基準② D〔CI〕 | 結果 | 門檻 +0.585% |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f = lambda cv, bn: f"{r[f'{cv}_{bn}_D'] * 100:+.3f}〔{r[f'{cv}_{bn}_lo'] * 100:+.3f}, {r[f'{cv}_{bn}_hi'] * 100:+.3f}〕" if r.get(f"{cv}_{bn}_D") is not None else "—"
        L.append(f"| {r['H']} | {r['保留事件']} | {f('毛', '基準①')} | {r['毛_基準①_出口']} {r['毛_基準①_結果']} | {r['扣0.585%_基準①_結果']} | "
                 f"{f('毛', '基準②')} | {r['毛_基準②_出口']} {r['毛_基準②_結果']} | {r['扣0.585%_基準②_結果']} |")
    L += ["", "## 讀法與閘", "", f"- {S['讀法']}", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", f"- 穩：{json.dumps(st, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


# ═════════════════════════════════════ U：PREREGU 費波那契回撤（38.2／61.8 對鄰位的止跌反彈）
def _u_one(args):
    sid, market = args
    sys.path.insert(0, HERE)
    import researchU_core as UC
    from backtest import fib_u as FU
    cal, w0, w1, off = _G["cal"], _G["w0"], _G["w1"], _G["off"]
    S = UC.load(sid, market, cal, off)
    if S is None:
        return None
    _, cf = UC.detect_all(S, cal, w0, w1, cfgs=[(5, H) for H in HS])
    c = S["c"]; out = {}
    for (k, H), v in cf.items():
        rows = v["rows"]
        if not rows:
            continue
        E = pd.DataFrame(rows)
        E = E[E["狀態"] == "保留"].copy()
        if not len(E):
            continue
        T = E["T"].to_numpy(np.int64); p = E["p"].to_numpy(float)
        E["y"] = FU.outcome_vec(c, T, p, H, FU.BAND)
        cff = pd.Series(c).ffill().to_numpy()
        E["g"] = cff[np.minimum(T + H, len(c) - 1)] / c[T] - 1.0
        out[H] = E[["pos", "T", "tH", "y", "g"]].assign(sid=sid)
    return out


def dstat_fe(E, wts, cl, fe):
    """B1 的迴歸加十分位固定效果：y ＝ Σ_pos β_pos·1[pos] ＋ Σ_{q≥1} γ_q·1[dec＝q]（位置虛擬變數飽和、十分位去掉第 0 格）；D ＝ a'β，CR0 分群。"""
    d = E[E["pos"].isin(list(wts)) & (E["y"] >= 0) & (E[fe] >= 0)]
    P = list(wts)
    Xp = np.column_stack([(d["pos"] == p_).to_numpy(float) for p_ in P])
    Xq = np.column_stack([(d[fe] == q).to_numpy(float) for q in range(1, 10)])
    X = np.column_stack([Xp, Xq]); y = d["y"].to_numpy(float)
    XtX = X.T @ X
    Xi = np.linalg.pinv(XtX); beta = Xi @ X.T @ y; u = y - X @ beta
    sc = pd.DataFrame(X * u[:, None]).groupby(d[cl].to_numpy()).sum().to_numpy()
    V = Xi @ (sc.T @ sc) @ Xi
    a = np.r_[[wts[p_] for p_ in P], np.zeros(9)]
    Dv = float(a @ beta); se = float(np.sqrt(a @ V @ a))
    return {"D": Dv, "se": se, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se, "n": int(len(d))}


def run_U(a):
    from multiprocessing import Pool
    sys.path.insert(0, HERE)
    import researchH2 as H2
    import researchU as RU
    import researchU_core as UC
    from backtest import fib_u as FU
    OUT = os.path.join(OUT0, "U"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    cal = H2.D.load_calendar(); n = len(cal)
    w0, w1 = UC.win_index(cal)
    U = H2.UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    _G.update(cal=cal, w0=w0, w1=w1, off=H2.TR.load_official())
    with Pool(a.procs) as pool:
        res = pool.map(_u_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    M = load_matrix(a)
    Cm = np.where(M["valid"], np.column_stack([M["ST"][s]["c"] for s in M["sids"]]), np.nan)
    DEC = np.full((n, len(M["sids"])), -1, np.int8)
    for t in range(w0, w1 + 1):
        DEC[t] = deciles(M["r20"][t])
    ref = json.load(open(os.path.join(HERE, "resultsU", "summary.json"), encoding="utf-8"))
    rows = []; gate = {}
    WD = RU.WD; W3862 = {"38.2": 0.5, "61.8": 0.5}
    for H in HS:
        E = pd.concat([r[H] for r in res if r is not None and H in r], ignore_index=True)
        E["mon"] = [str(cal[t])[:7] for t in E["T"]]
        E["dec"] = [int(DEC[t, M["sidx"][s]]) if s in M["sidx"] else -1 for s, t in zip(E["sid"], E["T"])]
        s1 = RU.dstat(E, WD, "mon")
        blk = 20 if H <= 20 else H; cap = 115 if H <= 20 else 2313 // H
        ne = min(min(int(((E["pos"] == p_) & (E["y"] >= 0)).sum()), int(np.minimum((E.loc[(E["pos"] == p_) & (E["y"] >= 0), "T"] - w0) // blk, cap - 1).nunique())) for p_ in FU.SIX)
        nmin = min(int(((E["pos"] == p_) & (E["y"] >= 0)).sum()) for p_ in FU.SIX)
        ex1, rs1 = RU.verdict(s1, ne, nmin)
        s2 = dstat_fe(E, WD, "mon", "dec"); ex2, rs2 = RU.verdict(s2, ne, nmin)
        # 扣成本參考（判定量是反彈比例、⛔ 不涉成本）：38.2／61.8 觸及後 T 收盤進、持有 H 日的超額 − 0.585%
        EWc = RU.ew_close(Cm, M["cff"], H)
        e38 = E[E["pos"].isin(["38.2", "61.8"]) & (E["T"] + H <= w1)]
        xg = e38["g"].to_numpy(float) - EWc[e38["T"].to_numpy()]
        okx = np.isfinite(xg)
        mx, sx, _ = cr0(xg[okx] - C_STK, e38["mon"].to_numpy()[okx])
        row = {"H": H, "保留（六位置分勝負）": nmin, "n_eff": ne,
               "基準①_D": s1["D"], "基準①_lo": s1["lo"], "基準①_hi": s1["hi"], "基準①_出口": ex1, "基準①_結果": rs1,
               "基準②_D": s2["D"], "基準②_lo": s2["lo"], "基準②_hi": s2["hi"], "基準②_出口": ex2, "基準②_結果": rs2, "基準②_n": s2["n"],
               "38.2＋61.8_X扣0.585%": mx, "38.2＋61.8_X扣0.585%_lo": mx - 1.96 * sx, "38.2＋61.8_X扣0.585%_hi": mx + 1.96 * sx, "38.2＋61.8_n": int(okx.sum())}
        rows.append(row)
        if H == 20:
            q = ref["判定格"]; gate["H20 ＝ 判定格"] = abs(s1["D"] - q["D"]) < 1e-12 and abs(s1["lo"] - q["lo_月"]) < 1e-12
        if H == 10:
            q = ref["§六描述臂"]["b_判定帶與窗"]["10日窗"]; gate["H10 ＝ 描述臂 b 10日窗"] = abs(s1["D"] - q["D"]) < 1e-12 and abs(s1["lo"] - q["lo"]) < 1e-12
        print(f"  [U H{H}] {time.time() - t0:.0f}s", flush=True)
    T_ = pd.DataFrame(rows); T_.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    ok = all(gate.values())
    st = {bn: stable_text({r["H"]: {"p": str(r[f"{bn}_結果"]).startswith("結果②"), "m": r[f"{bn}_D"]} for r in rows}, "p", "m", lambda x: x > 0) for bn in ("基準①", "基準②")}
    S = {"件": "PREREGU 費波那契回撤（seq1）", "閘": gate, "閘過": ok, "穩（seq253 收緊）": st,
         "讀法": "判定量 D ＝ 38.2／61.8 的反彈比例 − 鄰位（原件 dstat：位置虛擬變數、月分群 CR0）；H 換成 5／10／20／60：觀察窗、[T, T+H] 斷點、T+H ≤ 窗尾照原件 V4（合併仍 20 日）；"
                 "n_eff 的區段：H ≤ 20 用 20 日（原件）、H60 用 60 日（上限 38）；基準② ＝ 同一迴歸加 T 日近 20 日報酬十分位固定效果（控制之前 20 日漲跌）；"
                 "扣成本：判定量是反彈比例、⛔ 不涉成本 ⇒ 另報 38.2＋61.8 觸及後 T 收盤進、持有 H 日對 gate3 等權的超額 − 0.585%（描述）"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 稽核 第 3 件之 U：PREREGU 費波那契回撤 補 5／60 日（10 日沿用描述臂 b）＋基準②＋成本參考", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。沿用：H20 判定格、H10 描述臂 b（閘逐格對過）。", "",
         "**結論：D（38.2／61.8 − 鄰位）基準① " + "、".join(f"H{r['H']} {str(r['基準①_結果']).split('（')[0]}" for r in rows)
         + "；基準② " + "、".join(f"H{r['H']} {str(r['基準②_結果']).split('（')[0]}" for r in rows) + f"。閘：{'過' if ok else '不過'}。**", "",
         "| H | 分勝負最少位置 | n_eff | 基準① D〔CI〕 | 結果 | 基準② D〔CI〕 | 結果 | 38.2＋61.8 超額扣 0.585%〔CI〕（描述） |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['H']} | {r['保留（六位置分勝負）']} | {r['n_eff']} | {r['基準①_D'] * 100:+.2f}pp〔{r['基準①_lo'] * 100:+.2f}, {r['基準①_hi'] * 100:+.2f}〕 | {r['基準①_出口']} {r['基準①_結果']} | "
                 f"{r['基準②_D'] * 100:+.2f}pp〔{r['基準②_lo'] * 100:+.2f}, {r['基準②_hi'] * 100:+.2f}〕 | {r['基準②_出口']} {r['基準②_結果']} | "
                 f"{r['38.2＋61.8_X扣0.585%'] * 100:+.2f}%〔{r['38.2＋61.8_X扣0.585%_lo'] * 100:+.2f}, {r['38.2＋61.8_X扣0.585%_hi'] * 100:+.2f}〕 |")
    L += ["", "## 讀法與閘", "", f"- {S['讀法']}", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", f"- 穩：{json.dumps(st, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


# ═════════════════════════════════════ X：PREREGX 型態量幅目標（甲）＋成形前讀法（乙）
def run_X(a):
    sys.path.insert(0, HERE)
    import researchX as RX
    import researchH1 as RH1
    OUT = os.path.join(OUT0, "X"); os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    cal, n, w0, w1, U, ST = RX.load_all(a.procs)
    wE, wB = w1 - RX.HMAX, w1 - RX.FORM_N
    Mx = RX.Mat(ST, n, w0, wE)
    # 基準② 的十分位：t 日近 20 日報酬（有效 K 棒 20 根）橫斷面十分位（排序同 Mat.DEC：升冪、平手依代號序）
    R20 = np.full((Mx.N, n), np.nan)
    for s in Mx.sids:
        S = ST[s]; b = np.flatnonzero(np.isfinite(S["c"]))
        if len(b) > 20:
            R20[Mx.ix[s], b[20:]] = S["c"][b[20:]] / S["c"][b[:-20]] - 1.0
    DEC2 = np.full((Mx.N, n), -1, np.int8)
    for t in range(w0, w1 + 1):
        DEC2[:, t] = deciles(R20[:, t])
    ref = json.load(open(os.path.join(HERE, "resultsX", "summary.json"), encoding="utf-8"))
    HA = (5, 10, 20, 60, 120)
    rowsA = []; gate = {}
    pools2 = {}

    def pool2(t, d, ok):
        k = (t, d, id(ok))
        if k not in pools2:
            pools2[k] = np.flatnonzero((DEC2[:, t] == d) & ~Mx.TRIG[:, t] & ok[:, t])
        return pools2[k]
    for typ in RX.TA:
        evs = []
        for s in sorted(ST):
            k, _ = RX.keep_A(ST[s], typ, w0, wE, n)
            evs += [dict(e, sid=s) for e in k]
        evs.sort(key=lambda e: (e["T"], e["sid"]))
        rng1 = np.random.default_rng(RX.SEED); rng2 = np.random.default_rng(RX.SEED)
        R = []
        for e in evs:
            i = Mx.ix[e["sid"]]; T = e["T"]
            j, _, _ = RX.draw_ctl(Mx, i, T, rng1)
            if j is None:
                continue
            d2 = int(DEC2[i, T]); j2 = None
            if d2 >= 0:
                p2 = pool2(T, d2, Mx.OK); p2 = p2[p2 != i]
                if len(p2):
                    j2 = int(p2[int(rng2.integers(len(p2)))])
            r = {"sid": e["sid"], "t": T, "month": cal[T].strftime("%Y-%m")}
            for H in HA:
                for cv, f in (("毛", 1.0), ("扣", 1.0 + C_STK)):
                    tg = e["target"] * f; tc = Mx.C[j, T] * (1.0 + e["dist"]) * f
                    r[f"{cv}_sig_{H}"] = Mx.hit(i, T, H, tg); r[f"{cv}_ctl_{H}"] = Mx.hit(j, T, H, tc)
                    r[f"{cv}_d1_{H}"] = r[f"{cv}_sig_{H}"] - r[f"{cv}_ctl_{H}"]
                    if j2 is not None:
                        tc2 = Mx.C[j2, T] * (1.0 + e["dist"]) * f
                        r[f"{cv}_ctl2_{H}"] = Mx.hit(j2, T, H, tc2); r[f"{cv}_d2_{H}"] = r[f"{cv}_sig_{H}"] - r[f"{cv}_ctl2_{H}"]
                    else:
                        r[f"{cv}_ctl2_{H}"] = np.nan; r[f"{cv}_d2_{H}"] = np.nan
            R.append(r)
        X = pd.DataFrame(R)
        for H in HA:
            row = {"組": "甲", "型": RX.NAME[typ], "H": H}
            for cv in ("毛", "扣"):
                j1 = RX.judge(X.assign(d=X[f"{cv}_d1_{H}"]), cal, w0, H, hitcols=(f"{cv}_sig_{H}", f"{cv}_ctl_{H}"))
                X2 = X[np.isfinite(X[f"{cv}_d2_{H}"])]
                j2 = RX.judge(X2.assign(d=X2[f"{cv}_d2_{H}"]), cal, w0, H, hitcols=(f"{cv}_sig_{H}", f"{cv}_ctl2_{H}"))
                for bn, j in (("基準①", j1), ("基準②", j2)):
                    row.update({f"{cv}_{bn}_D": j.get("D"), f"{cv}_{bn}_lo": j.get("lo"), f"{cv}_{bn}_hi": j.get("hi"), f"{cv}_{bn}_n": j.get("n"),
                                f"{cv}_{bn}_n_eff": j.get("n_eff"), f"{cv}_{bn}_出口": j.get("出口"), f"{cv}_{bn}_結果": j.get("結果")})
            rowsA.append(row)
            if H in (60, 120):
                q = ref["甲"][typ][f"H{H}"]
                gate[f"甲 {RX.NAME[typ]} H{H} ＝ 原件"] = row["毛_基準①_n"] == q["n"] and abs(row["毛_基準①_D"] - q["D"]) < 1e-12
        print(f"  [X 甲 {typ}] {time.time() - t0:.0f}s", flush=True)
    # 乙
    HB = (5, 10, 20, 60)
    EW = {H: RH1.market_ew(ST, n, H) for H in HB}
    CFF = np.vstack([ST[s]["cff"] for s in Mx.sids])
    rowsB = []
    for typ in RX.TB:
        ev = []
        for s in sorted(ST):
            k, _ = RX.keep_B(ST[s], typ, w0, wB, n)
            ev += [(s, g["S"]) for g in k]
        for H in HB:
            okc = Mx.OK40 if H <= RX.FORM_N else Mx.OK
            R = []
            for s, t in ev:
                if t + H > w1:
                    continue
                S = ST[s]; i = Mx.ix[s]
                g = S["cff"][t + H] / S["o"][t + 1] - 1.0
                x1 = g - C_STK - EW[H][t + 1]
                d2 = int(DEC2[i, t]); x2 = np.nan
                if d2 >= 0:
                    cm = (DEC2[:, t] == d2) & okc[:, t]; cm[i] = False
                    gc = CFF[cm, t + H] / Mx.O[cm, t + 1] - 1.0; gc = gc[np.isfinite(gc)]
                    if len(gc):
                        x2 = g - C_STK - float(gc.mean())
                R.append({"sid": s, "t": t, "month": cal[t].strftime("%Y-%m"), "X1": x1, "X2": x2})
            Xb = pd.DataFrame(R).sort_values(["t", "sid"]).reset_index(drop=True)
            row = {"組": "乙", "型": RX.NAME[typ], "H": H}
            for bn, col in (("基準①", "X1"), ("基準②", "X2")):
                Xs = Xb[np.isfinite(Xb[col])]
                for cv, sh in (("扣", 0.0), ("毛", C_STK)):
                    j = RX.judge(Xs.assign(Z=Xs[col] + sh), cal, w0, H, col="Z")
                    row.update({f"{cv}_{bn}_D": j.get("D"), f"{cv}_{bn}_lo": j.get("lo"), f"{cv}_{bn}_hi": j.get("hi"), f"{cv}_{bn}_n": j.get("n"),
                                f"{cv}_{bn}_n_eff": j.get("n_eff"), f"{cv}_{bn}_出口": j.get("出口"), f"{cv}_{bn}_結果": j.get("結果")})
            rowsB.append(row)
            if H == 20:
                q = ref["乙"][typ]["判定"]
                gate[f"乙 {RX.NAME[typ]} H20 ＝ 原件"] = row["扣_基準①_n"] == q["n"] and abs(row["扣_基準①_D"] - q["D"]) < 1e-12
        print(f"  [X 乙 {typ}] {time.time() - t0:.0f}s", flush=True)
    T_ = pd.DataFrame(rowsA + rowsB); T_.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    ok = all(gate.values())
    S = {"件": "PREREGX 型態量幅目標（甲）＋成形前讀法（乙）（seq2）", "閘": gate, "閘過": ok,
         "讀法": "甲：原件 keep_A／Mat／draw_ctl／judge，事件同一批（T ≤ 窗尾−120），達成窗 [T+1, T+H]、區段 H；H 加 5／10／20（60／120 原件已有）；"
                 "扣成本版 ＝ 目標價（事件與對照）× 1.00585（達成率不是報酬 ⇒ 把門檻抬高一個來回成本）；基準② ＝ 對照改抽「T 日近 20 日報酬十分位同格」（其餘池條件、亂數流同原件、另一條流）｜"
                 "乙：原件 keep_B，X ＝ close(S+H)／open(S+1) − 1 − 0.585% − EW_H(S+1)（原件已是扣成本版；毛版 ＝ ＋0.585%）；S+H ≤ 窗尾；"
                 "基準② ＝ S 日近 20 日報酬十分位同格、S+1 可成交且未來窗無斷點（H ≤ 40 用原件 OK40、H60 用 OK120）的全部股票同段報酬平均"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    L = ["# 稽核 第 3 件之 X：PREREGX 型態目標（甲）＋成形前讀法（乙）補視窗＋扣成本＋基準②", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。沿用：甲 H60／H120、乙 H20（閘逐格對過）。", ""]
    posA = [f"{r['型']}H{r['H']}" for r in rowsA if str(r["毛_基準①_結果"]).startswith("結果②")]
    posB = [f"{r['型']}H{r['H']}" for r in rowsB if str(r["扣_基準①_結果"]).startswith("結果②")]
    L.append(f"**結論：甲（達成率差，基準①）測得出（＋）：{'、'.join(posA) or '無'}；乙（扣成本超額，基準①）測得出（＋）：{'、'.join(posB) or '無'}。閘：{'過' if ok else '不過'}。**")
    L += ["", "| 組 | 型 | H | n／n_eff | 基準①（毛）〔CI〕 | 結果 | 扣成本版 結果 | 基準②（毛）〔CI〕 | 結果 | 扣成本版 結果 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rowsA + rowsB:
        f = lambda cv, bn: (f"{r[f'{cv}_{bn}_D'] * 100:+.2f}〔{r[f'{cv}_{bn}_lo'] * 100:+.2f}, {r[f'{cv}_{bn}_hi'] * 100:+.2f}〕" if r.get(f"{cv}_{bn}_D") is not None and np.isfinite(r.get(f"{cv}_{bn}_D")) else "—")
        L.append(f"| {r['組']} | {r['型']} | {r['H']} | {r['毛_基準①_n']}／{r['毛_基準①_n_eff']} | {f('毛', '基準①')} | {r['毛_基準①_出口']} {r['毛_基準①_結果']} | {r['扣_基準①_結果']} | "
                 f"{f('毛', '基準②')} | {r['毛_基準②_出口']} {r['毛_基準②_結果']} | {r['扣_基準②_結果']} |")
    L += ["", "## 讀法與閘", "", f"- {S['讀法']}", f"- 閘：{json.dumps(gate, ensure_ascii=False)}", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(L[4])
    if not ok:
        raise SystemExit("⛔ 閘不過")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["Y", "Rev", "M", "H1", "H2", "U", "X"])
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    {"Y": run_Y, "Rev": run_Rev, "M": run_M, "H1": run_H1, "H2": run_H2, "U": run_U, "X": run_X}.get(a.part, lambda _: print("（尚未實作）"))(a)


if __name__ == "__main__":
    main()

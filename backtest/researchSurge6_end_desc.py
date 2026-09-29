# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：飆股「結束」整理（照起漲端 overlap 的整理方式；⛔ 只描述：不判定、不計 N、不挑格）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_end_desc [--check]

⚠ 結束點 P 是事後才知道的最高點：當下沒有辦法確定那天就是頂。本件只描述「事後回頭看，頂那天長什麼樣」。

═══ 讀法（寫死於 2026-09-29 20:13（台北），在算任何數字之前；協調者 20:1x 更正 ②「不限 14 個」於開算前收到，已直接寫進 W5）═══
 W1 對象：seq6 events（~/s6work/events.npz；2021-01～2026-08、右截斷 2026-08-31），探索＋確認兩段合併
 W2 格：250 格中事件 ≥ 30 的全部格（同 overlap 的 182 格）⛔ 不挑格；逐格算，取格中位數，附 p10～p90
 W3 結束點 ＝ S7 的高點 P（(t, t＋H] 內最高收盤那天，同價取最早）；特徵一律看 P 當天收盤（含）以前可得的資料（同 S1 可得日），沿用 s5work 的 Q／F 表
    P 當天該股若沒有 K 棒（停牌、沿用前收），特徵「沒有值」（照報比例）
 W4 一般股-日對照（同 overlap V5）：兩段內有 K 棒、seq6 右截斷定義域 hdef6 ≥ H 的全部股-日；每個 H 一次，對到該 H 的各格
 W5 ① 涵蓋率 ＝ P 日有此級距的飆股 ÷ P 日此特徵有值的飆股；一般 ＝ 同式在一般股-日；倍數 ＝ 飆股格中位 ÷ 一般格中位
    級距 ＝ seq5 levels()（五等分 Q1～Q5、二元「是」、原門檻級距）；前 20 名只排非「原：」的級距，「原：」門檻版另表全列
 W6 ② 納入重疊的特徵（寫死；⭐ 協調者更正「不限定 14 個」）：飆股涵蓋率格中位 ≥ 10% 且 倍數 ＞ 1 的級距，
    每個「概念」只留涵蓋率最高的一個（同一概念只留一個回看、一個級距），⭐ 全部納入，有幾個就幾個（K）
    概念 ＝ 欄名去掉結尾「_回看」（r_5、r_120 ⇒ r）；原門檻欄對到底層概念：d_lu20→lu、d_att60→att、d_disp60→disp、d_tstreak→tstreak、d_px→price、
    d_K1／d_K1l→kdrun、d_V2l→v2run、d_K3a→rsi14、d_K3b→rsid、d_K5a／d_K5b→turn、d_mkt200→mkt、d_R2a／d_R2b→yoy、d_revhi→d24、d_eps→eps、
    d_gm→gmd、d_opm→opmd、d_bull→maalign、d_ma100→ma、d_shrink→achg、d_V3→v3box、d_X3→x3、d_R1→y3chg、d_K2→bbup、d_K4→tang；d_V1、d_X1、d_X2 各自一個概念
    重疊做法同 overlap（V4）：兩兩 P(B|A)、Jaccard 只在兩個都有值的列算；同時有幾個（0～K 逐個＋至少幾個累計）與組合以「沒有值 ＝ 沒有」算；
    組合 ＝ 完全相同的「有」集合，前 10 名只排非空組合
 W7 ③ 階段 2×2（P 日）：短線急拉 ＝ 5日報酬 Q5 或 F 表 lu_5（近 5 日漲停天數）≥ 1；之前已大漲 ＝ 120日報酬 Q5 或 F 表 lu_20 ≥ 3；沒有值 ＝ 不成立
    另報 t→P 天數（交易日 P−t）與到 P 已漲多少（seq6 事件的 M ＝ P 收盤 ÷ t 收盤 − 1；倍數 ＝ 1＋M），各格中位再取格中位
 W8 ④ 同一批 K 個級距在 P−1、P−3、P−5、P−10（日曆交易日）的飆股涵蓋率；一般股-日不隨位移（同 W4）；另報 P−k ≤ t（位移日已在起漲日當天或之前）的比例
 W9 ⑤ P 隔天 ＝ 該股 P 之後第一根 K 棒 d1（須 ≤ 2026-08-31；另報 d1 ≠ P 的下一個交易日的比例）：
    限價用 research11.limit_price、未還原價（前收 ＝ P 當天或之前最後一根的未還原收盤；2015-06-01 前 7%、之後 10%）；d1 是還原事件日 ⇒ 限價類不判（同 seq5 skip）
    收跌停 ＝ |未還原收 − 跌停價| ＜ 1e−6；盤中碰過跌停 ＝ 未還原低 ≤ 跌停價 ＋ 1e−6；開盤跳空跌 ≥ 3% ＝ 還原開 ÷ P 還原收 − 1 ≤ −3%；
    收跌 ≥ 5% ＝ 還原收 ÷ P 還原收 − 1 ≤ −5%；收黑 ＝ 未還原收 ＜ 未還原開；漲跌 ＝ 還原收 ÷ P 還原收 − 1（格內中位，再取格中位）
    P 後回落 10／20／30／50%：沿用 seq6 events 的 dd10～dd50（S8＋U4b 右截斷）⇒ 觸及比例、P 到觸及天數中位
    一般股-日對照（隔天）：同 W4 的列，隔天同式（不判還原事件日）
 W10 ⑥ 每個特徵標資料類別與可得時點：價／量／技術／規模／大盤／產業 ＝ 當日收盤；法人、融資、借券、注意處置 ＝ 當日盤後公布；
    月營收 ＝ 公布日（最晚次月 10 日）；財報 A2 ＝ A2 可用日（季後）；集保 ＝ 前一週資料
 W11 查核（--check）：抽 2 格，pandas 逐列重算：① 兩個級距涵蓋率＋一般 1 個、② 一對 P(B|A)、③ 2×2 四格、⑤ 收跌停與漲跌中位 ⇒ 對 cells 長表
輸出 backtest/resultsSurge6/end_desc/
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge5_feat as FT
from backtest import research11 as R11

D = S5.D
TIME = "2026-09-29 20:13（台北）"
WORK5 = S5.WORK; WORK6 = os.path.expanduser("~/s6work")
OUT = "backtest/resultsSurge6/end_desc"
HS = list(S5.HS); GS = list(S5.GS); MINEV = 30
SHIFTS = (1, 3, 5, 10)
DMAP = {"d_lu20": "lu", "d_att60": "att", "d_disp60": "disp", "d_tstreak": "tstreak", "d_px": "price", "d_K1": "kdrun", "d_K1l": "kdrun", "d_V2l": "v2run",
        "d_K3a": "rsi14", "d_K3b": "rsid", "d_K5a": "turn", "d_K5b": "turn", "d_mkt200": "mkt", "d_R2a": "yoy", "d_R2b": "yoy", "d_revhi": "d24", "d_eps": "eps",
        "d_gm": "gmd", "d_opm": "opmd", "d_bull": "maalign", "d_ma100": "ma", "d_shrink": "achg", "d_V3": "v3box", "d_X3": "x3", "d_R1": "y3chg", "d_K2": "bbup", "d_K4": "tang"}
AVAIL = {"價": "當日收盤", "量": "當日收盤", "技術": "當日收盤", "規模": "當日收盤", "大盤": "當日收盤", "產業": "當日收盤", "法人": "當日盤後公布", "融資": "當日盤後公布",
         "借券": "當日盤後公布", "注意處置": "當日盤後公布", "營收": "月營收公布日（最晚次月 10 日）", "財報A2": "季報 A2 可用日（季後）", "集保": "前一週資料"}
CAT = {s[0]: s[2] for s in S5.SPECS}


def concept(col):
    return DMAP.get(col, col if col.startswith("d_") else re.sub(r"_\d+$", "", col))


def cname(c):
    return S5.cell_name(c)


def q3(x):
    x = np.asarray(x, float)
    return (float(np.nanmedian(x)), float(np.nanpercentile(x, 10)), float(np.nanpercentile(x, 90))) if np.isfinite(x).any() else (np.nan,) * 3


def load():
    uni = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str)
    D.DATA = S5.ST; cal = D.load_calendar(); n = len(cal)
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    inseg = (mon >= 2021 * 12) & (mon <= 2026 * 12 + 7)
    bar = np.load(os.path.join(WORK5, "bar.npy")); h6 = np.load(os.path.join(WORK6, "hdef6.npy"))
    E = dict(np.load(os.path.join(WORK6, "events.npz")))
    ec = E["cell"].astype(int); cnt = np.bincount(ec, minlength=250)
    cells = [c for c in range(250) if cnt[c] >= MINEV]
    return uni, cal, n, inseg, bar, h6, E, cells, cnt


def pair_stats(P, Dm):
    Pf = P.astype(np.float32); Df = Dm.astype(np.float32)
    both = Pf.T @ Pf; a_bdef = Pf.T @ Df
    union = a_bdef + a_bdef.T - both
    with np.errstate(invalid="ignore", divide="ignore"):
        return both / a_bdef, both / union


def cnt_combo(P):
    k = P.shape[1]; c = P.sum(1)
    dist = np.bincount(c, minlength=k + 1) / max(len(c), 1)
    if len(c) == 0:
        return dist, {}
    pk = np.packbits(P, axis=1)
    v = pk.view(np.dtype((np.void, pk.shape[1]))).ravel()
    u, inv, cc = np.unique(v, return_inverse=True, return_counts=True)
    keys = [bytes(x) for x in u]
    return dist, dict(zip(keys, (cc / len(c)).tolist()))


def run(log):
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = load()
    ec, es, ed, Pv = E["cell"].astype(int), E["s"].astype(int), E["d"].astype(int), E["P"].astype(int)
    assert (Pv < n).all()
    LV = FT.levels()
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")
    rs, rt = np.nonzero(bar & inseg[None, :]); rh = np.minimum(h6[rs, rt].astype(np.int64), 250)
    HC = np.array([HS[c // len(GS)] for c in range(250)])
    Hset = sorted({HC[c] for c in cells})
    log(f"[結束] 合格格 {len(cells)}｜一般股-日 {len(rs):,} 列｜P 日有 K 棒比例 {bar[es, Pv].mean():.4f}")
    # ① 涵蓋率
    fis = sorted({x[0] for x in LV})
    covS = {}; covG = {}; covSh = {}
    for fi in fis:
        q = np.asarray(Qm[fi])
        qe = q[es, Pv].astype(np.int64)
        m = np.bincount(ec * 7 + qe, minlength=250 * 7).reshape(250, 7)
        g = np.bincount(q[rs, rt].astype(np.int64) * 251 + rh, minlength=7 * 251).reshape(7, 251)
        ge = np.cumsum(g[:, ::-1], axis=1)[:, ::-1]
        for lv in [x for x in LV if x[0] == fi]:
            code = lv[2]
            with np.errstate(invalid="ignore", divide="ignore"):
                covS[(fi, code)] = m[:, code] / m[:, 1:].sum(1)
                covG[(fi, code)] = {H: ge[code, H] / ge[1:, H].sum() for H in Hset}
        for k in SHIFTS:
            qk = q[es, np.maximum(Pv - k, 0)].astype(np.int64)
            mk = np.bincount(ec * 7 + qk, minlength=250 * 7).reshape(250, 7)
            for lv in [x for x in LV if x[0] == fi]:
                with np.errstate(invalid="ignore", divide="ignore"):
                    covSh[(fi, lv[2], k)] = mk[:, lv[2]] / mk[:, 1:].sum(1)
    log(f"[①] 涵蓋率完成 {time.time() - T0:.0f}s")
    C1 = []
    for lv in LV:
        fi, col, code = lv[0], lv[1], lv[2]
        s = q3(covS[(fi, code)][cells]); g = q3([covG[(fi, code)][HC[c]] for c in cells])
        C1.append({"特徵": FT.lvname(lv) if hasattr(FT, "lvname") else f"{lv[4]}｜{lv[3]}", "欄": col, "碼": code, "概念": concept(col), "原門檻": col.startswith("d_"),
                   "類別": CAT.get(col, ""), "可得時點": AVAIL.get(CAT.get(col, ""), ""), "飆股涵蓋率 中位": s[0], "p10": s[1], "p90": s[2], "一般 中位": g[0],
                   "倍數": s[0] / g[0] if g[0] > 0 else np.nan})
    C1 = pd.DataFrame(C1); C1.to_csv(os.path.join(OUT, "coverage_all.csv"), index=False, float_format="%.5g")
    top20 = C1[~C1["原門檻"]].sort_values("飆股涵蓋率 中位", ascending=False).head(20)
    top20.to_csv(os.path.join(OUT, "coverage_top20.csv"), index=False, float_format="%.5g")
    C1[C1["原門檻"]].to_csv(os.path.join(OUT, "coverage_original.csv"), index=False, float_format="%.5g")
    # ② 納入
    cand = C1[(C1["飆股涵蓋率 中位"] >= 0.10) & (C1["倍數"] > 1)].sort_values("飆股涵蓋率 中位", ascending=False)
    SEL = cand.drop_duplicates("概念", keep="first").reset_index(drop=True)
    K = len(SEL)
    SEL.to_csv(os.path.join(OUT, "selected.csv"), index=False, float_format="%.5g")
    log(f"[②] 納入 {K} 個（候選 {len(cand)} 個級距）")
    FXc = {c: i for i, c in enumerate(S5.FCOL)}
    Qsel = np.stack([np.asarray(Qm[FXc[c]]) for c in SEL["欄"]])                   # (K, S, n)
    codes = SEL["碼"].to_numpy(np.int8)
    SUR = {}
    for c in cells:
        k = np.flatnonzero(ec == c); q = Qsel[:, es[k], Pv[k]].T
        P_, Dm = q == codes[None, :], q > 0
        pba, jac = pair_stats(P_, Dm); dist, combo = cnt_combo(P_)
        SUR[c] = {"pba": pba, "jac": jac, "dist": dist, "combo": combo}
    GEN = {}
    for H in Hset:
        m_ = rh >= H; q = Qsel[:, rs[m_], rt[m_]].T
        P_, Dm = q == codes[None, :], q > 0
        pba, jac = pair_stats(P_, Dm); dist, combo = cnt_combo(P_)
        GEN[H] = {"pba": pba, "jac": jac, "dist": dist, "combo": combo}
    log(f"[②] 重疊完成 {time.time() - T0:.0f}s")
    names = SEL["特徵"].tolist()
    PR = []
    for a in range(K):
        for b in range(K):
            if a == b:
                continue
            x1 = q3([SUR[c]["pba"][a, b] for c in cells]); x2 = q3([SUR[c]["jac"][a, b] for c in cells])
            x3 = q3([GEN[HC[c]]["pba"][a, b] for c in cells]); x4 = q3([GEN[HC[c]]["jac"][a, b] for c in cells])
            PR.append({"A": names[a], "B": names[b], "飆股 P(B|A) 中位": x1[0], "p10": x1[1], "p90": x1[2], "飆股 Jaccard 中位": x2[0], "J p10": x2[1], "J p90": x2[2],
                       "一般 P(B|A) 中位": x3[0], "一般 J 中位": x4[0], "倍數": x1[0] / x3[0] if x3[0] > 0 else np.nan})
    PR = pd.DataFrame(PR); PR.to_csv(os.path.join(OUT, "pairs.csv"), index=False, float_format="%.5g")
    DI = []
    for i in range(K + 1):
        x = q3([SUR[c]["dist"][i] for c in cells]); y = q3([GEN[HC[c]]["dist"][i] for c in cells])
        xa = q3([SUR[c]["dist"][i:].sum() for c in cells]); ya = q3([GEN[HC[c]]["dist"][i:].sum() for c in cells])
        DI.append({"同時有幾個": i, "飆股 中位": x[0], "飆股 p10": x[1], "飆股 p90": x[2], "一般 中位": y[0], "至少幾個 飆股 中位": xa[0], "至少 p10": xa[1], "至少 p90": xa[2], "至少幾個 一般 中位": ya[0]})
    DI = pd.DataFrame(DI); DI.to_csv(os.path.join(OUT, "count_dist.csv"), index=False, float_format="%.5g")
    allm = set()
    for c in cells:
        allm |= {m for m in SUR[c]["combo"] if any(m)}
    CB = []
    for m in allm:
        xs = [SUR[c]["combo"].get(m, 0.0) for c in cells]; ys = [GEN[HC[c]]["combo"].get(m, 0.0) for c in cells]
        bits = np.unpackbits(np.frombuffer(m, np.uint8))[:K]
        CB.append({"組合": "＋".join(names[i] for i in range(K) if bits[i]), "特徵數": int(bits.sum()), "飆股 中位": float(np.median(xs)), "飆股 p10": float(np.percentile(xs, 10)),
                   "飆股 p90": float(np.percentile(xs, 90)), "一般 中位": float(np.median(ys)), "飆股÷一般": float(np.median(xs)) / float(np.median(ys)) if np.median(ys) > 0 else np.nan})
    CB = pd.DataFrame(CB).sort_values(["飆股 中位", "飆股 p90"], ascending=False)
    CB.head(50).to_csv(os.path.join(OUT, "combos_top50.csv"), index=False, float_format="%.5g")
    # ③ 階段
    q5r = np.asarray(Qm[FXc["r_5"]]); q120 = np.asarray(Qm[FXc["r_120"]])
    lu5 = np.asarray(Fm[FXc["lu_5"]]); lu20 = np.asarray(Fm[FXc["lu_20"]])

    def quad(s_, t_):
        a = (q5r[s_, t_] == 5) | (np.nan_to_num(lu5[s_, t_], nan=0) >= 1)
        b = (q120[s_, t_] == 5) | (np.nan_to_num(lu20[s_, t_], nan=0) >= 3)
        return np.array([(a & b).mean(), (a & ~b).mean(), (~a & b).mean(), (~a & ~b).mean()]) if len(s_) else np.full(4, np.nan)
    QS = {c: quad(es[ec == c], Pv[ec == c]) for c in cells}
    QG = {H: quad(rs[rh >= H], rt[rh >= H]) for H in Hset}
    QN = ["短線急拉＋之前已大漲", "只有短線急拉", "只有之前已大漲", "兩者皆非"]
    ST = []
    for i, nm in enumerate(QN):
        x = q3([QS[c][i] for c in cells]); y = q3([QG[HC[c]][i] for c in cells])
        ST.append({"P 日狀態": nm, "飆股 中位": x[0], "p10": x[1], "p90": x[2], "一般 中位": y[0], "倍數": x[0] / y[0] if y[0] > 0 else np.nan})
    ST = pd.DataFrame(ST); ST.to_csv(os.path.join(OUT, "stage_2x2.csv"), index=False, float_format="%.5g")
    days = q3([np.median(Pv[ec == c] - ed[ec == c]) for c in cells]); gain = q3([np.median(E["M"][ec == c]) for c in cells])
    TP = {"t→P 天數（格中位）": days, "到 P 已漲（M，格中位）": gain, "到 P 倍數（1＋M，格中位）": tuple(1 + x for x in gain)}
    # ④ 位移
    SH = []
    for _, r in SEL.iterrows():
        fi = S5.FIX[r["欄"]]; code = int(r["碼"])
        row = {"特徵": r["特徵"], "P 日": r["飆股涵蓋率 中位"], "一般": r["一般 中位"]}
        for k in SHIFTS:
            row[f"P−{k}"] = q3(covSh[(fi, code, k)][cells])[0]
        SH.append(row)
    SH = pd.DataFrame(SH)
    early = {k: float(np.median([np.mean(Pv[ec == c] - k <= ed[ec == c]) for c in cells])) for k in SHIFTS}
    SH.to_csv(os.path.join(OUT, "shift_coverage.csv"), index=False, float_format="%.5g")
    log(f"[③④] 完成 {time.time() - T0:.0f}s")
    # ⑤ P 隔天
    ND = nextday_table(uni, cal, n, bar, es, Pv, log)
    NX = ["收跌停", "盤中碰跌停", "開盤跳空跌≥3%", "收跌≥5%", "收黑"]
    NDc = []
    for c in cells:
        k = np.flatnonzero(ec == c); v = ND[k]
        ok = np.isfinite(v[:, 5]); okl = ok & np.isfinite(v[:, 0])
        r = {"格": cname(c), "事件": len(k), "有隔天": float(ok.mean()), "隔天非下一交易日": float(np.nanmean(v[ok, 6])) if ok.any() else np.nan}
        for i, nm in enumerate(NX):
            mm = okl if i < 2 else ok
            r[nm] = float(np.nanmean(v[mm, i])) if mm.any() else np.nan
        r["漲跌中位"] = float(np.nanmedian(v[ok, 5])) if ok.any() else np.nan
        for x in (10, 20, 30, 50):
            hv = E[f"dd{x}"][k]; r[f"回落{x}%比例"] = float((hv > 0).mean()); r[f"回落{x}%中位天數"] = float(np.median(hv[hv > 0])) if (hv > 0).any() else np.nan
        NDc.append(r)
    NDc = pd.DataFrame(NDc); NDc.to_csv(os.path.join(OUT, "nextday_cells.csv"), index=False, float_format="%.6g")
    GND = general_nextday(uni, cal, n, bar, inseg, h6, Hset, log)
    NS = []
    for col in ["收跌停", "盤中碰跌停", "開盤跳空跌≥3%", "收跌≥5%", "收黑", "漲跌中位"] + [f"回落{x}%比例" for x in (10, 20, 30, 50)] + [f"回落{x}%中位天數" for x in (10, 20, 30, 50)]:
        x = q3(NDc[col]); y = q3([GND[HC[c]].get(col, np.nan) for c in cells]) if col in GND[Hset[0]] else (np.nan,) * 3
        NS.append({"項目": col, "飆股 中位": x[0], "p10": x[1], "p90": x[2], "一般 中位": y[0]})
    NS = pd.DataFrame(NS); NS.to_csv(os.path.join(OUT, "nextday.csv"), index=False, float_format="%.5g")
    # 各格長表（查核用）
    CL = []
    for c in cells:
        for j, r in SEL.iterrows():
            CL.append({"格": cname(c), "項": "涵蓋率", "特徵": r["特徵"], "值": covS[(S5.FIX[r["欄"]], int(r["碼"]))][c], "一般": covG[(S5.FIX[r["欄"]], int(r["碼"]))][HC[c]]})
        for i, nm in enumerate(QN):
            CL.append({"格": cname(c), "項": "階段", "特徵": nm, "值": QS[c][i], "一般": QG[HC[c]][i]})
        if K >= 2:
            CL.append({"格": cname(c), "項": "P(B|A)", "特徵": f"{names[0]}→{names[1]}", "值": SUR[c]["pba"][0, 1], "一般": GEN[HC[c]]["pba"][0, 1]})
    pd.DataFrame(CL).to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.8g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "P日有K棒比例": float(bar[es, Pv].mean()), "納入重疊的特徵數 K": K, "候選級距數": int(len(cand)),
            "t→P 與漲幅": TP, "位移日已在起漲日或之前的比例（格中位）": early, "警語": "P 是事後才知道的最高點，當下無法確定那天就是頂", "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    page(META, top20, C1[C1["原門檻"]], SEL, PR, DI, CB.head(10), ST, SH, NS)
    log(f"[完] {time.time() - T0:.0f}s")


def _stock_arrays(sid, mk, cal, n):
    st = D.load_stock(sid, mk, cal)
    df = st.df
    cA = df["close"].to_numpy(float); oA = df["open"].to_numpy(float)
    raw = pd.read_csv(os.path.join(S5.ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "open", "low", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rr = {k: np.array(pd.to_numeric(raw[k], errors="coerce"), dtype=float) for k in ("open", "low", "close")}
    for k in rr:
        rr[k][~(rr[k] > 0)] = np.nan
    adj = D.load_adj(sid); evd = np.zeros(n, bool)
    if adj is not None and len(adj):
        for d in adj["date"]:
            p = int(cal.searchsorted(pd.Timestamp(d)))
            if p < n:
                evd[p] = True
    return cA, oA, rr, evd


def _nd(p, bars, cA, oA, rr, evd, cal, t1):
    """p 當天 ⇒ (收跌停, 碰跌停, 跳空跌≥3%, 收跌≥5%, 收黑, 漲跌, 非下一交易日)。"""
    j = int(np.searchsorted(bars, p, side="right"))
    if j >= len(bars) or bars[j] > t1:
        return (np.nan,) * 7
    d1 = int(bars[j]); jb = int(np.searchsorted(bars, p, side="right")) - 1
    if jb < 0:
        return (np.nan,) * 7
    pb = int(bars[jb]); cp = cA[p] if np.isfinite(cA[p]) else cA[pb]
    ret = cA[d1] / cp - 1; gap = oA[d1] / cp - 1
    blk = float(rr["close"][d1] < rr["open"][d1]) if np.isfinite(rr["close"][d1]) and np.isfinite(rr["open"][d1]) else np.nan
    lc, ll = np.nan, np.nan
    pc = rr["close"][pb]
    if not evd[d1] and np.isfinite(pc) and np.isfinite(rr["close"][d1]):
        lp = R11.limit_price(pc, False, 0.07 if cal[d1] < pd.Timestamp("2015-06-01") else 0.10)
        lc = float(abs(rr["close"][d1] - lp) < 1e-6)
        ll = float(rr["low"][d1] <= lp + 1e-6) if np.isfinite(rr["low"][d1]) else np.nan
    return (lc, ll, float(gap <= -0.03) if np.isfinite(gap) else np.nan, float(ret <= -0.05) if np.isfinite(ret) else np.nan, blk, ret, float(d1 != p + 1))


def nextday_table(uni, cal, n, bar, es, Pv, log):
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    out = np.full((len(es), 7), np.nan)
    for s in np.unique(es):
        ii = np.flatnonzero(es == s)
        cA, oA, rr, evd = _stock_arrays(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal, n)
        bars = np.flatnonzero(bar[s]); memo = {}
        for i in ii:
            p = int(Pv[i])
            if p not in memo:
                memo[p] = _nd(p, bars, cA, oA, rr, evd, cal, t1)
            out[i] = memo[p]
    log("[⑤] 飆股隔天完成")
    return out


def general_nextday(uni, cal, n, bar, inseg, h6, Hset, log):
    """一般股-日隔天（W9）：逐股向量化；依 hdef6 ≥ H 分 H 彙總。"""
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    NB = 251; acc = {k: np.zeros(NB) for k in ("n", "nl", "lc", "ll", "gap", "r5", "blk")}; rets = []
    for s in range(len(uni)):
        bars = np.flatnonzero(bar[s])
        if len(bars) < 2:
            continue
        p = bars[:-1]; d1 = bars[1:]
        keep = inseg[p] & (d1 <= t1)
        if not keep.any():
            continue
        p, d1 = p[keep], d1[keep]
        cA, oA, rr, evd = _stock_arrays(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal, n)
        h = np.minimum(h6[s, p].astype(np.int64), 250)
        ret = cA[d1] / cA[p] - 1; gap = oA[d1] / cA[p] - 1
        ok = np.isfinite(ret)
        pc = rr["close"][p]; okl = ok & ~evd[d1] & np.isfinite(pc) & np.isfinite(rr["close"][d1])
        lp = np.array([R11.limit_price(x, False, 0.07 if cal[d] < pd.Timestamp("2015-06-01") else 0.10) if o else np.nan for x, d, o in zip(pc, d1, okl)])
        lc = okl & (np.abs(rr["close"][d1] - lp) < 1e-6); ll = okl & (rr["low"][d1] <= lp + 1e-6)
        blk = ok & (rr["close"][d1] < rr["open"][d1])
        for k, v in (("n", ok), ("nl", okl), ("lc", lc), ("ll", ll), ("gap", ok & (gap <= -0.03)), ("r5", ok & (ret <= -0.05)), ("blk", blk)):
            acc[k] += np.bincount(h[v], minlength=NB)
        rets.append(np.c_[h[ok], ret[ok]])
    R = np.vstack(rets)
    ge = {k: np.cumsum(v[::-1])[::-1] for k, v in acc.items()}
    out = {}
    for H in Hset:
        out[H] = {"收跌停": ge["lc"][H] / ge["nl"][H], "盤中碰跌停": ge["ll"][H] / ge["nl"][H], "開盤跳空跌≥3%": ge["gap"][H] / ge["n"][H],
                  "收跌≥5%": ge["r5"][H] / ge["n"][H], "收黑": ge["blk"][H] / ge["n"][H], "漲跌中位": float(np.median(R[R[:, 0] >= H, 1]))}
    log("[⑤] 一般股-日隔天完成")
    return out


P_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.1f}%"
X_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.2f}"


def page(META, top20, orig, SEL, PR, DI, CB, ST, SH, NS):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.hm td,.hm th{font-size:11px;padding:3px 4px;text-align:center}.hm th.r{writing-mode:vertical-rl;white-space:nowrap}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
    K = len(SEL); tp = META["t→P 與漲幅"]
    st = ST.set_index("P 日狀態"); ns = NS.set_index("項目")
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>飆股結束整理</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股漲到最高那天長什麼樣？（2021–2026-08）</h1>",
         "<p class='warn'>⚠ 最高那天（P）是事後才知道的：當下沒有辦法確定那天就是頂。這份只描述「回頭看，頂那天長什麼樣」，不是賣出訊號，也沒有檢定。</p>",
         f"<p class='lead'>{META['合格格數']} 種飆股定義（10～250 天內漲 50%～10 倍以上、事件 ≥ 30 的格）各算一次，取中位數；讀法寫死 {html.escape(META['讀法寫死'])}。</p>",
         "<h2>先講結論</h2><ul>",
         f"<li>從起漲到最高點，中位 {tp['t→P 天數（格中位）'][0]:.0f} 個交易日，漲到 {tp['到 P 倍數（1＋M，格中位）'][0]:.2f} 倍。</li>",
         f"<li>最高那天：「短線急拉＋之前已大漲」占 {P_(st.loc['短線急拉＋之前已大漲', '飆股 中位'])}（一般股票 {P_(st.loc['短線急拉＋之前已大漲', '一般 中位'])}）；"
         f"兩者皆非 {P_(st.loc['兩者皆非', '飆股 中位'])}（一般 {P_(st.loc['兩者皆非', '一般 中位'])}）。</li>",
         f"<li>最常見的單一情況：{html.escape(top20.iloc[0]['特徵'])}，{P_(top20.iloc[0]['飆股涵蓋率 中位'])}（一般 {P_(top20.iloc[0]['一般 中位'])}）。</li>",
         f"<li>隔天：收跌停 {P_(ns.loc['收跌停', '飆股 中位'])}、收跌 ≥5% {P_(ns.loc['收跌≥5%', '飆股 中位'])}、收黑 {P_(ns.loc['收黑', '飆股 中位'])}；"
         f"漲跌中位 {P_(ns.loc['漲跌中位', '飆股 中位'])}（一般 {P_(ns.loc['漲跌中位', '一般 中位'])}）。</li>",
         f"<li>高點後回落 20%：{P_(ns.loc['回落20%比例', '飆股 中位'])}，中位 {ns.loc['回落20%中位天數', '飆股 中位']:.0f} 天；回落 50%：{P_(ns.loc['回落50%比例', '飆股 中位'])}。</li>",
         f"<li>重疊用的特徵：符合「涵蓋率 ≥10%、比一般多、同一概念只留一個」的全部納入，共 <b>{K}</b> 個。</li></ul>"]
    H.append("<h2>一、最高那天最常見的情況（前 20）</h2><div class='wrap'><table><tr><th class='l'>情況</th><th>飆股</th><th>一般</th><th>倍數</th><th>資料何時拿得到</th></tr>")
    for r in top20.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{P_(r['飆股涵蓋率 中位'])}<br><small>{P_(r['p10'])}～{P_(r['p90'])}</small></td><td>{P_(r['一般 中位'])}</td><td>{X_(r['倍數'])}</td><td class='l'><small>{html.escape(r['可得時點'])}</small></td></tr>")
    H.append("</table></div><h3>你給的原門檻版</h3><div class='wrap'><table><tr><th class='l'>情況</th><th>飆股</th><th>一般</th><th>倍數</th></tr>")
    for r in orig.sort_values("飆股涵蓋率 中位", ascending=False).to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{P_(r['飆股涵蓋率 中位'])}</td><td>{P_(r['一般 中位'])}</td><td>{X_(r['倍數'])}</td></tr>")
    H.append("</table></div>")
    H.append(f"<h2>二、這些情況會一起出現嗎？（納入 {K} 個）</h2><p class='note'>格內大字 ＝ 有 A（列）的飆股裡也有 B（欄）的比例；小字 ＝ 一般股票同一對。紅 ＝ 飆股比一般更常一起出現，藍 ＝ 較少。表可左右捲。</p>")
    SH_ = [f"{i + 1}" for i in range(K)]
    H.append("<div class='wrap' style='overflow-x:auto'><table class='hm'><tr><th></th>" + "".join(f"<th>{s}</th>" for s in SH_) + "</tr>")
    Pm = PR.set_index(["A", "B"]); nm = SEL["特徵"].tolist()
    for a in range(K):
        H.append(f"<tr><th class='l'>{a + 1} {html.escape(nm[a][:14])}</th>")
        for b in range(K):
            if a == b:
                H.append("<td style='background:#eee'>—</td>"); continue
            r = Pm.loc[(nm[a], nm[b])]; v, g, ra = r["飆股 P(B|A) 中位"], r["一般 P(B|A) 中位"], r["倍數"]
            lr = math.log2(ra) if np.isfinite(ra) and ra > 0 else 0.0; al = min(1, abs(lr) / 2)
            col = f"rgba(214,64,69,{al:.2f})" if lr > 0 else f"rgba(43,108,176,{al:.2f})"
            H.append(f"<td style='background:{col}'>{v * 100:.0f}<br><small>{g * 100:.0f}</small></td>" if np.isfinite(v) else "<td>—</td>")
        H.append("</tr>")
    H.append("</table></div>")
    H.append("<h3>倍數最高的 30 對</h3><div class='wrap'><table><tr><th class='l'>有 A 也有 B</th><th>飆股</th><th>一般</th><th>倍數</th></tr>")
    for r in PR.sort_values("倍數", ascending=False).head(30).to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['A'])}<br><small>→ {html.escape(r['B'])}</small></td><td>{P_(r['飆股 P(B|A) 中位'])}</td><td>{P_(r['一般 P(B|A) 中位'])}</td><td>{X_(r['倍數'])}</td></tr>")
    H.append("</table></div><p class='note'>完整兩兩表（含 Jaccard、p10～p90）見 pairs.csv。</p>")
    H.append("<h3>同時有幾個</h3><div class='wrap'><table><tr><th>幾個</th><th>剛好（飆股／一般）</th><th>至少（飆股／一般）</th></tr>")
    for r in DI.to_dict("records"):
        H.append(f"<tr><td>{int(r['同時有幾個'])}</td><td>{P_(r['飆股 中位'])}／{P_(r['一般 中位'])}</td><td>{P_(r['至少幾個 飆股 中位'])}／{P_(r['至少幾個 一般 中位'])}</td></tr>")
    H.append("</table></div><h3>最常見的組合（剛好就是這幾個，前 10）</h3><div class='wrap'><table><tr><th class='l'>組合</th><th>飆股</th><th>一般</th><th>倍數</th></tr>")
    for r in CB.to_dict("records"):
        H.append(f"<tr><td class='l'><small>{html.escape(r['組合'])}</small></td><td>{P_(r['飆股 中位'])}</td><td>{P_(r['一般 中位'])}</td><td>{X_(r['飆股÷一般'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>三、最高那天處在什麼階段</h2><p class='note'>短線急拉 ＝ 5 日報酬最高五分之一，或近 5 日有漲停；之前已大漲 ＝ 120 日報酬最高五分之一，或 20 日內漲停 ≥ 3 次。</p><div class='wrap'><table><tr><th class='l'>狀態</th><th>飆股</th><th>一般</th><th>倍數</th></tr>")
    for r in ST.to_dict("records"):
        H.append(f"<tr><td class='l'>{r['P 日狀態']}</td><td>{P_(r['飆股 中位'])}<br><small>{P_(r['p10'])}～{P_(r['p90'])}</small></td><td>{P_(r['一般 中位'])}</td><td>{X_(r['倍數'])}</td></tr>")
    H.append(f"</table></div><p class='note'>起漲到最高：中位 {tp['t→P 天數（格中位）'][0]:.0f} 天（各格 p10～p90：{tp['t→P 天數（格中位）'][1]:.0f}～{tp['t→P 天數（格中位）'][2]:.0f}）；已漲 {P_(tp['到 P 已漲（M，格中位）'][0])}。</p>")
    H.append("<h2>四、提早幾天看得到？</h2><p class='note'>同一批特徵在最高點前 1、3、5、10 天的出現比例；若只有 P 日特別高，就是到最後一天才出現。</p><div class='wrap'><table><tr><th class='l'>特徵</th><th>P−10</th><th>P−5</th><th>P−3</th><th>P−1</th><th>P 日</th><th>一般</th></tr>")
    for r in SH.to_dict("records"):
        H.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td>" + "".join(f"<td>{P_(r[k])}</td>" for k in ("P−10", "P−5", "P−3", "P−1", "P 日", "一般")) + "</tr>")
    H.append("</table></div>")
    H.append("<h2>五、最高那天的隔天，與之後回落</h2><div class='wrap'><table><tr><th class='l'>項目</th><th>飆股（p10～p90）</th><th>一般</th></tr>")
    for r in NS.to_dict("records"):
        f = (lambda x: f"{x:.0f} 天" if np.isfinite(x) else "—") if "天數" in r["項目"] else P_
        H.append(f"<tr><td class='l'>{r['項目']}</td><td>{f(r['飆股 中位'])}<br><small>{f(r['p10'])}～{f(r['p90'])}</small></td><td>{f(r['一般 中位'])}</td></tr>")
    H.append("</table></div><p class='note'>跌停用未還原價與當年漲跌幅限制算；回落是從最高點起算、到 2026-08-31 為止。</p></main></body></html>")
    open(os.path.join(OUT, "飆股結束整理.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, n, inseg, bar, h6, E, cells, cnt = load()
    CL = pd.read_csv(os.path.join(OUT, "cells.csv.gz")); SEL = pd.read_csv(os.path.join(OUT, "selected.csv")); NDc = pd.read_csv(os.path.join(OUT, "nextday_cells.csv"))
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")
    FX = {c: i for i, c in enumerate(json.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"])}
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False); errs = []
    t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    HSl = list(range(10, 251, 10))
    for c in pick:
        nm = f"H{HSl[c // 10]}_g{int(round([0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10][c % 10] * 100))}%"
        k = np.flatnonzero(E["cell"] == c); df = pd.DataFrame({"s": E["s"][k].astype(int), "t": E["d"][k].astype(int), "P": E["P"][k].astype(int)})
        for j in range(min(2, len(SEL))):
            col, code = SEL.loc[j, "欄"], int(SEL.loc[j, "碼"]); q = pd.Series(np.asarray(Qm[FX[col]])[df["s"], df["P"]])
            mine = (q == code).sum() / (q > 0).sum()
            r = CL[(CL["格"] == nm) & (CL["項"] == "涵蓋率") & (CL["特徵"] == SEL.loc[j, "特徵"])].iloc[0]
            if not np.isclose(mine, r["值"], rtol=1e-6):
                errs.append(f"① {nm} {col}：{mine} 檔 {r['值']}")
            if j == 0:
                H = HSl[c // 10]; ss, tt = np.nonzero(bar & inseg[None, :] & (h6 >= H)); qg = np.asarray(Qm[FX[col]])[ss, tt]
                mg = (qg == code).sum() / (qg > 0).sum()
                if not np.isclose(mg, r["一般"], rtol=1e-6):
                    errs.append(f"① 一般 {nm} {col}：{mg} 檔 {r['一般']}")
        if len(SEL) >= 2:
            a = pd.Series(np.asarray(Qm[FX[SEL.loc[0, "欄"]]])[df["s"], df["P"]]); b = pd.Series(np.asarray(Qm[FX[SEL.loc[1, "欄"]]])[df["s"], df["P"]])
            ok = (a > 0) & (b > 0); ha = ok & (a == SEL.loc[0, "碼"]); hb = ok & (b == SEL.loc[1, "碼"])
            mine = (ha & hb).sum() / ha.sum()
            r = CL[(CL["格"] == nm) & (CL["項"] == "P(B|A)")].iloc[0]
            if not np.isclose(mine, r["值"], rtol=1e-5):
                errs.append(f"② {nm}：{mine} 檔 {r['值']}")
        r5 = pd.Series(np.asarray(Qm[FX["r_5"]])[df["s"], df["P"]]); r120 = pd.Series(np.asarray(Qm[FX["r_120"]])[df["s"], df["P"]])
        l5 = pd.Series(np.asarray(Fm[FX["lu_5"]])[df["s"], df["P"]]).fillna(0); l20 = pd.Series(np.asarray(Fm[FX["lu_20"]])[df["s"], df["P"]]).fillna(0)
        A_ = (r5 == 5) | (l5 >= 1); B_ = (r120 == 5) | (l20 >= 3)
        mine = [(A_ & B_).mean(), (A_ & ~B_).mean(), (~A_ & B_).mean(), (~A_ & ~B_).mean()]
        ref = CL[(CL["格"] == nm) & (CL["項"] == "階段")]["值"].to_numpy()
        if not np.allclose(mine, ref, rtol=1e-6):
            errs.append(f"③ {nm}：{mine} 檔 {ref}")
        # ⑤ 自己讀未還原 csv 算收跌停與漲跌中位
        lc = []; rets = []
        for s, g in df.groupby("s"):
            sid, mk = uni.loc[s, "stock_id"], uni.loc[s, "market"]
            raw = pd.read_csv(os.path.join(S5.ST, "stocks", sid + ".csv"), dtype={"date": str}).drop_duplicates("date")
            raw["date"] = pd.to_datetime(raw["date"]); raw = raw.set_index("date").reindex(cal)
            adjc = D.load_stock(sid, mk, cal).df["close"].to_numpy(float)
            adj = D.load_adj(sid); evs = set(pd.to_datetime(adj["date"])) if adj is not None and len(adj) else set()
            bars = np.flatnonzero(bar[s])
            for P in g["P"]:
                nx = bars[bars > P]
                if not len(nx) or nx[0] > t1:
                    continue
                d1 = nx[0]; pb = bars[bars <= P][-1]
                cp = adjc[P] if np.isfinite(adjc[P]) else adjc[pb]
                rets.append(adjc[d1] / cp - 1)
                pc = pd.to_numeric(raw["close"].iloc[pb], errors="coerce"); c1 = pd.to_numeric(raw["close"].iloc[d1], errors="coerce")
                if cal[d1] in evs or not (pc > 0 and c1 > 0):
                    continue
                raw_lp = pc * 0.9; tk = 0.01 if raw_lp < 10 else 0.05 if raw_lp < 50 else 0.1 if raw_lp < 100 else 0.5 if raw_lp < 500 else 1.0 if raw_lp < 1000 else 5.0
                lp = math.ceil(raw_lp / tk - 1e-9) * tk
                lc.append(abs(c1 - lp) < 1e-6)
        r = NDc[NDc["格"] == nm].iloc[0]
        mine = (float(np.mean(lc)), float(np.median(rets)))
        if not np.allclose(mine, (r["收跌停"], r["漲跌中位"]), rtol=1e-5):  # csv 存 6 位有效數字
            errs.append(f"⑤ {nm}：{mine} 檔 {(r['收跌停'], r['漲跌中位'])}")
    out = {"抽格": [f"H{HSl[c // 10]}_g{int(round([0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10][c % 10] * 100))}%" for c in pick], "錯誤數": len(errs), "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] {out}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()

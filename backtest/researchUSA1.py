# -*- coding: utf-8 -*-
"""USREG-A1-1～5（美股大盤／ETF 類五件；美股帳 N）主程式。回測線，2026-10-07（台北）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA1 a3|a4|a1|a2|a5|all [--procs 3]
    獨立查核：~/tw-p16/.venv/bin/python -m backtest.researchUSA1_check　　網頁：-m backtest.researchUSA1_page

登錄：美股策略線 USREG-A1 seq1（sha 4d6b82a0d0fe84c3）＋seq2（cea9cc6132c26f2f）＋seq3（2f26cfea3035d3a7）；裁定 seq308 §三§四、seq309、seq311 §二、seq313 §二。
件三＝researchUSA1_drv.py、件四＝researchUSA1_rev.py、資料／引擎＝researchUSA1_data.py（讀法 D1～D8 寫在該檔開頭）。順序（登錄排程）：三、四 → 一、二 → 五。
台股原件（逐字沿用的部分照 import）：件一 researchLev2（PREREG正2現金 seq3）｜件二 researchLowFreq（擇時三件 seq1）｜件五 researchTri（三態輪動 seq4）。
⚠ 性質：想法來自台股（多數在台股不合格）；美股新資料 ⇒ 可當新證據（裁定 seq308 §三）。

══ 執行者補讀法（⭐ 2026-10-07 台北 02:45 寫死於看任何 A1 數字之前；登錄沒寫清楚處）══
 共通
 P1 段：探索 2007-04-02～2021-12-31｜確認 2022-01-03～2026-09-30（以 1.0 重算）｜早年合成段 E0～2007-03-30（E0 ＝ 該件所有格的訊號都可算之後第一個月初交易日，
    台股 researchLowFreq L1 同法；登錄寫 1990-01，資料 1990-01-02 起、要 200～250 根暖身 ⇒ 約 1991 起）；含 QQQ／QLD 的格早年段從 QQQ 可用後起（「部分段」，之前不可判定）。
 P2 判準基準 ^SP500TR 同窗（D7）；並列「一直抱 SPY」「一直抱 SSO」（各段自己開盤買進、付一次成本、現金不適用）。
 P3 條件出場主臂 ＝ 規則本身（訊號反轉才換、⛔ 無最長天數）；固定 {20, 60, 120, 240} 日只描述：researchUSA1_data.fixed_hold_path（進風險部位當天起抱滿 H 日、
    到期退出，要等下一次「由不成立變成立」才再進）；窗尾仍持有：確認段末（2026-09-30）是否持有風險部位，必報。
 P4 每格參數鄰格全報 ⇒ A1/A2/A5_cells.csv（只有彙總：年化、回落、比值、換手、占比）。
 件一（移植 researchLev2 R1～R19；問一 66 種 × ETF{SPY, QQQ} × 正2{SSO, QLD} ＝ 264 字面格全進挑選池（seq2 QLD 正式）；問二 C1～C4 × X1～X3）
 P5 挑法 ＝ L2.sel_pick（年化 ＞ 同窗 ^SP500TR 的格中比值最高；同分取正2 比例低、再表列序）；沒有 ⇒「照純 SPY」。X3 ＝ 問一挑中的權重（問一正2 0% ⇒ X3 無定義、不進池，台股 R10 主讀法）。
 P6 再平衡：每年第一個交易日（主）；每季、每月描述（挑中格、探索段全池挑一次＋確認段）。判斷 C1～C4 用 J 的 t−1 收盤（L2.cond_series）。
 P7 必報 2008（真實 SSO／QLD：2008-01-02 開盤買進、付成本；挑中格用探索段同一條權益，100 萬在 2007-12-31 收盤）與 2022（同法，確認段）年內最大回落、年底剩多少、谷底。
 P8 假訊號（⛔ 不判）：問一 ＝ 確認段不同持有組合均勻抽 1,000 次（rng 20260927）；問二 ＝ L2 R16 段長打亂 1,000 次（rng 20260928）⇒ p ≥ 5% 加警語。
 件二（移植 researchLowFreq；甲 4 均線 × 正2{SSO, QLD} × {SPY, 現金} ＝ 16｜乙 σ*3 × L2 × 正2 2 × {SPY, 現金} ＝ 24｜丙 持有{SPY, SSO, QLD} × x3 × R2 × D／M ＝ 36）
 P9 指標 ＝ LF.indicators（J 序列、有效 K 棒、月底 ＝ 合併日曆每月最後一個交易日）；乙 σ̂ ＝ LF.lev_sigma，ANN 改 252（√252 年化）；早年用合成正2。
 P10 主問「年化 ＞ 一直抱正2（同段）」：正2 ＝ 該格的正2（SSO 或 QLD；丙 SPY 版對 SSO）；早年段對合成正2。兩段（確認、早年）都多賺 ⇒ 穩；一段 ⇒ 不穩；都沒 ⇒ 沒多賺。
 P11 退化格（seq246）：探索＋早年合計換手 ＜ 2 或同一狀態 ＞ 95% ⇒ 不進挑選；挑法 ＝ 探索段年化最高（同分換手少、再表列序）；假訊號 rng 20260930 1,000 次（LF 同式）。
 件五（移植 researchTri；轉弱 W1～W8、跌深 P1～P7、反彈 U1～U7；A 態 SSO／QLD × B 態 SPY／QQQ／現金 × C 態 SPY／QQQ ＝ 12 版）
 P12 訊號 ＝ T.signals（J 序列；外資、融資三訊號拿掉）；狀態機 T.machine（t−1 判、t 開盤換、B 期間反彈優先）從所有使用中訊號可算的第一天以 A 起跑、連續跑到 2026-09-30。
 P13 第二層 ＝ A1-3 主讀法判「加碼候選」⇒ 加進反彈、「減碼候選」⇒ 加進轉弱；訊號日 ＝ 事件起算日的前一個交易日（起算日開盤就換）。
     第二、三層訊號在自己可算之前一律「不成立」，狀態機起跑日只看第一層（⛔ 不因新層延後起跑；DTWEXBGS 2009 前不可算）。
     第三層 ＝ A1-4 大盤層「通過」的訊號（任一判定視窗；原版用訊號日、確認版用確認日；偵測在 J 序列上做，早年才有值）。
 P14 挑法（乙）探索段年化最高（判定用）、（甲）使用者判準中比值最高（並列）；同分取狀態轉換少、再表列序；確認段 1 格：年化 ＞ ^SP500TR ⇒「只看報酬，贏 S&P 500」＋判準標籤。
 P15 假訊號 ＝ T 原件（確認段狀態序列保留轉換次數與依序狀態、轉換日隨機；rng 20260929；1,000 次）。壓力段 ＝ 早年合成段（A 態用合成正2、SPY 用 J、QQQ 1999-03 起）＋探索段裡真實 2008。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from itertools import product
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSA1_data as A          # noqa: E402
from backtest import researchLev2 as L2              # noqa: E402
from backtest import researchLowFreq as LF           # noqa: E402
from backtest import researchTri as T                # noqa: E402

LOGF = None
HF = (20, 60, 120, 240)
WEIGHTS = [(e, l, 10 - e - l) for e in range(11) for l in range(11 - e)]
TAG_TW = "想法來自台股（多數在台股不合格）"


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


def jdump(obj, name):
    json.dump(obj, open(os.path.join(A.OUT, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))


def setup():
    A.assert_pinned()
    M = A.load_market()
    for k in ("SSO", "QLD"):
        M["O"]["SYN_" + k], M["C"]["SYN_" + k] = A.synth(M, k, A.SPREAD)
        for s in A.SPREAD_SENS:
            M["O"][f"SYN_{k}_s{s}"], M["C"][f"SYN_{k}_s{s}"] = A.synth(M, k, s)
    return M


def segs_main(M):
    p = M["pos"]
    return {"探索": (p[A.EXP[0]], p[A.EXP[1]]), "確認": (p[A.CONF[0]], p[A.CONF[1]])}


def month_start_after(M, i):
    cal = M["cal"]
    for t in range(i + 1, len(cal)):
        if cal[t][:7] != cal[t - 1][:7]:
            return t
    return -1


def early_oc(lev, s=None):
    """早年段的資產對照：SPY ⇒ J（D3）；正2 ⇒ 合成。"""
    sfx = "" if s is None else f"_s{s}"
    return {"SPY": "J", "QQQ": "QQQ", "SSO": "SYN_SSO" + sfx, "QLD": "SYN_QLD" + sfx}


def run_assets(M, assets, W, i0, i1, early=False, s=None, **kw):
    if early:
        mp = early_oc(None, s)
        OC = {a: (M["O"][mp[a]], M["C"][mp[a]]) for a in assets}
        return A.run(M, assets, W, i0, i1, OC=OC, **kw)
    return A.run(M, assets, W, i0, i1, **kw)


def bench_all(M, i0, i1):
    c, m = A.bench(M["C"]["TR"], i0, i1)
    return {"年化": c, "回落": m, "比值": A.ratio(c, m)}


def hold_one(M, a, i0, i1, early=False):
    W = np.ones((i1 - i0 + 1, 1))
    r = run_assets(M, (a,), W, i0, i1, early=early)
    c, m = A.perf(r["eq"])
    return {"年化": c, "回落": m, "比值": A.ratio(c, m), "_eq": r["eq"]}


def switches(W):
    return int(np.sum(np.any(np.abs(W[1:] - W[:-1]) > 1e-12, axis=1)))


# ═════════════════════════════════════════ 件一 ═════════════════════════════════════════
def a1(M):
    t0 = time.time(); cal = M["cal"]; SG = segs_main(M)
    B = {k: bench_all(M, *v) for k, v in SG.items()}
    J = M["C"]["J"]
    cond = L2.cond_series(J)
    rows = []
    for etf, lev, (e, l, cc) in product(A.ETFS, A.LEVS, WEIGHTS):
        for sg, (i0, i1) in SG.items():
            n = i1 - i0 + 1
            r = A.run(M, (etf, lev), L2.q1_W(e, l, n), i0, i1, R=A.reb_mask(cal, i0, i1, "Y"))
            c_, m_ = A.perf(r["eq"])
            rows.append({"段": sg, "ETF": etf, "正2": lev, "ETF%": e * 10, "正2%": l * 10, "現金%": cc * 10, "年化": c_, "回落": m_, "比值": A.ratio(c_, m_),
                         "成本合計": float(r["cst"].sum()), "延後日": r["delay"], "年化>基準": c_ > B[sg]["年化"], "標籤": A.label(c_, m_, B[sg]["年化"], B[sg]["回落"])})
    q1 = pd.DataFrame(rows)
    pool1 = q1[q1["段"] == "探索"].reset_index(drop=True)
    pick1, nb1 = L2.sel_pick(pool1, B["探索"]["年化"], "正2%")
    log(f"[A1-1 問一] 池 {len(pool1)}｜年化>基準 {nb1}｜挑中 {None if pick1 is None else pick1[['ETF', '正2', 'ETF%', '正2%', '現金%']].to_dict()}")
    w13 = None if pick1 is None or pick1["正2%"] == 0 else (int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10))
    rows2, runs2 = [], {}
    for cd, x, etf, lev in product(L2.CONDS, ("X1", "X2", "X3"), A.ETFS, A.LEVS):
        if x == "X1" and etf != "SPY":
            continue
        if x == "X3" and (w13 is None or etf != pick1["ETF"] or lev != pick1["正2"]):
            continue
        for sg, (i0, i1) in SG.items():
            n = i1 - i0 + 1; on = cond[cd][i0:i1 + 1]
            W = L2.q2_W(x, on, n, w13); assets = L2.q2_assets(x, etf, lev)
            r = A.run(M, assets, W, i0, i1, R=A.reb_mask(cal, i0, i1, "Y"))
            c_, m_ = A.perf(r["eq"]); li = list(assets).index(lev)
            is_on = r["held"][:, li] > 0
            sw = int(np.sum(r["exec"][1:] & (is_on[1:] != is_on[:-1])))
            rows2.append({"段": sg, "條件": cd, "換法": x, "ETF": "—" if x == "X1" else etf, "正2": lev, "年化": c_, "回落": m_, "比值": A.ratio(c_, m_),
                          "平均正2權重": float(np.nanmean(r["held"][:, li])), "條件成立占比": float(on.mean()), "轉換次數": sw, "每年轉換": sw / (n / A.ANN),
                          "成本合計": float(r["cst"].sum()), "年化>基準": c_ > B[sg]["年化"], "標籤": A.label(c_, m_, B[sg]["年化"], B[sg]["回落"]),
                          "窗尾持有正2": bool(is_on[-1])})
            runs2[(sg, cd, x, etf if x != "X1" else "SPY", lev)] = (r, on)
    q2 = pd.DataFrame(rows2)
    pool2 = q2[q2["段"] == "探索"].reset_index(drop=True)
    pick2, nb2 = L2.sel_pick(pool2, B["探索"]["年化"], "平均正2權重")
    log(f"[A1-1 問二] 池 {len(pool2)}｜年化>基準 {nb2}｜挑中 {None if pick2 is None else pick2[['條件', '換法', 'ETF', '正2']].to_dict()}")

    def conf_row(df, pk, keys):
        m = df["段"] == "確認"
        for k in keys:
            m &= df[k] == pk[k]
        return df[m].iloc[0]
    S = {"件": "USREG-A1-1 ETF 比例轉換", "性質": TAG_TW, "N": "N_組合 ＋2（美股帳）", "先驗": "⚠ 受污染：本線看過台股 PREREG正2現金 結果；押 問一照純 SPY（約六成）、問二 20 日線類另列（約五成）",
         "基準": B, "問一": {"池": len(pool1), "年化>基準": nb1}, "問二": {"池": len(pool2), "年化>基準": nb2}}
    conf = {}
    if pick1 is not None:
        r1 = conf_row(q1, pick1, ["ETF", "正2", "ETF%", "正2%"])
        S["問一"]["挑中"] = {k: pick1[k] for k in ("ETF", "正2", "ETF%", "正2%", "現金%", "年化", "回落", "比值")}
        conf["問一"] = {"格": f"{pick1['ETF']} {pick1['ETF%']}%＋{pick1['正2']} {pick1['正2%']}%＋現金 {pick1['現金%']}%（每年再平衡）",
                       **{k: r1[k] for k in ("年化", "回落", "比值", "標籤")}}
    else:
        conf["問一"] = {"格": "探索段沒有年化贏 ^SP500TR 的比例 ⇒ 照純 SPY", "標籤": "—"}
    if pick2 is not None:
        r2 = conf_row(q2, pick2, ["條件", "換法", "ETF", "正2"])
        S["問二"]["挑中"] = {k: pick2[k] for k in ("條件", "換法", "ETF", "正2", "年化", "回落", "比值", "平均正2權重", "每年轉換")}
        conf["問二"] = {"格": f"{pick2['條件']}（{L2.COND_TXT[pick2['條件']].replace('0050', 'SPY')}）× {pick2['換法']}（{L2.X_TXT[pick2['換法']]}）× ETF {pick2['ETF']} × {pick2['正2']}",
                       **{k: r2[k] for k in ("年化", "回落", "比值", "標籤", "每年轉換", "窗尾持有正2")}}
    else:
        conf["問二"] = {"格": "探索段沒有年化贏 ^SP500TR 的轉換 ⇒ 照純 SPY", "標籤": "—"}
    S["確認段"] = {"基準": B["確認"], **conf}
    # 並列：一直抱
    S["並列一直抱"] = {sg: {a: {k: v for k, v in hold_one(M, a, *SG[sg]).items() if k != "_eq"} for a in ("SPY", "QQQ", "SSO", "QLD")} for sg in SG}
    # 假訊號（P8）
    q1c = q1[q1["段"] == "確認"].copy()
    q1c["持有"] = [tuple(sorted((a_, w_) for a_, w_ in ((r.ETF, r["ETF%"]), (r.正2, r["正2%"])) if w_ > 0)) for _, r in q1c.iterrows()]
    uniq = q1c.drop_duplicates("持有").reset_index(drop=True)
    draws = np.random.default_rng(20260927).integers(0, len(uniq), 1000)
    lab1 = uniq["標籤"].to_numpy()[draws]
    S["假訊號_問一"] = {"不同持有組合": len(uniq), "p_合格": float(np.mean(lab1 == "合格")), "p_另列": float(np.mean(lab1 == "另列")),
                     "母體合格比例": float(np.mean(uniq["標籤"] == "合格"))}
    if pick2 is not None:
        i0, i1 = SG["確認"]; n = i1 - i0 + 1
        on0 = cond[pick2["條件"]][i0:i1 + 1]
        runs = []; t = 0
        while t < n:
            if on0[t]:
                s_ = t
                while t < n and on0[t]:
                    t += 1
                runs.append(t - s_)
            else:
                t += 1
        k = len(runs); F = n - sum(runs); rng2 = np.random.default_rng(20260928); labs2 = []
        etf2 = pick2["ETF"] if pick2["換法"] != "X1" else "SPY"
        for j in range(1000):
            ln = rng2.permutation(runs); extra = F - max(k - 1, 0)
            cuts = np.sort(rng2.integers(0, extra + 1, k)); gaps = np.diff(np.concatenate([[0], cuts, [extra]]))
            st_ = np.zeros(n, bool); p_ = gaps[0]
            for q in range(k):
                st_[p_:p_ + ln[q]] = True; p_ += ln[q] + gaps[q + 1] + (1 if q < k - 1 else 0)
            r = A.run(M, L2.q2_assets(pick2["換法"], etf2, pick2["正2"]), L2.q2_W(pick2["換法"], st_, n, w13), i0, i1, R=A.reb_mask(cal, i0, i1, "Y"))
            c_, m_ = A.perf(r["eq"]); labs2.append(A.label(c_, m_, B["確認"]["年化"], B["確認"]["回落"]))
        labs2 = np.array(labs2)
        S["假訊號_問二"] = {"成立段數": k, "p_合格": float(np.mean(labs2 == "合格")), "p_另列": float(np.mean(labs2 == "另列"))}
    # 必報 2008／2022（P7）
    rep = []
    for yr, (a, b), sg in (("2008", ("2008-01-02", "2008-12-31"), "探索"), ("2022", ("2022-01-03", "2022-12-30"), "確認")):
        ia, ib = M["pos"][a], M["pos"][b]
        for lev in ("SSO", "QLD", "SPY", "QQQ"):
            r = A.run(M, (lev,), np.ones((ib - ia + 1, 1)), ia, ib)
            rep.append({"年": yr, "對象": f"{lev} 單獨（{a} 開盤買進、付成本）", **A.year_window(r["eq"], cal, ia, ia, ib)})
        i0, i1 = SG[sg]
        if pick1 is not None:
            n = i1 - i0 + 1
            r = A.run(M, (pick1["ETF"], pick1["正2"]), L2.q1_W(int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10), n), i0, i1, R=A.reb_mask(cal, i0, i1, "Y"))
            rep.append({"年": yr, "對象": "問一挑中格（段內同一條權益）", **A.year_window(r["eq"], cal, i0, ia, ib)})
        if pick2 is not None:
            r, _ = runs2[(sg, pick2["條件"], pick2["換法"], pick2["ETF"] if pick2["換法"] != "X1" else "SPY", pick2["正2"])]
            rep.append({"年": yr, "對象": "問二挑中格（段內同一條權益）", **A.year_window(r["eq"], cal, i0, ia, ib)})
    S["必報_2008_2022"] = rep
    # 描述
    desc = []
    for sg, (i0, i1) in SG.items():
        n = i1 - i0 + 1; Bs = B[sg]
        if pick1 is not None:
            e, l = int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10); ast = (pick1["ETF"], pick1["正2"])
            for nm, R_, cash, cost in (("現金 0%", "Y", False, A.COST), ("每季再平衡", "Q", True, A.COST), ("每月再平衡", "M", True, A.COST),
                                       ("成本 0.02%", "Y", True, A.COST_SENS[0]), ("成本 0.10%", "Y", True, A.COST_SENS[1])):
                r = A.run(M, ast, L2.q1_W(e, l, n), i0, i1, R=A.reb_mask(cal, i0, i1, R_), cash=cash, cost=cost)
                c_, m_ = A.perf(r["eq"]); desc.append({"段": sg, "格": "問一", "臂": nm, "年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, Bs["年化"], Bs["回落"])})
            OCn = {a: (M["NO"][a], M["NC"][a]) for a in ast}
            r = A.run(M, ast, L2.q1_W(e, l, n), i0, i1, R=A.reb_mask(cal, i0, i1, "Y"), OC=OCn)
            c_, m_ = A.perf(r["eq"]); cb, mb = A.bench(M["NC"]["TR"], i0, i1)
            desc.append({"段": sg, "格": "問一", "臂": "股息扣 30%（基準同扣）", "年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, cb, mb)})
        if pick2 is not None:
            etf2 = pick2["ETF"] if pick2["換法"] != "X1" else "SPY"; ast = L2.q2_assets(pick2["換法"], etf2, pick2["正2"])
            on = cond[pick2["條件"]][i0:i1 + 1]
            for nm, cash, cost in (("現金 0%", False, A.COST), ("成本 0.02%", True, A.COST_SENS[0]), ("成本 0.10%", True, A.COST_SENS[1])):
                r = A.run(M, ast, L2.q2_W(pick2["換法"], on, n, w13), i0, i1, R=A.reb_mask(cal, i0, i1, "Y"), cash=cash, cost=cost)
                c_, m_ = A.perf(r["eq"]); desc.append({"段": sg, "格": "問二", "臂": nm, "年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, Bs["年化"], Bs["回落"])})
            for H in HF:
                fon, ne = A.fixed_hold_path(on, H)
                r = A.run(M, ast, L2.q2_W(pick2["換法"], fon, n, w13), i0, i1, R=A.reb_mask(cal, i0, i1, "Y"))
                c_, m_ = A.perf(r["eq"])
                desc.append({"段": sg, "格": "問二", "臂": f"固定 {H} 日（描述，⛔ 不當判定對照）", "年化": c_, "回落": m_, "進場次數": ne, "標籤（描述）": A.label(c_, m_, Bs["年化"], Bs["回落"])})
    # 季度、月度全池挑一次（描述）
    for fq in ("Q", "M"):
        qq = []; i0, i1 = SG["探索"]; n = i1 - i0 + 1
        for etf, lev, (e, l, cc) in product(A.ETFS, A.LEVS, WEIGHTS):
            r = A.run(M, (etf, lev), L2.q1_W(e, l, n), i0, i1, R=A.reb_mask(cal, i0, i1, fq))
            c_, m_ = A.perf(r["eq"]); qq.append({"ETF": etf, "正2": lev, "ETF%": e * 10, "正2%": l * 10, "現金%": cc * 10, "年化": c_, "回落": m_, "比值": A.ratio(c_, m_)})
        qp, _ = L2.sel_pick(pd.DataFrame(qq), B["探索"]["年化"], "正2%")
        S[f"描述_{fq}再平衡全池挑"] = None if qp is None else {k: qp[k] for k in ("ETF", "正2", "ETF%", "正2%", "現金%", "年化", "回落")}
    # 早年合成段（描述／壓力）
    early = []
    E1 = M["pos"][A.EARLY_END]
    ma_first = int(np.flatnonzero(np.isfinite(pd.Series(J).rolling(200, min_periods=200).mean().to_numpy()))[0]) + 1
    E0 = month_start_after(M, ma_first); E0q = month_start_after(M, int(np.flatnonzero(np.isfinite(M["C"]["QQQ"]))[0]))
    S["早年段"] = {"E0（SPY／SSO）": cal[E0], "E0（含 QQQ／QLD，部分段）": cal[E0q], "E1": cal[E1], "標": A.SYN_TAG}
    for nm, ast, Wf in ((("問一挑中", None if pick1 is None else (pick1["ETF"], pick1["正2"]), "q1"), ("問二挑中", None if pick2 is None else L2.q2_assets(pick2["換法"], pick2["ETF"] if pick2["換法"] != "X1" else "SPY", pick2["正2"]), "q2"))):
        if ast is None:
            continue
        a0 = E0q if any(x in ("QQQ", "QLD") for x in ast) else E0
        n = E1 - a0 + 1
        for s in (None,) + A.SPREAD_SENS:
            if Wf == "q1":
                W = L2.q1_W(int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10), n)
            else:
                W = L2.q2_W(pick2["換法"], cond[pick2["條件"]][a0:E1 + 1], n, w13)
            r = run_assets(M, ast, W, a0, E1, early=True, s=s, R=A.reb_mask(cal, a0, E1, "Y"))
            c_, m_ = A.perf(r["eq"]); cb, mb = A.bench(M["C"]["TR"], a0, E1)
            early.append({"格": nm, "利差": "0.25%（主）" if s is None else f"{s:.2%}", "起": cal[a0], "迄": cal[E1], "年化": c_, "回落": m_,
                          "^SP500TR 年化": cb, "^SP500TR 回落": mb, "標籤（描述）": A.label(c_, m_, cb, mb), **({"dd": A.dd_info(r["eq"], cal, a0)} if s is None else {})})
    for lev in ("SSO", "QLD"):
        a0 = E0q if lev == "QLD" else E0
        h = hold_one(M, lev, a0, E1, early=True)
        early.append({"格": f"一直抱合成 {lev}", "利差": "0.25%（主）", "起": cal[a0], "迄": cal[E1], "年化": h["年化"], "回落": h["回落"]})
    S["早年合成段（描述）"] = early
    q1.to_csv(os.path.join(A.OUT, "A1_q1_cells.csv"), index=False, encoding="utf-8")
    q2.to_csv(os.path.join(A.OUT, "A1_q2_cells.csv"), index=False, encoding="utf-8")
    pd.DataFrame(desc).to_csv(os.path.join(A.OUT, "A1_desc.csv"), index=False, encoding="utf-8")
    S["秒"] = round(time.time() - t0)
    jdump(S, "A1_summary.json")
    log(f"[A1-1] 確認段 {json.dumps(S['確認段'], ensure_ascii=False, default=str)[:600]}｜{S['秒']}s")
    return S


# ═════════════════════════════════════════ 件二 ═════════════════════════════════════════
def a2(M):
    t0 = time.time(); cal = M["cal"]; N = len(cal); SG = segs_main(M)
    LF.ANN = A.ANN                                       # P9：√252（台股 245）
    G = {"cal": cal, "C": {"0050": M["C"]["J"], "SSO": M["C"]["SSO"], "QLD": M["C"]["QLD"], "SYN_SSO": M["C"]["SYN_SSO"], "SYN_QLD": M["C"]["SYN_QLD"]}}
    I = LF.indicators(G)
    e0 = SG["探索"][0]
    lev_of = {k: np.array(["SYN_" + k] * e0 + [k] * (N - e0), object) for k in A.LEVS}
    g0 = max(I["first_ok"]["hi250"], LF.first_true(np.isfinite(I["ma200"])), 60)
    need = max(I["first_ok"]["M12"], I["first_ok"]["D200"], I["first_ok"]["M6"], I["first_ok"]["M10"], g0, LF.first_true(np.isfinite(LF.lev_sigma(G, "SYN_SSO", 60))))
    E0 = month_start_after(M, need)
    needq = LF.first_true(np.isfinite(LF.lev_sigma(G, "SYN_QLD", 60)))
    E0q = month_start_after(M, needq)
    E1 = M["pos"][A.EARLY_END]
    CELLS = ([("甲", f"{m}_{v}_{lev}") for lev in A.LEVS for m in ("M6", "M10", "M12", "D200") for v in ("a", "b")]
             + [("乙", f"s{s}_L{L}_{v}_{lev}") for lev in A.LEVS for s in (20, 30, 40) for L in (20, 60) for v in ("a", "b")]
             + [("丙", f"{h}_x{x}_{r}_{f}") for h in ("SPY", "SSO", "QLD") for x in (10, 15, 20) for r in ("R1", "R2") for f in ("D", "M")])
    WS = {}
    for fam, key in CELLS:
        p = key.split("_")
        if fam == "甲":
            W, st = LF.W_jia(I, N, p[0], p[1]); lev = p[2]; WS[(fam, key)] = (W, (st == 1).astype(int), None, lev)
        elif fam == "乙":
            lev = p[3]; W, wv = LF.W_yi(I, G, N, int(p[0][1:]), int(p[1][1:]), p[2], lev_of[lev]); WS[(fam, key)] = (W, (np.abs(wv - 1.0) < 1e-12).astype(int), wv, lev)
        else:
            h = p[0]; lev = "SSO" if h in ("SPY", "SSO") else "QLD"
            W, st, evs = LF.W_bing(I, N, "A" if h == "SPY" else "B", int(p[1][1:]), p[2], p[3], g0); WS[(fam, key)] = (W, st, evs, lev)

    def segs_of(lev):
        return {"探索": SG["探索"], "確認": SG["確認"], "早年": ((E0q if lev == "QLD" else E0), E1)}
    # 退化（P11）
    deg = {}
    for (fam, key), (W, st, _, lev) in WS.items():
        ch = 0; ss = []
        for sg in ("探索", "早年"):
            i0, i1 = segs_of(lev)[sg]; ch += switches(W[i0:i1 + 1]); ss.append(np.asarray(st[i0:i1 + 1]))
        s_all = np.concatenate(ss); _, cnt = np.unique(s_all, return_counts=True); top = float(cnt.max() / len(s_all))
        bad = (["換手 ＜ 2"] if ch < 2 else []) + ([f"同一狀態 {top:.1%} ＞ 95%"] if top > 0.95 else [])
        deg[(fam, key)] = "；".join(bad)
    BASE = {}
    for lev in A.LEVS:
        for sg, (i0, i1) in segs_of(lev).items():
            BASE[(lev, sg)] = {"一直抱正2": hold_one(M, lev, i0, i1, early=(sg == "早年")), "SPY": hold_one(M, "SPY", i0, i1, early=(sg == "早年")),
                               "TR": bench_all(M, i0, i1)}
    rows = []; RUNS = {}
    for (fam, key), (W, st, extra, lev) in WS.items():
        for sg, (i0, i1) in segs_of(lev).items():
            r = run_assets(M, ("SPY", lev), W, i0, i1, early=(sg == "早年"))
            c_, m_ = A.perf(r["eq"]); Wd = W[i0:i1 + 1]; n = i1 - i0 + 1; ch = switches(Wd)
            Bx = BASE[(lev, sg)]
            x = {"件": fam, "格": key, "段": sg, "起": cal[i0], "迄": cal[i1], "年化": c_, "回落": m_, "比值": A.ratio(c_, m_), "換手次數": ch, "每年換手": ch / (n / A.ANN),
                 "成本／年": float(np.sum(r["cst"][1:] / np.r_[1.0, r["eq"][:-2]])) / (n / A.ANN) if n > 2 else np.nan,
                 "正2平均比例": float(np.nanmean(Wd[:, 1])), "SPY平均比例": float(np.nanmean(Wd[:, 0])), "現金平均比例": float(np.nanmean(1 - Wd.sum(1))),
                 "狀態占比": float(np.mean(np.asarray(st[i0:i1 + 1]) == 1)), "對基準判準": A.label(c_, m_, Bx["TR"]["年化"], Bx["TR"]["回落"]),
                 "比一直抱正2（點）": (c_ - Bx["一直抱正2"]["年化"]) * 100, "退化": deg[(fam, key)], "窗尾持有正2": bool(Wd[-1, 1] > 0) if np.isfinite(Wd[-1, 1]) else False,
                 **{f"dd_{k}": v for k, v in A.dd_info(r["eq"], cal, i0).items()}}
            if sg == "探索":
                x["2008窗"] = A.year_window(r["eq"], cal, i0, M["pos"]["2008-01-02"], M["pos"]["2009-03-31"])["谷底剩（萬）"]
            if sg == "確認":
                x["2022窗"] = A.year_window(r["eq"], cal, i0, M["pos"]["2022-01-03"], M["pos"]["2022-12-30"])["谷底剩（萬）"]
            if sg == "早年" and i0 <= M["pos"]["2000-01-03"]:
                x["2000～2002窗"] = A.year_window(r["eq"], cal, i0, M["pos"]["2000-01-03"], M["pos"]["2002-12-31"])["谷底剩（萬）"]
            rows.append(x); RUNS[(fam, key, sg)] = r["eq"]
    df = pd.DataFrame(rows)
    PICK, TOP5, Jd, FK, DESC = {}, {}, {}, {}, {}
    for fam in ("甲", "乙", "丙"):
        ex = df[(df["件"] == fam) & (df["段"] == "探索")].copy(); ex["_o"] = range(len(ex))
        TOP5[fam] = ex.sort_values(["年化", "換手次數", "_o"], ascending=[False, True, True]).head(5)[["格", "年化", "回落", "每年換手", "退化"]].to_dict("records")
        ok = ex[ex["退化"].fillna("") == ""]
        PICK[fam] = None if not len(ok) else ok.sort_values(["年化", "換手次數", "_o"], ascending=[False, True, True]).iloc[0]["格"]
    for fam, key in PICK.items():
        if key is None:
            Jd[fam] = {"判定": "依構造不可判定（全部格退化）"}; continue
        W, st, extra, lev = WS[(fam, key)]
        seg = {sg: df[(df["件"] == fam) & (df["格"] == key) & (df["段"] == sg)].iloc[0] for sg in ("探索", "確認", "早年")}
        more = {sg: bool(seg[sg]["年化"] > BASE[(lev, sg)]["一直抱正2"]["年化"]) for sg in ("確認", "早年")}
        read = "穩" if all(more.values()) else ("沒多賺" if not any(more.values()) else ("不穩，只在確認段（2022～2026）有用" if more["確認"] else "不穩，只在早年合成段有用"))
        Jd[fam] = {"格": key, "正2": lev, "多賺": more, "讀法": read, "早年段是部分段（QQQ 起）": lev == "QLD",
                   **{sg: {k: seg[sg][k] for k in ("起", "迄", "年化", "回落", "比值", "每年換手", "對基準判準", "比一直抱正2（點）", "正2平均比例", "狀態占比", "窗尾持有正2")} for sg in ("探索", "確認", "早年")},
                   "一直抱正2": {sg: {k: v for k, v in BASE[(lev, sg)]["一直抱正2"].items() if k != "_eq"} for sg in ("探索", "確認", "早年")},
                   "一直抱SPY": {sg: {k: v for k, v in BASE[(lev, sg)]["SPY"].items() if k != "_eq"} for sg in ("探索", "確認", "早年")},
                   "基準": {sg: BASE[(lev, sg)]["TR"] for sg in ("探索", "確認", "早年")},
                   "早年最慘": {k: seg["早年"][f"dd_{k}"] for k in ("最大回落", "高點日", "谷底日", "100萬在高點_谷底剩（萬）", "回到高點的交易日數")},
                   "2008窗谷底（萬）": seg["探索"].get("2008窗"), "2022窗谷底（萬）": seg["確認"].get("2022窗"), "2000～2002窗谷底（萬）": seg["早年"].get("2000～2002窗")}
        # 假訊號
        rng = np.random.default_rng(20260930); FK[fam] = {}
        for sg in ("確認", "早年"):
            i0, i1 = segs_of(lev)[sg]; Wd = W[i0:i1 + 1]; n = len(Wd)
            chg = np.flatnonzero(np.any(np.abs(Wd[1:] - Wd[:-1]) > 1e-12, axis=1)) + 1
            seqW = [Wd[0]] + [Wd[i] for i in chg]; res = []
            for j in range(1000):
                dd_ = np.sort(rng.choice(np.arange(1, n), size=len(chg), replace=False)) if len(chg) else np.zeros(0, int)
                W2 = np.repeat(seqW[0][None, :], n, axis=0)
                for q_, d_ in enumerate(dd_):
                    W2[d_:] = seqW[q_ + 1]
                res.append(A.perf(run_assets(M, ("SPY", lev), W2, i0, i1, early=(sg == "早年"))["eq"])[0])
            res = np.array(res); real = float(seg[sg]["年化"])
            FK[fam][sg] = {"換手次數": int(len(chg)), "中位": float(np.median(res)), "p（隨機 ≥ 本格）": float(np.mean(res >= real)),
                           "隨機贏一直抱正2比例": float(np.mean(res > BASE[(lev, sg)]["一直抱正2"]["年化"]))}
        # 描述：現金 0%、成本、利差、固定天數
        d = {}
        for sg in ("確認", "早年"):
            i0, i1 = segs_of(lev)[sg]
            d[f"{sg}_現金0%"] = A.perf(run_assets(M, ("SPY", lev), W, i0, i1, early=(sg == "早年"), cash=False)["eq"])
            for cst in A.COST_SENS:
                d[f"{sg}_成本{cst:.2%}"] = A.perf(run_assets(M, ("SPY", lev), W, i0, i1, early=(sg == "早年"), cost=cst)["eq"])
        for s in A.SPREAD_SENS:
            i0, i1 = segs_of(lev)["早年"]
            d[f"早年_利差{s:.2%}"] = A.perf(run_assets(M, ("SPY", lev), W, i0, i1, early=True, s=s)["eq"])
            h = run_assets(M, (lev,), np.ones((i1 - i0 + 1, 1)), i0, i1, early=True, s=s)
            d[f"早年_利差{s:.2%}_一直抱合成正2"] = A.perf(h["eq"])
        if fam in ("甲", "丙"):
            for sg in ("確認", "早年"):
                i0, i1 = segs_of(lev)[sg]; Wd = W[i0:i1 + 1]
                riskcol = 0 if (fam == "丙" and key.startswith("SPY")) else 1
                on = Wd[:, riskcol] > 0; offW = Wd[~on][0] if (~on).any() else np.zeros(2); onW = Wd[on][0] if on.any() else Wd[0]
                for H in HF:
                    fon, ne = A.fixed_hold_path(on, H)
                    W2 = np.where(fon[:, None], onW[None, :], offW[None, :])
                    d[f"{sg}_固定{H}日（描述）"] = A.perf(run_assets(M, ("SPY", lev), W2, i0, i1, early=(sg == "早年"))["eq"]) + (ne,)
        DESC[fam] = d
    S = {"件": "USREG-A1-2 擇時三件", "性質": TAG_TW, "N": "N_組合 ＋3（美股帳）", "先驗": "甲 早年多賺約六成、確認段沒多賺約七成；乙 回落較淺約八成；丙 兩段都沒多賺約六成五（國外文獻；台股結果本線未讀）",
         "格數": {"甲": 16, "乙": 24, "丙": 36}, "窗": {"探索": [cal[SG['探索'][0]], cal[SG['探索'][1]]], "確認": [cal[SG['確認'][0]], cal[SG['確認'][1]]],
                                                     "早年（SPY／SSO）": [cal[E0], cal[E1]], "早年（QLD，部分段）": [cal[E0q], cal[E1]]},
         "丙狀態機起跑": cal[g0], "挑格": PICK, "探索前5": TOP5, "判定": Jd, "假訊號": FK, "描述": DESC,
         "退化格": {f"{a}|{b}": v for (a, b), v in deg.items() if v}, "合成": A.SYN_TAG}
    df.to_csv(os.path.join(A.OUT, "A2_cells.csv"), index=False, encoding="utf-8")
    np.savez_compressed(os.path.join(A.WORK, "a2_eq_picked.npz"), **{f"{f}_{k}_{s}": v for (f, k, s), v in RUNS.items() if PICK.get(f) == k})
    S["秒"] = round(time.time() - t0)
    jdump(S, "A2_summary.json")
    log(f"[A1-2] 挑格 {PICK}｜讀法 " + json.dumps({f: (j.get('讀法'), j.get('確認', {}).get('對基準判準')) for f, j in Jd.items()}, ensure_ascii=False) + f"｜{S['秒']}s")
    return S


# ═════════════════════════════════════════ 件五 ═════════════════════════════════════════
VERS = [(a, b, c) for a in ("SSO", "QLD") for b in ("SPY", "QQQ", "現金") for c in ("SPY", "QQQ")]
ASSETS5 = ("SPY", "QQQ", "LEV")
_P: dict = {}


def weights5(st, ver):
    a, b, c = ver
    W = np.zeros((len(st), 3))
    W[st == 0, 2] = 1.0
    if b != "現金":
        W[st == 1, ASSETS5.index(b)] = 1.0
    W[st == 2, ASSETS5.index(c)] = 1.0
    return W


def _run5(M, W, lev, i0, i1, early=False):
    if early:
        OC = {"SPY": (M["O"]["J"], M["C"]["J"]), "QQQ": (M["O"]["QQQ"], M["C"]["QQQ"]), "LEV": (M["O"]["SYN_" + lev], M["C"]["SYN_" + lev])}
    else:
        OC = {"SPY": (M["O"]["SPY"], M["C"]["SPY"]), "QQQ": (M["O"]["QQQ"], M["C"]["QQQ"]), "LEV": (M["O"][lev], M["C"][lev])}
    return A.run(M, ASSETS5, W, i0, i1, OC=OC)


def seg_stats5(r, st_seg, n):
    c, m = A.perf(r["eq"])
    sw = int(np.sum(st_seg[1:] != st_seg[:-1]))
    out = {"年化": c, "回落": m, "比值": A.ratio(c, m), "狀態轉換": sw, "每年轉換": sw / (n / A.ANN), "每年成本": float(r["cst"].sum()) / (n / A.ANN), "延後": r["delay"]}
    for k, nm in ((0, "A"), (1, "B"), (2, "C")):
        out[f"{nm}占比"] = float(np.mean(st_seg == k))
    out["窗尾狀態"] = "ABC"[int(st_seg[-1])]
    return out


def _cell5(args):
    w, p, u = args
    M, S, s0, SG, B = _P["M"], _P["S"], _P["s0"], _P["SG"], _P["B"]
    st = T.machine(S, w, p, u, s0, len(M["cal"]))
    out = []
    for ver in VERS:
        W = weights5(st, ver)
        for sg, (i0, i1) in SG.items():
            r = _run5(M, W, ver[0], i0, i1)
            x = seg_stats5(r, st[i0:i1 + 1], i1 - i0 + 1)
            out.append({"段": sg, "轉弱": w, "跌深": p, "反彈": u, "A態": ver[0], "B態": ver[1], "C態": ver[2], **x,
                        "年化>基準": x["年化"] > B[sg]["年化"], "使用者判準": A.label(x["年化"], x["回落"], B[sg]["年化"], B[sg]["回落"])})
    return out


def layer_signals(M, N):
    """P13：第二層（A1-3 候選）、第三層（A1-4 大盤層通過）⇒ (額外轉弱, 額外反彈, 訊號 dict, first dict, 說明)。"""
    extraW, extraU, S, first, note = [], [], {}, {}, {}
    p3 = os.path.join(A.OUT, "A3_summary.json"); p4 = os.path.join(A.OUT, "A4_summary.json")
    s3 = json.load(open(p3, encoding="utf-8")); s4 = json.load(open(p4, encoding="utf-8"))
    ev = pd.read_csv(os.path.join(A.WORK, "a3_events_all.csv"))
    for kind, lst in (("加碼候選", extraU), ("減碼候選", extraW)):
        for cell in s3["候選"][kind]:
            fac, end = cell.split(" ")
            g = ev[(ev["因素"] == fac) & (ev["端"] == end) & (ev["版"] == "主")]
            arr = np.zeros(N, bool)
            sp = g["起算位置"].to_numpy(int); sp = sp[(sp >= 1) & (sp < N)]
            arr[sp - 1] = True
            code = f"Y{fac[1:]}{'H' if end in ('高端', '調升') else 'L'}"
            S[code] = arr; first[code] = int(sp.min()) - 1 if len(sp) else N - 1; lst.append(code); note[code] = f"A1-3 {cell}（{kind}）"
    tl = s4.get("第三層（給 A1-5）", [])
    if tl:
        import researchRev as RV
        X = {"dates": M["cal"], **{k.lower(): M[k]["J"] for k in ("O", "H", "L", "C", "V")}, "ro": M["RO"]["J"], "rh": M["RH"]["J"], "rl": M["RL"]["J"], "rc": M["RC"]["J"]}
        X["valid"] = np.isfinite(X["c"]); X["bars"] = np.flatnonzero(X["valid"])
        evs = RV.detect_series(X)
        for code, ver in tl:
            arr = np.zeros(N, bool); top = RV.SIDE[code] == "高"
            for t_, _ in evs[code]:
                d = t_ if ver == "原版" else RV.confirm_day(X["c"], X["valid"], X["h"][t_], X["l"][t_], t_, top, N - 2)
                if d >= 0:
                    arr[d] = True
            nm = f"R_{code}_{'o' if ver == '原版' else 'c'}"
            S[nm] = arr; first[nm] = int(X["bars"][0]) + 250; (extraW if top else extraU).append(nm); note[nm] = f"A1-4 大盤層通過 {RV.NAME[code]}（{ver}）"
    return extraW, extraU, S, first, note


def a5(M, procs):
    t0 = time.time(); cal = M["cal"]; N = len(cal); SG = segs_main(M)
    pos = M["pos"]
    dummy = pd.Series(np.ones(30), index=cal[:30])
    G = {"cal": cal, "pos": pos, "C": {"0050": M["C"]["J"]}, "H": {"0050": M["H"]["J"]}, "L": {"0050": M["L"]["J"]}, "fa": np.full(N, np.nan), "prev": dummy}
    S, first, _ = T.signals(G)
    for k in ("W9", "W10", "U8"):
        S.pop(k); first.pop(k)
    WEAK = [k for k, _ in T.WEAK if k in S]; DEEP = [k for k, _ in T.DEEP]; UP = [k for k, _ in T.UP if k in S]
    s0 = max(first[k] for k in WEAK + DEEP + UP)          # 第一層訊號全部可算的第一天（P12）
    eW, eU, S2, f2, note = layer_signals(M, N)
    S.update(S2); first.update(f2); WEAK += eW; UP += eU   # P13：第二、三層訊號在可算之前一律「不成立」，⛔ 不因它們延後起跑
    B = {k: bench_all(M, *v) for k, v in SG.items()}
    _P.update(M=M, S=S, s0=s0, SG=SG, B=B)
    combos = list(product(WEAK, DEEP, UP))
    rows = []
    with Pool(procs) as pool:
        for out in pool.imap(_cell5, combos, chunksize=8):
            rows += out
    df = pd.DataFrame(rows)
    x_total = len(combos) * len(VERS)
    log(f"[A1-5] 格 {x_total}（轉弱 {len(WEAK)} × 跌深 {len(DEEP)} × 反彈 {len(UP)} × 版 {len(VERS)}）｜{time.time() - t0:.0f}s")
    ex = df[df["段"] == "探索"].reset_index(drop=True); ex["_o"] = range(len(ex))
    pick_b = ex.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0]
    q = ex[(ex["年化"] > B["探索"]["年化"]) & (ex["比值"] >= B["探索"]["比值"])]
    pick_a = q.sort_values(["比值", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0] if len(q) else None
    keyc = ["轉弱", "跌深", "反彈", "A態", "B態", "C態"]

    def cf(pk):
        m = df["段"] == "確認"
        for k in keyc:
            m &= df[k] == pk[k]
        return df[m].iloc[0]
    NM = dict(T.WEAK + T.DEEP + T.UP); NM.update(note)

    def desc(pk):
        return (f"SPY {NM[pk['轉弱']]} ⇒ 換{'現金' if pk['B態'] == '現金' else pk['B態']}｜{NM[pk['跌深']]} ⇒ 抱 {pk['C態']}｜{NM[pk['反彈']]} ⇒ 回 {pk['A態']}").replace("0050", "SPY")
    cb = cf(pick_b)
    Sx = {"件": "USREG-A1-5 三態輪動", "性質": TAG_TW, "N": "N_組合 ＋1（美股帳）", "從x種挑出": x_total, "層": {"第二層": eW, "第三層": [k for k in eU + eW if k.startswith("R_")], "說明": note},
          "訊號": {"轉弱": WEAK, "跌深": DEEP, "反彈": UP, "U1≡U7": bool(np.array_equal(S["U1"], S["U7"]))}, "狀態機起跑": cal[s0], "基準": B,
          "挑法乙": {"格": [pick_b[k] for k in keyc], "白話": desc(pick_b), "探索": {k: pick_b[k] for k in ("年化", "回落", "比值", "每年轉換")},
                  "確認": cb.drop(["段"]).to_dict(), "判定": "只看報酬，贏 S&P 500" if cb["年化"] > B["確認"]["年化"] else "沒有贏 S&P 500",
                  "使用者判準": cb["使用者判準"]},
          "挑法甲": None if pick_a is None else {"格": [pick_a[k] for k in keyc], "白話": desc(pick_a), "探索": {k: pick_a[k] for k in ("年化", "回落", "比值")},
                                                "確認": cf(pick_a).drop(["段"]).to_dict(), "探索合格格數": len(q)}}
    log(f"[A1-5] 挑法乙 {Sx['挑法乙']['白話']}｜確認 {cb['年化']:.4f}／{cb['回落']:.4f}｜{Sx['挑法乙']['判定']}｜{cb['使用者判準']}")
    # 純抱、12 版各自第一名
    PH = {}
    for lev in A.LEVS + ("SPY", "QQQ"):
        PH[lev] = {sg: {k: v for k, v in hold_one(M, lev, *SG[sg]).items() if k != "_eq"} for sg in SG}
    Sx["純抱"] = PH
    six = []
    for ver in VERS:
        e_ = ex[(ex["A態"] == ver[0]) & (ex["B態"] == ver[1]) & (ex["C態"] == ver[2])].sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0]
        c_ = cf(e_)
        six.append({"版": "／".join(ver), "格": "｜".join(e_[k] for k in ("轉弱", "跌深", "反彈")), "探索年化": e_["年化"], "探索回落": e_["回落"], "確認年化": c_["年化"], "確認回落": c_["回落"], "確認判準": c_["使用者判準"]})
    Sx["12版各自探索第一名（描述）"] = six
    Sx["探索前10"] = ex.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).head(10)[keyc + ["年化", "回落", "每年轉換"]].to_dict("records")
    st_b = T.machine(S, pick_b["轉弱"], pick_b["跌深"], pick_b["反彈"], s0, N)
    ver_b = (pick_b["A態"], pick_b["B態"], pick_b["C態"])
    Wb = weights5(st_b, ver_b)
    c0, c1 = SG["確認"]
    rb = _run5(M, Wb, ver_b[0], c0, c1)
    Sx["2022"] = {"輪動": A.year_window(rb["eq"], cal, c0, pos["2022-01-03"], pos["2022-12-30"]),
                  f"純抱{ver_b[0]}": A.year_window(_run5(M, weights5(np.zeros(N, np.int8), ver_b), ver_b[0], c0, c1)["eq"], cal, c0, pos["2022-01-03"], pos["2022-12-30"]),
                  "SPY": A.year_window(hold_one(M, "SPY", c0, c1)["_eq"], cal, c0, pos["2022-01-03"], pos["2022-12-30"])}
    Sx["窗尾狀態（2026-09-30）"] = "ABC"[int(st_b[c1])]
    # 假訊號（P15）
    stc = st_b[c0:c1 + 1]; n = len(stc)
    chg = np.flatnonzero(stc[1:] != stc[:-1]) + 1
    seq = [int(stc[0])] + [int(stc[i]) for i in chg]
    rng = np.random.default_rng(20260929); res = []
    for j in range(1000):
        dd = np.sort(rng.choice(np.arange(1, n), size=len(chg), replace=False))
        s2 = np.full(n, seq[0], np.int8)
        for q_, d_ in enumerate(dd):
            s2[d_:] = seq[q_ + 1]
        full = np.zeros(N, np.int8); full[c0:c1 + 1] = s2
        res.append(A.perf(_run5(M, weights5(full, ver_b), ver_b[0], c0, c1)["eq"]))
    res = np.array(res)
    Sx["假訊號"] = {"轉換次數": int(len(chg)), "p_年化贏基準": float(np.mean(res[:, 0] > B["確認"]["年化"])),
                  f"年化贏純抱{ver_b[0]}比例": float(np.mean(res[:, 0] > PH[ver_b[0]]["確認"]["年化"])),
                  "使用者判準合格比例": float(np.mean([A.label(c_, m_, B["確認"]["年化"], B["確認"]["回落"]) == "合格" for c_, m_ in res]))}
    # 壓力段
    E1 = pos[A.EARLY_END]
    usesq = ver_b[0] == "QLD" or "QQQ" in ver_b[1:]
    a0 = month_start_after(M, max(s0, int(np.flatnonzero(np.isfinite(M["C"]["QQQ"]))[0]) if usesq else s0))
    stress = []
    i08a, i08b = pos["2008-01-02"], pos["2009-03-31"]; e0, e1 = SG["探索"]
    for nm, (a_, b_, early) in (("早年合成段" + ("（部分段：QQQ／QLD 1999-03 起）" if usesq else ""), (a0, E1, True)),
                               ("2000-01～2002-12（合成）", (max(a0, pos["2000-01-03"]), pos["2002-12-31"], True)),
                               ("2008-01～2009-03（真實 ETF，探索段同一條權益）", (i08a, i08b, False))):
        if a_ >= b_:
            continue
        for who in ("輪動", f"純抱{'合成' if early else ''}{ver_b[0]}", "SPY"):
            if early:
                if who == "輪動":
                    eq = _run5(M, Wb, ver_b[0], a_, b_, early=True)["eq"]
                elif who.startswith("純抱"):
                    eq = _run5(M, weights5(np.zeros(N, np.int8), ver_b), ver_b[0], a_, b_, early=True)["eq"]
                else:
                    eq = run_assets(M, ("SPY",), np.ones((b_ - a_ + 1, 1)), a_, b_, early=True)["eq"]
                yw = A.year_window(eq, cal, a_, a_, b_); n_ = b_ - a_ + 1
                stress.append({"期間": nm, "起": cal[a_], "迄": cal[b_], "對象": who, "年化": float(eq[-1] ** (A.ANN / n_) - 1), **yw, **{f"dd_{k}": v for k, v in A.dd_info(eq, cal, a_).items()}})
            else:
                if who == "輪動":
                    eq = _run5(M, Wb, ver_b[0], e0, e1)["eq"]
                elif who.startswith("純抱"):
                    eq = _run5(M, weights5(np.zeros(N, np.int8), ver_b), ver_b[0], e0, e1)["eq"]
                else:
                    eq = hold_one(M, "SPY", e0, e1)["_eq"]
                stress.append({"期間": nm, "起": cal[a_], "迄": cal[b_], "對象": who, **A.year_window(eq, cal, e0, a_, b_)})
    Sx["壓力"] = stress
    # 描述：固定天數（A 態抱滿 H 日）
    fx = {}
    for sg, (i0, i1) in SG.items():
        on = st_b[i0:i1 + 1] == 0
        for H in HF:
            fon, ne = A.fixed_hold_path(on, H)
            st2 = st_b[i0:i1 + 1].copy(); st2[~fon & (st2 == 0)] = 1; st2[fon] = 0
            full = st_b.copy(); full[i0:i1 + 1] = st2
            fx[f"{sg}_固定{H}日"] = A.perf(_run5(M, weights5(full, ver_b), ver_b[0], i0, i1)["eq"]) + (ne,)
    Sx["描述_固定天數（A 態抱滿 H 日；⛔ 不當判定對照）"] = fx
    df.to_csv(os.path.join(A.OUT, "A5_cells.csv.gz"), index=False, encoding="utf-8")
    pd.DataFrame(stress).to_csv(os.path.join(A.OUT, "A5_stress.csv"), index=False, encoding="utf-8")
    np.savez_compressed(os.path.join(A.WORK, "a5_picked.npz"), state=st_b, eq_conf=rb["eq"], null=res)
    Sx["秒"] = round(time.time() - t0)
    jdump(Sx, "A5_summary.json")
    log(f"[A1-5] 假訊號 {Sx['假訊號']}｜{Sx['秒']}s")
    return Sx


def recon(M):
    """seq3 對帳（⛔ 不判）：同一公式套 2007-04-02～2021-12-31，與真實 SSO／QLD（還原收盤）比：年化差、追蹤誤差（日對數報酬差的標準差 × √252）、相關。
    年化差絕對值 ＞ 1 點 ⇒ 結果句加「合成偏差約 x 點」；＞ 費用率 ⇒ 報告標出（裁定 seq311 §二）。"""
    a, b = M["pos"][A.EXP[0]], M["pos"][A.EXP[1]]
    out = {"窗": [A.EXP[0], A.EXP[1]], "公式": "2×r_idx − (DTB3_{t−1}/100＋s)/252 − f/252；SSO 用 ^SP500TR、QLD 用 QQQ 含息", "結果": []}
    for k in A.LEVS:
        for s in (A.SPREAD,) + A.SPREAD_SENS:
            _, Lc = A.synth(M, k, s)
            sy = Lc[a:b + 1] / Lc[a]; re = M["C"][k][a:b + 1] / M["C"][k][a]
            cs = sy[-1] ** (A.ANN / len(sy)) - 1; cr = re[-1] ** (A.ANN / len(re)) - 1
            d1 = np.diff(np.log(sy)); d2 = np.diff(np.log(re))
            pk = lambda x: float(((x - np.maximum.accumulate(x)) / np.maximum.accumulate(x)).min())
            diff = cs - cr
            out["結果"].append({"正2": k, "利差": s, "主": s == A.SPREAD, "合成年化": cs, "真實年化": cr, "年化差（點）": diff * 100,
                              "追蹤誤差（年化）": float(np.std(d1 - d2) * np.sqrt(A.ANN)), "日報酬相關": float(np.corrcoef(d1, d2)[0, 1]),
                              "合成回落": pk(sy), "真實回落": pk(re), "超過1點": bool(abs(diff) > 0.01), "超過費用率": bool(abs(diff) > A.FEE[k])})
    jdump(out, "A0_synth_recon.json")
    log("[對帳 合成 vs 真實] " + "｜".join(f"{r['正2']} s{r['利差']:.2%} 差 {r['年化差（點）']:+.2f} 點 TE {r['追蹤誤差（年化）']:.2%}" for r in out["結果"]))
    return out


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["a1", "a2", "a3", "a4", "a5", "all"])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(A.OUT, exist_ok=True); os.makedirs(A.WORK, exist_ok=True)
    LOGF = os.path.join(A.OUT, "run.log")
    log(f"===== researchUSA1 {a.mode} {A.now_tpe()}（台北）｜資料 {A.DATA_COMMIT[:10]} =====")
    M = setup()
    recon(M)
    modes = ["a3", "a4", "a1", "a2", "a5"] if a.mode == "all" else [a.mode]
    for md in modes:
        if md == "a3":
            from backtest import researchUSA1_drv as DRV
            DRV.run_a3(M, log)
        elif md == "a4":
            from backtest import researchUSA1_rev as REV
            REV.run_a4(M, a.procs, a.limit, log)
        elif md == "a1":
            a1(M)
        elif md == "a2":
            a2(M)
        elif md == "a5":
            a5(M, a.procs)
    json.dump({"資料commit": A.DATA_COMMIT, "資料": M["audit"], "J接點": M["J_splice"], "更新": A.now_tpe()},
              open(os.path.join(A.OUT, "data_audit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()

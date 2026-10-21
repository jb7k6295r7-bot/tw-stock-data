# -*- coding: utf-8 -*-
"""財報品質 seq1【事件層正式跑：Q-A、Q-I 兩格；Q-G 掛起】（台股策略線 登錄 sha fd142bbf73922770，2026-10-20 23:33；裁定 seq407 第二題、seq408 發號、
seq411 §四（一律 fs_xbrl、⛔ fs_hist）、seq412 §四 核准開正式跑：Q-A、Q-I 可判（排序年 4～5 ⚠ 照寫）；Q-G 等資料庫補 GrossProfit／CostOfSales、
⛔ 不改用 fs_hist ⇒ 本檔不跑 Q-G）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsFinQ/freq 不動）；researchFinQ_freq（讀法 F1～F10 寫死、沿用；load_fs、load_filing、delisted_set、dec_select、
   sort_points）、researchIndMom（共用：exright 版、出場、路徑、統計）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_check
輸出 backtest/resultsFinQ/（⛔ 不碰 freq/）：FinQ.json、FinQ_表.csv、by_year.csv、events.csv.gz（逐筆 R、對照、X）、fake_reps.csv、
     recon_freq.csv、exright_diff.csv、先驗.csv、run.log

═══ 讀法（F 標續編；頻率表 F1～F10 原樣沿用，以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 F11 資料快照 ＝ 頻率表當時的 origin/main b5532121f8d8（fs_xbrl、filing_dates、stocks.csv、產業別；唯讀）；價格面板 ＝ 頻率表同一份快取。
     exright 版（裁定 seq412 §三）＝ researchIndMom I11 同一份（進場剔除、出場壞根都用 exright 版）；另用舊口徑逐列重建 freq/picks.csv.gz
     （排序年、代號、已下市、Q-A、Q-I 值、兩格入選、兩格進場狀態）當對帳，任一不同 ⇒ 中止、⛔ 不算報酬；exright 版狀態不同的列照報。
 F12 持有（登錄 §二「5 月第一個交易日開盤買，抱 12 個月」；PTH R2 同式）：出場 ＝ 進場月（5 月）起第 H 個曆月最後交易日收盤（H12 ＝ 次年 4 月底）；
     H ＝ 12 判、6／24 描述（登錄 §四）；逐股出場規則 ＝ researchIndMom I13（壞根前一根強制、下市末根、到期無成交用前一根）；
     出場月超出主世界完整月 ⇒ 不可算（段只收走完：確認段 2022～2025）。R ＝ 出場還原收盤 ÷ e 還原開盤 − 1。
 F13 對照（登錄 §三「同日母體隨機 20 檔同持有平均；扣 0.585%」⇒ 兩邊同扣、X ＝ R − 對照平均 R）：池 ＝ 同排序年 F4 母體（非金融、500 張閘、年報 t 前已上傳）
     ∧ e 進場保留（exright 版）∧ 同 H 的 R 可算；★ 只扣事件股自己；不放回抽 20 檔（不足 ⇒ 全取）；
     種子 default_rng([20261021, 格標(Q-A 1／Q-I 2／假訊號 100＋r), Y, H, crc32(sid)])。
 F14 ⭐ 主 CI ＝ 持有月分群（登錄 §三、裁定 seq408）★ 作法：每筆 X 拆成逐持有月的價值增量 d_τ ＝ [V事件(τ) − V事件(τ−1)] − [V對照(τ) − V對照(τ−1)]
     （V ＝ 相對 e 開盤的買進持有價值、出場後凍結；V對照 ＝ 20 檔平均；τ ＝ 持有的 H 個月底；Σ_τ d_τ ＝ X 恰好成立）；
     se ＝ √Σ_τ u_τ² ÷ N，u_τ ＝ Σ_筆 (d_τ − X̄ ÷ H)（每筆把平均等分到它的 H 個持有月）；n_eff ＝ min(筆數, 段內相異持有月數)（＝頻率表 F7）。
     並報排序年分群（research11.cl_stats，key ＝ 排序年；n_eff ＝ 年數 ＜ 30 ⇒ 依構造不可判定，CI 照列）；兩者結論不同 ⇒ 照寫。
     ①②③ 以 1.96 判（登錄 §三「①／②／③ 兩段分報」，PTH R5 同）；Bonferroni ★ 族 N ＝ 登錄 3 格（Q-G 掛起仍計入，Φ⁻¹(1−0.05/6) ＝ 2.394）用於 seq322 第二條，
     N ＝ 2 並報。n_eff 30～99 ⇒「樣本中等」。
 F15 seq322（researchPTH R6 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ ★「逐持有月平均增量之中位數與 X̄ 同號」；探索、確認各報。
 F16 假訊號臂（登錄 §三「假訊號臂 30 次」；〈二十六〉月頻／年頻 ⇒ 同期同數量隨機股）★：r ＝ 0…29；每個段內排序年 Y：從 F13 池不放回抽「該格該年事件數」檔，
     種子 default_rng([20261021＋r, 格標, Y])；各自照 F13 抽對照（格標 100＋r）、算 X ⇒ F14 持有月分群 ⇒ 結果；x ＝ 落結果② 的次數。
 F17 描述：H6、H24；早年段 2014～2016（2014 依構造無值、2015～2016 在主世界）；每排序年 X̄；入選中已下市家數。
     與 PREREG品質 舊格重疊、Q-A vs Q-I 等價 ＝ 引頻率表（⛔ 不重算）。
 F18 結果句必附：「年頻，每段只有 4～5 個排序年」「原文為美股、多空組合」「單筆層通過 ≠ 組合會贏 0050」；
     本件財報母體 2015 後含已下市（頻率表 F8）⇒ 不附存活者句；本件不用月營收。早年附 researchTurtle.NOTE_EARLY（排序年 2014 在早年世界；本件早年段實際無事件於早年世界）。
     同根兩出場價取較低（seq373）：每筆只有一種出場價 ⇒ 不適用，照寫。固定持有期為登錄照文獻（seq308 照登錄）。
 F19 先驗（登錄 §六）判讀 ★：① 三格中至少一格兩段② ⇒ 只能以已判 2 格判讀（Q-G 補後可能改）；② Q-G 重疊 ⇒ Q-G 掛起、本次不可判讀；
     ③「Q-A 因缺現金流量表或年份不足而不可判」⇒ Q-A 已可判 ⇒ 不中。
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
import time
import zlib
from collections import Counter, defaultdict
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchFinQ_freq as FQ                # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402  共用（⛔ 只 import）
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import researchTurtle as TU                   # noqa: E402

REG_SHA = FQ.REG_SHA
PIN_SHA = "b5532121f8d8d18e52328cae2345cd56220289d0"
OUT = "backtest/resultsFinQ"
FREQ_DIR = FQ.OUT
COST = IMX.COST
Z196 = 1.96
ZB3 = NormalDist().inv_cdf(1 - 0.05 / 6)
ZB2 = NormalDist().inv_cdf(1 - 0.05 / 4)
NCTRL = 20
NFAKE = 30
HS = (6, 12, 24)
CELLS = ("Q-A", "Q-I")
CTAG = {"Q-A": 1, "Q-I": 2}
SEGY = {"探索": list(range(2017, 2022)), "確認": list(range(2022, 2026)), "早年": [2014, 2015, 2016]}
NAME = {"Q-A": "應計最低", "Q-I": "資產成長最慢"}
SENT = ["年頻，每段只有 4～5 個排序年", "原文為美股、多空組合", "單筆層通過 ≠ 組合會贏 0050"]
LOG = IM.LOG
log = IM.log
pct = IMX.pct


def hm_stats(D_, Hm, mkeys, zj=Z196, zb=ZB3):
    """F14：D_ (N, H) 逐筆逐持有月增量；mkeys (N, H) 持有月序號。"""
    N = len(D_)
    if N == 0:
        return {"n": 0, "n_eff": 0, "結果": "依構造不可判定"}
    X = D_.sum(1); m = float(X.mean())
    u = pd.Series((D_ - m / Hm).ravel()).groupby(mkeys.ravel()).sum()
    se = float(np.sqrt((u.to_numpy() ** 2).sum()) / N)
    ng = int(len(u)); ne = int(min(N, ng))
    mm = pd.Series(D_.ravel()).groupby(mkeys.ravel()).mean()
    lo, hi = m - zj * se, m + zj * se
    return {"n": int(N), "群數(持有月)": ng, "n_eff": ne, "X̄": m, "中位": float(np.median(X)), "X勝率": float((X > 0).mean()), "se": se,
            "lo": lo, "hi": hi, "結果": IMX.res_of(lo, hi, ne), "t": m / se if se > 0 else np.nan,
            "bonf_z": zb, "bonf_lo": m - zb * se, "bonf_hi": m + zb * se, "結果_Bonf3": IMX.res_of(m - zb * se, m + zb * se, ne),
            "結果_Bonf2": IMX.res_of(m - ZB2 * se, m + ZB2 * se, ne),
            "逐持有月平均增量之中位": float(mm.median()), "逐月中位與平均同號": bool(np.sign(mm.median()) == np.sign(m)),
            "樣本": "樣本中等" if 30 <= ne < 100 else ("一般" if ne >= 100 else "不足")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    DATA = IMX.pinned_data(PIN_SHA)
    log(f"[資料] 頻率表快照 {PIN_SHA[:12]} ⇒ {DATA}")
    K, finfo = FQ.load_fs(DATA)
    FD = FQ.load_filing(DATA)
    alive, mx_ls = FQ.delisted_set(DATA)
    PIT = IM.load_pit(DATA)
    Zs = {}; EXD = []
    for wn in ("早年", "主"):
        Zo = IMX.aux2(IM.panel_aux(IM.build_panel(wn, a.procs)))
        X = IMX.build_exr(Zo, a.procs)
        Zs[wn] = {"o": Zo, "x": IMX.make_x(Zo, X)}
    mcal = Zs["主"]["o"]["cal"]; MEm, MKm = PF.month_ends(mcal)
    me_of = {(int(y), int(m)): int(p) for p, (y, m) in zip(MEm, MKm)}
    pk = pd.read_csv(os.path.join(FREQ_DIR, "picks.csv.gz"), dtype={"sid": str})
    YD = {}; RECON = []
    for Y in FQ.YEARS:
        wn = "早年" if Y <= 2014 else "主"
        Zo = Zs[wn]["o"]; Zx = Zs[wn]["x"]; cal = Zo["cal"]
        t, e = FQ.sort_points(Zo, Y)
        if t is None:
            continue
        ts_lim = cal[t].normalize() + pd.Timedelta(days=1)
        univ = {}; vals = {c: {} for c in CELLS}
        for i in np.flatnonzero(Zo["G"][:, t] & np.isfinite(Zo["C"][:, t])):               # F4 原樣（價格閘與 BAD／UPL 無關）
            s = Zo["sids"][i]
            ind, _ = PIT.at(s, cal[t])
            if ind == "金融保險":
                continue
            r1 = K.get((s, Y - 1))
            if r1 is None or r1["industry_template"] in FQ.FIN_TPL:
                continue
            f1 = FD.get((s, Y - 1))
            if f1 is None or not (f1[0] < ts_lim):
                continue
            univ[s] = int(i)
            r2 = K.get((s, Y - 2)); f2 = FD.get((s, Y - 2))
            ta1 = r1["total_assets"]; ta2 = r2["total_assets"] if (r2 is not None and f2 is not None and f2[0] < ts_lim) else np.nan
            ni, ocf = r1["net_income_ytd"], r1["operating_cash_flow_ytd"]
            if np.isfinite(ta1) and np.isfinite(ta2) and ta1 > 0 and ta2 > 0:
                vals["Q-I"][s] = ta1 / ta2 - 1.0
                if np.isfinite(ni) and np.isfinite(ocf):
                    vals["Q-A"][s] = (ni - ocf) / ((ta1 + ta2) / 2.0)
        sel = {c: FQ.dec_select(vals[c], low=True)[0] for c in CELLS}
        # F11 對帳（舊口徑）
        mine = []
        for s, i in univ.items():
            mine.append({"排序年": Y, "sid": s, "已下市": s not in alive, "Q-A": vals["Q-A"].get(s, np.nan), "Q-I": vals["Q-I"].get(s, np.nan),
                         "Q-A入選": s in sel["Q-A"], "Q-I入選": s in sel["Q-I"],
                         "Q-A_st": IM.entry_flag(Zo, i, t, e) if s in sel["Q-A"] else "", "Q-I_st": IM.entry_flag(Zo, i, t, e) if s in sel["Q-I"] else ""})
        fm = pk[pk["排序年"] == Y].reset_index(drop=True)
        mi = pd.DataFrame(mine)
        ok = len(fm) == len(mi)
        bad_cols = []
        if ok:
            for c in ("sid", "已下市", "Q-A入選", "Q-I入選"):
                if not (fm[c].astype(str).to_numpy() == mi[c].astype(str).to_numpy()).all():
                    bad_cols.append(c)
            for c in ("Q-A_st", "Q-I_st"):
                if not (fm[c].fillna("").astype(str).to_numpy() == mi[c].astype(str).to_numpy()).all():
                    bad_cols.append(c)
            for c in ("Q-A", "Q-I"):
                f_ = fm[c].to_numpy(float); m_ = mi[c].to_numpy(float)
                if not ((np.isnan(f_) & np.isnan(m_)) | np.isclose(f_, m_, rtol=1e-12, atol=0)).all():
                    bad_cols.append(c)
        RECON.append({"排序年": Y, "頻率表列": len(fm), "本檔列": len(mi), "相同": ok and not bad_cols, "不同欄": "｜".join(bad_cols)})
        if not (ok and not bad_cols):
            raise SystemExit(f"⛔ [{Y}] 頻率表 picks 逐列重建不同：{bad_cols}（{len(fm)} vs {len(mi)}）⇒ 中止、不算報酬")
        # exright 版狀態
        stx = {s: IM.entry_flag(Zx, i, t, e) for s, i in univ.items()}
        for c in CELLS:
            for s in sel[c]:
                so = IM.entry_flag(Zo, univ[s], t, e)
                if so != stx[s]:
                    EXD.append({"排序年": Y, "格": c, "sid": s, "舊": so, "新": stx[s]})
        YD[Y] = {"wn": wn, "t": t, "e": e, "univ": univ, "sel": sel, "stx": stx, "vals": vals}
    log(f"[F11] 頻率表 picks 逐列重建：{len(RECON)} 個排序年全同｜exright 狀態不同 {len(EXD)} 列｜{time.time() - t0:.0f}s")
    # ── 報酬
    EVROWS = []; DM = {}       # DM[(cell, H, Y)] = (D (N,H), mkeys, sids, X, R, Rc)
    POOL = {}
    for Y, yd in YD.items():
        wn = yd["wn"]
        if wn != "主":
            continue
        Zx = Zs["主"]["x"]; t, e = yd["t"], yd["e"]
        for H in HS:
            mons = [((Y * 12 + 4 + k) // 12, (Y * 12 + 4 + k) % 12 + 1) for k in range(H)]
            if mons[-1] not in me_of:
                continue
            taus = np.array([me_of[m] for m in mons]); x = int(taus[-1])
            mk = np.array([y * 12 + m - 1 for y, m in mons])
            pool_s = [s for s, i in yd["univ"].items() if yd["stx"][s] == "保留"]
            ii = np.array([yd["univ"][s] for s in pool_s], np.int64)
            ex, Rv, typ = IMX.exits_vec(Zx, ii, e, x)
            V = IMX.path_val(Zx, ii, e, ex, taus)
            okp = np.isfinite(Rv)
            P = {"sids": [s for s, o in zip(pool_s, okp) if o], "R": Rv[okp], "V": V[okp], "typ": typ[okp], "mk": mk}
            P["ix"] = {s: k for k, s in enumerate(P["sids"])}
            POOL[(Y, H)] = P

    def x_of(Y, H, sids, tag):
        P = POOL[(Y, H)]; out = []
        for s in sids:
            k = P["ix"].get(s)
            if k is None:
                out.append(None); continue
            cand = np.array([q for q in range(len(P["sids"])) if q != k])
            rng = np.random.default_rng([20261021, tag, Y, H, zlib.crc32(s.encode())])
            pick = cand if len(cand) <= NCTRL else rng.choice(cand, NCTRL, replace=False)
            Vc = P["V"][pick].mean(0); Ve = P["V"][k]
            d = np.diff(np.r_[1.0, Ve]) - np.diff(np.r_[1.0, Vc])
            out.append((d, float(P["R"][k]), float(P["R"][pick].mean()), int(P["typ"][k]), len(pick), "|".join(P["sids"][q] for q in pick)))
        return out

    for c in CELLS:
        for Y, yd in YD.items():
            for H in HS:
                if (Y, H) not in POOL:
                    continue
                ev = sorted(s for s in yd["sel"][c] if yd["stx"][s] == "保留")
                res = x_of(Y, H, ev, CTAG[c])
                rows_d = []
                for s, r in zip(ev, res):
                    if r is None:
                        EVROWS.append({"格": c, "排序年": Y, "H": H, "sid": s, "R可算": False}); continue
                    d, Re, Rc, ty, nc, cl = r
                    EVROWS.append({"格": c, "排序年": Y, "H": H, "sid": s, "R可算": True, "R": Re, "對照R": Rc, "X": Re - Rc, "淨R": Re - COST,
                                   "出場": IMX.TYPN[ty], "對照檔數": nc, "對照": cl, "池大小": len(POOL[(Y, H)]["sids"]), "已下市": s not in alive, "Σd−X": float(d.sum() - (Re - Rc))})
                    rows_d.append(d)
                if rows_d:
                    DM[(c, H, Y)] = np.vstack(rows_d)
    EV = pd.DataFrame(EVROWS)
    log(f"[報酬] 事件列 {len(EV)}｜Σd−X 最大誤差 {EV['Σd−X'].abs().max():.2e}｜{time.time() - t0:.0f}s")

    def seg_stats(c, H, ys, D_src):
        mats = [(Y, D_src[(c, H, Y)]) for Y in ys if (c, H, Y) in D_src]
        if not mats:
            return None
        Dm = np.vstack([m for _, m in mats])
        mk = np.vstack([np.broadcast_to(POOL[(Y, H)]["mk"], m.shape) for Y, m in mats])
        st = hm_stats(Dm, H, mk)
        Xv = Dm.sum(1); yk = np.concatenate([[Y] * len(m) for Y, m in mats])
        cy = R.cl_stats(Xv, yk)
        st.update({"年分群_n_eff": int(min(len(Xv), cy["months"])), "年分群_lo": cy["lo"], "年分群_hi": cy["hi"],
                   "年分群_結果": IMX.res_of(cy["lo"], cy["hi"], int(min(len(Xv), cy["months"]))),
                   "年分群_結果(忽略n_eff)": "結果①" if cy["lo"] <= 0 <= cy["hi"] else ("結果②" if cy["lo"] > 0 else "結果③"),
                   "排序年": f"{mats[0][0]}～{mats[-1][0]}", "每年X̄": json.dumps({int(Y): round(float(m.sum(1).mean()), 4) for Y, m in mats})})
        return st

    # ── 假訊號臂（H12 判定）
    FAKE = []
    FDM = {}
    for c in CELLS:
        for r in range(NFAKE):
            for Y, yd in YD.items():
                if (Y, 12) not in POOL:
                    continue
                nev = int(((EV["格"] == c) & (EV["排序年"] == Y) & (EV["H"] == 12) & EV["R可算"]).sum())
                P = POOL[(Y, 12)]
                rng = np.random.default_rng([20261021 + r, CTAG[c], Y])
                ss = list(rng.choice(P["sids"], size=min(nev, len(P["sids"])), replace=False)) if nev else []
                res = x_of(Y, 12, [str(s) for s in ss], 100 + r)
                if res:
                    FDM[(c, r, Y)] = np.vstack([q[0] for q in res if q is not None])
            for sg, ys in SEGY.items():
                if sg == "早年":
                    continue
                src = {(c, 12, Y): FDM[(c, r, Y)] for Y in ys if (c, r, Y) in FDM}
                st = seg_stats(c, 12, ys, src)
                FAKE.append({"格": c, "段": sg, "r": r, "n": st["n"], "n_eff": st["n_eff"], "X̄": st["X̄"], "lo": st["lo"], "hi": st["hi"], "結果": st["結果"]})
    FK = pd.DataFrame(FAKE)
    log(f"[假訊號] 完｜{time.time() - t0:.0f}s")
    # ── 表
    TAB = []
    for c in CELLS:
        for H in HS:
            for sg, ys in SEGY.items():
                st = seg_stats(c, H, ys, DM)
                if st is None:
                    continue
                cell = "判定" if (H == 12 and sg != "早年") else "描述"
                row = {"格": c, "H": H, "段": sg, "身分": cell, **{k: st.get(k) for k in (
                    "排序年", "n", "群數(持有月)", "n_eff", "樣本", "X̄", "中位", "X勝率", "lo", "hi", "結果", "t", "結果_Bonf3", "結果_Bonf2", "bonf_lo",
                    "年分群_n_eff", "年分群_lo", "年分群_hi", "年分群_結果", "年分群_結果(忽略n_eff)", "逐持有月平均增量之中位", "逐月中位與平均同號", "每年X̄")}}
                sub = EV[(EV["格"] == c) & (EV["H"] == H) & EV["排序年"].isin(ys) & EV["R可算"]]
                row["R̄"] = float(sub["R"].mean()); row["對照R̄"] = float(sub["對照R"].mean()); row["入選中已下市"] = int(sub["已下市"].sum())
                row["出場占比"] = json.dumps({k: round(v / len(sub), 4) for k, v in Counter(sub["出場"]).items()}, ensure_ascii=False)
                row["年分群與持有月分群結論不同"] = bool(st["年分群_結果(忽略n_eff)"] != st["結果"])
                if cell == "判定":
                    fk = FK[(FK["格"] == c) & (FK["段"] == sg)]
                    xf = int((fk["結果"] == "結果②").sum()); row["假訊號x(／30)"] = xf
                    row["假訊號X̄中位"] = float(fk["X̄"].median()); row["假訊號X̄p95"] = float(fk["X̄"].quantile(0.95))
                    c322 = {"結果②": st["結果"] == "結果②", "Bonferroni下界>0(N=3)": bool(st["bonf_lo"] > 0), "假訊號x≤1": xf <= 1,
                            "X̄−0.585%>0": bool(st["X̄"] - COST > 0), "逐月中位與平均同號": bool(st["逐月中位與平均同號"])}
                    row["過seq322"] = all(c322.values()); row["seq322各條"] = json.dumps(c322, ensure_ascii=False)
                TAB.append(row)
    TB = pd.DataFrame(TAB)
    BY = EV[EV["R可算"]].groupby(["格", "H", "排序年"]).agg(n=("X", "size"), X̄=("X", "mean"), R̄=("R", "mean"), 對照R̄=("對照R", "mean"),
                                                         已下市=("已下市", "sum")).reset_index()

    def word(r):
        return {"結果②": "多", "結果③": "少", "結果①": "分不出"}.get(r, "依構造不可判定")
    sents = {}
    for c in CELLS:
        jd = TB[(TB["格"] == c) & (TB["身分"] == "判定")].set_index("段")
        sents[c] = (f"每年 4 月底挑{NAME[c]}的一成、抱一年：探索段（{jd.loc['探索', '排序年']}）比隨便買{word(jd.loc['探索', '結果'])} {pct(jd.loc['探索', 'X̄'])}"
                    f"（{jd.loc['探索', '樣本']}）、確認段（{jd.loc['確認', '排序年']}）{word(jd.loc['確認', '結果'])} {pct(jd.loc['確認', 'X̄'])}"
                    f"（{jd.loc['確認', '樣本']}）" + ("；⚠ 排序年分群結論不同" if jd["年分群與持有月分群結論不同"].any() else ""))
    both2 = {c: bool((TB[(TB["格"] == c) & (TB["身分"] == "判定")]["結果"] == "結果②").all()) for c in CELLS}
    PRIOR = [{"先驗": "① 三格中至少一格兩段②（約三成）", "中": any(both2.values()), "實際": "｜".join(f"{c} 兩段②={v}" for c, v in both2.items()) + "（Q-G 掛起；補後可能改）"},
             {"先驗": "② Q-G 與 PREREG品質 Q2 入選重疊 ≥ 50%（約六成）", "中": None, "實際": "Q-G 掛起（fs_xbrl 無毛利），本次不可判讀"},
             {"先驗": "③ Q-A 因缺現金流量表或年份不足而不可判（約四成）", "中": False, "實際": "fs_xbrl 有營業現金流、Q-A 可判（裁定 seq412）"}]
    eqf = pd.read_csv(os.path.join(FREQ_DIR, "equiv.csv")).to_dict("records")
    J = {"性質": "財報品質 seq1 事件層正式跑（Q-A、Q-I；Q-G 掛起）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq407 第二題、seq408、seq411 §四、seq412 §四（Q-G 掛起、品質先判 2 格 N_前段 ＋2）",
         "資料": {"快照": PIN_SHA, "fs_xbrl": finfo, "stocks.csv 最晚 last_seen": mx_ls},
         "判定": TB[TB["身分"] == "判定"].to_dict("records"), "結果句": sents, "必附": SENT, "Q-G": "掛起：fs_xbrl 無毛利／營業成本；⛔ 不改用 fs_hist（seq412 §四）",
         "先驗": PRIOR, "先驗中": sum(1 for p in PRIOR if p["中"] is True), "Q-A_vs_Q-I等價(引頻率表)": eqf,
         "頻率表重建": RECON, "exright差異列": EXD, "seq373": "同根兩出場價取較低：每筆只有一種出場價 ⇒ 不適用，照寫",
         "Z": {"1.96": Z196, "Bonf3": ZB3, "Bonf2": ZB2}, "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
    TB.to_csv(os.path.join(OUT, "FinQ_表.csv"), index=False, encoding="utf-8-sig")
    BY.to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        EV.to_csv(fh, index=False)
    FK.to_csv(os.path.join(OUT, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(RECON).to_csv(os.path.join(OUT, "recon_freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EXD, columns=["排序年", "格", "sid", "舊", "新"]).to_csv(os.path.join(OUT, "exright_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PRIOR).to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "FinQ.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for c in CELLS:
        log(f"[判定] {sents[c]}")
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

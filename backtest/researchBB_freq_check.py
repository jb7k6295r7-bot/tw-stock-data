# -*- coding: utf-8 -*-
"""researchBB_freq 對帳（布林 Method I／II seq1 頻率表乾跑，登錄 sha d5ac888e15ab1418）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBB_freq_check
輸出 backtest/resultsBB/freq/check.json、check.log

C1 抽 20 筆保留事件（主：M1 5、M2 5、M3 2；早年：M1 4、M2 3、M3 1；default_rng(20261018)），逐筆用【日曆 df 逐列手算】
   （⛔ 不呼叫 researchBB_freq 的 boll／mfi／squeeze／detect_*）：T 往前 20 個有成交日的還原收盤 ⇒ 中軌、母體標準差、上下軌、%b、BW；
   往前 11 個有成交日的還原高低收、原始收（csv）、成交量 ⇒ MFI(10)（方向用還原典型價、金額用原始典型價×量）；
   M1：本檔逐根 BW 序列找 [T−20, T−1] 內最近的擠壓日（125 根最低）⇒ 與事件檔擠壓日相符、收 ＞ 上軌、擠壓日到 T 無壞 K 棒；
   M2：%b ＞ 0.8 ∧ MFI ＞ 80 且前一天不成立；M3：本檔獨立轉折低點、%b、MFI 條件與頸線；
   母體（自算 500 張 ∧ 20 日有成交 ∧ pit_valid）；T＋1 可買；高低收同一還原因子。
C2 不前視：同 20 檔，截在 k ⇒ k 仍在；截在 k−1 ⇒ 沒有 k；另每檔 3 個隨機截點：M1、M2、M3 全序列偵測中 ≤ cut 者 ＝ 截斷序列偵測。
C3 指標逐根（擠壓判定同模組相對容差 1e−9）：同 20 檔全序列，模組 boll（中、上、下、BW、%b）／mfi 與本檔逐根迴圈版比對（有值位置相同、相對差 ＜ 1e−9）；%b、MFI 範圍。
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchBB_freq as BB                  # noqa: E402
from backtest import researchWR_freq as WF                  # noqa: E402
from backtest import researchUO_freq as RU                  # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of（⛔ 只 import）
from backtest import researchWR_freq_check as WC            # noqa: E402  gate_chk／adj_chk／next_open_chk（⛔ 只 import）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = BB.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def boll_loop(c, bad, n=20):
    N = len(c); M = np.full(N, np.nan); U = M.copy(); L = M.copy(); BW = M.copy(); PB = M.copy()
    for k in range(n - 1, N):
        if any(bad[j] for j in range(k - n + 2, k + 1)):
            continue
        x = c[k - n + 1:k + 1]; m = sum(x) / n; sd = math.sqrt(sum((v - m) ** 2 for v in x) / n)
        M[k] = m; U[k] = m + 2 * sd; L[k] = m - 2 * sd; BW[k] = 4 * sd / m
        if sd > 0:
            PB[k] = (c[k] - L[k]) / (U[k] - L[k])
    return M, U, L, BW, PB


def mfi_loop(h, l, c, v, rc, bad, n=10):
    N = len(c); out = np.full(N, np.nan); tp = [(h[k] + l[k] + c[k]) / 3 for k in range(N)]
    for k in range(n, N):
        P = Q = 0.0; okk = True
        for j in range(k - n + 1, k + 1):
            if bad[j] or j == 0 or not (np.isfinite(v[j]) and np.isfinite(rc[j]) and rc[j] > 0):
                okk = False; break
            mf = tp[j] / (c[j] / rc[j]) * v[j]
            if tp[j] > tp[j - 1]:
                P += mf
            elif tp[j] < tp[j - 1]:
                Q += mf
        if okk and P + Q > 0:
            out[k] = 100 * P / (P + Q)
    return out


def sq_loop(BW, n=125):
    N = len(BW); sq = np.zeros(N, bool)
    for k in range(n - 1, N):
        w = BW[k - n + 1:k + 1]
        if np.isfinite(w).all() and BW[k] <= w.min() * (1 + BB.SQ_TOL):
            sq[k] = True
    return sq


def piv_loop(c, bad, R=5):
    out = []
    for s in range(R, len(c) - R):
        if all(c[s] < c[j] for j in range(s - R, s)) and all(c[s] < c[j] for j in range(s + 1, s + R + 1)) \
                and not any(bad[j] for j in range(max(s - R + 1, 0), s + R + 1)):
            out.append(s)
    return out


def mod_det(cell, h, l, c, v, F, bad):
    m, up, lo, bw, pb = BB.boll(c, bad)
    if cell == "M1":
        return [k for k, _ in BB.detect_m1(c, up, BB.squeeze(bw), bad)]
    MF = BB.mfi(h, l, c, v, F, bad)
    if cell == "M2":
        return BB.detect_m2(pb, MF)
    return sorted(BB.detect_m3(c, pb, MF, bad, RU.pivots(c, bad, 5)).keys())


def rel(a, b):
    return abs(a - b) / max(1.0, abs(b))


def main():
    rng = np.random.default_rng(20261018)
    res = {"C1": [], "C2": [], "C3": []}; fails = []
    for wn, plan in (("主", (("M1", 5), ("M2", 5), ("M3", 2))), ("早年", (("M1", 4), ("M2", 3), ("M3", 1)))):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        for cell, m in plan:
            A = ev[(ev["格"] == cell) & (ev["st"] == "保留")].reset_index(drop=True)
            pick = A.iloc[np.sort(rng.choice(len(A), m, replace=False))]
            for _, e in pick.iterrows():
                sid = e["sid"]; B, idx, bad = RTC.bars_of(W, sid); df = B["df"]; i = W["ix"][sid]
                h, l, c = (np.asarray(B[z], float) for z in ("h", "l", "c"))
                rc = np.asarray(B["rc"], float)
                v = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
                F = np.where(rc > 0, c / rc, np.nan)
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T))
                # ── 日曆 df 逐列手算（T 當根的指標）
                trd = df["traded"].to_numpy(bool); Hc, Lc, Cc = (df[z].to_numpy(float) for z in ("high", "low", "close"))
                Vc = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
                raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
                raw.index = pd.to_datetime(raw["date"]); RCc = pd.to_numeric(raw["close"], errors="coerce").reindex(cal).to_numpy(float)
                bars = [j for j in range(T + 1) if trd[j]]

                def bb_at(p):
                    w = [j for j in bars if j <= p][-20:]
                    x = [Cc[j] for j in w]; mm = sum(x) / 20; sd = math.sqrt(sum((y - mm) ** 2 for y in x) / 20)
                    return mm, mm + 2 * sd, mm - 2 * sd, (Cc[p] - (mm - 2 * sd)) / (4 * sd) if sd > 0 else np.nan

                def mfi_at(p):
                    w = [j for j in bars if j <= p][-11:]
                    tp = [(Hc[j] + Lc[j] + Cc[j]) / 3 for j in w]; P = Q = 0.0
                    for a_ in range(1, 11):
                        mf = tp[a_] / (Cc[w[a_]] / RCc[w[a_]]) * Vc[w[a_]]
                        if tp[a_] > tp[a_ - 1]:
                            P += mf
                        elif tp[a_] < tp[a_ - 1]:
                            Q += mf
                    return 100 * P / (P + Q)
                chk = {}
                Ml, Ul, Ll, BWl, PBl = boll_loop(c, bad)
                MFl = mfi_loop(h, l, c, v, rc, bad)
                mm, uu, ll_, pb = bb_at(T)
                if cell == "M1":
                    chk["上軌相符"] = rel(uu, e["上軌"]) < 1e-9
                    chk["收>上軌"] = bool(Cc[T] > uu)
                    sq = sq_loop(BWl)
                    ss = [s for s in range(k - 20, k) if s >= 0 and sq[s]]
                    chk["20根內有擠壓日"] = bool(ss)
                    if ss:
                        s = ss[-1]
                        chk["擠壓日相符"] = str(cal[idx[s]].date()) == e["擠壓日"]
                        chk["擠壓日到T無壞根"] = bool(not bad[s + 1:k + 1].any())
                        chk["BW[s]相符"] = rel(BWl[s], e["BW[s]"]) < 1e-9
                elif cell == "M2":
                    mf = mfi_at(T)
                    chk["%b相符"] = rel(pb, e["%b"]) < 1e-9; chk["MFI相符"] = rel(mf, e["MFI"]) < 1e-9
                    chk["%b>0.8且MFI>80"] = bool(pb > 0.8 and mf > 80)
                    pp = bars[-2]; _, _, _, pb1 = bb_at(pp); mf1 = mfi_at(pp)
                    chk["前一天不成立且可判"] = bool(np.isfinite(pb1) and np.isfinite(mf1) and not (pb1 > 0.8 and mf1 > 80))
                    chk["前一天值相符"] = rel(pb1, e["%b[T-1]"]) < 1e-9 and rel(mf1, e["MFI[T-1]"]) < 1e-9
                    chk["窗內無壞根"] = bool(not bad[max(k - 19, 0):k + 1].any())
                else:
                    pv = piv_loop(c, bad)
                    p1 = int(np.searchsorted(idx, pos[e["P1"]])); p2 = int(np.searchsorted(idx, pos[e["P2"]]))
                    chk["P1P2是相鄰轉折低點"] = bool(p1 in pv and p2 in pv and pv.index(p2) == pv.index(p1) + 1)
                    chk["P2−P1≤60"] = p2 - p1 <= 60
                    chk["%b[P1]<0<%b[P2]"] = bool(PBl[p1] < 0 < PBl[p2])
                    chk["MFI[P2]>MFI[P1]"] = bool(MFl[p2] > MFl[p1])
                    neck = max(c[p1:p2 + 1])
                    chk["頸線相符"] = rel(neck, e["頸線"]) < 1e-12
                    first = [t for t in range(p2 + 6, min(p2 + 25, len(c) - 1) + 1) if c[t] > neck]
                    chk["T＝確認後20根內第一根破頸線"] = bool(first and first[0] == k)
                    chk["P1到T無壞根"] = bool(not bad[p1 + 1:k + 1].any())
                chk.update(WC.gate_chk(W, df, T, i))
                chk["T+1 可買"] = WC.next_open_chk(W, i, idx, bad, k, T)
                chk["高低收同一還原因子"] = WC.adj_chk(W, sid, df, T)
                # C2
                c2 = {"截在T仍偵測到": k in mod_det(cell, h[:k + 1], l[:k + 1], c[:k + 1], v[:k + 1], F[:k + 1], bad[:k + 1]),
                      "截在T−1無此T": k not in mod_det(cell, h[:k], l[:k], c[:k], v[:k], F[:k], bad[:k])}
                cuts = sorted(rng.choice(np.arange(200, len(c)), 3, replace=False).tolist())
                okc = True
                for ct in cuts:
                    for cc in ("M1", "M2", "M3"):
                        full = mod_det(cc, h, l, c, v, F, bad)
                        okc &= [z for z in full if z <= ct] == mod_det(cc, h[:ct + 1], l[:ct + 1], c[:ct + 1], v[:ct + 1], F[:ct + 1], bad[:ct + 1])
                c2["隨機截點偵測逐筆相同"] = bool(okc)
                # C3
                mm_, uu_, lo_, bw_, pb_ = BB.boll(c, bad); mf_ = BB.mfi(h, l, c, v, F, bad)
                c3 = {}
                for nm, a_, b_ in (("中軌", mm_, Ml), ("上軌", uu_, Ul), ("下軌", lo_, Ll), ("BW", bw_, BWl), ("%b", pb_, PBl), ("MFI", mf_, MFl)):
                    same = bool((np.isfinite(a_) == np.isfinite(b_)).all()); both = np.isfinite(a_) & np.isfinite(b_)
                    d = float(np.max(np.abs(a_[both] - b_[both]) / np.maximum(1.0, np.abs(b_[both])))) if both.any() else 0.0
                    c3[nm + "有值位置同"] = same; c3[nm + "相對差"] = d
                c3["擠壓日同"] = bool((BB.squeeze(bw_) == sq_loop(BWl)).all())
                c3["擠壓日數"] = int(sq_loop(BWl).sum())
                c3["轉折同"] = RU.pivots(c, bad, 5) == piv_loop(c, bad)
                c3["MFI範圍"] = [round(float(np.nanmin(mf_)), 3), round(float(np.nanmax(mf_)), 3)]
                c3["ok"] = bool(all(v_ for z, v_ in c3.items() if z.endswith("同")) and max(v_ for z, v_ in c3.items() if z.endswith("相對差")) < 1e-9
                                and np.nanmin(mf_) >= 0 and np.nanmax(mf_) <= 100)
                res["C1"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], **chk})
                res["C2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "截點": cuts, **c2})
                res["C3"].append({"世界": wn, "sid": sid, **c3})
                b1 = [z for z, v_ in chk.items() if not v_]; b2 = [z for z, v_ in c2.items() if not v_]
                if b1 or b2 or not c3["ok"]:
                    fails.append({"格": cell, "sid": sid, "T": e["T"], "C1不符": b1, "C2不符": b2, "C3": c3})
                log(f"{wn} {cell} {sid} T={e['T']}｜C1 {'✔' if not b1 else b1}｜C2 {'✔' if not b2 else b2}｜C3 {'✔' if c3['ok'] else c3}"
                    f"（BW 差 {c3['BW相對差']:.1e}、MFI 差 {c3['MFI相對差']:.1e}）")
    res["不符"] = fails
    res["結論"] = f"{len(res['C1'])} 筆全部相符" if not fails else f"{len(fails)} 筆不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

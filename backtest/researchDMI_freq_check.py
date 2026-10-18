# -*- coding: utf-8 -*-
"""researchDMI_freq 對帳（DMI 交叉＋極點進場 seq1 頻率表乾跑，登錄 sha 7329d0b51c85b40c）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDMI_freq_check
輸出 backtest/resultsDMI/freq/check.json、check.log

C1 抽 20 筆保留事件（主：E 7、D2 3；早年：E 7、D2 3；default_rng(20261018)），逐筆用【日曆 df 逐列手算】＋本檔獨立 DI
   （⛔ 不呼叫 researchDMI_freq 的 dmi_wilder／crosses／entry）：交叉日 c 的 +DI[c−1] ≤ −DI[c−1]、+DI[c] ＞ −DI[c]；c＋1 … T−1 每根
   開盤前 +DI ＞ −DI（DI[j]，j ＝ c … T−1）、沒有更早的觸發（E：h ≤ c 日最高；D2：收 ≤ c 日最高）；T − c ≤ 20；h[T]（D2：c[T]）＞ c 日最高（df 逐列）；
   [c, T] 無壞 K 棒；母體（自算 500 張 ∧ 20 日有成交 ∧ pit_valid）；E：T 開盤有效且非開盤鎖漲停；D2：T＋1 可買；事件檔 ADXR[T−1] ＝ 本檔獨立 ADX 算出；
   高低收同一還原因子。
C2 不前視：同 20 檔，截在 k ⇒ k 仍在；截在 k−1 ⇒ 沒有 k；截在 k−1 的 DI[k−1]、ADXR[k−1] ＝ 全序列（濾網不前視）；
   另每檔 3 個隨機截點：全序列 E、D2 偵測中 ≤ cut 者 ＝ 截斷序列偵測。
C3 DI／ADX：同 20 檔全序列，① dmi_wilder 的 ADX、段齡與 researchTurtle_freq.adx_wilder 逐位相同（patch 只加紀錄點）；
   ② +DI、−DI、ADX 與本檔【分段陣列版】Wilder 原式逐根比對（有值位置相同、最大差 ＜ 1e−9）；ADX 另與 researchTurtle_freq_check.adx_seg 比對。
   ⚠ venv 無第三方 DMI 套件 ⇒ 只能自寫兩份互對，未與第三方實作對帳。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchDMI_freq as DM                 # noqa: E402
from backtest import researchTurtle_freq as RT              # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of、adx_seg（⛔ 只 import）
from backtest import researchWR_freq_check as WC            # noqa: E402  gate_chk／adj_chk／next_open_chk（⛔ 只 import）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = DM.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def dmi_seg(h, l, c, bad, n=14):
    """分段陣列版：段內先算 TR1／±DM1 陣列，再照 StockCharts 步驟平滑 ⇒ +DI、−DI、ADX。"""
    N = len(c); PD = np.full(N, np.nan); MD = PD.copy(); AD = PD.copy()
    starts = [0] + [k for k in range(1, N) if bad[k]]
    ends = starts[1:] + [N]
    for s, e in zip(starts, ends):
        m = e - s
        if m < n + 1:
            continue
        H, L, C = h[s:e], l[s:e], c[s:e]
        tr = np.zeros(m); pdm = np.zeros(m); mdm = np.zeros(m)
        for j in range(1, m):
            tr[j] = max(H[j] - L[j], abs(H[j] - C[j - 1]), abs(L[j] - C[j - 1]))
            u = H[j] - H[j - 1]; d = L[j - 1] - L[j]
            pdm[j] = u if (u > d and u > 0) else 0.0
            mdm[j] = d if (d > u and d > 0) else 0.0
        S = np.full((m, 3), np.nan)
        S[n] = [tr[1:n + 1].sum(), pdm[1:n + 1].sum(), mdm[1:n + 1].sum()]
        for j in range(n + 1, m):
            S[j] = S[j - 1] - S[j - 1] / n + np.array([tr[j], pdm[j], mdm[j]])
        dx = np.full(m, np.nan)
        for j in range(n, m):
            if S[j, 0] > 0:
                p_ = 100 * S[j, 1] / S[j, 0]; q_ = 100 * S[j, 2] / S[j, 0]
                PD[s + j] = p_; MD[s + j] = q_
                if p_ + q_ > 0:
                    dx[j] = 100 * abs(p_ - q_) / (p_ + q_)
        a = np.full(m, np.nan); run = []; prev = np.nan
        for j in range(n, m):
            if not np.isfinite(dx[j]):
                run = []; prev = np.nan; continue
            if np.isfinite(prev):
                prev = (prev * (n - 1) + dx[j]) / n; a[j] = prev
            else:
                run.append(dx[j])
                if len(run) == n:
                    prev = float(np.mean(run)); a[j] = prev; run = []
        AD[s:e] = a
    return PD, MD, AD


def mod_det(cell, h, l, c, bad):
    _, _, P_, M_ = DM.dmi_wilder(h, l, c, bad)
    out = []
    for x in DM.crosses(P_, M_):
        t = DM.entry(x, h, c, P_, M_, bad, cell == "D2_收盤")
        if t is not None:
            out.append(t)
    return out


def main():
    rng = np.random.default_rng(20261018)
    res = {"C1": [], "C2": [], "C3": []}; fails = []
    for wn, plan in (("主", (("E", 7), ("D2_收盤", 3))), ("早年", (("E", 7), ("D2_收盤", 3)))):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        for cell, m in plan:
            A = ev[(ev["格"] == cell) & (ev["st"] == "保留")].reset_index(drop=True)
            pick = A.iloc[np.sort(rng.choice(len(A), m, replace=False))]
            d2 = cell == "D2_收盤"
            for _, e in pick.iterrows():
                sid = e["sid"]; B, idx, bad = RTC.bars_of(W, sid); df = B["df"]; i = W["ix"][sid]
                h, l, c = (np.asarray(B[z], float) for z in ("h", "l", "c"))
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T)); C0 = pos[e["c日"]]; x = int(np.searchsorted(idx, C0))
                Hc, Cc = df["high"].to_numpy(float), df["close"].to_numpy(float)
                PD, MD, AD = dmi_seg(h, l, c, bad)
                chk = {"c日最高相符(df)": bool(abs(Hc[C0] - e["c日最高"]) < 1e-12)}
                chk["交叉(+DI上穿−DI)"] = bool(PD[x - 1] <= MD[x - 1] and PD[x] > MD[x])
                chk["c…T−1 開盤前+DI>−DI"] = bool(all(PD[j] > MD[j] for j in range(x, k)))
                trig = (lambda j: Cc[idx[j]] > Hc[C0]) if d2 else (lambda j: Hc[idx[j]] > Hc[C0])
                chk["T觸發(df逐列)"] = bool(trig(k))
                chk["無更早觸發"] = bool(not any(trig(j) for j in range(x + 1, k)))
                chk["T−c≤20(有效K棒)"] = 1 <= k - x <= 20
                chk["[c,T]無壞根"] = bool(not bad[x + 1:k + 1].any())
                ar = (AD[k - 1] + AD[k - 15]) / 2 if k - 15 >= 0 else np.nan
                ae = e["ADXR[T-1]"]
                chk["ADXR[T-1]相符"] = bool((np.isnan(ae) and np.isnan(ar)) or abs(ar - ae) < 1e-8)
                chk["+DI[T-1]相符"] = bool(abs(PD[k - 1] - e["+DI[T-1]"]) < 1e-8)
                chk.update(WC.gate_chk(W, df, T, i))
                if d2:
                    chk["T+1 可買"] = WC.next_open_chk(W, i, idx, bad, k, T)
                else:
                    chk["T 開盤有效且非鎖漲停"] = bool(np.isfinite(W["O"][i][T]) and W["O"][i][T] > 0 and not W["UPL"][i][T])
                chk["高低收同一還原因子"] = WC.adj_chk(W, sid, df, T)
                # C2
                Afull, AGEf, Pf, Mf = DM.dmi_wilder(h, l, c, bad)
                At, AGEt, Pt, Mt = DM.dmi_wilder(h[:k], l[:k], c[:k], bad[:k])
                ARf = DM.adxr(Afull, AGEf); ARt = DM.adxr(At, AGEt)
                eq = lambda a_, b_: bool((np.isnan(a_) and np.isnan(b_)) or abs(a_ - b_) < 1e-12)
                c2 = {"截在T仍偵測到": k in mod_det(cell, h[:k + 1], l[:k + 1], c[:k + 1], bad[:k + 1]),
                      "截在T−1無此T": k not in mod_det(cell, h[:k], l[:k], c[:k], bad[:k]),
                      "截在T−1的DI與ADXR同全序列": eq(Pt[k - 1], Pf[k - 1]) and eq(Mt[k - 1], Mf[k - 1]) and eq(ARt[k - 1], ARf[k - 1])}
                cuts = sorted(rng.choice(np.arange(80, len(c)), 3, replace=False).tolist())
                okc = True
                for ct in cuts:
                    for cc in ("E", "D2_收盤"):
                        okc &= [z for z in mod_det(cc, h, l, c, bad) if z <= ct] == mod_det(cc, h[:ct + 1], l[:ct + 1], c[:ct + 1], bad[:ct + 1])
                c2["隨機截點偵測逐筆相同"] = bool(okc)
                # C3
                Ao, AGEo = RT.adx_wilder(h, l, c, bad)
                A2 = RTC.adx_seg(h, l, c, bad)
                c3 = {"ADX與海龜adx_wilder逐位同": bool(np.array_equal(Ao, Afull, equal_nan=True) and np.array_equal(AGEo, AGEf))}
                for nm, a_, b_ in (("+DI", Pf, PD), ("−DI", Mf, MD), ("ADX", Afull, AD), ("ADX對adx_seg", Afull, A2)):
                    same = bool((np.isfinite(a_) == np.isfinite(b_)).all()); both = np.isfinite(a_) & np.isfinite(b_)
                    c3[nm + "有值位置同"] = same; c3[nm + "最大差"] = float(np.max(np.abs(a_[both] - b_[both]))) if both.any() else 0.0
                c3["DI範圍"] = [round(float(np.nanmin(Pf)), 3), round(float(np.nanmax(Pf)), 3)]
                c3["ok"] = c3["ADX與海龜adx_wilder逐位同"] and all(v_ for z, v_ in c3.items() if z.endswith("同")) \
                    and max(v_ for z, v_ in c3.items() if z.endswith("最大差")) < 1e-9 and np.nanmin(Pf) >= 0 and np.nanmax(Pf) <= 100
                res["C1"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "c日": e["c日"], **chk})
                res["C2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "截點": cuts, **c2})
                res["C3"].append({"世界": wn, "sid": sid, **c3})
                b1 = [z for z, v_ in chk.items() if not v_]; b2 = [z for z, v_ in c2.items() if not v_]
                if b1 or b2 or not c3["ok"]:
                    fails.append({"格": cell, "sid": sid, "T": e["T"], "C1不符": b1, "C2不符": b2, "C3": c3})
                log(f"{wn} {cell} {sid} c={e['c日']} T={e['T']}｜C1 {'✔' if not b1 else b1}｜C2 {'✔' if not b2 else b2}｜C3 {'✔' if c3['ok'] else c3}"
                    f"（+DI 差 {c3['+DI最大差']:.1e}、ADX 差 {c3['ADX最大差']:.1e}）")
    res["不符"] = fails
    res["結論"] = f"{len(res['C1'])} 筆全部相符" if not fails else f"{len(fails)} 筆不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

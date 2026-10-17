# -*- coding: utf-8 -*-
"""researchTurtle_freq 對帳（海龜 Donchian 突破 seq2 頻率表乾跑，登錄 sha 87b39da0f38816e0）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtle_freq_check
輸出 backtest/resultsTurtle/freq/check.json、check.log

C1 抽 20 筆 S 格保留事件（主：S1 6、S2 6；早年：S1 4、S2 4；default_rng(20261017)）＋ 另抽 6 筆 D4（主 3、早年 3），逐筆用【日曆 df 逐列手算】
   （⛔ 不呼叫 researchTurtle_freq 的 detect／prev_high）：T 之前最近 N 個有成交日的還原最高取最大、與事件檔「前N日最高」相符；
   h[T]（D4：c[T]）＞ 該值（嚴格）；前 N 根與 T 之間每一段相鄰都不是壞 K 棒（D4 另查 T＋1 那根）；
   母體（自算 T−20～T−1 日均量 ≥ 500,000 股 ∧ 含 T 的 20 日都有成交 ∧ pit_valid）；S：T 開盤有效且非開盤鎖漲停（upl）；
   D4：T＋1 有成交、開盤有效、非開盤鎖漲停；還原口徑（原始 csv：T 當天 還原收盤／原始收盤 ＝ 還原高／原始高 ＝ 還原低／原始低）；
   事件檔 ADX 值 ＝ C3 獨立實作在 T−1（D4：T）的值。
C2 不前視：同 26 檔，把有效 K 棒截在 k（只留 ≤ T）重跑模組 detect ⇒ k 仍在；截在 k−1 ⇒ 沒有 k；截在 k−1 的 ADX[k−1] ＝ 全序列 ADX[k−1]
   （濾網不前視）。另每檔 3 個隨機截點 cut：全序列 S1／S2／D4 偵測中 k ≤ cut 者 ＝ 截斷序列偵測全部（逐筆相同），ADX[:cut+1] 逐根相同。
C3 ADX：同 26 檔全序列，模組 adx_wilder 與本檔【另寫的分段陣列版】Wilder 原式逐根比對（有值位置相同、最大差 ＜ 1e−9）；ADX ∈ [0, 100]。
   ⚠ venv 無任何第三方 ADX 套件 ⇒ 只能自寫兩份互相對帳，未與第三方實作對帳。
"""
from __future__ import annotations

import gzip
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTurtle_freq as RT              # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = RT.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def adx_seg(h, l, c, bad, n=14):
    """分段陣列版：先切無壞 K 棒段，段內先算 TR1／±DM1 陣列，再照 StockCharts 步驟逐段平滑。"""
    N = len(c); out = np.full(N, np.nan)
    starts = [0] + [k for k in range(1, N) if bad[k]]
    ends = starts[1:] + [N]
    for s, e in zip(starts, ends):
        m = e - s
        if m < 2 * n:
            continue
        H, L, C = h[s:e], l[s:e], c[s:e]
        tr = np.full(m, np.nan); pdm = np.zeros(m); mdm = np.zeros(m)
        for j in range(1, m):
            tr[j] = max(H[j] - L[j], abs(H[j] - C[j - 1]), abs(L[j] - C[j - 1]))
            u = H[j] - H[j - 1]; d = L[j - 1] - L[j]
            if u > d and u > 0:
                pdm[j] = u
            if d > u and d > 0:
                mdm[j] = d
        S = np.full((m, 3), np.nan)
        S[n] = [tr[1:n + 1].sum(), pdm[1:n + 1].sum(), mdm[1:n + 1].sum()]
        for j in range(n + 1, m):
            S[j] = S[j - 1] - S[j - 1] / n + np.array([tr[j], pdm[j], mdm[j]])
        dx = np.full(m, np.nan)
        for j in range(n, m):
            if S[j, 0] > 0:
                pdi = 100 * S[j, 1] / S[j, 0]; mdi = 100 * S[j, 2] / S[j, 0]
                if pdi + mdi > 0:
                    dx[j] = 100 * abs(pdi - mdi) / (pdi + mdi)
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
        out[s:e] = a
    return out


def bars_of(W, sid):
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"])
    idx = B["idx"].astype(np.int64); nb = len(idx)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    return B, idx, bad


def main():
    rng = np.random.default_rng(20261017)
    res = {"C1": [], "C2": [], "C3": []}; fails = []
    for wn, plan in (("主", (("S1", 6), ("S2", 6), ("D4_S1", 2), ("D4_S2", 1))), ("早年", (("S1", 4), ("S2", 4), ("D4_S1", 2), ("D4_S2", 1)))):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        for cell, m in plan:
            A = ev[(ev["格"] == cell) & (ev["st"] == "保留")].reset_index(drop=True)
            pick = A.iloc[np.sort(rng.choice(len(A), m, replace=False))]
            d4 = cell.startswith("D4"); N = RT.NS[cell[-2:]]
            for _, e in pick.iterrows():
                sid = e["sid"]; B, idx, bad = bars_of(W, sid); df = B["df"]
                h, l, c = (np.asarray(B[k], float) for k in ("h", "l", "c"))
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T)); i = W["ix"][sid]
                # 日曆 df 逐列手算
                trd = df["traded"].to_numpy(bool); Hc = df["high"].to_numpy(float); Cc = df["close"].to_numpy(float)
                prev = []; j = T - 1
                while len(prev) < N and j >= 0:
                    if trd[j]:
                        prev.append(j)
                    j -= 1
                chk = {}
                chk["前N根足"] = len(prev) == N
                mx = max(Hc[p] for p in prev)
                chk["前N日最高相符"] = bool(abs(mx - e["前N日最高"]) < 1e-9 * max(1.0, mx))
                x = Cc[T] if d4 else Hc[T]
                chk["突破(嚴格大於)"] = bool(x > mx)
                kk = [int(np.searchsorted(idx, p)) for p in sorted(prev)] + [k]
                chk["前N根到T相連無壞根"] = bool(not any(bad[q] for q in kk[1:]) and all(kk[t + 1] - kk[t] == 1 for t in range(len(kk) - 1)))
                vol = df["volume"].to_numpy(float)
                chk["母體 500 張"] = bool(trd[T - 19:T + 1].all() and np.isfinite(vol[T - 20:T]).all() and np.nanmean(vol[T - 20:T]) >= 500_000)
                chk["pit_valid"] = bool(W["PV"][i][T])
                if d4:
                    chk["T+1 可買"] = bool(k + 1 < len(idx) and idx[k + 1] == T + 1 and W["TRD"][i][T + 1] and np.isfinite(W["O"][i][T + 1])
                                         and W["O"][i][T + 1] > 0 and not W["UPL"][i][T + 1] and not bad[k + 1])
                else:
                    chk["T 開盤有效且非鎖漲停"] = bool(np.isfinite(W["O"][i][T]) and W["O"][i][T] > 0 and not W["UPL"][i][T])
                raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
                raw["date"] = pd.to_datetime(raw["date"]); rr = raw.set_index("date").loc[cal[T]]
                fc, fh, fl = Cc[T] / float(rr["close"]), Hc[T] / float(rr["high"]), df["low"].iloc[T] / float(rr["low"])
                chk["高低收同一還原因子"] = bool(abs(fc - fh) < 1e-9 * max(1, fc) and abs(fc - fl) < 1e-9 * max(1, fc))
                A2 = adx_seg(h, l, c, bad)
                ka = k if d4 else k - 1
                ae = e["ADX參考"]
                chk["ADX值相符"] = bool((np.isnan(ae) and np.isnan(A2[ka])) or abs(A2[ka] - ae) < 1e-8)
                # C2 不前視
                def det(kc, NN, cc):
                    ks, _ = RT.detect(h[:kc + 1], c[:kc + 1], bad[:kc + 1], NN, close_confirm=cc)
                    return [int(z) for z in ks]
                Am, _ = RT.adx_wilder(h, l, c, bad)
                At, _ = RT.adx_wilder(h[:k], l[:k], c[:k], bad[:k])
                c2 = {"截在T仍偵測到": k in det(k, N, d4), "截在T−1無此T": k not in det(k - 1, N, d4),
                      "截在T−1的ADX[T−1]同全序列": bool((np.isnan(At[k - 1]) and np.isnan(Am[k - 1])) or abs(At[k - 1] - Am[k - 1]) < 1e-12)}
                cuts = sorted(rng.choice(np.arange(80, len(c)), 3, replace=False).tolist())
                okc = True
                for ct in cuts:
                    for NN in (20, 55):
                        for cc in (False, True):
                            full = [z for z in det(len(c) - 1, NN, cc) if z <= ct]
                            okc &= full == det(ct, NN, cc)
                    Ac, _ = RT.adx_wilder(h[:ct + 1], l[:ct + 1], c[:ct + 1], bad[:ct + 1])
                    okc &= bool(np.array_equal(np.isfinite(Ac), np.isfinite(Am[:ct + 1])) and np.nanmax(np.abs(Ac - Am[:ct + 1])) < 1e-12)
                c2["隨機截點偵測與ADX逐筆相同"] = bool(okc)
                # C3
                both = np.isfinite(Am) & np.isfinite(A2)
                c3 = {"ADX有值位置相同": bool((np.isfinite(Am) == np.isfinite(A2)).all()),
                      "ADX最大差": float(np.max(np.abs(Am[both] - A2[both]))) if both.any() else 0.0,
                      "ADX有值根數": int(both.sum()), "ADX範圍": [round(float(np.nanmin(Am)), 3), round(float(np.nanmax(Am)), 3)]}
                c3["ok"] = c3["ADX有值位置相同"] and c3["ADX最大差"] < 1e-9 and 0 <= np.nanmin(Am) and np.nanmax(Am) <= 100
                r1 = {"世界": wn, "格": cell, "sid": sid, "T": e["T"], "前N日最高": round(mx, 4), ("收盤" if d4 else "最高"): round(x, 4),
                      "ADX參考": None if np.isnan(ae) else round(float(ae), 3), **chk}
                res["C1"].append(r1); res["C2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "截點": cuts, **c2})
                res["C3"].append({"世界": wn, "sid": sid, **c3})
                b1 = [z for z, v in chk.items() if not v]; b2 = [z for z, v in c2.items() if not v]
                if b1 or b2 or not c3["ok"]:
                    fails.append({"格": cell, "sid": sid, "T": e["T"], "C1不符": b1, "C2不符": b2, "C3": c3})
                log(f"{wn} {cell} {sid} T={e['T']} 前{N}高 {mx:.4f} {'收' if d4 else '高'} {x:.4f} ADX {ae:.2f}｜C1 {'✔' if not b1 else b1}｜"
                    f"C2 {'✔' if not b2 else b2}｜C3 {'✔' if c3['ok'] else c3}（ADX 最大差 {c3['ADX最大差']:.1e}）")
    res["不符"] = fails
    res["結論"] = f"{len(res['C1'])} 筆全部相符" if not fails else f"{len(fails)} 筆不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

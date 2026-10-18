# -*- coding: utf-8 -*-
"""researchWR_freq 對帳（Williams %R 對日線 KD seq1 頻率表乾跑，登錄 sha 92d0b5b84554d22e）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有天數、出場日。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWR_freq_check
輸出 backtest/resultsWR/freq/check.json、check.log

C1 抽 20 筆日線保留事件（主：W 6、K 4；早年：W 6、K 4；default_rng(20261018)）＋ 週線 4 筆（主、早年各 週_W 1、週_K 1），
   逐筆用【日曆 df 逐列手算】（⛔ 不呼叫 researchWR_freq 的 willr／kd_daily／detect_*；KD 也不呼叫 researchWeekly.kd）：
   %R(14)：T−1、T 往前各取 14 個有成交日的還原高低、算 %R，與事件檔相符且 %R[T−1] ＜ −80 ≤ %R[T]；
   KD：逐段迴圈重算（RSV、⅔⅓、起始 50），K 上穿 D 且 K ≤ 30、段內位置 ≥ 30；
   20 日合併：用本檔獨立偵測序列重做「先合併」⇒ 此事件不是合併掉；窗內 [T−14, T]（KD：段首到 T）無壞 K 棒；
   母體（自算 T−20～T−1 日均量 ≥ 500,000 股 ∧ 含 T 的 20 日都有成交 ∧ pit_valid）；T＋1 有成交、開盤有效、非開盤鎖漲停、非壞 K 棒；
   還原口徑（原始 csv：T 當天 還原收／原始收 ＝ 還原高／原始高 ＝ 還原低／原始低）。
   週線：本檔另以 pandas 依週一分組重建週 K、重算週 %R(14)／週 KD，比對事件檔值、訊號條件、T ＝ 該週最後有效 K 棒、進場日 ＝ 下一個日曆週第一個交易日。
C2 不前視：同 20 檔，把有效 K 棒截在 k（只留 ≤ T）重跑模組偵測 ⇒ k 仍在；截在 k−1 ⇒ 沒有 k；另每檔 3 個隨機截點 cut：
   全序列偵測中 ≤ cut 者 ＝ 截斷序列偵測（W、K 逐筆相同），且合併後狀態（合併掉／未合併）逐筆相同。
C3 指標逐根：同 20 檔全序列，模組 willr ／ kd_daily 與本檔逐根迴圈版比對（有值位置相同、最大差 ＜ 1e−9）；%R ∈ [−100, 0]、K、D ∈ [0, 100]。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WF                  # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of（⛔ 只 import）
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
OUT = WF.OUT
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


# ═════════════ 獨立逐根版 ═════════════
def wr_loop(h, l, c, bad, n=14):
    N = len(c); out = np.full(N, np.nan)
    for k in range(n - 1, N):
        if any(bad[j] for j in range(k - n + 2, k + 1)):
            continue
        hh = max(h[k - n + 1:k + 1]); ll = min(l[k - n + 1:k + 1])
        if hh > ll:
            out[k] = (hh - c[k]) / (hh - ll) * -100.0
    return out


def kd_loop(h, l, c, bad):
    N = len(c); K = np.full(N, np.nan); Dd = np.full(N, np.nan); pos = np.zeros(N, np.int64)
    s = 0; k0 = d0 = 50.0
    for t in range(N):
        if t == 0 or bad[t]:
            s = t; k0 = d0 = 50.0
        pos[t] = t - s
        if t - s < 8:
            continue
        lo = min(l[t - 8:t + 1]); hi = max(h[t - 8:t + 1])
        rsv = 50.0 if hi - lo <= 0 else (c[t] - lo) / (hi - lo) * 100.0
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3
        K[t] = k0; Dd[t] = d0
    return K, Dd, pos


def det_loop(cell, h, l, c, bad):
    if cell == "W":
        w = wr_loop(h, l, c, bad)
        return [k for k in range(1, len(c)) if np.isfinite(w[k - 1]) and np.isfinite(w[k]) and w[k - 1] < -80 and w[k] >= -80]
    K, Dd, pos = kd_loop(h, l, c, bad)
    return [k for k in range(1, len(c)) if pos[k] >= 30 and pos[k - 1] == pos[k] - 1 and K[k - 1] <= Dd[k - 1] and K[k] > Dd[k] and K[k] <= 30]


def merged_flags(ks, win=20):
    out = {}; last = -10 ** 9
    for k in ks:
        out[k] = k - last <= win
        if not out[k]:
            last = k
    return out


def mod_det(cell, h, l, c, bad):
    if cell == "W":
        return WF.detect_w(WF.willr(h, l, c, bad))
    return WF.detect_k(*WF.kd_daily(h, l, c, bad))


def gate_chk(W, df, T, i):
    trd = df["traded"].to_numpy(bool); vol = df["volume"].to_numpy(float)
    return {"母體 500 張": bool(trd[T - 19:T + 1].all() and np.isfinite(vol[T - 20:T]).all() and np.nanmean(vol[T - 20:T]) >= 500_000),
            "pit_valid": bool(W["PV"][i][T])}


def adj_chk(W, sid, df, T):
    cal = W["cal"]
    raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}).drop_duplicates("date")
    raw["date"] = pd.to_datetime(raw["date"]); rr = raw.set_index("date").loc[cal[T]]
    fc, fh, fl = df["close"].iloc[T] / float(rr["close"]), df["high"].iloc[T] / float(rr["high"]), df["low"].iloc[T] / float(rr["low"])
    return bool(abs(fc - fh) < 1e-9 * max(1, fc) and abs(fc - fl) < 1e-9 * max(1, fc))


def next_open_chk(W, i, idx, bad, k, T):
    return bool(k + 1 < len(idx) and idx[k + 1] == T + 1 and W["TRD"][i][T + 1] and np.isfinite(W["O"][i][T + 1])
                and W["O"][i][T + 1] > 0 and not W["UPL"][i][T + 1] and not bad[k + 1])


def weekly_check(W, sid, e, cell):
    """本檔獨立重建週 K（依週一分組），重算週 %R(14)／週 KD 於訊號週。"""
    B, idx, bad = RTC.bars_of(W, sid); df = B["df"]; cal = W["cal"]
    tr = df[df["traded"]].copy()
    mon = (tr.index - pd.to_timedelta(tr.index.weekday, unit="D")).normalize()
    g = tr.groupby(mon)
    wk = pd.DataFrame({"H": g["high"].max(), "L": g["low"].min(), "C": g["close"].last(), "last": g.apply(lambda x: x.index[-1])})
    T = cal.get_loc(pd.Timestamp(e["T"]))
    p = int(np.flatnonzero(wk["last"].to_numpy() == cal[T])[0])
    H, L, C = (wk[z].to_numpy(float) for z in ("H", "L", "C"))
    chk = {"T＝該週最後有效K棒": True, "週序相符": p == int(e["週序"]), "暖機≥52": p >= 52}
    allmon = pd.Series((cal - pd.to_timedelta(cal.weekday, unit="D")).normalize()).drop_duplicates().tolist()
    wpos = allmon.index(wk.index[p])
    nxt_first = int(np.flatnonzero(((cal - pd.to_timedelta(cal.weekday, unit="D")).normalize()) == allmon[wpos + 1])[0]) if wpos + 1 < len(allmon) else -1
    chk["進場日＝下一日曆週第一交易日"] = (str(cal[nxt_first].date()) if nxt_first >= 0 else "") == str(e["進場日位置"])
    if cell == "週_W":
        def wr(j):
            hh = H[j - 13:j + 1].max(); ll = L[j - 13:j + 1].min()
            return (hh - C[j]) / (hh - ll) * -100.0 if hh > ll else np.nan
        a, b = wr(p - 1), wr(p)
        chk["週%R相符"] = bool(abs(b - e["值"]) < 1e-9)
        chk["週%R由<−80回≥−80"] = bool(a < -80 <= b)
    else:
        k0 = d0 = 50.0; Ks = np.full(len(C), np.nan); Ds = np.full(len(C), np.nan)
        for t in range(8, len(C)):
            lo, hi = L[t - 8:t + 1].min(), H[t - 8:t + 1].max()
            rsv = 50.0 if hi - lo <= 0 else (C[t] - lo) / (hi - lo) * 100
            k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3; Ks[t] = k0; Ds[t] = d0
        chk["週K相符"] = bool(abs(Ks[p] - e["值"]) < 1e-9)
        chk["週KD金叉且K≤30"] = bool(Ks[p - 1] <= Ds[p - 1] and Ks[p] > Ds[p] and Ks[p] <= 30)
    # 壞根週與前後各 1 週
    bw = set()
    for q in np.flatnonzero(bad):
        m_ = (cal[idx[q]] - pd.Timedelta(days=cal[idx[q]].weekday())).normalize(); bw.add(allmon.index(m_))
    chk["非壞根週±1"] = not any(abs(wpos - x) <= 1 for x in bw)
    i = W["ix"][sid]
    chk.update(gate_chk(W, df, T, i))
    return chk


def main():
    rng = np.random.default_rng(20261018)
    res = {"C1": [], "C2": [], "C3": [], "週": []}; fails = []
    for wn, plan in (("主", (("W", 6), ("K", 4))), ("早年", (("W", 6), ("K", 4)))):
        W = AT.load_world(wn); cal = W["cal"]; pos = {str(d.date()): j for j, d in enumerate(cal)}
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        for cell, m in plan:
            A = ev[(ev["格"] == cell) & (ev["st"] == "保留")].reset_index(drop=True)
            pick = A.iloc[np.sort(rng.choice(len(A), m, replace=False))]
            for _, e in pick.iterrows():
                sid = e["sid"]; B, idx, bad = RTC.bars_of(W, sid); df = B["df"]; i = W["ix"][sid]
                h, l, c = (np.asarray(B[z], float) for z in ("h", "l", "c"))
                T = pos[e["T"]]; k = int(np.searchsorted(idx, T))
                # 日曆 df 逐列手算
                trd = df["traded"].to_numpy(bool); Hc, Lc, Cc = (df[z].to_numpy(float) for z in ("high", "low", "close"))
                bars = [j for j in range(T + 1) if trd[j]]
                chk = {}
                if cell == "W":
                    def wr_at(endpos):
                        win = [j for j in bars if j <= endpos][-14:]
                        hh = max(Hc[j] for j in win); ll = min(Lc[j] for j in win)
                        return (hh - Cc[endpos]) / (hh - ll) * -100.0, win
                    a, w1 = wr_at(bars[-2]); b, w2 = wr_at(T)
                    chk["%R[T-1]相符"] = bool(abs(a - e["%R[T-1]"]) < 1e-9); chk["%R[T]相符"] = bool(abs(b - e["%R[T]"]) < 1e-9)
                    chk["由<−80回≥−80"] = bool(a < -80 <= b)
                    kk = [int(np.searchsorted(idx, j)) for j in sorted(set(w1) | set(w2))]
                    chk["窗內無壞根"] = bool(not any(bad[q] for q in kk[1:]))
                else:
                    K, Dd, ps = kd_loop(h, l, c, bad)
                    chk["K[T]相符"] = bool(abs(K[k] - e["K[T]"]) < 1e-9); chk["D[T]相符"] = bool(abs(Dd[k] - e["D[T]"]) < 1e-9)
                    chk["K上穿D且K≤30"] = bool(K[k - 1] <= Dd[k - 1] and K[k] > Dd[k] and K[k] <= 30)
                    chk["段內位置≥30"] = bool(ps[k] >= 30)
                dl = det_loop(cell, h, l, c, bad)
                chk["獨立偵測含T"] = k in dl
                chk["非合併掉(20日)"] = bool(k in dl and not merged_flags(dl)[k])
                chk.update(gate_chk(W, df, T, i))
                chk["T+1 可買"] = next_open_chk(W, i, idx, bad, k, T)
                chk["高低收同一還原因子"] = adj_chk(W, sid, df, T)
                # C2
                c2 = {"截在T仍偵測到": k in mod_det(cell, h[:k + 1], l[:k + 1], c[:k + 1], bad[:k + 1]),
                      "截在T−1無此T": k not in mod_det(cell, h[:k], l[:k], c[:k], bad[:k])}
                cuts = sorted(rng.choice(np.arange(80, len(c)), 3, replace=False).tolist())
                okc = True
                for ct in cuts:
                    for cc in ("W", "K"):
                        full = mod_det(cc, h, l, c, bad); tr_ = mod_det(cc, h[:ct + 1], l[:ct + 1], c[:ct + 1], bad[:ct + 1])
                        okc &= [z for z in full if z <= ct] == tr_
                        mf, mt = merged_flags(full), merged_flags(tr_)
                        okc &= all(mf[z] == mt[z] for z in tr_)
                c2["隨機截點偵測與合併逐筆相同"] = bool(okc)
                # C3
                wm = WF.willr(h, l, c, bad); wl = wr_loop(h, l, c, bad)
                Km, Dm, pm = WF.kd_daily(h, l, c, bad); Kl, Dl, pl = kd_loop(h, l, c, bad)
                def cmp(a_, b_):
                    same = bool((np.isfinite(a_) == np.isfinite(b_)).all()); both = np.isfinite(a_) & np.isfinite(b_)
                    return same, float(np.max(np.abs(a_[both] - b_[both]))) if both.any() else 0.0
                s1, d1 = cmp(wm, wl); s2, d2 = cmp(Km, Kl); s3, d3 = cmp(Dm, Dl)
                c3 = {"%R有值位置同": s1, "%R最大差": d1, "K有值位置同": s2, "K最大差": d2, "D有值位置同": s3, "D最大差": d3,
                      "段內位置同": bool((pm == pl).all()),
                      "%R範圍": [round(float(np.nanmin(wm)), 3), round(float(np.nanmax(wm)), 3)]}
                c3["ok"] = s1 and s2 and s3 and c3["段內位置同"] and max(d1, d2, d3) < 1e-9 and np.nanmin(wm) >= -100 and np.nanmax(wm) <= 0 \
                    and np.nanmin(Km) >= 0 and np.nanmax(Km) <= 100
                res["C1"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], **chk})
                res["C2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "截點": cuts, **c2})
                res["C3"].append({"世界": wn, "sid": sid, **c3})
                b1 = [z for z, v in chk.items() if not v]; b2 = [z for z, v in c2.items() if not v]
                if b1 or b2 or not c3["ok"]:
                    fails.append({"格": cell, "sid": sid, "T": e["T"], "C1不符": b1, "C2不符": b2, "C3": c3})
                log(f"{wn} {cell} {sid} T={e['T']}｜C1 {'✔' if not b1 else b1}｜C2 {'✔' if not b2 else b2}｜"
                    f"C3 {'✔' if c3['ok'] else c3}（%R 差 {d1:.1e}、K 差 {d2:.1e}）")
        for cell in ("週_W", "週_K"):
            A = ev[(ev["格"] == cell) & (ev["st"] == "保留")].reset_index(drop=True)
            e = A.iloc[int(rng.integers(len(A)))]
            chk = weekly_check(W, e["sid"], e, cell)
            b = [z for z, v in chk.items() if not v]
            res["週"].append({"世界": wn, "格": cell, "sid": e["sid"], "T": e["T"], **chk})
            if b:
                fails.append({"格": cell, "sid": e["sid"], "T": e["T"], "週不符": b})
            log(f"{wn} {cell} {e['sid']} T={e['T']}｜週 {'✔' if not b else b}")
    res["不符"] = fails
    n = len(res["C1"]) + len(res["週"])
    res["結論"] = f"{n} 筆全部相符" if not fails else f"{len(fails)} 筆不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

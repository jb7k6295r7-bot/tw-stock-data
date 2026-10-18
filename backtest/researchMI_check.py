# -*- coding: utf-8 -*-
"""researchMI 對帳（Mass Index 反轉凸起 seq1 事件層正式跑，登錄 sha 356f3ccfda10a90f）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMI_check
輸出 backtest/resultsMI/check.json、check.log

K1 抽 20 筆判定格 A 交易（主 12、早年 8；default_rng(20261018)；從 trades_<世界>_A.csv.gz 中 X 可算者）逐根手算：
   EMA9(收盤) 用 researchMI_freq_check.loop_ind（自寫逐根迴圈），出場用本檔自寫迴圈（⛔ 不呼叫 researchMI 的 sim_mi／exit_ref、⛔ 不呼叫 researchBB）：
   T＋1 開盤進場 → 逐根（含進場當天）收盤 ＜ EMA9 且 EMA9 ＜ 前一日 → 下一根開盤賣（鎖死跌停順延到第一根非鎖死）；下一根壞 K 棒 ⇒ 前一根收盤強制；
   比對 出場日、出場種類、持有天數、R（|差| ＜ 1e−10）。
K2 對照抽樣重建（同 20 筆）：逐檔掃整個世界，自算 T 當天母體（含 T 的 20 日都有成交 ∧ T−20～T−1 日均量 ≥ 500,000 股 ∧ pit_valid）、
   T＋1 可買（下一根 ＝ 日曆 T＋1、非壞 K 棒、有成交、開盤 ＞ 0、非開盤鎖漲停）、T 非壞 K 棒、EMA9c[T] 有值（自寫迴圈）、R 可算（自寫迴圈出場）；
   扣自己與已提交頻率表事件檔 T 當天 A 原始偵測 ⇒ 依種子 [20261018, 1, T, crc32(sid)] 重抽 ⇒ 名單 ＝ 檔案「對照代號」；
   對照平均 R 用自寫迴圈重算 ＝ 檔案「對照平均R」。
K3 不前視：同 20 筆 ①資料截在 T 重跑頻率表偵測 ⇒ 該事件仍在、截在 T−1 ⇒ 不在；②EMA9c 截在賣出訊號那根 j 重算 ＝ 全序列 EMA9c[0..j]；
   ③自寫出場迴圈只給 ≤ j 的資料 ⇒ 訊號恰在 j；只給 ≤ j−1 ⇒ 尚無訊號（強制出場者：下一根確為壞 K 棒、之前無訊號）。
K4 彙總重算：由 trades 檔自算 探索／確認／主全窗／早年 A、D1_26、D2_無方向 的 X̄、曆月分群 SE、n_eff、勝率、平均持有 ＝ MI.json。
"""
from __future__ import annotations

import json
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchMI_freq as MF                  # noqa: E402  只用於 K3 截斷偵測
from backtest import researchMI_freq_check as MFC           # noqa: E402  loop_ind（自寫迴圈）
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsMI"
COST = 0.00585
LOG = []
_G = {}
NAMES = {3: "均線轉弱出場訊號(收盤<EMA9且EMA9下彎)", 4: "壞根前一根收盤強制", 5: "末根收盤(下市/之後無成交)", 6: "資料尾未出場"}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def exit_loop(o, c, EC, bad, dnl, idx, s, n_end, last_cal):
    """自寫出場迴圈：只看第 0..n_end−1 根；回 (訊號根或 None, 出場根或 None, 價, 種類)。"""
    delisted = last_cal - idx[n_end - 1] >= 5

    def endp(sg):
        return (sg, n_end - 1, c[n_end - 1], 5) if delisted else (sg, None, np.nan, 6)
    for j in range(s, n_end):
        if j > s and bad[j]:
            return None, j - 1, c[j - 1], 4
        if c[j] < EC[j] and EC[j] < EC[j - 1]:
            if j + 1 >= n_end:
                return (j, j, c[j], 5) if delisted else (j, None, np.nan, 6)
            if bad[j + 1]:
                return j, j, c[j], 4
            y = j + 1
            while y < n_end:
                if bad[y]:
                    return j, y - 1, c[y - 1], 4
                if not dnl[y]:
                    p = o[y] if (np.isfinite(o[y]) and o[y] > 0) else c[y]
                    return j, y, p, 3
                y += 1
            return endp(j)
    return endp(None)


def pool_job(a):
    wn, sid, Ts = a
    W = _G[wn]; n0 = W["n0"]; i = W["ix"][sid]
    D.DATA = W["data"]
    try:
        B, idx, bad = RTC.bars_of(W, sid)
    except Exception:
        return sid, {}
    if B is None:
        return sid, {}
    df = B["df"]; o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    vol = df["volume"].to_numpy(float); trd = df["traded"].to_numpy(bool)
    dnl = np.asarray(W["DNL"][i][idx], bool)
    _, EC, _ = MFC.loop_ind(h, l, c, bad)
    out = {}
    for T in Ts:
        if T < 20 or not trd[T]:
            continue
        if not (trd[T - 19:T + 1].all() and np.isfinite(vol[T - 20:T]).all() and np.nanmean(vol[T - 20:T]) >= 500_000):
            continue
        if not W["PV"][i][T]:
            continue
        k = int(np.searchsorted(idx, T))
        if bad[k]:
            continue
        if not (k + 1 < len(idx) and idx[k + 1] == T + 1 and not bad[k + 1] and W["TRD"][i][T + 1]
                and np.isfinite(W["O"][i][T + 1]) and W["O"][i][T + 1] > 0 and not W["UPL"][i][T + 1] and np.isfinite(o[k + 1]) and o[k + 1] > 0):
            continue
        if not np.isfinite(EC[k]):
            continue
        sg, eb, px, kind = exit_loop(o, c, EC, bad, dnl, idx, k + 1, len(idx), n0 - 1)
        if kind == 6:
            continue
        out[T] = px / o[k + 1] - 1.0
    return sid, out


def det_at(h, l, c, bad):
    MI, EC, *_ = MF.indicators(h, l, c, bad)
    done, _, _ = MF.bulges(MI, MF.DN)
    return [t for (t, k0, pk) in done if MF.down(EC, t)]


def main():
    rng = np.random.default_rng(20261018)
    J = json.load(open(os.path.join(OUT, "MI.json"), encoding="utf-8"))
    res = {"K1": [], "K2": [], "K3": [], "K4": []}; fails = []
    for wn, m in (("主", 12), ("早年", 8)):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; _G[wn] = W
        pos = {str(d.date()): j for j, d in enumerate(cal)}
        tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_A.csv.gz"), dtype={"sid": str, "對照代號": str}, keep_default_na=False,
                         na_values=[""])
        trx = tr[np.isfinite(tr["X"].astype(float))].reset_index(drop=True)
        pick = trx.iloc[np.sort(rng.choice(len(trx), m, replace=False))].reset_index(drop=True)
        fev = pd.read_csv(os.path.join(MF.OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        rawA = fev[fev["格"] == "A"].groupby("T")["sid"].apply(set).to_dict()
        Ts = sorted(set(pos[t] for t in pick["T"]))
        with Pool(3) as pool:
            PR = dict(pool.imap_unordered(pool_job, [(wn, s, Ts) for s in W["sids"]], chunksize=16))
        log(f"[{wn}] 全世界 {len(W['sids'])} 檔重建對照池（{len(Ts)} 個 T）完成")
        for _, e in pick.iterrows():
            sid = e["sid"]; T = pos[e["T"]]; i = W["ix"][sid]
            B, idx, bad = RTC.bars_of(W, sid)
            o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
            dnl = np.asarray(W["DNL"][i][idx], bool)
            _, EC, _ = MFC.loop_ind(h, l, c, bad)
            k = int(np.searchsorted(idx, T)); s = k + 1
            sg, eb, px, kind = exit_loop(o, c, EC, bad, dnl, idx, s, len(idx), n0 - 1)
            R_ = px / o[s] - 1.0
            exd = str(cal[idx[eb]].date()) if eb is not None else ""
            hold = int(idx[eb] - idx[s]) if eb is not None else -1
            k1 = {"出場日": exd == e["出場日"], "出場種類": NAMES[kind] == e["出場種類"], "持有天數": hold == int(e["持有天數"]),
                  "R": bool(abs(R_ - float(e["R"])) < 1e-10), "進場日＝T＋1": idx[s] == T + 1}
            path = [(str(cal[idx[j]].date()), round(float(c[j]), 4), round(float(EC[j]), 4)) for j in range(s, (eb if eb is not None else s) + 1)][:60]
            res["K1"].append({"世界": wn, "sid": sid, "T": e["T"], "進場價(還原開)": float(o[s]), "出場日": exd, "出場價": float(px), "種類": NAMES[kind],
                              "持有天數": hold, "R手算": float(R_), "R檔案": float(e["R"]), "路徑(日期,收,EMA9)": path, **k1})
            # K2
            cand = sorted([x for x, v in PR.items() if T in v and x != sid and x not in rawA.get(e["T"], set())], key=lambda x: W["ix"][x])
            ci = np.array([W["ix"][x] for x in cand], np.int64)
            g = np.random.default_rng([20261018, 1, T, zlib.crc32(sid.encode("utf-8"))])
            dr = np.sort(g.choice(ci, size=min(20, len(ci)), replace=False)) if len(ci) else ci
            names_d = [W["sids"][x] for x in dr]
            stored = [x for x in str(e["對照代號"]).split(";") if x and x != "nan"]
            cmean = float(np.mean([PR[x][T] for x in names_d])) if names_d else np.nan
            k2 = {"對照名單相同": names_d == stored, "對照平均R相同": bool(abs(cmean - float(e["對照平均R"])) < 1e-10),
                  "對照數": len(names_d) == int(e["對照數"])}
            res["K2"].append({"世界": wn, "sid": sid, "T": e["T"], "池大小(自算)": len(cand), "對照平均R自算": cmean, "檔案": float(e["對照平均R"]), **k2})
            # K3
            k3 = {"截在T仍偵測到": k in det_at(h[:k + 1], l[:k + 1], c[:k + 1], bad[:k + 1]),
                  "截在T−1無此T": k not in det_at(h[:k], l[:k], c[:k], bad[:k])}
            if kind in (3,) or (sg is not None):
                j = sg
                _, Et, *_ = MF.indicators(h[:j + 1], l[:j + 1], c[:j + 1], bad[:j + 1])
                k3["EMA9c截斷＝全序列"] = bool(np.allclose(Et, EC[:j + 1], equal_nan=True, rtol=0, atol=1e-9))
                s_j, *_ = exit_loop(o, c, Et, bad, dnl, idx, s, j + 1, n0 - 1)
                k3["截在j訊號恰在j"] = s_j == j
                if j > s:
                    s_j1, *_ = exit_loop(o, c, Et, bad, dnl, idx, s, j, n0 - 1)
                    k3["截在j−1無訊號"] = s_j1 is None
            elif kind == 4:
                k3["強制：下一根為壞K"] = bool(eb + 1 < len(idx) and bad[eb + 1])
                k3["強制前無訊號"] = all(not (c[q] < EC[q] and EC[q] < EC[q - 1]) for q in range(s, eb + 1))
            res["K3"].append({"世界": wn, "sid": sid, "T": e["T"], **k3})
            bad_ = [x for x, v in {**k1, **k2, **k3}.items() if not v]
            if bad_:
                fails.append({"世界": wn, "sid": sid, "T": e["T"], "不符": bad_})
            log(f"{wn} {sid} T={e['T']} 出場 {exd} {NAMES[kind]} 持有 {hold} R {R_:+.4%}（檔 {float(e['R']):+.4%}）｜池 {len(cand)} 對照均 {cmean:+.4%}"
                f"（檔 {float(e['對照平均R']):+.4%}）｜{'✔' if not bad_ else bad_}")
    # K4
    for wn, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for cell in ("A", "D1_26", "D2_無方向"):
            tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str}, keep_default_na=False, na_values=[""])
            tr["X"] = tr["X"].astype(float)
            for sg in sgs:
                a_, b_ = J["世界"][wn]["段"][sg].split("～")
                d = tr[(tr["T"] >= a_) & (tr["T"] <= b_) & np.isfinite(tr["X"])]
                x = d["X"].to_numpy(); mo = d["T"].str[:7].to_numpy()
                mu = x.mean(); s_ = pd.Series(x - mu).groupby(mo).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(x)
                ne = min(len(x), len(s_))
                win = float(((d["R"].astype(float) - COST) > 0).mean()); hm = float(d["持有天數"].astype(float).mean())
                st = J["世界"][wn]["格"][sg][cell]
                ok = (abs(mu - st["X̄"]) < 1e-12 and abs(se - st["se"]) < 1e-12 and ne == st["n_eff"] and len(x) == st["n"]
                      and abs(win - st["勝率"]) < 1e-12 and abs(hm - st["平均持有天數"]) < 1e-9)
                res["K4"].append({"世界": wn, "段": sg, "格": cell, "n": len(x), "X̄": mu, "se": se, "n_eff": ne, "勝率": win, "平均持有": hm, "相符": ok})
                log(f"K4 {wn}/{sg}/{cell}：n={len(x)} X̄={mu:+.4%} se={se:.4%} n_eff={ne} 勝率={win:.3f} 持有均={hm:.2f}｜{'✔' if ok else '✖'}")
                if not ok:
                    fails.append({"K4": f"{wn}/{sg}/{cell}"})
    res["不符"] = fails
    res["結論"] = "全部相符（K1 20 筆出場與報酬、K2 對照重建、K3 不前視、K4 彙總）" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

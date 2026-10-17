# -*- coding: utf-8 -*-
"""researchTurtle 對帳（海龜 Donchian 突破 seq2 事件層正式跑，登錄 sha 87b39da0f38816e0）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtle_check
輸出 backtest/resultsTurtle/check.json、check.log（⛔ 不碰 freq/）

K1 抽 20 筆判定格交易（主：S1 6、S2 6；早年：S1 4、S2 4；default_rng(20261017)；從 trades_<世界>_<格>.csv.gz 中 X 可算者）逐根手算：
   ⛔ 不呼叫 researchTurtle 的 natr／chan_low／sim_*：N 用本檔逐根迴圈（段首＝第 0 根或壞 K 棒、TR 從段首＋1、前 20 個 TR 平均為種子、(N×19＋TR)÷20）；
   前 N 日最高、前 M 日最低逐窗取 max／min；買價 ＝ max(開盤, 前 N 日最高)；停損 ＝ 買價 − 2N[T−1]；
   T＋1 起逐根：下一根壞 ⇒ 前一根收盤強制；最低 ＜ 通道 ⇒ min(開, 通道)；最低 ≤ 停損 ⇒ min(開, 停損)；同根取低；鎖死跌停 ⇒ 順延到第一根非鎖死開盤；
   比對 買價、N、停損價、出場日、出場種類、持有天數、R（|差| ＜ 1e−10）。
K2 對照重建（同 20 筆）：逐檔掃整個世界，自算 T 當天母體（含 T 的 20 日都有成交 ∧ T−20～T−1 日均量 ≥ 500,000 股 ∧ pit_valid）、
   T 非壞 K 棒、T 開盤有效且非開盤鎖漲停、N[T−1] 有值（本檔迴圈）、R 可算（本檔出場迴圈、T 開盤進場、停損 ＝ 開盤 − 2N[T−1]）；
   扣自己與已提交頻率表事件檔 T 當天同系統原始偵測 ⇒ 依種子 [20261017, 格標, T, crc32(sid)] 重抽 ⇒ 名單 ＝ 檔案「對照代號」；對照平均 R 自算 ＝ 檔案。
K3 不前視：同 20 筆 ①資料截在 T 重跑頻率表偵測 ⇒ 該事件仍在；②N 截在 T−1 重算 ＝ 全序列 N[T−1]；③出場迴圈只給 ≤ 觸發根 ⇒ 觸發恰在該根；
   只給 ≤ 觸發根−1 ⇒ 尚無觸發（強制出場：下一根確為壞 K 棒、之前無觸發）。
K4 彙總重算：由 trades 檔自算 S1、S2 各段 X̄、曆月分群 SE、n_eff ＝ Turtle.json。
K5 持有限制：全部 S1、S2 交易檔：同檔下一筆 T ＞ 上一筆出場日；資料尾未出場之後無同檔交易。
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
from backtest import researchTurtle_freq as RTF             # noqa: E402  只用於 K3 截斷偵測、事件檔路徑
from backtest import researchTurtle_freq_check as RFC       # noqa: E402  bars_of
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsTurtle"
NS = {"S1": 20, "S2": 55}; MS = {"S1": 10, "S2": 20}; TAGS = {"S1": 1, "S2": 2}
NAMES = {1: "通道出場訊號(跌破10/20日低點)", 2: "2N停損", 3: "壞根前一根收盤強制", 4: "末根收盤(下市/之後無成交)", 5: "資料尾未出場"}
LOG = []
_G = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def n_loop(h, l, c, bad):
    nb = len(c); N = [np.nan] * nb
    s = 0; cnt = 0; acc = 0.0; v = None
    for j in range(nb):
        if j == 0 or bad[j]:
            s = j; cnt = 0; acc = 0.0; v = None
            continue
        tr = max(h[j] - l[j], abs(h[j] - c[j - 1]), abs(l[j] - c[j - 1]))
        if v is None:
            acc += tr; cnt += 1
            if cnt == 20:
                v = acc / 20.0; N[j] = v
        else:
            v = (v * 19.0 + tr) / 20.0; N[j] = v
    return np.array(N, float)


def exit_loop(o, l, c, bad, dnl, idx, s, stop, M, n_end, last_cal):
    """盤中觸價出場（自寫）。只看第 0..n_end−1 根。回 (觸發根或 None, 出場根或 None, 價, 種類, 順延)。"""
    def tail():
        if last_cal - idx[n_end - 1] >= 5:
            return n_end - 1, c[n_end - 1], 4
        return None, np.nan, 5
    j = s + 1
    while True:
        if j >= n_end:
            e = tail(); return None, e[0], e[1], e[2], False
        if bad[j]:
            return None, j - 1, c[j - 1], 3, False
        chan = min(l[j - M:j])
        tc = l[j] < chan; ts = l[j] <= stop
        if tc or ts:
            ty = 2 if ts else 1
            if dnl[j]:
                y = j + 1
                while y < n_end:
                    if bad[y]:
                        return j, y - 1, c[y - 1], 3, True
                    if not dnl[y]:
                        p = o[y] if (np.isfinite(o[y]) and o[y] > 0) else c[y]
                        return j, y, p, ty, True
                    y += 1
                e = tail(); return j, e[0], e[1], e[2], True
            ok = np.isfinite(o[j]) and o[j] > 0
            pc = min(o[j], chan) if ok else chan
            ps = min(o[j], stop) if ok else stop
            if tc and ts:
                return j, j, min(pc, ps), (2 if ps <= pc else 1), False
            return j, j, (pc if tc else ps), (1 if tc else 2), False
        j += 1


def pool_job(a):
    wn, sid, Ts = a
    W = _G[wn]; n0 = W["n0"]; i = W["ix"][sid]
    D.DATA = W["data"]
    try:
        B, idx, bad = RFC.bars_of(W, sid)
    except Exception:
        return sid, {}
    if B is None:
        return sid, {}
    df = B["df"]; o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    vol = df["volume"].to_numpy(float); trd = df["traded"].to_numpy(bool)
    dnl = np.asarray(W["DNL"][i][idx], bool)
    Nv = None; out = {"S1": {}, "S2": {}}
    for T in Ts:
        if T < 20 or not trd[T]:
            continue
        if not (trd[T - 19:T + 1].all() and np.isfinite(vol[T - 20:T]).all() and np.nanmean(vol[T - 20:T]) >= 500_000):
            continue
        if not W["PV"][i][T]:
            continue
        k = int(np.searchsorted(idx, T))
        if not (k < len(idx) and idx[k] == T) or k < 1 or bad[k]:
            continue
        if not (np.isfinite(W["O"][i][T]) and W["O"][i][T] > 0 and not W["UPL"][i][T] and np.isfinite(o[k]) and o[k] > 0):
            continue
        if Nv is None:
            Nv = n_loop(h, l, c, bad)
        if not np.isfinite(Nv[k - 1]):
            continue
        stop = o[k] - 2.0 * Nv[k - 1]
        for sy, M in MS.items():
            tg, eb, px, kind, _ = exit_loop(o, l, c, bad, dnl, idx, k, stop, M, len(idx), n0 - 1)
            if kind == 5:
                continue
            out[sy][T] = px / o[k] - 1.0
    return sid, out


def main():
    rng = np.random.default_rng(20261017)
    J = json.load(open(os.path.join(OUT, "Turtle.json"), encoding="utf-8"))
    res = {"K1": [], "K2": [], "K3": [], "K4": [], "K5": []}; fails = []
    for wn, plan in (("主", (("S1", 6), ("S2", 6))), ("早年", (("S1", 4), ("S2", 4)))):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; _G[wn] = W
        pos = {str(d.date()): j for j, d in enumerate(cal)}
        fev = pd.read_csv(os.path.join(RTF.OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        picks = []
        for cell, m in plan:
            tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str, "對照代號": str}, keep_default_na=False, na_values=[""])
            trx = tr[np.isfinite(tr["X"].astype(float))].reset_index(drop=True)
            pk = trx.iloc[np.sort(rng.choice(len(trx), m, replace=False))].reset_index(drop=True)
            picks += [(cell, e) for _, e in pk.iterrows()]
        Ts = sorted(set(pos[e["T"]] for _, e in picks))
        with Pool(3) as pool:
            PR = dict(pool.imap_unordered(pool_job, [(wn, s, Ts) for s in W["sids"]], chunksize=16))
        log(f"[{wn}] 全世界 {len(W['sids'])} 檔重建對照池（{len(Ts)} 個 T）完成")
        for cell, e in picks:
            sid = e["sid"]; T = pos[e["T"]]; N = NS[cell]; M = MS[cell]; i = W["ix"][sid]
            B, idx, bad = RFC.bars_of(W, sid)
            o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
            dnl = np.asarray(W["DNL"][i][idx], bool)
            k = int(np.searchsorted(idx, T))
            Nv = n_loop(h, l, c, bad)
            pm = max(h[k - N:k]); P = max(o[k], pm); stop = P - 2.0 * Nv[k - 1]
            tg, eb, px, kind, post = exit_loop(o, l, c, bad, dnl, idx, k, stop, M, len(idx), n0 - 1)
            R_ = px / P - 1.0
            exd = str(cal[idx[eb]].date()) if eb is not None else ""
            hold = int(idx[eb] - idx[k]) if eb is not None else -1
            k1 = {"T為突破(最高>前N日最高)": bool(h[k] > pm), "買價": abs(P - float(e["買價"])) < 1e-9, "N(T−1)": abs(Nv[k - 1] - float(e["N"])) < 1e-9,
                  "停損價": abs(stop - float(e["停損價"])) < 1e-9, "出場日": exd == e["出場日"], "出場種類": NAMES[kind] == e["出場種類"],
                  "持有天數": hold == int(e["持有天數"]), "R": bool(abs(R_ - float(e["R"])) < 1e-10)}
            end = eb if eb is not None else k
            path = [(str(cal[idx[j]].date()), round(float(o[j]), 3), round(float(l[j]), 3), round(float(min(l[j - M:j])), 3)) for j in range(k + 1, end + 1)][:60]
            res["K1"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "前N日最高": float(pm), "開盤": float(o[k]), "買價": float(P), "N(T−1)": float(Nv[k - 1]),
                              "停損價": float(stop), "出場日": exd, "出場價": float(px), "種類": NAMES[kind], "順延": post, "持有天數": hold,
                              "R手算": float(R_), "R檔案": float(e["R"]), "路徑(日期,開,低,通道)": path, **k1})
            # K2
            raw = set(fev[(fev["格"] == cell) & (fev["T"] == e["T"])]["sid"])
            cand = sorted([x for x, v in PR.items() if T in v.get(cell, {}) and x != sid and x not in raw], key=lambda x: W["ix"][x])
            ci = np.array([W["ix"][x] for x in cand], np.int64)
            g = np.random.default_rng([20261017, TAGS[cell], T, zlib.crc32(sid.encode("utf-8"))])
            dr = np.sort(g.choice(ci, size=min(20, len(ci)), replace=False)) if len(ci) else ci
            names_d = [W["sids"][x] for x in dr]
            stored = [x for x in str(e["對照代號"]).split(";") if x and x != "nan"]
            cmean = float(np.mean([PR[x][cell][T] for x in names_d])) if names_d else np.nan
            k2 = {"對照名單相同": names_d == stored, "對照平均R相同": bool(abs(cmean - float(e["對照平均R"])) < 1e-10), "對照數": len(names_d) == int(e["對照數"])}
            res["K2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "池大小(自算)": len(cand), "對照平均R自算": cmean, "檔案": float(e["對照平均R"]), **k2})
            # K3
            k3 = {}
            ks, _ = RTF.detect(h[:k + 1], c[:k + 1], bad[:k + 1], N)
            k3["截在T仍偵測到"] = bool(k in set(int(z) for z in ks))
            Nt = n_loop(h[:k], l[:k], c[:k], bad[:k])
            k3["N截在T−1＝全序列"] = bool(abs(Nt[k - 1] - Nv[k - 1]) < 1e-12)
            if tg is not None:
                t2, *_ = exit_loop(o, l, c, bad, dnl, idx, k, stop, M, tg + 1, n0 - 1)
                k3["截在觸發根：觸發恰在該根"] = t2 == tg
                if tg > k + 1:
                    t3, e3, _, kd3, _ = exit_loop(o, l, c, bad, dnl, idx, k, stop, M, tg, n0 - 1)
                    k3["截在觸發根−1：尚無觸發"] = t3 is None and kd3 in (4, 5)
            elif kind == 3:
                k3["強制：下一根為壞K"] = bool(eb + 1 < len(idx) and bad[eb + 1])
                k3["強制前無觸發"] = all(not (l[q] < min(l[q - M:q]) or l[q] <= stop) for q in range(k + 1, eb + 1))
            res["K3"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], **k3})
            bad_ = [x for x, v in {**k1, **k2, **k3}.items() if not v]
            if bad_:
                fails.append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "不符": bad_})
            log(f"{wn} {cell} {sid} T={e['T']} 買 {P:.4f}（開 {o[k]:.4f}／前{N}高 {pm:.4f}）N {Nv[k - 1]:.4f} 停損 {stop:.4f}｜出場 {exd} {NAMES[kind]}"
                f"{'(順延)' if post else ''} 價 {px:.4f} 持有 {hold} R {R_:+.4%}（檔 {float(e['R']):+.4%}）｜池 {len(cand)} 對照均 {cmean:+.4%}"
                f"（檔 {float(e['對照平均R']):+.4%}）｜{'✔' if not bad_ else bad_}")
    # K4、K5
    for wn, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for cell in ("S1", "S2"):
            tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str}, keep_default_na=False, na_values=[""])
            tr["X"] = tr["X"].astype(float)
            for sg in sgs:
                a_, b_ = J["世界"][wn]["段"][sg].split("～")
                d = tr[(tr["T"] >= a_) & (tr["T"] <= b_) & np.isfinite(tr["X"])]
                x = d["X"].to_numpy(); mo = d["T"].str[:7].to_numpy()
                mu = x.mean(); s_ = pd.Series(x - mu).groupby(mo).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(x)
                ne = min(len(x), len(s_))
                st = J["世界"][wn]["格"][sg][cell]
                ok = abs(mu - st["X̄"]) < 1e-12 and abs(se - st["se"]) < 1e-12 and ne == st["n_eff"] and len(x) == st["n"]
                res["K4"].append({"世界": wn, "格": cell, "段": sg, "n": len(x), "X̄": mu, "se": se, "n_eff": ne, "相符": ok})
                log(f"K4 {wn}/{cell}/{sg}：n={len(x)} X̄={mu:+.4%} se={se:.4%} n_eff={ne}｜{'✔' if ok else '✖'}")
                if not ok:
                    fails.append({"K4": f"{wn}/{cell}/{sg}"})
            viol = 0; after_open = 0
            for sid, g in tr.sort_values(["sid", "T"]).groupby("sid"):
                sells = g["出場日"].tolist(); Ts_ = g["T"].tolist(); kinds = g["出場種類"].tolist()
                for q in range(1, len(g)):
                    if kinds[q - 1] == NAMES[5]:
                        after_open += 1
                    elif not Ts_[q] > sells[q - 1]:
                        viol += 1
            ok5 = viol == 0 and after_open == 0
            res["K5"].append({"世界": wn, "格": cell, "交易數": len(tr), "T未晚於上一筆出場日": viol, "資料尾未出場後仍有交易": after_open, "相符": ok5})
            log(f"K5 {wn}/{cell}：{len(tr)} 筆，持有中再進 {viol}、資料尾後再進 {after_open}｜{'✔' if ok5 else '✖'}")
            if not ok5:
                fails.append({"K5": f"{wn}/{cell}"})
    res["不符"] = fails
    res["結論"] = "全部相符（K1 20 筆進出場價與報酬、2N 停損、K2 對照重建、K3 不前視、K4 彙總、K5 持有限制）" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

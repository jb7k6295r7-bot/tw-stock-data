# -*- coding: utf-8 -*-
"""researchBB 對帳（布林 Method I／II seq1 事件層正式跑，登錄 sha d5ac888e15ab1418）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBB_check
輸出 backtest/resultsBB/check.json、check.log（⛔ 不碰 freq/）

K1 抽 20 筆判定格交易（主：M1 6、M2 6；早年：M1 4、M2 4；default_rng(20261018)；從 trades_<世界>_<格>.csv.gz 中 X 可算者）逐根手算：
   ⛔ 不呼叫 researchBB 的 sim／sim_ref／sar_path、researchBB_freq 的 boll：軌道用本檔逐窗 math 計算（20 根收盤平均、母體標準差）；
   SAR 起點 ＝ 進場前 20 根最低價逐窗取 min；SAR 逐根：EP 起始＝進場根最高、新高才 AF＋0.02（上限 0.20）、明日 SAR ＝ min(今 SAR＋AF×(EP−今 SAR), 今低, 昨低)；
   M1：自進場根起逐根，下一根壞 ⇒ 前一根收盤強制；最低 ≤ SAR 或 ≤ 前一根下軌 ⇒ min(開, 先到＝較高價位)；鎖死跌停 ⇒ 順延；
   M2：收盤 ＜ 中軌 ⇒ 下一根開盤；比對 買價、SAR 起點、出場日、出場種類、出場價、持有天數、R（|差| ＜ 1e−10）。另列逐根路徑（日期、開、低、收、SAR、軌道）。
K2 對照重建（同 20 筆）：逐檔掃整個世界，自算 T 當天母體（含 T 的 20 日都有成交 ∧ T−20～T−1 日均量 ≥ 500,000 股 ∧ pit_valid）、T 非壞 K 棒、
   T＋1 可買、T 的 20 根相連（布林窗有值）、R 可算（本檔出場迴圈）；扣自己與已提交頻率表事件檔 T 當天同格原始偵測 ⇒ 依種子 [20261018, 格標, T, crc32(sid)]
   重抽 ⇒ 名單 ＝ 檔案「對照代號」；對照平均 R 自算 ＝ 檔案。
K3 不前視：同 20 筆 ①資料截在 T 重跑頻率表偵測 ⇒ 該事件仍在、截在 T−1 ⇒ 無；②每根 SAR 用截在前一根的資料重算 ＝ 全序列；
   ③出場迴圈只給 ≤ 觸發根 ⇒ 觸發恰在該根；只給 ≤ 觸發根−1 ⇒ 尚無觸發（強制出場：下一根確為壞 K 棒、之前無觸發）。
K4 彙總重算：由 trades 檔自算 M1、M2、M1_收盤判 各段 X̄、曆月分群 SE、n_eff、勝率、平均賺賠比、平均持有天數 ＝ BB.json；盤中−收盤判差（線性化 SE）＝ BB.json。
K5 持有限制：M1、M2、M1_收盤判 全部交易檔：同檔下一筆 T ≥ 上一筆出場日；資料尾未出場之後無同檔交易。
"""
from __future__ import annotations

import json
import math
import os
import sys
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchBB_freq as BBF                 # noqa: E402  只用於 K3 截斷偵測、事件檔路徑
from backtest import researchBB_freq_check as BFC           # noqa: E402  mod_det（截斷偵測）
from backtest import researchTurtle_freq_check as RTC       # noqa: E402  bars_of
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsBB"
TAGS = {"M1": 1, "M2": 2}
NAMES = {1: "SAR出場訊號", 2: "碰下軌出場訊號", 3: "跌破中軌出場訊號", 4: "壞根前一根收盤強制", 5: "末根收盤(下市/之後無成交)", 6: "資料尾未出場"}
COST = 0.00585
LOG = []
_G = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


class Bands:
    """逐窗 math 計算（快取）：中軌、下軌；窗內（除第一根）有壞 K 棒 ⇒ None。"""
    def __init__(self, c, bad):
        self.c = c; self.bad = bad; self.cache = {}

    def at(self, k):
        if k in self.cache:
            return self.cache[k]
        r = None
        if k >= 19 and not any(self.bad[j] for j in range(k - 18, k + 1)):
            x = [float(v) for v in self.c[k - 19:k + 1]]; m = sum(x) / 20.0
            sd = math.sqrt(sum((v - m) ** 2 for v in x) / 20.0)
            r = (m, m - 2.0 * sd)
        self.cache[k] = r
        return r


def exit_loop(cell, o, h, l, c, bad, dnl, idx, s, n_end, last_cal, bands, rec=None):
    """本檔自寫出場。只看第 0..n_end−1 根。回 (觸發根或 None, 出場根或 None, 價, 種類, 順延)。"""
    def tail():
        if last_cal - idx[n_end - 1] >= 5:
            return n_end - 1, c[n_end - 1], 5
        return None, np.nan, 6

    def defer(y, ty):
        while y < n_end:
            if bad[y]:
                return y - 1, c[y - 1], 4
            if not dnl[y]:
                return y, (o[y] if (np.isfinite(o[y]) and o[y] > 0) else c[y]), ty
            y += 1
        return tail()
    sar = min(float(v) for v in l[s - 20:s]); ep = h[s]; af = 0.02
    j = s
    while True:
        if j >= n_end:
            e = tail(); return None, e[0], e[1], e[2], False
        if j > s and bad[j]:
            return None, j - 1, c[j - 1], 4, False
        if cell == "M1":
            lb = bands.at(j - 1)[1]
            if rec is not None:
                rec.append((j, sar, lb))
            hs = l[j] <= sar; hb = l[j] <= lb
            if hs or hb:
                if hs and hb:
                    lvl = max(sar, lb); ty = 1 if sar >= lb else 2
                else:
                    lvl = sar if hs else lb; ty = 1 if hs else 2
                if dnl[j]:
                    e = defer(j + 1, ty); return j, e[0], e[1], e[2], True
                ok = np.isfinite(o[j]) and o[j] > 0
                return j, j, (min(o[j], lvl) if ok else lvl), ty, False
            # 明日 SAR
            if j > s and h[j] > ep:
                ep = h[j]; af = min(round(af + 0.02, 10), 0.20)
            sar = min(sar + af * (ep - sar), l[j], l[j - 1])
        else:
            mid = bands.at(j)[0]
            if rec is not None:
                rec.append((j, None, mid))
            if c[j] < mid:
                if j + 1 >= n_end:
                    if last_cal - idx[n_end - 1] >= 5:
                        return j, j, c[j], 5, False
                    return j, None, np.nan, 6, False
                if bad[j + 1]:
                    return j, j, c[j], 4, False
                if dnl[j + 1]:
                    e = defer(j + 1, 3); return j, e[0], e[1], e[2], True
                return j, j + 1, (o[j + 1] if (np.isfinite(o[j + 1]) and o[j + 1] > 0) else c[j + 1]), 3, False
        j += 1


def sar_at(h, l, s, upto):
    """SAR[upto]（只用 ≤ upto−1 的資料；不判出場）。"""
    sar = min(float(v) for v in l[s - 20:s]); ep = h[s]; af = 0.02
    for j in range(s, upto):
        if j > s and h[j] > ep:
            ep = h[j]; af = min(round(af + 0.02, 10), 0.20)
        sar = min(sar + af * (ep - sar), l[j], l[j - 1])
    return sar


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
    bands = Bands(c, bad); out = {"M1": {}, "M2": {}}
    for T in Ts:
        if T < 20 or not trd[T]:
            continue
        if not (trd[T - 19:T + 1].all() and np.isfinite(vol[T - 20:T]).all() and np.nanmean(vol[T - 20:T]) >= 500_000):
            continue
        if not W["PV"][i][T]:
            continue
        k = int(np.searchsorted(idx, T))
        if not (k < len(idx) and idx[k] == T) or bad[k]:
            continue
        if not (k + 1 < len(idx) and idx[k + 1] == T + 1 and T + 1 < n0 and W["TRD"][i][T + 1] and np.isfinite(W["O"][i][T + 1])
                and W["O"][i][T + 1] > 0 and not W["UPL"][i][T + 1] and not bad[k + 1] and np.isfinite(o[k + 1]) and o[k + 1] > 0):
            continue
        if bands.at(k) is None:
            continue
        s = k + 1
        for cell in ("M1", "M2"):
            tg, eb, px, kind, _ = exit_loop(cell, o, h, l, c, bad, dnl, idx, s, len(idx), n0 - 1, bands)
            if kind == 6:
                continue
            out[cell][T] = px / o[s] - 1.0
    return sid, out


def main():
    rng = np.random.default_rng(20261018)
    J = json.load(open(os.path.join(OUT, "BB.json"), encoding="utf-8"))
    res = {"K1": [], "K2": [], "K3": [], "K4": [], "K5": []}; fails = []
    for wn, plan in (("主", (("M1", 6), ("M2", 6))), ("早年", (("M1", 4), ("M2", 4)))):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; _G[wn] = W
        pos = {str(d.date()): j for j, d in enumerate(cal)}
        fev = pd.read_csv(os.path.join(BBF.OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        picks = []
        for cell, m in plan:
            tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str, "對照代號": str}, keep_default_na=False, na_values=[""])
            trx = tr[np.isfinite(tr["X"].astype(float))].reset_index(drop=True)
            pk = trx.iloc[np.sort(rng.choice(len(trx), m, replace=False))].reset_index(drop=True)
            picks += [(cell, e) for _, e in pk.iterrows()]
        Ts = sorted(set(pos[e["T"]] for _, e in picks))
        with Pool(2) as pool:
            PR = dict(pool.imap_unordered(pool_job, [(wn, s, Ts) for s in W["sids"]], chunksize=16))
        log(f"[{wn}] 全世界 {len(W['sids'])} 檔重建對照池（{len(Ts)} 個 T）完成")
        for cell, e in picks:
            sid = e["sid"]; T = pos[e["T"]]; i = W["ix"][sid]
            B, idx, bad = RTC.bars_of(W, sid)
            o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
            df = B["df"]; v = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
            rc = np.asarray(B["rc"], float); F = np.where(rc > 0, c / rc, np.nan)
            dnl = np.asarray(W["DNL"][i][idx], bool)
            k = int(np.searchsorted(idx, T)); s = k + 1
            bands = Bands(c, bad); path = []
            tg, eb, px, kind, post = exit_loop(cell, o, h, l, c, bad, dnl, idx, s, len(idx), n0 - 1, bands, rec=path)
            P = o[s]; sar0 = min(float(x) for x in l[s - 20:s])
            R_ = px / P - 1.0
            exd = str(cal[idx[eb]].date()) if eb is not None else ""
            hold = int(idx[eb] - idx[s]) if eb is not None else -1
            k1 = {"進場日＝T＋1": str(cal[idx[s]].date()) == e["進場日"], "買價": abs(P - float(e["買價"])) < 1e-9,
                  "SAR起點": abs(sar0 - float(e["SAR起點(前20日最低)"])) < 1e-9, "出場日": exd == e["出場日"], "出場種類": NAMES[kind] == e["出場種類"],
                  "出場價": abs(px - float(e["出場價"])) < 1e-9, "持有天數": hold == int(e["持有天數"]), "R": bool(abs(R_ - float(e["R"])) < 1e-10)}
            pth = [(str(cal[idx[j]].date()), round(float(o[j]), 4), round(float(l[j]), 4), round(float(c[j]), 4),
                    None if sv is None else round(float(sv), 4), round(float(bd), 4)) for j, sv, bd in path][:80]
            res["K1"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "買價(T+1開)": float(P), "SAR起點": sar0, "出場日": exd, "出場價": float(px),
                              "種類": NAMES[kind], "順延": post, "持有天數": hold, "R手算": float(R_), "R檔案": float(e["R"]),
                              "路徑(日期,開,低,收,SAR,軌道[M1前一根下軌/M2中軌])": pth, **k1})
            # K2
            raw = set(fev[(fev["格"] == cell) & (fev["T"] == e["T"])]["sid"])
            cand = sorted([x for x, vv in PR.items() if T in vv.get(cell, {}) and x != sid and x not in raw], key=lambda x: W["ix"][x])
            ci = np.array([W["ix"][x] for x in cand], np.int64)
            g = np.random.default_rng([20261018, TAGS[cell], T, zlib.crc32(sid.encode("utf-8"))])
            dr = np.sort(g.choice(ci, size=min(20, len(ci)), replace=False)) if len(ci) else ci
            names_d = [W["sids"][x] for x in dr]
            stored = [x for x in str(e["對照代號"]).split(";") if x and x != "nan"]
            cmean = float(np.mean([PR[x][cell][T] for x in names_d])) if names_d else np.nan
            k2 = {"對照名單相同": names_d == stored, "對照平均R相同": bool(abs(cmean - float(e["對照平均R"])) < 1e-10), "對照數": len(names_d) == int(e["對照數"]),
                  "X相同": bool(abs((R_ - cmean) - float(e["X"])) < 1e-10)}
            res["K2"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "池大小(自算)": len(cand), "對照平均R自算": cmean, "檔案": float(e["對照平均R"]), **k2})
            # K3
            k3 = {"截在T仍偵測到": k in BFC.mod_det(cell, h[:k + 1], l[:k + 1], c[:k + 1], v[:k + 1], F[:k + 1], bad[:k + 1]),
                  "截在T−1無此T": k not in BFC.mod_det(cell, h[:k], l[:k], c[:k], v[:k], F[:k], bad[:k])}
            if cell == "M1":
                endj = eb if eb is not None else len(idx) - 1
                okp = True
                for jj, sv, _ in path:
                    hh = h[:jj].copy(); ll_ = l[:jj].copy()                 # 只給 ≤ jj−1 的資料
                    okp &= abs(sar_at(hh, ll_, s, jj) - sv) < 1e-12 if jj > s else abs(sv - sar0) < 1e-15
                k3["SAR每根只用前一根以前資料"] = bool(okp)
            if tg is not None:
                t2, *_ = exit_loop(cell, o, h, l, c, bad, dnl, idx, s, tg + 1, n0 - 1, Bands(c[:tg + 1], bad[:tg + 1]))
                k3["截在觸發根：觸發恰在該根"] = t2 == tg
                if tg > s:
                    t3, e3, _, kd3, _ = exit_loop(cell, o, h, l, c, bad, dnl, idx, s, tg, n0 - 1, Bands(c[:tg], bad[:tg]))
                    k3["截在觸發根−1：尚無觸發"] = t3 is None and kd3 in (5, 6)
            elif kind == 4:
                k3["強制：下一根為壞K"] = bool(eb + 1 < len(idx) and bad[eb + 1])
            res["K3"].append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], **k3})
            bad_ = [x for x, vv in {**k1, **k2, **k3}.items() if not vv]
            if bad_:
                fails.append({"世界": wn, "格": cell, "sid": sid, "T": e["T"], "不符": bad_})
            log(f"{wn} {cell} {sid} T={e['T']} 買 {P:.4f} SAR起 {sar0:.4f}｜出場 {exd} {NAMES[kind]}{'(順延)' if post else ''} 價 {px:.4f} 持有 {hold} "
                f"R {R_:+.4%}（檔 {float(e['R']):+.4%}）｜池 {len(cand)} 對照均 {cmean:+.4%}（檔 {float(e['對照平均R']):+.4%}）｜{'✔' if not bad_ else bad_}")
    # K4、K5
    for wn, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        TRS = {}
        for cell in ("M1", "M2", "M1_收盤判"):
            tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str}, keep_default_na=False, na_values=[""])
            tr["X"] = tr["X"].astype(float); tr["R"] = tr["R"].astype(float); TRS[cell] = tr
            for sg in sgs:
                a_, b_ = J["世界"][wn]["段"][sg].split("～")
                d = tr[(tr["T"] >= a_) & (tr["T"] <= b_) & np.isfinite(tr["X"])]
                x = d["X"].to_numpy(); mo = d["T"].str[:7].to_numpy()
                mu = x.mean(); s_ = pd.Series(x - mu).groupby(mo).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(x)
                ne = min(len(x), len(s_))
                rn = d["R"].to_numpy() - COST; w = rn[rn > 0]; lo_ = rn[rn <= 0]
                win = (rn > 0).mean(); pl = w.mean() / abs(lo_.mean()); hd = d["持有天數"].astype(float).mean()
                st = J["世界"][wn]["格"][sg][cell]
                ok = (abs(mu - st["X̄"]) < 1e-12 and abs(se - st["se"]) < 1e-12 and ne == st["n_eff"] and len(x) == st["n"]
                      and abs(win - st["勝率"]) < 1e-12 and abs(pl - st["平均賺賠比"]) < 1e-9 and abs(hd - st["平均持有天數"]) < 1e-9)
                res["K4"].append({"世界": wn, "格": cell, "段": sg, "n": len(x), "X̄": mu, "se": se, "n_eff": ne, "勝率": win, "賺賠比": pl, "持有均": hd, "相符": ok})
                log(f"K4 {wn}/{cell}/{sg}：n={len(x)} X̄={mu:+.4%} se={se:.4%} n_eff={ne} 勝率 {win:.3f} 賺賠比 {pl:.3f} 持有 {hd:.2f}｜{'✔' if ok else '✖'}")
                if not ok:
                    fails.append({"K4": f"{wn}/{cell}/{sg}"})
            viol = 0; after_open = 0
            for sid, g in tr.sort_values(["sid", "T"]).groupby("sid"):
                sells = g["出場日"].tolist(); Ts_ = g["T"].tolist(); kinds = g["出場種類"].tolist()
                for q in range(1, len(g)):
                    if kinds[q - 1] == NAMES[6]:
                        after_open += 1
                    elif not Ts_[q] >= sells[q - 1]:
                        viol += 1
            ok5 = viol == 0 and after_open == 0
            res["K5"].append({"世界": wn, "格": cell, "交易數": len(tr), "T早於上一筆出場日": viol, "資料尾未出場後仍有交易": after_open, "相符": ok5})
            log(f"K5 {wn}/{cell}：{len(tr)} 筆，持有中再進 {viol}、資料尾後再進 {after_open}｜{'✔' if ok5 else '✖'}")
            if not ok5:
                fails.append({"K5": f"{wn}/{cell}"})
        # 盤中−收盤判差（線性化 SE）重算
        for sg in sgs:
            a_, b_ = J["世界"][wn]["段"][sg].split("～")
            A = TRS["M1"]; Bc = TRS["M1_收盤判"]
            A = A[(A["T"] >= a_) & (A["T"] <= b_) & np.isfinite(A["X"])]; Bc = Bc[(Bc["T"] >= a_) & (Bc["T"] <= b_) & np.isfinite(Bc["X"])]
            m1, m2 = A["X"].mean(), Bc["X"].mean()
            ga = pd.Series(A["X"].to_numpy() - m1).groupby(A["T"].str[:7].to_numpy()).sum() / len(A)
            gb = pd.Series(Bc["X"].to_numpy() - m2).groupby(Bc["T"].str[:7].to_numpy()).sum() / len(Bc)
            dd = ga.sub(gb, fill_value=0.0); se = float(np.sqrt((dd ** 2).sum()))
            st = J["世界"][wn]["格"][sg]["M1"]["盤中−收盤判"]
            ok = abs((m1 - m2) - st["差(D2−A)"]) < 1e-12 and abs(se - st["se"]) < 1e-12
            res["K4"].append({"世界": wn, "格": "盤中−收盤判", "段": sg, "差": m1 - m2, "se": se, "相符": ok})
            log(f"K4 {wn}/盤中−收盤判/{sg}：差 {m1 - m2:+.4%} se {se:.4%}｜{'✔' if ok else '✖'}")
            if not ok:
                fails.append({"K4": f"{wn}/盤中−收盤判/{sg}"})
    res["不符"] = fails
    res["結論"] = "全部相符（K1 20 筆逐根 SAR／軌道、出場價與報酬、K2 對照重建、K3 不前視、K4 彙總、K5 持有限制）" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""researchPEAD 對帳（財報公告後漂移 PEAD seq1 事件層正式跑，登錄 sha af545cdcfa5bf94f）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEAD_check
輸出 backtest/resultsPEAD/check.json、check.log

（⛔ 不呼叫 researchPEAD 的出場、抽樣、統計函式；SUE 用 researchPEAD_freq_check 自寫 csv 迴圈、出場用 researchPTH_check 日曆 df 逐列手算）
K1 抽 20 筆判定格（上季切點）交易（default_rng(20261020)；trades_上季切點.csv.gz 中 X 可算者）：自讀 fin_hist 算 SUE、自讀 filing_dates 取
   AI1 最早（否則 AI2）、e ＝ 日曆第一個 ＞ 上傳日的交易日、SUE ≥ quarterly.csv 該季「上季切點」；出場 ＝ e＋59 收盤（逐根走、壞根前一根強制）。
   比 SUE、進場日、出場日、出場種類、R（|差| ＜ 1e−10）。
K2 對照重建（同 20 筆）：池 ＝ 主世界有成交日 ≥ 260 的股票 ∧ 自算閘（含 e 的 20 日都有成交 ∧ e−20～e−1 二十日成交量都有值且平均 ≥ 500,000 股
   〔Frame.gate rolling min_periods＝20 同義；researchUO_check 同式〕∧ pit_valid[e]）
   ∧ e 有成交、快取開盤 ＞ 0、非開盤鎖漲停 ∧ 自算 R60 可算 − 自己 − 已提交事件檔同 e 上季切點原始入選；種子 [20261020, 0, e, crc32(sid)] 重抽
   ⇒ 名單 ＝ 檔案「對照代號」、對照平均 R ＝ 檔案。
K3 不前視（同 20 筆）：e ＞ 上傳日 ＞ 季底；SUE 只用 q−12～q（自寫迴圈構造）；到期出場者 df 截在到期日重算 ＝ 全序列；壞根強制者下一根成交日確為壞 K 棒。
K4 彙總重算：由 trades 檔自算 上季切點、同季切點 各段 X̄、曆月分群 SE、n_eff ＝ PEAD.json。
K5 策略鎖：python -m backtest.strategy_lock --check 必須相符。
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world（BADPOS、快取旗標輸入）
from backtest import researchPEAD_freq_check as PFC         # noqa: E402  read_fin、sue（自寫 csv 迴圈）
from backtest import researchPTH_check as PC                # noqa: E402  bars、hand_exit（日曆 df 逐列手算）
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsPEAD"
FREQ = "backtest/resultsPEAD/freq"
LOG = []
_G = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def pool_job(a):
    sid, es = a
    W = _G["主"]; cal = W["cal"]; n0 = W["n0"]; w = W["ix"][sid]
    D.DATA = W["data"]
    try:
        st = D.load_stock(sid, W["mk"].get(sid, "twse"), cal)
    except Exception:
        return sid, None
    if st is None:
        return sid, None
    df = st.df
    trd = df["traded"].to_numpy(bool)
    if trd.sum() < 260:
        return sid, None
    pos, o, c, badc = PC.bars(W, sid)
    vol = df["volume"].to_numpy(float)
    pv = np.asarray(UG.pit_valid(sid, cal, W["data"]), bool)
    out = {}
    for e in es:
        g = bool(e >= 20 and trd[e - 19:e + 1].all() and np.isfinite(vol[e - 20:e]).all() and np.mean(vol[e - 20:e]) >= 500_000 and pv[e])
        if not (g and trd[e] and W["TRD"][w][e] and np.isfinite(W["O"][w][e]) and W["O"][w][e] > 0 and not W["UPL"][w][e]):
            continue
        r = PC.hand_exit(pos, o, c, badc, e, e + 59, n0)
        if r is not None and np.isfinite(r[1]):
            out[e] = r[1]
    return sid, out


def main():
    rng = np.random.default_rng(20261020)
    J = json.load(open(os.path.join(OUT, "PEAD.json"), encoding="utf-8"))
    res = {"K1": [], "K2": [], "K3": [], "K4": []}; fails = []
    W = AT.load_world("主"); cal = W["cal"]; n0 = W["n0"]; _G["主"] = W
    posd = {str(d.date()): j for j, d in enumerate(cal)}
    tr = pd.read_csv(os.path.join(OUT, "events", "trades_上季切點.csv.gz"), dtype={"sid": str, "對照代號": str}, keep_default_na=False, na_values=[""])
    trx = tr[np.isfinite(tr["X"].astype(float))].reset_index(drop=True)
    pick = trx.iloc[np.sort(rng.choice(len(trx), 20, replace=False))].reset_index(drop=True)
    fev = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str})
    rawA = fev[fev["上季切點_入選"]].groupby("e")["sid"].apply(set).to_dict()
    qt = pd.read_csv(os.path.join(FREQ, "quarterly.csv")).set_index("季")
    fin = PFC.read_fin()
    up = {}
    with open(os.path.join(PFC.WD, "meta", "filing_dates.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["doc_code"] in ("AI1", "AI2") and r["uploaded_at"]:
                k = (r["stock_id"], int(r["year"]) * 4 + int(r["season"]) - 1)
                up.setdefault(k, {}).setdefault(r["doc_code"], []).append(r["uploaded_at"])
    es = sorted(set(posd[x] for x in pick["進場日"]))
    with Pool(3) as pool:
        PR = dict(pool.imap_unordered(pool_job, [(s, es) for s in W["sids"]], chunksize=16))
    ok = sorted(s for s, v in PR.items() if v is not None)
    oki = {s: k for k, s in enumerate(ok)}
    log(f"全世界 {len(W['sids'])} 檔重建對照池（{len(es)} 個 e；有成交日 ≥ 260：{len(ok)} 檔）")
    for _, e in pick.iterrows():
        sid = e["sid"]; ee = posd[e["進場日"]]
        y, q = int(e["季"][:4]), int(e["季"][-1]); qi = y * 4 + q - 1
        v, why = PFC.sue(fin, sid, qi)
        u = up.get((sid, qi), {}); ts = min(u["AI1"]) if "AI1" in u else (min(u["AI2"]) if "AI2" in u else None)
        ud = pd.Timestamp(ts[:10]); e_h = int(cal.searchsorted(ud, side="right"))
        cut = float(qt.loc[e["季"], "上季切點"])
        pos, o, c, badc = PC.bars(W, sid)
        eb, Rh, kind = PC.hand_exit(pos, o, c, badc, ee, ee + 59, n0)
        exd = str(cal[eb].date()) if eb >= 0 else ""
        k1 = {"SUE": why == "ok" and abs(v - float(e["SUE"])) < 1e-9, "SUE≥上季切點": bool(v >= cut), "進場日": e_h == ee,
              "出場日": exd == e["出場日"], "出場種類": PC.NAMES[kind] == e["出場種類"], "R": bool(abs(Rh - float(e["R"])) < 1e-10)}
        res["K1"].append({"sid": sid, "季": e["季"], "SUE手算": v, "上季切點": cut, "上傳": ts, "進場日": e["進場日"], "進場價(還原開)": float(o[ee]),
                          "出場日": exd, "種類": PC.NAMES[kind], "R手算": float(Rh), "R檔案": float(e["R"]), **k1})
        cand = sorted([s for s in ok if s != sid and s not in rawA.get(e["進場日"], set()) and ee in PR[s]])
        ci = np.array([oki[s] for s in cand], np.int64)
        g = np.random.default_rng([20261020, 0, ee, zlib.crc32(sid.encode("utf-8"))])
        dr = np.sort(g.choice(ci, size=min(20, len(ci)), replace=False)) if len(ci) else ci
        names = [ok[x] for x in dr]
        stored = [x for x in str(e["對照代號"]).split(";") if x and x != "nan"]
        cmean = float(np.mean([PR[s][ee] for s in names])) if names else np.nan
        k2 = {"對照名單相同": names == stored, "對照平均R相同": bool(abs(cmean - float(e["對照平均R"])) < 1e-10)}
        res["K2"].append({"sid": sid, "進場日": e["進場日"], "池大小(自算)": len(cand), "對照平均R自算": cmean, "檔案": float(e["對照平均R"]), **k2})
        qend = pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0)
        k3 = {"e晚於上傳日": bool(cal[ee] > ud), "上傳日晚於季底": bool(ud > qend)}
        if kind in (1, 2):
            r2 = PC.hand_exit(pos, o, c, badc, ee, ee + 59, n0, upto=min(ee + 59, n0 - 1))
            k3["截在到期日重算出場相同"] = bool(r2 is not None and r2[0] == eb and abs(r2[1] - Rh) < 1e-12)
        elif kind == 3:
            qq = int(np.searchsorted(pos, eb))
            k3["強制：下一根為壞K"] = bool(qq + 1 < len(pos) and badc[pos[qq + 1]])
        res["K3"].append({"sid": sid, "季": e["季"], **k3})
        bad_ = [x for x, v_ in {**k1, **k2, **k3}.items() if not v_]
        if bad_:
            fails.append({"sid": sid, "季": e["季"], "不符": bad_})
        log(f"{sid} {e['季']} SUE {v:.3f}（切點 {cut:.3f}）進 {e['進場日']} 出 {exd} {PC.NAMES[kind]} R {Rh:+.4%}（檔 {float(e['R']):+.4%}）｜池 {len(cand)} "
            f"對照均 {cmean:+.4%}（檔 {float(e['對照平均R']):+.4%}）｜{'✔' if not bad_ else bad_}")
    for cell in ("上季切點", "同季切點"):
        t2 = pd.read_csv(os.path.join(OUT, "events", f"trades_{cell}.csv.gz"), dtype={"sid": str}, keep_default_na=False, na_values=[""])
        t2["X"] = t2["X"].astype(float)
        for sg in ("段前", "探索", "確認", "主全窗"):
            a_, b_ = J["段"][sg]["期間"].split("～")
            d = t2[(t2["進場日"] >= a_) & (t2["進場日"] <= b_) & np.isfinite(t2["X"])]
            x = d["X"].to_numpy(); mo = d["進場日"].str[:7].to_numpy()
            mu = x.mean(); s_ = pd.Series(x - mu).groupby(mo).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(x)
            ne = min(len(x), len(s_))
            stj = J["段"][sg][cell]
            okk = abs(mu - stj["X̄"]) < 1e-12 and abs(se - stj["se"]) < 1e-12 and ne == stj["n_eff"] and len(x) == stj["n"]
            res["K4"].append({"段": sg, "格": cell, "n": len(x), "X̄": mu, "se": se, "n_eff": ne, "相符": okk})
            log(f"K4 {sg}/{cell}：n={len(x)} X̄={mu:+.4%} se={se:.4%} n_eff={ne}｜{'✔' if okk else '✖'}")
            if not okk:
                fails.append({"K4": f"{sg}/{cell}"})
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    res["K5_策略鎖"] = {"rc": p.returncode, "out": (p.stdout + p.stderr)[-800:]}
    log(f"[K5] strategy_lock --check rc={p.returncode}｜{(p.stdout + p.stderr).strip()[-300:]}")
    if p.returncode != 0:
        fails.append({"K5": "策略鎖不符"})
    res["不符"] = fails
    res["結論"] = "全部相符（K1 20 筆 SUE、進場、出場與報酬、K2 對照重建、K3 不前視、K4 彙總、K5 策略鎖）" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

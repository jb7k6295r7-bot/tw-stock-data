# -*- coding: utf-8 -*-
"""researchPTH 對帳（接近 52 週新高 PTH seq1 事件層正式跑，登錄 sha e5d57b29ddb34ee7）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH_check
輸出 backtest/resultsPTH/check.json、check.log

（⛔ 不呼叫 researchPTH 的出場、抽樣、統計函式；全用日曆 df 逐列手算）
K1 抽 20 筆判定格（跳月）交易（主 12、早年 8；default_rng(20261020)；trades_<世界>_跳月.csv.gz 中 X 可算者）：
   D.load_stock 日曆 df 自算——進場 ＝ 進場日還原開盤；到期日 ＝ 進場月起第 6 個曆月最後交易日（自算完整月）；逐根走有成交日，
   下一根是壞 K 棒 ⇒ 前一根收盤強制；壞 K 棒 ＝ 自算缺口（相鄰成交日日曆間隔 −1 ≥ 5）∪ load_bars 價格斷點／幽靈還原 ∪ crashwork／早年 reduce_v2
   （後兩者為輸入）；到期日無成交 ⇒ 前一根收盤；超出日曆 ⇒ 下市（末根距資料尾 ≥ 5 日）才出場。比 出場日、出場種類、R（|差| ＜ 1e−10）。
K2 對照重建（同 20 筆）：池 ＝ 已提交頻率表事件檔同形成月、跳月狀態「保留」的列 ∩ 自算 R 可算（K1 同式逐檔手算）− 自己；
   依種子 [20261020, 0, j, crc32(sid)]（j ＝ 自算完整月底序）重抽 20 檔 ⇒ 名單 ＝ 檔案「對照代號」、對照平均 R ＝ 檔案。
K3 不前視（同 20 筆）：①df 截在形成月底 t 重算 PTH ＝ 事件檔（頻率表 check 的 hand）；②進場日 ＞ t；③到期出場者：df 截在到期日重算出場 ＝ 全序列；
   壞根強制者：出場那根的下一根成交日確為壞 K 棒。
K4 彙總重算：由 trades 檔自算 跳月、不跳 各段 X̄、進場月分群 SE、n_eff ＝ PTH.json。
K5 區塊 CI 重算：由 trades 檔自寫 6 個月分塊、同種子重抽 ⇒ lo、hi ＝ PTH.json。
K6 策略鎖：python -m backtest.strategy_lock --check 必須相符。
"""
from __future__ import annotations

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
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world（BADPOS 輸入）
from backtest import researchPTH_freq_check as PFC          # noqa: E402  hand（PTH 手算）
from backtest import research11 as R                        # noqa: E402  load_bars（價格斷點旗標輸入）
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsPTH"
FREQ = "backtest/resultsPTH/freq"
LOG = []
_G = {}
NAMES = {1: "到期收盤", 2: "到期日無成交、用前一根收盤", 3: "壞根前一根收盤強制", 4: "末根收盤(之後無成交)", 5: "資料尾未出場"}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def complete_month_ends(cal):
    s = pd.Series(cal, index=cal)
    g = s.groupby(cal.to_period("M")).max()
    last = cal[-1]
    if last < last + pd.offsets.BMonthEnd(0):
        g = g.iloc[:-1]
    return g


def bars(W, sid):
    D.DATA = W["data"]; cal = W["cal"]
    st = D.load_stock(sid, W["mk"].get(sid, "twse"), cal)
    df = st.df
    pos = np.flatnonzero(df["traded"].to_numpy(bool))
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    badc = np.zeros(len(cal), bool)
    gap = np.zeros(len(cal), bool)
    gap[pos[1:]] = (np.diff(pos) - 1) >= 5
    badc |= gap
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is not None:
        idx = B["idx"].astype(np.int64); nb = len(idx)
        lb = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
        badc[idx[lb]] = True
        assert np.array_equal(idx, pos)
        assert not (gap[idx] & ~lb).any(), "自算缺口不在 load_bars 壞根內"
    for p in W["BADPOS"].get(sid, ()):
        k = np.searchsorted(pos, p, "left")
        if k < len(pos):
            badc[pos[k]] = True
    return pos, o, c, badc


def hand_exit(pos, o, c, badc, e, X, n0, upto=None):
    """e ＝ 進場日曆位置、X ＝ 到期日曆位置（＞ n0−1 ＝ 超出日曆）；upto ＝ 只看 ≤ upto 的資料。"""
    p = pos if upto is None else pos[pos <= upto]
    if e not in set(p.tolist()) or not (np.isfinite(o[e]) and o[e] > 0):
        return None
    k = int(np.searchsorted(p, e)); end = min(X, n0 - 1)
    while k + 1 < len(p) and p[k + 1] <= end:
        if badc[p[k + 1]]:
            return p[k], c[p[k]] / o[e] - 1, 3
        k += 1
    delisted = (n0 - 1 - pos[-1]) >= 5 and k == len(pos) - 1
    if X <= n0 - 1:
        if p[k] == X:
            return p[k], c[p[k]] / o[e] - 1, 1
        if delisted:
            return p[k], c[p[k]] / o[e] - 1, 4
        return p[k], c[p[k]] / o[e] - 1, 2
    if delisted:
        return p[k], c[p[k]] / o[e] - 1, 4
    return -1, np.nan, 5


def pool_job(a):
    wn, sid, jobs = a          # jobs ＝ [(e, X)]
    W = _G[wn]
    try:
        pos, o, c, badc = bars(W, sid)
    except Exception:
        return sid, {}
    out = {}
    for e, X in jobs:
        r = hand_exit(pos, o, c, badc, e, X, W["n0"])
        if r is not None and np.isfinite(r[1]):
            out[(e, X)] = r[1]
    return sid, out


def main():
    rng = np.random.default_rng(20261020)
    J = json.load(open(os.path.join(OUT, "PTH.json"), encoding="utf-8"))
    res = {"K1": [], "K2": [], "K3": [], "K4": [], "K5": []}; fails = []
    for wn, m in (("主", 12), ("早年", 8)):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]; _G[wn] = W
        posd = {str(d.date()): j for j, d in enumerate(cal)}
        mes = complete_month_ends(cal)
        me_pos = [int(cal.searchsorted(x)) for x in mes.values]
        jof = {str(cal[p].date()): j for j, p in enumerate(me_pos)}
        mp = {(cal[p].year, cal[p].month): p for p in me_pos}
        tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_跳月.csv.gz"), dtype={"sid": str, "對照代號": str}, keep_default_na=False, na_values=[""])
        trx = tr[np.isfinite(tr["X"].astype(float))].reset_index(drop=True)
        pick = trx.iloc[np.sort(rng.choice(len(trx), m, replace=False))].reset_index(drop=True)
        fev = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype={"sid": str})
        st = pd.read_csv(os.path.join(W["data"], "meta", "stocks.csv"), dtype=str)
        mesP = PFC.my_month_ends(cal)

        def xpos(e, H=6):
            y, mm = cal[e].year, cal[e].month
            k = y * 12 + (mm - 1) + (H - 1)
            return mp.get((k // 12, k % 12 + 1), n0 + 1)
        jobs = {}
        for _, e in pick.iterrows():
            ee = posd[e["進場日"]]; X = xpos(ee)
            g = fev[(fev["形成月底"] == e["形成月底"]) & (fev["跳月_st"] == "保留")]
            for s in g["sid"]:
                jobs.setdefault(s, set()).add((ee, X))
        with Pool(3) as pool:
            PR = dict(pool.imap_unordered(pool_job, [(wn, s, sorted(v)) for s, v in jobs.items()], chunksize=8))
        log(f"[{wn}] 對照池手算 {len(jobs)} 檔完成")
        for _, e in pick.iterrows():
            sid = e["sid"]; ee = posd[e["進場日"]]; X = xpos(ee)
            pos, o, c, badc = bars(W, sid)
            eb, Rh, kind = hand_exit(pos, o, c, badc, ee, X, n0)
            exd = str(cal[eb].date()) if eb >= 0 else ""
            k1 = {"出場日": exd == e["出場日"], "出場種類": NAMES[kind] == e["出場種類"], "R": bool(abs(Rh - float(e["R"])) < 1e-10),
                  "持有天數": (eb - ee) == int(e["持有天數"])}
            res["K1"].append({"世界": wn, "sid": sid, "形成月底": e["形成月底"], "進場日": e["進場日"], "進場價(還原開)": float(o[ee]), "出場日": exd,
                              "種類": NAMES[kind], "R手算": float(Rh), "R檔案": float(e["R"]), **k1})
            # K2
            j = jof[e["形成月底"]]
            g = fev[(fev["形成月底"] == e["形成月底"]) & (fev["跳月_st"] == "保留")]
            cand = sorted([s for s in g["sid"] if s != sid and (ee, X) in PR.get(s, {})], key=lambda s: W["ix"][s])
            ci = np.array([W["ix"][s] for s in cand], np.int64)
            gg = np.random.default_rng([20261020, 0, j, zlib.crc32(sid.encode("utf-8"))])
            dr = np.sort(gg.choice(ci, size=min(20, len(ci)), replace=False)) if len(ci) else ci
            names = [W["sids"][x] for x in dr]
            stored = [x for x in str(e["對照代號"]).split(";") if x and x != "nan"]
            cmean = float(np.mean([PR[s][(ee, X)] for s in names])) if names else np.nan
            k2 = {"對照名單相同": names == stored, "對照平均R相同": bool(abs(cmean - float(e["對照平均R"])) < 1e-10)}
            res["K2"].append({"世界": wn, "sid": sid, "形成月底": e["形成月底"], "池大小(自算)": len(cand), "對照平均R自算": cmean,
                              "檔案": float(e["對照平均R"]), **k2})
            # K3
            t = pd.Timestamp(e["形成月底"])
            h = PFC.hand(sid, W["mk"].get(sid, "twse"), W["data"], cal, t, mesP)
            fr = fev[(fev["sid"] == sid) & (fev["形成月底"] == e["形成月底"])].iloc[0]
            k3 = {"截在t的PTH＝事件檔": bool(abs(h["pth_trunc"] - fr["PTH"]) < 1e-9), "進場日晚於t": bool(pd.Timestamp(e["進場日"]) > t)}
            if eb >= 0 and kind in (1, 2):
                r2 = hand_exit(pos, o, c, badc, ee, X, n0, upto=min(X, n0 - 1))
                k3["截在到期日重算出場相同"] = bool(r2 is not None and r2[0] == eb and abs(r2[1] - Rh) < 1e-12)
            elif kind == 3:
                q = int(np.searchsorted(pos, eb))
                k3["強制：下一根為壞K"] = bool(q + 1 < len(pos) and badc[pos[q + 1]])
            res["K3"].append({"世界": wn, "sid": sid, "形成月底": e["形成月底"], **k3})
            bad_ = [x for x, v in {**k1, **k2, **k3}.items() if not v]
            if bad_:
                fails.append({"世界": wn, "sid": sid, "形成月底": e["形成月底"], "不符": bad_})
            log(f"{wn} {sid} t={e['形成月底']} 進 {e['進場日']} 出 {exd} {NAMES[kind]} R {Rh:+.4%}（檔 {float(e['R']):+.4%}）｜池 {len(cand)} 對照均 {cmean:+.4%}"
                f"（檔 {float(e['對照平均R']):+.4%}）｜{'✔' if not bad_ else bad_}")
    # K4、K5
    for wn, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for cell, tag in (("跳月", 0), ("不跳", 1)):
            tr = pd.read_csv(os.path.join(OUT, "events", f"trades_{wn}_{cell}.csv.gz"), dtype={"sid": str}, keep_default_na=False, na_values=[""])
            tr["X"] = tr["X"].astype(float)
            for sg in sgs:
                a_, b_ = J["世界"][wn]["段"][sg].split("～")
                d = tr[(tr["進場日"] >= a_) & (tr["進場日"] <= b_) & np.isfinite(tr["X"])]
                x = d["X"].to_numpy(); mo = d["進場日"].str[:7].to_numpy()
                mu = x.mean(); s_ = pd.Series(x - mu).groupby(mo).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(x)
                ne = min(len(x), len(s_))
                stj = J["世界"][wn]["格"][sg][cell]
                ok = abs(mu - stj["X̄"]) < 1e-12 and abs(se - stj["se"]) < 1e-12 and ne == stj["n_eff"] and len(x) == stj["n"]
                res["K4"].append({"世界": wn, "段": sg, "格": cell, "n": len(x), "X̄": mu, "se": se, "n_eff": ne, "相符": ok})
                log(f"K4 {wn}/{sg}/{cell}：n={len(x)} X̄={mu:+.4%} se={se:.4%} n_eff={ne}｜{'✔' if ok else '✖'}")
                if not ok:
                    fails.append({"K4": f"{wn}/{sg}/{cell}"})
                # K5
                mon = (d["進場日"].str[:4].astype(int) * 12 + d["進場日"].str[5:7].astype(int)).to_numpy()
                blk = (mon - mon.min()) // 6; nbk = int(blk.max()) + 1
                Sx = np.zeros(nbk); Nx = np.zeros(nbk)
                for b, v in zip(blk, x):
                    Sx[b] += v; Nx[b] += 1
                segnum = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}[sg]
                g = np.random.default_rng([20261022, segnum, tag])
                pk = g.integers(0, nbk, size=(10_000, nbk))
                mm = Sx[pk].sum(1) / Nx[pk].sum(1)
                lo, hi = float(np.percentile(mm, 2.5)), float(np.percentile(mm, 97.5))
                bj = stj["區塊CI"]
                ok5 = abs(lo - bj["lo"]) < 1e-12 and abs(hi - bj["hi"]) < 1e-12 and nbk == bj["塊數"]
                res["K5"].append({"世界": wn, "段": sg, "格": cell, "塊數": nbk, "lo": lo, "hi": hi, "相符": ok5})
                log(f"K5 {wn}/{sg}/{cell}：塊 {nbk} 區塊 CI {lo:+.4%}～{hi:+.4%}｜{'✔' if ok5 else '✖'}")
                if not ok5:
                    fails.append({"K5": f"{wn}/{sg}/{cell}"})
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    res["K6_策略鎖"] = {"rc": p.returncode, "out": (p.stdout + p.stderr)[-800:]}
    log(f"[K6] strategy_lock --check rc={p.returncode}｜{(p.stdout + p.stderr).strip()[-300:]}")
    if p.returncode != 0:
        fails.append({"K6": "策略鎖不符"})
    res["不符"] = fails
    res["結論"] = "全部相符（K1 20 筆出場與報酬、K2 對照重建、K3 不前視、K4 彙總、K5 區塊 CI、K6 策略鎖）" if not fails else f"{len(fails)} 項不符"
    log(res["結論"])
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()

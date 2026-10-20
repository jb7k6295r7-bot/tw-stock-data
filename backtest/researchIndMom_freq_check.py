# -*- coding: utf-8 -*-
"""researchIndMom_freq 對帳（獨立寫法；⛔ 不讀、不算任何進場後報酬）——回測線計算子代理，2026-10-21。
 C1 登錄 sha 獨立重算（信箱根目錄＋_封存-*；去 pw1 行 sha256 前 16 碼）
 C2 抽樣手算：每世界抽 2 個形成月（default_rng(20261021)），逐檔重讀 research11.load_bars、自建 500 張閘、壞根、6 個月報酬、
    自讀原始 csv（主）／daily_all（早年）的市值、自解析 industry_pit.csv（沒有該檔才借 PRE.PIT fallback，計數）⇒
    排序母體檔數、各產業成員數、市值加權／等權前 3、最弱 3 與 monthly.csv、industry_months.csv.gz 逐項相同
 C3 不前視：對抽樣月把面板 t 之後的收盤、壞根、閘、市值全部抹掉，再跑 researchIndMom_freq.month_table／rank_inds ⇒ 入選與成員完全相同
 C4 PTH／12−1 重疊：抽樣月由 resultsPTH/freq/events 獨立重算重疊檔數 ⇒ 與 monthly.csv 相同
 C5 策略鎖：python -m backtest.strategy_lock --check 相符（25 支）
輸出 backtest/resultsIndMom/freq/check.json
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import patterns as P                          # noqa: E402

OUT = IM.OUT
_W = {}


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def reg_ok(sha):
    fs = []
    for d in [IM.MAILBOX] + sorted(glob.glob(os.path.join(IM.MAILBOX, "_封存-*"))):
        fs += [f for f in glob.glob(os.path.join(d, "*.md")) if f"sha{sha}" in os.path.basename(f)]
    return bool(fs) and all(sha_of(f) == sha for f in fs), [os.path.basename(f) for f in fs]


def lock_ok():
    p = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    out = (p.stdout + p.stderr).strip().splitlines()
    return ("相符" in "".join(out[-3:])) and p.returncode == 0, out[-3:]


class MyPIT:
    def __init__(self, DATA):
        p = pd.read_csv(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), dtype=str).fillna("")
        self.seg = defaultdict(list)
        for s, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
            self.seg[s].append((a or "0000-00-00", b or "9999-99-99", ind))
        for s in self.seg:
            self.seg[s].sort()

    def at(self, s, d):
        if s not in self.seg:
            return None
        sg = self.seg[s]
        for a, b, ind in sg:
            if a <= d <= b:
                return ind
        if d > sg[-1][1]:
            return sg[-1][2]
        if d < sg[0][0]:
            return sg[0][2]
        return [z for z in sg if z[1] < d][-1][2]


def _job(a):
    wn, sid, t, apos = a
    W = _W[wn]; cal = W["cal"]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = B["idx"].astype(np.int64); c = np.asarray(B["c"], float); nb = len(idx)
    bad = list(np.asarray(B["next_bad"][:nb] == np.arange(nb), bool))
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    g = bool(np.asarray(P.Frame(B["df"], set()).gate, bool)[t]) and bool(W["PV"][W["ix"][sid]][t])
    kt = [k for k in range(nb) if idx[k] == t]
    if not g or not kt:
        return sid, ("閘外", None)
    kt = kt[0]
    ka = [k for k in range(nb) if idx[k] <= apos]
    if not ka:
        return sid, ("未滿", None)
    ka = ka[-1]
    if any(bad[k] for k in range(ka + 1, kt + 1)):
        return sid, ("壞根", None)
    r = c[kt] / c[ka] - 1.0
    mc = np.nan
    if wn == "主":
        raw = pd.read_csv(os.path.join(W["data"], "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close", "shares"])
        raw = raw[pd.to_datetime(raw["date"]) <= cal[apos]]
        v = pd.to_numeric(raw["close"], errors="coerce") * pd.to_numeric(raw["shares"], errors="coerce")
        v = v[v > 0]
        mc = float(v.iloc[-1]) if len(v) else np.nan
    return sid, ("ok", (r, mc))


def main():
    CK = {}
    for nm_, sha in (("產業動能", IM.REG_SHA),):
        CK[f"C1_登錄sha_{nm_}"] = reg_ok(sha)
    sha, DATA = IM.ensure_main()
    mp = MyPIT(DATA); PIT = IM.load_pit(DATA)
    mon = pd.read_csv(os.path.join(OUT, "monthly.csv"), dtype=str)
    with gzip.open(os.path.join(OUT, "industry_months.csv.gz"), "rt", encoding="utf-8") as fh:
        INDM = pd.read_csv(fh, dtype=str)
    rng = np.random.default_rng(20261021)
    C2 = []; C3 = []; C4 = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); _W[wn] = W; cal = W["cal"]
        ME, MK = PF.month_ends(cal)
        Z = IM.panel_aux(IM.build_panel(wn, 2))
        js = sorted(rng.choice(np.arange(7, len(ME)), 2, replace=False).tolist())
        da = None
        if wn == "早年":
            da0 = pd.read_pickle(IM.EOTC_DAILY)[["date", "stock_id", "close", "shares"]]
            da0 = da0[da0["stock_id"].isin(set(Z["sids"]))].copy()
            da0["date"] = pd.to_datetime(da0["date"])
            da = {s: g for s, g in da0.groupby("stock_id")}
            del da0
        for j in js:
            t = int(ME[j]); apos = int(ME[j - 6]); ts = str(cal[t].date())
            with Pool(2) as pool:
                res = dict(pool.map(_job, [(wn, s, t, apos) for s in Z["sids"]], chunksize=16))
            mem = defaultdict(list); n_fb = 0
            for s, v in res.items():
                if v is None or v[0] != "ok":
                    continue
                r, mc = v[1]
                if wn == "早年":
                    q = da.get(s, pd.DataFrame(columns=["date", "close", "shares"]))
                    q = q[q["date"] <= cal[apos]]
                    vv = pd.to_numeric(q["close"], errors="coerce") * pd.to_numeric(q["shares"], errors="coerce")
                    q = q.assign(v=vv.values)
                    q = q[q["v"] > 0].sort_values("date")
                    mc = float(q["v"].iloc[-1]) if len(q) else np.nan
                if not (np.isfinite(mc) and mc > 0):
                    continue
                ind = mp.at(s, ts)
                if ind is None:
                    ind = PIT.at(s, cal[t])[0]; n_fb += 1
                if ind is None or ind in IM.EXCL_IND:
                    continue
                mem[ind].append((r, mc))
            rk = {k: v for k, v in mem.items() if len(v) >= 5}
            vw = sorted(((k, sum(r * w for r, w in v) / sum(w for _, w in v)) for k, v in rk.items()), key=lambda z: (-z[1], z[0]))
            ew = sorted(((k, float(np.mean([r for r, _ in v]))) for k, v in rk.items()), key=lambda z: (-z[1], z[0]))
            row = mon[(mon["世界"] == wn) & (mon["形成月底"] == ts)].iloc[0]
            im = INDM[(INDM["世界"] == wn) & (INDM["形成月底"] == ts)]
            memcnt_main = dict(zip(im["產業"], im["成員數"].astype(int)))
            memcnt_mine = {k: len(v) for k, v in rk.items()}
            ok = (sum(len(v) for v in mem.values()) == int(float(row["排序母體檔數"])) and "｜".join(k for k, _ in vw[:3]) == row["市值加權前3"]
                  and "｜".join(k for k, _ in ew[:3]) == row["等權前3"] and "｜".join(k for k, _ in vw[-3:][::-1]) == row["最弱3(描述)"]
                  and memcnt_main == memcnt_mine)
            C2.append({"世界": wn, "形成月底": ts, "相同": bool(ok), "母體(手算/主)": [sum(len(v) for v in mem.values()), int(float(row["排序母體檔數"]))],
                       "前3(手算)": [k for k, _ in vw[:3]], "前3(主)": row["市值加權前3"], "等權前3(手算)": [k for k, _ in ew[:3]],
                       "fallback產業別檔數": n_fb, "產業成員數不同": {k: (memcnt_mine.get(k), memcnt_main.get(k)) for k in set(memcnt_main) | set(memcnt_mine)
                                                          if memcnt_main.get(k) != memcnt_mine.get(k)}})
            # C3 不前視：抹掉 t 之後
            Zc = dict(Z)
            Zc["C"] = Z["C"].copy(); Zc["C"][:, t + 1:] = np.nan
            Zc["BAD"] = Z["BAD"].copy(); Zc["BAD"][:, t + 1:] = False
            Zc["G"] = Z["G"].copy(); Zc["G"][:, t + 1:] = False
            Zc["MC"] = Z["MC"].copy(); Zc["MC"][:, t + 1:] = np.nan
            Zc.pop("VP", None); Zc.pop("CB", None); Zc = IM.panel_aux(Zc)
            same = True
            for L in (6, 1):
                m1, _, u1 = IM.month_table(Z, PIT, ME, j, L); m2, _, u2 = IM.month_table(Zc, PIT, ME, j, L)
                same &= (IM.rank_inds(m1) == IM.rank_inds(m2)) and (sorted(u1) == sorted(u2))
            C3.append({"世界": wn, "形成月底": ts, "抹掉t之後入選相同": bool(same)})
            # C4 PTH 重疊
            ev = pd.read_csv(IM.PTH_EV.format(wn), dtype={"sid": str})
            ev = ev[ev["形成月底"] == ts]
            if len(ev) and "重疊_PTH前30%_檔數" in row and isinstance(row["重疊_PTH前30%_檔數"], str):
                top3 = row["市值加權前3"].split("｜")
                m6, _, _ = IM.month_table(Z, PIT, ME, j, 6)
                ids = {Z["sids"][i] for k in top3 for (i, _, _) in m6[k]}
                pth = set(ev.loc[ev["入選"].astype(str) == "True", "sid"])
                mm = ev[ev["mom12_1"].notna()]; kk = math.ceil(0.3 * len(mm)); cut = sorted(mm["mom12_1"], reverse=True)[kk - 1]
                mom = set(mm.loc[mm["mom12_1"] >= cut, "sid"])
                C4.append({"世界": wn, "形成月底": ts, "PTH(手算/主)": [len(ids & pth), int(float(row["重疊_PTH前30%_檔數"]))],
                           "12-1(手算/主)": [len(ids & mom), int(float(row["重疊_12-1前30%_檔數"]))],
                           "相同": len(ids & pth) == int(float(row["重疊_PTH前30%_檔數"])) and len(ids & mom) == int(float(row["重疊_12-1前30%_檔數"]))})
            print(C2[-1], C3[-1], C4[-1] if C4 else None, flush=True)
    CK["C2_抽樣手算"] = C2; CK["C3_不前視"] = C3; CK["C4_重疊"] = C4
    CK["C5_策略鎖"] = lock_ok()
    CK["全過"] = bool(CK["C1_登錄sha_產業動能"][0] and all(x["相同"] for x in C2) and all(x["抹掉t之後入選相同"] for x in C3)
                    and all(x["相同"] for x in C4) and CK["C5_策略鎖"][0])
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("全過" if CK["全過"] else "⛔ 有不符", json.dumps({k: v for k, v in CK.items() if k.startswith("C1") or k.startswith("C5")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

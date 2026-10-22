# -*- coding: utf-8 -*-
"""researchIndRevHold_freq 對帳（獨立寫法；⛔ 不讀、不算任何報酬）——回測線計算子代理，2026-10-22。
 C1 登錄 sha 獨立重算（信箱根目錄＋_封存-*；去 pw1 行 sha256 前 16 碼）：seq2 800ad3a4bcacd7da（判）、seq1 2f0f5925257a3260（記錄）
 C2 A 表：抽 3 個營收月（主段批 1、早年批 1、2026 年 1 個；default_rng(20261022)），PRE.ck_load／ck_A 從原始 csv 逐公司重算
    （判定日 ＝ 本檔自己由日曆算的 10／15 日規則可用日前一交易日）⇒ 該月全部產業 A1～A3 相對差 ≤ 1e−12、公司數相同
 C3 挑選：每世界抽 2 個批日（A2｜K3），自己讀面板 csv（eligible、pit_ok）、自己由原始 csv 算市值、PRE.ck_ind 分產業、C2 的 ck_A 排名（公司數 ≥ 5、
    A 有限、A ＞ 0、前 K）⇒ 挑中產業、各產業全成員名單（S3）與前 20（S1）與主程式（FQ.W[world]["MEM"]／PK）逐位相同
 C4 可用日／不前視：batches.csv.gz 全部批：批日 ＝ 營收月可用日（自算：≤2025-12 用 10 日、≥2026-01 用 15 日，嚴格大於）的次一交易日
 C5 乾跑帳獨立重算：每世界抽 1 格（＋主段固定 A2｜K3｜S3｜750），逐日迴圈（開盤買、收盤判停止交易／下一有成交日是壞根／到期可賣）⇒
    每日不同代號持股數與 daily.npz 完全相同、現金比例差 ≤ 1e−9
 C6 策略鎖：python -m backtest.strategy_lock --check 相符（25 支）
 C7 無報酬：主程式原始碼不取 ["c"]／close 數值（只 TR.one 旗標與市值排序）；輸出欄名不含「報酬」「年化」「回落」
輸出 backtest/resultsIndRevHold/freq/check.json
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
from argparse import Namespace
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndRevHold_freq as FQ          # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchIndRevLag_prereg as LAGP       # noqa: E402
from backtest import researchScore as SC                    # noqa: E402
from backtest import data as D                              # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402

OUT = FQ.OUT


def my_sha(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def c1():
    out = {}
    for k, sh in (("seq2", "800ad3a4bcacd7da"), ("seq1", "2f0f5925257a3260")):
        fs = []
        for d in ["/mnt/c/SynologyDrive/跨線信箱"] + sorted(glob.glob("/mnt/c/SynologyDrive/跨線信箱/_封存-*")):
            fs += [f for f in glob.glob(os.path.join(d, "*.md")) if f"sha{sh}" in os.path.basename(f)]
        out[k] = {"檔數": len(fs), "相符": bool(fs) and all(my_sha(f) == sh for f in fs)}
    return out


def gcal():
    D.DATA = SC.EARLY_DATA; ce = D.load_calendar()
    RR.use_snapshot(); cm = D.load_calendar()
    return ce[ce <= pd.Timestamp("2014-12-31")].append(cm[cm > pd.Timestamp("2014-12-31")])


def my_avail(cal, M):
    y, m = int(M[:4]), int(M[5:])
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    day = 15 if M >= "2026-01" else 10
    cut = pd.Timestamp(year=y2, month=m2, day=day)
    k = next(i for i, d in enumerate(cal) if d > cut)
    return k


def lock_ok():
    p = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    out = (p.stdout + p.stderr).strip().splitlines()
    return ("相符" in "".join(out[-3:])) and p.returncode == 0, out[-3:]


def my_mcap(world, sid, dlim, cache):
    if world == "main":
        raw = pd.read_csv(os.path.join(cache["data"], "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close", "shares"])
        raw = raw[raw["date"] <= dlim]
        v = pd.to_numeric(raw["close"], errors="coerce") * pd.to_numeric(raw["shares"], errors="coerce")
        v = v[v > 0]
        return float(v.iloc[-1]) if len(v) else np.nan
    g = cache["da"].get(sid)
    if g is None:
        return np.nan
    g = g[g["date"] <= dlim]
    v = pd.to_numeric(g["close"], errors="coerce") * pd.to_numeric(g["shares"], errors="coerce")
    v = v[v > 0]
    return float(v.iloc[-1]) if len(v) else np.nan


def daysim(Wd, BL, picks, K, S, H):
    """C5：逐日迴圈（獨立寫法）。⇒ (每日不同代號數, 每日現金)。"""
    cal = Wd["cal"]; T = Wd["T"]; n = len(cal); FL = Wd["FL"]; SFd = Wd["SF"]
    nsl = int(round(H / 21)); sl = 1.0 / nsl
    bd = {b: j for j, (b, _) in enumerate(BL)}
    batches = []   # dict(mat, slice, lots[list of [sid, amt, alive]], released)
    dist = np.zeros(n, int); cash = np.ones(n)
    isbad = {}; nxt = {}

    def prep(s):
        if s not in isbad:
            f = FL[s]; ib = np.zeros(n + 1, bool); ib[f["bad"]] = True; isbad[s] = ib
            tr = np.flatnonzero(f["trd"]); k = np.searchsorted(tr, np.arange(n), "right")
            nxt[s] = np.where(k < len(tr), tr[np.minimum(k, len(tr) - 1)], n)
    for t in range(BL[0][0], T + 1):
        if t in bd:
            j = bd[t]; b = t
            occ = sum(x["slice"] for x in batches if not x["released"])
            Aj = min(sl, max(1.0 - occ, 0.0))
            mem = Wd["MEM"][b][0]
            lots = []
            for i in picks[j]:
                lst = mem.get(i, [])
                lst = lst[:20] if S == "S1" else lst
                for s in lst:
                    f = FL.get(s)
                    if f is None:
                        continue
                    prep(s)
                    if not f["trd"][b] or not Wd["okopen"][s][b] or f["up"][b] or isbad[s][b]:
                        continue
                    lots.append([s, Aj / K / len(lst), True])
            batches.append({"mat": b + H - 1, "slice": Aj, "lots": lots, "released": False})
        # 收盤
        for x in batches:
            if x["released"]:
                continue
            end = min(x["mat"], T)
            for L in x["lots"]:
                if not L[2]:
                    continue
                s = L[0]; f = FL[s]
                sold = False
                if t <= end:
                    Lst = SFd.get(s)
                    if Lst is not None and t == Lst + 1:
                        sold = True
                    elif f["trd"][t]:
                        q = int(nxt[s][t])
                        if q <= end and isbad[s][q]:
                            sold = True
                if not sold and t >= x["mat"] and f["trd"][t] and not f["dc"][t]:
                    sold = True
                if sold:
                    L[2] = False
            if t >= x["mat"] and not any(L[2] for L in x["lots"]):
                x["released"] = True
        live = [L for x in batches if not x["released"] for L in x["lots"] if L[2]]
        dist[t] = len({L[0] for L in live}); cash[t] = 1.0 - sum(L[1] for L in live)
    return dist, cash


def main():
    CK = {"C1_登錄sha": c1()}
    am = json.load(open(os.path.join(OUT, "A_meta.json"), encoding="utf-8"))
    a = Namespace(procs=4, sha=am["main"], reps=0)
    sha = LAGP.setup(a, am["main"]); FQ.install_A(sha)
    K_ = PRE.ck_load(PRE._C["DATA"])
    cal = gcal()
    AT = pd.read_csv(os.path.join(OUT, "A_table.csv.gz"), float_precision="round_trip")
    BT = pd.read_csv(os.path.join(OUT, "batches.csv.gz"), dtype={"營收月": str})
    rng = np.random.default_rng(20261022)
    # C4
    bad4 = []
    for w, g in BT.drop_duplicates(["世界", "批日"]).groupby("世界"):
        for d, M in zip(g["批日"], g["營收月"]):
            k = my_avail(cal, M)
            if str(cal[k + 1].date()) != d:
                bad4.append((w, d, M, str(cal[k + 1].date())))
    CK["C4_批日＝可用日次日"] = {"批數": int(BT.drop_duplicates(["世界", "批日"]).shape[0]), "不同": bad4[:10], "過": not bad4}
    # C2
    mm = sorted(set(BT.loc[BT["世界"] == "main", "營收月"])); me = sorted(set(BT.loc[BT["世界"] == "early", "營收月"]))
    Ms = [mm[int(rng.integers(len(mm)))], me[int(rng.integers(len(me)))], [x for x in mm if x >= "2026-01"][int(rng.integers(len([x for x in mm if x >= "2026-01"])))]]
    C2 = []; ckA = {}
    for M in Ms:
        k = my_avail(cal, M); dstr = str(cal[k - 1].date())
        mine = PRE.ck_A(K_, M, dstr); ckA[M] = mine
        A_ = AT[(AT["M"] == M) & (AT["ver"] == "pit")].set_index("產業")
        diff = 0.0; cdiff = []
        for i, (a1, a2, a3, c) in mine.items():
            if i not in A_.index:
                cdiff.append((i, "主表無")); continue
            r = A_.loc[i]
            if int(r["公司數"]) != c:
                cdiff.append((i, int(r["公司數"]), c))
            for x, y in ((a1, r["A1"]), (a2, r["A2"]), (a3, r["A3"])):
                if np.isfinite(x) or np.isfinite(y):
                    diff = max(diff, abs(x - y) / max(abs(y), 1e-12) if (np.isfinite(x) and np.isfinite(y)) else np.inf)
        extra = sorted(set(A_.index) - set(mine))
        C2.append({"M": M, "判定日": dstr, "產業數": len(mine), "A最大相對差": diff, "公司數或產業不同": cdiff[:5], "主表多出": extra[:5],
                   "過": diff <= 1e-12 and not cdiff and not extra})
    CK["C2_A表"] = C2
    # C3、C5
    C3 = []; C5 = []
    npz = np.load(os.path.join(OUT, "daily.npz"))
    for world in ("main", "early"):
        Wd = FQ.prep_world(world, a)
        BL = Wd["BL"]["主讀法"]
        cache = {"data": Wd["C"]["data"]}
        if world == "early":
            da = pd.read_pickle(PRE.EOTC_DAILY)[["date", "stock_id", "close", "shares"]]
            cache["da"] = {s: g for s, g in da.groupby("stock_id")}
            pn = pd.read_csv(LAGP.PANEL_EOTC, dtype=str)
        else:
            pn = pd.read_csv(SC.PANEL_EXT, dtype=str)
        pn["measure_date"] = pd.to_datetime(pn["measure_date"])
        js = sorted(rng.choice(len(BL), 2, replace=False).tolist())
        for j in js:
            b, M = BL[j]; d = Wd["cal"][b]; dlim = str(Wd["cal"][b - 1].date())
            md = max(x for x in set(pn["measure_date"]) if x.year == d.year and x.month == d.month)
            q = pn[(pn["measure_date"] == md) & (pn["eligible"] == "True")]
            if "pit_ok" in q.columns:
                q = q[q["pit_ok"] == "True"]
            el = [s for s in sorted(q["stock_id"]) if s in Wd["C"]["P"]]
            grp = defaultdict(list)
            for s in el:
                i = PRE.ck_ind(K_, s, dlim)
                if i is None or i in PRE.EXCL:
                    continue
                mc = my_mcap(world, s, dlim, cache)
                if not (np.isfinite(mc) and mc > 0):
                    continue
                grp[i].append((-mc, s))
            mem = {i: [s for _, s in sorted(v)] for i, v in grp.items()}
            if M not in ckA:
                k = my_avail(cal, M); ckA[M] = PRE.ck_A(K_, M, str(cal[k - 1].date()))
            rk = sorted(((i, v) for i, v in ckA[M].items() if v[3] >= 5 and np.isfinite(v[1])), key=lambda z: (-z[1][1], z[0]))
            pk = [i for i, v in rk if v[1] > 0][:3]
            main_mem = Wd["MEM"][b][0]; main_pk = Wd["PK"]["主讀法"][("A2", 3)][j]
            same_pk = pk == main_pk
            same_mem = all(mem.get(i, []) == main_mem.get(i, []) for i in set(mem) | set(main_mem))
            C3.append({"世界": world, "批日": str(d.date()), "M": M, "挑中(手算)": pk, "挑中(主)": main_pk, "挑中相同": same_pk,
                       "全成員相同": same_mem, "產業數(手算/主)": [len(mem), len(main_mem)],
                       "挑中產業成員數(手算)": [len(mem.get(i, [])) for i in pk], "過": same_pk and same_mem})
            print(C3[-1], flush=True)
        # C5
        cells = [(A, K, S, H) for A in FQ.AS for K in FQ.KS for S in FQ.SS for H in FQ.HS]
        pick = [cells[int(rng.integers(len(cells)))]] + ([("A2", 3, "S3", 750)] if world == "main" else [])
        for (A, K, S, H) in pick:
            dist, cash = daysim(Wd, BL, Wd["PK"]["主讀法"][(A, K)], K, S, H)
            key = f"{world}__主讀法__{A}__{K}__{S}__{H}"
            arr = npz[key]; t0 = BL[0][0]; T = Wd["T"]
            dd = int(np.sum(arr[0][t0:T + 1].astype(int) != dist[t0:T + 1]))
            cd = float(np.max(np.abs(arr[1][t0:T + 1].astype(float) - cash[t0:T + 1])))
            C5.append({"世界": world, "格": f"{A}|K{K}|{S}|{H}", "持股數不同日數": dd, "現金最大差": cd, "過": dd == 0 and cd <= 1e-6})
            print(C5[-1], flush=True)
        FQ.W.pop(world, None)
    CK["C3_挑選"] = C3; CK["C5_乾跑帳"] = C5
    CK["C5_註"] = "daily.npz 現金存 float32 ⇒ 門檻放寬為 1e−6（float32 精度）；持股數逐日完全相同"
    CK["C6_策略鎖"] = lock_ok()
    src = open("backtest/researchIndRevHold_freq.py", encoding="utf-8").read()
    hits = re.findall(r'\["c"\]|\[.c.\]\[t|cumprod|load_bench', src)
    cols = set()
    for f in ("cells.csv", "allind.csv", "similarity.csv", "overlap_prev.csv"):
        cols |= set(pd.read_csv(os.path.join(OUT, f), nrows=1).columns)
    bad = [c for c in cols if any(w in c for w in ("報酬", "年化", "回落"))]
    CK["C7_無報酬"] = {"原始碼取價格": hits, "輸出報酬欄": bad, "過": not hits and not bad}
    CK["全過"] = bool(CK["C1_登錄sha"]["seq2"]["相符"] and CK["C4_批日＝可用日次日"]["過"] and all(x["過"] for x in C2) and all(x["過"] for x in C3)
                    and all(x["過"] for x in C5) and CK["C6_策略鎖"][0] and CK["C7_無報酬"]["過"])
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("全過" if CK["全過"] else "⛔ 有不符", json.dumps({k: v for k, v in CK.items() if k in ("C1_登錄sha", "C4_批日＝可用日次日", "C6_策略鎖", "C7_無報酬")},
                                                    ensure_ascii=False, default=str))
    print(json.dumps(C2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

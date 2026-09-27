# -*- coding: utf-8 -*-
"""營量 v1 重測（裁定 seq257 §三 順 1；稽核 seq3 §七之二）。回測線，2026-09-27。⭐ 停止交易強制出場：開。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLretest.py b1|report [--procs 2] [--reps 200]

營量 v1 ＝ #13 ＝ PREREGP1 AND N20 d=∞ relvol H60、無大盤閘（rerun17._sim_engine P1 路徑；原件 resultsN17/seeds_main.csv main #13）
  引擎：research11.simulate_mtm(sig, "H60", 20, default_rng(7000＋r), closes, opens, ncal, return_equity=True, log=[], d_max=None, pick="relvol", queue_days=0)
  ⭐ 本件一律多帶 stop_force（research11.stop_force_days(valid_from_data(母體), 主窗尾)）⇒ 停止交易強制出場：開
第一批（先交）
  ① 主窗開 stop_force 200 顆，並列原件（閘：關的時候 200 顆逐位元 ＝ seeds_main #13）
  ② 主窗假訊號 200 次：每一筆真訊號（窗內）換成「同月隨機交易日 × 當天有 K 棒的隨機股」（母體 load_universe∩gate3、load_bars 有資料），
     其 relvol（＝ researchp1.feat_worker 同式：成交額 ÷ 前 60 根中位數）與 H60 出場（research11.fixed_exit、壞根 next_bad 同 hsweep.exits）照原件產生器算；
     每次一顆引擎種子（7000＋i）、抽樣種子 default_rng([20260927, i]) ⇒ 報 p ＝ 假訊號比值 ≥ 1.124 的比例
     「219 取最好」百分位（⚠ 估計，沒跑 219 格的假訊號）：以 #13 的假訊號比值分佈 F 當每格的虛無分佈、K 格視為獨立 ⇒ P(最好 ≤ 1.124) ＝ F(1.124)^K；
     K＝219（獨立上界，格間高度相關 ⇒ 實際有效格數較少，這個百分位偏嚴）、K＝17（候選 17 格）並列
  ③ 起點挪 5／10／15／20 個交易日：只收進場 ≥ 新起點的訊號、年化／回落從新起點算到主窗尾；0050 同窗重算；各 200 顆
  ④ relvol − 隨機：#13 − #14（同訊號、pick=None）同顆種子配對差；CI ＝ 平均 ± 1.96 × 標準差 ÷ √200（種子間的抽籤變異，⛔ 不是市場抽樣誤差）
判準：使用者的合格／另列／不合格（年化中位 ＞ 0050 同窗；比值 ≥ 0050 同窗比值）；「穩」照 seq253 收緊
輸出 backtest/resultsYLretest/
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import research11 as R
from backtest import universe_gate as UG

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsYLretest")
SEED0 = 7000
TAG = "停止交易強制出場：開"
_G: dict = {}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def engine(sig, r, pick="relvol", sf=None):
    kw = {"stop_force": sf} if sf is not None else {}
    return R.simulate_mtm(sig, "H60", 20, np.random.default_rng(SEED0 + r), _G["closes"], _G["opens"], _G["ncal"], return_equity=True,
                          log=[], d_max=None, pick=pick, queue_days=0, **kw)


def run_one(args):
    key, r = args
    sig, pick, sf, w0 = _G["CELLS"][key]
    s = engine(sig, r, pick, sf)
    c, m, v = RR.win_metrics(s["equity"], s["first"], s["end"], w0, _G["w1"])
    return {"key": key, "r": r, "cagr": float(c), "mdd": float(m), "vol": float(v), "first": int(s["first"]), "end": int(s["end"]),
            "trades": int(s["trades"]), "eq_sha": sha(s["equity"]), "forced": int(s.get("x_stop_force_n", -1))}


def fake_rows(i):
    """一次假訊號：每筆真訊號 ⇒ 同月隨機交易日 × 當天有 K 棒的隨機股。"""
    rng = np.random.default_rng([20260927, i])
    real = _G["REAL"]; days_by_m = _G["DAYS_BY_M"]; alive = _G["ALIVE"]; B = _G["BARS"]
    rows = []
    for m_ in real["m"].to_numpy():
        ds = days_by_m[m_]
        for _ in range(50):
            d = int(ds[rng.integers(len(ds))])
            pool = alive.get(d)
            if pool is None or not len(pool):
                continue
            sid = pool[rng.integers(len(pool))]
            idx, o, c, amt, nb_ = B[sid]
            k = int(np.searchsorted(idx, d))
            if k + 1 >= len(idx):
                continue
            if k >= 60:
                med = float(np.nanmedian(amt[k - 60:k]))
                rel = float(amt[k]) / med if med > 0 and np.isfinite(amt[k]) else np.nan
            else:
                rel = np.nan
            nb = nb_[max(0, k - 20)]
            r = R.fixed_exit(o, c, k, 60, nb) if nb > k else None
            rows.append((sid, k, d, int(idx[k + 1]), int(idx[r[0]]) if r else -1, float(r[1]) if r else np.nan, rel))
            break
    F = pd.DataFrame(rows, columns=["sid", "k", "pos", "entry_pos", "xpos_H60", "g_H60", "relvol"]).drop_duplicates(["sid", "entry_pos"])
    return F


def fake_one(i):
    F = fake_rows(i)
    e = F["entry_pos"].to_numpy()
    F = F[(e >= _G["w0"]) & (e <= _G["w1"])].reset_index(drop=True)
    s = engine(F, i, "relvol", _G["SF"])
    c, m, v = RR.win_metrics(s["equity"], s["first"], s["end"], _G["w0"], _G["w1"])
    return {"i": i, "cagr": float(c), "mdd": float(m), "ratio": float(c / abs(m)) if m else np.nan, "n_rows": int(len(F)),
            "n_valid": int((F["xpos_H60"] >= 0).sum()), "trades": int(s["trades"])}


def label(c, m, b):
    r50 = b["cagr"] / abs(b["mdd"])
    return "合格" if (c > b["cagr"] and c / abs(m) >= r50) else ("另列" if c > b["cagr"] else "不合格")


def med(rows):
    c = float(np.median([x["cagr"] for x in rows])); m = float(np.median([x["mdd"] for x in rows]))
    return c, m, c / abs(m)


def b1(a):
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16] for f in ("researchYLretest.py", "research11.py", "rerun17.py")}
    log(f"===== researchYLretest b1 procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜{src} =====")
    S = {"停止交易強制出場": "開", "程式": src}
    cal = D.load_calendar()
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log)
    G = RR._G; w0, w1, ncal = G["w0"], G["w1"], G["ncal"]
    AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    sig = AND[(e >= w0) & (e <= w1)].reset_index(drop=True)
    U = D.load_universe(); U = U[U["stock_id"].isin(set(UG.gate3(pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str))["stock_id"]))]
    mk = U.set_index("stock_id")["market"]
    closes, opens = RR.load_prices(sorted(set(U["stock_id"])), cal, mk, "branch")
    for s_ in G["closes"]:                                  # AND 股沿用原件價格（逐位元）
        closes[s_] = G["closes"][s_]; opens[s_] = G["opens"][s_]
    valid = R.valid_from_data(sorted(closes), mk, cal)
    SF = R.stop_force_days(valid, w1)
    S["停止交易股（母體、主窗內）"] = len(SF)
    _G.update(closes=closes, opens=opens, ncal=ncal, w0=w0, w1=w1, SF=SF)
    bench = RR.load_bench(cal); b50 = RR.bench_row(cal, bench, w0, w1 + 1); S["0050主窗"] = b50
    CELLS = {"#13_關": (sig, "relvol", None, w0), "#13_開": (sig, "relvol", SF, w0), "#14_開": (sig, None, SF, w0)}
    for sh in (5, 10, 15, 20):
        ws = w0 + sh; es = sig["entry_pos"].to_numpy()
        CELLS[f"#13_開_起點+{sh}"] = (sig[es >= ws].reset_index(drop=True), "relvol", SF, ws)
    _G["CELLS"] = CELLS
    t0 = time.time(); RES = {k: [] for k in CELLS}
    with Pool(a.procs) as pool:
        for x in pool.imap_unordered(run_one, [(k, r) for k in CELLS for r in range(a.reps)], chunksize=4):
            RES[x["key"]].append(x)
    log(f"  [主窗各格] {len(CELLS)} 格 × {a.reps} 顆｜{time.time() - t0:.0f}s")
    seeds = pd.DataFrame([x for v in RES.values() for x in v]).sort_values(["key", "r"])
    seeds.to_csv(os.path.join(OUT, "b1_seeds.csv"), index=False)
    # 閘：關 ＝ seeds_main #13
    ref = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["cell"] == 13) & (ref["mode"] == "win")].sort_values("r").reset_index(drop=True)
    off = seeds[seeds["key"] == "#13_關"].sort_values("r").reset_index(drop=True)
    bad = {k: int(sum(repr(float(x)) != repr(float(y)) for x, y in zip(off[k], ref[k]))) for k in ("cagr", "mdd", "vol")}
    bad.update({k: int((off[k].astype(str) != ref[k].astype(str)).sum()) for k in ("eq_sha", "trades", "first", "end")})
    S["閘_關＝seeds_main#13"] = bad; log(f"[閘 關＝原件] {bad}")
    if any(bad.values()):
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        raise SystemExit("⛔ 閘不過")
    CEL = {}
    for k, rows in RES.items():
        c, m, rt = med(rows)
        bw = b50 if not k.startswith("#13_開_起點") else RR.bench_row(cal, bench, CELLS[k][3], w1 + 1)
        CEL[k] = {"年化中位": c, "回落中位": m, "比值": rt, "標籤": label(c, m, bw), "0050同窗": bw, "強制出場每顆": float(np.mean([x["forced"] for x in rows])),
                  "交易筆中位": float(np.median([x["trades"] for x in rows])), "年化p10": float(np.percentile([x["cagr"] for x in rows], 10)),
                  "年化p90": float(np.percentile([x["cagr"] for x in rows], 90))}
    S["格"] = CEL
    on = seeds[seeds["key"] == "#13_開"].set_index("r"); of_ = off.set_index("r")
    S["①開vs關"] = {"年化差_點": (CEL["#13_開"]["年化中位"] - CEL["#13_關"]["年化中位"]) * 100, "回落差_點": (CEL["#13_開"]["回落中位"] - CEL["#13_關"]["回落中位"]) * 100,
                  "逐顆年化有變的顆數": int((on["cagr"] != of_["cagr"]).sum())}
    # ④ #13 − #14 配對
    s14 = seeds[seeds["key"] == "#14_開"].set_index("r")
    dd = {}
    for k_ in ("cagr", "mdd"):
        d = (on[k_] - s14[k_]).to_numpy()
        dd[k_] = {"平均": float(d.mean()), "CI": [float(d.mean() - 1.96 * d.std(ddof=1) / np.sqrt(len(d))), float(d.mean() + 1.96 * d.std(ddof=1) / np.sqrt(len(d)))],
                  "中位": float(np.median(d)), "為正顆數": int((d > 0).sum())}
    dr = (on["cagr"] / on["mdd"].abs() - s14["cagr"] / s14["mdd"].abs()).to_numpy()
    dd["ratio"] = {"平均": float(dr.mean()), "CI": [float(dr.mean() - 1.96 * dr.std(ddof=1) / np.sqrt(len(dr))), float(dr.mean() + 1.96 * dr.std(ddof=1) / np.sqrt(len(dr)))],
                   "中位": float(np.median(dr)), "為正顆數": int((dr > 0).sum())}
    S["④relvol減隨機"] = dd
    # ② 假訊號
    real = sig[sig["xpos_H60"] >= 0].copy()
    mon = np.array([str(x)[:7] for x in cal]); real["m"] = mon[real["pos"].to_numpy(int)]
    days_by_m = {m_: np.array([d for d in range(len(cal)) if mon[d] == m_]) for m_ in set(real["m"])}
    BARS = {}; alive = {}
    for s_ in sorted(closes):
        Bx = R.load_bars(s_, mk.get(s_, "twse"), cal)
        if Bx is None:
            continue
        BARS[s_] = (Bx["idx"], Bx["o"], Bx["c"], Bx["amt"], Bx["next_bad"])
        for d in Bx["idx"]:
            alive.setdefault(int(d), []).append(s_)
    alive = {d: np.array(v) for d, v in alive.items()}
    _G.update(REAL=real, DAYS_BY_M=days_by_m, ALIVE=alive, BARS=BARS)
    t0 = time.time()
    with Pool(a.procs) as pool:
        FK = pd.DataFrame(list(pool.imap_unordered(fake_one, range(a.reps), chunksize=4))).sort_values("i")
    FK.to_csv(os.path.join(OUT, "b1_fake.csv"), index=False)
    log(f"  [假訊號] {a.reps} 次｜{time.time() - t0:.0f}s")
    main_ratio = CEL["#13_開"]["比值"]
    Fcdf = float((FK["ratio"] <= 1.124).mean())
    S["②假訊號"] = {"真訊號筆數（窗內、有 H60 出場）": int(len(real)), "假訊號_年化中位": float(FK["cagr"].median()), "假訊號_回落中位": float(FK["mdd"].median()),
                  "假訊號_比值中位": float(FK["ratio"].median()), "p（假訊號比值 ≥ 本格開關版比值）": float((FK["ratio"] >= main_ratio).mean()),
                  "p（假訊號比值 ≥ 1.124）": float((FK["ratio"] >= 1.124).mean()), "假訊號標籤分佈": FK.apply(lambda x: label(x["cagr"], x["mdd"], b50), axis=1).value_counts().to_dict(),
                  "219取最好_估計": {"做法": "以 #13 假訊號比值分佈 F 當每格虛無分佈、格間視為獨立 ⇒ P(最好 ≤ 1.124) ＝ F(1.124)^K（⚠ 估計、沒跑 219 格假訊號；獨立假設使 K＝219 偏嚴）",
                                  "F(1.124)": Fcdf, "K=219 百分位": Fcdf ** 219, "K=17 百分位": Fcdf ** 17}}
    log(f"[假訊號] {S['②假訊號']}")
    S["秒"] = round(time.time() - t00)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report()


# ═════════════════════════════════════════════════════════════════════════════════════
# 第二批（裁定 seq257 §三 順 1 後補項＋協調追加「219 取最好」隨機分數）⭐ 停止交易強制出場：開
#   b2m（主窗；快照 edc6f）：
#     ⑤ 219 取最好的選擇偏誤（描述）：在 AND 訊號集本身上，把 relvol 換成隨機分數（＝ pick=None、rng.permutation，#14 那種挑法），
#        照 219 表裡【以 AND 訊號集為底】的 63 格掃變體軸（PREREG10 AND 12 格、PREREG11 AND 12 格、P1 AND 22 格、P3 乙 17 格）；
#        relvol 與 null 兩格在隨機分數下是同一個設定 ⇒ 44 個不重複設定；S／G／OR 與其他族不是 AND 底 ⇒ ⛔ 不在範圍（逐字標）
#        每顆種子 r（0～199）各設定跑一次（引擎照 rerun17._sim_engine／Year1M.run_engine：P10 族 1000＋r；P1、P3 乙 7000＋r）
#        ⇒ 每顆的「44 設定中最大比值」分佈；#13 的 1.124 落在第幾百分位；另報各設定 200 顆中位
#     ⑥ 下市公司月營收：資料庫 mops/revenue_hist 沒有主窗內下市公司的月營收（147 檔下市、代號在營收檔出現的 20 檔多為代號回收）
#        ⇒ 照 P4（researchp4.survivor_bound，〈九十四〉有界論證）報下界：把「下市股、該日沒有營收面板」的 S 訊號（主窗內）全部當成 AND 訊號加進來，
#        報酬代入邊界值（−100％ 下市歸零／0％ 原價出場；⛔ 不挑代理組），relvol 照原件公式算；加進來的列不套強制出場（照邊界值出）
#   b2e（早年段；early 版面 3edc0e2206、只上市、窗 2012-06-04～2014-12-31）：
#     ⑦ 主版（main）與剔轉上市版（noT）：開強制出場 200 顆（閘：關的時候 ＝ resultsV/body_seeds.csv.gz #13 逐位元）
#     ⑧ H 30～80（每 10）、N 10／20／30：H 的出場欄照原件產生器（fixed_exit＋next_bad）＋T1 資料尾補回（Year1M.and_censor 同式）
#        ＋R8 減資截斷（researchV.apply_events 同式）重算；閘：重算的 H60 欄 ＝ Year1M._G AND_mtm 的 H60 欄逐位元
#   上櫃（早年）：early 版面只建上市（裁定 seq206）⇒ 要另建含上櫃的早年版面（上櫃還原事件、上櫃營收、上櫃 AND 四步）⇒ ⏳ 本批沒做（逐字標）
# ═════════════════════════════════════════════════════════════════════════════════════
def cells_219_and():
    """219 表中以 AND 訊號集為底的格 ⇒ 隨機分數下不重複的設定。"""
    T = pd.read_csv(os.path.join(HERE, "resultsN219", "table219.csv"))
    fams = {"PREREG10／研究十三": "P10", "PREREG11／研究十三b": "P10", "P1": "P1", "P3 乙臂（閒置放 0050）": "P3B"}
    rows = []
    for fam, g in T[T["族"].isin(fams)].groupby("族"):
        for cell in g["格"]:
            parts = cell.split("｜")
            if fams[fam] == "P10":
                if parts[0] != "AND":
                    continue
                reg = parts[1] == "regime=True"; N = int(parts[2][1:]); rule = parts[3]
                rows.append({"族": fams[fam], "原格": f"{fam}｜{cell}", "reg": reg, "N": N, "rule": rule, "d": None})
            elif fams[fam] == "P1":
                if parts[0] != "AND":
                    continue
                N = int(parts[1][1:]); d = None if parts[2] == "d=inf" else float(parts[2][2:])
                rows.append({"族": "P1", "原格": f"{fam}｜{cell}", "reg": False, "N": N, "rule": "H60", "d": d})
            else:
                N = int(parts[1][1:]); d = None if parts[2] == "d=inf" else float(parts[2][2:])
                rows.append({"族": "P3B", "原格": f"{fam}｜{cell}", "reg": False, "N": N, "rule": "H60", "d": d})
    D_ = pd.DataFrame(rows)
    D_["設定"] = [f"{r.族}|reg={r.reg}|N{r.N}|{r.rule}|d={r.d}" for r in D_.itertuples()]
    return D_


def run_rand(args):
    cfg, r = args
    fam, reg, N, rule, d = cfg
    sig = _G["SIG_REG"] if reg else _G["SIG"]
    cl, op, ncal = _G["closes"], _G["opens"], _G["ncal"]
    if fam == "P10":
        s = R.simulate_mtm(sig, rule, N, np.random.default_rng(1000 + r), cl, op, ncal, return_equity=True, stop_force=_G["SF"])
    else:
        kw = dict(d_max=d, pick=None, queue_days=RR.P1_QUEUE if d is not None else 0, return_equity=True, stop_force=_G["SF"])
        if fam == "P1":
            s = R.simulate_mtm(sig, "H60", N, np.random.default_rng(SEED0 + r), cl, op, ncal, log=[], **kw)
        else:
            s = R.simulate_mtm(sig, "H60", N, np.random.default_rng(SEED0 + r), cl, op, ncal, cash_mode="bench", bench=_G["bench"],
                               bench_cost=RR.COST_STD / 2, **kw)
    c, m, _ = RR.win_metrics(s["equity"], s["first"], s["end"], _G["w0"], _G["w1"])
    return {"設定": "|".join(map(str, (fam, f"reg={reg}", f"N{N}", rule, f"d={d}"))), "r": r, "cagr": float(c), "mdd": float(m),
            "ratio": float(c / abs(m)) if m else np.nan}


def run_bound(args):
    tag, r = args
    sig, sf = _G["BOUND"][tag]
    s = R.simulate_mtm(sig, "H60", 20, np.random.default_rng(SEED0 + r), _G["closes"], _G["opens"], _G["ncal"], return_equity=True,
                       log=[], d_max=None, pick="relvol", queue_days=0, stop_force=sf)
    c, m, _ = RR.win_metrics(s["equity"], s["first"], s["end"], _G["w0"], _G["w1"])
    return {"tag": tag, "r": r, "cagr": float(c), "mdd": float(m)}


def b2m(a):
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    log(f"===== researchYLretest b2m procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    SP = os.path.join(OUT, "summary.json"); S = json.load(open(SP, encoding="utf-8"))
    cal = D.load_calendar()
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", log)
    G = RR._G; w0, w1, ncal = G["w0"], G["w1"], G["ncal"]
    AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    sig = AND[(e >= w0) & (e <= w1)].reset_index(drop=True)
    sig_reg = sig[G["regime"][sig["entry_pos"].to_numpy()]].reset_index(drop=True)
    U = D.load_universe(); U = U[U["stock_id"].isin(set(UG.gate3(pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str))["stock_id"]))]
    mk = U.set_index("stock_id")["market"]
    # ⑥ 下界用的 S 列（下市股、沒有營收面板）
    Ssig = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "signals_S.csv.gz"), dtype={"sid": str},
                       usecols=["sid", "k", "pos", "entry_pos", "month", "g_H60", "xpos_H60"])
    dl = pd.read_csv(os.path.join(RR.H2D, "meta", "delisted.csv"), dtype=str)
    dls = set(dl["stock_id"])
    PR = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"])
    by = {s_: g["signal_pos"].to_numpy() for s_, g in PR.sort_values(["stock_id", "signal_pos"]).groupby("stock_id")}
    es = Ssig["entry_pos"].to_numpy()
    Sw = Ssig[(es >= w0) & (es <= w1) & Ssig["sid"].isin(dls) & (Ssig["xpos_H60"] >= 0)].copy()

    def has_rev(s_, pos):
        sp = by.get(s_)
        if sp is None:
            return False
        j = int(np.searchsorted(sp, pos, side="right")) - 1
        return j >= 0 and pos - sp[j] <= 45                      # research13.STALE_MAX
    miss = Sw[[not has_rev(s_, int(p_)) for s_, p_ in zip(Sw["sid"], Sw["pos"])]].copy()
    sids_all = sorted(set(G["closes"]) | set(miss["sid"]))
    closes, opens = RR.load_prices(sids_all, cal, mk, "branch")
    for s_ in G["closes"]:
        closes[s_] = G["closes"][s_]; opens[s_] = G["opens"][s_]
    valid = R.valid_from_data(sids_all, mk, cal)
    SF = R.stop_force_days(valid, w1)
    rel = []
    for s_, k in zip(miss["sid"], miss["k"].astype(int)):
        B = R.load_bars(s_, mk.get(s_, "twse"), cal)
        if B is None or k < 60:
            rel.append(np.nan); continue
        med_ = float(np.nanmedian(B["amt"][k - 60:k])); rel.append(float(B["amt"][k]) / med_ if med_ > 0 and np.isfinite(B["amt"][k]) else np.nan)
    miss["relvol"] = rel
    S["⑥下市月營收"] = {"資料庫有沒有": "沒有：mops/revenue_hist 主窗內下市 147 檔，代號在營收檔出現的只 20 檔、且多為代號回收（最後營收月晚於下市月）",
                     "照 P4 報下界的做法": "下市股（meta/delisted.csv）在主窗內、當天沒有營收面板（research13.and_flags 的 STALE_MAX 45 日內沒有列）的 S 訊號，全部當成 AND 加進來；"
                                        "H60 報酬代入邊界值 −100％（下市歸零）／0％（原價出場）；⛔ 不挑代理組（〈九十四〉）；加進來的列不套強制出場",
                     "加進來的列": int(len(miss)), "檔數": int(miss["sid"].nunique())}
    BOUND = {}
    for tag, v in (("下界_−100％", -1.0), ("下界_0％", 0.0)):
        add = miss.copy(); add["g_H60"] = v
        sg = pd.concat([sig, add[sig.columns.intersection(add.columns)]], ignore_index=True)
        BOUND[tag] = (sg, {s_: L for s_, L in SF.items() if s_ not in set(miss["sid"])})
    bench = RR.load_bench(cal); b50 = RR.bench_row(cal, bench, w0, w1 + 1)
    _G.update(closes=closes, opens=opens, ncal=ncal, w0=w0, w1=w1, SF=SF, SIG=sig, SIG_REG=sig_reg, bench=G["bench"], BOUND=BOUND)
    t0 = time.time(); resb = {k: [] for k in BOUND}
    fb = os.path.join(OUT, "b2_bound_seeds.csv")
    if a.reuse_bound and os.path.exists(fb):
        # 行程中斷後續跑：⑥ 的 400 顆已落檔（b2_bound_seeds.csv）⇒ 直接讀回、不重跑；加進來的列須與落檔的 b2_bound_rows.csv 相同
        old = pd.read_csv(os.path.join(OUT, "b2_bound_rows.csv"), dtype={"sid": str})
        if list(old["sid"]) != list(miss["sid"]) or list(old["entry_pos"]) != list(miss["entry_pos"]):
            raise SystemExit("⛔ 續跑：加進來的列與落檔不同")
        for x in pd.read_csv(fb, float_precision="round_trip").to_dict("records"):
            resb[x["tag"]].append(x)
        if any(len(v) != a.reps for v in resb.values()):
            raise SystemExit("⛔ 續跑：落檔顆數不對")
        log("  [⑥ 下界] 續跑：讀回 b2_bound_seeds.csv（23:16 落檔）")
    else:
        with Pool(a.procs) as pool:
            for x in pool.imap_unordered(run_bound, [(k, r) for k in BOUND for r in range(a.reps)], chunksize=4):
                resb[x["tag"]].append(x)
    pd.DataFrame([x for v in resb.values() for x in v]).to_csv(os.path.join(OUT, "b2_bound_seeds.csv"), index=False)
    miss.to_csv(os.path.join(OUT, "b2_bound_rows.csv"), index=False)
    for k, rows in resb.items():
        c, m, rt = med(rows)
        S["⑥下市月營收"][k] = {"年化中位": c, "回落中位": m, "比值": rt, "標籤": label(c, m, b50)}
    log(f"  [⑥ 下界] {time.time() - t0:.0f}s｜{S['⑥下市月營收']}")
    # ⑤ 219 隨機分數
    C219 = cells_219_and()
    cfgs = C219.drop_duplicates("設定")[["族", "reg", "N", "rule", "d"]].itertuples(index=False)
    # ⚠ drop_duplicates 會把 d 欄的 None 變成 NaN ⇒ 轉回 None（d＝∞：d_max＝None、queue_days＝0）；
    #   2026-09-28 00:3x 修：先前 d＝∞ 的 P1／P3 乙設定誤以 d_max＝NaN、queue_days＝5 跑，那些列已刪掉重跑（P10 族不用 d，只改名）
    cfgs = [(f_, bool(rg), int(N_), str(ru), None if pd.isna(d_) else float(d_)) for f_, rg, N_, ru, d_ in cfgs]
    t0 = time.time()
    # 邊跑邊落檔（b2_rand219_part.csv）⇒ 行程中斷可續跑；續跑時已有的 (設定, r) 不重跑
    fp = os.path.join(OUT, "b2_rand219_part.csv")
    done = pd.read_csv(fp, float_precision="round_trip") if os.path.exists(fp) else pd.DataFrame(columns=["設定", "r", "cagr", "mdd", "ratio"])
    have = set(zip(done["設定"], done["r"].astype(int)))
    key = lambda cf: "|".join(map(str, (cf[0], f"reg={cf[1]}", f"N{cf[2]}", cf[3], f"d={cf[4]}")))
    todo = [(cf, r) for cf in cfgs for r in range(a.reps) if (key(cf), r) not in have]
    log(f"  [⑤] 已落檔 {len(have)} 組、待跑 {len(todo)} 組")
    with open(fp, "a", encoding="utf-8") as fh:
        if not have:
            fh.write("設定,r,cagr,mdd,ratio\n")
        with Pool(a.procs) as pool:
            for x in pool.imap_unordered(run_rand, todo, chunksize=4):
                fh.write(f"{x['設定']},{x['r']},{x['cagr']!r},{x['mdd']!r},{x['ratio']!r}\n"); fh.flush()
    RND = pd.read_csv(fp, float_precision="round_trip")
    RND = RND[RND["設定"].isin([key(cf) for cf in cfgs]) & (RND["r"] < a.reps)].drop_duplicates(["設定", "r"]).sort_values(["設定", "r"]).reset_index(drop=True)
    if len(RND) != len(cfgs) * a.reps:
        raise SystemExit(f"⛔ ⑤ 顆數 {len(RND)} ≠ {len(cfgs) * a.reps}")
    RND.to_csv(os.path.join(OUT, "b2_rand219.csv"), index=False)
    log(f"  [⑤ 219 隨機分數] {len(cfgs)} 設定 × {a.reps} 顆｜{time.time() - t0:.0f}s")
    mx = RND.groupby("r")["ratio"].max()
    per = RND.groupby("設定").apply(lambda g: float(g["cagr"].median()) / abs(float(g["mdd"].median())))
    S["⑤219隨機分數"] = {"做法": "AND 訊號集上 relvol 換成隨機分數（pick=None）；219 表中以 AND 為底的 63 格 ⇒ 不重複設定 " + str(len(cfgs)) +
                         " 個（relvol／null 兩格在隨機分數下同一設定）；每顆種子各設定一次 ⇒ 每顆取 " + str(len(cfgs)) +
                         " 設定中的最大比值；⚠ 單顆比值比 200 顆中位雜 ⇒ 最大值分佈偏大（對 #13 偏嚴）；S／G／OR 與非 AND 族不在範圍",
                     "63 格": int(len(C219)), "不重複設定": len(cfgs), "每顆最大比值_中位": float(mx.median()), "p10": float(mx.quantile(.1)), "p90": float(mx.quantile(.9)),
                     "1.124 的百分位（最大值 ≤ 1.124 的比例）": float((mx <= 1.124).mean()),
                     "各設定 200 顆中位比值_最大": float(per.max()), "各設定 200 顆中位比值_最大的設定": str(per.idxmax()),
                     "各設定 200 顆中位比值 ≥ 1.124 的設定數": int((per >= 1.124).sum())}
    # 同尺度版（⭐ 與 #13 的 1.124 同為「200 顆中位年化／|200 顆中位回落|」）：種子自助抽樣 2,000 次（同一組種子套到全部設定、保留格間相關）
    #   ⇒ 每次取各設定中位比值的最大 ⇒ 「最大中位比值」的分佈
    Cm = RND.pivot(index="r", columns="設定", values="cagr").to_numpy(float)
    Mm = RND.pivot(index="r", columns="設定", values="mdd").to_numpy(float)
    rb = np.random.default_rng(20260928); bs = []
    for _ in range(2000):
        ix = rb.integers(0, Cm.shape[0], Cm.shape[0])
        bs.append(float(np.max(np.median(Cm[ix], axis=0) / np.abs(np.median(Mm[ix], axis=0)))))
    bs = np.array(bs)
    S["⑤219隨機分數"].update({"同尺度_做法": "種子自助抽樣 2,000 次（rng 20260928；同一組抽到的種子套到全部設定）⇒ 每次各設定算 200 顆中位年化／|中位回落|、取設定間最大",
                              "同尺度_最大中位比值_中位": float(np.median(bs)), "同尺度_p5": float(np.quantile(bs, .05)), "同尺度_p95": float(np.quantile(bs, .95)),
                              "同尺度_1.124 的百分位": float((bs <= 1.124).mean())})
    per.rename("中位比值").to_csv(os.path.join(OUT, "b2_rand219_cfg.csv"))
    log(f"[⑤] {S['⑤219隨機分數']}")
    S["b2m秒"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


# ── 早年段 ──
def exits_H(T, H, cal, uni, EV, ncal):
    """早年 AND 表的 H 出場欄：fixed_exit＋next_bad（hsweep.exits）＋T1 資料尾補回（Year1M.and_censor）＋R8 截斷（researchV.apply_events）。"""
    xp = np.full(len(T), -1, np.int64); gg = np.full(len(T), np.nan)
    cache = {}
    for i, (s_, k) in enumerate(zip(T["sid"].to_numpy(), T["k"].to_numpy(int))):
        if s_ not in cache:
            B = R.load_bars(s_, uni.get(s_, "twse"), cal); cache[s_] = B
        B = cache[s_]
        if B is None:
            continue
        idx, o, c, nbar = B["idx"], B["o"], B["c"], B["next_bad"]; n = len(idx)
        nb = nbar[max(0, k - 20)]
        r = R.fixed_exit(o, c, k, H, nb)
        if r:
            xp[i] = int(idx[r[0]]); gg[i] = r[1]
        elif D.exit_pos(k + 1, H) >= n and nb > n - 1 and int(idx[n - 1]) == ncal - 1:
            xp[i] = ncal; gg[i] = float(c[n - 1] / o[k + 1] - 1.0)
    if EV is not None:
        pos = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(cal)}
        ev = {}
        for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
            if e_ in pos and L_ in pos:
                ev.setdefault(s_, []).append((pos[e_], pos[L_]))
        sidv = T["sid"].to_numpy(); ent = T["entry_pos"].to_numpy(int); pc = {}
        for s_, lst in ev.items():
            for i in np.flatnonzero(sidv == s_):
                for pe, pL in lst:
                    if xp[i] < 0 or not (ent[i] <= pL and xp[i] >= pe):
                        continue
                    if s_ not in pc:
                        st = D.load_stock(s_, "twse", cal); pc[s_] = (st.df["open"].to_numpy(float), st.df["close"].to_numpy(float))
                    o_, c_ = pc[s_]
                    xp[i] = pL; gg[i] = c_[pL] / o_[ent[i]] - 1.0
    return xp, gg


def run_early(args):
    key, r = args
    sig, N, rule, sf = _G["ECELLS"][key]
    kw = {"stop_force": sf} if sf is not None else {}
    s = R.simulate_mtm(sig, rule, N, np.random.default_rng(SEED0 + r), _G["closes"], _G["opens"], _G["NP"], return_equity=True,
                       log=[], d_max=None, pick="relvol", queue_days=0, **kw)
    c, m, _ = RR.win_metrics(s["equity"], s["first"], s["end"], _G["w0"], _G["w1"])
    return {"key": key, "r": r, "cagr": float(c), "mdd": float(m), "forced": int(s.get("x_stop_force_n", -1))}


def b2e(a):
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    log(f"===== researchYLretest b2e procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    SP = os.path.join(OUT, "summary.json"); S = json.load(open(SP, encoding="utf-8"))
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import early_data as E
    ref = pd.read_csv(os.path.join(HERE, "resultsV", "body_seeds.csv.gz"), float_precision="round_trip")
    OUTE = {}; SEEDS = []
    for variant in ("main", "noT"):
        V.body_setup(variant, log)
        cal = V._B["cal"]; w0, w1, ncal = V._B["w0"], V._B["w1"], V._B["ncal"]
        uni = D.load_universe().set_index("stock_id")["market"]
        T = Y.sig_of(13, "mtm", w0, w1).reset_index(drop=True)
        EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
        xp60, g60 = exits_H(T, 60, cal, uni, EV, ncal)
        gd = np.abs(g60 - T["g_H60"].to_numpy(float))
        gate = {"H60 xpos 不同": int((xp60 != T["xpos_H60"].to_numpy(np.int64)).sum()),
                "H60 g 差 ＞ 1e−12": int(np.nansum(gd > 1e-12))}
        OUTE[f"{variant}_H60 g 逐位元不同（CSV 讀檔的末位捨入；最大差）"] = [int(np.nansum(gd > 0)), float(np.nanmax(gd))]
        for H in (30, 40, 50, 70, 80):
            xp, gg = exits_H(T, H, cal, uni, EV, ncal); T[f"xpos_H{H}"] = xp; T[f"g_H{H}"] = gg
        valid = R.valid_from_data(sorted(Y._G["closes"]), uni, cal)
        SF = R.stop_force_days(valid, w1)
        cl, op, NP = Y._G["closes"], Y._G["opens"], Y._G["NP"]
        EC = {f"{variant}|關|N20|H60": (T, 20, "H60", None), f"{variant}|開|N20|H60": (T, 20, "H60", SF)}
        for N in (10, 30):
            EC[f"{variant}|開|N{N}|H60"] = (T, N, "H60", SF)
        for H in (30, 40, 50, 70, 80):
            EC[f"{variant}|開|N20|H{H}"] = (T, 20, f"H{H}", SF)
        _G.update(ECELLS=EC, closes=cl, opens=op, NP=NP, w0=w0, w1=w1)
        t0 = time.time(); res = {k: [] for k in EC}
        with Pool(a.procs) as pool:
            for x in pool.imap_unordered(run_early, [(k, r) for k in EC for r in range(a.reps)], chunksize=4):
                res[x["key"]].append(x)
        log(f"  [早年 {variant}] {len(EC)} 格｜{time.time() - t0:.0f}s")
        b50 = RR.bench_row(cal, RR.load_bench(cal), w0, w1 + 1)
        rr = ref[(ref["variant"] == variant) & (ref["cell"] == 13)].sort_values("r").reset_index(drop=True)
        off = pd.DataFrame(res[f"{variant}|關|N20|H60"]).sort_values("r").reset_index(drop=True)
        gate["關＝resultsV #13 逐位元（cagr／mdd 不同顆數）"] = int(sum(repr(x) != repr(float(y)) for x, y in zip(off["cagr"], rr["cagr"]))) + \
            int(sum(repr(x) != repr(float(y)) for x, y in zip(off["mdd"], rr["mdd"])))
        log(f"[閘 早年 {variant}] {gate}")
        OUTE[f"{variant}_閘"] = gate; OUTE[f"{variant}_0050"] = b50; OUTE[f"{variant}_停止交易股"] = len(SF)
        for k, rows in res.items():
            c, m, rt = med(rows)
            OUTE[k] = {"年化中位": c, "回落中位": m, "比值": rt, "標籤": label(c, m, b50), "強制出場每顆": float(np.mean([x["forced"] for x in rows]))}
            SEEDS += rows
    pd.DataFrame(SEEDS).to_csv(os.path.join(OUT, "b2_early_seeds.csv"), index=False)
    S["⑦⑧早年"] = OUTE
    S["上櫃早年"] = "⏳ 本批沒做：early 版面只建上市（裁定 seq206）；要另建含上櫃的早年版面（上櫃還原事件 otcexright／otcreduce、上櫃月營收、上櫃 AND 四步）才能跑"
    S["b2e秒"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    bad = any(v for g in (OUTE["main_閘"], OUTE["noT_閘"]) for v in g.values())
    if bad:
        raise SystemExit("⛔ 早年閘不過")


def _p(x):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = S["格"]; b = S["0050主窗"]; F = S["②假訊號"]; P = S["④relvol減隨機"]
    on, off = C["#13_開"], C["#13_關"]
    shifts = [C[f"#13_開_起點+{sh}"] for sh in (5, 10, 15, 20)]
    labs = [x["標籤"] for x in shifts]
    stable = len(set(labs + [on["標籤"]])) == 1
    L = ["# 營量 v1 重測（第一批＋第二批）", "", f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq257 §三 順 1；稽核 seq3 §七之二。回測線。⭐ **{TAG}**。", ""]
    E_ = S.get("⑦⑧早年"); R5 = S.get("⑤219隨機分數"); R6 = S.get("⑥下市月營收")
    if E_ and R5 and R6 and "同尺度_1.124 的百分位" in R5:
        m0, n0 = E_["main|開|N20|H60"], E_["noT|開|N20|H60"]
        L.append(f"**第二批結論：早年段（2012-06～2014-12、只上市）開強制出場後營量 v1 主版 {_p(m0['年化中位'])}／{_p(m0['回落中位'])}、{m0['標籤']}，"
                 f"剔轉上市版 {_p(n0['年化中位'])}／{_p(n0['回落中位'])}、{n0['標籤']}（0050 同窗 {_p(E_['main_0050']['cagr'])}／{_p(E_['main_0050']['mdd'])}）；"
                 f"H 30～80、N 10／20／30 的標籤隨參數變；219 取最好（隨機分數、{R5['不重複設定']} 個 AND 底設定）下 1.124 的百分位 "
                 f"同尺度 {R5['同尺度_1.124 的百分位']:.3f}、單顆最大 {R5['1.124 的百分位（最大值 ≤ 1.124 的比例）']:.3f}；"
                 f"下市月營收照 P4 報下界：−100％ {R6['下界_−100％']['標籤']}、0％ {R6['下界_0％']['標籤']}；上櫃早年沒做。**")
        L += ["", "| 第二批項 | 主版 | 剔轉上市版 |", "|---|---|---|"]
        for tail, nm in (("開|N20|H60", "早年 #13（開）"), ("開|N10|H60", "早年 N10"), ("開|N30|H60", "早年 N30"), ("開|N20|H30", "早年 H30"),
                         ("開|N20|H80", "早年 H80")):
            x, y = E_[f"main|{tail}"], E_[f"noT|{tail}"]
            L.append(f"| {nm} | {_p(x['年化中位'])}／{_p(x['回落中位'])}　{x['標籤']} | {_p(y['年化中位'])}／{_p(y['回落中位'])}　{y['標籤']} |")
        L += ["", "| 主窗第二批項 | 值 |", "|---|---|",
              f"| ⑤ 219 取最好：1.124 的百分位（同尺度／單顆最大） | {R5['同尺度_1.124 的百分位']:.3f}／{R5['1.124 的百分位（最大值 ≤ 1.124 的比例）']:.3f} |",
              f"| ⑥ 下市月營收下界 −100％ | {_p(R6['下界_−100％']['年化中位'])}／{_p(R6['下界_−100％']['回落中位'])}　{R6['下界_−100％']['標籤']} |",
              f"| ⑥ 下市月營收下界 0％ | {_p(R6['下界_0％']['年化中位'])}／{_p(R6['下界_0％']['回落中位'])}　{R6['下界_0％']['標籤']} |", "",
              "---", "", "## 第一批", ""]
    L.append(f"**結論：開強制出場後營量 v1 主窗 {_p(on['年化中位'])}／{_p(on['回落中位'])}、{on['標籤']}（與原件差 {S['①開vs關']['年化差_點']:+.2f} 點）；"
             f"假訊號 200 次的 p＝{F['p（假訊號比值 ≥ 本格開關版比值）']:.3f}；起點挪 1～4 週標籤{'都不變' if stable else '有變：' + '／'.join(labs)}；"
             f"relvol 比隨機的年化差 {P['cagr']['平均'] * 100:+.2f} 點（CI {P['cagr']['CI'][0] * 100:+.2f}～{P['cagr']['CI'][1] * 100:+.2f}）。**")
    L += ["", f"0050 主窗：年化 {_p(b['cagr'])}、回落 {_p(b['mdd'])}（比值 {b['cagr'] / abs(b['mdd']):.3f}）", "",
          "| 項 | 年化中位 | 回落中位 | 比值 | 標籤 |", "|---|---|---|---|---|",
          f"| 原件（關；＝ seeds_main #13 逐位元） | {_p(off['年化中位'])} | {_p(off['回落中位'])} | {off['比值']:.3f} | {off['標籤']} |",
          f"| ① 開強制出場 | {_p(on['年化中位'])} | {_p(on['回落中位'])} | {on['比值']:.3f} | {on['標籤']} |",
          f"| ② 假訊號（200 次中位） | {_p(F['假訊號_年化中位'])} | {_p(F['假訊號_回落中位'])} | {F['假訊號_比值中位']:.3f} | p＝{F['p（假訊號比值 ≥ 本格開關版比值）']:.3f} |"]
    for sh, x in zip((5, 10, 15, 20), shifts):
        L.append(f"| ③ 起點挪 {sh} 個交易日（0050 同窗 {_p(x['0050同窗']['cagr'])}／{_p(x['0050同窗']['mdd'])}） | {_p(x['年化中位'])} | {_p(x['回落中位'])} | {x['比值']:.3f} | {x['標籤']} |")
    L.append(f"| ④ #14 隨機挑（開） | {_p(C['#14_開']['年化中位'])} | {_p(C['#14_開']['回落中位'])} | {C['#14_開']['比值']:.3f} | {C['#14_開']['標籤']} |")
    L += ["", "## ① 停止交易強制出場", "", f"- 母體內主窗內停止交易的股票 {S['停止交易股（母體、主窗內）']} 檔；營量 v1 每顆實際強制出場 {on['強制出場每顆']:.2f} 筆；"
          f"年化差 {S['①開vs關']['年化差_點']:+.2f} 點、回落差 {S['①開vs關']['回落差_點']:+.2f} 點；200 顆裡年化有變的 {S['①開vs關']['逐顆年化有變的顆數']} 顆",
          f"- 閘：關的時候 200 顆與 resultsN17/seeds_main.csv #13 逐位元相同：{S['閘_關＝seeds_main#13']}", "",
          "## ② 假訊號（同月隨機日 × 隨機股，200 次）", "",
          f"- 真訊號（窗內、有 H60 出場）{F['真訊號筆數（窗內、有 H60 出場）']} 筆 ⇒ 每次換成同數量的隨機訊號；relvol 與 H60 出場照原件產生器算；強制出場開",
          f"- 假訊號比值中位 {F['假訊號_比值中位']:.3f}；比值 ≥ 本格（{on['比值']:.3f}）的比例 p＝{F['p（假訊號比值 ≥ 本格開關版比值）']:.3f}；≥ 1.124 的比例 {F['p（假訊號比值 ≥ 1.124）']:.3f}",
          f"- 假訊號對 0050 的標籤分佈：{F['假訊號標籤分佈']}",
          f"- 「219 取最好」百分位（⚠ 估計）：{F['219取最好_估計']['做法']}；F(1.124)＝{F['219取最好_估計']['F(1.124)']:.3f} ⇒ "
          f"K＝219：{F['219取最好_估計']['K=219 百分位']:.3f}、K＝17：{F['219取最好_估計']['K=17 百分位']:.3f}",
          "- ⚠ 怎麼讀：這個假訊號是「全母體隨機股 × 同月隨機日」，是弱的虛無——它只說明 AND 訊號集比隨便買好很多；"
          "⛔ 它【沒有】處理「219 格都是同一批 AND 訊號的變體、從中挑最好」的選擇偏誤（那要比的是 219 格真訊號彼此之間，不是對隨機股）"
          "⇒ 219 取最好的百分位＝1.000 是這個虛無下的結果，不代表挑選偏誤已排除", "",
          "## ③ 起點挪 1～4 週（seq253 收緊的「穩」）", "",
          f"- 標籤：原點 {on['標籤']}、挪 5／10／15／20 日 {'／'.join(labs)} ⇒ {'四個挪法標籤都和原點相同' if stable else '標籤會隨起點變 ⇒ ⛔ 不寫「穩」'}", "",
          "## ④ relvol − 隨機（#13 − #14，同顆種子配對、強制出場開）", "",
          f"- 年化差 平均 {P['cagr']['平均'] * 100:+.2f} 點（CI {P['cagr']['CI'][0] * 100:+.2f}～{P['cagr']['CI'][1] * 100:+.2f}；為正 {P['cagr']['為正顆數']}／200）",
          f"- 回落差 平均 {P['mdd']['平均'] * 100:+.2f} 點（CI {P['mdd']['CI'][0] * 100:+.2f}～{P['mdd']['CI'][1] * 100:+.2f}；為正＝較淺 {P['mdd']['為正顆數']}／200）",
          f"- 比值差 平均 {P['ratio']['平均']:+.3f}（CI {P['ratio']['CI'][0]:+.3f}～{P['ratio']['CI'][1]:+.3f}）",
          "- ⚠ 這個 CI 只量「同一批訊號、不同抽籤」的變異，⛔ 不是市場抽樣誤差（訊號本身只有一段歷史）", "",
          ]
    if S.get("⑦⑧早年"):
        E_ = S["⑦⑧早年"]
        L += ["## ⑦⑧ 早年段（2012-06-04～2014-12-31、只上市；描述）", "",
              f"- 閘：關的時候 ＝ resultsV #13 逐位元（主版 {E_['main_閘']}；剔轉上市 {E_['noT_閘']}）；早年停止交易股 主版 {E_['main_停止交易股']} 檔",
              f"- 0050 同窗：{_p(E_['main_0050']['cagr'])}／{_p(E_['main_0050']['mdd'])}（比值 {E_['main_0050']['cagr'] / abs(E_['main_0050']['mdd']):.3f}）", "",
              "| 格 | 主版 年化／回落（標籤） | 剔轉上市版 年化／回落（標籤） |", "|---|---|---|"]
        for tail in ("關|N20|H60", "開|N20|H60", "開|N10|H60", "開|N30|H60", "開|N20|H30", "開|N20|H40", "開|N20|H50", "開|N20|H70", "開|N20|H80"):
            x, y = E_[f"main|{tail}"], E_[f"noT|{tail}"]
            L.append(f"| {tail.replace('關', '原件（強制出場關）').replace('|', '／')} | {_p(x['年化中位'])}／{_p(x['回落中位'])}（{x['標籤']}） | {_p(y['年化中位'])}／{_p(y['回落中位'])}（{y['標籤']}） |")
        L += ["", f"- 上櫃（早年）：{S.get('上櫃早年')}", ""]
    if S.get("⑤219隨機分數"):
        R5 = S["⑤219隨機分數"]
        L += ["## ⑤ 「219 取最好」的選擇偏誤（描述）", "", f"- 做法：{R5['做法']}",
              f"- 每顆種子「{R5['不重複設定']} 設定中最大比值」的分佈：中位 {R5['每顆最大比值_中位']:.3f}（p10 {R5['p10']:.3f}、p90 {R5['p90']:.3f}）",
              f"- #13 的 1.124 在這個最大值分佈的百分位：{R5['1.124 的百分位（最大值 ≤ 1.124 的比例）']:.3f}",
              f"- ⭐ 同尺度版（{R5['同尺度_做法']}）：最大中位比值 中位 {R5['同尺度_最大中位比值_中位']:.3f}（p5 {R5['同尺度_p5']:.3f}、p95 {R5['同尺度_p95']:.3f}）；1.124 的百分位 {R5['同尺度_1.124 的百分位']:.3f}",
              "- ⚠ 過程紀錄：d＝∞ 的 P1／P3 乙設定（14 個）一度誤以 d_max＝NaN、queue_days＝5 跑（drop_duplicates 把 None 變 NaN），已刪掉那 2,800 列重跑；"
              "查核：隨機分數的 P1｜N20｜d＝∞ ＝ 第一批 #14_開 200／200 逐位元",
              "- ⚠ 範圍：只含 219 表中以 AND 訊號集為底的 63 格（44 個不重複設定）；S／G／OR 與其他族沒有納入 ⇒ 這是 219 格的子集",
              f"- 各設定 200 顆中位比值的最大：{R5['各設定 200 顆中位比值_最大']:.3f}（{R5['各設定 200 顆中位比值_最大的設定']}）；中位比值 ≥ 1.124 的設定 {R5['各設定 200 顆中位比值 ≥ 1.124 的設定數']} 個", ""]
    if S.get("⑥下市月營收"):
        R6 = S["⑥下市月營收"]
        L += ["## ⑥ 下市公司月營收（照 P4 報下界）", "", f"- 資料庫：{R6['資料庫有沒有']}", f"- 做法：{R6['照 P4 報下界的做法']}",
              f"- 加進來的列 {R6['加進來的列']}（{R6['檔數']} 檔）"]
        for k in ("下界_−100％", "下界_0％"):
            if k in R6:
                L.append(f"- {k}：{_p(R6[k]['年化中位'])}／{_p(R6[k]['回落中位'])}（比值 {R6[k]['比值']:.3f}、{R6[k]['標籤']}）")
        try:
            Ss = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "signals_S.csv.gz"), usecols=["entry_pos", "xpos_H60"])
            An = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), usecols=["entry_pos", "xpos_H60"])
            cal_ = D.load_calendar(); w0_, w1_ = RR.win_bounds(cal_)
            ns = int(((Ss["entry_pos"] >= w0_) & (Ss["entry_pos"] <= w1_) & (Ss["xpos_H60"] >= 0)).sum())
            na = int(((An["entry_pos"] >= w0_) & (An["entry_pos"] <= w1_) & (An["xpos_H60"] >= 0)).sum())
            L.append(f"- ⚠ 怎麼讀：下界假設這 {R6['加進來的列']} 列【全部】過營收條件；主窗有營收的 S 列過 AND 的比例是 {na:,}／{ns:,}＝{na / ns:.1%}"
                     " ⇒ 全數通過是極端假設，兩個下界都是「最壞情境」，⛔ 不是估計值；持有期間的逐日市值照實際收盤，只有出場報酬代入邊界值")
        except Exception as ex:
            L.append(f"- （S→AND 通過率沒算出來：{ex}）")
        L += [""]
    L += ["## 營量 v1 重測後建議狀態（本線讀法，⛔ 由裁定線定）", ""]
    pA = F["p（假訊號比值 ≥ 本格開關版比值）"]
    rec = []
    rec.append(f"- 強制出場：{'不影響結論' if abs(S['①開vs關']['年化差_點']) < 0.5 else '有影響'}")
    rec.append(f"- 假訊號：p＝{pA:.3f} ⇒ " + ("隨機訊號也常做得到 ⇒ 訊號本身的貢獻站不住" if pA >= 0.05 else "隨機訊號很少做得到 ⇒ 不是運氣"))
    rec.append(f"- 起點：{'不穩（標籤隨起點變）' if not stable else '四個挪法標籤不變'}")
    rec.append(f"- relvol：{'比隨機好、CI 不含 0' if P['cagr']['CI'][0] > 0 else '比隨機好不出來（CI 含 0 或為負）'}")
    if E_ and R5 and R6 and "同尺度_1.124 的百分位" in R5:
        q = R5["同尺度_1.124 的百分位"]
        rec.append(f"- 219 取最好（⑤，只含 {R5['不重複設定']} 個 AND 底設定）：同尺度百分位 {q:.3f}、單顆最大 {R5['1.124 的百分位（最大值 ≤ 1.124 的比例）']:.3f} ⇒ "
                   + ("1.124 高過隨機分數下「各設定取最好」的 95％ ⇒ relvol 的挑法不只是變體裡挑到運氣好的" if q >= 0.95 else
                      (f"隨機分數下光是在 {R5['不重複設定']} 個設定裡挑最好，比值就到 {R5['同尺度_最大中位比值_中位']:.3f}，1.124 比它低" if q < 0.05 else
                       "1.124 落在隨機分數下「各設定取最好」的分佈之內") + " ⇒ 選擇偏誤【無法排除】"))
        labs_e = {v: [E_[f"{v}|{t}"]["標籤"] for t in ("開|N20|H30", "開|N20|H40", "開|N20|H50", "開|N20|H60", "開|N20|H70", "開|N20|H80")] for v in ("main", "noT")}
        labs_n = {v: [E_[f"{v}|{t}"]["標籤"] for t in ("開|N10|H60", "開|N20|H60", "開|N30|H60")] for v in ("main", "noT")}
        rec.append(f"- 早年 #13（開）：主版 {E_['main|開|N20|H60']['標籤']}、剔轉上市版 {E_['noT|開|N20|H60']['標籤']}；早年停止交易強制出場每顆 "
                   f"{E_['main|開|N20|H60']['強制出場每顆']:.2f} 筆 ⇒ 強制出場在早年不改結果")
        rec.append(f"- 早年 H 30～80：主版 {'／'.join(labs_e['main'])}；剔轉上市 {'／'.join(labs_e['noT'])}；N 10／20／30：主版 {'／'.join(labs_n['main'])}；"
                   f"剔轉上市 {'／'.join(labs_n['noT'])} ⇒ 標籤隨 H、N 變 ⇒ ⛔ 不寫「穩」（seq253）；各格只報中位與標籤，⛔ 沒有各格的顯著檢定")
        rec.append(f"- 下市月營收：資料庫沒有 ⇒ 照 P4 報下界，−100％ {R6['下界_−100％']['標籤']}、0％ {R6['下界_0％']['標籤']} ⇒ "
                   "最壞情境下不合格，⚠ 但這是全數通過營收條件的極端假設；缺的影響【沒有】被排除，也沒有被證實")
        rec.append("- 上櫃早年：⏳ 沒做（要另建含上櫃的早年版面）")
        good = [f"主窗開強制出場後 {on['標籤']}"] + (["假訊號 p＜0.05"] if pA < 0.05 else []) + (["起點挪動標籤不變"] if stable else []) + \
            ([f"219 取最好同尺度百分位 {q:.3f}"] if q >= 0.95 else [])
        bad = ([f"早年 #13 主版只到「{E_['main|開|N20|H60']['標籤']}」"] if E_['main|開|N20|H60']['標籤'] != "合格" else []) + \
            (["早年 H／N 一動標籤就變"] if len(set(labs_e['main'] + labs_n['main'])) > 1 else []) + \
            ([f"219 取最好同尺度百分位只有 {q:.3f}"] if q < 0.95 else []) + \
            ([f"下市月營收下界 {R6['下界_0％']['標籤']}（最壞情境）"] if R6['下界_0％']['標籤'] != "合格" else []) + ["上櫃早年未測"]
        rec.append(f"- 本線讀法：站得住的——{'、'.join(good)}；沒過或沒測的——{'、'.join(bad)} ⇒ "
                   + ("本線認為「暫定」的理由沒有被這兩批解除，⛔ 不建議升格" if bad else "本線看不到留在暫定的理由") + "；由裁定線定")
        L += rec + [""]
    else:
        rec.append(f"- 219 取最好（估計）：K＝17 百分位 {F['219取最好_估計']['K=17 百分位']:.3f}、K＝219 {F['219取最好_估計']['K=219 百分位']:.3f}"
                   "；⚠ 但同訊號變體之間的挑選偏誤不在這個虛無裡")
        L += rec + ["- 第二批出來後再給完整建議", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["b1", "b2m", "b2e", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--reuse-bound", action="store_true")
    a = ap.parse_args()
    {"b1": b1, "b2m": b2m, "b2e": b2e}.get(a.mode, lambda _: None)(a)
    report()

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


def _p(x):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"


def report():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = S["格"]; b = S["0050主窗"]; F = S["②假訊號"]; P = S["④relvol減隨機"]
    on, off = C["#13_開"], C["#13_關"]
    shifts = [C[f"#13_開_起點+{sh}"] for sh in (5, 10, 15, 20)]
    labs = [x["標籤"] for x in shifts]
    stable = len(set(labs + [on["標籤"]])) == 1
    L = ["# 營量 v1 重測（第一批）", "", f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq257 §三 順 1；稽核 seq3 §七之二。回測線。⭐ **{TAG}**。", ""]
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
          "## 營量 v1 重測後建議狀態（本線讀法，⛔ 由裁定線定）", ""]
    pA = F["p（假訊號比值 ≥ 本格開關版比值）"]
    rec = []
    rec.append(f"- 強制出場：{'不影響結論' if abs(S['①開vs關']['年化差_點']) < 0.5 else '有影響'}")
    rec.append(f"- 假訊號：p＝{pA:.3f} ⇒ " + ("隨機訊號也常做得到 ⇒ 訊號本身的貢獻站不住" if pA >= 0.05 else "隨機訊號很少做得到 ⇒ 不是運氣"))
    rec.append(f"- 219 取最好（估計）：K＝17 百分位 {F['219取最好_估計']['K=17 百分位']:.3f}、K＝219 {F['219取最好_估計']['K=219 百分位']:.3f}"
               "；⚠ 但同訊號變體之間的挑選偏誤不在這個虛無裡 ⇒ 暫定理由「同窗挑同判、219 取最好」本身【沒有】被這批結果解除，要等早年段（第二批）")
    rec.append(f"- 起點：{'不穩（標籤隨起點變）' if not stable else '四個挪法標籤不變'}")
    rec.append(f"- relvol：{'比隨機好、CI 不含 0' if P['cagr']['CI'][0] > 0 else '比隨機好不出來（CI 含 0 或為負）'}")
    L += rec + ["- 第二批（早年強制出場、上櫃、H 30～80、檔數 10／20／30、剔轉上市、下市月營收下界）出來後再給完整建議", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["b1", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    b1(a) if a.mode == "b1" else report()

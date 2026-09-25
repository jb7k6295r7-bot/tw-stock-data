# -*- coding: utf-8 -*-
"""PREREG探索批【探索段】的切點 fixture 與引擎對帳（登錄 §一：「回測線以資料切點實作、交件附切點 fixture」）。

    python3 backtest/selftest_explore.py fixture [--full] [--reuse] [--out backtest/resultsExplore]   # --reuse：已跑過的擾動／前視目錄直接拿來比
    python3 backtest/selftest_explore.py w1       # 引擎呼叫 ＝ W1：全期資料上重現 resultsAFC/w1_1000.csv 前 20 顆
    python3 backtest/selftest_explore.py elig     # 截斷日曆重建的 eligible ＝ AFC 面板同量測日的 eligible
    python3 backtest/selftest_explore.py probe    # 擾動確實有作用：每類檔案 CUT 後的列變了、CUT 前一字不差

fixture（先證明分得出來、不假紅〈一百二十六〉）：
  ① 不變性：--perturb 777（CUT 以後的價／量／法人／融資／本益比／還原事件／月營收改亂數並亂刪 30% 列；日曆 CUT 以後亂刪 30%；
     上市／下市日期 CUT 以後改成亂的 CUT 以後日期）⇒ features.csv、cands.csv、cand_stats.csv 逐位元相同；
     引擎：每格前 3 顆＋S0 前 20 顆＋W1ref 前 3 顆，逐種子 cagr／mdd／tr／expo／vol／trades／權益曲線 sha1 全相同
     （--full：全尺寸重跑，所有輸出檔 sha256 相同）
  ② 鑑別力：--leak（F05 在 2022-12-01 量測日故意讀 2023-01-03 的收盤）在真資料與擾動資料上各跑一次 ⇒ 要【不同】
     （同一個 perturb 抓得到前視 ⇒ ①的「相同」不是因為 fixture 沒有作用）
"""
import hashlib
import os
import subprocess
import sys

import numpy as np
import pandas as pd

PY = sys.executable
PROG = "backtest/researchExplore.py"
ENV = dict(os.environ, PYTHONPATH=os.path.expanduser("~/tw-p17"))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def run(args):
    print("  $ " + " ".join(args), flush=True)
    r = subprocess.run([PY, PROG] + args, env=ENV, cwd=os.path.expanduser("~/tw-p17"), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("⛔ 子程式失敗")
    return r.stdout


def fresh(d):
    if os.path.exists(d):
        import shutil
        shutil.rmtree(d)


def fixture(out, full=False, reuse=False):
    SIG_FILES = ("features.csv", "cands.csv", "cand_stats.csv")
    # ① 不變性
    px = os.path.join(out, "_fx_perturb")
    if not (reuse and os.path.exists(os.path.join(px, "summary.json" if full else "cand_stats.csv"))):
        fresh(px); _run1 = True
    else:
        _run1 = False
    if full:
        _run1 and run(["--perturb", "777", "--out", px, "--procs", os.environ.get("FX_PROCS", "1")])
        files = SIG_FILES + ("seeds.csv", "ranking_171.csv", "clues.csv", "summary.json")
    else:
        _run1 and run(["--perturb", "777", "--reps", "3", "--s0", "20", "--out", px])
        files = SIG_FILES
    ok1 = True
    for f in files:
        a, b = sha(os.path.join(out, f)), sha(os.path.join(px, f))
        print(f"  ①{'✅' if a == b else '⛔'} {f}：真 {a}｜擾動 {b}")
        ok1 &= a == b
    if not full:
        A = pd.read_csv(os.path.join(out, "seeds.csv"), dtype=str)
        B = pd.read_csv(os.path.join(px, "seeds.csv"), dtype=str)
        M = B.merge(A, on=["cell", "seed"], how="left", suffixes=("_p", ""))
        cols = [c for c in A.columns if c not in ("cell", "seed")]
        same = np.all([(M[c] == M[c + "_p"]).to_numpy() for c in cols], axis=0)
        print(f"  ①{'✅' if same.all() else '⛔'} 引擎 {len(B)} 次模擬（每格前 3 顆＋S0 前 20＋W1ref 前 3）：逐欄相同 {int(same.sum())}／{len(B)}（含權益曲線 sha1）")
        ok1 &= bool(same.all()) and len(B) == len(M)
    # ② 鑑別力
    lr, lp = os.path.join(out, "_fx_leak_real"), os.path.join(out, "_fx_leak_pert")
    if not (reuse and os.path.exists(os.path.join(lr, "cands.csv")) and os.path.exists(os.path.join(lp, "cands.csv"))):
        fresh(lr); fresh(lp)
        run(["--leak", "--stage", "sig", "--out", lr])
        run(["--leak", "--perturb", "777", "--stage", "sig", "--out", lp])
    a, b = sha(os.path.join(lr, "cands.csv")), sha(os.path.join(lp, "cands.csv"))
    Fr = pd.read_csv(os.path.join(lr, "features.csv"), dtype=str).fillna(""); Fp = pd.read_csv(os.path.join(lp, "features.csv"), dtype=str).fillna("")
    nF = int((Fr["F05"] != Fp["F05"]).sum())
    Cr = pd.read_csv(os.path.join(lr, "cands.csv"), dtype=str); Cp = pd.read_csv(os.path.join(lp, "cands.csv"), dtype=str)
    diffcells = sorted(c for c in set(Cr["cell"]) if not Cr[Cr["cell"] == c].reset_index(drop=True).equals(Cp[Cp["cell"] == c].reset_index(drop=True)))
    ok2 = a != b and nF > 0
    print(f"  ②{'✅ 抓到' if ok2 else '⛔ 沒抓到'}：前視版 cands 真 {a}｜擾動 {b}；F05 不同 {nF} 列；候選不同的格 {len(diffcells)} 格（例 {diffcells[:4]}）")
    Fm = pd.read_csv(os.path.join(out, "features.csv"), dtype=str).fillna("")   # ⭐ 空值當字串比（NaN != NaN 會假紅）
    dcol = [c for c in Fm.columns if not (Fm[c] == Fr[c]).all()]
    rows = Fm.index[(Fm["F05"] != Fr["F05"])]
    only = set(Fm.loc[rows, "measure_date"]) <= {"2022-12-01"}
    print(f"  ②' 前視開關只動到 F05＠2022-12-01：不同欄 {dcol}、不同列的量測日 {sorted(set(Fm.loc[rows, 'measure_date']))} ⇒ {'✅' if dcol == ['F05'] and only else '⛔'}")
    ok2 &= dcol == ["F05"] and only
    print("fixture：" + ("✅ ①不變 ②抓得到" if ok1 and ok2 else "⛔ 失敗"))
    return ok1 and ok2


def w1():
    sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
    import researchExplore as RE                  # ⭐ 用同一支 run_one；⛔ 不裝 as-of 還原、⛔ 不截日曆（全期 ＝ W1 的條件）
    D, P7, P12, P4F, T = RE.D, RE.P7, RE.P12, RE.P4F, RE.T
    cal = D.load_calendar(); ncal = len(cal)
    panel = P4F.read_panel("backtest/resultsAFC/panel.csv.gz")
    uni = D.load_universe().set_index("stock_id")["market"]
    closes, opens = {}, {}
    for s in sorted(set(panel["stock_id"])) + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        c = st.df["close"].to_numpy(float)
        closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
    sig = sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    trad = T.build(set(sig["sid"]), cal); dl = T.delist_status(trad, cal, official=T.load_official())
    w0, w1_ = P12.win_bounds(cal, "全窗")
    RE._S.update(sigs={"W1": sig}, closes=closes, opens=opens, ncal=ncal, trad=trad, dl=dl, w0=w0, w1=w1_, marks=P12.month_marks(cal, w0, w1_))
    ref = pd.read_csv("backtest/resultsAFC/w1_1000.csv", float_precision="round_trip").set_index("seed")   # ⭐ 預設解析器不是 round-trip（p4_features.read_panel 的坑）
    n_ok = 0; dmax = 0.0
    for r in range(20):
        o = RE.run_one(("W1", 102000 + r))
        same = o["cagr"] == ref.loc[o["seed"], "cagr"] and o["mdd"] == ref.loc[o["seed"], "mdd"]
        n_ok += int(same); dmax = max(dmax, abs(o["cagr"] - ref.loc[o["seed"], "cagr"]), abs(o["mdd"] - ref.loc[o["seed"], "mdd"]))
    print(f"w1：run_one 在全期資料上重現 resultsAFC/w1_1000.csv 前 20 顆 ⇒ 逐位元相同 {n_ok}／20（最大差 {dmax:.1e}）{'✅' if n_ok == 20 else '⛔'}")
    return n_ok == 20


def probe():
    """擾動確實有作用（⛔ 否則 ①的「相同」可能只是擾動沒生效）：每一類檔案抽一個，比對擾動前後
    ⇒ CUT 以後的列要【變了】、CUT 以前（含當天）的列要【一字不差】。"""
    sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
    import researchExplore as RE
    root = RE.H2.H2D
    orig = pd.read_csv
    RE.install_perturb(777, root)
    pert = pd.read_csv
    pd.read_csv = orig
    ok = True
    cases = [("stocks/2330.csv", "date"), ("stocks_inst/2330.csv", "date"), ("stocks_per/2330.csv", "date"),
             ("stocks_margin/2330.csv", "date"), ("adj/2330.csv", "date"), ("mops/revenue_hist/2022-11_twse.csv", "period"),
             ("mops/revenue_hist/2023-01_twse.csv", "period"), ("meta/calendar_twse.csv", "date"),
             ("meta/stocks.csv", "last_seen"), ("meta/delisted.csv", "delist_date")]
    for rel, key in cases:
        p = os.path.join(root, rel)
        a = orig(p, dtype=str); b = pert(p, dtype=str)
        cut = "2022-12" if key == "period" else "2022-12-30"
        post = (lambda s: s >= cut) if key == "period" else (lambda s: s.str[:10] > cut)
        pa, pb = a[~post(a[key].astype(str))], b[~post(b[key].astype(str))]
        same_pre = pa.reset_index(drop=True).equals(pb.reset_index(drop=True)) if key not in ("last_seen", "delist_date") else \
            a.loc[~post(a[key].astype(str))].equals(b.loc[~post(a[key].astype(str))])
        qa = a[post(a[key].astype(str))]
        if key in ("last_seen", "delist_date"):
            changed = int((a.loc[qa.index, key] != b.loc[qa.index, key]).sum()); n_post = len(qa)
        else:
            qb = b[post(b[key].astype(str))]
            n_post = len(qa)
            if len(qb) != len(qa):
                changed = n_post                       # 列被亂刪
            else:
                num = [c for c in a.columns if c not in ("date", "stock_id", "name", "market", "period", "產業別")]
                changed = int((qa[num].reset_index(drop=True) != qb[num].reset_index(drop=True)).any(axis=1).sum())
        good = same_pre and (n_post == 0 or changed > 0)
        ok &= good
        print(f"  probe {'✅' if good else '⛔'} {rel:<38} CUT 前一字不差 {same_pre}｜CUT 後 {n_post} 列、變動 {changed}（列數 {len(a)}→{len(b)}）")
    print("probe：" + ("✅ 擾動只動 CUT 以後、而且每類都動到了" if ok else "⛔"))
    return ok


def elig(out):
    F = pd.read_csv(os.path.join(out, "features.csv"), dtype={"sid": str})
    P = pd.read_csv("backtest/resultsAFC/panel.csv.gz", dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "eligible"])
    P = P[(P["measure_date"] >= "2017-01-01") & (P["measure_date"] <= "2022-12-30") & P["eligible"].astype(bool)]
    a = set(zip(F["measure_date"], F["sid"])); b = set(zip(P["measure_date"].str[:10], P["stock_id"]))
    print(f"elig：截斷重建 {len(a):,}｜AFC 面板 {len(b):,}｜只在前者 {len(a - b)}｜只在後者 {len(b - a)} ⇒ {'✅ 相同' if a == b else '⚠ 不同'}")
    return a == b


if __name__ == "__main__":
    os.chdir(os.path.expanduser("~/tw-p17"))
    what = sys.argv[1] if len(sys.argv) > 1 else "fixture"
    out = "backtest/resultsExplore"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    ok = {"fixture": lambda: fixture(out, "--full" in sys.argv, "--reuse" in sys.argv), "w1": w1, "elig": lambda: elig(out), "probe": probe}[what]()
    sys.exit(0 if ok else 1)

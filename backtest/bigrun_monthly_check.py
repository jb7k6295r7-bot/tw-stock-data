# -*- coding: utf-8 -*-
"""大漲觀察月報（bigrun_monthly）驗證——回測線開發子代理，2026-10-22。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.bigrun_monthly_check --csv <月報 csv> --qcsv <季加報 csv> [--parts due,cells,look,g,auto]
部分：
  due   到期判斷 fixture（各月 11／12／13 日、季期限隔天、已產不重產、跨年、首份之前、週末期限）＋ auto 未到期 exit 0（輕）
  cells 抽 20 格（月報 14、季加報 6；種子固定）從原始檔另寫一條路重算：月營收 git show 截止版本的每日版／revenue_hist 原檔、
        價格用 adj factor 欄自己連乘（⛔ 不用 data.load_stock／cum_factor）、財報讀 fs_xbrl 原檔自己差分；⛔ 不 import bigrun_monthly 的計算函式
  look  不前視：截止版本 commit 時間 ≤ 資料日 23:59:59 且在 sha 的 first-parent 鏈上；A～F 每檔最新期月營收列「第一次出現在 main」的 commit 時間 ≤ 資料日；
        季加報各檔所用季的上傳時戳 ≤ 資料日（filing_dates 原檔重查）
  g     G 表以 10/20 資料（sha 5cb00a60c1、資料日 2026-10-20、--g-rev hist）重產 ⇒ 與 10/20 快照 csv 逐字比對；另報公告當時口徑（pit）與快照差幾格（資訊）
  auto  auto 實跑一次（暫存 state／輸出夾、首份鍵暫改 2026-10）⇒ 產檔、寫 state；再跑一次 ⇒ 「未到期」不重產；
        名單 md 第十二節（接檔尾、其他段不變、LINE 摘要格式、冪等、同資料日重產補回、別的資料日移除）；put_daily 節在中間
  sp    前瞻小部位 fixture：起點前不記、補記起點（鎖漲停／無成交買不到）、凍結不重算、轉強加 2 份只一次、期限當天不賣、
        12 個月未轉強賣出（無持股、鎖跌停順延）、期限後判定不記、累計報酬算式
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
TZ = "Asia/Taipei"
G_SHA = "5cb00a60c1fcdc6f2a388a9fbcb50a8812e32584"
G_SNAP = os.path.join(REPO, "backtest", "resultsLongPool", "pool169_20261020.csv")
RES = []


def rec(part, item, ok, detail=""):
    RES.append((part, item, bool(ok), detail))
    print(f"[{part}] {'✔' if ok else '✖'} {item}｜{detail}", flush=True)


def git(*a, check=True):
    r = subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout if r.returncode == 0 else None


# ═════════════ due ═════════════
def part_due():
    from backtest import bigrun_monthly as BM
    T = pd.Timestamp
    S0 = {"月報": {}, "季加報": {}}

    def st(m=(), q=()):
        return {"月報": {k: 1 for k in m}, "季加報": {k: 1 for k in q}}
    cases = [
        ("首份之前 2026-10-22（10 月月報、2026Q2 季加報都不產）", T("2026-10-22"), S0, []),
        ("2026-11-11（11 日）", T("2026-11-11"), S0, []),
        ("2026-11-12（12 日）", T("2026-11-12"), S0, [("月報", "2026-11")]),
        ("2026-11-13（13 日，未產）", T("2026-11-13"), S0, [("月報", "2026-11")]),
        ("2026-11-13（13 日，12 日已產 ⇒ 不重產）", T("2026-11-13"), st(["2026-11"]), []),
        ("2026-11-14（季期限當天）", T("2026-11-14"), st(["2026-11"]), []),
        ("2026-11-15（季期限隔天）", T("2026-11-15"), st(["2026-11"]), [("季加報", "2026Q3")]),
        ("2026-11-16（週日 11-15 無資料 ⇒ 週一資料日到期）", T("2026-11-16"), st(["2026-11"]), [("季加報", "2026Q3")]),
        ("2026-11-17（季加報已產 ⇒ 不重產）", T("2026-11-17"), st(["2026-11"], ["2026Q3"]), []),
        ("2026-11-16（月報、季加報都沒產 ⇒ 兩份）", T("2026-11-16"), S0, [("月報", "2026-11"), ("季加報", "2026Q3")]),
        ("2026-12-11", T("2026-12-11"), st(["2026-11"], ["2026Q3"]), []),
        ("2026-12-14（12-12 週六 ⇒ 週一）", T("2026-12-14"), st(["2026-11"], ["2026Q3"]), [("月報", "2026-12")]),
        ("跨年 2027-01-11", T("2027-01-11"), st(["2026-11", "2026-12"], ["2026Q3"]), []),
        ("跨年 2027-01-12", T("2027-01-12"), st(["2026-11", "2026-12"], ["2026Q3"]), [("月報", "2027-01")]),
        ("跨年 2027-01-13（已產）", T("2027-01-13"), st(["2026-11", "2026-12", "2027-01"], ["2026Q3"]), []),
        ("2027-03-31（Q4 期限當天）", T("2027-03-31"), st(["2027-03"], ["2026Q3"]), []),
        ("2027-04-01（Q4 期限隔天 ⇒ 2026Q4）", T("2027-04-01"), st(["2027-03"], ["2026Q3"]), [("季加報", "2026Q4")]),
        ("2027-05-15（Q1 期限當天）", T("2027-05-15"), st(["2027-05"], ["2026Q3", "2026Q4"]), []),
        ("2027-05-16（Q1 期限隔天）", T("2027-05-16"), st(["2027-05"], ["2026Q3", "2026Q4"]), [("季加報", "2027Q1")]),
        ("2027-08-15（Q2 期限隔天）", T("2027-08-15"), st(["2027-08"], ["2027Q1"]), [("季加報", "2027Q2")]),
        ("2027-11-15（Q3 期限隔天，月報已產）", T("2027-11-15"), st(["2027-11"], ["2027Q2"]), [("季加報", "2027Q3")]),
    ]
    for name, d, s, exp in cases:
        got = BM.due(d, s)
        rec("due", name, got == exp, f"得 {got}｜應 {exp}")
    for d, exp in (("2027-01-05", "2026Q3"), ("2026-10-22", "2026Q2"), ("2027-04-01", "2026Q4"), ("2027-03-31", "2026Q3")):
        rec("due", f"quarter_key({d})", BM.quarter_key(T(d)) == exp, f"得 {BM.quarter_key(T(d))}｜應 {exp}")
    # 月營收期別與可用日規則（12 日產時 10 月期「依規則尚未可用、以已公布值描述」）
    Lf = pd.DataFrame({"period": ["2026-08", "2026-09", "2026-10"]})
    for d, expP, expAv in (("2026-11-10", "2026-09", True), ("2026-11-12", "2026-10", False), ("2026-11-16", "2026-10", True),
                           ("2026-01-12", None, None)):
        if expP is None:
            rec("due", "可用日規則 2025-12 期 ＝ 2026-01-10 後（舊規則 10 日）", str(BM.rev_avail("2025-12").date()) == "2026-01-10", str(BM.rev_avail("2025-12").date()))
            continue
        P = BM.report_period(Lf, T(d)); av = bool(BM.rev_avail(P) < T(d))
        rec("due", f"資料日 {d} ⇒ 月報期 {expP}、依規則{'已' if expAv else '尚未'}可用", P == expP and av == expAv, f"期 {P}｜可用 {av}")
    # auto 未到期 ⇒ exit 0、不產（實際命令列）
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "state.json")
        r = subprocess.run([sys.executable, "-m", "backtest.bigrun_monthly", "--sha", G_SHA, "--kind", "auto", "--state", sp, "--out", os.path.join(td, "x.md")],
                           cwd=REPO, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": REPO})
        rec("due", "auto（資料日 2026-10-20）⇒ 未到期、exit 0、不寫 state、不產檔",
            r.returncode == 0 and "未到期" in r.stdout and not os.path.exists(sp) and not os.path.exists(os.path.join(td, "x.md")), r.stdout.strip()[-200:])


# ═════════════ cells ═════════════
def roc(p):
    return str((int(p[:4]) - 1911) * 100 + int(p[5:]))


class Rev:
    """截止版本 AC 的原始檔：每日版 revenue/<期>.csv（期別欄、資料年月相符）優先、否則 revenue_hist <期>_{twse,tpex,esb}.csv（後讀者覆蓋：twse 最後）。"""
    def __init__(self, ac):
        self.ac = ac; self.cache = {}

    def row(self, sid, p):
        if p not in self.cache:
            out = {}
            for mk in ("esb", "tpex", "twse"):
                t = git("show", f"{self.ac}:data/mops/revenue_hist/{p}_{mk}.csv", check=False)
                if t:
                    x = pd.read_csv(io.StringIO(t), dtype=str)
                    for s, a, b, c in zip(x["stock_id"], pd.to_numeric(x["當月營收"], errors="coerce"), pd.to_numeric(x["上月營收"], errors="coerce"),
                                          pd.to_numeric(x["去年當月營收"], errors="coerce")):
                        out[s] = (a, b, c)
            t = git("show", f"{self.ac}:data/mops/revenue/{p}.csv", check=False)
            if t:
                x = pd.read_csv(io.StringIO(t), dtype=str)
                for _, r in x.iterrows():
                    if str(r["資料年月"]).strip() == roc(p) and str(r.get("period", p)) == p:
                        out[r["stock_id"]] = (float(r["營業收入-當月營收"]), float(r["營業收入-上月營收"]), float(r["營業收入-去年當月營收"]))
            self.cache[p] = out
        return self.cache[p].get(sid, (np.nan, np.nan, np.nan))


def shift(p, k):
    return str(pd.Period(p, "M") + k)


def rev_cell(R, sid, p, f):
    def yoy(q):
        a, _, c = R.row(sid, q)
        return a / c - 1 if c > 0 else np.nan
    a, b, c = R.row(sid, p)
    if f == "rev_k":
        return a
    if f == "yoy":
        return yoy(p)
    if f == "mom":
        return a / b - 1 if b > 0 else np.nan
    y3 = [yoy(shift(p, -i)) for i in range(3)]; y12 = [yoy(shift(p, -i)) for i in range(12)]
    if f == "yoy3":
        return np.mean(y3) if np.all(np.isfinite(y3)) else np.nan
    if f == "accel":
        return np.mean(y3) - np.mean(y12) if np.all(np.isfinite(y12)) else np.nan
    if f == "hi24":
        h = [R.row(sid, shift(p, -i))[0] for i in range(1, 25)]
        return bool(a >= max(h)) if np.all(np.isfinite(h)) else np.nan


def adj_close(H, sid):
    x = pd.read_csv(os.path.join(H, "stocks", f"{sid}.csv"), usecols=["date", "close"])
    x["date"] = pd.to_datetime(x["date"]); x = x.drop_duplicates("date").set_index("date").sort_index()
    x = x[x["close"] > 0]
    F = np.ones(len(x)); p = os.path.join(H, "adj", f"{sid}.csv")
    if os.path.exists(p):
        a = pd.read_csv(p); a["date"] = pd.to_datetime(a["date"])
        for d, f in zip(a["date"], a["factor"].astype(float)):
            F[x.index < d] *= f
    x["ac"] = x["close"] * F
    return x


def px_cell(H, sid, asof, f):
    x = adj_close(H, sid)
    if sid == "3718":
        o = adj_close(H, "5371"); x = pd.concat([o[o.index < x.index.min()], x])
    x = x[x.index <= asof]
    if f == "close":
        return float(x["close"].iloc[-1])
    c = x["ac"]
    if f == "pct_from_high":
        return c.iloc[-1] / c[c.index >= asof - pd.Timedelta(days=364)].max() - 1
    if f == "ret_1y":
        b = c[c.index <= asof - pd.Timedelta(days=365)]
        return c.iloc[-1] / b.iloc[-1] - 1 if len(b) else np.nan


_XB = {}


def fs_cell(ac, sid, q, f, asof):
    s = "5371" if sid == "3718" else sid
    def x_of(y):
        if (ac, y) not in _XB:
            _XB[(ac, y)] = pd.read_csv(io.StringIO(git("show", f"{ac}:data/meta/fs_xbrl/fs_xbrl_{y}.csv")), dtype={"stock_id": str})
        x = _XB[(ac, y)]
        return x[x["stock_id"] == s].sort_values("report")         # cr 在 ir 前
    def v(qq, c):
        x = x_of(qq[:4]); x = x[x["period"] == qq]
        return float(pd.to_numeric(x[c], errors="coerce").iloc[0]) if len(x) else np.nan
    def prevq(qq):
        y, n = int(qq[:4]), int(qq[-1])
        return f"{y}Q{n - 1}" if n > 1 else None
    def sq(qq, c):
        pq = prevq(qq)
        return v(qq, c) if pq is None else v(qq, c) - v(pq, c)
    ly = f"{int(q[:4]) - 1}Q{q[-1]}"
    def cl(qq):
        a, b = v(qq, "contract_liabilities_current"), v(qq, "contract_liabilities_noncurrent")
        return np.nan if np.isnan(a) and np.isnan(b) else np.nansum([a, b])
    def days(qq):
        cg = sq(qq, "cost_of_sales_ytd"); iv = v(qq, "inventories")
        return iv / cg * 91.25 if cg > 0 else np.nan
    def gm(qq):
        rv = sq(qq, "revenue_ytd")
        return sq(qq, "gross_profit_ytd") / rv if rv > 0 else np.nan
    if f == "cl":
        return cl(q)
    if f == "cl_yoy":
        return cl(q) / cl(ly) - 1 if cl(ly) > 0 else np.nan
    if f == "inv_days_chg":
        return days(q) - days(ly)
    if f == "gm_chg":
        return gm(q) - gm(ly)


def same(a, b):
    if isinstance(a, (bool, np.bool_)) or isinstance(b, (bool, np.bool_)) or b in ("True", "False"):
        return str(bool(a)) == str(b) if not (isinstance(a, float) and np.isnan(a)) else pd.isna(b)
    a = float(a) if a is not None else np.nan; b = float(b) if not pd.isna(b) else np.nan
    return (np.isnan(a) and np.isnan(b)) or (np.isfinite(a) and np.isfinite(b) and abs(a - b) <= 2e-5 * max(1, abs(b)))


def part_cells(csv, qcsv):
    meta = json.load(open(csv.replace(".csv", "_meta.json"), encoding="utf-8"))
    asof = pd.Timestamp(meta["資料日"]); ac = meta["截止版本"]; H = os.path.expanduser(f"~/h2data/{meta['sha']}/data")
    M = pd.read_csv(csv, dtype={"stock_id": str, "rev_period": str})
    rng = np.random.default_rng(20261022)
    pairs = [(s, f) for s in M["stock_id"] for f in ("rev_k", "yoy", "mom", "yoy3", "accel", "hi24", "close", "pct_from_high", "ret_1y")]
    pick = [pairs[i] for i in rng.choice(len(pairs), 14, replace=False)]
    R = Rev(ac)
    for sid, f in pick:
        r = M[M["stock_id"] == sid].iloc[0]
        mine = rev_cell(R, sid, r["rev_period"], f) if f in ("rev_k", "yoy", "mom", "yoy3", "accel", "hi24") else px_cell(H, sid, asof, f)
        rec("cells", f"月報 {sid} {f}（{r['rev_period']}）", same(mine, r[f]), f"重算 {mine}｜表 {r[f]}")
    if qcsv:
        qm = json.load(open(qcsv.replace(".csv", "_meta.json"), encoding="utf-8"))
        Q = pd.read_csv(qcsv, dtype={"stock_id": str})
        qp = [(s, f) for s, q, src in zip(Q["stock_id"], Q["fs_q"], Q["pl_src"]) if isinstance(q, str) and src == "fs_xbrl"
              for f in ("cl", "cl_yoy", "inv_days_chg", "gm_chg")]          # 只抽全用 fs_xbrl 的列（本檢查走 fs_xbrl 原檔）
        if len(qp) < 6:
            rec("cells", "季加報可抽格（全用 fs_xbrl 的列）≥ 6", False, f"只有 {len(qp)} 格")
        for i in rng.choice(len(qp), min(6, len(qp)), replace=False):
            sid, f = qp[i]; r = Q[Q["stock_id"] == sid].iloc[0]
            mine = fs_cell(qm["截止版本"], sid, r["fs_q"], f, pd.Timestamp(qm["資料日"]))
            rec("cells", f"季加報 {sid} {f}（{r['fs_q']}）", same(mine, r[f]), f"重算 {mine}｜表 {r[f]}")


# ═════════════ look ═════════════
BLOB: dict = {}


def part_look(csv, qcsv):
    meta = json.load(open(csv.replace(".csv", "_meta.json"), encoding="utf-8"))
    asof = pd.Timestamp(meta["資料日"]); cut = pd.Timestamp(f"{asof.date()} 23:59:59", tz=TZ); ac = meta["截止版本"]; sha = meta["sha"]
    t_ac = pd.Timestamp(git("show", "-s", "--format=%cI", ac).strip()).tz_convert(TZ)
    fp = set(git("rev-list", "--first-parent", sha).split())
    rec("look", "截止版本 commit 時間 ≤ 資料日 23:59:59、且在 sha first-parent 鏈上", t_ac <= cut and ac in fp, f"{ac[:10]} {t_ac}")
    M = pd.read_csv(csv, dtype={"stock_id": str, "rev_period": str})
    worst = None; bad = []
    first_seen = {}
    for sid, p in zip(M["stock_id"], M["rev_period"]):
        if not isinstance(p, str):
            continue
        paths = [f"data/mops/revenue/{p}.csv", f"data/mops/revenue_hist/{p}_twse.csv", f"data/mops/revenue_hist/{p}_tpex.csv"]
        best = None
        for path in paths:
            key = path
            if key not in first_seen:
                L = git("log", "--first-parent", "--reverse", "--format=%H %cI", ac, "--", path).split("\n")
                first_seen[key] = [(h, pd.Timestamp(t).tz_convert(TZ)) for h, t in (x.split() for x in L if x.strip())]
            for h, t in first_seen[key]:
                if (h, path) not in BLOB:
                    BLOB[(h, path)] = {line.split(",", 1)[0] for line in (git("show", f"{h}:{path}", check=False) or "").splitlines()}
                if sid in BLOB[(h, path)]:
                    best = t if best is None else min(best, t); break
        if best is None or best > cut:
            bad.append((sid, p, best))
        worst = best if worst is None or (best is not None and best > worst) else worst
    rec("look", f"A～F {len(M)} 檔最新期月營收列第一次進 main ≤ 資料日 23:59:59", not bad, f"最晚一檔 {worst}；違反 {bad}")
    if qcsv:
        qm = json.load(open(qcsv.replace(".csv", "_meta.json"), encoding="utf-8"))
        Q = pd.read_csv(qcsv, dtype={"stock_id": str})
        fd = pd.read_csv(io.StringIO(git("show", f"{qm['截止版本']}:data/meta/filing_dates.csv")), dtype=str)
        fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce")
        lim = pd.Timestamp(qm["資料日"]) + pd.Timedelta(days=1); bad = []; mx = None
        for sid, q in zip(Q["stock_id"], Q["fs_q"]):
            if not isinstance(q, str):
                continue
            s = "5371" if sid == "3718" else sid
            x = fd[(fd["stock_id"] == s) & (fd["year"] == q[:4]) & (fd["season"] == q[-1])].dropna(subset=["d"])
            d = x.loc[x["doc_code"] == "AI1", "d"].min() if (x["doc_code"] == "AI1").any() else x["d"].min()
            if not (pd.notna(d) and d < lim):
                bad.append((sid, q, d))
            mx = d if mx is None or (pd.notna(d) and d > mx) else mx
        rec("look", f"季加報 {Q['fs_q'].notna().sum()} 檔所用季上傳時戳 ≤ 資料日", not bad, f"最晚 {mx}；違反 {bad}")


# ═════════════ g ═════════════
def part_g():
    from backtest import bigrun_monthly as BM
    from backtest import data as D
    snap = open(G_SNAP, encoding="utf-8-sig").read()
    H = BM.ensure_snapshot(G_SHA); D.DATA = H
    cal = D.load_calendar(); asof = cal[-1]
    rec("g", "5cb00a60c1 日曆尾 ＝ 2026-10-20", str(asof.date()) == "2026-10-20", str(asof.date()))
    FD = BM.ensure_fund(G_SHA)
    G = BM.build_g(asof, cal, H, FD, 3, None)
    mine = G["df"].to_csv(index=False, float_format="%.6g", lineterminator="\n")
    a = pd.read_csv(io.StringIO(snap), dtype=str, keep_default_na=False); b = pd.read_csv(io.StringIO(mine), dtype=str, keep_default_na=False)
    ncell = int((a.values != b.values).sum()) if a.shape == b.shape and list(a.columns) == list(b.columns) else -1
    rec("g", "G 表（hist 口徑）以 10/20 資料重產 ＝ 10/20 快照 csv 逐字相符", mine.replace("\r\n", "\n") == snap.replace("\r\n", "\n"),
        f"形狀 {b.shape} vs {a.shape}；欄序同 {list(a.columns) == list(b.columns)}；不同格 {ncell}")
    # 資訊：公告當時口徑（pit）與快照差幾格
    ac, _ = BM.asof_commit(G_SHA, asof)
    L, _ = BM.load_rev_pit(BM.ensure_rev(ac))
    G2 = BM.build_g(asof, cal, H, FD, 3, L)
    c = pd.read_csv(io.StringIO(G2["df"].to_csv(index=False, float_format="%.6g")), dtype=str, keep_default_na=False)
    diff = [(a.at[i, "stock_id"], col) for i in range(len(a)) for col in a.columns if a.at[i, col] != c.at[i, col]]
    rec("g", "（資訊）G 表 pit 口徑 vs 快照", True, f"不同 {len(diff)} 格：{diff[:12]}")


# ═════════════ auto ═════════════
def part_auto():
    from backtest import bigrun_monthly as BM
    import argparse as ap_
    import re
    import shutil
    orig_daily = os.path.join(REPO, "backtest", "resultsDaily", "daily_2026-10-20.md")
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "state.json"); BM.FWD = os.path.join(td, "fwd"); BM.FIRST = {"月報": "2026-10", "季加報": "2026Q3"}
        dmd = os.path.join(td, "daily_2026-10-20.md"); shutil.copyfile(orig_daily, dmd)
        orig = open(orig_daily, encoding="utf-8").read()
        a = ap_.Namespace(asof=None, sha=G_SHA, out=os.path.join(td, "out", "x.md"), kind="auto", procs=3, g_rev="pit", state=sp, md=dmd)
        rc = BM.run(a)
        d1 = open(dmd, encoding="utf-8").read()
        k = d1.find("\n## 十二、大漲觀察月報（2026-09 營收）\n")
        sec = d1[k + 1:] if k >= 0 else ""
        rec("auto", "名單 md 接檔尾第十二節「## 十二、大漲觀察月報（2026-09 營收）」、其他段逐字不變",
            k >= 0 and d1[:k].rstrip("\n") == orig.rstrip("\n") and sec.count("\n## ") == 0, f"節長 {len(sec)} 字")
        sl = sec.split("\n")
        i = next((j for j, x in enumerate(sl) if x.startswith("- 【LINE】")), None)
        ln = []
        if i is not None:
            ln = [sl[i]] + [x for x in __import__("itertools").takewhile(lambda x: x.startswith("  ") and not x.startswith("  - "), sl[i + 1:])]
        ok = (i is not None and sl[i] == "- 【LINE】⭐ 大漲觀察（9 月營收）：" and 2 <= len(ln) <= 4
              and all(re.match(r"^  (轉強：|警訊：|重點：|本月無變化$)", x) for x in ln[1:]) and sum(x.startswith("- 【LINE】") for x in sl) == 1)
        rec("auto", "LINE 摘要格式（首行、續行兩空白縮排不以「- 」開頭、≤ 4 行、只一則）", ok, " ／ ".join(ln)[:400])
        bad = [w for w in ("買", "賣", "推薦", "建議") if any(w in x for x in ln)]
        rec("auto", "LINE 摘要不含買／賣／推薦／建議字樣", not bad, str(bad))
        st = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
        fs = sorted(os.listdir(BM.FWD)) if os.path.isdir(BM.FWD) else []
        rec("auto", "首跑（首份鍵暫改 2026-10，資料日 2026-10-20）⇒ 產月報、寫 state、--out 有副本",
            rc == 0 and "2026-10" in st.get("月報", {}) and "2026-10_月報.md" in fs and os.path.exists(a.out) and "2026-10_月報_G169.csv" in fs,
            f"state {st}；fwd {fs}")
        rec("auto", "季加報 2026Q2 ＜ 首份 2026Q3 ⇒ 不產", "季加報" not in st or not st["季加報"], str(st.get("季加報")))
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc2 = BM.run(a)
        rec("auto", "再跑一次 ⇒ 已產不重產（未到期、exit 0）", rc2 == 0 and "未到期" in buf.getvalue(), buf.getvalue().strip()[-150:])
        rec("auto", "再跑一次 ⇒ 名單 md 不變（冪等）", open(dmd, encoding="utf-8").read() == d1, "")
        shutil.copyfile(orig_daily, dmd)                       # 模擬同資料日名單被重產（新 sha）
        with contextlib.redirect_stdout(io.StringIO()):
            BM.run(a)
        rec("auto", "同資料日名單重產 ⇒ 第十二節從存檔補回、與首跑逐字相同", open(dmd, encoding="utf-8").read() == d1, "")
        st = json.load(open(sp, encoding="utf-8")); st["月報"]["2026-10"]["資料日"] = "2026-10-19"
        json.dump(st, open(sp, "w", encoding="utf-8"), ensure_ascii=False)   # 模擬「產出是前一個資料日」
        with contextlib.redirect_stdout(io.StringIO()):
            BM.run(a)
        rec("auto", "不是產出那個資料日 ⇒ 移除第十二節、名單回到原樣", open(dmd, encoding="utf-8").read().rstrip("\n") == orig.rstrip("\n"), "")
    # put_daily：節在中間 ⇒ 抽出、接檔尾；空 ⇒ 移除
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "d.md")
        open(p, "w", encoding="utf-8").write("# t\n\n## 一、a\n- x\n\n## 十二、大漲觀察月報（2026-09 營收）\n- old\n\n## 十三、b\n- y\n")
        BM.put_daily(p, [["## 十二、大漲觀察月報（2026-10 營收）", "", "- new"]])
        t1 = open(p, encoding="utf-8").read()
        BM.put_daily(p, [["## 十二、大漲觀察月報（2026-10 營收）", "", "- new"]])
        rec("auto", "put_daily：舊節（在中間）整節移除、新節接檔尾、重放冪等",
            t1 == "# t\n\n## 一、a\n- x\n\n## 十三、b\n- y\n\n## 十二、大漲觀察月報（2026-10 營收）\n\n- new\n" and open(p, encoding="utf-8").read() == t1, repr(t1[-80:]))


# ═════════════ sp（前瞻小部位 fixture） ═════════════
def part_sp():
    from backtest import bigrun_monthly as BM
    T = pd.Timestamp
    cal = pd.bdate_range("2026-10-19", "2027-11-30")
    nm = {s: f"名{s}" for s in BM.SP_CODES}

    class FakePx:
        def __init__(self, over=None):
            self.over = over or {}

        def bar(self, sid, d):
            k = (sid, str(d.date()))
            if k in self.over:
                return self.over[k]
            return {"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "pc": 100.0}
    def upd(rows, asof, px, J=()):
        return BM.sp_update(rows, cal, T(asof), px, list(J), nm, "now", "f" * 40)
    rec("sp", "起點前（2026-10-21）⇒ 不記", upd([], "2026-10-21", FakePx()) == [], "")
    lock = {("1312", "2026-10-22"): {"o": 110.0, "h": 110.0, "l": 110.0, "c": 110.0, "pc": 100.0},
            ("1305", "2026-10-22"): None}
    r1 = upd([], "2026-10-22", FakePx(lock))
    ev = {(r["stock_id"], r["event"]): r for r in r1}
    rec("sp", "補記起點：10-22 開盤各 1 份、1312 開盤鎖漲停買不到、1305 無成交買不到、註明補記",
        len(r1) == 4 and ev[("1503", "起點買進")]["units"] == "1" and ev[("1503", "起點買進")]["price_raw"] == "100.0"
        and ev[("1312", "起點買進")]["status"] == "買不到（開盤鎖漲停）" and ev[("1312", "起點買進")]["units"] == "0"
        and ev[("1305", "起點買進")]["status"] == "買不到（當日無成交）" and all("補記" in r["note"] for r in r1),
        "；".join(f"{r['stock_id']} {r['status']} {r['units']}" for r in r1))
    rows = list(r1)
    snap = [dict(r) for r in rows]
    r2 = upd(rows, "2026-10-23", FakePx({("1503", "2026-10-22"): {"o": 999.0, "h": 999.0, "l": 999.0, "c": 999.0, "pc": 999.0}}))
    rec("sp", "凍結不重算：隔天價格換掉 ⇒ 不新增、舊列不變", r2 == [] and rows == snap, "")
    J1 = [("2026-11", T("2026-11-12"), {"1503": (True, "x"), "1513": (False, "x"), "1305": (False, "x"), "1312": (False, "x")})]
    r3 = upd(rows, "2026-11-12", FakePx(), J1); rows += r3
    rec("sp", "月報 2026-11 判定 4 列；隔日資料還沒到 ⇒ 還不加碼",
        len(r3) == 4 and all(r["event"] == "月報判定" for r in r3) and sum(r["judge"] == "轉強" for r in r3) == 1, str([(r["stock_id"], r["judge"]) for r in r3]))
    r4 = upd(rows, "2026-11-13", FakePx({("1503", "2026-11-13"): {"o": 120.0, "h": 125.0, "l": 119.0, "c": 124.0, "pc": 118.0}})); rows += r4
    rec("sp", "轉強 ⇒ 月報隔一交易日（11-13）開盤加 2 份", len(r4) == 1 and r4[0]["event"] == "轉強加碼" and r4[0]["units"] == "2"
        and r4[0]["trade_date"] == "2026-11-13" and r4[0]["price_raw"] == "120.0", str(r4))
    J2 = [("2026-12", T("2026-12-14"), {"1503": (True, "x"), "1513": (True, "x"), "1305": (False, "x"), "1312": (False, "x")})]
    r5 = upd(rows, "2026-12-15", FakePx(), J2); rows += r5
    rec("sp", "轉強加 2 份只一次：1503 再轉強 ⇒ 不再判、不再加；1513 新轉強 ⇒ 判定＋12-15 加 2 份",
        sum(r["stock_id"] == "1503" for r in r5) == 0 and [(r["stock_id"], r["event"]) for r in r5 if r["stock_id"] == "1513"] == [("1513", "月報判定"), ("1513", "轉強加碼")]
        and sum(r["stock_id"] == "1503" and r["event"] == "轉強加碼" for r in rows) == 1, str([(r["stock_id"], r["event"], r["units"]) for r in r5]))
    r6 = upd(rows, "2027-10-22", FakePx()); rows += r6
    rec("sp", "期限當天（2027-10-22）⇒ 還不賣", r6 == [], str(r6))
    dn = {("1312", "2027-10-25"): {"o": 90.0, "h": 90.0, "l": 90.0, "c": 90.0, "pc": 100.0}}
    r7 = upd(rows, "2027-10-26", FakePx(dn)); rows += r7
    e7 = {r["stock_id"]: r for r in r7}
    rec("sp", "12 個月未轉強 ⇒ 期限隔一交易日開盤賣出記未確認（1305 起點買不到 ⇒ 無持股；1312 起點買不到 ⇒ 無持股）；已確認者不賣",
        set(e7) == {"1305", "1312"} and all(r["event"] == "到期賣出" for r in r7) and e7["1305"]["status"] == "未確認（無持股）", str([(r["stock_id"], r["status"], r["trade_date"]) for r in r7]))
    # 有持股者的到期賣出（含鎖跌停順延）：另起一份 1305、1312 都有起點持股的紀錄
    base = upd([], "2026-10-22", FakePx())
    r8 = upd(base, "2027-10-26", FakePx(dn))
    e8 = {r["stock_id"]: r for r in r8}
    rec("sp", "有持股未轉強 ⇒ 2027-10-25 開盤賣 −1 份；1312 開盤鎖跌停 ⇒ 順延 10-26",
        e8["1305"]["units"] == "-1" and e8["1305"]["trade_date"] == "2027-10-25" and e8["1305"]["status"] == "未確認賣出"
        and e8["1312"]["trade_date"] == "2027-10-26" and "順延" in e8["1312"]["note"] and "1503" in e8, str([(r["stock_id"], r["trade_date"], r["units"]) for r in r8]))
    J3 = [("2027-11", T("2027-11-12"), {"1305": (True, "x"), "1312": (True, "x"), "1503": (True, "x"), "1513": (True, "x")})]
    r9 = upd(base + r8, "2027-11-12", FakePx(), J3)
    rec("sp", "期限後的月報判定不記", r9 == [], str(r9))
    # 累計報酬（還原 ＝ 未還原的假資料）：1503 起點 100、加碼 120×2，資料日收 130 ⇒ (1×(1.3−1) ＋ 2×(130/120−1)) ÷ 3 − 0.585%
    idx = pd.bdate_range("2026-10-22", "2026-11-20")
    def adj(sid):
        d = pd.DataFrame({"open": 100.0, "close": 100.0}, index=idx)
        if sid == "1503":
            d.loc[T("2026-11-13"), "open"] = 120.0; d["close"] = 130.0
        return d
    val, tot = BM.sp_value([r for r in rows if r["stock_id"] == "1503"], T("2026-11-20"), adj)
    exp = (0.3 + 2 * (130 / 120 - 1)) / 3 - 0.00585
    rec("sp", "累計報酬照規則（等額份數、每份扣 0.585%）", abs(val["1503"][1] - exp) < 1e-12 and val["1503"][0] == 3, f"{val['1503']} vs {exp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv"); ap.add_argument("--qcsv"); ap.add_argument("--parts", default="due,cells,look,g")
    a = ap.parse_args()
    parts = a.parts.split(",")
    if "due" in parts:
        part_due()
    if "cells" in parts:
        part_cells(a.csv, a.qcsv)
    if "look" in parts:
        part_look(a.csv, a.qcsv)
    if "g" in parts:
        part_g()
    if "auto" in parts:
        part_auto()
    if "sp" in parts:
        part_sp()
    n = len(RES); ok = sum(r[2] for r in RES)
    print(f"\n驗證 {n} 項：通過 {ok}、不符 {n - ok}")
    for r in RES:
        if not r[2]:
            print("✖", r)
    sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()

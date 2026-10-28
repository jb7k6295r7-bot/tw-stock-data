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
  sp    前瞻小部位 seq3 fixture：起點前不記、補記起點（鎖漲停／無成交買不到）、國喬標記、凍結不重算、轉強加 2 份只一次、
        第 12 份月報未轉強賣出（鎖跌停順延）、第 12 份當期未公布 ⇒ 第 13 份補判並順延、期中補判、放棄後不再判、照規則累計、使用者實際欄讀入與報酬
  sp3   seq8：8 檔、新候選 10/26 晚（前一個日曆日）只出一晚、進場時已轉強標記、250／625 日提醒附描述、新需求型燈2 加碼與放棄、報價提醒（進場後發布才推、同段一次、實資料讀得到）
  sp2   台股 seq547 讀法核對：①加碼看每期判定本身（不套 LINE「上期沒轉強才列」）②2026-11 鍵起判（2026-10 鍵不判）
        ③首次創 24 月新高＝本期創上期沒創、加速 ≥ 5 點是狀態；LINE 小部位事件行（股數、賣出句、新候選起點、不計入 4 行）、設定鍵、下一交易日外推
"""
from __future__ import annotations

import argparse
import contextlib
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
        r = subprocess.run([sys.executable, "-m", "backtest.bigrun_monthly", "--sha", G_SHA, "--kind", "auto", "--state", sp, "--out", os.path.join(td, "x.md"),
                            "--fwd", os.path.join(td, "fwd")],
                           cwd=os.environ.get("BGM_PYTHONPATH", REPO), capture_output=True, text=True, env={**os.environ, "PYTHONPATH": os.environ.get("BGM_PYTHONPATH", REPO)})
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
        BM.NOW_OVERRIDE = pd.Timestamp("2026-10-20 12:00")     # 固定「台北現在」＝ 資料日當天中午（各候選的新候選通知都還沒到時點，不干擾本段）
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
            ln = [sl[i]] + [x for x in __import__("itertools").takewhile(lambda x: x.startswith("  ") and not x.startswith("  - "), sl[i + 1:])
                            if not x.startswith("  小部位：")]                    # 小部位事件行另計、不算摘要 4 行（seq444）
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


# ═════════════ sp（前瞻小部位 seq3 fixture） ═════════════
def _J(BM, key, ra, up=(), judged=None, up_prev=()):
    """judgments 一份：up／up_prev ＝ 成立的代號集合；judged ＝ 當期有營收的代號集合（None ＝ 全部）。"""
    return (key, pd.Timestamp(ra), {s: {"up": s in up, "up_prev": s in up_prev, "judged": judged is None or s in judged, "det": "d", "det_prev": "dp"}
                                     for s in BM.SP_CODES})


def _part_sp():
    from backtest import bigrun_monthly as BM
    T = pd.Timestamp
    cal = pd.bdate_range("2026-10-19", "2028-01-31")
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

    def rd(key):                                   # 每月 12 日（遇週末往後）當月報資料日
        return cal[cal >= T(f"{key}-12")][0]

    def keys(n, k0="2026-11"):
        return [str(pd.Period(k0, "M") + i) for i in range(n)]
    rec("sp", "起點前（2026-10-21）⇒ 不記", upd([], "2026-10-21", FakePx()) == [], "")
    lock = {("1312", "2026-10-22"): {"o": 110.0, "h": 110.0, "l": 110.0, "c": 110.0, "pc": 100.0}, ("1305", "2026-10-22"): None}
    r1 = upd([], "2026-10-22", FakePx(lock))
    ev = {(r["stock_id"], r["event"]): r for r in r1}
    rec("sp", "補記起點：10-22 開盤各 1 份、1312 開盤鎖漲停買不到、1305 無成交買不到、註明補記",
        ev[("1503", "起點買進")]["units"] == "1" and ev[("1503", "起點買進")]["price_raw"] == "100.0"
        and ev[("1312", "起點買進")]["status"] == "買不到（開盤鎖漲停）" and ev[("1305", "起點買進")]["status"] == "買不到（當日無成交）"
        and all("補記" in r["note"] for r in r1 if r["event"] == "起點買進"), "；".join(f"{r['stock_id']} {r['event']} {r['status']}" for r in r1))
    rec("sp", "國喬標記：smallpos 另記一列「標記」＝進場時已轉強（只記一次）",
        [r["stock_id"] for r in r1 if r["event"] == "標記"] == ["1312"] and "進場時已轉強" in ev[("1312", "標記")]["note"]
        and upd(r1, "2026-10-23", FakePx()) == [], ev[("1312", "標記")]["note"][:30])
    rows = list(r1); snap = [dict(r) for r in rows]
    r2 = upd(rows, "2026-10-23", FakePx({("1503", "2026-10-22"): {"o": 999.0, "h": 999.0, "l": 999.0, "c": 999.0, "pc": 999.0}}))
    rec("sp", "凍結不重算：隔天價格換掉 ⇒ 不新增、舊列不變", r2 == [] and rows == snap, "")
    r3 = upd(rows, "2026-11-12", FakePx(), [_J(BM, "2026-11", "2026-11-12", up={"1503"})]); rows += r3
    rec("sp", "月報 2026-11 判定 4 列（第 1 份）；隔日資料還沒到 ⇒ 還不加碼",
        len(r3) == 4 and all(r["event"] == "月報判定" and r["note"].startswith("第 1 份") for r in r3), str([(r["stock_id"], r["judge"]) for r in r3]))
    r4 = upd(rows, "2026-11-13", FakePx({("1503", "2026-11-13"): {"o": 120.0, "h": 125.0, "l": 119.0, "c": 124.0, "pc": 118.0}})); rows += r4
    rec("sp", "轉強 ⇒ 月報隔天（11-13）開盤加 2 份", len(r4) == 1 and r4[0]["event"] == "轉強加碼" and r4[0]["units"] == "2" and r4[0]["price_raw"] == "120.0", str(r4))
    r5 = upd(rows, "2026-12-15", FakePx(), [_J(BM, "2026-12", "2026-12-14", up={"1503", "1513"})]); rows += r5
    rec("sp", "轉強加 2 份只一次：1503 再轉強 ⇒ 不再判、不再加；1513 新轉強 ⇒ 判定（第 2 份）＋隔天加 2 份",
        not [r for r in r5 if r["stock_id"] == "1503"] and [(r["stock_id"], r["event"]) for r in r5 if r["stock_id"] == "1513"] == [("1513", "月報判定"), ("1513", "轉強加碼")]
        and sum(r["stock_id"] == "1503" and r["event"] == "轉強加碼" for r in rows) == 1, str([(r["stock_id"], r["event"], r["units"]) for r in r5]))
    # 12 份月報都沒轉強 ⇒ 第 12 份（2027-10）隔天開盤賣（全部有持股的另一份紀錄）
    base = upd([], "2026-10-22", FakePx())
    R = list(base)
    for k in keys(11):
        R += upd(R, rd(k).date(), FakePx(), [_J(BM, k, rd(k))])
    sell11 = [r for r in R if r["event"] == BM.SELL_EV]
    r12 = upd(R, rd("2027-10").date(), FakePx(), [_J(BM, "2027-10", rd("2027-10"))]); R += r12
    nxt = cal[cal > rd("2027-10")][0]
    dn = {("1312", str(nxt.date())): {"o": 90.0, "h": 90.0, "l": 90.0, "c": 90.0, "pc": 100.0}}
    r13 = upd(R, cal[cal > nxt][0].date(), FakePx(dn)); R += r13
    e13 = {r["stock_id"]: r for r in r13}
    rec("sp", "第 1～11 份未轉強 ⇒ 不賣；第 12 份（2027-10）未轉強 ⇒ 記放棄判定、該份月報隔天開盤賣 −1 份（1312 鎖跌停 ⇒ 順延一天）",
        not sell11 and all("放棄判定" in r["note"] and r["note"].startswith("第 12 份") for r in r12) and len(r12) == 4
        and e13["1503"]["trade_date"] == str(nxt.date()) and e13["1503"]["units"] == "-1" and e13["1503"]["status"] == "未確認賣出"
        and e13["1312"]["trade_date"] == str(cal[cal > nxt][0].date()) and "順延" in e13["1312"]["note"],
        str([(r["stock_id"], r["trade_date"], r["units"]) for r in r13]))
    rec("sp", "已放棄者之後的月報不再判", upd(R, rd("2027-11").date(), FakePx(), [_J(BM, "2027-11", rd("2027-11"), up=set(BM.SP_CODES))]) == [], "")
    # 第 12 份當期營收未公布 ⇒ 不判；第 13 份只補判上一期、作放棄判定、賣出順延到第 13 份隔天
    R = list(base)
    for k in keys(11):
        R += upd(R, rd(k).date(), FakePx(), [_J(BM, k, rd(k))])
    r12 = upd(R, rd("2027-10").date(), FakePx(), [_J(BM, "2027-10", rd("2027-10"), judged={"1503", "1513", "1312"})]); R += r12
    r12b = upd(R, cal[cal > rd("2027-10")][0].date(), FakePx()); R += r12b
    r13 = upd(R, rd("2027-11").date(), FakePx(), [_J(BM, "2027-11", rd("2027-11"), up={"1305"}, up_prev=set())]); R += r13
    r13b = upd(R, cal[cal > rd("2027-11")][0].date(), FakePx()); R += r13b
    j1305 = [r for r in R if r["stock_id"] == "1305" and r["event"] == "月報判定"]
    s1305 = [r for r in R if r["stock_id"] == "1305" and r["event"] == BM.SELL_EV]
    rec("sp", "第 12 份當期未公布 ⇒ 記未判、不賣；第 13 份只補判上一期（本期轉強不算）⇒ 放棄判定、賣出順延到第 13 份隔天",
        j1305[-2]["judge"].startswith("未判") and j1305[-1]["note"].startswith("第 13 份") and "放棄判定" in j1305[-1]["note"]
        and j1305[-1]["judge"] == "未轉強" and len(s1305) == 1 and s1305[0]["trade_date"] == str(cal[cal > rd("2027-11")][0].date())
        and not [r for r in r12b if r["stock_id"] == "1305"], str([(r["report_key"], r["judge"], r["note"][:12]) for r in j1305[-2:]]) + str(s1305[:1]))
    R2 = list(base)
    R2 += upd(R2, rd("2026-11").date(), FakePx(), [_J(BM, "2026-11", rd("2026-11"), judged={"1503", "1513", "1312"})])
    r = upd(R2, rd("2026-12").date(), FakePx(), [_J(BM, "2026-12", rd("2026-12"), up_prev={"1305"})])
    j = [x for x in r if x["stock_id"] == "1305"]
    rec("sp", "期中當期未公布 ⇒ 下一份補判上一期（上一期轉強 ⇒ 確認）", len(j) == 1 and j[0]["judge"] == "轉強" and "補判上一期" in j[0]["judge_detail"], str(j))
    # 累計報酬（還原 ＝ 未還原的假資料）：1503 起點 100、加碼 120×2，資料日收 130 ⇒ (1×0.3 ＋ 2×(130/120−1)) ÷ 3 − 0.585%
    idx = pd.bdate_range("2026-10-22", "2026-11-20")

    def adj(sid):
        d = pd.DataFrame({"open": 100.0, "close": 100.0}, index=idx)
        if sid == "1503":
            d.loc[T("2026-11-13"), "open"] = 120.0; d["close"] = 130.0
        return d
    val, tot, mdd = BM.sp_value([x for x in rows if x["stock_id"] == "1503"], T("2026-11-20"), adj)
    exp = (0.3 + 2 * (130 / 120 - 1)) / 3 - 0.00585
    rec("sp", "照規則累計報酬（等額份數、每份扣 0.585%）", abs(val["1503"][1] - exp) < 1e-12 and val["1503"][0] == 3, f"{val['1503']} vs {exp}")
    # 使用者實際欄：種子讀入＋補記＋報酬（成交價換算還原、依金額加權、扣 0.585%）
    with tempfile.TemporaryDirectory() as td:
        pu = os.path.join(td, "u.csv")
        for x in BM.USER_SEED:
            BM.user_add(pu, x)
        BM.user_add(pu, {"stock_id": "1503", "name": "士電", "event": "轉強加碼", "trade_date": "2026-11-13", "shares": "200", "price": "125",
                         "detail": "200@125", "source": "fixture", "note": ""})
        U = BM.user_load(pu)
        ok_seed = [(x["stock_id"], x["shares"], x["price"]) for x in U[:4]] == [("1503", "104", "194.5"), ("1513", "123", "163.5"), ("1305", "1574", "12.7365"), ("1312", "1302", "15.25")]

        class P2:                                  # 未還原收盤 ＝ 假還原收盤（還原因子 1）
            def bar(self, sid, d):
                c = float(adj(sid).at[d, "close"])
                return {"o": c, "h": c, "l": c, "c": c, "pc": c}
        uv = BM.user_value(U, T("2026-11-20"), adj, P2())
        c1, c2 = 104 * 194.5, 200 * 125
        expu = (c1 * (130 / 194.5 - 1 - 0.00585) + c2 * (130 / 125 - 1 - 0.00585)) / (c1 + c2)
        rec("sp", "使用者實際欄：情報 1000 種子 4 檔讀入（1503 104@194.5、1513 123@163.5、1305 1574@12.7365、1312 1302@15.25）＋補記一列、報酬算式",
            ok_seed and len(U) == 5 and uv["1503"][0] == 304 and abs(uv["1503"][2] - expu) < 1e-12, f"{uv['1503']} vs {expu}")


# ═════════════ sp2（讀法核對＋LINE 事件行） ═════════════
def _part_sp2():
    from backtest import bigrun_monthly as BM
    T = pd.Timestamp
    ps = list(pd.period_range("2023-01", "2026-10", freq="M").astype(str)); n = len(ps)
    rows = []
    for i, p in enumerate(ps):
        r5 = 101.0 if i == n - 1 else (99.0 if i == n - 2 else 100.0); l5 = 100.0 if i == n - 1 else r5    # 1305：首次創 24 月新高、加速極小
        r3 = 100.0 + i; l3 = r3 / 1.1                                                                     # 1503：月月創新高、加速 0
        r2 = 100.0; l2 = 100.0 / 1.5 if i >= n - 4 else 100.0                                             # 1312：加速狀態連兩期 ≥ 5 點
        for sid, rv, ly in (("1305", r5, l5), ("1503", r3, l3), ("1312", r2, l2)):
            rows.append({"stock_id": sid, "period": p, "rev": rv, "ly": ly, "h_rev": rv, "d_rev": np.nan, "src": "revenue_hist"})
    L = pd.DataFrame(rows).sort_values(["stock_id", "period"])
    L["prev"] = L.groupby("stock_id")["rev"].shift(1)
    RM, P = BM.rev_metrics(L, ["1305", "1503", "1312"], T("2026-11-12"), {})
    df = pd.DataFrame([{"group": "D", "stock_id": s, "name": f"名{s}", **{k: v for k, v in RM[s].items() if k != "notes"}} for s in ("1305", "1503", "1312")])
    J = BM.sp_judgments(df, "2026-11", T("2026-11-12"), P)[0][2]
    rec("sp2", "③ 首次創 24 月新高 ＝ 本期創、上期沒創（1305 加速 < 5 點仍轉強）", P == "2026-10" and J["1305"]["up"] and J["1305"]["judged"], J["1305"]["det"])
    rec("sp2", "③ 本期與上期都創新高、加速 < 5 點 ⇒ 不是轉強（1503）", not J["1503"]["up"], J["1503"]["det"])
    rec("sp2", "③ 加速 ≥ 5 點是狀態：上期已成立、本期仍成立 ⇒ 本期照判轉強（1312）", J["1312"]["up"] and J["1312"]["up_prev"], J["1312"]["det"])
    LN = BM.line_month(df, P)
    ln = "\n".join(LN)
    rec("sp2", "① 加碼看每期判定本身、不套 LINE「上期沒轉強才列」：1312 判定轉強、LINE 轉強行不列", J["1312"]["up"] and "1312" not in ln and "1305" in ln, ln.replace("\n", " ／ "))
    cal = pd.bdate_range("2026-10-19", "2027-01-30")

    class Px:
        def bar(self, sid, d):
            return {"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "pc": 100.0}
    nm = {s: f"名{s}" for s in BM.SP_CODES}
    base = BM.sp_update([], cal, T("2026-10-22"), Px(), [], nm, "now", "f" * 40)
    r9 = BM.sp_update(base, cal, T("2026-10-23"), Px(), [_J(BM, "2026-10", "2026-10-23", up=set(BM.SP_CODES))], nm, "now", "f" * 40)
    r11 = BM.sp_update(base, cal, T("2026-11-12"), Px(), [_J(BM, "2026-11", "2026-11-12", up={"1312"})], nm, "now", "f" * 40)
    rec("sp2", "② 從起點後第一份月報（2026-11）起判：2026-10 鍵即使資料日在起點後也不判",
        r9 == [] and len([r for r in r11 if r["event"] == "月報判定"]) == 4, f"2026-10 鍵 {len(r9)}；2026-11 鍵 {len(r11)}")
    # LINE 事件行
    rec("sp2", "設定檔已開「小部位_LINE」（回測線改）、「小部位」＝20000（本模組只讀）", BM.sp_line_on() is True and BM.sp_cfg().get("小部位") == 20000, BM.CFG)
    with tempfile.TemporaryDirectory() as td:
        p1, p2 = os.path.join(td, "a.json"), os.path.join(td, "b.json")
        json.dump({"營量": 20000}, open(p1, "w")); json.dump({"小部位_LINE": True}, open(p2, "w"))
        rec("sp2", "缺鍵 ＝ false、鍵 true ＝ 開", BM.sp_line_on(p1) is False and BM.sp_line_on(p2) is True, "")
    cfg = {"小部位": 20000}
    ev = BM.sp_events_report(r11, {"1312": 15.25}, cfg)
    rec("sp2", "加碼行帶股數：設定 20000 × 2 ÷ 月報資料日未還原收盤 15.25 ＝ 2,622 股（零股取整）",
        ev == ["  小部位：1312 名1312 轉強 ⇒ 明天開盤加 2 份（約 2,622 股）"], str(ev))
    rec("sp2", "缺「小部位」金額 ⇒ 不估股數", BM.sp_events_report(r11, {"1312": 15.25}, {}) == ["  小部位：1312 名1312 轉強 ⇒ 明天開盤加 2 份（股數照你決定）"], "")
    ab = [dict(r, note="第 12 份月報；放棄判定（…）", judge="未轉強") for r in r11 if r["stock_id"] == "1305"]
    rec("sp2", "賣出行：第 12 份月報仍未轉強 ⇒ 明天開盤賣", BM.sp_events_report(ab, {}, cfg) == ["  小部位：1305 名1305 第 12 份月報仍未轉強 ⇒ 明天開盤賣"], "")
    evn = ["  小部位：2002 中鋼 新候選 ⇒ 10/27（二）開盤買 1 份（約 1,015 股）"]
    blk = LN + ["", "x"]
    out = BM.insert_line_events(blk, ev + evn)
    i0 = out.index(LN[0]); cont = [x for x in out[i0 + 1:] if x.startswith("  ")]
    rec("sp2", "小部位行不計入摘要 4 行：插在續行之後；摘要本身（不含小部位行）≤ 4 行",
        1 + len([x for x in cont if not x.startswith("  小部位：")]) <= 4 and cont[-2:] == ev + evn and len(LN) <= 4, " ／ ".join(out[i0:i0 + 6]))
    H = os.path.expanduser("~/h2data/eeb5af5f8feca83d0702fa0423a0c58cdb77900d/data")
    rec("sp2", "下一交易日外推（休市表）：2026-10-21 ⇒ 10-22；2026-10-23（五）⇒ 10-27（10-26 光復節補假）",
        BM.next_trading_day(H, T("2026-10-21")) == T("2026-10-22") and BM.next_trading_day(H, T("2026-10-23")) == T("2026-10-27"), "")


@contextlib.contextmanager
def four_cands(BM):
    """sp／sp2 的舊 fixture 只用 10/22 那 4 檔（seq5 新增 2002、1101 另在 sp3 測）；測的是原規則機制 ⇒ 暫時清空 SP_V4（v4 只記另在 sp3 測）。"""
    oc, ocodes, ov4 = dict(BM.SP_CANDS), list(BM.SP_CODES), set(BM.SP_V4)
    BM.SP_CANDS.clear(); BM.SP_CANDS.update({k: v for k, v in oc.items() if v == "2026-10-22"}); BM.SP_CODES[:] = list(BM.SP_CANDS)
    BM.SP_V4.clear()
    try:
        yield
    finally:
        BM.SP_CANDS.clear(); BM.SP_CANDS.update(oc); BM.SP_CODES[:] = ocodes
        BM.SP_V4.clear(); BM.SP_V4.update(ov4)


# ═════════════ sp3（seq8：候選 8 檔、新候選 10/26 晚、250／625 日提醒、新需求型燈2、報價提醒） ═════════════
def part_sp3():
    from backtest import bigrun_monthly as BM
    T = pd.Timestamp
    H = os.path.expanduser("~/h2data/eeb5af5f8feca83d0702fa0423a0c58cdb77900d/data")
    cal = pd.bdate_range("2026-10-19", "2029-12-31")
    cal = cal[(cal != T("2026-10-26")) & (cal != T("2026-10-23"))]        # 光復節補假、10/23 颱風休市
    nm = {"1503": "士電", "1513": "中興電", "1305": "華夏", "1312": "國喬", "4510": "高鋒", "6609": "瀧澤科", "8936": "國統", "3376": "新日興", "1519": "華城"}
    cfg = {"小部位": 20000}
    closes = {"4510": 40.0, "6609": 50.0, "8936": 20.0, "3376": 25.0}

    class Px:
        def bar(self, sid, d):
            return {"o": 100.0, "h": 101.0, "l": 99.0, "c": 100.0, "pc": 100.0}
    base = BM.sp_update([], cal, T("2026-10-22"), Px(), [], nm, "now", "f" * 40)

    def notify(rows, asof, now, **kw):
        return BM.sp_notify(rows, cal, T(asof), H, closes, cfg, nm, T(now), "f" * 40, **kw)
    exp = []
    rec("sp3", "SP_CANDS（10/25 使用者指示後）：5 檔、10/27 只買 8936；−2002 −1101 −2014 −4510 −6609、3376 延後；缺貨型 1305、1312；固定句 5 檔",
        list(BM.SP_CANDS) == ["1503", "1513", "1305", "1312"] and set(BM.SP_VIRTUAL) == {"8936", "1519"}
        and not {"2002", "1101", "2014", "4510", "6609", "3376"} & set(BM.SP_CANDS) and BM.SP_SHORTAGE == ["1305", "1312"] and BM.SP_NEWDEMAND == ["3376"]
        and BM.SP_FIX.startswith("台股 4 檔（10/22 四檔）；10/26 使用者「全賣了") and set(BM.SP_PPI) == {"1305", "1312"}, BM.SP_FIX)
    rec("sp3", "進場時已轉強標記：只剩 1312（3376 暫存 DORMANT）", set(BM.SP_ENTRY_UP) == {"1312"} and "3376" in BM.SP_ENTRY_UP_DORMANT, "")
    us = BM.user_sell_load()
    rec("sp3", "user_sell.csv：1305、1312 預定 2026-10-27 開盤賣（往前看判準不過，你 10/25 同意）",
        sorted(us) == ["1305", "1312", "1503", "1513"] and all(v[0] == T("2026-10-27") for v in us.values()) and all("10/25 同意" in us[x][1] for x in ("1305", "1312")) and all("使用者全賣" in us[x][1] for x in ("1503", "1513")), str(us))
    n0 = notify(base, "2026-10-22", "2026-10-24 20:00")
    n0b = notify(base, "2026-10-22", "2026-10-26 06:40")
    rec("sp3", "前一晚＝起點前一個日曆日（10/26）：10/24 晚、10/26 早上都不出", n0 == [] and n0b == [], str(n0 + n0b))
    n1 = notify(base, "2026-10-22", "2026-10-26 20:00")
    rec("sp3", "10/26 晚 20:00（資料日仍 10/22）⇒ 出 1 行新候選（10/27（二）開盤、股數＝20000÷未還原收盤取整），掛在 10/22 那份名單",
        [r["judge_detail"] for r in n1] == exp and all(r["event"] == "新候選通知" and r["report_asof"] == "2026-10-22" for r in n1), str([r["judge_detail"] for r in n1]))
    R = base + n1
    n2 = notify(R, "2026-10-22", "2026-10-26 23:30")
    rec("sp3", "只出一晚：已記 ⇒ 不再記；10/22 名單重產原樣補回", n2 == [] and BM.sp_event_lines(R, T("2026-10-22")) == exp, "")
    # 使用者指示賣出（產業 seq17／19／20）
    usx = {"1305": (T("2026-10-27"), "往前看判準不過，你 10/25 同意", "產業 seq17")}
    s0 = notify(base, "2026-10-22", "2026-10-26 06:40", usell=usx)
    s1 = notify(base, "2026-10-22", "2026-10-26 20:00", usell=usx)
    s2 = notify(base + s1, "2026-10-22", "2026-10-26 23:00", usell=usx)
    rec("sp3", "（指示賣出）10/26 早不出；10/26 晚出「1305 華夏 ⇒ 10/27（二）開盤賣（往前看判準不過，你 10/25 同意）」只一次（另 8936 新候選）",
        [r["judge_detail"] for r in s0] == [] and [r["judge_detail"] for r in s1 if r["stock_id"] == "1305"] == ["  小部位：1305 華夏 ⇒ 10/27（二）開盤賣（往前看判準不過，你 10/25 同意）"]
        and [r for r in s2 if r["stock_id"] == "1305"] == [], str([r["judge_detail"] for r in s1]))
    v27 = BM.sp_update(base, cal, T("2026-10-27"), Px(), [], nm, "now", "f" * 40, usell=usx)
    sl = [r for r in v27 if r["stock_id"] == "1305"]
    jx = BM.sp_update(base + v27, cal, T("2026-11-12"), Px(), [("2026-11", T("2026-11-12"), {"1305": {"up": True, "up_prev": False, "judged": True, "det": "d", "det_prev": "dp"}})],
                      nm, "now", "f" * 40, usell=usx)
    rec("sp3", "（指示賣出）10/27 開盤記「使用者指示賣出」−1 份、status 指示賣出；之後月報不再判、不加碼",
        [(r["event"], r["trade_date"], r["units"], r["status"]) for r in sl] == [("使用者指示賣出", "2026-10-27", "-1", "指示賣出")]
        and "不算規則本身的放棄" in sl[0]["note"] and [r for r in jx if r["stock_id"] == "1305"] == [], str(sl))
    n3 = notify(base, "2026-10-22", "2026-10-26 23:30")
    n4 = notify(base, "2026-10-27", "2026-10-27 00:30")
    rec("sp3", "10/26 20:00 沒跑到 ⇒ 當晚之後第一次執行補出；10/27（起點當天）起不出", [r["judge_detail"] for r in n3] == exp and n4 == [], "")
    r27 = BM.sp_update(base, cal, T("2026-10-27"), Px(), [], nm, "now", "f" * 40)
    rec("sp3", "10/27 sp_update：國統、華城已改虛擬卡 ⇒ 不補記起點（無新列）",
        sorted((r["stock_id"], r["event"]) for r in r27) == [], str([(r["stock_id"], r["event"]) for r in r27]))
    # 250／625 日提醒（缺貨型；附三項描述）
    cf = dict({c: "" for c in BM.SP_COLS}, stock_id="1305", name="華夏", event="月報判定", judge="轉強", report_key="2026-11", report_asof="2026-11-12")
    cf2 = dict(cf, stock_id="1503", name="士電")                 # 1503 不是缺貨型 ⇒ 不提醒
    after = cal[cal > T("2026-11-12")]
    dsc = lambda sid, c, asof: "描述"                              # noqa: E731
    m249 = notify(base + [cf, cf2], str(after[248].date()), f"{after[248].date()} 20:00", desc=dsc)
    m250 = notify(base + [cf, cf2], str(after[249].date()), f"{after[249].date()} 20:00", desc=dsc)
    m251 = notify(base + [cf, cf2] + m250, str(after[250].date()), f"{after[250].date()} 20:00", desc=dsc)
    m625 = notify(base + [cf, cf2] + m250, str(after[624].date()), f"{after[624].date()} 20:00", desc=dsc)
    mboth = notify(base + [cf, cf2], str(after[624].date()), f"{after[624].date()} 20:00")
    rec("sp3", "確認後第 249 日不出；第 250 日出一次（附三項描述）；隔天不再；第 625 日再出一次；兩者同時到只出 625；非缺貨型不出",
        m249 == [] and [r["judge_detail"] for r in m250] == ["  小部位：1305 華夏 確認後已滿 250 個交易日 ⇒ 續抱或賣？（你決定）｜描述"] and m251 == []
        and [r["judge_detail"] for r in m625] == ["  小部位：1305 華夏 確認後已滿 625 個交易日 ⇒ 續抱或賣？（你決定）｜描述"]
        and [r["judge_detail"] for r in mboth] == ["  小部位：1305 華夏 確認後已滿 625 個交易日 ⇒ 續抱或賣？（你決定）"], str([r["judge_detail"] for r in m250 + m625 + mboth]))
    # v4 卡（裁定 seq473）：1503、1513、8936 月報轉強只記、不加碼、不放棄
    Jv = {x: {"up": True, "up_prev": False, "judged": True, "det": "d", "det_prev": "dp"} for x in ("1503", "1513")}
    v1 = BM.sp_update(base + r27, cal, T("2026-11-12"), Px(), [("2026-11", T("2026-11-12"), Jv)], nm, "now", "f" * 40)
    v2 = BM.sp_update(base + r27 + v1, cal, T("2026-11-16"), Px(), [], nm, "now", "f" * 40)
    vj = [(r["stock_id"], r["judge"]) for r in v1]
    rec("sp3", "（v4）1503、1513 月報轉強 ⇒ 記「只記（v4）」、月報 LINE 無加碼行、之後不自動加碼；SP_V4＝{1503,1513,8936}",
        BM.SP_V4 == {"1503", "1513"} and sorted(vj) == [("1503", "只記（v4）"), ("1513", "只記（v4）")] and BM.sp_events_report(v1, closes, cfg) == []
        and not [r for r in v2 if r["event"] == "轉強加碼"], str(vj))
    # 新需求型 3376：燈2（機制測試：暫時把 4510、3376 放回候選，測完還原）
    oc, ocodes = dict(BM.SP_CANDS), list(BM.SP_CODES)
    BM.SP_CANDS.update({"4510": "2026-10-27", "3376": "2026-10-27"}); BM.SP_CODES[:] = list(BM.SP_CANDS)
    r27 = BM.sp_update(base, cal, T("2026-10-27"), Px(), [], nm, "now", "f" * 40)
    J = lambda up: {"3376": {"up": up, "up_prev": False, "judged": True, "det": "d", "det_prev": "dp"},     # noqa: E731
                    "4510": {"up": up, "up_prev": False, "judged": True, "det": "d", "det_prev": "dp"}}
    R27 = base + r27
    j1 = BM.sp_update(R27, cal, T("2026-11-12"), Px(), [("2026-11", T("2026-11-12"), J(True))], nm, "now", "f" * 40)
    rec("sp3", "（新需求型）月報轉強也不加碼：3376 記「燈2未亮」、4510 記「轉強」；月報 LINE 只出 4510 一行",
        [(r["stock_id"], r["event"], r["judge"]) for r in j1 if r["stock_id"] == "3376"] == [("3376", "月報判定", "燈2未亮")]
        and [r["judge"] for r in j1 if r["stock_id"] == "4510"] == ["轉強"]
        and BM.sp_events_report(j1, closes, cfg) == ["  小部位：4510 高鋒 轉強 ⇒ 明天開盤加 2 份（約 1,000 股）"], str([(r["stock_id"], r["event"], r["judge"]) for r in j1]))
    lp = {"3376": (T("2026-12-03"), "產業 seq99", "https://example/1")}
    l1 = notify(R27 + j1, "2026-12-03", "2026-12-03 22:00", lamp2=lp)
    l2 = notify(R27 + j1 + l1, "2026-12-04", "2026-12-04 20:00", lamp2=lp)
    rec("sp3", "（新需求型）燈2 收信 ⇒ 當晚通知「燈2 亮 ⇒ 12/4（五）開盤加 2 份」只一次",
        [r["judge_detail"] for r in l1] == ["  小部位：3376 新日興 燈2 亮 ⇒ 12/4（五）開盤加 2 份（約 1,600 股）"] and l2 == [], str([r["judge_detail"] for r in l1]))
    u1 = BM.sp_update(R27 + j1 + l1, cal, T("2026-12-04"), Px(), [], nm, "now", "f" * 40, lamp2=lp)
    rec("sp3", "（新需求型）收信後下一交易日 12/4 開盤加 2 份（事件「轉強加碼」、註燈2）",
        [(r["stock_id"], r["event"], r["trade_date"], r["units"]) for r in u1 if r["stock_id"] == "3376"] == [("3376", "轉強加碼", "2026-12-04", "2")]
        and "燈2" in u1[0]["note"], str([(r["stock_id"], r["event"], r["trade_date"]) for r in u1]))
    jj = []
    keys = [str(pd.Period("2026-11", freq="M") + k) for k in range(12)]
    for k in keys:
        jj += BM.sp_update(R27 + jj, cal, T(k + "-12"), Px(), [(k, T(k + "-12"), J(False))], nm, "now", "f" * 40)
    j3 = [r for r in jj if r["stock_id"] == "3376"]
    sell = BM.sp_update(R27 + jj, cal, T("2027-10-14"), Px(), [], nm, "now", "f" * 40)
    rec("sp3", "（新需求型）12 份月報燈2 都沒亮 ⇒ 第 12 份放棄判定、LINE「第 12 份月報燈2 仍未亮 ⇒ 明天開盤賣」、隔天賣出",
        len(j3) == 12 and all(r["judge"] == "燈2未亮" for r in j3) and "放棄判定" in j3[-1]["note"]
        and "  小部位：3376 新日興 第 12 份月報燈2 仍未亮 ⇒ 明天開盤賣" in BM.sp_events_report(j3, closes, cfg)
        and any(r["stock_id"] == "3376" and r["event"] == BM.SELL_EV for r in sell), j3[-1]["note"] if j3 else "")
    BM.SP_CANDS.clear(); BM.SP_CANDS.update(oc); BM.SP_CODES[:] = ocodes
    # 報價代理提醒：10/23 資料庫 PPI 到庫後開（缺鍵／false 仍不出）
    s = pd.Series([100.0, 99.0, 98.0, 97.0], index=["2027-01", "2027-02", "2027-03", "2027-04"])
    rec("sp3", "報價提醒：設定檔已開「小部位_報價提醒」（回測線 10/23 改）；缺鍵 ⇒ 不出", BM.sp_cfg().get("小部位_報價提醒") is True
        and BM.sp_ppi_lines([], T("2027-05-20"), nm, {}, loader=lambda sid: s) == [], "")
    on = {"小部位_報價提醒": True}
    rec("sp3", "（機制）開了但資料讀不到 ⇒ 不出；開了且連 3 月下跌 ⇒ 該檔出一行",
        BM.sp_ppi_lines([], T("2027-05-20"), nm, on, loader=None) == []
        and BM.sp_ppi_lines([], T("2027-05-20"), nm, on, loader=lambda sid: s if sid == "1305" else None) == ["  小部位：1305 華夏 報價代理連 3 個月下跌 ⇒ 續抱或賣？（你決定）"], "")
    s2 = pd.Series([100.0, 101.0, 99.0, 98.0], index=["2027-01", "2027-02", "2027-03", "2027-04"])
    rec("sp3", "（機制）只連跌 2 個月 ⇒ 不出", BM.sp_ppi_lines([], T("2027-05-20"), nm, on, loader=lambda sid: s2 if sid == "1305" else None) == [], "")
    pre = s.copy(); pre.attrs["rel"] = {m: T("2026-10-15") for m in pre.index}       # 最新月在起點 10/22 前發布 ⇒ 進場前已知
    post = s.copy(); post.attrs["rel"] = {**{m: T("2026-10-15") for m in post.index}, "2027-04": T("2026-11-13")}
    rec("sp3", "（機制）最新月在起點前發布 ⇒ 不出（只看進場後）；在起點後發布 ⇒ 出",
        BM.sp_ppi_lines([], T("2026-11-20"), nm, on, loader=lambda sid: pre if sid == "1305" else None) == []
        and BM.sp_ppi_lines([], T("2026-11-20"), nm, on, loader=lambda sid: post if sid == "1305" else None) == ["  小部位：1305 華夏 報價代理連 3 個月下跌 ⇒ 續抱或賣？（你決定）"], "")
    s5 = pd.Series([100.0, 99.0, 98.0, 97.0, 96.0], index=["2027-01", "2027-02", "2027-03", "2027-04", "2027-05"])
    L4 = lambda sid: s if sid == "1305" else None                                     # noqa: E731
    L5 = lambda sid: s5 if sid == "1305" else None                                    # noqa: E731
    p1 = BM.sp_notify(base, cal, T("2027-05-20"), H, closes, on, nm, T("2027-05-20 20:00"), "f" * 40, ppi=L4)
    p2 = BM.sp_notify(base + p1, cal, T("2027-06-20"), H, closes, on, nm, T("2027-06-20 20:00"), "f" * 40, ppi=L5)
    p0 = BM.sp_notify(base, cal, T("2027-05-20"), H, closes, cfg, nm, T("2027-05-20 20:00"), "f" * 40, ppi=L4)
    rec("sp3", "（機制）報價提醒寫成「提醒」紀錄列、隨 sp_event_lines 補回；同一段下跌（段起月同）隔月續跌不再出；設定關 ⇒ 不出",
        [r["judge_detail"] for r in p1] == ["  小部位：1305 華夏 報價代理連 3 個月下跌 ⇒ 續抱或賣？（你決定）"] and p1[0]["event"] == "提醒"
        and "段起 2027-02" in p1[0]["note"] and p2 == [] and p0 == []
        and BM.sp_event_lines(base + p1, T("2027-05-20")) == ["  小部位：1305 華夏 報價代理連 3 個月下跌 ⇒ 續抱或賣？（你決定）"], p1[0]["note"] if p1 else "")
    LR = BM.ppi_loader(T("2026-10-23"), fetch=False)
    rec("sp3", "（實資料，只看結構不印值）私有庫 PPI 讀得到：四檔對三條代理、最新已發布月 ≥ 2026-08、10/23 晚因進場前已知不出",
        LR is not None and all(LR(x) is not None and LR(x).index[-1] >= "2026-08" for x in BM.SP_SHORTAGE)
        and BM.sp_ppi_lines([], T("2026-10-23"), nm, on, loader=LR) == [], "")


def part_sp():
    from backtest import bigrun_monthly as BM
    with four_cands(BM):
        _part_sp()


def part_sp2():
    from backtest import bigrun_monthly as BM
    with four_cands(BM):
        _part_sp2()


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
    if "sp2" in parts:
        part_sp2()
    if "sp3" in parts:
        part_sp3()
    n = len(RES); ok = sum(r[2] for r in RES)
    print(f"\n驗證 {n} 項：通過 {ok}、不符 {n - ok}")
    for r in RES:
        if not r[2]:
            print("✖", r)
    sys.exit(0 if ok == n else 1)


if __name__ == "__main__":
    main()

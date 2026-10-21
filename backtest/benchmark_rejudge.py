# -*- coding: utf-8 -*-
"""台股基準改「大盤」＝臺灣發行量加權股價報酬指數（含息）：基準對照、重判、排名、0050 不強的時候（裁定 seq425～428）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.benchmark_rejudge <指令> [--tr 來源] [--procs 3]
      compare    第 1 項：基準對照表（探索／確認／早年 × 0050 含息／大盤報酬指數／大盤價格指數：年化、回落、比值＋逐年差）
      rejudge    第 2 項：重判（原標籤並列「新基準重看」）＋ 對帳（以 0050 當基準走同一條路 ⇒ 重現原 0050 值與原標籤，0 不符才算過）
      rank       第 3 項：排名表（seq426 格式 | 排名 | 策略 | 年化 | 最大回落 | 比值 | 對大盤 |；三段；主排名 ＝ 確認段）
      weak       第 4 項：「0050 不強的時候」（滾動 12 個月 0050 落後大盤的期間；只描述）
      buildeq    重建權益（營飆 v1 主世界 200 顆、營量 v1／營飆 v1 早年；researchYL_integrate.eng 原樣；閘 eq_sha ＝ resultsYL_integrate/seeds.csv.gz）
                 --part 主｜早年（各一次，單次 < 10 分鐘）
      all        compare＋rejudge＋rank＋weak
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.benchmark_rejudge_check

  基準序列（任一日序列：日期、指數值）：
    --tr <路徑.csv>｜git:<ref>:<repo 內路徑>   欄 ＝ date ＋（close｜value｜tri｜第二欄）
    沒給 --tr ⇒ 讀固定路徑 TR_FIXED（存在才用）；都沒有 ⇒ 報酬指數欄一律「—（報酬指數未到庫）」
    ⛔ 不以價格指數、也不自行用股利還原「代替」報酬指數產出任何判定或排名（回測線規矩：等資料庫）

輸出 backtest/resultsBenchRejudge/：compare.json／compare_seg.csv／compare_year.csv、rejudge.csv／rejudge_check.json、
     rank_<段>.md／rank.csv、weak.json／weak_periods.csv、eq_cache.npz（buildeq）、run.log

═══ 讀法（寫死於 2026-10-21 15:00（台北），寫死前 ⛔ 沒看過大盤報酬指數任何數字（資料不在庫）；看過的：各件已交的 0050 基準數字與標籤）═══
 B0 統計式 ⛔ 不另寫：策略權益窗內年化／回落 ＝ rerun17.win_metrics；基準序列 ＝ rerun17.bench_row（窗首為基、不含成本、年化 ＝ 窗內交易日數／245）；
    比值 ＝ researchAscTri.ratio（年化 ÷ |回落|）；標籤 ＝ researchAscTri.label（合格 ＝ 年化 ＞ 基準 且 比值 ≥ 基準；另列 ＝ 只贏年化；其餘不合格）；
    逐年 ＝ researchPTHpf.yearly（日曆年末 ÷ 前一年末；段首年用段首）；月底 ＝ researchPTH_freq.month_ends；
    六四 v1 ＝ researchMix70.load／sim ＋ researchLev2.perf（research64retest 同式；ETF 成本 0.385% 建倉與調回皆扣）；
    多顆種子 ⇒ 年化中位、回落中位、比值 ＝ 中位 ÷ |中位|（rerun17 慣例，⛔ 不是逐顆比值的中位）
 B1 基準序列對齊：依各件世界日曆 reindex ＋ ffill（＝ rerun17.load_bench 同式）；窗首缺值 ⇒ 該格「—」；報 ffill 補值日數
 B2 段（compare）：探索 2017-03-02～2021-12-30、確認 2022-01-03～資料尾（另報 ～2026-08-24 ＝ 排名窗）、早年 2005 首個交易日～2014-12-31；
    0050 含息 ＝ 還原收盤（data.load_stock 還原因子）；探索／確認讀 tw-stock-data origin/main（抽到 ~/bmkwork/main_<sha12>/data），早年讀早年版面（researchAddOn.EOTC）
 B3 重判（rejudge）：每件每段 ＝ 該件原判定所用的世界、窗、判定臂；年化／回落 有存權益者以權益重算（並與檔值比對），否則讀檔值（附精度）
    ⇒ 原標籤（對 0050，檔內）並列「新基準重看」標籤（對大盤報酬指數同窗）；原判定、整件結論 ⛔ 不改、不刪
    ⇒ 新基準下才變合格的：只算候選、最多暫定（seq425 §一）——本支只標「新基準重看：合格（候選、最多暫定）」，⛔ 不改任何件的狀態
    對帳：同一條路改餵 0050（各件世界資料的 rerun17.load_bench）⇒ 0050 年化／回落 ＝ 檔值（容差 ＝ 檔值精度）、標籤 ＝ 原標籤，逐列 0 不符
 B4 排名（rank）：窗 ＝ 確認（主排名）2022-01-03～2026-08-24（營量 v1、營飆 v1 定版資料尾；所有列同窗）｜探索（參考）2017-03-02～2021-12-30｜
    早年（參考）2005-02-01～2014-12-31（營量／營飆早年訊號起點）；同表同窗、各件原成本口徑（個股 0.585% 來回、六四 ETF 0.385%、0050／正2／大盤 不含成本＝判準慣例）；
    排序 ＝ 比值由高到低、同比值年化高者前；另附年化名次（並列）；起點不同（六四探索段 2018-01-15 起）另表、⛔ 不與全段並排比名次；算不出 ⇒「—」＋原因
    對大盤 ＝ researchAscTri.label 對大盤報酬指數同窗；⛔ 不擇優、不寫「最好用哪個」
 B5 0050 不強的時候（weak）：各段 pts ＝ 段首 ＋ 段內完整月底（researchPTH_freq.month_ends）；滾動 12 個月窗 (pts[k−12], pts[k])；
    0050 落後 ⇔ r0050 ＜ r大盤（嚴格）；落後幅度 d ＝ r大盤 − r0050 分組 (0, 2]、(2, 5]、＞ 5 個百分點；連續落後的窗尾月份併成「期間」列出
    ⇒ 各策略在落後窗的 12 個月報酬：窗數、平均、中位、贏大盤的窗比例、窗內名次平均（依 12 個月報酬，排名組同 B4）；只描述 ⛔ 不成規則
    ⚠ 滾動窗彼此重疊 ⇒ 窗數不是獨立樣本數
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import researchPTHpf as PF                    # noqa: E402
from backtest import researchPTH_freq as PFQ                # noqa: E402

TIME = "2026-10-21 15:00（台北）"
OUT = "backtest/resultsBenchRejudge"
WORK = os.path.expanduser("~/bmkwork")
TR_FIXED = os.path.join(WORK, "taiex_tr.csv")               # 報酬指數到庫後：放這裡（date,close）或用 --tr git:origin/main:<路徑>
PRICE_GIT = "data/history/market_index.csv"                # 大盤價格指數（tw-stock-data origin/main）
NA_TR = "—（報酬指數未到庫）"
WORLD_DATA = {"主": RR.H2D, "早年": RA.EOTC}
CMP_SEG = {"探索": ("主", "2017-03-02", "2021-12-30"), "確認": ("主", "2022-01-03", None), "確認至2026-08-24": ("主", "2022-01-03", "2026-08-24"),
           "早年": ("早年", "2005-01-01", "2014-12-31")}
RANK_SEG = {"確認": ("主", "2022-01-03", "2026-08-24"), "探索": ("主", "2017-03-02", "2021-12-30"), "早年": ("早年", "2005-02-01", "2014-12-31")}
RANK_NOTE = {"確認": "主排名", "探索": "參考（市場結構與現在不同）", "早年": "參考（市場結構與現在不同）"}
LAG_BINS = ((0.0, 0.02, "0～2 點"), (0.02, 0.05, "2～5 點"), (0.05, np.inf, "5 點以上"))
LOGF = None


def log(m):
    s = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(s + "\n")


def git(*a):
    return subprocess.check_output(["git", "-C", os.path.expanduser("~/tw-p17"), *a]).decode("utf-8")


# ═════════════ 資料：世界日曆、最新庫、基準序列 ═════════════
_CAL: dict = {}


def world_cal(data):
    if data not in _CAL:
        old = D.DATA; D.DATA = data
        _CAL[data] = D.load_calendar()
        D.DATA = old
    return _CAL[data]


def latest_data():
    """tw-stock-data origin/main 抽出計算要的檔（唯讀 git show）⇒ ~/bmkwork/main_<sha12>/data。"""
    sha = git("rev-parse", "origin/main").strip()
    root = os.path.join(WORK, f"main_{sha[:12]}", "data")
    need = ["meta/calendar_twse.csv", "stocks/0050.csv", "adj/0050.csv", "stocks/00631L.csv", "adj/00631L.csv", "stocks/00685L.csv", PRICE_GIT.replace("data/", "")]
    for rel in need:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            continue
        try:
            txt = git("show", f"{sha}:data/{rel}")
        except subprocess.CalledProcessError:
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt)
    return root, sha


def stock_close(data, sid):
    """還原收盤（ffill）＝ rerun17.load_bench 同式（0050 以外的 ETF 也用同一式）。"""
    old = D.DATA; D.DATA = data
    cal = D.load_calendar()
    st = D.load_stock(sid, "twse", cal)
    D.DATA = old
    if st is None:
        return None
    return pd.Series(pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(float), index=cal)


def bench0050(data):
    old = D.DATA; D.DATA = data
    cal = D.load_calendar(); b = RR.load_bench(cal)
    D.DATA = old
    return pd.Series(np.asarray(b, float), index=cal)


def read_series(src):
    """任一日序列 ⇒ pd.Series（DatetimeIndex 由小到大、float）。src ＝ 路徑或 git:<ref>:<path>。"""
    if src.startswith("git:"):
        _, ref, path = src.split(":", 2)
        df = pd.read_csv(io.StringIO(git("show", f"{ref}:{path}")))
    else:
        df = pd.read_csv(src)
    cols = [c for c in df.columns if str(c).lower() != "date"]
    vc = next((c for c in ("close", "value", "tri", "index") if c in df.columns), cols[0])
    s = pd.Series(pd.to_numeric(df[vc], errors="coerce").to_numpy(float), index=pd.to_datetime(df["date"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


def tr_source(a):
    if getattr(a, "tr", None):
        return a.tr
    if os.path.exists(TR_FIXED):
        return TR_FIXED
    return None


def on_cal(s, cal):
    """B1：日序列 ⇒ 世界日曆（reindex＋ffill）；回 (陣列, 補值日數)。"""
    r = s.reindex(cal)
    nfill = int(r.isna().sum() - r.ffill().isna().sum())
    return r.ffill().to_numpy(float), nfill


def seg_pos(cal, a, b):
    """段端點 ⇒ 日曆位置（researchAscTri_freq.load_world 同式：起 searchsorted、迄 side='right'−1；迄 None ⇒ 資料尾）。"""
    x = int(cal.searchsorted(pd.Timestamp(a)))
    y = len(cal) - 1 if b is None else int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
    return x, y


def bstat(cal, arr, x, y):
    """B0：基準序列窗內 年化／回落／比值（rerun17.bench_row）；窗首或窗內缺值 ⇒ None。"""
    if not np.all(np.isfinite(arr[x:y + 1])):
        return None
    r = RR.bench_row(cal, arr, x, y + 1)
    return {"cagr": float(r["cagr"]), "mdd": float(r["mdd"]), "ratio": AS.ratio(r["cagr"], r["mdd"]), "a": str(cal[x].date()), "b": str(cal[y].date()), "days": y - x + 1}


def estat(eq, x, y):
    """B0：策略權益窗內 年化／回落（rerun17.win_metrics；first＝0、end＝len）。"""
    c, m, _ = RR.win_metrics(np.asarray(eq, float), 0, len(eq), x, y)
    return float(c), float(m)


def med_stat(eqs, x, y):
    v = [estat(e, x, y) for e in eqs]
    c, m = float(np.median([z[0] for z in v])), float(np.median([z[1] for z in v]))
    return c, m


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


def f2(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.2f}"


# ═════════════ 第 1 項：基準對照 ═════════════
def compare(a):
    os.makedirs(OUT, exist_ok=True)
    root, sha = latest_data()
    trs = tr_source(a)
    price = read_series(f"git:origin/main:{PRICE_GIT}")
    TR = read_series(trs) if trs else None
    S = {"讀法寫死": TIME, "最新庫": f"tw-stock-data origin/main {sha[:10]}（抽到 {root}）", "價格指數": f"origin/main:{PRICE_GIT}",
         "報酬指數": trs or NA_TR, "段": {}, "逐年": {}}
    rows, yrows = [], []
    for sg, (wn, a_, b_) in CMP_SEG.items():
        data = root if wn == "主" else WORLD_DATA["早年"]
        cal = world_cal(data)
        x, y = seg_pos(cal, a_, b_)
        ser = {"0050 含息": bench0050(data), "大盤價格指數": price}
        if TR is not None:
            ser["大盤報酬指數"] = TR
        arr, fills = {}, {}
        for k, s in ser.items():
            arr[k], fills[k] = on_cal(s, cal)
        out = {}
        for k in ("0050 含息", "大盤報酬指數", "大盤價格指數"):
            if k not in arr:
                out[k] = None
                rows.append({"段": sg, "序列": k, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": np.nan, "回落": np.nan, "比值": np.nan, "註": NA_TR})
                continue
            st = bstat(cal, arr[k], x, y)
            out[k] = st
            rows.append({"段": sg, "序列": k, "窗": f"{cal[x].date()}～{cal[y].date()}", "交易日": y - x + 1,
                         "年化": st["cagr"] if st else np.nan, "回落": st["mdd"] if st else np.nan, "比值": st["ratio"] if st else np.nan,
                         "註": "" if st else "窗內缺值", "ffill補值日": fills[k]})
        S["段"][sg] = {"窗": f"{cal[x].date()}～{cal[y].date()}", "資料": data, **{k: v for k, v in out.items()}}
        if sg in ("確認至2026-08-24",):
            continue
        yy = {}
        for k in arr:
            if np.all(np.isfinite(arr[k][x:y + 1])):
                yy[k] = PF.yearly(arr[k], arr[k], cal, x, y)
        for Y in sorted(next(iter(yy.values())).keys()) if yy else []:
            r = {"段": sg, "年": Y}
            for k in ("0050 含息", "大盤報酬指數", "大盤價格指數"):
                r[k] = yy[k][Y]["本件"] if k in yy else np.nan
            r["起"], r["訖"] = yy["0050 含息"][Y]["起"], yy["0050 含息"][Y]["訖"]
            r["0050−報酬指數"] = r["0050 含息"] - r["大盤報酬指數"]
            r["0050−價格指數"] = r["0050 含息"] - r["大盤價格指數"]
            r["報酬指數−價格指數"] = r["大盤報酬指數"] - r["大盤價格指數"]
            yrows.append(r)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "compare_seg.csv"), index=False, float_format="%.10g", encoding="utf-8")
    pd.DataFrame(yrows).to_csv(os.path.join(OUT, "compare_year.csv"), index=False, float_format="%.10g", encoding="utf-8")
    json.dump(S, open(os.path.join(OUT, "compare.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[compare] {len(rows)} 列、逐年 {len(yrows)} 列 ⇒ {OUT}/compare_*.csv")
    return rows, yrows


# ═════════════ 第 2 項：重判登錄表（每件每段一列）═════════════
def _win(s):
    a_, b_ = str(s).split("～")
    return a_.strip(), b_.strip()


def fw_rows(name, path, filt, eqf=None, idcol=None, ident=None, verdict=None, note=""):
    """新框架結果表（欄：世界、段、窗、年化、回落、0050年化、0050回落、標籤）；eqf ＝ {世界: (npz, 鍵)} 有則以權益重算。"""
    T = pd.read_csv(path, encoding="utf-8-sig", float_precision="round_trip", dtype=str)
    for k, v in filt.items():
        T = T[T[k] == v]
    out = []
    for _, r in T.iterrows():
        a_, b_ = _win(r["窗"])
        wn = r["世界"]
        row = {"策略": name, "身分": ident or (r[idcol] if idcol and idcol in r else "判定"), "世界": wn, "段": r["段"], "a": a_, "b": b_,
               "年化_檔": float(r["年化"]), "回落_檔": float(r["回落"]), "0050年化_檔": float(r["0050年化"]), "0050回落_檔": float(r["0050回落"]),
               "原標籤": r["標籤"], "出處": f"{path}｜{filt}", "整件原結論": verdict or "", "註": note, "精度": "檔 6 位有效"}
        row["年化"], row["回落"], row["值來源"] = row["年化_檔"], row["回落_檔"], "檔值"
        if eqf and wn in eqf:
            npz, key = eqf[wn]
            eq = np.load(npz)[key]
            cal = world_cal(WORLD_DATA[wn])
            x, y = seg_pos(cal, a_, b_)
            c, m = estat(eq, x, y)
            row["年化"], row["回落"], row["值來源"] = c, m, f"權益重算 {npz}[{key}]"
        out.append(row)
    return out


def yl_rows():
    """營量 v1／營飆 v1：researchYL_integrate 定版（cells.csv %.8g；0050 ＝ summary.json 全精度）。"""
    C = pd.read_csv("backtest/resultsYL_integrate/cells.csv", float_precision="round_trip")
    S = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))
    W = {"探索": ("主", "2017-03-02", "2021-12-30"), "確認": ("主", "2022-01-03", "2026-08-24"), "早年": ("早年", "2005-02-01", "2014-12-31")}
    out = []
    for name, key, n in (("營量 v1", "H60·S20·無·relvol", 1), ("營飆 v1", "H120·S10·閘·抽籤", 200)):
        for sg, (wn, a_, b_) in W.items():
            r = C[(C["世界"] == wn) & (C["格"] == key)].iloc[0]
            b = S["0050"][wn][sg]
            out.append({"策略": name, "身分": "判定（暫定）", "世界": wn, "段": sg, "a": a_, "b": b_, "年化": float(r[f"{sg}_年化"]), "回落": float(r[f"{sg}_回落"]),
                        "年化_檔": float(r[f"{sg}_年化"]), "回落_檔": float(r[f"{sg}_回落"]), "0050年化_檔": b["cagr"], "0050回落_檔": b["mdd"],
                        "原標籤": r[f"{sg}_標籤"], "出處": f"backtest/resultsYL_integrate/cells.csv｜{key}", "值來源": "檔值" + ("（200 顆中位）" if n > 1 else ""),
                        "精度": "檔 8 位有效；0050 全精度", "整件原結論": "暫定（等 2026-10 起實際紀錄滿一年）", "註": "早年 ＝ 上市＋上櫃 W_B" if wn == "早年" else ""})
    return out


def six4_rows():
    """六四 v1：research64retest（窗 A 2018-01-15～2026-08-24、窗 B 2022-01-03～2026-08-24）；以 researchMix70.sim 重算。"""
    from backtest import research64retest as R64
    from backtest import researchMix70 as MX
    from backtest import researchLev2 as L2
    X = _mx()
    S = json.load(open("backtest/results64retest/summary.json", encoding="utf-8"))["① 同窗判定＋⑤ 並列"]
    out = []
    for wk, sg, (a_, b_) in (("A 2018-01-15～2026-08-24", "2018～2026（窗 A）", R64.WA), ("B 確認段 2022-01-03～2026-08-24", "確認", R64.WB)):
        i0, i1 = X["pos"][a_], X["pos"][b_]
        eq, *_ = MX.sim(("0050", "00685L"), R64.W64, i0, i1, X["O"], X["C"], X["cal"], "Y", 1)
        c, m = L2.perf(eq)
        f = S[wk]["六四 v1（真 00685L）"]; b = S[wk]["0050（判準，還原、不含成本）"]
        out.append({"策略": "六四 v1", "身分": "判定", "世界": "六四", "段": sg, "a": a_, "b": b_, "年化": c, "回落": m, "年化_檔": f["年化"], "回落_檔": f["最大回落"],
                    "0050年化_檔": b["年化"], "0050回落_檔": b["最大回落"], "原標籤": f["判準"], "出處": f"backtest/results64retest/summary.json｜{wk}",
                    "值來源": "重算 researchMix70.sim＋researchLev2.perf", "精度": "全精度", "整件原結論": "報酬面正式；風險面 ⚠（1990／2000／2008 型崩盤 −68～−87%）",
                    "註": "00685L 2017-03-30 上市；窗 A 起 2018-01-15"})
    return out


_MXC: dict = {}


def _mx():
    if "X" not in _MXC:
        from backtest import researchMix70 as MX
        _MXC["X"] = MX.load()
        _MXC["X"]["calidx"] = pd.DatetimeIndex(pd.to_datetime(_MXC["X"]["cal"]))
    return _MXC["X"]


M_EXP, M_CON = ("主", "2017-03-02", "2021-12-30"), ("主", "2022-01-03", "2026-08-24")


def _b(v):
    """0050 值各種寫法 ⇒ (年化, 回落)。"""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return float(v[0]), float(v[1])
    for c, m in (("cagr", "mdd"), ("年化", "回落"), ("年化", "最大回落")):
        if c in v and m in v:
            return float(v[c]), float(v[m])
    return None


def _row(name, sg, w, c, m, lab, b50, src, ident="判定", verdict="", note="", prec="檔值", vsrc="檔值"):
    wn, a_, b_ = w
    return {"策略": name, "身分": ident, "世界": wn, "段": sg, "a": a_, "b": b_, "年化": float(c), "回落": float(m), "年化_檔": float(c), "回落_檔": float(m),
            "0050年化_檔": (b50[0] if b50 else np.nan), "0050回落_檔": (b50[1] if b50 else np.nan), "原標籤": lab, "出處": src, "值來源": vsrc,
            "精度": prec, "整件原結論": verdict, "註": note}


def tab_rows(name, path, filt, segs, b50=None, fmt="wide", segcol="段", cc="年化", mc="回落", lc="標籤", b50cols=None, **kw):
    """一般結果表：fmt＝wide（欄 <段>_年化）或 long（段欄）；segs ＝ {段: (世界, 起, 迄)}；b50 ＝ {段: 0050 值} 或 b50cols ＝ (年化欄, 回落欄)。"""
    T = pd.read_csv("backtest/" + path, encoding="utf-8-sig", float_precision="round_trip", dtype=str, keep_default_na=False)
    for k, v in filt.items():
        T = T[T[k] == v]
    out = []
    for sg, w in segs.items():
        if fmt == "wide":
            if T.empty or f"{sg}_{cc}" not in T.columns:
                continue
            if len(T) > 1:
                raise SystemExit(f"⛔ {name}：篩選後 {len(T)} 列（判定臂不唯一）")
            r = T.iloc[0]; c, m, lab = r[f"{sg}_{cc}"], r[f"{sg}_{mc}"], r.get(f"{sg}_{lc}", "")
            bb = (float(r[b50cols[0].format(sg=sg)]), float(r[b50cols[1].format(sg=sg)])) if b50cols else _b((b50 or {}).get(sg))
        else:
            g = T[T[segcol] == sg]
            if g.empty:
                continue
            if len(g) > 1:
                raise SystemExit(f"⛔ {name} {sg}：篩選後 {len(g)} 列（判定臂不唯一）")
            r = g.iloc[0]; c, m, lab = r[cc], r[mc], r.get(lc, "")
            bb = (float(r[b50cols[0]]), float(r[b50cols[1]])) if b50cols else _b((b50 or {}).get(sg))
        if c in ("", "nan") or m in ("", "nan"):
            continue
        out.append(_row(name, sg, w, c, m, lab, bb, f"backtest/{path}｜{filt}", **kw))
    return out


GRID_EXTRA = {"resultsF4Launch": {"母體": "all", "群": "F4"}}       # 連續虧損：判定臂 ＝ 主母體、帶 F4（researchF4Launch L12）


def grid_rows(name, d, cell, ver, **kw):
    """grid.csv＋summary.json 族（BARR、急跌、好營收…）：主 ＝ 探索／確認（2026-08-24 尾），早年 ＝ summary 早年.格[cell|ver]。"""
    S = json.load(open(f"backtest/{d}/summary.json", encoding="utf-8"))
    b = S.get("meta", {}).get("0050") or S.get("0050")
    out = tab_rows(name, f"{d}/grid.csv", {"格": cell, "版本": ver, **GRID_EXTRA.get(d, {})}, {"探索": M_EXP, "確認": M_CON}, b50=b, prec="檔 6 位有效", **kw)
    e = S.get("早年")
    if isinstance(e, dict) and isinstance(e.get("格"), dict) and f"{cell}|{ver}" in e["格"]:
        g = e["格"][f"{cell}|{ver}"]; a_, b_ = e["窗"]
        out.append(_row(name, "早年", ("早年", a_, b_), g["早年_年化"], g["早年_回落"], g["早年_標籤"], _b(e["0050"]), f"backtest/{d}/summary.json｜早年.格.{cell}|{ver}",
                        prec="全精度", **kw))
    return out


def json_rows(name, path, getter, segs, b50, **kw):
    """summary.json 內直接存的段值：getter(S) ⇒ {段: (年化, 回落, 標籤)}。"""
    S = json.load(open("backtest/" + path, encoding="utf-8"))
    V = getter(S); out = []
    for sg, w in segs.items():
        if sg in V:
            c, m, lab = V[sg]
            out.append(_row(name, sg, w, c, m, lab, _b(b50(S).get(sg)) if b50 else None, f"backtest/{path}", prec="全精度", **kw))
    return out


REGISTRY_NOTE = {
    "未納入自動重判（本階段）": [
        "庫藏股事件（resultsEvt）：探索段 2012-01～2018-12 跨早年／主兩個版面（接合日曆），只納確認、早年兩段",
        "門檻B W1／219 種組態／P7～P17／A／F／C／D4（resultsN219/table219.csv）：錨是捨入值（0.248／0.241／0.2454…）、窗各族不同 ⇒ 要逐族確認窗與捨入規則才能逐列重現，本階段列盤點不自動重判；主窗 17 格（resultsN17/rerun17.csv 主窗段）已納入",
        "加減碼 12 種（resultsP9run、P9ext）：主窗＋A／B 窗、0050 錨為浮動窗 ⇒ 同上",
        "產業動能（resultsIndMom）：事件層、沒有組合年化 ⇒ 依構造無法重判",
        "長線組合 Long3：月頻回落、與日頻判準口徑不同 ⇒ 不納",
        "CGO＋低波動、X1 多因子：只有主窗或非標準拼接段、身分描述 ⇒ 不納",
        "一目三役（resultsLongI）：A 2009-01～2019-03 跨版面 ⇒ 只納 B 段",
        "強勢類股（resultsSector）：cells 無標籤、判定在 body.json／Audit5 ⇒ 下一階段補",
        "營量／營飆變體（加碼、真頂、ListExit、YfStop、YfTime、YfRank、YfV2、YfSlots2、YfMix13、Slip、YLearly、YLnoDup、OpenBaseLock、SuspendHold）：描述或 T1 前、或比的是對原策略 ⇒ 不納",
        "大盤／ETF 類（三態輪動 Audit2/1、20 日線切換 Lev2、0050＋正2＋現金、跌深加碼 Dip、低頻擇時 LowFreq、純抱正2、微台 2 倍 TXF）：資料世界為 researchTri.load_all 合併日曆、窗 2015-11-02 起 ⇒ 下一階段補（六四已納）",
        "大跌類（MktDrop v1／v3／up／addon2、大跌 4 檔）：無合格標籤欄（只有方向判語）⇒ 無舊標籤可並列",
    ]}


def registry():
    R = []
    R += yl_rows()
    R += six4_rows()
    B = "backtest/"
    R += fw_rows("高10（接近 52 週高 最高 10 檔）", B + "resultsPTHn/PTHn_main.csv", {"N": "10", "滑價": "False"},
                 {"主": (B + "resultsPTHn/eq_主.npz", "N10_eq"), "早年": (B + "resultsPTHn/eq_早年.npz", "N10_eq")}, ident="描述（10/21 起推 LINE、前瞻紀錄）")
    R += fw_rows("52 週高 前 30%（PTHpf）", B + "resultsPTHpf/PTHpf_main.csv", {"臂": "M"},
                 {"主": (B + "resultsPTHpf/eq_主.npz", "M_eq"), "早年": (B + "resultsPTHpf/eq_早年.npz", "M_eq")}, verdict="不合格")
    R += fw_rows("52 週高 前 30%（PTHpf）滑價版", B + "resultsPTHpf/PTHpf_main.csv", {"臂": "Mslip"},
                 {"主": (B + "resultsPTHpf/eq_主.npz", "Mslip_eq"), "早年": (B + "resultsPTHpf/eq_早年.npz", "Mslip_eq")}, verdict="（可執行性條款）")
    R += fw_rows("上升三角組合", B + "resultsAscTri/AscTri_main.csv", {"臂": "M0050"},
                 {"主": (B + "resultsAscTri/eq_主.npz", "M0050"), "早年": (B + "resultsAscTri/eq_早年.npz", "M0050")}, verdict="不合格")
    R += fw_rows("海龜 S2 組合", B + "resultsTurtleS2PF/TurtleS2PF_main.csv", {"臂": "M"},
                 {"主": (B + "resultsTurtleS2PF/eq_主.npz", "M_eq"), "早年": (B + "resultsTurtleS2PF/eq_早年.npz", "M_eq")}, verdict="不合格")
    R += fw_rows("海龜 S2 組合 滑價版", B + "resultsTurtleS2PF/TurtleS2PF_main.csv", {"臂": "Mslip"},
                 {"主": (B + "resultsTurtleS2PF/eq_主.npz", "Mslip_eq"), "早年": (B + "resultsTurtleS2PF/eq_早年.npz", "Mslip_eq")})
    R += fw_rows("PEAD 財報意外組合", B + "resultsPEADpf/PEADpf_main.csv", {"臂": "M"}, {"主": (B + "resultsPEADpf/eq.npz", "M_eq")})
    R += fw_rows("PEAD 財報意外組合 滑價版", B + "resultsPEADpf/PEADpf_main.csv", {"臂": "Mslip"}, {"主": (B + "resultsPEADpf/eq.npz", "Mslip_eq")})
    R += [r for r in fw_rows("最笨交易法", B + "resultsDumb/Dumb_main.csv", {"格": "F1", "滑價": "False"},
                             {"主": (B + "resultsDumb/eq_主.npz", "F1"), "早年": (B + "resultsDumb/eq_早年.npz", "F1")}, verdict="不合格") if r["段"] in ("探索", "確認", "早年")]
    # ── grid.csv＋summary.json 族（0.585% 版 b；好營收漲停另報現實版 r＝主要參考）──
    for nm, d, cell, ver, vd in (("BARR 底", "resultsBARR", "E2", "b", "不合格"), ("急跌錯殺", "resultsCrashOversold", "F1X2", "b", "不合格"),
                                 ("急跌：等營收證實", "resultsCrashExt/急跌後等營收證實", "V1X2", "b", "不合格"), ("急跌：等止跌", "resultsCrashExt/急跌後等止跌", "S2X2", "b", "不合格"),
                                 ("急跌：法人逆勢買", "resultsCrashExt/急跌中有人逆勢買", "I1X2", "b", "不合格"), ("急跌：融資大減", "resultsCrashExt/融資大減型錯殺", "M1X2", "b", "不合格"),
                                 ("好營收漲停隔天買（0.585% 版）", "resultsRevLimitUp", "E2", "b", "不合格"), ("好營收漲停隔天買（現實版，主要參考）", "resultsRevLimitUp", "E2", "r", "不合格"),
                                 ("好營收股價已認同", "resultsRevPriceOK", "C2S2", "b", "不合格"), ("單季 EPS 比上季高", "resultsEPSqoq", "G2", "b", "不合格"),
                                 ("個股趨勢全多", "resultsTrendAll", "D2", "b", "不合格"), ("財報前季營收前段（全格退化、只描述）", "resultsPreFinRev", "A2", "b", "判不了（全退化）"),
                                 ("高成長加速", "resultsRevAccel", "E2", "b", "不合格"), ("連續虧損股起漲", "resultsF4Launch", "k5_x20_E1", "b", "不合格")):
        R += grid_rows(nm, d, cell, ver, verdict=vd)
    # ── 一般寬表／長表 ──
    J = lambda p: json.load(open("backtest/" + p, encoding="utf-8"))
    E1 = ("早年", "2005-01-04", "2014-12-31")
    s = J("resultsLowTO/summary.json")["0050"]
    for cell in ("甲_L120_半年_N10", "乙_L120_季_N20"):
        R += tab_rows(f"低週轉 {cell[0]}", "resultsLowTO/cells.csv", {"格": cell}, {"探索": M_EXP, "確認": M_CON, "早年": E1}, b50=s, verdict="不合格")
    R += tab_rows("週線達華斯", "resultsLongD/cells.csv", {"格": "週_N20"}, {"探索": M_EXP, "確認": M_CON, "早年": ("早年", "2005-01-03", "2014-12-31")},
                  b50=J("resultsLongD/summary.json")["0050"], verdict="不合格")
    R += tab_rows("趨勢樣板", "resultsLongT/table.csv", {"格": "乙_月_N20"}, {"探索": M_EXP, "確認": M_CON, "早年": ("早年", "2005-03-01", "2014-12-31")},
                  b50=J("resultsLongT/summary.json")["0050"], verdict="不合格")
    R += tab_rows("借券＋法人（營量再加濾網）", "resultsSBL/cells_combo.csv", {"世界": "主", "格": "乙_L20"}, {"探索": M_EXP, "確認": M_CON},
                  b50=J("resultsSBL/summary.json")["0050 同段"], verdict="不合格")
    R += tab_rows("借券＋法人（營量再加濾網）", "resultsSBL/cells_combo_early.csv", {"世界": "早年", "格": "乙_L20"}, {"早年": ("早年", "2012-08-01", "2014-12-31")}, verdict="不合格")
    s = J("resultsQual/summary.json")["0050"]
    for d in ("resultsQual", "resultsQualA0"):
        P = J(f"{d}/summary.json")["挑格"]
        R += tab_rows(f"品質因子 甲（{d[-2:] if d.endswith('A0') else 'A2'} 版）", f"{d}/cells.csv", {"格": P["甲"]["格"]},
                      {"探索": M_EXP, "確認": M_CON, "早年": ("早年", "2014-06-04", "2014-12-31")}, fmt="long", verdict="只在一段合格")
        R += tab_rows(f"品質因子 乙（{d[-2:] if d.endswith('A0') else 'A2'} 版）", f"{d}/cells.csv", {"格": P["乙"]["格"]},
                      {"探索": M_EXP, "確認": M_CON, "早年": ("主", "2015-08-04", "2016-12-30")}, fmt="long", verdict="只在一段合格")
    S = J("resultsMomX/summary.json")
    for k, v in S["挑格"].items():
        R += tab_rows(f"動能改良 {k}", "resultsMomX/cells.csv", {"格": v["格"]}, {"探索": M_EXP, "確認": M_CON, "早年": ("早年", "2006-01-03", "2014-12-31")},
                      b50=S["0050"], fmt="long", note="同格主／早年兩世界列以段欄分", verdict="M1 另列；其餘不合格")
    R += tab_rows("機器學習 改目標", "resultsMLx/cells.csv", {"格": "A_GB_季_N20"}, {"探索": ("主", "2019-01-01", "2021-12-30"), "確認": M_CON},
                  b50=J("resultsMLx/summary.json")["0050"], fmt="long", verdict="不合格")
    R += tab_rows("合成分數", "resultsScore/cells.csv", {"格": "L20_月換_N10"}, {"探索": M_EXP, "確認": M_CON}, b50=J("resultsScore/summary.json")["0050"], fmt="long", verdict="不合格")
    e = J("resultsScore/summary.json")["早年"]["A"]
    R.append(_row("合成分數", "早年", ("早年", *e["窗"]), e["年化"], e["回落"], e["標籤"], _b(e["0050"]), "backtest/resultsScore/summary.json｜早年.A", prec="全精度",
                  note=f"早年資料 {e['資料']}"))
    for nm, path, filt in (("訊號進訊號出 E1（任一高檔訊號出）", "resultsSig/cells.csv", {"E": "E1", "出場": "EVE", "停損": "無", "停利": "無"}),
                           ("訊號進訊號出 E2", "resultsSig/cells.csv", {"E": "E2", "出場": "EVE", "停損": "無", "停利": "無"}),
                           ("訊號進訊號出 E1＋停損停利", "resultsSig/cells.csv", {"E": "E1", "出場": "EVE", "停損": "SL10", "停利": "TP50h"}),
                           ("訊號進訊號出（重挑）E1", "resultsSigRe/cells.csv", {"E": "E1", "出場": "VSc", "停損": "無", "停利": "無"}),
                           ("訊號進訊號出（重挑）E2", "resultsSigRe/cells.csv", {"E": "E2", "出場": "VSc", "停損": "無", "停利": "無"}),
                           ("跌破均線出 E1", "resultsSigMA/cells.csv", {"E": "E1", "出場": "MA60"}), ("跌破均線出 E2", "resultsSigMA/cells.csv", {"E": "E2", "出場": "MA60"})):
        R += tab_rows(nm, path, filt, {"探索": M_EXP, "確認": M_CON}, fmt="long", cc="cagr_med", mc="mdd_med", lc="label", b50cols=("c50", "m50"), verdict="不合格",
                      note="200 顆中位")
    for d in ("resultsExtAuth", "resultsExtAuth2"):
        for k, cell in J(f"{d}/summary.json")["探索段挑格"].items():
            if "|" not in cell:
                continue
            ky, ex = cell.split("|")
            R += tab_rows(f"外部作者 {ky}", f"{d}/cells.csv", {"顆": ky, "出場／H": ex}, {"探索": M_EXP, "確認": M_CON}, fmt="long", cc="cagr_med", mc="mdd_med", lc="label",
                          b50cols=("c50", "m50"), verdict="不合格", note="200 顆中位")
    R += tab_rows("季節性：營量 1～2 月換 0050（丙）", "resultsSeason/cells.csv", {"策略": "營量", "格": "丙_1～2月"},
                  {"探索": M_EXP, "確認": M_CON, "早年": ("早年", "2012-06-04", "2014-12-31")}, b50=J("resultsSeason/summary.json")["0050"], fmt="long",
                  cc="年化中位", mc="回落中位", verdict="測不出（年判定）", note="200 顆中位")
    m4 = J("resultsMaster4/summary.json")
    T = pd.read_csv("backtest/resultsMaster4/cells.csv", float_precision="round_trip")
    for _, r in T.iterrows():
        R.append(_row(f"App 大師 {r['套']} H{r['H']}", "單窗", ("主", "2019-06-03", "2026-08-24"), r["年化中位"], r["回落中位"], r["標籤"], _b(m4["0050同窗"]),
                      "backtest/resultsMaster4/cells.csv", verdict="9 格全不合格", note="起點 2019-06-03（財報時戳覆蓋）"))
    vb = J("resultsVolBreak/summary.json")["0050"]
    T = pd.read_csv("backtest/resultsVolBreak/cells.csv", float_precision="round_trip", dtype={"B": str, "k": str, "L": str})
    T = T[(T["出場"] == "ema") & (T["臂"] == "M")]
    W3 = {"探索": M_EXP, "確認": M_CON, "早年": ("早年", "2005-02-01", "2014-12-30")}
    for _, r in T.iterrows():
        R.append(_row(f"爆量突破 B{r['B']}·k{r['k']}·L{r['L']}", r["段"], W3[r["段"]], r["年化中位"], r["回落中位"], r["標籤"], _b(vb[r["段"]]),
                      "backtest/resultsVolBreak/cells.csv", prec="檔 10 位", verdict="整套不合格（60 格過半才算）", note="50 顆中位", ident="判定（整套 60 格）"))
    E12 = ("早年", "2012-06-01", "2014-12-30")
    for nm, p, vd in (("產業營收加速（爆發產業）", "resultsIndRev/prereg/variants.csv", "不合格"), ("產業營收加速但股價落後", "resultsIndRevLag/prereg/variants.csv", "不合格")):
        R += tab_rows(nm, p, {"版本": "主表（industry_pit）"}, {"探索": M_EXP, "確認": M_CON, "早年": E12}, fmt="long", b50cols=("0050年化", "0050回落"), verdict=vd, prec="檔 10 位")
    R += tab_rows("產業營收落後：買賣點改版", "resultsIndRevLag/buysell/cells.csv", {"key": "B0|T60"}, {"探索": M_EXP, "確認": M_CON, "早年": E12},
                  b50=J("resultsIndRevLag/buysell/meta.json")["0050"], verdict="不合格", prec="檔 10 位")
    T = pd.read_csv("backtest/resultsTopPrevTW/cells.csv", float_precision="round_trip")
    for _, r in T[(T["格"] == "T6") & (T["臂"] == "主臂") & (T["世界"].isin(["主", "早年"]))].iterrows():
        a_, b_ = [x.strip(" '") for x in r["窗"].strip("[]").split(",")]
        lab = "合格" if (r["年化贏0050"] and r["比值贏0050"]) else ("另列" if r["年化贏0050"] else "不合格")
        R.append(_row("去年漲最多（T6 前 10 名、營收年增＞0）", r["段"], (r["世界"], a_, b_), r["年化"], r["回落"], lab, (r["0050年化"], r["0050回落"]),
                      "backtest/resultsTopPrevTW/cells.csv｜T6 主臂", prec="檔 10 位", verdict="不給合格（seq348：只描述落點）",
                      note="原檔無標籤欄，以「年化贏0050／比值贏0050」兩布林換成同義標籤"))
    T = pd.read_csv("backtest/resultsEvt/port_cells.csv", float_precision="round_trip", dtype={"H": str})
    for _, r in T[(T["類型"] == "全部") & (T["H"] == "120") & (T["段"].isin(["確認", "早年"]))].iterrows():
        w = ("主", "2019-01-01", "2026-08-24") if r["段"] == "確認" else ("早年", "2005-01-01", "2011-12-31")
        R.append(_row("庫藏股買回後買（H120）", r["段"], w, r["年化中位"], r["回落中位"], r["標籤"], None, "backtest/resultsEvt/port_cells.csv", verdict="不合格",
                      note="200 顆中位；探索段 2012～2018 跨版面未納"))
    # ── 營量／營飆家族（判過的變體）──
    YE = ("早年", "2012-06-04", "2014-12-31")
    b = J("resultsYLtrend/summary.json")["0050"]
    R += tab_rows("營量趨勢（乙_T3_H40）", "resultsYLtrend/cells.csv", {"格": "乙_T3_H40"}, {"探索": M_EXP, "確認": M_CON, "早年": YE}, b50=b, verdict="不合格（對營量 v1 不穩）")
    b = J("resultsYLexit/summary.json")["0050"]
    for cell in ("營量_甲_b5_H40", "營量_乙_k60_C120"):
        R += tab_rows(f"營量出場 seq1 {cell}", "resultsYLexit/cells.csv", {"格": cell}, {"探索": M_EXP, "確認": M_CON, "早年": YE}, b50=b, verdict="不合格")
    b = J("resultsYLexit3/summary.json")["0050"]
    for cell in ("營量_甲3_b5_H40", "營量_乙3_k55_c10_C120"):
        R += tab_rows(f"營量出場 seq3 {cell}", "resultsYLexit3/cells.csv", {"格": cell}, {"探索": M_EXP, "確認": M_CON, "早年": YE}, b50=b, verdict="不合格")
    R += tab_rows("週線乙（營量看週收盤）", "resultsWeekly/乙_cells.csv", {"格": "L5_m8_C26"}, {"探索": M_EXP, "確認": M_CON, "早年": YE}, verdict="不合格", prec="檔 6 位有效")
    for nm, p, keys in (("毛利率沒退步", "resultsYLmargin/cells.csv", ("vol|q1", "fly|q1")), ("同產業最多 3 檔", "resultsYLindcap/cells.csv", ("vol|cap", "fly|cap"))):
        for k in keys:
            R += tab_rows(f"{nm}（{'營量' if k.startswith('vol') else '營飆'}）", p, {"key": k}, {"探索": M_EXP, "確認": M_CON}, fmt="long",
                          b50cols=("0050年化", "0050回落"), verdict="沒有改善")
    for n in ("15", "20"):
        R += tab_rows(f"營飆 {n} 檔", "resultsYF_N/cells.csv", {"世界": "主", "N": n}, {"探索": M_EXP, "確認": M_CON}, fmt="long", cc="年化_中位", mc="回落_中位",
                      lc="對0050", b50cols=("0050年化", "0050回落"), prec="檔 10 位", note="200 顆中位")
        R += tab_rows(f"營飆 {n} 檔", "resultsYF_N/cells.csv", {"世界": "早年", "N": n}, {"早年": ("早年", "2005-02-01", "2014-12-31")}, fmt="long", cc="年化_中位",
                      mc="回落_中位", lc="對0050", b50cols=("0050年化", "0050回落"), prec="檔 10 位", note="200 顆中位")
    R += [dict(r, 策略="營量 v1 補下市營收（描述）", 身分="描述") for r in tab_rows("x", "resultsDelistRev/cells.csv", {"變體": "merged_a", "策略": "營量"},
                                                                         {"探索": M_EXP, "確認": M_CON}, fmt="long", lc="對0050", b50cols=("0050年化", "0050回落"), prec="檔 10 位")]
    R += [dict(r, 策略="營飆 v1 補下市營收（描述）", 身分="描述") for r in tab_rows("x", "resultsDelistRev/cells.csv", {"變體": "merged_a", "策略": "營飆"},
                                                                         {"探索": M_EXP, "確認": M_CON}, fmt="long", lc="對0050", b50cols=("0050年化", "0050回落"), prec="檔 10 位")]
    T = pd.read_csv("backtest/resultsN17/rerun17.csv", float_precision="round_trip", dtype={"編號": str})
    for _, r in T.iterrows():
        R.append(_row(f"候選 17 格 #{r['編號']} {r['族']}｜{r['格']}", "主窗", ("主", "2017-03-02", "2026-08-24"), r["主窗_年化"], r["主窗_回落"], r["主窗_標籤"],
                      (r["錨_年化"], r["錨_回落"]), "backtest/resultsN17/rerun17.csv", prec="全精度", verdict="候選（219 種裡看過才挑）", note="200 顆中位（rerun17）"))
    return R


def rejudge(a, bench_override=None):
    """第 2 項。bench_override ＝ {世界: pd.Series}（對帳用：0050）；預設 ＝ 大盤報酬指數（無 ⇒ 新標籤「—」）。"""
    os.makedirs(OUT, exist_ok=True)
    trs = tr_source(a)
    TR = read_series(trs) if trs else None
    R = registry()
    out = []
    for r in R:
        cal = _mx()["calidx"] if r["世界"] == "六四" else world_cal(WORLD_DATA[r["世界"]])
        x, y = seg_pos(cal, r["a"], r["b"])
        o = dict(r); o["窗"] = f"{cal[x].date()}～{cal[y].date()}"; o["比值"] = AS.ratio(r["年化"], r["回落"])
        if bench_override is not None:
            s = bench_override[r["世界"]]
        else:
            s = TR
        if s is None:
            o.update({"基準年化": np.nan, "基準回落": np.nan, "基準比值": np.nan, "新基準重看": NA_TR})
        else:
            arr, nfill = on_cal(s, cal)
            st = bstat(cal, arr, x, y)
            if st is None:
                o.update({"基準年化": np.nan, "基準回落": np.nan, "基準比值": np.nan, "新基準重看": "—（基準窗內缺值）"})
            else:
                lab = AS.label(r["年化"], r["回落"], st)
                if bench_override is None and lab == "合格" and r["原標籤"] != "合格":
                    lab = "合格（新基準下才變合格 ⇒ 候選、最多暫定）"
                o.update({"基準年化": st["cagr"], "基準回落": st["mdd"], "基準比值": st["ratio"], "新基準重看": lab, "基準ffill補值日": nfill})
        out.append(o)
    df = pd.DataFrame(out)
    if bench_override is None:
        df.to_csv(os.path.join(OUT, "rejudge.csv"), index=False, float_format="%.10g", encoding="utf-8")
        log(f"[rejudge] {len(df)} 列｜基準 {trs or NA_TR}")
    return df


def bench0050_worlds():
    return {"主": bench0050(WORLD_DATA["主"]), "早年": bench0050(WORLD_DATA["早年"]),
            "六四": pd.Series(np.asarray(_mx()["C"]["0050"], float), index=_mx()["calidx"])}


def reconcile(a):
    """B3 對帳：同一條路餵 0050 ⇒ 0050 值 ＝ 檔值、標籤 ＝ 原標籤；年化／回落 權益重算 ＝ 檔值（容差依精度）。"""
    df = rejudge(a, bench_override=bench0050_worlds())
    rows = []
    for _, r in df.iterrows():
        t = 1e-12 if r["精度"] == "全精度" else (5e-8 if "8 位" in r["精度"] else 1e-5)     # 檔值捨入（6 位有效最寬 5e−6）
        has50 = np.isfinite(r["0050年化_檔"])
        d50c = abs(r["基準年化"] - r["0050年化_檔"]) / max(abs(r["0050年化_檔"]), 1e-12) if has50 else np.nan
        d50m = abs(r["基準回落"] - r["0050回落_檔"]) / max(abs(r["0050回落_檔"]), 1e-12) if has50 else np.nan
        dc = abs(r["年化"] - r["年化_檔"]) / max(abs(r["年化_檔"]), 1e-12)
        dm = abs(r["回落"] - r["回落_檔"]) / max(abs(r["回落_檔"]), 1e-12)
        rows.append({"策略": r["策略"], "段": r["段"], "窗": r["窗"], "原標籤": r["原標籤"], "0050 基準重現標籤": r["新基準重看"],
                     "標籤相同": r["新基準重看"] == r["原標籤"], "0050年化相對差": d50c, "0050回落相對差": d50m,
                     "0050相符": ("檔無 0050 值" if not has50 else bool(d50c <= t and d50m <= t)),
                     "年化相對差": dc, "回落相對差": dm, "年化回落相符": bool(dc <= t and dm <= t), "容差": t, "值來源": r["值來源"], "出處": r["出處"]})
    C = pd.DataFrame(rows)
    res = {"列數": len(C), "策略件數": int(C["策略"].nunique()), "標籤不符": int((~C["標籤相同"]).sum()),
           "0050 值不符": int((C["0050相符"] == False).sum()), "0050 值檔無（只比標籤）": int((C["0050相符"] == "檔無 0050 值").sum()),  # noqa: E712
           "年化回落不符": int((~C["年化回落相符"]).sum())}
    C.to_csv(os.path.join(OUT, "rejudge_check.csv"), index=False, float_format="%.3g", encoding="utf-8")
    json.dump(res, open(os.path.join(OUT, "rejudge_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[對帳 0050 基準] {res}")
    return res, C


# ═════════════ 權益重建（營飆 v1 主世界、營量／營飆 早年）═════════════
YLK, YFK = "H60·S20·無·relvol", "H120·S10·閘·抽籤"
_BW: dict = {}


def _eq_job(args):
    from backtest import researchYL_integrate as IG
    key, r = args
    o, _ = IG.eng(_BW["W"], key, r, audit=False)
    eq = np.asarray(o["equity"], float)
    return key, r, eq, IG.sha(eq)


def buildeq(a):
    """researchYL_integrate.eng 原樣重跑定版兩格（⛔ 不改任何參數）；閘：逐顆 eq_sha ＝ resultsYL_integrate/seeds.csv.gz，0 不符才存。"""
    from backtest import researchYL_integrate as IG
    part = a.part
    if part not in ("主", "早年"):
        raise SystemExit("⛔ buildeq 要 --part 主｜早年")
    T0 = time.time()
    W, gate = IG.main_world(log) if part == "主" else IG.early_world(log, a.procs)
    _BW["W"] = W
    jobs = [(YFK, r) for r in range(200)] + [(YLK, 0)]
    with Pool(a.procs) as pool:
        res = pool.map(_eq_job, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[ref["世界"] == part].set_index(["格", "r"])["eq_sha"]
    bad = [(k, r) for k, r, _, s in res if ref.loc[(k, r)] != s]
    log(f"[buildeq {part}] {len(res)} 條｜eq_sha 不符 {len(bad)}｜世界閘 {gate}｜{time.time() - T0:.0f}s")
    if bad:
        raise SystemExit(f"⛔ eq_sha 不符 {bad[:5]} ⇒ 不存")
    YF = np.array([eq for k, r, eq, _ in sorted(res, key=lambda z: (z[0], z[1])) if k == YFK])
    YL = np.array([eq for k, r, eq, _ in res if k == YLK])
    cal = W["cal"]
    np.savez_compressed(os.path.join(OUT, f"eq_{part}.npz"), YF=YF, YL=YL, dates=np.array([str(d.date()) for d in cal]))
    json.dump({"世界": part, "條數": len(res), "eq_sha 不符": 0, "世界閘": gate, "秒": round(time.time() - T0)},
              open(os.path.join(OUT, f"eq_{part}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


def _eq_series(arr, cal):
    """權益陣列（位置 ＝ 世界日曆）⇒ pd.Series（多出的尾端 NP 位置丟掉）。"""
    arr = np.asarray(arr, float)
    return pd.Series(arr[:len(cal)], index=cal[:min(len(cal), len(arr))])


def rank_universe(wn):
    """B4／B5 排名組在世界 wn 的權益（日期索引；多顆 ⇒ list）。缺 ⇒ (None, 原因)。"""
    cal = world_cal(WORLD_DATA[wn])
    B = "backtest/"
    E = {}
    if wn == "主":
        E["營量 v1"] = [_eq_series(np.load(B + "resultsYL_integrate/pair_main.npz")["pk"][0], cal)]
    p = os.path.join(OUT, f"eq_{wn}.npz")
    if os.path.exists(p):
        Z = np.load(p)
        if wn == "早年":
            E["營量 v1"] = [_eq_series(Z["YL"][0], cal)]
        E["營飆 v1"] = [_eq_series(e, cal) for e in Z["YF"]]
    E["高10"] = [_eq_series(np.load(B + f"resultsPTHn/eq_{wn}.npz")["N10_eq"], cal)]
    E["0050"] = [bench0050(WORLD_DATA[wn])]
    if wn == "主":
        E["正2（00631L）"] = [stock_close(WORLD_DATA[wn], "00631L")]
    return E


def six4_eq(a_, b_):
    from backtest import research64retest as R64
    from backtest import researchMix70 as MX
    X = _mx()
    i0, i1 = X["pos"][a_], X["pos"][b_]
    eq, *_ = MX.sim(("0050", "00685L"), R64.W64, i0, i1, X["O"], X["C"], X["cal"], "Y", 1)
    return eq, X["calidx"][i0:i1 + 1]


def rank(a):
    """第 3 項（B4）。"""
    from backtest import researchLev2 as L2
    trs = tr_source(a)
    TR = read_series(trs) if trs else None
    YLR = {(r["策略"], r["段"]): r for r in yl_rows()}
    allrows, md = [], []
    for sg, (wn, a_, b_) in RANK_SEG.items():
        cal = world_cal(WORLD_DATA[wn]); x, y = seg_pos(cal, a_, b_)
        bt = None
        if TR is not None:
            arr, _ = on_cal(TR, cal); bt = bstat(cal, arr, x, y)
        rows, side = [], []

        def add(name, c, m, note="", tab=rows, win=None):
            lab = "—" if (bt is None or c is None or not np.isfinite(c)) else AS.label(c, m, bt)
            tab.append({"段": sg, "策略": name, "年化": c, "回落": m, "比值": AS.ratio(c, m) if c is not None else np.nan, "對大盤": lab if bt is not None else NA_TR,
                        "窗": win or f"{cal[x].date()}～{cal[y].date()}", "註": note})
        for nm in ("營量 v1", "營飆 v1"):
            r = YLR[(nm, sg)]
            if (r["a"], r["b"]) != (str(cal[x].date()), str(cal[y].date())):
                raise SystemExit(f"⛔ {nm} {sg} 窗 {r['a']}～{r['b']} ≠ 排名窗")
            add(nm, r["年化"], r["回落"], "200 顆中位（比值 ＝ 中位÷|中位|）" if nm == "營飆 v1" else "")
        e10 = np.load(f"backtest/resultsPTHn/eq_{wn}.npz")["N10_eq"]
        c, m = estat(e10, x, y); add("高10", c, m, "PTHn N10 權益切窗（原件連續跑、窗首帶持股）")
        if sg == "確認":
            eq, _ = six4_eq(a_, b_); c, m = L2.perf(eq); add("六四 v1", c, m, "research64retest 窗 B 同式（ETF 0.385%）")
        elif sg == "探索":
            eq, _ = six4_eq("2018-01-15", b_); c, m = L2.perf(eq)
            add("六四 v1", c, m, "起點不同：00685L 2017-03-30 上市、六四判定窗 2018-01-15 起 ⇒ 另表、⛔ 不並排比名次", tab=side, win=f"2018-01-15～{b_}")
        else:
            add("六四 v1", None, None, "早年無 00685L（2017-03-30 上市）；2008 只有用 0050×2 合成的模擬 ⇒ 不列")
        add("大跌 4 檔", None, None, "只有往後紀錄（2026-10-15 那次起、10 次才判）；歷史只有「每次大跌平均報酬」與「平時抱 0050、事件撥 20%」口徑，⛔ 不是 4 檔組合年化")
        b50 = bench0050(WORLD_DATA[wn]); arr50, _ = on_cal(b50, cal); s50 = bstat(cal, arr50, x, y)
        add("0050", s50["cagr"], s50["mdd"], "還原收盤、不含成本（判準慣例）")
        if wn == "主":
            p2 = stock_close(WORLD_DATA[wn], "00631L"); ap2, _ = on_cal(p2, cal); s2 = bstat(cal, ap2, x, y)
            add("正2（00631L）", s2["cagr"], s2["mdd"], "還原收盤、不含成本（同 0050 口徑）")
        else:
            add("正2（00631L）", None, None, "00631L 2014-10-31 上市 ⇒ 早年無")
        if bt is not None:
            rows.append({"段": sg, "策略": "大盤（報酬指數）", "年化": bt["cagr"], "回落": bt["mdd"], "比值": bt["ratio"], "對大盤": "（基準）",
                         "窗": f"{cal[x].date()}～{cal[y].date()}", "註": "不含成本"})
        else:
            add("大盤（報酬指數）", None, None, NA_TR)
        T = pd.DataFrame(rows)
        ok = T["年化"].notna() & np.isfinite(T["年化"].astype(float))
        V = T[ok].sort_values(["比值", "年化"], ascending=[False, False]).reset_index(drop=True)
        V["排名"] = (np.arange(1, len(V) + 1).astype(str) if bt is not None else "—（待報酬指數）")
        V["年化名次"] = V["年化"].rank(ascending=False, method="min").astype(int)
        NA = T[~ok].assign(排名="—", 年化名次=np.nan)
        T = pd.concat([V, NA], ignore_index=True)
        allrows += T.to_dict("records") + [dict(r, 排名="另表（起點不同）", 年化名次=np.nan) for r in side]
        hd = f"### {sg}｜{cal[x].date()}～{cal[y].date()}｜{RANK_NOTE[sg]}" + ("" if bt is not None else "（⚠ 大盤報酬指數未到庫：排名欄未定）")
        md += [hd, "", "| 排名 | 策略 | 年化 | 最大回落 | 比值 | 對大盤 |", "|---|---|---|---|---|---|"]
        for _, r in T.iterrows():
            md.append(f"| {r['排名']} | {r['策略']} | {pct(r['年化'])} | {pct(r['回落'])} | {f2(r['比值'])} | {r['對大盤']} |")
        md += ["", "年化名次（並列參考）：" + "、".join(f"{r['策略']} {int(r['年化名次'])}" for _, r in V.iterrows())]
        md += ["", "註：" + "；".join(f"{r['策略']}：{r['註']}" for _, r in T.iterrows() if r["註"])]
        for r in side:
            md += ["", f"另表（起點不同，⛔ 不並排比名次）：{r['策略']} {r['窗']} 年化 {pct(r['年化'])}、回落 {pct(r['回落'])}、比值 {f2(r['比值'])}、對大盤 {r['對大盤']}｜{r['註']}"]
        md.append("")
    pd.DataFrame(allrows).to_csv(os.path.join(OUT, "rank.csv"), index=False, float_format="%.10g", encoding="utf-8")
    open(os.path.join(OUT, "rank.md"), "w", encoding="utf-8").write("\n".join(md))
    log(f"[rank] {len(allrows)} 列 ⇒ rank.md／rank.csv｜基準 {trs or NA_TR}")
    return allrows


def lag_windows(cal, x, y, s0050, sTR):
    """B5：段首＋段內完整月底 ⇒ 滾動 12 個月窗；回 list[(pa, pb, r0050, rTR)]（位置）。"""
    ME, _ = PFQ.month_ends(cal)
    pts = [x] + [int(t) for t in ME if x < t <= y]
    out = []
    for k in range(12, len(pts)):
        pa, pb = pts[k - 12], pts[k]
        out.append((pa, pb, s0050[pb] / s0050[pa] - 1.0, sTR[pb] / sTR[pa] - 1.0))
    return out


def weak_core(cal, x, y, s0050, sTR, EQ):
    """B5 主體（純函式，_check 以合成序列驗）：EQ ＝ {策略: list[陣列（位置 ＝ cal）]}。"""
    W = lag_windows(cal, x, y, s0050, sTR)
    lag = [(pa, pb, r5, rT) for pa, pb, r5, rT in W if r5 < rT]
    per = []
    for pa, pb, r5, rT in lag:
        d = rT - r5
        grp = next(nm for lo, hi, nm in LAG_BINS if lo < d <= hi)
        rets = {}
        for nm, L in EQ.items():
            v = [e[pb] / e[pa] - 1.0 for e in L if np.isfinite(e[pa]) and np.isfinite(e[pb])]
            rets[nm] = float(np.median(v)) if v else np.nan
        rets["0050"], rets["大盤（報酬指數）"] = r5, rT
        okn = {k: v for k, v in rets.items() if np.isfinite(v)}
        order = sorted(okn, key=lambda k: -okn[k])
        per.append({"窗": f"{cal[pa].date()}～{cal[pb].date()}", "pa": pa, "pb": pb, "落後": d, "組": grp, "報酬": rets,
                    "名次": {k: order.index(k) + 1 for k in okn}})
    # 期間：連續落後的窗尾月份
    idx = [i for i, w in enumerate(W) if w[2] < w[3]]
    periods, run = [], []
    for i in idx:
        if run and i != run[-1] + 1:
            periods.append(run); run = []
        run.append(i)
    if run:
        periods.append(run)
    P = [{"窗尾起": str(cal[W[r[0]][1]].date()), "窗尾訖": str(cal[W[r[-1]][1]].date()), "窗數": len(r),
          "最大落後": float(max(W[i][3] - W[i][2] for i in r))} for r in periods]
    summ = {}
    for gname in ["全部"] + [nm for _, _, nm in LAG_BINS]:
        sel = [p for p in per if gname == "全部" or p["組"] == gname]
        if not sel:
            summ[gname] = {"窗數": 0}; continue
        names = sorted({k for p in sel for k in p["報酬"]})
        summ[gname] = {"窗數": len(sel), "策略": {}}
        for k in names:
            v = np.array([p["報酬"][k] for p in sel], float); v = v[np.isfinite(v)]
            rk = [p["名次"][k] for p in sel if k in p["名次"]]
            win = [p["報酬"][k] > p["報酬"]["大盤（報酬指數）"] for p in sel if np.isfinite(p["報酬"][k])]
            summ[gname]["策略"][k] = {"窗數": int(len(v)), "12 個月報酬平均": float(v.mean()) if len(v) else np.nan,
                                     "中位": float(np.median(v)) if len(v) else np.nan, "贏大盤窗比例": float(np.mean(win)) if win else np.nan,
                                     "名次平均": float(np.mean(rk)) if rk else np.nan}
    return {"滾動窗數": len(W), "落後窗數": len(lag), "期間": P, "分組": summ, "逐窗": per}


def weak(a):
    """第 4 項（B5）。"""
    trs = tr_source(a)
    if not trs:
        json.dump({"狀態": NA_TR, "讀法": "B5"}, open(os.path.join(OUT, "weak.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log(f"[weak] {NA_TR} ⇒ 不產出（⛔ 不以價格指數代替）")
        return None
    TR = read_series(trs)
    S, prow = {"基準": trs}, []
    for sg, (wn, a_, b_) in RANK_SEG.items():
        cal = world_cal(WORLD_DATA[wn]); x, y = seg_pos(cal, a_, b_)
        E = rank_universe(wn)
        EQ = {k: [on_cal(s, cal)[0] for s in v] for k, v in E.items() if k != "0050"}
        if sg in ("確認", "探索"):
            eq, d = six4_eq(a_ if sg == "確認" else "2018-01-15", b_)
            EQ["六四 v1"] = [on_cal(pd.Series(eq, index=d), cal)[0]]
        s50 = on_cal(E["0050"][0], cal)[0]; sT = on_cal(TR, cal)[0]
        R = weak_core(cal, x, y, s50, sT, EQ)
        R["缺權益"] = [k for k in ("營量 v1", "營飆 v1") if k not in E]
        S[sg] = {k: v for k, v in R.items() if k != "逐窗"}
        for p in R["期間"]:
            prow.append({"段": sg, **p})
    json.dump(S, open(os.path.join(OUT, "weak.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.DataFrame(prow).to_csv(os.path.join(OUT, "weak_periods.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log(f"[weak] ⇒ weak.json／weak_periods.csv")
    return S


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compare", "rejudge", "rank", "weak", "buildeq", "all", "reconcile"])
    ap.add_argument("--tr", default=None)
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--part", default=None)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    log(f"===== benchmark_rejudge {a.cmd}｜{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）")
    if a.cmd in ("compare", "all"):
        compare(a)
    if a.cmd in ("reconcile",):
        reconcile(a)
    if a.cmd in ("rejudge", "all"):
        rejudge(a)
    if a.cmd in ("rank", "all"):
        rank(a)
    if a.cmd in ("weak", "all"):
        weak(a)
    if a.cmd == "buildeq":
        buildeq(a)


if __name__ == "__main__":
    main()

"""前瞻紀錄：四型（PREREGP4）——每月第一個交易日（量測日）的【次一交易日】收盤後跑一次（那天才有進場開盤價），把當月合格母體全部檔的【原始輸入】與型號記進
backtest/forward/p4_types/（⛔ 只寫當月、不判定、不挑、不排名、不截斷；開檔後 24 個月才第一次判定）。

    python3 -m backtest.forward_p4 [--date YYYY-MM-DD] [--centers centers.json] [--out DIR] [--procs 4] [--limit N] [--seed-v0]

特徵全部 import p4_features（同一件事只有一份實作）。⚠ 讀 data/ ⇒ 一定要在 main 上跑（分支的 data/ 比 main 舊）。
〈二十八〉三個事後補不回來的欄位：asof（台北時戳）、data_sha（git rev-parse HEAD）、has_adj（當天有沒有還原因子）；
母體名單 universe.csv 只增不減（first_seen／last_seen）。型號欄：--centers 沒給就留空（中心到了再貼，⛔ 原始輸入不重算）。
冪等：同一個量測日已在 records.csv 就不再寫（回傳 0 列）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P
from . import research34 as R34

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(HERE, "forward", "p4_types")
RAW_COLS = P.FEATURES + ["shares_ok", "close", "open"]
_G: dict = {}


def _init(cal, rev_flags):
    _G["cal"] = cal; _G["rev_flags"] = rev_flags


def worker(args):
    sid, market, pos = args
    rf = _G["rev_flags"][sid] if sid in _G["rev_flags"].columns else None
    raw = P.stock_raw(sid, market, _G["cal"], rf)
    if raw is None or pos >= len(raw):
        return None
    row = raw.iloc[pos]
    if not bool(row["traded"]) or not (row["amt20"] >= P.LIQ_MIN):
        return {"stock_id": sid, "market": market, "eligible": False, "amt20": float(row["amt20"]) if pd.notna(row["amt20"]) else np.nan}
    adj = D.load_adj(sid)
    out = {"stock_id": sid, "market": market, "eligible": True, "has_adj": int(adj is not None and len(adj) > 0)}
    for c in RAW_COLS:
        out[c] = float(row[c]) if pd.notna(row[c]) else np.nan
    nxt = raw["open"].iloc[pos + 1] if pos + 1 < len(raw) else np.nan
    out["open_next"] = float(nxt) if pd.notna(nxt) else np.nan   # 進場價＝次一交易日開盤（還原）；本程式在進場日收盤後跑，所以拿得到
    return out


def parse_v0(path: str) -> list[str]:
    """策略線 09-11 開檔那份 markdown 的四型名單 ⇒ 代號清單（累積名單的種子）。"""
    t = open(path, encoding="utf-8").read()
    codes = []
    for body in re.findall(r"### \d_.*?\n```\n(.*?)```", t, re.S):
        codes += body.split()
    return codes


def update_universe(out: str, sids: list[str], date: str) -> pd.DataFrame:
    p = os.path.join(out, "universe.csv")
    u = pd.read_csv(p, dtype=str) if os.path.exists(p) else pd.DataFrame(columns=["stock_id", "first_seen", "last_seen"])
    u = u.set_index("stock_id")
    for s in sids:
        if s in u.index:
            u.loc[s, "last_seen"] = max(str(u.loc[s, "last_seen"]), date)
        else:
            u.loc[s] = [date, date]
    u = u.sort_index()
    assert len(u) >= (len(pd.read_csv(p, dtype=str)) if os.path.exists(p) else 0), "累積名單只增不減"
    u.reset_index().to_csv(p, index=False)
    return u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="量測日所在月份的任一天（預設：日曆最後一天所在月）；實際量測日＝該月第一個交易日")
    ap.add_argument("--centers", default=None, help="JSON：{version, centers(4×13), mu(13), sd(13)}；沒給就型號留空")
    ap.add_argument("--out", default=OUT_DEFAULT); ap.add_argument("--procs", type=int, default=4); ap.add_argument("--limit", type=int)
    ap.add_argument("--seed-v0", default=None, help="策略線 v0 markdown 路徑：把 612 檔種進累積名單（first_seen 2026-09-11）")
    ap.add_argument("--pub-day", type=int, default=10)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); t0 = time.time()
    cal = D.load_calendar()
    if a.seed_v0:
        codes = parse_v0(a.seed_v0); update_universe(a.out, codes, "2026-09-11")
        print(f"v0 種子：{len(codes)} 檔進累積名單（first_seen 2026-09-11）", file=sys.stderr)
    target = pd.Timestamp(a.date) if a.date else cal[-1]
    md = P.measurement_days(cal)
    cand = [i for i in md if cal[i].to_period("M") == target.to_period("M")]
    if not cand:
        print(f"⛔ {target.date()} 所在月沒有量測日（日曆最後一天 {cal[-1].date()}）", file=sys.stderr); sys.exit(1)
    pos = int(cand[0]); mdate = str(cal[pos].date())
    if pos + 1 >= len(cal):
        print(f"⛔ 量測日 {mdate} 的次一交易日還沒有資料（進場價要次日開盤）——等隔天再跑", file=sys.stderr); sys.exit(1)
    edate = str(cal[pos + 1].date())
    rec_p = os.path.join(a.out, "records.csv")
    if os.path.exists(rec_p) and (pd.read_csv(rec_p, dtype={"stock_id": str})["measure_date"] == mdate).any():
        print(f"量測日 {mdate} 已有紀錄，不重寫（冪等）", file=sys.stderr); return
    uni = D.load_universe()
    uni = uni[(uni["first_seen"] <= cal[pos]) & (uni["last_seen"] >= cal[pos])]
    if a.limit:
        uni = uni.head(a.limit)
    rev, _, _ = R34.load_revenue(); rev_flags = P.rev_hi24_flags(rev, cal, a.pub_day)
    jobs = [(r.stock_id, r.market, pos) for r in uni.itertuples()]
    rows = []
    with Pool(a.procs, initializer=_init, initargs=(cal, rev_flags)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, jobs, chunksize=8)):
            if r is not None:
                rows.append(r)
            if (i + 1) % 400 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", file=sys.stderr)
    allr = pd.DataFrame(rows); elig = allr[allr["eligible"]].set_index("stock_id").copy()
    n_pop = len(allr); n_el = len(elig)
    X = P.cross_section(elig[P.FEATURES])
    n_filled = elig[P.FEATURES].isna().sum(axis=1)
    label = pd.Series(np.nan, index=elig.index, dtype=object); cver = ""
    if a.centers:
        cj = json.load(open(a.centers, encoding="utf-8")); cver = str(cj.get("version", "?"))
        label = pd.Series(P.assign(X, np.array(cj["centers"]), np.array(cj["mu"]), np.array(cj["sd"])), index=elig.index)
    asof = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%dT%H:%M:%S+08:00")
    data_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    rec = pd.DataFrame({"measure_date": mdate, "entry_date": edate, "stock_id": elig.index, "market": elig["market"].to_numpy(),
                        "type": label.to_numpy(), "centers_version": cver, "n_filled": n_filled.to_numpy(), "has_adj": elig["has_adj"].to_numpy(),
                        "shares_ok": elig["shares_ok"].astype(int).to_numpy()})
    for c in P.FEATURES:
        rec[f"raw_{c}"] = elig[c].to_numpy(); rec[f"pct_{c}"] = X[c].to_numpy()
    rec["close"] = elig["close"].to_numpy(); rec["open_next"] = elig["open_next"].to_numpy()
    rec["asof"] = asof; rec["data_sha"] = data_sha
    rec = rec.sort_values("stock_id")
    header = not os.path.exists(rec_p)
    rec.to_csv(rec_p, mode="a", header=header, index=False)
    back = pd.read_csv(rec_p, dtype={"stock_id": str}); assert (back["measure_date"] == mdate).sum() == n_el, "寫完重讀，列數要對"
    u = update_universe(a.out, list(elig.index), mdate)
    tc = label.value_counts(dropna=False).to_dict() if a.centers else {"（型號未貼，中心未到）": n_el}
    log = [f"## {mdate}（跑於 {asof}，data_sha {data_sha[:12]}）",
           f"- 母體 {n_pop:,} → 過流動性門檻（近 20 日均額 ≥ {P.LIQ_MIN / 1e6:.0f} 百萬）{n_el:,} 檔；進場日 {edate}；型號 {tc}；centers_version「{cver}」",
           f"- has_adj=0 {int((elig['has_adj'] == 0).sum())} 檔；shares_ok=0 {int((elig['shares_ok'] == 0).sum())} 檔；補值欄數≥1 {int((n_filled >= 1).sum())} 檔（rev_hi24 缺 {int(elig['rev_hi24'].isna().sum())}、turn20 缺 {int(elig['turn20'].isna().sum())}）",
           f"- 累積名單 {len(u):,} 檔；{time.time() - t0:.0f}s", ""]
    with open(os.path.join(a.out, "runlog.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print("\n".join(log), file=sys.stderr)


if __name__ == "__main__":
    main()

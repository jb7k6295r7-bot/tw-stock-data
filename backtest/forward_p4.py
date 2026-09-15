"""前瞻紀錄：四型（PREREGP4）——每月第一個交易日（量測日）的【次一交易日】收盤後跑一次（那天才有進場開盤價），把當月合格母體全部檔的【原始輸入】與型號記進
backtest/forward/p4_types/（⛔ 只寫當月、不判定、不挑、不排名、不截斷；開檔後 24 個月才第一次判定）。

    python3 -m backtest.forward_p4 [--date YYYY-MM-DD] [--centers centers.json] [--out DIR] [--procs 4] [--limit N] [--seed-v0]

特徵全部 import p4_features（同一件事只有一份實作）。⚠ 讀 data/ ⇒ 一定要在 main 上跑（分支的 data/ 比 main 舊）。
〈二十八〉三個事後補不回來的欄位：asof（台北時戳）、data_sha（git rev-parse HEAD）、has_adj（當天有沒有還原因子）；
母體名單 universe.csv 只增不減（first_seen／last_seen）。型號欄：--centers 預設 auto＝讀 p4_types/centers_v3.json（策略線 09-15 12:52，sha256 前 16 23be85b004977222）；
檔不在就留空、大聲說；`--centers none` 強制留空。中心 JSON 收 centers_z（v3 投遞格式）或 centers。
⛔ v1 起始月下限 V1_START＝2026-10（0141 §三：2026-09-01 那期不補寫；資料庫線 1320 §三 (b)）：量測月早於它一律紅、不寫，除非 --allow-before-v1（只給自測用）。
冪等：同一個量測日已在 records.csv 就不再寫（回傳 0 列）。
"""
from __future__ import annotations

import argparse
import hashlib
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
V1_START = "2026-10"                                             # ⛔ 前瞻 v1 起始月；之前的月份不寫
CENTERS_DEFAULT = os.path.join(OUT_DEFAULT, "centers_v3.json")


def load_centers(path: str | None):
    """回傳 (centers, mu, sd, version) 或 None。path：None／"auto" ⇒ CENTERS_DEFAULT（不存在 ⇒ None）；"none" ⇒ None。"""
    if path in (None, "auto"):
        path = CENTERS_DEFAULT if os.path.exists(CENTERS_DEFAULT) else None
    elif path == "none":
        path = None
    if path is None:
        return None
    raw = open(path, "rb").read(); cj = json.loads(raw.decode("utf-8"))
    C = cj.get("centers_z", cj.get("centers"))
    order = cj.get("feature_order")
    if order is not None and list(order) != P.FEATURES:
        raise SystemExit(f"⛔ 中心的 feature_order 與 p4_features.FEATURES 不同：{order}")
    ver = str(cj.get("version") or cj.get("schema") or "?") + "@" + hashlib.sha256(raw).hexdigest()[:16]
    return np.array(C, float), np.array(cj["mu"], float), np.array(cj["sd"], float), ver
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
    if not bool(row["traded"]) or not (row["amt20"] >= P.LIQ_MIN) or int(row["bars"]) < P.MIN_BARS:   # v3 補件 §3-1：bars ≥ MIN_BARS 才進母體
        return {"stock_id": sid, "market": market, "eligible": False, "amt20": float(row["amt20"]) if pd.notna(row["amt20"]) else np.nan, "bars": int(row["bars"]),
                "liq_ok": bool(pd.notna(row["amt20"]) and row["amt20"] >= P.LIQ_MIN)}
    adj = D.load_adj(sid)
    out = {"stock_id": sid, "market": market, "eligible": True, "has_adj": int(adj is not None and len(adj) > 0), "bars": int(row["bars"]), "liq_ok": True}
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
    ap.add_argument("--centers", default="auto", help="auto＝p4_types/centers_v3.json（不在就留空）；none＝強制留空；或給路徑")
    ap.add_argument("--allow-before-v1", action="store_true", help="⚠ 只給自測：允許量測月早於 V1_START")
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
    if str(cal[pos].to_period("M")) < V1_START and not a.allow_before_v1:
        print(f"⛔ 量測月 {cal[pos].to_period('M')} 早於前瞻 v1 起始月 {V1_START}——不寫（那不是前瞻；要跑舊月份是回溯，用 researchp4）", file=sys.stderr); sys.exit(2)
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
    cen = load_centers(a.centers)
    if cen is not None:
        C_, mu_, sd_, cver = cen
        label = pd.Series(P.assign(X, C_, mu_, sd_), index=elig.index)
    else:
        print("⚠ 沒有中心檔 ⇒ 型號留空（p4_types/centers_v3.json 不在這個 ref 上？）", file=sys.stderr)
    asof = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%dT%H:%M:%S+08:00")
    data_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    rec = pd.DataFrame({"measure_date": mdate, "entry_date": edate, "stock_id": elig.index, "market": elig["market"].to_numpy(),
                        "type": label.to_numpy(), "centers_version": cver, "n_filled": n_filled.to_numpy(), "has_adj": elig["has_adj"].to_numpy(),
                        "shares_ok": elig["shares_ok"].astype(int).to_numpy(), "bars": elig["bars"].astype(int).to_numpy()})
    for c in P.FEATURES:
        rec[f"raw_{c}"] = elig[c].to_numpy(); rec[f"pct_{c}"] = X[c].to_numpy()
    rec["close"] = elig["close"].to_numpy(); rec["open_next"] = elig["open_next"].to_numpy()
    rec["asof"] = asof; rec["data_sha"] = data_sha
    rec = rec.sort_values("stock_id")
    header = not os.path.exists(rec_p)
    rec.to_csv(rec_p, mode="a", header=header, index=False)
    back = pd.read_csv(rec_p, dtype={"stock_id": str}); assert (back["measure_date"] == mdate).sum() == n_el, "寫完重讀，列數要對"
    u = update_universe(a.out, list(elig.index), mdate)
    tc = label.value_counts(dropna=False).to_dict() if cen is not None else {"（型號未貼，沒有中心檔）": n_el}
    log = [f"## {mdate}（跑於 {asof}，data_sha {data_sha[:12]}）",
           f"- 母體 {n_pop:,} → 過流動性門檻（近 20 日均額 ≥ {P.LIQ_MIN / 1e6:.0f} 百萬）{int(allr['liq_ok'].sum()):,} 檔 → 再過 bars ≥ {P.MIN_BARS} 閘門 {n_el:,} 檔（擋掉 {int((allr['liq_ok'] & (allr['bars'] < P.MIN_BARS)).sum())} 檔）；進場日 {edate}；型號 {tc}；centers_version「{cver}」",
           f"- has_adj=0 {int((elig['has_adj'] == 0).sum())} 檔；shares_ok=0 {int((elig['shares_ok'] == 0).sum())} 檔；補值欄數≥1 {int((n_filled >= 1).sum())} 檔（rev_hi24 缺 {int(elig['rev_hi24'].isna().sum())}、turn20 缺 {int(elig['turn20'].isna().sum())}）",
           f"- 累積名單 {len(u):,} 檔；{time.time() - t0:.0f}s", ""]
    with open(os.path.join(a.out, "runlog.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")
    print("\n".join(log), file=sys.stderr)


if __name__ == "__main__":
    main()

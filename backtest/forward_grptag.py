# -*- coding: utf-8 -*-
"""營量 v1 每日名單加「族群營收轉強」標記——前瞻紀錄（只標記、不改買法）。回測線，2026-11-11。
登錄：台股策略線 seq1（sha 2f4cf5174864e620，3279 B）〈營量每日名單加族群營收轉強標記_只標記不改買法_前瞻紀錄登錄〉
發號：裁定線 seq505 §一（判定 1 格＝營量 ⇒ N_單筆 ＋1；營飆只描述；起點後新資料才算；半年只報筆數、不報報酬；2030-12 仍 < 24 就停排）

⛔ 只標記：不改營量／營飆選股程式、不動策略鎖（本檔不在鎖內、只 import）、⛔ 不進 LINE（不接 run_daily_list.sh、不寫 _營量觀察/）。
⛔ 本檔不讀、不算任何報酬（滿 24 個月前只報筆數與月數；判定另開正式程式、另請閘門）。
⛔ 不寫第二份實作：
   成交 ＝ 照規則簿 backtest/forward/yl_rule/positions.csv（forward_yl 寫的；只讀）
   營收期別 ＝ list_prereg10.build_panel 面板＋researchGroupRevUp_freq.cand_period（＝ research13.and_flags 同式：訊號日當下最新一期、距離 ≤ 45）
   分群 ＝ 產業 seq112 clusters_by_year（researchGroupRevUp_freq.load_industry／ind_tables）
   旗標 ＝ 產業 group_month_flags 有該 (營收月, 分群年, 群) 列就用；沒有（產業檔之後的新營收月）⇒ 產業分群＋本機營收 README 規則
          （researchGroupRevUp_freq.readme_up；與產業檔逐列 100% 相同，commit 8f826608e5 的 S3）

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_grptag [--procs 2] [--dry]

═══ 讀法（寫死於 2026-11-11（台北），標記第一筆之前；★ ＝ 登錄沒寫清楚、執行者定）═══
 T1 對象：positions.csv 中 策略 ∈ {營量v1（判定）, 營飆v1（只描述）}、有進場日的列（持有中、已出場都算）；鍵 ＝ (策略, 代號, 進場日)
 T2 起點：該筆的營收期別 ≥ 2026-10（登錄「2026-10 期營收起第一筆照規則成交」）；期別 < 2026-10 ⇒ 不寫入（只在 runlog 報筆數）
 T3 ★ 分群年 ＝ cyear(期別)（README 第 4 點：營收月 m 的訊號日在 m＋1 月 ⇒ 看 m＋1 月的年；2026-12 期 ⇒ 2027 年分群）
 T4 ★ 族群營收轉強「是」＝ 個股在該年分群、群 used＝1、該 (期別, 分群年, 群) 旗標＝1；不在分群或群 used＝0 ⇒「否」（同 seq2 apply_flags）
 T5 ★ 分群年還沒有產業分群檔 ⇒ 該筆標「待分群檔」、先不寫入（下次再補）；產業逾期（每年 1 月第 10 個交易日）⇒ 改自建 v2 並報一致率（另件，屆時再加）
 T6 ★ 凍結：每筆第一次寫入就凍結（含 n_with_revenue、n_new_high、旗標來源、寫入時間、main sha）；之後重跑只追加新筆，
      對已寫入的筆重算，若與凍結不同 ⇒ runlog 記差異、⛔ 不改凍結（同照規則簿）
 T7 有效樣本（登錄）＝「是」「否」兩批都有成交的不同訊號月數（同月多筆算一月）；訊號月 ＝ 訊號日所在月 ★
輸出（只追加）：backtest/forward/yl_grptag/tags.csv、runlog.md
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import data as D                              # noqa: E402
from backtest import researchGroupRevUp_freq as G           # noqa: E402  旗標、期別（⛔ 不另寫）

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BOOK = os.path.join(HERE, "forward", "yl_rule", "positions.csv")
OUTD = os.environ.get("GT_OUT_DIR") or os.path.join(HERE, "forward", "yl_grptag")
START_PERIOD = os.environ.get("GT_START_TEST") or "2026-10"           # GT_START_TEST 只給測試（配 GT_OUT_DIR 指到暫存）
STOP_MONTH = "2030-12"
NEED_MONTHS = 24
STRATS = {"營量v1": "判定", "營飆v1": "只描述"}
COLS = ["策略", "角色", "代號", "名稱", "訊號日", "進場日", "訊號月", "營收期別", "分群年", "群號", "群used",
        "n_with_revenue", "n_new_high", "族群營收轉強", "旗標來源", "main", "寫入時間"]


def now_tpe():
    return subprocess.run(["bash", "-c", "TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S'"], capture_output=True, text=True).stdout.strip()


def data_dir():
    sha = subprocess.run(["git", "-C", REPO, "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    d = os.path.expanduser(f"~/h2data/{sha}/data")
    if not os.path.isdir(d):
        raise SystemExit(f"⛔ 沒有 {d}（每日名單會 archive 最新 main；或先 git archive）")
    return sha, d


def load_trades():
    P = pd.read_csv(BOOK, dtype=str, encoding="utf-8-sig")
    P = P[P["策略"].isin(STRATS) & P["進場日"].notna() & (P["進場日"].str.len() > 0)].copy()
    return P[["策略", "代號", "名稱", "訊號日", "進場日"]].reset_index(drop=True)


def periods_for(P, cal, procs, log):
    """訊號日當下的營收期別（cand_period ＝ and_flags 同式）。"""
    from backtest import list_prereg10 as LP
    stocks, uni = LP.universe()
    need = set(P["代號"])
    uni = uni[uni["stock_id"].isin(need)]
    panel, _, _ = LP.build_panel(cal, uni, log)
    S = pd.DataFrame({"sid": P["代號"].to_numpy(), "pos": [int(cal.get_loc(pd.Timestamp(d))) for d in P["訊號日"]]})
    per, nohi = G.cand_period(S, panel)
    return per, nohi


def flag_tables():
    cl, gm, sg = G.load_industry()
    got, ok = G.check_industry(cl, gm, sg)
    if not ok:
        raise SystemExit(f"⛔ 產業分群檔筆數不符：{got}")
    memi, upi = G.ind_tables(cl, gm)
    stat_i = {(m, int(Y), int(g)): (int(a), int(b)) for m, Y, g, a, b in
              zip(gm["revenue_month"], gm["cluster_year"], gm["group"], gm["n_with_revenue"], gm["n_new_high"])}
    rev = G.load_revenue()
    _, hib = G.hi24_tables(rev)
    up3, stat3 = G.readme_up(memi, rev, hib)
    # 自檢：本機 README 規則對產業檔逐列（應 100%）
    keys = list(upi)
    agree = sum(up3.get(k) == upi[k] for k in keys)
    return memi, upi, stat_i, up3, stat3, (agree, len(keys))


def tag_rows(P, per, memi, upi, stat_i, up3, stat3, sha, ts):
    rows, pending, before = [], [], 0
    for r, p in zip(P.itertuples(index=False), per):
        if not isinstance(p, str):
            pending.append((r.策略, r.代號, r.進場日, "查無營收期別")); continue
        if p < START_PERIOD:
            before += 1; continue
        Y = G.cyear(p)
        if Y not in memi:
            pending.append((r.策略, r.代號, r.進場日, f"待 {Y} 年分群檔")); continue
        c = memi[Y].get(r.代號)
        k = (p, Y, c[0]) if c else None
        if c is None or not c[1]:
            flag, src, a, b = False, ("不在分群母體" if c is None else "群不足 4 檔（used=0）"), None, None
        elif k in upi:
            flag, src = upi[k], "產業 group_month_flags"
            a, b = stat_i[k]
        elif k in up3:
            flag, src = up3[k], "產業分群＋本機營收 README 規則"
            a, b = stat3[k]
        else:
            pending.append((r.策略, r.代號, r.進場日, f"查無 {k} 旗標")); continue
        rows.append({"策略": r.策略, "角色": STRATS[r.策略], "代號": r.代號, "名稱": r.名稱, "訊號日": r.訊號日, "進場日": r.進場日,
                     "訊號月": r.訊號日[:7], "營收期別": p, "分群年": Y, "群號": (c[0] if c else ""), "群used": (int(c[1]) if c else ""),
                     "n_with_revenue": ("" if a is None else a), "n_new_high": ("" if b is None else b),
                     "族群營收轉強": "是" if flag else "否", "旗標來源": src, "main": sha[:10], "寫入時間": ts})
    return pd.DataFrame(rows, columns=COLS), pending, before


def merge_frozen(new, path):
    """T6：已寫入的筆不改；回 (追加後全表, 新增筆, 與凍結不同的訊息)。"""
    key = ["策略", "代號", "進場日"]
    if os.path.exists(path):
        old = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    else:
        old = pd.DataFrame(columns=COLS)
    newS = new.astype(str)
    ok = set(map(tuple, old[key].to_numpy())) if len(old) else set()
    isnew = np.array([tuple(x) not in ok for x in newS[key].to_numpy()], bool)
    diffs = []
    if len(old):
        m = old.merge(newS, on=key, suffixes=("_凍", "_重"))
        for r in m.itertuples(index=False):
            d = r._asdict()
            for c in ("營收期別", "族群營收轉強", "n_with_revenue", "n_new_high"):
                if str(d[f"{c}_凍"]) != str(d[f"{c}_重"]):
                    diffs.append(f"{d['策略']} {d['代號']} {d['進場日']} {c}：凍結 {d[f'{c}_凍']}｜重算 {d[f'{c}_重']}（照凍結）")
    add = newS[isnew]
    full = pd.concat([old, add], ignore_index=True)
    return full, add, diffs


def counts(T):
    """登錄：滿 24 個月前只報筆數與月數（⛔ 不報報酬）。"""
    out = {}
    for st in STRATS:
        x = T[T["策略"] == st]
        y, n = x[x["族群營收轉強"] == "是"], x[x["族群營收轉強"] == "否"]
        both = sorted(set(y["訊號月"]) & set(n["訊號月"]))
        out[st] = {"筆數": len(x), "是": len(y), "否": len(n), "兩批都有的不同訊號月數": len(both), "門檻": NEED_MONTHS}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--dry", action="store_true", help="只印、不寫檔")
    a = ap.parse_args(argv)
    ts = now_tpe()
    sha, DATA = data_dir()
    D.DATA = DATA
    cal = D.load_calendar()
    log = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)  # noqa: E731
    P = load_trades()
    log(f"照規則簿成交 {len(P)} 筆（{dict(P['策略'].value_counts())}）｜資料日 {cal[-1].date()}｜main {sha[:10]}")
    memi, upi, stat_i, up3, stat3, (ag, nk) = flag_tables()
    log(f"本機 README 規則對產業 group_month_flags 逐列一致 {ag}/{nk}")
    if ag != nk:
        raise SystemExit("⛔ 本機旗標與產業檔不一致，先查")
    per, nohi = periods_for(P, cal, a.procs, log)
    T, pending, before = tag_rows(P, per, memi, upi, stat_i, up3, stat3, sha, ts)
    path = os.path.join(OUTD, "tags.csv")
    full, add, diffs = merge_frozen(T, path)
    C = counts(full)
    lines = [f"## {ts}（台北）資料日 {cal[-1].date()}｜main {sha[:10]}", "",
             f"- 成交 {len(P)} 筆；起點（營收期別 {START_PERIOD}）前 {before} 筆不算；本次新標 {len(add)} 筆；待補 {len(pending)} 筆"
             + (f"（{pending}）" if pending else ""),
             f"- 本機 README 規則對產業檔逐列一致 {ag}/{nk}；期別取得時面板最新列非營收新高 {nohi} 筆（描述）"]
    for st, c in C.items():
        lines.append(f"- {st}（{STRATS[st]}）：累計 {c['筆數']} 筆（是 {c['是']}／否 {c['否']}）；兩批都有的不同訊號月數 {c['兩批都有的不同訊號月數']}／{NEED_MONTHS}（⛔ 不報報酬）")
    for x in diffs:
        lines.append(f"- 重算差異：{x}")
    if cal[-1].strftime("%Y-%m") > STOP_MONTH and C["營量v1"]["兩批都有的不同訊號月數"] < NEED_MONTHS:
        lines.append(f"- ⚠ 已過 {STOP_MONTH} 仍 < {NEED_MONTHS} 月 ⇒ 本方法範圍內測不到、停排（登錄）")
    txt = "\n".join(lines) + "\n"
    print(txt)
    if a.dry:
        return
    os.makedirs(OUTD, exist_ok=True)
    full.to_csv(path, index=False, encoding="utf-8-sig")
    rl = os.path.join(OUTD, "runlog.md")
    head = "" if os.path.exists(rl) else ("# 營量名單族群營收轉強標記 runlog（backtest/forward_grptag.py；只追加；⛔ 不報報酬）\n\n"
                                         "登錄 台股 seq1 sha 2f4cf5174864e620｜裁定 seq505 §一（N_單筆 ＋1）\n\n")
    with open(rl, "a", encoding="utf-8") as f:
        f.write(head + txt + "\n")


if __name__ == "__main__":
    main()

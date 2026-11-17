# -*- coding: utf-8 -*-
"""集保 400 張以上大戶比例 4 週升幅前 5%：買進抱 60 日（全收版、10 檔版）組合層 seq1（台股策略線 sha b6c00cb614caa84e；裁定 seq507 發號）
——【頻率表】⛔ 本檔不讀、不算、不印任何報酬（只用日期、檔數、份數；價格檔只讀 amount 與 open 是否存在）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigHolderRise

═══ 訊號（照情報線研究 #76 的 B 格；#76 程式 `claude/bigholder_rise_code_20261117.md` 在情報線專案，本機與三個 GitHub repo 都找不到 ⇒ 依登錄與情報信文字重寫，見 ★）═══
 資料：tw-stock-data commit e2fdcdef9（＝ #76 同一 sha）git archive 到 ~/h2data/<sha>/data（唯讀）
 大戶比例 ＝ 集保第 12～15 級 shares 合計 ÷ 第 1～15 級 shares 合計（★ 用 shares 欄、不用四捨五入到 0.01 的 pct 欄）
 4 週升幅 ＝ 比例(d) − 比例(d′)，d′ ＝ 集保資料日中與 d−28 日曆日相差 ≤ 3 日的那一週（★ 差值、百分點；找不到 d′ ⇒ 該週不算）
 母體（每週）：stocks.csv kind＝stock、market∈{twse,tpex}、四碼代號（含已下市）；前 20 日均成交額 ≥ 5,000 萬
   ★ 前 20 日 ＝ 資料日 d 當天或之前最後一個交易日往回 20 個交易日（含），amount 欄（元，官方日成交金額），沒成交日記 0
   ★ 兩週比例都要有值
 B ＝ 升幅 ≥ 當週母體橫斷面第 95 百分位（numpy linear）且 > 0
 進場日 ＝ 資料日 +2 日曆日當天或之後第一個交易日（TWSE 日曆），開盤；出場 ＝ data.exit_pos(進場, 60) 收盤
   ★ 進場日當天沒有開盤價（停牌等）⇒ 買不到、不補，件數照報
 段：依進場日 探索 2018-11-01～2021-12-31｜確認 2022-01-01～資料尾

═══ 組合模擬（只用進出日期、檔數、份數）═══
 全收版：12 份輪動；每週用一份「已出場（出場根 < 本次進場根）」的空份，等權買進當週全部買得到的訊號、抱滿 60 根；
   當週沒有訊號 ⇒ 不動用（現金）。★ 12 份全都還沒出場 ⇒ 本週不買、件數照報
   ★〔另一讀法：死板輪 週序 mod 12；60 個交易日因假日常超過 12 週 ⇒ 輪到的那份常未出場，略過週數另報（rigid_conflict）〕
 10 檔版：最多 10 檔、每檔 10%；進場日空位 ＝ 10 − 持有中（出場根 ≥ 進場根）檔數；從當週買得到的訊號依升幅大到小補；
   ★ 已持有的同一檔不重複買（件數照報）
 ★ 兩段各自從空倉開始模擬，指標只算段內交易日；資料尾還沒到期的部位算持有到資料尾
 現金比例 ＝ 空份數 ÷ 份數（全收 12、10 檔 10）逐日平均；年換手 ＝ 買進筆數 ÷ 段長（日曆年）；份數換手 ＝ 買進資金份額合計 ÷ 段長

═══ 與營量 v1 的重疊 ═══
 正式產物 backtest/resultsYFallin/trades_W.csv.gz 世界「主」帳 YL（營量 v1：無閘、H60、20 檔、relvol）buy／sell 列，
   日期 ＝ daily_W.csv.gz 同世界同帳 t→日期（2015-01-05～2026-09-24）；只讀 世界、帳、side、t、sid 欄
 ① 持倉重疊：訊號股進場日當天，營量 v1 正持有同一檔（買進日 ≤ 進場日 ≤ 賣出日）
 ② 新買重疊：營量 v1 在訊號進場日前後 5 個交易日內新買同一檔
 ③ 候選重疊（只 2025-08～2026-06）：backtest/resultsYLlist/營量v1名單＋營量v1未入選候選（20260928）任一列，同檔、候選進場日在訊號進場日前後 5 個交易日內
 分母 ＝ 進場日 ≤ 2026-09-24 的訊號／買進（③ 只取進場日在 2025-08-01～2026-06-30）

輸出 backtest/resultsBigHolderRise/freq/：頻率表.md、freq.csv、weekly.csv、signals.csv（訊號清單，無報酬）、equiv76.md、data_check.csv、run.log
"""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np
import pandas as pd

from backtest import data as D

SHA = "e2fdcdef97bd527f8c4d754bb3657434e9a9851e"
DATA = os.path.expanduser(f"~/h2data/{SHA}/data")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsBigHolderRise", "freq")
YFA = os.path.join(HERE, "resultsYFallin")
YLL = os.path.join(HERE, "resultsYLlist")
AMT_MIN = 5e7
Q = 0.95
HOLD = 60
SEGS = {"探索": ("2018-11-01", "2021-12-31"), "確認": ("2022-01-01", "2099-12-31")}
LOGS: list[str] = []


def log(s=""):
    print(s, flush=True); LOGS.append(str(s))


# ───────── 集保 ─────────
def load_tdcc():
    parts = []
    for f in sorted(glob.glob(os.path.join(DATA, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "shares"])
        x["date"] = x["date"].astype(str); x["stock_id"] = x["stock_id"].astype(str); x["src"] = 0
        parts.append(x)
    for f in sorted(glob.glob(os.path.join(DATA, "tdcc", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "level", "shares"])
        x["src"] = 1; parts.append(x)
    A = pd.concat(parts, ignore_index=True)
    A = A[A["stock_id"].str.fullmatch(r"\d{4}")]
    A["level"] = A["level"].astype(int); A["shares"] = pd.to_numeric(A["shares"], errors="coerce")
    A = A[A["level"].between(1, 15)]
    A = A.sort_values("src").drop_duplicates(["date", "stock_id", "level"], keep="last")
    g = A.groupby(["date", "stock_id"])
    tot = g["shares"].sum()
    big = A[A["level"] >= 12].groupby(["date", "stock_id"])["shares"].sum().reindex(tot.index).fillna(0)
    R = (big / tot.replace(0, np.nan)).rename("ratio").reset_index()
    R["date"] = pd.to_datetime(R["date"])
    return R


def lag_map(dates):
    """每個資料日 d ⇒ 與 d−28 相差 ≤ 3 日的資料日（最近者）；沒有 ⇒ NaT。"""
    ds = np.array(sorted(dates), dtype="datetime64[ns]")
    out = {}
    for d in ds:
        tgt = d - np.timedelta64(28, "D")
        j = np.searchsorted(ds, tgt)
        best = None
        for k in (j - 1, j):
            if 0 <= k < len(ds):
                gap = abs((ds[k] - tgt) / np.timedelta64(1, "D"))
                if gap <= 3 and (best is None or gap < best[0]):
                    best = (gap, ds[k])
        out[pd.Timestamp(d)] = pd.Timestamp(best[1]) if best else pd.NaT
    return out


# ───────── 價量（只讀 amount、open 是否存在）─────────
def load_amount_open(sids, cal):
    n = len(cal); AMT = {}; OPN = {}
    for s in sids:
        p = os.path.join(DATA, "stocks", f"{s}.csv")
        if not os.path.exists(p):
            continue
        r = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "amount"])
        r["date"] = pd.to_datetime(r["date"]); r = r.drop_duplicates("date").set_index("date")
        a = pd.to_numeric(r["amount"], errors="coerce").reindex(cal).fillna(0).to_numpy(float)
        o = pd.to_numeric(r["open"], errors="coerce").reindex(cal).to_numpy(float)
        AMT[s] = pd.Series(a).rolling(20, min_periods=20).mean().to_numpy()
        OPN[s] = np.isfinite(o) & (o > 0)
    return AMT, OPN


# ───────── 模擬（只用位置）─────────
def sim_full(W, cal, last_pos, seg_lo, seg_hi):
    """全收版：W ＝ 段內週列表（dict：d, e, buys[sid...]）。回 cohorts、positions、conflicts。"""
    slot_exit = [-1] * 12; cohorts = []; pos = []; conflict = []
    for w in W:
        e = w["e"]
        free = [i for i in range(12) if slot_exit[i] < e]
        if not w["buys"]:
            cohorts.append({"d": w["d"], "slot": -1, "n": 0, "e": e}); continue
        if not free:
            conflict.append({"d": w["d"], "slot": -1, "n": len(w["buys"])}); continue
        k = free[0]
        x = D.exit_pos(e, HOLD)
        slot_exit[k] = x
        cohorts.append({"d": w["d"], "slot": k, "n": len(w["buys"]), "e": e, "x": x})
        for s in w["buys"]:
            pos.append({"sid": s, "e": e, "x": x, "w": 1 / 12 / len(w["buys"]), "slot": k})
    return cohorts, pos, conflict


def rigid_conflict(W):
    """另一讀法：死板輪（週序 mod 12）時，輪到的那份還沒出場的週數。"""
    slot_exit = [-1] * 12; n = 0
    d0 = W[0]["d"] if W else None
    for w in W:
        if not w["buys"]:
            continue
        k = int(round((w["d"] - d0).days / 7)) % 12
        if slot_exit[k] >= w["e"]:
            n += 1; continue
        slot_exit[k] = D.exit_pos(w["e"], HOLD)
    return n


def sim_ten(W):
    held = []  # (sid, e, x)
    pos = []; st = {"free_no_sig": 0, "full_skip": 0, "dup_skip": 0, "free_weeks": 0, "weeks": 0}
    for w in W:
        e = w["e"]; st["weeks"] += 1
        held = [h for h in held if h[2] >= e]
        free = 10 - len(held)
        hs = {h[0] for h in held}
        cand = [s for s in w["buys_ranked"] if s not in hs]
        st["dup_skip"] += len(w["buys_ranked"]) - len(cand)
        if free > 0:
            st["free_weeks"] += 1
            if not w["buys_ranked"]:
                st["free_no_sig"] += 1
        take = cand[:max(free, 0)]
        st["full_skip"] += len(cand) - len(take)
        x = D.exit_pos(e, HOLD)
        for s in take:
            held.append((s, e, x)); pos.append({"sid": s, "e": e, "x": x, "w": 0.1})
    return pos, st


def daily_occupancy(pos, lo, hi, nslot, kind, cohorts=None):
    """lo..hi（含）每個交易日：持有部位數、不同檔數、空份比例。"""
    n = hi - lo + 1
    cnt = np.zeros(n); occ = np.zeros(n)
    sets = [set() for _ in range(n)]
    for p in pos:
        a = max(p["e"], lo); b = min(p["x"], hi)
        if a > b:
            continue
        cnt[a - lo:b - lo + 1] += 1
        for t in range(a, b + 1):
            sets[t - lo].add(p["sid"])
    if kind == "full":
        for c in cohorts or []:
            if c.get("n", 0) == 0 or "x" not in c:
                continue
            a = max(c["e"], lo); b = min(c["x"], hi)
            if a <= b:
                occ[a - lo:b - lo + 1] += 1
    else:
        occ = cnt.copy()
    dist = np.array([len(s) for s in sets], float)
    cash = 1 - np.minimum(occ, nslot) / nslot
    return cnt, dist, cash


# ───────── 營量 v1 ─────────
def load_yl():
    d = pd.read_csv(os.path.join(YFA, "daily_W.csv.gz"), usecols=["世界", "帳", "t", "日期"])
    d = d[(d["世界"] == "主") & (d["帳"] == "YL")]
    t2d = dict(zip(d["t"].astype(int), pd.to_datetime(d["日期"])))
    T = pd.read_csv(os.path.join(YFA, "trades_W.csv.gz"), usecols=["世界", "帳", "side", "t", "sid"], dtype={"sid": str})
    T = T[(T["世界"] == "主") & (T["帳"] == "YL")].sort_values("t")
    yl_end = max(t2d.values())
    iv = {}; buys = {}
    for s, g in T.groupby("sid"):
        b = g[g["side"] == "buy"]["t"].astype(int).tolist(); se = g[g["side"] == "sell"]["t"].astype(int).tolist()
        for bt in b:
            st = next((x for x in se if x > bt), None)
            bd = t2d[bt]; sd = t2d.get(st, yl_end) if st is not None else yl_end
            iv.setdefault(s, []).append((bd, sd)); buys.setdefault(s, []).append(bd)
    cands = []
    for f in glob.glob(os.path.join(YLL, "營量v1名單_*.csv")) + glob.glob(os.path.join(YLL, "營量v1未入選候選_*.csv")):
        c = pd.read_csv(f, usecols=["進場日", "代號"], dtype={"代號": str}, encoding="utf-8-sig")
        cands.append(c)
    C = pd.concat(cands); C["進場日"] = pd.to_datetime(C["進場日"])
    cset = {}
    for s, g in C.groupby("代號"):
        cset[s] = sorted(g["進場日"].tolist())
    return iv, buys, cset, yl_end, (C["進場日"].min(), C["進場日"].max(), len(C), len(glob.glob(os.path.join(YLL, "營量v1*候選*.csv"))))


def overlap(rows, cal, iv, buys, cset, yl_end):
    """rows：list of (sid, entry_pos)。回 dict。"""
    cpos = {d: i for i, d in enumerate(cal)}
    n = n1 = n2 = 0; m3 = h3 = 0
    for s, e in rows:
        ed = cal[e]
        if ed > yl_end:
            continue
        n += 1
        if any(a <= ed <= b for a, b in iv.get(s, [])):
            n1 += 1
        if any(abs(cpos.get(bd, -10**6) - e) <= 5 for bd in buys.get(s, [])):
            n2 += 1
        if pd.Timestamp("2025-08-01") <= ed <= pd.Timestamp("2026-06-30"):
            m3 += 1
            if any(abs(cpos.get(cd, -10**6) - e) <= 5 for cd in cset.get(s, [])):
                h3 += 1
    f = lambda a, b: (a / b if b else np.nan)
    return {"n": n, "持倉重疊": n1, "持倉重疊比": f(n1, n), "新買±5日重疊": n2, "新買±5日重疊比": f(n2, n),
            "候選n_2025-08~2026-06": m3, "候選±5日重疊": h3, "候選±5日重疊比": f(h3, m3)}


# ───────── 事件資料可得性 ─────────
def event_inventory(sig):
    M = os.path.join(DATA, "meta")
    out = []
    E = pd.read_csv(os.path.join(M, "seo_cb_events", "seo_cb_events.csv"), dtype=str)
    E["date"] = pd.to_datetime(E["date"]); E["y"] = E["date"].dt.year
    for k, msk in {"現金增資決議（一般，非私募非承銷）": (E["class"] == "seo") & (E["private"] != "1") & (E["ipo"] != "1"),
                   "私募決議（現增＋可轉債）": E["private"] == "1",
                   "可轉債發行決議（非私募）": (E["class"] == "cb") & (E["private"] != "1")}.items():
        x = E[msk]
        out.append({"類": k, "來源": "data/meta/seo_cb_events/seo_cb_events.csv（news 主旨分類；決議日）",
                    "起": str(x["date"].min().date()), "迄": str(x["date"].max().date()), "筆數": len(x),
                    "2018-11起筆數": int((x["date"] >= "2018-11-01").sum())})
    P = pd.read_csv(os.path.join(M, "placement_detail", "placement_detail.csv"), dtype=str)
    P["decide_date"] = pd.to_datetime(P["decide_date"], errors="coerce")
    out.append({"類": "私募明細（僅 E3 名單公司）", "來源": "data/meta/placement_detail/placement_detail.csv",
                "起": str(P["decide_date"].min().date()), "迄": str(P["decide_date"].max().date()), "筆數": len(P),
                "2018-11起筆數": int((P["decide_date"] >= "2018-11-01").sum())})
    # 可轉債轉換：沒有專表 ⇒ news 主旨關鍵字盤點（含「轉換」且含「普通股」或「轉換公司債」，且含 發行新股／換發／轉換股數／增資 之一）
    nf = sorted(glob.glob(os.path.join(DATA, "mops", "news", "*.csv")))
    N = pd.concat([pd.read_csv(f, dtype=str, usecols=["date", "stock_id", "subject"]) for f in nf])
    sub = N["subject"].fillna("").str.replace(r"\s", "", regex=True)
    conv = sub.str.contains("轉換") & sub.str.contains("公司債") & sub.str.contains("普通股|發行新股|換發|轉換股數|股本")
    x = N[conv]; xd = pd.to_datetime(x["date"])
    out.append({"類": "可轉債轉換（無專表；news 主旨關鍵字代理）", "來源": "data/mops/news/<年>.csv 主旨含 轉換＋公司債＋(普通股|發行新股|換發|轉換股數|股本)",
                "起": str(xd.min().date()), "迄": str(xd.max().date()), "筆數": len(x), "2018-11起筆數": int((xd >= "2018-11-01").sum())})
    out.append({"類": "ETF 申贖成分調整", "來源": "資料庫沒有 ETF 申購買回清單（PCF）；只有 data/meta/tw50（0050 成分異動）、data/universe/etfsplit（ETF 分割）",
                "起": "", "迄": "", "筆數": 0, "2018-11起筆數": 0})
    T50 = pd.read_csv(os.path.join(M, "tw50", "tw50_changes.csv"), dtype=str)
    dc = next((c for c in T50.columns if "date" in c.lower() or "日" in c), T50.columns[0])
    td = pd.to_datetime(T50[dc], errors="coerce")
    out.append({"類": "（旁證）0050 成分異動", "來源": "data/meta/tw50/tw50_changes.csv", "起": str(td.min().date()) if td.notna().any() else "",
                "迄": str(td.max().date()) if td.notna().any() else "", "筆數": len(T50), "2018-11起筆數": int((td >= "2018-11-01").sum())})
    # 訊號窗（資料日前 28 日～資料日）內有事件的訊號比例（只盤點覆蓋，⛔ 不剔除、不算報酬）
    ev = {}
    for k, msk in {"現增": (E["class"] == "seo") & (E["private"] != "1") & (E["ipo"] != "1"), "私募": E["private"] == "1",
                   "可轉債發行": (E["class"] == "cb") & (E["private"] != "1")}.items():
        ev[k] = E[msk].groupby("stock_id")["date"].apply(lambda s: np.array(sorted(s), dtype="datetime64[ns]")).to_dict()
    cv = x.assign(d=xd).groupby("stock_id")["d"].apply(lambda s: np.array(sorted(s), dtype="datetime64[ns]")).to_dict()
    ev["轉換公告"] = cv
    cover = {}
    for k, m in ev.items():
        hit = 0
        for s, d in zip(sig["sid"], sig["d"]):
            a = m.get(s)
            if a is None:
                continue
            lo = np.datetime64(d - pd.Timedelta(days=28)); hi = np.datetime64(d)
            i = np.searchsorted(a, lo)
            if i < len(a) and a[i] <= hi:
                hit += 1
        cover[k] = (hit, len(sig))
    return pd.DataFrame(out), cover


def pct(x):
    return "" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{100 * x:.1f}%"


def write_md(F, agg, extra, cover, inv, dc, cinfo, yl_end, SIG):
    g = lambda seg, ver: F[(F["段"] == seg) & (F["版"] == ver)].iloc[0]
    L = ["# 集保大戶比例 4 週升幅前 5%・組合層 seq1（裁定 seq507）頻率表", "",
         f"回測線計算子代理｜資料 tw-stock-data `{SHA[:10]}`（＝ 情報 #76 同 sha）｜程式 `backtest/researchBigHolderRise.py`｜⛔ 不附任何報酬", ""]
    mx = max(F["持倉重疊比"].max(), F["新買±5日重疊比"].max(), F["候選±5日重疊比"].fillna(0).max())
    L += ["## 〇、與營量 v1 重疊（裁定附註：≥ 50% 先回信）", "",
          f"**最大重疊 {pct(mx)} ＜ 50% ⇒ 不觸發**。" if mx < 0.5 else f"⚠⚠ **重疊 {pct(mx)} ≥ 50% ⇒ 先回信**", "",
          "| 段 | 版 | 分母（進場日 ≤ " + str(yl_end.date()) + "） | ① 營量 v1 持倉中 | ② 營量 v1 前後 5 日新買 | ③ 營量 v1 候選前後 5 日（只 2025-08～2026-06） |", "|---|---|---:|---:|---:|---:|"]
    for seg in SEGS:
        for ver in ("全收版", "10檔版"):
            r = g(seg, ver)
            L.append(f"| {seg} | {ver} | {r['n']} | {r['持倉重疊']}（{pct(r['持倉重疊比'])}） | {r['新買±5日重疊']}（{pct(r['新買±5日重疊比'])}） | "
                     f"{r['候選±5日重疊']}／{r['候選n_2025-08~2026-06']}（{pct(r['候選±5日重疊比'])}） |")
        o = extra[seg]["全部訊號"]
        L.append(f"| {seg} | 全部訊號（不經組合） | {o['n']} | {o['持倉重疊']}（{pct(o['持倉重疊比'])}） | {o['新買±5日重疊']}（{pct(o['新買±5日重疊比'])}） | "
                 f"{o['候選±5日重疊']}／{o['候選n_2025-08~2026-06']}（{pct(o['候選±5日重疊比'])}） |")
    L += ["", "營量 v1 名單出處：① ② `backtest/resultsYFallin/trades_W.csv.gz` 世界「主」帳 YL（＋daily_W 日期，2015-01-05～2026-09-24）；"
          f"③ `backtest/resultsYLlist/營量v1名單＋營量v1未入選候選_20260928.csv`（{cinfo[2]} 列，{cinfo[0].date()}～{cinfo[1].date()}）。只讀 日期／代號 欄。", ""]
    L += ["## 一、條件等價檢查（seq377）", "",
          "- ⚠ 情報 #76 的事件清單與程式（`claude/bigholder_rise_code_20261117.md`、結果檔）在情報線專案，本機、WSL 三個 repo、GitHub 三個 repo 都找不到 ⇒ **逐筆一致率做不了**；改做彙總對照，見 `equiv76.md`。",
          f"- 彙總對照（同 sha）：可算週且 60 日到期 **{agg['可算B週數_且60日到期']} 週**（#76：B60 360 週）；母體平均 **{agg['母體平均(全段)']}** 檔（#76：約 570）；週訊號平均 **{agg['週訊號平均(全段)']}**（#76：約 29）⇒ 三項都對得上。",
          f"- 與營量 v1 不等價（上表 ≤ {pct(mx)}）。", ""]
    L += ["## 二、訊號頻率（依進場日分段）", "", "| 項 | 探索 | 確認 |", "|---|---:|---:|"]
    a, b = g("探索", "全收版"), g("確認", "全收版")
    for k in ["段起", "段迄", "段長_年", "集保週數(段內)", "缺週(間隔>10日推估)", "可算B週數", "無前4週資料週", "母體_平均", "母體_中位",
              "週訊號_平均", "週訊號_中位", "週訊號_最少", "週訊號_最多", "0訊號週", "訊號總數", "進場日無開盤"]:
        L.append(f"| {k} | {a[k]} | {b[k]} |")
    L += ["", f"集保缺口：探索 {a['缺口']}｜確認 {b['缺口']}", ""]
    L += ["## 三、組合（只用日期與份數）", "", "| 項 | 探索 全收 | 探索 10檔 | 確認 全收 | 確認 10檔 |", "|---|---:|---:|---:|---:|"]
    rr = [g("探索", "全收版"), g("探索", "10檔版"), g("確認", "全收版"), g("確認", "10檔版")]
    for k in ["買進筆數", "買進批數", "有進場不同月數", "四十九", "平均持股部位", "平均不同檔數", "現金比例", "現金比例_2019_07起",
              "年換手_筆每年", "年換手_份額每年", "輪到份未出場_略過週", "輪到份未出場_略過訊號", "死板輪_略過週",
              "空位但當週0訊號週", "滿了沒買訊號", "已持有同檔略過"]:
        L.append(f"| {k} | " + " | ".join(str(r[k]) for r in rr) + " |")
    L += ["", "- 〈四十九〉：任一段有進場的不同月數 < 24 ⇒ 該格還沒測。",
          "- 10 檔版每次都是 10 格同時空出、同一週補滿 ⇒ 進場集中成批（約每 60 個交易日一批），不同月數因此少。",
          "- 全收版平均持股部位含同一檔在不同份重複持有；不同檔數另列。",
          "- 現金比例_2019_07起：探索段扣掉 2019-01～06 集保缺資料那半年（那半年沒訊號、全現金）。", ""]
    L += ["## 四、事件拆解資料可得性（只盤點，⛔ 不剔除、不算報酬）", "", "| 類 | 來源 | 起 | 迄 | 筆數 | 2018-11 起 |", "|---|---|---|---|---:|---:|"]
    for r in inv.itertuples():
        L.append(f"| {r.類} | {r.來源} | {r.起} | {r.迄} | {r.筆數} | {r._6} |")
    L += ["", "訊號窗（資料日前 28 日～資料日）內同檔有公告的訊號比例（決議／公告日口徑，只看覆蓋）："]
    for k, (h, n) in cover.items():
        L.append(f"- {k}：{h}／{n}（{pct(h / n)}）")
    L += ["", "- ETF 申贖：資料庫沒有 ETF 申購買回清單（PCF）⇒ 這一類拆不到；0050 成分異動只是旁證。",
          "- 可轉債「轉換」沒有專表，只能用重訊主旨關鍵字代理；實際轉換多半不發重訊（月報股本變動），覆蓋偏低。", ""]
    L += ["## 五、資料檢查", "",
          f"- 集保（tdcc_hist parquet＋tdcc csv，四碼普通股）2018-11 起每週檔數：最少 {int(dc[dc['資料日'] >= pd.Timestamp('2018-11-01').date()]['四碼普通股檔數'].min())}、"
          f"最多 {int(dc[dc['資料日'] >= pd.Timestamp('2018-11-01').date()]['四碼普通股檔數'].max())}（逐週見 data_check.csv）。",
          "- 缺週：2018-12-28 → 2019-06-28 整段 25 週沒有資料（探索段實際只有 2018-11～12 與 2019-07 起）；其餘缺口多為春節或單週缺。",
          "- 成交額門檻：`data/stocks/<代號>.csv` 的 amount 欄（官方日成交金額，元），資料日當天或之前最後一個交易日往回 20 個交易日平均（沒成交日記 0）≥ 5,000 萬。",
          "- 大戶比例用 shares 欄（第 12～15 級 ÷ 第 1～15 級），不用 pct 欄。", ""]
    L += ["## 六、執行者定（★）", "",
          "1. 4 週前 ＝ 與資料日 −28 日相差 ≤ 3 日的集保資料日；找不到 ⇒ 該週不算（探索 9 週、確認 6 週）。",
          "2. 升幅 ＝ 比例差（百分點），不是相對變化。",
          "3. 全收版：每週動用一份已出場的空份；12 份都未出場 ⇒ 本週不買（件數見表）。死板輪（週序 mod 12）因 60 個交易日常超過 12 週，會略過近半數週（見「死板輪_略過週」），不採用。",
          "4. 10 檔版：已持有的同一檔不重複買。",
          "5. 兩段各自從空倉開始；資料尾未到期部位算持有到資料尾。",
          "6. 進場日當天沒開盤 ⇒ 買不到、不補。", "", "描述，不是買賣建議", ""]
    with open(os.path.join(OUT, "頻率表.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    E = ["# 對情報 #76 的條件等價檢查（seq377）", "",
         "## 逐筆一致率：做不了", "",
         "- #76 的事件清單、程式（`claude/bigholder_rise_code_20261117.md`）、結果檔（`sources/bigholder_rise_results_20261117.md`）放在情報線的專案；",
         "  本機 C:\\SynologyDrive（含 投資\\情報用）、WSL 家目錄、tw-stock-data 全部分支、GitHub 三個 repo（tw-stock-data、tw-daily-line、us-stock-data）都找不到。",
         "- ⇒ 本檔依登錄全文與情報 1117-1422 信的文字定義重寫（`backtest/researchBigHolderRise.py`，單一新檔），⛔ 沒有第二套。", "",
         "## 彙總對照（同 sha e2fdcdef9）", "", "| 項 | 本線 | #76（情報信） |", "|---|---:|---:|",
         f"| B60 可用週數（60 日到期） | {agg['可算B週數_且60日到期']} | 360（221／360 週為正那句的分母） |",
         f"| 每週母體平均 | {agg['母體平均(全段)']} | 約 570 |",
         f"| 每週訊號平均 | {agg['週訊號平均(全段)']} | 約 29 |",
         f"| B60 訊號筆數（到期） | {agg['B60訊號筆數(到期)']} | 信中未列 |", "",
         "三項有數的都對得上 ⇒ 判讀為同一訊號；逐筆清單要情報線把事件清單放到本機（或跨線信箱附件）才能補做。", "",
         "## 與已登錄策略：營量 v1", "", f"- 重疊最多 {pct(mx)}（見頻率表〇），遠低於 90% ⇒ 不是營量 v1 的名單。", ""]
    with open(os.path.join(OUT, "equiv76.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(E))


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    D.DATA = DATA
    cal = D.load_calendar()
    s2330 = pd.read_csv(os.path.join(DATA, "stocks", "2330.csv"), usecols=["date"])
    data_end = pd.Timestamp(s2330["date"].max())
    cal = cal[cal <= data_end]; last_pos = len(cal) - 1
    log(f"[資料] tw-stock-data {SHA[:10]}｜日曆 {cal[0].date()}～{cal[-1].date()}（資料尾＝2330 最後一天）")

    stk = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    stk = stk[(stk["kind"] == "stock") & stk["market"].isin(["twse", "tpex"]) & stk["stock_id"].str.fullmatch(r"\d{4}")]
    sids = stk["stock_id"].tolist()
    log(f"[母體候選] 四碼普通股（含已下市）{len(sids)} 檔")

    R = load_tdcc()
    R = R[R["stock_id"].isin(set(sids))]
    dates = sorted(R["date"].unique())
    log(f"[集保] 四碼普通股 股-週 {len(R):,}｜資料日 {len(dates)} 個 {dates[0].date()}～{dates[-1].date()}")
    # 資料檢查
    cnt = R.groupby("date")["stock_id"].nunique()
    dc = pd.DataFrame({"資料日": [d.date() for d in cnt.index], "四碼普通股檔數": cnt.values})
    dc["距上一資料日_日"] = pd.Series(cnt.index).diff().dt.days.values
    dc.to_csv(os.path.join(OUT, "data_check.csv"), index=False, encoding="utf-8-sig")
    lm = lag_map(dates)

    AMT, OPN = load_amount_open(sids, cal)
    log(f"[價量] 讀到 {len(AMT)} 檔 amount／open")

    piv = R.pivot(index="date", columns="stock_id", values="ratio")
    weeks = []; sig_rows = []
    for d in dates:
        if d < pd.Timestamp("2018-11-01"):
            continue
        dl = lm[d]
        p = int(cal.searchsorted(d, side="right")) - 1           # 資料日當天或之前最後一個交易日
        e = int(cal.searchsorted(d + pd.Timedelta(days=2), side="left"))   # 資料日 +2 日曆日當天或之後第一個交易日
        wrow = {"d": d, "lag": dl, "e": e if e <= last_pos else None, "uni": 0, "nsig": 0, "buys": [], "buys_ranked": [], "q95": np.nan, "nobuy": 0}
        if pd.isna(dl) or p < 0:
            wrow["status"] = "無前4週資料" if pd.isna(dl) else "無交易日"; weeks.append(wrow); continue
        chg = (piv.loc[d] - piv.loc[dl]).dropna()
        ok = [s for s in chg.index if s in AMT and np.isfinite(AMT[s][p]) and AMT[s][p] >= AMT_MIN]
        c = chg[ok]
        wrow["uni"] = len(c)
        if len(c) == 0:
            wrow["status"] = "母體0"; weeks.append(wrow); continue
        q = float(np.quantile(c.to_numpy(), Q)); wrow["q95"] = q
        sg = c[(c >= q) & (c > 0)].sort_values(ascending=False)
        wrow["nsig"] = len(sg); wrow["status"] = "ok" if e <= last_pos else "進場日超過資料尾"
        for rk, (s, v) in enumerate(sg.items(), 1):
            can = bool(e <= last_pos and OPN[s][e])
            sig_rows.append({"資料日": d.date(), "前4週資料日": dl.date(), "進場日": cal[e].date() if e <= last_pos else "",
                             "sid": s, "升幅_pp": round(float(v) * 100, 6), "當週名次": rk, "當週母體": len(c),
                             "進場日有開盤": int(can), "e": e})
            if can:
                wrow["buys"].append(s); wrow["buys_ranked"].append(s)
            elif e <= last_pos:
                wrow["nobuy"] += 1
        weeks.append(wrow)
    SIG = pd.DataFrame(sig_rows)
    SIG.drop(columns=["e"]).to_csv(os.path.join(OUT, "signals.csv"), index=False, encoding="utf-8-sig")
    WK = pd.DataFrame([{"資料日": w["d"].date(), "前4週資料日": (w["lag"].date() if pd.notna(w["lag"]) else ""),
                        "進場日": (cal[w["e"]].date() if w["e"] is not None else ""), "狀態": w["status"], "母體": w["uni"],
                        "第95百分位_pp": round(w["q95"] * 100, 6) if np.isfinite(w["q95"]) else "", "訊號": w["nsig"],
                        "進場日無開盤": w["nobuy"], "買得到": len(w["buys"])} for w in weeks])
    WK.to_csv(os.path.join(OUT, "weekly.csv"), index=False, encoding="utf-8-sig")
    log(f"[訊號] 週 {len(weeks)}（ok {sum(w['status']=='ok' for w in weeks)}）｜訊號 {len(SIG)}｜進場日無開盤 {int((SIG['進場日有開盤']==0).sum()) if len(SIG) else 0}")

    iv, ylbuys, cset, yl_end, cinfo = load_yl()
    log(f"[營量 v1] resultsYFallin 帳 YL 持倉 {sum(len(v) for v in iv.values())} 筆、資料尾 {yl_end.date()}｜候選檔 {cinfo[2]} 列 {cinfo[0].date()}～{cinfo[1].date()}")

    rows = []; extra = {}
    for seg, (a, b) in SEGS.items():
        lo = int(cal.searchsorted(pd.Timestamp(a))); hi = min(int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1, last_pos)
        Wseg = [w for w in weeks if w["status"] == "ok" and lo <= w["e"] <= hi]
        Wall = [w for w in weeks if w["e"] is not None and lo <= w["e"] <= hi]
        ns = np.array([w["nsig"] for w in Wseg]); nu = np.array([w["uni"] for w in Wseg])
        yrs = (cal[hi] - cal[lo]).days / 365.25
        # 曆週缺資料
        d_in = [w["d"] for w in weeks if pd.Timestamp(a) <= w["d"] <= pd.Timestamp(b)]
        gaps = [(d_in[i - 1].date(), d_in[i].date(), (d_in[i] - d_in[i - 1]).days) for i in range(1, len(d_in)) if (d_in[i] - d_in[i - 1]).days > 10]
        miss_weeks = sum(int(round(g[2] / 7)) - 1 for g in gaps)
        base = {"段": seg, "段起": cal[lo].date(), "段迄": cal[hi].date(), "段長_年": round(yrs, 3),
                "集保週數(段內)": len(d_in), "缺週(間隔>10日推估)": miss_weeks, "缺口": "; ".join(f"{g[0]}→{g[1]}({g[2]}日)" for g in gaps),
                "可算B週數": len(Wseg), "無前4週資料週": sum(w["status"] == "無前4週資料" for w in Wall),
                "母體_平均": round(nu.mean(), 1) if len(nu) else np.nan, "母體_中位": float(np.median(nu)) if len(nu) else np.nan,
                "週訊號_平均": round(ns.mean(), 2) if len(ns) else np.nan, "週訊號_中位": float(np.median(ns)) if len(ns) else np.nan,
                "週訊號_最少": int(ns.min()) if len(ns) else np.nan, "週訊號_最多": int(ns.max()) if len(ns) else np.nan,
                "0訊號週": int((ns == 0).sum()), "訊號總數": int(ns.sum()),
                "進場日無開盤": int(sum(w["nobuy"] for w in Wseg))}
        # 全收版
        coh, posF, conf = sim_full(Wseg, cal, last_pos, lo, hi)
        cntF, distF, cashF = daily_occupancy(posF, lo, hi, 12, "full", coh)
        mF = sorted({cal[p["e"]].strftime("%Y-%m") for p in posF})
        lo2 = max(lo, int(cal.searchsorted(pd.Timestamp("2019-07-01"))))
        rF = dict(base, 版="全收版", 買進筆數=len(posF), 買進批數=sum(1 for c in coh if c.get("n", 0) > 0 and "x" in c),
                  輪到份未出場_略過週=len(conf), 輪到份未出場_略過訊號=sum(c["n"] for c in conf), 死板輪_略過週=rigid_conflict(Wseg),
                  現金比例_2019_07起=round(cashF[lo2 - lo:].mean(), 4),
                  有進場不同月數=len(mF), 四十九=("還沒測(<24)" if len(mF) < 24 else "可判(≥24)"),
                  平均持股部位=round(cntF.mean(), 2), 平均不同檔數=round(distF.mean(), 2), 現金比例=round(cashF.mean(), 4),
                  年換手_筆每年=round(len(posF) / yrs, 1), 年換手_份額每年=round(sum(p["w"] for p in posF) / yrs, 3),
                  空位但當週0訊號週="", 滿了沒買訊號="", 已持有同檔略過="")
        rF.update(overlap([(p["sid"], p["e"]) for p in posF], cal, iv, ylbuys, cset, yl_end))
        rows.append(rF)
        # 10 檔版
        posT, st = sim_ten(Wseg)
        cntT, distT, cashT = daily_occupancy(posT, lo, hi, 10, "ten")
        mT = sorted({cal[p["e"]].strftime("%Y-%m") for p in posT})
        rT = dict(base, 版="10檔版", 買進筆數=len(posT), 買進批數=len({p["e"] for p in posT}),
                  輪到份未出場_略過週="", 輪到份未出場_略過訊號="", 死板輪_略過週="",
                  現金比例_2019_07起=round(cashT[lo2 - lo:].mean(), 4),
                  有進場不同月數=len(mT), 四十九=("還沒測(<24)" if len(mT) < 24 else "可判(≥24)"),
                  平均持股部位=round(cntT.mean(), 2), 平均不同檔數=round(distT.mean(), 2), 現金比例=round(cashT.mean(), 4),
                  年換手_筆每年=round(len(posT) / yrs, 1), 年換手_份額每年=round(sum(p["w"] for p in posT) / yrs, 3),
                  空位但當週0訊號週=st["free_no_sig"], 滿了沒買訊號=st["full_skip"], 已持有同檔略過=st["dup_skip"])
        rT.update(overlap([(p["sid"], p["e"]) for p in posT], cal, iv, ylbuys, cset, yl_end))
        rows.append(rT)
        # 全部訊號（不經組合）的重疊
        sg = SIG[(SIG["e"] >= lo) & (SIG["e"] <= hi)]
        extra[seg] = {"全部訊號": overlap(list(zip(sg["sid"], sg["e"])), cal, iv, ylbuys, cset, yl_end),
                      "全收版月": mF, "10檔版月": mT, "10檔版空位週": st["free_weeks"], "10檔版週": st["weeks"]}
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")

    inv, cover = event_inventory(SIG.assign(d=pd.to_datetime(SIG["資料日"])))
    inv.to_csv(os.path.join(OUT, "event_inventory.csv"), index=False, encoding="utf-8-sig")

    # #76 對照（只有彙總）
    full60 = [w for w in weeks if w["status"] == "ok" and D.exit_pos(w["e"], HOLD) <= last_pos]
    agg = {"可算B週數(全段)": sum(w["status"] == "ok" for w in weeks),
           "可算B週數_且60日到期": len(full60),
           "其中有訊號週": sum(1 for w in full60 if w["nsig"] > 0),
           "母體平均(全段)": round(np.mean([w["uni"] for w in weeks if w["status"] == "ok"]), 1),
           "週訊號平均(全段)": round(np.mean([w["nsig"] for w in weeks if w["status"] == "ok"]), 2),
           "B60訊號筆數(到期)": int(sum(w["nsig"] for w in full60))}
    J = {"sha": SHA, "agg76": agg, "extra": extra, "cover": cover, "ylcand": [str(cinfo[0].date()), str(cinfo[1].date()), cinfo[2]]}
    with open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=str)
    log(json.dumps(agg, ensure_ascii=False))
    log(json.dumps({k: v["全部訊號"] for k, v in extra.items()}, ensure_ascii=False, default=str))
    log(json.dumps(cover, ensure_ascii=False))
    log(F.T.to_string())
    log(inv.to_string())
    write_md(F, agg, extra, cover, inv, dc, cinfo, yl_end, SIG)
    log(f"[完成] {time.time() - t0:.0f}s")
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOGS) + "\n")


if __name__ == "__main__":
    main()

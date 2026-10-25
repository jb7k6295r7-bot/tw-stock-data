# -*- coding: utf-8 -*-
"""USREG-C3s（動能只在 S&P 500）——可操作輸出（ops）。⛔ 不改登錄、不改規則（S1）、不加 N；看過段只描述、不判。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC3s_ops            # 全部（持股、換股單 gate、統計）
    ... -m backtest.researchUSC3s_ops --month 2026-10-30                    # 某月底的換股單（主臂續抱簿；下一交易日開盤執行）
    ... -m backtest.researchUSC3s_ops --month 2026-10-30 --book forward     # 前瞻 ② 簿（2026-10 月底收盤起新開，S7）
    ... -m backtest.researchUSC3s_ops --check                               # 獨立寫法重算持股、換股單與統計（差 ≤ 1e−9 判同）

同一來源：MOM ＝ researchUSC_c3.mom_scores()；名單 ＝ researchUSC.rank_tables(MOM, S&P 500 m5)；換股簿 ＝ researchUSC.book
（＝ researchUSC3s.rank_main 同一呼叫；⛔ 不另寫選股邏輯）。月底之後的換股日（2026-10 起）只把 mom_scores 的換股日清單往後延（R["ms"] 暫時擴充），
算式不動；閘：擴充後 2017-01～2026-09 的名單與原版逐日相同。
換股單產生器 order_for(M) ＝ book 跑到月底 M 收盤的持股 ＋ S1 規則套在 e ＝ M 的下一交易日：賣「不在前 20%（含掉出指數／MOM 不可算）」者，
再依 MOM 遞減從前 10% 補空槽；輸出列格式 ＝ forward_template.csv 欄位（讀該檔表頭，⛔ 不改該檔）。
⚠ 產生器無法預知 e 當天的開盤停牌（book 會延後賣／該檔不買不遞補）與 e 當天的價格斷點強制出場；gate 會把這兩類列出。
私有（S9）：repo resultsUSC/C3s/ops/ 只放代號、排名、漲幅%、換股代號、統計；逐筆明細寫 ~/us_work/c/c3s/ops/。
全名（美股策略線 1025-0122 §二、裁定 seq472 §五：美股一律「代號（IB 全名）」）：換股單另加一欄「全名」，插在最後一欄「備註」之前
（⛔ 不放最後：researchUSC3s_stop.order_with_level 以 cols[-1] 寫備註；前 25 欄位置與值不變）。名稱查 backtest/forward/us_names.csv
（① 美股策略線對照表、② us-stock-data cik_map.csv 的 SEC 名稱「未核（名冊）」）；都沒有 ⇒「未知（請在 IB 確認）」。⛔ 只排版，不動選股。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K          # noqa: E402
from backtest import researchUSC_c3 as C3      # noqa: E402
from backtest import researchUSC3s as C3S      # noqa: E402

OPSD = os.path.join(C3S.OUTD, "ops")
PRIVD = os.path.join(C3S.WORKD, "ops")
TPL = os.path.join(C3S.OUTD, "forward_template.csv")
FWD_START_MONTH = (2026, 10)          # S7：前瞻 ② 起點 ＝ 2026-10 最後交易日收盤選、11 月第一個交易日開盤買
SPLIT = pd.Timestamp("2022-01-01")    # 統計第二段：出場日 ≥ 2022-01-01
TOL = 1e-9
NAMES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forward", "us_names.csv")
FULLNAME_COL = "全名"
NAME_UNKNOWN = "未知（請在 IB 確認）"
IB_NOTE = "下單前在 IB 輸入代號，確認名稱一致（全名未在 IB 逐一核）"
_NAMES: dict = {}


def jd(obj, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return K.jdump(obj, p)


def pct(x):
    return None if x is None or not np.isfinite(x) else float(x * 100)


# ═════════════ 同一來源：擴充換股日的名單 ═════════════
_T: dict = {}


def tables(virtual_e=False):
    """C3.mom_scores ＋ K.rank_tables（S&P 500）。換股日清單延到資料最後；virtual_e ⇒ 再加一個資料外的換股日（資料最後一日當月底）。"""
    key = bool(virtual_e)
    if key in _T:
        return _T[key]
    R = K.rworld(); n = R["n"]
    ms0, ym0 = R["ms"], R["ym"]
    ms = sorted(v for v in R["first"].values() if 0 < v < n)
    ym = ym0
    if virtual_e:
        ms = ms + [n]; ym = np.append(ym0, ym0[n - 1] + 1)
    try:
        R["ms"] = np.array(ms); R["ym"] = ym
        S = C3.mom_scores()
    finally:
        R["ms"] = ms0; R["ym"] = ym0
    M5 = R["memb"]["只500"]
    if virtual_e:
        M5 = np.vstack([M5, M5[-1:]])          # e＝n 只會用到 M5[e−1]＝M5[n−1]
    BUY, KEEP, ORD = K.rank_tables(S, M5)
    _, _, FULL = K.rank_tables(S, M5, ent=1.0, ext=1.0)
    t0 = min(e for e, v in S.items() if np.isfinite(v).any())
    _T[key] = dict(S=S, BUY=BUY, KEEP=KEEP, ORD=ORD, FULL=FULL, t0=t0, M5=M5)
    return _T[key]


def rank_of(T, e, j):
    f = T["FULL"].get(e, [])
    try:
        return f.index(j) + 1, len(f)
    except ValueError:
        return None, len(f)


def run_book(T, t0, t1, Wd=None):
    """＝ researchUSC3s.rank_main 內的 K.book 呼叫（rebs ＝ sorted(KEEP)）。"""
    tr = []
    res = K.book(K.rworld()["Wd"] if Wd is None else Wd, sorted(T["KEEP"]), T["KEEP"], T["BUY"], K.N_SLOTS, t0, t1, trades_out=tr)
    return res, tr


# ═════════════ 全名（只排版；⛔ 不動選股）═════════════
def names():
    """us_names.csv ⇒ {代號: (全名, verified)}。"""
    if not _NAMES and os.path.exists(NAMES_CSV):
        with open(NAMES_CSV, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                _NAMES[r["ticker"].strip()] = (r["full_name"].strip(), r["verified"].strip())
    return _NAMES


def full_name(t):
    v = names().get(str(t))
    return v[0] if v and v[0] else NAME_UNKNOWN


def label(t):
    """「代號（全名）」；名冊來源另標［未核（名冊）］。"""
    v = names().get(str(t))
    if not v or not v[0]:
        return f"{t}（{NAME_UNKNOWN}）"
    return f"{t}（{v[0]}）" + (f"［{v[1]}］" if v[1] == "未核（名冊）" else "")


def order_tickers(o, tick):
    """換股單提到的代號（換股後持股 → 新進 → 賣出，去重保序）。"""
    out = []
    for j in list(o["after"]) + list(o["buys"]) + [j for j, _ in o["sells"]]:
        t = str(tick[j])
        if t not in out:
            out.append(t)
    return out


# ═════════════ 換股單產生器（＝ forward_template 欄位）═════════════
def month_end_index(d):
    R = K.rworld(); cal = R["cal"]; n = R["n"]
    ts = pd.Timestamp(d)
    M = int(cal.searchsorted(ts))
    if M >= n or cal[M] != ts:
        raise SystemExit(f"{d} 不是資料內的交易日")
    virtual = M == n - 1
    if not virtual and R["ym"][M + 1] == R["ym"][M]:
        raise SystemExit(f"{d} 不是當月最後一個交易日（下一交易日 {cal[M + 1].date()} 同月）")
    return M, virtual


def proxy_world(M):
    """只用到月底 M 為止的資料（＝ 實盤當晚能看到的），再接一個虛擬換股日 e＝M＋1：開盤價 ≈ M 收盤（ffill）、無斷點。
    存續判定：M 前 5 根內有有效 K 棒者視為仍在交易（last ← e），否則 last ＝ M 前最後有效日。⚠ 只影響成交價估計，⛔ 不動選股規則。"""
    W = K.rworld()["Wd"]; e = M + 1
    v = W["valid"][:M + 1]
    anyv = v.any(axis=0)
    lt = np.where(anyv, M - np.argmax(v[::-1], axis=0), -1)
    last = np.where(lt >= M - 4, e, lt)
    return {"O": np.vstack([W["O"][:M + 1], W["CF"][M:M + 1]]), "CF": np.vstack([W["CF"][:M + 1], W["CF"][M:M + 1]]),
            "valid": np.vstack([v, np.isfinite(W["CF"][M:M + 1]) & (lt >= M - 4)[None, :]]),
            "pb": np.vstack([W["pb"][:M + 1], np.zeros((1, v.shape[1]), bool)]), "last": last, "cal": range(e + 1)}


def order_for(M, book="main", mode="auto"):
    """月底 M 收盤 ⇒ e ＝ 下一交易日開盤的換股單。＝ K.book（主臂同一呼叫）跑到 e，讀 e 的賣／買。
    book：main ＝ 主臂（2017-01 起續抱）、forward ＝ 前瞻 ②（2026-10 月底起新開）。
    mode：exact ＝ 用真實 e 開盤（只能事後）；proxy ＝ 只用到 M 的資料、e 開盤 ≈ M 收盤（實盤當晚的做法）；auto ＝ e 在資料內 ⇒ exact，否則 proxy。"""
    R = K.rworld(); W = R["Wd"]; n = R["n"]; tick = W["tick"]
    virtual = M == n - 1
    T = tables(virtual_e=virtual)
    e = M + 1
    if e not in T["S"]:
        raise SystemExit("e 不在換股日清單（MOM 不可算）")
    if mode == "auto":
        mode = "proxy" if virtual else "exact"
    if virtual and mode == "exact":
        raise SystemExit("e 在資料外，只能 proxy")
    Wd = W if mode == "exact" else proxy_world(M)
    if book == "main":
        b0 = T["t0"]
    else:
        y, m = FWD_START_MONTH
        k0 = y * 12 + m - 1
        if int(R["ym"][M]) < k0:
            raise SystemExit("前瞻 ② 簿 2026-10 月底才開始")
        b0 = R["last"][k0] + 1          # 2026-11 第一個交易日（＝ 第 0 列買進日）
    held, cashf = {}, 1.0
    if b0 <= M:
        r0, _ = run_book(T, b0, M, Wd)
        held = {int(j): int(b) for j, b, _hi in r0["open"]}; cashf = float(r0["cashf"][M])
    r1, tr1 = run_book(T, min(b0, e), e, Wd)
    after = list(r1["holds"].get(e, sorted(int(j) for j, _, _ in r1["open"])))
    keep, buy, M5, S = T["KEEP"][e], T["BUY"][e], T["M5"], T["S"][e]
    sells = []
    for x in tr1:
        if x[2] == e and x[5] == "換股":
            j = int(x[0])
            why = "掉出指數" if not M5[e - 1, j] else ("MOM 不可算（斷點／缺價）" if not np.isfinite(S[j]) else "跌出前20%")
            sells.append((j, why))
    sells.sort(key=lambda s: str(tick[s[0]]))
    forced = [(int(x[0]), x[5]) for x in tr1 if x[2] == e - 1 and x[5] != "換股" and int(x[0]) in held]
    buys = [j for j in after if j not in held]
    delayed = [j for j in held if j not in keep and j in after]
    after.sort(key=lambda j: rank_of(T, e, j)[0] or 10 ** 6)
    buys.sort(key=lambda j: rank_of(T, e, j)[0])
    cand = [j for j in buy if j not in after][:max(K.N_SLOTS - len(after), 0)]
    out = {"book": book, "mode": mode, "M": M, "e": e, "virtual_e": virtual, "held_before": held, "cashf_M": cashf,
           "sells": sells, "forced": forced, "delayed": delayed, "buys": buys, "after": after, "cand": cand,
           "n_rank": len(T["FULL"][e]), "k10": len(buy), "k20": len(keep)}
    return out, T


def order_row(o, T):
    """forward_template.csv 欄位的一列（表頭讀該檔；⛔ 月報酬欄留空，月底後由前瞻紀錄填）。
    回傳的 cols ＝ 範本欄位、在最後一欄（備註）之前插入「全名」；⛔ 範本檔不改。"""
    R = K.rworld(); cal = R["cal"]; tick = R["Wd"]["tick"]; n = R["n"]
    cols = next(csv.reader(open(TPL, encoding="utf-8-sig")))
    M, e = o["M"], o["e"]
    k_e = int(R["ym"][M]) + 1
    y0, m0 = FWD_START_MONTH
    period = k_e - (y0 * 12 + m0 - 1)
    ey, em = divmod(k_e, 12)
    month = f"{ey}-{em + 1:02d}"
    e_str = str(cal[e].date()) if e < n else "（資料外：下一交易日）"
    end = [i for i in range(e, n) if R["ym"][i] == k_e]
    end_str = str(cal[end[-1]].date()) if end and (end[-1] + 1 < n) else ""
    h = [str(tick[j]) for j in o["after"]] + [""] * (8 - len(o["after"]))
    row = {c: "" for c in cols}
    row.update({cols[0]: (str(period) if o["book"] == "forward" else "主臂"), cols[1]: month,
                cols[2]: str(cal[M].date()), cols[3]: e_str, cols[4]: end_str})
    for i in range(8):
        row[cols[5 + i]] = h[i]
    row[cols[13]] = " ".join(str(tick[j]) for j in o["buys"])
    row[cols[14]] = " ".join(str(tick[j]) for j, _ in o["sells"])
    row[cols[15]] = " ".join(f"{tick[j]}:{w}" for j, w in o["sells"])
    row[cols[16]] = str(o["n_rank"]); row[cols[17]] = str(o["k10"])
    row[cols[22]] = "world.npz m5（us-stock-data 881c86a，point-in-time）"
    row[cols[23]] = "us-stock-data 881c86a（~/us_work/a4/world.npz）"
    row[cols[24]] = K.now_tpe()
    row[cols[25]] = (f"{o['book']} 簿；空槽 {K.N_SLOTS - len(o['after'])}" + ("；e 在資料外，開盤可否成交未知" if o["virtual_e"] else ""))
    assert FULLNAME_COL not in cols
    row[FULLNAME_COL] = "；".join(label(t) for t in order_tickers(o, tick)) + f"｜⚠ {IB_NOTE}"
    cols = cols[:-1] + [FULLNAME_COL] + cols[-1:]
    return cols, row


def order_view(o, T):
    R = K.rworld(); cal = R["cal"]; tick = R["Wd"]["tick"]; n = R["n"]; e = o["e"]
    return {"簿": o["book"], "成交價口徑": {"exact": "真實 e 開盤", "proxy": "e 開盤 ≈ 月底收盤（實盤當晚做法）"}[o["mode"]],
            "量測月底": str(cal[o["M"]].date()), "執行": (str(cal[e].date()) if e < n else "下一交易日") + " 開盤",
            "賣": [{"代號": str(tick[j]), "全名": full_name(tick[j]), "原因": w, "月底排名": rank_of(T, e, j)[0]} for j, w in o["sells"]],
            "買（依序）": [{"代號": str(tick[j]), "全名": full_name(tick[j]), "月底排名": rank_of(T, e, j)[0]} for j in o["buys"]],
            "換股後持股": [str(tick[j]) for j in o["after"]], "空槽": K.N_SLOTS - len(o["after"]),
            "換股後持股（代號（全名））": [label(tick[j]) for j in o["after"]],
            "空槽候補（前10% 未持有、依 MOM 序；現金不足或開盤無效所以沒買）": [str(tick[j]) for j in o["cand"]],
            "月底現金占總值（%）": pct(o["cashf_M"]),
            "e 當日強制出場（斷點／下市）": [f"{tick[j]}:{w}" for j, w in o["forced"]],
            "該賣但開盤無效延後": [str(tick[j]) for j in o["delayed"]],
            "排名分母（S&P 500 可排檔數）": o["n_rank"], "前10%檔數": o["k10"], "前20%檔數": o["k20"],
            "每筆新買金額": "min(前一日帳戶總值 ÷ 8, 可用現金)，依 MOM 序買，現金用完即停（⛔ 不賣贏家補錢，K.book 原式）",
            "⚠ 全名": IB_NOTE}


def order_md(o, T):
    """換股單 md（印給人看；代號＋全名）。"""
    R = K.rworld(); cal = R["cal"]; tick = R["Wd"]["tick"]; n = R["n"]; e = o["e"]
    ex = (str(cal[e].date()) if e < n else "下一交易日") + " 開盤"
    L = [f"### C3s 換股單（{o['book']} 簿）：{cal[o['M']].date()} 月底量測 → {ex}", "",
         "| 動作 | 代號 | 全名 | 月底排名 | 原因 |", "|---|---|---|---|---|"]
    for j, w in o["sells"]:
        L.append(f"| 賣 | {tick[j]} | {full_name(tick[j])} | {rank_of(T, e, j)[0] or '—'} | {w} |")
    for j in o["buys"]:
        L.append(f"| 買 | {tick[j]} | {full_name(tick[j])} | {rank_of(T, e, j)[0]} | |")
    for j in o["after"]:
        if j not in o["buys"]:
            L.append(f"| 續抱 | {tick[j]} | {full_name(tick[j])} | {rank_of(T, e, j)[0] or '—'} | |")
    L += ["", f"空槽 {K.N_SLOTS - len(o['after'])}", "", f"⚠ {IB_NOTE}"]
    return chr(10).join(L)


# ═════════════ 統計（看過段、描述）═════════════
def trade_stats(tr, cal, w1):
    def one(xs):
        if not xs:
            return {"筆數": 0}
        r = np.array([x[3] for x in xs]); nr = np.array([x[4] for x in xs if np.isfinite(x[4])])
        hd = np.array([x[2] - x[1] for x in xs], float)
        w = r[r > 0]; l_ = r[r <= 0]
        return {"筆數": int(len(xs)), "勝率": float((r > 0).mean()), "平均賺（%）": pct(w.mean()) if len(w) else None,
                "平均賠（%）": pct(l_.mean()) if len(l_) else None, "平均每筆（%）": pct(r.mean()),
                "賣出價距持有期最高收盤回落_中位（%）": pct(np.median(nr)),
                "持有天數_中位": float(np.median(hd)), "持有天數_p25": float(np.percentile(hd, 25)), "持有天數_p75": float(np.percentile(hd, 75)),
                "持有天數_最長": float(hd.max()), "持有天數_最短": float(hd.min()), "出場原因": dict(Counter(x[5] for x in xs))}
    done = [x for x in tr if x[2] <= w1]
    return {"全窗（2017-01-03～2026-09-30 出場）": one(done),
            "2022～（出場日 ≥ 2022-01-01）": one([x for x in done if cal[x[2]] >= SPLIT]),
            "口徑": "已出場筆（窗尾仍持有者不計）；報酬 ＝ 賣出價 ÷ 進場開盤價 − 1（未扣成本 0.05%）；勝 ＝ 報酬 ＞ 0、賠 ＝ ≤ 0；"
                    "回落 ＝ 賣出價 ÷ max(進場開盤價, 持有期每日收盤, 賣出價) − 1（＝ K.hold_stats 離頂多近）；持有天數 ＝ 交易日數（出場索引 − 進場索引）"}


# ═════════════ 主流程 ═════════════
def run_all():
    T0 = time.time()
    os.makedirs(OPSD, exist_ok=True); os.makedirs(PRIVD, exist_ok=True)
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; n = R["n"]; tick = W["tick"]
    gates = {}
    # 閘 0：擴充名單 ＝ 原版（≤ w1）
    S0 = C3.mom_scores(); B0, K0, _ = K.rank_tables(S0, R["memb"]["只500"])
    T = tables()
    gates["G0 擴充後 2017-01～2026-09 名單與原版相同（不同換股日數）"] = sum(int(B0[e] != T["BUY"][e] or K0[e] != T["KEEP"][e]) for e in B0)
    gates["G0 MOM 最大差"] = float(max(np.nanmax(np.abs(np.where(np.isfinite(S0[e]), S0[e] - T["S"][e], 0))) for e in S0))
    t0 = T["t0"]; a0 = t0 - 1
    res, tr = run_book(T, t0, w1)
    pk = pd.read_pickle(os.path.join(C3S.WORKD, "c3s_eq_trades.pkl"))
    gates["G1 權益 對 pickle 最大差"] = float(np.max(np.abs(res["eq"][:w1 + 1] - pk["eq"][:w1 + 1])))
    gates["G1 逐筆 對 pickle 相同"] = bool(len(tr) == len(pk["tr"]) and all(
        a[0] == b[0] and a[1] == b[1] and a[2] == b[2] and a[5] == b[5] and abs(a[3] - b[3]) <= 1e-12 for a, b in zip(tr, pk["tr"])))
    leq, pnl, openj, fills = C3S.ledger_book(W, T["KEEP"], T["BUY"], K.N_SLOTS, t0, w1)
    summ = json.load(open(os.path.join(C3S.OUTD, "summary.json"), encoding="utf-8"))
    tail_sum = set(summ["a 看過段"]["窗尾持股（2026-09-30）"])
    open_bk = {int(j): (int(b), float(hi)) for j, b, hi in res["open"]}
    tail_bk = {str(tick[j]) for j in open_bk}
    gates["G2 窗尾持股 ＝ ledger_book"] = bool(tail_bk == {str(tick[j]) for j in openj})
    gates["G2 窗尾持股 ＝ summary.json（pickle 同次產出）"] = bool(tail_bk == tail_sum)
    gates["G2 pickle 損益鍵 ⊇ 窗尾持股"] = bool(set(open_bk) <= set(int(k) for k in pk["pnl"]))
    # 1. 2026-09-30 持股
    e_now = w1 + 1                       # 2026-10-01：以 9/30 收盤 MOM 排名
    hold = []
    for j, (b, _hi) in sorted(open_bk.items(), key=lambda kv: rank_of(T, e_now, kv[0])[0] or 10 ** 6):
        r_in, d_in = rank_of(T, b, j); r_now, d_now = rank_of(T, e_now, j)
        hold.append({"代號": str(tick[j]), "進場月": cal[b].strftime("%Y-%m"), "進場日": str(cal[b].date()),
                     "進場時排名": r_in, "進場時分母": d_in, "目前排名（9/30 收盤）": r_now, "目前分母": d_now,
                     "持有期間漲幅（%）": pct(W["CF"][w1, j] / W["O"][b, j] - 1)})
    with open(os.path.join(OPSD, "holdings_20260930.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(list(hold[0].keys()))
        for h in hold:
            wr.writerow([("" if v is None else (f"{v:.2f}" if isinstance(v, float) else v)) for v in h.values()])
        for _ in range(K.N_SLOTS - len(hold)):
            wr.writerow(["（空槽）", "", "", "", "", "", "", "現金≈0，見 ops.json「1 空槽」"])
    # 9/30 權重（私有）：ledger 每檔損益扣已出場筆 ⇒ 未出場金額；閘：Σ 市值 ＋ 現金 ＝ 權益
    closed = defaultdict(float)
    for j, b, t_, amt, val in fills:
        closed[int(j)] += val - amt - amt * K.COST
    cash_w1 = float(res["cashf"][w1] * res["eq"][w1]); wts = {}
    for j, (b, _hi) in open_bk.items():
        r_ = W["CF"][w1, j] / W["O"][b, j] - 1
        amt = (pnl[j] - closed[j]) / r_
        wts[j] = amt * (1 + r_) / res["eq"][w1]
    gates["G2 權重恆等式 |Σ權重 ＋ 現金占比 − 1|"] = float(abs(sum(wts.values()) + cash_w1 / res["eq"][w1] - 1))
    # 空槽：何時開始、為何沒補
    npos = res["npos"]
    since = max(t for t in range(t0 + 1, w1 + 1) if npos[t] != npos[t - 1])
    why_empty = {"7 檔起始日": str(cal[since].date()), "9/30 現金占總值（%）": pct(cash_w1 / res["eq"][w1]),
                 "原因": "K.book 原式：新買金額 ＝ min(前一日總值 ÷ 8, 可用現金)、現金用完即停；賣出回收不夠補兩檔時第二檔不買，"
                         "之後持股漲跌都不再平衡 ⇒ 空槽一直留到下次有賣出回收現金（⛔ 不改規則，照原式）",
                 "主臂窗內持股＜8 的交易日": int((npos[t0:w1 + 1] < K.N_SLOTS).sum()), "主臂窗內交易日": int(w1 + 1 - t0)}
    # 2. 換股單 gate：最後 3 個歷史月底（e ≤ w1）；exact ＝ 真實 e 開盤、proxy ＝ 只用到月底資料（實盤當晚做法）
    rebs = sorted(e for e in T["BUY"] if t0 <= e <= w1)
    g2 = []
    for e in rebs[-3:]:
        sells_main = {x[0] for x in tr if x[2] == e and x[5] == "換股"}
        forced = [str(tick[x[0]]) + ":" + x[5] for x in tr if x[2] == e - 1 and x[5] != "換股"]
        row = {"月底": str(cal[e - 1].date()), "執行日": str(cal[e].date()),
               "主臂賣": sorted(str(tick[j]) for j in sells_main), "主臂換股後持股": sorted(str(tick[j]) for j in res["holds"][e]),
               "e 當日強制出場": forced}
        held_m = set()
        for mode in ("exact", "proxy"):
            o, _ = order_for(e - 1, "main", mode)
            held_m = set(o["held_before"])
            row[f"{mode} 賣"] = sorted(str(tick[j]) for j, _ in o["sells"])
            row[f"{mode} 買"] = sorted(str(tick[j]) for j in o["buys"])
            row[f"{mode} 換股後持股"] = sorted(str(tick[j]) for j in o["after"])
            row[f"{mode} 空槽候補"] = [str(tick[j]) for j in o["cand"]]
            row[f"{mode} 相同"] = bool(row[f"{mode} 賣"] == row["主臂賣"] and row[f"{mode} 換股後持股"] == row["主臂換股後持股"] and not forced)
        row["主臂買"] = sorted(str(tick[j]) for j in set(res["holds"][e]) - held_m)
        row["exact 相同"] &= row["exact 買"] == row["主臂買"]; row["proxy 相同"] &= row["proxy 買"] == row["主臂買"]
        g2.append(row)
    gates["G3 最後 3 個月底換股單 ＝ 主臂逐筆成交（exact）"] = f"{sum(x['exact 相同'] for x in g2)}／{len(g2)}"
    gates["G3 最後 3 個月底換股單 ＝ 主臂逐筆成交（proxy：只用月底前資料）"] = f"{sum(x['proxy 相同'] for x in g2)}／{len(g2)}"
    # 2b. 2026-09-30 月底換股單（10/1 開盤）：proxy（9/30 當晚做法）對 K.book 用真實 10/01 開盤跑出的成交
    o930, _ = order_for(w1, "main", "proxy")
    o930x, _ = order_for(w1, "main", "exact")
    res_x, tr_x = run_book(T, t0, e_now)
    same930 = (sorted(o930["after"]) == sorted(res_x["holds"][e_now]) == sorted(o930x["after"])
               and [j for j, _ in o930["sells"]] == [j for j, _ in o930x["sells"]] and o930["buys"] == o930x["buys"])
    gates["G4 9/30 換股單（proxy）＝ K.book 真實 10/01 開盤成交"] = bool(same930)
    gates["G4 延伸簿 ≤ 9/30 權益與主臂最大差"] = float(np.max(np.abs(res_x["eq"][:w1 + 1] - res["eq"][:w1 + 1])))
    cnt_v = W["valid"].sum(axis=1)
    lastc = max(t for t in range(w1, n) if cnt_v[t] >= 0.95 * cnt_v[w1])
    now = []
    open_x = {int(j): int(b) for j, b, _ in res_x["open"]}
    for j in o930x["after"]:
        b = open_x[j]
        r_in, d_in = rank_of(T, b, j); r_now, d_now = rank_of(T, e_now, j)
        now.append({"代號": str(tick[j]), "進場月": cal[b].strftime("%Y-%m"), "進場時排名": r_in, "進場時分母": d_in,
                    "目前排名（9/30 收盤）": r_now, "目前分母": d_now, "10/01 新買": j in o930x["buys"],
                    f"至 {cal[lastc].date()} 收盤持有漲幅（%）": pct(W["CF"][lastc, j] / W["O"][b, j] - 1)})
    # 3. 統計
    st = trade_stats(tr, cal, w1)
    a = summ["a 看過段"]; full = st["全窗（2017-01-03～2026-09-30 出場）"]
    gates["G5 統計 對 summary.json（筆數、勝率、持有天數中位／最長、回落中位）"] = bool(
        full["筆數"] == a["出場筆數"] and abs(full["勝率"] - a["出場勝率"]) <= 1e-12 and full["持有天數_中位"] == a["持有天數_中位"]
        and full["持有天數_最長"] == a["持有天數_最長"] and abs(full["賣出價距持有期最高收盤回落_中位（%）"] / 100 - a["離頂多近_中位"]) <= 1e-12)
    st["件"] = "USREG-C3s 逐筆統計（看過段、⛔ 只描述、不判）"; st["算於"] = K.now_tpe() + "（台北）"
    jd(st, os.path.join(OPSD, "stats.json"))
    # 私有：逐筆明細、換股單明細
    with open(os.path.join(PRIVD, "trades.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(["代號", "進場日", "出場日", "報酬", "距持有期最高回落", "持有交易日", "原因", "進場價", "出場價"])
        for x in tr:
            j, b, t_, r_, nr, why = x
            wr.writerow([str(tick[j]), str(cal[b].date()), str(cal[t_].date()), r_, nr, t_ - b, why, W["O"][b, j], W["O"][b, j] * (1 + r_)])
    wtab = {str(tick[j]): float(v) for j, v in sorted(wts.items(), key=lambda kv: -kv[1])}
    pd.to_pickle({"open_930": open_bk, "o930": o930, "g2": g2, "權重_20260930": wtab, "現金占比_20260930": cash_w1 / res["eq"][w1]},
                 os.path.join(PRIVD, "ops_detail.pkl"))
    with open(os.path.join(PRIVD, "weights_20260930.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(["代號", "9/30 收盤市值占總值"])
        for c, v in wtab.items():
            wr.writerow([c, v])
        wr.writerow(["現金", cash_w1 / res["eq"][w1]])
    cols, row = order_row(o930, T)
    with open(os.path.join(OPSD, f"order_{cal[w1].strftime('%Y%m%d')}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(cols); wr.writerow([row[c] for c in cols])
    allok = (gates["G0 擴充後 2017-01～2026-09 名單與原版相同（不同換股日數）"] == 0 and gates["G1 權益 對 pickle 最大差"] <= 1e-12
             and gates["G1 逐筆 對 pickle 相同"] and gates["G2 窗尾持股 ＝ ledger_book"] and gates["G2 窗尾持股 ＝ summary.json（pickle 同次產出）"]
             and gates["G2 權重恆等式 |Σ權重 ＋ 現金占比 − 1|"] <= 1e-9
             and all(x["exact 相同"] for x in g2) and gates["G4 9/30 換股單（proxy）＝ K.book 真實 10/01 開盤成交"]
             and gates["G5 統計 對 summary.json（筆數、勝率、持有天數中位／最長、回落中位）"])
    out = {"件": "USREG-C3s 可操作輸出（ops）", "規則": "S1 原樣（⛔ 不改登錄、不改規則、不加 N）；看過段只描述、不判",
           "資料": {"world": "~/us_work/a4/world.npz（us-stock-data 881c86a）", "日曆最後一日": str(cal[n - 1].date()), "主臂窗尾": str(cal[w1].date())},
           "1 2026-09-30 持股（主臂窗尾）": hold, "1 空槽": {"檔數": K.N_SLOTS - len(hold), **why_empty},
           "2 2026-09-30 月底換股單（10/01 開盤）": order_view(o930, T),
           "2 10/01 開盤後持股（現在該持有）": now,
           "2 權重": "各檔市值占比在 repo 外 weights_20260930.csv（S9：repo 只放代號、排名、漲幅）",
           "2 換股單 gate（最後 3 個歷史月底）": g2,
           "3 統計": "見 stats.json",
           "前瞻 ② 註": "forward_template（S7）是 2026-10 月底收盤起新開的 8 檔（空倉起算），與主臂續抱簿持股不同；用 --month <10 月最後交易日> --book forward 產第 0／1 列",
           "閘": gates, "全部閘通過": bool(allok),
           "私有": {"逐筆": os.path.join(PRIVD, "trades.csv"), "sha256": K.sha256f(os.path.join(PRIVD, "trades.csv"))},
           "存活者偏差": "S&P 500 有 18 檔不在母體 ⇒ 偏向存活股、偏樂觀（S10）",
           "算於": K.now_tpe() + "（台北）", "秒": round(time.time() - T0)}
    jd(out, os.path.join(OPSD, "ops.json"))
    print(json.dumps({"閘": gates, "全部閘通過": allok}, ensure_ascii=False, indent=1, default=K._jdef))
    return out


def run_month(d, book):
    R = K.rworld(); cal = R["cal"]
    M, virtual = month_end_index(d)
    o, T = order_for(M, book)
    v = order_view(o, T)
    if virtual:
        v["⚠"] = f"{d} 是資料最後一日，假設為當月最後交易日"
    cols, row = order_row(o, T)
    p = os.path.join(OPSD, f"order_{cal[M].strftime('%Y%m%d')}{'_forward' if book == 'forward' else ''}.csv")
    os.makedirs(OPSD, exist_ok=True)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(cols); wr.writerow([row[c] for c in cols])
    print(json.dumps(v, ensure_ascii=False, indent=1, default=K._jdef)); print(); print(order_md(o, T)); print("→", p)
    return v


# ═════════════ --check（獨立寫法：⛔ 不呼叫 mom_scores／rank_tables／book／ledger_book／order_for）═════════════
def check():
    T0 = time.time()
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; w1 = R["w1"]; n = R["n"]; tick = W["tick"]
    C, valid, pb, O, m5 = W["C"], W["valid"], W["pb"], W["O"], W["m5"]
    nS = C.shape[1]
    CFf = pd.DataFrame(C).ffill().to_numpy()
    mk = np.array([d.year * 12 + d.month - 1 for d in cal])
    lastd, firstd = {}, {}
    for i, k in enumerate(mk):
        lastd[int(k)] = i; firstd.setdefault(int(k), i)
    lastv = np.array([(np.flatnonzero(valid[:, j])[-1] if valid[:, j].any() else -1) for j in range(nS)])
    rebs = [firstd[k] for k in sorted(firstd) if 0 < firstd[k] < n and (k - 13) in lastd]

    def ranking(e):
        k = int(mk[e]); a12, a1 = lastd[k - 13], lastd[k - 2]
        el = []
        for j in range(nS):
            if not m5[e - 1, j]:
                continue
            if not valid[max(a12 - 4, 0):a12 + 1, j].any() or not valid[max(a1 - 4, 0):a1 + 1, j].any():
                continue
            if pb[a12 + 1:e, j].any():
                continue
            v = CFf[a1, j] / CFf[a12, j] - 1
            if np.isfinite(v):
                el.append((-v, j))
        el.sort()
        return [j for _, j in el]

    RK = {e: ranking(e) for e in rebs}
    RK = {e: v for e, v in RK.items() if v}
    rebset = sorted(RK); t0 = rebset[0]

    def lists(e):
        f = RK[e]; k1 = -(-len(f) // 10); k2 = -(-2 * len(f) // 10)
        return f[:k1], set(f[:k2])

    def sim(t_end):
        hold = {}; cash = 1.0; prev = 1.0; pend = set(); trades = []
        for t in range(t0, t_end + 1):
            for j in list(hold):
                h = hold[j]
                if t > h["b"] and pb[t, j]:
                    px = CFf[t - 1, j]; why = "斷點"
                elif t > lastv[j]:
                    px = CFf[lastv[j], j]; why = "下市"
                else:
                    continue
                del hold[j]; pend.discard(j)
                cash += h["u"] * px - h["a"] * K.COST
                trades.append((j, h["b"], t - 1, px / h["p"] - 1, px / h["hi"] - 1, why))
            if t in RK:
                bl, kl = lists(t)
                pend = (pend | {j for j in hold if j not in kl}) - kl
            for j in sorted(pend):
                if j not in hold:
                    pend.discard(j); continue
                if valid[t, j] and np.isfinite(O[t, j]) and O[t, j] > 0:
                    h = hold.pop(j); pend.discard(j); px = O[t, j]
                    cash += h["u"] * px - h["a"] * K.COST
                    trades.append((j, h["b"], t, px / h["p"] - 1, px / max(h["hi"], px) - 1, "換股"))
            if t in RK:
                for j in [j for j in bl if j not in hold][:max(8 - len(hold), 0)]:
                    if not (valid[t, j] and np.isfinite(O[t, j]) and O[t, j] > 0):
                        continue
                    amt = min(prev / 8, cash)
                    if amt <= 1e-12:
                        break
                    cash -= amt; hold[j] = {"u": amt / O[t, j], "a": amt, "b": t, "p": O[t, j], "hi": O[t, j]}
            v = cash
            for j, h in hold.items():
                v += h["u"] * CFf[t, j]; h["hi"] = max(h["hi"], CFf[t, j])
            prev = v
        return hold, trades, cash

    hold, trades, cash_c = sim(w1)
    ops = json.load(open(os.path.join(OPSD, "ops.json"), encoding="utf-8"))
    sts = json.load(open(os.path.join(OPSD, "stats.json"), encoding="utf-8"))
    diffs = []; nchk = 0
    e_now = w1 + 1
    mine = {}
    for j, h in hold.items():
        mine[str(tick[j])] = {"進場日": str(cal[h["b"]].date()), "進場時排名": RK[h["b"]].index(j) + 1,
                              "目前排名（9/30 收盤）": (RK[e_now].index(j) + 1) if j in RK[e_now] else None,
                              "持有期間漲幅（%）": (CFf[w1, j] / h["p"] - 1) * 100}
    theirs = {h["代號"]: h for h in ops["1 2026-09-30 持股（主臂窗尾）"]}
    nchk += 1
    if set(mine) != set(theirs):
        diffs.append(("持股集合", sorted(mine), sorted(theirs)))
    for c, m in mine.items():
        if c not in theirs:
            continue
        for k_ in ("進場日", "進場時排名", "目前排名（9/30 收盤）"):
            nchk += 1
            if m[k_] != theirs[c][k_]:
                diffs.append((c, k_, m[k_], theirs[c][k_]))
        nchk += 1
        if abs(m["持有期間漲幅（%）"] - theirs[c]["持有期間漲幅（%）"]) > TOL:
            diffs.append((c, "漲幅", m["持有期間漲幅（%）"], theirs[c]["持有期間漲幅（%）"]))

    # 換股單：最後 3 個歷史月底 ＋ 9/30（獨立：月底持股 ＋ 規則）
    # 權重（repo 外檔）：獨立記帳的 9/30 市值占比
    det = pd.read_pickle(os.path.join(PRIVD, "ops_detail.pkl"))
    eqw = sum(h["u"] * CFf[w1, j] for j, h in hold.items())       # 現金另加
    tot_c = eqw + cash_c
    for c_, v_ in det["權重_20260930"].items():
        j = int(W["ix"][c_]); nchk += 1
        if j not in hold or abs(hold[j]["u"] * CFf[w1, j] / tot_c - v_) > TOL:
            diffs.append(("權重", c_, v_))

    def order_ind(e):
        hb = sim(e - 1)[0]; ha = sim(e)[0]
        return sorted(str(tick[j]) for j in hb if j not in ha), sorted(str(tick[j]) for j in ha if j not in hb)
    hist = [e for e in rebset if e <= w1][-3:]
    for e, g in zip(hist, ops["2 換股單 gate（最後 3 個歷史月底）"]):
        s_, b_ = order_ind(e); nchk += 2
        if not (s_ == g["exact 賣"] == g["主臂賣"]):
            diffs.append((str(cal[e].date()), "賣", s_, g["exact 賣"], g["主臂賣"]))
        if not (b_ == g["exact 買"] == g["主臂買"]):
            diffs.append((str(cal[e].date()), "買", b_, g["exact 買"], g["主臂買"]))
    s_, b_ = order_ind(e_now); o9 = ops["2 2026-09-30 月底換股單（10/01 開盤）"]; nchk += 2
    if s_ != sorted(x["代號"] for x in o9["賣"]):
        diffs.append(("9/30", "賣", s_, o9["賣"]))
    if b_ != sorted(x["代號"] for x in o9["買（依序）"]):
        diffs.append(("9/30", "買", b_, o9["買（依序）"]))

    # 統計
    done = [x for x in trades if x[2] <= w1]

    def st(xs):
        r = [x[3] for x in xs]; nr = sorted(x[4] for x in xs if np.isfinite(x[4])); hd = sorted(x[2] - x[1] for x in xs)
        w = [v for v in r if v > 0]; lo = [v for v in r if v <= 0]

        def med(a):
            m = len(a); return (a[m // 2] if m % 2 else (a[m // 2 - 1] + a[m // 2]) / 2)

        def q(a, p):
            x = p * (len(a) - 1); i = int(np.floor(x)); f = x - i
            return a[i] + (a[min(i + 1, len(a) - 1)] - a[i]) * f
        return {"筆數": len(xs), "勝率": len(w) / len(r), "平均賺（%）": sum(w) / len(w) * 100, "平均賠（%）": sum(lo) / len(lo) * 100,
                "平均每筆（%）": sum(r) / len(r) * 100, "賣出價距持有期最高收盤回落_中位（%）": med(nr) * 100,
                "持有天數_中位": float(med(hd)), "持有天數_p25": float(q(hd, 0.25)), "持有天數_p75": float(q(hd, 0.75)),
                "持有天數_最長": float(hd[-1]), "持有天數_最短": float(hd[0])}
    for name, xs in (("全窗（2017-01-03～2026-09-30 出場）", done), ("2022～（出場日 ≥ 2022-01-01）", [x for x in done if cal[x[2]] >= SPLIT])):
        mine_s = st(xs)
        for k_, v in mine_s.items():
            nchk += 1
            if abs(v - sts[name][k_]) > TOL:
                diffs.append((name, k_, v, sts[name][k_]))
    out = {"件": "USREG-C3s ops --check（獨立寫法：逐股迴圈排名、dict 換股簿；⛔ 不呼叫 mom_scores／rank_tables／book／ledger_book／order_for）",
           "比對項數": nchk, "不同": len(diffs), "不同明細": [list(map(str, d)) for d in diffs], "容差": TOL,
           "算於": K.now_tpe() + "（台北）", "秒": round(time.time() - T0)}
    jd(out, os.path.join(OPSD, "check_ops.json"))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="月底日期 YYYY-MM-DD（當月最後交易日）⇒ 下一交易日開盤的換股單")
    ap.add_argument("--book", choices=("main", "forward"), default="main")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        check()
    elif a.month:
        run_month(a.month, a.book)
    else:
        run_all()


if __name__ == "__main__":
    main()

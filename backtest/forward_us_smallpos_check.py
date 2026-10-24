# -*- coding: utf-8 -*-
"""forward_us_smallpos 的 fixture 自測（合成資料、⛔ 不碰私有庫、⛔ 不寫 repo 紀錄夾）——回測線計算子代理，2026-10-24（台北）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_smallpos_check

項目：T1 起點補記（資料未到起點不寫；到了寫 1 份成交＋進場檢查）｜T2 10/30 月底無新季報 ⇒「不判」｜T3 甲轉強 ⇒ 次一交易日加 2 份、只一次、之後不再判｜
      T4 乙（首次 8 季新高）轉強且甲不成立｜T5 第 4 份新季報仍未轉強 ⇒ 次一交易日賣、月份無季報皆「不判」｜T6 進場時已轉強標記｜
      T7 資料晚到補判｜T8 冪等（重跑零新列、book 位元組相同）＋逐晚跑 ＝ 一次補跑｜T9 私有欄不外洩（repo 檔無價格／營收值）｜
      T10 --dry 不寫檔｜T11 月底外推（Memorial Day、Good Friday）｜T12 事件行（轉強、放棄、新候選前一晚、別晚不出）
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import forward_us_smallpos as F      # noqa: E402

RES = []


def ok(name, cond, info=""):
    RES.append((name, bool(cond), info))
    print(("PASS " if cond else "FAIL ") + name + (f"｜{info}" if info else ""))


def bdays(a, b):
    out, d = [], pd.Timestamp(a).date()
    while d <= pd.Timestamp(b).date():
        if d.weekday() < 5 and d not in F.nyse_holidays(d.year):
            out.append(pd.Timestamp(d))
        d += dt.timedelta(days=1)
    return out


CAL = bdays("2024-01-02", "2027-12-31")
QS = pd.period_range("2021Q1", "2027Q4", freq="Q")


def filed(q):
    e = q.end_time.normalize()
    return (e + pd.Timedelta(days=57 if q.quarter == 4 else 35)).date()  # Q3 2026 ⇒ 11-04；Q4 ⇒ 2-26；Q1 ⇒ 5-05；Q2 ⇒ 8-04


def revenue(kind):
    v = {}
    for i, q in enumerate(QS):
        x = 5000000000 * 1.005 ** i                                  # 穩定成長：年增＝近 4 季年增 ⇒ 甲不成立；每季都新高 ⇒ 乙「首次」不成立
        v[q] = x
    if kind == "jia":                                                # 2026Q3 起跳 20% ⇒ 甲成立（乙：上一季已是新高 ⇒ 不成立）
        for q in QS:
            if q >= pd.Period("2026Q3", "Q"):
                v[q] *= 1.20
    if kind == "yi":                                                 # 平 100、2025Q3=101、之後 99×3、2026Q3=101.5 ⇒ 首次 8 季新高、甲不成立
        for q in QS:
            v[q] = 5000000000.0
        for q, k in (("2025Q3", 1.01), ("2025Q4", .99), ("2026Q1", .99), ("2026Q2", .99), ("2026Q3", 1.015), ("2026Q4", 1.0), ("2027Q1", 1.0), ("2027Q2", 1.0)):
            v[pd.Period(q, "Q")] = 5000000000.0 * k
    if kind == "entry":                                              # 2026Q2 起跳 ⇒ 進場時已轉強；2026Q3 照穩定（相對已跳）
        for q in QS:
            if q >= pd.Period("2026Q2", "Q"):
                v[q] *= 1.20
    return v


def build(root, kind, drop=()):
    for sub in ("prices_yahoo", "macro", "fundamentals"):
        os.makedirs(os.path.join(root, "data", sub), exist_ok=True)
    n = len(CAL)
    o = 137.4219 + np.arange(n) * 0.0731 + np.sin(np.arange(n) / 7.0) * 3.3
    c = o + 0.4113
    pd.DataFrame({"date": [d.strftime("%Y-%m-%d") for d in CAL], "open": o, "high": c + 1, "low": o - 1, "close": c,
                  "adjclose": c * 0.9713, "volume": 1000}).to_csv(os.path.join(root, "data", "prices_yahoo", "ETN.csv"), index=False)
    g = pd.DataFrame({"date": [d.strftime("%Y-%m-%d") for d in CAL], "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1})
    g.to_csv(os.path.join(root, "data", "macro", "yahoo_GSPC.csv"), index=False)
    pd.DataFrame({"date": g["date"], "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1,
                  "adjclose": 9000.1234 * 1.0003 ** np.arange(n)}).to_csv(os.path.join(root, "data", "macro", "yahoo_SP500TR.csv"), index=False)
    v = revenue(kind)
    rows = []
    for q in QS:
        if str(q) in drop:
            continue
        rows.append({"ticker": "ETN", "cik": "1551182", "period_start": q.start_time.date(), "period_end": q.end_time.date(),
                     "value": int(round(v[q])), "first_filed": filed(q), "first_form": "10-K" if q.quarter == 4 else "10-Q",
                     "latest_value": int(round(v[q] * 1.37)), "latest_filed": filed(q), "tag": "Revenues", "derived": int(q.quarter == 4)})
    pd.DataFrame(rows).to_csv(os.path.join(root, "data", "fundamentals", "quarterly_revenue.csv"), index=False)
    return v


NOW = pd.Timestamp("2026-10-24 20:00")


def nightly(root, fwd, priv, a, b, now=None):
    out = []
    for d in [x for x in CAL if pd.Timestamp(a) <= x <= pd.Timestamp(b)]:
        out.append(F.run(F.Src(root), fwd, priv, asof=str(d.date()), now=now or (d + pd.Timedelta(hours=44)), quiet=True))
    return out


def book(fwd):
    return F.read_rows(os.path.join(fwd, "book.csv"))


def strip(rows):
    return [{k: v for k, v in r.items() if k not in ("recorded_at", "note")} | {"note": re.sub(r"資料日 \S+ 晚補記", "", r["note"])} for r in rows]


def main():
    T = tempfile.mkdtemp(prefix="smallpos_chk_")
    real_us = dict(F.USER_SELL)
    F.USER_SELL.clear()                              # 機制情境不含使用者指示賣出（最後另測）
    try:
        # ── 情境 A：穩定成長（永不轉強 ⇒ 放棄）
        rA = os.path.join(T, "A"); fA = os.path.join(T, "fwdA"); pA = os.path.join(T, "privA")
        vA = build(rA, "flat")
        o = F.run(F.Src(rA), fA, pA, asof="2026-10-22", now=pd.Timestamp("2026-10-23 08:00"), quiet=True)
        ok("T1a 資料未到起點 ⇒ 不寫起點列", not any(r["event"] == "起點買進" for r in o["rows"]), o["summary"][:60])
        ok("T12c 新候選前一晚事件行", o["ev"] == ["美股小部位：ETN 新增 ⇒ 明天開盤買 1 份"], str(o["ev"]))
        o2 = F.run(F.Src(rA), os.path.join(T, "x"), os.path.join(T, "xp"), asof="2026-10-22", now=NOW, dry=True, quiet=True)
        ok("T12d 起點已過（台北今天 10/24）不出新候選行", o2["ev"] == [], str(o2["ev"]))
        ok("T10 --dry 不寫任何檔", not os.path.exists(os.path.join(T, "x")) and not os.path.exists(os.path.join(T, "xp")))
        nightly(rA, fA, pA, "2026-10-23", "2027-09-10")
        B = book(fA)
        b0 = [r for r in B if r["event"] == "起點買進"]
        ok("T1b 起點補記 2026-10-23 1 份成交", len(b0) == 1 and b0[0]["trade_date"] == "2026-10-23" and b0[0]["units"] == "1" and b0[0]["status"] == "成交")
        ent = [r for r in B if r["event"] == "進場檢查"]
        ok("T1c 進場檢查用起點前最近一份（2026Q2）、未轉強", len(ent) == 1 and ent[0]["report_q"] == "2026Q2" and ent[0]["judge"] == "進場時未轉強", ent[0]["judge"] if ent else "")
        j = [r for r in B if r["event"] in F.JUDGE_EV]
        oct_ = [r for r in j if r["judge_date"] == "2026-10-30"]
        ok("T2 10/30 無新季報 ⇒ 不判", len(oct_) == 1 and oct_[0]["judge"] == F.NOJUDGE and not oct_[0]["report_q"])
        jq = [r for r in j if r["report_q"]]
        ok("T5a 4 份新季報依序 2026Q3、2026Q4、2027Q1、2027Q2，判定日＝月底（含 2027-05-28 Memorial Day 前）",
           [(r["report_q"], r["judge_date"], r["report_n"]) for r in jq] == [("2026Q3", "2026-11-30", "1"), ("2026Q4", "2027-02-26", "2"),
                                                                             ("2027Q1", "2027-05-28", "3"), ("2027Q2", "2027-08-31", "4")],
           str([(r["report_q"], r["judge_date"]) for r in jq]))
        ok("T5b 都未轉強、第 4 份放棄判定", all(r["judge"] == "未轉強" for r in jq) and "放棄判定" in jq[-1]["note"])
        s = [r for r in B if r["event"] == F.SELL_EV]
        ok("T5c 次一交易日 2027-09-01 開盤賣 −1 份（未確認）", len(s) == 1 and s[0]["trade_date"] == "2027-09-01" and s[0]["units"] == "-1" and s[0]["status"] == "未確認賣出")
        nj = sorted(r["judge_date"] for r in j if not r["report_q"])
        ok("T5d 無季報月份都記「不判」（10、12、1、3、4、6、7 月）", nj == ["2026-10-30", "2026-12-31", "2027-01-29", "2027-03-31", "2027-04-30", "2027-06-30", "2027-07-30"], str(nj))
        ok("T5e 放棄後不再判", not [r for r in j if r["judge_date"] > "2027-08-31"])
        o = F.run(F.Src(rA), os.path.join(T, "y"), os.path.join(T, "yp"), asof="2027-08-31", now=NOW, quiet=True)
        ok("T12b 放棄事件行（判定那晚）", o["ev"] == ["美股小部位：ETN 第 4 份新季報仍未轉強 ⇒ 明天開盤賣"], str(o["ev"]))
        # T8 冪等＋逐晚＝補跑
        raw = open(os.path.join(fA, "book.csv"), "rb").read()
        o = F.run(F.Src(rA), fA, pA, asof="2027-09-10", now=NOW, quiet=True)
        ok("T8a 重跑零新列、book 位元組相同", not o["new"] and open(os.path.join(fA, "book.csv"), "rb").read() == raw)
        F.run(F.Src(rA), os.path.join(T, "batch"), os.path.join(T, "batchp"), asof="2027-09-10", now=NOW, quiet=True)
        ok("T8b 逐晚跑 ＝ 一次補跑（除記錄時間與補記註）", strip(book(fA)) == strip(book(os.path.join(T, "batch"))))
        # T9 私有不外洩
        txt = "".join(open(os.path.join(fA, f), encoding="utf-8-sig").read() for f in ("book.csv", "state.json", "runlog.md"))
        dec = [x for x in re.findall(r"(?<![\d.])\d+\.\d+(?!\d*%)", txt)]
        big = re.findall(r"(?<!\d)\d{7,}(?!\d)", txt)
        ok("T9a repo 檔無小數價格（只有 % 彙總）", not dec, str(dec[:5]))
        ok("T9b repo 檔無營收值（無 7 位以上數字）", not big, str(big[:5]))
        priv_ok = all(os.path.exists(os.path.join(pA, f)) for f in ("smallpos_daily.csv", "smallpos_rev.csv", "smallpos_fills.csv"))
        fl = F.read_rows(os.path.join(pA, "smallpos_fills.csv"))
        ok("T9c 價格／營收細節在私有檔（fills 2 筆：起點、賣出）", priv_ok and [r["event"] for r in fl] == ["起點買進", "放棄賣出"])
        st = json.load(open(os.path.join(fA, "state.json"), encoding="utf-8"))
        ok("T9d state 彙總只有 %", st["組合（照規則欄）"]["累計報酬"].endswith("%") and st["候選"]["ETN"]["狀態"] == "已賣（未確認）", st["組合（照規則欄）"]["累計報酬"])

        # ── 情境 B：甲
        rB = os.path.join(T, "B"); fB = os.path.join(T, "fwdB"); pB = os.path.join(T, "privB")
        build(rB, "jia")
        nightly(rB, fB, pB, "2026-10-23", "2027-09-10")
        B = book(fB); j = [r for r in B if r["event"] in F.JUDGE_EV and r["report_q"]]
        ok("T3a 2026Q3 於 2026-11-30 判轉強（甲成立、乙不成立）", len(j) == 1 and j[0]["judge"] == "轉強" and j[0]["judge_date"] == "2026-11-30"
           and "甲 成立" in j[0]["judge_detail"] and "乙 不成立" in j[0]["judge_detail"], j[0]["judge_detail"] if j else "")
        ad = [r for r in B if r["event"] == "轉強加碼"]
        ok("T3b 次一交易日 2026-12-01 開盤加 2 份、只一次", len(ad) == 1 and ad[0]["trade_date"] == "2026-12-01" and ad[0]["units"] == "2")
        ok("T3c 確認後不再判、不賣", not [r for r in B if r["event"] in F.JUDGE_EV and r["judge_date"] > "2026-11-30"] and not [r for r in B if r["event"] == F.SELL_EV])
        o = F.run(F.Src(rB), os.path.join(T, "z"), os.path.join(T, "zp"), asof="2026-11-30", now=NOW, quiet=True)
        o1 = F.run(F.Src(rB), os.path.join(T, "z"), os.path.join(T, "zp"), asof="2026-11-30", now=NOW, quiet=True)
        o2 = F.run(F.Src(rB), os.path.join(T, "z"), os.path.join(T, "zp"), asof="2026-12-01", now=NOW, quiet=True)
        ok("T12a 轉強事件行：判定那晚出、同資料日重跑原樣、隔晚不出",
           o["ev"] == ["美股小部位：ETN 轉強 ⇒ 明天開盤加 2 份"] and o1["ev"] == o["ev"] and not o1["new"] and o2["ev"] == [], f"{o['ev']} {o2['ev']}")
        # ── 情境 C：乙
        rC = os.path.join(T, "C"); fC = os.path.join(T, "fwdC"); pC = os.path.join(T, "privC")
        build(rC, "yi")
        F.run(F.Src(rC), fC, pC, asof="2026-12-10", now=NOW, quiet=True)
        B = book(fC); j = [r for r in B if r["event"] in F.JUDGE_EV and r["report_q"]]
        ok("T4 乙：首次 8 季新高 ⇒ 轉強（甲不成立）", len(j) == 1 and j[0]["judge"] == "轉強" and "甲 不成立" in j[0]["judge_detail"] and "乙 成立" in j[0]["judge_detail"],
           j[0]["judge_detail"] if j else "")
        ok("T4b 乙情境加碼 2026-12-01", [r["trade_date"] for r in B if r["event"] == "轉強加碼"] == ["2026-12-01"])
        # ── 情境 D：進場時已轉強
        rD = os.path.join(T, "D"); fD = os.path.join(T, "fwdD"); pD = os.path.join(T, "privD")
        build(rD, "entry")
        F.run(F.Src(rD), fD, pD, asof="2026-10-23", now=NOW, quiet=True)
        e = [r for r in book(fD) if r["event"] == "進場檢查"]
        ok("T6 進場時已轉強標記（2026Q2）", len(e) == 1 and e[0]["judge"] == "進場時已轉強" and e[0]["report_q"] == "2026Q2" and "不當「確認前」樣本" in e[0]["note"])
        # ── 情境 E：資料晚到（2026Q3 列 12/03 才進庫）
        rE = os.path.join(T, "E"); fE = os.path.join(T, "fwdE"); pE = os.path.join(T, "privE")
        build(rE, "jia", drop=("2026Q3",))
        nightly(rE, fE, pE, "2026-10-23", "2026-12-02")
        nov = [r for r in book(fE) if r["judge_date"] == "2026-11-30"]
        ok("T7a 11/30 當時庫無 2026Q3 ⇒ 不判", len(nov) == 1 and nov[0]["judge"] == F.NOJUDGE)
        build(rE, "jia")
        o = F.run(F.Src(rE), fE, pE, asof="2026-12-03", now=NOW, quiet=True)
        B = book(fE); lt = [r for r in B if r["event"] == "補判（資料晚到）"]
        ok("T7b 進庫那晚補判轉強、事件行出", len(lt) == 1 and lt[0]["judge_date"] == "2026-12-03" and lt[0]["judge"] == "轉強" and o["ev"] == ["美股小部位：ETN 轉強 ⇒ 明天開盤加 2 份"])
        F.run(F.Src(rE), fE, pE, asof="2026-12-04", now=NOW, quiet=True)
        ok("T7c 補判後次一交易日 12/04 加 2 份", [r["trade_date"] for r in book(fE) if r["event"] == "轉強加碼"] == ["2026-12-04"])
        F.run(F.Src(rE), fE, pE, asof="2026-12-31", now=NOW, quiet=True)
        ok("T7d 補判後 12 月底不再判", not [r for r in book(fE) if r["judge_date"] == "2026-12-31"])
        # ── T11 月底外推
        def me(D):
            cal = pd.DatetimeIndex([x for x in bdays("2024-01-02", D)])
            return pd.Timestamp(D) in F.month_ends(cal, pd.Timestamp(D))
        ok("T11 月底外推：2027-05-28（5/31 Memorial）、2024-03-28（3/29 Good Friday）、2026-10-30 是；2026-10-29、2027-05-27 不是",
           me("2027-05-28") and me("2024-03-28") and me("2026-10-30") and not me("2026-10-29") and not me("2027-05-27"))
        ok("T11b NYSE 休市：2026-11-26 感恩節、2026-12-25、2027-07-05（7/4 週日補）、2027-12-24（聖誕週六前一天）",
           {dt.date(2026, 11, 26), dt.date(2026, 12, 25)} <= F.nyse_holidays(2026) and {dt.date(2027, 7, 5), dt.date(2027, 12, 24)} <= F.nyse_holidays(2027))
    finally:
        shutil.rmtree(T, ignore_errors=True)
    n = sum(1 for _, c, _ in RES if c)
    # ── 情境 U：使用者指示賣出（產業 seq17／19／20）
    T2 = tempfile.mkdtemp(prefix="smallpos_chkU_")
    try:
        F.USER_SELL.clear(); F.USER_SELL.update({"ETN": ("2026-10-26", "往前看判準不過，你 10/25 同意", "產業 seq17")})
        rU = os.path.join(T2, "U"); fU = os.path.join(T2, "fwdU"); pU = os.path.join(T2, "privU")
        build(rU, "flat")
        nightly(rU, fU, pU, "2026-10-23", "2026-10-23")
        oU = F.run(F.Src(rU), fU, pU, asof="2026-10-23", now=pd.Timestamp("2026-10-25 20:00"), quiet=True)
        ok("TU1 指示賣出前一晚事件行「ETN ⇒ 10/26（一）美股開盤賣（台北當晚；…）」", oU["ev"] == ["美股小部位：ETN ⇒ 10/26（一）美股開盤賣（台北當晚；往前看判準不過，你 10/25 同意）"], str(oU["ev"]))
        nightly(rU, fU, pU, "2026-10-24", "2027-09-10")
        BU = book(fU)
        su = [r for r in BU if r["event"] == F.USER_SELL_EV]
        ok("TU2 10/26 開盤記「使用者指示賣出」−1 份、之後不再判定、不放棄", len(su) == 1 and su[0]["trade_date"] == "2026-10-26" and su[0]["units"] == "-1"
           and su[0]["status"] == "指示賣出" and not [r for r in BU if r["event"] in F.JUDGE_EV and r["judge"] in ("轉強", "未轉強")]
           and not [r for r in BU if r["event"] == F.SELL_EV], str([(r["event"], r["trade_date"]) for r in BU][-4:]))
    finally:
        shutil.rmtree(T2, ignore_errors=True)
        F.USER_SELL.clear(); F.USER_SELL.update(real_us)
    ok("TU3 實設定：ETN 2026-10-26 指示賣出", F.USER_SELL.get("ETN", ("",))[0] == "2026-10-26")
    n = sum(1 for _, c, _ in RES if c)
    print(f"自測：{n}/{len(RES)} 過")
    raise SystemExit(0 if n == len(RES) else 1)


if __name__ == "__main__":
    main()

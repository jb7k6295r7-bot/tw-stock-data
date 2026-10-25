# -*- coding: utf-8 -*-
"""forward_us_v4 的 fixture 自測（合成資料、⛔ 不碰私有庫、⛔ 不寫 repo 紀錄夾）——回測線程式子代理，2026-10-25（台北）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_v4_check

項目：T1 未核（APPROVED=None）只乾跑、任何檔都不寫｜T2 核後起點補記（10/23 只記 K1★、10/26 起點 1 份；晚跑補記同日）｜
      T3 起點無 K 棒順延｜T4 ADDS 成交、SELLS 成交與順延、賣光｜T5 冪等（重跑零新列、book 位元組相同）＋逐晚＝補跑｜
      T6 私有欄不外洩｜T7 K1a／b／c 對手算值（代替月底與月底兩列；月底列只在燈亮月最後交易日之後出）｜
      T8 實際欄（使用者回報檔；repo 無股數價格；報酬對手算）｜T9 核後 --dry 不寫｜T10 月底淨值列｜T11 規則欄報酬、^SP500TR、賣後回 SPY 對手算
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import forward_us_v4 as F      # noqa: E402

RES = []
OK_SEQ = "seqTEST"


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


CAL = bdays("2023-01-03", "2027-03-31")
N = len(CAL)
I = np.arange(N)
SER = {   # 代號: (open, close, adjclose)
    "BE": (61.3127 + I * 0.0913 + np.sin(I / 9.0) * 6.1,),
    "LRCX": (88.4411 + I * 0.0517 + np.cos(I / 13.0) * 4.7,),
}
for t in SER:
    o = SER[t][0]; c = o * 1.0037 + 0.1311
    adj = c * (0.9411 + 0.0589 * I / N)                       # 還原係數逐日變（測 × adjclose ÷ close）
    SER[t] = (o, c, adj)
TRV = 9000.1234 * 1.00031 ** I + np.sin(I / 5.0) * 7.3
SPYO = 401.2231 + I * 0.0711; SPYC = SPYO + 0.3127; SPYA = SPYC * 0.9833


def build(root, drop=None):
    drop = drop or {}
    for sub in ("prices_yahoo", "macro"):
        os.makedirs(os.path.join(root, "data", sub), exist_ok=True)
    ds = [d.strftime("%Y-%m-%d") for d in CAL]
    for t, (o, c, a) in SER.items():
        df = pd.DataFrame({"date": ds, "open": o, "high": c + 1, "low": o - 1, "close": c, "adjclose": a, "volume": 1000})
        df = df[~df["date"].isin(drop.get(t, []))]
        df.to_csv(os.path.join(root, "data", "prices_yahoo", f"{t}.csv"), index=False)
    pd.DataFrame({"date": ds, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}).to_csv(os.path.join(root, "data", "macro", "yahoo_GSPC.csv"), index=False)
    pd.DataFrame({"date": ds, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1, "adjclose": TRV}).to_csv(
        os.path.join(root, "data", "macro", "yahoo_SP500TR.csv"), index=False)
    pd.DataFrame({"date": ds, "open": SPYO, "high": SPYC + 1, "low": SPYO - 1, "close": SPYC, "volume": 1, "adjclose": SPYA}).to_csv(
        os.path.join(root, "data", "macro", "yahoo_SPY.csv"), index=False)


def ix(d):
    return CAL.index(pd.Timestamp(d))


def aopen(t, d):
    o, c, a = SER[t]; i = ix(d); return o[i] * a[i] / c[i]


def aclose(t, d):
    return SER[t][2][ix(d)]


def tr(d):
    return TRV[ix(d)]


def prev(d):
    return CAL[ix(d) - 1]


def k1_hand(t, close_d, M):
    """手算：月底收盤表 ⇒ K1a／b／c（窗 M−23～M，M 用 close_d 的收盤）。"""
    a = SER[t][2]
    me = {}
    for i, d in enumerate(CAL):
        if d <= pd.Timestamp(close_d):
            me[d.to_period("M")] = (d, a[i])
    c = aclose(t, close_d)
    bd, b = me[M - 6]
    win = [me[M - k][1] for k in range(1, 24)] + [c]
    ka = c / b
    return ka, ka / (tr(close_d) / tr(bd)), c / min(win)


NOW = pd.Timestamp("2026-10-25 20:00")


def run(root, fwd, priv, asof, approved=OK_SEQ, dry=False, now=None):
    return F.run(F.Src(root), fwd, priv, asof=asof, dry=dry, now=now or NOW, quiet=True, approved=approved)


def book(fwd):
    return F.read_rows(os.path.join(fwd, "book.csv"))


def ev(rows, t, e):
    return [r for r in rows if r["ticker"] == t and r["event"] == e]


def files(*ds):
    return [os.path.join(dp, f) for d in ds if os.path.exists(d) for dp, _, fs in os.walk(d) for f in fs]


def main():
    T = tempfile.mkdtemp(prefix="v4_chk_")
    R = os.path.join(T, "root"); build(R)
    ok("T0 常數 APPROVED 預設 None（未核）", F.APPROVED is None, repr(F.APPROVED))
    # T1 未核
    fw, pv = os.path.join(T, "f1"), os.path.join(T, "p1")
    o = run(R, fw, pv, "2026-11-05", approved=None)
    ok("T1a 未核：任何檔都不寫（紀錄夾、私有夾都不存在）", not files(fw, pv) and o["dry"], str(files(fw, pv)))
    ok("T1b 未核：彙總標「未核…只乾跑」、最後行首「美股 v4 小部位：」", o["summary"].startswith("美股 v4 小部位：") and "未核（APPROVED=None）⇒ 只乾跑、不寫" in o["summary"])
    ok("T1c 未核：乾跑仍算得出起點列與 K1★（記憶體）", {r["event"] for r in o["new"]} >= {"起點買進", F.K1P, F.K1M}, str(sorted({r["event"] for r in o["new"]})))
    o = F.run(F.Src(R), fw, pv, asof="2026-11-05", now=NOW, quiet=True)          # 用模組常數（None）
    ok("T1d 不傳 approved ⇒ 用常數 None ⇒ 不寫", not files(fw, pv) and o["dry"])

    # T2 核後：逐晚跑 10/22～2027-01-29
    fA, pA = os.path.join(T, "fA"), os.path.join(T, "pA")
    o22 = run(R, fA, pA, "2026-10-22")
    ok("T2a 10/22：還不是開卡前最後一個收盤 ⇒ 不記 K1★、不記起點", not o22["new"], str([r["event"] for r in o22["new"]]))
    o23 = run(R, fA, pA, "2026-10-23")
    ok("T2b 10/23：兩卡記 K1★（代替月底，收盤日 10/23）、不記起點",
       sorted((r["ticker"], r["event"], r["k1_close_date"]) for r in o23["new"]) == [("BE", F.K1P, "2026-10-23"), ("LRCX", F.K1P, "2026-10-23")])
    o26 = run(R, fA, pA, "2026-10-26")
    st = [(r["ticker"], r["trade_date"], r["units"], r["status"]) for r in o26["new"] if r["event"] == "起點買進"]
    ok("T2c 10/26：兩卡起點 1 份成交", sorted(st) == [("BE", "2026-10-26", "1", "成交"), ("LRCX", "2026-10-26", "1", "成交")], str(st))
    fl = F.read_rows(os.path.join(pA, "v4_fills.csv"))
    ok("T2d 起點原始開盤價只在私有 fills、等於 fixture open",
       len(fl) == 2 and all(abs(float(r["yahoo_open_raw"]) - SER[r["ticker"]][0][ix("2026-10-26")]) < 1e-9 for r in fl))
    for d in CAL:
        if pd.Timestamp("2026-10-27") <= d <= pd.Timestamp("2027-01-29"):
            run(R, fA, pA, str(d.date()), now=d + pd.Timedelta(hours=30))
    B = book(fA)
    km = [(r["ticker"], r["k1_close_date"]) for r in B if r["event"] == F.K1M]
    ok("T7a K1 月底列在 10/30（燈亮月最後交易日）各一", sorted(km) == [("BE", "2026-10-30"), ("LRCX", "2026-10-30")], str(km))
    oz = run(R, os.path.join(T, "fz"), os.path.join(T, "pz"), "2026-10-29")
    ok("T7b 10/29 還沒有 K1 月底列", not [r for r in oz["new"] if r["event"] == F.K1M])
    good = True; info = []
    for t in ("BE", "LRCX"):
        for e, cd in ((F.K1P, "2026-10-23"), (F.K1M, "2026-10-30")):
            r = ev(B, t, e)[0]
            h = k1_hand(t, cd, pd.Period("2026-10", "M"))
            got = (float(r["k1a"]), float(r["k1b"]), float(r["k1c"]))
            good &= all(abs(g - round(x, 3)) < 1e-9 for g, x in zip(got, h)) and r["k1_base_date"] == "2026-04-30"
            info.append(f"{t}{'★' if e == F.K1P else ''} {got} 手算 {tuple(round(x, 3) for x in h)}")
    ok("T7c K1a／b／c（兩卡 × 代替月底／月底）＝手算（3 位）、基期 2026-04-30", good, "；".join(info))
    kp = F.read_rows(os.path.join(pA, "v4_k1.csv"))
    ok("T7d K1 細項（收盤、最低、TR）只在私有 v4_k1.csv（4 列、n_months＝24）", len(kp) == 4 and all(r["n_months"] == "24" for r in kp))
    # T10 月底淨值
    nav = sorted((r["ticker"], r["trade_date"]) for r in B if r["event"] == F.NAV_EV)
    exp = sorted((t, d) for t in ("BE", "LRCX", F.ALL) for d in ("2026-10-30", "2026-11-30", "2026-12-31", "2027-01-29"))
    ok("T10a 月底淨值列：兩卡＋全部 × 10/30、11/30、12/31、2027-01-29（資料日本身是月底 ⇒ 外推跨月才記）", nav == exp, str(nav))
    o28 = run(R, os.path.join(T, "f28"), os.path.join(T, "p28"), "2027-01-28")
    ok("T10a' 資料日 1/28（非月底）不記 1 月淨值", not [x for x in o28["new"] if x["event"] == F.NAV_EV and x["trade_date"] >= "2027-01-01"])
    r = [x for x in B if x["event"] == F.NAV_EV and x["ticker"] == "BE" and x["trade_date"] == "2026-11-30"][0]
    h = (aclose("BE", "2026-11-30") / aopen("BE", "2026-10-26") - 1 - 2 * F.COST)
    ok("T10b BE 11/30 淨值＝手算", r["ret_rule"] == f"{h * 100:+.2f}%" and r["ret_sp500tr"] == f"{(tr('2026-11-30') / tr('2026-10-23') - 1) * 100:+.2f}%",
       f"{r['ret_rule']} vs {h * 100:+.2f}%")

    # T5 冪等
    raw = open(os.path.join(fA, "book.csv"), "rb").read()
    o = run(R, fA, pA, "2027-01-29")
    ok("T5a 重跑零新列、book 位元組相同", not o["new"] and open(os.path.join(fA, "book.csv"), "rb").read() == raw)
    fB, pB = os.path.join(T, "fB"), os.path.join(T, "pB")
    run(R, fB, pB, "2027-01-29")
    strip = lambda rows: [{k: v for k, v in x.items() if k not in ("recorded_at", "note", "seq")} for x in rows]   # noqa: E731
    key = lambda x: (x["ticker"], x["event"], x["trade_date"], x["k1_close_date"])                              # noqa: E731
    ok("T2e／T5b 晚跑一次補記 ＝ 逐晚跑（起點同為 10/26；除 seq 順序、記錄時間、註）",
       sorted(strip(book(fB)), key=key) == sorted(strip(book(fA)), key=key))
    # T9 核後 --dry
    o = run(R, os.path.join(T, "fd"), os.path.join(T, "pd"), "2026-11-05", dry=True)
    ok("T9 核後 --dry 不寫", not files(os.path.join(T, "fd"), os.path.join(T, "pd")) and o["new"])

    # T3 起點無 K 棒順延；T4 ADDS／SELLS；T11 報酬；T8 實際欄
    R2 = os.path.join(T, "root2"); build(R2, drop={"BE": ["2026-10-26"], "LRCX": ["2026-12-01", "2026-12-02"]})
    F.ADDS.clear(); F.SELLS.clear()
    F.ADDS["BE"] = ("2026-11-10", 2, "產業來信：加碼（測試）", "產業 seqT1")
    F.SELLS["LRCX"] = ("2026-12-01", "產業來信：賣出（測試）", "產業 seqT2")
    fC, pC = os.path.join(T, "fC"), os.path.join(T, "pC")
    os.makedirs(pC, exist_ok=True)
    UF = [("2026-10-27", "BE", 7, 66.6612), ("2026-11-11", "BE", 3, 71.0011), ("2026-12-15", "BE", -4, 73.5521)]
    with open(os.path.join(pC, "v4_user_fills.csv"), "w", encoding="utf-8") as f:
        f.write("date,ticker,shares,price\n" + "".join(f"{d},{t},{s},{p}\n" for d, t, s, p in UF))
    try:
        for d in CAL:
            if pd.Timestamp("2026-10-23") <= d <= pd.Timestamp("2026-12-31"):
                o = run(R2, fC, pC, str(d.date()), now=d + pd.Timedelta(hours=30))
        B = book(fC)
        s0 = ev(B, "BE", "起點買進")
        ok("T3 BE 10/26 無 K 棒 ⇒ 起點順延 10/27、註明", len(s0) == 1 and s0[0]["trade_date"] == "2026-10-27" and s0[0]["sched_date"] == "2026-10-26"
           and "順延：2026-10-26 無 K 棒" in s0[0]["note"], s0[0]["note"] if s0 else "")
        a = ev(B, "BE", "加碼")
        ok("T4a ADDS：BE 2026-11-10 開盤加 2 份成交、理由與出處照設定", len(a) == 1 and a[0]["trade_date"] == "2026-11-10" and a[0]["units"] == "2"
           and a[0]["reason"] == "產業來信：加碼（測試）" and a[0]["source"] == "產業 seqT1")
        s = ev(B, "LRCX", F.SELL_EV)
        ok("T4b SELLS：LRCX 12/01、12/02 無 K 棒 ⇒ 順延 12/03 開盤賣光 −1 份", len(s) == 1 and s[0]["trade_date"] == "2026-12-03" and s[0]["units"] == "-1"
           and "順延：2026-12-01、2026-12-02 無 K 棒" in s[0]["note"], str(s[0] if s else ""))
        ok("T4c 未設的卡不自動加碼／賣出（LRCX 無加碼、BE 無賣出）", not ev(B, "LRCX", "加碼") and not ev(B, "BE", F.SELL_EV))
        per = o["per"]; D = "2026-12-31"
        hb = (1 * (aclose("BE", D) / aopen("BE", "2026-10-27") - 1 - 2 * F.COST) + 2 * (aclose("BE", D) / aopen("BE", "2026-11-10") - 1 - 2 * F.COST)) / 3
        hbt = (1 * (tr(D) / tr("2026-10-26") - 1) + 2 * (tr(D) / tr(prev("2026-11-10")) - 1)) / 3
        hl = aopen("LRCX", "2026-12-03") / aopen("LRCX", "2026-10-26") - 1 - 2 * F.COST
        hlt = tr(prev("2026-12-03")) / tr("2026-10-23") - 1
        hs = SPYA[ix(D)] / (SPYO[ix("2026-12-03")] * SPYA[ix("2026-12-03")] / SPYC[ix("2026-12-03")]) - 1
        ok("T11a BE 規則欄報酬（1＋2 份）＝手算", abs(per["BE"]["累計報酬"] - hb) < 1e-12, f"{per['BE']['累計報酬']:.6f} vs {hb:.6f}")
        ok("T11b BE ^SP500TR 同期（成交日前一交易日收盤起）＝手算", abs(per["BE"]["^SP500TR同期"] - hbt) < 1e-12)
        ok("T11c LRCX 賣出：規則欄＝賣出日開盤、^SP500TR 到賣出日前一交易日＝手算", abs(per["LRCX"]["累計報酬"] - hl) < 1e-12 and abs(per["LRCX"]["^SP500TR同期"] - hlt) < 1e-12)
        ok("T11d 賣後回 SPY（賣出日 SPY 開盤 → 資料日收盤、還原價）＝手算", abs(per["LRCX"]["賣後回SPY"] - hs) < 1e-12, f"{per['LRCX'].get('賣後回SPY')}")
        k = lambda d: SER["BE"][2][ix(d)] / SER["BE"][1][ix(d)]                                     # noqa: E731
        inv = 7 * 66.6612 * k("2026-10-27") * (1 + F.COST) + 3 * 71.0011 * k("2026-11-11") * (1 + F.COST)
        proc = 4 * 73.5521 * k("2026-12-15") * (1 - F.COST)
        ha = (proc + 6 * aclose("BE", D) * (1 - F.COST)) / inv - 1
        ok("T8a 實際欄報酬（使用者回報 3 筆、還原價口徑）＝手算", abs(per["BE"]["實際報酬"] - ha) < 1e-12, f"{per['BE']['實際報酬']:.6f} vs {ha:.6f}")
        u = ev(B, "BE", F.USER_EV)
        ok("T8b repo 只記實際成交事件與日期（3 列、股數價格欄空）", [x["trade_date"] for x in u] == ["2026-10-27", "2026-11-11", "2026-12-15"]
           and all(x["units"] == "" and "私有" in x["note"] for x in u))
        stj = json.load(open(os.path.join(fC, "state.json"), encoding="utf-8"))
        ok("T8c state 同列規則欄與實際欄", stj["卡"]["BE"]["實際欄"].startswith(f"{ha * 100:+.2f}%") and stj["卡"]["BE"]["規則欄累計報酬"] == f"{hb * 100:+.2f}%"
           and stj["卡"]["LRCX"]["實際欄"] == "未回報", f"{stj['卡']['BE']['實際欄']}｜{stj['卡']['BE']['規則欄累計報酬']}")
        nv = [x for x in B if x["event"] == F.NAV_EV and x["ticker"] == "LRCX" and x["trade_date"] == "2026-12-31"]
        ok("T10c 賣後月底淨值列：狀態已賣、賣後回 SPY 欄有值", nv and nv[0]["status"] == "已賣" and nv[0]["ret_spy_after"] == f"{hs * 100:+.2f}%")
        raw = open(os.path.join(fC, "book.csv"), "rb").read()
        o = run(R2, fC, pC, "2026-12-31")
        ok("T5c ADDS／SELLS／實際欄情境重跑零新列、位元組相同", not o["new"] and open(os.path.join(fC, "book.csv"), "rb").read() == raw)
        # T6 私有不外洩（兩情境）
        bad = []
        for fw_ in (fA, fC):
            for x in book(fw_):
                for c in F.COLS:
                    if c in ("k1a", "k1b", "k1c") or c.startswith("ret_") or c in ("recorded_at", "data_commit"):
                        continue
                    bad += [f"{c}:{m}" for m in re.findall(r"(?<![\d.])\d+\.\d+", x[c])]
                for c in ("ret_rule", "ret_sp500tr", "ret_spy_after", "ret_actual"):
                    if x[c] and not re.fullmatch(r"[+-]\d+\.\d\d%", x[c]):
                        bad.append(f"{c}:{x[c]}")
            for fn in ("state.json", "runlog.md"):
                txt = open(os.path.join(fw_, fn), encoding="utf-8").read()
                txt = re.sub(r"[+-]\d+\.\d\d%", "", txt).replace("v4.1", "")
                txt = re.sub(r"(?:a|b|c|\"k1[abc]\": \")\d+\.\d{3}(?!\d)", "", txt)
                bad += [f"{fn}:{m}" for m in re.findall(r"(?<![\d.])\d+\.\d+", txt)]
        allpx = set()
        for t, (o_, c_, a_) in SER.items():
            allpx |= {f"{v:.2f}" for v in np.concatenate([o_, c_, a_])}
        allpx |= {str(p) for _, _, _, p in UF} | {str(s) for _, _, s, _ in UF if abs(s) > 3}
        repo_txt = "".join(open(p, encoding="utf-8-sig").read() for fw_ in (fA, fC) for p in files(fw_))
        leak = [p for p in {str(p) for _, _, _, p in UF} if p in repo_txt]
        ok("T6a repo 檔（book、state、runlog）無價格小數（只剩 % 與 K1 三位比值）", not bad, str(bad[:6]))
        ok("T6b 使用者回報價格不在 repo 檔", not leak, str(leak))
        ok("T6c repo 檔不含股數欄（使用者回報股數只在私有檔）", all(x["units"] == "" for x in book(fC) if x["event"] == F.USER_EV))
    finally:
        F.ADDS.clear(); F.SELLS.clear()
    n_ok = sum(1 for _, c, _ in RES if c)
    print(f"自測：{n_ok}/{len(RES)} PASS")
    sys.exit(0 if n_ok == len(RES) else 1)


if __name__ == "__main__":
    main()

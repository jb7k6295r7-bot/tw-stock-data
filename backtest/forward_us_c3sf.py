# -*- coding: utf-8 -*-
"""USREG-C3sF seq1（動能＋大盤濾網；美股策略線 sha d16267eb388f0711；裁定 seq353 §三.5 發號；N_組合 ＋1 於判定時計）——前瞻紙上紀錄。
回測線計算子代理建，2026-10-17 00:05（台北）。⛔ 只記前瞻；早年段、看過段只描述（describe_seen，一行、不判）；使用者不跟單本格、不影響換股單。

═══ 規則（登錄 §一 逐字；其餘逐字同 C3s S1）與補讀法（⭐ 寫死於看任何 C3sF 數字之前）═══
 F1 選股、續抱、8 槽等權、成本 0.05%、換股日 ＝ C3s forward 簿同一來源：researchUSC3s_ops.tables()（MOM ＋ S&P 500 內排名）、
    起點 ＝ ops.FWD_START_MONTH（2026-10 最後交易日收盤量測、11 月第一個交易日開盤執行），⛔ 不另寫選股。
 F2 濾網：每個月底 M 收盤量測 SPY 還原收盤（adjclose）＜ SPY 最近 200 個交易日還原收盤簡單平均（含 M 當日；SPY 自己的交易日序列）
    ⇒ 下一換股日 e ＝ M＋1【不新買】（進場名單視為空）；已持有照 C3s 原規則出場（跌出前 20%／掉出指數 ⇒ e 開盤賣；斷點、下市同 K.book）。
    SPY ≥ 200 日線 ⇒ 照 C3s 補滿空槽（每槽 ＝ 前一日總值 ÷ 8、現金用完即停，K.book 原式）。⛔ 只在月底看一次、月中不看。
 F3 空槽資金：登錄「空槽放國庫券（SHY 代替亦可，擇一寫明）」⇒ ⭐ 擇【國庫券 DTB3】：被擋那個月（e 到下一換股日前一日）現金每日 × (1 ＋ DTB3_{t−1}÷100÷252)；
    未被擋的月份現金照 C3s（K.book 現金 0 報酬）⇒ 濾網全程不觸發時 C3sF ＝ C3s forward 簿（閘：逐日差 ≤ 1e−12）。
 F4 濾網決定一經寫入 filter.csv 即凍結（SPY 還原價日後回補股利會微動，⛔ 不回頭改）；重算權益一律用已凍結的決定。
 F5 資料：個股 ＝ K.rworld() 的 world.npz（＝ C3s ops 同一份；前瞻每月需資料庫／回測照 C3s 流程更新 world）；SPY、DTB3 ＝ us-stock-data（預設本機 clone
    ~/us-stock-data，⛔ 只讀、不 pull），每列記 commit。^SP500TR ＝ K.rworld()["B"]。
 F6 紀錄（backtest/forward/us_c3sf/，只追加）：filter.csv（每月底：SPY、200 日線、擋／不擋）、monthly.csv（每期：換股後持股代號、新進、賣出、現金占比、
    月報酬、C3sF／C3s 本體／^SP500TR 累積）、state.json、runlog.md。⛔ 逐日權益只寫 ~/us_work/forward_us/c3sf_daily.csv。
 F7 判定（登錄 §二、§三）：滿 36 期（2029-10 月底）與 C3s forward 同時判，對 ^SP500TR；必報：年化、最大回落、比值、擋下月份數、擋下期間 C3s 本體報酬、
    平均股票曝險與同曝險 C3s＋國庫券對照。⛔ 中途只報不判。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_c3sf                 # 補到最後一個已結束月底
    ... -m backtest.forward_us_c3sf --month 2026-10-30      # 資料最後一日就是月底（當晚）：先記濾網決定（第 0 列）
    ... -m backtest.forward_us_c3sf --selftest              # 閘：濾網全不擋 ⇒ ＝ K.book；SMA200 另寫對照
    ... -m backtest.forward_us_c3sf --describe              # 看過段一行描述（⛔ 不判）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K            # noqa: E402
from backtest import researchUSC3s_ops as OPS    # noqa: E402
from backtest.forward_us_c11 import commit_of, now_tpe   # noqa: E402

ROOT = os.path.expanduser("~/us-stock-data")
SNAP = os.path.expanduser("~/usdata/881c86a")       # world.npz 同一快照（describe／selftest 用）
FWD = os.path.expanduser("~/tw-p17/backtest/forward/us_c3sf")
PRIV = os.path.expanduser("~/us_work/forward_us")
SMA_N = 200
BASE_DAY = "2026-10-30"      # 起點月底（2026-10 最後交易日）
FCOLS = ["月底", "SPY還原收盤", "SPY200日線", "濾網", "作用換股日", "資料commit", "記錄時間（台北）"]
MCOLS = ["期", "月份", "量測月底", "濾網", "換股日", "月底", *[f"持股{i}" for i in range(1, 9)], "本月新進", "本月賣出", "持股數", "現金占比",
         "C3sF月報酬", "^SP500TR月報酬", "C3sF累積", "C3s本體累積", "^SP500TR累積", "資料", "記錄時間（台北）", "備註"]
TOL = 1e-9


# ═════════════ SPY 濾網與 DTB3 ═════════════
def spy_filter_table(root=ROOT):
    y = pd.read_csv(os.path.join(root, "data", "macro", "yahoo_SPY.csv"), dtype={"date": str}).drop_duplicates("date").set_index("date").sort_index()
    ac = pd.to_numeric(y["adjclose"], errors="coerce").dropna()
    ac = ac[ac > 0]
    sma = ac.rolling(SMA_N, min_periods=SMA_N).mean()
    return pd.DataFrame({"adj": ac, "sma": sma})


def dtb3_g(cal, root=ROOT):
    r = pd.read_csv(os.path.join(root, "data", "macro", "fred_DTB3.csv"), dtype=str, keep_default_na=False)
    v = pd.Series(pd.to_numeric(r["value"].replace({"": None, ".": None}), errors="coerce").to_numpy(float), index=r["date"].to_numpy(str)).dropna()
    ds = [str(d.date()) for d in cal]
    dt = v.reindex(sorted(set(v.index) | set(ds))).ffill().reindex(ds).to_numpy(float)
    g = np.zeros(len(cal)); g[1:] = np.nan_to_num(dt[:-1]) / 100.0 / 252
    return g


# ═════════════ 換股簿（K.book 同式 ＋ 被擋換股日不新買 ＋ 被擋月份現金生息）═════════════
def book_f(Wd, keep, buy, N, t0, t1, blocked, cash_g, cost=K.COST):
    O, CF, valid, last, brk = Wd["O"], Wd["CF"], Wd["valid"], Wd["last"], Wd["pb"]
    n = len(Wd["cal"]); eq = np.ones(n); cash = 1.0; pos = {}; pend = set()
    npos = np.zeros(n, np.int16); cashf = np.zeros(n); stockw = np.zeros(n)
    rset = set(int(e) for e in keep if t0 <= e <= t1)
    holds, sells, buys = {}, {}, {}
    blk = False
    for t in range(t0, t1 + 1):
        for j in list(pos):
            u, amt, b, hi = pos[j]
            if t > b and brk[t, j]:
                px = CF[t - 1, j]
            elif t > last[j]:
                px = CF[last[j], j]
            else:
                continue
            pos.pop(j); pend.discard(j); cash += u * px - amt * cost; sells.setdefault(t, []).append((j, "斷點／下市"))
        isreb = t in rset
        if isreb:
            blk = t in blocked
            ks = keep.get(t, set())
            pend |= (set(pos) - set(ks)); pend -= set(ks)
        for j in sorted(pend):
            if j not in pos:
                pend.discard(j); continue
            o_t = O[t, j]
            if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                continue
            u, amt, b, hi = pos.pop(j); cash += u * o_t - amt * cost; pend.discard(j); sells.setdefault(t, []).append((j, "換股"))
        if isreb:
            if not blk:
                free = N - len(pos)
                for j in [j for j in buy.get(t, []) if j not in pos][:max(free, 0)]:
                    o_t = O[t, j]
                    if not (valid[t, j] and np.isfinite(o_t) and o_t > 0):
                        continue
                    amt = min(eq[t - 1] / N, cash)
                    if amt <= 1e-12:
                        break
                    cash -= amt; pos[j] = [amt / o_t, amt, t, o_t]; buys.setdefault(t, []).append(j)
            holds[t] = sorted(pos)
        if blk:
            cash *= 1.0 + cash_g[t]
        hv = 0.0
        for j, p in pos.items():
            c = CF[t, j]; hv += p[0] * c
            if c > p[3]:
                p[3] = c
        eq[t] = cash + hv; npos[t] = len(pos); cashf[t] = cash / eq[t]; stockw[t] = hv / eq[t]
    eq[:t0] = 1.0; eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "npos": npos, "cashf": cashf, "stockw": stockw, "holds": holds, "sells": sells, "buys": buys, "open": sorted(pos)}


def decide(ft, d):
    """月底 d（YYYY-MM-DD）⇒ (SPY, SMA200, 擋?)；SPY 當日無資料 ⇒ None（T3：當月暫停新買由 C3s 停用條件處理，這裡回 None 由呼叫端報錯）。"""
    if d not in ft.index or not np.isfinite(ft.loc[d, "sma"]):
        return None
    a, s = float(ft.loc[d, "adj"]), float(ft.loc[d, "sma"])
    return a, s, bool(a < s)


def read_csv_rows(fp):
    return list(csv.DictReader(open(fp, encoding="utf-8-sig"))) if os.path.exists(fp) else []


def write_csv_rows(fp, cols, rows):
    with open(fp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def update(month=None, root=ROOT, fwd=FWD, priv=PRIV, start_month=None):
    T0 = time.time(); os.makedirs(fwd, exist_ok=True); os.makedirs(priv, exist_ok=True)
    R = K.rworld(); cal = R["cal"]; n = R["n"]; W = R["Wd"]; tick = W["tick"]; ym = R["ym"]
    y0, m0 = start_month or OPS.FWD_START_MONTH
    k0 = y0 * 12 + m0 - 1
    if k0 not in R["last"]:
        msg = f"world 資料未到起點月 {y0}-{m0:02d}（world 最後一日 {cal[-1].date()}）"; print(msg); return {"狀態": msg}
    M0 = R["last"][k0]
    if start_month is None and str(cal[M0].date()) != BASE_DAY:
        msg = f"world 尚未含起點月底 {BASE_DAY}（world 最後一日 {cal[-1].date()}）"; print(msg); return {"狀態": msg}
    MEs = [p for p in range(M0, n) if (p + 1 < n and ym[p + 1] != ym[p])]
    if month is not None:
        Mf, _v = OPS.month_end_index(month)
        if Mf not in MEs:
            MEs.append(Mf)
    if not MEs or MEs[0] != M0:
        msg = f"起點月底 {cal[M0].date()} 尚未確認結束（world 最後一日 {cal[-1].date()}；當晚請用 --month）"; print(msg); return {"狀態": msg}
    commit = commit_of(root); ft = spy_filter_table(root)
    ffp = os.path.join(fwd, "filter.csv"); frows = read_csv_rows(ffp); fz = {r["月底"]: r for r in frows}
    log = []
    for p in MEs:
        d = str(cal[p].date())
        if d in fz:
            continue
        r = decide(ft, d)
        if r is None:
            raise SystemExit(f"SPY {d} 無資料或 200 日線不可算（資料 {commit[:10]}）⇒ 先補資料")
        e_str = str(cal[p + 1].date()) if p + 1 < n else "（下一交易日）"
        fz[d] = {"月底": d, "SPY還原收盤": repr(r[0]), "SPY200日線": repr(r[1]), "濾網": "擋" if r[2] else "不擋", "作用換股日": e_str,
                 "資料commit": commit[:10], "記錄時間（台北）": now_tpe()}
        frows.append(fz[d]); log.append(f"{d} 濾網 {fz[d]['濾網']}")
    write_csv_rows(ffp, FCOLS, frows)
    # 權益：b0 ＝ M0＋1 起；需 b0 在資料內
    mrows_fp = os.path.join(fwd, "monthly.csv"); old = read_csv_rows(mrows_fp); have = {r["期"]: r for r in old}
    out = list(old); b0 = M0 + 1
    rows = []
    if "0" not in have:
        f0 = fz[str(cal[M0].date())]
        rows.append({"期": "0", "月份": f"起點 {y0}-{m0:02d}", "量測月底": str(cal[M0].date()), "濾網": f0["濾網"], "換股日": f0["作用換股日"], "月底": str(cal[M0].date()),
                     "C3sF累積": "1.0", "C3s本體累積": "1.0", "^SP500TR累積": "1.0", "資料": f"world {cal[-1].date()}／SPY {commit[:10]}",
                     "記錄時間（台北）": now_tpe(), "備註": "起點：月底收盤量測、下一交易日開盤執行" + ("；⚠ 濾網擋 ⇒ 起點不買、全數國庫券" if f0["濾網"] == "擋" else "")})
    done = [p for p in MEs if p > M0]
    if done:
        T = OPS.tables(); t1 = done[-1]
        blocked = {p + 1 for p in MEs if fz[str(cal[p].date())]["濾網"] == "擋"}
        g = dtb3_g(cal, root)
        rf = book_f(W, T["KEEP"], T["BUY"], K.N_SLOTS, b0, t1, blocked, g)
        rc, _ = OPS.run_book(T, b0, t1)
        B = R["B"]
        prev = M0
        for k, p in enumerate(done, 1):
            if str(k) in have:
                o = have[str(k)]
                if abs(float(o["C3sF累積"]) - rf["eq"][p]) > TOL:
                    log.append(f"期 {k} 重算 {rf['eq'][p]!r} ≠ 已寫 {o['C3sF累積']}（保留已寫）")
                prev = p; continue
            e = prev + 1
            hs = [str(tick[j]) for j in rf["holds"].get(e, [])]
            sl = [str(tick[j]) for t in range(e, p + 1) for j, _w in rf["sells"].get(t, [])]
            f_ = fz[str(cal[prev].date())]
            rows.append({"期": str(k), "月份": cal[p].strftime("%Y-%m"), "量測月底": str(cal[prev].date()), "濾網": f_["濾網"], "換股日": str(cal[e].date()),
                         "月底": str(cal[p].date()), **{f"持股{i + 1}": (hs[i] if i < len(hs) else "") for i in range(8)},
                         "本月新進": " ".join(str(tick[j]) for j in rf["buys"].get(e, [])), "本月賣出": " ".join(sl), "持股數": str(int(rf["npos"][p])),
                         "現金占比": f"{rf['cashf'][p]:.6f}", "C3sF月報酬": f"{rf['eq'][p] / rf['eq'][prev] - 1:.6f}", "^SP500TR月報酬": f"{B[p] / B[prev] - 1:.6f}",
                         "C3sF累積": repr(float(rf["eq"][p])), "C3s本體累積": repr(float(rc["eq"][p])), "^SP500TR累積": repr(float(B[p] / B[M0])),
                         "資料": f"world {cal[-1].date()}／SPY {commit[:10]}", "記錄時間（台北）": now_tpe(),
                         "備註": ("被擋：不新買、現金放國庫券（DTB3）" if f_["濾網"] == "擋" else "") + ("；⭐ 滿 36 期：與 C3s forward 同時判" if k == 36 else "")})
            prev = p
        pd.DataFrame({"日期": cal[M0:t1 + 1].strftime("%Y-%m-%d"), "C3sF": rf["eq"][M0:t1 + 1], "C3s本體": rc["eq"][M0:t1 + 1],
                      "^SP500TR": B[M0:t1 + 1] / B[M0], "股票占比": rf["stockw"][M0:t1 + 1]}).to_csv(os.path.join(priv, "c3sf_daily.csv"), index=False, float_format="%.12g")
    out += rows
    write_csv_rows(mrows_fp, MCOLS, out)
    st = {"件": "USREG-C3sF seq1 前瞻紙上紀錄（SPY 月底在 200 日線下不新買）", "起點": f"{cal[M0].date()} 收盤量測／{'下一交易日' if b0 >= n else cal[b0].date()} 開盤",
          "濾網已記月底": len(frows), "權益已記期數": len(done), "world 最後一日": str(cal[-1].date()), "SPY／DTB3 資料commit": commit, "寫入時間": now_tpe()}
    json.dump(st, open(os.path.join(fwd, "state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(fwd, "runlog.md"), "a", encoding="utf-8") as f:
        f.write(f"- {now_tpe()}｜world 至 {cal[-1].date()}｜SPY {commit[:10]}｜濾網 {len(frows)} 個月底｜權益 {len(done)} 期｜新增 {len(rows)} 列"
                + ("｜" + "；".join(log) if log else "") + f"｜{time.time() - T0:.0f}s\n")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    return st


# ═════════════ 閘與描述 ═════════════
def selftest():
    R = K.rworld(); cal = R["cal"]; w1 = R["w1"]; W = R["Wd"]
    T = OPS.tables(); t0 = T["t0"]
    g = dtb3_g(cal, SNAP)
    rf = book_f(W, T["KEEP"], T["BUY"], K.N_SLOTS, t0, w1, set(), g)
    rc, _ = OPS.run_book(T, t0, w1)
    out = {"G1 濾網全不擋 ⇒ book_f ＝ K.book（主臂 2017-01～2026-09）最大差": float(np.max(np.abs(rf["eq"] - rc["eq"])))}
    # 全擋：只出不進、現金生息 ⇒ 權益 ＝ 現金路徑（另算）
    allb = {e for e in T["KEEP"] if t0 <= e <= w1}
    rb = book_f(W, T["KEEP"], T["BUY"], K.N_SLOTS, t0, w1, allb, g)
    cash = 1.0
    for t in range(t0, w1 + 1):
        cash *= 1 + g[t]
    out["G2 全擋 ⇒ 全期現金、權益 ＝ Π(1＋DTB3) 差"] = abs(rb["eq"][w1] - cash)
    # SMA200 另寫（迴圈）抽 5 個月底
    ft = spy_filter_table(SNAP)
    adj = ft["adj"]; idx = list(adj.index); mism = 0
    for d in ("2018-12-31", "2020-03-31", "2022-06-30", "2023-10-31", "2026-09-30"):
        i = idx.index(d); s = sum(adj.iloc[i - SMA_N + 1:i + 1]) / SMA_N
        mism += int(abs(s - ft.loc[d, "sma"]) > 1e-9)
    out["G3 SMA200 另寫迴圈 抽 5 個月底 不同數"] = mism
    out["全過"] = bool(out["G1 濾網全不擋 ⇒ book_f ＝ K.book（主臂 2017-01～2026-09）最大差"] <= 1e-12 and out["G2 全擋 ⇒ 全期現金、權益 ＝ Π(1＋DTB3) 差"] <= 1e-12 and mism == 0)
    out["算於"] = now_tpe()
    os.makedirs(FWD, exist_ok=True)
    json.dump(out, open(os.path.join(FWD, "selftest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def describe_seen():
    """看過段（2016-12-30～2026-09-30）C3sF 一行描述：⛔ 不判（登錄 §二：早年、看過段只描述；結果句附「偏向存活股」）。"""
    R = K.rworld(); cal = R["cal"]; w1 = R["w1"]; W = R["Wd"]
    T = OPS.tables(); t0 = T["t0"]; a0 = t0 - 1
    ft = spy_filter_table(SNAP); g = dtb3_g(cal, SNAP)
    rebs = sorted(e for e in T["KEEP"] if t0 <= e <= w1)
    blocked = set()
    for e in rebs:
        r = decide(ft, str(cal[e - 1].date()))
        if r is not None and r[2]:
            blocked.add(e)
    rf = book_f(W, T["KEEP"], T["BUY"], K.N_SLOTS, t0, w1, blocked, g)
    rc, _ = OPS.run_book(T, t0, w1)
    mf, mc, mb = K.metrics(rf["eq"], a0, w1), K.metrics(rc["eq"], a0, w1), K.metrics(R["B"], a0, w1)
    o = {"件": "USREG-C3sF 看過段描述（⛔ 不判；母體事後縮成 S&P 500、偏向存活股）", "窗": [str(cal[a0].date()), str(cal[w1].date())],
         "C3sF": mf, "C3s 本體": mc, "^SP500TR": mb, "被擋換股日數": len(blocked), "換股日數": len(rebs),
         "被擋月份": [str(cal[e - 1].date())[:7] for e in sorted(blocked)], "平均股票占比": float(rf["stockw"][t0:w1 + 1].mean()),
         "C3s 本體平均股票占比": float(1 - rc["cashf"][t0:w1 + 1].mean()), "SPY／DTB3": "us-stock-data 881c86a", "算於": now_tpe()}
    o["一行"] = (f"看過段（只描述）：C3sF 年化 {mf['年化']:+.1%}、回落 {mf['回落']:.1%}；C3s 本體 {mc['年化']:+.1%}／{mc['回落']:.1%}；"
               f"^SP500TR {mb['年化']:+.1%}／{mb['回落']:.1%}；{len(rebs)} 個換股日中被擋 {len(blocked)} 個（偏向存活股、⛔ 不判）")
    os.makedirs(FWD, exist_ok=True)
    json.dump(o, open(os.path.join(FWD, "describe_seen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=K._jdef)
    print(o["一行"])
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--describe", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.describe:
        describe_seen()
    else:
        update(a.month, a.root)


if __name__ == "__main__":
    main()

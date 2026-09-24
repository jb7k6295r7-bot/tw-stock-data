"""D4 前置：門檻B／參考C 對 0050 的【權重】重疊度 —— 回測線執行端。

⏳ 委託：台股策略線 20260924-0031 §四（描述性，⛔ 不開登錄、⛔ 不重跑策略）
✅ 裁定線 20260924-0037 §二末：「§四 回測線量現行 overlap：照做，⭐ 它仍然有用」
✅ 裁定線 20260924-0810 §七：「回測線：⋯D4 overlap 照量」

⛔⛔ 逐字照 0031 §四 的定義（⛔ 本支一個字都不自訂）：
    逐再平衡日 t：overlap(t) = Σ_i min( w_策略(i,t) , w_0050(i,t) )
    ・i 跑遍兩邊持股的聯集
    ・兩邊權重各自先正規化到總和 1
    ・0050 的成分與權重用【本專案的市值前 50 口徑】（原始收盤 × 當日 shares）⛔ 不是官方成分
    ・報逐月中位數 ＋ p10／p90
    ⛔ 不可用「檔數重疊比例」代替 —— 那個量對權重不敏感，而要管的正是權重

⭐⭐⭐ 本支要回報【三個定義落差】（⛔ 本線不自己裁，但要把量算出來給你們看）：

  ① ⛔⛔ **既有的「重疊度」是【檔數】比例，不是這一個量。**
     `researchp13._daily_overlap` 算的是 ov_hold ＝ |持股 ∩ 前50| ÷ |持股|
     ⇒ ⚠⚠ 而 PREREGP13 的【否證③】就是用它，門檻 OVERLAP_MAX = 0.50
     ⇒ ⇒ ⭐ 所以「重疊度」這個詞現在指兩個不同的量：
          舊（P13 否證③）＝ 檔數比例　　新（0031 §四）＝ Σ min(w, w)
     ⇒ ⛔⛔ **P13 的 50% 門檻【不可以】搬到新的量上** —— 它是在舊量上訂的。
     ⇒ ⭐ 本支把【兩個量都算、都報】，⛔ 不挑（〈一百〇八〉軸沒指定就都交代）。
     ⇒ ⏳ 這正是〈一百三十五〉的形狀（同一個名字、不同的算法）⇒ 請裁定線看要不要出卡。

  ② ⚠ 0031 §四 寫「逐【再平衡日】t」，⛔ 但門檻B／參考C 【沒有再平衡日】
     —— 它們是 N 個等權槽的連續進出場策略（逐訊號進場、到 exit_pos 出場），
     ⛔ 不像 P14／P17 那樣有月度再平衡日。
     ⇒ ⭐ 本支取【逐交易日】（＝ 與 P13 否證③ 同一個取法），並逐月取中位。
     ⇒ ⏳ 若你們要的是別的取法（例如只取每月第一個交易日），說一聲本線重算。

  ③ ⚠ w_策略 的定義：引擎是【N 個等權槽】⇒ 本支取 w ＝ 1/持股檔數（當日在手）。
     ⇒ ⭐ 這是引擎實際的配置方式，⛔ 不是本線挑的。
     ⚠ 但要注意：槽位可能沒滿（現金部位）⇒ 依 0031「兩邊權重各自先正規化到總和 1」，
       本支把在手持股正規化到 1 ⇒ ⛔ 等於把現金部位排除在這個量之外。
     ⇒ ⏳ 若你們要把現金也算進分母（那會讓 overlap 系統性變小），說一聲本線重算。
"""

from __future__ import annotations

import argparse
import ast
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
P16 = os.path.expanduser("~/tw-p16")
OUT = os.path.join(HERE, "resultsd4ov")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = lambda x: print(x, flush=True)

    sys.path.insert(0, os.path.dirname(HERE))
    from backtest import data as D
    from backtest import p4_features as P4F
    from backtest import research11 as R
    from backtest import researchp1 as P1
    from backtest import researchp7 as P7
    from backtest import researchp12 as P12

    # ⭐ 市值與前 50：直接取正典 researchp13 的原始碼，⛔ 不維護第二份（四點五）
    src = open(os.path.join(P16, "backtest", "researchp13.py"), encoding="utf-8").read()
    lines = src.splitlines(keepends=True)
    take, consts = [], []
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name in ("load_mktcap", "top50_by_month"):
            take.append("".join(lines[node.lineno - 1:node.end_lineno]))
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) in ("TOP_N", "N_SLOTS", "OVERLAP_MAX") for t in node.targets):
            consts.append("".join(lines[node.lineno - 1:node.end_lineno]))
    ns = {"np": np, "pd": pd, "os": os, "D": D}
    exec("".join(consts) + "\n" + "\n".join(take), ns)   # noqa: S102
    load_mktcap, top50_by_month = ns["load_mktcap"], ns["top50_by_month"]
    TOP_N, N_SLOTS, OVERLAP_MAX = ns["TOP_N"], ns["N_SLOTS"], ns["OVERLAP_MAX"]
    log("✅ 取自正典 researchp13：load_mktcap／top50_by_month；TOP_N={} N_SLOTS={} OVERLAP_MAX={}"
        .format(TOP_N, N_SLOTS, OVERLAP_MAX))

    cal = D.load_calendar(); ncal = len(cal)
    uni_df = D.load_universe()
    uni = uni_df.set_index("stock_id")["market"]
    panel = P4F.read_panel(os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, "全窗")
    # ⭐ listed 的定義逐字照 researchp13 第 291 行：上市（twse）普通股（kind==stock）
    #   ⚠ 所以前 50 是【上市普通股】前 50 ＝ 0050 的代理，⛔ 不是「全市場」前 50
    #     （top50_share.py 曾標出這個口徑差；0031 §四 說用「本專案的市值前 50 口徑」
    #      ⇒ ⭐ 本支取正典函式的口徑，並在此標明）
    listed = set(uni_df.loc[(uni_df["market"] == "twse") & (uni_df["kind"] == "stock"), "stock_id"])
    caps = load_mktcap(set(panel["stock_id"]) | listed, cal)
    # ⚠ 量測點：本支取【逐月】（P12.month_marks）；⛔ 而 researchp13 傳的是 entry_pos
    #   ⇒ ⭐ 又是一個沒指定的軸，本支取逐月並在報告裡標明
    months = P12.month_marks(cal, w0, w1)
    top50 = top50_by_month(caps, listed, months, ncal)
    log("[窗] 全窗 [{},{}]（{} ~ {}）｜前50 逐月 {} 個月".format(
        w0, w1, cal[w0].date(), cal[w1].date(), len(top50)))

    # ⭐ 0050 代理的【權重】＝ 市值前 50 的市值權重（原始收盤 × 當日 shares，正規化到 1）
    #   ⛔ 0031 §四 逐字：「0050 的成分與權重用本專案的市值前 50 口徑，⛔ 不是官方成分」
    capmat = {s: np.asarray(v, float) for s, v in caps.items()}

    rows = []
    for tag, sigflag in (("門檻B", "B"), ("參考C", "C")):
        sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START,
                                 signal=P12.SIG_OF["S1"] if sigflag == "B" else None) \
            if False else P7.build_sig_gate_b(panel, cal, closes, opens,
                                             start=P12.START, signal=sigflag)
        lg: list = []
        R.COST = P12.COST_STD
        R.simulate_mtm(sig, P12.RULE, N_SLOTS, np.random.default_rng(P12.SEED0),
                       closes, opens, ncal, return_equity=True, pick=None, cap_fn=None,
                       d_max=None, queue_days=0, cash_mode="zero", bench=None, log=lg)
        ev = [(int(r["t"]), int(r["exit_pos"]), r["sid"]) for r in lg if r["reason"] == "in"]
        log("[{}] 訊號 {:,} 筆／進場 {:,} 筆".format(tag, len(sig), len(ev)))

        mi = 0
        hold: dict = {}
        recs = []
        for t in range(w0, w1 + 1):
            while mi + 1 < len(months) and months[mi + 1] <= t:
                mi += 1
            cur_top = top50[int(months[mi])]
            for s in [s for s, x in hold.items() if x <= t]:
                hold.pop(s)
            for t0, x, s in ev:
                if t0 == t and x > t:
                    hold[s] = x
            if not hold:
                continue
            # w_策略：N 個等權槽 ⇒ 在手持股等權，正規化到 1（見檔頭 ③）
            hs = sorted(hold)
            w_s = {s: 1.0 / len(hs) for s in hs}
            # w_0050：前 50 的市值權重，正規化到 1
            cw = {}
            for s in cur_top:
                v = capmat.get(s)
                if v is not None and np.isfinite(v[t]) and v[t] > 0:
                    cw[s] = float(v[t])
            tot = sum(cw.values())
            if tot <= 0:
                continue
            w_b = {s: v / tot for s, v in cw.items()}
            # ⭐ 0031 §四 逐字：Σ_i min(w_策略, w_0050)，i 跑遍聯集
            ov_w = sum(min(w_s.get(s, 0.0), w_b.get(s, 0.0)) for s in set(w_s) | set(w_b))
            k = sum(1 for s in hs if s in cur_top)
            recs.append({"t": t, "ym": cal[t].strftime("%Y-%m"), "n_hold": len(hs),
                         "ov_weight": ov_w,               # ⭐ 0031 §四 要的量
                         "ov_count": k / len(hs),         # ⛔ 舊量（P13 否證③ 用的）
                         "ov_top50": k / TOP_N})
        d = pd.DataFrame(recs)
        d["pool"] = tag
        rows.append(d)
        by = d.groupby("ym")[["ov_weight", "ov_count"]].median()
        log("  ⇒ 逐日 {:,} 天有持股｜逐月中位的中位：權重 {:.4%}／檔數 {:.2%}"
            .format(len(d), by["ov_weight"].median(), by["ov_count"].median()))

    allr = pd.concat(rows, ignore_index=True)
    allr.to_csv(os.path.join(OUT, "overlap_daily.csv.gz"), index=False)

    print()
    print("=" * 78)
    print("⭐⭐ 0031 §四 要的答案：對 0050 的【權重】重疊度（逐月中位 ＋ p10／p90）")
    print("=" * 78)
    print()
    print("  {:<8}{:>12}{:>12}{:>12}{:>14}".format("候選池", "逐月中位", "p10", "p90", "有持股月數"))
    print("  " + "-" * 58)
    summ = []
    for tag in ("門檻B", "參考C"):
        d = allr[allr["pool"] == tag]
        by = d.groupby("ym")["ov_weight"].median()
        print("  {:<8}{:>11.4%}{:>12.4%}{:>12.4%}{:>14}".format(
            tag, by.median(), by.quantile(0.10), by.quantile(0.90), len(by)))
        summ.append({"pool": tag, "metric": "ov_weight", "median": by.median(),
                     "p10": by.quantile(0.10), "p90": by.quantile(0.90), "n_month": len(by)})
    print()
    print("=" * 78)
    print("⛔⛔ 對照：【檔數】重疊比例（＝ PREREGP13 否證③ 用的那個量，門檻 {:.0%}）"
          .format(OVERLAP_MAX))
    print("=" * 78)
    print()
    print("  {:<8}{:>12}{:>12}{:>12}".format("候選池", "逐月中位", "p10", "p90"))
    print("  " + "-" * 46)
    for tag in ("門檻B", "參考C"):
        d = allr[allr["pool"] == tag]
        by = d.groupby("ym")["ov_count"].median()
        print("  {:<8}{:>11.2%}{:>12.2%}{:>12.2%}".format(
            tag, by.median(), by.quantile(0.10), by.quantile(0.90)))
        summ.append({"pool": tag, "metric": "ov_count", "median": by.median(),
                     "p10": by.quantile(0.10), "p90": by.quantile(0.90), "n_month": len(by)})
    pd.DataFrame(summ).to_csv(os.path.join(OUT, "overlap_summary.csv"), index=False)
    print()
    print("⭐⭐ 兩個量的量級差很大 ⇒ ⛔⛔ P13 否證③ 的 50% 門檻【不可以】搬到權重那個量上。")
    print("⇒ ⏳ 這是〈一百三十五〉的形狀（同一個名字、不同算法）⇒ 請裁定線看要不要出卡。")
    print()
    print("[輸出] {}／overlap_daily.csv.gz、overlap_summary.csv".format(OUT))


if __name__ == "__main__":
    main()

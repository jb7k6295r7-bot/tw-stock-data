# -*- coding: utf-8 -*-
"""PREREGU §五「先報頻率（⛔ 不看結果）」＋ 開跑前算術（裁定線 seq162 §二）——只數波段、觸及的日期與個數、剔除計數。
判準＝台股策略線 PREREGU seq1（sha 4ff4c1731fdded12）。

⛔⛔ 本支不算、不印、不存任何報酬或反彈判定：不讀 T 以後的任何收盤（剔除只看硬斷點旗標），不算 b(x)、D、X。
讀檔／偵測／事件狀態：researchU_core.py（讀法 V1～V5）＋ fib_u.py（讀法 U1～U6）。

⭐ 本支的落地讀法（⛔ 在看任何頻率之前寫在這裡）：
 Q1 合格波段數 ＝ 確認日 conf ∈ [窗起點, 窗尾−20] 的波段；每檔每年 ＝ 該檔合格波段數 ÷ 曝露年（曝露同 PREREGM Q6：
    該檔在 [窗起點, 窗尾−20] 內、從首個到最後一個有效 K 棒所跨的交易日數 ÷ 每年交易日數）；分佈只取曝露 ≥ 1 年者，另報合併母體比率。
 Q2 確認前已觸及的比例：分母 ＝ 合格波段 × 位置（每個波段每個位置一對）；分子 ＝ 該對為「確認前已觸及」。另報「至少一個位置確認前已觸及」的波段比例。
 Q3 同日穿過多位置的比例：分母 ＝ 窗內（T ∈ [窗起點, 窗尾−20]）的原始觸及（合併、剔除之前）；分子 ＝ 同一波段同一個 T 還有別的位置也被觸及者。
 Q4 開跑前算術：每格每個位置的「依構造最多區段數」＝ min(115, ⌈(窗尾−H − 窗起點 + 1)／20⌉)；「實際可達上限」＝ min(保留事件數, 有保留事件的區段數)
    （⚠ 判定用的 n_eff 只算【分勝負】的事件，那要看 T 以後的收盤 ⇒ 本支只能給上限；上限 < 30 ⇒ 依構造只能落出口①）。
"""
from __future__ import annotations
import os, sys, time, json
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchU_core as UC
from backtest import fib_u as FU
from backtest import selftest_fib_u as SFU

OUT = "backtest/resultsU"
_G = {}


def _init(cal, w0, w1, off):
    _G.update(cal=cal, w0=w0, w1=w1, off=off)


def work(args):
    sid, market = args
    cal, w0, w1, off = _G["cal"], _G["w0"], _G["w1"], _G["off"]
    S = UC.load(sid, market, cal, off)
    if S is None:
        return None
    wE = w1 - 20
    bars = S["bars"]
    lo_, hi_ = max(int(bars[0]), w0), min(int(bars[-1]), wE)
    det, cf = UC.detect_all(S, cal, w0, w1)
    wv = {}
    for k, r in det.items():
        W = r["waves"]
        inwin = [i for i, w in enumerate(W) if w0 <= w["conf"] <= wE]
        st = {}
        for t in r["touches"]:
            if t["wave"] in inwin:
                st[(t["pos"], t["state"])] = st.get((t["pos"], t["state"]), 0) + 1
        anypre = len({t["wave"] for t in r["touches"] if t["wave"] in inwin and t["state"] == "確認前已觸及"})
        raw = [t for t in r["touches"] if t["state"] == "觸及" and w0 <= t["T"] <= wE]
        key = {}
        for t in raw:
            key[(t["wave"], t["T"])] = key.get((t["wave"], t["T"]), 0) + 1
        multi = {}
        for t in raw:
            a = multi.setdefault(t["pos"], [0, 0]); a[0] += 1; a[1] += int(key[(t["wave"], t["T"])] >= 2)
        wv[k] = {"n_all": len(W), "n_win": len(inwin), "why_end": pd.Series([W[i]["why_end"] for i in inwin], dtype=object).value_counts().to_dict(),
                 "qual": r["stats"]["確認時判定"], "state": st, "anypre": anypre, "multi": multi,
                 "conf_years": [int(cal[W[i]["conf"]].year) for i in inwin],
                 "waves": [(cal[w["tL"]].date(), cal[w["tH"]].date(), cal[w["conf"]].date(), cal[w["end"]].date(), w["why_end"], w["L0"], w["H0"])
                           for w in W if w0 <= w["conf"] <= wE] if k == 5 else None}
    return {"sid": sid, "market": market, "expo": max(0, hi_ - lo_ + 1), "cfg": {k_: v["rows"] for k_, v in cf.items()},
            "wv": wv, "nan_low": S["nan_low"], "nan_high": S["nan_high"], "status": S["status"]}


def qd(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "平均": round(float(x.mean()), 4), "中位": round(float(np.median(x)), 4),
            "p90": round(float(np.percentile(x, 90)), 4), "零佔比": round(float((x == 0).mean()), 4)}


def rate(per, DPY):
    P = pd.DataFrame(per)
    P["yrs"] = P["expo"] / DPY; P = P[P["expo"] > 0]
    P["rate"] = P["n"] / P["yrs"]; P1 = P[P["yrs"] >= 1.0]
    out = {"全體": {**qd(P1["rate"]), "合併母體比率_每股票年": round(float(P["n"].sum() / P["yrs"].sum()), 4), "股票年": round(float(P["yrs"].sum()), 1)}}
    for mk, nm in (("twse", "上市"), ("tpex", "上櫃")):
        Pm = P[P["market"] == mk]; P1m = P1[P1["market"] == mk]
        out[nm] = {**qd(P1m["rate"]), "合併母體比率_每股票年": round(float(Pm["n"].sum() / Pm["yrs"].sum()), 4)}
    return out


def main():
    t0 = time.time()
    print("[時點] 開跑 {}".format(time.strftime("%F %T")), flush=True)
    fx = SFU.run_all()                                     # ⭐ fixture 全過才開跑
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cal = UC.D.load_calendar(); n = len(cal)
    w0, w1 = UC.win_index(cal); wE = w1 - 20
    DPY = (wE - w0 + 1) / ((cal[wE] - cal[w0]).days / 365.25)
    stocks = pd.read_csv(os.path.join(UC.H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UC.UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = UC.TR.load_official()
    print("[資料] 快照 {}｜日曆 {} 根｜判定窗 [{}, {}]｜T 可落 [{}, {}]｜每年交易日 {:.2f}｜gate3 {:,} 檔".format(
        UC.SHA[:10], n, UC.W0, UC.W1, cal[w0].date(), cal[wE].date(), DPY, len(U)), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, off)) as pool:
        res = pool.map(work, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    sids = sorted(ST)
    print("[讀檔＋偵測] 可用 {:,} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    R_ = {"性質": "PREREGU §五 先報頻率 ＋ 開跑前算術（⛔ 未讀任何 T 以後收盤、未算任何報酬或反彈判定）", "快照": UC.SHA,
          "判定窗": [UC.W0, UC.W1], "gate3母體": int(len(U)), "可用檔數": len(ST), "每年交易日": round(DPY, 3),
          "設計參數": {"k": FU.K_MAIN, "描述臂k": [3, 10], "回看": FU.LOOKBACK, "最短跨度": FU.MIN_SPAN, "最小漲幅": FU.MIN_RISE,
                    "有效期": FU.LIFE, "位置": FU.POS, "合併": UC.MERGE, "區段": UC.BLOCK, "區段上限": UC.CAP},
          "fixture": fx,
          "資料診斷": {"有效K棒但還原low缺值": int(sum(ST[s]["nan_low"] for s in sids)), "有效K棒但還原high缺值": int(sum(ST[s]["nan_high"] for s in sids)),
                    "下市狀態": pd.Series([ST[s]["status"] for s in sids], dtype=object).value_counts(dropna=False).to_dict()}}
    # ── 波段
    WV = {}
    for k in (5, 3, 10):
        per = [{"sid": s, "market": ST[s]["market"], "expo": ST[s]["expo"], "n": ST[s]["wv"][k]["n_win"]} for s in sids]
        why, qual, state, multi = {}, {}, {}, {}
        yrs = []
        for s in sids:
            v = ST[s]["wv"][k]
            for a, b in v["why_end"].items():
                why[a] = why.get(a, 0) + b
            for a, b in v["qual"].items():
                qual[a] = qual.get(a, 0) + b
            for (p, stt), b in v["state"].items():
                state.setdefault(p, {}); state[p][stt] = state[p].get(stt, 0) + b
            for p, (a, b) in v["multi"].items():
                m_ = multi.setdefault(p, [0, 0]); m_[0] += a; m_[1] += b
            yrs += v["conf_years"]
        nwin = sum(p["n"] for p in per)
        pre = {p: {"確認前已觸及": state.get(p, {}).get("確認前已觸及", 0), "分母_波段×位置": nwin,
                   "比例": round(state.get(p, {}).get("確認前已觸及", 0) / max(1, nwin), 4),
                   "窗內觸及": state.get(p, {}).get("觸及", 0), "未觸及": state.get(p, {}).get("未觸及", 0)} for p in FU.POS}
        anyp = sum(ST[s]["wv"][k]["anypre"] for s in sids)
        mt = {p: {"原始觸及": multi.get(p, [0, 0])[0], "同波段同日另有位置": multi.get(p, [0, 0])[1],
                  "比例": round(multi.get(p, [0, 0])[1] / max(1, multi.get(p, [0, 0])[0]), 4)} for p in FU.POS}
        tot = [sum(multi.get(p, [0, 0])[i] for p in FU.POS) for i in (0, 1)]
        WV["k{}".format(k)] = {"合格波段數_conf在窗內": nwin, "合格波段數_全期": int(sum(ST[s]["wv"][k]["n_all"] for s in sids)),
                               "有合格波段的檔數": int(sum(1 for p in per if p["n"] > 0)),
                               "每檔每年": rate(per, DPY), "逐年（conf年）": {str(a): int(b) for a, b in pd.Series(yrs).value_counts().sort_index().items()},
                               "市場別": {nm: int(sum(p["n"] for p in per if p["market"] == mk)) for mk, nm in (("twse", "上市"), ("tpex", "上櫃"))},
                               "波段結束原因": why, "擺動高點確認時判定（全期）": qual,
                               "確認前已觸及（逐位置）": pre, "至少一個位置確認前已觸及的波段": {"n": anyp, "比例": round(anyp / max(1, nwin), 4)},
                               "同日穿過多位置（逐位置）": mt, "同日穿過多位置（七位置合計）": {"原始觸及": tot[0], "同日另有位置": tot[1], "比例": round(tot[1] / max(1, tot[0]), 4)}}
        print("[波段 k{}] 窗內合格 {:,}｜每股票年 {}｜確認前已觸及(38.2) {}｜同日多位置 {}".format(
            k, nwin, WV["k{}".format(k)]["每檔每年"]["全體"]["合併母體比率_每股票年"], pre["38.2"]["比例"],
            WV["k{}".format(k)]["同日穿過多位置（七位置合計）"]["比例"]), flush=True)
    R_["波段"] = WV
    wrows = [{"sid": s, "market": ST[s]["market"], "tL": str(a), "tH": str(b), "conf": str(c_), "end": str(d), "結束原因": e,
              "L0": L0, "H0": H0} for s in sids for (a, b, c_, d, e, L0, H0) in ST[s]["wv"][5]["waves"]]
    pd.DataFrame(wrows).to_csv(os.path.join(OUT, "waves_k5.csv"), index=False, encoding="utf-8")
    # ── 事件（逐格、逐位置）
    EVF = {}; ARITH = {}
    for k, H in UC.CFGS:
        nm = UC.cfg_name(k, H)
        rows = []
        for s in sids:
            for r in ST[s]["cfg"][(k, H)]:
                rows.append({"sid": s, "market": ST[s]["market"], "pos": r["pos"], "T": str(cal[r["T"]].date()), "Ti": r["T"],
                             "tL": str(cal[r["tL"]].date()), "tH": str(cal[r["tH"]].date()), "conf": str(cal[r["conf"]].date()),
                             "狀態": r["狀態"], "f_brk_lit": r["f_brk_lit"], "f_dl_in": r["f_dl_in"], "f_brk_wave": r["f_brk_wave"]})
        E = pd.DataFrame(rows)
        E.drop(columns=["Ti", "f_brk_lit", "f_dl_in", "f_brk_wave"]).to_csv(os.path.join(OUT, "events_{}.csv".format(nm)), index=False, encoding="utf-8")
        wLast = w1 - H
        blk_max = int(min(UC.CAP, -(-(wLast - w0 + 1) // UC.BLOCK)))
        pos_d = {}
        for p in FU.POS:
            e = E[E["pos"] == p]; kpt = e[e["狀態"] == "保留"]
            blocks = int(np.minimum((kpt["Ti"] - w0) // UC.BLOCK, UC.CAP - 1).nunique()) if len(kpt) else 0
            per = [{"sid": s, "market": ST[s]["market"], "expo": ST[s]["expo"], "n": 0} for s in sids]
            cnt = kpt["sid"].value_counts().to_dict()
            for q in per:
                q["n"] = int(cnt.get(q["sid"], 0))
            pos_d[p] = {"原始_窗內": int(len(e)), "合併掉": int((e["狀態"] == "合併掉").sum()), "剔除_硬斷點": int((e["狀態"] == "剔除_硬斷點").sum()),
                        "保留": int(len(kpt)), "相異檔數": int(kpt["sid"].nunique()), "有事件的曆月數": int(kpt["T"].str[:7].nunique()),
                        "有保留事件的20日區段數": blocks, "min(保留,區段)": int(min(len(kpt), blocks)),
                        "保留中_持有窗內下市（delist on，未剔除）": int(kpt["f_dl_in"].sum()),
                        "保留中_若照H2字面下市後缺日也算斷點會多剔除": int((kpt["f_brk_lit"]).sum()),
                        "保留中_波段內部[tL,T)有硬斷點（未剔除）": int(kpt["f_brk_wave"].sum()),
                        "逐年保留": {str(a): int(b) for a, b in kpt["T"].str[:4].value_counts().sort_index().items()},
                        "市場別保留": {({"twse": "上市", "tpex": "上櫃"}[a]): int(b) for a, b in kpt["market"].value_counts().items()},
                        "每檔每年": rate(per, DPY) if H == 20 else None}
        ub = min(pos_d[p]["min(保留,區段)"] for p in FU.SIX)
        exits = ["出口①"] + (["出口②"] if min(ub, blk_max) >= 30 else []) + (["出口③"] if min(ub, blk_max) >= 100 else [])
        EVF[nm] = pos_d
        ARITH[nm] = {"T可落窗": [str(cal[w0].date()), str(cal[wLast].date())], "可落交易日": int(wLast - w0 + 1),
                     "依構造最多區段數（每位置）": blk_max, "依構造可能出口": ["出口①"] + (["出口②"] if blk_max >= 30 else []) + (["出口③"] if blk_max >= 100 else []),
                     "六位置各自 min(保留,區段)": {p: pos_d[p]["min(保留,區段)"] for p in FU.SIX},
                     "n_eff上限（六位置取最小；判定用的只算分勝負者 ⇒ 實際 ≤ 此值）": int(ub),
                     "依頻率可能出口（上限）": exits, "只能落一個出口": bool(len(exits) == 1 or blk_max < 30)}
        print("[{}] ".format(nm) + "｜".join("{} 原{:,}/併{:,}/斷{:,}/留{:,}/段{}".format(p, pos_d[p]["原始_窗內"], pos_d[p]["合併掉"], pos_d[p]["剔除_硬斷點"],
                                                                                   pos_d[p]["保留"], pos_d[p]["有保留事件的20日區段數"]) for p in FU.POS), flush=True)
        print("   算術：最多區段 {}｜n_eff 上限 {}｜可能出口 {}".format(blk_max, ub, exits), flush=True)
    R_["事件（逐格逐位置）"] = EVF
    R_["開跑前算術"] = ARITH
    R_["時點_頻率完成"] = time.strftime("%F %T")
    json.dump(R_, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("完成 {:.0f}s｜{}".format(time.time() - t0, R_["時點_頻率完成"]))


if __name__ == "__main__":
    main()
